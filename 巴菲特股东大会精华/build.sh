#!/usr/bin/env bash
# 一键生成《巴菲特与芒格 · 股东大会精华》（约 10 分钟）+ 每段一条竖版短视频
# 依赖: ffmpeg, python3 (numpy opencv-python-headless pillow), yt-dlp
# 网络: 需要能访问 youtube.com / *.googlevideo.com（下载素材）和 fonts.googleapis.com / fonts.gstatic.com（字体）
# 品牌角标取自仓库根目录 brand/（见 brand/BRAND.md）
set -euo pipefail
cd "$(dirname "$0")"
python3 src/fetch.py subs          # 1) 每届股东大会只下字幕/转写稿（几十 KB）
python3 src/locate.py              # 2) 在转写稿里自动定位每段金句的时间码 -> work/located.json
python3 src/fetch.py media         # 3) 只下载用得到的片段（yt-dlp --download-sections）
python3 src/render.py              # 4) 合成横版成片 -> 巴菲特股东大会精华.mp4 + 章节时间码.md
if [ "${1:-}" = "--shorts" ]; then
  python3 src/render.py shorts     # 5) 可选：每段一条 1080×1920 竖版短视频 -> shorts/
fi
