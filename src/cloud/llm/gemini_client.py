import base64
import hashlib
import json
import os
import sqlite3
import threading
import time
from pathlib import Path

from src.common.ratelimit import Pacer, estimate_tokens, retry_after


class GeminiClient:
    """Caches every response so the same request is never sent twice; throttles to GEMINI_RPM; retries 429/5xx.

    chat() supports function calling. Thread-safe, so a batch can run several questions at once (query.py --workers):
    the cache and the request spacing are shared under locks. Gemma models return their reasoning as parts marked
    `thought`; those are dropped. GEMINI_THINKING (minimal | low | medium | high) sets the thinking level.
    GEMINI_TPM caps input tokens per minute (free-tier Gemma: 16,000), see src/common/ratelimit.py.
    """

    def __init__(self, model=None, cache_path="cache/gemini.sqlite", thinking=None):
        from google import genai  # imported here so tests and the offline pipeline need no google-genai
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        # GEMINI_THINKING applies to Gemma models only, so cached Gemini calls (red-team, recall queries) still match.
        self.thinking = thinking or (os.environ.get("GEMINI_THINKING") if self.model.startswith("gemma") else None) or None
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.pacer = Pacer(os.environ.get("GEMINI_RPM", "10"), os.environ.get("GEMINI_TPM"))
        self.calls = 0  # real (non-cached) requests this session
        self.lock = threading.Lock()
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(cache_path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, response TEXT)")

    def generate(self, prompt, system=None, temperature=0.0):
        return self.chat([{"role": "user", "text": prompt}], system, [], temperature)["text"]

    def chat(self, messages, system=None, tool_specs=(), temperature=0.0):
        # The thinking level joins the key only when set, so older cache entries (none set) still match.
        parts = [self.model, system, messages, [t["name"] for t in tool_specs], temperature] + ([self.thinking] if self.thinking else [])
        key = hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        with self.lock:
            row = self.db.execute("SELECT response FROM cache WHERE key = ?", (key,)).fetchone()
        if row:
            return json.loads(row[0])
        out = self._request(messages, system, tool_specs, temperature)
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO cache VALUES (?, ?)", (key, json.dumps(out, ensure_ascii=False)))
            self.db.commit()
        return out

    def _request(self, messages, system, tool_specs, temperature):
        from google.genai import types
        cfg = types.GenerateContentConfig(
            system_instruction=system, temperature=temperature,
            tools=[types.Tool(function_declarations=[types.FunctionDeclaration(
                name=t["name"], description=t["description"], parameters=_schema(t["parameters"])) for t in tool_specs])] if tool_specs else None,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            thinking_config=types.ThinkingConfig(thinking_level=self.thinking) if self.thinking else None)
        contents = []
        for m in messages:
            if m["role"] == "user":
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=m["text"])]))
            elif m["role"] == "model":
                parts = ([types.Part.from_text(text=m["text"])] if m.get("text") else []) + \
                        [_call_part(types, c) for c in m["tool_calls"]]
                contents.append(types.Content(role="model", parts=parts))
            else:
                contents.append(types.Content(role="user", parts=[
                    types.Part.from_function_response(name=r["name"], response={"result": r["result"]}) for r in m["results"]]))
        tokens = estimate_tokens((system or "") + json.dumps(messages, ensure_ascii=False) + json.dumps(list(tool_specs)))
        for attempt in range(10):
            self.pacer.wait(tokens)
            self.calls += 1
            try:
                resp = self.client.models.generate_content(model=self.model, contents=contents, config=cfg)
                parts = resp.candidates[0].content.parts or []
                parts = [p for p in parts if not getattr(p, "thought", False)]
                return {"text": "".join(p.text for p in parts if getattr(p, "text", None)),
                        "tool_calls": [_call_dict(p) for p in parts if getattr(p, "function_call", None)]}
            except Exception as e:  # quota (429) and server errors: back off, then give up so the batch can resume later
                if attempt == 9 or not any(c in str(e) for c in ("429", "500", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "INTERNAL")):
                    raise
                if "PerDay" in str(e):  # daily quota: no point retrying today; the batch stops and resumes later
                    raise
                time.sleep(retry_after(e, 10 * 2 ** min(attempt, 3)))


def _call_dict(p):
    """Gemini 3 models reject a follow-up request unless each function call keeps its thought_signature."""
    c = {"name": p.function_call.name, "args": dict(p.function_call.args or {})}
    if getattr(p, "thought_signature", None):
        c["thought_signature"] = base64.b64encode(p.thought_signature).decode()  # JSON-safe for the cache
    return c


def _call_part(types, c):
    part = types.Part.from_function_call(name=c["name"], args=c["args"])
    if c.get("thought_signature"):
        part.thought_signature = base64.b64decode(c["thought_signature"])
    return part


def _schema(s):
    """JSON schema -> the subset Gemini accepts, with upper-case type names."""
    out = {"type": s["type"].upper()}
    for k in ("description", "enum", "required"):
        if k in s:
            out[k] = s[k]
    if "properties" in s:
        out["properties"] = {n: _schema(v) for n, v in s["properties"].items()}
    return out
