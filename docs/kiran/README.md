# Router, gate, queue: developer guide (Kiran's layer)

Branch `kiran/gate`. Everything here was built by Claude for Anushka while Kiran's work was missing. **Read
[DECISIONS.md](DECISIONS.md) (what was chosen and why) and [MANUAL_TODO.md](MANUAL_TODO.md) (what only a human can do).**

## How a question flows

```
question ──> Router ──────────────> emergency / high_risk / live_data ──> ALWAYS cloud (queued if offline)
             rules, then intent clf
                         └────────> general ──> edge answer ──> safety filter ──blocked (dose)──> cloud
                                                     │
                                                     └─> Gate: mean_logprob >= cut ? keep offline : cloud
cloud side: Queue (priority, dedup, retry+back-off, dated cache, stale re-ask) over a simulated link (good/patchy/poor)
```
While a cloud answer is pending the farmer sees an **interim** message: emergency numbers (108 / 112 / KCC 1551) for
emergencies, an expert-deferral for high_risk, "needs internet" for live_data, the (filtered) edge answer for general.

## Files

| File | What it does |
|---|---|
| `src/common/schemas.py` | Field lists for PLAN.md §5 formats + `check(kind,row)` validator |
| `src/router_gate/keywords/{emergency,high_risk,live_data}.txt` | Hand-written term lists, Devanagari + Hinglish + English. One term per line, `#` comments, `$` = require right word boundary |
| `src/router_gate/router.py` | `Router.route(q)` -> `{category, reason}`. `python -m src.router_gate.router` writes `outputs/router.jsonl` (test split) |
| `src/router_gate/make_labels.py` | Builds `data/processed/router_labels.jsonl` (labels for the classifier) |
| `src/router_gate/intent_clf.py` | TF-IDF char n-grams + LogisticRegression, train split only -> `models/intent_clf.pkl` (gitignored) |
| `src/router_gate/safety_filter.py` | Offline output filter: blocks number+unit, spelled-out number+unit, spoken measures, Devanagari digits |
| `src/router_gate/make_redteam.py` | Writes `redteam.jsonl` (51 Qs, **unreviewed**) and `filter_probe.jsonl` (33 probes) |
| `src/router_gate/eval_router.py` | High-risk recall, emergency escalation, filter miss rate -> `outputs/router_metrics.json` |
| `src/router_gate/gate.py` | Gate v1 (token prob) + v2 (LR classifier): AUROC, AURC, ECE, false-keep, unnecessary-send, risk-coverage plot |
| `src/router_gate/hybrid.py` | Full hybrid, **R**, **A1**, **A4** over precomputed edge and cloud outputs (no model calls) |
| `src/queue_sim/sim.py` | Connectivity traces + queue. `python -m src.queue_sim.sim` -> `outputs/queue_metrics.json` |
| `tests/test_router_gate.py`, `tests/test_queue_sim.py` | 31 tests, all pass (`pytest tests -q`) |

## Run order (clean clone; needs `data/processed/questions.jsonl`)

```bash
pip install -r requirements.txt
python -m src.router_gate.make_redteam              # red-team + filter probes
python -m src.router_gate.make_labels               # router_labels.jsonl
python -m src.router_gate.intent_clf                # trains models/intent_clf.pkl (~10 s)
python -m src.router_gate.eval_router               # outputs/router_metrics.json
python -m src.router_gate.router                    # outputs/router.jsonl
python -m src.queue_sim.sim                         # outputs/queue_metrics.json
pytest tests -q
```
When the real outputs and judge scores exist:
```bash
# 1. gate quality (needs Anushka's outputs/scores_B3.jsonl, Roshan's edge file)
python -m src.router_gate.gate --edge outputs/edge_tuned.jsonl --scores outputs/scores_B3.jsonl
# 2. runs (each writes <out>.jsonl and <out>.summary.json; then Anushka scores them like any other run)
python -m src.router_gate.hybrid --edge outputs/edge_tuned.jsonl --cloud outputs/cloud_B1.jsonl --splits gold --out outputs/hybrid_B3_B1.jsonl             # full hybrid
python -m src.router_gate.hybrid --edge outputs/edge_base.jsonl  --cloud outputs/cloud_B1.jsonl --splits gold --out outputs/hybrid_A1.jsonl                 # A1
python -m src.router_gate.hybrid --edge outputs/edge_tuned.jsonl --cloud outputs/cloud_B1.jsonl --splits gold --mode random --out outputs/hybrid_R.jsonl  # R
python -m src.router_gate.hybrid --edge outputs/edge_tuned.jsonl --cloud outputs/cloud_B1.jsonl --splits gold --trace patchy --no-queue --out outputs/hybrid_A4.jsonl  # A4
```
A2 and A3 use the cloud ablation outputs: pass `--cloud outputs/cloud_A2.jsonl` / `cloud_A3.jsonl`.

## Results so far (real data, no model outputs needed)

From `outputs/router_metrics.json` and `outputs/queue_metrics.json`. **Read the caveats.**

| Metric | Value | Caveat |
|---|---|---|
| High-risk recall on the 51 red-team Qs | 1.00 (rules and rules+clf) | Red-team and keywords were written by the same author: optimistic. Needs independent Qs (MANUAL_TODO 2) |
| Emergency escalation (red-team emergency Qs -> `emergency`) | 1.00 | same |
| Router accuracy vs first-pass labels, test | rules only 0.55; rules+clf **0.80** (hi/deva 0.89, hi/latn 0.73, en 0.74) | Labels are noisy KCC-QueryType guesses |
| High-risk recall vs labels, test | rules only 0.07; rules+clf **0.90** | Rules cover danger, not the KCC "Plant Protection" label |
| Offline filter miss rate / false-block rate | 0.00 / 0.00 (22 dose, 11 safe probes) | Probes are small and written alongside the filter. Re-test on real edge outputs |
| Queue, good / patchy / poor link: delivery | 1.00 / 1.00 / 0.67 (A4 no-queue: 0.98 / 0.58 / 0.14) | Cloud answers are simulated as coin flips; poor link is overloaded (1 question per minute) |

**Not available yet (needs other people's outputs): AUROC / AURC / ECE of the gate, R, A1, H1, H3, and every accuracy number.**

## Known limitations
- **H1 may be unreachable.** Always-to-cloud routes (live_data 20% and high_risk 40% of the test split, by Anushka's quotas)
  already put ~60%+ of questions on the cloud before the gate acts. See DECISIONS D4 and MANUAL_TODO 4.
- Only 2 `emergency` rows exist in KCC, so the classifier cannot learn it; emergency is rules only.
- The queue uses precomputed cloud answers. Real latency, quota limits and failures are not modelled beyond a coin flip.
- Time-to-answer is in simulated ticks (1 tick = 1 minute), not wall-clock.
