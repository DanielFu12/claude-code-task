"""原创卡点配乐（120 BPM，A 小调，Am–F–C–G）——全部用 numpy 逐音符合成，无任何外部采样

用法：python3 music.py <work_dir>
输出：<work_dir>/mix.wav（配乐 + 转场音效，已母带处理）、<work_dir>/events.json（鼓点时间，供画面卡点）

设计：
- 情绪曲线：前奏悬念 → 停顿式重音 → 军鼓滚奏蓄力 → DROP（满编：四拍底鼓、二四拍拍手、十六分踩镲、侧链泵动的贝斯和超锯齿和弦）
  → 半速暗色段 → 抽空心跳 → 第二次 DROP（加入主旋律）→ 终止重击。
- 每个转场点都有：前一拍的军鼓过门 + 转场拍上的低音 tom / 低频冲击 / 柔和的镲片涌起。
- 音色刻意压住高频（踩镲、镲片都经过低通），整体温暖、厚重、不刺耳。
"""
import sys, os, json
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import *

SR = 44100
N = int(DUR * SR)
rng = np.random.default_rng(2026)

def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x, axis=0)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x, axis=0)
def bp(x, f0, f1, o=2): return sosfilt(butter(o, [f0, f1], 'band', fs=SR, output='sos'), x, axis=0)
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def tt(n): return np.arange(n) / SR

class Bus:
    def __init__(self): self.x = np.zeros((N, 2))
    def put(self, t, sig, g=1.0, pan=0.0):
        i = int(round(t * SR))
        if sig.ndim == 1:
            sig = np.stack([sig * (1 - max(pan, 0)), sig * (1 + min(pan, 0))], 1)
        j0, j1 = max(i, 0), min(i + len(sig), N)
        if j1 > j0: self.x[j0:j1] += sig[j0 - i:j1 - i] * g

drums, bass, pad, arp, lead, fx, verb_send = (Bus() for _ in range(7))
EV = {'kick': [], 'snare': [], 'accent': []}

# ------------------------------------------------------------------ 音色
def kick(dur=0.45, f0=150, f1=44, dec=0.30):
    n = int(dur * SR); t = tt(n)
    f = f1 + (f0 - f1) * np.exp(-t / 0.028)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / dec)
    s = np.tanh(s * 2.6) / np.tanh(2.6)
    click = lp(rng.standard_normal(n), 3000) * np.exp(-t / 0.005) * 0.45
    return (s + click) * np.minimum(t / 0.001, 1)

def clap(dur=0.35):
    n = int(dur * SR); t = tt(n)
    nz = bp(rng.standard_normal(n), 900, 4200)
    env = np.exp(-t / 0.11)
    for d in (0.0, 0.009, 0.018):
        env = env + 0.6 * np.exp(-np.maximum(t - d, 0) / 0.006) * (t >= d)
    body = np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.05) * 0.5
    return nz * env * 0.6 + body

def snare_short(dur=0.18):
    n = int(dur * SR); t = tt(n)
    return bp(rng.standard_normal(n), 700, 4000) * np.exp(-t / 0.045) * 0.7 + np.sin(2 * np.pi * 200 * t) * np.exp(-t / 0.03) * 0.4

def hat(dur=0.06, dec=0.022):
    n = int(dur * SR); t = tt(n)
    return lp(hp(rng.standard_normal(n), 6500), 10000) * np.exp(-t / dec)

def tom(dur=1.0, f0=110, f1=58):
    n = int(dur * SR); t = tt(n)
    f = f1 + (f0 - f1) * np.exp(-t / 0.08)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.35)
    return np.tanh(s * 1.5) + lp(rng.standard_normal(n), 600) * np.exp(-t / 0.04) * 0.4

def boom(dur=3.0, f0=70, f1=30):
    n = int(dur * SR); t = tt(n)
    f = f1 + (f0 - f1) * np.exp(-t / 0.3)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 1.0)
    return np.tanh(s * 1.6) / np.tanh(1.6) + lp(rng.standard_normal(n), 200) * np.exp(-t / 0.2) * 0.4

def crash(dur=2.4):
    """柔和镲片：低通噪声长衰减（不刺耳）"""
    n = int(dur * SR); t = tt(n)
    nz = lp(hp(rng.standard_normal((n, 2)), 2500), 7000)
    return nz * (np.exp(-t / 0.9) * np.minimum(t / 0.01, 1))[:, None]

def swell(dur):
    """反向镲：在转场前一拍涌起"""
    return crash(dur)[::-1] * np.linspace(0, 1, int(dur * SR))[:, None] ** 2

def whoosh(dur=1.0):
    n = int(dur * SR); t = tt(n)
    nz = np.cumsum(rng.standard_normal((n, 2)), 0); nz = hp(nz, 40); nz /= np.abs(nz).max() + 1e-9
    e = np.sin(np.pi * t / dur) ** 2
    return lp(nz, 700) * e[:, None]

def riser(dur):
    n = int(dur * SR); t = tt(n); u = t / dur
    nz = rng.standard_normal((n, 2)); out = np.zeros_like(nz)
    for k in range(6):
        c = 150 * (3200 / 150) ** (k / 5)
        out += bp(nz, c * 0.75, c * 1.3) * np.exp(-((u * 5 - k) ** 2) / 1.0)[:, None]
    f = 55 * 2 ** (u * 2)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.5 + np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR) * 0.2
    return (out * 0.7 + tone[:, None]) * (u ** 2.2)[:, None]

def saw(f, n, ph=0.0):
    return 2 * ((ph + np.cumsum(np.full(n, f / SR))) % 1.0) - 1

def supersaw(m, dur, voices=5, spread=0.18):
    n = int(dur * SR); out = np.zeros((n, 2))
    for v in range(voices):
        det = (v - (voices - 1) / 2) / ((voices - 1) / 2) * spread
        s = saw(mtof(m + det), n, rng.random())
        pan = (v / (voices - 1)) * 2 - 1
        out[:, 0] += s * (1 - 0.6 * max(pan, 0)); out[:, 1] += s * (1 + 0.6 * min(pan, 0))
    return out / voices

def pluck(m, dur=0.35, dec=0.16, bright=0.5):
    n = int(dur * SR); t = tt(n)
    s = saw(mtof(m), n) * 0.7 + np.sign(np.sin(2 * np.pi * mtof(m) * t)) * 0.3
    s = lp(s, 600 + 4000 * bright) * np.exp(-t / dec) * np.minimum(t / 0.002, 1)
    return s

def sub(m, dur, rel=0.05):
    n = int(dur * SR); t = tt(n)
    e = np.minimum(t / 0.01, 1) * np.minimum((dur - t) / rel, 1)
    return np.sin(2 * np.pi * mtof(m) * t) * e

# ------------------------------------------------------------------ 和声
CH = {'Am': [57, 60, 64, 69], 'F': [53, 57, 60, 65], 'C': [55, 60, 64, 67], 'G': [55, 59, 62, 67]}
ROOT = {'Am': 33, 'F': 29, 'C': 36, 'G': 31}
MAIN = ['Am', 'F', 'C', 'G']
BREAK = ['F', 'G', 'Am', 'Am']

def chord_of(bar):
    if 40 <= bar <= 48: return BREAK[(bar - 40) % 4]
    if 49 <= bar <= 52: return ['Am', 'F', 'Am', 'G'][bar - 49]
    if bar >= 73: return 'Am'
    return MAIN[bar % 4]

def section(bar):
    if bar <= 4: return 'intro'
    if bar <= 8: return 'groove'
    if bar <= 10: return 'stops'
    if bar == 11: return 'build'
    if 30 <= bar <= 35: return 'light'
    if bar <= 39: return 'drop1'
    if bar <= 48: return 'half'
    if bar <= 52: return 'void'
    if bar <= 72: return 'drop2'
    return 'end'

NBARS = 73

# ------------------------------------------------------------------ 编排
FILL_BEATS = {round(tc / SPB) - 1 for tc in CUTS}      # 每个转场前一拍放军鼓过门

for bar in range(NBARS + 1):
    sec = section(bar); ch = chord_of(bar); t0 = b(bar * 4)
    # ---- 鼓
    for k in range(4):
        bi = bar * 4 + k; tb = b(bi)
        if sec == 'intro' and bar >= 2:
            drums.put(tb, lp(kick(), 280), 0.45)
        if sec in ('groove', 'drop1', 'drop2', 'light'):
            if not (bi in FILL_BEATS and sec != 'groove' and k == 3 and False):
                drums.put(tb, kick(), 1.0); EV['kick'].append(tb)
            if k in (1, 3) and not (sec == 'groove' and bar == 5) and sec != 'light':
                drums.put(tb, clap(), 0.55); verb_send.put(tb, clap(), 0.25); EV['snare'].append(tb)
            for s16 in range(4):
                g = 0.15 if s16 % 2 == 0 else 0.08
                if sec in ('groove', 'light') and s16 % 2: continue
                drums.put(tb + s16 * SPB / 4, hat(), g, pan=0.25)
            if sec not in ('groove', 'light'):
                drums.put(tb + SPB / 2, hat(0.25, 0.09), 0.07, pan=-0.2)          # 反拍开镲
        if sec == 'half':
            if k == 0: drums.put(tb, kick(), 0.95); EV['kick'].append(tb)
            if k == 1: drums.put(tb + SPB / 2, kick(), 0.7); EV['kick'].append(tb + SPB / 2)
            if k == 2:
                drums.put(tb, clap(), 0.6); verb_send.put(tb, clap(), 0.4); EV['snare'].append(tb)
            drums.put(tb, hat(), 0.07, pan=0.2); drums.put(tb + SPB / 2, hat(), 0.045, pan=0.2)
        if sec == 'stops' or (sec == 'void' and 50 <= bar <= 51):
            for s16 in range(4):
                drums.put(tb + s16 * SPB / 4, hat(0.04, 0.012), 0.05, pan=0.3)       # 紧张的细碎滴答
        if sec == 'void' and bar <= 51 and k in (0, 2):
            drums.put(tb, lp(kick(), 200), 0.8); drums.put(tb + 0.22, lp(kick(), 200), 0.5)   # 心跳
            EV['kick'].append(tb)
        # 过门
        if bi in FILL_BEATS and sec in ('drop1', 'drop2', 'half', 'groove'):
            for s16 in range(4):
                drums.put(tb + s16 * SPB / 4, snare_short(), 0.18 + 0.1 * s16, pan=(s16 - 1.5) * 0.2)
    # ---- 军鼓滚奏（第 8、31 小节）
    if sec == 'build' or bar == 52:
        n_hits = [4, 8, 16, 16]
        for k in range(4):
            for j in range(n_hits[k]):
                th = b(bar * 4 + k) + j * SPB / n_hits[k]
                if th >= b(bar * 4 + 3.75): break
                drums.put(th, snare_short(), 0.12 + 0.35 * (k * 0.25 + j / n_hits[k] * 0.25), pan=0.1 * np.sin(j))
    # ---- 贝斯
    root = ROOT[ch]
    if sec in ('groove', 'stops', 'half', 'void'):
        d = 2.0 if sec != 'stops' else 2.0
        bass.put(t0, sub(root, d), 0.9 if sec != 'void' else 0.4)
    if sec in ('drop1', 'drop2', 'light'):
        for e8 in range(8):
            te = t0 + e8 * SPB / 2
            bass.put(te, sub(root, SPB / 2 * 0.95), 0.9)
            mid = lp(np.tanh(2.5 * saw(mtof(root + 12), int(SPB / 2 * 0.9 * SR))), 1400) * np.exp(-tt(int(SPB / 2 * 0.9 * SR)) / 0.18)
            bass.put(te, mid, 0.75)
    if sec == 'intro' and bar >= 1:
        bass.put(t0, sub(33, 2.0, 0.3) * np.linspace(0.3, 1, int(2.0 * SR)), 0.5)
    # ---- 和弦垫
    if sec != 'end':
        for m in CH[ch]:
            pad.put(t0, supersaw(m, 2.02, 5 if sec in ('drop1', 'drop2') else 3), 0.22)
            if sec in ('drop1', 'drop2'): pad.put(t0, supersaw(m + 12, 2.02, 3), 0.07)
    # ---- 琶音（十六分音符）
    if sec in ('intro', 'groove', 'build', 'drop1', 'drop2', 'stops', 'light'):
        tones = CH[ch] + [x + 12 for x in CH[ch]]
        for s16 in range(16):
            ts = t0 + s16 * SPB / 4
            m = tones[[0, 1, 2, 3, 4, 3, 2, 1][s16 % 8] + (s16 // 8) * 0]
            br = {'intro': 0.1 + 0.25 * (bar + s16 / 16) / 4, 'groove': 0.45, 'build': 0.6, 'stops': 0.35, 'light': 0.4}.get(sec, 0.55)
            g = {'intro': 0.25 + 0.1 * bar, 'drop1': 0.45, 'drop2': 0.4}.get(sec, 0.55)
            arp.put(ts, pluck(m + 12, 0.3, 0.12, br), g, pan=0.35 * np.sin(s16 * 0.8))
    # ---- 主旋律（第二次 DROP）
    if sec == 'drop2':
        A = {'Am': [81, 0, 79, 76, 0, 76, 79, 81], 'F': [77, 0, 76, 72, 0, 72, 76, 77],
             'C': [79, 0, 76, 72, 0, 74, 76, 79], 'G': [79, 0, 74, 71, 0, 74, 76, 74]}
        B = {'Am': [76, 0, 0, 81, 0, 84, 83, 81], 'F': [77, 0, 0, 81, 0, 84, 81, 79],      # B 乐句：音区抬高、留白更多
             'C': [76, 0, 0, 79, 0, 84, 83, 79], 'G': [74, 0, 0, 79, 0, 83, 81, 79]}
        motif = (B if (bar - 51) // 4 % 2 else A)[ch]
        for e8, m in enumerate(motif):
            if m: lead.put(t0 + e8 * SPB / 2, pluck(m - 12, 0.5, 0.22, 0.45), 0.5)
    # ---- 轻编段（新进公司讲解）：稀疏的钟琴式旋律，每小节两个长音
    if sec == 'light':
        bell = {'Am': [76, 72], 'F': [77, 72], 'C': [76, 79], 'G': [74, 79]}[ch]
        for k, m in enumerate(bell):
            n = int(1.0 * SR); tb = tt(n)
            tone = (np.sin(2 * np.pi * mtof(m) * tb) + 0.35 * np.sin(2 * np.pi * mtof(m) * 2.0 * tb)
                    + 0.12 * np.sin(2 * np.pi * mtof(m) * 3.01 * tb)) * np.exp(-tb / 0.45) * np.minimum(tb / 0.004, 1)
            lead.put(t0 + k * 1.0, tone, 0.42, pan=0.25 * (1 if k else -1))
            verb_send.put(t0 + k * 1.0, tone, 0.25)

# ---- 停顿式重音：四个数字
for th in TILE_HITS:
    drums.put(th, kick(), 1.0); drums.put(th, tom(), 0.6); verb_send.put(th, tom(), 0.3)
    fx.put(th, crash(1.4), 0.10)
    for m in CH[chord_of(int(th // 2))]:
        pad.put(th, supersaw(m, 0.6) * np.exp(-tt(int(0.6 * SR)) / 0.18)[:, None], 0.5)
    EV['accent'].append(th); EV['kick'].append(th)
# ---- 转场重音
for tc in CUTS:
    fx.put(tc - SPB, swell(SPB), 0.12)
    fx.put(tc - 0.55, whoosh(1.1), 0.30)
    drums.put(tc, tom(), 0.45); verb_send.put(tc, tom(), 0.2)
    fx.put(tc, crash(), 0.08)
    EV['accent'].append(tc)
# ---- 两次 DROP 与终止
for t0, t1 in RISERS:
    fx.put(t0, riser(t1 - t0 - SPB / 2), 0.22)
for ti, k in IMPACTS:
    fx.put(ti, boom(3.4 if k >= 1 else 2.2), 0.75 * k)
    drums.put(ti, tom(1.2, 90, 40), 0.7 * k); verb_send.put(ti, tom(1.2, 90, 40), 0.5 * k)
    fx.put(ti, crash(3.0), 0.16 * k)
    EV['accent'].append(ti)
# 片尾：长和弦余韵 + 低频金属感
for m in CH['Am'] + [45]:
    pad.put(T_END, supersaw(m, 6.0) * np.exp(-tt(int(6.0 * SR)) / 2.0)[:, None], 0.3)
gong = sum(a * np.sin(2 * np.pi * f * tt(int(6 * SR)) + p) * np.exp(-tt(int(6 * SR)) / d)
           for f, a, d, p in [(55, 1.0, 2.4, 0), (82.4, .6, 1.9, 1), (110.3, .45, 1.6, 2), (164.9, .25, 1.2, .5)])
fx.put(T_END, gong, 0.35)
# 冷开场的计数「滴答」
for k in range(24):
    th = 1.0 + k * SPB / 4 * (1 if k < 16 else 1)
    if th < b(12): fx.put(th, np.sin(2 * np.pi * 900 * tt(1200)) * np.exp(-tt(1200) / 0.006), 0.035)

# ------------------------------------------------------------------ 自动化 + 侧链
T = tt(N)
def curve(points):
    return np.interp(T, [p[0] for p in points], [p[1] for p in points])

# 和弦垫亮度：前奏暗 → DROP 亮 → 半速段暗 → 抽空最暗 → DROP2 最亮
bright = curve([(0, 0.0), (b(44), 0.35), (T_DROP1 - 0.05, 0.6), (T_DROP1, 1.0), (T_S9 - 0.05, 1.0), (T_S9, 0.35),
                (T_S10 - 0.05, 0.3), (T_S10, 0.08), (T_DROP2 - 0.05, 0.25), (T_DROP2, 1.0), (DUR, 1.0)])[:, None]
pad_dark, pad_bright = lp(pad.x, 700, 2), lp(pad.x, 3800, 2)
pad_mix = pad_dark * (1 - bright) + pad_bright * bright
arp_mix = lp(arp.x, 5000)

sc = np.ones(N)
for tk in EV['kick']:
    i = int(tk * SR); m = min(int(0.4 * SR), N - i)
    if m > 0: sc[i:i + m] = np.minimum(sc[i:i + m], 1 - 0.65 * np.exp(-tt(m) / 0.11))
sc = sc[:, None]

# 混响（指数衰减噪声脉冲响应）
ir_n = int(2.4 * SR)
ir = lp(rng.standard_normal((ir_n, 2)), 4500) * np.exp(-tt(ir_n) / 0.7)[:, None]
ir /= np.sqrt((ir ** 2).sum(0))
rev_in = verb_send.x + pad_mix * 0.25 + arp_mix * 0.3 + lead.x * 0.35
rev = np.stack([fftconvolve(rev_in[:, c], ir[:, c])[:N] for c in range(2)], 1)

def norm(x, db):
    r = np.sqrt((x ** 2).mean()) + 1e-12
    return x * (10 ** (db / 20) / r)

mix = (norm(drums.x, -15) + norm(bass.x * sc, -18.5) + norm(pad_mix * sc, -18.5) + norm(arp_mix * sc, -22.5)
       + norm(lead.x * sc, -25) + norm(fx.x, -22) + norm(rev, -23))
mix = hp(mix, 25)
mix = mix - 0.5 * lp(mix, 95, 2)            # 低频搁架衰减约 -6 dB：避免手机外放发闷
mix = mix + 0.25 * bp(mix, 2500, 6000)       # 轻微提亮中高频（只到 6 kHz，不刺耳）
# 段落动态：前奏渐强、半速段略收、抽空段明显压低，把两次 DROP 衬托出来
dyn = curve([(0, 0.55), (b(19.9), 0.8), (b(20), 0.9), (T_DROP1 - 0.01, 0.9), (T_DROP1, 1.0), (T_S8 - 0.05, 1.0), (T_S8 + 0.5, 0.72),
             (T_ADD - 0.05, 0.72), (T_ADD, 1.0), (T_S9 - 0.05, 1.0), (T_S9, 0.82),
             (T_S10 - 0.05, 0.82), (T_S10 + 0.6, 0.62), (b(206), 0.62), (b(208), 0.7), (T_DROP2 - 0.05, 0.85), (T_DROP2, 1.05),
             (DUR, 1.05)])[:, None]
mix = mix * dyn
# 软削波 + 归一化
mix = np.tanh(mix * 1.6) / 1.6
fo = int(1.5 * SR); mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
mix *= 0.93 / np.abs(mix).max()
try:   # 响度对齐到约 -12 LUFS（短视频平台常用），峰值不超过 -1 dBFS
    import pyloudnorm as pl
    g = 10 ** ((-12.0 - pl.Meter(SR).integrated_loudness(mix)) / 20)
    mix *= min(g, 0.89 / np.abs(mix).max())
except ImportError:
    pass
WK = sys.argv[1]
sf.write(os.path.join(WK, 'mix.wav'), mix.astype(np.float32), SR, subtype='FLOAT')
json.dump({k: sorted(set(round(v, 4) for v in vs)) for k, vs in EV.items()}, open(os.path.join(WK, 'events.json'), 'w'))
print('music', DUR, 's  kicks', len(EV['kick']), ' snares', len(EV['snare']), ' accents', len(EV['accent']))
