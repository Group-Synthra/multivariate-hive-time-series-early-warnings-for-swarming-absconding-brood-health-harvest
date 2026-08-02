import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = BASE_DIR / "data" / "harvest_dataset.csv"
OUTPUT_FILE = BASE_DIR / "data" / "harvest_dataset_labeled.csv"


def create_harvest_labels():
    data = pd.read_csv(INPUT_FILE)

    # Fill missing derived values safely
    data["near_recent_max"] = data["near_recent_max"].fillna(0)
    data["weight_change_72h"] = data["weight_change_72h"].fillna(0)
    data["weight_std_72h"] = data["weight_std_72h"].fillna(999)
    data["plateau_detected"] = data["plateau_detected"].fillna(0)

    # Default label: 0 = Not Ready
    data["harvest_readiness_label"] = 0

    # 1 = Approaching
    approaching_condition = (
        (data["near_recent_max"] >= 0.80) &
        (data["weight_change_72h"] > 0)
    )

    data.loc[approaching_condition, "harvest_readiness_label"] = 1

    # 2 = Ready
    ready_condition = (
        (data["near_recent_max"] >= 0.95) &
        (data["weight_std_72h"] <= 0.75) &
        (data["weight_change_72h"] >= 0) &
        (data["plateau_detected"] == 1)
    )

    data.loc[ready_condition, "harvest_readiness_label"] = 2

    data["harvest_readiness_status"] = data["harvest_readiness_label"].map({
        0: "Not Ready",
        1: "Approaching",
        2: "Ready"
    })

    data.to_csv(OUTPUT_FILE, index=False)

    print("Harvest labels created successfully.")
    print(f"Saved file: {OUTPUT_FILE}")
    print("\nLabel distribution:")
    print(data["harvest_readiness_status"].value_counts())


if __name__ == "__main__":
    create_harvest_labels()