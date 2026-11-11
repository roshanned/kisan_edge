"""Gate: decides, for a 'general' question, whether the edge answer is good enough to keep offline.

v1 (Phase 1)  : confidence = mean_logprob of the edge answer (token probability).
v2 (Phase 2)  : logistic regression on logprob features + question type, answer length, script, unknown words
                (share of question words never seen in the train split), and whether the answer is a safe deferral.
Label: 1 if the judge scored the edge answer 'correct' (--positive correct, DECISIONS.md D6).
Fit on dev, pick the threshold on calib, report on test. If dev/calib rows are absent (Phase 1, gold only) the
threshold comes from the eval rows themselves and the report says so.
H3 adds a paired bootstrap over test rows: the share of resamples where the classifier's AUROC beats token-prob's.
--save writes the fitted gates (kind, scaler, model, calib cut) for src.router_gate.hybrid --gate-model.

Usage: python -m src.router_gate.gate --edge outputs/edge_tuned.jsonl --scores outputs/scores_B3.jsonl [--target-rate 0.5]
       -> outputs/gate_metrics_<edge name>.json, outputs/gate_riskcov_<edge name>.png (+ _by_lang.png)
       --scores takes a comma list (one scores file per split).
"""
import argparse
import json
import math
import pickle
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from src.data.common import read_jsonl
from src.edge.prompts import HIGH_RISK_ANSWER, LIVE_DATA_ANSWER
from src.router_gate.safety_filter import DEFERRAL

DEFERRALS = [t[:40] for d in (HIGH_RISK_ANSWER, LIVE_DATA_ANSWER, DEFERRAL) for t in d.values()]
FEATURE_NAMES = ["mean_logprob", "min_logprob", "log_tokens", "log_chars", "deva", "hinglish", "crop_known",
                 "live_data", "high_risk", "unknown_rate", "deferral"]


def words(text):
    return re.findall(r"[\wऀ-ॿ]+", str(text).lower())


@lru_cache(maxsize=1)
def train_vocab():
    """Words in train-split questions; a new question's unseen words are mostly unknown crops, pests and products."""
    return frozenset(w for q in read_jsonl("data/processed/questions.jsonl") if q["split"] == "train" for w in words(q["question"]))


def unknown_rate(question):
    ws = words(question)
    return sum(w not in train_vocab() for w in ws) / len(ws) if ws else 0.0


def is_deferral(answer):
    return any(answer.strip().startswith(d) for d in DEFERRALS) if answer else False


def load(edge_path, scores_path, positive=("correct",)):
    """Edge rows joined with judge labels. 'category' is the ROUTER's category (what the phone knows at run time),
    not the dataset label, so the gate never sees a feature that is unavailable online."""
    from src.router_gate import intent_clf
    from src.router_gate.router import Router
    router = Router(intent_clf.load())
    qs = {q["id"]: q for q in read_jsonl("data/processed/questions.jsonl")}
    sc = {s["id"]: s for p in str(scores_path).split(",") for s in read_jsonl(p)}
    rows = []
    for e in read_jsonl(edge_path):
        q, s = qs.get(e["id"]), sc.get(e["id"])
        if q and s:
            rows.append({**e, "split": q["split"], "lang": q["lang"], "script": q["script"],
                         "category": router.route(q["question"])["category"],
                         "crop_known": q["crop"] is not None, "question": q["question"],
                         "unknown": unknown_rate(q["question"]), "deferral": is_deferral(e["answer"]),
                         "y": int(s["label"] in positive), "group": f"{q['lang']}/{q['script']}"})
    return rows


def gate_rows(edge_rows, questions):
    """Edge output rows -> the dicts features() needs, without a label (for the hybrid runner). questions[id] must
    carry the router's category."""
    out = []
    for e in edge_rows:
        q = questions[e["id"]]
        out.append({**e, "lang": q["lang"], "script": q["script"], "category": q["category"],
                    "crop_known": q["crop"] is not None, "unknown": unknown_rate(q["question"]),
                    "deferral": is_deferral(e["answer"])})
    return out


def features(r):
    a = r["answer"] or ""
    return [r["mean_logprob"] if r["mean_logprob"] is not None else -20.0,
            r["min_logprob"] if r["min_logprob"] is not None else -20.0,
            math.log1p(r["n_tokens"]), math.log1p(len(a)),
            r["script"] == "deva", r["script"] == "latn" and r["lang"] == "hi", r["crop_known"],
            r["category"] == "live_data", r["category"] == "high_risk", r["unknown"], r["deferral"]]


def fit_classifier(rows):
    sc = StandardScaler().fit([features(r) for r in rows])
    lr = LogisticRegression(max_iter=1000, class_weight="balanced").fit(
        sc.transform([features(r) for r in rows]), [r["y"] for r in rows])
    return sc, lr


class Gate:
    """A fitted gate: keep the edge answer offline if conf(row) >= cut. kind = token_prob | classifier."""

    def __init__(self, kind, cut, sc=None, lr=None):
        self.kind, self.cut, self.sc, self.lr = kind, cut, sc, lr

    def conf(self, rows):
        if self.kind == "token_prob":
            return np.array([r["mean_logprob"] if r["mean_logprob"] is not None else -99.0 for r in rows])
        return self.lr.predict_proba(self.sc.transform([features(r) for r in rows]))[:, 1]

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(pickle.dumps(self))

    @staticmethod
    def load(path):
        return pickle.loads(Path(path).read_bytes())


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


def bootstrap_h3(y, a, b, n=2000, seed=0):
    """Paired bootstrap over rows: share of resamples where AUROC(a) > AUROC(b), and the 95% interval of the difference."""
    rng, y, a, b, diffs = np.random.default_rng(seed), np.asarray(y), np.asarray(a), np.asarray(b), []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        if len(set(y[i])) == 2:
            diffs.append(roc_auc_score(y[i], a[i]) - roc_auc_score(y[i], b[i]))
    d = np.array(diffs)
    return {"p_classifier_better": round(float((d > 0).mean()), 3),
            "auroc_diff_ci95": [round(float(np.quantile(d, 0.025)), 4), round(float(np.quantile(d, 0.975)), 4)]}


def evaluate(rows, target_rate, fit_split="dev", calib_split="calib", eval_split="test"):
    ev = [r for r in rows if r["split"] == eval_split] or rows
    fit, cal = [r for r in rows if r["split"] == fit_split], [r for r in rows if r["split"] == calib_split]
    y = np.array([r["y"] for r in ev])
    out = {"eval_rows": len(ev), "edge_accuracy": round(float(y.mean()), 3), "phase1_no_calib": not cal,
           "calib_rows": len(cal), "target_rate": target_rate}
    tp_gate = Gate("token_prob", None)
    tp = tp_gate.conf(ev)  # token-prob confidence (higher = surer)
    tp_gate.cut = cut = threshold_for_rate(tp_gate.conf(cal or ev), target_rate)
    out["token_prob"] = {"auroc": _auc(y, tp), "aurc": round(aurc(tp, y), 4),
                         "ece": round(ece(np.exp(np.clip(tp, -20, 0)), y), 4), **gate_metrics(tp, y, cut)}
    conf_by, gates = {"token_prob": tp}, {"token_prob": tp_gate}
    if len(fit) >= 50 and len({r["y"] for r in fit}) == 2:
        sc, lr = fit_classifier(fit)
        g = Gate("classifier", None, sc, lr)
        pe = g.conf(ev)
        g.cut = cut2 = threshold_for_rate(g.conf(cal or ev), target_rate)
        gates["classifier"] = g
        out["classifier"] = {"auroc": _auc(y, pe), "aurc": round(aurc(pe, y), 4), "ece": round(ece(pe, y), 4),
                             **gate_metrics(pe, y, cut2), "fit_rows": len(fit),
                             "coef": dict(zip(FEATURE_NAMES, np.round(lr.coef_[0], 3).tolist()))}
        conf_by["classifier"] = pe
        out["h3_classifier_beats_token_prob"] = (out["classifier"]["auroc"] or 0) > (out["token_prob"]["auroc"] or 0)
        if len(set(y)) == 2:
            out["h3_bootstrap"] = bootstrap_h3(y, pe, tp)
    else:
        out["classifier"] = f"not fitted: need >=50 dev rows with both labels, have {len(fit)}"
    for name, conf in conf_by.items():
        out[f"per_group_{name}_auroc"] = {
            g: _auc(np.array([r["y"] for r in ev if r["group"] == g]),
                    np.array([c for r, c in zip(ev, conf) if r["group"] == g]))
            for g in sorted({r["group"] for r in ev})}
    return out, ev, conf_by, gates


def _auc(y, s):
    return round(float(roc_auc_score(y, s)), 4) if len(set(y)) == 2 else None


def _riskcov(ax, y, conf, label):
    err = 1 - np.asarray(y)[np.argsort(-np.asarray(conf))]
    ax.plot(np.arange(1, len(err) + 1) / len(err), np.cumsum(err) / np.arange(1, len(err) + 1), label=label)


def plot(ev, conf_by, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5, 3.5))
    for name, conf in conf_by.items():
        _riskcov(ax, [r["y"] for r in ev], conf, name)
    ax.set_xlabel("coverage (share of answers kept offline)")
    ax.set_ylabel("risk (error rate of kept answers)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    groups = sorted({r["group"] for r in ev})
    fig, axes = plt.subplots(1, len(groups), figsize=(4 * len(groups), 3.3), sharey=True, squeeze=False)
    for ax, g in zip(axes[0], groups):
        idx = [i for i, r in enumerate(ev) if r["group"] == g]
        for name, conf in conf_by.items():
            _riskcov(ax, [ev[i]["y"] for i in idx], np.asarray(conf)[idx], name)
        ax.set_title(f"{g} (n={len(idx)})")
        ax.set_xlabel("coverage")
    axes[0][0].set_ylabel("risk")
    axes[0][0].legend()
    fig.tight_layout()
    fig.savefig(str(path).replace(".png", "_by_lang.png"), dpi=150)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--edge", required=True)
    ap.add_argument("--scores", required=True)
    ap.add_argument("--target-rate", type=float, default=0.5, help="share of general Qs to send to the cloud")
    ap.add_argument("--positive", default="correct", help="comma list of judge labels that count as a good edge answer")
    ap.add_argument("--out-dir", default="outputs")
    ap.add_argument("--save", default=None, help="directory for the fitted gates: <dir>/gate_<kind>.pkl")
    a = ap.parse_args()
    rows = load(a.edge, a.scores, tuple(a.positive.split(",")))
    if not rows:
        raise SystemExit("no rows: edge ids and score ids do not overlap with questions.jsonl")
    out, ev, conf_by, gates = evaluate(rows, a.target_rate)
    if a.save:
        for kind, g in gates.items():
            g.save(f"{a.save}/gate_{kind}.pkl")
    stem = Path(a.edge).stem
    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    Path(f"{a.out_dir}/gate_metrics_{stem}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    plot(ev, conf_by, f"{a.out_dir}/gate_riskcov_{stem}.png")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
