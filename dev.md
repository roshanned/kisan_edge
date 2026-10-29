# How to run (data and evaluation)

Everything runs from the repo root. Python 3.10+; the commands below were tested on 3.14.

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # pandas, huggingface_hub, requests, matplotlib, pytest, ...
cp .env.example .env                       # then set GEMINI_API_KEY=... in .env (never commit it)
```
`.env` keys: `GEMINI_API_KEY`, `GEMINI_MODEL` (default `gemini-2.5-flash`), `GEMINI_RPM` (default 10, calls per minute).

## 1. Build the split (once; already done and frozen)
```bash
python -m src.data.fetch_inputs            # Roshan's cleaned files -> data/raw/hf/processed/
python -m src.data.build_questions         # -> data/processed/{questions,seed_50,gold_candidates}.jsonl,
                                           #    gold_batches/*.csv, split_manifest.json
python -m pytest tests/test_split.py       # leak / frozen-test checks
```
The script **refuses to run if `questions.jsonl` exists** (the test set is frozen). `--force` overrides it; do not use it after the files were shared.

## 2. Gold set
1. Send each person their sheet `data/processed/gold_batches/gold_batch_<name>.csv` (open in Excel/LibreOffice, UTF-8).
2. They fill the `y/n` columns, optional `fixed_category`, `fixed_reference_answer`, `drop`.
3. Put the returned CSVs back in `data/processed/gold_batches/`, then:
```bash
python -m src.eval.merge_gold              # -> data/processed/gold.jsonl (works with partly filled sheets)
```

## 3. Score a run
```bash
python -m src.eval.score --run B2 --outputs outputs/edge_base.jsonl
python -m src.eval.score --run B3 --outputs outputs/edge_tuned.jsonl
python -m src.eval.score --run B1 --outputs outputs/cloud_B1.jsonl
python -m src.eval.score --run A1 --outputs outputs/hybrid_A1.jsonl     # reads final_answer
# options: --subset gold|test|dev|calib   --limit 20   --judge mock
```
Output: `outputs/scores_<RUN>.jsonl`. The first call to an API judge writes a cache (`outputs/cache/`), so re-runs cost nothing.
Debug on `--limit 20` first (free-tier quota).

## 4. Judge trust check
```bash
python -m src.eval.judge_check sample --n 50     # -> reports/mid/judge_check_sheet.csv
# fill the human_label column (correct | partly_correct | wrong) without looking at judge_label
python -m src.eval.judge_check agree             # -> reports/mid/judge_agreement.md
```

## 5. Tables and plots
```bash
python -m src.eval.report                  # -> reports/mid/tables/*.md|csv, reports/mid/figures/accuracy_by_language.png
```

## Test the pipeline without real outputs or a key
```bash
python -m src.eval.make_mock_outputs       # fake edge/cloud files from the gold set
python -m src.eval.score --run B3 --outputs outputs/mock_edge.jsonl --judge mock
python -m src.eval.score --run B1 --outputs outputs/mock_cloud.jsonl --judge mock
python -m src.eval.report --out /tmp/rep
rm outputs/scores_*.jsonl outputs/mock_*.jsonl      # clean up; mock labels are not results
python -m pytest                           # unit tests for split, parsing, kappa, Wilson interval
```

## Files
| Path | What |
|---|---|
| `src/data/build_questions.py` | the one-time split + gold batches |
| `src/data/fetch_inputs.py` | downloads Roshan's files |
| `src/eval/judge.py` | Gemini / mock judge with disk cache |
| `src/eval/score.py` | one run -> `scores_<RUN>.jsonl` |
| `src/eval/merge_gold.py` | gold sheets -> `gold.jsonl` |
| `src/eval/judge_check.py` | human-vs-judge agreement |
| `src/eval/report.py` | tables + plot |
| `tests/` | pytest checks |
