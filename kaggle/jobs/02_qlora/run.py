"""Kaggle job 02: QLoRA pilot run on the chosen edge model, then base vs tuned on the pilot set.

Uses job 01's output (cleaned + translated data) as input. Ungated model copies only, so no
HF token is needed and the job can be pushed from the CLI:
  kaggle kernels push -p kaggle/jobs/02_qlora --accelerator NvidiaTeslaT4
  kaggle kernels output roshanned/kisan-edge-02-qlora -p kaggle/results/02_qlora

Set MODEL from the pilot result before pushing.
"""
import glob
import os
import shutil
import subprocess
import sys
import zipfile

MODEL = "unsloth/Llama-3.2-3B-Instruct"  # chosen from the pilot; ungated copy of meta-llama/Llama-3.2-3B-Instruct
RUN_NAME = "pilot-r16-e1"
TRAIN_ARGS = "--epochs 1 --rank 16 --lr 2e-4 --batch-size 8 --grad-accum 2"

WORK = "/kaggle/working"
REPO = f"{WORK}/kisan_edge"


def sh(cmd):
    print(f"\n$ {cmd}", flush=True)
    subprocess.run(cmd, shell=True, check=True, cwd=REPO)


def find_input(name):
    hits = glob.glob(f"/kaggle/input/**/{name}", recursive=True)
    if not hits:
        sys.exit(f"input not found: {name}")
    return hits[0]


def main():
    base = os.path.dirname(find_input("requirements.txt"))
    os.makedirs(REPO, exist_ok=True)
    shutil.copy(f"{base}/requirements.txt", REPO)
    if os.path.isdir(f"{base}/src"):
        shutil.copytree(f"{base}/src", f"{REPO}/src", dirs_exist_ok=True)
    else:
        with zipfile.ZipFile(f"{base}/src.zip") as z:
            z.extractall(f"{REPO}/src")

    # Cleaned + translated data from job 01
    processed = os.path.dirname(find_input("kcc_1m_other.jsonl"))
    shutil.copytree(processed, f"{REPO}/data/processed", dirs_exist_ok=True)
    print("data from", processed, os.listdir(f"{REPO}/data/processed"))

    sh("pip install -q -r requirements.txt")
    sh("nvidia-smi --query-gpu=name,memory.total --format=csv")

    name = MODEL.split("/")[-1]
    adapter = f"models/{name}-{RUN_NAME}"
    sh("python -m src.edge.build_sft_data --pilot")
    sh(f"python -m src.edge.train_qlora --model {MODEL} --out {adapter} {TRAIN_ARGS}")

    # Quick H2 preview on the 100-question Hindi pilot set (dev data): base vs tuned
    sh(f"python -m src.edge.generate --model {MODEL} --questions data/processed/pilot.jsonl "
       f"--out outputs/pilot_{name}.jsonl --batch-size 16")
    sh(f"python -m src.edge.generate --model {MODEL} --adapter {adapter} --questions data/processed/pilot.jsonl "
       f"--out outputs/pilot_{name}+{RUN_NAME}.jsonl --batch-size 16")
    sh(f"python -m src.edge.compare_pilot outputs/pilot_{name}.jsonl outputs/pilot_{name}+{RUN_NAME}.jsonl")

    for sub in ["outputs", "models"]:
        shutil.copytree(f"{REPO}/{sub}", f"{WORK}/{sub}", dirs_exist_ok=True)
    for f in ["sft_train.jsonl", "sft_val.jsonl"]:
        shutil.copy(f"{REPO}/data/processed/{f}", WORK)
    # Drop optimizer checkpoints; keep only the final adapter
    for ckpt in glob.glob(f"{WORK}/models/*/checkpoint-*"):
        shutil.rmtree(ckpt)
    shutil.rmtree(REPO)


if __name__ == "__main__":
    main()
