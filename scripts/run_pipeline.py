"""Orchestrate the full rebuild: catalog -> stock -> customers -> embeddings ->
ES indices -> bulk load. Run this after any change to data/seed/*.yaml or the
embedding model.
"""
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent

STEPS = [
    "generate_mock_catalog.py",
    "generate_stock_levels.py",
    "generate_customers.py",
    "generate_embeddings.py",
    "build_es_indices.py",
    "load_es_data.py",
]


def main():
    for step in STEPS:
        print(f"\n=== {step} ===")
        result = subprocess.run([sys.executable, str(SCRIPTS_DIR / step)])
        if result.returncode != 0:
            print(f"Pipeline stopped: {step} failed")
            sys.exit(result.returncode)

    print("\nPipeline complete.")


if __name__ == "__main__":
    main()
