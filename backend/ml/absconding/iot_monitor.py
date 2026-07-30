"""
Background IoT polling service for Module 03 — Absconding Live Prediction.

Why this file exists:
    The frontend dashboard refresh interval only controls the browser. This service
    makes the BACKEND fetch real IoT readings from Supabase/PostgreSQL every
    10 minutes, run the saved ML model, and cache the latest prediction JSON.

Live production flow:
    IoT device -> Supabase table -> backend polling loop every 10 minutes
    -> feature engineering -> saved ML model -> cached latest prediction
    -> dashboard/API reads the cached real IoT prediction.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from backend.ml.absconding.iot_live_prediction import (
    DEFAULT_OUTPUT_DIR,
    IOT_INTERVAL_MINUTES,
    predict_live_iot_absconding,
)

_LOCK = threading.Lock()
_THREAD: Optional[threading.Thread] = None
_STOP_EVENT = threading.Event()

_STATE: Dict[str, Any] = {
    "enabled": False,
    "running": False,
    "thread_alive": False,
    "interval_minutes": IOT_INTERVAL_MINUTES,
    "poll_count": 0,
    "success_count": 0,
    "failure_count": 0,
    "last_poll_started_at": None,
    "last_poll_finished_at": None,
    "last_success_at": None,
    "last_error_at": None,
    "last_error": None,
    "next_poll_at": None,
    "last_cached_prediction_path": None,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


def _state_path(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    return output_dir / "predictions" / "iot_monitor_status.json"


def _prediction_path(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    return output_dir / "predictions" / "iot_live_latest.json"


def _write_state(output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    path = _state_path(output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = get_iot_monitor_status(output_dir)
    path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


def get_iot_monitor_status(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    """Return in-memory monitor status plus cache diagnostics."""
    with _LOCK:
        status = dict(_STATE)
    status["thread_alive"] = bool(_THREAD and _THREAD.is_alive())
    status["cache_exists"] = _prediction_path(output_dir).exists()
    status["status_file"] = str(_state_path(output_dir))
    status["prediction_cache_file"] = str(_prediction_path(output_dir))
    return status


def read_cached_live_prediction(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Optional[Dict[str, Any]]:
    """Read the latest cached real IoT prediction created by the polling loop."""
    path = _prediction_path(output_dir)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("status", "cached")
    data["backend_iot_monitor"] = get_iot_monitor_status(output_dir)
    return data


def run_iot_monitor_once(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    """
    Pull the latest real IoT data from Supabase/PostgreSQL immediately and cache it.

    This is used by:
      - the background thread every 10 minutes
      - POST /api/absconding/iot/monitor/run-now
      - GET /api/absconding/iot/live?force=true
    """
    started_at = _now_iso()
    with _LOCK:
        _STATE["running"] = True
        _STATE["enabled"] = True
        _STATE["poll_count"] += 1
        _STATE["last_poll_started_at"] = started_at
        _STATE["last_error"] = None

    try:
        result = predict_live_iot_absconding(output_dir=output_dir)
        finished_at = _now_iso()
        with _LOCK:
            _STATE["running"] = False
            _STATE["success_count"] += 1
            _STATE["last_poll_finished_at"] = finished_at
            _STATE["last_success_at"] = finished_at
            _STATE["last_cached_prediction_path"] = str(_prediction_path(output_dir))
        result["backend_iot_monitor"] = get_iot_monitor_status(output_dir)
        _write_state(output_dir)
        return result
    except Exception as exc:
        finished_at = _now_iso()
        with _LOCK:
            _STATE["running"] = False
            _STATE["failure_count"] += 1
            _STATE["last_poll_finished_at"] = finished_at
            _STATE["last_error_at"] = finished_at
            _STATE["last_error"] = str(exc)
        _write_state(output_dir)
        raise


def _monitor_loop(output_dir: Path, interval_seconds: int) -> None:
    """Continuous backend loop: fetch IoT data, predict, sleep until next cycle."""
    while not _STOP_EVENT.is_set():
        cycle_started = _now()
        next_poll = cycle_started + timedelta(seconds=interval_seconds)
        with _LOCK:
            _STATE["next_poll_at"] = next_poll.isoformat()
        try:
            run_iot_monitor_once(output_dir)
        except Exception:
            # Error is stored in _STATE. Keep the thread alive so it can retry in the next cycle.
            pass

        # Sleep in small chunks so tests/shutdown can stop quickly.
        while not _STOP_EVENT.is_set() and _now() < next_poll:
            time.sleep(min(5, max(0.2, (next_poll - _now()).total_seconds())))


def start_iot_monitor(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    """
    Start backend polling if enabled.

    Env:
        IOT_MONITOR_ENABLED=true        # default true when IOT_DATA_SOURCE=postgres
        IOT_INTERVAL_MINUTES=10         # polling interval matches sensor interval
    """
    global _THREAD

    data_source = os.getenv("IOT_DATA_SOURCE", "").strip().lower()
    has_db = bool(os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL") or os.getenv("POSTGRES_URL"))
    default_enabled = has_db or data_source in {"postgres", "postgresql", "supabase", "supabase_postgres"}
    enabled = _bool_env("IOT_MONITOR_ENABLED", default_enabled)

    with _LOCK:
        _STATE["enabled"] = enabled
        _STATE["interval_minutes"] = IOT_INTERVAL_MINUTES

    if not enabled:
        _write_state(output_dir)
        return get_iot_monitor_status(output_dir)

    if _THREAD and _THREAD.is_alive():
        return get_iot_monitor_status(output_dir)

    _STOP_EVENT.clear()
    interval_seconds = max(60, int(IOT_INTERVAL_MINUTES * 60))
    _THREAD = threading.Thread(
        target=_monitor_loop,
        args=(output_dir, interval_seconds),
        name="absconding-iot-monitor",
        daemon=True,
    )
    _THREAD.start()
    _write_state(output_dir)
    return get_iot_monitor_status(output_dir)


def stop_iot_monitor(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    """Stop the background monitor loop gracefully."""
    _STOP_EVENT.set()
    with _LOCK:
        _STATE["enabled"] = False
        _STATE["running"] = False
    _write_state(output_dir)
    return get_iot_monitor_status(output_dir)
