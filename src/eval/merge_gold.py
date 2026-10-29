"""Merge the four hand-checked gold sheets into data/processed/gold.jsonl.

Sheets: data/processed/gold_batches/gold_batch_<person>.csv (filled in by each person).
Per row:
  drop = y, or question_ok = n, or answer_correct = n with no fixed_reference_answer  -> removed
  fixed_category / fixed_reference_answer                                            -> applied
  row with every check column empty                                                  -> kept, human_checked = false
Run it any time: with unfilled sheets it writes all 200 candidates unchecked, so people can start running
B1/B2/B3 right away; rerun it after the sheets come back and filter on human_checked / drops.

Usage: python -m src.eval.merge_gold
"""
import csv
from collections import Counter

from src.data.common import read_jsonl, write_jsonl

PEOPLE = ["anushka", "kiran", "roshan", "sai"]
CHECK = ["question_ok (y/n)", "answer_correct (y/n)", "lang_script_tag_ok (y/n)", "category_ok (y/n)", "drop (y/n)"]
CATEGORIES = {"general", "live_data", "high_risk", "emergency"}


def yn(v):
    return (v or "").strip().lower()[:1]


def main():
    cands = {r["id"]: r for r in read_jsonl("data/processed/gold_candidates.jsonl")}
    gold, stats = [], Counter()
    for person in PEOPLE:
        with open(f"data/processed/gold_batches/gold_batch_{person}.csv", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                r = dict(cands[row["id"]])
                fixed_answer = (row["fixed_reference_answer"] or "").strip()
                if not any(row[c].strip() for c in CHECK):
                    r["human_checked"] = False
                    stats["unchecked"] += 1
                elif yn(row["drop (y/n)"]) == "y" or yn(row["question_ok (y/n)"]) == "n" or \
                        (yn(row["answer_correct (y/n)"]) == "n" and not fixed_answer):
                    stats["dropped"] += 1
                    continue
                else:
                    r["human_checked"] = True
                    r["checked_by"] = person
                    stats["checked"] += 1
                    if fixed_answer:
                        r["reference_answer"] = fixed_answer
                        stats["answer_fixed"] += 1
                    fixed_cat = (row["fixed_category"] or "").strip()
                    if fixed_cat in CATEGORIES and fixed_cat != r["category"]:
                        r["category"] = fixed_cat
                        stats["category_fixed"] += 1
                gold.append(r)
    write_jsonl(sorted(gold, key=lambda r: r["id"]), "data/processed/gold.jsonl")
    print(f"gold.jsonl: {len(gold)} questions;", dict(stats))


if __name__ == "__main__":
    main()
