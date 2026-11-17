"""旁白段落划分：同一段落一次读完（豆包 TTS，src/tts_doubao.py），句间衔接自然；段落之间才是“换场”。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, TEASE, DROPPED

PASSAGES = [
    ('hook', ['h1'], ''),
    ('hook2', ['h2', 'h3', 'h4'], ''),
    ('ch1a', ['c1a', 'c1b'], ''),
    ('ch1b', ['c1c', 'c1d', 'c1e'], ''),
    ('ch1c', ['c1f', 'c1g', 'c1h'], ''),
    ('ch1d', ['c1i'], ''),
    ('ch1e', ['c1j'], ''),
    ('ch2a', ['c2a', 'c2b'], ''),
    ('ch2b', ['c2c', 'c2d'], ''),
    ('ch2c', ['c2e'], ''),
    ('ch2d', ['c2f', 'c2g'], ''),
    ('ch3a', ['c3a', 'c3b', 'c3c'], ''),
    ('ch3b', ['c3d', 'c3e', 'c3f'], ''),
    ('ch3c', ['c3g'], ''),
    ('ch3d', ['c3h', 'c3i'], ''),
    ('ch4a', ['c4a', 'c4b', 'c4c'], ''),
    ('ch4b', ['c4d', 'c4e'], ''),
    ('ch4c', ['c4f', 'c4g', 'c4h'], ''),
    ('ch5a', ['c5a', 'c5b', 'c5c'], ''),
    ('ch5b', ['c5d', 'c5e'], ''),
    ('ch5c', ['c5f', 'c5g'], ''),
    ('ch5d', ['c5h', 'c5i'], ''),
    ('ch5e', ['c5j', 'c5k'], ''),
    ('ch6a', ['c6a', 'c6b'], ''),
    ('ch6b', ['c6c', 'c6d'], ''),
    ('ch6c', ['c6e', 'c6f'], ''),
    ('ch7a', ['c7a', 'c7b', 'c7c'], ''),
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
