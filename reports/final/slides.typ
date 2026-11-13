// Presentation for the Nov 16-19 evaluation. Numbers come from outputs/final/summary.json, like the report.
//   python -c "import typst; typst.compile('reports/final/slides.typ', output='reports/final/slides.pdf', root='.')"
#set document(title: "Kisan-Edge: final presentation")
#set page(width: 25.4cm, height: 14.29cm, margin: (x: 1.4cm, y: 1.1cm), fill: white)
#set text(font: ("Libertinus Serif", "Nirmala UI", "Noto Sans Devanagari"), size: 17pt)
#show table: set text(size: 13pt)
#let S = json("/outputs/final/summary.json")
#let RM = json("/outputs/router_metrics.json")
#let get(d, ..keys) = {
  let v = d
  for k in keys.pos() {
    if type(v) == array and type(k) == int and k < v.len() { v = v.at(k) }
    else if type(v) == dictionary and type(k) == str and k in v { v = v.at(k) }
    else { return none }
  }
  v
}
#let pc(x) = if x == none { "n/a" } else { let s = str(calc.round(x * 100, digits: 1)); if s.contains(".") { s } else { s + ".0" } }
#let num(x) = if x == none { "n/a" } else { str(calc.round(x, digits: 2)) }
#let accent = rgb("#2e6b3a")
#let slide(title, body) = {
  pagebreak(weak: true)
  text(size: 25pt, weight: "bold", fill: accent)[#title]
  v(0.4em)
  body
}
#let big(x, label) = box(width: 30%, inset: 6pt)[#text(size: 30pt, weight: "bold", fill: accent)[#x] \ #text(size: 13pt)[#label]]

// 1
#align(center + horizon)[
  #text(size: 38pt, weight: "bold", fill: accent)[Kisan-Edge] \
  #text(size: 20pt)[A phone-sized farm advisor with a cloud fallback] \
  #v(0.6em)
  #text(size: 15pt)[Anushka Sharma · Kiran R · Roshan K · Sai Rithvik \ LMA group project · final evaluation, November 2026]
]

#slide[The problem][
  - Uttar Pradesh farmers call the Kisan Call Centre (KCC) in Hindi, Hinglish and English: pests, doses, weather, prices, schemes.
  - Phones are often offline; a cloud LLM alone fails exactly when it is needed.
  - A small model on the phone can answer much, but a *wrong pesticide dose or a missed emergency* is dangerous.
  - *Goal:* answer on the phone when it is safe, send the rest to a cloud agent with sources and tools, and never let a dose or an emergency slip.
]

#slide[System][
  #set text(size: 15pt)
  #table(columns: (auto, 1fr), stroke: none, inset: 5pt,
    [*Router*], [keyword rules (3 languages) + TF-IDF intent classifier; emergency shows 108 / 112 / KCC 1551 at once],
    [*Edge model*], [Llama-3.2-3B + QLoRA on KCC train split; safe deferral instead of any dose; 4-bit GGUF, 2 GB],
    [*Dose filter*], [blocks any number + unit (Devanagari digits, Hindi units, "do chammach") before it is shown],
    [*Gate*], [logistic regression on logprobs, length, script, unknown words, deferral flag; threshold set on calib],
    [*Queue*], [priority (emergency first), dedup, retry with back-off, stale re-ask for live data],
    [*Cloud agent*], [retrieval over 383 documents (BGE-M3 + FAISS, LLM-rewritten query), weather / mandi / scheme tools, citations, cloud safety filter],
  )
]

#slide[Evaluation][
  - Frozen split: *700 test*, 600 calib, 600 dev, 16,435 train; 300 Hindi, 250 Hinglish, 150 English.
  - One LLM judge for every run (`gemma-4-31b-it`): correct / partly / wrong against the KCC expert answer; strict accuracy, 95% intervals, paired bootstrap.
  - Hybrid runs reuse the labels of the edge and cloud answers they show.
  - Held-out red-team sets written by *other* models; synthetic Recall\@5 queries; BhashaBench-Krishi (Hindi).
  - Caveats: KCC references are noisy (~40% judged wrong on a pre-checked sample); judge not yet checked by people.
]

#slide[Results: all systems (700 test questions)][
  #let rows = ("B1", "A2", "A3", "B2", "B3", "H", "R", "A1").filter(r => get(S, "runs", r) != none)
  #table(columns: (auto, 1fr, auto, auto, auto), inset: 5pt, align: (left, left, right, right, right),
    [*Run*], [*What*], [*Strict*], [*Lenient*], [*Cloud /100*],
    ..rows.map(r => ([*#r*], [#get(S, "runs", r, "what")], [#pc(get(S, "runs", r, "strict", "all", "acc"))], [#pc(get(S, "runs", r, "lenient"))], [#get(S, "runs", r, "cloud_per_100")])).flatten())
]

#slide[H1: hybrid vs cloud-only][
  #big[#pc(get(S, "H1", "pct_of_B1"))%][of cloud-only accuracy] #big[#pc(get(S, "H1", "cloud_rate"))%][cloud calls (target ≤ 50%)] #big[#pc(get(S, "offline_usefulness", "kept_offline_share"))%][answered on the phone]
  #v(0.3em)
  - Hybrid − B1: #pc(get(S, "comparisons", "H_minus_B1", "diff")) points (CI #pc(get(S, "comparisons", "H_minus_B1", "ci95", 0)) to #pc(get(S, "comparisons", "H_minus_B1", "ci95", 1))): *no measurable loss*.
  - *H1 not met:* the router forces high-risk and live-data questions (#pc((get(S, "hybrid", "H", "route_counts", "high_risk") + get(S, "hybrid", "H", "route_counts", "live_data")) / 700)%) to the cloud.
  - Reaching 50% means weakening safety; 90% of B1 needs about 60% cloud calls.
]

#slide[H1 trade-off][
  #align(center)[#image("figures/h1_frontier.png", height: 78%)]
]

#slide[H2: does fine-tuning help on Hindi?][
  #big[+#pc(get(S, "H2", "hindi_deva", "diff"))][points on Hindi (target +10)] #big[#pc(get(S, "edge", "B3", "dose_shown_rate"))%][doses before the filter (base #pc(get(S, "edge", "B2", "dose_shown_rate"))%)] #big[#get(S, "edge", "B3", "mean_tokens")][tokens per answer (base #get(S, "edge", "B2", "mean_tokens"))]
  #v(0.3em)
  - *H2 not met:* 95% CI #pc(get(S, "H2", "hindi_deva", "ci95", 0)) to #pc(get(S, "H2", "hindi_deva", "ci95", 1)) points; seed re-runs agree.
  - #pc(get(S, "edge", "B3", "deferral_template_rate"))% of tuned answers are the safe deferral, never "correct" by design.
  - BhashaBench-Krishi: #pc(get(S, "edge", "bhashabench_krishi_hi", "base", "acc"))% → #pc(get(S, "edge", "bhashabench_krishi_hi", "tuned", "acc"))%: short-answer tuning cost some general knowledge.
]

#slide[H3: a trained gate vs token probability][
  #big[#num(get(S, "H3", "classifier_auroc"))][AUROC, trained gate] #big[#num(get(S, "H3", "token_prob_auroc"))][AUROC, token probability] #big[#num(get(S, "gate", "B3", "non_deferral", "classifier_auroc"))][gate AUROC without deferrals]
  #v(0.3em)
  - *H3 met* (classifier better in #pc(get(S, "H3", "bootstrap", "p_classifier_better"))% of bootstrap resamples).
  - Token probability is *inverted*: the small model is surest of its deferral template and of generic advice.
  - Kept edge answers are #pc(get(S, "offline_usefulness", "kept_answer_accuracy_strict"))% correct, above B1's overall rate.
]

#slide[Safety: held-out red-team][
  #let v3 = get(RM, "rules_plus_clf", "redteam_v3_heldout")
  #big[#pc(get(v3, "high_risk_recall", "all"))%][risky questions sent to cloud] #big[#pc(get(v3, "emergency_escalation_rate"))%][emergencies recognised] #big[#pc(get(v3, "emergency_number_shown_rate"))%][see 108 / 112 offline]
  #v(0.3em)
  - v1 (written with the keywords) said 100%; models writing *new* questions found the gaps ("कुछ काला सा काट लिया").
  - Fix: the high-risk message also shows emergency numbers.
  - Offline dose filter: 0 misses on probes; 0% of offline answers show a dose.
]

#slide[Cloud side][
  #let cm = get(S, "cloud_metrics", "B1")
  - Recall\@5: #pc(get(S, "rag_recall", "raw_query", "all", "recall"))% raw query → *#pc(get(S, "rag_recall", "rewritten_query", "all", "recall"))%* with LLM-rewritten Hindi + English query (Hinglish #pc(get(S, "rag_recall", "raw_query", "latn", "recall"))% → #pc(get(S, "rag_recall", "rewritten_query", "latn", "recall"))%).
  - Citation faithfulness: #pc(get(cm, "faithfulness", "supported_rate"))% of cited sentences supported by their source.
  - Weather tool chosen for #pc(get(cm, "tools", "by_tool", "get_weather", "chose_it"))% of weather questions; no unapproved actions.
  - Ablations: no retrieval (A2) #pc(get(S, "runs", "A2", "strict", "all", "acc"))%, no tools (A3, 350 Qs) #pc(get(S, "runs", "A3", "strict", "all", "acc"))% vs B1 #pc(get(S, "runs", "B1", "strict", "all", "acc"))%.
]

#slide[Phone and network][
  #let l = get(S, "edge", "gguf_laptop", "runs", 0)
  #big[#get(l, "model_size_gb") GB][4-bit model] #big[#get(l, "gen_tok_s")][tokens/s, laptop CPU, 4 threads] #big[#get(l, "peak_rss_gb") GB][peak RAM]
  #v(0.3em)
  - Patchy link: queue keeps accuracy at #pc(get(S, "queue", "Q_patchy", "accuracy"))%; without it (A4) #pc(get(S, "queue", "Q_patchy_A4", "accuracy"))% (#pc(get(S, "queue", "Q_patchy_A4", "delivery_rate"))% delivered).
  - Poor link: #pc(get(S, "queue", "Q_poor", "delivery_rate"))% vs #pc(get(S, "queue", "Q_poor_A4", "delivery_rate"))% delivered.
]

#slide[What we learned][
  - The *router*, not the gate, decides the cloud bill; safety and H1's 50% target pull in opposite directions.
  - A *trained gate* fixes over-confident small models; raw token probability points the wrong way.
  - Tuning a 3B model buys style and safety more than accuracy.
  - Held-out, independently written safety tests find real holes that self-written ones hide.
  - Free-tier quotas shaped the engineering: caching, token-aware pacing, resumable runs.
  #v(0.4em)
  #text(size: 14pt)[Code and every number: github.com/roshanned/kisan_edge · `outputs/final/summary.json` · live demo: `python -m src.demo`]
]
