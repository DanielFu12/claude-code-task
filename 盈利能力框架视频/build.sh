#!/usr/bin/env bash
# 一键重建《企业盈利能力评估框架》10 分钟视频
# 依赖: ffmpeg, python3 (numpy scipy numba opencv-python-headless pillow soundfile librosa pyloudnorm)
# 旁白需要能访问 openspeech.bytedance.com（豆包 Seed-TTS 2.0，凭证由环境代理注入）；已合成的句子缓存在 work/tts/
# 品牌角标取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); WORK="$ROOT/work"; mkdir -p "$WORK" fonts
JOBS=${JOBS:-4}

# 1) 字体（Google Fonts）
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Serif+SC 500 serif_med; get Noto+Serif+SC 900 serif_black
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 500 sans_med; get Noto+Sans+SC 700 sans_bold; get Noto+Sans+SC 900 sans_black
get Cormorant+Garamond 600 corm; get Orbitron 700 orb; get JetBrains+Mono 500 mono; get Oswald 600 oswald

# 2) 旁白 -> 3) 节拍时间轴 -> 4) 原创配乐 -> 5) 混音母带
python3 src/tts.py
python3 src/timeline.py
python3 src/music.py
python3 src/mix.py

# 6) 逐帧渲染（并行，中间片用高码率快速编码）
N=$(python3 -c "import sys; sys.path.insert(0,'src'); from common import TOTAL, FPS; print(int(round(TOTAL*FPS)))")
Q=$(( (N + JOBS - 1) / JOBS ))
for ((k=0; k<JOBS; k++)); do python3 src/video.py chunk $((k*Q)) $(((k+1)*Q)) "$WORK/seg$k.mp4" & done; wait
: > "$WORK/list.txt"; for ((k=0; k<JOBS; k++)); do echo "file '$WORK/seg$k.mp4'" >> "$WORK/list.txt"; done
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -c copy "$WORK/inter.mp4"

# 7a) 高清母版（CRF 18，不入库）
ffmpeg -loglevel error -y -i "$WORK/inter.mp4" -i "$WORK/final_audio.wav" -map 0:v -map 1:a \
  -c:v libx264 -preset slow -tune animation -crf 18 -pix_fmt yuv420p -c:a aac -b:a 256k -movflags +faststart \
  "$WORK/企业盈利能力评估框架_高清.mp4"

# 7b) 仓库版：两遍编码控制在 95MB 以内（GitHub 单文件上限 100MB，仓库 LFS 额度已满）
ffmpeg -loglevel error -y -i "$WORK/inter.mp4" -map 0:v -c:v libx264 -preset slow -tune animation -b:v 1050k \
  -pass 1 -passlogfile "$WORK/repo2pass" -an -f null /dev/null
ffmpeg -loglevel error -y -i "$WORK/inter.mp4" -i "$WORK/final_audio.wav" -map 0:v -map 1:a \
  -c:v libx264 -preset slow -tune animation -b:v 1050k -maxrate 4000k -bufsize 8000k -pass 2 -passlogfile "$WORK/repo2pass" \
  -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart "$ROOT/企业盈利能力评估框架.mp4"
echo "done -> $ROOT/企业盈利能力评估框架.mp4 （高清母版：$WORK/企业盈利能力评估框架_高清.mp4）"
