#set document(title: "Kisan-Edge: Mid-submission report")
#set page(paper: "a4", margin: 2.2cm, numbering: "1")
#set text(font: ("Libertinus Serif", "Noto Sans Devanagari"), size: 10.5pt)
#set par(justify: true)
#set heading(numbering: "1.1")
#show table: set text(size: 9pt)
#show figure.caption: set text(size: 9pt)

// Placeholder box for sections that other team members still have to write.
#let todo(body) = block(fill: luma(240), inset: 8pt, radius: 3pt, width: 100%)[
  #text(fill: rgb("#a33"), weight: "bold")[TODO] #body
]

#align(center)[
  #text(size: 18pt, weight: "bold")[Kisan-Edge] \
  #text(size: 12pt)[A phone-sized farm advisor with a cloud fallback] \
  #v(2pt)
  Mid-submission report · LMA group project · Oct 30, 2026
]

= Progress summary

#todo[Short summary of what is built against the architecture in Figure 1 of the proposal (edge model, router, gate, queue, cloud agent, evaluation). One paragraph plus a status table: component, state, what remains.]

= Datasets

== Sources

The main dataset is the cleaned Kisan Call Centre (KCC) data for Uttar Pradesh, restricted to four crops (wheat, paddy, mustard, sugarcane). We use the public KCC 1M-row sample rather than a fresh KCC 2024-25 download; this is a deviation from the proposal, taken to save time because those files were already cleaned with the shared rules.

#figure(
  table(
    columns: (auto, auto, 1fr),
    align: (left, right, left),
    [*Source*], [*Rows*], [*Used as*],
    [KCC sample, Hinglish questions], [9,432], [Hinglish test/train questions, used as typed],
    [KCC sample, English summaries with native Hindi expert answer], [20,883], [Hindi questions: the English summary translated with IndicTrans2],
    [KCC sample, English summaries with English answer], [5,662], [English questions],
    [KCC sample, English summaries with Hinglish answer], [7,000], [Dropped: would reward replying in the wrong language],
    [KisanVaani English Q-A], [2,328], [Only the 11 rows on our crops are used],
  ),
  caption: [Input files and how each is used. Data are on the public Hugging Face dataset `kisan-edge/kisan-edge-data`.],
)

== Cleaning and labelling

- Uttar Pradesh rows and the four crops only; phone numbers replaced by a placeholder; HTML-encoded Hindi decoded; corrupted and very short rows dropped.
- Script tag: Hindi in Devanagari, Hinglish (romanised Hindi), or English.
- Category tag: general, live-data (weather, prices, schemes), high-risk (doses, pesticides, credit), emergency. The KCC query type is noisy (weather questions tagged as plant protection), so keyword rules override it. The router labels (see the router section) are the final labels.
- One record per distinct question text and language, after normalising case, spaces and trailing punctuation. This removes, for example, 5,215 copies of the same weather question.

== Splits

The split was made once, with a fixed seed, and then frozen; the script refuses to run again and a hash of the test ids is stored in the repository. A question text, together with the English source of a translated Hindi question, occurs in exactly one split, because KCC contains many rows with identical questions and a row-level random split would leak test questions into training. The 100 pilot questions used to choose the edge model are all in the dev split.

#figure(
  table(
    columns: (auto, auto, auto, auto, auto),
    align: (left, right, right, right, right),
    [*Split*], [*Hindi (Devanagari)*], [*Hinglish*], [*English*], [*Total*],
    [test], [300], [250], [150], [*700*],
    [calibration], [250], [200], [150], [600],
    [dev], [300], [200], [100], [600],
    [train], [8,424], [5,871], [2,140], [16,435],
  ),
  caption: [Questions per split and language/script. Test, calibration and dev are balanced across languages; train is the remainder.],
)

Within each language and split, 40% of the questions are general, 40% high-risk and 20% live-data. Live-data answers depend on the date (old weather, old mandi prices), so they are capped; high-risk is kept large for the safety metrics. The test set has 280 general, 280 high-risk and 140 live-data questions, and by crop 271 wheat, 244 paddy, 101 sugarcane and 84 mustard.

== Gold set

The gold set has 200 questions drawn from the frozen test split: 70 Hindi, 70 Hinglish and 60 English, stratified by category. They were dealt into four batches of 50 with the same language and category mix, and each team member checked one batch: is the question clear, is the reference answer correct, are the language and category tags right. Rows that failed were fixed or dropped. Every Phase 1 result is reported on this set.

#todo[Fill in after the sheets are merged: how many gold questions were kept, fixed and dropped, and by whom they were checked.]

== Known limitations

+ *The Hindi questions are machine translated.* Only 11 of 33,556 KCC rows have a natively Devanagari question; the others are English operator summaries translated with IndicTrans2. The expert answers are native Hindi. Hindi results therefore measure translated-question Hindi; Hinglish questions are genuine farmer text.
+ *The data are older than proposed.* The Hinglish rows are from 2012-2017 and the others from 2019-2023, not 2024-25.
+ *English data are thin.* KisanVaani contributes only 11 usable rows, so English comes mostly from KCC rows with English answers, many of them mandi price look-ups.
+ *KCC questions and answers are noisy*: typos, mislabelled query types, and terse answers. The hand-checked gold set and per-slice reporting are the mitigation.
+ *Live-data references are stale snapshots.* The judge is told not to penalise different numbers on these questions.
+ *The test mix is balanced by language and category rather than natural*, so absolute accuracies are not comparable to a random sample of KCC.
+ The crop-recommendation exact-match metric from the proposal is dropped, since no dataset exists for it.

= Evaluation method

Each answer is labelled correct, partly correct or wrong against the KCC expert answer by an LLM judge (Gemini, temperature 0, JSON output). The same judge is used for every run so that results are comparable, and every response is cached so no item is judged twice. The judge also records whether an answer is a deferral (declines to answer or points to a helpline), which is reported separately rather than forced into a label. For live-data questions the judge is told the reference is a past snapshot and gives credit for the right kind of information or the right source.

To check whether the judge can be trusted, a stratified sample of judged answers is relabelled by hand without seeing the judge's label, and we report exact agreement, agreement on wrong versus not-wrong, and Cohen's kappa overall and per language.

#todo[Fill in after the check: number of rows labelled, agreement, kappa, and what kinds of disagreement occur.]

Results are reported per language and script. Accuracy is the share of answers labelled correct, with 95% Wilson confidence intervals; "lenient" accuracy counts partly correct answers as well.

= Baseline experiments

#todo[B1 (cloud only), B2 (small base model) and B3 (small tuned model) on the gold set, with accuracy per language. Each owner adds a short description of their run: model, prompt, settings, cost.]

#figure(
  table(
    columns: (auto, auto, auto, auto, auto),
    align: (left, right, right, right, right),
    [*Run*], [*Hindi*], [*Hinglish*], [*English*], [*All*],
    [B1 cloud only], [TBD], [TBD], [TBD], [TBD],
    [B2 small base], [TBD], [TBD], [TBD], [TBD],
    [B3 small tuned], [TBD], [TBD], [TBD], [TBD],
  ),
  caption: [Share of gold questions judged correct, per language. To be filled from `reports/mid/tables/by_language.md`.],
)

= Ablations

#todo[A1 (hybrid with the base model), A2 (no retrieval) and R (random routing at the same cloud-call rate, as a sanity check of the gate). Short table plus one paragraph each.]

= Results

#todo[Summary table, risk-coverage plot of the gate, and the first H2 result (tuned versus base on Hindi).]

#figure(
  rect(width: 100%, height: 5cm, stroke: (dash: "dashed"))[#align(center + horizon)[Accuracy by language and run (`figures/accuracy_by_language.png`)]],
  caption: [Placeholder for the accuracy plot.],
)

= Challenges faced

== Data and evaluation

- *Noisy labels and answers.* See the limitations above. We deduplicated by question text, hand-checked a gold subset and report by slice.
- *Translated Hindi.* Few native Devanagari questions exist, so Hindi test questions are translations. We keep the original English text with each record so the effect can be inspected.
- *Leakage through repeated questions.* KCC repeats the same question many times with different answers; splitting by question text instead of by row avoids test questions appearing in training.
- *Judge cost and reliability.* Free-tier API quota limits judging volume; we cache all responses and check the judge against human labels.

== Edge model
#todo[Hindi quality, VRAM, training time, looping outputs.]

== Cloud side
#todo[API quota, retrieval quality, tool failures.]

== Router, gate and queue
#todo[Gate quality, safety filter misses, simulator realism.]

= Mitigation plans

#todo[From section 13 of the proposal, updated with what actually happened. Each owner adds the mitigations for their own challenges above.]

= Timeline to final

#todo[Copy from the Phase 2 section of the project plan: dates, owners and the code freeze on Nov 14; submission on Nov 15.]

= Code and repository

#todo[GitHub link, the `mid-submission` tag, and a short guide to the repository layout. Reproduction steps for the data and evaluation parts are in `dev.md`.]
