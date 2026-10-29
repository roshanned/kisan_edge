"""Cloud agent: RAG sources in the prompt, then a function-calling loop over the tools, then the safety filter.

Runs (PLAN.md 4.2):  B1 = RAG + tools   A2 = tools, no RAG   A3 = RAG, no tools   B4 = plain LLM (no RAG, no tools; our definition).
The LLM object only needs  chat(messages, system, tool_specs) -> {"text": str, "tool_calls": [{"name","args"}]}.
Messages are plain dicts: {role:user,text} | {role:model,text,tool_calls} | {role:tool,results:[{name,result}]}.
"""
import json
import re

from src.cloud import safety
from src.cloud.tools import Tools

MAX_STEPS = 4
BASE = """You are an agricultural advisor for farmers in Uttar Pradesh, India (crops: wheat, paddy, mustard, sugarcane).
Reply in the same language and script as the question, briefly and simply.
If you are not sure, say you do not know and suggest calling the Kisan Call Centre at 1551.
Never give pesticide or fertilizer quantities unless a source or tool result gives them. Never recommend banned pesticides."""
RAG_RULES = """Answer only from the numbered sources given. Cite every fact with its source id in square brackets, e.g. [icar_wheat_2025]."""
TOOL_RULES = """For weather, market prices or government schemes call the matching tool; never guess such facts.
Cite tool facts as [tool:<tool_name>] and say the 'as_of' date. If a tool returns an ERROR, fix the argument and retry once, or say the information is unavailable."""


def system_prompt(use_rag, use_tools):
    return "\n".join([BASE] + ([RAG_RULES] if use_rag else []) + ([TOOL_RULES] if use_tools else []))


def source_block(chunks):
    return "\n\n".join(f"[{c['doc_id']}] {c['title']} ({c['source']}, {c['date']})\n{c['text']}" for c in chunks)


def run(question, llm, retriever=None, tools=None, k=5, min_score=0.4, max_steps=MAX_STEPS):
    """Returns the PLAN.md section 5 cloud fields (answer, citations, tool_calls) plus 'safety_events' and 'steps'."""
    chunks = [c for c in retriever.search(question, k) if c["score"] >= min_score] if retriever else []
    prompt = (f"Sources:\n{source_block(chunks) or '(no relevant sources found)'}\n\n" if retriever else "") + f"Question: {question}"
    msgs, calls, text = [{"role": "user", "text": prompt}], [], ""
    system = system_prompt(retriever is not None, tools is not None)
    steps = 0
    for steps in range(1, max_steps + 1):
        r = llm.chat(msgs, system, tools.specs() if tools else [])
        text = r["text"] or text
        if not r["tool_calls"] or not tools:
            break
        results = []
        for c in r["tool_calls"]:
            res, status = tools.call(c["name"], c["args"])
            calls.append({"name": c["name"], "args": c["args"], "status": status})
            results.append({"name": c["name"], "result": res})
        msgs += [{"role": "model", "text": r["text"], "tool_calls": r["tool_calls"]}, {"role": "tool", "results": results}]
    else:
        text = text or "जानकारी नहीं मिल सकी। कृपया KCC 1551 पर कॉल करें। / Could not complete; please call KCC 1551."
    allowed = {c["doc_id"] for c in chunks} | {f"tool:{c['name']}" for c in calls if c["status"] == "ok"}
    text, events = safety.apply(text, allowed)
    cited = set(re.findall(r"\[([^\[\]]+)\]", text))
    dates = {c["doc_id"]: c["date"] for c in chunks if c["doc_id"] in cited}
    cites = [{"doc_id": d, "date": dt} for d, dt in dates.items()]
    as_of = tools.as_of if tools else None
    cites += [{"doc_id": f"tool:{c['name']}", "date": as_of} for c in calls if c["status"] == "ok" and f"tool:{c['name']}" in cited]
    return {"answer": text, "citations": cites, "tool_calls": calls, "safety_events": events, "steps": steps}
