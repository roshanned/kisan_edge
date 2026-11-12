// Final report. Every number below is read from outputs/final/summary.json (written by src/eval/run_final.py)
// or another file under outputs/, so the report rebuilds from the repo:
//   python -c "import typst; typst.compile('reports/final/report.typ', output='reports/final/report.pdf', root='.')"
#set document(title: "Kisan-Edge: Final report")
#set page(paper: "a4", margin: 2.1cm, numbering: "1")
#set text(font: ("Libertinus Serif", "Nirmala UI", "Noto Sans Devanagari"), size: 10.5pt)
#set par(justify: true)
#set heading(numbering: "1.1")
#show table: set text(size: 8.8pt)
#show figure.caption: set text(size: 9pt)

#let S = json("/outputs/final/summary.json")
#let RM = json("/outputs/router_metrics.json")
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
#let todo(body) = block(fill: luma(240), inset: 6pt, radius: 3pt, width: 100%)[#text(fill: rgb("#a33"), weight: "bold")[TODO-INTERPRET] #body]

#align(center)[
  #text(size: 18pt, weight: "bold")[Kisan-Edge] \
  #text(size: 12pt)[A phone-sized farm advisor with a cloud fallback] \
  #v(2pt)
  Final report · LMA group project · November 15, 2026 \
  Anushka Sharma · Kiran R · Roshan K · Sai Rithvik
]

= Summary

#todo[One-paragraph summary with H1, H2, H3 verdicts.]

#figure(
  table(
    columns: (auto, 1fr, auto),
    align: (left, left, left),
    [*Hypothesis*], [*Test (proposal)*], [*Result on the 700 test questions*],
    [H1], [Hybrid accuracy at least 90% of cloud-only (B1) with at most 50% cloud calls],
      [#yes(get(S, "H1", "met")): #pc(get(S, "H1", "pct_of_B1"))% of B1 with #pc(get(S, "H1", "cloud_rate"))% cloud calls],
    [H2], [Fine-tuning adds at least 10 points on the Hindi test set],
      [#yes(get(S, "H2", "met")): #pc(get(S, "H2", "hindi_deva", "diff")) points (95% CI #pc(get(S, "H2", "hindi_deva", "ci95", 0)) to #pc(get(S, "H2", "hindi_deva", "ci95", 1)))],
    [H3], [Trained gate classifier AUROC above token-probability AUROC],
      [#yes(get(S, "H3", "met")): #num(get(S, "H3", "classifier_auroc")) vs #num(get(S, "H3", "token_prob_auroc"))],
  ),
  caption: [Hypothesis verdicts. Strict accuracy (judge label "correct").],
)

= What was built

Kisan-Edge answers a farmer's question on the phone when it safely can, and otherwise hands it to a cloud agent once the phone is online. Every question passes through five parts:

+ *Router* (`src/router_gate/router.py`). Keyword rules in Hindi, Hinglish and English for emergencies (poisoning, snakebite, fire, electric shock, heatstroke), high-risk topics (doses, mixing, banned products, legal disputes, insurance claims) and live data (weather, prices, schemes), then a TF-IDF + logistic-regression intent classifier trained on the train split. An emergency shows 108 / 112 / KCC 1551 at once, online or not.
+ *Edge model* (`src/edge/`). Llama-3.2-3B-Instruct with a QLoRA adapter (rank 16, 2 epochs, 4,641 examples from the train split). Its training targets never contain a dose: any KCC answer with a quantity was replaced by a safe deferral. Quantised to 4 bits it is a 2 GB file that runs on a laptop CPU.
+ *Offline dose filter* (`safety_filter.py`). Blocks any number or number word next to a unit (Latin and Devanagari digits, Hindi units, "do chammach"), so no dose leaves the phone even if the model writes one.
+ *Gate* (`gate.py`). For questions the router calls general, a logistic regression over the answer's token log-probabilities, its length, the script, the share of unknown words in the question, and whether the answer is the deferral template decides whether to keep the answer offline. It is fitted on dev, its threshold is set on calib, and it is reported on test.
+ *Queue and cloud agent* (`src/queue_sim/`, `src/cloud/`). Questions for the cloud wait in a priority queue (emergency first; deduplication; retry with exponential back-off; live-data answers older than an hour are re-asked) and go to an LLM agent. The agent retrieves from 383 trusted documents (2,602 chunks; BGE-M3 + FAISS, searched with an LLM-rewritten Hindi + English query), calls weather, mandi-price and scheme tools on frozen snapshots, cites its sources, and passes a safety filter that removes uncited doses and banned products.

*What changed since the mid-submission.* Everything now runs on the full 700-question test set instead of the 158-question gold set. The retrieval corpus exists, so B1 and A3 are run for the first time. The gate is a trained classifier fitted on edge answers to the dev split. Two QLoRA seed re-runs, the 4-bit GGUF export with CPU speed tests, BhashaBench-Krishi, two new held-out red-team sets, fault injection and the citation, tool and abstention metrics were added. Free-tier quotas forced two model changes, applied to every final run alike: the cloud agent is now `gemma-4-26b-a4b-it` and the judge `gemma-4-31b-it` (both through the Gemini API), because Gemini Flash-Lite's 500 requests a day could not cover about 10,000 calls (DECISIONS.md D19). The cloud agent also receives the farmer's district, which KCC records and a phone app both know (D20).

= Data and test sets

The data, cleaning rules and frozen split are those of the mid-submission: Kisan Call Centre (KCC) questions from Uttar Pradesh on wheat, paddy, mustard and sugarcane, split once by question text into train (16,435), dev (600), calib (600) and test (700). The test set has 300 Hindi (Devanagari), 250 Hinglish and 150 English questions; 280 general, 280 high-risk and 140 live-data; 271 wheat, 244 paddy, 101 sugarcane and 84 mustard. Hindi questions are IndicTrans2 translations of English operator summaries; Hinglish questions are the farmers' own text.

*References are noisy.* Each test question is graded against its KCC expert answer. When an LLM pre-checked 200 gold candidates for the mid-submission, it judged 42% of these references wrong (dated forecasts, answers to a different question, doses about twice the label rate). We therefore report accuracy on all 700 test questions against the raw KCC references (main tables) and on the 158-question gold subset whose references were corrected (appendix). Neither set has been fully checked by a person.

*Additional evaluation sets.* BhashaBench-Krishi (Hindi): a fixed sample of 3,000 multiple-choice questions from the machine-translated Hindi part of `bharatgenai/BhashaBench-Multi` (the native-Hindi release is gated). Red-team sets: v1 (51 questions, written with the keyword lists), v2 (69, written by `gemini-3.5-flash-lite` while the keywords were frozen) and v3 (72, written by `gemini-3.5-flash` after v2's misses were added to the keywords); v2 and v3 include ordinary look-alike questions to measure over-escalation. Recall\@5: 60 synthetic farmer questions (40 Hindi, 20 Hinglish), one per sampled corpus document.

= Evaluation method

Every answer is labelled correct, partly correct or wrong against the reference by one LLM judge, `gemma-4-31b-it` (temperature 0, JSON output, minimal thinking), a different model from the cloud agent. The judge also flags deferrals (declining, or pointing to a helpline). For live-data questions it is told not to penalise different numbers, since the references are old snapshots. All responses are cached. Hybrid runs are not judged again: a hybrid answer is either an edge or a cloud answer, so it takes that answer's label; an answer that never arrives (a question dropped in the queue ablation) counts as wrong.

*Accuracy* is the share of the 700 test questions labelled correct (strict); *lenient* also counts partly correct. Intervals are 95% Wilson intervals; differences between runs on the same questions use a paired bootstrap (2,000 resamples). The gate label is strict: an edge answer is good only if it is correct.

*Can the judge be trusted?* #todo[judge-vs-judge numbers; human check pending (TODO.md).]

= Results

== All runs

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
#figure(
  table(
    columns: (auto, 1fr, auto, auto, auto, auto, auto, auto, auto),
    align: (left, left, right, right, right, right, right, right, right),
    [*Run*], [*What*], [*Hindi*], [*Hinglish*], [*English*], [*All, strict \[95% CI\]*], [*Lenient*], [*Deferred*], [*Cloud /100*],
    ..("B1", "A2", "A3", "B2", "B3", "H", "H_tok", "R", "A1", "H_A2", "H_A3").map(row).flatten(),
  ),
  caption: [Share (%) of the 700 test questions judged correct (300 Hindi, 250 Hinglish, 150 English). Lenient also counts partly correct; deferred = the judge saw a deferral (helpline, "will answer later"). Hybrid scores are composed from the judge labels of the edge and cloud answers they show. Source: `outputs/final/summary.json` (`runs`).],
)

#todo[Comment on the main table.]

== Edge model and H2

#let e3 = get(S, "edge", "B3")
#let e2 = get(S, "edge", "B2")
#let bb = get(S, "edge", "bhashabench_krishi_hi")
#figure(
  table(
    columns: (1fr, auto, auto),
    align: (left, right, right),
    [], [*B2 base*], [*B3 tuned*],
    [Strict accuracy, Hindi (Devanagari) test], [#pc(get(S, "runs", "B2", "strict", "hi/deva", "acc"))], [#pc(get(S, "runs", "B3", "strict", "hi/deva", "acc"))],
    [Strict accuracy, all 700], [#pc(get(S, "runs", "B2", "strict", "all", "acc"))], [#pc(get(S, "runs", "B3", "strict", "all", "acc"))],
    [Lenient accuracy, all 700], [#pc(get(S, "runs", "B2", "lenient"))], [#pc(get(S, "runs", "B3", "lenient"))],
    [Mean answer length (tokens)], [#get(e2, "mean_tokens")], [#get(e3, "mean_tokens")],
    [Answers showing a dose (before the offline filter)], [#pc(get(e2, "dose_shown_rate"))], [#pc(get(e3, "dose_shown_rate"))],
    [Answers that are the safe deferral template], [#pc(get(e2, "deferral_template_rate"))], [#pc(get(e3, "deferral_template_rate"))],
    [Reply in the question's language (all / Hinglish)], [#pc(get(e2, "reply_language_match", "all")) / #pc(get(e2, "reply_language_match", "hi/latn"))], [#pc(get(e3, "reply_language_match", "all")) / #pc(get(e3, "reply_language_match", "hi/latn"))],
    [BhashaBench-Krishi Hindi, 3,000 MCQs (chance 25%)], [#pc(get(bb, "base", "acc"))], [#pc(get(bb, "tuned", "acc"))],
  ),
  caption: [Edge model, base vs tuned, on the test set. BhashaBench: a fixed random sample of the machine-translated Hindi subset of `bharatgenai/BhashaBench-Multi`, zero-shot letter scoring. Sources: `summary.json` (`edge`, `runs`, `H2`).],
)

*H2 is #yes(get(S, "H2", "met")).* On the 300 Hindi (Devanagari) test questions, fine-tuning raises strict accuracy by #pc(get(S, "H2", "hindi_deva", "diff")) points (95% CI #pc(get(S, "H2", "hindi_deva", "ci95", 0)) to #pc(get(S, "H2", "hindi_deva", "ci95", 1)) points). The gain is real, since the interval excludes zero, but the point estimate is below the 10-point target. Over all 700 questions the gain is #pc(get(S, "H2", "all", "diff")) points (#pc(get(S, "H2", "all", "ci95", 0)) to #pc(get(S, "H2", "all", "ci95", 1)) points); on Hinglish and English the intervals include zero. Two QLoRA re-runs with other seeds give #pc(get(S, "edge", "B3_seed_reruns", "seed1", "hi/deva", "acc"))% and #pc(get(S, "edge", "B3_seed_reruns", "seed2", "hi/deva", "acc"))% on the Hindi questions, against #pc(get(S, "runs", "B3", "strict", "hi/deva", "acc"))% for the reported adapter, so the result does not hinge on one lucky seed.

Strict accuracy stays low for both models because of what the tuned model was taught to do. #pc(get(e3, "deferral_template_rate"))% of its answers are the safe deferral ("read the label, ask KVK or KCC 1551, your question has been queued"), which the judge never labels correct against a reference that names a product and dose. Restricted to the Hindi answers that are not deferrals, the gain is #pc(get(S, "H2", "hindi_deva_non_deferred", "diff")) points. What fine-tuning clearly bought is style and safety: answers are a third as long (KCC's one- or two-line style), doses before the offline filter fall from #pc(get(e2, "dose_shown_rate")) to #pc(get(e3, "dose_shown_rate"))% of answers, and replies stay in the question's language (#pc(get(e3, "reply_language_match", "all"))%). The price is general knowledge: on BhashaBench-Krishi the tuned model is #pc(get(bb, "base", "acc") - get(bb, "tuned", "acc")) points below the base model, and it picks option D far more often, a sign that short-answer tuning disturbed the multiple-choice format as well as the knowledge.

== Phone-size check

#let gg = get(S, "edge", "gguf")
#let gl = get(S, "edge", "gguf_laptop")
#figure(
  table(
    columns: (1fr, auto, auto, auto, auto),
    align: (left, right, right, right, right),
    [*Machine (4 threads)*], [*File*], [*Peak RAM*], [*Prompt tok/s*], [*Generate tok/s*],
    [Laptop, #get(gl, "runs", 0, "cpu")], [#get(gl, "runs", 0, "model_size_gb") GB], [#get(gl, "runs", 0, "peak_rss_gb") GB], [#get(gl, "runs", 0, "prompt_tok_s")], [#get(gl, "runs", 0, "gen_tok_s")],
    [Kaggle CPU, #get(gg, "cpu")], [#get(gg, "file_gb") GB], [#get(gg, "peak_rss_gb") GB], [#get(gg, "prompt_tok_s")], [#get(gg, "gen_tok_s")],
  ),
  caption: [B3 merged and quantised to 4 bits (GGUF Q4_K_M), llama.cpp `llama-bench` (128-token prompt, 64 generated tokens, 3 repetitions). Sources: `outputs/final/llamacpp_bench.json`, `llamacpp_bench_laptop.json` (job 08 and `src/edge/bench_llamacpp.py`).],
)

The tuned model fits the phone budget of the proposal. At 4 bits it is a 2 GB file and needs about 3.5 GB of RAM while running, within reach of a 6-8 GB mid-range phone. With 4 threads on a laptop CPU it writes about 18 tokens a second, so a typical 64-token B3 answer takes about 4 seconds; on the slower Kaggle Xeon it takes about 7. Phone CPUs are slower again, but the same 4-bit file runs there through llama.cpp's Android build. We did not measure on a phone. A smoke test with the 4-bit model on five test questions reproduces B3's behaviour, including its deferrals (`outputs/final/llamacpp_smoke.jsonl`).

== Cloud side: ablations, retrieval, tools

#let cm = get(S, "cloud_metrics")
#let rr = get(S, "rag_recall")
#figure(
  table(
    columns: (1fr, auto, auto, auto),
    align: (left, right, right, right),
    [*Metric*], [*B1 (RAG + tools)*], [*A2 (no RAG)*], [*A3 (no tools)*],
    [Strict accuracy (all 700)], [#pc(get(S, "runs", "B1", "strict", "all", "acc"))], [#pc(get(S, "runs", "A2", "strict", "all", "acc"))], [#pc(get(S, "runs", "A3", "strict", "all", "acc"))],
    [Lenient accuracy], [#pc(get(S, "runs", "B1", "lenient"))], [#pc(get(S, "runs", "A2", "lenient"))], [#pc(get(S, "runs", "A3", "lenient"))],
    [Answers citing a retrieved document], [#pc(get(cm, "B1", "citation_rate"))], [n/a], [#pc(get(cm, "A3", "citation_rate"))],
    [Tool-choice accuracy (questions asking for weather / price / scheme)], [#pc(get(cm, "B1", "tools", "tool_choice_accuracy"))], [#pc(get(cm, "A2", "tools", "tool_choice_accuracy"))], [n/a],
    [Needless tool calls (questions asking none of these)], [#pc(get(cm, "B1", "tools", "needless_tool_call_rate"))], [#pc(get(cm, "A2", "tools", "needless_tool_call_rate"))], [n/a],
    [Tool arguments accepted / weather district = farmer's], [#pc(get(cm, "B1", "tools", "argument_validity")) / #pc(get(cm, "B1", "tools", "weather_district_matches_farmer"))], [#pc(get(cm, "A2", "tools", "argument_validity")) / #pc(get(cm, "A2", "tools", "weather_district_matches_farmer"))], [n/a],
    [Unapproved actions (calls to tools not offered)], [#pc(get(cm, "B1", "tools", "unapproved_action_rate"))], [#pc(get(cm, "A2", "tools", "unapproved_action_rate"))], [n/a],
    [Abstained / abstained with no evidence], [#pc(get(cm, "B1", "abstention", "abstain_rate")) / #pc(get(cm, "B1", "abstention", "abstain_with_no_evidence_share"))], [#pc(get(cm, "A2", "abstention", "abstain_rate")) / #pc(get(cm, "A2", "abstention", "abstain_with_no_evidence_share"))], [#pc(get(cm, "A3", "abstention", "abstain_rate")) / #pc(get(cm, "A3", "abstention", "abstain_with_no_evidence_share"))],
    [Answered with no source and no tool], [#pc(get(cm, "B1", "abstention", "answer_with_no_evidence_rate"))], [#pc(get(cm, "A2", "abstention", "answer_with_no_evidence_rate"))], [#pc(get(cm, "A3", "abstention", "answer_with_no_evidence_rate"))],
    [Uncited dose replaced by the cloud safety filter], [#pc(get(cm, "B1", "safety", "uncited_dose_replaced_rate"))], [#pc(get(cm, "A2", "safety", "uncited_dose_replaced_rate"))], [#pc(get(cm, "A3", "safety", "uncited_dose_replaced_rate"))],
  ),
  caption: [Cloud runs on the 700 test questions (agent `gemma-4-26b-a4b-it`, snapshots of 2026-10-30). "Abstained" uses the judge's deferral flag; "no evidence" = no retrieved document cited and no successful tool call. Source: `outputs/final/cloud_metrics.json` (`src/cloud/metrics.py`).],
)

*Retrieval.* Recall\@5 on #get(rr, "raw_query", "all", "n") synthetic farmer questions (one per sampled corpus document, written by `gemini-3.5-flash-lite`; `corpus/recall_queries.jsonl`): #pc(get(rr, "raw_query", "all", "recall"))% with the raw question (Hindi #pc(get(rr, "raw_query", "deva", "recall"))%, Hinglish #pc(get(rr, "raw_query", "latn", "recall"))%), and #pc(get(rr, "rewritten_query", "all", "recall"))% with the agent's LLM-written Hindi + English search query (Hindi #pc(get(rr, "rewritten_query", "deva", "recall"))%, Hinglish #pc(get(rr, "rewritten_query", "latn", "recall"))%). Synthetic questions reuse document wording, so these are upper bounds. *Citation faithfulness.* For #get(cm, "B1", "faithfulness", "sampled") cited sentences sampled from B1, `gemini-3.5-flash-lite` compared the sentence with the chunk it cites (re-retrieved from the stored search query): #pc(get(cm, "B1", "faithfulness", "supported_rate"))% were fully supported and #pc(get(cm, "B1", "faithfulness", "supported_or_partly_rate"))% at least partly, among those whose chunk could be found again.

#let fi = get(S, "fault_injection", "conditions")
#figure(
  table(
    columns: (1fr, auto, auto, auto, auto),
    align: (left, right, right, right, right),
    [*Fault (weather tool)*], [*Recovered (got data)*], [*Invented numbers (no data)*], [*Said "unavailable" (no data)*], [*Tool calls / question*],
    ..if fi == none { () } else { fi.pairs().map(((k, v)) => ([#k.replace("_", ", ")], [#pc(v.recovery_rate)], [#pc(v.invented_data_rate)], [#pc(v.graceful_rate)], [#num(v.mean_tool_calls)])).flatten() },
  ),
  caption: [Fault injection on #get(S, "fault_injection", "n_questions") weather questions from the test set (A2 agent: tools, no retrieval). Transient = the first call fails, a retry works; persistent = every call fails. Source: `outputs/final/fault_injection.json` (`src/cloud/fault_injection.py`).],
)

#todo[Cloud paragraph.]

== Router and safety

#let sf = get(S, "safety")
#let rc = get(sf, "rules_plus_clf")
#let ro = get(sf, "rules_only")
#figure(
  table(
    columns: (2.2fr, 1fr, 1fr, 1fr, 1fr),
    align: (left, right, right, right, right),
    [*Red-team set (router: rules + classifier / rules only)*], [*Risky sent to cloud*], [*Emergency recognised*], [*Emergency number shown*], [*Controls over-escalated*],
    [v1: 51 Qs, written with the keyword lists], [#pc(get(rc, "redteam", "risky_recall")) / #pc(get(ro, "redteam", "risky_recall"))], [#pc(get(rc, "redteam", "emergency_escalation")) / #pc(get(ro, "redteam", "emergency_escalation"))], [#pc(get(rc, "redteam", "emergency_number_shown"))], [n/a],
    [v2: 54 + 15 controls, held out, *before* the keyword fix], [#pc(get(sf, "v2_before_keyword_fix", "rules_plus_clf", "risky_recall")) / #pc(get(sf, "v2_before_keyword_fix", "rules_only", "risky_recall"))], [#pc(get(sf, "v2_before_keyword_fix", "rules_plus_clf", "emergency_escalation")) / #pc(get(sf, "v2_before_keyword_fix", "rules_only", "emergency_escalation"))], [n/a], [n/a],
    [v2 after the keyword fix (now a dev set)], [#pc(get(rc, "redteam_v2_dev", "risky_recall")) / #pc(get(ro, "redteam_v2_dev", "risky_recall"))], [#pc(get(rc, "redteam_v2_dev", "emergency_escalation")) / #pc(get(ro, "redteam_v2_dev", "emergency_escalation"))], [#pc(get(rc, "redteam_v2_dev", "emergency_number_shown"))], [#pc(get(rc, "redteam_v2_dev", "control_over_escalation")) / #pc(get(ro, "redteam_v2_dev", "control_over_escalation"))],
    [*v3: 54 + 18 controls, held out (final)*], [*#pc(get(rc, "redteam_v3_heldout", "risky_recall"))* / #pc(get(ro, "redteam_v3_heldout", "risky_recall"))], [*#pc(get(rc, "redteam_v3_heldout", "emergency_escalation"))* / #pc(get(ro, "redteam_v3_heldout", "emergency_escalation"))], [*#pc(get(rc, "redteam_v3_heldout", "emergency_number_shown"))* / #pc(get(ro, "redteam_v3_heldout", "emergency_number_shown"))], [#pc(get(rc, "redteam_v3_heldout", "control_over_escalation")) / #pc(get(ro, "redteam_v3_heldout", "control_over_escalation"))],
  ),
  caption: [Router on the red-team sets. v2 was written by `gemini-3.5-flash-lite` and v3 by `gemini-3.5-flash`, each in Hindi, Hinglish and English, read item by item but not yet by a native speaker. "Emergency number shown" = routed emergency or high-risk, since both offline messages now show 108 / 112. Sources: `outputs/router_metrics.json`, `outputs/final/router_metrics_keywords_v1.json`.],
)

The v1 red-team set says the router is perfect. The held-out sets say otherwise. Written by other models, with vaguer wording ("कुछ काला सा काट लिया", "लाल वाली शीशी पूरी टंकी में उडेल दें"), v2 exposed missed emergencies (electric shock, an animal eating poisonous leaves) and banned products. After those were added to the keyword lists, the fresh v3 set gives the final picture. With the intent classifier, #pc(get(rc, "redteam_v3_heldout", "risky_recall"))% of risky questions still go to the cloud, but only #pc(get(rc, "redteam_v3_heldout", "emergency_escalation"))% of emergencies are recognised as emergencies; most of the others are routed as high-risk. Because the high-risk offline message now carries 108 / 112 as well (DECISIONS.md D18), #pc(get(rc, "redteam_v3_heldout", "emergency_number_shown"))% of v3 emergencies see an emergency number without a connection. One field-fire message was missed entirely. Rules alone would be far less safe (#pc(get(ro, "redteam_v3_heldout", "risky_recall"))% of risky questions). Safety costs cloud calls: #pc(get(rc, "redteam_v3_heldout", "control_over_escalation"))% of ordinary look-alike questions ("best time of day to spray") are also escalated.

On the test set, the router sends #pc(get(sf, "high_risk_label_sent_to_cloud"))% of the questions labelled high-risk to the cloud. The offline dose filter blocks every dose probe and no safe probe (miss rate #pc(get(sf, "filter_probes", "miss_rate"))%, false blocks #pc(get(sf, "filter_probes", "false_block_rate"))%\; #get(sf, "filter_probes", "n_dose") + #get(sf, "filter_probes", "n_safe") probes). Before the filter, #pc(get(sf, "B3_raw_dose_rate"))% of tuned answers and #pc(get(sf, "B2_raw_dose_rate"))% of base answers contain a dose; after it, #pc(get(sf, "offline_dose_rate_shown"))% of the answers shown offline do. In the cloud, the safety filter replaced an uncited quantity in #pc(get(cm, "B1", "safety", "uncited_dose_replaced_rate"))% of B1 answers and refused a banned product in #pc(get(cm, "B1", "safety", "banned_refused_rate"))%.

== Gate and H3

#let g3 = get(S, "gate", "B3")
#figure(
  table(
    columns: (1fr, auto, auto),
    align: (left, right, right),
    [*On the 700 test answers of B3*], [*Token probability*], [*Trained classifier*],
    [AUROC (higher is better)], [#num(get(g3, "token_prob", "auroc"))], [#num(get(g3, "classifier", "auroc"))],
    [AURC (lower is better)], [#num(get(g3, "token_prob", "aurc"))], [#num(get(g3, "classifier", "aurc"))],
    [ECE], [#num(get(g3, "token_prob", "ece"))], [#num(get(g3, "classifier", "ece"))],
    [Cloud-call rate at the calib cut], [#pc(get(g3, "token_prob", "cloud_call_rate"))], [#pc(get(g3, "classifier", "cloud_call_rate"))],
    [False keep (wrong answers kept offline)], [#pc(get(g3, "token_prob", "false_keep_rate"))], [#pc(get(g3, "classifier", "false_keep_rate"))],
    [Unnecessary send (correct answers sent)], [#pc(get(g3, "token_prob", "unnecessary_send_rate"))], [#pc(get(g3, "classifier", "unnecessary_send_rate"))],
    [Accuracy of the answers kept], [#pc(get(g3, "token_prob", "kept_accuracy"))], [#pc(get(g3, "classifier", "kept_accuracy"))],
    ..GROUPS.map(k => ([AUROC, #k], [#num(get(g3, "per_group_token_prob_auroc", k))], [#num(get(g3, "per_group_classifier_auroc", k))])).flatten(),
    [AUROC, answers that are not the deferral (n = #get(g3, "non_deferral", "n"))], [#num(get(g3, "non_deferral", "token_prob_auroc"))], [#num(get(g3, "non_deferral", "classifier_auroc"))],
  ),
  caption: [Gate quality. Label = the judge says the edge answer is correct. Classifier: logistic regression fitted on the #get(g3, "classifier", "fit_rows") dev answers; cut = the 50% quantile of calib confidences; reported on test. Paired bootstrap (2,000 resamples): the classifier beats token probability in #pc(get(S, "H3", "bootstrap", "p_classifier_better"))% of resamples, AUROC difference 95% CI #num(get(S, "H3", "bootstrap", "auroc_diff_ci95", 0)) to #num(get(S, "H3", "bootstrap", "auroc_diff_ci95", 1)). Source: `summary.json` (`gate`).],
)

#figure(
  stack(spacing: 6pt,
    image("figures/gate_riskcov_B3.png", width: 55%),
    image("figures/gate_riskcov_B3_by_lang.png", width: 100%)),
  caption: [Risk-coverage curves of the two gates on B3's test answers, overall and per language.],
)

*H3 is #yes(get(S, "H3", "met")).* The trained gate separates good from bad edge answers far better than the raw token probability (AUROC #num(get(g3, "classifier", "auroc")) vs #num(get(g3, "token_prob", "auroc"))), in every language, and the difference holds in every bootstrap resample. Token probability is not just weak but *inverted*: an AUROC below 0.5 means the model is most confident when it is wrong. The fitted coefficients say why. The strongest negative weights are the deferral flag (#num(get(g3, "classifier", "coef", "deferral"))) and the mean log-probability itself (#num(get(g3, "classifier", "coef", "mean_logprob"))). The model is surest of its memorised deferral and of short generic advice ("निराई करें", weed the field), and neither is ever judged correct. A harder test leaves out the deferrals: on the #get(g3, "non_deferral", "n") remaining answers the classifier still reaches #num(get(g3, "non_deferral", "classifier_auroc")) against #num(get(g3, "non_deferral", "token_prob_auroc")), so the gate does more than spot the template. Longer answers (#num(get(g3, "classifier", "coef", "log_chars"))) and Hinglish questions (#num(get(g3, "classifier", "coef", "hinglish"))) raise confidence; router-flagged high-risk questions lower it.

At the threshold set on calib, the trained gate sends #pc(get(g3, "classifier", "cloud_call_rate"))% of answers to the cloud and wastes only #pc(get(g3, "classifier", "unnecessary_send_rate"))% of the good ones, where the token-probability gate sent #pc(get(g3, "token_prob", "unnecessary_send_rate"))% of the good answers away. It still keeps #pc(get(g3, "classifier", "false_keep_rate"))% of the wrong answers, because with an edge accuracy near 10% even the confident half is mostly wrong (accuracy of kept answers #pc(get(g3, "classifier", "kept_accuracy"))%). The gate ranks well; the edge model is the limit.

== Hybrid and H1

#let hy = get(S, "hybrid")
#let to = get(S, "h1_tradeoff")
#figure(
  table(
    columns: (1fr, auto, auto, auto, auto),
    align: (left, right, right, right, right),
    [*Router, policy (B3 edge + B1 cloud, classifier gate)*], [*Accuracy*], [*% of B1*], [*Cloud calls*], [*H1*],
    ..if to == none { () } else { to.pairs().filter(((k, v)) => k != "frontier").map(((k, v)) => ([#k], [#pc(v.accuracy)], [#pc(v.pct_of_B1)], [#pc(v.cloud_rate)], [#yes(v.h1_met)])).flatten() },
  ),
  caption: [The H1 trade-off. "safety" = the design: everything the router calls high-risk, live-data or emergency goes to the cloud. "gate_all" lets high-risk questions through the gate, with the offline dose filter as their only guard. Rules only = no intent classifier. Source: `summary.json` (`h1_tradeoff`).],
)

#figure(image("figures/h1_frontier.png", width: 72%),
  caption: [Accuracy vs cloud-call rate as the gate cut moves from "send everything gated" to "keep everything gated", for each router and policy. Dashed: 90% of B1; dotted: 50% cloud calls.])

#todo[H1 paragraph; offline usefulness; R vs H; A1 vs H_tok; H_A2/H_A3.]

== Queue and connectivity (A4)

#let qq = get(S, "queue")
#figure(
  table(
    columns: (1fr, auto, auto, auto, auto, auto, auto),
    align: (left, right, right, right, right, right, right),
    [*Link trace, queue*], [*Delivered*], [*p50 wait*], [*p90 wait*], [*Stale (live data)*], [*Duplicate sends*], [*Accuracy*],
    ..if qq == none { () } else { qq.pairs().map(((k, v)) => ([#k.replace("Q_", "").replace("_A4", ", no queue (A4)")], [#pc(v.delivery_rate)], [#v.p50_ticks], [#v.p90_ticks], [#pc(v.stale_rate)], [#pc(v.duplicate_send_rate)], [#pc(v.accuracy)])).flatten() },
  ),
  caption: [Full hybrid (H) through the queue simulator: one question per minute, waits in minutes. A question whose answer never arrives counts as wrong. Traces are illustrative two-state link models (DECISIONS.md D9), not measured. Source: `summary.json` (`queue`).],
)

#todo[Queue paragraph.]

= Discussion

#todo[What worked, what did not, why.]

= Limitations

+ *The judge has not been checked against people.* Every accuracy rests on one LLM judge. Its agreement with a second LLM judge is reported above, but a 100-answer human check is still to be done (`reports/final/judge_check_sheet.csv`). The judge is stricter than the mid-submission's: absolute numbers are not comparable with the mid report, only differences between runs judged here.
+ *Noisy references.* The 700 test questions are graded against raw KCC answers, of which an LLM pre-check judged 42% wrong on the gold sample. This depresses every accuracy and favours answers that repeat KCC's habits. The gold subset (158) is cleaner but small and was cleaned by an LLM, not a person.
+ *Strict accuracy punishes safe deferrals.* A deferral to KCC 1551 is never "correct", so the tuned model and every safety rule are penalised for doing what the design asks. The lenient and deferral columns are reported for this reason.
+ *Translated Hindi.* Hindi test questions are IndicTrans2 translations of English operator summaries; only Hinglish is farmers' own text. BhashaBench-Krishi is also the machine-translated subset.
+ *Synthetic safety and retrieval sets.* Red-team v2/v3 and the Recall\@5 queries were written by LLMs and read by an LLM assistant, not by a native Hindi speaker. Synthetic retrieval queries reuse document wording, so Recall\@5 is an upper bound.
+ *Snapshots, not live data.* Tools read weather snapshots dated 2026-10-30. There are no mandi-price snapshots (no data.gov.in key), so price questions get "unavailable", and the scheme facts were written from memory.
+ *Models changed for quota reasons.* The final cloud agent and judge are Gemma 4 models on the free Gemini-API tier, not the proposal's Gemini Flash; A3 covers a stratified half of the test set (DECISIONS.md D29).
+ *Simulated connectivity.* The good / patchy / poor link traces are illustrative two-state models, not measured rural networks, and phone speed was measured on laptop and server CPUs, not on a phone.
+ *Corpus chunking.* Eleven corpus chunks are 10-46k characters long because some documents were split badly; the source block is capped (D28), but re-chunking would improve retrieval.

= Reproducibility

Every number in this report is in `outputs/final/summary.json` or another file named in a caption; `scripts/final_pipeline.sh` lists the commands that produce them, in order, and `python -m src.eval.run_final` rebuilds `summary.json`, the tables and the figures from the saved answers and judge labels without any model call. Model calls are cached (`cache/gemini.sqlite`, `outputs/cache/judge_cache.jsonl`). GPU work is in `kaggle/jobs/` (06: B2/B3 and BhashaBench, 07: seed re-runs, 08: GGUF). Design decisions, including those made for the final phase (D17-D29), are in `docs/kiran/DECISIONS.md`. Code: https://github.com/roshanned/kisan_edge; data and outputs: https://huggingface.co/datasets/kisan-edge/kisan-edge-data.

= Contributions

The project was planned as four workstreams (PLAN.md): data and evaluation (Anushka Sharma), edge model (Roshan K), cloud side (Sai Rithvik), and router, gate, queue and integration (Kiran R). Up to the mid-submission each person worked on their layer and checked a batch of gold questions. From October 30, Roshan K carried the whole project. The final phase described here (full-test runs of every system, the trained gate, red-team v2 and v3, the cloud metrics, the GGUF export, the analysis pipeline and this report) was carried out by Roshan K with an AI coding assistant (Claude), which wrote much of the code and this draft and read the generated red-team items. Where a step needed a human and none was available, the report says so: the gold set and the red-team sets were checked by an LLM, not by a native Hindi speaker, and the LLM judge has not yet been checked against human labels.
