import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = BASE_DIR / "data" / "initial_dataset.csv"
OUTPUT_FILE = BASE_DIR / "data" / "harvest_dataset.csv"


def create_weight_features():
    data = pd.read_csv(INPUT_FILE)

    # Clean column names
    data.columns = data.columns.str.strip().str.lower().str.replace(" ", "_")

    # Rename your dataset columns to standard names
    data = data.rename(columns={
        "hive": "hive_id",
        "weight": "hive_weight_kg",
        "temp": "internal_temperature_c",
        "humidity": "internal_humidity_pct",
        "co2": "co2_ppm"
    })

    print("Available columns after renaming:")
    print(data.columns.tolist())

    required_columns = ["timestamp", "hive_id", "hive_weight_kg"]

    for col in required_columns:
        if col not in data.columns:
            raise ValueError(f"Missing required column: {col}")

    data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce")
    data["hive_weight_kg"] = pd.to_numeric(data["hive_weight_kg"], errors="coerce")

    data = data.dropna(subset=["timestamp", "hive_id", "hive_weight_kg"])
    data = data.sort_values(["hive_id", "timestamp"])

    # Detect data interval automatically
    time_diffs = (
        data.groupby("hive_id")["timestamp"]
        .diff()
        .dropna()
        .dt.total_seconds()
    )

    median_interval_seconds = time_diffs.median()

    records_24h = round((24 * 60 * 60) / median_interval_seconds)
    records_72h = records_24h * 3
    records_7d = records_24h * 7

    print(f"\nDetected median interval: {median_interval_seconds / 60:.2f} minutes")
    print(f"Records for 24h: {records_24h}")
    print(f"Records for 72h: {records_72h}")
    print(f"Records for 7d: {records_7d}")

    # Weight change features
    data["weight_change_1_record"] = data.groupby("hive_id")["hive_weight_kg"].diff()
    data["weight_change_24h"] = data.groupby("hive_id")["hive_weight_kg"].diff(records_24h)
    data["weight_change_72h"] = data.groupby("hive_id")["hive_weight_kg"].diff(records_72h)

    # Weight stability features
    data["weight_std_24h"] = (
        data.groupby("hive_id")["hive_weight_kg"]
        .rolling(window=records_24h, min_periods=max(3, records_24h // 4))
        .std()
        .reset_index(level=0, drop=True)
    )

    data["weight_std_72h"] = (
        data.groupby("hive_id")["hive_weight_kg"]
        .rolling(window=records_72h, min_periods=max(6, records_72h // 4))
        .std()
        .reset_index(level=0, drop=True)
    )

    # Rolling max weight in last 7 days
    data["rolling_max_7d"] = (
        data.groupby("hive_id")["hive_weight_kg"]
        .rolling(window=records_7d, min_periods=max(12, records_24h))
        .max()
        .reset_index(level=0, drop=True)
    )

    # Current weight compared to recent max
    data["near_recent_max"] = data["hive_weight_kg"] / data["rolling_max_7d"]
    data["near_recent_max"] = data["near_recent_max"].clip(0, 1)

    # Possible harvest/drop event
    data["harvest_drop_detected"] = (
        data["weight_change_1_record"] <= -10
    ).astype(int)

    # Plateau detection
    data["plateau_detected"] = (
        (data["near_recent_max"] >= 0.95)
        & (data["weight_std_72h"] <= 0.75)
        & (data["weight_change_72h"] >= 0)
    ).astype(int)

    data.to_csv(OUTPUT_FILE, index=False)

    print("\nFeature engineering completed.")
    print(f"Saved file: {OUTPUT_FILE}")

    print("\nPreview:")
    print(data[[
        "hive_id",
        "timestamp",
        "hive_weight_kg",
        "weight_change_1_record",
        "weight_change_24h",
        "weight_change_72h",
        "weight_std_24h",
        "weight_std_72h",
        "rolling_max_7d",
        "near_recent_max",
        "harvest_drop_detected",
        "plateau_detected"
    ]].head(20))


if __name__ == "__main__":
    create_weight_features()