"""导出字幕（SRT），与画面烧录字幕一致：原始影像段为「中文译文 + 英文原话」，动画段为屏幕文字。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import lines
from script import NARRATION, CAPTIONS
from clips import CLIPS
import part1 as P1


def ts(x):
    h, m, s = int(x // 3600), int(x % 3600 // 60), x % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'


def items():
    out = []
    for cid, t0 in P1.FT.SEQ:
        c = CLIPS[cid]
        for a, b, en, zh in c['cues']:
            out.append((t0 + a - c['a'], t0 + b - c['a'] + 0.2, f'{zh}\n{en}'))
    for nid, a, b in lines():
        if nid >= 'N18':
            out.append((a, b + 0.2, CAPTIONS.get(nid, NARRATION[nid])))
    out.sort()
    return [(a, min(b, out[k + 1][0] - 0.02) if k + 1 < len(out) else b, x) for k, (a, b, x) in enumerate(out)]


if __name__ == '__main__':
    out = sys.argv[1]
    with open(out, 'w', encoding='utf-8') as f:
        for k, (a, b, txt) in enumerate(items(), 1):
            f.write(f'{k}\n{ts(a)} --> {ts(b)}\n{txt}\n\n')
    print('wrote', out)
