#!/usr/bin/env bash
# Final-phase pipeline, in order. Every number in reports/final/ comes from these commands.
# Heavy GPU steps run on Kaggle (kaggle/jobs/06-08); Gemini-API steps are cached and resumable, so re-running a step
# costs nothing for answers already made. Run from the repo root with .env filled in (see README).
set -euo pipefail
export PYTHONIOENCODING=utf-8
AGENT=gemma-4-26b-a4b-it                # cloud agent for B1 / A2 / A3 (DECISIONS.md D19)
export GEMINI_THINKING=minimal GEMINI_RPM=28 GEMINI_TPM=15000
Q=data/processed/questions.jsonl
F=outputs/final

step() { echo; echo "== $*"; }

step "0. router labels, keywords, classifier, red-team sets (all cached / deterministic)"
python -m src.router_gate.intent_clf
python -m src.router_gate.make_redteam_v2 --version 2
python -m src.router_gate.make_redteam_v2 --version 3
python -m src.router_gate.eval_router            # -> outputs/router_metrics.json

step "1. edge model on Kaggle: B2/B3 on test+calib+dev, BhashaBench, seed re-runs, 4-bit GGUF"
if [ "${SKIP_KAGGLE:-0}" != 1 ]; then
  python kaggle/push_code.py "final phase"
  kaggle kernels push -p kaggle/jobs/06_edge_full --accelerator NvidiaTeslaT4
  kaggle kernels push -p kaggle/jobs/07_reruns --accelerator NvidiaTeslaT4
  kaggle kernels push -p kaggle/jobs/08_gguf
  echo "wait for the three jobs (kaggle kernels status ...), then:"
  echo "  kaggle kernels output roshanned/kisan-edge-06-edge-full -p kaggle/results/06_edge_full"
  echo "  kaggle kernels output roshanned/kisan-edge-07-reruns -p kaggle/results/07_reruns"
  echo "  kaggle kernels output roshanned/kisan-edge-08-gguf -p kaggle/results/08_gguf"
fi
cp kaggle/results/06_edge_full/outputs/{edge_base_full,edge_tuned_full,bhashabench_base,bhashabench_tuned}.jsonl $F/
cp kaggle/results/07_reruns/outputs/edge_tuned_s{1,2}.jsonl $F/
cp kaggle/results/08_gguf/outputs/llamacpp_{bench.json,smoke.jsonl} $F/
python -m src.edge.bench_llamacpp --bin tools_ext/llamacpp/bin --model kaggle/results/08_gguf/models/kisan-edge-3b-Q4_K_M.gguf

step "2. cloud runs on the 700 test questions (resumable; rerun after a quota stop)"
for RUN in B1 A2; do
  python -m src.cloud.query --questions $Q --split test --run $RUN --model $AGENT --as-of 2026-10-30 \
      --workers 6 --out $F/cloud_$RUN.jsonl
done
# A3 on the stratified 350-question half (docs/DECISIONS.md D29)
python -m src.cloud.query --questions $Q --split test --run A3 --model $AGENT --as-of 2026-10-30 \
    --workers 6 --ids data/processed/test_half_ids.txt --out $F/cloud_A3.jsonl

step "3. judge (JUDGE_MODEL in .env = gemma-4-31b-it)"
J="--judge gemini --workers 10 --out-dir $F"
python -m src.eval.score --run B3 --outputs $F/edge_tuned_full.jsonl --subset test $J
python -m src.eval.score --run B3_calib --outputs $F/edge_tuned_full.jsonl --subset calib $J
python -m src.eval.score --run B3_dev --outputs $F/edge_tuned_full.jsonl --subset dev $J
python -m src.eval.score --run B2 --outputs $F/edge_base_full.jsonl --subset test $J
for RUN in B1 A2 A3; do python -m src.eval.score --run $RUN --outputs $F/cloud_$RUN.jsonl --subset test $J; done
# seed re-runs: Hindi (Devanagari) test questions only, the H2 subset (judge quota, docs/DECISIONS.md D26)
for S in 1 2; do python -m src.eval.score --run B3_s$S --outputs $F/edge_tuned_s$S.jsonl --subset test --script deva $J; done

step "4. cloud metrics: Recall@5, tools, citations (+ faithfulness on 60 sentences), abstention, fault injection"
python -m src.cloud.rag.make_recall_queries
python -m src.cloud.rag.recall_check --rewrite --model $AGENT --out $F/rag_recall.json
python -m src.cloud.metrics --runs B1,A2,A3 --faithfulness 60
python -m src.cloud.fault_injection --n 20 --model $AGENT

step "5. gate, hybrids (H, R, A1, A4, traces), H1/H2/H3, tables and figures"
python -m src.eval.run_final                     # -> $F/summary.json, reports/final/tables, reports/final/figures
python -m src.eval.judge_check --dir $F judges --n 150 --model gemini-3.5-flash-lite   # judge vs a second judge
python -m src.eval.judge_check --dir $F --report-dir reports/final sample --n 100      # sheet for the human check (MANUAL)
