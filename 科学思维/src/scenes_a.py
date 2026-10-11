"""序章与标题：棋盘阴影错觉 → 华盛顿与两千年的放血疗法 → 「科学思维」。"""
import math

import cv2
import numpy as np
import skia

import engine as E
import timeline as T
from engine import (W, H, CX, CY, INK, DIM, GREY, CYAN, GOLD, RED, GREEN, clip01, ease, ease_out, ease_io,
                    lerp, mixc, win, text, paint, line)

s, e = T.s, T.e

# ================================================================ 0 钩子：一只眼睛 + 四记重拍上的四行大字
HOOK = ["h1", "h2", "h3", "h4"]
EYE_C = (CX, 420)
_r = np.random.default_rng(1799)
IRIS_N = 260
IRIS_ANG = np.sort(_r.random(IRIS_N)) * math.tau
IRIS_L = 0.55 + 0.45 * _r.random(IRIS_N)
IRIS_COL = _r.random(IRIS_N)
CRACKS = []
for k in range(7):                       # 「一定是真的吗？」时，虹膜上裂开的纹路
    ang = k * math.tau / 7 + _r.random() * 0.5
    pts = [(math.cos(ang) * 40, math.sin(ang) * 40)]
    r_ = 40.0
    for _ in range(6):
        r_ += 40 + _r.random() * 40
        ang += (_r.random() - 0.5) * 0.5
        pts.append((math.cos(ang) * r_, math.sin(ang) * r_))
    CRACKS.append(pts)


def _almond(cx, cy, w, h):
    p = skia.Path()
    p.moveTo(cx - w / 2, cy)
    p.cubicTo(cx - w * 0.22, cy - h, cx + w * 0.22, cy - h, cx + w / 2, cy)
    p.cubicTo(cx + w * 0.22, cy + h, cx - w * 0.22, cy + h, cx - w / 2, cy)
    p.close()
    return p


def scene_hook(ctx):
    t, c = ctx.t, ctx.c
    end = T.SEC["hook"][1]
    a = 1 - ease((t - end + 0.25) / 0.25)
    t1, t2, t3, t4 = (s(k) for k in HOOK)
    cx, cy = EYE_C
    # 每一记重拍：眼睛猛地一缩一张
    punch = sum(math.exp(-(t - tk) / 0.18) for tk in (t1, t2, t3, t4) if t >= tk)
    open_ = ease_out((t - t1 + 0.05) / 0.9, 3) * (1 - 0.12 * punch)
    W_, H_ = 980, 290 * open_
    ek = ease_out((t - t4) / 0.35, 3)            # 最后一问：眼睛上移、缩小，给四行字让位
    c.save()
    c.translate(cx, cy - 95 * ek)
    c.scale(1 - 0.22 * ek, 1 - 0.22 * ek)
    c.translate(-cx, -cy)
    # 闭眼时的一道光缝
    if open_ < 0.98:
        c.drawLine(cx - W_ / 2, cy, cx + W_ / 2, cy, paint(CYAN, a * (1 - open_) * 0.9, stroke=2, blur=1))
        c.drawLine(cx - W_ / 2, cy, cx + W_ / 2, cy, paint(CYAN, a * (1 - open_) * 0.5, stroke=10, blur=12))
    lid = _almond(cx, cy, W_, H_)
    c.drawPath(lid, paint(CYAN, 0.08 * a * open_, blur=40))
    c.save()
    c.clipPath(lid, doAntiAlias=True)
    c.drawPath(lid, paint((0.02, 0.03, 0.06), a))
    # 虹膜：放射状光纹，随时间缓慢转动
    rot = t * 0.08
    R0, R1 = 70, 210 * (1 + 0.04 * punch)
    k4 = ease((t - t4) / 0.25)
    for i in range(IRIS_N):
        ang = IRIS_ANG[i] + rot
        r1 = R0 + (R1 - R0) * IRIS_L[i]
        col = mixc(mixc(CYAN, (0.35, 0.55, 1.0), IRIS_COL[i]), GOLD, 0.3 * IRIS_COL[i] ** 3)
        col = mixc(col, RED, 0.6 * k4 * IRIS_COL[i])
        c.drawLine(cx + math.cos(ang) * R0, cy + math.sin(ang) * R0, cx + math.cos(ang) * r1, cy + math.sin(ang) * r1,
                   paint(col, a * (0.35 + 0.4 * IRIS_COL[i]), stroke=2.2))
    c.drawCircle(cx, cy, R1, paint(CYAN, 0.6 * a, stroke=2))
    c.drawCircle(cx, cy, R1 + 8, paint(CYAN, 0.25 * a, stroke=10, blur=12))
    c.drawCircle(cx, cy, R0 * (1 - 0.15 * punch), paint((0, 0, 0), a))
    c.drawCircle(cx - 26, cy - 30, 16, paint((1, 1, 1), 0.85 * a, blur=2))
    # 裂纹
    if k4 > 0:
        for pts in CRACKS:
            p = skia.Path()
            p.moveTo(cx + pts[0][0], cy + pts[0][1])
            for (x, y) in pts[1:]:
                p.lineTo(cx + x, cy + y)
            c.drawPath(p, paint((1, 0.85, 0.8), a, stroke=2.2, trim=(0, k4)))
            c.drawPath(p, paint(RED, 0.6 * a, stroke=7, blur=8, trim=(0, k4)))
    c.restore()
    c.drawPath(lid, paint(INK, 0.55 * a * open_, stroke=2))
    c.restore()
    # 四行大字：新的一行在重拍上砸下来，旧的一行上移变淡
    for i, k in enumerate(HOOK):
        tk = s(k)
        if t < tk - 0.02:
            continue
        txt = T.TEXT[k]
        age = sum(1 for kk in HOOK[i + 1:] if t >= s(kk) - 0.02)
        kin = ease_out((t - tk) / 0.22, 3)
        kup = ease_out((t - s(HOOK[i + age]) if age else 0) / 0.3, 3) if age else 0.0
        y = 830 - (age - 1 + kup) * 58 - (0 if age == 0 else 40) + 30 * (1 - kin) + 20 * ek
        last = i == 3
        size = (96 if last else 76) * lerp(1.35, 1.0, kin) * (0.55 if age else 1.0) * (1 - 0.1 * max(0, age - 1))
        al = a * kin * (1.0 if age == 0 else 0.42 if age == 1 else 0.2)
        if last:
            text(c, txt, CX, y, size, "serif_black", GOLD, al, "c", 14, shader=E.gold_shader(y - 60, y + 40),
                 glow=0.6, glow_rgb=GOLD)
        else:
            text(c, txt, CX, y, size, "serif_black", INK, al, "c", 12, glow=0.25 if age == 0 else 0, glow_rgb=CYAN)


# ================================================================ 1 冷开场：华盛顿与放血疗法
def _bust_path(x0, y0, sc=1.0):
    p = skia.Path()
    def P(x, y):
        return x0 + x * sc, y0 + y * sc
    p.moveTo(*P(200, 30))
    p.cubicTo(*P(255, 30), *P(285, 80), *P(282, 135))
    p.cubicTo(*P(280, 190), *P(258, 228), *P(236, 240))
    p.lineTo(*P(238, 272))
    p.cubicTo(*P(300, 290), *P(372, 300), *P(392, 360))
    p.lineTo(*P(400, 520))
    p.lineTo(*P(0, 520))
    p.lineTo(*P(8, 360))
    p.cubicTo(*P(28, 300), *P(100, 290), *P(162, 272))
    p.lineTo(*P(164, 240))
    p.cubicTo(*P(142, 228), *P(120, 190), *P(118, 135))
    p.cubicTo(*P(115, 80), *P(145, 30), *P(200, 30))
    p.close()
    return p


BLEEDS = [0.38, 0.53, 0.53, 0.95]       # 四次放血（升）：约 12–14、18、18、32 盎司，合计约 2.4 L
BODY_L = 6.0                             # 估计全身血量（升），2.4 / 6 ≈ 40%


def _bleed_times():
    """四次放血落在四个连续的半小节上（与鼓点同步）。"""
    a = T.at("b2", "医生为他")
    return [a + i * 2 * T.BEAT for i in range(4)]


BLEED_T = _bleed_times()


def drained(t):
    v = 0.0
    for bt, amt in zip(BLEED_T, BLEEDS):
        v += amt * ease((t - bt) / 0.9)
    return v


def dot_grid(c, cx, cy, t, t_start, dur, rate, seed, label=None, label_rgb=INK, a=1.0, n=10, sp=34, r=10.5,
             sick=RED, well=GREEN):
    """10×10 病人点阵：从 t_start 起，在 dur 内按随机顺序变绿，最终比例 rate。"""
    rng = np.random.default_rng(seed)
    order = rng.permutation(n * n)
    k = int(round(rate * n * n))
    when = {int(order[i]): t_start + dur * (i / max(1, k)) ** 0.9 for i in range(k)}
    x0 = cx - (n - 1) * sp / 2
    y0 = cy - (n - 1) * sp / 2
    done = 0
    for idx in range(n * n):
        gx, gy = idx % n, idx // n
        x, y = x0 + gx * sp, y0 + gy * sp
        appear = ease((t - (t_start - 1.0) - (gx + gy) * 0.012) / 0.5)
        if appear <= 0:
            continue
        kk = ease((t - when[idx]) / 0.35) if idx in when else 0.0
        if kk > 0.5:
            done += 1
        col = E.mixc(sick, well, kk)
        c.drawCircle(x, y, r * (0.6 + 0.4 * appear) * (1 + 0.25 * math.sin(math.pi * kk)), paint(col, a * appear))
    return done


def scene_blood(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = T.SEC["blood"]
    # ---- 时光倒流：2026 → 1799
    a_year = win(t, t0 + 0.05, s("b2") + 0.2, 0.4, 0.4)
    if a_year > 0:
        k = ease_io((t - t0 - 0.3) / (s("b2") - t0 + 0.2))
        yr = int(round(lerp(2026, 1799, k)))
        y_c = lerp(CY - 30, 250, ease((t - s("b2") - 0.2) / 0.9))
        size = lerp(200, 92, ease((t - s("b2") - 0.2) / 0.9))
        text(c, str(yr), CX, y_c, size, "inter_thin", INK, a_year, "c", 4)
        # 刻度尺随年份滚动
        if t < s("b2") + 0.3:
            for i in range(-30, 31):
                yv = yr + i
                x = CX + i * 32 - (lerp(2026, 1799, k) - yr) * 32
                big = yv % 10 == 0
                al = a_year * (1 - abs(i) / 31) * 0.7 * (1 - ease((t - s("b2")) / 0.3))
                line(c, x, CY + 120, x, CY + 120 + (26 if big else 12), INK, al, 1.4)
                if big:
                    text(c, str(yv), x, CY + 172, 18, "inter_light", DIM, al)
    # ---- 华盛顿：血量计
    a_b = win(t, s("b2") + 0.4, e("b3") + 0.6, 0.8, 0.7)
    if a_b > 0:
        bx, by, sc = 520, 300, 1.0
        path = _bust_path(bx, by, sc)
        lv = 1 - drained(t) / BODY_L                     # 剩余比例
        dead = ease((t - s("b3") - 0.3) / 1.2)
        c.save()
        c.clipPath(path, doAntiAlias=True)
        top, bot = by + 30, by + 520
        surface_y = bot - (bot - top) * lv
        wave = skia.Path()
        wave.moveTo(bx - 10, bot + 10)
        for i in range(0, 43):
            x = bx - 10 + i * 10
            wave.lineTo(x, surface_y + 5 * math.sin(i * 0.5 + t * 3.0) * (1 - dead))
        wave.lineTo(bx + 420, bot + 10)
        wave.close()
        red = E.mixc((0.78, 0.08, 0.12), (0.30, 0.10, 0.12), dead)
        c.drawPath(wave, paint(red, 0.85 * a_b))
        c.restore()
        c.drawPath(path, paint(E.mixc(INK, GREY, dead), 0.75 * a_b, stroke=2.2))
        c.drawPath(path, paint(E.mixc(RED, GREY, dead), 0.25 * a_b, stroke=6, blur=8))
        text(c, "乔治·华盛顿", bx + 200, by - 40, 30, "serif_bold", INK, a_b, "c", 6)
        text(c, "1799 年 12 月 14 日 · 弗农山庄", bx + 200, by - 2, 18, "sans_light", DIM, a_b, "c", 2)
        # 右侧：四次放血
        gx = 1080
        text(c, "放血记录", gx, 330, 22, "sans_med", DIM, a_b, "l", 6)
        for i, (bt, amt) in enumerate(zip(BLEED_T, BLEEDS)):
            k = ease((t - bt + 0.2) / 0.5)
            if k <= 0:
                continue
            y = 390 + i * 64
            text(c, f"第 {i + 1} 次", gx, y, 24, "sans_reg", INK, a_b * k, "l")
            bw = amt / 1.0 * 360 * ease((t - bt) / 0.9)
            E.rrect(c, gx + 120, y - 9, max(bw, 1), 18, 9, paint((0.85, 0.12, 0.16), a_b * k))
            text(c, f"{amt:.2f} L", gx + 130 + bw + 12, y, 20, "mono", DIM, a_b * k, "l")
        tot = drained(t)
        kk = ease((t - BLEED_T[0] + 0.3) / 0.5)
        text(c, f"{tot:.1f}", gx, 700, 96, "inter_thin", (1.0, 0.45, 0.45), a_b * kk, "l")
        text(c, "升  ≈  全身血量的 " + f"{100 * tot / BODY_L:.0f}%", gx + 175, 712, 26, "sans_reg", INK,
             a_b * kk, "l", 2)
        text(c, "史料记载合计约 80 盎司；血量按约 6 升估算", gx, 776, 16, "sans_light", GREY, a_b * kk * 0.9,
             "l", 1)
        # 心电线：当晚拉平
        if t > s("b3") - 0.6:
            ka = ease((t - s("b3") + 0.6) / 0.5) * a_b
            pa = skia.Path()
            y0 = 868
            pa.moveTo(400, y0)
            for i in range(240):
                x = 400 + i * 5
                ph = (x - t * 420) % 260
                amp = (1 - dead) * (60 if 120 < ph < 128 else -22 if 128 <= ph < 136 else 8 * math.sin(ph / 9) if ph < 40 else 0)
                pa.lineTo(x, y0 - amp)
            c.drawPath(pa, paint(E.mixc(RED, GREY, dead), 0.8 * ka, stroke=2))
            text(c, "1799.12.14 · 夜", 1600, 830, 22, "inter_light", INK, ka * dead, "r", 3)

    # ---- 两千年：时间轴
    a_tl = win(t, s("b4") - 0.2, s("b4") + 2.5, 0.6, 0.4)
    if a_tl > 0:
        k = ease_io((t - s("b4") + 0.2) / 2.6)
        x0, x1, y = 260, 1660, 520
        line(c, x0, y, x1, y, INK, 0.35 * a_tl, 2, k)
        marks = [(0.0, "公元前 5 世纪", "希波克拉底医派"), (0.33, "2 世纪", "盖伦"), (0.66, "中世纪—18 世纪", "欧洲医院的常规疗法"),
                 (1.0, "1799", "华盛顿")]
        for (p, a_, b_) in marks:
            kk = ease((k - p) / 0.12 + 0.5)
            x = lerp(x0, x1, p)
            c.drawCircle(x, y, 7, paint((0.9, 0.2, 0.25), a_tl * kk))
            c.drawCircle(x, y, 18, paint((0.9, 0.2, 0.25), 0.3 * a_tl * kk, blur=10))
            text(c, a_, x, y - 50, 24, "inter_light" if a_[0].isdigit() else "sans_reg", INK, a_tl * kk)
            text(c, b_, x, y + 50, 20, "sans_light", DIM, a_tl * kk)
        text(c, "2000+ 年", CX, 360, 64, "inter_thin", GOLD, a_tl * ease((k - 0.6) / 0.3), "c", 6)
    # ---- 放过血的病人，大多数都好了 / 不放血也会好
    a_g = win(t, s("b4") + 3.2, T.SEC["blood"][1] - 0.3, 0.6, 0.3)
    if a_g > 0:
        split = ease_io((t - s("b5") + 0.1) / 0.9)
        cxL = lerp(CX, 620, split)
        n1 = dot_grid(c, cxL, 540, t, s("b4") + 4.0, 3.6, 0.8, 5, a=a_g)
        text(c, "放血", cxL, 330, 30, "serif_bold", (1, 0.5, 0.5), a_g, "c", 8)
        text(c, f"康复 {n1}%", cxL, 760, 34, "inter_light", GREEN, a_g * ease((t - s("b4") - 4.0) / 0.4), "c", 2)
        if split > 0:
            n2 = dot_grid(c, 1300, 540, t, s("b5") + 1.1, 2.4, 0.82, 9, a=a_g * split)
            text(c, "不放血", 1300, 330, 30, "serif_bold", CYAN, a_g * split, "c", 8)
            text(c, f"康复 {n2}%", 1300, 760, 34, "inter_light", GREEN, a_g * ease((t - s("b5") - 1.1) / 0.4), "c", 2)
            text(c, "示意数据：多数疾病本来就会自行好转", CX, 820, 18, "sans_light", GREY, a_g * split * 0.9, "c", 2)
        # 对照
        kc = ease((t - s("b6") - 0.9) / 0.6)
        if kc > 0:
            text(c, "对照", CX, 540, 120 + 10 * (1 - kc), "serif_black", GOLD, a_g * kc, "c", 10,
                 shader=E.gold_shader(480, 600), glow=0.5, glow_rgb=GOLD)
            text(c, "CONTROL", CX, 640, 22, "corm6", E.SUBGOLD, a_g * kc, "c", 12)


# ================================================================ 标题
def scene_title(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = T.SEC["title"]
    a = ease((t - t0) / 0.25) * (1 - ease((t - t1 + 0.5) / 0.5))
    k = ease_out((t - t0) / 1.6)
    # 放射光线
    for i in range(36):
        ang = i * math.tau / 36 + t * 0.05
        L = 900 * k
        c.drawLine(CX, CY - 20, CX + math.cos(ang) * L, CY - 20 + math.sin(ang) * L,
                   paint(GOLD, 0.05 * a * (0.5 + 0.5 * math.sin(i * 2.7)), stroke=2, blur=3))
    sc = lerp(1.25, 1.0, k)
    c.save()
    c.translate(CX, CY - 30)
    c.scale(sc, sc)
    c.translate(-CX, -(CY - 30))
    text(c, "科学思维", CX, CY - 40, 168, "serif_black", GOLD, a, "c", 24, shader=E.gold_shader(CY - 120, CY + 30),
         glow=0.45 * (1 + 2 * math.exp(-(t - t0) / 0.3)), glow_rgb=GOLD, reveal=ease((t - t0) / 0.8))
    c.restore()
    text(c, "S C I E N T I F I C   T H I N K I N G", CX, CY + 92, 22, "corm6", E.SUBGOLD,
         a * ease((t - t0 - 0.6) / 0.6), "c", 2)
    text(c, "一场关于「如何不被自己欺骗」的旅程", CX, CY + 150, 28, "serif_light", INK,
         a * ease((t - t0 - 1.2) / 0.6), "c", 6, reveal=ease((t - t0 - 1.2) / 1.0))
    # 流光扫过标题
    sh = clip01((t - t0 - 1.4) / 1.2)
    if 0 < sh < 1:
        x = lerp(CX - 500, CX + 500, ease_io(sh))
        c.drawRect(skia.Rect.MakeXYWH(x - 40, CY - 160, 80, 240),
                   paint((1, 0.95, 0.8), 0.10 * a, blur=30, blend="add"))
    # 粒子从四周汇入
    rng = np.random.default_rng(4)
    n = 1400
    ang = rng.random(n) * math.tau
    r0 = 500 + rng.random(n) * 700
    kk = ease_out((t - t0 + rng.random(n) * 0.4) / 1.4)
    r = r0 * (1 - kk) + 40 * kk
    P = np.c_[CX + np.cos(ang) * r * 1.6, CY - 40 + np.sin(ang) * r]
    al = (1 - kk) * a * 0.9
    ctx.splat(P, al[:, None] * np.array(GOLD, np.float32)[None, :] * 1.6)


SCENES = [
    (0.0, T.SEC["hook"][1], scene_hook),
    (T.SEC["blood"][0], T.SEC["blood"][1], scene_blood),
    (T.SEC["title"][0], T.SEC["title"][1], scene_title),
]
