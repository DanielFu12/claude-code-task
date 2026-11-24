#!/usr/bin/env bash
# 逐条评估 WORK/vo_take/roll_*.wav：设为正式录音 → 对齐 → 逐句识别；结果写 WORK/rolls_eval.txt
set -u; WORK=${1:-work}; cd "$(dirname "$0")/.."
: > $WORK/rolls_eval.txt
for f in $WORK/vo_take/roll_*.wav; do
  python3 src/take_rolls.py $WORK pick "$f" >/dev/null
  if ! python3 src/voice_build.py $WORK > $WORK/vb_roll.log 2>&1; then echo "$f  ALIGN-CRASH" >> $WORK/rolls_eval.txt; continue; fi
  fails=$(grep -A6 "alignment check" $WORK/vo/report.txt | grep -c "own\|长度")
  sum=$(python3 src/check_vo.py $WORK 2>&1 | tail -1)
  echo "$f  align_fails=$fails  $sum" >> $WORK/rolls_eval.txt
  python3 src/check_vo.py $WORK 2>&1 | grep -v "相似度 1.000" | grep -v "「她」 识别「他」\|「得」 识别「的」\|「地」 识别「的」\|「它」 识别「他」" | grep -B1 "脚本" > "${f%.wav}.check.txt"
done
cat $WORK/rolls_eval.txt
