# Data and evaluation: choices and facts (Anushka)

What was built, why, and what to watch out for. How to run it: [dev.md](dev.md). Status: [checklist.md](checklist.md).
Plan: [PLAN.md](PLAN.md). Written Oct 28, 2026.

## 1. Where the data comes from

The main dataset is **Roshan's cleaned KCC data**, not a fresh KCC UP 2024-25 download (decision: Oct 28, saves time and
those files are already cleaned with the shared rules). Roshan's files are on the public HF dataset
`kisan-edge/kisan-edge-data`; `python -m src.data.fetch_inputs` pulls `processed/*` into `data/raw/hf/`.

| Input | Rows | Used as |
|---|---|---|
| `kcc_hinglish.jsonl` | 9,432 | `hi/latn` (Hinglish questions), used as is |
| `kcc_1m_other.jsonl`, expert answer in Devanagari | 20,883 | `hi/deva`: **question = IndicTrans2 Hindi translation** of the English summary |
| `kcc_1m_other.jsonl`, expert answer in English | 5,662 | `en/latn` |
| `kcc_1m_other.jsonl`, English question + Hinglish answer | 7,000 | **dropped** (rewards replying in the wrong language; same call Roshan made for training) |
| `kisanvaani_en.jsonl` | 2,328 | only the 11 rows on our 4 crops (`in_scope`) |
| `pilot_ids.txt` | 100 | forced into dev |

### Things you must know (limitations to state in the report)

1. **"Hindi" test questions are machine-translated.** Only 11 of 33,556 KCC rows have a natively Devanagari question; the
   rest are English operator summaries translated by IndicTrans2. Records carry `question_translated: true` and
   `question_en` (original summary). The expert *answers* are native Hindi. So H2 ("Hindi test set") measures
   translated-question Hindi. Hinglish (`hi/latn`) questions are genuine farmer typing.
2. **Data is 2012-2017 (Hinglish) and 2019-2023 (other), not 2024-25** as in the proposal.
3. **English is thin and narrow.** KisanVaani adds only 11 usable rows; English comes mostly from KCC rows whose answer is
   English. Many are price lookups ("Farmer asked price detail of Mustard in X mandi").
4. **KCC labels and answers are noisy** (typos, weather questions tagged "Plant Protection", terse answers like
   "spray Kashu-B @2 ml/lit"). This is why the gold set is hand-checked.
5. **Live-data references are stale snapshots** (old weather, old mandi prices). The judge is told not to penalise
   different numbers on `live_data` questions.

## 2. Cleaning and labelling rules (shared)

Implemented in Roshan's `src/data/common.py` (reused as is; merged into this branch) and applied before my split:

- Keep only wheat, paddy, mustard, sugarcane; Uttar Pradesh rows only.
- Phone numbers replaced with `[PHONE]`; HTML-entity Hindi decoded; corrupted ("????") and too-short rows dropped; duplicates dropped.
- Script tag: `hi/deva` (Devanagari), `hi/latn` (Hinglish), `en/latn`.
- Category: `general | live_data | high_risk | emergency`, recomputed from QueryType plus keyword overrides (QueryType is noisy).
  Kiran's router labels are the final ones; mine are first-pass. KCC has essentially no real emergencies, so any
  keyword-flagged "emergency" is folded into `high_risk` until Kiran's red-team set covers emergencies.
- My additional rule: **one record per distinct question text per language bucket** (normalised: lower-case, spaces, trailing `?.!` removed).
  This removes things like 5,215 copies of "Farmer asked query on Weather".

## 3. The split (frozen)

Script: `src/data/build_questions.py`. Seeded (2026), deterministic, and it refuses to run again once `questions.jsonl` exists.
`split_manifest.json` stores a SHA-256 of the test ids; `tests/test_split.py` re-checks it.

| Split | hi/deva | hi/latn | en/latn | Total |
|---|---|---|---|---|
| test | 300 | 250 | 150 | **700** |
| calib | 250 | 200 | 150 | 600 |
| dev | 300 | 200 | 100 | 600 |
| train | 8,424 | 5,871 | 2,140 | 16,435 |

- Sizes follow PLAN.md (~700 test; ~2,000 across test + calib + dev). Language mix in test/calib/dev is deliberately balanced so
  every language gets a usable number of questions; train is whatever is left, so it is Hindi/Hinglish heavy.
- Within each language and split: **40% general, 40% high_risk, 20% live_data** (live_data answers are date-specific, so capped;
  high_risk is kept large for the safety metrics). Test has 280/280/140. Crops follow the natural mix (test: wheat 271, paddy 244, sugarcane 101, mustard 84).
- **Leak control:** a question text (or the English source text of a translated Hindi question) lives in exactly one split.
  The same question text appears in multiple rows in KCC, so a random row split would leak. 150 train rows were dropped for sharing a text with test/calib/dev.
- **Roshan's 100 pilot questions are all in dev** (99 distinct; one is a punctuation-only twin of another pilot question).
- Sampling happened before Roshan retrains: his current adapter used his own files, so it must be retrained on `split == "train"`.

## 4. Gold set

200 questions from the **test** split, 70 `hi/deva` + 70 `hi/latn` + 60 `en/latn`, stratified 40/40/20 by category.
Sorted by (language, category) then dealt round-robin into four batches of 50, so each person gets the same mix
(`gold_batch` = anushka | kiran | roshan | sai). Sheets: `data/processed/gold_batches/gold_batch_<name>.csv`.

- Reviewers answer: is the question clear, is the reference answer right, are lang/script tags and category right; fix or drop.
- `src.eval.merge_gold` builds `gold.jsonl`: drops rejected rows, applies fixes, sets `human_checked`. **Right now `gold.jsonl` = the 200 candidates, unchecked**,
  so Roshan/Sai/Kiran can run B1/B2/B3 immediately; the ids do not change, only dropped ones disappear. Re-merge after the sheets return.
- Hindi reading: PLAN.md allows swapping batches if a reviewer is not comfortable with Hindi. Each batch has ~35 Hindi/Hinglish rows and ~15 English.

## 5. Evaluation harness

- **Judge** (`src/eval/judge.py`): Gemini via REST (default `gemini-2.5-flash`, override with `GEMINI_MODEL`), temperature 0, JSON output,
  labels `correct | partly_correct | wrong` plus `deferred` (did the answer decline / say "contact KVK/call later"). Every response is cached
  on disk (`outputs/cache/`, gitignored), rate-limited (`GEMINI_RPM`, default 10) and retried on 429/5xx. A `mock` backend (word overlap) exists
  only to test the pipeline; its output is stamped `judge: mock` and the report/judge-check refuse to treat it as a result.
- **One judge for every run**, so runs are comparable (never mix judges within an experiment).
- **Scoring** (`src.eval.score`): joins an output file to the gold set (or test/dev/calib) by `id`, reads `answer` or `final_answer`,
  counts missing answers explicitly, writes `outputs/scores_<RUN>.jsonl` in the shared format plus lang/script/category/crop/deferred.
- **Trust check** (`src.eval.judge_check`): sample N scored rows stratified by language, you relabel them blind (the judge label is the last column), then
  exact agreement, wrong-vs-not-wrong agreement and Cohen's kappa are reported overall and per language. Mid: ~50 rows; final: 100 (PLAN).
- **Report** (`src.eval.report`): per run and per language/script (and per category): % correct with 95% Wilson interval, lenient (correct + partly),
  % deferred, plus a bar chart. Strict accuracy = share labelled `correct`.

## 6. Decisions still open / assumptions I made

| # | Item | Status |
|---|---|---|
| 1 | Crop-recommendation "exact match" metric (PLAN section 9.3) | **Dropped** (no dataset exists). State it in the report as a change to the proposal. |
| 2 | Judge model name | `gemini-2.5-flash` is my default; confirm which model your key can use. |
| 3 | `live_data` scoring policy | Judge ignores stale numbers and gives credit for pointing to the right source. A pure deferral is tracked in `deferred`, not forced into a label. Say if you want deferrals labelled differently. |
| 4 | Test mix is language-balanced, not natural | Intentional; it changes absolute accuracy vs a random sample of KCC. State in report. |
| 5 | KCC 2024-25 | Not used. |

## 7. Not done by me (owned by others)

Router labels / red-team set (Kiran), edge outputs B2/B3 (Roshan), cloud outputs B1/A2 (Sai). Scoring waits on their files in `outputs/`.
