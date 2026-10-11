"""《科学思维》原创卡点配乐（全部 numpy 合成，全片无配音）。

D 小调，100 BPM，与画面共用 timeline.py 的节拍网格（第 0 小节从 0.5 s 开始）。
- 每章第一拍是重拍（braam + 低频冲击 + 镲），重拍前 0.3 秒全体抽空、画面同时推入黑场。
- T.ACCENTS 里的画面揭示点（黑天鹅、星光偏折、4.26 分、诺贝尔奖、215 位股神……）都落在拍点上并配打击。
- 主题动机 A–D–E–F 贯穿：标题、可证伪的高潮、纠错（转大调）、终章钢琴，最后在 D 大调上落地。
- 底鼓侧链压缩让铺底随节拍呼吸；响度 −15 LUFS，真峰值 ≤ −2.5 dBTP（压缩编码后仍不过载）。

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


MOTIF = ["A4", "D5", "E5", "F5", "E5", "D5", "C5", "A4"]
MOTIF_MAJ = ["C5", "F5", "G5", "A5", "G5", "F5", "E5", "C5"]


def snare(gain=0.4):
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.05)
    nz = bandpass(rng.normal(0, 1, n), 1200, 8000) * np.exp(-t / 0.12)
    return (body * 0.6 + nz) * gain


def crash(gain=0.3, dur=2.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = highpass(rng.normal(0, 1, n), 4500) * np.exp(-t / (dur * 0.35))
    x += 0.3 * np.sin(2 * np.pi * 5200 * t + 3 * np.sin(2 * np.pi * 7300 * t)) * np.exp(-t / 0.5)
    return x * gain


def tom(f0=150, gain=0.5):
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    f = f0 * (0.65 + 0.35 * np.exp(-t / 0.08))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.22) * gain


def lead(f, dur, gain=1.0):
    """温暖的主奏：两支微失谐锯齿 + 正弦，带延迟颤音。"""
    n = int((dur + 0.4) * SR)
    t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - 0.25) / 0.3, 0, 1)
    ph = np.cumsum(f * vib) / SR
    x = (np.interp((ph * 1.003) % 1 * _TAB, np.arange(_TAB), SAW_TAB) +
         np.interp((ph * 0.997) % 1 * _TAB, np.arange(_TAB), SAW_TAB)) * 0.5
    x = lowpass(x, 2600) * 0.6 + np.sin(2 * np.pi * ph) * 0.5
    return x * env(n, 0.03, 0.4, dur) * gain


def stab(chord, gain=0.2, dur=1.2):
    """和弦重音（钢琴 + 铺底的短促一击）。"""
    n = int((dur + 1.0) * SR)
    out = np.zeros(n)
    for nn in CH[chord][1:]:
        p_ = piano(hz(m(nn)), dur + 1.0)[:n]
        q_ = pad_note(hz(m(nn)), dur * 0.4, 3000, att=0.01, rel=0.8)[:n]
        out[:len(p_)] += p_ * 0.5
        out[:len(q_)] += q_ * 0.6
    return out * gain


KICKS = []          # 记录所有底鼓时刻，用于侧链


def K(t, g=0.6, **kw):
    drums.add(t, kick(g, **kw))
    KICKS.append((t, g))


def melody(t0, notes, step=BEAT, gain=0.12, oct_=0, dur=None):
    for i, nn in enumerate(notes):
        if nn:
            arp.add(t0 + i * step, lead(hz(m(nn) + oct_), dur or step * 0.9), gain, pan=0.1)


def pattern(sec, t_from, t_to, kick_on=(0, 2), snare_on=(1, 3), hats=8, hat_g=0.2, kick_g=0.6, snare_g=0.32,
            ticks=False):
    """在 [t_from, t_to) 内按小节铺鼓组（全片统一网格）。"""
    a, b = SEC[sec]
    t_to = min(t_to, b)
    for k, t in bars(sec):
        for bt in range(4):
            tt = t + bt * BEAT
            if tt < t_from - 1e-6 or tt > t_to - 0.32:
                continue
            if bt in kick_on:
                K(tt, kick_g)
            if bt in snare_on:
                drums.add(tt, snare(snare_g), pan=0.05)
            if hats:
                sub = hats // 4
                for j in range(sub):
                    th = tt + j * BEAT / sub
                    if th < t_to - 0.32:
                        drums.add(th, hat(0.03 if j % 2 else 0.05, hat_g * (0.6 if j % 2 else 1.0)), pan=0.3)
            if ticks:
                drums.add(tt, tick(2400 if bt % 2 == 0 else 1800, 0.14), pan=-0.25)


def hit_fx(t, big=1.0, chord="Dm"):
    fx.add(t, braam("D1", 3.5 if big > 0.8 else 2.5), 0.22 * big)
    fx.add(t, boom(), 0.22 * big)
    fx.add(t, crash(0.5 * big), 1.0, pan=0.2)
    K(t, 0.75 * big, f0=120, f1=45, dec=0.4)
    keys.add(t, stab(chord, 0.25 * big), 1.0)


def accent(t, kind="mid", chord="Dm"):
    if kind == "big":
        fx.add(t, boom(1.8), 0.20)
        fx.add(t, crash(0.35), 1.0, pan=-0.2)
        K(t, 0.7)
        keys.add(t, stab(chord, 0.22), 1.0)
    elif kind == "mid":
        K(t, 0.55)
        drums.add(t, snare(0.3))
        fx.add(t, crash(0.18, 1.5), 1.0, pan=0.3)
    elif kind == "bell":
        arp.add(t, bell(hz(m("D6")), 2.0, 2.0, 0.9), 0.10)
        arp.add(t, bell(hz(m("A5")), 2.0, 2.0, 0.9), 0.07, pan=0.4)
    elif kind == "crack":
        fx.add(t, crack(), 0.45)
        fx.add(t, boom(1.5), 0.15)


s_, e_, at = T.s, T.e, T.at
B, BR = BEAT, BAR

# ================================================================ 0 钩子：四记重拍
a, b = SEC["hook"]
for nn, g in (("D1", 0.14), ("D2", 0.10), ("A2", 0.06)):
    pad.add(0.0, pad_note(hz(m(nn)), b - 0.4, 420, att=4.0, rel=0.4), g)
punch_ch = ["Dm", "Bb", "Gm", "A"]
for i, h in enumerate(["h1", "h2", "h3", "h4"]):
    tt = s_(h)
    big = 1.0 if i == 3 else 0.75
    fx.add(tt, boom(2.0), 0.28 * big)
    fx.add(tt, braam("D1", 2.2), 0.16 * big)
    K(tt, 0.8 * big, f0=120, f1=40, dec=0.45)
    keys.add(tt, stab(punch_ch[i], 0.30, 1.6), 1.0)
    fx.add(tt, crash(0.25 * big, 2.0), 1.0, pan=(-0.3, 0.3, -0.2, 0.2)[i])
# 秒针：越来越密
for k in range(int((b - 0.5) / (B / 2))):
    tt = 0.5 + k * B / 2
    dense = tt > s_("h3")
    if tt < b - 0.35 and (k % 2 == 0 or dense):
        drums.add(tt, tick(2400 if k % 4 == 0 else 1800, 0.10 + 0.08 * (tt / b)), pan=-0.3)
for j in range(8):                      # 最后一小节的军鼓滚奏
    tt = s_("h4") + 2 * B + j * B / 4
    if tt < b - 0.32:
        drums.add(tt, snare(0.10 + 0.03 * j), pan=0.1)

# ================================================================ 1 返航战机：低鸣 → 弹孔打点 → 抽空 →「恰恰相反」→ 坠落
WALD = ["Dm", "Bb", "Gm", "A"]
a, b = SEC["wald"]
chord_pad("wald", WALD, 0.08, 900)
bassline("wald", WALD, 0.22, (0, 2))
# 螺旋桨低鸣：低通噪声 + 两支微失谐低音锯齿，随入场渐强
n_ = int((T.s("w6") - a) * SR)
tt_ = np.arange(n_) / SR
drone = lowpass(rng.normal(0, 1, n_), 180, 2) * 2.0 + (saw(55, n_) + saw(55.7, n_)) * 0.25
drone *= np.minimum(1, tt_ / 3.0) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.25 * tt_)) * np.clip((T.s("w6") - a - tt_) / 0.4, 0, 1)
fx.add(a, lowpass(drone, 400, 2), 0.10)
# 军鼓进行曲：w1 起
pattern("wald", T.s("w1"), T.s("w5"), kick_on=(0, 2), snare_on=(1, 3), hats=8, hat_g=0.12, kick_g=0.45, snare_g=0.22)
# 弹孔：与画面同一公式——每个弹孔一声极短的金属「嗒」（量化到十六分音符，避免过密）
h0, h1 = T.s("w3"), T.e("w4")
step = T.BEAT / 4
k_ = 0
tq = h0
while tq < h1 - 1e-6:
    drums.add(tq, tick(3200 + 400 * (k_ % 3), 0.10), pan=0.5 * math.sin(k_ * 1.3))
    if k_ % 4 == 0:
        drums.add(tq, snare(0.10), pan=-0.2)
    tq += step
    k_ += 1
# 「哪里弹孔多，就加固哪里」：上扬，然后在「恰恰相反」前抽空半小节
fx.add(T.s("w6") - 2.4, riser(2.4), 0.14)
gate_dead = (T.s("w6") - 2 * B, T.s("w6"))
accent(T.s("w6"), "big", "Bb")
fx.add(T.s("w6"), braam("D1", 3.0), 0.16)
pattern("wald", T.s("w6"), b, kick_on=(0, 2), snare_on=(2,), hats=8, hat_g=0.14, kick_g=0.55)
for i, nn in enumerate(["D6", "A5", "F5", "D5"]):                  # 发动机亮起：四声钟
    arp.add(T.at("w7", "发动机") + i * B / 2, bell(hz(m(nn)), 1.6, 2.0, 0.8), 0.08, pan=(i - 1.5) * 0.4)
# 坠落的飞机：下行的音高 + 远处的闷响
for j in range(6):
    tg = T.s("w8") + j * 0.36
    n2 = int(2.2 * SR)
    t2 = np.arange(n2) / SR
    f = 900 * np.exp(-t2 / 1.1) + 120
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t2 / 1.2) * 0.4 + lowpass(rng.normal(0, 1, n2), 1500) * np.exp(-t2 / 0.8) * 0.15
    fx.add(T.q(tg), x, 0.07, pan=(-0.6, 0.6, -0.3, 0.3, -0.8, 0.8)[j])
    fx.add(T.q(tg) + 1.6, boom(1.2), 0.05)
accent(T.s("w9"), "bell")
arpeggio("wald", WALD, T.s("w9") - a, 0.05, 0.5, 1.5)
accent(T.s("w10"), "big", "Dm")
for j in range(8):
    tt = b - BR + 2 * B + j * B / 4
    drums.add(tt, snare(0.08 + 0.03 * j))

# ================================================================ 标题：主题动机第一次完整出现
a, b = SEC["title"]
for nn in ["D2", "A2", "D3", "E4", "F4", "A4", "D5"]:
    pad.add(a, pad_note(hz(m(nn)), b - a - 0.2, 2600, att=0.05, rel=1.2), 0.07)
melody(a, MOTIF, B / 2 * 1.0, 0.14, 0, B * 0.45)
melody(a + 4 * B, ["A4", None, "D5", None], B, 0.12)

# ================================================================ 01 相关≠因果：好奇的律动
CAUSE = ["Dm", "F", "C", "Bb"]
a, b = SEC["cause"]
chord_pad("cause", CAUSE, 0.06, 1400)
bassline("cause", CAUSE, 0.26, (0, 1.5, 2.5))
arpeggio("cause", CAUSE, 0.0, 0.07, 0.5, 2.0)
t_neq0, t_neq1 = s_("c5"), s_("c6")
pattern("cause", a, t_neq0, hats=8)
pattern("cause", t_neq1, s_("c7"), kick_on=(0,), snare_on=(3,), hats=8, hat_g=0.12)   # 保健品：放轻
pattern("cause", s_("c7"), b, hats=16, hat_g=0.16)                                  # 随机对照实验：十六分音符更紧
arpeggio("cause", CAUSE, s_("c7") - a, 0.05, 0.25, 2.4, octave=24)
arp.add(at("c6", "是它的功劳"), bell(hz(m("E6")), 1.6, 2.0, 0.9), 0.09)
melody(s_("c3"), ["A4", "D5", "E5", "F5"], B, 0.08)
accent(at("c4", "天越热"), "big", "Bb")
accent(t_neq0, "big", "Dm")                               # 「相关 ≠ 因果」：鼓组停一拍半，只剩重音
accent(at("c7", "抛硬币"), "mid")
accent(s_("c8"), "mid")
for j in range(4):
    drums.add(b - BR + 3 * B + j * B / 4 - 0.3, tom(160 - 18 * j, 0.35))

# ================================================================ 02 可证伪：从半拍到全速，星光偏折是高潮
FALS = ["Dm", "Bb", "F", "C"]
a, b = SEC["falsify"]
chord_pad("falsify", FALS, 0.08, 1300)
bassline("falsify", FALS, 0.26, (0, 2))
pattern("falsify", a, s_("f3"), kick_on=(0,), snare_on=(2,), hats=4, hat_g=0.14)
accent(at("f2", "一只黑天鹅"), "crack")
accent(at("f2", "一只黑天鹅") + 0.0, "big", "Gm")
# 日食：鼓组逐渐加密，嗵鼓推进
pattern("falsify", s_("f3"), s_("f5"), kick_on=(0, 2), snare_on=(), hats=8, hat_g=0.16)
arpeggio("falsify", FALS, s_("f3") - a, 0.06, 0.25, 1.6)
for j in range(8):
    tt = s_("f5") - 2 * B + j * B / 4
    drums.add(tt, tom(170 - 10 * j, 0.32 + 0.03 * j))
fx.add(s_("f5") - 2.4, riser(2.4), 0.16)
# 「星光，真的偏了」：主题在高八度唱响
accent(s_("f5"), "big", "Bb")
fx.add(s_("f5"), braam("D1", 3.0), 0.16)
pattern("falsify", s_("f5"), s_("f7"), kick_on=(0, 2), snare_on=(1, 3), hats=8, hat_g=0.2, kick_g=0.65)
melody(s_("f5"), MOTIF, B, 0.13, 12, B * 0.95)
accent(at("f6", "而在于"), "mid")
pattern("falsify", s_("f7"), b, kick_on=(0,), snare_on=(2,), hats=8, hat_g=0.14)
accent(at("f7", "再画靶"), "bell")

# ================================================================ 03 伪科学的魔术：音乐盒
BARN = ["Gm", "Dm", "A", "Dm"]
a, b = SEC["barnum"]
chord_pad("barnum", BARN, 0.06, 1000)
arpeggio("barnum", BARN, 0.0, 0.07, 0.5, inst="bell", octave=24)
bassline("barnum", BARN, 0.2, (0, 2))
pattern("barnum", s_("m2"), s_("m5"), kick_on=(0, 2), snare_on=(3,), hats=8, hat_g=0.12, kick_g=0.45)
accent(at("m2", "准确度打分"), "bell")
fx.add(s_("m3") - 0.4, whoosh(1.0), 0.3)
accent(s_("m3"), "big", "Gm")
for k_, key in enumerate(["能被证伪", "能被重复", "有可测量", "会随新证据"]):   # 四道门：每道一记
    tg = at("m5", key)
    K(tg, 0.6)
    arp.add(tg, bell(hz(m(["A5", "C6", "D6", "E6"][k_])), 1.8, 3.0, 1.0), 0.10)
pattern("barnum", at("m5", "能被证伪"), b, kick_on=(0,), snare_on=(), hats=16, hat_g=0.10, kick_g=0.4)
t_run = e_("m5") + 0.1
for j in range(5):                       # 五个理论冲过检验门
    arp.add(T.q(t_run) + j * B / 2, pluck(hz(m(["D5", "F5", "A5", "C6", "D6"][j])), 0.5, 1.5), 0.10)

# ================================================================ 04 纠错的机器：转向大调
CORR = ["F", "C", "Dm", "Bb"]
a, b = SEC["correct"]
chord_pad("correct", CORR, 0.09, 1700)
bassline("correct", CORR, 0.24, (0, 2, 2.5))
arpeggio("correct", CORR, 0.0, 0.06, 0.5, 1.2)
pattern("correct", a, s_("k4"), kick_on=(0, 2), snare_on=(1, 3), hats=8, hat_g=0.15, kick_g=0.5)
melody(s_("k1"), MOTIF_MAJ, B, 0.09)
accent(s_("k3"), "crack")
accent(at("k3", "2005"), "big", "F")
for i, nn in enumerate(["F5", "A5", "C6", "F6"]):
    arp.add(at("k3", "2005") + i * B / 2, bell(hz(m(nn)), 2.4, 2.0, 0.6), 0.07)
motif(s_("k4"), ["C5", "F5", "G5", "A5", None, "G5", "F5", "C5"], 0.13, B)
accent(at("k4", "而你自己"), "bell")

# ================================================================ 05 投资：全片最强的律动
INV = ["Dm", "Bb", "F", "C"]
a, b = SEC["invest"]
chord_pad("invest", INV, 0.07, 1500)
bassline("invest", INV, 0.26, (0, 0.5, 1.5, 2, 2.5, 3.5))
pattern("invest", a, s_("i5"), kick_on=(0, 1, 2, 3), snare_on=(1, 3), hats=8, hat_g=0.18, kick_g=0.55, ticks=True)
# 硬币：每淘汰一天一声「叮」（八分音符，与画面计数同步）
for d in range(1, 21):
    tt = T.COIN_T0 + d * T.COIN_STEP
    arp.add(tt, bell(hz(m("E6") + (d % 2) * 5), 0.6, 4.1, 1.2), 0.05 + 0.002 * d, pan=0.3 * (-1) ** d)
accent(T.COIN_T0 + 20 * T.COIN_STEP, "big", "Bb")
accent(at("i4", "那就不是运气"), "big", "F")
# 确认偏误、达尔文：律动收窄
pattern("invest", s_("i5"), s_("i7"), kick_on=(0, 2), snare_on=(3,), hats=8, hat_g=0.14, kick_g=0.5, ticks=True)
arpeggio("invest", INV, s_("i5") - a, 0.05, 0.5, 2.0)
# 五步法：每一步一记，十六分音符推进，主题回归
pattern("invest", s_("i7"), b, kick_on=(0, 1, 2, 3), snare_on=(1, 3), hats=16, hat_g=0.14, kick_g=0.6)
arpeggio("invest", INV, s_("i7") - a, 0.06, 0.25, 2.2)
for key in ["提出假设", "写下什么", "查看基础", "主动寻找", "随新信息"]:
    accent(at("i7", key), "mid")
melody(s_("i8"), MOTIF, B, 0.11, 0, B * 0.9)
accent(at("i8", "这个假设"), "big", "F")

# ================================================================ 终章：钢琴独白 → 再起 → 终句
END = ["Bb", "F", "C", "Dm"]
a, b = SEC["end"]
chord_pad("end", END, 0.08, 1100)
motif(a + 0.05, MOTIF, 0.17, B)
bassline("end", END, 0.18, (0,))
pattern("end", s_("e2"), s_("e3"), kick_on=(0,), snare_on=(2,), hats=8, hat_g=0.12, kick_g=0.45)
accent(at("e1", "而是始终"), "bell")
accent(at("e2", "错得更少"), "mid")
accent(at("e2", "改得更快"), "big", "Bb")
accent(s_("e3"), "big", "Dm")
fx.add(T.LOGO_T - 0.1, riser(T.BRAND_T - T.LOGO_T), 0.14)
for i, nn in enumerate(["D5", "F#5", "A5", "D6", "F#6", "A6"]):     # logo 汇聚：上行的泛音
    arp.add(T.LOGO_T + i * B / 2, bell(hz(m(nn)), 2.0, 2.0, 0.8), 0.07, pan=(i - 2.5) * 0.25)
# 片尾重拍：D 大调落地
for nn in CH["D"] + ["D5", "F#5"]:
    pad.add(T.BRAND_T, pad_note(hz(m(nn)), T.DUR - T.BRAND_T - 0.8, 2400, att=0.03, rel=2.0), 0.08)
for nn, g in (("D3", 0.25), ("F#4", 0.15), ("A4", 0.15), ("D5", 0.15)):
    keys.add(T.BRAND_T, piano(hz(m(nn)), 6.0), g)

# ================================================================ 章节重拍
HIT_CHORD = {}
for name, (a, b) in SEC.items():
    HIT_CHORD[a] = {"wald": "Dm", "title": "Dm", "cause": "Dm", "falsify": "Bb", "barnum": "Gm", "correct": "F",
                    "invest": "Dm", "end": "Bb"}.get(name, "D")
for h in HITS:
    if h != T.BRAND_T:
        fx.add(h - 2.4, riser(2.4), 0.16)
    big = 1.0 if h in (SEC["title"][0], T.BRAND_T, SEC["wald"][0]) else 0.8
    hit_fx(h, big, HIT_CHORD.get(h, "D") if h != T.BRAND_T else "D")

# ---------------------------------------------------------------- 抽空：重拍前 0.3 秒 / 「恰恰相反」前半小节 / 「相关 ≠ 因果」前
gate = np.ones(N, np.float32)
ramp = int(0.04 * SR)
for (g0, g1) in [(h - 0.30, h) for h in HITS] + [gate_dead, (T.s("c5") - 0.3, T.s("c5"))]:
    i0, i1 = int(g0 * SR), int(g1 * SR)
    gate[i0:i1] = 0.0
    gate[max(0, i0 - ramp):i0] = np.minimum(gate[max(0, i0 - ramp):i0], np.linspace(1, 0, min(ramp, i0)))
    gate[i1:i1 + ramp] = np.minimum(gate[i1:i1 + ramp], np.linspace(0, 1, ramp))
for bus in (pad, bass, drums, arp, keys):
    bus.x *= gate

# ---------------------------------------------------------------- 侧链：每次底鼓让铺底和低音「呼吸」
sc = np.ones(N, np.float32)
tt_ = np.arange(int(0.35 * SR)) / SR
for (t, g) in KICKS:
    i0 = int(t * SR)
    seg = 1 - min(0.55, 0.7 * g) * np.exp(-tt_ / 0.11)
    n_ = min(len(seg), N - i0)
    if n_ > 0:
        sc[i0:i0 + n_] = np.minimum(sc[i0:i0 + n_], seg[:n_])
pad.x *= sc
bass.x *= sc
arp.x *= 0.5 + 0.5 * sc


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


def shelf(x, f0, gain_db, kind):
    """RBJ 搁架滤波器。"""
    A = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * f0 / SR
    al = math.sin(w0) / 2 * math.sqrt(2)
    cw = math.cos(w0)
    if kind == "low":
        b_ = [A * ((A + 1) - (A - 1) * cw + 2 * math.sqrt(A) * al), 2 * A * ((A - 1) - (A + 1) * cw),
              A * ((A + 1) - (A - 1) * cw - 2 * math.sqrt(A) * al)]
        a_ = [(A + 1) + (A - 1) * cw + 2 * math.sqrt(A) * al, -2 * ((A - 1) + (A + 1) * cw),
              (A + 1) + (A - 1) * cw - 2 * math.sqrt(A) * al]
    else:
        b_ = [A * ((A + 1) + (A - 1) * cw + 2 * math.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * cw),
              A * ((A + 1) + (A - 1) * cw - 2 * math.sqrt(A) * al)]
        a_ = [(A + 1) - (A - 1) * cw + 2 * math.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * cw),
              (A + 1) - (A - 1) * cw - 2 * math.sqrt(A) * al]
    return signal.lfilter(np.array(b_) / a_[0], np.array(a_) / a_[0], x)


music = (verb(pad.x, 0.9) + bass.x * 1.0 + verb(drums.x, 0.12) * 1.0 + verb(arp.x, 0.55) + verb(keys.x, 0.5) +
         verb(fx.x, 0.35))
music = highpass(music, 35, 2)
# 频谱倾斜：压低超低频、提亮高频，让手机扬声器也能听清
music = shelf(music, 110, -5, "low")
music = shelf(music, 2500, 4, "high")
mix = music / (np.abs(music).max() + 1e-9)
# 开头 / 结尾
fo = int(1.6 * SR)
mix[:, -int(0.5 * SR) - fo:-int(0.5 * SR)] *= np.linspace(1, 0, fo) ** 1.5
mix[:, -int(0.5 * SR):] = 0

try:
    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    lufs = meter.integrated_loudness(mix.T)
    mix *= 10 ** ((-14 - lufs) / 20)
    print("loudness", round(lufs, 1), "→ -14 LUFS")
except Exception as ex:   # noqa: BLE001
    print("pyloudnorm unavailable:", ex)
    mix *= 0.5 / np.sqrt((mix ** 2).mean())
# 真峰值限幅：先去掉 16 kHz 以上的毛刺，再在 4 倍过采样上做带释放的增益压缩，保证真峰值 ≤ −1 dBTP
from scipy.ndimage import maximum_filter1d  # noqa: E402


def tp_limit(x, peak_db=-2.5):
    up = signal.resample_poly(lowpass(x, 16000, 4), 4, 1, axis=1)
    peak = 10 ** (peak_db / 20)
    need = np.maximum(np.abs(up).max(0) / peak, 1.0)
    win_ = int(0.004 * SR * 4)
    need = maximum_filter1d(need, size=2 * win_ + 1)                 # 前后 4 ms 内取最大：预读 + 保持
    g = 1 / need
    rel = math.exp(-1 / (0.08 * SR * 4))                             # 80 ms 释放
    g = np.minimum(g, signal.lfilter([1 - rel], [1, -rel], g - 1) + 1)
    return np.clip(signal.resample_poly(up * g[None, :], 1, 4, axis=1), -peak, peak)


try:
    gain_db = 0.0
    TARGET = -15.0                        # 留出重拍的动态；AAC 编码后真峰值仍 < −0.5 dBTP
    for _ in range(4):                    # 限幅会吃掉一点响度：补偿后再限，迭代到目标响度
        out = tp_limit(mix * 10 ** (gain_db / 20))
        l2 = meter.integrated_loudness(out.T)
        if abs(l2 - TARGET) < 0.2:
            break
        gain_db += TARGET - l2
    mix = out
    print("after limiter", round(l2, 2), "LUFS")
except NameError:
    mix = tp_limit(mix)
sf.write(os.path.join(WORK, "score.wav"), mix.T.astype(np.float32), SR, subtype="PCM_24")
print("written", os.path.join(WORK, "score.wav"), round(N / SR, 2), "s")
