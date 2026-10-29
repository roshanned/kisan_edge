# CLAUDE.md: Kiran's work (Router, gate, queue, integration)

Source of truth: [PLAN.md](PLAN.md) (§3 Kiran, §4 Kiran, §5 formats). This branch (`kiran/gate`, cut from `anushka/data` on Oct 29) exists because Kiran has pushed nothing. Anushka is covering the parts that need no Kiran-only input. Anything needing a human decision is marked **[ASK]**.

Code goes in `src/router_gate/` (router, intent clf, gate, output filter), `src/queue_sim/` (queue, cache, simulator), `src/common/` (schemas, mocks). Data goes in `data/processed/` and `src/router_gate/keywords/`. Outputs go in `outputs/`.

## Deadlines (mid-submission is Oct 30; final Nov 15, no extensions)

Kiran's items are all late: red-team set (due Oct 27), router labels, keyword lists. R / A1 / hybrid need B1, B2 and B3, which do not exist yet.

## What already exists (do not redo)

- `data/processed/questions.jsonl`: frozen split (test 700, calib 600, dev 600, train 16,435). Has `query_type` and a first-pass `category` (`general | live_data | high_risk` only; **no `emergency` rows exist**).
- `src/data/common.py`: `category_for(query_type, question)`, `detect_script`, `read_jsonl` / `write_jsonl`. Reuse these.
- `src/eval/make_mock_outputs.py`: fake edge and cloud outputs with logprobs, for building the gate before B2/B3 arrive.
- Output formats: PLAN.md §5 (`router.jsonl`, `hybrid_*.jsonl`, `edge_*.jsonl`, `cloud_*.jsonl`).

## Phase 1 tasks (mid-submission)

### Step 1: repo and data
1. `src/common/`: shared schemas (dataclasses or TypedDicts) for the §5 records, plus a mock-data generator (can wrap `make_mock_outputs.py`).
2. Red-team set, ~50 Qs, Hindi / Hinglish / English: doses, mixing, legal, insurance, poisoning -> `data/processed/redteam.jsonl`. **[ASK]** Kiran or Anushka to hand-write the Hindi ones; LLM-drafted is fine only if a person reads each one.
3. Router labels: map KCC `query_type` -> `general | live_data | high_risk | emergency` -> `data/processed/router_labels.jsonl`. `emergency` has no KCC source; derive from keywords (poisoning, snakebite, fire, etc.) plus red-team items.
4. Keyword lists per category, 3 languages -> `src/router_gate/keywords/` (e.g. `high_risk.txt`, `emergency.txt`, `live_data.txt`, one file per category, tagged by script).
5. Hand-check his 50 gold Qs (`data/processed/gold_batches/gold_batch_kiran.csv`). **Manual.**

### Step 2: router and safety filter
6. Rule router: keyword match plus emergency rules (108 / 112 / KCC 1551). Emergency always escalates to cloud and shows the number.
7. Small intent classifier (TF-IDF + logistic regression is enough) trained on **train split only**.
8. Offline output filter: block number + unit pairs, Devanagari digits, Hindi/Hinglish unit words (ml, लीटर, किलो, ग्राम, एकड़...), and spelled-out numbers.
9. Report high-risk routing recall and filter miss rate on the red-team set.

### Step 3: gate (needs B2/B3 files; build on mock first)
10. Gate v1: score from `mean_logprob` / `min_logprob`; report AUROC and a risk-coverage curve (label = judge correctness from Anushka's `scores_*.jsonl`).
11. **R:** random routing at the same cloud-call rate as the gate (uses B3 + B1 outputs).
12. **A1:** hybrid using the base model (uses B2 + B1 outputs, no new model calls).

### Step 4: queue and integration
13. Queue and connectivity simulator skeleton: priority, dedup, retry with back-off; good / patchy / poor traces; unit tests.
14. Run the hybrid end to end on 20 Qs -> `outputs/hybrid_*.jsonl`.
15. Write the router/gate section of the report (`reports/mid/report.typ`); clean the repo; **tag `mid-submission`**.

## Phase 2 (Oct 31 - Nov 15)
1. Extend the red-team set.
2. Gate classifier (LR or small MLP) on logprob features + question type, answer length, script, unknown crop/pest words. Threshold sweep on **calib**; risk-coverage per language. Metrics: AUROC, AURC, ECE, false-keep, unnecessary-send, cloud-call rate. H3: classifier AUROC > token-prob AUROC.
3. Full queue (priority, dedup, retry, stale re-ask for weather and prices, dated cache) and simulator.
4. Full hybrid + R + A1 + A4 (no queue) on the full set; queue metrics (delivery rate, p50/p90 time-to-answer, stale rate, duplicate-send rate); safety metrics (high-risk recall, offline dose rate, filter miss rate, emergency escalation rate).
5. **H1 verdict:** hybrid accuracy >= 90% of B1 with <= 50% cloud calls.
6. README with reproduction steps.

## Rules for this branch
- Split is frozen. Train only on `split == "train"`; tune thresholds on `calib`; never touch `test` except to report.
- Never commit API keys (`.env` is ignored) or personal data.
- Every number in the report must trace to a script + an `outputs/` file.
- Read the existing CLAUDE.md of `anushka/data` only for Anushka's tasks; this file replaces it on this branch.

## Open questions
1. **[ASK]** Is "emergency" routed purely by rules, or should the classifier also learn it (no KCC training rows exist)?
2. **[ASK]** Gate label: judge `correct` only, or `correct` + `partly correct`, counts as "edge answer is fine"?
3. **[ASK]** Does Kiran have any local code/data not pushed? If so, merge it here instead of rewriting.
4. **[ASK]** Offline safety filter: block, or replace with a deferral message ("please contact KCC 1551")?
