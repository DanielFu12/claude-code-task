"""把旁白排到 80BPM 节拍网格上 -> work/timeline.json + work/voice.wav
规则：
- 台词默认起于半拍；章节起于整拍。
- 带「揭晓点」的台词（数字落地、锤子落下……），反推起点，让揭晓点正好落在整拍上。
- cues 记录所有揭晓点，配乐重击与画面落点共用。"""
import json, math, os, sys
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES
W = sys.argv[1] if len(sys.argv) > 1 else 'work'
BPM = 80; BEAT = 60 / BPM; BAR = 4 * BEAT; SR = 48000
up = lambda t, q: math.ceil(t / q - 1e-6) * q


def pauses(y):
    """句内停顿 [(起, 止)]（相对句首，秒）"""
    hop = 480; n = len(y) // hop
    r = np.sqrt(np.mean(y[:n * hop].reshape(n, hop) ** 2, 1) + 1e-12)
    db = 20 * np.log10(r / r.max()); sil = db < -32
    out, k = [], 0
    while k < n:
        if sil[k]:
            j = k
            while j < n and sil[j]: j += 1
            if j - k >= 7 and k > 5 and j < n - 5: out.append((k * hop / SR, j * hop / SR))
            k = j
        else: k += 1
    return [(round(a, 3), round(b, 3)) for a, b in out]


def fine_pauses(y, db_thr=-24, min_len=0.15):
    """更细的词间隙（用于逐词卡点）"""
    hop = 240; n = len(y) // hop
    r = np.sqrt(np.mean(y[:n * hop].reshape(n, hop) ** 2, 1) + 1e-12)
    sil = 20 * np.log10(r / r.max()) < db_thr; out, k = [], 0
    while k < n:
        if sil[k]:
            j = k
            while j < n and sil[j]: j += 1
            if (j - k) * hop / SR >= min_len and k > 3: out.append((k * hop / SR, j * hop / SR))
            k = j
        else: k += 1
    return out


def chunks(sub, ps, t0, d):
    """字幕按 | 分段，分段点吸附到最近的停顿"""
    parts = sub.split('|')
    if len(parts) == 1: return [(sub, round(t0, 3), round(t0 + d, 3))]
    tot = sum(len(p) for p in parts); acc = 0; bounds = []
    for p in parts[:-1]:
        acc += len(p); est = d * acc / tot
        cand = [(abs((a + b) / 2 - est), b) for a, b in ps if b not in bounds]
        bounds.append(min(cand)[1] if cand and min(cand)[0] < 1.2 else est)
    bounds = sorted(bounds); ts = [0] + bounds + [d]
    return [(p, round(t0 + ts[k], 3), round(t0 + ts[k + 1], 3)) for k, p in enumerate(parts)]


# 章节：(名字, 起始台词, 起点前额外留白拍数)
SECTIONS = [('hook', 'H1', 0), ('cases', 'T1', 0), ('pivot', 'Q1', 1), ('hammer', 'M1', 0), ('strikes', 'M3', 0),
            ('ask', 'M6', 0), ('two', 'M7', 0), ('tx', 'K1', 1), ('ali', 'K4', 1), ('zp', 'K5', 1), ('nv', 'K6', 1),
            ('cure', 'V1', 1), ('report', 'V2', 0), ('ring', 'V3', 0), ('finale', 'E1', 1), ('outro', 'E2', 1)]
SEC_START = {s[1]: (s[0], s[2]) for s in SECTIONS}
TITLE_BEATS = 6                 # 「伪价值投资」标题卡

# 揭晓点：台词 -> 相对句首的偏移规则
def reveal_off(i, ps, d):
    after = lambda k: ps[k][1] if len(ps) > k else None
    last = lambda: ps[-1][1] if ps else None
    knock = lambda: min(ps, key=lambda p: abs(p[1] - d * 0.62))[1] if ps else d * 0.6   # 「，敲一下」
    R = {'H1': lambda: after(len([p for p in ps if p[1] < d * 0.45]) - 1) if ps else d * 0.45,
         'T2': lambda: after(0), 'Z2': lambda: after(1) if len(ps) > 1 else after(0), 'A2': lambda: 1.05,
         'N3': lambda: d - 1.15, 'M3': knock, 'M4': knock, 'M5': knock}
    if i not in R: return None
    v = R[i]()
    return v if v is not None else None


lines, secs, cues = [], {}, {}
voice = np.zeros(int(260 * SR), np.float32)
t = BEAT * 1
for (i, text, sub, ctx, gap) in LINES:
    y, _ = sf.read(f'{W}/vo/{i}.wav', dtype='float32')
    d = len(y) / SR; ps = pauses(y)
    if i in SEC_START:
        name, pad = SEC_START[i]
        if name == 'hook': t = BEAT
        else:
            if name == 'hammer':            # 标题卡
                t = up(t, BEAT); secs['title'] = t; t += TITLE_BEATS * BEAT
            t = up(t + pad * BEAT, BEAT)
        secs[name] = t
    off = reveal_off(i, ps, d)
    if off is not None:                  # 让揭晓点落在整拍上
        t = up(t + off, BEAT) - off
        prev = {'M4': 'M3', 'M5': 'M4'}.get(i)
        if prev and t + off < cues[prev] + BAR - 1e-6:   # 三锤之间严格一小节
            t = cues[prev] + BAR - off
        cues[i] = round(t + off, 3)
    lines.append(dict(id=i, t0=round(t, 4), t1=round(t + d, 4), sub=sub, pauses=ps, chunks=chunks(sub, ps, t, d)))
    a = int(t * SR); voice[a:a + len(y)] += y
    t = up(t + d + gap, BEAT / 2)
secs['card'] = up(t + 3.0, BEAT)          # 结尾自查清单需要时间读完
T = secs['card'] + 7 * BEAT
voice = voice[:int(T * SR)]
sf.write(f'{W}/voice.wav', voice, SR, subtype='FLOAT')

LD = {l['id']: l for l in lines}
CH = lambda i, k: LD[i]['chunks'][k][1]
y_m2, _ = sf.read(f'{W}/vo/M2.wav', dtype='float32')
m2 = [b for a, b in fine_pauses(y_m2) if a > 0.8][:5]           # 好公司/好价格/护城河/现金流/回购 的开口
q0 = LD['Q1']['t0']
cues.update(
    q_items=[round(q0 + o, 3) for o in (0.0, 0.99, 2.12, 3.21)],  # 不追高/不碰垃圾股/熟读巴菲特/专门等回调（逐词测得）
    q_std=round(q0 + 4.79, 3),                           # 「每一步，都是标准答案」
    q_ask=round(q0 + 7.56, 3),                           # 「错在哪？」
    m2_words=[round(LD['M2']['t0'] + b, 3) for b in m2],
    m6_ask=CH('M6', 1),                                  # 「可你从没问过……看懂了吗？」
    m6_hit=round(LD['M6']['t1'] - 1.0, 3),               # 「看懂了吗」
    m7_two=CH('M7', 1),                                  # 「能力圈，和反过来想」
    k1_why=CH('K1', 1), k2_pe=CH('K2', 1), k3_punch=CH('K3', 1),
    k4_inv=CH('K4', 1), k4_rivals=CH('K4', 2), k4_buyback=CH('K4', 3),
    k5_mos=CH('K5', 1), k5_future=CH('K5', 2), k5_q=CH('K5', 3),
    k6_peak=CH('K6', 1), k6_26=round(LD['K6']['t1'] - 1.1, 3),
    tx_now=cues['T2'], ali_low=cues['A2'], zp_now=cues['Z2'], nv_now=cues['N3'], h1_turn=cues['H1'],
    ali_now=round(CH('A2', 1) + 1.25, 3),               # 「五年后的今天，|84」
    v2_q=CH('V2', 1), v2_no=CH('V2', 2), v3_out=CH('V3', 1), v3_idx=CH('V3', 2), e1_turn=CH('E1', 1),
)
json.dump(dict(cues=cues, bpm=BPM, beat=BEAT, bar=BAR, total=T, sections=secs, lines=lines),
          open(f'{W}/timeline.json', 'w'), ensure_ascii=False, indent=1)
for k, v in secs.items(): print(f'{k:8s} {v:7.2f}')
print('cues', {k: v for k, v in cues.items() if not isinstance(v, list)})
print('total', T)
