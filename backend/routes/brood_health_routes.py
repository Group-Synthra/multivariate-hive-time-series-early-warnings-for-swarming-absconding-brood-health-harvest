from flask import Blueprint, jsonify, request
import pandas as pd
import numpy as np
from pathlib import Path
import threading
import joblib
import sys
import json

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from brood_health.analyzer import compute_brood_health_metrics

brood_health_bp = Blueprint('brood_health', __name__, url_prefix='/api')

# Paths
THIS_DIR = Path(__file__).parent.parent
DATA_PATH = THIS_DIR / 'data' / 'hive_data_with_features.csv'
MODEL_DIR = THIS_DIR / 'models'
MODEL_PATH = MODEL_DIR / 'best_brood_model.joblib'
FEATURE_COLS_PATH = MODEL_DIR / 'brood_feature_columns.joblib'

# Training status with progress fields
training_status = {
    'running': False,
    'result': None,
    'error': None,
    'current_step': '',
    'progress': 0,
    'message': ''
}

# Helper to load raw data
def load_raw_hive_data():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"CSV not found at {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.rename(columns={
        'internal_temperature_c': 'temp',
        'internal_humidity_pct': 'humidity',
        'co2_ppm': 'co2',
        'hive_weight_kg': 'weight',
        'hive_id': 'hive'
    })
    if 'hive' not in df.columns and 'hive_id' in df.columns:
        df['hive'] = df['hive_id']
    return df

# ──────────────────────────────────────────────
# Existing Brood Health Endpoints
# ──────────────────────────────────────────────
@brood_health_bp.route('/brood_health', methods=['GET'])
def get_brood_health():
    try:
        df = load_raw_hive_data()
        result_df = compute_brood_health_metrics(df)
        result_df['timestamp'] = result_df['timestamp'].astype(str)
        return jsonify(result_df.to_dict(orient='records'))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@brood_health_bp.route('/brood_health/summary', methods=['GET'])
def brood_health_summary():
    try:
        df = load_raw_hive_data()
        result_df = compute_brood_health_metrics(df)
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
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ──────────────────────────────────────────────
# Model Training Endpoints with Progress
# ──────────────────────────────────────────────
def train_task():
    global training_status
    training_status['running'] = True
    training_status['error'] = None
    training_status['progress'] = 0
    training_status['message'] = 'Starting training...'
    training_status['current_step'] = 'Initializing'

    def progress_callback(event, data):
        """Update training_status based on events from the training script."""
        if event == 'start':
            training_status['message'] = data['message']
            training_status['progress'] = data.get('progress', 0)
        elif event == 'data_ready':
            training_status['message'] = data['message']
            training_status['progress'] = data.get('progress', 10)
        elif event == 'split_done':
            training_status['message'] = data['message']
            training_status['progress'] = data.get('progress', 20)
        elif event == 'model_start':
            training_status['current_step'] = data['model']
            training_status['message'] = data['message']
            training_status['progress'] = data.get('progress', 0)
        elif event == 'model_end':
            training_status['message'] = data['message']
            training_status['progress'] = data.get('progress', 0)
        elif event == 'saving':
            training_status['message'] = data['message']
            training_status['progress'] = data.get('progress', 90)
        elif event == 'complete':
            training_status['message'] = data['message']
            training_status['progress'] = 100
            training_status['result'] = data['result']

    try:
        # Import inside function to avoid startup errors if ml module is missing
        from ml.train_brood_health_models import run_training
        run_training(progress_callback=progress_callback)
    except Exception as e:
        training_status['error'] = str(e)
        training_status['message'] = f'Error: {e}'
        import traceback
        traceback.print_exc()
    finally:
        training_status['running'] = False
        training_status['current_step'] = ''

@brood_health_bp.route('/brood_health/train', methods=['POST'])
def start_training():
    if training_status['running']:
        return jsonify({'status': 'already_running', 'message': 'Training already in progress'}), 409
    thread = threading.Thread(target=train_task)
    thread.start()
    return jsonify({'status': 'started', 'message': 'Training started'})

# @brood_health_bp.route('/brood_health/train/status', methods=['GET'])
# def training_status_endpoint():
#     return jsonify({
#         'running': training_status['running'],
#         'result': training_status['result'],
#         'error': training_status['error'],
#         'current_step': training_status.get('current_step', ''),
#         'progress': training_status.get('progress', 0),
#         'message': training_status.get('message', '')
#     })

@brood_health_bp.route('/brood_health/train/status', methods=['GET'])
def training_status_endpoint():
    # Check if we already have a saved result
    summary_path = MODEL_DIR / 'training_summary.json'
    if summary_path.exists():
        with open(summary_path, 'r') as f:
            saved_result = json.load(f)
        return jsonify({
            'running': False,
            'result': saved_result,
            'error': None,
            'progress': 100,
            'message': 'Training complete (cached results)'
        })
    
    # Otherwise return the live in‑memory status (if any training is running)
    return jsonify({
        'running': training_status.get('running', False),
        'result': training_status.get('result'),
        'error': training_status.get('error'),
        'progress': training_status.get('progress', 0),
        'message': training_status.get('message', ''),
        'current_step': training_status.get('current_step', '')
    })

# ──────────────────────────────────────────────
# Prediction Endpoint (for future IoT integration)
# ──────────────────────────────────────────────
@brood_health_bp.route('/brood_health/predict', methods=['POST'])
def predict():
    """Accept real‑time sensor readings and return predicted brood health score."""
    try:
        data = request.get_json()
        # Placeholder – replace with actual model prediction when IoT data arrives
        return jsonify({
            'predicted_score': 75.5,
            'health_level': 'Good',
            'message': 'Prediction endpoint ready – will use saved model once IoT data arrives.'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500