"""《科学思维》原创卡点配乐（v5）：D 小调，112.9 BPM，与画面共用 timeline 的节拍网格。

- 乐器：FluidR3_GM 音色库（MIT 许可，fluidsynth 离线渲染）的弦乐、铜管、合唱、钢琴、钢片琴、拨弦、定音鼓、合成贝斯等；
  鼓组、冲击、反向镲、上升音效全部在 numpy 里原创合成。
- 每一个音都写在网格上（拍 / 八分 / 十六分）；章节重拍前 0.27 s 整体抽空，重拍上冲击；段落重音上加一记「咚」。
- 声音跟着画面走：斯金纳箱里食物落地 = 钢片琴叮；「市场」箱子掉下的红 K 线 = 高音拨弦、绿 K 线 = 低音；
  硬币每淘汰一天 = 一声逐级升高的钟琴；光速测量值越接近真值，钟琴的音高就越接近准确的 D；四道门 = 四记上行铜管。
- 输出 work/score.wav（48 kHz 立体声）与 work/pulse.npy（每帧的底鼓脉冲，直接由鼓的落点算出）。

用法：python3 src/music.py work/
"""
import math
import os
import sys

import numpy as np
import soundfile as sf
from scipy import signal
from scipy.ndimage import maximum_filter1d

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as T  # noqa: E402

WORK = sys.argv[1] if len(sys.argv) > 1 else T.WORK
SF2 = os.environ.get("SF2", "/usr/share/sounds/sf2/FluidR3_GM.sf2")
SR = 48000
B = T.BEAT
N = int((T.DUR + 1.0) * SR)
rng = np.random.default_rng(2026)


def tg(g):
    """全局拍号 → 秒（第 0 拍 = 第 0 小节第一拍）。"""
    return T.ORIGIN + g * B


def gt(t):
    return (t - T.ORIGIN) / B


SECBAR = {k: int(round(gt(a) / 4)) for k, (a, _) in T.SEC.items()}
SECBAR["hook"] = 0


def G(sec, bar, beat=0.0):
    return (SECBAR[sec] + bar) * 4 + beat


# ================================================================ 音高与和弦
NAMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def m(s):
    """'D4' → 62；'Bb3'、'C#5' 亦可。"""
    pc = NAMES[s[0]]
    i = 1
    while s[i] in "#b":
        pc += 1 if s[i] == "#" else -1
        i += 1
    return 12 * (int(s[i:]) + 1) + pc


PC = {"Dm": (2, 5, 9), "Bb": (10, 2, 5), "F": (5, 9, 0), "C": (0, 4, 7), "Gm": (7, 10, 2), "A": (9, 1, 4),
      "Asus": (9, 2, 4), "Dmaj": (2, 6, 9), "Am": (9, 0, 4)}
ROOT = {"Dm": 2, "Bb": 10, "F": 5, "C": 0, "Gm": 7, "A": 9, "Asus": 9, "Dmaj": 2, "Am": 9}


def tones(ch, lo, hi):
    return [k for k in range(lo, hi + 1) if k % 12 in PC[ch]]


def bass_of(ch, lo=33):
    r = ROOT[ch]
    k = lo + ((r - lo) % 12)
    return k


# 每一章的和弦（每小节一个）
PLAN = {
    "hook": ["Dm", "Dm", "Bb", "Bb", "Gm", "Gm", "A", "A"],
    "eight": ["Dm", "Bb", "F", "C", "Bb", "A"] + ["Dm", "Dm", "Bb", "A"] * 2 + ["Dm", "Dm", "Bb"] +
             ["Dm", "Bb", "Gm", "A", "Dm", "Bb", "A"],
    "title": ["Dm", "A"],
    "cause": ["Dm", "Bb", "F", "C"] * 2 + ["Dm", "Bb", "Gm", "A"] + ["Dm", "Bb", "F", "C"] + ["Gm", "A"],
    "falsify": ["Dm", "C", "Bb", "A", "Dm", "A"] + ["Bb", "C", "Dm", "Bb", "Gm", "A"] + ["Dm", "Bb", "F", "C"],
    "barnum": ["Dm", "Bb", "Gm", "A"] * 3,
    "correct": ["F", "C", "Dm", "Bb"] * 2 + ["Bb", "F", "Gm", "A"],
    "invest": ["Dm", "Bb", "F", "C"] * 2 + ["Bb", "F", "C", "Dm", "Bb", "A"] + ["Dm", "Bb", "F", "C", "Gm", "A"] +
              ["Dm", "Bb", "F", "A"],
    "end": ["Bb", "F", "C", "Dm", "Bb", "F", "C", "Gm", "A", "Bb", "C", "A"],
    "outro": ["Bb", "Bb", "Gm", "A", "Dmaj", "Dmaj", "Dmaj"],
}
CHORDS = []                                  # (起始拍, 和弦)
for sec, chs in PLAN.items():
    for i, ch in enumerate(chs):
        CHORDS.append((G(sec, i), ch))
CHORDS.sort()


def chord_at(g):
    cur = CHORDS[0][1]
    for g0, ch in CHORDS:
        if g0 <= g + 1e-6:
            cur = ch
        else:
            break
    return cur


# ================================================================ 音符事件（fluidsynth）
STEMS = {
    "orch": {"strings": 48, "slow": 49, "cello": 42, "cbass": 43, "pizz": 45, "harp": 46, "trem": 44},
    "brass": {"brass": 61, "horn": 60, "trom": 57, "choir": 52, "timp": 47},
    "keys": {"piano": 0, "celesta": 8, "glock": 9, "mbox": 10, "vibes": 11},
    "synth": {"sbass": 38, "wpad": 89, "poly": 90, "sweep": 95, "saw": 81},
}
INST = {}
for st, d in STEMS.items():
    for i, (name, prog) in enumerate(d.items()):
        INST[name] = (st, i if i < 9 else i + 1, prog)
EV = []                                       # (stem, ch, key, t_on, t_off, vel)


def note(inst, key, g, dur, vel=90):
    st, ch, _ = INST[inst]
    vel = int(max(1, min(127, vel + rng.integers(-4, 5))))
    t0 = tg(g)
    EV.append((st, ch, int(key), t0, t0 + dur * B, vel))


def chord(inst, ch, g, dur, vel=80, lo=50, hi=72):
    for k in tones(ch, lo, hi):
        note(inst, k, g, dur, vel)


def pad(inst, sec, b0, b1, vel=70, lo=50, hi=70, per=1):
    for b in range(b0, b1, per):
        ch = PLAN[sec][b]
        chord(inst, ch, G(sec, b), 4 * per, vel, lo, hi)


def bassline(inst, sec, b0, b1, pattern, vel=95, dur=0.45, octave_lo=33):
    for b in range(b0, b1):
        ch = PLAN[sec][b]
        k = bass_of(ch, octave_lo)
        for p in pattern:
            note(inst, k, G(sec, b, p), dur, vel + (6 if p % 1 == 0.5 else 0))


def ostinato(inst, sec, b0, b1, step=0.5, vel=70, lo=50, hi=69, dur=None, shape=(0, 2, 1, 2)):
    for b in range(b0, b1):
        ch = PLAN[sec][b]
        ts = tones(ch, lo, hi)
        for j in range(int(4 / step)):
            k = ts[shape[j % len(shape)] % len(ts)]
            note(inst, k, G(sec, b, j * step), dur or step * 0.9, vel + (8 if j % 2 == 0 else 0))


def arp(inst, sec, b0, b1, step=0.25, vel=60, lo=62, hi=86, up=True):
    for b in range(b0, b1):
        ch = PLAN[sec][b]
        ts = tones(ch, lo, hi)
        seq = ts + ts[-2:0:-1]
        for j in range(int(4 / step)):
            note(inst, seq[j % len(seq)], G(sec, b, j * step), step * 1.6, vel - (0 if j % 4 == 0 else 10))


# 主题动机：「8」的旋律（4 小节一句；P1 = Dm Bb F C）
THEME_A = [[(0, "A4", 1), (1, "D5", 1), (2, "E5", 1), (3, "F5", 1)], [(0, "F5", 2), (2, "E5", 1), (3, "D5", 1)],
           [(0, "C5", 1), (1, "D5", 1), (2, "E5", 1), (3, "F5", 1)], [(0, "G5", 2), (2, "E5", 2)]]
THEME_B = [[(0, "A5", 2), (2, "F5", 1), (3, "D5", 1)], [(0, "D5", 2), (2, "F5", 1), (3, "E5", 1)],
           [(0, "C5", 3), (3, "A4", 1)], [(0, "E5", 4)]]
THEME_P2 = [THEME_A[0], THEME_A[1], [(0, "Bb4", 1), (1, "D5", 1), (2, "G5", 2)], [(0, "E5", 2), (2, "C#5", 2)]]


def theme(inst, sec, b0, phrase, vel=96, oct_=0, legato=0.95, bars=None):
    for i, bar in enumerate(phrase[:bars] if bars else phrase):
        for (beat, nm, d) in bar:
            note(inst, m(nm) + 12 * oct_, G(sec, b0 + i, beat), d * legato, vel)


# ================================================================ 合成：鼓与音效（numpy，原创）
def lowpass(x, fc, order=2):
    b, a = signal.butter(order, min(fc, SR / 2 * 0.95) / (SR / 2), "low")
    return signal.lfilter(b, a, x)


def highpass(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), "high")
    return signal.lfilter(b, a, x)


def bandpass(x, f0, f1, order=2):
    b, a = signal.butter(order, [f0 / (SR / 2), min(f1, SR / 2 * 0.95) / (SR / 2)], "band")
    return signal.lfilter(b, a, x)


def _t(d):
    return np.arange(int(d * SR)) / SR


def kick(f0=130, f1=44, dec=0.42, click=0.35):
    t = _t(0.8)
    f = f1 + (f0 - f1) * np.exp(-t / 0.045)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / dec)
    cl = highpass(rng.normal(0, 1, len(t)), 2500) * np.exp(-t / 0.004) * click
    return np.tanh(1.6 * (body + cl)) * 0.9


def snare():
    t = _t(0.5)
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.07) * 0.6
    nz = bandpass(rng.normal(0, 1, len(t)), 1500, 9000) * np.exp(-t / 0.13)
    return (tone + nz) * 0.7


def clap():
    t = _t(0.6)
    nz = bandpass(rng.normal(0, 1, len(t)), 900, 5200)
    env = np.zeros(len(t))
    for d in (0.0, 0.011, 0.023):
        env += (t >= d) * np.exp(-np.clip(t - d, 0, None) / 0.008)
    env += (t >= 0.03) * np.exp(-np.clip(t - 0.03, 0, None) / 0.16) * 0.6
    return nz * env * 0.8


def hat(dec=0.045):
    t = _t(max(0.3, dec * 6))
    return highpass(rng.normal(0, 1, len(t)), 7500, 3) * np.exp(-t / dec) * 0.5


def crash(dur=2.4):
    t = _t(dur)
    x = highpass(rng.normal(0, 1, len(t)), 3800, 2) * np.exp(-t / (dur * 0.35))
    return x * 0.55


def tom(f0=160):
    t = _t(0.7)
    f = f0 * (0.6 + 0.4 * np.exp(-t / 0.08))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.25) * 0.8


def tick(f=3200):
    t = _t(0.06)
    return np.sin(2 * np.pi * f * t) * np.exp(-t / 0.008) * 0.5


def subdrop(dur=2.2, f0=85, f1=30):
    t = _t(dur)
    f = f1 + (f0 - f1) * np.exp(-t / 0.4)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (dur * 0.35))


def impact(dur=2.6):
    t = _t(dur)
    body = lowpass(rng.normal(0, 1, len(t)), 180, 4) * np.exp(-t / 0.35) * 2.5
    crk = highpass(rng.normal(0, 1, len(t)), 3000) * np.exp(-t / 0.05) * 0.5
    air = highpass(rng.normal(0, 1, len(t)), 6000) * np.exp(-t / 0.9) * 0.12
    return body + crk + air + subdrop(dur) * 0.9


def thump():
    t = _t(0.6)
    f = 45 + 70 * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.18) + \
        bandpass(rng.normal(0, 1, len(t)), 800, 5000) * np.exp(-t / 0.03) * 0.25


def riser(dur):
    t = _t(dur)
    k = t / dur
    nz = rng.normal(0, 1, len(t))
    out = np.zeros(len(t))
    seg = int(0.05 * SR)
    for i in range(0, len(t), seg):
        fc = 400 + 9000 * k[i] ** 2
        out[i:i + seg] = bandpass(nz[i:i + seg + 0], fc * 0.7, fc * 1.3, 1)[:len(out[i:i + seg])]
    tone = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (3 * k)) / SR) * 0.15
    return (out * 1.5 + tone) * k ** 2.2


def reverse_swell(dur):
    t = _t(dur)
    return highpass(rng.normal(0, 1, len(t)), 3000) * (t / dur) ** 3 * 0.6


def whoosh(dur=0.5):
    t = _t(dur)
    k = t / dur
    x = bandpass(rng.normal(0, 1, len(t)), 500, 6000)
    return x * np.sin(np.pi * k) ** 2 * 0.5


def glass(dur=0.9):
    t = _t(dur)
    x = highpass(rng.normal(0, 1, len(t)), 2500) * np.exp(-t / 0.06)
    for f in (2950, 4170, 5630, 7020):
        x += np.sin(2 * np.pi * f * t + rng.random() * 6) * np.exp(-t / (0.15 + rng.random() * 0.2)) * 0.25
    return x * 0.6


def deflate(dur=0.9, f0=520, f1=110):
    t = _t(dur)
    f = f1 + (f0 - f1) * (1 - t / dur) ** 1.5
    ph = np.cumsum(f) / SR
    x = signal.sawtooth(2 * np.pi * ph) * 0.5 + np.sin(2 * np.pi * ph)
    return lowpass(x, 1800) * np.exp(-t / (dur * 0.6)) * 0.35


class Bus:
    def __init__(self):
        self.x = np.zeros((2, N), np.float32)

    def add(self, t, sig, gain=1.0, pan=0.0):
        i0 = int(round(t * SR))
        if i0 < 0:
            sig = sig[-i0:]
            i0 = 0
        n = min(len(sig), N - i0)
        if n <= 0:
            return
        l, r = math.cos((pan + 1) * math.pi / 4) * 1.414, math.sin((pan + 1) * math.pi / 4) * 1.414
        self.x[0, i0:i0 + n] += (sig[:n] * gain * l).astype(np.float32)
        self.x[1, i0:i0 + n] += (sig[:n] * gain * r).astype(np.float32)


DR = Bus()      # 鼓
FX = Bus()      # 音效
KICKS = []      # 底鼓落点（给画面的脉冲）
K_SIG, SN_SIG, CL_SIG = kick(), snare(), clap()
HAT_SIGS = [hat(0.04), hat(0.05), hat(0.035)]
OH_SIG = hat(0.28)


def K(g, gain=1.0):
    DR.add(tg(g), K_SIG, gain)
    KICKS.append((tg(g), gain))


def groove(sec, b0, b1, kick_on=(0, 1, 2, 3), clap_on=(1, 3), hats=8, hat_g=0.16, kick_g=0.95, clap_g=0.5,
           snare_on=(), ghost=True, open_every=2):
    for b in range(b0, b1):
        for p in kick_on:
            K(G(sec, b, p), kick_g)
        for p in clap_on:
            DR.add(tg(G(sec, b, p)), CL_SIG, clap_g, 0.05)
        for p in snare_on:
            DR.add(tg(G(sec, b, p)), SN_SIG, clap_g, -0.05)
        if hats:
            step = 4 / hats
            for j in range(hats):
                p = j * step
                off = (p % 1) == 0.5
                g_ = hat_g * (1.0 if off else 0.55 if hats == 8 else 0.4 if (p % 1) else 0.7)
                DR.add(tg(G(sec, b, p)), HAT_SIGS[j % 3], g_, 0.25 if j % 2 else -0.2)
        if open_every and b % open_every == open_every - 1:
            DR.add(tg(G(sec, b, 3.5)), OH_SIG, hat_g * 0.9, 0.3)


def roll(g0, g1, gain=0.5, inst=None):
    """军鼓滚奏：十六分 → 三十二分，渐强。"""
    n = int((g1 - g0) * 4)
    for j in range(n):
        k = j / max(1, n - 1)
        for sub in ((0,) if k < 0.6 else (0, 0.125)):
            DR.add(tg(g0 + j * 0.25 + sub), SN_SIG, gain * (0.25 + 0.75 * k ** 1.5), (-0.1, 0.1)[j % 2])


def timp_roll(g0, g1, key=m("D2"), vel=70):
    n = int((g1 - g0) * 4)
    for j in range(n):
        note("timp", key, g0 + j * 0.25, 0.3, int(vel * (0.5 + 0.5 * j / max(1, n - 1))))


def ticks(sec, b0, b1, every=1.0, gain=0.10, f=3200):
    g = G(sec, b0)
    while g < G(sec, b1) - 1e-6:
        FX.add(tg(g), tick(f if (g % 2) < 1 else f * 0.8), gain, 0.3)
        g += every


def stab(g, ch=None, vel=105, brass=True, strings=True, lo=50, hi=74):
    ch = ch or chord_at(g)
    if brass:
        chord("brass", ch, g, 1.2, vel, lo, hi)
        note("trom", bass_of(ch, 38), g, 1.2, vel)
    if strings:
        chord("strings", ch, g, 0.9, vel - 10, lo + 7, hi + 7)
    note("timp", bass_of(ch, 38), g, 1.0, vel)


# ================================================================ 编曲
s, e, at = T.s, T.e, T.at
pt = gt                                       # 时刻 → 拍号

# ---------------- 0 钩子（8 小节）：钟表滴答 + 低音长音，四记重拍，逐步加厚
pad("slow", "hook", 0, 8, 62, 38, 62, per=2)
note("cbass", m("D2"), G("hook", 0), 16, 80)
note("cbass", m("G1") + 12, G("hook", 4), 8, 82)
note("cbass", m("A1") + 12, G("hook", 6), 8, 88)
ticks("hook", 0, 8, 1.0, 0.11)
for i, lid in enumerate(("h1", "h2", "h3", "h4")):
    g = pt(s(lid))
    note("piano", m("D3"), g, 4, 100)
    note("piano", m("D2"), g, 4, 100)
    note("piano", [m("A4"), m("D5"), m("F5"), m("A5")][i], g, 3, 92)
    note("timp", m("D2"), g, 2, 110)
# h1：K 线每个十六分音符长一根 → 钟琴上行音阶
for j in range(24):
    k = [x for x in range(62, 110) if x % 12 in (2, 4, 5, 7, 9, 10, 0)][j]      # D 小调音阶逐级上行
    note("celesta", k, pt(s("h1")) + j * 0.25, 0.4, 60 + j)
FX.add(s("h1") + 6 * B, crash(1.6), 0.25)
note("glock", m("D6"), pt(s("h1")) + 6, 1, 110)
note("glock", m("A6"), pt(s("h1")) + 6, 1, 100)
# h2：三张盈利卡片 → 三声上行钟琴；第 6 拍「全部盈利」
for i, k in enumerate(("F5", "A5", "D6")):
    note("glock", m(k), pt(s("h2")) + 2 * i, 1.5, 105)
    note("vibes", m(k) - 12, pt(s("h2")) + 2 * i, 1.5, 90)
stab(pt(s("h2")) + 6, "Bb", 95, strings=False)
# h3：八块瓦片每半拍一块 → 八分音符上行
for i in range(8):
    note("celesta", tones("Gm", 67, 96)[i], pt(s("h3")) + i * 0.5, 0.6, 70 + 4 * i)
ostinato("cello", "hook", 4, 8, 0.5, 62, 38, 57, shape=(0, 2, 1, 2))
# h4：金色 8 升起，第 4、6 拍裂开
chord("choir", "A", pt(s("h4")), 8, 80, 57, 76)
for k in (4, 6):
    FX.add(s("h4") + k * B, glass(), 0.55)
    note("timp", m("A1") + 12, pt(s("h4")) + k, 1, 120)
roll(G("hook", 7), G("hook", 8) - 0.6, 0.55)

# ---------------- 1 序章：赢钱（0–6 小节）→ 斯金纳的鸽子（6–17）→ 市场（17–23）→ 交学费（23）
groove("eight", 0, 6, hats=16, hat_g=0.15, clap_g=0.45)
bassline("sbass", "eight", 0, 6, (0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5), 92, 0.4)
pad("strings", "eight", 0, 6, 72, 50, 70)
arp("poly", "eight", 0, 6, 0.25, 52, 62, 84)
theme("piano", "eight", 0, THEME_A, 104)
theme("vibes", "eight", 0, THEME_A, 80)
note("brass", m("D4"), G("eight", 0), 2, 100)
FX.add(tg(G("eight", 0)), crash(), 0.35)
for g in (pt(s("s2")), pt(s("s4"))):                      # +30%、金色 8
    stab(g, None, 108)
    FX.add(tg(g), crash(), 0.35)
for lid, key in (("s3", "第二次"), ("s3", "第三次")):
    note("glock", m("A5"), pt(at(lid, key)), 1, 100)
note("glock", m("D6"), pt(at("s3", "第三次")) + 1, 1, 105)
chord("choir", "Bb", pt(s("s4")), 6, 85, 58, 77)
# s1：自选股逐行出现（十六分）、选中（第 2 拍）、买入（第 4 拍）、「吉」字章（第 6 拍）
for j in range(6):
    FX.add(s("s1") + j * B / 4, tick(2600 + 200 * j), 0.12)
note("glock", m("F6"), pt(s("s1")) + 2, 1, 100)
FX.add(s("s1") + 4 * B, tick(1800), 0.35)
FX.add(s("s1") + 6 * B, thump(), 0.35)
# 斯金纳：神秘的拨弦 + 钟表 + 食物落地的叮
s5g, s10g = pt(s("s5")), pt(s("s10"))
pad("wpad", "eight", 6, 17, 60, 50, 69)
for b in range(6, 17):
    ch = PLAN["eight"][b]
    ts = tones(ch, 55, 74)
    for j in range(8 if b >= 10 else 4):
        step = 0.5 if b >= 10 else 1
        note("pizz", ts[(0, 2, 1, 3, 2, 1, 3, 2)[j] % len(ts)], G("eight", b, j * step), 0.5, 78 + (8 if j == 0 else 0))
    note("cbass", bass_of(ch, 33) + 12, G("eight", b), 3.5, 70)
    K(G("eight", b), 0.55)
    if b >= 12:
        K(G("eight", b, 2), 0.4)
ticks("eight", 6, 17, 0.5, 0.06, 4200)
for g in (s5g, s5g + 2, s5g + 4):                                 # 1948 · 斯金纳 · 实验
    note("timp", m("D2"), g, 1, 90)
    FX.add(tg(g), thump(), 0.25)


def lands(t0, t1, every=4):
    k0 = math.ceil((t0 - T.ORIGIN) / (every * B) - 1e-6)
    out = []
    while T.ORIGIN + k0 * every * B < t1:
        out.append(T.ORIGIN + k0 * every * B)
        k0 += 1
    return out


PELLETS = (lands(s("s6") + 0.4, s("s7")) + lands(s("s7"), s("s8")) + lands(s("s8"), s("s9"), 2) +
           lands(s("s9"), s("s10")))
for i, L in enumerate(PELLETS):
    ch = chord_at(pt(L))
    k = tones(ch, 79, 93)[i % 3]
    note("celesta", k, pt(L), 1.5, 112)
    note("glock", k + 12, pt(L), 0.5, 70)
for i, key in enumerate(("逆时针", "把头伸向", "像钟摆")):        # 三种仪式
    note("horn", [m("D4"), m("F4"), m("A4")][i], pt(max(s("s8"), at("s8", key))), 2, 88)
note("trom", m("A2"), pt(s("s9")) + 5, 2, 95)                     # 划掉「它以为的因果」
FX.add(tg(pt(s("s9")) + 5), thump(), 0.3)
# 市场：半时值的驱动 + 掉下来的 K 线（红 = 高音，绿 = 低音）
groove("eight", 17, 23, kick_on=(0, 2), clap_on=(), snare_on=(1, 3), hats=8, hat_g=0.13, kick_g=0.9, clap_g=0.35)
bassline("sbass", "eight", 17, 23, (0, 0.75, 1.5, 2, 2.75, 3.5), 92, 0.45)
ostinato("cello", "eight", 17, 23, 0.25, 70, 38, 57, shape=(0, 1, 2, 1))
pad("strings", "eight", 17, 23, 66, 50, 70)
S10_FALL = np.random.default_rng(10).random((24, 3))
for j in range(16):
    L = s("s10") + (j + 1) * B / 2
    if L >= s("s11"):
        break
    red = S10_FALL[j][0] > 0.48
    ch = chord_at(pt(L))
    note("pizz", tones(ch, 74, 86)[j % 3] if red else tones(ch, 43, 55)[j % 3], pt(L), 0.5, 100)
theme("horn", "eight", 19, THEME_P2, 86, oct_=-1, bars=4)                 # 研究：主题在圆号上变暗
# 交学费：重音 + 下滑
FX.add(s("s13") + B, deflate(1.2, 400, 70), 0.6)
for j, g in enumerate((pt(s("s13")) + 2, pt(s("s13")) + 2.5, pt(s("s13")) + 3)):
    note("trom", [m("A2"), m("G2"), m("F2")][j], g, 0.45, 100)

# ---------------- 标题：全奏和弦
tt = G("title", 0)
chord("brass", "Dm", tt, 4, 118, 50, 74)
chord("choir", "Dm", tt, 6, 100, 57, 77)
chord("strings", "Dm", tt, 6, 105, 50, 81)
note("cbass", m("D2"), tt, 6, 115)
note("timp", m("D2"), tt, 2, 127)
theme("horn", "title", 0, [THEME_A[0]], 110)
chord("brass", "A", G("title", 1, 2), 2, 100, 52, 73)
timp_roll(G("title", 1), G("title", 2) - 0.6, m("A1") + 12, 95)
FX.add(tg(tt), crash(3.0), 0.45)

# ---------------- 2 相关 ≠ 因果
bassline("sbass", "cause", 0, 18, (0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5), 88, 0.4)
ostinato("strings", "cause", 0, 8, 0.25, 64, 57, 76, dur=0.22, shape=(0, 2, 1, 2))
g_bull = pt(s("c3"))
groove("cause", 0, 2, kick_on=(0,), clap_on=(), hats=8, hat_g=0.10, kick_g=0.7)
g = G("cause", 2)
while g < g_bull:
    K(g, 0.75)
    g += 1
for b in range(2, 8):
    for p in range(4):
        if G("cause", b, p) >= g_bull:
            K(G("cause", b, p), 0.95)
    for p in (1, 3):
        if G("cause", b, p) >= g_bull:
            DR.add(tg(G("cause", b, p)), CL_SIG, 0.45)
    for j in range(16):
        if G("cause", b, j / 4) >= g_bull:
            DR.add(tg(G("cause", b, j / 4)), HAT_SIGS[j % 3], 0.14 if j % 2 else 0.07, 0.2)
FX.add(s("c3"), crash(), 0.4)
roll(g_bull - 2, g_bull - 0.05, 0.4)
pad("strings", "cause", 2, 8, 70, 50, 74)
theme("brass", "cause", 4, THEME_A, 95, oct_=-1)
# 相关 ≠ 因果：三记
for j, kk in enumerate((m("D2"), m("D2"), m("A2"))):
    g = pt(s("c5")) + j * 0.5
    note("timp", kk, g, 1, 115)
    chord("brass", "Dm" if j < 2 else "A", g, 0.6 if j < 2 else 2, 112, 50, 74)
# 对照组：拨弦 + 轻打
groove("cause", 8, 11, kick_on=(0, 2), clap_on=(), hats=8, hat_g=0.10, kick_g=0.6)
for b in range(8, 11):
    ts = tones(PLAN["cause"][b], 55, 74)
    for j in range(8):
        note("pizz", ts[(0, 2, 1, 3)[j % 4] % len(ts)], G("cause", b, j * 0.5), 0.5, 82)
FX.add(at("c7", "8，什么"), deflate(), 0.55)
# 随机对照实验：定音鼓脉冲逐渐变密，抛硬币
for b in range(11, 18):
    every = 1.0 if b < 13 else 0.5
    g = G("cause", b)
    while g < G("cause", b + 1) - 1e-6:
        note("timp", bass_of(PLAN["cause"][b], 38), g, 0.5, 80 + (b - 11) * 5)
        g += every
groove("cause", 13, 18, hats=16, hat_g=0.12, kick_g=0.85, clap_g=0.4)
ostinato("strings", "cause", 11, 18, 0.25, 66, 57, 76, dur=0.22, shape=(0, 2, 1, 2))
pad("slow", "cause", 11, 18, 62, 50, 70)
note("glock", m("D7"), pt(s("c9")), 1, 110)
note("glock", m("A6"), pt(s("c9")) + 0.5, 1, 100)
stab(pt(s("c10")) + 2, "Dm", 112)
theme("horn", "cause", 12, THEME_B, 92, oct_=-1)
FX.add(tg(G("cause", 16)), riser(2 * T.BAR - 0.3), 0.35)

# ---------------- 3 可证伪：亏钱 → 借口 → 「科学恰恰相反」→ 日食 → 偏了！
for b in range(0, 6):                                             # 下行的哀歌低音 + 心跳
    ch = PLAN["falsify"][b]
    note("cbass", bass_of(ch, 33) + 12, G("falsify", b), 4, 92)
    chord("piano", ch, G("falsify", b), 4, 70, 50, 65)
    K(G("falsify", b), 0.7)
    K(G("falsify", b, 0.5), 0.45)
    K(G("falsify", b, 2), 0.6)
pad("slow", "falsify", 0, 6, 60, 50, 70)
for g, keys in ((pt(s("f1")), ("D3", "C3", "Bb2", "A2")), (pt(s("f2")), ("F3", "E3")),
                (pt(s("f3")) + 0.5, ("Eb3", "D3"))):                # 亏损的下行 + 两次「借口」的弱音长号
    for j, kk in enumerate(keys):
        note("trom", m(kk), g + j * 0.5, 0.6, 96)
for j in range(4):                                                  # 「涨也灵、跌也灵」的机器
    note("glock", m("D6") if j % 2 == 0 else m("A5"), pt(s("f4")) + j + 0.9, 0.5, 90)
stab(pt(s("f4")) + 4, "Bb", 105)
stab(pt(s("f4")) + 6, "A", 110)
# 科学恰恰相反：明亮、上升
g5 = pt(s("f5"))
for b in range(6, 12):
    ch = PLAN["falsify"][b]
    for j in range(16):
        note("trem", tones(ch, 62, 81)[j % 3], G("falsify", b, j / 4), 0.24, 58 + (b - 6) * 7)
    note("cbass", bass_of(ch, 33) + 12, G("falsify", b), 4, 85)
note("glock", m("A5"), g5, 1, 100)
note("glock", m("D6"), g5 + 1, 1, 100)
stab(pt(at("f5", "怎样就算")) + 2, "Dm", 108)                       # 盖章：可证伪
chord("choir", "Dm", pt(s("f6")), 10, 80, 62, 81)
chord("choir", "Gm", G("falsify", 10), 4, 88, 62, 81)
chord("choir", "A", G("falsify", 11), 4, 96, 61, 81)
for b in range(9, 12):
    g = G("falsify", b)
    while g < G("falsify", b + 1) - 1e-6:
        note("timp", m("A1") + 12, g, 0.4, 80 + (b - 9) * 12)
        g += 0.5 if b < 11 else 0.25
groove("falsify", 7, 12, kick_on=(0, 2), clap_on=(), hats=8, hat_g=0.09, kick_g=0.7)
note("glock", m("E6"), pt(at("f6", "1.75")), 1, 110)               # 预言 1.75″
note("glock", m("E5"), pt(at("f6", "是牛顿")), 1, 90)               # 牛顿 0.87″（低八度）
FX.add(tg(G("falsify", 11)), riser(T.BAR - 0.05), 0.45)
# 偏了！全奏释放
g8 = pt(s("f8"))
groove("falsify", 12, 16, hats=16, hat_g=0.15, clap_g=0.5)
bassline("sbass", "falsify", 12, 16, (0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5), 95, 0.4)
pad("strings", "falsify", 12, 16, 85, 50, 79)
chord("choir", "Dm", g8, 4, 105, 62, 81)
theme("brass", "falsify", 12, THEME_A, 112)
arp("celesta", "falsify", 12, 16, 0.25, 55, 74, 93)
FX.add(tg(g8), crash(3.0), 0.5)
FX.add(tg(g8), impact(), 0.25)
FX.add(tg(pt(s("f9")) + 2), thump(), 0.35)                          # 先画靶，再开枪：一箭
for i in range(4):                                                  # 先开枪：四箭
    FX.add(tg(pt(at("f9", "迷信")) + i / 4), tick(900), 0.5)
roll(G("falsify", 15, 2), G("falsify", 16) - 0.6, 0.5)

# ---------------- 4 我们为什么会信：八音盒 → 记忆 → 四道门
pad("wpad", "barnum", 0, 12, 58, 50, 69)
theme("mbox", "barnum", 0, THEME_P2, 92, oct_=1)
for b in range(0, 6):
    K(G("barnum", b), 0.5)
    note("cbass", bass_of(PLAN["barnum"][b], 33) + 12, G("barnum", b), 4, 80)
MEM = [10.0, -21.5, 8.2, -12.9, 10.0, -16.3, 6.1, -9.8, 10.0, -14.0]
for j, pct in enumerate(MEM):                                      # 涨停卡片飞进记忆（高音），套牢化成灰（低、闷）
    g = pt(s("m2")) + j * 0.5
    ch = chord_at(g)
    if pct > 0:
        note("celesta", tones(ch, 79, 93)[j % 3], g, 1.0, 105)
    else:
        note("pizz", tones(ch, 40, 52)[j % 3], g, 0.4, 70)
roll(pt(s("m4")) + 4, pt(s("m5")) - 0.05, 0.4)
pad("strings", "barnum", 4, 12, 72, 50, 74)
for i, lid in enumerate(("m5", "m6", "m7", "m8")):                  # 四道门：上行的铜管
    g = pt(s(lid))
    root = [m("D3"), m("F3"), m("A3"), m("D4")][i]
    for kk in (root, root + 7, root + 12):
        note("brass", kk, g, 1.5, 112)
    note("timp", [m("D2"), m("F2"), m("A2"), m("D3")][i], g, 1, 120)
    FX.add(tg(g), crash(1.4), 0.25)
    K(g, 1.0)
g_run = pt(e("m8"))
groove("barnum", int(round((g_run - G("barnum", 0)) / 4)), 12, hats=16, hat_g=0.13, kick_g=0.85, clap_g=0.42)
bassline("sbass", "barnum", int(round((g_run - G("barnum", 0)) / 4)), 12, (0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5), 90)
for j in range(4):
    FX.add(tg(g_run + j * 0.5), whoosh(0.45), 0.4, (-0.5, 0.5)[j % 2])
    FX.add(tg(g_run + j * 0.5 + 3), thump(), 0.25)
FX.add(tg(G("barnum", 11)), riser(T.BAR - 0.3), 0.4)

# ---------------- 5 纠错的机器：光速测量收敛到准确的 D → 共识被打碎 → 诺贝尔 → 费曼
LIGHT = [220000, 301000, 315000, 298000, 299910, 299796, 299792.5, 299792.4562, 299792.458]
for i, v in enumerate(LIGHT):
    d = v - 299792.458
    off = int(round(math.copysign(math.log10(1 + abs(d)) / 5.0, d) * 6))   # 偏差越大，音越不准
    g = pt(s("k1")) + (i + 1) * 0.75
    note("glock", m("D6") + off, g, 1.2, 100)
    note("vibes", m("D5") + off, g, 1.2, 80)
note("choir", m("D5"), pt(s("k1")) + 9 * 0.75, 4, 90)
pad("slow", "correct", 0, 2, 66, 50, 72)
pad("strings", "correct", 2, 9, 70, 53, 74)
arp("piano", "correct", 2, 9, 0.5, 70, 53, 77)
groove("correct", 2, 9, kick_on=(0, 2), clap_on=(1, 3), hats=8, hat_g=0.10, kick_g=0.75, clap_g=0.3)
bassline("cbass", "correct", 2, 9, (0, 2), 88, 1.8)
stab(pt(s("k2")), "Dm", 100)                                        # 共识盖章
for j in range(3):                                                  # 一杯细菌：咕嘟
    note("vibes", m("A4") - 3 * j, pt(at("k3", "喝下了")) + j, 1, 80)
FX.add(s("k4"), glass(1.2), 0.7)                                    # 共识碎裂
stab(pt(s("k4")), "Bb", 115)
g_nobel = pt(at("k4", "2005"))
for j, kk in enumerate(("D4", "F4", "A4", "D5")):                   # 诺贝尔奖：号角
    note("brass", m(kk), g_nobel + j * 0.5, 2.5 - j * 0.5, 115)
    note("horn", m(kk) - 12, g_nobel + j * 0.5, 2.5 - j * 0.5, 100)
note("glock", m("D7"), g_nobel + 1.5, 2, 110)
FX.add(tg(g_nobel), crash(2.6), 0.35)
for b in range(9, 12):                                              # 费曼：钢琴独白
    ch = PLAN["correct"][b]
    chord("piano", ch, G("correct", b), 4, 72, 50, 67)
    note("piano", bass_of(ch, 33), G("correct", b), 4, 80)
    chord("slow", ch, G("correct", b), 4, 62, 55, 74)
theme("piano", "correct", 9, [THEME_B[0], THEME_B[1], [(0, "Bb4", 2), (2, "D5", 2)]], 92)
note("piano", m("A4"), pt(at("k5", "而你自己")), 3, 100)

# ---------------- 6 回到股市：第二次高潮
gi = G("invest", 0)
groove("invest", 0, 8, hats=16, hat_g=0.15, clap_g=0.5)
bassline("sbass", "invest", 0, 8, (0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5), 98, 0.4)
pad("strings", "invest", 0, 8, 80, 50, 79)
ostinato("cello", "invest", 0, 8, 0.25, 72, 38, 57, shape=(0, 1, 2, 1))
theme("horn", "invest", 4, THEME_B, 100)
chord("brass", "Dm", gi, 2, 120, 50, 74)
FX.add(tg(gi), crash(3.0), 0.45)
for k in range(21):                                                 # 抛硬币：每淘汰一天一声，逐级升高
    g = pt(T.COIN_T0 + k * T.COIN_STEP)
    sc = tones("Dm", 62, 100) + [101, 105, 108]
    note("glock", sc[min(k, len(sc) - 1)], g, 0.5, 80 + k)
stab(pt(T.COIN_T0 + 20 * T.COIN_STEP), "Dm", 118)
for j in range(3):                                                  # 三连胜：三枚硬币
    note("glock", [m("A5"), m("D6"), m("F6")][j], pt(s("i3")) + j * 0.5, 1, 110)
stab(pt(s("i3")) + 2, "Bb", 105)
stab(pt(s("i3")) + 2.5, "F", 115)
# 村庄与达尔文：放慢
pad("slow", "invest", 8, 14, 70, 50, 74)
for b in range(8, 14):
    ch = PLAN["invest"][b]
    note("cbass", bass_of(ch, 33) + 12, G("invest", b), 4, 85)
    K(G("invest", b), 0.7)
    K(G("invest", b, 2), 0.55)
    DR.add(tg(G("invest", b, 3)), SN_SIG, 0.25)
arp("piano", "invest", 8, 14, 0.5, 66, 57, 79)
chord("choir", "C", pt(at("i4", "同一个")), 4, 85, 60, 79)
for i in range(4):                                                  # 达尔文的笔记：一条一声
    note("celesta", m("A5") + [0, 3, 5, 7][i], pt(s("i5")) + 2 + i, 1, 95)
roll(pt(s("i6")), G("invest", 15, 1) - 0.05, 0.45)
timp_roll(pt(s("i6")) + 2, G("invest", 15, 1) - 0.05, m("A1") + 12, 95)
# 五步法：每步一记，逐级上行
for i in range(5):
    g = pt(s(f"i{7 + i}"))
    ch = chord_at(g)
    root = [m("D3"), m("E3"), m("F3"), m("G3"), m("A3")][i]
    for kk in (root, root + 12):
        note("brass", kk, g, 1.5, 110)
    note("timp", root - 12, g, 1, 118)
    FX.add(tg(g), crash(1.2), 0.2)
groove("invest", 15, 24, hats=16, hat_g=0.15, clap_g=0.5)
bassline("sbass", "invest", 15, 24, (0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5), 98, 0.4)
pad("strings", "invest", 15, 24, 82, 50, 79)
arp("celesta", "invest", 20, 24, 0.25, 55, 74, 93)
theme("brass", "invest", 20, THEME_A, 114)                          # 喜诗糖果：主题在铜管上凯旋
theme("strings", "invest", 20, THEME_A, 96, oct_=1)
for i in range(3):
    note("glock", [m("D6"), m("F6"), m("A6")][i], pt(s("i12")) + 2 + i, 1, 105)
stab(pt(at("i12", "定价权")), None, 112)
FX.add(tg(G("invest", 23)), riser(T.BAR - 0.3), 0.4)

# ---------------- 7 终章：情绪 → 「我的 8，是什么？」→ 终句
pad("strings", "end", 0, 6, 74, 50, 76)
chord("choir", "Bb", G("end", 0), 8, 75, 58, 77)
theme("piano", "end", 0, THEME_B, 96)
for b in range(0, 6):
    ch = PLAN["end"][b]
    note("cbass", bass_of(ch, 33) + 12, G("end", b), 4, 88)
    K(G("end", b), 0.6)
    K(G("end", b, 2), 0.45)
for key in ("错得更少", "改得更快"):
    stab(pt(at("e2", key)), None, 108, strings=True)
g3 = pt(s("e3"))
g = g3
while g < pt(s("e4")) - 1e-6:                                       # 下单之前：心跳
    K(g, 0.55)
    K(g + 0.25, 0.35)
    g += 1
note("piano", m("D3"), g3, 4, 80)
g4 = pt(s("e4"))
note("piano", m("D2"), g4, 8, 110)
note("piano", m("A5"), g4, 4, 96)
note("timp", m("D2"), g4, 2, 120)
chord("slow", "Gm", g4, 4, 60, 55, 74)
g4q = g4 + 4                                                        # 8 翻过去，背面是问号
note("celesta", m("A6"), g4q, 2, 115)
note("glock", m("E6"), g4q, 2, 100)
chord("choir", "A", g4q, 4, 90, 61, 81)
chord("slow", "A", g4q, 4, 70, 55, 76)
g5_ = pt(s("e5"))
for b, ch in ((9, "Bb"), (10, "C"), (11, "A")):
    chord("strings", ch, G("end", b), 4, 70 + (b - 9) * 12, 50, 81)
    chord("choir", ch, G("end", b), 4, 70 + (b - 9) * 12, 58, 79)
    note("cbass", bass_of(ch, 33) + 12, G("end", b), 4, 90)
note("piano", m("F5"), g5_, 2, 96)
timp_roll(G("end", 11), G("end", 12) - 0.05, m("A1") + 12, 100)

# ---------------- 片尾：粒子汇聚 → logo → 「巴芒价值」落在 D 大调上
go = G("outro", 0)
chord("slow", "Bb", go, 8, 80, 50, 81)
arp("harp", "outro", 0, 2, 0.25, 70, 62, 93)
chord("strings", "Gm", G("outro", 2), 4, 82, 55, 81)
chord("strings", "A", G("outro", 3), 4, 92, 57, 81)
note("celesta", m("D7"), pt(T.LOGO_SHOW), 2, 110)
note("glock", m("A6"), pt(T.LOGO_SHOW), 2, 100)
note("cbass", m("A1") + 12, G("outro", 2), 8, 92)
timp_roll(G("outro", 3), G("outro", 4) - 0.05, m("A1") + 12, 105)
gb = pt(T.BRAND_T)
chord("brass", "Dmaj", gb, 8, 120, 50, 74)
chord("strings", "Dmaj", gb, 10, 108, 50, 86)
chord("choir", "Dmaj", gb, 10, 105, 57, 81)
note("cbass", m("D2"), gb, 10, 115)
note("timp", m("D2"), gb, 2, 127)
note("glock", m("F#6"), gb, 3, 110)
note("celesta", m("D7"), gb, 3, 110)
FX.add(T.BRAND_T, crash(4.0), 0.5)
FX.add(tg(G("outro", 2)), riser(2 * T.BAR - 0.05), 0.35)

# ---------------- 章节重拍与段落重音
HITS = T.HITS
for h in HITS:
    big = h in (T.SEC["eight"][0], T.SEC["title"][0], T.SEC["invest"][0], T.BRAND_T)
    FX.add(h, impact(), 0.32 if big else 0.22)
    K(gt(h), 1.0)
for h in HITS[:-1]:
    FX.add(h - 2 * B, reverse_swell(2 * B - 0.27), 0.22)
for a in T.ACCENTS:
    if all(abs(a - h) > 0.2 for h in HITS):
        FX.add(a, thump(), 0.12)


# ================================================================ 渲染
def render_stem(stem):
    import fluidsynth
    fs = fluidsynth.Synth(samplerate=float(SR), gain=0.35)
    sfid = fs.sfload(SF2)
    for name, prog in STEMS[stem].items():
        _, ch, _ = INST[name]
        fs.program_select(ch, sfid, 0, prog)
    rv = {"orch": (0.85, 0.35, 0.9, 0.55), "brass": (0.85, 0.35, 0.9, 0.5), "keys": (0.7, 0.4, 0.9, 0.45),
          "synth": (0.5, 0.5, 0.8, 0.25)}[stem]
    fs.set_reverb(*rv)
    fs.set_chorus(3, 1.2, 0.3, 8.0, 0)
    evs = []
    for (st, ch, key, t0, t1, vel) in EV:
        if st == stem:
            evs.append((int(round(t0 * SR)), 1, ch, key, vel))
            evs.append((int(round(t1 * SR)), 0, ch, key, 0))
    evs.sort(key=lambda x: (x[0], x[1]))
    out = np.zeros((N, 2), np.float32)
    pos = 0
    for (i, on, ch, key, vel) in evs:
        i = min(max(i, 0), N)
        if i > pos:
            out[pos:i] = np.frombuffer(fs.get_samples(i - pos), np.int16).reshape(-1, 2) / 32768.0
            pos = i
        if on:
            fs.noteon(ch, key, vel)
        else:
            fs.noteoff(ch, key)
    if pos < N:
        out[pos:] = np.frombuffer(fs.get_samples(N - pos), np.int16).reshape(-1, 2) / 32768.0
    fs.delete()
    return out.T


def reverb_ir(sec=2.4, seed=1):
    r = np.random.default_rng(seed)
    t = _t(sec)
    ir = r.normal(0, 1, (2, len(t))) * np.exp(-t / (sec * 0.25))
    ir = np.stack([lowpass(ir[0], 6000), lowpass(ir[1], 6000)])
    return ir / np.sqrt((ir ** 2).sum(1, keepdims=True))


def verb(x, wet, sec=2.2):
    ir = reverb_ir(sec)
    y = np.stack([signal.fftconvolve(x[c], ir[c])[:x.shape[1]] for c in range(2)])
    return x + wet * y


stems = {k: render_stem(k) for k in STEMS}
for k, v in stems.items():
    print("stem", k, "rms", round(float(np.sqrt((v ** 2).mean())), 4))
# 侧链：底鼓压缩合成贝斯、弦乐与 pad（现代的“呼吸”感）
duck = np.ones(N, np.float32)
idx = np.arange(int(0.3 * SR))
shape = 1 - 0.5 * np.exp(-idx / SR / 0.09)
for (tk, gk) in KICKS:
    i0 = int(tk * SR)
    n = min(len(shape), N - i0)
    if n > 0 and gk >= 0.7:
        duck[i0:i0 + n] = np.minimum(duck[i0:i0 + n], 1 - (1 - shape[:n]) * min(1.0, gk))
drums = verb(DR.x, 0.10, 1.2)
drums = np.stack([drums[0], drums[1]])
fx = verb(FX.x, 0.18, 2.6)
mix = (stems["orch"] * 1.0 * (0.4 + 0.6 * duck) + stems["brass"] * 0.9 + stems["keys"] * 1.5 +
       stems["synth"] * 0.85 * duck + drums * 0.55 + fx * 0.55)
mix = np.stack([highpass(mix[0], 28, 2), highpass(mix[1], 28, 2)])

# 章节重拍前 0.27 s 抽空（与画面的推入黑场同步）
gate = np.ones(N, np.float32)
ramp = int(0.012 * SR)
for h in HITS[:-1]:
    i0, i1 = int((h - 0.27) * SR), int(h * SR)
    gate[i0:i1] = 0.0
    gate[i0 - ramp:i0] = np.minimum(gate[i0 - ramp:i0], np.linspace(1, 0, ramp))
    gate[i1 - 40:i1] = 0.0
# 抽空期间保留反向镲（它本来就是为重拍蓄力的）
swell = np.zeros((2, N), np.float32)
for h in HITS[:-1]:
    tmp = Bus()
    tmp.add(h - 2 * B, reverse_swell(2 * B - 0.27), 0.22)
    swell += tmp.x
mix = mix * gate[None, :] + swell * (1 - gate[None, :]) * 0.55
fo = int(1.4 * SR)
end_i = int(T.DUR * SR)
mix[:, end_i - fo:end_i] *= np.linspace(1, 0, fo)[None, :] ** 1.5
mix[:, end_i:] = 0


def glue(x, thr_db=-16, ratio=2.0, att=0.01, rel=0.18):
    """总线压缩：让各声部粘在一起。"""
    lvl = np.sqrt(lowpass(x.mean(0) ** 2, 12, 1).clip(1e-12, None))
    db = 20 * np.log10(lvl)
    over = np.maximum(db - thr_db, 0)
    gr = over * (1 - 1 / ratio)
    a_, r_ = math.exp(-1 / (att * SR)), math.exp(-1 / (rel * SR))
    sm = signal.lfilter([1 - r_], [1, -r_], gr)
    return x * (10 ** (-sm / 20))[None, :]


def tp_limit(x, peak_db=-2.0):
    up = signal.resample_poly(lowpass(x, 16000, 4), 4, 1, axis=1)
    peak = 10 ** (peak_db / 20)
    need = np.maximum(np.abs(up).max(0) / peak, 1.0)
    w = int(0.004 * SR * 4)
    need = maximum_filter1d(need, size=2 * w + 1)
    g = 1 / need
    rel = math.exp(-1 / (0.08 * SR * 4))
    g = np.minimum(g, signal.lfilter([1 - rel], [1, -rel], g - 1) + 1)
    return np.clip(signal.resample_poly(up * g[None, :], 1, 4, axis=1), -peak, peak)


mix = glue(mix)
import pyloudnorm as pyln  # noqa: E402

meter = pyln.Meter(SR)
TARGET = -14.5
gain_db = TARGET - meter.integrated_loudness(mix.T)
for _ in range(5):
    res = tp_limit(mix * 10 ** (gain_db / 20))
    l2 = meter.integrated_loudness(res.T)
    if abs(l2 - TARGET) < 0.15:
        break
    gain_db += TARGET - l2
sf.write(os.path.join(WORK, "score.wav"), res.T.astype(np.float32), SR, subtype="PCM_24")
np.save(os.path.join(WORK, "stems_rms.npy"), np.array([0]))

# ================================================================ 画面用的鼓点脉冲：直接由底鼓与重拍落点生成
nf = int(T.DUR * T.FPS) + 2
pulse = np.zeros(nf, np.float32)
for (tk, gk) in KICKS:
    f0 = tk * T.FPS
    for f in range(int(f0), min(nf, int(f0) + 12)):
        if f >= f0 - 0.5:
            v = min(1.0, gk) * math.exp(-max(0.0, f / T.FPS - tk) / 0.16)
            pulse[f] = max(pulse[f], v)
pulse *= gate[np.minimum((np.arange(nf) / T.FPS * SR).astype(int), N - 1)]
np.save(os.path.join(WORK, "pulse.npy"), pulse)
print("notes", len(EV), "kicks", len(KICKS), "loudness", round(l2, 2), "LUFS")
print("written", os.path.join(WORK, "score.wav"))
