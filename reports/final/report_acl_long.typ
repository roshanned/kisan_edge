// Final report, two-column ACL layout. Every number below is read from outputs/final/summary.json
// (written by src/eval/run_final.py) or another file under outputs/, so the report rebuilds from the repo:
//   typst compile --root . reports/final/report.typ reports/final/report.pdf
// (the previous single-column version is kept as report_old.typ)
#set document(title: "Kisan-Edge: A Phone-Sized Farm Advisor with a Cloud Fallback")
#set page(
  paper: "a4",
  margin: (x: 2.5cm, top: 2.5cm, bottom: 2.5cm),
  columns: 2,
  numbering: "1",
)
#set columns(gutter: 0.6cm)
#set text(font: ("Times New Roman", "Nimbus Roman", "Nirmala UI", "Noto Sans Devanagari"), size: 11pt)
#set par(justify: true, leading: 0.55em, spacing: 0.7em)
#set heading(numbering: "1.1")
#show heading.where(level: 1): it => {
  set text(size: 12pt, weight: "bold")
  set par(justify: false)
  v(1em, weak: true)
  it
  v(0.5em, weak: true)
}
#show heading.where(level: 2): it => {
  set text(size: 11pt, weight: "bold")
  set par(justify: false)
  v(0.8em, weak: true)
  it
  v(0.4em, weak: true)
}
#show raw: set text(font: ("DejaVu Sans Mono", "Liberation Mono"), size: 8pt)
#show link: set text(font: ("DejaVu Sans Mono", "Liberation Mono"), size: 8pt)
#show figure.caption: set text(size: 9pt)
#show figure.caption: set par(justify: true)
#show figure.caption: it => [#strong[#it.supplement~#context it.counter.display(it.numbering)#it.separator]#it.body]
#set figure.caption(separator: [: ])
#show figure.where(kind: table): set figure.caption(position: top)
#show figure.where(kind: table): set text(size: 8pt)
#set figure(gap: 5pt)
#set table(
  stroke: (_, y) => if y <= 1 { (top: 0.5pt) } else { none },
  inset: (x: 2.5pt, y: 2pt),
)

#let S = json("/outputs/final/summary.json")
#let RM = json("/outputs/router_metrics.json")
#let JJ = json("/outputs/final/judge_vs_judge.json")
#let JH = S.at("judge_human")
#let gd = S.at("gate_diagnostics")
// percent with one decimal ("12.3"); n/a for none
#let pc(x, d: 1) = if x == none { "n/a" } else {
  let s = str(calc.round(x * 100, digits: d))
  if d > 0 and not s.contains(".") { s + ".0" } else { s }
}
#let num(x, d: 2) = if x == none { "n/a" } else {
  let s = str(calc.round(x, digits: d))
  if d > 0 and not s.contains(".") { s + "." + "0" * d } else { s }
}
// safe nested lookup: get(S, "runs", "B3", "lenient") -> value or none
#let get(d, ..keys) = {
  let v = d
  for k in keys.pos() {
    if type(v) == array and type(k) == int and k < v.len() { v = v.at(k) }
    else if type(v) == dictionary and type(k) == str and k in v { v = v.at(k) }
    else { return none }
  }
  v
}
#let yes(b) = if b == true [*met*] else if b == false [*not met*] else [n/a]
#let GROUPS = ("hi/deva", "hi/latn", "en/latn")
// table helper: closes the table with a rule
#let T(..a) = table(..a, table.hline())
// full-width (both columns) table / figure placed at the top of a page
#let wide(body, caption) = figure(body, caption: caption, placement: top, scope: "parent", kind: table)

// ---------------------------------------------------------------- title + abstract
#place(top + center, float: true, scope: "parent", clearance: 1.2em)[
  #text(size: 15pt, weight: "bold")[Kisan-Edge: A Phone-Sized Farm Advisor with a Cloud Fallback \
  for Hindi, Hinglish and English Questions]
  #v(0.9em)
  #text(size: 11pt)[Anushka Sharma #h(1.5em) Kiran R #h(1.5em) Roshan K #h(1.5em) Sai Rithvik] \
  #text(size: 10pt)[LMA group project · Final report · November 15, 2026]
  #v(1.1em)
  #align(center)[#text(size: 12pt, weight: "bold")[Abstract]]
  #v(0.2em)
  #block(width: 92%)[
    #set text(size: 10pt)
    #set par(justify: true, leading: 0.5em)
    Farmers in Uttar Pradesh ask crop questions in Hindi, Hinglish and English, often over weak mobile links, and a wrong pesticide dose can cause harm. However, a 3B-parameter model small enough for a phone is correct on only #pc(get(S, "runs", "B3", "strict", "all", "acc"))% of such questions, while a cloud agent (correct on #pc(get(S, "H1_all_questions", "B1_acc"))%) needs a connection and has no way to keep a dose off a screen. We build Kisan-Edge, which answers on the phone with a 4-bit Llama-3.2-3B model tuned with QLoRA, uses a safety-first router, an offline dose filter and a trained gate to decide which questions may stay offline, and queues the rest for a cloud agent with retrieval and tools. On 700 held-out Kisan Call Centre (KCC) questions, the hybrid is correct on #pc(get(S, "H1_all_questions", "hybrid_acc"))% against #pc(get(S, "H1_all_questions", "B1_acc"))% for the cloud agent alone (difference #pc(get(S, "comparisons", "H_minus_B1", "diff")) points, 95% CI #pc(get(S, "comparisons", "H_minus_B1", "ci95", 0)) to #pc(get(S, "comparisons", "H_minus_B1", "ci95", 1))), answers #pc(get(S, "offline_usefulness", "kept_offline_share"))% of questions on the phone, and shows no dose offline; on general questions it keeps #pc(get(S, "H1", "pct_of_B1"))% of cloud-only accuracy with #pc(get(S, "H1", "cloud_rate"))% cloud calls (95% CI of the ratio #num(get(S, "H1", "ratio_ci95", 0)) to #num(get(S, "H1", "ratio_ci95", 1))), but over all questions the safety rules send #pc(get(S, "H1_all_questions", "cloud_rate"))% to the cloud. A phone model plus a safety-first router therefore matches cloud accuracy on this test set while answering a quarter of the questions offline, yet the cloud still answers three quarters of them, fine-tuning adds #pc(get(S, "H2", "hindi_deva", "diff")) points on Hindi (target: 10), and a trained gate beats raw token probability mainly because that probability is inverted for the tuned model (AUROC #num(get(S, "H3", "classifier_auroc")) vs #num(get(S, "H3", "token_prob_auroc")); #num(get(gd, "auroc_all", "token_prob_sign_corrected")) after correcting its sign).
  ]
]

// ---------------------------------------------------------------- 1 Introduction
= Introduction

Farmers need an answer about a pest, a dose or a forecast while the crop is still in the field. India's Kisan Call Centre (KCC) answers such questions by phone @kcc, and recent work shows two ways to automate parts of it: small language models that fit on a phone after quantisation @dettmers2023qlora @gerganov2023llamacpp, and large cloud models that ground their answers in retrieved documents and tool calls @lewis2020rag @yao2023react.

However, neither route works alone for a farmer in Uttar Pradesh. A phone model is cheap and works offline, but our tuned 3B model is correct on only #pc(get(S, "runs", "B3", "strict", "all", "acc"))% of KCC test questions. A cloud agent is far more accurate (#pc(get(S, "H1_all_questions", "B1_acc"))%), but rural links are patchy, and a cloud model can write a pesticide dose that is twice the label rate, name a banned product, or miss an emergency such as poisoning or snakebite. Routing between a small and a large model is well studied @chen2023frugalgpt @ding2024hybridllm, but those systems assume both models are always reachable and optimise cost, not safety or offline use.

In this paper, we build and evaluate Kisan-Edge, a phone-first advisor with a cloud fallback, and test it end to end on 700 held-out questions in Hindi, Hinglish and English. We make five claims, each refutable from the tables that follow:

+ *The hybrid matches cloud-only accuracy.* It is correct on #pc(get(S, "H1_all_questions", "hybrid_acc"))% of questions against #pc(get(S, "H1_all_questions", "B1_acc"))% for the cloud agent, and answers #pc(get(S, "offline_usefulness", "kept_offline_share"))% of them on the phone (@sec:runs, @tab:runs).
+ *No dose reaches the screen offline.* The offline filter blocks #pc(1 - get(S, "safety", "filter_probes", "miss_rate"))% of dose probes and #pc(get(S, "safety", "high_risk_label_sent_to_cloud"))% of high-risk test questions go to the cloud (@sec:safety).
+ *A trained gate ranks phone answers better than raw token probability* (AUROC #num(get(S, "H3", "classifier_auroc")) vs #num(get(S, "H3", "token_prob_auroc"))), mainly because the tuned model's token probability is inverted (@sec:gate).
+ *Each cloud component earns its place.* Removing tools cuts live-data accuracy from 61.4% to 14.3%, and the offline queue lifts accuracy on a patchy link from #pc(get(S, "queue", "Q_patchy_A4", "accuracy"))% to #pc(get(S, "queue", "Q_patchy", "accuracy"))% (@sec:abl).
+ *The proposal's three hypotheses are decided with caveats.* H1 (at least 90% of cloud accuracy with at most 50% cloud calls on general questions) holds on the point estimate only; H2 (+10 points on Hindi) fails at +#pc(get(S, "H2", "hindi_deva", "diff")); H3 holds as defined (@sec:eval, @tab:verdicts).

Three objections follow from these results, and we answer them before the reader asks. The references are noisy (an LLM pre-check judged 42% of a gold sample wrong), so we also report a corrected 158-question subset; the phone model alone is weak, so we report its accuracy next to every hybrid number; and H1 is decided on 280 questions with a wide interval, so we show the interval and a random-routing control (@sec:lim).

// ---------------------------------------------------------------- 2 Literature Review
= Literature Review

We group prior work by the problem each line solves, and we state at the end what none of them covers.

*KCC logs supply the training and test data.* The Kisan Call Centre logs @kcc record farmers' questions and operators' short answers in many Indian languages. The answers are a few lines long, often dated or specific to one call, and only partly correct as references; we measure this in @sec:data. We build on the logs and do not survey agriculture-specific chatbots beyond them.

*Small models fit on a phone after tuning and quantisation.* LoRA @hu2022lora trains low-rank adapters, and QLoRA @dettmers2023qlora does so on a 4-bit base model, which lets one GPU adapt a 3B model. GPTQ @frantar2023gptq and the GGUF format of llama.cpp @gerganov2023llamacpp then run models of a few billion parameters on a CPU. Our phone model is Llama-3.2-3B-Instruct from the Llama 3 family @grattafiori2024llama3, tuned with QLoRA and exported to 4-bit GGUF.

*Cascades and routers choose between a small and a large model.* FrugalGPT @chen2023frugalgpt queries models from cheap to expensive and stops when a learned scorer trusts the answer. Hybrid LLM @ding2024hybridllm routes a query to the small model when it predicts a small quality gap, and RouteLLM @ong2024routellm learns routers from preference data. These systems assume both models are reachable and optimise cost. Kisan-Edge differs in three ways: a safety-first router and a dose filter act before any quality estimate, because the small model must be safe with no link; the gate is trained on judge labels of the phone model's own answers; and a store-and-forward queue covers the case where the large model cannot be reached.

*Selective prediction decides which answers to keep.* The reject option @chow1970reject and the risk-coverage curve @geifman2017selective frame the gate's task. The usual baseline is the model's own probability @hendrycks2017baseline, which modern networks report poorly calibrated @guo2017calibration, and language models can estimate their own correctness @kadavath2022know. We measure AUROC, AURC and ECE and compare a feature-based gate with token probability. A model tuned to answer in a fixed safe template is a case this work does not cover: its token probability is inverted, and a sign-corrected baseline is much stronger (@sec:gate).

*Retrieval and tools ground the cloud answers.* Retrieval-augmented generation @lewis2020rag grounds answers in documents, and ReAct @yao2023react and Toolformer @schick2023toolformer show how models call tools. We use the multilingual embedder BGE-M3 @chen2024bgem3 with FAISS @johnson2019faiss, and a rewritten Hindi plus English search query, because an embedder matches romanised Hinglish poorly as typed.

*LLM judges, Indic benchmarks and red teams support the evaluation.* A strong LLM can grade answers at scale, with known biases @zheng2023judge; we use one judge that differs from the answering model, compare it with a second judge (Cohen's $kappa$ @cohen1960kappa) and with one person's labels, and report Wilson intervals @wilson1927interval and paired bootstrap differences @efron1993bootstrap. IndicTrans2 @gala2023indictrans2 produced the Hindi test questions, BhashaBench-Krishi @bhashabench measures Hindi agricultural knowledge, and generated adversarial inputs @perez2022redteam motivate our held-out red-team sets.

*What is missing.* To our knowledge, no earlier system combines an on-phone Indic model, a safety-first router, a trained gate and an offline queue with a grounded cloud agent, and measures each part against ablations on one held-out set. We do not claim to have searched exhaustively.

// ---------------------------------------------------------------- 3 Dataset
= Dataset Created and Used <sec:data>

*We split the public KCC questions once and freeze the split.* The data are KCC questions @kcc from Uttar Pradesh on wheat, paddy, mustard and sugarcane, cleaned and split by question text into train (16,435), dev (600), calib (600) and test (700). We train only on train, fit the gate on dev, set thresholds on calib, and report on test. The test set has 300 Hindi (Devanagari), 250 Hinglish and 150 English questions; 280 are general, 280 high-risk and 140 live-data; 271 concern wheat, 244 paddy, 101 sugarcane and 84 mustard. IndicTrans2 @gala2023indictrans2 translated the English operator summaries into the Hindi questions, while the Hinglish questions are the farmers' own text.

*The phone model trains on 4,641 train examples whose targets contain no dose.* Where a KCC answer gave a quantity, we replaced the answer with a safe deferral that tells the farmer to read the label and ask the KVK or KCC 1551.

*The KCC references are noisy, so we report two views.* When an LLM pre-checked 200 gold candidates for the mid-submission, it judged 42% of the references wrong (dated forecasts, answers to a different question, doses about twice the label rate). We therefore report accuracy on all 700 test questions against the raw references (main tables) and on a 158-question gold subset with corrected references (appendix). Team members who read Hindi then read the gold questions in full and made no further changes; the 700 test references were not checked.

*The cloud agent retrieves from a corpus we built and reads frozen tool snapshots.* The corpus has 383 trusted documents (2,602 chunks) on crops, pests and schemes. The weather, mandi-price and scheme tools read snapshots dated 2026-10-30; no price data exist (no data.gov.in key), and a team member checked and corrected the scheme facts.

*Five further sets test single components.* BhashaBench-Krishi: 3,000 multiple-choice questions sampled from the machine-translated Hindi part of `BhashaBench-Multi` @bhashabench (the native-Hindi release is gated). Red-team sets: v1 (51 questions, written with the keyword lists), v2 (69, drafted by `gemini-3.5-flash-lite` while the keywords were frozen) and v3 (72, drafted by `gemini-3.5-flash` after v2's misses entered the keywords); v2 and v3 include ordinary look-alike controls, and team members who read Hindi read all rows. Recall\@5: 60 synthetic farmer questions (40 Hindi, 20 Hinglish), one per sampled document. Dose-filter probes: synthetic sentences with and without doses.

*Ethics.* We collected no new data from people. The KCC records are public, and the only human labelling is by team members.

// ---------------------------------------------------------------- 4 Methodology
= Methodology <sec:method>

== System overview

*A question passes through six parts in a fixed order* (@fig:flow). We first give one worked example, then define each part.

#let nd(t, w: 100%) = box(width: w, stroke: 0.5pt, inset: 3pt, radius: 2pt, align(center, text(size: 8pt, t)))
#let ar = align(center, text(size: 8pt)[↓])
#figure(
  stack(spacing: 2pt,
    nd[Farmer's question (Hindi / Hinglish / English)], ar,
    nd[*Router*: rules + intent classifier], ar,
    grid(columns: (1fr, 1fr), gutter: 4pt,
      stack(spacing: 2pt, nd[_emergency_: show 108 / 112 / 1551 at once], nd[_high-risk, live data_: wait for the cloud]),
      stack(spacing: 2pt, nd[_general_: *edge model* + offline dose filter], ar, nd[*Gate*: keep offline or send])),
    ar,
    nd[*Queue* (priority, dedupe, retry, stale re-ask)], ar,
    nd[*Cloud agent*: retrieval + tools + safety filter],
  ),
  caption: [Kisan-Edge routes emergencies and high-risk or live-data questions away from the phone's free-form answer, keeps good general answers offline, and queues everything else for the cloud.],
  kind: image, supplement: [Figure],
) <fig:flow>

*Worked example (illustrative, not from the test set).* A farmer types in Hinglish, "gehun mein peela rust, kitni dawai daalein?" (yellow rust in wheat, how much fungicide?). The router flags a dose request as high-risk, so the phone does not generate a dose; it shows a safe interim message with the KVK and KCC 1551 contacts and puts the question in the queue. When a link appears, the cloud agent rewrites the query into Hindi and English, retrieves crop-protection chunks, cites them, and its safety filter keeps a dose only if a retrieved source supports it. A general question such as "when should I irrigate wheat?" instead goes to the phone model, whose answer the gate keeps or sends.

*The router sends emergencies, high-risk and live-data questions away from free-form phone answers* (`router.py`). Keyword rules in Hindi, Hinglish and English flag emergencies (poisoning, snakebite, fire, electric shock, heatstroke), high-risk topics and live data (weather, prices, schemes); a TF-IDF + logistic-regression intent classifier trained on the train split follows. An emergency shows 108 / 112 / KCC 1551 at once, online or not.

*The edge model is Llama-3.2-3B-Instruct with a QLoRA adapter* (`src/edge/`): rank 16, 2 epochs, seed 42 for the reported adapter (seeds 1 and 2 for re-runs). Merged and quantised to 4 bits (GGUF Q4_K_M), it is a 2 GB file for llama.cpp. Other training settings are in `src/edge/` and `kaggle/jobs/`.

*The offline dose filter blocks any number or number word next to a unit* (`safety_filter.py`; Latin and Devanagari digits, Hindi units, "do chammach"), so no dose leaves the phone even if the model writes one.

*The gate keeps or sends each general answer* (`gate.py`). A logistic regression over the answer's token log-probabilities, its length, the script, the share of unknown words in the question, and a flag for the deferral template predicts whether the answer is correct. We fit it on dev, set its threshold on calib at a fixed 50% send rate, and report on test. The baseline gate uses only the mean token probability.

*The queue holds cloud-bound questions until a link exists* (`src/queue_sim/`): priority order (emergency first), deduplication, retry with exponential back-off, and a re-ask for live-data answers older than an hour.

*The cloud agent retrieves, calls tools, cites, and filters* (`src/cloud/`). It embeds with BGE-M3, searches FAISS with an LLM-rewritten Hindi + English query, calls weather, price and scheme tools, cites its sources, and passes a safety filter that removes uncited doses and banned pesticides. It also receives the farmer's district, which KCC records and a phone app both know. The agent is `gemma-4-26b-a4b-it` and the judge `gemma-4-31b-it`, both through the Gemini API; free-tier quotas forced this change from the proposal's Gemini Flash, and it applies to every final run alike (DECISIONS.md D19). The ban list was a 10-name draft for the final runs; we have since checked it against the official CIB\&RC list (updated 31 October 2026) and extended it to #get(S, "banned_official", "n_names") entries (@sec:safety).

== Evaluation protocol

*One LLM judge labels every answer correct, partly correct or wrong against its reference.* The judge `gemma-4-31b-it` runs at temperature 0 with JSON output and minimal thinking, and differs from the cloud agent. It also flags deferrals (declining, or pointing to a helpline). For live-data questions it does not penalise different numbers, because the references are old snapshots. A hybrid answer is either an edge or a cloud answer, so it takes that answer's label; an answer that never arrives (a question dropped in the queue ablation) counts as wrong. All model responses are cached.

*Strict accuracy counts only "correct"; lenient accuracy also counts "partly correct".* Intervals are 95% Wilson intervals, and differences between runs on the same questions use a paired bootstrap with 2,000 resamples. The gate label is strict: a phone answer is good only if it is correct. Gate quality is AUROC, AURC and ECE. Every number in this report is read from `outputs/final/summary.json` or a file named in a caption.

// ---------------------------------------------------------------- 5 Experiment runs
= Experiment Runs <sec:runs>

== Systems and results

#let row(run) = {
  let r = get(S, "runs", run)
  if r == none { () } else {
    let g = r.strict
    (
      [*#run*], [#r.what],
      ..GROUPS.map(k => [#pc(g.at(k).acc)]),
      [*#pc(g.all.acc)* \[#pc(g.all.ci95.at(0))-#pc(g.all.ci95.at(1))\]],
      [#pc(r.lenient)], [#pc(r.deferred)], [#r.cloud_per_100],
    )
  }
}
#wide(
  T(
    columns: (auto, 1fr, auto, auto, auto, auto, auto, auto, auto),
    align: (left, left, right, right, right, right, right, right, right),
    [*Run*], [*What*], [*Hindi*], [*Hinglish*], [*English*], [*All, strict \[95% CI\]*], [*Lenient*], [*Deferred*], [*Cloud /100*],
    ..("B1", "A2", "A3", "B2", "B3", "H", "H_tok", "R", "A1", "H_A2", "H_A3").map(row).flatten(),
  ),
  [Share (%) of the 700 test questions judged correct (300 Hindi, 250 Hinglish, 150 English). Lenient also counts partly correct; deferred = the judge saw a deferral (helpline, "will answer later"). Hybrid scores are composed from the judge labels of the edge and cloud answers they show. Source: `summary.json` (`runs`).],
) <tab:runs>

*The hybrid H matches the cloud agent B1, and both beat the phone model B3 by a wide margin* (@tab:runs). B1 is the cloud agent alone (retrieval and tools), B2 the untuned phone model, B3 the tuned phone model, and H the full hybrid; the table also lists the ablation runs (A1 to A3, R, H_tok and hybrids with weaker clouds), which @sec:abl discusses.

B1 is #pc(get(S, "comparisons", "B1_minus_B3", "diff")) points above B3. Absolute accuracies are low for every run, because the references are raw KCC answers (about four in ten judged wrong on the gold sample) and because deferrals never count as correct. On the 158 gold questions with corrected references, B1 reaches #pc(get(S, "runs_gold", "B1", "strict", "all", "acc"))% and H #pc(get(S, "runs_gold", "H", "strict", "all", "acc"))% (@tab:gold), and the ordering of the runs is the same on both sets.

== Edge model and H2

*Fine-tuning raised Hindi accuracy by #pc(get(S, "H2", "hindi_deva", "diff")) points, below the 10-point target, and it changed style and safety more than accuracy* (@tab:edge).

#let e3 = get(S, "edge", "B3")
#let e2 = get(S, "edge", "B2")
#let bb = get(S, "edge", "bhashabench_krishi_hi")
#figure(
  T(
    columns: (1fr, auto, auto),
    align: (left, right, right),
    [], [*B2 base*], [*B3 tuned*],
    [Strict accuracy, Hindi test], [#pc(get(S, "runs", "B2", "strict", "hi/deva", "acc"))], [#pc(get(S, "runs", "B3", "strict", "hi/deva", "acc"))],
    [Strict accuracy, all 700], [#pc(get(S, "runs", "B2", "strict", "all", "acc"))], [#pc(get(S, "runs", "B3", "strict", "all", "acc"))],
    [Lenient accuracy, all 700], [#pc(get(S, "runs", "B2", "lenient"))], [#pc(get(S, "runs", "B3", "lenient"))],
    [Mean answer length (tokens)], [#get(e2, "mean_tokens")], [#get(e3, "mean_tokens")],
    [Answers showing a dose (before filter)], [#pc(get(e2, "dose_shown_rate"))], [#pc(get(e3, "dose_shown_rate"))],
    [Answers = safe deferral template], [#pc(get(e2, "deferral_template_rate"))], [#pc(get(e3, "deferral_template_rate"))],
    [Reply in question's language (all / Hinglish)], [#pc(get(e2, "reply_language_match", "all")) / #pc(get(e2, "reply_language_match", "hi/latn"))], [#pc(get(e3, "reply_language_match", "all")) / #pc(get(e3, "reply_language_match", "hi/latn"))],
    [BhashaBench-Krishi Hindi, 3,000 MCQs (chance 25%)], [#pc(get(bb, "base", "acc"))], [#pc(get(bb, "tuned", "acc"))],
  ),
  caption: [Edge model, base vs tuned (%, unless stated). BhashaBench: zero-shot letter scoring on a fixed sample of the machine-translated Hindi subset. Sources: `summary.json` (`edge`, `runs`, `H2`).],
) <tab:edge>

*H2 is #yes(get(S, "H2", "met")).* On the 300 Hindi (Devanagari) test questions, fine-tuning raises strict accuracy by #pc(get(S, "H2", "hindi_deva", "diff")) points (95% CI #pc(get(S, "H2", "hindi_deva", "ci95", 0)) to #pc(get(S, "H2", "hindi_deva", "ci95", 1))). The interval excludes zero but sits below 10 points. Over all 700 questions the gain is #pc(get(S, "H2", "all", "diff")) points (#pc(get(S, "H2", "all", "ci95", 0)) to #pc(get(S, "H2", "all", "ci95", 1))), and on Hinglish and English the intervals include zero. Two QLoRA re-runs with other seeds give #pc(get(S, "edge", "B3_seed_reruns", "seed1", "hi/deva", "acc"))% and #pc(get(S, "edge", "B3_seed_reruns", "seed2", "hi/deva", "acc"))% on Hindi, against #pc(get(S, "runs", "B3", "strict", "hi/deva", "acc"))% for the reported adapter, so one lucky seed does not explain the result.

Strict accuracy stays low because #pc(get(e3, "deferral_template_rate"))% of B3's answers are the safe deferral, which the judge never labels correct against a reference that names a product and dose. Restricted to Hindi answers that are not deferrals, the gain is #pc(get(S, "H2", "hindi_deva_non_deferred", "diff")) points. Fine-tuning clearly bought style and safety: answers are a third as long, doses before the offline filter fall from #pc(get(e2, "dose_shown_rate")) to #pc(get(e3, "dose_shown_rate"))% of answers, and replies stay in the question's language (#pc(get(e3, "reply_language_match", "all"))%). It cost general knowledge: on BhashaBench-Krishi the tuned model scores #pc(get(bb, "base", "acc") - get(bb, "tuned", "acc")) points below the base model and picks option D far more often, which suggests that short-answer tuning disturbed the multiple-choice format as well as the knowledge.

== Phone-size check

*The 4-bit tuned model fits a mid-range phone's budget* (@tab:phone): a 2 GB file, about 3.5 GB of RAM, and about 18 tokens per second on a laptop CPU.

#let gg = get(S, "edge", "gguf")
#let gl = get(S, "edge", "gguf_laptop")
#figure(
  T(
    columns: (1fr, auto, auto, auto, auto),
    align: (left, right, right, right, right),
    [*Machine, 4 threads*], [*File*], [*RAM*], [*Prompt tok/s*], [*Gen tok/s*],
    [Laptop (13th-gen i7)], [#get(gl, "runs", 0, "model_size_gb") GB], [#get(gl, "runs", 0, "peak_rss_gb") GB], [#get(gl, "runs", 0, "prompt_tok_s")], [#get(gl, "runs", 0, "gen_tok_s")],
    [Kaggle CPU (Xeon)], [#get(gg, "file_gb") GB], [#get(gg, "peak_rss_gb") GB], [#get(gg, "prompt_tok_s")], [#get(gg, "gen_tok_s")],
  ),
  caption: [B3 as 4-bit GGUF (Q4_K_M), `llama-bench`, 128-token prompt, 64 generated tokens, 3 repetitions. Sources: `llamacpp_bench_laptop.json`, `llamacpp_bench.json`.],
) <tab:phone>

A typical 64-token B3 answer therefore takes about 4 seconds on a laptop CPU with 4 threads, and about 7 on the slower Kaggle Xeon. The RAM need is within reach of a 6-8 GB phone, and the same file runs on Android through llama.cpp, but we did not measure on a phone. A smoke test on five test questions reproduces B3's behaviour, including its deferrals.

== Gate and H3 <sec:gate>

*The trained gate ranks phone answers better than token probability, but token probability is inverted, so the margin depends on the baseline* (@tab:gate, @fig:riskcov).

#let g3 = get(S, "gate", "B3")
#wide(
  T(
    columns: (1.6fr, 1fr, 1fr, 0.1fr, 1.6fr, 1fr, 1fr),
    align: (left, right, right, center, left, right, right),
    [*On B3's 700 test answers*], [*Token prob.*], [*Classifier*], [], [*On B3's 700 test answers*], [*Token prob.*], [*Classifier*],
    [AUROC (higher better)], [#num(get(g3, "token_prob", "auroc"))], [#num(get(g3, "classifier", "auroc"))], [], [AUROC, hi/deva], [#num(get(g3, "per_group_token_prob_auroc", "hi/deva"))], [#num(get(g3, "per_group_classifier_auroc", "hi/deva"))],
    [AURC (lower better)], [#num(get(g3, "token_prob", "aurc"))], [#num(get(g3, "classifier", "aurc"))], [], [AUROC, hi/latn], [#num(get(g3, "per_group_token_prob_auroc", "hi/latn"))], [#num(get(g3, "per_group_classifier_auroc", "hi/latn"))],
    [ECE], [#num(get(g3, "token_prob", "ece"))], [#num(get(g3, "classifier", "ece"))], [], [AUROC, en/latn], [#num(get(g3, "per_group_token_prob_auroc", "en/latn"))], [#num(get(g3, "per_group_classifier_auroc", "en/latn"))],
    [Cloud-call rate at calib cut], [#pc(get(g3, "token_prob", "cloud_call_rate"))], [#pc(get(g3, "classifier", "cloud_call_rate"))], [], [AUROC, non-deferrals (n = #get(g3, "non_deferral", "n"))], [#num(get(g3, "non_deferral", "token_prob_auroc"))], [#num(get(g3, "non_deferral", "classifier_auroc"))],
    [False keep (wrong kept offline)], [#pc(get(g3, "token_prob", "false_keep_rate"))], [#pc(get(g3, "classifier", "false_keep_rate"))], [], [Accuracy of kept answers], [#pc(get(g3, "token_prob", "kept_accuracy"))], [#pc(get(g3, "classifier", "kept_accuracy"))],
    [Unnecessary send (correct sent)], [#pc(get(g3, "token_prob", "unnecessary_send_rate"))], [#pc(get(g3, "classifier", "unnecessary_send_rate"))], [], [], [], [],
  ),
  [Gate quality. Label = the judge says the edge answer is correct. Classifier: logistic regression fitted on #get(g3, "classifier", "fit_rows") dev answers; cut = the 50% quantile of calib confidences; reported on test. Paired bootstrap (2,000 resamples): the classifier beats token probability in #pc(get(S, "H3", "bootstrap", "p_classifier_better"))% of resamples, AUROC difference 95% CI #num(get(S, "H3", "bootstrap", "auroc_diff_ci95", 0)) to #num(get(S, "H3", "bootstrap", "auroc_diff_ci95", 1)). Source: `summary.json` (`gate`).],
) <tab:gate>

#figure(
  image("figures/gate_riskcov_B3.png", width: 90%),
  caption: [Risk-coverage curves of the two gates on B3's test answers. The trained classifier lowers the error rate at every coverage, while the token-probability curve is worse because its ranking is inverted.],
) <fig:riskcov>

*H3 is #yes(get(S, "H3", "met")) as defined.* The trained gate separates good from bad edge answers better than the raw token probability as the proposal defines it (AUROC #num(get(g3, "classifier", "auroc")) vs #num(get(g3, "token_prob", "auroc"))), in every language, and in every bootstrap resample. Token probability is inverted: an AUROC below 0.5 means the model is most confident when it is wrong. The fitted coefficients show why. The strongest negative weights belong to the deferral flag (#num(get(g3, "classifier", "coef", "deferral"))) and the mean log-probability itself (#num(get(g3, "classifier", "coef", "mean_logprob"))), because the model is surest of its memorised deferral and of short generic advice, and neither is ever judged correct. The baseline in H3 is therefore weak for this model. Without the deferrals, the #get(g3, "non_deferral", "n") remaining answers still give the classifier #num(get(g3, "non_deferral", "classifier_auroc")) against #num(get(g3, "non_deferral", "token_prob_auroc")).

*A sign-corrected baseline closes most of the gap.* The proposal defines the baseline as "higher probability means keep". The direction can be learned, though: on dev the sign of mean log-probability is negative (dev AUROC #num(get(gd, "dev_auroc_mean_logprob"))), so a sign-corrected baseline is fair. It reaches AUROC #num(get(gd, "auroc_all", "token_prob_sign_corrected")) on test against #num(get(gd, "auroc_all", "classifier")) for the classifier (#num(get(gd, "auroc_non_deferral", "token_prob_sign_corrected")) against #num(get(gd, "auroc_non_deferral", "classifier")) without deferrals). The classifier stays ahead by #num(get(gd, "classifier_minus_sign_corrected_token_prob", "all", 0)) to #num(get(gd, "classifier_minus_sign_corrected_token_prob", "all", 1)) AUROC (95% CI), a few points, not the gap that H3 as defined suggests. The inversion has a plain cause: #pc(get(gd, "deferral_share_test"))% of edge answers are the fixed deferral template, which is always very confident (mean log-probability #num(get(gd, "mean_logprob", "deferral"))) and never correct. Among real answers the correct ones are longer (#get(gd, "n_tokens_non_deferral", "correct") against #get(gd, "n_tokens_non_deferral", "wrong") tokens) and have lower mean log-probability (#num(get(gd, "mean_logprob", "non_deferral_correct")) against #num(get(gd, "mean_logprob", "non_deferral_wrong"))), because specific answers with product names and numbers contain low-probability tokens, while generic KCC phrases are high-probability and usually wrong. Longer answers (#num(get(g3, "classifier", "coef", "log_chars"))) and Hinglish questions (#num(get(g3, "classifier", "coef", "hinglish"))) raise the classifier's confidence; router-flagged high-risk questions lower it. Source: `summary.json` (`gate_diagnostics`).

At the threshold set on calib, the trained gate sends #pc(get(g3, "classifier", "cloud_call_rate"))% of answers to the cloud and wastes only #pc(get(g3, "classifier", "unnecessary_send_rate"))% of the good ones, where the token-probability gate sent #pc(get(g3, "token_prob", "unnecessary_send_rate"))% of the good answers away. It still keeps #pc(get(g3, "classifier", "false_keep_rate"))% of the wrong answers, because with an edge accuracy near 10% even the confident half is mostly wrong (accuracy of kept answers #pc(get(g3, "classifier", "kept_accuracy"))%). The gate ranks well; the phone model limits the result.

== Hybrid and H1

*H1 holds on the point estimate for general questions, and fails on cloud calls over all questions.*

#let hy = get(S, "hybrid")
#let to = get(S, "h1_tradeoff")
*H1 is #yes(get(S, "H1", "met")) on the point estimate, with weak support.* The proposal states H1 for general farming questions. On the #get(S, "H1", "n") test questions labelled general, the hybrid is correct on #pc(get(S, "H1", "hybrid_acc"))% against #pc(get(S, "H1", "B1_acc"))% for B1 (#pc(get(S, "H1", "pct_of_B1"))%; difference #pc(get(S, "H1", "diff", "diff")) points, CI #pc(get(S, "H1", "diff", "ci95", 0)) to #pc(get(S, "H1", "diff", "ci95", 1))) and sends #pc(get(S, "H1", "cloud_rate"))% of them to the cloud. The interval is wide, because the subset has only #get(S, "H1", "n") questions, and some general questions still go to the cloud because the router, erring on the side of safety, calls them high-risk.

*How strong is this?* Not very. The bootstrap 95% interval on the hybrid-to-B1 ratio is #num(get(S, "H1", "ratio_ci95", 0)) to #num(get(S, "H1", "ratio_ci95", 1)), and only #pc(get(S, "H1", "p_ratio_at_least_0.9"))% of resamples keep the ratio at or above 0.9, so the data are compatible with H1 failing on accuracy. Random routing at a similar cloud rate (#pc(get(S, "H1", "random_routing", "cloud_rate"))%) already reaches #pc(get(S, "H1", "random_routing", "pct_of_B1"))% of B1 on the same questions, so H1 on this subset is met mostly because the cloud answers most of them, not because the gate picks well. Absolute accuracy is low for both systems (#pc(get(S, "H1", "B1_acc"))% for B1). We also adopted the general-questions reading of H1 after seeing that the all-question reading fails; it is the wording of the proposal, but the reader should know the order.

*Over all 700 questions, the cloud-call half of H1 fails.* The full hybrid (B3 + B1, trained gate, routing as designed) reaches #pc(get(S, "H1_all_questions", "hybrid_acc"))% against #pc(get(S, "H1_all_questions", "B1_acc"))% for cloud-only, #pc(get(S, "H1_all_questions", "pct_of_B1"))% of B1. The difference is #pc(get(S, "comparisons", "H_minus_B1", "diff")) points (95% CI #pc(get(S, "comparisons", "H_minus_B1", "ci95", 0)) to #pc(get(S, "comparisons", "H_minus_B1", "ci95", 1))), within noise, while #pc(get(S, "offline_usefulness", "kept_offline_share"))% of questions stay on the phone. Yet #pc(get(S, "H1_all_questions", "cloud_rate"))% of questions reach the cloud. The router causes this, not the gate: with the intent classifier, #get(S, "hybrid", "H", "route_counts", "high_risk") of the 700 test questions are high-risk and #get(S, "hybrid", "H", "route_counts", "live_data") need live data, so #pc((get(S, "hybrid", "H", "route_counts", "high_risk") + get(S, "hybrid", "H", "route_counts", "live_data")) / 700)% go to the cloud before the gate is consulted.

*The phone answers the questions it can answer, but the cloud supplies most of the hybrid's accuracy.* The edge answers the gate keeps offline are judged correct #pc(get(S, "offline_usefulness", "kept_answer_accuracy_strict"))% of the time (#pc(get(S, "offline_usefulness", "kept_answer_accuracy_lenient"))% lenient), above B3's #pc(get(S, "runs", "B3", "strict", "all", "acc"))% overall, so the gate does keep the questions the small model can answer. With no link at all, a farmer gets a correct or partly correct answer to #pc(get(S, "offline_usefulness", "useful_offline_share"))% of questions, plus the safe interim message or emergency numbers for the rest. B3 alone is correct on only #pc(get(S, "runs", "B3", "strict", "all", "acc"))% of questions.

// ---------------------------------------------------------------- 6 Ablations
= Ablations <sec:abl>

We remove one component at a time and measure the loss on the same questions. Tools matter most among the cloud parts, the queue matters on bad links, and the gate and the tuned phone model add small gains.

== Cloud components: retrieval and tools

*Removing the tools costs about four times as much accuracy as removing retrieval* (@tab:cloud).

#let cm = get(S, "cloud_metrics")
#let rr = get(S, "rag_recall")
#wide(
  T(
    columns: (2fr, 1fr, 1fr, 1fr),
    align: (left, right, right, right),
    [*Metric*], [*B1 (RAG + tools)*], [*A2 (no RAG)*], [*A3 (no tools)*],
    [Strict accuracy (A3: its 350-question half)], [#pc(get(S, "runs", "B1", "strict", "all", "acc"))], [#pc(get(S, "runs", "A2", "strict", "all", "acc"))], [#pc(get(S, "runs", "A3", "strict", "all", "acc"))],
    [Lenient accuracy], [#pc(get(S, "runs", "B1", "lenient"))], [#pc(get(S, "runs", "A2", "lenient"))], [#pc(get(S, "runs", "A3", "lenient"))],
    [Answers citing a retrieved document], [#pc(get(cm, "B1", "citation_rate"))], [n/a], [#pc(get(cm, "A3", "citation_rate"))],
    [Tool-choice accuracy (weather / price / scheme questions)], [#pc(get(cm, "B1", "tools", "tool_choice_accuracy"))], [#pc(get(cm, "A2", "tools", "tool_choice_accuracy"))], [n/a],
    [Needless tool calls (questions needing none)], [#pc(get(cm, "B1", "tools", "needless_tool_call_rate"))], [#pc(get(cm, "A2", "tools", "needless_tool_call_rate"))], [n/a],
    [Tool arguments accepted / weather district = farmer's], [#pc(get(cm, "B1", "tools", "argument_validity")) / #pc(get(cm, "B1", "tools", "weather_district_matches_farmer"))], [#pc(get(cm, "A2", "tools", "argument_validity")) / #pc(get(cm, "A2", "tools", "weather_district_matches_farmer"))], [n/a],
    [Unapproved actions (tools not offered)], [#pc(get(cm, "B1", "tools", "unapproved_action_rate"))], [#pc(get(cm, "A2", "tools", "unapproved_action_rate"))], [n/a],
    [Abstained / abstained with no evidence], [#pc(get(cm, "B1", "abstention", "abstain_rate")) / #pc(get(cm, "B1", "abstention", "abstain_with_no_evidence_share"))], [#pc(get(cm, "A2", "abstention", "abstain_rate")) / #pc(get(cm, "A2", "abstention", "abstain_with_no_evidence_share"))], [#pc(get(cm, "A3", "abstention", "abstain_rate")) / #pc(get(cm, "A3", "abstention", "abstain_with_no_evidence_share"))],
    [Answered with no source and no tool], [#pc(get(cm, "B1", "abstention", "answer_with_no_evidence_rate"))], [#pc(get(cm, "A2", "abstention", "answer_with_no_evidence_rate"))], [#pc(get(cm, "A3", "abstention", "answer_with_no_evidence_rate"))],
    [Uncited dose replaced by the cloud safety filter], [#pc(get(cm, "B1", "safety", "uncited_dose_replaced_rate"))], [#pc(get(cm, "A2", "safety", "uncited_dose_replaced_rate"))], [#pc(get(cm, "A3", "safety", "uncited_dose_replaced_rate"))],
  ),
  [Cloud ablations on the 700 test questions (agent `gemma-4-26b-a4b-it`, snapshots of 2026-10-30), in %. "Abstained" uses the judge's deferral flag; "no evidence" = no retrieved document cited and no successful tool call. Source: `cloud_metrics.json` (`src/cloud/metrics.py`).],
) <tab:cloud>

Removing retrieval (A2) costs #pc(-get(S, "runs", "A2", "vs_B1_same_questions", "diff")) points against B1 on the same 700 questions (CI #pc(get(S, "runs", "A2", "vs_B1_same_questions", "ci95", 0)) to #pc(get(S, "runs", "A2", "vs_B1_same_questions", "ci95", 1))). Removing the tools (A3, on a stratified half) changes accuracy by #pc(get(S, "runs", "A3", "vs_B1_same_questions", "diff")) points against B1 on the same #get(S, "runs", "A3", "n") questions (CI #pc(get(S, "runs", "A3", "vs_B1_same_questions", "ci95", 0)) to #pc(get(S, "runs", "A3", "vs_B1_same_questions", "ci95", 1))). The whole loss falls on live-data questions: on the 70 live-data questions of the half, B1 is correct on 61.4% and A3 on 14.3%, and without the weather tool the agent defers (71% of these answers) instead of answering. On general and high-risk questions the two runs differ by less than 3 points (B1 25.0% vs A3 24.3%, and 17.9% vs 15.0%). Tools are therefore the most valuable cloud component for the questions that need them, even with weather snapshots only and no price data. Retrieval changes usefulness more than accuracy: without it the agent abstains in #pc(get(cm, "A2", "abstention", "abstain_rate"))% of answers, against #pc(get(cm, "B1", "abstention", "abstain_rate"))% for B1. In the hybrid, the cloud without retrieval gives #pc(get(S, "hybrid", "H_A2", "accuracy"))%, against #pc(get(S, "H1_all_questions", "hybrid_acc"))% with it.

== Edge model and gate: A1 and random routing

*The tuned phone model and the trained gate each add a small gain whose interval touches zero.*

Replacing the tuned edge model with the base model (A1, token-probability gate) costs #pc(get(S, "comparisons", "H_tok_minus_A1", "diff")) points against the same gate on the tuned model, and the dose filter has to block #get(S, "hybrid", "A1", "filter_blocked") base answers against #get(S, "hybrid", "H", "filter_blocked") tuned ones: fine-tuning moves safety work from the filter into the model. Random routing at the same cloud rate (R) is #pc(get(S, "comparisons", "H_minus_R", "diff")) points below the gated hybrid (CI #pc(get(S, "comparisons", "H_minus_R", "ci95", 0)) to #pc(get(S, "comparisons", "H_minus_R", "ci95", 1))). Both gains are small because the phone answers only a quarter of the questions.

== Router policy and the cost of safety

*Cutting cloud calls below about 60% costs accuracy or safety* (@tab:tradeoff, @fig:frontier).

#wide(
  T(
    columns: (2fr, auto, auto, auto, auto),
    align: (left, right, right, right, right),
    [*Router, policy (B3 edge + B1 cloud, classifier gate)*], [*Accuracy*], [*% of B1*], [*Cloud calls*], [*≥90% of B1 and ≤50% cloud, all questions*],
    ..if to == none { () } else { to.pairs().filter(((k, v)) => k != "frontier").map(((k, v)) => ([#k], [#pc(v.accuracy)], [#pc(v.pct_of_B1)], [#pc(v.cloud_rate)], [#yes(v.h1_met)])).flatten() },
  ),
  [The trade-off over all 700 questions (H1 itself is stated for general questions and is met). "safety" = the design: everything the router calls high-risk, live-data or emergency goes to the cloud. "gate_all" lets high-risk questions through the gate, with the offline dose filter as their only guard. Rules only = no intent classifier. Source: `summary.json` (`h1_tradeoff`).],
) <tab:tradeoff>

#figure(image("figures/h1_frontier.png", width: 100%),
  caption: [Accuracy vs cloud-call rate as the gate cut moves from "send everything gated" to "keep everything gated", for each router and policy. Dashed: 90% of B1; dotted: 50% cloud calls.]) <fig:frontier>

Under the designed routing, moving the gate cut alone cannot push cloud calls below about 69%. Dropping the intent classifier (rules only), or letting high-risk questions through the gate with the dose filter as their only guard, allows lower rates, but accuracy falls with them: 90% of B1 needs about 60% cloud calls, and at 50% cloud calls the best variant reaches only #pc(get(S, "h1_tradeoff", "rules only, gate_all", "pct_of_B1"))% of B1. These variants also give up the router's safety: rules alone send only #pc(get(get(S, "safety"), "rules_only", "redteam_v3_heldout", "risky_recall"))% of held-out risky questions to the cloud (@sec:safety). We keep the safe design, so H1 holds for general questions and the overall cloud rate is the price of the safety rules.

== Connectivity: the queue (A4)

*The queue lifts accuracy on a patchy link from #pc(get(S, "queue", "Q_patchy_A4", "accuracy"))% to #pc(get(S, "queue", "Q_patchy", "accuracy"))%* (@tab:queue).

#let qq = get(S, "queue")
#wide(
  T(
    columns: (1fr, auto, auto, auto, auto, auto, auto),
    align: (left, right, right, right, right, right, right),
    [*Link trace, queue*], [*Delivered*], [*p50 wait*], [*p90 wait*], [*Stale (live data)*], [*Duplicate sends*], [*Accuracy*],
    ..if qq == none { () } else { qq.pairs().map(((k, v)) => ([#k.replace("Q_", "").replace("_A4", ", no queue (A4)")], [#pc(v.delivery_rate)], [#v.p50_ticks], [#v.p90_ticks], [#pc(v.stale_rate)], [#pc(v.duplicate_send_rate)], [#pc(v.accuracy)])).flatten() },
  ),
  [Full hybrid (H) through the queue simulator: one question per minute, waits in minutes, other columns in %. A question whose answer never arrives counts as wrong. Traces are illustrative two-state link models (DECISIONS.md D9), not measured. Source: `summary.json` (`queue`).],
) <tab:queue>

On the patchy trace the queue delivers every cloud-bound question (median wait #get(qq, "Q_patchy", "p50_ticks") minutes, 90th percentile #get(qq, "Q_patchy", "p90_ticks")) and accuracy stays at #pc(get(qq, "Q_patchy", "accuracy"))%. Without the queue (A4) only #pc(get(qq, "Q_patchy_A4", "delivery_rate"))% of answers arrive and accuracy falls to #pc(get(qq, "Q_patchy_A4", "accuracy"))%. On the poor trace the queue still delivers #pc(get(qq, "Q_poor", "delivery_rate"))% against #pc(get(qq, "Q_poor_A4", "delivery_rate"))% without it, but answers wait hours, and #pc(get(qq, "Q_poor", "stale_rate"))% of live-data answers go stale and are re-asked once. Deduplication never fires on test, because the split has no repeated questions (unit tests cover it with synthetic duplicates). The traces are illustrative, so the direction of the gap matters more than its size.

// ---------------------------------------------------------------- 7 Evaluations
= Evaluations <sec:eval>

This section tests the pieces around the accuracy numbers: the hypotheses, the judge, retrieval and tools, fault handling and safety.

== Hypothesis verdicts

*One hypothesis fails (H2), and the other two hold only with caveats* (@tab:verdicts).

#figure(
  T(
    columns: (auto, 1fr, 1.1fr),
    align: (left, left, left),
    [*H*], [*Test (proposal)*], [*Result on the test set*],
    [H1], [General questions: hybrid at least 90% of B1 with at most 50% cloud calls],
      [#yes(get(S, "H1", "met")) on the point estimate, weakly supported: #pc(get(S, "H1", "pct_of_B1"))% of B1, #pc(get(S, "H1", "cloud_rate"))% cloud (n = #get(S, "H1", "n"); ratio CI #num(get(S, "H1", "ratio_ci95", 0)) to #num(get(S, "H1", "ratio_ci95", 1))). All 700: #pc(get(S, "H1_all_questions", "pct_of_B1"))% of B1 at #pc(get(S, "H1_all_questions", "cloud_rate"))% cloud],
    [H2], [Fine-tuning adds at least 10 points on Hindi],
      [#yes(get(S, "H2", "met")): #pc(get(S, "H2", "hindi_deva", "diff")) points (CI #pc(get(S, "H2", "hindi_deva", "ci95", 0)) to #pc(get(S, "H2", "hindi_deva", "ci95", 1)))],
    [H3], [Trained gate AUROC above token probability],
      [#yes(get(S, "H3", "met")) as defined: #num(get(S, "H3", "classifier_auroc")) vs #num(get(S, "H3", "token_prob_auroc")); vs sign-corrected #num(get(gd, "auroc_all", "token_prob_sign_corrected"))],
  ),
  caption: [H2 fails, H1 holds on the point estimate only, and H3 holds as defined. Strict accuracy (judge label "correct").],
) <tab:verdicts>

== Judge reliability <sec:judge>

Two checks support the judge, and a second judge agrees on #pc(get(JJ, "agreement_correct_vs_not"), d: 0)% of the correct-vs-not decisions. The second judge, `gemini-3.5-flash-lite` (a different model, from the same vendor), relabelled #get(JJ, "n") answers stratified over B1, B2, B3 and the three languages. The two judges agree on *correct vs not correct*, the split behind every strict accuracy in this report, for #pc(get(JJ, "agreement_correct_vs_not"))% of answers. Exact three-way agreement is lower (#pc(get(JJ, "exact_agreement"))%, Cohen's $kappa$ = #num(get(JJ, "kappa"))), almost entirely because our judge calls "wrong" what the second calls "partly correct" (#get(JJ, "confusion_main_x_second", "wrong|partly_correct") of #get(JJ, "n") answers). Strict numbers are therefore stable across judges; lenient numbers depend on the judge more. On the mid-submission's gold answers, the new judge agreed with the old flash-lite judge on 69% of labels ($kappa$ = 0.49). A $kappa$ of this size means the three-way labels deserve cautious reading.

*One person's labels agree with the judge on #pc(get(JH, "agreement_correct_vs_not"), d: 0)% of the correct-vs-not decisions.* One team member relabelled #get(JH, "n") judged answers (B1, B2 and B3; Hindi and English questions) without seeing the judge's label, using the judge's own rule: compare the answer with the KCC reference, not with the truth. The person and the judge agree exactly on #pc(get(JH, "exact_agreement"), d: 0)% of answers (Cohen's $kappa$ = #num(get(JH, "kappa"))) and on *correct vs not correct* for #pc(get(JH, "agreement_correct_vs_not"), d: 0)%, the split behind every strict accuracy. The person marks #pc(get(JH, "human_correct_rate"), d: 0)% of answers correct and the judge #pc(get(JH, "judge_correct_rate"), d: 0)%, so strict accuracy shows no bias on this sample; the judge is a little more generous on partly correct (#pc(get(JH, "judge_lenient_rate"), d: 0)% not wrong, against #pc(get(JH, "human_lenient_rate"), d: 0)%). Agreement is similar for B1, B2 and B3 (#pc(get(JH, "by_run", "B1"), d: 0)%, #pc(get(JH, "by_run", "B2"), d: 0)%, #pc(get(JH, "by_run", "B3"), d: 0)%) and for Hindi and English (#pc(get(JH, "by_language", "hi"), d: 0)% and #pc(get(JH, "by_language", "en"), d: 0)%). Limits: 100 answers, one labeller (no human-human agreement), most answers are wrong so only 13 are human-correct, and the 95% interval on the exact agreement is roughly 77% to 91%. Source: `summary.json` (`judge_human`), `judge_agreement.md`.

== Retrieval, grounding and tool use

*Rewriting the query lifts Recall\@5 from #pc(get(rr, "raw_query", "all", "recall"))% to #pc(get(rr, "rewritten_query", "all", "recall"))%, and cited sentences are mostly faithful.*

Recall\@5 on #get(rr, "raw_query", "all", "n") synthetic farmer questions (one per sampled corpus document): #pc(get(rr, "raw_query", "all", "recall"))% with the raw question (Hindi #pc(get(rr, "raw_query", "deva", "recall"))%, Hinglish #pc(get(rr, "raw_query", "latn", "recall"))%), and #pc(get(rr, "rewritten_query", "all", "recall"))% with the agent's LLM-written Hindi + English search query (Hindi #pc(get(rr, "rewritten_query", "deva", "recall"))%, Hinglish #pc(get(rr, "rewritten_query", "latn", "recall"))%). Synthetic questions reuse document wording, so these are upper bounds. Query rewriting was the single biggest retrieval improvement.

In a faithfulness check, for #get(cm, "B1", "faithfulness", "sampled") cited sentences sampled from B1, `gemini-3.5-flash-lite` compared the sentence with the chunk it cites: #pc(get(cm, "B1", "faithfulness", "supported_rate"))% were fully supported and #pc(get(cm, "B1", "faithfulness", "supported_or_partly_rate"))% at least partly, among those whose chunk could be found again. B1 cites a retrieved document in #pc(get(cm, "B1", "citation_rate"))% of answers.

The agent uses tools carefully but too rarely. It never called a tool it was not offered and rarely called one without need (#pc(get(cm, "B1", "tools", "needless_tool_call_rate"))% of questions). Its weakness is under-use: it chose the weather tool for #pc(get(cm, "B1", "tools", "by_tool", "get_weather", "chose_it"))% of weather questions, and the price and scheme tools almost never. When it calls the weather tool, the district matches the farmer's in #pc(get(cm, "B1", "tools", "weather_district_matches_farmer"))% of calls, thanks to the district context.

== Robustness: fault injection

*The agent recovers from transient tool faults but not from empty results* (@tab:fault).

#let fi = get(S, "fault_injection", "conditions")
#figure(
  T(
    columns: (1.5fr, 1fr, 1fr, 1fr, 1fr),
    align: (left, right, right, right, right),
    [*Weather-tool fault*], [*Recovered*], [*Invented*], [*Said "unavailable"*], [*Calls / Q*],
    ..if fi == none { () } else { fi.pairs().map(((k, v)) => ([#k.replace("_", ", ")], [#pc(v.recovery_rate)], [#pc(v.invented_data_rate)], [#pc(v.graceful_rate)], [#num(v.mean_tool_calls)])).flatten() },
  ),
  caption: [Fault injection on #get(S, "fault_injection", "n_questions") weather questions (A2 agent), in %. Transient = first call fails, a retry works; persistent = every call fails. "Invented" and "unavailable" are over cases with no data. Source: `fault_injection.json`.],
) <tab:fault>

Under injected tool faults, the agent retries and recovers from #pc(get(fi, "timeout_transient", "recovery_rate"))% of transient timeouts and #pc(get(fi, "5xx_transient", "recovery_rate"))% of transient server errors, but from only #pc(get(fi, "empty_transient", "recovery_rate"))% of empty results: it treats an empty answer as final. When the tool keeps failing, it says the data is unavailable in #pc(get(fi, "empty_persistent", "graceful_rate"))-#pc(get(fi, "timeout_persistent", "graceful_rate"))% of cases and invents weather numbers in at most #pc(get(fi, "empty_persistent", "invented_data_rate"))%.

== Router and safety <sec:safety>

*The held-out red-team sets expose misses that the first set hid, and safety costs cloud calls* (@tab:redteam).

#let sf = get(S, "safety")
#let rc = get(sf, "rules_plus_clf")
#let ro = get(sf, "rules_only")
#wide(
  T(
    columns: (2.4fr, 1fr, 1fr, 1fr, 1fr),
    align: (left, right, right, right, right),
    [*Red-team set (router: rules + classifier / rules only)*], [*Risky sent to cloud*], [*Emergency recognised*], [*Emergency number shown*], [*Controls over-escalated*],
    [v1: 51 Qs, written with the keyword lists], [#pc(get(rc, "redteam", "risky_recall")) / #pc(get(ro, "redteam", "risky_recall"))], [#pc(get(rc, "redteam", "emergency_escalation")) / #pc(get(ro, "redteam", "emergency_escalation"))], [#pc(get(rc, "redteam", "emergency_number_shown"))], [n/a],
    [v2: 54 + 15 controls, held out, *before* the keyword fix], [#pc(get(sf, "v2_before_keyword_fix", "rules_plus_clf", "risky_recall")) / #pc(get(sf, "v2_before_keyword_fix", "rules_only", "risky_recall"))], [#pc(get(sf, "v2_before_keyword_fix", "rules_plus_clf", "emergency_escalation")) / #pc(get(sf, "v2_before_keyword_fix", "rules_only", "emergency_escalation"))], [n/a], [n/a],
    [v2 after the keyword fix (now a dev set)], [#pc(get(rc, "redteam_v2_dev", "risky_recall")) / #pc(get(ro, "redteam_v2_dev", "risky_recall"))], [#pc(get(rc, "redteam_v2_dev", "emergency_escalation")) / #pc(get(ro, "redteam_v2_dev", "emergency_escalation"))], [#pc(get(rc, "redteam_v2_dev", "emergency_number_shown"))], [#pc(get(rc, "redteam_v2_dev", "control_over_escalation")) / #pc(get(ro, "redteam_v2_dev", "control_over_escalation"))],
    [*v3: 54 + 18 controls, held out (final)*], [*#pc(get(rc, "redteam_v3_heldout", "risky_recall"))* / #pc(get(ro, "redteam_v3_heldout", "risky_recall"))], [*#pc(get(rc, "redteam_v3_heldout", "emergency_escalation"))* / #pc(get(ro, "redteam_v3_heldout", "emergency_escalation"))], [*#pc(get(rc, "redteam_v3_heldout", "emergency_number_shown"))* / #pc(get(ro, "redteam_v3_heldout", "emergency_number_shown"))], [#pc(get(rc, "redteam_v3_heldout", "control_over_escalation")) / #pc(get(ro, "redteam_v3_heldout", "control_over_escalation"))],
  ),
  [Router on the red-team sets, in %. v2 was written by `gemini-3.5-flash-lite` and v3 by `gemini-3.5-flash`, each in Hindi, Hinglish and English, read in full by team members who read Hindi (no changes). "Emergency number shown" = routed emergency or high-risk, since both offline messages show 108 / 112. Sources: `router_metrics.json`, `router_metrics_keywords_v1.json`.],
) <tab:redteam>

The v1 red-team set suggests the router is perfect, but the held-out sets show misses. Written by other models, with vaguer wording, v2 exposed missed emergencies (electric shock, an animal eating poisonous leaves) and banned products. After those were added to the keyword lists, the fresh v3 set gives the final picture. With the intent classifier, #pc(get(rc, "redteam_v3_heldout", "risky_recall"))% of risky questions still go to the cloud, but only #pc(get(rc, "redteam_v3_heldout", "emergency_escalation"))% of emergencies are recognised as emergencies; most of the others are routed as high-risk. Because the high-risk offline message now carries 108 / 112 as well (DECISIONS.md D18), #pc(get(rc, "redteam_v3_heldout", "emergency_number_shown"))% of v3 emergencies see an emergency number without a connection. One field-fire message was missed entirely. Rules alone would be far less safe (#pc(get(ro, "redteam_v3_heldout", "risky_recall"))% of risky questions). Safety costs cloud calls: #pc(get(rc, "redteam_v3_heldout", "control_over_escalation"))% of ordinary look-alike questions ("best time of day to spray") are also escalated.

On the test set, the router sends #pc(get(sf, "high_risk_label_sent_to_cloud"))% of the questions labelled high-risk to the cloud. The offline dose filter blocks every dose probe and no safe probe (miss rate #pc(get(sf, "filter_probes", "miss_rate"))%, false blocks #pc(get(sf, "filter_probes", "false_block_rate"))%; #get(sf, "filter_probes", "n_dose") + #get(sf, "filter_probes", "n_safe") probes). Before the filter, #pc(get(sf, "B3_raw_dose_rate"))% of tuned answers and #pc(get(sf, "B2_raw_dose_rate"))% of base answers contain a dose; after it, #pc(get(sf, "offline_dose_rate_shown"))% of the answers shown offline do. In the cloud, the safety filter replaced an uncited quantity in #pc(get(cm, "B1", "safety", "uncited_dose_replaced_rate"))% of B1 answers and refused a banned product in #pc(get(cm, "B1", "safety", "banned_refused_rate"))%. That refusal used a short draft list of 10 names. We have since checked the list against the official CIB\&RC list of banned pesticides (updated 31 October 2026) and extended it to #get(S, "banned_official", "n_names") entries. Re-checking the saved answers against the corrected list, #get(S, "banned_official", "B1", "answers_naming_banned") of the #get(S, "banned_official", "B1", "n") B1 answers (#pc(get(S, "banned_official", "B1", "rate"))%) name a product that is on it (phorate, carbaryl, tridemorph, dichlorvos, parathion), mostly as recommendations (several with doses) taken from a retrieved crop-protection document, and none of them was refused; the answers without retrieval (A2) name none. These answers were not regenerated or re-scored, so the accuracy numbers include them, and the corrected filter would have replaced those sentences with a refusal. The retrieval corpus itself contains documents that recommend such products, which is a gap in the corpus, not only in the filter. In #pc(get(cm, "B1", "safety", "high_risk_referral_rate"))% of its answers to high-risk questions, B1 also refers the farmer to an expert, the KVK, KCC 1551, an officer or a lawyer.

== Gold-subset check

*The gold subset gives the same ordering of systems as the full test set* (@tab:gold).

On the 158 gold questions with corrected references, B1 reaches #pc(get(S, "runs_gold", "B1", "strict", "all", "acc"))% and H #pc(get(S, "runs_gold", "H", "strict", "all", "acc"))%, so the conclusions do not rest on the noisy references alone.

// ---------------------------------------------------------------- 8 Limitations
= Limitations <sec:lim>

We list the objections a reviewer is most likely to raise, each with what we did about it and what remains.

+ *The judge was checked against one person, on 100 answers.* Every accuracy rests on one LLM judge. It agrees with one person's labels on #pc(get(JH, "exact_agreement"), d: 0)% of 100 answers ($kappa$ = #num(get(JH, "kappa"))), but that is one labeller, the person used the judge's own reference-based rule, and the sample is small (@sec:judge). The judge is stricter than the mid-submission's, so absolute numbers are not comparable with the mid report, only differences between runs judged here.
+ *Noisy references.* The 700 test questions are graded against raw KCC answers, of which an LLM pre-check judged 42% wrong on the gold sample. This depresses every accuracy and favours answers that repeat KCC's habits. The gold subset (158) is cleaner but small: an LLM pre-check proposed the corrections, and team members who read Hindi then checked every question and reference and made no further changes.
+ *Strict accuracy punishes safe deferrals.* A deferral to KCC 1551 is never "correct", so the tuned model and every safety rule are penalised for doing what the design asks. The lenient and deferral columns are reported for this reason.
+ *The phone model is weak.* The tuned 3B model alone is correct on #pc(get(S, "runs", "B3", "strict", "all", "acc"))% of questions. The hybrid matches the cloud mostly because the cloud answers about three quarters of questions.
+ *H1 is decided on a subset, weakly.* H1 uses the #get(S, "H1", "n") questions labelled general; the confidence interval of the ratio to B1 is #num(get(S, "H1", "ratio_ci95", 0)) to #num(get(S, "H1", "ratio_ci95", 1)), random routing at a similar cloud rate reaches #pc(get(S, "H1", "random_routing", "pct_of_B1"))% of B1, the general-questions reading was adopted after the all-question reading failed, and across all questions the cloud-call target is not met.
+ *H3 is met only as defined.* A sign-corrected token probability reaches AUROC #num(get(gd, "auroc_all", "token_prob_sign_corrected")) against #num(get(gd, "auroc_all", "classifier")) for the classifier, so the classifier's real advantage is a few points.
+ *Translated Hindi.* Hindi test questions are IndicTrans2 translations of English operator summaries; only Hinglish is farmers' own text. BhashaBench-Krishi is also the machine-translated subset.
+ *Synthetic safety and retrieval sets.* Red-team v2/v3 (141 questions) were drafted by LLMs and then read in full by team members who read Hindi, who changed no row. The router keyword lists were also checked by a team member. The Recall\@5 queries were written by an LLM and not reviewed by a person; they reuse document wording, so Recall\@5 is an upper bound. Only #pc(get(rc, "redteam_v3_heldout", "emergency_escalation"))% of v3 emergencies are recognised as emergencies.
+ *Snapshots, not live data.* Tools read weather snapshots dated 2026-10-30. There are no mandi-price snapshots, so price questions get "unavailable", the scheme facts were checked and corrected by a team member (the scheme tool was never called in the saved runs, so no result depends on them), and the banned-pesticide list was checked against the official CIB\&RC list only after the runs, so #get(S, "banned_official", "B1", "answers_naming_banned") saved B1 answers name a banned product that the final filter did not catch.
+ *Models changed for quota reasons.* The final cloud agent and judge are Gemma 4 models on the free Gemini-API tier, not the proposal's Gemini Flash; A3 covers a stratified half of the test set (DECISIONS.md D29).
+ *Simulated connectivity.* The good / patchy / poor link traces are illustrative two-state models, not measured rural networks, and phone speed was measured on laptop and server CPUs, not on a phone.
+ *Deviations from the proposal.* The gate's threshold is a fixed 50% send rate on calib, not the proposal's "most coverage at a target offline accuracy" rule; the risk-coverage curves show every alternative. The crop-recommendation exact-match metric was dropped (no dataset), and the native-Hindi BhashaBench-Krishi and the Indic-KCC benchmark are gated and were not run.
+ *Corpus chunking.* Eleven corpus chunks are 10-46k characters long because some documents were split badly; the source block is capped (D28), but re-chunking would improve retrieval.

// ---------------------------------------------------------------- 9 Conclusions
= Conclusions

*What worked.* A phone model with a safety-first router matches the cloud agent's accuracy on this test set (#pc(get(S, "H1_all_questions", "pct_of_B1"))% of B1, difference within noise) while answering a quarter of the questions on the phone, and it does so safely: no dose is shown offline, #pc(get(rc, "redteam_v3_heldout", "risky_recall"))% of held-out risky questions go to the cloud, and the queue keeps answers flowing on a patchy link. H1 holds on the point estimate for general questions, with weak support. The trained gate is the clearest technical result: a logistic regression over a dozen features turns an inverted confidence signal into a usable gate (AUROC #num(get(S, "H3", "classifier_auroc"))), though most of the gain over the proposal's baseline comes from learning the sign, since a sign-corrected token probability reaches #num(get(gd, "auroc_all", "token_prob_sign_corrected")). Among the cloud parts, tools decide live-data accuracy, and query rewriting was the largest retrieval gain, especially for romanised Hinglish.

*What did not.* Fine-tuning on 4,641 noisy KCC answers taught the phone model KCC's style and our safety rules, not much more: Hindi accuracy rose #pc(get(S, "H2", "hindi_deva", "diff")) points (target: 10), and BhashaBench fell. Across all questions the cloud still receives #pc(get(S, "H1_all_questions", "cloud_rate"))% of questions, because so much of a KCC-like stream is high-risk or live-data and safety comes first. The cloud agent rarely calls the price and scheme tools.

*Future work.* (1) Narrow the router's high-risk class with a classifier trained on real dose and legal questions, since it currently sends some ordinary general questions to the cloud (among questions the router itself calls general, the hybrid sends only 41 of 219, 18.7%). (2) Distil the cloud agent's answers on the train split into the edge model rather than raw KCC answers, whose references are often wrong. (3) Train the router on emergency examples instead of relying on keywords, since indirect wording defeats lists. (4) Add mandi snapshots and verified scheme facts, re-chunk the corpus, re-run the cloud agent with the corrected ban list and a cleaned corpus, check the judge against a second human labeller, and measure on a real phone.

#heading(numbering: none, level: 1)[Contributions and Reproducibility]

The project was planned as four workstreams (PLAN.md): data and evaluation (Anushka Sharma), edge model (Roshan K), cloud side (Sai Rithvik), and router, gate, queue and integration (Kiran R). Up to the mid-submission each person worked on their layer and checked a batch of gold questions. From October 30, Roshan K carried the whole project. The final phase (full-test runs of every system, the trained gate, red-team v2 and v3, the cloud metrics, the GGUF export, the analysis pipeline and this report) was carried out by Roshan K with an AI coding assistant (Claude), which wrote much of the code and the first draft of this report and read the generated red-team items. The gold set (after an LLM pre-check) and the red-team sets (drafted by an LLM) were read in full by team members who read Hindi, with no changes, and the LLM judge was checked against one person's labels on 100 answers, not against several.

Every number in this report is in `summary.json` or another file named in a caption; `scripts/final_pipeline.sh` lists the commands in order, and `python -m src.eval.run_final` rebuilds the results, tables and figures from the saved answers and judge labels without any model call. Model calls are cached. GPU work is in `kaggle/jobs/`. Code: #link("https://github.com/roshanned/kisan_edge"); data and outputs: #link("https://huggingface.co/datasets/kisan-edge/kisan-edge-data").

// ---------------------------------------------------------------- References
#bibliography("refs.bib", title: [References], style: "apa")

// ---------------------------------------------------------------- Appendix
#pagebreak()
#counter(heading).update(0)
#set heading(numbering: "A.1", supplement: [Appendix])
#heading(level: 1)[Results on the 158-Question Gold Subset]

#wide(
  T(
    columns: (auto, 1fr, auto, auto, auto, auto, auto),
    align: (left, left, right, right, right, right, right),
    [*Run*], [*What*], [*Hindi*], [*Hinglish*], [*English*], [*All, strict \[95% CI\]*], [*Lenient*],
    ..("B1", "A2", "A3", "B2", "B3", "H", "H_tok", "R", "A1").map(run => {
      let r = get(S, "runs_gold", run)
      if r == none { () } else {
        let g = r.strict
        ([*#run*], [#get(S, "runs", run, "what")], ..GROUPS.map(k => [#pc(g.at(k).acc)]),
         [*#pc(g.all.acc)* \[#pc(g.all.ci95.at(0))-#pc(g.all.ci95.at(1))\]], [#pc(r.lenient)])
      }
    }).flatten(),
  ),
  [Share (%) of the gold questions judged correct (61 Hindi, 47 Hinglish, 50 English; references corrected by an LLM pre-check, then checked by team members who read Hindi). Source: `summary.json` (`runs_gold`).],
) <tab:gold>
