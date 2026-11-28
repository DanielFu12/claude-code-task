#!/usr/bin/env bash
# 一键重建《不情愿的顾客——巴菲特与穆迪》（第二季第一期）
# 依赖：ffmpeg、fluidsynth + musescore-general-soundfont（缺省时退回 fluid-soundfont-gm）、Mesa EGL（libegl1 libgl1-mesa-dri）；
#       python3：numpy opencv-python-headless pillow soundfile librosa pyloudnorm moderngl fonttools pretty_midi praat-parselmouth scipy pypdfium2
#       （逐句核对另需 sherpa-onnx 与 Paraformer 中文模型，见 src/check_vo.py）
# 旁白录音已入库（assets/generated：整篇一次合成的录音 FLAC + 逐句参考音频），缺失或改稿才重新合成（豆包 TTS，需代理注入 API Key）。
# 原声片源：FCIC 工作人员访谈巴菲特录音（2010-05-26，斯坦福法学院 FCIC 档案，下载到 work_clips/fcic_buffett_20100526.mp3，链接见 src/cut_sot.py）。
# 第一季回顾片段取自本系列成片预览版（../美国运通、../喜诗糖果、../巴菲特与可口可乐、../巴菲特与苹果，需 git lfs pull）。
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
python3 src/cut_sot.py $WORK               # 巴菲特原声 5 段（FCIC 访谈录音）
python3 src/timeline.py $WORK
python3 src/score.py $WORK && python3 src/audio_mix.py $WORK     # 配乐：score.py（第三版作曲引擎，MuseScore General 音色库：apt install musescore-general-soundfont）
python3 src/fetch_ia.py                    # archive.org 影像（1897–1903 年铁路影片、1941 年交易所影片、纽交所资料片）→ work_clips/；第一季回顾片段见 docs/SOURCES.md
python3 src/fetch_commons.py || true       # 维基共享资源照片（已入库的跳过；限流时稍后重跑）
WORK=$WORK bash render.sh
python3 src/make_docs.py $WORK
