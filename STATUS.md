# Project status (Oct 30, 2026, mid-submission day)

`main` has everything. **What is left for today is in [TODO.md](TODO.md).** Details per area: `docs/kiran/` (router, queue), `docs/cloud/` (cloud side).

## Done

| Part | Done |
|---|---|
| **Data** | Cleaned and split once (700 test, 600 calib, 600 dev, 16,435 train). 200 gold candidates; an AI pre-check dropped 42 bad ones, **158 remain**. Judge, scoring, tables, chart |
| **Small model (Roshan)** | Llama-3.2-3B chosen from a 100-question pilot; fine-tuned; **B2 (base) and B3 (tuned) run on all 200 gold questions** |
| **Cloud** | Agent with weather, market-price and scheme tools, safety filter, resumable runner. **A2 (cloud, tools, no document search) run on 200 questions** with `gemini-3.5-flash-lite` |
| **Router, gate, queue** | Router, dose filter, gate, queue simulator. **Combined system, A1 and R run and scored** |
| **Report** | `reports/mid/report.pdf` written with tables and a chart, no empty sections |
| **Hugging Face dataset** | Public at [kisan-edge/kisan-edge-data](https://huggingface.co/datasets/kisan-edge/kisan-edge-data). **Out of date**: last updated Oct 25, so it lacks the split, gold set, model answers, scores and weather files |

## Results (158 gold questions, AI judge; share of answers judged fully correct)

| Run | Correct | Run | Correct |
|---|---|---|---|
| B2 small base | 1.9% | A1 combined, base model | 39.9% |
| B3 small tuned | 10.1% | R combined, random routing | 40.5% |
| A2 cloud (tools) | 46.8% | Combined system | 43.0% |

- **Tuning (H2):** +8.2 points overall, +5.0 on Hindi. Target was +10 on Hindi. Not met.
- **Combined system (H1):** 92% of the cloud score (target 90%), but 83 of 100 questions go to the cloud (target 50 or fewer). Half met. The fixed safety rules cause this, not the gate.
- **Gate:** the small model's confidence does not predict correct answers (AUROC 0.18, worse than chance). The combined system (43.0%) is barely better than random routing (40.5%).

## Not done
- **B1 and A3** (need document search): no trusted documents collected yet. Sites cannot be scraped; must be downloaded by hand.
- **Market prices:** need a free data.gov.in key.
- **Human checks:** 0 of 158 gold questions human-checked (only AI pre-checked); AI judge not yet compared with human labels.
- **Unverified facts:** scheme details, banned-pesticide list, and the 51 test questions and word lists Claude drafted.
- Trained gate on dev/calib data, 4-bit export and phone-speed test, fault tests.

## Final submission (Nov 15)
Full 700-question runs of everything, fix the gate, collect documents and run B1/A3, judge check on 100 questions, final report. Code freeze Nov 14.
