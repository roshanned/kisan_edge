# Kisan-Edge: Project Plan and Work Split

**Team:** Anushka Sharma · Kiran R · Roshan K · Sai Rithvik
**Course:** LMA group project

| Milestone | Date | What is due |
|---|---|---|
| Plan locked | Sat, Oct 24 | This document, repo skeleton, shared data formats |
| **Mid-submission** | **Fri, Oct 30** | Progress, datasets, baselines, ablations, results, challenges, mitigations, final timeline, **updated GitHub with all code** |
| **Final submission** | **Sun, Nov 15** | Everything in the proposal, evaluated on the full test set. **No extensions.** |
| Evaluations | Nov 16 – 19 | Live presentation and demo |

> The TAs said: *"Since the final submission is just 15 days after the mid-submission, expectations will be high."* So the mid-submission must have **real numbers**, not just setup.

---

## 1. Who owns what

Each person owns one layer of the system. The layers talk to each other only through the files listed in [Section 5](#5-shared-interfaces-agree-on-day-1). That's what lets everyone work in parallel.

| Person | Workstream | Owns (proposal sections) | Baselines and ablations they run |
|---|---|---|---|
| **Anushka Sharma** | Data and evaluation | §9 main KCC dataset, the single split script, §11 metrics, gold set, judging, final report | Scoring for all runs |
| **Roshan K** | Edge model | §7.1(1) edge model, §12 fine-tuning, GGUF, llama.cpp | **B2**, **B3** (H2) |
| **Sai Rithvik** | Cloud side | §7.1(5) cloud agent, RAG corpus, tools, cloud safety filter | **B1**, **A2**, **A3** |
| **Kiran R** | Router, gate, queue and integration | §7.1(2–4), §7.3 gate, red-team set, router labels, connectivity simulator, offline safety filter, repo owner | **R**, **A1**, **A4**, full hybrid (H1, H3) |

**Hindi review:** gold-set checking and Hindi/Hinglish rewrites (§13) need Hindi-fluent reviewers. Gold-set checking is split 50 Qs per person (Section 2.3); if someone isn't comfortable reading Hindi, a Hindi-fluent teammate takes their batch. Swap any role if that suits the team better. Just update this table.

---

## 2. DATA FIRST (everyone, before anything else)

> **Nothing can be trained, tested or scored without data.** So for the first ~2 days (target: **Oct 24 – Oct 26**), all four people work on data at the same time. Each person collects the data **their own layer** needs, so they also understand it best.

### 2.1 The three rules everyone follows

1. **One format.** Every question file uses the format in Section 5 (`questions.jsonl`). Agree on it before anyone writes cleaning code.
2. **One set of cleaning rules:**
   - Keep only the 4 crops: wheat, paddy, mustard, sugarcane
   - Remove personal names and phone numbers
   - Remove duplicate questions
   - Tag the script: `deva` (Hindi in Devanagari), `latn` Hindi (Hinglish), `latn` English
   - Tag the category: `general`, `live_data`, `high_risk`, `emergency`
3. **One split, made once, then frozen.** Anushka's split script makes train / dev / calib / test **one time** over everyone's cleaned data. After that the test set never changes, and **nobody trains on anything until the split exists**. Otherwise test questions can leak into training and the H2 result becomes meaningless.

### 2.2 Who collects what

| Person | Dataset | Source | Output file | What it's used for |
|---|---|---|---|---|
| **Anushka** | KCC UP 2024-25 (Hindi, **main dataset**) | data.gov.in KCC, filtered to Uttar Pradesh | `data/processed/kcc_hi.jsonl` | Training, testing, gold set |
| **Anushka** | The final splits | Her split script over all cleaned files | `data/processed/questions.jsonl` | Everyone |
| **Roshan** | KCC 2014-19 sample (Hinglish) | 1-million-row public KCC sample, UP rows | `data/processed/kcc_hinglish.jsonl` | Hinglish training and test |
| **Roshan** | KisanVaani (English) | KisanVaani Q-A dataset (~22.6k pairs) | `data/processed/kisanvaani_en.jsonl` | English training and test |
| **Roshan** | Hindi translations of the English KCC summaries | IndicTrans2 (run locally) | Added into `kcc_hi.jsonl` | Training |
| **Sai Rithvik** | RAG corpus (first 50–100 docs) | UP Agri Dept, ICAR, CRIDA, CIB&RC, PM-KISAN, PMFBY, myScheme | `corpus/docs.jsonl` (source, date, language per doc) | Cloud answers with citations |
| **Sai Rithvik** | Saved live data | Agmarknet mandi prices, Open-Meteo weather | `data/snapshots/` | Fair, repeatable tool evaluation |
| **Kiran** | Red-team set (~50 Qs) | Written by hand: doses, mixing, legal, insurance, poisoning; in Hindi, Hinglish and English | `data/processed/redteam.jsonl` | Safety metrics |
| **Kiran** | Router labels | Map KCC QueryType → general / live-data / high-risk / emergency | `data/processed/router_labels.jsonl` | Router intent classifier |
| **Kiran** | Keyword lists | Written by hand, for each category, in 3 languages | `src/router_gate/keywords/` | Rule router |
| **All four** | **Gold test set (~200 Qs)** | Picked from the frozen test split; **50 Qs each**, hand-checked | `data/processed/gold.jsonl` | Every Phase 1 result |

### 2.3 Order of the data sprint

1. **Agree on the format and cleaning rules** (Anushka shares them, everyone reads them).
2. **Everyone downloads and cleans their own data, in parallel.**
3. **Roshan sends** the cleaned Hinglish and English files to Anushka.
4. **Anushka runs the split script once.** The test set is now frozen.
5. **Anushka picks ~200 gold candidates** from the test split and gives each person a batch of 50.
6. **Everyone hand-checks their 50:** is the question clear, is the reference answer correct, are the language and category tags right? Fix or drop bad ones. If you're not comfortable reading Hindi, swap batches with a Hindi-fluent teammate.
7. **Anushka merges the batches** into `gold.jsonl`. Data is done; everyone moves on to their own layer.

---

## 3. Phase 1: Mid-submission (Oct 24 → Oct 30)

Goal: every layer works on the **gold set (~200 Qs)** and produces real numbers for B1, B2, B3, R, A1 and A2.

Each person's list is in order: **do Step 1 first, then Step 2, and so on.**

### Anushka Sharma: Data and evaluation

**Step 1: Data (first)**
1. Write the cleaning rules and labelling rules and share them with everyone
2. Download and clean KCC UP 2024-25 (the main Hindi dataset)
3. Publish a **50-question seed file** in the shared format right away, so others can start building
4. Write the split script; run it **once** over your file plus Roshan's files; freeze the test set
5. Pick ~200 gold candidates from the test split and send each person their 50
6. Hand-check your own 50, then merge everyone's into `gold.jsonl`
7. Send the frozen train split to Roshan

**Step 2: Evaluation harness**
8. Build the scoring script: correct / partly correct / wrong, using an LLM judge
9. Hand-check a sample of the judge's labels to see whether it can be trusted
10. Make it report results per language and script (Hindi, Hinglish, English)

**Step 3: Results and report**
11. Score every output file (B1, B2, B3, R, A1, A2)
12. Make the tables and plots
13. Put together and submit the mid-submission report (outline in 3.1)

### Roshan K: Edge model

**Step 1: Data (first)**
1. Download and clean the KCC 2014-19 sample (Hinglish) and KisanVaani (English) using the shared rules
2. Translate the English KCC question summaries to Hindi with IndicTrans2
3. Send the cleaned files to Anushka for the split
4. Hand-check your 50 gold questions

**Step 2: Setup and model choice (can start in parallel with Step 1)**
5. Set up Kaggle/Colab
6. Write a batch generation script that saves each answer with its **token logprobs** (mean, min), token count and latency
7. Run the 100-question Hindi pilot: Qwen3-1.7B vs Llama-3.2-1B vs Llama-3.2-3B
8. **Pick the edge model**

**Step 3: Baseline and fine-tuning**
9. **B2:** run the base model on the gold set and send the outputs to Kiran
10. Build the QLoRA training set from the **frozen train split only** (short answers, native Hindi, safe deferral)
11. **Start QLoRA run #1** as early as possible (Kaggle allows ~30 GPU-hours a week)
12. **B3:** run the tuned model on the gold set and send the outputs to Kiran

**Step 4: Results**
13. Report the first H2 number (tuned vs base)
14. Write the edge-model section of the report, noting any issues (Hindi quality, VRAM, training time)

### Sai Rithvik: Cloud side

**Step 1: Data (first)**
1. Collect the first ~50–100 trusted RAG documents (UP Agri Dept, ICAR, CRIDA, CIB&RC, PM-KISAN, PMFBY, myScheme), recording source, date and language for each
2. Save Agmarknet mandi-price and weather data, so evaluation doesn't depend on live APIs
3. Hand-check your 50 gold questions

**Step 2: Retrieval**
4. Chunk the documents (keep source, date and language on every chunk)
5. Build the BGE-M3 + FAISS index
6. Check Recall@5 on ~30 Hindi queries

**Step 3: Cloud agent**
7. Get the Gemini API key; write a client wrapper that **caches every response** so no question is sent twice
8. Build the agent loop with function calling and the Open-Meteo weather tool; answers come with citations and an "as of" date
9. Debug on 20 questions

**Step 4: Runs (start as early as possible; free-tier quota is the bottleneck)**
10. **B1:** cloud-only run on the gold set
11. **A2:** the same agent with retrieval turned off
12. Decide what B4 means (see Section 9)
13. Write the cloud section of the report

### Kiran R: Router, gate, queue and integration

**Step 1: Repo and data (first)**
1. Set up the repo skeleton, README, `.gitignore`, shared schemas and a **mock-data generator** so everyone can build before real data arrives
2. Write the red-team set (~50 high-risk and emergency Qs) in Hindi, Hinglish and English
3. Map KCC QueryType values to router categories to make the router labels
4. Write keyword lists for each category in all 3 languages
5. Hand-check your 50 gold questions

**Step 2: Router and safety filter**
6. Rule router: keyword lists plus emergency rules (108 / 112 / KCC 1551)
7. Train the small intent classifier on the router labels (train split only)
8. Offline output filter: blocks number + unit pairs, Devanagari digits, Hindi/Hinglish unit words and spelled-out numbers
9. Report high-risk routing recall and filter miss rate on the red-team set

**Step 3: Gate (once Roshan's B2/B3 outputs arrive)**
10. Gate v1: token-probability score; AUROC and a risk-coverage curve
11. **R:** random routing at the same cloud-call rate
12. **A1:** hybrid using the base model (uses B2 + B1 outputs, no new model calls)

**Step 4: Queue and integration**
13. Queue and connectivity simulator skeleton (data structures, good / patchy / poor traces, unit tests)
14. Run the hybrid end to end on 20 Qs
15. Write the router and gate section of the report; clean the repo and **tag `mid-submission` on GitHub**

### 3.1 Mid-submission report outline (Anushka edits; everyone writes their own section)

1. **Progress summary:** what's built vs the architecture in Figure 1
2. **Datasets:** sources, counts per crop, language and script, splits, cleaning steps, known limitations
3. **Baseline experiments:** B1, B2, B3 on the gold set, with accuracy per language
4. **Ablations:** A1, A2 (and R as a sanity check on the gate)
5. **Results:** tables plus a risk-coverage plot plus the first H2 result
6. **Challenges faced** (e.g. noisy KCC labels, API quota, Hindi output quality, GPU hours)
7. **Mitigation plans** (from §13 of the proposal, updated with what actually happened)
8. **Timeline to final:** Section 4 of this document
9. **GitHub link** and a short repo guide

---

## 4. Phase 2: Final submission (Oct 31 → Nov 15)

Goal: run everything on the **full test set (~700 Qs)**, complete every component, and get final verdicts on H1, H2 and H3. Diwali falls in this period, so get the heavy runs done early and keep Nov 14–15 as buffer.

Again, each list is in order: **Step 1 first, then Step 2, and so on.**

### Anushka Sharma: Data and evaluation

**Step 1: Data (first)**
1. Grow the test set to the full ~700 Qs, with the calib and dev splits (~2,000 Qs in total), using the same frozen split
2. Add evaluation loaders for BhashaBench-Krishi Hindi (2,757 Qs) and the Indic-KCC-Agri-Advisory benchmark

**Step 2: Judge check**
3. Check LLM judge vs human agreement on 100 Qs and report it

**Step 3: Results and report**
4. Score every run; tables per language and script
5. Overall metrics: accuracy, cloud calls per 100 Qs, offline usefulness
6. Write and submit the final report

### Roshan K: Edge model

**Step 1: Training**
1. Main QLoRA run plus 2 re-runs (different seeds or hyperparameters)

**Step 2: Full runs**
2. Run B2 and B3 on the full test, calib and dev sets (~2,000 Qs × 2 models), with logprobs, and send them to Kiran

**Step 3: Phone-size checks**
3. Export the tuned model as a 4-bit GGUF
4. llama.cpp speed and memory on a laptop CPU (tokens/s, RAM, model size)

**Step 4: Results**
5. BhashaBench-Krishi Hindi accuracy, base vs tuned
6. Reply-language match rate
7. **Final H2 verdict** (does tuning add ≥ 10 points on the Hindi test set?)

### Sai Rithvik: Cloud side

**Step 1: Data (first)**
1. Complete the corpus (200–400 docs: UP Agri Dept, ICAR-CRIDA, CIB&RC, fertilizer recommendations, variety notes, PM-KISAN, PMFBY, myScheme) and rebuild the index

**Step 2: Tools and safety**
2. Add the Agmarknet mandi-price tool (with frozen snapshots) and the scheme-lookup tool
3. Cloud safety filter: doses only from cited sources, banned products refused

**Step 3: Full runs**
4. **B1**, **A2** and **A3** on the full test set

**Step 4: Metrics**
5. RAG: Recall@5, citation faithfulness, correct-abstain rate
6. Tools: tool-choice accuracy, argument validity (Hindi district and mandi names map to the right IDs), unapproved-action rate
7. Fault injection (timeouts, empty results, 5xx errors) and recovery rate

### Kiran R: Router, gate, queue and integration

**Step 1: Data (first)**
1. Extend the red-team set

**Step 2: Gate**
2. Gate classifier (logistic regression or small MLP) on logprob features plus question type, answer length, script and unknown crop/pest words
3. Threshold sweep on the calib split; risk-coverage curves per language
4. Gate metrics: AUROC, AURC, ECE, false-keep rate, unnecessary-send rate, cloud-call rate, token prob vs classifier (**H3**)

**Step 3: Queue and simulator**
5. Complete the queue: priority, dedup, retry with back-off, stale re-ask for weather and prices, cache with dates
6. Connectivity simulator with good / patchy / poor traces

**Step 4: Full system runs**
7. Full hybrid run plus **R**, **A1** and **A4** on the full set
8. Queue metrics: delivery rate, p50/p90 time-to-answer, stale-answer rate, duplicate-send rate
9. Safety metrics: high-risk recall, offline dose rate, filter miss rate, emergency escalation rate
10. **Final H1 verdict**
11. README with reproduction steps

### 4.1 Final steps (everyone)
- Code freeze on Nov 14; everyone re-runs their scripts from a clean clone to check the results reproduce
- Slides and demo script; submit on **Nov 15**
- Nov 16 – 19: evaluations. Each person presents their own layer.

### 4.2 Final experiment checklist

| ID | Experiment | Owner | Reuses |
|---|---|---|---|
| B1 | Cloud-only (LLM + RAG + tools) | Sai Rithvik | n/a |
| B2 | Small base, no tuning or gate | Roshan | n/a |
| B3 | Small tuned, no gate | Roshan | n/a |
| R | Random routing at the gate's cloud-call rate | Kiran | B3 + B1 outputs |
| A1 | Hybrid with the base model | Kiran | B2 + B1 outputs |
| A2 | Hybrid without RAG | Sai Rithvik (cloud) + Kiran (hybrid) | n/a |
| A3 | Hybrid without tools | Sai Rithvik + Kiran | n/a |
| A4 | No queue (drop offline Qs), simulator only | Kiran | Hybrid outputs |
| Hybrid | Full system | Kiran | B3 + B1 outputs |

| Hypothesis | Test | Owner |
|---|---|---|
| H1 | Hybrid accuracy ≥ 90% of B1 with ≤ 50% cloud calls | Kiran |
| H2 | B3 ≥ B2 + 10 points on the Hindi test set | Roshan |
| H3 | Gate classifier AUROC > token-prob AUROC | Kiran |

---

## 5. Shared interfaces (agree on Day 1)

Everyone reads and writes **JSONL**, one record per line. If a field needs to change, post it in the group chat first.

**`data/processed/questions.jsonl`** (written by Anushka)
```json
{"id": "kcc_000123", "split": "test", "lang": "hi", "script": "deva",
 "crop": "wheat", "query_type": "Plant Protection", "category": "high_risk",
 "district": "Lucknow", "question": "...", "reference_answer": "...",
 "source": "kcc_2024", "gold": true}
```
- `split`: `train | dev | calib | test`
- `lang` / `script`: `hi/deva`, `hi/latn` (Hinglish), `en/latn`
- `category`: `general | live_data | high_risk | emergency`

**`outputs/edge_{base|tuned}.jsonl`** (written by Roshan)
```json
{"id": "kcc_000123", "model": "qwen3-1.7b-lora-v1", "answer": "...",
 "mean_logprob": -0.82, "min_logprob": -4.1, "n_tokens": 57, "latency_ms": 840}
```

**`outputs/cloud_{B1|A2|A3}.jsonl`** (written by Sai Rithvik)
```json
{"id": "kcc_000123", "run": "B1", "answer": "...",
 "citations": [{"doc_id": "icar_wheat_2025_p3", "date": "2025-03-01"}],
 "tool_calls": [{"name": "get_weather", "args": {"district": "Lucknow"}, "status": "ok"}],
 "as_of": "2026-10-28", "provider": "gemini-flash"}
```

**`outputs/router.jsonl` and `outputs/hybrid_*.jsonl`** (written by Kiran)
```json
{"id": "kcc_000123", "route": "general", "gate_score": 0.71, "kept_offline": true,
 "final_answer": "...", "answered_by": "edge", "queued_at": null, "delivered_at": null}
```

**`outputs/scores_*.jsonl`** (written by Anushka)
```json
{"id": "kcc_000123", "run": "B3", "label": "correct", "judge": "llm", "human_checked": false}
```

> Until the real files exist, Kiran's mock-data generator writes fake versions of every file so each person can build and test against them.

---

## 6. Repo structure

```
kisan_edge/
├── PLAN.md                  # this file
├── README.md                # setup + how to reproduce every result
├── project_proposal.pdf
├── requirements.txt
├── data/
│   ├── raw/                 # gitignored, with download scripts only
│   └── processed/           # questions.jsonl, gold, red-team (small files committed)
├── corpus/                  # RAG docs metadata (+ gitignored PDFs)
├── src/
│   ├── data/                # Anushka: cleaning, splits, translation
│   ├── eval/                # Anushka: judge, scoring, tables, plots
│   ├── edge/                # Roshan: generation, QLoRA, GGUF, llama.cpp bench
│   ├── cloud/               # Sai Rithvik: rag/, tools/, agent.py, safety.py
│   ├── router_gate/         # Kiran: router, intent clf, gate, output filter
│   ├── queue_sim/           # Kiran: queue, cache, connectivity simulator
│   └── common/              # shared schemas + mock data
├── notebooks/               # Kaggle/Colab notebooks (cleared outputs)
├── outputs/                 # run outputs (JSONL), committed if small
├── reports/
│   ├── mid/                 # mid-submission report + figures
│   └── final/
└── tests/
```

**Git rules:** one branch per person (`anushka/data`, `roshan/edge`, `sai/cloud`, `kiran/gate`); merge into `main` through PRs; never commit API keys (use `.env`, which is gitignored); commit outputs and results tables so anyone can reproduce the report.

---

## 7. Dependencies between people

| Who needs | What | From | By |
|---|---|---|---|
| Roshan, Sai Rithvik, Kiran | 50-Q seed file + cleaning and labelling rules | Anushka | **Oct 24** |
| Anushka | Cleaned Hinglish (KCC 2014-19) and English (KisanVaani) files | Roshan | Oct 25 |
| Everyone | Frozen train / dev / calib / test splits + gold batches of 50 to hand-check | Anushka | Oct 26 |
| Anushka | Hand-checked gold batches | Everyone | Oct 27 |
| Kiran | Edge outputs with logprobs (B2) | Roshan | Oct 27 |
| Kiran | Edge outputs (B3) | Roshan | Oct 28 |
| Kiran | Cloud answers (B1) | Sai Rithvik | Oct 28 |
| Anushka | Red-team set (for scoring safety metrics) | Kiran | Oct 27 |
| Anushka | All outputs for scoring | Everyone | Oct 29 (mid), Nov 12 (final) |

If something you need is late, **work on mock data** and don't wait.

---

## 8. Risks and what to do now

| Risk | Impact | Owner | Action |
|---|---|---|---|
| Gemini free-tier quota (~3,800 calls take 3–15 days) | B1 not ready | Sai Rithvik | **Start B1 calls by Oct 26.** Cache every response. Debug on 20 Qs first. Fall back to Flash-Lite, then Groq/Cerebras (switch a whole experiment at once, never part of one) |
| Kaggle GPU limit (~30 hrs/week) | No B3 for the mid-submission | Roshan | Start QLoRA by Oct 27; use Colab T4 as backup; keep pilot runs short |
| Noisy KCC labels and answers | Unreliable accuracy | Anushka | Human-checked gold subset; report results by slice |
| Weak Hindi from the small model | H2 fails | Roshan | Pick the most Hindi-fluent model in the pilot; fall back to answering in English and translating |
| Weak gate (AUROC < 0.7) | H1/H3 fail | Kiran | Stricter fixed rules plus more cloud calls; report the trade-off honestly |
| Mandi API failures | Tool metrics break | Sai Rithvik | Frozen Agmarknet snapshots |
| Diwali week | Lost days | All | Front-load Week 1; Nov 14–15 is buffer only |

---

## 9. Gaps in the proposal to fix

1. **B4** appears in the compute plan (§12: "700 for B4") but is **never defined** in §10. Define it (for example, cloud LLM without tools or RAG) or remove it. *Sai Rithvik to decide by Oct 27.*
2. §7.1(2) refers to "rules in **6.3**". It should be **7.3**.
3. **Crop-recommendation data** and its "exact match" metric (§9, §11) have no source. Define the dataset or drop the metric. *Anushka to decide by Oct 27.*
4. The **judging method** for correct/partly correct/wrong isn't specified. We'll use an LLM judge plus a human-checked sample and report their agreement. *Anushka.*

---

## 10. Definition of done (applies to everyone)

- [ ] Code is in `src/<your area>/` and runs from a clean clone using the README instructions
- [ ] Outputs are in the shared JSONL format in `outputs/`
- [ ] Results are reported **per language and script** (Hindi Devanagari, Hinglish, English)
- [ ] Every number in the report can be traced to a script and an output file
- [ ] No API keys or personal data are committed
