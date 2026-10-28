"""Ingest docs listed in a manifest into the RAG store and rebuild the FAISS index.

Usage: python -m src.cloud.rag_ingest --docs corpus/docs.jsonl [--as-of 2026-10-26]
"""
import argparse
import json
from pathlib import Path

import faiss
import numpy as np
from datasketch import MinHashLSH

from src.cloud.rag.chunker import chunk_text
from src.cloud.rag.dedup import NUM_PERM, content_hash, minhash
from src.cloud.rag.embed import DIM, embed
from src.cloud.rag.loaders import load_text
from src.cloud.rag.store import Store


def ingest(records, store, base_dir, threshold):
    report = {"added": [], "already_ingested": [], "empty": [], "exact_dup": [], "near_dup": []}
    lsh = MinHashLSH(threshold=threshold, num_perm=NUM_PERM)
    for d in store.all_docs():
        lsh.insert(d["doc_id"], minhash(d["text"]))

    for r in sorted(records, key=lambda r: r["date"]):
        if store.get_doc(r["doc_id"]):
            report["already_ingested"].append(r["doc_id"])
            continue
        text = load_text(base_dir / r["path"])
        if not text:
            report["empty"].append(r["doc_id"])
            continue
        h = content_hash(text)
        if dup := store.find_by_hash(h):
            report["exact_dup"].append(f"{r['doc_id']} == {dup}")
            continue
        m = minhash(text)
        # Versions of the same doc_key are expected to be near-duplicates, so skip this check for them.
        if not r.get("doc_key") and (near := lsh.query(m)):
            report["near_dup"].append(f"{r['doc_id']} ~ {', '.join(near)}")
            continue
        store.add_doc({**r, "hash": h, "text": text}, chunk_text(text))
        lsh.insert(r["doc_id"], m)
        report["added"].append(r["doc_id"])
    return report


def build_index(store, as_of=None):
    chunks = store.active_chunks(as_of)
    vecs = store.get_embeddings([c["hash"] for c in chunks])
    todo = {c["hash"]: c["text"] for c in chunks if c["hash"] not in vecs}
    if todo:
        new = embed(list(todo.values()))
        store.save_embeddings(list(todo), new)
        vecs.update(zip(todo, new))

    index = faiss.IndexFlatIP(DIM)
    if chunks:
        index.add(np.stack([vecs[c["hash"]] for c in chunks]))
    store.save_index(index, [c["chunk_id"] for c in chunks])
    return len(chunks)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--docs", default="corpus/docs.jsonl")
    p.add_argument("--index-dir", default="corpus/index")
    p.add_argument("--as-of", help="only use docs dated on or before this date (YYYY-MM-DD)")
    p.add_argument("--near-dup-threshold", type=float, default=0.85)
    args = p.parse_args()

    docs_path = Path(args.docs)
    records = [json.loads(line) for line in docs_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    store = Store(args.index_dir)

    report = ingest(records, store, docs_path.parent, args.near_dup_threshold)
    n_chunks = build_index(store, args.as_of)

    active = set(store.active_doc_ids(args.as_of))
    report["superseded"] = [
        d["doc_id"] for d in store.all_docs()
        if d["doc_id"] not in active and (not args.as_of or d["date"] <= args.as_of)
    ]
    for key, ids in report.items():
        print(f"{key}: {len(ids)}")
        for i in ids:
            print(f"  {i}")
    print(f"index: {len(active)} active docs, {n_chunks} chunks")


if __name__ == "__main__":
    main()
