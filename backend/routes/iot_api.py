import os
import pandas as pd
from flask import Blueprint, jsonify, request
from sqlalchemy import text
from database import get_engine

iot_bp = Blueprint("iot", __name__)

engine = get_engine()

TABLE = os.getenv("IOT_SENSOR_TABLE", "beehive_readings")

HIVE = os.getenv("IOT_HIVE_COLUMN", "device_id")
TIME = os.getenv("IOT_TIMESTAMP_COLUMN", "reading_at")

TEMP = os.getenv("IOT_TEMPERATURE_COLUMN", "internal_temp")
HUM = os.getenv("IOT_HUMIDITY_COLUMN", "internal_humidity")
CO2 = os.getenv("IOT_CO2_COLUMN", "internal_co2")
WEIGHT = os.getenv("IOT_WEIGHT_COLUMN", "total_weight")
EXT_TEMP = os.getenv("IOT_EXTERNAL_TEMPERATURE_COLUMN", "external_temp")
EXT_HUM = os.getenv("IOT_EXTERNAL_HUMIDITY_COLUMN", "external_humidity")
BATTERY = os.getenv("IOT_BATTERY_VOLTAGE_COLUMN", "battery_voltage")


@iot_bp.route("/api/iot/devices", methods=["GET"])
def devices():

    sql = text(f"""
        SELECT DISTINCT {HIVE}
        FROM {TABLE}
        ORDER BY {HIVE}
    """)

    df = pd.read_sql(sql, engine)

    return jsonify({
        "devices": df[HIVE].dropna().tolist()
    })


@iot_bp.route("/api/iot/realtime-data", methods=["GET"])
def realtime():

    device_id = request.args.get("device_id")

    limit = int(request.args.get("limit", 432))

    if not device_id:
        return jsonify({"error": "device_id is required"}), 400

    sql = text(f"""
        SELECT
            {TIME},
            {TEMP},
            {HUM},
            {CO2},
            {WEIGHT},
            {EXT_TEMP},
            {EXT_HUM},
            {BATTERY}
        FROM {TABLE}
        WHERE {HIVE} = :device
        ORDER BY {TIME} DESC
        LIMIT :limit
    """)

    df = pd.read_sql(
        sql,
        engine,
        params={
            "device": device_id,
            "limit": limit,
        },
    )

    df = df.sort_values(TIME)

    return jsonify({
        "readings": df.to_dict(orient="records")
    })