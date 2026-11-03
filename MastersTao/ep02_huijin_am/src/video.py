"""《汇金退出了谁？》分镜渲染。python3 video.py chunk <起始帧> <结束帧> <输出.mp4> | still <秒,秒> <输出_%.png>

复用 EP01 的渲染引擎（ep01_national_team/src/engine.py）与 MastersTao 品牌模块。
"""
import math, os, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.join(HERE, "..", "..", "ep01_national_team", "src"))
from engine import *  # noqa
from timeline import BAR, BEAT, DURATION, HITS, QSCHED, BIG, MAIN_END, PRE_DROP, S, QL, b

NQ = len(QL)
CNT = S["count"]
STEPS = S["steps"]
QSTART = {i: b(s) for i, s, d in QSCHED}
QEND = {i: b(s + d) for i, s, d in QSCHED}
CAPMAX = max(e["cap"] for st in STEPS for e in st["exits"])       # 贵州茅台 150.76 亿
NAME = "汇金"
FULL = "中央汇金资产管理有限责任公司"


def qtxt(q):
    return q[:4] + " Q" + q[-1]


def fmt_d(v):
    return ("+" if v > 0 else "−" if v < 0 else "±") + str(abs(v))


def fmt_yi(v):
    return f"{v:,.1f}" if v >= 10 else f"{v:.2f}"


# ---------------------------------------------------------------- 背景 / 通用
_yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
_xx = np.linspace(0, 1, W, dtype=np.float32)[None, :]
BG = (np.array([0.020, 0.024, 0.052], np.float32)[None, None, :] * (1 - _yy[..., None]) +
      np.array([0.007, 0.008, 0.018], np.float32)[None, None, :] * _yy[..., None])
BG = BG * (1 - 0.55 * np.clip(((_xx - 0.5) ** 2 * 1.4 + (_yy - 0.48) ** 2 * 1.1) * 2.2, 0, 1))[..., None]
rng0 = np.random.default_rng(7)
NST = 700
STAR = np.stack([rng0.uniform(-30, 30, NST), rng0.uniform(-8, 40, NST), rng0.uniform(-20, 140, NST)], 1)
STAR_C = np.where(rng0.random(NST)[:, None] < 0.5, BA, GOLD) * 0.6 + 0.4
STAR_A = rng0.uniform(0.15, 0.6, NST)


def beat_pulse(t):
    return math.exp(-((t % BEAT) / BEAT) * 5)


def nebula(F, t, cols=(GOLD * 0.55, BB), amt=1.0, cy=0.45):
    if amt <= 0.01: return
    h, w = 60, 34
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]; xx = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    acc = np.zeros((h, w, 3), np.float32)
    for k, (px, py, r, c) in enumerate(((0.25, cy - 0.1, 0.35, cols[0]), (0.78, cy + 0.12, 0.4, cols[1]),
                                        (0.5, cy + 0.35, 0.3, cols[0]))):
        x0 = px + 0.08 * math.sin(t * 0.07 + k * 2); y0 = py + 0.05 * math.cos(t * 0.05 + k)
        acc += np.exp(-((xx - x0) ** 2 * 3.2 + (yy - y0) ** 2) / (2 * r * r * 0.5))[..., None] * np.asarray(c, np.float32)
    F.C += cv2.resize(acc, (W, H), interpolation=cv2.INTER_CUBIC) * (0.05 * amt)


def stars(F, t, amt=1.0, drift=0.0):
    cam = Cam(pos=(0, 6, -20 + drift), f=900)
    x, y, z = cam.project(STAR)
    ok = z > 0.5
    a = STAR_A * amt * np.clip(1.2 - z / 140, 0, 1) * (0.75 + 0.25 * np.sin(t * 2 + STAR[:, 0]))
    F.splat(x[ok], y[ok], STAR_C[ok] * 0.55, a[ok], buf="G")


def glass_num(F, s, x, y, size, col, a=1.0, anchor="m", fnt="numb", glow=0.35):
    if a <= 0.003: return 0
    top = np.minimum(np.asarray(col) * 0.35 + 0.75, 1.0)
    tw = F.text(s, x, y, size, fnt, col, a, anchor=anchor, tab=True, grad=(top, np.asarray(col) * 0.85), shadow=0.6)
    F.text(s, x, y, size, fnt, col, a * glow * 0.5, anchor=anchor, tab=True, glow=glow)
    return tw


def roll(v0, v1, t, t0, dur=0.5):
    return int(round(v0 + (v1 - v0) * eo((t - t0) / dur)))


def tag(F, lab, col, x, y, a=1.0, size=22):
    tw = text_width(lab, "bold", size)
    pts = F.rrect_pts(x, y - size * 0.72, x + tw + size * 1.1, y + size * 0.72, size * 0.7)
    F.fill(pts, col * 0.16, a, buf="C")
    F.poly(pts + [pts[0]], col, a * 0.8, 1.5, buf="G")
    F.text(lab, x + size * 0.55, y, size, "bold", col, a, anchor="l")
    return tw + size * 1.1


def footnote(F, a=1.0):
    """底部常驻备注：简称「汇金」的全称与解释、统计口径"""
    if a <= 0.01: return
    F.fill([(60, 1782), (W - 60, 1782), (W - 60, 1783.5), (60, 1783.5)], INK3, a * 0.6, buf="C", mode="add")
    F.text(f"汇金：{FULL}（中央汇金投资全资子公司，2015 年设立）", W / 2, 1812, 23, "med", INK2, a)
    F.text("统计其出现在前十大股东 / 前十大流通股东的 A 股公司 · 市值为上一季末持股市值 · 退出名单 ≠ 清仓",
           W / 2, 1848, 20, "reg", INK3 + 0.2, a)


# ---------------------------------------------------------------- 钩子（0–4 小节）：第一帧即封面
def sc_hook(F, t):
    nebula(F, t, amt=0.7)
    stars(F, t, amt=0.5, drift=t * 0.6)
    st = STEPS[BIG]
    F.text("今年二季度，" + NAME + "一次退出", W / 2, 260, 58, "black", INK, 1.0, glow=0.15, shadow=0.6)
    F.text(f"{st['n_exit']} 家公司的十大股东名单", W / 2, 345, 58, "black", RED * 0.55 + INK * 0.45, 1.0, glow=0.2, shadow=0.6)
    v = roll(CNT[BIG - 1], CNT[BIG], t, b(1), b(2))
    F.text("出现在名单中的公司", W / 2, 620, 34, "med", INK2, 1.0)
    glass_num(F, str(v), W / 2, 790, 260, GOLD, 1.0, fnt="numk", glow=0.45)
    F.text("家", W / 2, 960, 40, "med", INK2, 1.0)
    F.text("2026 Q1" if t < b(1) else "2026 Q2", W / 2, 1035, 40, "numb", INK, 1.0, tab=True)
    ga = eo((t - b(1)) / 0.3)
    glass_num(F, fmt_d(CNT[BIG] - CNT[BIG - 1]), W / 2, 1160, 96, RED, ga, fnt="numk", glow=0.5)
    top = st["exits"][0]
    ta = eo((t - b(2.5)) / 0.3)
    F.glass(90, 1270, W - 90, 1470, 30, ta, tint=GOLD, edge=GOLD * 0.8)
    F.text("退出的最大一笔", W / 2, 1320, 32, "med", INK2, ta)
    F.text(f"{top['name']}  {top['cap']:.1f} 亿", W / 2, 1405, 64, "black", GOLD, ta, glow=0.25)
    qa = eo((t - b(3.25)) / 0.3)
    F.text("还退出了谁？", W / 2, 1600, 72, "black", INK, qa, glow=0.25)
    footnote(F, 1.0)
    F.bloom = 1.0 + 0.4 * eo((t - b(3)) / 1.5)


# ---------------------------------------------------------------- 标题（4–6）
def sc_title(F, t):
    t0 = b(4); lt = t - t0
    nebula(F, t, amt=1.0)
    stars(F, t, amt=0.6, drift=t * 2)
    F.flash = 0.4 * math.exp(-lt / 0.15); F.ca = 4 * math.exp(-lt / 0.3); F.zoom = 1 + 0.035 * math.exp(-lt / 0.4)
    a = win(t, t0, b(6) + 0.15, 0.15, 0.3)
    s = 1.0 + 0.06 * math.exp(-lt / 0.35)
    F.text(NAME, W / 2, 720, int(220 * s) // 2 * 2, "black", GOLD, a, grad=(INK, GOLD), glow=0.3, shadow=0.5)
    F.text("退出了谁？", W / 2, 950, int(170 * s) // 2 * 2, "black", INK, a, glow=0.25, shadow=0.5)
    w = 380 * eo((lt - 0.4) / 0.6)
    F.fill([(W / 2 - w, 1090), (W / 2 + w, 1090), (W / 2 + w, 1093), (W / 2 - w, 1093)], GOLD, a * 0.8, buf="G", mode="add")
    F.text_reveal("19 个季度 · 每季退出榜", W / 2, 1170, 54, t0 + 0.4, "bold", INK, a, stag=0.03, dur=0.3)
    F.text("按持股市值排名前 10", W / 2, 1250, 40, "med", INK2, a * eo((lt - 0.8) / 0.4))
    F.text("2022 Q1  ——  2026 Q3", W / 2, 1340, 34, "numm", INK3 + 0.25, a * eo((lt - 1.1) / 0.4), track=0.08)
    footnote(F, a)


# ---------------------------------------------------------------- 主体：逐季
CX0, CX1, CY0, CY1 = 120, 990, 610, 960


def cur_q(t):
    k = 0
    for i, s, d in QSCHED:
        if t >= b(s): k = i
    return k


def cx(i):
    return CX0 + (CX1 - CX0) * i / (NQ - 1)


def cy(v):
    return CY1 - (CY1 - CY0) * v / 170


def chart(F, t, k, a=1.0):
    p = eo5((t - QSTART[k]) / 0.4) if k > 0 else 1.0
    for v in (0, 50, 100, 150):
        F.line((CX0, cy(v)), (CX1, cy(v)), INK3, a * (0.4 if v == 0 else 0.2), 1.0)
        F.text(str(v), CX0 - 14, cy(v), 22, "numm", INK3 + 0.2, a * 0.9, anchor="r", tab=True)
    for i, q in enumerate(QL):
        if q.endswith("Q1"):
            F.text(q[:4], cx(i), CY1 + 30, 22, "numm", INK2, a, tab=True)
    pts = [(cx(i), cy(CNT[i])) for i in range(k)]
    if k > 0:
        pts.append((cx(k - 1) + (cx(k) - cx(k - 1)) * p, cy(CNT[k - 1] + (CNT[k] - CNT[k - 1]) * p)))
    else:
        pts = [(cx(0), cy(CNT[0]))]
    if len(pts) > 1:
        F.fill(pts + [(pts[-1][0], CY1), (pts[0][0], CY1)], GOLD, a * 0.55, buf="G", mode="add",
               grad=(GOLD * 0.18, GOLD * 0.0, CY0, CY1))
        F.poly(pts, GOLD, a * 0.25, 10); F.poly(pts, GOLD, a, 4)
    # 退出标记：红点大小 ∝ 当季退出市值
    for i in range(1, k + 1):
        cap = STEPS[i]["exit_cap_yi"]
        if cap <= 0: continue
        e = a * (eo((t - QSTART[i]) / 0.4) if i == k else 1.0)
        r = 4 + 18 * math.sqrt(cap / 876.1)
        F.glow_dot(cx(i), cy(CNT[i]), r, RED * 0.9, e * 0.8)
    F.glow_dot(pts[-1][0], pts[-1][1], 9 + 4 * beat_pulse(t), GOLD * 2.2, a)


def header(F, t, k, a=1.0):
    t0 = QSTART[k]
    F.glass(60, 190, W - 60, 540, 34, a, tint=GOLD)
    p = eo5((t - t0) / 0.4)
    if k > 0 and p < 1:
        F.text(qtxt(QL[k - 1]), 110, 270 - 50 * p, 64, "numb", INK, a * (1 - p), anchor="l", tab=True)
    glass_num(F, qtxt(QL[k]), 110, 270 + 50 * (1 - p), 64, INK, a * p, anchor="l", glow=0.2)
    F.text(f"{NAME} 出现在", 110, 345, 30, "med", INK2, a, anchor="l")
    v = roll(CNT[k - 1] if k > 0 else CNT[0], CNT[k], t, t0, 0.45 if k != BIG else 0.3)
    glass_num(F, str(v), 110, 445, 120, GOLD, a, anchor="l", fnt="numk", glow=0.4)
    F.text("家公司的十大股东名单", 110 + text_width(str(v), "numk", 120, tab=True) + 20, 470, 30, "med", INK2, a, anchor="l")
    st = STEPS[k]
    if k > 0:
        dv = CNT[k] - CNT[k - 1]
        dc = RED if dv > 0 else GRN if dv < 0 else INK3 + 0.3
        e = a * eo((t - t0 - 0.15) / 0.3)
        glass_num(F, fmt_d(dv), W - 110, 290, 76 if abs(dv) < 50 else 92, dc, e, anchor="r", fnt="numk", glow=0.4)
        F.text(f"退出 {st['n_exit']} 家 · 新进 {st['n_new']} 家", W - 110, 380, 30, "bold", INK, e, anchor="r")
        if st["exit_cap_yi"] > 0:
            F.text(f"退出市值合计 {st['exit_cap_yi']:,.1f} 亿", W - 110, 430, 28, "med", RED * 0.6 + INK * 0.4, e, anchor="r")
    else:
        F.text("起点", W - 110, 290, 40, "bold", INK2, a, anchor="r")


def board(F, t, k, a=1.0):
    st = STEPS[k]
    t0 = QSTART[k]
    y0 = 1040
    if k == 0:
        F.glass(60, y0, W - 60, y0 + 220, 30, a)
        F.text("接下来，每个季度", W / 2, y0 + 80, 40, "bold", INK, a)
        F.text("看汇金退出了哪些公司（按持股市值排序）", W / 2, y0 + 145, 32, "med", INK2, a)
        return
    if st["n_exit"] == 0:
        F.glass(60, y0, W - 60, y0 + 160, 30, a)
        F.text("本季没有退出", W / 2, y0 + 80, 44, "bold", INK2, a * eo((t - t0) / 0.3))
        return
    rows = st["exits"]
    n = len(rows)
    rh = 84 if n <= 5 else 62
    fs = 40 if n <= 5 else 34
    if n > 5: y0 = 1010
    hh = 100 + rh * n
    F.glass(60, y0, W - 60, y0 + hh, 30, a, tint=RED * 0.6 + GOLD * 0.4)
    F.text("本季退出 · 按上季末持股市值", 100, y0 + 48, 30, "bold", INK, a, anchor="l")
    if st["n_exit"] > n:
        F.text(f"前 {n} / 共 {st['n_exit']} 家", W - 100, y0 + 48, 28, "med", INK2, a, anchor="r")
    bx0, bx1 = 400, 820
    for j, e in enumerate(rows):
        if k == BIG:   # 倒数揭晓：第 10 名先出，每拍一名，第 1 名落在重拍上
            tj = t0 + (n - 1 - j) * BEAT + 0.0
            if j == 0: tj = b(QSCHED[BIG][1] + 2.5)
        else:
            tj = t0 + 0.15 + j * 0.07
        pj = eo5((t - tj) / 0.3)
        if pj <= 0: continue
        yy = y0 + 112 + j * rh
        dx = (1 - pj) * 60
        first = j == 0
        col = GOLD if first else INK
        F.text(str(j + 1), 100 + dx, yy, fs, "numk", GOLD if first else INK2, a * pj, anchor="l", tab=True)
        F.text(e["name"], 160 + dx, yy, fs + (4 if first else 0), "black" if first else "bold", col, a * pj, anchor="l")
        w = max(6, (bx1 - bx0) * e["cap"] / CAPMAX) * eo((t - tj - 0.05) / 0.4)
        bh = 13 if n <= 5 else 10
        F.fill([(bx0 + dx, yy - bh), (bx0 + dx + w, yy - bh), (bx0 + dx + w, yy + bh), (bx0 + dx, yy + bh)],
               (GOLD if first else RED * 0.7 + GOLD * 0.3), a * pj * 0.9, buf="G", mode="add")
        F.text("亿", W - 100, yy, fs - 8, "med", INK2, a * pj, anchor="r")
        F.text(fmt_yi(e["cap"]), W - 100 - text_width("亿", "med", fs - 8) - 8, yy, fs - 2, "numb", col, a * pj,
               anchor="r", tab=True)
        if e.get("note"):
            F.text("吸收合并退市", bx0 + dx + w + 14, yy, 22, "med", INK2, a * pj, anchor="l")
        if first and k == BIG and 0 <= t - tj < 0.6:
            F.flash = max(F.flash, 0.35 * math.exp(-(t - tj) / 0.12))
            F.ca = max(F.ca, 5 * math.exp(-(t - tj) / 0.3))
            F.zoom = max(F.zoom, 1 + 0.04 * math.exp(-(t - tj) / 0.3))


def impact(F, t, k):
    lt = t - QSTART[k]
    if lt < 0 or k == 0: return
    s = cl(STEPS[k]["exit_cap_yi"] / 80.0)
    F.zoom = max(F.zoom, 1 + (0.008 + 0.04 * s) * math.exp(-lt / 0.25))
    if s > 0.2:
        F.flash = max(F.flash, 0.25 * s * math.exp(-lt / 0.12))
        F.ca = max(F.ca, 5 * s * math.exp(-lt / 0.3))
    if k == BIG:
        A = 16 * math.exp(-lt / 0.3)
        F.shake = (A * math.sin(lt * 70), A * 0.7 * math.cos(lt * 53))


def sc_main(F, t):
    k = cur_q(t)
    pre = b(PRE_DROP) <= t < b(PRE_DROP + 1)
    dark = eio((t - b(PRE_DROP)) / 0.6) * 0.75 if pre else 0.0
    nebula(F, t, amt=0.6 * (1 - dark))
    stars(F, t, amt=0.45, drift=t * 0.8)
    a = eo((t - b(6)) / 0.3) * (1 - dark)
    header(F, t, k, a)
    chart(F, t, k, a)
    board(F, t, k, a)
    impact(F, t, k)
    footnote(F, 1.0)
    if pre:
        F.text_reveal("2026 年二季度", W / 2, 1050, 84, b(PRE_DROP) + 0.1, "black", INK, eo((t - b(PRE_DROP)) / 0.3),
                      stag=0.06, dur=0.25)
        F.glow_dot(W / 2, 1050, 380, RED * 0.14 * beat_pulse(t * 2), 1.0, buf="C")


# ---------------------------------------------------------------- 总结（4 小节）
def sc_summary(F, t):
    t0 = b(MAIN_END); lt = t - t0
    nebula(F, t, amt=0.9)
    stars(F, t, amt=0.6, drift=t)
    F.flash = 0.3 * math.exp(-lt / 0.14); F.zoom = 1 + 0.035 * math.exp(-lt / 0.3) + 0.02 * eio(lt / 7)
    a = win(t, t0, b(MAIN_END + 4) + 0.1, 0.15, 0.3)
    F.text_reveal("19 个季度，汇金一共", W / 2, 260, 60, t0, "black", INK, a, stag=0.04, dur=0.3)
    cards = [(f"{S['total_exits']}", "次退出名单", f"涉及 {S['unique_exit_companies']} 家公司（部分进出多次）", GOLD, 0.3),
             (f"{S['total_exit_cap_yi']:,.0f}", "亿 · 按上季末市值", f"其中 2026Q2 一季 {STEPS[BIG]['exit_cap_yi']:,.0f} 亿"
              f"（{STEPS[BIG]['exit_cap_yi'] / S['total_exit_cap_yi'] * 100:.0f}%）", RED, 0.9)]
    for j, (num, unit, sub, col, tj) in enumerate(cards):
        p = eo5((lt - tj) / 0.4)
        if p <= 0: continue
        y0 = 360 + j * 330
        F.glass(70, y0, W - 70, y0 + 290, 32, a * p, tint=col, edge=col * 0.8)
        tw = glass_num(F, num, 120, y0 + 115, 130, col, a * p, anchor="l", fnt="numk", glow=0.4)
        F.text(unit, 140 + tw, y0 + 135, 40, "bold", INK, a * p, anchor="l")
        F.text(sub, 120, y0 + 230, 32, "med", INK2, a * p, anchor="l")
    p = eo5((lt - 2.0) / 0.4)
    if p > 0:
        F.glass(70, 1040, W - 70, 1700, 32, a * p, tint=VIO)
        F.text(f"留下的 {CNT[-1]} 家，持股市值仍有 {S['cap'][-1]:,.0f} 亿", W / 2, 1110, 40, "black", INK, a * p)
        names = REMAIN
        for j, nm in enumerate(names):
            pj = eo((lt - 2.3 - j * BEAT / 4) / 0.25)
            F.text(nm, 190 + (j % 4) * 233, 1210 + (j // 4) * 78, 34, "bold", GOLD * 0.5 + INK * 0.5, a * p * pj)
        F.text("退出名单 ≠ 清仓：可能只是持股降到前十之外", W / 2, 1640, 30, "med", INK2, a * eo((lt - 4.0) / 0.4))
    footnote(F, 1.0)


import gzip, csv as _csv
REMAIN = sorted({r["name"] for r in _csv.DictReader(gzip.open(os.path.join(HERE, "..", "..", "ep01_national_team", "data",
                 "company_panel.csv.gz"), "rt", encoding="utf-8")) if r["quarter"] == QL[-1] and r["entity"] == "汇金资管"})


# ---------------------------------------------------------------- 片尾（3 小节）
LOGO = load_logo("blue", "logo-dark", 230)


def sc_end(F, t):
    t0 = b(MAIN_END + 4); lt = t - t0
    nebula(F, t, cols=(BA, BB), amt=1.0, cy=0.42)
    stars(F, t, amt=0.8, drift=t * 0.4)
    F.flash = 0.35 * math.exp(-lt / 0.15)
    rgb, al = LOGO
    h, w = al.shape
    a = eo((lt - 0.1) / 0.6)
    x0, y0 = (W - w) // 2, 560
    F.glow_dot(W / 2 - w * 0.33, y0 + h / 2, 160, BB * 0.22, a)
    rev = eo5((lt - 0.1) / 1.0)
    m = al.copy(); m[:, int(w * rev):] = 0
    F.blit(m, x0, y0, (1, 1, 1), a, colimg=rgb)
    w2 = 300 * eo((lt - 0.8) / 0.6)
    F.fill([(W / 2 - w2, y0 + h + 90), (W / 2 + w2, y0 + h + 90), (W / 2 + w2, y0 + h + 92.5), (W / 2 - w2, y0 + h + 92.5)],
           VIO, a * 0.8, buf="G", mode="add")
    F.text("这些公司里，你最关心哪一家？评论区聊聊", W / 2, 1000, 38, "bold", GOLD * 0.6 + INK * 0.4, a * eo((lt - 0.6) / 0.4))
    F.text_reveal("关注 MastersTao", W / 2, 1110, 68, t0 + 1.0, "black", INK, a, stag=0.05, glow=0.2)
    F.text_reveal("看懂机构持仓背后的投资逻辑。", W / 2, 1210, 46, t0 + 1.4, "med", INK2, a, stag=0.04)
    F.text("masterstao.com", W / 2, 1420, 28, "numm", INK3 + 0.2, a * eo((lt - 2.0) / 0.5), track=0.08)


# ---------------------------------------------------------------- 调度
SCENE_FUN = [(b(0), b(4), sc_hook), (b(4), b(6), sc_title), (b(6), b(MAIN_END), sc_main),
             (b(MAIN_END), b(MAIN_END + 4), sc_summary), (b(MAIN_END + 4), DURATION + 1, sc_end)]
HUD = Hud(width=W, series=None)


def render(t):
    F = Frame(t, BG)
    for a0, a1, fn in SCENE_FUN:
        if a0 <= t < a1:
            fn(F, t); break
    F.bloom *= 1.0 + 0.12 * beat_pulse(t) * (b(6) <= t < b(MAIN_END + 4))
    F.fade = 1 - eio((t - (DURATION - 1.2)) / 1.2)
    hud_a = 1 - eo((t - b(MAIN_END + 4)) / 0.6)
    return F.finish(hud=(lambda img: HUD.draw(img, t, hud_a)) if hud_a > 0 else None, grain_seed=int(t * FPS))


def chunk(f0, f1, out):
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-threads", "2", "-crf", "14", "-pix_fmt", "yuv420p", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        p.stdin.write(render(fi / FPS).tobytes())
        if (fi - f0) % 150 == 0:
            print(f"[{out}] {fi}/{f1}", flush=True)
    p.stdin.close(); p.wait()


if __name__ == "__main__":
    if sys.argv[1] == "still":
        from PIL import Image
        for s_ in sys.argv[2].split(","):
            t = float(s_)
            Image.fromarray(render(t)).save(sys.argv[3].replace("%", f"{t:06.2f}"))
    else:
        chunk(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
