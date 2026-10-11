"""时间轴：由文字脚本推出所有时间点，并全部吸附到配乐的节拍网格上。画面、字幕、配乐共用。

- 配乐 100 BPM，一拍 0.6 s，一小节 2.4 s；第 0 小节从 ORIGIN 秒开始。
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
BPM = 100
BEAT = 60 / BPM
BAR = 4 * BEAT
ORIGIN = 0.5            # 片头留 0.5 s 黑场，第一记重拍落在 0.5 s

PUNCT = "，。：；？！、—「」“” ·"


def nchars(s):
    return len([ch for ch in s if ch not in PUNCT])


def read_time(text):
    """看懂一行字幕所需时间（秒）。"""
    return 0.6 + 0.2 * nchars(text)


def beat_t(b):
    return ORIGIN + b * BEAT


def q(t, mode="round"):
    """把时间吸附到最近的拍点。"""
    k = (t - ORIGIN) / BEAT
    k = math.ceil(k - 1e-6) if mode == "ceil" else math.floor(k + 1e-6) if mode == "floor" else round(k)
    return beat_t(k)


LINES = {}           # id -> (start, end, subtitle)
ORDER = []
SEC = {}
HITS = []            # 每章开头的重拍
TEXT = {}

b = 0                # 当前拍
for name, lead, hit, lines in SECTIONS:
    b = math.ceil(b / 4 - 1e-9) * 4            # 章节从小节线开始
    s0 = beat_t(b)
    if hit:
        HITS.append(s0)
    b += round(lead / BEAT)
    for lid, text, sub, pause in lines:
        TEXT[lid] = text
        nb = FIXED_BEATS.get(lid) or (max(1, math.ceil(read_time(text) / BEAT)) if text else 0)
        LINES[lid] = (beat_t(b), beat_t(b + nb), text if sub is None else sub)
        ORDER.append(lid)
        b += nb + round(pause / BEAT)
    b = math.ceil(b / 4 - 1e-9) * 4
    SEC[name] = (s0, beat_t(b))
SEC["hook"] = (0.0, SEC["hook"][1])

LAST_END = SEC[list(SEC)[-1]][1]
LOGO_T = LAST_END                       # 终句化作粒子、开始汇聚成 logo（小节线）
LOGO_SHOW = LOGO_T + 2 * BEAT           # 清晰 logo 浮现
BRAND_T = LOGO_T + BAR                  # 金色「巴芒价值」落在下一小节的重拍上
DUR = BRAND_T + 2 * BAR + 0.6
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
    s("b3"), s("b6"),
    at("c4", "火越大"), s("c7"),
    at("f2", "一只黑天鹅"), s("f5"), at("f6", "而在于"), at("f7", "再画靶"),
    at("m2", "准确度打分"), s("m3"),
    s("k3"), at("k3", "2005"), at("k4", "而你自己"),
    COIN_T0 + 20 * COIN_STEP, at("i4", "那就不是运气"), at("i8", "这个假设"),
    at("e1", "而是始终"), at("e2", "错得更少"), at("e2", "改得更快"), s("e3"),
})

if __name__ == "__main__":
    for k, (a, b_) in SEC.items():
        print(f"{k:8s} {a:7.2f} – {b_:7.2f}  ({b_ - a:5.1f}s, {(b_ - a) / BAR:4.1f} bars)")
    print("hits", [round(h, 2) for h in HITS])
    print("DUR", round(DUR, 2), f"= {int(DUR // 60)}:{DUR % 60:04.1f}")
