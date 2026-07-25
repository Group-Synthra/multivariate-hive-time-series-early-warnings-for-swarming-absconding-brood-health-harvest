"""Predict future brood-health scores from live PostgreSQL sensor history."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from brood_health.analyzer import (
    HEALTH_LEVEL_DEFINITIONS,
    build_early_warning,
    classify_health,
    compute_brood_health_metrics,
)
from ml.features import (
    FEATURE_SCHEMA_VERSION,
    SENSORS,
    build_latest_feature_row,
    count_hourly_observations,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = BACKEND_DIR / "models" / "best_brood_model.joblib"

_SENSOR_LABELS = {
    "temp": "internal temperature",
    "humidity": "internal humidity",
    "co2": "internal CO2",
    "weight": "total hive weight",
    "external_temp": "external temperature",
    "external_humidity": "external humidity",
}


class BroodHealthPredictor:

    def __init__(self, model_path: Path = DEFAULT_MODEL_PATH) -> None:
        self.model_path = Path(model_path)
        self._bundle: dict[str, Any] | None = None
        self._loaded_mtime: float | None = None

    def _load_bundle(self) -> dict[str, Any]:
        if not self.model_path.exists():
            raise FileNotFoundError(
                "No trained brood-health model exists. Train the comparison models "
                "using backend/data/hive_data_with_features.csv first."
            )

        modified_time = self.model_path.stat().st_mtime
        if self._bundle is None or self._loaded_mtime != modified_time:
            bundle = joblib.load(self.model_path)
            required = {"model", "model_name", "feature_columns", "horizon_hours"}
            if not isinstance(bundle, dict) or not required.issubset(bundle):
                raise ValueError("Saved model bundle is incomplete or incompatible")

            saved_schema = bundle.get("feature_schema_version")
            if saved_schema != FEATURE_SCHEMA_VERSION:
                raise ValueError(
                    "The saved model was trained with an older feature schema. "
                    "Retrain it so external temperature and external humidity are "
                    f"included. Expected {FEATURE_SCHEMA_VERSION!r}, received {saved_schema!r}."
                )

            self._bundle = bundle
            self._loaded_mtime = modified_time
        return self._bundle

    def model_information(self) -> dict[str, Any]:
        bundle = self._load_bundle()
        return {
            "model_name": bundle["model_name"],
            "horizon_hours": int(bundle["horizon_hours"]),
            "feature_count": len(bundle["feature_columns"]),
            "feature_schema_version": bundle.get("feature_schema_version"),
            "prediction_inputs": bundle.get("prediction_inputs", list(SENSORS)),
            "trained_at_utc": bundle.get("trained_at_utc"),
            "training_source": "backend/data/hive_data_with_features.csv",
            "live_source": "public.beehive_readings",
            "target_kind": bundle.get("target_kind", "unknown"),
            "target_warning": bundle.get("target_warning"),
            "battery_voltage_usage": "device_quality_only_not_model_input",
        }

    def _domain_shift_warnings(
        self,
        readings: pd.DataFrame,
        reference: dict[str, dict[str, float]],
    ) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []
        if not reference:
            return warnings

        ordered = readings.sort_values("timestamp")
        recent = ordered.tail(min(len(ordered), 144))
        for sensor in SENSORS:
            if sensor not in recent.columns or sensor not in reference:
                continue
            values = pd.to_numeric(recent[sensor], errors="coerce").dropna()
            if values.empty:
                continue
            live_median = float(values.median())
            low = float(reference[sensor].get("p01", live_median))
            high = float(reference[sensor].get("p99", live_median))
            if live_median < low or live_median > high:
                warnings.append(
                    {
                        "sensor": sensor,
                        "label": _SENSOR_LABELS[sensor],
                        "live_recent_median": round(live_median, 4),
                        "training_p01": round(low, 4),
                        "training_p99": round(high, 4),
                        "message": (
                            f"Live {_SENSOR_LABELS[sensor]} is outside the central "
                            "training-data range. Check units, calibration and local "
                            "Sri Lankan validation before relying on the prediction."
                        ),
                    }
                )
        return warnings

    @staticmethod
    def _latest_input_payload(latest_sensor: pd.Series) -> dict[str, float | None]:
        def optional_number(name: str, digits: int) -> float | None:
            value = latest_sensor.get(name)
            if value is None or pd.isna(value):
                return None
            return round(float(value), digits)

        return {
            "internal_temperature_c": optional_number("temp", 3),
            "internal_humidity_pct": optional_number("humidity", 3),
            "internal_co2_ppm": optional_number("co2", 3),
            "hive_weight_kg": optional_number("weight", 4),
            "external_temperature_c": optional_number("external_temp", 3),
            "external_humidity_pct": optional_number("external_humidity", 3),
            "battery_voltage": optional_number("battery_voltage", 3),
        }

    def predict_from_history(
        self,
        readings: pd.DataFrame,
        *,
        data_source: str = "postgresql_iot",
        timeline_points: int = 144,
    ) -> dict[str, Any]:
        """Return forecast risk, BHSI, RoD and a ten-minute live timeline."""
        if readings.empty:
            raise ValueError("No IoT readings were supplied for prediction")

        bundle = self._load_bundle()
        X_latest, input_timestamp, hive = build_latest_feature_row(
            readings,
            expected_features=bundle["feature_columns"],
        )

        predicted_score = float(bundle["model"].predict(X_latest)[0])
        predicted_score = max(0.0, min(100.0, predicted_score))
        predicted_level = classify_health(predicted_score)
    
        health_definition = next(
            definition
            for definition in HEALTH_LEVEL_DEFINITIONS
            if definition["level"] == predicted_level
        )

        current_metrics = compute_brood_health_metrics(readings)
        current_metrics = current_metrics.sort_values("timestamp")
        current_latest = current_metrics.iloc[-1]
        latest_sensor = readings.sort_values("timestamp").iloc[-1]

        early_warning = build_early_warning(
            predicted_score=predicted_score,
            current_score=float(current_latest["brood_health_score"]),
            bhsi=float(current_latest["bhsi"]),
            rod=float(current_latest["rod"]),
        )

        horizon_hours = int(bundle["horizon_hours"])
        forecast_timestamp = input_timestamp + pd.Timedelta(hours=horizon_hours)
        domain_shift = self._domain_shift_warnings(
            readings,
            bundle.get("training_sensor_reference", {}),
        )

        timeline = current_metrics.tail(max(24, int(timeline_points))).copy()
        timeline_records = []
        for row in timeline.to_dict(orient="records"):
            timeline_records.append(
                {
                    "timestamp": pd.Timestamp(row["timestamp"]).isoformat(),
                    "brood_health_score": float(row["brood_health_score"]),
                    "bhsi": float(row["bhsi"]),
                    "rod": float(row["rod"]),
                    "health_level": str(row["health_level"]),
                    "stability_level": str(row["stability_level"]),
                    "trend_label": str(row["trend_label"]),
                }
            )

        return {
            "hive": hive,
            "data_source": data_source,
            "model_training_source": "historical_csv",
            "input_timestamp": pd.Timestamp(input_timestamp).isoformat(),
            "latest_sensor_timestamp": pd.Timestamp(latest_sensor["timestamp"]).isoformat(),
            "forecast_timestamp": pd.Timestamp(forecast_timestamp).isoformat(),
            "forecast_horizon_hours": horizon_hours,
            "model_name": bundle["model_name"],
            "feature_schema_version": bundle.get("feature_schema_version"),
            "model_inputs": list(SENSORS),
            "predicted_score": round(predicted_score, 2),
            "predicted_health_level": predicted_level,
            "predicted_health_range": health_definition["display_range"],
            "predicted_health_rule": health_definition["rule"],
            "current_score": float(current_latest["brood_health_score"]),
            "current_health_level": str(current_latest["health_level"]),
            "bhsi": float(current_latest["bhsi"]),
            "stability_level": str(current_latest["stability_level"]),
            "rod": float(current_latest["rod"]),
            "trend_label": str(current_latest["trend_label"]),
            "early_warning": early_warning,
            "latest_inputs": self._latest_input_payload(latest_sensor),
            "history_rows_received": int(len(readings)),
            "hourly_observations_used": count_hourly_observations(readings),
            "prediction_reliability": (
                "caution" if domain_shift else "within_training_range"
            ),
            "domain_shift_warnings": domain_shift,
            "timeline": timeline_records,
            "timeline_sampling": "source_frequency_approximately_10_minutes",
            "recommended_refresh_seconds": 600,
            "target_kind": bundle.get("target_kind", "unknown"),
            "target_warning": bundle.get("target_warning"),
        }