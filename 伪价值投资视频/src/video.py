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
S = TL['sections']; TOTAL = TL['total']; BEAT = TL['beat']
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
        (S['cases'] + 1, (C(30, 80, 120), C(3, 7, 12))), (L0('L07'), (C(90, 40, 60), C(8, 4, 8))),
        (L0('L12'), (C(30, 90, 70), C(3, 8, 7))), (L0('L13'), (C(30, 30, 40), C(2, 2, 4))),
        (S['pivot'] + 3, (C(60, 30, 30), C(5, 2, 3))), (S['title'], (C(140, 100, 40), C(8, 6, 3))),
        (S['munger'] + 1, (C(110, 80, 40), C(7, 5, 3))), (S['p2'], (C(60, 80, 130), C(4, 5, 10))),
        (S['p3'], (C(50, 100, 110), C(3, 7, 9))), (S['kill'], (C(150, 30, 30), C(9, 2, 3))),
        (S['cure'] - 0.5, (C(40, 40, 60), C(3, 3, 6))), (S['cure'] + 1.5, (C(70, 110, 170), C(5, 7, 13))),
        (L0('L28'), (C(170, 120, 50), C(9, 7, 4))), (S['card'], (C(60, 50, 30), C(3, 3, 3)))]

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
 dict(no='01', name='腾讯控股', sub='0700.HK · 港元', x0=2017.7, x1=2026.95, y0=120, y1=860, buy=(2018.22, 400),
      anchors=[(2017.7, 330), (2018.08, 476), (2018.22, 400), (2018.5, 380), (2018.83, 255), (2019.3, 395), (2019.65, 325),
               (2020.2, 380), (2020.55, 560), (2021.13, 775), (2021.6, 440), (2022.0, 470), (2022.4, 350), (2022.82, 190),
               (2023.08, 400), (2023.7, 310), (2024.1, 270), (2024.8, 410), (2025.3, 500), (2025.8, 650), (2026.05, 630),
               (2026.4, 520), (2026.81, 375)],
      peak=(2018.08, 476, '高点 476'), end=(2026.81, 375, '375'), grid=[200, 400, 600, 800],
      xl=[(2018.0, '2018'), (2022.0, '2022'), (2026.0, '2026')],
      t_in=L0('L04'), t_out=L0('L07') - 0.5, badge='-6%', cap='持有 8 年 · 原地踏步', seed=3,
      rev=[(L0('L04'), 2017.7), (L0('L04') + 1.9, 2018.08), (CH('L04', 1) - 0.1, 2018.22), (onset('L05') - 1.0, 2018.22), (onset('L05'), 2026.81)]),
 dict(no='02', name='阿里巴巴', sub='BABA · 美元', x0=2020.45, x1=2022.95, y0=20, y1=360, buy=(2021.68, 150),
      anchors=[(2020.45, 250), (2020.6, 270), (2020.82, 319), (2021.0, 222), (2021.15, 260), (2021.45, 210), (2021.6, 168),
               (2021.68, 150), (2021.82, 170), (2022.0, 120), (2022.2, 75), (2022.45, 118), (2022.62, 92), (2022.81, 60)],
      peak=(2020.82, 319, '高点 319'), end=(2022.81, 60, '≈60'), grid=[100, 200, 300],
      xl=[(2020.6, '2020'), (2021.5, '2021'), (2022.5, '2022')],
      t_in=L0('L07') - 0.25, t_out=L0('L09') - 0.5, badge='-60%', cap='腰斩之后，又跌六成', seed=8,
      rev=[(L0('L07'), 2020.45), (L0('L07') + 1.6, 2020.82), (CH('L07', 1) - 0.2, 2021.68), (onset('L08') - 0.9, 2021.68), (onset('L08'), 2022.81)]),
 dict(no='03', name='智谱', sub='2513.HK · 港元', x0=2026.38, x1=2026.9, y0=0, y1=3300, buy=(2026.57, 1500),
      anchors=[(2026.38, 620), (2026.43, 900), (2026.455, 1050), (2026.47, 2980), (2026.49, 2350), (2026.52, 1950),
               (2026.57, 1500), (2026.62, 1280), (2026.69, 980), (2026.77, 720), (2026.86, 430)],
      peak=(2026.47, 2980, '高点 2980'), end=(2026.86, 430, '<500'), grid=[1000, 2000, 3000],
      xl=[(2026.42, '2026.06'), (2026.84, '2026.11')],
      t_in=L0('L09') - 0.25, t_out=L0('L12') - 0.5, badge='≤-67%', cap='避开第一场腰斩，赶上后两场', seed=11,
      rev=[(L0('L09'), 2026.38), (L0('L09') + 1.7, 2026.47), (CH('L09', 1) - 0.3, 2026.57), (onset('L10') - 0.9, 2026.57), (onset('L10'), 2026.86)]),
 dict(no='04', name='英伟达', sub='NVDA · 美元', x0=2026.45, x1=2027.1, y0=110, y1=270, buy=(2026.885, 180),
      anchors=[(2026.45, 172), (2026.53, 188), (2026.6, 182), (2026.66, 206), (2026.72, 224), (2026.77, 240), (2026.81, 214),
               (2026.85, 196), (2026.885, 180)],
      peak=(2026.77, 240, '高点 ≈240'), end=None, grid=[150, 200, 250],
      xl=[(2026.5, '2026.07'), (2026.88, '现在'), (2027.05, '?')],
      t_in=L0('L12') - 0.25, t_out=S['pivot'] - 0.6, badge='?', cap='', seed=21,
      rev=[(L0('L12'), 2026.45), (CH('L12', 1), 2026.77), (CH('L12', 2) - 0.2, 2026.885)]),
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
    if m.sum() < 2: return
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
    def mark(xv, yv, lab, col, side=1, big=False, alpha=1.0):
        if d < xv - 1e-6: return
        u = cl((d - xv) / ((c['x1'] - c['x0']) * 0.03) + 0.0001) if xv < d else 1.0
        u = 1.0 if d >= xv else 0.0
        p = (px(xv), py(yv)); aa = a * alpha
        fr.circle(p, 9 if not mini else 6, col, aa, 2)
        fr.glow(p, 12, col, aa * 0.5)
        if not mini and lab:
            fr.text(lab, p[0] + 18 * side, p[1] - 30, 30 if not big else 34, 'sans_med', col, aa, anchor='l' if side > 0 else 'r')
    pk = c['peak']; mark(pk[0], pk[1], pk[2], C(200, 205, 220), 1)
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
            t6 = L0('L06')
            if t > t6:
                p0, p1 = (px(2018.22), py(400)), (px(2026.81), py(375))
                u = eo((t - t6) / 1.4)
                dashed(fr, p0, p1, GOLD, a * 0.9, 2, prog=u)
                if t > CH('L06', 1):
                    au = a * eo((t - CH('L06', 1)) / 0.5)
                    fx, fy = p1[0], p1[1] - 6
                    fr.line((fx, fy), (fx, fy - 70), GOLD, au, 3)
                    fr.fillpoly([(fx, fy - 70), (fx + 46, fy - 58), (fx, fy - 46)], GOLD, au * 0.9, 'E')
                    fr.text('目的地：提前 8 年到达', CX + dx, py(560), 36, 'sans_black', GOLD, au, mode='L', glow=0.2)
            # 八年快进：年份计数
            o5 = onset('L05')
            if o5 - 1.0 < t < o5 + 1.4:
                yr = int(keys(t, c['rev']))
                ay = a * env(t, o5 - 1.0, o5 + 1.4, 0.2, 0.4)
                fr.text(str(yr), 900 + dx, 520, 64, 'num', WHITE, ay * 0.85, anchor='r', mode='L', glow=0.2)
    # 阿里：回购
    c = CASES[1]
    if c['t_in'] - 0.1 < t < c['t_out'] + 0.6:
        r = case_scene(fr, t, c, 1)
        if r:
            px, py, a, dx = r
            tb = CH('L07', 1) + 0.3
            if t > tb:
                ab = a * eo((t - tb) / 0.4)
                x0, y0 = px(2021.68) + 40, py(150) - 150
                fr.rrect(x0, y0 - 30, x0 + 190, y0 + 30, 28, GOLD, ab * 0.9, 2)
                fr.text('大额回购 ✓', x0 + 95, y0, 30, 'sans_med', GOLD, ab)
    # 智谱：三场腰斩
    c = CASES[2]
    if c['t_in'] - 0.1 < t < c['t_out'] + 0.6:
        r = case_scene(fr, t, c, 2)
        if r:
            px, py, a, dx = r
            tb = CH('L09', 1)
            if t > tb:
                ab = a * eo((t - tb) / 0.4) * (1 - eio((t - L0('L11')) / 0.4))
                x0, y0 = px(2026.57) + 30, py(1500) - 120
                fr.rrect(x0, y0 - 30, x0 + 250, y0 + 30, 28, GOLD, ab * 0.9, 2)
                fr.text('泡沫挤干了？', x0 + 125, y0, 30, 'sans_med', GOLD, ab)
            t11 = L0('L11')
            if t > t11:
                xb = 985 + dx
                segs = [(2980, 1500, '①', DIM, t11, '避开'), (1500, 750, '②', RED2, CH('L11', 1), ''), (750, 375, '③', RED2, CH('L11', 1) + 0.45, '')]
                for hi, lo, lab, col, ts, note in segs:
                    if t < ts: continue
                    u = eo((t - ts) / 0.45); ya, yb = py(hi), py(lo)
                    fr.line((xb, ya), (xb, lerp(ya, yb, u)), col, a, 3)
                    fr.line((xb - 12, ya), (xb, ya), col, a * u, 3); fr.line((xb - 12, yb), (xb, yb), col, a * u, 3)
                    fr.text(lab, xb + 30, (ya + yb) / 2, 34, 'sans_black', col, a * u, mode='L', glow=0.2)
                    if note: fr.text(note, xb - 22, (ya + yb) / 2, 28, 'sans_med', col, a * u, anchor='r')
    # 英伟达：这一次，总该对了吧？
    c = CASES[3]
    if c['t_in'] - 0.1 < t < c['t_out'] + 0.6:
        r = case_scene(fr, t, c, 3)
        if r:
            px, py, a, dx = r
            for k, (lab, tt) in enumerate([('回调 25%', CH('L12', 1) + 0.6), ('明年 PE 13×', CH('L12', 2) + 0.5)]):
                if t > tt:
                    ab = a * eo((t - tt) / 0.35)
                    x0, y0 = 150 + dx, 1270 + k * 86
                    fr.rrect(x0, y0 - 32, x0 + 330, y0 + 32, 30, GOLD, ab * 0.9, 2)
                    fr.text(lab, x0 + 165, y0, 34, 'sans_black', GOLD, ab, mode='L', glow=0.15)
            t13 = L0('L13')
            if t > t13:
                aq = a * eo((t - t13) / 0.6)
                bx = px(2026.885)
                fr.rrect_fill(bx + 8, BY0, BX1 + dx, BY1, 8, C(30, 34, 50), aq * 0.5)
                for k in range(6):
                    yk = BY0 + 40 + k * 95
                    dashed(fr, (bx + 20, yk), (BX1 + dx - 10, yk), DIM, aq * 0.25, 1, 6, 12)
                pul = 0.75 + 0.25 * math.sin(t * 4)
                fr.text('?', (bx + BX1 + dx) / 2, (BY0 + BY1) / 2, 260, 'serif_black', WHITE, aq * pul, mode='L', glow=0.5)
                if int(t * 2.2) % 2 == 0:
                    fr.line((bx + 14, py(180) - 26), (bx + 14, py(180) + 26), WHITE, aq, 3)

# ================================================================ 场景
def scene_hook(fr, t):
    t1, t2, t3 = L0('L01'), L0('L02'), L0('L03')
    # 淡淡的作业本横线
    ah = env(t, 0, S['cases'] + 0.3, 1.0, 0.5)
    for k in range(18):
        y = 300 + k * 72
        fr.line((70, y), (W - 70, y), C(90, 110, 160), ah * 0.07, 1)
    fr.line((150, 260), (150, 1600), RED, ah * 0.08, 1)
    a1 = env(t, t1, t2 + 0.9, 0.3, 0.5)
    if a1 > 0:
        lift = eio((t - t2) / 0.9) * 60
        fr.text('在股市里', CX, 700 - lift, 58, 'serif_med', C(200, 205, 220), a1, t0=t1, mode='L')
        fr.text('亏得最惨的', CX, 840 - lift, 112, 'serif_black', WHITE, a1, t0=t1 + 0.6, mode='L', glow=0.12)
        tc = CH('L01', 1) + 0.6
        tw = text_width('往往不是赌徒', 'serif_black', 112)
        fr.text('往往不是', CX - tw / 2, 990 - lift, 112, 'serif_black', WHITE, a1, anchor='l', t0=tc, mode='L', glow=0.12)
        xg = CX - tw / 2 + text_width('往往不是', 'serif_black', 112)
        fr.text('赌徒', xg, 990 - lift, 112, 'serif_black', RED2, a1, anchor='l', t0=tc + 0.25, mode='L', glow=0.3)
        if t > t2:   # 划掉「赌徒」
            u = eo((t - t2) / 0.35)
            fr.line((xg - 10, 995 - lift), (xg - 10 + (text_width('赌徒', 'serif_black', 112) + 20) * u, 985 - lift), RED, a1, 6)
    a2 = env(t, t2 + 0.4, t3 - 0.1, 0.4, 0.5)
    if a2 > 0:
        tp = t2 + 0.55
        fr.text('而是', CX, 770, 60, 'serif_med', C(200, 205, 220), a2, t0=tp - 0.3)
        fr.text('最听话的', CX, 920, 120, 'serif_black', WHITE, a2, t0=tp, mode='L', glow=0.12)
        sc = 1 + 0.05 * (1 - eo((t - tp - 0.5) / 0.6))
        fr.text('好学生', CX, 1110, int(190 * sc), 'serif_black', GOLD, a2, t0=tp + 0.45, stag=0.08, mode='L', glow=0.55,
                grad=[GOLD2, GOLD, GOLDD])
    # 自检表
    a3 = env(t, t3 - 0.3, S['cases'] + 0.2, 0.4, 0.45)
    if a3 > 0:
        fr.text('股市好学生 · 自检表', CX, 520, 34, 'mono', GOLD, a3 * 0.9, track=0.2, t0=t3 - 0.3)
        items = ['不追高', '不碰垃圾股', '熟读巴菲特', '专门等回调']
        starts = [t3, P('L03', 0), P('L03', 1), P('L03', 2)]
        for k, (it, ts) in enumerate(zip(items, starts)):
            y = 680 + k * 150
            ai = a3 * eo((t - ts + 0.15) / 0.35)
            fr.rrect(250, y - 42, 334, y + 42, 12, C(200, 205, 225), ai * 0.7, 2)
            fr.text(it, 380, y, 70, 'serif_med', WHITE, ai, anchor='l')
            check(fr, 292, y, 70, (t - ts - 0.25) / 0.35, GOLD, ai, 6)
            if t > ts + 0.25: fr.glow((292, y), 30, GOLD, ai * 0.25 * math.exp(-(t - ts - 0.4) * 2))
        stamp(fr, t, '满分', 810, 1300, 120, L1('L03') + 0.3, RED, -14, a3)

def scene_pivot(fr, t):
    t0 = S['pivot']; a = env(t, t0 - 0.2, S['title'] + 0.05, 0.5, 0.15)
    if a <= 0: return
    hb = impact(t)
    boxes = [(80, 380, 520, 700), (560, 380, 1000, 700), (80, 760, 520, 1080), (560, 760, 1000, 1080)]
    caps = ['腾讯 -6% · 8年', '阿里 -60%', '智谱 ≤-67%', '英伟达 ?']
    for k, (c, b, cap) in enumerate(zip(CASES, boxes, caps)):
        ak = a * 0.55 * eo((t - t0 - k * 0.12) / 0.4)
        fr.rrect(b[0], b[1], b[2], b[3], 14, DIM, ak * 0.4, 1)
        d = c['rev'][-1][1]
        draw_chart(fr, t, c, ak, 0, (b[0] + 24, b[1] + 70, b[2] - 24, b[3] - 24), d=d, mini=True)
        fr.text(cap, (b[0] + b[2]) / 2, b[1] + 36, 30, 'sans_med', RED2 if k < 3 else WHITE, ak * 1.4)
    for k, (lab, ts) in enumerate(zip(['有研究', '有耐心', '有纪律'], [t0, P('L14', 0), P('L14', 1)])):
        x = 210 + k * 330
        ai = a * eo((t - ts) / 0.3)
        fr.text(lab, x + 30, 1200, 52, 'serif_med', WHITE, ai, anchor='m')
        check(fr, x - 70, 1200, 44, (t - ts - 0.15) / 0.3, GOLD, ai, 5)
    tq = CH('L14', 1)
    aq = a * eo((t - tq) / 0.35)
    sc = 1 + 0.03 * hb
    fr.text('那么，错在哪？', CX, 1370, int(110 * sc), 'serif_black', WHITE, aq, t0=tq, stag=0.06, mode='L', glow=0.3)

def scene_title(fr, t):
    t0 = S['title']; a = env(t, t0, S['munger'] + 0.2, 0.05, 0.5)
    if a <= 0: return
    u = t - t0
    # 冲击波
    for k, (spd, col) in enumerate([(1500, GOLD), (900, RED)]):
        r = spd * eo(u / 1.2) + 10
        aw = (1 - eo(u / 1.2)) * a
        fr.circle((CX, 900), r, col, aw * 0.6, 3)
        fr.glow((CX, 900), 60 + r * 0.1, col, aw * 0.15)
    # 粒子爆散
    rr = np.random.default_rng(42); n = 260
    ang = rr.random(n) * 6.283; spd = 150 + rr.random(n) * 900
    d = spd * (1 - np.exp(-u * 2.2)) / 2.2
    xs = CX + np.cos(ang) * d; ys = 900 + np.sin(ang) * d * 0.8 + u * u * 20
    fr.dots(xs, ys, GOLD2, np.exp(-u * 0.9) * 0.8 * a, 1, 'E')
    fr.text('一个「价投好学生」的困惑', CX, 680, 38, 'sans_light', C(200, 200, 210), a * eo((u - 0.4) / 0.5), track=0.1)
    sc = 1 + 0.08 * (1 - eo(u / 0.5))
    tw = text_width('伪价值投资', 'serif_black', int(176 * sc))
    x = CX - tw / 2
    fr.text('伪', x, 900, int(176 * sc), 'serif_black', RED2, a, anchor='l', mode='L', glow=0.6)
    x2 = x + glyph('伪', 'serif_black', int(176 * sc))[1]
    fr.text('价值投资', x2, 900, int(176 * sc), 'serif_black', GOLD, a, anchor='l', mode='L', glow=0.45, grad=[GOLD2, GOLD, GOLDD, GOLD])
    # 流光
    sw = (u - 0.6) / 1.2
    if 0 < sw < 1:
        sx = lerp(x - 100, x + tw + 100, eio(sw))
        fr.glow((sx, 900), 60, WHITE, a * 0.35 * math.sin(math.pi * sw))
    fr.line((CX - 200 * eo((u - 0.5) / 0.6), 1030), (CX + 200 * eo((u - 0.5) / 0.6), 1030), GOLD, a * 0.8, 2)
    fr.text('价值投资的三个幻觉', CX, 1110, 56, 'serif_med', WHITE, a, t0=t0 + 0.8, stag=0.05)
    fr.text('THREE ILLUSIONS OF VALUE INVESTING', CX, 1190, 28, 'corm_b', GOLD, a * 0.85, track=0.25, t0=t0 + 1.2, stag=0.01)

def scene_munger(fr, t):
    t0 = S['munger']; a = env(t, t0 - 0.2, S['p1'] + 0.1, 0.5, 0.4)
    if a <= 0: return
    fr.text('如果芒格在场', CX, 640, 64, 'serif_med', C(220, 220, 230), a, t0=t0)
    fr.text('CHARLIE MUNGER', CX, 760, 52, 'corm_b', GOLD, a, track=0.3, t0=t0 + 0.4, stag=0.03, mode='L', glow=0.3)
    fr.text('1924 — 2023', CX, 825, 28, 'mono', DIM, a, track=0.2, t0=t0 + 0.7)
    fr.text('他不会安慰你', CX, 960, 80, 'serif_black', WHITE, a, t0=P('L15', 0) - 0.1, mode='L', glow=0.12)
    tc = CH('L15', 1)
    fr.text('只会让你看清三件事', CX, 1090, 56, 'serif_med', C(220, 220, 230), a, t0=tc)
    for k in range(3):
        tk = tc + 1.0 + k * BEAT / 2
        ak = a * eo((t - tk) / 0.3)
        x = CX + (k - 1) * 200
        fr.circle((x, 1260), 56, GOLD, ak, 3)
        fr.glow((x, 1260), 40, GOLD, ak * 0.25)
        fr.text('①②③'[k], x, 1258, 64, 'sans_black', GOLD, ak, mode='L', glow=0.3)

def scene_p1(fr, t):
    t0 = S['p1']; a = env(t, t0 - 0.1, S['p2'] + 0.1, 0.4, 0.45)
    if a <= 0: return
    header(fr, t, 'ILLUSION 01', '跌得多 ≠ 便宜', a, t0, hl='≠')
    t17, t18 = L0('L17'), L0('L18')
    ax = 170; xr = 930
    py = lambda v: 1240 - v / 3200 * 680
    av = a * eo((t - t17 + 0.3) / 0.6)
    fr.line((ax, py(0)), (ax, py(3200)), DIM, av * 0.6, 2)
    for v in (0, 1000, 2000, 3000):
        fr.line((ax - 8, py(v)), (ax, py(v)), DIM, av * 0.6, 2)
        fr.text(str(v), ax - 16, py(v), 24, 'mono', DIM, av * 0.7, anchor='r')
    # 最高价：锚 —— 「股票不记得自己涨到过多高」后消散
    tf = P('L17', 0) - 0.6
    apk = av * (1 - 0.75 * eio((t - tf) / 0.8))
    dashed(fr, (ax, py(3000)), (xr, py(3000)), C(210, 210, 225), apk, 2, prog=eo((t - t17) / 0.7))
    fr.text('最高价 3000  ·  你心里的「锚」', ax + 20, py(3000) - 34, 32, 'sans_med', C(210, 210, 225), apk * eo((t - t17 - 0.3) / 0.4), anchor='l')
    if t > tf:
        rr = np.random.default_rng(3); n = 220
        xs = ax + rr.random(n) * (xr - ax); u = t - tf
        ys = py(3000) - u * (40 + rr.random(n) * 90)
        fr.splat(xs + np.sin(u * 3 + xs) * 6, ys, C(220, 220, 235), np.clip(1 - u / 2.2, 0, 1) * a * 0.9, 'E')
    # 现价 1500
    ap = av * eo((t - t17 - 0.4) / 0.5)
    fr.line((ax, py(1500)), (xr, py(1500)), WHITE, ap, 3)
    fr.text('现价 1500', ax + 20, py(1500) - 32, 34, 'sans_black', WHITE, ap, anchor='l')
    # 内在价值 300
    tv = CH('L17', 1)
    ai = a * eo((t - tv) / 0.5)
    fr.line((ax, py(300)), (ax + (xr - ax) * eo((t - tv) / 0.6), py(300)), GOLD, ai, 4)
    fr.glow((ax + (xr - ax) * eo((t - tv) / 0.6), py(300)), 20, GOLD, ai * 0.6)
    fr.text('内在价值 300', ax + 20, py(300) + 38, 36, 'sans_black', GOLD, ai, anchor='l', mode='L', glow=0.25)
    # 真正该量的距离（价格 ↔ 价值）
    tb = tv + 1.2
    if t > tb:
        u = eo((t - tb) / 0.6); xb = 820
        ya, yb = py(1500), py(300)
        fr.line((xb, ya), (xb, lerp(ya, yb, u)), GOLD, a, 4)
        fr.line((xb - 16, ya), (xb + 16, ya), GOLD, a * u, 4); fr.line((xb - 16, yb), (xb + 16, yb), GOLD, a * u, 4)
        fr.text('该量的', xb - 30, (ya + yb) / 2 - 22, 32, 'sans_black', GOLD, a * u, anchor='r')
        fr.text('距离', xb - 30, (ya + yb) / 2 + 22, 32, 'sans_black', GOLD, a * u, anchor='r')
    # 不是和最高价的距离
    tn = CH('L17', 2)
    if t > tn:
        u = eo((t - tn) / 0.5); xb = 560
        ya, yb = py(3000), py(1500)
        fr.line((xb, ya), (xb, lerp(ya, yb, u)), DIM, a, 3)
        cross(fr, xb, (ya + yb) / 2, 34, (t - tn - 0.4) / 0.5, RED, a, 6)
        fr.text('不是这段', xb + 50, (ya + yb) / 2, 34, 'sans_black', RED2, a * eo((t - tn - 0.6) / 0.4), anchor='l')
    # 5 倍
    t5 = CH('L18', 1)
    if t > t5:
        u = eo((t - t5) / 0.5)
        fr.text('贵了 5 倍', 430, (py(1500) + py(300)) / 2 + 10, int(84 + 20 * impact(t)), 'num', RED2, a * u, mode='L', glow=0.5)
    if t18 < t < t5:
        for v, lab in ((3000, '3000'), (1500, '1500'), (300, '300')):
            pass

def scene_p2(fr, t):
    t0 = S['p2']; a = env(t, t0 - 0.1, S['p3'] + 0.1, 0.4, 0.45)
    if a <= 0: return
    header(fr, t, 'ILLUSION 02', '低市盈率，可能是陷阱', a, t0)
    t20 = L0('L20'); c2, c3 = CH('L20', 1), CH('L20', 2)
    af = a * eo((t - t20) / 0.5)
    # 公式
    fr.text('PE', 300, 560, 72, 'num', WHITE, af, mode='L', glow=0.2)
    fr.text('=', 390, 560, 64, 'sans_med', DIM, af)
    fr.text('价格', 600, 515, 50, 'serif_black', WHITE, af)
    fr.line((480, 560), (720, 560), WHITE, af, 3)
    shrink = eio((t - c3 - 0.4) / 2.2)
    fr.text('利润', 600, 610, int(50 * (1 - 0.35 * shrink)), 'serif_black', GOLD if shrink < 0.5 else RED2, af)
    # 利润柱状图（周期）
    vals = [.36, .42, .5, .58, .67, .76, .86, .95, 1.0, .9, .78, .66, .56, .5]
    nb = len(vals); x0, x1, yb, hmax = 140, 940, 1240, 290
    bw = (x1 - x0) / nb
    for k, v in enumerate(vals):
        if k <= 8: ts = c2 - 0.6 + k * 0.12
        else: ts = c3 + 0.3 + (k - 9) * 0.38
        u = eo((t - ts) / 0.35)
        if u <= 0: continue
        col = GOLD if k == 8 else (RED2 if k > 8 else C(110, 140, 200))
        h = v * hmax * u; xa = x0 + k * bw + 6
        fr.rrect_fill(xa, yb - h, xa + bw - 12, yb, 4, col, a * (0.55 if k != 8 else 0.85))
        if k == 8: fr.glow((xa + bw / 2 - 6, yb - h), 30, GOLD, a * 0.4 * u)
    fr.line((x0, yb), (x1, yb), DIM, a * 0.6, 2)
    fr.text('行业利润（周期）', x0, yb + 40, 28, 'sans_med', DIM, a * eo((t - c2 + 0.6) / 0.4), anchor='l')
    tp = c2 + 0.3
    if t > tp:
        ap = a * eo((t - tp) / 0.4); xk = x0 + 8 * bw + bw / 2
        fr.text('周期顶点', xk, yb - hmax - 46, 34, 'sans_black', GOLD, ap, mode='L', glow=0.2)
        fr.line((xk, yb - hmax - 22), (xk, yb - hmax + 6), GOLD, ap, 2)
    # PE 读数
    tr = c2 + 1.2
    if t > tr:
        ar = a * eo((t - tr) / 0.4)
        pe = counter(t, c3 + 0.6, L1('L20') - 0.95, 13, 26) if t > c3 + 0.6 else 13
        bad = pe > 14
        col = lerpc(GOLD, RED2, cl((pe - 13) / 6))
        fr.text(f'{pe:.0f}×', CX, 735, int(150 + 30 * impact(t) * (pe > 25)), 'num', col, ar, mode='L', glow=0.5)
        fr.text('股价不变，利润腰斩' if bad else '看着很便宜', CX, 830, 36, 'sans_med', C(210, 210, 220), ar)
    # 严谨的注脚
    tn = c3 + 2.0
    fr.text('注：不是断言谁已见顶，而是先问一句——这份利润，能持续吗？', CX, 1330, 28, 'sans_light', C(190, 190, 200),
            a * eo((t - tn) / 0.6))

def scene_p3(fr, t):
    t0 = S['p3']; a = env(t, t0 - 0.1, S['kill'] + 0.1, 0.4, 0.45)
    if a <= 0: return
    header(fr, t, 'ILLUSION 03', '好赛道 ≠ 好回报', a, t0, hl='≠')
    t22 = L0('L22'); c2, c3 = CH('L22', 1), CH('L22', 2); t23 = L0('L23')
    cols, rows = 50, 40; x0, y0, sp = 148, 560, 16
    rr = np.random.default_rng(9)
    order = rr.random(cols * rows)
    keep = np.zeros(cols * rows, bool); keep[[612, 1037, 1544]] = True
    gx = x0 + (np.arange(cols * rows) % cols) * sp
    gy = y0 + (np.arange(cols * rows) // cols) * sp
    # 出现：波浪
    ua = np.clip((t - c2 + 0.2 - (gy - y0) / 640 * 0.9 - order * 0.2) / 0.3, 0, 1)
    # 消失：随机
    die = np.clip((t - c3 - 0.2 - order * 1.0) / 0.3, 0, 1) * (~keep)
    al = ua * (1 - die)
    a_out = 1 - eio((t - t23) / 0.6)
    fr.dots(gx, gy, C(160, 185, 240), al * a * 0.9 * a_out, 1, 'L')
    fr.splat(gx, gy, C(150, 175, 230), al * a * 0.5 * a_out, 'B')
    # 「汽车改变了世界」：一条前进的公路光线
    ar = a * env(t, t22, c2 + 0.3, 0.3, 0.4)
    if ar > 0:
        u = eo((t - t22) / 1.0)
        for k in range(5):
            yk = 760 + k * 90
            fr.line((140, yk), (140 + 800 * u, yk), C(150, 175, 230), ar * (0.6 - k * 0.08), 2)
        fr.glow((140 + 800 * u, 940), 40, GOLD, ar * 0.6)
    if t > c3 - 0.1:
        ak = a * eo((t - c3 - 0.9) / 0.5) * a_out
        names = ['通用', '福特', '克莱斯勒']
        for k, idx in enumerate(np.where(keep)[0]):
            fr.glow((gx[idx], gy[idx]), 16, GOLD, ak * 0.9)
            fr.circle((gx[idx], gy[idx]), 7, GOLD2, ak, -1)
            fr.text(names[k], gx[idx], gy[idx] - 34, 30, 'sans_black', GOLD, ak, mode='L', glow=0.2)
    if t > c2:
        n = 2000 if t < c3 + 0.2 else counter(t, c3 + 0.2, L1('L22') - 0.8, 2000, 3)
        an = a * eo((t - c2) / 0.4) * a_out
        col = WHITE if n > 1000 else lerpc(RED2, GOLD, cl((50 - n) / 47))
        fr.text(f'{n:.0f}', 380, 1330, 120, 'num', col, an, mode='L', glow=0.35)
        fr.text('家车企' if n > 3.5 else '家活下来', 560, 1340, 44, 'serif_black', col, an, anchor='l')
        fr.text('巴菲特 · 1999', 560, 1395, 26, 'mono', DIM, an * 0.8, anchor='l')
    # 资本涌入，利润被卷没
    a3 = a * env(t, t23, S['kill'] + 0.2, 0.4, 0.4)
    if a3 > 0:
        u = t - t23
        rr2 = np.random.default_rng(13); n = 500
        sx = rr2.random(n) * W; sy = 300 + rr2.random(n) * 1400
        ph = (u * (0.35 + rr2.random(n) * 0.5) + rr2.random(n)) % 1.0
        tx, ty = CX, 900
        xs = lerp(sx, tx, ph ** 1.5); ys = lerp(sy, ty, ph ** 1.5)
        fr.dots(xs, ys, C(120, 200, 255), a3 * (1 - ph) * 0.8 * eo(u / 0.8), 1, 'E')
        bw = 520 * (1 - eio((u - 1.2) / 2.6))
        fr.rrect_fill(CX - bw / 2, 1100, CX + bw / 2, 1160, 8, GOLD, a3 * 0.85, 'E')
        fr.text('行业利润', CX, 1060, 36, 'sans_black', GOLD, a3)
        if u > 3.2: fr.text('被卷没', CX, 1230, 52, 'serif_black', RED2, a3 * eo((u - 3.2) / 0.4), mode='L', glow=0.3)
        fr.text('资本 · 人才 · 产能', CX, 640, 44, 'serif_med', C(150, 210, 255), a3 * eo((u - 0.3) / 0.5))
        ab = a3 * 0  # placeholder

def scene_kill(fr, t):
    t0 = S['kill']; a = env(t, t0 - 0.1, S['cure'] - 0.6, 0.4, 0.8)
    if a <= 0: return
    tq = CH('L24', 1)
    th = [h for h, s in HITS if abs(h - (L1('L24') - 1.1)) < 0.05][0]
    chips = ['护城河', '回购', '低估值']
    ts = [t0 + 0.9, t0 + 1.9, t0 + 2.75]
    for k, (lab, tk) in enumerate(zip(chips, ts)):
        ak = a * eo((t - tk) / 0.35)
        y = 620 + k * 150
        shake = 0
        if t > th:
            shake = math.sin(t * 60 + k) * 8 * math.exp(-(t - th) * 5)
            fall = eio((t - th - 0.2) / 1.6) * (180 + k * 60)
            ak *= 1 - 0.6 * eio((t - th) / 1.2)
            y += fall
        x0 = 300 + shake
        fr.rrect(x0, y - 50, x0 + 480, y + 50, 50, GOLD, ak * 0.9, 3)
        fr.rrect_fill(x0, y - 50, x0 + 480, y + 50, 50, GOLD, ak * 0.08)
        fr.text(lab, x0 + 240, y, 58, 'serif_black', GOLD, ak, mode='L', glow=0.2)
        check(fr, x0 + 420, y, 40, (t - tk - 0.2) / 0.3, GOLD, ak, 5)
        if t > th:
            r = np.random.default_rng(k)
            pts = [(x0 + 60 + j * 70, y - 50 + r.random() * 100) for j in range(6)]
            fr.poly(pts, RED, ak * eo((t - th) / 0.15), 3)
    fr.text('却从没问过', CX, 1130, 52, 'serif_med', C(220, 200, 200), a * eo((t - tq) / 0.4))
    tk2 = th - 0.9
    sc = 1 + 0.06 * impact(t)
    fr.text('什么，会杀死它？', CX, 1280, int(108 * sc), 'serif_black', RED2, a * eo((t - tk2) / 0.3), t0=tk2, stag=0.07,
            mode='L', glow=0.5)

def mirror_text(fr, t, s, y, size, a, col, t0):
    m = line_mask(s, 'serif_black', size)
    blit_mask(fr, m, CX, y, col, a * eo((t - t0) / 0.5), 'E', 0.2)
    u = eo((t - t0 - 0.55) / 0.9)
    if u <= 0: return
    r = m[::-1].copy()
    h = r.shape[0]
    fade = np.linspace(0.75, 0.0, h)[:, None] ** 1.3
    rows = np.arange(h)
    shift = (np.sin(rows * 0.18 - t * 5) * 4 * (rows / h)).astype(np.int32)
    rw = np.zeros_like(r)
    for k in range(h): rw[k] = np.roll(r[k], shift[k])
    yc = y + h * 0.82
    blit_mask(fr, rw * fade, CX, yc, GOLD, a * u, 'E', 0.35)

def scene_cure(fr, t):
    t0 = S['cure']
    # L25 反过来想（倒影）
    a = env(t, t0 - 0.2, L0('L26') - 0.1, 0.4, 0.45)
    if a > 0:
        fr.text('芒格说', CX, 640, 46, 'serif_med', GOLD, a, t0=t0)
        mirror_text(fr, t, '反过来想', 840, 150, a, WHITE, t0 + 0.4)
        ti = P('L25', 0)
        fr.text('总是反过来想', CX, 1180, 62, 'serif_med', WHITE, a, t0=ti, stag=0.05)
        fr.text('INVERT, ALWAYS INVERT.', CX, 1270, 36, 'corm_b', GOLD, a * 0.9, track=0.2, t0=ti + 0.5, stag=0.01)
    # L26 做空报告
    t26 = L0('L26'); a = env(t, t26 - 0.2, L0('L27') - 0.1, 0.45, 0.45)
    if a > 0:
        yo = (1 - eo((t - t26 + 0.2) / 0.6)) * 80
        x0, y0, x1, y1 = 140, 470 + yo, 940, 1370 + yo
        fr.rrect_fill(x0, y0, x1, y1, 18, C(30, 28, 24), a * 0.9, 'L')
        fr.rrect(x0, y0, x1, y1, 18, GOLD, a * 0.6, 2)
        fr.text('SHORT REPORT', CX, y0 + 70, 26, 'mono', GOLD, a * 0.8, track=0.4)
        fr.text('给自己的做空报告', CX, y0 + 150, 66, 'serif_black', PAPER, a)
        c2, c3 = CH('L26', 1), CH('L26', 2)
        fr.text('如果三年后再跌 50%，原因是？', CX, y0 + 250, 40, 'sans_med', C(220, 200, 170), a * eo((t - c2) / 0.4))
        for k in range(3):
            yk = y0 + 380 + k * 150
            ak = a * eo((t - c2 - 0.3 - k * 0.15) / 0.3)
            fr.text('①②③'[k], x0 + 80, yk, 50, 'sans_black', GOLD, ak)
            fr.line((x0 + 130, yk + 30), (x1 - 70, yk + 30), DIM, ak * 0.6, 1)
            if k < 2:   # 前两条「写」上
                tw = c2 + 1.0 + k * 0.9
                u = eo((t - tw) / 0.8)
                if u > 0:
                    xs = np.linspace(x0 + 150, x0 + 150 + (x1 - x0 - 260) * u, 60)
                    rr = np.random.default_rng(k + 4)
                    ys = yk + 4 + np.sin(xs * 0.09 + k) * 10 * rr.random(60) ** 0.5
                    fr.poly(np.stack([xs, ys], 1), C(240, 220, 170), ak * 0.9, 3)
            else:
                if int(t * 2.5) % 2 == 0 and t > c2 + 1.5:
                    fr.line((x0 + 155, yk - 26), (x0 + 155, yk + 26), WHITE, ak, 3)
        stamp(fr, t, '别买', 760, y1 - 160, 120, c3 + 0.55, RED, -12, a)
    # L27 三个篮子
    t27 = L0('L27'); a = env(t, t27 - 0.2, L0('L28') - 0.1, 0.45, 0.45)
    if a > 0:
        bx = [(110, 360, '能投', 'IN', TEAL), (390, 640, '不投', 'OUT', DIM), (670, 970, '太难', 'TOO HARD', GOLD)]
        yb = 1060
        for k, (xa, xb_, zh, en, col) in enumerate(bx):
            ak = a * eo((t - t27 - k * 0.12) / 0.4)
            big = k == 2
            fr.poly([(xa, yb - 150), (xa + 20, yb), (xb_ - 20, yb), (xb_, yb - 150)], col, ak * (1 if big else 0.6), 4 if big else 2)
            fr.text(zh, (xa + xb_) / 2, yb + 60, 52 if big else 44, 'serif_black', col, ak, mode='L', glow=0.25 if big else 0)
            fr.text(en, (xa + xb_) / 2, yb + 115, 24, 'mono', col, ak * 0.8, track=0.2)
        items = ['大模型', '算力芯片', '动力电池', '周期矿业']
        for k, it in enumerate(items):
            ts = t27 + 0.5 + k * 0.42
            u = (t - ts) / 0.7
            if u <= 0: continue
            sx = 220 + k * 210; sy = 560
            ex = 820; ey = yb - 38 - k * 40
            x = lerp(sx, ex, eio(u)); y = lerp(sy, ey, eio(u)) - math.sin(cl(u) * math.pi) * 120
            sc = 1 - 0.45 * eio(u)
            fr.rrect(x - 95 * sc, y - 34 * sc, x + 95 * sc, y + 34 * sc, 20 * sc, WHITE, a * 0.8, 2)
            fr.text(it, x, y, int(40 * sc), 'sans_black', WHITE, a)
        ti = CH('L27', 1)
        ai = a * eo((t - ti - 0.3) / 0.5)
        fr.rrect(330, 1280, 750, 1380, 50, TEAL, ai, 3)
        fr.rrect_fill(330, 1280, 750, 1380, 50, TEAL, ai * 0.12)
        fr.text('看不懂 → 指数基金', CX, 1330, 46, 'sans_black', TEAL, ai, mode='L', glow=0.3)
    # L28 结语
    t28 = L0('L28'); a = env(t, t28 - 0.2, S['end'] - 0.1, 0.5, 0.45)
    if a > 0:
        fr.text('价值投资最难的', CX, 660, 60, 'serif_med', C(220, 215, 205), a, t0=t28)
        fr.text('从来不是等到便宜', CX, 800, 84, 'serif_black', WHITE, a * (1 - 0.55 * eio((t - CH('L28', 1)) / 0.6)), t0=t28 + 0.9)
        tw = text_width('从来不是等到便宜', 'serif_black', 84)
        if t > CH('L28', 1) - 0.4:
            u = eo((t - CH('L28', 1) + 0.4) / 0.5)
            fr.line((CX - tw / 2 - 10, 805), (CX - tw / 2 - 10 + (tw + 20) * u, 795), GOLD, a, 5)
        tc = CH('L28', 1)
        fr.text('而是', CX, 960, 56, 'serif_med', C(220, 215, 205), a, t0=tc)
        fr.text('知道自己', CX, 1110, 128, 'serif_black', GOLD, a, t0=tc + 0.5, stag=0.07, mode='L', glow=0.4, grad=[GOLD2, GOLD, GOLDD])
        fr.text('不知道什么', CX, 1270, 128, 'serif_black', GOLD, a, t0=tc + 1.1, stag=0.07, mode='L', glow=0.4, grad=[GOLD2, GOLD, GOLDD])
        dust(fr, t, a * 1.5)

def scene_end(fr, t):
    t0 = S['end']; a = env(t, t0 - 0.2, S['card'] + 0.3, 0.4, 0.5)
    if a > 0:
        fr.text('这几个坑，你踩过几个？', CX, 560, 76, 'serif_black', WHITE, a, t0=t0, stag=0.04, mode='L', glow=0.15)
        traps = ['拿最高价当安全边际', '用巅峰利润算低 PE', '把好赛道当好生意', '从没写过做空报告']
        for k, s in enumerate(traps):
            ak = a * eo((t - t0 - 0.4 - k * 0.22) / 0.35)
            y = 760 + k * 130
            fr.rrect(190, y - 34, 258, y + 34, 10, GOLD, ak * 0.9, 3)
            fr.text(s, 300, y, 54, 'serif_med', WHITE, ak, anchor='l')
        fr.text('评论区，说说你的故事', CX, 1360, 40, 'sans_med', GOLD, a * eo((t - t0 - 1.4) / 0.5))

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
    fr.text('不构成投资建议 · 股价为公开行情约数，走势为示意', CX, 1720, 26, 'sans_light', DIM, a * 0.8)

# ================================================================ 字幕 / HUD / 合成
HIDE = {'L01', 'L02', 'L03', 'L14', 'L16', 'L19', 'L21', 'L25', 'L28', 'L29', 'L15'}
HIDE_CHUNK = {('L24', 1)}
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
            # 柔和描边阴影
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
                post_text(out, s, CX, y, size, 'sans_med', a,
                          lambda ch: GOLD2 if ch in GOLD_CH else (0.96, 0.96, 0.97))

def chapter(fr, t):
    if t < S['title']: lab = '01  好学生的困惑'
    elif t < S['cure']: lab = '02  芒格的三刀'
    else: lab = '03  解药'
    a = 0.75 * (1 - eio((t - S['card'] + 0.5) / 0.5)) * eo((t - 0.6) / 0.5)
    fr.text(lab, 52, 92, 26, 'sans_med', C(200, 200, 210), a, anchor='l')

HUD = Hud(scale=1.0, frame_w=W)

def render(t):
    fr = Frame(t)
    bg = background(t)
    imp = impact(t, 0.85)
    dust(fr, t, 0.6)
    scene_hook(fr, t)
    if S['cases'] - 0.5 < t < S['pivot'] + 0.5: scene_cases(fr, t)
    scene_pivot(fr, t); scene_title(fr, t); scene_munger(fr, t)
    scene_p1(fr, t); scene_p2(fr, t); scene_p3(fr, t); scene_kill(fr, t)
    scene_cure(fr, t); scene_end(fr, t); draw_card_text(fr, t)
    chapter(fr, t)
    fr.flash = 0.035 * imp
    big = impact(t, 1.3)
    fr.ca = 4 * big
    out = finish(fr, bg, bloom_k=1.0 + 0.8 * imp, vignette=VIG, grain=GRAIN[int(t * 30) % 6])
    scene_card(fr, t, out)
    # 镜头：缓慢呼吸 + 重拍推近
    z = 1.0 + 0.012 * math.sin(t * 0.4) + 0.025 * impact(t)
    if abs(z - 1) > 1e-4:
        M = cv2.getRotationMatrix2D((W / 2, H * 0.45), 0, z)
        out = cv2.warpAffine(out, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    # 顶部进度条
    p = t / TOTAL
    out[0:5, :int(W * p)] = out[0:5, :int(W * p)] * 0.3 + np.array(GOLD, np.float32) * 0.7
    subtitles(out, t)
    out = np.clip(out, 0, 1)
    HUD.draw(out, t)
    # 首尾黑场
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
                               '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17',
                               '-pix_fmt', 'yuv420p', outp], stdin=subprocess.PIPE)
        for f in range(f0, f1):
            pr.stdin.write(render(f / FPS).tobytes())
        pr.stdin.close(); pr.wait()
