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
EXTRAS = ["models/Llama-3.2-3B-Instruct-split-r16-e2", "data/raw/bhashabench/bhashabench_krishi/hi.parquet"]


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
        # The B3 adapter (jobs 06/08 reuse it instead of retraining) and the BhashaBench-Krishi Hindi file.
        for extra in EXTRAS:
            src = ROOT / extra
            if src.is_dir():
                shutil.copytree(src, tmp / extra, ignore=shutil.ignore_patterns("checkpoint-*"))
            elif src.exists():
                (tmp / extra).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, tmp / extra)
        (tmp / "dataset-metadata.json").write_text(json.dumps({
            "title": "kisan-edge-code", "id": DATASET, "licenses": [{"name": "CC0-1.0"}]}))

        exists = subprocess.run(["kaggle", "datasets", "status", DATASET],
                                capture_output=True, text=True).returncode == 0
        cmd = (["kaggle", "datasets", "version", "-p", str(tmp), "-m", message, "--dir-mode", "zip"] if exists
               else ["kaggle", "datasets", "create", "-p", str(tmp), "--dir-mode", "zip"])
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
