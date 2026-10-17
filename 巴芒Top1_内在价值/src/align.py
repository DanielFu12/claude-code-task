"""把字幕对齐到原声：faster-whisper 逐词时间戳 + 与逐字稿做序列匹配。

用法：python3 src/align.py WORK
输出：WORK/words.json（识别出的逐词时间，片段内秒数）、WORK/orig_cues.json（每条字幕的起止）
字幕文字始终用逐字稿；识别结果只用来定时间（识别错字不影响字幕）。
"""
import difflib, json, os, re, sys
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import ORIGINAL

work = sys.argv[1]


def norm(w):
    w = w.lower().replace('’', "'").strip()
    w = re.sub(r"[^a-z0-9']", '', w)
    return {'gaap': 'gap'}.get(w, w)


wp = os.path.join(work, 'words.json')
if not os.path.exists(wp):
    from faster_whisper import WhisperModel
    a, _ = sf.read(os.path.join(work, 'orig16.wav'), dtype='float32')
    model = WhisperModel('medium.en', device='cpu', compute_type='int8', cpu_threads=4)
    segs, _ = model.transcribe(a, language='en', word_timestamps=True, beam_size=5, vad_filter=False)
    words = [dict(w=w.word, s=round(w.start, 3), e=round(w.end, 3)) for s in segs for w in s.words]
    json.dump(words, open(wp, 'w'))
words = json.load(open(wp))

# 逐字稿词序列（带所属字幕编号）
ref, owner = [], []
for k, (cid, part, en, zh) in enumerate(ORIGINAL):
    for w in en.split():
        n = norm(w)
        if n:
            ref.append(n); owner.append(k)
hyp = [norm(w['w']) for w in words]
# 只在提问开始之后匹配（片段开头是上一位提问的回答）
start = next(i for i in range(len(hyp) - 1) if hyp[i] == 'mr' and hyp[i + 1] == 'buffett')
sm = difflib.SequenceMatcher(None, ref, hyp[start:], autojunk=False)
t0 = np.full(len(ref), np.nan); t1 = np.full(len(ref), np.nan)
for blk in sm.get_matching_blocks():
    for j in range(blk.size):
        w = words[start + blk.b + j]
        t0[blk.a + j], t1[blk.a + j] = w['s'], w['e']
matched = np.isfinite(t0).mean()
# 未匹配的词按前后已匹配词线性插值
idx = np.arange(len(ref)); ok = np.isfinite(t0)
t0 = np.interp(idx, idx[ok], t0[ok]); t1 = np.interp(idx, idx[ok], t1[ok])
cues = []
for k, (cid, part, en, zh) in enumerate(ORIGINAL):
    ii = [i for i in idx if owner[i] == k]
    cues.append(dict(id=cid, part=part, en=en, zh=zh, s=round(float(t0[ii[0]]), 3), e=round(float(t1[ii[-1]]), 3),
                     matched=round(float(ok[ii].mean()), 2)))
for a, b in zip(cues, cues[1:]):
    assert a['s'] < a['e'] <= b['s'] + 0.05, (a, b)
json.dump(cues, open(os.path.join(work, 'orig_cues.json'), 'w'), ensure_ascii=False, indent=1)
print('matched %.0f%% of transcript words; %d cues %.2f–%.2fs' % (matched * 100, len(cues), cues[0]['s'], cues[-1]['e']))
for c in cues:
    if c['matched'] < 0.7: print('low match', c['id'], c['matched'], c['en'][:50])
