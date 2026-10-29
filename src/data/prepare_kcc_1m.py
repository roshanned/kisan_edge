"""Clean the 1M-row KCC sample (Omegaindebt/Kisan_Call_Centre_Transcripts) for UP + our 4 crops.

Writes:
  data/processed/kcc_hinglish.jsonl  questions typed in Hinglish (Roshan's deliverable)
  data/processed/kcc_1m_other.jsonl  the remaining clean rows (English summaries / Devanagari),
                                     handed to Anushka as extra data for the split
  data/processed/kcc_1m_stats.json   counts for the report

Usage: python -m src.data.prepare_kcc_1m
"""
import json
import re
from collections import Counter

import pandas as pd

from src.data.common import (MOJIBAKE, category_for, detect_script, norm, record,
                             remove_phones, write_jsonl)

RAW = "data/raw/kcc_1m/train.parquet"
OUT_HINGLISH = "data/processed/kcc_hinglish.jsonl"
OUT_OTHER = "data/processed/kcc_1m_other.jsonl"
OUT_STATS = "data/processed/kcc_1m_stats.json"

CROPS = {
    "Wheat": "wheat",
    "Paddy (Dhan)": "paddy",
    "Sugarcane (Noble Cane)": "sugarcane",
    "Mustard": "mustard",
    "Indian rapeseed and mustard (yellow sarson)": "mustard",
}
MIN_ANSWER_CHARS = 8


def main():
    df = pd.read_parquet(RAW)
    stats = Counter(total=len(df))

    df = df[df.StateName.str.upper().str.contains("UTTAR PRADESH", na=False)]
    stats["uttar_pradesh"] = len(df)
    df = df[df.Crop.isin(CROPS)]
    stats["four_crops"] = len(df)

    hinglish, other, seen = [], [], set()
    for row in df.itertuples(index=False):
        q = remove_phones(norm(row.QueryText))
        a = remove_phones(norm(row.KccAns))
        if not q or len(a) < MIN_ANSWER_CHARS:
            stats["dropped_empty_or_short"] += 1
            continue
        if MOJIBAKE.search(a) or MOJIBAKE.search(q):
            stats["dropped_corrupted_text"] += 1
            continue
        key = (q.lower(), a.lower())
        if key in seen:
            stats["dropped_duplicate"] += 1
            continue
        seen.add(key)

        lang, script = detect_script(q)
        _, a_script = detect_script(a)
        # Numeric QueryType values are codes with no label in this dump.
        qtype = row.QueryType if row.QueryType and not re.fullmatch(r"\d+", str(row.QueryType)) else None
        rec = record(
            source="kcc1m", question=q, answer=a, lang=lang, script=script,
            crop=CROPS[row.Crop], query_type=qtype, category=category_for(qtype, q),
            district=norm(row.DistrictName).title() or None, year=int(row.year),
            answer_script="hinglish" if a_script == "latn" and _ == "hi" else a_script,
        )
        (hinglish if script == "latn" and lang == "hi" else other).append(rec)

    write_jsonl(hinglish, OUT_HINGLISH)
    write_jsonl(other, OUT_OTHER)

    stats["kept_hinglish"] = len(hinglish)
    stats["kept_hinglish_unique_questions"] = len({r["question"].lower() for r in hinglish})
    stats["kept_other"] = len(other)
    for name, rows in [("hinglish", hinglish), ("other", other)]:
        stats[f"{name}_by_crop"] = dict(Counter(r["crop"] for r in rows))
        stats[f"{name}_by_category"] = dict(Counter(r["category"] for r in rows))
        stats[f"{name}_by_answer_script"] = dict(Counter(r["answer_script"] for r in rows))
    stats["other_by_question_script"] = dict(Counter(f'{r["lang"]}/{r["script"]}' for r in other))
    with open(OUT_STATS, "w", encoding="utf-8") as f:
        json.dump(dict(stats), f, indent=2, ensure_ascii=False)
    print(json.dumps(dict(stats), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
