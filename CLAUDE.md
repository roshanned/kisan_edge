# CLAUDE.md: Kisan-Edge, final phase

Read [STATUS.md](STATUS.md) first: what is done, what is running, and the ordered list of everything pending. [PLAN.md](PLAN.md) is the original plan (sections 4 and 4.2 = final-phase goals and the experiment checklist); [docs/kiran/DECISIONS.md](docs/kiran/DECISIONS.md) records every design decision (D1-D27). The final submission is due **Nov 15, 2026**, with no extensions.

## Layout
`src/data` split and cleaning · `src/edge` edge model, GGUF bench, BhashaBench · `src/cloud` agent, retrieval, tools, metrics · `src/router_gate` router, filter, gate, hybrid, red-team · `src/queue_sim` queue · `src/eval` judge, scoring, `run_final.py` · `src/demo.py` live demo · `kaggle/jobs` GPU/CPU jobs · `scripts/` pipelines · `outputs/final` final-phase results · `outputs/` (top level) mid-submission files, keep unchanged · `reports/final/report.typ` final report.

## Rules
- The split is frozen. Train only on `split == "train"`; tune thresholds on `calib` (gate fitted on `dev`); report on `test`.
- One judge for every final run: `JUDGE_MODEL=gemma-4-31b-it`. Cloud agent: `GEMINI_MODEL=gemma-4-26b-a4b-it` (`.env.example`). Do not mix models within a run.
- All model calls are cached (`cache/gemini.sqlite`, `outputs/cache/judge_cache.jsonl`); runs are resumable. Never run two copies of the same chain: they append to the same files.
- Free-tier limits per model: 30 requests and 16,000 input tokens per minute; `src/common/ratelimit.py` paces both.
- Heavy GPU work goes to Kaggle (`kaggle/push_code.py`, then `kaggle kernels push`), not the laptop.
- Every number in the report must come from `outputs/final/summary.json` or another file named in its caption; `python -m src.eval.run_final` rebuilds them without model calls.
- Never commit `.env`, API keys or personal data. Work on `main` only (all other branches are merged). Do not tag `final-submission` without Roshan's approval.
- Things only a human can do (hand-labelling, Hindi review, logins, approvals) go in STATUS.md "Needs a human"; never claim them as done.
- Tests: `pytest -q` (62 tests, no network).
