#!/usr/bin/env bash
# 一键重建《低价格，不是护城河》竖屏短视频（1080×1920 · 30fps）
# 依赖：ffmpeg、fluidsynth + FluidR3_GM、python3（numpy opencv-python-headless pillow soundfile scipy pretty_midi pyloudnorm fonttools）
# 旁白：豆包 Seed-TTS 3.0（voice.cn-beijing.volces.com，X-Api-Key 由环境代理注入）；品牌角标取自仓库根目录 brand/
set -euo pipefail
cd "$(dirname "$0")"; WORK=work; mkdir -p $WORK
python3 src/get_fonts.py
src/fetch_clips.sh
python3 src/tts_take.py $WORK          # 整篇一次合成 + 按逐字时间戳切句（有缓存）
python3 src/timeline.py $WORK
python3 src/music.py $WORK
python3 src/mix.py $WORK
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
NF=$(python3 src/video.py $WORK nf); P=4; STEP=$(( (NF + P - 1) / P ))
for k in $(seq 0 $((P-1))); do python3 src/video.py $WORK chunk $((k*STEP)) $(((k+1)*STEP)) $WORK/seg$k.mp4 > $WORK/seg$k.log 2>&1 & done; wait
printf "file '%s'\n" seg0.mp4 seg1.mp4 seg2.mp4 seg3.mp4 > $WORK/list.txt
ffmpeg -v error -y -f concat -safe 0 -i $WORK/list.txt -i $WORK/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -ar 48000 \
  -shortest -movflags +faststart "低价格不是护城河.mp4"
echo "done -> 低价格不是护城河.mp4"
