"""解说声色 A/B 试听包：参照段（片名后的第一段解说 G2，及开场解说 G1）→ 0.8 秒间隔 → 重新合成的段落。
每个文件都是「A = 参照，B = 新合成」，用于人耳确认同一声音、同一风格。
用法：python3 tools/ab_pack.py OUT_DIR
"""
import os, sys, json
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
from story import vo_groups, TAKES, REF_GROUPS

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
VD = os.path.join(ROOT, 'work', 'vo')
SR = 48000


def gwav(gid):
    ids = next([sid for sid, _ in it[2]] for it in vo_groups() if it[1] == gid)
    x, _ = sf.read(os.path.join(VD, 'G_' + '_'.join(ids) + '.wav'))
    return x / (np.sqrt(np.mean(x[np.abs(x) > 1e-3] ** 2)) + 1e-9) * 10 ** (-20 / 20)     # 响度对齐，只比声色


def tone(f=880, d=0.12):
    t = np.arange(int(d * SR)) / SR
    return 0.05 * np.sin(2 * np.pi * f * t) * np.hanning(len(t))


if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    gap = np.zeros(int(0.8 * SR))
    ref = np.concatenate([gwav(REF_GROUPS[1]), gap, gwav(REF_GROUPS[0])[:int(8 * SR)]])
    for gid in TAKES:
        y = np.concatenate([ref, gap, tone(), gap, gwav(gid)])
        p = os.path.join(out, f'AB_参照G2G1_vs_{gid}.wav')
        sf.write(p, y, SR, subtype='PCM_16')
        print(p)
