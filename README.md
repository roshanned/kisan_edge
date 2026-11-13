# Kisan-Edge

**A phone-sized farm advisor with a cloud fallback.** A LoRA-tuned 3B language model answers Uttar Pradesh farmers' questions in Hindi, Hinglish and English on the phone, offline. A router and a trained confidence gate decide which questions the phone may answer alone. The rest (pesticide doses, emergencies, weather and prices, low-confidence answers) wait in an offline queue and go to a cloud agent with document retrieval and tools as soon as the phone is online.

LMA group project · Anushka Sharma · Kiran R · Roshan K · Sai Rithvik

| Read | |
|---|---|
| Final report | [reports/final/report.pdf](reports/final/report.pdf) |
| Slides | [reports/final/slides.pdf](reports/final/slides.pdf) |
| Proposal / plan | [project_proposal.pdf](project_proposal.pdf) · [PLAN.md](PLAN.md) |
| Status and what is left | [STATUS.md](STATUS.md) · [TODO.md](TODO.md) |
| Design decisions | [docs/DECISIONS.md](docs/DECISIONS.md) · all docs: [docs/README.md](docs/README.md) |

## How a question flows through the system

```
 farmer's question (Hindi / Hinglish / English)
        │
        ▼
 ① ROUTER  src/router_gate/router.py
    keyword rules (3 languages) + TF-IDF intent classifier
        │
        ├── emergency (poisoning, snakebite, fire, shock, heatstroke)
        │       └─ show 108 / 112 / KCC 1551 immediately ─────────────────────────┐
        ├── high-risk (doses, mixing, banned products, legal, insurance)           │
        │       └─ safe interim message (+ emergency numbers) ───────────────────┐ │
        ├── live-data (weather, mandi prices, schemes)                           │ │
        │       └─ "needs internet" interim message ────────────────────────────┐│ │
        └── general                                                             ││ │
                ▼                                                               ││ │
 ② EDGE MODEL  src/edge/   Llama-3.2-3B + QLoRA, 4-bit GGUF (2 GB) on the phone ││ │
        ▼                                                                       ││ │
 ③ OFFLINE DOSE FILTER  src/router_gate/safety_filter.py                        ││ │
    any number + unit / spelled-out quantity → blocked, sent to cloud ─────────┐││ │
        ▼                                                                      │││ │
 ④ GATE  src/router_gate/gate.py                                               │││ │
    logistic regression on token logprobs, length, script, unknown words,     │││ │
    deferral flag; threshold set on the calib split                            │││ │
        ├── confident → ANSWER SHOWN OFFLINE (done)                            │││ │
        └── unsure → interim answer shown ────────────────────────────────────┐│││ │
                                                                              ▼▼▼▼ ▼
 ⑤ OFFLINE QUEUE  src/queue_sim/sim.py
    priority (emergency > high-risk > live-data > general), de-duplication,
    retry with back-off, live-data answers re-asked if stale
        ▼  (when the connection is up)
 ⑥ CLOUD AGENT  src/cloud/agent.py   (gemma-4-26b-a4b-it via the Gemini API)
    LLM-rewritten Hindi + English search query → BGE-M3 + FAISS over 383 trusted documents
    → function calling: get_weather / get_mandi_price / lookup_scheme (frozen snapshots)
    → cloud safety filter: uncited doses and banned pesticides removed
        ▼
 ANSWER with citations and an "as of" date
```

The live demo runs exactly this path on one question: `python -m src.demo "..."` (see [Demo](#demo)).

## Results (700 held-out test questions)

All numbers come from [`outputs/final/summary.json`](outputs/final/summary.json), rebuilt by `python -m src.eval.run_final`. Accuracy = share judged "correct" by the LLM judge against the Kisan Call Centre expert answer.

| Hypothesis (proposal) | Result |
|---|---|
| **H1**: on general farming questions, the hybrid reaches ≥ 90% of cloud-only accuracy while sending ≤ 50% of them to the cloud | **Met**: 95.9% of B1 with 43.6% of the 280 general questions sent to the cloud. Over all 700 questions the hybrid reaches 98.0% of B1 (no significant difference) but makes 74.6% cloud calls, because the safety rules send every high-risk and live-data question to the cloud |
| **H2**: LoRA tuning adds ≥ 10 points on the Hindi test set | **Not met**: +7.0 points (95% CI 3.0 to 10.7); two seed re-runs agree |
| **H3**: a trained gate has higher AUROC than raw token probability | **Met**: 0.87 vs 0.16 (0.77 vs 0.27 without the deferral answers) |

| System | Strict accuracy | Cloud calls / 100 |
|---|---|---|
| B1 cloud only (LLM + retrieval + tools) | 28.6% | 100 |
| A2 cloud without retrieval | 25.7% | 100 |
| A3 cloud without tools (350-question half) | 18.6% | 100 |
| B2 small base model | 5.0% | 0 |
| B3 small tuned model | 9.4% | 0 |
| **H hybrid (B3 + B1, trained gate)** | **28.0%** | **74.6** |
| R random routing at the same cloud rate | 27.0% | 74.4 |
| A1 hybrid with the base model | 26.0% | 87.4 |

Also measured:
- **Safety.** No dose is ever shown offline. On a held-out red-team set written by another model, 92.6% of risky questions go to the cloud and 95.8% of emergencies see an emergency number.
- **Retrieval.** Recall@5 rises from 0.60 to 0.92 with the LLM-rewritten query.
- **Citations and tools.** Citation faithfulness is 91%. Without tools, accuracy on live-data questions drops from 61% to 14%.
- **Queue.** On a patchy link, accuracy is 28.0% with the queue and 18.7% without it.
- **Phone size.** The 4-bit model generates 17.9 tokens/s on a laptop CPU with 4 threads, using 3.5 GB of RAM.
- **BhashaBench-Krishi (Hindi).** Base 33.6%, tuned 29.8%.
- **Judge.** A second LLM judge agrees with ours on "correct vs not correct" for 93% of 150 sampled answers.

Caveats are in the report's *Limitations* section. The main ones: the KCC references are noisy, and the judge has not yet been checked against human labels.

## Repository map

```
kisan_edge/
├── README.md  STATUS.md  TODO.md  PLAN.md  CLAUDE.md  project_proposal.pdf  requirements.txt  .env.example
├── src/
│   ├── data/          cleaning, IndicTrans2 translation, the frozen split (build_questions.py), shared helpers (common.py)
│   ├── edge/          model pilot, generation with token logprobs (generate.py), safe SFT data, QLoRA (train_qlora.py),
│   │                  BhashaBench (bhashabench.py), llama.cpp benchmark (bench_llamacpp.py), prompts
│   ├── router_gate/   router + keywords/, intent classifier, offline dose filter, gate, hybrid runner,
│   │                  red-team generators (make_redteam*.py), router/safety evaluation (eval_router.py)
│   ├── queue_sim/     offline queue and connectivity simulator (good / patchy / poor links)
│   ├── cloud/         agent loop, LLM client with cache and pacing (llm/), retrieval (rag/), tools, safety filter,
│   │                  batch runner (query.py), metrics, fault injection, corpus and snapshot fetchers
│   ├── eval/          LLM judge, scoring, judge checks, compose_scores, run_final.py (all final tables and figures)
│   ├── common/        shared record schemas, API rate limiting
│   └── demo.py        end-to-end demo on one question
├── tests/             62 unit tests, no network needed (pytest -q)
├── kaggle/            GPU/CPU jobs run from the command line (jobs/01-08) and push_code.py
├── scripts/           final_pipeline.sh (every final-phase command in order); resumable run chains
├── data/
│   ├── processed/     questions.jsonl (frozen split), gold.jsonl, router_labels.jsonl, red-team sets, SFT data
│   └── snapshots/     frozen weather forecasts (76 UP districts), district coordinates, scheme facts
├── corpus/            RAG document list (docs.jsonl) and Recall@5 queries; raw files and index are rebuilt, not committed
├── outputs/
│   ├── final/         final-phase answers, judge scores, hybrid runs, metrics and summary.json
│   └── mid/           mid-submission run files (kept so the mid report reproduces)
├── reports/
│   ├── final/         report.typ/.pdf, slides.typ/.pdf, figures/, tables/, judge_check_sheet.csv
│   └── mid/           mid-submission report
└── docs/              DECISIONS.md, DEMO.md, per-layer guides (layers/), archive/
```

## Setup

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows; on Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # add GEMINI_API_KEY (free key from Google AI Studio)
pytest -q                       # 62 tests, no network needed
```

Compute: GPU work (fine-tuning, generation, GGUF export) runs on Kaggle through the `kaggle` CLI. The laptop runs the API calls, the analysis and the llama.cpp CPU benchmark.

## Reproduce the results

Every final-phase command, in order, is in [`scripts/final_pipeline.sh`](scripts/final_pipeline.sh). The short version:

| Step | Command | Writes |
|---|---|---|
| 1. Router, red-team sets | `python -m src.router_gate.eval_router` | `outputs/router_metrics.json` |
| 2. Edge model on Kaggle | `python kaggle/push_code.py "msg"` then `kaggle kernels push -p kaggle/jobs/06_edge_full --accelerator NvidiaTeslaT4` (and jobs 07, 08) | B2/B3 answers with logprobs, BhashaBench, seed re-runs, 4-bit GGUF |
| 3. Cloud runs | `python -m src.cloud.query --questions data/processed/questions.jsonl --split test --run B1 --as-of 2026-10-30 --workers 8 --out outputs/final/cloud_B1.jsonl` (A2 likewise; A3 with `--ids data/processed/test_half_ids.txt`) | `outputs/final/cloud_*.jsonl` |
| 4. Judging | `bash scripts/judge_chain.sh B3 B2 B3_calib B3_dev B1 A2 A3 B3_s1 B3_s2` | `outputs/final/scores_*.jsonl` |
| 5. Cloud metrics | `python -m src.cloud.rag.recall_check --rewrite --out outputs/final/rag_recall.json`, `python -m src.cloud.metrics --runs B1,A2,A3 --faithfulness 60`, `python -m src.cloud.fault_injection --n 20` | `rag_recall.json`, `cloud_metrics.json`, `fault_injection.json` |
| 6. Everything else | `python -m src.eval.run_final` | gate, hybrids, queue traces, H1-H3: `outputs/final/summary.json`, `reports/final/{tables,figures}` |
| 7. Report and slides | `python -c "import typst; typst.compile('reports/final/report.typ', output='reports/final/report.pdf', root='.')"` (same for `slides.typ`) | PDFs |

Steps 1, 6 and 7 need no API key and run in minutes from the committed outputs. Model and judge calls are cached (`cache/gemini.sqlite`, `outputs/cache/judge_cache.jsonl`), so re-running a finished step costs nothing, and every batch run resumes after an interruption. The free Gemini-API tier allows Gemma 4 about 30 requests and 16,000 input tokens per minute per model. The cloud agent (`gemma-4-26b-a4b-it`) and the judge (`gemma-4-31b-it`) are different models, so they have separate quotas. From scratch, the cloud runs take about 10 hours and the judging about 8.

## Demo

```bash
# needs the llama.cpp CPU build in tools_ext/llamacpp/bin and the GGUF from Kaggle job 08
python -m src.demo "gehu ki buvai ka sahi samay kya hai" --district Kheri                       # answered on the phone
python -m src.demo "bachche ne galti se keetnashak pee liya hai" --offline                      # emergency numbers at once
python -m src.demo "Bareilly mein agle 3 din mausam kaisa rahega" --district Bareilly --offline   # interim answer, queued
python -m src.demo --flush                                                                      # back online: queue answered by the cloud
```
Each step prints what the router, edge model, dose filter, gate and cloud agent decided, with timings. Talk track: [docs/DEMO.md](docs/DEMO.md).

## Data

- **Questions.** Kisan Call Centre records from Uttar Pradesh for wheat, paddy, mustard and sugarcane, plus KisanVaani English Q-A. Raw data is downloaded by `python -m src.data.download` from [Omegaindebt/Kisan_Call_Centre_Transcripts](https://huggingface.co/datasets/Omegaindebt/Kisan_Call_Centre_Transcripts) and [KisanVaani/agriculture-qa-english-only](https://huggingface.co/datasets/KisanVaani/agriculture-qa-english-only). The split (`data/processed/questions.jsonl`) is frozen: train only on `split == "train"`, set thresholds on `calib`, report on `test`.
- **Processed data and all model outputs** are on the Hugging Face dataset [kisan-edge/kisan-edge-data](https://huggingface.co/datasets/kisan-edge/kisan-edge-data). Load them with `huggingface_hub.snapshot_download("kisan-edge/kisan-edge-data", repo_type="dataset")`.
- **External benchmark.** BhashaBench-Krishi (Hindi) comes from the ungated [bharatgenai/BhashaBench-Multi](https://huggingface.co/datasets/bharatgenai/BhashaBench-Multi).
- **Privacy.** Phone numbers and personal names are removed during cleaning. Never commit `.env` or API keys.
