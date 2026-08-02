"""PostgreSQL access layer for live beehive IoT readings."""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_identifier(value: str, setting_name: str) -> str:
    if not _IDENTIFIER_PATTERN.fullmatch(value):
        raise RuntimeError(f"Unsafe SQL identifier in {setting_name}: {value!r}")
    return value


def _setting(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Required environment setting is missing: {name}")
    return value


DATABASE_URL = _setting("DATABASE_URL")
DATABASE_SSLMODE = os.getenv("DATABASE_SSLMODE", "require")

SCHEMA = _safe_identifier(_setting("IOT_SCHEMA", "public"), "IOT_SCHEMA")
TABLE = _safe_identifier(_setting("IOT_SENSOR_TABLE", "beehive_readings"), "IOT_SENSOR_TABLE")

HIVE_COLUMN = _safe_identifier(_setting("IOT_HIVE_COLUMN", "device_id"), "IOT_HIVE_COLUMN")
RECORDED_AT_COLUMN = _safe_identifier(
    _setting("IOT_TIMESTAMP_COLUMN", "recorded_at"), "IOT_TIMESTAMP_COLUMN"
)
READING_AT_COLUMN = _safe_identifier(
    _setting("IOT_READING_AT_COLUMN", "reading_at"), "IOT_READING_AT_COLUMN"
)
TEMPERATURE_COLUMN = _safe_identifier(
    _setting("IOT_TEMPERATURE_COLUMN", "internal_temp"), "IOT_TEMPERATURE_COLUMN"
)
HUMIDITY_COLUMN = _safe_identifier(
    _setting("IOT_HUMIDITY_COLUMN", "internal_humidity"), "IOT_HUMIDITY_COLUMN"
)
CO2_COLUMN = _safe_identifier(_setting("IOT_CO2_COLUMN", "internal_co2"), "IOT_CO2_COLUMN")
WEIGHT_COLUMN = _safe_identifier(_setting("IOT_WEIGHT_COLUMN", "total_weight"), "IOT_WEIGHT_COLUMN")
EXTERNAL_TEMPERATURE_COLUMN = _safe_identifier(
    _setting("IOT_EXTERNAL_TEMPERATURE_COLUMN", "external_temp"),
    "IOT_EXTERNAL_TEMPERATURE_COLUMN",
)
EXTERNAL_HUMIDITY_COLUMN = _safe_identifier(
    _setting("IOT_EXTERNAL_HUMIDITY_COLUMN", "external_humidity"),
    "IOT_EXTERNAL_HUMIDITY_COLUMN",
)
BATTERY_COLUMN = _safe_identifier(
    _setting("IOT_BATTERY_VOLTAGE_COLUMN", "battery_voltage"),
    "IOT_BATTERY_VOLTAGE_COLUMN",
)

TABLE_REFERENCE = f'"{SCHEMA}"."{TABLE}"'
EVENT_TIMESTAMP_EXPRESSION = (
    f'COALESCE("{READING_AT_COLUMN}", "{RECORDED_AT_COLUMN}")'
)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create one pooled SQLAlchemy engine for the Flask process."""
    connect_args: dict[str, str] = {}
    if DATABASE_SSLMODE:
        connect_args["sslmode"] = DATABASE_SSLMODE

    return create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_size=int(os.getenv("DATABASE_POOL_SIZE", "3")),
        max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "2")),
        pool_recycle=int(os.getenv("DATABASE_POOL_RECYCLE_SECONDS", "1800")),
    )


def check_database_health() -> dict:
    with get_engine().connect() as connection:
        row = connection.execute(
            text(
                f"""
                SELECT
                    NOW() AS server_time,
                    COUNT(*) AS total_rows,
                    COUNT(DISTINCT "{HIVE_COLUMN}") AS total_devices,
                    MAX({EVENT_TIMESTAMP_EXPRESSION}) AS latest_timestamp
                FROM {TABLE_REFERENCE}
                """
            )
        ).mappings().one()

    return {
        "database_connected": True,
        "server_time": row["server_time"].isoformat() if row["server_time"] else None,
        "total_rows": int(row["total_rows"] or 0),
        "total_devices": int(row["total_devices"] or 0),
        "latest_timestamp": (
            row["latest_timestamp"].isoformat() if row["latest_timestamp"] else None
        ),
    }


def get_available_devices() -> list[str]:
    query = text(
        f"""
        SELECT DISTINCT "{HIVE_COLUMN}" AS hive_id
        FROM {TABLE_REFERENCE}
        WHERE "{HIVE_COLUMN}" IS NOT NULL
        ORDER BY "{HIVE_COLUMN}"
        """
    )

    with get_engine().connect() as connection:
        rows = connection.execute(query).mappings().all()

    return [str(row["hive_id"]) for row in rows]


def _base_select_sql() -> str:
    return f"""
        SELECT
            "{HIVE_COLUMN}" AS hive_id,
            {EVENT_TIMESTAMP_EXPRESSION} AS timestamp,
            "{TEMPERATURE_COLUMN}" AS internal_temperature_c,
            "{HUMIDITY_COLUMN}" AS internal_humidity_pct,
            "{CO2_COLUMN}" AS co2_ppm,
            "{WEIGHT_COLUMN}" AS hive_weight_kg,
            "{EXTERNAL_TEMPERATURE_COLUMN}" AS external_temperature_c,
            "{EXTERNAL_HUMIDITY_COLUMN}" AS external_humidity_pct,
            "{BATTERY_COLUMN}" AS battery_voltage,
            "{RECORDED_AT_COLUMN}" AS recorded_at,
            "{READING_AT_COLUMN}" AS reading_at
        FROM {TABLE_REFERENCE}
    """


def get_latest_reading(device_id: str) -> dict | None:
    query = text(
        _base_select_sql()
        + f"""
        WHERE "{HIVE_COLUMN}" = :device_id
          AND {EVENT_TIMESTAMP_EXPRESSION} IS NOT NULL
        ORDER BY {EVENT_TIMESTAMP_EXPRESSION} DESC
        LIMIT 1
        """
    )

    with get_engine().connect() as connection:
        row = connection.execute(query, {"device_id": device_id}).mappings().first()

    if row is None:
        return None

    result = dict(row)
    for column in ["timestamp", "recorded_at", "reading_at"]:
        if result.get(column) is not None:
            result[column] = result[column].isoformat()
    return result


def get_recent_readings(device_id: str, history_hours: int = 168) -> pd.DataFrame:
    if history_hours <= 0 or history_hours > 24 * 365:
        raise ValueError("history_hours must be between 1 and 8760.")

    query = text(
        _base_select_sql()
        + f"""
        WHERE "{HIVE_COLUMN}" = :device_id
          AND {EVENT_TIMESTAMP_EXPRESSION} IS NOT NULL
          AND {EVENT_TIMESTAMP_EXPRESSION}
              >= NOW() - (:history_hours * INTERVAL '1 hour')
        ORDER BY {EVENT_TIMESTAMP_EXPRESSION} ASC
        """
    )

    with get_engine().connect() as connection:
        frame = pd.read_sql_query(
            query,
            connection,
            params={"device_id": device_id, "history_hours": int(history_hours)},
        )

    return frame


def get_recent_readings_for_all_devices(history_hours: int = 168) -> pd.DataFrame:
    if history_hours <= 0 or history_hours > 24 * 365:
        raise ValueError("history_hours must be between 1 and 8760.")

    query = text(
        _base_select_sql()
        + f"""
        WHERE {EVENT_TIMESTAMP_EXPRESSION} IS NOT NULL
          AND {EVENT_TIMESTAMP_EXPRESSION}
              >= NOW() - (:history_hours * INTERVAL '1 hour')
        ORDER BY "{HIVE_COLUMN}", {EVENT_TIMESTAMP_EXPRESSION} ASC
        """
    )

    with get_engine().connect() as connection:
        frame = pd.read_sql_query(
            query,
            connection,
            params={"history_hours": int(history_hours)},
        )

    return frame
