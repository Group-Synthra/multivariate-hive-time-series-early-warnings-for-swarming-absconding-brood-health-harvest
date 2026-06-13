
from pathlib import Path
import sys

# Allow running from project root: python backend/scripts/run_absconding.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.ml.absconding.absconding_pipeline import AbscondingConfig, train_absconding_module

if __name__ == "__main__":
    cfg = AbscondingConfig(
        data_path=str(PROJECT_ROOT / "backend" / "data" / "hive_data_with_features.csv"),
        output_dir=str(PROJECT_ROOT / "backend" / "outputs" / "absconding"),
        model_type="fast",  # change to "rf" for final report-quality feature importance
    )
    dashboard = train_absconding_module(cfg)
    print("✅ Absconding module outputs generated")
    print(PROJECT_ROOT / "backend" / "outputs" / "absconding" / "absconding_dashboard.json")
