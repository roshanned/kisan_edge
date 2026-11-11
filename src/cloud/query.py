"""Ask the cloud agent (RAG + tools + safety filter). See docs/cloud/README.md.

Usage:
  python -m src.cloud.query "गेहूं में पीला रतुआ का इलाज?"                    # one question
  python -m src.cloud.query                                                  # interactive
  python -m src.cloud.query --questions data/processed/questions.jsonl --gold --run B1 --limit 20   # debug on 20 first
  python -m src.cloud.query --questions data/processed/questions.jsonl --gold --run B1               # resumes if interrupted
Runs: B1 = RAG + tools, A2 = no RAG, A3 = no tools, B4 = neither.  Output: outputs/cloud_<run>.jsonl (PLAN.md section 5).
To change model (e.g. flash-lite when the quota is gone), switch the WHOLE run: delete the output file and rerun with --model.
"""
import argparse
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from src.cloud import agent
from src.cloud.tools import Tools

RUNS = {"B1": (True, True), "A2": (False, True), "A3": (True, False), "B4": (False, False)}  # (use_rag, use_tools)


def load_questions(path, split=None, gold=False):
    rows = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    if gold:  # questions.jsonl has gold=False everywhere until merge; gold.jsonl is the source of truth
        ids = {json.loads(line)["id"] for line in open("data/processed/gold.jsonl", encoding="utf-8")}
        rows = [r for r in rows if r["id"] in ids]
    return [r for r in rows if not split or r["split"] == split]


def run_batch(rows, ask, run, out, provider, as_of, limit=0, workers=1):
    """Appends one record per question; skips ids already in the file, so a quota stop is resumable.
    workers > 1 asks several questions at once (the LLM client is thread-safe); file order then follows completion."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(line)["id"] for line in open(out, encoding="utf-8")} if out.exists() else set()
    todo = [r for r in rows if r["id"] not in done][: limit or None]
    stop, lock, n = threading.Event(), threading.Lock(), [0]

    def one(r, f):
        if stop.is_set():
            return
        try:
            res = ask(r["question"], r.get("district"))
        except Exception as e:  # quota or network: stop cleanly, rerun later to resume
            print(f"STOP at {r['id']}: {str(e)[:300]}", flush=True)
            stop.set()
            return
        rec = {"id": r["id"], "run": run, "answer": res["answer"], "citations": res["citations"],
               "tool_calls": res["tool_calls"], "as_of": as_of, "provider": provider, "safety_events": res["safety_events"]}
        if res.get("search_query"):
            rec["search_query"] = res["search_query"]
        with lock:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            n[0] += 1
            print(f"{n[0]}/{len(todo)} {r['id']}", flush=True)

    with open(out, "a", encoding="utf-8") as f, ThreadPoolExecutor(max(1, workers)) as ex:
        list(ex.map(lambda r: one(r, f), todo))
    print(f"{len(done)} already done, {n[0]} of {len(todo)} answered -> {out}")
    return int(stop.is_set())


def main():
    from src.eval.judge import load_env
    load_env()
    p = argparse.ArgumentParser()
    p.add_argument("question", nargs="?")
    p.add_argument("--questions")
    p.add_argument("--split")
    p.add_argument("--gold", action="store_true")
    p.add_argument("--run", default="B1", choices=RUNS)
    p.add_argument("--out")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--index-dir", default="corpus/index")
    p.add_argument("--model")
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--workers", type=int, default=1, help="questions asked in parallel (keep RPM in .env in mind)")
    p.add_argument("--no-rewrite", action="store_true", help="retrieve with the raw question, not an LLM-written search query")
    p.add_argument("--as-of", default=date.today().isoformat(), help="snapshot date for tools; keep it fixed for the whole evaluation")
    p.add_argument("--live", action="store_true", help="(reserved) live tool data; evaluation must use snapshots")
    args = p.parse_args()

    from src.cloud.llm.gemini_client import GeminiClient
    llm = GeminiClient(args.model)
    use_rag, use_tools = RUNS[args.run]
    retriever = None
    if use_rag:
        from src.cloud.rag.retriever import Retriever
        retriever = Retriever(args.index_dir)
    tools = Tools(args.as_of) if use_tools else None

    def ask(q, district=None):
        return agent.run(q, llm, retriever, tools, args.k, rewrite=not args.no_rewrite, district=district)

    if args.questions:
        run_batch(load_questions(args.questions, args.split, args.gold), ask, args.run,
                  args.out or f"outputs/cloud_{args.run}.jsonl", llm.model, args.as_of, args.limit, args.workers)
    elif args.question:
        print(json.dumps(ask(args.question), ensure_ascii=False, indent=2))
    else:
        while (q := input("> ").strip()) not in ("", "exit"):
            res = ask(q)
            print(res["answer"], "\n", res["citations"], res["tool_calls"], "\n")


if __name__ == "__main__":
    main()
