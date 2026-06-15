"""
Optional Colab/GPU LSTM comparison for Module 03 — Absconding Behaviour Prediction.

This script trains an actual sequence model on ordered hive windows and writes:
    backend/outputs/absconding/metrics/lstm_absconding_metrics.json

After running this, run the normal backend pipeline again:
    python backend/scripts/run_absconding.py --model rf --compare-models
The React dashboard will merge LSTM into the model comparison table.

Example in Google Colab / VS Code Colab extension:
    !pip install tensorflow pandas numpy scikit-learn matplotlib joblib
    !python lstm_absconding.py --data hive_data_with_features.csv --output absconding_outputs --epochs 30 --sequence-length 72
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, average_precision_score, confusion_matrix, f1_score,
    mean_absolute_error, mean_squared_error, precision_recall_curve,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight

try:
    import tensorflow as tf
    from tensorflow import keras
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "TensorFlow is required for LSTM. Run this in Google Colab/GPU or install tensorflow.\n"
        f"Original error: {exc}"
    )

# Allow importing pipeline from project root or from copied Colab files.
THIS_FILE = Path(__file__).resolve()
for candidate in [THIS_FILE.parents[3], THIS_FILE.parents[2], Path.cwd()]:
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

try:
    from backend.ml.absconding.absconding_pipeline import (
        BASE_FEATURES, add_aliases_and_clean, engineer_features, load_dataset, time_based_split,
        choose_threshold,
    )
except Exception:
    # If the two files are uploaded flat into Colab, import by local name.
    from absconding_pipeline import (  # type: ignore
        BASE_FEATURES, add_aliases_and_clean, engineer_features, load_dataset, time_based_split,
        choose_threshold,
    )


def compute_metrics(y_true: np.ndarray, prob: np.ndarray, threshold: float) -> Dict[str, Any]:
    pred = (prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    metrics = {
        "model_key": "lstm",
        "model_name": "LSTM + Time-Series Sequence",
        "model_family": "Deep learning sequence model",
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


def make_sequences(df: pd.DataFrame, features: List[str], target: str, sequence_length: int, stride: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    X_list, y_list, t_list = [], [], []
    for _, sub in df.sort_values(["hive_id", "timestamp"]).groupby("hive_id", sort=False):
        values = sub[features].values.astype("float32")
        labels = sub[target].values.astype("int32")
        times = sub["timestamp"].values
        if len(sub) < sequence_length:
            continue
        for end in range(sequence_length, len(sub), stride):
            start = end - sequence_length
            X_list.append(values[start:end])
            y_list.append(labels[end - 1])
            t_list.append(times[end - 1])
    return np.asarray(X_list, dtype="float32"), np.asarray(y_list, dtype="int32"), np.asarray(t_list)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train LSTM sequence model for absconding comparison.")
    parser.add_argument("--data", default="backend/data/hive_data_with_features.csv")
    parser.add_argument("--output", default="backend/outputs/absconding")
    parser.add_argument("--target", default="absconding_label_next_72h")
    parser.add_argument("--sequence-length", type=int, default=72, help="Hours/readings per input sequence. Use 72 for 3 days hourly data.")
    parser.add_argument("--stride", type=int, default=3, help="Stride between sequence windows. Larger is faster.")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--max-rows", type=int, default=None)
    args = parser.parse_args()

    output_dir = Path(args.output)
    for sub in ["models", "metrics", "plots"]:
        (output_dir / sub).mkdir(parents=True, exist_ok=True)

    raw = load_dataset(Path(args.data), args.max_rows)
    df = engineer_features(add_aliases_and_clean(raw))
    if args.target not in df.columns:
        raise ValueError(f"Target column not found: {args.target}")
    df[args.target] = pd.to_numeric(df[args.target], errors="coerce").fillna(0).astype(int)
    features = [f for f in BASE_FEATURES if f in df.columns]

    # Scale features before sequence creation.
    train_mask, test_mask = time_based_split(df, 0.20)
    scaler = StandardScaler()
    df_scaled = df.copy()
    df_scaled.loc[train_mask, features] = scaler.fit_transform(df.loc[train_mask, features].astype(float))
    df_scaled.loc[test_mask, features] = scaler.transform(df.loc[test_mask, features].astype(float))

    X_seq, y_seq, t_seq = make_sequences(df_scaled, features, args.target, args.sequence_length, args.stride)
    if len(X_seq) == 0:
        raise ValueError("No sequences created. Reduce --sequence-length or check dataset.")
    split_time = np.array(sorted(df["timestamp"].unique()))[int(len(df["timestamp"].unique()) * 0.80)]
    train_seq_mask = pd.to_datetime(t_seq) < pd.to_datetime(split_time)
    X_train, y_train = X_seq[train_seq_mask], y_seq[train_seq_mask]
    X_test, y_test = X_seq[~train_seq_mask], y_seq[~train_seq_mask]

    if len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2:
        raise ValueError("LSTM train/test split contains one class only. Use more data or change stride/max_rows.")

    class_values = np.unique(y_train)
    weights = compute_class_weight(class_weight="balanced", classes=class_values, y=y_train)
    class_weight = {int(c): float(w) for c, w in zip(class_values, weights)}

    tf.random.set_seed(42)
    model = keras.Sequential([
        keras.layers.Input(shape=(args.sequence_length, len(features))),
        keras.layers.Masking(mask_value=0.0),
        keras.layers.LSTM(128, return_sequences=True),
        keras.layers.Dropout(0.30),
        keras.layers.LSTM(64),
        keras.layers.Dropout(0.25),
        keras.layers.Dense(32, activation="relu"),
        keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss="binary_crossentropy",
        metrics=[keras.metrics.Precision(name="precision"), keras.metrics.Recall(name="recall"), keras.metrics.AUC(name="auc")],
    )
    callbacks = [
        keras.callbacks.EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True),
        keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, min_lr=1e-5),
    ]
    history = model.fit(
        X_train, y_train,
        validation_split=0.15,
        epochs=args.epochs,
        batch_size=args.batch_size,
        class_weight=class_weight,
        callbacks=callbacks,
        verbose=1,
    )

    prob_train = model.predict(X_train, batch_size=args.batch_size).ravel()
    threshold = choose_threshold(y_train, prob_train)
    prob_test = model.predict(X_test, batch_size=args.batch_size).ravel()
    metrics = compute_metrics(y_test, prob_test, threshold)
    metrics.update({
        "sequence_length": args.sequence_length,
        "stride": args.stride,
        "epochs_requested": args.epochs,
        "epochs_completed": len(history.history.get("loss", [])),
        "training_sequences": int(len(X_train)),
        "testing_sequences": int(len(X_test)),
        "features_used": features,
        "note": "Real LSTM sequence metrics generated from ordered hive windows. Merge into dashboard by re-running run_absconding.py.",
    })

    model.save(output_dir / "models" / "absconding_lstm_sequence_model.keras")
    (output_dir / "metrics" / "lstm_absconding_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("\n✅ LSTM absconding comparison completed.")
    print(f"   Metrics: {output_dir / 'metrics' / 'lstm_absconding_metrics.json'}")
    print(f"   Recall: {metrics['recall']} | F1: {metrics['f1_score']} | PR-AUC: {metrics['pr_auc']} | Defence score: {metrics['defence_score']}")


if __name__ == "__main__":
    main()
