"""序章与标题：一只睁开又碎裂的眼睛 → 返航战机的弹孔（幸存者偏差）→ 「科学思维」。"""
import math

import cv2
import numpy as np
import skia

import engine as E
import timeline as T
from engine import (W, H, CX, CY, INK, DIM, GREY, CYAN, GOLD, RED, GREEN, clip01, ease, ease_out, ease_io,
                    ease_in, lerp, mixc, win, text, paint, line, cross, arrow)

s, e, at = T.s, T.e, T.at

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


# ================================================================ 1 冷开场：返航战机的弹孔（幸存者偏差）
# 俯视的四发战机（蓝图风格，原创绘制）。局部坐标：机头朝上，原点在机身中心。
def _plane_parts():
    fus = skia.Path()
    fus.moveTo(0, -300)
    fus.cubicTo(30, -296, 38, -250, 38, -200)
    fus.lineTo(34, 250)
    fus.cubicTo(30, 290, 12, 305, 0, 306)
    fus.cubicTo(-12, 305, -30, 290, -34, 250)
    fus.lineTo(-38, -200)
    fus.cubicTo(-38, -250, -30, -296, 0, -300)
    fus.close()
    wing = skia.Path()
    for sg in (1, -1):
        wing.moveTo(sg * 30, -80)
        wing.lineTo(sg * 505, -38)
        wing.cubicTo(sg * 520, -34, sg * 520, -10, sg * 505, -6)
        wing.lineTo(sg * 30, 40)
        wing.close()
    tail = skia.Path()
    for sg in (1, -1):
        tail.moveTo(sg * 28, 228)
        tail.lineTo(sg * 175, 254)
        tail.cubicTo(sg * 186, 256, sg * 186, 278, sg * 175, 280)
        tail.lineTo(sg * 28, 292)
        tail.close()
    engines = [(x, -66) for x in (-330, -165, 165, 330)]
    eng = skia.Path()
    for (x, y) in engines:
        eng.addOval(skia.Rect.MakeLTRB(x - 24, y - 62, x + 24, y + 50))
    cock = skia.Path()
    cock.addOval(skia.Rect.MakeLTRB(-20, -268, 20, -206))
    return fus, wing, tail, eng, cock, engines


FUS, WING, TAIL, ENG, COCK, ENGINES = _plane_parts()


def _holes():
    """返航飞机的弹孔（示意）：集中在机翼、机身中段、尾翼；发动机与驾驶舱几乎没有。"""
    r = np.random.default_rng(1943)
    pts = []
    while len(pts) < 170:
        x, y = r.uniform(-520, 520), r.uniform(-300, 306)
        if ENG.contains(x, y) or COCK.contains(x, y) or (abs(y + 66) < 75 and any(abs(x - ex) < 40 for ex, _ in ENGINES)):
            continue
        if WING.contains(x, y) or TAIL.contains(x, y) or (FUS.contains(x, y) and -190 < y < 280):
            pts.append((x, y))
    pts.append((-330 + 12, -40))       # 发动机上只零星两个
    pts.append((165 - 10, -90))
    order = r.permutation(len(pts))
    return np.array(pts)[order], r.random(len(pts))


HOLES, HOLE_R = _holes()
PLANE_C = (CX, 560)


def _plane(c, cx, cy, sc, a, rot=0.0, col=CYAN, fill=0.10, glow=True, dash=False):
    c.save()
    c.translate(cx, cy)
    c.rotate(rot)
    c.scale(sc, sc)
    for p in (WING, TAIL, FUS):
        c.drawPath(p, paint((0.04, 0.07, 0.12), 0.9 * a))
        c.drawPath(p, paint(col, fill * a))
    for p in (WING, TAIL, FUS, ENG):
        pp = paint(col, 0.85 * a, stroke=2.0 / sc, dash=([10 / sc, 7 / sc], 0) if dash else None)
        c.drawPath(p, pp)
        if glow:
            c.drawPath(p, paint(col, 0.25 * a, stroke=7 / sc, blur=8 / sc))
    c.drawPath(ENG, paint((0.04, 0.07, 0.12), 0.9 * a))
    c.drawPath(ENG, paint(col, 0.85 * a, stroke=2.0 / sc, dash=([10 / sc, 7 / sc], 0) if dash else None))
    c.drawPath(COCK, paint(col, 0.35 * a))
    # 蓝图细节：翼梁与桁条
    for sg in (1, -1):
        c.drawLine(sg * 40, -40, sg * 500, -22, paint(col, 0.22 * a, stroke=1 / sc))
    for y in range(-160, 260, 40):
        c.drawLine(-30, y, 30, y, paint(col, 0.12 * a, stroke=1 / sc))
    c.restore()


def _year_roll(c, t, t0, t_end, target):
    a_year = win(t, t0 + 0.05, t_end, 0.3, 0.4)
    if a_year <= 0:
        return
    k = ease_io((t - t0 - 0.1) / (t_end - t0 - 0.2))
    yr = int(round(lerp(2026, target, k)))
    text(c, str(yr), CX, CY - 30, 200, "inter_thin", INK, a_year, "c", 4)
    for i in range(-30, 31):
        yv = yr + i
        x = CX + i * 32 - (lerp(2026, target, k) - yr) * 32
        big = yv % 10 == 0
        al = a_year * (1 - abs(i) / 31) * 0.7
        line(c, x, CY + 120, x, CY + 120 + (26 if big else 12), INK, al, 1.4)
        if big:
            text(c, str(yv), x, CY + 172, 22, "inter_light", DIM, al)


def scene_wald(ctx):
    t, c = ctx.t, ctx.c
    t0, t1 = T.SEC["wald"]
    _year_roll(c, t, t0, s("w1") + 0.3, 1943)
    a = win(t, s("w1") + 0.2, t1 - 0.3, 0.8, 0.3)
    if a <= 0:
        return
    cx, cy = PLANE_C
    # 战机入场：从下方滑入、微微倾斜回正
    kin = ease_out((t - s("w1") - 0.2) / 1.6, 3)
    t_ghost = s("w8")
    t_row = s("w10")
    k_row = ease_io((t - t_row + 0.1) / 0.8)
    sc = lerp(0.62, 0.78, kin) * (1 - 0.45 * k_row)
    px = cx + lerp(0, -360, k_row)
    py = cy + 120 * (1 - kin) + lerp(0, -40, k_row)
    rot = -8 * (1 - kin)
    # 蓝图网格
    ag = a * 0.5 * (1 - k_row)
    for gx in range(160, 1780, 80):
        line(c, gx, 160, gx, 960, CYAN, 0.05 * ag, 1)
    for gy in range(160, 980, 80):
        line(c, 160, gy, 1760, gy, CYAN, 0.05 * ag, 1)
    _plane(c, px, py, sc, a, rot)
    text(c, "返航战机 · 弹孔分布（示意）", 160, 190, 22, "sans_reg", DIM, a * kin * (1 - k_row), "l", 2)
    # 弹孔：在 w3–w4 两句里按八分音符一批批出现
    h0, h1 = s("w3"), e("w4")
    n_show = int(len(HOLES) * clip01((t - h0) / (h1 - h0)))
    beat_q = T.q(t, "floor")
    c.save()
    c.translate(px, py)
    c.rotate(rot)
    c.scale(sc, sc)
    for i in range(n_show):
        x, y = HOLES[i]
        th = h0 + (h1 - h0) * i / len(HOLES)
        pop = ease_out((t - th) / 0.18, 2)
        r = (5 + 4 * HOLE_R[i]) * (1 + 0.6 * (1 - pop))
        c.drawCircle(x, y, r * 2.2, paint(RED, 0.25 * a * pop, blur=6))
        c.drawCircle(x, y, r, paint((1.0, 0.32, 0.30), a * pop))
        c.drawCircle(x, y, r * 0.45, paint((0.08, 0.02, 0.02), a * pop))
    # 「哪里弹孔多，就加固哪里」：机翼 / 机身 / 尾翼铺上橙色装甲
    k_arm = ease((t - at("w5", "哪里弹孔多") + 0.1) / 0.5)
    k_flip = ease((t - s("w6")) / 0.35)
    if k_arm > 0:
        orange = (1.0, 0.6, 0.2)
        for p in (WING, TAIL, FUS):
            c.drawPath(p, paint(orange, 0.22 * a * k_arm * (1 - 0.8 * k_flip)))
            c.drawPath(p, paint(orange, 0.8 * a * k_arm * (1 - 0.8 * k_flip), stroke=3 / sc, dash=([12 / sc, 8 / sc], t * 30)))
        c.drawPath(ENG, paint((0.04, 0.07, 0.12), a))
        c.drawPath(ENG, paint(CYAN, 0.85 * a, stroke=2.0 / sc))
    # 发动机：真正要加固的地方
    k_eng = ease((t - at("w7", "发动机") + 0.1) / 0.4)
    if k_eng > 0:
        pulse = 0.5 + 0.5 * math.sin((t - at("w7", "发动机")) * math.tau / T.BEAT)
        for (x, y) in ENGINES:
            c.drawOval(skia.Rect.MakeLTRB(x - 30, y - 70, x + 30, y + 58), paint(GOLD, 0.35 * a * k_eng))
            c.drawOval(skia.Rect.MakeLTRB(x - 30, y - 70, x + 30, y + 58), paint(GOLD, a * k_eng, stroke=4 / sc))
            c.drawCircle(x, y - 6, (70 + 30 * pulse) * k_eng, paint(GOLD, 0.35 * a * k_eng * (1 - k_row), stroke=3 / sc, blur=3))
    c.restore()
    if k_arm > 0:
        lx, ly = CX + 620, 400
        gone = 1 - ease((t - at("w7", "发动机")) / 0.4)
        text(c, "加固这里？", lx, ly, 44, "serif_black", (1.0, 0.65, 0.3), a * k_arm * (1 - 0.6 * k_flip) * gone, "c", 8)
        arrow(c, lx - 40, ly + 40, CX + 260, 520, (1.0, 0.65, 0.3), a * k_arm * (1 - 0.6 * k_flip) * gone, 3, k_arm, 16)
        if k_flip > 0:
            cross(c, lx, ly, 80, RED, a * (1 - ease((t - at("w7", "发动机")) / 0.4)), k_flip, 7)
    kc = ease_out((t - s("w6")) / 0.3, 3) * (1 - ease((t - at("w7", "发动机") + 0.2) / 0.4))
    if kc > 0:
        text(c, "恰恰相反", CX, 190, 96 * lerp(1.3, 1.0, kc), "serif_black", GOLD, a * kc, "c", 16,
             shader=E.gold_shader(140, 240), glow=0.6, glow_rgb=GOLD)
    if k_eng > 0:
        text(c, "发动机：几乎没有弹孔", CX, 190, 52, "serif_black", GOLD, a * k_eng * (1 - k_row), "c", 8,
             shader=E.gold_shader(160, 220))
    # 发动机中弹的飞机：没能飞回来
    k_g = win(t, t_ghost - 0.1, t_row + 0.6, 0.3, 0.5)
    if k_g > 0:
        for j, (gx, gy0, ph) in enumerate(((330, 260, 0.0), (1590, 300, 0.3), (230, 700, 0.6), (1690, 760, 0.9),
                                           (520, 900, 1.2), (1420, 950, 1.5))):
            tg = t_ghost + ph * 1.2
            kk = clip01((t - tg) / 3.5)
            if t < tg:
                continue
            fall = ease_in(kk, 2)
            gx_ = gx + 60 * fall * (1 if gx < CX else -1)
            gy = gy0 + 420 * fall
            gr = (25 + 40 * fall) * (1 if gx < CX else -1)
            ga = a * k_g * (1 - ease((kk - 0.6) / 0.4)) * ease(kk / 0.1)
            _plane(c, gx_, gy, 0.2, ga * 0.55, gr, col=RED, fill=0.05, glow=False)
            # 发动机上的弹孔 + 拖烟
            ang = math.radians(gr)
            ex, ey = ENGINES[j % 4]
            hx = gx_ + 0.2 * (ex * math.cos(ang) - ey * math.sin(ang))
            hy = gy + 0.2 * (ex * math.sin(ang) + ey * math.cos(ang))
            c.drawCircle(hx, hy, 6, paint((1.0, 0.45, 0.3), ga))
            for k_ in range(10):
                c.drawCircle(hx - k_ * 6 * (1 if gx < CX else -1) * 0.3, hy - k_ * 14, 6 + k_ * 2.2,
                             paint((0.5, 0.5, 0.55), ga * 0.12 * (1 - k_ / 10), blur=6))
        text(c, "发动机中弹的飞机 —— 没有飞回来", CX, 960 - 40, 28, "sans_med", RED, k_g * a * (1 - k_row), "c", 2)
    # 幸存者偏差
    k_sb = ease((t - s("w9") + 0.1) / 0.5) * (1 - k_row)
    if k_sb > 0:
        text(c, "幸存者偏差", CX + 580, 330, 60, "serif_black", GOLD, a * k_sb, "c", 12, shader=E.gold_shader(295, 365),
             glow=0.4, glow_rgb=GOLD)
        text(c, "SURVIVORSHIP BIAS", CX + 580, 395, 22, "corm6", E.SUBGOLD, a * k_sb, "c", 6)
    # 看得见的一半 / 看不见的一半
    if k_row > 0:
        text(c, "看得见的：飞回来的", px, 860, 30, "sans_med", CYAN, a * k_row, "c", 2)
        for j in range(4):
            kk = ease((t - t_row - 0.3 - j * 0.15) / 0.5)
            _plane(c, 1060 + j * 200, 540, 0.17, a * kk * 0.8, 0, col=(0.6, 0.62, 0.7), fill=0.0, glow=False, dash=True)
        text(c, "看不见的：没飞回来的", 1360, 860, 30, "sans_med", DIM, a * ease((t - t_row - 0.5) / 0.5), "c", 2)
        line(c, CX - 40, 380, CX - 40, 900, INK, 0.2 * a * k_row, 1.5)


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
    (T.SEC["wald"][0], T.SEC["wald"][1], scene_wald),
    (T.SEC["title"][0], T.SEC["title"][1], scene_title),
]
