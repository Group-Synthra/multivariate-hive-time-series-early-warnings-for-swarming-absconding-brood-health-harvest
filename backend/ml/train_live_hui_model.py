"""Train a live-compatible HUI regression model from the historical dataset.

Run from the project root:
    python backend/ml/train_live_hui_model.py

Fast test:
    python backend/ml/train_live_hui_model.py --sample 50000

Input:
    backend/outputs/harvest/hui_dataset.csv

Outputs:
    backend/models/best_live_hui_model.joblib
    backend/models/live_hui_feature_columns.joblib
    backend/models/live_hui_model_metadata.json
    backend/outputs/harvest/live_model_comparison.csv
    backend/outputs/harvest/live_model_comparison.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.harvest.live_feature_engineering import (  # noqa: E402
    FeatureEngineeringConfig,
    LIVE_MODEL_FEATURES,
    add_live_features,
    canonicalize_historical_data,
    resample_hourly,
)

load_dotenv(PROJECT_ROOT / ".env")

DATA_PATH = PROJECT_ROOT / "backend" / "outputs" / "harvest" / "hui_dataset.csv"
MODEL_DIR = PROJECT_ROOT / "backend" / "models"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "outputs" / "harvest"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET = "harvest_urgency_index_0_100"
MODEL_FILE = MODEL_DIR / "best_live_hui_model.joblib"
FEATURE_FILE = MODEL_DIR / "live_hui_feature_columns.joblib"
METADATA_FILE = MODEL_DIR / "live_hui_model_metadata.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Optional chronological coverage sample for a faster test run.",
    )
    parser.add_argument(
        "--no-resample",
        action="store_true",
        help="Skip hourly resampling only when the historical file is already regular hourly data.",
    )
    return parser.parse_args()


def sample_chronological_coverage(data: pd.DataFrame, sample_size: int | None) -> pd.DataFrame:
    """Keep one contiguous recent block so lag and rolling features remain valid."""
    if not sample_size or sample_size >= len(data):
        return data

    return data.tail(sample_size).reset_index(drop=True)


def feature_ranges(frame: pd.DataFrame) -> dict[str, dict[str, float | None]]:
    ranges: dict[str, dict[str, float | None]] = {}
    for column in LIVE_MODEL_FEATURES:
        numeric = pd.to_numeric(frame[column], errors="coerce").dropna()
        if numeric.empty:
            ranges[column] = {"p01": None, "p99": None, "min": None, "max": None}
            continue

        ranges[column] = {
            "p01": round(float(numeric.quantile(0.01)), 6),
            "p99": round(float(numeric.quantile(0.99)), 6),
            "min": round(float(numeric.min()), 6),
            "max": round(float(numeric.max()), 6),
        }
    return ranges


def main() -> None:
    args = parse_args()

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Historical HUI dataset not found: {DATA_PATH}. "
            "Run backend/eda/eda_analysis_harvest.py first."
        )

    print(f"Loading historical dataset: {DATA_PATH}")
    raw = pd.read_csv(DATA_PATH)

    required = {"timestamp", "hive_id", TARGET}
    missing = sorted(required - set(raw.columns))
    if missing:
        raise ValueError(f"Historical dataset is missing columns: {missing}")

    timestamps_are_utc = os.getenv("HISTORICAL_TIMESTAMPS_ARE_UTC", "false").lower() == "true"
    timezone = os.getenv("IOT_FEATURE_TIMEZONE", "Asia/Colombo")

    config = FeatureEngineeringConfig(
        feature_timezone=timezone,
        timestamps_are_utc=timestamps_are_utc,
        interpolation_limit_hours=int(os.getenv("IOT_INTERPOLATION_LIMIT_HOURS", "3")),
    )

    data = canonicalize_historical_data(raw, config=config)
    data = data.dropna(subset=["timestamp", "hive_id", TARGET])
    data = data.sort_values(["timestamp", "hive_id"]).reset_index(drop=True)
    data = sample_chronological_coverage(data, args.sample)

    if not args.no_resample:
        data = resample_hourly(data, config=config, preserve_columns=[TARGET])

    # The target may already exist after resampling because it is numeric.
    if TARGET not in data.columns:
        raise ValueError(f"Target column was lost during preprocessing: {TARGET}")

    feature_data = add_live_features(data, config=config)
    usable = feature_data.dropna(subset=[TARGET]).copy()

    missing_features = [column for column in LIVE_MODEL_FEATURES if column not in usable.columns]
    if missing_features:
        raise ValueError(f"Missing engineered features: {missing_features}")

    usable = usable.sort_values("timestamp").reset_index(drop=True)
    if len(usable) < 500:
        raise ValueError(f"Only {len(usable)} usable rows remain; at least 500 are recommended.")

    split_index = int(len(usable) * 0.80)
    if split_index <= 0 or split_index >= len(usable):
        raise ValueError("Unable to create chronological 80/20 split.")

    X = usable[LIVE_MODEL_FEATURES].copy()
    y = pd.to_numeric(usable[TARGET], errors="coerce")

    X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]

    estimators = {
        "Random Forest": RandomForestRegressor(
            n_estimators=220,
            max_depth=18,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        ),
        "XGBoost": XGBRegressor(
            n_estimators=450,
            learning_rate=0.04,
            max_depth=7,
            subsample=0.85,
            colsample_bytree=0.85,
            objective="reg:squarederror",
            random_state=42,
            n_jobs=-1,
        ),
        "LightGBM": LGBMRegressor(
            n_estimators=450,
            learning_rate=0.04,
            num_leaves=48,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=42,
            n_jobs=-1,
            verbosity=-1,
        ),
    }

    trained: dict[str, Pipeline] = {}
    results: list[dict[str, float | str]] = []

    for name, estimator in estimators.items():
        print(f"Training {name}...")
        pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("model", estimator),
            ]
        )
        pipeline.fit(X_train, y_train)
        prediction = np.clip(pipeline.predict(X_test), 0, 100)

        result = {
            "model": name,
            "mae": round(float(mean_absolute_error(y_test, prediction)), 4),
            "rmse": round(float(np.sqrt(mean_squared_error(y_test, prediction))), 4),
            "r2": round(float(r2_score(y_test, prediction)), 4),
        }
        print(result)
        trained[name] = pipeline
        results.append(result)

    results.sort(key=lambda row: (row["rmse"], row["mae"], -row["r2"]))
    best_name = str(results[0]["model"])
    best_model = trained[best_name]

    joblib.dump(best_model, MODEL_FILE)
    joblib.dump(LIVE_MODEL_FEATURES, FEATURE_FILE)

    metadata = {
        "model_version": "live_hui_v1",
        "best_model": best_name,
        "selection_rule": "Lowest RMSE, then lowest MAE, then highest R2",
        "target": TARGET,
        "target_type": "expert_rule_proxy",
        "training_source": "historical_hui_dataset",
        "deployment_source": "Sri Lankan IoT PostgreSQL",
        "split": "chronological_80_20",
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "minimum_history_hours": 72,
        "recommended_history_hours": 168,
        "feature_timezone": timezone,
        "features": LIVE_MODEL_FEATURES,
        "training_feature_ranges": feature_ranges(X_train),
        "results": results,
        "warning": (
            "The target is a proxy HUI generated from expert rules, not observed "
            "beekeeper-confirmed harvest ground truth."
        ),
    }

    with METADATA_FILE.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    with (OUTPUT_DIR / "live_model_comparison.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    pd.DataFrame(results).to_csv(OUTPUT_DIR / "live_model_comparison.csv", index=False)

    print(f"Best live-compatible model: {best_name}")
    print(f"Saved model: {MODEL_FILE}")
    print(f"Saved features: {FEATURE_FILE}")
    print(f"Saved metadata: {METADATA_FILE}")


if __name__ == "__main__":
    main()
