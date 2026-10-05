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


# ------------------------------------------------------------------ 电影感乐器（低频为主）
epL, epR = np.zeros(N), np.zeros(N)       # 低音重击 / 弦乐重复音型
choL, choR = np.zeros(N), np.zeros(N)     # 类人声合唱
hall = np.zeros(N)                        # 大厅混响发送（太鼓、重击）
music_gate = np.ones(N)                   # 冲击前的瞬间静音


def sweep_filter(x, fc_fn, order=2, blk=1024):
    out = np.zeros_like(x)
    zi = None
    n = len(x)
    for i in range(0, n, blk):
        fc = float(np.clip(fc_fn(i / SR), 40, SR / 2 - 200))
        sos = signal.butter(order, fc / (SR / 2), "low", output="sos")
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        out[i:i + blk], zi = signal.sosfilt(sos, x[i:i + blk], zi=zi)
    return out


def braam(t0, root, g=1.0, dur=3.4):
    """电影预告片式的低音重击：低八度锯齿叠加，滤波器猛开后缓缓合上，再加饱和。"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for m, a in ((root, 1.0), (root + 12, 0.75), (root + 7, 0.45), (root + 19, 0.2)):
        for d in (-0.13, 0.0, 0.13):
            sig += osc_table(mtof(m) * 2 ** (d / 12), n, phase=rng.random()) * a
    sig = sweep_filter(sig, lambda tt: 160 + 2000 * min(1, tt / 0.25) * np.exp(-max(0, tt - 0.25) * 1.6))
    env = np.minimum(1, t / 0.02) * np.exp(-t * 0.75) * np.clip((dur - t) / 0.8, 0, 1)
    sig = np.tanh(sig * env * 0.55) * 0.9
    sub = np.sin(2 * np.pi * mtof(root) * t) * env * 0.6
    add(epL, t0, (sig + sub) * g)
    add(epR, t0 + 0.009, (sig + sub) * g)
    add(hall, t0, sig * 0.35 * g)


def taiko(t0, g=1.0, low=False, pulse=True):
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    f0 = 52 if low else 72
    f = f0 + 70 * np.exp(-t * 16)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (4 if low else 5.5))
    skin = bandpass(rng.normal(0, 1, n), 70, 450) * np.exp(-t * 22) * 0.7
    v = (body + skin) * np.minimum(1, t / 0.002) * g
    add(drums, t0, v * 0.9)
    add(hall, t0, v * 0.45)
    add(kick_env, t0, np.exp(-t * 6) * g * 0.8)
    if pulse:
        beats["kicks"].append([round(t0, 4), round(min(1.0, g), 2)])


def tom_roll(t_end, dur=BAR, g=0.9):
    """冲击前越打越密、越打越响的太鼓推进，在冲击前 0.12 秒收住。"""
    t = t_end - dur
    step = BEAT / 2
    k = 0
    while t < t_end - 0.12:
        p = 1 - (t_end - t) / dur
        taiko(t, g * (0.25 + 0.75 * p ** 1.5), low=k % 2 == 0, pulse=p > 0.6)
        step = max(BEAT / 8, step * 0.86)
        t += step
        k += 1


def ostinato(tb, chord, E):
    """低音弦乐式的快速重复音型（八分 / 十六分音符），推动感的来源。"""
    root = chord[0] - 12
    pat = [0, 0, 7, 0, 12, 0, 7, 0] if E == 2 else [0, 0, 12, 0, 7, 0, 12, 7, 0, 0, 12, 0, 7, 12, 0, 7]
    steps = len(pat)
    dt = BAR / steps
    for i, iv in enumerate(pat):
        n = int(dt * 1.6 * SR)
        t = np.arange(n) / SR
        f = mtof(root + iv)
        v = osc_table(f, n, phase=rng.random()) + 0.5 * osc_table(f * 1.004, n, phase=rng.random())
        v = lowpass(v, 900 if E == 2 else 1400) * np.exp(-t * (14 if E == 3 else 10)) * np.minimum(1, t / 0.004)
        acc = 1.0 if i % (steps // 4) == 0 else 0.7
        pan = 0.25 if i % 2 else -0.25
        add(epL, tb + i * dt, v * 0.14 * acc * (1 - pan))
        add(epR, tb + i * dt, v * 0.14 * acc * (1 + pan))


def choir(tb, dur, chord, g=0.5):
    """类人声“啊——”：锯齿和弦经过元音共振峰滤波，慢起音，带轻微颤音。"""
    n = int((dur + 1.2) * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t)
    for m in chord + [chord[0] + 12]:
        f = mtof(m + 12)
        for d in (-0.08, 0.08):
            ph = np.cumsum(f * 2 ** (d / 12) * vib / SR) + rng.random()
            sig += np.interp(ph % 1.0 * TABLE, np.arange(TABLE + 1), np.append(SAW, SAW[0]))
    v = bandpass(sig, 600, 860) * 1.0 + bandpass(sig, 1000, 1250) * 0.55 + bandpass(sig, 2300, 2600) * 0.12
    v *= np.minimum(1, t / 0.7) * np.clip((dur + 1.2 - t) / 1.2, 0, 1) * g * 0.35
    add(choL, tb, v)
    add(choR, tb + 0.015, v)


def gap_before(t, length=0.28):
    """冲击前的瞬间静音：音乐在冲击前 length 秒内迅速压低，冲击时回到原样。"""
    a, b = int((t - length) * SR), int(t * SR)
    if a < 0:
        return
    k = b - a
    music_gate[a:b] = np.minimum(music_gate[a:b], np.linspace(1, 0.08, k) ** 1.5)


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
        # 电影感层：弦乐重复音型、太鼓、合唱
        if E >= 2 and not sec.get("heart") and sid != "title":
            ostinato(tb, chord, E)
        if E == 2 and not sec.get("heart"):
            taiko(tb, 0.75, low=True)
        if E == 3:
            taiko(tb, 1.0, low=True)
            taiko(tb + 1.5 * BEAT, 0.55)
            taiko(tb + 2 * BEAT, 0.8, low=True)
            taiko(tb + 3 * BEAT, 0.6)
            taiko(tb + 3.5 * BEAT, 0.7)
        if E == 3 or sid in ("title", "finale"):
            choir(tb, BAR, CH["Dm"] if last_bar else chord, 0.55 if E == 3 else 0.4)
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
        if c.get("hit"):
            braam(tc, 26, 1.25, dur=5.0)
            impact(tc, 1.0)
            tom_roll(tc, BAR, 1.0)
            gap_before(tc, 0.35)
            riser(tc, BAR, 0.5)
        if c.get("tick"):
            low_tick(tc)
        if c.get("unlock"):
            low_bell(tc + BEAT)
    # 段首冲击与铺垫
    if sec.get("impact"):
        big = sec.get("warp") or sid in ("title", "set4", "finale")
        impact(s0, 1.0 if big else 0.75)
        root = CH[prog[0]][0] - 24   # 低两个八度的根音
        braam(s0, root, 1.0 if big else 0.6, dur=4.0 if big else 3.0)
        if si > 0:
            riser(s0, BAR if big else BAR * 0.75, 0.5 if big else 0.35)
            if E >= 1:
                tom_roll(s0, BAR if big else BAR / 2, 0.9 if big else 0.6)
            gap_before(s0, 0.3 if big else 0.18)

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
EG = {0: 0.45, 1: 0.6, 2: 0.8, 3: 1.0}
gain = np.zeros(N)
for s_ in secs:
    a, b = int(s_["start"] * SR), int((s_["start"] + s_["dur"]) * SR)
    gain[a:b] = EG[s_["energy"]]
gain[int(TOTAL * SR):] = EG[0]
w = int(0.4 * SR)
gain = np.convolve(gain, np.ones(w) / w, mode="same")
# 大厅混响（太鼓、重击）：4.5 秒、偏暗
hn = int(4.5 * SR)
th = np.arange(hn) / SR
hL = lowpass(rng.normal(0, 1, hn), 2500) * np.exp(-th * 1.4)
hR = lowpass(rng.normal(0, 1, hn), 2500) * np.exp(-th * 1.4)
hL[:int(0.04 * SR)] = 0
hR[:int(0.04 * SR)] = 0
hL /= np.sqrt(np.sum(hL ** 2))
hR /= np.sqrt(np.sum(hR ** 2))
hallL = signal.oaconvolve(hall + (choL + choR) * 0.2, hL)[:N] * 0.8
hallR = signal.oaconvolve(hall + (choL + choR) * 0.2, hR)[:N] * 0.8
epL[:] = lowpass(epL, 5000)
epR[:] = lowpass(epR, 5000)
musL = (padL * 0.7 + bass * 0.8 + drums * 0.9 + plL * 0.6 + keysL * 0.55 + revL + choL * 0.9 + hallL * 0.9) * gain
musR = (padR * 0.7 + bass * 0.8 + drums * 0.9 + plR * 0.6 + keysR * 0.55 + revR + choR * 0.9 + hallR * 0.9) * gain
gate = np.convolve(music_gate, np.ones(240) / 240, mode="same")
L = (musL + epL * 0.85) * gate + sfx * 0.95
R = (musR + epR * 0.85) * gate + sfx * 0.95
mix = np.stack([L, R], axis=1)
mix = mix[: int((TOTAL + 0.5) * SR)]
# 淡入淡出
fi, fo = int(1.5 * SR), int(8 * SR)
mix[:fi] *= np.linspace(0, 1, fi)[:, None]
mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
# 母带：RMS 压缩（阈值 -18 dB、3:1）后软限幅
mono = np.abs(mix).max(axis=1)
env = np.sqrt(signal.lfilter([1 - np.exp(-1 / (0.03 * SR))], [1, -np.exp(-1 / (0.03 * SR))], mono ** 2) + 1e-12)
mix /= np.max(env) + 1e-9
env /= np.max(env) + 1e-9
db = 20 * np.log10(env + 1e-9)
thr, ratio = -18.0, 3.0
gr = np.where(db > thr, (db - thr) * (1 - 1 / ratio), 0.0)
gr = signal.lfilter([1 - np.exp(-1 / (0.15 * SR))], [1, -np.exp(-1 / (0.15 * SR))], gr)
mix *= (10 ** (-gr / 20))[:, None]
# 峰值限幅：以 99.95% 分位为满刻度，超出部分软削，整体响度更足
ref = np.quantile(np.abs(mix), 0.9995)
mix = mix / (ref + 1e-9) * 0.82
mix = np.tanh(mix * 1.25) / np.tanh(1.25) * 0.97
mix = np.clip(mix, -0.98, 0.98)
sf.write(os.path.join(BUILD, "v3_music.wav"), mix.astype(np.float32), SR)
json.dump(beats, open(os.path.join(BUILD, "v3_beats.json"), "w"))
print("music", round(len(mix) / SR, 1), "s; kicks", len(beats["kicks"]), "impacts", len(beats["impacts"]))
