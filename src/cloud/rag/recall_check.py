"""Recall@5 of the retriever on a hand-made query set (PLAN.md Sai step 2.6: ~30 Hindi queries).

corpus/recall_queries.jsonl, one per line: {"query": "...", "doc_ids": ["icar_wheat_2025"]}   (any listed doc counts as a hit)
Usage: python -m src.cloud.rag.recall_check [--k 5]
"""
import argparse
import json

from src.cloud.rag.retriever import Retriever


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", default="corpus/recall_queries.jsonl")
    ap.add_argument("--k", type=int, default=5)
    a = ap.parse_args()
    qs = [json.loads(line) for line in open(a.queries, encoding="utf-8") if line.strip()]
    r = Retriever()
    hits = sum(bool({c["doc_id"] for c in r.search(q["query"], a.k)} & set(q["doc_ids"])) for q in qs)
    print(f"Recall@{a.k} = {hits}/{len(qs)} = {hits / len(qs):.2f}")


if __name__ == "__main__":
    main()
