"""
XGBoost Classifier for Swarming Prediction - UPDATED for optimized features
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
import time
import xgboost as xgb
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                            f1_score, roc_auc_score, confusion_matrix,
                            matthews_corrcoef)
from imblearn.over_sampling import SMOTE
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')


class XGBoostSwarmingModel:
    def __init__(self, output_dir=None, figures_dir=None):
        self.output_dir = output_dir or Path(__file__).parent.parent.parent.parent / 'ml' / 'swarming' / 'models'
        self.figures_dir = figures_dir or Path(__file__).parent.parent.parent.parent / 'outputs' / 'swarming' / 'figures'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        self.model = None
        self.feature_cols = None
        
    def reshape_for_sklearn(self, X):
        """Reshape 3D sequences to 2D (or handle 2D input)"""
        if len(X.shape) == 3:
            n_samples, n_timesteps, n_features = X.shape
            print(f"   Reshaping 3D data ({n_samples}, {n_timesteps}, {n_features}) to 2D")
            return X.reshape(n_samples, n_timesteps * n_features)
        elif len(X.shape) == 2:
            print(f"   Data already 2D with shape {X.shape}")
            return X
        else:
            raise ValueError(f"Expected 2D or 3D input, got shape {X.shape}")
    
    def handle_imbalance(self, X_train, y_train):
        """Handle class imbalance using SMOTE"""
        print("\n   Handling class imbalance with SMOTE...")
        
        # Store original shape info if 3D
        original_shape = X_train.shape if len(X_train.shape) == 3 else None
        
        # Reshape to 2D for SMOTE
        X_train_reshaped = self.reshape_for_sklearn(X_train)
        
        print(f"   Before SMOTE - Class 0: {(y_train==0).sum()}, Class 1: {(y_train==1).sum()}")
        
        # Only apply SMOTE if we have both classes and enough samples
        if len(np.unique(y_train)) > 1 and min(np.bincount(y_train)) > 1:
            smote = SMOTE(random_state=42, sampling_strategy=0.3)
            X_resampled, y_resampled = smote.fit_resample(X_train_reshaped, y_train)
            print(f"   After SMOTE - Class 0: {(y_resampled==0).sum()}, Class 1: {(y_resampled==1).sum()}")
        else:
            print(f"   Skipping SMOTE - insufficient class diversity")
            X_resampled, y_resampled = X_train_reshaped, y_train
        
        # Reshape back to 3D if original was 3D
        if original_shape is not None:
            X_resampled = X_resampled.reshape(-1, original_shape[1], original_shape[2])
        
        return X_resampled, y_resampled
    
    def calculate_metrics(self, y_true, y_pred, y_proba):
        """Calculate comprehensive evaluation metrics"""
        return {
            'accuracy': round(accuracy_score(y_true, y_pred), 4),
            'precision': round(precision_score(y_true, y_pred, zero_division=0), 4),
            'recall': round(recall_score(y_true, y_pred, zero_division=0), 4),
            'f1_score': round(f1_score(y_true, y_pred, zero_division=0), 4),
            'roc_auc': round(roc_auc_score(y_true, y_proba), 4) if len(np.unique(y_true)) > 1 else 0.5,
            'matthews_corrcoef': round(matthews_corrcoef(y_true, y_pred), 4),
            'confusion_matrix': confusion_matrix(y_true, y_pred).tolist()
        }
    
    def train(self, X_train, y_train, X_val, y_val, X_test, y_test, feature_cols=None):
        """Train XGBoost model"""
        print("\n" + "="*70)
        print("TRAINING XGBOOST CLASSIFIER (Optimized Features)")
        print("="*70)
        
        self.feature_cols = feature_cols
        
        start_time = time.time()
        
        # Print input shapes
        print(f"\n[1/4] Input data shapes:")
        print(f"   X_train shape: {X_train.shape}")
        print(f"   X_val shape: {X_val.shape}")
        print(f"   X_test shape: {X_test.shape}")
        
        # Reshape for sklearn/XGBoost
        print(f"\n[2/4] Reshaping data...")
        X_train_2d = self.reshape_for_sklearn(X_train)
        X_val_2d = self.reshape_for_sklearn(X_val)
        X_test_2d = self.reshape_for_sklearn(X_test)
        
        print(f"   X_train_2d shape: {X_train_2d.shape}")
        print(f"   X_val_2d shape: {X_val_2d.shape}")
        print(f"   X_test_2d shape: {X_test_2d.shape}")
        
        # Handle imbalance
        print(f"\n[3/4] Handling class imbalance...")
        X_train_resampled, y_train_resampled = self.handle_imbalance(X_train_2d, y_train)
        
        # Calculate scale_pos_weight for imbalance
        neg_count = (y_train_resampled == 0).sum()
        pos_count = (y_train_resampled == 1).sum()
        scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1
        
        print(f"   Scale pos weight: {scale_pos_weight:.2f}")
        
        # Train XGBoost
        print(f"\n[4/4] Training XGBoost...")
        self.model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            random_state=42,
            use_label_encoder=False,
            eval_metric='logloss',
            verbosity=1,
            n_jobs=-1  # Use all CPU cores
        )
        
        self.model.fit(
            X_train_resampled, y_train_resampled,
            eval_set=[(X_val_2d, y_val)],
            verbose=False
        )
        
        training_time = time.time() - start_time
        
        # Predictions
        y_train_pred = self.model.predict(X_train_resampled)
        y_val_pred = self.model.predict(X_val_2d)
        y_test_pred = self.model.predict(X_test_2d)
        
        y_train_proba = self.model.predict_proba(X_train_resampled)[:, 1]
        y_val_proba = self.model.predict_proba(X_val_2d)[:, 1]
        y_test_proba = self.model.predict_proba(X_test_2d)[:, 1]
        
        # Metrics
        metrics = {
            'train': self.calculate_metrics(y_train_resampled, y_train_pred, y_train_proba),
            'validation': self.calculate_metrics(y_val, y_val_pred, y_val_proba),
            'test': self.calculate_metrics(y_test, y_test_pred, y_test_proba),
            'training_time_seconds': round(training_time, 2),
            'model_name': 'XGBoost',
            'feature_count': X_train.shape[1] if len(X_train.shape) == 2 else X_train.shape[2],
            'sequence_length': X_train.shape[1] if len(X_train.shape) == 3 else 1,
            'flattened_features': X_train_2d.shape[1]
        }
        
        # Save model
        model_path = self.output_dir / 'xgboost_model.pkl'
        joblib.dump(self.model, model_path)
        print(f"   ✅ Model saved to: {model_path}")
        
        # Also save as JSON for compatibility
        json_path = self.output_dir / 'xgboost_model.json'
        self.model.save_model(str(json_path))
        print(f"   ✅ Model saved as JSON to: {json_path}")
        
        # Save feature info
        feature_info = {
            'feature_cols': feature_cols if feature_cols else [f'feature_{i}' for i in range(metrics['feature_count'])],
            'sequence_length': metrics['sequence_length'],
            'feature_count': metrics['feature_count'],
            'flattened_features': metrics['flattened_features']
        }
        
        feature_info_path = self.output_dir / 'xgboost_feature_info.json'
        import json
        with open(feature_info_path, 'w') as f:
            json.dump(feature_info, f, indent=2)
        print(f"   ✅ Feature info saved to: {feature_info_path}")
        
        # Plot confusion matrix
        self.plot_confusion_matrix(y_test, y_test_pred, "XGBoost")
        
        # Plot feature importance (top 20)
        self.plot_feature_importance(metrics['feature_count'])
        
        print(f"\n   ✅ Training completed in {training_time:.2f} seconds")
        print(f"\n   📊 VALIDATION SET METRICS:")
        print(f"      Accuracy:  {metrics['validation']['accuracy']:.4f}")
        print(f"      Precision: {metrics['validation']['precision']:.4f}")
        print(f"      Recall:    {metrics['validation']['recall']:.4f}")
        print(f"      F1-Score:  {metrics['validation']['f1_score']:.4f}")
        print(f"      ROC-AUC:   {metrics['validation']['roc_auc']:.4f}")
        
        print(f"\n   📊 TEST SET METRICS:")
        print(f"      Accuracy:  {metrics['test']['accuracy']:.4f}")
        print(f"      Precision: {metrics['test']['precision']:.4f}")
        print(f"      Recall:    {metrics['test']['recall']:.4f}")
        print(f"      F1-Score:  {metrics['test']['f1_score']:.4f}")
        print(f"      ROC-AUC:   {metrics['test']['roc_auc']:.4f}")
        
        return metrics
    
    def plot_confusion_matrix(self, y_true, y_pred, model_name):
        """Plot confusion matrix"""
        cm = confusion_matrix(y_true, y_pred)
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                    xticklabels=['No Swarm (0)', 'Swarm (1)'],
                    yticklabels=['No Swarm (0)', 'Swarm (1)'])
        plt.title(f'{model_name} - Confusion Matrix', fontsize=14)
        plt.ylabel('Actual Label', fontsize=12)
        plt.xlabel('Predicted Label', fontsize=12)
        
        tn, fp, fn, tp = cm.ravel()
        accuracy = (tp + tn) / (tp + tn + fp + fn)
        plt.figtext(0.5, -0.05, f'Accuracy: {accuracy:.4f} | TP: {tp} | TN: {tn} | FP: {fp} | FN: {fn}',
                   ha='center', fontsize=10)
        
        plt.tight_layout()
        plt.savefig(self.figures_dir / f'xgb_confusion_matrix.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"   ✅ Confusion matrix saved to: {self.figures_dir / f'xgb_confusion_matrix.png'}")
    
    def plot_feature_importance(self, n_features_per_timestep):
        """Plot top 20 feature importances"""
        if self.model is None:
            return
        
        # Get feature importances
        importances = self.model.feature_importances_
        
        # Create meaningful feature names
        feature_names = []
        if self.feature_cols:
            # If we have feature columns, create names based on them
            flattened_features = len(importances)
            if flattened_features == len(self.feature_cols):
                # Data is already flattened
                feature_names = self.feature_cols
            else:
                # Try to reconstruct sequence feature names
                seq_length = flattened_features // len(self.feature_cols) if len(self.feature_cols) > 0 else 1
                for t in range(seq_length):
                    for f in range(len(self.feature_cols)):
                        feature_names.append(f"t-{seq_length-t}_{self.feature_cols[f]}")
        else:
            # Generic feature names
            feature_names = [f"feature_{i}" for i in range(len(importances))]
        
        # Take top 20 or all if less than 20
        n_top = min(20, len(importances))
        indices = np.argsort(importances)[-n_top:]
        
        plt.figure(figsize=(10, 8))
        plt.barh(range(n_top), importances[indices])
        plt.yticks(range(n_top), [feature_names[i] for i in indices])
        plt.xlabel('Feature Importance')
        plt.title('XGBoost - Top {} Feature Importances'.format(n_top))
        plt.tight_layout()
        plt.savefig(self.figures_dir / 'xgb_feature_importance.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"   ✅ Feature importance plot saved to: {self.figures_dir / 'xgb_feature_importance.png'}")
    
    def predict(self, X):
        """Make predictions on new data"""
        if self.model is None:
            raise ValueError("Model not trained yet. Call train() first.")
        
        # Reshape if needed
        X_2d = self.reshape_for_sklearn(X)
        
        # Predict
        predictions = self.model.predict(X_2d)
        probabilities = self.model.predict_proba(X_2d)[:, 1]
        
        return predictions, probabilities
    
    def load_model(self, model_path=None):
        """Load a trained model"""
        if model_path is None:
            model_path = self.output_dir / 'xgboost_model.pkl'
        
        self.model = joblib.load(model_path)
        print(f"✅ Model loaded from: {model_path}")
        return self.model