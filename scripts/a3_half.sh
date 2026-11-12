#!/usr/bin/env bash
# A3 (RAG, no tools) on the stratified 350-question half (data/processed/test_half_ids.txt; DECISIONS.md D29),
# then tool fault injection. Waits for A2 to finish first, since both use the agent model's quota.
export PYTHONIOENCODING=utf-8
F=outputs/final
n() { [ -f "$1" ] && grep -c . "$1" || echo 0; }
until [ "$(n $F/cloud_A2.jsonl)" -ge 700 ]; do sleep 30; done
# cloud_chain.sh would now start A3 on all 700 questions: stop it (only that script and its A3 run)
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match 'cloud_chain\.sh' -or (\$_.CommandLine -match 'src\.cloud\.query' -and \$_.CommandLine -match '--run A3') } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force }"
until [ "$(python -c "import json; ids=set(open('data/processed/test_half_ids.txt').read().split()); print(sum(json.loads(l)['id'] in ids for l in open('$F/cloud_A3.jsonl', encoding='utf-8')) if __import__('os').path.exists('$F/cloud_A3.jsonl') else 0)")" -ge 350 ]; do
  echo "== $(date +%H:%M) A3 half"
  python -m src.cloud.query --questions data/processed/questions.jsonl --split test --as-of 2026-10-30 --workers 8 \
      --run A3 --ids data/processed/test_half_ids.txt --out $F/cloud_A3.jsonl >> logs/cloud_A3.log 2>&1
done
[ -f $F/fault_injection.json ] || { echo "== $(date +%H:%M) fault injection"; python -m src.cloud.fault_injection --n 20 --workers 6; }
echo "== $(date +%H:%M) a3 half done"
