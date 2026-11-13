---
license: cc0-1.0
language: [hi, en]
pretty_name: Kisan-Edge data and results
---

# Kisan-Edge: data and results

Data, model outputs and judge scores for Kisan-Edge (LMA group project): a LoRA-tuned 3B model answers Uttar Pradesh farmers' questions on the phone, and a router + trained confidence gate + offline queue send the rest to a cloud agent with retrieval and tools.
Code, report and slides: https://github.com/roshanned/kisan_edge (branch `main`). Every number in the final report is in `outputs/final/summary.json`.

Final results (700 test questions): cloud agent B1 28.6% strict accuracy; hybrid 28.0% at 74.6% cloud calls; on general questions the hybrid keeps 95.9% of B1 with 43.6% cloud calls (H1 met); fine-tuning +7.0 points on Hindi (H2 not met); trained gate AUROC 0.87 vs 0.16 for token probability (H3 met).

All `.jsonl` files use the shared formats in the repo's PLAN.md section 5.

## processed/
| File | What it is |
|---|---|
| `questions.jsonl` | The frozen split: train 16,435 / dev 600 / calib 600 / test 700 (Hindi, Hinglish, English; wheat, paddy, mustard, sugarcane) |
| `gold.jsonl`, `gold_candidates.jsonl` | 158-question gold subset of test (references corrected by an LLM pre-check) and the 200 candidates |
| `router_labels.jsonl` | Router categories (general / live_data / high_risk / emergency) |
| `redteam.jsonl`, `redteam_v2.jsonl`, `redteam_v3.jsonl` | Safety red-team sets: v1 written with the keyword lists; v2 and v3 held out, written by other LLMs, with benign controls |
| `filter_probe.jsonl` | Dose / safe probes for the offline dose filter |
| `test_half_ids.txt` | Stratified 350-question half of test used for the A3 ablation |
| `sft_train_split.jsonl`, `sft_val_split.jsonl` | QLoRA training data from the frozen train split (4,641 / val), used for B3 |
| `kcc_*.jsonl`, `kisanvaani_en.jsonl`, `pilot*`, `sft_train.jsonl`, `sft_val.jsonl` | Earlier cleaned inputs and the pilot SFT set (before the split) |

## outputs/final/ (final phase)
| Files | What they are |
|---|---|
| `edge_base_full.jsonl`, `edge_tuned_full.jsonl` | B2 / B3 answers on test + calib + dev with token logprobs |
| `edge_tuned_s1.jsonl`, `edge_tuned_s2.jsonl` | QLoRA seed re-runs (test) |
| `cloud_B1.jsonl`, `cloud_A2.jsonl`, `cloud_A3.jsonl` | Cloud agent: RAG + tools; no RAG; no tools (A3 on the 350-question half). Citations, tool calls, safety events |
| `scores_*.jsonl` | Judge labels (gemma-4-31b-it): correct / partly_correct / wrong, deferred flag |
| `hybrid_*.jsonl` (+ `.summary.json`) | Hybrid runs: H, H_tok, R, A1, H_A2, H_A3, router/policy trade-off (`TO_*`), queue traces (`Q_*`, `_A4` = no queue) |
| `summary.json` | Every reported number |
| `cloud_metrics.json`, `rag_recall.json`, `fault_injection.json(l)`, `judge_vs_judge.json`, `llamacpp_*`, `bhashabench_*.jsonl`, `router_metrics_keywords_v1.json` | Cloud, retrieval, robustness, judge-agreement, phone-speed, benchmark and router metrics |

## Other folders
- `outputs/mid/`: mid-submission (Oct 30) runs on the gold set; `outputs/pilot_*`: the model-choice pilot.
- `corpus/`: the 383 RAG documents (source, date, language, URL) and the 60 Recall@5 queries.
- `snapshots/`: frozen weather forecasts for 76 UP districts (2026-10-30), district coordinates, scheme facts (unverified).
- `reports/`: final report and slides (PDF).

Sources: KCC 1M sample `Omegaindebt/Kisan_Call_Centre_Transcripts` (data.gov.in), `KisanVaani/agriculture-qa-english-only`. Phone numbers are replaced with `[PHONE]`.

## Load
```python
from huggingface_hub import snapshot_download
path = snapshot_download("kisan-edge/kisan-edge-data", repo_type="dataset")
```
