#!/usr/bin/env bash
# 一键生成《沃伦·巴菲特：股神的复利人生》
# 依赖：ffmpeg、python3（numpy opencv-python-headless pillow soundfile librosa global-land-mask）
# 画面素材 assets/*.jpg 和配乐 assets/music/*.mp3 已入库；要重新生成素材，运行 python3 src/assets.py（需要 Gemini 额度）
# 品牌角标取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p work fonts
# 1) 字体（Google Fonts）
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Sans+SC 900 sans_black; get Noto+Sans+SC 700 sans_bold; get Noto+Sans+SC 400 sans_reg
get Noto+Serif+SC 900 serif_black; get Noto+Serif+SC 600 serif_semi; get Cormorant+Garamond 600 corm; get Oswald 700 oswald
# 2) 配乐拼接 + 镜头对齐节拍
python3 src/music.py
# 3) 脚本文档与分镜数据保持一致
python3 src/shots.py > 脚本.md
# 4) 逐帧渲染（4 进程并行）
N=$(python3 -c "import json;print(int(json.load(open('work/timeline.json'))['total']*30))")
for k in 0 1 2 3; do python3 src/render.py chunk $((N*k/4)) $((N*(k+1)/4)) work/seg$k.mp4 & done; wait
printf "file '%s'\n" "$PWD"/work/seg{0,1,2,3}.mp4 > work/list.txt
ffmpeg -loglevel error -y -f concat -safe 0 -i work/list.txt -i work/bgm.wav \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "沃伦·巴菲特：股神的复利人生.mp4"
echo "done -> 沃伦·巴菲特：股神的复利人生.mp4"
