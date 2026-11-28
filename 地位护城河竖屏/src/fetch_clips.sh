#!/usr/bin/env bash
# 视频片段：Prelinger 档案《Design for Dreaming》（1956，公有领域）截两段 ≤6 秒；Commons 视频（CC BY 3.0）转成 H.264 片段
set -euo pipefail; cd "$(dirname "$0")/.."; mkdir -p media/clips
U=https://dn801209.us.archive.org/0/items/Designfo1956/Designfo1956.mp4
for c in "crowd 108 6" "car 127 6" "turn 349 6"; do
  set -- $c; [ -f media/clips/dfd_$1.mp4 ] || ffmpeg -v error -y -ss $2 -i "$U" -t $3 -an -c:v libx264 -crf 14 -preset fast media/clips/dfd_$1.mp4
done
# 香港机场 7 米 Labubu、孔雀开屏（由 src/fetch_titles.py 下载到 media_raw/）
clip() { [ -f "media/clips/$2.mp4" ] || ffmpeg -v error -y -ss $3 -i "media_raw/$1.webm" -t $4 -an -vf "scale=-2:1080" -c:v libx264 -crf 15 -preset fast "media/clips/$2.mp4"; }
clip v_airport airport ${AIRPORT_SS:-0} 6
clip v_peacock peacock ${PEACOCK_SS:-0} 7
