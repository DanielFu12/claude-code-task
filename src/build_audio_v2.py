# -*- coding: utf-8 -*-
"""v2 配乐：复用 v1 的旁白与时间轴，换成更有电影感的氛围铺底，并在粒子爆发/章节转场处加入音效。
输出 build/audio_v2.wav（与 build/timeline.json 对齐）。"""
import json
import os

import numpy as np
import soundfile as sf

from build_audio import BUILD, SR, SCENES, speakable, synth

rng = np.random.default_rng(42)


def whoosh(dur=1.6, amp=0.22, rise=0.7):
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    # 频率随时间扫动的简易带通：对白噪声做一阶低通，截止频率逐渐升高再降低
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    cutoff = 300 + 5000 * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.zeros(n)
    acc = 0.0
    for i in range(n):  # 只有几秒，逐点计算即可
        acc = a[i] * acc + (1 - a[i]) * noise[i]
        y[i] = acc
    y = y / (np.max(np.abs(y)) + 1e-9)
    return (amp * y * env).astype(np.float32)


def boom(amp=0.35):
    t = np.arange(int(2.5 * SR)) / SR
    f = 55 * np.exp(-t * 1.5) + 32
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (amp * np.sin(ph) * np.exp(-t * 1.8) * np.minimum(1, t / 0.01)).astype(np.float32)


def shimmer(amp=0.06, dur=2.2):
    t = np.arange(int(dur * SR)) / SR
    s = sum(np.sin(2 * np.pi * f * t + i) * np.exp(-t * (1.5 + i * 0.4)) for i, f in enumerate([1318.5, 1760, 2093, 2637]))
    return (amp * s / 4 * np.minimum(1, t / 0.02)).astype(np.float32)


def tick(amp=0.12):
    t = np.arange(int(0.06 * SR)) / SR
    return (amp * np.sin(2 * np.pi * 1300 * t) * np.exp(-t * 70)).astype(np.float32)


def drone(total):
    """深色氛围铺底：低频持续音 + 缓慢呼吸的和弦泛音 + 稀疏高音粒。"""
    n = int(total * SR)
    t = np.arange(n) / SR
    midi = lambda m: 440 * 2 ** ((m - 69) / 12)
    out = 0.5 * np.sin(2 * np.pi * midi(33) * t) + 0.3 * np.sin(2 * np.pi * midi(45) * t + 0.3 * np.sin(2 * np.pi * 0.05 * t))
    chords = [[57, 60, 64, 69], [53, 57, 60, 65], [48, 55, 60, 64], [55, 59, 62, 67]]
    seg = 10.0
    for k in range(int(np.ceil(total / seg)) + 1):
        t0 = k * seg - 2
        a, b = max(0, int(t0 * SR)), min(n, int((t0 + seg + 4) * SR))
        if a >= b:
            continue
        tt = t[a:b] - t0
        env = np.sin(np.pi * np.clip(tt / (seg + 4), 0, 1)) ** 2
        for i, m in enumerate(chords[k % 4]):
            f = midi(m)
            out[a:b] += 0.22 * env * (np.sin(2 * np.pi * f * tt + i) + 0.5 * np.sin(2 * np.pi * (f * 1.003) * tt)) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.08 * tt + i))
    # 稀疏高音粒（像粒子闪烁）
    for k in range(int(total / 1.7)):
        ts = k * 1.7 + rng.uniform(0, 1.2)
        s0 = int(ts * SR)
        if s0 >= n:
            break
        s1 = min(n, s0 + int(2.0 * SR))
        tp = t[s0:s1] - ts
        f = midi(rng.choice([76, 79, 81, 84, 88]))
        out[s0:s1] += 0.08 * np.sin(2 * np.pi * f * tp) * np.exp(-tp * 2.5) * np.minimum(1, tp / 0.005)
    out *= 0.02 / (np.sqrt(np.mean(out ** 2)) + 1e-9)
    return out.astype(np.float32)


def main():
    tl = json.load(open(os.path.join(BUILD, "timeline.json")))
    total = tl["total"]
    n = int(total * SR) + SR
    voice = np.zeros(n, np.float32)
    speech = np.zeros(n, np.float32)
    sfx = []
    for sc, t in zip(SCENES, tl["scenes"]):
        for i, line in enumerate(sc["lines"]):
            say = line if isinstance(line, str) else line[1]
            clip = synth(speakable(say))
            a = int((t["start"] + t["ls"][i]) * SR)
            voice[a:a + len(clip)] += clip
            speech[a:a + len(clip)] = 1
        kind = sc.get("kind", "normal")
        if kind == "chapter":
            sfx += [(t["start"] - 0.4, whoosh(2.0, 0.2)), (t["start"] + 0.2, boom(0.3)), (t["start"] + 0.4, shimmer(0.05))]
        for i in sc.get("pause", {}):
            for k in range(3):
                sfx.append((t["start"] + t["ls"][i] + t["ld"][i] + 0.15 + k, tick()))
    # 片名粒子爆发（场景 3 第 4 句 70% 处）与片尾
    s3 = tl["scenes"][3]
    sfx += [(s3["start"] + s3["ls"][3] + 0.7 * s3["ld"][3] - 0.5, whoosh(1.4, 0.18)), (s3["start"] + s3["ls"][3] + 0.72 * s3["ld"][3], boom(0.32)),
            (s3["start"] + s3["ls"][3] + 0.72 * s3["ld"][3] + 0.1, shimmer(0.06))]
    voice *= 0.89 / np.max(np.abs(voice))
    win = int(0.6 * SR)
    c = np.cumsum(np.concatenate([[0], speech]))
    sm = (c[win:] - c[:-win]) / win
    sm = np.concatenate([sm, np.full(n - len(sm), sm[-1])])
    bgm = drone(n / SR) * (1.0 - 0.4 * sm)
    fi, fo = int(2 * SR), int(5 * SR)
    bgm[:fi] *= np.linspace(0, 1, fi)
    bgm[-fo:] *= np.linspace(1, 0, fo)
    mix = voice + bgm
    for st, s in sfx:
        a = int(st * SR)
        if a < 0:
            s, a = s[-a:], 0
        mix[a:a + len(s)] += s[: max(0, n - a)]
    mix = np.clip(mix, -0.99, 0.99)
    sf.write(os.path.join(BUILD, "audio_v2.wav"), mix[: int(total * SR)], SR)
    print("audio_v2", total)


if __name__ == "__main__":
    main()
