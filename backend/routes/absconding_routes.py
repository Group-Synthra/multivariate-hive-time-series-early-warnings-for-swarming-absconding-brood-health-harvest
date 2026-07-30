"""
Flask routes for Module 03 — Absconding Behaviour Prediction.

Register in backend/app.py:
    from backend.routes.absconding_routes import absconding_bp
    app.register_blueprint(absconding_bp)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make imports work whether backend/app.py is run from project root or backend folder.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Blueprint, jsonify, send_from_directory, request

try:
    from backend.ml.absconding.absconding_pipeline import predict_latest_from_saved_model
except Exception:
    predict_latest_from_saved_model = None

try:
    from backend.ml.absconding.iot_live_prediction import (
        append_iot_reading,
        predict_live_iot_absconding,
    )
    from backend.ml.absconding.iot_monitor import (
        get_iot_monitor_status,
        read_cached_live_prediction,
        run_iot_monitor_once,
        start_iot_monitor,
        stop_iot_monitor,
    )
except Exception:
    append_iot_reading = None
    predict_live_iot_absconding = None
    get_iot_monitor_status = None
    read_cached_live_prediction = None
    run_iot_monitor_once = None
    start_iot_monitor = None
    stop_iot_monitor = None

absconding_bp = Blueprint("absconding", __name__, url_prefix="/api/absconding")

BACKEND_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BACKEND_DIR / "outputs" / "absconding"
DASHBOARD_JSON = OUTPUT_DIR / "absconding_dashboard.json"


def _read_dashboard():
    if not DASHBOARD_JSON.exists():
        return None
    return json.loads(DASHBOARD_JSON.read_text(encoding="utf-8"))


@absconding_bp.get("/summary")
def summary():
    data = _read_dashboard()
    if data is None:
        return jsonify({
            "error": "Absconding dashboard data not found. Run: python backend/scripts/run_absconding.py --model rf --compare-models"
        }), 404
    return jsonify(data)


@absconding_bp.get("/predictions")
def predictions():
    data = _read_dashboard()
    if data is None:
        return jsonify({"error": "Run absconding pipeline first"}), 404
    return jsonify({
        "per_hive_absconding_risk": data.get("per_hive_absconding_risk", []),
        "alerts": data.get("alerts", []),
    })


@absconding_bp.get("/hives")
def hives():
    data = _read_dashboard()
    if data is None:
        return jsonify({"error": "Run absconding pipeline first"}), 404
    return jsonify({
        "hive_options": data.get("hive_options", []),
        "per_hive_absconding_risk": data.get("per_hive_absconding_risk", []),
    })


@absconding_bp.get("/hive/<path:hive_id>")
def hive_detail(hive_id):
    data = _read_dashboard()
    if data is None:
        return jsonify({"error": "Run absconding pipeline first"}), 404
    details = data.get("hive_details", {})
    if hive_id not in details:
        return jsonify({"error": f"Hive '{hive_id}' not found", "available_hives": data.get("hive_options", [])}), 404
    return jsonify(details[hive_id])


@absconding_bp.get("/metrics")
def metrics():
    data = _read_dashboard()
    if data is None:
        return jsonify({"error": "Run absconding pipeline first"}), 404
    return jsonify(data.get("model_metrics", {}))


@absconding_bp.get("/model-comparison")
def model_comparison():
    data = _read_dashboard()
    if data is None:
        return jsonify({"error": "Run absconding pipeline first"}), 404
    return jsonify({
        "model_comparison": data.get("model_comparison", []),
        "model_selection_rationale": data.get("model_selection_rationale", {}),
    })


@absconding_bp.get("/iot/live")
def iot_live_prediction():
    """
    Live IoT prediction endpoint for the dashboard.

    Normal mode: returns the latest prediction cached by the backend IoT monitor.
    Force mode: /api/absconding/iot/live?force=true pulls Supabase immediately.

    This means real IoT data collection is handled by the BACKEND every 10 minutes,
    not only by the frontend refresh timer.
    """
    if predict_live_iot_absconding is None:
        return jsonify({"status": "error", "error": "IoT live prediction module unavailable"}), 500

    force = str(request.args.get("force", "")).lower() in {"1", "true", "yes", "now"}

    try:
        if force and run_iot_monitor_once is not None:
            result = run_iot_monitor_once(OUTPUT_DIR)
            result["api_delivery_mode"] = "forced_database_pull"
            return jsonify(result)

        # Prefer the backend monitor cache. The monitor fetches the real Supabase
        # data every 10 minutes even when the browser is closed.
        if read_cached_live_prediction is not None:
            cached_result = read_cached_live_prediction(OUTPUT_DIR)
            if cached_result is not None:
                cached_result["api_delivery_mode"] = "backend_cached_real_iot"
                return jsonify(cached_result)

        # First run fallback: if no cache exists yet, pull Supabase immediately.
        if run_iot_monitor_once is not None:
            result = run_iot_monitor_once(OUTPUT_DIR)
            result["api_delivery_mode"] = "initial_database_pull"
            return jsonify(result)

        # Last fallback for old installs.
        result = predict_live_iot_absconding(OUTPUT_DIR)
        result["api_delivery_mode"] = "direct_database_pull"
        return jsonify(result)

    except Exception as exc:
        # Try to return the last saved real IoT result if the DB temporarily disconnects.
        if read_cached_live_prediction is not None:
            cached_result = read_cached_live_prediction(OUTPUT_DIR)
            if cached_result is not None:
                cached_result["status"] = "cached"
                cached_result["warning"] = f"Live source temporarily unavailable: {exc}"
                cached_result["api_delivery_mode"] = "cached_after_live_error"
                return jsonify(cached_result)
        return jsonify({
            "status": "not_configured",
            "error": str(exc),
            "setup": [
                "Train model first: python backend/scripts/run_absconding.py --model rf --compare-models",
                "Set IOT_DATA_SOURCE=postgres and DATABASE_URL=<your PostgreSQL URL> in backend/.env",
                "Set IOT_SENSOR_TABLE=beehive_readings and screenshot-style column env variables",
                "Keep IOT_MONITOR_ENABLED=true so the backend pulls IoT data every 10 minutes",
            ]
        }), 404


@absconding_bp.get("/iot/monitor/status")
def iot_monitor_status():
    """Check whether the backend IoT polling loop is running."""
    if get_iot_monitor_status is None:
        return jsonify({"status": "error", "error": "IoT monitor module unavailable"}), 500
    return jsonify(get_iot_monitor_status(OUTPUT_DIR))


@absconding_bp.post("/iot/monitor/start")
def iot_monitor_start():
    """Start backend polling loop manually."""
    if start_iot_monitor is None:
        return jsonify({"status": "error", "error": "IoT monitor module unavailable"}), 500
    return jsonify(start_iot_monitor(OUTPUT_DIR))


@absconding_bp.post("/iot/monitor/stop")
def iot_monitor_stop():
    """Stop backend polling loop manually."""
    if stop_iot_monitor is None:
        return jsonify({"status": "error", "error": "IoT monitor module unavailable"}), 500
    return jsonify(stop_iot_monitor(OUTPUT_DIR))


@absconding_bp.post("/iot/monitor/run-now")
def iot_monitor_run_now():
    """Immediately fetch Supabase IoT data and create a new live prediction."""
    if run_iot_monitor_once is None:
        return jsonify({"status": "error", "error": "IoT monitor module unavailable"}), 500
    try:
        result = run_iot_monitor_once(OUTPUT_DIR)
        result["api_delivery_mode"] = "manual_database_pull"
        return jsonify(result)
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@absconding_bp.post("/iot/ingest")
def ingest_iot_reading():
    """
    Temporary/manual IoT ingestion endpoint.

    Use this until the final database link is connected. An ESP32, Postman, or
    test script can POST one reading every 10 minutes.
    """
    if append_iot_reading is None:
        return jsonify({"status": "error", "error": "IoT ingestion module unavailable"}), 500
    payload = request.get_json(silent=True) or {}
    if not payload:
        return jsonify({
            "status": "error",
            "error": "Send JSON with timestamp, hive_id, temperature, humidity, co2, and weight."
        }), 400
    try:
        saved = append_iot_reading(payload)
        # Update live cache immediately after manual/demo ingestion.
        refreshed = None
        if run_iot_monitor_once is not None:
            try:
                refreshed = run_iot_monitor_once(OUTPUT_DIR)
            except Exception:
                refreshed = None
        return jsonify({"status": "saved", "reading": saved, "live_prediction_refreshed": refreshed is not None})
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400


@absconding_bp.get("/images/<path:filename>")
def images(filename):
    plots_dir = OUTPUT_DIR / "plots"
    return send_from_directory(plots_dir, filename)


@absconding_bp.post("/refresh")
def refresh_predictions():
    """Optional: refresh per-hive predictions from the latest saved model."""
    if predict_latest_from_saved_model is None:
        return jsonify({"error": "Prediction function unavailable"}), 500
    model_candidates = sorted((OUTPUT_DIR / "models").glob("absconding_*_model.joblib"))
    if not model_candidates:
        return jsonify({"error": "No saved absconding model found. Run the training script first."}), 404
    data_path = BACKEND_DIR / "data" / "hive_data_with_features.csv"
    result = predict_latest_from_saved_model(model_candidates[-1], data_path, OUTPUT_DIR)
    return jsonify(result)
