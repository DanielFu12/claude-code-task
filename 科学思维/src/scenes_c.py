"""04 纠错的机器 · 05 像科学家一样投资 · 终章。"""
import math

import numpy as np
import skia

import engine as E
import timeline as T
from engine import (W, H, CX, CY, INK, DIM, GREY, CYAN, GOLD, RED, GREEN, clip01, ease, ease_out, ease_io, ease_in,
                    back_out, lerp, mixc, win, text, paint, line, arrow, rrect, glow_dot, check, cross)

s, e, at = T.s, T.e, T.at
TEAL = (0.35, 0.95, 0.85)

# ================================================================ 04 光速测量：一次次修正，逼近真相
# 数据：历史上的光速测量值（km/s）
LIGHT = [(1676, 220000, "罗默 / 惠更斯"), (1729, 301000, "布拉德雷"), (1849, 315000, "斐索"), (1862, 298000, "傅科"),
         (1879, 299910, "迈克耳孙"), (1926, 299796, "迈克耳孙"), (1950, 299792.5, "埃森"), (1972, 299792.4562, "激光测量"),
         (1983, 299792.458, "定义值")]


def scene_light(ctx):
    t, c = ctx.t, ctx.c
    t0 = T.SEC["correct"][0]
    a = win(t, t0, e("k1") + 0.2, 0.5, 0.5)
    if a <= 0:
        return
    x0, x1, yc = 260, 1660, 560
    k = ease_io((t - t0 - 0.1) / 3.2)
    # 纵轴：与真值的偏差（对称对数），越往右越贴近中线
    def Y(v):
        d = v - 299792.458
        return yc - math.copysign(math.log10(1 + abs(d)) / 5.0, d) * 300

    def X(yr):
        return lerp(x0, x1, (yr - 1676) / (1983 - 1676))
    line(c, x0, yc, x1, yc, GOLD, 0.5 * a, 2, k)
    text(c, "真值 299,792.458 km/s", x0 + 20, yc - 28, 24, "inter_light", GOLD, a * k, "l")
    pts = []
    for i, (yr, v, who) in enumerate(LIGHT):
        kk = ease((k * 1.15 - (yr - 1676) / (1983 - 1676)) / 0.08)
        if kk <= 0:
            continue
        x, y = X(yr), Y(v)
        pts.append((x, y))
        glow_dot(c, x, y, 7, CYAN if i < len(LIGHT) - 1 else GOLD, a * kk, 3)
        up = y < yc
        if i < 6 or i == len(LIGHT) - 1:
            text(c, f"{yr}", x, y + (-36 if up else 36) if i < 6 else y + 40, 22, "inter_med", INK, a * kk)
        lab = f"{v:,.0f}" if v < 299000 or v > 300000 else f"{v:,.3f}".rstrip("0").rstrip(".")
        if i < 5:
            text(c, lab, x, y + (-62 if up else 62), 22, "inter_light", DIM, a * kk)
    if len(pts) > 1:
        p = skia.Path()
        p.moveTo(*pts[0])
        for q in pts[1:]:
            p.lineTo(*q)
        c.drawPath(p, paint(CYAN, 0.6 * a, stroke=2))
    text(c, "人类测量光速的 300 年：不断修正，向真值收敛", CX, 860, 28, "serif_med", INK, a * ease((t - t0 - 1) / 0.8), "c", 4)
    text(c, "纵轴为与真值的偏差（对数刻度）", CX, 904, 22, "sans_light", GREY, a * ease((t - t0 - 1) / 0.8), "c", 2)


# ---- 马歇尔：喝下一杯细菌
def _bacterium(c, x, y, ang, sc, t, a, col=TEAL):
    p = skia.Path()
    n = 18
    for i in range(n + 1):
        u = i / n
        px = (u - 0.5) * 60 * sc
        py = math.sin(u * math.tau * 1.5 + t * 6) * 7 * sc
        X = x + px * math.cos(ang) - py * math.sin(ang)
        Y = y + px * math.sin(ang) + py * math.cos(ang)
        (p.moveTo if i == 0 else p.lineTo)(X, Y)
    c.drawPath(p, paint(col, a, stroke=5 * sc))
    c.drawPath(p, paint(col, 0.4 * a, stroke=12 * sc, blur=6 * sc))
    # 鞭毛
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
    t0 = s("k2")
    a = win(t, t0 - 0.3, e("k3") + 0.3, 0.6, 0.5)
    if a <= 0:
        return
    # 共识印章
    t_drink = at("k2", "喝下了")
    t_flip = s("k3")
    t_nobel = at("k3", "2005")
    crack = ease((t - t_flip - 0.4) / 0.5)
    shake = math.sin(t * 55) * 5 * math.exp(-max(0, t - t_flip - 0.4) / 0.2) if t > t_flip + 0.4 else 0
    ks = back_out((t - t0 - 0.2) / 0.5)
    if ks > 0:
        mv = ease_io((t - at("k2", "澳大利亚") + 0.4) / 0.9)
        x, y = lerp(CX, 560, mv) + shake, lerp(500, 300, mv)
        col = mixc(INK, RED, crack)
        c.save()
        c.translate(x, y)
        c.rotate(-4 * mv)
        c.scale(ks * lerp(1.35, 1.0, mv), ks * lerp(1.35, 1.0, mv))
        rrect(c, -330, -64, 660, 128, 16, paint(col, 0.08 * a))
        rrect(c, -330, -64, 660, 128, 16, paint(col, 0.75 * a, stroke=3))
        text(c, "医学共识（1984）", 0, -30, 22, "sans_reg", DIM, a, "c", 3)
        text(c, "胃溃疡 ＝ 压力 ＋ 胃酸", 0, 18, 44, "serif_black", col, a, "c", 6)
        if crack > 0:
            c.drawLine(-300, 40, 300, -40, paint(RED, a * crack, stroke=5, trim=(0, crack)))
        c.restore()
    # 一杯细菌
    kg = ease((t - at("k2", "澳大利亚") + 0.2) / 0.6)
    if kg > 0:
        gx, gy = 560, 680
        drink = ease_io((t - t_drink - 0.3) / 2.2)
        lvl = 1 - drink
        glass = skia.Path()
        glass.moveTo(gx - 120, gy - 150)
        glass.lineTo(gx - 95, gy + 150)
        glass.lineTo(gx + 95, gy + 150)
        glass.lineTo(gx + 120, gy - 150)
        c.save()
        c.clipPath(glass, doAntiAlias=True)
        top = lerp(gy + 150, gy - 110, lvl)
        c.drawRect(skia.Rect.MakeLTRB(gx - 130, top, gx + 130, gy + 160), paint(TEAL, 0.14 * a * kg))
        for (bx, by, ang, sc) in BAC:
            yy = gy + by * 0.9
            if yy > top + 10:
                _bacterium(c, gx + bx * 0.6, yy, ang + t * 0.3, sc, t, a * kg)
        c.restore()
        c.drawPath(glass, paint(INK, 0.7 * a * kg, stroke=2.5))
        text(c, "幽门螺杆菌培养液", gx, gy + 196, 24, "sans_reg", TEAL, a * kg, "c", 2)
        text(c, "巴里·马歇尔", 1240, 520, 44, "serif_black", INK, a * kg, "c", 8)
        text(c, "澳大利亚医生 · 1984 年亲自喝下细菌", 1240, 576, 24, "sans_light", DIM, a * kg, "c", 2)
        kw = ease((t - t_flip) / 0.5) * (1 - ease((t - t_nobel + 0.1) / 0.4))
        text(c, "一周后：胃炎", 1240, 680, 40, "serif_bold", RED, a * kw, "c", 6)
        text(c, "幽门螺杆菌，才是元凶之一", 1240, 736, 26, "sans_reg", INK, a * kw, "c", 2)
    # 诺贝尔奖
    kn = ease((t - t_nobel) / 0.7)
    if kn > 0:
        mx, my = 1240, 720
        for i in range(24):
            ang = i * math.tau / 24 + t * 0.2
            line(c, mx + math.cos(ang) * 92, my + math.sin(ang) * 92, mx + math.cos(ang) * (92 + 40 * kn),
                 my + math.sin(ang) * (92 + 40 * kn), GOLD, 0.25 * a * kn, 2)
        c.drawCircle(mx, my, 84, paint(shader=E.gold_shader(my - 84, my + 84), a=a * kn))
        c.drawCircle(mx, my, 70, paint((0.45, 0.30, 0.08), 0.6 * a * kn, stroke=2))
        text(c, "2005", mx, my - 12, 40, "inter_bold", (0.30, 0.18, 0.04), a * kn)
        text(c, "NOBEL", mx, my + 26, 22, "corm6", (0.30, 0.18, 0.04), a * kn, "c", 4)
        text(c, "诺贝尔生理学或医学奖 · 马歇尔与沃伦", mx, my + 130, 24, "sans_reg", GOLD, a * kn, "c", 2)


def scene_feynman(ctx):
    t, c = ctx.t, ctx.c
    t0 = s("k4")
    a = win(t, t0 - 0.3, T.SEC["correct"][1] - 0.05, 0.6, 0.4)
    if a <= 0:
        return
    text(c, "“", 330, 330, 200, "serif_black", GOLD, 0.5 * a, "c")
    text(c, "第一条原则，是不要欺骗自己——", CX, 440, 60, "serif_bold", INK, a, "c", 6, reveal=ease((t - t0 - 0.2) / 1.4))
    t2 = at("k4", "而你自己")
    text(c, "而你自己，最容易被骗。", CX, 540, 60, "serif_black", INK, a, "c", 6, reveal=ease((t - t2) / 1.2),
         glow=0.3, glow_rgb=GOLD)
    k3 = ease((t - t2 - 0.8) / 0.8)
    text(c, "The first principle is that you must not fool yourself", CX, 650, 26, "corm", DIM, a * k3, "c", 1)
    text(c, "— and you are the easiest person to fool.", CX, 690, 26, "corm", DIM, a * k3, "c", 1)
    text(c, "理查德·费曼 · 1974 年加州理工毕业典礼演讲", CX, 770, 24, "sans_light", GOLD, a * k3, "c", 3)


# ================================================================ 05 抛硬币大赛
_r = np.random.default_rng(1984)
COIN_N = 220160               # 第 10 天的幸存者约 22 万；之后每天淘汰一半，第 20 天约 215 人
_rad = np.sqrt(-2 * np.log(1 - _r.random(COIN_N) * 0.96)) / 2.6   # 高斯形的“人群星云”
_ang = _r.random(COIN_N) * 2 * np.pi
COIN_P = np.c_[0.5 + _rad * np.cos(_ang) * 0.55, 0.5 + _rad * np.sin(_ang) * 0.55]
COIN_DIE = _r.random(COIN_N)   # 越小越早出局
FINAL_IDX = np.argsort(COIN_DIE)[-215:]


def coin_day(t):
    t0 = at("i2", "每天猜")
    t1 = at("i2", "二十天后")
    return clip01((t - t0) / (t1 - t0 + 1.2)) * 20


def scene_coins(ctx):
    t, c = ctx.t, ctx.c
    t0 = T.SEC["invest"][0]
    a = win(t, s("i2") - 0.4, e("i3") + 0.4, 0.6, 0.6)
    a_open = win(t, t0, s("i2") + 0.2, 0.3, 0.5)
    if a_open > 0:
        # 进入市场：K 线从网格里长出来
        _r2 = np.random.default_rng(3)
        v = 540.0
        for i in range(44):
            k = ease((t - t0 - 0.2 - i * 0.04) / 0.3)
            o = v
            v += _r2.normal(0.6, 18)
            hi, lo = max(o, v) + _r2.random() * 14, min(o, v) - _r2.random() * 14
            x = 230 + i * 34
            col = (0.3, 0.85, 0.55) if v < o else (1.0, 0.38, 0.38)
            line(c, x, lo, x, hi, col, a_open * k, 1.5)
            rrect(c, x - 9, min(o, v), 18, max(abs(v - o), 2) * k, 2, paint(col, a_open * k))
        text(c, "把科学思维，带进市场", CX, 220, 52, "serif_black", GOLD, a_open * ease((t - t0 - 0.4) / 0.6), "c", 10,
             shader=E.gold_shader(190, 250))
    if a <= 0:
        return
    day = coin_day(t)
    # 粒子：活下来的人
    alive_frac = 0.5 ** day
    dens = a * (1 - ease((t - e("i3")) / 0.4))
    if day < 10:
        # 2.25 亿人：用一片光雾表示，逐日变稀
        P = COIN_P * [1400, 640] + [260, 260]
        al = np.full(COIN_N, 0.10 + 0.55 * alive_frac ** 0.35, np.float32)
        ctx.splat(P, al[:, None] * np.array(GOLD, np.float32) * dens)
    else:
        thr = 1 - 0.5 ** (day - 10)          # 第 10 天之后：每个点就是一个人
        live = COIN_DIE >= thr
        P = COIN_P[live] * [1400, 640] + [260, 260]
        sz = 0.35 + 0.65 * clip01((day - 14) / 6)
        al = np.full(len(P), 0.9 + 2.2 * sz, np.float32)
        ctx.splat(P, al[:, None] * np.array(GOLD, np.float32) * dens)
        if day > 17:
            kk = clip01((day - 17) / 3)
            for i in FINAL_IDX[::3]:
                x, y = COIN_P[i] * [1400, 640] + [260, 260]
                c.drawCircle(x, y, 3 + 3 * kk, paint(GOLD, 0.6 * kk * dens))
    people = 225_000_000 * 0.5 ** math.floor(day)
    kt = ease((t - s("i2")) / 0.5)
    rrect(c, CX - 330, 800, 660, 110, 24, paint((0, 0, 0), 0.45 * a * kt, blur=18))
    text(c, f"第 {int(day):2d} 天", CX - 200, 855, 36, "sans_med", INK, a * kt, "c", 2)
    text(c, f"{people:,.0f}", CX + 110, 855, 54, "inter_light", GOLD, a * kt, "c", 1)
    text(c, "人", CX + 300, 859, 26, "sans_reg", DIM, a * kt, "c")
    # 「股神」
    kg = ease((t - s("i3") + 0.1) / 0.5) * (1 - ease((t - at("i3", "过去涨得好")) / 0.4))
    if kg > 0:
        text(c, "215 位「股神」：连续猜对 20 次", CX, 190, 44, "serif_black", GOLD, a * kg, "c", 6, shader=E.gold_shader(160, 220))
        text(c, "2.25 亿 × (1/2)²⁰ ≈ 215 —— 纯属运气也会发生", CX, 250, 26, "inter_light", DIM, a * kg, "c", 1)
    kd = ease((t - at("i3", "过去涨得好") + 0.1) / 0.5)
    if kd > 0:
        text(c, "第 21 天：猜对的概率仍是", CX - 60, 210, 40, "serif_bold", INK, a * kd, "c", 4)
        text(c, "50%", CX + 330, 206, 72, "inter_light", CYAN, a * kd, "c", glow=0.5)


# ---- 格雷厄姆-多德村
_r = np.random.default_rng(1934)
WIN_P = np.c_[260 + _r.random(215) * 1400, 300 + _r.random(215) * 520]
VILLAGE = (1240, 560)
VIL_IDX = _r.permutation(215)[:40]
VIL_OFF = _r.normal(0, 1, (40, 2)) * [70, 50]


def scene_village(ctx):
    t, c = ctx.t, ctx.c
    t0 = s("i4")
    a = win(t, t0 - 0.3, e("i4") + 0.3, 0.6, 0.5)
    if a <= 0:
        return
    k = ease_io((t - at("i4", "如果许多") - 0.2) / 1.6)
    vis = set(VIL_IDX.tolist())
    for i in range(215):
        x, y = WIN_P[i]
        if i in vis:
            j = list(VIL_IDX).index(i)
            x, y = lerp(x, VILLAGE[0] + VIL_OFF[j][0], k), lerp(y, VILLAGE[1] + VIL_OFF[j][1], k)
            col = mixc(GOLD, (1, 0.95, 0.7), k)
            glow_dot(c, x, y, 5 + 2 * k, col, a, 2.5)
        else:
            glow_dot(c, x, y, 4, GOLD, a * (1 - 0.6 * k), 2)
    kv = ease((t - at("i4", "如果许多") - 1.4) / 0.6)
    if kv > 0:
        c.drawCircle(*VILLAGE, 190, paint(GOLD, 0.7 * a * kv, stroke=2, dash=([10, 8], t * 20)))
        c.drawCircle(*VILLAGE, 190, paint(GOLD, 0.15 * a * kv, blur=40))
        text(c, "格雷厄姆-多德村", VILLAGE[0], VILLAGE[1] - 240, 34, "serif_black", GOLD, a * kv, "c", 6)
        text(c, "同一位老师：本杰明·格雷厄姆", VILLAGE[0], VILLAGE[1] + 240, 24, "sans_reg", INK, a * kv, "c", 2)
    kr = ease((t - at("i4", "那就不是运气") + 0.1) / 0.6)
    if kr > 0:
        text(c, "不是运气", 520, 470, 64, "serif_black", INK, a * kr, "c", 8)
        text(c, "而是值得研究的「原因」", 520, 560, 40, "serif_bold", GOLD, a * kr, "c", 6)
        text(c, "巴菲特 1984《格雷厄姆-多德村的超级投资者》", 520, 630, 22, "sans_light", DIM, a * kr, "c", 2)


# ---- 确认偏误：只收利好
NEWS = [("营收超预期", 1), ("核心高管离职", 0), ("新品口碑火爆", 1), ("毛利率三连降", 0), ("机构上调评级", 1),
        ("竞争对手降价 30%", 0), ("股价创新高", 1), ("应收账款激增", 0), ("社交媒体热议", 1), ("客户续约率下滑", 0)]


def scene_confirm(ctx):
    t, c = ctx.t, ctx.c
    t0 = s("i5")
    a = win(t, t0 - 0.3, e("i5") + 0.3, 0.6, 0.5)
    if a <= 0:
        return
    hx, hy = CX, 560
    c.drawCircle(hx, hy, 120, paint(GOLD, 0.12 * a))
    c.drawCircle(hx, hy, 120, paint(GOLD, 0.8 * a, stroke=2.5))
    text(c, "我的判断", hx, hy - 16, 34, "serif_black", GOLD, a, "c", 4)
    text(c, "「买对了」", hx, hy + 30, 24, "sans_reg", INK, a, "c", 2)
    for i, (n, good) in enumerate(NEWS):
        ph = ((t - t0) * 0.32 + i / len(NEWS)) % 1.0
        ang = i * 2.39996
        R = lerp(760, 160, ph)
        x, y = hx + math.cos(ang) * R * 1.15, hy + math.sin(ang) * R * 0.62
        if not good and ph > 0.55:
            # 利空被弹开、变淡
            kk = (ph - 0.55) / 0.45
            R2 = lerp(R, R + 500, kk)
            x, y = hx + math.cos(ang) * R2 * 1.15, hy + math.sin(ang) * R2 * 0.62
            al = a * (1 - kk)
        else:
            al = a * clip01(ph / 0.15) * (1 if not good else clip01((1 - ph) / 0.12))
        col = (0.36, 0.92, 0.62) if good else RED
        tw = E.measure(n, 24, "sans_med", 1) + 34
        rrect(c, x - tw / 2, y - 24, tw, 48, 12, paint(col, 0.15 * al))
        rrect(c, x - tw / 2, y - 24, tw, 48, 12, paint(col, 0.8 * al, stroke=1.5))
        text(c, n, x, y, 24, "sans_med", INK, al, "c", 1)
    text(c, "利好：吸收　　利空：屏蔽", CX, 920, 26, "sans_reg", DIM, a, "c", 4)


def scene_darwin(ctx):
    t, c = ctx.t, ctx.c
    t0 = s("i6")
    a = win(t, t0 - 0.3, e("i6") + 0.3, 0.6, 0.5)
    if a <= 0:
        return
    # 笔记本
    nx, ny, nw, nh = 300, 230, 720, 640
    rrect(c, nx, ny, nw, nh, 18, paint((0.96, 0.92, 0.82), 0.10 * a))
    rrect(c, nx, ny, nw, nh, 18, paint((0.96, 0.92, 0.82), 0.6 * a, stroke=2))
    for i in range(10):
        line(c, nx + 40, ny + 130 + i * 50, nx + nw - 40, ny + 130 + i * 50, INK, 0.12 * a, 1)
    text(c, "与我的理论「相反」的事实", nx + 40, ny + 70, 34, "serif_bold", GOLD, a, "l", 4)
    notes = ["竞争对手降价 30%，客户开始比价", "毛利率连续三个季度下滑", "核心高管离职，理由不明",
             "应收账款增速远超营收"]
    for i, n in enumerate(notes):
        k = ease((t - at("i6", "看到与") - i * 0.9) / 0.9)
        text(c, n, nx + 50, ny + 155 + i * 100, 28, "serif_med", INK, a, "l", 2, reveal=k)
        if k > 0.95:
            cross(c, nx + nw - 70, ny + 155 + i * 100, 20, RED, a, ease((t - at("i6", "看到与") - i * 0.9 - 0.9) / 0.3), 3)
    text(c, "达尔文的「黄金法则」", 1400, 380, 46, "serif_black", INK, a, "c", 8)
    text(c, "“这类事实，比有利的事实", 1400, 470, 30, "serif_med", DIM, a, "c", 2)
    text(c, "更容易从记忆中溜走。”", 1400, 518, 30, "serif_med", DIM, a, "c", 2)
    text(c, "——《达尔文自传》", 1400, 570, 24, "sans_light", GREY, a, "c", 2)
    km = ease((t - at("i6", "芒格")) / 0.6)
    text(c, "芒格：反面证据，要优先对待", 1400, 700, 32, "serif_bold", GOLD, a * km, "c", 4)


STEPS = [("提出假设", "这家公司拥有定价权", "提出假设"), ("写下证伪条件", "若一提价，客户就大量流失 → 假设作废", "写下什么"),
         ("查看基础概率", "长期保持高增长的公司，本来就是少数", "查看基础"), ("主动寻找反证", "最有力的看空理由是什么？", "主动寻找"),
         ("随新信息更新", "调整判断与仓位，而不是捍卫观点", "随新信息")]


def scene_steps(ctx):
    t, c = ctx.t, ctx.c
    t0 = s("i7")
    a = win(t, t0 - 0.3, e("i7") + 0.25, 0.6, 0.35)
    if a <= 0:
        return
    text(c, "像科学家一样分析一家企业", CX, 190, 46, "serif_black", GOLD, a * ease((t - t0) / 0.6), "c", 8,
         shader=E.gold_shader(160, 220))
    cur = -1
    for i, (title, ex, key) in enumerate(STEPS):
        ti = at("i7", key)
        if t >= ti - 0.15:
            cur = i
    for i, (title, ex, key) in enumerate(STEPS):
        ti = at("i7", key)
        k = 0.35 * ease((t - t0 - 0.3 - i * 0.12) / 0.5) + 0.65 * ease((t - ti + 0.2) / 0.5)
        y = 300 + i * 118
        x = 330
        hot = 1.0 if i == cur else 0.55
        rrect(c, x, y, 1260, 96, 18, paint(GOLD if i == cur else INK, (0.10 if i == cur else 0.04) * a * k))
        rrect(c, x, y, 1260, 96, 18, paint(GOLD if i == cur else INK, (0.7 if i == cur else 0.2) * a * k, stroke=1.6))
        text(c, f"0{i + 1}", x + 60, y + 48, 40, "inter_thin", GOLD, a * k * hot, "c")
        text(c, title, x + 130, y + 48, 34, "serif_bold", INK, a * k * hot, "l", 4)
        text(c, ex, x + 470, y + 48, 26, "sans_reg", DIM if i != cur else INK, a * k * hot, "l", 1)
    # 回环：第 5 步回到第 1 步
    kl = ease((t - at("i7", "随新信息") - 0.6) / 0.8)
    if kl > 0:
        p = skia.Path()
        p.moveTo(1590, 300 + 4 * 118 + 48)
        p.cubicTo(1720, 300 + 4 * 118 + 48, 1720, 348, 1600, 348)
        c.drawPath(p, paint(GOLD, 0.8 * a, stroke=3, trim=(0, kl)))
        text(c, "循环", 1700, 580, 24, "sans_reg", GOLD, a * kl, "c", 4)


def scene_sees(ctx):
    t, c = ctx.t, ctx.c
    t0 = s("i8")
    a = win(t, t0 - 0.3, T.SEC["invest"][1] - 0.1, 0.6, 0.4)
    if a <= 0:
        return
    text(c, "喜诗糖果 See's Candies", 300, 240, 44, "serif_black", INK, a, "l", 4)
    text(c, "伯克希尔 1972 年收购", 300, 296, 24, "sans_light", DIM, a, "l", 2)
    # 示意：每年提价的台阶线 + 平稳的顾客带
    x0, x1, yb = 300, 1080, 820
    k = ease_io((t - t0 - 0.2) / 3.0)
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
    c.drawPath(p, paint(GOLD, 0.9 * a, stroke=3))
    text(c, "价格：几乎年年上调", x0 + 10, yb - 420, 24, "sans_reg", GOLD, a * k, "l", 2)
    band_y = yb - 150
    c.drawRect(skia.Rect.MakeLTRB(x0, band_y - 14, lerp(x0, x1, k), band_y + 14), paint(CYAN, 0.25 * a))
    text(c, "顾客：始终都在", lerp(x0, x1, k) - 10, band_y - 40, 24, "sans_reg", CYAN, a * k, "r", 2)
    line(c, x0, yb, x1, yb, INK, 0.4 * a, 1.5)
    text(c, "1972", x0, yb + 30, 22, "inter_light", DIM, a)
    text(c, "2007", x1, yb + 30, 22, "inter_light", DIM, a * k)
    text(c, "示意图", x1, yb + 64, 22, "sans_light", GREY, a * k, "r")
    # 数据卡（巴菲特 2007 年致股东信）
    facts = [("2,500 万美元", "1972 年收购价"), ("8,200 万美元", "2007 年税前利润（单年）"), ("13.5 亿美元", "1972–2007 累计税前利润")]
    for i, (big, small) in enumerate(facts):
        kk = ease((t - t0 - 0.8 - i * 0.6) / 0.6)
        y = 400 + i * 150
        text(c, big, 1240, y, 54, "inter_light" if big[0].isdigit() else "sans_light", GOLD, a * kk, "l")
        text(c, small, 1240, y + 52, 24, "sans_reg", DIM, a * kk, "l", 2)
    text(c, "数据：巴菲特 2007 年致股东信", 1240, 840, 22, "sans_light", GREY, a, "l", 2)
    kh = ease((t - at("i8", "这个假设") + 0.1) / 0.5)
    if kh > 0:
        rrect(c, 300, 880, 1320, 70, 35, paint(GREEN, 0.12 * a * kh))
        check(c, 350, 915, 30, GREEN, a, kh, 4)
        text(c, "假设「有定价权」：经受住了几十年的检验", 400, 915, 30, "serif_bold", INK, a * kh, "l", 4)


# ================================================================ 终章
def scene_munger(ctx):
    t, c = ctx.t, ctx.c
    t0 = s("e1")
    a = win(t, t0 - 0.4, e("e1") + 0.3, 0.6, 0.5)
    if a <= 0:
        return
    text(c, "查理·芒格", CX, 300, 34, "serif_bold", GOLD, a, "c", 10)
    text(c, "我们的优势，不是努力变得非常聪明，", CX, 470, 56, "serif_bold", DIM, a, "c", 4, reveal=ease((t - t0 - 0.3) / 1.6))
    t2 = at("e1", "而是始终")
    text(c, "而是始终努力不做蠢事。", CX, 570, 64, "serif_black", INK, a, "c", 6, reveal=ease((t - t2) / 1.2),
         glow=0.3, glow_rgb=GOLD)
    text(c, "1989 年 Wesco 致股东信（大意）", CX, 680, 24, "sans_light", GREY, a * ease((t - t2 - 0.6) / 0.6), "c", 2)


def scene_less_wrong(ctx):
    t, c = ctx.t, ctx.c
    t0 = s("e2")
    a = win(t, t0 - 0.3, e("e2") + 0.4, 0.6, 0.5)
    if a <= 0:
        return
    k1 = ease((t - t0) / 0.7)
    tw = text(c, "永远正确", CX, 380, 84, "serif_black", INK, a * (1 - 0.6 * ease((t - at("e2", "而是让你")) / 0.4)), "c", 10,
              reveal=k1)
    ks = ease((t - at("e2", "而是让你") - 0.1) / 0.5)
    if ks > 0:
        c.drawLine(CX - tw / 2 - 20, 380, lerp(CX - tw / 2 - 20, CX + tw / 2 + 20, ks), 380, paint(RED, a, stroke=6))
    k2 = ease((t - at("e2", "错得更少") + 0.1) / 0.6)
    k3 = ease((t - at("e2", "改得更快") + 0.1) / 0.6)
    text(c, "错得更少", CX - 260, 600, 92, "serif_black", GOLD, a * k2, "c", 10, shader=E.gold_shader(550, 650),
         glow=0.4 * k2, glow_rgb=GOLD)
    text(c, "改得更快", CX + 260, 600, 92, "serif_black", GOLD, a * k3, "c", 10, shader=E.gold_shader(550, 650),
         glow=0.4 * k3, glow_rgb=GOLD)
    text(c, "·", CX, 600, 92, "serif_black", GOLD, a * k3, "c")


SCENES = [
    (T.SEC["correct"][0], e("k1") + 0.8, scene_light),
    (s("k2") - 0.3, e("k3") + 0.9, scene_ulcer),
    (s("k4") - 0.3, T.SEC["correct"][1], scene_feynman),
    (T.SEC["invest"][0], e("i3") + 1.0, scene_coins),
    (s("i4") - 0.3, e("i4") + 0.9, scene_village),
    (s("i5") - 0.3, e("i5") + 0.9, scene_confirm),
    (s("i6") - 0.3, e("i6") + 0.9, scene_darwin),
    (s("i7") - 0.3, e("i7") + 1.0, scene_steps),
    (s("i8") - 0.3, T.SEC["invest"][1], scene_sees),
    (s("e1") - 0.4, e("e1") + 0.9, scene_munger),
    (s("e2") - 0.3, e("e2") + 1.0, scene_less_wrong),
]
