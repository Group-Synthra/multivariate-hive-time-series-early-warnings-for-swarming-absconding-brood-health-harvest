"""
run_eda.py — Project root runner for the HiveEDA pipeline.

Usage:
    python run_eda.py

This will:
    1. Run the full EDA analysis (backend/eda/eda_analysis.py)
    2. Generate all plots in backend/outputs/eda_complete/
    3. Generate dashboard.json for the REST API
"""

import subprocess
import sys
from pathlib import Path

EDA_SCRIPT = Path(__file__).resolve().parent / 'backend' / 'eda' / 'eda_analysis.py'

if not EDA_SCRIPT.exists():
    print(f"ERROR: EDA script not found at {EDA_SCRIPT}")
    sys.exit(1)

print("🐝 Starting HiveEDA Analysis Pipeline...\n")
result = subprocess.run([sys.executable, str(EDA_SCRIPT)])
sys.exit(result.returncode)
