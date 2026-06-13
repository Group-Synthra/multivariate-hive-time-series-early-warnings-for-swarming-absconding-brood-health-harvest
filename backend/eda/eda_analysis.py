"""
EDA for ALL modules - WITH COMPREHENSIVE OUTLIER ANALYSIS
Integrated backend version - uses file-relative paths, generates dashboard.json
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server use
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

# ──────────────────────────────────────────────
# PATHS — all relative to this file's location
# ──────────────────────────────────────────────
THIS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = THIS_DIR.parent
DATA_PATH = BACKEND_DIR / 'data' / 'hive_data_with_features.csv'
OUTPUT_DIR = BACKEND_DIR / 'outputs' / 'eda_complete'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────
# PLOT STYLE
# ──────────────────────────────────────────────
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['figure.dpi'] = 100


# ──────────────────────────────────────────────
# 1. DATA LOADING
# ──────────────────────────────────────────────
def load_data():
    """
    Load and prepare the uploaded hive dataset.

    The source CSV uses descriptive column names such as ``hive_id`` and
    ``internal_temperature_c``. The existing EDA functions use the shorter
    analysis names ``hive``, ``temp``, ``humidity``, ``co2`` and ``weight``.
    This function creates those aliases while retaining every original column.
    """
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"CSV not found at {DATA_PATH}\\n"
            "Copy hive_data_with_features.csv into backend/data/"
        )

    df = pd.read_csv(DATA_PATH)

    # Remove accidental leading/trailing spaces from CSV headers.
    df.columns = df.columns.astype(str).str.strip()

    # Map the actual CSV schema to the names used throughout this EDA script.
    # New alias columns are created instead of deleting/renaming source columns.
    column_aliases = {
        'hive': 'hive_id',
        'temp': 'internal_temperature_c',
        'humidity': 'internal_humidity_pct',
        'co2': 'co2_ppm',
        'weight': 'hive_weight_kg',
    }

    created_aliases = []
    for analysis_name, source_name in column_aliases.items():
        if analysis_name not in df.columns and source_name in df.columns:
            df[analysis_name] = df[source_name]
            created_aliases.append(f"{source_name} → {analysis_name}")

    required_columns = ['timestamp', 'hive', 'temp', 'humidity', 'co2', 'weight']
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(
            "The CSV is missing columns required by the EDA pipeline.\\n"
            f"Missing analysis columns: {missing_columns}\\n"
            f"Available CSV columns: {df.columns.tolist()}\\n"
            "Expected source mapping: "
            "hive_id→hive, internal_temperature_c→temp, "
            "internal_humidity_pct→humidity, co2_ppm→co2, "
            "hive_weight_kg→weight."
        )

    # Parse and validate timestamps.
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    invalid_timestamp_count = int(df['timestamp'].isna().sum())
    if invalid_timestamp_count:
        raise ValueError(
            f"Found {invalid_timestamp_count:,} invalid timestamp value(s). "
            "Correct them in the CSV before running the EDA."
        )

    # Ensure all sensor columns are numeric.
    sensor_columns = ['temp', 'humidity', 'co2', 'weight']
    for column in sensor_columns:
        df[column] = pd.to_numeric(df[column], errors='coerce')

    missing_sensor_values = df[sensor_columns].isna().sum()
    missing_sensor_values = missing_sensor_values[missing_sensor_values > 0]
    if not missing_sensor_values.empty:
        details = ", ".join(
            f"{column}: {int(count):,}"
            for column, count in missing_sensor_values.items()
        )
        raise ValueError(
            "Non-numeric or missing values were found in required sensors: "
            f"{details}"
        )

    # All change/trend calculations must be performed chronologically per hive.
    df = df.sort_values(['hive', 'timestamp']).reset_index(drop=True)

    # Generate optional features expected by the anomaly sections when they are
    # not already present in the dataset.
    if 'weight_change' not in df.columns:
        df['weight_change'] = (
            df.groupby('hive', sort=False)['weight']
              .diff()
              .fillna(0.0)
        )

    if 'co2_trend' not in df.columns:
        df['co2_trend'] = (
            df.groupby('hive', sort=False)['co2']
              .diff()
              .fillna(0.0)
        )

    if 'temp_deviation' not in df.columns:
        rolling_temp_mean = (
            df.groupby('hive', sort=False)['temp']
              .transform(
                  lambda values: values.rolling(
                      window=24,
                      min_periods=1,
                      center=True
                  ).mean()
              )
        )
        df['temp_deviation'] = df['temp'] - rolling_temp_mean

    if created_aliases:
        print("✅ Adapted dataset columns:")
        for mapping in created_aliases:
            print(f"   {mapping}")

    print(f"✅ Loaded {len(df):,} records from {DATA_PATH}")
    print(f"   Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")
    print(f"   Hives: {df['hive'].nunique()} ({list(df['hive'].unique())})")
    return df


# ──────────────────────────────────────────────
# 2. OUTLIER ANALYSIS
# ──────────────────────────────────────────────
def outlier_analysis_all_sensors(df):
    print("\n" + "=" * 70)
    print("0. OUTLIER ANALYSIS FOR ALL FOUR SENSORS")
    print("=" * 70)

    sensors = ['co2', 'temp', 'humidity', 'weight']
    sensor_names = ['CO2 (ppm)', 'Temperature (°C)', 'Humidity (%)', 'Weight (kg)']
    outlier_results = {}

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    for idx, (sensor, name) in enumerate(zip(sensors, sensor_names)):
        row, col = idx // 2, idx % 2
        Q1 = df[sensor].quantile(0.25)
        Q3 = df[sensor].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        outliers = df[(df[sensor] < lower) | (df[sensor] > upper)]
        count = len(outliers)
        pct = count / len(df) * 100

        outlier_results[sensor] = {
            'Q1': round(Q1, 2), 'Q3': round(Q3, 2), 'IQR': round(IQR, 2),
            'lower_bound': round(lower, 2), 'upper_bound': round(upper, 2),
            'outlier_count': count, 'outlier_percent': round(pct, 2)
        }
        print(f"\n{sensor.upper()}: Q1={Q1:.2f}, Q3={Q3:.2f}, IQR={IQR:.2f}")
        print(f"  Normal range: [{lower:.2f}, {upper:.2f}]")
        print(f"  Outliers: {count} ({pct:.2f}%)")

        ax = axes[row, col]
        bp = ax.boxplot(df[sensor].dropna(), vert=True, patch_artist=True)
        bp['boxes'][0].set_facecolor('lightblue')
        bp['boxes'][0].set_alpha(0.7)
        ax.set_title(f'{name} — Boxplot', fontsize=12)
        ax.set_ylabel(name)
        ax.grid(True, alpha=0.3)
        ax.text(0.95, 0.95, f'Outliers: {count}\n({pct:.2f}%)',
                transform=ax.transAxes, ha='right', va='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.suptitle('Outlier Analysis — IQR Method (1.5× IQR)', fontsize=14)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'outlier_analysis_boxplots.png', dpi=150, bbox_inches='tight')
    plt.close()

    # Bar chart — outlier percentages
    fig, ax = plt.subplots(figsize=(10, 6))
    labels = ['CO2', 'Temperature', 'Humidity', 'Weight']
    pcts = [outlier_results[s]['outlier_percent'] for s in sensors]
    colors = ['green' if p < 1 else 'orange' if p < 5 else 'red' for p in pcts]
    bars = ax.bar(labels, pcts, color=colors, edgecolor='black')
    ax.set_ylabel('Outlier Percentage (%)')
    ax.set_title('Outlier Percentage by Sensor Type')
    ax.axhline(y=5, color='orange', linestyle='--', alpha=0.7, label='5% Warning')
    ax.axhline(y=10, color='red', linestyle='--', alpha=0.7, label='10% Critical')
    ax.legend()
    for bar, pct in zip(bars, pcts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f'{pct:.2f}%', ha='center', va='bottom', fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'outlier_percentage_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()

    # Time series with outliers highlighted (sample hive)
    sample_hive = df['hive'].unique()[0]
    hive_sample = df[df['hive'] == sample_hive].sort_values('timestamp')
    fig, axes = plt.subplots(4, 1, figsize=(15, 12), sharex=True)
    for idx, (sensor, name) in enumerate(zip(sensors, sensor_names)):
        lower = outlier_results[sensor]['lower_bound']
        upper = outlier_results[sensor]['upper_bound']
        outliers_hive = hive_sample[
            (hive_sample[sensor] < lower) | (hive_sample[sensor] > upper)
        ]
        axes[idx].plot(hive_sample['timestamp'], hive_sample[sensor],
                       color='blue', alpha=0.5, linewidth=0.5, label='Normal')
        if len(outliers_hive) > 0:
            axes[idx].scatter(outliers_hive['timestamp'], outliers_hive[sensor],
                              color='red', s=10, alpha=0.7, label='Outlier', zorder=5)
        axes[idx].axhline(y=lower, color='orange', linestyle='--', alpha=0.5)
        axes[idx].axhline(y=upper, color='orange', linestyle='--', alpha=0.5)
        axes[idx].set_ylabel(name)
        axes[idx].set_title(f'{name} — Outliers Highlighted ({sample_hive})')
        axes[idx].legend(loc='upper right', fontsize=8)
        axes[idx].grid(True, alpha=0.3)
    axes[-1].set_xlabel('Date')
    plt.suptitle('Time Series: Normal vs Outlier Points', fontsize=14)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'outlier_time_series.png', dpi=150, bbox_inches='tight')
    plt.close()

    # Save summary CSV
    summary_df = pd.DataFrame([
        {
            'Sensor': s.upper(),
            'Q1': outlier_results[s]['Q1'],
            'Q3': outlier_results[s]['Q3'],
            'IQR': outlier_results[s]['IQR'],
            'Lower Bound': outlier_results[s]['lower_bound'],
            'Upper Bound': outlier_results[s]['upper_bound'],
            'Outlier Count': outlier_results[s]['outlier_count'],
            'Outlier %': f"{outlier_results[s]['outlier_percent']:.2f}%"
        }
        for s in sensors
    ])
    summary_df.to_csv(OUTPUT_DIR / 'outlier_summary.csv', index=False)
    print(f"\nOutlier summary saved → {OUTPUT_DIR / 'outlier_summary.csv'}")
    return outlier_results


# ──────────────────────────────────────────────
# 3. OVERALL STATISTICS
# ──────────────────────────────────────────────
def overall_statistics(df):
    print("\n" + "=" * 70)
    print("1. OVERALL DATASET STATISTICS")
    print("=" * 70)
    sensors = ['co2', 'temp', 'humidity', 'weight']
    stats = {}
    for s in sensors:
        stats[s] = {
            'mean': round(df[s].mean(), 2),
            'std': round(df[s].std(), 2),
            'min': round(df[s].min(), 2),
            'q1': round(df[s].quantile(0.25), 2),
            'median': round(df[s].median(), 2),
            'q3': round(df[s].quantile(0.75), 2),
            'max': round(df[s].max(), 2),
        }
    stats_df = pd.DataFrame(stats).round(2)
    print(stats_df)
    stats_df.to_csv(OUTPUT_DIR / 'overall_statistics.csv')
    return stats


# ──────────────────────────────────────────────
# 4. CORRELATION ANALYSIS
# ──────────────────────────────────────────────
def correlation_analysis(df):
    print("\n" + "=" * 70)
    print("2. CORRELATION MATRIX")
    print("=" * 70)
    features = ['co2', 'temp', 'humidity', 'weight']
    optional = ['co2_trend', 'temp_trend', 'weight_change']
    all_feat = features + [f for f in optional if f in df.columns]
    corr = df[all_feat].corr()

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr, annot=True, cmap='coolwarm', center=0,
                fmt='.2f', square=True, ax=ax)
    ax.set_title('Feature Correlation Matrix (All Modules)', fontsize=14)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'correlation_matrix_all_modules.png', dpi=150, bbox_inches='tight')
    plt.close()

    result = {}
    for f1 in all_feat:
        result[f1] = {}
        for f2 in all_feat:
            result[f1][f2] = round(float(corr.loc[f1, f2]), 3)
    return result


# ──────────────────────────────────────────────
# 5. MULTI-HIVE COMPARISON
# ──────────────────────────────────────────────
def multi_hive_comparison(df):
    print("\n" + "=" * 70)
    print("3. MULTI-HIVE COMPARISON")
    print("=" * 70)
    hive_summary = df.groupby('hive')[['co2', 'temp', 'humidity', 'weight']].mean().round(2)
    print(hive_summary)

    fig, axes = plt.subplots(2, 2, figsize=(20, 10))
    for i, sensor in enumerate(['co2', 'temp', 'humidity', 'weight']):
        row, col = i // 2, i % 2
        df.boxplot(column=sensor, by='hive', ax=axes[row, col])
        axes[row, col].set_title(f'{sensor.upper()} by Hive')
        axes[row, col].set_xlabel('Hive')
    plt.suptitle('Hive Comparison — All Sensors', fontsize=12)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'hive_comparison_all_modules.png', dpi=150, bbox_inches='tight')
    plt.close()

    hive_stats = []
    for hive in df['hive'].unique():
        subset = df[df['hive'] == hive]
        hive_stats.append({
            'hive': hive,
            'co2_mean': round(float(subset['co2'].mean()), 2),
            'temp_mean': round(float(subset['temp'].mean()), 2),
            'humidity_mean': round(float(subset['humidity'].mean()), 2),
            'weight_mean': round(float(subset['weight'].mean()), 2),
            'weight_max': round(float(subset['weight'].max()), 2),
        })
    return hive_stats


# ──────────────────────────────────────────────
# 6. TEMPORAL PATTERNS
# ──────────────────────────────────────────────
def temporal_patterns(df):
    print("\n" + "=" * 70)
    print("4. TEMPORAL PATTERNS")
    print("=" * 70)
    df = df.copy()
    df['hour'] = df['timestamp'].dt.hour
    df['month'] = df['timestamp'].dt.month
    df['day_of_week'] = df['timestamp'].dt.dayofweek

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    hourly_temp = df.groupby('hour')['temp'].mean()
    axes[0, 0].plot(hourly_temp.index, hourly_temp.values, marker='o', color='red')
    axes[0, 0].axhline(y=35, color='blue', linestyle='--', label='Optimal')
    axes[0, 0].set_xlabel('Hour')
    axes[0, 0].set_ylabel('Temperature (°C)')
    axes[0, 0].set_title('Hourly Temperature Pattern')
    axes[0, 0].legend()

    daily_weight = df.groupby('hour')['weight'].mean()
    axes[0, 1].plot(daily_weight.index, daily_weight.values, marker='o', color='brown')
    axes[0, 1].set_xlabel('Hour')
    axes[0, 1].set_ylabel('Weight (kg)')
    axes[0, 1].set_title('Hourly Weight Pattern')

    monthly_co2 = df.groupby('month')['co2'].mean()
    axes[1, 0].bar(monthly_co2.index, monthly_co2.values, color='green')
    axes[1, 0].set_xlabel('Month')
    axes[1, 0].set_ylabel('CO2 (ppm)')
    axes[1, 0].set_title('Monthly CO2 Pattern')

    dow_temp = df.groupby('day_of_week')['temp'].mean()
    axes[1, 1].bar(dow_temp.index, dow_temp.values, color='orange')
    axes[1, 1].set_xlabel('Day of Week (0=Mon)')
    axes[1, 1].set_ylabel('Temperature (°C)')
    axes[1, 1].set_title('Temperature by Day of Week')

    plt.suptitle('Temporal Patterns (All Modules)', fontsize=14)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'temporal_patterns_all_modules.png', dpi=150, bbox_inches='tight')
    plt.close()

    hourly_patterns = []
    for hour in range(24):
        subset = df[df['hour'] == hour]
        hourly_patterns.append({
            'hour': hour,
            'temp': round(float(subset['temp'].mean()), 2) if len(subset) > 0 else 0,
            'humidity': round(float(subset['humidity'].mean()), 2) if len(subset) > 0 else 0,
            'co2': round(float(subset['co2'].mean()), 2) if len(subset) > 0 else 0,
            'weight': round(float(subset['weight'].mean()), 2) if len(subset) > 0 else 0,
        })
    return hourly_patterns


# ──────────────────────────────────────────────
# 7. DISTRIBUTIONS
# ──────────────────────────────────────────────
def distribution_analysis(df):
    print("\n" + "=" * 70)
    print("5. DISTRIBUTION ANALYSIS")
    print("=" * 70)
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    sensors = ['co2', 'temp', 'humidity', 'weight']
    for i, sensor in enumerate(sensors):
        row, col = i // 2, i % 2
        axes[row, col].hist(df[sensor].dropna(), bins=50, color='skyblue', edgecolor='black')
        axes[row, col].set_xlabel(sensor.upper())
        axes[row, col].set_ylabel('Frequency')
        axes[row, col].set_title(f'{sensor.upper()} Distribution')
        if sensor == 'temp':
            axes[row, col].axvspan(34, 36, alpha=0.3, color='green', label='Optimal Brood')
        elif sensor == 'humidity':
            axes[row, col].axvspan(50, 65, alpha=0.3, color='green', label='Optimal Brood')
        axes[row, col].legend()
    plt.suptitle('Sensor Distributions', fontsize=14)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'distributions_all_modules.png', dpi=150, bbox_inches='tight')
    plt.close()


# ──────────────────────────────────────────────
# 8. ANOMALY DETECTION
# ──────────────────────────────────────────────
def detect_anomalies(df):
    print("\n" + "=" * 70)
    print("6. ANOMALY DETECTION")
    print("=" * 70)
    temp_anomalies = pd.DataFrame()
    weight_drops = pd.DataFrame()
    co2_spikes = pd.DataFrame()

    if 'temp_deviation' in df.columns:
        temp_anomalies = df[df['temp_deviation'].abs() > 1.0]
    if 'weight_change' in df.columns:
        weight_drops = df[df['weight_change'] < -0.5]
    if 'co2_trend' in df.columns:
        co2_spikes = df[df['co2_trend'] > 1000]
    elif 'co2' in df.columns:
        co2_spikes = df[df['co2'] > 1800]

    print(f"  Temperature anomalies: {len(temp_anomalies)}")
    print(f"  Weight drops (<-0.5 kg): {len(weight_drops)}")
    print(f"  CO2 spikes: {len(co2_spikes)}")

    # Plot anomalies for first hive
    sample_hive = df['hive'].unique()[0]
    hive_sample = df[df['hive'] == sample_hive].sort_values('timestamp')
    fig, axes = plt.subplots(3, 1, figsize=(15, 10), sharex=True)

    axes[0].plot(hive_sample['timestamp'], hive_sample['co2'], color='green', alpha=0.5)
    if len(co2_spikes):
        h = co2_spikes[co2_spikes['hive'] == sample_hive]
        if len(h):
            axes[0].scatter(h['timestamp'], h['co2'], color='red', s=20, label='CO2 Spike')
    axes[0].set_ylabel('CO2 (ppm)')
    axes[0].legend()
    axes[0].set_title('CO2 Anomalies (Swarming Indicator)')

    axes[1].plot(hive_sample['timestamp'], hive_sample['weight'], color='brown', alpha=0.5)
    if len(weight_drops):
        h = weight_drops[weight_drops['hive'] == sample_hive]
        if len(h):
            axes[1].scatter(h['timestamp'], h['weight'], color='red', s=20, label='Weight Drop')
    axes[1].set_ylabel('Weight (kg)')
    axes[1].legend()
    axes[1].set_title('Weight Anomalies (Swarming/Absconding/Harvesting)')

    axes[2].plot(hive_sample['timestamp'], hive_sample['temp'], color='red', alpha=0.5)
    if len(temp_anomalies):
        h = temp_anomalies[temp_anomalies['hive'] == sample_hive]
        if len(h):
            axes[2].scatter(h['timestamp'], h['temp'], color='orange', s=20, label='Temp Anomaly')
    axes[2].axhline(y=35, color='blue', linestyle='--', label='Optimal')
    axes[2].set_ylabel('Temperature (°C)')
    axes[2].set_xlabel('Date')
    axes[2].legend()
    axes[2].set_title('Temperature Anomalies (Brood Health)')

    plt.suptitle('Anomaly Detection — Early Warning Signals', fontsize=14)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'anomalies_all_modules.png', dpi=150, bbox_inches='tight')
    plt.close()

    return {
        'temperature_anomalies': int(len(temp_anomalies)),
        'weight_drops': int(len(weight_drops)),
        'co2_spikes': int(len(co2_spikes)),
    }


# ──────────────────────────────────────────────
# 9. MODULE-SPECIFIC INSIGHTS
# ──────────────────────────────────────────────
def module_insights(df):
    print("\n" + "=" * 70)
    print("7. MODULE-SPECIFIC INSIGHTS")
    print("=" * 70)
    insights = {}

    # Brood Health
    optimal_temp_pct = ((df['temp'] >= 34) & (df['temp'] <= 36)).mean() * 100
    optimal_hum_pct = ((df['humidity'] >= 50) & (df['humidity'] <= 65)).mean() * 100
    temp_hum_corr = round(float(df['temp'].corr(df['humidity'])), 2)
    insights['brood_health'] = (
        f"Temp in optimal range (34–36°C): {optimal_temp_pct:.1f}% of readings. "
        f"Humidity in optimal range (50–65%): {optimal_hum_pct:.1f}% of readings. "
        f"Temp–Humidity correlation: {temp_hum_corr}."
    )
    print(f"\nBrood Health: {insights['brood_health']}")

    # Swarming
    weight_drop_count = int((df['weight_change'] < -0.5).sum()) if 'weight_change' in df.columns else 0
    co2_spike_count = int((df['co2'] > 1800).sum())
    insights['swarming'] = (
        f"Detected {weight_drop_count} weight drops (<-0.5 kg) and {co2_spike_count} CO2 spikes (>1800 ppm). "
        "Concurrent events may indicate swarm preparation."
    )
    print(f"Swarming: {insights['swarming']}")

    # Absconding
    if 'weight_change' in df.columns:
        sustained_decline = df.groupby('hive')['weight_change'].apply(
            lambda x: (x < -0.1).sum()
        ).to_dict()
        high_risk = [h for h, v in sustained_decline.items() if v > 50]
    else:
        high_risk = []
    insights['absconding'] = (
        f"Long-term weight decline detected. {len(high_risk)} hive(s) show sustained negative weight trend "
        f"(>50 consecutive drops). High-risk: {high_risk if high_risk else 'None detected'}."
    )
    print(f"Absconding: {insights['absconding']}")

    # Harvesting
    peak_weights = df.groupby('hive')['weight'].max()
    current_weights = df.groupby('hive')['weight'].last()
    ready_hives = peak_weights[peak_weights > 40].index.tolist()
    insights['harvesting'] = (
        f"Weight range: {df['weight'].min():.1f}–{df['weight'].max():.1f} kg. "
        f"Peak weight hives (>40 kg): {ready_hives}. "
        f"Harvest when weight plateaus after peak accumulation."
    )
    print(f"Harvesting: {insights['harvesting']}")

    # Per-hive brood health table
    brood_per_hive = []
    for hive in df['hive'].unique():
        sub = df[df['hive'] == hive]
        n = len(sub)
        opt_temp = int(((sub['temp'] >= 34) & (sub['temp'] <= 36)).sum())
        opt_hum = int(((sub['humidity'] >= 50) & (sub['humidity'] <= 65)).sum())
        opt_both = int(((sub['temp'] >= 34) & (sub['temp'] <= 36) &
                        (sub['humidity'] >= 50) & (sub['humidity'] <= 65)).sum())
        brood_per_hive.append({
            'hive': hive,
            'optimal_temp_pct': round(opt_temp / n * 100, 1) if n > 0 else 0,
            'optimal_humidity_pct': round(opt_hum / n * 100, 1) if n > 0 else 0,
            'optimal_both_pct': round(opt_both / n * 100, 1) if n > 0 else 0,
            'avg_temp': round(float(sub['temp'].mean()), 2),
            'avg_humidity': round(float(sub['humidity'].mean()), 2),
            'status': (
                'Excellent' if (opt_both / n * 100) > 80
                else 'Good' if (opt_both / n * 100) > 50
                else 'Needs Attention'
            ) if n > 0 else 'N/A'
        })

    # Per-hive harvesting table
    harvest_per_hive = []
    for hive in df['hive'].unique():
        sub = df[df['hive'] == hive].sort_values('timestamp')
        weights = sub['weight'].dropna().values
        if len(weights) < 5:
            continue
        current_wt = round(float(weights[-1]), 2)
        max_wt = round(float(weights.max()), 2)

        # Detect harvest events: single step drop > 8 kg
        harvest_count = 0
        for i in range(1, len(weights)):
            if (weights[i] - weights[i - 1]) < -8.0:
                # Confirm it stays low for the next 3 readings
                if i + 3 < len(weights) and weights[i + 3] < weights[i - 1] - 5.0:
                    harvest_count += 1

        # Plateau check: weight range in last 5% of records < 0.5 kg
        last_n = max(10, len(weights) // 20)
        last_weights = weights[-last_n:]
        is_plateau = (last_weights.max() - last_weights.min()) < 0.5 and current_wt > 25
        readiness = 'Optimal Harvest Window' if is_plateau else ('Nearing Capacity' if current_wt > 35 else 'Accumulating')

        harvest_per_hive.append({
            'hive': hive,
            'current_weight': current_wt,
            'max_weight': max_wt,
            'harvest_count': harvest_count,
            'status': readiness,
        })

    return insights, brood_per_hive, harvest_per_hive


# ──────────────────────────────────────────────
# 10. DASHBOARD JSON
# ──────────────────────────────────────────────
def generate_dashboard_json(df, stats, outlier_results, anomaly_counts,
                             insights, hive_stats, hourly_patterns,
                             brood_per_hive, harvest_per_hive):
    print("\n" + "=" * 70)
    print("8. GENERATING dashboard.json")
    print("=" * 70)

    dashboard = {
        "summary": {
            "total_hives": int(df['hive'].nunique()),
            "total_records": int(len(df)),
            "analysis_start": str(df['timestamp'].min()),
            "analysis_end": str(df['timestamp'].max()),
        },
        "sensor_statistics": {
            "temperature": {
                "mean": stats['temp']['mean'],
                "min": stats['temp']['min'],
                "max": stats['temp']['max'],
                "median": stats['temp']['median'],
                "std": stats['temp']['std'],
                "q1": stats['temp']['q1'],
                "q3": stats['temp']['q3'],
            },
            "humidity": {
                "mean": stats['humidity']['mean'],
                "min": stats['humidity']['min'],
                "max": stats['humidity']['max'],
                "median": stats['humidity']['median'],
                "std": stats['humidity']['std'],
                "q1": stats['humidity']['q1'],
                "q3": stats['humidity']['q3'],
            },
            "weight": {
                "mean": stats['weight']['mean'],
                "min": stats['weight']['min'],
                "max": stats['weight']['max'],
                "median": stats['weight']['median'],
                "std": stats['weight']['std'],
                "q1": stats['weight']['q1'],
                "q3": stats['weight']['q3'],
            },
            "co2": {
                "mean": stats['co2']['mean'],
                "min": stats['co2']['min'],
                "max": stats['co2']['max'],
                "median": stats['co2']['median'],
                "std": stats['co2']['std'],
                "q1": stats['co2']['q1'],
                "q3": stats['co2']['q3'],
            },
        },
        "outlier_analysis": {
            "temperature_percentage": outlier_results['temp']['outlier_percent'],
            "humidity_percentage": outlier_results['humidity']['outlier_percent'],
            "weight_percentage": outlier_results['weight']['outlier_percent'],
            "co2_percentage": outlier_results['co2']['outlier_percent'],
            "details": {
                s: {
                    "Q1": outlier_results[s]['Q1'],
                    "Q3": outlier_results[s]['Q3'],
                    "IQR": outlier_results[s]['IQR'],
                    "lower_bound": outlier_results[s]['lower_bound'],
                    "upper_bound": outlier_results[s]['upper_bound'],
                    "outlier_count": outlier_results[s]['outlier_count'],
                    "outlier_percent": outlier_results[s]['outlier_percent'],
                }
                for s in ['co2', 'temp', 'humidity', 'weight']
            }
        },
        "anomalies": anomaly_counts,
        "module_insights": {
            "brood_health": insights['brood_health'],
            "swarming": insights['swarming'],
            "absconding": insights['absconding'],
            "harvesting": insights['harvesting'],
        },
        "hive_stats": hive_stats,
        "hourly_patterns": hourly_patterns,
        "brood_health_per_hive": brood_per_hive,
        "harvesting_per_hive": harvest_per_hive,
    }

    json_path = OUTPUT_DIR / 'dashboard.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(dashboard, f, indent=2, default=str)

    print(f"✅ dashboard.json written → {json_path}")
    return dashboard


# ──────────────────────────────────────────────
# 11. FULL EDA TEXT REPORT
# ──────────────────────────────────────────────
def generate_report(df, stats, outlier_results):
    lines = [
        "=" * 70,
        "COMPLETE EDA REPORT",
        "For: Brood Health | Swarming | Absconding | Harvesting",
        "=" * 70,
        f"Period: {df['timestamp'].min()} → {df['timestamp'].max()}",
        f"Hives: {df['hive'].nunique()} | Records: {len(df):,}",
        "",
        "-" * 50, "SENSOR STATISTICS", "-" * 50,
    ]
    for s in ['co2', 'temp', 'humidity', 'weight']:
        lines += [
            f"\n{s.upper()}:",
            f"  Mean: {stats[s]['mean']}  |  Std: {stats[s]['std']}",
            f"  Min:  {stats[s]['min']}  |  Max: {stats[s]['max']}",
        ]
    lines += [
        "", "-" * 50, "OUTLIER SUMMARY", "-" * 50,
    ]
    for s in ['co2', 'temp', 'humidity', 'weight']:
        pct = outlier_results[s]['outlier_percent']
        rating = "EXCELLENT" if pct < 1 else "GOOD" if pct < 5 else "HIGH"
        lines.append(f"  {s.upper()}: {pct:.2f}% outliers — {rating}")

    report_path = OUTPUT_DIR / 'complete_eda_report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"✅ Report saved → {report_path}")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def run_full_eda():
    print("\n" + "=" * 30)
    print("HIVE EDA PIPELINE — STARTING")
    print("=" * 30 + "\n")

    df = load_data()

    outlier_results = outlier_analysis_all_sensors(df)
    stats = overall_statistics(df)
    correlation_analysis(df)
    hive_stats = multi_hive_comparison(df)
    hourly_patterns = temporal_patterns(df)
    distribution_analysis(df)
    anomaly_counts = detect_anomalies(df)
    insights, brood_per_hive, harvest_per_hive = module_insights(df)

    generate_dashboard_json(
        df, stats, outlier_results, anomaly_counts,
        insights, hive_stats, hourly_patterns,
        brood_per_hive, harvest_per_hive
    )
    generate_report(df, stats, outlier_results)

    print("\n" + "=" * 70)
    print("✅ EDA COMPLETE — all outputs in:", OUTPUT_DIR)
    print("=" * 70)


if __name__ == "__main__":
    run_full_eda()