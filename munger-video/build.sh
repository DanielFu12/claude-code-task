#!/usr/bin/env bash
# Full build: fonts -> score -> frames -> mux.  Usage: ./build.sh [output.mp4]
set -euo pipefail
cd "$(dirname "$0")"
OUT="${1:-../芒格投资理念-思维的格栅.mp4}"
TMP="$(mktemp -d)"
[ -f fonts/fonts.css ] || ./fetch-fonts.sh
node audio.js "$TMP/score.wav"
NODE_PATH="${NODE_PATH:-$(npm root -g)}" node render.js "$TMP/video.mp4" --workers "${WORKERS:-4}"
# light denoise removes the per-frame film grain so the final file stays small
ffmpeg -v error -y -i "$TMP/video.mp4" -i "$TMP/score.wav" -map 0:v -map 1:a \
  -vf "hqdn3d=5:4:10:8" -c:v libx264 -preset slow -crf 23 -pix_fmt yuv420p \
  -af "loudnorm=I=-14:TP=-1.0:LRA=11" -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart "$OUT"
echo "wrote $OUT"
