"""QLoRA fine-tuning of the edge model on data/processed/sft_{train,val}.jsonl.

The training text is built exactly like inference in generate.py (chat template with the
generation prompt, then the answer and EOS), and loss is computed on the answer tokens only.

Usage (T4 GPU):
  python -m src.edge.train_qlora --model Qwen/Qwen3-1.7B --out models/qwen3-1.7b-kisan-lora
  add --max-steps 50 for a quick smoke test
"""
import argparse
import json

import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer,
                          TrainingArguments)

from src.data.common import read_jsonl


def encode(tok, example, max_len):
    msgs = example["messages"]
    kwargs = {"enable_thinking": False} if "qwen3" in tok.name_or_path.lower() else {}
    prompt = tok.apply_chat_template(msgs[:-1], tokenize=False, add_generation_prompt=True, **kwargs)
    prompt_ids = tok(prompt, add_special_tokens=False)["input_ids"]
    answer_ids = tok(msgs[-1]["content"] + tok.eos_token, add_special_tokens=False)["input_ids"]
    ids = (prompt_ids + answer_ids)[:max_len]
    labels = ([-100] * len(prompt_ids) + answer_ids)[:max_len]
    return {"input_ids": ids, "labels": labels}


class Collator:
    def __init__(self, pad_id):
        self.pad_id = pad_id

    def __call__(self, batch):
        width = max(len(b["input_ids"]) for b in batch)
        ids = [b["input_ids"] + [self.pad_id] * (width - len(b["input_ids"])) for b in batch]
        labels = [b["labels"] + [-100] * (width - len(b["labels"])) for b in batch]
        mask = [[1] * len(b["input_ids"]) + [0] * (width - len(b["input_ids"])) for b in batch]
        return {"input_ids": torch.tensor(ids), "labels": torch.tensor(labels),
                "attention_mask": torch.tensor(mask)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--train", default="data/processed/sft_train.jsonl")
    ap.add_argument("--val", default="data/processed/sft_val.jsonl")
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--max-steps", type=int, default=-1)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--grad-accum", type=int, default=2)
    ap.add_argument("--max-len", type=int, default=512)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    train = [encode(tok, ex, args.max_len) for ex in read_jsonl(args.train)]
    val = [encode(tok, ex, args.max_len) for ex in read_jsonl(args.val)]
    print(f"train {len(train)}, val {len(val)}, "
          f"mean tokens {sum(len(t['input_ids']) for t in train) / len(train):.0f}")

    model = AutoModelForCausalLM.from_pretrained(
        args.model, device_map="auto", torch_dtype=torch.float16,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                               bnb_4bit_use_double_quant=True,
                                               bnb_4bit_compute_dtype=torch.float16))
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model = get_peft_model(model, LoraConfig(
        r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.05, task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]))
    model.print_trainable_parameters()

    trainer = Trainer(
        model=model,
        train_dataset=train,
        eval_dataset=val,
        data_collator=Collator(tok.pad_token_id),
        args=TrainingArguments(
            output_dir=args.out, num_train_epochs=args.epochs, max_steps=args.max_steps,
            per_device_train_batch_size=args.batch_size, per_device_eval_batch_size=args.batch_size,
            gradient_accumulation_steps=args.grad_accum, learning_rate=args.lr,
            lr_scheduler_type="cosine", warmup_ratio=0.03, fp16=True,  # T4 has no bf16
            logging_steps=20, eval_strategy="steps", eval_steps=200, save_strategy="steps",
            save_steps=200, save_total_limit=2, report_to="none", seed=args.seed,
            group_by_length=True, remove_unused_columns=False),
    )
    trainer.train()
    model.save_pretrained(args.out)
    tok.save_pretrained(args.out)
    metrics = trainer.evaluate()
    with open(f"{args.out}/train_log.json", "w") as f:
        json.dump({"args": vars(args), "final_eval": metrics, "history": trainer.state.log_history}, f, indent=2)
    print("final eval:", metrics)


if __name__ == "__main__":
    main()
