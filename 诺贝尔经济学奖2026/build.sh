#!/usr/bin/env bash
# 一键重建《2026 诺贝尔经济学奖：为什么你的预期，决定了经济的未来？》（1080×1920 竖屏）
# 依赖：ffmpeg、python3（numpy scipy numba opencv-python-headless pillow soundfile pyloudnorm）
# 品牌角标与片尾 logo 取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); mkdir -p fonts build
OUT="$ROOT/2026诺贝尔经济学奖_为什么你的预期决定了经济的未来.mp4"
PREVIEW="$ROOT/2026诺贝尔经济学奖_预览版.mp4"
# 1) 字体（Google Fonts：思源宋体 / 思源黑体 / Inter / Cormorant Garamond）
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Serif+SC 900 serif_black; get Noto+Serif+SC 700 serif_bold; get Noto+Serif+SC 500 serif_med; get Noto+Serif+SC 300 serif_light
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 400 sans_reg; get Noto+Sans+SC 500 sans_med; get Noto+Sans+SC 700 sans_bold; get Noto+Sans+SC 900 sans_black
get Inter 300 inter_light; get Inter 500 inter_med; get Inter 700 inter_bold; get Inter 800 inter_xbold
get Cormorant+Garamond 600 corm; get Cormorant+Garamond 700 corm_bold
# 2) 原创配乐（numpy 合成）→ build/music.wav + 逐帧节拍数据
python3 src/music.py build
# 3) 逐帧渲染（4 进程并行，12 段）
CRF=12 PRESET=medium python3 src/video.py render 4
ffmpeg -v error -y -f concat -safe 0 -i build/chunks.txt -c copy build/master_video.mp4
# 4) 成片：两遍编码控制在 GitHub 单文件 100 MB 以内；音频 AAC 192k
VBR=3700k
ffmpeg -v error -y -i build/master_video.mp4 -c:v libx264 -preset slow -b:v $VBR -pass 1 -passlogfile build/x264 \
  -x264-params aq-mode=3 -pix_fmt yuv420p -an -f mp4 /dev/null
ffmpeg -v error -y -i build/master_video.mp4 -i build/music.wav -map 0:v -map 1:a -c:v libx264 -preset slow -b:v $VBR \
  -pass 2 -passlogfile build/x264 -x264-params aq-mode=3 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest \
  -movflags +faststart "$OUT"
# 5) 预览版（< 30 MB）：720×1280，两遍编码
PV=1080k
ffmpeg -v error -y -i build/master_video.mp4 -vf scale=720:1280:flags=lanczos -c:v libx264 -preset slow -b:v $PV -pass 1 \
  -passlogfile build/x264p -pix_fmt yuv420p -an -f mp4 /dev/null
ffmpeg -v error -y -i build/master_video.mp4 -i build/music.wav -map 0:v -map 1:a -vf scale=720:1280:flags=lanczos \
  -c:v libx264 -preset slow -b:v $PV -pass 2 -passlogfile build/x264p -pix_fmt yuv420p -c:a aac -b:a 128k -shortest \
  -movflags +faststart "$PREVIEW"
ls -la "$OUT" "$PREVIEW"
