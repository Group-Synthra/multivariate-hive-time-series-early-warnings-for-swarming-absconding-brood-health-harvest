"""
Absconding Prediction Module — Module 03
Team Synthra

This file implements the absconding module required by the interim report:
- multivariate hive time-series preprocessing
- temporal feature engineering and sequence-aware trend features
- model comparison across multiple models
- probability, Low/Medium/High risk levels, ARM, alerts, and explainable factors
- per-hive dropdown-ready data for the React dashboard

Run from project root:
    python backend/scripts/run_absconding.py --model rf --compare-models

For LSTM final comparison, run the Colab/GPU script after this:
    python backend/ml/absconding/lstm_absconding.py --data backend/data/hive_data_with_features.csv --output backend/outputs/absconding --epochs 30
Then re-run:
    python backend/scripts/run_absconding.py --model rf --compare-models
The dashboard will merge the LSTM metrics into the model comparison table.
"""

from __future__ import annotations

import argparse
import json
import math
import warnings
import importlib.util
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier, HistGradientBoostingClassifier, GradientBoostingClassifier
from sklearn.linear_model import SGDClassifier, RidgeClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight

warnings.filterwarnings("ignore")


@dataclass
class AbscondingConfig:
    data_path: str
    output_dir: str
    model_type: str = "rf"  # fast | rf | extratrees | histgb | best_classical
    target_column: str = "absconding_label_next_72h"
    test_fraction: float = 0.20
    random_state: int = 42
    alert_threshold: float = 0.70
    medium_threshold: float = 0.35
    arm_alert_threshold: float = 0.08
    max_rows: int | None = None
    compare_models: bool = True
    timeline_points_per_hive: int = 180
    comparison_max_rows: int = 20000


BASE_FEATURES = [
    "temp", "humidity", "co2", "weight",
    "external_temp", "external_humidity", "rainfall_mm_hour", "wind_speed_mps",
    "nectar_flow_season_proxy", "dearth_season_proxy", "monsoon_rain_period_proxy",
    "hour_sin", "hour_cos", "doy_sin", "doy_cos", "dayofweek", "month",
    "temp_diff_1h", "humidity_diff_1h", "co2_diff_1h", "weight_change_1h",
    "weight_change_6h", "weight_change_24h", "weight_change_72h",
    "co2_change_6h", "co2_change_24h", "co2_change_72h",
    "temp_change_6h", "temp_change_24h", "humidity_change_6h", "humidity_change_24h",
    "temp_deviation_from_35", "humidity_deviation_from_optimal", "co2_high_flag",
    "rapid_weight_loss_flag", "sustained_weight_loss_24h", "sustained_weight_loss_72h",
    "environmental_stress_score", "stress_trend_24h",
    "temp_roll_mean_6h", "temp_roll_std_6h", "humidity_roll_mean_6h", "humidity_roll_std_6h",
    "co2_roll_mean_6h", "co2_roll_std_6h", "weight_roll_mean_6h", "weight_roll_std_6h",
    "temp_roll_mean_24h", "temp_roll_std_24h", "humidity_roll_mean_24h", "humidity_roll_std_24h",
    "co2_roll_mean_24h", "co2_roll_std_24h", "weight_roll_mean_24h", "weight_roll_std_24h",
    "temp_roll_mean_72h", "humidity_roll_mean_72h", "co2_roll_mean_72h", "weight_roll_mean_72h",
]

MODEL_NAME_MAP = {
    "fast": "Logistic Regression + Time-Series Features",
    "ridge": "Ridge Classifier + Time-Series Features",
    "rf": "Random Forest + Time-Series Features",
    "extratrees": "Extra Trees + Time-Series Features",
    "histgb": "Hist Gradient Boosting + Time-Series Features",
    "gb": "Gradient Boosting + Time-Series Features",
    "xgb": "XGBoost + Time-Series Features",
    "dt": "Decision Tree + Time-Series Features",
    "gnb": "Gaussian Naive Bayes + Time-Series Features",
    "best_classical": "Best Classical Time-Series Model",
}


def ensure_dirs(output_dir: Path) -> None:
    for sub in ["models", "metrics", "predictions", "plots"]:
        (output_dir / sub).mkdir(parents=True, exist_ok=True)


def load_dataset(path: Path, max_rows: int | None = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}\n"
            "Copy hive_data_with_features.csv into backend/data/ or pass --data path/to/csv."
        )
    df = pd.read_csv(path)
    if max_rows:
        # Keep the whole period shape; don't only take the first records.
        indices = np.linspace(0, len(df) - 1, min(max_rows, len(df)), dtype=int)
        df = df.iloc[indices].copy()
    df.columns = df.columns.astype(str).str.strip()

    required = [
        "timestamp", "hive_id", "internal_temperature_c", "internal_humidity_pct",
        "co2_ppm", "hive_weight_kg",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required dataset columns: {missing}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    bad_ts = int(df["timestamp"].isna().sum())
    if bad_ts:
        raise ValueError(f"Invalid timestamp values found: {bad_ts}")
    return df.sort_values(["hive_id", "timestamp"]).reset_index(drop=True)


def add_aliases_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    aliases = {
        "temp": "internal_temperature_c",
        "humidity": "internal_humidity_pct",
        "co2": "co2_ppm",
        "weight": "hive_weight_kg",
        "external_temp": "external_temperature_c",
        "external_humidity": "external_humidity_pct",
    }
    for new_col, source_col in aliases.items():
        if source_col in df.columns:
            df[new_col] = pd.to_numeric(df[source_col], errors="coerce")
        elif new_col not in df.columns:
            df[new_col] = np.nan

    optional_numeric = [
        "rainfall_mm_hour", "wind_speed_mps", "nectar_flow_season_proxy",
        "dearth_season_proxy", "monsoon_rain_period_proxy",
    ]
    for col in optional_numeric:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce")

    clean_cols = ["temp", "humidity", "co2", "weight", "external_temp", "external_humidity"] + optional_numeric
    df[clean_cols] = (
        df.groupby("hive_id", sort=False)[clean_cols]
          .transform(lambda s: s.interpolate(limit_direction="both"))
    )
    df[clean_cols] = df[clean_cols].ffill().bfill()

    # Moving median smoothing keeps long-term trends but suppresses isolated sensor spikes.
    for col in ["temp", "humidity", "co2", "weight"]:
        df[col] = (
            df.groupby("hive_id", sort=False)[col]
              .transform(lambda s: s.rolling(3, min_periods=1).median())
        )
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    g = df.groupby("hive_id", sort=False)

    df["hour"] = df["timestamp"].dt.hour
    df["dayofweek"] = df["timestamp"].dt.dayofweek
    df["month"] = df["timestamp"].dt.month
    df["dayofyear"] = df["timestamp"].dt.dayofyear
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["doy_sin"] = np.sin(2 * np.pi * df["dayofyear"] / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * df["dayofyear"] / 365.25)

    # Short and long trend features for chronic deterioration.
    for col, prefix in [("temp", "temp"), ("humidity", "humidity"), ("co2", "co2"), ("weight", "weight")]:
        df[f"{prefix}_diff_1h"] = g[col].diff().fillna(0)
    df["weight_change_1h"] = df["weight_diff_1h"]

    for lag in [6, 24, 72]:
        df[f"weight_change_{lag}h"] = g["weight"].diff(lag).fillna(0)
        df[f"co2_change_{lag}h"] = g["co2"].diff(lag).fillna(0)
        if lag in [6, 24]:
            df[f"temp_change_{lag}h"] = g["temp"].diff(lag).fillna(0)
            df[f"humidity_change_{lag}h"] = g["humidity"].diff(lag).fillna(0)

    for win in [6, 24, 72]:
        for col in ["temp", "humidity", "co2", "weight"]:
            df[f"{col}_roll_mean_{win}h"] = g[col].transform(lambda s: s.rolling(win, min_periods=1).mean())
            if win in [6, 24]:
                df[f"{col}_roll_std_{win}h"] = (
                    g[col].transform(lambda s: s.rolling(win, min_periods=2).std()).fillna(0)
                )

    df["temp_deviation_from_35"] = (df["temp"] - 35.0).abs()
    df["humidity_deviation_from_optimal"] = np.select(
        [df["humidity"] < 50, df["humidity"] > 65],
        [50 - df["humidity"], df["humidity"] - 65],
        default=0.0,
    )
    df["co2_high_flag"] = (df["co2"] > 3000).astype(int)
    df["rapid_weight_loss_flag"] = (df["weight_change_6h"] < -0.5).astype(int)
    df["sustained_weight_loss_24h"] = (df["weight_change_24h"] < -1.0).astype(int)
    df["sustained_weight_loss_72h"] = (df["weight_change_72h"] < -2.0).astype(int)

    df["environmental_stress_score"] = (
        np.clip(df["temp_deviation_from_35"] / 5, 0, 1) * 0.30
        + np.clip(df["humidity_deviation_from_optimal"] / 20, 0, 1) * 0.25
        + np.clip((df["co2"] - 1800) / 4000, 0, 1) * 0.25
        + np.clip((-df["weight_change_24h"]) / 3, 0, 1) * 0.20
    )
    df["stress_trend_24h"] = g["environmental_stress_score"].diff(24).fillna(0)

    if "absconding_label_next_72h" not in df.columns and "absconding_event_label" in df.columns:
        # Construct 72-hour look-ahead label from event indicator as fallback.
        def _forward_label(s: pd.Series) -> pd.Series:
            return s.iloc[::-1].rolling(72, min_periods=1).max().iloc[::-1]
        df["absconding_label_next_72h"] = g["absconding_event_label"].transform(_forward_label).fillna(0).astype(int)

    return df.replace([np.inf, -np.inf], np.nan).fillna(0)


def time_based_split(df: pd.DataFrame, test_fraction: float) -> Tuple[np.ndarray, np.ndarray]:
    unique_times = np.array(sorted(df["timestamp"].unique()))
    split_index = max(1, min(len(unique_times) - 1, int(len(unique_times) * (1 - test_fraction))))
    split_time = unique_times[split_index]
    train_mask = df["timestamp"] < split_time
    test_mask = ~train_mask
    return train_mask.values, test_mask.values


def build_model(model_type: str, random_state: int):
    if model_type == "rf":
        return RandomForestClassifier(
            n_estimators=30, max_depth=10, min_samples_leaf=12,
            class_weight="balanced_subsample", n_jobs=1, random_state=random_state,
        )
    if model_type == "extratrees":
        return ExtraTreesClassifier(
            n_estimators=40, max_depth=12, min_samples_leaf=10,
            class_weight="balanced", n_jobs=1, random_state=random_state,
        )
    if model_type == "histgb":
        return HistGradientBoostingClassifier(
            max_iter=80, learning_rate=0.08, max_leaf_nodes=31,
            l2_regularization=0.1, random_state=random_state,
        )
    if model_type == "gb":
        return GradientBoostingClassifier(
            n_estimators=80, learning_rate=0.06, max_depth=3, random_state=random_state,
        )
    if model_type == "xgb":
        try:
            from xgboost import XGBClassifier
        except Exception as exc:
            raise RuntimeError("XGBoost is not installed. Install xgboost or remove xgb from comparison.") from exc
        return XGBClassifier(
            n_estimators=120, max_depth=4, learning_rate=0.05, subsample=0.85, colsample_bytree=0.85,
            eval_metric="logloss", tree_method="hist", random_state=random_state, n_jobs=1,
        )
    if model_type == "dt":
        return DecisionTreeClassifier(
            max_depth=12, min_samples_leaf=12, class_weight="balanced", random_state=random_state,
        )
    if model_type == "ridge":
        return Pipeline([("scale", StandardScaler()), ("clf", RidgeClassifier(class_weight="balanced", random_state=random_state))])
    if model_type == "gnb":
        return Pipeline([("scale", StandardScaler()), ("clf", GaussianNB())])
    # Fast time-series logistic baseline.
    return Pipeline([
        ("scale", StandardScaler()),
        ("clf", SGDClassifier(
            loss="log_loss", penalty="elasticnet", alpha=0.0003, l1_ratio=0.05,
            class_weight="balanced", max_iter=2000, tol=1e-4, random_state=random_state,
        )),
    ])


def predict_proba(model, X: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    if hasattr(model, "decision_function"):
        decision = model.decision_function(X)
        return 1 / (1 + np.exp(-decision))
    return model.predict(X).astype(float)


def choose_threshold(y_true: np.ndarray, prob: np.ndarray, beta: float = 2.0) -> float:
    precision, recall, thresholds = precision_recall_curve(y_true, prob)
    if len(thresholds) == 0:
        return 0.5
    fbeta = (1 + beta**2) * precision[:-1] * recall[:-1] / (
        beta**2 * precision[:-1] + recall[:-1] + 1e-12
    )
    return float(thresholds[int(np.nanargmax(fbeta))])


def compute_metrics(y_true: np.ndarray, prob: np.ndarray, threshold: float) -> Dict[str, Any]:
    pred = (prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    metrics = {
        "threshold": round(float(threshold), 4),
        "accuracy": round(float(accuracy_score(y_true, pred)), 4),
        "precision": round(float(precision_score(y_true, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, pred, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_true, pred, zero_division=0)), 4),
        "mae": round(float(mean_absolute_error(y_true, prob)), 4),
        "rmse": round(float(math.sqrt(mean_squared_error(y_true, prob))), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "positive_rate_actual": round(float(np.mean(y_true)), 4),
        "positive_rate_predicted": round(float(np.mean(pred)), 4),
    }
    try:
        metrics["roc_auc"] = round(float(roc_auc_score(y_true, prob)), 4)
    except Exception:
        metrics["roc_auc"] = None
    try:
        metrics["pr_auc"] = round(float(average_precision_score(y_true, prob)), 4)
    except Exception:
        metrics["pr_auc"] = None
    metrics["defence_score"] = round(float(
        0.40 * metrics["recall"]
        + 0.25 * metrics["f1_score"]
        + 0.20 * (metrics["pr_auc"] or 0)
        + 0.15 * (metrics["roc_auc"] or 0)
    ), 4)
    return metrics


def model_feature_importance(model, feature_names: List[str]) -> List[Dict[str, Any]]:
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    elif isinstance(model, Pipeline):
        clf = model.named_steps.get("clf")
        importances = np.abs(clf.coef_[0]) if hasattr(clf, "coef_") else np.zeros(len(feature_names))
    else:
        importances = np.zeros(len(feature_names))
    items = [{"feature": f, "importance": round(float(v), 6)} for f, v in zip(feature_names, importances)]
    return sorted(items, key=lambda x: x["importance"], reverse=True)


def train_one_model(model_type: str, X_train: pd.DataFrame, y_train: np.ndarray, X_test: pd.DataFrame,
                    y_test: np.ndarray, random_state: int) -> Tuple[Any, Dict[str, Any], np.ndarray, float]:
    if model_type == "rule":
        train_prob = np.clip(X_train["environmental_stress_score"].values, 0, 1)
        test_prob = np.clip(X_test["environmental_stress_score"].values, 0, 1)
        threshold = choose_threshold(y_train, train_prob)
        metrics = compute_metrics(y_test, test_prob, threshold)
        metrics.update({"model_key": "rule", "model_name": "Rule-Based Environmental Stress Baseline", "model_family": "Rules"})
        return None, metrics, test_prob, threshold

    model = build_model(model_type, random_state)
    model.fit(X_train, y_train)
    train_prob = predict_proba(model, X_train)
    threshold = choose_threshold(y_train, train_prob)
    test_prob = predict_proba(model, X_test)
    metrics = compute_metrics(y_test, test_prob, threshold)
    metrics.update({
        "model_key": model_type,
        "model_name": MODEL_NAME_MAP.get(model_type, model_type),
        "model_family": "Classical ML with engineered time-series features",
    })
    return model, metrics, test_prob, threshold


def read_lstm_metrics(output_dir: Path) -> Dict[str, Any] | None:
    path = output_dir / "metrics" / "lstm_absconding_metrics.json"
    if not path.exists():
        return None
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
        row.setdefault("model_key", "lstm")
        row.setdefault("model_name", "LSTM + Time-Series Sequence")
        row.setdefault("model_family", "Deep learning sequence model")
        row["used_for_backend_predictions"] = False
        row["note"] = "Generated by lstm_absconding.py / Google Colab and merged into comparison."
        # ensure defence_score is present
        if "defence_score" not in row:
            row["defence_score"] = round(float(
                0.40 * row.get("recall", 0)
                + 0.25 * row.get("f1_score", 0)
                + 0.20 * (row.get("pr_auc") or 0)
                + 0.15 * (row.get("roc_auc") or 0)
            ), 4)
        return row
    except Exception:
        return None


def compare_models(X_train: pd.DataFrame, y_train: np.ndarray, X_test: pd.DataFrame, y_test: np.ndarray,
                   output_dir: Path, random_state: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    model_keys = ["rule", "gnb", "fast", "ridge", "dt", "rf", "extratrees"]
    rows.append({
        "model_key": "xgb",
        "model_name": "XGBoost + Time-Series Features",
        "model_family": "Gradient boosting baseline",
        "status": "Optional",
        "note": "Run --model xgb or enable xgb manually if you want this heavier optional model."
    })
    for key in model_keys:
        try:
            _, metrics, _, _ = train_one_model(key, X_train, y_train, X_test, y_test, random_state)
            rows.append(metrics)
        except Exception as exc:
            rows.append({"model_key": key, "model_name": MODEL_NAME_MAP.get(key, key), "error": str(exc)})

    lstm_row = read_lstm_metrics(output_dir)
    if lstm_row:
        rows.append(lstm_row)
    else:
        rows.append({
            "model_key": "lstm",
            "model_name": "LSTM + Time-Series Sequence",
            "model_family": "Deep learning sequence model",
            "status": "Not run yet",
            "note": "Run backend/ml/absconding/lstm_absconding.py in Google Colab/GPU to add real LSTM metrics.",
        })

    # Sort rows with metrics first by defence score.
    rows = sorted(rows, key=lambda r: r.get("defence_score", -1), reverse=True)
    pd.DataFrame(rows).to_csv(output_dir / "metrics" / "absconding_model_comparison.csv", index=False)
    (output_dir / "metrics" / "absconding_model_comparison.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    save_model_comparison_plot(rows, output_dir)
    return rows


def save_model_comparison_plot(rows: List[Dict[str, Any]], output_dir: Path) -> None:
    valid = [r for r in rows if "f1_score" in r]
    if not valid:
        return
    labels = [r["model_name"].replace(" + ", "\n+") for r in valid]
    recall = [r.get("recall", 0) for r in valid]
    f1 = [r.get("f1_score", 0) for r in valid]
    x = np.arange(len(labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(12, 5.8))
    ax.bar(x - width/2, recall, width, label="Recall")
    ax.bar(x + width/2, f1, width, label="F1 score")
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.05)
    ax.set_title("Absconding Model Comparison — Time-Based Test Split")
    ax.set_xticks(x, labels, rotation=20, ha="right")
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "plots" / "absconding_model_comparison.png", dpi=150)
    plt.close()


def risk_level(prob: float, arm: float, medium_threshold: float, high_threshold: float, arm_threshold: float) -> str:
    if prob >= high_threshold or (prob >= medium_threshold and arm >= arm_threshold):
        return "High"
    if prob >= medium_threshold or arm >= arm_threshold:
        return "Medium"
    return "Low"


def arm_trend_label(arm: float) -> str:
    if arm >= 0.12:
        return "Rapidly Increasing"
    if arm >= 0.04:
        return "Increasing"
    if arm <= -0.08:
        return "Improving"
    return "Stable"


def explanations_for_row(row: pd.Series) -> List[Dict[str, Any]]:
    checks = [
        ("Rapid hive weight decline", -row.get("weight_change_24h", 0), "kg/24h", row.get("weight_change_24h", 0) < -1.0),
        ("Sustained 72h weight loss", -row.get("weight_change_72h", 0), "kg/72h", row.get("weight_change_72h", 0) < -2.0),
        ("CO₂ accumulation", row.get("co2", 0), "ppm", row.get("co2", 0) > 3000),
        ("Temperature instability", row.get("temp_deviation_from_35", 0), "°C from 35", row.get("temp_deviation_from_35", 0) > 1.0),
        ("Humidity deviation", row.get("humidity_deviation_from_optimal", 0), "% outside 50–65", row.get("humidity_deviation_from_optimal", 0) > 5),
        ("Combined environmental stress", row.get("environmental_stress_score", 0), "0–1", row.get("environmental_stress_score", 0) > 0.45),
    ]
    factors = []
    for name, value, unit, active in checks:
        if active:
            factors.append({
                "factor": name,
                "value": round(float(value), 3),
                "unit": unit,
                "interpretation": f"{name} is contributing to elevated absconding risk.",
            })
    if not factors:
        factors.append({
            "factor": "No severe single-factor trigger",
            "value": 0,
            "unit": "",
            "interpretation": "Risk is mainly based on combined long-term time-series pattern.",
        })
    return factors[:5]


def add_predictions_and_arm(df: pd.DataFrame, probabilities: np.ndarray) -> pd.DataFrame:
    df = df.copy()
    df["absconding_risk_probability"] = np.clip(probabilities, 0, 1)
    g = df.groupby("hive_id", sort=False)
    df["previous_risk"] = g["absconding_risk_probability"].shift(1)
    df["previous_timestamp"] = g["timestamp"].shift(1)
    delta_hours = (df["timestamp"] - df["previous_timestamp"]).dt.total_seconds() / 3600.0
    delta_hours = delta_hours.replace(0, np.nan).fillna(1.0)
    df["arm"] = (df["absconding_risk_probability"] - df["previous_risk"].fillna(df["absconding_risk_probability"])) / delta_hours
    df["arm"] = df["arm"].replace([np.inf, -np.inf], 0).fillna(0)
    df["risk_percentage"] = df["absconding_risk_probability"] * 100
    return df


def make_per_hive_outputs(df: pd.DataFrame, cfg: AbscondingConfig) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    latest_rows = df.sort_values(["hive_id", "timestamp"]).groupby("hive_id", sort=False).tail(1).copy()
    per_hive: List[Dict[str, Any]] = []
    alerts: List[Dict[str, Any]] = []
    hive_details: Dict[str, Any] = {}

    for _, row in latest_rows.iterrows():
        prob = float(row["absconding_risk_probability"])
        arm = float(row["arm"])
        level = risk_level(prob, arm, cfg.medium_threshold, cfg.alert_threshold, cfg.arm_alert_threshold)
        trend = arm_trend_label(arm)
        factors = explanations_for_row(row)
        alert_required = level == "High"
        message = (
            f"WARNING: {row['hive_id']} absconding risk {prob*100:.1f}% ({trend}). "
            "Check queen status, food stores, ventilation, pests, and hive disturbance."
            if alert_required else
            f"{row['hive_id']} absconding risk is {level.lower()} ({prob*100:.1f}%). Continue monitoring."
        )
        latest_sensor = {
            "temperature_c": round(float(row["temp"]), 2),
            "humidity_pct": round(float(row["humidity"]), 2),
            "co2_ppm": round(float(row["co2"]), 2),
            "weight_kg": round(float(row["weight"]), 2),
            "weight_change_24h": round(float(row.get("weight_change_24h", 0)), 3),
            "co2_change_24h": round(float(row.get("co2_change_24h", 0)), 3),
            "environmental_stress_score": round(float(row.get("environmental_stress_score", 0)), 4),
        }
        item = {
            "hive": str(row["hive_id"]),
            "timestamp": str(row["timestamp"]),
            "risk_probability": round(prob, 4),
            "risk_percentage": round(prob * 100, 2),
            "risk_level": level,
            "arm": round(arm, 4),
            "arm_trend": trend,
            "alert_required": bool(alert_required),
            "message": message,
            "latest_sensor_readings": latest_sensor,
            "key_factors": factors,
        }
        per_hive.append(item)
        if alert_required:
            alerts.append(item)

    per_hive = sorted(per_hive, key=lambda x: x["risk_probability"], reverse=True)

    # Dropdown details: one timeline per hive for frontend line charts and table.
    for hive_id, sub in df.sort_values(["hive_id", "timestamp"]).groupby("hive_id", sort=False):
        tail = sub.tail(cfg.timeline_points_per_hive).copy()
        timeline_cols = [
            "timestamp", "risk_percentage", "arm", "temp", "humidity", "co2", "weight",
            "weight_change_24h", "co2_change_24h", "environmental_stress_score",
        ]
        if cfg.target_column in tail.columns:
            timeline_cols.append(cfg.target_column)
        timeline = []
        for _, r in tail[timeline_cols].iterrows():
            row_obj = {
                "timestamp": str(r["timestamp"]),
                "risk_percentage": round(float(r["risk_percentage"]), 2),
                "arm": round(float(r["arm"]), 4),
                "temperature_c": round(float(r["temp"]), 2),
                "humidity_pct": round(float(r["humidity"]), 2),
                "co2_ppm": round(float(r["co2"]), 2),
                "weight_kg": round(float(r["weight"]), 2),
                "weight_change_24h": round(float(r["weight_change_24h"]), 3),
                "co2_change_24h": round(float(r["co2_change_24h"]), 3),
                "environmental_stress_score": round(float(r["environmental_stress_score"]), 4),
            }
            if cfg.target_column in tail.columns:
                row_obj["actual_next_72h_label"] = int(r[cfg.target_column])
            timeline.append(row_obj)
        latest = next((x for x in per_hive if x["hive"] == str(hive_id)), None)
        hive_details[str(hive_id)] = {"latest": latest, "timeline": timeline}

    return per_hive, alerts, hive_details


def save_plots(df_test: pd.DataFrame, y_test: np.ndarray, prob_test: np.ndarray,
               metrics: Dict[str, Any], feature_importance: List[Dict[str, Any]], output_dir: Path) -> None:
    plots_dir = output_dir / "plots"
    cm = metrics["confusion_matrix"]
    matrix = np.array([[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]])
    fig, ax = plt.subplots(figsize=(5.5, 4.8))
    im = ax.imshow(matrix)
    ax.set_xticks([0, 1], labels=["Pred Normal", "Pred Risk"])
    ax.set_yticks([0, 1], labels=["Actual Normal", "Actual Risk"])
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(matrix[i, j]), ha="center", va="center", fontsize=13, fontweight="bold")
    ax.set_title("Absconding Prediction Confusion Matrix")
    fig.colorbar(im, ax=ax)
    plt.tight_layout()
    plt.savefig(plots_dir / "absconding_confusion_matrix.png", dpi=150)
    plt.close()

    top = feature_importance[:12]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh([x["feature"] for x in reversed(top)], [x["importance"] for x in reversed(top)])
    ax.set_title("Top Absconding Risk Contributing Features")
    ax.set_xlabel("Importance")
    plt.tight_layout()
    plt.savefig(plots_dir / "absconding_feature_importance.png", dpi=150)
    plt.close()

    df_plot = df_test.copy()
    df_plot["actual"] = y_test
    if df_plot["hive_id"].nunique() > 0:
        top_hive = df_plot.groupby("hive_id")["absconding_risk_probability"].max().sort_values(ascending=False).index[0]
        sub = df_plot[df_plot["hive_id"] == top_hive].sort_values("timestamp").tail(400)
        fig, ax = plt.subplots(figsize=(13, 5))
        ax.plot(sub["timestamp"], sub["absconding_risk_probability"], label="Risk probability")
        ax.plot(sub["timestamp"], sub["arm"].clip(-0.2, 0.2), label="ARM (clipped)")
        actual_points = sub[sub["actual"] == 1]
        if len(actual_points):
            ax.scatter(actual_points["timestamp"], actual_points["absconding_risk_probability"], s=25, label="Actual next-72h label")
        ax.axhline(0.70, linestyle="--", label="High threshold")
        ax.axhline(0.35, linestyle="--", label="Medium threshold")
        ax.set_title(f"Absconding Risk Timeline with ARM - {top_hive}")
        ax.set_ylabel("Risk / ARM")
        ax.legend()
        plt.tight_layout()
        plt.savefig(plots_dir / "absconding_risk_timeline.png", dpi=150)
        plt.close()


def make_selection_rationale(model_comparison: List[Dict[str, Any]]) -> Dict[str, Any]:
    valid = [r for r in model_comparison if "defence_score" in r]
    best = max(valid, key=lambda r: r.get("defence_score", 0)) if valid else None
    lstm = next((r for r in model_comparison if r.get("model_key") == "lstm" and "defence_score" in r), None)
    return {
        "best_model_by_defence_score": best.get("model_name") if best else None,
        "lstm_metrics_available": bool(lstm),
        "is_lstm_best": bool(lstm and best and best.get("model_key") == "lstm"),
        "why_lstm_is_defensible": [
            "Absconding is described as a long-term instability pattern, not a single sudden spike; LSTM reads ordered windows rather than isolated rows.",
            "LSTM can capture long-term dependencies and nonlinear interactions between temperature, humidity, CO₂, and weight.",
            "Classical models are still included as baselines so the final selection is defended by measured Recall, F1, PR-AUC, and ROC-AUC, not only by theory.",
            "For this risk module, Recall is weighted strongly because a missed absconding warning is more costly than a moderate false alarm.",
        ],
        "honest_defence_note": (
            "Use the LSTM as the final selected model only after running lstm_absconding.py and confirming that its recall/F1/PR-AUC are the best or clearly competitive. "
            "Do not fake metrics; the dashboard marks LSTM as not run until real Colab metrics are available."
        ),
    }



def stratified_cap(X: pd.DataFrame, y: np.ndarray, max_rows: int | None, random_state: int) -> Tuple[pd.DataFrame, np.ndarray]:
    """Cap training rows for model comparison while keeping positive labels represented."""
    if max_rows is None or len(X) <= max_rows:
        return X, y
    rng = np.random.default_rng(random_state)
    pos_idx = np.where(y == 1)[0]
    neg_idx = np.where(y == 0)[0]
    # Keep all positives when possible, because absconding labels are rare.
    n_pos = min(len(pos_idx), max(1, int(max_rows * 0.35)))
    n_neg = max_rows - n_pos
    pos_take = rng.choice(pos_idx, size=n_pos, replace=False) if len(pos_idx) > n_pos else pos_idx
    neg_take = rng.choice(neg_idx, size=min(len(neg_idx), n_neg), replace=False) if len(neg_idx) > n_neg else neg_idx
    take = np.sort(np.concatenate([pos_take, neg_take]))
    return X.iloc[take], y[take]

def train_absconding_module(cfg: AbscondingConfig) -> Dict[str, Any]:
    output_dir = Path(cfg.output_dir)
    ensure_dirs(output_dir)

    raw = load_dataset(Path(cfg.data_path), cfg.max_rows)
    df = engineer_features(add_aliases_and_clean(raw))
    if cfg.target_column not in df.columns:
        raise ValueError(f"Target column '{cfg.target_column}' was not found. The dataset should include absconding_label_next_72h.")
    df[cfg.target_column] = pd.to_numeric(df[cfg.target_column], errors="coerce").fillna(0).astype(int)

    features = [f for f in BASE_FEATURES if f in df.columns]
    X = df[features].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0)
    y = df[cfg.target_column].values.astype(int)
    train_mask, test_mask = time_based_split(df, cfg.test_fraction)
    X_train, X_test = X.loc[train_mask], X.loc[test_mask]
    y_train, y_test = y[train_mask], y[test_mask]

    if len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2:
        raise ValueError("Train/test split has only one class. Use full dataset or reduce --max-rows carefully.")

    X_train_cmp, y_train_cmp = stratified_cap(X_train, y_train, cfg.comparison_max_rows, cfg.random_state)
    X_test_cmp, y_test_cmp = stratified_cap(X_test, y_test, min(max(cfg.comparison_max_rows // 3, 5000), len(X_test)), cfg.random_state + 1)
    model_comparison = compare_models(X_train_cmp, y_train_cmp, X_test_cmp, y_test_cmp, output_dir, cfg.random_state) if cfg.compare_models else []

    active_model_key = cfg.model_type
    if active_model_key == "best_classical":
        classical = [r for r in model_comparison if r.get("model_key") in ["gnb", "fast", "dt", "gb", "histgb", "ridge", "rf", "extratrees", "xgb"] and "defence_score" in r]
        active_model_key = max(classical, key=lambda r: r.get("defence_score", 0))["model_key"] if classical else "rf"

    model, metrics, prob_test, threshold = train_one_model(active_model_key, X_train, y_train, X_test, y_test, cfg.random_state)
    metrics.update({
        "model_type": active_model_key,
        "model_name": MODEL_NAME_MAP.get(active_model_key, active_model_key),
        "training_records": int(len(X_train)),
        "testing_records": int(len(X_test)),
        "total_records": int(len(df)),
        "total_hives": int(df["hive_id"].nunique()),
        "analysis_start": str(df["timestamp"].min()),
        "analysis_end": str(df["timestamp"].max()),
        "features_used": features,
        "target_column": cfg.target_column,
        "comparison_training_records": int(len(X_train_cmp)) if cfg.compare_models else 0,
        "comparison_testing_records": int(len(X_test_cmp)) if cfg.compare_models else 0,
        "note": "Backend predictions use the active saved classical model. Model comparison uses a stratified capped sample for speed and LSTM metrics are merged after running the Colab/GPU script.",
    })

    full_prob = predict_proba(model, X)
    df_pred = add_predictions_and_arm(df, full_prob)
    df_test_pred = df_pred.loc[test_mask].copy()
    df_test_pred["actual_label"] = y_test

    feature_importance = model_feature_importance(model, features)
    per_hive, alerts, hive_details = make_per_hive_outputs(df_pred, cfg)
    save_plots(df_test_pred, y_test, prob_test, metrics, feature_importance, output_dir)

    selection_rationale = make_selection_rationale(model_comparison)
    dashboard = {
        "summary": {
            "module_name": "Prediction of Absconding Behavior",
            "total_hives": metrics["total_hives"],
            "total_records": metrics["total_records"],
            "analysis_start": metrics["analysis_start"],
            "analysis_end": metrics["analysis_end"],
            "positive_label_count": int(df[cfg.target_column].sum()),
            "positive_label_percentage": round(float(df[cfg.target_column].mean() * 100), 3),
            "high_risk_hives": int(sum(1 for h in per_hive if h["risk_level"] == "High")),
            "medium_risk_hives": int(sum(1 for h in per_hive if h["risk_level"] == "Medium")),
            "low_risk_hives": int(sum(1 for h in per_hive if h["risk_level"] == "Low")),
            "latest_alerts": len(alerts),
            "active_backend_model": metrics["model_name"],
        },
        "model_metrics": metrics,
        "model_comparison": model_comparison,
        "model_selection_rationale": selection_rationale,
        "risk_thresholds": {
            "low": f"< {cfg.medium_threshold}",
            "medium": f"{cfg.medium_threshold} - {cfg.alert_threshold}",
            "high": f">= {cfg.alert_threshold}",
            "arm_escalation": f">= {cfg.arm_alert_threshold}",
        },
        "hive_options": [h["hive"] for h in per_hive],
        "per_hive_absconding_risk": per_hive,
        "hive_details": hive_details,
        "alerts": alerts,
        "feature_importance": feature_importance[:20],
        "plots": {
            "confusion_matrix": "/api/absconding/images/absconding_confusion_matrix.png",
            "feature_importance": "/api/absconding/images/absconding_feature_importance.png",
            "risk_timeline": "/api/absconding/images/absconding_risk_timeline.png",
            "model_comparison": "/api/absconding/images/absconding_model_comparison.png",
        },
        "explainability_note": (
            "Key factors are generated from domain-informed stress features: weight decline, CO₂ buildup, "
            "temperature instability, humidity deviation, and combined environmental stress."
        ),
    }

    model_path = output_dir / "models" / f"absconding_{active_model_key}_model.joblib"
    joblib.dump({"model": model, "features": features, "threshold": threshold, "config": asdict(cfg)}, model_path)

    (output_dir / "metrics" / "absconding_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (output_dir / "absconding_dashboard.json").write_text(json.dumps(dashboard, indent=2), encoding="utf-8")
    pd.DataFrame(model_comparison).to_csv(output_dir / "metrics" / "absconding_model_comparison.csv", index=False)
    pd.DataFrame(feature_importance).to_csv(output_dir / "metrics" / "absconding_feature_importance.csv", index=False)

    pred_cols = [
        "timestamp", "hive_id", "absconding_risk_probability", "risk_percentage", "arm",
        "temp", "humidity", "co2", "weight", "weight_change_24h", "co2_change_24h", cfg.target_column,
    ]
    df_pred[pred_cols].tail(10000).to_csv(output_dir / "predictions" / "absconding_predictions_tail.csv", index=False)
    pd.DataFrame(per_hive).to_csv(output_dir / "predictions" / "latest_absconding_risk_per_hive.csv", index=False)

    return dashboard


def predict_latest_from_saved_model(model_path: Path, data_path: Path, output_dir: Path) -> Dict[str, Any]:
    bundle = joblib.load(model_path)
    features = bundle["features"]
    model = bundle["model"]
    cfg_dict = bundle.get("config", {})
    cfg = AbscondingConfig(**cfg_dict) if cfg_dict else AbscondingConfig(str(data_path), str(output_dir))
    raw = load_dataset(data_path)
    df = engineer_features(add_aliases_and_clean(raw))
    X = df[features].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0)
    prob = predict_proba(model, X)
    df_pred = add_predictions_and_arm(df, prob)
    per_hive, alerts, hive_details = make_per_hive_outputs(df_pred, cfg)
    return {"per_hive_absconding_risk": per_hive, "alerts": alerts, "hive_details": hive_details}


def parse_args() -> AbscondingConfig:
    parser = argparse.ArgumentParser(description="Train and generate absconding prediction outputs.")
    parser.add_argument("--data", default="backend/data/hive_data_with_features.csv")
    parser.add_argument("--output", default="backend/outputs/absconding")
    parser.add_argument("--model", choices=["fast", "gnb", "ridge", "dt", "gb", "histgb", "rf", "extratrees", "xgb", "best_classical"], default="rf")
    parser.add_argument("--target", default="absconding_label_next_72h")
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--no-compare-models", action="store_true")
    parser.add_argument("--timeline-points-per-hive", type=int, default=180)
    parser.add_argument("--comparison-max-rows", type=int, default=20000)
    args = parser.parse_args()
    return AbscondingConfig(
        data_path=args.data,
        output_dir=args.output,
        model_type=args.model,
        target_column=args.target,
        max_rows=args.max_rows,
        compare_models=not args.no_compare_models,
        timeline_points_per_hive=args.timeline_points_per_hive,
        comparison_max_rows=args.comparison_max_rows,
    )


if __name__ == "__main__":
    config = parse_args()
    result = train_absconding_module(config)
    print("\n✅ Absconding module completed.")
    print(f"   Output: {config.output_dir}/absconding_dashboard.json")
    print(f"   Active backend model: {result['summary']['active_backend_model']}")
    print(f"   High-risk hives: {result['summary']['high_risk_hives']}")
    print(f"   Latest alerts: {result['summary']['latest_alerts']}")
    print(f"   Recall: {result['model_metrics']['recall']} | F1: {result['model_metrics']['f1_score']} | PR-AUC: {result['model_metrics']['pr_auc']}")
