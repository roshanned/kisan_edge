"""Check whether the LLM judge can be trusted: you relabel a sample by hand, we measure agreement.

  python -m src.eval.judge_check sample --n 50     -> reports/mid/judge_check_sheet.csv (fill human_label)
  python -m src.eval.judge_check agree             -> reports/mid/judge_agreement.md (+ marks scores human_checked)

human_label is one of: correct, partly_correct, wrong (the sheet shows the judge's label last, so label first).
"""
import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

from src.data.common import read_jsonl, write_jsonl
from src.eval.judge import LABELS

SHEET = Path("reports/mid/judge_check_sheet.csv")
REPORT = Path("reports/mid/judge_agreement.md")


def sample(n, seed=11):
    qs = {q["id"]: q for q in read_jsonl("data/processed/questions.jsonl")}
    answers = {}
    for f in Path("outputs").glob("*.jsonl"):
        if f.name.startswith("scores_"):
            continue
        for r in read_jsonl(f):
            answers[(r.get("run") or f.stem, r["id"])] = r.get("final_answer") or r.get("answer")
    scores = [s for f in sorted(Path("outputs").glob("scores_*.jsonl")) for s in read_jsonl(f) if s["judge"] != "mock"]
    if not scores:
        raise SystemExit("no non-mock scores found in outputs/scores_*.jsonl")
    random.Random(seed).shuffle(scores)
    by_lang = {}
    for s in scores:  # stratify by language bucket so Hindi / Hinglish / English are all covered
        by_lang.setdefault((s["lang"], s["script"]), []).append(s)
    picked = []
    while len(picked) < n and any(by_lang.values()):
        for k in list(by_lang):
            if by_lang[k] and len(picked) < n:
                picked.append(by_lang[k].pop())
    SHEET.parent.mkdir(parents=True, exist_ok=True)
    with SHEET.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "run", "lang", "script", "category", "question", "reference_answer", "answer",
                    "human_label", "judge_label"])
        for s in picked:
            q = qs[s["id"]]
            ans = next((a for (run, i), a in answers.items() if i == s["id"] and run == s["run"]), "")
            w.writerow([s["id"], s["run"], s["lang"], s["script"], s["category"], q["question"],
                        q["reference_answer"], ans, "", s["label"]])
    print(f"wrote {len(picked)} rows to {SHEET}")


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in LABELS) / n ** 2
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def agree():
    rows = [r for r in csv.DictReader(SHEET.open(encoding="utf-8-sig")) if r["human_label"].strip()]
    if not rows:
        raise SystemExit(f"{SHEET} has no human_label filled in yet")
    pairs = [(r["human_label"].strip().lower(), r["judge_label"]) for r in rows]
    bad = {h for h, _ in pairs} - set(LABELS)
    if bad:
        raise SystemExit(f"unknown human labels: {bad}; use {LABELS}")
    acc = sum(h == j for h, j in pairs) / len(pairs)
    # "lenient" agreement: collapse partly_correct into correct, a looser view of usefulness
    loose = lambda x: "wrong" if x == "wrong" else "ok"
    acc2 = sum(loose(h) == loose(j) for h, j in pairs) / len(pairs)
    conf = Counter(pairs)
    lines = [f"# Judge vs human agreement\n", f"- Rows hand-labelled: {len(pairs)}",
             f"- Exact agreement: {acc:.1%}", f"- Agreement on wrong vs not-wrong: {acc2:.1%}",
             f"- Cohen's kappa (3 classes): {kappa(pairs):.2f}\n", "| human \\ judge | " + " | ".join(LABELS) + " |",
             "|---|" + "---|" * len(LABELS)]
    for h in LABELS:
        lines.append(f"| {h} | " + " | ".join(str(conf[(h, j)]) for j in LABELS) + " |")
    by_lang = {}
    for r in rows:
        by_lang.setdefault(f"{r['lang']}/{r['script']}", []).append(r["human_label"].strip().lower() == r["judge_label"])
    lines += ["", "| language | n | agreement |", "|---|---|---|"]
    lines += [f"| {k} | {len(v)} | {sum(v) / len(v):.1%} |" for k, v in sorted(by_lang.items())]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    human = {(r["run"], r["id"]): r["human_label"].strip().lower() for r in rows}
    for f in Path("outputs").glob("scores_*.jsonl"):
        recs = read_jsonl(f)
        for s in recs:
            if (s["run"], s["id"]) in human:
                s["human_checked"], s["human_label"] = True, human[(s["run"], s["id"])]
        write_jsonl(recs, f)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sample").add_argument("--n", type=int, default=50)
    sub.add_parser("agree")
    a = ap.parse_args()
    sample(a.n) if a.cmd == "sample" else agree()
