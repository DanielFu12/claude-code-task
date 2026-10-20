#!/usr/bin/env bash
# 一键重建第五版《AI时代，更要守住复利：李录、巴菲特、芒格谈复利》（1080×1920 · 30fps · 6 分 36 秒）
# 依赖：ffmpeg（含 rubberband）、yt-dlp、python3（numpy numba opencv-python-headless pillow soundfile librosa scipy pyloudnorm
#       faster-whisper）。解说只用 Gemini TTS gemini-3.8-flash-tts（Gemini API 的 key 由环境注入）。
# 品牌角标 / logo / 字体与颜色全部取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); WORK="$ROOT/work"; mkdir -p "$WORK" fonts
JOBS=${JOBS:-4}
export NUMBA_NUM_THREADS=${NUMBA_NUM_THREADS:-1} OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
OUT=${OUT:-"$ROOT/AI时代更要守住复利_李录巴菲特芒格谈复利.mp4"}
# 1) 字体（Google Fonts）
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Serif+SC 300 serif_light; get Noto+Serif+SC 500 serif_med; get Noto+Serif+SC 900 serif_black
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 500 sans_med; get Noto+Sans+SC 700 sans_bold
get Cormorant+Garamond 500 corm; get Cormorant+Garamond 600 corm_sb; get JetBrains+Mono 400 mono
# 2) 原始影像片段（源文件见 tools/fetch_footage.sh）
python3 src/prep_clips.py --stale       # 缺失或出入点 / 裁切改动过的片段才重做
# 3) 解说（Gemini TTS；已合成的段落有缓存。以退出码 2 停止时需要人工处理，见 src/tts3.py 开头说明）
python3 src/tts3.py "$WORK"
python3 src/t3.py
# 4) 混音
python3 src/audio3.py "$WORK/mix3.wav"
# 5) 逐帧渲染（并行，按帧数均分）
TOTAL=$(python3 -c "import sys; sys.path.insert(0,'src'); from t3 import DUR; print(int(round(DUR*30)))")
STEP=$(( (TOTAL + JOBS - 1) / JOBS ))
rm -f "$WORK"/v3seg*.mp4 "$WORK"/v3seg*.log
for k in $(seq 0 $((JOBS-1))); do
  a=$((k*STEP)); b=$(( (k+1)*STEP < TOTAL ? (k+1)*STEP : TOTAL ))
  python3 src/render3.py chunk $a $b "$WORK/v3seg$k.mp4" ${CRF:-16} > "$WORK/v3seg$k.log" 2>&1 &
done
wait
if grep -l Traceback "$WORK"/v3seg*.log; then echo "render failed (see logs above)"; exit 1; fi
for k in $(seq 0 $((JOBS-1))); do echo "file '$WORK/v3seg$k.mp4'"; done > "$WORK/v3list.txt"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/v3list.txt" -i "$WORK/mix3.wav" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart "$OUT"
# 6) 字幕
python3 src/srt3.py "$ROOT/字幕_中英.srt"
echo "done -> $OUT"
