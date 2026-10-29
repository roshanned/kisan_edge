# Decisions made while building Kiran's layer

Each decision: what was picked, why, and how to change it. Those marked **CONFIRM** were made without anyone asking
and should be confirmed by Kiran or Anushka.

| # | Decision | Why | To change |
|---|---|---|---|
| D1 | Branch `kiran/gate` cut from `anushka/data`, not `main` | `main` only has PLAN.md; the frozen split and `common.py` are on Anushka's branch. PLAN.md names the branch `kiran/gate` | Rebase onto `main` once Anushka's PR merges |
| D2 | **Router labels** = Anushka's first-pass `category`, upgraded (never downgraded) to `emergency` / `high_risk` when our keyword rules fire. 143 upgrades. Result: high_risk 7,703, live_data 7,063, general 3,567, emergency 2 | PLAN.md says "map KCC QueryType". That mapping already exists in `common.category_for`; re-doing it would diverge from Anushka's split. **CONFIRM** | `make_labels.py` |
| D3 | **Emergency is rules only.** The classifier is trained on the labels but has only 2 emergency rows, so it cannot predict it | No KCC emergency data. The rules are the guarantee | Add real emergency Qs to the red-team set and train on them in Phase 2 |
| D4 | **Everything that is not `general` goes to the cloud, always.** The gate only sees `general` questions. Also, if the classifier gives P(high_risk)+P(emergency) >= 0.35, the question is treated as risky (`CLF_SAFETY_MASS`) | Safety first: a wrong dose is worse than an extra cloud call. **CONFIRM, and see the H1 problem below** | `CLF_SAFETY_MASS` in `router.py`; `--no-clf` in `hybrid.py` runs rules-only |
| D5 | **Offline filter blocks, then asks the cloud.** A blocked edge answer is replaced by a deferral message and the question is queued for the cloud. It over-blocks on purpose ("40 kg seed" is blocked) | Open question 4 in CLAUDE.md. A deferral keeps the farmer informed; silent dropping would not | `safety_filter.apply` / `DEFERRAL` text |
| D6 | **Gate label:** the edge answer is "good" only if the judge says `correct` (not `partly correct`) | Open question 2. Strict is the safer default | `gate.py --positive correct,partly correct` |
| D7 | **Hybrid output = PLAN.md §5 router format + extra fields** (`route_reason`, `filter_blocked`, `interim_answer`, `stale_reasked`). `final_answer` is the **eventual** answer (cloud answer if delivered, else the interim message) | Anushka's scorer reads `final_answer`; extra fields do not break it. Offline usefulness can be scored on `interim_answer` | `hybrid.py` |
| D8 | **Gate threshold = target cloud rate** (default 50% of `general` Qs) via a quantile of confidence. Phase 1 has only gold rows (no calib), so the cut is taken from the eval rows themselves and the metrics file says `phase1_no_calib: true` | H1 is stated as ≤ 50% cloud calls. A calib-tuned threshold needs Roshan's calib outputs (Phase 2) | `--target-rate` |
| D9 | **Queue simulation is discrete (1 tick = 1 minute)**; one question arrives per tick; link up/down is a 2-state Markov chain; at most 3 sends per tick; back-off 2^tries (max 64); 6 tries then give up; trace params in `TRACES` (good 98% / patchy 70% / poor 40% send success) | PLAN.md gives no numbers. These are invented to be plausible. **CONFIRM, or replace with measured numbers** | `TRACES`, `CAP`, `MAX_TRIES` in `sim.py` |
| D10 | **Stale handling:** a live_data answer that waited longer than 60 ticks counts as stale; we then re-ask once (one extra send) | PLAN.md says "stale re-ask for weather and prices" with no TTL | `LIVE_TTL` |
| D11 | **Duplicate-send** = a successful send for a key already delivered. With dedup on it is 0 by construction; the test split has no duplicate questions (dedup was done in cleaning), so the real-data rate is 0 | Honest: the metric only shows something on synthetic duplicates (tested) | n/a |
| D12 | Red-team set is **51 Qs drafted by Claude**: 36 high_risk (dose 16, mixing 8, legal 6, insurance 6) and 15 emergency (poison 12, snake 3); 18 Devanagari / 17 Hinglish / 16 English | PLAN.md says hand-written. Marked `human_reviewed: false` | MANUAL_TODO 1 |
| D13 | Keyword lists were also drafted by Claude, from `common.py` words plus domain knowledge. Insurance **claims/complaints** are high_risk; plain "bima/scheme" questions stay live_data (matches Anushka's labels) | Insurance claims involve money and legal rights; scheme lookups are factual | Edit the `.txt` files |
| D14 | The classifier is TF-IDF char n-grams + logistic regression, `class_weight=balanced`, trained on train only. Dev accuracy 0.82 | Small, fast, no GPU, no new dependency beyond scikit-learn | `intent_clf.py` |
| D15 | Gate v2 features: mean/min logprob, log token count, log answer length, script flags, crop known, category flags. Fit on dev, threshold on calib, report on test | PLAN.md §4 Kiran step 2. "Unknown crop/pest words" is implemented as "crop is None" only | `gate.features` |
| D16 | `models/` stays gitignored; `data/processed/router_labels.jsonl`, `redteam.jsonl`, `filter_probe.jsonl`, `outputs/router.jsonl`, `outputs/hybrid_*.jsonl` are committed | Small, and needed to reproduce the report (PLAN.md git rules) | `.gitignore` |

## Problem for the team: H1 and the forced-cloud share
H1 asks for hybrid accuracy ≥ 90% of B1 with ≤ 50% cloud calls. With D4, on the 200 gold questions (same category mix as
the test split; the edge confidences were mock, but the forced share does not depend on them) **66% of questions go to the cloud with rules only, and 85% with the classifier** before the gate does
anything. The 40% high_risk share comes from Anushka's split quota; "high_risk" in KCC mostly means *Plant Protection /
Fertilizer* QueryType, not "contains a dose".
Options: (a) accept and report the real cloud rate honestly (PLAN.md risks table already says to "report the trade-off
honestly"); (b) narrow high_risk to dose / mixing / legal / claim / emergency keywords only (rules-only gives 66%); (c)
report H1 on `general` questions only as a secondary number. Not decided: see MANUAL_TODO 4.
