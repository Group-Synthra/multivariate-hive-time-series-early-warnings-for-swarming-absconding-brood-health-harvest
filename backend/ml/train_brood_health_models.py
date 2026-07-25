# Train and compare leakage-aware brood-health forecasting models.

from __future__ import annotations

import argparse
import gc
import json
import math
import time
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import (
    ExtraTreesRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    recall_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

try:
    from xgboost import XGBRegressor
except ImportError:  
    XGBRegressor = None

try:
    from .features import (
        DEFAULT_TARGET,
        FEATURE_SCHEMA_VERSION,
        SENSORS,
        build_supervised_dataset,
    )
except ImportError:  
    from features import (
        DEFAULT_TARGET,
        FEATURE_SCHEMA_VERSION,
        SENSORS,
        build_supervised_dataset,
    )

try:
    from brood_health.analyzer import (
        CRITICAL_UPPER_BOUND,
        GOOD_UPPER_BOUND,
        HEALTH_LEVEL_DEFINITIONS,
        POOR_UPPER_BOUND,
    )
except ImportError: 
    from ..brood_health.analyzer import (
        CRITICAL_UPPER_BOUND,
        GOOD_UPPER_BOUND,
        HEALTH_LEVEL_DEFINITIONS,
        POOR_UPPER_BOUND,
    )

ProgressCallback = Callable[[str, dict[str, Any]], None]

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BACKEND_DIR / "data" / "hive_data_with_features.csv"
MODEL_DIR = BACKEND_DIR / "models"
OUTPUT_DIR = BACKEND_DIR / "brood_health" / "outputs"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _sensor_reference(raw: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Capture training-sensor ranges for live domain-shift warnings."""
    aliases = {
        "internal_temperature_c": "temp",
        "internal_humidity_pct": "humidity",
        "co2_ppm": "co2",
        "hive_weight_kg": "weight",
        "external_temperature_c": "external_temp",
        "external_humidity_pct": "external_humidity",
    }
    frame = raw.rename(columns=aliases)
    reference: dict[str, dict[str, float]] = {}
    for sensor in SENSORS:
        if sensor not in frame.columns:
            continue
        values = pd.to_numeric(frame[sensor], errors="coerce").dropna()
        if values.empty:
            continue
        reference[sensor] = {
            "minimum": float(values.min()),
            "p01": float(values.quantile(0.01)),
            "p05": float(values.quantile(0.05)),
            "median": float(values.median()),
            "p95": float(values.quantile(0.95)),
            "p99": float(values.quantile(0.99)),
            "maximum": float(values.max()),
        }
    return reference


def _notify(callback: ProgressCallback | None, event: str, **data: Any) -> None:
    if callback:
        callback(event, data)


def _health_level(values: np.ndarray) -> np.ndarray:
    return np.select(
        [
            values >= GOOD_UPPER_BOUND,
            values >= POOR_UPPER_BOUND,
            values >= CRITICAL_UPPER_BOUND,
        ],
        ["Excellent", "Good", "Poor"],
        default="Critical",
    )


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    clipped = np.clip(np.asarray(y_pred, dtype=float), 0.0, 100.0)
    true = np.asarray(y_true, dtype=float)
    critical_true = true < CRITICAL_UPPER_BOUND
    critical_pred = clipped < CRITICAL_UPPER_BOUND
    critical_recall = (
        recall_score(critical_true, critical_pred, zero_division=0)
        if critical_true.any()
        else float("nan")
    )
    return {
        "mae": float(mean_absolute_error(true, clipped)),
        "rmse": float(math.sqrt(mean_squared_error(true, clipped))),
        "r2": float(r2_score(true, clipped)),
        "level_accuracy": float(np.mean(_health_level(true) == _health_level(clipped))),
        "critical_recall": float(critical_recall),
    }


def _build_models(*, fast_mode: bool = False) -> dict[str, Any]:
    trees = 15 if fast_mode else 120
    models: dict[str, Any] = {
        "Dummy Median": DummyRegressor(strategy="median"),
        "Ridge Regression": make_pipeline(
            StandardScaler(),
            Ridge(alpha=10.0),
        ),
        **({
            "XGBoost": XGBRegressor(
                n_estimators=50 if fast_mode else 350,
                learning_rate=0.05,
                max_depth=8,
                min_child_weight=3,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.05,
                reg_lambda=1.0,
                objective="reg:squarederror",
                n_jobs=-1,
                random_state=42,
            )
        } if XGBRegressor is not None else {}),
        "Random Forest": RandomForestRegressor(
            n_estimators=trees,
            max_depth=18,
            min_samples_leaf=3,
            max_features=0.75,
            max_samples=0.60,
            n_jobs=-1,
            random_state=42,
        ),
        "Extra Trees": ExtraTreesRegressor(
            n_estimators=15 if fast_mode else 90,
            max_depth=16,
            min_samples_leaf=3,
            max_features=0.55,
            bootstrap=True,
            max_samples=0.60,
            n_jobs=-1,
            random_state=42,
        ),
        "Histogram Gradient Boosting": HistGradientBoostingRegressor(
            learning_rate=0.07,
            max_iter=60 if fast_mode else 250,
            max_leaf_nodes=31,
            l2_regularization=1.0,
            early_stopping=True,
            random_state=42,
        ),
    }
    return models


def _final_temporal_split(
    metadata: pd.DataFrame,
    *,
    test_fraction: float = 0.20,
) -> tuple[np.ndarray, np.ndarray, pd.Timestamp]:
    unique_times = np.sort(metadata["timestamp"].unique())
    if len(unique_times) < 10:
        raise ValueError("Not enough unique timestamps for a temporal holdout")
    split_position = min(
        max(int(len(unique_times) * (1.0 - test_fraction)), 1),
        len(unique_times) - 1,
    )
    test_start = pd.Timestamp(unique_times[split_position])

    # Purge training rows whose future target lands in the test period.
    train_mask = metadata["target_timestamp"] < test_start
    test_mask = metadata["timestamp"] >= test_start
    return train_mask.to_numpy(), test_mask.to_numpy(), test_start


def _temporal_cv_folds(
    metadata: pd.DataFrame,
    *,
    n_splits: int = 3,
) -> list[tuple[np.ndarray, np.ndarray]]:
    unique_times = np.sort(metadata["timestamp"].unique())
    if len(unique_times) < (n_splits + 2) * 24:
        return []

    validation_size = max(24, len(unique_times) // (n_splits + 2))
    folds: list[tuple[np.ndarray, np.ndarray]] = []
    for fold in range(n_splits):
        validation_end = len(unique_times) - (n_splits - fold - 1) * validation_size
        validation_start = validation_end - validation_size
        if validation_start <= 0:
            continue
        val_start_time = pd.Timestamp(unique_times[validation_start])
        val_end_time = pd.Timestamp(unique_times[validation_end - 1])
        train_mask = metadata["target_timestamp"] < val_start_time
        val_mask = metadata["timestamp"].between(val_start_time, val_end_time)
        train_idx = np.flatnonzero(train_mask.to_numpy())
        val_idx = np.flatnonzero(val_mask.to_numpy())
        if len(train_idx) and len(val_idx):
            folds.append((train_idx, val_idx))
    return folds


def _downsample_indices(indices: np.ndarray, maximum: int) -> np.ndarray:
    if len(indices) <= maximum:
        return indices
    positions = np.linspace(0, len(indices) - 1, maximum, dtype=int)
    return indices[positions]


def _serialise_metric_dict(values: dict[str, Any]) -> dict[str, Any]:
    serialised: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, (np.floating, float)):
            serialised[key] = None if not np.isfinite(value) else round(float(value), 5)
        elif isinstance(value, (np.integer, int)):
            serialised[key] = int(value)
        else:
            serialised[key] = value
    return serialised


def _run_model_worker(
    *,
    model_name: str,
    shared_data_path: Path,
    output_dir: Path,
    fast_mode: bool,
) -> None:
    """Train one candidate in an isolated process.

    Isolation avoids OpenMP/thread-pool conflicts between XGBoost and scikit-learn
    tree ensembles when all candidates are trained from a long-running Flask process.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    data = joblib.load(shared_data_path)
    models = _build_models(fast_mode=fast_mode)
    if model_name not in models:
        raise ValueError(f"Unknown model: {model_name}")

    estimator = models[model_name]
    X_train = data["X_train"]
    y_train = data["y_train"]
    X_test = data["X_test"]
    y_test = data["y_test"]
    cv_folds = data["cv_folds"]

    started = time.perf_counter()
    model = clone(estimator)
    model.fit(X_train, y_train)
    prediction = np.clip(model.predict(X_test), 0.0, 100.0)
    test_metrics = _metrics(y_test.to_numpy(), prediction)

    fold_maes: list[float] = []
    selected_folds = cv_folds[-1:] if fast_mode else cv_folds
    for local_train, local_val in selected_folds:
        local_train = _downsample_indices(
            local_train, 50000 if not fast_mode else 5000
        )
        local_val = _downsample_indices(
            local_val, 15000 if not fast_mode else 2000
        )
        cv_model = clone(estimator)
        cv_model.fit(X_train.iloc[local_train], y_train.iloc[local_train])
        cv_prediction = np.clip(
            cv_model.predict(X_train.iloc[local_val]), 0.0, 100.0
        )
        fold_maes.append(
            float(mean_absolute_error(y_train.iloc[local_val], cv_prediction))
        )

    model_result = _serialise_metric_dict(
        {
            "test_mae": test_metrics["mae"],
            "test_rmse": test_metrics["rmse"],
            "test_r2": test_metrics["r2"],
            "health_level_accuracy": test_metrics["level_accuracy"],
            "critical_recall": test_metrics["critical_recall"],
            "cv_mae_mean": float(np.mean(fold_maes)) if fold_maes else float("nan"),
            "cv_mae_std": float(np.std(fold_maes)) if fold_maes else float("nan"),
            "fit_seconds": time.perf_counter() - started,
            "status": "ok",
        }
    )
    joblib.dump(model, output_dir / "model.joblib")
    np.save(output_dir / "prediction.npy", prediction)
    (output_dir / "result.json").write_text(
        json.dumps(model_result, indent=2), encoding="utf-8"
    )


def run_training(
    *,
    progress_callback: ProgressCallback | None = None,
    data_path: Path = DATA_PATH,
    horizon_hours: int = 6,
    fast_mode: bool = False,
    models_to_run: Iterable[str] | None = None,
) -> dict[str, Any]:
    _notify(progress_callback, "start", message="Loading dataset", progress=2)
    if not data_path.exists():
        raise FileNotFoundError(f"CSV not found: {data_path}")

    raw = pd.read_csv(data_path)
    training_sensor_reference = _sensor_reference(raw)
    _notify(
        progress_callback,
        "data_ready",
        message="Building causal lag and rolling features",
        progress=8,
    )
    X, y, metadata, feature_columns = build_supervised_dataset(
        raw,
        target_column=DEFAULT_TARGET,
        horizon_hours=horizon_hours,
    )

    if fast_mode and len(X) > 70000:
        keep = np.linspace(0, len(X) - 1, 70000, dtype=int)
        X = X.iloc[keep].reset_index(drop=True)
        y = y.iloc[keep].reset_index(drop=True)
        metadata = metadata.iloc[keep].reset_index(drop=True)

    train_mask, test_mask, test_start = _final_temporal_split(metadata)
    train_indices = np.flatnonzero(train_mask)
    test_indices = np.flatnonzero(test_mask)
    if len(train_indices) == 0 or len(test_indices) == 0:
        raise ValueError("Temporal split produced an empty train or test set")

    X_train, y_train = X.iloc[train_indices].reset_index(drop=True), y.iloc[train_indices].reset_index(drop=True)
    X_test, y_test = X.iloc[test_indices].reset_index(drop=True), y.iloc[test_indices].reset_index(drop=True)
    train_metadata = metadata.iloc[train_indices].reset_index(drop=True)
    cv_folds = _temporal_cv_folds(train_metadata, n_splits=3)

    _notify(
        progress_callback,
        "split_done",
        message=f"Temporal split complete; test begins {test_start.isoformat()}",
        progress=15,
    )

    candidate_names = list(_build_models(fast_mode=fast_mode).keys())
    if models_to_run:
        requested = set(models_to_run)
        candidate_names = [name for name in candidate_names if name in requested]
    if not candidate_names:
        raise ValueError("No candidate models were selected")

    results: dict[str, dict[str, Any]] = {}
    predictions: dict[str, np.ndarray] = {}
    best_name: str | None = None
    minimum_critical_recall = 0.70
    model_paths: dict[str, Path] = {}
    best_candidate_path = MODEL_DIR / ".best_brood_candidate.joblib"
    best_candidate_path.unlink(missing_ok=True)

    with tempfile.TemporaryDirectory(prefix="brood_training_", dir=MODEL_DIR) as temp_name:
        temp_dir = Path(temp_name)
        shared_data_path = temp_dir / "shared_training_data.joblib"
        joblib.dump(
            {
                "X_train": X_train,
                "y_train": y_train,
                "X_test": X_test,
                "y_test": y_test,
                "cv_folds": cv_folds,
            },
            shared_data_path,
            compress=0,
        )
        train_sample_count = len(X_train)
        test_sample_count = len(X_test)
        del raw, X, y, X_train, y_train, X_test, y_test, train_metadata
        gc.collect()

        for model_index, name in enumerate(candidate_names):
            base_progress = 18 + int(65 * model_index / max(len(candidate_names), 1))
            _notify(
                progress_callback,
                "model_start",
                model=name,
                message=f"Training {name}",
                progress=base_progress,
            )
            worker_dir = temp_dir / f"model_{model_index}"
            command = [
                sys.executable,
                "-m",
                "ml.train_brood_health_models",
                "--worker-model",
                name,
                "--worker-data",
                str(shared_data_path),
                "--worker-output",
                str(worker_dir),
            ]
            if fast_mode:
                command.append("--fast")

            try:
                worker_dir.mkdir(parents=True, exist_ok=True)
                log_path = worker_dir / "worker.log"
                with log_path.open("w", encoding="utf-8") as worker_log:
                    completed = subprocess.run(
                        command,
                        cwd=BACKEND_DIR,
                        stdout=worker_log,
                        stderr=subprocess.STDOUT,
                        text=True,
                        check=False,
                    )
                result_path = worker_dir / "result.json"
                if completed.returncode != 0 or not result_path.exists():
                    detail = log_path.read_text(encoding="utf-8", errors="replace").strip()
                    raise RuntimeError((detail or "Worker failed")[-3000:])

                model_result = json.loads(result_path.read_text(encoding="utf-8"))
                prediction = np.load(worker_dir / "prediction.npy")
                results[name] = model_result
                predictions[name] = prediction

                if name != "Dummy Median":
                    model_paths[name] = worker_dir / "model.joblib"

                message = (
                    f"{name}: MAE {model_result['test_mae']:.3f}, "
                    f"RMSE {model_result['test_rmse']:.3f}"
                )
            except Exception as exc:
                results[name] = {"status": "failed", "error": str(exc)}
                message = f"{name} failed: {exc}"

            _notify(
                progress_callback,
                "model_end",
                model=name,
                message=message,
                progress=base_progress + max(1, int(65 / max(len(candidate_names), 1))),
            )

        successful_names = [
            name
            for name, values in results.items()
            if name != "Dummy Median" and values.get("status") == "ok"
        ]
        if not successful_names:
            raise RuntimeError("All non-baseline candidate models failed")
        recall_eligible = [
            name
            for name in successful_names
            if (results[name].get("critical_recall") or 0.0) >= minimum_critical_recall
        ]
        selection_pool = recall_eligible or successful_names
        best_name = min(
            selection_pool,
            key=lambda name: (
                float(results[name]["test_mae"]),
                float(results[name]["test_rmse"]),
            ),
        )
        shutil.copy2(model_paths[best_name], best_candidate_path)

        evaluation_data = joblib.load(shared_data_path)
        X_test = evaluation_data["X_test"]
        y_test = evaluation_data["y_test"]

    if best_name is None or not best_candidate_path.exists():
        raise RuntimeError("Model selection failed")
    best_model = joblib.load(best_candidate_path)

    _notify(
        progress_callback,
        "saving",
        message=f"Saving {best_name} and evaluation artefacts",
        progress=90,
    )

    bundle = {
        "model": best_model,
        "model_name": best_name,
        "feature_columns": feature_columns,
        "horizon_hours": horizon_hours,
        "target_column": DEFAULT_TARGET,
        "target_kind": "provisional_proxy",
        "target_warning": (
            "The current target is a dataset-provided proxy score, not an independently "
            "observed brood-health measurement."
        ),
        "health_level_definitions": list(HEALTH_LEVEL_DEFINITIONS),
        "trained_at_utc": pd.Timestamp.utcnow().isoformat(),
        "training_sensor_reference": training_sensor_reference,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "prediction_inputs": list(SENSORS),
        "battery_voltage_usage": "device_quality_only_not_model_input",
    }
    joblib.dump(bundle, MODEL_DIR / "best_brood_model.joblib")
    joblib.dump(feature_columns, MODEL_DIR / "brood_feature_columns.joblib")
    best_candidate_path.unlink(missing_ok=True)

    test_output = metadata.iloc[test_indices].copy()
    test_output["actual_future_score"] = y_test.to_numpy()
    for name, prediction in predictions.items():
        test_output[f"prediction__{name}"] = prediction
    test_output.to_csv(OUTPUT_DIR / "brood_model_test_predictions.csv", index=False)

    try:
        if hasattr(best_model, "feature_importances_"):
            importance_frame = pd.DataFrame(
                {
                    "feature": feature_columns,
                    "importance_mean": best_model.feature_importances_,
                    "importance_std": np.nan,
                }
            ).sort_values("importance_mean", ascending=False)
        else:
            importance_sample_size = min(1000, len(X_test))
            importance_indices = np.linspace(
                0, len(X_test) - 1, importance_sample_size, dtype=int
            )
            importance = permutation_importance(
                best_model,
                X_test.iloc[importance_indices],
                y_test.iloc[importance_indices],
                scoring="neg_mean_absolute_error",
                n_repeats=1,
                random_state=42,
                n_jobs=1,
            )
            importance_frame = pd.DataFrame(
                {
                    "feature": feature_columns,
                    "importance_mean": importance.importances_mean,
                    "importance_std": importance.importances_std,
                }
            ).sort_values("importance_mean", ascending=False)
        importance_frame.to_csv(OUTPUT_DIR / "brood_feature_importance.csv", index=False)
    except Exception as exc:
        importance_error = str(exc)
    else:
        importance_error = None

    summary = {
        "best_model": best_name,
        "selection_metric": (
            "minimum critical recall of 0.70, then lowest final temporal-holdout "
            "MAE; RMSE used as tie-breaker. Falls back to MAE if no model reaches "
            "the recall threshold."
        ),
        "minimum_critical_recall": minimum_critical_recall,
        "metrics": results[best_name],
        "all_models": results,
        "feature_columns": feature_columns,
        "feature_count": len(feature_columns),
        "horizon_hours": horizon_hours,
        "target_column": DEFAULT_TARGET,
        "target_kind": "provisional_proxy",
        "target_warning": bundle["target_warning"],
        "health_level_definitions": list(HEALTH_LEVEL_DEFINITIONS),
        "training_sensor_reference": training_sensor_reference,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "prediction_inputs": list(SENSORS),
        "battery_voltage_usage": "device_quality_only_not_model_input",
        "train_samples": int(train_sample_count),
        "test_samples": int(test_sample_count),
        "train_hives": int(metadata.iloc[train_indices]["hive"].nunique()),
        "test_hives": int(metadata.iloc[test_indices]["hive"].nunique()),
        "test_start": test_start.isoformat(),
        "data_start": pd.Timestamp(metadata["timestamp"].min()).isoformat(),
        "data_end": pd.Timestamp(metadata["timestamp"].max()).isoformat(),
        "cv_strategy": "expanding temporal folds with target-time purging",
        "split_strategy": "final chronological holdout with target-time purging",
        "feature_importance_error": importance_error,
    }
    (MODEL_DIR / "training_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    _notify(
        progress_callback,
        "complete",
        message=f"Training complete. Best model: {best_name}",
        progress=100,
        result=summary,
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    parser.add_argument("--horizon-hours", type=int, default=6)
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--worker-model")
    parser.add_argument("--worker-data", type=Path)
    parser.add_argument("--worker-output", type=Path)
    args = parser.parse_args()

    if args.worker_model:
        if args.worker_data is None or args.worker_output is None:
            parser.error("worker mode requires --worker-data and --worker-output")
        _run_model_worker(
            model_name=args.worker_model,
            shared_data_path=args.worker_data,
            output_dir=args.worker_output,
            fast_mode=args.fast,
        )
        return

    summary = run_training(
        data_path=args.data,
        horizon_hours=args.horizon_hours,
        fast_mode=args.fast,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()