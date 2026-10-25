"""Build the QLoRA fine-tuning set (chat format) for the edge model.

Targets follow the proposal's safety rules (7.3 A):
  any answer containing a dose (any category; labels are noisy) -> the safe, number-free
                deferral answer (read the label, protective gear, KVK / KCC 1551, queued)
  general / high_risk without a dose -> the KCC expert answer
  live_data  -> a deferral answer (capped, so weather questions don't swamp the data)
  emergency  -> dropped (the rule router handles these before the model)

Sources:
  --split-file data/processed/questions.jsonl   Anushka's frozen splits; only split == "train" is used
  --pilot                                       before the split exists: use our own cleaned files,
                                                minus the pilot questions. FOR PILOT RUNS ONLY.

Writes data/processed/sft_train.jsonl and sft_val.jsonl: {"id", "messages": [...], "kind"}
Usage: python -m src.edge.build_sft_data --pilot
"""
import argparse
import random
from collections import Counter
from pathlib import Path

from src.data.common import category_for, read_jsonl, write_jsonl
from src.edge.prompts import HIGH_RISK_ANSWER, LIVE_DATA_ANSWER, has_dose, messages, prompt_kind

OWN_FILES = ["data/processed/kcc_hinglish.jsonl", "data/processed/kcc_1m_other.jsonl",
             "data/processed/kisanvaani_en.jsonl"]
PILOT_IDS = "data/processed/pilot_ids.txt"
PILOT = "data/processed/pilot.jsonl"
LIVE_DATA_SHARE = 0.10   # at most 10% of examples are live-data deferrals
DEFERRAL_SHARE = 0.25    # at most 25% are the high-risk safe answer, so the model doesn't defer everything
MAX_ANSWER_CHARS = 600   # KCC answers are short; drop rare very long ones
VAL_SHARE = 0.03


def question_rows(rows):
    """Turn each cleaned record into the question(s) the model should learn from."""
    for r in rows:
        # Recompute with the current rules (keyword overrides for noisy QueryType labels).
        r = {**r, "category": category_for(r["query_type"], r["question"])}
        if r["lang"] == "en" and r["answer_script"] == "deva":
            # English KCC summary + native Hindi answer: train on the Hindi translation of the question.
            if r.get("question_hi"):
                yield {**r, "question": r["question_hi"], "lang": "hi", "script": "deva"}
        elif r["lang"] == "en" and r["answer_script"] == "hinglish":
            continue  # English question, Hinglish answer: would teach replying in the wrong language
        else:
            yield r


def target(r):
    kind = prompt_kind(r)
    if r["category"] == "live_data":
        return LIVE_DATA_ANSWER[kind], "live_data"
    # Any dose in the answer, whatever the (noisy) label says: the phone never shows doses offline.
    if has_dose(r["reference_answer"]):
        return HIGH_RISK_ANSWER[kind], "high_risk_deferral"
    return r["reference_answer"], r["category"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split-file", default=None)
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--out-dir", default="data/processed")
    args = ap.parse_args()

    if args.split_file:
        rows = [r for r in read_jsonl(args.split_file) if r["split"] == "train"]
    elif args.pilot:
        skip = set(Path(PILOT_IDS).read_text().split()) if Path(PILOT_IDS).exists() else set()
        rows = [r for f in OWN_FILES if Path(f).exists() for r in read_jsonl(f) if r["id"] not in skip]
        if Path(PILOT).exists():  # same question text under another id would also leak
            pilot_texts = {t for p in read_jsonl(PILOT) for t in (p["question"].lower(), p["question_en"].lower())}
            rows = [r for r in rows if r["question"].lower() not in pilot_texts
                    and (r.get("question_hi") or "").lower() not in pilot_texts]
    else:
        ap.error("pass --split-file (real runs) or --pilot (before the split exists)")

    examples, live, deferral, seen = [], [], [], set()
    for r in question_rows(rows):
        if r["category"] == "emergency" or len(r["reference_answer"]) > MAX_ANSWER_CHARS:
            continue
        if r["question"].lower() in seen:  # one answer per question text
            continue
        seen.add(r["question"].lower())
        answer, kind = target(r)
        ex = {"id": r["id"], "messages": messages(r, answer), "kind": kind, "lang": prompt_kind(r)}
        {"live_data": live, "high_risk_deferral": deferral}.get(kind, examples).append(ex)

    random.seed(7)
    n = len(examples)  # answerable examples; the caps are shares of the final mix
    rest = 1 - LIVE_DATA_SHARE - DEFERRAL_SHARE
    examples += random.sample(live, min(int(n * LIVE_DATA_SHARE / rest), len(live)))
    examples += random.sample(deferral, min(int(n * DEFERRAL_SHARE / rest), len(deferral)))
    random.shuffle(examples)
    n_val = max(50, int(len(examples) * VAL_SHARE))
    write_jsonl(examples[n_val:], f"{args.out_dir}/sft_train.jsonl")
    write_jsonl(examples[:n_val], f"{args.out_dir}/sft_val.jsonl")
    print(f"train {len(examples) - n_val}, val {n_val}")
    print("by kind:", dict(Counter(e["kind"] for e in examples)))
    print("by language:", dict(Counter(e["lang"] for e in examples)))


if __name__ == "__main__":
    main()
