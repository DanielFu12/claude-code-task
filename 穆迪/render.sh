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
# 高清版（1080×1920）：v4 起画面不加颗粒、不再降噪（降噪会把字边抹软），CRF 17 + slow
ffmpeg -loglevel error -y -i "$OUT" -c:v libx264 -crf 17 -preset slow -pix_fmt yuv420p \
  -c:a aac -b:a 192k -movflags +faststart "一张支票换一句话_巴菲特与内布拉斯加家具城_高清版.mp4"
# 预览版（入库，≤ 30MB）：v4 改为 1080×1920 HEVC 两遍编码（同样体积下比 720p H.264 清晰得多；hvc1 标签，苹果/安卓/浏览器可直接播放）
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")
VB=$(python3 -c "print(int(28.8e6 * 8 / 1000 / $D - 80))")      # 目标 ≤ 28.8 MB（十进制），留出容器开销
PV="一张支票换一句话_巴菲特与内布拉斯加家具城_预览版.mp4"
XP="log-level=error:aq-mode=3:psy-rd=1.5:deblock=-1,-1"
ffmpeg -loglevel error -y -i "$OUT" -c:v libx265 -b:v ${VB}k -preset slow -x265-params "pass=1:stats=$WORK/x265pv.log:$XP" -pix_fmt yuv420p -an -f mp4 /dev/null
ffmpeg -loglevel error -y -i "$OUT" -c:v libx265 -b:v ${VB}k -preset slow -x265-params "pass=2:stats=$WORK/x265pv.log:$XP:vbv-maxrate=$((VB*3)):vbv-bufsize=$((VB*4))" \
  -pix_fmt yuv420p -tag:v hvc1 -c:a aac -b:a 80k -movflags +faststart "$PV"
ls -la "$OUT" "$PV" "一张支票换一句话_巴菲特与内布拉斯加家具城_高清版.mp4"
[ -s $WORK/loop.log ] && { echo "素材不够、循环重放的镜头："; sort -u $WORK/loop.log; }
echo done; [ -s $WORK/slow.log ] && { echo "慢放镜头："; sort -u $WORK/slow.log; } || echo "无低于 0.62 倍的慢放镜头"
