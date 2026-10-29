"""Gate: decides, for a 'general' question, whether the edge answer is good enough to keep offline.

v1 (Phase 1)  : confidence = mean_logprob of the edge answer (token probability).
v2 (Phase 2)  : logistic regression on logprob features + question type, answer length, script, unknown crop.
Label: 1 if the judge scored the edge answer 'correct' (--positive correct, DECISIONS.md D6).
Fit on dev, pick the threshold on calib, report on test. If dev/calib rows are absent (Phase 1, gold only) the
threshold comes from the eval rows themselves and the report says so.

Usage: python -m src.router_gate.gate --edge outputs/edge_tuned.jsonl --scores outputs/scores_B3.jsonl [--target-rate 0.5]
       -> outputs/gate_metrics_<edge name>.json and outputs/gate_riskcov_<edge name>.png
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from src.data.common import read_jsonl


def load(edge_path, scores_path, positive=("correct",)):
    qs = {q["id"]: q for q in read_jsonl("data/processed/questions.jsonl")}
    sc = {s["id"]: s for s in read_jsonl(scores_path)}
    rows = []
    for e in read_jsonl(edge_path):
        q, s = qs.get(e["id"]), sc.get(e["id"])
        if q and s:
            rows.append({**e, "split": q["split"], "lang": q["lang"], "script": q["script"], "category": q["category"],
                         "crop_known": q["crop"] is not None, "question": q["question"],
                         "y": int(s["label"] in positive), "group": f"{q['lang']}/{q['script']}"})
    return rows


def features(r):
    a = r["answer"] or ""
    return [r["mean_logprob"], r["min_logprob"], math.log1p(r["n_tokens"]), math.log1p(len(a)),
            r["script"] == "deva", r["script"] == "latn" and r["lang"] == "hi", r["crop_known"],
            r["category"] == "live_data", r["category"] == "high_risk"]


def aurc(conf, y):
    """Mean risk over all coverage levels when answers are kept in order of confidence (lower is better)."""
    order = np.argsort(-np.asarray(conf))
    err = 1 - np.asarray(y)[order]
    return float(np.mean(np.cumsum(err) / np.arange(1, len(err) + 1)))


def ece(p, y, bins=10):
    p, y, n, tot = np.asarray(p), np.asarray(y), len(p), 0.0
    for i in range(bins):
        m = (p >= i / bins) & ((p < (i + 1) / bins) if i < bins - 1 else (p <= 1))
        if m.any():
            tot += m.sum() / n * abs(p[m].mean() - y[m].mean())
    return float(tot)


def threshold_for_rate(conf, rate):
    """Keep the top (1-rate) share by confidence; returns the cut: keep offline if conf >= cut."""
    return float(np.quantile(conf, rate)) if len(conf) else 0.0


def decisions(conf, cut):
    return np.asarray(conf) >= cut  # True = keep offline


def gate_metrics(conf, y, cut):
    keep, y = decisions(conf, cut), np.asarray(y)
    wrong, right = (y == 0), (y == 1)
    return {"n": int(len(y)), "cloud_call_rate": round(float((~keep).mean()), 3),
            "false_keep_rate": round(float((keep & wrong).sum() / max(1, wrong.sum())), 3),       # wrong answers we kept
            "unnecessary_send_rate": round(float(((~keep) & right).sum() / max(1, right.sum())), 3),  # good answers we sent
            "kept_accuracy": round(float(y[keep].mean()), 3) if keep.any() else None}


def evaluate(rows, target_rate, fit_split="dev", calib_split="calib", eval_split="test"):
    ev = [r for r in rows if r["split"] == eval_split] or rows
    fit, cal = [r for r in rows if r["split"] == fit_split], [r for r in rows if r["split"] == calib_split]
    y = np.array([r["y"] for r in ev])
    out = {"eval_rows": len(ev), "edge_accuracy": round(float(y.mean()), 3), "phase1_no_calib": not cal}
    tp = np.array([r["mean_logprob"] for r in ev])  # token-prob confidence (higher = surer)
    cut = threshold_for_rate([r["mean_logprob"] for r in (cal or ev)], target_rate)
    out["token_prob"] = {"auroc": _auc(y, tp), "aurc": round(aurc(tp, y), 4),
                         "ece": round(ece(np.exp(np.clip(tp, -20, 0)), y), 4), **gate_metrics(tp, y, cut)}
    conf_by = {"token_prob": tp}
    if len(fit) >= 50 and len({r["y"] for r in fit}) == 2:
        sc = StandardScaler().fit([features(r) for r in fit])
        lr = LogisticRegression(max_iter=1000, class_weight="balanced").fit(sc.transform([features(r) for r in fit]), [r["y"] for r in fit])
        pr = lambda rs: lr.predict_proba(sc.transform([features(r) for r in rs]))[:, 1]
        pe = pr(ev)
        cut2 = threshold_for_rate(pr(cal or ev), target_rate)
        out["classifier"] = {"auroc": _auc(y, pe), "aurc": round(aurc(pe, y), 4), "ece": round(ece(pe, y), 4), **gate_metrics(pe, y, cut2)}
        conf_by["classifier"] = pe
        out["h3_classifier_beats_token_prob"] = (out["classifier"]["auroc"] or 0) > (out["token_prob"]["auroc"] or 0)
    else:
        out["classifier"] = f"not fitted: need >=50 dev rows with both labels, have {len(fit)}"
    out["per_group_token_prob_auroc"] = {g: _auc(np.array([r["y"] for r in ev if r["group"] == g]),
                                                 np.array([r["mean_logprob"] for r in ev if r["group"] == g]))
                                         for g in sorted({r["group"] for r in ev})}
    return out, ev, conf_by, cut


def _auc(y, s):
    return round(float(roc_auc_score(y, s)), 4) if len(set(y)) == 2 else None


def plot(ev, conf_by, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5, 3.5))
    for name, conf in conf_by.items():
        err = 1 - np.asarray([r["y"] for r in ev])[np.argsort(-np.asarray(conf))]
        ax.plot(np.arange(1, len(err) + 1) / len(err), np.cumsum(err) / np.arange(1, len(err) + 1), label=name)
    ax.set_xlabel("coverage (share of answers kept offline)")
    ax.set_ylabel("risk (error rate of kept answers)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--edge", required=True)
    ap.add_argument("--scores", required=True)
    ap.add_argument("--target-rate", type=float, default=0.5, help="share of general Qs to send to the cloud")
    ap.add_argument("--positive", default="correct", help="comma list of judge labels that count as a good edge answer")
    a = ap.parse_args()
    rows = load(a.edge, a.scores, tuple(a.positive.split(",")))
    if not rows:
        raise SystemExit("no rows: edge ids and score ids do not overlap with questions.jsonl")
    out, ev, conf_by, _ = evaluate(rows, a.target_rate)
    stem = Path(a.edge).stem
    Path(f"outputs/gate_metrics_{stem}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    plot(ev, conf_by, f"outputs/gate_riskcov_{stem}.png")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
