"""Batch-generate edge-model answers and save token logprobs for the confidence gate.

Output format (PLAN.md section 5), one JSON line per question:
  {id, model, answer, mean_logprob, min_logprob, n_tokens, latency_ms}

Usage:
  python -m src.edge.generate --model Qwen/Qwen3-1.7B --questions data/processed/pilot.jsonl \
      --out outputs/pilot_qwen3-1.7b.jsonl
  add --adapter <dir> to run a QLoRA-tuned model (B3); add --load-4bit to save VRAM.
"""
import argparse
import json
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from src.data.common import read_jsonl
from src.edge.prompts import messages

def load(model_name, adapter, load_4bit):
    tok = AutoTokenizer.from_pretrained(model_name)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                               bnb_4bit_compute_dtype=torch.float16) if load_4bit else None
    model = AutoModelForCausalLM.from_pretrained(
        model_name, torch_dtype=torch.float16, device_map="auto", quantization_config=quant)
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter)
    return tok, model.eval()


def build_prompt(tok, row):
    kwargs = {"enable_thinking": False} if "qwen3" in tok.name_or_path.lower() else {}
    return tok.apply_chat_template(messages(row), tokenize=False, add_generation_prompt=True, **kwargs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--questions", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--load-4bit", action="store_true")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--max-new-tokens", type=int, default=200)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    rows = read_jsonl(args.questions)[:args.limit]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["id"] for l in out_path.open(encoding="utf-8")} if out_path.exists() else set()
    rows = [r for r in rows if r["id"] not in done]  # resume after a crash or Kaggle timeout
    print(f"{len(rows)} questions to answer ({len(done)} already done)")

    tok, model = load(args.model, args.adapter, args.load_4bit)
    tag = args.model.split("/")[-1] + ("+" + Path(args.adapter).name if args.adapter else "")

    with out_path.open("a", encoding="utf-8") as f:
        for i in range(0, len(rows), args.batch_size):
            batch = rows[i:i + args.batch_size]
            enc = tok([build_prompt(tok, r) for r in batch], return_tensors="pt", padding=True).to(model.device)
            start = time.perf_counter()
            with torch.no_grad():
                # no_repeat_ngram_size stops loops like "वरदान-2, वरदान-3, ..." seen in the pilot.
                # output_scores are the processed scores, so logprobs reflect these constraints.
                gen = model.generate(**enc, max_new_tokens=args.max_new_tokens, do_sample=False,
                                     no_repeat_ngram_size=4, repetition_penalty=1.1,
                                     output_scores=True, return_dict_in_generate=True,
                                     pad_token_id=tok.pad_token_id)
            latency = (time.perf_counter() - start) * 1000 / len(batch)

            new_tokens = gen.sequences[:, enc["input_ids"].shape[1]:]
            # Log-probability the model gave each token it actually chose.
            logprobs = torch.stack(
                [torch.log_softmax(s.float(), dim=-1).gather(1, new_tokens[:, t:t + 1]).squeeze(1)
                 for t, s in enumerate(gen.scores)], dim=1)
            for j, row in enumerate(batch):
                keep = new_tokens[j] != tok.pad_token_id
                if tok.eos_token_id is not None:
                    keep &= new_tokens[j] != tok.eos_token_id
                lp = logprobs[j][keep]
                f.write(json.dumps({
                    "id": row["id"],
                    "model": tag,
                    "answer": tok.decode(new_tokens[j][keep], skip_special_tokens=True).strip(),
                    "mean_logprob": round(lp.mean().item(), 4) if len(lp) else None,
                    "min_logprob": round(lp.min().item(), 4) if len(lp) else None,
                    "n_tokens": int(keep.sum()),
                    "latency_ms": round(latency, 1),
                }, ensure_ascii=False) + "\n")
            f.flush()
            print(f"answered {min(i + args.batch_size, len(rows))}/{len(rows)}", flush=True)


if __name__ == "__main__":
    main()
