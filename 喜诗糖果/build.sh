#!/usr/bin/env bash
# 一键重建《一盒糖的学费——芒格怎样改变了巴菲特》
# 依赖：ffmpeg、fluidsynth + fluid-soundfont-gm、Mesa EGL（libegl1 libgl1-mesa-dri）；
#       python3：numpy opencv-python-headless pillow soundfile librosa pyloudnorm moderngl fonttools pretty_midi
# 旁白录音已入库（assets/generated/tts_db），缺失才重新合成（豆包 TTS，需代理注入 API Key）。
set -euo pipefail
cd "$(dirname "$0")"
WORK=work; mkdir -p $WORK/tts_db
python3 src/get_fonts.py                   # 字体（google/fonts 仓库 → 静态字重）
for f in assets/generated/tts_db/*.mp3; do b=$(basename "$f" .mp3); [ -f "$WORK/tts_db/$b.wav" ] || { cp assets/generated/tts_db/$b.json $WORK/tts_db/; ffmpeg -loglevel error -y -i "$f" -ar 48000 -ac 1 "$WORK/tts_db/$b.wav"; }; done
python3 src/tts_doubao.py $WORK            # 只补缺失的段落
python3 src/fetch_ia.py                    # archive.org 实拍（喜诗工厂/门店/1981 新闻/1988 广告/The Kid/HBO 芒格访谈）→ work_clips/、work/src_dl/
python3 src/cut_sot.py $WORK               # 大师原声片段（芒格 HBO 访谈、巴菲特 CNBC 专访，带音轨）→ work_clips/sot_*.mp4、$WORK/sot/
python3 src/voice_build.py $WORK && python3 src/timeline.py $WORK
python3 src/music.py $WORK && python3 src/audio_mix.py $WORK
python3 src/cut_cnbc.py                     # CNBC 专访画面 → work_clips/（原片在 ../谷歌/）
python3 src/fetch_media.py || true         # Commons 照片（已入库的跳过；网络受限时 gg.py 自动改用自绘插画）
WORK=$WORK bash render.sh
python3 src/make_docs.py $WORK
