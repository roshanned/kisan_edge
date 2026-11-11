"""Kaggle job 06 (final phase): B2 and B3 on the full test, calib and dev splits (1,900 Qs each, with logprobs),
then BhashaBench-Krishi Hindi accuracy for both models. Reuses the B3 adapter from job 03 (shipped in kisan-edge-code).

  python kaggle/push_code.py "msg"
  kaggle kernels push -p kaggle/jobs/06_edge_full --accelerator NvidiaTeslaT4
  kaggle kernels output roshanned/kisan-edge-06-edge-full -p kaggle/results/06_edge_full

Outputs: outputs/edge_base_full.jsonl (B2), outputs/edge_tuned_full.jsonl (B3),
         outputs/bhashabench_base.jsonl, outputs/bhashabench_tuned.jsonl
"""
import glob
import os
import shutil
import subprocess
import sys
import zipfile

MODEL = "unsloth/Llama-3.2-3B-Instruct"
ADAPTER = "models/Llama-3.2-3B-Instruct-split-r16-e2"
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
    q = "data/processed/questions.jsonl"
    splits = "test,calib,dev"
    sh(f"python -m src.edge.generate --model {MODEL} --questions {q} --splits {splits} "
       f"--out outputs/edge_base_full.jsonl --batch-size 16")
    sh(f"python -m src.edge.generate --model {MODEL} --adapter {ADAPTER} --questions {q} --splits {splits} "
       f"--out outputs/edge_tuned_full.jsonl --batch-size 16")
    bb = "data/raw/bhashabench/bhashabench_krishi/hi.parquet"
    sh(f"python -m src.edge.bhashabench --model {MODEL} --parquet {bb} --out outputs/bhashabench_base.jsonl")
    sh(f"python -m src.edge.bhashabench --model {MODEL} --adapter {ADAPTER} --parquet {bb} "
       f"--out outputs/bhashabench_tuned.jsonl")
    shutil.copytree(f"{REPO}/outputs", f"{WORK}/outputs", dirs_exist_ok=True)
    shutil.rmtree(REPO)


if __name__ == "__main__":
    main()
