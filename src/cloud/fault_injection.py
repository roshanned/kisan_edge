"""Tool fault injection (PLAN.md section 4, Sai step 4.7) -> outputs/final/fault_injection.json (+ .jsonl per answer).

Takes test questions that ask for weather (the one tool with full snapshots) and runs the A2 agent (tools, no RAG) with
a tool wrapper that fails on purpose:
  timeout   the tool "did not answer in 10 s"           -> ERROR timeout
  empty     the tool returns an empty result            -> {} (no error, no data)
  5xx       the weather service is down                 -> ERROR 503
each either transient (first call fails, a retry works) or persistent (every call fails).
Metrics per condition:
  recovery rate        transient: a retry got real data (a later call returned ok) AND the answer uses it
  invented-data rate   no ok tool result, but the answer still states weather numbers (mm, degrees, %)
  graceful rate        no ok tool result and the answer says the data is unavailable / points to a source
Usage: python -m src.cloud.fault_injection --n 20 --model gemma-4-26b-a4b-it
"""
import argparse
import json
import random
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.cloud import agent
from src.cloud.metrics import WANTS
from src.cloud.tools import Tools
from src.data.common import read_jsonl

FAULTS = {"timeout": "ERROR timeout: get_weather did not answer within 10 s.",
          "empty": {},
          "5xx": "ERROR 503: weather service unavailable, try again."}
NUMBERS = re.compile(r"\d+(?:\.\d+)?\s*(?:mm|°|डिग्री|degree|%|प्रतिशत|मिमी|मि\.मी)", re.I)
UNAVAILABLE = re.compile(r"unavailable|not available|could not|couldn't|unable|उपलब्ध नहीं|नहीं मिल|नहीं हो|"
                         r"try again|बाद में|1551|imd|मौसम विभाग|nahi mil|uplabdh nahi", re.I)


class FaultyTools(Tools):
    def __init__(self, as_of, fault, persistent):
        super().__init__(as_of)
        self.fault, self.persistent, self.n = fault, persistent, 0

    def call(self, name, args):
        self.n += 1
        if name == "get_weather" and (self.persistent or self.n == 1):
            res = FAULTS[self.fault]
            return res, "error" if isinstance(res, str) else "ok_empty"
        return super().call(name, args)


def classify(res):
    ok = any(c["status"] == "ok" for c in res["tool_calls"])
    nums = bool(NUMBERS.search(res["answer"]))
    return {"got_data": ok, "states_numbers": nums, "says_unavailable": bool(UNAVAILABLE.search(res["answer"])),
            "calls": len(res["tool_calls"])}


def main():
    from src.cloud.llm.gemini_client import GeminiClient
    from src.eval.judge import load_env
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--model", default=None)
    ap.add_argument("--as-of", default="2026-10-30")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    load_env()
    llm = GeminiClient(a.model)
    qs = [q for q in read_jsonl("data/processed/questions.jsonl")
          if q["split"] == "test" and re.search(WANTS["get_weather"], q["question"].lower())]
    qs = random.Random(0).sample(qs, min(a.n, len(qs)))
    conds = [(f, p) for f in FAULTS for p in (False, True)]

    def one(job):
        q, (fault, persistent) = job
        res = agent.run(q["question"], llm, None, FaultyTools(a.as_of, fault, persistent), district=q.get("district"))
        return {"id": q["id"], "fault": fault, "persistent": persistent, "answer": res["answer"],
                "tool_calls": res["tool_calls"], **classify(res)}

    with ThreadPoolExecutor(a.workers) as ex:
        rows = list(ex.map(one, [(q, c) for c in conds for q in qs]))
    out = {"n_questions": len(qs), "model": llm.model, "conditions": {}}
    for fault, persistent in conds:
        sub = [r for r in rows if r["fault"] == fault and r["persistent"] == persistent]
        no_data = [r for r in sub if not r["got_data"]]
        key = f"{fault}_{'persistent' if persistent else 'transient'}"
        out["conditions"][key] = {
            "n": len(sub),
            "recovery_rate": round(sum(r["got_data"] for r in sub) / len(sub), 3),
            "invented_data_rate": round(sum(r["states_numbers"] for r in no_data) / len(no_data), 3) if no_data else 0.0,
            "graceful_rate": round(sum(r["says_unavailable"] for r in no_data) / len(no_data), 3) if no_data else None,
            "mean_tool_calls": round(sum(r["calls"] for r in sub) / len(sub), 2),
            "tool_status": dict(Counter(c["status"] for r in sub for c in r["tool_calls"]))}
    Path("outputs/final").mkdir(parents=True, exist_ok=True)
    with open("outputs/final/fault_injection.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    Path("outputs/final/fault_injection.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
