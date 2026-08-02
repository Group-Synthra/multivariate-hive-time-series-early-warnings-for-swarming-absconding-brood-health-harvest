# """Harvest-module EDA and proxy HUI generation.

# Run from the project root:
#     python backend/eda/eda_analysis_harvest.py

# Input:
#     backend/data/hive_data_with_features.csv

# Outputs:
#     backend/outputs/harvest/harvest_eda_summary.json
#     backend/outputs/harvest/hui_dataset.csv
#     backend/outputs/harvest/*.png

# Important: HUI is an expert-rule proxy target, not observed beekeeper ground truth.
# """

# from __future__ import annotations

# import json
# from pathlib import Path

# import matplotlib.pyplot as plt
# import numpy as np
# import pandas as pd

# PROJECT_ROOT = Path(__file__).resolve().parents[2]
# DATA_PATH = PROJECT_ROOT / "backend" / "data" / "hive_data_with_features.csv"
# OUTPUT_DIR = PROJECT_ROOT / "backend" / "outputs" / "harvest"
# OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# REQUIRED_COLUMNS = {
#     "timestamp",
#     "hive_id",
#     "internal_temperature_c",
#     "internal_humidity_pct",
#     "co2_ppm",
#     "hive_weight_kg",
#     "external_temperature_c",
#     "external_humidity_pct",
#     "rainfall_mm_hour",
#     "wind_speed_mps",
#     "nectar_flow_season_proxy",
#     "dearth_season_proxy",
#     "monsoon_rain_period_proxy",
#     "brood_health_score_0_100",
# }

# def create_hive_harvest_analysis(df, output_dir):
#     """
#     Generate per-hive harvesting EDA information for the React dashboard.

#     Expected columns:
#     - hive
#     - timestamp
#     - hive_weight_kg
#     - internal_humidity_pct
#     - rainfall_mm_hour
#     - harvest_urgency_index_0_100
#     """

#     data = df.copy()

#     # Support either "hive" or "hive_id"
#     if "hive" in data.columns:
#         hive_column = "hive"
#     elif "hive_id" in data.columns:
#         hive_column = "hive_id"
#     else:
#         raise ValueError("Dataset must contain 'hive' or 'hive_id'.")

#     weight_column = "hive_weight_kg"

#     if weight_column not in data.columns:
#         raise ValueError(
#             f"Required column not found: {weight_column}"
#         )

#     data["timestamp"] = pd.to_datetime(
#         data["timestamp"],
#         errors="coerce"
#     )

#     data = data.dropna(
#         subset=["timestamp", hive_column, weight_column]
#     )

#     data = data.sort_values(
#         [hive_column, "timestamp"]
#     )

#     # Weight differences
#     data["weight_change_1h"] = (
#         data.groupby(hive_column)[weight_column]
#         .diff()
#     )

#     data["weight_change_24h"] = (
#         data.groupby(hive_column)[weight_column]
#         .diff(24)
#     )

#     # Rolling variability: lower value means more stable weight
#     data["weight_std_24h"] = (
#         data.groupby(hive_column)[weight_column]
#         .transform(
#             lambda series: series.rolling(
#                 24,
#                 min_periods=6
#             ).std()
#         )
#     )

#     # Plateau rule:
#     # - Hive is close to its recent maximum weight
#     # - Weight variability is small
#     # - Weight change is not strongly increasing/decreasing
#     rolling_max = (
#         data.groupby(hive_column)[weight_column]
#         .transform(
#             lambda series: series.rolling(
#                 168,
#                 min_periods=24
#             ).max()
#         )
#     )

#     data["near_recent_max"] = (
#         data[weight_column] >= rolling_max * 0.95
#     )

#     data["stable_weight"] = (
#         data["weight_std_24h"] <= 0.75
#     )

#     data["small_weight_change"] = (
#         data["weight_change_24h"].abs() <= 1.5
#     )

#     data["plateau_detected"] = (
#         data["near_recent_max"]
#         & data["stable_weight"]
#         & data["small_weight_change"]
#     )

#     # Possible harvest/extraction event:
#     # large sudden weight reduction
#     data["harvest_drop_detected"] = (
#         data["weight_change_1h"] <= -10
#     )

#     hive_analysis = []

#     for hive_id, hive_df in data.groupby(hive_column):
#         hive_df = hive_df.sort_values("timestamp")

#         latest = hive_df.iloc[-1]

#         current_weight = float(latest[weight_column])
#         maximum_weight = float(hive_df[weight_column].max())
#         minimum_weight = float(hive_df[weight_column].min())

#         recent_24h_change = latest.get(
#             "weight_change_24h",
#             np.nan
#         )

#         if pd.isna(recent_24h_change):
#             recent_24h_change = 0.0

#         plateau_rows = hive_df[
#             hive_df["plateau_detected"]
#         ]

#         plateau_detected = not plateau_rows.empty

#         plateau_start = None
#         plateau_end = None

#         if plateau_detected:
#             latest_plateau_group = plateau_rows.tail(48)

#             plateau_start = (
#                 latest_plateau_group["timestamp"]
#                 .min()
#                 .isoformat()
#             )

#             plateau_end = (
#                 latest_plateau_group["timestamp"]
#                 .max()
#                 .isoformat()
#             )

#         harvest_count = int(
#             hive_df["harvest_drop_detected"].sum()
#         )

#         current_hui = None

#         if "harvest_urgency_index_0_100" in hive_df.columns:
#             current_hui = float(
#                 latest["harvest_urgency_index_0_100"]
#             )

#         status = hui_to_status(current_hui)

#         # Reduce number of chart points to keep React responsive.
#         chart_df = hive_df.tail(1000).copy()

#         chart_data = []

#         for _, row in chart_df.iterrows():
#             chart_data.append({
#                 "timestamp": row["timestamp"].isoformat(),
#                 "weight": round(
#                     float(row[weight_column]),
#                     3
#                 ),
#                 "weight_change_24h": (
#                     None
#                     if pd.isna(row["weight_change_24h"])
#                     else round(
#                         float(row["weight_change_24h"]),
#                         3
#                     )
#                 ),
#                 "plateau_detected": bool(
#                     row["plateau_detected"]
#                 ),
#                 "harvest_drop_detected": bool(
#                     row["harvest_drop_detected"]
#                 )
#             })

#         hive_analysis.append({
#             "hive": str(hive_id),
#             "current_weight": round(current_weight, 2),
#             "maximum_weight": round(maximum_weight, 2),
#             "minimum_weight": round(minimum_weight, 2),
#             "weight_change_24h": round(
#                 float(recent_24h_change),
#                 2
#             ),
#             "current_hui": (
#                 None
#                 if current_hui is None
#                 else round(current_hui, 2)
#             ),
#             "status": status,
#             "plateau_detected": plateau_detected,
#             "plateau_start": plateau_start,
#             "plateau_end": plateau_end,
#             "historical_harvest_count": harvest_count,
#             "latest_timestamp": (
#                 latest["timestamp"].isoformat()
#             ),
#             "chart_data": chart_data
#         })

#     # Sort high-HUI hives first
#     hive_analysis.sort(
#         key=lambda item: (
#             item["current_hui"]
#             if item["current_hui"] is not None
#             else -1
#         ),
#         reverse=True
#     )

#     output = {
#         "total_hives": len(hive_analysis),
#         "plateau_hives": sum(
#             item["plateau_detected"]
#             for item in hive_analysis
#         ),
#         "ready_hives": sum(
#             item["status"] in {
#                 "Ready",
#                 "Optimal/Emergency"
#             }
#             for item in hive_analysis
#         ),
#         "hives": hive_analysis
#     }

#     output_path = (
#         Path(output_dir)
#         / "harvest_hive_analysis.json"
#     )

#     output_path.parent.mkdir(
#         parents=True,
#         exist_ok=True
#     )

#     with open(
#         output_path,
#         "w",
#         encoding="utf-8"
#     ) as file:
#         json.dump(
#             output,
#             file,
#             indent=2
#         )

#     print(
#         f"Saved hive harvesting analysis: {output_path}"
#     )

#     return output


# def hui_to_status(hui):
#     if hui is None:
#         return "Unknown"

#     if hui <= 30:
#         return "Not Ready"

#     if hui <= 60:
#         return "Approaching"

#     if hui <= 80:
#         return "Ready"

#     return "Optimal/Emergency"

# def robust_minmax(series: pd.Series, lower_q: float = 0.01, upper_q: float = 0.99) -> pd.Series:
#     """Scale to 0..1 after clipping extreme values to robust quantiles."""
#     numeric = pd.to_numeric(series, errors="coerce")
#     low = numeric.quantile(lower_q)
#     high = numeric.quantile(upper_q)
#     if pd.isna(low) or pd.isna(high) or np.isclose(low, high):
#         return pd.Series(np.zeros(len(series)), index=series.index, dtype=float)
#     return ((numeric.clip(low, high) - low) / (high - low)).clip(0, 1)


# def triangular_suitability(series: pd.Series, ideal: float, tolerance: float) -> pd.Series:
#     """Return 1 at the ideal and linearly reduce to 0 at ideal +/- tolerance."""
#     numeric = pd.to_numeric(series, errors="coerce")
#     return (1 - (numeric - ideal).abs() / tolerance).clip(0, 1)


# def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
#     """Create hive-level weight trend and stability features without future data."""
#     data = df.sort_values(["hive_id", "timestamp"]).copy()
#     group = data.groupby("hive_id", group_keys=False)

#     # Hourly data: 24 rows ~= 24h and 72 rows ~= 72h.
#     data["weight_change_24h_kg"] = group["hive_weight_kg"].diff(24)
#     data["weight_change_72h_kg"] = group["hive_weight_kg"].diff(72)
#     data["weight_std_24h_kg"] = (
#         group["hive_weight_kg"]
#         .rolling(window=24, min_periods=6)
#         .std()
#         .reset_index(level=0, drop=True)
#     )

#     for column in ["weight_change_24h_kg", "weight_change_72h_kg", "weight_std_24h_kg"]:
#         data[column] = data[column].fillna(0.0)

#     return data


# def generate_hui(df: pd.DataFrame) -> pd.DataFrame:
#     """Generate an explainable 0..100 Harvest Urgency Index proxy.

#     Positive components (sum to 0.80):
#       - Current hive weight: 0.25
#       - 72-hour weight gain: 0.15
#       - Weight stability/plateau: 0.10
#       - Nectar flow: 0.10
#       - Brood health: 0.10
#       - Internal temperature suitability: 0.05
#       - Internal humidity suitability: 0.05

#     Penalties (maximum total 0.20):
#       - Rain: 0.05
#       - Wind: 0.03
#       - CO2: 0.04
#       - Dearth season: 0.04
#       - Monsoon period: 0.04

#     The raw score is multiplied by 100 and clipped to 0..100.
#     """
#     data = add_temporal_features(df)

#     weight_score = robust_minmax(data["hive_weight_kg"])
#     weight_gain_score = robust_minmax(data["weight_change_72h_kg"])
#     # Stable weight after accumulation can indicate capped stores; lower variability is better.
#     weight_stability_score = 1 - robust_minmax(data["weight_std_24h_kg"])
#     brood_score = pd.to_numeric(data["brood_health_score_0_100"], errors="coerce").fillna(0).clip(0, 100) / 100
#     nectar_score = pd.to_numeric(data["nectar_flow_season_proxy"], errors="coerce").fillna(0).clip(0, 1)

#     temp_score = triangular_suitability(data["internal_temperature_c"], ideal=35.0, tolerance=5.0)
#     humidity_score = triangular_suitability(data["internal_humidity_pct"], ideal=60.0, tolerance=25.0)

#     rain_penalty = robust_minmax(data["rainfall_mm_hour"])
#     wind_penalty = robust_minmax(data["wind_speed_mps"])
#     co2_penalty = robust_minmax(data["co2_ppm"])
#     dearth_penalty = pd.to_numeric(data["dearth_season_proxy"], errors="coerce").fillna(0).clip(0, 1)
#     monsoon_penalty = pd.to_numeric(data["monsoon_rain_period_proxy"], errors="coerce").fillna(0).clip(0, 1)

#     positive = (
#         0.25 * weight_score
#         + 0.15 * weight_gain_score
#         + 0.10 * weight_stability_score
#         + 0.10 * nectar_score
#         + 0.10 * brood_score
#         + 0.05 * temp_score
#         + 0.05 * humidity_score
#     )
#     penalties = (
#         0.05 * rain_penalty
#         + 0.03 * wind_penalty
#         + 0.04 * co2_penalty
#         + 0.04 * dearth_penalty
#         + 0.04 * monsoon_penalty
#     )

#     data["harvest_urgency_index_0_100"] = (100 * (positive - penalties)).clip(0, 100).round(3)
#     data["hui_status"] = pd.cut(
#         data["harvest_urgency_index_0_100"],
#         bins=[-np.inf, 30, 60, 80, np.inf],
#         labels=["Not Ready", "Approaching", "Ready", "Optimal/Emergency"],
#     ).astype(str)
#     data["hui_generation_method"] = "expert_rule_proxy_v2_temporal"
#     return data


# def save_plots(data: pd.DataFrame) -> None:
#     plt.figure(figsize=(9, 5))
#     data["harvest_urgency_index_0_100"].hist(bins=40)
#     plt.title("Generated Harvest Urgency Index Distribution")
#     plt.xlabel("HUI (0-100)")
#     plt.ylabel("Rows")
#     plt.tight_layout()
#     plt.savefig(OUTPUT_DIR / "hui_distribution.png", dpi=160)
#     plt.close()

#     status_counts = data["hui_status"].value_counts().reindex(
#         ["Not Ready", "Approaching", "Ready", "Optimal/Emergency"], fill_value=0
#     )
#     plt.figure(figsize=(9, 5))
#     status_counts.plot(kind="bar")
#     plt.title("HUI Status Distribution")
#     plt.xlabel("Status")
#     plt.ylabel("Rows")
#     plt.xticks(rotation=20)
#     plt.tight_layout()
#     plt.savefig(OUTPUT_DIR / "hui_status_distribution.png", dpi=160)
#     plt.close()


# def main() -> None:
#     if not DATA_PATH.exists():
#         raise FileNotFoundError(
#             f"Dataset not found: {DATA_PATH}\n"
#             "Copy da.csv to backend/data/hive_data_with_features.csv first."
#         )

#     print(f"Loading: {DATA_PATH}")
#     df = pd.read_csv(DATA_PATH)
#     missing = sorted(REQUIRED_COLUMNS - set(df.columns))
#     if missing:
#         raise ValueError(f"Dataset is missing required columns: {missing}")

#     df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
#     if df["timestamp"].isna().any():
#         raise ValueError("Some timestamp values could not be parsed.")

#     data = generate_hui(df)
#     create_hive_harvest_analysis(
#         df=data,
#         output_dir=OUTPUT_DIR
#     )
#     output_csv = OUTPUT_DIR / "hui_dataset.csv"
#     data.to_csv(output_csv, index=False)
#     save_plots(data)

#     summary = {
#         "rows": int(len(data)),
#         "columns": int(len(data.columns)),
#         "hives": int(data["hive_id"].nunique()),
#         "start_time": data["timestamp"].min().isoformat(),
#         "end_time": data["timestamp"].max().isoformat(),
#         "hui": {
#             "mean": round(float(data["harvest_urgency_index_0_100"].mean()), 3),
#             "std": round(float(data["harvest_urgency_index_0_100"].std()), 3),
#             "min": round(float(data["harvest_urgency_index_0_100"].min()), 3),
#             "max": round(float(data["harvest_urgency_index_0_100"].max()), 3),
#         },
#         "status_counts": {k: int(v) for k, v in data["hui_status"].value_counts().items()},
#         "method": "expert_rule_proxy_v2_temporal",
#         "warning": "Proxy HUI; not beekeeper-confirmed ground truth.",
#     }
#     with (OUTPUT_DIR / "harvest_eda_summary.json").open("w", encoding="utf-8") as handle:
#         json.dump(summary, handle, indent=2)

#     print(f"Saved HUI dataset: {output_csv}")
#     print(f"Saved outputs in: {OUTPUT_DIR}")


# if __name__ == "__main__":
#     main()






"""Complete harvest-module EDA and proxy-HUI generation pipeline.

Run from the project root:
    python backend/eda/eda_analysis_harvest.py

Input:
    backend/data/hive_data_with_features.csv

Main outputs:
    backend/outputs/harvest/harvest_eda_summary.json
    backend/outputs/harvest/dataset_level_eda_summary.json
    backend/outputs/harvest/harvest_hive_analysis.json
    backend/outputs/harvest/hui_dataset.csv
    backend/outputs/harvest/*.csv
    backend/outputs/harvest/*.png
    backend/outputs/harvest/per_hive_weight_plots/*.png

Important:
    The Harvest Urgency Index (HUI) is an explainable expert-rule proxy.
    It is not observed or beekeeper-confirmed harvest ground truth.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# -----------------------------------------------------------------------------
# Paths and configuration
# -----------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "backend" / "data" / "hive_data_with_features.csv"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "outputs" / "harvest"
PER_HIVE_PLOT_DIR = OUTPUT_DIR / "per_hive_weight_plots"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PER_HIVE_PLOT_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_COLUMNS = {
    "timestamp",
    "hive_id",
    "internal_temperature_c",
    "internal_humidity_pct",
    "co2_ppm",
    "hive_weight_kg",
    "external_temperature_c",
    "external_humidity_pct",
    "rainfall_mm_hour",
    "wind_speed_mps",
    "nectar_flow_season_proxy",
    "dearth_season_proxy",
    "monsoon_rain_period_proxy",
    "brood_health_score_0_100",
}

RAW_SENSOR_COLUMNS = [
    "internal_temperature_c",
    "internal_humidity_pct",
    "co2_ppm",
    "hive_weight_kg",
    "external_temperature_c",
    "external_humidity_pct",
    "rainfall_mm_hour",
    "wind_speed_mps",
]

ENVIRONMENTAL_COLUMNS = [
    "internal_temperature_c",
    "internal_humidity_pct",
    "co2_ppm",
    "external_temperature_c",
    "external_humidity_pct",
    "rainfall_mm_hour",
    "wind_speed_mps",
]

STATUS_ORDER = [
    "Not Ready",
    "Approaching",
    "Ready",
    "Optimal/Emergency",
]

# These are screening rules for exploratory analysis only.
# A sudden drop is a potential extraction/harvest event, not a confirmed event.
POTENTIAL_HARVEST_DROP_THRESHOLD_KG = -10.0
PLATEAU_WEIGHT_STD_THRESHOLD_KG = 0.75
PLATEAU_24H_CHANGE_THRESHOLD_KG = 1.50
PLATEAU_RECENT_MAX_RATIO = 0.95

# Limit plotting samples so that a large dataset remains responsive.
MAX_HISTOGRAM_ROWS = 100_000
MAX_SCATTER_ROWS = 50_000
MAX_PER_HIVE_CHART_ROWS = 2_000


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON file with indentation and UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def make_json_safe(value: Any) -> Any:
    """Convert common pandas and NumPy values into JSON-compatible values."""
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        return float(value)

    if isinstance(value, np.bool_):
        return bool(value)

    return value


def safe_filename(value: Any) -> str:
    """Create a filesystem-safe label for hive IDs and plot names."""
    text = str(value).strip()
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text)
    return text or "unknown"


def save_placeholder_plot(path: Path, title: str, message: str) -> None:
    """Save an informative image when a requested plot has no valid data."""
    plt.figure(figsize=(10, 5))
    plt.text(
        0.5,
        0.5,
        message,
        horizontalalignment="center",
        verticalalignment="center",
        transform=plt.gca().transAxes,
    )
    plt.title(title)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def sample_for_plot(data: pd.DataFrame, maximum_rows: int) -> pd.DataFrame:
    """Return a deterministic sample for plotting large datasets."""
    if len(data) <= maximum_rows:
        return data.copy()
    return data.sample(n=maximum_rows, random_state=42).copy()


# -----------------------------------------------------------------------------
# Data loading and validation
# -----------------------------------------------------------------------------


def load_and_validate_data() -> pd.DataFrame:
    """Load the harvest dataset and validate required fields and timestamps."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}\n"
            "Copy the prepared hive dataset to "
            "backend/data/hive_data_with_features.csv first."
        )

    print(f"Loading: {DATA_PATH}")
    data = pd.read_csv(DATA_PATH)

    missing_columns = sorted(REQUIRED_COLUMNS - set(data.columns))
    if missing_columns:
        raise ValueError(f"Dataset is missing required columns: {missing_columns}")

    data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce")
    invalid_timestamp_count = int(data["timestamp"].isna().sum())

    if invalid_timestamp_count:
        raise ValueError(
            f"{invalid_timestamp_count} timestamp values could not be parsed. "
            "Correct or remove those rows before continuing."
        )

    # Keep original duplicate rows for the data-quality report. They are removed
    # later before temporal feature calculation.
    return data


def prepare_analysis_data(data: pd.DataFrame) -> pd.DataFrame:
    """Create the clean, ordered copy used for temporal calculations."""
    prepared = data.copy()

    # Keep the last record when the same hive and timestamp occur more than once.
    prepared = prepared.drop_duplicates(
        subset=["hive_id", "timestamp"],
        keep="last",
    )

    prepared = prepared.sort_values(
        ["hive_id", "timestamp"]
    ).reset_index(drop=True)

    return add_calendar_features(prepared)


# -----------------------------------------------------------------------------
# Dataset-level EDA
# -----------------------------------------------------------------------------


def create_dataset_level_eda(
    data: pd.DataFrame,
    output_dir: Path,
) -> dict[str, Any]:
    """Perform dataset coverage, quality, missingness and interval analysis."""
    frame = data.copy().sort_values(["hive_id", "timestamp"])

    duplicate_mask = frame.duplicated(
        subset=["hive_id", "timestamp"],
        keep=False,
    )
    duplicate_rows = int(duplicate_mask.sum())
    duplicate_groups = int(
        frame.loc[duplicate_mask, ["hive_id", "timestamp"]]
        .drop_duplicates()
        .shape[0]
    )

    hive_coverage = (
        frame.groupby("hive_id")
        .agg(
            records=("timestamp", "size"),
            start_time=("timestamp", "min"),
            end_time=("timestamp", "max"),
        )
        .reset_index()
    )

    hive_coverage["duration_hours"] = (
        hive_coverage["end_time"] - hive_coverage["start_time"]
    ).dt.total_seconds() / 3600
    hive_coverage["duration_days"] = hive_coverage["duration_hours"] / 24
    hive_coverage["expected_hourly_records"] = (
        hive_coverage["duration_hours"].round().astype(int) + 1
    )
    hive_coverage["hourly_coverage_pct"] = (
        100
        * hive_coverage["records"]
        / hive_coverage["expected_hourly_records"].replace(0, np.nan)
    ).clip(upper=100)

    hive_coverage.to_csv(
        output_dir / "hive_date_coverage.csv",
        index=False,
    )

    frame["sampling_interval_hours"] = (
        frame.groupby("hive_id")["timestamp"]
        .diff()
        .dt.total_seconds()
        / 3600
    )

    valid_intervals = frame.loc[
        frame["sampling_interval_hours"].notna()
        & (frame["sampling_interval_hours"] >= 0)
    ].copy()

    if not valid_intervals.empty:
        interval_summary = (
            valid_intervals.groupby("hive_id")["sampling_interval_hours"]
            .agg(
                interval_count="count",
                minimum_interval_hours="min",
                median_interval_hours="median",
                mean_interval_hours="mean",
                maximum_interval_hours="max",
            )
            .reset_index()
        )

        irregular = valid_intervals.assign(
            irregular_interval=~np.isclose(
                valid_intervals["sampling_interval_hours"],
                1.0,
                atol=0.01,
            )
        )

        irregular_summary = (
            irregular.groupby("hive_id")["irregular_interval"]
            .mean()
            .mul(100)
            .reset_index(name="irregular_interval_pct")
        )

        interval_summary = interval_summary.merge(
            irregular_summary,
            on="hive_id",
            how="left",
        )
    else:
        interval_summary = pd.DataFrame(
            columns=[
                "hive_id",
                "interval_count",
                "minimum_interval_hours",
                "median_interval_hours",
                "mean_interval_hours",
                "maximum_interval_hours",
                "irregular_interval_pct",
            ]
        )

    interval_summary.to_csv(
        output_dir / "sampling_interval_summary.csv",
        index=False,
    )

    missing_summary = pd.DataFrame(
        {
            "column": frame.columns,
            "missing_count": frame.isna().sum().values,
            "missing_percentage": frame.isna().mean().mul(100).values,
        }
    ).sort_values("missing_percentage", ascending=False)

    missing_summary.to_csv(
        output_dir / "missing_value_summary.csv",
        index=False,
    )

    available_sensors = [
        column for column in RAW_SENSOR_COLUMNS if column in frame.columns
    ]

    sensor_statistics = (
        frame[available_sensors]
        .apply(pd.to_numeric, errors="coerce")
        .describe(
            percentiles=[0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]
        )
        .transpose()
        .reset_index()
        .rename(columns={"index": "variable"})
    )

    sensor_statistics.to_csv(
        output_dir / "sensor_descriptive_statistics.csv",
        index=False,
    )

    calendar_frame = add_calendar_features(frame)

    monthly_distribution = (
        calendar_frame.groupby(["year", "month"])
        .size()
        .reset_index(name="records")
    )
    monthly_distribution.to_csv(
        output_dir / "monthly_record_distribution.csv",
        index=False,
    )

    if "apiary_season" in calendar_frame.columns:
        seasonal_distribution = (
            calendar_frame["apiary_season"]
            .fillna("Unknown")
            .astype(str)
            .value_counts()
            .rename_axis("season")
            .reset_index(name="records")
        )
    else:
        seasonal_distribution = pd.DataFrame(
            columns=["season", "records"]
        )

    seasonal_distribution.to_csv(
        output_dir / "seasonal_record_distribution.csv",
        index=False,
    )

    # Records per hive
    records_plot = hive_coverage.sort_values("records", ascending=False)
    plt.figure(figsize=(13, 6))
    plt.bar(
        records_plot["hive_id"].astype(str),
        records_plot["records"],
    )
    plt.title("Number of Records per Hive")
    plt.xlabel("Hive ID")
    plt.ylabel("Number of Records")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(output_dir / "records_per_hive.png", dpi=160)
    plt.close()

    # Date coverage per hive
    coverage_plot = hive_coverage.sort_values("start_time").reset_index(drop=True)
    plt.figure(figsize=(13, max(6, len(coverage_plot) * 0.22)))
    y_positions = np.arange(len(coverage_plot))
    durations = (
        coverage_plot["end_time"] - coverage_plot["start_time"]
    ).dt.total_seconds() / 86400
    starts = coverage_plot["start_time"].map(pd.Timestamp.toordinal)
    plt.barh(y_positions, durations, left=starts)
    plt.yticks(y_positions, coverage_plot["hive_id"].astype(str))
    tick_positions = plt.gca().get_xticks()
    tick_labels = []
    for tick in tick_positions:
        try:
            tick_labels.append(pd.Timestamp.fromordinal(int(tick)).strftime("%Y-%m-%d"))
        except (ValueError, OverflowError):
            tick_labels.append("")
    plt.gca().set_xticks(tick_positions)
    plt.gca().set_xticklabels(tick_labels, rotation=30, ha="right")
    plt.title("Date Coverage per Hive")
    plt.xlabel("Date")
    plt.ylabel("Hive ID")
    plt.tight_layout()
    plt.savefig(output_dir / "date_coverage_per_hive.png", dpi=160)
    plt.close()

    # Missing values
    missing_plot = missing_summary.loc[
        missing_summary["missing_count"] > 0
    ].copy()

    if missing_plot.empty:
        save_placeholder_plot(
            output_dir / "missing_value_distribution.png",
            "Missing Values by Variable",
            "No missing values detected.",
        )
    else:
        plt.figure(figsize=(11, max(5, len(missing_plot) * 0.35)))
        plt.barh(
            missing_plot["column"],
            missing_plot["missing_percentage"],
        )
        plt.title("Missing Values by Variable")
        plt.xlabel("Missing Values (%)")
        plt.ylabel("Variable")
        plt.tight_layout()
        plt.savefig(output_dir / "missing_value_distribution.png", dpi=160)
        plt.close()

    # Sampling interval distribution
    if valid_intervals.empty:
        save_placeholder_plot(
            output_dir / "sampling_interval_distribution.png",
            "Sampling-Interval Distribution",
            "No valid sampling intervals were available.",
        )
    else:
        interval_plot_data = valid_intervals[
            "sampling_interval_hours"
        ].clip(upper=24)
        plt.figure(figsize=(10, 6))
        plt.hist(interval_plot_data, bins=48)
        plt.title(
            "Sampling-Interval Distribution "
            "(Intervals Above 24 Hours Clipped)"
        )
        plt.xlabel("Sampling Interval (hours)")
        plt.ylabel("Frequency")
        plt.tight_layout()
        plt.savefig(output_dir / "sampling_interval_distribution.png", dpi=160)
        plt.close()

    # Monthly distribution
    month_counts = (
        calendar_frame.groupby("month")
        .size()
        .reindex(range(1, 13), fill_value=0)
    )
    plt.figure(figsize=(10, 6))
    plt.bar(month_counts.index, month_counts.values)
    plt.title("Record Distribution by Month")
    plt.xlabel("Month")
    plt.ylabel("Number of Records")
    plt.xticks(range(1, 13))
    plt.tight_layout()
    plt.savefig(output_dir / "monthly_distribution.png", dpi=160)
    plt.close()

    summary = {
        "rows_before_duplicate_removal": int(len(frame)),
        "columns": int(len(frame.columns)),
        "number_of_hives": int(frame["hive_id"].nunique()),
        "start_time": frame["timestamp"].min().isoformat(),
        "end_time": frame["timestamp"].max().isoformat(),
        "duplicate_hive_timestamp_rows": duplicate_rows,
        "duplicate_hive_timestamp_groups": duplicate_groups,
        "total_missing_values": int(frame.isna().sum().sum()),
        "overall_missing_percentage": round(
            float(frame.isna().sum().sum() / frame.size * 100),
            4,
        ),
        "median_sampling_interval_hours": (
            None
            if valid_intervals.empty
            else round(
                float(valid_intervals["sampling_interval_hours"].median()),
                4,
            )
        ),
        "minimum_records_per_hive": int(hive_coverage["records"].min()),
        "maximum_records_per_hive": int(hive_coverage["records"].max()),
        "median_records_per_hive": round(
            float(hive_coverage["records"].median()),
            2,
        ),
        "minimum_hourly_coverage_pct": round(
            float(hive_coverage["hourly_coverage_pct"].min()),
            2,
        ),
        "median_hourly_coverage_pct": round(
            float(hive_coverage["hourly_coverage_pct"].median()),
            2,
        ),
    }

    write_json(output_dir / "dataset_level_eda_summary.json", summary)
    return summary


# -----------------------------------------------------------------------------
# Calendar and temporal feature engineering used by EDA and HUI
# -----------------------------------------------------------------------------


def add_calendar_features(data: pd.DataFrame) -> pd.DataFrame:
    """Add calendar variables used by EDA, model training and prediction APIs."""
    frame = data.copy()
    timestamp = pd.to_datetime(frame["timestamp"], errors="coerce")

    if timestamp.isna().any():
        raise ValueError("Invalid timestamp values were found.")

    frame["year"] = timestamp.dt.year
    frame["month"] = timestamp.dt.month
    frame["day_of_week"] = timestamp.dt.dayofweek
    frame["hour"] = timestamp.dt.hour
    frame["date"] = timestamp.dt.date.astype(str)

    return frame


def add_temporal_features(data: pd.DataFrame) -> pd.DataFrame:
    """Create causal hive-level weight trend and stability features."""
    frame = data.sort_values(["hive_id", "timestamp"]).copy()
    group = frame.groupby("hive_id", group_keys=False)

    # These row-based windows assume approximately hourly records. The dataset-
    # level interval report must be reviewed before interpreting them as exact
    # 24-hour and 72-hour periods.
    frame["weight_change_1h_kg"] = group["hive_weight_kg"].diff(1)
    frame["weight_change_24h_kg"] = group["hive_weight_kg"].diff(24)
    frame["weight_change_72h_kg"] = group["hive_weight_kg"].diff(72)

    frame["weight_mean_24h_kg"] = (
        group["hive_weight_kg"]
        .rolling(window=24, min_periods=6)
        .mean()
        .reset_index(level=0, drop=True)
    )

    frame["weight_std_24h_kg"] = (
        group["hive_weight_kg"]
        .rolling(window=24, min_periods=6)
        .std()
        .reset_index(level=0, drop=True)
    )

    frame["weight_mean_72h_kg"] = (
        group["hive_weight_kg"]
        .rolling(window=72, min_periods=12)
        .mean()
        .reset_index(level=0, drop=True)
    )

    frame["weight_std_72h_kg"] = (
        group["hive_weight_kg"]
        .rolling(window=72, min_periods=12)
        .std()
        .reset_index(level=0, drop=True)
    )

    frame["weight_slope_24h_kg_per_hour"] = (
        frame["weight_change_24h_kg"] / 24.0
    )

    frame["weight_acceleration_24h"] = (
        frame.groupby("hive_id")["weight_slope_24h_kg_per_hour"].diff(24)
        / 24.0
    )

    frame["rolling_max_7d_kg"] = (
        group["hive_weight_kg"]
        .rolling(window=168, min_periods=24)
        .max()
        .reset_index(level=0, drop=True)
    )

    frame["distance_from_7d_max_kg"] = (
        frame["rolling_max_7d_kg"] - frame["hive_weight_kg"]
    )

    frame["near_recent_max"] = (
        frame["hive_weight_kg"]
        >= frame["rolling_max_7d_kg"] * PLATEAU_RECENT_MAX_RATIO
    ).fillna(False)

    frame["stable_weight"] = (
        frame["weight_std_24h_kg"] <= PLATEAU_WEIGHT_STD_THRESHOLD_KG
    ).fillna(False)

    frame["small_weight_change"] = (
        frame["weight_change_24h_kg"].abs()
        <= PLATEAU_24H_CHANGE_THRESHOLD_KG
    ).fillna(False)

    frame["plateau_detected"] = (
        frame["near_recent_max"]
        & frame["stable_weight"]
        & frame["small_weight_change"]
    )

    frame["potential_harvest_drop_detected"] = (
        frame["weight_change_1h_kg"]
        <= POTENTIAL_HARVEST_DROP_THRESHOLD_KG
    ).fillna(False)

    # Backward-compatible alias used by the existing React dashboard.
    frame["harvest_drop_detected"] = frame[
        "potential_harvest_drop_detected"
    ]

    return frame


# -----------------------------------------------------------------------------
# Raw sensor distributions
# -----------------------------------------------------------------------------


def create_sensor_distribution_eda(
    data: pd.DataFrame,
    output_dir: Path,
) -> dict[str, Any]:
    """Create one distribution plot for every available raw sensor variable."""
    available_sensors = [
        column for column in RAW_SENSOR_COLUMNS if column in data.columns
    ]

    plot_frame = sample_for_plot(data[available_sensors], MAX_HISTOGRAM_ROWS)
    generated_plots: list[str] = []

    for column in available_sensors:
        values = pd.to_numeric(plot_frame[column], errors="coerce").dropna()
        filename = f"distribution_{safe_filename(column)}.png"
        path = output_dir / filename

        if values.empty:
            save_placeholder_plot(
                path,
                f"Distribution of {column}",
                "No valid numeric values were available.",
            )
        else:
            plt.figure(figsize=(9, 5))
            plt.hist(values, bins=50)
            plt.title(f"Distribution of {column}")
            plt.xlabel(column)
            plt.ylabel("Frequency")
            plt.tight_layout()
            plt.savefig(path, dpi=160)
            plt.close()

        generated_plots.append(filename)

    summary = {
        "sensor_variables": available_sensors,
        "number_of_sensor_distribution_plots": len(generated_plots),
        "plots": generated_plots,
    }
    write_json(output_dir / "sensor_distribution_eda_summary.json", summary)
    return summary


# -----------------------------------------------------------------------------
# Hive-weight EDA
# -----------------------------------------------------------------------------


def calculate_daily_weight_changes(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate first-to-last hive-weight change for each calendar day."""
    daily = (
        data.set_index("timestamp")
        .groupby("hive_id")["hive_weight_kg"]
        .resample("1D")
        .agg(["first", "last", "min", "max", "mean", "std", "count"])
        .reset_index()
    )

    daily = daily.loc[
        daily["first"].notna() & daily["last"].notna()
    ].copy()
    daily["daily_weight_change_kg"] = daily["last"] - daily["first"]
    return daily


def create_hive_weight_eda(
    data: pd.DataFrame,
    output_dir: Path,
    per_hive_plot_dir: Path,
) -> dict[str, Any]:
    """Create weight trends, rolling statistics, plateau and drop-event EDA."""
    frame = data.copy()
    daily = calculate_daily_weight_changes(frame)
    daily.to_csv(output_dir / "daily_hive_weight_summary.csv", index=False)

    weight_feature_columns = [
        "hive_id",
        "timestamp",
        "hive_weight_kg",
        "weight_change_1h_kg",
        "weight_change_24h_kg",
        "weight_change_72h_kg",
        "weight_mean_24h_kg",
        "weight_std_24h_kg",
        "weight_mean_72h_kg",
        "weight_std_72h_kg",
        "weight_slope_24h_kg_per_hour",
        "weight_acceleration_24h",
        "distance_from_7d_max_kg",
        "plateau_detected",
        "potential_harvest_drop_detected",
    ]

    frame[weight_feature_columns].to_csv(
        output_dir / "hive_weight_temporal_features.csv",
        index=False,
    )

    potential_events = frame.loc[
        frame["potential_harvest_drop_detected"],
        [
            "hive_id",
            "timestamp",
            "hive_weight_kg",
            "weight_change_1h_kg",
            "weight_change_24h_kg",
            "internal_temperature_c",
            "internal_humidity_pct",
            "co2_ppm",
            "rainfall_mm_hour",
            "wind_speed_mps",
        ],
    ].copy()

    potential_events.to_csv(
        output_dir / "potential_harvest_drop_events.csv",
        index=False,
    )

    plateau_periods: list[dict[str, Any]] = []
    per_hive_summary: list[dict[str, Any]] = []
    generated_hive_plots: list[str] = []

    for hive_id, hive_frame in frame.groupby("hive_id", sort=True):
        hive_frame = hive_frame.sort_values("timestamp").copy()

        # Identify consecutive plateau runs.
        flag = hive_frame["plateau_detected"].fillna(False).astype(bool)
        run_id = flag.ne(flag.shift(fill_value=False)).cumsum()

        for _, run in hive_frame.loc[flag].groupby(run_id[flag]):
            start_time = run["timestamp"].min()
            end_time = run["timestamp"].max()
            duration_hours = (
                end_time - start_time
            ).total_seconds() / 3600 + 1

            plateau_periods.append(
                {
                    "hive_id": str(hive_id),
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_hours": round(float(duration_hours), 2),
                    "mean_weight_kg": round(
                        float(run["hive_weight_kg"].mean()),
                        3,
                    ),
                    "mean_weight_std_24h_kg": round(
                        float(run["weight_std_24h_kg"].mean()),
                        3,
                    ),
                }
            )

        latest = hive_frame.iloc[-1]
        recent_24 = hive_frame.tail(24)
        current_plateau_ratio = float(
            recent_24["plateau_detected"].mean()
        ) if not recent_24.empty else 0.0
        current_plateau = current_plateau_ratio >= 0.75

        per_hive_summary.append(
            {
                "hive_id": str(hive_id),
                "records": int(len(hive_frame)),
                "start_time": hive_frame["timestamp"].min().isoformat(),
                "end_time": hive_frame["timestamp"].max().isoformat(),
                "minimum_weight_kg": round(
                    float(hive_frame["hive_weight_kg"].min()), 3
                ),
                "maximum_weight_kg": round(
                    float(hive_frame["hive_weight_kg"].max()), 3
                ),
                "mean_weight_kg": round(
                    float(hive_frame["hive_weight_kg"].mean()), 3
                ),
                "latest_weight_kg": round(float(latest["hive_weight_kg"]), 3),
                "latest_weight_change_24h_kg": make_json_safe(
                    round(float(latest["weight_change_24h_kg"]), 3)
                    if pd.notna(latest["weight_change_24h_kg"])
                    else None
                ),
                "current_plateau": current_plateau,
                "current_plateau_ratio_last_24_rows": round(
                    current_plateau_ratio, 3
                ),
                "potential_harvest_drop_count": int(
                    hive_frame["potential_harvest_drop_detected"].sum()
                ),
            }
        )

        # Use the most recent rows for readable dashboard-style charts.
        plot_frame = hive_frame.tail(MAX_PER_HIVE_CHART_ROWS)
        plot_path = per_hive_plot_dir / (
            f"hive_{safe_filename(hive_id)}_weight_timeseries.png"
        )

        plt.figure(figsize=(14, 6))
        plt.plot(
            plot_frame["timestamp"],
            plot_frame["hive_weight_kg"],
            label="Observed hive weight",
            linewidth=1.1,
        )
        plt.plot(
            plot_frame["timestamp"],
            plot_frame["weight_mean_24h_kg"],
            label="24-row rolling mean",
            linewidth=1.4,
        )

        plateau_points = plot_frame.loc[plot_frame["plateau_detected"]]
        if not plateau_points.empty:
            plt.scatter(
                plateau_points["timestamp"],
                plateau_points["hive_weight_kg"],
                label="Potential plateau",
                s=12,
            )

        drop_points = plot_frame.loc[
            plot_frame["potential_harvest_drop_detected"]
        ]
        if not drop_points.empty:
            plt.scatter(
                drop_points["timestamp"],
                drop_points["hive_weight_kg"],
                label="Potential sudden weight-drop event",
                marker="x",
                s=45,
            )

        plt.title(f"Hive Weight over Time — Hive {hive_id}")
        plt.xlabel("Timestamp")
        plt.ylabel("Hive Weight (kg)")
        plt.legend()
        plt.tight_layout()
        plt.savefig(plot_path, dpi=160)
        plt.close()
        generated_hive_plots.append(plot_path.name)

    pd.DataFrame(plateau_periods).to_csv(
        output_dir / "potential_plateau_periods.csv",
        index=False,
    )
    pd.DataFrame(per_hive_summary).to_csv(
        output_dir / "hive_weight_summary.csv",
        index=False,
    )

    # Daily weight-change distribution
    daily_change_values = pd.to_numeric(
        daily["daily_weight_change_kg"], errors="coerce"
    ).dropna()

    if daily_change_values.empty:
        save_placeholder_plot(
            output_dir / "daily_weight_change_distribution.png",
            "Daily Hive-Weight Change Distribution",
            "No valid daily weight changes were available.",
        )
    else:
        lower = daily_change_values.quantile(0.01)
        upper = daily_change_values.quantile(0.99)
        plt.figure(figsize=(10, 6))
        plt.hist(daily_change_values.clip(lower, upper), bins=60)
        plt.title("Daily Hive-Weight Change Distribution (1st–99th Percentiles)")
        plt.xlabel("Daily Weight Change (kg)")
        plt.ylabel("Frequency")
        plt.tight_layout()
        plt.savefig(output_dir / "daily_weight_change_distribution.png", dpi=160)
        plt.close()

    # Weight by month
    monthly_plot_frame = sample_for_plot(
        frame.loc[frame["hive_weight_kg"].notna(), ["month", "hive_weight_kg"]],
        MAX_HISTOGRAM_ROWS,
    )

    if monthly_plot_frame.empty:
        save_placeholder_plot(
            output_dir / "hive_weight_by_month.png",
            "Hive Weight by Month",
            "No valid hive-weight observations were available.",
        )
    else:
        month_groups = [
            monthly_plot_frame.loc[
                monthly_plot_frame["month"] == month,
                "hive_weight_kg",
            ].dropna().values
            for month in range(1, 13)
        ]
        plt.figure(figsize=(12, 6))
        plt.boxplot(month_groups, tick_labels=[str(month) for month in range(1, 13)])
        plt.title("Hive Weight by Month")
        plt.xlabel("Month")
        plt.ylabel("Hive Weight (kg)")
        plt.tight_layout()
        plt.savefig(output_dir / "hive_weight_by_month.png", dpi=160)
        plt.close()

    # Weight by season when available
    if "apiary_season" in frame.columns:
        season_frame = sample_for_plot(
            frame.loc[
                frame["hive_weight_kg"].notna(),
                ["apiary_season", "hive_weight_kg"],
            ],
            MAX_HISTOGRAM_ROWS,
        )
        season_frame["apiary_season"] = (
            season_frame["apiary_season"].fillna("Unknown").astype(str)
        )
        seasons = sorted(season_frame["apiary_season"].unique().tolist())
        season_groups = [
            season_frame.loc[
                season_frame["apiary_season"] == season,
                "hive_weight_kg",
            ].dropna().values
            for season in seasons
        ]

        if seasons:
            plt.figure(figsize=(12, 6))
            plt.boxplot(season_groups, tick_labels=seasons)
            plt.title("Hive Weight by Apiary Season")
            plt.xlabel("Season")
            plt.ylabel("Hive Weight (kg)")
            plt.xticks(rotation=25, ha="right")
            plt.tight_layout()
            plt.savefig(output_dir / "hive_weight_by_season.png", dpi=160)
            plt.close()

    summary = {
        "number_of_hives": int(frame["hive_id"].nunique()),
        "daily_weight_records": int(len(daily)),
        "potential_harvest_drop_count": int(
            frame["potential_harvest_drop_detected"].sum()
        ),
        "potential_plateau_row_count": int(frame["plateau_detected"].sum()),
        "potential_plateau_period_count": int(len(plateau_periods)),
        "per_hive_weight_plot_count": int(len(generated_hive_plots)),
        "potential_drop_rule": (
            f"weight_change_1h_kg <= {POTENTIAL_HARVEST_DROP_THRESHOLD_KG}"
        ),
        "plateau_rule": {
            "near_recent_max_ratio": PLATEAU_RECENT_MAX_RATIO,
            "maximum_weight_std_24h_kg": PLATEAU_WEIGHT_STD_THRESHOLD_KG,
            "maximum_absolute_weight_change_24h_kg": (
                PLATEAU_24H_CHANGE_THRESHOLD_KG
            ),
        },
        "warning": (
            "Potential sudden weight-drop events are screening signals only; "
            "they are not confirmed harvest events."
        ),
    }

    write_json(output_dir / "hive_weight_eda_summary.json", summary)
    return summary


# -----------------------------------------------------------------------------
# Environmental and relationship EDA
# -----------------------------------------------------------------------------


def create_correlation_heatmap(
    data: pd.DataFrame,
    output_dir: Path,
) -> pd.DataFrame:
    """Create a Spearman correlation matrix and heatmap."""
    columns = [
        "hive_weight_kg",
        "weight_change_24h_kg",
        "weight_change_72h_kg",
        "weight_std_24h_kg",
        "internal_temperature_c",
        "internal_humidity_pct",
        "co2_ppm",
        "external_temperature_c",
        "external_humidity_pct",
        "rainfall_mm_hour",
        "wind_speed_mps",
        "brood_health_score_0_100",
    ]
    available = [column for column in columns if column in data.columns]
    numeric = data[available].apply(pd.to_numeric, errors="coerce")
    correlation = numeric.corr(method="spearman")
    correlation.to_csv(output_dir / "spearman_correlation_matrix.csv")

    if correlation.empty:
        save_placeholder_plot(
            output_dir / "correlation_heatmap.png",
            "Spearman Correlation Heatmap",
            "Insufficient numeric variables were available.",
        )
        return correlation

    plt.figure(figsize=(13, 10))
    image = plt.imshow(correlation.values, aspect="auto", vmin=-1, vmax=1)
    plt.colorbar(image, label="Spearman correlation")
    plt.xticks(
        np.arange(len(correlation.columns)),
        correlation.columns,
        rotation=45,
        ha="right",
    )
    plt.yticks(np.arange(len(correlation.index)), correlation.index)

    for row_index in range(len(correlation.index)):
        for column_index in range(len(correlation.columns)):
            value = correlation.iloc[row_index, column_index]
            if pd.notna(value):
                plt.text(
                    column_index,
                    row_index,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=7,
                )

    plt.title("Spearman Correlation Heatmap")
    plt.tight_layout()
    plt.savefig(output_dir / "correlation_heatmap.png", dpi=160)
    plt.close()
    return correlation


def create_environmental_eda(
    data: pd.DataFrame,
    output_dir: Path,
) -> dict[str, Any]:
    """Study associations between environmental variables and weight change."""
    available_environmental = [
        column for column in ENVIRONMENTAL_COLUMNS if column in data.columns
    ]

    relationship_rows: list[dict[str, Any]] = []
    generated_plots: list[str] = []

    for column in available_environmental:
        pair = data[[column, "weight_change_24h_kg"]].copy()
        pair[column] = pd.to_numeric(pair[column], errors="coerce")
        pair["weight_change_24h_kg"] = pd.to_numeric(
            pair["weight_change_24h_kg"], errors="coerce"
        )
        pair = pair.replace([np.inf, -np.inf], np.nan).dropna()

        pearson_value = None
        spearman_value = None

        if len(pair) >= 3 and pair[column].nunique() > 1:
            pearson_value = float(
                pair[column].corr(pair["weight_change_24h_kg"], method="pearson")
            )
            spearman_value = float(
                pair[column].corr(pair["weight_change_24h_kg"], method="spearman")
            )

        relationship_rows.append(
            {
                "environmental_variable": column,
                "valid_pairs": int(len(pair)),
                "pearson_correlation_with_weight_change_24h": pearson_value,
                "spearman_correlation_with_weight_change_24h": spearman_value,
            }
        )

        filename = f"{safe_filename(column)}_vs_weight_change_24h.png"
        path = output_dir / filename

        if pair.empty:
            save_placeholder_plot(
                path,
                f"{column} versus 24-Hour Weight Change",
                "No valid paired observations were available.",
            )
        else:
            plot_pair = sample_for_plot(pair, MAX_SCATTER_ROWS)
            lower = plot_pair["weight_change_24h_kg"].quantile(0.01)
            upper = plot_pair["weight_change_24h_kg"].quantile(0.99)
            plot_pair["weight_change_24h_kg"] = plot_pair[
                "weight_change_24h_kg"
            ].clip(lower, upper)

            plt.figure(figsize=(9, 6))
            plt.scatter(
                plot_pair[column],
                plot_pair["weight_change_24h_kg"],
                s=8,
                alpha=0.25,
            )
            plt.title(f"{column} versus 24-Hour Hive-Weight Change")
            plt.xlabel(column)
            plt.ylabel("24-Hour Weight Change (kg)")
            plt.tight_layout()
            plt.savefig(path, dpi=160)
            plt.close()

        generated_plots.append(filename)

    relationship_summary = pd.DataFrame(relationship_rows)
    relationship_summary.to_csv(
        output_dir / "environmental_weight_relationships.csv",
        index=False,
    )

    monthly_summary = (
        data.groupby("month")
        .agg(
            records=("timestamp", "size"),
            mean_hive_weight_kg=("hive_weight_kg", "mean"),
            mean_weight_change_24h_kg=("weight_change_24h_kg", "mean"),
            median_weight_change_24h_kg=("weight_change_24h_kg", "median"),
            mean_internal_temperature_c=("internal_temperature_c", "mean"),
            mean_internal_humidity_pct=("internal_humidity_pct", "mean"),
            mean_co2_ppm=("co2_ppm", "mean"),
            total_rainfall_mm=("rainfall_mm_hour", "sum"),
            mean_wind_speed_mps=("wind_speed_mps", "mean"),
        )
        .reset_index()
    )
    monthly_summary.to_csv(
        output_dir / "monthly_environmental_weight_summary.csv",
        index=False,
    )

    if "apiary_season" in data.columns:
        seasonal_summary = (
            data.assign(
                apiary_season=data["apiary_season"].fillna("Unknown").astype(str)
            )
            .groupby("apiary_season")
            .agg(
                records=("timestamp", "size"),
                mean_hive_weight_kg=("hive_weight_kg", "mean"),
                mean_weight_change_24h_kg=("weight_change_24h_kg", "mean"),
                median_weight_change_24h_kg=("weight_change_24h_kg", "median"),
                mean_internal_temperature_c=("internal_temperature_c", "mean"),
                mean_internal_humidity_pct=("internal_humidity_pct", "mean"),
                mean_co2_ppm=("co2_ppm", "mean"),
                total_rainfall_mm=("rainfall_mm_hour", "sum"),
                mean_wind_speed_mps=("wind_speed_mps", "mean"),
            )
            .reset_index()
        )
        seasonal_summary.to_csv(
            output_dir / "seasonal_environmental_weight_summary.csv",
            index=False,
        )

    correlation = create_correlation_heatmap(data, output_dir)

    strongest_relationships: list[dict[str, Any]] = []
    if not relationship_summary.empty:
        ranked = relationship_summary.dropna(
            subset=["spearman_correlation_with_weight_change_24h"]
        ).copy()
        if not ranked.empty:
            ranked["absolute_spearman"] = ranked[
                "spearman_correlation_with_weight_change_24h"
            ].abs()
            strongest_relationships = (
                ranked.sort_values("absolute_spearman", ascending=False)
                .head(5)
                .drop(columns=["absolute_spearman"])
                .to_dict(orient="records")
            )

    summary = {
        "environmental_variables": available_environmental,
        "relationship_plot_count": len(generated_plots),
        "relationship_plots": generated_plots,
        "correlation_matrix_variable_count": int(len(correlation.columns)),
        "strongest_spearman_relationships": strongest_relationships,
        "interpretation_warning": (
            "EDA correlations describe association only and do not establish "
            "causation or confirm harvest readiness."
        ),
    }

    write_json(output_dir / "environmental_eda_summary.json", summary)
    return summary


# -----------------------------------------------------------------------------
# Proxy HUI generation
# -----------------------------------------------------------------------------


def robust_minmax(
    series: pd.Series,
    lower_q: float = 0.01,
    upper_q: float = 0.99,
) -> pd.Series:
    """Scale to 0..1 after clipping extreme values to robust quantiles."""
    numeric = pd.to_numeric(series, errors="coerce")
    low = numeric.quantile(lower_q)
    high = numeric.quantile(upper_q)

    if pd.isna(low) or pd.isna(high) or np.isclose(low, high):
        return pd.Series(np.zeros(len(series)), index=series.index, dtype=float)

    return (
        (numeric.clip(low, high) - low) / (high - low)
    ).clip(0, 1)


def triangular_suitability(
    series: pd.Series,
    ideal: float,
    tolerance: float,
) -> pd.Series:
    """Return 1 at the ideal and linearly reduce to 0 at ideal ± tolerance."""
    numeric = pd.to_numeric(series, errors="coerce")
    return (1 - (numeric - ideal).abs() / tolerance).clip(0, 1)


def hui_to_status(hui: float | None) -> str:
    """Convert a HUI score to the existing four-level dashboard status."""
    if hui is None or pd.isna(hui):
        return "Unknown"
    if hui <= 30:
        return "Not Ready"
    if hui <= 60:
        return "Approaching"
    if hui <= 80:
        return "Ready"
    return "Optimal/Emergency"


def generate_hui(data: pd.DataFrame) -> pd.DataFrame:
    """Generate an explainable 0..100 expert-rule proxy HUI.

    Positive components originally total 0.80. They are normalized by 0.80
    before penalties are applied, so the theoretical maximum HUI can reach 100.

    Positive components:
      - Current hive weight: 0.25
      - 72-hour weight gain: 0.15
      - Weight stability/plateau: 0.10
      - Nectar-flow proxy: 0.10
      - Brood health: 0.10
      - Internal-temperature suitability: 0.05
      - Internal-humidity suitability: 0.05

    Penalties:
      - Rain: 0.05
      - Wind: 0.03
      - CO2: 0.04
      - Dearth-season proxy: 0.04
      - Monsoon-period proxy: 0.04
    """
    frame = data.copy()

    # Fill only the initial rolling-window gaps for HUI construction. The raw
    # temporal columns remain available for EDA and model diagnostics.
    weight_change_72 = frame["weight_change_72h_kg"].fillna(0.0)
    weight_std_24 = frame["weight_std_24h_kg"].fillna(
        frame["weight_std_24h_kg"].median()
    ).fillna(0.0)

    frame["hui_weight_score_0_1"] = robust_minmax(frame["hive_weight_kg"])
    frame["hui_weight_gain_score_0_1"] = robust_minmax(weight_change_72)
    frame["hui_weight_stability_score_0_1"] = (
        1 - robust_minmax(weight_std_24)
    ).clip(0, 1)
    frame["hui_nectar_score_0_1"] = (
        pd.to_numeric(frame["nectar_flow_season_proxy"], errors="coerce")
        .fillna(0)
        .clip(0, 1)
    )
    frame["hui_brood_score_0_1"] = (
        pd.to_numeric(frame["brood_health_score_0_100"], errors="coerce")
        .fillna(0)
        .clip(0, 100)
        / 100
    )
    frame["hui_temperature_score_0_1"] = triangular_suitability(
        frame["internal_temperature_c"],
        ideal=35.0,
        tolerance=5.0,
    ).fillna(0)
    frame["hui_humidity_score_0_1"] = triangular_suitability(
        frame["internal_humidity_pct"],
        ideal=60.0,
        tolerance=25.0,
    ).fillna(0)

    frame["hui_rain_penalty_0_1"] = robust_minmax(
        frame["rainfall_mm_hour"]
    ).fillna(0)
    frame["hui_wind_penalty_0_1"] = robust_minmax(
        frame["wind_speed_mps"]
    ).fillna(0)
    frame["hui_co2_penalty_0_1"] = robust_minmax(
        frame["co2_ppm"]
    ).fillna(0)
    frame["hui_dearth_penalty_0_1"] = (
        pd.to_numeric(frame["dearth_season_proxy"], errors="coerce")
        .fillna(0)
        .clip(0, 1)
    )
    frame["hui_monsoon_penalty_0_1"] = (
        pd.to_numeric(frame["monsoon_rain_period_proxy"], errors="coerce")
        .fillna(0)
        .clip(0, 1)
    )

    positive_weight_total = 0.80

    positive_score = (
        0.25 * frame["hui_weight_score_0_1"]
        + 0.15 * frame["hui_weight_gain_score_0_1"]
        + 0.10 * frame["hui_weight_stability_score_0_1"]
        + 0.10 * frame["hui_nectar_score_0_1"]
        + 0.10 * frame["hui_brood_score_0_1"]
        + 0.05 * frame["hui_temperature_score_0_1"]
        + 0.05 * frame["hui_humidity_score_0_1"]
    )

    penalty_score = (
        0.05 * frame["hui_rain_penalty_0_1"]
        + 0.03 * frame["hui_wind_penalty_0_1"]
        + 0.04 * frame["hui_co2_penalty_0_1"]
        + 0.04 * frame["hui_dearth_penalty_0_1"]
        + 0.04 * frame["hui_monsoon_penalty_0_1"]
    )

    frame["hui_positive_score_normalized_0_1"] = (
        positive_score / positive_weight_total
    ).clip(0, 1)
    frame["hui_total_penalty_0_1"] = penalty_score.clip(0, 1)

    frame["harvest_urgency_index_0_100"] = (
        100
        * (
            frame["hui_positive_score_normalized_0_1"]
            - frame["hui_total_penalty_0_1"]
        )
    ).clip(0, 100).round(3)

    frame["hui_status"] = frame[
        "harvest_urgency_index_0_100"
    ].apply(hui_to_status)
    frame["hui_generation_method"] = (
        "expert_rule_proxy_v3_normalized_temporal"
    )

    return frame


def save_hui_plots(data: pd.DataFrame, output_dir: Path) -> None:
    """Save HUI distribution and status plots."""
    plt.figure(figsize=(9, 5))
    data["harvest_urgency_index_0_100"].hist(bins=40)
    plt.title("Generated Harvest Urgency Index Distribution")
    plt.xlabel("HUI (0–100)")
    plt.ylabel("Rows")
    plt.tight_layout()
    plt.savefig(output_dir / "hui_distribution.png", dpi=160)
    plt.close()

    status_counts = data["hui_status"].value_counts().reindex(
        STATUS_ORDER,
        fill_value=0,
    )
    plt.figure(figsize=(9, 5))
    plt.bar(status_counts.index, status_counts.values)
    plt.title("HUI Status Distribution")
    plt.xlabel("Status")
    plt.ylabel("Rows")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(output_dir / "hui_status_distribution.png", dpi=160)
    plt.close()


# -----------------------------------------------------------------------------
# Per-hive dashboard JSON
# -----------------------------------------------------------------------------


def create_hive_harvest_analysis(
    data: pd.DataFrame,
    output_dir: Path,
) -> dict[str, Any]:
    """Generate per-hive EDA and proxy-HUI information for the React dashboard."""
    frame = data.sort_values(["hive_id", "timestamp"]).copy()
    hive_analysis: list[dict[str, Any]] = []

    for hive_id, hive_frame in frame.groupby("hive_id", sort=True):
        hive_frame = hive_frame.sort_values("timestamp")
        latest = hive_frame.iloc[-1]
        recent_24 = hive_frame.tail(24)

        current_plateau_ratio = (
            float(recent_24["plateau_detected"].mean())
            if not recent_24.empty
            else 0.0
        )
        current_plateau_detected = current_plateau_ratio >= 0.75

        plateau_start = None
        plateau_end = None

        if current_plateau_detected:
            recent_plateau_rows = hive_frame.tail(168).loc[
                lambda value: value["plateau_detected"]
            ]
            if not recent_plateau_rows.empty:
                plateau_start = recent_plateau_rows["timestamp"].min().isoformat()
                plateau_end = recent_plateau_rows["timestamp"].max().isoformat()

        current_hui = make_json_safe(
            float(latest["harvest_urgency_index_0_100"])
            if pd.notna(latest["harvest_urgency_index_0_100"])
            else None
        )
        status = hui_to_status(current_hui)

        chart_frame = hive_frame.tail(MAX_PER_HIVE_CHART_ROWS)
        chart_data: list[dict[str, Any]] = []

        for _, row in chart_frame.iterrows():
            chart_data.append(
                {
                    "timestamp": row["timestamp"].isoformat(),
                    "weight": round(float(row["hive_weight_kg"]), 3),
                    "weight_mean_24h": make_json_safe(
                        round(float(row["weight_mean_24h_kg"]), 3)
                        if pd.notna(row["weight_mean_24h_kg"])
                        else None
                    ),
                    "weight_std_24h": make_json_safe(
                        round(float(row["weight_std_24h_kg"]), 3)
                        if pd.notna(row["weight_std_24h_kg"])
                        else None
                    ),
                    "weight_change_24h": make_json_safe(
                        round(float(row["weight_change_24h_kg"]), 3)
                        if pd.notna(row["weight_change_24h_kg"])
                        else None
                    ),
                    "hui": make_json_safe(
                        round(float(row["harvest_urgency_index_0_100"]), 3)
                        if pd.notna(row["harvest_urgency_index_0_100"])
                        else None
                    ),
                    "plateau_detected": bool(row["plateau_detected"]),
                    "harvest_drop_detected": bool(
                        row["potential_harvest_drop_detected"]
                    ),
                    "potential_harvest_drop_detected": bool(
                        row["potential_harvest_drop_detected"]
                    ),
                }
            )

        recent_24h_change = (
            float(latest["weight_change_24h_kg"])
            if pd.notna(latest["weight_change_24h_kg"])
            else 0.0
        )

        potential_drop_count = int(
            hive_frame["potential_harvest_drop_detected"].sum()
        )

        hive_analysis.append(
            {
                "hive": str(hive_id),
                "current_weight": round(float(latest["hive_weight_kg"]), 2),
                "maximum_weight": round(
                    float(hive_frame["hive_weight_kg"].max()), 2
                ),
                "minimum_weight": round(
                    float(hive_frame["hive_weight_kg"].min()), 2
                ),
                "weight_change_24h": round(recent_24h_change, 2),
                "current_hui": (
                    None if current_hui is None else round(float(current_hui), 2)
                ),
                "status": status,
                "plateau_detected": current_plateau_detected,
                "plateau_ratio_last_24_rows": round(current_plateau_ratio, 3),
                "plateau_start": plateau_start,
                "plateau_end": plateau_end,
                # Retained for the existing dashboard, but the event is not confirmed.
                "historical_harvest_count": potential_drop_count,
                "potential_harvest_drop_count": potential_drop_count,
                "latest_timestamp": latest["timestamp"].isoformat(),
                "chart_data": chart_data,
            }
        )

    hive_analysis.sort(
        key=lambda item: (
            item["current_hui"] if item["current_hui"] is not None else -1
        ),
        reverse=True,
    )

    output = {
        "total_hives": len(hive_analysis),
        "plateau_hives": int(
            sum(item["plateau_detected"] for item in hive_analysis)
        ),
        "ready_hives": int(
            sum(
                item["status"] in {"Ready", "Optimal/Emergency"}
                for item in hive_analysis
            )
        ),
        "warning": (
            "Historical harvest counts are potential sudden weight-drop events "
            "and must be confirmed using beekeeper records."
        ),
        "hives": hive_analysis,
    }

    output_path = output_dir / "harvest_hive_analysis.json"
    write_json(output_path, output)
    print(f"Saved hive harvesting analysis: {output_path}")
    return output


# -----------------------------------------------------------------------------
# Main pipeline
# -----------------------------------------------------------------------------


def main() -> None:
    raw_data = load_and_validate_data()

    print("Running dataset-level EDA...")
    dataset_eda_summary = create_dataset_level_eda(
        raw_data,
        OUTPUT_DIR,
    )

    analysis_data = prepare_analysis_data(raw_data)

    print("Creating raw sensor distribution analysis...")
    sensor_eda_summary = create_sensor_distribution_eda(
        analysis_data,
        OUTPUT_DIR,
    )

    print("Creating temporal weight features...")
    temporal_data = add_temporal_features(analysis_data)

    print("Running hive-weight EDA...")
    hive_weight_summary = create_hive_weight_eda(
        temporal_data,
        OUTPUT_DIR,
        PER_HIVE_PLOT_DIR,
    )

    print("Running environmental relationship EDA...")
    environmental_summary = create_environmental_eda(
        temporal_data,
        OUTPUT_DIR,
    )

    print("Generating proxy HUI...")
    hui_data = generate_hui(temporal_data)

    output_csv = OUTPUT_DIR / "hui_dataset.csv"
    hui_data.to_csv(output_csv, index=False)

    save_hui_plots(hui_data, OUTPUT_DIR)
    create_hive_harvest_analysis(hui_data, OUTPUT_DIR)

    status_counts = (
        hui_data["hui_status"]
        .value_counts()
        .reindex(STATUS_ORDER, fill_value=0)
    )

    summary = {
        # Backward-compatible top-level fields used by the existing dashboard.
        "rows": int(len(hui_data)),
        "columns": int(len(hui_data.columns)),
        "hives": int(hui_data["hive_id"].nunique()),
        "start_time": hui_data["timestamp"].min().isoformat(),
        "end_time": hui_data["timestamp"].max().isoformat(),
        "hui": {
            "mean": round(
                float(hui_data["harvest_urgency_index_0_100"].mean()), 3
            ),
            "std": round(
                float(hui_data["harvest_urgency_index_0_100"].std()), 3
            ),
            "min": round(
                float(hui_data["harvest_urgency_index_0_100"].min()), 3
            ),
            "max": round(
                float(hui_data["harvest_urgency_index_0_100"].max()), 3
            ),
        },
        "status_counts": {
            key: int(value) for key, value in status_counts.items()
        },
        "method": "expert_rule_proxy_v3_normalized_temporal",
        "warning": (
            "Proxy HUI; not beekeeper-confirmed ground truth. Potential "
            "harvest-drop events are exploratory signals only."
        ),
        # Expanded EDA sections for the revised dashboard.
        "dataset_level_eda": dataset_eda_summary,
        "sensor_distribution_eda": sensor_eda_summary,
        "hive_weight_eda": hive_weight_summary,
        "environmental_eda": environmental_summary,
        "eda_questions": {
            "primary_question": (
                "What temporal, environmental and hive-weight patterns occur "
                "before a potentially suitable harvest period?"
            ),
            "current_limit": (
                "The dataset has no beekeeper-confirmed harvest-readiness or "
                "harvest-event ground truth, so EDA identifies candidate "
                "patterns rather than validated pre-harvest patterns."
            ),
        },
    }

    write_json(OUTPUT_DIR / "harvest_eda_summary.json", summary)

    print(f"Saved HUI dataset: {output_csv}")
    print(f"Saved EDA outputs in: {OUTPUT_DIR}")
    print("Harvest EDA pipeline completed successfully.")


if __name__ == "__main__":
    main()
