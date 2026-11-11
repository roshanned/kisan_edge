"""Kaggle job 07 (final phase): two QLoRA re-runs with the job-03 recipe and different seeds, each run on the
700 test questions, so the H2 result comes with a seed spread (PLAN.md section 4, Roshan step 1).

  python kaggle/push_code.py "msg"
  kaggle kernels push -p kaggle/jobs/07_reruns --accelerator NvidiaTeslaT4
  kaggle kernels output roshanned/kisan-edge-07-reruns -p kaggle/results/07_reruns

Outputs: outputs/edge_tuned_s{SEED}.jsonl and models/<adapter>/train_log.json for each seed
"""
import glob
import os
import shutil
import subprocess
import sys
import zipfile

MODEL = "unsloth/Llama-3.2-3B-Instruct"
TRAIN_ARGS = "--epochs 2 --rank 16 --lr 2e-4 --batch-size 8 --grad-accum 2"  # same as job 03 (seed 42)
SEEDS = [1, 2]
WORK = "/kaggle/working"
REPO = f"{WORK}/kisan_edge"


def sh(cmd):
    print(f"\n$ {cmd}", flush=True)
    subprocess.run(cmd, shell=True, check=True, cwd=REPO)


def setup():
    """Copy the attached kisan-edge-code dataset into REPO; zipped folders are extracted in place."""
    req = glob.glob("/kaggle/input/**/requirements.txt", recursive=True)
    if not req:
        sys.exit("kisan-edge-code dataset not attached")
    base = os.path.dirname(req[0])
    os.makedirs(f"{REPO}/data/processed", exist_ok=True)
    for name in os.listdir(base):
        src = f"{base}/{name}"
        if name.endswith(".jsonl"):
            shutil.copy(src, f"{REPO}/data/processed/{name}")
        elif name.endswith(".zip"):
            with zipfile.ZipFile(src) as z:
                z.extractall(f"{REPO}/{name[:-4]}")
        elif os.path.isdir(src):
            shutil.copytree(src, f"{REPO}/{name}", dirs_exist_ok=True)
        else:
            shutil.copy(src, REPO)
    sh('pip install -q "transformers>=4.51,<5" accelerate "peft<0.18" bitsandbytes pandas pyarrow')
    sh("nvidia-smi --query-gpu=name,memory.total --format=csv")


def main():
    setup()
    sh("python -m src.edge.build_sft_data --split-file data/processed/questions.jsonl")
    for seed in SEEDS:
        adapter = f"models/{MODEL.split('/')[-1]}-split-r16-e2-s{seed}"
        sh(f"python -m src.edge.train_qlora --model {MODEL} --out {adapter} {TRAIN_ARGS} --seed {seed}")
        sh(f"python -m src.edge.generate --model {MODEL} --adapter {adapter} --questions data/processed/questions.jsonl "
           f"--splits test --out outputs/edge_tuned_s{seed}.jsonl --batch-size 16")
    for sub in ["outputs", "models"]:
        shutil.copytree(f"{REPO}/{sub}", f"{WORK}/{sub}", dirs_exist_ok=True)
    for ckpt in glob.glob(f"{WORK}/models/*/checkpoint-*"):
        shutil.rmtree(ckpt)
    shutil.rmtree(f"{WORK}/models/Llama-3.2-3B-Instruct-split-r16-e2", ignore_errors=True)  # the shipped B3 adapter
    shutil.rmtree(REPO)


if __name__ == "__main__":
    main()
