"""01 相关 ≠ 因果 · 02 可证伪性 · 03 伪科学的魔术。"""
import math

import numpy as np
import skia

import engine as E
import timeline as T
from engine import (W, H, CX, CY, INK, DIM, GREY, CYAN, GOLD, RED, GREEN, FIRE, clip01, ease, ease_out, ease_io, ease_in,
                    back_out, lerp, mixc, win, text, paint, line, arrow, rrect, glow_dot, check, cross)

s, e, at = T.s, T.e, T.at


def node(c, x, y, label, rgb, a, w=None, size=30, fill=0.10, sub=None):
    if a <= 0.003:
        return
    tw = w or E.measure(label, size, "serif_bold", 4) + 70
    h = 76 if sub is None else 96
    rrect(c, x - tw / 2, y - h / 2, tw, h, 18, paint(rgb, fill * a))
    rrect(c, x - tw / 2, y - h / 2, tw, h, 18, paint(rgb, 0.9 * a, stroke=2))
    rrect(c, x - tw / 2, y - h / 2, tw, h, 18, paint(rgb, 0.35 * a, stroke=6, blur=10))
    text(c, label, x, y - (12 if sub else 0), size, "serif_bold", INK, a, "c", 4)
    if sub:
        text(c, sub, x, y + 26, 17, "sans_light", DIM, a, "c", 2)


# ================================================================ 01 大脑是一台连线机器：把随机的星星连成星座
_r = np.random.default_rng(31)
CONST_N = 90
CONST_P = np.c_[220 + _r.random(CONST_N) * 1480, 150 + _r.random(CONST_N) * 700]
CONST_PH = _r.random(CONST_N) * 7
PAIRS = []
for k in range(60):
    i = int(_r.integers(CONST_N))
    d = np.hypot(*(CONST_P - CONST_P[i]).T)
    d[i] = 1e9
    j = int(np.argsort(d)[int(_r.integers(1, 3))])
    PAIRS.append((i, j, 51.6 + k * 0.105 + _r.random() * 0.2))


def scene_constellation(ctx):
    t, c = ctx.t, ctx.c
    a = win(t, T.SEC["cause"][0], s("c2") + 0.2, 0.4, 0.6)
    if a <= 0:
        return
    for i, (x, y) in enumerate(CONST_P):
        tw = 0.45 + 0.55 * max(0, math.sin(t * 2.2 + CONST_PH[i])) ** 6
        glow_dot(c, x, y, 2.6 + 1.5 * tw, INK, a * (0.35 + 0.65 * tw), 3.5)
    for (i, j, tt) in PAIRS:
        k = ease((t - tt) / 0.35)
        if k > 0:
            (x0, y0), (x1, y1) = CONST_P[i], CONST_P[j]
            line(c, x0, y0, x1, y1, CYAN, 0.55 * a, 1.6, k)
            if t - tt < 0.4:
                glow_dot(c, x0, y0, 5, CYAN, a * (1 - (t - tt) / 0.4), 4)
                glow_dot(c, x1, y1, 5, CYAN, a * (1 - (t - tt) / 0.4), 4)
    text(c, "星座：大脑在随机的星星之间「连线」", CX, 930, 22, "sans_light", DIM, a * ease((t - 53.5) / 0.8), "c", 3)


# ================================================================ 消防员散点图 → 混杂因素
_r = np.random.default_rng(7)
FIRE_N = 46
FSIZE = np.sort(_r.lognormal(0, 0.55, FIRE_N))
FIREMEN = np.clip(3 + 9 * FSIZE + _r.normal(0, 2.2, FIRE_N), 2, 40)
LOSS = np.clip(18 * FSIZE + _r.normal(0, 4.5, FIRE_N), 1, 80)
R_CORR = float(np.corrcoef(FIREMEN, LOSS)[0, 1])
FORD = _r.permutation(FIRE_N)
PX0, PY0, PW, PH = 170, 300, 640, 520     # 图表区域


FM_MAX, LS_MAX = float(FIREMEN.max() * 1.12), float(LOSS.max() * 1.12)


def _pt(fm, ls):
    return PX0 + fm / FM_MAX * PW, PY0 + PH - ls / LS_MAX * PH


def _flame(c, x, y, sc, t, a):
    for k, (col, s_) in enumerate(((FIRE, 1.0), ((1.0, 0.78, 0.3), 0.66), ((1.0, 0.95, 0.75), 0.36))):
        p = skia.Path()
        f = sc * s_
        wob = math.sin(t * 9 + k) * 0.08
        p.moveTo(x, y + 30 * f)
        p.cubicTo(x - 34 * f, y + 28 * f, x - 34 * f, y - 10 * f, x + (wob - 0.05) * 40 * f, y - 62 * f)
        p.cubicTo(x + 12 * f, y - 30 * f, x + 36 * f, y - 16 * f, x + 30 * f, y + 6 * f)
        p.cubicTo(x + 26 * f, y + 24 * f, x + 14 * f, y + 30 * f, x, y + 30 * f)
        c.drawPath(p, paint(col, a * (0.95 if k else 0.85), blur=1.5 if k else 3))
    c.drawCircle(x, y - 10 * sc, 70 * sc, paint(FIRE, 0.18 * a, blur=40 * sc))


def scene_scatter(ctx):
    t, c = ctx.t, ctx.c
    a = win(t, s("c2") - 0.3, s("c5") - 0.45, 0.6, 0.3)
    if a <= 0:
        return
    # 坐标轴
    ka = ease((t - s("c2") + 0.3) / 0.8)
    line(c, PX0, PY0 + PH, PX0 + PW, PY0 + PH, DIM, 0.7 * a, 2, ka)
    line(c, PX0, PY0 + PH, PX0, PY0, DIM, 0.7 * a, 2, ka)
    text(c, "到场消防员人数 →", PX0 + PW, PY0 + PH + 40, 20, "sans_reg", DIM, a * ka, "r", 2)
    text(c, "火灾损失 →", PX0 - 20, PY0 - 30, 20, "sans_reg", DIM, a * ka, "l", 2)
    conf = ease((t - at("c4", "火越大") - 0.2) / 1.0)     # 按火势着色：混杂因素现形
    for n, i in enumerate(FORD):
        k = back_out((t - s("c2") - 0.4 - n * 0.055) / 0.35)
        if k <= 0:
            continue
        x, y = _pt(FIREMEN[i], LOSS[i])
        fz = clip01((FSIZE[i] - 0.4) / 2.2)
        col = mixc(GOLD, mixc((1.0, 0.85, 0.35), (1.0, 0.25, 0.15), fz), conf)
        r = 7 * k * (1 + conf * (fz * 1.2 - 0.3))
        glow_dot(c, x, y, max(r, 0.5), col, a, 2.4)
    # 回归线
    kl = ease((t - s("c2") - 2.8) / 0.9)
    if kl > 0:
        m, b = np.polyfit(FIREMEN, LOSS, 1)
        x0, x1 = float(FIREMEN.min()), float(FIREMEN.max())
        (sx, sy), (ex, ey) = _pt(x0, m * x0 + b), _pt(x1, m * x1 + b)
        line(c, sx, sy, ex, ey, GOLD, 0.8 * a, 3, kl)
        text(c, f"r = {R_CORR:.2f}", PX0 + PW - 10, PY0 + 20, 30, "inter_light", GOLD, a * kl, "r")
        text(c, "高度相关", PX0 + PW - 10, PY0 + 58, 18, "sans_light", DIM, a * kl, "r", 2)
    if conf > 0:
        text(c, "颜色 / 大小 = 火势", PX0 + 10, PY0 + 20, 18, "sans_reg", FIRE, a * conf, "l", 2)
    # 因果图
    kc = ease((t - s("c3") + 0.1) / 0.6)
    if kc > 0:
        nx0, nx1, ny = 1120, 1620, 690
        node(c, nx0, ny, "消防员", CYAN, a * kc)
        node(c, nx1, ny, "损失", RED, a * kc)
        bad = ease((t - at("c4", "火越大") - 0.6) / 0.6)
        col = mixc(INK, RED, bad)
        if bad < 0.99:
            arrow(c, nx0, ny, nx1, ny, col, a * kc * (1 - 0.6 * bad), 3, ease((t - s("c3")) / 0.6), 18, 100, 80)
        else:
            c.drawLine(nx0 + 100, ny, nx1 - 80, ny, paint(RED, a * 0.5, stroke=3, dash=([10, 10], 0)))
        if bad > 0:
            cross(c, (nx0 + nx1) / 2, ny, 46, RED, a * bad, bad)
        q = ease((t - s("c3") - 0.4) / 0.4) * (1 - ease((t - s("c4")) / 0.3))
        text(c, "?", (nx0 + nx1) / 2, ny - 60, 72, "serif_black", GOLD, a * q, "c")
        # 火势：真正的原因
        kf = ease((t - at("c4", "火越大") + 0.2) / 0.7)
        if kf > 0:
            fx, fy = (nx0 + nx1) / 2, 400 - 40 * (1 - kf)
            _flame(c, fx, fy - 20, 1.0, t, a * kf)
            node(c, fx, fy + 80, "火势", FIRE, a * kf, sub="隐藏的第三因素")
            ka2 = ease((t - at("c4", "火越大") - 0.3) / 0.7)
            arrow(c, fx, fy + 80, nx0, ny, FIRE, a * kf, 3, ka2, 18, 60, 50)
            arrow(c, fx, fy + 80, nx1, ny, FIRE, a * kf, 3, ka2, 18, 60, 50)


def scene_neq(ctx):
    t, c = ctx.t, ctx.c
    a = win(t, s("c5") - 0.1, s("c6") - 0.3, 0.4, 0.3)
    if a <= 0:
        return
    k = ease_out((t - s("c5")) / 0.6)
    sc = lerp(1.15, 1.0, k)
    c.save()
    c.translate(CX, CY - 40)
    c.scale(sc, sc)
    text(c, "相关", -220, 0, 110, "serif_black", INK, a, "c", 8)
    text(c, "因果", 220, 0, 110, "serif_black", INK, a, "c", 8)
    text(c, "≠", 0, -6, 120, "inter_light", GOLD, a, "c", glow=0.8, glow_rgb=GOLD)
    c.restore()
    chips = ["隐藏的第三因素", "倒果为因", "纯属巧合"]
    for i, ch in enumerate(chips):
        kk = ease((t - s("c5") - 0.5 - i * 0.18) / 0.4)
        x = CX + (i - 1) * 300
        rrect(c, x - 120, CY + 100, 240, 54, 27, paint(INK, 0.3 * a * kk, stroke=1.5))
        text(c, ch, x, CY + 127, 22, "sans_reg", DIM, a * kk, "c", 2)


# ---- 随机对照实验
_r = np.random.default_rng(1747)
RCT_N = 160
AGE = _r.random(RCT_N)
HEALTH = _r.random(RCT_N)
GROUP = _r.permutation(np.r_[np.zeros(RCT_N // 2), np.ones(RCT_N // 2)]).astype(int)
ANG = _r.random(RCT_N) * math.tau
RAD = np.sqrt(_r.random(RCT_N))
SLOT = np.zeros((RCT_N, 2))
for g in (0, 1):
    idx = np.nonzero(GROUP == g)[0]
    for n, i in enumerate(idx):
        SLOT[i] = (n % 10, n // 10)
EFFECT = _r.random(RCT_N)


def scene_rct(ctx):
    t, c = ctx.t, ctx.c
    a = win(t, s("c6") + 0.05, T.SEC["cause"][1] - 0.2, 0.5, 0.4)
    if a <= 0:
        return
    t_coin = at("c6", "抛硬币")
    t_same = at("c6", "除了一件事")
    split = ease_io((t - t_coin - 0.6) / 1.4)
    k_in = ease((t - s("c6") + 0.2) / 0.8)
    # 硬币
    kc = win(t, t_coin - 0.4, t_coin + 1.8, 0.3, 0.4)
    if kc > 0:
        ph = (t - t_coin) * 16
        rx = 46 * abs(math.cos(ph))
        cy = 230 - 60 * math.sin(clip01((t - t_coin) / 1.2) * math.pi)
        c.drawOval(skia.Rect.MakeLTRB(CX - max(rx, 3), cy - 46, CX + max(rx, 3), cy + 46),
                   paint(GOLD if math.cos(ph) > 0 else GOLD_D, a * kc))
        c.drawOval(skia.Rect.MakeLTRB(CX - max(rx, 3), cy - 46, CX + max(rx, 3), cy + 46),
                   paint((1, 0.95, 0.8), 0.6 * a * kc, stroke=2))
    for i in range(RCT_N):
        # 起点：中央混合人群；终点：两组方阵
        x0 = CX + math.cos(ANG[i]) * RAD[i] * 300 * 1.3
        y0 = 560 + math.sin(ANG[i]) * RAD[i] * 220
        gx = (520 if GROUP[i] == 0 else 1400) + (SLOT[i][0] - 4.5) * 36
        gy = 470 + SLOT[i][1] * 36
        kk = ease((split * 1.3 - EFFECT[i] * 0.3))
        x, y = lerp(x0, gx, kk), lerp(y0, gy, kk)
        col = mixc((0.45, 0.75, 1.0), (0.80, 0.55, 1.0), HEALTH[i])
        healed = 0.0
        if GROUP[i] == 0:
            healed = ease((t - s("c7") - 0.2 - EFFECT[i] * 1.2) / 0.3) * (EFFECT[i] < 0.70)
        else:
            healed = ease((t - s("c7") - 0.2 - EFFECT[i] * 1.2) / 0.3) * (EFFECT[i] < 0.45)
        col = mixc(col, GREEN, healed)
        c.drawCircle(x, y, 7 + 5 * AGE[i], paint(col, a * k_in * 0.92))
    for g, gx, name in ((0, 520, "实验组"), (1, 1400, "对照组")):
        kl = ease((split - 0.6) / 0.4)
        text(c, name, gx, 400, 32, "serif_bold", INK, a * kl, "c", 8)
        # 组成对比
        ks = ease((t - t_same) / 0.6)
        if ks > 0:
            idx = GROUP == g
            for j, (lab, v) in enumerate((("平均年龄", AGE[idx].mean()), ("健康状况", HEALTH[idx].mean()))):
                y = 800 + j * 42
                text(c, lab, gx - 170, y, 18, "sans_light", DIM, a * ks, "l")
                rrect(c, gx - 80, y - 6, 240, 12, 6, paint(INK, 0.12 * a * ks))
                rrect(c, gx - 80, y - 6, 240 * v * ks, 12, 6, paint(CYAN, 0.8 * a * ks))
    # 唯一差别：新疗法
    kp = ease((t - at("c6", "除了一件事") - 0.5) / 0.6)
    if kp > 0:
        pulse = 0.5 + 0.5 * math.sin(t * 5)
        rrect(c, 520 - 210, 440, 420, 370, 28, paint(GOLD, a * kp * (0.6 + 0.3 * pulse), stroke=2.5))
        rrect(c, 520 - 210, 440, 420, 370, 28, paint(GOLD, a * kp * 0.3, stroke=8, blur=12))
        text(c, "＋ 唯一的差别：新疗法", 520, 900, 22, "sans_med", GOLD, a * kp, "c", 2)
    kr = ease((t - s("c7") - 1.2) / 0.6)
    if kr > 0:
        text(c, "70%", 520, 960, 44, "inter_light", GREEN, a * kr, "c")
        text(c, "45%", 1400, 960, 44, "inter_light", GREEN, a * kr, "c")
        text(c, "康复率（示意）", CX, 960, 20, "sans_light", DIM, a * kr, "c", 2)
        arrow(c, 760, 330, 1160, 330, GOLD, a * kr, 3, ease((t - s("c7") - 1.5) / 0.6), 18)
        text(c, "差异 = 因果", CX, 300, 26, "serif_bold", GOLD, a * kr, "c", 6)


GOLD_D = E.GOLD_D


# ================================================================ 02 可证伪性
def swan_path(x, y, sc, flip=False):
    pts = [("m", 5, 46), ("c", 20, 70, 60, 72, 80, 52), ("c", 88, 44, 86, 34, 78, 26), ("c", 70, 18, 72, 6, 84, 6),
           ("l", 98, 10), ("l", 86, 1), ("c", 70, -2, 60, 10, 68, 24), ("c", 74, 34, 70, 40, 58, 40),
           ("c", 40, 40, 22, 36, 5, 46)]
    p = skia.Path()
    f = -1 if flip else 1

    def P(u, v):
        return x + (u - 50) * sc * f, y + (v - 36) * sc
    for op in pts:
        if op[0] == "m":
            p.moveTo(*P(op[1], op[2]))
        elif op[0] == "l":
            p.lineTo(*P(op[1], op[2]))
        else:
            p.cubicTo(*P(op[1], op[2]), *P(op[3], op[4]), *P(op[5], op[6]))
    p.close()
    return p


def scene_proof(ctx):
    t, c = ctx.t, ctx.c
    a = win(t, s("f1") - 0.3, s("f2") + 0.2, 0.5, 0.5)
    if a > 0:
        k = ease_out((t - s("f1")) / 0.8)
        text(c, "实验", CX - 150, CY - 40, 96, "serif_black", INK, a, "c", 10, reveal=k)
        text(c, "＝", CX, CY - 40, 80, "inter_thin", DIM, a * k, "c")
        text(c, "证明？", CX + 190, CY - 40, 96, "serif_black", GOLD, a, "c", 10, reveal=ease((t - s("f1") - 0.9) / 0.8),
             shader=E.gold_shader(CY - 100, CY + 20))


SWAN_COLS, SWAN_ROWS = 25, 10


def scene_swans(ctx):
    t, c = ctx.t, ctx.c
    t0 = s("f2")
    t_black = at("f2", "一只黑天鹅")
    a = win(t, t0 - 0.2, s("f3") + 0.1, 0.5, 0.6)
    if a <= 0:
        return
    # 命题牌
    kb = ease((t - t_black - 0.6) / 0.5)
    plate_rgb = mixc(INK, RED, kb)
    shake = math.sin(t * 60) * 6 * math.exp(-max(0, t - t_black - 0.6) / 0.2) if t > t_black + 0.6 else 0
    rrect(c, CX - 330 + shake, 150, 660, 90, 20, paint(plate_rgb, 0.08 * a))
    rrect(c, CX - 330 + shake, 150, 660, 90, 20, paint(plate_rgb, 0.7 * a, stroke=2))
    text(c, "命题：所有天鹅都是白的", CX + shake, 195, 36, "serif_bold", plate_rgb, a, "c", 6)
    if kb > 0:
        c.drawLine(CX - 300, 160, CX + 300, 230, paint(RED, a * kb, stroke=4, trim=(0, kb)))
        text(c, "被推翻", CX + 420, 195, 30, "serif_black", RED, a * kb, "c", 6)
    # 白天鹅网格
    fill = ease_io((t - t0 - 0.2) / (t_black - t0 - 0.6))
    shown = int(fill * SWAN_COLS * SWAN_ROWS)
    dim = 1 - 0.75 * ease((t - t_black) / 0.6)
    for n in range(shown):
        gx, gy = n % SWAN_COLS, n // SWAN_COLS
        x = CX + (gx - (SWAN_COLS - 1) / 2) * 62
        y = 330 + gy * 52
        c.drawPath(swan_path(x, y, 0.42), paint(INK, 0.85 * a * dim))
    cnt = int(round(10000 * fill))
    kcnt = ease((t - t0) / 0.4) * (1 - ease((t - t_black) / 0.5))
    text(c, f"已观察 {cnt:,} 只白天鹅", CX, 880, 30, "sans_reg", INK, a * kcnt, "c", 3)
    text(c, "仍然无法证明命题", CX, 922, 20, "sans_light", DIM, a * kcnt * ease((fill - 0.6) / 0.3), "c", 3)
    # 黑天鹅
    kk = ease_out((t - t_black + 0.1) / 1.1)
    if kk > 0:
        x = lerp(W + 200, CX, kk)
        y = 600 + 6 * math.sin(t * 2)
        c.drawCircle(x, y, 260, paint((0.3, 0.1, 0.1), 0.35 * a * kk, blur=90))
        p = swan_path(x, y, 4.2, flip=False)
        c.drawPath(p, paint((0.03, 0.03, 0.05), a))
        c.drawPath(p, paint(GOLD, 0.8 * a, stroke=2.4))
        c.drawPath(p, paint(GOLD, 0.35 * a, stroke=8, blur=10))
        bx, by = x + (93 - 50) * 4.2, y + (6 - 36) * 4.2
        c.drawCircle(bx - 6, by + 4, 9, paint((0.95, 0.15, 0.2), a))
        kt = ease((t - t_black - 1.0) / 0.6)
        text(c, "1697 年 · 澳大利亚西部 · 荷兰探险队首次记录黑天鹅", CX, 920, 22, "sans_light", DIM, a * kt, "c", 2)
        text(c, "10,000 次证实  <  1 次证伪", CX, 870, 34, "inter_light", GOLD, a * kt, "c", 2)


# ---- 1919 日食
SUN = (760, 540)
SUN_R = 120


def _eclipse(c, t, a):
    x, y = SUN
    for i in range(48):
        ang = i * math.tau / 48 + 0.2 * math.sin(i * 1.7)
        L = SUN_R * (1.5 + 0.9 * abs(math.sin(i * 2.3 + 0.3)))
        c.drawLine(x + math.cos(ang) * SUN_R * 0.95, y + math.sin(ang) * SUN_R * 0.95, x + math.cos(ang) * L,
                   y + math.sin(ang) * L, paint((0.85, 0.9, 1.0), 0.10 * a, stroke=10, blur=14))
    c.drawCircle(x, y, SUN_R * 1.35, paint((0.8, 0.88, 1.0), 0.35 * a, blur=40))
    c.drawCircle(x, y, SUN_R * 1.08, paint((1, 1, 1), 0.7 * a, blur=10))
    c.drawCircle(x, y, SUN_R, paint((0.0, 0.0, 0.01), a))


def scene_eclipse(ctx):
    t, c = ctx.t, ctx.c
    a = win(t, s("f3") - 0.3, e("f5") + 0.5, 0.6, 0.6)
    if a <= 0:
        return
    _eclipse(c, t, a)
    text(c, "1919 年 5 月 29 日 · 日全食", SUN[0], SUN[1] + 230, 22, "sans_reg", DIM, a, "c", 3)
    # 星光路径：真实恒星 → 太阳附近弯折 → 地球；地球上看到的位置被“推”向外侧
    ky = ease((t - at("f3", "太阳会让星光") + 0.2) / 1.2)
    star = (140, 300)
    earth = (1500, 640)
    bend = (SUN[0] + 30, SUN[1] - SUN_R - 40)
    glow_dot(c, star[0], star[1], 6, INK, a, 4)
    text(c, "恒星的真实位置", star[0], star[1] - 40, 18, "sans_light", DIM, a, "c", 2)
    glow_dot(c, earth[0], earth[1], 10, CYAN, a, 3)
    text(c, "地球", earth[0], earth[1] + 40, 20, "sans_reg", CYAN, a, "c", 3)
    if ky > 0:
        p = skia.Path()
        p.moveTo(*star)
        p.quadTo(bend[0] - 80, bend[1] - 40, *bend)
        p.quadTo(bend[0] + 300, bend[1] + 40, *earth)
        c.drawPath(p, paint(GOLD, 0.9 * a, stroke=2.5, trim=(0, ky)))
        c.drawPath(p, paint(GOLD, 0.3 * a, stroke=8, blur=8, trim=(0, ky)))
    kap = ease((t - at("f3", "太阳会让星光") + 0.2 - 1.2) / 0.8)
    if kap > 0:
        # 从地球沿入射方向反推：看到的位置
        dx, dy = earth[0] - bend[0], earth[1] - bend[1]
        L = math.hypot(dx, dy)
        app = (earth[0] - dx / L * 1500, earth[1] - dy / L * 1500)
        c.drawLine(earth[0], earth[1], lerp(earth[0], app[0], kap), lerp(earth[1], app[1], kap),
                   paint(INK, 0.5 * a, stroke=1.5, dash=([8, 8], 0)))
        if kap > 0.95:
            glow_dot(c, app[0], app[1], 6, GOLD, a, 4)
        text(c, "看到的位置（向外偏移）", 300, 140, 18, "sans_light", GOLD, a * kap, "c", 2)
    # 刻度：0 / 0.87 / 1.75
    kg = ease((t - at("f3", "是牛顿") + 0.3) / 0.7)
    if kg > 0:
        gx0, gx1, gy = 1160, 1780, 860
        def X(v):
            return gx0 + v / 2.3 * (gx1 - gx0)
        line(c, gx0, gy, gx1, gy, INK, 0.5 * a * kg, 2)
        for v in (0, 0.5, 1.0, 1.5, 2.0):
            line(c, X(v), gy - 8, X(v), gy + 8, INK, 0.5 * a * kg, 1.5)
            text(c, f"{v:g}″", X(v), gy + 30, 16, "inter_light", DIM, a * kg)
        for v, lab, col in ((0.87, "牛顿 0.87″", GREY), (1.75, "爱因斯坦 1.75″", CYAN)):
            c.drawCircle(X(v), gy, 9, paint(col, a * kg))
            text(c, lab, X(v), gy - 34, 20, "sans_med", col, a * kg, "c", 2)
        kz = ease((t - s("f4") - 0.2) / 0.6) * (1 - 0.6 * ease((t - s("f5")) / 0.5))
        if kz > 0:
            rrect(c, X(0) - 26, gy - 26, 60, 52, 10, paint(RED, 0.25 * a * kz))
            text(c, "≈0″ → 相对论出局", X(0) + 10, gy + 70, 20, "sans_med", RED, a * kz, "l", 2)
        km = ease((t - s("f5") - 0.1) / 0.6)
        for v, err, lab, dy in ((1.98, 0.12, "索布拉尔 1.98″", -78), (1.61, 0.30, "普林西比 1.61″", -108)):
            if km > 0:
                yy = gy + dy + 60 * (1 - km)
                c.drawLine(X(v - err), yy, X(v + err), yy, paint(GOLD, a * km, stroke=2))
                glow_dot(c, X(v), yy, 6, GOLD, a * km, 3)
                text(c, lab, X(v) + 14, yy - 22, 17, "sans_reg", GOLD, a * km, "c", 1)
        text(c, "1919 年观测结果", gx0, gy - 170, 18, "sans_light", DIM, a * km, "l", 2)
    text(c, "偏折角度已放大示意", 1856, 1046, 15, "sans_light", GREY, 0.6 * a, "r", 1)


def scene_popper(ctx):
    t, c = ctx.t, ctx.c
    a = win(t, s("f6") - 0.2, e("f6") + 0.2, 0.5, 0.4)
    if a <= 0:
        return
    k1 = ease((t - s("f6")) / 1.0)
    text(c, "科学的力量，不在于被证明", CX, CY - 70, 56, "serif_bold", DIM, a, "c", 8, reveal=k1)
    t2 = at("f6", "而在于")
    text(c, "而在于——敢被推翻", CX, CY + 40, 76, "serif_black", INK, a, "c", 10, reveal=ease((t - t2) / 0.9),
         glow=0.35, glow_rgb=GOLD)
    text(c, "卡尔·波普尔 · 可证伪性（1934）", CX, CY + 150, 22, "sans_light", GOLD, a * ease((t - t2 - 0.6) / 0.6), "c", 4)


def _target(c, x, y, a, k=1.0, col=INK):
    for i, r in enumerate((110, 78, 46, 16)):
        c.drawCircle(x, y, r, paint(col if i % 2 == 0 else RED, a * (0.9 if i == 3 else 0.75), stroke=3,
                                    trim=(0, clip01(k * 1.4 - i * 0.12))))


def scene_targets(ctx):
    t, c = ctx.t, ctx.c
    a = win(t, s("f7") - 0.3, T.SEC["falsify"][1] - 0.1, 0.5, 0.35)
    if a <= 0:
        return
    t0 = s("f7")
    line(c, CX, 260, CX, 820, INK, 0.15 * a, 1.5)
    # 左：先画靶，再开枪
    lx, ly = 540, 560
    _target(c, lx, ly, a, ease((t - t0) / 0.8))
    ka = ease_in((t - t0 - 1.0) / 0.5, 2)
    if ka > 0:
        hx, hy = lx + 30, ly - 18
        sx, sy = lerp(lx - 420, hx, ka), lerp(ly + 60, hy, ka)
        c.drawLine(sx - 60, sy + 9, sx, sy, paint(GOLD, a, stroke=4))
        glow_dot(c, sx, sy, 5, GOLD, a, 3)
    text(c, "科学", lx, 300, 40, "serif_black", CYAN, a, "c", 10)
    text(c, "先画靶，再开枪 —— 可能会脱靶", lx, 760, 22, "sans_reg", DIM, a, "c", 2)
    # 右：先开枪，再画靶
    rx = 1380
    hits = [(1250, 430), (1520, 520), (1330, 650), (1470, 380)]
    for i, (hx, hy) in enumerate(hits):
        kh = ease_in((t - at("f7", "先开枪") - i * 0.25) / 0.35, 2)
        if kh > 0:
            sx, sy = lerp(hx - 300, hx, kh), lerp(hy + 40, hy, kh)
            c.drawLine(sx - 50, sy + 7, sx, sy, paint(GOLD, a, stroke=4))
            glow_dot(c, sx, sy, 4, GOLD, a, 3)
        kt = ease((t - at("f7", "再画靶") - i * 0.15) / 0.6)
        if kt > 0:
            for j, r in enumerate((70, 46, 22)):
                c.drawCircle(hx, hy, r, paint(INK if j % 2 == 0 else RED, a * 0.75, stroke=2.5,
                                              trim=(0, clip01(kt * 1.3 - j * 0.15))))
    text(c, "伪科学", rx, 300, 40, "serif_black", RED, a, "c", 10)
    text(c, "先开枪，再画靶 —— 永远「命中」", rx, 760, 22, "sans_reg", DIM, a, "c", 2)
    kq = ease((t - at("f7", "怎么说都对") + 0.1) / 0.5)
    text(c, "怎么说都对 ＝ 什么也没说", CX, 880, 30, "serif_bold", GOLD, a * kq, "c", 6)


# ================================================================ 03 伪科学的魔术
ZODIAC = ["白羊", "金牛", "双子", "巨蟹", "狮子", "处女", "天秤", "天蝎", "射手", "摩羯", "水瓶", "双鱼"]
MBTI = ["INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP",
        "ISFP", "ESTP", "ESFP"]


def scene_zodiac(ctx):
    t, c = ctx.t, ctx.c
    a = win(t, T.SEC["barnum"][0], s("m2") + 0.2, 0.4, 0.5)
    if a <= 0:
        return
    rot = t * 0.12
    for i, z in enumerate(ZODIAC):
        ang = rot + i * math.tau / 12
        x, y = CX + math.cos(ang) * 330, 530 + math.sin(ang) * 330
        text(c, z, x, y, 26, "serif_med", mixc(INK, (0.85, 0.65, 1.0), 0.5), a * 0.9, "c", 4)
    c.drawCircle(CX, 530, 380, paint((0.8, 0.6, 1.0), 0.25 * a, stroke=1.2))
    c.drawCircle(CX, 530, 280, paint((0.8, 0.6, 1.0), 0.25 * a, stroke=1.2))
    for i in range(12):
        ang = rot + (i + 0.5) * math.tau / 12
        line(c, CX + math.cos(ang) * 280, 530 + math.sin(ang) * 280, CX + math.cos(ang) * 380,
             530 + math.sin(ang) * 380, (0.8, 0.6, 1.0), 0.25 * a, 1.2)
    for i, m in enumerate(MBTI):
        gx, gy = i % 4, i // 4
        k = 0.5 + 0.5 * math.sin(t * 3 + i * 1.3)
        text(c, m, CX + (gx - 1.5) * 96, 530 + (gy - 1.5) * 52, 24, "inter_med", INK, a * (0.35 + 0.5 * k), "c", 2)


# 福勒实验：39 份「专属」分析
RATINGS = [5] * 16 + [4] * 18 + [3] * 4 + [2] * 1      # 平均 4.256 ≈ 4.26（分布为示意，均值为原始实验结果）
_r = np.random.default_rng(1948)
_r.shuffle(RATINGS)
FORER = ["你很需要别人喜欢和欣赏你。", "你有时外向、亲切、好交际，", "有时却内向、谨慎、沉默。",
         "你有许多尚未发挥出来的潜能。", "你对自己常常比较苛刻。"]


def _card(c, x, y, w, h, a, title, lines_=None, size=18, glow=0.0):
    rrect(c, x - w / 2, y - h / 2, w, h, 12, paint((0.10, 0.09, 0.16), 0.92 * a))
    rrect(c, x - w / 2, y - h / 2, w, h, 12, paint((0.8, 0.65, 1.0), 0.55 * a, stroke=1.5))
    if glow > 0:
        rrect(c, x - w / 2, y - h / 2, w, h, 12, paint(GOLD, glow * a, stroke=6, blur=12))
    text(c, title, x, y - h / 2 + 26, size, "sans_med", INK, a, "c", 1)
    if lines_:
        for i, l in enumerate(lines_):
            text(c, l, x - w / 2 + 40, y - h / 2 + 90 + i * 46, 26, "serif_med", INK, a, "l", 2)
    else:
        for i in range(3):
            rrect(c, x - w / 2 + 12, y - h / 2 + 46 + i * 14, w - 24 - i * 14, 5, 2.5, paint(INK, 0.25 * a))


def scene_forer(ctx):
    t, c = ctx.t, ctx.c
    t0 = s("m2")
    a = win(t, t0 - 0.2, e("m3") + 0.3, 0.5, 0.5)
    if a <= 0:
        return
    t_score = at("m2", "准确度打分")
    t_stack = s("m3") + 0.2
    stack = ease_io((t - t_stack) / 1.2)
    for i in range(39):
        gx, gy = i % 13, i // 13
        x0, y0 = CX + (gx - 6) * 128, 330 + gy * 128
        kk = back_out((t - t0 - 0.3 - i * 0.04) / 0.4)
        if kk <= 0:
            continue
        x, y = lerp(x0, CX + (i - 19) * 0.6, stack), lerp(y0, 560 + (i - 19) * 0.4, stack)
        w, h = lerp(112, 760, stack), lerp(110, 400, stack)
        if stack < 0.98 or i == 38:
            _card(c, x, y, w * kk, h * kk, a * (1 if stack < 0.98 else 1), f"No.{i + 1:02d}" if stack < 0.5 else
                  "每个人拿到的「专属分析」", FORER if (i == 38 and stack > 0.98) else None,
                  size=lerp(13, 26, stack), glow=0.0)
        # 评分
        ks = ease((t - t_score - i * 0.03) / 0.3) * (1 - stack)
        if ks > 0:
            text(c, "★" * RATINGS[i], x, y + 36, 13, "sans_reg", GOLD, a * ks, "c")
    km = ease((t - t_score - 1.3) / 0.6) * (1 - ease((t - t_stack) / 0.4))
    if km > 0:
        text(c, f"{lerp(0, 4.26, ease_out((t - t_score - 1.3) / 1.4)):.2f}", CX - 40, 800, 96, "inter_thin", GOLD, a * km, "r")
        text(c, "/ 5   平均准确度评分", CX - 20, 812, 28, "sans_reg", INK, a * km, "l", 2)
    kq = ease((t - t_stack - 1.1) / 0.6)
    text(c, "福勒（1948）给学生的原文节选 · 大多摘自一本星座书", CX, 800, 20, "sans_light", DIM, a * kq, "c", 2)
    text(c, "39 份「专属」分析，一字不差", CX, 230, 30, "serif_bold", GOLD, a * kq, "c", 6)


def scene_memory(ctx):
    t, c = ctx.t, ctx.c
    t0 = s("m4")
    a = win(t, t0 - 0.2, e("m4") + 0.2, 0.5, 0.4)
    if a <= 0:
        return
    text(c, "巴纳姆效应", 560, 300, 40, "serif_black", (0.85, 0.65, 1.0), a, "c", 8)
    text(c, "模糊的话，人人都能对号入座", 560, 352, 22, "sans_light", DIM, a, "c", 2)
    text(c, "确认偏误", 1360, 300, 40, "serif_black", GOLD, a * ease((t - at("m4", "说中的")) / 0.5), "c", 8)
    text(c, "说中的记住，说错的忘掉", 1360, 352, 22, "sans_light", DIM, a * ease((t - at("m4", "说中的")) / 0.5),
         "c", 2)
    # 左：一段模糊描述被投射到很多人身上
    for i in range(18):
        ang = i * math.tau / 18 + t * 0.2
        x, y = 560 + math.cos(ang) * 210, 610 + math.sin(ang) * 150
        k = ease((t - t0 - i * 0.05) / 0.4)
        line(c, 560, 610, x, y, (0.85, 0.65, 1.0), 0.25 * a * k, 1.2)
        c.drawCircle(x, y, 12, paint(INK, 0.8 * a * k))
        check(c, x, y - 30, 18, GREEN, a * ease((t - t0 - 0.8 - i * 0.05) / 0.3), 1.0, 3)
    _card(c, 560, 610, 200, 90, a, "「你需要被认可」")
    # 右：预测流进记忆，说错的消失
    ks = ease((t - at("m4", "说中的") + 0.2) / 0.4)
    if ks > 0:
        _r = np.random.default_rng(12)
        for i in range(14):
            ok = _r.random() < 0.45
            ph = ((t - at("m4", "说中的")) * 0.45 + i / 14) % 1.0
            x = 1110 + ph * 500
            y = 560 + (i % 5) * 60
            fade = 1.0 if ok else clip01(1 - (ph - 0.5) / 0.25)
            col = GREEN if ok else RED
            rrect(c, x - 40, y - 20, 80, 40, 10, paint(col, 0.18 * a * ks * fade))
            if ok:
                check(c, x, y, 22, GREEN, a * ks, 1.0, 3)
            else:
                cross(c, x, y, 18, RED, a * ks * fade, 1.0, 3)
        rrect(c, 1360 - 60, 500, 120, 330, 18, paint(INK, 0.25 * a * ks, stroke=1.5, dash=([6, 6], 0)))
        text(c, "记忆", 1360, 860, 20, "sans_reg", DIM, a * ks, "c", 4)


GATES = ["能被证伪吗？", "能被重复吗？", "有可测量的证据吗？", "会随新证据修正吗？"]
TOKENS = [("进化论", 4, CYAN, ""), ("黑洞理论", 4, CYAN, ""), ("星座", 0, RED, "怎么说都对，无法证伪"),
          ("MBTI", 1, RED, "相隔数周重测，常有近半数人类型改变"), ("平行宇宙", 0, GREY, "目前无法检验——不一定错，但暂不算科学")]


def scene_gates(ctx):
    t, c = ctx.t, ctx.c
    t0 = s("m5")
    a = win(t, t0 - 0.2, T.SEC["barnum"][1] - 0.1, 0.5, 0.35)
    if a <= 0:
        return
    keys = ["能被证伪", "能被重复", "有可测量", "会随新证据"]
    gx = [560, 860, 1160, 1460]
    kh = ease((t - t0) / 0.7)
    text(c, "科学的四道检验", CX, 180, 44, "serif_black", GOLD, a * kh, "c", 10, shader=E.gold_shader(150, 210))
    for i, (g, kk) in enumerate(zip(GATES, keys)):
        tg = at("m5", kk)
        k = 0.25 * ease((t - t0 - 0.2 - i * 0.15) / 0.6) + 0.75 * ease((t - tg + 0.15) / 0.5)
        x = gx[i]
        # 一道发光的拱门
        gate = skia.Path()
        gate.moveTo(x - 46, 760)
        gate.lineTo(x - 46, 420)
        gate.arcTo(skia.Rect.MakeLTRB(x - 46, 374, x + 46, 466), 180, 180, False)
        gate.lineTo(x + 46, 760)
        c.drawPath(gate, paint(CYAN, 0.06 * a * k))
        c.drawPath(gate, paint(CYAN, 0.9 * a * k, stroke=2.5, trim=(0, k)))
        c.drawPath(gate, paint(CYAN, 0.45 * a * k, stroke=8, blur=12, trim=(0, k)))
        text(c, f"0{i + 1}", x, 330, 22, "inter_med", GOLD, a * k, "c", 2)
        text(c, g, x, 290, 24, "sans_med", INK, a * k, "c", 1)
    t_run = e("m5") + 0.1
    for j, (name, passed, col, note) in enumerate(TOKENS):
        y = 420 + j * 72
        kin = ease((t - t_run - j * 0.12) / 0.4)
        if kin <= 0:
            continue
        prog = ease_io((t - t_run - j * 0.12) / 1.6)
        stop_x = gx[passed] - 70 if passed < 4 else 1700
        x = lerp(250, stop_x, prog)
        tw = E.measure(name, 24, "sans_med", 2) + 40
        rrect(c, x - tw / 2, y - 22, tw, 44, 22, paint(col, 0.18 * a * kin))
        rrect(c, x - tw / 2, y - 22, tw, 44, 22, paint(col, 0.8 * a * kin, stroke=1.5))
        text(c, name, x, y, 24, "sans_med", INK, a * kin, "c", 2)
        for g in range(4):
            if passed > g and x > gx[g]:
                check(c, gx[g] + 26, y - 26, 18, GREEN, a * kin, 1.0, 3)
        if passed < 4 and prog > 0.98:
            if col == GREY:
                text(c, "？", gx[passed] + 24, y, 30, "sans_bold", GREY, a, "c")
            else:
                cross(c, gx[passed] + 24, y, 22, RED, a, ease((t - t_run - j * 0.12 - 1.6) / 0.3), 3.5)
            text(c, note, gx[passed] + 50, y, 18, "sans_light", DIM, a * ease((t - t_run - j * 0.12 - 1.7) / 0.4),
                 "l", 1)
        if passed == 4 and prog > 0.98:
            check(c, x + tw / 2 + 26, y, 26, GREEN, a, ease((t - t_run - j * 0.12 - 1.6) / 0.3), 4)


SCENES = [
    (T.SEC["cause"][0], s("c2") + 1.0, scene_constellation),
    (s("c2") - 0.3, s("c5") + 0.5, scene_scatter),
    (s("c5") - 0.1, s("c6") + 0.9, scene_neq),
    (s("c6") - 0.2, T.SEC["cause"][1], scene_rct),
    (s("f1") - 0.3, s("f2") + 0.8, scene_proof),
    (s("f2") - 0.2, s("f3") + 0.8, scene_swans),
    (s("f3") - 0.3, e("f5") + 1.2, scene_eclipse),
    (s("f6") - 0.2, e("f6") + 0.7, scene_popper),
    (s("f7") - 0.3, T.SEC["falsify"][1], scene_targets),
    (T.SEC["barnum"][0], s("m2") + 0.8, scene_zodiac),
    (s("m2") - 0.2, e("m3") + 0.9, scene_forer),
    (s("m4") - 0.2, e("m4") + 0.7, scene_memory),
    (s("m5") - 0.2, T.SEC["barnum"][1], scene_gates),
]
