"""04 纠错的机器 · 05 像科学家一样投资 · 终章「你的 8 是什么」。"""
import math

import numpy as np
import skia

import engine as E
import timeline as T
from engine import (CX, CY, INK, DIM, GREY, CYAN, GOLD, UP, DOWN, clip01, ease, ease_out, ease_io, ease_in,
                    lerp, mixc, text, paint, line, arrow, rrect, glow_dot, check, cross, cutin, punch)
from scenes_a import bt, zoomed

s, e, at = T.s, T.e, T.at
B = T.BEAT
RED = UP
TEAL = (0.35, 0.95, 0.85)

# ================================================================ 04 光速测量：一次次修正，逼近真相
LIGHT = [(1676, 220000), (1729, 301000), (1849, 315000), (1862, 298000), (1879, 299910), (1926, 299796),
         (1950, 299792.5), (1972, 299792.4562), (1983, 299792.458)]


def scene_light(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("k1"), s("k2")
    a = cutin(t, t0, t1 + 0.02, 0.0, 0.02)
    if a <= 0:
        return
    x0, x1, yc = 260, 1660, 520

    def Y(v):
        d = v - 299792.458
        return yc - math.copysign(math.log10(1 + abs(d)) / 5.0, d) * 300

    def X(yr):
        return lerp(x0, x1, (yr - 1676) / (1983 - 1676))
    kl = ease_out((t - t0) / 0.5)
    line(c, x0, yc, x1, yc, GOLD, 0.6 * a, 2, kl)
    text(c, "真值 299,792.458 km/s", x0 + 20, yc - 30, 24, "inter_light", GOLD, a * kl, "l")
    pts = []
    for i, (yr, v) in enumerate(LIGHT):
        ti = t0 + (i + 1) * B * 0.75             # 每个附点八分音符一次测量
        if t < ti:
            break
        kk = ease_out((t - ti) / 0.18, 3)
        x, y = X(yr), Y(v)
        pts.append((x, y))
        last = i == len(LIGHT) - 1
        glow_dot(c, x, y, 7 + 6 * math.exp(-(t - ti) / 0.2), GOLD if last else CYAN, a * kk, 3)
        up = y < yc
        if i < 6 or last:
            text(c, f"{yr}", x, y + (-36 if up else 36) if i < 6 else y + 40, 22, "inter_med", INK, a * kk)
        if i < 5:
            lab = f"{v:,.0f}"
            text(c, lab, x, y + (-62 if up else 62), 22, "inter_light", DIM, a * kk)
    if len(pts) > 1:
        p = skia.Path()
        p.moveTo(*pts[0])
        for q in pts[1:]:
            p.lineTo(*q)
        c.drawPath(p, paint(CYAN, 0.6 * a, stroke=2))
    text(c, "人类测量光速的 300 年：一次次修正，逼近真值", CX, 820, 30, "serif_bold", INK, a * kl, "c", 4)
    text(c, "纵轴为与真值的偏差（对数刻度）", CX, 866, 22, "sans_light", GREY, a * kl, "c", 2)


# ---- 马歇尔：喝下一杯细菌
def _bacterium(c, x, y, ang, sc, t, a, col=TEAL):
    p = skia.Path()
    n = 18
    for i in range(n + 1):
        u = i / n
        px = (u - 0.5) * 60 * sc
        py = math.sin(u * math.tau * 1.5 + t * 6) * 7 * sc
        (p.moveTo if i == 0 else p.lineTo)(x + px * math.cos(ang) - py * math.sin(ang),
                                           y + px * math.sin(ang) + py * math.cos(ang))
    c.drawPath(p, paint(col, a, stroke=5 * sc))
    c.drawPath(p, paint(col, 0.4 * a, stroke=12 * sc, blur=6 * sc))
    ex = x - 30 * sc * math.cos(ang)
    ey = y - 30 * sc * math.sin(ang)
    for j in range(3):
        q = skia.Path()
        q.moveTo(ex, ey)
        for i in range(1, 8):
            u = i / 7
            px = -u * 34 * sc
            py = math.sin(u * 9 + t * 10 + j) * 4 * sc + (j - 1) * 6 * sc * u
            q.lineTo(ex + px * math.cos(ang) - py * math.sin(ang), ey + px * math.sin(ang) + py * math.cos(ang))
        c.drawPath(q, paint(col, 0.6 * a, stroke=1.4 * sc))


_r = np.random.default_rng(1984)
BAC = [(_r.random() * 280 - 140, _r.random() * 150 - 50, _r.random() * 6.28, 0.6 + _r.random() * 0.5) for _ in range(16)]


def scene_ulcer(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("k2"), s("k5")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    t_who = s("k3")
    t_drink = at("k3", "喝下了")
    t_flip = s("k4")
    t_nobel = at("k4", "2005")
    crack = ease_out((t - t_flip) / 0.3)
    shake = math.sin(t * 55) * 8 * math.exp(-max(0, t - t_flip) / 0.2) if t > t_flip else 0
    mv = ease_io((t - t_who) / 0.5)
    x, y = lerp(CX, 560, mv) + shake, lerp(470, 250, mv)
    col = mixc(INK, RED, crack)
    ks = ease_out((t - t0) / 0.25, 3)
    c.save()
    c.translate(x, y)
    c.rotate(-4 * mv)
    sc = lerp(1.5, 1.0, ks) * lerp(1.3, 0.9, mv)
    c.scale(sc, sc)
    rrect(c, -350, -72, 700, 144, 18, paint(col, 0.08 * a))
    rrect(c, -350, -72, 700, 144, 18, paint(col, 0.8 * a, stroke=3))
    text(c, "医学共识（1984）", 0, -34, 24, "sans_med", DIM, a, "c", 3)
    text(c, "胃溃疡 ＝ 压力 ＋ 胃酸", 0, 18, 48, "serif_black", col, a, "c", 6)
    if crack > 0:
        p = skia.Path()
        p.moveTo(-320, 50)
        for j, (px, py) in enumerate(((-180, 10), (-90, 36), (20, -20), (120, 8), (230, -36), (330, -50))):
            p.lineTo(px, py)
        c.drawPath(p, paint(RED, a, stroke=6, trim=(0, crack)))
        c.drawPath(p, paint(RED, 0.5 * a, stroke=16, blur=10, trim=(0, crack)))
    c.restore()
    if t >= t_who:
        kg = ease_out((t - t_who) / 0.3)
        gx, gy = 560, 680
        drink = ease_io((t - t_drink) / (3 * B))
        lvl = 1 - drink
        glass = skia.Path()
        glass.moveTo(gx - 110, gy - 140)
        glass.lineTo(gx - 88, gy + 140)
        glass.lineTo(gx + 88, gy + 140)
        glass.lineTo(gx + 110, gy - 140)
        c.save()
        c.clipPath(glass, doAntiAlias=True)
        top = lerp(gy + 140, gy - 100, lvl)
        c.drawRect(skia.Rect.MakeLTRB(gx - 130, top, gx + 130, gy + 150), paint(TEAL, 0.16 * a * kg))
        for (bx, by, ang, bs) in BAC:
            yy = gy + by * 0.9
            if yy > top + 10:
                _bacterium(c, gx + bx * 0.55, yy, ang + t * 0.3, bs, t, a * kg)
        c.restore()
        c.drawPath(glass, paint(INK, 0.7 * a * kg, stroke=2.5))
        text(c, "一杯幽门螺杆菌", gx, gy + 186, 26, "sans_med", TEAL, a * kg, "c", 2)
        E.slam(c, "巴里·马歇尔", 1260, 500, 64, t, t_who, "serif_black", INK, a, 8)
        text(c, "澳大利亚医生 · 不信，就亲自试", 1260, 570, 28, "sans_reg", DIM, a * kg, "c", 2)
    if t >= t_flip:
        kw = 1 - ease((t - t_nobel + 0.1) / 0.3)
        E.slam(c, "几天后：胃炎", 1260, 690, 56, t, t_flip, "serif_black", RED, a * kw, 6, glow=0.4, glow_rgb=RED)
        text(c, "幽门螺杆菌，才是元凶之一", 1260, 760, 30, "sans_med", INK, a * kw * ease_out((t - t_flip - 0.3) / 0.3),
             "c", 2)
    if t >= t_nobel:
        kn = ease_out((t - t_nobel) / 0.35, 3)
        mx, my = 1260, 720
        for i in range(30):
            ang = i * math.tau / 30 + t * 0.2
            line(c, mx + math.cos(ang) * 100, my + math.sin(ang) * 100, mx + math.cos(ang) * (100 + 60 * kn),
                 my + math.sin(ang) * (100 + 60 * kn), GOLD, 0.3 * a * kn, 2)
        c.save()
        c.translate(mx, my)
        c.scale(lerp(1.6, 1.0, kn), lerp(1.6, 1.0, kn))
        c.drawCircle(0, 0, 90, paint(shader=E.gold_shader(-90, 90), a=a * kn))
        c.drawCircle(0, 0, 76, paint((0.45, 0.30, 0.08), 0.6 * a * kn, stroke=2))
        text(c, "2005", 0, -12, 44, "inter_bold", (0.30, 0.18, 0.04), a * kn)
        text(c, "NOBEL", 0, 28, 22, "corm6", (0.30, 0.18, 0.04), a * kn, "c", 4)
        c.restore()
        text(c, "诺贝尔生理学或医学奖 · 马歇尔与沃伦", mx, my + 140, 26, "sans_med", GOLD, a * kn, "c", 2)
        E.burst(ctx, t, t_nobel, mx, my, GOLD, 600, 1200, 0.9, a)


def scene_feynman(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("k5"), T.SEC["correct"][1]
    a = cutin(t, t0, t1 + 0.02, 0.0, 0.02)
    if a <= 0:
        return
    text(c, "“", 330, 320, 220, "serif_black", GOLD, 0.5 * a, "c")
    text(c, "第一条原则，是不要欺骗自己——", CX, 430, 62, "serif_bold", INK, a, "c", 6, reveal=ease((t - t0) / (3 * B)))
    t2 = at("k5", "而你自己")
    if t >= t2:
        E.slam(c, "而你自己，最容易被骗。", CX, 540, 72, t, t2, "serif_black", GOLD, a, 8,
               shader=E.gold_shader(-44, 32), glow=0.4, glow_rgb=GOLD)
    k3 = ease((t - t2 - 0.5) / 0.6)
    text(c, "The first principle is that you must not fool yourself", CX, 650, 28, "corm", DIM, a * k3, "c", 1)
    text(c, "— and you are the easiest person to fool.", CX, 690, 28, "corm", DIM, a * k3, "c", 1)
    text(c, "理查德·费曼 · 1974 年加州理工毕业典礼演讲", CX, 770, 24, "sans_light", GOLD, a * k3, "c", 3)


# ================================================================ 05 回到股市
BURST_C = E.make_ohlc(40, 5, drift=0.5, vol=3.0)


def scene_i1(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("i1"), s("i2")
    a = cutin(t, t0, t1 + 0.02, 0.0, 0.02)
    if a <= 0:
        return
    E.candles(c, 100, 200, 1720, 640, BURST_C, k=ease_out((t - t0) / (2 * B), 2), a=0.5 * a)
    rrect(c, CX - 420, 400, 840, 220, 30, paint((0.02, 0.02, 0.03), 0.7 * a, blur=30))
    E.slam(c, "回到股市", CX, 510, 150, t, t0, "serif_black", GOLD, a, 24, shader=E.gold_shader(-90, 65),
           glow=0.5, glow_rgb=GOLD)
    E.burst(ctx, t, t0, CX, 510, GOLD, 900, 2000, 1.2, a)


_r = np.random.default_rng(1984)
COIN_N = 220160                # 第 10 天的幸存者约 22 万；之后每天淘汰一半，第 20 天约 215 人
_rad = np.sqrt(-2 * np.log(1 - _r.random(COIN_N) * 0.96)) / 2.6
_ang = _r.random(COIN_N) * 2 * np.pi
COIN_P = np.c_[0.5 + _rad * np.cos(_ang) * 0.55, 0.5 + _rad * np.sin(_ang) * 0.55]
COIN_DIE = _r.random(COIN_N)
FINAL_IDX = np.argsort(COIN_DIE)[-215:]


def coin_day(t):
    """第几天：与配乐的八分音符同步，每个八分音符淘汰一半。"""
    return clip01((t - T.COIN_T0) / (20 * T.COIN_STEP)) * 20


def scene_coins(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("i2"), s("i3")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    E.slam(c, "巴菲特的思想实验", CX, 170, 44, t, t0, "serif_black", GOLD, a, 8)
    day = coin_day(t)
    alive_frac = 0.5 ** day
    if day < 10:
        P = COIN_P * [1400, 600] + [260, 240]
        al = np.full(COIN_N, 0.10 + 0.55 * alive_frac ** 0.35, np.float32)
        ctx.splat(P, al[:, None] * np.array(GOLD, np.float32) * a)
    else:
        thr = 1 - 0.5 ** (day - 10)
        live = COIN_DIE >= thr
        P = COIN_P[live] * [1400, 600] + [260, 240]
        sz = 0.35 + 0.65 * clip01((day - 14) / 6)
        al = np.full(len(P), 0.9 + 2.2 * sz, np.float32)
        ctx.splat(P, al[:, None] * np.array(GOLD, np.float32) * a)
        if day > 17:
            kk = clip01((day - 17) / 3)
            for i in FINAL_IDX[::3]:
                x, y = COIN_P[i] * [1400, 600] + [260, 240]
                c.drawCircle(x, y, 3 + 3 * kk, paint(GOLD, 0.6 * kk * a))
    people = 225_000_000 * 0.5 ** math.floor(day)
    rrect(c, CX - 360, 790, 720, 110, 24, paint((0, 0, 0), 0.5 * a, blur=18))
    text(c, f"第 {int(day):2d} 天", CX - 220, 845, 38, "sans_bold", INK, a, "c", 2)
    text(c, f"{people:,.0f}", CX + 100, 845, 60, "inter_bold", GOLD, a, "c", 1,
         glow=0.3 * E.beat_env(t, T.COIN_T0, 20, 0.5, 0.1))
    text(c, "人", CX + 320, 849, 28, "sans_reg", DIM, a, "c")
    tf = T.COIN_T0 + 20 * T.COIN_STEP
    if t >= tf:
        E.slam(c, "连续猜对 20 次：215 人", CX, 250, 52, t, tf, "serif_black", INK, a, 8, glow=0.3, glow_rgb=GOLD)


_r = np.random.default_rng(81)
I3_N = 2400
I3_P = np.c_[_r.random(I3_N) * 1500 + 210, _r.random(I3_N) * 420 + 470]
I3_WIN = _r.random(I3_N) < 1 / 8


def scene_i3(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("i3"), s("i4")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    # 你的三连胜：三枚硬币依次翻开
    for j in range(3):
        tj = t0 + j * B / 2
        if t < tj:
            continue
        k = ease_out((t - tj) / 0.25, 3)
        x = CX - 720 + j * 150
        rx = 56 * abs(math.cos((1 - k) * math.pi * 3))
        c.drawOval(skia.Rect.MakeLTRB(x - max(rx, 3), 220 - 56, x + max(rx, 3), 220 + 56),
                   paint(shader=E.gold_shader(164, 276), a=a))
        if k > 0.8:
            text(c, "涨", x, 220, 44, "serif_black", (0.35, 0.18, 0.04), a, "c")
    tb = t0 + 2 * B
    if t >= tb:
        E.slam(c, "(½)³ =", CX + 60, 220, 84, t, tb, "inter_light", INK, a, 4, align="r")
        E.slam(c, "1/8", CX + 100, 220, 120, t, tb + B / 2, "inter_bold", GOLD, a, 4, align="l", glow=0.6,
               glow_rgb=GOLD)
    # 上亿股民：每 8 个人里就有 1 个三连胜
    tc = at("i3", "放进")
    if t >= tc:
        k = clip01((t - tc) / 0.4)
        lit = ease_out((t - tc - B) / 0.3)
        al = np.where(I3_WIN, 0.5 + 2.5 * lit, 0.45 * (1 - 0.5 * lit)).astype(np.float32) * a * k
        col = np.where(I3_WIN[:, None], np.array(GOLD, np.float32)[None, :],
                       np.array((0.55, 0.6, 0.75), np.float32)[None, :])
        for (px, py), w_, al_ in zip(I3_P[::2], I3_WIN[::2], al[::2]):
            if w_:
                c.drawCircle(px, py, 4.5, paint(GOLD, min(1.0, al_ / 3)))
                c.drawCircle(px, py, 10, paint(GOLD, min(1.0, al_ / 3) * 0.35, blur=6))
            else:
                c.drawCircle(px, py, 2.6, paint((0.55, 0.6, 0.75), min(1.0, al_)))
        if lit > 0:
            text(c, "上亿股民里：约 1/8 的人，都有过同样的三连胜", CX, 420, 34, "serif_bold", INK, a * lit, "c", 4)
    td = at("i3", "一点也不")
    if t >= td:
        rrect(c, CX - 360, 880 - 50, 720, 100, 24, paint((0.02, 0.02, 0.04), 0.85 * a))
        E.slam(c, "一点也不稀奇", CX, 880, 64, t, td, "serif_black", GOLD, a, 12, shader=E.gold_shader(-38, 28))


# ---- 格雷厄姆-多德村
_r = np.random.default_rng(1934)
WIN_P = np.c_[260 + _r.random(215) * 1400, 260 + _r.random(215) * 560]
VILLAGE = (1240, 540)
VIL_IDX = _r.permutation(215)[:40]
VIL_OFF = _r.normal(0, 1, (40, 2)) * [70, 50]
VIL_J = {int(i): j for j, i in enumerate(VIL_IDX)}


def scene_village(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("i4"), s("i5")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    tg = at("i4", "同一个")
    k = ease_io((t - tg) / (2 * B))
    for i in range(215):
        x, y = WIN_P[i]
        if i in VIL_J:
            j = VIL_J[i]
            x, y = lerp(x, VILLAGE[0] + VIL_OFF[j][0], k), lerp(y, VILLAGE[1] + VIL_OFF[j][1], k)
            glow_dot(c, x, y, 5 + 2 * k, mixc(GOLD, (1, 0.95, 0.7), k), a, 2.5)
        else:
            glow_dot(c, x, y, 4, GOLD, a * (1 - 0.6 * k), 2)
    kv = ease_out((t - tg - 2 * B) / 0.3)
    if kv > 0:
        c.drawCircle(*VILLAGE, 190, paint(GOLD, 0.7 * a * kv, stroke=2, dash=([10, 8], t * 20)))
        c.drawCircle(*VILLAGE, 190, paint(GOLD, 0.15 * a * kv, blur=40))
        text(c, "格雷厄姆-多德村", VILLAGE[0], VILLAGE[1] - 240, 38, "serif_black", GOLD, a * kv, "c", 6)
        text(c, "同一位老师：本杰明·格雷厄姆", VILLAGE[0], VILLAGE[1] + 240, 26, "sans_med", INK, a * kv, "c", 2)
    tr = at("i4", "那就不是运气")
    if t >= tr:
        rrect(c, 180, 380, 700, 300, 30, paint((0.02, 0.02, 0.04), 0.75 * a, blur=20))
        E.slam(c, "不是运气", 520, 470, 72, t, tr, "serif_black", INK, a, 8)
        tr2 = at("i4", "而是值得")
        if t >= tr2:
            E.slam(c, "而是值得研究的「原因」", 520, 570, 42, t, tr2, "serif_bold", GOLD, a, 6)
        text(c, "巴菲特 1984《格雷厄姆-多德村的超级投资者》", 520, 640, 22, "sans_light", DIM, a, "c", 2)


NOTES = [("3 月", "•••808", "−18.4%"), ("5 月", "•••188", "−11.2%"), ("同期", "不带 8 的股票", "也涨了 30%"),
         ("复盘", "牛市一过，带 8 的照样跌", "")]


def scene_darwin(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("i5"), s("i6")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    E.slam(c, "达尔文的「黄金法则」", 1420, 300, 52, t, t0, "serif_black", INK, a, 8)
    tq = at("i5", "凡是")
    k = ease_out((t - tq) / 0.4)
    text(c, "与自己理论相反的事实，", 1420, 400, 32, "serif_med", INK, a * k, "c", 2)
    text(c, "立刻记下来——", 1420, 452, 32, "serif_med", INK, a * k, "c", 2)
    text(c, "因为它忘得最快。", 1420, 504, 32, "serif_bold", GOLD, a * ease_out((t - at("i5", "因为")) / 0.3), "c", 2)
    text(c, "——《达尔文自传》（大意）", 1420, 570, 24, "sans_light", GREY, a * k, "c", 2)
    # 笔记本：与「8 很灵」相反的记录
    nx, ny, nw, nh = 230, 210, 760, 640
    kn = ease_out((t - tq) / 0.3)
    rrect(c, nx, ny, nw, nh, 18, paint((0.96, 0.92, 0.82), 0.08 * a * kn))
    rrect(c, nx, ny, nw, nh, 18, paint((0.96, 0.92, 0.82), 0.55 * a * kn, stroke=2))
    for i in range(10):
        line(c, nx + 40, ny + 130 + i * 50, nx + nw - 40, ny + 130 + i * 50, INK, 0.10 * a * kn, 1)
    text(c, "与「8 很灵」相反的记录", nx + 40, ny + 68, 34, "serif_black", GOLD, a * kn, "l", 4)
    for i, (when, what, res) in enumerate(NOTES):
        ti = tq + (i + 1) * B
        if t < ti:
            continue
        ki = ease_out((t - ti) / 0.2)
        y = ny + 170 + i * 110
        text(c, when, nx + 50, y, 26, "sans_med", DIM, a * ki, "l", 2)
        if what.startswith("•"):
            E.code_text(c, what, nx + 150, y, 34, a * ki, "l")
        else:
            text(c, what, nx + 150, y, 32, "serif_bold", INK, a * ki, "l", 2)
        if res:
            text(c, res, nx + nw - 50, y, 34, "inter_bold", DOWN if res.startswith("−") else RED, a * ki, "r")
        cross(c, nx + nw - 20, y - 28, 18, GOLD, a * ki, ki, 3)


STEPS = [("提出假设", "这家公司有定价权"), ("写下什么能推翻它", "一提价，客户就大量流失"),
         ("查看基础概率", "能长期提价的公司，本来就是少数"), ("主动寻找反证", "最强的看空理由是什么？"),
         ("随新信息更新判断", "调整判断，而不是捍卫观点")]


def scene_i6(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("i6"), s("i7")
    a = cutin(t, t0, t1 + 0.02, 0.0, 0.02)
    if a <= 0:
        return
    E.slam(c, "像科学家一样", CX, 430, 110, t, t0, "serif_black", INK, a, 16, glow=0.3, glow_rgb=CYAN)
    tb = t0 + 2 * B
    if t >= tb:
        E.slam(c, "分析一家企业", CX, 580, 110, t, tb, "serif_black", GOLD, a, 16, shader=E.gold_shader(-66, 48),
               glow=0.5, glow_rgb=GOLD)


def scene_steps(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("i7"), s("i12")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    E.slam(c, "像科学家一样分析一家企业", CX, 170, 44, t, t0, "serif_black", GOLD, a, 8, shader=E.gold_shader(-26, 20))
    cur = -1
    for i in range(5):
        if t >= s(f"i{7 + i}"):
            cur = i
    for i, (title, ex) in enumerate(STEPS):
        ti = s(f"i{7 + i}")
        if t < ti:
            continue
        k = ease_out((t - ti) / 0.22, 3)
        y = 250 + i * 128
        x = 300
        hot = i == cur
        c.save()
        c.translate(x + 660, y + 50)
        sc = lerp(1.12, 1.0, k)
        c.scale(sc, sc)
        c.translate(-(x + 660), -(y + 50))
        E.glass(c, x, y, 1320, 104, 20, a, edge=GOLD if hot else INK, edge_a=0.7 if hot else 0.2,
                glow=0.35 * math.exp(-(t - ti) / 0.4) if hot else 0.0)
        text(c, f"0{i + 1}", x + 70, y + 52, 46, "inter_thin", GOLD, a * (1 if hot else 0.6), "c")
        text(c, title, x + 140, y + 52, 38, "serif_black", INK, a * (1 if hot else 0.6), "l", 4)
        text(c, ex, x + 1290, y + 52, 28, "sans_med", INK if hot else DIM, a * (1 if hot else 0.6), "r", 1)
        c.restore()
        E.burst(ctx, t, ti, x + 70, y + 52, GOLD, 160, 500, 0.5, a)
    tl = s("i11") + 2 * B
    if t >= tl:
        kl = ease_out((t - tl) / 0.6)
        p = skia.Path()
        p.moveTo(1620, 250 + 4 * 128 + 52)
        p.cubicTo(1760, 250 + 4 * 128 + 52, 1760, 302, 1625, 302)
        c.drawPath(p, paint(GOLD, 0.9 * a, stroke=3, trim=(0, kl)))
        c.drawPath(p, paint(GOLD, 0.4 * a, stroke=10, blur=10, trim=(0, kl)))
        text(c, "循环", 1745, 560, 26, "sans_bold", GOLD, a * kl, "c", 4)


def scene_sees(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("i12"), T.SEC["invest"][1]
    a = cutin(t, t0, t1 + 0.02, 0.0, 0.02)
    if a <= 0:
        return
    E.slam(c, "喜诗糖果 See's Candies", 300, 230, 48, t, t0, "serif_black", INK, a, 4, align="l")
    text(c, "伯克希尔 1972 年收购", 300, 290, 26, "sans_reg", DIM, a, "l", 2)
    x0, x1, yb = 300, 1080, 800
    k = ease_io((t - t0 - 0.2) / (8 * B))
    p = skia.Path()
    p.moveTo(x0, yb - 60)
    yv = yb - 60
    n = 36
    for i in range(n):
        x = lerp(x0, x1, (i + 1) / n)
        if (i + 1) / n > k:
            break
        p.lineTo(x, yv)
        yv -= 9
        p.lineTo(x, yv)
    c.drawPath(p, paint(GOLD, 0.95 * a, stroke=3.5))
    c.drawPath(p, paint(GOLD, 0.35 * a, stroke=10, blur=8))
    text(c, "价格：几乎年年上调", x0 + 10, yb - 420, 26, "sans_med", GOLD, a * k, "l", 2)
    band_y = yb - 150
    c.drawRect(skia.Rect.MakeLTRB(x0, band_y - 14, lerp(x0, x1, k), band_y + 14), paint(CYAN, 0.25 * a))
    text(c, "顾客：始终都在", lerp(x0, x1, k) - 10, band_y - 40, 26, "sans_med", CYAN, a * k, "r", 2)
    line(c, x0, yb, x1, yb, INK, 0.4 * a, 1.5)
    text(c, "1972", x0, yb + 30, 22, "inter_light", DIM, a)
    text(c, "2007", x1, yb + 30, 22, "inter_light", DIM, a * k)
    text(c, "示意图", x1, yb + 64, 22, "sans_light", GREY, a * k, "r")
    facts = [("2,500 万美元", "1972 年收购价"), ("8,200 万美元", "2007 年税前利润（单年）"),
             ("13.5 亿美元", "1972–2007 累计税前利润")]
    for i, (big, small) in enumerate(facts):
        ti = t0 + (2 + i) * B
        if t < ti:
            continue
        kk = ease_out((t - ti) / 0.22)
        y = 380 + i * 140
        E.slam(c, big, 1240, y, 56, t, ti, "inter_bold", GOLD, a, align="l")
        text(c, small, 1240, y + 52, 24, "sans_reg", DIM, a * kk, "l", 2)
    text(c, "数据：巴菲特 2007 年致股东信", 1240, 790, 22, "sans_light", GREY, a, "l", 2)
    th = at("i12", "定价权")
    if t >= th:
        kh = ease_out((t - th) / 0.3)
        rrect(c, 300, 850, 1320, 76, 38, paint(RED, 0.14 * a * kh))
        rrect(c, 300, 850, 1320, 76, 38, paint(RED, 0.6 * a * kh, stroke=2))
        check(c, 352, 888, 32, GOLD, a, kh, 4)
        text(c, "假设「有定价权」：经受住了几十年的检验", 404, 888, 32, "serif_black", INK, a * kh, "l", 4)


# ================================================================ 终章
def scene_munger(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("e1"), s("e2")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    E.slam(c, "查理·芒格", CX, 300, 40, t, t0, "serif_black", GOLD, a, 12)
    text(c, "我们的优势，不是努力变得非常聪明，", CX, 460, 58, "serif_bold", DIM, a, "c", 4, reveal=ease((t - t0) / (4 * B)))
    t2 = at("e1", "而是始终")
    if t >= t2:
        E.slam(c, "而是始终努力不做蠢事。", CX, 570, 70, t, t2, "serif_black", INK, a, 6, glow=0.3, glow_rgb=GOLD)
    text(c, "（大意）", CX, 690, 24, "sans_light", GREY, a * ease((t - t2 - 0.5) / 0.5), "c", 2)


def scene_less_wrong(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("e2"), s("e3")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    E.slam(c, "科学思维", CX, 230, 44, t, t0, "serif_black", GOLD, a, 16)
    tw = E.slam(c, "永远正确", CX, 400, 96, t, t0 + B, "serif_black", INK,
                a * (1 - 0.6 * ease((t - at("e2", "而是让你")) / 0.3)), 12)
    tsx = at("e2", "而是让你")
    if t >= tsx:
        ks = ease_out((t - tsx) / 0.25)
        tw = E.measure("永远正确", 96, "serif_black", 12)
        c.drawLine(CX - tw / 2 - 20, 400, lerp(CX - tw / 2 - 20, CX + tw / 2 + 20, ks), 400, paint(RED, a, stroke=7))
    for key, x in (("错得更少", CX - 280), ("改得更快", CX + 280)):
        tk = at("e2", key)
        if t >= tk:
            E.slam(c, key, x, 620, 100, t, tk, "serif_black", GOLD, a, 10, shader=E.gold_shader(-60, 44),
                   glow=0.5, glow_rgb=GOLD)
            E.burst(ctx, t, tk, x, 620, GOLD, 300, 900, 0.7, a)


def scene_e3(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("e3"), s("e4")
    a = cutin(t, t0, t1 + 0.02, 0.0, 0.02)
    if a <= 0:
        return
    E.slam(c, "下一次下单之前", CX, 300, 72, t, t0, "serif_black", INK, a, 12)
    k = ease_out((t - t0 - B) / 0.3)
    bx, by = CX, 560
    pulse = 0.5 + 0.5 * math.cos((t - t0) / B * math.tau)
    rrect(c, bx - 220, by - 50, 440, 100, 50, paint(RED, 0.9 * a * k))
    rrect(c, bx - 220, by - 50, 440, 100, 50, paint(RED, 0.5 * a * k * pulse, stroke=14, blur=20))
    text(c, "买入", bx, by, 44, "sans_bold", (1, 1, 1), a * k, "c", 10)
    cx_, cy_ = lerp(bx + 420, bx + 60, ease_out((t - t0 - B) / (2 * B))), lerp(by + 220, by + 30, ease_out((t - t0 - B) / (2 * B)))
    cur = skia.Path()
    cur.moveTo(cx_, cy_)
    cur.lineTo(cx_, cy_ + 54)
    cur.lineTo(cx_ + 14, cy_ + 42)
    cur.lineTo(cx_ + 26, cy_ + 66)
    cur.lineTo(cx_ + 36, cy_ + 60)
    cur.lineTo(cx_ + 24, cy_ + 37)
    cur.lineTo(cx_ + 42, cy_ + 37)
    cur.close()
    c.drawPath(cur, paint((1, 1, 1), a * k))
    c.drawPath(cur, paint((0, 0, 0), a * k, stroke=2))
    tq = t0 + 3 * B
    if t >= tq:
        E.slam(c, "问问自己：", CX, 760, 52, t, tq, "serif_bold", DIM, a, 10)


def scene_e4(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = s("e4"), s("e5")
    a = cutin(t, t0, t1)
    if a <= 0:
        return
    k = ease_out((t - t0) / 0.4, 3)
    tm = t0 + 4 * B                                   # 第 4 拍：8 翻过去，背面是问号
    turn = clip01((t - tm + 0.2) / 0.4)
    spin = turn * math.pi
    for i in range(36):
        ang = i * math.tau / 36 + t * 0.1
        L = 900 * k
        c.drawLine(CX, 400, CX + math.cos(ang) * L, 400 + math.sin(ang) * L,
                   paint(GOLD, 0.06 * a * (0.5 + 0.5 * math.sin(i * 1.7)), stroke=4, blur=5))
    if turn < 0.5:
        E.gold8(c, CX, 400, 430 * lerp(1.3, 1.0, k), t, a, spin=spin, glow=1.6)
    else:
        sx = max(0.04, abs(math.cos(spin)))
        c.save()
        c.translate(CX, 400)
        c.scale(sx, 1)
        text(c, "？", 0, 0, 430, "serif_black", GOLD, a, "c", shader=E.gold_shader(-240, 180), glow=0.7, glow_rgb=GOLD)
        c.restore()
    E.burst(ctx, t, t0, CX, 400, GOLD, 600, 1300, 1.0, a)
    E.burst(ctx, t, tm, CX, 400, GOLD, 900, 1800, 1.2, a)
    E.slam(c, "我的 8，是什么？", CX, 820, 88, t, t0 + B, "serif_black", INK, a, 14, glow=0.3, glow_rgb=GOLD)


SCENES = [
    (s("k1"), s("k2") + 0.03, scene_light),
    (s("k2"), s("k5"), scene_ulcer),
    (s("k5"), T.SEC["correct"][1] + 0.03, scene_feynman),
    (s("i1"), s("i2") + 0.03, scene_i1),
    (s("i2"), s("i3"), scene_coins),
    (s("i3"), s("i4"), scene_i3),
    (s("i4"), s("i5"), scene_village),
    (s("i5"), s("i6"), scene_darwin),
    (s("i6"), s("i7") + 0.03, scene_i6),
    (s("i7"), s("i12"), scene_steps),
    (s("i12"), T.SEC["invest"][1] + 0.03, scene_sees),
    (s("e1"), s("e2"), scene_munger),
    (s("e2"), s("e3"), scene_less_wrong),
    (s("e3"), s("e4") + 0.03, scene_e3),
    (s("e4"), s("e5"), scene_e4),
]
