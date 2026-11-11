"""Upload corpus/raw + corpus/docs.jsonl to the private Kaggle dataset roshanned/kisan-edge-corpus (for job 04).

Usage: python kaggle/push_corpus.py "what changed"
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DATASET = "roshanned/kisan-edge-corpus"
ROOT = Path(__file__).resolve().parent.parent


def main():
    message = sys.argv[1] if len(sys.argv) > 1 else "update corpus"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shutil.copytree(ROOT / "corpus/raw", tmp / "raw")
        shutil.copy(ROOT / "corpus/docs.jsonl", tmp)
        (tmp / "dataset-metadata.json").write_text(json.dumps({
            "title": "kisan-edge-corpus", "id": DATASET, "licenses": [{"name": "other"}]}))

        exists = subprocess.run(["kaggle", "datasets", "status", DATASET],
                                capture_output=True, text=True).returncode == 0
        cmd = (["kaggle", "datasets", "version", "-p", str(tmp), "-m", message, "--dir-mode", "zip"] if exists
               else ["kaggle", "datasets", "create", "-p", str(tmp), "--dir-mode", "zip"])
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
