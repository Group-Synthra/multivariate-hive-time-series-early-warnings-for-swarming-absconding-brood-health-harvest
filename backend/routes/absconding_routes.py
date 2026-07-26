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
except Exception:
    append_iot_reading = None
    predict_live_iot_absconding = None

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
    Real-time IoT prediction endpoint for one verification hive.

    The endpoint reads the latest IoT records, applies the saved model, calculates
    ARM, and returns next-24h warning output for the Live Prediction (IoT) tab.
    """
    if predict_live_iot_absconding is None:
        return jsonify({"status": "error", "error": "IoT live prediction module unavailable"}), 500
    try:
        result = predict_live_iot_absconding(OUTPUT_DIR)
        return jsonify(result)
    except Exception as exc:
        # Try to return the last saved live result if available.
        cached = OUTPUT_DIR / "predictions" / "iot_live_latest.json"
        if cached.exists():
            data = json.loads(cached.read_text(encoding="utf-8"))
            data["status"] = "cached"
            data["warning"] = f"Live source temporarily unavailable: {exc}"
            return jsonify(data)
        return jsonify({
            "status": "not_configured",
            "error": str(exc),
            "setup": [
                "Train model first: python backend/scripts/run_absconding.py --model rf --compare-models",
                "Send IoT readings using POST /api/absconding/iot/ingest",
                "For Supabase: set IOT_DATA_SOURCE=postgres and SUPABASE_DB_URL=<your PostgreSQL URL>",
                "Set IOT_TABLE and column env variables if your table/columns use different names",
                "Or create backend/data/iot_live_readings.csv for local testing",
            ]
        }), 404


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
        return jsonify({"status": "saved", "reading": saved})
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
