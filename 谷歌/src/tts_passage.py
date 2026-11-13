"""旁白段落划分：同一段落一次读完（豆包 TTS，src/tts_doubao.py），句间衔接自然；段落之间才是“换场”。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, TEASE, DROPPED

PASSAGES = [
    ('hook', ['h1', 'h2', 'h3', 'h4', 'h5'], ''),
    ('hook2', ['h6'], ''),
    ('ch1a', ['c1a', 'c1b', 'c1c'], ''),
    ('ch1b', ['c1d', 'c1e', 'c1f'], ''),
    ('ch2a', ['c2a', 'c2b', 'c2c'], ''),
    ('ch2b', ['c2d', 'c2e', 'c2f'], ''),
    ('ch3a', ['c3a', 'c3b', 'c3c', 'c3d'], ''),
    ('ch3b', ['c3e', 'c3f'], ''),
    ('ch4a', ['c4a', 'c4b', 'c4c', 'c4d'], ''),
    ('ch4b', ['c4e', 'c4e2', 'c4f', 'c4g', 'c4g2'], ''),
    ('ch4c', ['c4h', 'c4i'], ''),
    ('ch5a', ['m1', 'm2', 'm3', 'm4'], ''),
    ('ch5b', ['m5', 'm6', 'm7', 'm8'], ''),
    ('ch5c', ['m9', 'm10', 'm11', 'm12'], ''),
    ('ch6a', ['c5a', 'c5a2', 'c5b', 'c5b2', 'c5c', 'c5d'], ''),
    ('ch6b', ['c5e', 'c5e2', 'c5f', 'c5g', 'c5h', 'c5j'], ''),
    ('ch7a', ['c6a', 'c6a2', 'c6b', 'c6c'], ''),
    ('ch7b', ['c6e', 'c6f', 'c6g', 'c6h', 'c6i', 'c6j'], ''),
]
TEASE_P = ('tease', ['tease'], '')
GROUPS = {p[0]: [p[0]] for p in PASSAGES}
assert sorted(i for p in PASSAGES for i in p[1]) == sorted(l[0] for l in LINES), '段落与 LINES 不一致'


def spoken(lid):
    if lid == 'tease': return TEASE[1]
    if lid in DROPPED: return DROPPED[lid]
    l = next(l for l in LINES if l[0] == lid)
    return l[3] or l[2]
