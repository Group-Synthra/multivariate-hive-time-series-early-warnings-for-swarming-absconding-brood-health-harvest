# Read live beehive measurements from PostgreSQL/Supabase.
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class IoTDatabaseError(RuntimeError):
    """Raised when live IoT readings cannot be loaded safely."""


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise IoTDatabaseError(
            f"{name} is not configured. Add it to backend/.env and restart Flask."
        )
    return value


def _identifier(name: str, value: str) -> str:
    """Validate configurable SQL identifiers before interpolating them."""
    if not _IDENTIFIER.fullmatch(value):
        raise IoTDatabaseError(
            f"Invalid SQL identifier in {name}: {value!r}. "
            "Use letters, digits and underscores only."
        )
    return value


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class IoTDatabaseSettings:
    """PostgreSQL connection and schema mapping.

    Defaults match the supplied Supabase table ``public.beehive_readings``.
    Environment variables may still override the mapping for other deployments.
    """

    database_url: str
    schema: str
    table: str
    hive_column: str
    timestamp_column: str
    temperature_column: str
    humidity_column: str
    co2_column: str
    weight_column: str
    reading_at_column: str
    external_temperature_column: str
    external_humidity_column: str
    battery_voltage_column: str
    feature_timezone: str
    timestamps_are_utc: bool
    sslmode: str

    @classmethod
    def from_environment(cls) -> "IoTDatabaseSettings":
        return cls(
            database_url=_required_env("DATABASE_URL"),
            schema=_identifier("IOT_SCHEMA", os.getenv("IOT_SCHEMA", "public")),
            table=_identifier(
                "IOT_SENSOR_TABLE",
                os.getenv("IOT_SENSOR_TABLE", "beehive_readings"),
            ),
            hive_column=_identifier(
                "IOT_HIVE_COLUMN",
                os.getenv("IOT_HIVE_COLUMN", "device_id"),
            ),
            timestamp_column=_identifier(
                "IOT_TIMESTAMP_COLUMN",
                os.getenv("IOT_TIMESTAMP_COLUMN", "recorded_at"),
            ),
            temperature_column=_identifier(
                "IOT_TEMPERATURE_COLUMN",
                os.getenv("IOT_TEMPERATURE_COLUMN", "internal_temp"),
            ),
            humidity_column=_identifier(
                "IOT_HUMIDITY_COLUMN",
                os.getenv("IOT_HUMIDITY_COLUMN", "internal_humidity"),
            ),
            co2_column=_identifier(
                "IOT_CO2_COLUMN",
                os.getenv("IOT_CO2_COLUMN", "internal_co2"),
            ),
            weight_column=_identifier(
                "IOT_WEIGHT_COLUMN",
                os.getenv("IOT_WEIGHT_COLUMN", "total_weight"),
            ),
            reading_at_column=_identifier(
                "IOT_READING_AT_COLUMN",
                os.getenv("IOT_READING_AT_COLUMN", "reading_at"),
            ),
            external_temperature_column=_identifier(
                "IOT_EXTERNAL_TEMPERATURE_COLUMN",
                os.getenv("IOT_EXTERNAL_TEMPERATURE_COLUMN", "external_temp"),
            ),
            external_humidity_column=_identifier(
                "IOT_EXTERNAL_HUMIDITY_COLUMN",
                os.getenv("IOT_EXTERNAL_HUMIDITY_COLUMN", "external_humidity"),
            ),
            battery_voltage_column=_identifier(
                "IOT_BATTERY_VOLTAGE_COLUMN",
                os.getenv("IOT_BATTERY_VOLTAGE_COLUMN", "battery_voltage"),
            ),
            feature_timezone=os.getenv("IOT_FEATURE_TIMEZONE", "Asia/Colombo").strip(),
            timestamps_are_utc=_env_bool("IOT_TIMESTAMPS_ARE_UTC", True),
            sslmode=os.getenv("DATABASE_SSLMODE", "require").strip(),
        )

    @property
    def qualified_table(self) -> str:
        return f'"{self.schema}"."{self.table}"'

    @property
    def expected_columns(self) -> list[str]:
        return [
            self.hive_column,
            self.timestamp_column,
            self.temperature_column,
            self.humidity_column,
            self.co2_column,
            self.weight_column,
            self.reading_at_column,
            self.external_temperature_column,
            self.external_humidity_column,
            self.battery_voltage_column,
        ]


class PostgreSQLHiveRepository:
    """Read-only repository for actual hive sensor measurements."""

    def __init__(
        self,
        settings: IoTDatabaseSettings | None = None,
        engine: Engine | None = None,
    ) -> None:
        self.settings = settings or IoTDatabaseSettings.from_environment()
        self._engine = engine

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            connect_args: dict[str, Any] = {}
            if self.settings.sslmode:
                connect_args["sslmode"] = self.settings.sslmode
            self._engine = create_engine(
                self.settings.database_url,
                pool_pre_ping=True,
                pool_recycle=300,
                connect_args=connect_args,
            )
        return self._engine

    def ping(self) -> dict[str, Any]:
        """Check connectivity and confirm that the expected table columns exist."""
        s = self.settings
        column_query = text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema
              AND table_name = :table
            ORDER BY ordinal_position
            """
        )
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                available = {
                    row[0]
                    for row in connection.execute(
                        column_query,
                        {"schema": s.schema, "table": s.table},
                    ).all()
                }
        except (SQLAlchemyError, OSError) as exc:
            raise IoTDatabaseError(f"Unable to connect to the IoT database: {exc}") from exc

        if not available:
            raise IoTDatabaseError(
                f"Table {s.schema}.{s.table} was not found or is not visible to the database user."
            )

        missing = [column for column in s.expected_columns if column not in available]
        if missing:
            raise IoTDatabaseError(
                f"Table {s.schema}.{s.table} is missing configured columns: {missing}"
            )

        return {
            "connected": True,
            "schema": s.schema,
            "table": s.table,
            "feature_timezone": s.feature_timezone,
            "timestamp_column": s.timestamp_column,
            "hive_column": s.hive_column,
            "validated_columns": s.expected_columns,
        }

    def list_hives(self) -> list[dict[str, Any]]:
        s = self.settings
        query = text(
            f"""
            SELECT
                "{s.hive_column}"::text AS hive,
                MAX("{s.timestamp_column}") AS latest_timestamp,
                COUNT(*) AS reading_count
            FROM {s.qualified_table}
            WHERE "{s.hive_column}" IS NOT NULL
            GROUP BY "{s.hive_column}"
            ORDER BY "{s.hive_column}"::text
            """
        )
        try:
            with self.engine.connect() as connection:
                rows = connection.execute(query).mappings().all()
        except SQLAlchemyError as exc:
            raise IoTDatabaseError(f"Unable to list IoT hives: {exc}") from exc

        output: list[dict[str, Any]] = []
        for row in rows:
            timestamp = self._normalise_single_timestamp(row["latest_timestamp"])
            output.append(
                {
                    "hive": str(row["hive"]),
                    "latest_timestamp": timestamp,
                    "reading_count": int(row["reading_count"]),
                }
            )
        return output

    def fetch_history(
        self,
        hive: str,
        *,
        hours: int = 168,
        max_rows: int = 20000,
    ) -> pd.DataFrame:
        """Return actual readings from the latest ``hours`` for one hive.

        The IoT table contains roughly ten-minute readings, while the model was
        trained on hourly data. Fetching by time span rather than a raw row count
        guarantees that feature engineering receives enough hours of history.
        """
        hive = str(hive).strip()
        if not hive:
            raise ValueError("hive is required")

        hours = min(max(int(hours), 25), 24 * 30)
        max_rows = min(max(int(max_rows), 100), 100000)
        s = self.settings

        query = text(
            f"""
            WITH latest AS (
                SELECT MAX("{s.timestamp_column}") AS latest_timestamp
                FROM {s.qualified_table}
                WHERE "{s.hive_column}"::text = :hive
            )
            SELECT
                "{s.hive_column}"::text AS hive,
                "{s.timestamp_column}" AS timestamp,
                "{s.temperature_column}" AS temp,
                "{s.humidity_column}" AS humidity,
                "{s.co2_column}" AS co2,
                "{s.weight_column}" AS weight,
                "{s.reading_at_column}" AS reading_at,
                "{s.external_temperature_column}" AS external_temp,
                "{s.external_humidity_column}" AS external_humidity,
                "{s.battery_voltage_column}" AS battery_voltage
            FROM {s.qualified_table}, latest
            WHERE "{s.hive_column}"::text = :hive
              AND latest.latest_timestamp IS NOT NULL
              AND "{s.timestamp_column}" >=
                  latest.latest_timestamp - (:history_hours * INTERVAL '1 hour')
              AND "{s.timestamp_column}" IS NOT NULL
              AND "{s.temperature_column}" IS NOT NULL
              AND "{s.humidity_column}" IS NOT NULL
              AND "{s.co2_column}" IS NOT NULL
              AND "{s.weight_column}" IS NOT NULL
              AND "{s.external_temperature_column}" IS NOT NULL
              AND "{s.external_humidity_column}" IS NOT NULL
            ORDER BY "{s.timestamp_column}" ASC
            LIMIT :max_rows
            """
        )

        try:
            with self.engine.connect() as connection:
                frame = pd.read_sql_query(
                    query,
                    connection,
                    params={
                        "hive": hive,
                        "history_hours": hours,
                        "max_rows": max_rows,
                    },
                )
        except SQLAlchemyError as exc:
            raise IoTDatabaseError(
                f"Unable to load IoT history for hive {hive!r}: {exc}"
            ) from exc

        return self._clean_frame(frame)

    def fetch_latest(self, hive: str) -> dict[str, Any] | None:
        """Return the newest valid actual sensor row for one hive."""
        hive = str(hive).strip()
        if not hive:
            raise ValueError("hive is required")

        s = self.settings
        query = text(
            f"""
            SELECT
                "{s.hive_column}"::text AS hive,
                "{s.timestamp_column}" AS timestamp,
                "{s.temperature_column}" AS temp,
                "{s.humidity_column}" AS humidity,
                "{s.co2_column}" AS co2,
                "{s.weight_column}" AS weight,
                "{s.reading_at_column}" AS reading_at,
                "{s.external_temperature_column}" AS external_temp,
                "{s.external_humidity_column}" AS external_humidity,
                "{s.battery_voltage_column}" AS battery_voltage
            FROM {s.qualified_table}
            WHERE "{s.hive_column}"::text = :hive
              AND "{s.timestamp_column}" IS NOT NULL
              AND "{s.temperature_column}" IS NOT NULL
              AND "{s.humidity_column}" IS NOT NULL
              AND "{s.co2_column}" IS NOT NULL
              AND "{s.weight_column}" IS NOT NULL
              AND "{s.external_temperature_column}" IS NOT NULL
              AND "{s.external_humidity_column}" IS NOT NULL
            ORDER BY "{s.timestamp_column}" DESC
            LIMIT 1
            """
        )
        try:
            with self.engine.connect() as connection:
                frame = pd.read_sql_query(query, connection, params={"hive": hive})
        except SQLAlchemyError as exc:
            raise IoTDatabaseError(
                f"Unable to load latest IoT reading for hive {hive!r}: {exc}"
            ) from exc

        frame = self._clean_frame(frame)
        if frame.empty:
            return None

        latest = frame.iloc[-1]
        return {
            "hive": str(latest["hive"]),
            "timestamp": pd.Timestamp(latest["timestamp"]).isoformat(),
            "recorded_at": pd.Timestamp(latest["timestamp"]).isoformat(),
            "reading_at": self._timestamp_or_none(latest.get("reading_at")),
            "temp": float(latest["temp"]),
            "humidity": float(latest["humidity"]),
            "co2": float(latest["co2"]),
            "weight": float(latest["weight"]),
            "external_temp": self._float_or_none(latest.get("external_temp")),
            "external_humidity": self._float_or_none(latest.get("external_humidity")),
            "battery_voltage": self._float_or_none(latest.get("battery_voltage")),
            "data_source": "postgresql_iot",
        }

    def _clean_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return frame

        frame = frame.copy()
        frame["timestamp"] = self._normalise_timestamps(frame["timestamp"])
        if "reading_at" in frame.columns:
            frame["reading_at"] = self._normalise_timestamps(frame["reading_at"])

        numeric_columns = [
            "temp",
            "humidity",
            "co2",
            "weight",
            "external_temp",
            "external_humidity",
            "battery_voltage",
        ]
        for column in numeric_columns:
            if column in frame.columns:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")

        frame = frame.dropna(
            subset=[
                "hive",
                "timestamp",
                "temp",
                "humidity",
                "co2",
                "weight",
                "external_temp",
                "external_humidity",
            ]
        )
        frame = frame.sort_values("timestamp").drop_duplicates(
            ["hive", "timestamp"], keep="last"
        )
        return frame.reset_index(drop=True)

    def _normalise_timestamps(self, values: pd.Series) -> pd.Series:
        if self.settings.timestamps_are_utc:
            parsed = pd.to_datetime(values, errors="coerce", utc=True)
        else:
            parsed = pd.to_datetime(values, errors="coerce")
            if getattr(parsed.dt, "tz", None) is None:
                parsed = parsed.dt.tz_localize(
                    self.settings.feature_timezone,
                    ambiguous="NaT",
                    nonexistent="shift_forward",
                )
        if getattr(parsed.dt, "tz", None) is not None:
            parsed = parsed.dt.tz_convert(self.settings.feature_timezone)
        return parsed

    def _normalise_single_timestamp(self, value: Any) -> str | None:
        series = pd.Series([value])
        parsed = self._normalise_timestamps(series).iloc[0]
        return None if pd.isna(parsed) else pd.Timestamp(parsed).isoformat()

    @staticmethod
    def _timestamp_or_none(value: Any) -> str | None:
        return None if value is None or pd.isna(value) else pd.Timestamp(value).isoformat()

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        return None if value is None or pd.isna(value) else float(value)