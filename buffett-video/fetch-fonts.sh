#!/usr/bin/env bash
# Downloads the Google Fonts used by the video into ./fonts (Noto Serif/Sans SC, Cormorant, JetBrains Mono, Playfair).
set -euo pipefail
cd "$(dirname "$0")" && mkdir -p fonts && cd fonts
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
curl -sS -A "$UA" "https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@500;700;900&family=Noto+Sans+SC:wght@300;400;500;700&family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500;1,600&family=JetBrains+Mono:wght@400;500;700&family=Playfair+Display:wght@700;900&display=block" -o remote.css
grep -o "https://fonts.gstatic.com[^)]*" remote.css | sort -u | xargs -P 16 -n 1 sh -c 'f=$(echo "$0" | md5sum | cut -c1-16).woff2; [ -f "$f" ] || curl -sS -o "$f" "$0"'
python3 - <<'PY'
import re, hashlib
css = open('remote.css').read()
css = re.sub(r'url\((https://fonts\.gstatic\.com[^)]*)\)', lambda m: 'url(%s.woff2)' % hashlib.md5((m.group(1) + '\n').encode()).hexdigest()[:16], css)
open('fonts.css', 'w').write(css)
PY
