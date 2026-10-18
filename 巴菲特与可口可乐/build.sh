#!/usr/bin/env bash
# 一键重建《38年，一股未卖——巴菲特与可口可乐》
# 依赖：ffmpeg、python3（numpy opencv-python-headless pillow soundfile librosa scipy pyloudnorm moderngl）、
#       Mesa EGL（libegl1 libegl-mesa0，用于无头 OpenGL）。品牌角标取自仓库根目录 brand/。
# 生成式素材（旁白 TTS、Lyria 配乐）需要 Gemini API；已生成的文件会被复用（work/tts、work/music）。
set -euo pipefail
cd "$(dirname "$0")"
WORK=work; mkdir -p "$WORK" fonts
NAME="38年一股未卖_巴菲特与可口可乐"
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Serif+SC 400 serif_reg; get Noto+Serif+SC 600 serif_semi; get Noto+Serif+SC 900 serif_black
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 500 sans_med; get Noto+Sans+SC 700 sans_bold; get Noto+Sans+SC 900 sans_black
get Cormorant+Garamond 600 corm; get Cormorant+Garamond 500 corm_med; get JetBrains+Mono 500 mono
get Special+Elite 400 typewriter; get Oswald 600 oswald; get Playfair+Display 700 playfair

# 已入库的生成素材（旁白逐句 wav、选定的 3 段 Lyria 配乐）先放进 work/，避免重新生成带来的随机差异
mkdir -p "$WORK/tts" "$WORK/music"
cp -n assets/generated/tts/*.wav "$WORK/tts/" 2>/dev/null || true
cp -n assets/generated/music/*.mp3 "$WORK/music/" 2>/dev/null || true

python3 data/calc.py > /dev/null                       # 收益与股息计算 → data/calc.json
python3 src/tts_gen.py "$WORK"                          # 旁白（缺失才生成）
[ -f "$WORK/music/A_2.mp3" ] || { python3 src/music_gen.py "$WORK" A 3; python3 src/music_gen.py "$WORK" B 3; }
python3 src/timeline.py "$WORK" > /dev/null          # 旁白变速/去静音，得到每句时长
python3 src/music_plan.py "$WORK"                     # 配乐按旁白整小节重复/剪裁，给出卡点
python3 src/timeline.py "$WORK" --keep                # 按卡点排出最终时间线
python3 src/audio_mix.py "$WORK"

N=$(python3 -c "import json;print(int(round(json.load(open('$WORK/timeline.json'))['total']*30)))")
P=${PROCS:-4}; STEP=$(( (N + P - 1) / P ))
for k in $(seq 0 $((P-1))); do python3 src/film.py "$WORK" chunk $((k*STEP)) $(((k+1)*STEP)) "$WORK/seg$k.mp4" & done; wait
: > "$WORK/list.txt"; for k in $(seq 0 $((P-1))); do echo "file 'seg$k.mp4'" >> "$WORK/list.txt"; done
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -c copy "$WORK/video.mp4"
./encode.sh                                              # 成片 + 30MB 预览版
