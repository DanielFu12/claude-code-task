#!/usr/bin/env bash
# 一键重建《汇金退出了谁？》（依赖与 EP01 相同；复用 EP01 的渲染引擎、原始全量名单与配乐素材）
#   ./build.sh            使用已缓存数据
#   ./build.sh --refetch  重新下载汇金资管逐条持股记录
set -euo pipefail
cd "$(dirname "$0")"
EP=$(pwd); WORK="$EP/work"; OUT="$EP/output"; mkdir -p "$WORK" "$OUT"
[ "${1:-}" = "--refetch" ] && python3 scripts/fetch_hjam.py
[ -f data/raw/hjam_RPT_F10_EH_HOLDERS.csv ] || python3 scripts/fetch_hjam.py
python3 scripts/build_hjam.py > /dev/null
python3 scripts/verify.py
python3 src/audio_track.py "$WORK/score.wav"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
N=$(python3 -c "import sys; sys.path.insert(0,'src'); from timeline import DURATION; print(int(round(DURATION*30)))")
P=4; STEP=$(( (N + P - 1) / P )); rm -f "$WORK"/seg*.mp4; pids=()
for k in $(seq 0 $((P-1))); do
  s=$((k*STEP)); e=$(( (k+1)*STEP < N ? (k+1)*STEP : N ))
  python3 src/video.py chunk $s $e "$WORK/seg$k.mp4" & pids+=($!)
done
for p in "${pids[@]}"; do wait "$p" || { echo "渲染进程失败" >&2; exit 1; }; done
printf "file '%s'\n" "$WORK"/seg{0,1,2,3}.mp4 > "$WORK/list.txt"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -c copy "$WORK/video.mp4"
M="$OUT/汇金退出了谁_1080x1920.mp4"; PV="$OUT/汇金退出了谁_预览版.mp4"
ffmpeg -loglevel error -y -i "$WORK/video.mp4" -c:v libx264 -preset slow -b:v 8000k -pass 1 -passlogfile "$WORK/pm" -an -f mp4 /dev/null
ffmpeg -loglevel error -y -i "$WORK/video.mp4" -i "$WORK/score.wav" -map 0:v -map 1:a -c:v libx264 -preset slow -b:v 8000k \
  -maxrate 16000k -bufsize 16000k -pass 2 -passlogfile "$WORK/pm" -pix_fmt yuv420p -profile:v high -level 4.2 \
  -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart "$M"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$M")
VB=$(python3 -c "print(int(30*8*1000*1000*0.955/$DUR/1000 - 128))")
VF="scale=720:1280:flags=lanczos,hqdn3d=1.5:1.5:4:4"
ffmpeg -loglevel error -y -i "$WORK/video.mp4" -vf "$VF" -c:v libx264 -preset slower -b:v ${VB}k -pass 1 -passlogfile "$WORK/pp" -an -f mp4 /dev/null
ffmpeg -loglevel error -y -i "$WORK/video.mp4" -i "$WORK/score.wav" -map 0:v -map 1:a -vf "$VF" -c:v libx264 -preset slower \
  -b:v ${VB}k -maxrate $((VB*2))k -bufsize $((VB*3))k -pass 2 -passlogfile "$WORK/pp" -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 48000 -shortest -movflags +faststart "$PV"
ls -la "$OUT"
