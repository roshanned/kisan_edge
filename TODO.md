# TODO for the mid-submission (Oct 30)

Plain list. Do these in order. "Time" is a rough guess.

## What we already have
- Answers from the small model (before and after tuning), from the cloud model (with tools, no document search), and from the combined system, all scored.
- Results tables, a chart and the report (`reports/mid/report.pdf`).
- Document search (B1) and the "no tools" run (A3) are **not** done, because we have no document collection. The report says so.

## Must do today

| # | What | Who | Time |
|---|---|---|---|
| 1 | **Spot-check what the AI changed in the gold set.** The AI dropped 42 bad questions and rewrote 60 answers and 35 categories (sheets in `data/processed/gold_batches/precheck/`). A team member already reviewed the drops, but **nobody has checked the rewrites**. Read as many as you can, Hindi ones first. Note any you disagree with. | Anushka + one Hindi reader | 30 min |
| 2 | **Check 50 of the AI judge's scores by hand** (`python -m src.eval.judge_check sample --n 50`, fill in the sheet, then `python -m src.eval.judge_check agree`). Write down how often you agree with the judge. Put the number in the report. | Anushka | 30 min |
| 3 | **Only if you changed any gold question in step 1:** run `python -m src.eval.merge_gold`, re-score each run (`python -m src.eval.score --run B3 --outputs outputs/edge_tuned.jsonl --judge gemini`, same for the others), then `python -m src.eval.report`. If there is no time, leave the numbers and say in the report that the spot-check found N problems. | Anushka | 20-60 min |
| 4 | **Read the report PDF start to finish.** Fix anything that is not true. Each person checks their own section. | Everyone | 30 min |
| 5 | **Upload the new files to the Hugging Face dataset** (it was last updated Oct 25): split, gold, model answers, scores, weather files. Commands are in the README. | Roshan (has the token) | 10 min |
| 6 | Make sure no password or key is in the repo (`.env` must not be committed). | Anyone | 5 min |
| 7 | **Tag `mid-submission` on GitHub and submit** the report PDF and the GitHub link. | Repo owner | 10 min |

## Be ready to explain (the report already says these)
- The small model got 10% right after tuning (2% before). The target was +10 points on Hindi; we got +5. Not met yet.
- The combined system gets 92% of the cloud model's score but sends 83 of 100 questions to the cloud (target was 50 or less). The safety rules force most questions to the cloud.
- The "is this answer sure?" signal from the small model does not work (worse than a coin flip). Needs a better method in the final phase.
- Scores come from an AI judge that has not been checked against humans yet (item 2), on gold questions that an AI cleaned up and humans have not fully checked (item 1). Both are stated in the report.

## Can wait until after submission
- Sai: collect 50-100 trusted documents, then run B1 and A3. Get a free data.gov.in key for market prices. (`docs/cloud/MANUAL_TODO.md`)
- Kiran or anyone: read the 51 test questions and word lists Claude drafted (`docs/kiran/MANUAL_TODO.md`).
- Decide: keep "always send risky questions to the cloud" or narrow it (`docs/kiran/DECISIONS.md`).
- Roshan: retrain a better tuned model; run on the dev and calibration sets.

## Final submission (Nov 15) in one line
Run everything on the full 700-question test set, fix the gate, finish documents and B1/A3, check the judge on 100 questions, write the final report. Code freeze Nov 14.
