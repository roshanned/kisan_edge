"""llama.cpp speed and peak RAM of the 4-bit B3 model on this machine's CPU (PLAN.md section 4, Roshan step 3).

Runs llama-bench (pp128 = read a 128-token prompt, tg64 = write 64 tokens, 3 repetitions) for each thread count and
samples the process's resident memory to get its peak. -> outputs/final/llamacpp_bench_laptop.json
Usage: python -m src.edge.bench_llamacpp --bin tools_ext/llamacpp/bin --model kaggle/results/08_gguf/models/kisan-edge-3b-Q4_K_M.gguf
"""
import argparse
import json
import platform
import subprocess
import time
from pathlib import Path

import psutil


def bench(exe, model, threads):
    p = subprocess.Popen([str(exe), "-m", model, "-t", str(threads), "-p", "128", "-n", "64", "-r", "3", "-o", "json"],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    proc, peak = psutil.Process(p.pid), 0
    while p.poll() is None:
        try:
            peak = max(peak, proc.memory_info().rss)
        except psutil.Error:
            break
        time.sleep(0.05)
    runs = json.loads(p.stdout.read())
    return {"threads": threads, "peak_rss_gb": round(peak / 1e9, 2),
            "prompt_tok_s": round(next(r["avg_ts"] for r in runs if r["n_prompt"]), 1),
            "gen_tok_s": round(next(r["avg_ts"] for r in runs if r["n_gen"]), 1),
            "cpu": runs[0].get("cpu_info"), "model_size_gb": round(runs[0]["model_size"] / 1e9, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--threads", default="4,8")
    ap.add_argument("--out", default="outputs/final/llamacpp_bench_laptop.json")
    a = ap.parse_args()
    exe = Path(a.bin) / ("llama-bench.exe" if platform.system() == "Windows" else "llama-bench")
    res = {"machine": platform.processor() or platform.machine(), "logical_cpus": psutil.cpu_count(),
           "ram_gb": round(psutil.virtual_memory().total / 1e9, 1),
           "runs": [bench(exe, a.model, int(t)) for t in a.threads.split(",")]}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
