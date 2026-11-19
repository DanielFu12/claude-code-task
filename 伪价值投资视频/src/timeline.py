"""把旁白排到节拍网格上 -> work/timeline.json + work/voice.wav
80 BPM：1 拍 0.75s，1 小节 3s。台词起点吸附到半拍；章节起点吸附到小节线。"""
import json, math, os, sys
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(__file__))
from script import LINES
W = sys.argv[1] if len(sys.argv) > 1 else 'work'
BPM = 80; BEAT = 60 / BPM; BAR = 4 * BEAT; SR = 48000
# 章节：从哪一句开始，起点前额外留多少小节（音乐/画面过门）
SECTIONS = [('hook', 'H1', 0), ('cases', 'T1', 0), ('pivot', 'L14', 0), ('title', None, 0),
            ('munger', 'L15', 0), ('p1', 'L16', 0), ('p2', 'L19', 0), ('p3', 'L21', 0), ('kill', 'L24', 0),
            ('cure', 'L25', 0), ('end', 'L29', 0), ('card', None, 0)]
SEC_START = {s[1]: s[0] for s in SECTIONS if s[1]}
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

up = lambda t, q: math.ceil(t / q - 1e-6) * q
t = BEAT * 1                    # 开场 1 拍就进旁白（钩子要快）
EXTRA = dict(cases=0, pivot=BEAT, p1=0, p2=BEAT / 2, p3=BEAT / 2, kill=BEAT, cure=BEAT * 2, end=BEAT)
lines, secs = [], {'hook': 0.0}
voice = np.zeros(int(200 * SR), np.float32)
for (i, text, sub, ctx, gap) in LINES:
    y, _ = sf.read(f'{W}/vo/{i}.wav', dtype='float32')
    d = len(y) / SR
    if i in SEC_START and i != 'H1':
        name = SEC_START[i]
        if name == 'munger':            # 标题卡：「伪价值投资」6 拍
            t = up(t, BEAT); secs['title'] = t; t += 6 * BEAT
        t = up(t + EXTRA.get(name, 0), BEAT)
        secs[name] = t
    ps = pauses(y)
    lines.append(dict(id=i, t0=round(t, 4), t1=round(t + d, 4), sub=sub, pauses=ps,
                      chunks=chunks(sub, ps, t, d)))
    a = int(t * SR); voice[a:a + len(y)] += y
    t = up(t + d + gap, BEAT / 2)
LD = {l['id']: l for l in lines}
def after_pause(i, k):
    l = LD[i]; return round(l['t0'] + l['pauses'][k][1], 3)
# 数字揭晓的瞬间（配乐重击 + 画面落点共用）
cues = dict(
    h1_turn=LD['H1']['chunks'][1][1],                 # 「八年后，股价还在成本线下」
    tx_now=after_pause('T2', 0),                      # 「如今，|373」
    ali_low=round(LD['A2']['t0'] + 1.05, 3),          # 「后来，跌到|60」
    ali_now=round(LD['A2']['chunks'][1][1] + 1.25, 3),# 「五年后的今天，|84」
    zp_now=after_pause('Z2', 1),                      # 「如今，|366」（第 0 个停顿在句首）
    nv_now=round(LD['N3']['t1'] - 1.15, 3),           # 「却跌到|151」
    stamp=LD['G1']['chunks'][2][1] + 0.6,             # 「这样的好学生」盖章
)
secs['card'] = up(t + BEAT / 2, BEAT)
T = secs['card'] + 6 * BEAT
voice = voice[:int(T * SR)]
sf.write(f'{W}/voice.wav', voice, SR, subtype='FLOAT')
json.dump(dict(cues=cues, bpm=BPM, beat=BEAT, bar=BAR, total=T, sections=secs, lines=lines), open(f'{W}/timeline.json', 'w'),
          ensure_ascii=False, indent=1)
for k, v in secs.items(): print(f'{k:7s} {v:7.2f}  bar {v / BAR:.2f}')
print('total', T)
