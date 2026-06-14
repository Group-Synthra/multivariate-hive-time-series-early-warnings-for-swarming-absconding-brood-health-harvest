from pathlib import Path
import json

from flask import Blueprint, jsonify, request, send_from_directory

from services.harvest_service import (
    get_sample_input,
    predict_hui
)


harvest_bp = Blueprint(
    "harvest",
    __name__,
    url_prefix="/api/harvest"
)


BACKEND_DIR = Path(__file__).resolve().parent.parent
HARVEST_OUTPUT_DIR = BACKEND_DIR / "outputs" / "harvest"

EDA_SUMMARY_FILE = (
    HARVEST_OUTPUT_DIR /
    "harvest_eda_summary.json"
)

MODEL_RESULTS_FILE = (
    HARVEST_OUTPUT_DIR /
    "model_comparison.json"
)

HIVE_ANALYSIS_FILE = (
    HARVEST_OUTPUT_DIR
    / "harvest_hive_analysis.json"
)

@harvest_bp.route("/eda-summary", methods=["GET"])
def get_eda_summary():
    if not EDA_SUMMARY_FILE.exists():
        return jsonify({
            "error": "Harvest EDA summary not found.",
            "hint": "Run the harvest pipeline first."
        }), 404

    try:
        with open(
            EDA_SUMMARY_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        return jsonify(data)

    except Exception as error:
        return jsonify({
            "error": str(error)
        }), 500


@harvest_bp.route("/model-results", methods=["GET"])
def get_model_results():
    if not MODEL_RESULTS_FILE.exists():
        return jsonify({
            "error": "Model-comparison results not found.",
            "hint": "Run train_hui_models.py first."
        }), 404

    try:
        with open(
            MODEL_RESULTS_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        return jsonify(data)

    except Exception as error:
        return jsonify({
            "error": str(error)
        }), 500


@harvest_bp.route("/images", methods=["GET"])
def list_images():
    if not HARVEST_OUTPUT_DIR.exists():
        return jsonify([])

    images = sorted(
        file.name
        for file in HARVEST_OUTPUT_DIR.glob("*.png")
    )

    return jsonify(images)


@harvest_bp.route(
    "/images/<path:filename>",
    methods=["GET"]
)
def serve_image(filename):
    image_path = HARVEST_OUTPUT_DIR / filename

    if not image_path.exists():
        return jsonify({
            "error": f"Harvest image not found: {filename}"
        }), 404

    return send_from_directory(
        str(HARVEST_OUTPUT_DIR),
        filename
    )


@harvest_bp.route("/sample", methods=["GET"])
def get_sample():
    try:
        return jsonify(get_sample_input())

    except FileNotFoundError as error:
        return jsonify({
            "error": str(error)
        }), 404

    except Exception as error:
        return jsonify({
            "error": str(error)
        }), 500


@harvest_bp.route("/predict", methods=["POST"])
def predict():
    payload = request.get_json(silent=True)

    if not payload or not isinstance(payload, dict):
        return jsonify({
            "error": "A JSON object containing model inputs is required."
        }), 400

    try:
        return jsonify(predict_hui(payload))

    except FileNotFoundError as error:
        return jsonify({
            "error": str(error)
        }), 404

    except ValueError as error:
        return jsonify({
            "error": str(error)
        }), 400

    except Exception as error:
        return jsonify({
            "error": "Prediction failed.",
            "details": str(error)
        }), 500
    

@harvest_bp.route(
    "/hive-analysis",
    methods=["GET"]
)
def get_hive_analysis():
    if not HIVE_ANALYSIS_FILE.exists():
        return jsonify({
            "error": "Hive harvesting analysis not found.",
            "hint": "Run the harvest EDA pipeline first."
        }), 404

    try:
        with open(
            HIVE_ANALYSIS_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        return jsonify(data)

    except Exception as error:
        return jsonify({
            "error": str(error)
        }), 500