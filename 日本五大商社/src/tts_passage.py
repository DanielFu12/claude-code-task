"""旁白段落划分：同一段落一次读完（豆包 TTS，src/tts_doubao.py），句间衔接自然；段落之间才是“换场”。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, TEASE, DROPPED

PASSAGES = [
    ('hook', ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7'], ''),
    ('ch1a', ['c1a', 'c1b', 'c1c', 'c1d'], ''),
    ('ch1b', ['c1e', 'c1f', 'c1g', 'c1h', 'c1i'], ''),
    ('ch2a', ['c2a', 'c2b', 'c2c', 'c2d', 'c2e'], ''),
    ('ch2b', ['c2f', 'c2g', 'c2h', 'c2i', 'c2j', 'c2k', 'c2l'], ''),
    ('ch3a', ['c3a', 'c3b', 'c3c', 'c3d', 'c3e'], ''),
    ('ch3b', ['c3f', 'c3g', 'c3h', 'c3i', 'c3j'], ''),
    ('ch4a', ['c4a', 'c4b', 'c4c', 'c4d', 'c4e', 'c4f', 'c4g'], ''),
    ('ch4b', ['c4h', 'c4i', 'c4j', 'c4k'], ''),
    ('ch4c', ['c4l', 'c4m', 'c4n', 'c4o', 'c4p'], ''),
    ('ch5a', ['c5a', 'c5b', 'c5c', 'c5d', 'c5e', 'c5f', 'c5g', 'c5h'], ''),
    ('ch6a', ['c6a', 'c6b', 'c6c', 'c6d', 'c6e', 'c6f'], ''),
    ('ch6b', ['c6g', 'c6h'], ''),
    ('ch6c', ['c6i', 'c6j', 'c6k', 'c6l', 'c6m', 'c6n'], ''),
]
TEASE_P = ('tease', ['tease'], '')
GROUPS = {p[0]: [p[0]] for p in PASSAGES}


def spoken(lid):
    if lid == 'tease': return TEASE[1]
    if lid in DROPPED: return DROPPED[lid]
    l = next(l for l in LINES if l[0] == lid)
    return l[3] or l[2]
