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
SECTIONS = [('hook', 'H1', 0), ('cases', 'T1', 0), ('ali', 'A1', 0), ('zp', 'Z1', 0), ('nv', 'N1', 0), ('pivot', 'Q1', 1),
            ('rewind', 'R0', 0), ('r1', 'R1a', 1), ('r2', 'R2a', 1), ('r3', 'R3a', 1), ('r4', 'R4a', 1), ('r5', 'R5a', 1),
            ('hammer', 'R5b', 0), ('strikes', 'S1', 0), ('clue', 'R5c', 0), ('tx', 'R5d', 1), ('inv', 'R5e', 1),
            ('wake', 'W1', 1), ('ibm', 'W2', 0), ('three', 'W3', 0), ('q1', 'W4', 0), ('q2', 'W5', 0), ('q3', 'W6', 0),
            ('mos', 'W7', 0), ('quote', 'E1', 1), ('outro', 'E2', 1)]
SEC_START = {s[1]: (s[0], s[2]) for s in SECTIONS}
BIG = {'cases', 'pivot', 'rewind', 'r1', 'r2', 'r3', 'r4', 'r5', 'strikes', 'wake', 'three', 'quote', 'outro'}
GAP_K = 0.55                    # 句间停顿压缩系数
TITLE_BEATS = 6                 # 「伪价值投资」标题卡（在 R0 之前）
TITLE_BEFORE = 'R0'

# 揭晓点：台词 -> 相对句首的偏移规则（让这一瞬间落在整拍上）
def reveal_off(i, ps, d):
    after = lambda k: ps[k][1] if len(ps) > k else None
    last = lambda: ps[-1][1] if ps else None
    near = lambda f: (min(ps, key=lambda p: abs(p[1] - d * f))[1] if ps else d * f)
    # 数字开口位置由逐词间隙实测（work/vo 缓存的配音）：「它收在|373」「如今，|84」「如今，|367」「却跌到|151」
    R = {'H1': lambda: near(0.48), 'T1': lambda: 6.75, 'A1': lambda: 5.87, 'Z1': lambda: 6.67, 'N1': lambda: 8.6,
         'S1': lambda: near(0.62), 'S2': lambda: near(0.62), 'S3': lambda: near(0.62)}
    return R[i]() if i in R else None


lines, secs, cues = [], {}, {}
voice = np.zeros(int(400 * SR), np.float32)
t = BEAT * 1
for (i, text, sub, ctx, gap) in LINES:
    y, _ = sf.read(f'{W}/vo/{i}.wav', dtype='float32')
    d = len(y) / SR; ps = pauses(y)
    if i in SEC_START:
        name, pad = SEC_START[i]
        if name == 'hook': t = BEAT
        else:
            if i == TITLE_BEFORE:           # 标题卡
                t = up(t, BEAT); secs['title'] = t; t += TITLE_BEATS * BEAT
            t = up(t + pad * BEAT, BEAT if name in BIG else BEAT / 2)
        secs[name] = t
    off = reveal_off(i, ps, d)
    if off is not None:                  # 让揭晓点落在整拍上
        t = up(t + off, BEAT) - off
        prev = {'S2': 'S1', 'S3': 'S2'}.get(i)
        if prev and t + off < cues[prev] + BAR - 1e-6:   # 三锤之间严格一小节
            t = cues[prev] + BAR - off
        cues[i] = round(t + off, 3)
    lines.append(dict(id=i, t0=round(t, 4), t1=round(t + d, 4), sub=sub, pauses=ps, chunks=chunks(sub, ps, t, d)))
    a = int(t * SR); voice[a:a + len(y)] += y
    t = up(t + d + gap * GAP_K, BEAT / 2)
secs['card'] = up(t + 1.5, BEAT)          # 结尾问句之后留一口气
T = secs['card'] + 6 * BEAT
voice = voice[:int(T * SR)]
sf.write(f'{W}/voice.wav', voice, SR, subtype='FLOAT')

LD = {l['id']: l for l in lines}
CH = lambda i, k: LD[i]['chunks'][k][1]
cues.update(
    r1_q=CH('R1b', 0), r1_anchor=CH('R1b', 1), r1_cash=CH('R1b', 2), r1_mos=CH('R1b', 3),
    r2_q=CH('R2b', 0), r2_bask=CH('R2b', 1), r2_drop=CH('R2b', 2),
    r3_q=CH('R3b', 0), r3_peak=CH('R3b', 1), r3_26=round(LD['R3b']['t1'] - 1.1, 3),
    r4_story=CH('R4a', 1), r4_think=CH('R4a', 2), r4_cars=CH('R4b', 1), r4_3=round(CH('R4b', 2) - 0.6, 3), r4_lesson=CH('R4b', 2),
    r5_think=CH('R5a', 1), r5_quote=CH('R5b', 0),
    tx_profit=CH('R5d', 1), tx_pe=CH('R5d', 2), tx_moat=CH('R5d', 3), tx_expect=CH('R5d', 4),
    inv_q=CH('R5e', 0), inv_moat=CH('R5e', 1), inv_rivals=CH('R5e', 2),
    w_find=CH('W1', 1), w_tick=CH('W1', 2), ibm_t=CH('W2', 1), ibm_admit=CH('W2', 2), three=CH('W3', 1),
    q1_a=CH('W4', 1), q2_a=CH('W5', 1), q3_a=CH('W6', 1), q3_idx=CH('W6', 2), mos2=CH('W7', 1),
    e1_b=CH('E1', 1), e1_c=CH('E1', 2), e2_b=CH('E2', 1),
)
q0 = LD['Q1']['t0']                                    # 逐词实测：不追高/不碰垃圾股/熟读巴菲特/专门等回调
cues['q_items'] = [round(q0 + o, 3) for o in (0.0, 0.89, 1.98, 3.15)]
cues['q_ok'] = round(q0 + 4.68, 3)                     # 「每个动作都没错」
cues['q_ask'] = round(q0 + 6.13, 3)                    # 「为什么结果总是一样？」
cues['clue'] = round(LD['R5c']['t0'] + 3.75, 3)        # 「当成了结论」
json.dump(dict(cues=cues, bpm=BPM, beat=BEAT, bar=BAR, total=T, sections=secs, lines=lines),
          open(f'{W}/timeline.json', 'w'), ensure_ascii=False, indent=1)
for k, v in secs.items(): print(f'{k:8s} {v:7.2f}')
print('cues', {k: v for k, v in cues.items() if not isinstance(v, list)})
print('total', T)
