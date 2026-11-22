"""合成乐器：每个函数返回 float32 数组（单声道 n 或立体声 n×2）。"""
import numpy as np
from dsp import (SR, saw, square, sine, noise, lp, hp, bp, svf, env_adsr, tanh_sat, midi, sos_filter)

RNG = np.random.default_rng(7)


def _t(n):
    return np.arange(n, dtype=np.float32) / SR


def _f(x):
    return np.atleast_1d(np.asarray(x, np.float32))


# ---------------------------------------------------------------- drums
def kick(vel=1.0, tight=1.0, sub=1.0):
    n = int(0.55 * SR)
    t = _t(n)
    f = 44 + 120 * np.exp(-t / (0.028 * tight)) + 30 * np.exp(-t / 0.18)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR)
    amp = np.exp(-t / (0.30 * sub)) * np.minimum(t / 0.0015, 1)
    click = hp(noise(n, 3), 2500) * np.exp(-t / 0.004) * 0.35
    k = tanh_sat(body * amp * 1.25 + click, 1.6) * vel
    return k


def snare(vel=1.0):
    n = int(0.45 * SR)
    t = _t(n)
    body = (np.sin(2 * np.pi * 185 * t) * 0.7 + np.sin(2 * np.pi * 330 * t) * 0.35) * np.exp(-t / 0.07)
    nz = bp(noise(n, 11), 3500, 0.6) * np.exp(-t / 0.16) * 1.1
    nz += hp(noise(n, 12), 6000) * np.exp(-t / 0.05) * 0.5
    return tanh_sat((body + nz) * 0.8, 1.3) * vel


def clap(vel=1.0):
    n = int(0.5 * SR)
    t = _t(n)
    nz = bp(noise(n, 21), 1600, 0.9)
    env = np.zeros(n, np.float32)
    for k, d in enumerate([0.0, 0.009, 0.019, 0.031]):
        tt = t - d
        env += np.where(tt >= 0, np.exp(-np.maximum(tt, 0) / (0.008 if k < 3 else 0.14)), 0)
    return tanh_sat(nz * env * 1.6, 1.2) * vel


def hat(vel=1.0, open_=False):
    n = int((0.35 if open_ else 0.08) * SR)
    t = _t(n)
    # 808 式金属音：6 个方波
    m = np.zeros(n, np.float32)
    for f in (205.3, 304.4, 369.6, 522.7, 540.0, 800.0):
        m += square(_f(f * 2.2), n, RNG.random())
    m = hp(bp(m, 9000, 0.8), 7000) * 0.25 + hp(noise(n, 31), 8000) * 0.6
    return m * np.exp(-t / (0.11 if open_ else 0.022)) * vel


def shaker(vel=1.0):
    n = int(0.09 * SR)
    t = _t(n)
    env = np.minimum(t / 0.02, 1) * np.exp(-t / 0.03)
    return hp(noise(n, 41), 5000) * env * vel


def crash(vel=1.0, dur=2.6):
    n = int(dur * SR)
    t = _t(n)
    out = np.zeros((n, 2), np.float32)
    for c in range(2):
        m = np.zeros(n, np.float32)
        for f in (311, 457, 598, 803, 1123, 1489):
            m += square(_f(f * (1.6 + 0.03 * c)), n, RNG.random())
        s = hp(noise(n, 50 + c), 3500) * 0.8 + hp(m, 4000) * 0.12
        out[:, c] = s * (np.exp(-t / (dur * 0.28)) * 0.85 + 0.15 * np.exp(-t / 0.05)) * np.minimum(t / 0.002, 1)
    return out * vel


def taiko(vel=1.0, pitch=1.0):
    n = int(1.2 * SR)
    t = _t(n)
    f = (62 + 40 * np.exp(-t / 0.03)) * pitch
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.42)
    skin = lp(noise(n, 61), 900) * np.exp(-t / 0.06) * 1.5
    slap = bp(noise(n, 62), 2200, 1.2) * np.exp(-t / 0.012) * 0.5
    return tanh_sat((body + skin + slap) * 0.9, 1.4) * vel


def tom(vel=1.0, f0=110):
    n = int(0.6 * SR)
    t = _t(n)
    f = f0 * (1 + 0.5 * np.exp(-t / 0.04))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.22)
    return tanh_sat(body + lp(noise(n, 71), 1500) * np.exp(-t / 0.03) * 0.4, 1.2) * vel


# ---------------------------------------------------------------- tonal
def supersaw(freq, dur, voices=7, detune=0.16, cutoff=3000, attack=0.35, release=1.2, q=0.8, seed=0, bright_env=None):
    """立体声超级锯齿 pad"""
    n = int((dur + release) * SR)
    out = np.zeros((n, 2), np.float32)
    rng = np.random.default_rng(seed)
    for v in range(voices):
        d = (v - (voices - 1) / 2) / ((voices - 1) / 2) if voices > 1 else 0
        cents = d * detune * 100 * (0.5 + 0.5 * abs(d))
        f = freq * 2 ** (cents / 1200)
        s = saw(_f(f), n, rng.random())
        p = 0.5 + 0.45 * d
        out[:, 0] += s * np.cos(p * np.pi / 2)
        out[:, 1] += s * np.sin(p * np.pi / 2)
    out /= np.sqrt(voices)
    env = env_adsr(n, attack, 0.5, 0.85, release, hold=dur)
    cut = cutoff if bright_env is None else bright_env(n)
    for c in range(2):
        out[:, c] = svf(out[:, c], _f(cut), q, 0) * env
    return out


def pluck(freq, vel=1.0, decay=0.28, cut0=5500, cut1=500, wave='saw', seed=0):
    n = int((decay * 2.5 + 0.05) * SR)
    t = _t(n)
    if wave == 'saw':
        s = saw(_f(freq), n, 0.0) * 0.6 + saw(_f(freq * 1.004), n, 0.3) * 0.5
    else:
        s = square(_f(freq), n, 0.0, 0.3) * 0.6 + saw(_f(freq * 2.0), n, 0.1) * 0.2
    cut = cut1 + (cut0 - cut1) * np.exp(-t / (decay * 0.35))
    s = svf(s, cut.astype(np.float32), 1.1, 0)
    return s * np.exp(-t / decay) * np.minimum(t / 0.002, 1) * vel


def piano(freq, vel=1.0, dur=2.0):
    n = int((dur + 1.5) * SR)
    t = _t(n)
    out = np.zeros(n, np.float32)
    B = 0.00035
    tau0 = 2.8 * (220 / freq) ** 0.45
    for k in range(1, 14):
        fk = freq * k * np.sqrt(1 + B * k * k)
        if fk > 16000: break
        a = (1 / k ** 1.25) * (1.0 if k < 3 else (0.6 + 0.4 * vel))
        tau = tau0 / (1 + 0.45 * (k - 1))
        for dtn in (-0.7, 0.7):  # 双弦微失谐
            out += a * 0.5 * np.sin(2 * np.pi * fk * (1 + dtn * 0.0004) * t + RNG.random() * 6.28) * np.exp(-t / tau)
    damp = np.where(t > dur, np.exp(-(t - dur) / 0.25), 1.0)
    hammer = bp(noise(n, 81), freq * 4, 1.5) * np.exp(-t / 0.006) * 0.15
    s = (out * damp + hammer) * np.minimum(t / 0.003, 1)
    return s * vel * 0.35


def bell(freq, vel=1.0, dur=2.5, ratio=3.5, index=3.0):
    n = int(dur * SR)
    t = _t(n)
    I = index * np.exp(-t / 0.35) + 0.4
    mod = np.sin(2 * np.pi * freq * ratio * t) * I
    s = np.sin(2 * np.pi * freq * t + mod) * np.exp(-t / (dur * 0.35))
    s += 0.25 * np.sin(2 * np.pi * freq * 2 * t) * np.exp(-t / (dur * 0.15))
    return s * np.minimum(t / 0.001, 1) * vel * 0.4


def string_stab(freq, vel=1.0, dur=0.16):
    n = int((dur + 0.25) * SR)
    t = _t(n)
    s = sum(saw(_f(freq * 2 ** (c / 1200)), n, RNG.random()) for c in (-9, 0, 8)) / 3
    s = lp(s, 2800, 0.7)
    env = np.minimum(t / 0.004, 1) * np.where(t < dur, np.exp(-t / 0.12), np.exp(-dur / 0.12) * np.exp(-(t - dur) / 0.05))
    return s * env * vel


def braam(freq, vel=1.0, dur=3.0):
    """低音铜管式 Braam：失真的失谐锯齿 + 滤波器打开"""
    n = int(dur * SR)
    t = _t(n)
    out = np.zeros((n, 2), np.float32)
    cut = 120 + 2200 * (1 - np.exp(-t / 0.12)) * np.exp(-t / 1.3) + 200
    for c in range(2):
        s = np.zeros(n, np.float32)
        for k, (mult, cents) in enumerate([(1, -14), (1, 11), (2, -6), (2, 7), (0.5, 0), (1.5, 3)]):
            s += saw(_f(freq * mult * 2 ** ((cents + 4 * c) / 1200)), n, RNG.random()) * (0.6 if mult == 0.5 else 1)
        s = tanh_sat(s * 0.6, 2.2)
        s = svf(s, cut.astype(np.float32), 1.0, 0)
        out[:, c] = s
    env = np.minimum(t / 0.04, 1) * np.exp(-t / (dur * 0.45))
    return out * env[:, None] * vel * 0.5


def sub_bass(freq, dur, vel=1.0):
    n = int((dur + 0.08) * SR)
    t = _t(n)
    s = np.sin(2 * np.pi * freq * t) + 0.18 * np.sin(4 * np.pi * freq * t)
    env = np.minimum(t / 0.01, 1) * np.where(t < dur, 1, np.exp(-(t - dur) / 0.03))
    return tanh_sat(s * env, 1.2) * vel


def bass_synth(freq, dur, vel=1.0, cut=900):
    n = int((dur + 0.06) * SR)
    t = _t(n)
    s = saw(_f(freq), n, 0) * 0.5 + saw(_f(freq * 1.006), n, 0.5) * 0.5 + square(_f(freq / 2), n, 0) * 0.4
    c = 180 + cut * np.exp(-t / 0.09)
    s = svf(s, c.astype(np.float32), 1.2, 0)
    env = np.minimum(t / 0.004, 1) * np.where(t < dur, np.exp(-t / 0.5), np.exp(-dur / 0.5) * np.exp(-(t - dur) / 0.02))
    return tanh_sat(s * env * 1.2, 1.5) * vel


def lead(freq, dur, vel=1.0, bright=3500):
    n = int((dur + 0.5) * SR)
    t = _t(n)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - 0.25) / 0.3, 0, 1)
    fa = (freq * vib).astype(np.float32)
    s = saw(fa, n, 0) * 0.55 + saw((fa * 1.005).astype(np.float32), n, 0.4) * 0.45 + square((fa * 0.5).astype(np.float32), n, 0.2) * 0.3
    c = bright * (0.55 + 0.45 * np.minimum(t / 0.08, 1))
    s = svf(s, c.astype(np.float32), 0.9, 0)
    env = env_adsr(n, 0.02, 0.3, 0.8, 0.35, hold=dur)
    return s * env * vel * 0.5


def choir(freq, dur, vel=1.0, vowel='a'):
    n = int((dur + 1.2) * SR)
    t = _t(n)
    vib = 1 + 0.005 * np.sin(2 * np.pi * 4.8 * t + RNG.random() * 6)
    src = np.zeros(n, np.float32)
    for c in (-12, -4, 4, 12):
        src += saw((freq * vib * 2 ** (c / 1200)).astype(np.float32), n, RNG.random())
    F = {'a': [(800, 1.0, 8), (1150, 0.6, 9), (2900, 0.25, 12)], 'o': [(450, 1.0, 7), (800, 0.5, 8), (2830, 0.15, 12)]}[vowel]
    s = sum(bp(src, f, q) * g for f, g, q in F)
    env = env_adsr(n, 0.6, 0.5, 0.9, 1.1, hold=dur)
    return s * env * vel * 0.6


# ---------------------------------------------------------------- fx
def impact(vel=1.0, dur=3.0):
    n = int(dur * SR)
    t = _t(n)
    f = 28 + 50 * np.exp(-t / 0.12)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.9)
    thump = lp(noise(n, 91), 400) * np.exp(-t / 0.08) * 1.6
    crack = hp(noise(n, 92), 1500) * np.exp(-t / 0.03) * 0.5
    s = tanh_sat((boom * 1.2 + thump + crack), 1.6)
    return s * np.minimum(t / 0.001, 1) * vel


def riser(dur, vel=1.0, f0=250, f1=9000):
    n = int(dur * SR)
    t = _t(n)
    x = t / dur
    fc = f0 * (f1 / f0) ** (x ** 1.6)
    nz = noise(n, 101)
    s = svf(nz, fc.astype(np.float32), 2.5, 1) * 1.4
    tone_f = 110 * 2 ** (x ** 2 * 3)
    tone = saw(tone_f.astype(np.float32), n, 0) * 0.12
    tone = svf(tone, (fc * 0.5).astype(np.float32), 1.0, 0)
    amp = x ** 2.2
    out = np.zeros((n, 2), np.float32)
    mod = 0.5 + 0.5 * np.sin(2 * np.pi * (2 + 14 * x ** 2) * t)  # 越来越快的颤动，左右摆
    out[:, 0] = (s * (0.6 + 0.4 * mod) + tone) * amp
    out[:, 1] = (s * (0.6 + 0.4 * (1 - mod)) + tone) * amp
    return out * vel


def reverse_cymbal(dur=1.6, vel=1.0):
    c = crash(1.0, dur + 0.4)[:int(dur * SR)][::-1].copy()
    t = _t(c.shape[0])
    return c * (t / t[-1])[:, None] ** 0.5 * vel


def whoosh(dur=0.8, vel=1.0, up=True):
    n = int(dur * SR)
    t = _t(n)
    x = t / dur
    fc = (400 * (12 ** x)) if up else (5000 * (1 / 12) ** x)
    s = svf(noise(n, 111), fc.astype(np.float32), 1.8, 1)
    env = np.sin(np.pi * x) ** 2
    out = np.zeros((n, 2), np.float32)
    out[:, 0] = s * env * (1 - x * 0.6)
    out[:, 1] = s * env * (0.4 + x * 0.6)
    return out * vel


def sub_drop(dur=1.6, vel=1.0):
    n = int(dur * SR)
    t = _t(n)
    f = 30 + 45 * np.exp(-t / 0.5)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (dur * 0.5)) * np.minimum(t / 0.005, 1) * vel


def tick(vel=1.0):
    """木质钟表滴答"""
    n = int(0.06 * SR)
    t = _t(n)
    body = np.sin(2 * np.pi * 1150 * t) * np.exp(-t / 0.012) * 0.6
    click = bp(noise(n, 121), 2200, 2.5) * np.exp(-t / 0.006)
    return lp(body + click, 5000) * vel


def metal_hit(vel=1.0, dur=2.5):
    """电影感金属撞击：非谐波分音 + 噪声"""
    n = int(dur * SR)
    t = _t(n)
    s = np.zeros(n, np.float32)
    for f, d, g in ((187, 1.2, 1.0), (293, 0.9, 0.8), (461, 0.7, 0.6), (667, 0.5, 0.5), (1013, 0.35, 0.4), (1560, 0.25, 0.3)):
        s += np.sin(2 * np.pi * f * t + RNG.random() * 6) * np.exp(-t / d) * g
    s += bp(noise(n, 141), 3000, 0.8) * np.exp(-t / 0.08) * 0.8
    return tanh_sat(s * 0.5, 1.5) * np.minimum(t / 0.0008, 1) * vel


def heartbeat(vel=1.0):
    n = int(0.7 * SR)
    t = _t(n)
    def th(d):
        tt = np.maximum(t - d, 0)
        return np.sin(2 * np.pi * 52 * tt) * np.exp(-tt / 0.09) * (t >= d)
    return tanh_sat((th(0) + 0.75 * th(0.22)) * 1.3, 1.3) * vel


def blip(freq, vel=1.0):
    """界面元素弹出的提示音：短促的玻璃质感"""
    n = int(0.6 * SR)
    t = _t(n)
    s = np.sin(2 * np.pi * freq * t + 1.2 * np.sin(2 * np.pi * freq * 2 * t) * np.exp(-t / 0.05))
    return s * np.exp(-t / 0.16) * np.minimum(t / 0.0015, 1) * vel * 0.4


def scratch(vel=1.0):
    """唱片急停"""
    n = int(0.45 * SR)
    t = _t(n)
    f = 900 * np.exp(-t / 0.12) + 60
    s = saw(f.astype(np.float32), n, 0) * 0.5 + bp(noise(n, 131), 1200, 1.5)
    return lp(s, 3000) * np.exp(-t / 0.18) * vel
