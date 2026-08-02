"""
Step 3 - Harvest Readiness Model Comparison

Models:
1. Logistic Regression
2. Random Forest
3. XGBoost
4. LightGBM

Target:
harvest_readiness_label

Classes:
0 = Not Ready
1 = Approaching
2 = Ready
"""

from pathlib import Path
import argparse
import json
import joblib

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
)

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

from xgboost import XGBClassifier
from lightgbm import LGBMClassifier


BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = BASE_DIR / "data" / "harvest_dataset_labeled.csv"

MODEL_DIR = BASE_DIR / "models"
OUTPUT_DIR = BASE_DIR / "outputs" / "harvest"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BEST_MODEL_FILE = MODEL_DIR / "best_harvest_classifier.joblib"
FEATURE_COLUMNS_FILE = MODEL_DIR / "harvest_feature_columns.joblib"

MODEL_RESULTS_FILE = OUTPUT_DIR / "classification_model_comparison.json"
MODEL_RESULTS_CSV = OUTPUT_DIR / "classification_model_comparison.csv"
CLASSIFICATION_REPORT_FILE = OUTPUT_DIR / "classification_report.json"
CONFUSION_MATRIX_FILE = OUTPUT_DIR / "classification_confusion_matrix.png"
MODEL_COMPARISON_PLOT = OUTPUT_DIR / "classification_model_comparison.png"


CLASS_NAMES = {
    0: "Not Ready",
    1: "Approaching",
    2: "Ready"
}


def load_dataset(sample_size=None):
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}\n"
            "Run Step 1 and Step 2 first."
        )

    data = pd.read_csv(INPUT_FILE)

    print("Dataset loaded successfully.")
    print("Original shape:", data.shape)

    if sample_size is not None and sample_size < len(data):
        data = data.sample(
            n=sample_size,
            random_state=42
        ).reset_index(drop=True)

        print(f"Using sample size: {sample_size}")
        print("Sampled shape:", data.shape)

    print("\nAvailable columns:")
    print(data.columns.tolist())

    return data


def prepare_features_and_target(data):
    target_column = "harvest_readiness_label"

    if target_column not in data.columns:
        raise ValueError(
            f"Target column not found: {target_column}"
        )

    remove_columns = [
        "timestamp",
        "hive_id",
        "hive",

        # target/output columns
        "harvest_readiness_label",
        "harvest_readiness_status",
    ]

    remove_columns = [
        column
        for column in remove_columns
        if column in data.columns
    ]

    X = data.drop(columns=remove_columns)
    y = data[target_column]

    # Use only numeric columns
    X = X.select_dtypes(
        include=[
            "int64",
            "float64",
            "int32",
            "float32",
            "bool"
        ]
    )

    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(0)

    print("\nSelected feature columns:")
    print(X.columns.tolist())

    print("\nTarget distribution:")
    print(y.value_counts().sort_index())

    print("\nTarget distribution percentage:")
    print((y.value_counts(normalize=True).sort_index() * 100).round(2))

    return X, y


def build_models():
    models = {
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=42
            ))
        ]),

        "Random Forest": RandomForestClassifier(
            n_estimators=200,
            random_state=42,
            class_weight="balanced",
            n_jobs=-1
        ),

        "XGBoost": XGBClassifier(
            n_estimators=250,
            learning_rate=0.05,
            max_depth=5,
            objective="multi:softprob",
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=-1
        ),

        "LightGBM": LGBMClassifier(
            n_estimators=250,
            learning_rate=0.05,
            random_state=42,
            class_weight="balanced"
        )
    }

    return models


def evaluate_models(models, X_train, X_test, y_train, y_test):
    results = []
    trained_models = {}

    for model_name, model in models.items():
        print(f"\nTraining {model_name}...")

        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred)

        precision = precision_score(
            y_test,
            y_pred,
            average="weighted",
            zero_division=0
        )

        recall = recall_score(
            y_test,
            y_pred,
            average="weighted",
            zero_division=0
        )

        f1 = f1_score(
            y_test,
            y_pred,
            average="weighted",
            zero_division=0
        )

        ready_recall = recall_score(
            y_test,
            y_pred,
            labels=[2],
            average="macro",
            zero_division=0
        )

        results.append({
            "model": model_name,
            "accuracy": round(float(accuracy), 4),
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1_score": round(float(f1), 4),
            "ready_class_recall": round(float(ready_recall), 4)
        })

        trained_models[model_name] = model

        print(f"{model_name} Accuracy: {accuracy:.4f}")
        print(f"{model_name} Precision: {precision:.4f}")
        print(f"{model_name} Recall: {recall:.4f}")
        print(f"{model_name} F1 Score: {f1:.4f}")
        print(f"{model_name} Ready Class Recall: {ready_recall:.4f}")

    return results, trained_models


def select_best_model(results, trained_models):
    results_df = pd.DataFrame(results)

    results_df = results_df.sort_values(
        by=[
            "f1_score",
            "ready_class_recall",
            "accuracy"
        ],
        ascending=False
    ).reset_index(drop=True)

    best_model_name = results_df.iloc[0]["model"]
    best_model = trained_models[best_model_name]

    print("\nFinal Model Comparison:")
    print(results_df)

    print("\nBest Model Selected:", best_model_name)

    return best_model_name, best_model, results_df


def save_model_comparison_plot(results_df):
    plot_df = results_df.copy()

    x = np.arange(len(plot_df["model"]))
    width = 0.2

    plt.figure(figsize=(10, 6))

    plt.bar(
        x - width,
        plot_df["accuracy"],
        width,
        label="Accuracy"
    )

    plt.bar(
        x,
        plot_df["precision"],
        width,
        label="Precision"
    )

    plt.bar(
        x + width,
        plot_df["recall"],
        width,
        label="Recall"
    )

    plt.bar(
        x + (2 * width),
        plot_df["f1_score"],
        width,
        label="F1 Score"
    )

    plt.xticks(
        x,
        plot_df["model"],
        rotation=20,
        ha="right"
    )

    plt.ylim(0, 1.05)
    plt.ylabel("Score")
    plt.title("Harvest Readiness Model Comparison")
    plt.legend()
    plt.tight_layout()
    plt.savefig(MODEL_COMPARISON_PLOT, dpi=160)
    plt.close()


def save_outputs(
    best_model_name,
    best_model,
    results_df,
    X_train,
    X_test,
    y_test
):
    joblib.dump(best_model, BEST_MODEL_FILE)
    joblib.dump(X_train.columns.tolist(), FEATURE_COLUMNS_FILE)

    results_df.to_csv(MODEL_RESULTS_CSV, index=False)

    comparison_output = {
        "problem_type": "multiclass_classification",
        "target": "harvest_readiness_label",
        "classes": {
            "0": "Not Ready",
            "1": "Approaching",
            "2": "Ready"
        },
        "selection_rule": (
            "Best model selected using highest weighted F1-score, "
            "then Ready-class recall, then accuracy."
        ),
        "best_model": best_model_name,
        "results": results_df.to_dict(orient="records")
    }

    with MODEL_RESULTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(comparison_output, file, indent=2)

    y_pred_best = best_model.predict(X_test)

    report = classification_report(
        y_test,
        y_pred_best,
        labels=[0, 1, 2],
        target_names=[
            "Not Ready",
            "Approaching",
            "Ready"
        ],
        output_dict=True,
        zero_division=0
    )

    with CLASSIFICATION_REPORT_FILE.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    cm = confusion_matrix(
        y_test,
        y_pred_best,
        labels=[0, 1, 2]
    )

    display = ConfusionMatrixDisplay(
        confusion_matrix=cm,
        display_labels=[
            "Not Ready",
            "Approaching",
            "Ready"
        ]
    )

    fig, ax = plt.subplots(figsize=(7, 6))
    display.plot(
        ax=ax,
        cmap="Blues",
        values_format="d"
    )

    plt.title(f"Confusion Matrix - {best_model_name}")
    plt.tight_layout()
    plt.savefig(CONFUSION_MATRIX_FILE, dpi=160)
    plt.close()

    save_model_comparison_plot(results_df)

    print("\nSaved files:")
    print(BEST_MODEL_FILE)
    print(FEATURE_COLUMNS_FILE)
    print(MODEL_RESULTS_FILE)
    print(MODEL_RESULTS_CSV)
    print(CLASSIFICATION_REPORT_FILE)
    print(CONFUSION_MATRIX_FILE)
    print(MODEL_COMPARISON_PLOT)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Optional sample size for faster testing, example: --sample 50000"
    )

    args = parser.parse_args()

    data = load_dataset(sample_size=args.sample)

    X, y = prepare_features_and_target(data)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    print("\nTrain shape:", X_train.shape)
    print("Test shape:", X_test.shape)

    models = build_models()

    results, trained_models = evaluate_models(
        models,
        X_train,
        X_test,
        y_train,
        y_test
    )

    best_model_name, best_model, results_df = select_best_model(
        results,
        trained_models
    )

    save_outputs(
        best_model_name,
        best_model,
        results_df,
        X_train,
        X_test,
        y_test
    )

    print("\nStep 3 completed successfully.")


if __name__ == "__main__":
    main()