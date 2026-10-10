"""序章与标题：棋盘阴影错觉 → 华盛顿与两千年的放血疗法 → 「科学思维」。"""
import math

import cv2
import numpy as np
import skia

import engine as E
import timeline as T
from engine import (W, H, CX, CY, INK, DIM, GREY, CYAN, GOLD, RED, GREEN, clip01, ease, ease_out, ease_io,
                    lerp, win, text, paint, line)

s, e = T.s, T.e

# ================================================================ 0 钩子：棋盘阴影错觉
# 按 Adelson（1995）的构造原理自行绘制：亮格反射率 L、暗格 D，阴影系数 S = D / L，
# 于是「阴影里的亮格 B」与「光照下的暗格 A」像素值完全相同（L·S = D）。
LIGHT, DARK = 0.82, 0.47
SHADOW = DARK / LIGHT
GROUND = np.float32([[0, 0], [5, 0], [5, 5], [0, 5]])
QUAD = np.float32([[960, 935], [1530, 650], [960, 385], [390, 650]])
HOMO = cv2.getPerspectiveTransform(GROUND, QUAD)
HINV = np.linalg.inv(HOMO)
CYL = (4.0, 1.0)            # 圆柱站在棋盘右侧，光从右后方照来
A_TILE, B_TILE = (3, 4), (2, 2)


def g2s(u, v):
    p = HOMO @ np.array([u, v, 1.0])
    return p[0] / p[2], p[1] / p[2]


def _shadow(u, v):
    """地面上的软阴影：从圆柱朝左后方延伸的一条带。返回 0..1 的遮挡度。"""
    du, dv = u - CYL[0], v - CYL[1]
    d_perp = np.abs(du + dv) / math.sqrt(2)
    d_along = (-du + dv) / math.sqrt(2)
    half = 0.62 + 0.18 * np.maximum(d_along, 0)          # 越远越宽
    soft = 0.10 + 0.10 * np.maximum(d_along, 0)          # 半影越远越软
    k = np.clip((half - d_perp) / soft + 0.5, 0, 1)
    k = k * k * (3 - 2 * k)
    k *= np.clip((d_along + 0.2) / 0.5, 0, 1)
    k = np.maximum(k, np.clip((0.62 - np.hypot(du, dv)) / 0.1, 0, 1))   # 圆柱脚下
    return k


def _board():
    ss = 2
    yy, xx = np.mgrid[0:H * ss, 0:W * ss].astype(np.float64) / ss
    den = HINV[2, 0] * xx + HINV[2, 1] * yy + HINV[2, 2]
    u = (HINV[0, 0] * xx + HINV[0, 1] * yy + HINV[0, 2]) / den
    v = (HINV[1, 0] * xx + HINV[1, 1] * yy + HINV[1, 2]) / den
    inside = (u >= 0) & (u < 5) & (v >= 0) & (v < 5)
    i, j = np.floor(u).astype(int), np.floor(v).astype(int)
    refl = np.where((i + j) % 2 == 0, LIGHT, DARK)
    sh = _shadow(u, v)
    val = refl * (1 - sh * (1 - SHADOW))
    img = np.zeros((H * ss, W * ss, 4), np.float32)
    img[..., :3] = val[..., None]
    img[..., 3] = inside
    img[..., :3] *= img[..., 3:4]
    small = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)
    # 不透明区域内保持精确值：A、B 格内部像素必须完全一样
    return small


BOARD = _board()


def _board_rgba_u8(kA=1.0):
    a = BOARD[..., 3:4]
    rgb = np.where(a > 1e-4, BOARD[..., :3] / np.maximum(a, 1e-4), 0)
    out = np.dstack([rgb, a])
    return (out * 255 + 0.5).astype(np.uint8)


BOARD_IMG = E.image_from(_board_rgba_u8())


def _tile_path(tile, inset=0.0):
    i, j = tile
    pts = [g2s(i + inset, j + inset), g2s(i + 1 - inset, j + inset), g2s(i + 1 - inset, j + 1 - inset),
           g2s(i + inset, j + 1 - inset)]
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    p.close()
    return p


def _draw_cylinder(c, a):
    bx, by = g2s(*CYL)
    rx, ry = 66, 33
    h = 290
    body = skia.Rect.MakeLTRB(bx - rx, by - h, bx + rx, by)
    c.saveLayerAlpha(None, int(255 * a))
    a = 1.0
    sh = skia.GradientShader.MakeLinear([skia.Point(bx - rx, 0), skia.Point(bx + rx, 0)],
                                        [E.c4((0.06, 0.18, 0.10)), E.c4((0.16, 0.42, 0.24)), E.c4((0.42, 0.80, 0.50)),
                                         E.c4((0.30, 0.64, 0.38))], [0, 0.35, 0.78, 1])
    c.drawOval(skia.Rect.MakeLTRB(bx - rx, by - ry, bx + rx, by + ry), paint(shader=sh, a=a))
    c.drawRect(body, paint(shader=sh, a=a))
    c.drawOval(skia.Rect.MakeLTRB(bx - rx, by - h - ry, bx + rx, by - h + ry), paint((0.42, 0.78, 0.50), a))
    c.restore()


def _draw_board_edges(c, a):
    # 棋盘的两个侧面，增加立体感
    th = 26
    for (p0, p1, col) in ((QUAD[3], QUAD[0], (0.20, 0.20, 0.22)), (QUAD[0], QUAD[1], (0.13, 0.13, 0.15))):
        pa = skia.Path()
        pa.moveTo(*p0)
        pa.lineTo(*p1)
        pa.lineTo(p1[0], p1[1] + th)
        pa.lineTo(p0[0], p0[1] + th)
        pa.close()
        c.drawPath(pa, paint(col, a))


def scene_hook(ctx):
    t, c = ctx.t, ctx.c
    ctx.bloom, ctx.vign, ctx.bg = 0.0, 0.0, 0.0   # 关闭后期：A、B 两格的像素必须严格相等
    end = T.SEC["hook"][1]
    a_in = ease((t - 0.2) / 1.2) * (1 - ease((t - end + 0.25) / 0.25))
    t_rev = s("h3")                       # 「但它们，是同一种灰」
    k_bar = ease((t - t_rev + 0.1) / 0.7)
    k_dim = ease((t - t_rev - 0.6) / 0.9)
    zoom = 1.0 + 0.035 * ease_io(t / end)
    c.save()
    c.translate(CX, 640)
    c.scale(zoom, zoom)
    c.translate(-CX, -640)
    board_a = a_in * (1 - 0.9 * k_dim)
    _draw_board_edges(c, board_a)
    c.drawImage(BOARD_IMG, 0, 0, skia.SamplingOptions(), paint(INK, board_a))
    _draw_cylinder(c, board_a)
    # A、B 两格在其余部分变暗后仍保留原样
    if k_dim > 0:
        for tile in (A_TILE, B_TILE):
            c.drawPath(_tile_path(tile, 0.02), paint((DARK, DARK, DARK), a_in))
    # 连接 A、B 的等色条：同一种灰
    ax, ay = g2s(A_TILE[0] + 0.5, A_TILE[1] + 0.5)
    bx, by = g2s(B_TILE[0] + 0.5, B_TILE[1] + 0.5)
    if k_bar > 0:
        p = paint((DARK, DARK, DARK), a_in)
        ex, ey = lerp(ax, bx, k_bar), lerp(ay, by, k_bar)
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy)
        nx, ny = -dy / L * 16, dx / L * 16
        band = skia.Path()
        band.moveTo(ax + nx, ay + ny)
        band.lineTo(ex + nx, ey + ny)
        band.lineTo(ex - nx, ey - ny)
        band.lineTo(ax - nx, ay - ny)
        band.close()
        c.drawPath(band, p)
    c.restore()

    # 标注：A、B（引线 + 圆圈字母），不覆盖格子本身
    k_lab = ease((t - s("h1") + 0.2) / 0.5) * a_in
    for (tile, lab, dx, dy) in ((A_TILE, "A", -230, -60), (B_TILE, "B", -330, 120)):
        x, y = g2s(tile[0] + 0.5, tile[1] + 0.5)
        x, y = CX + (x - CX) * zoom, 640 + (y - 640) * zoom
        lx, ly = x + dx, y + dy
        hot = lab == "A" and s("h2") < t < s("h3")
        col = E.GOLD if hot or k_bar > 0.5 else INK
        c.drawCircle(x, y, 5, paint(col, k_lab))
        line(c, x, y, lx + 26 * (1 if dx < 0 else -1), ly, col, 0.8 * k_lab, 1.6, ease((t - s("h1")) / 0.6))
        c.drawCircle(lx, ly, 26, paint(col, 0.9 * k_lab, stroke=2))
        text(c, lab, lx, ly, 30, "inter_med", col, k_lab)
        if k_dim > 0:
            text(c, "RGB 122 · 122 · 122", lx, ly + 54, 20, "mono", E.GOLD, k_dim * a_in)
    # 「哪一个更深？」时画面里一枚小问号
    text(c, "棋盘阴影错觉 · 按 E. Adelson（1995）原理重绘", 1856, 1046, 16, "sans_light", GREY,
         0.6 * a_in, "r", 1)


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
    t0, t1 = s("b2"), e("b2")
    a = t0 + (t1 - t0) * 0.42
    return [a + i * (t1 - a) / 4.2 for i in range(4)]


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
