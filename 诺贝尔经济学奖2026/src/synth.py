"""小型合成器：振荡器、时变滤波器（numba）、包络、混响和各类乐器。全部 numpy 生成，无外部采样。"""
import math
import numpy as np
from numba import njit
from scipy import signal

SR = 48000
RNG = np.random.default_rng(2026)


def S(t):
    return int(round(t * SR))


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


# ---------------------------------------------------------------- 振荡器
def phase_of(freq, n, ph0=0.0):
    f = np.broadcast_to(np.asarray(freq, np.float64), (n,))
    return (ph0 + np.cumsum(f) / SR) % 1.0, f / SR


def saw(freq, n, ph0=None):
    """PolyBLEP 带限锯齿"""
    if ph0 is None:
        ph0 = RNG.random()
    ph, dt = phase_of(freq, n, ph0)
    y = 2 * ph - 1
    m = ph < dt
    x = ph[m] / dt[m]
    y[m] -= x + x - x * x - 1
    m = ph > 1 - dt
    x = (ph[m] - 1) / dt[m]
    y[m] -= x * x + x + x + 1
    return y


def sine(freq, n, ph0=0.0):
    f = np.broadcast_to(np.asarray(freq, np.float64), (n,))
    return np.sin(2 * np.pi * (ph0 + np.cumsum(f) / SR))


def tri(freq, n, ph0=None):
    if ph0 is None:
        ph0 = RNG.random()
    ph, _ = phase_of(freq, n, ph0)
    return 4 * np.abs(ph - 0.5) - 1


def noise(n):
    return RNG.standard_normal(n)


# ---------------------------------------------------------------- 滤波器
@njit(cache=True)
def _svf(x, fc, q, mode):
    """TPT 状态变量滤波器（Zavalishin），fc 可逐点变化。mode 0=LP 1=BP 2=HP"""
    n = x.shape[0]
    y = np.empty(n)
    ic1 = 0.0
    ic2 = 0.0
    k = 1.0 / q
    for i in range(n):
        f = fc[i]
        if f > 20000.0:
            f = 20000.0
        if f < 10.0:
            f = 10.0
        g = math.tan(math.pi * f / 48000.0)
        a1 = 1.0 / (1.0 + g * (g + k))
        a2 = g * a1
        a3 = g * a2
        v3 = x[i] - ic2
        v1 = a1 * ic1 + a2 * v3
        v2 = ic2 + a2 * ic1 + a3 * v3
        ic1 = 2.0 * v1 - ic1
        ic2 = 2.0 * v2 - ic2
        if mode == 0:
            y[i] = v2
        elif mode == 1:
            y[i] = v1
        else:
            y[i] = x[i] - k * v1 - v2
    return y


def svf(x, fc, q=0.707, mode='lp'):
    fc = np.broadcast_to(np.asarray(fc, np.float64), (len(x),)).copy()
    m = {'lp': 0, 'bp': 1, 'hp': 2}[mode]
    if x.ndim == 2:
        return np.stack([_svf(np.ascontiguousarray(x[:, c]), fc, q, m) for c in range(x.shape[1])], 1)
    return _svf(np.ascontiguousarray(x, dtype=np.float64), fc, q, m)


def lp(x, fc, order=2):
    sos = signal.butter(order, min(fc, SR * 0.45), 'low', fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=0)


def hp(x, fc, order=2):
    sos = signal.butter(order, fc, 'high', fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=0)


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, min(hi, SR * 0.45)], 'band', fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=0)


def shelf_high(x, fc, gain_db):
    """简单高架：用高通分量加减"""
    return x + (10 ** (gain_db / 20) - 1) * hp(x, fc, 1)


# ---------------------------------------------------------------- 包络
def adsr(n, a, d, s, r, hold=None):
    """hold = 按住的秒数（到 release 开始）；n 为总采样数"""
    t = np.arange(n) / SR
    if hold is None:
        hold = n / SR - r
    e = np.where(t < a, t / max(a, 1e-4),
                 np.where(t < a + d, 1 - (1 - s) * (t - a) / max(d, 1e-4), s))
    rel = t > hold
    if rel.any():
        lvl = np.interp(hold, t, e)
        e[rel] = lvl * np.exp(-(t[rel] - hold) / max(r / 4.6, 1e-4))
    return e


def fade(x, fi=0.005, fo=0.02):
    n = len(x)
    a, b = min(S(fi), n), min(S(fo), n)
    e = np.ones(n)
    if a > 0:
        e[:a] = np.sin(np.linspace(0, np.pi / 2, a)) ** 2
    if b > 0:
        e[n - b:] *= np.cos(np.linspace(0, np.pi / 2, b)) ** 2
    return x * (e[:, None] if x.ndim == 2 else e)


def pan(x, p):
    """等功率声像，p∈[-1,1]"""
    l, r = math.cos((p + 1) * math.pi / 4), math.sin((p + 1) * math.pi / 4)
    return np.stack([x * l, x * r], 1) * 1.41421356


# ---------------------------------------------------------------- 混响
def make_ir(t60=2.6, pre=0.02, n_er=18, damp0=9000, damp1=1800, seed=1, width=1.0):
    r = np.random.default_rng(seed)
    n = S(t60 * 1.15)
    t = np.arange(n) / SR
    out = np.zeros((n + S(pre), 2))
    for c in range(2):
        x = r.standard_normal(n) * np.exp(-6.91 * t / t60)
        fc = damp1 + (damp0 - damp1) * np.exp(-t / (t60 * 0.25))
        x = _svf(x, fc, 0.6, 0)
        x[:S(0.004)] *= np.linspace(0, 1, S(0.004))
        out[S(pre):, c] = x
        # 早期反射
        for _ in range(n_er):
            d = S(pre + r.random() * 0.07)
            out[d, c] += (r.random() * 2 - 1) * 0.9 * (1 - (d / SR) / 0.1)
    # 立体声宽度
    m = (out[:, 0] + out[:, 1]) / 2
    s = (out[:, 0] - out[:, 1]) / 2 * width
    out = np.stack([m + s, m - s], 1)
    return out / np.sqrt((out ** 2).sum() / 2)


def convolve(x, ir):
    y = np.stack([signal.fftconvolve(x[:, c], ir[:, c])[:len(x)] for c in range(2)], 1)
    return y


# ---------------------------------------------------------------- 乐器
def supersaw(m, dur, voices=5, detune=12.0, sub=0.35):
    n = S(dur)
    y = np.zeros((n, 2))
    for k in range(voices):
        c = (k - (voices - 1) / 2) / ((voices - 1) / 2) if voices > 1 else 0
        f = mtof(m) * 2 ** (c * detune / 1200)
        y += pan(saw(f, n), c * 0.8) / voices
    if sub:
        y += pan(sine(mtof(m - 12), n), 0) * sub
    return y


def pad_chord(notes, dur, cut=1800, att=0.5, rel=0.8, detune=11.0, voices=5, cut_end=None, q=0.8):
    n = S(dur + rel)
    y = np.zeros((n, 2))
    for m in notes:
        y += supersaw(m, dur + rel, voices, detune, sub=0.0)
    fc = cut if cut_end is None else np.linspace(cut, cut_end, n)
    y = svf(y, fc, q, 'lp')
    e = adsr(n, att, 0.3, 0.9, rel, hold=dur)
    return y * e[:, None] / max(len(notes), 1) ** 0.5


def strings(notes, dur, att=0.35, rel=0.9, cut=3200, vib=5.2):
    n = S(dur + rel)
    t = np.arange(n) / SR
    y = np.zeros((n, 2))
    for i, m in enumerate(notes):
        for k in range(3):
            v = 1 + 0.0035 * np.sin(2 * np.pi * (vib + 0.3 * k) * t + RNG.random() * 6) * np.clip(t / 0.6, 0, 1)
            f = mtof(m) * 2 ** ((k - 1) * 7 / 1200) * v
            y += pan(saw(f, n), (k - 1) * 0.6 + (i - len(notes) / 2) * 0.08)
    y = svf(y, cut, 0.7, 'lp')
    y = hp(y, 180, 1)
    e = adsr(n, att, 0.2, 0.92, rel, hold=dur)
    return y * e[:, None] / (3 * max(len(notes), 1) ** 0.6)


_PIANO = {}


def piano_note(m, vel=0.7, dur=2.0, bright=0.6):
    """加法合成钢琴（偏柔的 felt piano）：非谐泛音 + 双段衰减 + 弦间微失谐 + 槌击噪声"""
    key = (m, round(vel, 2), round(dur, 1), round(bright, 2))
    if key in _PIANO:
        return _PIANO[key]
    f0 = mtof(m)
    T = dur + 1.6
    n = S(T)
    t = np.arange(n) / SR
    y = np.zeros(n)
    B = 0.00025 * (m / 60) ** 2
    nmax = int(min(24, 16000 / f0))
    t1 = 3.2 * (60 / m) ** 1.5 + 0.6          # 基音衰减（秒）
    for k in range(1, nmax + 1):
        fk = f0 * k * math.sqrt(1 + B * k * k)
        amp = (1 / k ** (1.35 - 0.5 * bright * vel)) * (0.6 + 0.4 * vel)
        tau = t1 / (k ** 0.75)
        env = 0.55 * np.exp(-t / (tau * 0.18)) + 0.45 * np.exp(-t / tau)
        for d in (-0.6, 0.6):                    # 两根弦
            y += amp * env * np.sin(2 * np.pi * fk * (1 + d * 0.0006) * t + RNG.random() * 6)
    y *= 0.5
    ham = lp(noise(S(0.012)), 2500 + 2000 * vel) * np.exp(-np.arange(S(0.012)) / S(0.003)) * 0.25 * vel
    y[:len(ham)] += ham
    # 抬键
    rel = np.ones(n)
    k0 = S(dur)
    if k0 < n:
        rel[k0:] = np.exp(-(t[k0:] - dur) / 0.25)
    y *= rel
    y = lp(y, 2600 + 6500 * bright * vel, 2)
    att = np.clip(t / 0.004, 0, 1)
    y *= att
    _PIANO[key] = y
    return y


def bell(m, dur=2.5, bright=1.0):
    f0 = mtof(m)
    n = S(dur)
    t = np.arange(n) / SR
    ratios = [1.0, 2.0, 2.76, 3.0, 4.07, 5.4, 6.8]
    amps = [1.0, 0.45, 0.5, 0.25, 0.22, 0.14, 0.08]
    y = np.zeros(n)
    for r_, a_ in zip(ratios, amps):
        if f0 * r_ > 15000:
            continue
        y += a_ * bright ** (r_ / 3) * np.sin(2 * np.pi * f0 * r_ * t) * np.exp(-t / (dur * 0.35 / r_ ** 0.6))
    y *= np.clip(t / 0.002, 0, 1)
    return y * 0.4


def pluck(m, dur=0.25, cut0=5000, cut1=500, decay=0.18, wave='saw'):
    n = S(dur + 0.3)
    t = np.arange(n) / SR
    f = mtof(m)
    x = saw(f, n) * 0.7 + saw(f * 1.004, n) * 0.3 if wave == 'saw' else tri(f, n)
    fc = cut1 + (cut0 - cut1) * np.exp(-t / 0.07)
    y = _svf(x, fc, 1.1, 0)
    e = np.exp(-t / decay) * np.clip(t / 0.002, 0, 1)
    e[S(dur):] *= np.exp(-(t[S(dur):] - dur) / 0.04)
    return y * e


def pizz(m, vel=0.8):
    n = S(0.5)
    t = np.arange(n) / SR
    f = mtof(m)
    x = saw(f, n) + 0.5 * saw(2 * f, n)
    y = _svf(x, 600 + 3000 * vel * np.exp(-t / 0.05), 0.9, 0)
    return y * np.exp(-t / 0.13) * np.clip(t / 0.003, 0, 1) * vel


def bass_note(m, dur, cut=420, drive=1.6):
    n = S(dur + 0.05)
    t = np.arange(n) / SR
    f = mtof(m)
    y = 0.75 * sine(f, n) + 0.35 * _svf(saw(f, n), np.full(n, cut) * (1 + 1.5 * np.exp(-t / 0.05)), 0.9, 0)
    y = np.tanh(y * drive) / np.tanh(drive)
    e = np.clip(t / 0.006, 0, 1) * np.exp(-t / (dur * 2.5))
    e[S(dur):] *= np.exp(-(t[S(dur):] - dur) / 0.03)
    return y * e


def sub_note(m, dur):
    n = S(dur)
    t = np.arange(n) / SR
    return sine(mtof(m), n) * np.clip(t / 0.01, 0, 1) * np.clip((dur - t) / 0.08, 0, 1)


# ---------------------------------------------------------------- 打击乐
def kick(power=1.0, length=0.45, f_hi=110, f_lo=44, tone=1.0):
    n = S(length)
    t = np.arange(n) / SR
    f = f_lo + (f_hi - f_lo) * np.exp(-t / 0.035)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (length * 0.45))
    click = lp(noise(n), 4000) * np.exp(-t / 0.004) * 0.35
    y = np.tanh((body * tone + click) * 1.8 * power) * 0.9
    return y


def snare(power=1.0, length=0.35, bright=0.6):
    n = S(length)
    t = np.arange(n) / SR
    nz = bp(noise(n), 900, 4500 + 3000 * bright) * np.exp(-t / 0.09)
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.05) * 0.6
    return np.tanh((nz * 0.9 + tone) * 1.5 * power) * 0.8


def clap(power=1.0):
    n = S(0.3)
    t = np.arange(n) / SR
    e = np.zeros(n)
    for d in (0.0, 0.011, 0.022, 0.034):
        e += np.where(t >= d, np.exp(-(t - d) / 0.012), 0)
    e += np.exp(-t / 0.11) * 0.6
    return bp(noise(n), 900, 3800) * e * 0.55 * power


def hat(power=1.0, length=0.06, open_=False):
    n = S(0.4 if open_ else length * 2)
    t = np.arange(n) / SR
    y = hp(noise(n), 7000, 2) * np.exp(-t / (0.12 if open_ else length * 0.45))
    return lp(y, 12000) * 0.35 * power


def shaker(power=1.0):
    n = S(0.12)
    t = np.arange(n) / SR
    e = np.clip(t / 0.02, 0, 1) * np.exp(-t / 0.03)
    return bp(noise(n), 4000, 9000) * e * 0.25 * power


def tick(freq=2600, power=1.0):
    n = S(0.07)
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.008) + 0.5 * np.sin(2 * np.pi * freq * 1.52 * t) * np.exp(-t / 0.005)
    y += bp(noise(n), freq * 0.7, freq * 1.6) * np.exp(-t / 0.003) * 0.6
    return y * 0.35 * power


def tom(m=45, power=1.0, length=0.8):
    n = S(length)
    t = np.arange(n) / SR
    f0 = mtof(m)
    f = f0 * (1 + 0.6 * np.exp(-t / 0.04))
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (length * 0.35))
    y += lp(noise(n), 1500) * np.exp(-t / 0.02) * 0.2
    return np.tanh(y * 1.5 * power) * 0.8


def timpani_roll(m=38, dur=2.0, power=1.0):
    """定音鼓滚奏：密集小击 + 渐强"""
    n = S(dur + 1.5)
    y = np.zeros(n)
    k = 0.0
    while k < dur:
        a = (k / dur) ** 1.6 * 0.8 + 0.2
        h = tom(m, power * a * 0.5, 1.2)
        i = S(k)
        j = min(n, i + len(h))
        y[i:j] += h[:j - i] * (0.8 + 0.4 * RNG.random())
        k += 0.045 + 0.01 * RNG.random()
    return y * 0.5


# ---------------------------------------------------------------- 音效（全部偏低频、柔和）
def boom(power=1.0, length=3.2, f0=58, f1=28):
    n = S(length)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.25)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (length * 0.32))
    nz = lp(noise(n), 900) * np.exp(-t / 0.18) * 0.5
    y = np.tanh((y + nz) * 2.2 * power) * 0.8
    return lp(y, 2200)


def subdrop(length=1.4, f0=80, f1=26, power=1.0):
    n = S(length)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * (1 - t / length) ** 2
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.clip(t / 0.01, 0, 1) * (1 - t / length) ** 1.2 * power


def braam(root=26, length=2.6, power=1.0):
    """低沉铜管式「braam」：多层锯齿 + 快速打开的低通 + 饱和"""
    n = S(length)
    t = np.arange(n) / SR
    y = np.zeros((n, 2))
    for m, a in ((root, 1.0), (root + 12, 0.8), (root + 19, 0.5), (root + 24, 0.35)):
        y += supersaw(m, length, voices=4, detune=18, sub=0) * a
    fc = 150 + 1800 * np.clip(t / 0.25, 0, 1) * np.exp(-t / 1.2)
    y = svf(y, fc, 1.2, 'lp')
    e = np.clip(t / 0.04, 0, 1) * np.exp(-t / (length * 0.45))
    return np.tanh(y * e[:, None] * 2.5 * power) * 0.5


def riser(length=4.0, m0=50, m1=74, power=1.0):
    """音高上滑的锯齿簇 + 打开的滤波 + 末端渐强（不用白噪声）"""
    n = S(length)
    t = np.arange(n) / SR
    u = t / length
    y = np.zeros((n, 2))
    for k, dm in enumerate((0, 7, 12, 19)):
        f = mtof(m0 + dm + (m1 - m0) * u ** 1.8)
        y += pan(saw(f, n), (k - 1.5) * 0.4)
    y = svf(y, 300 + 6000 * u ** 2.2, 1.4, 'lp')
    return y * (u ** 2.4)[:, None] * 0.25 * power


def reverse_swell(length=2.0, cut=5000, power=1.0):
    """反向镲片式渐强（低通，避免刺耳）"""
    n = S(length)
    t = np.arange(n) / SR
    u = t / length
    x = noise(n)
    y = _svf(x, 600 + cut * u ** 2, 0.7, 0)
    return y * u ** 3 * 0.3 * power


def crystal(length=1.6, power=1.0, base=84):
    """碎裂的晶体：一簇快速衰减的高音铃（柔和的「破碎」）"""
    n = S(length)
    y = np.zeros((n, 2))
    for _ in range(26):
        m = base + RNG.integers(-12, 14)
        d = RNG.random() * 0.35
        b = bell(m, 0.9 + RNG.random() * 0.6, 0.8)
        i = S(d)
        j = min(n, i + len(b))
        y[i:j] += pan(b[:j - i], RNG.random() * 1.6 - 0.8) * (0.25 + 0.3 * RNG.random()) * (1 - d * 1.8)
    return y * power


def shimmer(length=2.0, base=86, power=1.0, notes=(0, 4, 7, 11, 12, 16, 19, 24)):
    n = S(length + 2.0)
    y = np.zeros((n, 2))
    for k, iv in enumerate(notes):
        d = k * length / len(notes)
        b = bell(base + iv, 2.0, 1.0)
        i = S(d)
        j = min(n, i + len(b))
        y[i:j] += pan(b[:j - i], math.sin(k * 1.7) * 0.7) * 0.35
    return y * power
