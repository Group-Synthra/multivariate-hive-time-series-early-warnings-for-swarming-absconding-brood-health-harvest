"""Run Module 03 — Absconding Behaviour Prediction.

From project root:
    python backend/scripts/run_absconding.py --model rf --compare-models
Development quick run:
    python backend/scripts/run_absconding.py --model fast --max-rows 60000
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import os

# Make imports work whether the script is run from project root or scripts folder.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.ml.absconding.absconding_pipeline import AbscondingConfig, train_absconding_module


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Absconding Module outputs for backend/frontend.")
    parser.add_argument("--data", default=str(ROOT / "backend" / "data" / "hive_data_with_features.csv"))
    parser.add_argument("--output", default=str(ROOT / "backend" / "outputs" / "absconding"))
    parser.add_argument("--model", choices=["fast", "gnb", "ridge", "dt", "gb", "histgb", "rf", "extratrees", "xgb", "best_classical"], default="best_classical")
    parser.add_argument("--target", default="absconding_label_next_72h")
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--compare-models", action="store_true", help="Run all model comparison rows. This is also the default.")
    parser.add_argument("--no-compare-models", action="store_true", help="Skip model comparison for a faster quick run.")
    parser.add_argument("--timeline-points-per-hive", type=int, default=180)
    parser.add_argument("--comparison-max-rows", type=int, default=20000, help="Caps model-comparison training rows for speed; active final model still trains on the selected dataset.")
    args = parser.parse_args()

    cfg = AbscondingConfig(
        data_path=args.data,
        output_dir=args.output,
        model_type=args.model,
        target_column=args.target,
        max_rows=args.max_rows,
        compare_models=not args.no_compare_models,
        timeline_points_per_hive=args.timeline_points_per_hive,
        comparison_max_rows=args.comparison_max_rows,
    )
    dashboard = train_absconding_module(cfg)
    print("\n✅ Absconding dashboard generated")
    print(f"   JSON: {Path(args.output) / 'absconding_dashboard.json'}")
    print(f"   Active model: {dashboard['summary']['active_backend_model']}")
    print(f"   High-risk hives: {dashboard['summary']['high_risk_hives']}")
    print(f"   Dropdown hives: {len(dashboard.get('hive_options', []))}")
    sys.stdout.flush()
    # Some ML backends keep non-daemon worker threads alive on Windows. Force clean CLI termination after outputs are written.
    os._exit(0)


if __name__ == "__main__":
    main()
