"""Builds corpus/recall_queries.jsonl for the Recall@5 check (PLAN.md Sai step 2.6 / Phase 2 RAG metrics).

Samples documents from the index (fixed seed, half Hindi, half English) and asks gemini-3.5-flash-lite to write one
farmer question per document, answerable from the excerpt shown: Hindi in Devanagari for --n-deva documents and
Hinglish for --n-latn others. The source document is the relevant one ({"query", "doc_ids", "script"}). Synthetic
queries are easier than real ones (they reuse the document's words), so read Recall@5 as an upper bound.

Usage: python -m src.cloud.rag.make_recall_queries [--n-deva 40 --n-latn 20]
"""
import argparse
import json
import random
import re

from src.cloud.rag.store import Store

MODEL = "gemini-3.5-flash-lite"
ASK = """Below are {n} numbered excerpts from Indian agriculture documents. For EACH excerpt write one short question
that a farmer in Uttar Pradesh might ask and that the excerpt answers. Write the questions in {lang}. Do not copy
long phrases from the excerpt and do not name the document.
Reply with a JSON list of {n} strings, in the same order.

{excerpts}"""
LANG = {"deva": "Hindi, in Devanagari script", "latn": "Hinglish (Hindi written in Latin letters, as typed on a phone)"}


def main():
    from src.cloud.llm.gemini_client import GeminiClient
    from src.eval.judge import load_env
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-deva", type=int, default=40)
    ap.add_argument("--n-latn", type=int, default=20)
    ap.add_argument("--index-dir", default="corpus/index")
    ap.add_argument("--out", default="corpus/recall_queries.jsonl")
    a = ap.parse_args()
    load_env()
    store, llm = Store(a.index_dir), GeminiClient(MODEL)
    docs = sorted(store.active_doc_ids())
    rng = random.Random(0)
    hi = [d for d in docs if store.get_doc(d)["lang"] == "hi"]
    en = [d for d in docs if store.get_doc(d)["lang"] != "hi"]
    total = a.n_deva + a.n_latn
    picked = rng.sample(hi, total // 2) + rng.sample(en, total - total // 2)
    rng.shuffle(picked)
    out = []
    for script, ids in (("deva", picked[:a.n_deva]), ("latn", picked[a.n_deva:])):
        for i in range(0, len(ids), 10):
            batch = ids[i:i + 10]
            excerpts = "\n\n".join(f"[{j + 1}] {store.get_chunk(f'{d}#0')['text'][:900]}" for j, d in enumerate(batch))
            text = llm.generate(ASK.format(n=len(batch), lang=LANG[script], excerpts=excerpts))
            qs = json.loads(re.search(r"\[.*\]", text, re.S).group(0))
            out += [{"query": q.strip(), "doc_ids": [d], "script": script, "generated_by": MODEL}
                    for q, d in zip(qs, batch) if isinstance(q, str) and q.strip()]
    with open(a.out, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(out)} queries to {a.out}")


if __name__ == "__main__":
    main()
