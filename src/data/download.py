"""Download the raw datasets this workstream needs into data/raw/ (skips files that already exist).

Usage: python -m src.data.download
"""
from pathlib import Path

from huggingface_hub import hf_hub_download

FILES = {
    "data/raw/kcc_1m/train.parquet": ("Omegaindebt/Kisan_Call_Centre_Transcripts", "data/train-00000-of-00001.parquet"),
    "data/raw/kisanvaani/train.parquet": ("KisanVaani/agriculture-qa-english-only", "data/train-00000-of-00001.parquet"),
}


def main():
    for dest, (repo, name) in FILES.items():
        dest = Path(dest)
        if dest.exists():
            print(f"exists: {dest}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        path = hf_hub_download(repo, name, repo_type="dataset")
        dest.write_bytes(Path(path).read_bytes())
        print(f"downloaded: {dest}")


if __name__ == "__main__":
    main()
