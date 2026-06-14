"""
Flask REST API — HiveEDA Dashboard Backend
Exposes EDA data via JSON API and serves static PNG images.
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from pathlib import Path
import json
import subprocess
import sys
import pandas as pd
import numpy as np

# Import brood health analyzer (create this module as described)
from brood_health.analyzer import compute_brood_health_metrics

app = Flask(__name__)
CORS(app)

# Paths
THIS_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = THIS_DIR / 'outputs' / 'eda_complete'
DASHBOARD_JSON = OUTPUT_DIR / 'dashboard.json'
EDA_SCRIPT = THIS_DIR / 'eda' / 'eda_analysis.py'
DATA_PATH = THIS_DIR / 'data' / 'hive_data_with_features.csv'

# ──────────────────────────────────────────────
# Helper to load raw data for brood health
# ──────────────────────────────────────────────
def load_raw_hive_data():
    """Load the CSV and rename columns to match analyzer expectations."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"CSV not found at {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    # Rename columns to the standard names used by the analyzer
    df = df.rename(columns={
        'internal_temperature_c': 'temp',
        'internal_humidity_pct': 'humidity',
        'co2_ppm': 'co2',
        'hive_weight_kg': 'weight',
        'hive_id': 'hive'
    })
    # Ensure 'hive' column exists (some datasets use 'hive')
    if 'hive' not in df.columns and 'hive_id' in df.columns:
        df['hive'] = df['hive_id']
    return df

# ──────────────────────────────────────────────
# Existing EDA endpoints
# ──────────────────────────────────────────────
def load_dashboard():
    if not DASHBOARD_JSON.exists():
        return None
    with open(DASHBOARD_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)
# ──────────────────────────────────────────────
# GET /api/eda — Main data endpoint
# ──────────────────────────────────────────────
@app.route('/api/eda', methods=['GET'])
def get_eda_data():
    data = load_dashboard()
    if data is None:
        return jsonify({
            'error': 'dashboard.json not found. Run: python run_eda.py first.',
            'hint': 'Execute the EDA pipeline to generate analysis results.'
        }), 404
    return jsonify(data)
# ──────────────────────────────────────────────
# GET /api/eda/images/<filename> — Static PNG serving
# ──────────────────────────────────────────────
@app.route('/api/eda/images/<path:filename>', methods=['GET'])
def serve_image(filename):
    if not (OUTPUT_DIR / filename).exists():
        return jsonify({'error': f'Image not found: {filename}'}), 404
    return send_from_directory(str(OUTPUT_DIR), filename)
# ──────────────────────────────────────────────
# GET /api/eda/images — List available images
# ──────────────────────────────────────────────
@app.route('/api/eda/images', methods=['GET'])
def list_images():
    if not OUTPUT_DIR.exists():
        return jsonify([])
    images = [f.name for f in OUTPUT_DIR.glob('*.png')]
    return jsonify(images)
# ──────────────────────────────────────────────
# POST /api/eda/run — Trigger EDA re-run
# ──────────────────────────────────────────────
@app.route('/api/eda/run', methods=['POST'])
def run_eda():
    try:
        result = subprocess.run(
            [sys.executable, str(EDA_SCRIPT)],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            return jsonify({
                'status': 'success',
                'message': 'EDA analysis completed successfully.',
                'output': result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'EDA script failed.',
                'error': result.stderr[-2000:]
            }), 500
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'EDA timed out (>5 min).'}), 504
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
# ──────────────────────────────────────────────
# GET /api/health — Health check
# ──────────────────────────────────────────────
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'dashboard_ready': DASHBOARD_JSON.exists(),
        'outputs_dir': str(OUTPUT_DIR),
    })

# ──────────────────────────────────────────────
# Brood Health Endpoints
# ──────────────────────────────────────────────
@app.route('/api/brood_health', methods=['GET'])
def get_brood_health():
    """
    Return full brood health metrics for all hives (time series).
    Each record includes brood_health_score, bhsi, rod, health_level, etc.
    """
    try:
        df = load_raw_hive_data()
        result_df = compute_brood_health_metrics(df)
        # Convert timestamp to string for JSON serialization
        result_df['timestamp'] = result_df['timestamp'].astype(str)
        return jsonify(result_df.to_dict(orient='records'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/brood_health/summary', methods=['GET'])
def brood_health_summary():
    """
    Return per‑hive summary: current score, average BHSI, health level,
    stability level, and trend label.
    """
    try:
        df = load_raw_hive_data()
        result_df = compute_brood_health_metrics(df)
        # Aggregate per hive
        summary = result_df.groupby('hive').agg({
            'brood_health_score': ['mean', 'last'],
            'bhsi': 'mean',
            'health_level': lambda x: x.iloc[-1],
            'stability_level': lambda x: x.iloc[-1],
            'trend_label': lambda x: x.iloc[-1],
        }).round(1)
        summary.columns = ['avg_score', 'current_score', 'avg_bhsi',
                           'health_level', 'stability_level', 'trend_label']
        summary = summary.reset_index().to_dict(orient='records')
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🐝 HiveEDA API running on http://localhost:5000")
    print("   GET  /api/eda                  — Dashboard JSON data")
    print("   GET  /api/eda/images/<fn>      — Serve PNG plots")
    print("   POST /api/eda/run              — Trigger EDA re-run")
    print("   GET  /api/brood_health         — Full brood health time series")
    print("   GET  /api/brood_health/summary — Per‑hive brood summary")
    print("   GET  /api/health               — Health check")
    app.run(host='0.0.0.0', port=5000, debug=False)