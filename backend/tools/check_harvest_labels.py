"""Inspect the existing harvest-related target columns.

This project dataset does not contain a column named `harvest`.
The default training target is the already prepared binary column:

    honey_harvest_label_next_7d

Run:
    python backend/tools/check_harvest_labels.py
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

DATA_PATH = Path(
    os.getenv(
        "HARVEST_HISTORICAL_DATA_PATH",
        PROJECT_ROOT
        / "backend"
        / "data"
        / "hive_data_with_features.csv",
    )
)

TARGET_COLUMN = os.getenv(
    "HARVEST_LABEL_COLUMN",
    "honey_harvest_label_next_7d",
)

RELATED_COLUMNS = [
    "honey_harvest_ready_label",
    "honey_harvest_label_next_7d",
    "honey_harvest_readiness_label",
]


def print_distribution(
    data: pd.DataFrame,
    column: str,
) -> None:
    if column not in data.columns:
        print(f"\n{column}: NOT FOUND")
        return

    values = pd.to_numeric(
        data[column],
        errors="coerce",
    )

    print(f"\n{column}:")
    print(values.value_counts(dropna=False).sort_index())

    unique_non_missing = sorted(
        values.dropna().unique().tolist()
    )

    print(
        "Unique non-missing values:",
        unique_non_missing[:30],
    )

    if len(unique_non_missing) > 30:
        print(
            f"... plus "
            f"{len(unique_non_missing) - 30} more"
        )


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Historical dataset not found: "
            f"{DATA_PATH}"
        )

    data = pd.read_csv(DATA_PATH)

    print(f"Dataset: {DATA_PATH}")
    print(f"Rows: {len(data):,}")
    print(f"Columns: {data.columns.tolist()}")

    required = {
        "timestamp",
        "hive_id",
        TARGET_COLUMN,
    }
    missing = sorted(
        required - set(data.columns)
    )

    if missing:
        raise ValueError(
            f"Required columns are missing: "
            f"{missing}"
        )

    for column in RELATED_COLUMNS:
        print_distribution(data, column)

    target = pd.to_numeric(
        data[TARGET_COLUMN],
        errors="coerce",
    )

    unique_target = set(
        target.dropna().unique().tolist()
    )

    if not unique_target.issubset({0, 1}):
        raise ValueError(
            f"{TARGET_COLUMN} is not binary. "
            f"Observed values: "
            f"{sorted(unique_target)}"
        )

    positive = data.loc[
        target.fillna(0).eq(1),
        [
            "timestamp",
            "hive_id",
            TARGET_COLUMN,
        ],
    ]

    print(
        f"\nSelected training target: "
        f"{TARGET_COLUMN}"
    )
    print(
        f"Positive rows: {len(positive):,}"
    )
    print(
        f"Negative rows: "
        f"{target.fillna(0).eq(0).sum():,}"
    )
    print(
        f"Positive rate: "
        f"{target.fillna(0).mean():.4%}"
    )
    print(
        "Hives containing positive rows:",
        positive["hive_id"].nunique(),
    )

    print("\nFirst 30 positive rows:")
    print(
        positive.head(30).to_string(
            index=False
        )
    )

    print(
        "\nInterpretation used by the new "
        "training pipeline:"
    )
    print(
        f"  {TARGET_COLUMN} = 1 means the "
        "dataset already marks a harvest "
        "within the next seven days."
    )
    print(
        "The classifier will learn this "
        "existing future label directly. "
        "It will NOT create another shifted "
        "future target from this column."
    )
    print(
        "\nImportant limitation:"
    )
    print(
        "A seven-day future label cannot be "
        "converted into an honest three-day "
        "probability. A three-day model needs "
        "an actual harvest-event timestamp or "
        "a separately generated next-72-hour "
        "label."
    )


if __name__ == "__main__":
    main()
