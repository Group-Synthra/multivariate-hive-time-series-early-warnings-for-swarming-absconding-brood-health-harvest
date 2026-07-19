"""
=========================================================
MODEL COMPARISON
=========================================================
"""

import os
import json
import pandas as pd
import matplotlib.pyplot as plt

from config import *

print("="*70)
print("MODEL COMPARISON")
print("="*70)

# ---------------------------------------------------
# Metric Files
# ---------------------------------------------------

RF_FILE = os.path.join(
    OUTPUT_FOLDER,
    "rf_metrics.json"
)

XGB_FILE = os.path.join(
    OUTPUT_FOLDER,
    "xgb_metrics.json"
)

LSTM_FILE = os.path.join(
    OUTPUT_FOLDER,
    "lstm_metrics.json"
)

print("\nLoading metric files...")

with open(RF_FILE, "r") as f:
    rf_metrics = json.load(f)

with open(XGB_FILE, "r") as f:
    xgb_metrics = json.load(f)

with open(LSTM_FILE, "r") as f:
    lstm_metrics = json.load(f)

print("Metric files loaded successfully.")



# ---------------------------------------------------
# Create Comparison DataFrame
# ---------------------------------------------------

comparison = pd.DataFrame([

    rf_metrics,

    xgb_metrics,

    lstm_metrics

])

comparison = comparison[

    [

        "Model",

        "Accuracy",

        "Precision",

        "Recall",

        "F1-Score"

    ]

]

comparison = comparison.sort_values(

    by="F1-Score",

    ascending=False

)

comparison = comparison.reset_index(drop=True)

print("\nComparison Table")

print(comparison)

# ---------------------------------------------------
# Best Model
# ---------------------------------------------------

best_model = comparison.iloc[0]

print("\n" + "="*70)
print("BEST MODEL")
print("="*70)

print(best_model)

best_model_path = os.path.join(

    OUTPUT_FOLDER,

    "best_model.json"

)

with open(best_model_path, "w") as f:

    json.dump(

        best_model.to_dict(),

        f,

        indent=4

    )

print("\nBest model saved.")

print(best_model_path)


comparison_csv = os.path.join(

    OUTPUT_FOLDER,

    "model_comparison.csv"

)

comparison_json = os.path.join(

    OUTPUT_FOLDER,

    "model_comparison.json"

)

comparison.to_csv(

    comparison_csv,

    index=False

)

comparison.to_json(

    comparison_json,

    orient="records",

    indent=4

)

print("\nComparison files saved.")

comparison_plot = comparison.set_index("Model")[

    [

        "Accuracy",

        "Precision",

        "Recall",

        "F1-Score"

    ]

]

comparison_plot.plot(

    kind="bar",

    figsize=(10,6)

)

plt.title("Model Performance Comparison")

plt.ylabel("Score")

plt.tight_layout()

plot_path = os.path.join(

    OUTPUT_FOLDER,

    "model_comparison.png"

)

plt.savefig(plot_path)

plt.close()

print("Comparison chart saved.")