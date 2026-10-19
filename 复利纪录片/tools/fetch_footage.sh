#!/usr/bin/env bash
# 获取本片使用的原始影像（不入库，仅供复现）。下载到 footage/src/，文件名与 src/clips.py 中的 src 字段一致。
# 说明：YouTube 原始上传在本环境被机器人验证拦截，因此改用 B 站转载版本；B 站版本带有转载者的硬字幕/水印，
#       prep_clips.py 会通过裁切 + 去字幕（src/desub.py）去除，画面中出现的所有字幕均为本片重新制作。
set -euo pipefail
cd "$(dirname "$0")/.."; mkdir -p footage/src; cd footage/src
B="yt-dlp --no-playlist"
# 李录 · 哥伦比亚商学院第 36 届格雷厄姆与多德年度活动（2026.10）——原始：youtube.com/watch?v=YRhnX_JAbC8
[ -f lilu_gd2026.mp4 ] || $B -f "30064+30280" --merge-output-format mp4 -o lilu_gd2026.mp4 "https://www.bilibili.com/video/BV1t6HS6yEbd/?p=1"
# 芒格 · BBC 专访（2009.10）片段转载
[ -f munger_bbc2009.mp4 ] || $B -f "bv*+ba" --merge-output-format mp4 -o munger_bbc2009.mp4 "https://www.bilibili.com/video/BV1bSTg6NEoc"
# 芒格 · 南加州大学法学院毕业典礼演讲（2007.05.13），无字幕版本
[ -f munger_usc2007.mp4 ] || $B -f "bv*[height<=720]+30280" --http-chunk-size 2M --merge-output-format mp4 -o munger_usc2007.mp4 "https://www.bilibili.com/video/BV1Mx411h7cg"
# 巴菲特 · 伯克希尔 1999 年股东大会（只下载用到的两段；clips.py 中的 off 即段落起点）
[ -f brk1999_a.mp4 ] || $B -f "bv*[height<=720]+ba" --merge-output-format mp4 --download-sections "*1430-1465" --force-keyframes-at-cuts -o brk1999_a.mp4 "https://www.bilibili.com/video/BV1M319ByEQF"
[ -f brk1999_b.mp4 ] || $B -f "bv*[height<=720]+ba" --merge-output-format mp4 --download-sections "*13615-13660" --force-keyframes-at-cuts -o brk1999_b.mp4 "https://www.bilibili.com/video/BV1M319ByEQF"
# 注意：--download-sections 的实际起点可能有零点几秒偏差；如有偏差，用 tools 外的词级时间戳重新测量后修改 clips.py 的 off。
ls -la
