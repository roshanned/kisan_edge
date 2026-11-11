"""BhashaBench-Krishi (Hindi) multiple-choice accuracy, base vs tuned (PLAN.md section 4, Roshan step 4).

Source: the ungated `bharatgenai/BhashaBench-Multi`, file `bhashabench_krishi/hi.parquet` (15,405 questions machine-
translated from English, with LLM-judged translation quality). The native-Hindi `BhashaBench-Krishi` (2,757 Qs) is
gated; once its terms are accepted on Hugging Face, pass its parquet with --native (columns question, option_a..d).
Scoring: zero-shot, the option letter (A-D) with the highest next-token logit after the chat prompt. A fixed random
sample (--n, --seed) keeps base and tuned on exactly the same questions.

Usage: python -m src.edge.bhashabench --model unsloth/Llama-3.2-3B-Instruct [--adapter models/...] \
           --parquet data/raw/bhashabench/bhashabench_krishi/hi.parquet --out outputs/bhashabench_base.jsonl
"""
import argparse
import json
from pathlib import Path

import pandas as pd
import torch

from src.edge.generate import load

SYSTEM = "आप एक कृषि विशेषज्ञ हैं। प्रश्न का सही विकल्प चुनें और केवल उसका अक्षर (A, B, C या D) लिखें।"
LETTERS = ["A", "B", "C", "D"]


def load_questions(path, n, seed, native=False):
    d = pd.read_parquet(path)
    sfx = "" if native else "_translated"
    d = d.rename(columns={f"{c}{sfx}": f"hi_{c}" for c in ["question", "option_a", "option_b", "option_c", "option_d"]})
    d = d.dropna(subset=["hi_question", "correct_answer"])
    d = d[d["correct_answer"].isin(LETTERS)]
    if n and n < len(d):
        d = d.sample(n=n, random_state=seed)
    return d.to_dict("records")


def prompt(tok, r):
    body = r["hi_question"] + "\n" + "\n".join(f"{L}. {r[f'hi_option_{L.lower()}']}" for L in LETTERS) + "\nउत्तर:"
    return tok.apply_chat_template([{"role": "system", "content": SYSTEM}, {"role": "user", "content": body}],
                                   tokenize=False, add_generation_prompt=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--parquet", required=True)
    ap.add_argument("--native", action="store_true", help="parquet is the gated native-Hindi BhashaBench-Krishi")
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rows = load_questions(a.parquet, a.n, a.seed, a.native)
    tok, model = load(a.model, a.adapter, False)
    letter_ids = [tok.encode(L, add_special_tokens=False)[0] for L in LETTERS]
    tag = a.model.split("/")[-1] + ("+" + Path(a.adapter).name if a.adapter else "")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    correct = 0
    with open(a.out, "w", encoding="utf-8") as f:
        for i in range(0, len(rows), a.batch_size):
            batch = rows[i:i + a.batch_size]
            enc = tok([prompt(tok, r) for r in batch], return_tensors="pt", padding=True,
                      add_special_tokens=False).to(model.device)
            with torch.no_grad():
                logits = model(**enc).logits[:, -1, :]  # left padding, so the last position is the next token
            picks = logits[:, letter_ids].argmax(-1).tolist()
            for r, p in zip(batch, picks):
                ok = LETTERS[p] == r["correct_answer"]
                correct += ok
                f.write(json.dumps({"id": r["id"], "model": tag, "pred": LETTERS[p], "gold": r["correct_answer"],
                                    "correct": ok, "level": r.get("question_level"), "type": r.get("question_type"),
                                    "domain": r.get("subject_domain")}, ensure_ascii=False) + "\n")
            print(f"{min(i + a.batch_size, len(rows))}/{len(rows)} acc so far {correct / min(i + a.batch_size, len(rows)):.3f}",
                  flush=True)
    print(json.dumps({"model": tag, "n": len(rows), "accuracy": round(correct / len(rows), 4)}))


if __name__ == "__main__":
    main()
