"""
Probability Distribution Analysis for Trained Random Forest Model
"""

import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split

# Import the Random Forest model class to use its aggregate_features method
import sys
sys.path.append(str(Path(__file__).parent))
from train_random_forest import RandomForestSwarmingModel

print("=" * 60)
print("PROBABILITY DISTRIBUTION ANALYSIS")
print("=" * 60)

base_path = Path(__file__).parent.parent.parent.parent

# Paths
model_path = base_path / 'ml' / 'swarming' / 'models' / 'random_forest_model.pkl'
csv_path = base_path / 'data' / 'processed' / 'swarming' / 'processed_data.csv'

print(f"\n📁 Model path: {model_path}")
print(f"📁 CSV path: {csv_path}")

# Step 1: Load the trained model
print("\n[1/5] Loading trained Random Forest model...")
rf_model = joblib.load(model_path)
print("✅ Model loaded")

# Step 2: Create an instance of RandomForestSwarmingModel to use its aggregation method
rf_wrapper = RandomForestSwarmingModel()
print("✅ RandomForestSwarmingModel initialized")

# Step 3: Load and prepare data
print("\n[2/5] Loading data from CSV...")
df = pd.read_csv(csv_path)
print(f"✅ Loaded {len(df)} records")

# Step 4: Create sequences (same as in model_comparison.py)
print("\n[3/5] Creating sequences...")

sequence_length = 288

# Identify numeric feature columns
exclude_cols = ['swarming_event', 'timestamp', 'hive_id', 'date', 'time', 'label', 'hive']
numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
feature_cols = [col for col in numeric_cols if col not in exclude_cols and col != 'label']

# Get target column
if 'label' in df.columns:
    target_col = 'label'
elif 'swarming_event' in df.columns:
    target_col = 'swarming_event'
else:
    target_col = None

print(f"   Using features: {feature_cols}")

X_sequences = []
y_labels = []

if 'hive' in df.columns:
    hives = df['hive'].unique()
    print(f"   Processing {len(hives)} hives...")
    
    for hive in hives:
        hive_data = df[df['hive'] == hive].sort_values('time' if 'time' in df.columns else df.index)
        
        if len(hive_data) <= sequence_length:
            continue
            
        hive_features = hive_data[feature_cols].values.astype(np.float32)
        
        if target_col and target_col in hive_data.columns:
            hive_labels = hive_data[target_col].values
        else:
            hive_labels = np.zeros(len(hive_data))
        
        for i in range(len(hive_features) - sequence_length):
            sequence = hive_features[i:i + sequence_length]
            label = 1 if np.sum(hive_labels[i + 1:i + sequence_length + 1]) > 0 else 0
            X_sequences.append(sequence)
            y_labels.append(label)
else:
    features = df[feature_cols].values.astype(np.float32)
    if target_col and target_col in df.columns:
        labels = df[target_col].values
    else:
        labels = np.zeros(len(df))
    
    for i in range(len(features) - sequence_length):
        X_sequences.append(features[i:i + sequence_length])
        y_labels.append(1 if np.sum(labels[i + 1:i + sequence_length + 1]) > 0 else 0)

X = np.array(X_sequences, dtype=np.float32)
y = np.array(y_labels, dtype=np.int8)

print(f"   Created {len(X)} sequences")

# Step 5: Split data
print("\n[4/5] Splitting data...")

indices = np.random.permutation(len(X))
X_shuffled = X[indices]
y_shuffled = y[indices]

split_idx = int(0.7 * len(X_shuffled))
X_train = X_shuffled[:split_idx]
y_train = y_shuffled[:split_idx]
X_temp = X_shuffled[split_idx:]
y_temp = y_shuffled[split_idx:]

val_split = int(0.5 * len(X_temp))
X_val = X_temp[:val_split]
y_val = y_temp[:val_split]
X_test = X_temp[val_split:]
y_test = y_temp[val_split]

print(f"   Test set size: {len(X_test)} sequences")
print(f"   Test set shape: {X_test.shape}")

# Step 6: Aggregate features (THIS IS THE KEY STEP)
print("\n[5/5] Aggregating features and getting probabilities...")

# Use the wrapper's aggregate_features method (same as during training)
X_test_aggregated = rf_wrapper.aggregate_features(X_test)
print(f"   Aggregated test shape: {X_test_aggregated.shape}")

# Now predict using the aggregated features
probabilities = rf_model.predict_proba(X_test_aggregated)[:, 1]

# Results
print("\n" + "=" * 60)
print("PROBABILITY DISTRIBUTION RESULTS")
print("=" * 60)

min_prob = np.min(probabilities)
max_prob = np.max(probabilities)
avg_prob = np.mean(probabilities)
std_prob = np.std(probabilities)

print(f"\n📊 Basic Statistics:")
print(f"   Minimum probability: {min_prob:.4f} ({min_prob*100:.2f}%)")
print(f"   Maximum probability: {max_prob:.4f} ({max_prob*100:.2f}%)")
print(f"   Average probability: {avg_prob:.4f} ({avg_prob*100:.2f}%)")
print(f"   Standard deviation:  {std_prob:.4f}")

# Count by risk levels
low = np.sum(probabilities < 0.40)
medium = np.sum((probabilities >= 0.40) & (probabilities < 0.70))
high = np.sum(probabilities >= 0.70)
total = len(probabilities)

print(f"\n📊 Risk Level Distribution (thresholds 40% and 70%):")
print(f"   Low risk (below 40%):     {low:6,} samples ({low/total*100:.2f}%)")
print(f"   Medium risk (40-70%):     {medium:6,} samples ({medium/total*100:.2f}%)")
print(f"   High risk (above 70%):    {high:6,} samples ({high/total*100:.2f}%)")
print(f"   ─────────────────────────────────")
print(f"   Total:                     {total:6,} samples (100%)")

# Insights
print(f"\n📊 Key Insights:")
if low > total * 0.95:
    print(f"   ✅ Most samples ({low/total*100:.1f}%) are LOW risk - normal operation")
if high > 0:
    print(f"   ⚠️  {high} samples ({high/total*100:.2f}%) are HIGH risk - immediate action needed")
if medium > 0:
    print(f"   📋 {medium} samples ({medium/total*100:.2f}%) are MEDIUM risk - prepare equipment")

print("\n" + "=" * 60)
print("✅ Analysis Complete!")
print("=" * 60)