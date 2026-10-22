#!/usr/bin/env bash
# 一键重建《追涨十年》视频（1080×1920 · 30fps · 181s）
# 依赖: ffmpeg, python3 (numpy opencv-python-headless pillow[raqm] scipy soundfile librosa pandas requests curl_cffi)
# 品牌角标与片尾 logo 取自仓库根目录 brand/（见 brand/BRAND.md）
#
#   ./build.sh            # 用已提交的 backtest/out_*.json 直接渲染
#   ./build.sh backtest   # 先重新下载数据并回测（约 30–60 分钟，需要网络）
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd); WORK="$ROOT/work"; mkdir -p "$WORK" fonts
NAME="追涨十年"

# 0) 可选：重跑回测
if [ "${1:-}" = "backtest" ]; then
  C="$ROOT/backtest/cache"; mkdir -p "$C"
  [ -d "$C/sp500" ] || git clone --depth 1 https://github.com/fja05680/sp500.git "$C/sp500"
  python3 - "$C" <<'PY'
import sys, pandas as pd
c = sys.argv[1]
d = pd.read_csv(c + '/sp500/S&P 500 Historical Components & Changes (Updated).csv'); d['date'] = pd.to_datetime(d.date)
s = set()
for y in range(2014, 2026): s |= set(d[d.date <= f'{y}-12-31'].iloc[-1].tickers.split(','))
open(c + '/us_tickers.txt', 'w').write('\n'.join(sorted(s | {'^SP500TR'})))
PY
  (cd "$C" && python3 "$ROOT/backtest/fetch_us.py" us_raw us_tickers.txt)
  (cd "$C" && python3 "$ROOT/backtest/fetch_cn.py" month cn/month)
  python3 backtest/fetch_cn_ipo.py "$C/cn/ipo.json"
  python3 backtest/fetch_cn_events.py "$C/cn/events.json"
  (cd backtest && CHAMP_CACHE="$C" python3 us.py && CHAMP_CACHE="$C" python3 cn.py && python3 export_tables.py)
fi

# 1) 字体（Google Fonts）
get(){ [ -f "fonts/$3.ttf" ] && return; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Serif+SC 500 serif_med; get Noto+Serif+SC 700 serif_bold; get Noto+Serif+SC 900 serif_black
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 400 sans_reg; get Noto+Sans+SC 500 sans_med
get Noto+Sans+SC 700 sans_bold; get Noto+Sans+SC 900 sans_black
get Inter 400 inter_reg; get Inter 600 inter_semi; get Inter 800 inter_xbold; get Inter+Tight 900 intert_black
get Cormorant+Garamond 600 corm; get JetBrains+Mono 500 mono

# 2) 画面数据 + 配乐（Lyria 配乐 + 低频音效层，事件对齐 src/timeline.py）
(cd src && python3 story.py)
(cd src && python3 audio.py ../music/score_lyria.mp3 "$WORK/mix.wav")

# 3) 逐帧渲染（4 进程并行）
N=$(python3 -c "import sys; sys.path.insert(0,'src'); from timeline import T_TOTAL; print(int(round(T_TOTAL*30)))")
P=4; S=$(( (N + P - 1) / P ))
for k in $(seq 0 $((P-1))); do
  a=$((k*S)); b=$(( (k+1)*S < N ? (k+1)*S : N ))
  (cd src && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python3 video.py chunk $a $b "$WORK/seg$k.mp4") &
done
wait
: > "$WORK/list.txt"; for k in $(seq 0 $((P-1))); do echo "file '$WORK/seg$k.mp4'" >> "$WORK/list.txt"; done

# 4) 合成正式成片（x264 slow / CRF 16 / High@4.2，音频 AAC 256k）
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -i "$WORK/mix.wav" \
  -map 0:v -map 1:a -c:v libx264 -preset slow -crf 16 -profile:v high -level 4.2 -pix_fmt yuv420p \
  -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart "$ROOT/$NAME.mp4"

# 5) 预览版（< 30 MB：两遍 x264 码率控制）
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$ROOT/$NAME.mp4")
VB=$(python3 -c "print(int(27.5e6*8/$DUR - 128000))")   # 目标约 27.5 MB（十进制），确保 < 30,000,000 字节
ffmpeg -loglevel error -y -i "$ROOT/$NAME.mp4" -c:v libx264 -preset slow -b:v $VB -pass 1 -an -f mp4 -passlogfile "$WORK/x264" /dev/null
ffmpeg -loglevel error -y -i "$ROOT/$NAME.mp4" -c:v libx264 -preset slow -b:v $VB -pass 2 -passlogfile "$WORK/x264" \
  -c:a aac -b:a 128k -movflags +faststart "$ROOT/${NAME}_预览版.mp4"
ls -lh "$ROOT/$NAME.mp4" "$ROOT/${NAME}_预览版.mp4"
