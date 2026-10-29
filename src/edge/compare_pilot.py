"""Compare pilot outputs from several edge models and write a sheet for manual Hindi rating.

Automatic signals (cheap proxies until Anushka's judge exists):
  hindi_rate   share of answers written mostly in Devanagari (did it reply in Hindi?)
  overlap_f1   word-overlap F1 against the KCC reference answer
  mean_logprob, n_tokens, latency_ms

Also writes outputs/pilot_rating_sheet.csv: one row per question with every model's answer,
so a Hindi speaker can mark each answer correct / partly / wrong.

Usage: python -m src.edge.compare_pilot outputs/pilot_*.jsonl
"""
import csv
import re
import sys
from collections import Counter
from statistics import mean

from src.data.common import read_jsonl

PILOT = "data/processed/pilot.jsonl"
SHEET = "outputs/pilot_rating_sheet.csv"
WORD = re.compile(r"[\wऀ-ॿ]+")


def devanagari_share(text):
    letters = [c for c in text if c.isalpha()]
    return sum("ऀ" <= c <= "ॿ" for c in letters) / len(letters) if letters else 0.0


def overlap_f1(pred, ref):
    p, r = Counter(WORD.findall(pred.lower())), Counter(WORD.findall(ref.lower()))
    common = sum((p & r).values())
    if not common:
        return 0.0
    precision, recall = common / sum(p.values()), common / sum(r.values())
    return 2 * precision * recall / (precision + recall)


def main(paths):
    pilot = {r["id"]: r for r in read_jsonl(PILOT)}
    runs = {}
    for path in paths:
        rows = read_jsonl(path)
        runs[rows[0]["model"]] = {r["id"]: r for r in rows}

    print(f"{'model':32} {'n':>4} {'hindi_rate':>10} {'overlap_f1':>10} {'mean_lp':>8} {'tokens':>7} {'ms/q':>7}")
    for model, out in runs.items():
        rows = [r for i, r in out.items() if i in pilot]
        print(f"{model:32} {len(rows):>4} "
              f"{mean(devanagari_share(r['answer']) >= 0.5 for r in rows):>10.2f} "
              f"{mean(overlap_f1(r['answer'], pilot[r['id']]['reference_answer']) for r in rows):>10.3f} "
              f"{mean(r['mean_logprob'] for r in rows if r['mean_logprob'] is not None):>8.3f} "
              f"{mean(r['n_tokens'] for r in rows):>7.1f} "
              f"{mean(r['latency_ms'] for r in rows):>7.0f}")

    models = list(runs)
    with open(SHEET, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig so Excel shows Hindi
        w = csv.writer(f)
        w.writerow(["id", "crop", "question", "reference_answer"]
                   + [c for m in models for c in (f"{m} answer", f"{m} rating (correct/partly/wrong)")])
        for qid, q in pilot.items():
            w.writerow([qid, q["crop"], q["question"], q["reference_answer"]]
                       + [c for m in models for c in (runs[m].get(qid, {}).get("answer", ""), "")])
    print(f"\nrating sheet: {SHEET}")


if __name__ == "__main__":
    main(sys.argv[1:])
