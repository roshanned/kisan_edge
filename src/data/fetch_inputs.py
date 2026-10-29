"""Download Roshan's cleaned files from the public HF dataset into data/raw/hf/ (input of the split).

Usage: python -m src.data.fetch_inputs
"""
from huggingface_hub import snapshot_download

REPO = "kisan-edge/kisan-edge-data"


def main():
    path = snapshot_download(REPO, repo_type="dataset", local_dir="data/raw/hf", allow_patterns=["processed/*"])
    print("downloaded to", path)


if __name__ == "__main__":
    main()
