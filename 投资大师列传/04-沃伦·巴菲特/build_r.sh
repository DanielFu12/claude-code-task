#!/usr/bin/env bash
# 一键生成竖屏版（使用参照片配乐，用户已获授权）：1080×1920
# 依赖同 build.sh；配乐原曲 assets/music/ref_bgm.m4a
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p work fonts
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Sans+SC 900 sans_black; get Noto+Sans+SC 700 sans_bold; get Noto+Sans+SC 400 sans_reg
get Noto+Serif+SC 900 serif_black; get Noto+Serif+SC 600 serif_semi; get Cormorant+Garamond 600 corm; get Oswald 700 oswald
python3 src/music_r.py
export TL=r
N=$(python3 -c "import json;print(int(json.load(open('work/timeline_r.json'))['total']*30))")
for k in 0 1 2 3; do python3 src/render_v.py chunk $((N*k/4)) $((N*(k+1)/4)) work/r$k.mp4 & done; wait
printf "file '%s'\n" "$PWD"/work/r{0,1,2,3}.mp4 > work/rlist.txt
ffmpeg -loglevel error -y -f concat -safe 0 -i work/rlist.txt -i work/bgm_r.wav \
  -map 0:v -map 1:a -c:v libx264 -preset medium -crf 24 -tune grain -pix_fmt yuv420p \
  -c:a aac -b:a 192k -shortest -movflags +faststart "沃伦·巴菲特：股神的复利人生（竖屏）.mp4"
echo "done -> 沃伦·巴菲特：股神的复利人生（竖屏）.mp4"
