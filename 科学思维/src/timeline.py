"""时间轴：由文字脚本推出所有时间点，并全部吸附到配乐的节拍网格上。画面、字幕、配乐共用。

- 原创配乐（src/music.py）写在这张网格上：112.9 BPM，一拍 0.5314 s，第 0 小节从 ORIGIN 秒开始。
- 每句字幕按阅读时长占若干拍，从拍点开始；每个章节从小节线开始，有重拍的章节在第一拍打击。
- T.s('c3') / T.e('c3')：某句的开始 / 结束；T.at('c6', '抛硬币')：句中某个词的出现时刻（吸附到拍点）。
- T.ACCENTS：段落中间的重音（画面里的关键揭示），配乐在这些拍点上加打击，镜头轻推。
"""
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import SECTIONS, FIXED_BEATS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("WORK", os.path.join(HERE, "..", "work"))
FPS = 30
BEAT = 0.5314021732630634          # 112.9 BPM
BPM = 60 / BEAT
BAR = 4 * BEAT
ORIGIN = 0.6579022113645169 - BEAT  # 第 0 小节的第一拍

PUNCT = "，。：；？！、—「」“” ·"


def nchars(s):
    return len([ch for ch in s if ch not in PUNCT])


def read_time(text):
    """看懂一行字幕所需时间（秒）。"""
    return 0.5 + 0.18 * nchars(text)


def beat_t(b):
    return ORIGIN + b * BEAT


def q(t, mode="round"):
    """把时间吸附到最近的拍点。"""
    k = (t - ORIGIN) / BEAT
    k = math.ceil(k - 1e-6) if mode == "ceil" else math.floor(k + 1e-6) if mode == "floor" else round(k)
    return beat_t(k)


# 每章的小节数（配乐按章节逐小节编写）；内容放不下时会报错
SECTION_BARS = {"hook": 8, "eight": 24, "title": 2, "cause": 18, "falsify": 16, "barnum": 12, "correct": 12,
                "invest": 24, "end": 12}
OUTRO_BARS = 6

LINES = {}           # id -> (start, end, subtitle)
ORDER = []
SEC = {}
HITS = []            # 每章开头的重拍
TEXT = {}

b = 0                # 当前拍
for name, lead, hit, lines in SECTIONS:
    s0b = b
    s0 = beat_t(b)
    if hit:
        HITS.append(s0)
    b += lead
    for lid, text, sub, pause in lines:
        TEXT[lid] = text
        nb = FIXED_BEATS.get(lid) or (max(1, math.ceil(read_time(text) / BEAT)) if text else 0)
        LINES[lid] = (beat_t(b), beat_t(b + nb), text if sub is None else sub)
        ORDER.append(lid)
        b += nb + pause
    need = SECTION_BARS[name] * 4
    if b - s0b > need:
        raise SystemExit(f"章节 {name} 内容 {b - s0b} 拍，超出 {need} 拍")
    b = s0b + need
    SEC[name] = (s0, beat_t(b))
SEC["hook"] = (0.0, SEC["hook"][1])

LAST_END = SEC[list(SEC)[-1]][1]
LOGO_T = LAST_END                       # 终句化作粒子、开始汇聚成 logo（小节线）
LOGO_SHOW = LOGO_T + 2 * BAR            # 清晰 logo 浮现
BRAND_T = LOGO_T + 4 * BAR              # 金色「巴芒价值」落在配乐最后的 D 大调和弦上
DUR = LOGO_T + OUTRO_BARS * BAR + 0.4
HITS.append(BRAND_T)
SEC["outro"] = (LAST_END, DUR)


def s(lid):
    return LINES[lid][0]


def e(lid):
    return LINES[lid][1]


def _w(ch):
    if ch in "，。：；？！、":
        return 1.6
    if ch in "「」“” —":
        return 0.0
    return 1.0


def at(lid, sub, end=False):
    """句中子串 sub 出现的时刻：按阅读权重插值，再吸附到拍点。"""
    txt = TEXT[lid]
    i = txt.index(sub) + (len(sub) if end else 0)
    tot = sum(_w(ch) for ch in txt)
    pre = sum(_w(ch) for ch in txt[:i])
    a, b_ = LINES[lid][0], LINES[lid][1]
    return q(a + (b_ - a) * pre / tot)


# 抛硬币：从「每天猜」起，每个八分音符淘汰一天，20 天
COIN_T0 = at("i2", "每天猜")
COIN_STEP = BEAT / 2

# ---------------------------------------------------------------- 段落中的重音（画面揭示点）
ACCENTS = sorted({
    s("h1"), s("h2"), s("h3"), s("h4"),
    s("s2"), s("s3"), s("s4"), s("s10"), s("s11"), s("s13"),
    s("c3"), s("c5"), s("c7"), s("c10"),
    s("f2"), s("f3"), s("f4"), s("f8"), at("f9", "迷信"),
    s("m2"), s("m5"), s("m6"), s("m7"), s("m8"),
    s("k3"), at("k4", "2005"), s("k5"),
    COIN_T0 + 20 * COIN_STEP, s("i3"), at("i4", "那就不是运气"),
    s("i7"), s("i8"), s("i9"), s("i10"), s("i11"), at("i12", "定价权"),
    s("e2"), s("e4"), s("e5"),
})

if __name__ == "__main__":
    for k, (a, b_) in SEC.items():
        print(f"{k:8s} {a:7.2f} – {b_:7.2f}  ({b_ - a:5.1f}s, {(b_ - a) / BAR:4.1f} bars)")
    print("hits", [round(h, 2) for h in HITS])
    print("DUR", round(DUR, 2), f"= {int(DUR // 60)}:{DUR % 60:04.1f}")
