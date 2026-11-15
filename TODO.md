# TODO for the final submission (Nov 15)

Only the steps that need a human: a decision, a login, or a Hindi reader. The full pending list, including the automatic steps still running, is in `STATUS.md`. In order of importance.

## Must do before submitting

| # | What | Why it matters | Time |
|---|---|---|---|
| 1 | **Read `reports/final/report.pdf` end to end.** Fix anything that is not true or not clear. | It is the graded deliverable. | 45 min |
| 2 | **Approve tagging `final-submission` on `main`** once the report is final. All work is on `main`. | Graders look at GitHub. | 10 min |
| 3 | ~~Check 100 judge labels by hand~~ **Done Nov 14**: 85% exact agreement with the judge, kappa 0.63, 92% on correct vs not (`reports/final/judge_agreement.md`, report section "Can the judge be trusted?"). Optional: a second labeller on the same sheet. | Every accuracy number rests on the LLM judge. | done |
| 4 | **Upload to Hugging Face**: the saved token is read-only. Create a token with write access to the `kisan-edge` org, `hf auth login`, then `python scripts/upload_hf.py` (everything is staged by the script). | The README says all data lives there. | 5 min |
| 5 | Prepare the slides and rehearse the live demo (`python -m src.demo ...`, see README "Demo"). | Nov 16-19 presentation. | 1-2 h |

## Should do (each one improves a reported number or removes a caveat)

| # | What | Effect |
|---|---|---|
| 6 | ~~Red-team v2/v3 review and keyword lists~~ **done Nov 15**, no changes. | | done |
| 7 | ~~Human check of the 158 gold questions~~ **done Nov 15**, no changes (`gold.jsonl`: `human_checked: true`). | | done |
| 8 | ~~Verify `banned_pesticides.txt` and `schemes.json`~~ **done Nov 15** (banned list: CIB&RC 31.10.2026, 87 entries; schemes checked and corrected). | | done |
| 9 | Get a free data.gov.in API key, put `DATA_GOV_API_KEY` in `.env`, run `python -m src.cloud.fetch_snapshots mandi`. | The mandi-price tool has no data, so price questions get "unavailable" |
| 10 | Accept the terms of the gated datasets on Hugging Face: `bharatgenai/BhashaBench-Krishi` (native Hindi, 2,757 Qs; we used the machine-translated Hindi subset of the ungated BhashaBench-Multi) and `sthanika-ai/Indic-KCC-Agri-Advisory-Benchmark` (evaluation-only licence). Then `python -m src.edge.bhashabench --native --parquet <file>` on Kaggle. | Native-Hindi benchmark numbers |
| 11 | Confirm or change decisions D17-D27 in `docs/DECISIONS.md` (model switch to Gemma, district context, red-team method, judge-quota savings). | The team owns the choices |
