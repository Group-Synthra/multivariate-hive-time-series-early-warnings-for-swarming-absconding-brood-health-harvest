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
from routes.model_training import model_training_bp
from routes.swarming_api import swarming_live_bp

# from routes.iot_api import iot_bp

 
app = Flask(__name__)
CORS(app)
app.register_blueprint(model_training_bp)
app.register_blueprint(swarming_live_bp)
# app.register_blueprint(iot_bp)
# Paths
THIS_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = THIS_DIR / 'outputs' / 'eda_complete'
DASHBOARD_JSON = OUTPUT_DIR / 'dashboard.json'
RUN_EDA_SCRIPT = THIS_DIR.parent / "run_eda.py"

# Swarming EDA paths
SWARM_OUTPUT_DIR = THIS_DIR / 'outputs' / 'eda_swarming'
SWARM_DASHBOARD_JSON = SWARM_OUTPUT_DIR / 'dashboard.json'
SWARM_IMAGES_DIR = SWARM_OUTPUT_DIR / 'images'
SWARM_REPORTS_DIR = SWARM_OUTPUT_DIR / 'reports'


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
            [sys.executable, str(RUN_EDA_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=300
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
                'error': result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr
            }), 500

    except subprocess.TimeoutExpired:
        return jsonify({
            'status': 'error',
            'message': 'EDA timed out (>5 min).'
        }), 504

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ──────────────────────────────────────────────
# GET /api/eda-swarming — Swarming EDA dashboard JSON
# ──────────────────────────────────────────────
@app.route('/api/eda-swarming', methods=['GET'])
def get_swarm_eda_data():
    if not SWARM_DASHBOARD_JSON.exists():
        return jsonify({
            'error': 'eda_swarming/dashboard.json not found. Run eda_analysis_swarming.py first.',
            'hint': 'Execute the swarming EDA pipeline to generate results.'
        }), 404
    with open(SWARM_DASHBOARD_JSON, 'r', encoding='utf-8') as f:
        return jsonify(json.load(f))


# ──────────────────────────────────────────────
# GET /api/eda-swarming/images — List swarming images
# ──────────────────────────────────────────────
@app.route('/api/eda-swarming/images', methods=['GET'])
def list_swarm_images():
    if not SWARM_IMAGES_DIR.exists():
        return jsonify([])
    images = [f.name for f in SWARM_IMAGES_DIR.glob('*.png')]
    return jsonify(sorted(images))


# ──────────────────────────────────────────────
# GET /api/eda-swarming/images/<filename> — Serve swarming image
# ──────────────────────────────────────────────
@app.route('/api/eda-swarming/images/<path:filename>', methods=['GET'])
def serve_swarm_image(filename):
    img_path = SWARM_IMAGES_DIR / filename
    if not img_path.exists():
        return jsonify({'error': f'Image not found: {filename}'}), 404
    return send_from_directory(str(SWARM_IMAGES_DIR), filename)


# ──────────────────────────────────────────────
# GET /api/eda-swarming/report — Feature analysis report text
# ──────────────────────────────────────────────
@app.route('/api/eda-swarming/report', methods=['GET'])
def get_swarm_report():
    report_path = SWARM_REPORTS_DIR / 'feature_analysis_summary.txt'
    if not report_path.exists():
        return jsonify({'error': 'Report not found.'}), 404
    with open(report_path, 'r', encoding='utf-8') as f:
        return jsonify({'report': f.read()})


# ──────────────────────────────────────────────
# GET /api/health — Health check
# ──────────────────────────────────────────────
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'dashboard_ready': DASHBOARD_JSON.exists(),
        'swarm_eda_ready': SWARM_DASHBOARD_JSON.exists(),
        'outputs_dir': str(OUTPUT_DIR),
    })


if __name__ == '__main__':
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    print("HiveEDA API running on http://localhost:5000")
    print("  GET  /api/eda                            - Dashboard JSON data")
    print("  GET  /api/eda/images/<fn>                - Serve PNG plots")
    print("  POST /api/eda/run                        - Trigger EDA re-run")
    print("  GET  /api/health                         - Health check")
    print("  POST /api/swarming/live-prediction       - Live swarming prediction")
    print("  GET  /api/swarming/live-prediction/health- Model health check")
    print("  GET  /api/swarming/live-prediction/sample- Sample payload")
    app.run(host='0.0.0.0', port=5000, debug=False)
 