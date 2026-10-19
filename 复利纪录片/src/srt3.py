"""第三版字幕（SRT）：原始影像为「中文译文 + 英文原话」，解说为中文（与画面一致）。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t3
from clips import CLIPS, parts


def ts(x):
    h, m, s = int(x // 3600), int(x % 3600 // 60), x % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'


def clip_to_film(c, a0, src):
    """源文件时间 → 成片时间（拼接片段逐段映射）"""
    off = 0.0
    for a, b in parts(c):
        if a - 0.5 <= src <= b + 0.5:
            return a0 + off + (src - a)
        off += b - a
    return a0 + off


def items():
    out = []
    for s in t3.SEGS:
        if s['kind'] != 'clip': continue
        c = CLIPS[s['id']]
        for a, b, en, zh in c['cues']:
            out.append((clip_to_film(c, s['a0'], a), clip_to_film(c, s['a0'], b) + 0.2, f'{zh}\n{en}'))
    for sid, s in t3.SENTS.items():
        out.append((s['t0'], s['t1'] + 0.1, s['text']))
    out.sort()
    return [(a, min(b, out[k + 1][0] - 0.02) if k + 1 < len(out) else b, x) for k, (a, b, x) in enumerate(out)]


if __name__ == '__main__':
    out = sys.argv[1]
    with open(out, 'w', encoding='utf-8') as f:
        for k, (a, b, txt) in enumerate(items(), 1):
            f.write(f'{k}\n{ts(a)} --> {ts(b)}\n{txt}\n\n')
    print('wrote', out)
