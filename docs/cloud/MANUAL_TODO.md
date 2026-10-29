# What only a human can do (cloud layer)

| # | Task | Blocks | Time |
|---|---|---|---|
| 1 | **Put `GEMINI_API_KEY` in `.env`**, then run `python -m src.cloud.query "बरेली में कल का मौसम?" --run B1` once. This is the first real call of the Gemini function-calling code; if it errors, the fix is in `gemini_client._request` | everything | 10 min |
| 2 | **Collect the RAG corpus, 50-100 trusted docs** (UP Agri Dept, ICAR, CRIDA, CIB&RC, PM-KISAN, PMFBY, myScheme). Most government sites time out or return empty pages from scripts, so download PDFs by hand into `corpus/raw/`, list each in `corpus/docs.jsonl` (see `docs.example.jsonl`: doc_id, doc_key, path, source, date, lang, title). Hindi first | Retrieval, B1, A3 | half a day |
| 3 | Install the heavy packages (`pip install -r requirements.txt`; BGE-M3 is a ~2 GB download), run `rag_ingest`, then write ~30 Hindi queries in `corpus/recall_queries.jsonl` and run `recall_check` | Recall@5 | 1 h |
| 4 | **Get a free `DATA_GOV_API_KEY`** (data.gov.in > My Account) and run `fetch_snapshots mandi`. Until then the price tool returns `ERROR no_data` and B1 cannot answer price questions. Check the resource id in `fetch_snapshots.py` still works | Price tool | 20 min |
| 5 | **Verify `data/snapshots/schemes.json`** against official pages (PM-KISAN amount and helplines, PMFBY premium percentages, KCC terms, Soil Health Card). Every entry has `needs_verification: true`; flip it when checked | Scheme answers | 30 min |
| 6 | **Verify `src/cloud/banned_pesticides.txt`** against the current CIB&RC banned/restricted list | Safety | 20 min |
| 7 | **Run B1 and A2 on the 200 gold questions** (start now: free tier is about 3,800 calls over 3-15 days). Debug on `--limit 20` first. If quota runs out, switch the *whole* run to `--model gemini-2.5-flash-lite` after deleting the partial output | B1, A2, A1, R, hybrid | days |
| 8 | **Hand-check your 50 gold questions** (`data/processed/gold_batches/gold_batch_sai.csv`) | gold.jsonl | 1 h |
| 9 | **Confirm B4** = plain LLM, no RAG, no tools, or drop it from the compute plan | Plan gap | 5 min |
| 10 | Read 20 real answers for citations that do not support the claim, and for safety-filter replacements that hid a useful answer (`safety_events` field in each record) | Report | 30 min |
| 11 | Write the cloud section of the report | Report | 30 min |
