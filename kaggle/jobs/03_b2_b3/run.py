"""Kaggle job 03: QLoRA on the frozen train split, then B2 (base) and B3 (tuned) on the gold set.

Ungated model copy, so it runs from the CLI with no secrets:
  python kaggle/push_code.py "msg"
  kaggle kernels push -p kaggle/jobs/03_b2_b3 --accelerator NvidiaTeslaT4
  kaggle kernels output roshanned/kisan-edge-03-b2-b3 -p kaggle/results/03_b2_b3

Outputs (names Kiran's and Anushka's scripts expect):
  outputs/edge_base.jsonl   B2
  outputs/edge_tuned.jsonl  B3
  models/<adapter>/         LoRA adapter + train_log.json
"""
import glob
import os
import shutil
import subprocess
import sys
import zipfile

MODEL = "unsloth/Llama-3.2-3B-Instruct"  # ungated copy of meta-llama/Llama-3.2-3B-Instruct
RUN_NAME = "split-r16-e2"
TRAIN_ARGS = "--epochs 2 --rank 16 --lr 2e-4 --batch-size 8 --grad-accum 2"  # 4.6k examples, so 2 epochs

WORK = "/kaggle/working"
REPO = f"{WORK}/kisan_edge"


def sh(cmd):
    print(f"\n$ {cmd}", flush=True)
    subprocess.run(cmd, shell=True, check=True, cwd=REPO)


def main():
    req = glob.glob("/kaggle/input/**/requirements.txt", recursive=True)
    if not req:
        sys.exit("kisan-edge-code dataset not attached")
    base = os.path.dirname(req[0])
    os.makedirs(f"{REPO}/data/processed", exist_ok=True)
    shutil.copy(f"{base}/requirements.txt", REPO)
    for name in ["questions.jsonl", "gold.jsonl"]:
        shutil.copy(f"{base}/{name}", f"{REPO}/data/processed/{name}")
    if os.path.isdir(f"{base}/src"):
        shutil.copytree(f"{base}/src", f"{REPO}/src", dirs_exist_ok=True)
    else:
        with zipfile.ZipFile(f"{base}/src.zip") as z:
            z.extractall(f"{REPO}/src")

    # Only what the edge model needs; the full requirements pull in the cloud stack.
    sh('pip install -q "transformers>=4.51,<5" accelerate "peft<0.18" bitsandbytes pandas')
    sh("nvidia-smi --query-gpu=name,memory.total --format=csv")

    adapter = f"models/{MODEL.split('/')[-1]}-{RUN_NAME}"
    sh("python -m src.edge.build_sft_data --split-file data/processed/questions.jsonl")
    sh(f"python -m src.edge.train_qlora --model {MODEL} --out {adapter} {TRAIN_ARGS}")

    gold = "data/processed/gold.jsonl"
    sh(f"python -m src.edge.generate --model {MODEL} --questions {gold} --out outputs/edge_base.jsonl --batch-size 16")
    sh(f"python -m src.edge.generate --model {MODEL} --adapter {adapter} --questions {gold} "
       f"--out outputs/edge_tuned.jsonl --batch-size 16")

    for sub in ["outputs", "models"]:
        shutil.copytree(f"{REPO}/{sub}", f"{WORK}/{sub}", dirs_exist_ok=True)
    for f in ["sft_train.jsonl", "sft_val.jsonl"]:
        shutil.copy(f"{REPO}/data/processed/{f}", WORK)
    for ckpt in glob.glob(f"{WORK}/models/*/checkpoint-*"):
        shutil.rmtree(ckpt)
    shutil.rmtree(REPO)


if __name__ == "__main__":
    main()
