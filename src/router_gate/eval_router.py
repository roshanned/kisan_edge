"""Router and offline-filter metrics -> outputs/router_metrics.json. No model outputs needed.

high-risk recall   = red-team rows labelled high_risk/emergency that the router sends to high_risk/emergency
emergency escalation = red-team emergency rows routed to 'emergency'
emergency number shown = emergency rows routed to emergency OR high_risk (both offline messages show 108 / 112)
over-escalation    = v2 control rows (ordinary questions that share words with risky ones) routed to high_risk/emergency
filter miss rate   = dose probes (should_block) that the filter lets through; false-block = safe probes it blocks
Red-team v1 was written by the keyword lists' author; v2 was held out until its misses were used to add keywords
(Nov 11; the held-out v2 result is outputs/final/router_metrics_keywords_v1.json); v3 is the held-out set now.
Also reports router accuracy vs the (noisy, first-pass) labels on dev and test, per script.
Usage: python -m src.router_gate.eval_router
"""
import json
from collections import defaultdict
from pathlib import Path

from src.data.common import read_jsonl
from src.router_gate import intent_clf, safety_filter
from src.router_gate.router import Router

RISKY = {"high_risk", "emergency"}


def redteam(router, path="data/processed/redteam.jsonl"):
    rows = read_jsonl(path)
    risky = [r for r in rows if r["category"] in RISKY]
    out, misses = defaultdict(lambda: [0, 0]), []
    for r in risky:
        got = router.route(r["question"])["category"]
        for key in ("all", r["script"] if r["lang"] == "hi" else "en", r["kind"]):
            out[key][1] += 1
            out[key][0] += got in RISKY
        if got not in RISKY:
            misses.append({"id": r["id"], "got": got, "q": r["question"]})
    emerg = [r for r in rows if r["category"] == "emergency"]
    esc = [r for r in emerg if router.route(r["question"])["category"] == "emergency"]
    shown = [r for r in emerg if router.route(r["question"])["category"] in RISKY]  # both interim messages show 108/112
    res = {"high_risk_recall": {k: round(a / b, 3) for k, (a, b) in out.items()},
           "emergency_escalation_rate": round(len(esc) / len(emerg), 3),
           "emergency_number_shown_rate": round(len(shown) / len(emerg), 3), "n": len(risky), "missed": misses,
           "emergency_not_escalated": [r["question"] for r in emerg if r not in esc]}
    controls = [r for r in rows if r["kind"] == "control"]
    if controls:
        over = [r for r in controls if router.route(r["question"])["category"] in RISKY]
        res["control_over_escalation_rate"] = round(len(over) / len(controls), 3)
        res["n_controls"] = len(controls)
        res["over_escalated"] = [r["question"] for r in over]
    return res


def vs_labels(router, split):
    labels = {r["id"]: r for r in read_jsonl("data/processed/router_labels.jsonl") if r["split"] == split}
    qs = {q["id"]: q["question"] for q in read_jsonl("data/processed/questions.jsonl") if q["id"] in labels}
    acc, risk = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for i, r in labels.items():
        got = router.route(qs[i])["category"]
        key = f"{r['lang']}/{r['script']}"
        for k in ("all", key):
            acc[k][1] += 1
            acc[k][0] += got == r["label"]
            if r["label"] in RISKY:
                risk[k][1] += 1
                risk[k][0] += got in RISKY
    f = lambda d: {k: round(a / b, 3) for k, (a, b) in d.items() if b}
    return {"accuracy": f(acc), "high_risk_recall": f(risk), "n": len(labels)}


def filter_metrics():
    probes = read_jsonl("data/processed/filter_probe.jsonl")
    pos, neg = [p for p in probes if p["should_block"]], [p for p in probes if not p["should_block"]]
    miss = [p["text"] for p in pos if not safety_filter.check(p["text"])[0]]
    fb = [p["text"] for p in neg if safety_filter.check(p["text"])[0]]
    return {"miss_rate": round(len(miss) / len(pos), 3), "false_block_rate": round(len(fb) / len(neg), 3),
            "n_dose": len(pos), "n_safe": len(neg), "missed": miss, "false_blocks": fb}


def main():
    clf = intent_clf.load()
    v2, v3 = "data/processed/redteam_v2.jsonl", "data/processed/redteam_v3.jsonl"
    each = lambda r: {"redteam": redteam(r), "redteam_v2_dev": redteam(r, v2), "redteam_v3_heldout": redteam(r, v3),
                      "dev": vs_labels(r, "dev"), "test": vs_labels(r, "test")}
    res = {"rules_only": each(Router()),
           "rules_plus_clf": each(Router(clf)) if clf else "intent_clf not trained: run python -m src.router_gate.intent_clf",
           "filter": filter_metrics()}
    Path("outputs").mkdir(exist_ok=True)
    Path("outputs/router_metrics.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for name in ("rules_only", "rules_plus_clf"):
        if isinstance(res[name], dict):
            r = res[name]
            v = r["redteam_v3_heldout"]
            print(name, "| v3 held-out recall", v["high_risk_recall"]["all"], "emergency", v["emergency_escalation_rate"],
                  "over-escalation", v["control_over_escalation_rate"])
            print(name, "| redteam recall", r["redteam"]["high_risk_recall"]["all"], "emergency", r["redteam"]["emergency_escalation_rate"],
                  "| test acc", r["test"]["accuracy"]["all"], "test risk recall", r["test"]["high_risk_recall"]["all"])
    print("filter", {k: v for k, v in res["filter"].items() if k.endswith("rate")})


if __name__ == "__main__":
    main()
