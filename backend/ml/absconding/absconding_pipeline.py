
"""
Absconding Prediction Module
Team Synthra - Module 03

Purpose
-------
Builds the Absconding Behaviour Prediction module described in the interim report:
1. Loads multivariate hive time-series data.
2. Performs preprocessing, temporal alignment, smoothing, and feature engineering.
3. Trains a fast time-series baseline model and/or Random Forest classifier.
4. Generates absconding risk probability, Low/Medium/High risk levels, ARM,
   explainable contributing factors, alert messages, and dashboard JSON.
5. Saves metrics, plots, model artefacts, and prediction tables for backend/frontend use.

Expected dataset columns
------------------------
timestamp, hive_id, internal_temperature_c, internal_humidity_pct, co2_ppm,
hive_weight_kg, external_temperature_c, external_humidity_pct, rainfall_mm_hour,
wind_speed_mps, nectar_flow_season_proxy, dearth_season_proxy,
monsoon_rain_period_proxy, absconding_label_next_72h

Run from project root:
    python backend/scripts/run_absconding.py
or directly:
    python backend/ml/absconding/absconding_pipeline.py --data backend/data/hive_data_with_features.csv

Recommended:
    Use --model rf for final report screenshots.
    Use --model fast during development.
"""

from __future__ import annotations

import argparse
import json
import math
import warnings
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple, Any

import joblib
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import SGDClassifier
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
from sklearn.utils.class_weight import compute_class_weight


warnings.filterwarnings("ignore")


@dataclass
class AbscondingConfig:
    data_path: str
    output_dir: str
    model_type: str = "fast"   # fast | rf
    target_column: str = "absconding_label_next_72h"
    test_fraction: float = 0.20
    random_state: int = 42
    alert_threshold: float = 0.70
    medium_threshold: float = 0.35
    arm_alert_threshold: float = 0.08
    max_rows: int | None = None


BASE_FEATURES = [
    "temp",
    "humidity",
    "co2",
    "weight",
    "external_temp",
    "external_humidity",
    "rainfall_mm_hour",
    "wind_speed_mps",
    "nectar_flow_season_proxy",
    "dearth_season_proxy",
    "monsoon_rain_period_proxy",
    "hour_sin",
    "hour_cos",
    "doy_sin",
    "doy_cos",
    "dayofweek",
    "month",
    "temp_diff_1h",
    "humidity_diff_1h",
    "co2_diff_1h",
    "weight_change_1h",
    "weight_change_6h",
    "weight_change_24h",
    "co2_change_6h",
    "co2_change_24h",
    "temp_change_6h",
    "humidity_change_6h",
    "temp_deviation_from_35",
    "humidity_deviation_from_optimal",
    "co2_high_flag",
    "rapid_weight_loss_flag",
    "sustained_weight_loss_24h",
    "environmental_stress_score",
    "temp_roll_mean_6h",
    "temp_roll_std_6h",
    "humidity_roll_mean_6h",
    "humidity_roll_std_6h",
    "co2_roll_mean_6h",
    "co2_roll_std_6h",
    "weight_roll_mean_6h",
    "weight_roll_std_6h",
    "temp_roll_mean_24h",
    "temp_roll_std_24h",
    "humidity_roll_mean_24h",
    "humidity_roll_std_24h",
    "co2_roll_mean_24h",
    "co2_roll_std_24h",
    "weight_roll_mean_24h",
    "weight_roll_std_24h",
    "temp_roll_mean_72h",
    "humidity_roll_mean_72h",
    "co2_roll_mean_72h",
    "weight_roll_mean_72h",
]


def ensure_dirs(output_dir: Path) -> None:
    for sub in ["models", "metrics", "predictions", "plots"]:
        (output_dir / sub).mkdir(parents=True, exist_ok=True)


def load_dataset(path: Path, max_rows: int | None = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}\n"
            "Copy hive_data_with_features.csv into backend/data/ or pass --data path/to/csv"
        )

    df = pd.read_csv(path)
    if max_rows:
        # keep chronological coverage by sampling evenly, not only from the beginning
        indices = np.linspace(0, len(df) - 1, min(max_rows, len(df)), dtype=int)
        df = df.iloc[indices].copy()

    df.columns = df.columns.astype(str).str.strip()
    required = [
        "timestamp", "hive_id", "internal_temperature_c", "internal_humidity_pct",
        "co2_ppm", "hive_weight_kg"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required dataset columns: {missing}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    if df["timestamp"].isna().any():
        bad = int(df["timestamp"].isna().sum())
        raise ValueError(f"Invalid timestamps found: {bad}")

    df = df.sort_values(["hive_id", "timestamp"]).reset_index(drop=True)
    return df


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
        "rainfall_mm_hour",
        "wind_speed_mps",
        "nectar_flow_season_proxy",
        "dearth_season_proxy",
        "monsoon_rain_period_proxy",
    ]
    for col in optional_numeric:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce")

    clean_cols = [
        "temp", "humidity", "co2", "weight", "external_temp", "external_humidity"
    ] + optional_numeric

    # temporal interpolation inside each hive keeps time-series continuity
    df[clean_cols] = (
        df.groupby("hive_id", sort=False)[clean_cols]
          .transform(lambda x: x.interpolate(limit_direction="both"))
    )
    df[clean_cols] = df[clean_cols].ffill().bfill()

    # Moving median smoothing reduces spikes without removing behavioural trends.
    smooth_cols = ["temp", "humidity", "co2", "weight"]
    for col in smooth_cols:
        df[f"{col}_smoothed"] = (
            df.groupby("hive_id", sort=False)[col]
              .transform(lambda x: x.rolling(3, min_periods=1).median())
        )
        df[col] = df[f"{col}_smoothed"]

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

    df["temp_diff_1h"] = g["temp"].diff().fillna(0)
    df["humidity_diff_1h"] = g["humidity"].diff().fillna(0)
    df["co2_diff_1h"] = g["co2"].diff().fillna(0)
    df["weight_change_1h"] = g["weight"].diff().fillna(0)

    df["weight_change_6h"] = g["weight"].diff(6).fillna(0)
    df["weight_change_24h"] = g["weight"].diff(24).fillna(0)
    df["co2_change_6h"] = g["co2"].diff(6).fillna(0)
    df["co2_change_24h"] = g["co2"].diff(24).fillna(0)
    df["temp_change_6h"] = g["temp"].diff(6).fillna(0)
    df["humidity_change_6h"] = g["humidity"].diff(6).fillna(0)

    for win in [6, 24, 72]:
        for col in ["temp", "humidity", "co2", "weight"]:
            df[f"{col}_roll_mean_{win}h"] = (
                g[col].transform(lambda s: s.rolling(win, min_periods=1).mean())
            )
            if win in [6, 24]:
                df[f"{col}_roll_std_{win}h"] = (
                    g[col].transform(lambda s: s.rolling(win, min_periods=2).std())
                ).fillna(0)

    # Domain-informed chronic stress features for absconding.
    df["temp_deviation_from_35"] = (df["temp"] - 35.0).abs()
    df["humidity_deviation_from_optimal"] = np.select(
        [df["humidity"] < 50, df["humidity"] > 65],
        [50 - df["humidity"], df["humidity"] - 65],
        default=0,
    )
    df["co2_high_flag"] = (df["co2"] > 3000).astype(int)
    df["rapid_weight_loss_flag"] = (df["weight_change_6h"] < -0.5).astype(int)
    df["sustained_weight_loss_24h"] = (df["weight_change_24h"] < -1.0).astype(int)

    df["environmental_stress_score"] = (
        np.clip(df["temp_deviation_from_35"] / 5, 0, 1) * 0.30
        + np.clip(df["humidity_deviation_from_optimal"] / 20, 0, 1) * 0.25
        + np.clip((df["co2"] - 1800) / 4000, 0, 1) * 0.25
        + np.clip((-df["weight_change_24h"]) / 3, 0, 1) * 0.20
    )

    if "absconding_label_next_72h" not in df.columns and "absconding_event_label" in df.columns:
        # fallback: construct a 72-hour forward-looking label from event indicator
        df["absconding_label_next_72h"] = (
            g["absconding_event_label"]
            .transform(lambda s: s.shift(-72).rolling(72, min_periods=1).max())
            .fillna(0).astype(int)
        )

    return df.replace([np.inf, -np.inf], np.nan).fillna(0)


def time_based_split(df: pd.DataFrame, test_fraction: float) -> Tuple[np.ndarray, np.ndarray]:
    unique_times = np.array(sorted(df["timestamp"].unique()))
    split_index = int(len(unique_times) * (1 - test_fraction))
    split_time = unique_times[split_index]
    train_mask = df["timestamp"] < split_time
    test_mask = ~train_mask
    return train_mask.values, test_mask.values


def build_model(model_type: str, random_state: int):
    if model_type == "rf":
        return RandomForestClassifier(
            n_estimators=140,
            max_depth=16,
            min_samples_leaf=8,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=random_state,
        )

    # Fast baseline: behaves like time-series logistic regression and is suitable
    # for quick VS Code runs or Colab tests.
    return Pipeline([
        ("scale", StandardScaler()),
        ("clf", SGDClassifier(
            loss="log_loss",
            penalty="elasticnet",
            alpha=0.0003,
            l1_ratio=0.05,
            class_weight="balanced",
            max_iter=2000,
            tol=1e-4,
            random_state=random_state,
        )),
    ])


def predict_proba(model, X: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    decision = model.decision_function(X)
    return 1 / (1 + np.exp(-decision))


def choose_threshold(y_true: np.ndarray, prob: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(y_true, prob)
    if len(thresholds) == 0:
        return 0.5
    beta = 2.0  # prioritize recall because missed absconding is costly
    fbeta = (1 + beta**2) * precision[:-1] * recall[:-1] / (
        beta**2 * precision[:-1] + recall[:-1] + 1e-12
    )
    best = int(np.nanargmax(fbeta))
    return float(thresholds[best])


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
    factors = []
    checks = [
        ("Rapid hive weight decline", -row.get("weight_change_24h", 0), "kg/24h", row.get("weight_change_24h", 0) < -1.0),
        ("CO₂ accumulation", row.get("co2", 0), "ppm", row.get("co2", 0) > 3000),
        ("Temperature instability", row.get("temp_deviation_from_35", 0), "°C from 35", row.get("temp_deviation_from_35", 0) > 1.0),
        ("Humidity deviation", row.get("humidity_deviation_from_optimal", 0), "% outside 50–65", row.get("humidity_deviation_from_optimal", 0) > 5),
        ("Combined environmental stress", row.get("environmental_stress_score", 0), "0–1", row.get("environmental_stress_score", 0) > 0.45),
    ]
    for name, value, unit, active in checks:
        if active:
            factors.append({
                "factor": name,
                "value": round(float(value), 3),
                "unit": unit,
                "interpretation": f"{name} is contributing to elevated absconding risk."
            })
    if not factors:
        factors.append({
            "factor": "No severe single-factor trigger",
            "value": 0,
            "unit": "",
            "interpretation": "Risk is mainly based on combined long-term time-series pattern."
        })
    return factors[:4]


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
    return metrics


def make_per_hive_outputs(df: pd.DataFrame, feature_importance: List[Dict[str, Any]], cfg: AbscondingConfig) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    latest_rows = (
        df.sort_values(["hive_id", "timestamp"])
          .groupby("hive_id", sort=False)
          .tail(1)
          .copy()
    )

    per_hive = []
    alerts = []
    for _, row in latest_rows.iterrows():
        prob = float(row["absconding_risk_probability"])
        arm = float(row["arm"])
        level = risk_level(prob, arm, cfg.medium_threshold, cfg.alert_threshold, cfg.arm_alert_threshold)
        trend = arm_trend_label(arm)
        factors = explanations_for_row(row)

        alert_required = level == "High"
        message = (
            f"WARNING: {row['hive_id']} absconding risk {prob*100:.1f}% "
            f"({trend}). Check queen status, food stores, ventilation, pests, and hive disturbance."
            if alert_required else
            f"{row['hive_id']} absconding risk is {level.lower()} ({prob*100:.1f}%). Continue monitoring."
        )

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
            "key_factors": factors,
        }
        per_hive.append(item)
        if alert_required:
            alerts.append(item)

    per_hive = sorted(per_hive, key=lambda x: x["risk_probability"], reverse=True)
    return per_hive, alerts


def save_plots(df_test: pd.DataFrame, y_test: np.ndarray, prob_test: np.ndarray, metrics: Dict[str, Any], feature_importance: List[Dict[str, Any]], output_dir: Path) -> None:
    plots_dir = output_dir / "plots"

    # Confusion matrix
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

    # Feature importance
    top = feature_importance[:12]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh([x["feature"] for x in reversed(top)], [x["importance"] for x in reversed(top)])
    ax.set_title("Top Absconding Risk Contributing Features")
    ax.set_xlabel("Importance")
    plt.tight_layout()
    plt.savefig(plots_dir / "absconding_feature_importance.png", dpi=150)
    plt.close()

    # Risk probability timeline for a top risky hive in test data
    df_plot = df_test.copy()
    df_plot["actual"] = y_test
    if df_plot["hive_id"].nunique() > 0:
        top_hive = (
            df_plot.groupby("hive_id")["absconding_risk_probability"]
              .max()
              .sort_values(ascending=False)
              .index[0]
        )
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


def model_feature_importance(model, X_test: pd.DataFrame, y_test: np.ndarray, feature_names: List[str]) -> List[Dict[str, Any]]:
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    elif isinstance(model, Pipeline):
        clf = model.named_steps.get("clf")
        if hasattr(clf, "coef_"):
            importances = np.abs(clf.coef_[0])
        else:
            importances = np.zeros(len(feature_names))
    else:
        importances = np.zeros(len(feature_names))

    items = [
        {"feature": f, "importance": round(float(v), 6)}
        for f, v in zip(feature_names, importances)
    ]
    return sorted(items, key=lambda x: x["importance"], reverse=True)


def add_predictions_and_arm(df: pd.DataFrame, probabilities: np.ndarray) -> pd.DataFrame:
    df = df.copy()
    df["absconding_risk_probability"] = np.clip(probabilities, 0, 1)
    g = df.groupby("hive_id", sort=False)

    df["previous_risk"] = g["absconding_risk_probability"].shift(1)
    df["previous_timestamp"] = g["timestamp"].shift(1)
    delta_hours = (df["timestamp"] - df["previous_timestamp"]).dt.total_seconds() / 3600.0
    delta_hours = delta_hours.replace(0, np.nan).fillna(1.0)
    df["arm"] = ((df["absconding_risk_probability"] - df["previous_risk"].fillna(df["absconding_risk_probability"])) / delta_hours)
    df["arm"] = df["arm"].replace([np.inf, -np.inf], 0).fillna(0)
    return df


def train_absconding_module(cfg: AbscondingConfig) -> Dict[str, Any]:
    output_dir = Path(cfg.output_dir)
    ensure_dirs(output_dir)

    raw = load_dataset(Path(cfg.data_path), cfg.max_rows)
    df = engineer_features(add_aliases_and_clean(raw))

    if cfg.target_column not in df.columns:
        raise ValueError(
            f"Target column '{cfg.target_column}' was not found. "
            "The current dataset should include absconding_label_next_72h."
        )

    df[cfg.target_column] = pd.to_numeric(df[cfg.target_column], errors="coerce").fillna(0).astype(int)
    features = [f for f in BASE_FEATURES if f in df.columns]
    X = df[features].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0)
    y = df[cfg.target_column].values.astype(int)

    train_mask, test_mask = time_based_split(df, cfg.test_fraction)
    X_train, X_test = X.loc[train_mask], X.loc[test_mask]
    y_train, y_test = y[train_mask], y[test_mask]
    df_train, df_test = df.loc[train_mask].copy(), df.loc[test_mask].copy()

    if len(np.unique(y_train)) < 2:
        raise ValueError("Training set contains only one class. Use more data or disable max_rows.")

    model = build_model(cfg.model_type, cfg.random_state)
    model.fit(X_train, y_train)

    prob_train = predict_proba(model, X_train)
    threshold = choose_threshold(y_train, prob_train)

    prob_test = predict_proba(model, X_test)
    metrics = compute_metrics(y_test, prob_test, threshold)
    metrics.update({
        "model_type": cfg.model_type,
        "training_records": int(len(X_train)),
        "testing_records": int(len(X_test)),
        "total_records": int(len(df)),
        "total_hives": int(df["hive_id"].nunique()),
        "analysis_start": str(df["timestamp"].min()),
        "analysis_end": str(df["timestamp"].max()),
        "features_used": features,
        "target_column": cfg.target_column,
    })

    # full-dataset predictions for dashboard latest hive state
    full_prob = predict_proba(model, X)
    df_pred = add_predictions_and_arm(df, full_prob)
    df_test_pred = df_pred.loc[test_mask].copy()
    df_test_pred["actual_label"] = y_test

    feature_importance = model_feature_importance(model, X_test, y_test, features)
    per_hive, alerts = make_per_hive_outputs(df_pred, feature_importance, cfg)

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
        },
        "model_metrics": metrics,
        "risk_thresholds": {
            "low": f"< {cfg.medium_threshold}",
            "medium": f"{cfg.medium_threshold} - {cfg.alert_threshold}",
            "high": f">= {cfg.alert_threshold}",
            "arm_escalation": f">= {cfg.arm_alert_threshold}",
        },
        "per_hive_absconding_risk": per_hive,
        "alerts": alerts,
        "feature_importance": feature_importance[:20],
        "plots": {
            "confusion_matrix": "/api/absconding/images/absconding_confusion_matrix.png",
            "feature_importance": "/api/absconding/images/absconding_feature_importance.png",
            "risk_timeline": "/api/absconding/images/absconding_risk_timeline.png",
        },
        "explainability_note": (
            "Key factors are generated from domain-informed stress features: weight decline, "
            "CO2 buildup, temperature instability, humidity deviation, and combined stress score."
        )
    }

    save_plots(df_test_pred, y_test, prob_test, metrics, feature_importance, output_dir)

    # Save artefacts
    model_path = output_dir / "models" / f"absconding_{cfg.model_type}_model.joblib"
    joblib.dump({"model": model, "features": features, "threshold": threshold, "config": asdict(cfg)}, model_path)

    (output_dir / "metrics" / "absconding_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (output_dir / "absconding_dashboard.json").write_text(json.dumps(dashboard, indent=2), encoding="utf-8")

    pred_cols = [
        "timestamp", "hive_id", "absconding_risk_probability", "arm",
        "temp", "humidity", "co2", "weight",
        "weight_change_24h", "co2_change_24h", cfg.target_column
    ]
    df_pred[pred_cols].tail(5000).to_csv(output_dir / "predictions" / "absconding_predictions_tail.csv", index=False)
    pd.DataFrame(per_hive).to_csv(output_dir / "predictions" / "latest_absconding_risk_per_hive.csv", index=False)
    pd.DataFrame(feature_importance).to_csv(output_dir / "metrics" / "absconding_feature_importance.csv", index=False)

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
    per_hive, alerts = make_per_hive_outputs(df_pred, [], cfg)
    return {"per_hive_absconding_risk": per_hive, "alerts": alerts}


def parse_args() -> AbscondingConfig:
    parser = argparse.ArgumentParser(description="Train and generate absconding prediction outputs.")
    parser.add_argument("--data", default="backend/data/hive_data_with_features.csv")
    parser.add_argument("--output", default="backend/outputs/absconding")
    parser.add_argument("--model", choices=["fast", "rf"], default="fast")
    parser.add_argument("--target", default="absconding_label_next_72h")
    parser.add_argument("--max-rows", type=int, default=None)
    args = parser.parse_args()
    return AbscondingConfig(
        data_path=args.data,
        output_dir=args.output,
        model_type=args.model,
        target_column=args.target,
        max_rows=args.max_rows,
    )


if __name__ == "__main__":
    config = parse_args()
    result = train_absconding_module(config)
    print("\n✅ Absconding module completed.")
    print(f"   Output: {config.output_dir}/absconding_dashboard.json")
    print(f"   High-risk hives: {result['summary']['high_risk_hives']}")
    print(f"   Latest alerts: {result['summary']['latest_alerts']}")
    print(f"   F1: {result['model_metrics']['f1_score']} | Recall: {result['model_metrics']['recall']} | PR-AUC: {result['model_metrics']['pr_auc']}")
