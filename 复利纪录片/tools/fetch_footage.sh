#!/usr/bin/env bash
# 获取本片使用的原始影像（不入库，仅供复现）。下载到 footage/src/，文件名与 src/clips.py 中的 src 字段一致。
# YouTube 原片在本环境无法下载（googlevideo 对所有出口 IP 返回 403），因此用 B 站转载版本：
#   - 李录：转载的是哥大官方多机位录像（1440×1080，16:9 画面 + 上下黑边），无烧录字幕，转载水印在黑边里，裁切后不可见。
#   - 巴菲特 1999 股东大会：转载版本带水印和底部硬字幕，clips.py 的裁切框只取讲台区域，两者都在画面外。
#   - 芒格 BBC：转载者剪的竖版短片，只取其中的 BBC 原画面区域。
# 画面中出现的所有字幕都是本片重新制作的。
set -euo pipefail
cd "$(dirname "$0")/.."; mkdir -p footage/src; cd footage/src
B="yt-dlp --no-playlist -R 30 --fragment-retries 30"
# 李录 · 哥伦比亚商学院第 36 届格雷厄姆与多德年度活动（2026.10.05）——原始：youtube.com/watch?v=YRhnX_JAbC8
# 只取 4970–5240 秒（四段原声都在这里）。区间下载的音轨偶尔会被截短，所以音轨单独取整段再按同一区间裁切。
if [ ! -f lilu_official_4970.mp4 ]; then
  $B -f 30080 --download-sections "*4970-5240" --force-keyframes-at-cuts -o lilu_v.mp4 "https://www.bilibili.com/video/BV1EKJQ6fErY"
  $B -f 30280 -o lilu_a.m4a "https://www.bilibili.com/video/BV1EKJQ6fErY"
  ffmpeg -loglevel error -y -i lilu_v.mp4 -i lilu_a.m4a -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k \
    -af "atrim=start=4970:end=5240,asetpts=PTS-STARTPTS" lilu_official_4970.mp4
fi
# 芒格 · BBC 专访（2009.10）片段转载
[ -f munger_bbc2009.mp4 ] || $B -f "bv*+ba" --merge-output-format mp4 -o munger_bbc2009.mp4 "https://www.bilibili.com/video/BV1bSTg6NEoc"
# 芒格 · 南加州大学法学院毕业典礼演讲（2007.05.13），无字幕版本
[ -f munger_usc2007.mp4 ] || $B -f "bv*[height<=720]+30280" --http-chunk-size 2M --merge-output-format mp4 -o munger_usc2007.mp4 "https://www.bilibili.com/video/BV1Mx411h7cg"
# 巴菲特 · 伯克希尔 1999 年股东大会（只下载用到的两段；clips.py 中的 off 即段落起点，已用词级时间戳校准）
[ -f brk1999_a.mp4 ] || $B -f "bv*[height<=720]+ba" --merge-output-format mp4 --download-sections "*1430-1465" --force-keyframes-at-cuts -o brk1999_a.mp4 "https://www.bilibili.com/video/BV1M319ByEQF"
[ -f brk1999_b.mp4 ] || $B -f "bv*[height<=720]+ba" --merge-output-format mp4 --download-sections "*13615-13660" --force-keyframes-at-cuts -o brk1999_b.mp4 "https://www.bilibili.com/video/BV1M319ByEQF"
# 注意：--download-sections 的实际起点可能有零点几秒偏差；如有偏差，用词级时间戳重新测量后修改 clips.py 的 off。
ls -la
