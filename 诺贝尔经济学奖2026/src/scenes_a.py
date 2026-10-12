"""钩子 → 标题 → 01 反常（时间之桥、贷款、存款、悖论、分化、原因 → 预期）"""
import math

import numpy as np

from common import *          # noqa: F401,F403
from registry import scene
from timeline import CAP, HITS

CX = W / 2


def cap(key):
    return CAP[key]


def rich(fr, parts, cx, y, a=1.0, anchor='c', gap=10):
    """一行混排：parts = [(文字, 字体, 字号, 底色), ...]，整体按 anchor 对齐，竖直居中于 y"""
    ws = [text_size(s, f, z)[0] for s, f, z, _ in parts]
    total = sum(ws) + gap * (len(parts) - 1)
    x = cx - total / 2 if anchor == 'c' else (cx if anchor == 'l' else cx - total)
    for (s, f, z, base), w in zip(parts, ws):
        dy = z * 0.04 if f.startswith('inter') else 0
        fr.text(s, x + w / 2, y + dy, z, f, base, a, 'c', glow=0.2, shadow=0.5)
        x += w + gap
    return total


def num_unit(fr, x, y, num, unit, nsize, usize, base='gold', a=1.0, nfont='inter_xbold', ufont='sans_med',
             anchor='c', glow=0.25):
    wn = text_size(num, nfont, nsize)[0]
    wu = text_size(unit, ufont, usize)[0] if unit else 0
    gap = nsize * 0.08
    total = wn + (gap + wu if unit else 0)
    x0 = x - total / 2 if anchor == 'c' else x
    fr.text(num, x0 + wn / 2, y, nsize, nfont, base, a, 'c', glow=glow, shadow=0.5)
    if unit:
        fr.text(unit, x0 + wn + gap + wu / 2, y + nsize * 0.18, usize, ufont, base, a, 'c', glow=glow * 0.6,
                shadow=0.5)
    return total


def caption(fr, key, y, size=60, fname='serif_bold', t=None, a=1.0, base='white', fi=0.35, fo=0.3, lines=None,
            lh=1.38, stagger=True):
    """按 CAP 时间显示一条文案；lines 用 '|' 分行（默认按 '，' 自动分行）"""
    t0, t1, s = CAP[key]
    k = win(t, t0, t1, fi, fo) * a
    if k <= 0:
        return 0.0
    rows = lines if lines is not None else [s]
    n = len(rows)
    for i, row in enumerate(rows):
        yy = y + (i - (n - 1) / 2) * size * lh
        st = (t - t0 - i * 0.18, 0.035, 0.45) if stagger else None
        fr.text(row, CX, yy, size, fname, base, k, 'c', glow=0.22, shadow=0.6, stagger=st)
    return k


# ================================================================ 钩子 0–12
LPR = [4.85, 4.65, 4.45, 4.30, 4.20, 3.95, 3.60, 3.50]
LPR_T = [0.5 + 0.5 * k for k in range(8)]
LPR_PATH = [4.85, 4.80, 4.75, 4.65, 4.65, 4.60, 4.45, 4.30, 4.20, 3.95, 3.85, 3.60, 3.50]   # 2019.8 → 2025.5 每次调整


def hook_field_cam(t):
    z = -52 + t * 0.9
    return Cam((0, 5.5, z), (0, 0.4, z + 50), fov=58, cy=H * 0.70)


@scene(0.0, 12.0, 0.0, 0.25)
def sc_hook(fr, t, a):
    # 背景：夜色中的千万家庭
    dim = 1 - 0.6 * ss((t - 10.2) / 1.2)
    cam = hook_field_cam(t)
    FIELD.draw(fr, cam, t, a * 0.55 * dim, warm=np.full(FIELD.n, 0.85))
    draw_dust(fr, t, a * 0.6)
    # -------- 利率一降再降
    k = win(t, 0.0, 3.85, 0.3, 0.3) * a
    if k > 0:
        fr.text('贷款利率', CX, 600, 44, 'sans_med', 'grey', k, track=0.2, glow=0)
        i = max([j for j, tt in enumerate(LPR_T) if t >= tt] + [0])
        # 里程表式滚动
        p = eo((t - LPR_T[i]) / 0.22) if t >= LPR_T[0] else 1.0
        cur = f'{LPR[i]:.2f}%'
        fr.text(cur, CX, 790 + (1 - p) * 60, 240, 'inter_xbold', 'ice', k * p, glow=0.35)
        if i > 0 and p < 1:
            fr.text(f'{LPR[i - 1]:.2f}%', CX, 790 - p * 60, 240, 'inter_xbold', 'ice', k * (1 - p), glow=0.3)
        fr.text('一降再降', CX, 975, 76, 'serif_bold', 'white', k * win(t, 0.9, 4.0, 0.4, 0.2), glow=0.2)
        fr.text('5年期以上 LPR · 2019.8 → 2025.5', CX, 1052, 30, 'sans_reg', 'dim', k, track=0.05, glow=0)
        # 折线
        n = len(LPR_PATH)
        xs = np.linspace(200, 880, n)
        ys = 1130 + (4.85 - np.array(LPR_PATH)) / (4.85 - 3.5) * 120
        upto = cl((t - 0.5) / 3.1) * (n - 1)
        m = int(upto)
        pts = list(zip(xs[:m + 1], ys[:m + 1]))
        if m < n - 1:
            f = upto - m
            pts.append((lerp(xs[m], xs[m + 1], f), lerp(ys[m], ys[m + 1], f)))
        fr.stroke(pts, ICE, k * 0.9, 3, glow=0.8)
        fr.glow(pts[-1], 10, ICE_HI, k * 1.2)
        fr.disc(pts[-1], 5, ICE_HI, k)
    # -------- 可是，大家借的钱反而越来越少
    k = win(t, 4.0, 7.6, 0.25, 0.3) * a
    if k > 0:
        fr.text('可是，', CX, 430, 62, 'serif_bold', 'grey', k, stagger=(t - 4.0, 0.06, 0.35))
        fr.text('大家借的钱反而越来越少', CX, 528, 72, 'serif_black', 'white', k, stagger=(t - 4.25, 0.04, 0.4))
        base_y, hmax = 1180, 520
        for j, (yr, v, x) in enumerate((('2021', 7.92, 330), ('2025', 0.44, 750))):
            grow = eo((t - 4.3 - j * 0.15) / 0.6)
            hh = hmax * grow
            if j == 1:
                hh = hmax * grow * (1 - eio((t - 5.0) / 0.6) * (1 - v / 7.92))
            bw = 150
            bar_glass(fr, x - bw / 2, base_y - hh, x + bw / 2, base_y, GOLD, k)
            fr.text(yr, x, base_y + 44, 40, 'inter_bold', 'grey', k, glow=0)
            vv = 7.92 if j == 0 else lerp(7.92, v, eio((t - 5.0) / 0.6))
            num_unit(fr, x, base_y - hh - 56, f'{vv:.2f}', '万亿', 58, 30, 'gold', k)
        fr.text('居民新增贷款', CX, 1310, 34, 'sans_med', 'grey', k, track=0.1, glow=0)
        footnote(fr, '来源：中国人民银行', k)
    # -------- 钱，纷纷存进了银行
    k = win(t, 7.8, 10.4, 0.25, 0.25) * a
    if k > 0:
        fr.text('钱，纷纷存进了银行', CX, 470, 74, 'serif_black', 'white', k, stagger=(t - 7.8, 0.045, 0.4))
        p = eo((t - 8.0) / 1.6)
        num_unit(fr, CX, 740, f'{17.84 * p:.2f}', '万亿', 210, 76, 'ice', k, ufont='serif_bold', glow=0.4)
        fr.text('2022年 居民新增存款 · 历史最高', CX, 880, 38, 'sans_med', 'grey', k, track=0.05, glow=0)
        pour(fr, t, k)
        footnote(fr, '来源：中国人民银行', k)
    # -------- 这到底是为什么？
    k = win(t, 10.5, 12.2, 0.25, 0.05) * a
    if k > 0:
        p = eo((t - 10.5) / 0.55)
        fr.text('这到底是为什么？', CX, 900, 96, 'serif_black', 'white', k, scale=1.12 - 0.12 * p,
                blur=(1 - p) * 8, glow=0.35)
    fr.zoom = 1 + 0.05 * ei((t - 11.2) / 0.8)


def bar_glass(fr, x0, y0, x1, y1, col, a, th=2.5):
    """2D 发光玻璃柱"""
    if y1 - y0 < 1:
        fr.line((x0, y1), (x1, y1), col, a, th, glow=1.0)
        return
    fr.rrect_fill(x0, y0, x1, y1, 6, col * 0.22, a, glow=0.15)
    n = 12
    for k in range(n):         # 竖向渐变（上亮下暗）
        yy0 = y0 + (y1 - y0) * k / n
        yy1 = y0 + (y1 - y0) * (k + 1) / n
        fr.fill([(x0 + 3, yy0), (x1 - 3, yy0), (x1 - 3, yy1), (x0 + 3, yy1)], col * 0.10 * (1 - k / n), a)
    fr.rrect(x0, y0, x1, y1, 6, col, a * 0.9, th, glow=0.8)
    fr.line((x0 + 8, y0 + 2), (x1 - 8, y0 + 2), GOLD_HI if col is GOLD else ICE_HI, a, 3, glow=1.5)


_PR = np.random.default_rng(11)
POUR_N = 900
POUR_T0 = 7.9 + _PR.random(POUR_N) * 2.2
POUR_X = _PR.normal(0, 70, POUR_N)
POUR_V = 900 + _PR.random(POUR_N) * 500
POUR_SPL = _PR.normal(0, 1, (POUR_N, 2))


def pour(fr, t, a):
    """冰蓝光粒从上方倾泻进底部的「水位」"""
    level = 1260 - 70 * eo((t - 8.0) / 2.4)
    dt = t - POUR_T0
    alive = dt > 0
    y = 960 + POUR_V * dt + 300 * dt ** 2
    landed = y > level
    x = CX + POUR_X * (1 + 0.5 * dt)
    # 落入后溅开并沉入水面
    ls = np.clip((y - level) / POUR_V, 0, None)
    xs = np.where(landed, x + POUR_SPL[:, 0] * 120 * ls, x)
    ys = np.where(landed, level - np.abs(POUR_SPL[:, 1]) * 140 * ls + 600 * ls ** 2, y)
    al = np.where(landed, np.clip(1 - ls * 3, 0, 1), 1.0) * alive * a
    ok = al > 0.01
    fr.splat(xs[ok], ys[ok], ICE_HI, al[ok] * 0.9)
    fr.splat(xs[ok], ys[ok], ICE, al[ok] * 1.4, layer='B')
    # 水位面
    xx = np.linspace(170, 910, 60)
    yy = level + 6 * np.sin(xx * 0.03 + t * 6)
    fr.stroke(list(zip(xx, yy)), ICE, a * 0.9, 3, glow=1.2)
    fr.fill(list(zip(xx, yy)) + [(910, 1330), (170, 1330)], ICE * 0.10, a)


# ================================================================ 标题 12–20
def title_cam(t):
    p = eo((t - 12.0) / 2.2)
    z = lerp(-41.6, -8.0, p) + (t - 12.0) * 0.6
    y = lerp(5.5, 3.2, p)
    return Cam((0, y, z), (0, lerp(0.4, 2.2, p), z + 50), fov=58, cy=H * 0.70)


@scene(12.0, 20.0, 0.0, 0.5)
def sc_title(fr, t, a):
    lt = t - 12.0
    fr.flash = max(fr.flash, 0.85 * math.exp(-lt / 0.055) * a)
    fr.ca = 7 * math.exp(-lt / 0.2)
    cam = title_cam(t)
    # 地平线上的「明天」之光
    hx, hy, _, _ = cam.project([[0, 0, 400]])
    hy = float(hy[0])
    warm = np.clip(0.6 + 0.4 * (FIELD.P[:, 2] + 48) / 96, 0, 1)
    FIELD.draw(fr, cam, t, a * (0.9 - 0.3 * ss((t - 18.5) / 1.5)), warm=warm, size=1.2)
    k = a * eo(lt / 1.2)
    for s_, al in ((900, 0.10), (380, 0.18), (120, 0.35)):
        fr.glow((CX, hy), s_, GOLD, k * al)
    xs = np.linspace(-80, W + 80, 80)
    fr.stroke(list(zip(xs, np.full(80, hy))), GOLD_HI, k * 0.8, 2, glow=1.5)
    # 冲击波
    r = 1500 * eo(lt / 1.1)
    fr.circle((CX, 900), r, GOLD_HI, a * 0.7 * (1 - cl(lt / 1.1)), 3, glow=1.5)
    draw_dust(fr, t, a * 0.8, speed=3.0 * math.exp(-lt / 1.5) + 0.5)
    # 文字
    k = a * win(t, 12.3, 19.6, 0.5, 0.4)
    fr.text('2026 诺贝尔经济学奖', CX, 610, 46, 'serif_med', 'gold', k, track=0.28, glow=0.35,
            stagger=(t - 12.3, 0.05, 0.5))
    ln = 300 * eo((t - 12.7) / 0.9)
    def rule(img, k=k, ln=ln):
        if ln > 2:
            y = 676
            x0, x1 = int(CX - ln / 2), int(CX + ln / 2)
            img[y:y + 2, x0:x1] = img[y:y + 2, x0:x1] * (1 - 0.8 * k) + 0.8 * k * GOLD
    fr.overlay_fn(rule)
    fr.text('为什么你的【预期】，', CX, 800, 100, 'serif_black', 'white', k, glow=0.3,
            stagger=(t - 12.55, 0.06, 0.5))
    fr.text('决定了经济的【未来】？', CX, 935, 100, 'serif_black', 'white', k, glow=0.3,
            stagger=(t - 12.95, 0.06, 0.5))
    k2 = a * win(t, 13.8, 19.6, 0.8, 0.4)
    fr.text('Robert E. Hall  ·  Michael Woodford', CX, 1075, 40, 'corm_bold', 'subgold', k2, track=0.06, glow=0.2)
    fr.zoom = 1 + 0.035 * ss(lt / 7.5)


# ================================================================ 时间之桥 20–28
TODAY = np.array([0.0, 0.0, 0.0])
TMRW = np.array([0.0, 7.0, 62.0])


def bridge_pt(u, off=0.0, lift=0.0):
    u = np.asarray(u, np.float64)
    P = TODAY[None, :] * (1 - u[:, None]) + TMRW[None, :] * u[:, None]
    P[:, 1] += 2.2 * np.sin(np.pi * u) + lift
    P[:, 0] += off
    return P


_BR = np.random.default_rng(21)
BR_N = 1400
BR_U0 = _BR.random(BR_N)
BR_OX = _BR.normal(0, 0.55, BR_N)
BR_OY = _BR.normal(0, 0.35, BR_N) + 0.5
BR_SP = 0.8 + 0.4 * _BR.random(BR_N)
V = 0.085            # 每秒走过桥长的比例


def bridge_disp(t):
    """粒子沿桥的累计位移（负 = 明天→今天）：23.9–24.7 秒间速度由 −V 线性变到 +V"""
    ta, tb = 23.9, 24.7
    if t < ta:
        return -V * (t - 20.0)
    d0 = -V * (ta - 20.0)
    if t < tb:
        s = t - ta
        return d0 - V * s + V * s * s / (tb - ta)
    s = tb - ta
    return d0 - V * s + V * s * s / (tb - ta) + V * (t - tb)


def bridge_vel(t):
    ta, tb = 23.9, 24.7
    return -V if t < ta else (V if t > tb else lerp(-V, V, (t - ta) / (tb - ta)))


def bridge_cam(t):
    lt = t - 20.0
    return Cam((1.4 - lt * 0.12, 4.4, -17.0 + lt * 0.35), (0.0, 3.4, 30), fov=52, cy=H * 0.45)


@scene(20.0, 28.0, 0.4, 0.45)
def sc_bridge(fr, t, a):
    cam = bridge_cam(t)
    vel = bridge_vel(t)
    w = cl(0.5 - vel / (2 * V))          # 1 = 借（金），0 = 存（冰）
    col = GOLD * w + ICE * (1 - w)
    colhi = GOLD_HI * w + ICE_HI * (1 - w)
    # 桥：两条轨道 + 横枕
    u = np.linspace(0, 1, 120)
    for off in (-1.3, 1.3):
        x, y, z, s = cam.project(bridge_pt(u, off))
        ok = z > 0.5
        fr.stroke(list(zip(x[ok], y[ok])), col, a * 0.55, 2, glow=0.7)
    for uu in np.linspace(0.02, 0.98, 34):
        P = bridge_pt(np.array([uu, uu]), np.array([-1.3, 1.3]))
        P[1, 0] = 1.3
        P[0, 0] = -1.3
        x, y, z, s = cam.project(P)
        if (z > 0.5).all():
            fr.line((x[0], y[0]), (x[1], y[1]), col, a * 0.25 * (1 - uu * 0.6), 1.5, glow=0.4)
    # 平台
    for c, rad, lbl, sz, base in ((TODAY, 2.6, '今天', 58, 'white'), (TMRW, 4.6, '明天', 54, 'gold')):
        ang = np.linspace(0, 2 * np.pi, 90)
        P = np.c_[c[0] + rad * np.cos(ang), np.full(90, c[1]), c[2] + rad * np.sin(ang)]
        x, y, z, s = cam.project(P)
        fr.stroke(list(zip(x, y)), colhi if lbl == '今天' else GOLD, a * 0.9, 2.5, closed=True, glow=1.2)
        fr.fill(list(zip(x, y)), (colhi if lbl == '今天' else GOLD) * 0.06, a)
        px, py, pz, ps = cam.project([c + np.array([0, -1.5 if lbl == '今天' else 7.5, 0])])
        fr.text(lbl, float(px[0]), float(py[0]), sz, 'serif_bold', base, a, glow=0.4)
    px, py, _, _ = cam.project([TMRW + np.array([0, 0.5, 0])])
    fr.glow((float(px[0]), float(py[0])), 160, GOLD, a * 0.28)
    fr.glow((float(px[0]), float(py[0])), 40, GOLD_HI, a * 0.3)
    # 粒子流
    d = bridge_disp(t)
    uu = (BR_U0 + d * BR_SP) % 1.0
    P = bridge_pt(uu, BR_OX, BR_OY)
    x, y, z, s = cam.project(P)
    ok = z > 0.5
    fade_ends = np.clip(np.minimum(uu, 1 - uu) * 12, 0, 1)
    al = a * fade_ends * np.clip(s * 0.012, 0.15, 1.0)
    fr.splat(x[ok], y[ok], colhi, al[ok] * 1.3)
    fr.dots(x[ok], y[ok], np.clip(s[ok] * 0.07, 0.6, 3.0), col, al[ok] * 0.8, layer='B')
    draw_dust(fr, t, a * 0.5)
    # 文案
    k = a * win(t, *cap('br_borrow')[:2], 0.4, 0.3)
    if k > 0:
        fr.text('【借钱】', CX, 290, 128, 'serif_black', 'white', k, glow=0.45, stagger=(t - 20.5, 0.08, 0.5))
        fr.text('是把明天的钱，拿到今天花', CX, 420, 54, 'sans_med', 'white', k, track=0.04,
                stagger=(t - 20.8, 0.035, 0.4))
    k = a * win(t, *cap('br_save')[:2], 0.4, 0.4)
    if k > 0:
        fr.text('〔存钱〕', CX, 290, 128, 'serif_black', 'white', k, glow=0.45, stagger=(t - 24.2, 0.08, 0.5))
        fr.text('是把今天的钱，留给明天', CX, 420, 54, 'sans_med', 'white', k, track=0.04,
                stagger=(t - 24.5, 0.035, 0.4))


# ================================================================ 3D 柱状图（贷款 / 存款）
YEARS = ['2020', '2021', '2022', '2023', '2024', '2025', '2026上半年']
LOANS = [7.87, 7.92, 3.83, 4.33, 2.72, 0.44, -0.37]
LOAN_T = [28.6, 29.1, 32.0, 32.5, 33.0, 33.5, 34.0]
DEPS = [11.3, 9.9, 17.84, 16.67, 14.26, 14.64, None]
DEP_T = [36.3, 36.6, 37.0, 37.4, 37.8, 38.2, None]
BX = [-3.0 + 1.0 * i for i in range(7)]


def chart_cam(t):
    az = math.radians(lerp(-24, -10, ss((t - 28) / 16)))
    r = 15.0
    tgt = np.array([0.0, 1.9, 0.0])
    pos = tgt + np.array([r * math.sin(az), 3.4, -r * math.cos(az)])
    return Cam(pos, tgt, fov=50, cy=H * 0.43)


def bar3d(fr, cam, x, z, w, d, h, col, a, edge=1.0):
    """3D 玻璃柱：底面在 y=0，高 h（可为负）。按深度画可见面 + 发光棱。"""
    if abs(h) < 1e-3:
        return
    y0, y1 = (0.0, h) if h > 0 else (h, 0.0)
    xs = (x - w / 2, x + w / 2)
    zs = (z - d / 2, z + d / 2)
    V8 = np.array([[xs[i & 1], (y0, y1)[(i >> 1) & 1], zs[(i >> 2) & 1]] for i in range(8)])
    px, py, pz, ps = cam.project(V8)
    if (pz < 0.5).any():
        return
    P2 = np.c_[px, py]
    faces = {  # 顶点索引、亮度
        'top': ([2, 3, 7, 6], 1.0), 'front': ([0, 1, 3, 2], 0.55), 'left': ([0, 2, 6, 4], 0.35),
        'right': ([1, 5, 7, 3], 0.35), 'bottom': ([0, 4, 5, 1], 0.3), 'back': ([4, 6, 7, 5], 0.3)}
    cpos = cam.pos
    vis = []
    normals = {'top': (0, 1, 0), 'front': (0, 0, -1), 'left': (-1, 0, 0), 'right': (1, 0, 0), 'bottom': (0, -1, 0),
               'back': (0, 0, 1)}
    for name, (idx, lum) in faces.items():
        c3 = V8[idx].mean(0)
        if np.dot(np.array(normals[name]), cpos - c3) > 0:
            vis.append((np.linalg.norm(cpos - c3), name, idx, lum))
    vis.sort(reverse=True)
    for _, name, idx, lum in vis:
        pts = P2[idx]
        fr.fill(pts, col * (0.16 * lum), a)
        fr.stroke(pts, col, a * 0.75 * edge, 1.8, closed=True, glow=0.55 * edge)
    # 顶面高光
    top = P2[[2, 3, 7, 6]] if h > 0 else P2[[0, 1, 5, 4]]
    fr.stroke(top, GOLD_HI if col is GOLD else (ICE_HI if col is ICE else col), a * edge, 2.2, closed=True,
              glow=1.3 * edge)


def floor_grid(fr, cam, a, col=GREY):
    for xx in np.arange(-3.75, 3.76, 0.75):
        P = np.array([[xx, 0, -2.2], [xx, 0, 2.2]])
        x, y, z, s = cam.project(P)
        fr.line((x[0], y[0]), (x[1], y[1]), col, a * 0.12, 1)
    for zz in np.arange(-2.2, 2.21, 0.55):
        P = np.array([[-3.75, 0, zz], [3.75, 0, zz]])
        x, y, z, s = cam.project(P)
        fr.line((x[0], y[0]), (x[1], y[1]), col, a * 0.12, 1)
    P = np.array([[-3.8, 0, -0.45], [3.8, 0, -0.45]])
    x, y, z, s = cam.project(P)
    fr.line((x[0], y[0]), (x[1], y[1]), WHITE, a * 0.35, 1.5, glow=0.3)


def label_at(fr, cam, P, s, size, fname, base, a, dy=0):
    x, y, z, sc = cam.project([P])
    fr.text(s, float(x[0]), float(y[0]) + dy, size, fname, base, a, glow=0.15, shadow=0.6)
    return float(x[0]), float(y[0])


@scene(28.0, 36.0, 0.4, 0.0)
def sc_loans(fr, t, a):
    draw_chart(fr, t, a, phase='loans')


@scene(36.0, 44.0, 0.0, 0.4)
def sc_deposits(fr, t, a):
    draw_chart(fr, t, a, phase='deps')


def draw_chart(fr, t, a, phase):
    cam = chart_cam(t)
    gk = a * (1 - ss((t - 39.6) / 0.6))      # 40 秒前后图表让位给储蓄意愿圆环
    draw_dust(fr, t, a * 0.4)
    if gk > 0.01:
        floor_grid(fr, cam, gk)
        sink = ss((t - 36.0) / 0.7)           # 贷款柱下沉、存款柱升起
        for i, yr in enumerate(YEARS):
            # 贷款柱
            if t < 37.0:
                g = eback((t - LOAN_T[i]) / 0.7, 1.3) if t >= LOAN_T[i] else 0.0
                h = LOANS[i] * 0.55 * g * (1 - sink)
                col = GOLD if LOANS[i] > 0 else CORAL
                if abs(h) > 0.01:
                    bar3d(fr, cam, BX[i], 0, 0.62, 0.62, h, col, gk * (1 - sink))
                    if g > 0.3 and sink < 0.5:
                        top = np.array([BX[i], max(h, 0) + 0.35, 0])
                        label_at(fr, cam, top, f'{LOANS[i]:.2f}'.replace('-', '−'), 40, 'inter_bold',
                                 'gold' if h > 0 else 'coral', gk * cl((g - 0.3) / 0.4) * (1 - 2 * sink))
            # 存款柱
            if DEPS[i] is not None and t >= DEP_T[i] if DEP_T[i] else False:
                g = eback((t - DEP_T[i]) / 0.8, 1.2)
                h = DEPS[i] * 0.26 * g
                bar3d(fr, cam, BX[i], 0, 0.62, 0.62, h, ICE, gk, edge=1.0 + 0.6 * (i == 2) * pulse(t))
                if g > 0.3:
                    label_at(fr, cam, np.array([BX[i], h + 0.35, 0]), f'{DEPS[i]:.2f}', 40, 'inter_bold', 'ice',
                             gk * cl((g - 0.3) / 0.4))
            # 年份
            yk = gk if (t < 36 or DEPS[i] is not None) else gk * (1 - sink)
            if i < 6:
                label_at(fr, cam, np.array([BX[i], -0.05, -0.75]), yr, 30, 'inter_med', 'grey', yk, dy=26)
            else:
                label_at(fr, cam, np.array([BX[i], -0.05, -0.75]), '2026', 30, 'inter_med', 'grey', yk, dy=26)
                label_at(fr, cam, np.array([BX[i], -0.05, -0.75]), '上半年', 24, 'sans_med', 'grey', yk, dy=58)
    # ---- 文案
    if phase == 'loans':
        k = a * win(t, *cap('ln_past')[:2], 0.4, 0.3)
        if k > 0:
            fr.text('那几年，很多人敢借明天的钱', CX, 215, 56, 'serif_bold', 'white', k, stagger=(t - 28.3, 0.035, 0.4))
            for j, (s, ic) in enumerate((('贷款买房', 'house'), ('分期买车', 'car'), ('超前消费', 'card'))):
                kk = k * eo((t - 28.5 - 0.5 * j) / 0.4)
                cx = 205 + 335 * j
                chip(fr, '    ' + s, cx, 320, kk, GOLD, 38, scale=0.94 + 0.06 * kk)
                fr.overlay_draw(lambda cv, ic=ic, cx=cx, kk=kk: icon(cv, ic, (cx - 92, 320), 40, GOLD, kk, 2.5, glow=0))
        k = a * win(t, *cap('ln_now')[:2], 0.4, 0.3)
        if k > 0:
            fr.text('后来，大家借得越来越少', CX, 225, 60, 'serif_bold', 'white', k, stagger=(t - 32.0, 0.04, 0.4))
        k = a * win(t, *cap('ln_neg')[:2], 0.3, 0.3)
        if k > 0:
            chip(fr, '2026上半年 转为负数：还的，比借的多', CX, 1235, k, CORAL, 38, base='coral')
        k = a * win(t, 28.4, 36.4, 0.4, 0.3)
        fr.text('居民新增贷款（万亿元）', CX, 1320, 34, 'sans_med', 'grey', k, track=0.08, glow=0)
        footnote(fr, '来源：中国人民银行《金融统计数据报告》', k)
    else:
        k = a * win(t, *cap('dp_head')[:2], 0.4, 0.3)
        if k > 0:
            fr.text('钱，被存给了明天', CX, 225, 64, 'serif_bold', 'white', k, stagger=(t - 36.2, 0.05, 0.4))
        k = a * win(t, 37.3, 39.9, 0.3, 0.3)
        if k > 0:
            chip(fr, '2022年 17.84万亿 · 历史最高', CX, 1235, k, ICE, 38, base='ice')
        k = a * win(t, 36.0, 40.0, 0.01, 0.4)
        fr.text('居民新增存款（万亿元）', CX, 1320, 34, 'sans_med', 'grey', k, track=0.08, glow=0)
        footnote(fr, '来源：中国人民银行《金融统计数据报告》', k)
        gauge(fr, t, a)


def gauge(fr, t, a):
    k = a * win(t, 40.2, 43.9, 0.45, 0.35)
    if k <= 0:
        return
    c, R = (CX, 790), 270
    fr.text('想「更多储蓄」的城镇储户', CX, 300, 60, 'serif_bold', 'white', k, stagger=(t - 40.2, 0.04, 0.4))
    fr.arc(c, R, 0, 2 * np.pi, GREY, k * 0.18, 22)
    p1 = eo((t - 40.5) / 0.8) * 0.457
    p2 = 0.457 + eo((t - 41.6) / 1.0) * (0.618 - 0.457)
    a0 = -np.pi / 2
    fr.arc(c, R, a0, a0 + 2 * np.pi * p1, ICE * 0.55, k, 22, glow=0.5)
    if t > 41.6:
        fr.arc(c, R, a0 + 2 * np.pi * 0.457, a0 + 2 * np.pi * p2, ICE_HI, k, 24, glow=1.4)
        ang = a0 + 2 * np.pi * p2
        fr.glow((c[0] + R * math.cos(ang), c[1] + R * math.sin(ang)), 18, ICE_HI, k * 1.5)
    v = p2 * 100 if t > 41.6 else p1 * 100
    fr.text(f'{v:.1f}%', CX, 770, 150, 'inter_xbold', 'ice', k * cl((t - 40.45) / 0.25), glow=0.4)
    q = '2022年四季度' if t > 41.6 else '2019年四季度'
    fr.text(q, CX, 885, 38, 'sans_med', 'grey', k, glow=0)
    # 刻度注释
    a1 = a0 + 2 * np.pi * 0.457
    px, py = c[0] + (R + 70) * math.cos(a1), c[1] + (R + 70) * math.sin(a1)
    fr.text('45.7%', px - 10, py + 10, 34, 'inter_bold', 'ice', k * cl((t - 41.2) / 0.4) * 0.8, glow=0)
    fr.text('2019Q4', px - 10, py + 50, 26, 'inter_med', 'dim', k * cl((t - 41.2) / 0.4), glow=0)
    footnote(fr, '来源：中国人民银行 城镇储户问卷调查', k)


# ================================================================ 悖论 44–48
LPR_Y = [4.65, 4.65, 4.30, 4.20, 3.60, 3.50]
LOAN_Y = [7.87, 7.92, 3.83, 4.33, 2.72, 0.44]


@scene(44.0, 48.0, 0.3, 0.35)
def sc_paradox(fr, t, a):
    draw_dust(fr, t, a * 0.4)
    k = a * win(t, 44.1, 48.2, 0.35, 0.3)
    rich(fr, [('利率降了', 'serif_bold', 58, 'white'), ('1.35', 'inter_xbold', 76, 'ice'),
              ('个百分点', 'serif_bold', 58, 'white')], CX, 290, k)
    fr.text('5年期以上 LPR · 2019.8 → 2025.5', CX, 372, 30, 'sans_reg', 'dim', k, glow=0)
    xs = np.linspace(170, 910, 6)
    base = 1090
    p = cl((t - 44.3) / 1.4)
    for i, (x, v) in enumerate(zip(xs, LOAN_Y)):
        g = eo((p * 6 - i) / 1.2)
        hh = v / 7.92 * 330 * g
        bar_glass(fr, x - 34, base - hh, x + 34, base, GOLD, k * 0.9, 2)
        fr.text(f'{2020 + i}', x, base + 38, 30, 'inter_med', 'grey', k, glow=0)
    ys = 520 + (4.65 - np.array(LPR_Y)) / (4.65 - 3.5) * 230
    m = p * 5
    j = int(m)
    pts = list(zip(xs[:j + 1], ys[:j + 1]))
    if j < 5:
        pts.append((lerp(xs[j], xs[j + 1], m - j), lerp(ys[j], ys[j + 1], m - j)))
    fr.stroke(pts, ICE, k, 4, glow=1.2)
    for (x, y) in pts[:j + 1]:
        fr.disc((x, y), 7, ICE_HI, k)
    fr.text('贷款利率', 170, 470, 34, 'sans_bold', 'ice', k, anchor='l', glow=0.1)
    fr.text('居民新增贷款', 170, 640, 34, 'sans_bold', 'gold', k * cl((t - 44.8) / 0.4), anchor='l', glow=0.1)
    k2 = a * win(t, *cap('px_line')[:2], 0.4, 0.3)
    fr.text('钱〔更便宜〕了，人却【更谨慎】了', CX, 1250, 66, 'serif_black', 'white', k2, glow=0.3,
            stagger=(t - 44.6, 0.045, 0.45))
    footnote(fr, '利率为各年末5年期以上 LPR · 来源：中国人民银行', k)


# ================================================================ 分化 48–56
CARDS = [
    ('house', '新房销售额', '−12.6%', 'coral', '2025年 · 不到2021年高点一半'),
    ('plug', '家电零售额', '+11%', 'gold', '2025年 · 以旧换新拉动'),
    ('plane', '服务零售额', '+5.5%', 'gold', '2025年 · 商品零售 +3.8%'),
    ('wheat', '农村人均消费', '+5.3%', 'gold', '2025年实际增速 · 城镇 +3.7%'),
]


@scene(48.0, 56.0, 0.3, 0.4)
def sc_split(fr, t, a):
    lt = t - 48.0
    fr.flash = max(fr.flash, 0.25 * math.exp(-lt / 0.12) * a)
    draw_dust(fr, t, a * 0.5)
    k = a * win(t, *cap('sp_head')[:2], 0.4, 0.3)
    fr.text('但并不是所有人都不花钱', CX, 285, 58, 'serif_bold', 'white', k, stagger=(t - 48.2, 0.04, 0.4))
    for i, (ic, lbl, num, base, note) in enumerate(CARDS):
        kk = a * eo((t - 48.5 - 0.5 * i) / 0.5) * win(t, 48.3, 56.2, 0.01, 0.4)
        if kk <= 0.01:
            continue
        col = CORAL if base == 'coral' else GOLD
        x0 = 56 if i % 2 == 0 else 552
        y0 = 420 if i < 2 else 800
        y0 += (1 - kk) * 60 + 6 * math.sin(t * 1.3 + i * 1.7)
        x1, y1 = x0 + 472, y0 + 340
        fr.card(x0, y0, x1, y1, 30, kk, tint=col, border=col, border_a=0.55, fill_a=0.07, blur=14)
        fr.overlay_draw(lambda cv, ic=ic, x0=x0, y0=y0, col=col, kk=kk: icon(cv, ic, (x0 + 66, y0 + 70), 52, col, kk, 3, glow=0))
        fr.text(lbl, x0 + 116, y0 + 70, 38, 'sans_bold', 'white', kk, anchor='l', glow=0, shadow=0.3)
        val = float(num.replace('−', '-').replace('%', ''))
        cnt = val * eo((t - 48.6 - 0.5 * i) / 0.9)
        dec = 0 if num.endswith('11%') else 1
        txt = (('+' if val > 0 else '−') + f'{abs(cnt):.{dec}f}%')
        fr.text(txt, (x0 + x1) / 2, y0 + 190, 118, 'inter_xbold', base, kk, glow=0.35, shadow=0.3)
        sw = (t - 48.7 - 0.5 * i) / 0.9
        if 0 < sw < 1:
            def sheen(img, x0=x0, y0=y0, x1=x1, y1=y1, sw=sw, kk=kk):
                X0, Y0, X1, Y1 = int(x0) + 4, int(y0) + 4, int(x1) - 4, int(y1) - 4
                yy, xx = np.mgrid[Y0:Y1, X0:X1].astype(np.float32)
                pos = X0 - 200 + sw * (X1 - X0 + 400)
                img[Y0:Y1, X0:X1] += (np.exp(-((xx + (yy - Y0) * 0.5 - pos) / 40) ** 2) * 0.10 * kk)[..., None]
            fr.overlay_fn(sheen)
        fr.text(note, (x0 + x1) / 2, y0 + 292, 28, 'sans_reg', 'grey', kk, glow=0, shadow=0.3)
    k = a * win(t, *cap('sp_tail')[:2], 0.4, 0.4)
    fr.text('消费没有消失，而是在【分化】', CX, 1262, 64, 'serif_black', 'white', k, glow=0.3,
            stagger=(t - 52.0, 0.045, 0.45))
    footnote(fr, '来源：国家统计局、商务部（家电为限额以上单位口径）', a * win(t, 48.3, 56.2, 0.4, 0.4))


# ================================================================ 原因 → 预期 56–60
WORDS = ['收入', '就业', '房价', '债务', '人口', '社保', '物价', '补贴']
_CR = np.random.default_rng(4)
CS_N = 600
CS_W = _CR.integers(0, 8, CS_N)
CS_U = _CR.random(CS_N)


@scene(56.0, 60.0, 0.4, 0.25)
def sc_causes(fr, t, a):
    c = np.array([CX, 820.0])
    draw_dust(fr, t, a * 0.5)
    k = a * win(t, *cap('cs_head')[:2], 0.4, 0.25)
    fr.text('原因很多，但都绕不开一个词', CX, 330, 56, 'serif_bold', 'white', k, stagger=(t - 56.2, 0.04, 0.4))
    shrink = eio((t - 58.3) / 1.5)
    rx, ry = 380 * (1 - 0.8 * shrink), 165 * (1 - 0.8 * shrink)
    ang0 = (t - 56) * 0.35
    pos = []
    for i, w in enumerate(WORDS):
        q = ang0 + i * 2 * np.pi / 8
        x, y = c[0] + rx * math.cos(q), c[1] + ry * math.sin(q)
        depth = (math.sin(q) + 1) / 2          # 1 = 前
        pos.append((x, y, depth))
    order = np.argsort([p[2] for p in pos])
    for i in order:
        x, y, d = pos[i]
        kk = a * eo((t - 56.3 - 0.12 * i) / 0.4) * (1 - 0.85 * ss((t - 58.0) / 0.6))
        fr.line((x, y), tuple(c), GOLD, kk * 0.18, 1.2, glow=0.4)
        fr.text(WORDS[i], x, y, int(40 + 22 * d), 'serif_bold', 'white', kk * (0.55 + 0.45 * d), glow=0.15)
    # 沿连线向心流动的光粒
    P = np.array([(p[0], p[1]) for p in pos])
    u = (CS_U + (t - 56) * 0.5) % 1.0
    src = P[CS_W]
    xy = src * (1 - u[:, None]) + c[None, :] * u[:, None]
    fr.splat(xy[:, 0], xy[:, 1], GOLD, a * 0.6 * np.sin(np.pi * u) * cl((t - 56.4) / 0.5))
    # 预期
    kk = a * cl((t - 58.0) / 0.25)
    if kk > 0:
        p = eo((t - 58.0) / 0.7)
        fr.glow(tuple(c), 260 * p, GOLD, kk * 0.25)
        fr.circle(tuple(c), 60 + 600 * eo((t - 58.0) / 1.0), GOLD_HI, kk * (1 - cl((t - 58.0) / 1.0)), 3, glow=1.2)
        fr.text('【预期】', CX, c[1], 190, 'serif_black', 'white', kk, scale=1.35 - 0.35 * p, blur=(1 - p) * 6,
                glow=0.55)
        fr.flash = max(fr.flash, 0.2 * math.exp(-(t - 58.0) / 0.1))
    fr.zoom = 1 + 0.06 * ei((t - 59.2) / 0.8)
