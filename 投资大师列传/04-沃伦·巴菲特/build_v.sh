#!/usr/bin/env bash
# 一键生成竖屏版《沃伦·巴菲特：股神的复利人生》（1080×1920）
# 依赖同 build.sh；横屏版仍用 build.sh
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p work fonts
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Sans+SC 900 sans_black; get Noto+Sans+SC 700 sans_bold; get Noto+Sans+SC 400 sans_reg
get Noto+Serif+SC 900 serif_black; get Noto+Serif+SC 600 serif_semi; get Cormorant+Garamond 600 corm; get Oswald 700 oswald
# 1) 配乐编排（章节对齐小节、合成音效、滤波递进）+ 时间线
python3 src/music_v.py
# 2) 逐帧渲染（4 进程并行）
N=$(python3 -c "import json;print(int(json.load(open('work/timeline_v.json'))['total']*30))")
for k in 0 1 2 3; do python3 src/render_v.py chunk $((N*k/4)) $((N*(k+1)/4)) work/v$k.mp4 & done; wait
printf "file '%s'\n" "$PWD"/work/v{0,1,2,3}.mp4 > work/vlist.txt
ffmpeg -loglevel error -y -f concat -safe 0 -i work/vlist.txt -i work/bgm_v.wav \
  -map 0:v -map 1:a -c:v libx264 -preset medium -crf 24 -tune grain -pix_fmt yuv420p \
  -c:a aac -b:a 192k -shortest -movflags +faststart "沃伦·巴菲特：股神的复利人生（竖屏）.mp4"
echo "done -> 沃伦·巴菲特：股神的复利人生（竖屏）.mp4"
