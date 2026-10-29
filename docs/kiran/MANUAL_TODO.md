# What only a human can do (Kiran's layer)

Ordered by what blocks the mid-submission. "Who" is a suggestion.

| # | Task | Who | Blocks | Time |
|---|---|---|---|---|
| 1 | **Read all 51 red-team Qs** in `data/processed/redteam.jsonl` (Hindi especially). Fix wording, set `human_reviewed: true`. Re-run `eval_router` | Hindi reader | Safety numbers in the report | 30 min |
| 2 | **Write ~20 NEW red-team Qs without looking at the keyword lists**, then run `python -m src.router_gate.eval_router`. This is the honest recall number; the current 1.00 is optimistic | Kiran or Anushka | Report | 30 min |
| 3 | **Review the keyword lists** `src/router_gate/keywords/*.txt`: add dialect spellings (Awadhi, Bhojpuri, Braj words), remove anything that wrongly fires (e.g. check "dawa" and "rain" prefixes on test questions) | Hindi reader | Router accuracy | 30 min |
| 4 | **Decide the H1 question** (DECISIONS "Problem for the team"): keep safety-first (accept ~66-85% cloud) or narrow high_risk. Whichever is chosen, say it in the report | Team | H1 verdict | discussion |
| 5 | **Confirm the CONFIRM rows** in DECISIONS.md (D2, D4, D9) | Kiran | n/a | 10 min |
| 6 | **Hand-check Kiran's 50 gold questions**: `data/processed/gold_batches/gold_batch_kiran.csv` (columns question_ok, answer_correct, lang_script_tag_ok, category_ok, fixed_*, drop) | Kiran | gold.jsonl | 1 h |
| 7 | **Probe the safety filter by hand:** read 30 real edge answers from Roshan's B3 file; note any dose the filter misses (spelled-out numbers, dialect units) and any safe answer it blocks; add them to `PROBE` in `make_redteam.py` | Kiran | Filter miss rate | 30 min |
| 8 | **Get the edge and cloud outputs** (B2, B3 from Roshan; B1 from Sai) and Anushka's `scores_B3.jsonl`, then run the commands in README "When the real outputs exist" | Whoever has the files | Gate, R, A1, H1, H3 | 10 min |
| 9 | **Check the interim messages** in `hybrid.py` `INTERIM` and `safety_filter.DEFERRAL` read naturally in Hindi; check the emergency numbers (108, 112, KCC 1551) are right for UP | Hindi reader | Demo | 10 min |
| 10 | **Choose the queue numbers** (D9): link success rates, 1 question/minute, TTL 60 ticks. Replace with measured values if anyone has them, or state "illustrative" in the report | Kiran | Queue metrics | 15 min |
| 11 | Write the router/gate paragraph in the report. Draft in `reports/mid/kiran_section.md` | Kiran | Report | 30 min |
| 12 | Tag `mid-submission` on `main` after the PR merges (PLAN.md Kiran 15) | Repo owner | Submission | 5 min |

## Phase 2 (after Oct 30) still open
- Extend the red-team set (PLAN.md §4 Kiran 1); add real emergency Qs so the classifier can learn them.
- Run gate v2 on Roshan's full dev/calib/test outputs; threshold sweep on calib; per-language risk-coverage curves.
- Wire the real cloud client into the queue (D9 note) if a live demo is wanted.
- Add "unknown pest word" feature (D15) if time allows.
- README reproduction steps for the whole repo (repo owner).
