#!/usr/bin/env bash
# 一键重建《内在价值：没有把握，就不知道它值多少》（巴芒精华库 Top 1）竖屏视频
# 依赖：ffmpeg、python3（numpy opencv-python-headless pillow soundfile librosa scipy sherpa-onnx faster-whisper）
# 网络：archive.org（原始录音）、GitHub release（TTS 模型）、Hugging Face（faster-whisper 模型）、Google Fonts
# 品牌：右上角角标和片尾 logo / 文字全部取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); WORK="$ROOT/work"; mkdir -p "$WORK" fonts
OUT="$ROOT/内在价值_巴芒Top1_1080x1920.mp4"
PREVIEW="$ROOT/内在价值_巴芒Top1_预览版.mp4"

# 1) 字体：品牌字体由 brand.py 下载到 brand/fonts/；字幕和图表字体来自 Google Fonts
python3 -c "import sys; sys.path.insert(0, '../brand'); import brand; brand._font('serif_black', 10); brand._font('corm', 10)"
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 500 sans_med; get Noto+Sans+SC 700 sans_bold
get Noto+Serif+SC 700 serif_bold; get Noto+Sans 400 en_reg; get Noto+Sans 500 en_med; get Cormorant+Garamond 600 corm

# 2) 原始录音：从 archive.org 的 1994 年全场录像里按区间取 280 秒音频（下午场只有音频）
python3 src/fetch.py "$WORK"
# 3) 字幕对齐：faster-whisper 逐词时间戳 × CNBC 逐字稿
python3 src/align.py "$WORK"

# 4) 投资启示解说：离线 TTS（sherpa-onnx + Kokoro v1.1-zh，约 330MB，来自 GitHub release）
MODEL="${KOKORO_DIR:-$WORK/kokoro-multi-lang-v1_1}"
if [ ! -f "$MODEL/model.onnx" ]; then
  curl -sSL https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_1.tar.bz2 | tar xj -C "$WORK"
fi
python3 src/tts.py "$WORK" "$MODEL"

# 5) 混音：片头音乐 → 原声 → 音乐重拍进入投资启示 → 片尾重拍对准「巴芒价值」
ffmpeg -loglevel error -y -i "../opus5.5涌现.mp4" -vn -ac 2 -ar 44100 "$WORK/bgm.wav"
python3 src/audio.py "$WORK" "$WORK/bgm.wav"

# 6) 逐帧渲染（4 进程并行）
N=$(cd src && python3 render.py nframes "$WORK")
Q=$(( (N + 3) / 4 ))
for k in 0 1 2 3; do (cd src && python3 render.py chunk $((k*Q)) $(((k+1)*Q)) "$WORK/seg$k.mp4" "$WORK") & done; wait
printf "file '%s'\n" "$WORK"/seg{0,1,2,3}.mp4 > "$WORK/list.txt"

# 7) 合成：画面 + 混音（响度归一到 -16 LUFS）
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -i "$WORK/mix.wav" \
  -map 0:v -map 1:a -c:v copy -af "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000" -c:a aac -b:a 192k \
  -shortest -movflags +faststart "$OUT"

# 8) 双语字幕文件（SRT）
python3 src/srt.py "$WORK" "$ROOT/字幕_中英.srt"

# 9) 30MB 以内的预览版：同分辨率，两遍编码按码率控制体积，音频直接复制
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")
VB=$(python3 -c "print(int(26*8*1024*1024/$DUR/1000) - 192)")
ffmpeg -loglevel error -y -i "$OUT" -c:v libx264 -preset slow -b:v ${VB}k -pass 1 -passlogfile "$WORK/p" -an -f mp4 /dev/null
ffmpeg -loglevel error -y -i "$OUT" -c:v libx264 -preset slow -b:v ${VB}k -pass 2 -passlogfile "$WORK/p" \
  -c:a copy -movflags +faststart "$PREVIEW"
ls -la "$OUT" "$PREVIEW"
