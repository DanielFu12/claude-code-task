#!/usr/bin/env bash
# 一键重建《贝叶斯思维》
# 依赖: ffmpeg, python3 (numpy scipy opencv-python-headless pillow soundfile pyloudnorm matplotlib)
# 品牌角标与片尾 logo 取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p fonts work
# 1) 字体（Google Fonts：思源宋体 / 思源黑体 / Inter / Cormorant Garamond / JetBrains Mono）
get(){ [ -s "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Serif+SC 300 serif_light; get Noto+Serif+SC 500 serif_med; get Noto+Serif+SC 700 serif_bold; get Noto+Serif+SC 900 serif_black
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 400 sans_reg; get Noto+Sans+SC 700 sans_bold
get Cormorant+Garamond 500 corm; get Cormorant+Garamond 600 corm6
get Inter 200 inter_thin; get Inter 300 inter_light; get Inter 600 inter_semi; get JetBrains+Mono 400 mono
# 2) 原创配乐（numpy 合成，96 BPM）
python3 src/music.py work
# 3) 逐帧渲染（4 进程并行）并合成音轨
python3 src/video.py render
#    成片两遍编码到约 2.2 Mbps，保证 < 100 MB（GitHub 单文件上限）
for p in 1 2; do
  ffmpeg -v error -y -i work/video.mp4 -i work/score.wav -map 0:v -map 1:a -c:v libx264 -preset slow -b:v 2200k \
    -pass $p -passlogfile work/x264 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart \
    $( [ $p = 1 ] && echo "-f mp4 /dev/null" || echo "贝叶斯思维.mp4" )
done
# 4) 预览版（< 30 MB）
ffmpeg -v error -y -i "贝叶斯思维.mp4" -vf scale=1280:720:flags=lanczos -c:v libx264 -preset slow -b:v 700k \
  -maxrate 1000k -bufsize 2000k -c:a aac -b:a 128k -movflags +faststart "work/贝叶斯思维_预览版.mp4"
echo "done -> 贝叶斯思维.mp4"
