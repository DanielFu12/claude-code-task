"""M06 原创配乐 + 低频转场音效（全部用 numpy 合成，无外部采样）

配乐：128.57 BPM（1 拍 = 14 帧），E 小调，节奏更紧，表现「你加一步、我跟一步」的升级感；
  和声走 i–VI–III–VII（Em–C–G–D），抽空段走 iv–VI–III–V（Am–C–G–B）。
  安静段（drone + 心跳）→ 上扬段（鼓组、八分音符贝斯）→ 高潮（四拍底鼓 + 主旋律）→ 抽空 → 高潮 2 → 尾声。
音效：只用 sub drop / 低频 boom / 低沉膨胀 / 闷击，全部经 4 阶低通（180 Hz）→ 能量集中在 200 Hz 以下；
  不用白噪声、whoosh、尖锐上升音；每个音效按所在位置的音乐响度自动压低（比音乐低 ≥4 dB）。

用法：python3 music.py WORKDIR   → bgm.wav（音乐）、sfx.wav（音效）、mix.wav（成片音轨）
"""
import sys, os, math
import numpy as np, soundfile as sf
from scipy import signal
from timeline import *

SR = 44100
N = int(round(DUR * SR))
RNG = np.random.default_rng(7)


def S(t):  # 秒 → 采样点
    return int(round(t * SR))


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def sos_lp(fc, order=2):
    return signal.butter(order, min(fc, SR * 0.45), 'low', fs=SR, output='sos')


def sos_hp(fc, order=2):
    return signal.butter(order, fc, 'high', fs=SR, output='sos')


def sos_bp(lo, hi, order=2):
    return signal.butter(order, [lo, hi], 'band', fs=SR, output='sos')


def lp(x, fc, order=2):
    return signal.sosfilt(sos_lp(fc, order), x, axis=0)


def saw(freq, n, phase=0.0):
    """PolyBLEP 带限锯齿波"""
    dt = np.broadcast_to(np.asarray(freq, np.float64) / SR, (n,))
    ph = (phase + np.cumsum(dt)) % 1.0
    y = 2 * ph - 1
    m = ph < dt
    x = ph[m] / dt[m]; y[m] -= x + x - x * x - 1
    m = ph > 1 - dt
    x = (ph[m] - 1) / dt[m]; y[m] -= x * x + x + x + 1
    return y


def sine(freq, n, phase=0.0):
    f = np.broadcast_to(np.asarray(freq, np.float64), (n,))
    return np.sin(2 * np.pi * (phase + np.cumsum(f) / SR))


def add(buf, x, t, gain=1.0, pan=0.0):
    """把单声道/立体声片段加到 buf（N×2）的 t 秒处"""
    i = S(t)
    if x.ndim == 1:
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        x = np.stack([x * l * 1.41421, x * r * 1.41421], 1)
    j = min(i + len(x), N)
    if j <= i or i < 0: return
    buf[i:j] += x[:j - i] * gain


def new():
    return np.zeros((N, 2), np.float64)


# ================================================================ 和声
CH = {  # pad 音（midi）、琶音音、贝斯根音 —— E 小调
    'Em': ([52, 55, 59, 64], [64, 67, 71, 76], 40),
    'C': ([52, 55, 60, 64], [64, 67, 72, 76], 36),
    'G': ([50, 55, 59, 62], [62, 67, 71, 74], 43),
    'D': ([50, 54, 57, 62], [62, 66, 69, 74], 38),
    'Am': ([48, 52, 57, 60], [60, 64, 69, 72], 45),
    'B': ([51, 54, 59, 63], [63, 66, 71, 75], 35),
    'Em9': ([52, 54, 59, 62], [64, 66, 71, 74], 40),
}
PROG_A = ['Em', 'C', 'G', 'D']
PROG_B = ['Am', 'C', 'G', 'B']
SEC_START = [4, 9, 25, 41, 57, 69, 85, 93]


def chord_at(bar):
    if bar < 4: return 'Em'
    if bar == 8: return 'B'
    if bar >= 93: return 'Em9'
    if bar in (91, 92): return ['Am', 'B'][bar - 91]
    s = max(x for x in SEC_START if x <= bar)
    if 57 <= bar < 69: return PROG_B[(bar - s) % 4]
    return PROG_A[(bar - s) % 4]


def ramp(bar, a, z, v0, v1):
    return v0 + (v1 - v0) * min(max((bar - a) / max(z - a, 1e-6), 0), 1)


def pad_cut(bar):
    if bar < 4: return 500
    if bar < 9: return 750
    if bar < 25: return ramp(bar, 9, 25, 800, 1400)
    if bar < 41: return ramp(bar, 25, 41, 1400, 2600)
    if bar < 57: return 3200
    if bar < 65: return 900
    if bar < 69: return ramp(bar, 65, 69, 900, 2600)
    if bar < 85: return 3600
    if bar < 93: return ramp(bar, 85, 93, 2200, 700)
    return 1600


def pad_gain(bar):
    if bar < 4: return 0.0
    if bar < 9: return 0.6
    if bar < 25: return ramp(bar, 9, 25, 0.5, 0.7)
    if bar < 41: return ramp(bar, 25, 41, 0.75, 0.95)
    if bar < 57: return 1.0
    if bar < 69: return 0.55
    if bar < 85: return 1.05
    if bar < 93: return ramp(bar, 85, 93, 0.85, 0.45)
    return 0.0  # 片尾和弦单独写


# ================================================================ 乐器
def pad_bar(bar, chord, cut, gain):
    t0 = b(bar) - 0.08
    dur = BAR + 0.16
    n = S(dur)
    notes = CH[chord][0]
    out = np.zeros((n, 2))
    det = [-14, -7, 0, 7, 14]
    for m in notes:
        for k, c in enumerate(det):
            f = mtof(m) * 2 ** (c / 1200)
            v = saw(f, n, RNG.random())
            pan = (k - 2) / 2 * 0.7
            out[:, 0] += v * math.cos((pan + 1) * math.pi / 4)
            out[:, 1] += v * math.sin((pan + 1) * math.pi / 4)
    out = lp(out, cut, 4)
    e = np.ones(n); f = S(0.16)
    e[:f] = np.sin(np.linspace(0, np.pi / 2, f)) ** 2
    e[-f:] = np.cos(np.linspace(0, np.pi / 2, f)) ** 2
    return t0, out * e[:, None] * gain * 0.022


def pluck(m, dur, cut, vel=1.0):
    n = S(dur + 0.35)
    f = mtof(m)
    v = saw(f, n, RNG.random()) + 0.6 * saw(f * 1.004, n, RNG.random()) + 0.4 * sine(f / 2, n)
    t = np.arange(n) / SR
    bright = lp(v, min(cut * 2.6, 12000), 2) * np.exp(-t / 0.05)
    dark = lp(v, cut, 2) * np.exp(-t / 0.22)
    e = np.minimum(t / 0.003, 1)
    return (bright * 0.6 + dark) * e * vel


def kick(depth=1.0):
    n = S(0.7)
    t = np.arange(n) / SR
    f = 42 + 95 * np.exp(-t / 0.055)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.38)
    x = np.tanh(x * 1.6) / np.tanh(1.6)
    click = lp(RNG.standard_normal(n), 2500, 2) * np.exp(-t / 0.004) * 0.25
    return (x + click) * depth


def heartbeat():
    n = S(0.6)
    t = np.arange(n) / SR
    f = 40 + 40 * np.exp(-t / 0.05)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.18) * np.minimum(t / 0.006, 1)
    return lp(x, 160, 2)


def clap():
    n = S(0.5)
    t = np.arange(n) / SR
    nz = RNG.standard_normal(n)
    env = np.zeros(n)
    for k, d in enumerate((0, 0.011, 0.022)):
        i = S(d); env[i:] += np.exp(-(t[:n - i]) / (0.006 if k < 2 else 0.14)) * (0.7 if k < 2 else 1)
    x = signal.sosfilt(sos_bp(500, 2600), nz) * env
    body = np.sin(2 * np.pi * 175 * t) * np.exp(-t / 0.07) * 0.5
    return x + body


def hat():
    n = S(0.12)
    t = np.arange(n) / SR
    x = signal.sosfilt(sos_bp(5500, 9500), RNG.standard_normal(n)) * np.exp(-t / 0.025)
    return x


def tom(f0=95):
    n = S(0.6)
    t = np.arange(n) / SR
    f = f0 * (0.78 + 0.5 * np.exp(-t / 0.06))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.28)
    return x + lp(RNG.standard_normal(n), 900, 2) * np.exp(-t / 0.03) * 0.15


def tick():
    n = S(0.08)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 950 * t) + 0.4 * np.sin(2 * np.pi * 1520 * t)) * np.exp(-t / 0.012)


def lead_note(m, dur, cut=2400, oct_bell=0.0):
    n = S(dur + 0.4)
    t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.minimum(t / 0.4, 1)
    f = mtof(m) * vib
    v = saw(f * 0.997, n, RNG.random()) + saw(f * 1.003, n, RNG.random()) + 0.7 * sine(f / 2, n)
    v = lp(v, cut, 2)
    a = np.minimum(t / 0.02, 1)
    rel = np.clip(1 - (t - dur) / 0.35, 0, 1)
    e = a * rel * (0.75 + 0.25 * np.exp(-t / 0.3))
    x = v * e
    if oct_bell > 0:  # FM 钟声，高八度
        fb = mtof(m + 12)
        bell = np.sin(2 * np.pi * fb * t + 1.8 * np.exp(-t / 0.4) * np.sin(2 * np.pi * fb * 2.0 * t)) * np.exp(-t / 0.9)
        x = x + bell * oct_bell * (t < dur + 0.4)
    return x


def bell(m, dur):
    n = S(dur + 1.6)
    t = np.arange(n) / SR
    f = mtof(m)
    x = np.sin(2 * np.pi * f * t + 1.2 * np.exp(-t / 0.6) * np.sin(2 * np.pi * f * 3.0 * t)) * np.exp(-t / 1.4)
    x += 0.35 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t / 0.7)
    return x * np.minimum(t / 0.004, 1)


def sub_note(m, dur, sat=1.3):
    n = S(dur + 0.08)
    t = np.arange(n) / SR
    x = sine(mtof(m), n)
    x = np.tanh(x * sat) / np.tanh(sat)
    e = np.minimum(t / 0.01, 1) * np.clip((dur + 0.08 - t) / 0.08, 0, 1)
    return x * e


# ================================================================ 旋律
MEL = [  # 8 小节（Em C G D ×2），(midi, 拍数)
    [(71, 1), (76, 1), (74, .5), (71, 1.5)],
    [(72, 1), (71, .5), (67, .5), (64, 2)],
    [(67, 1), (71, 1), (74, 1), (71, 1)],
    [(69, 1.5), (66, .5), (62, 2)],
    [(71, 1), (76, 1), (79, .5), (78, 1.5)],
    [(76, 1), (72, .5), (71, .5), (72, 2)],
    [(74, 1), (79, .5), (74, .5), (71, 1), (69, 1)],
    [(69, 1), (71, 1), (66, 2)],
]
MEL_END = [(66, 1), (69, 1), (71, 2)]
BELL_MOTIF = [  # 抽空段（Am C G B）
    [(76, 3), (72, 1)], [(72, 4)], [(71, 2), (67, 2)], [(66, 3), (63, 1)],
]

ARP_PAT = [0, 2, 1, 2, 3, 2, 1, 2, 0, 2, 1, 3, 2, 1, 3, 1]


def compose():
    pad, arp, bass, drums, lead, fx, wet_send = new(), new(), new(), new(), new(), new(), new()
    kicks = []  # 用于侧链

    # ---------- drone（钩子、抽空、片尾）
    for (a, z, g) in ((0, 4.0, 1.0), (57, 69, 0.7), (93, 99, 0.8)):
        t0, t1 = b(a), b(z)
        n = S(t1 - t0)
        t = np.arange(n) / SR
        x = (sine(41.20, n) * 0.9 + sine(82.41 * 1.002, n) * 0.45 + sine(61.74 * 0.999, n) * 0.25)   # E1 / E2 / B1
        x *= 0.8 + 0.2 * np.sin(2 * np.pi * 0.11 * t)
        e = np.minimum(t / 1.2, 1) * np.clip((t1 - t0 - t) / 0.4, 0, 1)
        if a == 0:
            e *= 0.55 + 0.45 * (t / (t1 - t0)) ** 2
        add(pad, x * e * 0.16 * g, t0)
        # 低通的柔和和声层
        if a == 0:
            for m in (52, 59, 64):
                v = lp(saw(mtof(m), n, RNG.random()) + saw(mtof(m) * 1.005, n, RNG.random()), 420, 4)
                add(pad, v * e * 0.03, t0, pan=(m - 57) / 10)

    # ---------- 心跳 + 时钟滴答（钩子）
    for bar in range(0, 4):
        for bt in (0, 0.42, 2, 2.42):
            add(drums, heartbeat() * (0.55 if bt % 1 else 0.75) * (0.7 + 0.1 * bar), b(bar, bt))
        for bt in range(4):
            add(fx, tick() * 0.05, b(bar, bt + 0.5), pan=0.3 * (1 if bt % 2 else -1))

    # ---------- pad
    for bar in range(4, 93):
        g = pad_gain(bar)
        if g <= 0: continue
        t0, x = pad_bar(bar, chord_at(bar), pad_cut(bar), g)
        add(pad, x, t0)
        add(wet_send, x * 0.35, t0)

    # ---------- 16 分音符琶音（"一直在跑"）
    def arp_on(bar):
        if 4 <= bar < 57: return ramp(bar, 4, 9, 0.35, 0.5) if bar < 9 else ramp(bar, 9, 25, 0.5, 0.7) if bar < 25 else ramp(bar, 25, 41, 0.75, 0.95) if bar < 41 else 1.0
        if 65 <= bar < 69: return ramp(bar, 65, 69, 0.4, 0.85)
        if 69 <= bar < 85: return 1.0
        if 85 <= bar < 93: return ramp(bar, 85, 93, 0.8, 0.35)
        return 0
    for bar in range(4, 93):
        g = arp_on(bar)
        if g <= 0: continue
        tones = CH[chord_at(bar)][1]
        cut = (
            ramp(bar, 4, 25, 700, 1300) if bar < 25 else ramp(bar, 25, 41, 1300, 2600) if bar < 41 else
            3000 if bar < 57 else ramp(bar, 65, 69, 800, 2400) if bar < 69 else 3400 if bar < 85 else ramp(bar, 85, 93, 2200, 700))
        for k in range(16):
            t = b(bar, k * 0.25)
            if (bar in (40, 68) and k >= 12): continue          # 重拍前抽空
            m = tones[ARP_PAT[k]] + (12 if (bar >= 69 and bar < 85 and k in (6, 14)) else 0)
            vel = (1.0 if k % 4 == 0 else 0.62 if k % 2 == 0 else 0.48) * g
            x = pluck(m, 0.14, cut, vel) * 0.055
            pan = 0.35 * math.sin(k * math.pi / 4)
            add(arp, x, t, pan=pan)
            add(wet_send, np.stack([x, x], 1) * 0.3, t)
    # 立体声乒乓延迟（附点八分）
    d = S(BEAT * 0.75)
    dl = np.zeros_like(arp)
    dl[d:, 0] += arp[:-d, 1] * 0.32
    dl[2 * d:, 1] += arp[:-2 * d, 0] * 0.22
    arp += lp(dl, 3500, 2)

    # ---------- 贝斯
    for bar in range(4, 93):
        root = CH[chord_at(bar)][2]
        if bar < 25 or 57 <= bar < 65 or bar >= 85:
            g = 0.28 if bar < 25 else 0.36
            if 57 <= bar < 65: g = 0.24
            add(bass, sub_note(root, BAR - 0.02, 1.2) * g, b(bar))
        elif 65 <= bar < 69:
            for k in range(8):
                if bar == 68 and k >= 6: continue
                add(bass, sub_note(root, BEAT / 2 - 0.04, 1.6) * 0.32, b(bar, k / 2))
        else:
            for k in range(8):
                if bar == 40 and k >= 6: continue
                m = root + (12 if k in (3, 7) and bar >= 41 else 0)
                add(bass, sub_note(m, BEAT / 2 - 0.03, 1.8) * (0.42 if k % 2 == 0 else 0.34), b(bar, k / 2))

    # ---------- 鼓
    def K(t, g=1.0):
        add(drums, kick(g) * 0.62, t); kicks.append((t, g))
    for bar in range(17, 25):
        K(b(bar, 0), 0.55); K(b(bar, 2), 0.45)
    for bar in range(25, 41):
        if bar == 40:
            for k in range(6): K(b(bar, k / 2), 0.55 + 0.07 * k)
            continue
        if bar >= 39:
            for k in range(8): K(b(bar, k / 2), 0.55 + 0.03 * k)
            continue
        K(b(bar, 0), 0.8); K(b(bar, 2), 0.7)
        if bar % 2 == 1: K(b(bar, 2.5), 0.45)
        if bar >= 29 and bar < 39:
            add(drums, clap() * 0.13, b(bar, 1)); add(drums, clap() * 0.13, b(bar, 3))
            add(wet_send, np.stack([clap()] * 2, 1) * 0.05, b(bar, 1))
    for (a, z) in ((41, 57), (69, 85)):
        for bar in range(a, z):
            for k in range(4): K(b(bar, k), 0.95 if k == 0 else 0.85)
            for k in (1, 3):
                add(drums, clap() * 0.16, b(bar, k)); add(wet_send, np.stack([clap()] * 2, 1) * 0.06, b(bar, k))
            for k in range(4):
                add(drums, hat() * 0.028, b(bar, k + 0.5), pan=0.25)
            if (bar - a) % 8 == 7:   # 每 8 小节一个低音嗵鼓过门
                for j, k in enumerate((2.5, 3, 3.25, 3.5, 3.75)):
                    add(drums, tom(110 - 8 * j) * 0.22, b(bar, k), pan=-0.3 + 0.15 * j)
    # 重拍前的嗵鼓渐强
    for (a, z) in ((39, 41), (67, 69)):
        n16 = int((z - a) * 16) - 4
        for k in range(n16):
            tt = b(a, k * 0.25)
            if k < n16 / 2 and k % 2: continue
            g = 0.06 + 0.22 * (k / n16) ** 1.5
            add(drums, tom(85 + 25 * (k / n16)) * g, tt, pan=0.2 * math.sin(k))
    # 抽空段末尾 2 小节底鼓
    for bar in (65, 66, 67, 68):
        for k in range(4 if bar < 67 else 8):
            if bar == 68 and k >= 6: continue
            K(b(bar, k * (1 if bar < 67 else 0.5)), 0.5 + 0.05 * (bar - 65))
    # 尾声：底鼓渐弱
    for bar in range(85, 89):
        K(b(bar, 0), 0.6 - 0.08 * (bar - 85)); K(b(bar, 2), 0.5 - 0.08 * (bar - 85))

    # ---------- 主旋律
    def play_mel(a, oct=0, cut=2400, bellg=0.0, g=0.07):
        for rep in range(2):
            for i, barnotes in enumerate(MEL if rep == 0 else MEL[:7] + [MEL_END]):
                bt = 0.0
                for (m, d) in barnotes:
                    tt = b(a + rep * 8 + i, bt)
                    x = lead_note(m + oct, d * BEAT * 0.95, cut, bellg) * g
                    add(lead, x, tt, pan=0.05)
                    add(wet_send, np.stack([x, x], 1) * 0.5, tt)
                    bt += d
    play_mel(41, 0, 2200, 0.0, 0.065)
    play_mel(69, 12, 2800, 0.25, 0.05)
    play_mel(69, 0, 1800, 0.0, 0.035)   # 低八度叠加，高潮 2 更厚
    # 抽空段：钟声动机
    for rep in range(3):
        for i, barnotes in enumerate(BELL_MOTIF):
            bt = 0.0
            for (m, d) in barnotes:
                tt = b(57 + rep * 4 + i, bt)
                x = bell(m + (12 if rep == 1 and i % 2 else 0), d * BEAT) * 0.05
                add(lead, x, tt, pan=-0.15 + 0.1 * i)
                add(wet_send, np.stack([x, x], 1) * 0.8, tt)
                bt += d

    # ---------- 片尾：bar 94.5 轻击（logo 浮现），bar 95 重拍大和弦（品牌字）
    EL, EW, EZ = b(94, 2), b(95), b(99)
    for (tt, g) in ((EL, 0.45), (EW, 1.0)):
        K(tt, g)
        add(drums, tom(70) * 0.3 * g, tt)
    n = S(EZ - EW)
    t = np.arange(n) / SR
    e = np.minimum(t / 0.01, 1) * np.exp(-t / 3.2)
    for m in CH['Em9'][0] + [76, 79]:
        for c in (-9, 0, 9):
            v = lp(saw(mtof(m) * 2 ** (c / 1200), n, RNG.random()), 2600, 2)
            add(pad, v * e * 0.016, EW, pan=c / 12)
            add(wet_send, np.stack([v, v], 1) * e[:, None] * 0.01, EW)
    sn = sub_note(40, EZ - EW - 0.1, 1.4)
    add(bass, sn * e[:len(sn)] * 0.45, EW)
    for m in (76, 83, 88):
        x = bell(m, 2.0) * 0.045
        add(lead, x, EW); add(wet_send, np.stack([x, x], 1) * 0.8, EW)
    # bar 93–95：汇聚段的低频和弦膨胀
    n2 = S(EW - b(93))
    t2 = np.arange(n2) / SR
    sw = 0.3 + 0.7 * (t2 / t2[-1]) ** 2.0
    for m in (40, 47, 52, 59, 64):
        v = lp(saw(mtof(m), n2, RNG.random()) + saw(mtof(m) * 1.004, n2, RNG.random()), 900, 2)
        add(pad, v * sw * 0.045, b(93), pan=(m - 53) / 16)
        add(wet_send, np.stack([v, v], 1) * sw[:, None] * 0.02, b(93))

    # ---------- 侧链（底鼓压 pad/琶音/贝斯）
    duck = np.ones(N)
    for (t, g) in kicks:
        i = S(t); n = S(0.32)
        j = min(i + n, N)
        tt = np.arange(j - i) / SR
        duck[i:j] = np.minimum(duck[i:j], 1 - 0.55 * g * np.exp(-tt / 0.11))
    for bus in (pad, arp, bass):
        bus *= duck[:, None]

    # ---------- 混响
    ir_n = S(3.6)
    ti = np.arange(ir_n) / SR
    ir = np.stack([RNG.standard_normal(ir_n), RNG.standard_normal(ir_n)], 1) * np.exp(-ti / 0.62)[:, None]
    ir = lp(ir, 5200, 2); ir[:S(0.025)] = 0; ir /= np.sqrt((ir ** 2).sum(0))
    wet = np.stack([signal.oaconvolve(wet_send[:, c], ir[:, c])[:N] for c in range(2)], 1)
    wet = signal.sosfilt(sos_hp(180), wet, axis=0)

    mix = pad + arp + bass * 1.0 + drums + lead + fx + wet * 0.55
    mix = signal.sosfilt(sos_hp(24), mix, axis=0)
    return mix


# ================================================================ 低频转场音效
def sfx_boom(k):
    n = S(3.2)
    t = np.arange(n) / SR
    f = 34 + 46 * np.exp(-t / 0.22)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.3 * np.sin(4 * np.pi * np.cumsum(f) / SR)
    x *= np.minimum(t / 0.003, 1) * np.exp(-t / (0.9 + 0.6 * k))
    return np.tanh(x * 1.4)


def sfx_subdrop(k):
    n = S(3.6)
    t = np.arange(n) / SR
    f = 27 + 85 * np.exp(-t / 0.32)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR)
    x *= np.minimum(t / 0.004, 1) * np.exp(-t / 1.5)
    return np.tanh(x * 1.6)


def sfx_thud(k):
    n = S(1.2)
    t = np.arange(n) / SR
    f = 50 + 38 * np.exp(-t / 0.05)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(t / 0.002, 1) * np.exp(-t / 0.32)
    return np.tanh(x * 1.3)


def sfx_swell(dur):
    """低沉膨胀：低频和弦簇缓慢放大（含极低频隆隆声），在重拍那一帧前收住"""
    n = S(dur)
    t = np.arange(n) / SR
    u = t / dur
    x = np.zeros(n)
    for f, a in ((36.71, 1.0), (36.9, 0.8), (55.0, 0.6), (73.4, 0.35)):
        x += a * np.sin(2 * np.pi * f * (1 + 0.06 * u ** 2) * t)
    rum = signal.sosfilt(sos_lp(70, 4), np.cumsum(RNG.standard_normal(n)) * 0.002)
    rum = rum / (np.abs(rum).max() + 1e-9)
    x = x / 2.75 + 0.5 * rum
    e = u ** 2.4 * np.clip((dur - t) / 0.02, 0, 1)
    return x * e


def build_sfx(music):
    m_mono = music.mean(1)
    out = np.zeros(N)
    LPS = sos_lp(180, 4)

    def local_rms(t, w):
        i, j = S(t), min(S(t + w), N)
        return math.sqrt(float(np.mean(m_mono[i:j] ** 2)) + 1e-12)

    events = [(t, k, 'boom') for (t, k) in IMPACTS] + list(CUTS)
    log = []
    for (t, k, kind) in events:
        x = {'boom': sfx_boom, 'subdrop': sfx_subdrop, 'thud': sfx_thud}[kind](k)
        x = signal.sosfilt(LPS, x)
        x = signal.sosfilt(LPS, x)
        w = 0.6
        ex = math.sqrt(float(np.mean(x[:S(w)] ** 2)))
        mu = local_rms(t, w)
        target = mu * 10 ** (-(4.0 + (1 - k) * 6) / 20)   # 比音乐低 4 dB（弱音效更低）
        g = target / ex
        add_mono(out, x * g, t)
        log.append((t, kind, 20 * math.log10(mu), 20 * math.log10(target)))
    for (t0, t1) in SWELLS:
        x = signal.sosfilt(LPS, sfx_swell(t1 - t0))
        ex = math.sqrt(float(np.mean(x[-S(1.0):] ** 2)))
        mu = local_rms(t1 - 1.0, 1.0)
        g = mu * 10 ** (-6 / 20) / ex
        add_mono(out, x * g, t0)
        log.append((t0, 'swell', 20 * math.log10(mu), 20 * math.log10(mu) - 6))
    return out, log


def add_mono(buf, x, t):
    i = S(t); j = min(i + len(x), N)
    buf[i:j] += x[:j - i]


def leveler(x, target_db=-12.5, strength=0.4, lo=0.85, hi=1.8):
    """慢速电平器：响的地方几乎不动，安静段适度抬高，保留「安静 → 高潮」的起伏"""
    from scipy.ndimage import uniform_filter1d
    ms = uniform_filter1d(x.mean(1) ** 2, S(0.4))
    g = (10 ** (target_db / 20) / np.sqrt(ms + 1e-10)) ** strength
    g = uniform_filter1d(np.clip(g, lo, hi), S(1.5))
    return x * g[:, None]


def limiter(x, ceiling=0.89):
    """前视峰值限制器（5 ms），避免削波失真"""
    look = S(0.005)
    peak = np.abs(x).max(1)
    from scipy.ndimage import maximum_filter1d, uniform_filter1d
    pk = maximum_filter1d(peak, size=2 * look + 1)
    g = np.minimum(1.0, ceiling / np.maximum(pk, 1e-9))
    # 平滑增益（快攻慢放）
    g = -maximum_filter1d(-g, size=2 * look + 1)
    g = uniform_filter1d(g, size=look)
    return x * g[:, None]


if __name__ == '__main__':
    W = sys.argv[1]
    os.makedirs(W, exist_ok=True)
    music = compose()
    # 响度：高潮段 RMS 调到约 −12.5 dBFS，再用慢速电平器把安静段托起来（最多 +5 dB）
    seg = music[S(b(41)):S(b(57))]
    g = 10 ** (-12.5 / 20) / math.sqrt(float(np.mean(seg ** 2)))
    music *= g
    music = leveler(music)
    # 结尾淡出（与画面最终淡出同步）
    f0, f1 = S(b(97)), N
    music[f0:f1] *= np.linspace(1, 0, f1 - f0)[:, None] ** 1.6
    sfx, log = build_sfx(music)
    sf.write(os.path.join(W, 'bgm.wav'), limiter(music).astype(np.float32), SR)
    sf.write(os.path.join(W, 'sfx.wav'), np.stack([sfx, sfx], 1).astype(np.float32), SR)
    mix = limiter(music + sfx[:, None])
    sf.write(os.path.join(W, 'mix.wav'), mix.astype(np.float32), SR)
    for r in log:
        print('%7.2f %-8s music %6.1f dB  sfx %6.1f dB' % r)
    print('peak', np.abs(mix).max(), 'dur', len(mix) / SR)
