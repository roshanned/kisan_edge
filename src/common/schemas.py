"""Field lists for the shared JSONL formats (PLAN.md section 5) plus one checker, so every writer can validate.

ponytail: plain field tuples, no dataclasses. If formats start to drift, move to pydantic.
"""
CATEGORIES = ("general", "live_data", "high_risk", "emergency")
SPLITS = ("train", "dev", "calib", "test")

REQUIRED = {
    "questions": ("id", "split", "lang", "script", "crop", "query_type", "category", "question", "reference_answer"),
    "edge": ("id", "model", "answer", "mean_logprob", "min_logprob", "n_tokens", "latency_ms"),
    "cloud": ("id", "run", "answer", "citations", "tool_calls", "as_of", "provider"),
    "router": ("id", "route", "gate_score", "kept_offline", "final_answer", "answered_by", "queued_at", "delivered_at"),
    "scores": ("id", "run", "label", "judge", "human_checked"),
}


def check(kind, row):
    """Raises ValueError naming the first missing field; returns the row so it can be chained."""
    missing = [f for f in REQUIRED[kind] if f not in row]
    if missing:
        raise ValueError(f"{kind} record {row.get('id')!r} is missing {missing}")
    if "category" in row and row["category"] not in CATEGORIES:
        raise ValueError(f"bad category {row['category']!r} in {row.get('id')!r}")
    return row
