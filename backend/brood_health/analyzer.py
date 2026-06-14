"""
Brood Health Analyzer – relative scoring (z‑score based)
Works for any hive weight / temperature scale (EU or Sri Lanka)
"""

import pandas as pd
import numpy as np
from pathlib import Path

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
ROLLING_WINDOW_HOURS = 168      # 7 days for baseline
STABILITY_WINDOW_HOURS = 6      # for BHSI (rolling 6h)
EPS = 1e-6

# Weights for final score (biological priority)
WEIGHTS = {
    'temperature': 0.40,
    'humidity': 0.25,
    'co2': 0.20,
    'weight': 0.15
}

# -------------------------------------------------------------------
# Helper: rolling z‑score (relative deviation)
# -------------------------------------------------------------------
def rolling_zscore(series, window_hours, freq='15min'):
    """Compute rolling mean & std, then z = (x - mean)/std."""
    # Convert to hourly based on freq if needed
    roll = series.rolling(window=window_hours, min_periods=int(window_hours*0.5))
    mean = roll.mean()
    std = roll.std()
    z = (series - mean) / (std + EPS)
    return z.fillna(0)

# -------------------------------------------------------------------
# Sub‑scores with directional penalties
# -------------------------------------------------------------------
def temp_score(z):
    """Penalise cold twice as much as heat."""
    penalty = abs(z) * (2.0 if z < 0 else 1.0)
    score = 100 * np.exp(- (penalty**2) / 4.5)   # k=1.5 → k²=2.25, multiplied by 2
    return np.clip(score, 0, 100)

def humidity_score(z):
    """Symmetric penalty (too dry or too wet)."""
    score = 100 * np.exp(- (z**2) / 4.5)
    return np.clip(score, 0, 100)

def co2_score(z):
    """Only high CO₂ is bad (z > 0)."""
    effective_z = max(0, z)
    score = 100 * np.exp(- (effective_z**2) / 4.5)
    return np.clip(score, 0, 100)

def weight_score(z):
    """Only weight loss (negative z) is penalised."""
    effective_z = max(0, -z)
    score = 100 * np.exp(- (effective_z**2) / 4.5)
    return np.clip(score, 0, 100)

# -------------------------------------------------------------------
# Brood Health Stability Index (BHSI) – 0 to 100
# -------------------------------------------------------------------
def compute_bhsi(group, window_hours=STABILITY_WINDOW_HOURS, freq='15min'):
    """
    BHSI = 100 - 100 * ( average CoV ) / 0.1
    CoV = std/mean for T, H, CO₂ over a rolling 6h window.
    Returns a Series aligned with group index.
    """
    # Rolling 6h = 24 rows (at 15min freq)
    window = int(window_hours * 60 / 15)   # e.g., 6h -> 24
    # Coefficient of variation for each sensor
    temp_cov = group['temp'].rolling(window, min_periods=window//2).std() / (group['temp'].rolling(window).mean() + EPS)
    hum_cov  = group['humidity'].rolling(window, min_periods=window//2).std() / (group['humidity'].rolling(window).mean() + EPS)
    co2_cov  = group['co2'].rolling(window, min_periods=window//2).std() / (group['co2'].rolling(window).mean() + EPS)
    avg_cov = (temp_cov + hum_cov + co2_cov) / 3.0
    # Normalise: assume worst acceptable CoV = 0.1 (10% variation)
    bhsi = 100 - 100 * (avg_cov / 0.1)
    bhsi = bhsi.clip(0, 100)
    return bhsi.fillna(50)   # default neutral during initial period

# -------------------------------------------------------------------
# Rate of Deterioration (RoD) – slope of Brood Health Score over last 4h
# -------------------------------------------------------------------
def compute_rod(brood_scores, timestamps, window_hours=4):
    """Linear regression slope of health score vs time (points/hour)."""
    if len(brood_scores) < 2:
        return 0.0
    # Use last `window_hours` of data (assumes 15min intervals -> 16 points)
    n_points = int(window_hours * 4)   # 4 readings per hour
    scores = brood_scores[-n_points:]
    times = np.arange(len(scores)) * 0.25   # hours
    if len(scores) < 2:
        return 0.0
    slope = np.polyfit(times, scores, 1)[0]
    return slope

# -------------------------------------------------------------------
# Main function: compute full brood health metrics for a DataFrame
# -------------------------------------------------------------------
def compute_brood_health_metrics(df):
    """
    Input df must have columns: hive, timestamp, temp, humidity, co2, weight
    Output: DataFrame with added columns:
        - brood_health_score (0-100)
        - bhsi (0-100)
        - rod (points/hour)
        - health_level (Excellent, Good, Poor, Critical)
        - stability_level (High, Moderate, Low)
        - trend_label (Rapid improving, Slow improving, Stable, Slow declining, Rapid declining)
    """
    df = df.copy()
    # Ensure sorted per hive
    df = df.sort_values(['hive', 'timestamp']).reset_index(drop=True)

    # 1. Compute rolling z‑scores (7‑day baseline = 168h)
    df['z_temp'] = df.groupby('hive')['temp'].transform(
        lambda x: rolling_zscore(x, ROLLING_WINDOW_HOURS)
    )
    df['z_hum'] = df.groupby('hive')['humidity'].transform(
        lambda x: rolling_zscore(x, ROLLING_WINDOW_HOURS)
    )
    df['z_co2'] = df.groupby('hive')['co2'].transform(
        lambda x: rolling_zscore(x, ROLLING_WINDOW_HOURS)
    )
    df['z_weight'] = df.groupby('hive')['weight'].transform(
        lambda x: rolling_zscore(x, ROLLING_WINDOW_HOURS)
    )

    # 2. Per‑row sub‑scores
    df['temp_sub'] = df['z_temp'].apply(temp_score)
    df['hum_sub']  = df['z_hum'].apply(humidity_score)
    df['co2_sub']  = df['z_co2'].apply(co2_score)
    df['weight_sub'] = df['z_weight'].apply(weight_score)

    # 3. Weighted brood health score
    df['brood_health_score'] = (
        WEIGHTS['temperature'] * df['temp_sub'] +
        WEIGHTS['humidity'] * df['hum_sub'] +
        WEIGHTS['co2'] * df['co2_sub'] +
        WEIGHTS['weight'] * df['weight_sub']
    ).round(1).clip(0, 100)

    # 4. BHSI (rolling stability)
    df['bhsi'] = df.groupby('hive', group_keys=False).apply(
        lambda g: compute_bhsi(g)
    ).round(1)

    # 5. Rate of Deterioration (rolling 4h slope) – per hive, forward fill
    df['rod'] = 0.0
    for hive, group in df.groupby('hive'):
        scores = group['brood_health_score'].values
        rod_vals = []
        for i in range(1, len(scores)+1):
            window_scores = scores[max(0, i-16):i]   # last 4h = 16 points
            rod = compute_rod(window_scores, None, 4) if len(window_scores) >= 2 else 0.0
            rod_vals.append(rod)
        df.loc[group.index, 'rod'] = rod_vals

    # 6. Classifications
    def classify_health(score):
        if score >= 80: return "Excellent"
        if score >= 60: return "Good"
        if score >= 40: return "Poor"
        return "Critical"

    def classify_stability(bhsi):
        if bhsi >= 70: return "High"
        if bhsi >= 40: return "Moderate"
        return "Low"

    def classify_trend(rod):
        if rod > 3.0: return "Rapid Improving"
        if rod > 0.5: return "Slow Improving"
        if rod >= -0.5: return "Stable"
        if rod >= -3.0: return "Slow Declining"
        return "Rapid Declining"

    df['health_level'] = df['brood_health_score'].apply(classify_health)
    df['stability_level'] = df['bhsi'].apply(classify_stability)
    df['trend_label'] = df['rod'].apply(classify_trend)

    # Keep only relevant columns for output (optional)
    out_cols = ['hive', 'timestamp', 'temp', 'humidity', 'co2', 'weight',
                'brood_health_score', 'bhsi', 'rod', 'health_level',
                'stability_level', 'trend_label']
    return df[out_cols]

# -------------------------------------------------------------------
# For standalone testing
# -------------------------------------------------------------------
if __name__ == "__main__":
    # Example load data
    data_path = Path(__file__).parents[1] / 'data' / 'hive_data_with_features.csv'
    if data_path.exists():
        df = pd.read_csv(data_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # Ensure required columns exist (rename if needed)
        df = df.rename(columns={
            'internal_temperature_c': 'temp',
            'internal_humidity_pct': 'humidity',
            'co2_ppm': 'co2',
            'hive_weight_kg': 'weight'
        })
        result = compute_brood_health_metrics(df)
        print(result.head())
        result.to_csv('brood_health_output.csv', index=False)