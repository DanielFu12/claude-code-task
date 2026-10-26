#!/usr/bin/env bash
# 一键重建《投资的教训》视频
# 依赖: ffmpeg, python3 (numpy opencv-python-headless pillow soundfile librosa)
# 品牌角标取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); WORK="$ROOT/work"; mkdir -p "$WORK" fonts
# 1) 字体（Google Fonts: Noto Serif SC / Noto Sans SC / Cormorant Garamond / Orbitron / JetBrains Mono）
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Serif+SC 300 serif_light; get Noto+Serif+SC 500 serif_med; get Noto+Serif+SC 900 serif_black
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 500 sans_med; get Noto+Sans+SC 900 sans_black
get Cormorant+Garamond 500 corm; get Orbitron 700 orb; get JetBrains+Mono 400 mono
# 2) 背景音乐：两段 Lyria 原创配乐（music/），对齐到同一条 120 BPM 节拍网格，拼成 296 秒
python3 src/audio.py "$WORK"
# 3) 逐帧渲染（4 进程并行，共 8880 帧）
N=8880; K=4; S=$(( (N + K - 1) / K ))
for k in $(seq 0 $((K-1))); do python3 src/video.py chunk $((k*S)) $(( (k+1)*S < N ? (k+1)*S : N )) "$WORK/seg$k.mp4" & done; wait
for k in $(seq 0 $((K-1))); do echo "file '$WORK/seg$k.mp4'"; done > "$WORK/list.txt"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -i "$WORK/bgm.wav" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "$ROOT/投资的教训.mp4"
echo "done -> $ROOT/投资的教训.mp4"
