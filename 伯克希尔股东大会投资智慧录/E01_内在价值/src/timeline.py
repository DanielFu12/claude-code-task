"""整片时间线：把口播、原声、字幕、场景、音乐和音效排到同一条以秒为单位的时间轴上。

用法：python3 src/timeline.py WORK
输入：WORK/vo_index.json、WORK/vo/*.wav、WORK/orig_subs.json
输出：WORK/timeline.json（render.py / audio.py / docs.py 共用）
"""
import difflib, json, os, re, sys
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import INTRO, INSIGHT, SUMMARY, COLD_IDS, LAUGH_AFTER

work = sys.argv[1]
VO = json.load(open(os.path.join(work, 'vo_index.json')))
ORIG = json.load(open(os.path.join(work, 'orig_subs.json')))
OD = {s['id']: s for s in ORIG}

# ------------------------------------------------------------------ 关键时间点（秒）
T_COLD = 1.0                    # 冷开场原声开始
# 剪点按原声能量曲线手工确认：109.31 是 "like" 与 "And" 之间的能量低谷；114.45 之后是句间停顿
COLD_IN, COLD_OUT = 109.31, 114.45
T_TITLE = 7.4                   # 片名 + 第一个音乐重拍
T_S1 = 8.9                      # 片头口播开始
# 原始问答：39.05（芒格上一题说完后的静音）→ 254.95（"plenty of people that do." 之后、下一位提问者 "Zone 3?" 之前的静音）
Q_IN, Q_OUT = 39.05, 254.95
FPS = 30

# 音乐重拍（由 audio.py 里的同一组常量驱动；数值来自对曲目能量突变的分析）
LENTO_HIT_A = 2.6               # Impact Lento 第一个和弦进入
LENTO_HIT_SUM = 117.8           # Impact Lento 尾段的大段落起点 → 总结句
LENTO_HIT_BRAND = 130.1         # 下一个重拍 → 「巴芒价值」浮现
LOST_HIT = 2.0                  # Lost Time 第一个和弦进入 → 投资启示


def voiced(sid):
    x, sr = sf.read(os.path.join(work, 'vo', sid + '.wav'))
    e = np.abs(x) > 10 ** (-45 / 20)
    i = int(np.argmax(e)); j = len(x) - int(np.argmax(e[::-1]))
    a = max(0, i - int(0.04 * sr)); b = min(len(x), j + int(0.10 * sr))
    return a / sr, b / sr


PUNCT = '，。；：？！、—…“”《》·（）,.;:?!'
CUT = '，。；：？！'


def content(s):
    return [c for c in s if c not in PUNCT and not c.isspace()]


def char_times(sid, lead):
    """display 文本每个内容字的 (t0, t1)，相对句子开头（已去掉前导静音）"""
    v = VO[sid]
    say = v['say']; disp = v['text']
    # SAY 文本里每个字的时间：按 WordBoundary 的词文本在 SAY 里依次定位
    st = [None] * len(say)
    pos = 0
    for w0, w1, wt in v['words']:
        k = say.find(wt, pos)
        if k < 0: continue
        n = len(wt)
        for j in range(n):
            st[k + j] = (w0 - lead + (w1 - w0) * j / n, w0 - lead + (w1 - w0) * (j + 1) / n)
        pos = k + n
    sc = [(c, st[i]) for i, c in enumerate(say) if c not in PUNCT and not c.isspace() and st[i]]
    dc = content(disp)
    sm = difflib.SequenceMatcher(None, dc, [c for c, _ in sc], autojunk=False)
    out = [None] * len(dc)
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        for k in range(a0, a1):
            if b1 > b0:
                j = b0 + int((k - a0) * (b1 - b0) / max(a1 - a0, 1))
                out[k] = sc[min(j, b1 - 1)][1]
    last = (0.0, 0.0)
    for k in range(len(out)):
        if out[k] is None: out[k] = last
        last = out[k]
    return out


def vw(s):
    """显示宽度（以一个汉字为 1）"""
    return sum(0.55 if ord(c) < 128 else 1.0 for c in content(s))


def chunks(text, maxw=16.5, short=3.6):
    """按全角标点断句；过长的在「、」/「《」前/「只就也却」前/「的」后等自然断点切开；
    很短的片段（如「大家好」「年底」）按语义并入后一句（逗号后）或前一句（句末）。
    返回 [(显示文本, 首字内容序号, 末字内容序号)]"""
    parts, cur, book = [], '', False
    for ch in text:
        book = (book or ch == '《') and ch != '》'
        if ch in CUT and not book:
            if ch in '？！': cur += ch
            parts.append((cur, ch)); cur = ''
        else:
            cur += ch
    if cur.strip(): parts.append((cur, '。'))
    parts = [(p.strip(), e) for p, e in parts if content(p)]
    out = []
    for p, e in parts:
        stack = [(p, e)]
        while stack:
            q, qe = stack.pop(0)
            if vw(q) <= maxw or ('《' in q and vw(q) <= 21):
                out.append((q, qe)); continue
            n = len(q); mid = n / 2
            inb = [False] * n; f = False
            for j, c in enumerate(q):
                if c == '《': f = True
                inb[j] = f and c != '《'
                if c == '》': f = False
            cand = [(i, 0) for i, c in enumerate(q) if c in '、—' and 2 < i < n - 2]
            cand += [(i, 1) for i, c in enumerate(q) if c in '《只就也却' and 2 < i < n - 2]
            cand += [(i + 1, 2) for i, c in enumerate(q) if c in '的和与在是了' and 2 < i < n - 3]
            cand = [c for c in cand if not inb[c[0]]]
            k = min(cand, key=lambda x: abs(x[0] - mid) + x[1] * 1.5)[0] if cand else int(mid)
            stack[0:0] = [(q[:k].rstrip('、—'), ''), (q[k:].lstrip('、—'), qe)]
    i = 0
    while i < len(out):
        q, qe = out[i]
        if vw(q) <= short:
            if qe in '，：' and i + 1 < len(out) and vw(q) + vw(out[i + 1][0]) <= maxw:
                out[i:i + 2] = [(q + ' ' + out[i + 1][0], out[i + 1][1])]; continue
            if qe in '。？！；' and i > 0 and out[i - 1][1] in '，：' and vw(q) + vw(out[i - 1][0]) <= maxw:
                out[i - 1:i + 1] = [(out[i - 1][0] + ' ' + q, qe)]; i -= 1; continue
        i += 1
    res, idx = [], 0
    for q, qe in out:
        n = len(content(q))
        res.append((q.replace('——', '—'), idx, idx + n - 1)); idx += n
    return res


def lay_vo(items, t, gap_scale=1.0):
    vo, subs, words = [], [], []
    for sid, scene, text, pause in items:
        a, b = voiced(sid)
        ct = char_times(sid, a)
        dur = b - a
        vo.append(dict(id=sid, scene=scene, t0=round(t, 3), t1=round(t + dur, 3), src_in=round(a, 3), text=text))
        for txt, i0, i1 in chunks(text):
            subs.append(dict(id=sid, text=txt, t0=round(t + ct[i0][0] - 0.12, 3), t1=round(t + ct[i1][1] + 0.1, 3)))
        # 逐词（屏幕动画卡点用）
        for w0, w1, wt in VO[sid]['words']:
            words.append(dict(id=sid, w=wt, t=round(t + w0 - a, 3)))
        t += dur + pause * gap_scale
    # 字幕首尾衔接：相邻两条不重叠，短空隙直接接上
    for s0, s1 in zip(subs, subs[1:]):
        if s1['t0'] - s0['t1'] < 0.35: s0['t1'] = s1['t0'] - 0.02
    return vo, subs, words, t


tl = dict(fps=FPS)
# 冷开场
tl['cold'] = dict(t0=T_COLD, t1=T_COLD + COLD_OUT - COLD_IN, src_in=COLD_IN, src_out=COLD_OUT)
tl['cold_subs'] = [dict(id=s['id'], en=s['en'], zh=s['zh'], t0=round(T_COLD + s['t0'] - COLD_IN, 3),
                        t1=round(T_COLD + s['t1'] - COLD_IN + 0.2, 3)) for s in ORIG if s['id'] in COLD_IDS]
for s0, s1 in zip(tl['cold_subs'], tl['cold_subs'][1:]):
    s0['t1'] = min(s0['t1'], s1['t0'] - 0.02)
tl['t_title'] = T_TITLE
# 系列片头口播
vo, subs, words, t = lay_vo(INTRO, T_S1)
tl['intro'] = dict(vo=vo, subs=subs, words=words, t0=T_S1, t1=round(vo[-1]['t1'], 3))
# 进入 1994
T_CTX = round(vo[-1]['t1'] + 1.7, 3)
T_Q = T_CTX + 4.2
T_QEND = T_Q + (Q_OUT - Q_IN)
tl['ctx'] = dict(t0=T_CTX, t1=T_Q + 1.5)
osubs = []
for s in ORIG:
    osubs.append(dict(id=s['id'], scene=s['scene'], en=s['en'], zh=s['zh'],
                      t0=round(T_Q + s['t0'] - Q_IN - 0.08, 3), t1=round(T_Q + s['t1'] - Q_IN + 0.25, 3)))
for s0, s1 in zip(osubs, osubs[1:]):
    if s0['t1'] > s1['t0'] - 0.02: s0['t1'] = s1['t0'] - 0.02
    if s1['t0'] - s0['t1'] < 0.6: s0['t1'] = s1['t0'] - 0.02       # 短停顿时字幕不闪断
laugh = next(s for s in osubs if s['id'] == LAUGH_AFTER)
nxt = osubs[osubs.index(laugh) + 1]
tl['laugh'] = dict(t0=round(laugh['t1'], 3), t1=round(nxt['t0'] - 0.05, 3))
tl['qa'] = dict(t0=round(T_Q, 3), t1=round(T_QEND, 3), src_in=round(Q_IN, 3), src_out=round(Q_OUT, 3),
                subs=osubs, answer_t=next(s['t0'] for s in osubs if s['id'] == 'A1'))
# 场景切换时间（按字幕所属段落）
sc = []
for s in osubs:
    if not sc or sc[-1]['scene'] != s['scene']:
        sc.append(dict(scene=s['scene'], t0=s['t0']))
for a, b in zip(sc, sc[1:]): a['t1'] = b['t0']
sc[-1]['t1'] = T_QEND
tl['qa']['scenes'] = sc
# 投资启示
T_INS = round(T_QEND + 1.4, 3)
vo, subs, words, t = lay_vo(INSIGHT, T_INS + 3.6)
tl['insight'] = dict(t_card=T_INS, vo=vo, subs=subs, words=words, t0=round(T_INS + 3.6, 3), t1=round(vo[-1]['t1'], 3))
# 一句话总结 + 片尾
T_SUM = round(vo[-1]['t1'] + 1.6, 3)
vo, subs, words, t = lay_vo([SUMMARY], T_SUM + 0.9)
tl['summary'] = dict(t0=T_SUM, vo=vo, subs=subs, words=words)
T_BRAND = round(T_SUM + (LENTO_HIT_BRAND - LENTO_HIT_SUM), 3)
tl['end'] = dict(t_particles=round(T_BRAND - 3.9, 3), t_logo=round(T_BRAND - 1.1, 3), t_brand=T_BRAND,
                 t_shine=round(T_BRAND + 1.6, 3), t_fade0=round(T_BRAND + 6.2, 3), t_fade1=round(T_BRAND + 8.2, 3))
DUR = round(T_BRAND + 8.4, 3)
tl['dur'] = DUR
tl['nframes'] = int(round(DUR * FPS))
# 音乐（曲目内时间 → 片内时间）
tl['music'] = [
    dict(track='Impact Lento', src_in=LENTO_HIT_A - 0.25, t0=T_TITLE - 0.25, t1=T_CTX + 0.6, fade_in=0.05, fade_out=2.6),
    dict(track='Lost Time', src_in=LOST_HIT - 0.15, t0=T_INS - 0.15, t1=T_SUM - 0.6, fade_in=0.05, fade_out=3.0),
    dict(track='Impact Lento', src_in=LENTO_HIT_SUM - 6.0, t0=T_SUM - 6.0, t1=DUR, fade_in=4.0, fade_out=2.2),
]
tl['music_hits'] = dict(title=T_TITLE, insight=T_INS, summary=T_SUM, brand=T_BRAND)
# 转场音效（全部 200Hz 以下）
tl['sfx'] = [
    dict(kind='swell', t=T_TITLE - 1.7, dur=1.7, gain=-12),
    dict(kind='impact', t=T_TITLE, gain=-8),
    dict(kind='swell', t=T_CTX - 1.8, dur=1.8, gain=-13),
    dict(kind='subdrop', t=T_CTX, gain=-10),
    dict(kind='swell', t=T_INS - 1.6, dur=1.6, gain=-13),
    dict(kind='impact', t=T_INS, gain=-9),
    dict(kind='subdrop', t=T_SUM, gain=-12),
    dict(kind='impact', t=T_BRAND, gain=-9),
]
tl['sections'] = [
    dict(name='冷开场（原声）', t0=0, t1=T_TITLE),
    dict(name='片名', t0=T_TITLE, t1=T_S1),
    dict(name='系列片头口播', t0=T_S1, t1=tl['intro']['t1']),
    dict(name='回到 1994', t0=T_CTX, t1=T_Q),
    dict(name='原始问答（1994 下午场原声）', t0=T_Q, t1=T_QEND),
    dict(name='投资启示（AI 解读）', t0=T_INS, t1=tl['insight']['t1']),
    dict(name='一句话总结', t0=T_SUM, t1=tl['end']['t_particles']),
    dict(name='品牌片尾', t0=tl['end']['t_particles'], t1=DUR),
]
json.dump(tl, open(os.path.join(work, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
for s in tl['sections']:
    print(f"{s['t0']:7.2f}–{s['t1']:7.2f}  {s['name']}")
print('总时长', DUR, '秒 =', f'{int(DUR // 60)}:{DUR % 60:04.1f}', ' 投资启示口播', round(tl['insight']['t1'] - tl['insight']['t0'], 1), '秒')
