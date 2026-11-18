#!/usr/bin/env bash
# 一键重建《投资大师最新持仓 · 巴菲特 / 伯克希尔 2026Q3》竖屏短视频
# 依赖: ffmpeg, python3 (numpy opencv-python-headless pillow soundfile scipy；可选 pyloudnorm 做响度对齐)
# 品牌角标取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); WORK="$ROOT/work"; mkdir -p "$WORK" fonts
OUT="$ROOT/投资大师最新持仓_巴菲特伯克希尔_2026Q3.mp4"
# 0) 可选：对照参考网页 masterstao.com 与 SEC 原文复核全部数据
[ "${VERIFY:-0}" = 1 ] && python3 verify_data.py
# 1) 字体（Google Fonts）
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Serif+SC 500 serif_med; get Noto+Serif+SC 900 serif_black
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 500 sans_med; get Noto+Sans+SC 900 sans_black
get Cormorant+Garamond 500 corm; get Bebas+Neue 400 bebas; get JetBrains+Mono 500 mono; get Oswald 500 oswald
# 2) 原创卡点配乐：120 BPM，按 timeline.py 的拍号逐音符合成；同时导出鼓点时间 events.json 供画面卡点
python3 src/music.py "$WORK"
# 3) 逐帧渲染（4 进程并行，118 s × 30 fps = 3540 帧）
for k in 0 1 2 3; do python3 src/video.py chunk $((k*885)) $(((k+1)*885)) "$WORK/seg$k.mp4" & done; wait
printf "file '%s'\n" "$WORK"/seg{0,1,2,3}.mp4 > "$WORK/list.txt"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -i "$WORK/mix.wav" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "$OUT"
echo "done -> $OUT"
