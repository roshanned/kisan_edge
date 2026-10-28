# Anushka checklist (updated Oct 28, 2026)

Legend: [x] done and tested, [ ] to do, [~] needs someone else / needs your input.

## Phase 1: data
- [x] Cleaning and labelling rules written ([info.md](info.md) section 2; code is Roshan's `src/data/common.py`)
- [x] Main data = Roshan's cleaned KCC (decision recorded)
- [x] 50-question seed file: `data/processed/seed_50.jsonl` (train questions only)
- [x] Split script, run once, test frozen (700 test / 600 calib / 600 dev / 16,435 train), leak tests pass
- [x] Roshan's pilot questions all in dev
- [x] ~200 gold candidates picked, 4 batches of 50 in `data/processed/gold_batches/`
- [x] `gold.jsonl` written (200, unchecked) so others can run now
- [ ] [~] Send each person their gold sheet + tell Roshan the pilot ids are in dev
- [ ] Hand-check my own 50 (`gold_batch_anushka.csv`)
- [ ] [~] Collect the other three sheets, run `merge_gold` again
- [ ] Send the frozen train split (`questions.jsonl`, `split == "train"`) to Roshan; he retrains QLoRA
- [ ] Commit and push `anushka/data`; open PR to `main`

## Phase 1: evaluation harness
- [x] LLM judge (Gemini REST, cached, rate-limited, retries) + offline mock for testing
- [x] Scoring script, shared format, missing answers counted
- [x] Per-language/script reporting, Wilson 95% intervals, bar chart
- [x] Judge-vs-human check script (agreement + kappa)
- [x] Unit tests for split, parser, kappa, intervals (11 pass)
- [~] Put `GEMINI_API_KEY` in `.env` (currently blank); confirm model name
- [ ] Smoke test the real judge on `--limit 20`
- [ ] Hand-label ~50 judged rows and run `judge_check agree`

## Phase 1: results and report
- [ ] [~] Score B1, B2, B3, R, A1, A2 (waiting on outputs from Sai / Roshan / Kiran, due Oct 28-29)
- [ ] Tables and plots (`src.eval.report`)
- [ ] Mid-submission report in `reports/mid/` (outline PLAN.md 3.1; collect sections from everyone)
- [ ] Submit Oct 30

## Phase 2 (Oct 31 - Nov 15)
- [ ] Score the full 700 test set; per-language tables
- [ ] Loaders for BhashaBench-Krishi Hindi (2,757 Qs) and Indic-KCC-Agri-Advisory
- [ ] Judge vs human agreement on 100 Qs
- [ ] Overall metrics: accuracy, cloud calls per 100 Qs, offline usefulness
- [ ] Final report; submit Nov 15

## Decisions recorded
- [x] Crop-recommendation exact-match metric dropped (no data)
- [x] No KCC 2024-25; Roshan's data is the main dataset
