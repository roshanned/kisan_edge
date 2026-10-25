"""Kaggle job 01: data cleaning, IndicTrans2 translation and the 100-question edge-model pilot.

Pushed with:  kaggle kernels push -p kaggle/jobs/01_pilot --accelerator NvidiaTeslaT4
Results land in /kaggle/working/{data/processed,outputs}; fetch them with
  kaggle kernels output roshanned/kisan-edge-01-pilot -p kaggle/results/01_pilot

Needs the HF_TOKEN Kaggle secret attached to this notebook (gated: IndicTrans2, Llama 3.2).
"""
import glob
import os
import shutil
import subprocess
import sys
import zipfile

WORK = "/kaggle/working"
REPO = f"{WORK}/kisan_edge"
MODELS = ["Qwen/Qwen3-1.7B", "meta-llama/Llama-3.2-1B-Instruct", "meta-llama/Llama-3.2-3B-Instruct"]


def sh(cmd):
    print(f"\n$ {cmd}", flush=True)
    subprocess.run(cmd, shell=True, check=True, cwd=REPO)


def get_code():
    """Copy src/ and requirements.txt from the attached kisan-edge-code dataset."""
    req = glob.glob("/kaggle/input/**/requirements.txt", recursive=True)
    if not req:
        sys.exit("kisan-edge-code dataset not attached")
    base = os.path.dirname(req[0])
    os.makedirs(REPO, exist_ok=True)
    shutil.copy(req[0], REPO)
    if os.path.isdir(f"{base}/src"):
        shutil.copytree(f"{base}/src", f"{REPO}/src", dirs_exist_ok=True)
    else:
        with zipfile.ZipFile(f"{base}/src.zip") as z:
            z.extractall(f"{REPO}/src")
    print("code from", base, os.listdir(f"{REPO}/src"))


def get_hf_token():
    try:
        from kaggle_secrets import UserSecretsClient
        os.environ["HF_TOKEN"] = UserSecretsClient().get_secret("HF_TOKEN")
        print("HF_TOKEN loaded")
    except Exception as e:  # stop before spending GPU time on a run that can't load gated models
        sys.exit(f"HF_TOKEN secret not available ({e}). Attach it: Add-ons -> Secrets -> HF_TOKEN.")


def main():
    get_hf_token()
    get_code()
    # Raw data stays out of /kaggle/working so it isn't saved as job output.
    os.makedirs("/tmp/raw", exist_ok=True)
    os.makedirs(f"{REPO}/data", exist_ok=True)
    if not os.path.exists(f"{REPO}/data/raw"):
        os.symlink("/tmp/raw", f"{REPO}/data/raw")

    sh("pip install -q -r requirements.txt")
    sh("nvidia-smi --query-gpu=name,memory.total --format=csv")

    # Step 1: clean
    sh("python -m src.data.download")
    sh("python -m src.data.prepare_kcc_1m")
    sh("python -m src.data.prepare_kisanvaani")
    # Step 2: translate English KCC questions to Hindi (IndicTrans2 needs the older transformers)
    sh('pip install -q "transformers==4.46.3"')
    sh("python -m src.data.translate_indictrans2 data/processed/kcc_1m_other.jsonl --batch-size 16")
    sh('pip install -q "transformers>=4.51,<5"')
    # Step 3: pilot set
    sh("python -m src.edge.make_pilot")
    # Step 4: run the pilot on each candidate
    outs = []
    for m in MODELS:
        out = f"outputs/pilot_{m.split('/')[-1]}.jsonl"
        sh(f"python -m src.edge.generate --model {m} --questions data/processed/pilot.jsonl --out {out} --batch-size 16")
        outs.append(out)
    # Step 5: compare
    sh("python -m src.edge.compare_pilot " + " ".join(outs))

    # Keep only results in the job output: move them up out of the code folder.
    for sub in ["data/processed", "outputs"]:
        shutil.copytree(f"{REPO}/{sub}", f"{WORK}/{sub}", dirs_exist_ok=True)
    shutil.rmtree(REPO)


if __name__ == "__main__":
    main()
