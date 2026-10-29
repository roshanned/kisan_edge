# Project status (Oct 30, 2026, mid-submission day)

All code lives on `main`. 50 tests pass. **No model has produced answers yet**, so there are no accuracy numbers. That is the main gap for the mid-submission.

## What is done

| Part | Done |
|---|---|
| **Data (Anushka)** | Data cleaned and split once (700 test, 600 calib, 600 dev, 16,435 train). 200 gold candidates in 4 batches of 50. Judge, scoring script, per-language report, judge-vs-human check. Report draft in `reports/mid/` |
| **Edge model (Roshan)** | Hinglish and English data, Hindi translations, 100-question model pilot, generation and QLoRA scripts |
| **Cloud (Sai's part, finished by Claude)** | Agent loop with function calling, 3 tools (weather, mandi price, schemes), safety filter, Gemini client with cache and retries, resumable batch runner for B1/A2/A3/B4, weather forecasts for 76 UP districts (dated 2026-10-30). Guide: `docs/cloud/` |
| **Router and queue (Kiran's part, finished by Claude)** | Router, offline dose filter, gate metrics, queue simulator, hybrid runner (full, R, A1, A4), 51 red-team questions. Guide: `docs/kiran/` |

Real numbers so far: router 80% accurate on test and sends 90% of high-risk questions to the cloud; queue delivers 100% / 99.8% / 67% on good / patchy / poor links.

## What is NOT done and why
- **Cloud code has never called Gemini.** No API key in the repo. Only tested with fakes.
- **No RAG corpus.** Government sites could not be scraped; documents must be downloaded by hand.
- **No mandi prices.** Needs a free data.gov.in key.
- **Scheme facts and banned-pesticide list are from memory.** Marked unverified.
- **Nobody has hand-checked any gold question** (0 of 200).
- Red-team questions, keyword lists and the router and queue settings are Claude's drafts and need a human read.

## To do for the mid-submission, in order

**Now (30 min, one person each, all in parallel)**
1. **Anushka:** send the train split to Roshan. Put `GEMINI_API_KEY` in `.env`. Hand-check your 50 gold questions.
2. **Sai:** put the Gemini key in `.env`; run `python -m src.cloud.query ... --run B1 --limit 20` (debug first). Then start B1 on the gold set; quota makes it slow. Start A2 after.
3. **Roshan:** run B2 (base model) on the gold set; start QLoRA on the train split; then B3.
4. **Kiran / anyone:** read the 51 red-team questions and keyword lists (Hindi).
5. **Everyone else:** hand-check your 50 gold questions and send them to Anushka.

**Then**
6. Anushka merges the gold sheets (`merge_gold`) and scores every output file (B1, B2, B3, A1, A2, R).
7. Run the gate, R, A1 commands in `docs/kiran/README.md` as soon as B1, B2, B3 exist.
8. Hand-label ~50 judge outputs and run `judge_check agree`.
9. Fill the TODO blocks in `reports/mid/report.typ` (drafts: `reports/mid/kiran_section.md`; each person writes their own).
10. Tag `mid-submission` and submit.

**Fallback if B1, B3 or the corpus are not ready today:** submit with what exists (data, split, judge, router, queue, edge pilot, cloud code), say clearly which runs are pending and why, and finish them before the Nov 12 scoring deadline.

**Decisions the team must make**
- H1 may be unreachable: live-data and high-risk questions always go to the cloud (66-85% of gold). Accept and report honestly, or narrow high-risk (`docs/kiran/DECISIONS.md`).
- Confirm B4 = plain LLM, no RAG, no tools (`docs/cloud/README.md`).
- Confirm Claude's choices marked CONFIRM in `docs/kiran/DECISIONS.md` (queue numbers are invented).

## After Oct 30 (final, Nov 15)
Full 700-question runs of everything; RAG corpus of 200-400 docs; Recall@5, citation and tool metrics, fault injection (Sai); 4-bit model export and phone-speed test, QLoRA re-runs (Roshan); full gate classifier and queue metrics, H1 verdict (Kiran); BhashaBench loaders and judge agreement on 100 questions, final report (Anushka). Code freeze Nov 14.

More detail: `docs/kiran/` (router and queue), `docs/cloud/` (cloud), each with a `MANUAL_TODO.md`.
