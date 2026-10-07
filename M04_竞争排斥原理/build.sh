#!/usr/bin/env bash
# 一键重建 M04《产品越来越像，竞争会走向哪里？》——竞争排斥原理（竖屏 1080×1920）
# 依赖: ffmpeg, python3 (numpy scipy opencv-python-headless pillow soundfile)
# 品牌角标与 logo 取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); WORK="$ROOT/work"; mkdir -p "$WORK" fonts
OUT="$ROOT/M04_产品越来越像竞争会走向哪里_竞争排斥原理_竖屏.mp4"
# 1) 字体（Google Fonts）
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Serif+SC 300 serif_light; get Noto+Serif+SC 500 serif_med; get Noto+Serif+SC 900 serif_black
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 500 sans_med; get Noto+Sans+SC 900 sans_black
get Cormorant+Garamond 500 corm; get Cormorant+Garamond 600 corm_semi; get Orbitron 700 orb; get JetBrains+Mono 400 mono
python3 src/timeline.py > "$WORK/captions_check.txt"       # 字幕阅读速度校验（≤6 字/秒）
# 2) 原创配乐 + 低频转场音效
(cd src && python3 music.py "$WORK")
# 3) 逐帧渲染（4 进程并行，共 5940 帧 = 198 s）
for k in 0 1 2 3; do (cd src && python3 video.py chunk $((k*1485)) $(((k+1)*1485)) "$WORK/seg$k.mp4") & done; wait
printf "file '%s'\n" "$WORK"/seg{0,1,2,3}.mp4 > "$WORK/list.txt"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -i "$WORK/mix.wav" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "$WORK/full.mp4"
# 4) 炫光层细节多，CRF 18 会超过 GitHub 100 MiB 单文件上限 → 两遍编码到 3.4 Mbps（约 92 MiB）
ffmpeg -loglevel error -y -i "$WORK/full.mp4" -map 0:v -c:v libx264 -preset slow -tune animation -b:v 3400k -pass 1 -passlogfile "$WORK/p2" -an -f null /dev/null
ffmpeg -loglevel error -y -i "$WORK/full.mp4" -map 0:v -map 0:a -c:v libx264 -preset slow -tune animation -b:v 3400k -pass 2 -passlogfile "$WORK/p2" \
  -pix_fmt yuv420p -c:a copy -movflags +faststart "$OUT"
echo "done -> $OUT"
