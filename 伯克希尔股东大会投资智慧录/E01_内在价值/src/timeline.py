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
# 原始问答（节选）：61.55（"Could you perhaps…" 之前的静音，-47dB）→ 222.40（"…with large businesses, basically." 之后的停顿，-65dB）
# 省略：提问者自我介绍与铺垫（约 22 秒）；回答结尾关于“粉饰会计数字”的补充（约 33 秒）。核心问题与完整论证不剪。
Q_IN, Q_OUT = 61.55, 222.40
FPS = 30
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# ------------------------------------------------------------------ 配乐与重拍（曲内秒数；能量突变 + 节拍分析见 README）
U_TRACK, U_HIT_TITLE = 'Undaunted', 10.1           # 大鼓进入 → 片名
E_TRACK = 'The Escalation'
E_HIT_CARD, E_HIT_SEES, E_HIT_SUM = 155.6, 201.2, 277.1   # 渐强起点 → 投资启示；大段落进入 → “看得清”；高潮 → 总结句
E_BRAND_AFTER = 9.8                                  # 总结重拍之后 5 小节（同一高潮段内的强拍）→「巴芒价值」
BEATS = {k: np.load(os.path.join(DATA, f'beats_{k.replace(" ", "_")}.npy')) for k in (U_TRACK, E_TRACK)}


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
    text = text.replace('——', '，')                    # 破折号处也断句（字幕里不显示破折号）
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


def lay_vo(items, t, anchors=None, beats=None, max_extra=3.0):
    """排口播。段内句间停顿保留 Gemini 的原始节奏；段落之间的停顿可伸缩：
    1) anchors {句子 id: 片内时刻}：该句在这个音乐重拍上开口，差额分摊到前一锚点之后的段落停顿里；
    2) beats（片内节拍时刻）：其余段落的开口吸附到最近的节拍（-0.15～+0.3 秒），
       用同一锚点区间内下一个可伸缩停顿抵消，锚点位置不变。"""
    anchors = anchors or {}
    ids = [it[0] for it in items]
    dur = {sid: (lambda ab: ab[1] - ab[0])(voiced(sid)) for sid in ids}
    gap = [VO[sid].get('gap', items[k][3]) for k, sid in enumerate(ids[:-1])]
    flex = [VO[sid].get('gap') is None for sid in ids[:-1]]
    LEAD = 0.04                                         # 人声在拍点后 40ms 开口

    def pos(k):
        return t + sum(dur[ids[j]] + gap[j] for j in range(k))

    seg0 = 0
    for k, sid in enumerate(ids):
        if sid not in anchors or k == 0: continue
        delta = anchors[sid] + LEAD - pos(k)
        fj = [j for j in range(seg0, k) if flex[j]]
        if fj:
            if delta >= 0:
                for j in fj: gap[j] += delta / len(fj)
            else:
                room = sum(max(gap[j] - 0.25, 0) for j in fj)
                take = min(-delta, room)
                for j in fj: gap[j] -= max(gap[j] - 0.25, 0) / max(room, 1e-9) * take
        print(f'  锚点 {sid}: 调整 {delta:+.2f}s（分摊到 {len(fj)} 个段落停顿）' + ('' if fj and max(gap[j] for j in fj) < max_extra + 1 else ' ⚠'))
        seg0 = k
    if beats is not None:
        akeys = [k for k, sid in enumerate(ids) if sid in anchors] + [len(ids)]
        for k in range(1, len(ids)):
            if not flex[k - 1] or ids[k] in anchors: continue
            p0 = pos(k)
            near = beats[(beats > p0 - LEAD - 0.15) & (beats < p0 - LEAD + 0.3)]
            if not len(near): continue
            d = float(near[0]) + LEAD - p0
            na = min(a for a in akeys if a > k)
            if gap[k - 1] + d < 0.15: continue
            if na == len(ids):                         # 之后没有锚点：直接顺延
                gap[k - 1] += d; continue
            nxt = next((j for j in range(k, min(na, len(ids) - 1)) if flex[j]), None)
            if nxt is None or gap[nxt] - d < 0.2: continue
            gap[k - 1] += d; gap[nxt] -= d
    vo, subs, words = [], [], []
    for k, (sid, scene, text, pause) in enumerate(items):
        t0 = pos(k)
        a, b = voiced(sid)
        ct = char_times(sid, a)
        vo.append(dict(id=sid, scene=scene, t0=round(t0, 3), t1=round(t0 + dur[sid], 3), src_in=round(a, 3), text=text))
        for txt, i0, i1 in chunks(text):
            subs.append(dict(id=sid, text=txt, t0=round(t0 + ct[i0][0] - 0.12, 3), t1=round(t0 + ct[i1][1] + 0.1, 3)))
        for w0, w1, wt in VO[sid]['words']:
            words.append(dict(id=sid, w=wt, t=round(t0 + w0 - a, 3)))
    for s0, s1 in zip(subs, subs[1:]):
        if s1['t0'] - s0['t1'] < 0.35: s0['t1'] = s1['t0'] - 0.02
    return vo, subs, words, pos(len(ids) - 1) + dur[ids[-1]]


tl = dict(fps=FPS)
# ------------------------------------------------------------------ 冷开场
tl['cold'] = dict(t0=T_COLD, t1=T_COLD + COLD_OUT - COLD_IN, src_in=COLD_IN, src_out=COLD_OUT)
tl['cold_subs'] = [dict(id=s['id'], en=s['en'], zh=s['zh'], t0=round(T_COLD + s['t0'] - COLD_IN, 3),
                        t1=round(T_COLD + s['t1'] - COLD_IN + 0.2, 3)) for s in ORIG if s['id'] in COLD_IDS]
for s0, s1 in zip(tl['cold_subs'], tl['cold_subs'][1:]):
    s0['t1'] = min(s0['t1'], s1['t0'] - 0.02)
tl['t_title'] = T_TITLE
# ------------------------------------------------------------------ 系列片头（Undaunted：片名对准大鼓进入）
U_OFF = T_TITLE - U_HIT_TITLE                          # 片内时刻 = 曲内时刻 + U_OFF
u_beats = BEATS[U_TRACK] + U_OFF
vo, subs, words, t_end = lay_vo(INTRO, T_TITLE + 1.3, beats=u_beats)
tl['intro'] = dict(vo=vo, subs=subs, words=words, t0=vo[0]['t0'], t1=round(t_end, 3))
# 进入 1994：背景卡落在问题读完后的第 3 拍之后的小节强拍上
bars = u_beats[np.argmin(np.abs(u_beats - T_TITLE))::4]
T_CTX = round(float(bars[bars > t_end + 1.0][0]), 3)
T_Q = T_CTX + 3.6
T_QEND = T_Q + (Q_OUT - Q_IN)
tl['ctx'] = dict(t0=T_CTX, t1=T_Q + 1.4)
osubs = []
for s in ORIG:
    if s['t0'] < Q_IN - 0.05 or s['t1'] > Q_OUT + 0.3: continue      # 只保留节选范围内的字幕
    osubs.append(dict(id=s['id'], scene=s['scene'], en=s['en'], zh=s['zh'],
                      t0=round(T_Q + s['t0'] - Q_IN - 0.08, 3), t1=round(T_Q + s['t1'] - Q_IN + 0.25, 3)))
for s0, s1 in zip(osubs, osubs[1:]):
    if s0['t1'] > s1['t0'] - 0.02: s0['t1'] = s1['t0'] - 0.02
    if s1['t0'] - s0['t1'] < 0.6: s0['t1'] = s1['t0'] - 0.02
osubs[-1]['t1'] = min(osubs[-1]['t1'], T_QEND - 0.1)
laugh = next(s for s in osubs if s['id'] == LAUGH_AFTER)
nxt = osubs[osubs.index(laugh) + 1]
tl['laugh'] = dict(t0=round(laugh['t1'], 3), t1=round(nxt['t0'] - 0.05, 3))
tl['qa'] = dict(t0=round(T_Q, 3), t1=round(T_QEND, 3), src_in=round(Q_IN, 3), src_out=round(Q_OUT, 3),
                subs=osubs, answer_t=next(s['t0'] for s in osubs if s['id'] == 'A1'),
                omitted=['提问者自我介绍与铺垫（Zone 2 / Sean Barry / 年报与会计准则的铺垫，约 22 秒）',
                         '回答结尾关于“会计数字与粉饰数字”的补充（约 33 秒）'])
sc = []
for s in osubs:
    if not sc or sc[-1]['scene'] != s['scene']:
        sc.append(dict(scene=s['scene'], t0=s['t0']))
for a, b in zip(sc, sc[1:]): a['t1'] = b['t0']
sc[-1]['t1'] = T_QEND
tl['qa']['scenes'] = sc
# ------------------------------------------------------------------ 投资启示（The Escalation：结构与论证同步）
T_INS = round(T_QEND + 1.2, 3)
# 先按自然节奏排一遍，找到“看得清”开口的时刻，再让配乐的大段落进入（201.2s）正好落在这里——不为卡点额外加停顿
vo0, *_ = lay_vo(INSIGHT, T_INS + 3.4)
n7 = next(v['t0'] for v in vo0 if v['id'] == 'I7')
E_OFF = n7 - E_HIT_SEES
e_beats = BEATS[E_TRACK] + E_OFF
anchors = {'I7': n7}
vo, subs, words, t_end = lay_vo(INSIGHT, T_INS + 3.4, anchors=anchors, beats=e_beats)
tl['insight'] = dict(t_card=T_INS, vo=vo, subs=subs, words=words, t0=vo[0]['t0'], t1=round(t_end, 3))
# 一句话总结：落在高潮重拍上（若口播比预期长，就落在其后最近的小节强拍）
T_SUM = E_HIT_SUM + E_OFF
if T_SUM < t_end + 1.0:
    eb = e_beats[np.argmin(np.abs(e_beats - T_SUM))::4]
    T_SUM = float(eb[eb > t_end + 1.0][0])
T_SUM = round(T_SUM, 3)
vo, subs, words, t = lay_vo([SUMMARY], T_SUM + 0.7)
tl['summary'] = dict(t0=T_SUM, vo=vo, subs=subs, words=words)
eb = e_beats[np.argmin(np.abs(e_beats - T_SUM))::4]
T_BRAND = round(float(eb[eb > T_SUM + E_BRAND_AFTER - 0.6][0]), 3)
tl['end'] = dict(t_particles=round(T_BRAND - 3.9, 3), t_logo=round(T_BRAND - 1.1, 3), t_brand=T_BRAND,
                 t_shine=round(T_BRAND + 1.6, 3), t_follow=round(T_BRAND + 1.3, 3),
                 t_fade0=round(T_BRAND + 7.0, 3), t_fade1=round(T_BRAND + 9.0, 3))
DUR = round(T_BRAND + 9.2, 3)
tl['dur'] = DUR
tl['nframes'] = int(round(DUR * FPS))
# ------------------------------------------------------------------ 音乐（曲目内时间 → 片内时间）
tl['music'] = [
    dict(track=U_TRACK, src_in=-U_OFF, t0=0.0, t1=T_CTX + 0.5, fade_in=1.5, fade_out=1.8, level=-19.0),
    dict(track=E_TRACK, src_in=T_INS - 1.0 - E_OFF, t0=T_INS - 1.0, t1=DUR, fade_in=0.8, fade_out=2.6, level=-18.0),
]
# 画面卡点：强重拍（推镜 + 闪光 + 色散）与节拍（轻微脉动）
hits = [(T_TITLE, 1.0), (T_CTX, 0.8), (T_INS, 1.0), (tl['insight']['vo'][[v['id'] for v in tl['insight']['vo']].index('I7')]['t0'] - 0.04, 1.0),
        (T_SUM, 1.0), (T_BRAND, 1.0)]
for part in ('intro', 'insight'):
    prev = None
    for v in tl[part]['vo']:
        if prev and v['scene'] != prev: hits.append((v['t0'] - 0.04, 0.5))
        prev = v['scene']
tl['hits'] = sorted(set((round(a, 3), b) for a, b in hits))
tl['beats'] = [round(float(b), 3) for b in np.r_[u_beats[(u_beats > T_TITLE) & (u_beats < T_CTX)],
                                                  e_beats[(e_beats > T_INS) & (e_beats < DUR - 2)]]]
# 转场音效（全部 200Hz 以下）：只在结构转折处
tl['sfx'] = [
    dict(kind='swell', t=T_TITLE - 1.7, dur=1.7, gain=-13),
    dict(kind='impact', t=T_TITLE, gain=-9),
    dict(kind='swell', t=T_CTX - 1.6, dur=1.6, gain=-13),
    dict(kind='subdrop', t=T_CTX, gain=-9),
    dict(kind='impact', t=T_INS, gain=-10),
    dict(kind='impact', t=n7, gain=-11),
    dict(kind='subdrop', t=T_SUM, gain=-10),
    dict(kind='impact', t=T_BRAND, gain=-9),
]
tl['sections'] = [
    dict(name='冷开场（原声）', t0=0, t1=T_TITLE),
    dict(name='片名 + 系列介绍', t0=T_TITLE, t1=tl['intro']['t1']),
    dict(name='回到 1994', t0=T_CTX, t1=T_Q),
    dict(name='原始问答（1994 下午场原声·节选）', t0=T_Q, t1=T_QEND),
    dict(name='投资启示（解读）', t0=T_INS, t1=tl['insight']['t1']),
    dict(name='一句话总结', t0=T_SUM, t1=tl['end']['t_particles']),
    dict(name='品牌片尾', t0=tl['end']['t_particles'], t1=DUR),
]
json.dump(tl, open(os.path.join(work, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
for s in tl['sections']:
    print(f"{s['t0']:7.2f}–{s['t1']:7.2f}  {s['name']}")
print('总时长', DUR, '秒 =', f'{int(DUR // 60)}:{DUR % 60:04.1f}', ' 系列介绍口播', round(tl['intro']['t1'] - tl['intro']['t0'], 1),
      '秒  投资启示口播', round(tl['insight']['t1'] - tl['insight']['t0'], 1), '秒')
