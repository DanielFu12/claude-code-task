#!/usr/bin/env bash
# 一键重建《好公司，为什么还会亏？》竖屏短视频（1080×1920 · 30fps）
# 依赖: ffmpeg, fluidsynth, python3 (numpy scipy opencv-python-headless pillow soundfile librosa mido praat-parselmouth pyloudnorm)
# 旁白: 火山引擎 Seed-TTS 2.0（work/vo 已存在时跳过合成）；品牌角标取自仓库根目录 brand/
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); WORK="$ROOT/work"; mkdir -p "$WORK"
./fetch_fonts.sh
python3 src/gen_script.py
[ -f "$WORK/vo_ref/L95.wav" ] || python3 src/tts_all.py "$WORK/vo_ref"   # 逐句参考：只用于强制对齐切句与校验
[ -f "$WORK/vo/gaps.json" ] || python3 src/tts_take.py "$WORK"           # 整篇一次合成（一条录完）→ 拉平长文本音高漂移 → 逐句对齐切句 → 第三章放慢
python3 src/timeline.py "$WORK"
python3 src/music.py "$WORK"
NF=$(python3 -c "import json;print(int(json.load(open('$WORK/timeline.json'))['total']*30))")
pids=(); for k in 0 1 2 3; do WORK="$WORK" python3 src/video.py chunk $((k*NF/4)) $(((k+1)*NF/4)) "$WORK/seg$k.mp4" & pids+=($!); done
for p in "${pids[@]}"; do wait "$p"; done   # 任一分段失败即中止
printf "file '%s'\n" "$WORK"/seg{0,1,2,3}.mp4 > "$WORK/list.txt"
# 混音：旁白粘合 + 配乐闪避（人声时 -12 dB，人声频段再 -5 dB）+ 线性响度 -14 LUFS
python3 src/mix.py "$WORK"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -i "$WORK/mix.wav" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$ROOT/好公司为什么还会亏.mp4"
echo "done -> $ROOT/好公司为什么还会亏.mp4"
