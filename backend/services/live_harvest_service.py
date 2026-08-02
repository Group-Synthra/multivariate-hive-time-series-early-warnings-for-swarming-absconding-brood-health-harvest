"""Probability-based live honey-harvest prediction service."""

from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"

for path in [str(PROJECT_ROOT), str(BACKEND_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)

from harvest.live_feature_engineering import (  # noqa: E402
    FeatureEngineeringConfig,
    HARVEST_CLASSIFIER_FEATURES,
    add_live_features,
    calculate_hourly_completeness,
    canonicalize_live_data,
    latest_complete_feature_rows,
    resample_hourly,
)
from services.harvest_prediction_history_service import (  # noqa: E402
    detect_sustained_harvest_window,
    get_prediction_history,
    save_prediction,
)
from services.iot_data_service import (  # noqa: E402
    check_database_health,
    get_available_devices,
    get_latest_reading,
    get_recent_readings,
)


load_dotenv(PROJECT_ROOT / ".env")

MODEL_DIR = BACKEND_DIR / "models"

CALIBRATED_MODEL_FILE = (
    MODEL_DIR
    / "calibrated_harvest_classifier.joblib"
)
ENSEMBLE_FILE = (
    MODEL_DIR
    / "harvest_classifier_ensemble.joblib"
)
FEATURE_FILE = (
    MODEL_DIR
    / "harvest_classifier_features.joblib"
)
METADATA_FILE = (
    MODEL_DIR
    / "harvest_classifier_metadata.json"
)

DEFAULT_HISTORY_HOURS = int(
    os.getenv("IOT_HISTORY_HOURS", "168")
)
MINIMUM_HISTORY_HOURS = int(
    os.getenv("IOT_MIN_HISTORY_HOURS", "72")
)
STALE_AFTER_MINUTES = int(
    os.getenv("IOT_STALE_AFTER_MINUTES", "120")
)
MINIMUM_COMPLETENESS = float(
    os.getenv("IOT_MIN_COMPLETENESS", "0.80")
)
FEATURE_TIMEZONE = os.getenv(
    "IOT_FEATURE_TIMEZONE",
    "Asia/Colombo",
)
TIMESTAMPS_ARE_UTC = (
    os.getenv(
        "IOT_TIMESTAMPS_ARE_UTC",
        "true",
    ).lower()
    == "true"
)
INTERPOLATION_LIMIT_HOURS = int(
    os.getenv(
        "IOT_INTERPOLATION_LIMIT_HOURS",
        "3",
    )
)
LOW_BATTERY_VOLTAGE = float(
    os.getenv(
        "IOT_LOW_BATTERY_VOLTAGE",
        "3.4",
    )
)

CONFIG = FeatureEngineeringConfig(
    feature_timezone=FEATURE_TIMEZONE,
    timestamps_are_utc=TIMESTAMPS_ARE_UTC,
    source_timezone="UTC",
    interpolation_limit_hours=(
        INTERPOLATION_LIMIT_HOURS
    ),
)


@lru_cache(maxsize=1)
def load_classifier_artifacts():
    required = [
        CALIBRATED_MODEL_FILE,
        FEATURE_FILE,
        METADATA_FILE,
    ]
    missing = [
        path
        for path in required
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Classifier artifacts are missing: "
            + ", ".join(str(path) for path in missing)
            + ". Run python backend/ml/"
            "train_harvest_classifier.py first."
        )

    model = joblib.load(
        CALIBRATED_MODEL_FILE
    )
    features = joblib.load(
        FEATURE_FILE
    )

    if hasattr(features, "tolist"):
        features = features.tolist()

    ensemble = {}
    if ENSEMBLE_FILE.exists():
        ensemble = joblib.load(
            ENSEMBLE_FILE
        )

    with METADATA_FILE.open(
        "r",
        encoding="utf-8",
    ) as handle:
        metadata = json.load(handle)

    return (
        model,
        list(features),
        ensemble,
        metadata,
    )


def _safe_float(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), 4)


def _history_span_hours(
    frame: pd.DataFrame,
) -> float:
    timestamps = pd.to_datetime(
        frame.get("timestamp"),
        errors="coerce",
        utc=True,
    ).dropna()

    if timestamps.empty:
        return 0.0

    return float(
        (
            timestamps.max()
            - timestamps.min()
        ).total_seconds()
        / 3600
    )


def _latest_timestamp(
    frame: pd.DataFrame,
) -> pd.Timestamp | None:
    timestamps = pd.to_datetime(
        frame.get("timestamp"),
        errors="coerce",
        utc=True,
    ).dropna()

    if timestamps.empty:
        return None

    return timestamps.max()


def _staleness_minutes(
    timestamp: pd.Timestamp | None,
) -> float | None:
    if timestamp is None:
        return None

    return max(
        0.0,
        float(
            (
                pd.Timestamp.now(tz="UTC")
                - timestamp
            ).total_seconds()
            / 60
        ),
    )


def _horizon_description(
    horizon_hours: int,
) -> str:
    if horizon_hours % 24 == 0:
        days = horizon_hours // 24
        unit = "day" if days == 1 else "days"
        return (
            f"Harvest within the next "
            f"{days} {unit}"
        )

    return (
        f"Harvest within the next "
        f"{horizon_hours} hours"
    )


def _recommendation_for_horizon(
    status: str,
    horizon_hours: int,
) -> str:
    if horizon_hours % 24 == 0:
        horizon_text = (
            f"{horizon_hours // 24} days"
        )
    else:
        horizon_text = (
            f"{horizon_hours} hours"
        )

    if status == "Not Ready":
        return "Continue monitoring the hive."

    if status == "Developing":
        return (
            "Honey stores appear to be "
            "developing. Continue routine "
            "monitoring."
        )

    if status == "Approaching Harvest":
        return (
            "Inspect the hive soon and review "
            "the trend before deciding."
        )

    if status == "Ready":
        return (
            "Inspect the hive and plan "
            f"harvesting within the next "
            f"{horizon_text}."
        )

    return (
        "Inspect the hive as soon as practical "
        "and harvest when field inspection "
        "confirms readiness."
    )


def readiness_status(
    hui: float,
) -> str:
    if hui < 30:
        return "Not Ready"
    if hui < 50:
        return "Developing"
    if hui < 70:
        return "Approaching Harvest"
    if hui < 85:
        return "Ready"
    return "High-Priority Harvest"


def recommendation_for_status(
    status: str,
) -> str:
    return {
        "Not Ready": (
            "Continue monitoring the hive."
        ),
        "Developing": (
            "Honey stores appear to be "
            "developing. Continue routine "
            "monitoring."
        ),
        "Approaching Harvest": (
            "Inspect the hive within the "
            "next two days."
        ),
        "Ready": (
            "Plan harvesting within the "
            "next three days."
        ),
        "High-Priority Harvest": (
            "Inspect and harvest as soon "
            "as practical."
        ),
    }[status]


def _out_of_distribution_warnings(
    row: pd.Series,
    metadata: dict,
    features: list[str],
) -> list[str]:
    ranges = metadata.get(
        "training_feature_ranges",
        {},
    )
    warnings = []

    for feature in features:
        value = row.get(feature)

        if pd.isna(value):
            continue

        limits = ranges.get(feature, {})
        low = limits.get("p01")
        high = limits.get("p99")

        if (
            low is not None
            and float(value) < float(low)
        ):
            warnings.append(
                f"{feature} is below the "
                "historical training range."
            )
        elif (
            high is not None
            and float(value) > float(high)
        ):
            warnings.append(
                f"{feature} is above the "
                "historical training range."
            )

    return warnings[:8]


def _confidence_level(
    *,
    probabilities: list[float],
    completeness: float,
    stale: bool,
    out_of_distribution_count: int,
) -> str:
    disagreement = (
        float(np.std(probabilities))
        if len(probabilities) > 1
        else 0.0
    )

    if (
        completeness >= 0.90
        and not stale
        and out_of_distribution_count == 0
        and disagreement <= 0.08
    ):
        return "High"

    if (
        completeness >= 0.75
        and not stale
        and disagreement <= 0.15
    ):
        return "Medium"

    return "Low"


def _environmental_suitability(
    row: pd.Series,
    metadata: dict,
) -> dict:
    ranges = metadata.get(
        "positive_environment_ranges",
        {},
    )

    fields = {
        "internal_temperature": (
            "internal_temperature_mean_24h"
        ),
        "internal_humidity": (
            "internal_humidity_mean_24h"
        ),
        "external_temperature": (
            "external_temperature_c"
        ),
        "external_humidity": (
            "external_humidity_pct"
        ),
    }

    statuses = {}

    for output_name, feature in fields.items():
        value = row.get(feature)
        limits = ranges.get(feature)

        if (
            limits is None
            or pd.isna(value)
        ):
            statuses[output_name] = (
                "Unavailable"
            )
            continue

        low = float(limits["p10"])
        high = float(limits["p90"])
        value = float(value)

        if low <= value <= high:
            statuses[output_name] = "Suitable"
        elif (
            low - abs(high - low) * 0.25
            <= value
            <= high + abs(high - low) * 0.25
        ):
            statuses[output_name] = (
                "Moderately Suitable"
            )
        else:
            statuses[output_name] = "Unsuitable"

    available = [
        value
        for value in statuses.values()
        if value != "Unavailable"
    ]

    if not available:
        overall = "Unavailable"
    elif "Unsuitable" in available:
        overall = "Unsuitable"
    elif "Moderately Suitable" in available:
        overall = "Moderately Suitable"
    else:
        overall = "Suitable"

    return {
        "status": overall,
        **statuses,
        "basis": (
            "Compared with environmental "
            "ranges observed in historical "
            "pre-harvest rows."
        ),
        "limitation": (
            "The model was trained using "
            "historical data and is not yet "
            "locally calibrated with confirmed "
            "Sri Lankan harvest events."
        ),
    }


def _plain_language_reasons(
    row: pd.Series,
    metadata: dict,
) -> list[str]:
    top_features = [
        item["feature"]
        for item in metadata.get(
            "top_features",
            [],
        )[:10]
    ]
    patterns = metadata.get(
        "feature_pattern_summary",
        {},
    )

    messages = {
        "weight_change_72h_kg": (
            lambda value: (
                f"Hive weight changed by "
                f"{value:.2f} kg during the "
                "previous 72 hours."
            )
        ),
        "weight_change_24h_kg": (
            lambda value: (
                f"Hive weight changed by "
                f"{value:.2f} kg during the "
                "previous 24 hours."
            )
        ),
        "distance_from_7day_max_kg": (
            lambda value: (
                f"Current weight is "
                f"{value:.2f} kg below its "
                "seven-day maximum."
            )
        ),
        "weight_std_24h_kg": (
            lambda value: (
                f"The 24-hour weight "
                f"variability is "
                f"{value:.2f} kg."
            )
        ),
        "internal_temperature_mean_24h": (
            lambda value: (
                f"Mean internal temperature "
                f"during the previous 24 hours "
                f"is {value:.2f} °C."
            )
        ),
        "internal_humidity_mean_24h": (
            lambda value: (
                f"Mean internal humidity "
                f"during the previous 24 hours "
                f"is {value:.2f}%."
            )
        ),
        "co2_mean_24h": (
            lambda value: (
                f"Mean internal CO₂ during "
                f"the previous 24 hours is "
                f"{value:.0f} ppm."
            )
        ),
    }

    reasons = []

    for feature in top_features:
        value = row.get(feature)

        if (
            feature not in messages
            or pd.isna(value)
        ):
            continue

        pattern = patterns.get(feature, {})
        positive_median = pattern.get(
            "positive_median"
        )
        negative_median = pattern.get(
            "negative_median"
        )

        relationship = ""
        if (
            positive_median is not None
            and negative_median is not None
        ):
            distance_to_positive = abs(
                float(value)
                - float(positive_median)
            )
            distance_to_negative = abs(
                float(value)
                - float(negative_median)
            )

            if (
                distance_to_positive
                < distance_to_negative
            ):
                relationship = (
                    " This is closer to the "
                    "pattern observed before "
                    "historical harvest events."
                )
            else:
                relationship = (
                    " This is closer to the "
                    "non-harvest historical "
                    "pattern."
                )

        reasons.append(
            messages[feature](float(value))
            + relationship
        )

        if len(reasons) == 4:
            break

    if not reasons:
        reasons.append(
            "The recommendation is based on "
            "the combined live sensor pattern "
            "processed by the selected "
            "classifier."
        )

    return reasons


def get_live_health() -> dict:
    database = check_database_health()

    return {
        **database,
        "classifier_ready": (
            CALIBRATED_MODEL_FILE.exists()
            and FEATURE_FILE.exists()
            and METADATA_FILE.exists()
        ),
        "ensemble_ready": (
            ENSEMBLE_FILE.exists()
        ),
        "prediction_horizon_hours": (
            load_classifier_artifacts()[3].get(
                "prediction_horizon_hours",
                168,
            )
            if CALIBRATED_MODEL_FILE.exists()
            else None
        ),
        "minimum_history_hours": (
            MINIMUM_HISTORY_HOURS
        ),
        "recommended_history_hours": (
            DEFAULT_HISTORY_HOURS
        ),
        "feature_timezone": FEATURE_TIMEZONE,
    }


def get_live_devices() -> list[str]:
    return get_available_devices()


def get_live_latest(
    device_id: str,
) -> dict:
    reading = get_latest_reading(device_id)

    if reading is None:
        raise ValueError(
            f"No readings found for device: "
            f"{device_id}"
        )

    return reading


def get_live_history(
    device_id: str,
    history_hours: int = DEFAULT_HISTORY_HOURS,
) -> dict:
    raw = get_recent_readings(
        device_id,
        history_hours=history_hours,
    )

    if raw.empty:
        raise ValueError(
            f"No recent readings found for "
            f"device: {device_id}"
        )

    canonical = canonicalize_live_data(
        raw,
        config=CONFIG,
    ).sort_values("timestamp")

    readings = []

    for _, row in canonical.iterrows():
        readings.append(
            {
                "timestamp": (
                    row["timestamp"].isoformat()
                    if pd.notna(row["timestamp"])
                    else None
                ),
                "internal_temperature_c": (
                    _safe_float(
                        row.get(
                            "internal_temperature_c"
                        )
                    )
                ),
                "internal_humidity_pct": (
                    _safe_float(
                        row.get(
                            "internal_humidity_pct"
                        )
                    )
                ),
                "co2_ppm": _safe_float(
                    row.get("co2_ppm")
                ),
                "hive_weight_kg": _safe_float(
                    row.get("hive_weight_kg")
                ),
                "external_temperature_c": (
                    _safe_float(
                        row.get(
                            "external_temperature_c"
                        )
                    )
                ),
                "external_humidity_pct": (
                    _safe_float(
                        row.get(
                            "external_humidity_pct"
                        )
                    )
                ),
                "battery_voltage": _safe_float(
                    row.get("battery_voltage")
                ),
            }
        )

    return {
        "device_id": device_id,
        "history_hours_requested": (
            history_hours
        ),
        "rows": len(readings),
        "completeness": round(
            calculate_hourly_completeness(
                canonical
            ),
            4,
        ),
        "readings": readings,
    }


def predict_live_harvest(
    device_id: str,
    history_hours: int = DEFAULT_HISTORY_HOURS,
) -> dict:
    history_hours = max(
        history_hours,
        MINIMUM_HISTORY_HOURS,
    )

    raw = get_recent_readings(
        device_id,
        history_hours=history_hours,
    )

    if raw.empty:
        return {
            "device_id": device_id,
            "prediction_available": False,
            "reason": (
                "No recent sensor readings "
                "were found."
            ),
        }

    canonical = canonicalize_live_data(
        raw,
        config=CONFIG,
    )
    completeness = (
        calculate_hourly_completeness(
            canonical
        )
    )
    history_span = _history_span_hours(
        canonical
    )
    latest_timestamp = _latest_timestamp(
        canonical
    )
    stale_minutes = _staleness_minutes(
        latest_timestamp
    )
    stale = (
        stale_minutes is None
        or stale_minutes > STALE_AFTER_MINUTES
    )

    warnings = []

    if history_span < MINIMUM_HISTORY_HOURS:
        warnings.append(
            f"Only {history_span:.1f} hours "
            "of sensor history are available."
        )

    if completeness < MINIMUM_COMPLETENESS:
        warnings.append(
            f"Hourly completeness is "
            f"{completeness:.1%}, below the "
            f"required {MINIMUM_COMPLETENESS:.0%}."
        )

    if stale:
        warnings.append(
            "The latest sensor reading is stale."
        )

    if history_span < MINIMUM_HISTORY_HOURS:
        return {
            "device_id": device_id,
            "prediction_available": False,
            "reason": (
                "Insufficient sensor history."
            ),
            "available_history_hours": round(
                history_span,
                2,
            ),
            "required_history_hours": (
                MINIMUM_HISTORY_HOURS
            ),
            "data_completeness": round(
                completeness,
                4,
            ),
            "warnings": warnings,
        }

    hourly = resample_hourly(
        canonical,
        config=CONFIG,
    )
    featured = add_live_features(
        hourly,
        config=CONFIG,
    )

    (
        model,
        features,
        ensemble,
        metadata,
    ) = load_classifier_artifacts()

    latest_rows = latest_complete_feature_rows(
        featured,
        feature_columns=features,
    )

    if latest_rows.empty:
        return {
            "device_id": device_id,
            "prediction_available": False,
            "reason": (
                "A complete model feature row "
                "could not be produced."
            ),
            "data_completeness": round(
                completeness,
                4,
            ),
            "warnings": warnings,
        }

    latest = latest_rows.iloc[-1]
    X = pd.DataFrame(
        [latest[features].to_dict()]
    )[features]

    probability = float(
        model.predict_proba(X)[0, 1]
    )
    probability = float(
        np.clip(probability, 0, 1)
    )

    ensemble_probabilities = []

    for _, ensemble_model in ensemble.items():
        try:
            ensemble_probabilities.append(
                float(
                    ensemble_model.predict_proba(
                        X
                    )[0, 1]
                )
            )
        except Exception:
            continue

    if not ensemble_probabilities:
        ensemble_probabilities = [probability]

    horizon_hours = int(
        metadata.get(
            "prediction_horizon_hours",
            168,
        )
    )

    hui = round(probability * 100, 2)
    status = readiness_status(hui)
    recommendation = (
        _recommendation_for_horizon(
            status,
            horizon_hours,
        )
    )
    threshold = float(
        metadata.get(
            "decision_threshold",
            0.70,
        )
    )

    out_of_distribution = (
        _out_of_distribution_warnings(
            latest,
            metadata,
            features,
        )
    )
    warnings.extend(out_of_distribution)

    confidence = _confidence_level(
        probabilities=ensemble_probabilities,
        completeness=completeness,
        stale=stale,
        out_of_distribution_count=len(
            out_of_distribution
        ),
    )

    environment = _environmental_suitability(
        latest,
        metadata,
    )
    reasons = _plain_language_reasons(
        latest,
        metadata,
    )

    prediction_timestamp = pd.Timestamp.now(
        tz="UTC"
    )
    sensor_timestamp = pd.Timestamp(
        latest["timestamp"]
    )

    save_prediction(
        device_id=device_id,
        prediction_timestamp=(
            prediction_timestamp.isoformat()
        ),
        sensor_timestamp=(
            sensor_timestamp.isoformat()
        ),
        harvest_probability=probability,
        hui=hui,
        status=status,
        decision_threshold=threshold,
        model_version=metadata.get(
            "model_version"
        ),
        data_completeness=completeness,
        confidence=confidence,
    )

    if horizon_hours == 72:
        harvest_window = (
            detect_sustained_harvest_window(
                device_id,
                threshold=threshold,
                required_hours=24,
            )
        )
    else:
        harvest_window = {
            "available": False,
            "reason": (
                "The available historical target "
                f"covers {horizon_hours} hours. "
                "A single future-horizon classifier "
                "cannot identify an exact start and "
                "end date for harvesting. Add an "
                "actual harvest-event timestamp or a "
                "separate next-72-hour target to "
                "produce a three-day harvest window."
            ),
        }

    battery_voltage = latest.get(
        "battery_voltage"
    )
    low_battery = (
        pd.notna(battery_voltage)
        and float(battery_voltage)
        < LOW_BATTERY_VOLTAGE
    )

    if low_battery:
        warnings.append(
            "Battery voltage is low; sensor "
            "reliability should be checked."
        )

    ready_for_action = (
        probability >= threshold
    )

    return {
        "device_id": device_id,
        "prediction_available": True,
        "reading_timestamp": (
            sensor_timestamp.isoformat()
        ),
        "prediction_timestamp": (
            prediction_timestamp.isoformat()
        ),
        "prediction_horizon": (
            _horizon_description(
                horizon_hours
            )
        ),
        "harvest_probability": round(
            probability,
            6,
        ),
        "harvest_readiness_percent": hui,
        "hui": hui,
        "status": status,
        "operational_decision": {
            "ready_for_action": (
                ready_for_action
            ),
            "validated_threshold": round(
                threshold * 100,
                2,
            ),
        },
        "recommendation": recommendation,
        "recommended_harvest_window": (
            harvest_window
        ),
        "estimated_days_until_harvest": {
            "available": False,
            "reason": (
                (
                    f"A {horizon_hours}-hour "
                    "classifier estimates event "
                    "probability, not exact "
                    "time-to-harvest."
                )
            ),
        },
        "confidence": {
            "level": confidence,
            "model_probabilities": [
                round(value, 6)
                for value
                in ensemble_probabilities
            ],
            "basis": (
                "Model agreement, sensor "
                "completeness, freshness and "
                "training-range checks."
            ),
        },
        "environmental_suitability": (
            environment
        ),
        "main_reasons": reasons,
        "current_sensor_values": {
            "internal_temperature_c": (
                _safe_float(
                    latest.get(
                        "internal_temperature_c"
                    )
                )
            ),
            "internal_humidity_pct": (
                _safe_float(
                    latest.get(
                        "internal_humidity_pct"
                    )
                )
            ),
            "co2_ppm": _safe_float(
                latest.get("co2_ppm")
            ),
            "hive_weight_kg": _safe_float(
                latest.get("hive_weight_kg")
            ),
            "external_temperature_c": (
                _safe_float(
                    latest.get(
                        "external_temperature_c"
                    )
                )
            ),
            "external_humidity_pct": (
                _safe_float(
                    latest.get(
                        "external_humidity_pct"
                    )
                )
            ),
            "battery_voltage": _safe_float(
                battery_voltage
            ),
        },
        "derived_values": {
            "weight_change_24h_kg": (
                _safe_float(
                    latest.get(
                        "weight_change_24h_kg"
                    )
                )
            ),
            "weight_change_72h_kg": (
                _safe_float(
                    latest.get(
                        "weight_change_72h_kg"
                    )
                )
            ),
            "weight_std_24h_kg": (
                _safe_float(
                    latest.get(
                        "weight_std_24h_kg"
                    )
                )
            ),
            "distance_from_7day_max_kg": (
                _safe_float(
                    latest.get(
                        "distance_from_7day_max_kg"
                    )
                )
            ),
        },
        "trend": {
            "previous_7_day_predictions": (
                get_prediction_history(
                    device_id,
                    hours=168,
                )
            )
        },
        "colony_risks": {
            "brood_health": "Unavailable",
            "swarming_risk": "Unavailable",
            "absconding_risk": "Unavailable",
            "note": (
                "Connect the outputs of the "
                "other modules here. Do not "
                "invent Good/Low values."
            ),
        },
        "data_quality": {
            "available_history_hours": round(
                history_span,
                2,
            ),
            "data_completeness": round(
                completeness,
                4,
            ),
            "reading_stale": stale,
            "staleness_minutes": (
                None
                if stale_minutes is None
                else round(stale_minutes, 2)
            ),
            "low_battery": bool(low_battery),
        },
        "model": {
            "name": metadata.get(
                "best_model"
            ),
            "version": metadata.get(
                "model_version"
            ),
            "target": metadata.get(
                "target"
            ),
            "trained_on": (
                "Historical dataset"
            ),
            "local_validation_status": (
                "Pending confirmed Sri Lankan "
                "harvest events"
            ),
        },
        "warnings": warnings,
    }


def predict_all_live_hives(
    history_hours: int = DEFAULT_HISTORY_HOURS,
) -> list[dict]:
    results = []

    for device_id in get_available_devices():
        try:
            result = predict_live_harvest(
                device_id,
                history_hours=history_hours,
            )
        except Exception as error:
            result = {
                "device_id": device_id,
                "prediction_available": False,
                "reason": str(error),
            }

        results.append(result)

    return results
