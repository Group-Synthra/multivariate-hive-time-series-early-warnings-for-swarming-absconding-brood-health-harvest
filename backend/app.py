# backend/app.py

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from pathlib import Path
import json
import subprocess
import sys

# Import the blueprint
from routes.brood_health_routes import brood_health_bp

app = Flask(__name__)
CORS(app)

# Register blueprint
app.register_blueprint(brood_health_bp)

# Paths (remain as before)
THIS_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = THIS_DIR / 'outputs' / 'eda_complete'
DASHBOARD_JSON = OUTPUT_DIR / 'dashboard.json'
EDA_SCRIPT = THIS_DIR / 'eda' / 'eda_analysis.py'

def load_dashboard():
    if not DASHBOARD_JSON.exists():
        return None
    with open(DASHBOARD_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)

# ──────────────────────────────────────────────
# EDA Endpoints (unchanged)
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

@app.route('/api/eda/images/<path:filename>', methods=['GET'])
def serve_image(filename):
    if not (OUTPUT_DIR / filename).exists():
        return jsonify({'error': f'Image not found: {filename}'}), 404
    return send_from_directory(str(OUTPUT_DIR), filename)

@app.route('/api/eda/images', methods=['GET'])
def list_images():
    if not OUTPUT_DIR.exists():
        return jsonify([])
    images = [f.name for f in OUTPUT_DIR.glob('*.png')]
    return jsonify(images)

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

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'dashboard_ready': DASHBOARD_JSON.exists(),
        'outputs_dir': str(OUTPUT_DIR),
    })

if __name__ == '__main__':
    print("🐝 HiveEDA API running on http://localhost:5000")
    print("   GET  /api/eda                  — Dashboard JSON data")
    print("   GET  /api/eda/images/<fn>      — Serve PNG plots")
    print("   POST /api/eda/run              — Trigger EDA re-run")
    print("   GET  /api/brood_health         — Full brood health time series")
    print("   GET  /api/brood_health/summary — Per‑hive brood summary")
    print("   POST /api/brood_health/train   — Start model training")
    print("   GET  /api/brood_health/train/status — Training status")
    print("   POST /api/brood_health/predict — Real‑time prediction (IoT)")
    print("   GET  /api/health               — Health check")
    app.run(host='0.0.0.0', port=5000, debug=False)