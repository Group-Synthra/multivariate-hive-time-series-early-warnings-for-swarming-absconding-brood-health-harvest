"""Flask routes for live IoT harvest monitoring and HUI prediction."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.live_harvest_service import (
    get_live_devices,
    get_live_health,
    get_live_history,
    get_live_latest,
    predict_all_live_hives,
    predict_live_hui,
)

live_harvest_bp = Blueprint(
    "live_harvest",
    __name__,
    url_prefix="/api/harvest/live",
)


def _history_hours_from_request(default: int = 168) -> int:
    raw = request.args.get("hours", str(default))
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError("Query parameter 'hours' must be an integer.") from error

    if value <= 0 or value > 8760:
        raise ValueError("Query parameter 'hours' must be between 1 and 8760.")
    return value


@live_harvest_bp.route("/health", methods=["GET"])
def health():
    try:
        return jsonify(get_live_health())
    except Exception as error:
        return jsonify({"database_connected": False, "error": str(error)}), 500


@live_harvest_bp.route("/devices", methods=["GET"])
def devices():
    try:
        return jsonify({"devices": get_live_devices()})
    except Exception as error:
        return jsonify({"error": str(error)}), 500


@live_harvest_bp.route("/latest/<string:device_id>", methods=["GET"])
def latest(device_id: str):
    try:
        return jsonify(get_live_latest(device_id))
    except ValueError as error:
        return jsonify({"error": str(error)}), 404
    except Exception as error:
        return jsonify({"error": str(error)}), 500


@live_harvest_bp.route("/history/<string:device_id>", methods=["GET"])
def history(device_id: str):
    try:
        hours = _history_hours_from_request()
        return jsonify(get_live_history(device_id, history_hours=hours))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": str(error)}), 500


@live_harvest_bp.route("/predict/<string:device_id>", methods=["GET"])
def predict(device_id: str):
    try:
        hours = _history_hours_from_request()
        result = predict_live_hui(device_id, history_hours=hours)
        status_code = 200 if result.get("prediction_available") else 422
        return jsonify(result), status_code
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 404
    except Exception as error:
        return jsonify({"error": "Live prediction failed.", "details": str(error)}), 500


@live_harvest_bp.route("/predict-all", methods=["GET"])
def predict_all():
    try:
        hours = _history_hours_from_request()
        return jsonify(predict_all_live_hives(history_hours=hours))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 404
    except Exception as error:
        return jsonify({"error": "Live prediction failed.", "details": str(error)}), 500
