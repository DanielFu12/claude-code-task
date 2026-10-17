"""整片时间线：把口播、原声、字幕、场景、音乐和音效排到同一条以秒为单位的时间轴上。

用法：python3 src/timeline.py WORK
输入：WORK/vo_index.json、WORK/vo/*.wav、WORK/orig_subs.json、WORK/orig16.wav
输出：WORK/timeline.json（render.py / audio.py / docs.py 共用）
"""
import difflib, json, os, sys
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import INTRO, INSIGHT, SUMMARY, COLD_IDS, LAUGH_AFTER, QA_SEGMENTS, QA_OMITTED

work = sys.argv[1]
VO = json.load(open(os.path.join(work, 'vo_index.json')))
ORIG = json.load(open(os.path.join(work, 'orig_subs.json')))
OD = {s['id']: s for s in ORIG}
FPS = 30
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# ------------------------------------------------------------------ 原声能量（找剪点：句间静音处）
_o, _osr = sf.read(os.path.join(work, 'orig16.wav'))
_f = _osr // 100
OLEV = 20 * np.log10(np.sqrt((_o[:len(_o) // _f * _f].reshape(-1, _f) ** 2).mean(1)) + 1e-9)   # 10ms 帧


def quiet(t, lo, hi):
    """t 附近 [t+lo, t+hi] 内能量最低的 30ms 中心（秒，相对 CLIP_IN）"""
    a, b = int((t + lo) * 100), int((t + hi) * 100)
    seg = np.convolve(OLEV[a:b], np.ones(3) / 3, 'same')
    return (a + int(np.argmin(seg))) / 100


# ------------------------------------------------------------------ 配乐与重拍（曲内秒数；能量突变 + 起音分析见 README）
H_TRACK, H_HIT = 'Hiding Your Reality', 9.012          # 暗色铺底 → 打击乐整体进入：片名
N_TRACK = 'Nerves'
N_ENTRY, N_DROP, N_SURGE, N_BREAK, N_CLIMAX = 28.48, 46.27, 62.25, 99.64, 108.26
N_BRAND_AFTER = 9.8                                    # 高潮重拍之后约 5.7 小节的强拍 →「巴芒价值」
BEATS = {k: np.load(os.path.join(DATA, f'beats_{k.replace(" ", "_")}.npy')) for k in (H_TRACK, N_TRACK)}


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
    v = VO[sid]
    say = v['say']; disp = v['text']
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
    return sum(0.55 if ord(c) < 128 else 1.0 for c in content(s))


def chunks(text, maxw=16.5, short=3.6):
    """按全角标点断句；过长的在自然断点切开；很短的片段并入相邻句。返回 [(显示文本, 首字序号, 末字序号)]"""
    parts, cur, book = [], '', False
    text = text.replace('——', '，')
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
            cand = [(i, 0) for i, c in enumerate(q) if c in '、—' and 2 < i < n - 2]
            cand += [(i, 1) for i, c in enumerate(q) if c in '《只就也却' and 2 < i < n - 2]
            cand += [(i + 1, 2) for i, c in enumerate(q) if c in '的和与在是了' and 2 < i < n - 3]
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


def lay_vo(items, t, anchors=None, beats=None):
    """排口播（与第一集相同）：段内停顿保留 Gemini 的节奏；段落之间的停顿可伸缩，
    锚点句在指定的重拍上开口，其余段落开口吸附到最近的节拍。"""
    anchors = anchors or {}
    ids = [it[0] for it in items]
    dur = {sid: (lambda ab: ab[1] - ab[0])(voiced(sid)) for sid in ids}
    gap = [VO[sid].get('gap', items[k][3]) if VO[sid].get('gap') is not None else items[k][3] for k, sid in enumerate(ids[:-1])]
    flex = [VO[sid].get('gap') is None for sid in ids[:-1]]
    LEAD = 0.04

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
        print(f'  锚点 {sid}: 调整 {delta:+.2f}s（分摊到 {len(fj)} 个段落停顿）')
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
            if na == len(ids):
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
# ------------------------------------------------------------------ 冷开场：巴芒原声里最有冲击力的一句
T_COLD = 0.9
c0 = quiet(OD[COLD_IDS[0]]['t0'], -0.6, -0.05); c1 = quiet(OD[COLD_IDS[-1]]['t1'], 0.0, 0.5)
tl['cold'] = dict(t0=T_COLD, t1=round(T_COLD + c1 - c0, 3), src_in=c0, src_out=c1)
tl['cold_subs'] = [dict(id=s['id'], en=s['en'], zh=s['zh'], t0=round(T_COLD + s['t0'] - c0 - 0.05, 3),
                        t1=round(T_COLD + s['t1'] - c0 + 0.25, 3)) for s in ORIG if s['id'] in COLD_IDS]
# ------------------------------------------------------------------ 片名：Hiding Your Reality 的整体进入（9.01s）
T_TITLE = round(tl['cold']['t1'] + 1.35, 3)
tl['t_title'] = T_TITLE
H_OFF = T_TITLE - H_HIT
h_beats = BEATS[H_TRACK] + H_OFF
vo, subs, words, t_end = lay_vo(INTRO, T_TITLE + 2.9, beats=h_beats)
tl['intro'] = dict(vo=vo, subs=subs, words=words, t0=vo[0]['t0'], t1=round(t_end, 3))
bars = h_beats[np.argmin(np.abs(h_beats - T_TITLE))::4]
T_CTX = round(float(bars[bars > t_end + 0.9][0]), 3)
T_Q = round(T_CTX + 3.8, 3)
tl['ctx'] = dict(t0=T_CTX, t1=round(T_Q + 1.2, 3))

# ------------------------------------------------------------------ 原始问答：四段节选，剪点都在句间静音处
GAP = 0.55                                               # 每处省略之间留 0.55 秒（画面上一道扫过的细光）
segs, t = [], T_Q
ids = [s['id'] for s in ORIG]
for a_id, b_id in QA_SEGMENTS:
    s_in = quiet(OD[a_id]['t0'], -0.7, -0.05)
    s_out = quiet(OD[b_id]['t1'], 0.02, 0.55)
    if b_id == LAUGH_AFTER:                              # 芒格之后保留现场笑声，直到档案录像里的硬切（数字静音）之前
        k0 = int(OD[b_id]['t1'] * 100)
        dead = np.where(OLEV[k0:] < -85)[0]
        s_out = (k0 + int(dead[0])) / 100 - 0.03 if len(dead) else OD[b_id]['t1'] + 1.5
    segs.append(dict(src_in=round(s_in, 3), src_out=round(s_out, 3), t0=round(t, 3), t1=round(t + s_out - s_in, 3), ids=[a_id, b_id]))
    t += s_out - s_in + GAP
T_QEND = round(segs[-1]['t1'], 3)
osubs = []
for sg in segs:
    i0, i1 = ids.index(sg['ids'][0]), ids.index(sg['ids'][1])
    for s in ORIG[i0:i1 + 1]:
        if s['scene'] == 'omit': continue
        osubs.append(dict(id=s['id'], scene=s['scene'], en=s['en'], zh=s['zh'],
                          t0=round(max(sg['t0'], sg['t0'] + s['t0'] - sg['src_in'] - 0.08), 3),
                          t1=round(min(sg['t1'] - 0.05, sg['t0'] + s['t1'] - sg['src_in'] + 0.25), 3)))
for s0, s1 in zip(osubs, osubs[1:]):
    if s0['t1'] > s1['t0'] - 0.02: s0['t1'] = s1['t0'] - 0.02
    if s1['t0'] - s0['t1'] < 0.6 and s1['t0'] - s0['t1'] > 0: s0['t1'] = s1['t0'] - 0.02
laugh = next(s for s in osubs if s['id'] == LAUGH_AFTER)
tl['laugh'] = dict(t0=round(laugh['t1'] - 0.3, 3), t1=round(T_QEND - 0.2, 3))
tl['qa'] = dict(t0=T_Q, t1=T_QEND, segs=segs, subs=osubs, cuts=[round(s['t1'] + GAP / 2, 3) for s in segs[:-1]],
                answer_t=next(s['t0'] for s in osubs if s['id'] == 'A1'), munger_t=next(s['t0'] for s in osubs if s['id'] == 'M1'),
                omitted=QA_OMITTED)
sc = []
for s in osubs:
    if not sc or sc[-1]['scene'] != s['scene']:
        sc.append(dict(scene=s['scene'], t0=s['t0']))
for a, b in zip(sc, sc[1:]): a['t1'] = b['t0']
sc[-1]['t1'] = T_QEND
tl['qa']['scenes'] = sc

# ------------------------------------------------------------------ 投资启示（Nerves：结构与论证同步）
T_INS = round(T_QEND + 1.3, 3)
vo0, *_ = lay_vo(INSIGHT, T_INS + 2.6)
n4 = next(v['t0'] for v in vo0 if v['id'] == 'I4')
N_OFF = n4 - N_ENTRY                                     # 正例（华盛顿邮报）开口 = 配乐大段落进入
if N_OFF < T_INS - 0.5:                                  # 曲子不能早于启示卡开始：往后推整段口播
    shift = T_INS - 0.5 - N_OFF
    vo0, *_ = lay_vo(INSIGHT, T_INS + 2.6 + shift); n4 = next(v['t0'] for v in vo0 if v['id'] == 'I4'); N_OFF = n4 - N_ENTRY
n_beats = BEATS[N_TRACK] + N_OFF
T_SUM = round(N_CLIMAX + N_OFF, 3)
vo, subs, words, t_end = lay_vo(INSIGHT, vo0[0]['t0'], anchors={'I4': n4}, beats=n_beats)
if t_end > T_SUM - 0.6:
    print(f'  ⚠ 启示口播结束 {t_end:.2f} 晚于总结重拍 {T_SUM:.2f}：压缩段落停顿')
    vo, subs, words, t_end = lay_vo(INSIGHT, vo0[0]['t0'], anchors={'I4': n4, 'I13': T_SUM - 0.8 - (vo0[-1]['t1'] - vo0[-1]['t0'])})
tl['insight'] = dict(t_card=T_INS, vo=vo, subs=subs, words=words, t0=vo[0]['t0'], t1=round(t_end, 3))
vo, subs, words, t = lay_vo([SUMMARY], T_SUM + 0.75)
tl['summary'] = dict(t0=T_SUM, vo=vo, subs=subs, words=words)
eb = n_beats[np.argmin(np.abs(n_beats - T_SUM))::4]
T_BRAND = round(float(eb[eb > T_SUM + N_BRAND_AFTER - 0.6][0]), 3)
tl['end'] = dict(t_particles=round(T_BRAND - 3.9, 3), t_logo=round(T_BRAND - 1.1, 3), t_brand=T_BRAND,
                 t_shine=round(T_BRAND + 1.6, 3), t_follow=round(T_BRAND + 1.3, 3),
                 t_fade0=round(T_BRAND + 7.0, 3), t_fade1=round(T_BRAND + 9.0, 3))
DUR = round(T_BRAND + 9.2, 3)
tl['dur'] = DUR
tl['nframes'] = int(round(DUR * FPS))
tl['nerves'] = dict(off=round(N_OFF, 3), entry=round(N_ENTRY + N_OFF, 3), drop=round(N_DROP + N_OFF, 3),
                    surge=round(N_SURGE + N_OFF, 3), brk=round(N_BREAK + N_OFF, 3), climax=T_SUM)

# ------------------------------------------------------------------ 音乐（曲目内时间 → 片内时间）
tl['music'] = [
    # 暗色铺底从冷开场中段淡入（人声期间被侧链压低），在片名处整体进入
    dict(track=H_TRACK, src_in=round(2.0 - H_OFF, 3), t0=2.0, t1=round(T_CTX + 0.6, 3), fade_in=2.4, fade_out=1.8, level=-19.0),
    dict(track=N_TRACK, src_in=round(max(0.0, T_INS - 0.6 - N_OFF), 3), t0=round(max(T_INS - 0.6, N_OFF), 3), t1=DUR,
         fade_in=1.0, fade_out=2.6, level=-18.0),
]
# Nerves 的留白段（收尾句之后、高潮之前）整体抬高 6dB，避免出现“断档”
tl['music_boost'] = [dict(t0=round(tl['insight']['t1'] + 0.2, 3), t1=round(T_SUM - 0.05, 3), db=6.0)]
# 画面卡点：强重拍（推镜 + 闪光 + 色散）与小节强拍（轻微脉动）
hits = [(T_TITLE, 1.0), (T_CTX, 0.7), (T_INS, 0.8), (round(N_ENTRY + N_OFF, 3), 1.0), (round(N_SURGE + N_OFF, 3), 0.8),
        (T_SUM, 1.0), (T_BRAND, 1.0)]
for part in ('intro', 'insight'):
    prev = None
    for v in tl[part]['vo']:
        if prev and v['scene'] != prev: hits.append((v['t0'] - 0.04, 0.45))
        prev = v['scene']
tl['hits'] = sorted(set((round(a, 3), b) for a, b in hits))
tl['beats'] = [round(float(b), 3) for b in np.r_[h_beats[(h_beats > T_TITLE) & (h_beats < T_CTX)],
                                                  n_beats[(n_beats > T_INS) & (n_beats < DUR - 2)]]]
# 转场音效（全部 200Hz 以下）：只在结构转折处
tl['sfx'] = [
    dict(kind='swell', t=round(T_TITLE - 1.8, 3), dur=1.8, gain=-13),
    dict(kind='impact', t=T_TITLE, gain=-9),
    dict(kind='swell', t=round(T_CTX - 1.5, 3), dur=1.5, gain=-14),
    dict(kind='subdrop', t=T_CTX, gain=-10),
    dict(kind='impact', t=T_INS, gain=-11),
    dict(kind='impact', t=round(N_ENTRY + N_OFF, 3), gain=-12),
    dict(kind='subdrop', t=round(next(v['t0'] for v in tl['insight']['vo'] if v['id'] == 'I9') + 0.05, 3), gain=-11),
    dict(kind='swell', t=round(T_SUM - 4.2, 3), dur=4.2, gain=-11),            # 留白里的低频蓄力，推向高潮重拍
    dict(kind='subdrop', t=T_SUM, gain=-10),
    dict(kind='impact', t=T_BRAND, gain=-9),
]
tl['sections'] = [
    dict(name='冷开场（原声）', t0=0, t1=T_TITLE),
    dict(name='片名 + 开场口播', t0=T_TITLE, t1=tl['intro']['t1']),
    dict(name='回到 1994', t0=T_CTX, t1=T_Q),
    dict(name='原始问答（1994 上午场原始录像·节选）', t0=T_Q, t1=T_QEND),
    dict(name='投资启示（解读）', t0=T_INS, t1=tl['insight']['t1']),
    dict(name='一句话总结', t0=T_SUM, t1=tl['end']['t_particles']),
    dict(name='品牌片尾', t0=tl['end']['t_particles'], t1=DUR),
]
json.dump(tl, open(os.path.join(work, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
for s in tl['sections']:
    print(f"{s['t0']:7.2f}–{s['t1']:7.2f}  {s['name']}")
for sg in segs:
    print(f"  原声段 {sg['ids'][0]}–{sg['ids'][1]}: 源 {sg['src_in']:.2f}–{sg['src_out']:.2f} → 片内 {sg['t0']:.2f}–{sg['t1']:.2f}")
print('Nerves 偏移', round(N_OFF, 2), ' 启示口播', round(tl['insight']['t0'], 2), '–', round(tl['insight']['t1'], 2), ' 总结', T_SUM, ' 品牌', T_BRAND)
for v in tl['insight']['vo']:
    print(f"   {v['id']:4s} {v['t0']:7.2f}  (Nerves {v['t0'] - N_OFF:6.2f})  {v['text'][:24]}")
print('总时长', DUR, '秒 =', f'{int(DUR // 60)}:{DUR % 60:04.1f}', ' 开场口播', round(tl['intro']['t1'] - tl['intro']['t0'], 1),
      '秒  原声', round(sum(s['t1'] - s['t0'] for s in segs), 1), '秒  投资启示口播', round(tl['insight']['t1'] - tl['insight']['t0'], 1), '秒')
