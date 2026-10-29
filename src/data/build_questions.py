"""Build the frozen question splits (PLAN.md section 5) from Roshan's cleaned files. RUN ONCE.

Inputs  (data/raw/hf/processed/, fetched by src.data.fetch_inputs):
  kcc_hinglish.jsonl   Hinglish questions                        -> lang hi / script latn
  kcc_1m_other.jsonl   English KCC summaries + IndicTrans2 Hindi -> Hindi variant when the expert answer is
                       Devanagari (question = question_hi), English variant when the answer is English
  kisanvaani_en.jsonl  English Q-A; only the rows on our 4 crops (in_scope) are used
  pilot_ids.txt        Roshan's 100 pilot questions: forced into dev

Writes (data/processed/):
  questions.jsonl        every record with its split + gold flag
  seed_50.jsonl          50 train questions for people to build against
  gold_candidates.jsonl  ~200 test questions, 4 batches of 50 (gold_batch = anushka|kiran|roshan|sai)
  gold_batches/*.csv     one hand-check sheet per person
  split_manifest.json    counts + SHA-256 of the test ids (the freeze check)

The split is made once and then frozen: the script refuses to run again if questions.jsonl exists.
Usage: python -m src.data.build_questions
"""
import argparse
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from src.data.common import category_for, read_jsonl, write_jsonl

RAW = Path("data/raw/hf/processed")
OUT = Path("data/processed")
SEED = 2026

# Per-split quota per language bucket (PLAN: ~700 test, ~2,000 test+calib+dev; train = everything else).
QUOTA = {
    "test":  {"hi/deva": 300, "hi/latn": 250, "en/latn": 150},
    "calib": {"hi/deva": 250, "hi/latn": 200, "en/latn": 150},
    "dev":   {"hi/deva": 300, "hi/latn": 200, "en/latn": 100},  # hi/deva dev includes the 100 pilot questions
}
# Within each (split, language) quota: share of each category. live_data answers are date-specific
# (weather, prices), so they are capped; shortfalls are filled from the other categories.
CATEGORY_SHARE = {"general": 0.4, "high_risk": 0.4, "live_data": 0.2}
GOLD_PER_LANG = {"hi/deva": 70, "hi/latn": 70, "en/latn": 60}
GOLD_PEOPLE = ["anushka", "kiran", "roshan", "sai"]
SEED_SIZE = 50


def bucket(r):
    return f"{r['lang']}/{r['script']}"


def qkey(text):
    return " ".join(str(text).lower().split()).rstrip(" ?.!")


def load_pool(pilot_ids):
    """All candidate records in the shared format, one per distinct question text per language bucket."""
    rows = []
    for r in read_jsonl(RAW / "kcc_hinglish.jsonl"):
        rows.append({**r, "question_translated": False})
    for r in read_jsonl(RAW / "kcc_1m_other.jsonl"):
        if r["answer_script"] == "deva" and r.get("question_hi"):
            rows.append({**r, "question_en": r["question"], "question": r["question_hi"],
                         "lang": "hi", "script": "deva", "question_translated": True})
        elif r["answer_script"] == "latn" and r["lang"] == "en":
            rows.append({**r, "question_translated": False})
        # English question + Hinglish answer is dropped (would reward replying in the wrong language)
    for r in read_jsonl(RAW / "kisanvaani_en.jsonl"):
        if r.get("in_scope"):
            rows.append({**r, "question_translated": False})

    out, seen = [], set()
    for r in sorted(rows, key=lambda r: (r["id"] not in pilot_ids, r["id"])):  # pilot rows win dedup
        r.pop("question_hi", None)
        r.pop("in_scope", None)
        # Recompute with the current rules: keyword overrides fix noisy KCC QueryType labels.
        r["category"] = category_for(r.get("query_type"), r["question"])
        if r["category"] == "emergency":
            r["category"] = "high_risk"  # KCC has no real emergencies; Kiran's red-team set covers these
        k = (bucket(r), qkey(r["question"]))
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def take(pool, n, rng):
    """Sample n records from pool following CATEGORY_SHARE, topping up from whatever is left."""
    by_cat = defaultdict(list)
    for r in pool:
        by_cat[r["category"]].append(r)
    for v in by_cat.values():
        rng.shuffle(v)
    picked = []
    for cat, share in CATEGORY_SHARE.items():
        picked += by_cat[cat][:round(n * share)]
        by_cat[cat] = by_cat[cat][round(n * share):]
    rest = [r for v in by_cat.values() for r in v]
    rng.shuffle(rest)
    picked += rest[:n - len(picked)]
    return picked[:n]


def keys_of(r):
    return {qkey(r["question"])} | ({qkey(r["question_en"])} if r.get("question_en") else set())


def assign_splits(pool, pilot_ids, rng):
    """test, then calib, then dev. A question text (or English source) used in one split is never offered to another."""
    split_of = {}
    claimed = {}  # question key -> split that owns it
    for r in pool:  # pilot questions are reserved for dev before anything is sampled
        if r["id"] in pilot_ids:
            for k in keys_of(r):
                claimed[k] = "dev"
    for name in ["test", "calib", "dev"]:
        for b in sorted({bucket(r) for r in pool}):
            avail = [r for r in pool if bucket(r) == b and r["id"] not in split_of
                     and all(claimed.get(k, name) == name for k in keys_of(r))]
            forced = [r for r in avail if name == "dev" and r["id"] in pilot_ids]
            rest = [r for r in avail if r not in forced]
            chosen = forced + take(rest, max(QUOTA[name].get(b, 0) - len(forced), 0), rng)
            for r in chosen:
                split_of[r["id"]] = name
                for k in keys_of(r):
                    claimed[k] = name
    return split_of


def drop_leaks(pool, split_of):
    """Train must not contain any question (or its English source) that appears in test/calib/dev."""
    held = set()
    for r in pool:
        if split_of.get(r["id"]):
            held.add(qkey(r["question"]))
            if r.get("question_en"):
                held.add(qkey(r["question_en"]))
    leaks = 0
    for r in pool:
        if r["id"] not in split_of:
            if qkey(r["question"]) in held or (r.get("question_en") and qkey(r["question_en"]) in held):
                split_of[r["id"]] = "dropped_leak"
                leaks += 1
            else:
                split_of[r["id"]] = "train"
    return leaks


def pick_gold(rows, rng):
    gold = []
    for b, n in GOLD_PER_LANG.items():
        test_b = [r for r in rows if r["split"] == "test" and bucket(r) == b]
        gold += take(test_b, n, rng)
    gold.sort(key=lambda r: (bucket(r), r["category"], r["id"]))
    for i, r in enumerate(gold):  # round-robin so each batch has the same language/category mix
        r["gold"] = True
        r["gold_batch"] = GOLD_PEOPLE[i % len(GOLD_PEOPLE)]
    return gold


def write_gold_sheets(gold):
    d = OUT / "gold_batches"
    d.mkdir(parents=True, exist_ok=True)
    cols = ["id", "lang", "script", "category", "crop", "question", "reference_answer",
            "question_ok (y/n)", "answer_correct (y/n)", "lang_script_tag_ok (y/n)", "category_ok (y/n)",
            "fixed_category", "fixed_reference_answer", "drop (y/n)", "notes"]
    for person in GOLD_PEOPLE:
        with open(d / f"gold_batch_{person}.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for r in gold:
                if r["gold_batch"] == person:
                    w.writerow([r["id"], r["lang"], r["script"], r["category"], r["crop"],
                                r["question"], r["reference_answer"]] + [""] * 8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="overwrite an existing split (breaks the freeze!)")
    args = ap.parse_args()
    if (OUT / "questions.jsonl").exists() and not args.force:
        raise SystemExit("questions.jsonl exists: the split is frozen. Pass --force only if the team agrees.")

    rng = random.Random(SEED)
    pilot_ids = set((RAW / "pilot_ids.txt").read_text().split())
    pool = load_pool(pilot_ids)
    missing = pilot_ids - {r["id"] for r in pool}
    if missing:  # pilot rows are dropped only if deduplication removed them; report so nothing is silent
        print(f"WARNING: {len(missing)} pilot ids are not in the pool (deduplicated away): {sorted(missing)[:3]}...")

    split_of = assign_splits(pool, pilot_ids, rng)
    leaks = drop_leaks(pool, split_of)
    rows = []
    for r in pool:
        r["split"] = split_of[r["id"]]
        if r["split"] != "dropped_leak":
            r["gold"] = False
            rows.append(r)

    gold = pick_gold(rows, rng)
    OUT.mkdir(parents=True, exist_ok=True)
    order = {"train": 0, "dev": 1, "calib": 2, "test": 3}
    rows.sort(key=lambda r: (order[r["split"]], r["id"]))
    write_jsonl(rows, OUT / "questions.jsonl")
    write_jsonl(gold, OUT / "gold_candidates.jsonl")
    write_gold_sheets(gold)
    train = [r for r in rows if r["split"] == "train"]
    write_jsonl(random.Random(SEED).sample(train, SEED_SIZE), OUT / "seed_50.jsonl")

    test_ids = sorted(r["id"] for r in rows if r["split"] == "test")
    manifest = {
        "seed": SEED, "quota": QUOTA, "category_share": CATEGORY_SHARE, "dropped_for_leakage": leaks,
        "pilot_ids_in_dev": sum(r["id"] in pilot_ids and r["split"] == "dev" for r in rows),
        "counts": {s: dict(Counter(bucket(r) for r in rows if r["split"] == s)) for s in order},
        "categories": {s: dict(Counter(r["category"] for r in rows if r["split"] == s)) for s in order},
        "crops": {s: dict(Counter(r["crop"] for r in rows if r["split"] == s)) for s in order},
        "gold": dict(Counter(f"{r['gold_batch']}:{bucket(r)}" for r in gold)),
        "test_ids_sha256": hashlib.sha256("\n".join(test_ids).encode()).hexdigest(),
    }
    (OUT / "split_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ["dropped_for_leakage", "pilot_ids_in_dev", "counts", "categories"]},
                     indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
