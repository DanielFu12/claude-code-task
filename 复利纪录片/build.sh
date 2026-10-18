#!/usr/bin/env bash
# 一键重建《AI 越快，越要慢》竖屏纪录片（1080×1920 · 30fps）
# 依赖：ffmpeg、python3（numpy numba opencv-python-headless pillow soundfile librosa scipy pyloudnorm fonttools）
# 品牌角标 / logo / 品牌字体与颜色全部取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); WORK="$ROOT/work"; mkdir -p "$WORK" fonts
JOBS=${JOBS:-4}
export NUMBA_NUM_THREADS=${NUMBA_NUM_THREADS:-1} OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
OUT=${OUT:-"$ROOT/AI越快越要慢_李录巴菲特芒格谈复利.mp4"}
# 1) 字体（Google Fonts）
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Serif+SC 300 serif_light; get Noto+Serif+SC 500 serif_med; get Noto+Serif+SC 900 serif_black
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 500 sans_med; get Noto+Sans+SC 700 sans_bold
get Cormorant+Garamond 500 corm; get Cormorant+Garamond 600 corm_sb; get JetBrains+Mono 400 mono
# 2) 旁白（已生成的 assets/voice/*.wav 会直接使用；如需重新生成：python3 src/tts.py Orus）
python3 src/timeline.py
# 3) 混音
python3 src/audio.py "$WORK/mix.wav"
# 4) 逐帧渲染（并行）
TOTAL=$(python3 -c "import sys; sys.path.insert(0,'src'); from timeline import DUR; print(int(round(DUR*30)))")
STEP=$(( (TOTAL + JOBS - 1) / JOBS ))
rm -f "$WORK"/seg*.mp4
for k in $(seq 0 $((JOBS-1))); do
  a=$((k*STEP)); b=$(( (k+1)*STEP < TOTAL ? (k+1)*STEP : TOTAL ))
  python3 src/render.py chunk $a $b "$WORK/seg$k.mp4" ${CRF:-14} > "$WORK/seg$k.log" 2>&1 &
done
wait
for k in $(seq 0 $((JOBS-1))); do echo "file '$WORK/seg$k.mp4'"; done > "$WORK/list.txt"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -i "$WORK/mix.wav" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart "$OUT"
echo "done -> $OUT"
