#!/usr/bin/env bash
# 一键重建《伯克希尔股东大会投资智慧录》第一集 · 内在价值（1080×1920 竖屏）
# 依赖：ffmpeg、python3（numpy scipy opencv-python-headless pillow soundfile librosa edge-tts faster-whisper）
# 网络：archive.org（原始录音与影像）、Google Fonts、incompetech.com（CC BY 音乐）、generativelanguage.googleapis.com（Gemini TTS）、Hugging Face（faster-whisper 模型）
# 配音：Gemini TTS（声音 charon）。key 由云环境的 Network secret 注入，或本地设环境变量 GEMINI_API_KEY；TTS_ENGINE=edge 改用备用的 Edge TTS
# 品牌：右上角角标与片尾 logo / 文字全部取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); WORK="$ROOT/work"; mkdir -p "$WORK/music" fonts
OUT="$ROOT/E01_内在价值_1080x1920.mp4"
PREVIEW="$ROOT/E01_内在价值_预览版.mp4"

# 1) 字体（Google Fonts，SIL OFL）；品牌字体由 brand.py 下载到 brand/fonts/
python3 -c "import sys; sys.path.insert(0, '../../brand'); import brand; brand._font('serif_black', 10); brand._font('corm', 10)"
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf -A curl "https://fonts.googleapis.com/css2?family=$1:$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Sans+SC wght@300 sans_light; get Noto+Sans+SC wght@400 sans_reg; get Noto+Sans+SC wght@500 sans_med; get Noto+Sans+SC wght@700 sans_bold
get Noto+Serif+SC wght@500 serif_med; get Noto+Serif+SC wght@700 serif_bold; get Noto+Serif+SC wght@900 serif_black
get Cormorant+Garamond wght@500 corm_med; get Cormorant+Garamond wght@600 corm
get EB+Garamond wght@400 ebg_reg; get EB+Garamond ital,wght@1,400 ebg_ital; get Inter wght@400 inter_reg; get Inter wght@600 inter_semi

# 2) 原始素材：按区间读取 archive.org 上的 1994 年全场录像
python3 src/fetch.py "$WORK"
# 3) 原声字幕对齐（逐词时间戳已存在 data/asr_words.json；删掉它会用 faster-whisper medium.en 重新识别）
[ -f data/asr_words.json ] || python3 src/asr.py "$WORK/orig16.wav" data/asr_words.json
cp data/asr_words.json "$WORK/asr_words.json"
python3 src/align.py "$WORK"
# 4) 旁白配音：Gemini TTS 按段落合成 + faster-whisper 强制对齐切句
python3 src/tts.py "$WORK"
# 5) 时间线
python3 src/timeline.py "$WORK"
# 6) 音乐（Kevin MacLeod，CC BY 4.0）与混音
for t in "Undaunted" "The Escalation"; do
  [ -f "$WORK/music/$t.mp3" ] || curl -sSfL -o "$WORK/music/$t.mp3" "https://incompetech.com/music/royalty-free/mp3-royaltyfree/${t// /%20}.mp3"
done
python3 src/audio.py "$WORK" "$WORK/music"
# 7) 逐帧渲染（4 进程并行）
N=$(cd src && python3 render.py nframes "$WORK")
Q=$(( (N + 3) / 4 ))
for k in 0 1 2 3; do
  E=$(( (k + 1) * Q < N ? (k + 1) * Q : N ))
  (cd src && python3 render.py chunk $((k * Q)) $E "$WORK/seg$k.mp4" "$WORK") &
done
wait
printf "file '%s'\n" "$WORK"/seg{0,1,2,3}.mp4 > "$WORK/list.txt"
# 8) 合成：画面 + 混音
#    音频：两遍 loudnorm 线性归一到 -16 LUFS / -1.5 dBTP，AAC 192k
#    视频：从 crf16 中间片两遍编码到 1.4Mbps（实测相对中间片 PSNR≈45dB；更高码率只多保留随机胶片颗粒，肉眼无差别），
#          成片约 90MB，按仓库惯例直接提交（GitHub 单文件上限 100MiB）
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -c copy "$WORK/video_master.mp4"
J=$(ffmpeg -nostats -i "$WORK/mix.wav" -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
mi=$(echo "$J" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"measured_I={d['input_i']}:measured_TP={d['input_tp']}:measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:offset={d['target_offset']}\")")
ffmpeg -loglevel error -y -i "$WORK/mix.wav" -af "loudnorm=I=-16:TP=-1.5:LRA=11:$mi:linear=true,aresample=48000" -c:a aac -b:a 192k -ar 48000 "$WORK/audio.m4a"
X264="-c:v libx264 -preset slow -tune film -profile:v high -pix_fmt yuv420p -b:v 1400k -maxrate 3000k -bufsize 6000k"
ffmpeg -loglevel error -y -i "$WORK/video_master.mp4" $X264 -pass 1 -passlogfile "$WORK/m" -an -f mp4 /dev/null
ffmpeg -loglevel error -y -i "$WORK/video_master.mp4" -i "$WORK/audio.m4a" -map 0:v -map 1:a $X264 -pass 2 -passlogfile "$WORK/m" \
  -c:a copy -shortest -movflags +faststart "$OUT"
# 9) 字幕文件与文档
python3 src/srt.py "$WORK" "$ROOT"
python3 src/docs.py "$WORK" "$ROOT/docs"
# 10) 30MB 以内的预览版：保持 1080×1920，轻度时域降噪（去掉随机颗粒，省码率）后两遍编码，约 28MB
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")
VB=$(python3 -c "print(int(27.8*8*1000*1000/$DUR/1000) - 112)")
P264="-c:v libx264 -preset slow -tune film -profile:v high -pix_fmt yuv420p -b:v ${VB}k -maxrate $((VB*3))k -bufsize $((VB*6))k"
ffmpeg -loglevel error -y -i "$WORK/video_master.mp4" -vf hqdn3d=3:3:6:6 $P264 -pass 1 -passlogfile "$WORK/p" -an -f mp4 /dev/null
ffmpeg -loglevel error -y -i "$WORK/video_master.mp4" -i "$WORK/audio.m4a" -map 0:v -map 1:a -vf hqdn3d=3:3:6:6 $P264 -pass 2 -passlogfile "$WORK/p" \
  -c:a aac -b:a 112k -shortest -movflags +faststart "$PREVIEW"
# 11) 质检
python3 src/check.py "$OUT" "$WORK" "$ROOT/qc"
ls -la "$OUT" "$PREVIEW"
