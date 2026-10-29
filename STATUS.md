# Project status (Oct 30, 2026)

All four branches are merged into `main`. 42 tests pass. **No model results exist yet** (B1, B2, B3, A1, A2, R have no outputs), so the mid-submission has no accuracy numbers.

## Done

**Anushka (data and scoring)**
- Data cleaned and split once: 700 test, 600 calib, 600 dev, 16,435 train. Test is frozen; pilot questions are in dev.
- 50-question seed file; 200 gold candidates in 4 batches of 50.
- LLM judge, scoring script, per-language report with confidence intervals, judge-vs-human check script.
- Mid-report draft (`reports/mid/report.typ`) with TODO blocks.

**Roshan (edge model)**
- Hinglish and English data cleaned; English questions translated to Hindi.
- 100-question model pilot, generation script, QLoRA training script, Kaggle jobs.

**Sai (cloud)**
- RAG pipeline skeleton (chunking, dedup, embeddings, retriever) and Gemini client. Only 2 example corpus rows.

**Kiran's layer (built by Claude)**
- Router (keywords + classifier), offline dose filter, gate metrics, queue and link simulator, hybrid runner (full, R, A1, A4), 51 red-team questions. Guides in `docs/kiran/`.
- Router: 80% accuracy and 90% high-risk recall on test. Queue delivers 100% / 99.8% / 67% on good / patchy / poor links.

## Left

**Blocks everything else**
1. Send the train split to Roshan so he can train. Then Roshan runs B2 and B3 on gold with logprobs.
2. Sai: real corpus, index, agent loop, then B1 and A2 on gold (Gemini quota is slow).
3. Put `GEMINI_API_KEY` in `.env`, smoke-test the judge on 20 rows.

**Human checking (nobody has done any; `gold.jsonl` has 0 of 200 checked)**
4. Everyone hand-checks their 50 gold questions; merge with `merge_gold`.
5. Hand-label ~50 judge outputs and run `judge_check agree`.
6. Read Claude's 51 red-team questions and keyword lists (Hindi). Write ~20 independent red-team questions.

**Then**
7. Score all runs, make tables and plots, fill the report TODOs.
8. Run gate, R, A1, A4 once outputs exist (commands in `docs/kiran/README.md`). Gives AUROC, H1, H3.
9. Tag `mid-submission` and submit.

**Open decisions**
- H1 may be unreachable: live-data and high-risk questions always go to the cloud, which is 66-85% of gold. Pick: accept and report honestly, or narrow high-risk (`docs/kiran/DECISIONS.md`).
- Confirm the Claude-made choices (D2, D4, D9). Queue numbers are invented.
- Define B4 or drop it (Sai). Crop-recommendation metric is already dropped.

**Phase 2 (Nov 15):** full 700-question runs, BhashaBench loaders, judge agreement on 100 questions, full gate classifier, final report.

Not done by anyone: Sai's tools (weather, mandi, schemes), cloud safety filter, Roshan's GGUF and phone-size tests.
