"""Recall@k of the retriever on a query set (PLAN.md Sai step 2.6; Phase 2 RAG metrics).

corpus/recall_queries.jsonl, one per line: {"query": "...", "doc_ids": ["icar_wheat_2025"], "script": "deva"}
(any listed doc counts as a hit). Built by src.cloud.rag.make_recall_queries.
--rewrite also measures retrieval with the agent's LLM-written search query (src.cloud.agent.search_query), which is
what B1 actually retrieves with; --model picks the LLM (use the B1 model).
Usage: python -m src.cloud.rag.recall_check [--k 5] [--rewrite --model gemma-4-26b-a4b-it] [--out outputs/final/rag_recall.json]
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from src.cloud.rag.retriever import Retriever


def recall(qs, retriever, k, query_of):
    by = defaultdict(lambda: [0, 0])
    for q in qs:
        hit = bool({c["doc_id"] for c in retriever.search(query_of(q), k)} & set(q["doc_ids"]))
        for key in ("all", q.get("script", "all")):
            by[key][0] += hit
            by[key][1] += 1
    return {key: {"recall": round(h / n, 3), "n": n} for key, (h, n) in by.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", default="corpus/recall_queries.jsonl")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--rewrite", action="store_true")
    ap.add_argument("--model", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    qs = [json.loads(line) for line in open(a.queries, encoding="utf-8") if line.strip()]
    r = Retriever()
    res = {"k": a.k, "raw_query": recall(qs, r, a.k, lambda q: q["query"])}
    if a.rewrite:
        from src.cloud import agent
        from src.cloud.llm.gemini_client import GeminiClient
        from src.eval.judge import load_env
        load_env()
        llm = GeminiClient(a.model)
        res["rewritten_query"] = recall(qs, r, a.k, lambda q: agent.search_query(q["query"], llm))
        res["rewrite_model"] = llm.model
    print(json.dumps(res, indent=1))
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
