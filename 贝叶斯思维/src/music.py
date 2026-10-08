"""《贝叶斯思维》原创配乐：96 BPM，D 小调，最后落在 D 大调（皮卡第三度）。

全部用 numpy 合成：管风琴 / 合唱垫音 / FM 电钢琴 / 拨弦琶音 / 低音 / 鼓组 / 电影感冲击音效。
结构和重拍完全由 timeline.py 决定；每个 HIT 前 0.6 s 抽空。

用法：python3 src/music.py work/   → work/score.wav（44.1 kHz 立体声，-14 LUFS）
"""
import math
import os
import sys

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as T  # noqa: E402

SR = 44100
LEN = T.DUR + 1.0
N = int(LEN * SR)
rng = np.random.default_rng(1763)
B, BAR = T.BEAT, T.BAR


def bt(bar_i, beat=0.0):
    return bar_i * BAR + beat * B


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}
NOTE.update({"Bb": 10, "Eb": 3, "Ab": 8, "Db": 1, "Gb": 6})


def m(s):
    """'D4' -> midi"""
    name, octv = s[:-1], int(s[-1])
    return 12 * (octv + 1) + NOTE[name]


# 和弦（低到高的声部）
CH = {
    "Dm": ["D3", "A3", "D4", "F4", "A4"],
    "Dm9": ["D3", "A3", "E4", "F4", "A4"],
    "Bb": ["Bb2", "F3", "D4", "F4", "Bb4"],
    "Bbmaj7": ["Bb2", "F3", "A3", "D4", "F4"],
    "F": ["F2", "C3", "A3", "C4", "F4"],
    "C": ["C3", "G3", "E4", "G4", "C5"],
    "Gm": ["G2", "D3", "Bb3", "D4", "G4"],
    "Gm9": ["G2", "D3", "A3", "Bb3", "F4"],
    "A": ["A2", "E3", "C#4", "E4", "A4"],
    "Asus": ["A2", "E3", "D4", "E4", "A4"],
    "D": ["D3", "A3", "D4", "F#4", "A4"],
    "Csus": ["C3", "G3", "D4", "F4", "G4"],
}
ROOT = {k: m(v[0]) for k, v in CH.items()}


class Bus:
    def __init__(self):
        self.x = np.zeros((2, N), np.float32)

    def add(self, t, sig, gain=1.0, pan=0.0):
        """sig: 1D (mono) 或 2×n。pan -1..1"""
        i0 = int(round(t * SR))
        if sig.ndim == 1:
            l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
            sig = np.stack([sig * l * 1.414, sig * r * 1.414])
        n = sig.shape[1]
        a, b = max(i0, 0), min(i0 + n, N)
        if b <= a:
            return
        self.x[:, a:b] += (sig[:, a - i0:b - i0] * gain).astype(np.float32)


def env_adsr(n, a, d, s, r, sus_len):
    """a,d,r 秒；s 持续电平；sus_len 秒（不含 release）"""
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    rel = np.clip((t - sus_len) / max(r, 1e-4), 0, 1)
    return (e * (1 - rel) ** 2).astype(np.float32)


def lp(x, fc, order=2):
    sos = signal.butter(order, min(fc, SR * 0.45), "low", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=-1)


def hp(x, fc, order=2):
    sos = signal.butter(order, fc, "high", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=-1)


def bp(x, f1, f2, order=2):
    sos = signal.butter(order, [f1, min(f2, SR * 0.45)], "band", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=-1)


def saw(f, n, ph=0.0):
    t = np.arange(n) / SR
    return (2 * ((f * t + ph) % 1.0) - 1).astype(np.float32)


def tv_filter(x, fn, kind="low", order=2.0):
    """时变滤波（STFT 掩膜）。fn(t 秒数组) -> 截止频率数组。x: 2×n 或 n"""
    nper = 2048
    f, tt, Z = signal.stft(x, SR, nperseg=nper, noverlap=nper - 512)
    fc = fn(tt)[None, :]
    ff = f[:, None]
    if kind == "low":
        g = 1 / np.sqrt(1 + (ff / fc) ** (2 * order))
    else:
        g = 1 / np.sqrt(1 + (fc / np.maximum(ff, 1)) ** (2 * order))
    _, y = signal.istft(Z * g, SR, nperseg=nper, noverlap=nper - 512)
    n = x.shape[-1]
    return y[..., :n].astype(np.float32)


# ================================================================ 乐器

def pad_note(midi, dur, bright=1200, voices=5, det=9.0, rel=1.6, att=0.5):
    n = int((dur + rel) * SR)
    f = hz(midi)
    out = np.zeros((2, n), np.float32)
    for v in range(voices):
        c = (v - (voices - 1) / 2) * det / max(1, (voices - 1) / 2)
        s = saw(f * 2 ** (c / 1200), n, rng.random())
        pan = (v - (voices - 1) / 2) / max(1, voices - 1) * 1.2
        out[0] += s * math.cos((pan + 1) * math.pi / 4)
        out[1] += s * math.sin((pan + 1) * math.pi / 4)
    out = lp(out, bright, 2) / voices
    out += np.sin(2 * np.pi * f * np.arange(n) / SR)[None, :] * 0.35
    return out * env_adsr(n, att, 1.0, 0.85, rel, dur)[None, :]


def choir_note(midi, dur, rel=1.8, att=0.8):
    """合唱 'ah'：锯齿叠加 + 三个共振峰"""
    n = int((dur + rel) * SR)
    f = hz(midi)
    t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.1 * t + rng.random() * 6)
    src = np.zeros((2, n), np.float32)
    for v in range(4):
        ph = np.cumsum(f * vib * 2 ** (((v - 1.5) * 6) / 1200)) / SR
        s = (2 * ((ph + rng.random()) % 1.0) - 1).astype(np.float32)
        src[v % 2] += s
    y = bp(src, 600, 820) * 1.0 + bp(src, 1050, 1350) * 0.55 + bp(src, 2400, 2800) * 0.25
    y = y * 0.9 + lp(src, 500) * 0.25
    return (y * env_adsr(n, att, 1.5, 0.9, rel, dur)[None, :]).astype(np.float32)


def organ_note(midi, dur, rel=1.2, att=0.08):
    n = int((dur + rel) * SR)
    t = np.arange(n) / SR
    f = hz(midi)
    s = np.zeros(n)
    for k, a in [(1, 1.0), (2, 0.55), (3, 0.3), (4, 0.22), (6, 0.1), (8, 0.06), (0.5, 0.4)]:
        s += a * np.sin(2 * np.pi * f * k * t * (1 + 0.0006 * np.sin(2 * np.pi * 0.3 * t)))
    return (s * env_adsr(n, att, 0.6, 0.9, rel, dur)).astype(np.float32) * 0.35


def epiano(midi, dur=2.0, vel=1.0, bell=False):
    n = int((dur + 1.5) * SR)
    t = np.arange(n) / SR
    f = hz(midi)
    ratio = 3.5 if bell else 1.0
    idx = (2.2 if bell else 1.6) * np.exp(-t * (2.5 if bell else 4.0)) * vel
    y = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * ratio * t))
    y += 0.25 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 3)
    e = np.exp(-t * (1.1 if bell else 1.6)) * np.minimum(1, t / 0.004)
    e *= np.clip((dur + 1.5 - t) / 0.3, 0, 1)
    return (y * e * vel).astype(np.float32) * 0.5


def pluck(midi, dur=0.5, bright=1.0):
    n = int((dur + 0.4) * SR)
    t = np.arange(n) / SR
    f = hz(midi)
    y = np.zeros(n)
    for k in range(1, 14):
        if f * k > 9000:
            break
        y += np.sin(2 * np.pi * f * k * t + k) / k * np.exp(-t * (4 + 2.6 * k / bright))
    y *= np.minimum(1, t / 0.002) * np.clip((dur + 0.4 - t) / 0.1, 0, 1)
    return y.astype(np.float32) * 0.45


def bass_note(midi, dur, cut=420):
    n = int((dur + 0.15) * SR)
    t = np.arange(n) / SR
    f = hz(midi)
    y = 0.8 * np.sin(2 * np.pi * f * t) + 0.35 * lp(saw(f, n), cut)
    e = np.minimum(1, t / 0.006) * np.exp(-t * 1.2) * np.clip((dur + 0.15 - t) / 0.12, 0, 1)
    return (y * e).astype(np.float32) * 0.6


def kick(v=1.0, low=44):
    n = int(0.55 * SR)
    t = np.arange(n) / SR
    f = low + 110 * np.exp(-t * 32)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7.5)
    y[:90] += rng.normal(0, 0.25, 90) * np.linspace(1, 0, 90)
    return (np.tanh(y * 1.6) * v).astype(np.float32) * 0.8


def taiko(v=1.0):
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    f = 62 + 70 * np.exp(-t * 18)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    y += lp(rng.normal(0, 1, n), 900) * np.exp(-t * 14) * 0.5
    return (np.tanh(y * 1.3) * v).astype(np.float32) * 0.8


def clap(v=1.0):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    nz = bp(rng.normal(0, 1, n), 900, 5200)
    e = np.zeros(n)
    for d in (0.0, 0.011, 0.022):
        e += (t >= d) * np.exp(-np.maximum(t - d, 0) * (90 if d < 0.02 else 16))
    return (nz * e * 0.5 * v).astype(np.float32)


def snare(v=1.0):
    n = int(0.4 * SR)
    t = np.arange(n) / SR
    y = bp(rng.normal(0, 1, n), 1500, 8000) * np.exp(-t * 18) * 0.55
    y += np.sin(2 * np.pi * 185 * t) * np.exp(-t * 28) * 0.5
    return (y * v).astype(np.float32)


def hat(v=1.0, open_=False):
    n = int((0.35 if open_ else 0.08) * SR)
    t = np.arange(n) / SR
    y = hp(rng.normal(0, 1, n), 7500) * np.exp(-t * (14 if open_ else 70))
    return (y * 0.35 * v).astype(np.float32)


def tick(v=1.0, hi=True):
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    f = 3100 if hi else 2350
    y = np.sin(2 * np.pi * f * t) * np.exp(-t * 160) + hp(rng.normal(0, 1, n), 4000) * np.exp(-t * 400) * 0.6
    y += np.sin(2 * np.pi * 900 * t) * np.exp(-t * 120) * 0.4
    return (y * 0.22 * v).astype(np.float32)


def sub_boom(v=1.0, f0=62, f1=31, dur=3.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 2.2)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.3) * np.minimum(1, t / 0.005)
    return (y * v).astype(np.float32)


def crash(v=1.0, dur=3.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = hp(rng.normal(0, 1, (2, n)), 3500) * np.exp(-t * 1.4)[None, :]
    y = lp(y, 12000)
    return (y * 0.25 * v).astype(np.float32)


def braam(root_midi, v=1.0, dur=4.0):
    """低音铜管冲击（电影预告片式）：低频锯齿簇 + 失真 + 滤波下扫"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros((2, n), np.float32)
    for k, (iv, a) in enumerate([(0, 1.0), (12, 0.8), (19, 0.45), (24, 0.35), (-12, 0.6)]):
        for d in (-7, 0, 7):
            s = saw(hz(root_midi + iv) * 2 ** (d / 1200), n, rng.random())
            y[(k + d // 7) % 2] += s * a
    y = np.tanh(y * 0.6)
    y = tv_filter(y, lambda tt: 300 + 2600 * np.exp(-tt * 2.2), "low", 2)
    e = np.minimum(1, t / 0.02) * np.exp(-t * 0.9)
    return (y * e[None, :] * 0.33 * v).astype(np.float32)


def riser(dur, v=1.0, f0=300, f1=9000):
    n = int(dur * SR)
    t = np.arange(n) / SR
    nz = rng.normal(0, 1, (2, n)).astype(np.float32)
    y = tv_filter(nz, lambda tt: f0 * (f1 / f0) ** np.clip(tt / dur, 0, 1) ** 1.6, "low", 2.5)
    y = hp(y, 200)
    # 升调 Shepard 式音高
    ph = np.cumsum(220 * 2 ** (2.0 * (t / dur) ** 1.5)) / SR
    tone = (np.sin(2 * np.pi * ph) + 0.5 * np.sin(4 * np.pi * ph)) * 0.25
    e = (t / dur) ** 2.2
    return ((y * 0.35 + tone[None, :]) * e[None, :] * v).astype(np.float32)


def reverse_swell(dur, v=1.0):
    c = crash(1.0, dur)[:, ::-1]
    return (c * np.linspace(0, 1, c.shape[1])[None, :] ** 2 * v * 1.6).astype(np.float32)


def whoosh(dur=1.2, v=1.0, up=True):
    n = int(dur * SR)
    t = np.arange(n) / SR
    nz = rng.normal(0, 1, (2, n)).astype(np.float32)
    u = t / dur
    y = tv_filter(nz, lambda tt: 400 + 4000 * np.sin(np.pi * np.clip(tt / dur, 0, 1)) ** 2, "low", 2)
    e = np.sin(np.pi * u) ** 2
    return (y * e[None, :] * 0.3 * v).astype(np.float32)


def shimmer(dur=3.0, v=1.0, base=74):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros((2, n))
    for i, iv in enumerate([0, 7, 12, 16, 19, 24]):
        f = hz(base + iv)
        y[i % 2] += np.sin(2 * np.pi * f * t + i) * (0.6 + 0.4 * np.sin(2 * np.pi * (0.7 + 0.3 * i) * t)) / (1 + i * 0.3)
    e = np.minimum(1, t / 0.4) * np.exp(-t * 0.8)
    return (y * e[None, :] * 0.08 * v).astype(np.float32)


def glitch(dur=0.5, v=1.0):
    n = int(dur * SR)
    y = np.zeros(n)
    i = 0
    while i < n:
        L = int(rng.integers(200, 2200))
        f = rng.choice([180, 440, 1200, 2600, 5200])
        seg = np.sign(np.sin(2 * np.pi * f * np.arange(L) / SR)) * rng.uniform(0.2, 1)
        if rng.random() < 0.3:
            seg = rng.normal(0, 0.6, L)
        y[i:i + L] = seg[:max(0, min(L, n - i))]
        i += L + int(rng.integers(0, 800))
    y = hp(y, 300)
    return (y * 0.18 * v * np.linspace(1, 0.3, n)).astype(np.float32)


def sparkle(dur, density, v=1.0, lo=84, hi=100):
    """颗粒状的细碎高音（点阵出现、模拟计数等）"""
    n = int(dur * SR)
    y = np.zeros((2, n), np.float32)
    cnt = int(dur * density)
    scale = [0, 2, 3, 5, 7, 9, 10]
    for _ in range(cnt):
        t0 = rng.random() * dur
        mm = rng.integers(lo, hi)
        mm = mm - (mm % 12) + scale[int(rng.integers(len(scale)))] + 2
        s = pluck(int(mm), 0.12, 0.6) * rng.uniform(0.3, 1.0)
        i0 = int(t0 * SR)
        L = min(len(s), n - i0)
        ch = int(rng.integers(2))
        y[ch, i0:i0 + L] += s[:L]
        y[1 - ch, i0:i0 + L] += s[:L] * 0.4
    return y * 0.25 * v


# ================================================================ 编曲

pads, choir, organ, keys, arp, bass, drums, sfx, hits = (Bus() for _ in range(9))
kick_env = np.zeros(N, np.float32)


def K(t, v=1.0, low=44):
    drums.add(t, kick(v, low), 1.0)
    i = int(t * SR)
    L = min(int(0.35 * SR), N - i)
    if L > 0:
        kick_env[i:i + L] = np.maximum(kick_env[i:i + L], v * np.exp(-np.arange(L) / SR * 9))


def chord_pad(t, name, bars=1, g=1.0, bright=1400, upper_only=False):
    notes = CH[name][1:] if upper_only else CH[name]
    for k, nn in enumerate(notes):
        pads.add(t, pad_note(m(nn), bars * BAR, bright), g * (0.6 if k == 0 else 0.42), pan=(k - 2) * 0.2)


def chord_choir(t, name, bars=1, g=1.0, octave=0):
    for k, nn in enumerate(CH[name][1:]):
        choir.add(t, choir_note(m(nn) + 12 * octave, bars * BAR), g * 0.32, pan=(k - 1.5) * 0.35)


def chord_organ(t, name, bars=1, g=1.0):
    for k, nn in enumerate(CH[name]):
        organ.add(t, organ_note(m(nn), bars * BAR), g * (0.7 if k == 0 else 0.45), pan=(k - 2) * 0.15)
    organ.add(t, organ_note(m(CH[name][0]) - 12, bars * BAR), g * 0.5)


def bass_line(t, name, bars=1, pattern="8th", g=1.0, cut=420):
    r = ROOT[name]
    if r > 50:
        r -= 12
    if pattern == "8th":
        for i in range(8 * bars):
            bass.add(t + i * B / 2, bass_note(r if i % 8 != 7 else r + 12, B / 2 * 0.9, cut), g * (1.0 if i % 2 == 0 else 0.7))
    elif pattern == "whole":
        bass.add(t, bass_note(r, bars * BAR * 0.98, cut), g)
    elif pattern == "pulse":
        for i in range(4 * bars):
            bass.add(t + i * B, bass_note(r, B * 0.5, cut), g * (1.0 if i % 4 == 0 else 0.6))


def arp_line(t, name, bars=1, div=4, g=1.0, bright=1.0, octave=1, pan_sweep=True):
    tones = [m(x) for x in CH[name][1:]]
    seq = tones + tones[::-1][1:-1]
    step = B / (div / 1)
    cnt = int(round(bars * BAR / step))
    for i in range(cnt):
        nn = seq[i % len(seq)] + 12 * octave
        acc = 1.0 if i % div == 0 else 0.7
        arp.add(t + i * step, pluck(nn, step * 1.6, bright), g * acc * 0.55,
                pan=math.sin(i * 0.7) * 0.6 if pan_sweep else 0)


def drums_groove(t, bars, style="four", g=1.0, hats=True, claps=True):
    for b in range(bars):
        t0 = t + b * BAR
        if style == "four":
            for k in range(4):
                K(t0 + k * B, g)
            if claps:
                drums.add(t0 + B, clap(g * 0.8), 1, 0.1)
                drums.add(t0 + 3 * B, clap(g * 0.8), 1, -0.1)
        elif style == "half":
            K(t0, g)
            K(t0 + 2.5 * B, g * 0.6)
            drums.add(t0 + 2 * B, snare(g * 0.8), 1)
        elif style == "heart":
            K(t0, g * 0.9, 40)
            K(t0 + 0.42 * B, g * 0.6, 40)
        elif style == "taiko":
            drums.add(t0, taiko(g), 1)
            drums.add(t0 + 1.5 * B, taiko(g * 0.55), 1, 0.2)
            drums.add(t0 + 2 * B, taiko(g * 0.8), 1, -0.2)
            drums.add(t0 + 3.5 * B, taiko(g * 0.5), 1)
        if hats:
            for k in range(8 if style != "four" else 16):
                st = B / 2 if style != "four" else B / 4
                hv = (0.55 if k % 2 == 0 else 0.3) * g
                drums.add(t0 + k * st, hat(hv, open_=(style == "four" and k % 4 == 2)), 1, 0.35)


def ticks(t, bars, sub=1, g=1.0):
    for i in range(int(bars * 4 * sub)):
        sfx.add(t + i * B / sub, tick(g * (1.0 if i % sub == 0 else 0.55), hi=(i // sub) % 2 == 0), 1, 0.25)


def HIT(t, root="D2", big=1.0, choir_chord=None):
    hits.add(t, braam(m(root), big), 1.0)
    hits.add(t, sub_boom(big), 0.9)
    hits.add(t, crash(big), 1.0)
    hits.add(t, taiko(big), 0.8)
    K(t, big * 1.1, 38)
    hits.add(t - 0.6 - 1.9, reverse_swell(1.9, 0.9 * big), 1.0)   # 吸入 → 0.6 s 静默 → 重拍


def melody(t, notes, g=1.0, bell=False, octave=0):
    """notes: [(beat, midi_str, dur_beats)]"""
    for b0, nn, d in notes:
        keys.add(t + b0 * B, epiano(m(nn) + 12 * octave, d * B + 0.4, 1.0, bell), g * 0.9, pan=0.1)


PROG = ["Dm", "Bb", "F", "C"]
THEME = [  # 1 小节 4 拍 × 4 小节，配 Dm Bb F C
    (0, "D5", 1.5), (1.5, "A4", 0.5), (2, "D5", 0.5), (2.5, "E5", 0.5), (3, "F5", 1),
    (4, "F5", 1.5), (5.5, "E5", 0.5), (6, "D5", 2),
    (8, "C5", 1.5), (9.5, "D5", 1), (10.5, "C5", 0.5), (11, "A4", 1),
    (12, "G4", 2), (14, "E5", 2),
]
MOTIF = [(0, "F5", 1), (1, "E5", 1), (2, "D5", 1), (3, "A4", 3)]   # "问号"动机：fa-mi-re-la


GAPS = []   # 重拍前的抽空区间


def build():
    # ------------------------------------------------ 0–25  序章：神秘
    for b, ch in zip(range(0, 10, 2), ["Dm9", "Bbmaj7", "Dm9", "Gm9", "Dm9"]):
        chord_pad(bt(b), ch, 2, 0.55, 900)
    for b in range(0, 10):
        bass.add(bt(b), bass_note(m("D2"), BAR * 0.98, 200), 0.35)
    ticks(bt(0, 2), 9.5, 1, 0.8)
    melody(bt(2), MOTIF, 0.7)
    melody(bt(4, 2), [(0, "A5", 1), (1, "F5", 1), (2, "E5", 2)], 0.4, bell=True)
    melody(bt(6), MOTIF, 0.75)
    melody(bt(8), [(0, "F5", 1), (1, "E5", 1), (2, "D5", 1), (3, "E5", 3)], 0.75)
    # 开门（17.5）：
    sfx.add(bt(7) - 1.0, whoosh(1.4, 1.2), 1.0)
    sfx.add(bt(7), shimmer(3.0, 1.2, 81), 1.0)
    drums.add(bt(7), taiko(0.7), 1)
    hits.add(bt(7), sub_boom(0.5), 1)
    # 选择 1 号门（10.0）
    sfx.add(bt(4), shimmer(2.0, 0.7, 86), 1)
    # ------------------------------------------------ 25–30 换还是不换：心跳
    chord_pad(bt(10), "Gm9", 1, 0.6, 1100)
    chord_pad(bt(11), "Asus", 1, 0.65, 1200)
    drums_groove(bt(10), 2, "heart", 0.9, hats=False)
    ticks(bt(10), 2, 2, 0.9)
    # ------------------------------------------------ 30–40 直觉 50/50
    for b, ch in zip(range(12, 16), ["Dm", "Bb", "Gm", "A"]):
        chord_pad(bt(b), ch, 1, 0.65, 1300)
        bass_line(bt(b), ch, 1, "pulse", 0.6, 300)
    drums_groove(bt(12), 2, "heart", 0.8, hats=False)
    ticks(bt(12), 3.0, 2, 0.8)
    sfx.add(bt(15) - 0.05, glitch(0.6, 1.0), 1)       # 50/50 裂开
    sfx.add(bt(14), riser(bt(16) - 0.6 - bt(14), 1.0), 1)
    GAPS.append((bt(16) - 0.6, bt(16)))
    # ------------------------------------------------ 40 揭晓：2/3
    HIT(bt(16), "D2", 1.0)
    for i, ch in enumerate(["Dm", "Bb", "F", "C", "Dm", "Bb", "F", "C"]):
        b = 16 + i
        chord_pad(bt(b), ch, 1, 0.7, 1600)
        bass_line(bt(b), ch, 1, "8th", 0.75, 380)
        if i >= 2:
            arp_line(bt(b), ch, 1, 2, 0.55, 0.8)
    chord_choir(bt(16), "Dm", 2, 0.8)
    for b in range(18, 23):
        K(bt(b), 0.7)
        K(bt(b, 2), 0.55)
        drums.add(bt(b, 1), hat(0.4), 1, 0.3)
        drums.add(bt(b, 3), hat(0.4), 1, 0.3)
    melody(bt(18), THEME[:6], 0.55, bell=True)
    sfx.add(bt(20, 1.6), whoosh(2.0, 0.8), 1)               # 信件飞来
    sfx.add(bt(20, 1.6), sparkle(4.0, 30, 0.7), 1)
    sfx.add(bt(22), riser(bt(24) - 0.6 - bt(22), 1.1), 1)
    for k in range(8):                                      # 军鼓滚奏
        drums.add(bt(23) + k * B / 2, snare(0.25 + 0.08 * k), 1)
    GAPS.append((bt(24) - 0.6, bt(24)))
    # ------------------------------------------------ 60 标题
    HIT(bt(24), "D2", 1.25)
    chord_organ(bt(24), "Dm", 3, 0.9)
    chord_choir(bt(24), "Dm9", 3, 1.0)
    chord_pad(bt(24), "Dm9", 3, 0.6, 2200)
    hits.add(bt(24), shimmer(6.0, 1.6, 86), 1)
    arp_line(bt(26), "Dm", 1, 4, 0.35, 0.8)
    # ------------------------------------------------ 67.5–82.5 计算机模拟：律动
    for i in range(6):
        b = 27 + i
        ch = PROG[i % 4]
        chord_pad(bt(b), ch, 1, 0.55, 1500)
        bass_line(bt(b), ch, 1, "8th", 0.85, 520)
        arp_line(bt(b), ch, 1, 4, 0.6, 1.1)
    drums_groove(bt(27), 6, "four", 0.85)
    sfx.add(bt(27, 2), sparkle(9.0, 70, 0.55), 1)          # 一局局对局的计数声
    HIT_small = bt(31)
    hits.add(HIT_small, sub_boom(0.6), 1)
    hits.add(HIT_small, crash(0.6), 1)
    chord_choir(bt(31), "F", 2, 0.6)
    # ------------------------------------------------ 82.5–100 100 扇门
    for i in range(7):
        b = 33 + i
        ch = ["Dm", "Bb", "F", "C", "Gm", "Bb", "Asus"][i]
        chord_pad(bt(b), ch, 1, 0.6, 900 + 200 * i)
        bass_line(bt(b), ch, 1, "8th" if i >= 2 else "whole", 0.75, 400)
        if i >= 1:
            arp_line(bt(b), ch, 1, 4, 0.35 + 0.05 * i, 0.7 + 0.08 * i)
    for b in range(35, 39):
        K(bt(b), 0.6)
        K(bt(b, 2), 0.6)
    for (td, d) in T.CASCADE:                               # 开门的细碎拨弦
        mm = [74, 77, 79, 81, 84, 86, 89][d % 7]
        sfx.add(td, pluck(mm, 0.15, 0.7), 0.22, pan=((d - 1) % 20 - 9.5) / 10)
    sfx.add(T.CASCADE[6][0], whoosh(2.4, 1.0), 1)
    sfx.add(bt(38), riser(bt(40) - 0.6 - bt(38), 1.0), 1)
    GAPS.append((bt(40) - 0.6, bt(40)))
    # ------------------------------------------------ 100 74 号门：99%
    HIT(bt(40), "Bb1", 1.0)
    for i, ch in enumerate(["Bbmaj7", "F", "Gm9", "Asus", "Asus"]):
        chord_pad(bt(40 + i), ch, 1, 0.55, 1000)
    chord_choir(bt(40), "Bb", 2, 0.5)
    melody(bt(41), MOTIF, 0.65)
    melody(bt(43), [(0, "F5", 1), (1, "G5", 1), (2, "A5", 2)], 0.6)
    sfx.add(bt(42, 0), shimmer(3.0, 0.8, 86), 1)            # "证据"
    # ------------------------------------------------ 112.5–122.5 1763：管风琴
    for i, ch in enumerate(["Dm", "Bb", "Gm", "Asus"]):
        chord_organ(bt(45 + i), ch, 1, 0.8)
    ticks(bt(45), 4, 1, 1.0)
    hits.add(bt(45), sub_boom(0.6, 50, 28), 1)
    sfx.add(bt(47), riser(bt(49) - 0.6 - bt(47), 0.9), 1)
    GAPS.append((bt(49) - 0.6, bt(49)))
    # ------------------------------------------------ 122.5 公式
    HIT(bt(49), "D2", 1.05)
    for i in range(5):
        b = 49 + i
        ch = PROG[i % 4]
        chord_pad(bt(b), ch, 1, 0.6, 1500)
        bass_line(bt(b), ch, 1, "8th", 0.75, 420)
        arp_line(bt(b), ch, 1, 2 if i < 2 else 4, 0.45, 0.9)
        K(bt(b), 0.7)
        K(bt(b, 2), 0.55)
        drums.add(bt(b, 1), clap(0.5), 1)
        drums.add(bt(b, 3), clap(0.5), 1)
    melody(bt(50), THEME[:6], 0.5, bell=True)
    sfx.add(bt(51), shimmer(2.0, 0.8, 81), 1)               # 公式 → 人话
    # ------------------------------------------------ 135–150 医学检测：悬疑
    for i, ch in enumerate(["Dm9", "Dm9", "Bbmaj7", "Bbmaj7", "Gm9", "Asus"]):
        chord_pad(bt(54 + i), ch, 1, 0.5, 800)
        bass_line(bt(54 + i), ch, 1, "pulse", 0.55, 250)
    ticks(bt(54), 6, 2, 0.75)
    drums_groove(bt(57), 2, "heart", 0.6, hats=False)
    hits.add(bt(59), braam(m("A1"), 0.45, 2.5), 1)          # "99%？"
    hits.add(bt(59), sub_boom(0.4), 1)
    # ------------------------------------------------ 150–170 一万个点
    sfx.add(bt(60), sparkle(2.5, 220, 0.8), 1)               # 一万个点出现
    sfx.add(bt(60), whoosh(1.6, 0.8), 1)
    for i in range(7):
        b = 60 + i
        ch = ["Dm", "Bb", "F", "C", "Gm", "Bb", "Asus"][i]
        chord_pad(bt(b), ch, 1, 0.55, 800 + 180 * i)
        bass_line(bt(b), ch, 1, "8th" if i >= 1 else "whole", 0.7, 350 + 30 * i)
        arp_line(bt(b), ch, 1, 4, 0.3 + 0.05 * i, 0.6 + 0.09 * i)
        if i >= 2:
            K(bt(b), 0.65)
            K(bt(b, 2), 0.6)
        if i >= 4:
            K(bt(b, 1), 0.55)
            K(bt(b, 3), 0.55)
            for k in range(8):
                drums.add(bt(b) + k * B / 2, hat(0.35 + 0.1 * (k % 2 == 0)), 1, 0.3)
    sfx.add(bt(63), shimmer(2.5, 0.8, 79), 1)                # 病人点亮
    sfx.add(bt(65), shimmer(2.5, 0.8, 84), 1)                # 误报点亮
    sfx.add(bt(67) - 0.4, whoosh(2.0, 1.1), 1)               # 点汇聚
    sfx.add(bt(66, 2), riser(bt(68) - 0.6 - bt(66, 2), 1.0), 1)
    GAPS.append((bt(68) - 0.6, bt(68)))
    # ------------------------------------------------ 170–190 50% → 99%：全编制主题
    HIT(bt(68), "D2", 1.15)
    for i in range(8):
        b = 68 + i
        ch = PROG[i % 4]
        chord_pad(bt(b), ch, 1, 0.65, 1800)
        bass_line(bt(b), ch, 1, "8th", 0.85, 520)
        arp_line(bt(b), ch, 1, 4, 0.5, 1.1)
    chord_choir(bt(68), "Dm", 4, 0.55)
    chord_choir(bt(72), "F", 4, 0.55)
    drums_groove(bt(68), 8, "four", 0.85)
    melody(bt(68), THEME, 0.7, bell=True)
    melody(bt(72), THEME, 0.7, bell=False)
    hits.add(bt(73), sub_boom(0.7), 1)
    hits.add(bt(73), crash(0.7), 1)
    sfx.add(bt(71, 2), whoosh(1.4, 0.7), 1)
    # ------------------------------------------------ 190–207.5 证据的力度：半速
    for i in range(7):
        b = 76 + i
        ch = ["Gm9", "Bbmaj7", "F", "Asus", "Gm9", "Bbmaj7", "Csus"][i]
        chord_pad(bt(b), ch, 1, 0.55, 1200)
        bass_line(bt(b), ch, 1, "pulse", 0.65, 380)
        arp_line(bt(b), ch, 1, 2, 0.4, 0.9)
    drums_groove(bt(76), 7, "half", 0.7)
    sfx.add(bt(79, 3.8), whoosh(0.8, 0.6), 1)
    sfx.add(bt(81, 3.8), whoosh(0.8, 0.6), 1)
    hits.add(bt(81, 1.5), shimmer(2.5, 1.0, 86), 1)          # 强证据：表针拉满
    # ------------------------------------------------ 207.5–217.5 回到三扇门：动机再现
    for i, ch in enumerate(["Dm9", "Bbmaj7", "Gm9", "Asus"]):
        chord_pad(bt(83 + i), ch, 1, 0.55 + 0.05 * i, 1000 + 250 * i)
        bass_line(bt(83 + i), ch, 1, "whole" if i < 2 else "8th", 0.6, 380)
    melody(bt(83), MOTIF, 0.75)
    melody(bt(85), [(0, "F5", 1), (1, "E5", 1), (2, "D5", 1), (3, "E5", 1)], 0.75)
    ticks(bt(83), 4, 2, 0.6)
    sfx.add(bt(85, 1), whoosh(1.2, 0.6), 1)                 # 相乘
    sfx.add(bt(86), riser(bt(87) - 0.6 - bt(86), 0.9), 1)
    GAPS.append((bt(87) - 0.6, bt(87)))
    # ------------------------------------------------ 217.5 2/3 解开
    HIT(bt(87), "D2", 1.0)
    chord_choir(bt(87), "F", 2, 0.7)
    chord_pad(bt(87), "F", 1, 0.6, 1600)
    chord_pad(bt(88), "C", 1, 0.6, 1600)
    melody(bt(87), [(0, "A5", 2), (2, "C6", 2), (4, "G5", 4)], 0.5, bell=True)
    # ------------------------------------------------ 222.5–245 生活与投资：明亮、温暖
    LIFE = ["Bb", "F", "C", "Dm", "Bb", "F", "C", "Csus", "Bb", "F", "C", "Dm", "Bb", "F", "C", "Asus"]
    for i in range(9):
        b = 89 + i
        ch = LIFE[i]
        chord_pad(bt(b), ch, 1, 0.6, 1700)
        bass_line(bt(b), ch, 1, "8th", 0.8, 500)
        arp_line(bt(b), ch, 1, 4, 0.45, 1.0)
    drums_groove(bt(89), 1, "half", 0.6, hats=True)
    drums_groove(bt(90), 8, "four", 0.75)
    LMEL = [(0, "D5", 1), (1, "F5", 1), (2, "C6", 2), (4, "A5", 2), (6, "G5", 1), (7, "F5", 1),
            (8, "E5", 2), (10, "G5", 2), (12, "F5", 3), (15, "E5", 1)]
    melody(bt(90), LMEL, 0.6, bell=True)
    melody(bt(94), LMEL, 0.6, bell=False)
    for t0 in (bt(90, 2.2), bt(92, 0), bt(93, 2.2), bt(95, 0)):      # 证据更新时的提示音
        sfx.add(t0, shimmer(1.5, 0.6, 86), 1)
    # ------------------------------------------------ 245–250 抬升
    chord_pad(bt(98), "Bb", 1, 0.7, 2200)
    chord_pad(bt(99), "Csus", 1, 0.75, 2600)
    chord_choir(bt(98), "Bb", 1, 0.7)
    chord_choir(bt(99), "Csus", 1, 0.8)
    drums_groove(bt(98), 2, "taiko", 0.9, hats=False)
    for k in range(16):
        drums.add(bt(99) + k * B / 4, snare(0.15 + 0.05 * k), 1)
    sfx.add(bt(98), riser(bt(100) - 0.6 - bt(98), 1.2), 1)
    GAPS.append((bt(100) - 0.6, bt(100)))
    # ------------------------------------------------ 250 终极重拍：观点是用来迭代的
    HIT(bt(100), "D2", 1.35)
    for i, ch in enumerate(["Bb", "C", "Dm"]):
        chord_pad(bt(100 + i), ch, 1, 0.75, 2400)
        chord_choir(bt(100 + i), ch, 1, 0.95)
        chord_organ(bt(100 + i), ch, 1, 0.55)
        bass_line(bt(100 + i), ch, 1, "whole", 0.9, 300)
        arp_line(bt(100 + i), ch, 1, 4, 0.4, 1.2)
    drums_groove(bt(100), 2, "taiko", 1.0, hats=False)
    melody(bt(100), [(0, "D6", 2), (2, "C6", 2), (4, "E6", 2), (6, "G5", 2), (8, "F5", 4)], 0.55, bell=True)
    hits.add(bt(102), reverse_swell(bt(103) - bt(102), 1.0), 1)
    # ------------------------------------------------ 257.5 巴芒价值：D 大调落地
    HIT(bt(103), "D2", 0.9)
    chord_choir(bt(103), "D", 2.2, 1.0)
    chord_pad(bt(103), "D", 2.2, 0.75, 2000)
    chord_organ(bt(103), "D", 2.2, 0.6)
    hits.add(bt(103), shimmer(7.0, 1.8, 86), 1)
    melody(bt(103), [(0, "F#5", 2), (2, "A5", 2), (4, "D6", 6)], 0.55, bell=True)
    hits.add(T.SHIMMER_T, shimmer(2.5, 1.0, 93), 1)                 # 流光扫过


# ================================================================ 混音

def reverb_ir(dur=3.2, predelay=0.02, damp=True):
    n = int(dur * SR)
    t = np.arange(n) / SR
    ir = rng.normal(0, 1, (2, n)) * np.exp(-t * 6.9 / dur)[None, :]
    if damp:
        ir = tv_filter(ir.astype(np.float32), lambda tt: 9000 * np.exp(-tt * 1.2) + 600, "low", 1.5)
    ir = np.concatenate([np.zeros((2, int(predelay * SR))), ir], axis=1)
    return ir / np.sqrt((ir ** 2).sum(axis=1, keepdims=True))


def gap_gain():
    g = np.ones(N, np.float32)
    for a, b in GAPS:
        i0, i1 = int(a * SR), int(b * SR)
        ramp = int(0.05 * SR)
        g[i0 - ramp:i0] = np.minimum(g[i0 - ramp:i0], np.linspace(1, 0, ramp))
        g[i0:i1] = 0
    return g


def lufs(x):
    import pyloudnorm as pyln
    return pyln.Meter(SR).integrated_loudness(x.T.astype(np.float64))


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "work"
    os.makedirs(out_dir, exist_ok=True)
    build()
    # 侧链：底鼓压低垫音和低音
    sc = np.clip(1 - 0.4 * np.convolve(kick_env, np.ones(200) / 200, "same"), 0.55, 1).astype(np.float32)
    gg = gap_gain()
    mixes = {
        "pads": (pads, 0.55, 0.35), "choir": (choir, 0.5, 0.5), "organ": (organ, 0.55, 0.4),
        "keys": (keys, 0.55, 0.45), "arp": (arp, 0.38, 0.35), "bass": (bass, 0.7, 0.05),
        "drums": (drums, 0.75, 0.1), "sfx": (sfx, 0.7, 0.35), "hits": (hits, 0.8, 0.3),
    }
    dry = np.zeros((2, N), np.float32)
    send = np.zeros((2, N), np.float32)
    for k, (bus, g, rv) in mixes.items():
        x = bus.x * g
        if k in ("pads", "bass", "arp", "choir", "organ"):
            x = x * sc[None, :]
        if k != "hits":
            x = x * gg[None, :]
        rms = float(np.sqrt((x ** 2).mean()))
        print(f"{k:6s} rms {20 * np.log10(rms + 1e-9):6.1f} dB  peak {np.abs(x).max():.2f}")
        dry += x
        send += x * rv
    ir = reverb_ir(3.4)
    wet = np.stack([signal.fftconvolve(send[c], ir[c])[:N] for c in range(2)]).astype(np.float32)
    mix = dry + wet * 0.55
    mix = hp(mix, 28).astype(np.float32)
    # 母带：柔和压缩 + 软限幅 + 响度标准化
    loud = lufs(mix)
    mix *= 10 ** ((-16.0 - loud) / 20)
    mix = np.tanh(mix * 1.25) / 1.25
    loud = lufs(mix)
    mix *= 10 ** ((-14.0 - loud) / 20)
    pk = np.abs(signal.resample_poly(mix, 4, 1, axis=1)).max()
    if pk > 0.93:
        mix = np.tanh(mix / 0.93) * 0.93
    # 片尾淡出
    t = np.arange(N) / SR
    mix *= np.clip((T.DUR - t) / (T.DUR - T.FADE_OUT), 0, 1)[None, :] ** 1.5
    mix *= np.clip(t / 0.3, 0, 1)[None, :]
    import soundfile as sf
    sf.write(os.path.join(out_dir, "score.wav"), mix.T[: int(T.DUR * SR)], SR, subtype="PCM_24")
    print("LUFS", round(lufs(mix), 2), "peak", round(float(np.abs(mix).max()), 3))


if __name__ == "__main__":
    main()
