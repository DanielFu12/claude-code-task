#!/usr/bin/env bash
# 一键重建《一张支票，换一句话——巴菲特与内布拉斯加家具城》（第八期）
# 依赖：ffmpeg、fluidsynth + fluid-soundfont-gm、Mesa EGL（libegl1 libgl1-mesa-dri）；
#       python3：numpy opencv-python-headless pillow soundfile librosa pyloudnorm moderngl fonttools pretty_midi praat-parselmouth scipy pypdfium2
#       （逐句核对另需 sherpa-onnx 与 Paraformer 中文模型，见 src/check_vo.py）
# 旁白录音已入库（assets/generated：整篇一次合成的录音 FLAC + 逐句参考音频），缺失或改稿才重新合成（豆包 TTS，需代理注入 API Key）。
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
python3 src/timeline.py $WORK
python3 src/music.py $WORK && python3 src/audio_mix.py $WORK
python3 src/fetch_ia.py                    # archive.org 影像（2015 年 NFM 得州店、约 1960 年地毯宣传片、1958《American Look》、1921 年教育片、1999 年 Levitz 广告）→ work_clips/
SKIP_COMMONS=1 python3 src/fetch_media.py || true   # 美国国会图书馆照片与年报文件影像（已入库的跳过）
WORK=$WORK bash render.sh
python3 src/make_docs.py $WORK
