"""《伪价值投资》竖屏 1080×1920 分镜。所有时间点读自 work/timeline.json（旁白排在 80BPM 网格上）。
用法: python3 video.py chunk F0 F1 out.mp4   |   python3 video.py still t out.png"""
import sys, os, json, math, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw
from scipy.interpolate import PchipInterpolator
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', 'brand'))
from engine import *
from engine import font as get_font
from brand import Hud, load_logo

WORK = os.environ.get('WORK', os.path.join(HERE, '..', 'work'))
TL = json.load(open(os.path.join(WORK, 'timeline.json')))
HITS = json.load(open(os.path.join(WORK, 'hits.json')))
LN = {l['id']: l for l in TL['lines']}
S = TL['sections']; TOTAL = TL['total']; BEAT = TL['beat']; CUE = TL['cues']
CH_ = None
CX = W / 2
RED2 = C(255, 86, 86); DIM = C(120, 128, 150); PAPER = C(236, 228, 210)

def L0(i): return LN[i]['t0']
def L1(i): return LN[i]['t1']
def CH(i, k): return LN[i]['chunks'][k][1]
def onset(i):
    l = LN[i]; ps = [b for a, b in l['pauses'] if a > 0.3]
    return l['t0'] + (ps[0] if ps else 0.36 * (l['t1'] - l['t0']))
def P(i, k):   # 第 k 个停顿结束（相对句首→绝对时间）
    return LN[i]['t0'] + LN[i]['pauses'][k][1]

def impact(t, big=0.0):
    v = 0.0
    for th, s in HITS:
        if th <= t < th + 2 and s >= big: v = max(v, s * math.exp(-(t - th) * 4.5))
    return v

# ================================================================ 背景
rng0 = np.random.default_rng(5)
NEB_A = fbm(240, 427, 3, octaves=5, base=3)
NEB_B = fbm(240, 427, 17, octaves=5, base=3)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.55 * np.clip(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.46) / (H * 0.6)) ** 2, 0, 1.4) ** 1.3)[..., None]
VIG = np.clip(VIG, 0.25, 1).astype(np.float32)
GRAD = (1 - yy / H)[..., None].astype(np.float32)
del xx, yy
GRAIN = [cv2.resize(rng0.normal(0, 1, (H // 2, W // 2)).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)[..., None] * 0.016
         for _ in range(6)]
DUST = dict(x=rng0.random(150) * W, y=rng0.random(150) * H, z=0.3 + rng0.random(150) * 0.7, ph=rng0.random(150) * 6.28)

# 每个章节的色调：(星云色, 底色)
MOOD = [(0, (C(40, 70, 140), C(4, 6, 14))), (S['cases'] - 0.5, (C(40, 70, 140), C(4, 6, 14))),
        (S['cases'] + 1, (C(30, 80, 120), C(3, 7, 12))), (L0('A1'), (C(90, 40, 60), C(8, 4, 8))),
        (L0('N1'), (C(30, 90, 70), C(3, 8, 7))), (L0('N2'), (C(30, 30, 40), C(2, 2, 4))), (L0('N3'), (C(70, 30, 35), C(6, 2, 3))),
        (S['pivot'] + 3, (C(60, 30, 30), C(5, 2, 3))), (S['title'], (C(140, 100, 40), C(8, 6, 3))),
        (S['hammer'] + 1, (C(120, 80, 30), C(7, 5, 2))), (S['strikes'], (C(150, 70, 30), C(8, 4, 2))),
        (S['ask'] + 1, (C(40, 40, 60), C(2, 2, 4))), (S['two'] + 1, (C(150, 115, 50), C(8, 6, 3))),
        (S['tx'], (C(60, 80, 130), C(4, 5, 10))), (S['ali'], (C(130, 60, 40), C(7, 3, 3))),
        (S['zp'], (C(60, 70, 110), C(4, 4, 9))), (S['nv'], (C(40, 100, 80), C(3, 7, 6))),
        (S['cure'] - 0.5, (C(40, 40, 60), C(3, 3, 6))), (S['cure'] + 1.5, (C(70, 110, 170), C(5, 7, 13))),
        (S['finale'], (C(170, 120, 50), C(9, 7, 4))), (S['card'], (C(60, 50, 30), C(3, 3, 3)))]

def mood(t):
    nb = keys(t, [(a, b[0]) for a, b in MOOD]); base = keys(t, [(a, b[1]) for a, b in MOOD])
    return nb, base

def background(t):
    nb, base = mood(t)
    ox, oy = 18 * math.sin(t * 0.05), t * 1.6
    M1 = np.float32([[1, 0, ox], [0, 1, -oy % 427]])
    a = cv2.warpAffine(NEB_A, M1, (240, 427), borderMode=cv2.BORDER_WRAP)
    b = cv2.warpAffine(NEB_B, np.float32([[1, 0, -ox * 0.7], [0, 1, (-oy * 0.6) % 427]]), (240, 427), borderMode=cv2.BORDER_WRAP)
    n = np.clip(a * 0.6 + b * 0.6 - 0.45, 0, 1) ** 1.6
    n = cv2.resize(n, (W, H), interpolation=cv2.INTER_CUBIC)[..., None]
    bg = np.array(base, np.float32) * (0.6 + 0.8 * GRAD) + n * np.array(nb, np.float32) * 0.22
    return bg.astype(np.float32)

def dust(fr, t, a=1.0, col=GOLD2):
    d = DUST
    x = (d['x'] + 8 * np.sin(t * 0.3 + d['ph'])) % W
    y = (d['y'] - t * 22 * d['z']) % H
    tw = 0.5 + 0.5 * np.sin(t * 1.3 + d['ph'] * 3)
    fr.splat(x, y, col, 0.35 * a * d['z'] * tw, 'B')
    fr.splat(x, y, col, 0.12 * a * d['z'] * tw, 'E')

# ================================================================ 小工具
@lru_cache(512)
def line_mask(s, fnt, size, track=0.0):
    tw = int(text_width(s, fnt, size, track)) + int(size * 0.6)
    f = get_font(fnt, size); asc, desc = f.getmetrics()
    im = Image.new('L', (tw, asc + desc + int(size * 0.4)), 0)
    d = ImageDraw.Draw(im); x = size * 0.3
    for ch in s:
        d.text((x, int(size * 0.2) + asc), ch, font=f, fill=255, anchor='ls'); x += f.getlength(ch) + track * size
    return np.asarray(im, np.float32) / 255

@lru_cache(64)
def stamp_mask(s, size, ang):
    m = line_mask(s, 'serif_black', size)
    h, w = m.shape; pad = int(size * 0.35)
    im = np.zeros((h + 2 * pad, w + 2 * pad), np.float32); im[pad:pad + h, pad:pad + w] = m
    bw = max(3, size // 14)
    cv2.rectangle(im, (pad // 2, pad // 2 + int(size * 0.12)), (w + pad + pad // 2, h + pad + pad // 2 - int(size * 0.12)), 1.0, bw)
    M = cv2.getRotationMatrix2D((im.shape[1] / 2, im.shape[0] / 2), ang, 1.0)
    big = int(max(im.shape) * 1.2)
    M[0, 2] += (big - im.shape[1]) / 2; M[1, 2] += (big - im.shape[0]) / 2
    return cv2.warpAffine(im, M, (big, big))

def blit_mask(fr, m, cx, cy, col, a, mode='L', glow=0.0, scale=1.0):
    if a <= 0.003: return
    if abs(scale - 1) > 0.01:
        m = cv2.resize(m, (max(1, int(m.shape[1] * scale)), max(1, int(m.shape[0] * scale))), interpolation=cv2.INTER_LINEAR)
    fr._blit(m, cx - m.shape[1] / 2, cy - m.shape[0] / 2, col, a, mode, glow)

def stamp(fr, t, s, x, y, size, t0, col=RED, ang=-12, a=1.0):
    if t < t0: return
    u = (t - t0) / 0.28
    sc = 1 + 0.8 * (1 - eo(u)); al = eo(u) * a
    blit_mask(fr, stamp_mask(s, size, ang), x, y, col, al * 0.95, 'E', 0.25, sc)

def dashed(fr, p0, p1, col, a, th=2, dash=14, gap=10, prog=1.0):
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) * prog
    if L < 1: return
    ux, uy = (p1[0] - p0[0]) / max(L / prog, 1e-6), (p1[1] - p0[1]) / max(L / prog, 1e-6)
    s = 0.0
    while s < L:
        e = min(s + dash, L)
        fr.line((p0[0] + ux * s, p0[1] + uy * s), (p0[0] + ux * e, p0[1] + uy * e), col, a, th)
        s += dash + gap

def check(fr, x, y, sz, prog, col=GOLD, a=1.0, th=4):
    if prog <= 0: return
    pts = [(x - sz * 0.45, y), (x - sz * 0.12, y + sz * 0.33), (x + sz * 0.5, y - sz * 0.42)]
    l1 = math.dist(pts[0], pts[1]); l2 = math.dist(pts[1], pts[2]); L = (l1 + l2) * cl(prog)
    if L <= l1:
        u = L / l1; fr.line(pts[0], (lerp(pts[0][0], pts[1][0], u), lerp(pts[0][1], pts[1][1], u)), col, a, th)
    else:
        u = (L - l1) / l2
        fr.poly([pts[0], pts[1], (lerp(pts[1][0], pts[2][0], u), lerp(pts[1][1], pts[2][1], u))], col, a, th)

def cross(fr, x, y, sz, prog, col=RED, a=1.0, th=4):
    u1, u2 = cl(prog * 2), cl(prog * 2 - 1)
    if u1 > 0: fr.line((x - sz, y - sz), (x - sz + 2 * sz * u1, y - sz + 2 * sz * u1), col, a, th)
    if u2 > 0: fr.line((x + sz, y - sz), (x + sz - 2 * sz * u2, y - sz + 2 * sz * u2), col, a, th)

def counter(t, t0, t1, v0, v1):
    return lerp(v0, v1, eo((t - t0) / max(t1 - t0, 1e-3)))

def header(fr, t, tag, title, a, t0, hl=None, y=330):
    """章节标题：小标签 + 大字（hl: 需要标红的字符集合）"""
    fr.text(tag, CX, y - 92, 30, 'mono', GOLD, a * 0.9, track=0.25, t0=t0, mode='L')
    fs = 92
    while text_width(title, 'serif_black', fs) > 900: fs -= 4
    tw = text_width(title, 'serif_black', fs)
    x = CX - tw / 2
    for i, ch in enumerate(title):
        col = RED2 if hl and ch in hl else WHITE
        fr.text(ch, x, y, fs, 'serif_black', col, a, anchor='l', t0=t0 + 0.1 + i * 0.04, mode='L', glow=0.15)
        x += glyph(ch, 'serif_black', fs)[1]
    fr.line((CX - 60 * a, y + 78), (CX + 60 * a, y + 78), GOLD, a * 0.8, 2)

# ================================================================ 股价走势（关键价位为真实约数，中间为示意）
def make_series(anchors, n=600, seed=1, wig=0.02):
    xs = np.array([p[0] for p in anchors], float); ys = np.array([p[1] for p in anchors], float)
    X = np.linspace(xs[0], xs[-1], n); Y = PchipInterpolator(xs, ys)(X)
    r = np.random.default_rng(seed)
    nz = cv2.GaussianBlur(r.standard_normal((1, n)).astype(np.float32), (0, 0), 2.0)[0]; nz /= nz.std() + 1e-6
    idx = np.searchsorted(xs, X).clip(1, len(xs) - 1)
    u = (X - xs[idx - 1]) / np.maximum(xs[idx] - xs[idx - 1], 1e-9)
    return X, Y * (1 + wig * nz * np.sin(np.pi * u))

CASES = [
 dict(no='01', name='腾讯控股', sub='0700.HK · 港元 · 截至 2026.11.18', x0=2017.7, x1=2026.95, y0=120, y1=860, buy=(2018.22, 400),
      anchors=[(2017.7, 330), (2018.08, 476), (2018.22, 400), (2018.5, 380), (2018.83, 255), (2019.3, 395), (2019.65, 325),
               (2020.2, 380), (2020.55, 560), (2021.13, 775), (2021.6, 440), (2022.0, 470), (2022.4, 350), (2022.82, 190),
               (2023.08, 400), (2023.7, 310), (2024.1, 270), (2024.8, 410), (2025.3, 500), (2025.8, 650), (2026.05, 630),
               (2026.4, 520), (2026.81, 375), (2026.85, 430), (2026.88, 373)],
      peak=(2018.08, 476, '高点 476'), end=(2026.88, 373, '373'), grid=[200, 400, 600, 800],
      xl=[(2018.0, '2018'), (2022.0, '2022'), (2026.0, '2026')],
      t_in=L0('T1') - 0.3, t_out=L0('A1') - 0.5, badge='-7%', cap='8 年 · 股价仍低于买入价（不含分红）', seed=3,
      rev=[(L0('T1'), 2017.7), (L0('T1') + 1.9, 2018.08), (CH('T1', 1) - 0.1, 2018.22), (CUE['tx_now'] - 1.0, 2018.22), (CUE['tx_now'], 2026.88)]),
 dict(no='02', name='阿里巴巴', sub='BABA · 美元 · 截至 2026.11.18', x0=2020.45, x1=2026.95, y0=20, y1=360, buy=(2021.68, 150),
      anchors=[(2020.45, 250), (2020.82, 319), (2021.0, 222), (2021.15, 260), (2021.45, 210), (2021.6, 168), (2021.68, 150),
               (2021.85, 165), (2022.0, 120), (2022.2, 75), (2022.45, 118), (2022.62, 92), (2022.81, 60), (2023.08, 118),
               (2023.5, 95), (2023.95, 72), (2024.1, 68), (2024.75, 108), (2025.15, 140), (2025.3, 105), (2025.6, 120),
               (2025.78, 185), (2026.0, 147), (2026.4, 125), (2026.7, 115), (2026.84, 107), (2026.88, 84)],
      peak=(2020.82, 319, '高点 319'), end=(2026.88, 84, '84'), grid=[100, 200, 300],
      marks=[(2022.81, 60, '2022 低点 60')],
      xl=[(2021.0, '2021'), (2023.0, '2023'), (2025.0, '2025'), (2026.6, '2026')],
      t_in=L0('A1') - 0.25, t_out=L0('Z1') - 0.5, badge='-44%', cap='5 年后，仍亏四成多', seed=8,
      rev=[(L0('A1'), 2020.45), (L0('A1') + 1.6, 2020.82), (CH('A1', 1) - 0.2, 2021.68), (CUE['ali_low'] - 0.9, 2021.68),
           (CUE['ali_low'], 2022.81), (CUE['ali_now'] - 1.3, 2022.81), (CUE['ali_now'], 2026.88)]),
 dict(no='03', name='智谱', sub='2513.HK · 港元 · 截至 2026.11.18', x0=2026.38, x1=2026.92, y0=0, y1=3300, buy=(2026.57, 1500),
      anchors=[(2026.38, 620), (2026.43, 900), (2026.455, 1050), (2026.47, 2980), (2026.49, 2350), (2026.52, 1950),
               (2026.57, 1500), (2026.62, 1280), (2026.69, 980), (2026.77, 720), (2026.83, 442), (2026.86, 408),
               (2026.875, 335), (2026.88, 366)],
      peak=(2026.47, 2980, '高点 2980'), end=(2026.88, 366, '366'), grid=[1000, 2000, 3000],
      xl=[(2026.42, '2026.06'), (2026.86, '2026.11')],
      t_in=L0('Z1') - 0.25, t_out=L0('N1') - 0.5, badge='-76%', cap='1500 → 750 → 375：又是两场腰斩', seed=11,
      rev=[(L0('Z1'), 2026.38), (L0('Z1') + 1.7, 2026.47), (CH('Z1', 1) - 0.3, 2026.57), (CUE['zp_now'] - 0.9, 2026.57), (CUE['zp_now'], 2026.88)]),
 dict(no='04', name='英伟达', sub='NVDA · 美元 · 截至 2026.11.18', x0=2026.45, x1=2026.93, y0=120, y1=260, buy=(2026.85, 180),
      anchors=[(2026.45, 172), (2026.53, 188), (2026.6, 182), (2026.66, 206), (2026.72, 224), (2026.77, 240), (2026.81, 214),
               (2026.835, 196), (2026.85, 180), (2026.86, 186), (2026.87, 162), (2026.875, 155), (2026.88, 151)],
      peak=(2026.77, 240, '高点 ≈240'), end=(2026.88, 151, '151'), grid=[150, 200, 250],
      xl=[(2026.5, '2026.07'), (2026.86, '2026.11')],
      t_in=L0('N1') - 0.25, t_out=S['pivot'] - 0.6, badge='-16%', cap='营收翻倍，股价照跌', seed=21,
      rev=[(L0('N1'), 2026.45), (CH('N1', 1), 2026.77), (CH('N1', 2) - 0.2, 2026.85), (CUE['nv_now'] - 1.4, 2026.85), (CUE['nv_now'], 2026.88)]),
]
for c in CASES:
    c['X'], c['Y'] = make_series(c['anchors'], seed=c['seed'])

BX0, BX1, BY0, BY1 = 110, 930, 560, 1150

def case_xf(c, box=(BX0, BY0, BX1, BY1), dx=0.0):
    x0b, y0b, x1b, y1b = box
    px = lambda x: x0b + (x - c['x0']) / (c['x1'] - c['x0']) * (x1b - x0b) + dx
    py = lambda y: y1b - (y - c['y0']) / (c['y1'] - c['y0']) * (y1b - y0b)
    return px, py

def draw_chart(fr, t, c, a, dx=0.0, box=None, d=None, mini=False):
    box = box or (BX0, BY0, BX1, BY1)
    px, py = case_xf(c, box, dx)
    x0b, y0b, x1b, y1b = box
    if d is None: d = keys(t, c['rev'])
    # 网格
    for g in c['grid']:
        fr.line((x0b + dx, py(g)), (x1b + dx, py(g)), DIM, a * 0.18, 1)
        if not mini: fr.text(str(g), x1b + 14 + dx, py(g), 24, 'mono', DIM, a * 0.55, anchor='l')
    fr.line((x0b + dx, y1b), (x1b + dx, y1b), DIM, a * 0.4, 1)
    if not mini:
        for xv, lab in c['xl']:
            fr.text(lab, px(xv), y1b + 34, 26, 'mono', DIM, a * 0.7)
    X, Y = c['X'], c['Y']
    m = X <= d
    if m.sum() < 2: return px, py
    xs = np.append(X[m], d); ys = np.append(Y[m], np.interp(d, X, Y))
    pts = np.stack([[px(x) for x in xs], [py(y) for y in ys]], 1)
    bx = c['buy'][0]
    pre = xs <= bx
    th = 2 if mini else 3
    fr.poly(pts[pre], C(220, 228, 245), a * 0.85, th)
    if (~pre).sum() > 0:
        k = max(pre.sum() - 1, 0)
        post, yv = pts[k:], ys[k:]
        below = yv < c['buy'][1]
        fr.poly(post, C(220, 228, 245), a * 0.7, th)
        i = 0
        while i < len(below):          # 跌破买点的区段标红
            if below[i]:
                j = i
                while j < len(below) and below[j]: j += 1
                fr.poly(post[max(i - 1, 0):j + 1], RED2, a * 0.95, th + 1)
                i = j
            else: i += 1
    area = np.vstack([pts, [[pts[-1, 0], y1b], [pts[0, 0], y1b]]])
    fr.fillpoly(area, RED if d > bx else C(120, 150, 220), a * 0.06)
    tip = pts[-1]
    if not mini:
        fr.glow(tip, 14, RED2 if d > bx else WHITE, a * 0.5)
        fr.circle(tip, 5, WHITE, a, -1)
    # 标注
    def mark(xv, yv, lab, col, side=1, big=False, alpha=1.0, dy=-30):
        if d < xv - 1e-6: return
        u = cl((d - xv) / ((c['x1'] - c['x0']) * 0.03) + 0.0001) if xv < d else 1.0
        u = 1.0 if d >= xv else 0.0
        p = (px(xv), py(yv)); aa = a * alpha
        fr.circle(p, 9 if not mini else 6, col, aa, 2)
        fr.glow(p, 12, col, aa * 0.5)
        if not mini and lab:
            fr.text(lab, p[0] + 18 * side, p[1] + dy, 30 if not big else 34, 'sans_med', col, aa, anchor='l' if side > 0 else 'r')
    pk = c['peak']; mark(pk[0], pk[1], pk[2], C(200, 205, 220), 1)
    for mx, my, ml in c.get('marks', []): mark(mx, my, ml, C(255, 150, 150), 1, alpha=0.85, dy=34)
    bx, bv = c['buy']
    if d >= bx:
        p = (px(bx), py(bv)); pulse = 0.5 + 0.5 * math.sin(t * 5)
        fr.circle(p, 11 if not mini else 7, GOLD, a, 3)
        fr.glow(p, 18 + 6 * pulse, GOLD, a * 0.6)
        if not mini:
            fr.text('你的买点 ' + str(bv), p[0] - 18 + (0 if p[0] > 300 else 36), p[1] + (44 if p[0] > 300 else 64), 32, 'sans_black', GOLD, a, anchor='l' if p[0] < 600 else 'r', mode='L', glow=0.2)
    if c['end'] and d >= c['end'][0] - 1e-6:
        e = c['end']; p = (px(e[0]), py(e[1]))
        fr.circle(p, 10 if not mini else 7, RED2, a, -1)
        fr.glow(p, 22, RED, a * 0.9)
        if not mini:
            fr.text(e[2], p[0] - 4, p[1] + 52, 46, 'num', RED2, a, anchor='r', mode='L', glow=0.35)
    return px, py

def case_scene(fr, t, c, i):
    a_in = eo((t - c['t_in']) / 0.5); a_out = 1 - eio((t - c['t_out']) / 0.5)
    a = a_in * a_out
    if a <= 0.003: return
    dx = (1 - eo((t - c['t_in']) / 0.6)) * 260 - eio((t - c['t_out']) / 0.5) * 260
    # 头部
    fr.text('CASE ' + c['no'] + ' / 04', CX + dx, 250, 28, 'mono', GOLD, a * 0.85, track=0.3)
    fr.text(c['name'], CX + dx, 345, 96, 'serif_black', WHITE, a, mode='L', glow=0.12)
    fr.text(c['sub'], CX + dx, 425, 30, 'mono', DIM, a * 0.9, track=0.1)
    px, py = draw_chart(fr, t, c, a, dx)
    # 收益徽章
    if c['end'] is not None:
        te = c['rev'][-1][0]
        ab = a * eo((t - te - 0.1) / 0.35)
        if ab > 0.01:
            fr.text(c['badge'], CX + dx, 1300, 150, 'num', RED2, ab, mode='L', glow=0.45)
            fr.text(c['cap'], CX + dx, 1410, 38, 'sans_med', C(210, 210, 220), ab * 0.9)
    return px, py, a, dx

def scene_cases(fr, t):
    # 腾讯：「你没有追高，只是提前八年到达了目的地」
    c = CASES[0]
    if c['t_in'] - 0.1 < t < c['t_out'] + 0.6:
        r = case_scene(fr, t, c, 0)
        if r:
            px, py, a, dx = r
            t6 = L0('T3')
            if t > t6:
                p0, p1 = (px(2018.22), py(400)), (px(2026.88), py(373))
                u = eo((t - t6) / 1.4)
                dashed(fr, p0, p1, GOLD, a * 0.9, 2, prog=u)
                if t > CH('T3', 1):
                    au = a * eo((t - CH('T3', 1)) / 0.5)
                    fx, fy = p1[0], p1[1] - 6
                    fr.line((fx, fy), (fx, fy - 70), GOLD, au, 3)
                    fr.fillpoly([(fx, fy - 70), (fx - 46, fy - 58), (fx, fy - 46)], GOLD, au * 0.9, 'E')
                    fr.text('目的地：提前 8 年到达', CX + dx, py(560), 36, 'sans_black', GOLD, au, mode='L', glow=0.2)
            o5 = CUE['tx_now']
            if o5 - 1.0 < t < o5 + 1.4:      # 八年快进：年份计数
                yr = int(keys(t, c['rev']))
                ay = a * env(t, o5 - 1.0, o5 + 1.4, 0.2, 0.4)
                fr.text(str(yr), 900 + dx, 520, 64, 'num', WHITE, ay * 0.85, anchor='r', mode='L', glow=0.2)
    # 阿里：回购 → 2022 低点 → 五年后
    c = CASES[1]
    if c['t_in'] - 0.1 < t < c['t_out'] + 0.6:
        r = case_scene(fr, t, c, 1)
        if r:
            px, py, a, dx = r
            tb = CH('A1', 1) + 0.3
            if t > tb:
                ab = a * eo((t - tb) / 0.4)
                x0, y0 = px(2021.68) + 40, py(150) - 150
                fr.rrect(x0, y0 - 30, x0 + 190, y0 + 30, 28, GOLD, ab * 0.9, 2)
                fr.text('大额回购 ✓', x0 + 95, y0, 30, 'sans_med', GOLD, ab)
            if t > CUE['ali_now'] - 1.3:
                ay = a * env(t, CUE['ali_now'] - 1.3, CUE['ali_now'] + 1.2, 0.2, 0.4)
                fr.text(str(int(keys(t, c['rev']))), 900 + dx, 520, 64, 'num', WHITE, ay * 0.85, anchor='r', mode='L', glow=0.2)
    # 智谱：三场腰斩
    c = CASES[2]
    if c['t_in'] - 0.1 < t < c['t_out'] + 0.6:
        r = case_scene(fr, t, c, 2)
        if r:
            px, py, a, dx = r
            tb = CH('Z1', 1)
            if t > tb:
                ab = a * eo((t - tb) / 0.4) * (1 - eio((t - L0('Z3')) / 0.4))
                x0, y0 = px(2026.57) + 30, py(1500) - 120
                fr.rrect(x0, y0 - 30, x0 + 250, y0 + 30, 28, GOLD, ab * 0.9, 2)
                fr.text('泡沫挤干了？', x0 + 125, y0, 30, 'sans_med', GOLD, ab)
            t11 = L0('Z3')
            if t > t11:
                xb = 985 + dx
                segs = [(2980, 1500, '①', DIM, t11, '避开'), (1500, 750, '②', RED2, CH('Z3', 1), ''), (750, 375, '③', RED2, CH('Z3', 1) + 0.45, '')]
                for hi, lo, lab, col, ts, note in segs:
                    if t < ts: continue
                    u = eo((t - ts) / 0.45); ya, yb = py(hi), py(lo)
                    fr.line((xb, ya), (xb, lerp(ya, yb, u)), col, a, 3)
                    fr.line((xb - 12, ya), (xb, ya), col, a * u, 3); fr.line((xb - 12, yb), (xb, yb), col, a * u, 3)
                    fr.text(lab, xb + 30, (ya + yb) / 2, 34, 'sans_black', col, a * u, mode='L', glow=0.2)
                    if note: fr.text(note, xb - 22, (ya + yb) / 2, 28, 'sans_med', col, a * u, anchor='r')
    # 英伟达：这一次，总该对了吧？ → 营收翻倍，股价照跌
    c = CASES[3]
    if c['t_in'] - 0.1 < t < c['t_out'] + 0.6:
        r = case_scene(fr, t, c, 3)
        if r:
            px, py, a, dx = r
            t3 = L0('N3')
            for k, (lab, tt) in enumerate([('回调 25%', CH('N1', 1) + 0.6), ('明年 PE 13×', CH('N1', 2) + 0.5)]):
                if t > tt:
                    ab = a * eo((t - tt) / 0.35) * (1 - eio((t - t3) / 0.4))
                    x0, y0 = 150 + dx, 1270 + k * 86
                    fr.rrect(x0, y0 - 32, x0 + 330, y0 + 32, 30, GOLD, ab * 0.9, 2)
                    fr.text(lab, x0 + 165, y0, 34, 'sans_black', GOLD, ab, mode='L', glow=0.15)
            t13 = L0('N2')
            aq = a * eo((t - t13) / 0.6) * (1 - eio((t - t3) / 0.5))
            if aq > 0.003:
                bx = px(2026.85)
                fr.rrect_fill(bx + 8, BY0, BX1 + dx, BY1, 8, C(30, 34, 50), aq * 0.5)
                for k in range(6):
                    yk = BY0 + 40 + k * 95
                    dashed(fr, (bx + 20, yk), (BX1 + dx - 10, yk), DIM, aq * 0.25, 1, 6, 12)
                pul = 0.75 + 0.25 * math.sin(t * 4)
                fr.text('?', (bx + BX1 + dx) / 2, (BY0 + BY1) / 2, 200, 'serif_black', WHITE, aq * pul, mode='L', glow=0.5)
            if t > t3:
                ae = a * eo((t - t3 - 0.2) / 0.4)
                x0, y0 = 150 + dx, 640
                fr.rrect(x0, y0 - 34, x0 + 380, y0 + 34, 32, TEAL, ae, 2)
                fr.rrect_fill(x0, y0 - 34, x0 + 380, y0 + 34, 32, TEAL, ae * 0.1)
                fr.text('Q3 营收 同比 +103%', x0 + 190, y0, 32, 'sans_black', TEAL, ae, mode='L', glow=0.2)

# ================================================================ 场景
def scene_hook(fr, t):
    h1 = L0('H1')
    ah = env(t, 0, S['cases'] + 0.2, 0.8, 0.5)
    for k in range(18):
        y = 300 + k * 72
        fr.line((70, y), (W - 70, y), C(90, 110, 160), ah * 0.07, 1)
    fr.line((150, 260), (150, 1600), RED, ah * 0.08, 1)
    a1 = env(t, h1 - 0.2, S['cases'] - 0.05, 0.3, 0.55)
    if a1 > 0:
        btext(fr, t, '等到回调', CX, 700, 104, 'serif_black', WHITE, a1, h1, glow=0.12)
        btext(fr, t, '买最好的公司', CX, 840, 104, 'serif_black', WHITE, a1, h1 + 0.75, glow=0.12)
        tc = CUE['H1']
        fr.line((CX - 160 * eo((t - tc + 0.3) / 0.4), 950), (CX + 160 * eo((t - tc + 0.3) / 0.4), 950), GOLD, a1 * 0.7, 2)
        btext(fr, t, '八年后', CX, 1040, 60, 'serif_med', C(200, 205, 220), a1, tc - 0.3)
        btext(fr, t, '股价还在成本线下', CX, 1180, int(100 * (1 + 0.05 * impact(t))), 'serif_black', RED2, a1, tc, glow=0.5, dur=0.45)


# ================================================================ 文字：模糊入场
@lru_cache(256)
def blurred(s, fnt, size, q):
    m = line_mask(s, fnt, size)
    p = int(q * 3) + 2
    m = np.pad(m, p)
    return cv2.GaussianBlur(m, (0, 0), q) if q > 0.2 else m

@lru_cache(64)
def grad_rows(h, stops):
    return np.stack([np.interp(np.linspace(0, 1, h), [k / (len(stops) - 1) for k in range(len(stops))], [s[c] for s in stops])
                     for c in range(3)], 1).astype(np.float32)

def btext(fr, t, s, x, y, size, fnt, col, a, t0, dur=0.7, glow=0.2, grad=None, blur=9.0):
    """模糊 → 清晰 + 轻微缩放的入场（电影片头式）。grad: 竖向渐变色标"""
    if a <= 0.003 or t < t0: return
    u = eo((t - t0) / dur)
    q = round(blur * (1 - u) * 2) / 2
    m = blurred(s, fnt, size, q)
    sc = 1 + 0.05 * (1 - u)
    if abs(sc - 1) > 0.004:
        m = cv2.resize(m, (int(m.shape[1] * sc), int(m.shape[0] * sc)), interpolation=cv2.INTER_LINEAR)
    al = a * u
    h, w = m.shape
    x0, y0 = int(x - w / 2), int(y - h / 2 + size * 0.06)
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if X1 <= X0 or Y1 <= Y0: return
    mm = m[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] * al
    rgb = grad_rows(h, tuple(tuple(g) for g in grad))[Y0 - y0:Y1 - y0, None, :] if grad else np.array(col, np.float32)
    fr.L[Y0:Y1, X0:X1] += mm[..., None] * rgb
    if glow > 0: fr.B[Y0:Y1, X0:X1] += (mm * glow)[..., None] * rgb

GOLDG = (GOLD2, GOLD, GOLDD, GOLD)
def veio(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)

def nail_header(fr, t, no, title, sub, a, t0):
    fr.text(f'NAIL {no}  ·  拔钉子', CX, 236, 28, 'mono', GOLD, a * 0.85, track=0.25, t0=t0)
    btext(fr, t, title, CX, 330, 84, 'serif_black', WHITE, a, t0 + 0.1, glow=0.12)
    fr.text(sub, CX, 410, 32, 'sans_med', C(190, 195, 210), a * 0.9, t0=t0 + 0.4)
    fr.line((CX - 50, 448), (CX + 50, 448), GOLD, a * 0.7, 2)

# ================================================================ 追问：满分 vs 四根红线
def scene_pivot(fr, t):
    t0 = S['pivot']; a = env(t, t0 - 0.2, S['title'] + 0.05, 0.5, 0.15)
    if a <= 0: return
    boxes = [(80, 300, 520, 600), (560, 300, 1000, 600), (80, 640, 520, 940), (560, 640, 1000, 940)]
    caps = ['腾讯 -7% · 8 年', '阿里 -44% · 5 年', '智谱 -76%', '英伟达 -16%']
    for k, (c, b, cap) in enumerate(zip(CASES, boxes, caps)):
        ak = a * 0.6 * eo((t - t0 - k * 0.12) / 0.4)
        fr.rrect(b[0], b[1], b[2], b[3], 14, DIM, ak * 0.4, 1)
        draw_chart(fr, t, c, ak, 0, (b[0] + 24, b[1] + 66, b[2] - 24, b[3] - 22), d=c['rev'][-1][1], mini=True)
        fr.text(cap, (b[0] + b[2]) / 2, b[1] + 34, 30, 'sans_med', RED2, ak * 1.4)
    items = ['不追高', '不碰垃圾股', '熟读巴菲特', '专门等回调']
    for k, (lab, ts) in enumerate(zip(items, CUE['q_items'])):
        x = 120 + (k % 2) * 460; y = 1040 + (k // 2) * 96
        ai = a * eo((t - ts) / 0.3)
        fr.rrect(x, y - 30, x + 60, y + 30, 10, C(200, 205, 225), ai * 0.6, 2)
        check(fr, x + 30, y, 44, (t - ts - 0.15) / 0.3, GOLD, ai, 5)
        fr.text(lab, x + 90, y, 50, 'serif_med', WHITE, ai, anchor='l')
    stamp(fr, t, '满分', 880, 1250, 84, CUE['q_std'] + 0.3, RED, -12, a)
    tq = CUE['q_ask']; hb = impact(t)
    btext(fr, t, '错在哪？', 470, 1370, int(140 * (1 + 0.03 * hb)), 'serif_black', WHITE, a, tq, glow=0.35, dur=0.5)

def scene_title(fr, t):
    t0 = S['title']; a = env(t, t0, S['hammer'] + 0.2, 0.05, 0.5)
    if a <= 0: return
    u = t - t0
    for k, (spd, col) in enumerate([(1500, GOLD), (900, RED)]):
        r = spd * eo(u / 1.2) + 10; aw = (1 - eo(u / 1.2)) * a
        fr.circle((CX, 900), r, col, aw * 0.6, 3); fr.glow((CX, 900), 60 + r * 0.1, col, aw * 0.15)
    rr = np.random.default_rng(42); n = 260
    ang = rr.random(n) * 6.283; spd = 150 + rr.random(n) * 900
    d = spd * (1 - np.exp(-u * 2.2)) / 2.2
    fr.dots(CX + np.cos(ang) * d, 900 + np.sin(ang) * d * 0.8 + u * u * 20, GOLD2, np.exp(-u * 0.9) * 0.8 * a, 1, 'E')
    fr.text('一个「价投好学生」的困惑', CX, 680, 38, 'sans_light', C(200, 200, 210), a * eo((u - 0.4) / 0.5), track=0.1)
    sc = 1 + 0.08 * (1 - eo(u / 0.5))
    tw = text_width('伪价值投资', 'serif_black', int(176 * sc)); x = CX - tw / 2
    fr.text('伪', x, 900, int(176 * sc), 'serif_black', RED2, a, anchor='l', mode='L', glow=0.6)
    x2 = x + glyph('伪', 'serif_black', int(176 * sc))[1]
    fr.text('价值投资', x2, 900, int(176 * sc), 'serif_black', GOLD, a, anchor='l', mode='L', glow=0.45, grad=[GOLD2, GOLD, GOLDD, GOLD])
    sw = (u - 0.6) / 1.2
    if 0 < sw < 1:
        fr.glow((lerp(x - 100, x + tw + 100, eio(sw)), 900), 60, WHITE, a * 0.35 * math.sin(math.pi * sw))
    fr.line((CX - 200 * eo((u - 0.5) / 0.6), 1030), (CX + 200 * eo((u - 0.5) / 0.6), 1030), GOLD, a * 0.8, 2)
    btext(fr, t, '你以为在做价值投资', CX, 1110, 52, 'serif_med', WHITE, a, t0 + 0.8)
    btext(fr, t, '其实只是在套公式', CX, 1190, 52, 'serif_med', GOLD, a, t0 + 1.4)

# ================================================================ 第二幕：铁锤人
def _hammer_sprite():
    k = 2; hw, hh, L_, hwid = 440 * k, 150 * k, 560 * k, 46 * k
    Wd, Hd = hw + 40 * k, hh + L_ + 30 * k
    im = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx = Wd // 2; hy0 = L_ + 10 * k
    # 手柄：石墨色 + 金色箍
    hx0 = cx - hwid // 2
    for x in range(hwid):
        u = x / hwid; v = int(28 + 40 * math.sin(math.pi * u) ** 2)
        d.line([(hx0 + x, 10 * k), (hx0 + x, hy0 + 10)], fill=(v, v, v + 8, 255))
    for yb in (40 * k, hy0 - 40 * k):
        d.rectangle([hx0 - 4 * k, yb, hx0 + hwid + 4 * k, yb + 14 * k], fill=(214, 168, 80, 255))
    # 锤头：金属金竖向渐变
    head = Image.new('RGBA', (hw, hh), (0, 0, 0, 0)); hd = ImageDraw.Draw(head)
    stops = [(0, (255, 240, 196)), (0.28, (232, 186, 92)), (0.55, (150, 104, 36)), (0.8, (217, 166, 74)), (1, (110, 76, 24))]
    for y in range(hh):
        u = y / hh
        c = [int(np.interp(u, [s[0] for s in stops], [s[1][j] for s in stops])) for j in range(3)]
        hd.line([(0, y), (hw, y)], fill=tuple(c) + (255,))
    mask = Image.new('L', (hw, hh), 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, hw - 1, hh - 1], 22 * k, fill=255)
    head.putalpha(mask)
    # 两端敲击面略暗
    ends = Image.new('RGBA', (hw, hh), (0, 0, 0, 0)); ed = ImageDraw.Draw(ends)
    ed.rectangle([0, 0, 26 * k, hh], fill=(60, 40, 10, 90)); ed.rectangle([hw - 26 * k, 0, hw, hh], fill=(60, 40, 10, 90))
    ends.putalpha(Image.fromarray(np.minimum(np.asarray(ends)[..., 3], np.asarray(mask))))
    head = Image.alpha_composite(head, ends)
    # 刻字
    hd = ImageDraw.Draw(head); f = get_font('serif_black', 30 * k)
    for row, txt in enumerate(['好公司 · 好价格 · 护城河', '现金流 · 回购']):
        y = int(hh * (0.36 + 0.34 * row))
        hd.text((hw // 2 + 2, y + 2), txt, font=f, fill=(255, 236, 190, 160), anchor='mm')
        hd.text((hw // 2, y), txt, font=f, fill=(70, 46, 12, 255), anchor='mm')
    im.alpha_composite(head, (cx - hw // 2, hy0))
    a = np.asarray(im).astype(np.float32) / 255
    a = cv2.resize(a, (Wd // k, Hd // k), interpolation=cv2.INTER_AREA)
    rgb = np.where(a[..., 3:] > 1e-3, a[..., :3], 0)
    return rgb, a[..., 3], (Wd // k / 2, Hd // k - 1)      # 接触点：锤头底边中点

HAM = None
def hammer_sprite():
    global HAM
    if HAM is None: HAM = _hammer_sprite()
    return HAM

NAIL_X = [250, 540, 830]; GROUND = 1240; NAIL_H0, NAIL_H1 = 170, 62
STRIKES = ['M3', 'M4', 'M5']
NAIL_LAB = ['阿里 · 回购', '宁德时代 · 份额第一', '腾讯 · 壁垒']

def nail_h(i, t):
    c = CUE[STRIKES[i]]
    return NAIL_H0 if t < c else lerp(NAIL_H0, NAIL_H1, eo((t - c) / 0.07))

def hammer_pose(t):
    """返回 (接触点 x, y, 角度°, 缩放)；角度为负 = 向后扬起"""
    A = CUE['m2_words'][-1] + 0.7
    rest = (CX, 900.0, 0.0, 1.0)
    if t < A: return rest
    c = [CUE[k] for k in STRIKES]
    top = lambda i, dy=0: (NAIL_X[i] + 40, GROUND - NAIL_H0 - 300 + dy, -32.0, 0.82)
    hitp = lambda i: (NAIL_X[i], GROUND - NAIL_H0, 0.0, 0.82)
    kf = [(A, rest), (c[0] - 1.1, rest), (c[0] - 0.35, top(0))]
    for i in range(3):
        kf += [(c[i] - 0.2, top(i, -20))]
        if t >= c[i] - 0.2 and t < c[i]:                       # 猛砸：加速落下
            u = ei((t - c[i] + 0.2) / 0.2); p0, p1 = top(i, -20), hitp(i)
            return tuple(lerp(p0[j], p1[j], u) for j in range(4))
        rec = (NAIL_X[i] + 10, GROUND - NAIL_H1 - 70, -8.0, 0.82)
        kf += [(c[i], (NAIL_X[i], GROUND - NAIL_H1, 0.0, 0.82)), (c[i] + 0.3, rec)]
        if i < 2: kf += [(c[i + 1] - 0.55, top(i + 1))]
    kf += [(c[2] + 1.2, (CX, 860.0, -6.0, 0.9)), (S['ask'] + 0.5, (CX, 860.0, 0.0, 0.9))]
    if t <= c[0] + 0.0 and t >= c[0] - 0.2: pass
    return keys(t, kf)

def draw_hammer(fr, t, a=1.0):
    rgb, al, (px, py) = hammer_sprite()
    x, y, ang, sc = hammer_pose(t)
    M_ = cv2.getRotationMatrix2D((px, py), -ang, sc)
    M_[0, 2] += x - px; M_[1, 2] += y - py
    pm = cv2.warpAffine(rgb * al[..., None], M_, (W, H), flags=cv2.INTER_LINEAR)
    aa = cv2.warpAffine(al, M_, (W, H), flags=cv2.INTER_LINEAR) * a
    ys, xs = np.where(aa > 0.004)
    if len(ys) == 0: return
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    A_ = aa[y0:y1, x0:x1]; P = pm[y0:y1, x0:x1] * a
    rgbc = np.where(A_[..., None] > 1e-3, P / np.maximum(A_[..., None], 1e-3), 0)
    fr.sprites.append((rgbc, A_, x0, y0))
    fr.B[y0:y1, x0:x1] += (A_ * 0.18)[..., None] * np.array(GOLD, np.float32)

def sparks(fr, t, c, x, y, n=110, seed=0, big=1.0):
    u = t - c
    if u < 0 or u > 1.2: return
    r = np.random.default_rng(seed)
    ang = -math.pi / 2 + (r.random(n) - 0.5) * 2.4
    sp = (300 + r.random(n) * 900) * big
    xs = x + np.cos(ang) * sp * u
    ys = y + np.sin(ang) * sp * u + 0.5 * 2200 * u * u
    life = np.clip(1 - u / (0.5 + r.random(n) * 0.7), 0, 1)
    cols = np.stack([np.ones(n), 0.65 + 0.3 * r.random(n), 0.25 + 0.3 * r.random(n)], 1)
    fr.dots(xs, ys, cols, life * 0.9, 1, 'E')
    # 冲击波：贴地的扁椭圆
    rx = 30 + 330 * eo(u / 0.6) * big
    th = np.linspace(0, 2 * math.pi, 80)
    fr.poly(np.stack([x + rx * np.cos(th), GROUND + rx * 0.16 * np.sin(th)], 1), GOLD2, (1 - eo(u / 0.6)) * 0.8, 2, closed=True)
    fr.glow((x, y), 50 * big, WHITE, max(0, 1 - u / 0.25) * 0.9)

def draw_nail(fr, i, t, a, mark=None):
    x = NAIL_X[i]; h = nail_h(i, t); top = GROUND - h
    fr.fillpoly([(x - 8, GROUND), (x - 8, top + 10), (x + 8, top + 10), (x + 8, GROUND)], C(150, 156, 172), a, 'L')
    fr.line((x - 3, GROUND), (x - 3, top + 12), C(230, 235, 245), a * 0.7, 2)
    fr.rrect_fill(x - 38, top - 4, x + 38, top + 12, 6, C(190, 196, 210), a, 'L')
    fr.line((x - 34, top - 2), (x + 34, top - 2), WHITE, a * 0.8, 2)
    c = CUE[STRIKES[i]]
    if t > c:   # 地面裂纹
        r = np.random.default_rng(i + 30); u = eo((t - c) / 0.25)
        for k in range(4):
            sgn = -1 if k % 2 else 1; pts = [(x, GROUND)]
            for j in range(4):
                px_, py_ = pts[-1]; pts.append((px_ + sgn * (14 + r.random() * 26) * u, py_ + (r.random() - 0.3) * 10 * u))
            fr.poly(pts, GOLD, a * 0.55, 2)
    return top

def scene_hammer(fr, t):
    t0 = S['hammer']; tend = S['two'] + 0.4
    a = env(t, t0 - 0.2, tend, 0.5, 0.45)
    if a <= 0: return
    # M1：芒格的话
    am = a * env(t, t0, L0('M2') + 0.2, 0.4, 0.5)
    if am > 0:
        fr.text('“', 170, 520, 160, 'serif_black', GOLD, am * 0.6, mode='L', glow=0.2)
        btext(fr, t, '手里拿着锤子的人', CX, 660, 80, 'serif_black', WHITE, am, t0 + 0.2, glow=0.1)
        btext(fr, t, '看什么都像钉子', CX, 790, 80, 'serif_black', GOLD, am, CH('M1', 1), glow=0.35, grad=GOLDG)
        fr.text('— 查理 · 芒格', CX + 200, 910, 36, 'serif_med', C(210, 200, 180), am, t0=CH('M1', 1) + 0.6)
    # M2：五个公式词飞入，拼成锤头
    tm2 = L0('M2'); A = CUE['m2_words'][-1] + 0.7
    aw = a * env(t, tm2, S['ask'], 0.4, 0.4)
    if aw > 0 and t < A + 0.6:
        btext(fr, t, '你也有一把锤子', CX, 470, 64, 'serif_black', WHITE, aw * (1 - eio((t - A) / 0.6)), tm2)
    words = ['好公司', '好价格', '护城河', '现金流', '回购']
    starts = [(250, 640), (820, 700), (300, 1080), (790, 1140), (540, 1290)]
    ends = [(395, 891), (540, 891), (685, 891), (480, 942), (600, 942)]
    for k, (wd, tw) in enumerate(zip(words, CUE['m2_words'])):
        if t < tw - 0.1 or t > A + 0.25: continue
        ap = eo((t - tw + 0.1) / 0.3)
        fly = eio((t - A + 0.6) / 0.6)
        x = lerp(starts[k][0], ends[k][0], fly); y = lerp(starts[k][1], ends[k][1], fly)
        sc = 1 - 0.45 * fly
        w2 = text_width(wd, 'serif_black', int(56 * sc)) / 2 + 30 * sc
        al = aw * ap * (1 - eio((t - A) / 0.25))
        fr.rrect(x - w2, y - 42 * sc, x + w2, y + 42 * sc, 40 * sc, GOLD, al, 3)
        fr.rrect_fill(x - w2, y - 42 * sc, x + w2, y + 42 * sc, 40 * sc, GOLD, al * 0.12)
        fr.text(wd, x, y, int(56 * sc), 'serif_black', GOLD, al, mode='L', glow=0.3)
        if t - tw < 0.4: fr.glow((x, y), 70, GOLD, (1 - (t - tw) / 0.4) * 0.5 * aw)
    # 锤子现身
    ah = a * eo((t - A + 0.15) / 0.35)
    shatter = CUE['m6_hit']
    if ah > 0 and t < shatter:
        if t < A + 0.5:
            fr.glow((CX, 860), 200, GOLD2, (1 - eo((t - A + 0.15) / 0.65)) * 0.8 * a)
        draw_hammer(fr, t, ah)
    # 地面与钉子
    ag = a * eo((t - L0('M3') + 0.6) / 0.5)
    if ag > 0:
        fr.line((90, GROUND), (990, GROUND), C(150, 160, 190), ag * 0.6, 2)
        fr.fillpoly([(90, GROUND), (990, GROUND), (990, GROUND + 30), (90, GROUND + 30)], C(40, 34, 30), ag * 0.8, 'L')
        for i in range(3):
            li = L0(STRIKES[i])
            ai = ag * eo((t - li + 0.3) / 0.4)
            if ai <= 0: continue
            top = draw_nail(fr, i, t, ai)
            lab = NAIL_LAB[i]; wl = text_width(lab, 'sans_black', 30) / 2 + 22
            fr.rrect(NAIL_X[i] - wl, GROUND + 64, NAIL_X[i] + wl, GROUND + 116, 26, C(200, 205, 225), ai * 0.8, 2)
            fr.text(lab, NAIL_X[i], GROUND + 90, 30, 'sans_black', WHITE, ai)
            c = CUE[STRIKES[i]]
            sparks(fr, t, c, NAIL_X[i], GROUND - NAIL_H0, seed=i, big=0.9 + 0.12 * i)
            # 「每一锤，都像价值投资」：✓ → 「可你从没问过」：?
            tq = CUE['m6_ask']
            if t > L0('M6') + 0.2:
                y = top - 90
                if t < tq:
                    check(fr, NAIL_X[i], y, 54, (t - L0('M6') - 0.2 - i * 0.18) / 0.3, GOLD, ai, 6)
                else:
                    u = eo((t - tq - i * 0.15) / 0.3)
                    fr.text('?', NAIL_X[i], y, int(90 * (0.6 + 0.4 * u)), 'serif_black', RED2, ai * u, mode='L', glow=0.5)
    # 「这门生意，我真的看懂了吗？」
    tq = CUE['m6_ask']
    aq = a * env(t, tq, S['two'] + 0.2, 0.3, 0.5)
    if aq > 0:
        btext(fr, t, '这门生意', CX, 460, 76, 'serif_black', WHITE, aq, tq + 0.5, glow=0.1)
        btext(fr, t, '我真的看懂了吗？', CX, 580, 92, 'serif_black', WHITE, aq, shatter - 0.35, glow=0.35, dur=0.45)
    shatter_fx(fr, t, a)

# 锤子碎裂 → 粒子重聚成「能力圈」
PART = None
def hammer_particles():
    global PART
    if PART is None:
        rgb, al, (px, py) = hammer_sprite()
        ys, xs = np.where(al > 0.6)
        r = np.random.default_rng(3); idx = r.choice(len(ys), 2200, replace=False)
        PART = dict(x=xs[idx] - px, y=ys[idx] - py, col=np.clip(rgb[ys[idx], xs[idx]] * 1.3, 0, 1),
                    vx=r.normal(0, 1, 2200), vy=r.normal(-0.4, 1, 2200), ring=r.random(2200) * 2 * math.pi,
                    rr=r.normal(0, 1, 2200))
    return PART

RING_C, RING_R = (CX, 800), 250
def shatter_fx(fr, t, a):
    ts = CUE['m6_hit']; tr0 = L0('M7'); tr1 = CUE['m7_two']
    if t < ts or t > S['tx'] + 0.4: return
    P = hammer_particles()
    x0, y0, ang, sc = hammer_pose(ts)
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(-ang))
    bx = x0 + (P['x'] * ca - P['y'] * sa) * sc; by = y0 + (P['x'] * sa + P['y'] * ca) * sc
    u = t - ts
    drift = 1 - np.exp(-u * 1.6)
    ex = bx + P['vx'] * 260 * drift; ey = by + P['vy'] * 260 * drift
    if t > tr0:   # 重聚成环
        g = eio((t - tr0) / max(tr1 - tr0, 0.5))
        rx = RING_C[0] + (RING_R + P['rr'] * 6) * np.cos(P['ring']); ry = RING_C[1] + (RING_R + P['rr'] * 6) * np.sin(P['ring'])
        ex = lerp(ex, rx, g); ey = lerp(ey, ry, g)
        col = P['col'] * (1 - g)[..., None] if np.ndim(g) else P['col'] * (1 - g) + np.array(GOLD2) * g
    else:
        col = P['col']
    al = a * (0.9 if t < tr1 else max(0, 1 - (t - tr1) / 0.6))
    fr.splat(ex, ey, col, al * 0.9, 'E'); fr.splat(ex, ey, col, al * 0.4, 'B')
    if u < 0.3: fr.glow((x0, y0 - 60), 160, GOLD2, (1 - u / 0.3) * a)

def scene_two(fr, t):
    t0 = S['two']; a = env(t, t0 - 0.1, S['tx'] + 0.1, 0.3, 0.45)
    if a <= 0: return
    btext(fr, t, '芒格反复讲的，从来不是公式', CX, 420, 50, 'serif_med', C(215, 215, 225), a, t0 + 0.1)
    tc = CUE['m7_two']
    if t > tc - 0.1:
        u = eo((t - tc + 0.1) / 0.6)
        fr.arc(RING_C, RING_R, -math.pi / 2, -math.pi / 2 + 2 * math.pi * u, GOLD, a, 4, 160)
        fr.glow(RING_C, RING_R * 0.9, GOLD, a * 0.08 * u)
        btext(fr, t, '能力圈', RING_C[0], RING_C[1], 104, 'serif_black', GOLD, a, tc, glow=0.4, grad=GOLDG)
        fr.text('CIRCLE OF COMPETENCE', RING_C[0], RING_C[1] + 90, 24, 'corm_b', GOLD, a * u * 0.8, track=0.25)
        mirror_text(fr, t, '反过来想', 1190, 104, a, WHITE, tc + 0.9)

# ================================================================ 第三幕：拔钉子
def scene_tx(fr, t):
    t0 = S['tx']; a = env(t, t0 - 0.1, S['ali'] + 0.05, 0.4, 0.4)
    if a <= 0: return
    nail_header(fr, t, '01', '腾讯 · 壁垒还在', '为什么利润翻了两番，股价却原地踏步？', a, t0)
    k2, kpe, kp = L0('K2'), CUE['k2_pe'], CUE['k3_punch']
    yr = '2018' if t < k2 else '2026'
    ay = a * eo((t - t0 - 0.6) / 0.4)
    fr.text(yr, CX, 520, 56, 'num', GOLD if t >= k2 else C(200, 205, 220), ay, mode='L', glow=0.2)
    base, hmax = 1230, 500
    cols = [(250, '股价'), (540, '利润'), (830, '市盈率')]
    # 公式就写在柱子正上方
    ae = a * eo((t - t0 - 0.3) / 0.5) * (1 - 0.7 * eio((t - kp) / 0.4))
    for (x, lab) in cols: fr.text(lab, x, 610, 50, 'serif_black', WHITE, ae)
    fr.text('=', 395, 610, 50, 'sans_med', DIM, ae); fr.text('×', 685, 610, 50, 'sans_med', DIM, ae)
    price = 400 if t < kpe + 1.7 else counter(t, kpe + 1.7, kpe + 2.5, 400, 373)
    prof = 651 if t < k2 + 0.1 else counter(t, k2 + 0.1, k2 + 1.3, 651, 2596)
    pe = 47 if t < kpe else counter(t, kpe, kpe + 1.6, 47, 12)
    vals = [(price, price / 500 * hmax, f'{price:.0f} 港元', C(200, 205, 220)),
            (prof, prof / 2596 * hmax, f'{prof:.0f} 亿', GOLD), (pe, pe / 47 * hmax, f'{pe:.0f}×', RED2 if t > kpe else C(150, 180, 240))]
    dim = 1 - 0.65 * eio((t - kp) / 0.4)
    for k, ((x, lab), (v, h, txt, col)) in enumerate(zip(cols, vals)):
        ak = a * eo((t - t0 - 0.6 - k * 0.15) / 0.4) * dim
        hh = h * eo((t - t0 - 0.6 - k * 0.15) / 0.6)
        fr.rrect_fill(x - 75, base - hh, x + 75, base, 10, col, ak * 0.55)
        fr.rrect(x - 75, base - hh, x + 75, base, 10, col, ak * 0.9, 2)
        fr.glow((x, base - hh), 40, col, ak * 0.3)
        fr.text(txt, x, base - hh - 36, 42, 'num', col, ak, mode='L', glow=0.25)
    fr.line((120, base), (960, base), DIM, a * 0.6 * dim, 2)
    # 原因：反垄断、人口红利见顶 —— 砸向市盈率
    for k, (lab, ts) in enumerate([('反垄断', CUE['k1_why'] + 0.5), ('人口红利见顶', CUE['k1_why'] + 1.6)]):
        if t < ts: continue
        u = eo((t - ts) / 0.35); x = lerp(1100, 830, u); y = 1310 + k * 70
        w2 = text_width(lab, 'sans_black', 30) / 2 + 22
        ak = a * u * dim
        fr.rrect(x - w2, y - 26, x + w2, y + 26, 24, RED2, ak, 2)
        fr.text(lab, x, y, 30, 'sans_black', RED2, ak)
    for k, (lab, x, ts, col) in enumerate([('×4', 540, k2 + 1.3, GOLD), ('÷4', 830, kpe + 1.6, RED2), ('≈ 原地', 250, kpe + 2.5, C(200, 205, 220))]):
        if t > ts:
            u = eo((t - ts) / 0.3)
            fr.text(lab, x, 1300, int(56 * (1.3 - 0.3 * u)), 'num' if lab[0] != '≈' else 'sans_black', col, a * u * dim, mode='L', glow=0.35)
    if t > kp - 0.2:
        ap = a * eo((t - kp + 0.2) / 0.4)
        fr.rrect_fill(110, 700, 970, 1060, 30, C(6, 6, 10), ap * 0.75, 'L')
        btext(fr, t, '你买的不是公司', CX, 790, 76, 'serif_black', WHITE, ap, kp - 0.2, glow=0.1)
        btext(fr, t, '是当年的估值', CX, 940, 120, 'serif_black', GOLD, ap, kp + 0.25, glow=0.45, grad=GOLDG)
    fr.text('利润：非 IFRS 归母净利润，2017 年 651 亿 → 2025 年 2596 亿元；市盈率按当时股价估算', CX, 1440, 22, 'sans_light',
            C(170, 170, 185), a * 0.8 * eo((t - k2) / 0.5))

def scene_ali(fr, t):
    t0 = S['ali']; a = env(t, t0 - 0.1, S['zp'] + 0.05, 0.4, 0.4)
    if a <= 0: return
    nail_header(fr, t, '02', '阿里 · 大额回购', '护城河是真的，可你反过来想过吗？', a, t0)
    cx, cy, R = CX, 900, 250
    tin, triv, tbb = CUE['k4_inv'], CUE['k4_rivals'], CUE['k4_buyback']
    # 反过来想：护城河上下翻转一次
    flip = abs(math.cos(math.pi * eio((t - tin) / 0.8))) if t > tin else 1.0
    gaps = []
    if t > triv + 0.5:
        g = eo((t - triv - 0.5) / 0.6) * 0.28
        gaps = [(math.radians(135) - g, math.radians(135) + g), (math.radians(45) - g, math.radians(45) + g)]
    th = np.linspace(0, 2 * math.pi, 240)
    keep = np.ones_like(th, bool)
    for g0, g1 in gaps: keep &= ~((th > g0) & (th < g1))
    for rr_, w_ in ((R, 4), (R + 18, 2)):
        xs = cx + rr_ * np.cos(th); ys = cy + rr_ * np.sin(th) * flip
        seg = []
        for k in range(len(th)):
            if keep[k]: seg.append((xs[k], ys[k]))
            elif len(seg) > 1: fr.poly(seg, GOLD, a, w_); seg = []
            else: seg = []
        if len(seg) > 1: fr.poly(seg, GOLD, a, w_)
    fr.text('护城河', cx + R * 0.82 + 40, cy - R * 0.62 * flip - 30, 34, 'sans_black', GOLD, a)
    fr.circle((cx, cy), 105, GOLD, a * 0.9, 3); fr.glow((cx, cy), 80, GOLD, a * 0.25)
    fr.text('阿里', cx, cy, 64, 'serif_black', GOLD, a, mode='L', glow=0.3)
    # 买家：在环内绕行；对手出现后从缺口流走
    r = np.random.default_rng(5); n = 140
    ph0 = r.random(n) * 2 * math.pi; rad = 130 + r.random(n) * 100; sp = 0.25 + r.random(n) * 0.3
    ang = ph0 + t * sp
    xs = cx + rad * np.cos(ang); ys = cy + rad * np.sin(ang) * flip
    if t > triv + 0.5:
        side = np.where(r.random(n) < 0.5, 0, 1); leave = r.random(n) < 0.6
        ts_ = triv + 0.6 + r.random(n) * 4.0; u = np.clip((t - ts_) / 1.4, 0, 1) * leave
        tx_ = np.where(side == 0, 150, 930); ty_ = 1350
        xs = lerp(xs, tx_, veio(u)); ys = lerp(ys, ty_, veio(u))
    fr.dots(xs, ys, C(170, 200, 255), a * 1.0, 1.5, 'E'); fr.splat(xs, ys, C(170, 200, 255), a * 0.6, 'B')
    if t > tin:
        btext(fr, t, '什么，能摧毁它？', CX, 530, 70, 'serif_black', RED2, a, tin + 0.4, glow=0.35)
    for k, (lab, sx, ang_) in enumerate([('拼多多', 150, 135), ('抖音', 930, 45)]):
        ts = triv + k * 0.45
        if t < ts: continue
        u = eo((t - ts) / 0.5)
        ex = cx + (R + 10) * math.cos(math.radians(ang_)); ey = cy + (R + 10) * math.sin(math.radians(ang_))
        x1 = lerp(sx, ex, u); y1 = lerp(1350, ey, u)
        fr.line((sx, 1350), (x1, y1), RED2, a, 5); fr.glow((x1, y1), 30, RED, a * 0.7)
        d = math.atan2(y1 - 1350, x1 - sx)
        fr.fillpoly([(x1, y1), (x1 - 30 * math.cos(d - 0.4), y1 - 30 * math.sin(d - 0.4)), (x1 - 30 * math.cos(d + 0.4), y1 - 30 * math.sin(d + 0.4))], RED2, a, 'E')
        fr.text(lab, sx, 1400, 44, 'serif_black', RED2, a * u, mode='L', glow=0.3)
    if t > tbb:
        ab = a * eo((t - tbb) / 0.4)
        fr.rrect(cx - 80, cy - 190, cx + 80, cy - 140, 24, GOLD, ab, 2)
        fr.text('回购', cx, cy - 165, 30, 'sans_black', GOLD, ab)
        fr.text('托不住生意的流失', CX, 1270, 46, 'serif_black', WHITE, ab, t0=tbb + 0.4)

def scene_zp(fr, t):
    t0 = S['zp']; a = env(t, t0 - 0.1, S['nv'] + 0.05, 0.4, 0.4)
    if a <= 0: return
    nail_header(fr, t, '03', '智谱 · 跌了一半', '离最高价远了，离价值近了吗？', a, t0)
    ax, xr = 170, 930
    py = lambda v: 1220 - v / 3200 * 640
    av = a * eo((t - t0 - 0.4) / 0.5)
    fr.line((ax, py(0)), (ax, py(3200)), DIM, av * 0.6, 2)
    for v in (0, 1000, 2000, 3000):
        fr.text(str(v), ax - 14, py(v), 22, 'mono', DIM, av * 0.7, anchor='r')
    tm, tf, tq = CUE['k5_mos'], CUE['k5_future'], CUE['k5_q']
    dashed(fr, (ax, py(2980)), (xr, py(2980)), C(210, 210, 225), av * (1 - 0.6 * eio((t - tm) / 0.6)), 2)
    fr.text('最高价 2980', ax + 20, py(2980) - 30, 30, 'sans_med', C(210, 210, 225), av * (1 - 0.6 * eio((t - tm) / 0.6)), anchor='l')
    fr.line((ax, py(1500)), (xr, py(1500)), GOLD, av, 3)
    fr.text('你的买点 1500', ax + 20, py(1500) - 30, 32, 'sans_black', GOLD, av, anchor='l')
    xb = 420; ub = eo((t - t0 - 1.0) / 0.6)
    if ub > 0:
        fr.line((xb, py(2980)), (xb, lerp(py(2980), py(1500), ub)), DIM, a, 3)
        fr.text('离最高价远了', xb + 24, (py(2980) + py(1500)) / 2, 32, 'sans_med', C(200, 205, 220), a * ub, anchor='l')
        if t > tm:
            cross(fr, xb, (py(2980) + py(1500)) / 2, 30, (t - tm) / 0.5, RED, a, 6)
            fr.text('≠ 安全边际', xb + 24, (py(2980) + py(1500)) / 2 + 46, 32, 'sans_black', RED2, a * eo((t - tm - 0.4) / 0.4), anchor='l')
    # 内在价值：先是一条金线，然后在「三年后的格局」里散成一片
    if t > tm + 0.8:
        u = eo((t - tm - 0.8) / 0.6); v0 = 600
        spread = eio((t - tf) / 1.6) if t > tf else 0
        r = np.random.default_rng(2)
        targets = r.uniform(60, 2700, 26)
        for k in range(26):
            v = lerp(v0, targets[k], spread) + spread * 90 * math.sin(t * (1.3 + k * 0.17) + k)
            al = a * u * (1 if k == 0 else spread) * (0.9 if k == 0 else 0.28)
            fr.line((ax + 10, py(v)), (ax + 10 + (xr - ax) * u, py(v)), GOLD, al, 3 if k == 0 and spread < 0.3 else 1)
        if spread < 0.5:
            fr.text('内在价值？', xr - 10, py(v0) + 36, 32, 'sans_black', GOLD, a * u * (1 - 2 * spread), anchor='r')
            xb2 = 820
            fr.line((xb2, py(1500)), (xb2, py(v0)), GOLD, a * u * (1 - 2 * spread), 3)
            fr.text('安全边际量这段', xb2 - 20, (py(1500) + py(v0)) / 2, 30, 'sans_black', GOLD, a * u * (1 - 2 * spread), anchor='r')
        if spread > 0.2:
            fr.text('三年后的格局？', xr - 10, py(2900), 34, 'sans_black', C(200, 205, 220), a * spread, anchor='r')
    if t > tq:
        btext(fr, t, '内在价值 = ?', CX, 1350, 96, 'serif_black', WHITE, a, tq, glow=0.4, dur=0.45)

def scene_nv(fr, t):
    t0 = S['nv']; a = env(t, t0 - 0.1, S['cure'] + 0.05, 0.4, 0.45)
    if a <= 0: return
    nail_header(fr, t, '04', '英伟达 · 13 倍市盈率', '便宜，是因为利润在山顶吗？', a, t0)
    tp, t26 = CUE['k6_peak'], CUE['k6_26']
    af = a * eo((t - t0 - 0.5) / 0.5)
    fr.text('PE', 320, 540, 64, 'num', WHITE, af, mode='L', glow=0.2)
    fr.text('=', 400, 540, 56, 'sans_med', DIM, af)
    fr.text('价格', 590, 500, 44, 'serif_black', WHITE, af)
    fr.line((480, 540), (700, 540), WHITE, af, 3)
    shrink = eio((t - tp - 0.6) / 2.0)
    fr.text('利润', 590, 585, int(44 * (1 - 0.35 * shrink)), 'serif_black', GOLD if shrink < 0.5 else RED2, af)
    vals = [.36, .42, .5, .58, .67, .76, .86, .95, 1.0, .9, .78, .66, .56, .5]
    nb = len(vals); x0, x1, yb, hmax = 140, 940, 1270, 260
    bw = (x1 - x0) / nb
    for k, v in enumerate(vals):
        ts = t0 + 0.8 + k * 0.1 if k <= 8 else tp + 0.4 + (k - 9) * 0.38
        u = eo((t - ts) / 0.35)
        if u <= 0: continue
        col = GOLD if k == 8 else (RED2 if k > 8 else C(110, 140, 200))
        h = v * hmax * u; xa = x0 + k * bw + 6
        fr.rrect_fill(xa, yb - h, xa + bw - 12, yb, 4, col, a * (0.55 if k != 8 else 0.85))
        if k == 8: fr.glow((xa + bw / 2 - 6, yb - h), 30, GOLD, a * 0.4 * u)
    fr.line((x0, yb), (x1, yb), DIM, a * 0.6, 2)
    fr.text('利润（周期）', x0, yb + 40, 28, 'sans_med', DIM, a * eo((t - t0 - 0.8) / 0.4), anchor='l')
    xk = x0 + 8 * bw + bw / 2
    ap = a * eo((t - t0 - 2.0) / 0.4)
    fr.text('创纪录的利润', xk, yb - hmax - 44, 32, 'sans_black', GOLD, ap, mode='L', glow=0.2)
    if t > tp: fr.text('如果这是山顶？', xk, yb - hmax - 90, 30, 'sans_med', RED2, a * eo((t - tp) / 0.4))
    tr = t0 + 1.0
    ar = a * eo((t - tr) / 0.4)
    pe = counter(t, tp + 0.6, t26, 13, 26) if t > tp + 0.6 else 13
    col = lerpc(GOLD, RED2, cl((pe - 13) / 6))
    fr.text(f'{pe:.0f}×', CX, 735, int(150 + 30 * impact(t) * (pe > 25)), 'num', col, ar, mode='L', glow=0.5)
    fr.text('价格不变，利润腰斩' if pe > 14 else '看着很便宜', CX, 840, 36, 'sans_med', C(210, 210, 220), ar)
    fr.text('注：不是断言谁已见顶，而是先问一句——这份利润，能持续吗？', CX, 1420, 28, 'sans_light', C(190, 190, 200),
            a * eo((t - t26 - 0.3) / 0.6))

# ================================================================ 第四幕：解药
def mirror_text(fr, t, s, y, size, a, col, t0):
    if t < t0: return
    m = line_mask(s, 'serif_black', size)
    blit_mask(fr, m, CX, y, col, a * eo((t - t0) / 0.5), 'L', 0.25)
    u = eo((t - t0 - 0.55) / 0.9)
    if u <= 0: return
    r = m[::-1].copy(); h = r.shape[0]
    fade = np.linspace(0.75, 0.0, h)[:, None] ** 1.3
    rows = np.arange(h); shift = (np.sin(rows * 0.18 - t * 5) * 4 * (rows / h)).astype(np.int32)
    rw = np.zeros_like(r)
    for k in range(h): rw[k] = np.roll(r[k], shift[k])
    blit_mask(fr, rw * fade, CX, y + h * 0.82, GOLD, a * u, 'L', 0.35)

def scene_cure(fr, t):
    t0 = S['cure']
    a = env(t, t0 - 0.2, S['report'] - 0.1, 0.4, 0.45)
    if a > 0:
        fr.text('芒格说', CX, 640, 46, 'serif_med', GOLD, a, t0=t0)
        mirror_text(fr, t, '反过来想', 840, 150, a, WHITE, t0 + 0.4)
        ti = P('V1', 0)
        btext(fr, t, '总是反过来想', CX, 1180, 62, 'serif_med', WHITE, a, ti)
        fr.text('INVERT, ALWAYS INVERT.', CX, 1270, 36, 'corm_b', GOLD, a * 0.9, track=0.2, t0=ti + 0.5, stag=0.01)
    t26 = S['report']; a = env(t, t26 - 0.2, S['ring'] - 0.1, 0.45, 0.45)
    if a > 0:
        yo = (1 - eo((t - t26 + 0.2) / 0.6)) * 80
        x0, y0, x1, y1 = 140, 470 + yo, 940, 1370 + yo
        fr.rrect_fill(x0, y0, x1, y1, 18, C(30, 28, 24), a * 0.9, 'L')
        fr.rrect(x0, y0, x1, y1, 18, GOLD, a * 0.6, 2)
        fr.text('SHORT REPORT', CX, y0 + 70, 26, 'mono', GOLD, a * 0.8, track=0.4)
        fr.text('给自己的做空报告', CX, y0 + 150, 66, 'serif_black', PAPER, a)
        c2, c3 = CUE['v2_q'], CUE['v2_no']
        fr.text('如果三年后再跌 50%，原因是？', CX, y0 + 250, 40, 'sans_med', C(220, 200, 170), a * eo((t - c2) / 0.4))
        for k in range(3):
            yk = y0 + 380 + k * 150
            ak = a * eo((t - c2 - 0.3 - k * 0.15) / 0.3)
            fr.text('①②③'[k], x0 + 80, yk, 50, 'sans_black', GOLD, ak)
            fr.line((x0 + 130, yk + 30), (x1 - 70, yk + 30), DIM, ak * 0.6, 1)
            if k < 2:
                tw = c2 + 1.0 + k * 0.9; u = eo((t - tw) / 0.8)
                if u > 0:
                    xs = np.linspace(x0 + 150, x0 + 150 + (x1 - x0 - 260) * u, 60)
                    rr = np.random.default_rng(k + 4)
                    ys = yk + 4 + np.sin(xs * 0.09 + k) * 10 * rr.random(60) ** 0.5
                    fr.poly(np.stack([xs, ys], 1), C(240, 220, 170), ak * 0.9, 3)
            elif int(t * 2.5) % 2 == 0 and t > c2 + 1.5:
                fr.line((x0 + 155, yk - 26), (x0 + 155, yk + 26), WHITE, ak, 3)
        stamp(fr, t, '别买', 760, y1 - 160, 120, c3 + 0.55, RED, -12, a)

def scene_ring(fr, t):
    t0 = S['ring']; a = env(t, t0 - 0.2, S['finale'] - 0.1, 0.45, 0.45)
    if a <= 0: return
    cx, cy, R = CX, 820, 290
    u = eo((t - t0) / 1.0)
    fr.arc((cx, cy), R, -math.pi / 2, -math.pi / 2 + 2 * math.pi * u, GOLD, a, 4, 180)
    fr.glow((cx, cy), R * 0.8, GOLD, a * 0.06 * u)
    fr.text('能力圈', cx, cy - R - 46, 44, 'serif_black', GOLD, a * u, mode='L', glow=0.3)
    r = np.random.default_rng(12)
    inside = [(cx + 120 * math.cos(k * 1.26), cy + 110 * math.sin(k * 1.26)) for k in range(5)]
    for k, (x, y) in enumerate(inside):
        ak = a * eo((t - t0 - 0.6 - k * 0.12) / 0.4)
        fr.glow((x, y), 16, GOLD2, ak * 0.9); fr.circle((x, y), 7, GOLD2, ak, -1)
    fr.text('真正看懂的生意', cx, cy + 10, 40, 'sans_black', GOLD2, a * eo((t - t0 - 1.2) / 0.4))
    n = 70; ang = r.random(n) * 2 * math.pi; rad = R + 50 + r.random(n) * 180
    ox = np.clip(cx + rad * np.cos(ang), 70, 1010); oy = np.clip(cy + rad * np.sin(ang) * 1.05, 470, 1180)
    tout = CUE['v3_out']
    st = tout + 0.4 + r.random(n) * 2.2; uu = np.clip((t - st) / 0.9, 0, 1)
    bx, by = 840 + r.normal(0, 40, n), 1300 + r.normal(0, 10, n)
    xs = lerp(ox, bx, veio(uu)); ys = lerp(oy, by, veio(uu)) - np.sin(uu * math.pi) * 140
    fr.dots(xs, ys, C(170, 180, 210), a * eo((t - t0 - 0.8) / 0.5) * 1.0, 1.5, 'L'); fr.splat(xs, ys, C(150, 170, 220), a * 0.5, 'B')
    ab = a * eo((t - tout) / 0.4)
    fr.poly([(700, 1230), (720, 1345), (960, 1345), (980, 1230)], GOLD, ab, 4)
    fr.text('太难', 840, 1395, 48, 'serif_black', GOLD, ab, mode='L', glow=0.25)
    fr.text('TOO HARD', 840, 1440, 22, 'mono', GOLD, ab * 0.8, track=0.25)
    ti = CUE['v3_idx']
    ai = a * eo((t - ti - 0.3) / 0.5)
    fr.rrect(110, 1260, 560, 1350, 45, TEAL, ai, 3); fr.rrect_fill(110, 1260, 560, 1350, 45, TEAL, ai * 0.12)
    fr.text('看不懂 → 指数基金', 335, 1305, 42, 'sans_black', TEAL, ai, mode='L', glow=0.3)

def scene_finale(fr, t):
    t0 = S['finale']; a = env(t, t0 - 0.2, S['outro'] - 0.1, 0.5, 0.45)
    if a <= 0: return
    tc = CUE['e1_turn']
    btext(fr, t, '价值投资', CX, 560, 64, 'serif_med', C(220, 215, 205), a, t0)
    dimv = 1 - 0.55 * eio((t - tc + 0.2) / 0.6)
    btext(fr, t, '从来不是买便宜的股票', CX, 700, 76, 'serif_black', WHITE, a * dimv, t0 + 0.8)
    tw = text_width('从来不是买便宜的股票', 'serif_black', 76)
    if t > tc - 0.4:
        u = eo((t - tc + 0.4) / 0.5)
        fr.line((CX - tw / 2 - 10, 706), (CX - tw / 2 - 10 + (tw + 20) * u, 696), GOLD, a, 5)
    btext(fr, t, '而是', CX, 860, 56, 'serif_med', C(220, 215, 205), a, tc)
    btext(fr, t, '买你真正', CX, 1010, 124, 'serif_black', GOLD, a, tc + 0.4, glow=0.45, grad=GOLDG)
    btext(fr, t, '看懂的生意', CX, 1160, 124, 'serif_black', GOLD, a, tc + 0.9, glow=0.45, grad=GOLDG)
    u = eo((t - tc) / 1.2)
    fr.arc((CX, 1085), 330, math.pi * 1.5 - math.pi * u, math.pi * 1.5 + math.pi * u, GOLD, a * 0.35, 2, 160)
    dust(fr, t, a * 1.5)

def scene_outro(fr, t):
    t0 = S['outro']; a = env(t, t0 - 0.2, S['card'] + 0.3, 0.4, 0.5)
    if a <= 0: return
    btext(fr, t, '你手里那把锤子', CX, 430, 72, 'serif_black', WHITE, a, t0)
    btext(fr, t, '敲过哪几颗钉子？', CX, 540, 72, 'serif_black', GOLD, a, P('E2', 0), glow=0.35, grad=GOLDG)
    traps = ['只看跌了多少，不看估值', '只看护城河，不想谁能摧毁它', '看不懂的生意，也敢下重注', '用巅峰利润，算出低市盈率']
    for k, s in enumerate(traps):
        ak = a * eo((t - t0 - 1.0 - k * 0.35) / 0.35)
        y = 720 + k * 130; x = 170
        fr.fillpoly([(x - 5, y + 26), (x - 5, y - 8), (x + 5, y - 8), (x + 5, y + 26)], C(170, 176, 190), ak, 'L')
        fr.rrect_fill(x - 24, y - 20, x + 24, y - 8, 4, C(200, 205, 215), ak, 'L')
        fr.text(s, 220, y, 48, 'serif_med', WHITE, ak, anchor='l')
    fr.text('评论区，说说你敲过的钉子', CX, 1290, 40, 'sans_med', GOLD, a * eo((t - t0 - 2.6) / 0.5))

LOGO = None
def scene_card(fr, t, out):
    """片尾：大号 logo + 金色「巴芒价值」+ BUFFETT · MUNGER（在 post 阶段直接合成到 out 上）"""
    global LOGO
    t0 = S['card']; a = eo((t - t0 - 0.15) / 0.8)
    if a <= 0: return
    if LOGO is None: LOGO = load_logo(300)
    rgb, al = LOGO
    sc_y = 820 - 30 * (1 - a)
    x0, y0 = int(CX - 150), int(sc_y - 150)
    reg = out[y0:y0 + 300, x0:x0 + 300]
    gl = cv2.GaussianBlur(al, (0, 0), 30)[..., None] * np.array(C(110, 175, 255), np.float32) * 0.35 * a
    reg += gl
    m = (al * a)[..., None]; reg *= (1 - m); reg += m * rgb

def draw_card_text(fr, t):
    t0 = S['card']; a = eo((t - t0 - 0.5) / 0.8)
    if a <= 0: return
    fr.text('巴芒价值', CX, 1090, 132, 'serif_black', GOLD, a, track=0.06, mode='L', glow=0.3, grad=[GOLD2, GOLD, GOLDD, GOLD])
    tw = text_width('巴芒价值', 'serif_black', 132, 0.06)
    s = 'BUFFETT · MUNGER'
    nat = text_width(s, 'corm_b', 44)
    tr = (tw - nat) / (len(s) - 1) / 44
    fr.text(s, CX, 1190, 44, 'corm_b', C(214, 178, 112), a, track=tr)
    fr.text('不构成投资建议 · 股价截至 2026.11.18 收盘（约数），中间走势为示意', CX, 1720, 26, 'sans_light', DIM, a * 0.8)

# ================================================================ 字幕 / HUD / 合成
HIDE = {'H1', 'Q1', 'M1', 'V1', 'E1', 'E2'}
HIDE_CHUNK = {('M6', 1), ('K3', 1), ('K5', 3)}
GOLD_CH = set('0123456789%×≠=÷.')

def post_text(out, s, x, y, size, fnt, a, colf):
    tw = text_width(s, fnt, size)
    cx = x - tw / 2; base = y + size * 0.36
    for i, ch in enumerate(s):
        m, adv, pad, bl = glyph(ch, fnt, size)
        if ch != ' ':
            x0, y0 = int(round(cx - pad)), int(round(base - bl))
            h, w = m.shape
            reg = out[y0:y0 + h, x0:x0 + w]
            mm = (m * a)[..., None]
            reg *= (1 - cv2.GaussianBlur(m, (0, 0), 3)[..., None] * 0.6 * a)
            reg *= (1 - mm); reg += mm * np.array(colf(ch), np.float32)
        cx += adv

def subtitles(out, t):
    for l in TL['lines']:
        if l['id'] in HIDE: continue
        ch = l['chunks']
        for k, (s, a0, a1) in enumerate(ch):
            if (l['id'], k) in HIDE_CHUNK: continue
            a1 = a1 + 0.25 if k == len(ch) - 1 else ch[k + 1][1] - 0.02
            if a0 - 0.08 <= t <= a1:
                a = eo((t - a0 + 0.08) / 0.12) * (1 - eio((t - a1 + 0.1) / 0.1))
                size = 50
                while text_width(s, 'sans_med', size) > 960: size -= 2
                y = 1560
                band = out[y - 70:y + 70]
                band *= (1 - 0.35 * a)
                post_text(out, s, CX, y, size, 'sans_med', a, lambda ch: GOLD2 if ch in GOLD_CH else (0.96, 0.96, 0.97))

CHAPTERS = [(0, '01  好学生的困惑'), (S['title'], '02  铁锤人'), (S['tx'] - 0.5, '03  拔钉子'), (S['cure'] - 0.5, '04  解药')]
def chapter(fr, t):
    lab = [l for t0, l in CHAPTERS if t >= t0][-1]
    a = 0.75 * (1 - eio((t - S['card'] + 0.5) / 0.5)) * eo((t - 0.6) / 0.5)
    fr.text(lab, 52, 92, 26, 'sans_med', C(200, 200, 210), a, anchor='l')

HUD = Hud(scale=1.0, frame_w=W)
CUTS = [S['cases'], L0('A1'), L0('Z1'), L0('N1'), S['pivot'], S['title'], S['hammer'], S['tx'], S['ali'], S['zp'], S['nv'],
        S['cure'], S['report'], S['ring'], S['finale'], S['card']]

def zoom_blur(out, k):
    """转场：径向推镜模糊（多层放大叠加）"""
    acc = out.copy(); wsum = 1.0
    for j in range(1, 5):
        z = 1 + 0.035 * j * k
        M_ = cv2.getRotationMatrix2D((W / 2, H * 0.45), 0, z)
        acc += cv2.warpAffine(out, M_, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT) * (1 - j * 0.15)
        wsum += 1 - j * 0.15
    return acc / wsum

def render(t):
    fr = Frame(t)
    bg = background(t)
    imp = impact(t, 0.85)
    dust(fr, t, 0.6)
    scene_hook(fr, t)
    if S['cases'] - 0.5 < t < S['pivot'] + 0.5: scene_cases(fr, t)
    scene_pivot(fr, t); scene_title(fr, t)
    if S['hammer'] - 0.5 < t < S['tx'] + 0.5: scene_hammer(fr, t); scene_two(fr, t)
    if S['tx'] - 0.5 < t < S['cure'] + 0.5: scene_tx(fr, t); scene_ali(fr, t); scene_zp(fr, t); scene_nv(fr, t)
    if t > S['cure'] - 0.5:
        scene_cure(fr, t); scene_ring(fr, t); scene_finale(fr, t); scene_outro(fr, t); draw_card_text(fr, t)
    chapter(fr, t)
    fr.flash = 0.035 * imp
    fr.ca = 4 * impact(t, 1.3)
    fr.streak = 0.3 + 0.9 * imp
    for key in STRIKES:                     # 锤击震屏
        u = t - CUE[key]
        if 0 <= u < 0.4:
            amp = 16 * math.exp(-u * 11)
            fr.shake = (int(amp * math.sin(u * 90)), int(amp * 0.5 * math.cos(u * 70)))
    out = finish(fr, bg, bloom_k=1.0 + 0.8 * imp, vignette=VIG, grain=GRAIN[int(t * 30) % 6])
    scene_card(fr, t, out)
    kz = max([math.exp(-((t - c) / 0.11) ** 2) for c in CUTS] + [0])
    if kz > 0.03: out = zoom_blur(out, kz)
    z = 1.0 + 0.012 * math.sin(t * 0.4) + 0.025 * impact(t)
    if abs(z - 1) > 1e-4:
        M_ = cv2.getRotationMatrix2D((W / 2, H * 0.45), 0, z)
        out = cv2.warpAffine(out, M_, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    p = t / TOTAL
    out[0:5, :int(W * p)] = out[0:5, :int(W * p)] * 0.3 + np.array(GOLD, np.float32) * 0.7
    subtitles(out, t)
    out = np.clip(out, 0, 1)
    HUD.draw(out, t)
    fade = min(1.0, t / 0.35) * min(1.0, (TOTAL - t) / 0.6)
    out *= fade
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)

if __name__ == '__main__':
    if sys.argv[1] == 'still':
        for k, ts in enumerate(sys.argv[2].split(',')):
            img = render(float(ts))
            p = sys.argv[3].replace('.png', f'_{k:02d}.png') if ',' in sys.argv[2] else sys.argv[3]
            cv2.imwrite(p, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    else:
        f0, f1, outp = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        pr = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                               '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '20',
                               '-pix_fmt', 'yuv420p', outp], stdin=subprocess.PIPE)
        for f in range(f0, f1):
            pr.stdin.write(render(f / FPS).tobytes())
        pr.stdin.close(); pr.wait()
