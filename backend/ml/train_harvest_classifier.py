"""Train probability-calibrated harvest-within-horizon classifiers.

Run from the project root:
    python backend/ml/train_harvest_classifier.py

Faster trial:
    python backend/ml/train_harvest_classifier.py --sample 100000
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from lightgbm import LGBMClassifier
from sklearn.calibration import (
    CalibratedClassifierCV,
    calibration_curve,
)
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"

for path in [str(PROJECT_ROOT), str(BACKEND_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)

from harvest.harvest_target import (  # noqa: E402
    TARGET_COLUMN as GENERATED_TARGET_COLUMN,
    create_future_harvest_target,
)
from harvest.live_feature_engineering import (  # noqa: E402
    FeatureEngineeringConfig,
    HARVEST_CLASSIFIER_FEATURES,
    add_live_features,
    canonicalize_historical_data,
    resample_hourly,
)


load_dotenv(PROJECT_ROOT / ".env")

DATA_PATH = Path(
    os.getenv(
        "HARVEST_HISTORICAL_DATA_PATH",
        BACKEND_DIR
        / "data"
        / "hive_data_with_features.csv",
    )
)

LABEL_COLUMN = os.getenv(
    "HARVEST_LABEL_COLUMN",
    "honey_harvest_label_next_7d",
)
TARGET_MODE = os.getenv(
    "HARVEST_TARGET_MODE",
    "precomputed",
).strip().lower()
TARGET_COLUMN = os.getenv(
    "HARVEST_MODEL_TARGET_COLUMN",
    "harvest_within_prediction_horizon",
)

MODEL_DIR = BACKEND_DIR / "models"
OUTPUT_DIR = (
    BACKEND_DIR / "outputs" / "harvest"
)

MODEL_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HORIZON_HOURS = int(
    os.getenv(
        "HARVEST_PREDICTION_HORIZON_HOURS",
        "72",
    )
)
PURGE_HOURS = int(
    os.getenv(
        "HARVEST_SPLIT_PURGE_HOURS",
        str(HORIZON_HOURS),
    )
)
POST_EVENT_EXCLUSION_HOURS = int(
    os.getenv(
        "HARVEST_POST_EVENT_EXCLUSION_HOURS",
        "24",
    )
)
EVENT_MERGE_GAP_HOURS = int(
    os.getenv(
        "HARVEST_EVENT_MERGE_GAP_HOURS",
        "12",
    )
)
MIN_THRESHOLD_RECALL = float(
    os.getenv(
        "HARVEST_MIN_THRESHOLD_RECALL",
        "0.80",
    )
)


SPLIT_STRATEGY = os.getenv(
    "HARVEST_SPLIT_STRATEGY",
    "auto",
).strip().lower()

MIN_POSITIVES_PER_SPLIT = int(
    os.getenv(
        "HARVEST_MIN_POSITIVES_PER_SPLIT",
        "10",
    )
)

MIN_NEGATIVES_PER_SPLIT = int(
    os.getenv(
        "HARVEST_MIN_NEGATIVES_PER_SPLIT",
        "100",
    )
)

HISTORICAL_TIMESTAMPS_ARE_UTC = (
    os.getenv(
        "HISTORICAL_TIMESTAMPS_ARE_UTC",
        "false",
    ).lower()
    == "true"
)
HISTORICAL_SOURCE_TIMEZONE = os.getenv(
    "HISTORICAL_SOURCE_TIMEZONE",
    "Europe/London",
)
FEATURE_TIMEZONE = os.getenv(
    "HISTORICAL_FEATURE_TIMEZONE",
    HISTORICAL_SOURCE_TIMEZONE,
)
INTERPOLATION_LIMIT_HOURS = int(
    os.getenv(
        "IOT_INTERPOLATION_LIMIT_HOURS",
        "3",
    )
)

CONFIG = FeatureEngineeringConfig(
    feature_timezone=FEATURE_TIMEZONE,
    timestamps_are_utc=(
        HISTORICAL_TIMESTAMPS_ARE_UTC
    ),
    source_timezone=HISTORICAL_SOURCE_TIMEZONE,
    interpolation_limit_hours=(
        INTERPOLATION_LIMIT_HOURS
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help=(
            "Development-only approximate row limit. "
            "Complete hive histories are selected; "
            "individual time-series rows are not "
            "uniformly removed."
        ),
    )
    return parser.parse_args()


def select_complete_hives_for_sample(
    raw: pd.DataFrame,
    max_rows: int,
) -> pd.DataFrame:
    """
    Select complete hive histories for a faster development run.

    Uniform row sampling is invalid here because it destroys hourly continuity,
    lag values and rolling windows. This function keeps complete hives.
    """
    if max_rows <= 0 or max_rows >= len(raw):
        return raw

    summary = (
        raw.groupby("hive_id")
        .agg(
            rows=("hive_id", "size"),
            positives=(LABEL_COLUMN, "sum"),
        )
        .reset_index()
    )
    summary["negatives"] = (
        summary["rows"] - summary["positives"]
    )
    summary["contains_both_classes"] = (
        summary["positives"].gt(0)
        & summary["negatives"].gt(0)
    )

    # Prefer hives that contain both classes. Smaller complete histories are
    # selected first so the development run stays near the requested limit.
    summary = summary.sort_values(
        [
            "contains_both_classes",
            "positives",
            "rows",
        ],
        ascending=[False, False, True],
    )

    selected_hives: list[str] = []
    selected_rows = 0

    for row in summary.itertuples(index=False):
        hive_id = str(row.hive_id)
        hive_rows = int(row.rows)

        if (
            selected_hives
            and selected_rows + hive_rows > max_rows
            and len(selected_hives) >= 3
        ):
            continue

        selected_hives.append(hive_id)
        selected_rows += hive_rows

        if (
            selected_rows >= max_rows
            and len(selected_hives) >= 3
        ):
            break

    sampled = raw.loc[
        raw["hive_id"].astype(str).isin(
            selected_hives
        )
    ].copy()

    print(
        "Development sample keeps complete histories "
        f"for {len(selected_hives)} hives and "
        f"{len(sampled):,} rows."
    )
    print(
        "Selected hives:",
        ", ".join(selected_hives),
    )

    return sampled


def prepare_model_target(
    featured: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepare the classifier target.

    precomputed:
        LABEL_COLUMN already means an event/readiness
        within the configured future horizon. This is
        the correct mode for:
            honey_harvest_label_next_7d

    event:
        LABEL_COLUMN is an actual event at the current
        timestamp. A future target is generated.
    """
    if TARGET_MODE == "precomputed":
        data = featured.copy()

        if LABEL_COLUMN not in data.columns:
            raise ValueError(
                f"Precomputed target column is "
                f"missing: {LABEL_COLUMN}"
            )

        numeric_target = pd.to_numeric(
            data[LABEL_COLUMN],
            errors="coerce",
        )

        observed_values = set(
            numeric_target.dropna().unique().tolist()
        )

        if not observed_values.issubset({0, 1}):
            raise ValueError(
                f"{LABEL_COLUMN} must be binary "
                f"for precomputed mode. Found: "
                f"{sorted(observed_values)}"
            )

        data[TARGET_COLUMN] = (
            numeric_target.fillna(0).astype(int)
        )

        # Remove each hive's final horizon because a
        # complete future period may not be observable.
        final_timestamp = data.groupby(
            "hive_id"
        )["timestamp"].transform("max")

        data["target_row_eligible"] = (
            data["timestamp"]
            <= final_timestamp
            - pd.Timedelta(
                hours=HORIZON_HOURS
            )
        )

        return data

    if TARGET_MODE == "event":
        generated = create_future_harvest_target(
            featured,
            label_column=LABEL_COLUMN,
            horizon_hours=HORIZON_HOURS,
            post_event_exclusion_hours=(
                POST_EVENT_EXCLUSION_HOURS
            ),
            merge_gap_hours=(
                EVENT_MERGE_GAP_HOURS
            ),
        )

        if GENERATED_TARGET_COLUMN != TARGET_COLUMN:
            generated = generated.rename(
                columns={
                    GENERATED_TARGET_COLUMN:
                        TARGET_COLUMN
                }
            )

        return generated

    raise ValueError(
        "HARVEST_TARGET_MODE must be either "
        "'precomputed' or 'event'."
    )


def make_calibrated_classifier(
    fitted_estimator,
    X_calibration: pd.DataFrame,
    y_calibration: pd.Series,
):
    """
    Use FrozenEstimator on modern scikit-learn and cv='prefit'
    as a compatibility fallback for older versions.
    """
    try:
        from sklearn.frozen import FrozenEstimator

        calibrated = CalibratedClassifierCV(
            estimator=FrozenEstimator(
                fitted_estimator
            ),
            method="sigmoid",
        )
    except ImportError:
        calibrated = CalibratedClassifierCV(
            estimator=fitted_estimator,
            method="sigmoid",
            cv="prefit",
        )

    calibrated.fit(
        X_calibration,
        y_calibration,
    )
    return calibrated


def split_class_summary(
    frame: pd.DataFrame,
) -> dict:
    positives = int(
        frame[TARGET_COLUMN].sum()
    )
    negatives = int(
        len(frame) - positives
    )

    return {
        "rows": int(len(frame)),
        "positives": positives,
        "negatives": negatives,
        "positive_rate": (
            round(
                positives / len(frame),
                6,
            )
            if len(frame)
            else 0.0
        ),
    }


def split_is_valid(
    frame: pd.DataFrame,
) -> bool:
    summary = split_class_summary(frame)

    return (
        summary["positives"]
        >= MIN_POSITIVES_PER_SPLIT
        and summary["negatives"]
        >= MIN_NEGATIVES_PER_SPLIT
        and frame[TARGET_COLUMN].nunique() == 2
    )


def save_target_distribution_reports(
    data: pd.DataFrame,
) -> None:
    report = data[
        ["timestamp", "hive_id", TARGET_COLUMN]
    ].copy()

    report["year_month"] = (
        pd.to_datetime(
            report["timestamp"],
            errors="coerce",
            utc=True,
        ).dt.strftime("%Y-%m")
    )

    monthly = (
        report.groupby("year_month")
        .agg(
            rows=(TARGET_COLUMN, "size"),
            positives=(TARGET_COLUMN, "sum"),
            hives=("hive_id", "nunique"),
        )
        .reset_index()
    )
    monthly["negatives"] = (
        monthly["rows"] - monthly["positives"]
    )
    monthly["positive_rate"] = (
        monthly["positives"]
        / monthly["rows"]
    )

    by_hive = (
        report.groupby("hive_id")
        .agg(
            rows=(TARGET_COLUMN, "size"),
            positives=(TARGET_COLUMN, "sum"),
            start_time=("timestamp", "min"),
            end_time=("timestamp", "max"),
        )
        .reset_index()
    )
    by_hive["negatives"] = (
        by_hive["rows"] - by_hive["positives"]
    )
    by_hive["positive_rate"] = (
        by_hive["positives"]
        / by_hive["rows"]
    )

    monthly.to_csv(
        OUTPUT_DIR
        / "harvest_target_distribution_by_month.csv",
        index=False,
    )
    by_hive.to_csv(
        OUTPUT_DIR
        / "harvest_target_distribution_by_hive.csv",
        index=False,
    )

    print("\nTarget distribution by month:")
    print(
        monthly[
            [
                "year_month",
                "rows",
                "positives",
                "negatives",
                "positive_rate",
            ]
        ].to_string(index=False)
    )


def event_aware_chronological_split(
    data: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    dict,
]:
    """
    Search chronological boundaries rather than assuming fixed 70/15/15
    quantiles contain both classes.

    A purge gap is maintained before validation and test.
    """
    ordered = data.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    purge = pd.Timedelta(
        hours=PURGE_HOURS
    )
    overall_positive_rate = float(
        ordered[TARGET_COLUMN].mean()
    )

    candidates: list[
        tuple[
            float,
            pd.DataFrame,
            pd.DataFrame,
            pd.DataFrame,
            dict,
        ]
    ] = []

    train_quantiles = np.arange(
        0.50,
        0.751,
        0.025,
    )

    for train_quantile in train_quantiles:
        validation_quantiles = np.arange(
            train_quantile + 0.10,
            0.901,
            0.025,
        )

        for validation_quantile in validation_quantiles:
            train_boundary = ordered[
                "timestamp"
            ].quantile(train_quantile)
            validation_boundary = ordered[
                "timestamp"
            ].quantile(validation_quantile)

            train = ordered.loc[
                ordered["timestamp"]
                <= train_boundary - purge
            ].copy()

            validation = ordered.loc[
                (
                    ordered["timestamp"]
                    >= train_boundary
                )
                & (
                    ordered["timestamp"]
                    <= validation_boundary - purge
                )
            ].copy()

            test = ordered.loc[
                ordered["timestamp"]
                >= validation_boundary
            ].copy()

            if not all(
                split_is_valid(frame)
                for frame in [
                    train,
                    validation,
                    test,
                ]
            ):
                continue

            row_shares = np.array(
                [
                    len(train),
                    len(validation),
                    len(test),
                ],
                dtype=float,
            )
            row_shares /= row_shares.sum()

            positive_rates = np.array(
                [
                    train[TARGET_COLUMN].mean(),
                    validation[TARGET_COLUMN].mean(),
                    test[TARGET_COLUMN].mean(),
                ],
                dtype=float,
            )

            size_penalty = float(
                np.abs(
                    row_shares
                    - np.array([0.70, 0.15, 0.15])
                ).sum()
            )
            prevalence_penalty = float(
                np.abs(
                    positive_rates
                    - overall_positive_rate
                ).mean()
            )

            score = (
                size_penalty
                + 0.50 * prevalence_penalty
            )

            metadata = {
                "strategy": (
                    "event_aware_chronological"
                ),
                "train_quantile": round(
                    float(train_quantile),
                    4,
                ),
                "validation_quantile": round(
                    float(validation_quantile),
                    4,
                ),
                "train_end": (
                    train["timestamp"]
                    .max()
                    .isoformat()
                ),
                "validation_start": (
                    validation["timestamp"]
                    .min()
                    .isoformat()
                ),
                "validation_end": (
                    validation["timestamp"]
                    .max()
                    .isoformat()
                ),
                "test_start": (
                    test["timestamp"]
                    .min()
                    .isoformat()
                ),
                "purge_hours": PURGE_HOURS,
            }

            candidates.append(
                (
                    score,
                    train,
                    validation,
                    test,
                    metadata,
                )
            )

    if not candidates:
        raise ValueError(
            "No chronological split could place both "
            "target classes in train, validation and "
            "test while retaining the purge gap."
        )

    candidates.sort(
        key=lambda item: item[0]
    )
    _, train, validation, test, metadata = (
        candidates[0]
    )

    return (
        train,
        validation,
        test,
        metadata,
    )


def group_holdout_split(
    data: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    dict,
]:
    """
    Hold out complete hives.

    This is a defensible fallback for deployment to a new Sri Lankan hive,
    because no historical hive appears in more than one split.
    """
    unique_hives = data["hive_id"].nunique()

    if unique_hives < 6:
        raise ValueError(
            "At least six hives are recommended "
            "for a train/validation/test group split."
        )

    best = None

    for seed in range(500):
        first_split = GroupShuffleSplit(
            n_splits=1,
            test_size=0.15,
            random_state=seed,
        )
        train_validation_indices, test_indices = (
            next(
                first_split.split(
                    data,
                    data[TARGET_COLUMN],
                    groups=data["hive_id"],
                )
            )
        )

        train_validation = data.iloc[
            train_validation_indices
        ].copy()
        test = data.iloc[
            test_indices
        ].copy()

        second_split = GroupShuffleSplit(
            n_splits=1,
            test_size=(0.15 / 0.85),
            random_state=seed + 1000,
        )
        train_indices, validation_indices = (
            next(
                second_split.split(
                    train_validation,
                    train_validation[TARGET_COLUMN],
                    groups=train_validation["hive_id"],
                )
            )
        )

        train = train_validation.iloc[
            train_indices
        ].copy()
        validation = train_validation.iloc[
            validation_indices
        ].copy()

        if not all(
            split_is_valid(frame)
            for frame in [
                train,
                validation,
                test,
            ]
        ):
            continue

        row_shares = np.array(
            [
                len(train),
                len(validation),
                len(test),
            ],
            dtype=float,
        )
        row_shares /= row_shares.sum()

        overall_positive_rate = float(
            data[TARGET_COLUMN].mean()
        )
        positive_rates = np.array(
            [
                train[TARGET_COLUMN].mean(),
                validation[TARGET_COLUMN].mean(),
                test[TARGET_COLUMN].mean(),
            ]
        )

        score = float(
            np.abs(
                row_shares
                - np.array([0.70, 0.15, 0.15])
            ).sum()
            + 0.50
            * np.abs(
                positive_rates
                - overall_positive_rate
            ).mean()
        )

        metadata = {
            "strategy": "group_holdout_by_hive",
            "random_state": seed,
            "purge_hours": 0,
            "train_hives": sorted(
                train["hive_id"]
                .astype(str)
                .unique()
                .tolist()
            ),
            "validation_hives": sorted(
                validation["hive_id"]
                .astype(str)
                .unique()
                .tolist()
            ),
            "test_hives": sorted(
                test["hive_id"]
                .astype(str)
                .unique()
                .tolist()
            ),
        }

        candidate = (
            score,
            train,
            validation,
            test,
            metadata,
        )

        if best is None or score < best[0]:
            best = candidate

    if best is None:
        raise ValueError(
            "No hive-group split could place both "
            "classes in train, validation and test. "
            "Inspect the target-distribution CSV files."
        )

    _, train, validation, test, metadata = best

    return (
        train,
        validation,
        test,
        metadata,
    )


def create_data_split(
    data: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    dict,
]:
    if SPLIT_STRATEGY not in {
        "auto",
        "chronological",
        "group",
    }:
        raise ValueError(
            "HARVEST_SPLIT_STRATEGY must be "
            "'auto', 'chronological' or 'group'."
        )

    if SPLIT_STRATEGY in {
        "auto",
        "chronological",
    }:
        try:
            result = (
                event_aware_chronological_split(
                    data
                )
            )
            print(
                "\nUsing event-aware chronological "
                "split."
            )
            return result
        except ValueError as error:
            if SPLIT_STRATEGY == "chronological":
                raise

            print(
                "\nChronological split unavailable:"
            )
            print(str(error))
            print(
                "Falling back to a complete-hive "
                "group holdout split because the "
                "deployment target is an unseen "
                "Sri Lankan hive."
            )

    result = group_holdout_split(data)
    print(
        "\nUsing complete-hive group holdout "
        "split."
    )
    return result


def choose_threshold(
    y_true: pd.Series,
    probabilities: np.ndarray,
) -> dict:
    precision, recall, thresholds = (
        precision_recall_curve(
            y_true,
            probabilities,
        )
    )

    if len(thresholds) == 0:
        return {
            "threshold": 0.5,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "selection_rule": (
                "Fallback threshold because validation "
                "contained one class."
            ),
        }

    precision_values = precision[:-1]
    recall_values = recall[:-1]
    f1_values = (
        2
        * precision_values
        * recall_values
        / np.maximum(
            precision_values + recall_values,
            1e-12,
        )
    )

    eligible = np.where(
        recall_values >= MIN_THRESHOLD_RECALL
    )[0]

    if len(eligible) > 0:
        best_index = eligible[
            np.argmax(f1_values[eligible])
        ]
        rule = (
            f"Highest F1 among thresholds with "
            f"recall >= {MIN_THRESHOLD_RECALL:.2f}"
        )
    else:
        best_index = int(
            np.argmax(f1_values)
        )
        rule = (
            "Highest F1 because the minimum recall "
            "requirement was not reached."
        )

    return {
        "threshold": round(
            float(thresholds[best_index]),
            6,
        ),
        "precision": round(
            float(precision_values[best_index]),
            6,
        ),
        "recall": round(
            float(recall_values[best_index]),
            6,
        ),
        "f1": round(
            float(f1_values[best_index]),
            6,
        ),
        "selection_rule": rule,
    }


def classification_metrics(
    y_true: pd.Series,
    probabilities: np.ndarray,
    threshold: float,
) -> dict:
    predictions = (
        probabilities >= threshold
    ).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        predictions,
        labels=[0, 1],
    ).ravel()

    false_alert_rate = (
        fp / (fp + tn)
        if (fp + tn) > 0
        else 0.0
    )
    missed_harvest_rate = (
        fn / (fn + tp)
        if (fn + tp) > 0
        else 0.0
    )

    result = {
        "precision": float(
            precision_score(
                y_true,
                predictions,
                zero_division=0,
            )
        ),
        "recall": float(
            recall_score(
                y_true,
                predictions,
                zero_division=0,
            )
        ),
        "f1": float(
            f1_score(
                y_true,
                predictions,
                zero_division=0,
            )
        ),
        "pr_auc": float(
            average_precision_score(
                y_true,
                probabilities,
            )
        ),
        "brier_score": float(
            brier_score_loss(
                y_true,
                probabilities,
            )
        ),
        "log_loss": float(
            log_loss(
                y_true,
                np.column_stack(
                    [
                        1 - probabilities,
                        probabilities,
                    ]
                ),
                labels=[0, 1],
            )
        ),
        "false_alert_rate": float(
            false_alert_rate
        ),
        "missed_harvest_rate": float(
            missed_harvest_rate
        ),
        "threshold": float(threshold),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
    }

    try:
        result["roc_auc"] = float(
            roc_auc_score(
                y_true,
                probabilities,
            )
        )
    except ValueError:
        result["roc_auc"] = None

    return {
        key: (
            round(value, 6)
            if isinstance(value, float)
            else value
        )
        for key, value in result.items()
    }


def feature_ranges(
    frame: pd.DataFrame,
) -> dict:
    ranges = {}

    for column in HARVEST_CLASSIFIER_FEATURES:
        values = pd.to_numeric(
            frame[column],
            errors="coerce",
        ).dropna()

        if values.empty:
            continue

        ranges[column] = {
            "p01": round(
                float(values.quantile(0.01)),
                6,
            ),
            "p50": round(
                float(values.quantile(0.50)),
                6,
            ),
            "p99": round(
                float(values.quantile(0.99)),
                6,
            ),
        }

    return ranges


def positive_environment_ranges(
    frame: pd.DataFrame,
) -> dict:
    columns = [
        "internal_temperature_mean_24h",
        "internal_humidity_mean_24h",
        "external_temperature_c",
        "external_humidity_pct",
    ]

    positive = frame.loc[
        frame[TARGET_COLUMN].eq(1)
    ]

    result = {}

    for column in columns:
        values = pd.to_numeric(
            positive[column],
            errors="coerce",
        ).dropna()

        if len(values) < 10:
            continue

        result[column] = {
            "p10": round(
                float(values.quantile(0.10)),
                6,
            ),
            "median": round(
                float(values.median()),
                6,
            ),
            "p90": round(
                float(values.quantile(0.90)),
                6,
            ),
        }

    return result


def extract_importance(
    fitted_pipeline: Pipeline,
) -> list[dict]:
    estimator = fitted_pipeline.named_steps[
        "model"
    ]

    if hasattr(estimator, "feature_importances_"):
        values = np.asarray(
            estimator.feature_importances_,
            dtype=float,
        )
    elif hasattr(estimator, "coef_"):
        values = np.abs(
            np.asarray(
                estimator.coef_[0],
                dtype=float,
            )
        )
    else:
        return []

    pairs = sorted(
        zip(
            HARVEST_CLASSIFIER_FEATURES,
            values,
        ),
        key=lambda pair: pair[1],
        reverse=True,
    )

    return [
        {
            "feature": feature,
            "importance": round(
                float(value),
                8,
            ),
        }
        for feature, value in pairs
    ]


def save_evaluation_plots(
    *,
    y_test: pd.Series,
    probability_by_model: dict[str, np.ndarray],
    best_model_name: str,
    best_threshold: float,
    best_importance: list[dict],
    test_frame: pd.DataFrame,
) -> None:
    best_probability = probability_by_model[
        best_model_name
    ]
    best_prediction = (
        best_probability >= best_threshold
    ).astype(int)

    matrix = confusion_matrix(
        y_test,
        best_prediction,
        labels=[0, 1],
    )

    plt.figure(figsize=(6, 5))
    plt.imshow(matrix)
    plt.title(
        f"Harvest Classifier Confusion Matrix\n"
        f"{best_model_name}"
    )
    plt.xlabel("Predicted class")
    plt.ylabel("Actual class")
    plt.xticks([0, 1], ["No harvest", "Harvest"])
    plt.yticks([0, 1], ["No harvest", "Harvest"])

    for row in range(2):
        for column in range(2):
            plt.text(
                column,
                row,
                str(matrix[row, column]),
                ha="center",
                va="center",
            )

    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR
        / "harvest_confusion_matrix.png",
        dpi=170,
    )
    plt.close()

    plt.figure(figsize=(8, 6))
    for name, probability in probability_by_model.items():
        precision, recall, _ = (
            precision_recall_curve(
                y_test,
                probability,
            )
        )
        plt.plot(
            recall,
            precision,
            label=name,
        )

    plt.title(
        "Harvest Classifier Precision-Recall Curves"
    )
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.legend()
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR
        / "harvest_precision_recall_curve.png",
        dpi=170,
    )
    plt.close()

    plt.figure(figsize=(8, 6))
    for name, probability in probability_by_model.items():
        try:
            fpr, tpr, _ = roc_curve(
                y_test,
                probability,
            )
            plt.plot(
                fpr,
                tpr,
                label=name,
            )
        except ValueError:
            continue

    plt.plot([0, 1], [0, 1], linestyle="--")
    plt.title("Harvest Classifier ROC Curves")
    plt.xlabel("False-positive rate")
    plt.ylabel("True-positive rate")
    plt.legend()
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "harvest_roc_curve.png",
        dpi=170,
    )
    plt.close()

    plt.figure(figsize=(8, 6))
    for name, probability in probability_by_model.items():
        try:
            observed, predicted = calibration_curve(
                y_test,
                probability,
                n_bins=10,
                strategy="quantile",
            )
            plt.plot(
                predicted,
                observed,
                marker="o",
                label=name,
            )
        except ValueError:
            continue

    plt.plot([0, 1], [0, 1], linestyle="--")
    plt.title(
        "Harvest Probability Calibration"
    )
    plt.xlabel("Mean predicted probability")
    plt.ylabel("Observed positive rate")
    plt.legend()
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR
        / "harvest_calibration_curve.png",
        dpi=170,
    )
    plt.close()

    if best_importance:
        importance_df = pd.DataFrame(
            best_importance[:15]
        ).sort_values(
            "importance",
            ascending=True,
        )

        plt.figure(figsize=(10, 7))
        plt.barh(
            importance_df["feature"],
            importance_df["importance"],
        )
        plt.title(
            f"Top Feature Importance — "
            f"{best_model_name}"
        )
        plt.xlabel("Importance")
        plt.tight_layout()
        plt.savefig(
            OUTPUT_DIR
            / "harvest_feature_importance.png",
            dpi=170,
        )
        plt.close()

    timeline = test_frame[
        ["timestamp", "hive_id", TARGET_COLUMN]
    ].copy()
    timeline["predicted_probability"] = (
        best_probability
    )

    timeline.to_csv(
        OUTPUT_DIR
        / "actual_vs_predicted_harvest_timeline.csv",
        index=False,
    )

    selected_hive = (
        timeline.groupby("hive_id")[
            TARGET_COLUMN
        ]
        .sum()
        .sort_values(
            ascending=False
        )
        .index[0]
    )

    hive_timeline = timeline.loc[
        timeline["hive_id"].eq(selected_hive)
    ].sort_values("timestamp")

    plt.figure(figsize=(13, 6))
    plt.plot(
        hive_timeline["timestamp"],
        hive_timeline["predicted_probability"],
        label="Predicted probability",
    )
    plt.plot(
        hive_timeline["timestamp"],
        hive_timeline[TARGET_COLUMN],
        label=(
            f"Actual {HORIZON_HOURS}-hour target"
        ),
        alpha=0.7,
    )
    plt.axhline(
        best_threshold,
        linestyle="--",
        label="Decision threshold",
    )
    plt.title(
        f"Actual vs Predicted Timeline — "
        f"Hive {selected_hive}"
    )
    plt.xlabel("Timestamp")
    plt.ylabel("Probability / class")
    plt.legend()
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR
        / "actual_vs_predicted_harvest_timeline.png",
        dpi=170,
    )
    plt.close()


def main() -> None:
    args = parse_args()

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Historical dataset not found: "
            f"{DATA_PATH}"
        )

    raw = pd.read_csv(DATA_PATH)

    required = {
        "timestamp",
        "hive_id",
        LABEL_COLUMN,
    }
    missing = sorted(
        required - set(raw.columns)
    )

    if missing:
        raise ValueError(
            f"Required columns are missing: {missing}"
        )

    raw[LABEL_COLUMN] = (
        pd.to_numeric(
            raw[LABEL_COLUMN],
            errors="coerce",
        )
        .fillna(0)
        .gt(0)
        .astype(int)
    )

    if args.sample and args.sample < len(raw):
        raw = select_complete_hives_for_sample(
            raw,
            args.sample,
        )

    canonical = canonicalize_historical_data(
        raw,
        config=CONFIG,
    )

    hourly = resample_hourly(
        canonical,
        config=CONFIG,
        aggregation_overrides={
            LABEL_COLUMN: "max"
        },
    )

    featured = add_live_features(
        hourly,
        config=CONFIG,
    )

    targeted = prepare_model_target(
        featured
    )

    modelling = targeted.loc[
        targeted["target_row_eligible"]
    ].copy()

    modelling = modelling.dropna(
        subset=[
            *HARVEST_CLASSIFIER_FEATURES,
            TARGET_COLUMN,
        ]
    )

    if modelling.empty:
        raise ValueError(
            "No modelling rows remain after target "
            "creation and feature validation."
        )

    positive_count = int(
        modelling[TARGET_COLUMN].sum()
    )
    negative_count = int(
        len(modelling) - positive_count
    )

    if positive_count == 0:
        raise ValueError(
            (
                "No positive target rows remain. "
                f"Check {LABEL_COLUMN}, target mode "
                f"{TARGET_MODE}, and the configured "
                "prediction horizon."
            )
        )

    modelling.to_csv(
        OUTPUT_DIR
        / "harvest_classifier_dataset.csv",
        index=False,
    )

    save_target_distribution_reports(
        modelling
    )

    train, validation, test, boundaries = (
        create_data_split(
            modelling
        )
    )

    split_summary = {
        "train": split_class_summary(train),
        "validation": split_class_summary(
            validation
        ),
        "test": split_class_summary(test),
    }

    print("\nSelected split summary:")
    print(
        json.dumps(
            split_summary,
            indent=2,
        )
    )

    for split_name, split_data in {
        "train": train,
        "validation": validation,
        "test": test,
    }.items():
        if split_data.empty:
            raise ValueError(
                f"{split_name} split is empty. "
                "Use more historical data or reduce "
                "HARVEST_SPLIT_PURGE_HOURS."
            )

        if split_data[
            TARGET_COLUMN
        ].nunique() < 2:
            raise ValueError(
                f"{split_name} split contains only "
                "one target class after the selected "
                "strategy. Inspect "
                "harvest_target_distribution_by_month.csv "
                "and harvest_target_distribution_by_hive.csv."
            )

    X_train = train[
        HARVEST_CLASSIFIER_FEATURES
    ]
    y_train = train[TARGET_COLUMN]

    X_validation = validation[
        HARVEST_CLASSIFIER_FEATURES
    ]
    y_validation = validation[TARGET_COLUMN]

    X_test = test[
        HARVEST_CLASSIFIER_FEATURES
    ]
    y_test = test[TARGET_COLUMN]

    scale_pos_weight = (
        y_train.eq(0).sum()
        / max(1, y_train.eq(1).sum())
    )

    models = {
        "Logistic Regression": Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median"
                    ),
                ),
                (
                    "scaler",
                    StandardScaler(),
                ),
                (
                    "model",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=42,
                    ),
                ),
            ]
        ),
        "Random Forest": Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median"
                    ),
                ),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=300,
                        max_depth=18,
                        min_samples_leaf=2,
                        class_weight=(
                            "balanced_subsample"
                        ),
                        random_state=42,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "XGBoost": Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median"
                    ),
                ),
                (
                    "model",
                    XGBClassifier(
                        n_estimators=450,
                        learning_rate=0.04,
                        max_depth=7,
                        subsample=0.85,
                        colsample_bytree=0.85,
                        objective="binary:logistic",
                        eval_metric="logloss",
                        scale_pos_weight=(
                            scale_pos_weight
                        ),
                        random_state=42,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "LightGBM": Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median"
                    ),
                ),
                (
                    "model",
                    LGBMClassifier(
                        n_estimators=450,
                        learning_rate=0.04,
                        num_leaves=48,
                        subsample=0.85,
                        colsample_bytree=0.85,
                        class_weight="balanced",
                        random_state=42,
                        n_jobs=-1,
                        verbosity=-1,
                    ),
                ),
            ]
        ),
    }

    results: list[dict] = []
    calibrated_models: dict = {}
    base_models: dict = {}
    probability_by_model: dict[
        str,
        np.ndarray,
    ] = {}
    thresholds: dict[str, dict] = {}
    importances: dict[str, list[dict]] = {}

    for name, estimator in models.items():
        print(f"Training {name}...")

        estimator.fit(
            X_train,
            y_train,
        )

        calibrated = make_calibrated_classifier(
            estimator,
            X_validation,
            y_validation,
        )

        validation_probability = (
            calibrated.predict_proba(
                X_validation
            )[:, 1]
        )

        threshold_info = choose_threshold(
            y_validation,
            validation_probability,
        )

        test_probability = (
            calibrated.predict_proba(
                X_test
            )[:, 1]
        )

        metrics = classification_metrics(
            y_test,
            test_probability,
            threshold_info["threshold"],
        )

        row = {
            "model": name,
            **metrics,
            "validation_threshold_precision": (
                threshold_info["precision"]
            ),
            "validation_threshold_recall": (
                threshold_info["recall"]
            ),
            "validation_threshold_f1": (
                threshold_info["f1"]
            ),
            "threshold_selection_rule": (
                threshold_info[
                    "selection_rule"
                ]
            ),
        }

        print(row)

        results.append(row)
        calibrated_models[name] = calibrated
        base_models[name] = estimator
        probability_by_model[name] = (
            test_probability
        )
        thresholds[name] = threshold_info
        importances[name] = (
            extract_importance(estimator)
        )

    results.sort(
        key=lambda row: (
            -row["pr_auc"],
            -row["recall"],
            row["brier_score"],
            row["false_alert_rate"],
        )
    )

    best_model_name = results[0]["model"]
    best_model = calibrated_models[
        best_model_name
    ]
    best_base_model = base_models[
        best_model_name
    ]
    best_threshold = float(
        thresholds[best_model_name][
            "threshold"
        ]
    )
    best_importance = importances[
        best_model_name
    ]

    training_ranges = feature_ranges(train)
    environment_ranges = (
        positive_environment_ranges(train)
    )

    feature_pattern_summary = {}

    for feature in HARVEST_CLASSIFIER_FEATURES:
        positive_values = pd.to_numeric(
            train.loc[
                train[TARGET_COLUMN].eq(1),
                feature,
            ],
            errors="coerce",
        ).dropna()

        negative_values = pd.to_numeric(
            train.loc[
                train[TARGET_COLUMN].eq(0),
                feature,
            ],
            errors="coerce",
        ).dropna()

        if (
            positive_values.empty
            or negative_values.empty
        ):
            continue

        feature_pattern_summary[feature] = {
            "positive_median": round(
                float(positive_values.median()),
                6,
            ),
            "negative_median": round(
                float(negative_values.median()),
                6,
            ),
        }

    metadata = {
        "model_version": (
            f"harvest_probability_"
            f"{HORIZON_HOURS}h_v1"
        ),
        "best_model": best_model_name,
        "target": TARGET_COLUMN,
        "target_mode": TARGET_MODE,
        "source_label_column": LABEL_COLUMN,
        "target_definition": (
            (
                f"Existing binary label "
                f"{LABEL_COLUMN}: harvest within "
                f"the next {HORIZON_HOURS} hours."
            )
            if TARGET_MODE == "precomputed"
            else (
                f"Generated from actual event rows: "
                f"harvest occurs after the current "
                f"row and within "
                f"{HORIZON_HOURS} hours."
            )
        ),
        "prediction_horizon_hours": (
            HORIZON_HOURS
        ),
        "decision_threshold": (
            best_threshold
        ),
        "threshold_selection": (
            thresholds[best_model_name]
        ),
        "training_source": str(DATA_PATH),
        "historical_source_timezone": (
            HISTORICAL_SOURCE_TIMEZONE
        ),
        "historical_feature_timezone": (
            FEATURE_TIMEZONE
        ),
        "deployment_timezone": os.getenv(
            "IOT_FEATURE_TIMEZONE",
            "Asia/Colombo",
        ),
        "split": {
            **boundaries,
            "train_rows": int(len(train)),
            "validation_rows": int(
                len(validation)
            ),
            "test_rows": int(len(test)),
            "class_summary": split_summary,
        },
        "class_distribution": {
            "all_rows": int(len(modelling)),
            "positive_rows": positive_count,
            "negative_rows": negative_count,
            "positive_rate": round(
                positive_count / len(modelling),
                6,
            ),
        },
        "features": (
            HARVEST_CLASSIFIER_FEATURES
        ),
        "training_feature_ranges": (
            training_ranges
        ),
        "positive_environment_ranges": (
            environment_ranges
        ),
        "feature_pattern_summary": (
            feature_pattern_summary
        ),
        "top_features": (
            best_importance[:15]
        ),
        "warning": (
            "The classifier is trained on "
            "historical data and must be "
            "locally validated using confirmed "
            "Sri Lankan harvest events."
        ),
    }

    joblib.dump(
        best_model,
        MODEL_DIR
        / "calibrated_harvest_classifier.joblib",
    )
    joblib.dump(
        best_base_model,
        MODEL_DIR
        / "best_harvest_base_model.joblib",
    )
    joblib.dump(
        calibrated_models,
        MODEL_DIR
        / "harvest_classifier_ensemble.joblib",
    )
    joblib.dump(
        HARVEST_CLASSIFIER_FEATURES,
        MODEL_DIR
        / "harvest_classifier_features.joblib",
    )

    with (
        MODEL_DIR
        / "harvest_classifier_metadata.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            metadata,
            handle,
            indent=2,
        )

    result_payload = {
        "best_model": best_model_name,
        "selection_rule": (
            "Highest test PR-AUC, then highest "
            "recall, then lowest Brier score and "
            "false-alert rate."
        ),
        "results": results,
        "metadata": metadata,
    }

    with (
        OUTPUT_DIR
        / "harvest_classifier_comparison.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            result_payload,
            handle,
            indent=2,
        )

    pd.DataFrame(results).to_csv(
        OUTPUT_DIR
        / "harvest_classifier_comparison.csv",
        index=False,
    )

    save_evaluation_plots(
        y_test=y_test,
        probability_by_model=(
            probability_by_model
        ),
        best_model_name=best_model_name,
        best_threshold=best_threshold,
        best_importance=best_importance,
        test_frame=test,
    )

    print(
        f"\nBest model: {best_model_name}"
    )
    print(
        f"Decision threshold: "
        f"{best_threshold:.4f}"
    )
    print(
        "Saved classifier artifacts in: "
        f"{MODEL_DIR}"
    )
    print(
        "Saved evaluation outputs in: "
        f"{OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()
