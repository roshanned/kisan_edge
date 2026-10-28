import hashlib
import json
import os
import sqlite3
from pathlib import Path

from google import genai
from google.genai import types


class GeminiClient:
    """Caches every response so the same request is never sent twice."""

    def __init__(self, model="gemini-2.5-flash", cache_path="cache/gemini.sqlite"):
        self.model = model
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(cache_path)
        self.db.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, response TEXT)")

    def generate(self, prompt, system=None, temperature=0.0):
        key = hashlib.sha256(json.dumps([self.model, system, prompt, temperature]).encode()).hexdigest()
        row = self.db.execute("SELECT response FROM cache WHERE key = ?", (key,)).fetchone()
        if row:
            return row[0]
        resp = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system, temperature=temperature),
        )
        self.db.execute("INSERT INTO cache VALUES (?, ?)", (key, resp.text))
        self.db.commit()
        return resp.text
