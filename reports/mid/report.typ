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

Every component of the proposed architecture now has working code, and the data, split and gold set are frozen. The edge model is chosen (Llama-3.2-3B-Instruct) and fine-tuned with QLoRA; the cloud agent answers with tools; the router, safety filter, gate and queue run on real questions.  
#figure(
  table(
    columns: (auto, auto, 1fr),
    align: (left, left, left),
    [*Component*], [*State*], [*What remains*],
    [Data, split, gold set], [Done; split frozen], [Human check of the 200 gold questions],
    [Evaluation (LLM judge, scoring, reports)], [Done], [Judge-vs-human agreement on 100 labels],
    [Edge model: pilot, QLoRA, generation with logprobs], [Done; B2, B3 run], [Re-runs, 4-bit GGUF export, CPU speed test],
    [Rule router and offline dose filter], [Done], [Independent red-team set],
    [Confidence gate], [Token-probability gate done], [Trained classifier gate on dev/calib (H3)],
    [Offline queue and connectivity simulator], [Done], [Measured (not illustrative) link traces],
    [Cloud agent: tools, safety filter], [Done; A2 run], [RAG corpus (200-400 documents), then B1, A3],
    [Mandi price tool], [Code done], [data.gov.in key and price snapshots],
  ),
  caption: [Status of each component on Oct 30.],
)

= Datasets

== Sources

The main dataset is the cleaned Kisan Call Centre (KCC) data for Uttar Pradesh, restricted to four crops (wheat, paddy, mustard, sugarcane). We use the public KCC 1M-row sample because those files were already cleaned with the shared rules.

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

The split was made once, with a fixed seed, and then frozen. A question text, together with the English source of a translated Hindi question, occurs in exactly one split, because KCC contains many rows with identical questions and a row-level random split would leak test questions into training. The pilot questions used to choose the edge model are all in the dev split.

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

The gold set has 200 questions drawn from the frozen test split: 70 Hindi, 70 Hinglish and 60 English, stratified by category. They were dealt into four batches of 50 with the same language and category mix, to be checked against four questions: is the question clear, is the reference answer correct, are the language and category tags right, and should the row be dropped. Every Phase 1 result is reported on the checked set.

*How the gold set was actually checked.* For the mid-submission, all 200 candidates were first pre-checked by an LLM (Claude) against the same criteria, and the 42 rows it flagged (11 unusable, 6 with a wrong reference it could not safely fix, 25 where it was unsure) were reviewed by a team member and dropped. The remaining 158 rows keep the AI pre-check's corrections: 60 reference answers replaced and 35 categories changed, mostly from general to high-risk because the reference contains a dose. These 158 rows are marked `check_method = ai_precheck`, not human-checked; a full human check is planned for the final submission.

#figure(
  table(
    columns: (auto, auto, auto, auto, auto),
    align: (left, right, right, right, right),
    [], [*Hindi (Devanagari)*], [*Hinglish*], [*English*], [*Total*],
    [Candidates], [70], [70], [60], [200],
    [Kept], [61], [47], [50], [*158*],
  ),
  caption: [Gold set after the pre-check. Kept rows by category: 76 high-risk, 50 general, 32 live-data.],
)

The pre-check is itself a finding: it judged *83 of the 200 KCC reference answers (42%) wrong*. The commonest faults were dated weather forecasts given as the answer (about 25 rows), answers to a different question (a jackal problem answered with an insecticide, a weather query answered with a fertiliser dose), doses about twice the label rate, and wrong products (a fungicide for an insect pest). KCC answers cannot be used as gold without checking.

== Known limitations

+ *The Hindi questions are machine translated.* Only 11 of 33,556 KCC rows have a natively Devanagari question; the others are English operator summaries translated with IndicTrans2. The expert answers are native Hindi. Hindi results therefore measure translated-question Hindi; Hinglish questions are genuine farmer text.
+ *The data are not the most recent ones.* The Hinglish rows are from 2012-2017 and the others from 2019-2023, not 2024-25.
+ *English data are thin.* KisanVaani contributes only 11 usable rows, so English comes mostly from KCC rows with English answers, many of them mandi price look-ups.
+ *KCC questions and answers are noisy*: typos, mislabelled query types, and terse answers. The checked gold set and per-slice reporting are the mitigation.
+ *Live-data references are stale snapshots.* The judge is told not to penalise different numbers on these questions.
+ *The test mix is balanced by language and category rather than natural*, so absolute accuracies are not comparable to a random sample of KCC.
+ The crop-recommendation exact-match metric from the proposal is dropped, since no dataset exists for it.

= Evaluation method

Each answer is labelled correct, partly correct or wrong against the KCC expert answer by an LLM judge (`gemini-3.1-flash-lite`, temperature 0, JSON output; a different model from the cloud agent's). The same judge is used for every run so that results are comparable, and every response is cached so no item is judged twice. The judge also records whether an answer is a deferral (declines to answer or points to a helpline), which is reported separately rather than forced into a label. For live-data questions the judge is told the reference is a past snapshot and gives credit for the right kind of information or the right source.

To check whether the judge can be trusted, a stratified sample of judged answers is relabelled by hand without seeing the judge's label, and we report exact agreement, agreement on wrong versus not-wrong, and Cohen's kappa overall and per language.

// *Not done for the mid-submission.* The scripts are ready (`src/eval/judge_check.py`); the hand-labelling of a stratified sample of 100 judged answers is scheduled for Phase 2. Until then the judge's labels are unvalidated, and small differences between runs should be read with that in mind.

Results are reported per language and script. Accuracy is the share of answers labelled correct, with 95% Wilson confidence intervals; "lenient" accuracy counts partly correct answers as well.

= Baseline experiments

All runs are on the 158 gold questions and scored by the same judge.

- *B2, small base.* Llama-3.2-3B-Instruct (ungated `unsloth` copy), fp16 on a Kaggle T4, greedy decoding, at most 200 new tokens, a one-line system prompt in the question's language. Token log-probabilities are saved for the gate.
- *B3, small tuned.* The same model with a QLoRA adapter (rank 16, alpha 32, all attention and MLP projections, 4-bit NF4 base, learning rate 2e-4, 2 epochs, on a T4). Training data: 4,641 examples from the frozen train split only, with the safety rules of the edge section (no dose in any target; live-data and dose questions answered with a fixed deferral). Validation loss fell from 1.21 to 1.09. Generation adds an n-gram repetition limit.
- *Cloud reference (A2).* `gemini-3.5-flash-lite` with the weather, mandi-price and scheme tools on frozen 2026-10-30 snapshots and the cloud safety filter, but no retrieval.

#figure(
  table(
    columns: (auto, auto, auto, auto, auto, auto),
    align: (left, right, right, right, right, right),
    [*Run*], [*Hindi*], [*Hinglish*], [*English*], [*All (correct)*], [*All (lenient)*],
    // [B1 cloud, retrieval + tools], [not run], [not run], [not run], [not run], [not run],
    [A2 cloud, tools only], [54.1], [46.8], [38.0], [*46.8*], [96.8],
    [B2 small base], [1.6], [0.0], [4.0], [1.9], [41.1],
    [B3 small tuned], [6.6], [14.9], [10.0], [10.1], [58.9],
  ),
  caption: [Share (%) of gold questions judged correct, per language; lenient also counts partly correct. n = 61 Hindi, 47 Hinglish, 50 English. 95% Wilson intervals are in `reports/mid/tables/by_language.md`; for n of about 50 they are roughly ±13 points.],
)

The base model almost never answers correctly: it writes long generic essays (178 tokens on average) and shows a pesticide or fertiliser dose in 12 answers. The tuned model answers in KCC's short style (64 tokens), shows *no* dose in any answer, and defers 50.6% of questions with the safe message, all of them dose or live-data questions. Its strict accuracy stays low because a deferral is never judged "correct" against a reference that gives the dose; the lenient score, which credits the right advice without the exact numbers, rises by 18 points.

= Ablations

The hybrid runs route every gold question with the rule router and intent classifier (71 high-risk, 33 live-data, 54 general). High-risk and live-data questions always go to the cloud; for general questions the token-probability gate keeps the edge answer or sends the question to the cloud at a 50% target rate. Since B1 is not run yet, A2 is the cloud part of every hybrid. Hybrid scores are composed from the judge labels of the edge and cloud answers they contain, so no answer is judged twice.

#figure(
  table(
    columns: (auto, auto, auto, auto, auto, auto),
    align: (left, right, right, right, right, right),
    [*Run*], [*Hindi*], [*Hinglish*], [*English*], [*All*], [*Cloud calls / 100*],
    [H: hybrid, tuned edge + A2], [49.2], [44.7], [34.0], [*43.0*], [82.9],
    [A1: hybrid, base edge + A2], [47.5], [38.3], [32.0], [39.9], [82.9],
    [R: random routing, tuned edge + A2], [45.9], [46.8], [28.0], [40.5], [82.9],
    [A2: cloud only, no retrieval], [54.1], [46.8], [38.0], [46.8], [100],
  ),
  caption: [Hybrid ablations on the gold set: share (%) judged correct. In all three hybrids the edge answers 27 of 158 questions.],
)

- *A1 (no fine-tuning).* Swapping the tuned edge model for the base model costs 3.1 points overall, and the offline dose filter has to block 10 base-model answers against 1 tuned answer: fine-tuning moves the safety work from the filter into the model.
- *A2 (no retrieval).* Reported above as the cloud reference; the retrieval ablation proper needs B1.
- *R (random routing).* Random routing at the same cloud-call rate is 2.5 points below the gated hybrid. With only 27 edge-answered questions this difference is well within noise, so the mid-submission gives no evidence yet that the gate beats chance.
- *A3 (no tools) and A4 (no queue)* need B1 and the full test set; they are planned for the final submission. The queue simulator alone delivers 100% / 99.8% / 67.1% of cloud-bound test questions on good / patchy / poor links, against 98% / 58% / 14% without the queue.

= Results

#figure(
  image("figures/accuracy_by_language.png", width: 100%),
  caption: [Share of gold questions judged correct, per run and language.],
)

*H2 (fine-tuning adds at least 10 points on Hindi): not met yet.* On the Hindi (Devanagari) gold questions the tuned model gains 5.0 points (1.6% to 6.6%), and 8.2 points over all languages (1.9% to 10.1%); on Hinglish it gains 14.9 points. On the lenient measure it gains 17.8 points overall. Two things hold the strict number down: half of the tuned answers are deliberate safety deferrals, which the judge never labels correct, and the training set from the frozen split is small (4,641 examples). The planned re-runs will test more data and epochs, and we will also report accuracy on non-deferred answers.

*H1 (hybrid at least 90% of cloud-only accuracy with at most 50% cloud calls): half met.* The hybrid reaches 43.0% against 46.8% for cloud only, 92% of it, but sends 82.9 of every 100 questions to the cloud. The cause is the fixed safety rules, not the gate: 104 of 158 gold questions are high-risk or live-data and are never answered offline. The team's position is to keep safety first and report the cloud rate honestly; the alternative, narrowing what counts as high-risk, would trade safety for fewer cloud calls.

*Gate (H3 sub-question): raw token probability does not work.* Over the tuned model's answers, mean token log-probability has an AUROC of 0.18 for predicting a correct answer, worse than chance. The reason is visible in the data: the model is most confident on its memorised safety deferral (mean log-probability -0.07 against -0.68 for other answers), and those are never labelled correct. Even without deferrals the AUROC is 0.38 (78 answers, only 16 correct). This supports the proposal's expectation that small models are over-confident and motivates the trained classifier gate (H3), which needs edge answers and judge labels on the dev and calibration splits; those runs are planned for Phase 2.

*Safety.* The tuned model shows no dose in any of its 158 answers (base: 12); the offline filter blocked 1 tuned answer that slipped through. The router sends 90% of high-risk test questions to the cloud.

= Challenges faced

== Data and evaluation

- *Noisy labels and answers.* The limitations are listed in the section above elaborately.
- *Translated Hindi.* Few native Devanagari questions exist, so Hindi test questions are translations. We keep the original English text with each record so the effect can be inspected.
- *Leakage through repeated questions.* KCC repeats the same question many times with different answers; splitting by question text instead of by row avoids test questions appearing in training.
- *Judge cost and reliability.* Free-tier API quota limits judging volume; we cache all responses, moved the judge to a second model when the first model's daily quota ran out.

== Edge model
- *Base models do not answer.* In the 100-question Hindi pilot, Qwen3-1.7B, Llama-3.2-1B and Llama-3.2-3B all replied in Hindi but wrote 200-token generic essays and invented variety names; none gave the KCC-style specific answer. Qwen3-1.7B also looped and was the most confident when wrong, which is bad for a probability-based gate; Llama-3.2-1B's Hindi broke down most. We chose Llama-3.2-3B (about 2 GB at 4 bits).
- *Doses in the training targets.* KCC labels are noisy, so many "general" answers contain pesticide or fertiliser doses. Any training answer with a number next to a unit (including Hindi units such as किग्रा) is replaced by a fixed safe deferral, whatever its label, so the phone model never learns to give doses. Safe deferrals are capped at 25% of the training set so the model does not learn to defer everything.
- *Looping and vague answers after tuning.* In the pilot run, 10 of 100 tuned answers repeated a list ("वरदान-2, वरदान-3, ..."); generation now uses an n-gram repetition limit. Some pest questions get a vague "निराई करें" (weed the field); the gate is expected to score these low.
- *Tooling.* IndicTrans2's model code breaks on current `transformers`, so translation runs on version 4.46.3 and the edge model on 4.51 or later. Kaggle does not pass secrets to jobs started from the command line, so all training uses ungated model copies.

== Cloud side
- *Model availability.* All cloud runs use `gemini-3.5-flash-lite` (about 1.5 seconds per call), the Flash-Lite fallback named in the proposal. The free tier allows 500 requests per day per model, and the cloud runs used that model's quota, so the judge runs on a different model, `gemini-3.1-flash-lite`. Using a separate judge model also avoids the cloud model grading its own answers.
- *Gemini 3 function calling.* Newer models reject a follow-up request unless each tool call carries its `thought_signature`; the client now keeps and returns it.
- *No retrieval corpus yet.* Government sites could not be scraped, so the 200-400 trusted documents must be downloaded by hand. B1 (retrieval and tools) is therefore not run; A2 (tools, no retrieval) is reported instead.
- *Safety filter false positives.* The cloud safety filter replaced at least one weather answer with a "ask KCC for the exact quantity" deferral, apparently reading rainfall in millimetres as a dose.

== Router, gate and queue
- *Forced-cloud share.* Live-data and high-risk questions always go to the cloud, so 66-85% of gold questions never reach the gate. This makes the H1 target of at most 50% cloud calls hard to meet; we report the real rate.
- *Router.* Rules alone catch only 7% of high-risk questions; the TF-IDF classifier trained on KCC query types raises high-risk recall to 90% on test. The red-team set (51 questions, 100% recall) was drafted together with the keyword lists, so it is an upper bound.
- *Simulator realism.* Link traces (good, patchy, poor) are illustrative, not measured.

= Mitigation plans

#figure(
  table(
    columns: (auto, 1fr, auto),
    align: (left, left, left),
    [*Risk*], [*What happened and what we do*], [*Status*],
    [Cloud quota], [Every response is cached and runs resume after a quota stop; switched to Flash-Lite after the newer Flash model proved too slow.], [Applied],
    [Noisy KCC labels and answers], [AI pre-check of all 200 gold questions found many wrong references; human review of every flagged row; dose check on every training answer; per-slice reporting.], [In progress],
    [Poor Hindi or Hinglish quality], [Hindi questions are IndicTrans2 translations of English summaries; the English source is kept with each record. Native Hinglish is kept as typed.], [Applied],
    [Poor small-model Hindi], [Pilot of three models; Llama-3.2-3B chosen for coherent Hindi. Tuning removes the essay style.], [Applied],
    [Weak gate (AUROC below 0.7)], [Stricter fixed rules already send most questions to the cloud; we will report the trade-off if the trained gate stays weak.], [Pending results],
    [Mandi API failure], [Tools read frozen snapshots only; prices need a data.gov.in key.], [Pending],
    [No retrieval corpus (new)], [Download the trusted documents by hand; run B1 and A3 once indexed. A2 stands in for now.], [Pending],
  ),
  caption: [Risks and mitigations, updated.],
)

= Timeline to final

#figure(
  table(
    columns: (auto, 1fr),
    align: (left, left),
    [*When*], [*What*],
    [Oct 31 - Nov 6], [Retrieval corpus (200-400 documents) and index; B1, A3 on the gold set; mandi snapshots; QLoRA re-runs; B2/B3 on dev and calibration for the trained gate; finish the human gold check.],
    [Nov 7 - Nov 13], [Full 700-question test runs of every baseline and ablation; trained gate (H3), risk-coverage curves, H1 verdict; Recall\@5, citation and tool metrics, fault injection; 4-bit GGUF export and laptop-CPU speed test; BhashaBench-Krishi Hindi; judge-vs-human agreement on 100 labels.],
    [Nov 12], [All scores in.],
    [Nov 14], [Code freeze; Report making.],
    [Nov 15], [Final report and submission.],
    // [Nov 16 - 19], [Evaluations.],
  ),
  caption: [Plan to the final submission.],
)

= Code and repository

Code: https://github.com/roshanned/kisan_edge (tag `mid-submission`). Processed data, translations and model outputs: https://huggingface.co/datasets/kisan-edge/kisan-edge-data.

- `src/data`: cleaning, IndicTrans2 translation, the frozen split. `src/eval`: judge, scoring, reports.
- `src/edge`: model pilot, generation with token logprobs, training-data builder with the safety rules, QLoRA training.
- `src/router_gate`, `src/queue_sim`: router, offline dose filter, gate, queue simulator and hybrid runner.
- `src/cloud`: Gemini client, agent loop, tools, cloud safety filter, retrieval.
- `kaggle/`: GPU jobs (training, B2/B3), run from the command line.

Reproduction steps for data and evaluation are in `dev.md`; guides for the cloud and router layers are in `docs/`.
