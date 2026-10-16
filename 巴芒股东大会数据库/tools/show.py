#!/usr/bin/env python3
"""阅读辅助：按章节 ID 打印逐字稿（提问者只保留开头，便于快速通读）。
用法：python3 tools/show.py CHAPTERS.jsonl 1994-M39 1995-M25 ...
"""
import json
import sys

KEEP = {'WARREN BUFFETT', 'CHARLIE MUNGER', 'GREG ABEL', 'AJIT JAIN'}


def main(path, ids):
    want = set(ids)
    for line in open(path, encoding='utf-8'):
        r = json.loads(line)
        if r['id'] not in want:
            continue
        print(f"\n##### {r['id']} | {r['title']} | {r['words']}w")
        for p in r['paragraphs']:
            sp = p['speaker'] or '?'
            t = p['text']
            if sp in KEEP:
                tag = {'WARREN BUFFETT': 'WB', 'CHARLIE MUNGER': 'CM'}.get(sp, sp)
                print(f"{tag}: {t}")
            else:
                w = t.split()
                print(f"[{sp[:12]}] {' '.join(w[:45])}{' …' if len(w) > 45 else ''}")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
