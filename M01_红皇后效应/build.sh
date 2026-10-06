#!/usr/bin/env bash
# 一键重建 M01《产品越来越强，为什么优势却未必变大？》——红皇后效应
# 依赖: ffmpeg, python3 (numpy scipy opencv-python-headless pillow soundfile)
# 品牌角标与 logo 取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); WORK="$ROOT/work"; mkdir -p "$WORK" fonts
OUT="$ROOT/M01_产品越来越强为什么优势却未必变大_红皇后效应.mp4"
# 1) 字体（Google Fonts）
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Serif+SC 300 serif_light; get Noto+Serif+SC 500 serif_med; get Noto+Serif+SC 900 serif_black
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 500 sans_med; get Noto+Sans+SC 900 sans_black
get Cormorant+Garamond 500 corm; get Cormorant+Garamond 600 corm_semi; get Orbitron 700 orb; get JetBrains+Mono 400 mono
python3 src/timeline.py > "$WORK/captions_check.txt"       # 字幕阅读速度校验（≤6 字/秒）
# 2) 原创配乐 + 低频转场音效
(cd src && python3 music.py "$WORK")
# 3) 逐帧渲染（4 进程并行，共 7440 帧）
for k in 0 1 2 3; do (cd src && python3 video.py chunk $((k*1860)) $(((k+1)*1860)) "$WORK/seg$k.mp4") & done; wait
printf "file '%s'\n" "$WORK"/seg{0,1,2,3}.mp4 > "$WORK/list.txt"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -i "$WORK/mix.wav" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "$OUT"
echo "done -> $OUT"
