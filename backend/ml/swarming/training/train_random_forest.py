"""
Random Forest Classifier for Swarming Prediction - FAST VERSION
Optimized for large datasets
"""

import numpy as np
import pandas as pd
from pathlib import Path
import joblib
import time
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                            f1_score, roc_auc_score, confusion_matrix)
import warnings
warnings.filterwarnings('ignore')


class RandomForestSwarmingModel:
    def __init__(self, output_dir=None, figures_dir=None):
        self.output_dir = output_dir or Path(__file__).parent.parent.parent.parent / 'ml' / 'swarming' / 'models'
        self.figures_dir = figures_dir or self.output_dir.parent / 'outputs' / 'swarming' / 'figures'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        self.model = None
        
    def aggregate_features(self, X):
        """
        Aggregate time series features to reduce dimensionality
        Handles both 2D (flattened) and 3D (sequence) data
        """
        print(f"   Aggregating features...")
        
        # Check dimensionality
        if len(X.shape) == 2:
            # Already flattened - need to detect if it came from sequences
            print(f"   Input is 2D with shape {X.shape}")
            
            n_samples = X.shape[0]
            n_features = X.shape[1]
            
            # Try to determine original sequence length
            # Common sequence lengths: 288 (24h), 144 (12h), 96 (8h), 72 (6h), 48 (4h), 24 (2h)
            possible_seq_lengths = [288, 144, 96, 72, 48, 24, 12]
            seq_length = None
            n_features_per_step = None
            
            for seq_len in possible_seq_lengths:
                if n_features % seq_len == 0:
                    n_features_per_step = n_features // seq_len
                    # Reasonable number of features per timestep (2-20)
                    if 2 <= n_features_per_step <= 20:
                        seq_length = seq_len
                        break
            
            if seq_length is not None and n_features_per_step is not None:
                print(f"   Detected {seq_length} timesteps × {n_features_per_step} features")
                print(f"   Reshaping from {n_features} features...")
                X_reshaped = X.reshape(n_samples, seq_length, n_features_per_step)
                return self._aggregate_3d_features(X_reshaped)
            else:
                # Can't determine shape, use statistical features on flattened data
                print(f"   Cannot determine sequence shape, using statistical features on flattened data...")
                return self._aggregate_2d_features(X)
        
        elif len(X.shape) == 3:
            return self._aggregate_3d_features(X)
        else:
            raise ValueError(f"Expected 2D or 3D input, got shape {X.shape}")
    
    def _aggregate_3d_features(self, X):
        """Aggregate features from 3D sequence data (samples, timesteps, features)"""
        n_samples, seq_length, n_features = X.shape
        print(f"   Processing {n_samples} sequences of {seq_length} timesteps × {n_features} features")
        print(f"   Reducing from {seq_length * n_features} to ~20 features per sample...")
        
        # Calculate total features we'll generate
        # For each of the n_features, we add 7 statistics = n_features * 7
        # Plus additional features (rolling, correlations, frequency)
        total_features = min(n_features * 7 + 10, 30)  # Cap at 30 features
        X_agg = np.zeros((n_samples, total_features))
        
        for i in range(n_samples):
            sample_data = X[i]  # Shape: (seq_length, n_features)
            
            feature_idx = 0
            
            # Statistics for each feature across time
            for f in range(n_features):
                feature_series = sample_data[:, f]
                
                # Basic statistics (7 values)
                stats = [
                    np.mean(feature_series),           # mean
                    np.std(feature_series),            # std
                    np.min(feature_series),            # min
                    np.max(feature_series),            # max
                    np.percentile(feature_series, 25), # Q1
                    np.percentile(feature_series, 75), # Q3
                    feature_series[-1] - feature_series[0]  # trend
                ]
                
                # Check if we have space for all 7 stats
                if feature_idx + 7 <= total_features:
                    X_agg[i, feature_idx:feature_idx+7] = stats
                    feature_idx += 7
                else:
                    # Not enough space, add what we can
                    remaining = total_features - feature_idx
                    if remaining > 0:
                        X_agg[i, feature_idx:feature_idx+remaining] = stats[:remaining]
                    feature_idx = total_features
                    break
            
            # Add rolling statistics for first feature (if space remains)
            if feature_idx < total_features and seq_length > 10:
                window = min(50, seq_length // 10)
                if window > 1:
                    feature_series = sample_data[:, 0]
                    rolling_means = np.convolve(feature_series, np.ones(window)/window, mode='valid')
                    if len(rolling_means) > 0 and feature_idx + 3 <= total_features:
                        rolling_stats = [
                            np.mean(rolling_means),              # average rolling mean
                            rolling_means[-1],                   # last rolling mean
                            rolling_means[-1] - rolling_means[0] if len(rolling_means) > 1 else 0  # trend
                        ]
                        X_agg[i, feature_idx:feature_idx+3] = rolling_stats
                        feature_idx += 3
            
            # Add cross-feature correlation (if space remains)
            if feature_idx < total_features and n_features >= 2:
                corr_matrix = np.corrcoef(sample_data[:, 0], sample_data[:, 1])
                X_agg[i, feature_idx] = corr_matrix[0, 1] if not np.isnan(corr_matrix[0, 1]) else 0
                feature_idx += 1
            
            # Add frequency domain features (if space remains)
            if feature_idx + 2 <= total_features:
                feature_series = sample_data[:, 0]
                fft_vals = np.abs(np.fft.rfft(feature_series))
                if len(fft_vals) > 5:
                    X_agg[i, feature_idx:feature_idx+2] = [
                        np.sum(fft_vals[1:5]) if len(fft_vals) > 5 else 0,  # low frequency energy
                        fft_vals[1] if len(fft_vals) > 1 else 0  # dominant frequency
                    ]
        
        print(f"   Aggregated shape: {X_agg.shape}")
        return X_agg
    
    def _aggregate_2d_features(self, X):
        """Aggregate features from 2D flattened data using statistical methods"""
        n_samples = X.shape[0]
        n_features = X.shape[1]
        print(f"   Processing {n_samples} samples with {n_features} flattened features")
        
        X_agg = np.zeros((n_samples, 20))
        
        for i in range(n_samples):
            sample = X[i]
            
            # Global statistics
            X_agg[i, 0:10] = [
                np.mean(sample),           # overall mean
                np.std(sample),            # overall std
                np.min(sample),            # min
                np.max(sample),            # max
                np.percentile(sample, 25), # Q1
                np.percentile(sample, 50), # median
                np.percentile(sample, 75), # Q3
                np.sum(np.abs(np.diff(sample))),  # total variation
                np.mean(np.abs(np.diff(sample))), # mean absolute change
                np.ptp(sample)             # peak-to-peak
            ]
            
            # Frequency domain features
            fft_vals = np.abs(np.fft.rfft(sample))
            if len(fft_vals) > 5:
                X_agg[i, 10:15] = [
                    fft_vals[1] if len(fft_vals) > 1 else 0,
                    fft_vals[2] if len(fft_vals) > 2 else 0,
                    np.mean(fft_vals[1:10]) if len(fft_vals) > 10 else 0,
                    np.std(fft_vals[1:10]) if len(fft_vals) > 10 else 0,
                    np.sum(fft_vals[1:5]) if len(fft_vals) > 5 else 0
                ]
            
            # Rolling statistics
            window = min(50, n_features // 10)
            if window > 1:
                rolling_means = np.convolve(sample, np.ones(window)/window, mode='valid')
                if len(rolling_means) > 0:
                    X_agg[i, 15:20] = [
                        np.mean(rolling_means),
                        np.std(rolling_means),
                        np.min(rolling_means),
                        np.max(rolling_means),
                        rolling_means[-1] - rolling_means[0]
                    ]
        
        print(f"   Aggregated shape: {X_agg.shape}")
        return X_agg
    
    def handle_imbalance(self, X_train, y_train):
        """Simple class weighting instead of SMOTE (faster)"""
        from sklearn.utils.class_weight import compute_class_weight
        
        classes = np.unique(y_train)
        weights = compute_class_weight('balanced', classes=classes, y=y_train)
        class_weight = dict(zip(classes, weights))
        
        print(f"   Class weights: {class_weight}")
        return class_weight
    
    def calculate_metrics(self, y_true, y_pred, y_proba):
        """Calculate metrics"""
        return {
            'accuracy': round(accuracy_score(y_true, y_pred), 4),
            'precision': round(precision_score(y_true, y_pred, zero_division=0), 4),
            'recall': round(recall_score(y_true, y_pred, zero_division=0), 4),
            'f1_score': round(f1_score(y_true, y_pred, zero_division=0), 4),
            'roc_auc': round(roc_auc_score(y_true, y_proba), 4) if len(np.unique(y_true)) > 1 else 0.5,
            'confusion_matrix': confusion_matrix(y_true, y_pred).tolist()
        }
    
    def train(self, X_train, y_train, X_val, y_val, X_test, y_test, feature_cols=None):
        """Train Random Forest with aggregated features"""
        print("\n" + "="*70)
        print("TRAINING RANDOM FOREST (Optimized - Aggregated Features)")
        print("="*70)
        
        start_time = time.time()
        
        # Print input shapes
        print(f"\n[1/5] Input data shapes:")
        print(f"   X_train shape: {X_train.shape}")
        print(f"   X_val shape: {X_val.shape}")
        print(f"   X_test shape: {X_test.shape}")
        
        # Aggregate features (reduce dimensionality)
        print("\n[2/5] Aggregating features...")
        X_train_agg = self.aggregate_features(X_train)
        X_val_agg = self.aggregate_features(X_val)
        X_test_agg = self.aggregate_features(X_test)
        
        print(f"   Aggregated X_train shape: {X_train_agg.shape}")
        print(f"   Aggregated X_val shape: {X_val_agg.shape}")
        print(f"   Aggregated X_test shape: {X_test_agg.shape}")
        
        # Handle imbalance with class weights
        print("\n[3/5] Setting class weights...")
        class_weight = self.handle_imbalance(X_train_agg, y_train)
        
        # Sample data for faster training if needed
        print("\n[4/5] Training Random Forest...")
        n_samples = len(X_train_agg)
        use_sampling = n_samples > 50000
        
        if use_sampling:
            print(f"   Using random {50000} samples from {n_samples} for faster training")
            indices = np.random.choice(n_samples, 50000, replace=False)
            X_train_sample = X_train_agg[indices]
            y_train_sample = y_train[indices]
        else:
            X_train_sample = X_train_agg
            y_train_sample = y_train
            print(f"   Using all {n_samples} training samples")
        
        # Check class balance in training sample
        pos_percent = np.mean(y_train_sample) * 100
        print(f"   Training set positive class: {pos_percent:.2f}%")
        
        # Train with optimized parameters
        self.model = RandomForestClassifier(
            n_estimators=100,        # Reduced from 200
            max_depth=15,            # Moderate depth
            min_samples_split=20,    # Increased for speed
            min_samples_leaf=10,     # Increased for speed
            max_features='sqrt',     # Use sqrt of features
            class_weight=class_weight,
            random_state=42,
            n_jobs=-1,               # Use all CPU cores
            verbose=1
        )
        
        self.model.fit(X_train_sample, y_train_sample)
        
        training_time = time.time() - start_time
        
        # Predictions
        print("\n[5/5] Evaluating model...")
        
        # Validation set evaluation
        y_val_pred = self.model.predict(X_val_agg)
        y_val_proba = self.model.predict_proba(X_val_agg)[:, 1] if hasattr(self.model, "predict_proba") else np.zeros(len(y_val))
        val_metrics = self.calculate_metrics(y_val, y_val_pred, y_val_proba)
        
        # Test set evaluation
        y_test_pred = self.model.predict(X_test_agg)
        y_test_proba = self.model.predict_proba(X_test_agg)[:, 1] if hasattr(self.model, "predict_proba") else np.zeros(len(y_test))
        test_metrics = self.calculate_metrics(y_test, y_test_pred, y_test_proba)
        
        # Metrics dictionary
        metrics = {
            'train': {
                'accuracy': self.model.score(X_train_sample, y_train_sample),
                'samples': len(y_train_sample)
            },
            'validation': val_metrics,
            'test': test_metrics,
            'training_time_seconds': round(training_time, 2),
            'model_name': 'Random Forest',
            'feature_count': X_train_agg.shape[1],
            'n_estimators': 100,
            'used_sampling': use_sampling,
            'original_samples': n_samples,
            'sampled_samples': len(y_train_sample) if use_sampling else n_samples
        }
        
        # Save model
        model_path = self.output_dir / 'random_forest_model.pkl'
        joblib.dump(self.model, model_path)
        print(f"   ✅ Model saved to: {model_path}")
        
        # Save feature info
        feature_info = {
            'feature_cols': feature_cols if feature_cols else [f'feature_{i}' for i in range(X_train_agg.shape[1])],
            'aggregated_features': True,
            'original_shape': X_train.shape,
            'aggregated_shape': X_train_agg.shape
        }
        
        feature_info_path = self.output_dir / 'random_forest_feature_info.json'
        import json
        with open(feature_info_path, 'w') as f:
            json.dump(feature_info, f, indent=2)
        print(f"   ✅ Feature info saved to: {feature_info_path}")
        
        print(f"\n   ✅ Training completed in {training_time:.2f} seconds")
        print(f"\n   📊 VALIDATION SET METRICS:")
        print(f"      Accuracy:  {val_metrics['accuracy']:.4f}")
        print(f"      Precision: {val_metrics['precision']:.4f}")
        print(f"      Recall:    {val_metrics['recall']:.4f}")
        print(f"      F1-Score:  {val_metrics['f1_score']:.4f}")
        print(f"      ROC-AUC:   {val_metrics['roc_auc']:.4f}")
        
        print(f"\n   📊 TEST SET METRICS:")
        print(f"      Accuracy:  {test_metrics['accuracy']:.4f}")
        print(f"      Precision: {test_metrics['precision']:.4f}")
        print(f"      Recall:    {test_metrics['recall']:.4f}")
        print(f"      F1-Score:  {test_metrics['f1_score']:.4f}")
        print(f"      ROC-AUC:   {test_metrics['roc_auc']:.4f}")
        
        return metrics
    
    def predict(self, X):
        """Make predictions on new data"""
        if self.model is None:
            raise ValueError("Model not trained yet. Call train() first.")
        
        # Aggregate features first
        X_agg = self.aggregate_features(X)
        
        # Predict
        predictions = self.model.predict(X_agg)
        probabilities = self.model.predict_proba(X_agg)[:, 1] if hasattr(self.model, "predict_proba") else None
        
        return predictions, probabilities
    
    def load_model(self, model_path=None):
        """Load a trained model"""
        if model_path is None:
            model_path = self.output_dir / 'random_forest_model.pkl'
        
        self.model = joblib.load(model_path)
        print(f"✅ Model loaded from: {model_path}")
        return self.model