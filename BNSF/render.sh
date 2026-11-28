#!/usr/bin/env bash
# 全片渲染：4 进程并行分段渲染（每帧同时出竖版与横版）→ 拼接 → 与混音合成 → 竖版、横版两条成片（第二季第一期起不再出预览版）
set -euo pipefail
cd "$(dirname "$0")"
WORK=${WORK:-work}
N=$(python3 -c "import json;print(int(round(json.load(open('$WORK/timeline.json'))['total']*30)))")
P=4; STEP=$(( (N + P - 1) / P ))
if [ -z "${SKIP_RENDER:-}" ]; then            # SKIP_RENDER=1：分段已渲染（或已用 src/patch_render.py 局部重渲染），只重新合成
rm -f $WORK/slow.log $WORK/loop.log
for k in $(seq 0 $((P-1))); do
  SLOWLOG=$WORK/slow.log LOOPLOG=$WORK/loop.log python3 src/film.py $WORK chunk $((k*STEP)) $(((k+1)*STEP)) $WORK/seg$k.mp4 > $WORK/render$k.log 2>&1 &
done
wait
fi
NAME="全押美国_巴菲特与BNSF"
for V in "" "_h"; do
  printf "file '%s'\n" $(for k in $(seq 0 $((P-1))); do echo "$PWD/$WORK/seg$k$V.mp4"; done) > $WORK/list$V.txt
  ffmpeg -loglevel error -y -f concat -safe 0 -i $WORK/list$V.txt -i $WORK/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "$WORK/master$V.mp4"
done
# 成片：x264 CRF 17 + slow（画面不加颗粒、不降噪，字边锐利）
ffmpeg -loglevel error -y -i "$WORK/master.mp4" -c:v libx264 -crf 17 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "${NAME}_竖版.mp4"
ffmpeg -loglevel error -y -i "$WORK/master_h.mp4" -c:v libx264 -crf 17 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "${NAME}_横版.mp4"
ls -la "${NAME}_竖版.mp4" "${NAME}_横版.mp4"
[ -s $WORK/loop.log ] && { echo "素材不够、循环重放的镜头："; sort -u $WORK/loop.log; }
echo done; [ -s $WORK/slow.log ] && { echo "慢放镜头："; sort -u $WORK/slow.log; } || echo "无低于 0.62 倍的慢放镜头"
