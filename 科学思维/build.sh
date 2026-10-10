#!/usr/bin/env bash
# 一键重建《科学思维》
# 依赖: ffmpeg, python3 (numpy scipy opencv-python-headless pillow soundfile pyloudnorm librosa skia-python sherpa-onnx)
# 品牌角标、片尾 logo 与品牌字体/金色取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p fonts work models
# 1) 字体（Google Fonts：思源宋体 / 思源黑体 / Inter / Cormorant Garamond / JetBrains Mono）
get(){ [ -s "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Serif+SC 300 serif_light; get Noto+Serif+SC 500 serif_med; get Noto+Serif+SC 700 serif_bold; get Noto+Serif+SC 900 serif_black
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 400 sans_reg; get Noto+Sans+SC 500 sans_med; get Noto+Sans+SC 700 sans_bold
get Inter 200 inter_thin; get Inter 300 inter_light; get Inter 500 inter_med; get Inter 700 inter_bold
get Cormorant+Garamond 500 corm; get Cormorant+Garamond 600 corm6; get JetBrains+Mono 400 mono
# 2) 离线语音模型（sherpa-onnx 发布页）：Kokoro v1.1-zh 配音，SenseVoice 回听校对
rel=https://github.com/k2-fsa/sherpa-onnx/releases/download
[ -d models/kokoro-multi-lang-v1_1 ] || curl -sSfL "$rel/tts-models/kokoro-multi-lang-v1_1.tar.bz2" | tar xj -C models
[ -d models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09 ] || \
  curl -sSfL "$rel/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09.tar.bz2" | tar xj -C models
# 3) 旁白（男声 68 号，语速 1.08）→ 原创配乐与混音（−14 LUFS）
python3 src/tts.py work 68 1.08
python3 src/music.py work
# 4) 逐帧渲染（4 进程并行）
python3 src/video.py render
# 5) 成片：两遍编码，控制在 GitHub 单文件 100 MB 以内
for p in 1 2; do
  ffmpeg -v error -y -i work/video.mp4 -i work/score.wav -map 0:v -map 1:a -c:v libx264 -preset slow -b:v 2300k \
    -pass $p -passlogfile work/x264 -pix_fmt yuv420p -c:a aac -b:a 160k -shortest -movflags +faststart \
    $( [ $p = 1 ] && echo "-f mp4 /dev/null" || echo "科学思维.mp4" )
done
# 6) 预览版（720p，< 30 MB）
for p in 1 2; do
  ffmpeg -v error -y -i "科学思维.mp4" -vf scale=1280:720:flags=lanczos -c:v libx264 -preset slow -b:v 640k \
    -pass $p -passlogfile work/x264p -pix_fmt yuv420p -c:a aac -b:a 96k -movflags +faststart \
    $( [ $p = 1 ] && echo "-f mp4 /dev/null" || echo "work/科学思维_预览版.mp4" )
done
echo "done -> 科学思维.mp4"
