# Project status: final phase (updated Nov 15, 2026)

Final submission: **Sun Nov 15**. Evaluations Nov 16-19. Branch: `main` (the only working branch; all other branches are merged into it).
This file is the hand-off: anyone (or any Claude session) can continue from it. Design decisions: `docs/DECISIONS.md` (D1-D29). Every command, in order: `scripts/final_pipeline.sh`.

## State: all automatic work is done (Nov 15)

Every run, judgment and metric is complete. Nothing is running. The human checks of Nov 14-15 (judge labels, Hindi review, ban list, schemes) are in `summary.json` and the report. On Nov 15 `reports/final/report.typ` was rewritten in two-column ACL layout with the sections Abstract, Introduction, Literature Review, Dataset, Methodology, Experiment Runs, Ablations, Evaluations, Limitations, Conclusions, References (bibliography in `reports/final/refs.bib`); the earlier single-column version is kept as `report_old.typ`. Build: `typst compile --root . reports/final/report.typ reports/final/report.pdf`. `slides.typ` is unchanged. Only the "Needs a human" items below are left.

## Final results (all in `outputs/final/summary.json`; report `reports/final/report.pdf`, slides `reports/final/slides.pdf`)

| | Result |
|---|---|
| B1 cloud (RAG + tools), 700 test | 28.6% strict, 47.0% lenient |
| Hybrid H (B3 + B1, trained gate) | 28.0% (98% of B1; difference -0.6, CI -2.9 to +1.7) at 74.6% cloud calls; 25% answered on the phone |
| **H1** (>= 90% of B1 with <= 50% cloud, on general questions as the proposal states it) | **met on the point estimate, weakly supported**: 280 general test questions, hybrid 25.0% vs B1 26.1% strict (95.9% of B1; lenient 46.4% vs 46.1%) with 43.6% sent to the cloud. Caveats (rechecked Nov 14): the bootstrap CI on the ratio is 0.76 to 1.19 (about 72% chance the true ratio is >= 0.9); random routing at 47.5% cloud gets 90.4% of B1, so the gate adds little over chance here; absolute accuracy is low for both (~25%); the "general" reading was adopted after the all-question view failed. **Over all 700 questions it is not met**: 98% of B1 but 74.6% cloud calls, because the router sends all high-risk and live-data questions to the cloud (90% of B1 needs about 60% cloud calls) |
| **H2** (+10 points on Hindi) | **not met**: +7.0 points (CI 3.0 to 10.7); seeds agree; BhashaBench 33.6% -> 29.8% |
| **H3** (trained gate > token probability) | **met as defined**: AUROC 0.87 vs 0.16 (0.77 vs 0.27 without deferrals). But token probability is inverted for the tuned model; with its sign corrected (chosen on dev) it reaches 0.84 (0.73 without deferrals), so the classifier leads by only a few points (CI +0.001 to +0.049). `outputs/final/gate_diagnostics.json` |
| Safety (held-out red-team v3) | 92.6% risky to cloud; emergency recognised 50%, number shown 95.8%; 0% doses shown offline |
| Cloud ablations | no retrieval (A2) 25.7% (-2.9 vs B1); no tools (A3, 350-question half) 18.6% (-10.9; live-data questions 61% -> 14%) |
| Cloud | Recall@5 0.60 -> 0.92 with query rewrite; citation faithfulness 91%; weather tool chosen 73%; fault injection: 90% recovery from transient timeouts, at most 5% invented numbers |
| Queue | patchy link: 28.0% with queue vs 18.7% without (A4) |
| Judge | second LLM judge agrees on correct vs not for 93% of 150 answers (kappa 0.34 three-way). **Human check (Nov 14, one labeller, 100 answers): 85% exact agreement, kappa 0.63, 92% on correct vs not, 89% on wrong vs not**; no bias in strict accuracy on this sample (human 13% correct, judge 13%); judge a bit more generous on partly correct (27% vs 22% not wrong). Sheet: `reports/final/judge_check_sheet_final.csv`, summary `reports/final/judge_agreement.md` |
| Phone | 4-bit GGUF 2.0 GB, 17.9 tok/s on a laptop CPU, 3.5 GB RAM |

## Pending

**Needs a human:**
1. Read the new `reports/final/report.pdf` (check the references in `refs.bib`: they were written from memory) and `slides.pdf`; tag `final-submission` on `main`; submit by Nov 15.
2. ~~Hand-label 100 judge outputs~~ **done Nov 14** (`judge_check_sheet_final.csv`; numbers in `summary.json` key `judge_human`, in the report). Optional: a second person labels the same sheet to get human-human agreement.
3. ~~Hindi review~~ **done Nov 15** by team members who read Hindi, no changes: red-team v2/v3 (141 rows, `human_reviewed: true`), the 158 gold questions, and the router keyword lists. (`gold.jsonl` now has `human_checked: true`; `check_method` stays `ai_precheck` because an LLM proposed the corrections the people confirmed.)
4. `src/cloud/banned_pesticides.txt` **verified Nov 15** against the CIB&RC list (updated 31.10.2026): 87 entries. Re-check of saved answers: 11 of 700 B1 answers (1.6%) name a now-listed banned product, not regenerated (see report, Safety). `data/snapshots/schemes.json` also checked and corrected Nov 15 (`needs_verification: false`; the scheme tool was never called in the saved runs, so no result changes).
5. Optional: data.gov.in key for mandi prices; accept HF terms for native BhashaBench-Krishi and Indic-KCC-Agri-Advisory.
6. Upload to Hugging Face: create a token with write access to the `kisan-edge` org (huggingface.co/settings/tokens), run `hf auth login`, then `python scripts/upload_hf.py` (stages and uploads everything, 217 files / 58 MB; the current saved token is read-only).
7. Rehearse the demo (`docs/DEMO.md`).

**To rebuild everything from the saved outputs:** `python -m src.eval.run_final`, then compile `reports/final/report.typ` and `slides.typ` with typst (see their headers). To re-run model calls elsewhere, copy `.env`, `cache/gemini.sqlite` and `outputs/cache/judge_cache.jsonl` (calls are cached; runs are resumable).
