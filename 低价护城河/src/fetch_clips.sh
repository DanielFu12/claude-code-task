#!/usr/bin/env bash
# ABC News《20/20》2005 年 Costco 报道（archive.org youtube-f9Iv_vdO7sw）里截取的几段空镜，每段 ≤6.4 秒，评论性引用
set -euo pipefail; cd "$(dirname "$0")/.."; mkdir -p media/clips
U=https://ia600405.us.archive.org/0/items/youtube-f9Iv_vdO7sw/f9Iv_vdO7sw.ia.mp4
for c in "crowd 37 8" "floor 150.7 3.1" "aisle 193.8 3.8" "cans 211.4 6.4" "fork 271.2 6.2"; do
  set -- $c; [ -f media/clips/abc_$1.mp4 ] || ffmpeg -v error -y -ss $2 -i "$U" -t $3 -an -c:v libx264 -crf 16 -preset fast media/clips/abc_$1.mp4
done
