#!/usr/bin/env bash
# 一键重建《社会地位象征型护城河》视频（无配音：原创配乐 + 动态视觉 + 关键文字 + 数据可视化）
# 依赖: ffmpeg, python3 (numpy scipy opencv-python-headless pillow soundfile)
# 品牌角标取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); WORK="$ROOT/work"; mkdir -p "$WORK" fonts
OUT="$ROOT/社会地位象征型护城河.mp4"
# 1) 字体（Google Fonts）
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Serif+SC 300 serif_light; get Noto+Serif+SC 500 serif_med; get Noto+Serif+SC 900 serif_black
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 500 sans_med; get Noto+Sans+SC 900 sans_black
get Cormorant+Garamond 500 corm; get Orbitron 700 orb; get JetBrains+Mono 400 mono; get Bebas+Neue 400 bebas
# 2) 原创配乐（程序化合成，120 BPM，与画面逐小节对齐）
(cd src && python3 music.py "$WORK/bgm.wav")
# 3) 逐帧渲染（4 进程并行，共 376 秒 × 30fps = 11280 帧）
N=11280; K=4; S=$(( (N + K - 1) / K ))
for k in $(seq 0 $((K-1))); do (cd src && python3 video.py chunk $((k*S)) $(( (k+1)*S < N ? (k+1)*S : N )) "$WORK/seg$k.mp4") & done; wait
for k in $(seq 0 $((K-1))); do echo "file '$WORK/seg$k.mp4'"; done > "$WORK/list.txt"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -i "$WORK/bgm.wav" \
  -map 0:v -map 1:a -c:v copy -af "loudnorm=I=-14:TP=-1.5:LRA=11" -c:a aac -b:a 192k -ar 48000 -shortest \
  -movflags +faststart "$OUT"
echo "done -> $OUT"
