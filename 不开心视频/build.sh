#!/usr/bin/env bash
# 一键重建《人为什么会感到不开心》视频
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
# 2) 背景音乐：取自参考视频，按节拍无缝拼接到 180 秒
ffmpeg -loglevel error -y -i "../opus5.5涌现.mp4" -vn -ac 2 -ar 44100 "$WORK/bgm.wav"
python3 - "$WORK" <<'PY'
import sys, numpy as np, librosa
y, sr = librosa.load(sys.argv[1] + '/bgm.wav', sr=22050)
_, b = librosa.beat.beat_track(y=y, sr=sr, hop_length=512)
np.save(sys.argv[1] + '/beats.npy', librosa.frames_to_time(b, sr=sr, hop_length=512))
PY
python3 src/audio.py "$WORK"
# 3) 逐帧渲染（4 进程并行）
for k in 0 1 2 3; do python3 src/video.py chunk $((k*1350)) $(((k+1)*1350)) "$WORK/seg$k.mp4" & done; wait
printf "file '%s'\n" "$WORK"/seg{0,1,2,3}.mp4 > "$WORK/list.txt"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -i "$WORK/bgm180.wav" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$ROOT/人为什么会感到不开心.mp4"
echo "done -> $ROOT/人为什么会感到不开心.mp4"
