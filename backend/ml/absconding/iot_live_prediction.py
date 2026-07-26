"""
Real-time IoT live prediction service for Module 03 — Absconding Behaviour Prediction.

This file connects the already-trained absconding model with live IoT readings.
It is designed for the final verification stage where ONE hive sends readings every
10 minutes to a Supabase PostgreSQL database.

Live flow:
    Supabase/PostgreSQL IoT row -> same feature engineering -> saved model
    -> next-24h risk probability -> ARM -> early warning notification -> dashboard

Supported live data sources:
    1) Supabase PostgreSQL / PostgreSQL: IOT_DATA_SOURCE=postgres
    2) Local CSV fallback: backend/data/iot_live_readings.csv
    3) HTTP/REST JSON endpoint: IOT_DATA_SOURCE=http and IOT_DATA_URL=...
    4) Manual POST test ingestion through /api/absconding/iot/ingest

Security note:
    Do not hardcode database credentials in this file. Keep SUPABASE_DB_URL in
    environment variables or backend/.env, and do not commit it to GitHub.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import joblib
import numpy as np
import pandas as pd

try:
    import requests
except Exception:  # requests is optional until HTTP source is used
    requests = None

try:
    import psycopg2
    from psycopg2 import sql
except Exception:  # psycopg2 is optional until PostgreSQL source is used
    psycopg2 = None
    sql = None

from backend.ml.absconding.absconding_pipeline import (
    AbscondingConfig,
    add_aliases_and_clean,
    add_predictions_and_arm,
    arm_trend_label,
    BASE_FEATURES,
    engineer_features,
    explanations_for_row,
    predict_proba,
    risk_level,
)

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = BACKEND_DIR / "outputs" / "absconding"
DEFAULT_IOT_CSV = BACKEND_DIR / "data" / "iot_live_readings.csv"

# IoT collection interval: user requirement = every 10 minutes.
IOT_INTERVAL_MINUTES = int(os.getenv("IOT_INTERVAL_MINUTES", "10"))
RECORDS_PER_HOUR = max(1, int(round(60 / IOT_INTERVAL_MINUTES)))
RECORDS_PER_24H = 24 * RECORDS_PER_HOUR       # 144 rows when interval is 10 minutes
RECORDS_PER_72H = 72 * RECORDS_PER_HOUR       # 432 rows when interval is 10 minutes
DEFAULT_POSTGRES_LIMIT = int(os.getenv("IOT_POSTGRES_LIMIT", str(max(600, RECORDS_PER_72H))))

# Flexible column candidates. You can override every one of these using env variables.
DEFAULT_COLUMN_CANDIDATES = {
    "timestamp": ["timestamp", "created_at", "recorded_at", "time", "datetime", "date_time"],
    "hive_id": ["hive_id", "hive", "device_id", "sensor_id", "node_id"],
    "temperature": ["temperature", "temperature_c", "temp", "temp_c", "internal_temperature_c", "internal_temp"],
    "humidity": ["humidity", "humidity_pct", "internal_humidity_pct", "internal_humidity", "relative_humidity"],
    "co2": ["co2", "co2_ppm", "co2_value", "carbon_dioxide", "internal_co2"],
    "weight": ["weight", "weight_kg", "hive_weight_kg", "load_cell_weight", "mass_kg", "total_weight"],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_any(names: Sequence[str], default: str = "") -> str:
    """Read the first non-empty environment variable from a list of accepted names."""
    for name in names:
        value = _env(name)
        if value:
            return value
    return default


def _add_sslmode_require(db_url: str) -> str:
    """Supabase pooler normally requires SSL. Add sslmode=require if missing."""
    if "sslmode=" in db_url:
        return db_url
    parsed = urlparse(db_url)
    query = dict(parse_qsl(parsed.query))
    query.setdefault("sslmode", _env("DATABASE_SSLMODE", "require") or "require")
    return urlunparse(parsed._replace(query=urlencode(query)))


def _safe_public_db_url() -> str:
    """Return a redacted DB URL for dashboard diagnostics."""
    db_url = _env_any(["SUPABASE_DB_URL", "DATABASE_URL", "POSTGRES_URL"])
    if not db_url:
        return "not configured"
    parsed = urlparse(db_url)
    host = parsed.hostname or "host"
    return f"{parsed.scheme}://***:***@{host}:{parsed.port or 5432}/{(parsed.path or '/postgres').lstrip('/')}"


def latest_model_path(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    """Return newest saved absconding model bundle."""
    model_dir = output_dir / "models"
    candidates = sorted(model_dir.glob("absconding_*_model.joblib"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(
            "No trained absconding model found. Run: "
            "python backend/scripts/run_absconding.py --model rf --target absconding_label_next_24h --compare-models"
        )
    return candidates[0]


def normalize_iot_record(record: Dict[str, Any], default_hive_id: str = "Hive_IoT_01") -> Dict[str, Any]:
    """
    Normalize one IoT reading into the same dataset schema used by training.

    Accepts flexible keys from ESP32/API/database:
      temperature | temp | internal_temperature_c
      humidity | internal_humidity_pct
      co2 | co2_ppm
      weight | hive_weight_kg
    """
    def first_value(keys: List[str], default=None):
        for key in keys:
            if key in record and record[key] not in [None, ""]:
                return record[key]
        return default

    timestamp = first_value(["timestamp", "created_at", "recorded_at", "reading_at", "time", "datetime"], _now_iso())
    hive_id = first_value(["hive_id", "hive", "device_id", "sensor_id"], default_hive_id)

    return {
        "timestamp": timestamp,
        "hive_id": str(hive_id),
        "internal_temperature_c": first_value(["internal_temperature_c", "internal_temp", "temperature", "temp", "temperature_c", "temp_c"], np.nan),
        "internal_humidity_pct": first_value(["internal_humidity_pct", "internal_humidity", "humidity", "humidity_pct", "relative_humidity"], np.nan),
        "co2_ppm": first_value(["co2_ppm", "internal_co2", "co2", "co2_value", "carbon_dioxide"], np.nan),
        "hive_weight_kg": first_value(["hive_weight_kg", "total_weight", "weight", "weight_kg", "load_cell_weight", "mass_kg"], np.nan),
        # Optional weather/proxy fields. Keep defaults so existing feature code works.
        "external_temperature_c": first_value(["external_temperature_c", "external_temp"], 0.0),
        "external_humidity_pct": first_value(["external_humidity_pct", "external_humidity"], 0.0),
        "battery_voltage": first_value(["battery_voltage"], np.nan),
        "rainfall_mm_hour": first_value(["rainfall_mm_hour", "rainfall"], 0.0),
        "wind_speed_mps": first_value(["wind_speed_mps", "wind_speed"], 0.0),
        "nectar_flow_season_proxy": first_value(["nectar_flow_season_proxy"], 0.0),
        "dearth_season_proxy": first_value(["dearth_season_proxy"], 0.0),
        "monsoon_rain_period_proxy": first_value(["monsoon_rain_period_proxy"], 0.0),
    }


def append_iot_reading(record: Dict[str, Any], csv_path: Path = DEFAULT_IOT_CSV) -> Dict[str, Any]:
    """
    Append one live IoT reading to a local CSV buffer.

    This is useful before/alongside the final database connection. Your IoT device,
    Postman, or frontend test button can POST a reading to /api/absconding/iot/ingest,
    and this function stores it locally.
    """
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_iot_record(record)
    df_new = pd.DataFrame([normalized])
    if csv_path.exists():
        old = pd.read_csv(csv_path)
        out = pd.concat([old, df_new], ignore_index=True)
    else:
        out = df_new
    out.to_csv(csv_path, index=False)
    return normalized


def _read_http_json(url: str) -> pd.DataFrame:
    if requests is None:
        raise RuntimeError("requests is not installed. Run: pip install requests")
    headers = {}
    token = _env("IOT_DATA_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()

    # Firebase Realtime Database often returns {id: {reading}, id2: {reading}}
    if isinstance(data, dict):
        if all(isinstance(v, dict) for v in data.values()):
            rows = list(data.values())
        else:
            rows = [data]
    elif isinstance(data, list):
        rows = data
    else:
        raise ValueError("HTTP IoT endpoint must return a JSON object or list of objects.")

    normalized = [normalize_iot_record(row, _env("IOT_HIVE_ID", "Hive_IoT_01")) for row in rows]
    return pd.DataFrame(normalized)


def _connect_postgres():
    if psycopg2 is None:
        raise RuntimeError("psycopg2-binary is not installed. Run: pip install psycopg2-binary")
    db_url = _env_any(["SUPABASE_DB_URL", "DATABASE_URL", "POSTGRES_URL"])
    if not db_url:
        raise ValueError(
            "DATABASE_URL is not set. Put your Supabase PostgreSQL URL in backend/.env "
            "or set DATABASE_URL/SUPABASE_DB_URL in PowerShell before running backend/app.py."
        )
    return psycopg2.connect(_add_sslmode_require(db_url), connect_timeout=15)


def _postgres_table_columns(conn, schema: str, table: str) -> List[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, table),
        )
        return [r[0] for r in cur.fetchall()]


def _list_public_tables(conn, schema: str) -> List[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """,
            (schema,),
        )
        return [r[0] for r in cur.fetchall()]


def _resolve_column(columns: Sequence[str], role: str, env_name: str, required: bool = True) -> Optional[str]:
    """Resolve a database column by env override first, then known candidate names."""
    lower_to_actual = {c.lower(): c for c in columns}
    override = _env(env_name)
    candidates = []
    if override:
        candidates.append(override)
    candidates.extend(DEFAULT_COLUMN_CANDIDATES[role])

    for c in candidates:
        if c in columns:
            return c
        if c.lower() in lower_to_actual:
            return lower_to_actual[c.lower()]

    if required:
        raise ValueError(
            f"Could not find {role} column. Available columns: {list(columns)}. "
            f"Set {env_name} to the correct column name."
        )
    return None


def _table_score(columns: Sequence[str]) -> int:
    """Score a table by how many required IoT roles it appears to contain."""
    score = 0
    lowered = {c.lower() for c in columns}
    for role in ["timestamp", "temperature", "humidity", "co2", "weight"]:
        if any(c.lower() in lowered for c in DEFAULT_COLUMN_CANDIDATES[role]):
            score += 1
    return score


def _auto_discover_iot_table(conn, schema: str) -> Tuple[str, List[str]]:
    tables = _list_public_tables(conn, schema)
    scored: List[Tuple[int, str, List[str]]] = []
    for table in tables:
        cols = _postgres_table_columns(conn, schema, table)
        score = _table_score(cols)
        if score >= 4:
            scored.append((score, table, cols))
    if not scored:
        raise ValueError(
            "IOT_TABLE is not set and no compatible IoT table was auto-detected. "
            "Set IOT_TABLE and the column env variables. Available tables: " + ", ".join(tables[:30])
        )
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return scored[0][1], scored[0][2]


def _read_postgres_iot_rows(limit: int = DEFAULT_POSTGRES_LIMIT) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Read latest live IoT rows from Supabase PostgreSQL/PostgreSQL.

    Required env:
        SUPABASE_DB_URL
        IOT_DATA_SOURCE=postgres

    Recommended env:
        IOT_SENSOR_TABLE=<your table name>       # screenshot style
        IOT_TIMESTAMP_COLUMN=<timestamp column> # screenshot style
        IOT_TEMPERATURE_COLUMN=<temperature column>
        IOT_HUMIDITY_COLUMN=<humidity column>
        IOT_CO2_COLUMN=<co2 column>
        IOT_WEIGHT_COLUMN=<weight column>
        IOT_HIVE_COLUMN=<hive/device column, optional if one hive>
        IOT_HIVE_ID=<one verification hive id, optional>

    Old aliases are also accepted: IOT_TABLE, IOT_TIMESTAMP_COL, IOT_TEMP_COL,
    IOT_HUMIDITY_COL, IOT_CO2_COL, IOT_WEIGHT_COL, IOT_HIVE_COL.
    """
    schema = _env("IOT_SCHEMA", "public")
    table = _env_any(["IOT_SENSOR_TABLE", "IOT_TABLE"])
    hive_filter = _env_any(["IOT_HIVE_ID", "IOT_DEVICE_ID"])

    with _connect_postgres() as conn:
        if table:
            columns = _postgres_table_columns(conn, schema, table)
            if not columns:
                available_tables = _list_public_tables(conn, schema)
                raise ValueError(
                    f"Table {schema}.{table} was not found or has no readable columns. "
                    f"Available tables: {available_tables[:30]}"
                )
        else:
            table, columns = _auto_discover_iot_table(conn, schema)

        # Accept both old variable names and the .env names shown in your screenshot.
        os.environ.setdefault("IOT_TIMESTAMP_COL", _env_any(["IOT_TIMESTAMP_COLUMN", "IOT_READING_AT_COLUMN"]))
        os.environ.setdefault("IOT_HIVE_COL", _env_any(["IOT_HIVE_COLUMN"]))
        os.environ.setdefault("IOT_TEMP_COL", _env_any(["IOT_TEMPERATURE_COLUMN"]))
        os.environ.setdefault("IOT_HUMIDITY_COL", _env_any(["IOT_HUMIDITY_COLUMN"]))
        os.environ.setdefault("IOT_CO2_COL", _env_any(["IOT_CO2_COLUMN"]))
        os.environ.setdefault("IOT_WEIGHT_COL", _env_any(["IOT_WEIGHT_COLUMN"]))

        ts_col = _resolve_column(columns, "timestamp", "IOT_TIMESTAMP_COL")
        hive_col = _resolve_column(columns, "hive_id", "IOT_HIVE_COL", required=False)
        temp_col = _resolve_column(columns, "temperature", "IOT_TEMP_COL")
        humidity_col = _resolve_column(columns, "humidity", "IOT_HUMIDITY_COL")
        co2_col = _resolve_column(columns, "co2", "IOT_CO2_COL")
        weight_col = _resolve_column(columns, "weight", "IOT_WEIGHT_COL")
        external_temp_col = _env_any(["IOT_EXTERNAL_TEMPERATURE_COLUMN", "IOT_EXTERNAL_TEMP_COL"])
        external_humidity_col = _env_any(["IOT_EXTERNAL_HUMIDITY_COLUMN", "IOT_EXTERNAL_HUMIDITY_COL"])
        battery_voltage_col = _env_any(["IOT_BATTERY_VOLTAGE_COLUMN"])

        selected = [
            sql.SQL("{} AS timestamp").format(sql.Identifier(ts_col)),
            sql.SQL("{} AS internal_temperature_c").format(sql.Identifier(temp_col)),
            sql.SQL("{} AS internal_humidity_pct").format(sql.Identifier(humidity_col)),
            sql.SQL("{} AS co2_ppm").format(sql.Identifier(co2_col)),
            sql.SQL("{} AS hive_weight_kg").format(sql.Identifier(weight_col)),
        ]
        if external_temp_col and external_temp_col in columns:
            selected.append(sql.SQL("{} AS external_temperature_c").format(sql.Identifier(external_temp_col)))
        if external_humidity_col and external_humidity_col in columns:
            selected.append(sql.SQL("{} AS external_humidity_pct").format(sql.Identifier(external_humidity_col)))
        if battery_voltage_col and battery_voltage_col in columns:
            selected.append(sql.SQL("{} AS battery_voltage").format(sql.Identifier(battery_voltage_col)))

        if hive_col:
            selected.insert(1, sql.SQL("{} AS hive_id").format(sql.Identifier(hive_col)))
        else:
            selected.insert(1, sql.Literal(hive_filter or "Hive_IoT_01") + sql.SQL(" AS hive_id"))

        query = sql.SQL("SELECT {} FROM {}.{}").format(
            sql.SQL(", ").join(selected),
            sql.Identifier(schema),
            sql.Identifier(table),
        )
        params: List[Any] = []
        if hive_col and hive_filter:
            query += sql.SQL(" WHERE {} = %s").format(sql.Identifier(hive_col))
            params.append(hive_filter)
        query += sql.SQL(" ORDER BY {} DESC LIMIT %s").format(sql.Identifier(ts_col))
        params.append(int(limit))

        df = pd.read_sql_query(query.as_string(conn), conn, params=params)

    metadata = {
        "source": "supabase_postgres",
        "database_url": _safe_public_db_url(),
        "schema": schema,
        "table": table,
        "env_table_variable_used": "IOT_SENSOR_TABLE/IOT_TABLE",
        "hive_filter": hive_filter or "all/latest one hive",
        "columns": {
            "timestamp": ts_col,
            "hive_id": hive_col or "constant Hive_IoT_01",
            "temperature": temp_col,
            "humidity": humidity_col,
            "co2": co2_col,
            "weight": weight_col,
            "external_temperature": external_temp_col if external_temp_col in columns else None,
            "external_humidity": external_humidity_col if external_humidity_col in columns else None,
            "battery_voltage": battery_voltage_col if battery_voltage_col in columns else None,
        },
        "limit": int(limit),
    }
    return df.iloc[::-1].reset_index(drop=True), metadata


def get_live_iot_dataframe(csv_path: Path = DEFAULT_IOT_CSV) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Load live IoT readings from PostgreSQL, HTTP, or CSV.

    For Supabase PostgreSQL:
        IOT_DATA_SOURCE=postgres
        SUPABASE_DB_URL=postgresql://...
    """
    # If DATABASE_URL exists and IOT_DATA_SOURCE is not explicitly set, use PostgreSQL automatically.
    default_source = "postgres" if _env_any(["DATABASE_URL", "SUPABASE_DB_URL", "POSTGRES_URL"]) else "csv"
    source = _env("IOT_DATA_SOURCE", default_source).lower()
    metadata: Dict[str, Any]

    if source in ["postgres", "postgresql", "supabase", "supabase_postgres"]:
        df, metadata = _read_postgres_iot_rows(DEFAULT_POSTGRES_LIMIT)
    elif source in ["http", "firebase", "rest"]:
        url = _env("IOT_DATA_URL")
        if not url:
            raise ValueError("IOT_DATA_SOURCE is HTTP but IOT_DATA_URL is empty.")
        df = _read_http_json(url)
        metadata = {"source": "http", "url": url}
    else:
        if not csv_path.exists():
            raise FileNotFoundError(
                f"No IoT live data found at {csv_path}. "
                "POST data to /api/absconding/iot/ingest, create backend/data/iot_live_readings.csv, "
                "or set IOT_DATA_SOURCE=postgres with SUPABASE_DB_URL."
            )
        df = pd.read_csv(csv_path)
        df = pd.DataFrame([normalize_iot_record(r, _env("IOT_HIVE_ID", "Hive_IoT_01")) for r in df.to_dict(orient="records")])
        metadata = {"source": "csv", "path": str(csv_path)}

    if df.empty:
        raise ValueError("IoT live data source returned no records.")

    # Normalize again so PostgreSQL/HTTP/CSV all end with the exact training schema.
    df = pd.DataFrame([normalize_iot_record(r, _env("IOT_HIVE_ID", "Hive_IoT_01")) for r in df.to_dict(orient="records")])
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"])
    if df.empty:
        raise ValueError("IoT live data has no valid timestamps.")

    for col in ["internal_temperature_c", "internal_humidity_pct", "co2_ppm", "hive_weight_kg"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["internal_temperature_c", "internal_humidity_pct", "co2_ppm", "hive_weight_kg"])
    if df.empty:
        raise ValueError("IoT live data has no complete sensor rows after cleaning.")

    # One verification hive only. If more hives appear and IOT_HIVE_ID is not set, use the most recently updated hive.
    hive_filter = _env("IOT_HIVE_ID")
    if hive_filter:
        df = df[df["hive_id"].astype(str) == hive_filter]
        if df.empty:
            raise ValueError(f"No IoT records found for IOT_HIVE_ID={hive_filter}")
    else:
        latest_hive = df.sort_values("timestamp").iloc[-1]["hive_id"]
        df = df[df["hive_id"].astype(str) == str(latest_hive)]

    return df.sort_values(["hive_id", "timestamp"]).reset_index(drop=True), metadata


def _recommended_action(level: str, prob: float, arm: float, factors: List[Dict[str, Any]]) -> str:
    factor_text = ", ".join([f["factor"] for f in factors[:3]]) or "combined risk pattern"
    if level == "High":
        return (
            "Immediate inspection recommended within 24 hours. Check queen status, food stores, pests, "
            f"ventilation, and disturbance. Main triggers: {factor_text}."
        )
    if level == "Medium" and arm > 0.04:
        return (
            "Early warning: risk is increasing. Monitor the hive closely and inspect ventilation, food stores, "
            f"and colony activity. Main triggers: {factor_text}."
        )
    if level == "Medium":
        return "Monitor closely during the next readings. Risk is moderate but not critical yet."
    return "Normal monitoring. Continue collecting IoT readings every 10 minutes."


def predict_live_iot_absconding(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    csv_path: Path = DEFAULT_IOT_CSV,
    timeline_records: int = RECORDS_PER_24H,
) -> Dict[str, Any]:
    """
    Main function used by /api/absconding/iot/live.

    It predicts next-24h warning status using the newest trained model and the latest
    IoT rolling window from the one verification hive.
    """
    model_path = latest_model_path(output_dir)
    bundle = joblib.load(model_path)
    model = bundle["model"]
    features = bundle.get("features", BASE_FEATURES)
    cfg_dict = bundle.get("config", {})
    cfg = AbscondingConfig(**cfg_dict) if cfg_dict else AbscondingConfig("", str(output_dir))

    raw, source_metadata = get_live_iot_dataframe(csv_path)

    # Keep enough history for rolling features. With 10-minute IoT readings:
    # 24h = 144 records, 72h = 432 records.
    live_history = raw.groupby("hive_id", sort=False).tail(max(RECORDS_PER_72H, timeline_records)).copy()
    df = engineer_features(add_aliases_and_clean(live_history))

    # Ensure all model features exist, even if the IoT source does not have optional weather fields.
    for col in features:
        if col not in df.columns:
            df[col] = 0.0
    X = df[features].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0)

    probabilities = predict_proba(model, X)
    df_pred = add_predictions_and_arm(df, probabilities)
    latest = df_pred.sort_values(["hive_id", "timestamp"]).groupby("hive_id", sort=False).tail(1).iloc[-1]

    prob = float(latest["absconding_risk_probability"])
    arm = float(latest["arm"])
    level = risk_level(prob, arm, cfg.medium_threshold, cfg.alert_threshold, cfg.arm_alert_threshold)
    trend = arm_trend_label(arm)
    factors = explanations_for_row(latest)

    # Next-day warning rule: notify if high probability OR medium-high probability with increasing ARM.
    high_or_escalating = level == "High" or (prob >= 0.55 and arm >= cfg.arm_alert_threshold)
    notification = {
        "should_notify": bool(high_or_escalating),
        "title": "Absconding Early Warning — Next 24 Hours" if high_or_escalating else "Absconding Risk Normal",
        "message": (
            f"{latest['hive_id']} has {prob*100:.1f}% predicted absconding risk within the next 24 hours. "
            f"ARM trend: {trend}. Action: {_recommended_action(level, prob, arm, factors)}"
            if high_or_escalating else
            f"{latest['hive_id']} is currently {level.lower()} risk ({prob*100:.1f}%). Continue monitoring."
        ),
        "risk_level": level,
        "risk_percentage": round(prob * 100, 2),
        "arm": round(arm, 4),
        "arm_trend": trend,
    }

    timeline = []
    for _, row in df_pred.tail(timeline_records).iterrows():
        timeline.append({
            "timestamp": str(row["timestamp"]),
            "temperature_c": round(float(row["temp"]), 2),
            "humidity_pct": round(float(row["humidity"]), 2),
            "co2_ppm": round(float(row["co2"]), 2),
            "weight_kg": round(float(row["weight"]), 2),
            "risk_percentage": round(float(row["risk_percentage"]), 2),
            "arm": round(float(row["arm"]), 4),
            "environmental_stress_score": round(float(row.get("environmental_stress_score", 0)), 4),
            "weight_change_24h": round(float(row.get("weight_change_24h", 0)), 3),
            "co2_change_24h": round(float(row.get("co2_change_24h", 0)), 3),
        })

    last_time = pd.to_datetime(latest["timestamp"], utc=True)
    age_minutes = None
    try:
        age_minutes = round((pd.Timestamp.now(tz="UTC") - last_time).total_seconds() / 60, 1)
    except Exception:
        pass

    result = {
        "mode": "real_time_iot",
        "status": "ok",
        "data_source": source_metadata,
        "hive_id": str(latest["hive_id"]),
        "prediction_window": "next_24_hours",
        "sampling_interval_minutes": IOT_INTERVAL_MINUTES,
        "expected_records_for_24h": RECORDS_PER_24H,
        "records_available": int(len(raw)),
        "records_used_for_prediction": int(len(df)),
        "last_updated": str(latest["timestamp"]),
        "data_age_minutes": age_minutes,
        "active_model_path": str(model_path),
        "active_model_name": cfg.model_type,
        "trained_target_column": cfg.target_column,
        "risk_probability": round(prob, 4),
        "risk_percentage": round(prob * 100, 2),
        "risk_level": level,
        "arm": round(arm, 4),
        "arm_trend": trend,
        "notification": notification,
        "recommended_action": _recommended_action(level, prob, arm, factors),
        "latest_sensor_readings": {
            "temperature_c": round(float(latest["temp"]), 2),
            "humidity_pct": round(float(latest["humidity"]), 2),
            "co2_ppm": round(float(latest["co2"]), 2),
            "weight_kg": round(float(latest["weight"]), 2),
            "environmental_stress_score": round(float(latest.get("environmental_stress_score", 0)), 4),
            "weight_change_24h": round(float(latest.get("weight_change_24h", 0)), 3),
            "co2_change_24h": round(float(latest.get("co2_change_24h", 0)), 3),
        },
        "key_factors": factors,
        "timeline": timeline,
        "live_note": (
            "The model is trained offline. Supabase IoT readings are used for live inference only. "
            "After collecting enough real IoT labels, retrain periodically for better local accuracy."
        ),
    }

    # Save latest live result so the dashboard can still show the last state if database temporarily disconnects.
    live_out = output_dir / "predictions" / "iot_live_latest.json"
    live_out.parent.mkdir(parents=True, exist_ok=True)
    live_out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
