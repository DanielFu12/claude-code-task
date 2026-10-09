#!/usr/bin/env bash
# 一键重建《你为什么总买在山顶？》
# 依赖: ffmpeg, python3 (numpy opencv-python-headless pillow soundfile librosa)
# 品牌角标与片尾 logo 取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); export WORK="$ROOT/work"; mkdir -p "$WORK" fonts
JOBS=${JOBS:-4}
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
# 1) 字体（Google Fonts：思源宋体 / 思源黑体 / Cormorant Garamond / JetBrains Mono）
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Serif+SC 300 serif_light; get Noto+Serif+SC 500 serif_med; get Noto+Serif+SC 700 serif_bold; get Noto+Serif+SC 900 serif_black
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 500 sans_med; get Noto+Sans+SC 700 sans_bold
get Cormorant+Garamond 500 corm; get Cormorant+Garamond 600 corm_sb; get JetBrains+Mono 300 mono; get JetBrains+Mono 500 mono_med
python3 -c "import sys; sys.path.insert(0,'../brand'); import brand; brand._font('serif_black',10); brand._font('corm',10)"
# 2) 背景音乐：取自 ../opus5.5涌现.mp4，按节拍无缝拼接到约 4 分 25 秒，并输出节拍分析
python3 src/audio.py "$WORK"
# 3) 逐帧渲染（JOBS 个进程并行）
N=$(python3 -c "import json,math;print(math.ceil(json.load(open('$WORK/music.json'))['duration']*30))")
STEP=$(( (N + JOBS - 1) / JOBS ))
for k in $(seq 0 $((JOBS-1))); do
  python3 src/film.py chunk $((k*STEP)) $(( (k+1)*STEP < N ? (k+1)*STEP : N )) "$WORK/seg$k.mp4" &
done; wait
for k in $(seq 0 $((JOBS-1))); do echo "file '$WORK/seg$k.mp4'"; done > "$WORK/list.txt"
OUT="$ROOT/你为什么总买在山顶.mp4"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -c copy "$WORK/master.mp4"
# 4) 成片：H.264 两遍编码，约 2.7 Mbps（总大小约 90 MB，低于 GitHub 单文件 100 MB 上限）
VB=${VB:-2550k}
ffmpeg -loglevel error -y -i "$WORK/master.mp4" -c:v libx264 -preset slow -tune animation -b:v $VB -pass 1 \
  -passlogfile "$WORK/x264" -pix_fmt yuv420p -an -f mp4 /dev/null
ffmpeg -loglevel error -y -i "$WORK/master.mp4" -i "$WORK/bgm.wav" -map 0:v -map 1:a -c:v libx264 -preset slow \
  -tune animation -b:v $VB -maxrate 6M -bufsize 8M -pass 2 -passlogfile "$WORK/x264" -pix_fmt yuv420p \
  -c:a aac -b:a 160k -shortest -movflags +faststart "$OUT"
# 5) 预览版：720p，约 25 MB
ffmpeg -loglevel error -y -i "$WORK/master.mp4" -i "$WORK/bgm.wav" -map 0:v -map 1:a -vf scale=1280:720:flags=lanczos \
  -c:v libx264 -preset slow -tune animation -b:v 760k -maxrate 2M -bufsize 3M -pix_fmt yuv420p \
  -c:a aac -b:a 96k -shortest -movflags +faststart "$WORK/preview_720p.mp4"
ls -la "$OUT" "$WORK/preview_720p.mp4"
echo "done -> $OUT"
