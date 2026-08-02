from pathlib import Path

import joblib
import numpy as np
import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parent.parent

MODEL_DIR = BACKEND_DIR / "models"
HARVEST_OUTPUT_DIR = BACKEND_DIR / "outputs" / "harvest"

BEST_MODEL_FILE = MODEL_DIR / "best_hui_model.joblib"
FEATURE_COLUMNS_FILE = MODEL_DIR / "hui_feature_columns.joblib"
HUI_DATASET_FILE = HARVEST_OUTPUT_DIR / "hui_dataset.csv"


def load_hui_model():
    """Load the selected HUI model and its feature-column list."""

    if not BEST_MODEL_FILE.exists():
        raise FileNotFoundError(
            f"Model file not found: {BEST_MODEL_FILE}"
        )

    model = joblib.load(BEST_MODEL_FILE)

    feature_columns = None

    if FEATURE_COLUMNS_FILE.exists():
        feature_columns = joblib.load(FEATURE_COLUMNS_FILE)

        if hasattr(feature_columns, "tolist"):
            feature_columns = feature_columns.tolist()

    return model, feature_columns


def get_sample_input():
    """Return one complete input row for the React prediction form."""

    if not HUI_DATASET_FILE.exists():
        raise FileNotFoundError(
            f"HUI dataset not found: {HUI_DATASET_FILE}"
        )

    sample_df = pd.read_csv(HUI_DATASET_FILE, nrows=1)

    if sample_df.empty:
        raise ValueError("The HUI dataset is empty.")

    _, feature_columns = load_hui_model()

    if feature_columns:
        missing_columns = [
            column
            for column in feature_columns
            if column not in sample_df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Dataset is missing model columns: {missing_columns}"
            )

        sample_df = sample_df[feature_columns]

    sample = sample_df.iloc[0].to_dict()

    return {
        key: make_json_safe(value)
        for key, value in sample.items()
    }


def predict_hui(payload):
    """Predict HUI from a JSON-compatible input dictionary."""

    model, feature_columns = load_hui_model()

    input_df = pd.DataFrame([payload])

    if feature_columns:
        missing_columns = [
            column
            for column in feature_columns
            if column not in input_df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {missing_columns}"
            )

        # Keep the same column order used during training.
        input_df = input_df[feature_columns]

    predicted_hui = float(model.predict(input_df)[0])
    predicted_hui = float(np.clip(predicted_hui, 0, 100))

    status = hui_to_status(predicted_hui)

    return {
        "predicted_hui": round(predicted_hui, 2),
        "harvest_status": status,
        "recommendation": get_recommendation(status),
        "disclaimer": (
            "This result is based on a proxy HUI target. "
            "Confirm the final harvesting decision with a beekeeper."
        )
    }


def hui_to_status(hui):
    if hui <= 30:
        return "Not Ready"

    if hui <= 60:
        return "Approaching"

    if hui <= 80:
        return "Ready"

    return "Optimal/Emergency"


def get_recommendation(status):
    recommendations = {
        "Not Ready": (
            "The hive is not ready. Continue monitoring."
        ),
        "Approaching": (
            "Harvest conditions are approaching. Monitor closely."
        ),
        "Ready": (
            "Plan harvesting within the next 3–5 days."
        ),
        "Optimal/Emergency": (
            "Harvest immediately or within the next 1–2 days."
        )
    }

    return recommendations[status]


def make_json_safe(value):
    """Convert Pandas and NumPy values into JSON-compatible values."""

    if pd.isna(value):
        return None

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        return float(value)

    if isinstance(value, np.bool_):
        return bool(value)

    return value