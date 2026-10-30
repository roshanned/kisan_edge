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
    args = ap.parse_args()

    parts = {
        "edge": ({r["id"]: r["answer"] for r in read_jsonl(args.edge)},
                 {s["id"]: s for s in read_jsonl(args.edge_scores)}),
        "cloud": ({r["id"]: r["answer"] for r in read_jsonl(args.cloud)},
                  {s["id"]: s for s in read_jsonl(args.cloud_scores)}),
    }
    out, stats = [], Counter()
    for h in read_jsonl(args.hybrid):
        answers, scores = parts.get(h["answered_by"], ({}, {}))
        s = scores.get(h["id"])
        # Only reuse a label if the final answer is exactly the text that was judged.
        if s is None or answers.get(h["id"]) != h["final_answer"]:
            stats["not_composable"] += 1
            continue
        out.append({**s, "run": args.run, "answered_by": h["answered_by"], "route": h["route"],
                    "composed_from": h["answered_by"]})
        stats[h["answered_by"]] += 1
    write_jsonl(out, f"outputs/scores_{args.run}.jsonl")
    print(f"{args.run}: {len(out)} composed {dict(stats)}; labels {dict(Counter(r['label'] for r in out))}")


if __name__ == "__main__":
    main()
