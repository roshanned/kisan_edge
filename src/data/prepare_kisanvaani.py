"""Clean KisanVaani English Q-A pairs (KisanVaani/agriculture-qa-english-only).

KisanVaani is general farming Q-A, not India- or crop-specific. Every row is kept and tagged:
`crop` is set when the text mentions one of our 4 crops, and `in_scope` marks those rows.

Writes data/processed/kisanvaani_en.jsonl and data/processed/kisanvaani_stats.json
Usage: python -m src.data.prepare_kisanvaani
"""
import json
from collections import Counter

import pandas as pd

from src.data.common import MOJIBAKE, find_crop, norm, record, remove_phones, write_jsonl

RAW = "data/raw/kisanvaani/train.parquet"
OUT = "data/processed/kisanvaani_en.jsonl"
OUT_STATS = "data/processed/kisanvaani_stats.json"
MIN_ANSWER_CHARS = 3


def main():
    df = pd.read_parquet(RAW)
    stats = Counter(total=len(df))
    rows, seen = [], set()
    for q, a in zip(df.question, df.answers):
        q, a = remove_phones(norm(q)), remove_phones(norm(a))
        if not q or len(a) < MIN_ANSWER_CHARS or MOJIBAKE.search(q + a):
            stats["dropped_empty_or_corrupted"] += 1
            continue
        if (q.lower(), a.lower()) in seen:
            stats["dropped_duplicate"] += 1
            continue
        seen.add((q.lower(), a.lower()))
        crop = find_crop(q, a)
        rec = record(source="kisanvaani", question=q, answer=a, lang="en", script="latn",
                     crop=crop, query_type=None, category="general", answer_script="latn")
        rec["in_scope"] = crop is not None
        rows.append(rec)

    write_jsonl(rows, OUT)
    stats["kept"] = len(rows)
    stats["kept_in_scope_4_crops"] = sum(r["in_scope"] for r in rows)
    stats["by_crop"] = dict(Counter(r["crop"] for r in rows if r["crop"]))
    with open(OUT_STATS, "w", encoding="utf-8") as f:
        json.dump(dict(stats), f, indent=2)
    print(json.dumps(dict(stats), indent=2))


if __name__ == "__main__":
    main()
