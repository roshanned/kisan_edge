"""Score one run's output file against the reference answers.

  python -m src.eval.score --run B3 --outputs outputs/edge_tuned.jsonl --judge gemini
  python -m src.eval.score --run B1 --outputs outputs/cloud_B1.jsonl --subset test

Reads the answer from `answer` (edge / cloud files) or `final_answer` (router / hybrid files).
Writes outputs/scores_<run>.jsonl in the shared format (+ lang, script, category, deferred, reason).
Questions with no answer in the output file are counted as missing, not silently skipped.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from src.data.common import read_jsonl, write_jsonl
from src.eval.judge import get_judge

SUBSETS = {"gold": "data/processed/gold.jsonl"}


def load_questions(subset):
    if subset in SUBSETS and Path(SUBSETS[subset]).exists():
        return read_jsonl(SUBSETS[subset])
    qs = read_jsonl("data/processed/questions.jsonl")
    if subset == "gold":
        return [q for q in qs if q["gold"]]
    return [q for q in qs if q["split"] == subset]


def answer_of(rec):
    return rec.get("final_answer") if rec.get("final_answer") is not None else rec.get("answer")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="run id: B1, B2, B3, R, A1, A2, ...")
    ap.add_argument("--outputs", required=True)
    ap.add_argument("--subset", default="gold", help="gold | test | dev | calib")
    ap.add_argument("--judge", default="gemini", choices=["gemini", "mock"])
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    questions = load_questions(args.subset)
    answers = {r["id"]: r for r in read_jsonl(args.outputs)}
    judge = get_judge(args.judge)
    out, missing = [], 0
    for q in questions[:args.limit]:
        rec = answers.get(q["id"])
        if rec is None or answer_of(rec) is None:
            missing += 1
            continue
        res = judge(q, answer_of(rec))
        out.append({"id": q["id"], "run": args.run, "label": res["label"], "judge": args.judge,
                    "human_checked": False, "lang": q["lang"], "script": q["script"],
                    "category": q["category"], "crop": q.get("crop"), "deferred": res["deferred"],
                    "reason": res["reason"], "answered_by": rec.get("answered_by")})
    Path("outputs").mkdir(exist_ok=True)
    write_jsonl(out, f"outputs/scores_{args.run}.jsonl")
    print(f"{args.run}: scored {len(out)} of {len(questions[:args.limit])}; missing {missing}; "
          f"labels {dict(Counter(r['label'] for r in out))}")
    if args.judge == "mock":
        print("WARNING: mock judge. These labels are for testing only, never report them.")


if __name__ == "__main__":
    main()
