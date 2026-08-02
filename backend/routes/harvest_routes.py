# from pathlib import Path
# import json

# from flask import Blueprint, jsonify, request, send_from_directory

# from services.harvest_service import (
#     get_sample_input,
#     predict_hui
# )

# from services.iot_data_service import (
#     check_database_health,
#     get_available_devices,
#     get_latest_reading,
#     get_recent_readings,
# )

# from services.live_harvest_service import (
#     predict_live_hui,
#     predict_all_live_hives,
# )

# harvest_bp = Blueprint(
#     "harvest",
#     __name__,
#     url_prefix="/api/harvest"
# )



# BACKEND_DIR = Path(__file__).resolve().parent.parent
# HARVEST_OUTPUT_DIR = BACKEND_DIR / "outputs" / "harvest"

# EDA_SUMMARY_FILE = (
#     HARVEST_OUTPUT_DIR /
#     "harvest_eda_summary.json"
# )

# MODEL_RESULTS_FILE = (
#     HARVEST_OUTPUT_DIR /
#     "model_comparison.json"
# )

# HIVE_ANALYSIS_FILE = (
#     HARVEST_OUTPUT_DIR
#     / "harvest_hive_analysis.json"
# )

# @harvest_bp.route("/eda-summary", methods=["GET"])
# def get_eda_summary():
#     if not EDA_SUMMARY_FILE.exists():
#         return jsonify({
#             "error": "Harvest EDA summary not found.",
#             "hint": "Run the harvest pipeline first."
#         }), 404

#     try:
#         with open(
#             EDA_SUMMARY_FILE,
#             "r",
#             encoding="utf-8"
#         ) as file:
#             data = json.load(file)

#         return jsonify(data)

#     except Exception as error:
#         return jsonify({
#             "error": str(error)
#         }), 500


# @harvest_bp.route("/model-results", methods=["GET"])
# def get_model_results():
#     if not MODEL_RESULTS_FILE.exists():
#         return jsonify({
#             "error": "Model-comparison results not found.",
#             "hint": "Run train_hui_models.py first."
#         }), 404

#     try:
#         with open(
#             MODEL_RESULTS_FILE,
#             "r",
#             encoding="utf-8"
#         ) as file:
#             data = json.load(file)

#         return jsonify(data)

#     except Exception as error:
#         return jsonify({
#             "error": str(error)
#         }), 500


# @harvest_bp.route("/images", methods=["GET"])
# def list_images():
#     if not HARVEST_OUTPUT_DIR.exists():
#         return jsonify([])

#     images = sorted(
#         file.name
#         for file in HARVEST_OUTPUT_DIR.glob("*.png")
#     )

#     return jsonify(images)


# @harvest_bp.route(
#     "/images/<path:filename>",
#     methods=["GET"]
# )
# def serve_image(filename):
#     image_path = HARVEST_OUTPUT_DIR / filename

#     if not image_path.exists():
#         return jsonify({
#             "error": f"Harvest image not found: {filename}"
#         }), 404

#     return send_from_directory(
#         str(HARVEST_OUTPUT_DIR),
#         filename
#     )


# @harvest_bp.route("/sample", methods=["GET"])
# def get_sample():
#     try:
#         return jsonify(get_sample_input())

#     except FileNotFoundError as error:
#         return jsonify({
#             "error": str(error)
#         }), 404

#     except Exception as error:
#         return jsonify({
#             "error": str(error)
#         }), 500


# @harvest_bp.route("/predict", methods=["POST"])
# def predict():
#     payload = request.get_json(silent=True)

#     if not payload or not isinstance(payload, dict):
#         return jsonify({
#             "error": "A JSON object containing model inputs is required."
#         }), 400

#     try:
#         return jsonify(predict_hui(payload))

#     except FileNotFoundError as error:
#         return jsonify({
#             "error": str(error)
#         }), 404

#     except ValueError as error:
#         return jsonify({
#             "error": str(error)
#         }), 400

#     except Exception as error:
#         return jsonify({
#             "error": "Prediction failed.",
#             "details": str(error)
#         }), 500
    

# @harvest_bp.route(
#     "/hive-analysis",
#     methods=["GET"]
# )
# def get_hive_analysis():
#     if not HIVE_ANALYSIS_FILE.exists():
#         return jsonify({
#             "error": "Hive harvesting analysis not found.",
#             "hint": "Run the harvest EDA pipeline first."
#         }), 404

#     try:
#         with open(
#             HIVE_ANALYSIS_FILE,
#             "r",
#             encoding="utf-8"
#         ) as file:
#             data = json.load(file)

#         return jsonify(data)

#     except Exception as error:
#         return jsonify({
#             "error": str(error)
#         }), 500

# # ──────────────────────────────────────────────
# # LIVE IOT DATABASE AND HARVEST PREDICTION ROUTES
# # ──────────────────────────────────────────────


# @harvest_bp.route("/live/health", methods=["GET"])
# def live_health():
#     """
#     Check PostgreSQL connectivity and live model availability.

#     Endpoint:
#         GET /api/harvest/live/health
#     """

#     try:
#         result = check_database_health()
#         return jsonify(result), 200

#     except Exception as error:
#         return jsonify({
#             "status": "error",
#             "database_connected": False,
#             "error": str(error)
#         }), 500


# @harvest_bp.route("/live/devices", methods=["GET"])
# def live_devices():
#     """
#     Return all unique IoT device IDs.

#     Endpoint:
#         GET /api/harvest/live/devices
#     """

#     try:
#         devices = get_available_devices()

#         return jsonify({
#             "total_devices": len(devices),
#             "devices": devices
#         }), 200

#     except Exception as error:
#         return jsonify({
#             "error": "Unable to retrieve IoT devices.",
#             "details": str(error)
#         }), 500


# @harvest_bp.route(
#     "/live/latest/<string:device_id>",
#     methods=["GET"]
# )
# def live_latest_reading(device_id):
#     """
#     Return the latest sensor reading for one device.

#     Endpoint:
#         GET /api/harvest/live/latest/<device_id>
#     """

#     try:
#         reading = get_latest_reading(device_id)

#         if reading is None:
#             return jsonify({
#                 "error": "No sensor readings found.",
#                 "device_id": device_id
#             }), 404

#         return jsonify(reading), 200

#     except ValueError as error:
#         return jsonify({
#             "error": str(error)
#         }), 400

#     except Exception as error:
#         return jsonify({
#             "error": "Unable to retrieve latest sensor reading.",
#             "details": str(error)
#         }), 500


# @harvest_bp.route(
#     "/live/history/<string:device_id>",
#     methods=["GET"]
# )
# def live_history(device_id):
#     """
#     Return recent sensor readings for one device.

#     Optional query:
#         ?hours=168

#     Endpoint:
#         GET /api/harvest/live/history/<device_id>?hours=168
#     """

#     try:
#         hours = request.args.get(
#             "hours",
#             default=168,
#             type=int
#         )

#         if hours is None or hours <= 0:
#             return jsonify({
#                 "error": "hours must be a positive integer."
#             }), 400

#         # Protect the API from very large requests.
#         hours = min(hours, 24 * 30)

#         readings = get_recent_readings(
#             device_id=device_id,
#             history_hours=hours
#         )

#         return jsonify({
#             "device_id": device_id,
#             "requested_history_hours": hours,
#             "records": len(readings),
#             "readings": readings
#         }), 200

#     except ValueError as error:
#         return jsonify({
#             "error": str(error)
#         }), 400

#     except Exception as error:
#         return jsonify({
#             "error": "Unable to retrieve IoT history.",
#             "details": str(error)
#         }), 500


# @harvest_bp.route(
#     "/live/predict/<string:device_id>",
#     methods=["GET"]
# )
# def live_predict(device_id):
#     """
#     Predict the current HUI using live IoT data.

#     Optional query:
#         ?hours=168

#     Endpoint:
#         GET /api/harvest/live/predict/<device_id>?hours=168
#     """

#     try:
#         hours = request.args.get(
#             "hours",
#             default=168,
#             type=int
#         )

#         if hours is None or hours <= 0:
#             return jsonify({
#                 "error": "hours must be a positive integer."
#             }), 400

#         result = predict_live_hui(
#             device_id=device_id,
#             history_hours=hours
#         )

#         if not result.get(
#             "prediction_available",
#             False
#         ):
#             return jsonify(result), 422

#         return jsonify(result), 200

#     except FileNotFoundError as error:
#         return jsonify({
#             "error": str(error),
#             "hint": (
#                 "Run backend/ml/"
#                 "train_live_hui_model.py first."
#             )
#         }), 404

#     except ValueError as error:
#         return jsonify({
#             "error": str(error)
#         }), 400

#     except Exception as error:
#         return jsonify({
#             "error": "Live HUI prediction failed.",
#             "details": str(error)
#         }), 500


# @harvest_bp.route(
#     "/live/predict-all",
#     methods=["GET"]
# )
# def live_predict_all():
#     """
#     Predict HUI for every connected hive.

#     Optional query:
#         ?hours=168

#     Endpoint:
#         GET /api/harvest/live/predict-all?hours=168
#     """

#     try:
#         hours = request.args.get(
#             "hours",
#             default=168,
#             type=int
#         )

#         if hours is None or hours <= 0:
#             return jsonify({
#                 "error": "hours must be a positive integer."
#             }), 400

#         results = predict_all_live_hives(
#             history_hours=hours
#         )

#         successful = sum(
#             bool(item.get("prediction_available"))
#             for item in results
#         )

#         return jsonify({
#             "total_devices": len(results),
#             "successful_predictions": successful,
#             "unavailable_predictions": (
#                 len(results) - successful
#             ),
#             "predictions": results
#         }), 200

#     except FileNotFoundError as error:
#         return jsonify({
#             "error": str(error),
#             "hint": (
#                 "Run backend/ml/"
#                 "train_live_hui_model.py first."
#             )
#         }), 404

#     except Exception as error:
#         return jsonify({
#             "error": "Unable to generate live predictions.",
#             "details": str(error)
#         }), 500




"""Harvest REST routes: historical EDA, historical proxy model, and live probability model."""

from pathlib import Path
import json

from flask import Blueprint, jsonify, request, send_from_directory

from services.harvest_service import (
    get_sample_input,
    predict_hui,
)
from services.live_harvest_service import (
    get_live_devices,
    get_live_health,
    get_live_history,
    get_live_latest,
    predict_all_live_hives,
    predict_live_harvest,
)


harvest_bp = Blueprint(
    "harvest",
    __name__,
    url_prefix="/api/harvest",
)


BACKEND_DIR = Path(__file__).resolve().parent.parent
HARVEST_OUTPUT_DIR = (
    BACKEND_DIR / "outputs" / "harvest"
)

EDA_SUMMARY_FILE = (
    HARVEST_OUTPUT_DIR
    / "harvest_eda_summary.json"
)
MODEL_RESULTS_FILE = (
    HARVEST_OUTPUT_DIR
    / "model_comparison.json"
)
CLASSIFIER_RESULTS_FILE = (
    HARVEST_OUTPUT_DIR
    / "harvest_classifier_comparison.json"
)
HIVE_ANALYSIS_FILE = (
    HARVEST_OUTPUT_DIR
    / "harvest_hive_analysis.json"
)


@harvest_bp.route(
    "/eda-summary",
    methods=["GET"],
)
def get_eda_summary():
    if not EDA_SUMMARY_FILE.exists():
        return jsonify(
            {
                "error": (
                    "Harvest EDA summary "
                    "not found."
                ),
                "hint": (
                    "Run the harvest EDA "
                    "pipeline first."
                ),
            }
        ), 404

    try:
        with EDA_SUMMARY_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            return jsonify(json.load(file))
    except Exception as error:
        return jsonify(
            {"error": str(error)}
        ), 500


@harvest_bp.route(
    "/model-results",
    methods=["GET"],
)
def get_model_results():
    if not MODEL_RESULTS_FILE.exists():
        return jsonify(
            {
                "error": (
                    "Proxy HUI model results "
                    "not found."
                ),
                "hint": (
                    "Run train_hui_models.py "
                    "first."
                ),
            }
        ), 404

    try:
        with MODEL_RESULTS_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            return jsonify(json.load(file))
    except Exception as error:
        return jsonify(
            {"error": str(error)}
        ), 500


@harvest_bp.route(
    "/classifier-results",
    methods=["GET"],
)
def get_classifier_results():
    if not CLASSIFIER_RESULTS_FILE.exists():
        return jsonify(
            {
                "error": (
                    "Harvest classifier "
                    "results not found."
                ),
                "hint": (
                    "Run python backend/ml/"
                    "train_harvest_classifier.py"
                ),
            }
        ), 404

    try:
        with CLASSIFIER_RESULTS_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            return jsonify(json.load(file))
    except Exception as error:
        return jsonify(
            {"error": str(error)}
        ), 500


@harvest_bp.route(
    "/images",
    methods=["GET"],
)
def list_images():
    if not HARVEST_OUTPUT_DIR.exists():
        return jsonify([])

    images = sorted(
        file.name
        for file
        in HARVEST_OUTPUT_DIR.glob("*.png")
    )
    return jsonify(images)


@harvest_bp.route(
    "/images/<path:filename>",
    methods=["GET"],
)
def serve_harvest_image(filename):
    image_path = (
        HARVEST_OUTPUT_DIR / filename
    )

    if not image_path.exists():
        return jsonify(
            {
                "error": (
                    "Harvest image not "
                    f"found: {filename}"
                )
            }
        ), 404

    return send_from_directory(
        str(HARVEST_OUTPUT_DIR),
        filename,
    )


@harvest_bp.route(
    "/sample",
    methods=["GET"],
)
def get_sample():
    try:
        return jsonify(get_sample_input())
    except FileNotFoundError as error:
        return jsonify(
            {"error": str(error)}
        ), 404
    except Exception as error:
        return jsonify(
            {"error": str(error)}
        ), 500


@harvest_bp.route(
    "/predict",
    methods=["POST"],
)
def predict_proxy_hui():
    payload = request.get_json(silent=True)

    if (
        not payload
        or not isinstance(payload, dict)
    ):
        return jsonify(
            {
                "error": (
                    "A JSON object containing "
                    "model inputs is required."
                )
            }
        ), 400

    try:
        return jsonify(predict_hui(payload))
    except FileNotFoundError as error:
        return jsonify(
            {"error": str(error)}
        ), 404
    except ValueError as error:
        return jsonify(
            {"error": str(error)}
        ), 400
    except Exception as error:
        return jsonify(
            {
                "error": (
                    "Proxy HUI prediction failed."
                ),
                "details": str(error),
            }
        ), 500


@harvest_bp.route(
    "/hive-analysis",
    methods=["GET"],
)
def get_hive_analysis():
    if not HIVE_ANALYSIS_FILE.exists():
        return jsonify(
            {
                "error": (
                    "Hive harvesting analysis "
                    "not found."
                ),
                "hint": (
                    "Run the harvest EDA "
                    "pipeline first."
                ),
            }
        ), 404

    try:
        with HIVE_ANALYSIS_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            return jsonify(json.load(file))
    except Exception as error:
        return jsonify(
            {"error": str(error)}
        ), 500


@harvest_bp.route(
    "/live/health",
    methods=["GET"],
)
def live_health():
    try:
        return jsonify(
            get_live_health()
        ), 200
    except Exception as error:
        return jsonify(
            {
                "status": "error",
                "error": str(error),
            }
        ), 500


@harvest_bp.route(
    "/live/devices",
    methods=["GET"],
)
def live_devices():
    try:
        devices = get_live_devices()
        return jsonify(
            {
                "total_devices": len(devices),
                "devices": devices,
            }
        ), 200
    except Exception as error:
        return jsonify(
            {
                "error": (
                    "Unable to retrieve "
                    "IoT devices."
                ),
                "details": str(error),
            }
        ), 500


@harvest_bp.route(
    "/live/latest/<string:device_id>",
    methods=["GET"],
)
def live_latest(device_id):
    try:
        return jsonify(
            get_live_latest(device_id)
        ), 200
    except ValueError as error:
        return jsonify(
            {"error": str(error)}
        ), 404
    except Exception as error:
        return jsonify(
            {
                "error": (
                    "Unable to retrieve the "
                    "latest reading."
                ),
                "details": str(error),
            }
        ), 500


@harvest_bp.route(
    "/live/history/<string:device_id>",
    methods=["GET"],
)
def live_history(device_id):
    hours = request.args.get(
        "hours",
        default=168,
        type=int,
    )

    if hours is None or hours <= 0:
        return jsonify(
            {
                "error": (
                    "hours must be a positive "
                    "integer."
                )
            }
        ), 400

    try:
        return jsonify(
            get_live_history(
                device_id,
                history_hours=min(
                    hours,
                    24 * 365,
                ),
            )
        ), 200
    except ValueError as error:
        return jsonify(
            {"error": str(error)}
        ), 404
    except Exception as error:
        return jsonify(
            {
                "error": (
                    "Unable to retrieve live "
                    "sensor history."
                ),
                "details": str(error),
            }
        ), 500


@harvest_bp.route(
    "/live/predict/<string:device_id>",
    methods=["GET"],
)
def live_predict(device_id):
    hours = request.args.get(
        "hours",
        default=168,
        type=int,
    )

    if hours is None or hours <= 0:
        return jsonify(
            {
                "error": (
                    "hours must be a positive "
                    "integer."
                )
            }
        ), 400

    try:
        result = predict_live_harvest(
            device_id,
            history_hours=min(
                hours,
                24 * 365,
            ),
        )

        status_code = (
            200
            if result.get(
                "prediction_available"
            )
            else 422
        )

        return jsonify(result), status_code

    except FileNotFoundError as error:
        return jsonify(
            {
                "error": str(error),
                "hint": (
                    "Run python backend/ml/"
                    "train_harvest_classifier.py"
                ),
            }
        ), 404
    except ValueError as error:
        return jsonify(
            {"error": str(error)}
        ), 400
    except Exception as error:
        return jsonify(
            {
                "error": (
                    "Live harvest prediction "
                    "failed."
                ),
                "details": str(error),
            }
        ), 500


@harvest_bp.route(
    "/live/predict-all",
    methods=["GET"],
)
def live_predict_all():
    hours = request.args.get(
        "hours",
        default=168,
        type=int,
    )

    if hours is None or hours <= 0:
        return jsonify(
            {
                "error": (
                    "hours must be a positive "
                    "integer."
                )
            }
        ), 400

    try:
        predictions = (
            predict_all_live_hives(
                history_hours=min(
                    hours,
                    24 * 365,
                )
            )
        )

        successful = sum(
            bool(
                item.get(
                    "prediction_available"
                )
            )
            for item in predictions
        )

        return jsonify(
            {
                "total_devices": (
                    len(predictions)
                ),
                "successful_predictions": (
                    successful
                ),
                "unavailable_predictions": (
                    len(predictions)
                    - successful
                ),
                "predictions": predictions,
            }
        ), 200
    except Exception as error:
        return jsonify(
            {
                "error": (
                    "Unable to generate live "
                    "predictions."
                ),
                "details": str(error),
            }
        ), 500
