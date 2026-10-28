"""LLM judge: labels one answer as correct / partly_correct / wrong against the KCC reference answer.

Backends:
  gemini  Gemini REST API. Key from env GEMINI_API_KEY (or .env), model from GEMINI_MODEL.
          Every response is cached on disk, so a question is never sent twice.
  mock    word-overlap heuristic. Only for testing the pipeline offline; its labels are NOT results.
"""
import hashlib
import json
import os
import re
import time
from pathlib import Path

import requests

LABELS = ["correct", "partly_correct", "wrong"]
CACHE = Path("outputs/cache/judge_cache.jsonl")
DEFAULT_MODEL = "gemini-2.5-flash"

PROMPT = """You are grading an answer to an Indian farmer's agricultural question.
The reference answer comes from a Kisan Call Centre (KCC) expert. The question and answers may be in
Hindi (Devanagari), Hinglish (romanised Hindi) or English; judge the meaning, not the script or wording.

Question category: {category}
Question: {question}
Reference answer (expert): {reference}
Answer to grade: {answer}

Labels:
- correct: gives the same advice or facts as the reference (extra harmless detail is fine).
- partly_correct: right direction but incomplete, vague, or mixes correct and incorrect points.
- wrong: contradicts the reference, answers a different question, invents facts, is empty or gibberish.
{live_note}
Also set "deferred" to true if the answer mostly declines to answer or says it will answer later /
asks the farmer to contact an officer, KVK or helpline instead of giving the information.

Reply with JSON only: {{"label": "correct|partly_correct|wrong", "deferred": true|false, "reason": "<one short sentence>"}}"""

LIVE_NOTE = ("NOTE: this is a live-data question (weather / market price / scheme). The reference is a snapshot "
             "from the past, so do NOT penalise different numbers or dates; judge whether the answer gives the "
             "kind of information that was asked, or points to the right source.\n")


def load_env(path=".env"):
    p = Path(path)
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def build_prompt(q, answer):
    return PROMPT.format(category=q.get("category"), question=q["question"], reference=q["reference_answer"],
                         answer=answer or "(empty)", live_note=LIVE_NOTE if q.get("category") == "live_data" else "")


def _tokens(t):
    return set(re.findall(r"[\wऀ-ॿ]+", str(t).lower()))


def mock_judge(q, answer):
    a, r = _tokens(answer), _tokens(q["reference_answer"])
    f1 = 2 * len(a & r) / (len(a) + len(r)) if a and r else 0.0
    return {"label": "correct" if f1 >= 0.5 else "partly_correct" if f1 >= 0.2 else "wrong",
            "deferred": False, "reason": f"mock word-overlap F1={f1:.2f}"}


class GeminiJudge:
    def __init__(self, model=None, rpm=None):
        load_env()
        self.key = os.environ.get("GEMINI_API_KEY", "")
        if not self.key:
            raise SystemExit("GEMINI_API_KEY is empty. Put it in .env (GEMINI_API_KEY=...) or use --judge mock.")
        self.model = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
        self.gap = 60.0 / float(rpm or os.environ.get("GEMINI_RPM", 10))
        self.last = 0.0
        self.cache = {}
        if CACHE.exists():
            for line in CACHE.open(encoding="utf-8"):
                row = json.loads(line)
                self.cache[row["key"]] = row["result"]

    def _call(self, prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
        for attempt in range(6):
            wait = self.gap - (time.time() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.time()
            resp = requests.post(url, json=body, headers={"x-goog-api-key": self.key}, timeout=60)
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(min(2 ** attempt * 5, 120))
                continue
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        raise RuntimeError("Gemini kept failing (429/5xx); try again later or lower GEMINI_RPM")

    def __call__(self, q, answer):
        prompt = build_prompt(q, answer)
        key = hashlib.sha256(f"{self.model}\n{prompt}".encode()).hexdigest()
        if key not in self.cache:
            result = parse(self._call(prompt))
            self.cache[key] = result
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            with CACHE.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"key": key, "model": self.model, "result": result}, ensure_ascii=False) + "\n")
        return self.cache[key]


def parse(text):
    m = re.search(r"\{.*\}", text, re.S)
    data = json.loads(m.group(0)) if m else {}
    label = str(data.get("label", "")).strip().lower().replace(" ", "_")
    if label not in LABELS:
        raise ValueError(f"judge returned an unusable label: {text[:200]!r}")
    return {"label": label, "deferred": bool(data.get("deferred", False)), "reason": str(data.get("reason", ""))[:300]}


def get_judge(name):
    return {"gemini": GeminiJudge, "mock": lambda: mock_judge}[name]()
