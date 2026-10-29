"""Ask the cloud LLM, grounded on the RAG index.

Usage:
  python -m src.cloud.query "गेहूं में पीला रतुआ का इलाज?"                 # one question
  python -m src.cloud.query                                               # interactive
  python -m src.cloud.query --questions data/processed/questions.jsonl --split test --gold --run B1
  python -m src.cloud.query --questions ... --run A2 --no-rag
"""
import argparse
import json
import re
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from src.cloud.llm.gemini_client import GeminiClient
from src.cloud.rag.retriever import Retriever

RAG_SYSTEM = """You are an agricultural advisor for farmers in Uttar Pradesh, India.
Answer only from the sources given. Cite every fact with its source id in square brackets, e.g. [icar_wheat_2025].
If the sources do not contain the answer, say you do not know and suggest calling the Kisan Call Centre at 1551.
Never give pesticide or fertilizer doses that are not in the sources.
Reply in the same language and script as the question, briefly and simply."""

NO_RAG_SYSTEM = """You are an agricultural advisor for farmers in Uttar Pradesh, India.
If you are not sure, say you do not know and suggest calling the Kisan Call Centre at 1551.
Reply in the same language and script as the question, briefly and simply."""


def build_prompt(question, chunks):
    sources = "\n\n".join(
        f"[{c['doc_id']}] {c['title']} ({c['source']}, {c['date']})\n{c['text']}" for c in chunks
    )
    return f"Sources:\n{sources or '(no relevant sources found)'}\n\nQuestion: {question}"


def answer(question, llm, retriever=None, k=5, min_score=0.4):
    if retriever is None:
        return {"answer": llm.generate(question, system=NO_RAG_SYSTEM), "citations": []}

    chunks = [c for c in retriever.search(question, k) if c["score"] >= min_score]
    text = llm.generate(build_prompt(question, chunks), system=RAG_SYSTEM)
    cited = set(re.findall(r"\[([^\[\]]+)\]", text))
    dates = {c["doc_id"]: c["date"] for c in chunks if c["doc_id"] in cited}
    return {"answer": text, "citations": [{"doc_id": d, "date": dt} for d, dt in dates.items()]}


def run_batch(args, ask):
    rows = [json.loads(line) for line in open(args.questions, encoding="utf-8") if line.strip()]
    rows = [r for r in rows if (not args.split or r["split"] == args.split) and (not args.gold or r.get("gold"))]
    out = Path(args.out or f"outputs/cloud_{args.run}.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for i, r in enumerate(rows, 1):
            rec = {"id": r["id"], "run": args.run, **ask(r["question"]),
                   "tool_calls": [], "as_of": args.as_of, "provider": args.model}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{i}/{len(rows)} {r['id']}")


def main():
    load_dotenv()
    p = argparse.ArgumentParser()
    p.add_argument("question", nargs="?")
    p.add_argument("--questions", help="questions.jsonl for a batch run")
    p.add_argument("--split")
    p.add_argument("--gold", action="store_true")
    p.add_argument("--run", default="B1")
    p.add_argument("--out")
    p.add_argument("--no-rag", action="store_true")
    p.add_argument("--index-dir", default="corpus/index")
    p.add_argument("--model", default="gemini-2.5-flash")
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--as-of", default=date.today().isoformat())
    args = p.parse_args()

    llm = GeminiClient(args.model)
    retriever = None if args.no_rag else Retriever(args.index_dir)

    def ask(q):
        return answer(q, llm, retriever, args.k)

    if args.questions:
        run_batch(args, ask)
    elif args.question:
        print(json.dumps(ask(args.question), ensure_ascii=False, indent=2))
    else:
        while (q := input("> ").strip()) not in ("", "exit"):
            res = ask(q)
            print(res["answer"], "\n", res["citations"], "\n")


if __name__ == "__main__":
    main()
