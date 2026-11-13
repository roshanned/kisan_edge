# Kisan-Edge

A phone-sized, LoRA-tuned language model that answers Uttar Pradesh farmers' questions in Hindi, Hinglish and English, offline. A router and a confidence gate send the questions it should not answer alone (doses, emergencies, weather and prices, low-confidence answers) to a cloud agent with document retrieval and tools, through an offline queue that delivers the answer once the farmer is back online.

**Final report:** [reports/final/report.pdf](reports/final/report.pdf) · **Proposal:** [project_proposal.pdf](project_proposal.pdf) · **Plan:** [PLAN.md](PLAN.md) · **What is left for a human:** [TODO.md](TODO.md)

**Team:** Anushka Sharma (data and evaluation) · Roshan K (edge model; from Oct 30 the whole project) · Sai Rithvik (cloud side) · Kiran R (router, gate, queue)

```
question ─> router (keywords + TF-IDF classifier) ─┬─ emergency ─> show 108 / 112 / KCC 1551 at once, then cloud
                                                   ├─ high-risk / live-data ─> safe interim message, queue -> cloud
                                                   └─ general ─> 4-bit Llama-3.2-3B on the phone ─> offline dose filter
                                                                   ─> gate (logprob features + classifier)
                                                                      ├─ confident: answer offline
                                                                      └─ unsure: interim answer, queue -> cloud
cloud agent: LLM + retrieval (BGE-M3 + FAISS over 383 documents) + tools (weather, mandi price, schemes) + safety filter
```

## Results (700 test questions; full report in `reports/final/report.pdf`)

| | Result |
|---|---|
| Cloud agent B1 (RAG + tools) | 28.6% strict accuracy |
| Hybrid (tuned edge + B1, trained gate) | 28.0%, i.e. 98% of B1 (no significant difference), with 74.6% cloud calls; 25% of questions answered on the phone, no dose ever shown offline |
| H1 (>= 90% of B1 at <= 50% cloud calls) | not met: the safety rules send 68.7% of questions to the cloud before the gate |
| H2 (+10 points on Hindi from fine-tuning) | not met: +7.0 points (95% CI 3.0 to 10.7) |
| H3 (trained gate beats token probability) | met: AUROC 0.87 vs 0.16 |
| Phone | 4-bit model 2.0 GB, about 18 tokens/s on a laptop CPU |

## Where things are

| Path | What |
|---|---|
| `src/data/` | Cleaning, IndicTrans2 translation, the frozen split (`data/processed/questions.jsonl`: test 700, calib 600, dev 600, train 16,435) |
| `src/edge/` | Model pilot, generation with token logprobs, safe SFT data, QLoRA, BhashaBench, llama.cpp benchmark |
| `src/cloud/` | Agent loop, Gemini/Gemma client (cache, pacing), retrieval, tools, cloud safety filter, metrics, fault injection |
| `src/router_gate/` | Router + keywords, intent classifier, offline dose filter, gate, hybrid runner, red-team sets |
| `src/queue_sim/` | Offline queue (priority, dedup, retry with back-off, stale re-ask) and connectivity traces |
| `src/eval/` | LLM judge, scoring, judge checks, `run_final.py` (every final table and figure) |
| `src/demo.py` | Live demo of the whole pipeline on one question |
| `kaggle/jobs/` | GPU/CPU jobs run from the command line: 01 pilot, 02-03 QLoRA + B2/B3, 04 RAG index, 06 full B2/B3 + BhashaBench, 07 seed re-runs, 08 4-bit GGUF + llama.cpp |
| `outputs/final/` | Final-phase answers, judge scores, hybrid runs and `summary.json` (every number in the final report) |
| `outputs/` (top level) | Mid-submission files, kept unchanged so the mid report still reproduces |
| `reports/final/`, `reports/mid/` | Reports (typst source + PDF), tables, figures |
| `docs/` | Layer guides; `docs/kiran/DECISIONS.md` lists every design decision (D1-D26) |

## Setup

```bash
python -m venv .venv && .venv/Scripts/activate      # Windows; use bin/activate elsewhere
pip install -r requirements.txt
cp .env.example .env    # GEMINI_API_KEY from Google AI Studio (free tier is enough, see below)
pytest -q               # 61 tests, no network needed
```
Compute: GPU steps run on Kaggle from the command line (`kaggle` CLI with an API token in `~/.kaggle`). The laptop only runs the API calls, the analysis and the llama.cpp benchmark.

## Reproduce the final results

[`scripts/final_pipeline.sh`](scripts/final_pipeline.sh) lists every command in order; each step writes to `outputs/final/`. In short:

1. **Edge (Kaggle):** `python kaggle/push_code.py "msg"`, then push jobs 06, 07 and 08 (`kaggle kernels push -p kaggle/jobs/06_edge_full --accelerator NvidiaTeslaT4`, ...) and download their outputs.
2. **Cloud:** `python -m src.cloud.query --questions data/processed/questions.jsonl --split test --run B1 --as-of 2026-10-30 --workers 8 --out outputs/final/cloud_B1.jsonl` (and A2, A3). Resumable after a quota stop.
3. **Judge:** `bash scripts/judge_chain.sh B3 B2 B3_calib B3_dev B1 A2 A3 B3_s1 B3_s2`.
4. **Metrics:** `python -m src.cloud.rag.recall_check --rewrite ...`, `python -m src.cloud.metrics --runs B1,A2,A3 --faithfulness 60`, `python -m src.cloud.fault_injection --n 20`, `python -m src.router_gate.eval_router`.
5. **Everything else:** `python -m src.eval.run_final` (gate, hybrids H / R / A1 / A4, queue traces, H1-H3) and `python -c "import typst; typst.compile('reports/final/report.typ', output='reports/final/report.pdf', root='.')"`.

**API quota.** All Gemini-API calls are cached (`cache/gemini.sqlite`, `outputs/cache/judge_cache.jsonl`), so re-running a finished step costs nothing. The free tier allows Gemma 4 about 30 requests and 16,000 input tokens per minute per model; the cloud agent (`gemma-4-26b-a4b-it`) and the judge (`gemma-4-31b-it`) use separate models and therefore separate quotas. From scratch, the cloud runs take about 10 hours and the judging about 8.

## Demo

```bash
# needs the llama.cpp CPU build in tools_ext/llamacpp/bin and the GGUF from Kaggle job 08
python -m src.demo "gehu ki buvai ka sahi samay kya hai" --district Kheri          # online
python -m src.demo "Bareilly mein agle 3 din mausam kaisa rahega" --offline       # interim answer + queued
python -m src.demo --flush                                                         # back online: answer the queue
```
Each step prints what the router, edge model, dose filter, gate and cloud agent decided, with timings. The 4-bit model answers in about 4 seconds on a laptop CPU (17.9 tokens/s at 4 threads).

## Data

Processed data, translations and model outputs are on the Hugging Face dataset [kisan-edge/kisan-edge-data](https://huggingface.co/datasets/kisan-edge/kisan-edge-data) (upload with `hf upload kisan-edge/kisan-edge-data <local path> <path in repo> --repo-type dataset`; ask Roshan for org access). Raw data is re-downloaded by `python -m src.data.download` from [Omegaindebt/Kisan_Call_Centre_Transcripts](https://huggingface.co/datasets/Omegaindebt/Kisan_Call_Centre_Transcripts) and [KisanVaani/agriculture-qa-english-only](https://huggingface.co/datasets/KisanVaani/agriculture-qa-english-only). BhashaBench-Krishi (Hindi) comes from the ungated [bharatgenai/BhashaBench-Multi](https://huggingface.co/datasets/bharatgenai/BhashaBench-Multi).

Never commit API keys (`.env` is gitignored) or personal data; phone numbers are removed during cleaning.
