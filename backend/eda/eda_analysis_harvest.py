"""Harvest-module EDA and proxy HUI generation.

Run from the project root:
    python backend/eda/eda_analysis_harvest.py

Input:
    backend/data/hive_data_with_features.csv

Outputs:
    backend/outputs/harvest/harvest_eda_summary.json
    backend/outputs/harvest/hui_dataset.csv
    backend/outputs/harvest/*.png

Important: HUI is an expert-rule proxy target, not observed beekeeper ground truth.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "backend" / "data" / "hive_data_with_features.csv"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "outputs" / "harvest"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_COLUMNS = {
    "timestamp",
    "hive_id",
    "internal_temperature_c",
    "internal_humidity_pct",
    "co2_ppm",
    "hive_weight_kg",
    "external_temperature_c",
    "external_humidity_pct",
    "rainfall_mm_hour",
    "wind_speed_mps",
    "nectar_flow_season_proxy",
    "dearth_season_proxy",
    "monsoon_rain_period_proxy",
    "brood_health_score_0_100",
}

def create_hive_harvest_analysis(df, output_dir):
    """
    Generate per-hive harvesting EDA information for the React dashboard.

    Expected columns:
    - hive
    - timestamp
    - hive_weight_kg
    - internal_humidity_pct
    - rainfall_mm_hour
    - harvest_urgency_index_0_100
    """

    data = df.copy()

    # Support either "hive" or "hive_id"
    if "hive" in data.columns:
        hive_column = "hive"
    elif "hive_id" in data.columns:
        hive_column = "hive_id"
    else:
        raise ValueError("Dataset must contain 'hive' or 'hive_id'.")

    weight_column = "hive_weight_kg"

    if weight_column not in data.columns:
        raise ValueError(
            f"Required column not found: {weight_column}"
        )

    data["timestamp"] = pd.to_datetime(
        data["timestamp"],
        errors="coerce"
    )

    data = data.dropna(
        subset=["timestamp", hive_column, weight_column]
    )

    data = data.sort_values(
        [hive_column, "timestamp"]
    )

    # Weight differences
    data["weight_change_1h"] = (
        data.groupby(hive_column)[weight_column]
        .diff()
    )

    data["weight_change_24h"] = (
        data.groupby(hive_column)[weight_column]
        .diff(24)
    )

    # Rolling variability: lower value means more stable weight
    data["weight_std_24h"] = (
        data.groupby(hive_column)[weight_column]
        .transform(
            lambda series: series.rolling(
                24,
                min_periods=6
            ).std()
        )
    )

    # Plateau rule:
    # - Hive is close to its recent maximum weight
    # - Weight variability is small
    # - Weight change is not strongly increasing/decreasing
    rolling_max = (
        data.groupby(hive_column)[weight_column]
        .transform(
            lambda series: series.rolling(
                168,
                min_periods=24
            ).max()
        )
    )

    data["near_recent_max"] = (
        data[weight_column] >= rolling_max * 0.95
    )

    data["stable_weight"] = (
        data["weight_std_24h"] <= 0.75
    )

    data["small_weight_change"] = (
        data["weight_change_24h"].abs() <= 1.5
    )

    data["plateau_detected"] = (
        data["near_recent_max"]
        & data["stable_weight"]
        & data["small_weight_change"]
    )

    # Possible harvest/extraction event:
    # large sudden weight reduction
    data["harvest_drop_detected"] = (
        data["weight_change_1h"] <= -10
    )

    hive_analysis = []

    for hive_id, hive_df in data.groupby(hive_column):
        hive_df = hive_df.sort_values("timestamp")

        latest = hive_df.iloc[-1]

        current_weight = float(latest[weight_column])
        maximum_weight = float(hive_df[weight_column].max())
        minimum_weight = float(hive_df[weight_column].min())

        recent_24h_change = latest.get(
            "weight_change_24h",
            np.nan
        )

        if pd.isna(recent_24h_change):
            recent_24h_change = 0.0

        plateau_rows = hive_df[
            hive_df["plateau_detected"]
        ]

        plateau_detected = not plateau_rows.empty

        plateau_start = None
        plateau_end = None

        if plateau_detected:
            latest_plateau_group = plateau_rows.tail(48)

            plateau_start = (
                latest_plateau_group["timestamp"]
                .min()
                .isoformat()
            )

            plateau_end = (
                latest_plateau_group["timestamp"]
                .max()
                .isoformat()
            )

        harvest_count = int(
            hive_df["harvest_drop_detected"].sum()
        )

        current_hui = None

        if "harvest_urgency_index_0_100" in hive_df.columns:
            current_hui = float(
                latest["harvest_urgency_index_0_100"]
            )

        status = hui_to_status(current_hui)

        # Reduce number of chart points to keep React responsive.
        chart_df = hive_df.tail(1000).copy()

        chart_data = []

        for _, row in chart_df.iterrows():
            chart_data.append({
                "timestamp": row["timestamp"].isoformat(),
                "weight": round(
                    float(row[weight_column]),
                    3
                ),
                "weight_change_24h": (
                    None
                    if pd.isna(row["weight_change_24h"])
                    else round(
                        float(row["weight_change_24h"]),
                        3
                    )
                ),
                "plateau_detected": bool(
                    row["plateau_detected"]
                ),
                "harvest_drop_detected": bool(
                    row["harvest_drop_detected"]
                )
            })

        hive_analysis.append({
            "hive": str(hive_id),
            "current_weight": round(current_weight, 2),
            "maximum_weight": round(maximum_weight, 2),
            "minimum_weight": round(minimum_weight, 2),
            "weight_change_24h": round(
                float(recent_24h_change),
                2
            ),
            "current_hui": (
                None
                if current_hui is None
                else round(current_hui, 2)
            ),
            "status": status,
            "plateau_detected": plateau_detected,
            "plateau_start": plateau_start,
            "plateau_end": plateau_end,
            "historical_harvest_count": harvest_count,
            "latest_timestamp": (
                latest["timestamp"].isoformat()
            ),
            "chart_data": chart_data
        })

    # Sort high-HUI hives first
    hive_analysis.sort(
        key=lambda item: (
            item["current_hui"]
            if item["current_hui"] is not None
            else -1
        ),
        reverse=True
    )

    output = {
        "total_hives": len(hive_analysis),
        "plateau_hives": sum(
            item["plateau_detected"]
            for item in hive_analysis
        ),
        "ready_hives": sum(
            item["status"] in {
                "Ready",
                "Optimal/Emergency"
            }
            for item in hive_analysis
        ),
        "hives": hive_analysis
    }

    output_path = (
        Path(output_dir)
        / "harvest_hive_analysis.json"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            output,
            file,
            indent=2
        )

    print(
        f"Saved hive harvesting analysis: {output_path}"
    )

    return output


def hui_to_status(hui):
    if hui is None:
        return "Unknown"

    if hui <= 30:
        return "Not Ready"

    if hui <= 60:
        return "Approaching"

    if hui <= 80:
        return "Ready"

    return "Optimal/Emergency"

def robust_minmax(series: pd.Series, lower_q: float = 0.01, upper_q: float = 0.99) -> pd.Series:
    """Scale to 0..1 after clipping extreme values to robust quantiles."""
    numeric = pd.to_numeric(series, errors="coerce")
    low = numeric.quantile(lower_q)
    high = numeric.quantile(upper_q)
    if pd.isna(low) or pd.isna(high) or np.isclose(low, high):
        return pd.Series(np.zeros(len(series)), index=series.index, dtype=float)
    return ((numeric.clip(low, high) - low) / (high - low)).clip(0, 1)


def triangular_suitability(series: pd.Series, ideal: float, tolerance: float) -> pd.Series:
    """Return 1 at the ideal and linearly reduce to 0 at ideal +/- tolerance."""
    numeric = pd.to_numeric(series, errors="coerce")
    return (1 - (numeric - ideal).abs() / tolerance).clip(0, 1)


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create hive-level weight trend and stability features without future data."""
    data = df.sort_values(["hive_id", "timestamp"]).copy()
    group = data.groupby("hive_id", group_keys=False)

    # Hourly data: 24 rows ~= 24h and 72 rows ~= 72h.
    data["weight_change_24h_kg"] = group["hive_weight_kg"].diff(24)
    data["weight_change_72h_kg"] = group["hive_weight_kg"].diff(72)
    data["weight_std_24h_kg"] = (
        group["hive_weight_kg"]
        .rolling(window=24, min_periods=6)
        .std()
        .reset_index(level=0, drop=True)
    )

    for column in ["weight_change_24h_kg", "weight_change_72h_kg", "weight_std_24h_kg"]:
        data[column] = data[column].fillna(0.0)

    return data


def generate_hui(df: pd.DataFrame) -> pd.DataFrame:
    """Generate an explainable 0..100 Harvest Urgency Index proxy.

    Positive components (sum to 0.80):
      - Current hive weight: 0.25
      - 72-hour weight gain: 0.15
      - Weight stability/plateau: 0.10
      - Nectar flow: 0.10
      - Brood health: 0.10
      - Internal temperature suitability: 0.05
      - Internal humidity suitability: 0.05

    Penalties (maximum total 0.20):
      - Rain: 0.05
      - Wind: 0.03
      - CO2: 0.04
      - Dearth season: 0.04
      - Monsoon period: 0.04

    The raw score is multiplied by 100 and clipped to 0..100.
    """
    data = add_temporal_features(df)

    weight_score = robust_minmax(data["hive_weight_kg"])
    weight_gain_score = robust_minmax(data["weight_change_72h_kg"])
    # Stable weight after accumulation can indicate capped stores; lower variability is better.
    weight_stability_score = 1 - robust_minmax(data["weight_std_24h_kg"])
    brood_score = pd.to_numeric(data["brood_health_score_0_100"], errors="coerce").fillna(0).clip(0, 100) / 100
    nectar_score = pd.to_numeric(data["nectar_flow_season_proxy"], errors="coerce").fillna(0).clip(0, 1)

    temp_score = triangular_suitability(data["internal_temperature_c"], ideal=35.0, tolerance=5.0)
    humidity_score = triangular_suitability(data["internal_humidity_pct"], ideal=60.0, tolerance=25.0)

    rain_penalty = robust_minmax(data["rainfall_mm_hour"])
    wind_penalty = robust_minmax(data["wind_speed_mps"])
    co2_penalty = robust_minmax(data["co2_ppm"])
    dearth_penalty = pd.to_numeric(data["dearth_season_proxy"], errors="coerce").fillna(0).clip(0, 1)
    monsoon_penalty = pd.to_numeric(data["monsoon_rain_period_proxy"], errors="coerce").fillna(0).clip(0, 1)

    positive = (
        0.25 * weight_score
        + 0.15 * weight_gain_score
        + 0.10 * weight_stability_score
        + 0.10 * nectar_score
        + 0.10 * brood_score
        + 0.05 * temp_score
        + 0.05 * humidity_score
    )
    penalties = (
        0.05 * rain_penalty
        + 0.03 * wind_penalty
        + 0.04 * co2_penalty
        + 0.04 * dearth_penalty
        + 0.04 * monsoon_penalty
    )

    data["harvest_urgency_index_0_100"] = (100 * (positive - penalties)).clip(0, 100).round(3)
    data["hui_status"] = pd.cut(
        data["harvest_urgency_index_0_100"],
        bins=[-np.inf, 30, 60, 80, np.inf],
        labels=["Not Ready", "Approaching", "Ready", "Optimal/Emergency"],
    ).astype(str)
    data["hui_generation_method"] = "expert_rule_proxy_v2_temporal"
    return data


def save_plots(data: pd.DataFrame) -> None:
    plt.figure(figsize=(9, 5))
    data["harvest_urgency_index_0_100"].hist(bins=40)
    plt.title("Generated Harvest Urgency Index Distribution")
    plt.xlabel("HUI (0-100)")
    plt.ylabel("Rows")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "hui_distribution.png", dpi=160)
    plt.close()

    status_counts = data["hui_status"].value_counts().reindex(
        ["Not Ready", "Approaching", "Ready", "Optimal/Emergency"], fill_value=0
    )
    plt.figure(figsize=(9, 5))
    status_counts.plot(kind="bar")
    plt.title("HUI Status Distribution")
    plt.xlabel("Status")
    plt.ylabel("Rows")
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "hui_status_distribution.png", dpi=160)
    plt.close()


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}\n"
            "Copy da.csv to backend/data/hive_data_with_features.csv first."
        )

    print(f"Loading: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    if df["timestamp"].isna().any():
        raise ValueError("Some timestamp values could not be parsed.")

    data = generate_hui(df)
    create_hive_harvest_analysis(
        df=data,
        output_dir=OUTPUT_DIR
    )
    output_csv = OUTPUT_DIR / "hui_dataset.csv"
    data.to_csv(output_csv, index=False)
    save_plots(data)

    summary = {
        "rows": int(len(data)),
        "columns": int(len(data.columns)),
        "hives": int(data["hive_id"].nunique()),
        "start_time": data["timestamp"].min().isoformat(),
        "end_time": data["timestamp"].max().isoformat(),
        "hui": {
            "mean": round(float(data["harvest_urgency_index_0_100"].mean()), 3),
            "std": round(float(data["harvest_urgency_index_0_100"].std()), 3),
            "min": round(float(data["harvest_urgency_index_0_100"].min()), 3),
            "max": round(float(data["harvest_urgency_index_0_100"].max()), 3),
        },
        "status_counts": {k: int(v) for k, v in data["hui_status"].value_counts().items()},
        "method": "expert_rule_proxy_v2_temporal",
        "warning": "Proxy HUI; not beekeeper-confirmed ground truth.",
    }
    with (OUTPUT_DIR / "harvest_eda_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    print(f"Saved HUI dataset: {output_csv}")
    print(f"Saved outputs in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
