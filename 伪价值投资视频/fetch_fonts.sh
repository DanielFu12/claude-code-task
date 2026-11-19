#!/usr/bin/env bash
# 从 Google Fonts 下载所需字体到 fonts/
set -euo pipefail; cd "$(dirname "$0")"; mkdir -p fonts
get(){ [ -f "fonts/$3.ttf" ] && return 0; url=$(curl -sSf "https://fonts.googleapis.com/css2?family=$1:wght@$2" | grep -o 'https://[^)]*\.ttf' | head -1); curl -sSfL -o "fonts/$3.ttf" "$url"; }
get Noto+Serif+SC 300 serif_light; get Noto+Serif+SC 500 serif_med; get Noto+Serif+SC 900 serif_black
get Noto+Sans+SC 300 sans_light; get Noto+Sans+SC 500 sans_med; get Noto+Sans+SC 900 sans_black
get Cormorant+Garamond 500 corm; get Cormorant+Garamond 600 corm_b; get JetBrains+Mono 400 mono; get Oswald 500 num; get Long+Cang 400 hand
