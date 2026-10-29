"""Connectivity traces + send queue, simulated in discrete ticks (1 tick = 1 minute). See docs/kiran/DECISIONS.md D8-D10.

A job is a question that must reach the cloud. Each tick: new jobs arrive; if the link is up, up to CAP queued jobs
are sent in priority order (emergency first). A send succeeds with the trace's success rate; a failure backs off
2^tries ticks (max 64) and a job gives up after MAX_TRIES. Jobs with the same dedup key share one send.
A live_data answer that waited longer than LIVE_TTL is "stale": we count it, then re-ask once (one extra send).

ponytail: cloud answers are precomputed (B1), so a send is just a coin flip, not a real request. If the real client
is wired in, replace `ok = rng.random() < P_OK` with the client call; the queue logic stays.
"""
import random
from collections import defaultdict

# link state per kind: P(up->down), P(down->up) per tick, and P(send succeeds | link up)
TRACES = {
    "good":   {"drop": 0.01, "recover": 0.50, "p_ok": 0.98},
    "patchy": {"drop": 0.15, "recover": 0.20, "p_ok": 0.70},
    "poor":   {"drop": 0.30, "recover": 0.05, "p_ok": 0.40},
}
PRIORITY = {"emergency": 0, "high_risk": 1, "live_data": 2, "general": 3}
CAP, MAX_TRIES, LIVE_TTL, BACKOFF_MAX = 3, 6, 60, 64


def make_trace(kind, n, seed=0):
    """List of n booleans: link up at each tick. 'none' = always up."""
    if kind == "none":
        return [True] * n
    p, rng, up, out = TRACES[kind], random.Random(seed), True, []
    for _ in range(n):
        out.append(up)
        up = (rng.random() >= p["drop"]) if up else (rng.random() < p["recover"])
    return out


def simulate(jobs, kind="patchy", queue=True, dedup=True, horizon=2000, seed=0):
    """jobs: dicts with id, arrive (tick), category, key (dedup key), live (bool).
    Returns ({id: {queued_at, delivered_at, sends, stale}}, metrics). queue=False is ablation A4: a job that
    arrives while the link is down is dropped, and nothing is retried."""
    trace, rng = make_trace(kind, horizon, seed), random.Random(seed + 1)
    p_ok = TRACES.get(kind, {"p_ok": 1.0})["p_ok"]
    res = {j["id"]: {"queued_at": j["arrive"], "delivered_at": None, "sends": 0, "stale": False} for j in jobs}
    by_tick = defaultdict(list)
    for j in jobs:
        by_tick[j["arrive"]].append(j)
    pending, done_key, waiters, tries, nxt = [], {}, defaultdict(list), {}, {}
    sends = dups = 0
    for t in range(horizon):
        up = trace[t]
        for j in by_tick[t]:
            fresh = j["key"] in done_key and not (j["live"] and t - done_key[j["key"]] > LIVE_TTL)
            if dedup and fresh:                      # cache hit: answered with no send
                res[j["id"]]["delivered_at"] = t
            elif dedup and any(p["key"] == j["key"] for p in pending):
                waiters[j["key"]].append(j)          # same question already queued: share its send
            elif queue or up:
                pending.append(j)
                tries[j["id"]], nxt[j["id"]] = 0, t
            # else: A4 and link down -> dropped
        if not up:
            continue
        ready = sorted((j for j in pending if nxt[j["id"]] <= t), key=lambda j: (PRIORITY[j["category"]], j["arrive"]))
        for j in ready[:CAP]:
            r = res[j["id"]]
            r["sends"] += 1
            sends += 1
            if j["key"] in done_key and not j["live"]:
                dups += 1                            # successful earlier send of the same key: wasted
            if rng.random() < p_ok:
                if j["live"] and t - j["arrive"] > LIVE_TTL:
                    r["stale"] = True                # data aged in the queue: re-ask once
                    r["sends"] += 1
                    sends += 1
                r["delivered_at"] = t
                done_key[j["key"]] = t
                pending.remove(j)
                for w in waiters.pop(j["key"], []):
                    res[w["id"]]["delivered_at"] = t
            else:
                tries[j["id"]] += 1
                nxt[j["id"]] = t + min(2 ** tries[j["id"]], BACKOFF_MAX)
                if tries[j["id"]] >= MAX_TRIES:
                    pending.remove(j)
    return res, metrics(jobs, res, sends, dups)


def metrics(jobs, res, sends, dups):
    waits = sorted(r["delivered_at"] - r["queued_at"] for r in res.values() if r["delivered_at"] is not None)
    live = [r for j in jobs if j["live"] and (r := res[j["id"]])["delivered_at"] is not None]
    pct = lambda p: waits[min(len(waits) - 1, int(p * len(waits)))] if waits else None
    return {"jobs": len(jobs), "delivery_rate": round(len(waits) / max(1, len(jobs)), 3),
            "p50_ticks": pct(0.5), "p90_ticks": pct(0.9),
            "stale_rate": round(sum(r["stale"] for r in live) / len(live), 3) if live else 0.0,
            "duplicate_send_rate": round(dups / sends, 3) if sends else 0.0, "sends": sends}


if __name__ == "__main__":
    # Queue metrics on the real test routes (outputs/router.jsonl), no model outputs needed: every non-general question
    # is a job, plus a random half of the general ones (the gate's target). -> outputs/queue_metrics.json
    import json
    from pathlib import Path
    from src.data.common import read_jsonl
    qs = {q["id"]: q for q in read_jsonl("data/processed/questions.jsonl")}
    rng, jobs = random.Random(0), []
    for i, r in enumerate(read_jsonl("outputs/router.jsonl")):
        if r["route"] != "general" or rng.random() < 0.5:
            jobs.append({"id": r["id"], "arrive": len(jobs), "category": r["route"], "live": r["route"] == "live_data",
                         "key": " ".join(qs[r["id"]]["question"].lower().split())})
    out = {f"{kind}{'' if q else '_no_queue(A4)'}": simulate(jobs, kind, queue=q, horizon=len(jobs) * 4)[1]
           for kind in ("good", "patchy", "poor") for q in (True, False)}
    Path("outputs/queue_metrics.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k, v)
