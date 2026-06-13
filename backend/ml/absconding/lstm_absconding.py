
"""
Optional LSTM implementation for Absconding Prediction.

This file is provided for Google Colab/GPU use. It is not required for the backend
to run, but it satisfies the research requirement of comparing Time Series Regression
/ baseline models with LSTM sequence learning.

Run in Colab or a GPU machine:
    python backend/ml/absconding/lstm_absconding.py --data backend/data/hive_data_with_features.csv

Outputs:
    backend/outputs/absconding/lstm_absconding_model.keras
    backend/outputs/absconding/metrics/lstm_metrics.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight

import tensorflow as tf
from tensorflow.keras import layers, models, callbacks

from absconding_pipeline import add_aliases_and_clean, engineer_features, load_dataset, BASE_FEATURES


def make_sequences(df, features, target, sequence_length=72, stride=6):
    X, y, meta = [], [], []
    for hive, sub in df.groupby("hive_id", sort=False):
        sub = sub.sort_values("timestamp").reset_index(drop=True)
        values = sub[features].values.astype("float32")
        labels = sub[target].values.astype("int32")
        times = sub["timestamp"].astype(str).values
        for end in range(sequence_length, len(sub), stride):
            start = end - sequence_length
            X.append(values[start:end])
            y.append(labels[end])
            meta.append((hive, times[end]))
    return np.asarray(X), np.asarray(y), meta


def main(args):
    out = Path(args.output)
    (out / "metrics").mkdir(parents=True, exist_ok=True)

    df = engineer_features(add_aliases_and_clean(load_dataset(Path(args.data), args.max_rows)))
    target = "absconding_label_next_72h"
    features = [f for f in BASE_FEATURES if f in df.columns]

    # Time-based split before scaling and sequencing
    times = np.array(sorted(df["timestamp"].unique()))
    split_time = times[int(len(times) * 0.8)]
    train_df = df[df["timestamp"] < split_time].copy()
    test_df = df[df["timestamp"] >= split_time].copy()

    scaler = StandardScaler()
    train_df[features] = scaler.fit_transform(train_df[features])
    test_df[features] = scaler.transform(test_df[features])

    X_train, y_train, _ = make_sequences(train_df, features, target, args.sequence_length, args.stride)
    X_test, y_test, _ = make_sequences(test_df, features, target, args.sequence_length, args.stride)

    classes = np.array([0, 1])
    weights = compute_class_weight("balanced", classes=classes, y=y_train)
    class_weight = {int(c): float(w) for c, w in zip(classes, weights)}

    model = models.Sequential([
        layers.Input(shape=(X_train.shape[1], X_train.shape[2])),
        layers.Masking(mask_value=0.0),
        layers.LSTM(128, return_sequences=True),
        layers.Dropout(0.30),
        layers.LSTM(64),
        layers.Dropout(0.20),
        layers.Dense(32, activation="relu"),
        layers.Dense(1, activation="sigmoid"),
    ])

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss="binary_crossentropy",
        metrics=[tf.keras.metrics.AUC(name="auc"), tf.keras.metrics.Precision(name="precision"), tf.keras.metrics.Recall(name="recall")],
    )

    es = callbacks.EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)
    history = model.fit(
        X_train, y_train,
        validation_split=0.15,
        epochs=args.epochs,
        batch_size=args.batch_size,
        class_weight=class_weight,
        callbacks=[es],
        verbose=1,
    )

    prob = model.predict(X_test).ravel()
    pred = (prob >= 0.5).astype(int)

    metrics = {
        "model": "LSTM",
        "sequence_length": args.sequence_length,
        "stride": args.stride,
        "accuracy": float(accuracy_score(y_test, pred)),
        "precision": float(precision_score(y_test, pred, zero_division=0)),
        "recall": float(recall_score(y_test, pred, zero_division=0)),
        "f1_score": float(f1_score(y_test, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, prob)) if len(np.unique(y_test)) > 1 else None,
        "pr_auc": float(average_precision_score(y_test, prob)) if len(np.unique(y_test)) > 1 else None,
        "confusion_matrix": confusion_matrix(y_test, pred).tolist(),
    }

    model.save(out / "models" / "lstm_absconding_model.keras")
    (out / "metrics" / "lstm_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="backend/data/hive_data_with_features.csv")
    p.add_argument("--output", default="backend/outputs/absconding")
    p.add_argument("--sequence-length", type=int, default=72)
    p.add_argument("--stride", type=int, default=6)
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--batch-size", type=int, default=128)
    p.add_argument("--max-rows", type=int, default=None)
    main(p.parse_args())
