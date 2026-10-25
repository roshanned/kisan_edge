# Kisan-Edge

A phone-sized, LoRA-tuned language model that answers farmers' questions in Hindi, Hinglish and English. A confidence gate sends questions it can't handle safely to a cloud LLM with RAG and tools, once the farmer is back online. See [project_proposal.pdf](project_proposal.pdf) for the design and [PLAN.md](PLAN.md) for the team plan.

**Team:** Anushka Sharma (data and evaluation) · Roshan K (edge model) · Sai Rithvik (cloud side) · Kiran R (router, gate, queue)

| | Date |
|---|---|
| Mid-submission | Oct 30, 2026 |
| Final submission | Nov 15, 2026 |

## Data and access

| What | Where | Access |
|---|---|---|
| Code | This repo; edge-model work is on branch `roshan/edge` | Public |
| Processed data, translations, model answers | Hugging Face dataset [kisan-edge/kisan-edge-data](https://huggingface.co/datasets/kisan-edge/kisan-edge-data), in the [kisan-edge](https://huggingface.co/kisan-edge) HF org | Public (anyone can download); org members can upload |
| Raw data | Re-downloaded by `python -m src.data.download` from [Omegaindebt/Kisan_Call_Centre_Transcripts](https://huggingface.co/datasets/Omegaindebt/Kisan_Call_Centre_Transcripts) and [KisanVaani/agriculture-qa-english-only](https://huggingface.co/datasets/KisanVaani/agriculture-qa-english-only) | Public |
| Fine-tuned LoRA adapter | Kaggle job output `roshanned/kisan-edge-02-qlora` (not in git) | Roshan |
| GPU jobs | Kaggle notebooks `roshanned/kisan-edge-01-pilot`, `roshanned/kisan-edge-02-qlora` (private) | Roshan |

Load the processed data:
```python
from huggingface_hub import snapshot_download
path = snapshot_download("kisan-edge/kisan-edge-data", repo_type="dataset")
# path/processed/*.jsonl, path/outputs/*.jsonl
```

What's in it:

| File | Rows | Contents |
|---|---|---|
| `processed/kcc_hinglish.jsonl` | 9,432 | KCC UP, 4 crops, Hinglish questions |
| `processed/kcc_1m_other.jsonl` | 33,556 | KCC UP, 4 crops, English summaries + `question_hi` (IndicTrans2 Hindi) |
| `processed/kisanvaani_en.jsonl` | 2,328 | KisanVaani English Q-A |
| `processed/pilot.jsonl`, `pilot_ids.txt` | 100 | Hindi pilot set. **Must go into dev, never test.** |
| `processed/sft_train.jsonl`, `sft_val.jsonl` | 9,146 / 282 | Fine-tuning set (pilot run) |
| `outputs/pilot_*.jsonl` | 100 each | Answers + token logprobs: Qwen3-1.7B, Llama-3.2-1B/3B base, Llama-3.2-3B tuned |
| `outputs/pilot_rating_sheet*.csv` | 100 | All answers side by side for manual rating |

All files use the shared question format from [PLAN.md](PLAN.md) section 5. `split` is empty until Anushka's split script fills it; `category` is a first-pass label (Kiran's router labels are final).

---

## Edge model (Roshan): Phase 1 status

*Last updated: Oct 25, 2026*

### Done

**Data**
- [x] Cleaned the KCC 1M-row sample, restricted to Uttar Pradesh and the 4 crops ([src/data/prepare_kcc_1m.py](src/data/prepare_kcc_1m.py))
  - **9,432 Hinglish rows** (6,740 unique questions)
  - **33,556 more rows** with English question summaries; ~62% have Hindi answers
  - Dropped 8,573 duplicates, 2,781 corrupted rows ("????" text) and 426 empty or short rows; phone numbers replaced with `[PHONE]`; HTML-encoded Hindi decoded
- [x] Cleaned KisanVaani ([src/data/prepare_kisanvaani.py](src/data/prepare_kisanvaani.py)). **Only 2,331 unique pairs** in the 22,615-row original, and just 11 mention our 4 crops.
- [x] Translated **33,545 English KCC questions to Hindi** with IndicTrans2 ([src/data/translate_indictrans2.py](src/data/translate_indictrans2.py))
- [x] Uploaded all processed data to the public dataset [kisan-edge/kisan-edge-data](https://huggingface.co/datasets/kisan-edge/kisan-edge-data) (see [Data and access](#data-and-access))
- [x] Code pushed to GitHub (branch `roshan/edge`)

**Model choice (100-question Hindi pilot)** ([src/edge/make_pilot.py](src/edge/make_pilot.py), [src/edge/compare_pilot.py](src/edge/compare_pilot.py))

| Model (base) | Replied in Hindi | Word overlap with expert | Mean logprob | ms/question |
|---|---|---|---|---|
| Qwen3-1.7B | 100% | 0.142 | -0.135 | 928 |
| Llama-3.2-1B | 100% | 0.123 | -0.299 | 489 |
| **Llama-3.2-3B (chosen)** | 100% | 0.125 | -0.223 | 843 |

- [x] **Chose Llama-3.2-3B-Instruct.** It wrote the most coherent Hindi with the fewest loops, and it's ~2 GB at 4-bit. Qwen3-1.7B looped and was the most confident while wrong, which is bad for the gate. Llama-3.2-1B's Hindi broke down most often.
- [x] No base model gave real answers: they invented variety names and wrote 200-token essays, where KCC answers are 1–2 lines.

**Fine-tuning (pilot QLoRA run)** ([src/edge/build_sft_data.py](src/edge/build_sft_data.py), [src/edge/train_qlora.py](src/edge/train_qlora.py))
- [x] Built the training set (9,146 train / 282 val; Hindi, Hinglish and English ~⅓ each) with the proposal's safety rules:
  - **Any answer containing a dose → safe answer** (read the label, wear protection, contact KVK / KCC 1800-180-1551, question queued). This applies to every category, because KCC labels are noisy. 0 doses remain in the training answers.
  - Weather, price and scheme questions → "will update when online" (capped at 10%)
  - Safe answers capped at 25%, so the model doesn't learn to defer everything
  - Emergencies dropped (the router handles them); pilot questions kept out of training
- [x] QLoRA run on Llama-3.2-3B: rank 16, 1 epoch, 44 min on a Kaggle T4. Validation loss went 1.39 → 1.17.
- [x] **First H2 preview** on the 100 Hindi pilot questions:

| | Base | Fine-tuned |
|---|---|---|
| Word overlap with expert answer | 0.125 | **0.217** |
| Answer length (tokens) | 200 | **78** |
| Answers containing a dose | 11 | **3** |
| Safe deferrals | 0 | 25 |

**Tooling**
- [x] Generation script that saves token logprobs (mean, min) for Kiran's gate ([src/edge/generate.py](src/edge/generate.py)), with repetition limits added after the pilot (not yet re-tested on Kaggle)
- [x] Kaggle jobs run from the command line ([kaggle/](kaggle/)): code is shipped as a private Kaggle dataset; job 01 = clean + translate + pilot, job 02 = QLoRA + base vs tuned

### Pending

| Task | Blocked on | Plan |
|---|---|---|
| Invite Anushka, Kiran, Sai to the `kisan-edge` HF org | n/a | Only needed to upload; downloading is open to everyone |
| Tell Anushka about the files + `pilot_ids.txt` | n/a | Pilot IDs must go into **dev**, never test |
| Hand-check 50 gold-set questions | Anushka's split + gold set | |
| **Retrain QLoRA on the frozen train split** | Anushka's split | Current adapter used our own files; retraining avoids test leakage (~45 min) |
| **B2** (base) on the gold set, with logprobs, to Kiran | Gold set | One Kaggle job |
| **B3** (tuned) on the gold set, with logprobs, to Kiran | Gold set + retrain | Same job |
| Official H2 number (base vs tuned) | Anushka's judge | Word overlap is only a proxy |
| Edge section of the mid-report | n/a | Datasets, pilot, H2 preview, challenges |

**Known issues to report**
- 10/100 tuned answers looped ("वरदान-2, वरदान-3, …"). Repetition limits are added to generation; to be verified on Kaggle.
- Some pest questions get a vague "निराई करें" (do weeding). The gate should score these low; the 2 planned re-runs may help.
- 3% of tuned answers still contain a dose. Kiran's output filter is the second layer; report this as the "offline dose rate before filter".

**Challenges and fixes so far**
- IndicTrans2's model code breaks on new `transformers` versions, so translation runs on 4.46.3 and the edge models on ≥4.51.
- Kaggle jobs started from the command line can't read secrets, so we use the ungated `unsloth/Llama-3.2-3B-Instruct` copy.
- KCC QueryType labels are noisy (weather questions tagged "Plant Protection"), so keyword rules and a dose check on every answer are applied.

---

## Repo layout

```
src/data/     cleaning, translation (shared cleaning rules in common.py)
src/edge/     pilot, generation with logprobs, SFT data, QLoRA training
kaggle/       Kaggle job scripts; push_code.py uploads src/ as a private Kaggle dataset
outputs/      small result files (answer files are on the HF dataset)
```

## Run

```bash
pip install -r requirements.txt
python -m src.data.download              # raw data from Hugging Face
python -m src.data.prepare_kcc_1m        # -> data/processed/kcc_hinglish.jsonl, kcc_1m_other.jsonl
python -m src.data.prepare_kisanvaani    # -> data/processed/kisanvaani_en.jsonl
# GPU steps run on Kaggle:
python kaggle/push_code.py "message"
kaggle kernels push -p kaggle/jobs/02_qlora --accelerator NvidiaTeslaT4
```
