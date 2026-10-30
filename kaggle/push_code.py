"""Upload src/ + requirements.txt to the private Kaggle dataset roshanned/kisan-edge-code.

Kaggle jobs attach this dataset to get our code. Re-run after every code change, before
pushing a job.

Usage: python kaggle/push_code.py "what changed"
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DATASET = "roshanned/kisan-edge-code"
ROOT = Path(__file__).resolve().parent.parent


def main():
    message = sys.argv[1] if len(sys.argv) > 1 else "update code"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shutil.copytree(ROOT / "src", tmp / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copy(ROOT / "requirements.txt", tmp)
        # Anushka's frozen split + gold set, so jobs train/evaluate on exactly what's in git.
        for name in ["questions.jsonl", "gold.jsonl"]:
            if (ROOT / "data/processed" / name).exists():
                shutil.copy(ROOT / "data/processed" / name, tmp)
        (tmp / "dataset-metadata.json").write_text(json.dumps({
            "title": "kisan-edge-code", "id": DATASET, "licenses": [{"name": "CC0-1.0"}]}))

        exists = subprocess.run(["kaggle", "datasets", "status", DATASET],
                                capture_output=True, text=True).returncode == 0
        cmd = (["kaggle", "datasets", "version", "-p", str(tmp), "-m", message, "--dir-mode", "zip"] if exists
               else ["kaggle", "datasets", "create", "-p", str(tmp), "--dir-mode", "zip"])
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
