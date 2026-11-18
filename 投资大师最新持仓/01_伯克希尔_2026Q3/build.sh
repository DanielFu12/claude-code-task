#!/usr/bin/env bash
# 一键重建《投资大师最新持仓 EP.01 · 巴菲特 / 伯克希尔 2026Q3》竖屏短视频
# 依赖: ffmpeg, python3 (numpy opencv-python-headless pillow soundfile scipy)
# 品牌角标取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); WORK="$ROOT/work"; mkdir -p "$WORK" fonts
OUT="$ROOT/投资大师最新持仓_EP01_巴菲特伯克希尔_2026Q3.mp4"
# 0) 可选：从 SEC 复核全部数据（需要访问 www.sec.gov）
[ "${VERIFY:-0}" = 1 ] && python3 verify_data.py
# 1) 字体（Google Fonts）
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Serif+SC 500 serif_med; get Noto+Serif+SC 900 serif_black
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 500 sans_med; get Noto+Sans+SC 900 sans_black
get Cormorant+Garamond 500 corm; get Bebas+Neue 400 bebas; get JetBrains+Mono 500 mono; get Oswald 500 oswald
# 2) 音乐：取自仓库根目录 opus5.5涌现.mp4，按节拍剪辑 + 合成低频转场音效
ffmpeg -loglevel error -y -i "../../opus5.5涌现.mp4" -vn -ac 2 -ar 44100 "$WORK/src.wav"
python3 src/audio.py "$WORK"
# 3) 逐帧渲染（4 进程并行，98 s × 30 fps = 2940 帧）
for k in 0 1 2 3; do python3 src/video.py chunk $((k*735)) $(((k+1)*735)) "$WORK/seg$k.mp4" & done; wait
printf "file '%s'\n" "$WORK"/seg{0,1,2,3}.mp4 > "$WORK/list.txt"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -i "$WORK/mix.wav" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "$OUT"
echo "done -> $OUT"
