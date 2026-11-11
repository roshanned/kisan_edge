"""Score a hybrid run (full hybrid, A1, R) from the scores its parts already have, with no new judge calls.

A hybrid answer is either the edge answer (answered_by = edge) or the cloud answer (answered_by = cloud),
so its label is the judge label of that part. Rows whose final answer is neither (for example a deferral
written by the offline dose filter) are left out and counted as `not_composable`; score those with
src.eval.score if they matter.

Usage:
  python -m src.eval.compose_scores --run H --hybrid outputs/hybrid_B3_A2.jsonl \
      --edge outputs/edge_tuned.jsonl --edge-scores outputs/scores_B3.jsonl \
      --cloud outputs/cloud_A2.jsonl --cloud-scores outputs/scores_A2.jsonl
Writes outputs/scores_<run>.jsonl in the same format as src.eval.score.
"""
import argparse
from collections import Counter

from src.data.common import read_jsonl, write_jsonl


def main():
    ap = argparse.ArgumentParser()
    for a in ["--run", "--hybrid", "--edge", "--edge-scores", "--cloud", "--cloud-scores"]:
        ap.add_argument(a, required=True)
    ap.add_argument("--out-dir", default="outputs")
    args = ap.parse_args()
    compose(args.run, args.hybrid, args.edge, args.edge_scores, args.cloud, args.cloud_scores, args.out_dir)


def compose(run, hybrid, edge, edge_scores, cloud, cloud_scores, out_dir="outputs"):
    """Returns (rows, stats); also writes <out_dir>/scores_<run>.jsonl. Paths, or already-loaded lists of rows."""
    rows = lambda x: read_jsonl(x) if isinstance(x, str) else x

    parts = {
        "edge": ({r["id"]: r["answer"] for r in rows(edge)}, {s["id"]: s for s in rows(edge_scores)}),
        "cloud": ({r["id"]: r["answer"] for r in rows(cloud)}, {s["id"]: s for s in rows(cloud_scores)}),
    }
    out, stats = [], Counter()
    for h in rows(hybrid):
        answers, scores = parts.get(h["answered_by"], ({}, {}))
        s = scores.get(h["id"])
        # Only reuse a label if the final answer is exactly the text that was judged.
        if s is None or answers.get(h["id"]) != h["final_answer"]:
            stats["not_composable"] += 1
            continue
        out.append({**s, "run": run, "answered_by": h["answered_by"], "route": h["route"],
                    "composed_from": h["answered_by"]})
        stats[h["answered_by"]] += 1
    write_jsonl(out, f"{out_dir}/scores_{run}.jsonl")
    print(f"{run}: {len(out)} composed {dict(stats)}; labels {dict(Counter(r['label'] for r in out))}")
    return out, stats


if __name__ == "__main__":
    main()
