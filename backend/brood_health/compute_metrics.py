import pandas as pd
import json
from pathlib import Path
from .analyzer import compute_brood_health_metrics

def generate_brood_health_json():
    # Load data
    data_path = Path(__file__).parents[1] / 'data' / 'hive_data_with_features.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.rename(columns={
        'internal_temperature_c': 'temp',
        'internal_humidity_pct': 'humidity',
        'co2_ppm': 'co2',
        'hive_weight_kg': 'weight'
    })
    
    # Compute all metrics
    result_df = compute_brood_health_metrics(df)
    
    # Prepare per‑hive summary for frontend
    summary = []
    for hive, group in result_df.groupby('hive'):
        latest = group.iloc[-1]
        summary.append({
            'hive': hive,
            'current_score': latest['brood_health_score'],
            'health_level': latest['health_level'],
            'bhsi': latest['bhsi'],
            'stability_level': latest['stability_level'],
            'rod': latest['rod'],
            'trend_label': latest['trend_label'],
            'avg_score': round(group['brood_health_score'].mean(), 1),
            'avg_bhsi': round(group['bhsi'].mean(), 1),
        })
    
    # Time series for each hive (last 500 points max)
    time_series = {}
    for hive, group in result_df.groupby('hive'):
        ts = group[['timestamp', 'brood_health_score', 'bhsi', 'rod']].tail(500)
        ts['timestamp'] = ts['timestamp'].astype(str)
        time_series[hive] = ts.to_dict(orient='records')
    
    output = {
        'summary': summary,
        'time_series': time_series,
        'all_data': result_df.to_dict(orient='records')  # optional, can be large
    }
    
    out_path = Path(__file__).parent / 'outputs' / 'brood_health_analysis.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"✅ Brood health data saved to {out_path}")

if __name__ == "__main__":
    generate_brood_health_json()