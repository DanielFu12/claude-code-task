"""《科学思维》原创配乐 + 旁白混音（全部 numpy 合成）。

D 小调，100 BPM；每个章节从重拍开始重新起拍，重拍前 0.3 秒抽空，配合上扬音效。
画面上的关键事件（硬币每过一天、黑天鹅推翻命题、四道检验门、诺贝尔奖……）都有对应的音效点。
最后混入旁白（自动压低音乐），响度标准化到 −14 LUFS。

用法：python3 src/music.py work/   → work/score.wav（48 kHz 立体声）
"""
import math
import os
import sys

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as T  # noqa: E402

WORK = sys.argv[1] if len(sys.argv) > 1 else T.WORK
SR = 48000
N = int((T.DUR + 0.5) * SR)
BPM = 100
BEAT = 60 / BPM
BAR = 4 * BEAT
rng = np.random.default_rng(2026)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "Ab": 8,
        "A": 9, "A#": 10, "Bb": 10, "B": 11}


def m(s):
    return 12 * (int(s[-1]) + 1) + NOTE[s[:-1]]


CH = {
    "Dm": ["D3", "A3", "D4", "F4", "A4"], "Bb": ["Bb2", "F3", "D4", "F4", "Bb4"], "Gm": ["G2", "D3", "Bb3", "D4", "G4"],
    "A": ["A2", "E3", "C#4", "E4", "A4"], "F": ["F2", "C3", "A3", "C4", "F4"], "C": ["C3", "G3", "E4", "G4", "C5"],
    "Am": ["A2", "E3", "C4", "E4", "A4"], "D": ["D3", "A3", "D4", "F#4", "A4"], "Bbmaj7": ["Bb2", "F3", "A3", "D4", "F4"],
    "Gm9": ["G2", "D3", "A3", "Bb3", "F4"], "Dsus": ["D3", "A3", "D4", "G4", "A4"],
}


class Bus:
    def __init__(self):
        self.x = np.zeros((2, N), np.float32)

    def add(self, t, sig, gain=1.0, pan=0.0):
        i0 = int(round(t * SR))
        if sig.ndim == 1:
            l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
            sig = np.stack([sig * l * 1.414, sig * r * 1.414])
        n = sig.shape[1]
        a, b = max(i0, 0), min(i0 + n, N)
        if b > a:
            self.x[:, a:b] += (sig[:, a - i0:b - i0] * gain).astype(np.float32)


# ---------------------------------------------------------------- 振荡器与乐器
_TAB = 4096
_ph = np.arange(_TAB) / _TAB
SAW_TAB = sum(np.sin(2 * np.pi * k * _ph) / k for k in range(1, 48)) * (2 / np.pi)


def saw(f, n, ph0=0.0):
    ph = (ph0 + np.cumsum(np.full(n, f / SR))) % 1.0
    return np.interp(ph * _TAB, np.arange(_TAB), SAW_TAB)


def env(n, a, r, hold=None):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4))
    rel_start = (n / SR - r) if hold is None else hold
    e *= np.clip(1 - (t - rel_start) / r, 0, 1)
    return e


def lowpass(x, fc, order=2):
    b, a = signal.butter(order, min(fc, SR / 2 * 0.95) / (SR / 2), "low")
    return signal.lfilter(b, a, x)


def highpass(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), "high")
    return signal.lfilter(b, a, x)


def bandpass(x, f0, f1, order=2):
    b, a = signal.butter(order, [f0 / (SR / 2), min(f1, SR / 2 * 0.95) / (SR / 2)], "band")
    return signal.lfilter(b, a, x)


def pad_note(f, dur, cutoff=1400, att=0.9, rel=1.4):
    n = int((dur + rel) * SR)
    x = sum(saw(f * d, n, rng.random()) for d in (0.994, 1.0, 1.006))
    x = lowpass(x, cutoff) * env(n, att, rel, dur)
    return x / 3


def pluck(f, dur=0.45, bright=2.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    I = bright * np.exp(-t / 0.08)
    x = np.sin(2 * np.pi * f * t + I * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / (dur * 0.35))
    return x * np.minimum(1, t / 0.003)


def bell(f, dur=2.5, ratio=3.5, idx=2.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t + idx * np.exp(-t / 0.6) * np.sin(2 * np.pi * ratio * f * t)) * np.exp(-t / (dur * 0.3))
    return x * np.minimum(1, t / 0.002)


def piano(f, dur=3.0, vel=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k in range(1, 9):
        fk = f * k * math.sqrt(1 + 0.0004 * k * k)
        if fk > SR / 2.2:
            break
        x += np.sin(2 * np.pi * fk * t + rng.random()) * (0.7 ** (k - 1)) * np.exp(-t * (0.9 + 0.55 * k) * (f / 260) ** 0.3)
    x *= np.minimum(1, t / 0.004)
    ham = highpass(rng.normal(0, 1, min(n, 2000)), 1500) * np.exp(-np.arange(min(n, 2000)) / 300) * 0.04
    x[:len(ham)] += ham
    return x * vel


def kick(gain=1.0, f0=110, f1=42, dec=0.35):
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.04)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / dec)
    x[:200] += rng.normal(0, 0.3, 200) * np.exp(-np.arange(200) / 40)
    return x * gain


def hat(dec=0.04, gain=0.25):
    n = int(0.25 * SR)
    x = highpass(rng.normal(0, 1, n), 7000) * np.exp(-np.arange(n) / SR / dec)
    return x * gain


def clap(gain=0.35):
    n = int(0.4 * SR)
    t = np.arange(n) / SR
    e_ = sum(np.exp(-np.maximum(t - d, 0) / 0.012) * (t >= d) for d in (0, 0.011, 0.023)) + 0.6 * np.exp(-t / 0.12)
    return bandpass(rng.normal(0, 1, n), 900, 5000) * e_ * gain


def tick(f=2600, gain=0.25):
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * f * t) * np.exp(-t / 0.006) * gain


def braam(root="D1", dur=4.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = sum(saw(hz(m(nn)) * d, n, rng.random()) for nn in (root, root[:-1] + str(int(root[-1]) + 1), "A1")
            for d in (0.997, 1.003))
    cut = 180 + 1800 * np.exp(-t / 0.5) * np.minimum(1, t / 0.05)
    # 时变低通：分段处理
    out = np.zeros(n)
    seg = 2400
    zi = None
    for i in range(0, n, seg):
        b, a = signal.butter(2, cut[i] / (SR / 2), "low")
        if zi is None:
            zi = signal.lfilter_zi(b, a) * 0
        out[i:i + seg], zi = signal.lfilter(b, a, x[i:i + seg], zi=zi)
    out = np.tanh(out * 1.8) * np.exp(-t / (dur * 0.45)) * np.minimum(1, t / 0.02)
    return out


def subdrop(dur=2.2, f0=80, f1=28):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.5)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (dur * 0.4))


def boom(dur=2.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = lowpass(rng.normal(0, 1, n), 160, 4) * np.exp(-t / 0.5) * 3
    return x + subdrop(dur) * 0.9


def riser(dur=2.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    k = (t / dur) ** 2
    noise = rng.normal(0, 1, n)
    out = np.zeros(n)
    seg = 2400
    for i in range(0, n, seg):
        fc = 300 + 7000 * k[i]
        out[i:i + seg] = bandpass(noise[max(0, i - 600):i + seg], fc * 0.6, fc * 1.4)[-len(noise[i:i + seg]):]
    tone = np.sin(2 * np.pi * np.cumsum(220 + 660 * k) / SR) * 0.15
    return (out * 0.7 + tone) * k * 0.9


def whoosh(dur=0.9):
    n = int(dur * SR)
    t = np.arange(n) / SR
    k = np.sin(np.pi * t / dur) ** 2
    return bandpass(rng.normal(0, 1, n), 400, 3500) * k * 0.6


def crack():
    n = int(0.8 * SR)
    t = np.arange(n) / SR
    x = highpass(rng.normal(0, 1, n), 2000) * np.exp(-t / 0.03) * 0.8
    k = kick(0.9, 90, 38, 0.3)
    x[:len(k)] += k * 0.9
    return x


# ---------------------------------------------------------------- 编曲
pad, bass, drums, arp, keys, fx = Bus(), Bus(), Bus(), Bus(), Bus(), Bus()
SEC = T.SEC
HITS = T.HITS


def bars(sec):
    a, b = SEC[sec]
    k = 0
    while a + k * BAR < b - 0.2:
        yield k, a + k * BAR
        k += 1


def chord_pad(sec, prog, gain=0.12, cutoff=1300, top=4, bars_per=1):
    cutoff = cutoff * 1.8
    a, b = SEC[sec]
    for k, t in bars(sec):
        ch = CH[prog[(k // bars_per) % len(prog)]]
        dur = min(BAR * bars_per, b - t) if k % bars_per == 0 else None
        if dur is None:
            continue
        for i, nn in enumerate(ch[1:top + 1]):
            pad.add(t, pad_note(hz(m(nn)), dur, cutoff), gain, pan=(i - 1.5) * 0.35)
        # 高八度的“空气”层：手机扬声器上也听得见和声
        for i, nn in enumerate(ch[2:4]):
            pad.add(t, pad_note(hz(m(nn) + 12), dur, 5000, att=1.2), gain * 0.35, pan=(-0.6, 0.6)[i])


def bassline(sec, prog, gain=0.32, pattern=(0, 2), bars_per=1, octave=-12):
    a, b = SEC[sec]
    for k, t in bars(sec):
        ch = CH[prog[(k // bars_per) % len(prog)]]
        f = hz(m(ch[0]) + 12 + octave)
        for p in pattern:
            tt = t + p * BEAT
            if tt < b - 0.3:
                n = int(BEAT * 1.6 * SR)
                tt_ = np.arange(n) / SR
                x = np.tanh(2.2 * np.sin(2 * np.pi * f * tt_)) * 0.7 + 0.25 * np.sin(4 * np.pi * f * tt_)
                bass.add(tt, x * env(n, 0.01, 0.25), gain * 0.6)


def groove(sec, start=0.0, kick_on=(0, 2), hat_on=True, clap_on=(), gain=1.0, end=None, tick_mode=False):
    a, b = SEC[sec]
    b = end or b
    for k, t in bars(sec):
        if t < a + start:
            continue
        for bt in range(4):
            tt = t + bt * BEAT
            if tt > b - 0.35:
                break
            if bt in kick_on:
                drums.add(tt, kick(0.5 * gain))
            if bt in clap_on:
                drums.add(tt, clap(0.3 * gain), pan=0.1)
            if hat_on:
                drums.add(tt + BEAT / 2, hat(gain=0.26 * gain), pan=0.3)
            if tick_mode:
                drums.add(tt, tick(2400 if bt % 2 == 0 else 1800, 0.18 * gain), pan=-0.2)


def arpeggio(sec, prog, start=0.0, gain=0.10, step=0.25, bright=2.0, inst="pluck", end=None, octave=12):
    a, b = SEC[sec]
    b = end or b
    order = [0, 2, 1, 3, 2, 4, 3, 1]
    for k, t in bars(sec):
        if t < a + start:
            continue
        ch = CH[prog[k % len(prog)]]
        n = int(4 / step)
        for i in range(n):
            tt = t + i * step * BEAT
            if tt > b - 0.35:
                break
            f = hz(m(ch[1 + order[i % 8] % 4]) + octave)
            sig = pluck(f, 0.5, bright) if inst == "pluck" else bell(f, 1.6, 3.5, 1.4)
            arp.add(tt, sig, 1.6 * gain * (1.0 if i % 4 == 0 else 0.7), pan=0.4 * math.sin(i))


def motif(t0, notes, gain=0.22, step=BEAT, oct_=0):
    for i, nn in enumerate(notes):
        if nn is None:
            continue
        keys.add(t0 + i * step, piano(hz(m(nn) + oct_), 3.2), gain, pan=-0.15)


MOTIF = ["A4", "D5", "E5", "F5", None, "E5", "D5", "A4"]

# ---- 0 钩子：低鸣 + 秒针 + 钢琴动机
a, b = SEC["hook"]
for nn, g in (("D2", 0.10), ("A2", 0.07), ("D3", 0.05)):
    pad.add(0.3, pad_note(hz(m(nn)), b - 0.6, 500, att=3.0, rel=0.8), g)
for i in range(int((b - 1.0) / (BEAT))):
    tt = 1.0 + i * BEAT
    if tt < b - 0.4:
        drums.add(tt, tick(2200 if i % 2 == 0 else 1700, 0.10), pan=-0.3)
motif(1.0, ["A4", "D5", "E5", "F5"], 0.16, BEAT * 1.0)
keys.add(T.s("h3"), piano(hz(m("D4")), 4.0), 0.18)
keys.add(T.s("h3"), piano(hz(m("F4")), 4.0), 0.12)
keys.add(T.s("h3"), piano(hz(m("A4")), 4.0), 0.12)
keys.add(T.s("h4"), piano(hz(m("C#5")), 3.0), 0.16)

# ---- 1 放血：心跳 → 停止 → 慢律动
chord_pad("blood", ["Dm", "Bb", "Gm", "A"], 0.10, 900)
a, b = SEC["blood"]
for i in range(60):
    tt = a + 0.4 + i * 1.0
    if tt > T.s("b3") + 0.4:
        break
    drums.add(tt, kick(0.45, 75, 45, 0.16))
    drums.add(tt + 0.22, kick(0.28, 70, 42, 0.13))
fx.add(T.s("b3") + 0.4, np.sin(2 * np.pi * 880 * np.arange(int(1.6 * SR)) / SR) * env(int(1.6 * SR), 0.01, 0.4), 0.035)
bassline("blood", ["Dm", "Bb", "Gm", "A"], 0.22, (0,))
groove("blood", start=T.s("b4") - a, kick_on=(0,), hat_on=False, gain=0.6)
motif(T.s("b6"), ["D5", "A4", "F4", "E4"], 0.15, BEAT / 2)

# ---- 标题：braam + 合唱般的长和弦
a, b = SEC["title"]
for nn in CH["Dsus"]:
    pad.add(a, pad_note(hz(m(nn)), b - a, 2200, att=0.05, rel=1.5), 0.10)

# ---- 01 相关≠因果：好奇的拨弦律动
chord_pad("cause", ["Dm", "F", "C", "Bb"], 0.07, 1500)
bassline("cause", ["Dm", "F", "C", "Bb"], 0.26, (0, 1.5, 2.5))
arpeggio("cause", ["Dm", "F", "C", "Bb"], 0.0, 0.07, 0.5, 2.0)
groove("cause", start=T.s("c2") - SEC["cause"][0], kick_on=(0, 2), clap_on=(1, 3), gain=0.6)

# ---- 02 可证伪：渐强的史诗感
chord_pad("falsify", ["Dm", "Bb", "F", "C"], 0.09, 1200)
bassline("falsify", ["Dm", "Bb", "F", "C"], 0.26, (0, 2))
groove("falsify", kick_on=(0,), hat_on=True, gain=0.55, end=T.s("f3"))
groove("falsify", start=T.s("f3") - SEC["falsify"][0], kick_on=(0, 2, 3), hat_on=True, clap_on=(2,), gain=0.7)
arpeggio("falsify", ["Dm", "Bb", "F", "C"], T.s("f3") - SEC["falsify"][0], 0.06, 0.25, 1.5)

# ---- 03 伪科学：音乐盒
chord_pad("barnum", ["Gm", "Dm", "A", "Dm"], 0.07, 1000)
arpeggio("barnum", ["Gm", "Dm", "A", "Dm"], 0.0, 0.08, 0.5, inst="bell", octave=24)
bassline("barnum", ["Gm", "Dm", "A", "Dm"], 0.2, (0, 2))
groove("barnum", start=T.s("m2") - SEC["barnum"][0], kick_on=(0,), hat_on=True, gain=0.45)

# ---- 04 纠错：转向希望（大调色彩）
chord_pad("correct", ["F", "C", "Dm", "Bb"], 0.10, 1600)
bassline("correct", ["F", "C", "Dm", "Bb"], 0.24, (0, 2))
arpeggio("correct", ["F", "C", "Dm", "Bb"], 0.0, 0.06, 0.5, 1.2)
groove("correct", start=T.s("k2") - SEC["correct"][0], kick_on=(0, 2), clap_on=(), gain=0.5, end=T.s("k4"))
motif(T.s("k4"), ["C5", "F5", "G5", "A5", None, "G5", "F5", "C5"], 0.13, BEAT)

# ---- 05 投资：秒针 + 律动
chord_pad("invest", ["Dm", "Bb", "F", "C"], 0.08, 1400)
bassline("invest", ["Dm", "Bb", "F", "C"], 0.28, (0, 1.5, 2, 3.5))
groove("invest", kick_on=(0, 2), clap_on=(1, 3), gain=0.65, tick_mode=True)
arpeggio("invest", ["Dm", "Bb", "F", "C"], T.s("i5") - SEC["invest"][0], 0.06, 0.25, 2.2)

# ---- 终章：钢琴动机回归 → D 大调
chord_pad("end", ["Bb", "F", "C", "Dm"], 0.10, 1300)
motif(SEC["end"][0] + 0.2, MOTIF, 0.16, BEAT)
a, b = SEC["end"]
bassline("end", ["Bb", "F", "C", "Dm"], 0.2, (0,))
# 片尾：重拍上 D 大调长和弦
for nn in CH["D"] + ["D5", "F#5"]:
    pad.add(T.BRAND_T, pad_note(hz(m(nn)), T.DUR - T.BRAND_T - 0.8, 2400, att=0.03, rel=2.0), 0.09)
keys.add(T.BRAND_T, piano(hz(m("D3")), 6.0), 0.25)
keys.add(T.BRAND_T, piano(hz(m("F#4")), 6.0), 0.15)
keys.add(T.BRAND_T, piano(hz(m("A4")), 6.0), 0.15)
keys.add(T.BRAND_T, piano(hz(m("D5")), 6.0), 0.15)
# logo 汇聚：上扬的泛音
for i, nn in enumerate(["D5", "F#5", "A5", "D6", "F#6", "A6"]):
    arp.add(T.LOGO_T + i * 0.28, bell(hz(m(nn)), 2.0, 2.0, 0.8), 0.07, pan=(i - 2.5) * 0.25)

# ---------------------------------------------------------------- 重拍与音效点
for h in HITS:
    fx.add(h - 2.6, riser(2.6), 0.20)
    big = h in (SEC["title"][0], T.BRAND_T)
    fx.add(h, braam("D1", 4.5 if big else 3.0), 0.30 if big else 0.18)
    fx.add(h, boom(), 0.30 if big else 0.18)
    drums.add(h, kick(0.7, 120, 45, 0.4))
    # 高频的“闪光”：铙钹般的噪声 + 钟声
    nn_ = int(2.5 * SR)
    fx.add(h, highpass(rng.normal(0, 1, nn_), 5000) * np.exp(-np.arange(nn_) / SR / 0.6) * 0.5, 0.10)
    arp.add(h, bell(hz(m("D6")), 2.5, 2.0, 1.0), 0.08)
# 黑天鹅推翻命题
fx.add(T.at("f2", "一只黑天鹅") + 0.6, crack(), 0.45)
# 星光真的偏了
for i, nn in enumerate(["A5", "D6", "E6", "A6"]):
    arp.add(T.s("f5") + 0.2 + i * 0.12, bell(hz(m(nn)), 2.2, 2.0, 0.8), 0.08)
# 四道检验门
for k in ["能被证伪", "能被重复", "有可测量", "会随新证据"]:
    arp.add(T.at("m5", k), bell(hz(m("A5")), 1.4, 3.0, 1.0), 0.09)
# 福勒：卡片叠成一张
fx.add(T.s("m3") + 0.1, whoosh(1.2), 0.25)
# 马歇尔：共识碎裂 / 诺贝尔奖
fx.add(T.s("k3") + 0.4, crack(), 0.4)
for i, nn in enumerate(["F5", "A5", "C6", "F6"]):
    arp.add(T.at("k3", "2005") + i * 0.1, bell(hz(m(nn)), 2.4, 2.0, 0.6), 0.08)
# 硬币：每过一天一声
t0c, t1c = T.at("i2", "每天猜"), T.at("i2", "二十天后")
for d in range(1, 21):
    tt = t0c + d / 20 * (t1c + 1.2 - t0c)
    arp.add(tt, bell(hz(m("E6") + (d % 2) * 5), 0.6, 4.1, 1.2), 0.05 + 0.002 * d, pan=0.3 * (-1) ** d)
# 五个步骤
for k in ["提出假设", "写下什么", "查看基础", "主动寻找", "随新信息"]:
    arp.add(T.at("i7", k), pluck(hz(m("D5")), 0.6, 1.0), 0.12)
# 每段转场的轻声 whoosh
for k in ["c5", "c6", "f3", "f6", "f7", "m4", "k4", "i4", "i5", "i6", "i8", "e2"]:
    fx.add(T.s(k) - 0.5, whoosh(0.9), 0.12)

# ---------------------------------------------------------------- 重拍前抽空（除音效外）
gate = np.ones(N, np.float32)
for h in HITS:
    i0, i1 = int((h - 0.30) * SR), int(h * SR)
    ramp = int(0.05 * SR)
    gate[i0:i1] = 0.0
    gate[i0 - ramp:i0] = np.minimum(gate[i0 - ramp:i0], np.linspace(1, 0, ramp))
for bus in (pad, bass, drums, arp, keys):
    bus.x *= gate


# ---------------------------------------------------------------- 混音
def reverb_ir(sec=2.8, seed=1):
    r = np.random.default_rng(seed)
    n = int(sec * SR)
    t = np.arange(n) / SR
    irs = []
    for _ in range(2):
        x = r.normal(0, 1, n) * np.exp(-t / (sec / 6.5))
        x = lowpass(x, 6000)
        irs.append(x / np.sqrt((x ** 2).sum()))
    return np.stack(irs)


IR = reverb_ir()


def verb(x, wet):
    out = np.stack([signal.fftconvolve(x[c_], IR[c_])[:N] for c_ in range(2)])
    return x + wet * out


music = (verb(pad.x, 0.9) * 1.0 + bass.x * 1.0 + verb(drums.x, 0.12) * 1.0 + verb(arp.x, 0.6) + verb(keys.x, 0.5) +
         verb(fx.x, 0.35))
music = highpass(music, 35, 2)


def shelf(x, f0, gain_db, kind):
    """RBJ 搁架滤波器。"""
    A = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * f0 / SR
    al = math.sin(w0) / 2 * math.sqrt(2)
    cw = math.cos(w0)
    if kind == "low":
        b = [A * ((A + 1) - (A - 1) * cw + 2 * math.sqrt(A) * al), 2 * A * ((A - 1) - (A + 1) * cw),
             A * ((A + 1) - (A - 1) * cw - 2 * math.sqrt(A) * al)]
        a = [(A + 1) + (A - 1) * cw + 2 * math.sqrt(A) * al, -2 * ((A - 1) + (A + 1) * cw),
             (A + 1) + (A - 1) * cw - 2 * math.sqrt(A) * al]
    else:
        b = [A * ((A + 1) + (A - 1) * cw + 2 * math.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * cw),
             A * ((A + 1) + (A - 1) * cw - 2 * math.sqrt(A) * al)]
        a = [(A + 1) - (A - 1) * cw + 2 * math.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * cw),
             (A + 1) - (A - 1) * cw - 2 * math.sqrt(A) * al]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x)


# 频谱倾斜：压低超低频、提亮高频，让手机扬声器也能听清配乐
music = shelf(music, 110, -6, "low")
music = shelf(music, 2500, 5, "high")

# 旁白
vo = np.zeros(N, np.float32)
for lid in T.ORDER:
    t0_, t1_, sub = T.LINES[lid]
    if t1_ <= t0_:
        continue
    x, sr = sf.read(os.path.join(WORK, "vo", lid + ".wav"), dtype="float32")
    x = signal.resample_poly(x, SR, sr)
    i0 = int(t0_ * SR)
    vo[i0:i0 + len(x)] += x[:N - i0]
vo = highpass(vo, 75, 2)
# 轻微提亮（存在感 3 kHz 附近）
vo = vo + 0.25 * bandpass(vo, 2500, 6000)
# 柔和压缩
envv = np.abs(vo)
envv = lowpass(envv, 20, 1)
gain_c = np.where(envv > 0.15, (0.15 / np.maximum(envv, 1e-6)) ** 0.4, 1.0)
vo = vo * gain_c
vo /= np.abs(vo).max() + 1e-9
# 音乐让位给旁白
speech = lowpass(np.abs(vo), 6, 1)
speech = np.clip(speech / (np.percentile(speech[speech > 1e-3], 70) + 1e-9), 0, 1)
duck = 1 - 0.70 * speech
music *= duck[None, :]
music /= np.abs(music).max() + 1e-9
mix = music * 0.60 + np.stack([vo, vo]) * 0.70
# 结尾淡出
fo = int(1.6 * SR)
mix[:, -int(0.5 * SR) - fo:-int(0.5 * SR)] *= np.linspace(1, 0, fo) ** 1.5
mix[:, -int(0.5 * SR):] = 0
fi = int(0.4 * SR)
mix[:, :fi] *= np.linspace(0, 1, fi)

try:
    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    lufs = meter.integrated_loudness(mix.T)
    mix *= 10 ** ((-14 - lufs) / 20)
    print("loudness", round(lufs, 1), "→ -14 LUFS")
except Exception as ex:   # noqa: BLE001
    print("pyloudnorm unavailable:", ex)
    mix *= 0.5 / np.sqrt((mix ** 2).mean())
# 简单限幅：峰值 -1 dBFS
peak = 10 ** (-1 / 20)
knee = 0.8 * peak
ax = np.abs(mix)
mix = np.where(ax > knee, np.sign(mix) * (knee + (peak - knee) * np.tanh((ax - knee) / (peak - knee))), mix)
sf.write(os.path.join(WORK, "score.wav"), mix.T.astype(np.float32), SR, subtype="PCM_24")
sf.write(os.path.join(WORK, "music_only.wav"), (music * 0.60).T.astype(np.float32), SR, subtype="PCM_24")
print("written", os.path.join(WORK, "score.wav"), round(N / SR, 2), "s")
