# CLAUDE.md: Anushka's work (Data and evaluation)

Source of truth: [PLAN.md](PLAN.md). This file lists only Anushka Sharma's tasks, what is already done elsewhere, and what is still undecided. **Do not invent answers to the open questions below; ask Anushka.**

Branch for this work: `anushka/data` (does not exist yet; only `main` and `origin/roshan/edge` exist as of Oct 28, 2026).
Code goes in `src/data/` (cleaning, split) and `src/eval/` (judge, scoring, tables, plots). Outputs go in `data/processed/` and `outputs/`.

## Deadlines (today is Oct 28)

| Item | Due | Status |
|---|---|---|
| Cleaning rules + 50-Q seed file to everyone | Oct 24 | Overdue |
| Frozen splits + gold batches of 50 sent out | Oct 26 | Overdue |
| Hand-checked gold batches back from everyone | Oct 27 | Overdue |
| All outputs in for scoring | Oct 29 | |
| **Mid-submission** (report + GitHub with all code) | **Oct 30** | |
| Final outputs for scoring | Nov 12 | |
| Final submission, no extensions | Nov 15 | |

## Phase 1 (mid-submission)

### Step 1: Data
1. Write the cleaning rules and labelling rules; share with everyone. (4 crops only; remove names and phones; dedupe; tag script `deva` / `latn` Hinglish / `latn` English; tag category `general | live_data | high_risk | emergency`.)
2. Download and clean KCC UP 2024-25 (main Hindi dataset) -> `data/processed/kcc_hi.jsonl`.
3. Publish a 50-question seed file in the shared format (PLAN.md section 5).
4. Write the split script (`train / dev / calib / test`). Run it **once** over my file plus Roshan's files. Freeze the test set.
5. Pick ~200 gold candidates from the test split; send 50 to each person.
6. Hand-check my own 50; merge everyone's into `data/processed/gold.jsonl`.
7. Send the frozen train split to Roshan.

### Step 2: Evaluation harness (`src/eval/`)
8. Scoring script: correct / partly correct / wrong, using an LLM judge. Output `outputs/scores_*.jsonl` (`{"id","run","label","judge","human_checked"}`).
9. Hand-check a sample of judge labels to see if it can be trusted.
10. Report results per language and script (Hindi deva, Hinglish, English).

### Step 3: Results and report
11. Score every output file: B1, B2, B3, R, A1, A2.
12. Tables and plots.
13. Assemble and submit the mid-submission report (outline in PLAN.md 3.1; everyone writes their own section, I edit).

## Phase 2 (final, Oct 31 - Nov 15)
1. Grow test to full ~700 Qs, plus calib and dev (~2,000 total), with the **same frozen split**.
2. Evaluation loaders for BhashaBench-Krishi Hindi (2,757 Qs) and the Indic-KCC-Agri-Advisory benchmark.
3. Judge vs human agreement on 100 Qs; report it.
4. Score every run; tables per language and script.
5. Overall metrics: accuracy, cloud calls per 100 Qs, offline usefulness.
6. Write and submit the final report.

## Other items assigned to me
- Gaps in the proposal (PLAN.md section 9): decide crop-recommendation data / "exact match" metric (define a dataset or drop it; was due Oct 27), and document the judging method (LLM judge + human-checked sample + agreement).
- Risk: noisy KCC labels -> human-checked gold subset, report results by slice.
- Definition of done (PLAN.md section 10): runs from a clean clone, JSONL outputs in `outputs/`, per-language results, every number traceable to a script, no API keys or personal data committed.

## Overlap with other people (checked against branches)

Only `origin/roshan/edge` exists (4 commits, last: "README: HF dataset is public"). No branches for Kiran or Sai.

| Overlap | What Roshan already did | What is left for me |
|---|---|---|
| Cleaning rules (Step 1.1) | `src/data/common.py` already implements them: 4-crop filter, phone -> `[PHONE]`, dedupe, script detection, first-pass category, record format. | Write/share the official rules doc; decide whether to adopt his `common.py` as the shared one. |
| Hinglish + English files | Done: `kcc_hinglish.jsonl` (9,432), `kisanvaani_en.jsonl` (2,328), `kcc_1m_other.jsonl` (33,556, English summaries + IndicTrans2 `question_hi`). On public HF dataset `kisan-edge/kisan-edge-data` (not in git). | Pull and feed into the split. Note KisanVaani has only 11 rows on our 4 crops. |
| Hindi translations | Done (33,545), stored in `kcc_1m_other.jsonl` as `question_hi`, **not** merged into `kcc_hi.jsonl` as PLAN.md says. | Decide how they enter the split. |
| Pilot set | `pilot_ids.txt` (100 IDs): **must go into dev, never test.** | Enforce in split script. |
| Category labels | His are first-pass only; Kiran's router labels are final. | Split must not depend on them being final (see questions). |
| Gold hand-check | Pending on my split. | Blocked on me. |
| Train split | He is waiting to retrain QLoRA on it. | Blocked on me. |
| Not done by anyone | KCC UP 2024-25, split script, seed file, judge, scoring, report. | All mine. |

## Open questions (ask before executing)
1. **KCC UP 2024-25:** PLAN.md says data.gov.in. Roshan's 1M-row file is the 2014-19 sample from HF. Do I have the 2024-25 file, or do I still need to download it (data.gov.in needs an API key / manual download)? If unavailable, is it OK to use what Roshan already cleaned as the main data? ---  USE ROSHANS DATA
2. **`kcc_hi.jsonl`:** should it contain only the original Devanagari 2024-25 rows, or also Roshan's translated `question_hi` rows?
3. **Split sizes:** only "~700 test, ~2,000 total for test+calib+dev" is stated. What are the dev, calib and train sizes/ratios? Is the split random, or stratified by language/crop/category?
4. **Gold set (~200):** random from test, or stratified (e.g. equal across Hindi / Hinglish / English, include some high_risk)? Note English data is thin (only 11 KisanVaani rows on our crops).
5. **LLM judge:** which model? Gemini free-tier quota is already Sai's bottleneck; should the judge use a different provider (and key)?
6. **Crop-recommendation / exact match metric:** define a dataset or drop it? (My call per PLAN.md; no source exists.)
7. **Overdue dates:** the seed file, split and gold batches were due Oct 24-27. Given the Oct 30 deadline, should I take the shortcut of splitting immediately over Roshan's existing files plus whatever Hindi data I have, and skip waiting for the others' hand-checks?
8. **Branch:** create `anushka/data` and work there, per PLAN.md git rules?
