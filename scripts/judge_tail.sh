#!/usr/bin/env bash
# After judge_chain.sh has judged A2: a fill-in pass for A2 (labels that failed on network errors), then A3 on its
# 350-question half (D29) once all 350 answers exist, then one fill-in pass over every run (cached, cheap).
export PYTHONIOENCODING=utf-8
F=outputs/final
J="--judge gemini --workers 12 --out-dir $F"
until grep -q "^A2: scored" logs/judge_chain_2.log; do sleep 30; done
echo "== $(date +%H:%M) A2 fill-in"; python -m src.eval.score --run A2 --outputs $F/cloud_A2.jsonl --subset test $J
until grep -q "a3 half done\|fault injection" logs/a3_half.log; do sleep 60; done
for i in 1 2; do echo "== $(date +%H:%M) A3 (pass $i)"; python -m src.eval.score --run A3 --outputs $F/cloud_A3.jsonl --subset test $J; done
for r in B1 A2; do python -m src.eval.score --run $r --outputs $F/cloud_$r.jsonl --subset test $J; done
echo "== $(date +%H:%M) judge tail done"
