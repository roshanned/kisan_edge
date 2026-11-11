"""Tests for the final-phase additions: pacing, cloud metrics, fault injection, judge checks, gate policy."""
import time

import numpy as np

from src.cloud import fault_injection, metrics
from src.common.ratelimit import Pacer, estimate_tokens, retry_after
from src.eval import judge_check
from src.router_gate import gate, hybrid


def test_pacer_holds_token_budget():
    p = Pacer(rpm=100, tpm=1000)
    t = time.time()
    p.wait(600)
    p.wait(300)
    assert time.time() - t < 1  # 900 tokens fit in the minute
    assert sum(x for _, x in p.sent) == 900 and estimate_tokens("x" * 300) > 0


def test_retry_after_reads_the_api_hint():
    assert abs(retry_after("Please retry in 3.39s.", 10) - 4.39) < 1e-9
    assert retry_after("no hint", 10) == 10


def test_tool_metrics_choice_and_district():
    qs = {"a": {"question": "kal barish hogi kya", "district": "Kheri"},
          "b": {"question": "gehu me khad kab dale", "district": "Agra"}}
    rows = [{"id": "a", "tool_calls": [{"name": "get_weather", "args": {"district": "Lakhimpur Kheri"}, "status": "ok"}]},
            {"id": "b", "tool_calls": [{"name": "delete_files", "args": {}, "status": "error"}]}]
    m = metrics.tool_metrics(rows, qs)
    assert m["tool_choice_accuracy"] == 1.0 and m["needless_tool_call_rate"] == 1.0
    assert m["weather_district_matches_farmer"] == 1.0  # alias: lakhimpur kheri -> kheri
    assert m["unapproved_action_rate"] == 0.5


def test_fault_classify_flags_invented_numbers():
    res = {"tool_calls": [{"name": "get_weather", "status": "error"}], "answer": "Kal 12 mm barish hogi."}
    c = fault_injection.classify(res)
    assert not c["got_data"] and c["states_numbers"]
    res = {"tool_calls": [{"name": "get_weather", "status": "error"}], "answer": "Mausam ki jankari abhi uplabdh nahi hai."}
    c = fault_injection.classify(res)
    assert not c["states_numbers"] and c["says_unavailable"]


def test_faulty_tools_transient_then_ok():
    t = fault_injection.FaultyTools("2026-10-30", "5xx", persistent=False)
    first, s1 = t.call("get_weather", {"district": "Bareilly"})
    assert s1 == "error" and first.startswith("ERROR 503")
    _, s2 = t.call("get_weather", {"district": "Nowhere"})
    assert s2 == "error"  # second call reaches the real tool (unknown district)


def test_stratified_sample_covers_every_bucket():
    rows = [{"run": r, "lang": l, "script": "deva"} for r in ("B1", "B3") for l in ("hi", "en") for _ in range(10)]
    picked = judge_check.stratified(rows, 8, 0, ("run", "lang", "script"))
    assert len(picked) == 8 and len({(p["run"], p["lang"]) for p in picked}) == 4


def test_gate_all_policy_lets_high_risk_through_the_gate():
    qs = [{"id": f"q{i}", "question": "dhan me keetnashak ki dawa" if i % 2 else "gehu ki buvai kab kare", "lang": "hi",
           "script": "latn", "crop": "paddy", "category": "general"} for i in range(20)]
    edge = {q["id"]: {"id": q["id"], "answer": "pani dein", "mean_logprob": -0.1, "min_logprob": -1.0, "n_tokens": 5} for q in qs}
    cloud = {q["id"]: {"id": q["id"], "answer": "cloud"} for q in qs}
    keep_all = gate.Gate("token_prob", -1e9)
    safe, _ = hybrid.run(qs, edge, cloud, gate=keep_all, policy="safety")
    loose, _ = hybrid.run(qs, edge, cloud, gate=keep_all, policy="gate_all")
    risky = [r for r in safe if r["route"] == "high_risk"]
    assert risky and all(not r["kept_offline"] for r in risky)
    assert all(r["kept_offline"] for r in loose if r["route"] == "high_risk")


def test_high_risk_interim_shows_emergency_numbers():
    for lang in ("hi", "en"):
        assert "108" in hybrid.INTERIM["high_risk"][lang] and "112" in hybrid.INTERIM["high_risk"][lang]


def test_deferral_detected_and_unknown_rate_bounded():
    from src.edge.prompts import HIGH_RISK_ANSWER
    assert gate.is_deferral(HIGH_RISK_ANSWER["deva"]) and not gate.is_deferral("पानी दें")
    assert 0.0 <= gate.unknown_rate("zzqx gehu") <= 1.0


def test_bootstrap_h3_prefers_the_better_score():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 300)
    good, noise = y + rng.normal(0, 0.5, 300), rng.normal(0, 1, 300)
    assert gate.bootstrap_h3(y, good, noise, n=200)["p_classifier_better"] > 0.95


def test_cloud_filter_keeps_tool_backed_weather_but_not_chemical_doses():
    from src.cloud import safety
    weather = "* **30 अक्टूबर:** अधिकतम तापमान 28.4°C, बारिश की संभावना 84% है।"
    dose = "कार्बेन्डाजिम 0.1% का छिड़काव करें।"
    assert safety.apply(weather, {"tool:get_weather"})[1] == []           # forecast from the tool: kept
    assert safety.apply(weather, set())[1][0]["type"] == "uncited_dose"    # no weather data: still replaced
    assert safety.apply(dose, {"tool:get_weather"})[1][0]["type"] == "uncited_dose"
