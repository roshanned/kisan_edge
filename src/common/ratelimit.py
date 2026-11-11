"""Request and input-token pacing for the Gemini API free tier, shared by the cloud client and the judge.

Free-tier limits are per model and per minute, on both requests (RPM) and input tokens (TPM; 16,000 for Gemma 4).
RAG prompts are several thousand tokens, so pacing on requests alone runs into 429 storms. Pacer.wait(tokens)
blocks until sending `tokens` more keeps the last 60 seconds within both budgets. Thread-safe.
"""
import re
import threading
import time
from collections import deque

CHARS_PER_TOKEN = 3.8  # measured 4.0-4.1 on Gemma for judge prompts and Hindi text; 3.8 keeps a small margin


def estimate_tokens(text):
    return int(len(text) / CHARS_PER_TOKEN) + 50


def retry_after(message, default):
    """Seconds the API asks us to wait ('Please retry in 3.39s'), else the default."""
    m = re.search(r"retry in ([0-9.]+)s", str(message))
    return float(m.group(1)) + 1.0 if m else default


class Pacer:
    def __init__(self, rpm, tpm=None):
        self.rpm, self.tpm = float(rpm), float(tpm) if tpm else None
        self.sent = deque()  # (time, tokens)
        self.lock = threading.Lock()

    def wait(self, tokens=0):
        if self.tpm:
            tokens = min(tokens, self.tpm)  # a single huge prompt must still go out eventually
        while True:
            with self.lock:
                now = time.time()
                while self.sent and now - self.sent[0][0] >= 60:
                    self.sent.popleft()
                used = sum(t for _, t in self.sent)
                if len(self.sent) < self.rpm and (not self.tpm or used + tokens <= self.tpm):
                    self.sent.append((now, tokens))
                    return
                sleep = 60 - (now - self.sent[0][0]) + 0.05 if self.sent else 1.0
            time.sleep(max(0.2, min(sleep, 5.0)))
