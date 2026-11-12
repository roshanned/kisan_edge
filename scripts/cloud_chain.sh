#!/usr/bin/env bash
# Cloud runs that share the agent model's quota, one after the other. Resumable: re-run after any stop.
#  1. wait until B1 has all 700 answers (start it separately, or this script resumes it)
#  2. regenerate B1 from the response cache with the current safety filter (DECISIONS.md D27; no new API calls)
#  3. A2, A3 (resume if partly done), then fault injection
export PYTHONIOENCODING=utf-8
F=outputs/final
Q="--questions data/processed/questions.jsonl --split test --as-of 2026-10-30 --workers 8"
n() { [ -f "$1" ] && grep -c . "$1" || echo 0; }

until [ "$(n $F/cloud_B1.jsonl)" -ge 700 ]; do
  echo "== $(date +%H:%M) B1 at $(n $F/cloud_B1.jsonl)/700, resuming"
  python -m src.cloud.query $Q --run B1 --out $F/cloud_B1.jsonl >> logs/cloud_B1.log 2>&1
done
if [ ! -f $F/.B1_regenerated ]; then
  echo "== $(date +%H:%M) regenerating B1 from cache"
  rm -f $F/cloud_B1_regen.jsonl
  until [ "$(n $F/cloud_B1_regen.jsonl)" -ge 700 ]; do
    python -m src.cloud.query $Q --run B1 --out $F/cloud_B1_regen.jsonl >> logs/cloud_B1_regen.log 2>&1
  done
  mv $F/cloud_B1.jsonl logs/cloud_B1_old_filter.jsonl && mv $F/cloud_B1_regen.jsonl $F/cloud_B1.jsonl && touch $F/.B1_regenerated
fi
for RUN in A2 A3; do
  until [ "$(n $F/cloud_$RUN.jsonl)" -ge 700 ]; do
    echo "== $(date +%H:%M) $RUN at $(n $F/cloud_$RUN.jsonl)/700"
    python -m src.cloud.query $Q --run $RUN --out $F/cloud_$RUN.jsonl >> logs/cloud_$RUN.log 2>&1
  done
done
[ -f $F/fault_injection.json ] || { echo "== $(date +%H:%M) fault injection"; python -m src.cloud.fault_injection --n 20 --workers 6; }
echo "== $(date +%H:%M) cloud chain done"
