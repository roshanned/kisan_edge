"""Build the 100-question Hindi pilot set used to pick the edge model (proposal 7.1).

Takes KCC rows whose answer is native Hindi (Devanagari) and whose English question summary
has been translated to Hindi (`question_hi`), skips live-data questions (weather answers are
date-specific), and samples 25 per crop.

These IDs must go into the dev split, never test. Send data/processed/pilot_ids.txt to Anushka.

Usage: python -m src.edge.make_pilot
"""
import random
from collections import defaultdict

from src.data.common import read_jsonl, write_jsonl

SOURCE = "data/processed/kcc_1m_other.jsonl"
OUT = "data/processed/pilot.jsonl"
OUT_IDS = "data/processed/pilot_ids.txt"
PER_CROP = 25
MIN_ANSWER_CHARS = 30


def main():
    rows = [r for r in read_jsonl(SOURCE)
            if r.get("question_hi") and r["answer_script"] == "deva"
            and r["category"] != "live_data" and len(r["reference_answer"]) >= MIN_ANSWER_CHARS]
    by_crop, seen = defaultdict(list), set()
    for r in rows:
        if r["question_hi"] not in seen:  # one row per distinct question
            seen.add(r["question_hi"])
            by_crop[r["crop"]].append(r)

    random.seed(13)
    pilot = []
    for crop in sorted(by_crop):
        for r in random.sample(by_crop[crop], min(PER_CROP, len(by_crop[crop]))):
            pilot.append({**r, "question_en": r["question"], "question": r["question_hi"],
                          "lang": "hi", "script": "deva", "split": "dev"})
    write_jsonl(pilot, OUT)
    with open(OUT_IDS, "w", encoding="utf-8") as f:
        f.write("\n".join(r["id"] for r in pilot) + "\n")
    print(f"pilot: {len(pilot)} questions", {c: min(PER_CROP, len(v)) for c, v in by_crop.items()})


if __name__ == "__main__":
    main()
