"""
Train and compare three regression models for Brood Health Score prediction.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import joblib
import sys
import json

# Add parent directory to path so we can import brood_health.analyzer
_current_dir = Path(__file__).resolve().parent
_parent_dir = _current_dir.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

# Now import from brood_health
from brood_health.analyzer import compute_brood_health_metrics

# Paths
DATA_PATH = _parent_dir / 'data' / 'hive_data_with_features.csv'
MODEL_DIR = _parent_dir / 'models'
MODEL_DIR.mkdir(exist_ok=True)

def load_and_prepare_data():
    """Load raw data, compute brood health metrics, and engineer features."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"CSV not found at {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    # Rename columns for analyzer
    df = df.rename(columns={
        'internal_temperature_c': 'temp',
        'internal_humidity_pct': 'humidity',
        'co2_ppm': 'co2',
        'hive_weight_kg': 'weight',
        'hive_id': 'hive'
    })
    # Compute brood health metrics (includes target)
    df_metrics = compute_brood_health_metrics(df)
    
    # Feature engineering: add time-based features and rolling statistics
    df_metrics['hour'] = df_metrics['timestamp'].dt.hour
    df_metrics['day_of_week'] = df_metrics['timestamp'].dt.dayofweek
    df_metrics['month'] = df_metrics['timestamp'].dt.month
    
    # Rolling averages of sensors (1h window = 4 rows at 15min)
    df_metrics['temp_roll1'] = df_metrics.groupby('hive')['temp'].transform(
        lambda x: x.rolling(4, min_periods=1).mean()
    )
    df_metrics['humidity_roll1'] = df_metrics.groupby('hive')['humidity'].transform(
        lambda x: x.rolling(4, min_periods=1).mean()
    )
    df_metrics['co2_roll1'] = df_metrics.groupby('hive')['co2'].transform(
        lambda x: x.rolling(4, min_periods=1).mean()
    )
    df_metrics['weight_roll1'] = df_metrics.groupby('hive')['weight'].transform(
        lambda x: x.rolling(4, min_periods=1).mean()
    )
    
    # Drop rows with NaN (due to rolling windows at start)
    df_metrics = df_metrics.dropna().reset_index(drop=True)
    
    # Define features and target
    feature_cols = [
        'temp', 'humidity', 'co2', 'weight',
        'temp_roll1', 'humidity_roll1', 'co2_roll1', 'weight_roll1',
        'hour', 'day_of_week', 'month'
    ]
    target_col = 'brood_health_score'
    
    X = df_metrics[feature_cols]
    y = df_metrics[target_col]
    
    return X, y, feature_cols

def train_and_evaluate(models_dict, X_train, X_test, y_train, y_test):
    """Train each model and return metrics."""
    results = {}
    for name, model in models_dict.items():
        print(f"Training {name}...")
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # Cross-validation score (3-fold)
        cv_scores = cross_val_score(model, X_train, y_train, cv=3, scoring='r2')
        cv_mean = cv_scores.mean()
        
        results[name] = {
            'rmse': round(rmse, 3),
            'mae': round(mae, 3),
            'r2': round(r2, 3),
            'cv_r2_mean': round(cv_mean, 3),
            'model': model
        }
        print(f"  RMSE: {rmse:.3f}, R2: {r2:.3f}")
    return results

def save_best_model(results, feature_cols):
    """Select best model (lowest RMSE) and save it."""
    best_name = min(results, key=lambda x: results[x]['rmse'])
    best_model = results[best_name]['model']
    joblib.dump(best_model, MODEL_DIR / 'best_brood_model.joblib')
    joblib.dump(feature_cols, MODEL_DIR / 'brood_feature_columns.joblib')
    return best_name, results[best_name]

def run_training():
    """Main training pipeline."""
    print("Loading data and computing brood health metrics...")
    X, y, feature_cols = load_and_prepare_data()
    print(f"Dataset shape: {X.shape}")
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Define models
    models = {
        'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
        'XGBoost': xgb.XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42),
        'Gradient Boosting': GradientBoostingRegressor(n_estimators=100, random_state=42)
    }
    
    print("Training and evaluating models...")
    results = train_and_evaluate(models, X_train, X_test, y_train, y_test)
    
    best_name, best_metrics_full = save_best_model(results, feature_cols)
    
    # Remove the model object from best_metrics for JSON serialization
    best_metrics = {k: v for k, v in best_metrics_full.items() if k != 'model'}
    
    print(f"\nBest model: {best_name} (RMSE = {best_metrics['rmse']})")
    
    # Prepare summary (without model objects)
    summary = {
        'best_model': best_name,
        'metrics': best_metrics,
        'all_models': {name: {k: v for k, v in m.items() if k != 'model'} 
                       for name, m in results.items()},
        'feature_columns': feature_cols,
        'train_samples': len(X_train),
        'test_samples': len(X_test)
    }
    return summary

if __name__ == '__main__':
    summary = run_training()
    summary_path = MODEL_DIR / 'training_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"Training summary saved to {summary_path}")