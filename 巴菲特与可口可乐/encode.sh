#!/usr/bin/env bash
# 只做最终编码（成片 + 30MB 预览版）：./encode.sh
set -euo pipefail
cd "$(dirname "$0")"
WORK=work; NAME="38年一股未卖_巴菲特与可口可乐"
# 正式成片（高码率 H.264 High，AAC 256k）
ffmpeg -loglevel error -y -i "$WORK/video.mp4" -i "$WORK/mix.wav" -map 0:v -map 1:a \
  -c:v libx264 -preset slow -crf 18 -maxrate 9M -bufsize 18M -pix_fmt yuv420p -profile:v high -tag:v avc1 \
  -af volume=-1.2dB -c:a aac -b:a 256k -movflags +faststart -shortest "$NAME.mp4"
# 30MB 以内预览版（两遍编码，按时长算码率）
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$WORK/video.mp4")
VB=$(python3 -c "print(int((27.0*8*1024*1024/$DUR - 128000)/1000))")
ffmpeg -loglevel error -y -i "$WORK/video.mp4" -c:v libx264 -preset slow -b:v ${VB}k -pass 1 -an -f mp4 -passlogfile "$WORK/p2" /dev/null
ffmpeg -loglevel error -y -i "$WORK/video.mp4" -i "$WORK/mix.wav" -map 0:v -map 1:a -c:v libx264 -preset slow -b:v ${VB}k -pass 2 \
  -passlogfile "$WORK/p2" -pix_fmt yuv420p -af volume=-1.2dB -c:a aac -b:a 128k -movflags +faststart -shortest "${NAME}_预览版.mp4"
ls -la "$NAME.mp4" "${NAME}_预览版.mp4"
