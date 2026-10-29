"""Tables and plots from outputs/scores_*.jsonl, per language and script (PLAN.md section 10).

Writes to reports/mid/ (or --out):
  tables/summary.md       one row per run: n, correct / partly / wrong %, deferred %
  tables/by_language.md   strict accuracy (+95% Wilson interval) per run x language/script
  tables/by_category.md   same per category
  tables/*.csv            the same numbers as CSV
  figures/accuracy_by_language.png

"accuracy" = share labelled correct. "lenient" = correct + partly_correct.
Usage: python -m src.eval.report [--out reports/mid]
"""
import argparse
import math
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.data.common import read_jsonl  # noqa: E402

ORDER = ["B1", "B2", "B3", "R", "A1", "A2", "A3", "A4", "Hybrid"]


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - h), min(1, c + h)


def load():
    runs = {}
    for f in Path("outputs").glob("scores_*.jsonl"):
        rows = read_jsonl(f)
        if rows:
            runs[rows[0]["run"]] = rows
    return dict(sorted(runs.items(), key=lambda kv: (ORDER.index(kv[0]) if kv[0] in ORDER else 99, kv[0])))


def table(runs, key):
    groups = sorted({key(r) for rows in runs.values() for r in rows})
    cells = {}
    for run, rows in runs.items():
        for g in groups:
            sub = [r for r in rows if key(r) == g]
            k = sum(r["label"] == "correct" for r in sub)
            cells[(run, g)] = (k, len(sub))
    return groups, cells


def md_table(runs, groups, cells):
    head = "| run | " + " | ".join(groups) + " |\n|---|" + "---|" * len(groups)
    lines = [head]
    for run in runs:
        out = []
        for g in groups:
            k, n = cells[(run, g)]
            lo, hi = wilson(k, n)
            out.append(f"{k / n:.1%} (n={n}, {lo:.0%}-{hi:.0%})" if n else "-")
        lines.append(f"| {run} | " + " | ".join(out) + " |")
    return "\n".join(lines) + "\n"


def csv_table(runs, groups, cells):
    lines = ["run," + ",".join(f"{g}_acc,{g}_n" for g in groups)]
    for run in runs:
        parts = []
        for g in groups:
            k, n = cells[(run, g)]
            parts += [f"{k / n:.4f}" if n else "", str(n)]
        lines.append(f"{run}," + ",".join(parts))
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/mid")
    out = Path(ap.parse_args().out)
    runs = load()
    if not runs:
        raise SystemExit("no outputs/scores_*.jsonl yet; run src.eval.score first")
    (out / "tables").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)

    summary = ["| run | judge | n | correct | partly | wrong | lenient | deferred |", "|---|---|---|---|---|---|---|---|"]
    for run, rows in runs.items():
        n = len(rows)
        c = {l: sum(r["label"] == l for r in rows) for l in ["correct", "partly_correct", "wrong"]}
        d = sum(bool(r.get("deferred")) for r in rows)
        summary.append(f"| {run} | {rows[0]['judge']} | {n} | {c['correct'] / n:.1%} | {c['partly_correct'] / n:.1%} | "
                       f"{c['wrong'] / n:.1%} | {(c['correct'] + c['partly_correct']) / n:.1%} | {d / n:.1%} |")
    (out / "tables/summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    for name, key in [("by_language", lambda r: f"{r['lang']}/{r['script']}"), ("by_category", lambda r: r["category"])]:
        groups, cells = table(runs, key)
        (out / f"tables/{name}.md").write_text(md_table(runs, groups, cells), encoding="utf-8")
        (out / f"tables/{name}.csv").write_text(csv_table(runs, groups, cells), encoding="utf-8")
        if name == "by_language":
            fig, ax = plt.subplots(figsize=(7, 4))
            width = 0.8 / len(runs)
            for i, run in enumerate(runs):
                accs, err = [], [[], []]
                for g in groups:
                    k, n = cells[(run, g)]
                    p = k / n if n else 0
                    lo, hi = wilson(k, n)
                    accs.append(p)
                    err[0].append(max(0.0, p - lo))
                    err[1].append(max(0.0, hi - p))
                ax.bar([x + i * width for x in range(len(groups))], accs, width, yerr=err, capsize=2, label=run)
            ax.set_xticks([x + 0.4 - width / 2 for x in range(len(groups))])
            ax.set_xticklabels(groups)
            ax.set_ylabel("share judged correct")
            ax.set_ylim(0, 1)
            ax.legend()
            ax.set_title("Accuracy by language/script (95% Wilson CI)")
            fig.tight_layout()
            fig.savefig(out / "figures/accuracy_by_language.png", dpi=150)
    print(f"wrote tables and figure to {out}")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
