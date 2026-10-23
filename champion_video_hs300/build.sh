#!/usr/bin/env bash
# 一键重建《追涨十年 · 沪深300版》（1080×1920 · 30fps · 206.6s）
# 与原版共用：配乐（../champion_video/music）、回测脚本与数据（../champion_video/backtest）、字体（../champion_video/fonts）
# 依赖: ffmpeg, python3 (numpy opencv-python-headless pillow[raqm] scipy soundfile librosa pandas requests)
#
#   ./build.sh            # 用已提交的 out_us.json / out_cn300.json / evidence300.json 直接渲染
#   ./build.sh backtest   # 先重跑沪深300口径回测与归因证据（需要原版的回测缓存 backtest/cache 与网络）
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); WORK="$ROOT/work"; BT="$ROOT/../champion_video/backtest"; FONTS="$ROOT/../champion_video/fonts"
NAME="追涨十年_沪深300版"
mkdir -p "$WORK" "$FONTS"

# 0) 可选：重跑沪深 300 口径回测、利润数据与归因证据
if [ "${1:-}" = "backtest" ]; then
  (cd "$BT" && python3 cn300.py && python3 fetch_profits.py && python3 evidence300.py && python3 export_tables300.py)
fi

# 1) 字体（Google Fonts，与原版相同）
get(){ [ -f "$FONTS/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "$FONTS/$3.ttf" "$url"; }
get Noto+Serif+SC 500 serif_med; get Noto+Serif+SC 700 serif_bold; get Noto+Serif+SC 900 serif_black
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 400 sans_reg; get Noto+Sans+SC 500 sans_med
get Noto+Sans+SC 700 sans_bold; get Noto+Sans+SC 900 sans_black
get Inter 400 inter_reg; get Inter 600 inter_semi; get Inter 800 inter_xbold; get Inter+Tight 900 intert_black
get Cormorant+Garamond 600 corm; get JetBrains+Mono 500 mono

# 2) 画面数据 + 配乐（事件对齐 src/timeline.py）
(cd src && python3 story.py)
(cd src && python3 audio.py ../../champion_video/music/score_lyria.mp3 "$WORK/mix.wav")

# 3) 逐帧渲染（4 进程并行）
N=$(python3 -c "import sys; sys.path.insert(0,'src'); from timeline import T_TOTAL; print(int(round(T_TOTAL*30)))")
P=4; S=$(( (N + P - 1) / P ))
for k in $(seq 0 $((P-1))); do
  a=$((k*S)); b=$(( (k+1)*S < N ? (k+1)*S : N ))
  (cd src && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python3 video.py chunk $a $b "$WORK/seg$k.mp4") &
done
wait
: > "$WORK/list.txt"; for k in $(seq 0 $((P-1))); do echo "file '$WORK/seg$k.mp4'" >> "$WORK/list.txt"; done

# 4) 正式成片（x264 slow / CRF 16 / High@4.2，AAC 256k）
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -i "$WORK/mix.wav" \
  -map 0:v -map 1:a -c:v libx264 -preset slow -crf 16 -profile:v high -level 4.2 -pix_fmt yuv420p \
  -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart "$ROOT/$NAME.mp4"

# 5) 预览版（< 30 MB：两遍 x264 码率控制，目标约 27.5 MB）
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$ROOT/$NAME.mp4")
VB=$(python3 -c "print(int(27.5e6*8/$DUR - 128000))")
ffmpeg -loglevel error -y -i "$ROOT/$NAME.mp4" -c:v libx264 -preset slow -b:v $VB -pass 1 -an -f mp4 -passlogfile "$WORK/x264" /dev/null
ffmpeg -loglevel error -y -i "$ROOT/$NAME.mp4" -c:v libx264 -preset slow -b:v $VB -pass 2 -passlogfile "$WORK/x264" \
  -c:a aac -b:a 128k -movflags +faststart "$ROOT/${NAME}_预览版.mp4"
ls -lh "$ROOT/$NAME.mp4" "$ROOT/${NAME}_预览版.mp4"
