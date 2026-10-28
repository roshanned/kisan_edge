"""Fake output files in the shared formats so the eval pipeline can be tested before real runs exist.
Answers are the reference with words randomly dropped, so a mock judge gives a spread of labels.

Usage: python -m src.eval.make_mock_outputs     -> outputs/mock_edge.jsonl, outputs/mock_cloud.jsonl
"""
import random

from src.data.common import read_jsonl, write_jsonl


def degrade(text, keep, rng):
    words = text.split()
    return " ".join(w for w in words if rng.random() < keep) or "pata nahi"


def main():
    rng = random.Random(5)
    gold = read_jsonl("data/processed/gold.jsonl")
    write_jsonl([{"id": q["id"], "model": "mock-edge", "answer": degrade(q["reference_answer"], 0.4, rng),
                  "mean_logprob": -rng.random(), "min_logprob": -4 * rng.random(), "n_tokens": 50, "latency_ms": 800}
                 for q in gold], "outputs/mock_edge.jsonl")
    write_jsonl([{"id": q["id"], "run": "B1", "answer": degrade(q["reference_answer"], 0.8, rng), "citations": [],
                  "tool_calls": [], "as_of": "2026-10-28", "provider": "mock"} for q in gold], "outputs/mock_cloud.jsonl")
    print("wrote outputs/mock_edge.jsonl, outputs/mock_cloud.jsonl")


if __name__ == "__main__":
    main()
