from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
import pandas as pd

EPS = 1e-9

CRITICAL_UPPER_BOUND = 40.0
POOR_UPPER_BOUND = 60.0
GOOD_UPPER_BOUND = 80.0

HEALTH_LEVEL_DEFINITIONS = (
    {
        "level": "Critical",
        "display_range": "0-39",
        "rule": "0 <= score < 40",
        "minimum": 0.0,
        "maximum": CRITICAL_UPPER_BOUND,
        "maximum_inclusive": False,
    },
    {
        "level": "Poor",
        "display_range": "40-59",
        "rule": "40 <= score < 60",
        "minimum": CRITICAL_UPPER_BOUND,
        "maximum": POOR_UPPER_BOUND,
        "maximum_inclusive": False,
    },
    {
        "level": "Good",
        "display_range": "60-79",
        "rule": "60 <= score < 80",
        "minimum": POOR_UPPER_BOUND,
        "maximum": GOOD_UPPER_BOUND,
        "maximum_inclusive": False,
    },
    {
        "level": "Excellent",
        "display_range": "80-100",
        "rule": "80 <= score <= 100",
        "minimum": GOOD_UPPER_BOUND,
        "maximum": 100.0,
        "maximum_inclusive": True,
    },
)

@dataclass(frozen=True)
class BroodHealthConfig:
    baseline_window: str = "7D"
    baseline_min_periods: int = 24
    stability_window: str = "6h"
    stability_min_periods: int = 3
    rod_window_hours: float = 4.0
    bhsi_reference_cov: float = 0.10
    temperature_cold_multiplier: float = 2.0
    penalty_denominator: float = 4.5


DEFAULT_WEIGHTS: Mapping[str, float] = {
    "temperature": 0.40,
    "humidity": 0.25,
    "co2": 0.20,
    "weight": 0.15,
}

COLUMN_ALIASES = {
    # Historical training CSV
    "hive_id": "hive",
    "internal_temperature_c": "temp",
    "internal_humidity_pct": "humidity",
    "co2_ppm": "co2",
    "hive_weight_kg": "weight",
    "external_temperature_c": "external_temp",
    "external_humidity_pct": "external_humidity",
    # Supabase IoT table
    "device_id": "hive",
    "recorded_at": "timestamp",
    "internal_temp": "temp",
    "internal_humidity": "humidity",
    "internal_co2": "co2",
    "total_weight": "weight",
}

REQUIRED_COLUMNS = ("hive", "timestamp", "temp", "humidity", "co2", "weight")
OPTIONAL_NUMERIC_COLUMNS = (
    "external_temp",
    "external_humidity",
    "battery_voltage",
)


def _validate_weights(weights: Mapping[str, float]) -> dict[str, float]:
    required = set(DEFAULT_WEIGHTS)
    if set(weights) != required:
        raise ValueError(f"weights must contain exactly {sorted(required)}")

    values = np.asarray(list(weights.values()), dtype=float)
    if np.any(~np.isfinite(values)) or np.any(values < 0):
        raise ValueError("weights must be finite and non-negative")
    if not np.isclose(values.sum(), 1.0, atol=1e-6):
        raise ValueError(f"weights must sum to 1.0; received {values.sum():.6f}")
    return {key: float(value) for key, value in weights.items()}


def normalise_input_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename known source columns and validate the internal sensor schema."""
    out = df.rename(columns=COLUMN_ALIASES).copy()
    missing = [column for column in REQUIRED_COLUMNS if column not in out.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    for column in ("temp", "humidity", "co2", "weight", *OPTIONAL_NUMERIC_COLUMNS):
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")

    out = out.dropna(subset=list(REQUIRED_COLUMNS))
    out = out.sort_values(["hive", "timestamp"])
    out = out.drop_duplicates(["hive", "timestamp"], keep="last")
    return out.reset_index(drop=True)


def _rolling_historical_zscore(
    series: pd.Series,
    timestamps: pd.Series,
    *,
    window: str,
    min_periods: int,
) -> pd.Series:
    """Compare each observation with its preceding historical window only."""
    indexed = pd.Series(series.to_numpy(dtype=float), index=pd.DatetimeIndex(timestamps))
    history = indexed.shift(1)
    mean = history.rolling(window, min_periods=min_periods).mean()
    std = history.rolling(window, min_periods=min_periods).std(ddof=0)
    z = (indexed - mean) / std.where(std > EPS)
    return pd.Series(z.fillna(0.0).to_numpy(), index=series.index)


def _exp_penalty(effective_z: np.ndarray, denominator: float) -> np.ndarray:
    return np.clip(100.0 * np.exp(-(effective_z**2) / denominator), 0.0, 100.0)


def _compute_subscores(frame: pd.DataFrame, config: BroodHealthConfig) -> pd.DataFrame:
    z_temp = frame["z_temp"].to_numpy(dtype=float)
    z_hum = frame["z_humidity"].to_numpy(dtype=float)
    z_co2 = frame["z_co2"].to_numpy(dtype=float)
    z_weight = frame["z_weight"].to_numpy(dtype=float)

    temp_penalty = np.abs(z_temp) * np.where(
        z_temp < 0,
        config.temperature_cold_multiplier,
        1.0,
    )
    frame["temperature_subscore"] = _exp_penalty(
        temp_penalty, config.penalty_denominator
    )
    frame["humidity_subscore"] = _exp_penalty(
        np.abs(z_hum), config.penalty_denominator
    )
    frame["co2_subscore"] = _exp_penalty(
        np.maximum(z_co2, 0.0), config.penalty_denominator
    )
    frame["weight_subscore"] = _exp_penalty(
        np.maximum(-z_weight, 0.0), config.penalty_denominator
    )
    return frame


def _compute_bhsi_for_hive(group: pd.DataFrame, config: BroodHealthConfig) -> pd.Series:
    """Measure stability of the internal brood environment over six hours.

    External weather is deliberately not included in BHSI. BHSI measures how
    consistently the colony maintains its *internal* brood environment despite
    external conditions. External temperature and humidity are used by the
    predictive model as contextual features.
    """
    timestamps = pd.DatetimeIndex(group["timestamp"])
    temp_kelvin = pd.Series(group["temp"].to_numpy() + 273.15, index=timestamps)
    humidity = pd.Series(group["humidity"].to_numpy(), index=timestamps)
    co2 = pd.Series(group["co2"].to_numpy(), index=timestamps)

    def rolling_cov(series: pd.Series) -> pd.Series:
        rolling = series.rolling(
            config.stability_window,
            min_periods=config.stability_min_periods,
        )
        return rolling.std(ddof=0) / rolling.mean().abs().clip(lower=EPS)

    average_cov = (
        rolling_cov(temp_kelvin) + rolling_cov(humidity) + rolling_cov(co2)
    ) / 3.0
    bhsi = 100.0 * (1.0 - average_cov / config.bhsi_reference_cov)
    values = bhsi.clip(0.0, 100.0).fillna(50.0).to_numpy()
    return pd.Series(values, index=group.index)


def _rolling_slope_points_per_hour(
    values: np.ndarray,
    timestamps: pd.DatetimeIndex,
    window_hours: float,
) -> np.ndarray:
    output = np.zeros(len(values), dtype=float)
    left = 0

    for right in range(len(values)):
        cutoff = timestamps[right] - pd.Timedelta(hours=window_hours)
        while left < right and timestamps[left] < cutoff:
            left += 1

        y = values[left : right + 1]
        if len(y) < 2:
            output[right] = 0.0
            continue

        x = (
            timestamps[left : right + 1] - timestamps[left]
        ).total_seconds() / 3600.0
        x = np.asarray(x, dtype=float)
        x_centered = x - x.mean()
        denominator = float(np.dot(x_centered, x_centered))
        output[right] = (
            0.0
            if denominator <= EPS
            else float(np.dot(x_centered, y - y.mean()) / denominator)
        )
    return output


def classify_health(score: float) -> str:
    value = float(score)
    if not np.isfinite(value):
        raise ValueError("health score must be finite")
    if value < CRITICAL_UPPER_BOUND:
        return "Critical"
    if value < POOR_UPPER_BOUND:
        return "Poor"
    if value < GOOD_UPPER_BOUND:
        return "Good"
    return "Excellent"


def classify_stability(score: float) -> str:
    if score >= 70.0:
        return "High"
    if score >= 40.0:
        return "Moderate"
    return "Low"


def classify_trend(slope: float) -> str:
    if slope > 3.0:
        return "Rapid Improving"
    if slope > 0.5:
        return "Slow Improving"
    if slope >= -0.5:
        return "Stable"
    if slope >= -3.0:
        return "Slow Declining"
    return "Rapid Declining"


def build_early_warning(
    *,
    predicted_score: float,
    current_score: float,
    bhsi: float,
    rod: float,
) -> dict[str, Any]:
    """Combine forecast health, stability and trend into one early-warning status.

    The final early-warning status uses the same four classes as the
    Brood Health Score:

    Excellent -> normal condition
    Good      -> monitor condition
    Poor      -> warning condition
    Critical  -> immediate intervention condition

    BHSI and RoD may lower the overall status before the current health
    score becomes poor or critical.
    """

    status_severity = {
        "Excellent": 0,
        "Good": 1,
        "Poor": 2,
        "Critical": 3,
    }

    severity_status = {
        0: "Excellent",
        1: "Good",
        2: "Poor",
        3: "Critical",
    }

    predicted_level = classify_health(predicted_score)
    current_level = classify_health(current_score)

    severity = status_severity[predicted_level]
    reasons: list[str] = []

    # Future model forecast
    if predicted_level == "Critical":
        reasons.append(
            "The model forecasts critical brood-health conditions "
            "within the prediction horizon."
        )
    elif predicted_level == "Poor":
        reasons.append(
            "The model forecasts poor brood-health conditions "
            "within the prediction horizon."
        )
    elif predicted_level == "Good":
        reasons.append(
            "The model forecasts generally good brood health, "
            "but continued monitoring is recommended."
        )

    # Current health condition
    severity = max(
        severity,
        status_severity[current_level],
    )

    if current_level == "Critical":
        reasons.append(
            "The current Brood Health Score is already critical."
        )
    elif current_level == "Poor":
        reasons.append(
            "The current Brood Health Score is poor."
        )

    # BHSI early-warning escalation
    if bhsi < 40.0:
        severity = max(severity, 2)

        reasons.append(
            "BHSI indicates low internal environmental stability."
        )

    elif bhsi < 70.0:
        severity = max(severity, 1)

        reasons.append(
            "BHSI indicates moderate internal environmental stability."
        )

    # RoD early-warning escalation
    if rod < -3.0:
        severity = 3

        reasons.append(
            "RoD indicates rapid deterioration in brood-health conditions."
        )

    elif rod < -0.5:
        severity = max(severity, 2)

        reasons.append(
            "RoD indicates a continuing decline in brood-health conditions."
        )

    final_status = severity_status[severity]

    actions = {
        "Excellent": (
            "Conditions are stable. Continue routine monitoring."
        ),
        "Good": (
            "Continue monitoring the next sensor readings and check "
            "for developing instability."
        ),
        "Poor": (
            "Inspect the hive soon and correct abnormal temperature, "
            "humidity, ventilation or food conditions."
        ),
        "Critical": (
            "Immediate physical inspection is recommended to prevent "
            "brood deterioration or failure."
        ),
    }

    if not reasons:
        reasons.append(
            "The predicted score, BHSI and RoD are currently within "
            "acceptable ranges."
        )

    return {
        "level": final_status,
        "predicted_health_level": predicted_level,
        "current_health_level": current_level,
        "is_alert": severity >= 2,
        "is_critical": severity == 3,
        "reasons": reasons,
        "recommended_action": actions[final_status],
    }


def compute_brood_health_metrics(
    df: pd.DataFrame,
    *,
    weights: Mapping[str, float] | None = None,
    config: BroodHealthConfig | None = None,
    include_debug_columns: bool = False,
) -> pd.DataFrame:
    """Compute current score, BHSI and RoD at the source sampling frequency."""
    config = config or BroodHealthConfig()
    weights = _validate_weights(weights or DEFAULT_WEIGHTS)
    frame = normalise_input_columns(df)

    for sensor, output_name in (
        ("temp", "z_temp"),
        ("humidity", "z_humidity"),
        ("co2", "z_co2"),
        ("weight", "z_weight"),
    ):
        frame[output_name] = 0.0
        for _, group in frame.groupby("hive", sort=False):
            frame.loc[group.index, output_name] = _rolling_historical_zscore(
                group[sensor],
                group["timestamp"],
                window=config.baseline_window,
                min_periods=config.baseline_min_periods,
            ).to_numpy()

    frame = _compute_subscores(frame, config)
    frame["brood_health_score"] = (
        weights["temperature"] * frame["temperature_subscore"]
        + weights["humidity"] * frame["humidity_subscore"]
        + weights["co2"] * frame["co2_subscore"]
        + weights["weight"] * frame["weight_subscore"]
    ).clip(0.0, 100.0)

    frame["bhsi"] = 50.0
    for _, group in frame.groupby("hive", sort=False):
        frame.loc[group.index, "bhsi"] = _compute_bhsi_for_hive(
            group, config
        ).to_numpy()

    frame["rod"] = 0.0
    for _, group in frame.groupby("hive", sort=False):
        frame.loc[group.index, "rod"] = _rolling_slope_points_per_hour(
            group["brood_health_score"].to_numpy(dtype=float),
            pd.DatetimeIndex(group["timestamp"]),
            config.rod_window_hours,
        )

    frame["brood_health_score"] = frame["brood_health_score"].round(2)
    frame["bhsi"] = frame["bhsi"].round(2)
    frame["rod"] = frame["rod"].round(3)
    frame["health_level"] = frame["brood_health_score"].map(classify_health)
    level_lookup = {item["level"]: item for item in HEALTH_LEVEL_DEFINITIONS}
    frame["health_range"] = frame["health_level"].map(
        lambda level: level_lookup[level]["display_range"]
    )
    frame["health_rule"] = frame["health_level"].map(
        lambda level: level_lookup[level]["rule"]
    )
    frame["stability_level"] = frame["bhsi"].map(classify_stability)
    frame["trend_label"] = frame["rod"].map(classify_trend)
    frame["score_method"] = "research_prior_relative_v3"

    base_columns = [
        "hive",
        "timestamp",
        "temp",
        "humidity",
        "co2",
        "weight",
    ]
    base_columns.extend(
        column for column in OPTIONAL_NUMERIC_COLUMNS if column in frame.columns
    )
    base_columns.extend(
        [
            "brood_health_score",
            "bhsi",
            "rod",
            "health_level",
            "health_range",
            "health_rule",
            "stability_level",
            "trend_label",
            "score_method",
        ]
    )

    if include_debug_columns:
        base_columns.extend(
            [
                "z_temp",
                "z_humidity",
                "z_co2",
                "z_weight",
                "temperature_subscore",
                "humidity_subscore",
                "co2_subscore",
                "weight_subscore",
            ]
        )
    return frame[base_columns]