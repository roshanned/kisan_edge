import random

import pytest

from src.router_gate import gate, hybrid, safety_filter
from src.router_gate.router import Router, rule_route


@pytest.mark.parametrize("q,cat", [
    ("bachche ne keetnashak pee liya", "emergency"), ("खेत में सांप ने काट लिया", "emergency"),
    ("Can I mix mancozeb and cypermethrin?", "high_risk"), ("फसल बीमा दावा खारिज हो गया", "high_risk"),
    ("kal ka mausam kaisa rahega", "live_data"), ("mandi bhav kya hai", "live_data"),
    ("aage kya karein", None), ("wheat sowing time", None)])
def test_rules(q, cat):
    assert rule_route(q)[0] == cat


def test_emergency_beats_high_risk_and_default_is_general():
    assert Router().route("spray ke baad behosh ho gaya")["category"] == "emergency"
    assert Router().route("wheat sowing time")["category"] == "general"


@pytest.mark.parametrize("t", ["Spray 2 ml per litre", "२५० ग्राम प्रति एकड़", "do chammach dawa", "आधा लीटर पानी", "ek bottle dawa", "5 mL/L", "40 kg seed"])
def test_filter_blocks_doses(t):
    assert safety_filter.check(t)[0]


@pytest.mark.parametrize("t", ["Irrigate after 21 days of sowing", "KCC 1551 पर कॉल करें", "बुवाई अक्टूबर में करें", "Call 108 now"])
def test_filter_lets_safe_text_through(t):
    assert not safety_filter.check(t)[0]


def fake_rows(n, split, seed):
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        y = int(rng.random() < 0.5)
        lp = -(0.4 + rng.random() * (0.6 if y else 1.4))
        rows.append({"id": f"{split}{i}", "split": split, "answer": "x" * rng.randint(5, 80), "mean_logprob": lp, "min_logprob": 3 * lp,
                     "n_tokens": 30, "lang": "hi", "script": "deva", "category": "general", "crop_known": True, "y": y, "group": "hi/deva"})
    return rows


def test_gate_evaluate_with_classifier_and_rate():
    rows = fake_rows(300, "dev", 1) + fake_rows(300, "calib", 2) + fake_rows(300, "test", 3)
    out, ev, conf, cut = gate.evaluate(rows, 0.5)
    assert len(ev) == 300 and not out["phase1_no_calib"]
    assert out["token_prob"]["auroc"] > 0.6 and isinstance(out["classifier"], dict)
    assert abs(out["token_prob"]["cloud_call_rate"] - 0.5) < 0.1


def test_aurc_prefers_good_confidence():
    y = [1, 1, 0, 0]
    assert gate.aurc([4, 3, 2, 1], y) < gate.aurc([1, 2, 3, 4], y)


def mini(n=40):
    qs = [{"id": f"q{i}", "question": "bachche ne pee liya" if i % 10 == 0 else "wheat sowing time", "lang": "hi", "script": "latn"} for i in range(n)]
    edge = {q["id"]: {"id": q["id"], "answer": "ek acre me 2 kg" if i % 4 == 0 else "pani dein", "mean_logprob": -0.1 * i} for i, q in enumerate(qs)}
    cloud = {q["id"]: {"id": q["id"], "answer": "cloud answer"} for q in qs}
    return qs, edge, cloud


def test_hybrid_never_shows_a_dose_and_emergency_always_goes_to_cloud():
    qs, edge, cloud = mini()
    out, s = hybrid.run(qs, edge, cloud, trace="none")
    for r in out:
        assert not safety_filter.check(r["interim_answer"])[0]
        if r["route"] == "emergency":
            assert not r["kept_offline"] and r["answered_by"] == "cloud"
    assert all(r["answered_by"] != "edge" or not r["filter_blocked"] for r in out)


def test_hybrid_offline_gives_deferral_not_silence_and_emergency_numbers():
    qs, edge, cloud = mini()
    out, _ = hybrid.run(qs, edge, cloud, trace="poor", queue=False)  # nothing delivered after a drop
    em = [r for r in out if r["route"] == "emergency" and r["delivered_at"] is None]
    assert all("108" in r["final_answer"] and "1551" in r["final_answer"] for r in em)
    assert all(r["final_answer"] for r in out)


def test_random_mode_sends_same_number_as_gate():
    qs, edge, cloud = mini()
    g, _ = hybrid.run(qs, edge, cloud, mode="gate")
    r, _ = hybrid.run(qs, edge, cloud, mode="random")
    sent = lambda o: sum(not x["kept_offline"] and x["route"] == "general" and not x["filter_blocked"] for x in o)
    assert abs(sent(g) - sent(r)) <= sum(x["filter_blocked"] for x in g)  # blocked ones are sent in both modes
