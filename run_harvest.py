"""Run the full harvest pipeline from the project root.

Usage:
    python run_harvest.py
    python run_harvest.py --sample 50000
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EDA_SCRIPT = ROOT / "backend" / "eda" / "eda_analysis_harvest.py"
TRAIN_SCRIPT = ROOT / "backend" / "ml" / "train_hui_models.py"


def run(command: list[str]) -> None:
    print("\n>", " ".join(command))
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=None)
    args = parser.parse_args()

    run([sys.executable, str(EDA_SCRIPT)])
    command = [sys.executable, str(TRAIN_SCRIPT)]
    if args.sample:
        command += ["--sample", str(args.sample)]
    run(command)
    print("\nHarvest pipeline completed successfully.")


if __name__ == "__main__":
    main()
