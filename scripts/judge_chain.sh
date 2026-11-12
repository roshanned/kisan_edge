#!/usr/bin/env bash
# One judge process at a time (the judge model's per-minute token budget is shared). Order = what the report needs
# first. Re-running is cheap: every judged answer is cached in outputs/cache/judge_cache.jsonl.
# Usage: bash scripts/judge_chain.sh [run ...]   (default: the edge runs; cloud runs once their answer files are complete)
export PYTHONIOENCODING=utf-8
F=outputs/final
J="--judge gemini --workers 20 --out-dir $F"
judge() {  # run, outputs file, subset, [extra args]
  echo "== $(date +%H:%M) judging $1"
  python -m src.eval.score --run "$1" --outputs "$2" --subset "$3" ${4:-} $J
}
[ $# -eq 0 ] && set -- B3 B2 B3_calib B3_dev
for run in "$@"; do
  case $run in
    B3) judge B3 $F/edge_tuned_full.jsonl test ;;
    B2) judge B2 $F/edge_base_full.jsonl test ;;
    B3_calib) judge B3_calib $F/edge_tuned_full.jsonl calib ;;
    B3_dev) judge B3_dev $F/edge_tuned_full.jsonl dev ;;
    B1|A2|A3)  # wait until the cloud run has all 700 answers
      until [ -f $F/cloud_$run.jsonl ] && [ "$(grep -c . $F/cloud_$run.jsonl)" -ge 700 ] \
            && { [ $run != B1 ] || [ -f $F/.B1_regenerated ]; }; do sleep 60; done  # B1: after the D27 regeneration
      judge $run $F/cloud_$run.jsonl test ;;
    B3_s1|B3_s2) judge $run $F/edge_tuned_${run#B3_}.jsonl test "--script deva" ;;
  esac
done
echo "== $(date +%H:%M) judge chain done"
