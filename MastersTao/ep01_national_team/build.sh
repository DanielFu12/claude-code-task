#!/usr/bin/env bash
# 一键重建 EP01《国家队去哪了？》
#   ./build.sh            使用已缓存的原始数据，重算统计 → 合成配乐 → 渲染 → 封装正式版与预览版
#   ./build.sh --refetch  重新下载 19 个季度的股东名单与指数（数据会随交易所披露更新）
# 依赖：ffmpeg、python3（numpy pandas opencv-python-headless pillow scipy soundfile）
set -euo pipefail
cd "$(dirname "$0")"
EP=$(pwd); ROOT=$(cd .. && pwd); WORK="$EP/work"; OUT="$EP/output"
mkdir -p "$WORK" "$OUT" "$ROOT/fonts"

# 1) 字体（Google Fonts：Noto Sans SC / Noto Serif SC / JetBrains Mono；Inter Display 取自系统或 rsms/inter）
get(){ [ -f "$ROOT/fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "$ROOT/fonts/$3.ttf" "$url"; }
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 400 sans_reg; get Noto+Sans+SC 500 sans_med
get Noto+Sans+SC 700 sans_bold; get Noto+Sans+SC 900 sans_black
get Noto+Serif+SC 700 serif_bold; get Noto+Serif+SC 900 serif_black; get JetBrains+Mono 500 mono
for w in SemiBold Bold Black Light Medium; do
  f="$ROOT/fonts/InterDisplay-$w.otf"; [ -f "$f" ] && continue
  if [ -f "/usr/share/fonts/opentype/inter/InterDisplay-$w.otf" ]; then cp "/usr/share/fonts/opentype/inter/InterDisplay-$w.otf" "$f"
  else curl -sSfL -o "$WORK/inter.zip" https://github.com/rsms/inter/releases/download/v4.0/Inter-4.0.zip && unzip -joq "$WORK/inter.zip" "extras/otf/InterDisplay-*.otf" -d "$ROOT/fonts/"; fi
done

# 2) 数据
if [ "${1:-}" = "--refetch" ]; then
  python3 scripts/fetch_holders.py --force
  rm -f data/raw/idx_*.json
fi
python3 scripts/fetch_holders.py          # 已缓存的季度会跳过
python3 scripts/fetch_index.py
python3 scripts/build_dataset.py
python3 scripts/verify.py

# 3) 配乐
python3 src/audio.py "$WORK/score.wav"

# 4) 逐帧渲染（4 进程并行，每进程单线程，避免线程争用）
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
N=$(python3 -c "import sys; sys.path.insert(0,'src'); from timeline import DURATION; print(int(round(DURATION*30)))")
P=4; STEP=$(( (N + P - 1) / P ))
for k in $(seq 0 $((P-1))); do
  s=$((k*STEP)); e=$(( (k+1)*STEP < N ? (k+1)*STEP : N ))
  python3 src/video.py chunk $s $e "$WORK/seg$k.mp4" &
done; wait
printf "file '%s'\n" "$WORK"/seg{0,1,2,3}.mp4 > "$WORK/list.txt"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -c copy "$WORK/video.mp4"

# 5) 正式版：1080×1920，两遍编码 8 Mbps（H.264 High）+ AAC 256k
M="$OUT/国家队去哪了_EP01_1080x1920.mp4"; PV="$OUT/国家队去哪了_EP01_预览版.mp4"
ffmpeg -loglevel error -y -i "$WORK/video.mp4" -c:v libx264 -preset slow -b:v 8000k -pass 1 -passlogfile "$WORK/pm" -an -f mp4 /dev/null
ffmpeg -loglevel error -y -i "$WORK/video.mp4" -i "$WORK/score.wav" -map 0:v -map 1:a -c:v libx264 -preset slow -b:v 8000k \
  -maxrate 16000k -bufsize 16000k -pass 2 -passlogfile "$WORK/pm" -pix_fmt yuv420p -profile:v high -level 4.2 \
  -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart "$M"

# 6) 预览版：≤ 30MB。720×1280 + 轻度降噪（去掉防色带颗粒）后两遍编码，码率按时长反算并留 4.5% 余量
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$M")
VB=$(python3 -c "print(int(30*8*1000*1000*0.955/$DUR/1000 - 128))")
VF="scale=720:1280:flags=lanczos,hqdn3d=1.5:1.5:4:4"
ffmpeg -loglevel error -y -i "$WORK/video.mp4" -vf "$VF" -c:v libx264 -preset slower -b:v ${VB}k -pass 1 -passlogfile "$WORK/pp" -an -f mp4 /dev/null
ffmpeg -loglevel error -y -i "$WORK/video.mp4" -i "$WORK/score.wav" -map 0:v -map 1:a -vf "$VF" -c:v libx264 -preset slower \
  -b:v ${VB}k -maxrate $((VB*2))k -bufsize $((VB*3))k -pass 2 -passlogfile "$WORK/pp" -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 48000 -shortest -movflags +faststart "$PV"
ls -la "$OUT"
