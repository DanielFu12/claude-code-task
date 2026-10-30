"""按 timeline 合成全片原创配乐（D 小调，96 BPM），输出 work/score.wav。

段落：低频心跳开场 → 标题重拍 → 身份介绍（八分音型）→ 时间隧道（十六分固定音型 + 底鼓）
→ 抽空蓄力 → Sub Drop 断崖 → 悬停 → 全景高潮 → 钢琴启示 → 片尾大三和弦。
"""
import os, sys
import numpy as np
import soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from synth import SR, Bus, mallet, pad, sub, pluck_bass, kick, thump, boom, subdrop, swell, bell, piano, taiko, \
    reverb, sidechain, lp, hp
from timeline import BAR, BEAT, DURATION, HITS, QSCHED, b

CH = {  # 和弦：(低音根音 midi, 铺底音符)
    "Dm": (38, [50, 53, 57, 62]), "Bb": (34, [46, 50, 53, 58]), "F": (41, [48, 53, 57, 60]),
    "C": (36, [48, 52, 55, 60]), "Gm": (43, [46, 50, 55, 58]), "A": (45, [49, 52, 57, 61]),
    "Dsus": (38, [50, 55, 57, 62]), "D": (38, [50, 54, 57, 62]), "Bbm7": (34, [46, 53, 57, 62]),
}
PROG = {}
def setp(bar0, seq):
    for i, c in enumerate(seq):
        PROG[bar0 + i] = c

setp(0, ["Dm"] * 5)
setp(5, ["Dm", "Bb", "Dm"])
setp(8, ["Dm", "Bb", "F", "C", "Dm", "Bb", "F", "C", "Gm", "A"])
setp(18, (["Dm", "Bb", "F", "C"] * 6))
setp(42, ["Bbm7", "A"])
setp(44, ["Dm", "Bb", "Gm", "A"])
setp(48, ["Bb", "A"])
setp(50, ["Dm", "Bb", "F", "C", "Dm", "Bb", "F", "C", "Gm", "A"])
setp(60, ["Bb", "F", "C", "Dm", "Bb", "F", "A"])
setp(67, ["Bb", "F", "Dsus", "D"])


def section(bar):
    if bar < 5: return "open"
    if bar < 8: return "title"
    if bar < 18: return "ident"
    if bar < 42: return "tunnel"
    if bar < 44: return "break"
    if bar < 48: return "collapse"
    if bar < 50: return "latest"
    if bar < 60: return "trend"
    if bar < 67: return "lessons"
    return "end"


def main(out):
    N = DURATION + 4.0
    pads, bass, drums, fx, lead = Bus(N), Bus(N), Bus(N), Bus(N), Bus(N)
    kicks = []

    # ---------------- 铺底 + Sub
    for bar in range(71):
        sec = section(bar)
        root, notes = CH[PROG[bar]]
        t0 = b(bar)
        gain = {"open": 0.32, "title": 0.8, "ident": 0.6, "tunnel": 0.62 + (bar - 18) * 0.008, "break": 0.5,
                "collapse": 0.72, "latest": 0.45, "trend": 1.05, "lessons": 0.6, "end": 0.9}[sec]
        bright = {"open": 3.0, "trend": 11.0, "end": 9.0, "collapse": 4.0, "latest": 3.5, "lessons": 6.0,
                  "tunnel": 8.0 + (bar - 18) * 0.1}.get(sec, 7.0)
        if sec == "open" and bar < 2:
            gain *= (bar + 0.5) / 2
        dur = BAR + (6.0 if bar == 70 else 0.9)
        pads.add(pad(notes, dur, bright=bright, att=0.5 if sec != "open" else 2.0, rel=0.9 if bar < 70 else 4.5,
                     seed=bar), t0 - 0.05, gain)
        # 高八度弦乐线（高潮 / 片尾）
        if sec in ("trend", "end") or (sec == "tunnel" and bar >= 30):
            top = [n + 12 for n in notes[1:]]
            pads.add(pad(top, dur, bright=3.0, att=0.6, rel=1.0, seed=bar + 100), t0, 0.32 if sec != "tunnel" else 0.18)
        # Sub 持续低音
        if sec not in ("lessons",) or bar >= 63:
            sg = {"open": 0.5, "break": 0.35, "latest": 0.35, "lessons": 0.3}.get(sec, 0.55)
            bass.add(sub(root - 12 if root > 40 else root, BAR + 0.3, att=0.08, rel=0.35), t0, sg)

    # ---------------- 固定音型
    pat8 = [0, 0, 12, 0, 7, 0, 12, 10]
    pat16 = [0, 0, 12, 0, 0, 7, 0, 12, 0, 0, 12, 0, 10, 7, 12, 0]
    for bar in range(8, 60):
        sec = section(bar)
        if sec in ("break", "latest"):
            continue
        root = CH[PROG[bar]][0]
        t0 = b(bar)
        if sec == "ident" or (sec == "tunnel" and bar < 22) or sec == "collapse":
            for k, iv in enumerate(pat8):
                g = 0.30 if sec != "collapse" else 0.22
                bass.add(pluck_bass(root + iv, 0.36, cutoff=700 if sec == "ident" else 900), t0 + k * BEAT / 2, g)
        else:
            cut = 900 + (bar - 22) * 40 if sec == "tunnel" else 1700
            for k, iv in enumerate(pat16):
                acc = 1.0 if k % 4 == 0 else 0.72
                bass.add(pluck_bass(root + iv, 0.22, cutoff=min(cut, 1900)), t0 + k * BEAT / 4,
                         0.27 * acc if sec == "tunnel" else 0.32 * acc)

    # ---------------- 「时钟」音型：和弦分解十六分音符（隧道后半与高潮）
    arp_oct = [0, 12, 7, 12, 3, 12, 7, 15]
    for bar in list(range(26, 42)) + list(range(50, 60)):
        root, notes = CH[PROG[bar]]
        t0 = b(bar)
        tones = sorted(set(n % 12 for n in notes))
        for k in range(16):
            n = notes[k % len(notes)] + 12 + (12 if k % 8 >= 4 else 0)
            v = (1.0 if k % 4 == 0 else 0.6) * (0.75 if bar < 50 else 1.0)
            lead.add(mallet(n, 0.45, v), t0 + k * BEAT / 4, 0.085)

    # ---------------- 鼓
    for bar in range(71):
        sec = section(bar)
        t0 = b(bar)
        beats = []
        if sec == "open" and bar >= 2:
            beats = [0, 2.5] if bar < 4 else [0, 1, 2, 2.5, 3, 3.5]   # 心跳 → 加速
        elif sec == "ident":
            beats = [0, 2]
        elif sec == "tunnel":
            beats = [0, 2] if bar < 26 else [0, 1, 2, 3]
        elif sec == "collapse":
            beats = [0] if bar > 44 else []
        elif sec == "trend":
            beats = [0, 1, 2, 3]
        elif sec == "lessons" and bar >= 63:
            beats = [0, 2]
        for bt in beats:
            tt = t0 + bt * BEAT
            if sec == "open":
                drums.add(thump(0.4, 95, 45), tt, 0.55)
            else:
                drums.add(kick(), tt, 0.62 if sec != "lessons" else 0.4)
                kicks.append(tt)
        # 太鼓：每 4 小节一次过门
        if sec in ("tunnel", "trend") and bar % 4 == 3:
            for k, bt in enumerate([2.5, 3.0, 3.5]):
                drums.add(taiko(), t0 + bt * BEAT, 0.28 + 0.1 * k)
        if sec == "collapse":
            drums.add(taiko(1.8), t0 + 2 * BEAT, 0.35)

    # ---------------- 季度切换：低频脉冲 + 玻璃钟音（和弦内音，中低音区）
    hit_times = {round(h[0], 3) for h in HITS}
    for i, s, d, note in QSCHED:
        tt = b(s)
        if round(tt, 3) not in hit_times:
            fx.add(thump(), tt, 0.5)
        notes = CH[PROG[s]][1]
        lead.add(bell(notes[(i * 2) % len(notes)] + 12, 2.2), tt, 0.13)

    # ---------------- 重拍 / Sub Drop / 渐强
    for tt, strength, kind in HITS:
        if kind in ("boom", "drop"):
            fx.add(boom(4.5), tt, 0.85 * strength)
            fx.add(swell(2.4 if kind == "boom" else 4.8, notes=(38, 45, 50, 57)), tt - (2.4 if kind == "boom" else 4.8),
                   0.5 * strength)
        if kind == "drop":
            fx.add(subdrop(3.2, 92, 22), tt, 1.0)
            fx.add(taiko(2.0), tt, 0.6)
        if kind == "pulse":
            fx.add(thump(0.6, 110, 40), tt, 1.0 * strength + 0.3)
            fx.add(subdrop(1.4, 70, 30), tt, 0.5 * strength)
            drums.add(taiko(1.6), tt, 0.45 * strength + 0.1)
    # 抽空：心跳 + 渐强
    for k in range(8):
        fx.add(thump(0.5, 90, 42), b(42) + k * BEAT, 0.35 + 0.05 * k)

    # ---------------- 钢琴（启示段与片尾）
    mel = [(60, 0, 74), (60, 1.5, 72), (60, 2, 69), (61, 0, 72), (61, 2, 69), (61, 3, 65),
           (62, 0, 67), (62, 2, 64), (63, 0, 65), (63, 1, 69), (63, 2, 74),
           (64, 0, 74), (64, 2, 77), (65, 0, 72), (65, 2, 69), (66, 0, 73), (66, 2, 76),
           (67, 0, 74), (68, 0, 72), (69, 0, 74), (69, 2, 78), (70, 0, 81)]
    for bar, bt, n in mel:
        lead.add(piano(n, 3.5), b(bar) + bt * BEAT, 0.22)
        lead.add(piano(n - 12, 3.5, 0.6), b(bar) + bt * BEAT, 0.12)

    # ---------------- 混音
    n = len(pads.x)
    sc = sidechain(kicks, n, depth=0.4, rel=0.22)[:, None]
    P = reverb(pads.x * sc, 3.2, 0.35)
    Bs = bass.x * (0.55 + 0.45 * sc)
    Bs = reverb(Bs, 1.4, 0.12, lpf=2000, seed=11)
    D = reverb(drums.x, 1.8, 0.14, lpf=2500, seed=5)
    F = reverb(fx.x, 3.8, 0.3, lpf=1800, seed=9)
    L = reverb(lead.x, 3.6, 0.42, lpf=5000, seed=13)
    mix = P * 1.45 + Bs * 0.55 + D * 0.8 + F * 0.8 + L * 1.25
    mix = hp(mix, 22, 2)
    # 整体包络：首尾淡入淡出
    tt = np.arange(n) / SR
    mix *= np.clip(tt / 0.4, 0, 1)[:, None]
    fade0 = DURATION - 2.5
    mix *= np.clip(1 - (tt - fade0) / 2.5, 0, 1)[:, None] ** 1.5
    mix = mix[:int(DURATION * SR)]
    # 母带：RMS 归一 + 软限幅
    rms = np.sqrt((mix ** 2).mean())
    mix *= 0.16 / rms
    mix = np.tanh(mix * 1.15) / 1.15
    mix *= 0.93 / np.abs(mix).max()
    sf.write(out, mix.astype(np.float32), SR, subtype="PCM_24")
    print("score ->", out, f"{len(mix) / SR:.2f}s rms={np.sqrt((mix ** 2).mean()):.3f}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "work", "score.wav"))
