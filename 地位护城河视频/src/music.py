"""原创配乐：程序化合成的电子/电影感配乐，与 timeline.py 的段落逐小节对齐。

用法: python3 music.py out.wav
只依赖 numpy + scipy + soundfile。所有声音（鼓、贝斯、超级锯齿 Pad、拨弦琶音、钟声主旋律、
上升音效、重拍冲击）都在这里从振荡器和噪声合成，没有任何采样。
"""
import sys, math
import numpy as np, soundfile as sf
from scipy import signal
from timeline import *

SR = 44100
N = int(DUR * SR) + SR * 2
RNG = np.random.default_rng(7)

NOTE_PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
CHORDS = {'Dm': (2, [0, 3, 7]), 'Bb': (10, [0, 4, 7]), 'F': (5, [0, 4, 7]), 'C': (0, [0, 4, 7]),
          'Gm': (7, [0, 3, 7]), 'A': (9, [0, 4, 7]), 'D': (2, [0, 4, 7])}

def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)

def chord_at_bar(b):
    t = b * BAR
    s = segment_at(t)
    k = int(round((t - s[0]) / BAR))
    if s[2] == 'outro':
        k = min(k, 3)
    return PROG[s[3]][k % 4]

NBARS = int(DUR / BAR)
BAR_CH = [chord_at_bar(b) for b in range(NBARS)]
BAR_STYLE = [segment_at(b * BAR)[2] for b in range(NBARS)]

def voicing(name, lo=55, n=4):
    root, ivs = CHORDS[name]
    pcs = [(root + i) % 12 for i in ivs]
    notes = []
    m = lo
    while len(notes) < n:
        if m % 12 in pcs: notes.append(m)
        m += 1
    return notes

# ------------------------------------------------------------------ helpers
def buf(): return np.zeros((N, 2), np.float32)

def add(dst, x, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N: return
    if x.ndim == 1:
        l = math.cos((pan + 1) * math.pi / 4); r = math.sin((pan + 1) * math.pi / 4)
        x = np.stack([x * l, x * r], 1) * math.sqrt(2)
    n = min(len(x), N - i)
    if i < 0:
        x = x[-i:]; n = min(len(x), N); i = 0
    dst[i:i + n] += x[:n] * gain

def polyblep_saw(freq):
    """freq: per-sample array -> band-limited saw"""
    dt = freq / SR
    ph = np.cumsum(dt) % 1.0
    y = 2 * ph - 1
    m1 = ph < dt
    x = ph[m1] / dt[m1]; y[m1] -= x + x - x * x - 1
    m2 = ph > 1 - dt
    x = (ph[m2] - 1) / dt[m2]; y[m2] -= x * x + x + x + 1
    return y

def lp(x, fc, order=2):
    sos = signal.butter(order, min(fc, SR * 0.45), 'low', fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=0)

def hp(x, fc, order=2):
    sos = signal.butter(order, fc, 'high', fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=0)

def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], 'band', fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=0)

def sweep_lp(x, fcs, block=256):
    """time-varying lowpass (fcs per block) with state carry"""
    out = np.zeros_like(x)
    zi = None
    for k in range(0, len(x), block):
        fc = float(fcs[min(k // block, len(fcs) - 1)])
        sos = signal.butter(2, min(max(fc, 30), SR * 0.45), 'low', fs=SR, output='sos')
        if zi is None:
            zi = np.zeros((sos.shape[0], 2) + x.shape[1:])
        out[k:k + block], zi = signal.sosfilt(sos, x[k:k + block], axis=0, zi=zi)
    return out

def tt(d): return np.arange(int(d * SR)) / SR

# ------------------------------------------------------------------ drums
def kick(strength=1.0):
    t = tt(0.55)
    f = 52 + 120 * np.exp(-t / 0.028) + 30 * np.exp(-t / 0.12)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / 0.32)
    click = hp(RNG.standard_normal(len(t)), 2500) * np.exp(-t / 0.004) * 0.35
    y = np.tanh((y + click) * 1.6) * strength
    return y.astype(np.float32)

def clap():
    t = tt(0.45)
    n = RNG.standard_normal(len(t))
    e = np.zeros_like(t)
    for d in (0, 0.011, 0.022):
        e += (t >= d) * np.exp(-np.maximum(t - d, 0) / (0.006 if d < 0.02 else 0.16))
    y = bp(n, 900, 4200) * e
    body = np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.05) * 0.5
    return (y * 0.9 + body).astype(np.float32)

def hat(open_=False):
    t = tt(0.35 if open_ else 0.08)
    y = hp(RNG.standard_normal(len(t)), 7500, 4) * np.exp(-t / (0.11 if open_ else 0.022))
    return y.astype(np.float32)

def heart():
    t = tt(0.5)
    def th(d, a):
        u = np.maximum(t - d, 0)
        return np.sin(2 * np.pi * (42 + 30 * np.exp(-u / 0.03)) * u) * np.exp(-u / 0.12) * (t >= d) * a
    return lp(th(0, 1.0) + th(0.24, 0.7), 180).astype(np.float32)

def impact(strength):
    t = tt(4.0)
    f = 30 + 45 * np.exp(-t / 0.35)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 1.1)
    crash = hp(RNG.standard_normal((len(t), 2)), 3000) * np.exp(-t / 1.4)[:, None] * 0.35
    noise = lp(RNG.standard_normal((len(t), 2)), 1200) * np.exp(-t / 0.18)[:, None] * 0.6
    y = np.stack([boom, boom], 1) * 0.9 + crash + noise
    return (np.tanh(y * 1.3) * strength).astype(np.float32)

def riser(d):
    t = tt(d)
    p = t / d
    n = RNG.standard_normal((len(t), 2))
    fcs = 250 * (40 ** p[::256])
    y = sweep_lp(n, fcs) * (p ** 2.2)[:, None] * 0.55
    f = 110 * 2 ** (2.5 * p ** 1.6)
    s = polyblep_saw(f) + polyblep_saw(f * 1.01)
    s = lp(s, 3000) * (p ** 2.5) * 0.18
    y[:, 0] += s; y[:, 1] += s
    # snare roll accelerating
    k = 0.0
    while k < d:
        rate = 4 + 12 * (k / d) ** 1.5  # hits per beat -> per second scaling
        i = int(k * SR)
        c = clap()[: int(0.12 * SR)] * (0.15 + 0.6 * (k / d) ** 2)
        n2 = min(len(c), len(t) - i)
        y[i:i + n2] += c[:n2, None] * 0.6
        k += BEAT / max(1, rate / 4) / 2
    return y.astype(np.float32)

# ------------------------------------------------------------------ tonal
def pluck(freq, d=0.45, bright=1.0):
    t = tt(d)
    f = np.full(len(t), freq)
    y = polyblep_saw(f) * 0.6 + polyblep_saw(f * 1.006) * 0.4
    env = np.exp(-t / 0.13)
    # simple filter envelope: mix of bright & dark
    hi = lp(y, 1800 + 3500 * bright)
    lo = lp(y, 700)
    e2 = np.exp(-t / 0.05)
    return ((hi * e2 + lo * (1 - e2)) * env).astype(np.float32)

def bell(freq, d=2.2):
    t = tt(d)
    idx = 2.2 * np.exp(-t / 0.25)
    y = np.sin(2 * np.pi * freq * t + idx * np.sin(2 * np.pi * freq * 2 * t))
    y += 0.25 * np.sin(2 * np.pi * freq * 3.01 * t) * np.exp(-t / 0.3)
    return (y * np.exp(-t / 0.8) * np.minimum(t / 0.004, 1)).astype(np.float32)

# ------------------------------------------------------------------ build
def main(out):
    drums, bass, pad, arp, lead, fx, heartb, kickb = buf(), buf(), buf(), buf(), buf(), buf(), buf(), buf()
    K, CL, HC, HO = kick(), clap(), hat(), hat(True)
    HB = heart()
    kicks = []
    for b in range(NBARS):
        st = BAR_STYLE[b]; t0 = b * BAR
        ch = BAR_CH[b]
        root = CHORDS[ch][0]
        last_bar_of_seg = segment_at(t0 + BAR)[0] == t0 + BAR or b == NBARS - 1
        # -------- kick pattern
        if st in ('full', 'fullplus', 'grooveB2', 'alarm'):
            ks = [0, 1, 2, 3]
        elif st in ('grooveA', 'grooveA2', 'grooveA3', 'grooveB', 'tension', 'epi'):
            ks = [0, 2, 2.5] if st in ('grooveA', 'tension') else [0, 1.5, 2, 3] if st == 'grooveB' else [0, 1, 2, 3]
        elif st == 'build':
            ks = [0, 1, 2, 3]
        elif st == 'half':
            ks = [0, 2.5]
        else:
            ks = []
        kg = {'epi': 0.6, 'build': 0.75, 'grooveA': 0.85}.get(st, 1.0)
        for k in ks:
            tk = t0 + k * BEAT
            if any(a <= tk < b2 for a, b2 in DROPOUTS): continue
            add(kickb, K, tk, 0.95 * kg); kicks.append(tk)
        # -------- clap / snare
        if st in ('full', 'fullplus', 'grooveA2', 'grooveA3', 'grooveB', 'grooveB2', 'alarm', 'tension', 'build', 'epi'):
            for k in (1, 3):
                add(drums, CL, t0 + k * BEAT, 0.42 * (0.7 if st == 'epi' else 1), pan=0.05)
        if st == 'half':
            add(drums, CL, t0 + 2 * BEAT, 0.45)
        # -------- hats
        if st not in ('intro', 'break', 'break2', 'rise', 'outro'):
            sub = 4 if st in ('full', 'fullplus', 'grooveB2', 'alarm') else 2
            for k in range(4 * sub):
                tk = t0 + k * BEAT / sub
                if any(a <= tk < b2 for a, b2 in DROPOUTS): continue
                if sub == 4 and k % 4 == 2:
                    add(drums, HO, tk, 0.16, pan=0.25)
                else:
                    acc = 1.0 if (k % sub == sub // 2) else 0.55
                    add(drums, HC, tk, 0.13 * acc, pan=-0.3 + 0.6 * ((k * 7) % 5) / 4)
        # fill on the last beat of a segment
        if last_bar_of_seg and st in ('full', 'grooveA2', 'grooveB', 'grooveB2', 'grooveA3', 'tension'):
            for k in range(4):
                add(drums, CL, t0 + 3 * BEAT + k * BEAT / 4, 0.18 + 0.08 * k, pan=-0.2 + 0.13 * k)
        # -------- heartbeat
        if st in ('intro', 'break2', 'rise') and not (st == 'rise' and t0 >= 306):
            for k in (0, 2):
                tk = t0 + k * BEAT
                if any(a <= tk < b2 for a, b2 in DROPOUTS): continue
                add(heartb, HB, tk, 0.9 if st != 'rise' else 0.7)
        # -------- bass
        bm = 26 + (root - 2) % 12   # around D1..C#2 -> use octave 2
        bf = mtof(bm + 12)
        if st in ('full', 'fullplus', 'alarm', 'grooveB2'):
            pat = [(k * 0.5 + 0.0, 0.42) for k in range(8)]
        elif st in ('grooveA', 'grooveA2', 'grooveA3', 'grooveB', 'build', 'tension', 'epi'):
            pat = [(0, 0.9), (1.5, 0.4), (2, 0.9), (3.5, 0.4)] if st != 'build' else [(k * 0.5, 0.42) for k in range(8)]
        elif st == 'half':
            pat = [(0, 1.8), (2.5, 1.2)]
        elif st in ('intro', 'break', 'break2', 'outro', 'rise'):
            pat = [(0, 2.0)] if st != 'rise' else []
        else:
            pat = []
        for k, d in pat:
            tk = t0 + k * BEAT
            if any(a <= tk < b2 for a, b2 in DROPOUTS): continue
            t = tt(d * BEAT + 0.05)
            env = np.minimum(t / 0.004, 1) * np.clip((d * BEAT + 0.05 - t) / 0.04, 0, 1)
            sub_ = np.sin(2 * np.pi * bf * t)
            grit = lp(polyblep_saw(np.full(len(t), bf)), 420 + 900 * ENERGY_OF[st])
            y = (sub_ * 0.6 + grit * 0.5 + np.sin(4 * np.pi * bf * t) * 0.18) * env
            g = 0.55 if st not in ('intro', 'break', 'break2', 'outro') else 0.35
            add(bass, y.astype(np.float32), tk, g)
        # -------- arp
        if st in ('grooveA', 'grooveA2', 'grooveA3', 'grooveB', 'grooveB2', 'full', 'fullplus', 'build', 'tension',
                  'alarm', 'epi', 'break'):
            notes = voicing(ch, 62, 7)
            order = [0, 2, 4, 6, 5, 3, 1, 3]
            rate = 4 if st in ('full', 'fullplus', 'grooveB2', 'alarm', 'build', 'epi') else 2
            for k in range(4 * rate):
                tk = t0 + k * BEAT / rate
                if any(a <= tk < b2 for a, b2 in DROPOUTS): continue
                m = notes[order[k % len(order)]]
                br = 0.25 + 0.75 * ENERGY_OF[st]
                if st == 'build':
                    s0 = segment_at(t0)
                    br = 0.15 + 0.85 * (t0 - s0[0]) / (s0[1] - s0[0])
                g = 0.11 if st != 'break' else 0.07
                add(arp, pluck(mtof(m), 0.4, br), tk, g * (1.0 if k % rate == 0 else 0.75), pan=0.5 * math.sin(k * 1.3))
        # -------- lead bell melody
        if st in ('full', 'fullplus', 'grooveA3', 'break', 'epi', 'outro', 'intro') and t0 >= 4:
            ci = PROG[segment_at(t0)[3]].index(ch) if ch in PROG[segment_at(t0)[3]] else 0
            mel = MELODY.get((segment_at(t0)[3], ci), [])
            if st in ('intro', 'outro'):
                mel = mel[:1]
            for k, m in enumerate(mel):
                if m is None: continue
                tk = t0 + k * BEAT / 2
                if any(a <= tk < b2 for a, b2 in DROPOUTS): continue
                g = 0.16 if st in ('full', 'fullplus') else 0.13
                add(lead, bell(mtof(m)), tk, g, pan=0.15 * math.sin(k))
                if st == 'fullplus':
                    add(lead, bell(mtof(m + 12), 1.2), tk, 0.05, pan=-0.3)

    # -------- pads (continuous supersaw, voice-led)
    print('pads...', flush=True)
    vo = []
    prev = None
    for b in range(NBARS):
        v = voicing(BAR_CH[b], 50, 4)
        if prev is not None:   # pick inversion closest to previous
            best = None
            for lo in range(45, 60):
                c = voicing(BAR_CH[b], lo, 4)
                d = sum(abs(x - y) for x, y in zip(c, prev))
                if best is None or d < best[0]: best = (d, c)
            v = best[1]
        vo.append(v); prev = v
    ns = int(NBARS * BAR * SR)
    tb = np.arange(ns) / SR
    bi = np.minimum((tb / BAR).astype(int), NBARS - 1)
    padL = np.zeros(ns, np.float32); padR = np.zeros(ns, np.float32)
    det = [-0.21, -0.13, -0.05, 0.0, 0.06, 0.14, 0.2]
    for vi in range(4):
        mids = np.array([vo[b][vi] for b in range(NBARS)], np.float64)
        f0 = mtof(mids)[bi]
        # 25ms glide
        f0 = signal.lfilter([1 - 0.999], [1, -0.999], f0, zi=[f0[0] * 0.999])[0]
        for j, d in enumerate(det):
            s = polyblep_saw(f0 * 2 ** (d / 12)).astype(np.float32)
            if j % 2: padL += s * 0.6; padR += s * 0.4
            else: padL += s * 0.4; padR += s * 0.6
        print(' voice', vi, flush=True)
    P = np.stack([padL, padR], 1) / 14
    # pad level & brightness follow the energy curve
    lev = np.array([{'intro': .55, 'rise': .6, 'break': .7, 'break2': .45, 'outro': .7, 'epi': .75}.get(BAR_STYLE[b], .5)
                    for b in range(NBARS)])
    cut = np.array([{'intro': 700, 'rise': 900, 'break': 1400, 'break2': 600, 'outro': 1200, 'epi': 2400,
                     'full': 3600, 'fullplus': 4500, 'alarm': 2000, 'tension': 1100}.get(BAR_STYLE[b], 1800) for b in range(NBARS)])
    blk = np.arange(0, ns, 256) / SR
    cblk = np.interp(blk, np.arange(NBARS) * BAR + 0.3, cut)
    # rising filter during risers
    for a, b2 in RISERS:
        m = (blk >= a) & (blk < b2)
        cblk[m] *= 1 + 4 * ((blk[m] - a) / (b2 - a)) ** 2
    P = sweep_lp(P, cblk)
    lv = np.interp(tb, np.arange(NBARS) * BAR + 0.4, lev)[:, None]
    lv *= np.minimum(tb / 4.0, 1)[:, None]   # fade-in at the start
    pad[:ns] += (P * lv).astype(np.float32)

    # -------- fx
    for a, b2 in RISERS:
        add(fx, riser(b2 - a), a, 0.55)
    for ti, k, _ in IMPACTS:
        add(fx, impact(k), ti, 0.75)
        # sub drop
        t = tt(1.4)
        add(fx, (np.sin(2 * np.pi * np.cumsum(70 * np.exp(-t / 0.5) + 28) / SR) * np.exp(-t / 0.6) * k).astype(np.float32),
            ti, 0.5)
    # alarm stabs (山姆争议段)
    for b in range(NBARS):
        if BAR_STYLE[b] == 'alarm':
            for k in (0, 1.5, 3):
                t = tt(0.35)
                y = (polyblep_saw(np.full(len(t), mtof(62))) + polyblep_saw(np.full(len(t), mtof(63)))) * np.exp(-t / 0.12)
                add(fx, lp(y, 2500).astype(np.float32), b * BAR + k * BEAT, 0.09, pan=-0.4 if k else 0.4)

    # -------- sidechain
    sc = np.ones(N, np.float32)
    tk = np.array(kicks)
    idx = np.arange(N) / SR
    j = np.searchsorted(tk, idx, 'right') - 1
    dtk = np.where(j >= 0, idx - tk[np.maximum(j, 0)], 9)
    sc = (1 - 0.65 * np.exp(-dtk / 0.11)).astype(np.float32)[:, None]

    # -------- delays & reverb
    def delay(x, d, fb=0.35, wet=0.3, pingpong=True):
        n = int(d * SR)
        y = np.zeros_like(x)
        tap = x.copy()
        for k in range(1, 6):
            tap = np.roll(tap, n, axis=0); tap[:n] = 0
            tap = lp(tap, 4000) * fb if k > 1 else tap * fb
            if pingpong and k % 2: y += tap[:, ::-1]
            else: y += tap
        return x + y * wet / fb

    print('fx chain...', flush=True)
    arp = delay(arp, 3 * BEAT / 4, 0.4, 0.45)
    lead = delay(lead, 3 * BEAT / 2, 0.35, 0.35)
    ir_t = tt(3.2)
    ir = RNG.standard_normal((len(ir_t), 2)) * np.exp(-ir_t / 0.75)[:, None]
    ir = lp(ir, 6000); ir[:int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))[:, None]
    ir /= np.sqrt((ir ** 2).sum(0))
    send = pad * 0.25 + arp * 0.5 + lead * 0.7 + drums * 0.06 + fx * 0.35 + heartb * 0.2
    send = hp(send, 200)
    rev = np.stack([signal.fftconvolve(send[:, c], ir[:, c])[:N] for c in range(2)], 1).astype(np.float32)

    mix = (kickb * 0.6 + drums * 1.15 + heartb * 0.9 + bass * sc * 0.6 + pad * sc * 1.25 + arp * sc * 1.35 + lead * 1.2 + fx * 0.75
           + rev * 0.55)
    # dropouts: duck everything except fx/rev briefly
    for a, b2 in DROPOUTS:
        i0, i1 = int(a * SR), int(b2 * SR)
        mix[i0:i1] = mix[i0:i1] * 0.25 + (fx[i0:i1] * 0.8 + rev[i0:i1] * 0.5) * 0.75
    mix = hp(mix, 28)
    # master: gentle glue + soft clip
    pk = np.abs(mix).max()
    mix = mix / pk * 1.6
    mix = np.tanh(mix) / np.tanh(1.6)
    L = int(DUR * SR)
    mix = mix[:L]
    fo = int(5.0 * SR)
    mix[-fo:] *= (np.linspace(1, 0, fo) ** 1.6)[:, None]
    mix = mix / np.abs(mix).max() * 0.89
    sf.write(out, mix.astype(np.float32), SR, subtype='PCM_16')
    rms = [20 * np.log10(np.sqrt((mix[int(a * SR):int(b * SR)] ** 2).mean()) + 1e-9) for a, b, *_ in SEGMENTS]
    for s, r in zip(SEGMENTS, rms):
        print(f'{s[0]:6.1f}-{s[1]:6.1f} {s[2]:9s} {r:6.1f} dBFS')

# bell melodies: (progression, chord index) -> 8 eighth notes
MELODY = {
    ('A', 0): [69, None, 74, None, 77, None, 76, 74],
    ('A', 1): [74, None, None, 72, 74, None, 77, None],
    ('A', 2): [77, None, 76, None, 72, None, 69, None],
    ('A', 3): [72, None, None, None, 76, None, 74, None],
    ('B', 0): [74, None, 77, None, None, None, 74, None],
    ('B', 1): [72, None, None, 69, None, None, None, None],
    ('B', 2): [76, None, 79, None, 76, None, 72, None],
    ('B', 3): [74, None, None, None, None, None, None, None],
    ('E', 0): [74, None, 77, None, 81, None, None, 79],
    ('E', 1): [77, None, None, 76, 77, None, 72, None],
    ('E', 2): [76, None, 79, None, 84, None, 81, None],
    ('E', 3): [81, None, None, 77, 74, None, None, None],
    ('Z', 0): [74, None, None, None, None, None, None, None],
    ('Z', 1): [72, None, None, None, None, None, None, None],
    ('Z', 2): [70, None, None, None, None, None, None, None],
    ('Z', 3): [69, None, None, None, 74, None, None, None],
}

if __name__ == '__main__':
    main(sys.argv[1])
