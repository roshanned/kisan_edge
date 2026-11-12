# TODO for the final submission (Nov 15)

Only the steps that need a human: a decision, a login, or a Hindi reader. The full pending list, including the automatic steps still running, is in `STATUS.md`. In order of importance.

## Must do before submitting

| # | What | Why it matters | Time |
|---|---|---|---|
| 1 | **Read `reports/final/report.pdf` end to end.** Fix anything that is not true or not clear. | It is the graded deliverable. | 45 min |
| 2 | **Approve the git commit, push, merge to `main` and tag `final-submission`.** Nothing from the final phase is committed yet. | Graders look at GitHub. | 10 min |
| 3 | **Check 100 judge labels by hand**: open `reports/final/judge_check_sheet.csv`, fill `human_label` (correct / partly_correct / wrong) without looking at `judge_label` first, then run `python -m src.eval.judge_check --dir outputs/final --report-dir reports/final agree`. Put the agreement into the report (section "Evaluation method"). | Every accuracy number rests on the LLM judge. Judge-vs-judge agreement is already reported, but it is not a human check. | 60-90 min |
| 4 | **Upload the final outputs to the Hugging Face dataset** `kisan-edge/kisan-edge-data` (folder `outputs/final/`, `data/processed/redteam_v2.jsonl`, `redteam_v3.jsonl`, `corpus/recall_queries.jsonl`). Commands are in the README. | The README says all data lives there. | 10 min |
| 5 | Prepare the slides and rehearse the live demo (`python -m src.demo ...`, see README "Demo"). | Nov 16-19 presentation. | 1-2 h |

## Should do (each one improves a reported number or removes a caveat)

| # | What | Effect |
|---|---|---|
| 6 | A Hindi speaker reads the red-team sets `redteam_v2.jsonl` (69) and `redteam_v3.jsonl` (72), and the keywords added on Nov 11 (bottom of `src/router_gate/keywords/*.txt`). Mark `human_reviewed: true` (or fix rows) and re-run `python -m src.router_gate.eval_router` and `python -m src.eval.run_final`. | Removes "LLM-written, machine-checked only" from the safety numbers |
| 7 | Human check of the 158 gold questions (`data/processed/gold.jsonl`, `check_method = ai_precheck`). | The gold columns become human-checked |
| 8 | Verify `src/cloud/banned_pesticides.txt` and `data/snapshots/schemes.json` against official lists (both were written from memory). | Cloud safety filter and scheme tool facts |
| 9 | Get a free data.gov.in API key, put `DATA_GOV_API_KEY` in `.env`, run `python -m src.cloud.fetch_snapshots mandi`. | The mandi-price tool has no data, so price questions get "unavailable" |
| 10 | Accept the terms of the gated datasets on Hugging Face: `bharatgenai/BhashaBench-Krishi` (native Hindi, 2,757 Qs; we used the machine-translated Hindi subset of the ungated BhashaBench-Multi) and `sthanika-ai/Indic-KCC-Agri-Advisory-Benchmark` (evaluation-only licence). Then `python -m src.edge.bhashabench --native --parquet <file>` on Kaggle. | Native-Hindi benchmark numbers |
| 11 | Confirm or change decisions D17-D26 in `docs/kiran/DECISIONS.md` (model switch to Gemma, district context, red-team method, judge-quota savings). | The team owns the choices |
