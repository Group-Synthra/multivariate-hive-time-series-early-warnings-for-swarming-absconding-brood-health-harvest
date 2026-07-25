"""Causal feature engineering for brood-health forecasting.

Training source
``backend/data/hive_data_with_features.csv``

Live inference source
``public.beehive_readings`` in PostgreSQL/Supabase.

"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

DEFAULT_TARGET = "brood_health_score_0_100"

SENSORS = (
    "temp",
    "humidity",
    "co2",
    "weight",
    "external_temp",
    "external_humidity",
)
INTERNAL_SENSORS = ("temp", "humidity", "co2", "weight")
EXTERNAL_SENSORS = ("external_temp", "external_humidity")
LAG_HOURS = (1, 3, 6, 12, 24)
ROLLING_HOURS = (3, 6, 12, 24)
DIFFERENCE_HOURS = (1, 6, 24)
FEATURE_SCHEMA_VERSION = "brood_features_v3_internal_external"

ALIASES = {
    # Historical training CSV names
    "hive_id": "hive",
    "internal_temperature_c": "temp",
    "internal_humidity_pct": "humidity",
    "co2_ppm": "co2",
    "hive_weight_kg": "weight",
    "external_temperature_c": "external_temp",
    "external_humidity_pct": "external_humidity",
    # Actual Supabase table names
    "device_id": "hive",
    "recorded_at": "timestamp",
    "internal_temp": "temp",
    "internal_humidity": "humidity",
    "internal_co2": "co2",
    "total_weight": "weight",
}


def _prepare_hourly_frame(
    df: pd.DataFrame,
    *,
    target_column: str | None = None,
) -> pd.DataFrame:
    frame = df.rename(columns=ALIASES).copy()
    required = ["hive", "timestamp", *SENSORS]
    if target_column:
        required.append(target_column)

    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(
            "Missing required columns for internal/external feature engineering: "
            f"{missing}"
        )

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    numeric_columns = [*SENSORS]
    if target_column:
        numeric_columns.append(target_column)
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame = frame.dropna(subset=required)
    frame = (
        frame.sort_values(["hive", "timestamp"])
        .drop_duplicates(["hive", "timestamp"], keep="last")
        .reset_index(drop=True)
    )

    hourly_parts: list[pd.DataFrame] = []
    keep_columns = list(SENSORS) + ([target_column] if target_column else [])

    for hive, group in frame.groupby("hive", sort=False):
        group = group.set_index("timestamp")[keep_columns].sort_index()

        hourly_sensors = group[list(SENSORS)].resample("1h").median()
        # Only bridge short outages. Never backfill from future observations.
        hourly_sensors = hourly_sensors.ffill(limit=3)
        hourly = hourly_sensors

        if target_column:
            hourly_target = group[[target_column]].resample("1h").mean()
            hourly = hourly.join(hourly_target, how="left")

        hourly["hive"] = hive
        hourly_parts.append(hourly.reset_index())

    if not hourly_parts:
        raise ValueError("No usable hourly hive records were produced")

    output = pd.concat(hourly_parts, ignore_index=True)
    return (
        output.dropna(subset=required)
        .sort_values(["hive", "timestamp"])
        .reset_index(drop=True)
    )


def _series_feature_dict(prefix: str, values: pd.Series) -> dict[str, pd.Series]:
    output: dict[str, pd.Series] = {prefix: values}

    for lag in LAG_HOURS:
        output[f"{prefix}_lag_{lag}h"] = values.shift(lag)

    for window in ROLLING_HOURS:
        rolling = values.rolling(window=window, min_periods=max(2, window // 2))
        output[f"{prefix}_mean_{window}h"] = rolling.mean()
        output[f"{prefix}_std_{window}h"] = rolling.std(ddof=0)

    for difference in DIFFERENCE_HOURS:
        output[f"{prefix}_change_{difference}h"] = values.diff(difference)
    return output


def _build_features_for_group(group: pd.DataFrame) -> pd.DataFrame:
    group = group.sort_values("timestamp").copy()
    feature_columns: dict[str, pd.Series | np.ndarray] = {}

    for sensor in SENSORS:
        feature_columns.update(
            _series_feature_dict(sensor, group[sensor].astype(float))
        )

    temp_difference = group["temp"].astype(float) - group["external_temp"].astype(float)
    humidity_difference = (
        group["humidity"].astype(float) - group["external_humidity"].astype(float)
    )
    feature_columns.update(
        _series_feature_dict("internal_external_temp_delta", temp_difference)
    )
    feature_columns.update(
        _series_feature_dict(
            "internal_external_humidity_delta",
            humidity_difference,
        )
    )

    feature_columns["external_heat_stress_above_35"] = np.maximum(
        group["external_temp"].astype(float) - 35.0,
        0.0,
    )
    feature_columns["external_cold_stress_below_20"] = np.maximum(
        20.0 - group["external_temp"].astype(float),
        0.0,
    )
    feature_columns["external_humidity_extreme"] = np.minimum(
        np.abs(group["external_humidity"].astype(float) - 60.0),
        60.0,
    )

    hour = group["timestamp"].dt.hour.astype(float)
    day_of_year = group["timestamp"].dt.dayofyear.astype(float)
    feature_columns["hour_sin"] = np.sin(2.0 * np.pi * hour / 24.0)
    feature_columns["hour_cos"] = np.cos(2.0 * np.pi * hour / 24.0)
    feature_columns["day_of_year_sin"] = np.sin(2.0 * np.pi * day_of_year / 365.25)
    feature_columns["day_of_year_cos"] = np.cos(2.0 * np.pi * day_of_year / 365.25)
    feature_columns["is_night"] = ((hour < 6) | (hour >= 19)).astype(int)
    return pd.DataFrame(feature_columns, index=group.index)


def count_hourly_observations(df: pd.DataFrame) -> int:
    try:
        frame = _prepare_hourly_frame(df)
    except ValueError:
        return 0
    return int(len(frame))


def build_supervised_dataset(
    df: pd.DataFrame,
    *,
    target_column: str = DEFAULT_TARGET,
    horizon_hours: int = 6,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, list[str]]:
    if horizon_hours < 1:
        raise ValueError("horizon_hours must be positive")

    frame = _prepare_hourly_frame(df, target_column=target_column)
    feature_parts: list[pd.DataFrame] = []
    target_parts: list[pd.Series] = []
    metadata_parts: list[pd.DataFrame] = []

    for hive, group in frame.groupby("hive", sort=False):
        group = group.sort_values("timestamp").copy()
        features = _build_features_for_group(group)
        target = group[target_column].shift(-horizon_hours).rename("target")
        target_timestamp = group["timestamp"].shift(-horizon_hours)
        metadata = pd.DataFrame(
            {
                "hive": hive,
                "timestamp": group["timestamp"],
                "target_timestamp": target_timestamp,
            },
            index=group.index,
        )
        valid = features.notna().all(axis=1) & target.notna() & target_timestamp.notna()
        feature_parts.append(features.loc[valid])
        target_parts.append(target.loc[valid])
        metadata_parts.append(metadata.loc[valid])

    if not feature_parts:
        raise ValueError("No training features were generated")

    X = pd.concat(feature_parts, ignore_index=True)
    y = pd.concat(target_parts, ignore_index=True).astype(float)
    metadata = pd.concat(metadata_parts, ignore_index=True)
    if X.empty:
        raise ValueError("No training rows remained after causal lag construction")
    return X, y, metadata, X.columns.tolist()


def build_latest_feature_row(
    readings: pd.DataFrame,
    *,
    expected_features: Iterable[str],
) -> tuple[pd.DataFrame, pd.Timestamp, str]:
    frame = _prepare_hourly_frame(readings)
    hives = frame["hive"].astype(str).unique()
    if len(hives) != 1:
        raise ValueError("Prediction history must contain readings from exactly one hive")
    if len(frame) < max(LAG_HOURS) + 1:
        raise ValueError(
            f"At least {max(LAG_HOURS) + 1} hourly readings are required; "
            f"received {len(frame)}"
        )

    feature_frame = _build_features_for_group(frame)
    latest = feature_frame.iloc[[-1]].copy()
    expected = list(expected_features)
    missing = [column for column in expected if column not in latest.columns]
    if missing:
        raise ValueError(
            "The saved model was trained with a different feature schema. "
            "Retrain the models after installing the internal/external feature code. "
            f"Unavailable features: {missing}"
        )

    latest = latest.reindex(columns=expected)
    if latest.isna().any(axis=None):
        missing_values = latest.columns[latest.isna().any()].tolist()
        raise ValueError(f"Insufficient history for features: {missing_values}")

    timestamp = pd.Timestamp(frame.iloc[-1]["timestamp"])
    return latest, timestamp, str(hives[0])