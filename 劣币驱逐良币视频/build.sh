#!/usr/bin/env bash
# 一键重建《谁杀死了好东西？——劣币驱逐良币》竖屏视频（1080×1920 · 30fps）
# 依赖: ffmpeg, python3 (numpy opencv-python-headless pillow soundfile fonttools)
# 品牌角标与片尾品牌元素取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); WORK="$ROOT/work"; mkdir -p "$WORK" fonts
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Serif+SC 400 serif_reg; get Noto+Serif+SC 600 serif_semi; get Noto+Serif+SC 900 serif_black
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 500 sans_med; get Noto+Sans+SC 900 sans_black
get Cormorant+Garamond 600 corm; get Cormorant+Garamond 500 corm_med; get JetBrains+Mono 500 mono; get Oswald 500 oswald
# 1) 配乐：Lyria 原创配乐按节拍拼接延长 + 低频转场音效
python3 src/audio.py "$WORK"
# 2) 逐帧渲染（4 进程并行，无损级中间片段）
N=$(python3 -c "import sys; sys.path.insert(0,'src'); from timeline import DUR; print(int(DUR*30))")
Q=$(( (N + 3) / 4 ))
cd src
for k in 0 1 2 3; do a=$((k*Q)); b=$(( (k+1)*Q < N ? (k+1)*Q : N )); python3 run.py chunk $a $b "$WORK/seg$k.mp4" & done; wait
cd ..
printf "file '%s'\n" "$WORK"/seg{0,1,2,3}.mp4 > "$WORK/list.txt"
OUT="$ROOT/谁杀死了好东西_劣币驱逐良币_1080x1920.mp4"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -i "$WORK/score.wav" -map 0:v -map 1:a \
  -c:v libx264 -preset slow -crf 19 -pix_fmt yuv420p -profile:v high -af "loudnorm=I=-14:TP=-1.0:LRA=11" -ar 48000 -c:a aac -b:a 256k -shortest -movflags +faststart "$OUT"
# 3) 30MB 以内的预览版（两遍编码按体积定码率）
DURS=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")
VB=$(python3 -c "print(int((27.0*8*1024*1024/$DURS - 128000)/1000))")
PREV="$ROOT/预览版_30MB以内.mp4"
ffmpeg -loglevel error -y -i "$OUT" -c:v libx264 -preset slow -b:v ${VB}k -pass 1 -an -f mp4 -passlogfile "$WORK/p2" /dev/null
ffmpeg -loglevel error -y -i "$OUT" -c:v libx264 -preset slow -b:v ${VB}k -pass 2 -passlogfile "$WORK/p2" -c:a aac -b:a 128k -movflags +faststart "$PREV"
ls -la "$OUT" "$PREV"
