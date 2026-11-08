#!/usr/bin/env bash
# 一键重建《东京下注——巴菲特与日本五大商社》
# 依赖同第二期（ffmpeg、python3：numpy opencv-python-headless pillow soundfile librosa scipy pyloudnorm moderngl torchaudio；Mesa EGL）。
# 字体与配乐素材取自 ../巴菲特与苹果（fonts/、work/music3/）；旁白录音已入库（assets/generated/tts_db），缺失才重新合成（豆包 TTS，需代理注入 API Key）。
set -euo pipefail
cd "$(dirname "$0")"
WORK=work; mkdir -p $WORK/tts_db $WORK/music3
[ -e fonts ] || ln -s ../巴菲特与苹果/fonts fonts
for f in assets/generated/tts_db/*.mp3; do b=$(basename "$f" .mp3); [ -f "$WORK/tts_db/$b.wav" ] || { cp "$f" assets/generated/tts_db/$b.json $WORK/tts_db/; ffmpeg -loglevel error -y -i "$f" -ar 48000 -ac 1 "$WORK/tts_db/$b.wav"; }; done
cp -n ../巴菲特与苹果/work/music3/*.mp3 $WORK/music3/ 2>/dev/null || true
python3 data/calc.py                       # 行情与倍数 → data/calc.json
python3 src/tts_doubao.py $WORK            # 只补缺失的段落
python3 src/voice_build.py $WORK && python3 src/timeline.py $WORK
python3 src/score.py $WORK --beats && python3 src/audio_mix.py $WORK
python3 src/fetch_ia.py                    # Internet Archive 片段 → work_clips/
for c in x_bwb_desk x_bwb_meeting x_bwb_cherrycoke x_bwbi_a x_bwbi_b x_bwbi_c v_tokyo; do
  [ -e work_clips/$c.mp4 ] || ln -s ../../巴菲特与苹果/work_clips/$c.mp4 work_clips/$c.mp4; done
bash $WORK/render.sh 2>/dev/null || { cp ../巴菲特与苹果/work/render.sh $WORK/; bash $WORK/render.sh; }
python3 src/make_docs.py $WORK
