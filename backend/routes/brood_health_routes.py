"""Flask endpoints for brood-health EDA, CSV training and PostgreSQL IoT inference."""

from __future__ import annotations

import json
import threading
import traceback
from pathlib import Path
from typing import Any

import pandas as pd
from flask import Blueprint, jsonify, request

from brood_health.analyzer import (
    HEALTH_LEVEL_DEFINITIONS,
    compute_brood_health_metrics,
)
from iot.postgres_repository import IoTDatabaseError, PostgreSQLHiveRepository
from ml.features import count_hourly_observations
from ml.predict_brood_health import BroodHealthPredictor

brood_health_bp = Blueprint("brood_health", __name__, url_prefix="/api")

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BACKEND_DIR / "data" / "hive_data_with_features.csv"
MODEL_DIR = BACKEND_DIR / "models"
SUMMARY_PATH = MODEL_DIR / "training_summary.json"

_status_lock = threading.Lock()
training_status: dict[str, Any] = {
    "running": False,
    "result": None,
    "error": None,
    "current_step": "",
    "progress": 0,
    "message": "",
}

predictor = BroodHealthPredictor(MODEL_DIR / "best_brood_model.joblib")
_repository: PostgreSQLHiveRepository | None = None
_repository_lock = threading.Lock()

_metrics_cache_lock = threading.Lock()
_metrics_cache_mtime_ns: int | None = None
_metrics_cache: pd.DataFrame | None = None


def _set_status(**updates: Any) -> None:
    with _status_lock:
        training_status.update(updates)


def _status_snapshot() -> dict[str, Any]:
    with _status_lock:
        return dict(training_status)


def _get_repository() -> PostgreSQLHiveRepository:
    global _repository
    with _repository_lock:
        if _repository is None:
            _repository = PostgreSQLHiveRepository()
        return _repository


def load_cached_brood_health_metrics() -> pd.DataFrame:
    """Load and cache CSV-derived EDA metrics."""
    global _metrics_cache, _metrics_cache_mtime_ns

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Training/EDA CSV not found: {DATA_PATH}")

    modified_time = DATA_PATH.stat().st_mtime_ns
    with _metrics_cache_lock:
        if _metrics_cache is None or _metrics_cache_mtime_ns != modified_time:
            raw = pd.read_csv(DATA_PATH)
            _metrics_cache = compute_brood_health_metrics(raw)
            _metrics_cache_mtime_ns = modified_time
        return _metrics_cache


# Historical CSV EDA endpoints
# ---------------------------------------------------------------------------
@brood_health_bp.get("/brood_health")
def get_brood_health():
    """Return CSV-derived historical metrics for exploratory analysis."""
    try:
        hive = request.args.get("hive")
        limit = min(max(request.args.get("limit", default=2000, type=int), 1), 10000)
        metrics = load_cached_brood_health_metrics()
        if hive:
            metrics = metrics[metrics["hive"].astype(str) == str(hive)]
            if metrics.empty:
                return jsonify({"error": f"Unknown historical hive: {hive}"}), 404
        metrics = metrics.groupby("hive", group_keys=False).tail(limit).copy()
        metrics["timestamp"] = metrics["timestamp"].map(pd.Timestamp.isoformat)
        return jsonify(metrics.to_dict(orient="records"))
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500


@brood_health_bp.get("/brood_health/health-levels")
def brood_health_health_levels():
    return jsonify(list(HEALTH_LEVEL_DEFINITIONS))


@brood_health_bp.get("/brood_health/summary")
def brood_health_summary():
    """Return historical CSV summary used by the EDA tab."""
    try:
        metrics = load_cached_brood_health_metrics()
        output: list[dict[str, Any]] = []
        for hive, group in metrics.groupby("hive", sort=True):
            group = group.sort_values("timestamp")
            latest = group.iloc[-1]
            output.append(
                {
                    "hive": str(hive),
                    "avg_score": round(float(group["brood_health_score"].mean()), 2),
                    "current_score": float(latest["brood_health_score"]),
                    "avg_bhsi": round(float(group["bhsi"].mean()), 2),
                    "current_bhsi": float(latest["bhsi"]),
                    "rod": float(latest["rod"]),
                    "health_level": latest["health_level"],
                    "health_range": latest["health_range"],
                    "health_rule": latest["health_rule"],
                    "stability_level": latest["stability_level"],
                    "trend_label": latest["trend_label"],
                    "timestamp": pd.Timestamp(latest["timestamp"]).isoformat(),
                    "temperature_c": round(float(latest["temp"]), 2),
                    "humidity_pct": round(float(latest["humidity"]), 2),
                    "co2_ppm": round(float(latest["co2"]), 2),
                    "hive_weight_kg": round(float(latest["weight"]), 3),
                    "data_source": "historical_csv",
                }
            )
        return jsonify(output)
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500

# Model training endpoints
# ---------------------------------------------------------------------------
def _train_task(*, fast_mode: bool, horizon_hours: int) -> None:
    _set_status(
        running=True,
        result=None,
        error=None,
        progress=0,
        message="Starting CSV model training",
        current_step="Initialising",
    )

    def progress_callback(event: str, data: dict[str, Any]) -> None:
        current = _status_snapshot()
        updates: dict[str, Any] = {
            "message": data.get("message", ""),
            "progress": data.get("progress", current.get("progress", 0)),
        }
        if data.get("model"):
            updates["current_step"] = data["model"]
        if event == "complete":
            updates["result"] = data.get("result")
        _set_status(**updates)

    try:
        from ml.train_brood_health_models import run_training

        result = run_training(
            progress_callback=progress_callback,
            data_path=DATA_PATH,
            horizon_hours=horizon_hours,
            fast_mode=fast_mode,
        )
        _set_status(result=result, progress=100, message="CSV model training complete")
    except Exception as exc:
        traceback.print_exc()
        _set_status(error=str(exc), message=f"Training failed: {exc}")
    finally:
        _set_status(running=False, current_step="")


@brood_health_bp.post("/brood_health/train")
def start_training():
    current = _status_snapshot()
    if current["running"]:
        return jsonify({"status": "already_running", "message": current["message"]}), 409

    payload = request.get_json(silent=True) or {}
    fast_mode = bool(payload.get("fast_mode", False))
    horizon_hours = int(payload.get("horizon_hours", 6))
    if horizon_hours < 1 or horizon_hours > 168:
        return jsonify({"error": "horizon_hours must be between 1 and 168"}), 400

    thread = threading.Thread(
        target=_train_task,
        kwargs={"fast_mode": fast_mode, "horizon_hours": horizon_hours},
        daemon=True,
    )
    thread.start()
    return jsonify(
        {
            "status": "started",
            "message": "Training started using backend/data/hive_data_with_features.csv",
            "fast_mode": fast_mode,
            "horizon_hours": horizon_hours,
            "training_source": "historical_csv",
        }
    )


@brood_health_bp.get("/brood_health/train/status")
def training_status_endpoint():
    live = _status_snapshot()
    if live["running"] or live["error"] or live["result"]:
        return jsonify(live)

    if SUMMARY_PATH.exists():
        cached = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
        return jsonify(
            {
                "running": False,
                "result": cached,
                "error": None,
                "current_step": "",
                "progress": 100,
                "message": "Training complete (saved CSV-trained model)",
            }
        )
    return jsonify(live)


@brood_health_bp.get("/brood_health/model")
def model_information():
    try:
        return jsonify(predictor.model_information())
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

# Live PostgreSQL/Supabase IoT endpoints
# ---------------------------------------------------------------------------
@brood_health_bp.get("/brood_health/iot/status")
def iot_database_status():
    try:
        status = _get_repository().ping()
        status["data_source"] = "postgresql_iot"
        return jsonify(status)
    except IoTDatabaseError as exc:
        return jsonify({"connected": False, "error": str(exc)}), 503


@brood_health_bp.get("/brood_health/iot/hives")
def iot_hives():
    try:
        return jsonify(_get_repository().list_hives())
    except IoTDatabaseError as exc:
        return jsonify({"error": str(exc)}), 503


@brood_health_bp.get("/brood_health/iot/latest")
def iot_latest():
    hive = request.args.get("hive", "").strip()
    if not hive:
        return jsonify({"error": "hive query parameter is required"}), 400
    try:
        latest = _get_repository().fetch_latest(hive)
        if latest is None:
            return jsonify({"error": f"No valid IoT readings found for hive {hive}"}), 404
        return jsonify(latest)
    except (IoTDatabaseError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 503 if isinstance(exc, IoTDatabaseError) else 400


@brood_health_bp.get("/brood_health/iot/history")
def iot_history():
    hive = request.args.get("hive", "").strip()
    if not hive:
        return jsonify({"error": "hive query parameter is required"}), 400

    hours = min(max(request.args.get("hours", default=168, type=int), 25), 24 * 30)
    max_rows = min(max(request.args.get("max_rows", default=20000, type=int), 100), 100000)
    try:
        history = _get_repository().fetch_history(hive, hours=hours, max_rows=max_rows)
        if history.empty:
            return jsonify({"error": f"No valid IoT readings found for hive {hive}"}), 404
        output = history.copy()
        for timestamp_column in ("timestamp", "reading_at"):
            if timestamp_column in output.columns:
                output[timestamp_column] = output[timestamp_column].map(
                    lambda value: None if pd.isna(value) else pd.Timestamp(value).isoformat()
                )
        output = output.astype(object).where(pd.notna(output), None)
        records = output.to_dict(orient="records")
        return jsonify(
            {
                "hive": hive,
                "data_source": "postgresql_iot",
                "requested_history_hours": hours,
                "raw_record_count": len(records),
                "hourly_observation_count": count_hourly_observations(history),
                "history_start": pd.Timestamp(history["timestamp"].min()).isoformat(),
                "history_end": pd.Timestamp(history["timestamp"].max()).isoformat(),
                "records": records,
            }
        )
    except (IoTDatabaseError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 503 if isinstance(exc, IoTDatabaseError) else 400


@brood_health_bp.get("/brood_health/iot/dashboard")
def iot_dashboard():
    hive = request.args.get("hive", "").strip()
    if not hive:
        return jsonify({"error": "hive query parameter is required"}), 400

    history_hours = min(
        max(request.args.get("hours", default=168, type=int), 25),
        24 * 30,
    )
    max_rows = min(
        max(request.args.get("max_rows", default=20000, type=int), 100),
        100000,
    )
    timeline_points = min(
        max(request.args.get("timeline_points", default=144, type=int), 24),
        1008,
    )

    try:
        history = _get_repository().fetch_history(
            hive,
            hours=history_hours,
            max_rows=max_rows,
        )
        if history.empty:
            return jsonify({"error": f"No valid IoT readings found for hive {hive}"}), 404

        result = predictor.predict_from_history(
            history,
            data_source="postgresql_iot",
            timeline_points=timeline_points,
        )
        result["requested_history_hours"] = history_hours
        result["raw_database_rows"] = int(len(history))
        result["database_table"] = "public.beehive_readings"
        return jsonify(result)
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 409
    except IoTDatabaseError as exc:
        return jsonify({"error": str(exc)}), 503
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500


@brood_health_bp.post("/brood_health/iot/predict")
def predict_from_iot_database():
    """Fetch actual PostgreSQL readings and predict with the CSV-selected model."""
    payload = request.get_json(silent=True) or {}
    hive = str(payload.get("hive", "")).strip()
    if not hive:
        return jsonify({"error": "Request body must contain a hive value"}), 400

    history_hours = min(max(int(payload.get("history_hours", 168)), 25), 24 * 30)
    max_rows = min(max(int(payload.get("max_rows", 20000)), 100), 100000)
    try:
        history = _get_repository().fetch_history(
            hive,
            hours=history_hours,
            max_rows=max_rows,
        )
        if history.empty:
            return jsonify({"error": f"No valid IoT readings found for hive {hive}"}), 404
        result = predictor.predict_from_history(history, data_source="postgresql_iot")
        return jsonify(result)
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 409
    except IoTDatabaseError as exc:
        return jsonify({"error": str(exc)}), 503
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500


@brood_health_bp.post("/brood_health/predict")
def deprecated_manual_prediction():
    return jsonify(
        {
            "error": (
                "This endpoint no longer accepts CSV/API readings for the live tab. "
                "Use POST /api/brood_health/iot/predict with {'hive': '<id>'}; "
                "the backend will fetch actual readings from PostgreSQL."
            )
        }
    ), 410