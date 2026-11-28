#!/usr/bin/env bash
# 视频片段：Prelinger 档案《Design for Dreaming》（1956，公有领域）截两段 ≤6 秒；Commons 视频（CC BY 3.0）转成 H.264 片段
set -euo pipefail; cd "$(dirname "$0")/.."; mkdir -p media/clips
U=https://dn801209.us.archive.org/0/items/Designfo1956/Designfo1956.mp4
for c in "crowd 108 6" "car 127 6" "turn 349 6"; do
  set -- $c; [ -f media/clips/dfd_$1.mp4 ] || ffmpeg -v error -y -ss $2 -i "$U" -t $3 -an -c:v libx264 -crf 14 -preset fast media/clips/dfd_$1.mp4
done
# 香港机场 7 米 Labubu、孔雀开屏（由 src/fetch_titles.py 下载到 media_raw/）
# 竖屏里以 16:9 画面居中展示（1080×608）。机场片段取正面镜头的上半幅（裁掉下方烧录字幕，台标在裁切范围外）
clip() { [ -f "media/clips/$2.mp4" ] || ffmpeg -v error -y -ss $3 -i "media_raw/$1.webm" -t $4 -an -vf "$5,scale=1080:608:flags=lanczos,setsar=1" -c:v libx264 -crf 14 -preset fast "media/clips/$2.mp4"; }
clip v_airport airport ${AIRPORT_SS:-0.2} 5.6 "crop=iw*0.44:iw*0.44*608/1080:iw*0.28:0"
clip v_peacock peacock ${PEACOCK_SS:-25.5} 7 "crop=iw:ih:0:0"
# 横版：孔雀片段保留 1280×720 原分辨率
[ -f media/clips/peacock_h.mp4 ] || ffmpeg -v error -y -ss ${PEACOCK_SS:-25.5} -i media_raw/v_peacock.webm -t 7 -an -c:v libx264 -crf 14 -preset fast media/clips/peacock_h.mp4
# v3：中国新闻社 Labubu 新闻片（CC BY 3.0，由 src/fetch_pages.py 下载）各取两段无采访、无字幕的人潮 / 货架镜头拼接；
# 裁掉左上角台标后缩回 1920×1080。竖版取中间 9:16，横版用全幅
cat2() { [ -f "media/clips/$1.mp4" ] || ffmpeg -v error -y -ss $3 -t $4 -i "media_raw/v_$1.webm" -ss $5 -t $6 -i "media_raw/v_$1.webm" \
  -filter_complex "[0:v][1:v]concat=n=2:v=1[c];[c]crop=iw*0.82:ih*0.82:iw*0.18:ih*0.16,scale=1920:1080:flags=lanczos,setsar=1,fps=30" -an -c:v libx264 -crf 16 -preset fast "media/clips/$1.mp4"; }
cat2 labubu_bj x 10 4 32 3.5      # 北京快闪店：泡泡玛特门店外的人群 → 排队
cat2 labubu_hk x 44 3.5 117 4.5   # 香港：POP MART 门店外的人潮 → 店内货架
