import json

import pytest

from src.cloud import agent, safety, tools as T
from src.cloud.query import run_batch


@pytest.fixture
def snap(tmp_path, monkeypatch):
    monkeypatch.setattr(T, "SNAP", tmp_path)
    (tmp_path / "weather").mkdir()
    (tmp_path / "places.json").write_text(json.dumps({"Bareilly": {"lat": 28.3, "lon": 79.4}}))
    d = {"time": ["2026-10-30", "2026-10-31"], "temperature_2m_max": [31, 30], "temperature_2m_min": [17, 16],
         "precipitation_sum": [0, 2.5], "precipitation_probability_max": [5, 60]}
    (tmp_path / "weather" / "Bareilly_2026-10-30.json").write_text(json.dumps({"daily": d}))
    (tmp_path / "mandi_2026-10-30.json").write_text(json.dumps([
        {"state": "Uttar Pradesh", "district": "Bareilly", "market": "Bareilly", "commodity": "Wheat", "arrival_date": "29/10/2026",
         "min_price": 2300, "max_price": 2500, "modal_price": 2400}]))
    (tmp_path / "schemes.json").write_text(json.dumps({"pm_kisan": {"aliases": ["pm kisan"], "summary": "Rs 6,000 a year"}}))
    return T.Tools(as_of="2026-10-30")


def test_weather_ok_and_alias_and_errors(snap):
    r, st = snap.call("get_weather", {"district": "bareilly", "days": 2})
    assert st == "ok" and r["as_of"] == "2026-10-30" and len(r["forecast"]) == 2
    r, st = snap.call("get_weather", {"district": "बरेली"})
    assert st == "error" and r.startswith("ERROR invalid_argument: district 'बरेली'")
    assert snap.call("get_weather", {"district": "Bareilly", "days": 9})[0].startswith("ERROR invalid_argument: days")
    assert snap.call("get_weather", {})[0].startswith("ERROR invalid_argument")  # missing argument


def test_snapshot_after_as_of_is_not_used(snap):
    assert T.Tools(as_of="2026-10-01").call("get_weather", {"district": "Bareilly"})[0].startswith("ERROR no_data")


def test_mandi_and_scheme(snap):
    r, _ = snap.call("get_mandi_price", {"crop": "wheat", "mandi": "Bareilly"})
    assert r["modal"] == 2400 and r["unit"] == "Rs per quintal"
    assert snap.call("get_mandi_price", {"crop": "गेहूं", "mandi": "Bareilly"})[0].startswith("ERROR invalid_argument: crop")
    assert snap.call("get_mandi_price", {"crop": "paddy", "mandi": "Bareilly"})[0].startswith("ERROR no_data")
    assert snap.call("lookup_scheme", {"scheme": "PM-KISAN"})[0]["scheme"] == "pm_kisan"
    assert snap.call("lookup_scheme", {"scheme": "xyz"})[0].startswith("ERROR no_data")
    assert snap.call("nope", {})[0].startswith("ERROR unknown_tool")


class FakeLLM:
    def __init__(self, replies):
        self.replies, self.seen = list(replies), []

    def chat(self, messages, system, tool_specs):
        self.seen.append((len(messages), [t["name"] for t in tool_specs]))
        return self.replies.pop(0)


class FakeRetriever:
    def search(self, q, k):
        return [{"doc_id": "icar_wheat_2025", "title": "Wheat", "source": "ICAR", "date": "2025-03-01", "text": "x", "score": 0.9}]


def test_agent_calls_tool_then_answers_with_citations(snap):
    llm = FakeLLM([{"text": "", "tool_calls": [{"name": "get_weather", "args": {"district": "Bareilly"}}]},
                   {"text": "कल बारिश की संभावना 60% है [tool:get_weather]", "tool_calls": []}])
    out = agent.run("Bareilly weather?", llm, None, snap)
    assert out["tool_calls"] == [{"name": "get_weather", "args": {"district": "Bareilly"}, "status": "ok"}]
    assert out["citations"] == [{"doc_id": "tool:get_weather", "date": "2026-10-30"}] and out["steps"] == 2


def test_agent_without_tools_never_offers_tools_and_without_rag_has_no_sources():
    llm = FakeLLM([{"text": "ठीक है", "tool_calls": []}])
    out = agent.run("q", llm, FakeRetriever(), None)
    assert llm.seen == [(1, [])] and out["tool_calls"] == []


def test_agent_stops_after_max_steps(snap):
    call = {"text": "", "tool_calls": [{"name": "get_weather", "args": {"district": "Bareilly"}}]}
    out = agent.run("q", FakeLLM([call] * 10), None, snap, max_steps=3)
    assert out["steps"] == 3 and "1551" in out["answer"]


def test_safety_uncited_dose_banned_and_cited_dose():
    allowed = {"icar_wheat_2025"}
    t, ev = safety.apply("Spray 2 ml per litre. Use endosulfan on the crop. Spray 3 ml per litre [icar_wheat_2025]. Irrigate after 21 days.", allowed)
    assert "2 ml" not in t and "endosulfan" not in t.lower() and "3 ml per litre [icar_wheat_2025]" in t and "21 days" in t
    assert [e["type"] for e in ev] == ["uncited_dose", "banned"]
    assert safety.apply("Spray 3 ml per litre [made_up_doc].", allowed)[1][0]["type"] == "uncited_dose"  # citing a doc we did not retrieve does not count


def test_batch_resumes_and_stops_on_error(tmp_path):
    rows = [{"id": f"q{i}", "question": "x"} for i in range(5)]
    n = {"c": 0}

    def ask(q):
        n["c"] += 1
        if n["c"] == 3:
            raise RuntimeError("429 quota")
        return {"answer": "a", "citations": [], "tool_calls": [], "safety_events": []}
    out = tmp_path / "o.jsonl"
    assert run_batch(rows, ask, "B1", out, "m", "2026-10-30") == 1
    assert len(out.read_text().splitlines()) == 2
    assert run_batch(rows, ask, "B1", out, "m", "2026-10-30") == 0
    assert [json.loads(l)["id"] for l in out.read_text().splitlines()] == [f"q{i}" for i in range(5)]
