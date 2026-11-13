"""Upload the final data, outputs and reports to the Hugging Face dataset kisan-edge/kisan-edge-data.

Needs a token with WRITE access to the kisan-edge org: https://huggingface.co/settings/tokens -> fine-grained ->
"Write access to contents/settings of all repos under kisan-edge", then `hf auth login`.
Usage: python scripts/upload_hf.py [--dry-run]
The dataset card is scripts/hf_dataset_card.md. Files keep the layout described there.
"""
import argparse
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "kisan-edge/kisan-edge-data"
PROCESSED = ["questions.jsonl", "gold.jsonl", "gold_candidates.jsonl", "router_labels.jsonl", "redteam.jsonl",
             "redteam_v2.jsonl", "redteam_v3.jsonl", "filter_probe.jsonl", "test_half_ids.txt", "split_manifest.json"]


def stage(tmp):
    (tmp / "processed").mkdir(parents=True)
    for f in PROCESSED:
        shutil.copy(ROOT / "data/processed" / f, tmp / "processed" / f)
    # the split-based SFT set (B3); the pilot SFT set already on the hub keeps its name
    shutil.copy(ROOT / "data/processed/sft_train.jsonl", tmp / "processed/sft_train_split.jsonl")
    shutil.copy(ROOT / "data/processed/sft_val.jsonl", tmp / "processed/sft_val_split.jsonl")
    shutil.copytree(ROOT / "outputs/final", tmp / "outputs/final", ignore=shutil.ignore_patterns(".*"))
    shutil.copytree(ROOT / "outputs/mid", tmp / "outputs/mid")
    (tmp / "corpus").mkdir()
    for f in ["docs.jsonl", "recall_queries.jsonl"]:
        shutil.copy(ROOT / "corpus" / f, tmp / "corpus" / f)
    shutil.copytree(ROOT / "data/snapshots", tmp / "snapshots")
    (tmp / "reports").mkdir()
    for f in ["report.pdf", "slides.pdf"]:
        shutil.copy(ROOT / "reports/final" / f, tmp / "reports" / f)
    shutil.copy(ROOT / "scripts/hf_dataset_card.md", tmp / "README.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        stage(tmp)
        files = [p for p in tmp.rglob("*") if p.is_file()]
        print(f"{len(files)} files, {sum(p.stat().st_size for p in files) / 1e6:.0f} MB staged")
        if a.dry_run:
            return
        from huggingface_hub import HfApi
        HfApi().upload_folder(folder_path=str(tmp), repo_id=REPO, repo_type="dataset",
                              commit_message="Final phase: split, gold, red-team v1-v3, final answers, judge scores, "
                                             "hybrid runs, metrics, summary.json, corpus list, snapshots, report, slides")
        print(f"uploaded to https://huggingface.co/datasets/{REPO}")


if __name__ == "__main__":
    main()
