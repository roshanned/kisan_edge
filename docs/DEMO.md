# Demo script (Nov 16-19 evaluation, about 6 minutes)

Everything runs on the laptop: the 4-bit edge model through llama.cpp on the CPU, the router, filter, gate and queue in Python, and the cloud agent through the Gemini API (needs internet and `GEMINI_API_KEY`).

**Before the session (5 min):**
```bash
.venv/Scripts/activate
python -m src.demo "test" --offline        # starts llama-server once and warms the model (about 10 s)
rm -f outputs/demo_queue.jsonl             # start with an empty queue
```
Open `reports/final/report.pdf` at the summary table, and `reports/final/figures/h1_frontier.png`.

## 1. A general question, answered on the phone (1 min)
```bash
python -m src.demo "gehu ki buvai ka sahi samay kya hai" --district Kheri
```
Say: the router calls it general; the 3B model answers on the CPU in about 4 seconds; the dose filter passes; the gate's confidence is above the cut learnt on the calibration split, so the answer stays offline. No network needed.

## 2. A dose question: never answered offline (1 min)
```bash
python -m src.demo "dhan me tana chhedak ke liye kitni dawa dalein ek acre me" --district Bareilly --offline
```
Say: high-risk route; even if the small model wrote a quantity, the filter would block it. Offline, the farmer gets a safe message (ask KCC 1551; the emergency numbers if someone is hurt) and the question is queued.

## 3. An emergency (30 s)
```bash
python -m src.demo "bachche ne galti se keetnashak pee liya hai" --offline
```
Say: 108 / 112 / KCC 1551 appear at once, with no network. Mention the held-out red-team result: half of indirectly worded emergencies were routed as high-risk rather than emergency, so the high-risk message now shows the numbers too (report, Router and safety).

## 4. Back online: the queue drains (1.5 min)
```bash
python -m src.demo "Bareilly mein agle 3 din mausam kaisa rahega, gehu bona hai" --district Bareilly --offline
python -m src.demo --flush
```
Say: queued questions go out in priority order (emergency, high-risk, live data, general). Name the place in the weather question: when it is missing the agent calls the weather tool only about 70% of the time (report, cloud metrics). Expect about 30 s per cloud answer; the rain-chance sentence may be replaced by a KCC deferral, a known false positive of the cloud dose filter (report, Limitations). The cloud agent retrieves documents and cites them, calls the weather tool for the farmer's district (snapshot dated 2026-10-30), and its own filter removes any dose that no retrieved source supports.

## 5. Results (2 min)
Show the summary table (H1, H2, H3) and the H1 trade-off figure. Key messages:
- What the hybrid achieves relative to cloud-only, and why the cloud-call target collides with the safety rules (most test questions are high-risk or live-data by design).
- What fine-tuning did: shorter, safer answers in the right language, but limited strict accuracy (the deferral template is never "correct").
- Whether the trained gate beats raw token probability (raw confidence is anti-correlated with correctness because the model is surest of its deferral template).

**If the network fails:** sections 1-3 work fully offline. Section 4 needs the API; skip to the results.
