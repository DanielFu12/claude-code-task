"""全片共用的视觉元素：背景（渐变 + 星云 + 景深尘埃）、千万家庭光点场、章节标签、图标、小组件。"""
import json
import math
import os

import cv2
import numpy as np

from engine import *          # noqa: F401,F403
from timeline import CHAPTERS, DUR, SEC

BUILD = os.path.join(ROOT, 'build')

# ---------------------------------------------------------------- 音乐同步数据
_META = None


def meta():
    global _META
    if _META is None:
        p = os.path.join(BUILD, 'music_meta.json')
        if os.path.exists(p):
            m = json.load(open(p))
            _META = (np.array(m['pulse'], np.float32), np.array(m['energy'], np.float32))
        else:
            n = int(DUR * FPS) + 2
            _META = (np.zeros(n, np.float32), np.full(n, 0.5, np.float32))
    return _META


def pulse(t):
    p, _ = meta()
    i = int(t * FPS)
    return float(p[min(max(i, 0), len(p) - 1)])


def energy(t):
    _, e = meta()
    i = int(t * FPS)
    return float(e[min(max(i, 0), len(e) - 1)])


def beat_pulse(t, decay=0.12):
    """每拍一次的轻脉冲（0.5 s 一拍）"""
    ph = (t % 0.5)
    return math.exp(-ph / decay)


# ---------------------------------------------------------------- 背景
_NEB = None


def _nebula_fields():
    global _NEB
    if _NEB is None:
        r = np.random.default_rng(31)
        fields = []
        for k in range(3):
            acc = np.zeros((H // 4 + 160, W // 4 + 160), np.float32)
            for sc, amp in ((40, 1.0), (18, 0.5), (8, 0.25)):
                n = r.standard_normal(acc.shape).astype(np.float32)
                acc += cv2.GaussianBlur(n, (0, 0), sc) * amp * sc
            acc = (acc - acc.min()) / (acc.max() - acc.min())
            fields.append(acc ** 2.2)
        _NEB = fields
    return _NEB


# 背景色关键帧：(时间, 顶色, 底色, 星云色A, 星云色B, 星云强度)
BGK = [
    (0.0, C(3, 5, 12), C(8, 13, 26), C(30, 60, 120), C(20, 30, 70), 0.35),
    (11.5, C(3, 5, 12), C(8, 13, 26), C(30, 60, 120), C(20, 30, 70), 0.3),
    (13.0, C(6, 6, 14), C(30, 20, 12), C(140, 90, 40), C(40, 50, 110), 0.55),
    (20.0, C(4, 7, 15), C(9, 16, 30), C(40, 80, 140), C(110, 80, 40), 0.4),
    (44.0, C(4, 6, 13), C(8, 12, 24), C(40, 70, 130), C(30, 40, 80), 0.3),
    (60.0, C(7, 6, 12), C(22, 16, 14), C(160, 110, 50), C(60, 50, 110), 0.5),
    (72.0, C(8, 6, 10), C(24, 16, 12), C(170, 110, 50), C(110, 60, 40), 0.45),
    (94.0, C(4, 8, 14), C(8, 18, 28), C(40, 120, 150), C(80, 60, 150), 0.42),
    (116.0, C(4, 6, 14), C(12, 12, 30), C(120, 90, 50), C(50, 80, 160), 0.5),
    (129.0, C(3, 6, 14), C(6, 14, 30), C(30, 80, 160), C(20, 40, 90), 0.45),
    (134.0, C(4, 6, 13), C(8, 12, 24), C(40, 70, 130), C(30, 40, 80), 0.3),
    (146.0, C(6, 6, 12), C(16, 14, 18), C(150, 100, 50), C(50, 70, 140), 0.45),
    (152.0, C(5, 6, 14), C(30, 18, 12), C(190, 120, 50), C(60, 60, 130), 0.55),
    (164.0, C(10, 4, 6), C(30, 10, 12), C(120, 40, 40), C(150, 100, 40), 0.45),
    (178.0, C(3, 4, 10), C(6, 9, 20), C(40, 70, 140), C(30, 40, 90), 0.3),
    (188.0, C(3, 4, 10), C(6, 9, 20), C(40, 70, 140), C(30, 40, 90), 0.3),
]


def _bgk(t):
    for (t0, *a), (t1, *b) in zip(BGK, BGK[1:]):
        if t <= t1:
            x = ss((t - t0) / max(t1 - t0, 1e-6))
            return [lerp(np.asarray(p), np.asarray(q), x) for p, q in zip(a, b)]
    return [np.asarray(v) for v in BGK[-1][1:]]


_GRAD = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]


_GRAD4 = np.linspace(0, 1, H // 4, dtype=np.float32)[:, None, None]


def background(t):
    """渐变 + 星云在 1/4 分辨率合成后一次放大（都是低频内容）"""
    top, bot, na, nb, ni = _bgk(t)
    h4, w4 = H // 4, W // 4
    img = (top[None, None, :] * (1 - _GRAD4) + bot[None, None, :] * _GRAD4).astype(np.float32)
    f = _nebula_fields()
    ox = 80 + 60 * math.sin(t * 0.021)
    oy = 80 + 70 * math.cos(t * 0.017)
    a = cv2.getRectSubPix(f[0], (w4, h4), (w4 / 2 + ox, h4 / 2 + oy))
    b = cv2.getRectSubPix(f[1], (w4, h4), (w4 / 2 + 160 - ox, h4 / 2 + 160 - oy))
    small = img + (a[..., None] * na[None, None, :] + b[..., None] * nb[None, None, :]) * ni * 0.5
    return cv2.resize(small.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)


# ---------------------------------------------------------------- 景深尘埃
_R = np.random.default_rng(77)
DUST_N = 520
DUST = np.c_[_R.uniform(-1600, 1600, DUST_N), _R.uniform(-2400, 2400, DUST_N), _R.uniform(300, 4200, DUST_N)]
DUST_TW = _R.random(DUST_N) * 6.28
DUST_COL = np.where(_R.random(DUST_N)[:, None] < 0.7, C(200, 215, 255), C(255, 220, 160))


def draw_dust(fr, t, a=1.0, speed=1.0, col=None):
    if a <= 0.01:
        return
    P = DUST.copy()
    P[:, 2] = (P[:, 2] - t * 60 * speed) % 3900 + 300
    P[:, 1] += 40 * np.sin(t * 0.1 + DUST_TW)
    s = 900.0 / P[:, 2]
    x = W / 2 + P[:, 0] * s
    y = H / 2 + P[:, 1] * s
    ok = (x > -10) & (x < W + 10) & (y > -10) & (y < H + 10)
    tw = 0.55 + 0.45 * np.sin(t * 1.3 + DUST_TW * 3)
    alpha = np.clip(s * 1.2, 0.05, 0.9) * tw * a * 0.55 * np.clip((P[:, 2] - 300) / 400, 0, 1)
    rad = np.clip(s * 2.2, 0.6, 3.5)
    cc = DUST_COL if col is None else np.broadcast_to(col, DUST_COL.shape)
    fr.dots(x[ok], y[ok], rad[ok], cc[ok], alpha[ok], layer='B')
    fr.splat(x[ok], y[ok], cc[ok], alpha[ok] * 0.6, layer='L')


# ---------------------------------------------------------------- 千万家庭光点场（3D 平面网格）
class Field:
    def __init__(self, n=96, spacing=1.0, seed=5):
        r = np.random.default_rng(seed)
        g = (np.arange(n) - (n - 1) / 2) * spacing
        X, Z = np.meshgrid(g, g)
        jit = r.uniform(-0.32, 0.32, (2, n, n)) * spacing
        self.P = np.c_[(X + jit[0]).ravel(), np.zeros(n * n), (Z + jit[1]).ravel()]
        self.n = n * n
        self.ph = r.random(self.n) * 6.28
        self.sz = r.random(self.n)
        self.kind = (r.random(self.n) < 0.12)       # 少数为企业（冰蓝）
        self.R = r.random(self.n)

    def draw(self, fr, cam, t, a=1.0, warm=None, bright=None, col_warm=GOLD, col_cold=ICE, size=1.0,
             lift=None, firms=True):
        """warm: (N,) 0..1 暖色比例（消费/乐观）；bright: (N,) 亮度乘子；lift: (N,) 竖直抬升"""
        if a <= 0.01:
            return None
        P = self.P if lift is None else self.P + np.c_[np.zeros(self.n), lift, np.zeros(self.n)]
        x, y, z, s = cam.project(P)
        ok = (z > 0.5) & (x > -20) & (x < W + 20) & (y > -20) & (y < H + 20)
        w = np.full(self.n, 0.8) if warm is None else warm
        col = col_warm[None, :] * w[:, None] + col_cold[None, :] * (1 - w[:, None])
        if firms:
            col = np.where(self.kind[:, None], ICE_HI[None, :] * 0.9, col)
        tw = 0.65 + 0.35 * np.sin(t * 2.0 + self.ph)
        br = tw * (0.45 + 0.55 * self.sz) if bright is None else tw * bright * (0.45 + 0.55 * self.sz)
        depth_fade = np.clip(s * 0.035, 0.12, 1.0)
        al = br * a * depth_fade * 2.2
        rad = np.clip(s * 0.05 * size * (0.6 + 0.7 * self.sz), 0.6, 4.0)
        fr.splat(x[ok], y[ok], col[ok], al[ok], layer='L')
        big = ok & (rad > 1.25)
        fr.dots(x[big], y[big], rad[big], col[big], al[big] * 0.9, layer='L')
        fr.splat(x[ok], y[ok], col[ok], al[ok] * 2.0, layer='B')
        return x, y, z, s, ok


FIELD = Field()


# ---------------------------------------------------------------- 章节标签 + 进度
def chapter_overlay(fr, t):
    for t0, t1, num, name in CHAPTERS:
        a = win(t, t0, t1, 0.6, 0.5)
        if a <= 0:
            continue
        fr.text(num, 64, 74, 30, 'inter_bold', 'gold', a * 0.95, 'l', track=0.08, glow=0.2, shadow=0.4)
        fr.text(name, 112, 74, 32, 'serif_bold', 'white', a * 0.9, 'l', track=0.12, glow=0.0, shadow=0.4)
        # 章节内进度条
        p = cl((t - t0) / (t1 - t0))

        def bar(img, a=a, p=p):
            x0, x1, y = 64, 64 + 236, 110
            img[y:y + 2, x0:x1] = img[y:y + 2, x0:x1] * (1 - 0.25 * a) + 0.25 * a * WHITE * 0.5
            xe = int(x0 + (x1 - x0) * p)
            img[y:y + 2, x0:xe] = img[y:y + 2, x0:xe] * (1 - 0.9 * a) + 0.9 * a * GOLD
        fr.overlay_fn(bar)


def footnote(fr, s, a, y=1412):
    fr.text(s, W / 2, y, 28, 'sans_reg', 'grey', a, 'c', track=0.03, glow=0, shadow=0.6)


def chip(fr, s, cx, cy, a, col=GOLD, size=40, fname='sans_med', base=None, pad=(30, 16), fill=0.1, scale=1.0):
    if a <= 0.01:
        return
    w, h = text_size(s, fname, int(size * scale))
    w2, h2 = w / 2 + pad[0] * scale, size * scale * 0.62 + pad[1] * scale
    fr.card(cx - w2, cy - h2, cx + w2, cy + h2, r=h2, a=a, tint=col, border=col, border_a=0.85, fill_a=fill,
            blur=10)
    fr.text(s, cx, cy, int(size * scale), fname, base or ('gold' if col is GOLD else 'white'), a, 'c', glow=0.15,
            shadow=0.0)


# ---------------------------------------------------------------- 线条图标（以中心 c、尺寸 s 绘制）
def icon(fr, kind, c, s, col, a=1.0, th=3.0, glow=0.6):
    x, y = c
    P = lambda pts: [(x + px * s, y + py * s) for px, py in pts]
    if kind == 'house':
        fr.stroke(P([(-0.5, -0.05), (0, -0.5), (0.5, -0.05)]), col, a, th, glow=glow)
        fr.stroke(P([(-0.38, -0.12), (-0.38, 0.45), (0.38, 0.45), (0.38, -0.12)]), col, a, th, glow=glow)
        fr.stroke(P([(-0.1, 0.45), (-0.1, 0.12), (0.1, 0.12), (0.1, 0.45)]), col, a, th * 0.8, glow=glow)
    elif kind == 'car':
        fr.stroke(P([(-0.55, 0.2), (-0.55, 0.0), (-0.35, -0.05), (-0.2, -0.3), (0.25, -0.3), (0.42, -0.05),
                     (0.55, 0.0), (0.55, 0.2), (-0.55, 0.2)]), col, a, th, glow=glow)
        fr.circle((x - 0.3 * s, y + 0.22 * s), 0.11 * s, col, a, th, glow=glow)
        fr.circle((x + 0.3 * s, y + 0.22 * s), 0.11 * s, col, a, th, glow=glow)
    elif kind == 'card':
        fr.rrect(x - 0.5 * s, y - 0.32 * s, x + 0.5 * s, y + 0.32 * s, 0.07 * s, col, a, th, glow=glow)
        fr.line((x - 0.5 * s, y - 0.12 * s), (x + 0.5 * s, y - 0.12 * s), col, a, th, glow=glow)
        fr.line((x - 0.35 * s, y + 0.15 * s), (x - 0.05 * s, y + 0.15 * s), col, a, th * 0.8, glow=glow)
    elif kind == 'factory':
        fr.stroke(P([(-0.55, 0.45), (-0.55, -0.05), (-0.25, -0.25), (-0.25, -0.05), (0.05, -0.25), (0.05, -0.05),
                     (0.35, -0.25), (0.35, -0.55), (0.5, -0.55), (0.5, 0.45), (-0.55, 0.45)]), col, a, th, glow=glow)
    elif kind == 'plug':
        fr.rrect(x - 0.42 * s, y - 0.3 * s, x + 0.42 * s, y + 0.25 * s, 0.06 * s, col, a, th, glow=glow)
        fr.line((x - 0.15 * s, y + 0.25 * s), (x - 0.22 * s, y + 0.42 * s), col, a, th, glow=glow)
        fr.line((x + 0.15 * s, y + 0.25 * s), (x + 0.22 * s, y + 0.42 * s), col, a, th, glow=glow)
        fr.line((x - 0.3 * s, y + 0.42 * s), (x + 0.3 * s, y + 0.42 * s), col, a, th, glow=glow)
    elif kind == 'plane':
        fr.stroke(P([(-0.55, 0.05), (0.5, -0.08), (0.58, 0.0), (0.5, 0.08), (-0.55, 0.05)]), col, a, th, glow=glow)
        fr.stroke(P([(0.0, -0.02), (-0.18, -0.45), (-0.05, -0.45), (0.22, -0.04)]), col, a, th, glow=glow)
        fr.stroke(P([(0.0, 0.06), (-0.18, 0.45), (-0.05, 0.45), (0.22, 0.06)]), col, a, th, glow=glow)
    elif kind == 'wheat':
        fr.line((x, y + 0.5 * s), (x, y - 0.5 * s), col, a, th, glow=glow)
        for k in range(4):
            yy = y - 0.35 * s + k * 0.2 * s
            fr.stroke([(x, yy + 0.08 * s), (x - 0.2 * s, yy - 0.05 * s)], col, a, th, glow=glow)
            fr.stroke([(x, yy + 0.08 * s), (x + 0.2 * s, yy - 0.05 * s)], col, a, th, glow=glow)
    elif kind == 'person':
        fr.circle((x, y - 0.32 * s), 0.17 * s, col, a, th, glow=glow)
        ang = np.linspace(math.pi, 2 * math.pi, 24)
        pts = [(x + 0.36 * s * math.cos(q), y + 0.45 * s + 0.5 * s * math.sin(q)) for q in ang]
        fr.stroke(pts + [pts[0]], col, a, th, glow=glow)
    elif kind == 'lock':
        fr.rrect(x - 0.32 * s, y - 0.05 * s, x + 0.32 * s, y + 0.42 * s, 0.06 * s, col, a, th, glow=glow)
        fr.arc((x, y - 0.05 * s), 0.2 * s, math.pi, 2 * math.pi, col, a, th, glow=glow)
    elif kind == 'bank':
        fr.stroke(P([(-0.55, -0.15), (0, -0.5), (0.55, -0.15), (-0.55, -0.15)]), col, a, th, glow=glow)
        for px in (-0.38, -0.13, 0.13, 0.38):
            fr.line((x + px * s, y - 0.08 * s), (x + px * s, y + 0.32 * s), col, a, th, glow=glow)
        fr.line((x - 0.58 * s, y + 0.42 * s), (x + 0.58 * s, y + 0.42 * s), col, a, th, glow=glow)
    elif kind == 'coin':
        fr.circle((x, y), 0.42 * s, col, a, th, glow=glow)
        fr.circle((x, y), 0.3 * s, col, a * 0.6, th * 0.7, glow=glow)
    elif kind == 'bowl':
        ang = np.linspace(0, math.pi, 24)
        fr.stroke([(x + 0.5 * s * math.cos(q), y + 0.4 * s * math.sin(q)) for q in ang] + [(x - 0.5 * s, y)], col,
                  a, th, glow=glow)
        for k in range(3):
            xx = x - 0.18 * s + k * 0.18 * s
            fr.stroke([(xx, y - 0.1 * s), (xx + 0.06 * s, y - 0.3 * s), (xx - 0.02 * s, y - 0.5 * s)], col, a * 0.7,
                      th * 0.7, glow=glow)


def fmt(v, d=2):
    return f'{v:.{d}f}'
