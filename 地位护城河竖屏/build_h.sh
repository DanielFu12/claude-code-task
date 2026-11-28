#!/usr/bin/env bash
# 横版（1920×1080 · 30fps）：与竖版共用旁白、配乐、混音和时间线，只重新渲染画面。
# 先跑过 ./build.sh（生成 work/ 里的 timeline、hits.json、mix.wav），再跑本脚本。
set -euo pipefail
cd "$(dirname "$0")"; WORK=work
[ -f $WORK/mix.wav ] && [ -f $WORK/hits.json ] || { echo "先运行 ./build.sh"; exit 1; }
src/fetch_clips.sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
NF=$(python3 src/video_h.py $WORK nf); P=4; STEP=$(( (NF + P - 1) / P ))
for k in $(seq 0 $((P-1))); do python3 src/video_h.py $WORK chunk $((k*STEP)) $(((k+1)*STEP)) $WORK/hseg$k.mp4 > $WORK/hseg$k.log 2>&1 & done; wait
printf "file '%s'\n" hseg0.mp4 hseg1.mp4 hseg2.mp4 hseg3.mp4 > $WORK/hlist.txt
ffmpeg -v error -y -f concat -safe 0 -i $WORK/hlist.txt -i $WORK/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -ar 48000 \
  -shortest $WORK/hmaster_crf20.mp4
# 成片：两遍编码约 93MB（须小于 100MB，按普通文件入库）；只出成片，不出预览版
(cd $WORK && ffmpeg -v error -y -i hmaster_crf20.mp4 -c:v libx264 -preset slow -b:v 1420k -tune animation -pass 1 -passlogfile h2 -an -f null /dev/null && \
  ffmpeg -v error -y -i hmaster_crf20.mp4 -c:v libx264 -preset slow -b:v 1420k -tune animation -maxrate 4500k -bufsize 6000k -pass 2 -passlogfile h2 \
  -c:a aac -b:a 160k -movflags +faststart "../多付的钱买的是什么_横版.mp4")
echo "done -> 多付的钱买的是什么_横版.mp4"
