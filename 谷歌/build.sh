#!/usr/bin/env bash
# 一键重建《二十年后的补票——巴菲特为什么出手谷歌》
# 依赖：ffmpeg、fluidsynth + fluid-soundfont-gm、Mesa EGL（libegl1 libgl1-mesa-dri）；
#       python3：numpy opencv-python-headless pillow soundfile librosa pyloudnorm moderngl fonttools pretty_midi
# 旁白录音已入库（assets/generated/tts_db），缺失才重新合成（豆包 TTS，需代理注入 API Key）。
set -euo pipefail
cd "$(dirname "$0")"
WORK=work; mkdir -p $WORK/tts_db
python3 src/get_fonts.py                   # 字体（google/fonts 仓库 → 静态字重）
for f in assets/generated/tts_db/*.mp3; do b=$(basename "$f" .mp3); [ -f "$WORK/tts_db/$b.wav" ] || { cp assets/generated/tts_db/$b.json $WORK/tts_db/; ffmpeg -loglevel error -y -i "$f" -ar 48000 -ac 1 "$WORK/tts_db/$b.wav"; }; done
python3 src/tts_doubao.py $WORK            # 只补缺失的段落
python3 src/voice_build.py $WORK && python3 src/timeline.py $WORK
python3 src/music.py $WORK && python3 src/audio_mix.py $WORK
python3 src/cut_cnbc.py && python3 src/cut_reuse.py     # 影像片段 → work_clips/
WORK=$WORK bash render.sh
python3 src/make_docs.py $WORK
