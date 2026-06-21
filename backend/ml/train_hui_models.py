"""Train and compare Random Forest, XGBoost, and LightGBM for HUI regression.

Run from project root after EDA:
    python backend/ml/train_hui_models.py

For a faster interim demo:
    python backend/ml/train_hui_models.py --sample 50000
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "backend" / "outputs" / "harvest" / "hui_dataset.csv"
MODEL_DIR = PROJECT_ROOT / "backend" / "models"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "outputs" / "harvest"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET = "harvest_urgency_index_0_100"

FEATURES = [
    "experiment_year",
    "experiment",
    "apiary_site",
    "apiary_context",
    "hive_id",
    "bee_stock",
    "internal_temperature_c",
    "internal_humidity_pct",
    "co2_ppm",
    "hive_weight_kg",
    "external_temperature_c",
    "external_humidity_pct",
    "rainfall_mm_hour",
    "wind_speed_mps",
    "apiary_season",
    "nectar_flow_season_proxy",
    "dearth_season_proxy",
    "monsoon_rain_period_proxy",
    "brood_health_score_0_100",
    "weight_change_24h_kg",
    "weight_change_72h_kg",
    "weight_std_24h_kg",
    "hour",
    "day_of_week",
    "month",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=None, help="Optional row limit for faster testing")
    return parser.parse_args()


def build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    numeric = X.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical = X.select_dtypes(exclude=["number", "bool"]).columns.tolist()
    return ColumnTransformer(
        transformers=[
            ("num", "passthrough", numeric),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=True), categorical),
        ],
        remainder="drop",
    )


def main() -> None:
    args = parse_args()
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"{DATA_PATH} does not exist. Run backend/eda/eda_analysis_harvest.py first."
        )

    data = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
    data = data.sort_values("timestamp").reset_index(drop=True)
    data["hour"] = data["timestamp"].dt.hour
    data["day_of_week"] = data["timestamp"].dt.dayofweek
    data["month"] = data["timestamp"].dt.month

    if args.sample and args.sample < len(data):
        # Keep chronological coverage rather than taking only the first time period.
        indices = np.linspace(0, len(data) - 1, args.sample, dtype=int)
        data = data.iloc[indices].reset_index(drop=True)

    missing = [column for column in FEATURES + [TARGET] if column not in data.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    X = data[FEATURES].copy()
    y = data[TARGET].copy()

    # Chronological split prevents training on future rows and testing on earlier rows.
    split_index = int(len(data) * 0.80)
    X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]

    models = {
        "Random Forest": RandomForestRegressor(
            n_estimators=180,
            max_depth=18,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        ),
        "XGBoost": XGBRegressor(
            n_estimators=350,
            learning_rate=0.05,
            max_depth=7,
            subsample=0.85,
            colsample_bytree=0.85,
            objective="reg:squarederror",
            random_state=42,
            n_jobs=-1,
        ),
        "LightGBM": LGBMRegressor(
            n_estimators=350,
            learning_rate=0.05,
            num_leaves=48,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=42,
            n_jobs=-1,
            verbosity=-1,
        ),
    }

    results: list[dict] = []
    trained: dict[str, Pipeline] = {}

    for name, estimator in models.items():
        print(f"Training {name}...")
        pipeline = Pipeline(
            steps=[
                ("preprocessor", build_preprocessor(X_train)),
                ("model", estimator),
            ]
        )
        pipeline.fit(X_train, y_train)
        predictions = np.clip(pipeline.predict(X_test), 0, 100)

        result = {
            "model": name,
            "mae": round(float(mean_absolute_error(y_test, predictions)), 4),
            "rmse": round(float(np.sqrt(mean_squared_error(y_test, predictions))), 4),
            "r2": round(float(r2_score(y_test, predictions)), 4),
        }
        print(result)
        results.append(result)
        trained[name] = pipeline

    results.sort(key=lambda row: (row["rmse"], row["mae"], -row["r2"]))
    best_name = results[0]["model"]
    best_model = trained[best_name]

    joblib.dump(best_model, MODEL_DIR / "best_hui_model.joblib")
    joblib.dump(FEATURES, MODEL_DIR / "hui_feature_columns.joblib")

    payload = {
        "best_model": best_name,
        "selection_rule": "Lowest RMSE, then lowest MAE, then highest R2",
        "split": "chronological_80_20",
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "results": results,
        "target": TARGET,
        "warning": "The HUI target is an expert-rule proxy, not observed ground truth.",
    }
    with (OUTPUT_DIR / "model_comparison.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    pd.DataFrame(results).to_csv(OUTPUT_DIR / "model_comparison.csv", index=False)
    print(f"Best model: {best_name}")
    print(f"Saved: {MODEL_DIR / 'best_hui_model.joblib'}")


if __name__ == "__main__":
    main()
