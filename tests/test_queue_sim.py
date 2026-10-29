from src.queue_sim.sim import make_trace, simulate


def jobs(n, cat="general", live=False, key=lambda i: i, every=1):
    return [{"id": f"q{i}", "arrive": i * every, "category": cat, "key": key(i), "live": live} for i in range(n)]


def test_always_up_delivers_everything():
    res, m = simulate(jobs(30), kind="none")
    assert m["delivery_rate"] == 1.0 and all(r["delivered_at"] is not None for r in res.values())


def test_trace_is_seeded_and_poor_is_worse_than_good():
    assert make_trace("patchy", 200, 1) == make_trace("patchy", 200, 1)
    assert sum(make_trace("poor", 2000, 1)) < sum(make_trace("good", 2000, 1))


def test_no_queue_drops_jobs_that_arrive_offline():
    _, with_q = simulate(jobs(200), kind="poor", queue=True, horizon=3000)
    _, no_q = simulate(jobs(200), kind="poor", queue=False, horizon=3000)
    assert no_q["delivery_rate"] < with_q["delivery_rate"]


def test_emergency_goes_before_general():
    js = [{"id": "g", "arrive": 0, "category": "general", "key": "g", "live": False}] * 1 + \
         [{"id": f"e{i}", "arrive": 0, "category": "emergency", "key": f"e{i}", "live": False} for i in range(3)]
    res, _ = simulate(js, kind="none")
    assert max(res[f"e{i}"]["delivered_at"] for i in range(3)) <= res["g"]["delivered_at"]


def test_dedup_removes_duplicate_sends():
    same = lambda i: "same question"
    _, on = simulate(jobs(40, key=same, every=70), kind="none", dedup=True)
    _, off = simulate(jobs(40, key=same, every=70), kind="none", dedup=False)
    assert on["sends"] < off["sends"] and off["duplicate_send_rate"] > 0


def test_stale_live_answer_is_flagged_and_reasked():
    res, m = simulate(jobs(60, cat="live_data", live=True), kind="poor", horizon=4000, seed=3)
    assert m["stale_rate"] > 0 and any(r["stale"] and r["sends"] >= 2 for r in res.values())
