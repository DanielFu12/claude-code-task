#!/usr/bin/env bash
# 一键重建《全押美国——巴菲特与 BNSF》
# 依赖：ffmpeg、fluidsynth + musescore-general-soundfont（缺省时退回 fluid-soundfont-gm）、Mesa EGL（libegl1 libgl1-mesa-dri）；
#       python3：numpy opencv-python-headless pillow soundfile librosa pyloudnorm moderngl fonttools pretty_midi praat-parselmouth scipy pypdfium2
#       （逐句核对另需 sherpa-onnx 与 Paraformer 中文模型，见 src/check_vo.py）
# 旁白录音已入库（assets/generated：整篇一次合成的录音 FLAC + 逐句参考音频），缺失或改稿才重新合成（豆包 TTS，需代理注入 API Key）。
# 原声片源：CNBC Squawk Box 2026-07-15 巴菲特专访（仓库内 ../谷歌/巴菲特谈Alphabet_CNBC专访_20260715_1080p.mp4）。
# 回顾片段取自本系列日本商社一期素材（见 docs/SOURCES.md）。
set -euo pipefail
cd "$(dirname "$0")"
WORK=work; mkdir -p $WORK/vo_take $WORK/vo_ref
python3 src/get_fonts.py                   # 字体（google/fonts 仓库 → 静态字重）
for d in vo_take vo_ref; do                # 入库的录音 → work（FLAC 无损，样本级一致）
  for f in assets/generated/$d/*.flac; do b=$(basename "$f" .flac)
    [ -f "$WORK/$d/$b.wav" ] || { ffmpeg -loglevel error -y -i "$f" -c:a pcm_s16le "$WORK/$d/$b.wav"; cp "assets/generated/$d/$b.json" "$WORK/$d/"; }
  done
done
python3 src/tts_take.py $WORK              # 只补缺失的：整篇录音（改了任何一句就整条重录）与逐句参考
python3 src/voice_build.py $WORK           # 拉平音高漂移 → 逐句子序列 DTW 切句 → 校验 → PSOLA 放慢（报告：work/vo/report.txt）
python3 src/pitch_level.py $WORK           # 逐章音高找平（章与章之间偏差 >1 半音的移到 0.4 半音内）
python3 src/cut_sot.py $WORK               # 巴菲特原声 1 段（CNBC 2026 专访，含出点尾段核查）
python3 src/timeline.py $WORK
python3 src/score_cues.py $WORK && python3 src/audio_mix.py $WORK   # 配乐：Kevin MacLeod 授权曲目（CC BY 4.0）按叙事剪辑卡点，曲源下载见 score_cues.py
python3 src/fetch_ia.py                    # archive.org 影像（1897–1903 年铁路影片、1941 年交易所影片、纽交所资料片）→ work_clips/；第一季回顾片段见 docs/SOURCES.md
python3 src/fetch_commons.py || true       # 维基共享资源照片（已入库的跳过；限流时稍后重跑）
WORK=$WORK bash render.sh
python3 src/make_docs.py $WORK
