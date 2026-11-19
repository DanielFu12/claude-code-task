"""《好公司，为什么还会亏？》竖屏 1080×1920 分镜（V7）。所有时间点读自 work/timeline.json（旁白排在 80BPM 网格上）。
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
MOOD = [(0, (C(40, 70, 140), C(4, 6, 14))), (S['tencent'], (C(30, 80, 120), C(3, 7, 12))), (S['catl'], (C(40, 90, 80), C(3, 7, 6))),
        (S['ali'], (C(90, 40, 60), C(8, 4, 8))), (S['zp'], (C(60, 70, 120), C(4, 4, 10))), (S['gold'], (C(130, 100, 40), C(7, 5, 2))),
        (S['nv'], (C(30, 90, 70), C(3, 8, 7))), (S['wall'], (C(60, 30, 30), C(5, 2, 3))), (S['title'], (C(140, 100, 40), C(8, 6, 3))),
        (S['q1_card'], (C(120, 90, 40), C(6, 5, 3))), (S['anchor'], (C(50, 60, 100), C(3, 4, 8))), (S['tenyear'], (C(60, 80, 130), C(4, 5, 10))),
        (S['ibm'], (C(50, 50, 80), C(3, 3, 7))), (S['story'], (C(40, 60, 120), C(3, 4, 10))), (S['capital'], (C(70, 40, 60), C(5, 3, 5))),
        (S['stair'], (C(40, 90, 90), C(3, 7, 7))), (S['expect'], (C(60, 70, 110), C(4, 4, 9))), (S['post2'], (C(120, 80, 30), C(7, 5, 2))),
        (S['hammer'], (C(150, 70, 30), C(8, 4, 2))), (S['verdict'], (C(40, 40, 60), C(2, 2, 4))), (S['inv'], (C(110, 50, 40), C(6, 3, 3))),
        (S['q2_card'], (C(50, 60, 90), C(3, 4, 7))), (S['band'], (C(60, 90, 120), C(4, 6, 9))), (S['line'], (C(70, 80, 110), C(4, 5, 8))),
        (S['q3_card'], (C(170, 120, 50), C(9, 7, 4))), (S['principles'], (C(120, 100, 60), C(6, 5, 3))), (S['finale'], (C(180, 130, 50), C(10, 7, 4))),
        (S['epilogue'], (C(70, 80, 120), C(4, 5, 9))), (S['last'], (C(140, 110, 60), C(7, 6, 4))), (S['card'], (C(60, 50, 30), C(3, 3, 3)))]

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

def _t(i): return LN[i]['t0']
# 关键价位为公开行情约数（截至 2026.11.18 / 19），中间路径为示意
CASES = [
 dict(no='01', name='腾讯控股', sub='0700.HK · 港元 · 截至 2026.11.18', x0=2017.7, x1=2026.95, y0=120, y1=860, buy=(2018.22, 400),
      anchors=[(2017.7, 330), (2018.08, 476), (2018.22, 400), (2018.5, 380), (2018.83, 255), (2019.3, 395), (2019.65, 325),
               (2020.2, 380), (2020.55, 560), (2021.13, 775), (2021.6, 440), (2022.0, 470), (2022.4, 350), (2022.82, 190),
               (2023.08, 400), (2023.7, 310), (2024.1, 270), (2024.8, 410), (2025.3, 500), (2025.8, 650), (2026.05, 630),
               (2026.4, 520), (2026.81, 375), (2026.85, 430), (2026.88, 373)],
      peak=(2018.08, 476, '高点 476'), end=(2026.88, 373, '373'), grid=[200, 400, 600, 800],
      xl=[(2018.0, '2018'), (2022.0, '2022'), (2026.0, '2026')], badge='-7%', cap='8 年 · 股价仍低于买入价（不含分红）', seed=3,
      t_in=_t('L03') - 0.2, t_out=S['unwilling'] - 0.5, t_buy=_t('L04') - 0.6,
      rev=[(_t('L03') + 0.3, 2017.7), (_t('L03') + 2.6, 2018.08), (_t('L03') + 3.8, 2018.22), (CUE['L04'] - 1.1, 2018.22), (CUE['L04'], 2026.88)]),
 dict(no='02', name='宁德时代', sub='300750.SZ · 人民币 · 截至 2026.11.19', x0=0.0, x1=1.0, y0=150, y1=520, buy=(0.52, 328),
      anchors=[(0.0, 300), (0.12, 330), (0.25, 390), (0.36, 468.75), (0.44, 410), (0.52, 328), (0.6, 345), (0.7, 300), (0.82, 268),
               (0.92, 248), (1.0, 235)],
      peak=(0.36, 468.75, '52 周高点 469'), end=(1.0, 235, '235'), grid=[200, 300, 400, 500],
      xl=[(0.36, '高点'), (0.52, '跌三成'), (0.95, '又跌三成')], badge='-29%', cap='从高点跌三成买入，又跌了三成', seed=31,
      t_in=_t('L07') - 0.2, t_out=S['ali'] - 0.5, t_buy=_t('L07') + 4.4,
      rev=[(_t('L07') + 0.2, 0.0), (_t('L07') + 1.6, 0.36), (_t('L07') + 4.2, 0.52), (CUE['L07'] - 1.0, 0.52), (CUE['L07'], 1.0)]),
 dict(no='03', name='阿里巴巴', sub='BABA · 美元 · 截至 2026.11.18', x0=2020.45, x1=2026.95, y0=20, y1=360, buy=(2021.68, 150),
      anchors=[(2020.45, 250), (2020.82, 319), (2021.0, 222), (2021.15, 260), (2021.45, 210), (2021.6, 168), (2021.68, 150),
               (2021.85, 165), (2022.0, 120), (2022.2, 75), (2022.45, 118), (2022.62, 92), (2022.81, 63), (2023.08, 118),
               (2023.5, 95), (2023.95, 72), (2024.1, 68), (2024.75, 108), (2025.15, 140), (2025.3, 105), (2025.6, 120),
               (2025.78, 185), (2026.0, 147), (2026.4, 125), (2026.7, 115), (2026.84, 107), (2026.88, 84)],
      peak=(2020.82, 319, '高点 319'), end=(2022.81, 63, '63'), grid=[100, 200, 300], marks=[],
      xl=[(2021.0, '2021'), (2022.81, '2022.10'), (2025.0, '2025')], badge='', cap='', seed=8,
      t_in=_t('L08') - 0.2, t_out=S['zp'] - 0.5, t_buy=_t('L08') + 2.2,
      rev=[(_t('L08') + 0.2, 2020.45), (_t('L08') + 1.5, 2020.82), (_t('L08') + 2.6, 2021.68), (CUE['L08'] - 1.0, 2021.68), (CUE['L08'], 2022.81)]),
 dict(no='04', name='智谱', sub='2513.HK · 港元 · 截至 2026.11.18', x0=2026.38, x1=2026.92, y0=0, y1=3300, buy=(2026.57, 1500),
      anchors=[(2026.38, 620), (2026.43, 900), (2026.455, 1050), (2026.47, 2980), (2026.49, 2350), (2026.52, 1950),
               (2026.57, 1500), (2026.62, 1280), (2026.69, 980), (2026.77, 720), (2026.83, 442), (2026.86, 408),
               (2026.875, 335), (2026.88, 367)],
      peak=(2026.47, 2980, '高点 2980'), end=(2026.88, 367, '367'), grid=[1000, 2000, 3000],
      xl=[(2026.42, '2026.06'), (2026.86, '2026.11')], badge='-76%', cap='1500 → 367', seed=11,
      t_in=_t('L09') - 0.2, t_out=S['gold'] - 0.5, t_buy=_t('L09') + 5.0,
      rev=[(_t('L09') + 1.4, 2026.38), (_t('L09') + 3.2, 2026.47), (_t('L09') + 5.0, 2026.57), (CUE['L09'] - 1.0, 2026.57), (CUE['L09'], 2026.88)]),
 dict(no='05', name='英伟达', sub='NVDA · 美元 · 截至 2026.11.18', x0=2026.45, x1=2026.93, y0=120, y1=260, buy=(2026.85, 180),
      anchors=[(2026.45, 172), (2026.53, 188), (2026.6, 182), (2026.66, 206), (2026.72, 224), (2026.77, 240), (2026.81, 214),
               (2026.835, 196), (2026.85, 180), (2026.86, 186), (2026.87, 162), (2026.875, 155), (2026.88, 151)],
      peak=(2026.77, 240, '高点 ≈240'), end=(2026.88, 151, '151'), grid=[150, 200, 250],
      xl=[(2026.5, '2026.07'), (2026.86, '2026.11')], badge='-16%', cap='AI 需求还在，股价继续下跌', seed=21,
      t_in=_t('L13'), t_out=S['wall'] - 0.5, t_buy=_t('L13') + 2.4,
      rev=[(_t('L13') + 0.1, 2026.45), (_t('L13') + 1.3, 2026.77), (_t('L13') + 2.3, 2026.85), (CUE['L13'] - 1.0, 2026.85), (CUE['L13'], 2026.88)]),
]

for c in CASES:
    c['X'], c['Y'] = make_series(c['anchors'], seed=c['seed'])
CASES[0]['segs'] = [((2018.22, 400), (2026.88, 373))]                       # 腾讯：买点→现价的虚线
CASES[2]['chip'] = ('大笔回购 ✓', 30)
CASES[4]['avoid'] = [(260 - 130, 640 - 30, 260 + 130, 640 + 30)]          # 英伟达：AI 需求还在
CASES[3]['avoid'] = [(885, 480, 1000, 1160)]                               # 智谱：右侧①②③腰斩标注

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
            lx, ly = chart_layout(c, box, (64 if box == (BX0, BY0, BX1, BY1) else 58))['label']
            if math.hypot(lx - p[0] + dx, ly - p[1]) > 75:      # 标签离买点较远时，用细引线连回去
                q = (lx + dx, ly - 22 if ly > p[1] else ly + 22)
                v = np.array(q) - np.array(p); v = v / (np.linalg.norm(v) + 1e-6)
                dashed(fr, (p[0] + v[0] * 16, p[1] + v[1] * 16), q, GOLD, a * 0.6, 2, 8, 7)
            fr.text('你的买点 ' + str(bv), lx + dx, ly, 32, 'sans_black', GOLD, a, mode='L', glow=0.2)
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
    fr.text('CASE ' + c['no'] + ' / 05', CX + dx, 250, 28, 'mono', GOLD, a * 0.85, track=0.3)
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


GOLDG = (GOLD2, GOLD, GOLDD, GOLD)

def veio(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)

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

_btext_raw = btext
def btext(fr, t, s, x, y, size, fnt, col, a, t0, **kw):
    """自动适配宽度：超过 960px 就缩小字号，杜绝出画/重叠"""
    while size > 24 and text_width(s, fnt, size) > 960: size -= 2
    return _btext_raw(fr, t, s, x, y, size, fnt, col, a, t0, **kw)

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

# ================================================================ V7 · 版式分区（防重叠）
# 顶栏 0-150：品牌角标/章节；标签区 230-280；标题区 330-560；主视觉区 600-1330；注脚区 1380-1450；字幕区 1500-1620
ZT, ZB, ZC0, ZC1, ZD = 250, 450, 600, 1330, 1420
ORDER = sorted([(v, k) for k, v in S.items() if k not in ('card',) and not k.endswith('_card')] +
               [(S[k + '_card'], k + '_card') for k in ('q1', 'q2', 'q3')] + [(S['card'], 'card')])
NEXT = {ORDER[i][1]: (ORDER[i + 1][0] if i + 1 < len(ORDER) else TOTAL) for i in range(len(ORDER))}
TAGS = {}

def shot(t, name, fi=0.35, fo=0.35, until=None):
    """镜头透明度：从本镜头起点淡入，到下一镜头起点前淡出完毕（不交叠）"""
    t0 = S[name]; t1 = until if until is not None else NEXT[name]
    if t < t0 - 0.01 or t > t1 + 0.01: return 0.0
    return eo((t - t0) / fi) * (1 - eio((t - t1 + fo) / fo))

def tag(fr, t, s, a, t0):
    """标签区：小节名（带两侧细线）"""
    if a <= 0: return
    u = eo((t - t0) / 0.5); w = text_width(s, 'sans_med', 30) / 2
    fr.text(s, CX, ZT, 30, 'sans_med', GOLD, a * u, track=0.15)
    fr.line((CX - w - 70 * u, ZT), (CX - w - 20, ZT), GOLD, a * u * 0.6, 2); fr.line((CX + w + 20, ZT), (CX + w + 70 * u, ZT), GOLD, a * u * 0.6, 2)

def quote_card(fr, t, lines_, src, a, t0, y0=640, size=62, gold_last=True):
    """引文卡：竖排的大引号 + 逐行模糊入场 + 出处"""
    if a <= 0: return
    fr.text('“', 140, y0 - 60, 170, 'serif_black', GOLD, a * 0.5 * eo((t - t0) / 0.5), mode='L', glow=0.2)
    for k, s in enumerate(lines_):
        last = gold_last and k == len(lines_) - 1
        btext(fr, t, s, CX, y0 + k * (size * 1.55), size, 'serif_black', GOLD if last else WHITE, a, t0 + 0.25 + k * 0.55,
              glow=0.35 if last else 0.1, grad=GOLDG if last else None)
    fr.text('— ' + src, CX, y0 + len(lines_) * size * 1.55 + 30, 30, 'serif_med', C(205, 195, 175), a * eo((t - t0 - 1.2) / 0.5))

def golden_line(fr, t, l1, l2, a, t0, y=820):
    """金句：两行，第二行金色"""
    btext(fr, t, l1, CX, y - 80, 70, 'serif_black', WHITE, a, t0, glow=0.12)
    btext(fr, t, l2, CX, y + 70, 84, 'serif_black', GOLD, a, t0 + 0.6, glow=0.45, grad=GOLDG)

def chip(fr, x, y, s, col, a, size=34, fill=0.1, w=None):
    if a <= 0: return
    w2 = (w or text_width(s, 'sans_black', size) + 48) / 2; h2 = size * 0.95
    fr.rrect(x - w2, y - h2, x + w2, y + h2, h2, col, a, 2); fr.rrect_fill(x - w2, y - h2, x + w2, y + h2, h2, col, a * fill)
    fr.text(s, x, y, size, 'sans_black', col, a, mode='L', glow=0.15)

# ---------------------------------------------------------------- 天平
def draw_scale(fr, t, cx, cy, sz, tilt, a, ltxt, rtxt, lw=1.0, rw=1.0, lcol=WHITE, rcol=GOLD, lnum='', rnum=''):
    """天平：tilt>0 右侧下沉（价值重）；砝码大小 lw/rw"""
    if a <= 0: return
    ang = math.radians(cl(tilt, -18, 18))
    fr.line((cx, cy - sz * 0.62), (cx, cy + sz * 0.62), C(200, 190, 160), a, 4)
    fr.line((cx - sz * 0.3, cy + sz * 0.62), (cx + sz * 0.3, cy + sz * 0.62), C(200, 190, 160), a, 4)
    fr.circle((cx, cy - sz * 0.62), 8, GOLD, a, -1)
    dx, dy = math.cos(ang) * sz, math.sin(ang) * sz
    L, R = (cx - dx, cy - sz * 0.62 - dy), (cx + dx, cy - sz * 0.62 + dy)
    fr.line(L, R, GOLD, a, 5); fr.glow((cx, cy - sz * 0.62), 30, GOLD, a * 0.3)
    for (px, py), txt, w, col, num in ((L, ltxt, lw, lcol, lnum), (R, rtxt, rw, rcol, rnum)):
        hy = py + sz * 0.45
        fr.line((px, py), (px - sz * 0.28, hy), C(200, 190, 160), a * 0.8, 2); fr.line((px, py), (px + sz * 0.28, hy), C(200, 190, 160), a * 0.8, 2)
        th = np.linspace(0, math.pi, 20)
        fr.poly(np.stack([px + sz * 0.3 * np.cos(th), hy + sz * 0.1 * np.sin(th)], 1), C(220, 205, 160), a, 3)
        bw, bh = sz * 0.17 * (0.55 + 0.45 * w), sz * 0.15 * (0.55 + 0.45 * w)
        fr.rrect_fill(px - bw, hy - bh * 2, px + bw, hy, 6, col, a * 0.75); fr.rrect(px - bw, hy - bh * 2, px + bw, hy, 6, col, a, 2)
        if num: fr.text(num, px, hy - bh, int(sz * 0.11), 'num', C(20, 16, 10) if col != WHITE else C(30, 30, 40), a, mode='O')
        fr.text(txt, px, hy + sz * 0.28, int(sz * 0.13), 'serif_black', col, a, mode='L', glow=0.2)

# ---------------------------------------------------------------- 雪球热帖卡片（不出现任何真实用户名/头像）
def post_card(fr, t, a, t0, y0=560, h=520, title='买的都是好公司，为什么还是亏？', lines_n=5, shrink=0.0):
    if a <= 0: return
    u = eo((t - t0) / 0.7); x0, x1 = 120, 960; y0 = y0 + (1 - u) * 60; y1 = y0 + h
    fr.rrect_fill(x0, y0, x1, y1, 26, C(24, 26, 34), a * 0.92, 'L'); fr.rrect(x0, y0, x1, y1, 26, C(120, 130, 160), a * 0.6, 2)
    fr.circle((x0 + 60, y0 + 62), 24, C(90, 100, 130), a * 0.8, -1)
    fr.text('雪球热帖 · 整理', x0 + 100, y0 + 50, 28, 'sans_med', C(200, 205, 220), a, anchor='l')
    fr.text('匿名投资者', x0 + 100, y0 + 86, 22, 'sans_light', DIM, a, anchor='l')
    fr.text(title, CX, y0 + 165, 44, 'serif_black', WHITE, a * eo((t - t0 - 0.3) / 0.5), mode='L', glow=0.1)
    r = np.random.default_rng(4)
    for k in range(lines_n):
        yy = y0 + 240 + k * 44; w = (x1 - x0 - 120) * (0.6 + 0.4 * r.random())
        fr.rrect_fill(x0 + 60, yy - 7, x0 + 60 + w * eo((t - t0 - 0.5 - k * 0.12) / 0.5), yy + 7, 7, C(70, 76, 96), a * 0.7, 'L')
    for k, ic in enumerate(['讨论', '转发', '收藏']):
        fr.text(ic, x0 + 120 + k * 230, y1 - 44, 26, 'sans_med', DIM, a, anchor='l')

# ================================================================ 序章 · 雪球热帖
def sh_post(fr, t):
    a = shot(t, 'post')
    if a <= 0: return
    post_card(fr, t, a, S['post'] + 0.2)

def sh_books(fr, t):
    a = shot(t, 'books')
    if a <= 0: return
    t0 = S['books']
    for k, (ttl, x, col) in enumerate([('巴菲特致股东的信', 400, GOLD), ('段永平投资问答录', 680, C(200, 210, 230))]):
        ak = a * eo((t - t0 - k * 0.3) / 0.6); y0, y1 = 640 + (1 - ak) * 40, 1220
        fr.rrect_fill(x - 70, y0, x + 70, y1, 10, C(40, 34, 26) if k == 0 else C(30, 34, 44), ak * 0.95, 'L')
        fr.rrect(x - 70, y0, x + 70, y1, 10, col, ak * 0.8, 2)
        for j, ch in enumerate(ttl):
            fr.text(ch, x, y0 + 60 + j * 62, 50, 'serif_black', col, ak, mode='L', glow=0.15)
    btext(fr, t, '买股票，就是买公司', CX, ZB, 76, 'hand', C(245, 232, 200), a, CH('L02', 1) - 0.1, glow=0.2)


# ---------------------------------------------------------------- 标注避让：买入印章、买点标签、旁注不压折线、不互相重叠
def _rect(x, y, w, h, m=0): return (x - w / 2 - m, y - h / 2 - m, x + w / 2 + m, y + h / 2 + m)
def _hit(r, a): return not (r[2] < a[0] or r[0] > a[2] or r[3] < a[1] or r[1] > a[3])
def _cands(rs, pref):
    out = []
    for r in rs:
        for k in range(24):
            ang = math.radians(k * 15)
            da = abs((k * 15 - pref + 180) % 360 - 180)
            out.append((r + da * 0.9, r * math.cos(ang), r * math.sin(ang)))
    return [(x, y) for _, x, y in sorted(out)]
def _free(pts, cx, cy, w, h, cands, bounds, avoid, m=16):
    for ox, oy in cands:
        x, y = cx + ox, cy + oy; r = _rect(x, y, w, h, m)
        if r[0] < bounds[0] or r[2] > bounds[2] or r[1] < bounds[1] or r[3] > bounds[3]: continue
        if np.any((pts[:, 0] > r[0]) & (pts[:, 0] < r[2]) & (pts[:, 1] > r[1]) & (pts[:, 1] < r[3])): continue
        if any(_hit(r, a) for a in avoid): continue
        return x, y
    best, bx = None, None                       # 实在没有空位：取压线最少的位置
    for ox, oy in cands:
        x, y = cx + ox, cy + oy; r = _rect(x, y, w, h, m)
        if r[0] < bounds[0] or r[2] > bounds[2] or r[1] < bounds[1] or r[3] > bounds[3]: continue
        n = int(np.sum((pts[:, 0] > r[0]) & (pts[:, 0] < r[2]) & (pts[:, 1] > r[1]) & (pts[:, 1] < r[3]))) + 1000 * sum(_hit(r, a) for a in avoid)
        if best is None or n < best: best, bx = n, (x, y)
    print('layout fallback', w, h, best, file=sys.stderr)
    return bx or (cx + cands[0][0], cy + cands[0][1])
_SBOX = {}
def stamp_box(s, size):
    k = (s, size)
    if k not in _SBOX:
        m = stamp_mask(s, size, -10); ys, xs = np.nonzero(m > 0.05)
        _SBOX[k] = (xs.max() - xs.min() + 1, ys.max() - ys.min() + 1)
    return _SBOX[k]
def chart_layout(c, box, ssize):
    main = box == (BX0, BY0, BX1, BY1)
    chip = c.get('chip') if main else None
    extra_avoid = c.get('avoid', ()) if main else ()
    key = (box, ssize)
    L = c.setdefault('_lay', {})
    if key in L: return L[key]
    px, py = case_xf(c, box)
    xs = np.linspace(c['x0'], c['X'][-1], 4000)
    pts = [np.stack([[px(x) for x in xs], [py(y) for y in np.interp(xs, c['X'], c['Y'])]], 1)]
    for (xa, ya), (xb, yb) in (c.get('segs', []) if main else []):
        u = np.linspace(0, 1, 200)[:, None]
        pts.append((1 - u) * np.array([px(xa), py(ya)]) + u * np.array([px(xb), py(yb)]))
    pts = np.vstack(pts)
    avoid = list(extra_avoid)
    pk = c['peak']; w = text_width(pk[2], 'sans_med', 30); P = (px(pk[0]), py(pk[1]))
    avoid.append((P[0] + 18 - 4, P[1] - 30 - 22, P[0] + 18 + w + 4, P[1] - 30 + 22))
    e = c['end']; w = text_width(e[2], 'num', 46); E = (px(e[0]), py(e[1]))
    avoid.append((E[0] - 4 - w - 4, E[1] + 52 - 30, E[0], E[1] + 52 + 30))
    avoid.append((box[2] + 4, box[1] - 40, box[2] + 90, box[3]))            # 右侧刻度
    bounds = (box[0] - 30, box[1] - 70, box[2], box[3] - 8)
    B = (px(c['buy'][0]), py(c['buy'][1]))
    sw, sh = stamp_box('买入', ssize)
    st = _free(pts, *B, sw, sh, _cands([110, 130, 150, 175, 200, 230, 260, 300, 340, 380], -45), bounds, avoid)
    avoid.append(_rect(*st, sw, sh))
    lab = '你的买点 ' + str(c['buy'][1]); lw = text_width(lab, 'sans_black', 32) + 8
    lb = _free(pts, *B, lw, 40, _cands([48, 62, 80, 100, 125, 150, 180, 215, 250, 290, 330], 90), bounds, avoid, 12)
    avoid.append(_rect(*lb, lw, 40))
    ch = None
    if chip:
        cw, chh = text_width(chip[0], 'sans_black', chip[1]) + 48, chip[1] * 1.9
        ch = _free(pts, *B, cw, chh, _cands([70, 90, 115, 140, 170, 200, 240], 60), bounds, avoid, 12)
    L[key] = dict(stamp=st, label=lb, chip=ch, B=B)
    return L[key]

def case_shot(fr, t, i):
    c = CASES[i]
    if not (c['t_in'] - 0.1 < t < c['t_out'] + 0.1): return None
    r = case_scene(fr, t, c, i)
    if not r: return None
    px, py, a, dx = r
    if t > c['t_buy']:
        bx, bv = c['buy']
        sx, sy = chart_layout(c, (BX0, BY0, BX1, BY1), 64)['stamp']
        stamp(fr, t, '买入', sx + dx, sy, 64, c['t_buy'], GOLD, -10, a)
        if t - c['t_buy'] < 0.5: fr.glow((px(bx), py(bv)), 60, GOLD2, (1 - (t - c['t_buy']) / 0.5) * 0.8 * a)
    return px, py, a, dx

def sh_tencent(fr, t):
    r = case_shot(fr, t, 0)
    if not r: return
    px, py, a, dx = r; c = CASES[0]
    o = CUE['L04']
    if o - 1.1 < t < o + 1.4:
        fr.text(str(int(keys(t, c['rev']))), 900 + dx, 520, 64, 'num', WHITE, a * env(t, o - 1.1, o + 1.4, 0.2, 0.4) * 0.85, anchor='r', mode='L', glow=0.2)
    t6 = S['dest']
    if t > t6:
        p0, p1 = (px(2018.22), py(400)), (px(2026.88), py(373))
        dashed(fr, p0, p1, GOLD, a * 0.9, 2, prog=eo((t - t6) / 1.4))
        au = a * eo((t - t6 - 1.2) / 0.5); fx, fy = p1[0], p1[1] - 6
        fr.line((fx, fy), (fx, fy - 70), GOLD, au, 3)
        fr.fillpoly([(fx, fy - 70), (fx - 46, fy - 58), (fx, fy - 46)], GOLD, au * 0.9, 'E')

def sh_unwilling(fr, t):
    a = shot(t, 'unwilling')
    btext(fr, t, '你不甘心。', CX, 900, 110, 'serif_black', WHITE, a, S['unwilling'] + 0.05, glow=0.2)

def sh_catl(fr, t): case_shot(fr, t, 1)

def sh_ali(fr, t):
    r = case_shot(fr, t, 2)
    if not r: return
    px, py, a, dx = r
    tb = CASES[2]['t_buy'] + 0.6
    cx_, cy_ = chart_layout(CASES[2], (BX0, BY0, BX1, BY1), 64)['chip']
    chip(fr, cx_ + dx, cy_, '大笔回购 ✓', GOLD, a * eo((t - tb) / 0.4), 30)
    if t > CUE['L08']:
        ab = a * eo((t - CUE['L08'] - 0.2) / 0.4)
        fr.text('一度跌到 63', CX + dx, 1300, 110, 'num', RED2, ab, mode='L', glow=0.45)
        fr.text('2022.10 · 如今 84（2026.11.18）', CX + dx, 1410, 32, 'sans_med', C(210, 210, 220), ab * 0.9)

def sh_zp(fr, t):
    r = case_shot(fr, t, 3)
    if not r: return
    px, py, a, dx = r
    t11 = S['halves']
    if t > t11:
        xb = 985 + dx
        segs = [(2980, 1500, '①', DIM, t11, '避开'), (1500, 750, '②', RED2, t11 + 1.0, ''), (750, 375, '③', RED2, t11 + 1.5, '')]
        for hi, lo, lab, col, ts, note_ in segs:
            if t < ts: continue
            u = eo((t - ts) / 0.45); ya, yb = py(hi), py(lo)
            fr.line((xb, ya), (xb, lerp(ya, yb, u)), col, a, 3)
            fr.line((xb - 12, ya), (xb, ya), col, a * u, 3); fr.line((xb - 12, yb), (xb, yb), col, a * u, 3)
            fr.text(lab, xb + 30, (ya + yb) / 2, 34, 'sans_black', col, a * u, mode='L', glow=0.2)
            if note_: fr.text(note_, xb - 22, (ya + yb) / 2, 28, 'sans_med', col, a * u, anchor='r')

def sh_gold(fr, t):
    a = shot(t, 'gold')
    if a <= 0: return
    t0 = S['gold']
    notes = [('黄金', 300, 760, -6, GOLD), ('紫金矿业', 760, 820, 5, GOLD), ('低市盈率？', 520, 1080, -3, C(230, 220, 190))]
    for k, (s, x, y, ang, col) in enumerate(notes):
        ak = a * eo((t - t0 - 0.2 - k * 0.6) / 0.4)
        if ak <= 0: continue
        m = stamp_mask(s, 66, ang)
        blit_mask(fr, m, x, y, col, ak * 0.9, 'L', 0.2, 1 + 0.3 * (1 - eo((t - t0 - 0.2 - k * 0.6) / 0.3)))
    fr.text('寻找低市盈率背后的机会', CX, ZB, 44, 'serif_med', C(220, 215, 205), a * eo((t - t0 - 1.6) / 0.5))

def sh_nv(fr, t):
    a0 = shot(t, 'nv', until=_t('L13'))
    if a0 > 0:
        btext(fr, t, '换个市场', CX, 760, 92, 'serif_black', WHITE, a0, S['nv'] + 1.0, glow=0.15)
        btext(fr, t, '美股 · 英伟达', CX, 920, 76, 'serif_black', GOLD, a0, S['nv'] + 2.4, glow=0.35, grad=GOLDG)
    r = case_shot(fr, t, 4)
    if not r: return
    px, py, a, dx = r
    chip(fr, 260 + dx, 640, 'AI 需求还在', TEAL, a * eo((t - CH('L13', 2)) / 0.4), 28)

def sh_wall(fr, t):
    a = shot(t, 'wall')
    if a <= 0: return
    t0 = S['wall']
    boxes = [(70, 330, 520, 610), (560, 330, 1010, 610), (70, 650, 520, 930), (560, 650, 1010, 930), (315, 970, 765, 1250)]
    for k, (c, b) in enumerate(zip(CASES, boxes)):
        ak = a * 0.75 * eo((t - t0 - k * 0.15) / 0.4)
        fr.rrect(b[0], b[1], b[2], b[3], 14, DIM, ak * 0.4, 1)
        box = (b[0] + 24, b[1] + 64, b[2] - 24, b[3] - 20)
        draw_chart(fr, t, c, ak, 0, box, d=c['rev'][-1][1], mini=True)
        fr.text(c['name'], (b[0] + b[2]) / 2, b[1] + 34, 30, 'sans_med', C(220, 220, 230), ak * 1.3)
        px, py = case_xf(c, box)
        stamp(fr, t, '买入', px(c['buy'][0]) + 36, py(c['buy'][1]) - 30, 30, t0 + 0.4 + k * 0.2, GOLD, -10, ak * 1.3)
    tq = _t('L15')
    btext(fr, t, '为什么买的都是好公司', CX, 1340, 56, 'serif_black', WHITE, a, tq, glow=0.12)
    btext(fr, t, '却还是赚不到钱？', CX, 1430, 56, 'serif_black', GOLD, a, tq + 1.2, glow=0.35)

def sh_title(fr, t):
    t0 = S['title']; a = env(t, t0, S['q1_card'], 0.05, 0.35)
    if a <= 0: return
    u = t - t0
    for k, (spd, col) in enumerate([(1500, GOLD), (900, C(120, 170, 255))]):
        rr_ = spd * eo(u / 1.2) + 10; aw = (1 - eo(u / 1.2)) * a
        fr.circle((CX, 900), rr_, col, aw * 0.6, 3); fr.glow((CX, 900), 60 + rr_ * 0.1, col, aw * 0.15)
    rg = np.random.default_rng(42); n = 260
    ang = rg.random(n) * 6.283; sp = 150 + rg.random(n) * 900; d = sp * (1 - np.exp(-u * 2.2)) / 2.2
    fr.dots(CX + np.cos(ang) * d, 900 + np.sin(ang) * d * 0.8 + u * u * 20, GOLD2, np.exp(-u * 0.9) * 0.8 * a, 1, 'E')
    sc = 1 + 0.06 * (1 - eo(u / 0.5))
    fr.text('好公司，', CX, 800, int(150 * sc), 'serif_black', WHITE, a, mode='L', glow=0.3)
    fr.text('为什么还会亏？', CX, 990, int(150 * sc), 'serif_black', GOLD, a, mode='L', glow=0.5, grad=[GOLD2, GOLD, GOLDD, GOLD])
    sw = (u - 0.6) / 1.2
    if 0 < sw < 1: fr.glow((lerp(80, 1000, eio(sw)), 990), 70, WHITE, a * 0.35 * math.sin(math.pi * sw))
    fr.line((CX - 200 * eo((u - 0.5) / 0.6), 1120), (CX + 200 * eo((u - 0.5) / 0.6), 1120), GOLD, a * 0.8, 2)
    fr.text('雪球热帖里的五笔交易 · 三个问题', CX, 1190, 36, 'sans_med', C(210, 205, 195), a * eo((u - 1.0) / 0.5), track=0.1)

def chapter_card(fr, t, key, no, q1, q2):
    """章节卡：问题编号 + 两行问题；在本章第一句旁白期间保留，随后淡出"""
    t0 = S[key + '_card']; t1 = NEXT[key]
    a = env(t, t0, t1, 0.25, 0.4)
    if a <= 0: return
    u = t - t0
    fr.glow((CX, 860), 300, GOLD, a * 0.12 * (1 - eo(u / 1.5)) + a * 0.03)
    fr.text(no, CX, 620, 40, 'sans_black', GOLD, a * eo(u / 0.4), track=0.4, mode='L', glow=0.3)
    fr.line((CX - 160 * eo(u / 0.6), 680), (CX + 160 * eo(u / 0.6), 680), GOLD, a * 0.7, 2)
    btext(fr, t, q1, CX, 820, 80, 'serif_black', WHITE, a, t0 + 0.15, glow=0.15)
    btext(fr, t, q2, CX, 960, 80, 'serif_black', GOLD, a, t0 + 0.55, glow=0.45, grad=GOLDG)

# ================================================================ 问题一 · 价格与价值
def sh_anchor(fr, t):
    a = shot(t, 'anchor')
    if a <= 0: return
    tag(fr, t, '问题一 · 价格与价值', a, S['anchor'])
    pairs = [('476', '400', '腾讯'), ('319', '150', '阿里'), ('2980', '1500', '智谱')]
    l17 = LN['L17']; ts = [l17['t0'] + 0.1, l17['t0'] + (l17['t1'] - l17['t0']) * 0.36, l17['t0'] + (l17['t1'] - l17['t0']) * 0.7]
    ta = _t('L18') + 1.4
    for k, ((hi, lo, nm), tk) in enumerate(zip(pairs, ts)):
        ak = a * eo((t - tk) / 0.4); y = 700 + k * 190
        fr.text(nm, 170, y, 34, 'sans_med', DIM, ak, anchor='l')
        fr.text(hi, 470, y, 76, 'num', C(230, 230, 240), ak, anchor='r', mode='L', glow=0.4 if t > ta else 0.1)
        fr.text('→', 560, y, 56, 'sans_med', DIM, ak)
        fr.text(lo, 650, y, 76, 'num', GOLD, ak, anchor='l', mode='L', glow=0.2)
        if t > ta: fr.glow((420, y), 60, WHITE, a * 0.25 * eo((t - ta) / 0.5))
    if t > ta:
        u = eo((t - ta) / 0.8)
        dashed(fr, (420, 640), (420, lerp(640, 1100, u)), WHITE, a * 0.8, 2)
        chip(fr, 420, 1190, '锚：过去的高点', C(230, 230, 240), a * eo((t - ta - 0.6) / 0.4), 32)

def sh_scale(fr, t):
    a = shot(t, 'scale')
    if a <= 0: return
    tag(fr, t, '问题一 · 价格与价值', a, S['anchor'])
    t0 = S['scale']; t20, t21 = _t('L20'), _t('L21')
    btext(fr, t, '卖多少钱 ≠ 值多少钱', CX, ZB, 66, 'serif_black', WHITE, a, t0 + 0.3, glow=0.15)
    tilt = 0
    draw_scale(fr, t, CX, 880, 360, tilt, a * eo((t - t0 - 0.6) / 0.5), '价格', '内在价值')
    if t > t20:     # 安全边际：放在天平下方，不与托盘争位置
        chip(fr, CX, 1200, '安全边际 = 内在价值 − 价格', GOLD, a * eo((t - t20 - 0.6) / 0.5) * (1 - eio((t - t21 + 0.2) / 0.4)), 36, 0.12)
    if t > t21:
        yrs = 8
        for k in range(yrs):
            ts = t21 + 0.5 + k * 0.12; u = eo((t - ts) / 0.4); mv = eio((t - t21 - 2.2 - k * 0.05) / 0.9)
            h = 120 * lerp(1.0, 0.88 ** (k + 1), mv); x = lerp(560 + k * 52, CX + 360 * 0.98, mv * 0)
            x = lerp(600 + k * 50, 1000 - 60, mv); yb = 1300
            fr.rrect_fill(x - 16, yb - h, x + 16, yb, 4, GOLD, a * u * (1 - 0.7 * mv) * 0.75)
            if mv < 0.05: fr.text(f'{k + 1}', x, yb + 22, 20, 'mono', DIM, a * u)
        cap = '未来每年的现金' if t < t21 + 2.4 else '折现到今天 = 内在价值'
        fr.text(cap, 380, 1250, 32, 'sans_black', GOLD, a * eo((t - t21 - 0.4) / 0.4), mode='L', glow=0.2)
        fr.text('巴菲特：内在价值是企业未来现金流的折现值（伯克希尔《股东手册》）', CX, ZD, 24, 'sans_light', DIM, a * eo((t - t21 - 1.0) / 0.5))

def sh_twoscales(fr, t):
    a = shot(t, 'twoscales')
    if a <= 0: return
    tag(fr, t, '问题一 · 价格与价值', a, S['anchor'])
    t0, t23 = S['twoscales'], _t('L23')
    a1 = a * eo((t - t0 - 0.2) / 0.5)
    tl = lerp(0, -14, eo((t - t0 - 1.2) / 1.0))
    draw_scale(fr, t, 290, 900, 220, tl, a1, '价格', '价值', 1.3, 0.5, WHITE, GOLD, '1500', '300')
    fr.text('依然昂贵得惊人', 290, 1240, 40, 'serif_black', RED2, a1 * eo((t - t0 - 2.2) / 0.4), mode='L', glow=0.3)
    a2 = a * eo((t - t23 - 0.2) / 0.5)
    tr = lerp(0, 12, eo((t - t23 - 1.2) / 1.0))
    draw_scale(fr, t, 790, 900, 220, tr, a2, '价格', '价值', 0.5, 1.2, WHITE, GOLD, '50', '100')
    fr.text('可能蕴藏机会', 790, 1240, 40, 'serif_black', TEAL, a2 * eo((t - t23 - 2.4) / 0.4), mode='L', glow=0.3)

def sh_gold1(fr, t):
    a = shot(t, 'gold1')
    golden_line(fr, t, '跌了多少，不是答案', '值多少钱，才是问题', a, S['gold1'] + 0.05)

# ================================================================ 问题一 · 护城河与能力圈
T12 = '问题一 · 护城河与能力圈'

def ring(fr, cx, cy, R, col, a, gaps=(), th=4, flip=1.0, n=220):
    t_ = np.linspace(0, 2 * math.pi, n); keep = np.ones(n, bool)
    for g0, g1 in gaps: keep &= ~((t_ > g0) & (t_ < g1))
    seg = []
    for k in range(n):
        if keep[k]: seg.append((cx + R * math.cos(t_[k]), cy + R * math.sin(t_[k]) * flip))
        elif len(seg) > 1: fr.poly(seg, col, a, th); seg = []
        else: seg = []
    if len(seg) > 1: fr.poly(seg, col, a, th)

def sh_tenyear(fr, t):
    a = shot(t, 'tenyear')
    if a <= 0: return
    tag(fr, t, T12, a, S['tenyear'])
    t0 = S['tenyear']; u = eo((t - t0 - 0.3) / 1.6)
    fr.line((140, 900), (140 + 800 * u, 900), GOLD, a, 3)
    fr.circle((140, 900), 10, GOLD, a, -1); fr.text('今天', 140, 960, 36, 'sans_black', GOLD, a, mode='L', glow=0.2)
    if u > 0.98:
        fr.text('十年后？', 940, 960, 40, 'serif_black', WHITE, a * eo((t - t0 - 1.9) / 0.4), anchor='r')
        for k in range(10):
            fr.glow((700 + k * 28, 900 + math.sin(t * 2 + k) * 12), 40, C(150, 160, 200), a * 0.08)
    btext(fr, t, '它十年后，依然优秀吗？', CX, ZB, 64, 'serif_black', WHITE, a, CH('L25', 1) + 0.2 if len(LN['L25']['chunks']) > 1 else t0 + 1.0, glow=0.15)

def sh_moat(fr, t):
    a = shot(t, 'moat')
    if a <= 0: return
    tag(fr, t, T12, a, S['tenyear'])
    t0, t27, t28 = S['moat'], _t('L27'), _t('L28')
    for k, (nm, x, sub) in enumerate([('腾讯', 300, '社交网络'), ('阿里', 780, '商家生态')]):
        ak = a * eo((t - t0 - 0.3 - k * 0.8) / 0.5)
        gaps = []
        if t > t28: g = eo((t - t28) / 0.8) * 0.22; gaps = [(-math.pi / 2 - g, -math.pi / 2 + g), (math.pi * 0.15 - g, math.pi * 0.15 + g)]
        ring(fr, x, 960, 180, GOLD, ak, gaps); ring(fr, x, 960, 198, GOLD, ak * 0.5, gaps, 2)
        fr.glow((x, 960), 120, GOLD, ak * 0.12)
        fr.text(nm, x, 940, 60, 'serif_black', GOLD, ak, mode='L', glow=0.3)
        fr.text(sub, x, 1005, 30, 'sans_med', C(220, 210, 180), ak)
    if t > t27:
        flows = ['短视频', '直播电商', '算法推荐']
        for k, s in enumerate(flows):
            ts = t27 + k * 0.9; u = eo((t - ts) / 0.5)
            if u <= 0: continue
            x = 220 + k * 320
            chip(fr, x, 640, s, C(140, 200, 255), a * u, 32)
            r = np.random.default_rng(k + 50); n = 60
            ph = (t * (0.5 + r.random(n) * 0.4) + r.random(n)) % 1.0
            tx_ = np.where(r.random(n) < 0.5, 300, 780) + r.normal(0, 40, n)
            xs = lerp(x + r.normal(0, 20, n), tx_, ph); ys = lerp(690, 790, ph)
            fr.dots(xs, ys, C(140, 200, 255), a * u * (1 - ph) * 0.9, 1, 'E')
    btext(fr, t, '护城河是真的，时代也在变', CX, ZB, 60, 'serif_black', WHITE, a, t0 + 0.6, glow=0.12)

def sh_quotes(fr, t):
    a = shot(t, 'quotes')
    if a <= 0: return
    tag(fr, t, T12, a, S['tenyear'])
    t0, t30 = S['quotes'], _t('L30')
    a1 = a * (1 - eio((t - t30 + 0.4) / 0.4))
    quote_card(fr, t, ['一条必须不断重建的护城河', '最终将不再是', '一条真正的护城河'], '沃伦 · 巴菲特，2007 年致股东信', a1, t0 + 0.2, 640, 60)
    a2 = a * eo((t - t30) / 0.4)
    if a2 > 0: quote_card(fr, t, ['许多传统的护城河', '正在迅速消失'], '查理 · 芒格，2020 年 Daily Journal 股东会', a2, t30 + 0.1, 720, 70)

def sh_newmoat(fr, t):
    a = shot(t, 'newmoat')
    if a <= 0: return
    tag(fr, t, T12, a, S['tenyear'])
    t0 = S['newmoat']
    pos = [(260, 760, 120), (560, 980, 150), (840, 760, 110), (330, 1180, 90), (790, 1170, 100)]
    for k, (x, y, R) in enumerate(pos):
        old = k % 2 == 0
        br = 0.5 + 0.5 * math.sin(t * 1.6 + k * 1.3)
        al = a * (eo((t - t0 - k * 0.25) / 0.6)) * ((1 - 0.6 * eo((t - t0 - 1.5) / 1.5)) if old else eo((t - t0 - 1.0 - k * 0.3) / 0.8))
        ring(fr, x, y, R, GOLD if not old else C(150, 140, 120), al * (0.6 + 0.4 * br), th=3)
        fr.glow((x, y), R * 0.6, GOLD, al * 0.1 * br)
    fr.text('旧的优势衰弱', 260, 600, 32, 'sans_med', C(170, 160, 140), a * eo((t - t0 - 1.5) / 0.5))
    fr.text('新的优势诞生', 820, 600, 32, 'sans_black', GOLD, a * eo((t - t0 - 2.5) / 0.5))
    btext(fr, t, '商业世界：最残酷，也最迷人', CX, ZB, 58, 'serif_black', WHITE, a, _t('L32') + 0.1, glow=0.12)

def sh_keep(fr, t):
    a = shot(t, 'keep')
    if a <= 0: return
    tag(fr, t, T12, a, S['tenyear'])
    t0, t34 = S['keep'], CUE['L34']
    am = a * (1 - eio((t - t34 + 0.4) / 0.4))
    if am > 0:
        R = 230; core = 120 + 30 * math.sin(t * 1.2)
        ring(fr, CX, 960, R, GOLD, am); ring(fr, CX, 960, R + 18, GOLD, am * 0.5, th=2)
        fr.circle((CX, 960), core, GOLD2, am * 0.5, 3); fr.glow((CX, 960), core, GOLD, am * 0.18)
        fr.text('利润', CX, 960, 56, 'serif_black', GOLD2, am, mode='L', glow=0.3)
        fr.text('护城河', CX + R + 10, 960 - R - 20, 34, 'sans_black', GOLD, am, anchor='l')
        btext(fr, t, '过去的成功 ≠ 未来的成功', CX, ZB, 60, 'serif_black', WHITE, am, t0 + 0.3, glow=0.12)
    golden_line(fr, t, '不只看护城河过去有多宽', '还要看它能守住多少利润', a * eo((t - t34) / 0.4), t34)

def sh_tech(fr, t):
    a = shot(t, 'tech')
    if a <= 0: return
    tag(fr, t, T12, a, S['tenyear'])
    t0 = S['tech']
    x0, x1, y0, y1 = 130, 950, 640, 1180
    for k in range(4):
        ts = t0 + 0.3 + k * 1.4; u = eo((t - ts) / 1.2)
        if u <= 0: continue
        xs = np.linspace(x0 + k * 160, x0 + k * 160 + 420, 60); xs = xs[xs <= x0 + k * 160 + 420 * u]
        if len(xs) < 2: continue
        ys = y1 - (y1 - y0) * (0.35 + 0.15 * k) / (1 + np.exp(-(xs - (x0 + k * 160 + 210)) / 45))
        col = GOLD if k == 3 else C(120, 150, 210)
        fr.poly(np.stack([xs, ys], 1), col, a * (0.5 + 0.5 * (k == 3) if t > ts + 1.4 else 0.9), 3)
    fr.line((x0, y1), (x1, y1), DIM, a * 0.6, 2); fr.text('每一代技术，都可能被下一代超越', CX, 1240, 32, 'sans_med', C(200, 205, 220), a * eo((t - t0 - 2.0) / 0.5))
    qs = ['领先能持续多久？', '格局会不会改变？', '利润能留下多少？']
    l35 = LN['L35']; ts_ = [c[1] for c in l35['chunks']][:3]
    for k, (q, ts) in enumerate(zip(qs, ts_ + [l35['t1']] * 3)):
        chip(fr, CX, 1300 - 0 + 0 * k, q, GOLD, 0, 30)
    j = sum(1 for ts in ts_ if t >= ts) - 1
    if j >= 0:
        u = eo((t - ts_[j]) / 0.4)
        btext(fr, t, qs[min(j, 2)], CX, ZB, 62, 'serif_black', GOLD, a, ts_[j], glow=0.3, dur=0.4)

def sh_ibm(fr, t):
    a = shot(t, 'ibm')
    if a <= 0: return
    tag(fr, t, T12, a, S['tenyear'])
    t0, t38 = S['ibm'], _t('L38')
    btext(fr, t, '连巴菲特也曾看走眼', CX, ZB, 66, 'serif_black', WHITE, a, t0 + 0.1, glow=0.15)
    x0, x1, y = 160, 920, 880; u = eo((t - t0 - 0.6) / 1.6)
    fr.line((x0, y), (lerp(x0, x1, u), y), GOLD, a, 3)
    for k, (yr, lab, xf) in enumerate([('2011', '重仓买入 IBM', 0.0), ('2017', '重新评估', 0.62), ('2018', '清仓', 1.0)]):
        ak = a * eo((t - t0 - 0.8 - k * 0.8) / 0.4); x = lerp(x0, x1, xf)
        fr.circle((x, y), 12, GOLD, ak, -1); fr.glow((x, y), 20, GOLD, ak * 0.6)
        fr.text(yr, x, y - 60, 48, 'num', GOLD, ak, mode='L', glow=0.25); fr.text(lab, x, y + 60, 34, 'sans_black', WHITE, ak)
    if t > t38:
        u2 = eo((t - t38) / 0.8)
        for k in range(16):
            fr.glow((CX + 60 + k * 26, y + math.sin(t + k) * 40), 60, C(140, 150, 180), a * u2 * 0.06)
        fr.text('过去', 300, 1080, 40, 'serif_black', WHITE, a * u2); fr.text('未来', 780, 1080, 40, 'serif_black', C(170, 175, 195), a * u2 * 0.7)
        fr.text('理解过去 ≠ 看清未来', CX, 1200, 46, 'serif_black', GOLD, a * eo((t - t38 - 0.8) / 0.4), mode='L', glow=0.3)
    fr.text('来源：CNBC 2017、2018 年采访', CX, ZD, 24, 'sans_light', DIM, a * eo((t - t0 - 2.5) / 0.5))

def sh_baskets(fr, t):
    a = shot(t, 'baskets')
    if a <= 0: return
    tag(fr, t, T12, a, S['tenyear'])
    t0, t40, t41 = S['baskets'], _t('L40'), _t('L41')
    btext(fr, t, '芒格的三个篮子', CX, ZB, 66, 'serif_black', WHITE, a, t0 + 0.1, glow=0.15)
    side = eio((t - t41 - 0.3) / 1.0)
    bx = [(110, 360, '可以投资', TEAL), (390, 640, '不值得投资', DIM), (670, 970, '太难', GOLD)]
    yb = 1150
    for k, (xa, xb_, zh_, col) in enumerate(bx):
        ak = a * eo((t - t0 - 0.6 - k * 0.5) / 0.4); big = k == 2
        dx = 0
        fr.poly([(xa + dx, yb - 160), (xa + 20 + dx, yb), (xb_ - 20 + dx, yb), (xb_ + dx, yb - 160)], col, ak * (1 if big else 0.7), 4 if big else 2)
        fr.text(zh_, (xa + xb_) / 2 + dx, yb + 60, 48 if big else 40, 'serif_black', col, ak, mode='L', glow=0.25 if big else 0)
    for k, it in enumerate(['大模型', '算力芯片']):
        ts = t40 + 0.6 + k * 0.7; u = (t - ts) / 0.8
        if u <= 0: continue
        x = lerp(300 + k * 300, 820, eio(u)); y = lerp(650, yb - 50 - k * 50, eio(u)) - math.sin(cl(u) * math.pi) * 120
        sc = 1 - 0.3 * eio(u)
        fr.rrect(x - 100 * sc, y - 34 * sc, x + 100 * sc, y + 34 * sc, 20 * sc, WHITE, a, 2); fr.text(it, x, y, int(40 * sc), 'sans_black', WHITE, a)
    if side > 0:
        fr.text('不是不能投，而是超出了自己的理解范围', CX, 1300, 34, 'sans_med', GOLD, a * side)

def sh_circle(fr, t):
    a = shot(t, 'circle')
    if a <= 0: return
    tag(fr, t, T12, a, S['tenyear'])
    t0 = S['circle']; cx, cy, R = CX, 940, 260
    u = eo((t - t0 - 0.2) / 1.2)
    fr.arc((cx, cy), R, -math.pi / 2, -math.pi / 2 + 2 * math.pi * u, GOLD, a, 4, 180)
    br = 0.6 + 0.4 * math.sin(t * 3)
    fr.arc((cx, cy), R + 4, -math.pi / 2, -math.pi / 2 + 2 * math.pi * u, GOLD2, a * 0.4 * br, 2, 180)
    fr.text('能力圈', cx, cy - 20, 66, 'serif_black', GOLD, a * u, mode='L', glow=0.35)
    fr.text('边界，比大小更重要', cx, cy + 50, 32, 'sans_med', GOLD2, a * eo((t - t0 - 1.6) / 0.4))
    r = np.random.default_rng(7); n = 80
    ang = r.random(n) * 2 * math.pi; rad = R + 70 + r.random(n) * 200
    sp = 0.05 + r.random(n) * 0.06
    xs = cx + rad * np.cos(ang + t * sp); ys = cy + rad * np.sin(ang + t * sp) * 0.9
    ok = (ys > ZC0) & (ys < ZC1)
    fr.dots(xs[ok], ys[ok], C(150, 160, 190), a * 0.55, 1, 'L')
    btext(fr, t, '不需要看懂所有公司', CX, ZB, 60, 'serif_black', WHITE, a, _t('L43'), glow=0.12)
    fr.text('巴菲特，1996 年致股东信', CX, ZD, 24, 'sans_light', DIM, a * eo((t - t0 - 1.0) / 0.5))

# ================================================================ 问题一 · 时代故事、周期、预期
T13 = '问题一 · 时代故事、周期与预期'

def sh_story(fr, t):
    a = shot(t, 'story')
    if a <= 0: return
    tag(fr, t, T13, a, S['story'])
    t0 = S['story']; r = np.random.default_rng(15)
    x = 80
    while x < 1000:
        w = 50 + r.random() * 70; h = 180 + r.random() * 380
        ak = a * eo((t - t0 - (x / 1000) * 0.8) / 0.5)
        fr.rrect_fill(x, 1260 - h, x + w, 1260, 3, C(26, 30, 44), ak, 'L'); fr.rrect(x, 1260 - h, x + w, 1260, 3, C(70, 80, 110), ak * 0.6, 1)
        for yy in range(int(1260 - h + 16), 1250, 26):
            for xx in range(int(x + 10), int(x + w - 8), 18):
                if r.random() < 0.35: fr.splat([xx], [yy], GOLD2, ak * 0.5 * (0.5 + 0.5 * math.sin(t * 2 + xx * 0.1)), 'E')
        x += w + 8
    for k, (s, ts) in enumerate([('新能源汽车会改变世界', _t('L45')), ('人工智能会改变世界', _t('L45') + 1.6)]):
        u = eo((t - ts) / 0.5); y = 640 + k * 110
        chip(fr, CX, y, s, GOLD, a * u, 44, 0.12)

def sh_cars(fr, t):
    a = shot(t, 'cars')
    if a <= 0: return
    tag(fr, t, T13, a, S['story'])
    t0, t1 = S['cars'], LN['L46']['t1']
    cols, rows = 50, 40; x0, y0, sp = 148, 600, 16
    rr = np.random.default_rng(9); order = rr.random(cols * rows)
    keep = np.zeros(cols * rows, bool); keep[[612, 1037, 1544, 300, 1888]] = True
    gx = x0 + (np.arange(cols * rows) % cols) * sp; gy = y0 + (np.arange(cols * rows) // cols) * sp
    ua = np.clip((t - t0 - 0.3 - (gy - y0) / 640 * 0.9 - order * 0.2) / 0.3, 0, 1)
    tk = t1 - 3.0
    die = np.clip((t - tk - order * 1.6) / 0.3, 0, 1) * (~keep)
    al = ua * (1 - die)
    fr.dots(gx, gy, C(160, 185, 240), al * a * 0.9, 1, 'L'); fr.splat(gx, gy, C(160, 185, 240), al * a * 0.5, 'B')
    ak = a * eo((t - tk - 1.6) / 0.5)
    for idx in np.where(keep)[0]: fr.glow((gx[idx], gy[idx]), 16, GOLD, ak * 0.9); fr.circle((gx[idx], gy[idx]), 7, GOLD2, ak, -1)
    fr.text('数以千计的汽车品牌', CX, 1310, 40, 'serif_black', C(200, 210, 240), a * eo((t - t0 - 1.0) / 0.4) * (1 - eio((t - tk - 1.0) / 0.4)))
    fr.text('绝大多数，消失在竞争之中', CX, 1310, 40, 'serif_black', GOLD, ak, mode='L', glow=0.3)
    btext(fr, t, '汽车改变了整个世界', CX, ZB, 64, 'serif_black', WHITE, a, t0 + 0.2, glow=0.12)
    fr.text('巴菲特，1999 年 Sun Valley 演讲（大意）', CX, ZD, 24, 'sans_light', DIM, a * eo((t - t0 - 1.5) / 0.5))

def sh_air(fr, t):
    a = shot(t, 'air')
    if a <= 0: return
    tag(fr, t, T13, a, S['story'])
    t0 = S['air']; u = eo((t - t0 - 0.2) / 2.5)
    xs = np.linspace(100, 100 + 880 * u, 80); ys = 780 - (xs - 100) * 0.18 + np.sin(xs * 0.01) * 20
    fr.poly(np.stack([xs, ys], 1), C(200, 220, 255), a * 0.8, 2)
    px_, py_ = xs[-1], ys[-1]
    fr.fillpoly([(px_ + 26, py_), (px_ - 18, py_ - 12), (px_ - 10, py_), (px_ - 18, py_ + 12)], WHITE, a, 'E'); fr.glow((px_, py_), 30, WHITE, a * 0.5)
    x0, x1, yb = 140, 940, 1200
    fr.line((x0, yb), (x1, yb), DIM, a * 0.6, 2)
    gx = np.linspace(x0, x0 + (x1 - x0) * eo((t - t0 - 1.0) / 2.0), 60)
    fr.poly(np.stack([gx, yb - (gx - x0) * 0.42], 1), C(140, 200, 255), a, 3)
    fr.poly(np.stack([gx, yb - 8 - 6 * np.sin(gx * 0.03)], 1), RED2, a, 3)
    fr.text('出行规模', x1, yb - (x1 - x0) * 0.42 - 30, 32, 'sans_black', C(140, 200, 255), a * eo((t - t0 - 2.8) / 0.4), anchor='r')
    fr.text('投资者的回报', x1, yb + 40, 32, 'sans_black', RED2, a * eo((t - t0 - 2.8) / 0.4), anchor='r')
    btext(fr, t, '航空业也是如此', CX, ZB, 64, 'serif_black', WHITE, a, t0 + 0.1, glow=0.12)
    fr.text('巴菲特，2007 年致股东信谈航空业', CX, ZD, 24, 'sans_light', DIM, a * eo((t - t0 - 1.5) / 0.5))

def sh_capital(fr, t):
    a = shot(t, 'capital')
    if a <= 0: return
    tag(fr, t, T13, a, S['story'])
    t0, t49 = S['capital'], _t('L49')
    r = np.random.default_rng(13); n = 420
    sx = r.random(n) * W; sy = 600 + r.random(n) * 200
    ph = (t * (0.35 + r.random(n) * 0.4) + r.random(n)) % 1.0
    xs = lerp(sx, 300, ph ** 1.4); ys = lerp(sy, 1150, ph ** 1.4)
    fr.dots(xs, ys, C(120, 200, 255), a * (1 - ph) * 0.7 * eo((t - t0) / 0.8), 1, 'E')
    fr.text('资本 · 技术 · 竞争者', CX, 640, 40, 'serif_med', C(150, 210, 255), a * eo((t - t0 - 0.4) / 0.5))
    bars = [('供给', 300, C(120, 200, 255), lambda u: 120 + 320 * u), ('行业规模', 560, C(140, 160, 230), lambda u: 150 + 260 * u),
            ('利润', 820, GOLD, lambda u: 220 - 30 * u)]
    u = eo((t - t0 - 1.0) / (t49 + 3 - t0))
    for k, (lab, x, col, fh) in enumerate(bars):
        h = fh(u); ak = a * eo((t - t0 - 0.6 - k * 0.3) / 0.4)
        fr.rrect_fill(x - 70, 1240 - h, x + 70, 1240, 8, col, ak * 0.6); fr.rrect(x - 70, 1240 - h, x + 70, 1240, 8, col, ak, 2)
        fr.text(lab, x, 1290, 34, 'sans_black', col, ak)
    if t > t49 + 2.0:
        ak = a * eo((t - t49 - 2.0) / 0.5)
        fr.rrect_fill(820 - 70, 1240 - 190, 820 + 70, 1240 - 120, 6, RED2, ak * 0.6)
        fr.text('维持地位的投入', 820, 760, 28, 'sans_black', RED2, ak)
    btext(fr, t, '规模越来越大，利润未必同步', CX, ZB, 58, 'serif_black', WHITE, a, t49, glow=0.12)

def sh_lowpe(fr, t):
    a = shot(t, 'lowpe')
    if a <= 0: return
    tag(fr, t, T13, a, S['story'])
    t0, t51, t52, t53, t54 = S['lowpe'], _t('L51'), _t('L52'), _t('L53'), CUE['L54']
    am = a * (1 - eio((t - t54 + 0.4) / 0.4))
    btext(fr, t, '市盈率越低，越危险？', CX, ZB, 64, 'serif_black', WHITE, am * (1 - eio((t - t51 + 0.4) / 0.4)), t0 + 0.1, glow=0.15)
    if am > 0 and t > t51 - 0.3:
        vals = [.36, .42, .5, .58, .67, .76, .86, .95, 1.0, .9, .78, .66, .56, .5]
        nb = len(vals); x0, x1, yb, hmax = 140, 940, 1250, 300; bw = (x1 - x0) / nb
        for k, v in enumerate(vals):
            ts = t51 + 0.2 + k * 0.12 if k <= 8 else t52 + 0.6 + (k - 9) * 0.35
            u = eo((t - ts) / 0.35)
            if u <= 0: continue
            col = GOLD if k == 8 else (RED2 if k > 8 else C(110, 140, 200))
            h = v * hmax * u; xa = x0 + k * bw + 6
            fr.rrect_fill(xa, yb - h, xa + bw - 12, yb, 4, col, am * (0.55 if k != 8 else 0.85))
            if k == 8: fr.glow((xa + bw / 2 - 6, yb - h), 30, GOLD, am * 0.4 * u)
        fr.line((x0, yb), (x1, yb), DIM, am * 0.6, 2); fr.text('一家矿业公司的利润（示意）', x0, yb + 40, 26, 'sans_med', DIM, am, anchor='l')
        if t > t52 + 0.6: dashed(fr, (x0, yb - 0.55 * hmax), (x1, yb - 0.55 * hmax), C(200, 205, 220), am * 0.7, 2)
        if t > t52 + 1.8: fr.text('正常水平', x1, yb - 0.55 * hmax - 26, 26, 'sans_med', C(200, 205, 220), am, anchor='r')
        xk = x0 + 8 * bw + bw / 2
        fr.text('景气高峰', xk, yb - hmax - 40, 30, 'sans_black', GOLD, am * eo((t - t51 - 1.5) / 0.4), mode='L', glow=0.2)
        if t < t53:
            fr.text('10×', CX, 740, 150, 'num', GOLD, am * eo((t - t51 - 2.0) / 0.4), mode='L', glow=0.5)
            fr.text('利润最肥的时候，市盈率最低', CX, 850, 34, 'sans_med', C(210, 210, 220), am * eo((t - t51 - 2.4) / 0.4))
        else:
            pe = counter(t, t53 + 2.2, t53 + 4.2, 13, 26) if t > t53 + 2.2 else 13
            col = lerpc(GOLD, RED2, cl((pe - 13) / 6))
            fr.text(f'{pe:.0f}×', CX, 740, int(150 + 30 * impact(t) * (pe > 25)), 'num', col, am * eo((t - t53) / 0.4), mode='L', glow=0.5)
            fr.text('假设：股价不变，利润减半', CX, 850, 34, 'sans_med', C(210, 210, 220), am * eo((t - t53 - 1.0) / 0.4))
    golden_line(fr, t, '最让人觉得便宜的时刻', '有时恰恰是企业最赚钱的时刻', a * eo((t - t54) / 0.4), t54)

def sh_stair(fr, t):
    a = shot(t, 'stair')
    if a <= 0: return
    tag(fr, t, T13, a, S['story'])
    t0, t56 = S['stair'], _t('L56')
    for side, (x0, lab, col, vals) in enumerate([(120, '景气高峰的暂时繁荣', RED2, [.3, .45, .62, .85, 1.0, .7, .5, .42]),
                                                 (590, '创新带来的新台阶', TEAL, [.3, .34, .5, .55, .7, .74, .9, .95])]):
        ak = a * eo((t - (t0 if side == 1 else t56) - 0.2) / 0.5)
        if side == 1: ak = a * eo((t - t0 - 0.3) / 0.5)
        else: ak = a * eo((t - t56 - 0.2) / 0.5)
        bw = 46
        for k, v in enumerate(vals):
            u = eo((t - (t0 if side else t56) - 0.5 - k * 0.1) / 0.35); h = v * 380 * u
            fr.rrect_fill(x0 + k * (bw + 8), 1200 - h, x0 + k * (bw + 8) + bw, 1200, 4, col, ak * 0.65)
        fr.text(lab, x0 + 4 * (bw + 8), 1260, 30, 'sans_black', col, ak)
    btext(fr, t, '并非所有高增长都只是周期', CX, ZB, 58, 'serif_black', WHITE, a * (1 - eio((t - t56 + 0.3) / 0.3)), t0 + 0.1, glow=0.12)
    btext(fr, t, '哪些利润能长期留下？', CX, ZB, 64, 'serif_black', GOLD, a * eo((t - t56) / 0.3), t56, glow=0.35)

def sh_q99(fr, t):
    a = shot(t, 'q99')
    if a <= 0: return
    tag(fr, t, T13, a, S['story'])
    quote_card(fr, t, ['投资的关键，不在于', '一个行业将如何改变社会', '而在于竞争优势', '能持续多久'], '沃伦 · 巴菲特，1999 年（大意）', a, S['q99'] + 0.2, 600, 60)

def sh_expect(fr, t):
    a = shot(t, 'expect')
    if a <= 0: return
    tag(fr, t, T13, a, S['story'])
    t0, t59, t60 = S['expect'], _t('L59'), CUE['L60']
    am = a * (1 - eio((t - t60 + 0.4) / 0.4))
    btext(fr, t, '增长，是否早已被算进价格？', CX, ZB, 60, 'serif_black', WHITE, am, t0 + 0.2, glow=0.15)
    if am > 0:
        base, x = 1250, CX; H_ = 560
        u = eo((t - t59) / 0.8); g = eio((t - t59 - 1.0) / 4.0)
        hc = H_ * lerp(0.4, 0.72, g); he = H_ - hc
        fr.rrect_fill(x - 120, base - hc, x + 120, base, 10, GOLD, am * 0.7)
        fr.text('公司', x, base - hc / 2, 44, 'sans_black', C(40, 26, 6), am, mode='O')
        if u > 0:
            fr.rrect(x - 120, base - H_, x + 120, base - hc, 10, C(150, 180, 240), am * u, 2)
            fr.rrect_fill(x - 120, base - H_, x + 120, base - hc, 10, C(150, 180, 240), am * u * 0.22)
            fr.text('期待', x, base - hc - he / 2, 44, 'sans_black', C(190, 210, 255), am * u)
        fr.text('你付出的价格', x - 160, base - H_ / 2, 30, 'sans_med', C(210, 210, 220), am * eo((t - t0 - 1.5) / 0.4), anchor='r')
        fr.text('利润翻倍', x + 160, base - hc + 20, 30, 'sans_black', GOLD, am * eo((t - t59 - 1.5) / 0.4), anchor='l')
        fr.text('预期已经算进去', x + 160, base - H_ + 40, 30, 'sans_black', C(160, 190, 250), am * eo((t - t59 - 2.5) / 0.4), anchor='l')
    golden_line(fr, t, '决定回报的，不只是公司有多优秀', '还有你为它的未来，付了多少钱', a * eo((t - t60) / 0.4), t60)

# ================================================================ 铁锤人
NAIL_X = [250, 540, 830]; GROUND = 1240; NAIL_H0, NAIL_H1 = 170, 62
STRIKES = ['L63a', 'L63b', 'L63c']
NAIL_LAB = ['阿里 · 回购', '宁德 · 份额领先', '腾讯 · 持续盈利']
NAIL_Q = ['回购价格贵不贵？', '有没有定价权？', '利润会不会变？']

def nail_h(i, t):
    c = CUE[STRIKES[i]]
    return NAIL_H0 if t < c else lerp(NAIL_H0, NAIL_H1, eo((t - c) / 0.07))

REST = (CX, 1010.0, 0.0, 0.72)
def hammer_pose(t):
    A = S['hammer'] + 0.8
    if t < A: return REST
    c = [CUE[k] for k in STRIKES]
    top = lambda i, dy=0: (NAIL_X[i] + 40, GROUND - NAIL_H0 - 300 + dy, -32.0, 0.72)
    hitp = lambda i: (NAIL_X[i], GROUND - NAIL_H0, 0.0, 0.72)
    kf = [(A, REST), (c[0] - 1.2, REST), (c[0] - 0.4, top(0))]
    for i in range(3):
        kf += [(c[i] - 0.2, top(i, -20))]
        if c[i] - 0.2 <= t < c[i]:
            u = ei((t - c[i] + 0.2) / 0.2); p0, p1 = top(i, -20), hitp(i)
            return tuple(lerp(p0[j], p1[j], u) for j in range(4))
        kf += [(c[i], (NAIL_X[i], GROUND - NAIL_H1, 0.0, 0.72)), (c[i] + 0.3, (NAIL_X[i] + 10, GROUND - NAIL_H1 - 70, -8.0, 0.72))]
        if i < 2: kf += [(c[i + 1] - 0.9, top(i + 1))]
    kf += [(c[2] + 1.2, (CX, 760.0, -6.0, 0.42)), (c[2] + 2.0, (CX, 760.0, 0.0, 0.42))]   # 三锤之后：缩小、抬高，让出钉子上方的位置
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
    A_ = aa[y0:y1, x0:x1]; P_ = pm[y0:y1, x0:x1] * a
    fr.sprites.append((np.where(A_[..., None] > 1e-3, P_ / np.maximum(A_[..., None], 1e-3), 0), A_, x0, y0))
    fr.B[y0:y1, x0:x1] += (A_ * 0.18)[..., None] * np.array(GOLD, np.float32)

def draw_nail(fr, i, t, a):
    x = NAIL_X[i]; h = nail_h(i, t); top = GROUND - h
    fr.fillpoly([(x - 8, GROUND), (x - 8, top + 10), (x + 8, top + 10), (x + 8, GROUND)], C(150, 156, 172), a, 'L')
    fr.line((x - 3, GROUND), (x - 3, top + 12), C(230, 235, 245), a * 0.7, 2)
    fr.rrect_fill(x - 38, top - 4, x + 38, top + 12, 6, C(190, 196, 210), a, 'L'); fr.line((x - 34, top - 2), (x + 34, top - 2), WHITE, a * 0.8, 2)
    c = CUE[STRIKES[i]]
    if t > c:
        r = np.random.default_rng(i + 30); u = eo((t - c) / 0.25)
        for k in range(4):
            sgn = -1 if k % 2 else 1; pts = [(x, GROUND)]
            for j in range(4):
                px_, py_ = pts[-1]; pts.append((px_ + sgn * (14 + r.random() * 26) * u, py_ + (r.random() - 0.3) * 10 * u))
            fr.poly(pts, GOLD, a * 0.55, 2)
    return top

def sh_post2(fr, t):
    a = shot(t, 'post2')
    if a <= 0: return
    t0 = S['post2']; post_card(fr, t, a * (1 - 0.5 * eo((t - t0 - 2.5) / 0.6)), t0 + 0.1, 600, 420, lines_n=3)
    words = ['龙头地位', '护城河', '低市盈率', '现金流', '股票回购']
    l61 = LN['L61']; tw0 = l61['chunks'][2][1] if len(l61['chunks']) > 2 else t0 + 4
    pos = [(250, 1120), (540, 1090), (830, 1120), (360, 1240), (720, 1240)]
    for k, (wd, (x, y)) in enumerate(zip(words, pos)):
        chip(fr, x, y, wd, GOLD, a * eo((t - tw0 - k * 0.45) / 0.35), 34, 0.12)
    btext(fr, t, '每一次买入，都有令人信服的理由', CX, ZB, 56, 'serif_black', WHITE, a, l61['chunks'][1][1] if len(l61['chunks']) > 1 else t0 + 2, glow=0.12)

def sh_hammer(fr, t):
    t0 = S['hammer']; tend = S['inv']
    a = env(t, t0 - 0.05, tend, 0.35, 0.35)
    if a <= 0: return
    tag(fr, t, '铁锤人倾向', a, t0)
    aq = a * (1 - eio((t - CUE['L63a'] + 1.6) / 0.5))
    if aq > 0:
        btext(fr, t, '手里只有一把锤子', CX, 380, 64, 'serif_black', WHITE, aq, CH('L62', 2) if len(LN['L62']['chunks']) > 2 else t0 + 3, glow=0.1)
        btext(fr, t, '看什么都像钉子', CX, 490, 64, 'serif_black', GOLD, aq, CH('L62', 3) if len(LN['L62']['chunks']) > 3 else t0 + 5, glow=0.35, grad=GOLDG)
    # 「买入」印章与五个词飞来合成锤子
    A = t0 + 0.8
    if t0 - 0.2 < t < A + 0.6:
        u = eio((t - t0 + 0.2) / 1.0)
        for k, (sx, sy) in enumerate([(150, 640), (930, 660), (140, 1300), (940, 1320), (540, 1400)]):
            stamp(fr, t, '买入', lerp(sx, CX, u), lerp(sy, 960, u), int(56 * (1 - 0.3 * u)), t0 - 0.2 + k * 0.05, GOLD, -10 + k * 4, a * (1 - eio((t - A) / 0.5)))
    ah = a * eo((t - A) / 0.5)
    if ah > 0:
        if t < A + 0.7: fr.glow((CX, 960), 200, GOLD2, (1 - eo((t - A) / 0.7)) * 0.9 * a)
        draw_hammer(fr, t, ah)
    ag = env(t, _t('L63a') - 0.8, tend, 0.5, 0.35)
    if ag > 0:
        fr.line((90, GROUND), (990, GROUND), C(150, 160, 190), ag * 0.6, 2)
        fr.fillpoly([(90, GROUND), (990, GROUND), (990, GROUND + 30), (90, GROUND + 30)], C(40, 34, 30), ag * 0.8, 'L')
        t64, t65 = _t('L64'), _t('L65')
        ch65 = [c[1] for c in LN['L65']['chunks']]
        for i in range(3):
            ai_ = ag * eo((t - _t(STRIKES[i]) + 0.5) / 0.4)
            if ai_ <= 0: continue
            top = draw_nail(fr, i, t, ai_)
            chip(fr, NAIL_X[i], GROUND + 90, NAIL_LAB[i], GOLD, ai_, 26)
            sparks(fr, t, CUE[STRIKES[i]], NAIL_X[i], GROUND - NAIL_H0, seed=i, big=0.9 + 0.12 * i)
            y = top - 90
            if t64 < t < t65 + 0.05:
                check(fr, NAIL_X[i], y, 54, (t - t64 - i * 0.18) / 0.3, GOLD, ai_, 6)
            elif t >= t65:
                tq = ch65[min(i, len(ch65) - 1)] if ch65 else t65 + i
                u = eo((t - tq) / 0.35)
                if u <= 0: check(fr, NAIL_X[i], y, 54, 1.0, GOLD, ai_, 6)
                else:
                    fr.text('?', NAIL_X[i], y, int(90 * (0.6 + 0.4 * u)), 'serif_black', RED2, ai_ * u, mode='L', glow=0.5)
                    fr.text(NAIL_Q[i], NAIL_X[i], y - 90, 26, 'sans_black', RED2, ai_ * u)
        if t > t64 and t < _t('L66') + 0.2:
            btext(fr, t, '这些判断，都有自己的道理', CX, ZB, 58, 'serif_black', WHITE, ag * (1 - eio((t - t65 + 0.3) / 0.3)), t64, glow=0.12)
        if t > _t('L66'):
            btext(fr, t, '几个熟悉的指标，概括不了一门复杂的生意', CX, ZB, 50, 'serif_black', GOLD, ag, _t('L66') + 0.1, glow=0.3)

def sh_inv(fr, t):
    a = shot(t, 'inv')
    if a <= 0: return
    tag(fr, t, '反过来想', a, S['inv'])
    t0, t68, t69 = S['inv'], _t('L68'), _t('L69')
    flip = abs(math.cos(math.pi * eio((t - t0 - 0.2) / 0.9)))
    btext(fr, t, '如果三年后，它再跌一半', CX, 470, 62, 'serif_black', WHITE, a, t0 + 1.0, glow=0.15)
    fr.text('会是因为什么？', CX, 560, 56, 'serif_black', RED2, a * eo((t - t0 - 2.5) / 0.4) * flip ** 0.3, mode='L', glow=0.35)
    qs = ['买入价格太贵？', '盈利无法持续？', '护城河正在被侵蚀？']
    l68 = LN['L68']; n = len(qs); d = l68['t1'] - l68['t0']
    for k, q in enumerate(qs):
        ts = l68['t0'] + d * k / n; ak = a * eo((t - ts) / 0.35) * (1 - eio((t - t69 + 0.3) / 0.4))
        chip(fr, CX, 760 + k * 130, q, [GOLD, C(230, 160, 110), RED2][k], ak, 40, 0.1)
    if t > t69 - 0.1:
        ar = a * eo((t - t69) / 0.5); x0, y0, x1, y1 = 170, 700, 910, 1300
        fr.rrect_fill(x0, y0, x1, y1, 18, C(30, 28, 24), ar * 0.9, 'L'); fr.rrect(x0, y0, x1, y1, 18, GOLD, ar * 0.6, 2)
        fr.text('给自己的做空报告', CX, y0 + 80, 54, 'serif_black', PAPER, ar)
        for j in range(3):
            yk = y0 + 220 + j * 120
            fr.text('①②③'[j], x0 + 70, yk, 44, 'sans_black', GOLD, ar); fr.line((x0 + 120, yk + 26), (x1 - 60, yk + 26), DIM, ar * 0.6, 1)
        if int(t * 2.5) % 2 == 0: fr.line((x0 + 130, y0 + 196), (x0 + 130, y0 + 244), WHITE, ar, 3)

# ================================================================ 问题二
T2 = '问题二 · 股价下跌，就说明买错了吗？'

def sh_q2(fr, t):
    chapter_card(fr, t, 'q2', 'QUESTION 02', '股价下跌', '就说明当初买错了吗？')
    a = shot(t, 'q2')
    t71 = _t('L71')
    btext(fr, t, '未必。', CX, 1250, 110, 'serif_black', GOLD, a, t71, glow=0.45, grad=GOLDG, dur=0.4)

def price_noise(t, k=0):
    return sum(math.sin(t * f + p) * w for f, p, w in ((3.1, 0.3, 1.0), (5.7, 1.1, 0.6), (9.3, 2.0, 0.35))) + k

def sh_noise(fr, t):
    a = shot(t, 'noise')
    if a <= 0: return
    tag(fr, t, T2, a, S['noise'])
    t0 = S['noise']
    tilt = 7 * price_noise(t)
    draw_scale(fr, t, CX, 900, 340, tilt, a * eo((t - t0 - 0.2) / 0.5), '每天的报价', '内在价值')
    xs = np.linspace(140, 940, 120); ys = 1300 - 40 * np.array([price_noise(t - 2 + x * 0.004) for x in xs])
    fr.poly(np.stack([xs, ys], 1), C(160, 180, 230), a * 0.6, 2); fr.line((140, 1300), (940, 1300), GOLD, a * 0.7, 2)
    fr.text('价格', 150, 1220, 28, 'sans_med', C(160, 180, 230), a, anchor='l'); fr.text('价值', 930, 1270, 28, 'sans_black', GOLD, a, anchor='r')
    btext(fr, t, '报价每天在变，价值不会同步改变', CX, ZB, 56, 'serif_black', WHITE, a, t0 + 0.2, glow=0.12)

def sh_drops(fr, t):
    a = shot(t, 'drops')
    if a <= 0: return
    tag(fr, t, T2, a, S['noise'])
    t0, t74 = S['drops'], _t('L74')
    ch = [c[1] for c in LN['L73']['chunks']]
    labs = [('竞争优势正在消失', RED2), ('盈利预期过于乐观', C(240, 160, 90)), ('恐慌与短期情绪', C(150, 170, 210))]
    for k, (lab, col) in enumerate(labs):
        ts = ch[min(k * max(1, len(ch) // 3), len(ch) - 1)] if ch else t0 + k * 2
        u = eo((t - ts) / 1.2); x0 = 160 + k * 290
        xs = np.linspace(x0, x0 + 220, 40); drop = [1.0, 0.8, 0.6][k]
        ys = 700 + (xs - x0) / 220 * 380 * drop * u + np.sin(xs * 0.2 + k) * 8
        hl = 1.0 if (k == 2 or t < t74) else 0.35
        fr.poly(np.stack([xs[:max(2, int(40 * u))], ys[:max(2, int(40 * u))]], 1), col, a * hl, 4)
        fr.text(lab, x0 + 110, 1180, 30, 'sans_black', col, a * eo((t - ts - 0.4) / 0.4) * hl)
    if t > t74:
        ak = a * eo((t - t74) / 0.4)
        draw_scale(fr, t, 740, 1000, 0, 0, 0, '', '')
        chip(fr, 740, 1290, '反而可能是机会', TEAL, ak, 36, 0.12)
    btext(fr, t, '下跌，有三种', CX, ZB, 64, 'serif_black', WHITE, a, t0 + 0.1, glow=0.15)

def sh_band(fr, t):
    a = shot(t, 'band')
    if a <= 0: return
    tag(fr, t, T2, a, S['noise'])
    t0, t76, t77 = S['band'], _t('L76'), _t('L77')
    btext(fr, t, '我们对未来的判断，可能是错的', CX, ZB, 56, 'serif_black', WHITE, a, t0 + 0.2, glow=0.12)
    py = lambda v: 1340 - v * 6
    vc = 85
    w = 4 + 26 * eo((t - t76) / 1.2)
    fr.rrect_fill(160, py(vc + w), 920, py(vc - w), 8, GOLD, a * 0.18); fr.line((160, py(vc)), (920, py(vc)), GOLD, a * 0.9, 3)
    fr.text('内在价值' if t < t76 else '内在价值：一个区间，而非一个数字', 170, py(vc + w) - 30, 32, 'sans_black', GOLD, a, anchor='l', mode='L', glow=0.25)
    if t > t77:
        u = eo((t - t77) / 0.6); pb = 40
        fr.line((160, py(pb)), (920, py(pb)), WHITE, a * u, 3); fr.text('买入价', 170, py(pb) + 34, 32, 'sans_black', WHITE, a * u, anchor='l')
        xb = 860; ya, yb = py(vc - w), py(pb)
        fr.line((xb, ya), (xb, lerp(ya, yb, u)), TEAL, a, 4); fr.line((xb - 14, ya), (xb + 14, ya), TEAL, a * u, 4); fr.line((xb - 14, yb), (xb + 14, yb), TEAL, a * u, 4)
        fr.text('安全边际', xb - 26, (ya + yb) / 2, 36, 'sans_black', TEAL, a * u, anchor='r', mode='L', glow=0.3)

def sh_guarantee(fr, t):
    a = shot(t, 'guarantee')
    if a <= 0: return
    tag(fr, t, T2, a, S['noise'])
    t0, t79 = S['guarantee'], _t('L79')
    ag = a * (1 - eio((t - t79 + 0.3) / 0.4))
    if ag > 0:
        fr.rrect_fill(260, 700, 820, 1100, 14, C(36, 34, 30), ag * 0.9, 'L'); fr.rrect(260, 700, 820, 1100, 14, PAPER, ag * 0.6, 2)
        fr.text('保 证 书', 540, 800, 70, 'serif_black', PAPER, ag)
        for j in range(3): fr.line((320, 900 + j * 50), (760, 900 + j * 50), DIM, ag * 0.6, 1)
        stamp(fr, t, '安全边际 ≠ 保证', 560, 960, 64, t0 + 1.4, RED, -10, ag)
    am = a * eo((t - t79) / 0.4)
    if am > 0:
        x0, y0, cw, chh = 210, 650, 330, 260
        fr.text('好结果', x0 + cw / 2, y0 - 36, 30, 'sans_black', TEAL, am); fr.text('坏结果', x0 + cw * 1.5, y0 - 36, 30, 'sans_black', RED2, am)
        fr.text('好判断', x0 - 20, y0 + chh / 2, 30, 'sans_black', GOLD, am, anchor='r'); fr.text('坏判断', x0 - 20, y0 + chh * 1.5, 30, 'sans_black', DIM, am, anchor='r')
        cells = [('应得的回报', TEAL), ('暂时亏钱', C(240, 160, 90)), ('碰巧赚钱', C(240, 160, 90)), ('应得的教训', RED2)]
        for k, (s, col) in enumerate(cells):
            cx_, cy_ = x0 + (k % 2) * cw, y0 + (k // 2) * chh
            hl = k in (1, 2)
            fr.rrect(cx_ + 8, cy_ + 8, cx_ + cw - 8, cy_ + chh - 8, 16, col, am * (1 if hl else 0.4), 3 if hl else 1)
            fr.text(s, cx_ + cw / 2, cy_ + chh / 2, 40 if hl else 34, 'serif_black', col, am * (1 if hl else 0.5), mode='L', glow=0.25 if hl else 0)
    btext(fr, t, '安全边际，不是保证书', CX, ZB, 64, 'serif_black', WHITE, a, t0 + 0.1, glow=0.15)

def sh_branches(fr, t):
    a = shot(t, 'branches')
    if a <= 0: return
    tag(fr, t, T2, a, S['noise'])
    t0, t81, t82 = S['branches'], _t('L81'), _t('L82')
    btext(fr, t, '看错了价值，还是价格暂时过低？', CX, ZB, 56, 'serif_black', WHITE, a, t0 + 0.2, glow=0.12)
    fr.circle((CX, 640), 12, WHITE, a, -1)
    for k, (lab, ex, col, ts) in enumerate([('优势依然成立', 800, TEAL, t81), ('事实已被推翻', 280, RED2, t82)]):
        u = eo((t - t0 - 0.8) / 0.8)
        fr.line((CX, 640), (lerp(CX, ex, u), lerp(640, 820, u)), col, a * (1 if t > ts else 0.5), 3)
        chip(fr, ex, 860, lab, col, a * u, 32)
    if t > t81:
        ak = a * eo((t - t81) / 0.5)
        draw_scale(fr, t, 800, 1130, 150, 12 * eo((t - t81) / 1.0), ak, '价格', '价值', 0.6, 1.1)
        fr.text('更好的机会', 800, 1310, 30, 'sans_black', TEAL, ak)
    if t > t82:
        for j in range(4):
            stamp(fr, t, '补仓', 240 + (j % 2) * 90, 1000 + j * 70, 44, t82 + 0.6 + j * 0.5, lerpc(RED, C(90, 60, 60), j / 3), -8 + j * 4, a)
        fr.text('不愿承认错误', 280, 1310, 30, 'sans_black', RED2, a * eo((t - t82 - 1.5) / 0.4))

def sh_line(fr, t):
    a = shot(t, 'line')
    if a <= 0: return
    tag(fr, t, T2, a, S['noise'])
    t0, t84 = S['line'], CUE['L84']
    am = a * (1 - eio((t - t84 + 0.4) / 0.4))
    if am > 0:
        u = eo((t - t0 - 0.3) / 0.8)
        fr.line((CX, 980 - 300 * u), (CX, 980 + 300 * u), WHITE, am, 2); fr.glow((CX, 980), 40, WHITE, am * 0.3)
        btext(fr, t, '耐心', 300, 980, 96, 'serif_black', TEAL, am, t0 + 0.6, glow=0.35)
        btext(fr, t, '固执', 780, 980, 96, 'serif_black', RED2, am, t0 + 1.0, glow=0.35)
        btext(fr, t, '只有一线之隔', CX, ZB, 64, 'serif_black', WHITE, am, t0 + 0.2, glow=0.12)
    golden_line(fr, t, '区分它们的，不是涨跌', '是企业的事实，有没有改变', a * eo((t - t84) / 0.4), t84)

# ================================================================ 问题三
T3 = '问题三 · 真正的价值投资'

def sh_q3(fr, t):
    chapter_card(fr, t, 'q3', 'QUESTION 03', '真正的价值投资', '究竟是什么？')

def sh_principles(fr, t):
    a = shot(t, 'principles')
    if a <= 0: return
    tag(fr, t, T3, a, S['principles'])
    t0 = S['principles']
    btext(fr, t, '买股票，就是买下一门生意', CX, ZB, 62, 'serif_black', WHITE, a, t0 + 0.1, glow=0.15)
    ch = [c[1] for c in LN['L86']['chunks']] + [LN['L86']['t1']] * 3
    for k, (s, sub) in enumerate([('它如何赚钱', '理解生意'), ('优势能否持续', '竞争优势'), ('未来创造多少现金', '估算价值')]):
        ts = ch[min(k + 1, len(ch) - 1)] if len(ch) > 1 else t0 + 1 + k
        ak = a * eo((t - ts + 0.2) / 0.4); y = 720 + k * 190
        fr.circle((200, y), 34, GOLD, ak, 3); fr.text(str(k + 1), 200, y, 40, 'num', GOLD, ak, mode='L', glow=0.3)
        fr.text(s, 270, y - 18, 50, 'serif_black', WHITE, ak, anchor='l'); fr.text(sub, 270, y + 32, 28, 'sans_med', GOLD, ak, anchor='l')

# 锤子碎片 → 天平
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
    L = [math.dist(a_, b_) for a_, b_ in segs]; cum = np.cumsum([0] + L); tot = cum[-1]
    s = u * tot; k = np.clip(np.searchsorted(cum, s) - 1, 0, len(segs) - 1)
    f = (s - cum[k]) / np.maximum(np.array(L)[k], 1e-6)
    A = np.array([segs[i][0] for i in k]); B = np.array([segs[i][1] for i in k])
    return A[:, 0] + (B[:, 0] - A[:, 0]) * f, A[:, 1] + (B[:, 1] - A[:, 1]) * f

def scale_segs(cx, cy, sz):
    s = [((cx, cy - sz * 0.62), (cx, cy + sz * 0.62)), ((cx - sz * 0.3, cy + sz * 0.62), (cx + sz * 0.3, cy + sz * 0.62)),
         ((cx - sz, cy - sz * 0.62), (cx + sz, cy - sz * 0.62))]
    for sx in (cx - sz, cx + sz):
        hy = cy - sz * 0.62 + sz * 0.45
        s += [((sx, cy - sz * 0.62), (sx - sz * 0.28, hy)), ((sx, cy - sz * 0.62), (sx + sz * 0.28, hy))]
        th = np.linspace(0, math.pi, 10); pts = [(sx + sz * 0.3 * math.cos(a_), hy + sz * 0.1 * math.sin(a_)) for a_ in th]
        s += list(zip(pts[:-1], pts[1:]))
    return s

def sh_rebuild(fr, t):
    a = shot(t, 'rebuild')
    if a <= 0: return
    tag(fr, t, T3, a, S['principles'])
    t0 = S['rebuild']; P = hammer_particles(); x0, y0, sc = CX, 1000.0, 0.6
    if t < t0 + 0.6: draw_hammer(fr, t, a * (1 - eo((t - t0) / 0.5)), pose=(x0, y0, 0.0, sc))
    bx = x0 + P['x'] * sc; by = y0 + P['y'] * sc; u = max(t - t0 - 0.3, 0)
    ex = bx + P['vx'] * 200 * (1 - math.exp(-u * 1.8)); ey = by + P['vy'] * 200 * (1 - math.exp(-u * 1.8))
    g = eio((t - t0 - 1.2) / 1.6)
    tx_, ty_ = along(scale_segs(CX, 960, 330), P['u']); tx_ += P['j'] * 3; ty_ += P['j'] * 3
    px_, py_ = lerp(ex, tx_, g), lerp(ey, ty_, g)
    if t > t0 + 0.2:
        fr.splat(px_, py_, P['col'] * (1 - g * 0.4) + np.array(GOLD2) * g * 0.4, a * 0.9 * (1 - eo((t - t0 - 3.4) / 0.6)), 'E')
        fr.splat(px_, py_, P['col'], a * 0.35, 'B')
    if t < t0 + 0.6: fr.glow((x0, y0 - 60), 180, GOLD2, max(0, 1 - (t - t0) / 0.6) * a)
    ad = a * eo((t - t0 - 3.0) / 0.6)
    draw_scale(fr, t, CX, 960, 330, 6 * eo((t - t0 - 3.2) / 1.0), ad, '价格', '保守估计的价值', 0.7, 1.0)
    chip(fr, CX, 1290, '为判断错误，留下安全边际', TEAL, ad * eo((t - t0 - 3.6) / 0.5), 34, 0.12)
    btext(fr, t, '能力圈 · 合理价格 · 安全边际', CX, ZB, 58, 'serif_black', GOLD, a, t0 + 1.0, glow=0.3, grad=GOLDG)

def sh_diversify(fr, t):
    a = shot(t, 'diversify')
    if a <= 0: return
    tag(fr, t, T3, a, S['principles'])
    t0 = S['diversify']; u = eio((t - t0 - 1.8) / 1.6)
    pos = [(CX, 960), (300, 800), (780, 800), (300, 1140), (780, 1140)]
    for k, (x, y) in enumerate(pos):
        if k == 0: R = lerp(300, 120, u); xx, yy = CX, 960
        else: R = 120 * u; xx, yy = lerp(CX, x, u), lerp(960, y, u)
        if R < 2: continue
        ring(fr, xx, yy, R, GOLD if k == 0 else TEAL, a, th=3); fr.glow((xx, yy), R * 0.5, GOLD if k == 0 else TEAL, a * 0.1)
    fr.text('风险管理', CX, 960, 50, 'serif_black', GOLD, a * (1 - u * 0.0), mode='L', glow=0.3)
    btext(fr, t, '做到这些，也无法保证每一次都成功', CX, ZB, 54, 'serif_black', WHITE, a, t0 + 0.2, glow=0.12)
    fr.text('适度分散', CX, 1330, 36, 'sans_black', TEAL, a * eo((t - t0 - 3.0) / 0.4))

def sh_finale(fr, t):
    a = shot(t, 'finale')
    if a <= 0: return
    t0 = S['finale']; t1 = LN['L89']['t1']
    a1 = a * (1 - eio((t - t1 - 0.2) / 0.5))
    btext(fr, t, '真正的价值投资', CX, 620, 64, 'serif_med', C(225, 220, 210), a1, t0 + 0.1)
    btext(fr, t, '从来不是追求永远正确', CX, 760, 76, 'serif_black', WHITE, a1, t0 + 0.8, glow=0.1)
    ch = LN['L89']['chunks']; tb = ch[1][1] if len(ch) > 1 else t0 + 3
    btext(fr, t, '而是在不确定的世界里', CX, 940, 66, 'serif_med', C(225, 220, 210), a1, tb)
    btext(fr, t, '争取长期合理的回报', CX, 1080, 86, 'serif_black', GOLD, a1, tb + 1.4, glow=0.45, grad=GOLDG)
    a2 = a * eo((t - t1 - 0.5) / 0.6)
    if a2 > 0:
        L3 = [('好公司，不一定是好投资', WHITE), ('好投资，也不一定立刻带来好回报', WHITE), ('真正的价值投资', GOLD), ('是在不确定的世界里', GOLD), ('尽可能作出有利于长期回报的决策', GOLD)]
        for k, (s, col) in enumerate(L3):
            btext(fr, t, s, CX, 640 + k * 130, 56 if k > 1 else 60, 'serif_black', col, a2, t1 + 0.5 + k * 0.7, glow=0.35 if col == GOLD else 0.1,
                  grad=GOLDG if col == GOLD else None)
    dust(fr, t, a * 1.3)

# ================================================================ 尾声
def sh_epilogue(fr, t):
    a = shot(t, 'epilogue')
    if a <= 0: return
    t0, t91, t92 = S['epilogue'], _t('L91'), CUE['L92']
    c = CASES[0]; box = (140, 640, 940, 1080)
    am = a * (1 - eio((t - t92 + 0.3) / 0.4)) * eo((t - t0 - 0.2) / 0.5)
    if am > 0:
        draw_chart(fr, t, c, am, 0, box, d=c['rev'][-1][1], mini=False)
        px, py = case_xf(c, box)
        sx, sy = chart_layout(c, box, 58)['stamp']
        stamp(fr, t, '买入', sx, sy, 58, t0, GOLD, -10, am)
        fr.text('截至 2026.11.18 · 股价不含分红与实物分派', CX, 1170, 26, 'sans_light', DIM, am)
        if t > t91:
            for k, s in enumerate(['业务在变', '竞争在变', '预期在变']):
                chip(fr, 260 + k * 280, 1280, s, C(160, 180, 230), am * eo((t - t91 - k * 0.6) / 0.4), 30)
    btext(fr, t, '八年过去，价格回到了原点', CX, ZB, 58, 'serif_black', WHITE, a * (1 - eio((t - t92 + 0.3) / 0.3)), t0 + 0.4, glow=0.12)
    golden_line(fr, t, '价格可以回到原点', '思考不必停在原点', a * eo((t - t92) / 0.4), t92)

def sh_hardest(fr, t):
    a = shot(t, 'hardest')
    if a <= 0: return
    t0, t94 = S['hardest'], _t('L94')
    btext(fr, t, '最难的，从来不是找到一家好公司', CX, ZB, 56, 'serif_black', WHITE, a, t0 + 0.1, glow=0.12)
    ch = [c[1] for c in LN['L93']['chunks']]
    tb = ch[1] if len(ch) > 1 else t0 + 3
    a1 = a * (1 - eio((t - t94 + 0.3) / 0.4))
    for k, s in enumerate(['它为什么好', '能好多久', '究竟值多少钱']):
        btext(fr, t, s, CX, 720 + k * 170, 80, 'serif_black', GOLD if k == 2 else WHITE, a1, tb + k * 0.8, glow=0.4 if k == 2 else 0.1, grad=GOLDG if k == 2 else None)
    a2 = a * eo((t - t94) / 0.5)
    if a2 > 0:
        draw_scale(fr, t, CX, 980, 300, 3 * math.sin(t * 0.8), a2, '判断', '价格与风险', 1.0, 1.0)

def sh_last(fr, t):
    t0 = S['last']; a = env(t, t0 - 0.05, S['card'], 0.35, 0.45)
    if a <= 0: return
    btext(fr, t, '这或许就是价值投资', CX, 780, 70, 'serif_black', WHITE, a, t0 + 0.1, glow=0.12)
    btext(fr, t, '最深刻，也最难掌握的地方', CX, 920, 76, 'serif_black', GOLD, a, t0 + 1.2, glow=0.45, grad=GOLDG)
    fr.text('你买过的好公司，后来怎么样了？', CX, 1150, 40, 'sans_med', GOLD2, a * eo((t - t0 - 2.6) / 0.5))

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
HIDE = {'L06', 'L15', 'L24', 'L34', 'L54', 'L60', 'L71', 'L84', 'L89', 'L92', 'L95'}
HIDE_CHUNK = set()
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

CHAPTERS = [(0, '序章  ·  雪球热帖'), (S['q1_card'], '问题一'), (S['q2_card'], '问题二'), (S['q3_card'], '问题三'), (S['epilogue'] - 0.5, '尾声')]
def chapter(fr, t):
    lab = [l for t0, l in CHAPTERS if t >= t0][-1]
    a = 0.75 * (1 - eio((t - S['card'] + 0.5) / 0.5)) * eo((t - 0.6) / 0.5)
    fr.text(lab, 52, 92, 26, 'sans_med', C(200, 200, 210), a, anchor='l')

HUD = Hud(scale=1.0, frame_w=W)
CUTS = sorted(set([v for k, v in S.items() if k not in ('post',)]))

def zoom_blur(out, k):
    """转场：径向推镜模糊（多层放大叠加）"""
    acc = out.copy(); wsum = 1.0
    for j in range(1, 5):
        z = 1 + 0.03 * j * k
        M_ = cv2.getRotationMatrix2D((W / 2, H * 0.48), 0, z)
        acc += cv2.warpAffine(out, M_, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT) * (1 - j * 0.15)
        wsum += 1 - j * 0.15
    return acc / wsum

SHOTS = [sh_post, sh_books, sh_tencent, sh_unwilling, sh_catl, sh_ali, sh_zp, sh_gold, sh_nv, sh_wall, sh_title,
         lambda fr, t: chapter_card(fr, t, 'q1', 'QUESTION 01', '买了好公司', '为什么还可能亏钱？'),
         sh_anchor, sh_scale, sh_twoscales, sh_gold1, sh_tenyear, sh_moat, sh_quotes, sh_newmoat, sh_keep, sh_tech, sh_ibm,
         sh_baskets, sh_circle, sh_story, sh_cars, sh_air, sh_capital, sh_lowpe, sh_stair, sh_q99, sh_expect, sh_post2,
         sh_hammer, sh_inv, sh_q2, sh_noise, sh_drops, sh_band, sh_guarantee, sh_branches, sh_line, sh_q3, sh_principles,
         sh_rebuild, sh_diversify, sh_finale, sh_epilogue, sh_hardest, sh_last]
STRIKE_KEYS = ['L63a', 'L63b', 'L63c']

def render(t):
    fr = Frame(t)
    bg = background(t)
    imp = impact(t, 0.85)
    dust(fr, t, 0.55)
    for f in SHOTS: f(fr, t)
    draw_card_text(fr, t)
    chapter(fr, t)
    fr.flash = 0.03 * imp
    fr.ca = 4 * impact(t, 1.3)
    fr.streak = 0.3 + 0.9 * imp
    for key in STRIKE_KEYS:                 # 锤击震屏
        u = t - CUE[key]
        if 0 <= u < 0.4:
            amp = 16 * math.exp(-u * 11)
            fr.shake = (int(amp * math.sin(u * 90)), int(amp * 0.5 * math.cos(u * 70)))
    out = finish(fr, bg, bloom_k=1.0 + 0.8 * imp, vignette=VIG, grain=GRAIN[int(t * 30) % 6])
    scene_card(fr, t, out)
    kz = max([math.exp(-((t - c) / 0.1) ** 2) for c in CUTS if abs(t - c) < 0.4] + [0])
    if kz > 0.03: out = zoom_blur(out, kz)
    z = 1.0 + 0.012 * math.sin(t * 0.4) + 0.022 * impact(t)
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
