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


# Many farmer questions are romanized Hindi ("dhan me jhonka rog"), which the embedder matches poorly against
# Hindi/English documents, so retrieval uses an LLM-written search query instead of the raw question.
REWRITE = """Rewrite the farmer's question as a search query for an index of Indian agriculture documents.
Write one line: the query in Hindi (Devanagari script), then ' / ', then the same query in English.
Name the crop and the specific pest, disease, variety, fertilizer, scheme or practice asked about. Do not answer the question."""


def search_query(question, llm):
    """Hindi + English search query for retrieval; falls back to the question if the model returns nothing."""
    return (llm.chat([{"role": "user", "text": question}], REWRITE, [])["text"] or "").strip() or question


def system_prompt(use_rag, use_tools):
    return "\n".join([BASE] + ([RAG_RULES] if use_rag else []) + ([TOOL_RULES] if use_tools else []))


MAX_SOURCE_CHARS = 30000  # about 8k tokens; a few badly split documents give 10-46k-character chunks (DECISIONS.md D28)


def source_block(chunks):
    """Numbered sources for the prompt. Only when they total more than MAX_SOURCE_CHARS is each chunk cut to an equal
    share, so the request fits the free tier's 16k input tokens a minute; no B1 test question below the cap changes."""
    total = sum(len(c["text"]) for c in chunks)
    share = MAX_SOURCE_CHARS // max(1, len(chunks)) if total > MAX_SOURCE_CHARS else None
    return "\n\n".join(f"[{c['doc_id']}] {c['title']} ({c['source']}, {c['date']})\n{c['text'][:share] if share else c['text']}"
                       for c in chunks)


def run(question, llm, retriever=None, tools=None, k=5, min_score=0.4, max_steps=MAX_STEPS, rewrite=False, district=None):
    """Returns the PLAN.md section 5 cloud fields (answer, citations, tool_calls) plus 'safety_events', 'steps'
    and 'search_query'. rewrite=True retrieves with search_query() (one extra LLM call) instead of the raw question.
    district: the farmer's district if known (the phone app knows it; KCC records have it), given as context so
    weather and price questions without a place name use the right district instead of a guess."""
    query = search_query(question, llm) if retriever and rewrite else question
    chunks = [c for c in retriever.search(query, k) if c["score"] >= min_score] if retriever else []
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
    return {"answer": text, "citations": cites, "tool_calls": calls, "safety_events": events, "steps": steps,
            "search_query": query if retriever else None}
