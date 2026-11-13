#!/usr/bin/env bash
# 全片渲染：4 进程并行分段渲染 → 拼接 → 与混音合成 → 成片 + 30MB 预览版
set -euo pipefail
cd "$(dirname "$0")"
WORK=${WORK:-work}
N=$(python3 -c "import json;print(int(round(json.load(open('$WORK/timeline.json'))['total']*30)))")
P=4; STEP=$(( (N + P - 1) / P ))
rm -f $WORK/slow.log
for k in $(seq 0 $((P-1))); do
  SLOWLOG=$WORK/slow.log python3 src/film.py $WORK chunk $((k*STEP)) $(((k+1)*STEP)) $WORK/seg$k.mp4 > $WORK/render$k.log 2>&1 &
done
wait
printf "file '%s'\n" $(for k in $(seq 0 $((P-1))); do echo "$PWD/$WORK/seg$k.mp4"; done) > $WORK/list.txt
OUT="二十年后的补票_巴菲特为什么出手谷歌.mp4"
ffmpeg -loglevel error -y -f concat -safe 0 -i $WORK/list.txt -i $WORK/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "$OUT"
# 预览版：控制在 30MB 以内
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")
VB=$(python3 -c "print(int((29.0*8*1024)/$D - 96))")
ffmpeg -loglevel error -y -i "$OUT" -vf scale=720:-2 -c:v libx264 -b:v ${VB}k -maxrate $((VB*2))k -bufsize $((VB*2))k -preset slow -c:a aac -b:a 96k -movflags +faststart "二十年后的补票_巴菲特为什么出手谷歌_预览版.mp4"
echo done; [ -s $WORK/slow.log ] && { echo "慢放镜头："; sort -u $WORK/slow.log; } || echo "无低于 0.62 倍的慢放镜头"
