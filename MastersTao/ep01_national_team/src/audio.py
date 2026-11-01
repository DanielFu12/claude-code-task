"""按 timeline 合成全片原创配乐（D 小调 → 升 E，120 BPM），输出 work/score.wav。

一条情绪线（与画面一一对应）：
  钩子：钢琴主题 + 心跳，军鼓滚奏加速 → 标题：预告片式重击
  对决：四拍底鼓 + 反拍低音，逐段加入军鼓、十六分镲、反拍和弦「抽吸」；每季重音强度由当季变化幅度决定
  今年以来：全部抽空 → 一季度半速 → 滚奏 + 吸气 → 断崖：Sub Drop + 咆哮低音
  今年总结：第一次高潮（主旋律完整出现）→ 它们是谁：中速推进，保持律动 → 一句话区分：两小节滚奏蓄力
  三条启示：全曲最高潮，整体升调 +2（D 小调 → E 小调），满编鼓组 + 主旋律八度 → 片尾：E 大三和弦落定
所有转场冲击都是低频（boom / sub drop / 脉冲），不使用高频 Whoosh 与白噪声。
"""
import json, os, sys
import numpy as np
import soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from synth import SR, Bus, mallet, pad, sub, pluck_bass, kick, thump, boom, subdrop, bell, piano, taiko, \
    clap, supersaw, riser, tom_roll, tick_hat, pluck_lead, snare, snare_roll, growl, chord_stab, \
    reverb, sidechain, lp, hp
from timeline import BAR, BEAT, DURATION, HITS, QSCHED, b, section

CH = {
    "Dm": (38, [50, 53, 57, 62]), "Bb": (34, [46, 50, 53, 58]), "F": (41, [48, 53, 57, 60]),
    "C": (36, [48, 52, 55, 60]), "Gm": (43, [46, 50, 55, 58]), "A": (45, [49, 52, 57, 61]),
    "Dsus": (38, [50, 55, 57, 62]), "D": (38, [50, 54, 57, 62]),
}
PROG = {}
def setp(bar0, seq):
    for i, c in enumerate(seq):
        PROG[bar0 + i] = c

setp(0, ["Dm", "Dm", "Bb", "Bb", "A"])
setp(5, ["Dm", "Bb"])
setp(7, ["Dm", "Bb", "F", "C"] * 4)
setp(23, ["Gm", "A", "Bb", "A"])
setp(27, ["Dm", "Bb", "A"])
setp(30, ["Dm", "Bb", "Gm", "A", "Bb", "A"])
setp(36, ["F", "C", "Dm", "Bb"])
setp(40, ["Dm", "Bb", "F", "C"] * 2 + ["Dm"])
setp(49, ["Bb", "A"])
setp(51, ["F", "C", "Dm", "Bb", "F", "C", "Dm", "Bb", "Gm", "A"])
setp(61, ["Bb", "F", "Dsus", "D", "D"])

MOTIF_A = [(0, 69, 1), (1, 74, 1), (2, 77, 1.5), (3.5, 76, 0.5), (4, 74, 1), (5, 72, 1), (6, 69, 2)]
MOTIF_B = [(0, 69, 1), (1, 74, 1), (2, 77, 1), (3, 79, 1), (4, 81, 1.5), (5.5, 79, 0.5), (6, 77, 2)]
MOTIF_C = [(0, 81, 1), (1, 79, 1), (2, 77, 1), (3, 76, 1), (4, 74, 2), (6, 74, 2)]


def tr(bar):
    """升调：三条启示与片尾整体 +2 半音"""
    return 2 if bar >= 51 else 0


def chord(bar):
    root, notes = CH[PROG[bar]]
    k = tr(bar)
    return root + k, [n + k for n in notes]


def main(out):
    N = DURATION + 4.0
    pads, bass, drums, fx, lead, keys, hits = (Bus(N) for _ in range(7))
    kicks = []

    def motif(bus, m, bar, inst, gain, oct=0):
        k = tr(bar)
        for bt, n, d in m:
            tt = b(bar) + bt * BEAT
            if inst == "piano":
                bus.add(piano(n + k + oct, 2.8 + d * BEAT), tt, gain)
                bus.add(piano(n + k + oct - 12, 2.8, 0.55), tt, gain * 0.45)
            else:
                bus.add(supersaw(n + k + oct, d * BEAT + 0.15, cutoff=4200), tt, gain)
                bus.add(supersaw(n + k + oct - 12, d * BEAT + 0.15, cutoff=2400, seed=3), tt, gain * 0.5)

    # ---------------- 铺底 / 高弦 / Sub
    for bar in range(66):
        sec = section(bar)
        root, notes = chord(bar)
        t0 = b(bar)
        g = {"hook": 0.3 + 0.08 * bar, "title": 0.9, "duel": 0.55, "ytd": 0.95, "who_hj": 0.6, "who_zj": 0.65,
             "compare": 0.75, "lessons": 1.0, "end": 0.95}[sec]
        if 25 <= bar < 27: g = 0.5
        if bar == 29: g = 0.25
        if 30 <= bar < 34: g = 0.75
        bright = {"ytd": 10.0, "lessons": 11.0, "end": 9.0, "hook": 4.0}.get(sec, 7.0)
        if 30 <= bar < 36: bright = 3.5
        dur = BAR + (6.0 if bar == 65 else 0.8)
        pads.add(pad(notes, dur, bright=bright, att=0.25 if sec != "hook" else 1.0, rel=0.8 if bar < 65 else 4.5,
                     seed=bar), t0 - 0.03, g)
        if sec in ("ytd", "lessons", "end", "compare") or (sec == "duel" and 15 <= bar < 25):
            pads.add(pad([n + 12 for n in notes[1:]], dur, bright=3.5, att=0.4, rel=0.9, seed=bar + 100), t0,
                     0.36 if sec != "duel" else 0.2)
        if bar != 29 and not (30 <= bar < 34):
            sg = {"hook": 0.4, "end": 0.5}.get(sec, 0.5)
            if 25 <= bar < 27: sg = 0.3
            bass.add(sub(root - 12 if root > 40 else root, BAR + 0.25, att=0.05, rel=0.3), t0, sg)

    # ---------------- 低音：反拍推进（8 分）/ 十六分固定音型 / 断崖咆哮
    pat16 = [0, 0, 12, 0, 0, 7, 0, 12, 0, 0, 12, 0, 10, 7, 12, 0]
    for bar in range(66):
        sec = section(bar)
        root, _ = chord(bar)
        t0 = b(bar)
        if sec in ("hook", "end") or 25 <= bar < 27 or bar == 29 or 34 <= bar < 36:
            continue
        if 30 <= bar < 34:      # 断崖：咆哮低音，LFO 每拍 2 → 4 次
            bass.add(growl(root - 12, BAR, rate=4.0 if bar < 32 else 8.0), t0, 0.32)
            continue
        if sec in ("title",) or (sec == "duel" and bar < 15) or 27 <= bar < 29 or sec in ("who_hj",):
            for k in range(8):   # 反拍低音：落在八分反拍，和底鼓互补
                n = root + (12 if k % 4 == 3 else 0)
                bass.add(pluck_bass(n, 0.26, cutoff=900), t0 + k * BEAT / 2 + (BEAT / 4 if k % 2 == 0 else 0), 0.3)
        else:
            for k, iv in enumerate(pat16):
                acc = 1.0 if k % 4 == 0 else 0.7
                bass.add(pluck_bass(root + iv, 0.2, cutoff=1700 if sec in ("lessons", "ytd") else 1200),
                         t0 + k * BEAT / 4, 0.28 * acc)

    # ---------------- 反拍和弦「抽吸」
    for bar in range(66):
        sec = section(bar)
        on = (sec == "duel" and 15 <= bar < 25) or sec in ("ytd", "lessons", "compare") or (sec == "who_zj")
        if not on: continue
        _, notes = chord(bar)
        g = {"duel": 0.10, "ytd": 0.17, "lessons": 0.2, "compare": 0.14, "who_zj": 0.11}[sec]
        for k in range(4):
            keys.add(chord_stab([n + 12 for n in notes[:3]], 0.24, cutoff=4800 if sec == "lessons" else 3800),
                     b(bar) + k * BEAT + BEAT / 2, g)

    # ---------------- 鼓组
    for bar in range(66):
        sec = section(bar)
        t0 = b(bar)
        K, SN, CP, HAT = [], [], [], 0     # 底鼓拍位 / 军鼓 / 拍手 / 镲细分（0 无，8，16）
        if sec == "hook":
            if bar >= 1: K = [0, 1.5] if bar < 3 else [0, 1, 2, 2.5, 3, 3.5]
        elif sec == "title":
            K = [0, 1.5]; SN = [2]
        elif sec == "duel":
            if bar < 11: K = [0, 1, 2, 3]; HAT = 8
            elif bar < 15: K = [0, 1, 2, 3]; CP = [1, 3]; HAT = 8
            elif bar < 25: K = [0, 1, 2, 3]; SN = [1, 3]; HAT = 16
            elif 27 <= bar < 29: K = [0, 1.5]; SN = [2]; HAT = 8
            elif 30 <= bar < 34: K = [0, 1.5, 2.75]; SN = [2]
        elif sec == "ytd":
            K = [0, 1, 2, 3]; SN = [1, 3]; HAT = 16
        elif sec in ("who_hj", "who_zj"):
            K = [0, 1, 2, 3]; CP = [1, 3]; HAT = 8 if sec == "who_hj" else 16
        elif sec == "compare":
            K = [0, 1, 2, 3] if bar == 49 else [0, 0.5, 1, 1.5, 2, 2.5]; HAT = 16
        elif sec == "lessons":
            K = [0, 1, 2, 3]; SN = [1, 3]; HAT = 16
        for bt in K:
            tt = t0 + bt * BEAT
            if sec == "hook":
                drums.add(thump(0.45, 95, 42), tt, 0.6)
            else:
                drums.add(kick(0.55, 165, 45, 0.28), tt, 0.62)
                kicks.append(tt)
        for bt in SN:
            drums.add(snare(), t0 + bt * BEAT, 0.34 if sec in ("lessons", "ytd") else 0.28)
            drums.add(clap(), t0 + bt * BEAT, 0.12)
        for bt in CP:
            drums.add(clap(), t0 + bt * BEAT, 0.2)
        if HAT:
            step = BEAT / (HAT / 4)
            for k in range(HAT):
                v = 1.0 if (k % 2 == 1 if HAT == 8 else k % 4 == 2) else 0.45
                drums.add(tick_hat(0.08, v), t0 + k * step, 0.065)
        # 四小节一次太鼓过门
        if sec in ("duel", "ytd", "lessons", "who_hj", "who_zj") and bar % 4 == 2 and not (24 <= bar < 36) and bar != 60:
            for k, bt in enumerate([3.0, 3.25, 3.5, 3.75]):
                drums.add(taiko(), t0 + bt * BEAT, 0.22 + 0.08 * k)
        if 30 <= bar < 34:
            drums.add(taiko(1.8), t0 + 2 * BEAT, 0.45)

    # ---------------- 蓄力：滚奏 + 上扬和声
    builds = [(3, 5, (45, 52, 57, 64)), (29, 30, (45, 52, 57, 61)), (49, 51, (45, 52, 57, 64)), (60, 61, (47, 54, 59, 66))]
    for s0, s1, nts in builds:
        d = b(s1) - b(s0)
        drums.add(snare_roll(d, 3 if d > 2.5 else 6, 22, 0.15, 0.85), b(s0), 0.42)
        fx.add(riser(d, notes=nts, oct_up=12 if d > 2.5 else 7), b(s0), 0.55)
    fx.add(riser(BAR * 2, notes=(46, 53, 58, 65)), b(25), 0.3)                    # 今年以来
    for k in range(8):
        fx.add(thump(0.45, 90, 40), b(29) + k * BEAT / 2, 0.25 + 0.06 * k)        # 心跳加速
    for k in range(4):
        fx.add(thump(0.5, 85, 40), b(34) + k * BEAT * 2, 0.35)                    # 断崖后的心跳

    # ---------------- 琶音（时钟感）
    for bar in list(range(15, 25)) + list(range(40, 49)) + list(range(51, 61)):
        _, notes = chord(bar)
        for k in range(16):
            n = notes[k % len(notes)] + 12 + (12 if k % 8 >= 4 else 0)
            keys.add(mallet(n, 0.4, 1.0 if k % 4 == 0 else 0.6), b(bar) + k * BEAT / 4, 0.065)
    for bar in list(range(15, 25)) + list(range(36, 40)) + list(range(51, 61)):
        _, notes = chord(bar)
        seq = [notes[0] + 24, notes[2] + 12, notes[1] + 24, notes[3] + 12]
        for k in range(8):
            keys.add(pluck_lead(seq[k % 4], 0.22), b(bar) + k * BEAT / 2, 0.07 if bar < 51 else 0.09)

    # ---------------- 主题动机串起全片：钢琴 → 主旋律 → 八度主旋律
    motif(keys, MOTIF_A, 1, "piano", 0.24); motif(keys, MOTIF_B, 3, "piano", 0.28)
    motif(keys, MOTIF_A, 25, "piano", 0.26)
    motif(lead, MOTIF_A, 36, "saw", 0.14); motif(lead, MOTIF_B, 38, "saw", 0.15)
    motif(keys, MOTIF_A, 41, "piano", 0.16); motif(keys, MOTIF_C, 47, "piano", 0.16)
    for bar, m in ((53, MOTIF_A), (55, MOTIF_B), (57, MOTIF_A), (59, MOTIF_C)):
        motif(lead, m, bar, "saw", 0.16)
        motif(lead, m, bar, "saw", 0.07, oct=12)
    motif(keys, MOTIF_A, 62, "piano", 0.26)

    # ---------------- 对决段：每季重音强度由「这一季变化有多大」决定
    st = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "stats.json"), encoding="utf-8"))
    A_, B_ = st["duo"]["huijin_am"], st["duo"]["csf"]
    hit_times = {round(h[0], 3) for h in HITS}
    data_hits = []
    for i, s, d, note in QSCHED:
        tt = b(s)
        m = 0 if i == 0 else max(abs(A_[i] - A_[i - 1]), abs(B_[i] - B_[i - 1]))
        sev = min(m / 40.0, 1.0)
        root, notes = chord(s)
        keys.add(bell(notes[(i * 2) % len(notes)] + 12, 1.8), tt, 0.10 * (1 - 0.5 * sev))
        if round(tt, 3) in hit_times:
            continue
        hits.add(thump(0.35, 120, 50), tt, 0.35 + 0.6 * sev)
        if m >= 5:
            hits.add(taiko(1.4), tt, 0.3 + 0.5 * sev)
            for n in notes[:3]:
                lead.add(supersaw(n - 12, 0.9, att=0.005, rel=0.5, cutoff=1400 + 2000 * sev), tt, 0.10 + 0.12 * sev)
        if m >= 12:
            hits.add(boom(3.0), tt, 0.45 + 0.4 * sev)
            hits.add(subdrop(1.8, 80, 26), tt, 0.4 + 0.4 * sev)
            data_hits.append(tt)

    # ---------------- 重拍：预告片式重击（boom + 太鼓 + 底鼓 + 和弦重音）
    for tt, strength, kind in HITS:
        bar = int(round(tt / BAR))
        _, notes = chord(min(bar, 65))
        if kind in ("boom", "drop"):
            hits.add(boom(4.0), tt, 0.95 * strength)
            hits.add(taiko(1.6), tt, 0.6 * strength)
            hits.add(kick(0.6, 175, 38, 0.4), tt, 0.8 * strength)
            for n in notes[:3]:
                lead.add(supersaw(n, 1.6, att=0.004, rel=1.0, cutoff=3800), tt, 0.12 * strength)
                lead.add(supersaw(n - 12, 1.6, att=0.004, rel=1.0, cutoff=2000), tt, 0.10 * strength)
        if kind == "drop":
            hits.add(subdrop(3.0, 92, 22), tt, 1.0)
        if kind == "pulse":
            hits.add(thump(0.6, 110, 40), tt, 0.9 * strength + 0.3)
            hits.add(subdrop(1.2, 70, 30), tt, 0.45 * strength)
            hits.add(taiko(1.4), tt, 0.4 * strength)

    # ---------------- 混音
    n = len(pads.x)
    sc = sidechain(kicks, n, depth=0.55, rel=0.16)[:, None]
    P = reverb(pads.x * sc, 3.0, 0.3)
    Bs = reverb(bass.x * (0.5 + 0.5 * sc), 1.2, 0.1, lpf=2200, seed=11)
    D = reverb(drums.x, 1.3, 0.12, lpf=6500, seed=5)
    F = reverb(fx.x, 3.5, 0.28, lpf=1800, seed=9)
    K = reverb(keys.x * (0.6 + 0.4 * sc), 2.8, 0.32, lpf=6500, seed=13)
    Ld = reverb(lead.x * (0.75 + 0.25 * sc), 2.6, 0.28, lpf=7000, seed=17)
    Hh = reverb(hits.x, 3.0, 0.22, lpf=1600, seed=19)
    mix = P * 1.45 + Bs * 0.42 + D * 0.95 + F * 0.8 + K * 1.4 + Ld * 1.4
    duck = np.ones(n)
    for ht, st_, kd in HITS + [(x, 0.8, "data") for x in data_hits]:
        if st_ < 0.8: continue
        i1 = int(ht * SR); i0 = max(i1 - int(0.22 * SR), 0)
        duck[i0:i1] = np.minimum(duck[i0:i1], np.linspace(1.0, 0.1, i1 - i0) ** 1.5)
    mix = mix * duck[:, None] + Hh
    mix = hp(mix, 24, 2)
    mix = mix - 0.3 * lp(mix, 90, 2)          # 低频搁架约 −3dB：手机外放时中频更突出
    tt = np.arange(n) / SR
    mix *= np.clip(tt / 0.3, 0, 1)[:, None]
    fade0 = DURATION - 2.5
    mix *= np.clip(1 - (tt - fade0) / 2.5, 0, 1)[:, None] ** 1.5
    mix = mix[:int(DURATION * SR)]
    rms = np.sqrt((mix ** 2).mean())
    mix *= 0.18 / rms
    mix = np.tanh(mix * 1.2) / 1.2
    mix *= 0.93 / np.abs(mix).max()
    sf.write(out, mix.astype(np.float32), SR, subtype="PCM_24")
    print("score ->", out, f"{len(mix) / SR:.2f}s rms={np.sqrt((mix ** 2).mean()):.3f}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "work", "score.wav"))
