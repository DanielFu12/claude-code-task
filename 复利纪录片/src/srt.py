"""导出旁白字幕（SRT），与画面烧录字幕一致。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import lines
from script import NARRATION, CAPTIONS


def ts(x):
    h, m, s = int(x // 3600), int(x % 3600 // 60), x % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'


if __name__ == '__main__':
    out = sys.argv[1]
    with open(out, 'w', encoding='utf-8') as f:
        for k, (nid, a, b) in enumerate(lines(), 1):
            f.write(f'{k}\n{ts(a)} --> {ts(b + 0.2)}\n{CAPTIONS.get(nid, NARRATION[nid])}\n\n')
    print('wrote', out)
