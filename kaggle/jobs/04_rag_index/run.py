"""Kaggle job 04: embed the RAG corpus with BGE-M3 on GPU and build the FAISS index for B1/A3.

The corpus (corpus/raw + corpus/docs.jsonl from src.cloud.fetch_corpus) goes up as its own private dataset:
  python kaggle/push_code.py "msg"
  python kaggle/push_corpus.py "msg"
  kaggle kernels push -p kaggle/jobs/04_rag_index --accelerator NvidiaTeslaT4
  kaggle kernels output roshanned/kisan-edge-04-rag-index -p kaggle/results/04_rag_index
Then copy kaggle/results/04_rag_index/corpus/index to corpus/index.

Output: corpus/index/ (rag.sqlite with docs, chunks and cached embeddings; FAISS index)
"""
import glob
import os
import shutil
import subprocess
import sys
import zipfile

AS_OF = "2026-10-30"  # same snapshot date as the tool data
WORK = "/kaggle/working"
REPO = f"{WORK}/kisan_edge"


def sh(cmd):
    print(f"\n$ {cmd}", flush=True)
    subprocess.run(cmd, shell=True, check=True, cwd=REPO)


def main():
    req = glob.glob("/kaggle/input/**/requirements.txt", recursive=True)
    docs = glob.glob("/kaggle/input/**/docs.jsonl", recursive=True)
    if not req or not docs:
        sys.exit("kisan-edge-code or kisan-edge-corpus dataset not attached")
    base = os.path.dirname(req[0])
    os.makedirs(REPO, exist_ok=True)
    if os.path.isdir(f"{base}/src"):
        shutil.copytree(f"{base}/src", f"{REPO}/src", dirs_exist_ok=True)
    else:
        with zipfile.ZipFile(f"{base}/src.zip") as z:
            z.extractall(f"{REPO}/src")
    corpus = os.path.dirname(docs[0])
    os.makedirs(f"{REPO}/corpus", exist_ok=True)
    shutil.copy(docs[0], f"{REPO}/corpus/docs.jsonl")
    if os.path.isdir(f"{corpus}/raw"):
        shutil.copytree(f"{corpus}/raw", f"{REPO}/corpus/raw")
    else:
        with zipfile.ZipFile(f"{corpus}/raw.zip") as z:
            z.extractall(f"{REPO}/corpus/raw")

    sh("pip install -q sentence-transformers faiss-cpu datasketch pypdf beautifulsoup4")
    sh("nvidia-smi --query-gpu=name,memory.total --format=csv")
    sh(f"python -m src.cloud.rag_ingest --docs corpus/docs.jsonl --index-dir corpus/index --as-of {AS_OF}")

    shutil.copytree(f"{REPO}/corpus/index", f"{WORK}/corpus/index", dirs_exist_ok=True)
    shutil.rmtree(REPO)


if __name__ == "__main__":
    main()
