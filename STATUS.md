# Project status: final phase (updated Nov 13, 2026, 12:40 IST)

Final submission: **Sun Nov 15**. Evaluations Nov 16-19. Branch: `main` (the only working branch; all other branches are merged into it).
This file is the hand-off: anyone (or any Claude session) can continue from it. Design decisions: `docs/kiran/DECISIONS.md` (D1-D29). Every command, in order: `scripts/final_pipeline.sh`.

## State: all automatic work is done (Nov 13, 12:40 IST)

Every run, judgment, metric, the report (`reports/final/report.pdf`) and the slides (`reports/final/slides.pdf`) are complete and pushed. Nothing is running. Only the "Needs a human" items below are left.

## Final results (all in `outputs/final/summary.json`; report `reports/final/report.pdf`, slides `reports/final/slides.pdf`)

| | Result |
|---|---|
| B1 cloud (RAG + tools), 700 test | 28.6% strict, 47.0% lenient |
| Hybrid H (B3 + B1, trained gate) | 28.0% (98% of B1; difference -0.6, CI -2.9 to +1.7) at 74.6% cloud calls; 25% answered on the phone |
| **H1** (>= 90% of B1 with <= 50% cloud) | **not met**: accuracy yes, cloud calls no; the router forces 68.7% of questions to the cloud. 90% of B1 needs about 60% cloud calls (trade-off curve) |
| **H2** (+10 points on Hindi) | **not met**: +7.0 points (CI 3.0 to 10.7); seeds agree; BhashaBench 33.6% -> 29.8% |
| **H3** (trained gate > token probability) | **met**: AUROC 0.87 vs 0.16 (0.77 vs 0.27 without deferrals) |
| Safety (held-out red-team v3) | 92.6% risky to cloud; emergency recognised 50%, number shown 95.8%; 0% doses shown offline |
| Cloud ablations | no retrieval (A2) 25.7% (-2.9 vs B1); no tools (A3, 350-question half) 18.6% (-10.9; live-data questions 61% -> 14%) |
| Cloud | Recall@5 0.60 -> 0.92 with query rewrite; citation faithfulness 91%; weather tool chosen 73%; fault injection: 90% recovery from transient timeouts, at most 5% invented numbers |
| Queue | patchy link: 28.0% with queue vs 18.7% without (A4) |
| Judge | second judge agrees on correct vs not for 93% of 150 answers (kappa 0.34 three-way) |
| Phone | 4-bit GGUF 2.0 GB, 17.9 tok/s on a laptop CPU, 3.5 GB RAM |

## Pending

**Needs a human:**
1. Read `reports/final/report.pdf` and `slides.pdf`; tag `final-submission` on `main`; submit by Nov 15.
2. Hand-label 100 judge outputs (`reports/final/judge_check_sheet.csv`, column `human_label`), then `python -m src.eval.judge_check --dir outputs/final --report-dir reports/final agree` and add the number to the report.
3. Hindi speaker reads red-team v2/v3, the Nov 11 keyword additions and the 158 gold questions.
4. Verify `src/cloud/banned_pesticides.txt` and `data/snapshots/schemes.json` (written from memory).
5. Optional: data.gov.in key for mandi prices; accept HF terms for native BhashaBench-Krishi and Indic-KCC-Agri-Advisory.
6. Upload `outputs/final/` to the HF dataset `kisan-edge/kisan-edge-data`.
7. Rehearse the demo (`docs/DEMO.md`).

**To rebuild everything from the saved outputs:** `python -m src.eval.run_final`, then compile `reports/final/report.typ` and `slides.typ` with typst (see their headers). To re-run model calls elsewhere, copy `.env`, `cache/gemini.sqlite` and `outputs/cache/judge_cache.jsonl` (calls are cached; runs are resumable).
