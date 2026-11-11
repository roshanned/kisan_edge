"""Kaggle job 08 (final phase, CPU only): phone-size checks for the B3 model (PLAN.md section 4, Roshan step 3).
Merges the B3 LoRA adapter into Llama-3.2-3B-Instruct, converts it to GGUF, quantizes to 4-bit (Q4_K_M) and measures
llama.cpp speed (prompt and generation tokens/s) and peak RAM on the Kaggle CPU (4 vCPU), then answers 5 test questions
with the 4-bit model as a smoke test.

  python kaggle/push_code.py "msg"
  kaggle kernels push -p kaggle/jobs/08_gguf
  kaggle kernels output roshanned/kisan-edge-08-gguf -p kaggle/results/08_gguf

Outputs: models/kisan-edge-3b-Q4_K_M.gguf, outputs/llamacpp_bench.json, outputs/llamacpp_smoke.jsonl
"""
import glob
import os
import shutil
import subprocess
import sys
import zipfile

MODEL = "unsloth/Llama-3.2-3B-Instruct"
ADAPTER = "models/Llama-3.2-3B-Instruct-split-r16-e2"
GGUF = "models/kisan-edge-3b-Q4_K_M.gguf"
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
    sh('pip install -q "transformers>=4.51,<5" accelerate "peft<0.18" pandas')
    sh("nproc; free -g")


MERGE = """
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
m = AutoModelForCausalLM.from_pretrained("%s", torch_dtype=torch.float16)
m = PeftModel.from_pretrained(m, "%s").merge_and_unload()
m.save_pretrained("merged")
AutoTokenizer.from_pretrained("%s").save_pretrained("merged")
"""

BENCH = """
import json, resource, subprocess
out = subprocess.run(["llama.cpp/build/bin/llama-bench", "-m", "%s", "-t", "4", "-p", "128", "-n", "64", "-r", "3",
                      "-o", "json"], capture_output=True, text=True, check=True).stdout
peak_mb = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024  # Linux reports KB
json.dump({"runs": json.loads(out), "peak_rss_mb": round(peak_mb, 1)}, open("outputs/llamacpp_bench.json", "w"), indent=1)
print(out, "peak RSS MB", peak_mb)
"""

SMOKE = """
import json, subprocess, time
from src.data.common import read_jsonl
from src.edge.prompts import messages
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("merged")
qs = [q for q in read_jsonl("data/processed/questions.jsonl") if q["split"] == "test"][:5]
with open("outputs/llamacpp_smoke.jsonl", "w", encoding="utf-8") as f:
    for q in qs:
        p = tok.apply_chat_template(messages(q), tokenize=False, add_generation_prompt=True)
        t = time.time()
        out = subprocess.run(["llama.cpp/build/bin/llama-completion", "-m", "%s", "-p", p, "-n", "120", "-t", "4",
                              "--temp", "0", "-no-cnv", "--no-display-prompt"], capture_output=True, text=True).stdout
        f.write(json.dumps({"id": q["id"], "question": q["question"], "answer": out.strip(),
                            "seconds": round(time.time() - t, 1)}, ensure_ascii=False) + "\\n")
"""


def main():
    setup()
    sh(f"python - <<'PY'\n{MERGE % (MODEL, ADAPTER, MODEL)}\nPY")
    sh("git clone --depth 1 https://github.com/ggml-org/llama.cpp")
    sh("pip install -q -r llama.cpp/requirements/requirements-convert_hf_to_gguf.txt")
    sh("python llama.cpp/convert_hf_to_gguf.py merged --outtype f16 --outfile models/tuned-f16.gguf")
    sh("cmake -S llama.cpp -B llama.cpp/build -DGGML_CUDA=OFF -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release")
    sh("cmake --build llama.cpp/build -j 4 --target llama-quantize llama-bench")
    sh(f"llama.cpp/build/bin/llama-quantize models/tuned-f16.gguf {GGUF} Q4_K_M")
    sh("ls -la models/")
    # pp128 = reading a 128-token prompt, tg64 = writing 64 tokens. Peak RAM = max RSS of the bench process.
    os.makedirs(f"{REPO}/outputs", exist_ok=True)
    sh(f"python - <<'PY'\n{BENCH % GGUF}\nPY")
    try:  # llama-completion is the non-chat CLI in recent llama.cpp; the smoke test is optional
        sh("cmake --build llama.cpp/build -j 4 --target llama-completion")
        sh(f"python - <<'PY'\n{SMOKE % GGUF}\nPY")
    except subprocess.CalledProcessError as e:
        print("smoke test failed (bench results are still saved):", e)
    os.makedirs(f"{WORK}/models", exist_ok=True)
    shutil.copy(f"{REPO}/{GGUF}", f"{WORK}/{GGUF}")
    shutil.copytree(f"{REPO}/outputs", f"{WORK}/outputs", dirs_exist_ok=True)
    shutil.rmtree(REPO)


if __name__ == "__main__":
    main()
