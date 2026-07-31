"""
=========================================================
Swarming Live Prediction API — Flask Blueprint
=========================================================

Routes:
  POST  /api/swarming/live-prediction
        Accepts: { "hive_id": str, "readings": [ ...24 dicts... ] }
        Returns: prediction JSON

  GET   /api/swarming/live-prediction/sample
        Returns a sample request payload for testing.

  GET   /api/swarming/live-prediction/health
        Returns model availability status.
=========================================================
"""

import os
import logging
import numpy as np

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

swarming_live_bp = Blueprint("swarming_live", __name__)

# Lazy import to avoid crashing Flask startup if TF is slow to load
_predictor = None


def _get_predictor():
    global _predictor
    if _predictor is None:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from live_prediction import live_predictor
        _predictor = live_predictor
    return _predictor


# -------------------------------------------------------
# Sample payload — realistic values for a high-risk hive
# -------------------------------------------------------

def _generate_sample_readings(n: int = 24) -> list:
    """Generate synthetic readings that mimic a pre-swarm state."""
    import random
    random.seed(42)
    readings = []
    for i in range(n):
        # Gradual temperature rise and CO2 spike toward the end
        temp_trend  = 0.3 * i
        co2_trend   = 15  * i
        weight_drop = -0.05 * i
        readings.append({
            "internal_temperature_c": round(34.5 + temp_trend + random.uniform(-0.2, 0.2), 2),
            "internal_humidity_pct" : round(65.0 + random.uniform(-1.0, 1.0), 2),
            "co2_ppm"               : round(1200 + co2_trend  + random.uniform(-30, 30), 2),
            "hive_weight_kg"        : round(35.0 + weight_drop + random.uniform(-0.1, 0.1), 2),
            "external_temperature_c": round(28.0 + random.uniform(-0.5, 0.5), 2),
            "external_humidity_pct" : round(55.0 + random.uniform(-1.0, 1.0), 2),
            "rainfall_mm_hour"      : round(max(0, random.uniform(0, 0.2)), 2),
            "wind_speed_mps"        : round(2.0  + random.uniform(0, 0.5), 2),
        })
    return readings


# ──────────────────────────────────────────────────────────────
# POST /api/swarming/live-prediction
# ──────────────────────────────────────────────────────────────
@swarming_live_bp.route("/api/swarming/live-prediction", methods=["POST"])
def live_prediction():
    """
    Run live swarming prediction.

    Request body (JSON):
    {
        "hive_id" : "Hive_01",
        "readings": [
            {
                "internal_temperature_c" : 35.2,
                "internal_humidity_pct"  : 64.5,
                "co2_ppm"                : 1850,
                "hive_weight_kg"         : 32.1,
                "external_temperature_c" : 27.0,
                "external_humidity_pct"  : 55.3,
                "rainfall_mm_hour"       : 0.0,
                "wind_speed_mps"         : 2.1
            },
            ...  (24 entries total)
        ]
    }
    """
    # ── Validate Content-Type ─────────────────────────────────
    if not request.is_json:
        return jsonify({
            "error"  : "Request must be JSON.",
            "hint"   : "Set Content-Type: application/json"
        }), 415

    body = request.get_json(silent=True)

    if body is None:
        return jsonify({"error": "Invalid or empty JSON body."}), 400

    # ── Validate required fields ──────────────────────────────
    hive_id  = body.get("hive_id",  "Hive_Unknown")
    readings = body.get("readings", None)

    if readings is None:
        return jsonify({
            "error": "Missing 'readings' field.",
            "hint" : "Provide a list of sensor reading dicts."
        }), 400

    if not isinstance(readings, list):
        return jsonify({
            "error": "'readings' must be a list.",
        }), 400

    if len(readings) < 24:
        return jsonify({
            "error"           : f"Insufficient data: {len(readings)} readings provided.",
            "required"        : 24,
            "received"        : len(readings),
            "hint"            : "Send at least 24 consecutive sensor readings."
        }), 422

    # ── Run prediction ────────────────────────────────────────
    try:
        predictor = _get_predictor()
        result    = predictor.predict(hive_id, readings)
        return jsonify(result), 200

    except ValueError as e:
        logger.warning("Validation error in live prediction: %s", e)
        return jsonify({
            "error"  : "Input validation failed.",
            "details": str(e)
        }), 422

    except FileNotFoundError as e:
        logger.error("Model file missing: %s", e)
        return jsonify({
            "error"  : "Model files not found.",
            "details": str(e),
            "hint"   : "Run the LSTM training pipeline to generate model files."
        }), 503

    except Exception as e:
        logger.exception("Unexpected error during prediction.")
        return jsonify({
            "error"  : "Prediction failed due to an internal error.",
            "details": str(e)
        }), 500


# ──────────────────────────────────────────────────────────────
# GET /api/swarming/live-prediction/sample
# ──────────────────────────────────────────────────────────────
@swarming_live_bp.route("/api/swarming/live-prediction/sample", methods=["GET"])
def sample_payload():
    """
    Return a sample request payload that can be POSTed to /live-prediction.
    Useful for testing without a real sensor.
    """
    sample = {
        "hive_id" : "Hive_01",
        "readings": _generate_sample_readings(24)
    }
    return jsonify(sample), 200


# ──────────────────────────────────────────────────────────────
# GET /api/swarming/live-prediction/health
# ──────────────────────────────────────────────────────────────
@swarming_live_bp.route("/api/swarming/live-prediction/health", methods=["GET"])
def prediction_health():
    """Return availability status of the model files."""
    from live_prediction.config import (
        LSTM_MODEL_PATH, SCALER_PATH, LABEL_ENCODER_PATH
    )
    status = {
        "lstm_model_ready"    : os.path.exists(LSTM_MODEL_PATH),
        "scaler_ready"        : os.path.exists(SCALER_PATH),
        "label_encoder_ready" : os.path.exists(LABEL_ENCODER_PATH),
    }
    status["all_ready"] = all(status.values())
    http_code = 200 if status["all_ready"] else 503
    return jsonify(status), http_code
