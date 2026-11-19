#!/usr/bin/env bash
# 一键重建《伪价值投资》竖屏短视频（1080×1920 · 30fps）
# 依赖: ffmpeg, python3 (numpy scipy opencv-python-headless pillow soundfile librosa)
# 旁白: 火山引擎 Seed-TTS 2.0（work/vo 已存在时跳过合成）；品牌角标取自仓库根目录 brand/
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); WORK="$ROOT/work"; mkdir -p "$WORK"
./fetch_fonts.sh
[ -f "$WORK/vo/L29.wav" ] || RATE=12 python3 src/tts_all.py "$WORK/vo"
python3 src/timeline.py "$WORK"
python3 src/music.py "$WORK"
NF=$(python3 -c "import json;print(int(json.load(open('$WORK/timeline.json'))['total']*30))")
pids=(); for k in 0 1 2 3; do WORK="$WORK" python3 src/video.py chunk $((k*NF/4)) $(((k+1)*NF/4)) "$WORK/seg$k.mp4" & pids+=($!); done
for p in "${pids[@]}"; do wait "$p"; done   # 任一分段失败即中止
printf "file '%s'\n" "$WORK"/seg{0,1,2,3}.mp4 > "$WORK/list.txt"
# 混音：旁白轻压缩 + 配乐，整体响度 -14 LUFS
ffmpeg -loglevel error -y -i "$WORK/voice.wav" -i "$WORK/music.wav" -filter_complex \
 "[0:a]highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=2,aformat=channel_layouts=stereo[v];\
  [1:a]volume=0.95[m];[v][m]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]" \
 -map "[a]" -ar 48000 "$WORK/mix.wav"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -i "$WORK/mix.wav" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$ROOT/伪价值投资.mp4"
echo "done -> $ROOT/伪价值投资.mp4"
