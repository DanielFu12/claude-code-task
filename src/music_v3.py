# -*- coding: utf-8 -*-
"""《出厂设置》v3 配乐：按 build/v3_timeline.json 的段落与卡片逐小节编曲，全部由代码合成。
输出 build/v3_music.wav（48kHz 立体声）与 build/v3_beats.json（鼓点/冲击/解锁时刻，供画面卡点）。
转场音效只用低频（低音下潜冲击、低频气流铺垫），不使用高频的“沙沙/刷”声。"""
import json
import os

import numpy as np
import soundfile as sf
from scipy import signal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
SR = 48000
rng = np.random.default_rng(7)

tl = json.load(open(os.path.join(BUILD, "v3_timeline.json")))
BEAT, BAR, TOTAL = tl["beat"], tl["bar"], tl["total"]
N = int((TOTAL + 4) * SR)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


CH = {"Dm": [50, 53, 57], "Bb": [46, 50, 53], "F": [53, 57, 60], "C": [48, 52, 55], "Gm": [43, 46, 50],
      "A": [45, 49, 52], "Am": [45, 48, 52], "Dsus": [50, 52, 57]}
PROG = {"default": ["Dm", "Bb", "F", "C"], "cold": ["Dm", "Dm", "Bb", "Bb"], "quiz": ["Dm", "Dm", "Bb", "A"],
        "warning": ["Gm", "Dm", "Bb", "A"], "return": ["Bb", "C", "Dm", "Dm"], "finale": ["Bb", "C", "F", "A"],
        "refs": ["Dm", "Dm", "Dm", "Dm"], "title": ["Dm", "Bb", "F", "C"]}
CUTOFF = {0: 900, 1: 1500, 2: 2400, 3: 4200}

# ------------------------------------------------------------------ 基础音色
TABLE = 4096
_ph = np.arange(TABLE) / TABLE
SAW = sum(np.sin(2 * np.pi * k * _ph) / k for k in range(1, 24)) * (2 / np.pi)


def osc_table(freq, n, table=SAW, phase=0.0):
    idx = (phase + np.cumsum(np.full(n, freq / SR))) % 1.0 * TABLE
    return np.interp(idx, np.arange(TABLE + 1), np.append(table, table[0]))


def adsr(n, a, r, sustain_len=None):
    t = np.arange(n) / SR
    env = np.minimum(1, t / max(a, 1e-4))
    if r > 0:
        tail = np.clip((n / SR - t) / r, 0, 1)
        env = env * tail
    return env


def add(buf, start_s, sig, gain=1.0):
    a = int(start_s * SR)
    if a < 0:
        sig, a = sig[-a:], 0
    b = min(len(buf), a + len(sig))
    if b > a:
        buf[a:b] += sig[: b - a] * gain


def lowpass(x, fc, order=2):
    sos = signal.butter(order, min(fc, SR / 2 - 100) / (SR / 2), "low", output="sos")
    return signal.sosfilt(sos, x)


def bandpass(x, lo, hi, order=2):
    sos = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], "band", output="sos")
    return signal.sosfilt(sos, x)


# 立体声总线
padL, padR = np.zeros(N), np.zeros(N)
bass = np.zeros(N)
drums = np.zeros(N)
plL, plR = np.zeros(N), np.zeros(N)
keysL, keysR = np.zeros(N), np.zeros(N)
sfx = np.zeros(N)
sfx_verb = np.zeros(N)
kick_env = np.zeros(N)

beats = {"kicks": [], "impacts": [], "unlocks": [], "ticks": [], "downbeats": []}


def kick(t0, strength=1.0, heart=False):
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    f = (40 if heart else 45) + (70 if heart else 85) * np.exp(-t * (24 if heart else 30))
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * (7 if heart else 6))
    click = lowpass(rng.normal(0, 1, n) * np.exp(-t * 200), 900) * 0.3
    add(drums, t0, (body + click) * strength * (0.8 if heart else 1.0))
    env = np.exp(-t * 6)
    add(kick_env, t0, env * strength)
    beats["kicks"].append([round(t0, 4), round(strength, 2)])


def low_snare(t0, g=0.35):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    noise = bandpass(rng.normal(0, 1, n), 150, 1200) * np.exp(-t * 14)
    tone = np.sin(2 * np.pi * 175 * t) * np.exp(-t * 20)
    add(drums, t0, (noise * 0.8 + tone * 0.6) * g)


def tok(t0, g=0.12):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    add(drums, t0, bandpass(rng.normal(0, 1, n), 300, 1400) * np.exp(-t * 40) * g)


def pad_chord(t0, dur, chord, energy):
    n = int((dur + 0.9) * SR)
    env = adsr(n, 0.5, 1.0)
    notes = chord + [chord[0] + 12] + ([chord[1] + 12] if energy >= 2 else [])
    for i, m in enumerate(notes):
        f = mtof(m)
        for d, pan in ((-0.07, -0.6), (0.0, 0.0), (0.07, 0.6)):
            v = osc_table(f * 2 ** (d / 12), n, phase=rng.random()) * env * 0.09
            add(padL, t0, v * (1 - pan) * 0.7)
            add(padR, t0, v * (1 + pan) * 0.7)
    # 低八度的柔和正弦垫底
    sub = np.sin(2 * np.pi * mtof(chord[0] - 12) * np.arange(n) / SR) * env * 0.12
    add(padL, t0, sub)
    add(padR, t0, sub)


def bass_note(t0, dur, midi, g=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = mtof(midi)
    v = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)) * adsr(n, 0.01, min(0.15, dur * 0.4))
    add(bass, t0, v * g)


def pluck(t0, midi, pan, g=0.22):
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    f = mtof(midi)
    v = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(6 * np.pi * f * t) * np.exp(-t * 8)) * np.exp(-t * 3.2) * np.minimum(1, t / 0.003)
    v = lowpass(v, 7000)
    for k, (dt, gg) in enumerate(((0, 1.0), (0.75 * BEAT, 0.35), (1.5 * BEAT, 0.14))):
        p = pan if k % 2 == 0 else -pan
        add(plL, t0 + dt, v * g * gg * (1 - p))
        add(plR, t0 + dt, v * g * gg * (1 + p))


def epiano(t0, midi, dur, g=0.2):
    n = int((dur + 1.2) * SR)
    t = np.arange(n) / SR
    f = mtof(midi)
    idx = 2.2 * np.exp(-t * 3)
    v = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t)) * np.exp(-t * 1.6) * np.minimum(1, t / 0.004)
    v += 0.25 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 4)
    v *= np.clip((dur + 1.2 - t) / 1.2, 0, 1)
    add(keysL, t0, v * g * 0.9)
    add(keysR, t0 + 0.012, v * g * 1.1)


# ------------------------------------------------------------------ 低频转场音效
def impact(t0, g=1.0):
    n = int(3.5 * SR)
    t = np.arange(n) / SR
    f = 28 + 42 * np.exp(-t * 2.2)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.3)
    body = np.sin(2 * np.pi * 90 * t) * np.exp(-t * 9) * 0.5
    rumble = lowpass(rng.normal(0, 1, n), 160, 4) * np.exp(-t * 2.5) * 0.9
    v = (sub + body + rumble) * np.minimum(1, t / 0.004)
    add(sfx, t0, v * 0.9 * g)
    add(sfx_verb, t0, lowpass(v, 400) * 0.5 * g)
    beats["impacts"].append(round(t0, 4))


def riser(t_end, dur=BAR, g=0.6):
    """低频气流渐强：低通噪声的截止频率从 70Hz 升到 650Hz，叠加缓慢上行的次低音，在冲击前 60ms 收住。"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    out = np.zeros(n)
    blk = 2048
    zi = None
    for i in range(0, n, blk):
        fc = 70 + 580 * (i / n) ** 2
        sos = signal.butter(2, fc / (SR / 2), "low", output="sos")
        if zi is None:
            zi = signal.sosfilt_zi(sos) * 0
        out[i:i + blk], zi = signal.sosfilt(sos, noise[i:i + blk], zi=zi)
    sweep = np.sin(2 * np.pi * np.cumsum(30 + 30 * (t / dur) ** 2) / SR) * 0.5
    env = (t / dur) ** 2.2
    v = (out * 1.6 + sweep) * env
    v[-int(0.06 * SR):] = 0
    add(sfx, t_end - dur, v * g)


def low_tick(t0, g=0.5):
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    v = (np.sin(2 * np.pi * 98 * t) + 0.6 * np.sin(2 * np.pi * 196 * t)) * np.exp(-t * 9) * np.minimum(1, t / 0.003)
    add(sfx, t0, v * g)
    add(sfx_verb, t0, v * 0.3 * g)
    beats["ticks"].append(round(t0, 4))


def low_bell(t0, g=0.35):
    n = int(4 * SR)
    t = np.arange(n) / SR
    v = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, a, d in
            ((146.83, 1.0, 0.9), (220.0, 0.6, 1.1), (293.66, 0.45, 1.4), (146.83 * 2.76, 0.12, 2.5)))
    v *= np.minimum(1, t / 0.01)
    add(sfx, t0, v * g)
    add(sfx_verb, t0, v * 0.6 * g)
    beats["unlocks"].append(round(t0, 4))


MOTIF = {
    "default": [[(0, 69, 1), (1, 74, 1), (2, 77, 1.5), (3.5, 76, 0.5)], [(0, 74, 2), (2, 70, 1), (3, 72, 1)],
                [(0, 72, 1), (1, 69, 1), (2, 77, 1.5), (3.5, 76, 0.5)], [(0, 76, 2), (2, 72, 2)]],
    "finale": [[(0, 74, 1), (1, 77, 1), (2, 82, 2)], [(0, 79, 1), (1, 76, 1), (2, 79, 2)],
               [(0, 77, 1), (1, 81, 1), (2, 84, 2)], [(0, 81, 4)]],
}
KEYS_SECTIONS = {"title", "organ", "set3", "set4", "return", "finale"}

# ------------------------------------------------------------------ 编曲
secs = tl["sections"]
for si, sec in enumerate(secs):
    sid, E, s0, nb = sec["id"], sec["energy"], sec["start"], sec["bars"]
    prog = PROG.get(sid, PROG["default"])
    for b in range(nb):
        tb = s0 + b * BAR
        beats["downbeats"].append(round(tb, 4))
        chord = CH[prog[b % 4]]
        last_bar = sid == "refs" or (sid == "finale" and b == nb - 1)
        pad_chord(tb, BAR * (3 if sid == "refs" and b == nb - 1 else 1), CH["Dm"] if last_bar else chord, E)
        root = (CH["Dm"] if last_bar else chord)[0] - 12
        # 低音
        if E == 1 or sid in ("cold", "return"):
            bass_note(tb, BAR * 0.95, root, 0.38)
        elif E == 2:
            for k in range(4):
                bass_note(tb + k * BEAT, BEAT * 0.9, root, 0.42)
        elif E == 3:
            for k in range(8):
                bass_note(tb + k * BEAT / 2, BEAT * 0.45, root + (12 if k % 4 == 3 else 0), 0.42)
        # 鼓
        if sec.get("heart"):
            pass  # 心跳在卡片循环中处理
        elif E == 2:
            kick(tb, 1.0)
            kick(tb + 2 * BEAT, 0.85)
            low_snare(tb + 3 * BEAT, 0.22)
        elif E == 3:
            for k in range(4):
                kick(tb + k * BEAT, 1.0 if k == 0 else 0.85)
                tok(tb + k * BEAT + BEAT / 2, 0.1)
            low_snare(tb + BEAT, 0.3)
            low_snare(tb + 3 * BEAT, 0.3)
        elif E == 1:
            kick(tb, 0.6)
        # 拨弦琶音
        tones = [m + 12 for m in chord] + [chord[0] + 24]
        if E == 0 and sid not in ("refs",):
            for k in (0, 2):
                if rng.random() < 0.7:
                    pluck(tb + k * BEAT, int(rng.choice(tones)) + 12, 0.3, 0.12)
        elif E in (1, 2):
            for k in range(8):
                pluck(tb + k * BEAT / 2, tones[(k * 3 + b) % 4], 0.35, 0.13 if E == 1 else 0.15)
        elif E == 3:
            for k in range(16):
                pluck(tb + k * BEAT / 4, tones[(k * 5 + b) % 4] + (12 if k % 8 == 6 else 0), 0.4, 0.11)
        # 电钢琴动机
        if sid in KEYS_SECTIONS:
            motif = MOTIF["finale" if sid == "finale" else "default"][b % 4]
            for off, m, d in motif:
                epiano(tb + off * BEAT, m, d * BEAT, 0.16 if sid != "finale" else 0.2)
    # 心跳
    if sec.get("heart"):
        for c in sec["cards"]:
            per = 2 * BEAT if c.get("heartFast") else 4 * BEAT
            t = s0 + c["start"]
            while t < s0 + c["start"] + c["dur"] - 0.05:
                kick(t, 0.9, heart=True)
                kick(t + 0.28 * BEAT * 1.4, 0.6, heart=True)
                t += per
    # 卡片事件
    for c in sec["cards"]:
        tc = s0 + c["start"]
        if c.get("tick"):
            low_tick(tc)
        if c.get("unlock"):
            low_bell(tc + BEAT)
    # 段首冲击与铺垫
    if sec.get("impact"):
        impact(s0, 1.0 if sec.get("warp") else 0.75)
        if si > 0:
            riser(s0, BAR if sec.get("warp") else BAR * 0.75, 0.55 if sec.get("warp") else 0.4)

# ------------------------------------------------------------------ 混音
# 侧链：底鼓压低铺底与低音
duck = 1 - 0.35 * np.clip(kick_env, 0, 1)
padL *= duck
padR *= duck
bass *= 1 - 0.5 * np.clip(kick_env, 0, 1)

# 铺底滤波：按段落能量逐块调整截止频率
def filt_pad(x):
    out = np.zeros_like(x)
    zi = None
    blk = 4096
    for i in range(0, len(x), blk):
        t = i / SR
        E = next((s["energy"] for s in secs if s["start"] <= t < s["start"] + s["dur"]), 0)
        fc = CUTOFF[E]
        sos = signal.butter(2, fc / (SR / 2), "low", output="sos")
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        out[i:i + blk], zi = signal.sosfilt(sos, x[i:i + blk], zi=zi)
    return out


padL, padR = filt_pad(padL), filt_pad(padR)
bass = lowpass(bass, 400)

# 混响（合成立体声脉冲响应）
irn = int(3.2 * SR)
ti = np.arange(irn) / SR
irL = lowpass(rng.normal(0, 1, irn), 4500) * np.exp(-ti * 2.0)
irR = lowpass(rng.normal(0, 1, irn), 4500) * np.exp(-ti * 2.0)
pre = int(0.025 * SR)
irL[:pre] = 0
irR[:pre] = 0
irL /= np.sqrt(np.sum(irL ** 2))
irR /= np.sqrt(np.sum(irR ** 2))
sendL = padL * 0.35 + plL * 0.6 + keysL * 0.5 + sfx_verb
sendR = padR * 0.35 + plR * 0.6 + keysR * 0.5 + sfx_verb
revL = signal.oaconvolve(sendL, irL)[:N] * 0.9
revR = signal.oaconvolve(sendR, irR)[:N] * 0.9

# 段落能量分档增益（平滑过渡），让铺垫与高潮拉开层次；转场音效不受影响
EG = {0: 0.5, 1: 0.66, 2: 0.82, 3: 1.0}
gain = np.zeros(N)
for s_ in secs:
    a, b = int(s_["start"] * SR), int((s_["start"] + s_["dur"]) * SR)
    gain[a:b] = EG[s_["energy"]]
gain[int(TOTAL * SR):] = EG[0]
w = int(0.4 * SR)
gain = np.convolve(gain, np.ones(w) / w, mode="same")
musL = (padL * 0.8 + bass * 0.75 + drums * 0.85 + plL * 0.7 + keysL * 0.6 + revL) * gain
musR = (padR * 0.8 + bass * 0.75 + drums * 0.85 + plR * 0.7 + keysR * 0.6 + revR) * gain
L = musL + sfx * 0.95
R = musR + sfx * 0.95
mix = np.stack([L, R], axis=1)
mix = mix[: int((TOTAL + 0.5) * SR)]
# 淡入淡出
fi, fo = int(1.5 * SR), int(8 * SR)
mix[:fi] *= np.linspace(0, 1, fi)[:, None]
mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
mix /= np.max(np.abs(mix)) + 1e-9
mix = np.tanh(mix * 1.15) / np.tanh(1.15) * 0.95
sf.write(os.path.join(BUILD, "v3_music.wav"), mix.astype(np.float32), SR)
json.dump(beats, open(os.path.join(BUILD, "v3_beats.json"), "w"))
print("music", round(len(mix) / SR, 1), "s; kicks", len(beats["kicks"]), "impacts", len(beats["impacts"]))
