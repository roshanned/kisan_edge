"""Hybrid runner: router + gate + safety filter + queue over PRECOMPUTED edge and cloud outputs (no new model calls).

  full hybrid : --edge outputs/edge_tuned.jsonl --cloud outputs/cloud_B1.jsonl            (B3 + B1)
  A1          : --edge outputs/edge_base.jsonl  --cloud outputs/cloud_B1.jsonl            (B2 + B1)
  R           : add --mode random   (same cloud rate as the gate would use, but random pick among general Qs)
  A4          : add --no-queue --trace patchy   (offline Qs are dropped, nothing retried)
Per question: emergency/high_risk/live_data -> always cloud. general -> cloud if edge confidence < cut or the safety filter
blocks the edge answer, else kept offline. Output = PLAN.md section 5 router format, plus extra fields (DECISIONS.md D7).
Usage: python -m src.router_gate.hybrid --edge ... --cloud ... --splits test --out outputs/hybrid_B3_B1.jsonl
"""
import argparse
import json
import random
from pathlib import Path

import numpy as np

from src.common.schemas import check
from src.data.common import read_jsonl, write_jsonl
from src.queue_sim.sim import simulate
from src.router_gate import intent_clf, safety_filter
from src.router_gate.gate import threshold_for_rate
from src.router_gate.router import EMERGENCY_NUMBERS, Router

INTERIM = {  # shown at once when the cloud answer is not there yet (offline or queued)
    "emergency": {"hi": f"यह आपातकाल हो सकता है। तुरंत कॉल करें: {EMERGENCY_NUMBERS}.",
                  "en": f"This may be an emergency. Call now: {EMERGENCY_NUMBERS}."},
    "high_risk": {"hi": "इस सवाल का सुरक्षित जवाब विशेषज्ञ से लें (KCC 1551)। इंटरनेट आते ही हम जाँचा हुआ जवाब भेजेंगे।",
                  "en": "Please check this with an expert (KCC 1551). We will send a checked answer as soon as you are online."},
    "live_data": {"hi": "ताज़ा जानकारी के लिए इंटरनेट चाहिए। इंटरनेट आते ही जवाब मिलेगा।",
                  "en": "This needs live data. You will get the answer as soon as you are online."},
}


def run(questions, edge, cloud, mode="gate", target_rate=0.5, trace="none", queue=True, clf=None, seed=0, every=1):
    router = Router(clf)
    plan = []
    for q in questions:
        e = edge.get(q["id"])
        r = router.route(q["question"])
        lang = "hi" if q["lang"] == "hi" else "en"
        blocked = False
        shown = None
        if e is not None:
            shown, blocked = safety_filter.apply(e["answer"], lang)
        plan.append({"q": q, "e": e, "cat": r["category"], "reason": r["reason"], "lang": lang, "blocked": blocked, "shown": shown})
    general = [p for p in plan if p["cat"] == "general" and p["e"] is not None]
    conf = [p["e"]["mean_logprob"] for p in general]
    cut = threshold_for_rate(conf, target_rate)
    gate_send = {p["q"]["id"] for p in general if p["e"]["mean_logprob"] < cut}
    if mode == "random":  # same number of sends as the gate, picked at random: the sanity-check baseline R
        gate_send = set(random.Random(seed).sample([p["q"]["id"] for p in general], len(gate_send)))
    for p in plan:
        qid = p["q"]["id"]
        if p["cat"] != "general":
            p["send"] = True
        elif p["e"] is None:
            p["send"] = True  # no edge answer at all: only the cloud can help
        else:
            p["send"] = qid in gate_send or p["blocked"]  # a blocked dose is never shown: ask the cloud
    jobs = [{"id": p["q"]["id"], "arrive": i * every, "category": p["cat"], "live": p["cat"] == "live_data",
             "key": " ".join(p["q"]["question"].lower().split())} for i, p in enumerate(plan) if p["send"]]
    sim, qmetrics = simulate(jobs, kind=trace, queue=queue, horizon=max(2000, len(plan) * every * 3), seed=seed) if jobs else ({}, {})
    out = []
    for i, p in enumerate(plan):
        qid, arrive = p["q"]["id"], i * every
        interim = p["shown"] if p["cat"] == "general" and p["shown"] and not p["blocked"] else INTERIM.get(p["cat"], INTERIM["high_risk"])[p["lang"]]
        row = {"id": qid, "route": p["cat"], "gate_score": p["e"]["mean_logprob"] if p["e"] else None, "kept_offline": not p["send"],
               "final_answer": interim, "answered_by": "edge" if not p["send"] else "deferral", "queued_at": None, "delivered_at": arrive if not p["send"] else None,
               "route_reason": p["reason"], "filter_blocked": p["blocked"], "interim_answer": interim}
        if p["send"]:
            s = sim[qid]
            row["queued_at"] = s["queued_at"]
            row["delivered_at"] = s["delivered_at"]
            row["stale_reasked"] = s["stale"]
            if s["delivered_at"] is not None and qid in cloud:
                row["final_answer"], row["answered_by"] = cloud[qid]["answer"], "cloud"
        out.append(check("router", row))
    n = len(out)
    summary = {"n": n, "mode": mode, "trace": trace, "queue": queue, "target_rate": target_rate,
               "cloud_calls_per_100": round(100 * sum(not r["kept_offline"] for r in out) / n, 1) if n else 0,
               "answered_by": {k: sum(r["answered_by"] == k for r in out) for k in ("edge", "cloud", "deferral")},
               "filter_blocked": sum(r["filter_blocked"] for r in out), "queue_metrics": qmetrics,
               "route_counts": {c: sum(r["route"] == c for r in out) for c in ("general", "live_data", "high_risk", "emergency")}}
    return out, summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--edge", required=True)
    ap.add_argument("--cloud", required=True)
    ap.add_argument("--splits", default="test", help="comma list; use 'gold' for the 200 gold questions")
    ap.add_argument("--mode", choices=["gate", "random"], default="gate")
    ap.add_argument("--target-rate", type=float, default=0.5)
    ap.add_argument("--trace", choices=["none", "good", "patchy", "poor"], default="none")
    ap.add_argument("--no-queue", action="store_true")
    ap.add_argument("--no-clf", action="store_true", help="rules only, ignore models/intent_clf.pkl")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    qs = read_jsonl("data/processed/questions.jsonl")
    if a.splits == "gold":
        gold = {g["id"] for g in read_jsonl("data/processed/gold.jsonl")}
        qs = [q for q in qs if q["id"] in gold]
    else:
        qs = [q for q in qs if q["split"] in a.splits.split(",")]
    edge = {e["id"]: e for e in read_jsonl(a.edge)}
    cloud = {c["id"]: c for c in read_jsonl(a.cloud)}
    qs = [q for q in qs if q["id"] in edge or q["id"] in cloud]
    if a.limit:
        qs = qs[: a.limit]
    out, summary = run(qs, edge, cloud, a.mode, a.target_rate, a.trace, not a.no_queue, None if a.no_clf else intent_clf.load(), a.seed)
    write_jsonl(out, a.out)
    Path(a.out).with_suffix(".summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
