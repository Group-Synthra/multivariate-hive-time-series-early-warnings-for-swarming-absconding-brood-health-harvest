"""
Simple Swarming Data Preprocessor
Fast processing for large datasets (277k+ records)
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from pathlib import Path
import joblib
import warnings
warnings.filterwarnings('ignore')


class SimpleSwarmingPreprocessor:
    def __init__(self):
        self.scaler = MinMaxScaler()
        self.feature_cols = None
        
    def process(self, data_path, output_dir):
        """Main processing function - simple and fast"""
        
        print("\n" + "="*60)
        print("SIMPLE SWARMING DATA PREPROCESSOR")
        print("="*60)
        
        # Step 1: Load data
        print("\n[1/5] Loading data...")
        df = pd.read_csv(data_path)
        print(f"   Loaded {len(df):,} rows")
        
        # Step 2: Select and rename columns
        print("\n[2/5] Selecting features...")
        df = df.rename(columns={
            'hive_id': 'hive',
            'timestamp': 'time',
            'internal_temperature_c': 'temp',
            'internal_humidity_pct': 'humidity',
            'co2_ppm': 'co2',
            'hive_weight_kg': 'weight'
        })
        
        # Convert time
        df['time'] = pd.to_datetime(df['time'])
        
        # Select features (simplified)
        self.feature_cols = ['temp', 'humidity', 'co2', 'weight']
        print(f"   Using features: {self.feature_cols}")
        
        # Step 3: Simple cleaning (remove extreme outliers)
        print("\n[3/5] Cleaning data...")
        for col in self.feature_cols:
            # Remove unreasonable values
            if col == 'temp':
                df = df[(df[col] > 0) & (df[col] < 50)]
            elif col == 'humidity':
                df = df[(df[col] > 0) & (df[col] <= 100)]
            elif col == 'co2':
                df = df[(df[col] > 0) & (df[col] < 50000)]
            elif col == 'weight':
                df = df[(df[col] > 0) & (df[col] < 100)]
        
        print(f"   After cleaning: {len(df):,} rows")
        
        # Step 4: Create labels (if not present)
        print("\n[4/5] Creating labels...")
        if 'swarming_event_label' in df.columns:
            df['label'] = df['swarming_event_label']
            print("   Using existing swarming labels")
        else:
            # Simple rule-based labeling
            # Calculate weight drop
            df['weight_change'] = df.groupby('hive')['weight'].diff(-1)
            # Label as swarm if weight drop > 0.5 kg in 1 hour
            df['label'] = (df['weight_change'] < -0.5).astype(int)
            print("   Created labels using weight drop rule")
        
        print(f"   Swarming events: {df['label'].sum():,} ({df['label'].mean()*100:.2f}%)")
        
        # Step 5: Normalize features
        print("\n[5/5] Normalizing features...")
        df[self.feature_cols] = self.scaler.fit_transform(df[self.feature_cols])
        
        # Save results
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save processed data as CSV (easier to inspect)
        output_csv = output_dir / 'processed_data.csv'
        df[['hive', 'time', 'temp', 'humidity', 'co2', 'weight', 'label']].to_csv(output_csv, index=False)
        print(f"   ✅ Saved CSV to: {output_csv}")
        
        # Save scaler
        joblib.dump(self.scaler, output_dir / 'scaler.pkl')
        print(f"   ✅ Saved scaler to: {output_dir / 'scaler.pkl'}")
        
        # Create sequences (fixed window)
        print("\n" + "="*60)
        print("CREATING SEQUENCES FOR LSTM")
        print("="*60)
        
        WINDOW = 72  # 72 hours (3 days)
        
        X, y = [], []
        
        for hive in df['hive'].unique():
            hive_data = df[df['hive'] == hive].sort_values('time')
            features = hive_data[self.feature_cols].values
            labels = hive_data['label'].values
            
            for i in range(len(features) - WINDOW):
                X.append(features[i:i+WINDOW])
                y.append(labels[i+WINDOW])
        
        X = np.array(X)
        y = np.array(y)
        
        print(f"   Created {len(X)} sequences")
        print(f"   X shape: {X.shape}")
        print(f"   y shape: {y.shape}")
        print(f"   Sequences shape: {X.shape[1]} timesteps, {X.shape[2]} features")
        
        # Split data
        n = len(X)
        train_idx = int(n * 0.7)
        val_idx = int(n * 0.8)
        
        X_train, y_train = X[:train_idx], y[:train_idx]
        X_val, y_val = X[train_idx:val_idx], y[train_idx:val_idx]
        X_test, y_test = X[val_idx:], y[val_idx:]
        
        print(f"\n   Train: {len(X_train)} sequences")
        print(f"   Val:   {len(X_val)} sequences")
        print(f"   Test:  {len(X_test)} sequences")
        
        # Save as NPZ (compressed)
        np.savez_compressed(
            output_dir / 'sequences.npz',
            X_train=X_train, y_train=y_train,
            X_val=X_val, y_val=y_val,
            X_test=X_test, y_test=y_test,
            feature_cols=np.array(self.feature_cols)
        )
        print(f"\n✅ Saved sequences to: {output_dir / 'sequences.npz'}")
        
        # Print summary
        print("\n" + "="*60)
        print("PREPROCESSING COMPLETE!")
        print("="*60)
        print(f"\n📊 Final Summary:")
        print(f"   Total records: {len(df):,}")
        print(f"   Sequences: {len(X)}")
        print(f"   Features: {len(self.feature_cols)}")
        print(f"   Train: {len(X_train)}")
        print(f"   Validation: {len(X_val)}")
        print(f"   Test: {len(X_test)}")
        
        return {
            'X_train': X_train, 'y_train': y_train,
            'X_val': X_val, 'y_val': y_val,
            'X_test': X_test, 'y_test': y_test,
            'feature_cols': self.feature_cols
        }


if __name__ == "__main__":
    # Set paths
    BACKEND_DIR = Path(__file__).parent.parent.parent.parent
    DATA_PATH = BACKEND_DIR / 'data' / 'hive_data_with_features.csv'
    OUTPUT_DIR = BACKEND_DIR / 'data' / 'processed' / 'swarming'
    
    print(f"Data path: {DATA_PATH}")
    
    if DATA_PATH.exists():
        preprocessor = SimpleSwarmingPreprocessor()
        data = preprocessor.process(DATA_PATH, OUTPUT_DIR)
        
        print(f"\n✅ Ready for training!")
        print(f"   Run: python ml/swarming/training/model_comparison.py")
    else:
        print(f"❌ Data not found at {DATA_PATH}")