"""时间轴：由旁白脚本 + 每句配音时长推出所有时间点。画面、字幕、配乐共用。

T.s('c3') / T.e('c3')：某句旁白的开始 / 结束秒数
T.sec['cause'] = (start, end)：章节起止；有重拍的章节在 start 处打击
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import SECTIONS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("WORK", os.path.join(HERE, "..", "work"))
FPS = 30
VO = json.load(open(os.path.join(WORK, "vo.json")))

OUTRO = 9.6          # 最后一句结束后：粒子汇聚 logo → 浮现 → 品牌字 → 淡出
LINES = {}           # id -> (start, end, subtitle)
ORDER = []
SEC = {}
HITS = []            # 重拍时间

t = 0.0
for name, lead, hit, lines in SECTIONS:
    s0 = t
    if hit:
        HITS.append(s0)
    t += lead
    for lid, text, sub, pause in lines:
        dur = VO[lid]["dur"] if text else 0.0
        LINES[lid] = (t, t + dur, text if sub is None else sub)
        ORDER.append(lid)
        t += dur + pause
    SEC[name] = (s0, t)

LAST_VO_END = LINES[ORDER[-1]][1]
LOGO_T = LAST_VO_END + 0.6      # 粒子开始汇聚成 logo
LOGO_SHOW = LOGO_T + 1.9        # 清晰 logo 浮现
BRAND_T = LOGO_SHOW + 0.75      # 金色「巴芒价值」在重拍上出现
DUR = LAST_VO_END + OUTRO
HITS.append(BRAND_T)
SEC["outro"] = (LAST_VO_END, DUR)


def s(lid):
    return LINES[lid][0]


def e(lid):
    return LINES[lid][1]


TEXT = {lid: text for sec in SECTIONS for (lid, text, _s, _p) in sec[3]}


def _w(ch):
    if ch in "，。：；？！、":
        return 1.6
    if ch in "「」“” —":
        return 0.0
    return 1.0


def at(lid, sub, end=False):
    """估计某句旁白里子串 sub 开始（或结束）念出的时间：按字数加权插值。"""
    txt = TEXT[lid]
    i = txt.index(sub) + (len(sub) if end else 0)
    tot = sum(_w(ch) for ch in txt)
    pre = sum(_w(ch) for ch in txt[:i])
    a, b = LINES[lid][0], LINES[lid][1]
    return a + (b - a) * pre / tot


if __name__ == "__main__":
    for k, (a, b) in SEC.items():
        print(f"{k:8s} {a:7.2f} – {b:7.2f}  ({b - a:5.1f}s)")
    print("hits", [round(h, 2) for h in HITS])
    print("DUR", round(DUR, 2), f"= {int(DUR // 60)}:{DUR % 60:04.1f}")
