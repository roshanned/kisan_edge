"""Final-phase results (PLAN.md section 4): every table and figure of the final report, from files in outputs/final/.
No model or judge calls: it only reads run outputs and judge scores, fits the gate, runs the hybrid over precomputed
answers, and composes hybrid scores from the parts' scores.

Inputs (outputs/final/):  edge_{base,tuned}_full.jsonl (B2/B3, test+calib+dev), edge_tuned_s{1,2}.jsonl (seed re-runs),
  cloud_{B1,A2,A3}.jsonl, scores_<run>.jsonl (test) and scores_<run>_{calib,dev}.jsonl for the gates,
  bhashabench_{base,tuned}.jsonl, rag_recall.json, cloud_metrics.json, fault_injection.json, llamacpp_bench.json
Outputs: outputs/final/summary.json (every reported number), outputs/final/hybrid_*.jsonl (+ scores_*),
  reports/final/tables/*.md, reports/final/figures/*.png
Accuracy = share of the 700 test questions judged 'correct' (strict); lenient also counts 'partly_correct'.
A question with no usable answer (missing, or an undelivered interim message) counts as wrong.

Usage: python -m src.eval.run_final
"""
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from src.data.common import detect_script, read_jsonl, write_jsonl
from src.eval.compose_scores import compose
from src.queue_sim.sim import simulate
from src.router_gate import gate as G
from src.router_gate import hybrid, intent_clf, safety_filter

D = Path("outputs/final")
R = Path("reports/final")
GROUPS = ["hi/deva", "hi/latn", "en/latn"]
GROUP_NAME = {"hi/deva": "Hindi", "hi/latn": "Hinglish", "en/latn": "English"}
LENIENT = ("correct", "partly_correct")


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, c - h), min(1.0, c + h))


def rows_or_none(p):
    return read_jsonl(p) if Path(p).exists() else None


def acc(scores, qids, strict=True):
    """Accuracy over qids; ids without a score count as wrong."""
    ok = LENIENT if not strict else ("correct",)
    sc = {s["id"]: s for s in scores}
    k = sum(sc[i]["label"] in ok for i in qids if i in sc)
    return k, len(qids)


def by_group(scores, qs, strict=True):
    out = {}
    for g in GROUPS + ["all"]:
        ids = [q["id"] for q in qs if g == "all" or f"{q['lang']}/{q['script']}" == g]
        k, n = acc(scores, ids, strict)
        lo, hi = wilson(k, n)
        out[g] = {"acc": round(k / n, 4) if n else None, "k": k, "n": n, "ci95": [round(lo, 4), round(hi, 4)]}
    return out


def paired_bootstrap(a, b, ids, n=2000, seed=0):
    """Accuracy difference a - b on the same ids, with a 95% bootstrap interval."""
    sa, sb = {s["id"]: s["label"] == "correct" for s in a}, {s["id"]: s["label"] == "correct" for s in b}
    x = np.array([sa.get(i, False) for i in ids], float)
    y = np.array([sb.get(i, False) for i in ids], float)
    rng, diffs = np.random.default_rng(seed), []
    for _ in range(n):
        j = rng.integers(0, len(ids), len(ids))
        diffs.append(x[j].mean() - y[j].mean())
    return {"diff": round(float(x.mean() - y.mean()), 4), "ci95": [round(float(np.quantile(diffs, q)), 4) for q in (0.025, 0.975)]}


def deferral_rate(scores, qids):
    sc = {s["id"]: s for s in scores}
    d = [sc[i]["deferred"] for i in qids if i in sc]
    return round(sum(d) / len(d), 4) if d else None


# ---------------------------------------------------------------- hybrid helpers

def hybrid_scores(run, out, edge_rows, edge_scores, cloud_rows, cloud_scores):
    """Compose the hybrid's labels from its parts. Rows that are neither part's judged text (an interim message
    that was never replaced, e.g. a question dropped by A4) are labelled wrong + deferred: the farmer got no answer."""
    composed, _ = compose(run, out, edge_rows, edge_scores, cloud_rows, cloud_scores, str(D))
    have = {s["id"] for s in composed}
    extra = [{"id": h["id"], "run": run, "label": "wrong", "deferred": True, "judge": "rule",
              "reason": "no answer delivered (interim message only)", "answered_by": h["answered_by"], "route": h["route"]}
             for h in out if h["id"] not in have]
    allrows = composed + extra
    write_jsonl(allrows, D / f"scores_{run}.jsonl")
    return allrows


def run_hybrid(name, qs, edge, cloud, edge_scores, cloud_scores, **kw):
    out, summary = hybrid.run(qs, {e["id"]: e for e in edge}, {c["id"]: c for c in cloud}, **kw)
    write_jsonl(out, D / f"hybrid_{name}.jsonl")
    sc = hybrid_scores(name, out, edge, edge_scores, cloud, cloud_scores)
    ids = [q["id"] for q in qs]
    k, n = acc(sc, ids)
    summary.update({"accuracy": round(k / n, 4), "lenient": round(acc(sc, ids, False)[0] / n, 4),
                    "by_group": by_group(sc, qs), "cloud_rate": round(sum(not r["kept_offline"] for r in out) / n, 4)})
    (D / f"hybrid_{name}.summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary, sc, out


# ---------------------------------------------------------------- sections

def edge_section(qs_test, S):
    res = {}
    for run, path in (("B2", D / "edge_base_full.jsonl"), ("B3", D / "edge_tuned_full.jsonl")):
        rows = rows_or_none(path)
        if not rows:
            continue
        rows = {r["id"]: r for r in rows}
        test = [rows[q["id"]] for q in qs_test if q["id"] in rows]
        match = Counter()
        for q in qs_test:
            if q["id"] in rows and rows[q["id"]]["answer"]:
                match[f"{q['lang']}/{q['script']}"] += detect_script(rows[q["id"]]["answer"])[0] == q["lang"]
        n_by = Counter(f"{q['lang']}/{q['script']}" for q in qs_test if q["id"] in rows)
        res[run] = {"n": len(test), "mean_tokens": round(float(np.mean([r["n_tokens"] for r in test])), 1),
                    "dose_shown_rate": round(sum(safety_filter.check(r["answer"])[0] for r in test) / len(test), 4),
                    "deferral_template_rate": round(sum(G.is_deferral(r["answer"]) for r in test) / len(test), 4),
                    "reply_language_match": {g: round(match[g] / n_by[g], 4) for g in GROUPS if n_by[g]} |
                                            {"all": round(sum(match.values()) / sum(n_by.values()), 4)}}
    seeds = {}
    for s in (1, 2):
        sc = rows_or_none(D / f"scores_B3_s{s}.jsonl")
        if sc:
            seeds[f"seed{s}"] = by_group(sc, qs_test)
    if seeds:
        res["B3_seed_reruns"] = seeds
    bb = {}
    for m in ("base", "tuned"):
        rows = rows_or_none(D / f"bhashabench_{m}.jsonl")
        if rows:
            k = sum(r["correct"] for r in rows)
            bb[m] = {"n": len(rows), "acc": round(k / len(rows), 4), "ci95": [round(x, 4) for x in wilson(k, len(rows))],
                     "by_level": {lv: round(np.mean([r["correct"] for r in rows if r["level"] == lv]), 4)
                                  for lv in sorted({r["level"] for r in rows if r["level"]})}}
    if bb:
        res["bhashabench_krishi_hi"] = bb
    bench = D / "llamacpp_bench.json"
    if bench.exists():
        b = json.loads(bench.read_text())
        res["gguf"] = {"file_gb": round(b["runs"][0]["model_size"] / 1e9, 2), "peak_rss_gb": round(b["peak_rss_mb"] / 1024, 2),
                       "prompt_tok_s": round(b["runs"][0]["avg_ts"], 1), "gen_tok_s": round(b["runs"][1]["avg_ts"], 1),
                       "cpu": b["runs"][0]["cpu_info"], "threads": b["runs"][0]["n_threads"], "quant": "Q4_K_M"}
        laptop = D / "llamacpp_bench_laptop.json"
        if laptop.exists():
            res["gguf_laptop"] = json.loads(laptop.read_text())
    S["edge"] = res


def gate_section(S):
    """Fit and evaluate the gates for B3 (full hybrid) and B2 (A1). Returns {run: {kind: Gate}}.
    Every token-prob cut is the target-rate quantile of the run's CALIB confidences (no labels needed), so B2, whose
    calib/dev answers were not judged (DECISIONS.md D26), still gets a calib-tuned gate."""
    fitted = {}
    S["gate"] = {}
    qs = {q["id"]: q for q in read_jsonl("data/processed/questions.jsonl")}
    for run, edge in (("B3", "edge_tuned_full"), ("B2", "edge_base_full")):
        parts = [D / f"scores_{run}{sfx}.jsonl" for sfx in ("", "_calib", "_dev")]
        if not (D / f"{edge}.jsonl").exists() or not parts[0].exists():
            continue
        rows = G.load(D / f"{edge}.jsonl", ",".join(str(p) for p in parts if p.exists()))
        out, ev, conf_by, gates = G.evaluate(rows, 0.5)
        calib = [e for e in read_jsonl(D / f"{edge}.jsonl") if qs.get(e["id"], {}).get("split") == "calib"]
        tp_cut = G.threshold_for_rate(G.Gate("token_prob", None).conf(calib), 0.5) if calib else gates["token_prob"].cut
        gates["token_prob"].cut = tp_cut
        out["token_prob"].update(G.gate_metrics(conf_by["token_prob"], [r["y"] for r in ev], tp_cut))
        out["token_prob"]["cut_from"] = "calib confidences" if calib else "eval rows"
        G.plot(ev, conf_by, str(R / "figures" / f"gate_riskcov_{run}.png"))
        for kind, g in gates.items():
            g.save(f"models/gate/{run}/gate_{kind}.pkl")
        fitted[run] = gates
        S["gate"][run] = out
    return fitted


def hybrid_section(qs, E, C, ES, CS, gates, S):
    clf = intent_clf.load()
    ids = [q["id"] for q in qs]
    res, sc_all = {}, {}
    b1_acc = acc(CS["B1"], ids)[0] / len(ids)
    gate3 = gates.get("B3", {}).get("classifier") or gates.get("B3", {}).get("token_prob")
    gate2 = gates.get("B2", {}).get("token_prob")
    configs = {  # name: (edge, cloud, kwargs)
        "H": ("B3", "B1", {"gate": gate3}),
        "H_tok": ("B3", "B1", {"gate": gates.get("B3", {}).get("token_prob")}),  # same gate type as A1
        "R": ("B3", "B1", {"gate": gate3, "mode": "random"}),
        "A1": ("B2", "B1", {"gate": gate2}),
        "H_A2": ("B3", "A2", {"gate": gate3}),
        "H_A3": ("B3", "A3", {"gate": gate3}),
    }
    for name, (e, c, kw) in configs.items():
        if e in E and c in C and e in ES and c in CS and kw.get("gate") is not None:
            # a cloud run made on part of the test set (A3: stratified half) is compared on those questions only
            have = {r["id"] for r in C[c]}
            qsub = [q for q in qs if q["id"] in have]
            summ, sc, _ = run_hybrid(name, qsub, E[e], C[c], ES[e], CS[c], clf=clf, **kw)
            b1_sub = acc(CS["B1"], [q["id"] for q in qsub])[0] / len(qsub)
            summ["pct_of_B1"] = round(summ["accuracy"] / b1_sub, 4) if b1_sub else None
            summ["n_questions"], summ["B1_acc_same_questions"] = len(qsub), round(b1_sub, 4)
            res[name], sc_all[name] = summ, sc
    # H1 trade-off: router variant x policy (all with the B3 gate, B1 cloud)
    tradeoff = {}
    if "B3" in E and "B1" in C and gate3 is not None:
        for label, router_clf, policy in (("rules+clf, safety (design)", clf, "safety"), ("rules only, safety", None, "safety"),
                                          ("rules+clf, gate_all", clf, "gate_all"), ("rules only, gate_all", None, "gate_all")):
            name = "TO_" + label.split(",")[0].replace("+", "_").replace(" ", "_") + "_" + policy
            summ, _, out = run_hybrid(name, qs, E["B3"], C["B1"], ES["B3"], CS["B1"], clf=router_clf, gate=gate3, policy=policy)
            tradeoff[label] = {"accuracy": summ["accuracy"], "pct_of_B1": round(summ["accuracy"] / b1_acc, 4) if b1_acc else None,
                               "cloud_rate": summ["cloud_rate"], "route_counts": summ["route_counts"],
                               "h1_met": bool(summ["accuracy"] >= 0.9 * b1_acc and summ["cloud_rate"] <= 0.5)}
        tradeoff["frontier"] = frontier(qs, E["B3"], C["B1"], ES["B3"], CS["B1"], gate3, clf, b1_acc)
    S["hybrid"], S["h1_tradeoff"] = res, tradeoff
    if "H" in res and "B3" in ES:
        # offline usefulness: with no link at all, the farmer still gets an answer the judge calls correct / partly
        # correct (edge answers kept offline), or the emergency numbers on an emergency question
        out = read_jsonl(D / "hybrid_H.jsonl")
        e_lab = {s["id"]: s["label"] for s in ES["B3"]}
        kept = [r for r in out if r["kept_offline"]]
        S["offline_usefulness"] = {
            "kept_offline_share": round(len(kept) / len(out), 4),
            "useful_offline_share": round(sum(e_lab.get(r["id"]) in LENIENT for r in kept) / len(out), 4),
            "correct_offline_share": round(sum(e_lab.get(r["id"]) == "correct" for r in kept) / len(out), 4),
            "kept_answer_accuracy_strict": round(sum(e_lab.get(r["id"]) == "correct" for r in kept) / max(1, len(kept)), 4),
            "kept_answer_accuracy_lenient": round(sum(e_lab.get(r["id"]) in LENIENT for r in kept) / max(1, len(kept)), 4),
            "emergency_routed": sum(r["route"] == "emergency" for r in out)}
    if "H" in res:
        h = res["H"]
        # H1 as the proposal states it (section 4): "on GENERAL farming questions, the hybrid reaches at least 90% of
        # cloud-only accuracy while sending at most 50% of THOSE questions to the cloud". General = the test label.
        hyb = {r["id"]: r for r in read_jsonl(D / "hybrid_H.jsonl")}
        gen = [q["id"] for q in qs if q["category"] == "general"]
        hg, bg = acc(sc_all["H"], gen)[0] / len(gen), acc(CS["B1"], gen)[0] / len(gen)
        cg = sum(not hyb[i]["kept_offline"] for i in gen) / len(gen)
        S["H1"] = {"definition": "general questions (proposal section 4)", "n": len(gen), "B1_acc": round(bg, 4),
                   "hybrid_acc": round(hg, 4), "pct_of_B1": round(hg / bg, 4) if bg else None, "cloud_rate": round(cg, 4),
                   "diff": paired_bootstrap(sc_all["H"], CS["B1"], gen),
                   "accuracy_ok": hg >= 0.9 * bg, "cloud_ok": cg <= 0.5, "met": bool(hg >= 0.9 * bg and cg <= 0.5)}
        # the stricter reading over all 700 questions, which counts the high-risk and live-data questions the design
        # always sends to the cloud
        S["H1_all_questions"] = {
            "B1_acc": round(b1_acc, 4), "hybrid_acc": h["accuracy"], "pct_of_B1": h["pct_of_B1"], "cloud_rate": h["cloud_rate"],
            "accuracy_ok": h["accuracy"] >= 0.9 * b1_acc, "cloud_ok": h["cloud_rate"] <= 0.5,
            "met": bool(h["accuracy"] >= 0.9 * b1_acc and h["cloud_rate"] <= 0.5),
            "best_config_meeting_cloud_target": max(((k, v) for k, v in tradeoff.items() if k != "frontier" and v["cloud_rate"] <= 0.5),
                                                    key=lambda kv: kv[1]["accuracy"], default=(None, None))[0]}
    return sc_all


def frontier(qs, edge, cloud, edge_scores, cloud_scores, gate, clf, b1_acc):
    """Accuracy vs cloud-call rate as the gate cut moves, for each router variant x policy (no queue)."""
    pts = {}
    ids = [q["id"] for q in qs]
    for label, router_clf, policy in (("rules+clf/safety", clf, "safety"), ("rules/safety", None, "safety"),
                                      ("rules+clf/gate_all", clf, "gate_all"), ("rules/gate_all", None, "gate_all")):
        pts[label] = []
        g = G.Gate(gate.kind, -1e9, gate.sc, gate.lr)  # keep everything once, to read the gated rows' confidences
        out, _ = hybrid.run(qs, {e["id"]: e for e in edge}, {c["id"]: c for c in cloud}, clf=router_clf, gate=g, policy=policy)
        conf = [r["gate_score"] for r in out if r["gate_score"] is not None]
        for keep in np.linspace(0, 1, 11):
            # cut = quantile of the gated questions' confidence, so `keep` of them stay offline
            g = G.Gate(gate.kind, -1e9 if keep >= 1 else 1e9 if keep <= 0 else float(np.quantile(conf, 1 - keep)), gate.sc, gate.lr)
            out, _ = hybrid.run(qs, {e["id"]: e for e in edge}, {c["id"]: c for c in cloud}, clf=router_clf, gate=g, policy=policy)
            composed, _ = compose("_frontier", out, edge, edge_scores, cloud, cloud_scores, str(D))
            k = sum(s["label"] == "correct" for s in composed)
            pts[label].append({"keep_share": round(float(keep), 2), "cloud_rate": round(sum(not r["kept_offline"] for r in out) / len(ids), 4),
                               "accuracy": round(k / len(ids), 4)})
    (D / "scores__frontier.jsonl").unlink(missing_ok=True)
    plot_frontier(pts, b1_acc)
    return pts


def plot_frontier(pts, b1_acc):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5.5, 3.8))
    for label, p in pts.items():
        ax.plot([x["cloud_rate"] for x in p], [x["accuracy"] for x in p], marker="o", ms=3, label=label)
    ax.axhline(0.9 * b1_acc, ls="--", c="grey", lw=1)
    ax.axvline(0.5, ls=":", c="grey", lw=1)
    ax.text(0.51, 0.9 * b1_acc, " 90% of B1", va="bottom", fontsize=8, color="grey")
    ax.set_xlabel("cloud calls per question")
    ax.set_ylabel("accuracy (strict)")
    ax.set_title("H1 trade-off: router x policy, gate cut swept")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(R / "figures" / "h1_frontier.png", dpi=150)


def queue_section(qs, E, C, ES, CS, gates, S):
    """A4 and the connectivity traces on the full hybrid (B3 + B1)."""
    gate3 = gates.get("B3", {}).get("classifier") or gates.get("B3", {}).get("token_prob")
    if not ("B3" in E and "B1" in C and gate3 is not None):
        return
    clf, res = intent_clf.load(), {}
    for trace in ("good", "patchy", "poor"):
        for queue in (True, False):
            name = f"Q_{trace}{'' if queue else '_A4'}"
            summ, _, _ = run_hybrid(name, qs, E["B3"], C["B1"], ES["B3"], CS["B1"], clf=clf, gate=gate3, trace=trace, queue=queue)
            res[name] = {"accuracy": summ["accuracy"], **summ["queue_metrics"]}
    S["queue"] = res
    S["A4"] = {t: {"with_queue": res[f"Q_{t}"]["accuracy"], "no_queue_A4": res[f"Q_{t}_A4"]["accuracy"],
                   "delivery_with_queue": res[f"Q_{t}"]["delivery_rate"], "delivery_no_queue": res[f"Q_{t}_A4"]["delivery_rate"]}
               for t in ("good", "patchy", "poor")}


def safety_section(qs, E, S):
    rm = json.loads(Path("outputs/router_metrics.json").read_text(encoding="utf-8"))
    frozen = D / "router_metrics_keywords_v1.json"
    out = {}
    for name in ("rules_only", "rules_plus_clf"):
        r = rm[name]
        out[name] = {k: {"risky_recall": r[k]["high_risk_recall"]["all"], "emergency_escalation": r[k]["emergency_escalation_rate"],
                         "emergency_number_shown": r[k].get("emergency_number_shown_rate"),
                         "control_over_escalation": r[k].get("control_over_escalation_rate")}
                     for k in ("redteam", "redteam_v2_dev", "redteam_v3_heldout")}
        out[name]["test_high_risk_recall_vs_labels"] = r["test"]["high_risk_recall"]["all"]
        out[name]["test_route_accuracy_vs_labels"] = r["test"]["accuracy"]["all"]
    if frozen.exists():
        f = json.loads(frozen.read_text(encoding="utf-8"))
        out["v2_before_keyword_fix"] = {n: {"risky_recall": f[n]["redteam_v2_heldout"]["high_risk_recall"]["all"],
                                            "emergency_escalation": f[n]["redteam_v2_heldout"]["emergency_escalation_rate"]}
                                        for n in ("rules_only", "rules_plus_clf")}
    out["filter_probes"] = {k: rm["filter"][k] for k in ("miss_rate", "false_block_rate", "n_dose", "n_safe")}
    # offline dose rate: edge answers shown offline that still contain a dose (filter after the fact = 0 by design;
    # the raw rate shows how often the filter had to act)
    h = rows_or_none(D / "hybrid_H.jsonl")
    if h:
        kept = [r for r in h if r["kept_offline"]]
        out["offline_dose_rate_shown"] = round(sum(safety_filter.check(r["final_answer"])[0] for r in kept) / max(1, len(kept)), 4)
        out["offline_answers_blocked_by_filter"] = sum(r["filter_blocked"] for r in h)
        risky_ids = {q["id"] for q in qs if q["category"] in ("high_risk",)}
        out["high_risk_label_sent_to_cloud"] = round(sum(not r["kept_offline"] for r in h if r["id"] in risky_ids) / max(1, len(risky_ids)), 4)
    if "B3" in E:
        test = {q["id"] for q in qs}
        raw = [e for e in E["B3"] if e["id"] in test]
        out["B3_raw_dose_rate"] = round(sum(safety_filter.check(e["answer"])[0] for e in raw) / len(raw), 4)
    if "B2" in E:
        test = {q["id"] for q in qs}
        raw = [e for e in E["B2"] if e["id"] in test]
        out["B2_raw_dose_rate"] = round(sum(safety_filter.check(e["answer"])[0] for e in raw) / len(raw), 4)
    S["safety"] = out


# ---------------------------------------------------------------- tables

def pct(x):
    return "n/a" if x is None else f"{100 * x:.1f}"


def write_tables(S):
    T = R / "tables"
    T.mkdir(parents=True, exist_ok=True)
    md = []
    runs = S.get("runs", {})
    if runs:
        md.append("| Run | What | Hindi | Hinglish | English | All (strict) [95% CI] | All (lenient) | Deferred | Cloud calls /100 |\n|---|---|---|---|---|---|---|---|---|")
        for run, r in runs.items():
            g = r["strict"]
            md.append(f"| {run} | {r['what']} | " + " | ".join(pct(g[x]["acc"]) for x in GROUPS) +
                      f" | {pct(g['all']['acc'])} [{pct(g['all']['ci95'][0])}-{pct(g['all']['ci95'][1])}] | {pct(r['lenient'])} | {pct(r['deferred'])} | {r['cloud_per_100']} |")
        (T / "main_results.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (T / "summary.json").write_text(json.dumps(S, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    for p in (D, R / "figures", R / "tables", Path("models/gate")):
        p.mkdir(parents=True, exist_ok=True)
    allq = {q["id"]: q for q in read_jsonl("data/processed/questions.jsonl")}
    qs = [q for q in allq.values() if q["split"] == "test"]
    gold = {g["id"] for g in read_jsonl("data/processed/gold.jsonl")}
    E = {k: r for k, p in (("B2", "edge_base_full"), ("B3", "edge_tuned_full")) if (r := rows_or_none(D / f"{p}.jsonl"))}
    C = {k: r for k in ("B1", "A2", "A3") if (r := rows_or_none(D / f"cloud_{k}.jsonl"))}
    SC = {k: r for k in ("B1", "A2", "A3", "B2", "B3") if (r := rows_or_none(D / f"scores_{k}.jsonl"))}
    ES, CS = {k: SC[k] for k in ("B2", "B3") if k in SC}, {k: SC[k] for k in ("B1", "A2", "A3") if k in SC}
    S = {"n_test": len(qs), "judge": "gemma-4-31b-it (minimal thinking)", "cloud_model": "gemma-4-26b-a4b-it",
         "edge_model": "Llama-3.2-3B-Instruct (+ QLoRA r16, 2 epochs, seed 42 for B3)"}

    edge_section(qs, S)
    gates = gate_section(S)
    sc_h = hybrid_section(qs, E, C, ES, CS, gates, S)
    queue_section(qs, E, C, ES, CS, gates, S)
    safety_section(qs, E, S)
    for name in ("rag_recall", "cloud_metrics", "fault_injection"):
        if (D / f"{name}.json").exists():
            S[name] = json.loads((D / f"{name}.json").read_text(encoding="utf-8"))

    what = {"B1": "cloud: LLM + RAG + tools", "A2": "cloud without RAG", "A3": "cloud without tools", "B2": "edge base",
            "B3": "edge tuned", "H": "hybrid (B3 + B1)", "R": "random routing, same cloud rate", "A1": "hybrid with base edge (B2 + B1)",
            "H_A2": "hybrid, cloud without RAG", "H_A3": "hybrid, cloud without tools",
            "H_tok": "hybrid (B3 + B1), token-prob gate"}
    ids, S["runs"], S["runs_gold"] = [q["id"] for q in qs], {}, {}
    for run in ("B2", "B3", "B1", "A2", "A3", "H", "H_tok", "R", "A1", "H_A2", "H_A3"):
        sc = SC.get(run) or sc_h.get(run)
        if not sc:
            continue
        cloud = 100 if run in C else 0 if run in E else round(100 * S["hybrid"][run]["cloud_rate"], 1)
        cl = run if run in C else {"H_A2": "A2", "H_A3": "A3"}.get(run)
        rq = [q for q in qs if q["id"] in {r["id"] for r in C[cl]}] if cl else qs  # A3: its 350-question half
        rids = [q["id"] for q in rq]
        S["runs"][run] = {"what": what[run] + ("" if len(rq) == len(qs) else f" ({len(rq)}-question stratified half)"),
                          "n": len(rq), "strict": by_group(sc, rq), "lenient": round(acc(sc, rids, False)[0] / len(rids), 4),
                          "deferred": deferral_rate(sc, rids), "cloud_per_100": cloud}
        if run in ("A2", "A3") and "B1" in SC:  # the cloud ablations, paired with B1 on the same questions
            S["runs"][run]["vs_B1_same_questions"] = paired_bootstrap(sc, SC["B1"], rids) | {
                "B1_acc": round(acc(SC["B1"], rids)[0] / len(rids), 4)}
        gq = [q for q in rq if q["id"] in gold]
        S["runs_gold"][run] = {"strict": by_group(sc, gq), "lenient": round(acc(sc, [q["id"] for q in gq], False)[0] / len(gq), 4)}
    # paired comparisons on the same questions (difference in strict accuracy, 95% bootstrap interval)
    allsc = {**SC, **sc_h}
    S["comparisons"] = {f"{a}_minus_{b}": paired_bootstrap(allsc[a], allsc[b], ids)
                        for a, b in (("H", "B1"), ("H", "R"), ("H", "A1"), ("H_tok", "A1"), ("H", "H_tok"), ("B1", "B3"))
                        if a in allsc and b in allsc}
    if "B2" in SC and "B3" in SC:
        hindi =[q["id"] for q in qs if q["script"] == "deva"]
        S["H2"] = {"hindi_deva": paired_bootstrap(SC["B3"], SC["B2"], hindi), "all": paired_bootstrap(SC["B3"], SC["B2"], ids),
                   "hinglish": paired_bootstrap(SC["B3"], SC["B2"], [q["id"] for q in qs if q["lang"] == "hi" and q["script"] == "latn"]),
                   "english": paired_bootstrap(SC["B3"], SC["B2"], [q["id"] for q in qs if q["lang"] == "en"])}
        nd = [i for i in hindi if not G.is_deferral(next((e["answer"] for e in E["B3"] if e["id"] == i), ""))]
        S["H2"]["hindi_deva_non_deferred"] = paired_bootstrap(SC["B3"], SC["B2"], nd) | {"n": len(nd)}
        S["H2"]["met"] = S["H2"]["hindi_deva"]["diff"] >= 0.10
    if "gate" in S and "B3" in S["gate"]:
        g = S["gate"]["B3"]
        S["H3"] = {"token_prob_auroc": g["token_prob"]["auroc"],
                   "classifier_auroc": g["classifier"]["auroc"] if isinstance(g["classifier"], dict) else None,
                   "met": g.get("h3_classifier_beats_token_prob"), "bootstrap": g.get("h3_bootstrap")}
    (D / "summary.json").write_text(json.dumps(S, ensure_ascii=False, indent=1), encoding="utf-8")
    write_tables(S)
    print(json.dumps({k: S[k] for k in ("H1", "H2", "H3") if k in S}, indent=1))
    print("wrote", D / "summary.json")


if __name__ == "__main__":
    main()
