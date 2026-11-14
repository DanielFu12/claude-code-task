"""旁白段落划分：同一段落一次读完（豆包 TTS，src/tts_doubao.py），句间衔接自然；段落之间才是“换场”。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, TEASE, DROPPED

PASSAGES = [
    ('hook', ['h1', 'h2', 'h3'], ''),
    ('hook2', ['h4'], ''),
    ('ch1a', ['c1a', 'c1a2', 'c1b'], ''),
    ('ch1b', ['c1d', 'c1e', 'c1c', 'c1h', 'c1g'], ''),
    ('ch2a', ['c2a', 'c2b', 'c2c', 'c2d'], ''),
    ('ch2b', ['c2e', 'c2f'], ''),
    ('ch3a', ['c3a', 'c3b', 'c3c', 'c3d', 'c3e'], ''),
    ('ch3b', ['c3f', 'c3g', 'c3h'], ''),
    ('ch3c', ['c3i', 'c3j'], ''),
    ('ch4a', ['c4a', 'c4b', 'c4c', 'c4d', 'c4e', 'c4f'], ''),
    ('ch4b', ['c4g', 'c4h'], ''),
    ('ch4c', ['c4i', 'c4j'], ''),
    ('ch5a', ['c5a', 'c5b', 'c5c', 'c5c2'], ''),
    ('ch5b', ['c5d', 'c5e', 'c5g', 'c5g2'], ''),
    ('ch5c', ['c5i', 'c5j', 'c5k', 'c5k2'], ''),
    ('ch6a', ['c6a', 'c6b', 'c6c', 'c6c2', 'c6d', 'c6e'], ''),
    ('ch7a', ['c7a', 'c7b2', 'c7c'], ''),
    ('ch7b', ['c7d'], ''),
]
TEASE_P = ('tease', ['tease'], '')
GROUPS = {p[0]: [p[0]] for p in PASSAGES}
assert sorted(i for p in PASSAGES for i in p[1]) == sorted(l[0] for l in LINES), '段落与 LINES 不一致'


def spoken(lid):
    if lid == 'tease': return TEASE[1]
    if lid in DROPPED: return DROPPED[lid]
    l = next(l for l in LINES if l[0] == lid)
    return l[3] or l[2]
