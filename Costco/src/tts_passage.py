"""旁白段落划分：同一段落一次读完（豆包 TTS，src/tts_doubao.py），句间衔接自然；段落之间才是“换场”。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, TEASE, DROPPED

PASSAGES = [
    ('hook', ['h1', 'h2'], ''),
    ('hook2', ['h3', 'h4', 'h5'], ''),
    ('ch1a', ['c1a', 'c1b', 'c1c'], ''),
    ('ch1b', ['c1d', 'c1e', 'c1f', 'c1g'], ''),
    ('ch2a', ['c2a', 'c2b', 'c2c', 'c2d'], ''),
    ('ch2b', ['c2e', 'c2f', 'c2g', 'c2h', 'c2i'], ''),
    ('ch3a', ['c3a', 'c3b', 'c3c'], ''),
    ('ch3b', ['c3d', 'c3e'], ''),
    ('ch3c', ['c3f', 'c3g', 'c3h', 'c3i'], ''),
    ('ch4a', ['c4a', 'c4b', 'c4c', 'c4d'], ''),
    ('ch4b', ['c4e', 'c4f'], ''),
    ('ch4c', ['c4g', 'c4h'], ''),
    ('ch5a', ['c5a', 'c5b', 'c5c'], ''),
    ('ch5b', ['c5d', 'c5e'], ''),
    ('ch5c', ['c5f', 'c5g'], ''),
    ('ch5d', ['c5h', 'c5i'], ''),
    ('ch5e', ['c5j', 'c5k'], ''),
    ('ch5f', ['c5l'], ''),
    ('ch6a', ['c6a', 'c6b', 'c6c', 'c6d'], ''),
    ('ch6b', ['c6e', 'c6f', 'c6g'], ''),
    ('ch7a', ['c7a'], ''),
    ('ch7d', ['c7d', 'c7e'], ''),
    ('ch7e', ['c7f', 'c7g'], ''),
]
TEASE_P = ('tease', ['tease'], '')
GROUPS = {p[0]: [p[0]] for p in PASSAGES}
assert sorted(i for p in PASSAGES for i in p[1]) == sorted(l[0] for l in LINES), '段落与 LINES 不一致'


def spoken(lid):
    if lid == 'tease': return TEASE[1]
    if lid in DROPPED: return DROPPED[lid]
    l = next(l for l in LINES if l[0] == lid)
    return l[3] or l[2]
