#!/usr/bin/env bash
# Cloud runs that share the agent model's quota, one after the other (B1 must be complete first).
export PYTHONIOENCODING=utf-8
F=outputs/final
until [ "$(grep -c . $F/cloud_B1.jsonl)" -ge 700 ]; do sleep 60; done
for RUN in A2 A3; do
  echo "== $(date +%H:%M) $RUN"
  python -m src.cloud.query --questions data/processed/questions.jsonl --split test --run $RUN --as-of 2026-10-30 \
      --workers 8 --out $F/cloud_$RUN.jsonl
done
echo "== $(date +%H:%M) fault injection"
python -m src.cloud.fault_injection --n 20 --workers 6
echo "== $(date +%H:%M) cloud chain done"
