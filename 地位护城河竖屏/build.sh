#!/usr/bin/env bash
# 一键重建《多付的钱，买的是什么｜身份成为护城河的三道关》竖屏短视频（护城河系列第 01 期 · 1080×1920 · 30fps）
# 依赖：ffmpeg、fluidsynth + FluidR3_GM、python3（numpy opencv-python-headless pillow soundfile scipy pretty_midi pyloudnorm fonttools）
# 旁白：豆包 Seed-TTS 3.0（voice.cn-beijing.volces.com，X-Api-Key 由环境代理注入）；品牌角标取自仓库根目录 brand/
set -euo pipefail
cd "$(dirname "$0")"; WORK=work; mkdir -p $WORK
python3 src/get_fonts.py
python3 src/fetch_titles.py   # Wikimedia Commons 图片 / 视频（限速，有缓存）
src/fetch_clips.sh
python3 src/tts_single.py $WORK 6      # 整篇一次合成（无接缝）6 条候选，选音高最平的一条，残余漂移 ≤2 半音平滑修正（有缓存）
python3 src/voice_qc_single.py $WORK   # 旁白一致性验收：60 秒窗音高、斜率、响度、谐噪比
python3 src/timeline.py $WORK
python3 ../视频脚本/export_script.py . 01 "多付的钱，买的是什么｜身份成为护城河的三道关"   # 定稿脚本单独存档：视频脚本/01_*.md
python3 src/music.py $WORK
python3 src/mix.py $WORK
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
NF=$(python3 src/video.py $WORK nf); P=4; STEP=$(( (NF + P - 1) / P ))
for k in $(seq 0 $((P-1))); do python3 src/video.py $WORK chunk $((k*STEP)) $(((k+1)*STEP)) $WORK/seg$k.mp4 > $WORK/seg$k.log 2>&1 & done; wait
printf "file '%s'\n" seg0.mp4 seg1.mp4 seg2.mp4 seg3.mp4 > $WORK/list.txt
ffmpeg -v error -y -f concat -safe 0 -i $WORK/list.txt -i $WORK/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -ar 48000 \
  -shortest $WORK/master_crf20.mp4
# 成片：两遍编码到约 93MB（7 分 44 秒，约 1.42 Mbps）（仓库 LFS 额度已满，按普通文件入库，须小于 100MB）；只出成片，不出预览版
(cd $WORK && ffmpeg -v error -y -i master_crf20.mp4 -c:v libx264 -preset slow -b:v 1420k -tune animation -pass 1 -passlogfile p2 -an -f null /dev/null && \
  ffmpeg -v error -y -i master_crf20.mp4 -c:v libx264 -preset slow -b:v 1420k -tune animation -maxrate 4500k -bufsize 6000k -pass 2 -passlogfile p2 \
  -c:a aac -b:a 160k -movflags +faststart "../多付的钱买的是什么.mp4")
echo "done -> 多付的钱买的是什么.mp4"
