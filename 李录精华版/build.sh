#!/usr/bin/env bash
# 一键重建《李录 · 哥大演讲精华》9:16 竖屏视频
# 依赖: ffmpeg, python3 (numpy opencv-python-headless pillow soundfile librosa)
# 品牌角标、logo、金色、品牌字体取自仓库根目录 brand/（见 brand/BRAND.md）
#
# 用法: ./build.sh <原片.mp4>
#   原片：https://www.youtube.com/watch?v=YRhnX_JAbC8（1440×1080，时长 1:28:17）
#   也可以从本仓库 Release「source-YRhnX_JAbC8」下载同一文件。
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); SRC=$(realpath "$1"); WORK="$ROOT/work"; mkdir -p "$WORK" fonts
export LILU_SRC="$SRC" LILU_WORK="$WORK"
# 1) 字体：品牌字体由 brand.py 自动下载；字幕字体从 Google Fonts 下载
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Sans+SC 400 sans_reg; get Noto+Sans+SC 500 sans_med; get Noto+Sans+SC 700 sans_bold
get Noto+Serif+SC 600 serif_semi; get Noto+Sans 400 latin_reg
# 2) 文稿对齐 → 剪辑点、双语字幕计时
cd src
python3 align.py youtube_asr.en.json3 script_en.txt "$WORK/align.json"
python3 build_cues.py "$WORK/align.json" cues.txt "$WORK/cues.json"
# 3) 逐镜头人脸跟随（YuNet 人脸检测模型）
[ -f "$WORK/yunet.onnx" ] || curl -sSfL -o "$WORK/yunet.onnx" \
  https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
python3 shots.py "$SRC" "$WORK/yunet.onnx" youtube_asr.en.json3
# 4) 音轨：原声拼接 + 配乐（仓库根目录 opus5.5涌现.mp4）
python3 audio.py "$SRC" "../../opus5.5涌现.mp4" "$WORK/mix_raw.wav"
# 5) 逐帧渲染（4 进程并行）
N=$(python3 render.py info | awk '/^frames/{print $2}'); K=4; S=$(( (N + K - 1) / K ))
for k in $(seq 0 $((K-1))); do LILU_CRF=${LILU_CRF:-20} python3 render.py chunk $((k*S)) $(((k+1)*S)) "$WORK/seg$k.mp4" & done; wait
printf "file '%s'\n" "$WORK"/seg{0,1,2,3}.mp4 > "$WORK/list.txt"
cd "$ROOT"
OUT="李录哥大演讲精华_9x16.mp4"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -i "$WORK/mix_raw.wav" -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-16:TP=-1.5:LRA=11" -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart "$OUT"
# 6) 30MB 以内预览版：720×1280，两遍编码，码率按时长自动计算
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")
VB=$(python3 -c "print(int((29.0*8*1024*1024/$DUR - 40000)/1000))")
ffmpeg -loglevel error -y -i "$OUT" -vf "scale=720:1280:flags=lanczos" -c:v libx264 -preset veryslow -tune film -b:v ${VB}k \
  -pass 1 -passlogfile "$WORK/p" -an -f mp4 /dev/null
ffmpeg -loglevel error -y -i "$OUT" -vf "scale=720:1280:flags=lanczos" -c:v libx264 -preset veryslow -tune film -b:v ${VB}k \
  -pass 2 -passlogfile "$WORK/p" -c:a aac -b:a 40k -ac 1 -movflags +faststart "李录哥大演讲精华_预览版.mp4"
echo "done -> $ROOT/$OUT"
