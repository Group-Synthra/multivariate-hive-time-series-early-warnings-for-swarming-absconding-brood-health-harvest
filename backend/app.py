"""
Flask REST API — HiveEDA Dashboard Backend
Exposes EDA data via JSON API and serves static PNG images.
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from pathlib import Path
import json
import joblib
import subprocess
import sys
import pandas as pd
import numpy as np

from routes.harvest_routes import harvest_bp

app = Flask(__name__)
CORS(app)
app.register_blueprint(harvest_bp)

# Paths
THIS_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = THIS_DIR / 'outputs' / 'eda_complete'
DASHBOARD_JSON = OUTPUT_DIR / 'dashboard.json'
EDA_SCRIPT = THIS_DIR / 'eda' / 'eda_analysis.py'

def load_dashboard():
    """Load and return dashboard.json content."""
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


if __name__ == '__main__':
    print(f"🐝 HiveEDA API running on http://localhost:5000")
    print(f"   GET  /api/eda              — Dashboard JSON data")
    print(f"   GET  /api/eda/images/<fn>  — Serve PNG plots")
    print(f"   POST /api/eda/run          — Trigger EDA re-run")
    print(f"   GET  /api/health           — Health check")
    print()
    print("   GET  /api/harvest/eda-summary")
    print("   GET  /api/harvest/images")
    print("   GET  /api/harvest/model-results")
    print("   GET  /api/harvest/sample")
    print("   POST /api/harvest/predict")
    app.run(host='0.0.0.0', port=5000, debug=False)
