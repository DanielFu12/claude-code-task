#!/usr/bin/env bash
# 全片渲染：4 进程并行分段渲染 → 拼接 → 与混音合成 → 成片 + 高清版 + 30MB 预览版
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
printf "file '%s'\n" $(for k in $(seq 0 $((P-1))); do echo "$PWD/$WORK/seg$k.mp4"; done) > $WORK/list.txt
OUT="一张支票换一句话_巴菲特与内布拉斯加家具城.mp4"
ffmpeg -loglevel error -y -f concat -safe 0 -i $WORK/list.txt -i $WORK/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "$OUT"
# 高清版（1080×1920，便于分享观看）：轻度降噪去掉胶片颗粒的“噪点码率”，CRF 21 + slow
ffmpeg -loglevel error -y -i "$OUT" -vf "hqdn3d=1.0:1.0:4:4" -c:v libx264 -crf 21 -preset slow -tune film -pix_fmt yuv420p \
  -c:a aac -b:a 192k -movflags +faststart "一张支票换一句话_巴菲特与内布拉斯加家具城_高清版.mp4"
# 预览版（入库，≤ 30MB）：720×1280，两遍编码；先降噪，码率留给文字与画面细节
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")
VB=$(python3 -c "print(int(28.8e6 * 8 / 1000 / $D - 80))")      # 目标 ≤ 28.8 MB（十进制），留出容器开销
PV="一张支票换一句话_巴菲特与内布拉斯加家具城_预览版.mp4"
VF="hqdn3d=2.0:2.0:6:6,scale=720:-2:flags=lanczos"
ffmpeg -loglevel error -y -i "$OUT" -vf "$VF" -c:v libx264 -b:v ${VB}k -preset slow -tune film -pass 1 -passlogfile $WORK/x264pv -an -f mp4 /dev/null
ffmpeg -loglevel error -y -i "$OUT" -vf "$VF" -c:v libx264 -b:v ${VB}k -maxrate $((VB*3))k -bufsize $((VB*4))k -preset slow -tune film -pass 2 \
  -passlogfile $WORK/x264pv -c:a aac -b:a 80k -movflags +faststart "$PV"
ls -la "$OUT" "$PV" "一张支票换一句话_巴菲特与内布拉斯加家具城_高清版.mp4"
[ -s $WORK/loop.log ] && { echo "素材不够、循环重放的镜头："; sort -u $WORK/loop.log; }
echo done; [ -s $WORK/slow.log ] && { echo "慢放镜头："; sort -u $WORK/slow.log; } || echo "无低于 0.62 倍的慢放镜头"
