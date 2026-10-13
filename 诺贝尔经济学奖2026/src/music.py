"""原创配乐 + 音效（numpy 合成）。120 BPM，D 小调 → 结尾转 D 大调，共 167 小节（5 分 34 秒）。

段落与画面一一对应（见 timeline.py；小节号 = 秒 / 2，霍尔及之后的段落沿用 v2 小节号，由 b() 后移 17 小节）：
  冷开场：利率每跳一次一声滴答；「按常理」一段上行；「可是」低音重击后进入不安的切分律动 → 标题重拍
  01 谨慎：拨弦琶音律动逐层加入贝斯、踩镲、拍手；企业观望处半速；「预期」一声铃 → 诺奖重拍
  02 诺奖 → 回到半个世纪前：年份倒转的滴答 → 战后模型（数据点下行、沿「菜单」上滑）→ 1973 石油危机的低频重击
      → 滞胀的心跳与不协和铃音 → 曲线一级级上移 → 旧规律碎裂 → 上行重建 → 三块基石 → 落到霍尔的 F 大调
  03 霍尔：温暖的钢琴主题两遍 + 弦乐；「意外」处整体抽空、转暗，再回到温暖
  04 伍德福德：钟表式拨奏 + 滴答 + 工厂律动；德拉吉一句话后舒展；「那么问题来了」抽空 → 重拍
  05 回到中国：全编制高潮（良性循环）→ 心跳（恶性循环）→ 时钟（真实利率）→ 推绳子 → 财政重建
      →「但别忘了霍尔的发现」时霍尔主题再现
  06 真相：钢琴 + 弦乐，关键句转 D 大调；获奖者：赞美诗和声 + 定音鼓
  片尾：汇聚 riser → logo 重拍 → 品牌字重拍 + 流光铃音 → 淡出
  四张「发现」卡片共用同一个铃声音型，形成记忆点。

用法：python3 music.py BUILD_DIR   → music.wav（48 kHz 立体声）+ music_meta.json（逐帧节拍/能量，供画面同步）
"""
import json
import math
import os
import sys

import numpy as np
import soundfile as sf

from synth import *          # noqa: F401,F403
from timeline import BAR, BEAT, CAP, DUR, FPS, HITS, SHIMMER_T0, T

N = S(DUR)

# v3 在诺奖之后插入了 50 秒的历史段（新时间轴 41–66 小节）。霍尔及之后的编曲仍沿用 v2 的小节号（霍尔从 49 小节起），
# 换算成秒时整体后移 DB 小节；历史段本身用 bn() 直接按新时间轴的小节号定位。
OM_B = 49                      # v2 小节号：霍尔开始
OM_NEW = 66                    # 新时间轴小节号：霍尔开始
DB = OM_NEW - OM_B             # 17 小节 = 34 秒


def b(bar, beat=0.0):
    """编曲小节（v2 小节号）→ 秒"""
    t = bar * BAR + beat * BEAT
    return t + DB * BAR if bar >= OM_B else t


def bn(bar, beat=0.0):
    """历史段：新时间轴的小节号 → 秒"""
    return bar * BAR + beat * BEAT

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
PROG = [  # (起始小节, 和弦)；1 小节 = 2 s；v2 小节号（霍尔从 49 小节起，换算成秒时由 b() 后移 17 小节）
    # 冷开场 0–14：利率下行 → 「按常理」→「可是」→ 钱去哪了 → 为什么
    (0, 'Dpow'), (3, 'F'), (4, 'C'),
    (5, 'Dm'), (6, 'Bb'), (7, 'Gm'), (8, 'A'), (9, 'Dm'), (10, 'Bb'), (11, 'Gm'), (12, 'Bbadd9'), (13, 'Asus'), (13.5, 'A'),
    # 标题 14–18
    (14, 'Bbadd9'), (15, 'F/A'), (16, 'Gm7'), (17, 'Asus'), (17.5, 'A'),
    # 01 谨慎 18–38
    (18, 'Dm'), (19, 'Bb'), (20, 'F'), (21, 'C'), (22, 'Dm'), (23, 'Bb'), (24, 'F'), (25, 'C'),
    (26, 'Dm'), (27, 'Bb'), (28, 'F'), (29, 'C'), (30, 'Dm'), (31, 'Bb'), (32, 'Gm'),
    (33, 'Gm'), (34, 'Bb'), (35, 'Gm'), (35.5, 'A'), (36, 'Bb'), (37, 'C'),
    # 02 诺奖 38–49
    (38, 'F'), (39, 'C/E'), (40, 'Dm'),
    (41, None),   # 41–49：v2 的「旧模型」段，v3 改写为 50 秒的历史段，见 history_music()（新时间轴上的 41–66 小节）
    # 03 霍尔 49–73（主题两遍；69.5 意外）
    (49, 'F'), (50, 'C/E'), (51, 'Dm'), (52, 'Bb'), (53, 'F'), (54, 'C/E'), (55, 'Dm'), (56, 'Bb'), (57, 'Gm'), (58, 'Bb'), (59, 'C'),
    (60, 'F'), (61, 'C/E'), (62, 'Dm'), (63, 'Bb'), (64, 'F'), (65, 'C/E'), (66, 'Dm'), (67, 'Bb'), (68, 'Gm'), (69, 'Bb'),
    (69.5, 'Eb'), (70, 'Gm'), (71, 'Bb'), (72, 'C'),
    # 04 伍德福德 73–101
    (73, 'Gm'), (74, 'Bb'), (75, 'Dm'), (76, 'A'), (77, 'Gm'), (78, 'Bb'), (79, 'F'), (80, 'C'), (81, 'Dm'), (82, 'Bb'),
    (83, 'Gm'), (84, 'Bb'), (85, 'Dm'), (86, 'A'), (87, 'Gm'), (88, 'Bb'), (89, 'F'), (90, 'A'),
    (90.5, 'Dm'), (92, 'Bb'), (93, 'F'), (94, 'C'), (95, 'A'), (96, 'Dm'), (97, 'Bb'), (98, 'Gm'), (100, 'A'),
    # 05 回到中国 101–129
    (101, 'Dm'), (102, 'Bb'), (103, 'F'), (104, 'C'), (105, 'Dm'), (106, 'Bb'), (107, 'F'), (107.5, 'C'),
    (108, 'Gm'), (109, 'Eb'), (109.5, 'A'),
    (110, 'Dm'), (111, 'Bb'), (112, 'Gm'), (113, 'A'), (114, 'Dm'), (115, 'Bb'), (116, 'Gm'), (117, 'A'),
    (118, 'Dm'), (119, 'Asus'), (119.5, 'A'),
    (120, 'Bb'), (121, 'C'), (122, 'Dm'), (122.5, 'F'), (123.5, 'C/E'), (124.5, 'Dm'), (125.5, 'Bb'), (126.5, 'Gm'), (128, 'A'),
    # 06 真相 129–136（关键句转 D 大调）
    (129, 'Bb'), (130, 'F/A'), (131, 'Gm'), (132, 'D'), (133, 'Bm'), (134, 'G'), (135, 'Asus'), (135.5, 'A'),
    # 获奖者 136–144
    (136, 'D'), (137, 'A/C#'), (138, 'Bm'), (139, 'G'), (140, 'D/F#'), (141, 'Em7'), (142, 'Asus'), (142.5, 'A'), (143, 'Bm'),
    # 片尾 144–149
    (144, 'G'), (144.5, 'A'), (145, 'Dadd9'), (149, None),
]
END_BAR = 149.6           # 最后的和弦延续到这里（v2 小节号；含片尾关注语的 2 秒）


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


def bar_of(sec):
    """秒 → 编曲小节（v2 小节号；与 b() 互逆，历史段内返回新时间轴小节号）"""
    bar = sec / BAR
    return bar - DB if bar >= OM_NEW else bar


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


def in_any(x, spans):
    return any(a <= x < z for a, z in spans)


# ---------------------------------------------------------------- 编曲
def pad_level(s0, mid):
    """每段和声垫的滤波截止频率与音量 —— 决定全片的明暗起伏"""
    table = [
        (0, 5, lambda: (ramp(mid, 0, 5, 380, 900), 0.55)),
        (5, 12, lambda: (ramp(mid, 5, 12, 900, 1700), 0.55)),
        (12, 14, lambda: (ramp(mid, 12, 14, 1200, 2600), 0.62)),
        (14, 18, lambda: (2300, 0.85)),
        (18, 33, lambda: (ramp(mid, 18, 33, 1100, 2600), 0.55)),
        (33, 35.5, lambda: (1100, 0.6)),
        (35.5, 38, lambda: (ramp(mid, 35.5, 38, 1500, 3200), 0.65)),
        (38, 41, lambda: (3300, 0.85)),
        (49, 69.5, lambda: (ramp(mid, 49, 69.5, 1500, 2600), 0.5)),
        (69.5, 71, lambda: (850, 0.5)),
        (71, 73, lambda: (2200, 0.55)),
        (73, 90.5, lambda: (ramp(mid, 73, 90.5, 1300, 2600), 0.5)),
        (90.5, 96, lambda: (2000, 0.55)),
        (96, 98.5, lambda: (ramp(mid, 96, 98.5, 2000, 3200), 0.6)),
        (98.5, 101, lambda: (900, 0.42)),
        (101, 108, lambda: (3600, 0.8)),
        (108, 110, lambda: (750, 0.75)),
        (110, 118, lambda: (950, 0.42)),
        (118, 120, lambda: (800, 0.42)),
        (120, 122.5, lambda: (ramp(mid, 120, 122.5, 1300, 3000), 0.62)),
        (122.5, 126.5, lambda: (2200, 0.55)),
        (126.5, 129, lambda: (ramp(mid, 126.5, 129, 1800, 3300), 0.62)),
        (129, 136, lambda: (ramp(mid, 129, 136, 2000, 2700), 0.55)),
        (136, 144, lambda: (2600, 0.75)),
        (144, 150, lambda: (3200, 0.8)),
    ]
    for a, z, f in table:
        if a <= s0 < z:
            return f()
    return 2000, 0.5


def pads():
    for s0, s1, c in segments():
        t0, t1 = b(s0), b(s1)
        notes, root = CH[c]
        cut, g = pad_level(s0, (s0 + s1) / 2)
        dur = (b(END_BAR) if s0 >= 145 else t1) - t0
        att = 0.8 if s0 < 5 else 0.25
        music.add(pad_chord(notes, dur + 0.05, cut=cut * 1.35, att=att, rel=0.9), t0 - 0.05, g * 0.5)


def strings_parts():
    secs = [(14, 18, 0.9), (36, 41, 0.6), (57.25, 69.5, 0.55), (86.5, 90.5, 0.5), (90.5, 96, 0.55),
            (101, 108, 0.6), (120, 129, 0.62), (129, 136, 0.75), (136, 144, 0.9), (145, 149, 0.9)]
    for s0, s1, c in segments():
        for a, z, g in secs:
            lo, hi_ = max(s0, a), min(s1, z)
            if lo < hi_:
                notes, root = CH[c]
                hi = [m + 12 for m in notes[1:]]
                dur = (b(END_BAR) if lo >= 145 else b(hi_)) - b(lo)
                music.add(strings(hi, dur, att=0.4, rel=1.1, cut=4300 if lo < 129 else 5000), b(lo), g * 0.55)


ARP_SECS = [  # (起, 止, 步长(拍), 截止频率起, 止, 音量)
    (5, 12, 0.5, 1400, 2400, 0.5),
    (12, 14, 0.25, 1800, 4200, 0.62),
    (18, 22.5, 0.5, 1400, 2200, 0.5),
    (22.5, 33, 0.25, 2200, 4200, 0.62),
    (33, 35.5, 0.5, 1600, 1600, 0.52),
    (35.5, 38, 0.25, 1800, 4500, 0.66),
    (101, 108, 0.25, 5200, 5200, 0.8),
    (110, 118, 0.5, 1700, 1700, 0.42),
    (120, 122.5, 0.5, 1800, 3600, 0.66),
    (126.5, 129, 0.5, 2000, 4000, 0.55),
]


def arps():
    """拨弦琶音：冷开场的不安、01 章的律动、05 章的高潮与财政重建"""
    pat16 = [0, 1, 2, 3, 2, 1, 2, 3]
    for s0, s1, c in segments():
        notes, root = CH[c]
        arp = [m + 12 for m in notes]
        for a, z, step, c0, c1, g in ARP_SECS:
            lo, hi_ = max(s0, a), min(s1, z)
            if lo >= hi_:
                continue
            k = 0
            for beat in np.arange(0, (hi_ - lo) * 4 - 1e-6, step):
                bar = lo + beat / 4
                cut = ramp(bar, a, z, c0, c1)
                m = arp[pat16[k % 8]] + (12 if (k // 8) % 2 and step < 0.5 else 0)
                vel = 0.9 if beat % 1 == 0 else 0.65
                x = pluck(m, dur=step * BEAT * 0.9, cut0=cut, cut1=cut * 0.18, decay=0.16)
                keys.add(x, b(lo, beat), g * vel * 0.32, p=0.35 * math.sin(k * 1.3))
                k += 1


def pizz_ostinato():
    """伍德福德：钟表式 16 分拨奏（企业定价、利率路径都在「算未来」）"""
    pat = [0, 2, 1, 2, 3, 2, 1, 2]
    for s0, s1, c in segments():
        notes, root = CH[c]
        for a, z in ((73, 90.5), (96, 98.5)):
            lo, hi_ = max(s0, a), min(s1, z)
            if lo >= hi_:
                continue
            for k in range(int(round((hi_ - lo) * 16))):
                t = b(lo, k * 0.25)
                m = notes[pat[k % 8]] + 12
                vel = 0.85 if k % 4 == 0 else 0.55
                keys.add(pizz(m, vel), t, 0.28 * ramp(lo, 73, 75, 0.6, 1.0), p=0.5 * math.sin(k * 0.9 + lo))


def basslines():
    for s0, s1, c in segments():
        notes, root = CH[c]
        bar = s0
        while bar < s1 - 1e-6:
            span = min(1.0, s1 - bar)
            if 5 <= bar < 12:
                for k in range(int(span * 8)):
                    bass.add(bass_note(root + (12 if k % 2 else 0), BEAT * 0.45, cut=ramp(bar, 5, 12, 360, 600)),
                             b(bar, k * 0.5), 0.5 if k % 2 == 0 else 0.36)
            elif 12 <= bar < 14:
                sub.add(sub_note(root - 12, BAR * span * 0.98), b(bar), 0.4)
            elif 18 <= bar < 22.5:
                for k in range(int(span * 4)):
                    bass.add(bass_note(root, BEAT * 0.9, cut=340), b(bar, k), 0.45)
            elif 22.5 <= bar < 33:
                for k in range(int(span * 8)):
                    bass.add(bass_note(root + (12 if k % 2 else 0), BEAT * 0.45, cut=380 + ramp(bar, 22.5, 33, 0, 300)),
                             b(bar, k * 0.5), 0.55 if k % 2 == 0 else 0.4)
            elif 33 <= bar < 35.5:
                bass.add(bass_note(root, BAR * span * 0.95, cut=300, drive=1.2), b(bar), 0.45)
            elif 35.5 <= bar < 38:
                for k in range(int(span * 8)):
                    bass.add(bass_note(root + (12 if k % 2 else 0), BEAT * 0.45, cut=500), b(bar, k * 0.5),
                             0.5 if k % 2 == 0 else 0.38)
            elif 57 <= bar < 69.5:
                bass.add(bass_note(root, BAR * span * 0.95, cut=300, drive=1.1), b(bar), 0.42)
            elif 69.5 <= bar < 71:
                sub.add(sub_note(root - 12, BAR * span), b(bar), 0.45)
            elif 77 <= bar < 90.5:
                for k in range(int(span * 8)):
                    bass.add(bass_note(root + (12 if k % 4 == 3 else 0), BEAT * 0.4, cut=420), b(bar, k * 0.5), 0.42)
            elif 90.5 <= bar < 96:
                bass.add(bass_note(root, BAR * span * 0.95, cut=260, drive=1.0), b(bar), 0.35)
            elif 96 <= bar < 98.5:
                for k in range(int(span * 8)):
                    bass.add(bass_note(root, BEAT * 0.45, cut=450), b(bar, k * 0.5), 0.45)
            elif 101 <= bar < 108:
                for k in range(int(span * 8)):
                    bass.add(bass_note(root + (12 if k % 2 else 0), BEAT * 0.45, cut=650, drive=2.0), b(bar, k * 0.5),
                             0.6 if k % 2 == 0 else 0.45)
            elif 108 <= bar < 110:
                sub.add(sub_note(root - 12, BAR * span), b(bar), 0.5)
            elif 110 <= bar < 118:
                for k in range(int(span * 4)):
                    bass.add(bass_note(root, BEAT * 0.8, cut=320, drive=1.2), b(bar, k), 0.4)
            elif 118 <= bar < 120:
                sub.add(sub_note(root - 12, BAR * span * 0.95), b(bar), 0.35)
            elif 120 <= bar < 122.5:
                for k in range(int(span * 8)):
                    bass.add(bass_note(root + (12 if k % 2 else 0), BEAT * 0.45, cut=500), b(bar, k * 0.5),
                             0.5 if k % 2 == 0 else 0.38)
            elif 122.5 <= bar < 126.5:
                bass.add(bass_note(root, BAR * span * 0.95, cut=280, drive=1.0), b(bar), 0.38)
            elif 126.5 <= bar < 129:
                for k in range(int(span * 8)):
                    bass.add(bass_note(root, BEAT * 0.45, cut=460), b(bar, k * 0.5), 0.42)
            elif 136 <= bar < 144:
                sub.add(sub_note(root - 12, BAR * span * 0.98), b(bar), 0.35)
                bass.add(bass_note(root, BAR * span * 0.9, cut=260, drive=1.0), b(bar), 0.35)
            elif bar == 145:
                sub.add(sub_note(26, b(END_BAR - 0.1) - b(145)), b(145), 0.45)
            bar += span


def snare_roll(bar0, beats, g=0.28, steps=0.25):
    n = int(beats / steps)
    for k in range(n):
        drums.add(snare(0.22 + 0.65 * (k / n) ** 2, length=0.18, bright=0.3), b(bar0, k * steps), g)


def drum_parts():
    # 冷开场：低沉的切分律动
    for bar in range(5, 12):
        K(b(bar, 0), 0.6)
        K(b(bar, 2.5), 0.42)
        if bar >= 7:
            for k in range(4):
                drums.add(hat(0.45), b(bar, k + 0.5), 0.35, p=0.25)
    K(b(12, 0), 0.55)
    for k in range(4):
        K(b(13, k), 0.45 + 0.1 * k)
    snare_roll(13, 4, 0.3)
    # 01 谨慎：逐层加入
    for bar in np.arange(18, 22.5, 1.0):
        K(b(bar, 0), 0.55)
    K(b(22, 2), 0.6)
    for bar in range(23, 33):
        K(b(bar, 0), 0.72)
        K(b(bar, 2), 0.62)
        if bar >= 24:
            for k in range(4):
                drums.add(hat(0.55), b(bar, k + 0.5), 0.45, p=0.25)
        if bar >= 28:
            drums.add(clap(0.8), b(bar, 1), 0.5, p=0.05)
            drums.add(clap(0.8), b(bar, 3), 0.5, p=-0.05)
    for k, m in enumerate([50, 47, 45, 43]):
        drums.add(tom(m, 0.7), b(32, 3 + k * 0.25), 0.4, p=-0.4 + k * 0.25)
    for bar in (33, 34):          # 企业观望：半速
        K(b(bar, 0), 0.7)
        drums.add(snare(0.7), b(bar, 2), 0.42)
    K(b(35, 0), 0.6)
    snare_roll(37, 4, 0.28, 0.125)
    for k in range(4):
        K(b(37, k), 0.45 + 0.1 * k)
    # 03 霍尔：两个人的对比开始，轻轻的心跳与沙锤
    for bar in np.arange(61, 69.5, 1.0):
        K(b(bar, 0), 0.5)
        for k in range(8):
            if bar + k / 8 < 69.5:
                drums.add(shaker(0.7 if k % 2 else 0.45), b(bar, k * 0.5), 0.42, p=0.3)
    for k in range(8):
        drums.add(tom(45 - k, 0.3 + 0.07 * k), b(72, 2 + k * 0.25), 0.3)
    # 04 伍德福德：滴答 + 工厂律动
    for a, z in ((73, 90.5), (96, 98.5)):
        for k in range(int((z - a) * 16)):
            drums.add(tick(2900 if k % 4 else 2200, 0.45 if k % 4 else 0.7), b(a, k * 0.25), 0.2, p=0.6 * math.sin(k))
    for bar in range(77, 90):
        K(b(bar, 0), 0.62)
        K(b(bar, 2), 0.52)
        drums.add(clap(0.7), b(bar, 1), 0.34)
        drums.add(clap(0.7), b(bar, 3), 0.34)
    snare_roll(89.5, 2, 0.3)
    for k in range(5):
        K(b(96, k * 0.5) if k < 4 else b(97, 0), 0.45 + 0.06 * k)
    for bar in (97, 98):
        for k in range(4):
            if bar + k / 4 < 98.5:
                K(b(bar, k), 0.6 + 0.05 * k)
    # 05 回到中国：全编制高潮（良性循环）
    for bar in range(101, 108):
        for k in range(4):
            K(b(bar, k), 0.85 if k % 2 == 0 else 0.7)
            drums.add(hat(0.5), b(bar, k + 0.5), 0.5, p=0.3)
            drums.add(hat(0.35), b(bar, k + 0.25), 0.35, p=-0.3)
            drums.add(hat(0.35), b(bar, k + 0.75), 0.35, p=-0.3)
        drums.add(snare(0.9), b(bar, 1), 0.5)
        drums.add(snare(0.9), b(bar, 3), 0.5)
    for k, m in enumerate([52, 50, 47, 45, 43, 40]):
        drums.add(tom(m, 0.8), b(107, 2.5 + k * 0.25), 0.45, p=-0.5 + k * 0.2)
    # 恶性循环：心跳
    for bar in (108, 109):
        K(b(bar, 0), 0.6, f_hi=80, f_lo=38, length=0.5)
        K(b(bar, 0.6), 0.45, f_hi=80, f_lo=38, length=0.5)
    # 降息为何不灵 / 真实利率：时钟
    for bar in range(110, 118):
        for k in range(4):
            drums.add(tick(2400, 0.6), b(bar, k), 0.25, p=0.3 * (-1) ** k)
        if bar >= 112:
            K(b(bar, 0), 0.45)
    # 财政重建
    for bar in (120, 121, 122):
        K(b(bar, 0), 0.7)
        if bar < 122:
            K(b(bar, 2), 0.65)
            drums.add(clap(0.8), b(bar, 1), 0.45)
            drums.add(clap(0.8), b(bar, 3), 0.45)
            for k in range(4):
                drums.add(hat(0.5), b(bar, k + 0.5), 0.45)
    # 长期政策 → 真相
    for k in range(4):
        K(b(128, k), 0.42 + 0.06 * k)
    snare_roll(128, 4, 0.24)
    # 获奖者：行进式低鼓
    for bar in range(136, 144):
        drums.add(tom(38, 0.55, 1.2), b(bar, 0), 0.4)
        drums.add(tom(38, 0.35, 1.0), b(bar, 2), 0.3)
        PULSE.append((b(bar, 0), 0.5))


HALL_THEME = [  # (小节, 拍, MIDI, 拍数) —— F 大调、11 小节
    (0, 0, 72, 1), (0, 1, 77, 1), (0, 2, 79, 1), (0, 3, 81, 1),
    (1, 0, 79, 2), (1, 2, 76, 1), (1, 3, 72, 1),
    (2, 0, 74, 2), (2, 2, 77, 1), (2, 3, 81, 1),
    (3, 0, 77, 3), (3, 3, 74, 1),
    (4, 0, 81, 2), (4, 2, 79, 1), (4, 3, 77, 1),
    (5, 0, 76, 2), (5, 2, 79, 1), (5, 3, 84, 1),
    (6, 0, 81, 3), (6, 3, 77, 1),
    (7, 0, 77, 2), (7, 2, 74, 2),
    (8, 0, 74, 2), (8, 2, 79, 2), (9, 0, 77, 2), (9, 2, 74, 2), (10, 0, 76, 4),
]


def piano_parts():
    P = lambda m, t, v=0.6, d=1.5, g=0.5, br=0.55, p=0.0: keys.add(piano_note(m, v, d, br), t, g, p)
    # 冷开场：开头两个高音；「按常理」一段向上的分解和弦（想象中的上升）
    P(86, 0.02, 0.5, 2.5, 0.35, p=0.2)
    P(81, 3.0, 0.45, 2.0, 0.3, p=-0.2)
    for k, m in enumerate([65, 69, 72, 77, 81]):
        P(m, 7.4 + k * 0.25, 0.5, 1.2, 0.3, p=-0.4 + 0.2 * k)
    P(26, HITS['kesh'], 0.9, 3.0, 0.5)          # 「可是」低音簇
    P(38, HITS['kesh'], 0.9, 3.0, 0.45)
    # 标题旋律
    mel = [(14, 0, 74, 1.5), (14, 1.5, 76, 0.5), (14, 2, 77, 2), (15, 0, 81, 3), (16, 0, 79, 2), (16, 2, 77, 2),
           (17, 0, 76, 3.5)]
    for bar, beat, m, d in mel:
        P(m, b(bar, beat), 0.62, d * BEAT, 0.45)
        P(m - 12, b(bar, beat), 0.4, d * BEAT, 0.18)
    # 霍尔主题：两遍（第二遍在「意外」处被打断）
    for start, cut in ((49, 60), (60, 69.5)):
        for bar, beat, m, d in HALL_THEME:
            if start + bar + beat / 4 >= cut:
                continue
            P(m, b(start + bar, beat), 0.58, d * BEAT * 0.95, 0.5 if start == 49 else 0.46, br=0.5)
            if start == 60:
                P(m - 12, b(start + bar, beat), 0.35, d * BEAT * 0.95, 0.16, br=0.45)
    for s0, s1, c in segments():                 # 左手分解和弦
        if 49 <= s0 < 69.5:
            notes, root = CH[c]
            seq = [root, notes[1], notes[2], notes[3], notes[2], notes[1], notes[2], notes[3]]
            for k in range(8):
                if s0 + k / 8 < 69.5:
                    P(seq[k] + (12 if k else 0), b(s0, k * 0.5), 0.42, 0.45, 0.22, br=0.4, p=-0.3)
    # 意外之后：低音区零星几下，再回到温暖（投票）
    for t_, m in ((b(70, 0), 43), (b(70, 2), 50), (b(70, 3), 55)):
        P(m, t_, 0.45, 1.2, 0.3)
    for bar in (71, 72):
        notes, root = CH[chord_at(bar)]
        for j, m in enumerate([root + 12] + [n + 12 for n in notes[1:]]):
            P(m, b(bar, j * 0.12), 0.5, 1.8, 0.28, br=0.45)
    # 德拉吉：一记和弦，市场平静后舒展
    for m in (50, 57, 62, 65):
        P(m, HITS['draghi'], 0.7, 2.0, 0.35)
    for m in (58, 62, 65, 69, 74):
        P(m, CAP['w_calm'][0], 0.5, 2.0, 0.25)
    # 回扣：「但别忘了霍尔的发现」—— 霍尔主题的前四小节再次出现
    for bar, beat, m, d in HALL_THEME:
        if bar < 4:
            P(m, b(122.5 + bar, beat), 0.55, d * BEAT * 0.95, 0.42, br=0.5)
    # 真相主题（Bb → D 大调）
    tru = [(129, 0, 74, 2), (129, 2, 77, 2), (130, 0, 76, 2), (130, 2, 72, 2), (131, 0, 74, 3), (131, 3, 70, 1),
           (132, 0, 78, 2), (132, 2, 81, 2), (133, 0, 83, 2), (133, 2, 81, 2), (134, 0, 79, 2), (134, 2, 76, 2),
           (135, 0, 74, 2), (135, 2, 73, 2)]
    for bar, beat, m, d in tru:
        P(m, b(bar, beat), 0.6, d * BEAT, 0.5, br=0.5)
        P(m - 12, b(bar, beat), 0.35, d * BEAT, 0.2)
    for s0, s1, c in segments():
        if 129 <= s0 < 136:
            notes, root = CH[c]
            for k, m in enumerate([root, notes[1], notes[2], notes[3]] * 2):
                if s0 + k / 8 < s1:
                    P(m + (12 if k else 0), b(s0, k * 0.5), 0.38, 0.5, 0.2, br=0.4, p=-0.25)
    # 获奖者：赞美诗旋律
    hymn = [(136, 0, 78, 2), (136, 2, 81, 2), (137, 0, 76, 4), (138, 0, 74, 2), (138, 2, 78, 2), (139, 0, 79, 4),
            (140, 0, 81, 2), (140, 2, 78, 2), (141, 0, 79, 2), (141, 2, 83, 2), (142, 0, 81, 4), (143, 0, 78, 4)]
    for bar, beat, m, d in hymn:
        P(m, b(bar, beat), 0.55, d * BEAT, 0.42, br=0.5)
    # 片尾：logo 与品牌字两记大和弦
    for m in (38, 50, 57, 62, 66, 69, 74):
        P(m, HITS['logo'], 0.7, 6.0, 0.32)
    for m in (74, 78, 81, 86):
        P(m, HITS['brandword'], 0.6, 4.0, 0.25)


def discovery(T0, power=1.0):
    """「发现」卡片的固定音型：沿当前和弦向上的铃声 + 轻重拍（霍尔 ①②、伍德福德 ①② 共用，形成记忆点）"""
    notes, root = CH[chord_at(bar_of(T0))]
    fx.add(reverse_swell(0.9, 3500, 0.8), T0 - 0.9, 0.35)
    for k, m in enumerate([notes[0] + 24, notes[1] + 24, notes[2] + 24, notes[3] + 24, notes[1] + 36]):
        fx.add(bell(m, 2.2), T0 + k * 0.09, 0.26 * power, p=-0.4 + 0.2 * k)
    fx.add(boom(0.55, 2.8), T0, 0.45 * power)
    PULSE.append((T0, 0.9))


def sfx():
    # ---- 冷开场
    for k in range(8):                           # 利率每跳一次一声滴答（与画面同步）
        t_ = 0.5 + 0.36 * k
        fx.add(tick(2500, 0.9), t_, 0.45, p=0.15 * (-1) ** k)
        PULSE.append((t_, 0.3))
    fx.add(bell(86, 2.0), CAP['c_low'][0], 0.25)
    fx.add(reverse_swell(1.2, 2500), HITS['kesh'] - 1.2, 0.35)
    fx.add(boom(1.0), HITS['kesh'], 0.75)
    sub.add(subdrop(1.2, 70, 28), HITS['kesh'], 0.6)
    PULSE.append((HITS['kesh'], 1.0))
    for k, v in enumerate([7.92, 3.83, 4.33, 2.72, 0.44]):   # 贷款柱逐个出现（音高≈数值）
        fx.add(pluck(58 + int(v * 2.6), 0.3, 2400, 400), HITS['kesh'] + 0.3 + 0.45 * k, 0.35)
    T0 = HITS['kesh'] + 0.3 + 0.45 * 5                       # 转负
    fx.add(tom(33, 1.0, 1.0), T0, 0.55)
    sub.add(subdrop(0.9, 60, 30), T0, 0.4)
    PULSE.append((T0, 0.8))
    fx.add(boom(0.5, 2.2), CAP['c_neg'][0], 0.4)
    fx.add(tom(36, 0.8, 1.0), CAP['c_neg'][0], 0.35)
    fx.add(boom(0.5, 2.4), CAP['c_where'][0], 0.4)
    for k, m in enumerate([74, 77, 81, 86]):                 # 存款 +6.99
        fx.add(bell(m, 1.4), CAP['c_where'][0] + 0.4 + k * 0.12, 0.3, p=-0.4 + 0.25 * k)
    fx.add(tom(34, 0.9, 1.0), CAP['c_where'][0] + 0.9, 0.45)   # 贷款 −1.03
    fx.add(reverse_swell(1.0, 3000), CAP['c_why'][0] - 1.0, 0.45)
    fx.add(boom(0.6, 2.6), CAP['c_why'][0], 0.45)
    fx.add(riser(1.9, 45, 69), HITS['title'] - 1.9, 0.8)
    fx.add(reverse_swell(1.8, 4000), HITS['title'] - 1.8, 0.6)
    # ---- 标题重拍
    T0 = HITS['title']
    fx.add(boom(1.2, 3.8), T0, 0.9)
    fx.add(braam(26, 3.0), T0, 0.55)
    sub.add(subdrop(1.8, 75, 26), T0, 0.7)
    fx.add(shimmer(1.6, 86), T0 + 0.05, 0.4)
    PULSE.append((T0, 1.4))
    # ---- 01 谨慎
    fx.add(boom(0.5, 2.2), HITS['survey'], 0.4)
    for k, m in enumerate([81, 76, 74]):                     # 三根调查柱
        fx.add(bell(m, 1.2), HITS['survey'] + 1.0 + 0.35 * k, 0.3, p=-0.3 + 0.3 * k)
    fx.add(boom(0.45, 2.2), HITS['spend'], 0.35)
    fx.add(shimmer(2.0, 86, 0.6), HITS['spend'] + 0.8, 0.2)  # 100 枚硬币点亮
    for k, m in enumerate([76, 74, 72]):                     # 67.5 → 64.6
        fx.add(pluck(m, 0.35, 2200, 400, wave='tri'), HITS['spend'] + 4.0 + k * 0.25, 0.32)
    fx.add(boom(0.5, 2.4), HITS['split'], 0.45)
    for k, m in enumerate([74, 78, 81]):                     # 分化卡片
        fx.add(bell(m, 1.4), HITS['split'] + 0.8 + k * 0.5, 0.26, p=-0.5 + k * 0.33)
    fx.add(tom(35, 0.9, 1.0), HITS['split'] + 2.3, 0.45)     # 新房 −13%
    fx.add(tom(33, 1.0, 1.1), HITS['firms'], 0.5)
    sub.add(subdrop(1.0, 60, 30), HITS['firms'], 0.4)
    fx.add(reverse_swell(1.2, 3000), HITS['yuqi'] - 1.2, 0.45)
    fx.add(bell(72, 3.0), HITS['yuqi'], 0.5)
    fx.add(boom(0.6, 2.6), HITS['yuqi'], 0.45)
    PULSE.append((HITS['yuqi'], 1.0))
    fx.add(riser(1.8, 50, 74), HITS['nobel'] - 1.8, 0.6)
    fx.add(reverse_swell(1.6, 3500), HITS['nobel'] - 1.6, 0.55)
    # ---- 02 诺奖
    T0 = HITS['nobel']
    fx.add(boom(1.0, 3.5), T0, 0.8)
    sub.add(subdrop(1.6, 70, 28), T0, 0.6)
    fx.add(shimmer(1.8, 84, notes=(0, 4, 7, 12, 16, 19, 24, 28)), T0, 0.5)
    PULSE.append((T0, 1.3))
    # ---- 03 霍尔
    fx.add(boom(0.6, 2.4), HITS['hall'], 0.45)
    PULSE.append((HITS['hall'], 0.8))
    discovery(HITS['law1'])
    fx.add(bell(93, 1.2), HITS['bonus'], 0.3)                # 一次性奖金：叮的一下
    fx.add(bell(88, 1.0), HITS['bonus'] + 0.08, 0.2)
    PULSE.append((HITS['bonus'], 0.6))
    fx.add(reverse_swell(1.0, 2500), HITS['raise'] - 1.0, 0.4)   # 长期涨薪：温暖的托起
    fx.add(boom(0.5, 3.0, 50, 30), HITS['raise'], 0.4)
    PULSE.append((HITS['raise'], 0.7))
    fx.add(boom(0.4, 2.0), HITS['people'], 0.35)
    discovery(HITS['law2'])
    fx.add(bell(77, 1.6), b(bar_of(HITS['surprise'])) - 2.4, 0.22)   # 如期涨薪：平静
    T0 = HITS['surprise']                                    # 意外：消费跳变
    sub.add(subdrop(1.4, 70, 28), T0, 0.65)
    fx.add(boom(0.8, 2.6), T0, 0.55)
    fx.add(tom(33, 1.0, 1.0), T0, 0.5)
    PULSE.append((T0, 1.1))
    fx.add(reverse_swell(1.4, 2500), CAP['h_vote'][0] - 1.0, 0.35)
    # ---- 04 伍德福德
    fx.add(boom(0.7, 2.8), HITS['woodford'], 0.55)
    PULSE.append((HITS['woodford'], 0.9))
    discovery(HITS['rule1'])
    for k in range(6):                                       # 月份一格格点亮
        fx.add(tick(1800, 0.8), CAP['w_price'][0] + 0.4 + k * 0.5, 0.35, p=0.2)
    discovery(HITS['rule2'])
    for k, m in enumerate([72, 69, 67, 69, 72]):             # 路径 A：降一下就回去
        fx.add(pluck(m, 0.35, 2000, 400, wave='tri'), CAP['w_loan'][0] + 0.3 + k * 0.25, 0.26)
    fx.add(reverse_swell(1.2, 3500), HITS['pathB'] - 1.2, 0.45)   # 路径 B：长期偏低
    fx.add(boom(0.5, 3.0), HITS['pathB'], 0.4)
    T0 = CAP['w_manage'][0]                                  # 央行旋钮
    fx.add(tom(31, 1.0, 1.4), T0, 0.55)
    fx.add(bell(50, 4.0, 0.7), T0, 0.32)
    fx.add(bell(62, 3.0, 0.8), T0 + 0.5, 0.22)
    PULSE.append((T0, 1.0))
    fx.add(boom(0.8, 3.0), HITS['draghi'], 0.6)
    PULSE.append((HITS['draghi'], 1.0))
    for k, m in enumerate([79, 77, 76, 74, 72]):             # 国债收益率回落
        fx.add(pluck(m, 0.35, 2000, 400, wave='tri'), HITS['draghi'] + 1.6 + k * 0.6, 0.28)
    for k, m in enumerate([38, 41, 45]):                     # 三块积木（家庭、企业、央行）
        fx.add(tom(m, 0.8, 0.9), HITS['synth'] + 0.2 + 0.35 * k, 0.4)
    for k, m in enumerate([74, 77, 81, 86]):                 # 屋顶
        fx.add(bell(m, 1.8), HITS['synth'] + 1.4 + k * 0.1, 0.25)
    fx.add(boom(0.5, 2.6), HITS['question'], 0.4)
    fx.add(riser(2.0, 50, 76), HITS['machine'] - 2.0, 0.8)
    fx.add(reverse_swell(1.9, 5000), HITS['machine'] - 1.9, 0.6)
    # ---- 05 回到中国：第三个大重拍
    T0 = HITS['machine']
    fx.add(boom(1.3, 4.0), T0, 0.95)
    fx.add(braam(26, 3.2, 1.1), T0, 0.6)
    sub.add(subdrop(2.0, 80, 26), T0, 0.7)
    PULSE.append((T0, 1.5))
    for k, m in enumerate([62, 65, 69, 72, 74]):             # 五个节点
        fx.add(bell(m + 12, 1.5), T0 + 0.5 + k * 0.5, 0.3, p=-0.6 + 0.3 * k)
    for k, m in enumerate([74, 77, 81, 84, 86]):             # 良性循环：一环扣一环
        fx.add(bell(m, 1.5), CAP['m_good'][0] + 0.3 + k * 1.05, 0.28)
    T0 = HITS['vicious']
    sub.add(subdrop(1.4, 70, 30), T0, 0.6)
    fx.add(boom(0.7, 2.4), T0, 0.5)
    for k, m in enumerate([45, 43, 41, 38]):                 # 恶性循环：一环一环往下
        fx.add(tom(m, 0.7, 0.9), T0 + 0.3 + k * 0.85, 0.35)
    T0 = HITS['selffulfil']
    fx.add(boom(1.0, 3.0), T0, 0.7)
    fx.add(braam(26, 2.4, 0.9), T0, 0.45)
    PULSE.append((T0, 1.2))
    fx.add(bell(76, 2.0), CAP['m_why'][0] + 1.2, 0.25)       # 「？」
    t2 = CAP['m_real'][0]
    fx.add(bell(81, 1.6), t2 + 1.4, 0.3)                     # ≈ 0%
    fx.add(tom(34, 0.9, 1.0), t2 + 2.8, 0.45)                # ≈ 6%
    fx.add(boom(0.4, 2.2), t2 + 2.8, 0.3)
    T0 = HITS['rope']
    n = S(1.5)
    tt = np.arange(n) / SR
    creak = lp(saw(mtof(38) * (1 - 0.08 * tt / 1.5), n), 500) * np.exp(-tt / 0.8)
    fx.add(creak, T0 + 2.0, 0.3)
    fx.add(tom(36, 0.8, 1.0), T0 + 2.0, 0.45)
    T0 = HITS['fiscal']
    fx.add(boom(0.7, 2.6), T0, 0.5)
    fx.add(shimmer(1.2, 81, notes=(0, 4, 7, 12, 16)), T0, 0.35)
    for k, m in enumerate([81, 86]):
        fx.add(bell(m, 1.4), CAP['m_fiscal'][0] + 0.1 + 0.5 * k, 0.28)
    PULSE.append((T0, 0.9))
    fx.add(reverse_swell(1.0, 3000), CAP['m_hall'][0] - 1.0, 0.35)    # 回扣霍尔
    fx.add(bell(77, 2.5), CAP['m_hall'][0], 0.3)
    fx.add(pluck(81, 0.4, 2400, 400), CAP['m_hall'][0] + 1.0, 0.32)    # +11%
    fx.add(tom(34, 0.9, 1.0), CAP['m_hall'][0] + 2.4, 0.45)           # −5.6%
    fx.add(reverse_swell(1.4, 3500), CAP['m_long'][0] - 1.0, 0.4)
    fx.add(reverse_swell(1.6, 3000), HITS['truth'] - 1.6, 0.45)
    # ---- 06 真相
    fx.add(boom(0.5, 3.0), HITS['truth'], 0.45)
    fx.add(bell(74, 3.5), HITS['keyline'], 0.45)
    fx.add(boom(0.6, 3.0), HITS['keyline'], 0.45)
    PULSE.append((HITS['keyline'], 1.0))
    # ---- 获奖者：定音鼓滚奏 → 重击
    for T0 in (HITS['laureates'], HITS['woodford_card'], HITS['both']):
        fx.add(timpani_roll(38, 1.4, 0.8), T0 - 1.4, 0.45)
        fx.add(tom(38, 1.0, 1.6), T0, 0.6)
        fx.add(boom(0.6, 3.0), T0, 0.4)
        PULSE.append((T0, 1.0))
    # ---- 片尾：汇聚 → logo → 品牌字 + 流光
    T0 = HITS['converge']
    fx.add(riser(2.0, 50, 74, 0.9), T0, 0.7)
    fx.add(reverse_swell(2.0, 4500), T0, 0.6)
    fx.add(shimmer(2.0, 74, notes=(0, 7, 12, 14, 19, 24, 26, 31)), T0, 0.3)
    T0 = HITS['logo']
    fx.add(boom(1.0, 3.5), T0, 0.75)
    sub.add(subdrop(1.6, 70, 26), T0, 0.55)
    PULSE.append((T0, 1.2))
    T0 = HITS['brandword']
    fx.add(boom(1.1, 4.0), T0, 0.8)
    fx.add(tom(38, 1.0, 1.8), T0, 0.6)
    fx.add(shimmer(1.4, 86, notes=(0, 4, 7, 11, 14, 16, 19, 24)), SHIMMER_T0, 0.45)
    fx.add(bell(81, 3.0, 0.8), CAP['e_slogan'][0], 0.22)            # 关注语浮现
    fx.add(bell(86, 2.5, 0.8), CAP['e_slogan'][0] + 0.25, 0.14)
    PULSE.append((T0, 1.4))


# ---------------------------------------------------------------- 回到半个世纪前（新时间轴第 41–66 小节，82–132 s）
PROG_OM = [  # (小节, 和弦)，直接用新时间轴的小节号
    (41, 'Dm'), (42, 'Bb'),                                             # 年份倒转
    (43, 'Dm'), (44, 'Bb'), (45, 'F'), (46, 'C'), (47, 'Gm'),          # 战后模型、政策菜单
    (47.5, 'Eb'), (48, 'Gm'), (49, 'A'),                                # 1973 石油危机
    (50, 'Dm'), (51, 'Eb'), (52, 'Gm'), (53, 'A'),                      # 滞胀
    (54, 'Gm'), (55, 'Eb'), (55.5, 'A'),                                # 旧模型失灵（55.5 碎裂）
    (56, 'Dm'), (57, 'Bb'), (58, 'F'), (59, 'C'),                       # 重建
    (60, 'Dm'), (61, 'Bb'), (62, 'F'), (63, 'C/E'), (64, 'Gm'), (65, 'C'), (OM_NEW, None),   # 新凯恩斯主义 → 霍尔（F）
]


def om_segments():
    for (s0, c), (s1, _) in zip(PROG_OM, PROG_OM[1:]):
        if c is not None:
            yield s0, s1, c


def history_music():
    P = lambda m, t, v=0.6, d=1.5, g=0.5, br=0.55, p=0.0: keys.add(piano_note(m, v, d, br), t, g, p)
    for s0, s1, c in om_segments():
        notes, root = CH[c]
        mid = (s0 + s1) / 2
        t0, t1 = bn(s0), bn(s1)
        # 和声垫：暖褐 → 暗红 → 冷 → 重新变暖
        if s0 < 43:
            cut, g, att = 900, 0.5, 0.8
        elif s0 < 47.5:
            cut, g, att = ramp(mid, 43, 47.5, 1500, 2100), 0.5, 0.25
        elif s0 < 50:
            cut, g, att = 850, 0.6, 0.1
        elif s0 < 55.5:
            cut, g, att = ramp(mid, 50, 55.5, 750, 1100), 0.62, 0.2
        elif s0 < 57:
            cut, g, att = 900, 0.45, 0.4
        else:
            cut, g, att = ramp(mid, 57, 66, 1600, 3000), 0.55, 0.3
        music.add(pad_chord(notes, t1 - t0 + 0.05, cut=cut * 1.35, att=att, rel=0.9), t0 - 0.05, g * 0.5)
        hi = [m + 12 for m in notes[1:]]
        if 50 <= s0 < 55.5:                                  # 滞胀：压低的弦乐
            music.add(strings([m - 12 for m in hi], t1 - t0, att=0.6, rel=1.0, cut=2400), t0, 0.3)
        if s0 >= 57:                                         # 重建：弦乐托起
            music.add(strings(hi, t1 - t0, att=0.5, rel=1.1, cut=4300), t0, 0.55 * ramp(s0, 57, 62, 0.6, 1.0))
        # 琶音
        pat = [0, 1, 2, 3, 2, 1, 2, 3]
        arp = [m + 12 for m in notes]
        if 43 <= s0 < 47.5 or s0 >= 58:
            step = 0.25 if s0 >= 62 else 0.5
            cut_a = 1500 if s0 < 47.5 else ramp(s0, 58, 66, 1800, 3800)
            ga = 0.38 if s0 < 47.5 else 0.5
            k = 0
            for beat in np.arange(0, (s1 - s0) * 4 - 1e-6, step):
                m = arp[pat[k % 8]]
                vel = 0.9 if beat % 1 == 0 else 0.65
                keys.add(pluck(m, dur=step * BEAT * 0.9, cut0=cut_a, cut1=cut_a * 0.18, decay=0.16), bn(s0, beat),
                         ga * vel * 0.32, p=0.35 * math.sin(k * 1.3))
                k += 1
        # 低音
        bar = s0
        while bar < s1 - 1e-6:
            span = min(1.0, s1 - bar)
            if 43 <= bar < 47.5 or 57 <= bar < 60:
                bass.add(bass_note(root, BAR * span * 0.95, cut=260, drive=1.0), bn(bar), 0.35)
            elif 47.5 <= bar < 50:
                for kk in range(int(round(span * 8))):
                    bass.add(bass_note(root + (12 if kk % 2 else 0), BEAT * 0.45, cut=420, drive=1.4), bn(bar, kk * 0.5),
                             0.48 if kk % 2 == 0 else 0.34)
            elif 50 <= bar < 55.5:
                sub.add(sub_note(root - 12, BAR * span * 0.98), bn(bar), 0.45)
            elif 60 <= bar < 66:
                for kk in range(int(round(span * 4))):
                    bass.add(bass_note(root, BEAT * 0.9, cut=340), bn(bar, kk), 0.4)
            bar += span
    # ---- 鼓：石油危机的切分律动 → 滞胀的心跳 → 新框架的稳步推进
    for bar in (47.5, 48, 49):
        K(bn(bar, 0), 0.62)
        if bar != 47.5:
            K(bn(bar, 2.5), 0.42)
            for kk in range(4):
                drums.add(hat(0.45), bn(bar, kk + 0.5), 0.32, p=0.25)
    for bar in (50, 51, 52):
        K(bn(bar, 0), 0.6, f_hi=80, f_lo=38, length=0.5)
        K(bn(bar, 0.6), 0.45, f_hi=80, f_lo=38, length=0.5)
    for bar in range(60, 66):
        K(bn(bar, 0), 0.5)
        if bar >= 62:
            K(bn(bar, 2), 0.42)
            for kk in range(8):
                drums.add(shaker(0.7 if kk % 2 else 0.45), bn(bar, kk * 0.5), 0.38, p=0.3)
    for kk in range(8):
        drums.add(tom(45 - kk, 0.3 + 0.07 * kk), bn(65, 2 + kk * 0.25), 0.28)
    # ---- 钢琴与音效（与画面逐一对齐）
    lt0 = HITS['rewind']
    P(86, lt0, 0.5, 2.5, 0.32, p=0.2)                      # 与开场呼应的两个高音
    P(81, lt0 + 2.1, 0.45, 2.0, 0.28, p=-0.2)
    fx.add(reverse_swell(2.6, 3500, 0.8), lt0, 0.4)        # 时间倒流
    for kk in range(16):                                   # 年份倒转：滴答先快后慢
        u = (kk + 0.5) / 16
        tt = T('oldmodel', 0.4) + 2.3 * (math.acos(1 - 2 * u) / math.pi)
        fx.add(tick(3000 - 70 * kk, 0.7), tt, 0.3, p=0.4 * math.sin(kk))
    for i, m in enumerate([84, 81, 79, 77, 76, 74, 72, 71, 69, 67]):   # 1960 年代的点逐个落下
        P(m, T('oldmodel', 3.9) + i * 0.25, 0.5, 0.35, 0.3, p=-0.6 + i * 0.13)
    fx.add(shimmer(1.4, 81, 0.6, notes=(0, 4, 7, 12, 16)), T('oldmodel', 6.4), 0.18)     # 曲线画出
    for i, m in enumerate([67, 69, 72, 74, 76, 79, 81, 84]):            # 沿着「菜单」滑动：通胀越来越高
        keys.add(pluck(m, 0.3, 2600, 400, wave='tri'), T('oldmodel', 9.0) + i * 0.25, 0.22, p=-0.4 + 0.1 * i)
    T0 = HITS['oil']                                       # 1973 石油危机
    fx.add(reverse_swell(1.0, 3000), T0 - 1.0, 0.4)
    fx.add(boom(0.9, 3.2), T0, 0.7)
    sub.add(subdrop(1.4, 70, 28), T0, 0.55)
    PULSE.append((T0, 1.0))
    for i, m in enumerate([62, 67, 74]):                   # 三根油价柱
        fx.add(pluck(m, 0.4, 2400, 400), T0 + 0.4 + 0.6 * i, 0.38)
    fx.add(bell(86, 1.6), T0 + 2.4, 0.3)                   # ≈ ×4
    fx.add(boom(0.45, 2.2), T0 + 2.4, 0.3)
    T0 = HITS['stag']                                      # 滞胀
    fx.add(boom(0.9, 3.0), T0, 0.65)
    music.add(pad_chord([50, 51, 52, 56], 0.9, cut=2500, att=0.005, rel=0.6), T0, 0.35)
    PULSE.append((T0, 1.1))
    for i, m in enumerate([86, 83, 88, 84, 90, 85, 89, 87, 91, 86, 92, 88]):   # 1970 年代的点一个个弹出（不协和）
        fx.add(bell(m, 0.8, 0.8), T0 + 0.18 * i, 0.12, p=0.5 * math.sin(i * 1.7))
    for i, (m, tt) in enumerate(((38, 24.6), (41, 25.4), (45, 26.2))):          # 曲线一级级上移
        fx.add(tom(m, 0.8, 1.0), T('oldmodel', tt), 0.42, p=-0.3 + 0.3 * i)
        PULSE.append((T('oldmodel', tt), 0.5))
    fx.add(bell(81, 1.6), T('oldmodel', 26.8), 0.25)
    T0 = HITS['shatter']                                   # 旧规律碎裂
    fx.add(reverse_swell(0.9, 4000), T0 - 0.9, 0.4)
    fx.add(crystal(1.8), T0, 0.55)
    fx.add(boom(0.8, 2.5), T0, 0.6)
    PULSE.append((T0, 1.0))
    T0 = HITS['rebuild']                                   # 碎片聚拢：上行
    for i, m in enumerate([62, 65, 69, 72, 74, 77, 81, 84]):
        P(m, T0 + 0.2 + i * 0.3, 0.5, 0.6, 0.3, p=0.6 - i * 0.15)
    for i, m in enumerate([74, 77, 81, 86]):               # 标题「新凯恩斯主义模型」
        fx.add(bell(m, 2.0), CAP['o_nk'][0] + i * 0.1, 0.22)
    for i, m in enumerate([38, 41, 45]):                   # 三块基石
        fx.add(tom(m, 0.8, 0.9), HITS['blocks'] + 1.5 * i, 0.4)
        fx.add(bell([77, 81, 84][i], 1.4), HITS['blocks'] + 1.5 * i, 0.2)
        PULSE.append((HITS['blocks'] + 1.5 * i, 0.6))
    fx.add(shimmer(1.2, 81, 0.6, notes=(0, 4, 7, 12, 16)), HITS['tool'] + 0.2, 0.2)
    T0 = HITS['base']                                      # 两位得主：这套框架的基石
    fx.add(boom(0.55, 3.0, 50, 30), T0 + 0.4, 0.45)
    for i, m in enumerate([65, 72, 77, 81]):
        fx.add(bell(m, 2.2), T0 + 0.6 + i * 0.12, 0.24)
    PULSE.append((T0 + 0.4, 0.8))
    fx.add(reverse_swell(1.6, 3000), HITS['hall'] - 1.6, 0.35)


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


def soften_hits(mix, fc=8000.0, pre=0.006, post=0.03):
    """大重拍的起音约 30 ms 内只保留 8 kHz 以下：「换气」后的突然重击会让 AAC 编码过冲 5 dB 以上（真峰值超 0 dBFS），
    柔化高频起音后成片真峰值回到 -1 dBTP 以下，低频冲击力不变"""
    for key in BIG:
        T = HITS[key]
        i0, i1 = S(T - pre - 0.05), S(T + post + 0.05)
        seg = mix[i0:i1].copy()
        lo = lp(seg, fc, 4)
        t = np.arange(i1 - i0) / SR - 0.05 - pre
        w = np.clip(t / 0.003, 0, 1) * np.clip(1 - (t - pre) / post, 0, 1) ** 2
        mix[i0:i1] = seg * (1 - w[:, None]) + lo * w[:, None]
    return mix


def main(build):
    os.makedirs(build, exist_ok=True)
    print('arranging…', flush=True)
    pads(); strings_parts(); arps(); pizz_ostinato(); basslines(); drum_parts(); piano_parts(); sfx()
    history_music()
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
    mix = soften_hits(mix)
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
