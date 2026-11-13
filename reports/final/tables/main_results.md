| Run | What | Hindi | Hinglish | English | All (strict) [95% CI] | All (lenient) | Deferred | Cloud calls /100 |
|---|---|---|---|---|---|---|---|---|
| B2 | edge base | 2.7 | 4.0 | 11.3 | 5.0 [3.6-6.9] | 15.0 | 4.4 | 0 |
| B3 | edge tuned | 9.7 | 7.2 | 12.7 | 9.4 [7.5-11.8] | 17.0 | 48.6 | 0 |
| B1 | cloud: LLM + RAG + tools | 32.0 | 26.4 | 25.3 | 28.6 [25.4-32.0] | 47.0 | 31.9 | 100 |
| A2 | cloud without RAG | 31.0 | 21.6 | 22.0 | 25.7 [22.6-29.1] | 44.4 | 71.1 | 100 |
| A3 | cloud without tools (350-question stratified half) | 19.3 | 17.6 | 18.7 | 18.6 [14.8-23.0] | 34.9 | 38.3 | 100 |
| H | hybrid (B3 + B1) | 32.0 | 22.4 | 29.3 | 28.0 [24.8-31.4] | 47.0 | 24.9 | 74.6 |
| H_tok | hybrid (B3 + B1), token-prob gate | 31.0 | 24.8 | 20.7 | 26.6 [23.4-30.0] | 44.3 | 35.9 | 92.0 |
| R | random routing, same cloud rate | 32.0 | 22.4 | 24.7 | 27.0 [23.8-30.4] | 45.0 | 30.0 | 74.4 |
| A1 | hybrid with base edge (B2 + B1) | 30.0 | 22.0 | 24.7 | 26.0 [22.9-29.4] | 43.3 | 29.4 | 87.4 |
| H_A2 | hybrid, cloud without RAG | 30.7 | 17.2 | 22.0 | 24.0 [21.0-27.3] | 43.1 | 58.7 | 74.6 |
| H_A3 | hybrid, cloud without tools (350-question stratified half) | 18.0 | 16.0 | 17.3 | 17.1 [13.6-21.4] | 34.0 | 30.0 | 74.6 |
