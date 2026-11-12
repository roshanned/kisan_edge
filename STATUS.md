# Project status: final phase (updated Nov 12, 2026, evening)

Final submission: **Sun Nov 15**. Evaluations Nov 16-19. Branch: `roshan/edge` (not yet merged to `main`).
This file is the hand-off: anyone (or any Claude session) can continue from it. Design decisions: `docs/kiran/DECISIONS.md` (D1-D27). Every command, in order: `scripts/final_pipeline.sh`.

## Done

| Area | What exists | Where |
|---|---|---|
| Data | Frozen split (test 700, calib 600, dev 600, train 16,435); gold subset 158 (LLM pre-checked) | `data/processed/` |
| Edge model | Llama-3.2-3B + QLoRA (B3); B2/B3 answers with logprobs on test+calib+dev; 2 seed re-runs on test; BhashaBench-Krishi Hindi (3,000 MCQs: base 33.6%, tuned 29.8%) | `outputs/final/edge_*`, `bhashabench_*` (Kaggle jobs 06, 07) |
| Phone size | 4-bit GGUF Q4_K_M, 2.01 GB; laptop i7 4 threads 17.9 tok/s generate, 3.5 GB RAM; Kaggle CPU 8.6 tok/s | `outputs/final/llamacpp_*` (job 08, `src/edge/bench_llamacpp.py`) |
| Judging | One judge (`gemma-4-31b-it`) for all final runs. Done: B3 test, B2 test, B3 calib, B3 dev. Judge vs old flash-lite judge on B3 gold: 69% agreement, kappa 0.49 | `outputs/final/scores_*` |
| Router / safety | Red-team v2 + v3 (held out, written by other models); final router on v3: 92.6% risky to cloud, emergency recognised 50%, emergency number shown 95.8%, controls over-escalated 38.9% | `outputs/router_metrics.json`, `data/processed/redteam_v*.jsonl` |
| Retrieval | Recall@5 0.60 raw query, 0.92 with LLM rewrite (60 synthetic queries) | `outputs/final/rag_recall.json` |
| Code | Gate v2 (classifier, calib cut, bootstrap H3), hybrid policies, cloud metrics, fault injection, `run_final.py` (all tables/figures), judge checks, live demo, report skeleton | `src/`, `reports/final/report.typ` |
| Tests | 62 passing (`pytest -q`) | `tests/` |

## Running now (on Roshan's laptop; both resumable)

| Chain | Steps | Log |
|---|---|---|
| `scripts/cloud_chain.sh` (agent model `gemma-4-26b-a4b-it`) | B1 to 700 (was 430/700) -> regenerate B1 from cache with the D27 weather fix -> A2 (700) -> A3 (700) -> fault injection | `logs/cloud_chain.log`, `logs/cloud_*.log` |
| `scripts/judge_chain.sh B3_s1 B3_s2 B3 B2 B3_calib B3_dev B1 A2 A3` (judge `gemma-4-31b-it`) | seed re-runs (Hindi only) -> fill-in pass for failed labels -> B1 (after regeneration) -> A2 -> A3 | `logs/judge_chain_2.log` |

Rough timing: about 2.3 B1/A3 questions a minute (agent limited to 16k input tokens/min), A2 faster; judge 7-10 labels/min (Gemma 31B is often "high demand"). Expected finish: early Nov 13.

**To resume on another machine:** copy `.env` (see `.env.example`), `cache/gemini.sqlite` and `outputs/cache/judge_cache.jsonl` if possible (otherwise answers are re-requested), then run the two chains above. Never run two copies of the same chain at once: they append to the same files.

## Pending (everything left, in order)

**Automatic (no decisions needed, just run):**
1. Finish the two chains above (B1, regeneration, A2, A3, fault injection; judge seeds, fill-in, B1, A2, A3).
2. `python -m src.cloud.metrics --runs B1,A2,A3 --faithfulness 60` (citation faithfulness uses `gemini-3.5-flash-lite`).
3. `python -m src.eval.judge_check --dir outputs/final judges --n 150 --model gemini-3.5-flash-lite` (judge vs second judge).
4. `python -m src.eval.run_final` -> `outputs/final/summary.json`, `reports/final/tables`, `reports/final/figures` (gate, hybrids H / H_tok / R / A1 / H_A2 / H_A3, queue traces + A4, H1 / H2 / H3).
5. Fill every `TODO-INTERPRET` block in `reports/final/report.typ` from `summary.json`, compile: `python -c "import typst; typst.compile('reports/final/report.typ', output='reports/final/report.pdf', root='.')"`, read the PDF.
6. Update README results line, commit, push.
7. `python -m src.eval.judge_check --dir outputs/final --report-dir reports/final sample --n 100` (sheet for the human judge check).
8. Slides for the presentation (results from `summary.json`; demo steps in `docs/DEMO.md`).

**Needs a human:**
9. Approve merge of `roshan/edge` into `main` and tag `final-submission`; submit report PDF + GitHub link by Nov 15.
10. Hand-label 100 judge outputs (`reports/final/judge_check_sheet.csv`), run `... judge_check --dir outputs/final --report-dir reports/final agree`, put the number in the report.
11. Hindi speaker reads red-team v2/v3 and the Nov 11 keyword additions; human check of the 158 gold questions.
12. Verify `src/cloud/banned_pesticides.txt` and `data/snapshots/schemes.json` (written from memory).
13. data.gov.in API key for mandi prices (`DATA_GOV_API_KEY`, `python -m src.cloud.fetch_snapshots mandi`); without it price questions get "unavailable".
14. Accept terms on Hugging Face for `bharatgenai/BhashaBench-Krishi` (native Hindi) and `sthanika-ai/Indic-KCC-Agri-Advisory-Benchmark`, if those numbers are wanted.
15. Upload `outputs/final/` and the new data files to the HF dataset `kisan-edge/kisan-edge-data`.
16. Rehearse the demo (`docs/DEMO.md`).

## Known results so far (preliminary, before the fill-in pass)
- Strict accuracy on test: B3 9.5%, B2 5.0%; Hindi (Devanagari) B3 9.9% vs B2 2.7%: about +7 points, so H2 (+10) looks not met.
- Token probability is anti-correlated with correctness for B3 (mid: AUROC 0.18): the model is surest of its deferral template.
- With the designed router (rules + classifier), 68.7% of test questions are forced to the cloud before the gate, so H1's 50% cloud-call target is out of reach by construction; the report shows the trade-off curve.
