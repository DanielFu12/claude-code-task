#!/usr/bin/env bash
# 一键重建《一张支票，换一句话——巴菲特与内布拉斯加家具城》（第八期）
# 依赖：ffmpeg、fluidsynth + musescore-general-soundfont（缺省时退回 fluid-soundfont-gm）、Mesa EGL（libegl1 libgl1-mesa-dri）；
#       python3：numpy opencv-python-headless pillow soundfile librosa pyloudnorm moderngl fonttools pretty_midi praat-parselmouth scipy pypdfium2
#       （逐句核对另需 sherpa-onnx 与 Paraformer 中文模型，见 src/check_vo.py）
# 旁白录音已入库（assets/generated：整篇一次合成的录音 FLAC + 逐句参考音频），缺失或改稿才重新合成（豆包 TTS，需代理注入 API Key）。
# 原声片源：仓库外的 CNBC 专访原片（../谷歌/*CNBC专访*.mp4）与 1994 年股东会录像片段（work/src_dl/agm1994_480.mp4，来源见 assets/media/ia_clips.json）。
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
python3 src/cut_sot.py $WORK               # 巴菲特原声 3 段（CNBC 2026 专访 2 段、1994 股东会 1 段）+ 专访双人景 B-roll；片源见脚注
python3 src/timeline.py $WORK
python3 src/score.py $WORK && python3 src/audio_mix.py $WORK     # 配乐：score.py（第三版作曲引擎，MuseScore General 音色库：apt install musescore-general-soundfont）
python3 src/fetch_ia.py                    # archive.org 影像（NFM 2001/2005 年电视广告、2015 年 NFM 得州店、约 1960 年地毯宣传片、1958《American Look》、1921 年教育片、1999 年 Levitz 广告）→ work_clips/
python3 src/fetch_commons.py || true       # 维基共享资源照片（已入库的跳过；限流时稍后重跑）
SKIP_COMMONS=1 python3 src/fetch_media.py || true   # 美国国会图书馆照片与年报文件影像（已入库的跳过）
WORK=$WORK bash render.sh
python3 src/make_docs.py $WORK
