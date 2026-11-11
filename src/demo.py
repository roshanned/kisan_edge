"""Live demo of the whole Kisan-Edge pipeline on one question (for the Nov 16-19 presentation).

  router -> 4-bit edge model on this CPU (llama.cpp, with token logprobs) -> offline dose filter -> gate
         -> online: cloud agent (RAG + tools)   |   offline: interim answer now, question queued for later

  python -m src.demo "gehu me peela ratua ka ilaj batao" --district Kheri
  python -m src.demo "kal barish hogi kya" --district Bareilly --offline      # queued in outputs/demo_queue.jsonl
  python -m src.demo --flush                                                   # back online: answer the queue

Needs tools_ext/llamacpp/bin (llama.cpp Windows CPU build) and the GGUF from Kaggle job 08; the gate from
src.eval.run_final (models/gate/B3/); GEMINI_API_KEY for the cloud step. Generation here uses llama.cpp's
repeat penalty; the evaluated B3 runs used transformers on a GPU, so answers can differ slightly.
"""
import argparse
import json
import subprocess
import time
from pathlib import Path

import requests

from src.data.common import detect_script, find_crop
from src.edge.prompts import SYSTEM_PROMPT, prompt_kind
from src.router_gate import intent_clf, safety_filter
from src.router_gate.gate import Gate, gate_rows
from src.router_gate.hybrid import INTERIM
from src.router_gate.router import EMERGENCY_NUMBERS, Router

BIN = Path("tools_ext/llamacpp/bin")
GGUF = Path("kaggle/results/08_gguf/models/kisan-edge-3b-Q4_K_M.gguf")
PORT = 8089
QUEUE = Path("outputs/demo_queue.jsonl")
AS_OF = "2026-10-30"  # date of the frozen weather snapshots


def edge_server():
    """Start llama-server once (kept running between demo questions); returns its URL."""
    url = f"http://127.0.0.1:{PORT}"
    try:
        requests.get(f"{url}/health", timeout=1)
        return url
    except requests.RequestException:
        pass
    exe = BIN / ("llama-server.exe" if (BIN / "llama-server.exe").exists() else "llama-server")
    subprocess.Popen([str(exe), "-m", str(GGUF), "--port", str(PORT), "-t", "4", "-c", "2048"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(120):
        try:
            if requests.get(f"{url}/health", timeout=1).status_code == 200:
                return url
        except requests.RequestException:
            pass
        time.sleep(0.5)
    raise SystemExit("llama-server did not start; check tools_ext/llamacpp/bin and the GGUF path")


def edge_answer(row):
    url = edge_server()
    t = time.time()
    r = requests.post(f"{url}/v1/chat/completions", timeout=300, json={
        "messages": [{"role": "system", "content": SYSTEM_PROMPT[prompt_kind(row)]}, {"role": "user", "content": row["question"]}],
        "max_tokens": 200, "temperature": 0, "repeat_penalty": 1.1, "logprobs": True}).json()
    lps = [x["logprob"] for x in r["choices"][0]["logprobs"]["content"]]
    return {"id": "demo", "answer": r["choices"][0]["message"]["content"].strip(),
            "mean_logprob": sum(lps) / len(lps) if lps else None, "min_logprob": min(lps) if lps else None,
            "n_tokens": len(lps), "latency_ms": round((time.time() - t) * 1000)}


def cloud_answer(question, district):
    from src.cloud import agent
    from src.cloud.llm.gemini_client import GeminiClient
    from src.cloud.rag.retriever import Retriever
    from src.cloud.tools import Tools
    from src.eval.judge import load_env
    load_env()
    return agent.run(question, GeminiClient(), Retriever(), Tools(AS_OF), rewrite=True, district=district)


def step(name, text):
    print(f"\n[{name}] {text}")


def handle(question, district=None, offline=False):
    lang, script = detect_script(question)
    row = {"id": "demo", "question": question, "lang": lang, "script": script, "crop": find_crop(question), "district": district}
    ui = "hi" if lang == "hi" else "en"
    route = Router(intent_clf.load()).route(question)
    step("router", f"{route['category']}  ({route['reason']})   language: {lang}/{script}")
    if route["category"] == "emergency":
        step("EMERGENCY", INTERIM["emergency"][ui] + "  (shown at once, online or not)")
    e = edge_answer(row)
    step("edge model", f"{e['n_tokens']} tokens in {e['latency_ms']} ms on this CPU, mean logprob {e['mean_logprob']:.2f}\n  {e['answer']}")
    shown, blocked = safety_filter.apply(e["answer"], ui)
    step("dose filter", "BLOCKED: the edge answer contained a quantity" if blocked else "passed")
    send = route["category"] != "general" or blocked
    why = "route is not general" if route["category"] != "general" else "dose blocked" if blocked else "general route, no gate fitted yet"
    gp = Path("models/gate/B3/gate_classifier.pkl")
    if not send and gp.exists():
        g = Gate.load(gp)
        conf = float(g.conf(gate_rows([e], {"demo": {**row, "category": route["category"]}}))[0])
        send, why = conf < g.cut, f"gate confidence {conf:.2f} vs cut {g.cut:.2f}"
    step("decision", ("ask the cloud" if send else "keep the edge answer offline") + f"  ({why})")
    if not send:
        step("ANSWER (offline)", shown)
        return
    interim = INTERIM.get(route["category"], INTERIM["high_risk"])[ui] if route["category"] != "general" or blocked else shown
    if offline:
        QUEUE.parent.mkdir(exist_ok=True)
        with QUEUE.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"question": question, "district": district, "category": route["category"],
                                "queued_at": time.strftime("%Y-%m-%d %H:%M")}, ensure_ascii=False) + "\n")
        step("ANSWER now (offline)", interim)
        step("queue", f"queued in {QUEUE}; run --flush when back online (emergency first, then high-risk, live, general)")
        return
    t = time.time()
    c = cloud_answer(question, district)
    tools = ", ".join(f"{x['name']}({x['status']})" for x in c["tool_calls"]) or "none"
    step("cloud agent", f"{time.time() - t:.1f} s; sources: {[x['doc_id'] for x in c['citations']]}; tools: {tools}; "
                        f"safety events: {[x['type'] for x in c['safety_events']]}")
    step("ANSWER (cloud)", c["answer"])


def flush():
    from src.queue_sim.sim import PRIORITY
    if not QUEUE.exists():
        print("queue is empty")
        return
    jobs = sorted((json.loads(l) for l in QUEUE.open(encoding="utf-8")), key=lambda j: PRIORITY[j["category"]])
    for j in jobs:
        step("from queue", f"{j['question']}  (queued {j['queued_at']}, {j['category']})")
        step("ANSWER (cloud)", cloud_answer(j["question"], j["district"])["answer"])
    QUEUE.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="?")
    ap.add_argument("--district", default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--flush", action="store_true")
    a = ap.parse_args()
    if a.flush:
        flush()
    elif a.question:
        handle(a.question, a.district, a.offline)
    else:
        print(f"Emergency numbers: {EMERGENCY_NUMBERS}")
        while (q := input("\nquestion> ").strip()) not in ("", "exit"):
            handle(q, a.district, a.offline)


if __name__ == "__main__":
    main()
