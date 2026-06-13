
"""
Flask routes for Absconding Prediction Module.

How to integrate in backend/app.py:

from backend.routes.absconding_routes import absconding_bp
app.register_blueprint(absconding_bp)

Make sure the absconding pipeline has already generated:
backend/outputs/absconding/absconding_dashboard.json
"""

from pathlib import Path
import json

from flask import Blueprint, jsonify, send_from_directory, request

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
            "error": "Absconding dashboard data not found. Run: python backend/scripts/run_absconding.py"
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


@absconding_bp.get("/metrics")
def metrics():
    data = _read_dashboard()
    if data is None:
        return jsonify({"error": "Run absconding pipeline first"}), 404
    return jsonify(data.get("model_metrics", {}))


@absconding_bp.get("/images/<path:filename>")
def images(filename):
    plots_dir = OUTPUT_DIR / "plots"
    return send_from_directory(plots_dir, filename)


@absconding_bp.post("/predict-latest")
def predict_latest():
    """
    Optional endpoint for a custom CSV path:
    {
      "data_path": "backend/data/hive_data_with_features.csv",
      "model_path": "backend/outputs/absconding/models/absconding_fast_model.joblib"
    }
    """
    if predict_latest_from_saved_model is None:
        return jsonify({"error": "Prediction dependencies not available"}), 500

    body = request.get_json(silent=True) or {}
    data_path = Path(body.get("data_path", BACKEND_DIR / "data" / "hive_data_with_features.csv"))
    model_path = Path(body.get("model_path", OUTPUT_DIR / "models" / "absconding_fast_model.joblib"))
    if not model_path.exists():
        return jsonify({"error": f"Model file not found: {model_path}"}), 404

    result = predict_latest_from_saved_model(model_path, data_path, OUTPUT_DIR)
    return jsonify(result)
