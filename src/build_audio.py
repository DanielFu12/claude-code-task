# -*- coding: utf-8 -*-
"""合成旁白、背景音乐与音效，输出 build/audio.wav、build/timeline.json 和字幕 .srt。"""
import hashlib
import json
import os
import re

import numpy as np
import soundfile as sf

from content import SCENES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = os.path.join(ROOT, "assets/models/kokoro-multi-lang-v1_1/")
BUILD = os.path.join(ROOT, "build")
SR = 24000
VOICE_ID = 58      # Kokoro v1.1 中文男声
SPEED = 1.12
GAP = 0.30         # 句间停顿
PADS = {"normal": (0.45, 0.75), "title": (0.6, 1.1), "chapter": (0.7, 1.0), "refs": (0.3, 0.0)}

_tts = None


def tts_engine():
    global _tts
    if _tts is None:
        import sherpa_onnx
        kc = sherpa_onnx.OfflineTtsKokoroModelConfig(
            model=M + "model.onnx", voices=M + "voices.bin", tokens=M + "tokens.txt",
            data_dir=M + "espeak-ng-data", dict_dir=M + "dict",
            lexicon=M + "lexicon-us-en.txt," + M + "lexicon-zh.txt")
        cfg = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(kokoro=kc, num_threads=4),
            rule_fsts=M + "phone-zh.fst," + M + "date-zh.fst," + M + "number-zh.fst",
            max_num_sentences=1)
        _tts = sherpa_onnx.OfflineTts(cfg)
    return _tts


def speakable(text):
    text = re.sub(r"[“”《》「」]", "", text)
    text = text.replace("——", "，").replace("……", "，").replace("·", "")
    return text


def trim(a, thr=0.01, margin=0.03):
    env = np.convolve(np.abs(a), np.ones(240) / 240, mode="same")
    idx = np.where(env > thr)[0]
    if len(idx) == 0:
        return a
    m = int(margin * SR)
    return a[max(0, idx[0] - m): idx[-1] + m]


def synth(text):
    os.makedirs(os.path.join(BUILD, "tts"), exist_ok=True)
    key = hashlib.md5(f"{VOICE_ID}|{SPEED}|{text}".encode()).hexdigest()[:16]
    path = os.path.join(BUILD, "tts", key + ".wav")
    if not os.path.exists(path):
        g = tts_engine().generate(text, sid=VOICE_ID, speed=SPEED)
        a = trim(np.asarray(g.samples, dtype=np.float32))
        fade = int(0.01 * SR)
        a[:fade] *= np.linspace(0, 1, fade)
        a[-fade:] *= np.linspace(1, 0, fade)
        sf.write(path, a, SR)
    return sf.read(path, dtype="float32")[0]


def bell(freq, dur=2.5, amp=0.1):
    t = np.arange(int(dur * SR)) / SR
    s = sum(w * np.sin(2 * np.pi * freq * r * t) * np.exp(-t * k)
            for r, w, k in [(1, 1, 2.2), (2.0, 0.35, 3.5), (3.01, 0.15, 5), (4.2, 0.06, 7)])
    return (amp * s * np.minimum(1, t / 0.005)).astype(np.float32)


def tick(amp=0.12):
    t = np.arange(int(0.06 * SR)) / SR
    return (amp * np.sin(2 * np.pi * 1300 * t) * np.exp(-t * 70)).astype(np.float32)


def music(total):
    """柔和的氛围铺底：Am - F - C - G 循环，外加稀疏的琶音。"""
    n = int(total * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, dtype=np.float64)
    midi = lambda m: 440 * 2 ** ((m - 69) / 12)
    chords = [[45, 57, 60, 64], [41, 57, 60, 65], [48, 55, 60, 64], [43, 55, 59, 62]]
    seg = 8.0
    nseg = int(np.ceil(total / seg)) + 1
    for k in range(nseg):
        notes = chords[k % 4]
        t0 = k * seg - 1.5
        a, b = max(0, int(t0 * SR)), min(n, int((t0 + seg + 3.0) * SR))
        if a >= b:
            continue
        tt = t[a:b] - t0
        env = np.sin(np.pi * np.clip(tt / (seg + 3.0), 0, 1)) ** 1.5
        sig = np.zeros(b - a)
        for i, m in enumerate(notes):
            f = midi(m)
            w = 1.0 if i else 0.8
            sig += w * (np.sin(2 * np.pi * f * tt + i) + 0.6 * np.sin(2 * np.pi * (f + 0.25) * tt) +
                        0.12 * np.sin(2 * np.pi * 2 * f * tt))
        out[a:b] += sig * env
        # 琶音：每拍一个和弦音，衰减很快
        arp = [notes[1] + 12, notes[2] + 12, notes[3] + 12, notes[2] + 12]
        for j in range(8):
            ts = k * seg + j * 1.0
            s0 = int(ts * SR)
            if s0 >= n or s0 < 0:
                continue
            s1 = min(n, s0 + int(1.6 * SR))
            tp = t[s0:s1] - ts
            f = midi(arp[j % 4])
            out[s0:s1] += 0.5 * np.sin(2 * np.pi * f * tp) * np.exp(-tp * 3.2) * np.minimum(1, tp / 0.01)
    out *= 0.022 / (np.sqrt(np.mean(out ** 2)) + 1e-9)
    return out.astype(np.float32)


def fmt_srt(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main():
    os.makedirs(BUILD, exist_ok=True)
    timeline, placed, sfx = [], [], []
    t = 0.0
    for si, sc in enumerate(SCENES):
        kind = sc.get("kind", "normal")
        pad0, pad1 = PADS[kind]
        pad1 = sc.get("end_pad", pad1)
        ls, ld, subs = [], [], []
        cur = pad0
        for i, line in enumerate(sc["lines"]):
            disp, say = (line, line) if isinstance(line, str) else line
            clip = synth(speakable(say))
            ls.append(cur)
            ld.append(len(clip) / SR)
            subs.append(disp)
            placed.append((t + cur, clip))
            cur += len(clip) / SR + GAP + sc.get("pause", {}).get(i, 0)
        dur = (cur - GAP + pad1) if sc["lines"] else sc.get("hold", 6.0)
        if kind == "chapter":
            sfx.append((t + 0.15, bell(659.25, amp=0.09)))
            sfx.append((t + 0.35, bell(987.77, amp=0.05)))
        for i, p in sc.get("pause", {}).items():
            for k in range(3):
                sfx.append((t + ls[i] + ld[i] + 0.15 + k, tick()))
        timeline.append(dict(start=round(t, 4), dur=round(dur, 4), ls=ls, ld=ld, subs=subs))
        print(f"scene {si:2d} {kind:8s} {dur:6.2f}s  {subs[0] if subs else ''}")
        t += dur

    total = t
    n = int(total * SR) + SR
    voice = np.zeros(n, dtype=np.float32)
    for st, clip in placed:
        a = int(st * SR)
        voice[a:a + len(clip)] += clip
    peak = np.max(np.abs(voice))
    voice *= 0.89 / peak

    # 有人声时把背景音乐压低（ducking）
    speech = np.zeros(n, dtype=np.float32)
    for st, clip in placed:
        a = int(st * SR)
        speech[a:a + len(clip)] = 1
    win = int(0.6 * SR)
    c = np.cumsum(np.concatenate([[0], speech]))
    smooth = (c[win:] - c[:-win]) / win
    smooth = np.concatenate([smooth, np.full(n - len(smooth), smooth[-1])])
    bgm = music(n / SR) * (1.0 - 0.45 * smooth)
    # 片头淡入、片尾淡出
    fi, fo = int(1.5 * SR), int(4 * SR)
    bgm[:fi] *= np.linspace(0, 1, fi)
    bgm[-fo:] *= np.linspace(1, 0, fo)

    mix = voice + bgm
    for st, s in sfx:
        a = int(st * SR)
        mix[a:a + len(s)] += s[: max(0, n - a)]
    mix = np.clip(mix, -0.99, 0.99)
    sf.write(os.path.join(BUILD, "audio.wav"), mix[: int(total * SR)], SR)

    json.dump(dict(total=total, scenes=timeline), open(os.path.join(BUILD, "timeline.json"), "w"), ensure_ascii=False, indent=1)
    with open(os.path.join(BUILD, "subtitles.srt"), "w", encoding="utf-8") as f:
        k = 1
        for sc in timeline:
            for st, d, s in zip(sc["ls"], sc["ld"], sc["subs"]):
                a = sc["start"] + st
                f.write(f"{k}\n{fmt_srt(a)} --> {fmt_srt(a + d + 0.15)}\n{s}\n\n")
                k += 1
    print(f"total {total:.1f}s ({total / 60:.1f} min)")


if __name__ == "__main__":
    main()
