"""Shared feature engineering for historical training and live IoT prediction.

Both the historical classifier-training script and the live prediction service
must import this module. This prevents training/serving feature mismatch.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


CANONICAL_SENSOR_COLUMNS = [
    "internal_temperature_c",
    "internal_humidity_pct",
    "co2_ppm",
    "hive_weight_kg",
    "external_temperature_c",
    "external_humidity_pct",
    "battery_voltage",
]

HARVEST_CLASSIFIER_FEATURES = [
    "internal_temperature_c",
    "internal_humidity_pct",
    "co2_ppm",
    "hive_weight_kg",
    "external_temperature_c",
    "external_humidity_pct",

    "weight_change_1h_kg",
    "weight_change_24h_kg",
    "weight_change_72h_kg",
    "weight_mean_24h_kg",
    "weight_mean_72h_kg",
    "weight_std_24h_kg",
    "weight_std_72h_kg",
    "weight_slope_24h_kg_per_hour",
    "distance_from_7day_max_kg",

    "internal_temperature_mean_24h",
    "internal_temperature_std_24h",
    "internal_humidity_mean_24h",
    "internal_humidity_std_24h",
    "co2_mean_24h",
    "co2_std_24h",
    "co2_change_24h",

    "internal_external_temperature_diff",
    "internal_external_humidity_diff",

    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
    "month_sin",
    "month_cos",
]


@dataclass(frozen=True)
class FeatureEngineeringConfig:
    feature_timezone: str = "Asia/Colombo"
    timestamps_are_utc: bool = True
    source_timezone: str = "UTC"
    interpolation_limit_hours: int = 3
    resample_frequency: str = "1h"


def _ensure_columns(df: pd.DataFrame, required: Iterable[str]) -> None:
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def parse_timestamps(
    series: pd.Series,
    *,
    timestamps_are_utc: bool,
    source_timezone: str,
) -> pd.Series:
    """Return timezone-aware UTC timestamps."""
    if timestamps_are_utc:
        return pd.to_datetime(series, errors="coerce", utc=True)

    parsed = pd.to_datetime(series, errors="coerce")

    if parsed.dt.tz is None:
        parsed = parsed.dt.tz_localize(
            source_timezone,
            ambiguous="NaT",
            nonexistent="shift_forward",
        )

    return parsed.dt.tz_convert("UTC")


def canonicalize_historical_data(
    df: pd.DataFrame,
    *,
    config: FeatureEngineeringConfig,
) -> pd.DataFrame:
    """Normalize the historical dataset to the project column names."""
    data = df.copy()
    _ensure_columns(data, ["timestamp", "hive_id"])

    data["timestamp"] = parse_timestamps(
        data["timestamp"],
        timestamps_are_utc=config.timestamps_are_utc,
        source_timezone=config.source_timezone,
    )
    data["hive_id"] = data["hive_id"].astype(str)

    for column in CANONICAL_SENSOR_COLUMNS:
        if column not in data.columns:
            data[column] = np.nan
        data[column] = pd.to_numeric(data[column], errors="coerce")

    return data


def canonicalize_live_data(
    df: pd.DataFrame,
    *,
    config: FeatureEngineeringConfig,
) -> pd.DataFrame:
    """Normalize the dataframe returned by iot_data_service.py."""
    data = df.copy()
    _ensure_columns(data, ["timestamp", "hive_id"])

    data["timestamp"] = parse_timestamps(
        data["timestamp"],
        timestamps_are_utc=config.timestamps_are_utc,
        source_timezone=config.source_timezone,
    )
    data["hive_id"] = data["hive_id"].astype(str)

    for column in CANONICAL_SENSOR_COLUMNS:
        if column not in data.columns:
            data[column] = np.nan
        data[column] = pd.to_numeric(data[column], errors="coerce")

    return data


def resample_hourly(
    df: pd.DataFrame,
    *,
    config: FeatureEngineeringConfig,
    aggregation_overrides: dict[str, str] | None = None,
) -> pd.DataFrame:
    """
    Resample every hive to one row per hour.

    Sensor columns use mean aggregation. Pass:
        aggregation_overrides={"harvest": "max"}
    during historical training so an event is retained inside its hour.
    """
    _ensure_columns(df, ["timestamp", "hive_id"])

    aggregation_overrides = aggregation_overrides or {}
    data = df.copy()
    data = data.dropna(subset=["timestamp", "hive_id"])
    data = data.sort_values(["hive_id", "timestamp"])
    data = data.drop_duplicates(["hive_id", "timestamp"], keep="last")

    output_frames: list[pd.DataFrame] = []

    for hive_id, hive_df in data.groupby("hive_id", sort=False):
        hive_df = hive_df.sort_values("timestamp").set_index("timestamp")

        aggregation: dict[str, str] = {}
        for column in hive_df.columns:
            if column == "hive_id":
                continue

            if column in aggregation_overrides:
                aggregation[column] = aggregation_overrides[column]
            elif pd.api.types.is_numeric_dtype(hive_df[column]):
                aggregation[column] = "mean"
            else:
                aggregation[column] = "last"

        if not aggregation:
            continue

        hourly = hive_df.resample(config.resample_frequency).agg(aggregation)

        for column in CANONICAL_SENSOR_COLUMNS:
            if column not in hourly.columns:
                hourly[column] = np.nan

            hourly[f"{column}_was_imputed"] = hourly[column].isna()

        hourly[CANONICAL_SENSOR_COLUMNS] = hourly[
            CANONICAL_SENSOR_COLUMNS
        ].interpolate(
            method="time",
            limit=config.interpolation_limit_hours,
            limit_area="inside",
        )

        hourly["hive_id"] = str(hive_id)
        hourly = hourly.reset_index()
        output_frames.append(hourly)

    if not output_frames:
        return pd.DataFrame(
            columns=["timestamp", "hive_id", *CANONICAL_SENSOR_COLUMNS]
        )

    result = pd.concat(output_frames, ignore_index=True)
    return result.sort_values(
        ["hive_id", "timestamp"]
    ).reset_index(drop=True)


def _rolling_mean(
    grouped: pd.core.groupby.SeriesGroupBy,
    window: int,
) -> pd.Series:
    return (
        grouped.rolling(
            window=window,
            min_periods=max(3, window // 4),
        )
        .mean()
        .reset_index(level=0, drop=True)
    )


def _rolling_std(
    grouped: pd.core.groupby.SeriesGroupBy,
    window: int,
) -> pd.Series:
    return (
        grouped.rolling(
            window=window,
            min_periods=max(3, window // 4),
        )
        .std()
        .reset_index(level=0, drop=True)
    )


def add_live_features(
    df: pd.DataFrame,
    *,
    config: FeatureEngineeringConfig,
) -> pd.DataFrame:
    """Create features from present and past rows only."""
    _ensure_columns(
        df,
        [
            "timestamp",
            "hive_id",
            "internal_temperature_c",
            "internal_humidity_pct",
            "co2_ppm",
            "hive_weight_kg",
            "external_temperature_c",
            "external_humidity_pct",
        ],
    )

    data = df.copy()
    data = data.sort_values(
        ["hive_id", "timestamp"]
    ).reset_index(drop=True)

    group = data.groupby("hive_id", group_keys=False)

    weight_group = group["hive_weight_kg"]
    temperature_group = group["internal_temperature_c"]
    humidity_group = group["internal_humidity_pct"]
    co2_group = group["co2_ppm"]

    data["weight_change_1h_kg"] = weight_group.diff(1)
    data["weight_change_24h_kg"] = weight_group.diff(24)
    data["weight_change_72h_kg"] = weight_group.diff(72)

    data["weight_mean_24h_kg"] = _rolling_mean(
        weight_group,
        24,
    )
    data["weight_mean_72h_kg"] = _rolling_mean(
        weight_group,
        72,
    )
    data["weight_std_24h_kg"] = _rolling_std(
        weight_group,
        24,
    )
    data["weight_std_72h_kg"] = _rolling_std(
        weight_group,
        72,
    )

    data["weight_slope_24h_kg_per_hour"] = (
        data["weight_change_24h_kg"] / 24.0
    )

    rolling_max_7d = (
        weight_group.rolling(
            window=168,
            min_periods=24,
        )
        .max()
        .reset_index(level=0, drop=True)
    )

    data["distance_from_7day_max_kg"] = (
        rolling_max_7d - data["hive_weight_kg"]
    )

    data["internal_temperature_mean_24h"] = _rolling_mean(
        temperature_group,
        24,
    )
    data["internal_temperature_std_24h"] = _rolling_std(
        temperature_group,
        24,
    )
    data["internal_humidity_mean_24h"] = _rolling_mean(
        humidity_group,
        24,
    )
    data["internal_humidity_std_24h"] = _rolling_std(
        humidity_group,
        24,
    )
    data["co2_mean_24h"] = _rolling_mean(
        co2_group,
        24,
    )
    data["co2_std_24h"] = _rolling_std(
        co2_group,
        24,
    )
    data["co2_change_24h"] = co2_group.diff(24)

    data["internal_external_temperature_diff"] = (
        data["internal_temperature_c"]
        - data["external_temperature_c"]
    )
    data["internal_external_humidity_diff"] = (
        data["internal_humidity_pct"]
        - data["external_humidity_pct"]
    )

    local_timestamp = data["timestamp"].dt.tz_convert(
        config.feature_timezone
    )

    hour = local_timestamp.dt.hour
    day_of_week = local_timestamp.dt.dayofweek
    month = local_timestamp.dt.month

    data["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    data["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    data["day_of_week_sin"] = np.sin(
        2 * np.pi * day_of_week / 7
    )
    data["day_of_week_cos"] = np.cos(
        2 * np.pi * day_of_week / 7
    )
    data["month_sin"] = np.sin(
        2 * np.pi * (month - 1) / 12
    )
    data["month_cos"] = np.cos(
        2 * np.pi * (month - 1) / 12
    )

    return data


def latest_complete_feature_rows(
    feature_df: pd.DataFrame,
    *,
    feature_columns: Iterable[str] = HARVEST_CLASSIFIER_FEATURES,
) -> pd.DataFrame:
    feature_columns = list(feature_columns)
    _ensure_columns(
        feature_df,
        ["timestamp", "hive_id", *feature_columns],
    )

    complete = feature_df.dropna(
        subset=feature_columns
    ).copy()

    if complete.empty:
        return complete

    return (
        complete.sort_values(["hive_id", "timestamp"])
        .groupby("hive_id", as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )


def calculate_hourly_completeness(
    df: pd.DataFrame,
) -> float:
    if df.empty:
        return 0.0

    timestamps = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True,
    ).dropna()

    if timestamps.empty:
        return 0.0

    start = timestamps.min().floor("h")
    end = timestamps.max().floor("h")
    expected = int(
        (end - start).total_seconds() // 3600
    ) + 1

    if expected <= 0:
        return 0.0

    observed = timestamps.dt.floor("h").nunique()
    return float(min(1.0, observed / expected))
