"""Local SQLite storage for live harvest-probability history."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = (
    BACKEND_DIR
    / "outputs"
    / "harvest"
    / "harvest_prediction_history.sqlite3"
)

DATABASE_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(
        DATABASE_PATH
    )
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS
            harvest_prediction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                prediction_timestamp TEXT NOT NULL,
                sensor_timestamp TEXT,
                harvest_probability REAL NOT NULL,
                hui REAL NOT NULL,
                status TEXT NOT NULL,
                decision_threshold REAL NOT NULL,
                model_version TEXT,
                data_completeness REAL,
                confidence TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_harvest_prediction_device_time
            ON harvest_prediction_history (
                device_id,
                prediction_timestamp
            )
            """
        )


def save_prediction(
    *,
    device_id: str,
    prediction_timestamp: str,
    sensor_timestamp: str | None,
    harvest_probability: float,
    hui: float,
    status: str,
    decision_threshold: float,
    model_version: str | None,
    data_completeness: float | None,
    confidence: str,
) -> None:
    initialize_database()

    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO
            harvest_prediction_history (
                device_id,
                prediction_timestamp,
                sensor_timestamp,
                harvest_probability,
                hui,
                status,
                decision_threshold,
                model_version,
                data_completeness,
                confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                device_id,
                prediction_timestamp,
                sensor_timestamp,
                harvest_probability,
                hui,
                status,
                decision_threshold,
                model_version,
                data_completeness,
                confidence,
            ),
        )


def get_prediction_history(
    device_id: str,
    *,
    hours: int = 168,
) -> list[dict]:
    initialize_database()

    cutoff = (
        pd.Timestamp.now(tz="UTC")
        - pd.Timedelta(hours=hours)
    ).isoformat()

    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT
                device_id,
                prediction_timestamp,
                sensor_timestamp,
                harvest_probability,
                hui,
                status,
                decision_threshold,
                model_version,
                data_completeness,
                confidence
            FROM harvest_prediction_history
            WHERE device_id = ?
              AND prediction_timestamp >= ?
            ORDER BY prediction_timestamp ASC
            """,
            (device_id, cutoff),
        ).fetchall()

    return [dict(row) for row in rows]


def detect_sustained_harvest_window(
    device_id: str,
    *,
    threshold: float,
    required_hours: int = 24,
    minimum_hourly_points: int = 18,
) -> dict:
    history = get_prediction_history(
        device_id,
        hours=max(required_hours + 6, 30),
    )

    if not history:
        return {
            "available": False,
            "reason": (
                "No stored live prediction history "
                "is available yet."
            ),
        }

    frame = pd.DataFrame(history)
    frame["prediction_timestamp"] = pd.to_datetime(
        frame["prediction_timestamp"],
        errors="coerce",
        utc=True,
    )
    frame = frame.dropna(
        subset=["prediction_timestamp"]
    )

    if frame.empty:
        return {
            "available": False,
            "reason": (
                "Stored prediction timestamps "
                "could not be parsed."
            ),
        }

    cutoff = (
        frame["prediction_timestamp"].max()
        - pd.Timedelta(hours=required_hours)
    )

    recent = frame.loc[
        frame["prediction_timestamp"] >= cutoff
    ].copy()

    recent["hour"] = (
        recent["prediction_timestamp"].dt.floor("h")
    )
    hourly = (
        recent.sort_values(
            "prediction_timestamp"
        )
        .groupby("hour", as_index=False)
        .tail(1)
    )

    span_hours = (
        hourly["hour"].max()
        - hourly["hour"].min()
    ).total_seconds() / 3600 if len(hourly) > 1 else 0

    all_above = bool(
        hourly["harvest_probability"]
        .ge(threshold)
        .all()
    )

    if (
        len(hourly) < minimum_hourly_points
        or span_hours < required_hours - 1
        or not all_above
    ):
        return {
            "available": False,
            "reason": (
                "Probability has not yet remained "
                "above the operational threshold "
                "with sufficient hourly coverage "
                f"for {required_hours} hours."
            ),
            "hourly_points": int(len(hourly)),
            "covered_hours": round(
                float(span_hours),
                2,
            ),
        }

    start = pd.Timestamp.now(
        tz="UTC"
    ).floor("h")
    end = start + pd.Timedelta(days=3)

    return {
        "available": True,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "basis": (
            "Harvest probability remained above "
            "the validated operational threshold "
            f"for approximately {required_hours} hours."
        ),
    }
