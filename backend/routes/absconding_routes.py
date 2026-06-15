"""
Flask routes for Module 03 — Absconding Behaviour Prediction.

Register in backend/app.py:
    from backend.routes.absconding_routes import absconding_bp
    app.register_blueprint(absconding_bp)
"""

from __future__ import annotations

import json
from pathlib import Path

from flask import Blueprint, jsonify, send_from_directory

try:
    from backend.ml.absconding.absconding_pipeline import predict_latest_from_saved_model
except Exception:
    predict_latest_from_saved_model = None

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
