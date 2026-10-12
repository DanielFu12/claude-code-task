"""原创配乐 + 音效（numpy 合成）。120 BPM，D 小调 → 结尾转 D 大调。

段落与画面一一对应（见 timeline.py）：
  钩子：时钟滴答 + 低频脉冲，「可是」处抽空后重击 → 标题重拍
  01 反常：拨弦琶音律动，逐层加入贝斯、拍手、踩镲；悖论处抽掉鼓
  02 地基：诺奖重拍（明亮大三和弦 + 铃）→ 旧模型「数据点」下行音 → 晶体碎裂 → 重建
  03 霍尔：温暖的 felt piano 主题 + 弦乐
  04 伍德福德：钟表式拨奏 ostinato，央行旋钮、德拉吉一句话
  05 传导：全编制高潮 → 恶性循环转暗 → 推绳子 → 财政重建
  06 真相：钢琴 + 弦乐，关键句转 D 大调
  获奖者：庄重的赞美诗和声 + 定音鼓
  片尾：汇聚 riser → logo 重拍 → 品牌字重拍 + 流光铃音 → 淡出

用法：python3 music.py BUILD_DIR   → music.wav（48 kHz 立体声）+ music_meta.json（逐帧节拍/能量，供画面同步）
"""
import json
import math
import os
import sys

import numpy as np
import soundfile as sf

from synth import *          # noqa: F401,F403
from timeline import BAR, BEAT, DUR, FPS, b, HITS

N = S(DUR)

# ---------------------------------------------------------------- 和弦
CH = {
    'Dm': ([50, 53, 57, 62], 38), 'Bb': ([50, 53, 58, 62], 34), 'F': ([48, 53, 57, 60], 41),
    'C': ([48, 52, 55, 60], 36), 'Gm': ([50, 55, 58, 62], 43), 'A': ([49, 52, 57, 61], 45),
    'Asus': ([50, 52, 57, 62], 45), 'C/E': ([48, 52, 55, 60], 40), 'F/A': ([48, 53, 57, 60], 45),
    'Eb': ([51, 55, 58, 63], 39), 'D': ([50, 54, 57, 62], 38), 'Bm': ([50, 54, 59, 62], 35),
    'G': ([50, 55, 59, 62], 43), 'A/C#': ([49, 52, 57, 61], 37), 'D/F#': ([50, 54, 57, 62], 42),
    'Em7': ([50, 55, 59, 64], 40), 'Bbadd9': ([50, 53, 58, 60], 34), 'Gm7': ([50, 53, 55, 58], 43),
    'Dadd9': ([50, 54, 57, 64], 38), 'Dpow': ([38, 45, 50], 38),
}
PROG = [  # (起始小节, 和弦)
    (0, 'Dpow'), (2, 'Dm'), (3, 'Bb'), (4, 'Gm'), (5, 'A'),
    (6, 'Bbadd9'), (7, 'F/A'), (8, 'Gm7'), (9, 'Asus'), (9.5, 'A'),
] + [(10 + i, c) for i, c in enumerate(['Dm', 'Bb', 'F', 'C'] * 3)] + [
    (22, 'Gm'), (23, 'A'), (24, 'Bb'), (25, 'F'), (26, 'C'), (27, 'Dm'), (28, 'Gm'), (29, 'A'),
    (30, 'F'), (31, 'C/E'), (32, 'Dm'), (34, 'Bb'), (35, 'C'),
    (36, 'F'), (37, 'C/E'), (38, 'Dm'), (39, 'Bb'), (40, 'F'), (41, 'C/E'), (42, 'Dm'), (43, 'Bb'),
    (44, 'Gm'), (45, 'Bb'), (46, 'C'),
    (47, 'Gm'), (48, 'Bb'), (49, 'Dm'), (50, 'A'), (51, 'Gm'), (52, 'Bb'), (53, 'F'), (54, 'C'),
    (55, 'Dm'), (56, 'Bb'), (57, 'A'),
    (58, 'Dm'), (59, 'Bb'), (60, 'F'), (61, 'C'), (62, 'Dm'), (63, 'Bb'), (64, 'F'),
    (64.5, 'Gm'), (65.5, 'Eb'), (66, 'A'),
    (67, 'Dm'), (68, 'Bb'), (69, 'Gm'), (70, 'A'),
    (71, 'Bb'), (72, 'C'), (73, 'Dm'), (74, 'F'), (75, 'Gm'), (75.5, 'A'),
    (76, 'Bb'), (77, 'F/A'), (78, 'Gm'), (79, 'D'), (80, 'Bm'), (81, 'Asus'), (81.5, 'A'),
    (82, 'D'), (83, 'A/C#'), (84, 'Bm'), (85, 'G'), (86, 'D/F#'), (87, 'Em7'), (88, 'Asus'), (88.5, 'A'),
    (89, 'G'), (89.5, 'A'), (90, 'Dadd9'), (94, None),
]


def chord_at(bar):
    c = PROG[0][1]
    for s, n in PROG:
        if s <= bar:
            c = n
    return c


def segments():
    for (s0, c), (s1, _) in zip(PROG, PROG[1:]):
        if c is not None:
            yield s0, s1, c


def ramp(x, a, z, v0, v1):
    return v0 + (v1 - v0) * min(max((x - a) / max(z - a, 1e-9), 0.0), 1.0)


# ---------------------------------------------------------------- 总线
class Bus:
    def __init__(self):
        self.y = np.zeros((N, 2))

    def add(self, x, t, gain=1.0, p=0.0):
        if x.ndim == 1:
            x = pan(x, p)
        i = S(t)
        if i >= N:
            return
        if i < 0:
            x = x[-i:]
            i = 0
        j = min(N, i + len(x))
        self.y[i:j] += x[:j - i] * gain


drums, bass, music, keys, fx, sub = Bus(), Bus(), Bus(), Bus(), Bus(), Bus()
KICKS = []          # 侧链用底鼓时间
PULSE = []          # 画面脉冲（时间, 强度）


def K(t, power=1.0, **kw):
    drums.add(kick(power, **kw), t, 0.9)
    KICKS.append((t, power))
    PULSE.append((t, power))


# ---------------------------------------------------------------- 编曲
def pads():
    for s0, s1, c in segments():
        t0, t1 = b(s0), b(s1)
        mid = (s0 + s1) / 2
        notes, root = CH[c]
        if s0 < 2:
            cut, g = ramp(mid, 0, 2, 380, 700), 0.55
        elif s0 < 6:
            cut, g = ramp(mid, 2, 6, 700, 1300), 0.6
        elif s0 < 10:
            cut, g = 2300, 0.85
        elif s0 < 22:
            cut, g = ramp(mid, 10, 22, 1100, 2600), 0.55
        elif s0 < 24:
            cut, g = 1100, 0.62
        elif s0 < 28:
            cut, g = 1700, 0.5
        elif s0 < 30:
            cut, g = ramp(mid, 28, 30, 1500, 3000), 0.65
        elif s0 < 32:
            cut, g = 3300, 0.85
        elif s0 < 36:
            cut, g = 1000, 0.45
        elif s0 < 47:
            cut, g = ramp(mid, 36, 47, 1500, 2400), 0.5
        elif s0 < 58:
            cut, g = ramp(mid, 47, 58, 1300, 2600), 0.5
        elif s0 < 64.5:
            cut, g = 3600, 0.8
        elif s0 < 67:
            cut, g = 750, 0.75
        elif s0 < 71:
            cut, g = 900, 0.42
        elif s0 < 76:
            cut, g = ramp(mid, 71, 76, 1200, 3300), 0.65
        elif s0 < 82:
            cut, g = 2000, 0.5
        elif s0 < 89:
            cut, g = 2600, 0.75
        else:
            cut, g = 3200, 0.8
        dur = t1 - t0
        if s0 >= 90:
            dur = b(93.6) - t0
        x = pad_chord(notes, dur + 0.05, cut=cut * 1.35, att=0.25 if s0 >= 10 else 0.8, rel=0.9)
        music.add(x, t0 - 0.05, g * 0.5)


def strings_parts():
    secs = [(6, 10, 0.9), (38, 47, 0.55), (58, 64.5, 0.6), (71, 76, 0.7), (76, 82, 0.75), (82, 89, 0.9), (90, 94, 0.9)]
    for s0, s1, c in segments():
        for a, z, g in secs:
            if a <= s0 < z:
                notes, root = CH[c]
                hi = [m + 12 for m in notes[1:]]
                dur = b(min(s1, z)) - b(s0)
                if s0 >= 90:
                    dur = b(93.6) - b(s0)
                music.add(strings(hi, dur, att=0.4, rel=1.1, cut=4300 if s0 < 82 else 5000), b(s0), g * 0.55)


def arps():
    """拨弦琶音：01 反常（16 分）、分化（8 分）、传导高潮（16 分）、财政重建（8 分）"""
    pat16 = [0, 1, 2, 3, 2, 1, 2, 3]
    for s0, s1, c in segments():
        notes, root = CH[c]
        arp = [m + 12 for m in notes]
        for bar in np.arange(s0, s1, 1.0 if s1 - s0 >= 1 else 0.5):
            span = min(1.0, s1 - bar)
            if 10 <= bar < 22:
                step, cut = 0.25, ramp(bar, 10, 22, 1400, 4200)
                g = ramp(bar, 10, 14, 0.5, 0.75)
            elif 22 <= bar < 24:
                step, cut, g = 0.5, 1600, 0.62
            elif 24 <= bar < 28:
                step, cut, g = 0.5, 2800, 0.6
            elif 28 <= bar < 30:
                step, cut, g = 0.25, ramp(bar, 28, 30, 1800, 4200), 0.68
            elif 67 <= bar < 71:
                step, cut, g = 0.5, 1700, 0.45
            elif 58 <= bar < 64.5:
                step, cut, g = 0.25, 5200, 0.8
            elif 72 <= bar < 76:
                step, cut, g = 0.5 if bar < 74 else 0.25, ramp(bar, 72, 76, 1800, 4500), 0.7
            else:
                continue
            k = 0
            for beat in np.arange(0, span * 4, step):
                m = arp[pat16[k % 8]] + (12 if (k // 8) % 2 and step < 0.5 else 0)
                t = b(bar, beat)
                vel = 0.9 if beat % 1 == 0 else 0.65
                x = pluck(m, dur=step * BEAT * 0.9, cut0=cut, cut1=cut * 0.18, decay=0.16)
                keys.add(x, t, g * vel * 0.32, p=0.35 * math.sin(k * 1.3))
                k += 1


def pizz_ostinato():
    """伍德福德：钟表式 16 分拨奏"""
    pat = [0, 2, 1, 2, 3, 2, 1, 2]
    for s0, s1, c in segments():
        if not (47 <= s0 < 56):
            continue
        notes, root = CH[c]
        for bar in np.arange(s0, s1, 1.0):
            for k in range(16):
                t = b(bar, k * 0.25)
                m = notes[pat[k % 8]] + 12
                vel = 0.85 if k % 4 == 0 else 0.55
                keys.add(pizz(m, vel), t, 0.30, p=0.5 * math.sin(k * 0.9 + bar))


def basslines():
    for s0, s1, c in segments():
        notes, root = CH[c]
        for bar in np.arange(s0, s1, 1.0):
            span = min(1.0, s1 - bar)
            if 14 <= bar < 22:
                for k in range(int(span * 8)):
                    m = root + (12 if k % 2 else 0)
                    bass.add(bass_note(m, BEAT * 0.45, cut=380 + ramp(bar, 14, 22, 0, 300)), b(bar, k * 0.5), 0.55 if k % 2 == 0 else 0.4)
            elif 24 <= bar < 28:
                for k in range(int(span * 4)):
                    bass.add(bass_note(root, BEAT * 0.9, cut=340), b(bar, k), 0.5)
            elif 40 <= bar < 47:
                bass.add(bass_note(root, BAR * span * 0.95, cut=300, drive=1.1), b(bar), 0.45)
            elif 47 <= bar < 56:
                for k in range(int(span * 8)):
                    bass.add(bass_note(root + (12 if k % 4 == 3 else 0), BEAT * 0.4, cut=420), b(bar, k * 0.5), 0.45)
            elif 58 <= bar < 64.5:
                for k in range(int(span * 8)):
                    m = root + (12 if k % 2 else 0)
                    bass.add(bass_note(m, BEAT * 0.45, cut=650, drive=2.0), b(bar, k * 0.5), 0.6 if k % 2 == 0 else 0.45)
            elif 64.5 <= bar < 67:
                sub.add(sub_note(root - 12, BAR * span), b(bar), 0.5)
            elif 67 <= bar < 71:
                for k in range(int(span * 4)):
                    bass.add(bass_note(root, BEAT * 0.8, cut=320, drive=1.2), b(bar, k), 0.4)
            elif 73 <= bar < 76:
                for k in range(int(span * 8)):
                    bass.add(bass_note(root + (12 if k % 2 else 0), BEAT * 0.45, cut=500), b(bar, k * 0.5), 0.5 if k % 2 == 0 else 0.38)
            elif 82 <= bar < 89:
                sub.add(sub_note(root - 12, BAR * span * 0.98), b(bar), 0.35)
                bass.add(bass_note(root, BAR * span * 0.9, cut=260, drive=1.0), b(bar), 0.35)
            elif 90 <= bar < 94:
                if bar == 90:
                    sub.add(sub_note(26, b(93.5) - b(90)), b(90), 0.45)


def drum_parts():
    # 01 反常律动
    for bar in range(10, 22):
        K(b(bar, 0), 0.75)
        K(b(bar, 2), 0.65)
        if bar >= 16:
            for k in range(4):
                drums.add(hat(0.6), b(bar, k + 0.5), 0.5, p=0.25)
        if bar >= 18:
            drums.add(clap(0.8), b(bar, 1), 0.55, p=0.05)
            drums.add(clap(0.8), b(bar, 3), 0.55, p=-0.05)
    for k, m in enumerate([50, 47, 45, 43]):
        drums.add(tom(m, 0.7), b(21, 3 + k * 0.25), 0.4, p=-0.4 + k * 0.25)
    # 分化：半速
    for bar in range(24, 28):
        K(b(bar, 0), 0.7)
        drums.add(snare(0.7), b(bar, 2), 0.42)
    # 原因 → 诺奖：渐强军鼓滚奏（柔）
    for k in range(32):
        t = b(28, k * 0.25 * 0.5 * 2) if False else b(29, k * 0.125)
        drums.add(snare(0.25 + 0.6 * (k / 32) ** 2, length=0.18, bright=0.3), t, 0.28)
    for k in range(4):
        K(b(29, k), 0.45 + 0.1 * k)
    # 霍尔：轻
    for bar in range(40, 46):
        K(b(bar, 0), 0.5)
        for k in range(8):
            drums.add(shaker(0.7 if k % 2 else 0.45), b(bar, k * 0.5), 0.45, p=0.3)
    for k in range(8):
        drums.add(tom(45 - k, 0.3 + 0.07 * k), b(46, 2 + k * 0.25), 0.3)
    # 伍德福德：滴答 + 工厂律动
    for bar in range(47, 56):
        for k in range(16):
            drums.add(tick(2900 if k % 4 else 2200, 0.45 if k % 4 else 0.7), b(bar, k * 0.25), 0.22, p=0.6 * math.sin(k))
    for bar in range(52, 56):
        K(b(bar, 0), 0.7)
        K(b(bar, 2), 0.6)
        drums.add(clap(0.7), b(bar, 1), 0.4)
        drums.add(clap(0.7), b(bar, 3), 0.4)
    for k in range(16):
        drums.add(snare(0.2 + 0.7 * (k / 16) ** 2, length=0.2, bright=0.3), b(57, k * 0.25), 0.3)
    # 传导高潮
    for bar in np.arange(58, 64.5, 1.0):
        for k in range(4):
            if bar + k / 4 >= 64.5:
                break
            K(b(bar, k), 0.85 if k % 2 == 0 else 0.7)
            drums.add(hat(0.5), b(bar, k + 0.5), 0.5, p=0.3)
            drums.add(hat(0.35), b(bar, k + 0.25), 0.35, p=-0.3)
            drums.add(hat(0.35), b(bar, k + 0.75), 0.35, p=-0.3)
        if bar + 0.5 < 64.5:
            drums.add(snare(0.9), b(bar, 1), 0.5)
        if bar + 0.75 < 64.5:
            drums.add(snare(0.9), b(bar, 3), 0.5)
    for k, m in enumerate([52, 50, 47, 45, 43, 40]):
        drums.add(tom(m, 0.8), b(61, 2.5 + k * 0.25), 0.45, p=-0.5 + k * 0.2)
    # 恶性循环：心跳
    for bar in np.arange(64.5, 67, 1.0):
        K(b(bar, 0), 0.6, f_hi=80, f_lo=38, length=0.5)
        K(b(bar, 0.6), 0.45, f_hi=80, f_lo=38, length=0.5)
    # 真实利率：时钟
    for bar in range(67, 71):
        for k in range(4):
            drums.add(tick(2400, 0.6), b(bar, k), 0.25, p=0.3 * (-1) ** k)
    # 财政重建
    for bar in range(73, 76):
        K(b(bar, 0), 0.7)
        K(b(bar, 2), 0.65)
        if bar >= 74:
            drums.add(clap(0.8), b(bar, 1), 0.45)
            drums.add(clap(0.8), b(bar, 3), 0.45)
            for k in range(4):
                drums.add(hat(0.5), b(bar, k + 0.5), 0.45)
    for k in range(8):
        drums.add(snare(0.3 + 0.08 * k, length=0.2, bright=0.3), b(75, 2 + k * 0.25), 0.3)
    # 获奖者：行进式低鼓
    for bar in range(82, 89):
        drums.add(tom(38, 0.55, 1.2), b(bar, 0), 0.4)
        drums.add(tom(38, 0.35, 1.0), b(bar, 2), 0.3)
        PULSE.append((b(bar, 0), 0.5))


def piano_parts():
    P = lambda m, t, v=0.6, d=1.5, g=0.5, br=0.55, p=0.0: keys.add(piano_note(m, v, d, br), t, g, p)
    # 钩子：开场的两个高音
    P(86, 0.02, 0.5, 2.5, 0.35, p=0.2)
    P(81, 2.0, 0.45, 2.0, 0.3, p=-0.2)
    P(26, 4.0, 0.9, 3.0, 0.5)          # 「可是」低音簇
    P(38, 4.0, 0.9, 3.0, 0.45)
    # 标题旋律
    mel = [(6, 0, 74, 1.5), (6, 1.5, 76, 0.5), (6, 2, 77, 2), (7, 0, 81, 3), (8, 0, 79, 2), (8, 2, 77, 2),
           (9, 0, 76, 3.5)]
    for bar, beat, m, d in mel:
        P(m, b(bar, beat), 0.62, d * BEAT, 0.45)
        P(m - 12, b(bar, beat), 0.4, d * BEAT, 0.18)
    # 旧模型：数据点逐个落下（下行）
    for k, m in enumerate([81, 79, 77, 76, 74, 72, 71, 69, 67]):
        P(m, 64.2 + k * 0.26, 0.5, 0.3, 0.3, p=-0.6 + k * 0.15)
    # 重建：上行
    for k, m in enumerate([62, 65, 69, 72, 74, 77, 81, 84]):
        P(m, 68.4 + k * 0.42, 0.5, 0.6, 0.3, p=0.6 - k * 0.15)
    # 霍尔主题（F 大调）
    hall = [  # (bar, beat, midi, beats)
        (36, 0, 72, 1), (36, 1, 77, 1), (36, 2, 79, 1), (36, 3, 81, 1),
        (37, 0, 79, 2), (37, 2, 76, 1), (37, 3, 72, 1),
        (38, 0, 74, 2), (38, 2, 77, 1), (38, 3, 81, 1),
        (39, 0, 77, 3), (39, 3, 74, 1),
        (40, 0, 81, 2), (40, 2, 79, 1), (40, 3, 77, 1),
        (41, 0, 76, 2), (41, 2, 79, 1), (41, 3, 84, 1),
        (42, 0, 81, 3), (42, 3, 77, 1),
        (43, 0, 77, 2), (43, 2, 74, 2),
        (44, 0, 74, 2), (44, 2, 79, 2), (45, 0, 77, 2), (45, 2, 74, 2), (46, 0, 76, 4),
    ]
    for bar, beat, m, d in hall:
        P(m, b(bar, beat), 0.58, d * BEAT * 0.95, 0.5, br=0.5)
    # 霍尔：左手分解和弦
    for s0, s1, c in segments():
        if 36 <= s0 < 47:
            notes, root = CH[c]
            seq = [root, notes[1], notes[2], notes[3], notes[2], notes[1], notes[2], notes[3]]
            for k in range(8):
                P(seq[k] + (12 if k else 0), b(s0, k * 0.5), 0.42, 0.45, 0.22, br=0.4, p=-0.3)
    # 德拉吉：一记和弦，随后舒展
    for m in (50, 57, 62, 65):
        P(m, b(56), 0.7, 2.0, 0.35)
    for m in (58, 62, 65, 69, 74):
        P(m, 113.4, 0.5, 2.0, 0.25)
    # 真相主题（Bb → D 大调）
    tru = [(76, 0, 74, 2), (76, 2, 77, 2), (77, 0, 76, 2), (77, 2, 72, 2), (78, 0, 74, 3), (78, 3, 70, 1),
           (79, 0, 78, 2), (79, 2, 81, 2), (80, 0, 83, 2), (80, 2, 81, 2), (81, 0, 79, 2), (81, 2, 76, 2)]
    for bar, beat, m, d in tru:
        P(m, b(bar, beat), 0.6, d * BEAT, 0.5, br=0.5)
        P(m - 12, b(bar, beat), 0.35, d * BEAT, 0.2)
    for s0, s1, c in segments():
        if 76 <= s0 < 82:
            notes, root = CH[c]
            for k, m in enumerate([root, notes[1], notes[2], notes[3]] * 2):
                P(m + (12 if k else 0), b(s0, k * 0.5), 0.38, 0.5, 0.2, br=0.4, p=-0.25)
    # 获奖者：赞美诗旋律
    hymn = [(82, 0, 78, 2), (82, 2, 81, 2), (83, 0, 76, 4), (84, 0, 74, 2), (84, 2, 78, 2), (85, 0, 79, 4),
            (86, 0, 81, 2), (86, 2, 78, 2), (87, 0, 79, 2), (87, 2, 83, 2), (88, 0, 81, 4)]
    for bar, beat, m, d in hymn:
        P(m, b(bar, beat), 0.55, d * BEAT, 0.42, br=0.5)
    # 片尾：最后的大和弦
    for m in (38, 50, 57, 62, 66, 69, 74):
        P(m, b(90), 0.7, 6.0, 0.32)
    for m in (74, 78, 81, 86):
        P(m, b(91), 0.6, 4.0, 0.25)


def sfx():
    # 钩子：利率每跳一次一声滴答
    for k in range(7):
        fx.add(tick(2500, 0.9), 0.5 + k * 0.5, 0.5, p=0.15 * (-1) ** k)
        PULSE.append((0.5 + k * 0.5, 0.3))
    fx.add(boom(1.0), HITS['kesh'], 0.75)
    sub.add(subdrop(1.2, 70, 28), HITS['kesh'], 0.6)
    PULSE.append((HITS['kesh'], 1.0))
    # 贷款柱塌缩
    fx.add(tom(36, 0.9, 1.0), 5.5, 0.55)
    # 存款计数上涨：上行铃
    for k, m in enumerate([74, 77, 81, 84, 86, 89]):
        fx.add(bell(m, 1.5), 8.0 + k * 0.25, 0.35, p=-0.4 + 0.16 * k)
    fx.add(boom(0.5, 2.0), 8.0, 0.35)
    # 「为什么？」→ 标题
    fx.add(riser(1.9, 45, 69), 10.1, 0.8)
    fx.add(reverse_swell(1.8, 4000), 10.2, 0.6)
    T = HITS['title']
    fx.add(boom(1.2, 3.8), T, 0.9)
    fx.add(braam(26, 3.0), T, 0.55)
    sub.add(subdrop(1.8, 75, 26), T, 0.7)
    fx.add(shimmer(1.6, 86), T + 0.05, 0.4)
    PULSE.append((T, 1.4))
    # 01 反常
    fx.add(boom(0.5, 2.2), 20.0, 0.4)
    fx.add(reverse_swell(0.9, 2500), 23.3, 0.4)
    for k, m in enumerate([74, 77, 81]):
        fx.add(bell(m, 1.2), 28.5 + k * 0.5, 0.3)
    for k, v in enumerate([3.83, 4.33, 2.72, 0.44]):        # 柱子逐个落下（音高≈数值）
        fx.add(pluck(60 + int(v * 2.5), 0.3, 2400, 400), 32.0 + k * 0.5, 0.35)
    fx.add(tom(33, 1.0, 1.0), 34.0, 0.55)
    sub.add(subdrop(0.9, 60, 30), 34.0, 0.4)
    fx.add(bell(86, 2.0), HITS['dep_spike'], 0.4)
    fx.add(boom(0.6, 2.0), HITS['dep_spike'], 0.4)
    PULSE.append((HITS['dep_spike'], 0.9))
    fx.add(riser(1.0, 62, 74, 0.5), 40.2, 0.4)
    fx.add(boom(0.6, 2.4), HITS['split'], 0.45)
    for k, m in enumerate([74, 78, 81, 86]):
        fx.add(bell(m, 1.4), 48.5 + k * 0.5, 0.28, p=-0.5 + k * 0.33)
    # 「预期」
    fx.add(bell(74, 3.0), HITS['yuqi'], 0.5)
    fx.add(reverse_swell(1.6, 3500), 58.4, 0.55)
    fx.add(riser(1.8, 50, 74), 58.2, 0.6)
    # 诺奖重拍
    T = HITS['nobel']
    fx.add(boom(1.0, 3.5), T, 0.8)
    sub.add(subdrop(1.6, 70, 28), T, 0.6)
    fx.add(shimmer(1.8, 84, notes=(0, 4, 7, 12, 16, 19, 24, 28)), T, 0.5)
    PULSE.append((T, 1.3))
    # 1970 年代：碎裂
    T = HITS['break70s']
    fx.add(crystal(1.8), T, 0.55)
    fx.add(boom(0.8, 2.5), T, 0.6)
    music.add(pad_chord([50, 51, 52, 56], 0.9, cut=2500, att=0.005, rel=0.6), T, 0.35)
    PULSE.append((T, 1.0))
    fx.add(boom(0.6, 2.4), HITS['hall'], 0.45)
    fx.add(boom(0.4, 2.0), HITS['two_people'], 0.35)
    sub.add(subdrop(1.2, 60, 28, 0.8), 88.2, 0.5)
    fx.add(boom(0.7, 2.8), HITS['woodford'], 0.55)
    PULSE.append((HITS['woodford'], 0.9))
    for k in range(6):                       # 日历翻页
        fx.add(tick(1800, 0.8), 99.0 + k * 0.5, 0.35, p=0.2)
    T = HITS['cbank']
    fx.add(tom(31, 1.0, 1.4), T, 0.6)
    fx.add(bell(50, 4.0, 0.7), T, 0.35)
    fx.add(bell(62, 3.0, 0.8), T + 0.5, 0.25)
    PULSE.append((T, 1.0))
    fx.add(boom(0.8, 3.0), HITS['draghi'], 0.6)
    for k, m in enumerate([79, 77, 76, 74, 72]):     # 利率回落
        fx.add(pluck(m, 0.35, 2000, 400, wave='tri'), 113.0 + k * 0.3, 0.3)
    fx.add(riser(2.0, 50, 76), 114.0, 0.8)
    fx.add(reverse_swell(1.9, 5000), 114.1, 0.6)
    # 传导：第三个大重拍
    T = HITS['machine']
    fx.add(boom(1.3, 4.0), T, 0.95)
    fx.add(braam(26, 3.2, 1.1), T, 0.6)
    sub.add(subdrop(2.0, 80, 26), T, 0.7)
    PULSE.append((T, 1.5))
    for k, m in enumerate([62, 65, 69, 72, 74]):
        fx.add(bell(m + 12, 1.5), 116.5 + k * 0.5, 0.3, p=-0.6 + 0.3 * k)
    for k, m in enumerate([74, 77, 81, 86]):
        fx.add(bell(m, 1.5), 124.5 + k * 1.0, 0.3)
    T = HITS['vicious']
    sub.add(subdrop(1.4, 70, 30), T, 0.6)
    fx.add(boom(0.7, 2.4), T, 0.5)
    T = HITS['selffulfil']
    fx.add(boom(1.0, 3.0), T, 0.7)
    fx.add(braam(26, 2.4, 0.9), T, 0.45)
    PULSE.append((T, 1.2))
    for k, t in enumerate([136.6, 137.8, 139.0]):
        fx.add(bell(81 + k * 2, 1.6), t, 0.3)
    T = HITS['rope']
    n = S(1.5)
    tt = np.arange(n) / SR
    creak = lp(saw(mtof(38) * (1 - 0.08 * tt / 1.5), n), 500) * np.exp(-tt / 0.8)
    fx.add(creak, T, 0.3)
    fx.add(tom(36, 0.8, 1.0), T, 0.45)
    T = HITS['fiscal']
    fx.add(boom(0.7, 2.6), T, 0.5)
    fx.add(shimmer(1.2, 81, notes=(0, 4, 7, 12, 16)), T, 0.35)
    PULSE.append((T, 0.9))
    fx.add(reverse_swell(1.6, 3000), 150.4, 0.45)
    fx.add(boom(0.5, 3.0), HITS['truth'], 0.45)
    fx.add(bell(74, 3.5), HITS['keyline'], 0.45)
    fx.add(boom(0.6, 3.0), HITS['keyline'], 0.45)
    PULSE.append((HITS['keyline'], 1.0))
    # 获奖者：定音鼓滚奏 → 重击
    for T in (HITS['laureates'], HITS['woodford_card'], HITS['both']):
        fx.add(timpani_roll(38, 1.4, 0.8), T - 1.4, 0.45)
        fx.add(tom(38, 1.0, 1.6), T, 0.6)
        fx.add(boom(0.6, 3.0), T, 0.4)
        PULSE.append((T, 1.0))
    # 片尾
    fx.add(riser(2.0, 50, 74, 0.9), 178.0, 0.7)
    fx.add(reverse_swell(2.0, 4500), 178.0, 0.6)
    fx.add(shimmer(2.0, 74, notes=(0, 7, 12, 14, 19, 24, 26, 31)), 178.0, 0.3)
    T = HITS['logo']
    fx.add(boom(1.0, 3.5), T, 0.75)
    sub.add(subdrop(1.6, 70, 26), T, 0.55)
    PULSE.append((T, 1.2))
    T = HITS['brandword']
    fx.add(boom(1.1, 4.0), T, 0.8)
    fx.add(tom(38, 1.0, 1.8), T, 0.6)
    fx.add(shimmer(1.4, 86, notes=(0, 4, 7, 11, 14, 16, 19, 24)), 182.6, 0.45)
    PULSE.append((T, 1.4))


# ---------------------------------------------------------------- 混音
def sidechain_env(depth=0.45, rel=0.16):
    e = np.zeros(N)
    t = np.arange(S(0.6)) / SR
    shape = np.exp(-t / rel) * np.clip(t / 0.004, 0, 1)
    for tk, pw in KICKS:
        i = S(tk)
        j = min(N, i + len(shape))
        e[i:j] = np.maximum(e[i:j], shape[:j - i] * min(pw, 1.0))
    return 1 - depth * e


def lufs(x):
    import pyloudnorm as pyln
    return pyln.Meter(SR).integrated_loudness(x)


def limiter(x, ceil=0.89, look=0.004, rel=0.12):
    """前瞻峰值限幅（逐采样增益，平滑）"""
    pk = np.abs(x).max(1)
    L = S(look)
    from scipy.ndimage import maximum_filter1d
    pk = maximum_filter1d(pk, size=2 * L + 1)
    g = np.minimum(1.0, ceil / np.maximum(pk, 1e-9))
    # 平滑：快速下降、慢速恢复
    a = math.exp(-1 / (rel * SR))
    gs = _smooth_gain(g, a)
    gs = np.minimum(gs, g)
    return x * gs[:, None]


from numba import njit  # noqa: E402


@njit(cache=True)
def _smooth_gain(g, a):
    out = np.empty_like(g)
    s = 1.0
    for i in range(g.shape[0]):
        if g[i] < s:
            s = g[i]
        else:
            s = a * s + (1 - a) * g[i]
        out[i] = s
    return out


BIG = ['title', 'nobel', 'machine', 'logo', 'brandword']


def breath_and_impact():
    """大重拍前留 90 ms「换气」（压掉 riser/swell 的尾巴），重拍处叠一层有力的瞬态"""
    for key in BIG:
        T = HITS[key]
        i0, i1 = S(T - 0.10), S(T - 0.004)
        env = np.ones(N)
        env[i0:i1] = 0.12
        r = S(0.03)
        env[i0 - r:i0] = np.linspace(1, 0.12, r)
        env[i1:i1 + S(0.004)] = np.linspace(0.12, 1, S(0.004))
        for bus in (fx, music, keys, drums, bass):
            bus.y *= env[:, None]
        drums.add(kick(1.3, length=0.6, f_hi=140, f_lo=40), T, 1.0)
        drums.add(snare(1.0, length=0.5, bright=0.8), T, 0.55)
        drums.add(clap(1.2), T, 0.45)
        KICKS.append((T, 1.2))


def main(build):
    os.makedirs(build, exist_ok=True)
    print('arranging…', flush=True)
    pads(); strings_parts(); arps(); pizz_ostinato(); basslines(); drum_parts(); piano_parts(); sfx()
    breath_and_impact()
    sc = sidechain_env()
    print('mixing…', flush=True)
    hall_ir = make_ir(2.8, 0.025, seed=3, width=1.1)
    room_ir = make_ir(0.9, 0.008, seed=5, damp0=7000, damp1=2500)
    m = music.y * sc[:, None] ** 0.7
    k = keys.y * sc[:, None] ** 0.5
    bs = bass.y * sc[:, None]
    send_hall = m * 0.35 + k * 0.45 + fx.y * 0.4 + drums.y * 0.08
    send_room = drums.y * 0.25 + bs * 0.05
    wet = convolve(send_hall, hall_ir) * 0.55 + convolve(send_room, room_ir) * 0.35
    dry = m * 0.8 + k * 0.85 + bs * 0.9 + drums.y * 0.85 + fx.y * 0.8 + lp(sub.y, 120, 4) * 0.9
    pre = hp(dry + wet, 28, 2)
    np.save(os.path.join(build, 'premaster.npy'), pre.astype(np.float32))
    master(build, pre, os.environ.get('MUSIC_OUT', 'music.wav'))


def movavg(x, n):
    """居中滑动平均（累积和实现，O(N)）"""
    c = np.cumsum(np.concatenate([np.zeros(1), x]))
    h = n // 2
    i0 = np.clip(np.arange(len(x)) - h, 0, len(x))
    i1 = np.clip(np.arange(len(x)) + n - h, 0, len(x))
    return (c[i1] - c[i0]) / np.maximum(i1 - i0, 1)


def master(build, mix=None, out='music.wav'):
    """母带：音色均衡（以参考曲目 opus5.5涌现 的频谱倾斜为目标）+ 激励器补「空气感」+ 电平 + 限幅"""
    if mix is None:
        mix = np.load(os.path.join(build, 'premaster.npy')).astype(np.float64)
    mix = mix + 0.30 * bp(mix, 140, 480, 2)                   # 低中频的温暖
    mix = mix - 0.18 * bp(mix, 520, 900, 2)                   # 去一点「箱音」
    ex = hp(np.tanh(hp(mix, 2800, 2) * 5.0) / 5.0, 5500, 2)   # 激励器：生成 5 kHz 以上的谐波
    mix = mix + 1.4 * ex
    mix = shelf_high(mix, 2500, 4.5)                          # 提亮：手机外放更清楚
    mix = shelf_high(mix, 6500, 5.0)
    # 缓速电平器：把安静段托起（保留动态起伏）
    rms = np.sqrt(movavg((mix ** 2).mean(1), S(1.5)) + 1e-12)
    target = np.sqrt(np.mean(rms ** 2))
    g = np.clip((target / rms) ** 0.35, 0.6, 2.2)
    g = movavg(g, S(0.5))
    mix = mix * g[:, None]
    mix = np.tanh(mix * 1.15) / 1.15                  # 轻微饱和
    # 响度：-14 LUFS，限幅 -1 dBFS
    gain = 10 ** ((-14.0 - lufs(mix)) / 20)
    mix = limiter(mix * gain, ceil=10 ** (-1.2 / 20))
    # 头尾
    f = S(2.0)
    mix[-f:] *= np.linspace(1, 0, f)[:, None] ** 2
    mix[:S(0.01)] *= np.linspace(0, 1, S(0.01))[:, None]
    print(f'LUFS {lufs(mix):.1f}  peak {20 * np.log10(np.abs(mix).max()):.2f} dBFS', flush=True)
    sf.write(os.path.join(build, out), mix.astype(np.float32), SR, subtype='PCM_24')
    if not PULSE:
        print('saved', out)
        return
    # ---- 画面同步数据（逐帧）
    nf = int(round(DUR * FPS))
    fr = np.zeros(nf)
    for t, p in PULSE:
        i = int(round(t * FPS))
        for d in range(0, 12):
            if i + d < nf:
                fr[i + d] = max(fr[i + d], p * math.exp(-d / 3.5))
    hop = SR // FPS
    mono = mix.mean(1)
    en = np.array([np.sqrt(np.mean(mono[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(nf)])
    en = np.convolve(en, np.ones(5) / 5, 'same')
    en = en / en.max()
    json.dump(dict(pulse=fr.round(4).tolist(), energy=en.round(4).tolist(), fps=FPS, dur=DUR),
              open(os.path.join(build, 'music_meta.json'), 'w'))
    print('saved', os.path.join(build, 'music.wav'))


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == 'master':
        master(sys.argv[1], out=sys.argv[3] if len(sys.argv) > 3 else 'music_test.wav')
    else:
        main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'build'))
