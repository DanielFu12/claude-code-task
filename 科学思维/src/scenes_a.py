"""钩子 · 序章「幸运数字 8」· 标题。

钩子四记重拍：一只带 8 的股票涨停 → 你的三笔盈利 → 满世界的 8 → 一个巨大的金色 8 裂开。
序章：你迷上了 8 → 1948 年斯金纳的鸽子 → 市场就是那只随机掉食物的箱子 → 研究：迷信要交学费。
所有切换都落在拍点上；大字在拍点砸下。
"""
import math

import numpy as np
import skia

import engine as E
import timeline as T
from engine import (CX, CY, INK, DIM, GREY, CYAN, GOLD, UP, DOWN, clip01, ease, ease_out, ease_io, ease_in,
                    lerp, text, paint, line, arrow, rrect, cross, cutin, punch)

s, e, at = T.s, T.e, T.at
B = T.BEAT
RED = UP


def bt(lid, k):
    """某句开始后的第 k 拍。"""
    return s(lid) + k * B


def bars(t0, t1, every=4):
    """[t0, t1) 内落在小节线（或每 every 拍）上的时刻。"""
    k0 = math.ceil((t0 - T.ORIGIN) / (every * B) - 1e-6)
    out = []
    while T.ORIGIN + k0 * every * B < t1:
        out.append(T.ORIGIN + k0 * every * B)
        k0 += 1
    return out


def zoomed(c, x, y, sc):
    c.save()
    c.translate(x, y)
    c.scale(sc, sc)
    c.translate(-x, -y)


def big_line(c, t, txt, t0, t1, y=872, size=84, gold=False, track=12):
    a = cutin(t, t0, t1, 0.05, 0.12)
    if a <= 0:
        return
    if gold:
        E.slam(c, txt, CX, y, size, t, t0, "serif_black", GOLD, a, track,
               shader=E.gold_shader(-size * 0.6, size * 0.45), glow=0.55, glow_rgb=GOLD)
    else:
        E.slam(c, txt, CX, y, size, t, t0, "serif_black", INK, a, track, glow=0.18, glow_rgb=CYAN)


# ================================================================ 0 钩子
HOOK_CHART = E.make_ohlc(24, 888, drift=1.6, vol=2.4, start=8.0)
_last = HOOK_CHART[-1]
HOOK_CHART[-1] = (_last[3], _last[3] * 1.10, _last[3] * 0.995, _last[3] * 1.10)     # 最后一根：涨停


def scene_h1(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("h1"), s("h2")
    a = cutin(t, 0.0, t1, 0.0, 0.08)
    if a <= 0:
        return
    zoomed(c, CX, 430, punch(t, t0, 0.06) * (1 + 0.02 * (t - t0) / 4))
    x0, y0, w, h = 330, 150, 1260, 560
    E.glass(c, x0, y0, w, h, 26, a)
    E.code_text(c, "•••888", x0 + 44, y0 + 56, 44, a, "l")
    shown = clip01((t - t0) / (6 * B))                 # 每个十六分音符长出一根 K 线，第 6 拍长满
    n = int(len(HOOK_CHART) * shown)
    last = HOOK_CHART[max(0, n - 1)][3]
    text(c, f"{last:.2f}", x0 + w - 44, y0 + 56, 44, "inter_bold", RED, a, "r", glow=0.3, glow_rgb=RED)
    for gy in range(4):
        line(c, x0 + 40, y0 + 130 + gy * 120, x0 + w - 40, y0 + 130 + gy * 120, INK, 0.06 * a, 1)
    lo = min(d[2] for d in HOOK_CHART)
    hi = max(d[1] for d in HOOK_CHART)
    E.candles(c, x0 + 50, y0 + 110, w - 100, h - 150, HOOK_CHART, k=shown, a=a, vmin=lo, vmax=hi)
    tb = bt("h1", 6)
    if t >= tb:
        k = ease_out((t - tb) / 0.2, 3)
        sc = lerp(1.6, 1.0, k)
        c.save()
        c.translate(x0 + 260, y0 + 200)
        c.scale(sc, sc)
        c.rotate(-6)
        rrect(c, -170, -50, 340, 100, 14, paint(RED, 0.92 * a * k))
        rrect(c, -170, -50, 340, 100, 14, paint(RED, 0.5 * a * k, stroke=10, blur=18))
        text(c, "涨停  +10.00%", 0, 0, 44, "sans_bold", (1, 1, 1), a * k, "c", 2)
        c.restore()
    c.restore()
    E.burst(ctx, t, tb, x0 + 260, y0 + 200, RED, 400, 900, 0.8, a)
    big_line(c, t, "你亲眼看到的", t0, t1)


H2_CARDS = [("•••888", 30.2, 3), ("•••168", 18.6, 5), ("•••518", 24.1, 8)]


def scene_h2(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("h2"), s("h3")
    a = cutin(t, t0, t1, 0.0, 0.08)
    if a <= 0:
        return
    for i, (code, pct, sd) in enumerate(H2_CARDS):
        ti = bt("h2", 2 * i)
        if t < ti:
            continue
        k = ease_out((t - ti) / 0.22, 3)
        x = CX + (i - 1) * 540
        c.save()
        c.translate(x, 420)
        c.scale(lerp(1.4, 1.0, k), lerp(1.4, 1.0, k))
        E.trade_card(c, 0, 0, a * clip01((t - ti) / 0.05), code, pct, t, 500, 170, f"第 {i + 1} 笔 · 买入",
                     glow=0.5 * math.exp(-(t - ti) / 0.3), k_num=ease_out((t - ti) / (1.5 * B)), seed=sd)
        c.restore()
        E.burst(ctx, t, ti, x, 420, RED, 260, 700, 0.6, a)
    tb = bt("h2", 6)
    if t >= tb:
        E.slam(c, "3 笔  ·  全部盈利", CX, 640, 48, t, tb, "serif_black", GOLD, a, 8,
               shader=E.gold_shader(-30, 20))
    big_line(c, t, "你亲身经历的", t0, t1)


H3_TILES = [("京A·88888", "车牌"), ("138 8888 8888", "手机号"), ("2008.08.08", "北京奥运开幕日"), ("¥ 888", "标价"),
            ("•••888", "股票代码"), ("8 楼", "楼层"), ("¥ 8.88", "红包"), ("88 号", "门牌")]


def _tile_pos(i):
    return CX + (i % 4 - 1.5) * 410, 300 + (i // 4) * 250


def scene_h3(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("h3"), s("h4") + 0.5
    a = cutin(t, t0, t1, 0.0, 0.5)
    if a <= 0:
        return
    collapse = ease_in((t - s("h4")) / 0.4, 2)      # 下一拍：所有瓦片被吸进中心
    glowk = E.beat_env(t, bt("h3", 5), 3, 1.0, 0.25)
    for i, (code, lab) in enumerate(H3_TILES):
        ti = t0 + i * B / 2
        if t < ti:
            continue
        k = ease_out((t - ti) / 0.2, 3)
        x, y = _tile_pos(i)
        x, y = lerp(x, CX, collapse), lerp(y, 430, collapse)
        sc = lerp(1.35, 1.0, k) * (1 - 0.8 * collapse)
        c.save()
        c.translate(x, y)
        c.scale(sc, sc)
        E.glass(c, -185, -95, 370, 190, 20, a, glow=0.35 * glowk, glow_rgb=GOLD)
        E.code_text(c, code, 0, -14, 46 if len(code) < 10 else 36, a, "c", glow=0.6 + 1.2 * glowk)
        text(c, lab, 0, 56, 22, "sans_reg", DIM, a, "c", 2)
        c.restore()
    if t < s("h4"):
        big_line(c, t, "所有人都深信不疑的", t0, s("h4"))


def scene_h4(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("h4"), T.SEC["hook"][1]
    a = cutin(t, t0, t1 + 0.01, 0.0, 0.05)
    if a <= 0:
        return
    k = ease_out((t - t0 - 0.15) / 0.5, 3)
    tc = bt("h4", 4)
    crack = 0.55 * ease_out((t - tc) / 0.25) + 0.45 * ease_out((t - bt("h4", 6)) / 0.25)
    shake = 9 * (E.beat_env(t, tc, 1, 1, 0.12) + E.beat_env(t, bt("h4", 6), 1, 1, 0.12))
    for i in range(28):
        ang = i * math.tau / 28 + t * 0.12
        L = 760 * k
        c.drawLine(CX, 430, CX + math.cos(ang) * L, 430 + math.sin(ang) * L,
                   paint(GOLD, 0.07 * a * (0.5 + 0.5 * math.sin(i * 2.3)) * (1 - 0.6 * crack), stroke=3, blur=4))
    E.gold8(c, CX + shake * math.sin(t * 90), 430, 470 * lerp(0.6, 1.0, k), t, a * clip01((t - t0) / 0.1),
            spin=(1 - k) * 1.2, crack=crack, glow=1.0 + 0.8 * math.exp(-(t - t0) / 0.3))
    E.burst(ctx, t, t0, CX, 430, GOLD, 700, 1300, 1.0, a)
    E.burst(ctx, t, tc, CX, 430, (1.0, 0.45, 0.35), 380, 900, 0.7, a)
    big_line(c, t, "一定是真的吗？", t0, t1 + 0.3, size=96, gold=True, track=16)


# ================================================================ 1 序章：你的 8
WATCH = [("•••235", 1.2), ("•••417", -0.6), ("•••888", 2.4), ("•••062", 0.3), ("•••359", -1.4), ("•••701", 0.8)]


def scene_s1(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("s1"), s("s2")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    zoomed(c, CX, 470, punch(t, t0, 0.08) * (1 + 0.03 * (t - t0) / 4))
    x0, y0, w = 560, 150, 800
    E.glass(c, x0, y0, w, 640, 28, a)
    text(c, "自选股", x0 + 40, y0 + 52, 30, "sans_bold", INK, a, "l", 4)
    text(c, "代码", x0 + 40, y0 + 108, 22, "sans_reg", GREY, a, "l", 2)
    text(c, "今日", x0 + w - 40, y0 + 108, 22, "sans_reg", GREY, a, "r", 2)
    t_pick = bt("s1", 2)
    t_buy = bt("s1", 4)
    for i, (code, pct) in enumerate(WATCH):
        ti = t0 + i * B / 4
        k = ease_out((t - ti) / 0.2, 3)
        y = y0 + 170 + i * 66
        hot = i == 2
        hk = ease_out((t - t_pick) / 0.18) if hot else 0.0
        dim = 1.0 if (hot or t < t_pick) else 0.4
        if hk > 0:
            rrect(c, x0 + 16, y - 30, w - 32, 60, 14, paint(GOLD, 0.12 * a * hk))
            rrect(c, x0 + 16, y - 30, w - 32, 60, 14, paint(GOLD, 0.8 * a * hk, stroke=2))
            rrect(c, x0 + 16, y - 30, w - 32, 60, 14, paint(GOLD, 0.4 * a * hk, stroke=8, blur=12))
        E.code_text(c, code, x0 + 40 + 40 * (1 - k), y, 36, a * k * dim, "l", glow=0.6 + 1.5 * hk)
        col = RED if pct >= 0 else DOWN
        text(c, f"{pct:+.2f}%", x0 + w - 40, y, 30, "inter_med", col, a * k * dim, "r")
    # 买入按钮
    if t >= t_buy - 0.6:
        kb = ease_out((t - t_buy + 0.6) / 0.3)
        bx, by = x0 + w / 2, y0 + 580
        pressed = t >= t_buy
        sc = 1.0 - 0.08 * math.exp(-(t - t_buy) / 0.08) if pressed else 1.0
        c.save()
        c.translate(bx, by)
        c.scale(sc, sc)
        rrect(c, -170, -34, 340, 68, 34, paint(RED, (0.95 if pressed else 0.5) * a * kb))
        text(c, "已买入" if pressed else "买入", 0, 0, 30, "sans_bold", (1, 1, 1), a * kb, "c", 4)
        c.restore()
        if pressed:
            kr = clip01((t - t_buy) / 0.6)
            c.drawCircle(bx, by, 40 + 260 * ease_out(kr), paint(RED, 0.5 * a * (1 - kr), stroke=4))
    # 「吉」字印章
    tj = bt("s1", 6)
    if t >= tj:
        kj = ease_out((t - tj) / 0.18, 3)
        c.save()
        c.translate(x0 + w + 110, y0 + 230)
        c.rotate(12)
        c.scale(lerp(2.0, 1.0, kj), lerp(2.0, 1.0, kj))
        rrect(c, -70, -70, 140, 140, 14, paint(RED, 0.9 * a * kj, stroke=8))
        text(c, "吉", 0, 0, 96, "serif_black", RED, a * kj, "c")
        c.restore()
    c.restore()


S2_BG = E.make_ohlc(48, 30, drift=0.9, vol=1.6)


def scene_s2(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("s2"), s("s3")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    E.candles(c, 120, 220, 1680, 640, S2_BG, k=ease_out((t - t0) / (3 * B), 2), a=0.30 * a)
    k = ease_out((t - t0) / (2 * B), 3)
    text(c, "一个月", CX, 260, 40, "sans_med", DIM, a, "c", 8)
    E.slam(c, f"+{30 * k:.0f}%", CX, 520, 300, t, t0, "inter_bold", RED, a, 0, glow=0.5, glow_rgb=RED)
    E.burst(ctx, t, t0, CX, 520, RED, 700, 1600, 1.0, a)


S3_CARDS = [("•••888", 30.2, 3, "第 1 次"), ("•••168", 18.6, 5, "第 2 次"), ("•••681", 24.1, 8, "第 3 次")]


def scene_s3(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("s3"), s("s4")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    t2 = max(at("s3", "第二次"), t0)
    times = [t0 - 10, t2, max(at("s3", "第三次"), t2 + B)]
    pos = []
    for i, (code, pct, sd, lab) in enumerate(S3_CARDS):
        ti = times[i]
        if t < ti:
            continue
        k = ease_out((t - ti) / 0.22, 3)
        x, y = CX + (i - 1) * 540, 470
        pos.append((x, y))
        c.save()
        c.translate(x, y)
        sc = lerp(1.4, 1.0, k)
        c.scale(sc, sc)
        E.trade_card(c, 0, 0, a * (1.0 if i == 0 else clip01((t - ti) / 0.05)), code, pct, t, 500, 180,
                     f"{lab} · 买入", glow=0.6 * math.exp(-max(0, t - ti) / 0.3), seed=sd)
        c.restore()
        if i:
            E.burst(ctx, t, ti, x, y, RED, 260, 800, 0.6, a)
    # 第 4 拍：三张卡片上的 8 连成一线
    tl = bt("s3", 4)
    if t >= tl and len(pos) == 3:
        kl = ease_out((t - tl) / 0.4)
        p = skia.Path()
        p.moveTo(pos[0][0] - 60, pos[0][1] - 100)
        p.cubicTo(pos[0][0] + 200, pos[0][1] - 260, pos[2][0] - 200, pos[2][1] - 260, pos[2][0] - 60, pos[2][1] - 100)
        c.drawPath(p, paint(GOLD, 0.9 * a, stroke=3, trim=(0, kl)))
        c.drawPath(p, paint(GOLD, 0.4 * a, stroke=10, blur=10, trim=(0, kl)))
        E.slam(c, "共同点：8", CX, 220, 56, t, tl, "serif_black", GOLD, a, 10, shader=E.gold_shader(-34, 25),
               glow=0.4, glow_rgb=GOLD)


def scene_s4(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("s4"), s("s5")
    a = cutin(t, t0, t1, 0.0, 0.06)
    if a <= 0:
        return
    k = ease_out((t - t0) / 0.5, 3)
    for i in range(36):
        ang = i * math.tau / 36 - t * 0.15
        L = 900 * k
        c.drawLine(CX, 420, CX + math.cos(ang) * L, 420 + math.sin(ang) * L,
                   paint(GOLD, 0.06 * a * (0.5 + 0.5 * math.sin(i * 1.7)), stroke=4, blur=5))
    E.gold8(c, CX, 420, 440 * lerp(1.25, 1.0, k), t, a, spin=(1 - k) * 2.6 + 0.12 * math.sin(t * 1.3),
            glow=1.2 + 1.5 * math.exp(-(t - t0) / 0.35))
    E.burst(ctx, t, t0, CX, 420, GOLD, 800, 1500, 1.1, a)
    text(c, "从此你认定", CX, 760, 36, "sans_med", DIM, a * ease((t - t0 - 0.1) / 0.3), "c", 10)
    big_line(c, t, "8，就是幸运数字", bt("s4", 2), t1 + 0.01, y=860, size=80, gold=True)


def scene_s5(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("s5"), s("s6")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    ctx.bg = 0.6
    # 胶片边框：时间回到 1948
    for yy in (120, 960):
        for i in range(-1, 26):
            x = (i * 80 + (t - t0) * 120) % 2080 - 80
            rrect(c, x, yy - 14, 44, 28, 6, paint(INK, 0.10 * a))
    line(c, 0, 150, 1920, 150, INK, 0.08 * a, 1.5)
    line(c, 0, 930, 1920, 930, INK, 0.08 * a, 1.5)
    E.slam(c, "1948", CX, 400, 300, t, t0, "inter_thin", INK, a, 20, glow=0.25, glow_rgb=CYAN)
    tb = bt("s5", 2)
    if t >= tb:
        E.slam(c, "B. F. 斯金纳", CX, 640, 60, t, tb, "serif_black", INK, a, 10)
        text(c, "美国心理学家 · 行为主义代表人物", CX, 712, 26, "sans_reg", DIM, a * ease((t - tb - 0.15) / 0.3), "c", 4)
    tc = bt("s5", 4)
    if t >= tc:
        kc = ease_out((t - tc) / 0.4)
        line(c, CX - 300 * kc, 770, CX + 300 * kc, 770, GOLD, 0.6 * a, 1.5)
        E.slam(c, "实验：鸽子会不会「迷信」？", CX, 830, 44, t, tc, "serif_bold", GOLD, a, 6)


# ---- 斯金纳箱
def lamp_at(t, lands):
    return max([math.exp(-abs(t - L + 0.3) / 0.15) for L in lands] or [0.0])


def skinner_box(c, x, y, w, h, a, edge=CYAN, glow=0.0, lamp=0.0, label=None):
    """透视的玻璃箱：返回 (投食口 x, 投食口 y, 地面 y)。"""
    d = 0.16
    fx0, fy0, fx1, fy1 = x - w / 2, y - h / 2, x + w / 2, y + h / 2
    bx0, by0 = x - w / 2 * (1 - d), y - h / 2 * (1 - d) - h * 0.07
    bx1, by1 = x + w / 2 * (1 - d), y + h / 2 * (1 - d) - h * 0.07
    hx = x + w * 0.24
    if a <= 0.003:
        return hx, by0 + 46, (fy1 + by1) / 2
    c.drawRect(skia.Rect.MakeLTRB(bx0, by0, bx1, by1), paint((0.03, 0.05, 0.09), 0.85 * a))
    fl = skia.Path()
    fl.moveTo(fx0, fy1)
    fl.lineTo(fx1, fy1)
    fl.lineTo(bx1, by1)
    fl.lineTo(bx0, by1)
    fl.close()
    sh = skia.GradientShader.MakeLinear([skia.Point(0, by1), skia.Point(0, fy1)],
                                        [E.c4(edge, 0.03), E.c4(edge, 0.14)], [0, 1])
    c.drawPath(fl, paint(shader=sh, a=a))
    for (p0, p1) in (((fx0, fy0), (bx0, by0)), ((fx1, fy0), (bx1, by0)), ((fx0, fy1), (bx0, by1)),
                     ((fx1, fy1), (bx1, by1))):
        c.drawLine(*p0, *p1, paint(edge, 0.35 * a, stroke=1.5))
    c.drawRect(skia.Rect.MakeLTRB(bx0, by0, bx1, by1), paint(edge, 0.25 * a, stroke=1.2))
    hp = skia.Path()
    hp.moveTo(hx - 36, by0)
    hp.lineTo(hx + 36, by0)
    hp.lineTo(hx + 14, by0 + 46)
    hp.lineTo(hx - 14, by0 + 46)
    hp.close()
    c.drawPath(hp, paint((0.25, 0.28, 0.36), a))
    c.drawPath(hp, paint(edge, 0.6 * a, stroke=1.5))
    c.drawCircle(hx + 60, by0 + 22, 9, paint(GOLD, a * (0.25 + 0.75 * lamp)))
    if lamp > 0.02:
        c.drawCircle(hx + 60, by0 + 22, 30, paint(GOLD, 0.5 * a * lamp, blur=14))
    c.drawRect(skia.Rect.MakeLTRB(fx0, fy0, fx1, fy1), paint(edge, 0.85 * a, stroke=2.2))
    if glow > 0:
        c.drawRect(skia.Rect.MakeLTRB(fx0, fy0, fx1, fy1), paint(edge, glow * a, stroke=10, blur=16))
    gl = skia.Path()
    gl.moveTo(fx0 + w * 0.08, fy0)
    gl.lineTo(fx0 + w * 0.20, fy0)
    gl.lineTo(fx0 + w * 0.05, fy1)
    gl.lineTo(fx0 - w * 0.02, fy1)
    gl.close()
    c.drawPath(gl, paint((1, 1, 1), 0.035 * a))
    if label:
        text(c, label, x, fy1 + 40, 24, "sans_med", DIM, a, "c", 3)
    return hx, by0 + 46, (fy1 + by1) / 2


def pellets(c, t, hx, top, floor, lands, a, rgb=GOLD, size=9):
    """在 lands 各时刻落地的食物粒。"""
    for i, L in enumerate(lands):
        if t < L - 0.32 or t > L + 2.6:
            continue
        if t < L:
            u = (t - L + 0.32) / 0.32
            y = lerp(top, floor, u * u)
            x = hx
        else:
            v = t - L
            y = floor - 40 * abs(math.sin(v * 9)) * math.exp(-v * 6)
            x = hx - 30 * (1 - math.exp(-v * 4)) * (1 if i % 2 else -1)
            c.drawCircle(x, floor + 4, 40 * math.exp(-v * 3), paint(rgb, 0.25 * a * math.exp(-v * 3), blur=12))
        al = a * (1 - ease((t - L - 2.0) / 0.6))
        c.drawCircle(x, y, size, paint(rgb, al))
        c.drawCircle(x, y, size * 2.5, paint(rgb, 0.3 * al, blur=8))


def pig(c, x, y, sc, a, t, mode, t_act=-1e9, rgb=(0.66, 0.70, 0.82)):
    """把鸽子的动作锁在节拍上：转圈每拍翻一次身，其余动作两拍一个来回。"""
    beats = (t - T.ORIGIN) / B
    if t < t_act:
        mode = "idle"
    tt = {"spin": beats * math.pi / 4, "corner": beats * math.pi / 3, "pendulum": beats * math.pi / 4.2}.get(mode, t)
    E.pigeon(c, x, y, sc, a, tt, mode, rgb)


def scene_s6(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("s6"), s("s7")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    zoomed(c, CX, 520, punch(t, t0, 0.08))
    lands = bars(t0 + 0.4, t1 + 0.3)
    hx, top, floor = skinner_box(c, CX, 500, 860, 520, a, lamp=lamp_at(t, lands))
    pellets(c, t, hx, top, floor, lands, a)
    pig(c, CX - 170, floor - 70, 1.25, a, t, "idle")
    # 计时圈：每个小节转一圈（实验里是 15 秒；时间已压缩）
    rx, ry = CX + 640, 330
    prev = max([L for L in [t0] + lands if L <= t])
    nxt = min([L for L in lands if L > t] or [prev + 4 * B])
    k = clip01((t - prev) / max(nxt - prev, 1e-3))
    c.drawCircle(rx, ry, 70, paint(INK, 0.15 * a, stroke=6))
    c.drawArc(skia.Rect.MakeLTRB(rx - 70, ry - 70, rx + 70, ry + 70), -90, 360 * k, False, paint(GOLD, a, stroke=6))
    text(c, "15 秒", rx, ry - 4, 34, "sans_bold", INK, a, "c", 2)
    text(c, "自动投食", rx, ry + 112, 24, "sans_reg", DIM, a, "c", 3)
    text(c, "（时间已压缩）", rx, ry + 146, 22, "sans_light", GREY, a, "c", 2)
    tr = at("s6", "跟它做什么")
    if t >= tr:
        E.slam(c, "与它做什么 · 毫无关系", CX - 560, 200, 34, t, tr, "sans_bold", GOLD, a, 4)
    c.restore()


S7_ON = [0, 2, 3, 5, 6, 7]
S7_MODE = ["spin", None, "corner", "pendulum", None, "spin", "pendulum", "corner"]


def scene_s7(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("s7"), s("s8")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    lands = bars(t0, t1 + 0.3)
    n_on = 0
    for i in range(8):
        x = CX + (i % 4 - 1.5) * 400
        y = 380 + (i // 4) * 300
        ti = t0 + i * B / 4
        k = ease_out((t - ti) / 0.2, 3)
        on_t = bt("s7", 2) + S7_ON.index(i) * B / 2 if i in S7_ON else 1e9
        on = t >= on_t
        n_on += on
        ok = math.exp(-(t - on_t) / 0.25) if on else 0
        edge = GOLD if on else GREY
        hx, top, floor = skinner_box(c, x, y, 340 * k, 240 * k, a * k, edge=edge, glow=0.25 * on + 0.6 * ok,
                                     lamp=lamp_at(t, lands))
        pellets(c, t, hx, top, floor, lands, a * k, size=5)
        pig(c, x - 40, floor - 32, 0.55, a * k * (1 if on or t < bt("s7", 2) else 0.45), t, S7_MODE[i] or "idle", on_t)
        if on:
            text(c, "仪式", x, y - 148, 24, "sans_bold", GOLD, a * ease_out((t - on_t) / 0.2), "c", 6)
    tc = bt("s7", 2)
    if t >= tc:
        text(c, f"{n_on}", CX - 30, 150, 84, "inter_bold", GOLD, a, "r", glow=0.5)
        text(c, "/ 8 只鸽子有了「仪式」", CX - 10, 158, 36, "sans_med", INK, a, "l", 4)


S8 = [("spin", "逆时针转圈", "逆时针"), ("corner", "头伸向角落", "把头伸向"), ("pendulum", "钟摆式晃头", "像钟摆")]


def scene_s8(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("s8"), s("s9")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    lands = bars(t0, t1 + 0.3, 2)
    for i, (mode, lab, key) in enumerate(S8):
        ta = max(t0, at("s8", key))
        x = CX + (i - 1) * 590
        act = t >= ta
        kk = ease_out((t - ta) / 0.25, 3) if act else 0.0
        hx, top, floor = skinner_box(c, x, 470, 540, 480, a, edge=GOLD if act else CYAN, glow=0.3 * kk,
                                     lamp=lamp_at(t, lands))
        pellets(c, t, hx, top, floor, lands, a)
        pig(c, x - 50, floor - 60, 1.05, a * (0.5 + 0.5 * kk), t, mode, ta)
        if act:
            E.slam(c, lab, x, 790, 38, t, ta, "serif_black", GOLD, a, 6)
            E.burst(ctx, t, ta, x, 470, GOLD, 200, 600, 0.5, a)


def scene_s9(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("s9"), s("s10")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    lands = bars(t0, t1 + 0.3)
    hx, top, floor = skinner_box(c, 520, 500, 640, 500, a, lamp=lamp_at(t, lands))
    pellets(c, t, hx, top, floor, lands, a)
    pig(c, 470, floor - 66, 1.15, a, t, "spin")
    rx = 1300
    k1 = ease_out((t - t0 - 0.05) / 0.3)
    E.glass(c, rx - 360, 250, 720, 140, 20, a * k1)
    text(c, "我转圈", rx - 200, 320, 40, "serif_black", INK, a * k1, "c", 4)
    text(c, "食物", rx + 220, 320, 40, "serif_black", GOLD, a * k1, "c", 4)
    c.drawLine(rx - 90, 320, rx + 140, 320, paint(GOLD, 0.9 * a * k1, stroke=3, dash=([14, 10], -t * 60)))
    text(c, "它以为的因果", rx, 220, 26, "sans_med", GOLD, a * k1, "c", 4)
    t2 = bt("s9", 3)
    if t >= t2:
        k2 = ease_out((t - t2) / 0.3)
        E.glass(c, rx - 360, 560, 720, 140, 20, a * k2)
        text(c, "时间到了", rx - 200, 630, 40, "serif_black", INK, a * k2, "c", 4)
        text(c, "食物", rx + 220, 630, 40, "serif_black", GOLD, a * k2, "c", 4)
        arrow(c, rx - 70, 630, rx + 150, 630, CYAN, a * k2, 4, k2, 18)
        text(c, "真正的原因", rx, 530, 26, "sans_med", CYAN, a * k2, "c", 4)
    t3 = bt("s9", 5)
    if t >= t3:
        cross(c, rx + 25, 320, 110, RED, a, ease_out((t - t3) / 0.25), 9)


S10_FALL = np.random.default_rng(10).random((24, 3))


def scene_s10(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("s10"), s("s11")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    E.slam(c, "市场", CX, 200, 150, t, t0, "serif_black", INK, a, 30, glow=0.3, glow_rgb=GOLD)
    lands = [t0 + (j + 1) * B / 2 for j in range(16)]
    hx, top, floor = skinner_box(c, CX, 560, 1000, 440, a, edge=GOLD, glow=0.15, lamp=lamp_at(t, lands))
    # 每半拍从投食口掉下一根随机的 K 线（红或绿）
    for j, L in enumerate(lands):
        if t < L - 0.3:
            break
        r = S10_FALL[j]
        col = RED if r[0] > 0.48 else DOWN
        u = clip01((t - L + 0.3) / 0.3)
        x = lerp(hx, CX - 420 + r[1] * 760, ease_out(u, 2))
        y = lerp(top, floor - 30 - r[2] * 40, u * u)
        hh = 30 + 60 * r[2]
        c.drawLine(x, y - hh * 0.8, x, y + hh * 0.8, paint(col, a, stroke=3))
        rrect(c, x - 11, y - hh / 2, 22, hh, 3, paint(col, a))
        rrect(c, x - 11, y - hh / 2, 22, hh, 3, paint(col, 0.4 * a, blur=8))
    tb = bt("s10", 2)
    if t >= tb:
        E.slam(c, "＝ 那只随机掉食物的箱子", CX, 880, 46, t, tb, "serif_black", GOLD, a, 8)


def scene_s11(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("s11"), s("s12")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    beats = (t - T.ORIGIN) / B
    hx, top, floor = skinner_box(c, CX - 470, 470, 560, 460, a)
    pig(c, CX - 520, floor - 60, 1.1, a, t, "spin")
    E.gold8(c, CX + 470, 450, 330, t, a, spin=beats * math.pi / 2, glow=1.2)   # 与鸽子同步翻转
    E.slam(c, "＝", CX, 450, 120, t, t0, "inter_light", GOLD, a, glow=0.6, glow_rgb=GOLD)
    big_line(c, t, "你的 8 ＝ 鸽子的转圈", bt("s11", 1), t1 + 0.01, y=860, size=70)


IPO_N = 60
_x = np.linspace(0, 1, IPO_N)
IPO_L = 0.82 - 0.62 * (1 - np.exp(-_x * 3.0)) + 0.015 * np.sin(_x * 23)
IPO_O = 0.50 - 0.05 * _x + 0.015 * np.sin(_x * 19 + 1)


def scene_s12(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("s12"), s("s13")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    x0, y0, w, h = 250, 140, 1420, 720
    E.glass(c, x0, y0, w, h, 26, a)
    E.slam(c, "研究：A 股里的「幸运数字」", x0 + 60, y0 + 64, 42, t, t0, "serif_black", GOLD, a, 4, align="l")
    text(c, "Hirshleifer, Jian & Zhang · Management Science · 2018", x0 + 60, y0 + 118, 22, "inter_light", DIM, a,
         "l", 1)
    tf = bt("s12", 2)
    if t >= tf:
        kf = ease_out((t - tf) / 0.25)
        E.glass(c, x0 + 60, y0 + 160, 560, 66, 33, a * kf, edge=GOLD, edge_a=0.5)
        E.code_text(c, "8", x0 + 100, y0 + 193, 36, a * kf, "c")
        text(c, "吉利代码，出现得比随机更多", x0 + 140, y0 + 193, 26, "sans_med", INK, a * kf, "l", 2)
    gx0, gy0, gw, gh = x0 + 110, y0 + 280, 1200, 340
    line(c, gx0, gy0 + gh, gx0 + gw, gy0 + gh, INK, 0.4 * a, 1.5)
    line(c, gx0, gy0, gx0, gy0 + gh, INK, 0.25 * a, 1.5)
    text(c, "估值", gx0 - 20, gy0 + 10, 22, "sans_reg", GREY, a, "r", 2)
    text(c, "上市", gx0, gy0 + gh + 34, 22, "sans_reg", GREY, a, "c", 2)
    text(c, "之后几年", gx0 + gw, gy0 + gh + 34, 22, "sans_reg", GREY, a, "r", 2)
    tc = bt("s12", 4)
    kc = ease_io((t - tc) / (6 * B))
    E.spark(c, gx0, gy0, gw, gh, IPO_O, (0.6, 0.64, 0.74), a, kc, 3, fill=False)
    E.spark(c, gx0, gy0, gw, gh, IPO_L, GOLD, a, kc, 4, fill=True)
    if t >= tc:
        kp = ease_out((t - tc) / 0.25)
        c.drawCircle(gx0, gy0 + gh * (1 - IPO_L[0]), 10, paint(GOLD, a * kp))
        text(c, "上市时：被炒得更贵", gx0 + 30, gy0 + gh * (1 - IPO_L[0]) - 36, 30, "serif_bold", GOLD, a * kp, "l", 2)
        text(c, "代码带吉利数字", gx0 + gw - 10, gy0 + gh * (1 - IPO_L[-1]) + 36, 22, "sans_med", GOLD, a * kc, "r", 2)
        text(c, "其他新股", gx0 + gw - 10, gy0 + gh * (1 - IPO_O[-1]) - 30, 22, "sans_med", DIM, a * kc, "r", 2)
    td = at("s12", "之后")
    if t >= td:
        E.slam(c, "之后：跑输市场", gx0 + gw * 0.62, gy0 + 40, 44, t, td, "serif_black", DOWN, a, 6,
               glow=0.3, glow_rgb=DOWN)
    text(c, "曲线为示意", x0 + w - 40, y0 + h - 30, 22, "sans_light", GREY, a, "r", 2)


def scene_s13(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("s13"), T.SEC["eight"][1]
    a = cutin(t, t0, t1 + 0.01, 0.0, 0.02)
    if a <= 0:
        return
    E.slam(c, "迷信，", CX - 250, 400, 120, t, t0, "serif_black", INK, a, 10)
    tb = bt("s13", 1)
    if t >= tb:
        E.slam(c, "是要交学费的。", CX + 120, 560, 120, t, tb, "serif_black", GOLD, a, 10,
               shader=E.gold_shader(-70, 50), glow=0.4, glow_rgb=GOLD)
    for j, v in enumerate((-12.4, -18.0, -8.8)):
        tj = bt("s13", 2) + j * B / 2
        if t >= tj:
            E.slam(c, f"{v:+.1f}%", CX - 500 + j * 500, 790, 58, t, tj, "inter_bold", DOWN, a, glow=0.3, glow_rgb=DOWN)


# ================================================================ 标题
def scene_title(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = T.SEC["title"]
    a = cutin(t, t0, t1 + 0.01, 0.0, 0.02)
    if a <= 0:
        return
    k = ease_out((t - t0) / 1.2)
    for i in range(40):
        ang = i * math.tau / 40 + t * 0.05
        L = 1000 * k
        c.drawLine(CX, CY - 30, CX + math.cos(ang) * L, CY - 30 + math.sin(ang) * L,
                   paint(GOLD, 0.06 * a * (0.5 + 0.5 * math.sin(i * 2.7)), stroke=2, blur=3))
    E.slam(c, "科学思维", CX, CY - 40, 176, t, t0, "serif_black", GOLD, a, 26, shader=E.gold_shader(-110, 70),
           glow=0.45 * (1 + 2 * math.exp(-(t - t0) / 0.3)), glow_rgb=GOLD, dur=0.35)
    text(c, "S C I E N T I F I C   T H I N K I N G", CX, CY + 96, 22, "corm6", E.SUBGOLD,
         a * ease((t - t0 - 0.3) / 0.4), "c", 2)
    tb = t0 + 4 * B
    if t >= tb:
        E.slam(c, "怎样，才不做那只鸽子", CX, CY + 170, 40, t, tb, "serif_bold", INK, a, 10)
    sh = clip01((t - t0 - 0.9) / 1.2)
    if 0 < sh < 1:
        x = lerp(CX - 520, CX + 520, ease_io(sh))
        c.drawRect(skia.Rect.MakeXYWH(x - 40, CY - 170, 80, 260), paint((1, 0.95, 0.8), 0.10 * a, blur=30, blend="add"))
    E.burst(ctx, t, t0, CX, CY - 40, GOLD, 900, 2000, 1.3, a)


SCENES = [
    (0.0, s("h2"), scene_h1),
    (s("h2"), s("h3"), scene_h2),
    (s("h3"), s("h4") + 0.6, scene_h3),
    (s("h4"), T.SEC["hook"][1] + 0.02, scene_h4),
    (s("s1"), s("s2"), scene_s1),
    (s("s2"), s("s3"), scene_s2),
    (s("s3"), s("s4"), scene_s3),
    (s("s4"), s("s5"), scene_s4),
    (s("s5"), s("s6"), scene_s5),
    (s("s6"), s("s7"), scene_s6),
    (s("s7"), s("s8"), scene_s7),
    (s("s8"), s("s9"), scene_s8),
    (s("s9"), s("s10"), scene_s9),
    (s("s10"), s("s11"), scene_s10),
    (s("s11"), s("s12"), scene_s11),
    (s("s12"), s("s13"), scene_s12),
    (s("s13"), T.SEC["eight"][1] + 0.02, scene_s13),
    (T.SEC["title"][0], T.SEC["title"][1] + 0.02, scene_title),
]
