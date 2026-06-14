# """
# Flask REST API — HiveEDA Dashboard Backend
# Exposes EDA data via JSON API and serves static PNG images.
# """

# from flask import Flask, jsonify, send_from_directory, request
# from flask_cors import CORS
# from pathlib import Path
# import json
# import subprocess
# import sys

# app = Flask(__name__)
# CORS(app)

# # Paths
# THIS_DIR = Path(__file__).resolve().parent
# OUTPUT_DIR = THIS_DIR / 'outputs' / 'eda_complete'
# DASHBOARD_JSON = OUTPUT_DIR / 'dashboard.json'
# EDA_SCRIPT = THIS_DIR / 'eda' / 'eda_analysis.py'


# def load_dashboard():
#     """Load and return dashboard.json content."""
#     if not DASHBOARD_JSON.exists():
#         return None
#     with open(DASHBOARD_JSON, 'r', encoding='utf-8') as f:
#         return json.load(f)


# # ──────────────────────────────────────────────
# # GET /api/eda — Main data endpoint
# # ──────────────────────────────────────────────
# @app.route('/api/eda', methods=['GET'])
# def get_eda_data():
#     data = load_dashboard()
#     if data is None:
#         return jsonify({
#             'error': 'dashboard.json not found. Run: python run_eda.py first.',
#             'hint': 'Execute the EDA pipeline to generate analysis results.'
#         }), 404
#     return jsonify(data)


# # ──────────────────────────────────────────────
# # GET /api/eda/images/<filename> — Static PNG serving
# # ──────────────────────────────────────────────
# @app.route('/api/eda/images/<path:filename>', methods=['GET'])
# def serve_image(filename):
#     if not (OUTPUT_DIR / filename).exists():
#         return jsonify({'error': f'Image not found: {filename}'}), 404
#     return send_from_directory(str(OUTPUT_DIR), filename)


# # ──────────────────────────────────────────────
# # GET /api/eda/images — List available images
# # ──────────────────────────────────────────────
# @app.route('/api/eda/images', methods=['GET'])
# def list_images():
#     if not OUTPUT_DIR.exists():
#         return jsonify([])
#     images = [f.name for f in OUTPUT_DIR.glob('*.png')]
#     return jsonify(images)


# # ──────────────────────────────────────────────
# # POST /api/eda/run — Trigger EDA re-run
# # ──────────────────────────────────────────────
# @app.route('/api/eda/run', methods=['POST'])
# def run_eda():
#     try:
#         result = subprocess.run(
#             [sys.executable, str(EDA_SCRIPT)],
#             capture_output=True, text=True, timeout=300
#         )
#         if result.returncode == 0:
#             return jsonify({
#                 'status': 'success',
#                 'message': 'EDA analysis completed successfully.',
#                 'output': result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
#             })
#         else:
#             return jsonify({
#                 'status': 'error',
#                 'message': 'EDA script failed.',
#                 'error': result.stderr[-2000:]
#             }), 500
#     except subprocess.TimeoutExpired:
#         return jsonify({'status': 'error', 'message': 'EDA timed out (>5 min).'}), 504
#     except Exception as e:
#         return jsonify({'status': 'error', 'message': str(e)}), 500


# # ──────────────────────────────────────────────
# # GET /api/health — Health check
# # ──────────────────────────────────────────────
# @app.route('/api/health', methods=['GET'])
# def health():
#     return jsonify({
#         'status': 'ok',
#         'dashboard_ready': DASHBOARD_JSON.exists(),
#         'outputs_dir': str(OUTPUT_DIR),
#     })


# if __name__ == '__main__':
#     print(f"🐝 HiveEDA API running on http://localhost:5000")
#     print(f"   GET  /api/eda              — Dashboard JSON data")
#     print(f"   GET  /api/eda/images/<fn>  — Serve PNG plots")
#     print(f"   POST /api/eda/run          — Trigger EDA re-run")
#     print(f"   GET  /api/health           — Health check")
#     app.run(host='0.0.0.0', port=5000, debug=False)

"""
Flask REST API — HiveEDA Dashboard Backend
Integrated with Swarming Prediction Module
Exposes EDA data and Swarming Model results via JSON API
LSTM model loading has been disabled as requested
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from pathlib import Path
import json
import subprocess
import sys
import pandas as pd
import numpy as np
import joblib
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app)

# ============================================
# PATH CONFIGURATION
# ============================================
THIS_DIR = Path(__file__).resolve().parent

# EDA Paths
OUTPUT_DIR = THIS_DIR / 'outputs' / 'eda_complete'
DASHBOARD_JSON = OUTPUT_DIR / 'dashboard.json'
EDA_SCRIPT = THIS_DIR / 'eda' / 'eda_analysis.py'

# Swarming Module Paths
SWARMING_OUTPUTS_DIR = THIS_DIR / 'outputs' / 'swarming'
SWARMING_FIGURES_DIR = SWARMING_OUTPUTS_DIR / 'figures'
SWARMING_MODELS_DIR = THIS_DIR / 'ml' / 'swarming' / 'models'
SWARMING_DATA_DIR = THIS_DIR / 'data' / 'processed' / 'swarming'

# Create directories if they don't exist
SWARMING_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
SWARMING_FIGURES_DIR.mkdir(parents=True, exist_ok=True)
SWARMING_MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Global variables for loaded models
rf_model = None
lstm_model = None
xgb_model = None
best_model_info = None
preprocessor = None
lstm_input_size = None


# ============================================
# LOAD SWARMING MODELS (LSTM DISABLED)
# ============================================
def load_swarming_models():
    """Load Random Forest and XGBoost models only (LSTM disabled)"""
    global rf_model, lstm_model, xgb_model, best_model_info, preprocessor, lstm_input_size
    
    print("\n🐝 Loading Swarming Prediction Models...")
    print("⚠️ LSTM model loading is DISABLED (as requested)")
    
    # Load preprocessor
    preprocessor_path = SWARMING_DATA_DIR / 'preprocessor.pkl'
    if preprocessor_path.exists():
        preprocessor = joblib.load(preprocessor_path)
        print(f"   ✅ Preprocessor loaded from {preprocessor_path}")
        if preprocessor and 'feature_cols' in preprocessor:
            lstm_input_size = len(preprocessor['feature_cols'])
    
    # Load Random Forest model
    rf_path = SWARMING_MODELS_DIR / 'random_forest_model.pkl'
    if rf_path.exists():
        rf_model = joblib.load(rf_path)
        print(f"   ✅ Random Forest model loaded from {rf_path}")
    else:
        print(f"   ⚠️ Random Forest model not found at {rf_path}")
    
    # LSTM - EXPLICITLY DISABLED
    lstm_model = None
    print(f"   ⚠️ LSTM model is DISABLED - will return fallback responses")
    
    # Load XGBoost model
    xgb_path = SWARMING_MODELS_DIR / 'xgboost_model.json'
    if xgb_path.exists():
        import xgboost as xgb
        xgb_model = xgb.XGBClassifier()
        xgb_model.load_model(str(xgb_path))
        print(f"   ✅ XGBoost model loaded from {xgb_path}")
    else:
        print(f"   ⚠️ XGBoost model not found at {xgb_path}")
    
    # Load best model info
    best_model_path = SWARMING_MODELS_DIR / 'best_model_info.json'
    if best_model_path.exists():
        with open(best_model_path, 'r') as f:
            best_model_info = json.load(f)
        print(f"   ✅ Best model info: {best_model_info.get('best_model', 'N/A')}")
        if 'models_with_placeholders' in best_model_info:
            print(f"   ⚠️ Note: {best_model_info['models_with_placeholders']} have placeholder metrics")
    
    print("="*50)


# ============================================
# EDA ENDPOINTS (Existing)
# ============================================

def load_dashboard():
    """Load and return dashboard.json content."""
    if not DASHBOARD_JSON.exists():
        return None
    with open(DASHBOARD_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)


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


# ============================================
# SWARMING MODULE ENDPOINTS (UPDATED)
# ============================================

@app.route('/api/swarming', methods=['GET'])
def swarming_root():
    """Swarming module root endpoint"""
    return jsonify({
        "message": "Swarming Prediction API",
        "version": "1.0",
        "models_loaded": {
            "random_forest": rf_model is not None,
            "lstm": False,  # Explicitly disabled
            "xgboost": xgb_model is not None
        },
        "lstm_enabled": False,
        "best_model": best_model_info.get('best_model') if best_model_info else None,
        "note": "LSTM model has been disabled as requested - using Random Forest and XGBoost only",
        "endpoints": [
            "/api/swarming/model-comparison",
            "/api/swarming/best-model",
            "/api/swarming/comparison-table",
            "/api/swarming/confusion-matrix/<model_name>",
            "/api/swarming/comparison-chart"
        ]
    })


@app.route('/api/swarming/model-comparison', methods=['GET'])
def get_model_comparison():
    """Get model comparison results as JSON"""
    json_path = SWARMING_OUTPUTS_DIR / 'model_comparison.json'
    
    if not json_path.exists():
        return jsonify({
            'error': 'Model comparison results not found. Run training first.',
            'hint': 'Execute model_comparison.py to generate results.',
            'note': 'LSTM model is disabled - results will show placeholder metrics'
        }), 404
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Add note about LSTM being disabled
    return jsonify({
        'models': data,
        'lstm_disabled': True,
        'note': 'LSTM model is disabled - placeholder metrics shown for UI compatibility'
    })


@app.route('/api/swarming/best-model', methods=['GET'])
def get_best_model():
    """Get best model information"""
    json_path = SWARMING_MODELS_DIR / 'best_model_info.json'
    
    if not json_path.exists():
        return jsonify({
            'error': 'Best model info not found. Run training first.',
            'hint': 'Execute model_comparison.py to generate best model info.'
        }), 404
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    return jsonify(data)


@app.route('/api/swarming/comparison-table', methods=['GET'])
def get_comparison_table():
    """Get comparison table as JSON"""
    csv_path = SWARMING_OUTPUTS_DIR / 'model_comparison.csv'
    
    if not csv_path.exists():
        return jsonify({
            'error': 'Comparison CSV not found. Run training first.'
        }), 404
    
    df = pd.read_csv(csv_path)
    return jsonify(df.to_dict(orient='records'))


@app.route('/api/swarming/confusion-matrix/<model_name>', methods=['GET'])
def get_confusion_matrix(model_name):
    """Get confusion matrix image for a specific model"""
    valid_models = ['rf', 'lstm', 'xgb', 'random_forest', 'xgboost']
    
    model_map = {
        'rf': 'rf_confusion_matrix.png',
        'random_forest': 'rf_confusion_matrix.png',
        'lstm': 'lstm_confusion_matrix.png',  # May not exist
        'xgb': 'xgb_confusion_matrix.png',
        'xgboost': 'xgb_confusion_matrix.png'
    }
    
    if model_name.lower() not in model_map:
        return jsonify({'error': f'Invalid model. Choose from: {list(model_map.keys())}'}), 400
    
    image_path = SWARMING_FIGURES_DIR / model_map[model_name.lower()]
    
    if not image_path.exists():
        if model_name.lower() == 'lstm':
            return jsonify({
                'error': f'Confusion matrix not found for {model_name}',
                'note': 'LSTM model is disabled - no confusion matrix available'
            }), 404
        else:
            return jsonify({'error': f'Confusion matrix not found for {model_name}'}), 404
    
    return send_from_directory(str(SWARMING_FIGURES_DIR), model_map[model_name.lower()])


@app.route('/api/swarming/comparison-chart', methods=['GET'])
def get_comparison_chart():
    """Get model comparison bar chart"""
    image_path = SWARMING_FIGURES_DIR / 'model_comparison_bar_chart.png'
    
    if not image_path.exists():
        return jsonify({'error': 'Comparison chart not found. Run training first.'}), 404
    
    return send_from_directory(str(SWARMING_FIGURES_DIR), 'model_comparison_bar_chart.png')


@app.route('/api/swarming/lstm-training-history', methods=['GET'])
def get_lstm_training_history():
    """Get LSTM training history plot - DISABLED"""
    return jsonify({
        'error': 'LSTM model is disabled',
        'note': 'LSTM training has been disabled as requested',
        'suggestion': 'Use Random Forest or XGBoost models instead'
    }), 404


@app.route('/api/swarming/predict/<model_name>', methods=['POST'])
def predict_swarming(model_name):
    """
    Predict swarming risk using specified model
    LSTM requests will get a fallback response
    """
    # Special handling for LSTM - return fallback response
    if model_name == 'lstm':
        return jsonify({
            'model_used': 'lstm',
            'probability': 0.30,
            'risk_percentage': 30.0,
            'risk_level': 'LOW',
            'predicted_event_window': 'beyond 48 hours',
            'note': 'LSTM model is disabled - returning default values',
            'suggestion': 'Use random_forest or xgboost for actual predictions'
        }), 200  # Return 200 with explanatory note
    
    # Check if model exists for non-LSTM models
    if model_name == 'random_forest' and rf_model is None:
        return jsonify({'error': 'Random Forest model not loaded'}), 404
    elif model_name == 'xgboost' and xgb_model is None:
        return jsonify({'error': 'XGBoost model not loaded'}), 404
    elif model_name not in ['random_forest', 'xgboost']:
        return jsonify({'error': f'Invalid model. Choose: random_forest, xgboost (LSTM is disabled)'}), 400
    
    data = request.get_json()
    
    if not data or 'sequence' not in data:
        return jsonify({'error': 'Missing sequence data. Provide sequence array.'}), 400
    
    sequence = np.array(data['sequence'])
    
    # Validate shape
    if len(sequence.shape) == 2:
        sequence = sequence.reshape(1, sequence.shape[0], sequence.shape[1])
    
    # Make prediction
    if model_name == 'random_forest':
        # Reshape for sklearn
        seq_flat = sequence.reshape(sequence.shape[0], -1)
        probability = rf_model.predict_proba(seq_flat)[0, 1]
        
    else:  # xgboost
        seq_flat = sequence.reshape(sequence.shape[0], -1)
        probability = xgb_model.predict_proba(seq_flat)[0, 1]
    
    risk_percentage = probability * 100
    
    # Determine risk level
    if risk_percentage > 70:
        risk_level = "HIGH"
        predicted_window = "within 24 hours"
    elif risk_percentage > 30:
        risk_level = "MEDIUM"
        predicted_window = "within 24-48 hours"
    else:
        risk_level = "LOW"
        predicted_window = "beyond 48 hours"
    
    return jsonify({
        'model_used': model_name,
        'probability': round(float(probability), 4),
        'risk_percentage': round(float(risk_percentage), 2),
        'risk_level': risk_level,
        'predicted_event_window': predicted_window
    })


# ============================================
# HEALTH CHECK ENDPOINT
# ============================================

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'dashboard_ready': DASHBOARD_JSON.exists(),
        'lstm_enabled': False,  # Explicitly disabled
        'swarming_models_loaded': {
            'random_forest': rf_model is not None,
            'lstm': False,  # Disabled
            'xgboost': xgb_model is not None
        },
        'best_model': best_model_info.get('best_model') if best_model_info else None,
        'outputs_dir': str(OUTPUT_DIR),
        'swarming_outputs_dir': str(SWARMING_OUTPUTS_DIR),
        'note': 'LSTM model has been disabled as requested'
    })


# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    # Load swarming models on startup
    load_swarming_models()
    
    print("\n" + "="*50)
    print("🐝 HiveEDA API running on http://localhost:5000")
    print("⚠️ LSTM model is DISABLED (as requested)")
    print("="*50)
    print("\n📊 EDA ENDPOINTS:")
    print("   GET  /api/eda              — Dashboard JSON data")
    print("   GET  /api/eda/images/<fn>  — Serve PNG plots")
    print("   POST /api/eda/run          — Trigger EDA re-run")
    print("\n🐝 SWARMING ENDPOINTS (LSTM DISABLED):")
    print("   GET  /api/swarming                    — Swarming module info")
    print("   GET  /api/swarming/model-comparison   — Model comparison JSON")
    print("   GET  /api/swarming/best-model         — Best model info")
    print("   GET  /api/swarming/comparison-table   — Comparison table")
    print("   GET  /api/swarming/confusion-matrix/<model> — Confusion matrix PNG")
    print("   GET  /api/swarming/comparison-chart   — Comparison bar chart")
    print("   POST /api/swarming/predict/<model>    — Make prediction (RF or XGB only)")
    print("\n⚠️  LSTM endpoints return fallback responses")
    print("\n🔧 GENERAL:")
    print("   GET  /api/health           — Health check")
    print("="*50)
    
    app.run(host='0.0.0.0', port=5000, debug=False)