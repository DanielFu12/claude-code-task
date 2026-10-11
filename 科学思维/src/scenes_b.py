"""01 相关 ≠ 因果 · 02 可证伪 · 03 我们为什么会信。

主线不变：还是你的「8」。牛市这阵风把所有股票都吹涨了 → 对照组一摆，8 什么也没做 → 医学的随机对照实验；
8 让你亏钱时你总有借口 → 科学敢事先说出“怎样算我错” → 1919 年日食；记忆只留下 8 的高光 → 四个问题。
"""
import math

import numpy as np
import skia

import engine as E
import timeline as T
from engine import (CX, CY, INK, DIM, GREY, CYAN, GOLD, UP, DOWN, clip01, ease, ease_out, ease_io, ease_in,
                    lerp, mixc, text, paint, line, arrow, rrect, glow_dot, check, cross, cutin, punch)
from scenes_a import bt, zoomed, big_line

s, e, at = T.s, T.e, T.at
B = T.BEAT
RED = UP
GOLD_D = E.GOLD_D


# ================================================================ 01 相关 ≠ 因果
def scene_c1(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("c1"), s("c2")
    a = cutin(t, t0, t1 + 0.02, 0.0, 0.02)
    if a <= 0:
        return
    k = ease_out((t - t0) / 0.3, 3)
    c.save()
    c.translate(CX - 120, 470)
    c.scale(lerp(1.9, 1.5, k), lerp(1.9, 1.5, k))
    E.trade_card(c, 0, 0, a, "•••888", 30.2, t, 500, 170, "你的第 1 笔 · 买入", glow=0.3, seed=3)
    c.restore()
    tq = bt("c1", 2)
    if t >= tq:
        E.slam(c, "？", CX + 560, 450, 300, t, tq, "serif_black", GOLD, a, shader=E.gold_shader(-160, 110),
               glow=0.6, glow_rgb=GOLD)
        E.burst(ctx, t, tq, CX + 560, 450, GOLD, 300, 900, 0.7, a)


INDEX = E.walk(80, 2015, 0.05, 0.05, 0.10, 0.88)


def scene_c2(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("c2"), s("c3")
    a = cutin(t, t0, t1 + 0.02, 0.0, 0.02)
    if a <= 0:
        return
    k = ease_io((t - t0) / (3 * B))
    gx0, gy0, gw, gh = 200, 200, 1520, 600
    for i in range(6):
        line(c, gx0, gy0 + i * gh / 5, gx0 + gw, gy0 + i * gh / 5, INK, 0.05 * a, 1)
    E.spark(c, gx0, gy0, gw, gh, INDEX, RED, a, k, 4, fill=True)
    E.slam(c, "大盘", gx0 + 10, gy0 - 40, 56, t, t0, "serif_black", INK, a, 8, align="l")
    text(c, "那一年 · 指数走势（示意）", gx0 + 150, gy0 - 36, 24, "sans_reg", DIM, a, "l", 2)
    # 你的那笔交易：缩成大盘上的一个小点
    i_buy = 46
    px, py = gx0 + gw * i_buy / 79, gy0 + gh * (1 - INDEX[i_buy])
    kd = ease_out((t - t0) / 0.5, 3)
    if k * 79 >= i_buy - 2:
        glow_dot(c, px, py, 9, GOLD, a, 4)
        E.code_text(c, "•••888", px, py - 46, 30, a * kd, "c")


_r = np.random.default_rng(78)
WALL = [("•••" + "".join(str(d) for d in _r.integers(0, 10, 3)), 3 + _r.random() * 40) for _ in range(80)]
WALL_ORDER = _r.permutation(80)


def scene_c3(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("c3"), s("c4")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    for i, (code, pct) in enumerate(WALL):
        x = 245 + (i % 10) * 159
        y = 215 + (i // 10) * 86
        tf = t0 + WALL_ORDER[i] / 80 * 4 * B
        f = ease_out((t - tf) / 0.12)
        col = mixc(GREY, RED, f)
        rrect(c, x - 72, y - 34, 144, 68, 10, paint(col, (0.06 + 0.10 * f) * a))
        rrect(c, x - 72, y - 34, 144, 68, 10, paint(col, (0.2 + 0.5 * f) * a, stroke=1.2))
        text(c, code, x, y - 12, 22, "mono", DIM, a, "c")
        text(c, f"+{pct * f:.1f}%", x, y + 16, 22, "inter_bold", col, a, "c")
    rrect(c, CX - 300, 380, 600, 230, 30, paint((0.02, 0.01, 0.01), 0.75 * a, blur=30))
    E.slam(c, "牛市", CX, 490, 200, t, t0, "serif_black", RED, a, 30, glow=0.6, glow_rgb=RED)
    E.burst(ctx, t, t0, CX, 490, RED, 700, 1600, 1.0, a)


WIND_N = 46
_r = np.random.default_rng(4)
WIND = _r.random((WIND_N, 4))
LINES = [E.walk(40, 100 + i, 0.06, 0.07) for i in range(26)]


def scene_c4(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("c4"), s("c5")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    # 风：流线从左往右
    for (y0, ph, sp, ln) in WIND:
        y = 160 + y0 * 720
        x = ((t * (500 + 700 * sp) + ph * 2400) % 2400) - 300
        L = 120 + 260 * ln
        p = skia.Path()
        for j in range(12):
            xx = x - L * j / 11
            yy = y + 18 * math.sin(xx * 0.006 + y0 * 9) - (xx / 1920) * 60
            (p.moveTo if j == 0 else p.lineTo)(xx, yy)
        c.drawPath(p, paint((1.0, 0.85, 0.75), 0.18 * a, stroke=2, blur=1))
    # 所有股票一起被吹高
    k = ease_io((t - t0) / (5 * B))
    for i, v in enumerate(LINES):
        y0 = 260 + (i % 13) * 34
        E.spark(c, 260, y0 - 150, 1400, 380, v, mixc(RED, (0.6, 0.4, 0.45), 0.5), 0.35 * a, k, 1.6, fill=False)
    gold = E.walk(40, 888, 0.06, 0.07)
    E.spark(c, 260, 110, 1400, 380 + 140, gold, GOLD, a, k, 5, fill=False)
    if k > 0.5:
        E.code_text(c, "•••888", 260 + 1400 * k + 20, 120 + 520 * (1 - gold[int(39 * k)]), 30, a, "l")
    tl = bt("c4", 4)
    if t >= tl:
        E.slam(c, "同一阵风：牛市", CX, 840, 64, t, tl, "serif_black", INK, a, 10, glow=0.3, glow_rgb=RED)


def scene_c5(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("c5"), s("c6")
    a = cutin(t, t0, t1 + 0.02, 0.0, 0.02)
    if a <= 0:
        return
    E.slam(c, "相关", CX - 290, CY - 30, 150, t, t0, "serif_black", INK, a, 10)
    E.slam(c, "因果", CX + 290, CY - 30, 150, t, t0 + B / 2, "serif_black", INK, a, 10)
    tn = t0 + B
    if t >= tn:
        E.slam(c, "≠", CX, CY - 40, 190, t, tn, "inter_light", GOLD, a, glow=0.9, glow_rgb=GOLD)
        E.burst(ctx, t, tn, CX, CY - 40, GOLD, 600, 1500, 0.9, a)
    tb = t0 + 2 * B
    if t >= tb:
        text(c, "一起出现，不代表谁导致了谁", CX, CY + 140, 36, "sans_med", DIM, a * ease_out((t - tb) / 0.25), "c", 6)


_r = np.random.default_rng(808)


def _codes(with8, n):
    out = []
    while len(out) < n:
        d = "".join(str(x) for x in _r.integers(0, 10, 3))
        if ("8" in d) == with8:
            out.append("•••" + d)
    return out


CODES8, CODES_O = _codes(True, 12), _codes(False, 12)


def scene_c67(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("c6"), s("c8")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    t_ctrl = at("c6", "同一时期")
    t_bar = at("c6", "不带 8")
    t7 = s("c7")
    dead = ease_out((t - at("c7", "8，什么")) / 0.3) if t >= at("c7", "8，什么") else 0.0
    for side, (cx, codes, title, col) in enumerate(((620, CODES8, "带 8 的股票", GOLD), (1300, CODES_O, "不带 8 的股票", CYAN))):
        ts = t0 if side == 0 else t_ctrl
        if t < ts:
            continue
        kk = ease_out((t - ts) / 0.25, 3)
        cc = mixc(col, GREY, dead) if side == 0 else col
        E.glass(c, cx - 300, 170, 600, 620, 26, a * kk, edge=cc, edge_a=0.5, glow=0.25 * (1 - dead) if side == 0 else 0)
        E.slam(c, title, cx, 230, 40, t, ts, "serif_black", cc, a, 6)
        if side == 1:
            text(c, "对照组", cx, 280, 24, "sans_med", DIM, a * kk, "c", 6)
        for j, code in enumerate(codes):
            tj = ts + j * B / 8
            kj = ease_out((t - tj) / 0.15)
            x = cx - 200 + (j % 3) * 200
            y = 340 + (j // 3) * 52
            if side == 0:
                E.code_text(c, code, x, y, 28, a * kj * (1 - 0.5 * dead), "c", glow=0.5 * (1 - dead))
            else:
                text(c, code, x, y, 28, "mono", INK, a * kj, "c")
        # 同期涨幅（示意）
        target = 31.0 if side == 0 else 30.0
        kb = ease_io((t - t_bar) / (3 * B))
        h = 130 * kb
        rrect(c, cx - 90, 740 - h, 180, h, 10, paint(RED, 0.75 * a))
        rrect(c, cx - 90, 740 - h, 180, h, 10, paint(RED, 0.4 * a, blur=12))
        if kb > 0.02:
            text(c, f"+{target * kb:.0f}%", cx, 740 - h - 36, 46, "inter_bold", RED, a, "c")
    if t >= t_bar:
        text(c, "同期涨幅（示意）", CX - 20, 770, 22, "sans_reg", GREY, a, "c", 2)
    t8 = at("c7", "8，什么")
    if t7 <= t < t8:
        E.slam(c, "差不多。", CX - 20, 860, 60, t, t7, "serif_black", INK, a, 8)
    if t >= t8:
        E.slam(c, "8，什么也没做", CX - 20, 860, 60, t, t8, "serif_black", GOLD, a, 10,
               shader=E.gold_shader(-36, 26), glow=0.3, glow_rgb=GOLD)


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
    for n, i in enumerate(np.nonzero(GROUP == g)[0]):
        SLOT[i] = (n % 10, n // 10)
EFFECT = _r.random(RCT_N)


def _capsule(c, x, y, L, w, ang, a, col1=GOLD, col2=(0.95, 0.95, 1.0)):
    c.save()
    c.translate(x, y)
    c.rotate(ang)
    rrect(c, -L / 2, -w / 2, L, w, w / 2, paint(col2, a))
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(-L / 2 - 2, -w, 0, w))
    rrect(c, -L / 2, -w / 2, L, w, w / 2, paint(col1, a))
    c.restore()
    c.drawLine(0, -w / 2, 0, w / 2, paint((0, 0, 0), 0.3 * a, stroke=2))
    rrect(c, -L / 2 + 8, -w / 2 + 6, L - 16, 6, 3, paint((1, 1, 1), 0.35 * a))
    c.restore()


def scene_c8(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("c8"), s("c9")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    text(c, "医学把这一招用到了极致", CX, 300, 34, "sans_med", DIM, a * ease_out((t - t0) / 0.25), "c", 8)
    tb = t0 + 2 * B
    if t >= tb:
        E.slam(c, "随机对照实验", CX, 470, 120, t, tb, "serif_black", INK, a, 16, glow=0.3, glow_rgb=CYAN)
        text(c, "R A N D O M I Z E D   C O N T R O L L E D   T R I A L", CX, 580, 24, "inter_light", CYAN,
             a * ease_out((t - tb - 0.2) / 0.3), "c", 2)
        k = ease_out((t - tb) / 0.5)
        _capsule(c, CX - 380, 740, 150, 56, -30 + 8 * math.sin(t * 2), a * k)
        _capsule(c, CX + 380, 740, 150, 56, 30 + 8 * math.sin(t * 2 + 1), a * k, col1=(0.85, 0.87, 0.95))
        text(c, "药", CX - 380, 820, 24, "sans_med", GOLD, a * k, "c")
        text(c, "安慰剂", CX + 380, 820, 24, "sans_med", DIM, a * k, "c")


def scene_rct(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("c9"), T.SEC["cause"][1]
    a = cutin(t, t0, t1 + 0.02, 0.0, 0.02)
    if a <= 0:
        return
    t_coin = t0
    t_same = at("c9", "除了")
    t_res = s("c10")
    split = ease_io((t - t_coin - 2 * B) / (3 * B))
    kc = cutin(t, t_coin, t_coin + 2.4, 0.05, 0.3)
    if kc > 0:
        ph = (t - t_coin) * 16
        rx = 56 * abs(math.cos(ph))
        cy = 200 - 70 * math.sin(clip01((t - t_coin) / (2 * B)) * math.pi)
        c.drawOval(skia.Rect.MakeLTRB(CX - max(rx, 3), cy - 56, CX + max(rx, 3), cy + 56),
                   paint(GOLD if math.cos(ph) > 0 else GOLD_D, a * kc))
        c.drawOval(skia.Rect.MakeLTRB(CX - max(rx, 3), cy - 56, CX + max(rx, 3), cy + 56),
                   paint((1, 0.95, 0.8), 0.6 * a * kc, stroke=2))
        text(c, "抛硬币分组", CX, 290, 26, "sans_med", GOLD, a * kc, "c", 6)
    for i in range(RCT_N):
        x0 = CX + math.cos(ANG[i]) * RAD[i] * 300 * 1.3
        y0 = 560 + math.sin(ANG[i]) * RAD[i] * 220
        gx = (520 if GROUP[i] == 0 else 1400) + (SLOT[i][0] - 4.5) * 36
        gy = 470 + SLOT[i][1] * 36
        kk = ease((split * 1.3 - EFFECT[i] * 0.3))
        x, y = lerp(x0, gx, kk), lerp(y0, gy, kk)
        col = mixc((0.45, 0.75, 1.0), (0.80, 0.55, 1.0), HEALTH[i])
        thr = 0.70 if GROUP[i] == 0 else 0.45
        healed = ease((t - t_res - EFFECT[i] * 1.0) / 0.25) * (EFFECT[i] < thr)
        col = mixc(col, RED, healed)
        c.drawCircle(x, y, 7 + 5 * AGE[i], paint(col, a * 0.92))
    for g, gx, name in ((0, 520, "药物组"), (1, 1400, "安慰剂组")):
        kl = ease((split - 0.6) / 0.4)
        text(c, name, gx, 400, 36, "serif_black", INK, a * kl, "c", 8)
        if t >= t_same:
            ks = ease_out((t - t_same) / 0.4)
            idx = GROUP == g
            for j, (lab, v) in enumerate((("平均年龄", AGE[idx].mean()), ("健康状况", HEALTH[idx].mean()))):
                y = 790 + j * 40
                text(c, lab, gx - 170, y, 22, "sans_light", DIM, a * ks, "l")
                rrect(c, gx - 60, y - 6, 220, 12, 6, paint(INK, 0.12 * a * ks))
                rrect(c, gx - 60, y - 6, 220 * v * ks, 12, 6, paint(CYAN, 0.8 * a * ks))
    if t >= t_same:
        ks = ease_out((t - t_same) / 0.3)
        text(c, "其余全都一样 —— 唯一的差别：药，还是安慰剂", CX, 300, 28, "sans_med", GOLD, a * ks, "c", 2)
    if t >= t_res:
        kr = ease_out((t - t_res - 0.6) / 0.4)
        text(c, "70%", 520, 330, 56, "inter_bold", RED, a * kr, "c", glow=0.4, glow_rgb=RED)
        text(c, "45%", 1400, 330, 56, "inter_bold", RED, a * kr, "c")
        text(c, "好转（示意）", CX, 330, 24, "sans_reg", DIM, a * kr, "c", 2)
        tb = t_res + 2 * B
        if t >= tb:
            rrect(c, CX - 280, 830, 560, 90, 24, paint((0.02, 0.02, 0.04), 0.85 * a))
            E.slam(c, "差异 → 原因", CX, 875, 60, t, tb, "serif_black", GOLD, a, 10, shader=E.gold_shader(-36, 26),
                   glow=0.4, glow_rgb=GOLD)


# ================================================================ 02 可证伪：8 让你亏钱时
CRASH = E.make_ohlc(30, 7, drift=-1.4, vol=2.2, start=20)


def scene_f1(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("f1"), s("f2")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    E.candles(c, 160, 200, 1600, 560, CRASH, k=ease_out((t - t0) / (3 * B), 2), a=0.55 * a)
    c.save()
    c.translate(CX, 470)
    k = ease_out((t - t0 - B) / 0.22, 3)
    if t >= t0 + B:
        c.scale(lerp(1.8, 1.4, k), lerp(1.8, 1.4, k))
        E.trade_card(c, 0, 0, a, "•••888", -18.4, t, 500, 170, "第 4 笔 · 买入", glow=0.6 * math.exp(-(t - t0 - B) / 0.3),
                     seed=11)
    c.restore()


def bubble(c, x, y, txt, a, t, t0, size=52, col=INK):
    """对话气泡：从尾巴处弹出。"""
    if t < t0 or a <= 0.003:
        return
    k = E.pop((t - t0) / 0.28)
    tw = E.measure(txt, size, "serif_black", 6) + 90
    h = size + 70
    c.save()
    c.translate(x, y)
    c.scale(k, k)
    E.glass(c, -tw / 2, -h / 2, tw, h, h / 2, a, edge=col, edge_a=0.5, fill=(0.07, 0.08, 0.12))
    p = skia.Path()
    p.moveTo(-tw * 0.25, h / 2 - 2)
    p.lineTo(-tw * 0.35, h / 2 + 40)
    p.lineTo(-tw * 0.12, h / 2 - 2)
    p.close()
    c.drawPath(p, paint((0.07, 0.08, 0.12), 0.82 * a))
    text(c, txt, 0, 0, size, "serif_black", col, a, "c", 6)
    c.restore()


def scene_f23(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("f2"), s("f4")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    c.save()
    c.translate(520, 640)
    c.scale(1.2, 1.2)
    E.trade_card(c, 0, 0, a, "•••808", -18.4, t, 500, 170, "第 4 笔", seed=11)
    c.restore()
    bubble(c, 640, 330, "这只的 8 不够多", a, t, t0, col=GOLD)
    t3 = s("f3")
    if t >= t3:
        k = ease_out((t - t3) / 0.22, 3)
        c.save()
        c.translate(1400, 640)
        c.scale(lerp(1.6, 1.2, k), lerp(1.6, 1.2, k))
        E.trade_card(c, 0, 0, a, "•••188", -11.2, t, 500, 170, "第 5 笔", glow=0.5 * math.exp(-(t - t3) / 0.3),
                     seed=13)
        c.restore()
        bubble(c, 1420, 330, "是买的日子不对", a, t, t3 + B / 2, col=GOLD)


def scene_f4(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("f4"), s("f5")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    # 一台「永远正确」的机器：涨也灵，跌也灵
    mx, my = CX, 430
    E.glass(c, mx - 230, my - 110, 460, 220, 30, a, edge=GOLD, edge_a=0.7, glow=0.3)
    E.code_text(c, "8", mx - 110, my, 110, a, "c", glow=1.0)
    text(c, "很灵", mx + 60, my, 72, "serif_black", INK, a, "c", 8)
    ins = [("涨了", RED, "→ 8 灵验"), ("跌了", DOWN, "→ 8 不够多"), ("又跌", DOWN, "→ 日子不对"), ("大涨", RED, "→ 8 灵验")]
    for j, (lab, col, out) in enumerate(ins):
        tj = t0 + j * B
        if t < tj:
            continue
        k = ease_in(clip01((t - tj) / (B * 0.9)), 2)
        y = my - 75 + (j % 2) * 150
        x = lerp(220, mx - 260, k)
        al = a * (1 - ease((k - 0.85) / 0.15))
        rrect(c, x - 70, y - 30, 140, 60, 30, paint(col, 0.85 * al))
        text(c, lab, x, y, 28, "sans_bold", (1, 1, 1), al, "c", 2)
        ko = ease_out((t - tj - B * 0.9) / 0.2)
        if ko > 0:
            yo = my - 120 + j * 80
            check(c, 1310, yo, 34, GOLD, a * ko, 1.0, 4)
            text(c, out, 1350, yo, 36, "serif_bold", GOLD, a * ko, "l", 2)
    tb = bt("f4", 4)
    if t >= tb:
        rrect(c, CX - 640, 720, 1280, 220, 30, paint((0.02, 0.02, 0.04), 0.8 * a, blur=20))
        E.slam(c, "怎么都不会错的说法", CX, 770, 64, t, tb, "serif_black", INK, a, 10)
        tb2 = tb + 2 * B
        if t >= tb2:
            E.slam(c, "其实什么也没说", CX, 870, 64, t, tb2, "serif_black", GOLD, a, 10, shader=E.gold_shader(-38, 28),
                   glow=0.4, glow_rgb=GOLD)


def scene_f5(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("f5"), s("f6")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    E.slam(c, "科学恰恰相反", CX, 220, 64, t, t0, "serif_black", CYAN, a, 12, glow=0.3, glow_rgb=CYAN)
    tc = at("f5", "它敢事先")
    if t >= tc:
        k = ease_out((t - tc) / 0.3, 3)
        x0, y0, w, h = CX - 520, 320, 1040, 460
        E.glass(c, x0, y0 + 40 * (1 - k), w, h, 26, a * k, edge=CYAN, edge_a=0.5)
        text(c, "事先写下：", x0 + 60, y0 + 80, 30, "sans_med", DIM, a * k, "l", 4)
        t1_ = tc + B
        text(c, "如果出现 ______", x0 + 60, y0 + 190, 56, "serif_black", INK, a, "l", 6,
             reveal=ease((t - t1_) / (1.2 * B)))
        t2_ = at("f5", "怎样就算")
        text(c, "我就错了。", x0 + 60, y0 + 300, 72, "serif_black", GOLD, a, "l", 8, reveal=ease((t - t2_) / B),
             glow=0.4, glow_rgb=GOLD)
        ts = t2_ + 2 * B
        if t >= ts:
            ks = ease_out((t - ts) / 0.2, 3)
            c.save()
            c.translate(x0 + w - 160, y0 + h - 110)
            c.rotate(-12)
            c.scale(lerp(2, 1, ks), lerp(2, 1, ks))
            rrect(c, -110, -50, 220, 100, 14, paint(CYAN, 0.9 * a * ks, stroke=6))
            text(c, "可证伪", 0, 0, 44, "serif_black", CYAN, a * ks, "c", 4)
            c.restore()


# ---- 1919 日食
SUN = (720, 520)
SUN_R = 120


def _eclipse(c, t, a, x=SUN[0], y=SUN[1]):
    for i in range(48):
        ang = i * math.tau / 48 + 0.2 * math.sin(i * 1.7) + t * 0.02
        L = SUN_R * (1.5 + 0.9 * abs(math.sin(i * 2.3 + 0.3)))
        c.drawLine(x + math.cos(ang) * SUN_R * 0.95, y + math.sin(ang) * SUN_R * 0.95, x + math.cos(ang) * L,
                   y + math.sin(ang) * L, paint((0.85, 0.9, 1.0), 0.10 * a, stroke=10, blur=14))
    c.drawCircle(x, y, SUN_R * 1.35, paint((0.8, 0.88, 1.0), 0.35 * a, blur=40))
    c.drawCircle(x, y, SUN_R * 1.08, paint((1, 1, 1), 0.7 * a, blur=10))
    c.drawCircle(x, y, SUN_R, paint((0.0, 0.0, 0.01), a))


def scene_eclipse(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("f6"), s("f9")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    zoomed(c, CX, 520, punch(t, t0, 0.08) * (1 + 0.03 * (t - t0) / 12))
    _eclipse(c, t, a)
    text(c, "爱因斯坦 · 广义相对论的预言", 160, 170, 30, "serif_bold", INK, a * ease_out((t - t0) / 0.3), "l", 4)
    star = (140, 320)
    earth = (1560, 470)
    bend = (SUN[0] + 30, SUN[1] - SUN_R - 40)
    glow_dot(c, star[0], star[1], 6, INK, a, 4)
    text(c, "恒星", star[0], star[1] - 40, 22, "sans_reg", DIM, a, "c", 2)
    glow_dot(c, earth[0], earth[1], 10, CYAN, a, 3)
    text(c, "地球", earth[0], earth[1] + 44, 24, "sans_reg", CYAN, a, "c", 3)
    ky = ease((t - t0 - 0.2) / (3 * B))
    if ky > 0:
        p = skia.Path()
        p.moveTo(*star)
        p.quadTo(bend[0] - 80, bend[1] - 40, *bend)
        p.quadTo(bend[0] + 300, bend[1] + 40, *earth)
        c.drawPath(p, paint(GOLD, 0.9 * a, stroke=2.5, trim=(0, ky)))
        c.drawPath(p, paint(GOLD, 0.3 * a, stroke=8, blur=8, trim=(0, ky)))
    # 刻度：0 / 0.87 / 1.75
    gx0, gx1, gy = 1080, 1780, 820

    def X(v):
        return gx0 + v / 2.3 * (gx1 - gx0)
    kg = ease_out((t - at("f6", "1.75") + 0.1) / 0.4)
    if kg > 0:
        line(c, gx0, gy, gx1, gy, INK, 0.5 * a * kg, 2)
        for v in (0, 0.5, 1.0, 1.5, 2.0):
            line(c, X(v), gy - 8, X(v), gy + 8, INK, 0.5 * a * kg, 1.5)
            text(c, f"{v:g}″", X(v), gy + 32, 22, "inter_light", DIM, a * kg)
        c.drawCircle(X(1.75), gy, 11, paint(CYAN, a * kg))
        text(c, "爱因斯坦 1.75″", X(1.75), gy - 38, 26, "sans_bold", CYAN, a * kg, "c", 2)
        tn = at("f6", "是牛顿")
        if t >= tn:
            kn = ease_out((t - tn) / 0.25)
            c.drawCircle(X(0.87), gy, 9, paint(GREY, a * kn))
            text(c, "牛顿 0.87″", X(0.87), gy - 38, 24, "sans_med", GREY, a * kn, "c", 2)
            text(c, "×2", (X(0.87) + X(1.75)) / 2, gy - 90, 40, "inter_bold", GOLD, a * kn, "c", glow=0.4)
    # f7：只要没偏，就出局
    t7 = s("f7")
    if t >= t7:
        k7 = ease_out((t - t7) / 0.3)
        text(c, "1919 年 5 月 29 日 · 日全食", SUN[0], SUN[1] + 230, 26, "sans_med", INK, a * k7, "c", 4)
        tz = at("f7", "只要星星")
        if t >= tz:
            kz = ease_out((t - tz) / 0.25) * (1 - 0.7 * ease((t - s("f8")) / 0.3))
            rrect(c, X(0) - 34, gy - 30, 68, 60, 12, paint(RED, 0.3 * a * kz))
            rrect(c, X(0) - 34, gy - 30, 68, 60, 12, paint(RED, 0.9 * a * kz, stroke=2))
            text(c, "没偏 → 相对论出局", X(0) - 20, gy - 74, 28, "sans_bold", RED, a * kz, "l", 2)
    # f8：星光真的偏了
    t8 = s("f8")
    if t >= t8:
        for j, (v, err, lab, dy) in enumerate(((1.98, 0.12, "索布拉尔 1.98″", -110), (1.61, 0.30, "普林西比 1.61″", -170))):
            tj = t8 + j * B / 2
            if t < tj:
                continue
            km = ease_out((t - tj) / 0.22, 3)
            yy = gy + dy - 40 * (1 - km)
            c.drawLine(X(v - err), yy, X(v + err), yy, paint(GOLD, a * km, stroke=3))
            glow_dot(c, X(v), yy, 8, GOLD, a * km, 3)
            text(c, lab, X(v) + 20, yy - 28, 22, "sans_med", GOLD, a * km, "c", 1)
        tb = t8 + B
        if t >= tb:
            E.slam(c, "偏了！", 1480, 250, 120, t, tb, "serif_black", GOLD, a, 10, shader=E.gold_shader(-70, 50),
                   glow=0.6, glow_rgb=GOLD)
            E.burst(ctx, t, tb, 1480, 250, GOLD, 600, 1400, 0.9, a)
    text(c, "偏折角度已放大示意", 1856, 1046 - 60, 22, "sans_light", GREY, 0.6 * a, "r", 1)
    c.restore()


def _target(c, x, y, a, k=1.0, col=INK):
    for i, r in enumerate((130, 92, 54, 18)):
        c.drawCircle(x, y, r, paint(col if i % 2 == 0 else RED, a * (0.9 if i == 3 else 0.75), stroke=4,
                                    trim=(0, clip01(k * 1.4 - i * 0.12))))


def scene_targets(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("f9"), T.SEC["falsify"][1]
    a = cutin(t, t0, t1 + 0.02, 0.0, 0.02)
    if a <= 0:
        return
    line(c, CX, 230, CX, 800, INK, 0.15 * a, 1.5)
    lx, ly = 520, 520
    _target(c, lx, ly, a, ease_out((t - t0) / (B * 0.8)))
    tsh = t0 + 2 * B
    ka = ease_in((t - tsh + 0.25) / 0.25, 2)
    if ka > 0:
        hx, hy = lx + 36, ly - 20
        sx, sy = lerp(lx - 420, hx, ka), lerp(ly + 60, hy, ka)
        c.drawLine(sx - 70, sy + 10, sx, sy, paint(GOLD, a, stroke=5))
        glow_dot(c, sx, sy, 6, GOLD, a, 3)
    E.slam(c, "科学", lx, 260, 56, t, t0, "serif_black", CYAN, a, 12)
    text(c, "先画靶，再开枪 —— 可能脱靶", lx, 740, 28, "sans_med", DIM, a, "c", 2)
    tm = at("f9", "迷信")
    if t >= tm:
        rx = 1400
        E.slam(c, "迷信", rx, 260, 56, t, tm, "serif_black", RED, a, 12)
        hits = [(1270, 420), (1540, 520), (1350, 640), (1490, 380)]
        for i, (hx, hy) in enumerate(hits):
            kh = ease_in((t - tm - i * B / 4) / 0.2, 2)
            if kh > 0:
                sx, sy = lerp(hx - 300, hx, kh), lerp(hy + 40, hy, kh)
                c.drawLine(sx - 50, sy + 7, sx, sy, paint(GOLD, a, stroke=4))
                glow_dot(c, sx, sy, 5, GOLD, a, 3)
            kt = ease_out((t - tm - 2 * B - i * B / 4) / 0.3)
            if kt > 0:
                for j, r in enumerate((76, 50, 24)):
                    c.drawCircle(hx, hy, r, paint(INK if j % 2 == 0 else RED, a * 0.75, stroke=3,
                                                  trim=(0, clip01(kt * 1.3 - j * 0.15))))
        text(c, "先开枪，再画靶 —— 永远「命中」", rx, 740, 28, "sans_med", DIM, a, "c", 2)


# ================================================================ 03 我们为什么会信
def scene_m1(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("m1"), s("m2")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    k = ease_out((t - t0) / 0.5, 3)
    E.gold8(c, CX, 450, 420 * lerp(0.8, 1.0, k), t, a, spin=(1 - k) * 1.5, glow=1.5)
    E.burst(ctx, t, t0, CX, 450, GOLD, 600, 1300, 1.0, a)


MEM = [(+10.0, "涨停"), (-21.5, "套牢"), (+8.2, ""), (-12.9, "割肉"), (+10.0, "涨停"), (-16.3, "套牢"),
       (+6.1, ""), (-9.8, ""), (+10.0, "涨停"), (-14.0, "套牢")]


def scene_m2(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("m2"), s("m4")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    # 右侧：记忆
    mx0, my0, mw, mh = 1240, 190, 460, 640
    E.glass(c, mx0, my0, mw, mh, 30, a, edge=GOLD, edge_a=0.5)
    text(c, "你的记忆", mx0 + mw / 2, my0 + 50, 34, "serif_black", GOLD, a, "c", 8)
    kept = 0
    for j, (pct, tag) in enumerate(MEM):
        tj = t0 + j * B / 2
        if t < tj:
            continue
        up = pct > 0
        col = RED if up else DOWN
        u = clip01((t - tj) / (2.5 * B))
        if up:
            slot = sum(1 for p, _ in MEM[:j] if p > 0)
            tx, ty = mx0 + mw / 2, my0 + 130 + slot * 100
            x = lerp(200, tx, ease_io(u))
            y = lerp(300 + (j % 4) * 120, ty, ease_io(u))
            al = a
            if u >= 1:
                kept += 1
        else:
            x = lerp(200, 1050, u)
            y = 300 + (j % 4) * 120
            al = a * (1 - ease((u - 0.55) / 0.35))
            if 0.55 < u < 1:
                E.burst(ctx, t, tj + 0.55 * 2.5 * B, x, y, DOWN, 120, 300, 0.8, a * 0.7)
        if al <= 0.003:
            continue
        w = 320
        E.glass(c, x - w / 2, y - 38, w, 76, 18, al, edge=col, edge_a=0.6,
                glow=0.35 if up and u >= 1 else 0.0, glow_rgb=col)
        E.code_text(c, "•••888", x - w / 2 + 24, y, 28, al, "l", glow=0.4)
        text(c, f"{pct:+.1f}%", x + w / 2 - 24, y, 34, "inter_bold", col, al, "r")
        if tag and u < 0.9:
            text(c, tag, x + 10, y - 54, 24, "sans_bold", col, al * (1 - ease((u - 0.7) / 0.2)), "c", 4)
    tr = at("m2", "涨停")
    if t >= tr:
        text(c, "记得清清楚楚", mx0 + mw / 2, my0 + mh + 46, 30, "serif_bold", RED, a * ease_out((t - tr) / 0.25), "c", 6)
    tf = at("m2", "套牢")
    if t >= tf:
        text(c, "转眼就忘", 760, 820, 30, "serif_bold", DOWN, a * ease_out((t - tf) / 0.25), "c", 6)


def scene_m4(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("m4"), s("m5")
    a = cutin(t, t0, t1 + 0.02, 0.0, 0.02)
    if a <= 0:
        return
    text(c, "判断一个说法是不是科学", CX, 360, 44, "serif_bold", DIM, a * ease_out((t - t0) / 0.3), "c", 8)
    tb = t0 + 3 * B
    if t >= tb:
        E.slam(c, "问四个问题", CX, 520, 120, t, tb, "serif_black", GOLD, a, 16, shader=E.gold_shader(-70, 50),
               glow=0.5, glow_rgb=GOLD)


GATES = ["能被证伪吗？", "能被别人重复吗？", "有可测量的证据吗？", "会随新证据修正吗？"]
TOKENS = [("相对论", 4, CYAN, ""), ("幸运数字 8", 0, GOLD, "涨了说灵，跌了说「不够多」"),
          ("星座", 0, RED, "怎么说都对"), ("MBTI", 1, RED, "隔几周重测，近半数人类型会变")]


def scene_gates(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("m5"), T.SEC["barnum"][1]
    a = cutin(t, t0, t1 + 0.02, 0.0, 0.02)
    if a <= 0:
        return
    gx = [480, 800, 1120, 1440]
    for i, g in enumerate(GATES):
        tg = s(f"m{5 + i}")
        if t < tg:
            continue
        k = ease_out((t - tg) / 0.3, 3)
        hot = math.exp(-(t - tg) / 0.4)
        x = gx[i]
        gate = skia.Path()
        gate.moveTo(x - 52, 800)
        gate.lineTo(x - 52, 430)
        gate.arcTo(skia.Rect.MakeLTRB(x - 52, 378, x + 52, 482), 180, 180, False)
        gate.lineTo(x + 52, 800)
        c.drawPath(gate, paint(CYAN, (0.06 + 0.15 * hot) * a))
        c.drawPath(gate, paint(CYAN, 0.9 * a, stroke=3, trim=(0, k)))
        c.drawPath(gate, paint(CYAN, (0.45 + 0.5 * hot) * a, stroke=10, blur=14, trim=(0, k)))
        text(c, f"0{i + 1}", x, 335, 26, "inter_bold", GOLD, a * k, "c", 2)
        E.slam(c, g, x, 290, 28, t, tg, "sans_bold", INK, a, 1)
        if hot > 0.05:
            E.slam(c, g, CX, 170, 60, t, tg, "serif_black", INK, a * hot, 8)
    t_run = e("m8")
    for j, (name, passed, col, note) in enumerate(TOKENS):
        y = 470 + j * 90
        tj = t_run + j * B / 2
        if t < tj:
            continue
        kin = ease_out((t - tj) / 0.2)
        prog = ease_io((t - tj) / (3 * B))
        stop_x = gx[passed] - 90 if passed < 4 else 1700
        x = lerp(220, stop_x, prog)
        tw = E.measure(name, 26, "sans_bold", 2) + 44
        rrect(c, x - tw / 2, y - 25, tw, 50, 25, paint(col, 0.2 * a * kin))
        rrect(c, x - tw / 2, y - 25, tw, 50, 25, paint(col, 0.9 * a * kin, stroke=1.8))
        text(c, name, x, y, 26, "sans_bold", INK, a * kin, "c", 2)
        for g in range(4):
            if passed > g and x > gx[g]:
                check(c, gx[g] + 30, y - 30, 20, GOLD, a * kin, 1.0, 3)
        done = t - tj - 3 * B
        if passed < 4 and done > 0:
            cross(c, gx[passed] + 28, y, 26, RED, a, ease_out(done / 0.2), 4)
            kn = a * ease_out((done - 0.1) / 0.25)
            nw = E.measure(note, 24, "sans_med", 1)
            rrect(c, gx[passed] + 52, y - 22, nw + 24, 44, 10, paint((0.02, 0.02, 0.05), 0.9 * kn))
            text(c, note, gx[passed] + 64, y, 24, "sans_med", INK, kn, "l", 1)
        if passed == 4 and done > 0:
            check(c, x + tw / 2 + 30, y, 30, GOLD, a, ease_out(done / 0.25), 4)


SCENES = [
    (s("c1"), s("c2") + 0.03, scene_c1),
    (s("c2"), s("c3") + 0.03, scene_c2),
    (s("c3"), s("c4"), scene_c3),
    (s("c4"), s("c5"), scene_c4),
    (s("c5"), s("c6") + 0.03, scene_c5),
    (s("c6"), s("c8"), scene_c67),
    (s("c8"), s("c9"), scene_c8),
    (s("c9"), T.SEC["cause"][1] + 0.03, scene_rct),
    (s("f1"), s("f2"), scene_f1),
    (s("f2"), s("f4"), scene_f23),
    (s("f4"), s("f5"), scene_f4),
    (s("f5"), s("f6"), scene_f5),
    (s("f6"), s("f9"), scene_eclipse),
    (s("f9"), T.SEC["falsify"][1] + 0.03, scene_targets),
    (s("m1"), s("m2"), scene_m1),
    (s("m2"), s("m4"), scene_m2),
    (s("m4"), s("m5") + 0.03, scene_m4),
    (s("m5"), T.SEC["barnum"][1] + 0.03, scene_gates),
]
