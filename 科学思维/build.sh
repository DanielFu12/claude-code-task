#!/usr/bin/env bash
# 一键重建《科学思维》
# 依赖: ffmpeg, python3 (numpy scipy opencv-python-headless pillow soundfile pyloudnorm skia-python)
# 品牌角标、片尾 logo 与品牌字体/金色取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p fonts work
# 1) 字体（Google Fonts：思源宋体 / 思源黑体 / Inter / Cormorant Garamond / JetBrains Mono）
get(){ [ -s "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Serif+SC 300 serif_light; get Noto+Serif+SC 500 serif_med; get Noto+Serif+SC 700 serif_bold; get Noto+Serif+SC 900 serif_black
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 400 sans_reg; get Noto+Sans+SC 500 sans_med; get Noto+Sans+SC 700 sans_bold
get Inter 200 inter_thin; get Inter 300 inter_light; get Inter 500 inter_med; get Inter 700 inter_bold
get Cormorant+Garamond 500 corm; get Cormorant+Garamond 600 corm6; get JetBrains+Mono 400 mono
# 2) 原创卡点配乐（numpy 合成，100 BPM，与画面共用节拍网格）
python3 src/music.py work
# 3) 逐帧渲染（4 进程并行）
python3 src/video.py render
# 4) 成片：两遍编码，控制在 GitHub 单文件 100 MB 以内
for p in 1 2; do
  ffmpeg -v error -y -i work/video.mp4 -i work/score.wav -map 0:v -map 1:a -c:v libx264 -preset slow -b:v 2300k \
    -pass $p -passlogfile work/x264 -pix_fmt yuv420p -c:a aac -b:a 256k -shortest -movflags +faststart \
    $( [ $p = 1 ] && echo "-f mp4 /dev/null" || echo "科学思维.mp4" )
done
# 5) 预览版（720p，< 30 MB）
for p in 1 2; do
  ffmpeg -v error -y -i "科学思维.mp4" -vf scale=1280:720:flags=lanczos -c:v libx264 -preset slow -b:v 640k \
    -pass $p -passlogfile work/x264p -pix_fmt yuv420p -c:a aac -b:a 128k -cutoff 16000 -movflags +faststart \
    $( [ $p = 1 ] && echo "-f mp4 /dev/null" || echo "work/科学思维_预览版.mp4" )
done
echo "done -> 科学思维.mp4"
