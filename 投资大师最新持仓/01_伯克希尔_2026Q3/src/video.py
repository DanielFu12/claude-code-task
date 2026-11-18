"""投资大师最新持仓 EP.01 · 巴菲特 / 伯克希尔·哈撒韦 2026Q3 13F —— 竖屏 1080×1920 动态图形短片

每个 sc_* 函数是一个镜头；时间点全部来自 timeline.py（对齐到音乐节拍），数据全部来自 data.py（SEC 13F 原始申报）。
"""
import math, os, sys
import numpy as np, cv2
from engine import *
from timeline import *
import data as D

NFR = int(DUR * FPS)
CX = W / 2

# ============================================================== 配色
UP = C(70, 228, 165)        # 增持
DOWN = C(255, 92, 98)       # 减持
NEWC = C(96, 178, 255)      # 新进
DIM = C(120, 130, 155)
INK = C(200, 206, 220)
GOLDS = [lerpc(GOLD2, C(150, 92, 30), (i / 9) ** 0.9) for i in range(10)]
OTHER = C(70, 80, 105)
MINUS = '−'


def beat_dt(t):
    i = np.searchsorted(BEATS, t, 'right') - 1
    return t - BEATS[i] if i >= 0 else 9.0

def beat_pulse(t, decay=0.13):
    return math.exp(-beat_dt(t) / decay)

def energy(t):
    return keys(t, [(0, .35), (T_S3, .35), (T_S3 + .1, .15), (T_DROP1, 1), (T_S9, 1), (T_S9 + .2, .45),
                    (T_S10, .45), (T_S10 + .1, .1), (T_DROP2, 1), (T_END, 1), (T_END + .5, .3)])

def sa(t, a, b, fi=0.45, fo=0.4):
    """镜头整体透明度（进入、退出都缓动）"""
    return env(t, a, b, fi, fo)

def wan(n):
    """股数格式化：亿 / 万"""
    if n >= 1e8: return f'{n / 1e8:.2f}亿'
    return f'{n / 1e4:.0f}万'

def yi(v, d=1):
    return f'{v / 1e8:,.{d}f}'

def pct(a, b):
    return (b - a) / a * 100


# ============================================================== 背景：深色星云 + 透视网格 + 金色微尘
NB1 = fbm(270, 480, 11, 6, 3); NB2 = fbm(270, 480, 22, 6, 3); NB3 = fbm(270, 480, 33, 5, 5)
BGK = [  # 时间, 主色, 副色, 强度
    (0, (60, 45, 18), (14, 22, 50), .55), (T_S2, (22, 38, 80), (40, 30, 15), .7),
    (T_S3, (18, 20, 40), (30, 22, 12), .5), (T_DROP1 - .3, (10, 10, 22), (16, 12, 8), .35),
    (T_DROP1, (150, 105, 35), (40, 50, 110), 1.4), (T_DROP1 + 2.5, (85, 62, 24), (22, 36, 85), .95),
    (T_S5, (20, 40, 90), (60, 45, 20), .85), (T_S7, (14, 60, 90), (25, 40, 100), .9),
    (T_S8, (12, 70, 70), (20, 45, 95), .9), (T_S9, (90, 22, 30), (30, 20, 50), .8),
    (T_S10 - .2, (60, 18, 25), (25, 18, 40), .6), (T_S10 + .3, (10, 10, 16), (16, 12, 10), .3),
    (T_DROP2 - .2, (14, 12, 16), (20, 15, 10), .35), (T_DROP2, (160, 112, 40), (60, 40, 110), 1.45),
    (T_SIG1, (80, 60, 25), (25, 35, 80), .95), (T_SIG2, (15, 65, 70), (60, 45, 22), .9),
    (T_SIG3, (70, 25, 35), (20, 40, 90), .85), (T_OUTRO, (80, 60, 25), (25, 30, 70), .9),
    (T_END, (40, 50, 110), (70, 52, 20), .8), (DUR, (20, 22, 45), (30, 24, 12), .5)]
_yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
BASE = (np.array([6, 8, 17], np.float32) * (1 - _yy) + np.array([3, 4, 9], np.float32) * _yy) / 255
_y2, _x2 = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_x2 - W / 2) / (W * 0.62)) ** 2 + ((_y2 - H * 0.47) / (H * 0.6)) ** 2)
VIGNETTE = np.clip(1 - 0.5 * _r ** 2.2, 0.22, 1)[..., None].astype(np.float32)
del _y2, _x2, _r, _yy


def bg_at(t):
    a = keys(t, [(k[0], k[1]) for k in BGK]); b = keys(t, [(k[0], k[2]) for k in BGK])
    I = keys(t, [(k[0], k[3]) for k in BGK]) * (1 + 0.15 * beat_pulse(t, .22) * energy(t))
    s = 1.06 + 0.04 * math.sin(t * 0.09)
    M = np.float32([[s, 0, -8 - 7 * math.sin(t * .05)], [0, s, -14 - 12 * math.cos(t * .04)]])
    n1 = cv2.warpAffine(NB1, M, (270, 480), borderMode=cv2.BORDER_REFLECT)
    M2 = np.float32([[s, 0, -8 + 7 * math.sin(t * .06 + 1)], [0, s, -14 + 12 * math.sin(t * .035)]])
    n2 = cv2.warpAffine(NB2, M2, (270, 480), borderMode=cv2.BORDER_REFLECT)
    d = (0.55 + 0.8 * NB3)[..., None]
    img = ((n1 ** 3)[..., None] * np.array(a, np.float32) + (n2 ** 3.2)[..., None] * np.array(b, np.float32)) * d
    img *= I * 0.5 / 255.0
    return BASE + cv2.resize(img, (W, H), interpolation=cv2.INTER_LINEAR)


def grid_floor(f, t):
    """画面下部缓慢前移的透视网格（数据地形感）"""
    a = 0.055 * (0.6 + 0.4 * energy(t)) * env(t, 0.5, DUR - 0.5, 1.5, 1.0)
    if a < 0.003: return
    hy, by = 1240, 1980
    for k in range(-9, 10):
        f.line((CX + k * 40, hy), (CX + k * 260, by), GOLD, a * 0.8, 1)
    sp = (t * 0.25) % 1
    for k in range(9):
        z = (k + 1 - sp) / 9
        y = hy + (by - hy) * z ** 2.2
        f.line((0, y), (W, y), GOLD, a * z, 1)


_DR = np.random.default_rng(3)
ND = 900
DU_X = _DR.uniform(0, W, ND); DU_Y = _DR.uniform(0, H, ND); DU_Z = _DR.uniform(0.3, 1.0, ND); DU_P = _DR.uniform(0, 6.28, ND)
DU_C = np.array([lerpc(GOLD2, WHITE, u) for u in _DR.uniform(0, .5, ND)], np.float32)

def dust(f, t):
    y = (DU_Y - t * 26 * DU_Z) % H
    x = DU_X + 14 * np.sin(t * 0.3 + DU_P)
    tw = 0.45 + 0.55 * np.sin(t * 1.7 + DU_P * 3) ** 2
    al = DU_Z ** 2 * tw * (0.20 + 0.25 * beat_pulse(t, .2) * energy(t))
    f.splat(x, y, DU_C, al, 'E')


# ============================================================== 通用特效
_BR = np.random.default_rng(77)
BURST = {s: (_BR.uniform(0, 2 * math.pi, 900), _BR.uniform(0.15, 1, 900) ** 0.6, _BR.uniform(0.4, 1.2, 900),
             _BR.integers(0, 6, 900)) for s in range(8)}

def burst(f, t, t0, cx, cy, cols, seed=0, n=700, speed=1300, life=1.2, drag=2.4, a=1.0):
    dt = t - t0
    if dt < 0 or dt > life * 2.4: return
    th, v, lf, ci = (x[:n] for x in BURST[seed])
    cc = np.array(cols, np.float32)[ci % len(cols)]
    for k in range(4):
        d = max(dt - k * 0.018, 0)
        r = speed * v * (1 - math.exp(-drag * d)) / drag
        al = np.exp(-d / (life * lf)) * a * (1 - k * 0.22)
        f.splat(cx + r * np.cos(th), cy + r * np.sin(th), cc, al * 1.4, 'E')

_IR = np.random.default_rng(91)
IMP = (_IR.uniform(0, 2 * math.pi, 1400), _IR.uniform(0.35, 1.25, 1400), _IR.uniform(0, 0.45, 1400), _IR.integers(0, 6, 1400))

def implode(f, t, t0, t1, cx, cy, cols, a=1.0, R0=700, turns=2.0):
    if t < t0 or t > t1: return
    p = (t - t0) / (t1 - t0)
    th, rr, dl, ci = IMP
    cc = np.array(cols, np.float32)[ci % len(cols)]
    for k in range(4):
        pk = np.clip((p - k * 0.008 - dl) / (1 - dl), 0, 1)
        r = R0 * rr * (1 - (pk ** 3) ** 0.9)
        ang = th + turns * pk ** 3
        al = np.where(pk > 0, np.minimum(pk * 6, 1), 0) * (1 - pk ** 8) * a * (1 - k * 0.2)
        f.splat(cx + r * np.cos(ang), cy + r * np.sin(ang), cc, al * 1.3, 'E')
    f.glow((cx, cy), 20 + 110 * ei(p), GOLD2, 0.2 + 0.8 * ei(p), 'B')

def shockwaves(f, t):
    for ti, k in IMPACTS:
        dt = t - ti
        if 0 <= dt < 1.3:
            cy = H * 0.47
            for j, (dd, sc) in enumerate(((0, 1.0), (0.1, 0.6), (0.2, 0.35))):
                d2 = dt - dd
                if d2 < 0: continue
                r = 30 + 1300 * eo(d2 / 1.1)
                al = (1 - cl(d2 / 1.1)) ** 1.6 * k * sc
                f.circle((CX, cy), r, GOLD2 if j == 0 else GOLD, al, 3 if j == 0 else 2)
            f.flash += k * 0.38 * math.exp(-dt / 0.14)
            f.ca += k * 8 * math.exp(-dt / 0.22)

def sweep(f, t):
    """转场光扫：一道柔和的横向光带自上而下扫过，配合低沉 whoosh"""
    for tc in CUTS:
        p = (t - (tc - 0.30)) / 0.55
        if 0 <= p <= 1:
            y = -100 + (H + 200) * eio(p)
            al = math.sin(p * math.pi)
            ys = slice(int(max(y - 120, 0)), int(min(y + 120, H)))
            if ys.stop > ys.start:
                g = np.exp(-((np.arange(ys.start, ys.stop) - y) / 55.0) ** 2)[:, None, None]
                f.B[ys] += g * np.array(GOLD, np.float32) * 0.10 * al
            f.line((0, y), (W, y), GOLD2, 0.55 * al, 1)

def punch(t):
    """重拍处的镜头推拉：返回缩放系数"""
    s = 1.0
    for ti, k in IMPACTS:
        dt = t - ti
        if 0 <= dt < 1.2: s += 0.045 * k * math.exp(-dt / 0.28)
    for tc in CUTS:
        dt = t - tc
        if 0 <= dt < 0.8: s += 0.012 * math.exp(-dt / 0.2)
    return s


# ============================================================== 文本 / 图形小组件
def runs(f, parts, x, y, a=1.0, anchor='m', mode='L', glow=0.0, t0=None, stag=0.03, rise=16, out=None):
    """多字体混排一行，基线对齐。parts: [(str, font, size, colour 或 grad 列表)]；y = 最大字号的视觉中心"""
    if a <= 0.003: return 0
    ws = [text_width(s, fn, sz) for s, fn, sz, c in parts]
    tw = sum(ws)
    big = max(sz for _, _, sz, _ in parts)
    base = y + big * 0.36
    xs = x - tw / 2 if anchor == 'm' else (x if anchor == 'l' else x - tw)
    k = 0
    for (s, fn, sz, c), w in zip(parts, ws):
        g = c if isinstance(c, list) else None
        col = WHITE if g else c
        yy = base - sz * 0.36
        f.text(s, xs, yy, sz, fn, col, a, 'l', mode=mode, glow=glow, grad=g,
               t0=None if t0 is None else t0 + k * stag, stag=stag, rise=rise, out=out)
        k += len(s); xs += w
    return tw

def eyebrow(f, s, y, a, t0=None, col=GOLD):
    """小标题：两侧细线 + 等宽英文/中文"""
    if a <= 0.003: return
    tw = text_width(s, 'sans_med', 26, 0.25)
    p = 1 if t0 is None else eo((f.t - t0) / 0.6)
    L = 70 * p
    f.line((CX - tw / 2 - 24 - L, y), (CX - tw / 2 - 24, y), col, a * 0.8, 1)
    f.line((CX + tw / 2 + 24, y), (CX + tw / 2 + 24 + L, y), col, a * 0.8, 1)
    f.text(s, CX, y, 26, 'sans_med', col, a, track=0.25, t0=t0, stag=0.02)

def headline(f, s, y, a, t0=None, size=76, grad=None, out=None):
    f.text(s, CX, y, size, 'serif_black', WHITE, a, grad=grad or [WHITE, lerpc(WHITE, GOLD2, .5)], t0=t0,
           stag=0.045, dur=0.5, rise=26, out=out, glow=0.12)

def box(f, x0, y0, x1, y1, col, a, fill=0.0, buf='L', glow=0.0):
    if a <= 0.003 or x1 - x0 < 0.5 or y1 - y0 < 0.5: return
    f.fillpoly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], col, a if fill == 0 else fill * a, buf)
    if glow > 0:
        f.fillpoly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], col, glow * a, 'B')

def chip(f, s, cx, cy, size, col, a, fnt='sans_med', fill=0.10):
    if a <= 0.003: return
    tw = text_width(s, fnt, size)
    px, py = size * 0.7, size * 0.5
    f.rrect_fill(cx - tw / 2 - px, cy - size / 2 - py, cx + tw / 2 + px, cy + size / 2 + py, size * 0.55, col, fill * a)
    f.rrect(cx - tw / 2 - px, cy - size / 2 - py, cx + tw / 2 + px, cy + size / 2 + py, size * 0.55, col, a * 0.85, 2)
    f.text(s, cx, cy, size, fnt, lerpc(col, WHITE, 0.55), a, mode='L', glow=0.2)

def stat(f, big, small, cx, cy, a, col=GOLD2, t0=None, bsz=84):
    """数字 + 下方说明"""
    if a <= 0.003: return
    p = 1 if t0 is None else eo((f.t - t0) / 0.45)
    f.text(big, cx, cy - (1 - p) * 20, bsz, 'bebas', col, a * p, glow=0.35, grad=[lerpc(col, WHITE, .35), col])
    f.text(small, cx, cy + bsz * 0.62, 26, 'sans_light', INK, a * p * 0.9)

def annulus(f, cx, cy, r0, r1, a0, a1, col, a, buf='L'):
    if a1 - a0 < 1e-3 or a <= 0.003: return
    n = max(4, int((a1 - a0) / 0.03))
    ts = np.linspace(a0, a1, n)
    pts = np.concatenate([np.stack([cx + r1 * np.cos(ts), cy + r1 * np.sin(ts)], 1),
                          np.stack([cx + r0 * np.cos(ts[::-1]), cy + r0 * np.sin(ts[::-1])], 1)])
    f.fillpoly(pts, col, a, buf)

def counter(v, p, fmt):
    return fmt(v * p)


# ============================================================== 镜头
def sc_open(f, t):
    """S1 冷开场：总市值计数"""
    if t > T_S2 + 0.5: return
    a = sa(t, 0.2, T_S2 + 0.2, 0.8, 0.5)
    out = (T_S2 - 0.55, 0.5)
    cy = 900
    # 背后的刻度盘
    p = eo((t - 0.3) / 2.5)
    for k in range(120):
        if k / 120 > p: break
        ang = -math.pi / 2 + k / 120 * 2 * math.pi + t * 0.03
        L = 22 if k % 10 == 0 else 10
        r = 420
        f.line((CX + r * math.cos(ang), cy + r * math.sin(ang)), (CX + (r - L) * math.cos(ang), cy + (r - L) * math.sin(ang)),
               GOLD, a * (0.35 if k % 10 == 0 else 0.16), 1)
    f.arc((CX, cy), 448, -math.pi / 2, -math.pi / 2 + 2 * math.pi * p, GOLD, a * 0.18, 1, 160)
    f.glow((CX, cy), 260, GOLD, a * 0.10, 'B')
    f.text('BERKSHIRE HATHAWAY  ·  FORM 13F', CX, 640, 24, 'mono', GOLD, a * 0.85, track=0.12, t0=0.6, stag=0.02, out=out)
    f.text('伯克希尔·哈撒韦  美股持仓总市值', CX, 712, 40, 'sans_med', WHITE, a, t0=1.0, stag=0.03, out=out)
    # 计数：固定左对齐，避免数字宽度变化导致抖动
    q = cl((t - 1.2) / 3.8)
    q = 1 - (1 - q) ** 4
    v = D.TOTAL / 1e8 * q
    s = f'{v:,.0f}'
    full = f'{D.TOTAL / 1e8:,.0f}'
    big = 250
    wfull = text_width('$' + full, 'bebas', big) + text_width('亿美元', 'sans_black', 64) + 10
    x0 = CX - wfull / 2
    ca = a * cl((t - 1.0) / 0.4) * (1 - eio((t - out[0]) / out[1]))
    lift = -eio((t - out[0]) / out[1]) * 30
    f.text('$' + s, x0, cy + lift, big, 'bebas', WHITE, ca, 'l', grad=[GOLD2, GOLD, GOLDD], mode='E', glow=0.35)
    f.text('亿美元', x0 + text_width('$' + full, 'bebas', big) + 10, cy + 62 + lift, 64, 'sans_black', GOLD2, ca * cl((t - 4.6) / 0.4), 'l')
    # 落定时的闪光线
    lp = eo((t - 5.0) / 0.8)
    f.line((CX - 400 * lp, 1060), (CX + 400 * lp, 1060), GOLD2, a * 0.7 * (1 - eio((t - out[0]) / out[1])), 2)
    f.glow((CX, 1060), 30, GOLD2, a * 0.5 * math.exp(-max(t - 5.0, 0) / 0.5) * (t > 5.0), 'B')
    f.text(f'截至 2026 年 9 月 30 日  ·  共 {D.N_ISSUERS} 家公司', CX, 1125, 34, 'sans_light', INK, a, t0=5.1, stag=0.02, out=out)
    chip(f, f'市值较上季  +{pct(D.TOTAL_PREV, D.TOTAL):.1f}%', CX, 1215, 30, UP, a * cl((t - 5.6) / 0.4) * (1 - eio((t - out[0]) / out[1])))


# ---- S2 星群（圆形打包，面积 ∝ 市值）
def _pack():
    rng = np.random.default_rng(5)
    v = np.array([x[2] for x in D.ALL], np.float64)
    r = np.sqrt(v / v.sum()) * 1.0
    k = 400 / math.sqrt((r ** 2).sum() / 0.62)      # 总面积约占半径 400 圆的 62%
    r = r * k
    r = np.maximum(r, 7)
    p = rng.normal(0, 60, (len(r), 2))
    for it in range(1500):
        d = p[:, None, :] - p[None, :, :]
        dist = np.sqrt((d ** 2).sum(-1)) + 1e-6
        ov = (r[:, None] + r[None, :] + 6) - dist
        np.fill_diagonal(ov, 0)
        ov = np.maximum(ov, 0)
        p += ((d / dist[..., None]) * ov[..., None] * 0.5).sum(1) * 0.5
        p -= p * 0.012
    p -= (p * (r[:, None] ** 2)).sum(0) / (r ** 2).sum()
    return p, r
PACK_P, PACK_R = _pack()

def sc_cluster(f, t):
    if not (T_S2 - 0.6 < t < T_S3 + 0.6): return
    a = sa(t, T_S2 - 0.3, T_S3 + 0.3, 0.4, 0.5)
    out = (T_S3 - 0.45, 0.45)
    cy = 920
    po = eio((t - (T_S3 - 0.45)) / 0.75)
    T = D.TOTAL
    for i, ((cu, tk, v), (px, py), r) in enumerate(zip(D.ALL, PACK_P, PACK_R)):
        p = (t - T_S2 - 0.05 - i * 0.045) / 0.55
        if p <= 0: continue
        s = eback(cl(p), 1.6) * (1 - po * 0.6)
        rr = r * s
        x = CX + px * (1 + po * 0.9); y = cy + py * (1 + po * 0.9)
        al = a * cl(p * 2)
        col = GOLDS[i] if i < 10 else OTHER
        f.circle((x, y), rr, col, al * (0.85 if i < 10 else 0.6), 2)
        if rr > 3:
            f.fillpoly(np.stack([x + rr * np.cos(np.linspace(0, 6.28, 40)), y + rr * np.sin(np.linspace(0, 6.28, 40))], 1),
                       col, al * (0.10 if i < 10 else 0.06), 'L')
        f.glow((x, y), rr * 0.6, col, al * 0.05, 'B')
        if r > 46:
            f.text('GOOGL' if tk == 'GOOGL' else tk, x, y - (r * 0.12 if r > 80 else 0), max(int(r * 0.42), 20), 'bebas',
                   lerpc(col, WHITE, .5), al)
        if r > 80:
            f.text(f'{v / T * 100:.1f}%', x, y + r * 0.32, int(r * 0.2), 'mono', INK, al * 0.85)
    f.text(f'{D.N_ISSUERS}', CX - 70, 380, 150, 'bebas', WHITE, a, grad=[GOLD2, GOLD], t0=T_S2, out=out, glow=0.3)
    f.text('家公司', CX + 70, 398, 64, 'serif_black', GOLD2, a, t0=T_S2 + 0.15, out=out)
    f.text('圆的面积 = 持仓市值', CX, 480, 28, 'sans_light', DIM, a, t0=T_S2 + 0.4, out=out)
    f.text('这个季度，它动了哪里？', CX, 1440, 58, 'serif_black', WHITE, a, t0=b(16), stag=0.06, out=out, glow=0.15)


# ---- S3 四个数字
TILES = [('新进', len(D.NEW), NEWC, 'Bending Spoons'), ('增持', len(D.ADD), UP, '莱纳 · 达美 · 梅西'),
         ('减持', len(D.CUT), DOWN, '美国银行等 6 家'), ('清仓', len(D.SOLD), GOLD2, '一只未卖光')]

def sc_four(f, t):
    if not (T_S3 - 0.5 < t < T_DROP1 + 0.1): return
    a = sa(t, T_S3 - 0.2, T_DROP1, 0.3, 0.05)
    eyebrow(f, '2026 Q3  vs  2026 Q2', 400, a, T_S3)
    f.text('本季调仓 · 一图看懂', CX, 480, 60, 'serif_black', WHITE, a, t0=T_S3 + 0.1, stag=0.05, glow=0.12)
    pull = ei(cl((t - b(28)) / (T_DROP1 - b(28))))
    for i, (lab, n, col, sub) in enumerate(TILES):
        ti = b(20 + 2 * i)
        p = (t - ti) / 0.5
        if p <= 0: continue
        sc = eback(cl(p), 2.0) * (1 - pull * 0.85)
        cx0 = 300 if i % 2 == 0 else 780
        cy0 = 790 if i < 2 else 1200
        cx = lerp(cx0, CX, pull); cy = lerp(cy0, 960, pull)
        al = a * cl(p * 2) * (1 - pull ** 2)
        hw, hh = 210 * sc, 180 * sc
        f.rrect_fill(cx - hw, cy - hh, cx + hw, cy + hh, 26 * sc, col, 0.07 * al)
        f.rrect(cx - hw, cy - hh, cx + hw, cy + hh, 26 * sc, col, 0.55 * al, 2)
        f.glow((cx, cy), 120 * sc, col, 0.10 * al * (1 + 2 * math.exp(-max(t - ti, 0) / 0.25)), 'B')
        if sc > 0.2:
            f.text(lab, cx, cy - 112 * sc, int(42 * sc), 'sans_med', lerpc(col, WHITE, .35), al)
            f.text(str(n), cx, cy + 6 * sc, int(190 * sc), 'bebas', lerpc(col, WHITE, .25), al, mode='E', glow=0.3)
            f.text(sub, cx, cy + 128 * sc, int(28 * sc), 'sans_light', INK, al * 0.9)
    implode(f, t, b(27), T_DROP1, CX, 960, [GOLD, GOLD2, WHITE, NEWC, UP, DOWN], 1.0, 760)


def sc_title(f, t):
    """S4 片名（第一次重拍）"""
    if not (T_DROP1 - 0.05 < t < T_S5 + 0.5): return
    a = sa(t, T_DROP1, T_S5 + 0.15, 0.05, 0.5)
    out = (T_S5 - 0.5, 0.5)
    burst(f, t, T_DROP1, CX, 900, [GOLD, GOLD2, WHITE, GOLDD], 1, 800, 1500, 1.3)
    zz = 1 + 0.05 * (t - T_DROP1)
    f.text('13F', CX, 900, int(560 * zz), 'bebas', GOLD, a * 0.07)
    eyebrow(f, '投资大师最新持仓  ·  EP.01', 640, a, T_DROP1 + 0.05)
    f.text('巴菲特', CX, 830, 220, 'serif_black', WHITE, a, grad=[GOLD2, GOLD, GOLDD], t0=T_DROP1 + 0.02, stag=0.09,
           dur=0.5, rise=40, mode='E', glow=0.45, out=out)
    f.text('伯克希尔·哈撒韦', CX, 1030, 80, 'serif_black', WHITE, a, t0=T_DROP1 + 0.35, stag=0.05, out=out)
    f.text('2026 Q3 · 13F 持仓全解析', CX, 1135, 40, 'sans_light', INK, a, track=0.15, t0=T_DROP1 + 0.7, stag=0.03, out=out)


def sc_donut(f, t):
    """S5 前十大重仓环形图"""
    if not (T_S5 - 0.5 < t < T_S6 + 0.6): return
    a = sa(t, T_S5 - 0.2, T_S6 + 0.05, 0.4, 0.45)
    out = (T_S6 - 0.5, 0.45)
    eyebrow(f, 'PORTFOLIO  ·  持仓全景', 290, a, T_S5)
    headline(f, '前十大重仓', 372, a, T_S5 + 0.1, out=out)
    cx, cy, R1, R0 = CX, 800, 330, 232
    rot = -math.pi / 2 + 0.25 * eio((t - T_S5) / 3) - 0.25
    exit_p = eio((t - out[0]) / 0.7)
    T = D.TOTAL
    segs = [(zh, tk, v) for zh, tk, v, s, s0 in D.TOP]
    rest = T - sum(v for _, _, v in segs)
    segs.append(('其他 17 家', '', rest))
    reveal = eio((t - T_S5 - 0.15) / 1.7)
    # 焦点循环：#1 → #5，每 2 拍一个
    fk = -1
    if b(44) <= t < b(54):
        fk = int(np.searchsorted(BEATS, t, 'right') - 1 - 44) // 2
    acc = 0.0
    for i, (zh, tk, v) in enumerate(segs):
        frac = v / T
        a0 = rot + acc * 2 * math.pi
        a1 = a0 + frac * 2 * math.pi
        acc += frac
        lim = rot + reveal * 2 * math.pi
        if a0 >= lim: break
        a1v = min(a1, lim)
        col = GOLDS[i] if i < 10 else OTHER
        foc = (i == fk)
        fp = 0.0
        if foc:
            fp = eback(cl((t - b(44 + 2 * fk)) / 0.35), 2)
        dim = 0.35 if (fk >= 0 and not foc) else 1.0
        mid = (a0 + a1) / 2
        off = 26 * fp
        ox, oy = off * math.cos(mid), off * math.sin(mid)
        rs = 1 - exit_p * 0.3
        annulus(f, cx + ox, cy + oy, R0 * rs, (R1 + 14 * fp) * rs, a0 + 0.008, a1v - 0.008, col, a * (0.85 * dim + 0.15) * (1 - exit_p))
        if foc:
            annulus(f, cx + ox, cy + oy, R0, R1 + 14 * fp, a0 + 0.008, a1v - 0.008, col, a * 0.35, 'B')
    f.circle((cx, cy), R0 - 18, GOLD, a * 0.25 * (1 - exit_p), 1)
    # 中心信息
    if fk < 0:
        ca = a * (1 - exit_p) * cl((t - T_S5 - 0.6) / 0.5) * (1 - eio((t - b(44) + 0.15) / 0.15) if t < b(44) else 1)
        if t >= b(54): ca = a * (1 - exit_p) * eo((t - b(54)) / 0.4)
        f.text('13F 总市值', cx, cy - 58, 32, 'sans_light', INK, ca)
        runs(f, [(f'{D.TOTAL / 1e8:,.0f}', 'bebas', 120, [GOLD2, GOLD]), (' 亿美元', 'sans_med', 34, GOLD2)], cx, cy + 22, ca)
    else:
        zh, tk, v, sh, sh0 = D.TOP[fk]
        tf = t - b(44 + 2 * fk)
        ca = a * eo(tf / 0.3)
        f.text(f'#{fk + 1}', cx, cy - 120, 36, 'bebas', GOLD, ca)
        f.text(zh, cx, cy - 62, 54, 'serif_black', WHITE, ca, t0=b(44 + 2 * fk), stag=0.03, rise=12)
        f.text(f'{v / T * 100:.2f}%', cx, cy + 38, 118, 'bebas', WHITE, ca, grad=[GOLD2, GOLD], glow=0.3, mode='E')
        f.text(f'{yi(v)} 亿美元', cx, cy + 122, 30, 'sans_light', INK, ca)
    # 图例（两列）
    for i, (zh, tk, v, sh, sh0) in enumerate(D.TOP):
        col = GOLDS[i]
        x = 110 if i < 5 else 590
        y = 1240 + (i % 5) * 70
        p = eo((t - T_S5 - 0.5 - i * 0.09) / 0.4)
        al = a * p * (1 - exit_p) * (1 if (fk < 0 or fk == i) else 0.45)
        if al < 0.01: continue
        x += (1 - p) * 30
        f.fillpoly([(x, y - 9), (x + 18, y - 9), (x + 18, y + 9), (x, y + 9)], col, al)
        f.text(f'{i + 1:02d}', x + 34, y, 24, 'mono', DIM, al, 'l')
        f.text(zh, x + 78, y, 32, 'sans_med', WHITE, al, 'l')
        f.text(f'{v / T * 100:.2f}%', x + 380, y, 34, 'bebas', lerpc(col, WHITE, .3), al, 'r')


def sc_conc(f, t):
    """S6 集中度"""
    if not (T_S6 - 0.4 < t < T_S7 + 0.6): return
    a = sa(t, T_S6 + 0.02, T_S7 + 0.3, 0.35, 0.5)
    out = (T_S7 - 0.45, 0.45)
    T = D.TOTAL
    top5 = sum(x[2] for x in D.TOP[:5]) / T * 100
    eyebrow(f, 'CONCENTRATION  ·  集中度', 330, a, T_S6)
    q = eo((t - T_S6 - 0.05) / 1.0)
    oa = a * (1 - eio((t - out[0]) / out[1]))
    f.text(f'{top5 * q:.1f}%', CX, 600, 300, 'bebas', WHITE, oa, grad=[GOLD2, GOLD, GOLDD], mode='E', glow=0.35)
    f.text('前五大重仓合计占比', CX, 790, 46, 'serif_black', WHITE, a, t0=T_S6 + 0.3, stag=0.04, out=out)
    # 100% 堆叠条
    x0, x1, y = 90, 990, 930
    acc = 0
    rv = eio((t - T_S6 - 0.3) / 1.0)
    for i in range(6):
        v = D.TOP[i][2] if i < 5 else T - sum(x[2] for x in D.TOP[:5])
        w = v / T * (x1 - x0)
        xa = x0 + acc; xb = min(xa + w, x0 + (x1 - x0) * rv)
        acc += w
        if xb <= xa + 2: continue
        col = GOLDS[i * 2] if i < 5 else OTHER
        box(f, xa + 2, y - 26, xb - 2, y + 26, col, oa * (0.9 if i < 5 else 0.5))
        if i < 5:
            box(f, xa + 2, y - 26, xb - 2, y + 26, col, oa * 0.25, buf='B')
        lab = D.TOP[i][1] if i < 5 else f'其他 {D.N_ISSUERS - 5} 家  {100 - top5:.1f}%'
        lab_al = oa * cl((t - T_S6 - 0.9 - i * 0.06) / 0.3)
        if i < 5:
            f.text(lab, (xa + xb) / 2, y + 58, 24, 'mono', INK, lab_al)
        else:
            f.text(lab, (xa + xb) / 2, y, 26, 'sans_med', WHITE, lab_al)
    # 持仓公司数 39 → 27
    t2 = b(60)
    f.text('持仓公司数', CX, 1130, 34, 'sans_med', INK, a, t0=t2 - 0.3, out=out)
    runs(f, [(f'{D.N_ISSUERS_Q4_25}', 'bebas', 110, DIM), ('  →  ', 'sans_light', 60, DIM),
             (f'{D.N_ISSUERS}', 'bebas', 110, [GOLD2, GOLD])], CX, 1240, oa * cl((t - t2 + 0.2) / 0.4))
    f.text('2025 年末          本季', CX, 1320, 26, 'sans_light', DIM, oa * cl((t - t2) / 0.4))
    n0, n1 = D.N_ISSUERS_Q4_25, D.N_ISSUERS
    for k in range(n0):
        x = 120 + k * (840 / (n0 - 1))
        gone = k >= n1
        fade = eio((t - t2 - 0.3 - (k - n1) * 0.05) / 0.4) if gone else 0
        al = oa * cl((t - t2 + 0.3 - k * 0.012) / 0.3) * (1 - fade * 0.8)
        f.circle((x, 1420 + fade * 18), 7, DOWN if gone and fade > 0 else GOLD, al * 0.9, 2)
        if not gone:
            f.glow((x, 1420), 5, GOLD, al * 0.5, 'E')


def bars_q(f, t, vals, labels, x0, x1, base, hmax, t0s, cols, a, vmax=None, lab_fmt=None, w=110):
    """季度柱状图"""
    vmax = vmax or max(vals)
    n = len(vals)
    for i, v in enumerate(vals):
        x = x0 + (x1 - x0) * i / (n - 1)
        p = eo((t - t0s[i]) / 0.5)
        h = hmax * v / vmax * p
        col = cols[i]
        if h > 1:
            box(f, x - w / 2, base - h, x + w / 2, base, col, a * 0.85)
            box(f, x - w / 2, base - h, x + w / 2, base - h + 4, lerpc(col, WHITE, .6), a)
            box(f, x - w / 2, base - h, x + w / 2, base, col, a * 0.18, buf='B')
        f.text(labels[i], x, base + 40, 26, 'mono', INK, a * cl((t - t0s[i] + 0.3) / 0.3))
        if p > 0.05:
            f.text(lab_fmt(v) if lab_fmt else wan(v), x, base - h - 34, 38, 'sans_med' if v else 'bebas', WHITE, a * p)
    f.line((x0 - w, base), (x1 + w, base), INK, a * 0.5, 1)


def sc_googl(f, t):
    """S7 Alphabet：一年股数 ×5.9"""
    if not (T_S7 - 0.4 < t < T_S8 + 0.6): return
    a = sa(t, T_S7 - 0.15, T_S8 + 0.3, 0.4, 0.5)
    out = (T_S8 - 0.45, 0.45)
    oa = a * (1 - eio((t - out[0]) / out[1]))
    h = D.HIST['GOOGL']
    eyebrow(f, 'SPOTLIGHT  ·  一年里最大的变化', 290, a, T_S7)
    headline(f, 'Alphabet（谷歌）', 380, a, T_S7 + 0.1, size=80, out=out)
    mult = h[-1] / h[0]
    runs(f, [('一年持股  ', 'serif_black', 50, WHITE), (f'×{mult:.1f}', 'bebas', 96, [GOLD2, GOLD])], CX, 488,
         oa * eo((t - b(72)) / 0.4), mode='E', glow=0.3)
    t0s = [b(66), b(67), b(68), b(69), b(70)]
    cols = [lerpc(NEWC, GOLD2, i / 4 * 0.6) for i in range(4)] + [GOLD2]
    bars_q(f, t, h, D.QUARTERS, 160, 920, 1150, 470, t0s, cols, oa)
    # 倍数弧线
    p = eio((t - b(71)) / 0.7)
    if p > 0:
        x0, y0, x1, y1 = 160, 1150 - 470 * h[0] / h[-1] - 80, 920, 1150 - 470 - 80
        pts = [(lerp(x0, x1, u), lerp(y0, y1, u) - 90 * math.sin(u * math.pi)) for u in np.linspace(0, p, 40)]
        f.poly(pts, GOLD2, oa * 0.8, 2)
        f.glow(pts[-1], 8, GOLD2, oa * 0.8, 'E')
    v = D.TOP[2][2]
    for i, (big, small) in enumerate([('#3', '第三大重仓'), (f'{v / D.TOTAL * 100:.2f}%', '组合占比'), (f'{yi(v)}', '市值 · 亿美元')]):
        stat(f, big, small, 200 + i * 340, 1340, oa, GOLD2, b(73) + i * 0.15)
    f.text('本季持股数不变', CX, 1500, 30, 'sans_light', DIM, a, t0=b(75), out=out)


def sc_new(f, t):
    """S8a 新进"""
    t1 = b(88)
    if not (T_S8 - 0.4 < t < t1 + 0.6): return
    a = sa(t, T_S8 - 0.15, t1 + 0.3, 0.4, 0.45)
    out = (t1 - 0.4, 0.4)
    oa = a * (1 - eio((t - out[0]) / out[1]))
    zh, tk, sh, v = D.NEW[0]
    eyebrow(f, 'NEW POSITION  ·  新进', 330, a, T_S8, NEWC)
    # 发光的「+」和扫描环
    p = eo((t - T_S8) / 0.8)
    cy = 640
    for k in range(3):
        rr = 120 + k * 40 + 10 * math.sin(t * 2 + k)
        f.arc((CX, cy), rr * p, t * (0.6 + k * 0.3), t * (0.6 + k * 0.3) + 4.2, NEWC, oa * (0.5 - k * 0.12), 2, 90)
    L = 56 * p
    box(f, CX - L, cy - 7, CX + L, cy + 7, NEWC, oa, glow=0.6)
    box(f, CX - 7, cy - L, CX + 7, cy + L, NEWC, oa, glow=0.6)
    burst(f, t, T_S8 + 0.05, CX, cy, [NEWC, WHITE, CYAN], 3, 400, 900, 0.9)
    f.text('BENDING SPOONS', CX, 900, 128, 'bebas', WHITE, a, grad=[WHITE, lerpc(NEWC, WHITE, .4)], t0=T_S8 + 0.25,
           stag=0.035, mode='E', glow=0.3, out=out)
    f.text('意大利科技公司 · 旗下有 Evernote、WeTransfer 等', CX, 1010, 32, 'sans_light', INK, a, t0=T_S8 + 0.6, stag=0.015, out=out)
    for i, (big, small) in enumerate([(wan(sh), '买入股数'), (f'{v / 1e8:.1f}亿', '市值 · 美元'), (f'{v / D.TOTAL * 100:.2f}%', '组合占比')]):
        stat(f, big, small, 200 + i * 340, 1200, oa, lerpc(NEWC, WHITE, .3), b(84) + i * 0.15, 80)
    f.text('本季唯一一只新进股票', CX, 1390, 32, 'sans_med', NEWC, a, t0=b(86), out=out)


def change_rows(f, t, rows, col, t0s, a, y0=640, dy=230, sign='+'):
    """增减持行：名称 + 前后股数对比条 + 百分比"""
    for i, (zh, tk, s0, s1) in enumerate(rows):
        y = y0 + i * dy
        p = eo((t - t0s[i]) / 0.5)
        if p <= 0: continue
        al = a * p
        x = 90 + (1 - p) * 40
        f.text(zh, x, y - 52, 44, 'serif_black', WHITE, al, 'l')
        f.text(tk, x + text_width(zh, 'serif_black', 44) + 18, y - 48, 28, 'mono', DIM, al, 'l')
        ch = pct(s0, s1)
        f.text(f'{"+" if ch > 0 else MINUS}{abs(ch):.1f}%', 990, y - 40, 96, 'bebas', lerpc(col, WHITE, .2), al, 'r', mode='E', glow=0.3)
        mx = max(s0, s1)
        L = 900
        q = eio((t - t0s[i] - 0.15) / 0.6)
        box(f, 90, y + 22, 90 + L * s0 / mx, y + 34, DIM, al * 0.55)                     # 上期
        nb = 90 + L * (s0 + (s1 - s0) * q) / mx
        box(f, 90, y + 44, nb, y + 64, col, al * 0.9)                                     # 本期
        box(f, 90, y + 44, nb, y + 64, col, al * 0.3, buf='B')
        f.text(f'{wan(s0)}  →  {wan(s1)} 股', 90, y + 96, 26, 'sans_light', INK, al * cl((t - t0s[i] - 0.4) / 0.4), 'l')


def sc_add(f, t):
    """S8b 增持"""
    t0 = b(88)
    if not (t0 - 0.4 < t < T_S9 + 0.6): return
    a = sa(t, t0 - 0.15, T_S9 + 0.3, 0.4, 0.5)
    eyebrow(f, 'ADDED  ·  增持', 330, a, t0, UP)
    headline(f, '增持 3 家', 410, a, t0 + 0.05, out=(T_S9 - 0.45, 0.45))
    change_rows(f, t, D.ADD, UP, [b(89), b(91), b(93)], a * (1 - eio((t - T_S9 + 0.45) / 0.45)), 640, 250)
    f.text('上期', 140, 1520, 24, 'sans_light', DIM, a * 0.8, 'l', t0=b(89))
    box(f, 90, 1513, 128, 1527, DIM, a * 0.5)
    f.text('本期（按申报股数）', 330, 1520, 24, 'sans_light', DIM, a * 0.8, 'l', t0=b(89))
    box(f, 280, 1510, 318, 1530, UP, a * 0.8)


def sc_cut(f, t):
    """S9 减持（渐弱段）"""
    t1 = b(106)
    if not (T_S9 - 0.4 < t < t1 + 0.6): return
    a = sa(t, T_S9 - 0.1, t1 + 0.3, 0.4, 0.5)
    out = (t1 - 0.45, 0.45)
    oa = a * (1 - eio((t - out[0]) / out[1]))
    eyebrow(f, 'TRIMMED  ·  减持', 290, a, T_S9, DOWN)
    headline(f, '减持 6 家', 370, a, T_S9 + 0.05, out=out)
    rows = sorted(D.CUT, key=lambda r: pct(r[2], r[3]))
    for i, (zh, tk, s0, s1) in enumerate(rows):
        y = 540 + i * 168
        ti = b(97) + i * (b(98) - b(97)) * 0.75
        p = eo((t - ti) / 0.45)
        if p <= 0: continue
        al = oa * p
        ch = pct(s0, s1)
        f.text(zh, 90, y, 40, 'serif_black', WHITE, al, 'l')
        f.text(tk, 90 + text_width(zh, 'serif_black', 40) + 14, y + 4, 24, 'mono', DIM, al, 'l')
        f.text(f'{MINUS}{abs(ch):.1f}%', 990, y, 76, 'bebas', lerpc(DOWN, WHITE, .2), al, 'r', mode='E', glow=0.25)
        # 被卖掉的比例条：整条代表上期持股，红色部分 = 卖出
        q = eio((t - ti - 0.1) / 0.6)
        L = 900
        box(f, 90, y + 46, 90 + L, y + 58, C(40, 44, 60), al * 0.9)
        keep = L * (1 - (1 - s1 / s0) * q)
        box(f, 90, y + 46, 90 + keep, y + 58, INK, al * 0.55)
        box(f, 90 + keep, y + 46, 90 + L, y + 58, DOWN, al * 0.9 * q)
        box(f, 90 + keep, y + 46, 90 + L, y + 58, DOWN, al * 0.3 * q, buf='B')
    f.text('灰色 = 保留部分　红色 = 本季卖出部分', CX, 1560, 24, 'sans_light', DIM, oa * cl((t - b(100)) / 0.5))


def line_chart(f, t, series, x0, x1, y0, y1, vmin, vmax, t0, dur, a, labels=None):
    """series: [(vals, colour, label)]；从 t0 开始在 dur 内画出"""
    n = len(series[0][0])
    p = eio((t - t0) / dur)
    for k in range(5):
        yy = y1 - (y1 - y0) * k / 4
        f.line((x0, yy), (x1, yy), DIM, a * 0.12, 1)
    for i in range(n):
        x = x0 + (x1 - x0) * i / (n - 1)
        if labels: f.text(labels[i], x, y1 + 42, 26, 'mono', INK, a * 0.85)
    for vals, col, lab in series:
        pts = [(x0 + (x1 - x0) * i / (n - 1), y1 - (y1 - y0) * (v - vmin) / (vmax - vmin)) for i, v in enumerate(vals)]
        m = p * (n - 1)
        k = int(m)
        seg = pts[:k + 1]
        if k < n - 1:
            u = m - k
            seg = seg + [(lerp(pts[k][0], pts[k + 1][0], u), lerp(pts[k][1], pts[k + 1][1], u))]
        f.poly(seg, col, a, 4)
        for j, pt in enumerate(pts[:k + 1]):
            f.glow(pt, 7, col, a, 'E')
        f.glow(seg[-1], 14, col, a * 0.6, 'B')
        if lab and p > 0.98:
            f.text(lab, pts[-1][0] - 10, pts[-1][1] - 44, 30, 'sans_med', lerpc(col, WHITE, .3), a * eo((t - t0 - dur) / 0.4), 'r')
    return p


def sc_bac(f, t):
    """S9b 美国银行：一年减持 19.8%"""
    t0 = b(106)
    if not (t0 - 0.4 < t < T_S10 + 0.5): return
    a = sa(t, t0 - 0.15, T_S10 + 0.2, 0.4, 0.45)
    out = (T_S10 - 0.4, 0.4)
    oa = a * (1 - eio((t - out[0]) / out[1]))
    h = D.HIST['BAC']
    eyebrow(f, 'TREND  ·  持续减持', 330, a, t0, DOWN)
    headline(f, '美国银行', 420, a, t0 + 0.05, size=84, out=out)
    yr = pct(h[0], h[-1])
    runs(f, [('一年减持  ', 'serif_black', 46, WHITE), (f'{MINUS}{abs(yr):.1f}%', 'bebas', 96, lerpc(DOWN, WHITE, .2))],
         CX, 520, oa * eo((t - t0 - 0.3) / 0.4), mode='E', glow=0.25)
    line_chart(f, t, [(h, DOWN, '')], 140, 940, 680, 1150, 4.0e8, 6.0e8, t0 + 0.4, 2.2, oa, D.QUARTERS)
    n = len(h)
    for i, v in enumerate(h):
        if eio((t - t0 - 0.4) / 2.2) * (n - 1) >= i - 0.01:
            x = 140 + 800 * i / (n - 1); y = 1150 - 470 * (v - 4.0e8) / 2.0e8
            f.text(f'{v / 1e8:.2f}亿', x, y - 40, 30, 'sans_med', WHITE, oa * 0.95)
    for i, (big, small) in enumerate([('#5', '仍是第五大重仓'), (f'{D.TOP[4][2] / D.TOTAL * 100:.2f}%', '组合占比'),
                                      (f'{MINUS}{abs(pct(D.HIST["COF"][0], D.HIST["COF"][-1])):.1f}%', '第一资本 · 一年')]):
        stat(f, big, small, 200 + i * 340, 1340, oa, GOLD2 if i < 2 else lerpc(DOWN, WHITE, .2), b(110) + i * 0.15, 80)


def sc_zero(f, t):
    """S10 清仓 = 0（鼓点抽空）"""
    if not (T_S10 - 0.1 < t < T_DROP2 + 0.1): return
    a = sa(t, T_S10, T_DROP2, 0.15, 0.05)
    pull = ei(cl((t - b(121)) / (T_DROP2 - b(121))))
    oa = a * (1 - pull)
    eyebrow(f, 'SOLD OUT  ·  清仓', 420, oa, T_S10 + 0.05)
    p = eo((t - T_S10) / 0.6)
    s = 1 + 0.25 * (1 - p)
    f.text('0', CX, 800 - 20 * pull, int(560 * s * (1 - 0.6 * pull)), 'bebas', WHITE, oa * p, grad=[GOLD2, GOLD, GOLDD], mode='E', glow=0.4)
    f.circle((CX, 800), 300 * p * (1 - pull * 0.8), GOLD, oa * 0.35, 2)
    f.arc((CX, 800), 330 * p * (1 - pull * 0.8), t * 0.8, t * 0.8 + 2, GOLD2, oa * 0.5, 2)
    f.text('本季清仓  0  家', CX, 1150, 50, 'serif_black', WHITE, oa, t0=T_S10 + 0.4, stag=0.05)
    # 清仓数量时间线
    xs = [250, 540, 830]
    for i, (q, n) in enumerate(D.EXITS):
        ti = b(117) + i * (b(118) - b(117))
        pp = eo((t - ti) / 0.4)
        if pp <= 0: continue
        col = DOWN if n > 0 else GOLD2
        f.circle((xs[i], 1300), 12 * pp, col, oa, 2)
        f.glow((xs[i], 1300), 8, col, oa * pp, 'E')
        f.text(f'{n}', xs[i], 1370, 64, 'bebas', lerpc(col, WHITE, .3), oa * pp)
        f.text(f'{q} 清仓', xs[i], 1430, 26, 'sans_med', INK, oa * pp)
        if i:
            f.line((xs[i - 1] + 16, 1300), (lerp(xs[i - 1] + 16, xs[i] - 16, pp), 1300), DIM, oa * 0.6, 2)
    f.text('半年前一季清仓 15 家，本季原有持仓全部保留', CX, 1530, 32, 'sans_light', INK, oa, t0=b(119), stag=0.02)
    implode(f, t, b(121), T_DROP2, CX, 800, [GOLD, GOLD2, WHITE], 1.0, 650)


def sc_signals_title(f, t):
    if not (T_DROP2 - 0.05 < t < T_SIG1 + 0.5): return
    a = sa(t, T_DROP2, T_SIG1 + 0.15, 0.05, 0.45)
    out = (T_SIG1 - 0.45, 0.45)
    burst(f, t, T_DROP2, CX, 900, [GOLD, GOLD2, WHITE, GOLDD], 2, 800, 1500, 1.3)
    f.text('最值得关注的', CX, 760, 52, 'sans_med', INK, a, t0=T_DROP2 + 0.05, stag=0.04, out=out)
    runs(f, [('3', 'bebas', 260, [GOLD2, GOLD]), (' 个信号', 'serif_black', 120, [GOLD2, GOLD])], CX, 920,
         a * (1 - eio((t - out[0]) / out[1])), mode='E', glow=0.4, t0=T_DROP2 + 0.1, stag=0.08, rise=40)


def sig_head(f, t, n, title, sub, t0, a, out, col=GOLD2):
    oa = a * (1 - eio((t - out[0]) / out[1]))
    p = eo((t - t0) / 0.5)
    f.text(n, 90 + (1 - p) * 40, 320, 120, 'bebas', lerpc(col, WHITE, .2), oa * p * 0.9, 'l', mode='E', glow=0.3)
    f.line((210, 280), (210, 360), col, oa * p * 0.7, 2)
    f.text(title, 236, 300, 52, 'serif_black', WHITE, a, 'l', t0=t0 + 0.1, stag=0.035, out=out)
    f.text(sub, 236, 360, 30, 'sans_light', INK, a, 'l', t0=t0 + 0.35, stag=0.02, out=out)


def sc_sig1(f, t):
    """信号 01：苹果连续 3 个季度一股未动"""
    if not (T_SIG1 - 0.4 < t < T_SIG2 + 0.6): return
    a = sa(t, T_SIG1 - 0.15, T_SIG2 + 0.3, 0.4, 0.5)
    out = (T_SIG2 - 0.45, 0.45)
    oa = a * (1 - eio((t - out[0]) / out[1]))
    sig_head(f, t, '01', '苹果：3 个季度一股未动', '仍是第一大重仓，占组合近四分之一', T_SIG1, a, out)
    h = D.HIST['AAPL']
    t0s = [b(129) + i * 0.27 for i in range(5)]
    cols = [DIM] + [GOLD2] * 4
    bars_q(f, t, h, D.QUARTERS, 160, 920, 1080, 480, t0s, cols, oa, lab_fmt=lambda v: f'{v / 1e8:.2f}亿')
    # 「持平」标注
    p = eio((t - b(132)) / 0.6)
    if p > 0:
        y = 1080 - 480 * h[1] / max(h) - 90
        f.line((350, y), (lerp(350, 970, p), y), GOLD2, oa * 0.6, 2)
        f.text('股数持平', 660, y - 30, 30, 'sans_med', GOLD2, oa * cl((t - b(133)) / 0.4))
    T = D.TOTAL
    v = D.TOP[0][2]
    for i, (big, small) in enumerate([(f'{yi(v)}', '市值 · 亿美元'), (f'{v / T * 100:.2f}%', '组合占比'),
                                      (f'+{(v - D.AAPL_PREV_VALUE) / 1e8:.1f}', '本季市值变化 · 亿美元')]):
        stat(f, big, small, 200 + i * 340, 1290, oa, GOLD2 if i < 2 else UP, b(134) + i * 0.15)
    f.text('市值增加完全来自股价上涨，股数没有变化', CX, 1460, 28, 'sans_light', DIM, a, t0=b(136), stag=0.015, out=out)



def sc_sig2(f, t):
    """信号 02：加码美国「住房 + 出行」"""
    if not (T_SIG2 - 0.4 < t < T_SIG3 + 0.6): return
    a = sa(t, T_SIG2 - 0.15, T_SIG3 + 0.3, 0.4, 0.5)
    out = (T_SIG3 - 0.45, 0.45)
    oa = a * (1 - eio((t - out[0]) / out[1]))
    sig_head(f, t, '02', '加码美国「住房 + 出行」', '连续多个季度买入同一批股票', T_SIG2, a, out, UP)
    panels = [('莱纳房屋', 'LEN · 住宅建筑商', D.HIST['LEN'], 560, b(141)),
              ('达美航空', 'DAL · 航空公司', D.HIST['DAL'], 1040, b(145))]
    for k, (zh, sub, h, y0, t0) in enumerate(panels):
        p = eo((t - t0) / 0.5)
        al = oa * p
        f.text(zh, 90, y0, 46, 'serif_black', WHITE, al, 'l')
        f.text(sub, 90 + text_width(zh, 'serif_black', 46) + 16, y0 + 4, 26, 'sans_light', DIM, al, 'l')
        base, hmax = y0 + 330, 230
        mx = max(h)
        for i, v in enumerate(h):
            x = 140 + i * 125
            q = eo((t - t0 - 0.2 - i * 0.12) / 0.45)
            hh = hmax * v / mx * q
            col = lerpc(C(40, 110, 90), UP, i / 4)
            if hh > 1:
                box(f, x - 38, base - hh, x + 38, base, col, al * 0.85)
                box(f, x - 38, base - hh, x + 38, base, col, al * 0.2, buf='B')
            f.text(D.QUARTERS[i], x, base + 30, 22, 'mono', INK, al * 0.8)
            if q > 0.1:
                f.text(wan(v) if v else '0', x, base - hh - 26, 26 if v else 30, 'sans_med' if v else 'bebas', WHITE, al * q)
        f.line((90, base), (700, base), INK, al * 0.4, 1)
        if k == 0:
            big, small = f'×{h[-1] / h[0]:.1f}', '一年持股倍数'
        else:
            big, small = '0 → ' + wan(h[-1]), '三个季度建仓'
        stat(f, big, small, 860, y0 + 180, oa, lerpc(UP, WHITE, .2), t0 + 0.8, 92 if k == 0 else 64)


def sc_sig3(f, t):
    """信号 03：银行股持续瘦身，运通一股未动"""
    if not (T_SIG3 - 0.4 < t < T_OUTRO + 0.6): return
    a = sa(t, T_SIG3 - 0.15, T_OUTRO + 0.3, 0.4, 0.5)
    out = (T_OUTRO - 0.45, 0.45)
    oa = a * (1 - eio((t - out[0]) / out[1]))
    sig_head(f, t, '03', '银行股继续做减法', '但第二大重仓美国运通，一股未动', T_SIG3, a, out, DOWN)
    idx = lambda h: [v / h[0] * 100 for v in h]
    ser = [(idx(D.HIST['AXP']), GOLD2, ''), (idx(D.HIST['BAC']), lerpc(DOWN, GOLD, .35), ''),
           (idx(D.HIST['COF']), DOWN, '')]
    names = ['美国运通', '美国银行', '第一资本']
    f.text('持股数（2025Q3 = 100）', 90, 520, 26, 'sans_light', DIM, a, 'l', t0=T_SIG3 + 0.4, out=out)
    p = line_chart(f, t, ser, 150, 760, 600, 1180, 0, 110, b(154), 2.6, oa, D.QUARTERS)
    for k, ((vals, col, _), lab) in enumerate(zip(ser, names)):
        y = 1180 - 580 * vals[-1] / 110
        al = oa * eo((t - b(154) - 2.6 - k * 0.15) / 0.4)
        ch = vals[-1] - 100
        f.text(lab, 790, y - 20 + (k == 1) * 6, 28, 'sans_med', WHITE, al, 'l')
        f.text('不变' if abs(ch) < 0.05 else f'{MINUS}{abs(ch):.1f}%', 790, y + 26 + (k == 1) * 6, 44, 'bebas' if abs(ch) >= 0.05 else 'sans_med',
               lerpc(col, WHITE, .2), al, 'l')
    f.text('此前（2026 Q1）还清仓了 Visa、万事达', CX, 1400, 30, 'sans_light', INK, a, t0=b(160), stag=0.015, out=out)


SUMMARY = [('核心重仓', '苹果 · 运通 · 可口可乐 纹丝不动', GOLD2), ('银行股', '美国银行 · 第一资本 继续减持', DOWN),
           ('住房与出行', '莱纳 · 达美 持续加仓', UP)]

def sc_outro(f, t):
    if not (T_OUTRO - 0.4 < t < T_END + 0.5): return
    a = sa(t, T_OUTRO - 0.15, T_END + 0.2, 0.4, 0.5)
    out = (T_END - 0.45, 0.45)
    eyebrow(f, 'TAKEAWAY  ·  一句话总结', 520, a, T_OUTRO)
    for i, (k, v, col) in enumerate(SUMMARY):
        ti = b(165 + i * 2)
        y = 680 + i * 220
        p = eo((t - ti) / 0.5)
        al = a * p * (1 - eio((t - out[0]) / out[1]))
        f.line((140, y - 70), (140, y + 70), col, al * 0.9, 3)
        f.glow((140, y), 30, col, al * 0.15, 'B')
        f.text(k, 180 + (1 - p) * 30, y - 28, 56, 'serif_black', lerpc(col, WHITE, .35), al, 'l', glow=0.2)
        f.text(v, 180 + (1 - p) * 30, y + 40, 34, 'sans_light', INK, al, 'l')


def sc_end(f, t):
    if t < T_END - 0.1: return
    e = cl((t - T_END) / 0.6)
    rgb, m = END_LOGO
    hgt = m.shape[0]
    sc = eo((t - T_END) / 1.0)
    X0, Y0 = int(CX - hgt / 2), int(760 - hgt / 2)
    f.over.append((m, X0, Y0, rgb, e * sc))
    f.glow((CX, 760), 150, C(110, 175, 255), e * 0.22, 'B')     # 淡蓝光晕
    burst(f, t, T_END + 0.05, CX, 760, [C(110, 175, 255), CYAN, GOLD2, WHITE], 7, 500, 900, 1.6)
    f.text('巴芒价值', CX, 1000, 120, 'serif_black', GOLD2, e, t0=T_END + 0.25, stag=0.12, dur=0.6,
           grad=[GOLD2, GOLD, GOLDD], mode='O', glow=0.5)
    f.text('BUFFETT · MUNGER', CX, 1096, 34, 'corm', C(214, 178, 112), e, track=0.42, t0=T_END + 0.8, stag=0.03, mode='O')
    f.text('投资大师最新持仓 · 下期见', CX, 1210, 34, 'sans_light', INK, e, track=0.2, t0=T_END + 1.2, stag=0.03)
    f.text(f'数据来源：SEC EDGAR · 伯克希尔 13F-HR（{D.FILING["filed"]} 提交，报告期 {D.FILING["period"]}）', CX, 1500, 22,
           'sans_light', DIM, e * 0.9, t0=T_END + 1.6, stag=0.005)
    f.text('仅为公开信息整理，不构成任何投资建议', CX, 1545, 22, 'sans_light', DIM, e * 0.9, t0=T_END + 1.8, stag=0.005)


# ============================================================== 品牌角标 + 页面框架
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'brand'))
from brand import Hud, load_logo as brand_logo
HUD = Hud(frame_w=W)
END_LOGO = brand_logo(220)

def draw_hud_post(img, t, a):
    if a <= 0.003: return img
    h = HUD.y0 + HUD.h + HUD.P + 2
    reg = img[:h].astype(np.float32) / 255
    HUD.draw(reg, t, a)
    img[:h] = (np.clip(reg, 0, 1) * 255 + 0.5).astype(np.uint8)
    return img

CHAPTERS = [(0, '序'), (T_DROP1, '持仓全景'), (T_S7, '焦点'), (T_S8, '买入'), (T_S9, '卖出'), (T_DROP2, '三个信号'),
            (T_OUTRO, '总结'), (T_END, '')]

def draw_chrome(f, t):
    al = 0.9 * env(t, 0.6, T_END, 0.8, 0.4)
    if al <= 0.003: return
    f.text('投资大师最新持仓', 56, 52, 28, 'sans_med', GOLD2, al, 'l', mode='O')
    f.text('EP.01 · BERKSHIRE · 2026Q3', 56, 90, 18, 'mono', DIM, al * 0.9, 'l', mode='O')
    # 底部进度条（章节刻度）
    x0, x1, y = 90, 990, 1740
    f.line((x0, y), (x1, y), DIM, al * 0.25, 1)
    u = cl(t / T_END)
    xc = lerp(x0, x1, u)
    f.line((x0, y), (xc, y), GOLD, al * 0.75, 2)
    f.glow((xc, y), 5, GOLD2, al * 0.8, 'E')
    for (ta, name), (tb, _) in zip(CHAPTERS, CHAPTERS[1:]):
        if ta == 0: continue
        x = lerp(x0, x1, ta / T_END)
        on = t >= ta
        f.line((x, y - 6), (x, y + 6), GOLD if on else DIM, al * (0.8 if on else 0.4), 1)
    cur = [n for ta, n in CHAPTERS if ta <= t][-1]
    f.text(cur, x0, y - 28, 22, 'sans_med', GOLD, al * 0.85, 'l', mode='O')
    f.text('数据：SEC 13F · 报告期 2026-09-30', x1, y - 28, 20, 'sans_light', DIM, al * 0.8, 'r', mode='O')


SCENES = [sc_open, sc_cluster, sc_four, sc_title, sc_donut, sc_conc, sc_googl, sc_new, sc_add, sc_cut, sc_bac,
          sc_zero, sc_signals_title, sc_sig1, sc_sig2, sc_sig3, sc_outro, sc_end]


def render(i):
    t = i / FPS
    f = Frame(t)
    bg = bg_at(t)
    grid_floor(f, t)
    dust(f, t)
    for s in SCENES:
        s(f, t)
    shockwaves(f, t)
    sweep(f, t)
    draw_chrome(f, t)
    img = finish(f, bg, bloom_k=1.0 + 0.25 * beat_pulse(t) * energy(t), vignette=VIGNETTE)
    s = punch(t)
    if s > 1.0005:
        M = cv2.getRotationMatrix2D((W / 2, H * 0.47), 0, s)
        img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    draw_hud_post(img, t, env(t, 0.3, T_END + 0.2, 0.8, 0.6))
    fade = cl(t / 0.4) * (1 - eio((t - (DUR - 1.2)) / 1.2))
    if fade < 1:
        img = (img.astype(np.float32) * fade).astype(np.uint8)
    return img


if __name__ == '__main__':
    import subprocess
    mode = sys.argv[1]
    if mode == 'stills':
        out = sys.argv[2]; os.makedirs(out, exist_ok=True)
        for tt in sys.argv[3:]:
            img = render(int(round(float(tt) * FPS)))
            cv2.imwrite(os.path.join(out, 'f_%06.2f.png' % float(tt)), img[..., ::-1])
    elif mode == 'chunk':
        a, b_, path = int(sys.argv[2]), min(int(sys.argv[3]), NFR), sys.argv[4]
        p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
                              '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '17',
                              '-pix_fmt', 'yuv420p', path], stdin=subprocess.PIPE)
        for i in range(a, b_):
            p.stdin.write(render(i).tobytes())
            if (i - a) % 150 == 0: print(path, i, flush=True)
        p.stdin.close(); p.wait()
