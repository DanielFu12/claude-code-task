"""按 timeline 合成全片原创配乐（D 小调，120 BPM），输出 work/score.wav。

情绪线（与画面一一对应）：
  钩子：钢琴动机 + 心跳，倒数式渐强          → 标题：重拍爆开
  对决：底鼓四拍 + 十六分低音，逐段加入拍手、琶音、高弦 → 今年以来：鼓点抽空，钢琴动机回归
  一季度：半速紧张律动 → 二季度前：心跳 + 上扬 → 断崖：Sub Drop + 低频冲击 + 重型半速
  今年总结：主旋律第一次完整出现（情绪抬升）→ 科普：轻律动保持注意力 → 鼓滚 + 上扬蓄力
  全景：全曲高潮（满编鼓组 + 和弦 + 主旋律）→ 启示：钢琴 + 弦乐 → 片尾：D 大三和弦落定
所有转场冲击都是低频（boom / sub drop / 脉冲），不使用高频 Whoosh 与白噪声。
"""
import os, sys
import numpy as np
import soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from synth import SR, Bus, mallet, pad, sub, pluck_bass, kick, thump, boom, subdrop, bell, piano, taiko, \
    clap, supersaw, riser, tom_roll, tick_hat, pluck_lead, reverb, sidechain, lp, hp
from timeline import BAR, BEAT, DURATION, HITS, QSCHED, b, section

CH = {  # 和弦：(低音根音 midi, 铺底音符)
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
setp(7, ["Dm", "Bb", "F", "C"] * 5)              # 7..26（23 起与 25、26 下面覆盖）
setp(23, ["Gm", "A"])                              # 2025Q3 起名单开始明显下滑：和声转暗
setp(25, ["Bb", "A"])
setp(27, ["Dm", "Bb", "A"])
setp(30, ["Dm", "Bb", "Gm", "A"])
setp(34, ["Bb", "A"])
setp(36, ["F", "C", "Dm", "Bb"])
setp(40, ["Dm", "Bb", "F", "C"] * 3)
setp(52, ["Gm", "A", "Bb", "C", "A"])
setp(57, ["Dm", "Bb", "F", "C", "Dm", "Bb", "F", "C", "Gm", "Bb", "A"])
setp(68, ["Bb", "F", "C", "Dm", "Bb", "F", "Gm", "A", "Bb", "A"])
setp(78, ["Bb", "F", "Dsus", "D", "D"])

# 主题动机（2 小节 = 8 拍）：(拍, 音, 时值拍)
MOTIF_A = [(0, 69, 1), (1, 74, 1), (2, 77, 1.5), (3.5, 76, 0.5), (4, 74, 1), (5, 72, 1), (6, 69, 2)]
MOTIF_B = [(0, 69, 1), (1, 74, 1), (2, 77, 1), (3, 79, 1), (4, 81, 1.5), (5.5, 79, 0.5), (6, 77, 2)]
MOTIF_C = [(0, 81, 1), (1, 79, 1), (2, 77, 1), (3, 76, 1), (4, 74, 2), (6, 74, 2)]


def energy(bar):
    """0..1 能量曲线，决定鼓组编制"""
    sec = section(bar)
    return {"hook": 0.15, "title": 0.6, "duel": 0.55 if bar < 15 else (0.75 if bar < 25 else 0.0),
            "ytd": 0.65, "huijin": 0.45, "zhengjin": 0.5, "compare": 0.3, "rules": 0.35, "trend": 1.0,
            "lessons": 0.3, "end": 0.0}[sec]


def main(out):
    N = DURATION + 4.0
    pads, bass, drums, fx, lead, keys, hits = Bus(N), Bus(N), Bus(N), Bus(N), Bus(N), Bus(N), Bus(N)
    kicks = []

    def play_motif(bus, motif, bar, inst="piano", gain=0.25, oct=0):
        for bt, n, d in motif:
            tt = b(bar) + bt * BEAT
            if inst == "piano":
                bus.add(piano(n + oct, 2.8 + d * BEAT), tt, gain)
                bus.add(piano(n + oct - 12, 2.8, 0.55), tt, gain * 0.45)
            else:
                bus.add(supersaw(n + oct, d * BEAT + 0.15, cutoff=3600), tt, gain)
                bus.add(supersaw(n + oct - 12, d * BEAT + 0.15, cutoff=2200, seed=3), tt, gain * 0.5)

    # ---------------- 铺底 + Sub
    for bar in range(83):
        sec = section(bar)
        root, notes = CH[PROG[bar]]
        t0 = b(bar)
        in_ytd_break = 25 <= bar < 27
        pre = bar == 29
        gain = {"hook": 0.3 + 0.08 * bar, "title": 0.85, "duel": 0.55 if bar < 25 else 0.6, "ytd": 0.85,
                "huijin": 0.55, "zhengjin": 0.55, "compare": 0.6, "rules": 0.65, "trend": 1.0, "lessons": 0.6,
                "end": 0.9}[sec]
        if in_ytd_break: gain = 0.5
        if pre: gain = 0.25
        if 30 <= bar < 34: gain = 0.8
        bright = {"hook": 4.0, "trend": 11.0, "end": 9.0, "ytd": 9.0, "lessons": 6.5}.get(sec, 7.0)
        if 30 <= bar < 36: bright = 4.0
        dur = BAR + (6.0 if bar == 82 else 0.8)
        pads.add(pad(notes, dur, bright=bright, att=0.25 if sec != "hook" else 1.0, rel=0.8 if bar < 82 else 4.5,
                     seed=bar), t0 - 0.03, gain)
        if sec in ("trend", "end", "ytd") or (sec == "duel" and 15 <= bar < 25):
            top = [n + 12 for n in notes[1:]]
            pads.add(pad(top, dur, bright=3.5, att=0.4, rel=0.9, seed=bar + 100), t0,
                     0.34 if sec in ("trend", "end", "ytd") else 0.2)
        if not pre:
            sg = {"hook": 0.4, "lessons": 0.3, "end": 0.5}.get(sec, 0.5)
            if in_ytd_break: sg = 0.3
            bass.add(sub(root - 12 if root > 40 else root, BAR + 0.25, att=0.05, rel=0.3), t0, sg)

    # ---------------- 低音固定音型
    pat8 = [0, 0, 12, 0, 7, 0, 12, 10]
    pat16 = [0, 0, 12, 0, 0, 7, 0, 12, 0, 0, 12, 0, 10, 7, 12, 0]
    for bar in range(83):
        sec = section(bar)
        root = CH[PROG[bar]][0]
        t0 = b(bar)
        if sec in ("hook", "compare", "lessons", "end") or 25 <= bar < 27 or bar == 29 or 34 <= bar < 36:
            continue
        if sec in ("title",) or (sec == "duel" and bar < 11) or sec in ("huijin", "zhengjin", "rules") or 27 <= bar < 34:
            for k, iv in enumerate(pat8):
                bass.add(pluck_bass(root + iv, 0.3, cutoff=800), t0 + k * BEAT / 2, 0.28)
        else:
            for k, iv in enumerate(pat16):
                acc = 1.0 if k % 4 == 0 else 0.7
                bass.add(pluck_bass(root + iv, 0.2, cutoff=1500 if sec == "trend" else 1100), t0 + k * BEAT / 4,
                         0.28 * acc)

    # ---------------- 鼓组
    for bar in range(83):
        sec = section(bar)
        t0 = b(bar)
        hk = []   # kick 拍位
        cp = []   # clap 拍位
        if sec == "hook":
            if bar >= 1:
                hk = [0, 1.5] if bar < 3 else [0, 1, 2, 2.5, 3, 3.5]
        elif sec == "title":
            hk = [0, 2]; cp = [1, 3] if bar == 6 else []
        elif sec == "duel":
            if bar < 15: hk = [0, 1, 2, 3]
            elif bar < 25: hk = [0, 1, 2, 3]; cp = [1, 3]
            elif 27 <= bar < 29: hk = [0, 2.5]; cp = [2]
            elif 30 <= bar < 34: hk = [0, 2.5]; cp = [2] if bar > 30 else []
        elif sec == "ytd":
            hk = [0, 1, 2, 3]; cp = [1, 3]
        elif sec in ("huijin", "zhengjin"):
            hk = [0, 2]; cp = [1, 3]
        elif sec == "rules":
            hk = [0, 1, 2, 3]
        elif sec == "trend":
            hk = [0, 1, 2, 3]; cp = [1, 3]
        elif sec == "lessons" and 70 <= bar < 76:
            hk = [0, 2]
        for bt in hk:
            tt = t0 + bt * BEAT
            if sec == "hook":
                drums.add(thump(0.45, 95, 42), tt, 0.6)
            else:
                drums.add(kick(0.55, 160, 46, 0.28), tt, 0.6 if sec != "lessons" else 0.4)
                kicks.append(tt)
        for bt in cp:
            drums.add(clap(), t0 + bt * BEAT, 0.20 if sec != "trend" else 0.26)
        # 段落尾过门：太鼓三连
        if (sec in ("duel", "trend") and bar % 4 == 2 and bar not in (24, 26, 28, 29, 33)) or bar in (39,):
            for k, bt in enumerate([3.0, 3.25, 3.5, 3.75]):
                drums.add(taiko(), t0 + bt * BEAT, 0.22 + 0.08 * k)
        if 30 <= bar < 34:
            drums.add(taiko(1.8), t0 + 2 * BEAT, 0.45)

    # ---------------- 琶音「时钟」（对决后半、科普、高潮）
    for bar in list(range(15, 25)) + list(range(40, 52)) + list(range(57, 68)):
        root, notes = CH[PROG[bar]]
        for k in range(16):
            n = notes[k % len(notes)] + 12 + (12 if k % 8 >= 4 else 0)
            v = (1.0 if k % 4 == 0 else 0.6) * (0.7 if bar < 57 else 1.0)
            keys.add(mallet(n, 0.4, v), b(bar) + k * BEAT / 4, 0.075)

    # ---------------- 推进层：音调化镲（八分 / 十六分）+ 明亮拨弦琶音
    for bar in range(83):
        sec = section(bar)
        drive = (sec == "duel" and 11 <= bar < 25) or sec in ("ytd", "trend") or (sec in ("huijin", "zhengjin") and bar % 2 == 1)
        if not drive: continue
        sub16 = sec == "trend" or (sec == "duel" and bar >= 15)
        for k in range(16 if sub16 else 8):
            step = BEAT / 4 if sub16 else BEAT / 2
            v = 1.0 if (k % 2 == 1 if not sub16 else k % 4 == 2) else 0.45
            drums.add(tick_hat(0.08, v), b(bar) + k * step, 0.06)
    for bar in list(range(15, 25)) + list(range(36, 40)) + list(range(57, 68)):
        root, notes = CH[PROG[bar]]
        seq = [notes[0] + 24, notes[2] + 12, notes[1] + 24, notes[3] + 12]
        for k in range(8):
            keys.add(pluck_lead(seq[k % 4], 0.22), b(bar) + k * BEAT / 2, 0.07 if bar < 57 else 0.09)

    # ---------------- 主题动机：钢琴 → 主旋律
    for bar in (1, 3):
        play_motif(keys, MOTIF_A if bar == 1 else MOTIF_B, bar, "piano", 0.24 + 0.04 * (bar == 3))
    play_motif(keys, MOTIF_A, 25, "piano", 0.26)
    play_motif(lead, MOTIF_A, 36, "saw", 0.12)
    play_motif(lead, MOTIF_B, 38, "saw", 0.13)
    for bar, m in ((59, MOTIF_A), (61, MOTIF_B), (63, MOTIF_A), (65, MOTIF_C)):
        play_motif(lead, m, bar, "saw", 0.15, oct=0)
        play_motif(lead, m, bar, "saw", 0.06, oct=12)
    for bar, m in ((70, MOTIF_A), (72, MOTIF_B), (74, MOTIF_A), (76, MOTIF_C)):
        play_motif(keys, m, bar, "piano", 0.24)
    play_motif(keys, MOTIF_A, 79, "piano", 0.26)

    # ---------------- 季度切换：重音强度由「这一季变化有多大」决定
    #   持平 → 只有轻钟音；小变化 → 低频脉冲；中变化（≥5）→ 太鼓 + 低音和弦重击；
    #   大变化（≥12）→ 低频冲击 + Sub Drop + 下行和弦，并在重拍前「吸气」
    import json
    st = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "stats.json"), encoding="utf-8"))
    A_, B_ = st["duo"]["huijin_am"], st["duo"]["csf"]
    hit_times = {round(h[0], 3) for h in HITS}
    data_hits = []
    for i, s, d, note in QSCHED:
        tt = b(s)
        m = 0 if i == 0 else max(abs(A_[i] - A_[i - 1]), abs(B_[i] - B_[i - 1]))
        sev = min(m / 40.0, 1.0)
        root, notes = CH[PROG[s]]
        keys.add(bell(notes[(i * 2) % len(notes)] + 12, 1.8), tt, 0.10 * (1 - 0.5 * sev))
        if round(tt, 3) in hit_times:
            continue
        hits.add(thump(0.35, 120, 50), tt, 0.35 + 0.6 * sev)
        if m >= 5:
            hits.add(taiko(1.4), tt, 0.3 + 0.5 * sev)
            stab = [n - 12 for n in notes[:3]]
            for n in stab:
                lead.add(supersaw(n, 0.9, att=0.005, rel=0.5, cutoff=1400 + 2000 * sev, voices=5), tt, 0.10 + 0.12 * sev)
        if m >= 12:
            hits.add(boom(3.0), tt, 0.45 + 0.4 * sev)
            hits.add(subdrop(1.8, 80, 26), tt, 0.4 + 0.4 * sev)
            data_hits.append(tt)

    # ---------------- 蓄力：上扬和声 + 鼓滚
    fx.add(riser(b(5) - b(3), notes=(45, 52, 57, 64)), b(3), 0.55)               # 钩子 → 标题
    fx.add(riser(BAR * 2, notes=(46, 53, 58, 65)), b(25), 0.35)                  # 今年以来
    fx.add(riser(BAR, notes=(45, 52, 57, 61), oct_up=7), b(29), 0.6)             # 二季度前
    for k in range(8):
        fx.add(thump(0.45, 90, 40), b(29) + k * BEAT / 2, 0.25 + 0.06 * k)       # 心跳加速
    fx.add(riser(b(57) - b(54), notes=(43, 50, 55, 62)), b(54), 0.5)             # 怎么看 → 全景
    drums.add(tom_roll(BAR * 2, 4, 18), b(55), 0.55)
    fx.add(riser(BAR * 2, notes=(46, 53, 58, 65)), b(76), 0.4)                   # 启示 → 片尾

    # ---------------- 重拍 / Sub Drop
    for tt, strength, kind in HITS:
        if kind in ("boom", "drop"):
            hits.add(boom(4.0), tt, 0.9 * strength)
            hits.add(taiko(1.6), tt, 0.55 * strength)
            hits.add(kick(0.6, 170, 40, 0.35), tt, 0.7 * strength)
        if kind == "drop":
            hits.add(subdrop(3.0, 92, 22), tt, 1.0)
        if kind == "pulse":
            hits.add(thump(0.6, 110, 40), tt, 0.9 * strength + 0.3)
            hits.add(subdrop(1.2, 70, 30), tt, 0.45 * strength)
            hits.add(taiko(1.4), tt, 0.35 * strength)

    # ---------------- 混音
    n = len(pads.x)
    sc = sidechain(kicks, n, depth=0.45, rel=0.18)[:, None]
    P = reverb(pads.x * sc, 3.0, 0.32)
    Bs = reverb(bass.x * (0.55 + 0.45 * sc), 1.2, 0.1, lpf=2000, seed=11)
    D = reverb(drums.x, 1.4, 0.12, lpf=3000, seed=5)
    F = reverb(fx.x, 3.5, 0.28, lpf=1800, seed=9)
    K = reverb(keys.x, 3.2, 0.38, lpf=5000, seed=13)
    Ld = reverb(lead.x * (0.7 + 0.3 * sc), 2.8, 0.3, lpf=6000, seed=17)
    Hh = reverb(hits.x, 3.0, 0.22, lpf=1600, seed=19)
    mix = P * 1.5 + Bs * 0.42 + D * 0.8 + F * 0.8 + K * 1.45 + Ld * 1.35
    # 大重拍前「吸一口气」：0.2 秒内压低全部乐器，重拍本身不受影响
    duck = np.ones(n)
    for ht, st_, kd in HITS + [(x, 0.8, "data") for x in data_hits]:
        if st_ < 0.8: continue
        i1 = int(ht * SR); i0 = max(i1 - int(0.22 * SR), 0)
        duck[i0:i1] = np.minimum(duck[i0:i1], np.linspace(1.0, 0.12, i1 - i0) ** 1.5)
    mix = mix * duck[:, None] + Hh * 1.0
    mix = hp(mix, 24, 2)
    mix = mix - 0.3 * lp(mix, 90, 2)          # 低频搁架约 −3dB：手机外放时中频更突出
    tt = np.arange(n) / SR
    mix *= np.clip(tt / 0.3, 0, 1)[:, None]
    fade0 = DURATION - 2.5
    mix *= np.clip(1 - (tt - fade0) / 2.5, 0, 1)[:, None] ** 1.5
    mix = mix[:int(DURATION * SR)]
    rms = np.sqrt((mix ** 2).mean())
    mix *= 0.17 / rms
    mix = np.tanh(mix * 1.15) / 1.15
    mix *= 0.93 / np.abs(mix).max()
    sf.write(out, mix.astype(np.float32), SR, subtype="PCM_24")
    print("score ->", out, f"{len(mix) / SR:.2f}s rms={np.sqrt((mix ** 2).mean()):.3f}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "work", "score.wav"))
