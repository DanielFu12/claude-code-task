"""原声字幕对齐：CNBC 逐字稿（字幕文字）× 语音识别逐词时间戳（只用来定时间）。

用法：python3 src/align.py WORK
输入：WORK/asr_words.json（asr.py 生成）
输出：WORK/orig_subs.json —— [{id, en, zh, t0, t1}]，时间相对 CLIP_IN（秒）
"""
import difflib, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import ORIGINAL

NUM = {'50oddbillion': ['50', 'odd', 'billion'], 'thereabouts': ['there', 'about'], 'ph': []}


def norm(w):
    w = w.lower().replace('’', "'")
    w = re.sub(r"[^a-z0-9']", '', w)
    return w.replace("'", '')


def tokens(s):
    out = []
    for w in s.split():
        n = norm(w)
        if not n:
            continue
        out += NUM.get(n, [n])
    return out


work = sys.argv[1]
asr = json.load(open(os.path.join(work, 'asr_words.json')))
A = []                       # (token, t0, t1)
for t0, t1, w, p in asr:
    for n in tokens(w):
        A.append((n, t0, t1))
# 从提问者开口（逐字稿第一句的第一个词）开始匹配；前面是上一个问题的结尾
first = tokens(ORIGINAL[0][2])[0]
start = next(i for i in range(len(A) - 1) if A[i][0] == first)
A = A[start:]

T, owner = [], []
for k, (sid, sc, en, zh) in enumerate(ORIGINAL):
    for n in tokens(en):
        T.append(n); owner.append(k)

sm = difflib.SequenceMatcher(None, T, [a[0] for a in A], autojunk=False)
tt = [None] * len(T)
for b in sm.get_matching_blocks():
    for j in range(b.size):
        tt[b.a + j] = (A[b.b + j][1], A[b.b + j][2])
hit = sum(x is not None for x in tt)
print(f'matched {hit}/{len(T)} words ({hit / len(T):.1%})')
# 没对上的词按前后已知时间插值
known = [i for i, x in enumerate(tt) if x]
for i in range(len(tt)):
    if tt[i] is None:
        lo = max([k for k in known if k < i], default=None)
        hi = min([k for k in known if k > i], default=None)
        if lo is None: tt[i] = tt[hi]
        elif hi is None: tt[i] = tt[lo]
        else:
            f = (i - lo) / (hi - lo)
            a, b = tt[lo][1], tt[hi][0]
            tt[i] = (a + (b - a) * f, a + (b - a) * f)
subs = []
for k, (sid, sc, en, zh) in enumerate(ORIGINAL):
    idx = [i for i, o in enumerate(owner) if o == k]
    subs.append(dict(id=sid, scene=sc, en=en, zh=zh, t0=round(tt[idx[0]][0], 3), t1=round(tt[idx[-1]][1], 3)))
for s in subs:
    print(f"{s['id']:5s} {s['t0']:7.2f} {s['t1']:7.2f}  {s['en'][:60]}")
json.dump(subs, open(os.path.join(work, 'orig_subs.json'), 'w'), ensure_ascii=False, indent=1)
