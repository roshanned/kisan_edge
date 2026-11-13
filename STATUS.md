# Project status: final phase (updated Nov 13, 2026, 11:00 IST)

Final submission: **Sun Nov 15**. Evaluations Nov 16-19. Branch: `main` (the only working branch; all other branches are merged into it).
This file is the hand-off: anyone (or any Claude session) can continue from it. Design decisions: `docs/kiran/DECISIONS.md` (D1-D29). Every command, in order: `scripts/final_pipeline.sh`.

## CLAIMED: a Claude session is running these on Roshan's laptop. Do NOT run them.

Claimed until this section is removed. Running them anywhere else duplicates API calls and, on this laptop, corrupts the output files (two writers append to the same file).

| Claimed task | State at Nov 13, 11:00 |
|---|---|
| `scripts/a3_half.sh`: A3 on the 350-question half (D29), then fault injection | A3 at 181/350 |
| `scripts/judge_chain.sh` (now judging A2) and `scripts/judge_tail.sh` (A2 fill-in, A3, final fill-in) | judging A2 |
| Re-run `python -m src.eval.run_final`, fill the last report placeholders (summary, cloud ablations), rebuild report and slides PDFs | after the above |

A second session can safely do only the "Needs a human" items or read-only review.

## Results so far (all in `outputs/final/summary.json`; report `reports/final/report.pdf`, slides `reports/final/slides.pdf`)

| | Result |
|---|---|
| B1 cloud (RAG + tools), 700 test | 28.6% strict, 47.0% lenient |
| Hybrid H (B3 + B1, trained gate) | 28.0% (98% of B1; difference -0.6, CI -2.9 to +1.7) at 74.6% cloud calls; 25% answered on the phone |
| **H1** (>= 90% of B1 with <= 50% cloud) | **not met**: accuracy yes, cloud calls no; the router forces 68.7% of questions to the cloud. 90% of B1 needs about 60% cloud calls (trade-off curve) |
| **H2** (+10 points on Hindi) | **not met**: +7.0 points (CI 3.0 to 10.7); seeds agree; BhashaBench 33.6% -> 29.8% |
| **H3** (trained gate > token probability) | **met**: AUROC 0.87 vs 0.16 (0.77 vs 0.27 without deferrals) |
| Safety (held-out red-team v3) | 92.6% risky to cloud; emergency recognised 50%, number shown 95.8%; 0% doses shown offline |
| Cloud | Recall@5 0.60 -> 0.92 with query rewrite; citation faithfulness 91%; weather tool chosen 73% |
| Queue | patchy link: 28.0% with queue vs 18.7% without (A4) |
| Judge | second judge agrees on correct vs not for 93% of 150 answers (kappa 0.34 three-way) |
| Phone | 4-bit GGUF 2.0 GB, 17.9 tok/s on a laptop CPU, 3.5 GB RAM |

## Pending

**Automatic (claimed above):** A3 half + judging, fault injection, A2/A3 judging and fill-ins, final `run_final`, last report text (summary and cloud ablation paragraphs), rebuild PDFs, remove the CLAIMED section.

**Needs a human:**
1. Read `reports/final/report.pdf` and `slides.pdf`; tag `final-submission` on `main`; submit by Nov 15.
2. Hand-label 100 judge outputs (`reports/final/judge_check_sheet.csv`, column `human_label`), then `python -m src.eval.judge_check --dir outputs/final --report-dir reports/final agree` and add the number to the report.
3. Hindi speaker reads red-team v2/v3, the Nov 11 keyword additions and the 158 gold questions.
4. Verify `src/cloud/banned_pesticides.txt` and `data/snapshots/schemes.json` (written from memory).
5. Optional: data.gov.in key for mandi prices; accept HF terms for native BhashaBench-Krishi and Indic-KCC-Agri-Advisory.
6. Upload `outputs/final/` to the HF dataset `kisan-edge/kisan-edge-data`.
7. Rehearse the demo (`docs/DEMO.md`). Keep the laptop awake and online while runs are going (sleep stalled them overnight).

**To resume elsewhere:** copy `.env`, `cache/gemini.sqlite` and `outputs/cache/judge_cache.jsonl`, then re-run the claimed scripts; all are resumable.
