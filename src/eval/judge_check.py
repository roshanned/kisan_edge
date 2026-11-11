"""Check whether the LLM judge can be trusted: you relabel a sample by hand, we measure agreement.

  python -m src.eval.judge_check sample --n 50     -> reports/mid/judge_check_sheet.csv (fill human_label)
  python -m src.eval.judge_check agree             -> reports/mid/judge_agreement.md (+ marks scores human_checked)
  python -m src.eval.judge_check judges --n 150 --model gemini-3.5-flash-lite
        a second LLM judge relabels a stratified sample of the same answers -> <dir>/judge_vs_judge.json
        (no human needed; it measures consistency between judges, not correctness)
Add --dir outputs/final --report-dir reports/final (before the sub-command) for the final-phase files.

human_label is one of: correct, partly_correct, wrong (the sheet shows the judge's label last, so label first).
"""
import argparse
import csv
import json
import random
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.data.common import read_jsonl, write_jsonl
from src.eval.judge import LABELS

SHEET = Path("reports/mid/judge_check_sheet.csv")
REPORT = Path("reports/mid/judge_agreement.md")
# Runs whose answers were judged directly; hybrid scores are copies of these, so sampling them would double-count.
RUN_FILES = {"B1": "cloud_B1", "A2": "cloud_A2", "A3": "cloud_A3", "B2": "edge_base_full", "B3": "edge_tuned_full"}


def judged_rows(d):
    """(scores, {(run, id): answer}). Final layout: only the directly judged runs; otherwise every file in d."""
    d = Path(d)
    if all((d / f"scores_{r}.jsonl").exists() for r in ("B1", "B3")):
        scores = [s for r in RUN_FILES if (d / f"scores_{r}.jsonl").exists() for s in read_jsonl(d / f"scores_{r}.jsonl")]
        answers = {(r, a["id"]): a["answer"] for r, f in RUN_FILES.items() if (d / f"{f}.jsonl").exists()
                   for a in read_jsonl(d / f"{f}.jsonl")}
        return scores, answers
    answers = {}
    for f in d.glob("*.jsonl"):
        if f.name.startswith("scores_"):
            continue
        for r in read_jsonl(f):
            answers[(r.get("run") or f.stem, r["id"])] = r.get("final_answer") or r.get("answer")
    return [s for f in sorted(d.glob("scores_*.jsonl")) for s in read_jsonl(f) if s["judge"] != "mock"], answers


def stratified(scores, n, seed, keys=("lang", "script")):
    """n rows, round-robin over buckets so every language (and run, if in keys) is covered."""
    rows = list(scores)
    random.Random(seed).shuffle(rows)
    by = {}
    for s in rows:
        by.setdefault(tuple(s[k] for k in keys), []).append(s)
    picked = []
    while len(picked) < n and any(by.values()):
        for k in sorted(by):
            if by[k] and len(picked) < n:
                picked.append(by[k].pop())
    return picked


def sample(n, seed=11, d="outputs"):
    qs = {q["id"]: q for q in read_jsonl("data/processed/questions.jsonl")}
    scores, answers = judged_rows(d)
    if not scores:
        raise SystemExit(f"no non-mock scores found in {d}/scores_*.jsonl")
    picked = stratified(scores, n, seed)
    SHEET.parent.mkdir(parents=True, exist_ok=True)
    with SHEET.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "run", "lang", "script", "category", "question", "reference_answer", "answer",
                    "human_label", "judge_label"])
        for s in picked:
            q = qs[s["id"]]
            w.writerow([s["id"], s["run"], s["lang"], s["script"], s["category"], q["question"],
                        q["reference_answer"], answers.get((s["run"], s["id"]), ""), "", s["label"]])
    print(f"wrote {len(picked)} rows to {SHEET}")


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in LABELS) / n ** 2
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def agree(d="outputs"):
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
    for f in Path(d).glob("scores_*.jsonl"):
        recs = read_jsonl(f)
        for s in recs:
            if (s["run"], s["id"]) in human:
                s["human_checked"], s["human_label"] = True, human[(s["run"], s["id"])]
        write_jsonl(recs, f)


def judges(n, model, d, seed=5):
    """A second LLM judge relabels a stratified sample (over run and language); agreement with the main judge."""
    from src.eval.judge import GeminiJudge
    qs = {q["id"]: q for q in read_jsonl("data/processed/questions.jsonl")}
    scores, answers = judged_rows(d)
    picked = [s for s in stratified(scores, n, seed, ("run", "lang", "script")) if answers.get((s["run"], s["id"])) is not None]
    second = GeminiJudge(model=model, rpm=14)

    def one(s):
        try:
            return second(qs[s["id"]], answers[(s["run"], s["id"])])
        except Exception as e:  # quota: leave this row out
            print("second judge failed:", str(e)[:120])
            return None

    with ThreadPoolExecutor(4) as ex:
        labels = list(ex.map(one, picked))
    done = [(s, b) for s, b in zip(picked, labels) if b]
    pairs = [(s["label"], b["label"]) for s, b in done]
    is_correct = lambda x: x == "correct"
    res = {"second_judge": model, "n": len(pairs),
           "exact_agreement": round(sum(a == b for a, b in pairs) / len(pairs), 3), "kappa": round(kappa(pairs), 3),
           "agreement_correct_vs_not": round(sum(is_correct(a) == is_correct(b) for a, b in pairs) / len(pairs), 3),
           "agreement_wrong_vs_not": round(sum((a == "wrong") == (b == "wrong") for a, b in pairs) / len(pairs), 3),
           "main_correct_rate": round(sum(is_correct(a) for a, _ in pairs) / len(pairs), 3),
           "second_correct_rate": round(sum(is_correct(b) for _, b in pairs) / len(pairs), 3),
           "confusion_main_x_second": {f"{a}|{b}": c for (a, b), c in sorted(Counter(pairs).items())},
           "by_run_exact_agreement": {r: round(sum(s["label"] == b["label"] for s, b in done if s["run"] == r) /
                                               sum(s["run"] == r for s, _ in done), 3) for r in sorted({s["run"] for s, _ in done})}}
    Path(d, "judge_vs_judge.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="outputs")
    ap.add_argument("--report-dir", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sample").add_argument("--n", type=int, default=50)
    sub.add_parser("agree")
    j = sub.add_parser("judges")
    j.add_argument("--n", type=int, default=150)
    j.add_argument("--model", default="gemini-3.5-flash-lite")
    a = ap.parse_args()
    if a.report_dir:
        SHEET, REPORT = Path(a.report_dir) / "judge_check_sheet.csv", Path(a.report_dir) / "judge_agreement.md"
    if a.cmd == "sample":
        sample(a.n, d=a.dir)
    elif a.cmd == "agree":
        agree(a.dir)
    else:
        judges(a.n, a.model, a.dir)
