// Final report, two-column ACL layout, 8-page budget. Every number below is read from outputs/final/summary.json
// (written by src/eval/run_final.py) or another file under outputs/, so the report rebuilds from the repo:
//   typst compile --root . reports/final/report.typ reports/final/report.pdf
// Earlier versions: report_old.typ (single column), report_acl_long.typ (13-page two-column).
#set document(title: "Kisan-Edge: A Phone-Sized Farm Advisor with a Cloud Fallback")
#set page(paper: "a4", margin: (x: 2.5cm, top: 2.2cm, bottom: 2.2cm), columns: 2, numbering: "1")
#set columns(gutter: 0.6cm)
#set text(font: ("Times New Roman", "Nimbus Roman", "Nirmala UI", "Noto Sans Devanagari"), size: 11pt)
#set par(justify: true, leading: 0.55em, spacing: 0.65em)
#set heading(numbering: "1.1")
#show heading.where(level: 1): it => {
  set text(size: 12pt, weight: "bold")
  set par(justify: false)
  v(0.7em, weak: true)
  it
  v(0.35em, weak: true)
}
#show heading.where(level: 2): it => {
  set text(size: 11pt, weight: "bold")
  set par(justify: false)
  v(0.5em, weak: true)
  it
  v(0.25em, weak: true)
}
#show raw: set text(font: ("DejaVu Sans Mono", "Liberation Mono"), size: 7.5pt)
#show link: set text(font: ("DejaVu Sans Mono", "Liberation Mono"), size: 7.5pt)
#show figure.caption: set text(size: 9.5pt)
#show figure.caption: set par(justify: true, leading: 0.45em)
#show figure.caption: it => [#strong[#it.supplement~#context it.counter.display(it.numbering)#it.separator]#it.body]
#set figure.caption(separator: [: ])
#show figure.where(kind: table): set figure.caption(position: top)
#show figure.where(kind: table): set text(size: 8pt)
#set figure(gap: 4pt)
#set table(
  stroke: (_, y) => if y <= 1 { (top: 0.5pt) } else { none },
  inset: (x: 2pt, y: 1.6pt),
)
#show bibliography: set text(size: 9.5pt)
#show bibliography: set par(leading: 0.4em, spacing: 0.4em)

#let S = json("/outputs/final/summary.json")
#let JJ = json("/outputs/final/judge_vs_judge.json")
#let JH = S.at("judge_human")
#let gd = S.at("gate_diagnostics")
#let pc(x, d: 1) = if x == none { "n/a" } else {
  let s = str(calc.round(x * 100, digits: d))
  if d > 0 and not s.contains(".") { s + ".0" } else { s }
}
#let num(x, d: 2) = if x == none { "n/a" } else {
  let s = str(calc.round(x, digits: d))
  if d > 0 and not s.contains(".") { s + "." + "0" * d } else { s }
}
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
#let T(..a) = table(..a, table.hline())
#let wide(body, caption) = figure(body, caption: caption, placement: top, scope: "parent", kind: table)
#let e2 = get(S, "edge", "B2")
#let e3 = get(S, "edge", "B3")
#let bb = get(S, "edge", "bhashabench_krishi_hi")
#let g3 = get(S, "gate", "B3")
#let cm = get(S, "cloud_metrics")
#let rr = get(S, "rag_recall")
#let fi = get(S, "fault_injection", "conditions")
#let qq = get(S, "queue")
#let sf = get(S, "safety")
#let rc = get(sf, "rules_plus_clf")
#let ro = get(sf, "rules_only")

// ---------------------------------------------------------------- title + abstract
#place(top + center, float: true, scope: "parent", clearance: 1em)[
  #text(size: 14pt, weight: "bold")[Kisan-Edge: A Phone-Sized Farm Advisor with a Cloud Fallback \
  for Hindi, Hinglish and English Questions]
  #v(0.6em)
  #text(size: 10.5pt)[Anushka Sharma #h(1.5em) Kiran R #h(1.5em) Roshan K #h(1.5em) Sai Rithvik] \
  #text(size: 9.5pt)[LMA group project · Final report · November 15, 2026]
  #v(0.8em)
  #text(size: 11pt, weight: "bold")[Abstract]
  #v(0.15em)
  #block(width: 94%)[
    #set text(size: 10pt)
    #set par(justify: true, leading: 0.5em)
    Farmers in Uttar Pradesh ask crop questions in Hindi, Hinglish and English, often over weak mobile links, and a wrong pesticide dose can cause harm. However, a 3B-parameter model small enough for a phone is correct on only #pc(get(S, "runs", "B3", "strict", "all", "acc"))% of such questions, while a cloud agent (#pc(get(S, "H1_all_questions", "B1_acc"))%) needs a connection and cannot keep a dose off a screen. We build Kisan-Edge, which answers on the phone with a 4-bit Llama-3.2-3B model tuned with QLoRA, uses a safety-first router, an offline dose filter and a trained gate to decide which questions may stay offline, and queues the rest for a cloud agent with retrieval and tools. On 700 held-out Kisan Call Centre (KCC) questions, the hybrid is correct on #pc(get(S, "H1_all_questions", "hybrid_acc"))% against #pc(get(S, "H1_all_questions", "B1_acc"))% for the cloud agent alone (difference #pc(get(S, "comparisons", "H_minus_B1", "diff")) points, 95% CI #pc(get(S, "comparisons", "H_minus_B1", "ci95", 0)) to #pc(get(S, "comparisons", "H_minus_B1", "ci95", 1))), answers #pc(get(S, "offline_usefulness", "kept_offline_share"))% of questions on the phone, and shows no dose offline; on general questions it keeps #pc(get(S, "H1", "pct_of_B1"))% of cloud accuracy with #pc(get(S, "H1", "cloud_rate"))% cloud calls, though the interval is wide (#num(get(S, "H1", "ratio_ci95", 0)) to #num(get(S, "H1", "ratio_ci95", 1))). A phone model with a safety-first router therefore matches cloud accuracy while answering a quarter of the questions offline, but the safety rules still send #pc(get(S, "H1_all_questions", "cloud_rate"))% of questions to the cloud, fine-tuning adds only #pc(get(S, "H2", "hindi_deva", "diff")) points on Hindi (target: 10), and a trained gate beats raw token probability mainly because that probability is inverted for the tuned model.
  ]
]

// ---------------------------------------------------------------- 1 Introduction
= Introduction

Farmers need answers about pests, doses and forecasts while the crop is in the field. India's Kisan Call Centre (KCC) answers such questions by phone @kcc. Two techniques could automate part of this work: small models that fit on a phone after quantisation @dettmers2023qlora @gerganov2023llamacpp, and cloud models that ground their answers in retrieved documents and tool calls @lewis2020rag @yao2023react.

However, neither works alone. Our tuned 3B phone model is correct on #pc(get(S, "runs", "B3", "strict", "all", "acc"))% of KCC test questions. A cloud agent reaches #pc(get(S, "H1_all_questions", "B1_acc"))% but needs a link, and it can write a dose at twice the label rate, name a banned product, or miss an emergency such as poisoning. Routing between small and large models is well studied @chen2023frugalgpt @ding2024hybridllm, but those systems assume both models are reachable and optimise cost, not safety or offline use.

In this paper, we build Kisan-Edge, a phone-first advisor with a cloud fallback, and test it on 700 held-out questions in Hindi, Hinglish and English. We make four claims, each checkable in the tables:

+ *The hybrid matches cloud-only accuracy* (#pc(get(S, "H1_all_questions", "hybrid_acc"))% vs #pc(get(S, "H1_all_questions", "B1_acc"))%) and answers #pc(get(S, "offline_usefulness", "kept_offline_share"))% of questions on the phone (@sec:runs).
+ *No dose reaches the screen offline*, and #pc(get(S, "safety", "high_risk_label_sent_to_cloud"))% of high-risk test questions go to the cloud (@sec:safety).
+ *A trained gate ranks phone answers better than token probability* (AUROC #num(get(S, "H3", "classifier_auroc")) vs #num(get(S, "H3", "token_prob_auroc"))), mainly because that probability is inverted for the tuned model (@sec:gate).
+ *Each cloud part and the queue earn their place*: removing tools cuts live-data accuracy from 61.4% to 14.3%, and the queue lifts accuracy on a patchy link from #pc(get(S, "queue", "Q_patchy_A4", "accuracy"))% to #pc(get(S, "queue", "Q_patchy", "accuracy"))% (@sec:abl).

The proposal set three hypotheses. *H1*: on general questions the hybrid reaches at least 90% of cloud accuracy with at most 50% cloud calls. *H2*: fine-tuning adds at least 10 points on Hindi. *H3*: a trained gate beats token probability in AUROC. H2 fails, and H1 and H3 hold with caveats (@sec:eval). We answer the three objections these results invite in @sec:lim: the references are noisy, the phone model alone is weak, and H1 rests on 280 questions.

// ---------------------------------------------------------------- 2 Literature Review
= Literature Review

*KCC logs supply the data.* They record farmers' questions and operators' short answers in many Indian languages @kcc. The answers are often dated or specific to one call, which makes them partly wrong as references (@sec:data).

*Small models fit on a phone after tuning and quantisation.* QLoRA @dettmers2023qlora trains LoRA adapters @hu2022lora on a 4-bit base model, and GPTQ @frantar2023gptq and llama.cpp's GGUF format @gerganov2023llamacpp run such models on a CPU. Our phone model is Llama-3.2-3B-Instruct from the Llama 3 family @grattafiori2024llama3.

*Cascades and routers choose between a small and a large model.* FrugalGPT @chen2023frugalgpt stops at the first model a learned scorer trusts, Hybrid LLM @ding2024hybridllm routes on predicted quality gap, and RouteLLM @ong2024routellm learns routers from preferences. All optimise cost and assume both models are reachable. Kisan-Edge adds a safety-first router and dose filter that act before any quality estimate, a gate trained on judge labels of the phone model's own answers, and a store-and-forward queue for lost links.

*Selective prediction decides which answers to keep.* The reject option @chow1970reject and risk-coverage curves @geifman2017selective frame the gate's task; the usual baseline is the model's own probability @hendrycks2017baseline, often poorly calibrated @guo2017calibration, though models can estimate their own correctness @kadavath2022know. A model tuned to answer in a fixed safe template is a case this work does not cover: its token probability is inverted (@sec:gate).

*Retrieval, tools and evaluation.* Retrieval-augmented generation @lewis2020rag and tool use @yao2023react @schick2023toolformer ground the cloud agent, with BGE-M3 @chen2024bgem3 and FAISS @johnson2019faiss for search. LLM judges grade at scale with known biases @zheng2023judge, so we compare ours with a second judge (Cohen's $kappa$ @cohen1960kappa) and one person, and report Wilson @wilson1927interval and bootstrap @efron1993bootstrap intervals. IndicTrans2 @gala2023indictrans2 produced the Hindi test questions, BhashaBench @bhashabench measures Hindi agronomy, and generated red-team inputs @perez2022redteam motivate our safety sets.

*Gap.* To our knowledge, no earlier system combines an on-phone Indic model, a safety-first router, a trained gate and an offline queue with a grounded cloud agent, and ablates each part on one held-out set. We did not search exhaustively.

// ---------------------------------------------------------------- 3 Dataset
= Dataset Created and Used <sec:data>

*We split public KCC questions once and freeze the split.* The questions come from Uttar Pradesh and cover wheat, paddy, mustard and sugarcane. The split is train (16,435), dev (600), calib (600) and test (700): we train on train, fit the gate on dev, set thresholds on calib and report on test. The test set has 300 Hindi (Devanagari), 250 Hinglish and 150 English questions, and 280 general, 280 high-risk and 140 live-data questions. IndicTrans2 @gala2023indictrans2 translated the English operator summaries into the Hindi questions; the Hinglish questions are the farmers' own text. The phone model trains on 4,641 train examples whose targets contain no dose: where a KCC answer gave a quantity, we replaced it with a safe deferral to the label, the KVK or KCC 1551.

*The references are noisy, so we report two views.* An LLM pre-check judged 42% of 200 gold candidates wrong (dated forecasts, answers to another question, doses at twice the label rate). We therefore report accuracy on all 700 test questions against raw references, and on a 158-question gold subset with corrected references, which team members who read Hindi then read in full without further changes.

*We built a retrieval corpus and froze the tool data.* The corpus has 383 documents (2,602 chunks) on crops, pests and schemes. The weather, price and scheme tools read snapshots dated 2026-10-30; price data are absent (no data.gov.in key), and a team member corrected the scheme facts.

*Five smaller sets test single components.* BhashaBench-Krishi: 3,000 Hindi multiple-choice questions from the machine-translated `BhashaBench-Multi` @bhashabench. Red-team sets: v1 (51 questions, written with the keyword lists), v2 (69) and v3 (72), drafted by other LLMs, with look-alike controls, and read in full by team members who read Hindi. Recall\@5: 60 synthetic questions, one per sampled document. Dose probes: synthetic sentences with and without doses. We collected no new data from people; the only human labelling is by team members.

// ---------------------------------------------------------------- 4 Methodology
= Methodology <sec:method>

== System overview

*A question passes through six parts in a fixed order* (@fig:flow).

#let nd(t, w: 100%) = box(width: w, stroke: 0.5pt, inset: 2.5pt, radius: 2pt, align(center, text(size: 7.5pt, t)))
#let ar = align(center, text(size: 7.5pt)[↓])
#figure(
  stack(spacing: 1.5pt,
    nd[Farmer's question (Hindi / Hinglish / English)], ar,
    nd[*Router*: rules + intent classifier], ar,
    grid(columns: (1fr, 1fr), gutter: 3pt,
      stack(spacing: 1.5pt, nd[_emergency_: show 108 / 112 / 1551 at once], nd[_high-risk, live data_: wait for the cloud]),
      stack(spacing: 1.5pt, nd[_general_: *edge model* + dose filter], ar, nd[*Gate*: keep offline or send])),
    ar,
    nd[*Queue* (priority, dedupe, retry, stale re-ask)], ar,
    nd[*Cloud agent*: retrieval + tools + safety filter],
  ),
  caption: [The router keeps emergencies and high-risk or live-data questions away from the phone's free-form answer; the gate keeps good general answers offline; the queue sends the rest to the cloud.],
  kind: image, supplement: [Figure],
) <fig:flow>

*Worked example (illustrative, not from the test set).* A farmer writes "gehun mein peela rust, kitni dawai daalein?" (yellow rust in wheat, how much fungicide?). The router flags a dose request as high-risk, so the phone shows a safe message with the KVK and KCC 1551 contacts and queues the question. Online, the cloud agent rewrites the query into Hindi and English, retrieves and cites crop-protection chunks, and keeps a dose only if a retrieved source supports it.

*The router* (`router.py`) uses keyword rules in three languages for emergencies (poisoning, snakebite, fire, electric shock, heatstroke), high-risk topics and live data, followed by a TF-IDF + logistic-regression intent classifier trained on train. An emergency shows 108 / 112 / KCC 1551 at once, online or not. *The edge model* is Llama-3.2-3B-Instruct with a QLoRA adapter (rank 16, 2 epochs, seed 42; seeds 1 and 2 for re-runs), merged and quantised to GGUF Q4_K_M (2 GB); other settings are in `src/edge/` and `kaggle/jobs/`. *The dose filter* blocks any number or number word next to a unit, in Latin and Devanagari digits and Hindi units, so no dose leaves the phone even if the model writes one.

*The gate* (`gate.py`) is a logistic regression over the answer's token log-probabilities, its length, its script, the share of unknown words in the question, and a deferral-template flag. We fit it on dev, set the cut on calib at a fixed 50% send rate, and report on test; the baseline uses only mean token probability. *The queue* holds cloud-bound questions by priority (emergency first) with deduplication, exponential back-off, and a re-ask for live-data answers older than an hour.

*The cloud agent* embeds with BGE-M3, searches FAISS with a rewritten Hindi + English query, calls weather, price and scheme tools, cites sources, and passes a safety filter that removes uncited doses and banned pesticides. It also receives the farmer's district. The agent is `gemma-4-26b-a4b-it` and the judge `gemma-4-31b-it` (Gemini API); free-tier quotas forced this change from the proposal's Gemini Flash, and it applies to every final run alike. The ban list was a 10-name draft during the runs; we have since checked it against the official CIB\&RC list (31 October 2026) and extended it to #get(S, "banned_official", "n_names") names (@sec:safety).

== Evaluation protocol

*One LLM judge labels every answer correct, partly correct or wrong against its reference* (temperature 0, differing from the cloud agent), and flags deferrals. For live-data questions it ignores differing numbers, since references are old snapshots. A hybrid answer takes the label of the edge or cloud answer it shows; an answer that never arrives counts as wrong. *Strict* accuracy counts only "correct"; *lenient* adds "partly correct". We report 95% Wilson intervals, paired bootstrap differences (2,000 resamples), and AUROC, AURC and ECE for the gate, whose label is strict. Every number comes from `outputs/final/summary.json` or a file named in a caption.

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
      [#pc(r.lenient)], [#r.cloud_per_100],
    )
  }
}
#wide(
  T(
    columns: (auto, 1fr, auto, auto, auto, auto, auto, auto),
    align: (left, left, right, right, right, right, right, right),
    [*Run*], [*What*], [*Hindi*], [*Hinglish*], [*English*], [*All, strict \[95% CI\]*], [*Lenient*], [*Cloud /100*],
    ..("B1", "A2", "A3", "B2", "B3", "H", "R", "A1").map(row).flatten(),
  ),
  [The hybrid H matches the cloud agent B1 and both far exceed the phone model B3. Share (%) of the 700 test questions judged correct (300 Hindi, 250 Hinglish, 150 English). A3 covers a 350-question half. Hybrid scores combine the judge labels of the answers they show. Source: `summary.json` (`runs`).],
) <tab:runs>

*The hybrid H matches the cloud agent B1, and both beat the phone model B3 by #pc(get(S, "comparisons", "B1_minus_B3", "diff")) points or more* (@tab:runs). B1 is the cloud agent alone, B2 the untuned phone model, B3 the tuned one, and H the full hybrid; A1 to A3 and R are ablations (@sec:abl). Absolute accuracies are low because the references are raw KCC answers and deferrals never count as correct. On the 158 gold questions with corrected references, B1 reaches #pc(get(S, "runs_gold", "B1", "strict", "all", "acc"))% and H #pc(get(S, "runs_gold", "H", "strict", "all", "acc"))%, in the same order.

== Edge model and H2

*Fine-tuning raised Hindi accuracy by #pc(get(S, "H2", "hindi_deva", "diff")) points, short of the 10-point target, and changed style and safety more than accuracy* (@tab:edge).

#figure(
  T(
    columns: (1fr, auto, auto),
    align: (left, right, right),
    [], [*B2 base*], [*B3 tuned*],
    [Strict accuracy, Hindi test], [#pc(get(S, "runs", "B2", "strict", "hi/deva", "acc"))], [#pc(get(S, "runs", "B3", "strict", "hi/deva", "acc"))],
    [Strict accuracy, all 700], [#pc(get(S, "runs", "B2", "strict", "all", "acc"))], [#pc(get(S, "runs", "B3", "strict", "all", "acc"))],
    [Mean answer length (tokens)], [#get(e2, "mean_tokens")], [#get(e3, "mean_tokens")],
    [Answers showing a dose (before filter)], [#pc(get(e2, "dose_shown_rate"))], [#pc(get(e3, "dose_shown_rate"))],
    [Answers = safe deferral template], [#pc(get(e2, "deferral_template_rate"))], [#pc(get(e3, "deferral_template_rate"))],
    [BhashaBench-Krishi Hindi (chance 25%)], [#pc(get(bb, "base", "acc"))], [#pc(get(bb, "tuned", "acc"))],
  ),
  caption: [Tuning shortens answers and removes doses but lowers BhashaBench accuracy (%, unless stated). Sources: `summary.json` (`edge`, `runs`).],
) <tab:edge>

*H2 is #yes(get(S, "H2", "met")).* On the 300 Hindi questions, fine-tuning raises strict accuracy by #pc(get(S, "H2", "hindi_deva", "diff")) points (95% CI #pc(get(S, "H2", "hindi_deva", "ci95", 0)) to #pc(get(S, "H2", "hindi_deva", "ci95", 1))); over all 700 it raises it by #pc(get(S, "H2", "all", "diff")) points, and on Hinglish and English the intervals include zero. Two re-runs with other seeds give #pc(get(S, "edge", "B3_seed_reruns", "seed1", "hi/deva", "acc"))% and #pc(get(S, "edge", "B3_seed_reruns", "seed2", "hi/deva", "acc"))% on Hindi, against #pc(get(S, "runs", "B3", "strict", "hi/deva", "acc"))%. Accuracy stays low because #pc(get(e3, "deferral_template_rate"))% of B3's answers are the safe deferral, which the judge never marks correct; without deferrals the Hindi gain is #pc(get(S, "H2", "hindi_deva_non_deferred", "diff")) points. Tuning clearly bought style and safety: answers are a third as long, and doses before the filter fall from #pc(get(e2, "dose_shown_rate")) to #pc(get(e3, "dose_shown_rate"))% of answers. It cost general knowledge: B3 scores #pc(get(bb, "base", "acc") - get(bb, "tuned", "acc")) points below B2 on BhashaBench-Krishi.

== Phone-size check

*The 4-bit model fits a mid-range phone's budget.* It is a #get(S, "edge", "gguf_laptop", "runs", 0, "model_size_gb") GB file that needs #get(S, "edge", "gguf_laptop", "runs", 0, "peak_rss_gb") GB of RAM and writes #get(S, "edge", "gguf_laptop", "runs", 0, "gen_tok_s") tokens per second on four laptop CPU threads (#get(S, "edge", "gguf", "gen_tok_s") on the slower Kaggle Xeon), so a typical 64-token answer takes about 4 seconds. We did not measure on a phone.

== Gate and H3 <sec:gate>

*The trained gate ranks phone answers better than token probability, but the proposal's baseline is inverted, so the margin depends on the baseline* (@tab:gate).

#figure(
  T(
    columns: (1fr, auto, auto),
    align: (left, right, right),
    [*B3's 700 test answers*], [*Token prob.*], [*Classifier*],
    [AUROC (higher better)], [#num(get(g3, "token_prob", "auroc"))], [#num(get(g3, "classifier", "auroc"))],
    [AUROC, non-deferrals (n = #get(g3, "non_deferral", "n"))], [#num(get(g3, "non_deferral", "token_prob_auroc"))], [#num(get(g3, "non_deferral", "classifier_auroc"))],
    [AUROC, sign-corrected token prob.], [#num(get(gd, "auroc_all", "token_prob_sign_corrected"))], [#num(get(gd, "auroc_all", "classifier"))],
    [ECE], [#num(get(g3, "token_prob", "ece"))], [#num(get(g3, "classifier", "ece"))],
    [Correct answers sent to cloud (%)], [#pc(get(g3, "token_prob", "unnecessary_send_rate"))], [#pc(get(g3, "classifier", "unnecessary_send_rate"))],
    [Wrong answers kept offline (%)], [#pc(get(g3, "token_prob", "false_keep_rate"))], [#pc(get(g3, "classifier", "false_keep_rate"))],
  ),
  caption: [The classifier wins on every row, but a sign-corrected token probability comes within #num(get(gd, "auroc_all", "classifier") - get(gd, "auroc_all", "token_prob_sign_corrected")) AUROC. Label: the judge marks the edge answer correct. Source: `summary.json` (`gate`, `gate_diagnostics`).],
) <tab:gate>

*H3 is #yes(get(S, "H3", "met")) as defined.* The classifier reaches AUROC #num(get(g3, "classifier", "auroc")) against #num(get(g3, "token_prob", "auroc")) for token probability (paired bootstrap: better in #pc(get(S, "H3", "bootstrap", "p_classifier_better"))% of resamples; difference 95% CI #num(get(S, "H3", "bootstrap", "auroc_diff_ci95", 0)) to #num(get(S, "H3", "bootstrap", "auroc_diff_ci95", 1))). An AUROC below 0.5 means the model is most confident when it is wrong. The cause is plain: #pc(get(gd, "deferral_share_test"))% of edge answers are the fixed deferral template, which the model always generates with high confidence (mean log-probability #num(get(gd, "mean_logprob", "deferral"))) and never correct; among real answers, the correct ones are longer (#get(gd, "n_tokens_non_deferral", "correct") against #get(gd, "n_tokens_non_deferral", "wrong") tokens) and have lower mean log-probability (#num(get(gd, "mean_logprob", "non_deferral_correct")) against #num(get(gd, "mean_logprob", "non_deferral_wrong"))), because specific answers with product names and numbers contain low-probability tokens. A baseline whose sign we learn on dev is fairer: it reaches #num(get(gd, "auroc_all", "token_prob_sign_corrected")), and the classifier leads by #num(get(gd, "classifier_minus_sign_corrected_token_prob", "all", 0)) to #num(get(gd, "classifier_minus_sign_corrected_token_prob", "all", 1)) AUROC (95% CI), a few points. The gate ranks well, yet the phone model limits the result: the answers it keeps are correct #pc(get(S, "offline_usefulness", "kept_answer_accuracy_strict"))% of the time.

== Hybrid and H1

*H1 holds on the point estimate for general questions and fails on cloud calls over all questions.* On the #get(S, "H1", "n") general test questions, the hybrid is correct on #pc(get(S, "H1", "hybrid_acc"))% against #pc(get(S, "H1", "B1_acc"))% for B1 (#pc(get(S, "H1", "pct_of_B1"))%) with #pc(get(S, "H1", "cloud_rate"))% cloud calls. Support is weak: the 95% interval of the ratio is #num(get(S, "H1", "ratio_ci95", 0)) to #num(get(S, "H1", "ratio_ci95", 1)), only #pc(get(S, "H1", "p_ratio_at_least_0.9"))% of bootstrap resamples keep the ratio at or above 0.9, and random routing at #pc(get(S, "H1", "random_routing", "cloud_rate"))% cloud calls already reaches #pc(get(S, "H1", "random_routing", "pct_of_B1"))% of B1. We also adopted the general-questions reading after seeing that the all-question reading fails.

Over all 700 questions, H reaches #pc(get(S, "H1_all_questions", "pct_of_B1"))% of B1, but #pc(get(S, "H1_all_questions", "cloud_rate"))% of questions reach the cloud. The router causes this, not the gate: #get(S, "hybrid", "H", "route_counts", "high_risk") questions are high-risk and #get(S, "hybrid", "H", "route_counts", "live_data") need live data, so #pc((get(S, "hybrid", "H", "route_counts", "high_risk") + get(S, "hybrid", "H", "route_counts", "live_data")) / 700)% go to the cloud before the gate is consulted. The cloud supplies most of the hybrid's accuracy. With no link, a farmer still gets a correct or partly correct answer to #pc(get(S, "offline_usefulness", "useful_offline_share"))% of questions, plus the safe interim message or emergency numbers for the rest.

// ---------------------------------------------------------------- 6 Ablations
= Ablations <sec:abl>

*Tools matter most among the cloud parts, and each component's loss is measured on the same questions.* Removing retrieval (A2) costs #pc(-get(S, "runs", "A2", "vs_B1_same_questions", "diff")) points against B1 (CI #pc(get(S, "runs", "A2", "vs_B1_same_questions", "ci95", 0)) to #pc(get(S, "runs", "A2", "vs_B1_same_questions", "ci95", 1))); removing tools (A3, 350-question half) costs #pc(-get(S, "runs", "A3", "vs_B1_same_questions", "diff")) points (CI #pc(get(S, "runs", "A3", "vs_B1_same_questions", "ci95", 0)) to #pc(get(S, "runs", "A3", "vs_B1_same_questions", "ci95", 1))), all on live-data questions: B1 is correct on 61.4% of them, A3 on 14.3%, and A3 defers on 71% of them (@tab:cloud). Retrieval changes usefulness more than accuracy: without it the agent abstains on #pc(get(cm, "A2", "abstention", "abstain_rate"))% of answers, against #pc(get(cm, "B1", "abstention", "abstain_rate"))% for B1.

#figure(
  T(
    columns: (1fr, auto, auto, auto),
    align: (left, right, right, right),
    [*%*], [*B1*], [*A2 (no RAG)*], [*A3 (no tools)*],
    [Strict accuracy], [#pc(get(S, "runs", "B1", "strict", "all", "acc"))], [#pc(get(S, "runs", "A2", "strict", "all", "acc"))], [#pc(get(S, "runs", "A3", "strict", "all", "acc"))],
    [Lenient accuracy], [#pc(get(S, "runs", "B1", "lenient"))], [#pc(get(S, "runs", "A2", "lenient"))], [#pc(get(S, "runs", "A3", "lenient"))],
    [Answers citing a document], [#pc(get(cm, "B1", "citation_rate"))], [n/a], [#pc(get(cm, "A3", "citation_rate"))],
    [Tool-choice accuracy], [#pc(get(cm, "B1", "tools", "tool_choice_accuracy"))], [#pc(get(cm, "A2", "tools", "tool_choice_accuracy"))], [n/a],
    [Abstained], [#pc(get(cm, "B1", "abstention", "abstain_rate"))], [#pc(get(cm, "A2", "abstention", "abstain_rate"))], [#pc(get(cm, "A3", "abstention", "abstain_rate"))],
    [Uncited dose replaced], [#pc(get(cm, "B1", "safety", "uncited_dose_replaced_rate"))], [#pc(get(cm, "A2", "safety", "uncited_dose_replaced_rate"))], [#pc(get(cm, "A3", "safety", "uncited_dose_replaced_rate"))],
  ),
  caption: [Cloud ablations on the 700 test questions (A3: 350-question half). Source: `cloud_metrics.json`.],
) <tab:cloud>

*The tuned phone model and the trained gate add small gains whose intervals touch zero.* Swapping in the base model (A1, token-probability gate) costs #pc(get(S, "comparisons", "H_tok_minus_A1", "diff")) points and makes the dose filter block #get(S, "hybrid", "A1", "filter_blocked") answers instead of #get(S, "hybrid", "H", "filter_blocked"); random routing at the same cloud rate (R) is #pc(get(S, "comparisons", "H_minus_R", "diff")) points below H (CI #pc(get(S, "comparisons", "H_minus_R", "ci95", 0)) to #pc(get(S, "comparisons", "H_minus_R", "ci95", 1))). Both gains are small because the phone answers only a quarter of the questions.

*Cutting cloud calls below about 60% costs accuracy or safety* (@fig:frontier). The designed routing cannot go below #pc(get(S, "h1_tradeoff", "rules+clf, gate_all", "cloud_rate"), d: 0)% cloud calls by moving the gate cut alone. Rules-only routing or letting high-risk questions through the gate allows lower rates, but 90% of B1 needs about 60% cloud calls, at 50% the best variant reaches only #pc(get(S, "h1_tradeoff", "rules only, gate_all", "pct_of_B1"))% of B1, and rules alone send only #pc(get(ro, "redteam_v3_heldout", "risky_recall"))% of held-out risky questions to the cloud. We keep the safe design.

#figure(image("figures/h1_frontier.png", width: 100%),
  caption: [Accuracy against cloud-call rate as the gate cut moves, for each router and policy. Dashed: 90% of B1; dotted: 50% cloud calls.]) <fig:frontier>

*The queue lifts accuracy on a patchy link from #pc(get(qq, "Q_patchy_A4", "accuracy"))% to #pc(get(qq, "Q_patchy", "accuracy"))%.* With the queue, every cloud-bound question arrives (median wait #get(qq, "Q_patchy", "p50_ticks") minutes, 90th percentile #get(qq, "Q_patchy", "p90_ticks")); without it (A4), #pc(get(qq, "Q_patchy_A4", "delivery_rate"))% arrive. On the poor trace the queue still delivers #pc(get(qq, "Q_poor", "delivery_rate"))% against #pc(get(qq, "Q_poor_A4", "delivery_rate"))%, but answers wait hours and #pc(get(qq, "Q_poor", "stale_rate"))% of live-data answers go stale and are re-asked. The traces are illustrative two-state models, so the direction of the gap matters more than its size.

// ---------------------------------------------------------------- 7 Evaluations
= Evaluations <sec:eval>

== Hypothesis verdicts

*H2 fails, and H1 and H3 hold only with caveats* (@tab:verdicts).

#figure(
  T(
    columns: (auto, 1fr),
    align: (left, left),
    [*H*], [*Result on the test set*],
    [H1], [#yes(get(S, "H1", "met")) on the point estimate: #pc(get(S, "H1", "pct_of_B1"))% of B1 at #pc(get(S, "H1", "cloud_rate"))% cloud calls (n = #get(S, "H1", "n"); ratio CI #num(get(S, "H1", "ratio_ci95", 0)) to #num(get(S, "H1", "ratio_ci95", 1))). Over all 700: #pc(get(S, "H1_all_questions", "pct_of_B1"))% at #pc(get(S, "H1_all_questions", "cloud_rate"))%],
    [H2], [#yes(get(S, "H2", "met")): +#pc(get(S, "H2", "hindi_deva", "diff")) points (CI #pc(get(S, "H2", "hindi_deva", "ci95", 0)) to #pc(get(S, "H2", "hindi_deva", "ci95", 1)))],
    [H3], [#yes(get(S, "H3", "met")) as defined: AUROC #num(get(S, "H3", "classifier_auroc")) vs #num(get(S, "H3", "token_prob_auroc")); vs sign-corrected #num(get(gd, "auroc_all", "token_prob_sign_corrected"))],
  ),
  caption: [Hypothesis verdicts (strict accuracy).],
) <tab:verdicts>

== Judge reliability <sec:judge>

*The judge agrees with a second judge on #pc(get(JJ, "agreement_correct_vs_not"), d: 0)% and with one person on #pc(get(JH, "agreement_correct_vs_not"), d: 0)% of the correct-vs-not decisions behind every strict accuracy.* The second judge (`gemini-3.5-flash-lite`) relabelled #get(JJ, "n") stratified answers; three-way agreement is lower (#pc(get(JJ, "exact_agreement"), d: 0)%, $kappa$ = #num(get(JJ, "kappa"))), mostly because our judge calls "wrong" what the second calls "partly correct". One team member relabelled #get(JH, "n") answers (B1, B2, B3; Hindi and English) blind, using the judge's rule of comparing with the reference, not the truth: exact agreement is #pc(get(JH, "exact_agreement"), d: 0)% ($kappa$ = #num(get(JH, "kappa"))), and the person and judge both mark #pc(get(JH, "human_correct_rate"), d: 0)% of answers correct, so strict accuracy shows no bias on this sample. The limits are one labeller and only 13 human-correct answers.

== Retrieval, tools and fault handling

*Rewriting the query lifts Recall\@5 from #pc(get(rr, "raw_query", "all", "recall"))% to #pc(get(rr, "rewritten_query", "all", "recall"))%* on #get(rr, "raw_query", "all", "n") synthetic questions (an upper bound, since they reuse document wording); the gain is largest for Hinglish (#pc(get(rr, "raw_query", "latn", "recall"))% to #pc(get(rr, "rewritten_query", "latn", "recall"))%). B1 cites a document in #pc(get(cm, "B1", "citation_rate"))% of answers, and #pc(get(cm, "B1", "faithfulness", "supported_rate"))% of #get(cm, "B1", "faithfulness", "sampled") sampled cited sentences are fully supported by their chunk. The agent uses tools carefully but too rarely: it never called a tool it was not offered and made needless calls on #pc(get(cm, "B1", "tools", "needless_tool_call_rate"))% of questions, yet it chose the weather tool for only #pc(get(cm, "B1", "tools", "by_tool", "get_weather", "chose_it"))% of weather questions and almost never the price or scheme tools. Under injected weather-tool faults (#get(S, "fault_injection", "n_questions") questions), it recovers from #pc(get(fi, "timeout_transient", "recovery_rate"))% of transient timeouts and #pc(get(fi, "5xx_transient", "recovery_rate"))% of transient server errors but only #pc(get(fi, "empty_transient", "recovery_rate"))% of empty results, which it treats as final; when the tool keeps failing it says the data are unavailable in #pc(get(fi, "empty_persistent", "graceful_rate"), d: 0)-#pc(get(fi, "timeout_persistent", "graceful_rate"), d: 0)% of cases and invents numbers in at most #pc(get(fi, "empty_persistent", "invented_data_rate"), d: 0)%.

== Router and safety <sec:safety>

*The held-out red-team sets expose misses that the first set hid, and safety costs cloud calls* (@tab:redteam).

#figure(
  T(
    columns: (1.7fr, 1fr, 1fr, 1fr),
    align: (left, right, right, right),
    [*Set (rules + classifier / rules only)*], [*Risky to cloud*], [*Emergency recognised*], [*Controls over-escalated*],
    [v1, 51 Qs, written with the keyword lists], [#pc(get(rc, "redteam", "risky_recall"), d: 0) / #pc(get(ro, "redteam", "risky_recall"), d: 0)], [#pc(get(rc, "redteam", "emergency_escalation"), d: 0) / #pc(get(ro, "redteam", "emergency_escalation"), d: 0)], [n/a],
    [v2, held out, before keyword fix], [#pc(get(sf, "v2_before_keyword_fix", "rules_plus_clf", "risky_recall"), d: 0) / #pc(get(sf, "v2_before_keyword_fix", "rules_only", "risky_recall"), d: 0)], [#pc(get(sf, "v2_before_keyword_fix", "rules_plus_clf", "emergency_escalation"), d: 0) / #pc(get(sf, "v2_before_keyword_fix", "rules_only", "emergency_escalation"), d: 0)], [n/a],
    [*v3, held out (final)*], [*#pc(get(rc, "redteam_v3_heldout", "risky_recall"))* / #pc(get(ro, "redteam_v3_heldout", "risky_recall"))], [*#pc(get(rc, "redteam_v3_heldout", "emergency_escalation"), d: 0)* / #pc(get(ro, "redteam_v3_heldout", "emergency_escalation"), d: 0)], [#pc(get(rc, "redteam_v3_heldout", "control_over_escalation")) / #pc(get(ro, "redteam_v3_heldout", "control_over_escalation"))],
  ),
  caption: [Router on the red-team sets (%). v2 and v3 were drafted by other LLMs and read in full by team members who read Hindi. Sources: `router_metrics.json`, `router_metrics_keywords_v1.json`.],
) <tab:redteam>

On v3, #pc(get(rc, "redteam_v3_heldout", "risky_recall"))% of risky questions go to the cloud, but only #pc(get(rc, "redteam_v3_heldout", "emergency_escalation"), d: 0)% of emergencies are recognised as emergencies; since the high-risk offline message also shows 108 / 112, #pc(get(rc, "redteam_v3_heldout", "emergency_number_shown"))% of emergencies see an emergency number offline. #pc(get(rc, "redteam_v3_heldout", "control_over_escalation"))% of ordinary look-alike questions are escalated too. On the test set, the router sends #pc(get(sf, "high_risk_label_sent_to_cloud"))% of high-risk questions to the cloud. The offline dose filter missed #pc(get(sf, "filter_probes", "miss_rate"))% of #get(sf, "filter_probes", "n_dose") dose probes and blocked #pc(get(sf, "filter_probes", "false_block_rate"))% of #get(sf, "filter_probes", "n_safe") safe ones; #pc(get(sf, "B3_raw_dose_rate"))% of tuned answers contained a dose before it, #pc(get(sf, "offline_dose_rate_shown"))% after.

*The cloud filter missed banned products on the corrected list.* During the runs it used a 10-name draft. Re-checking the saved answers against the official list (#get(S, "banned_official", "n_names") names), #get(S, "banned_official", "B1", "answers_naming_banned") of #get(S, "banned_official", "B1", "n") B1 answers (#pc(get(S, "banned_official", "B1", "rate"))%) name a listed product (phorate, carbaryl, tridemorph, dichlorvos, parathion), mostly as recommendations from a retrieved document, and none was refused; A2 names none. We did not regenerate or re-score them, and the corpus itself contains such recommendations, so the gap lies in the corpus as well as the filter.

// ---------------------------------------------------------------- 8 Limitations
= Limitations <sec:lim>

We state the objections a reviewer is most likely to raise, with what we did about each.

+ *Noisy references.* An LLM pre-check judged 42% of a gold sample wrong. We added a corrected 158-question subset, checked by team members who read Hindi; the 700 test references were not checked.
+ *The phone model is weak.* B3 is correct on #pc(get(S, "runs", "B3", "strict", "all", "acc"))% of questions, so the hybrid's accuracy comes mostly from the cloud, and strict accuracy penalises safe deferrals.
+ *H1 and H3 are decided weakly.* H1 rests on #get(S, "H1", "n") questions and was adopted after the all-question reading failed; H3 holds only against an inverted baseline.
+ *One judge, one human labeller.* The judge is a Gemma model, not the proposal's Gemini Flash, and was checked on 100 answers by one person who used the judge's rule.
+ *Translated Hindi and synthetic sets.* Hindi test questions and BhashaBench-Krishi are machine-translated; red-team v2/v3 and the Recall\@5 queries were drafted by LLMs (the latter were not reviewed), and only #pc(get(rc, "redteam_v3_heldout", "emergency_escalation"), d: 0)% of v3 emergencies are recognised as emergencies.
+ *Snapshots and simulation.* Tools read 2026-10-30 snapshots with no price data; link traces are illustrative; speed was measured on laptop and server CPUs, not a phone; A3 covers half the test set.
+ *Unresolved safety gap.* #get(S, "banned_official", "B1", "answers_naming_banned") saved B1 answers name a banned product (@sec:safety).
+ *Deviations from the proposal.* The gate cut is a fixed 50% send rate, not "most coverage at a target accuracy"; the crop-recommendation metric was dropped (no dataset); native BhashaBench-Krishi and Indic-KCC are gated and were not run.

// ---------------------------------------------------------------- 9 Conclusions
= Conclusions

*What worked.* A phone model with a safety-first router matches the cloud agent's accuracy on this test set (#pc(get(S, "H1_all_questions", "pct_of_B1"))% of B1, within noise) while answering a quarter of the questions offline and showing no dose: #pc(get(rc, "redteam_v3_heldout", "risky_recall"))% of held-out risky questions go to the cloud, and the queue keeps answers flowing on a patchy link. Tools decide live-data accuracy, and query rewriting was the largest retrieval gain. A logistic-regression gate turns an inverted confidence signal into a usable one (AUROC #num(get(S, "H3", "classifier_auroc"))), though most of its edge over the proposal's baseline is the learned sign.

*What did not.* Fine-tuning on noisy KCC answers taught the phone model style and safety, not much more (+#pc(get(S, "H2", "hindi_deva", "diff")) points on Hindi, and BhashaBench fell), and the safety rules keep #pc(get(S, "H1_all_questions", "cloud_rate"))% of questions on the cloud.

*Next steps.* We would train the router on real dose, legal and emergency examples to cut over-escalation, distil cloud answers into the phone model instead of raw KCC answers, rerun the cloud with the corrected ban list and a cleaner corpus, add price snapshots, and test on a real phone.

#heading(numbering: none, level: 2)[Contributions and Reproducibility]

The project had four workstreams: data and evaluation (Anushka Sharma), edge model (Roshan K), cloud (Sai Rithvik), and router, gate, queue and integration (Kiran R). From October 30, Roshan K carried the project and, with an AI coding assistant (Claude) that wrote much of the code and the first draft of this report, completed the final phase. Team members who read Hindi checked the gold and red-team sets, and one person labelled 100 judge outputs. `python -m src.eval.run_final` rebuilds every table and figure from saved answers without model calls; `scripts/final_pipeline.sh` lists all steps. Code: #link("https://github.com/roshanned/kisan_edge"); data: #link("https://huggingface.co/datasets/kisan-edge/kisan-edge-data").

// ---------------------------------------------------------------- References
#bibliography("refs.bib", title: [References], style: "apa")
