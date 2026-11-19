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
        (S['cases'] + 1, (C(30, 80, 120), C(3, 7, 12))), (S['ali'], (C(90, 40, 60), C(8, 4, 8))),
        (S['nv'], (C(30, 90, 70), C(3, 8, 7))), (S['pivot'] + 3, (C(60, 30, 30), C(5, 2, 3))),
        (S['title'], (C(140, 100, 40), C(8, 6, 3))), (S['rewind'] + 1, (C(50, 60, 100), C(3, 4, 8))),
        (S['r1'], (C(90, 50, 60), C(6, 3, 5))), (S['r2'], (C(60, 70, 110), C(4, 4, 9))), (S['r3'], (C(40, 100, 80), C(3, 7, 6))),
        (S['r4'], (C(60, 80, 130), C(4, 5, 10))), (S['r5'], (C(120, 80, 30), C(7, 5, 2))), (S['strikes'], (C(150, 70, 30), C(8, 4, 2))),
        (S['clue'], (C(40, 40, 60), C(2, 2, 4))), (S['tx'], (C(60, 80, 130), C(4, 5, 10))), (S['inv'], (C(130, 60, 40), C(7, 3, 3))),
        (S['wake'], (C(40, 40, 60), C(3, 3, 6))), (S['three'], (C(70, 110, 170), C(5, 7, 13))),
        (S['mos'], (C(170, 120, 50), C(9, 7, 4))), (S['quote'], (C(120, 95, 50), C(6, 5, 3))), (S['card'], (C(60, 50, 30), C(3, 3, 3)))]

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

_t, _a, _z, _n = L0('T1'), L0('A1'), L0('Z1'), L0('N1')
# 逐词实测的相对时刻（work/vo 缓存的配音）：见 timeline.py 中数字开口位置的说明
CASES = [
 dict(no='01', name='腾讯控股', sub='0700.HK · 港元 · 截至 2026.11.18', x0=2017.7, x1=2026.95, y0=120, y1=860, buy=(2018.22, 400),
      anchors=[(2017.7, 330), (2018.08, 476), (2018.22, 400), (2018.5, 380), (2018.83, 255), (2019.3, 395), (2019.65, 325),
               (2020.2, 380), (2020.55, 560), (2021.13, 775), (2021.6, 440), (2022.0, 470), (2022.4, 350), (2022.82, 190),
               (2023.08, 400), (2023.7, 310), (2024.1, 270), (2024.8, 410), (2025.3, 500), (2025.8, 650), (2026.05, 630),
               (2026.4, 520), (2026.81, 375), (2026.85, 430), (2026.88, 373)],
      peak=(2018.08, 476, '高点 476'), end=(2026.88, 373, '373'), grid=[200, 400, 600, 800],
      xl=[(2018.0, '2018'), (2022.0, '2022'), (2026.0, '2026')],
      t_in=_t - 0.3, t_out=_a - 0.5, t_buy=_t + 4.7, badge='-7%', cap='8 年 · 股价仍低于买入价（不含分红）', seed=3,
      rev=[(_t + 0.9, 2017.7), (_t + 2.6, 2018.08), (_t + 3.5, 2018.22), (CUE['T1'] - 1.0, 2018.22), (CUE['T1'], 2026.88)]),
 dict(no='02', name='阿里巴巴', sub='BABA · 美元 · 截至 2026.11.18', x0=2020.45, x1=2026.95, y0=20, y1=360, buy=(2021.68, 150),
      anchors=[(2020.45, 250), (2020.82, 319), (2021.0, 222), (2021.15, 260), (2021.45, 210), (2021.6, 168), (2021.68, 150),
               (2021.85, 165), (2022.0, 120), (2022.2, 75), (2022.45, 118), (2022.62, 92), (2022.81, 60), (2023.08, 118),
               (2023.5, 95), (2023.95, 72), (2024.1, 68), (2024.75, 108), (2025.15, 140), (2025.3, 105), (2025.6, 120),
               (2025.78, 185), (2026.0, 147), (2026.4, 125), (2026.7, 115), (2026.84, 107), (2026.88, 84)],
      peak=(2020.82, 319, '高点 319'), end=(2026.88, 84, '84'), grid=[100, 200, 300],
      marks=[(2022.81, 60, '2022 低点 60')],
      xl=[(2021.0, '2021'), (2023.0, '2023'), (2025.0, '2025'), (2026.6, '2026')],
      t_in=_a - 0.25, t_out=_z - 0.5, t_buy=_a + 4.0, badge='-44%', cap='5 年后，仍亏四成多', seed=8,
      rev=[(_a + 1.27, 2020.45), (_a + 2.6, 2020.82), (_a + 4.0, 2021.68), (CUE['A1'] - 1.3, 2021.68), (CUE['A1'], 2026.88)]),
 dict(no='03', name='智谱', sub='2513.HK · 港元 · 截至 2026.11.18', x0=2026.38, x1=2026.92, y0=0, y1=3300, buy=(2026.57, 1500),
      anchors=[(2026.38, 620), (2026.43, 900), (2026.455, 1050), (2026.47, 2980), (2026.49, 2350), (2026.52, 1950),
               (2026.57, 1500), (2026.62, 1280), (2026.69, 980), (2026.77, 720), (2026.83, 442), (2026.86, 408),
               (2026.875, 335), (2026.88, 367)],
      peak=(2026.47, 2980, '高点 2980'), end=(2026.88, 367, '367'), grid=[1000, 2000, 3000],
      xl=[(2026.42, '2026.06'), (2026.86, '2026.11')],
      t_in=_z - 0.25, t_out=_n - 0.5, t_buy=_z + 4.66, badge='-76%', cap='1500 → 367', seed=11,
      rev=[(_z + 1.29, 2026.38), (_z + 2.9, 2026.47), (_z + 4.66, 2026.57), (CUE['Z1'] - 0.9, 2026.57), (CUE['Z1'], 2026.88)]),
 dict(no='04', name='英伟达', sub='NVDA · 美元 · 截至 2026.11.18', x0=2026.45, x1=2026.93, y0=120, y1=260, buy=(2026.85, 180),
      anchors=[(2026.45, 172), (2026.53, 188), (2026.6, 182), (2026.66, 206), (2026.72, 224), (2026.77, 240), (2026.81, 214),
               (2026.835, 196), (2026.85, 180), (2026.86, 186), (2026.87, 162), (2026.875, 155), (2026.88, 151)],
      peak=(2026.77, 240, '高点 ≈240'), end=(2026.88, 151, '151'), grid=[150, 200, 250],
      xl=[(2026.5, '2026.07'), (2026.86, '2026.11')],
      t_in=_n - 0.25, t_out=S['pivot'] - 0.6, t_buy=_n + 6.6, badge='-16%', cap='营收翻倍，股价照跌', seed=21,
      rev=[(_n + 2.78, 2026.45), (_n + 4.49, 2026.77), (_n + 6.57, 2026.85), (CUE['N1'] - 1.0, 2026.85), (CUE['N1'], 2026.88)]),
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

def buy_stamp(fr, t, c, px, py, a, dx=0.0, t0=None, size=64):
    """锤子母题：每一次「买入」都是一记印章"""
    t0 = c['t_buy'] if t0 is None else t0
    if t < t0: return
    bx, bv = c['buy']
    stamp(fr, t, '买入', px(bx) + 70, py(bv) - 92, size, t0, GOLD, -10, a)
    u = t - t0
    if u < 0.5: fr.glow((px(bx), py(bv)), 60, GOLD2, (1 - u / 0.5) * 0.8 * a)

def scene_cases(fr, t):
    for i, c in enumerate(CASES):
        if not (c['t_in'] - 0.1 < t < c['t_out'] + 0.6): continue
        r = case_scene(fr, t, c, i)
        if not r: continue
        px, py, a, dx = r
        buy_stamp(fr, t, c, px, py, a, dx)
        if i == 0:      # 腾讯：「你没有追高，只是提前八年到达了目的地」
            t6 = L0('T3')
            if t > t6:
                p0, p1 = (px(2018.22), py(400)), (px(2026.88), py(373))
                dashed(fr, p0, p1, GOLD, a * 0.9, 2, prog=eo((t - t6) / 1.4))
                if t > CH('T3', 1):
                    au = a * eo((t - CH('T3', 1)) / 0.5); fx, fy = p1[0], p1[1] - 6
                    fr.line((fx, fy), (fx, fy - 70), GOLD, au, 3)
                    fr.fillpoly([(fx, fy - 70), (fx - 46, fy - 58), (fx, fy - 46)], GOLD, au * 0.9, 'E')
                    fr.text('目的地：提前 8 年到达', CX + dx, py(560), 36, 'sans_black', GOLD, au, mode='L', glow=0.2)
            o5 = CUE['T1']
            if o5 - 1.0 < t < o5 + 1.4:
                ay = a * env(t, o5 - 1.0, o5 + 1.4, 0.2, 0.4)
                fr.text(str(int(keys(t, c['rev']))), 900 + dx, 520, 64, 'num', WHITE, ay * 0.85, anchor='r', mode='L', glow=0.2)
        elif i == 1:    # 阿里：还在大笔回购
            tb = c['t_buy'] + 0.4
            if t > tb:
                ab = a * eo((t - tb) / 0.4); x0, y0 = px(2021.68) + 40, py(150) + 120
                fr.rrect(x0, y0 - 30, x0 + 190, y0 + 30, 28, GOLD, ab * 0.9, 2)
                fr.text('大额回购 ✓', x0 + 95, y0, 30, 'sans_med', GOLD, ab)
            o = CUE['A1']
            if o - 1.3 < t < o + 1.2:
                ay = a * env(t, o - 1.3, o + 1.2, 0.2, 0.4)
                fr.text(str(int(keys(t, c['rev']))), 900 + dx, 520, 64, 'num', WHITE, ay * 0.85, anchor='r', mode='L', glow=0.2)
        elif i == 2:    # 智谱：泡沫挤干了？
            tb = L0('Z1') + 6.1 - 1.4
            if t > tb:
                ab = a * eo((t - tb) / 0.4); x0, y0 = px(2026.57) + 30, py(1500) + 110
                fr.rrect(x0, y0 - 30, x0 + 250, y0 + 30, 28, GOLD, ab * 0.9, 2)
                fr.text('泡沫挤干了？', x0 + 125, y0, 30, 'sans_med', GOLD, ab)
        else:           # 英伟达
            n0 = L0('N1')
            for k, (lab, tt) in enumerate([('回调 25%', n0 + 4.5), ('预测 PE ≈13×', n0 + 6.0)]):
                if t > tt:
                    ab = a * eo((t - tt) / 0.35) * (1 - eio((t - CUE['N1'] + 0.4) / 0.4))
                    x0, y0 = 150 + dx, 1270 + k * 86
                    fr.rrect(x0, y0 - 32, x0 + 330, y0 + 32, 30, GOLD, ab * 0.9, 2)
                    fr.text(lab, x0 + 165, y0, 34, 'sans_black', GOLD, ab, mode='L', glow=0.15)
            if t > n0 + 6.0:
                fr.text('分析师对下一财年的盈利预测', 150 + dx + 345, 1356, 24, 'sans_light', C(180, 180, 195), a * eo((t - n0 - 6.2) / 0.4) * (1 - eio((t - CUE['N1'] + 0.4) / 0.4)), anchor='l')
            te = n0 + 7.1
            if t > te:
                ae = a * eo((t - te) / 0.4); x0, y0 = 150 + dx, 640
                fr.rrect(x0, y0 - 34, x0 + 420, y0 + 34, 32, TEAL, ae, 2); fr.rrect_fill(x0, y0 - 34, x0 + 420, y0 + 34, 32, TEAL, ae * 0.1)
                fr.text('Q3 季度营收 同比 +103%', x0 + 210, y0, 30, 'sans_black', TEAL, ae, mode='L', glow=0.2)

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
    stamp(fr, t, '满分', 880, 1250, 84, CUE['q_ok'], RED, -12, a)
    tq = CUE['q_ask']
    btext(fr, t, '为什么结果总是一样？', CX, 1370, 76, 'serif_black', WHITE, a, tq, glow=0.3, dur=0.5)
    if t > tq + 1.4 and int(t * 2.2) % 2 == 0:
        fr.line((CX + 380, 1340), (CX + 380, 1400), WHITE, a, 3)

def scene_title(fr, t):
    t0 = S['title']; a = env(t, t0, S['rewind'] + 0.2, 0.05, 0.5)
    if a <= 0: return
    u = t - t0
    for k, (spd, col) in enumerate([(1500, GOLD), (900, RED)]):
        r = spd * eo(u / 1.2) + 10; aw = (1 - eo(u / 1.2)) * a
        fr.circle((CX, 900), r, col, aw * 0.6, 3); fr.glow((CX, 900), 60 + r * 0.1, col, aw * 0.15)
    rr = np.random.default_rng(42); n = 260
    ang = rr.random(n) * 6.283; spd = 150 + rr.random(n) * 900
    d = spd * (1 - np.exp(-u * 2.2)) / 2.2
    fr.dots(CX + np.cos(ang) * d, 900 + np.sin(ang) * d * 0.8 + u * u * 20, GOLD2, np.exp(-u * 0.9) * 0.8 * a, 1, 'E')
    sc = 1 + 0.08 * (1 - eo(u / 0.5))
    tw = text_width('伪价值投资', 'serif_black', int(176 * sc)); x = CX - tw / 2
    fr.text('伪', x, 900, int(176 * sc), 'serif_black', RED2, a, anchor='l', mode='L', glow=0.6)
    x2 = x + glyph('伪', 'serif_black', int(176 * sc))[1]
    fr.text('价值投资', x2, 900, int(176 * sc), 'serif_black', GOLD, a, anchor='l', mode='L', glow=0.45, grad=[GOLD2, GOLD, GOLDD, GOLD])
    sw = (u - 0.6) / 1.2
    if 0 < sw < 1: fr.glow((lerp(x - 100, x + tw + 100, eio(sw)), 900), 60, WHITE, a * 0.35 * math.sin(math.pi * sw))
    fr.line((CX - 200 * eo((u - 0.5) / 0.6), 1030), (CX + 200 * eo((u - 0.5) / 0.6), 1030), GOLD, a * 0.8, 2)
    btext(fr, t, '你学会了巴菲特的动作', CX, 1110, 52, 'serif_med', WHITE, a, t0 + 0.8)
    btext(fr, t, '却没学会他的思考', CX, 1190, 52, 'serif_med', GOLD, a, t0 + 1.4)

# ================================================================ 倒带的公共元件
def replay_tag(fr, t, label, a, t0):
    """角标：◀◀ 倒带 · 2021 · 阿里 · 150 美元"""
    if a <= 0: return
    u = eo((t - t0) / 0.4)
    x = CX - text_width('◀◀  倒带  ·  ' + label, 'sans_med', 32) / 2
    fr.text('◀◀', x, 240, 32, 'sans_black', GOLD, a * u * (0.6 + 0.4 * (int(t * 3) % 2)), anchor='l')
    fr.text('倒带  ·  ' + label, x + text_width('◀◀  ', 'sans_med', 32), 240, 32, 'sans_med', GOLD, a * u, anchor='l')
    fr.line((CX - 60, 280), (CX + 60, 280), GOLD, a * u * 0.6, 2)

def inner(fr, t, s, y, a, t0, size=64):
    """内心独白：手写体逐字写出，配一对引号"""
    if a <= 0 or t < t0: return
    fr.text('“', 110, y - 34, 90, 'serif_black', C(240, 225, 190), a * 0.5 * eo((t - t0) / 0.4))
    fr.text(s, CX, y, size, 'hand', C(245, 232, 200), a, t0=t0, stag=0.06, dur=0.35, rise=8, mode='L', glow=0.15)

def deep_text(fr, t, s, x, y, size, col, a, t0, glow=0.35, grad=None):
    """芒格的问题：从画面深处推到眼前（缩放 0.7→1 + 模糊→清晰）"""
    if a <= 0 or t < t0: return
    u = eo((t - t0) / 0.8)
    q = round(10 * (1 - u) * 2) / 2
    m = blurred(s, 'serif_black', size, q)
    sc = 0.7 + 0.3 * u
    m = cv2.resize(m, (max(1, int(m.shape[1] * sc)), max(1, int(m.shape[0] * sc))), interpolation=cv2.INTER_LINEAR)
    h, w = m.shape; x0, y0 = int(x - w / 2), int(y - h / 2)
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if X1 <= X0 or Y1 <= Y0: return
    mm = m[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] * a * u
    rgb = grad_rows(h, tuple(tuple(g) for g in grad))[Y0 - y0:Y1 - y0, None, :] if grad else np.array(col, np.float32)
    fr.L[Y0:Y1, X0:X1] += mm[..., None] * rgb; fr.B[Y0:Y1, X0:X1] += (mm * glow)[..., None] * rgb

def frozen_chart(fr, t, c, a, box, d=None, stamp_t=None):
    """倒带定格：走势停在买点，「买入」印章发光"""
    px, py = case_xf(c, box)
    draw_chart(fr, t, c, a, 0, box, d=c['buy'][0] if d is None else d, mini=False)
    bx, bv = c['buy']
    stamp(fr, t, '买入', px(bx) + 70, py(bv) - 80, 58, stamp_t if stamp_t is not None else -1, GOLD, -10, a)
    return px, py

def quote_line(fr, t, s, y, a, t0):
    btext(fr, t, s, CX, y, 58, 'serif_black', GOLD, a, t0, glow=0.4, grad=GOLDG)

# ================================================================ 第二幕 · 倒带
def scene_rewind(fr, t):
    t0 = S['rewind']; a = env(t, t0 - 0.2, S['r1'] - 0.1, 0.4, 0.4)
    if a <= 0: return
    boxes = [(80, 420, 520, 720), (560, 420, 1000, 720), (80, 760, 520, 1060), (560, 760, 1000, 1060)]
    u = eio((t - t0 - 0.3) / 2.2)
    for k, (c, b) in enumerate(zip(CASES, boxes)):
        box = (b[0] + 24, b[1] + 60, b[2] - 24, b[3] - 22)
        d = lerp(c['rev'][-1][1], c['buy'][0], u)
        fr.rrect(b[0], b[1], b[2], b[3], 14, DIM, a * 0.3, 1)
        draw_chart(fr, t, c, a * 0.8, 0, box, d=d, mini=True)
        fr.text(c['name'], (b[0] + b[2]) / 2, b[1] + 32, 30, 'sans_med', C(210, 210, 220), a)
        if u >= 0.999:
            px, py = case_xf(c, box)
            stamp(fr, t, '买入', px(c['buy'][0]) + 40, py(c['buy'][1]) - 40, 34, t0 + 2.6 + k * 0.25, GOLD, -10, a)
    fr.text('◀◀  REWIND', CX, 330, 34, 'mono', GOLD, a * (0.5 + 0.5 * (int(t * 3) % 2)) * (1 - eo((t - t0 - 2.6) / 0.4)), track=0.3)
    btext(fr, t, '买入那一刻，你在想什么？', CX, 1240, 62, 'serif_black', WHITE, a, CH('R0', 1), glow=0.2)

def replay_phase(t, key, qid):
    """返回 (内心独白透明度, 问题段透明度)"""
    t0 = S[key]; tq = LN[qid]['t0']; t1 = {'r1': S['r2'], 'r2': S['r3'], 'r3': S['r4'], 'r4': S['r5'], 'r5': S['hammer']}[key]
    return env(t, t0 - 0.2, tq + 0.4, 0.4, 0.5), env(t, tq - 0.1, t1 - 0.1, 0.5, 0.45), env(t, t0 - 0.2, t1 - 0.1, 0.4, 0.45)

CBOX = (130, 620, 910, 1130)

def scene_r1(fr, t):
    if not (S['r1'] - 0.5 < t < S['r2'] + 0.3): return
    ai, aq, aa = replay_phase(t, 'r1', 'R1b')
    c = CASES[1]
    replay_tag(fr, t, '2021  ·  阿里  ·  150 美元', aa, S['r1'])
    if ai > 0:
        frozen_chart(fr, t, c, ai, CBOX)
        inner(fr, t, '从 319 跌到 150，够便宜了', 430, ai, CH('R1a', 1))
    if aq <= 0: return
    deep_text(fr, t, '便宜，是跟谁比？', CX, 400, 76, GOLD, aq, CUE['r1_q'], grad=GOLDG)
    ax, xr = 170, 930
    py = lambda v: 1180 - v / 360 * 600
    ta, tc, tm = CUE['r1_anchor'], CUE['r1_cash'], CUE['r1_mos']
    # 319：上一个人的出价（锚）→ 散成粒子
    aanc = aq * (1 - eio((t - ta - 0.6) / 0.8))
    dashed(fr, (ax, py(319)), (xr, py(319)), C(210, 210, 225), aanc, 2, prog=eo((t - CUE['r1_q']) / 0.6))
    fr.text('319  ·  上一个人的出价', ax + 10, py(319) - 34, 32, 'sans_med', C(210, 210, 225), aanc, anchor='l')
    if t > ta + 0.6:
        rr = np.random.default_rng(3); n = 260; u = t - ta - 0.6
        xs = ax + rr.random(n) * (xr - ax); ys = py(319) - u * (40 + rr.random(n) * 90)
        fr.splat(xs + np.sin(u * 3 + xs) * 6, ys, C(220, 220, 235), np.clip(1 - u / 2.0, 0, 1) * aq * 0.9, 'E')
    fr.line((ax, py(150)), (xr, py(150)), WHITE, aq * eo((t - CUE['r1_q'] - 0.3) / 0.5), 3)
    fr.text('价格 150', ax + 10, py(150) - 30, 34, 'sans_black', WHITE, aq * eo((t - CUE['r1_q'] - 0.3) / 0.5), anchor='l')
    # 未来的现金 → 折现 → 内在价值
    if t > tc:
        yrs = 9; vy = 250
        for k in range(yrs):
            ts = tc + 0.1 + k * 0.12
            u = eo((t - ts) / 0.4); mv = eio((t - tc - 1.6 - k * 0.04) / 0.9)
            disc = 0.88 ** (k + 1)
            h = 150 * lerp(1.0, disc, mv)
            x = lerp(560 + k * 44, 760, mv); yb = 1300
            fr.rrect_fill(x - 16, yb - h, x + 16, yb, 4, GOLD, aq * u * (1 - 0.6 * mv) * 0.7)
            if mv < 0.05: fr.text(f'{k + 1}', x, yb + 22, 20, 'mono', DIM, aq * u, mode='L')
        fr.text('未来每年的现金', 700, 1360, 28, 'sans_med', C(210, 200, 170), aq * eo((t - tc) / 0.4) * (1 - eio((t - tc - 1.6) / 0.5)))
        m2 = eo((t - tc - 2.4) / 0.5)
        if m2 > 0:
            fr.text('折现到今天 = 内在价值', 760, 1360, 30, 'sans_black', GOLD, aq * m2, mode='L', glow=0.3)
            fr.line((ax, py(vy)), (xr, py(vy)), GOLD, aq * m2, 4); fr.glow((xr, py(vy)), 20, GOLD, aq * m2 * 0.6)
            fr.text('内在价值（示意）', ax + 10, py(vy) - 32, 32, 'sans_black', GOLD, aq * m2, anchor='l', mode='L', glow=0.25)
    if t > tm:
        u = eo((t - tm) / 0.6); xb = 820
        fr.line((xb, py(150)), (xb, lerp(py(150), py(250), u)), GOLD, aq, 4)
        fr.line((xb - 16, py(150)), (xb + 16, py(150)), GOLD, aq * u, 4); fr.line((xb - 16, py(250)), (xb + 16, py(250)), GOLD, aq * u, 4)
        fr.text('安全边际', xb - 26, (py(150) + py(250)) / 2, 36, 'sans_black', GOLD, aq * u, anchor='r', mode='L', glow=0.3)
    quote_line(fr, t, '价格跌了，不代表价值低了', 1460, aq, L1('R1b') - 0.4)

def scene_r2(fr, t):
    if not (S['r2'] - 0.5 < t < S['r3'] + 0.3): return
    ai, aq, aa = replay_phase(t, 'r2', 'R2b')
    c = CASES[2]
    replay_tag(fr, t, '2026  ·  智谱  ·  1500 港元', aa, S['r2'])
    if ai > 0:
        frozen_chart(fr, t, c, ai, CBOX)
        inner(fr, t, 'AI 是大事，风险已经释放', 430, ai, CH('R2a', 1))
    if aq <= 0: return
    deep_text(fr, t, '三年后，谁赢？', CX, 400, 76, GOLD, aq, CUE['r2_q'], grad=GOLDG)
    tb, td = CUE['r2_bask'], CUE['r2_drop']
    # 「内在价值」在三年后的雾里散成二十几条可能
    af = aq * (1 - eio((t - tb) / 0.6))
    if af > 0:
        u = eio((t - CUE['r2_q'] - 0.3) / 1.6); r = np.random.default_rng(2); targets = r.uniform(60, 2700, 26)
        for k in range(26):
            v = lerp(1500, targets[k], u) + u * 90 * math.sin(t * (1.3 + k * 0.17) + k)
            yv = 1180 - v / 3200 * 600
            fr.line((170, 1180 - 1500 / 3200 * 600), (930, yv), GOLD, af * (0.9 if k == 0 else 0.3 * u), 1 if k else 2)
        fr.text('今天', 170, 1215, 26, 'mono', DIM, af); fr.text('三年后？', 930, 1215, 26, 'sans_med', DIM, af, anchor='r')
        fr.text('内在价值，有二十几种可能', CX, 560, 34, 'sans_med', C(210, 210, 220), af * u)
    if t > tb:
        ab = aq * eo((t - tb) / 0.5)
        bx = [(110, 360, '能投', TEAL), (390, 640, '不能投', DIM), (670, 970, '太难', GOLD)]
        yb = 1180
        for k, (xa, xb_, zh, col) in enumerate(bx):
            ak = ab * eo((t - tb - k * 0.35) / 0.4); big = k == 2
            fr.poly([(xa, yb - 150), (xa + 20, yb), (xb_ - 20, yb), (xb_, yb - 150)], col, ak * (1 if big else 0.7), 4 if big else 2)
            fr.text(zh, (xa + xb_) / 2, yb + 60, 52 if big else 44, 'serif_black', col, ak, mode='L', glow=0.25 if big else 0)
        u = (t - td) / 0.8
        x = 820; y = lerp(700, yb - 60, eio(u)) - math.sin(cl(u) * math.pi) * 120 if u > 0 else 700
        sc = 1 - 0.3 * eio(u) if u > 0 else 1
        fr.rrect(x - 90 * sc, y - 36 * sc, x + 90 * sc, y + 36 * sc, 20 * sc, WHITE, ab, 2)
        fr.text('智谱', x, y, int(44 * sc), 'serif_black', WHITE, ab)

def scene_r3(fr, t):
    if not (S['r3'] - 0.5 < t < S['r4'] + 0.3): return
    ai, aq, aa = replay_phase(t, 'r3', 'R3b')
    c = CASES[3]
    replay_tag(fr, t, '2026  ·  英伟达  ·  180 美元', aa, S['r3'])
    if ai > 0:
        frozen_chart(fr, t, c, ai, CBOX)
        inner(fr, t, '13 倍，比消费股还便宜', 430, ai, CH('R3a', 1))
    if aq <= 0: return
    deep_text(fr, t, '用的是哪一年的利润？', CX, 400, 70, GOLD, aq, CUE['r3_q'], grad=GOLDG)
    tp, t26 = CUE['r3_peak'], CUE['r3_26']
    af = aq * eo((t - CUE['r3_q'] - 0.4) / 0.5)
    fr.text('PE', 320, 540, 64, 'num', WHITE, af, mode='L', glow=0.2); fr.text('=', 400, 540, 56, 'sans_med', DIM, af)
    fr.text('价格', 590, 500, 44, 'serif_black', WHITE, af); fr.line((480, 540), (700, 540), WHITE, af, 3)
    shrink = eio((t - t26 + 1.6) / 1.4)
    fr.text('利润', 590, 585, int(44 * (1 - 0.35 * shrink)), 'serif_black', GOLD if shrink < 0.5 else RED2, af)
    vals = [.36, .42, .5, .58, .67, .76, .86, .95, 1.0, .9, .78, .66, .56, .5]
    nb = len(vals); x0, x1, yb, hmax = 140, 940, 1270, 260; bw = (x1 - x0) / nb
    for k, v in enumerate(vals):
        ts = CUE['r3_q'] + 0.8 + k * 0.1 if k <= 8 else t26 - 1.6 + (k - 9) * 0.3
        u = eo((t - ts) / 0.35)
        if u <= 0: continue
        col = GOLD if k == 8 else (RED2 if k > 8 else C(110, 140, 200))
        h = v * hmax * u; xa = x0 + k * bw + 6
        fr.rrect_fill(xa, yb - h, xa + bw - 12, yb, 4, col, aq * (0.55 if k != 8 else 0.85))
        if k == 8: fr.glow((xa + bw / 2 - 6, yb - h), 30, GOLD, aq * 0.4 * u)
    fr.line((x0, yb), (x1, yb), DIM, aq * 0.6, 2)
    fr.text('利润', x0, yb + 40, 28, 'sans_med', DIM, af, anchor='l')
    xk = x0 + 8 * bw + bw / 2
    if t > tp: fr.text('创纪录的一年', xk, yb - hmax - 44, 32, 'sans_black', GOLD, aq * eo((t - tp) / 0.4), mode='L', glow=0.2)
    pe = counter(t, t26 - 1.4, t26, 13, 26) if t > t26 - 1.4 else 13
    col = lerpc(GOLD, RED2, cl((pe - 13) / 6))
    fr.text(f'{pe:.0f}×', CX, 735, int(150 + 30 * impact(t) * (pe > 25)), 'num', col, af, mode='L', glow=0.5)
    fr.text('假设：股价不变，利润减半' if pe > 14 else '按创纪录的利润预测', CX, 840, 34, 'sans_med', C(210, 210, 220), af)
    fr.text('不是断言英伟达见顶，而是先问：这份利润，能持续吗？', CX, 1420, 28, 'sans_light', C(190, 190, 200), aq * eo((t - t26 - 0.3) / 0.6))

def scene_r4(fr, t):
    if not (S['r4'] - 0.5 < t < S['r5'] + 0.3): return
    ai, aq, aa = replay_phase(t, 'r4', 'R4b')
    replay_tag(fr, t, '你的每一次换仓', aa, S['r4'])
    if ai > 0:
        boxes = [(70, 700, 370, 940), (390, 700, 690, 940), (710, 700, 1010, 940)]
        signs = ['互联网', '电商', '人工智能']; cs = [CASES[0], CASES[1], CASES[3]]
        fr.line((90, 1000), (990, 1000), DIM, ai * 0.5, 2)
        for k, (b, sg, c) in enumerate(zip(boxes, signs, cs)):
            ak = ai * eo((t - S['r4'] - 0.3 - k * 0.3) / 0.4)
            draw_chart(fr, t, c, ak * 0.8, 0, (b[0] + 16, b[1] + 20, b[2] - 16, b[3] - 16), d=c['rev'][-1][1], mini=True)
            ts = CUE['r4_story'] + k * 0.55
            asg = ai * eo((t - ts) / 0.35)
            w2 = text_width(sg, 'serif_black', 46) / 2 + 30
            fr.rrect((b[0] + b[2]) / 2 - w2, 560, (b[0] + b[2]) / 2 + w2, 640, 14, GOLD, asg, 3)
            fr.text(sg, (b[0] + b[2]) / 2, 600, 46, 'serif_black', GOLD, asg, mode='L', glow=0.3)
            fr.circle(((b[0] + b[2]) / 2, 1000), 8, GOLD, ak, -1)
        inner(fr, t, '选对赛道，就赢了一半', 430, ai, CUE['r4_think'] + 0.8)
    if aq <= 0: return
    deep_text(fr, t, '汽车也改变了世界', CX, 400, 72, GOLD, aq, L0('R4b'), grad=GOLDG)
    cols, rows = 50, 40; x0, y0, sp = 148, 560, 16
    rr = np.random.default_rng(9); order = rr.random(cols * rows)
    keep = np.zeros(cols * rows, bool); keep[[612, 1037, 1544]] = True
    gx = x0 + (np.arange(cols * rows) % cols) * sp; gy = y0 + (np.arange(cols * rows) // cols) * sp
    tc, t3 = CUE['r4_cars'], CUE['r4_3']
    ua = np.clip((t - tc + 0.2 - (gy - y0) / 640 * 0.9 - order * 0.2) / 0.3, 0, 1)
    die = np.clip((t - t3 + 1.0 - order * 1.0) / 0.3, 0, 1) * (~keep)
    al = ua * (1 - die)
    fr.dots(gx, gy, C(160, 185, 240), al * aq * 0.9, 1, 'L'); fr.splat(gx, gy, C(160, 185, 240), al * aq * 0.5, 'B')
    if t > t3 - 0.2:
        ak = aq * eo((t - t3) / 0.5)
        for k, idx in enumerate(np.where(keep)[0]):
            fr.glow((gx[idx], gy[idx]), 16, GOLD, ak * 0.9); fr.circle((gx[idx], gy[idx]), 7, GOLD2, ak, -1)
            fr.text(['通用', '福特', '克莱斯勒'][k], gx[idx], gy[idx] - 34, 30, 'sans_black', GOLD, ak, mode='L', glow=0.2)
    if t > tc:
        n = 2000 if t < t3 - 1.0 else counter(t, t3 - 1.0, t3, 2000, 3)
        an = aq * eo((t - tc) / 0.4)
        col = WHITE if n > 1000 else lerpc(RED2, GOLD, cl((50 - n) / 47))
        fr.text(f'{n:.0f}', 380, 1290, 110, 'num', col, an, mode='L', glow=0.35)
        fr.text('家美国车企' if n > 3.5 else '家活下来', 560, 1300, 42, 'serif_black', col, an, anchor='l')
        fr.text('巴菲特 1999 年的提醒（大意）', 560, 1352, 24, 'sans_light', DIM, an * 0.9, anchor='l')
    quote_line(fr, t, '公司赢了，不代表股东一定赢了', 1460, aq, CUE['r4_lesson'] + 1.6)

# ================================================================ 第五段倒带 → 铁锤
def _hammer_sprite():
    k = 2; hw, hh, L_, hwid = 440 * k, 150 * k, 560 * k, 46 * k
    Wd, Hd = hw + 40 * k, hh + L_ + 30 * k
    im = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx = Wd // 2; hy0 = L_ + 10 * k; hx0 = cx - hwid // 2
    for x in range(hwid):
        u = x / hwid; v = int(28 + 40 * math.sin(math.pi * u) ** 2)
        d.line([(hx0 + x, 10 * k), (hx0 + x, hy0 + 10)], fill=(v, v, v + 8, 255))
    for yb in (40 * k, hy0 - 40 * k):
        d.rectangle([hx0 - 4 * k, yb, hx0 + hwid + 4 * k, yb + 14 * k], fill=(214, 168, 80, 255))
    head = Image.new('RGBA', (hw, hh), (0, 0, 0, 0)); hd = ImageDraw.Draw(head)
    stops = [(0, (255, 240, 196)), (0.28, (232, 186, 92)), (0.55, (150, 104, 36)), (0.8, (217, 166, 74)), (1, (110, 76, 24))]
    for y in range(hh):
        u = y / hh; c = [int(np.interp(u, [s[0] for s in stops], [s[1][j] for s in stops])) for j in range(3)]
        hd.line([(0, y), (hw, y)], fill=tuple(c) + (255,))
    mask = Image.new('L', (hw, hh), 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, hw - 1, hh - 1], 22 * k, fill=255)
    head.putalpha(mask)
    hd = ImageDraw.Draw(head); f = get_font('serif_black', 32 * k)
    for row, txt in enumerate(['龙头 · 护城河', '低市盈率 · 回购']):
        y = int(hh * (0.34 + 0.34 * row))
        hd.text((hw // 2 + 2, y + 2), txt, font=f, fill=(255, 236, 190, 160), anchor='mm')
        hd.text((hw // 2, y), txt, font=f, fill=(70, 46, 12, 255), anchor='mm')
    im.alpha_composite(head, (cx - hw // 2, hy0))
    a = np.asarray(im).astype(np.float32) / 255
    a = cv2.resize(a, (Wd // k, Hd // k), interpolation=cv2.INTER_AREA)
    rgb = np.where(a[..., 3:] > 1e-3, a[..., :3], 0)
    return rgb, a[..., 3], (Wd // k / 2, Hd // k - 1)

HAM = None
def hammer_sprite():
    global HAM
    if HAM is None: HAM = _hammer_sprite()
    return HAM

NAIL_X = [250, 540, 830]; GROUND = 1240; NAIL_H0, NAIL_H1 = 170, 62
STRIKES = ['S1', 'S2', 'S3']
NAIL_LAB = ['阿里 · 回购', '英伟达 · 13×', '腾讯 · 护城河']

def nail_h(i, t):
    c = CUE[STRIKES[i]]
    return NAIL_H0 if t < c else lerp(NAIL_H0, NAIL_H1, eo((t - c) / 0.07))

REST = (CX, 1010.0, 0.0, 0.72)
def hammer_pose(t):
    A = S['hammer'] + 0.6
    if t < A: return REST
    c = [CUE[k] for k in STRIKES]
    top = lambda i, dy=0: (NAIL_X[i] + 40, GROUND - NAIL_H0 - 300 + dy, -32.0, 0.82)
    hitp = lambda i: (NAIL_X[i], GROUND - NAIL_H0, 0.0, 0.82)
    kf = [(A, REST), (c[0] - 1.1, REST), (c[0] - 0.35, top(0))]
    for i in range(3):
        kf += [(c[i] - 0.2, top(i, -20))]
        if c[i] - 0.2 <= t < c[i]:
            u = ei((t - c[i] + 0.2) / 0.2); p0, p1 = top(i, -20), hitp(i)
            return tuple(lerp(p0[j], p1[j], u) for j in range(4))
        kf += [(c[i], (NAIL_X[i], GROUND - NAIL_H1, 0.0, 0.82)), (c[i] + 0.3, (NAIL_X[i] + 10, GROUND - NAIL_H1 - 70, -8.0, 0.82))]
        if i < 2: kf += [(c[i + 1] - 0.55, top(i + 1))]
    kf += [(c[2] + 1.2, (CX, 980.0, -6.0, 0.72)), (c[2] + 2.0, (CX, 980.0, 0.0, 0.72))]
    return keys(t, kf)

def draw_hammer(fr, t, a=1.0, pose=None):
    rgb, al, (px, py) = hammer_sprite()
    x, y, ang, sc = pose or hammer_pose(t)
    M_ = cv2.getRotationMatrix2D((px, py), -ang, sc); M_[0, 2] += x - px; M_[1, 2] += y - py
    pm = cv2.warpAffine(rgb * al[..., None], M_, (W, H), flags=cv2.INTER_LINEAR)
    aa = cv2.warpAffine(al, M_, (W, H), flags=cv2.INTER_LINEAR) * a
    ys, xs = np.where(aa > 0.004)
    if len(ys) == 0: return
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    A_ = aa[y0:y1, x0:x1]; P = pm[y0:y1, x0:x1] * a
    fr.sprites.append((np.where(A_[..., None] > 1e-3, P / np.maximum(A_[..., None], 1e-3), 0), A_, x0, y0))
    fr.B[y0:y1, x0:x1] += (A_ * 0.18)[..., None] * np.array(GOLD, np.float32)

def sparks(fr, t, c, x, y, n=110, seed=0, big=1.0):
    u = t - c
    if u < 0 or u > 1.2: return
    r = np.random.default_rng(seed)
    ang = -math.pi / 2 + (r.random(n) - 0.5) * 2.4; sp = (300 + r.random(n) * 900) * big
    xs = x + np.cos(ang) * sp * u; ys = y + np.sin(ang) * sp * u + 0.5 * 2200 * u * u
    life = np.clip(1 - u / (0.5 + r.random(n) * 0.7), 0, 1)
    cols = np.stack([np.ones(n), 0.65 + 0.3 * r.random(n), 0.25 + 0.3 * r.random(n)], 1)
    fr.dots(xs, ys, cols, life * 0.9, 1, 'E')
    rx = 30 + 330 * eo(u / 0.6) * big; th = np.linspace(0, 2 * math.pi, 80)
    fr.poly(np.stack([x + rx * np.cos(th), GROUND + rx * 0.16 * np.sin(th)], 1), GOLD2, (1 - eo(u / 0.6)) * 0.8, 2, closed=True)
    fr.glow((x, y), 50 * big, WHITE, max(0, 1 - u / 0.25) * 0.9)

def draw_nail(fr, i, t, a):
    x = NAIL_X[i]; h = nail_h(i, t); top = GROUND - h
    fr.fillpoly([(x - 8, GROUND), (x - 8, top + 10), (x + 8, top + 10), (x + 8, GROUND)], C(150, 156, 172), a, 'L')
    fr.line((x - 3, GROUND), (x - 3, top + 12), C(230, 235, 245), a * 0.7, 2)
    fr.rrect_fill(x - 38, top - 4, x + 38, top + 12, 6, C(190, 196, 210), a, 'L')
    fr.line((x - 34, top - 2), (x + 34, top - 2), WHITE, a * 0.8, 2)
    c = CUE[STRIKES[i]]
    if t > c:
        r = np.random.default_rng(i + 30); u = eo((t - c) / 0.25)
        for k in range(4):
            sgn = -1 if k % 2 else 1; pts = [(x, GROUND)]
            for j in range(4):
                px_, py_ = pts[-1]; pts.append((px_ + sgn * (14 + r.random() * 26) * u, py_ + (r.random() - 0.3) * 10 * u))
            fr.poly(pts, GOLD, a * 0.55, 2)
    return top

def scene_r5(fr, t):
    t0 = S['r5']; th = S['hammer']
    if not (t0 - 0.5 < t < S['tx'] + 0.3): return
    aa = env(t, t0 - 0.2, S['tx'] - 0.1, 0.4, 0.45)
    replay_tag(fr, t, '2018  ·  腾讯  ·  400 港元', aa * (1 - eio((t - th) / 0.5)), t0)
    c = CASES[0]
    ai = env(t, t0 - 0.2, th + 0.5, 0.4, 0.5)
    if ai > 0:     # 一切开始的那一笔：走势一路倒退回 2018 年的 400
        d = lerp(c['rev'][-1][1], c['buy'][0], eio((t - t0 - 0.2) / 2.2))
        frozen_chart(fr, t, c, ai, CBOX, d=d, stamp_t=t0 + 2.4)
        inner(fr, t, '龙头，护城河，回购——全都符合', 430, ai, CUE['r5_think'] + 0.8, size=58)
    # 前面所有「买入」印章飞来叠在一起 → 显形成锤子
    if th - 1.6 < t < th + 0.8:
        u = eio((t - th + 1.6) / 1.4)
        starts = [(150, 300), (930, 320), (140, 1350), (940, 1380), (540, 1500)]
        for k, (sx, sy) in enumerate(starts):
            x = lerp(sx, CX, u); y = lerp(sy, 960, u)
            stamp(fr, t, '买入', x, y, int(60 * (1 - 0.3 * u)), th - 1.6 + k * 0.05, GOLD, -10 + k * 4, (1 - eio((t - th - 0.2) / 0.5)))
    A = th + 0.2
    ah = eo((t - A) / 0.5)
    if ah > 0 and t < S['tx']:
        if t < A + 0.7: fr.glow((CX, 960), 200, GOLD2, (1 - eo((t - A) / 0.7)) * 0.9)
        draw_hammer(fr, t, ah * (1 - eio((t - S['tx'] + 0.6) / 0.5)))
    aq = env(t, th - 0.1, CUE['S1'] - 1.5, 0.4, 0.5)
    if aq > 0:
        btext(fr, t, '手里拿着锤子的人', CX, 290, 66, 'serif_black', WHITE, aq, th + 0.1, glow=0.1)
        btext(fr, t, '看什么都像钉子', CX, 390, 66, 'serif_black', GOLD, aq, CH('R5b', 1), glow=0.35, grad=GOLDG)
        fr.text('— 查理 · 芒格', CX + 220, 465, 30, 'serif_med', C(210, 200, 180), aq, t0=CH('R5b', 1) + 0.6)
    # 三颗钉子 = 你的三笔交易
    ag = env(t, L0('S1') - 0.8, S['tx'] - 0.1, 0.5, 0.45)
    if ag > 0:
        fr.line((90, GROUND), (990, GROUND), C(150, 160, 190), ag * 0.6, 2)
        fr.fillpoly([(90, GROUND), (990, GROUND), (990, GROUND + 30), (90, GROUND + 30)], C(40, 34, 30), ag * 0.8, 'L')
        for i in range(3):
            ai_ = ag * eo((t - L0(STRIKES[i]) + 0.4) / 0.4)
            if ai_ <= 0: continue
            top = draw_nail(fr, i, t, ai_)
            lab = NAIL_LAB[i]; wl = text_width(lab, 'sans_black', 30) / 2 + 22
            fr.rrect(NAIL_X[i] - wl, GROUND + 64, NAIL_X[i] + wl, GROUND + 116, 26, GOLD, ai_ * 0.8, 2)
            fr.text(lab, NAIL_X[i], GROUND + 90, 30, 'sans_black', GOLD, ai_)
            sparks(fr, t, CUE[STRIKES[i]], NAIL_X[i], GROUND - NAIL_H0, seed=i, big=0.9 + 0.12 * i)
            # 每一个词都没错（✓）→ 错的是，你把线索当成了结论（?）
            if t > L0('R5c'):
                y = top - 90; tq = CH('R5c', 1)
                if t < tq: check(fr, NAIL_X[i], y, 54, (t - L0('R5c') - i * 0.18) / 0.3, GOLD, ai_, 6)
                else:
                    u = eo((t - tq - i * 0.15) / 0.3)
                    fr.text('?', NAIL_X[i], y, int(90 * (0.6 + 0.4 * u)), 'serif_black', RED2, ai_ * u, mode='L', glow=0.5)
    if t > CUE['clue'] - 0.2:
        ac = env(t, CUE['clue'] - 0.2, S['tx'] - 0.1, 0.4, 0.45)
        btext(fr, t, '线索  ≠  结论', CX, 420, 100, 'serif_black', WHITE, ac, CUE['clue'] - 0.2, glow=0.35, dur=0.5)

# ================================================================ 腾讯：股价 = 利润 × 市盈率
def scene_tx(fr, t):
    t0 = S['tx']; a = env(t, t0 - 0.1, S['inv'] + 0.05, 0.4, 0.4)
    if a <= 0: return
    fr.text('腾讯  ·  2018 → 2026', CX, 250, 34, 'sans_med', GOLD, a, t0=t0)
    tp, tpe, tm, te = CUE['tx_profit'], CUE['tx_pe'], CUE['tx_moat'], CUE['tx_expect']
    base, hmax = 1180, 470
    cols = [(250, '股价'), (540, '利润'), (830, '市盈率')]
    ae = a * eo((t - t0 - 0.3) / 0.5) * (1 - 0.7 * eio((t - te) / 0.4))
    for (x, lab) in cols: fr.text(lab, x, 400, 50, 'serif_black', WHITE, ae)
    fr.text('=', 395, 400, 50, 'sans_med', DIM, ae); fr.text('×', 685, 400, 50, 'sans_med', DIM, ae)
    price = 400 if t < tpe + 1.4 else counter(t, tpe + 1.4, tpe + 2.2, 400, 373)
    prof = 1.0 if t < tp else counter(t, tp, tp + 1.2, 1.0, 2.86)
    pe = 39 if t < tpe else counter(t, tpe, tpe + 1.4, 39, 14)
    vals = [(price / 500 * hmax, f'{price:.0f} 港元', C(200, 205, 220)), (prof / 2.86 * hmax, f'×{prof:.1f}', GOLD),
            (pe / 39 * hmax, f'{pe:.0f}×', RED2 if t > tpe else C(150, 180, 240))]
    dim = 1 - 0.6 * eio((t - te) / 0.4)
    for k, ((x, lab), (h, txt, col)) in enumerate(zip(cols, vals)):
        ak = a * eo((t - t0 - 0.6 - k * 0.15) / 0.4) * dim
        hh = h * eo((t - t0 - 0.6 - k * 0.15) / 0.6)
        if k == 0 and t > tm:     # 股价拆成「公司」+「期待」
            u = eo((t - tm) / 0.8)
            hc = hh * lerp(0.35, 0.72, eio((t - tm) / 2.2)); he = hh - hc
            fr.rrect_fill(x - 75, base - hc, x + 75, base, 10, GOLD, ak * 0.7)
            fr.rrect(x - 75, base - hh, x + 75, base - hc, 10, C(150, 180, 240), ak * 0.9 * u, 2)
            fr.rrect_fill(x - 75, base - hh, x + 75, base - hc, 10, C(150, 180, 240), ak * 0.25 * u)
            fr.text('公司', x, base - hc / 2, 34, 'sans_black', C(40, 26, 6), ak * u, mode='O')
            fr.text('期待', x, base - hc - he / 2, 34, 'sans_black', C(190, 210, 255), ak * u)
        else:
            fr.rrect_fill(x - 75, base - hh, x + 75, base, 10, col, ak * 0.55)
            fr.rrect(x - 75, base - hh, x + 75, base, 10, col, ak * 0.9, 2)
        fr.glow((x, base - hh), 40, col, ak * 0.3)
        fr.text(txt, x, base - hh - 36, 42, 'num' if k else 'sans_black', col, ak, mode='L', glow=0.25)
    fr.line((120, base), (960, base), DIM, a * 0.6 * dim, 2)
    fr.text('2018 年 400 港元', 250, base + 40, 26, 'sans_med', DIM, a * dim * (1 if t < tpe + 1.4 else 0))
    fr.text('利润近三倍', 540, base + 40, 28, 'sans_black', GOLD, a * dim * eo((t - tp - 1.2) / 0.3))
    fr.text('近 40 倍 → 十几倍', 830, base + 40, 28, 'sans_black', RED2, a * dim * eo((t - tpe - 1.4) / 0.3))
    fr.text('股价回到原地', 250, base + 40, 28, 'sans_black', C(210, 210, 220), a * dim * eo((t - tpe - 2.2) / 0.3))
    if t > te - 0.2:
        ap = a * eo((t - te + 0.2) / 0.4)
        fr.rrect_fill(90, 520, 990, 900, 30, C(6, 6, 10), ap * 0.78, 'L')
        btext(fr, t, '你买下的，还有', CX, 620, 64, 'serif_black', WHITE, ap, te - 0.2, glow=0.1)
        btext(fr, t, '市场对它明天的期待', CX, 770, 88, 'serif_black', GOLD, ap, te + 0.4, glow=0.45, grad=GOLDG)
    fr.text('口径：IFRS 归母净利润 2018 年 787 亿 → 2025 年 2248 亿元；市盈率按当年利润估算；股价不含分红', CX, 1300, 22, 'sans_light',
            C(170, 170, 185), a * 0.8 * eo((t - tp) / 0.5))

def scene_inv(fr, t):
    t0 = S['inv']; a = env(t, t0 - 0.1, S['wake'] + 0.05, 0.4, 0.45)
    if a <= 0: return
    fr.text('反过来想', CX, 250, 34, 'sans_med', GOLD, a, t0=t0)
    cx, cy, R = CX, 900, 250
    tin, triv = CUE['inv_q'], CUE['inv_rivals']
    flip = abs(math.cos(math.pi * eio((t - tin - 0.3) / 0.8))) if t > tin + 0.3 else 1.0
    gaps = []
    if t > triv + 0.8:
        g = eo((t - triv - 0.8) / 0.6) * 0.28
        gaps = [(math.radians(135) - g, math.radians(135) + g), (math.radians(45) - g, math.radians(45) + g)]
    th = np.linspace(0, 2 * math.pi, 240); keep = np.ones_like(th, bool)
    for g0, g1 in gaps: keep &= ~((th > g0) & (th < g1))
    for rr_, w_ in ((R, 4), (R + 18, 2)):
        xs = cx + rr_ * np.cos(th); ys = cy + rr_ * np.sin(th) * flip; seg = []
        for k in range(len(th)):
            if keep[k]: seg.append((xs[k], ys[k]))
            elif len(seg) > 1: fr.poly(seg, GOLD, a, w_); seg = []
            else: seg = []
        if len(seg) > 1: fr.poly(seg, GOLD, a, w_)
    fr.text('护城河 ✓', cx + R * 0.82 + 40, cy - R * 0.62 * flip - 30, 34, 'sans_black', GOLD, a * eo((t - CUE['inv_moat']) / 0.4))
    fr.circle((cx, cy), 105, GOLD, a * 0.9, 3); fr.glow((cx, cy), 80, GOLD, a * 0.25)
    fr.text('阿里', cx, cy, 64, 'serif_black', GOLD, a, mode='L', glow=0.3)
    r = np.random.default_rng(5); n = 140
    ph0 = r.random(n) * 2 * math.pi; rad = 130 + r.random(n) * 100; sp = 0.25 + r.random(n) * 0.3
    ang = ph0 + t * sp; xs = cx + rad * np.cos(ang); ys = cy + rad * np.sin(ang) * flip
    if t > triv + 0.8:
        side = np.where(r.random(n) < 0.5, 0, 1); leave = r.random(n) < 0.6
        ts_ = triv + 0.9 + r.random(n) * 3.0; u = np.clip((t - ts_) / 1.4, 0, 1) * leave
        xs = lerp(xs, np.where(side == 0, 150, 930), veio(u)); ys = lerp(ys, 1350, veio(u))
    fr.dots(xs, ys, C(170, 200, 255), a, 1.5, 'E'); fr.splat(xs, ys, C(170, 200, 255), a * 0.6, 'B')
    if t > tin: deep_text(fr, t, '如果失败，会因为什么？', CX, 470, 66, RED2, a, tin + 0.1, glow=0.35)
    for k, (lab, sx, ang_) in enumerate([('拼多多', 150, 135), ('抖音', 930, 45)]):
        ts = triv + 0.3 + k * 0.45
        if t < ts: continue
        u = eo((t - ts) / 0.5)
        ex = cx + (R + 10) * math.cos(math.radians(ang_)); ey = cy + (R + 10) * math.sin(math.radians(ang_))
        x1 = lerp(sx, ex, u); y1 = lerp(1350, ey, u)
        fr.line((sx, 1350), (x1, y1), RED2, a, 5); fr.glow((x1, y1), 30, RED, a * 0.7)
        d = math.atan2(y1 - 1350, x1 - sx)
        fr.fillpoly([(x1, y1), (x1 - 30 * math.cos(d - 0.4), y1 - 30 * math.sin(d - 0.4)), (x1 - 30 * math.cos(d + 0.4), y1 - 30 * math.sin(d + 0.4))], RED2, a, 'E')
        fr.text(lab, sx, 1400, 44, 'serif_black', RED2, a * u, mode='L', glow=0.3)

# ================================================================ 第三幕 · 觉醒
def scene_wake(fr, t):
    t0 = S['wake']; a = env(t, t0 - 0.2, S['ibm'] - 0.1, 0.5, 0.45)
    if a <= 0: return
    draw_hammer(fr, t, a * 0.55, pose=(CX, 960.0, 0.0, 0.45))
    items = ['不追高', '不碰垃圾股', '熟读巴菲特', '专门等回调']
    tt = CUE['w_tick']
    for k, lab in enumerate(items):
        x = 120 + (k % 2) * 460; y = 1040 + (k // 2) * 96
        ai = a * eo((t - t0 - 0.3 - k * 0.12) / 0.4)
        off = eio((t - tt - 0.4 - k * 0.35) / 0.4)
        fr.rrect(x, y - 30, x + 60, y + 30, 10, C(200, 205, 225), ai * 0.6, 2)
        check(fr, x + 30, y, 44, 1.0, GOLD, ai * (1 - 0.85 * off), 5)
        fr.text(lab, x + 90, y, 50, 'serif_med', WHITE, ai * (1 - 0.5 * off), anchor='l')
    btext(fr, t, '结果不好，不一定是判断错了', CX, 420, 54, 'serif_med', C(220, 220, 230), a, CUE['w_find'])
    btext(fr, t, '可你没有在判断，只是在打勾', CX, 520, 60, 'serif_black', GOLD, a, tt, glow=0.35, grad=GOLDG)

def scene_ibm(fr, t):
    t0 = S['ibm']; a = env(t, t0 - 0.2, S['three'] - 0.1, 0.45, 0.45)
    if a <= 0: return
    btext(fr, t, '连巴菲特也看错过', CX, 440, 76, 'serif_black', WHITE, a, t0 + 0.1, glow=0.15)
    x0, x1, y = 160, 920, 820
    u = eo((t - CUE['ibm_t']) / 1.6)
    fr.line((x0, y), (lerp(x0, x1, u), y), GOLD, a, 3)
    for k, (yr, lab, xf) in enumerate([('2011', '重仓买入 IBM', 0.0), ('2017', '重新评估', 0.62), ('2018', '清仓', 1.0)]):
        tk = CUE['ibm_t'] + 0.2 + k * 0.7
        ak = a * eo((t - tk) / 0.4); x = lerp(x0, x1, xf)
        fr.circle((x, y), 12, GOLD, ak, -1); fr.glow((x, y), 20, GOLD, ak * 0.6)
        fr.text(yr, x, y - 60, 48, 'num', GOLD, ak, mode='L', glow=0.25)
        fr.text(lab, x, y + 60, 36, 'sans_black', WHITE, ak)
    btext(fr, t, '事实变了，他敢承认', CX, 1120, 72, 'serif_black', GOLD, a, CUE['ibm_admit'] + 0.4, glow=0.4, grad=GOLDG)
    fr.text('来源：CNBC 2017、2018 年采访', CX, 1220, 24, 'sans_light', DIM, a * eo((t - CUE['ibm_t'] - 2) / 0.5))

# 锤子碎片 → 天平 / 镜子 / 圆
PART = None
def hammer_particles():
    global PART
    if PART is None:
        rgb, al, (px, py) = hammer_sprite()
        ys, xs = np.where(al > 0.6)
        r = np.random.default_rng(3); idx = r.choice(len(ys), 2200, replace=False)
        PART = dict(x=xs[idx] - px, y=ys[idx] - py, col=np.clip(rgb[ys[idx], xs[idx]] * 1.3, 0, 1),
                    vx=r.normal(0, 1, 2200), vy=r.normal(-0.4, 1, 2200), u=r.random(2200), j=r.normal(0, 1, 2200))
    return PART

def along(segs, u):
    """把 0..1 的参数映射到一组折线上（按长度均分）"""
    L = [math.dist(a_, b_) for a_, b_ in segs]; cum = np.cumsum([0] + L); tot = cum[-1]
    s = u * tot; k = np.clip(np.searchsorted(cum, s) - 1, 0, len(segs) - 1)
    f = (s - cum[k]) / np.maximum(np.array(L)[k], 1e-6)
    A = np.array([segs[i][0] for i in k]); B = np.array([segs[i][1] for i in k])
    return A[:, 0] + (B[:, 0] - A[:, 0]) * f, A[:, 1] + (B[:, 1] - A[:, 1]) * f

TOOL_C = (CX, 840)
def tool_segs(name):
    cx, cy = TOOL_C
    if name == 'scale':
        segs = [((cx, cy - 230), (cx, cy + 210)), ((cx - 110, cy + 210), (cx + 110, cy + 210)), ((cx - 260, cy - 190), (cx + 260, cy - 190)),
                ((cx - 260, cy - 190), (cx - 320, cy - 20)), ((cx - 260, cy - 190), (cx - 200, cy - 20)),
                ((cx + 260, cy - 190), (cx + 200, cy - 20)), ((cx + 260, cy - 190), (cx + 320, cy - 20))]
        th = np.linspace(0, math.pi, 12)
        for sx in (cx - 260, cx + 260):
            pts = [(sx + 70 * math.cos(a_), cy - 20 + 34 * math.sin(a_)) for a_ in th]
            segs += list(zip(pts[:-1], pts[1:]))
        return segs
    if name == 'mirror':
        w2, h2 = 300, 330; return [((cx - w2, cy - h2), (cx + w2, cy - h2)), ((cx + w2, cy - h2), (cx + w2, cy + h2)),
                                   ((cx + w2, cy + h2), (cx - w2, cy + h2)), ((cx - w2, cy + h2), (cx - w2, cy - h2))]
    th = np.linspace(0, 2 * math.pi, 120); pts = [(cx + 280 * math.cos(a_), cy + 280 * math.sin(a_)) for a_ in th]
    return list(zip(pts[:-1], pts[1:]))

def scene_tools(fr, t):
    t3, q1, q2, q3, tm = S['three'], S['q1'], S['q2'], S['q3'], S['mos']
    if not (t3 - 0.5 < t < S['quote'] + 0.3): return
    a = env(t, t3 - 0.2, S['quote'] - 0.1, 0.4, 0.5)
    P = hammer_particles(); x0, y0, ang, sc = (CX, 960.0, 0.0, 0.45)
    if t < t3 + 0.6: draw_hammer(fr, t, a * (1 - eo((t - t3) / 0.5)), pose=(x0, y0, ang, sc))
    btext(fr, t, '巴菲特和芒格从没给过一套公式', CX, 400, 50, 'serif_med', C(220, 220, 230), a * env(t, t3, q1 - 0.1, 0.4, 0.4), t3 + 0.2)
    btext(fr, t, '只是诚实地回答三个问题', CX, 490, 60, 'serif_black', GOLD, a * env(t, t3, q1 - 0.1, 0.4, 0.4), CUE['three'], glow=0.3, grad=GOLDG)
    bx = x0 + P['x'] * sc; by = y0 + P['y'] * sc
    u = t - t3 - 0.4
    ex = bx + P['vx'] * 220 * (1 - math.exp(-max(u, 0) * 1.6)); ey = by + P['vy'] * 220 * (1 - math.exp(-max(u, 0) * 1.6))
    shapes = [(q1, 'scale'), (q2, 'mirror'), (q3, 'circle')]
    px_, py_ = ex, ey; col = P['col']; gsum = 0
    for k, (ts, nm) in enumerate(shapes):
        g = eio((t - ts + 0.3) / 1.0)
        if g <= 0: break
        tx_, ty_ = along(tool_segs(nm), P['u']); tx_ = tx_ + P['j'] * 3; ty_ = ty_ + P['j'] * 3
        px_ = lerp(px_, tx_, g); py_ = lerp(py_, ty_, g); gsum = g
    if t > t3 and t < tm + 0.5:
        ap = a * (1 - eio((t - tm) / 0.5)) * (0.9 if t > t3 + 0.3 else 0)
        fr.splat(px_, py_, col * (1 - gsum * 0.4) + np.array(GOLD2) * gsum * 0.4, ap, 'E'); fr.splat(px_, py_, col, ap * 0.4, 'B')
    if t < t3 + 0.6: fr.glow((x0, y0 - 60), 180, GOLD2, max(0, 1 - (t - t3) / 0.6) * a)
    # 三个问题
    Q = [(q1, '这门生意，值多少钱？', CUE['q1_a']), (q2, '我可能错在哪？', CUE['q2_a']), (q3, '真错了，我输得起吗？', CUE['q3_a'])]
    for k, (ts, s, ta) in enumerate(Q):
        nxt = [q2, q3, tm][k]
        aq = a * env(t, ts - 0.1, nxt - 0.1, 0.4, 0.4)
        if aq <= 0: continue
        fr.text(['①', '②', '③'][k], CX, 300, 44, 'sans_black', GOLD, aq, mode='L', glow=0.3)
        deep_text(fr, t, s, CX, 400, 70, WHITE, aq, ts, glow=0.2)
        cx, cy = TOOL_C
        if k == 0:     # 天平：价格 ↔ 价值；算不出来 → 太难
            ac = aq * eo((t - ts - 0.6) / 0.5)
            fr.text('价格', cx - 260, cy + 60, 40, 'serif_black', WHITE, ac); fr.text('价值', cx + 260, cy + 60, 40, 'serif_black', GOLD, ac)
            fr.text('?', cx + 260, cy - 70, 60, 'serif_black', GOLD, ac * (0.6 + 0.4 * math.sin(t * 4)), mode='L', glow=0.4)
            if t > ta:
                ab = aq * eo((t - ta) / 0.4)
                fr.rrect(cx - 230, 1220, cx + 230, 1300, 40, GOLD, ab, 3)
                fr.text('算不出来 → 放进「太难」', cx, 1260, 38, 'sans_black', GOLD, ab, mode='L', glow=0.3)
        elif k == 1:   # 镜子：给自己的做空报告
            ac = aq * eo((t - ts - 0.8) / 0.5)
            x0_, y0_, x1_ = cx - 260, cy - 290, cx + 260
            fr.text('给自己的做空报告', cx, y0_ + 60, 50, 'serif_black', PAPER, ac)
            fr.text('如果三年后再跌一半，原因是？', cx, y0_ + 130, 32, 'sans_med', C(220, 200, 170), ac)
            for j in range(3):
                yk = y0_ + 250 + j * 120
                aj = ac * eo((t - ts - 1.0 - j * 0.15) / 0.3)
                fr.text('①②③'[j], x0_ + 50, yk, 44, 'sans_black', GOLD, aj)
                fr.line((x0_ + 90, yk + 26), (x1_ - 40, yk + 26), DIM, aj * 0.6, 1)
                if j < 2:
                    uw = eo((t - ta - 0.2 - j * 0.7) / 0.7)
                    if uw > 0:
                        xs = np.linspace(x0_ + 110, x0_ + 110 + (x1_ - x0_ - 170) * uw, 50)
                        ys = yk + 4 + np.sin(xs * 0.09 + j) * 9 * np.random.default_rng(j + 4).random(50) ** 0.5
                        fr.poly(np.stack([xs, ys], 1), C(240, 220, 170), aj * 0.9, 3)
                elif int(t * 2.5) % 2 == 0 and t > ta: fr.line((x0_ + 115, yk - 24), (x0_ + 115, yk + 24), WHITE, aj, 3)
            stamp(fr, t, '别买', cx + 170, cy + 250, 100, ta + 1.8, RED, -12, aq)
        else:          # 圆：能力圈；圈外进「太难」；看不懂 → 指数
            ac = aq * eo((t - ts - 0.8) / 0.5)
            fr.text('能力圈', cx, cy - 330, 40, 'serif_black', GOLD, ac, mode='L', glow=0.3)
            for j in range(5):
                x, y = cx + 120 * math.cos(j * 1.26), cy + 110 * math.sin(j * 1.26)
                fr.glow((x, y), 16, GOLD2, ac * 0.9); fr.circle((x, y), 7, GOLD2, ac, -1)
            r = np.random.default_rng(12); n = 60; ang_ = r.random(n) * 2 * math.pi; rad = 330 + r.random(n) * 140
            ox = np.clip(cx + rad * np.cos(ang_), 70, 1010); oy = np.clip(cy + rad * np.sin(ang_), 480, 1200)
            st = ta + r.random(n) * 1.6; uu = np.clip((t - st) / 0.9, 0, 1)
            bxs, bys = 860 + r.normal(0, 30, n), 1330 + r.normal(0, 8, n)
            xs = lerp(ox, bxs, veio(uu)); ys = lerp(oy, bys, veio(uu)) - np.sin(uu * math.pi) * 120
            fr.dots(xs, ys, C(170, 180, 210), ac, 1.5, 'L')
            ab = aq * eo((t - ta) / 0.4)
            fr.poly([(740, 1270), (760, 1370), (960, 1370), (980, 1270)], GOLD, ab, 4)
            fr.text('太难', 860, 1410, 40, 'serif_black', GOLD, ab, mode='L', glow=0.25)
            ai = aq * eo((t - CUE['q3_idx'] - 0.2) / 0.5)
            fr.rrect(100, 1290, 600, 1380, 45, TEAL, ai, 3); fr.rrect_fill(100, 1290, 600, 1380, 45, TEAL, ai * 0.12)
            fr.text('看不懂 → 低成本指数基金', 350, 1335, 36, 'sans_black', TEAL, ai, mode='L', glow=0.3)
    # 真正的安全边际：三件工具排成一行
    am = a * env(t, tm - 0.1, S['quote'] - 0.1, 0.5, 0.45)
    if am > 0:
        for k, nm in enumerate(['scale', 'mirror', 'circle']):
            segs = tool_segs(nm); s_ = 0.28; ox = 220 + k * 320 - TOOL_C[0] * s_; oy = 560 - TOOL_C[1] * s_
            ak = am * eo((t - tm - k * 0.2) / 0.5)
            for (p0, p1) in segs: fr.line((ox + p0[0] * s_, oy + p0[1] * s_), (ox + p1[0] * s_, oy + p1[1] * s_), GOLD, ak, 3)
            fr.text(['价格与价值', '反过来想', '能力圈'][k], 220 + k * 320, 700, 30, 'sans_med', GOLD, ak)
        btext(fr, t, '真正的安全边际', CX, 880, 64, 'serif_med', C(225, 220, 210), am, tm + 0.2)
        btext(fr, t, '不是保证自己永远正确', CX, 1010, 70, 'serif_black', WHITE, am, tm + 0.9, glow=0.1)
        btext(fr, t, '而是即使犯错，也输得起', CX, 1150, 84, 'serif_black', GOLD, am, CUE['mos2'], glow=0.45, grad=GOLDG)
        dust(fr, t, am * 1.4)

def scene_quote(fr, t):
    t0 = S['quote']; a = env(t, t0 - 0.2, S['outro'] - 0.1, 0.5, 0.5)
    if a <= 0: return
    fr.text('“', 140, 520, 170, 'serif_black', GOLD, a * 0.55, mode='L', glow=0.2)
    btext(fr, t, '对大多数投资者而言', CX, 660, 56, 'serif_med', C(225, 220, 210), a, t0 + 0.1)
    btext(fr, t, '重要的不是知道多少', CX, 790, 72, 'serif_black', WHITE, a, CUE['e1_b'], glow=0.1)
    btext(fr, t, '而是清醒地认识到', CX, 930, 64, 'serif_med', C(225, 220, 210), a, CUE['e1_c'])
    btext(fr, t, '自己不知道什么', CX, 1070, 96, 'serif_black', GOLD, a, CUE['e1_c'] + 1.2, glow=0.45, grad=GOLDG)
    fr.text('— 沃伦 · 巴菲特，1992 年致股东信', CX, 1220, 30, 'serif_med', C(200, 190, 170), a * eo((t - CUE['e1_c'] - 1.6) / 0.5))

def scene_outro(fr, t):
    t0 = S['outro']; a = env(t, t0 - 0.2, S['card'] + 0.3, 0.5, 0.5)
    if a <= 0: return
    c = CASES[0]; box = (130, 360, 910, 820)
    px, py = case_xf(c, box)
    draw_chart(fr, t, c, a * 0.6, 0, box, d=c['buy'][0], mini=False)
    fade = 1 - eio((t - CUE['e2_b']) / 2.0)
    stamp(fr, t, '买入', px(c['buy'][0]) + 70, py(c['buy'][1]) - 80, 58, t0, GOLD, -10, a * fade)
    btext(fr, t, '你以为自己学会了巴菲特', CX, 1000, 58, 'serif_med', C(225, 220, 210), a, t0 + 0.1)
    btext(fr, t, '可你学会的，是他的动作', CX, 1140, 70, 'serif_black', WHITE, a, CUE['e2_b'], glow=0.1)
    btext(fr, t, '还是他的思考？', CX, 1270, 96, 'serif_black', GOLD, a, CUE['e2_b'] + 1.4, glow=0.45, grad=GOLDG)

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
    fr.text('不构成投资建议 · 股价截至 2026.11.18 收盘（约数），中间走势为示意 · 芒格的提问为其思考方式的演绎', CX, 1720, 26, 'sans_light', DIM, a * 0.8)

# ================================================================ 字幕 / HUD / 合成
HIDE = {'H1', 'Q1', 'R5b', 'W3', 'W7', 'E1', 'E2'}
HIDE_CHUNK = {('R1a', 1), ('R2a', 1), ('R3a', 1), ('R4a', 2), ('R5a', 1), ('R1b', 0), ('R2b', 0), ('R3b', 0), ('R4b', 0),
              ('R5d', 4), ('R5e', 0), ('W1', 1), ('W1', 2), ('W2', 0), ('W2', 2), ('W4', 0), ('W5', 0), ('W6', 0)}
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

CHAPTERS = [(0, '01  好学生的困惑'), (S['rewind'] - 0.3, '02  倒带'), (S['wake'] - 0.5, '03  觉醒')]
def chapter(fr, t):
    lab = [l for t0, l in CHAPTERS if t >= t0][-1]
    a = 0.75 * (1 - eio((t - S['card'] + 0.5) / 0.5)) * eo((t - 0.6) / 0.5)
    fr.text(lab, 52, 92, 26, 'sans_med', C(200, 200, 210), a, anchor='l')

HUD = Hud(scale=1.0, frame_w=W)
CUTS = [S[k] for k in ('cases', 'ali', 'zp', 'nv', 'pivot', 'title', 'rewind', 'r1', 'r2', 'r3', 'r4', 'r5', 'tx', 'inv', 'wake',
                       'ibm', 'three', 'mos', 'quote', 'outro', 'card')]

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
    scene_pivot(fr, t); scene_title(fr, t); scene_rewind(fr, t)
    scene_r1(fr, t); scene_r2(fr, t); scene_r3(fr, t); scene_r4(fr, t); scene_r5(fr, t)
    if S['tx'] - 0.5 < t < S['wake'] + 0.5: scene_tx(fr, t); scene_inv(fr, t)
    if t > S['wake'] - 0.5:
        scene_wake(fr, t); scene_ibm(fr, t); scene_tools(fr, t); scene_quote(fr, t); scene_outro(fr, t); draw_card_text(fr, t)
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
