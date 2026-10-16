#!/usr/bin/env python3
"""把 output/entries.json 和品牌角标打包成单文件网页 output/site/index.html。

用法：python3 tools/make_site.py [OUT_DIR]
角标使用仓库 brand/hud_lockup@4x.png（CLAUDE.md 要求：右上角放「巴芒价值」品牌角标）。
"""
import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent
KEEP = ['id', 'year', 'session', 'speakers', 'themes', 'cluster', 'cluster_name', 'title', 'core',
        'quote', 'zh', 'lesson', 'depth', 'practical', 'insight', 'score', 'start_hms', 'end_hms',
        'link', 'chapter', 'chapter_title', 'related', 'top_rank']


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'output'
    data = json.loads((out / 'entries.json').read_text(encoding='utf-8'))
    data['entries'] = [{k: e.get(k) for k in KEEP} for e in data['entries']]
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    badge = base64.b64encode((REPO / 'brand' / 'hud_lockup@4x.png').read_bytes()).decode()
    html = (ROOT / 'tools' / 'site_template.html').read_text(encoding='utf-8')
    html = html.replace('__BADGE__', 'data:image/png;base64,' + badge).replace('__DATA__', payload)
    site = out / 'site'
    site.mkdir(parents=True, exist_ok=True)
    (site / 'index.html').write_text(html, encoding='utf-8')
    print(f"{site / 'index.html'}: {len(html.encode()) / 1e6:.2f} MB")


if __name__ == '__main__':
    main()
