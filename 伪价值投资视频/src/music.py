"""原创配乐 + 音效（numpy/scipy 合成），按 work/timeline.json 卡点。
输出 work/music.wav（立体声 48k）与 work/hits.json（画面用的重拍时间）。
风格：D 小调 80BPM，深沉低频、柔和钢琴、弦乐垫底；所有声音都做了低通，避免刺耳高频。"""
import json, sys, os
import numpy as np, soundfile as sf
from scipy import signal

W = sys.argv[1] if len(sys.argv) > 1 else 'work'
TL = json.load(open(f'{W}/timeline.json'))
SR = 48000; BEAT = TL['beat']; T = TL['total']
S = TL['sections']; LN = {l['id']: l for l in TL['lines']}
N = int(T * SR) + SR
rng = np.random.default_rng(7)

def bus(): return np.zeros((N, 2), np.float32)
piano, pad, bass, hits, fx = bus(), bus(), bus(), bus(), bus()
HITS = []   # (time, strength) 给画面

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
NOTE = {n: i for i, n in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])}
def M(s):   # 'D3' -> midi
    return 12 * (int(s[-1]) + 1) + NOTE[s[:-1]]

def lp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), 'low'); return signal.lfilter(b, a, x, axis=0)
def hp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), 'high'); return signal.lfilter(b, a, x, axis=0)
def bp(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], 'band'); return signal.lfilter(b, a, x, axis=0)

def put(b, t, x, gain=1.0, pan=0.0):
    i = int(t * SR)
    if x.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        x = np.stack([x * l, x * r], 1) * 1.414
    n = min(len(x), N - i)
    if n > 0: b[i:i + n] += x[:n] * gain

# ---------------------------------------------------------------- 乐器
def piano_note(m, dur=3.0, vel=0.6):
    f = hz(m); n = int((dur + 1.5) * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    bright = 0.55 + 0.45 * vel
    for k in range(1, 12):
        fk = f * k * np.sqrt(1 + 0.00035 * k * k)
        if fk > 5000: break
        amp = (1 / k ** 1.25) * (bright ** (k - 1) if k > 1 else 1)
        dec = 0.55 + 0.45 * k + f / 600
        x += amp * np.sin(2 * np.pi * fk * t + rng.random() * 6) * np.exp(-t * dec)
    x *= np.minimum(t / 0.004, 1)
    rel = np.clip((dur - t) / 0.6 + 1, 0, 1); x *= rel
    x += 0.15 * np.sin(2 * np.pi * f * 0.5 * t) * np.exp(-t * 3) * (f < 300)
    return lp(x * vel * 0.32, 4200)

def saw(f, n, detune=0.0):
    t = np.arange(n) / SR
    ph = (f * (1 + detune) * t + rng.random()) % 1.0
    return 2 * ph - 1

def pad_chord(ms, t0, t1, gain=0.12, fc=1400, att=1.2, rel=1.8, width=0.6):
    n = int((t1 - t0 + rel) * SR); t = np.arange(n) / SR
    env = np.minimum(t / att, 1) * np.clip((t1 - t0 + rel - t) / rel, 0, 1)
    L = np.zeros(n); R = np.zeros(n)
    for m in ms:
        f = hz(m)
        for d in (-0.006, -0.002, 0.003, 0.007):
            s = saw(f, n, d)
            p = (d * 70) * width
            L += s * (0.5 - p * 0.5); R += s * (0.5 + p * 0.5)
    lfo = 1 + 0.08 * np.sin(2 * np.pi * 0.17 * t)
    x = np.stack([L, R], 1) * (env * lfo)[:, None] / (len(ms) * 2)
    x = lp(lp(x, fc), fc * 1.3)
    return x * gain

def cello(m, dur, vel=0.5):
    f = hz(m); n = int((dur + 0.4) * SR); t = np.arange(n) / SR
    env = np.minimum(t / 0.03, 1) * np.exp(-t * 1.8) * np.clip((dur + 0.4 - t) / 0.4, 0, 1)
    x = (saw(f, n, 0.0) + saw(f, n, 0.004)) * 0.5
    x = lp(lp(x, 900), 1200) * env * vel
    return x * 0.5

def sub_boom(strength=1.0, f0=62, f1=30, dec=1.6):
    n = int(3.5 * SR); t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 5)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t / dec * 1.0) * np.minimum(t / 0.003, 1)
    nz = lp(rng.standard_normal(n), 180) * np.exp(-t * 14) * 0.9
    tom = np.sin(2 * np.pi * 95 * t * (1 - 0.15 * t)) * np.exp(-t * 7) * 0.35
    return np.tanh((x + nz + tom) * 1.2) * 0.38 * strength

def kick(v=0.5):
    n = int(0.6 * SR); t = np.arange(n) / SR
    f = 42 + 70 * np.exp(-t * 28)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6.5)
    return lp(x, 240) * v

def heartbeat(v=0.6):
    a = kick(v); b = kick(v * 0.65)
    out = np.zeros(int(0.9 * SR)); out[:len(a)] += a; i = int(0.24 * SR); out[i:i + len(b)] += b[:len(out) - i]
    return out

def tick(v=0.05):
    n = int(0.08 * SR); t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * 1250 * t) * 0.6 + np.sin(2 * np.pi * 640 * t)) * np.exp(-t * 90)
    return lp(x, 2200) * v

def riser(dur, v=0.25, f_lo=120, f_hi=1600):
    n = int(dur * SR); t = np.arange(n) / SR; u = t / dur
    nz = rng.standard_normal(n)
    out = np.zeros(n); seg = int(0.05 * SR)
    for i in range(0, n, seg):           # 分段扫频带通
        c = f_lo * (f_hi / f_lo) ** (u[i] ** 1.6)
        out[i:i + seg] = bp(nz[max(0, i - 2000):i + seg], c * 0.7, c * 1.3, 1)[-len(out[i:i + seg]):]
    tone = np.sin(2 * np.pi * np.cumsum(55 * 2 ** (u * 1.0)) / SR) * 0.5
    env = u ** 2.2
    return (out * 0.8 + tone) * env * v

def whoosh(dur=1.2, v=0.12):
    n = int(dur * SR); t = np.arange(n) / SR; u = t / dur
    env = np.sin(np.pi * u) ** 2
    x = lp(rng.standard_normal(n), 900) * env
    return x * v

def drone(m, t0, t1, gain=0.1, att=2.0, rel=2.0):
    n = int((t1 - t0 + rel) * SR); t = np.arange(n) / SR
    env = np.minimum(t / att, 1) * np.clip((t1 - t0 + rel - t) / rel, 0, 1)
    f = hz(m)
    x = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.003 * t) + 0.25 * np.sin(2 * np.pi * f * 3.01 * t)
    x *= 1 + 0.15 * np.sin(2 * np.pi * 0.11 * t)
    return x * env * gain

def onset(L):
    """「后来，|六十美元」这类句子里，第二个短语开口的时刻"""
    l = LN[L]; ps = [b for a, b in l['pauses'] if a > 0.3]
    return l['t0'] + (ps[0] if ps else 0.36 * (l['t1'] - l['t0']))

def hit(t, s=1.0, **kw):
    put(hits, t, sub_boom(s, **kw)); HITS.append((round(t, 3), s))

# ---------------------------------------------------------------- 编排
B = lambda k: k * BEAT
DM, BB, F, C, GM, A = (['D3', 'F3', 'A3'], ['A#2', 'D3', 'F3'], ['F3', 'A3', 'C4'], ['C3', 'E3', 'G3'],
                       ['G2', 'A#2', 'D3'], ['A2', 'C#3', 'E3'])
ROOT = {'DM': 'D2', 'BB': 'A#1', 'F': 'F2', 'C': 'C2', 'GM': 'G1', 'A': 'A1'}
CH = dict(DM=DM, BB=BB, F=F, C=C, GM=GM, A=A)

# --- 序章 hook：低频长音 + 心跳 + 零星钢琴
t_cases = S['cases']
put(pad, 0, drone(M('D2'), 0, t_cases, 0.09, att=0.4))
put(pad, 0, pad_chord([M(x) for x in DM], 0, t_cases, 0.06, fc=700, att=3))
for k in range(0, int(t_cases / BEAT), 2):
    put(bass, B(k), heartbeat(0.55 if k < 12 else 0.7))
for k, n in [(0, 'A4'), (4, 'F4'), (8, 'D4'), (11, 'E4'), (12, 'F4'), (16, 'A4')]:
    put(piano, B(k) + 0.0, piano_note(M(n), 3.0, 0.42), pan=0.15)
hit(LN['L02']['t0'] + 0.0, 0.55)        # 「而是，最听话的好学生」
put(fx, t_cases - 1.5, riser(1.5, 0.12))

# --- 案例 cases：Dm-B♭-F-C 钢琴琶音 + 低鼓 + 钟表滴答
t_piv = S['pivot']; q_stop = LN['L13']['t0']
prog = ['DM', 'BB', 'F', 'C']
k0 = int(round(t_cases / BEAT)); k1 = int(round(q_stop / BEAT))
for k in range(k0, k1):
    bar = (k - k0) // 4; c = prog[bar % 4]; ms = [M(x) for x in CH[c]]
    if (k - k0) % 4 == 0:
        put(bass, B(k), cello(M(ROOT[c]), BEAT * 3.6, 0.55))
        put(pad, B(k), pad_chord([m + 12 for m in ms], B(k), B(k + 4), 0.05, fc=900, att=0.8, rel=1.2))
    for h in range(2):                   # 8 分音符琶音
        idx = [0, 1, 2, 1, 0, 2, 1, 2][((k - k0) % 4) * 2 + h]
        put(piano, B(k) + h * BEAT / 2, piano_note(ms[idx] + 12, 1.2, 0.30 + 0.06 * (h == 0)), pan=-0.2 + 0.2 * idx)
    if (k - k0) % 2 == 0: put(bass, B(k), kick(0.45))
    put(fx, B(k), tick(0.035), pan=0.3); put(fx, B(k) + BEAT / 2, tick(0.02), pan=0.3)
for L in ('L05', 'L08', 'L10'):          # 每一次「后来……」：深沉下坠
    t = onset(L)
    put(fx, t - 0.9, whoosh(0.9, 0.10)); hit(t, 0.9, f0=55, f1=28, dec=1.9)
hit(LN['L11']['t0'], 0.4)
hit(S['cases'], 0.6)
put(fx, LN['L12']['t0'], riser(LN['L13']['t0'] - LN['L12']['t0'], 0.10, 100, 900))
hit(q_stop, 0.5)                          # 「这一次，总该对了吧？」后音乐抽空
put(pad, q_stop, drone(M('A1'), q_stop, t_piv + 4, 0.12, att=0.3))

# --- 追问 pivot：心跳加速 + 上升 → 标题重拍
t_title = S['title']
for k in range(int(round(t_piv / BEAT)), int(round(t_title / BEAT))):
    put(bass, B(k), heartbeat(0.5 + 0.05 * (k - t_piv / BEAT)))
put(fx, t_title - 3.0, riser(3.0, 0.22, 90, 1500))
hit(t_title, 1.35, f0=70, f1=26, dec=2.6)
put(pad, t_title, pad_chord([M(x) for x in ['D2', 'A2', 'D3', 'F3', 'A3']], t_title, S['munger'] + 2, 0.13, fc=1100, att=0.05, rel=3))
put(piano, t_title, piano_note(M('D3'), 5, 0.7)); put(piano, t_title, piano_note(M('D4'), 5, 0.5))

# --- 芒格 munger + 三刀：Dm-B♭-Gm-A 弦乐，大提琴 8 分律动
t_kill = S['kill']
prog2 = ['DM', 'BB', 'GM', 'A']
k0 = int(round(S['munger'] / BEAT)); k1 = int(round(t_kill / BEAT))
for k in range(k0, k1):
    bar = (k - k0) // 4; c = prog2[bar % 4]; ms = [M(x) for x in CH[c]]
    if (k - k0) % 4 == 0:
        put(pad, B(k), pad_chord([m + 12 for m in ms] + [ms[0]], B(k), B(k + 4), 0.12, fc=1800, att=0.6, rel=1.0))
        put(piano, B(k), piano_note(ms[2] + 24, 2.5, 0.35), pan=0.25)
    if k >= S['p1'] / BEAT - 0.01:       # 第一刀开始加律动
        for h in range(2):
            put(bass, B(k) + h * BEAT / 2, cello(M(ROOT[c]) + (12 if h else 0), BEAT * 0.45, 0.42))
        if (k - k0) % 4 in (0, 2): put(bass, B(k), kick(0.5))
for key in ('p1', 'p2', 'p3'):
    t = S[key]; put(fx, t - 1.2, whoosh(1.2, 0.12)); hit(t, 1.0)
hit(LN['L18']['t1'] - 1.0, 0.45)        # 「依然贵了 5 倍」
hit(LN['L20']['t1'] - 0.95, 0.6)         # 「就是 26 倍」
hit(LN['L22']['t1'] - 0.8, 0.6)         # 「只有 3 家」

# --- kill：抽空，只留低音；「什么，会杀死它？」落一记重低音
t_cure = S['cure']
put(pad, t_kill, drone(M('A1'), t_kill, t_cure - 0.5, 0.15, att=0.2, rel=1.0))
put(pad, t_kill, pad_chord([M('A2'), M('E3'), M('A3')], t_kill, t_cure - 1, 0.05, fc=600, att=1.5))
t_q = LN['L24']['t0'] + 4.0
for k in range(int(round(t_kill / BEAT)), int(round(t_q / BEAT))):
    put(fx, B(k), tick(0.03), pan=0.3)
hit(LN['L24']['t1'] - 1.1, 1.1, f0=60, f1=24, dec=2.4)
put(fx, t_cure - 2.2, riser(2.2, 0.08, 200, 1200))

# --- cure：转到 F 大调，温暖钢琴旋律
t_end = S['end']; t_card = S['card']
prog3 = [['A#2', 'D3', 'F3', 'A3'], ['F2', 'A2', 'C3', 'E3'], ['C3', 'E3', 'G3', 'D4'], ['D3', 'F3', 'A3', 'C4']]
roots3 = ['A#1', 'F1', 'C2', 'D2']
mel = ['D5', 'C5', 'A4', 'C5', 'F5', 'E5', 'C5', 'G4', 'E5', 'D5', 'C5', 'D5', 'A4', 'G4', 'F4', 'A4']
k0 = int(round(t_cure / BEAT)); k1 = int(round(t_card / BEAT))
hit(t_cure, 0.7, f0=58, f1=32, dec=2.2)
for k in range(k0, k1):
    bar = (k - k0) // 4; ms = [M(x) for x in prog3[bar % 4]]
    if (k - k0) % 4 == 0:
        fc = 1100 + min(bar, 6) * 180
        put(pad, B(k), pad_chord([m + 12 for m in ms], B(k), B(k + 4), 0.11, fc=fc + 600, att=0.5, rel=1.2))
        put(bass, B(k), cello(M(roots3[bar % 4]), BEAT * 3.8, 0.5))
        if bar >= 2: put(bass, B(k), kick(0.35))
    for h in range(2):
        idx = [0, 2, 1, 3, 2, 1, 3, 2][((k - k0) % 4) * 2 + h]
        put(piano, B(k) + h * BEAT / 2, piano_note(ms[idx] + 12, 1.4, 0.24), pan=-0.25 + 0.15 * idx)
    if bar >= 1 and (k - k0) % 2 == 0:
        put(piano, B(k), piano_note(M(mel[((k - k0) // 2) % len(mel)]), 2.0, 0.34), pan=0.1)
# 结尾：F 大调加九和弦长音
fin = [M(x) for x in ['F2', 'C3', 'F3', 'A3', 'C4', 'G4']]
put(pad, t_end, pad_chord(fin, t_end, T - 1.0, 0.11, fc=1500, att=1.0, rel=2.5))
for i, m in enumerate(fin[2:]):
    put(piano, t_card + i * 0.12, piano_note(m + 12, 5, 0.38), pan=-0.3 + 0.2 * i)
put(bass, t_card, cello(M('F1'), 4, 0.6)); hit(t_card, 0.75, f0=55, f1=30, dec=2.8)

# ---------------------------------------------------------------- 混音
def ir(dur, dec, fc, seed):
    r = np.random.default_rng(seed); n = int(dur * SR); t = np.arange(n) / SR
    x = r.standard_normal(n) * np.exp(-t / dec) * np.minimum(t / 0.01, 1)
    return lp(x, fc) / np.sqrt(np.sum(x ** 2))
IRL, IRR = ir(3.5, 0.75, 3500, 1), ir(3.5, 0.75, 3500, 2)
def verb(x, wet):
    m = x.mean(1)
    return np.stack([signal.fftconvolve(m, IRL)[:N], signal.fftconvolve(m, IRR)[:N]], 1) * wet

mix = (piano * 1.7 + verb(piano, 0.9) + pad * 1.3 + verb(pad, 0.4) + bass * 0.7 + verb(bass, 0.06)
       + hits * 0.8 + verb(hits, 0.3) + fx * 1.0 + verb(fx, 0.45))
mix = hp(mix, 40, 2) + lp(mix, 40, 2) * 0.6   # 收一点超低频
mix = hp(mix, 28, 2)
mix = lp(mix, 9000, 2)                   # 全局去刺耳高频

# 旁白闪避：有人声时音乐压低约 7dB
v, vsr = sf.read(f'{W}/voice.wav', dtype='float32')
env = np.abs(v); env = np.pad(env, (0, max(0, N - len(env))))[:N]
k = int(0.02 * SR); env = np.convolve(env, np.ones(k) / k, 'same')
env = (env > 0.01).astype(np.float32)
# attack 80ms / release 450ms 平滑
a_att, a_rel = np.exp(-1 / (0.08 * SR)), np.exp(-1 / (0.45 * SR))
g = signal.lfilter([1 - a_rel], [1, -a_rel], env)
g = np.maximum(g, signal.lfilter([1 - a_att], [1, -a_att], env))
duck = 1 - 0.55 * np.clip(g * 1.4, 0, 1)
mix *= duck[:, None]
mix = mix[:int(T * SR)]
f = int(2.0 * SR); mix[-f:] *= np.linspace(1, 0, f)[:, None] ** 1.5
mix /= np.sqrt(np.mean(mix ** 2)) / 0.09         # 按 RMS 定电平
mix = np.tanh(mix / 0.8) * 0.8                  # 软限幅，只削重击峰值
sf.write(f'{W}/music.wav', mix.astype(np.float32), SR, subtype='FLOAT')
json.dump(sorted(HITS), open(f'{W}/hits.json', 'w'))
print('music ok', len(mix) / SR, 'hits', len(HITS))
