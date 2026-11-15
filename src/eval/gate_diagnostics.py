"""Why is raw token probability an INVERTED confidence signal for the tuned model (AUROC 0.16)?

No model calls: reads outputs/final/edge_tuned_full.jsonl and scores_B3*.jsonl.
Answers three questions, all on the test split, with the direction of the signal chosen on dev (never on test):
  1. How much of the inversion comes from the fixed deferral template (always wrong, always very confident)?
  2. What is the AUROC of token probability once its sign is corrected? (the fair comparison for H3)
  3. How far ahead of that is the trained classifier?
Writes outputs/final/gate_diagnostics.json; run_final copies it into summary.json["gate_diagnostics"].
"""
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

from src.router_gate import gate as G

D = Path("outputs/final")


def _auc(y, s):
    return round(float(roc_auc_score(y, s)), 4) if len(set(y)) == 2 else None


def diagnostics(d=D, seed=0):
    parts = ",".join(str(d / f"scores_B3{s}.jsonl") for s in ("", "_calib", "_dev") if (d / f"scores_B3{s}.jsonl").exists())
    rows = G.load(d / "edge_tuned_full.jsonl", parts)
    dev, test = [r for r in rows if r["split"] == "dev"], [r for r in rows if r["split"] == "test"]
    col = lambda rs, k: np.array([r[k] if r[k] is not None else -20.0 for r in rs], dtype=float)
    y_dev, y = np.array([r["y"] for r in dev]), np.array([r["y"] for r in test])
    nd_dev = np.array([not r["deferral"] for r in dev])
    nd = np.array([not r["deferral"] for r in test])
    out = {"n_test": len(test), "n_dev": len(dev), "deferral_share_test": round(float(1 - nd.mean()), 3),
           "accuracy_on_deferrals": round(float(y[~nd].mean()), 3) if (~nd).any() else None,
           "accuracy_non_deferral": round(float(y[nd].mean()), 3)}
    ml, mn, nt = col(test, "mean_logprob"), col(test, "min_logprob"), col(test, "n_tokens")
    out["mean_logprob"] = {"deferral": round(float(ml[~nd].mean()), 3), "non_deferral_correct": round(float(ml[nd & (y == 1)].mean()), 3),
                           "non_deferral_wrong": round(float(ml[nd & (y == 0)].mean()), 3)}
    out["n_tokens_non_deferral"] = {"correct": round(float(nt[nd & (y == 1)].mean()), 1), "wrong": round(float(nt[nd & (y == 0)].mean()), 1)}
    # direction of each single signal, decided on dev
    sign = {k: (1 if _auc(y_dev, col(dev, k)) >= 0.5 else -1) for k in ("mean_logprob", "min_logprob")}
    out["sign_chosen_on_dev"] = sign
    out["dev_auroc_mean_logprob"] = _auc(y_dev, col(dev, "mean_logprob"))
    sc, lr = G.fit_classifier(dev)
    clf = lr.predict_proba(sc.transform([G.features(r) for r in test]))[:, 1]
    sig = {"token_prob_as_defined": ml, "token_prob_sign_corrected": sign["mean_logprob"] * ml,
           "min_logprob_sign_corrected": sign["min_logprob"] * mn, "classifier": clf}
    out["auroc_all"] = {k: _auc(y, v) for k, v in sig.items()}
    out["auroc_non_deferral"] = {k: _auc(y[nd], v[nd]) for k, v in sig.items()}
    rng, diffs, diffs_nd = np.random.default_rng(seed), [], []
    for _ in range(2000):
        i = rng.integers(0, len(y), len(y))
        if len(set(y[i])) == 2:
            diffs.append(roc_auc_score(y[i], clf[i]) - roc_auc_score(y[i], sig["token_prob_sign_corrected"][i]))
        j = i[nd[i]]
        if len(set(y[j])) == 2:
            diffs_nd.append(roc_auc_score(y[j], clf[j]) - roc_auc_score(y[j], sig["token_prob_sign_corrected"][j]))
    ci = lambda a: [round(float(np.quantile(a, .025)), 4), round(float(np.quantile(a, .975)), 4)]
    out["classifier_minus_sign_corrected_token_prob"] = {"all": ci(diffs), "non_deferral": ci(diffs_nd)}
    return out


if __name__ == "__main__":
    res = diagnostics()
    (D / "gate_diagnostics.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
