# Cloud side: developer guide (Sai's layer)

Built on top of Sai's RAG skeleton (`src/cloud/rag/*`, `rag_ingest.py`, `llm/gemini_client.py`). **Nothing here has run against the
live Gemini API or the BGE-M3 index yet**: there is no API key in the repo, no corpus, and the heavy packages (faiss,
sentence-transformers, google-genai) are not installed on this machine. Everything else is tested with fakes (`pytest tests/test_cloud.py`, 8 tests).
Human tasks are in [MANUAL_TODO.md](MANUAL_TODO.md).

## Flow
```
question ─> retrieve top-5 chunks (BGE-M3 + FAISS) ─> Gemini with tools ─> tool loop (max 4 steps) ─> safety filter ─> answer + citations + tool_calls
```

| File | What it does |
|---|---|
| `src/cloud/agent.py` | The loop. RAG sources go in the prompt; Gemini may call tools; the answer is filtered. Runs: **B1** RAG+tools, **A2** no RAG, **A3** no tools, **B4** neither |
| `src/cloud/tools.py` | `get_weather(district, days)`, `get_mandi_price(crop, mandi)`, `lookup_scheme(scheme)`. Read frozen snapshots only. Errors are strings `ERROR <code>: ...` |
| `src/cloud/safety.py` | Per sentence: banned pesticide -> refusal; dose with no retrieved-source or tool citation -> deferral to KCC 1551 |
| `src/cloud/banned_pesticides.txt` | **Draft** banned list (10 long-banned products). Verify before the final report |
| `src/cloud/llm/gemini_client.py` | Cache every response (SQLite), throttle to `GEMINI_RPM`, retry on 429/5xx, function calling |
| `src/cloud/query.py` | CLI and batch runner. Resumes if interrupted. Writes `outputs/cloud_<run>.jsonl` |
| `src/cloud/fetch_snapshots.py` | `places` (geocode districts), `weather` (7-day forecast), `mandi` (needs `DATA_GOV_API_KEY`) |
| `src/cloud/rag/recall_check.py` | Recall@5 on `corpus/recall_queries.jsonl` |
| `data/snapshots/` | `places.json` (76 districts), `weather/` (76 forecasts dated 2026-10-30), `schemes.json` (5 schemes, **unverified**), `mandi_<date>.json` (**missing**) |

## Run order
```bash
pip install -r requirements.txt
cp .env.example .env            # put GEMINI_API_KEY (and DATA_GOV_API_KEY for prices) in .env
python -m src.cloud.fetch_snapshots mandi                        # once, needs the data.gov.in key
python -m src.cloud.rag_ingest --docs corpus/docs.jsonl          # builds the index from your corpus
python -m src.cloud.rag.recall_check                             # Recall@5
python -m src.cloud.query --questions data/processed/questions.jsonl --gold --run B1 --limit 20   # debug on 20 first
python -m src.cloud.query --questions data/processed/questions.jsonl --gold --run B1              # resumes after a quota stop
python -m src.cloud.query ... --run A2   # and A3, B4
```
Use `--as-of 2026-10-30` (the snapshot date) for every run so tool results are identical across B1/A2/A3.

## Decisions
- **B4 = plain cloud LLM, no RAG, no tools.** PLAN.md left it undefined; this is its own suggestion. Change `RUNS` in `query.py` to redefine.
- **Retrieval is not a tool.** The top-5 chunks (score >= 0.4) are always put in the prompt. Simpler, and one fewer model call per question.
- **Tools read snapshots, never the live API,** so every run sees the same weather and prices. Weather is dated 2026-10-30; the gold questions' references are old KCC answers, and the judge is told not to penalise different numbers for live-data questions.
- **Mandi tool uses crop + mandi name, not mandi IDs.** Crops are the four project crops (wheat, paddy, mustard, sugarcane). A model passing Hindi gets `ERROR invalid_argument: crop 'गेहूं' must be one of [...]` and retries.
- **A cited source must have been retrieved.** `[made_up_doc]` does not excuse a dose.
- **Safety filter is aggressive.** Any quantity not backed by a retrieved source is replaced by a deferral, even a correct one. Tool facts count as sources.
- **Districts use KCC spellings** (Bareilly, Kheri, Badaun, Faizabad...); 16 had no geocoder hit, so approximate district-HQ coordinates are hard-coded in `fetch_snapshots.py`. `Kanpur Dehat` was geocoded as Kanpur.
- **Not done:** fault injection (timeouts, empty results, 5xx) and the Phase 2 metrics (tool-choice accuracy, citation faithfulness, correct-abstain rate).
