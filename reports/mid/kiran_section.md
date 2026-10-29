# Router, gate and queue (draft for the mid report; Kiran to edit)

*Numbers below are real unless marked TBD. Everything marked TBD needs B1/B2/B3 outputs and Anushka's judge scores.*

**Router.** Questions are routed to `emergency`, `high_risk`, `live_data` or `general` by hand-written keyword lists
(Devanagari, Hinglish, English) with emergency rules (108 / 112 / KCC 1551), then by a TF-IDF + logistic-regression intent
classifier trained on the train split only for questions no rule matches. Everything except `general` goes to the cloud.
On the test split the router matches the first-pass labels 80.1% of the time (Hindi 89.3%, Hinglish 72.8%, English 74.0%) and
sends 90.0% of high-risk-labelled questions to high_risk/emergency (rules alone: 7.2%, so the classifier is what covers
KCC's broad "Plant Protection" label). On our 51-question red-team set recall is 100%, but the set was drafted together with
the keyword lists, so this is an upper bound; an independent set is TBD.

**Offline safety filter.** A rule filter blocks any edge answer containing a number next to a unit (ASCII or Devanagari digits),
a spelled-out number next to a unit, or a spoken measure ("do chammach"), and replaces it with a deferral while the
question is sent to the cloud. On 22 dose and 11 safe probes: miss rate 0/22, false blocks 0/11. Probes are small and
need to be re-checked on real B3 answers (TBD).

**Gate.** Token-probability gate (mean log-prob) and a logistic-regression gate (log-prob features, answer length, script, crop
known, category) over `general` questions. AUROC, AURC, ECE, false-keep and unnecessary-send rates, risk-coverage curves,
H3: **TBD** (needs `edge_*.jsonl` and `scores_B3.jsonl`).

**Queue and simulator.** Priority queue (emergency first), dedup, retry with exponential back-off, dated cache and stale re-ask for
weather/prices, run over simulated good / patchy / poor links (parameters are illustrative, not measured). On the test split's
583 cloud-bound questions: delivery 100% / 99.8% / 67.1% with the queue and 98% / 58% / 14% without it (A4); p50 / p90
time-to-answer 0 / 0, 5 / 50 and 767 / 1973 simulated minutes for good / patchy / poor.

**Challenges.** (1) Forced-cloud share: with always-cloud for live_data and high_risk, 66-85% of gold questions never reach
the gate, which makes H1's 50% cloud-call target hard to meet; we report the real rate. (2) KCC has almost no emergency
examples, so emergency routing is rules only. (3) The router labels are noisy KCC QueryType guesses.

**Not done / TBD:** R, A1, full hybrid, A4 accuracy, H1, H3, safety metrics on real outputs. See `docs/kiran/MANUAL_TODO.md`.
