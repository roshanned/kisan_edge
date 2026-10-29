"""Translate English KCC question summaries to Hindi with IndicTrans2 (ai4bharat, run locally).

Adds `question_hi` to every English-question record. Only unique questions are translated,
and finished translations are cached, so re-runs are cheap.

Needs: `hf auth login` and the licence accepted on
https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M

Needs transformers==4.46.3: IndicTrans2's model code breaks on newer versions (KV-cache
changes give garbage / CUDA errors). The edge models need >=4.51, so install 4.46.3 just for
this step, then switch back.
Memory: batch 8 fits a 6 GB GPU, 16 fits a 16 GB T4 (beam search over a 122k vocabulary).

Usage:
  python -m src.data.translate_indictrans2 data/processed/kcc_1m_other.jsonl
  python -m src.data.translate_indictrans2 data/processed/kcc_hi.jsonl --limit 50   # quick test
"""
import argparse
import json
from pathlib import Path

import torch
from IndicTransToolkit.processor import IndicProcessor
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from src.data.common import read_jsonl, write_jsonl

MODEL = "ai4bharat/indictrans2-en-indic-dist-200M"
CACHE = Path("data/processed/cache/indictrans2_en_hi.json")


def load_cache():
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


def save_cache(cache):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def translate(texts, batch_size):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(
        MODEL, trust_remote_code=True,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32).to(device).eval()
    ip = IndicProcessor(inference=True)

    out = []
    for i in range(0, len(texts), batch_size):
        batch = ip.preprocess_batch(texts[i:i + batch_size], src_lang="eng_Latn", tgt_lang="hin_Deva")
        enc = tok(batch, truncation=True, padding="longest", max_length=256, return_tensors="pt").to(device)
        with torch.no_grad():
            gen = model.generate(**enc, num_beams=5, max_length=256)
        dec = tok.batch_decode(gen, skip_special_tokens=True, clean_up_tokenization_spaces=True)
        out.extend(ip.postprocess_batch(dec, lang="hin_Deva"))
        print(f"translated {min(i + batch_size, len(texts))}/{len(texts)}", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--limit", type=int, default=None, help="translate only the first N unique questions")
    ap.add_argument("--batch-size", type=int, default=32)
    args = ap.parse_args()

    rows = read_jsonl(args.path)
    cache = load_cache()
    todo = sorted({r["question"] for r in rows if r["lang"] == "en" and r["question"] not in cache})
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(todo)} new unique English questions to translate")

    # Translate in chunks and save the cache after each one, so a crash loses little work.
    chunk = 1000
    for i in range(0, len(todo), chunk):
        part = todo[i:i + chunk]
        cache.update(zip(part, translate(part, args.batch_size)))
        save_cache(cache)

    for r in rows:
        if r["lang"] == "en":
            r["question_hi"] = cache.get(r["question"])
    write_jsonl(rows, args.path)
    print(f"wrote {args.path}: {sum(bool(r.get('question_hi')) for r in rows)} rows have question_hi")


if __name__ == "__main__":
    main()
