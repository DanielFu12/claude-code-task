"""社会地位象征型护城河 —— 无配音动态视觉短片（1920×1080 · 30fps · 6:16）

每个 sc_* 函数是一段分镜；时间点全部对齐 timeline.py 里的小节线（120 BPM，一小节 2 秒）。
"""
import math, os, sys
import numpy as np, cv2
from engine import *
from timeline import DUR, BEAT, BAR, SEGMENTS, IMPACTS, RISERS, DROPOUTS, CHAPTERS, ENERGY_OF, segment_at

NFR = int(DUR * FPS)
SILVER = C(200, 210, 230)
NAMED = {'gold': GOLD, 'cyan': CYAN, 'violet': VIOLET, 'white': WHITE, 'red': RED, 'magenta': MAGENTA}
IMP = [(a, k, NAMED[c]) for a, k, c in IMPACTS]

# ============================================================== music helpers
_EK = []
for a, b, st, _p in SEGMENTS:
    _EK += [(a, ENERGY_OF[st]), (b - 0.05, ENERGY_OF[st])]

def energy(t):
    return keys(t, _EK)

def beat_pulse(t, decay=0.13):
    if any(a <= t < b for a, b in DROPOUTS): return 0.0
    return math.exp(-(t % BEAT) / decay) * cl((energy(t) - 0.3) / 0.4)

def bar_pulse(t, decay=0.25):
    return math.exp(-(t % BAR) / decay) * cl((energy(t) - 0.2) / 0.4)

def count(t, t0, dur, v):
    return v * eo((t - t0) / dur)

# ============================================================== stars
RNG = np.random.default_rng(1234)
NST = 1400
ST_X = RNG.uniform(-1.8, 1.8, NST); ST_Y = RNG.uniform(-1.1, 1.1, NST); ST_Z0 = RNG.uniform(0, 1, NST)
ST_COL = np.array([lerpc(WHITE, [GOLD2, CYAN, WHITE, VIOLET, GOLD][i % 5], 0.4) for i in range(NST)], np.float32)

def star_speed(t):
    v = 0.03 + 0.03 * energy(t)
    for ti, k, _ in IMP:
        if t >= ti: v += k * 1.5 * math.exp(-(t - ti) / 0.55)
    for a, b in RISERS:
        if a <= t <= b: v += 0.4 * ei((t - a) / (b - a))
    return v

_ts = np.arange(NFR + 2) / FPS
ST_S = np.concatenate([[0], np.cumsum([star_speed(x) / FPS for x in _ts])])

def draw_stars(f, t, a=1.0):
    S = ST_S[min(int(t * FPS), NFR)]
    z = (ST_Z0 - S) % 1.0 + 0.03
    fx = W * 0.32
    sx = W / 2 + ST_X / z * fx; sy = H / 2 + ST_Y / z * fx
    b = np.clip((1.05 - z) ** 2.2, 0, 1) * (0.5 + 0.35 * beat_pulse(t, .18)) * a
    tw = 0.75 + 0.25 * np.sin(t * 3 + ST_X * 40)
    f.splat(sx, sy, ST_COL, b * tw * 0.85, 'L')
    near = z < 0.25
    f.splat(sx[near], sy[near], ST_COL[near], b[near] * 0.8, 'E')
    v = star_speed(t)
    if v > 0.25:
        z2 = z + min(v * 0.06, 0.25)
        sx2 = W / 2 + ST_X / z2 * fx; sy2 = H / 2 + ST_Y / z2 * fx
        al = cl((v - 0.25) / 1.0)
        idx = np.where((z < 0.7) & (abs(sx - W / 2) < W) & (abs(sy - H / 2) < H))[0][:450]
        for i in idx:
            f.line((sx2[i], sy2[i]), (sx[i], sy[i]), ST_COL[i], al * float(b[i]) * 1.2, 1)

# ============================================================== background
NB1 = fbm(512, 288, 11, 6, 3); NB2 = fbm(512, 288, 22, 6, 3); NB3 = fbm(512, 288, 33, 5, 5)
BGK = [
    (0, (10, 20, 60), (40, 12, 60), .7), (12, (25, 12, 50), (50, 12, 70), .6), (15.8, (15, 8, 30), (30, 8, 40), .45),
    (16.2, (170, 110, 25), (100, 30, 130), 1.4), (21, (70, 45, 90), (30, 50, 120), 1.0),
    (24, (20, 50, 120), (60, 25, 120), 1.0), (38, (15, 70, 100), (50, 25, 110), 1.0),
    (50, (20, 25, 70), (60, 20, 80), .8), (56, (15, 90, 90), (80, 40, 130), 1.05),
    (64, (80, 60, 20), (40, 30, 100), .95), (78, (100, 25, 120), (25, 60, 140), 1.0),
    (93.6, (30, 15, 50), (20, 25, 60), .55), (94.2, (20, 110, 160), (110, 30, 150), 1.35), (100, (20, 70, 120), (80, 30, 120), 1.0),
    (110, (40, 30, 90), (70, 30, 60), .9), (122, (100, 70, 20), (20, 60, 130), 1.05),
    (140, (30, 60, 90), (60, 50, 30), .95), (159.6, (20, 20, 40), (30, 20, 50), .5),
    (160.2, (90, 110, 160), (90, 90, 140), 1.35), (166, (35, 55, 120), (70, 70, 110), .95),
    (178, (15, 80, 75), (85, 65, 20), .95), (189.8, (15, 80, 75), (85, 65, 20), .95),
    (190.2, (160, 15, 40), (80, 10, 50), 1.3), (196, (90, 20, 45), (50, 15, 60), .95),
    (198, (25, 45, 100), (55, 25, 100), .95), (216, (12, 12, 35), (25, 12, 45), .5),
    (224, (40, 30, 110), (90, 30, 90), .85), (235.6, (25, 15, 50), (40, 15, 50), .55),
    (236.2, (140, 25, 125), (20, 90, 150), 1.35), (242, (70, 30, 110), (30, 70, 120), 1.0),
    (252, (70, 55, 20), (25, 45, 120), .95), (270, (60, 40, 15), (30, 70, 90), 1.05),
    (290, (8, 8, 20), (20, 10, 30), .4), (306, (25, 15, 45), (40, 20, 50), .55), (311.6, (10, 8, 20), (20, 8, 25), .4),
    (312.2, (180, 115, 25), (110, 30, 120), 1.45), (318, (70, 40, 100), (30, 60, 120), 1.0),
    (328, (60, 30, 110), (110, 70, 30), 1.0), (344, (90, 60, 20), (40, 25, 70), .9),
    (364, (40, 30, 15), (20, 12, 35), .55), (376, (10, 8, 5), (10, 5, 15), .3)]

def bg_at(t):
    a = keys(t, [(k[0], k[1]) for k in BGK]); b = keys(t, [(k[0], k[2]) for k in BGK])
    I = keys(t, [(k[0], k[3]) for k in BGK])
    I *= 1 + 0.18 * beat_pulse(t, 0.2)
    s = 1.0 + 0.04 * math.sin(t * 0.07)
    tx = -16 - 14 * math.sin(t * 0.045); ty = -9 - 8 * math.cos(t * 0.038)
    M = np.float32([[s, 0, tx], [0, s, ty]])
    n1 = cv2.warpAffine(NB1, M, (480, 270), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    M2 = np.float32([[s, 0, -16 + 14 * math.sin(t * 0.05 + 1)], [0, s, -9 + 8 * math.sin(t * 0.03)]])
    n2 = cv2.warpAffine(NB2, M2, (480, 270), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    n3 = cv2.warpAffine(NB3, M, (480, 270), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    d = (0.6 + 0.8 * n3)[..., None]
    img = ((n1 ** 3)[..., None] * np.array(a, np.float32) + (n2 ** 3.2)[..., None] * np.array(b, np.float32)) * d
    img *= I * 0.55 / 255.0
    return cv2.resize(img, (W, H), interpolation=cv2.INTER_LINEAR)

_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2)
VIGNETTE = np.clip(1 - 0.42 * _r ** 2.4, 0.25, 1)[..., None].astype(np.float32)
del _yy, _xx, _r

# ============================================================== brand HUD（见仓库根目录 brand/）
sys.path.insert(0, os.path.join(HERE, '..', '..', 'brand'))
from brand import Hud, load_logo as brand_logo
HUD = Hud()
END_LOGO = brand_logo(220)

def draw_hud_post(img, t, a):
    if a <= 0.003: return img
    h = HUD.y0 + HUD.h + HUD.P + 2
    reg = img[:h].astype(np.float32) / 255
    HUD.draw(reg, t, a)
    img[:h] = (np.clip(reg, 0, 1) * 255 + 0.5).astype(np.uint8)
    return img

def draw_chrome(f, t):
    for (a, num, zh, en), (b, *_r) in zip(CHAPTERS, CHAPTERS[1:]):
        if a <= t < b:
            al = env(t, a, b, 0.6, 0.4) * 0.9 * env(t, 0.8, 363.6, 0.8, 0.5)
            fn = 'orb' if num.isdigit() else 'serif_black'
            f.text(num, 70, 62, 30, fn, GOLD, al, 'l', mode='O')
            x = 70 + text_width(num, fn, 30) + 16
            f.line((x, 50), (x, 76), GOLD, al * 0.6, 1)
            f.text(zh, x + 16, 56, 24, 'sans_med', WHITE, al * 0.92, 'l', mode='O')
            f.text(en, x + 16, 84, 14, 'corm', GREY, al * 0.8, 'l', track=0.35, mode='O')
    pa = 0.5 * env(t, 1.0, 363.4, 1.0, 0.6)
    if pa > 0:
        x0, x1, y = 120, 1800, 1042
        f.L[y:y + 1, x0:x1] += np.float32(0.10 * pa)
        xc = x0 + (x1 - x0) * t / 364.0
        f.L[y:y + 1, x0:int(xc)] += np.array(GOLD, np.float32) * 0.35 * pa
        for (a, num, zh, en) in CHAPTERS[1:-1]:
            xx = int(x0 + (x1 - x0) * a / 364.0)
            lit = t >= a
            f.L[y - 5:y + 6, xx:xx + 1] += np.array(GOLD if lit else GREY, np.float32) * 0.5 * pa
            lab = zh if len(zh) <= 5 else zh[:2]
            f.text(lab, xx + 6, y - 14, 14, 'sans_light', GOLD if lit else GREY, pa * (0.9 if lit else 0.5), 'l', mode='L')
        f.glow((xc, y), 4, GOLD2, 0.9 * pa, 'E')
        f.glow((xc, y), 14, GOLD, 0.5 * pa, 'B')

# ============================================================== reusable FX
def shockwaves(f, t):
    for ti, k, col in IMP:
        dt = t - ti
        if 0 <= dt < 1.3:
            for j, (dd, sc) in enumerate(((0, 1.0), (0.12, 0.6), (0.24, 0.35))):
                d2 = dt - dd
                if d2 < 0: continue
                r = 40 + 1250 * eo(d2 / 1.1)
                al = (1 - cl(d2 / 1.1)) ** 1.6 * k * sc
                f.circle((W / 2, H / 2), r, col if j else lerpc(col, WHITE, .5), al, 3 if j == 0 else 2)
            f.flash += k * 0.4 * math.exp(-dt / 0.16)
            f.ca += k * 9 * math.exp(-dt / 0.22)

_BR = np.random.default_rng(77)
BURST = {s: (_BR.uniform(0, 2 * math.pi, 900), _BR.uniform(0.15, 1, 900) ** 0.6, _BR.uniform(0.4, 1.2, 900),
             _BR.integers(0, 6, 900)) for s in range(8)}

def burst(f, t, t0, cx, cy, cols, seed=0, n=700, speed=1500, life=1.4, drag=2.4, a=1.0, size=1):
    dt = t - t0
    if dt < 0 or dt > life * 2.4: return
    th, v, lf, ci = BURST[seed]
    th, v, lf, ci = th[:n], v[:n], lf[:n], ci[:n]
    cc = np.array(cols, np.float32)[ci % len(cols)]
    for k in range(4):
        d = max(dt - k * 0.018, 0)
        r = speed * v * (1 - math.exp(-drag * d)) / drag
        al = np.exp(-d / (life * lf)) * a * (1 - k * 0.22)
        xs = cx + r * np.cos(th); ys = cy + r * np.sin(th) * 0.8
        if size > 1: f.dots(xs, ys, cc, al, 1, 'E')
        else: f.splat(xs, ys, cc, al * 1.4, 'E')

_IR = np.random.default_rng(91)
IMPL = (_IR.uniform(0, 2 * math.pi, 1400), _IR.uniform(0.35, 1.25, 1400), _IR.uniform(0, 0.45, 1400), _IR.integers(0, 6, 1400))

def implode(f, t, t0, t1, cx, cy, cols, a=1.0, R0=950, turns=2.2):
    if t < t0 or t > t1: return
    p = (t - t0) / (t1 - t0)
    th, rr, dl, ci = IMPL
    cc = np.array(cols, np.float32)[ci % len(cols)]
    for k in range(4):
        pk = np.clip((p - k * 0.008 - dl) / (1 - dl), 0, 1)
        r = R0 * rr * (1 - (pk ** 3) ** 0.9)
        ang = th + turns * pk ** 3
        al = np.where(pk > 0, np.minimum(pk * 6, 1), 0) * (1 - pk ** 8) * a * (1 - k * 0.2)
        f.splat(cx + r * np.cos(ang), cy + r * np.sin(ang) * 0.75, cc, al * 1.3, 'E')
    f.glow((cx, cy), 20 + 120 * ei(p), WHITE, (0.25 + 0.9 * ei(p)) * a, 'B')
    f.glow((cx, cy), 6 + 14 * ei(p), WHITE, 0.6 * ei(p) * a, 'E')

_FR = np.random.default_rng(5)
FL_X = _FR.uniform(0, W + 300, 2200); FL_Y = _FR.uniform(-60, H + 60, 2200)
FL_P = _FR.uniform(0, 6.28, 2200); FL_S = _FR.uniform(0.4, 1.4, 2200); FL_C = _FR.integers(0, 6, 2200)

def flow(f, t, a, cols, speed=140, n=2200, rise=0.0):
    if a <= 0.003: return
    cc = np.array(cols, np.float32)[FL_C[:n] % len(cols)]
    for k in range(4):
        tt = t - k * 0.035
        x = (FL_X[:n] + FL_S[:n] * speed * tt) % (W + 300) - 150
        y = FL_Y[:n] + 70 * np.sin(x * 0.0035 + FL_P[:n] + tt * 0.5) + 28 * np.sin(x * 0.011 - tt * 0.9 + FL_P[:n] * 2)
        y = (y - rise * tt * FL_S[:n] * 60) % (H + 120) - 60
        al = a * (0.55 + 0.45 * np.sin(FL_P[:n] + t)) * (1 - k * 0.2)
        f.splat(x, y, cc, al * 2.2, 'E')

def chip(f, s, cx, cy, size, col, a, fnt='sans_med', fill=0.10, anchor='m'):
    if a <= 0.003: return 0
    tw = text_width(s, fnt, size)
    px, py = size * 0.75, size * 0.55
    if anchor == 'l': cx = cx + tw / 2 + px
    f.rrect_fill(cx - tw / 2 - px, cy - size / 2 - py, cx + tw / 2 + px, cy + size / 2 + py, size * 0.6, col, fill * a)
    f.rrect(cx - tw / 2 - px, cy - size / 2 - py, cx + tw / 2 + px, cy + size / 2 + py, size * 0.6, col, a * 0.9, 2)
    f.text(s, cx, cy, size, fnt, lerpc(col, WHITE, 0.55), a, mode='L', glow=0.25)
    return tw + 2 * px

def tokens(f, toks, cx, cy, size, a, gap=0.4, pill=True, appear=None, fnt='serif_black'):
    pads = size * 0.55
    widths = [text_width(s, fnt, size) + (2 * pads if (pill and term) else 0) for s, c, term in toks]
    total = sum(widths) + gap * size * (len(toks) - 1)
    x = cx - total / 2
    centers = []
    for i, ((s, col, term), w) in enumerate(zip(toks, widths)):
        p = 1.0 if appear is None else cl((f.t - appear[i]) / 0.35)
        if p > 0:
            al = a * eo(p)
            sc = 1 + 0.35 * (1 - eback(p, 2.2)) if appear is not None else 1
            sz = max(8, int(round(size * sc)))
            xc = x + w / 2
            if pill and term:
                hw = w / 2 * sc; hh = size * 0.92 * sc
                f.rrect_fill(xc - hw, cy - hh, xc + hw, cy + hh, hh * 0.9, col, 0.13 * al)
                f.rrect(xc - hw, cy - hh, xc + hw, cy + hh, hh * 0.9, col, al, 2)
                f.glow((xc, cy), hw * 0.5, col, 0.18 * al * (1 + bar_pulse(f.t)), 'B')
                f.text(s, xc, cy, sz, fnt, lerpc(col, WHITE, 0.6), al, mode='L', glow=0.35)
            else:
                f.text(s, xc, cy, sz, fnt, col, al, mode='L', glow=0.4)
        centers.append(x + w / 2)
        x += w + gap * size
    return centers

def ripple(f, t, t0, cx, cy, col, a=1.0, n=3, R=420, life=1.2, th=2):
    for j in range(n):
        d = t - t0 - j * 0.15
        if 0 <= d < life:
            f.circle((cx, cy), 20 + R * eo(d / life), col, a * (1 - d / life) ** 1.5, th)

def dashed(f, p0, p1, col, a, th=1, dash=10, gap=8, phase=0.0):
    x0, y0 = p0; x1, y1 = p1
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 1: return
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    s = -((phase * (dash + gap)) % (dash + gap))
    while s < L:
        a0 = max(s, 0); a1 = min(s + dash, L)
        if a1 > a0:
            f.line((x0 + ux * a0, y0 + uy * a0), (x0 + ux * a1, y0 + uy * a1), col, a, th)
        s += dash + gap

def arrow(f, p0, p1, col, a, th=3, head=16):
    f.line(p0, p1, col, a, th)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for s in (-1, 1):
        f.line(p1, (p1[0] - head * math.cos(ang + s * 0.45), p1[1] - head * math.sin(ang + s * 0.45)), col, a, th)

def fmt_money(v, pre='¥'):
    return pre + f'{int(round(v)):,}'

# ============================================================== icons
def icon_phone(f, cx, cy, h, col, a, t, premium=False, rim=0.0):
    if a <= 0.003: return
    w = h * 0.49
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    f.rrect_fill(x0, y0, x1, y1, w * 0.16, col, 0.07 * a)
    pts = f.rrect(x0, y0, x1, y1, w * 0.16, col, a, 3)
    f.rrect(x0 + 8, y0 + 8, x1 - 8, y1 - 8, w * 0.13, col, a * 0.35, 1)
    if premium:
        # camera bump
        f.rrect(x0 + 14, y0 + 14, x0 + w * 0.48, y0 + w * 0.48, 14, col, a * 0.9, 2)
        for (u, v) in ((0.17, 0.17), (0.34, 0.17), (0.25, 0.33)):
            f.circle((x0 + w * u + 6, y0 + w * v + 6), w * 0.065, col, a, 2)
            f.glow((x0 + w * u + 6, y0 + w * v + 6), 3, WHITE, a * 0.7, 'E')
        f.text('PRO', cx, cy + h * 0.22, int(h * 0.07), 'orb', col, a * 0.85, track=0.4, mode='L', glow=0.4)
    else:
        f.circle((cx, y0 + 26), 6, col, a * 0.6, 2)
    if rim > 0:
        n = len(pts)
        k = (t * 18) % n
        for j in range(14):
            q = pts[int(k + j) % n]
            f.glow(q, 6 + j * 0.6, lerpc(col, WHITE, 0.5), a * rim * (1 - j / 14), 'E')
        f.glow((cx, cy), h * 0.5, col, a * rim * 0.22, 'B')

def icon_cart(f, cx, cy, s, col, a):
    if a <= 0.003: return
    pts = [(cx - s * 0.9, cy - s * 0.6), (cx - s * 0.62, cy - s * 0.6), (cx - s * 0.4, cy + s * 0.3),
           (cx + s * 0.6, cy + s * 0.3), (cx + s * 0.8, cy - s * 0.35), (cx - s * 0.52, cy - s * 0.35)]
    f.poly(pts, col, a, 3)
    for k in range(1, 4):
        x = cx - s * 0.45 + k * s * 0.3
        f.line((x, cy - s * 0.33), (x - s * 0.04, cy + s * 0.28), col, a * 0.5, 1)
    f.circle((cx - s * 0.3, cy + s * 0.52), s * 0.1, col, a, 3)
    f.circle((cx + s * 0.5, cy + s * 0.52), s * 0.1, col, a, 3)

def icon_jacket(f, cx, cy, s, col, a, premium=False):
    if a <= 0.003: return
    P = lambda u, v: (cx + u * s, cy + v * s)
    body = [P(-0.25, -0.75), P(-0.6, -0.6), P(-0.95, 0.3), P(-0.75, 0.38), P(-0.55, -0.15), P(-0.55, 0.85),
            P(0.55, 0.85), P(0.55, -0.15), P(0.75, 0.38), P(0.95, 0.3), P(0.6, -0.6), P(0.25, -0.75)]
    f.fillpoly(body, col, 0.07 * a)
    f.poly(body, col, a, 3)
    f.poly([P(-0.25, -0.75), P(-0.18, -0.95), P(0.18, -0.95), P(0.25, -0.75)], col, a, 3)   # hood/collar
    f.line(P(0, -0.75), P(0, 0.85), col, a * 0.7, 2)
    if premium:
        f.poly([P(0.2, -0.45), P(0.35, -0.58), P(0.42, -0.42)], col, a, 2)   # small chest emblem
        f.line(P(-0.55, 0.1), P(-0.15, 0.1), col, a * 0.5, 1)

def icon_castle(f, cx, cy, s, col, a):
    if a <= 0.003: return
    P = lambda u, v: (cx + u * s, cy + v * s)
    pts = [P(-1, 0.6), P(-1, -0.2), P(-0.85, -0.2), P(-0.85, -0.05), P(-0.7, -0.05), P(-0.7, -0.2), P(-0.55, -0.2),
           P(-0.55, 0.0), P(-0.3, 0.0), P(-0.3, -0.55), P(-0.18, -0.55), P(-0.18, -0.42), P(-0.06, -0.42), P(-0.06, -0.55),
           P(0.06, -0.55), P(0.06, -0.42), P(0.18, -0.42), P(0.18, -0.55), P(0.3, -0.55), P(0.3, 0.0), P(0.55, 0.0),
           P(0.55, -0.2), P(0.7, -0.2), P(0.7, -0.05), P(0.85, -0.05), P(0.85, -0.2), P(1, -0.2), P(1, 0.6)]
    f.fillpoly(pts + [P(1, 0.6)], col, 0.06 * a)
    f.poly(pts, col, a, 3)
    f.poly([P(-0.14, 0.6), P(-0.14, 0.25), P(0, 0.12), P(0.14, 0.25), P(0.14, 0.6)], col, a, 2)
    f.line(P(0, -0.55), P(0, -0.9), col, a, 2)
    f.poly([P(0, -0.9), P(0.25, -0.82), P(0, -0.74)], col, a, 2)

def icon_person(f, cx, cy, s, col, a, fill=0.06, th=3):
    if a <= 0.003: return
    f.circle((cx, cy - s * 0.55), s * 0.28, col, a, th)
    f.fillpoly([(cx + s * 0.28 * math.cos(k), cy - s * 0.55 + s * 0.28 * math.sin(k)) for k in np.linspace(0, 6.283, 24)], col, fill * a)
    pts = [(cx + s * 0.62 * math.cos(k), cy + s * 0.62 + s * 0.62 * math.sin(k)) for k in np.linspace(math.pi, 2 * math.pi, 24)]
    f.poly(pts + [pts[0]], col, a, th)
    f.fillpoly(pts, col, fill * a)

def icon_gate(f, cx, cy, w, h, col, a):
    if a <= 0.003: return
    pts = [(cx - w / 2, cy + h / 2), (cx - w / 2, cy - h / 2 + w / 2)]
    for k in np.linspace(math.pi, 2 * math.pi, 30):
        pts.append((cx + w / 2 * math.cos(k), cy - h / 2 + w / 2 + w / 2 * math.sin(k)))
    pts.append((cx + w / 2, cy + h / 2))
    f.poly(pts, col, a, 4)
    f.poly([(x + (-18 if x < cx else 18 if x > cx else 0), y - (14 if y < cy else 0)) for x, y in pts], col, a * 0.4, 2)
    f.line((cx - w / 2 - 60, cy + h / 2), (cx + w / 2 + 60, cy + h / 2), col, a * 0.6, 2)


# ============================================================== SCENES
# ---------------------------------------------------------------- 序章 0–16
def compare(f, t, t0, t1, cap, draw_l, draw_r, lab_l, lab_r, val_l, val_r, bottom=None):
    a = env(t, t0, t1, 0.3, 0.35)
    if a <= 0: return
    f.text(cap, W / 2, 220, 50, 'serif_med', WHITE, a, t0=t0 + 0.05, stag=0.04, glow=0.15)
    p = eo((t - t0 - 0.2) / 0.5)
    draw_l(W / 2 - 330 - 40 * (1 - p), 520, a * p)
    draw_r(W / 2 + 330 + 40 * (1 - p), 520, a * p)
    f.text(lab_l, W / 2 - 330, 760, 30, 'sans_light', GREY, a * p, mode='L')
    f.text(lab_r, W / 2 + 330, 760, 30, 'sans_light', GOLD2, a * p, mode='L')
    cp = eo((t - t0 - 0.6) / 1.4)
    if isinstance(val_l, str):
        sl, sr = val_l, val_r
    else:
        sl, sr = fmt_money(val_l * cp), fmt_money(val_r * cp)
    cjk = lambda z: any('\u4e00' <= ch <= '\u9fff' for ch in z)
    fl = 'sans_black' if cjk(sl) else 'bebas'
    f.text(sl, W / 2 - 330, 840, 72 if fl == 'bebas' else 50, fl, SILVER, a * p, mode='L', glow=0.2)
    if '/' not in sr:
        f.text(sr, W / 2 + 330, 840, 92, 'bebas', GOLD, a * p, mode='L', glow=0.4 + 0.3 * beat_pulse(t))
    else:
        num, unit = sr.split('/')
        wn = text_width(num, 'bebas', 92); wu = text_width('/' + unit, 'sans_black', 50)
        x0 = W / 2 + 330 - (wn + wu) / 2
        f.text(num, x0, 840, 92, 'bebas', GOLD, a * p, 'l', mode='L', glow=0.4 + 0.3 * beat_pulse(t))
        f.text('/' + unit, x0 + wn + 4, 846, 50, 'sans_black', GOLD, a * p, 'l', mode='L', glow=0.3)
    f.text('VS', W / 2, 520, 40, 'orb', GREY, a * 0.6 * p, mode='L')
    if bottom:
        b = env(t, t0 + 1.9, t1, 0.3, 0.35)
        f.text(bottom, W / 2, 950, 36, 'sans_med', GOLD2, b, t0=t0 + 1.9, stag=0.03)

def sc_prologue(f, t):
    if t > 16.3: return
    compare(f, t, 0.6, 4.4, '同样能打电话、拍照、上网的手机',
            lambda x, y, a: icon_phone(f, x, y, 340, SILVER, a, t),
            lambda x, y, a: icon_phone(f, x, y, 340, GOLD2, a, t, True, rim=0.8),
            '普通款', 'PRO 款', 1999, 7999, '价格差了 4 倍，照样有人排队')
    compare(f, t, 4.4, 8.2, '同样是去超市买菜',
            lambda x, y, a: icon_cart(f, x, y, 150, SILVER, a),
            lambda x, y, a: (icon_cart(f, x, y, 150, GOLD2, a), f.glow((x, y), 140, GOLD, a * 0.25, 'B')),
            '普通商超', '会员店', '免费进门', '¥260/年', '先交年费，才有资格进门')
    compare(f, t, 8.2, 12.0, '同样是一件挡风防雨的外套',
            lambda x, y, a: icon_jacket(f, x, y, 160, SILVER, a),
            lambda x, y, a: (icon_jacket(f, x, y, 160, GOLD2, a, True), f.glow((x, y), 150, GOLD, a * 0.25, 'B')),
            '普通冲锋衣', '高端户外品牌', 599, 5800, '有人宁愿多花近十倍')
    a = env(t, 12.0, 15.6, 0.4, 0.3)
    f.text('多付的那部分钱，', W / 2, 430, 62, 'serif_med', lerpc(GREY, WHITE, 0.6), a, t0=12.05, stag=0.07, dur=0.5)
    f.text('到底买到了什么？', W / 2, 580, 96, 'serif_black', WHITE, a, t0=12.9, stag=0.1, dur=0.6, glow=0.35,
           grad=[WHITE, GOLD2, GOLD])
    implode(f, t, 13.4, 16.0, W / 2, H / 2, [GOLD, GOLD2, CYAN, VIOLET, WHITE, MAGENTA])

# ---------------------------------------------------------------- 标题 16–24
_MR = np.random.default_rng(8)
MOAT_TH = _MR.uniform(0, 2 * math.pi, 1500); MOAT_R = _MR.normal(1, 0.035, 1500); MOAT_S = _MR.uniform(0.5, 1.2, 1500)
MOAT_C = np.array([[CYAN, GOLD2, BLUE, WHITE, GOLD][i % 5] for i in range(1500)], np.float32)

def moat(f, t, cx, cy, rx, ry, a, n=1500):
    if a <= 0.003: return
    for k in range(4):
        th = MOAT_TH[:n] + (t - k * 0.03) * 0.35 * MOAT_S[:n]
        x = cx + rx * MOAT_R[:n] * np.cos(th); y = cy + ry * MOAT_R[:n] * np.sin(th)
        al = a * (0.5 + 0.5 * np.sin(th * 3 + t)) * (1 - k * 0.22)
        f.splat(x, y, MOAT_C[:n], al * 1.6, 'E')

def sc_title(f, t):
    if not (15.9 < t < 24.2): return
    burst(f, t, 16.0, W / 2, H / 2, [GOLD, GOLD2, CYAN, VIOLET, WHITE, MAGENTA], 0, 900, 1700, 1.3, 2.2, 1.0, 2)
    a = env(t, 16.0, 23.8, 0.05, 0.5)
    moat(f, t, W / 2, 545, 820 * eo((t - 16) / 1.2), 240 * eo((t - 16) / 1.2), a * 0.9)
    icon_castle(f, W / 2, 300, 120, GOLD2, a * eo((t - 16.3) / 0.6))
    f.glow((W / 2, 300), 120, GOLD, a * 0.2 * (1 + bar_pulse(t)), 'B')
    f.text('THE  STATUS  SIGNALING  MOAT', W / 2, 425, 26, 'corm', GOLD2, a * 0.9, track=0.45, t0=16.5, stag=0.02, mode='L')
    f.dim(260, 455, 1660, 625, 0.55 * a, 60)
    f.text('社会地位象征型护城河', W / 2, 540, 124, 'serif_black', WHITE, a, t0=16.0, stag=0.05, dur=0.35, rise=40,
           grad=[GOLD2, C(255, 250, 230), GOLD2, GOLD], mode='L', glow=0.45)
    w = 560 * eo((t - 16.9) / 0.8)
    if w > 200:
        f.line((W / 2 - w, 668), (W / 2 - 200, 668), GOLD, a * 0.8, 1)
        f.line((W / 2 + 200, 668), (W / 2 + w, 668), GOLD, a * 0.8, 1)
    f.text('当品牌，成为一种社会信号', W / 2, 668, 38, 'sans_light', GOLD2, a, t0=17.0, stag=0.04)
    f.text('一次第一性原理的拆解', W / 2, 760, 28, 'sans_light', GREY, a * 0.9, t0=18.0, stag=0.03, track=0.2)

# ---------------------------------------------------------------- 01a 三个问题 24–38
RINGS = [(110, CYAN, '功能', '① 我需要什么？', '功能价值 · FUNCTION', 26.0),
         (205, VIOLET, '身份', '② 我是谁？', '身份认同 · IDENTITY', 28.5),
         (300, GOLD, '地位', '③ 我希望别人怎样看我？', '社会地位 · STATUS', 31.0)]

def sc_questions(f, t):
    if not (24 < t < 38.3): return
    a = env(t, 24.1, 37.9, 0.4, 0.4)
    f.text('人买东西，其实在回答三个问题', W / 2, 150, 52, 'serif_black', WHITE, a, t0=24.2, stag=0.04, glow=0.2)
    cx, cy = 600, 590
    late = eo((t - 33.5) / 0.8)
    for i, (r, col, lab, q, en, t0) in enumerate(RINGS):
        p = eo((t - t0) / 0.7)
        if p <= 0: continue
        ra = a * p * (1 - 0.6 * late if i == 0 else 1 + 0.3 * late * bar_pulse(t))
        R = r * (0.6 + 0.4 * eback(cl((t - t0) / 0.7), 1.5))
        f.circle((cx, cy), R, col, ra * 0.9, 3)
        f.arc((cx, cy), R + 10, t * (0.5 + i * 0.2), t * (0.5 + i * 0.2) + 1.2, col, ra * 0.7, 2)
        f.arc((cx, cy), R + 10, t * (0.5 + i * 0.2) + 3.1, t * (0.5 + i * 0.2) + 3.7, col, ra * 0.5, 2)
        ang = t * (0.9 - 0.2 * i) + i * 2
        for k in range(5):
            qq = (cx + R * math.cos(ang + k * 1.2566), cy + R * math.sin(ang + k * 1.2566))
            f.glow(qq, 3, WHITE, ra * 0.9, 'E'); f.glow(qq, 10, col, ra * 0.5, 'B')
        f.glow((cx, cy), R * 0.9, col, ra * 0.08 * (1 + beat_pulse(t)), 'B')
        ly = cy if i == 0 else cy - (r - 48)
        f.text(lab, cx, ly, 34 if i == 0 else 28, 'serif_black', lerpc(col, WHITE, .5), ra, mode='L', glow=0.3)
        y = 360 + i * 165
        f.text(q, 1000, y, 50, 'serif_black', WHITE, a * (1 - 0.45 * late if i == 0 else 1), 'l', t0=t0, stag=0.04,
               glow=0.2)
        f.text(en, 1004, y + 54, 26, 'sans_light', col, a * (1 - 0.45 * late if i == 0 else 1), 'l', t0=t0 + 0.3,
               stag=0.02, track=0.1)
    b = env(t, 33.5, 37.9, 0.4, 0.4)
    f.text('后两个问题，才是品牌溢价的真正来源', W / 2, 900, 42, 'serif_black', GOLD2, b, t0=33.5, stag=0.04,
           mode='E', glow=0.5)
    f.text('（身份认同不全是虚荣：归属感、审美、信任、自我奖励，同样是购买动机）', W / 2, 965, 24, 'sans_light', GREY, b,
           t0=35.0, stag=0.012)

# ---------------------------------------------------------------- 01b 群居物种 38–50
_NR = np.random.default_rng(31)
PEOPLE = []
while len(PEOPLE) < 70:
    x, y = _NR.uniform(-1, 1, 2)
    if x * x + y * y < 1 and x * x + y * y > 0.03: PEOPLE.append((x, y))
PEOPLE = np.array(PEOPLE)
P_PH = _NR.uniform(0, 1, 70); P_D = np.hypot(PEOPLE[:, 0], PEOPLE[:, 1])
P_NB = [np.argsort(np.hypot(*(PEOPLE - PEOPLE[i]).T))[1:3] for i in range(70)]

def sc_social(f, t):
    if not (38 < t < 50.3): return
    a = env(t, 38.1, 49.9, 0.4, 0.4)
    f.text('为什么人这么在乎「别人怎么看」？', W / 2, 160, 52, 'serif_black', WHITE, a, t0=38.2, stag=0.04, glow=0.2)
    cx, cy, rx, ry = W / 2, 520, 720, 250
    P = np.stack([cx + PEOPLE[:, 0] * rx, cy + PEOPLE[:, 1] * ry], 1)
    P[:, 1] += np.sin(t * 0.9 + PEOPLE[:, 0] * 5) * 5
    hub = (cx, cy)
    hp = eo((t - 40.0) / 1.0)
    for i in range(70):
        ap = a * eo((t - 38.5 - 0.012 * i) / 0.5)
        for j in P_NB[i]:
            f.line(P[i], P[j], CYAN, ap * 0.25 * (1 - 0.5 * hp), 1)
        tl = 40.5 + P_D[i] * 1.6
        q = cl((t - tl) / 0.6)
        if q > 0:
            end = P[i] + (np.array(hub) - P[i]) * eo(q)
            f.line(P[i], tuple(end), lerpc(CYAN, GOLD, 0.6), ap * 0.35, 1)
            if q >= 1:
                ph = (t * 0.7 + P_PH[i]) % 1.0
                m = P[i] + (np.array(hub) - P[i]) * ph
                f.glow(tuple(m), 2.5, GOLD2, ap * 0.9, 'E')
        icon_person(f, P[i][0], P[i][1], 14, lerpc(CYAN, WHITE, 0.3), ap * 0.85, th=1)
    s = 30 + 28 * hp + 4 * beat_pulse(t)
    icon_person(f, hub[0], hub[1] - 6, s, GOLD2, a * (0.4 + 0.6 * hp), fill=0.15, th=3)
    f.glow(hub, 60 + 50 * hp, GOLD, a * 0.35 * hp * (1 + 0.6 * bar_pulse(t)), 'B')
    if 40.0 < t < 41.5:
        ripple(f, t, 40.0, hub[0], hub[1], GOLD2, a, 3, 500, 1.2)
    b = env(t, 43.5, 49.9, 0.4, 0.4)
    f.dim(260, 820, 1660, 1000, 0.7 * b, 30)
    f.text('在群体里被高看一眼 = 更多合作、资源与机会', W / 2, 870, 44, 'serif_black', WHITE, b, t0=43.6, stag=0.035,
           glow=0.2)
    c = env(t, 46.0, 49.9, 0.4, 0.4)
    f.text('在乎地位，是写进基因里的生存策略', W / 2, 945, 34, 'sans_med', GOLD2, c, t0=46.0, stag=0.04, mode='E', glow=0.4)

# ---------------------------------------------------------------- 01c 看不见的地位 → 昂贵信号 50–64
HID = ['能力？', '收入？', '品位？', '人脉？', '可靠？']

def sc_invisible(f, t):
    if not (50 < t < 56.4): return
    a = env(t, 50.1, 56.1, 0.35, 0.3)
    f.text('但是，地位是看不见的', W / 2, 190, 64, 'serif_black', WHITE, a, t0=50.15, stag=0.06, glow=0.25)
    for i in range(5):
        x = W / 2 + (i - 2) * 300
        p = eo((t - 50.6 - i * 0.15) / 0.5)
        icon_person(f, x, 520, 90, SILVER, a * p * 0.8, fill=0.04)
        fl = 0.55 + 0.45 * math.sin(t * 7 + i * 1.7) ** 2
        f.text('?', x, 440, 60, 'bebas', VIOLET, a * p * fl, mode='E', glow=0.7)
        f.text(HID[i], x, 660, 30, 'sans_light', lerpc(VIOLET, WHITE, .4), a * p * 0.8, mode='L')
    b = env(t, 52.4, 56.1, 0.35, 0.3)
    f.text('能力、收入、品位……都藏在一个人身上，别人无从验证', W / 2, 790, 38, 'sans_med', lerpc(GREY, WHITE, .5), b,
           t0=52.4, stag=0.025)
    c = env(t, 54.2, 56.1, 0.3, 0.3)
    f.text('于是，人需要「信号」', W / 2, 890, 56, 'serif_black', GOLD2, c, t0=54.2, stag=0.06, mode='E', glow=0.6)

NFEA = 41
def peacock(f, t, cx, cy, L, a, open_):
    if a <= 0.003: return
    spread = math.radians(170) * eo(open_)
    for k in range(NFEA):
        u = (k / (NFEA - 1)) - 0.5
        ang = -math.pi / 2 + u * spread + 0.02 * math.sin(t * 1.5 + k)
        ll = L * (0.82 + 0.18 * math.cos(u * math.pi)) * (0.4 + 0.6 * eo(open_))
        tip = (cx + ll * math.cos(ang), cy + ll * math.sin(ang))
        col = lerpc(TEAL, BLUE, abs(u) * 2)
        f.line((cx, cy), tip, col, a * 0.45, 1)
        for j in range(1, 6):   # barbs
            q = (cx + ll * j / 6 * math.cos(ang), cy + ll * j / 6 * math.sin(ang))
            f.line(q, (q[0] + 16 * math.cos(ang + 0.6), q[1] + 16 * math.sin(ang + 0.6)), col, a * 0.18, 1)
            f.line(q, (q[0] + 16 * math.cos(ang - 0.6), q[1] + 16 * math.sin(ang - 0.6)), col, a * 0.18, 1)
        sh = 1 + 0.25 * beat_pulse(t - k * 0.01)
        for rr_ in ((0.55, 0.6), (0.78, 0.8)):   # inner rows of eyes on alternating feathers
            if (k + (1 if rr_[0] < 0.6 else 0)) % 2 == 0:
                q = (cx + ll * rr_[0] * math.cos(ang), cy + ll * rr_[0] * math.sin(ang))
                f.circle(q, 11 * rr_[1] * sh, TEAL, a * 0.7, 2)
                f.circle(q, 6 * rr_[1] * sh, GOLD, a * 0.7, 1)
                f.glow(q, 3, lerpc(BLUE, WHITE, .3), a * 0.8, 'E')
        f.circle(tip, 17 * sh, TEAL, a * 0.9, 2)
        f.circle(tip, 10 * sh, GOLD, a * 0.9, 2)
        f.glow(tip, 5 * sh, lerpc(BLUE, WHITE, .3), a, 'E')
        f.glow(tip, 22, TEAL, a * 0.35, 'B')
    f.glow((cx, cy), 40, BLUE, a * 0.5, 'B')
    f.circle((cx, cy - 10), 22, lerpc(BLUE, WHITE, .3), a, 3)
    f.circle((cx + 4, cy - 52), 12, lerpc(BLUE, WHITE, .3), a, 2)

def sc_peacock(f, t):
    if not (56 < t < 64.3): return
    a = env(t, 56.1, 63.9, 0.4, 0.4)
    f.text('信号要可信，就必须有成本', W / 2, 150, 58, 'serif_black', WHITE, a, t0=56.15, stag=0.05, glow=0.25)
    peacock(f, t, W / 2, 830, 470, a, (t - 56.4) / 1.6)
    b = env(t, 58.6, 63.9, 0.4, 0.4)
    f.text('孔雀的尾巴：沉重、显眼、招惹天敌——正因为「装不起」，才可信', W / 2, 235, 34, 'sans_med', lerpc(TEAL, WHITE, .5), b,
           t0=58.6, stag=0.02)
    c = env(t, 60.8, 63.9, 0.35, 0.4)
    f.dim(420, 880, 1500, 1005, 0.75 * c, 30)
    f.text('品牌溢价，就是现代人的「孔雀尾巴」', W / 2, 925, 48, 'serif_black', GOLD2, c, t0=60.8, stag=0.05, mode='E', glow=0.6)
    f.text('昂贵信号理论 · Zahavi 1975 ／ 信号理论 · Spence 1973', W / 2, 980, 22, 'sans_light', GREY, c, t0=61.6, stag=0.01)

# ---------------------------------------------------------------- 01d 价格拆解 64–78
SEGS = [(0.36, SILVER, '成本', '原料 · 制造 · 渠道', 64.6), (0.30, CYAN, '功能价值', '好用 · 耐用 · 省心', 66.4),
        (0.34, GOLD, '社会信号价值', '别人怎么看你', 68.2)]

def stackbar(f, t, x, w, yb, h, a, segs, copy=False, t_copy=0.0):
    y = yb
    tops = []
    for i, (fr, col, lab, sub, t0) in enumerate(segs):
        tt0 = t_copy + i * 0.6 if copy else t0
        p = eo((t - tt0) / 0.8)
        hh = h * fr * p
        if copy and i == 2:
            # competitor can't copy the signal: dashed outline only
            q = eo((t - tt0) / 0.6)
            if q > 0:
                y1 = y - h * fr
                for (p0, p1) in (((x, y1), (x + w, y1)), ((x, y1), (x, y)), ((x + w, y1), (x + w, y))):
                    dashed(f, p0, p1, GOLD, a * q * 0.7, 2, 12, 9, t * 0.8)
                f.text('?', x + w / 2, y - h * fr / 2, 90, 'bebas', GOLD, a * q * (0.6 + 0.4 * math.sin(t * 5) ** 2),
                       mode='E', glow=0.6)
            tops.append(y - h * fr)
            break
        if hh > 1:
            f.rrect_fill(x, y - hh, x + w, y, 6, col, a * (0.38 if i == 2 else 0.22), 'L')
            f.rrect(x, y - hh, x + w, y, 6, col, a * 0.95, 2)
            if i == 2 and not copy:
                f.glow((x + w / 2, y - hh / 2), 120, GOLD, a * 0.25 * (1 + bar_pulse(t)), 'B')
                sh = (t * 0.6) % 1.0
                f.line((x + 4, y - hh * sh), (x + w - 4, y - hh * sh), GOLD2, a * 0.5, 2)
        tops.append(y - hh)
        y -= hh
    return tops

def sc_price(f, t):
    if not (64 < t < 78.3): return
    a = env(t, 64.1, 77.9, 0.4, 0.4)
    fa = a * (1 - eio((t - 73.6) / 0.5))
    toks = [('价格', WHITE, False), ('=', GREY, False), ('成本', SILVER, True), ('+', GREY, False),
            ('功能价值', CYAN, True), ('+', GREY, False), ('信号价值', GOLD, True)]
    tokens(f, toks, W / 2, 160, 46, fa, gap=0.35, appear=[64.2, 64.4, 64.6, 66.2, 66.4, 68.0, 68.2])
    x, w, yb, h = 560, 200, 900, 540
    stackbar(f, t, x, w, yb, h, a, SEGS)
    y = yb
    for i, (fr, col, lab, sub, t0) in enumerate(SEGS):
        p = eo((t - t0 - 0.3) / 0.6)
        ym = y - h * fr / 2
        f.line((x + w + 10, ym), (x + w + 60 * p, ym), col, a * p, 2)
        f.text(lab, x + w + 75, ym - 18, 40, 'serif_black', lerpc(col, WHITE, .4), a * p, 'l', mode='L', glow=0.3)
        f.text(sub, x + w + 77, ym + 26, 26, 'sans_light', col, a * p, 'l')
        y -= h * fr
    # competitor
    c = env(t, 70.6, 77.9, 0.4, 0.4)
    if c > 0:
        cx = 1360
        f.text('竞争对手', cx + w / 2, 950, 30, 'sans_med', GREY, c, mode='L')
        stackbar(f, t, cx, w, yb, h, c, SEGS, copy=True, t_copy=70.8)
        b = env(t, 71.6, 77.9, 0.3, 0.4)
        f.text('能复制成本和功能', cx + w / 2, 270, 32, 'sans_med', CYAN, b, t0=71.6, stag=0.03)
        f.text('复制不了「别人怎么看你」', cx + w / 2, 318, 32, 'sans_med', GOLD2, b * eo((t - 72.6) / 0.4), t0=72.6,
               stag=0.03)
    d = env(t, 74.1, 77.9, 0.4, 0.4)
    f.text('护城河，就藏在这一截里', W / 2, 160, 60, 'serif_black', GOLD2, d, t0=74.1, stag=0.06, mode='E', glow=0.6)
    if d > 0:
        y1, y0 = yb - h, yb - h * 0.66
        f.rrect(x - 14, y1 - 14, x + w + 14, y0 + 6, 12, GOLD2, d * (0.6 + 0.4 * bar_pulse(t)), 3)
        f.glow((x + w / 2, (y0 + y1) / 2), 160, GOLD, d * 0.25, 'B')


# ---------------------------------------------------------------- 02a 三股力量 78–94
_OR = np.random.default_rng(12)
ORB_TH = _OR.uniform(0, 2 * math.pi, 400); ORB_R = _OR.uniform(0.6, 1.5, 400); ORB_S = _OR.uniform(0.6, 1.6, 400)
FORCES = [((430, 400), GOLD, '社会地位信号', 'STATUS SIGNALING', '让别人觉得我更有钱、更有品位', 79.5),
          ((1490, 400), CYAN, '从众与社会认同', 'BANDWAGON EFFECT', '我向往的人都在用，我也想用', 82.5),
          ((960, 640), MAGENTA, '价格与准入门槛', 'PRESTIGE PREMIUM', '有分量，但普通中产够得着', 85.5)]

def orb(f, t, c, col, a, R=80, n=400):
    if a <= 0.003: return
    th = ORB_TH[:n] + t * ORB_S[:n]
    x = c[0] + R * ORB_R[:n] * np.cos(th); y = c[1] + R * ORB_R[:n] * np.sin(th) * 0.55
    f.splat(x, y, col, a * 1.6 * (0.5 + 0.5 * np.sin(th * 2)), 'E')
    f.glow(c, R * 0.55 * (1 + 0.15 * beat_pulse(t)), col, a * 0.9, 'B')
    f.glow(c, R * 0.18, WHITE, a * 0.8, 'E')
    f.circle(c, R * 0.42, lerpc(col, WHITE, .3), a * 0.8, 2)

def sc_forces(f, t):
    if not (78 < t < 94.2): return
    a = env(t, 78.1, 94.0, 0.4, 0.05)
    hdr = a * (1 - eio((t - 89) / 0.6))
    f.text('大众地位象征型品牌，是三股力量的叠加', W / 2, 140, 50, 'serif_black', WHITE, hdr, t0=78.3, stag=0.04, glow=0.2)
    merge = eio((t - 89.0) / 1.6)
    for i, (c, col, zh, en, desc, t0) in enumerate(FORCES):
        p = eo((t - t0) / 0.6)
        if p <= 0: continue
        cc = (lerp(c[0], W / 2, merge), lerp(c[1], 520, merge))
        orb(f, t, cc, col, a * p, 90 * (1 - 0.4 * merge))
        if i < 2 and p >= 1 and merge > 0:
            pass
        ta = a * p * (1 - eio((t - 88.8) / 0.5))
        ty = c[1] + 150 if i < 2 else c[1] + 140
        f.text(zh, c[0], ty, 46, 'serif_black', lerpc(col, WHITE, .4), ta, t0=t0, stag=0.05, glow=0.3)
        f.text(en, c[0], ty + 48, 22, 'corm', col, ta, track=0.35, t0=t0 + 0.2, stag=0.015)
        f.text(desc, c[0], ty + 92, 30, 'sans_light', WHITE, ta * 0.9, t0=t0 + 0.4, stag=0.025)
    if 88.6 < t < 90.6:   # streams into the core
        for i, (c, col, *_r) in enumerate(FORCES):
            for k in range(12):
                u = ((t * 1.4 + k / 12) % 1.0)
                q = (lerp(c[0], W / 2, u), lerp(c[1], 520, u) - math.sin(u * math.pi) * 60)
                f.glow(q, 4, col, a * 0.9 * env(t, 88.6, 90.6, 0.3, 0.3), 'E')
    m = env(t, 90.4, 94.0, 0.3, 0.05)
    if m > 0:
        orb(f, t, (W / 2, 470), GOLD2, m * 0.6, 160, 400)
        moat(f, t, W / 2, 470, 520, 160, m * 0.7, 900)
        f.text('大众地位象征型护城河', W / 2, 760, 70, 'serif_black', WHITE, m, t0=90.5, stag=0.06, mode='E', glow=0.6,
               grad=[GOLD, GOLD2, CYAN, MAGENTA])
        f.text('MASSTIGE  =  MASS  +  PRESTIGE', W / 2, 850, 30, 'corm', GOLD2, m, track=0.3, t0=91.2, stag=0.02)
    implode(f, t, 91.6, 94.0, W / 2, 520, [GOLD, CYAN, MAGENTA, WHITE, GOLD2, VIOLET], 0.8)

# ---------------------------------------------------------------- 02b 乘法公式 94–110
FACT = [('社会可见性', CYAN, 0.9), ('身份识别度', VIOLET, 0.8), ('心理溢价', GOLD, 0.7), ('广泛可及性', MAGENTA, 0.8)]

def sc_formula(f, t):
    if not (94 < t < 110.3): return
    a = env(t, 94.0, 109.9, 0.1, 0.4)
    toks = [('护城河', GOLD2, False), ('=', GREY, False)]
    app = [94.1, 94.3]
    for i, (s, col, v) in enumerate(FACT):
        if i: toks.append(('×', GREY, False)); app.append(94.5 + i * 1.0 - 0.25)
        toks.append((s, col, True)); app.append(94.5 + i * 1.0)
    cen = tokens(f, toks, W / 2, 230, 44, a, gap=0.32, appear=app)
    for i in range(4):
        ti = app[2 + 2 * i]
        if 0 < t - ti < 1.0:
            burst(f, t, ti, cen[2 + 2 * i], 230, [FACT[i][1], WHITE], 6, 160, 420, 0.5, 3.5, 0.9)
    # meters
    m = env(t, 98.4, 109.9, 0.4, 0.4)
    zero = eio((t - 102.6) / 0.6) * (1 - eio((t - 106.6) / 0.6))
    vals = []
    for i, (s, col, v) in enumerate(FACT):
        vv = v * eo((t - 98.5 - i * 0.25) / 0.8)
        if i == 0: vv *= 1 - zero
        vals.append(vv)
        x = cen[2 + 2 * i]
        y0, hh, w = 700, 330, 70
        f.rrect(x - w / 2, y0 - hh, x + w / 2, y0, 8, col, m * 0.35, 1)
        if vv > 0.005:
            cc = lerpc(col, RED, zero) if i == 0 else col
            f.rrect_fill(x - w / 2, y0 - hh * vv, x + w / 2, y0, 8, cc, m * 0.35, 'L')
            f.rrect(x - w / 2, y0 - hh * vv, x + w / 2, y0, 8, cc, m, 2)
            f.glow((x, y0 - hh * vv), 16, cc, m * 0.7, 'B')
        f.text(f'{vv:.1f}', x, y0 - hh * vv - 34, 44, 'bebas', lerpc(col, WHITE, .4) if not (i == 0 and zero > 0.5) else RED,
               m, mode='L', glow=0.3)
        if i < 3:
            f.text('×', (x + cen[4 + 2 * i]) / 2, y0 - hh / 2, 50, 'sans_light', GREY, m * 0.6, mode='L')
    prod = vals[0] * vals[1] * vals[2] * vals[3]
    rc = lerpc(GOLD2, RED, zero)
    f.text('=', 1590, 560, 60, 'sans_light', GREY, m, mode='L')
    f.text(f'{prod:.2f}', 1730, 545, 120, 'bebas', rc, m, mode='E', glow=0.6 + 0.4 * beat_pulse(t))
    f.text('护城河强度', 1730, 625, 26, 'sans_light', GREY, m, mode='L')
    if 102.6 < t < 104:
        f.shake = (int(round(6 * math.exp(-(t - 102.9) / 0.15) * math.sin(t * 90))), 0) if t > 102.9 else (0, 0)
        ripple(f, t, 102.9, 1730, 545, RED, m, 2, 220, 0.9)
    z1 = env(t, 102.6, 106.6, 0.3, 0.3)
    f.text('如果没人看得见（比如只在家里用）——', W / 2, 800, 36, 'sans_med', lerpc(RED, WHITE, .4), z1, t0=102.6, stag=0.025)
    z2 = env(t, 103.8, 109.9, 0.3, 0.4)
    f.dim(330, 850, 1590, 980, 0.6 * z2, 30)
    f.text('这是乘法：任何一项归零，护城河就归零', W / 2, 905, 50, 'serif_black', GOLD2, z2, t0=103.8, stag=0.05,
           mode='E', glow=0.5)
    z3 = env(t, 106.8, 109.9, 0.3, 0.4)
    f.text('四个因子，缺一不可', W / 2, 800, 36, 'sans_med', WHITE, z3, t0=106.8, stag=0.05)

# ---------------------------------------------------------------- 02c 不是凡勃伦 110–122
def mini_chart(f, t, x0, y0, w, h, a, curves, xl='价格 →', yl='需求量 ↑'):
    f.line((x0, y0 + h), (x0 + w, y0 + h), GREY, a * 0.7, 2)
    f.line((x0, y0 + h), (x0, y0), GREY, a * 0.7, 2)
    f.text(xl, x0 + w - 10, y0 + h + 30, 24, 'sans_light', GREY, a, 'r')
    f.text(yl, x0 + 10, y0 - 22, 24, 'sans_light', GREY, a, 'l')
    for fn, col, t0, lab, lu, dash in curves:
        p = eo((t - t0) / 1.2)
        if p <= 0: continue
        us = np.linspace(0.05, 0.05 + 0.9 * p, 60)
        pts = [(x0 + u * w, y0 + h - fn(u) * h) for u in us]
        if dash:
            for k in range(0, len(pts) - 1, 2):
                f.line(pts[k], pts[k + 1], col, a * 0.6, 2)
        else:
            f.poly(pts, col, a, 4)
            f.glow(pts[-1], 10, col, a * 0.8, 'B')
        if p > 0.95 and lab:
            f.text(lab, x0 + lu[0] * w, y0 + h - lu[1] * h, 26, 'sans_med', col, a * eo((t - t0 - 1.0) / 0.4), 'l')

def sc_veblen(f, t):
    if not (110 < t < 122.3): return
    a = env(t, 110.1, 121.9, 0.4, 0.4)
    f.text('注意：这不是「凡勃伦效应」', W / 2, 150, 54, 'serif_black', WHITE, a, t0=110.2, stag=0.05, glow=0.2)
    L = (230, 330, 620, 380); R = (1070, 330, 620, 380)
    f.text('凡勃伦商品', L[0] + L[2] / 2, 270, 38, 'serif_black', RED, a * eo((t - 110.8) / 0.4), mode='L', glow=0.3)
    f.text('大众地位品牌', R[0] + R[2] / 2, 270, 38, 'serif_black', GOLD2, a * eo((t - 113.2) / 0.4), mode='L', glow=0.3)
    mini_chart(f, t, *L, a * eo((t - 110.8) / 0.5), [(lambda u: 0.1 + 0.75 * u ** 1.3, RED, 111.2, '越贵，越想买', (0.25, 0.75), False)])
    mini_chart(f, t, *R, a * eo((t - 113.2) / 0.5), [
        (lambda u: 0.75 - 0.7 * u, GREY, 113.5, '普通商品', (0.62, 0.22), True),
        (lambda u: 0.92 - 0.55 * u, GOLD, 114.4, '愿付更高价', (0.5, 0.83), False)])
    if t > 115.6:
        p = eo((t - 115.6) / 0.5)
        x = R[0] + 0.4 * R[2]
        arrow(f, (x, R[1] + R[3] - (0.75 - 0.28) * R[3]), (x, R[1] + R[3] - (0.92 - 0.22) * R[3] + 8), GOLD2, a * p, 2, 12)
    f.text('价格本身提高购买意愿', L[0] + L[2] / 2, 765, 28, 'sans_light', lerpc(RED, WHITE, .4), a * eo((t - 112.2) / 0.4))
    f.text('需求曲线仍向下：不是因为贵才买', R[0] + R[2] / 2, 765, 28, 'sans_light', lerpc(GOLD, WHITE, .4),
           a * eo((t - 115.4) / 0.4))
    b = env(t, 116.8, 121.9, 0.4, 0.4)
    f.text('价格本身不是购买理由——信号才是', W / 2, 870, 50, 'serif_black', GOLD2, b, t0=116.8, stag=0.05, mode='E', glow=0.55)
    c = env(t, 118.6, 121.9, 0.4, 0.4)
    f.text('更准确地说：社会地位信号 + 从众效应 + 部分炫耀性消费', W / 2, 950, 28, 'sans_light', WHITE, c, t0=118.6, stag=0.015)


# ---------------------------------------------------------------- 03a 奢侈 vs 大众 122–140
_PY = np.random.default_rng(44)
def tri_pts(n, seed):
    r = np.random.default_rng(seed)
    u = r.uniform(0, 1, (n * 3, 2))
    u = u[u[:, 0] + u[:, 1] <= 1][:n]
    return u
LUX = tri_pts(90, 1); MAS = tri_pts(900, 2)
LUX_P = _PY.uniform(0, 6.28, 90); MAS_P = _PY.uniform(0, 6.28, 900)
ROWS = [('目标消费群体', '相对集中', '通常更广'),
        ('身份价值', '稀缺 · 财富 · 阶层', '品位 · 生活方式 · 归属'),
        ('规模扩大', '可能削弱稀缺性', '可能增强社会认同'),
        ('定价能力', '依赖稀缺与身份溢价', '依赖质量 · 品牌 · 转换成本'),
        ('成长潜力', '受稀缺定位限制', '可随用户群扩大而增长')]

def pyramid(f, t, cx, yb, w, h, u, ph, col, a, dot=False):
    # barycentric -> triangle (apex at top)
    A = np.array([cx, yb - h]); B = np.array([cx - w / 2, yb]); Cc = np.array([cx + w / 2, yb])
    P = A + (B - A) * u[:, :1] + (Cc - A) * u[:, 1:2]
    tw = 0.6 + 0.4 * np.sin(ph + t * 2)
    if dot: f.dots(P[:, 0], P[:, 1], col, a * tw, 1, 'E')
    else: f.splat(P[:, 0], P[:, 1], col, a * tw * 1.6, 'E')
    f.poly([tuple(B), tuple(A), tuple(Cc)], col, a * 0.5, 1)

def sc_luxury(f, t):
    if not (122 < t < 140.3): return
    a = env(t, 122.1, 139.9, 0.3, 0.4)
    f.text('奢侈品牌', 560, 130, 46, 'serif_black', GOLD, a, t0=122.3, stag=0.06, mode='E', glow=0.4)
    f.text('VS', W / 2, 130, 34, 'orb', GREY, a, mode='L')
    f.text('大众身份品牌', 1360, 130, 46, 'serif_black', CYAN, a, t0=122.6, stag=0.06, mode='E', glow=0.4)
    p = eo((t - 122.4) / 1.0)
    pyramid(f, t, 560, 420, 150 * p, 230, LUX, LUX_P, GOLD2, a * p, dot=True)
    pyramid(f, t, 1360, 420, 640 * p, 170, MAS, MAS_P, CYAN, a * p)
    f.text('少数人 · 稀缺', 560, 455, 26, 'sans_light', GOLD2, a * p)
    f.text('多数人 · 可及', 1360, 455, 26, 'sans_light', CYAN, a * p)
    hl = env(t, 135.6, 139.9, 0.4, 0.4)
    for i, (dim_, lv, rv) in enumerate(ROWS):
        t0 = 124.6 + i * 2.0
        q = eo((t - t0) / 0.5)
        if q <= 0: continue
        y = 530 + i * 86
        emph = 1 + 0.6 * hl if i == 2 else 1 - 0.45 * hl
        f.line((240, y - 43), (1680, y - 43), GREY, a * q * 0.18, 1)
        f.text(dim_, W / 2, y, 30, 'sans_med', WHITE, a * q * min(emph, 1), mode='L')
        f.text(lv, 830 - 30 * (1 - q), y, 32, 'serif_med', GOLD2, a * q * min(emph, 1), 'r', mode='L', glow=0.2 * emph)
        f.text(rv, 1090 + 30 * (1 - q), y, 32, 'serif_med', lerpc(CYAN, WHITE, .3), a * q * min(emph, 1), 'l', mode='L',
               glow=0.2 * emph)
        if i == 2 and hl > 0:
            f.rrect(230, y - 36, 1690, y + 36, 18, GOLD, a * hl * 0.8, 2)
            f.glow((W / 2, y), 300, GOLD, a * hl * 0.12 * (1 + bar_pulse(t)), 'B')

# ---------------------------------------------------------------- 03b 毛利率 / Costco 140–160
def hbar(f, t, x0, y, wmax, v, col, a, t0, label, val_txt):
    p = eo((t - t0) / 1.2)
    w = wmax * v * p
    f.rrect(x0, y - 30, x0 + wmax, y + 30, 12, GREY, a * 0.2, 1)
    if w > 4:
        f.rrect_fill(x0, y - 30, x0 + w, y + 30, 12, col, a * 0.3, 'L')
        f.rrect(x0, y - 30, x0 + w, y + 30, 12, col, a, 2)
        f.glow((x0 + w, y), 22, col, a * 0.6, 'B')
    f.text(label, x0 - 30, y, 40, 'serif_black', WHITE, a, 'r', mode='L')
    f.text(val_txt(p), x0 + w + 24, y + 2, 64, 'bebas', lerpc(col, WHITE, .3), a, 'l', mode='E', glow=0.4)

def donut(f, t, cx, cy, r, frac, col, a, t0):
    p = eo((t - t0) / 1.4)
    f.arc((cx, cy), r, 0, 2 * math.pi, GREY, a * 0.3, 30, 90)
    if p > 0:
        a0 = -math.pi / 2
        f.arc((cx, cy), r, a0, a0 + 2 * math.pi * frac * p, col, a, 34, 90)
        e = a0 + 2 * math.pi * frac * p
        f.glow((cx + r * math.cos(e), cy + r * math.sin(e)), 26, col, a * 0.8, 'B')

def sc_margin(f, t):
    if not (140 < t < 160.2): return
    a = env(t, 140.1, 159.9, 0.4, 0.3)
    s1 = a * (1 - eio((t - 149.4) / 0.6))
    f.text('市场更大 ≠ 定价权更强', W / 2, 160, 58, 'serif_black', WHITE, s1, t0=140.2, stag=0.05, glow=0.25)
    f.text('毛利率（FY2024 公司年报 · 约数）', W / 2, 260, 28, 'sans_light', GREY, s1, t0=140.8, stag=0.02)
    hbar(f, t, 560, 410, 1000, 0.46, GOLD, s1, 141.4, '苹果', lambda p: f'{46 * p:.0f}%')
    hbar(f, t, 560, 560, 1000, 0.11, CYAN, s1, 142.2, 'Costco', lambda p: f'{11 * p:.0f}%')
    f.text('（Costco 为商品毛利率）', 560 + 110 + 220, 610, 22, 'sans_light', GREY, s1 * eo((t - 143) / 0.5), 'l')
    b = env(t, 144.6, 149.6, 0.3, 0.4)
    f.text('同样有强烈认同感，赚钱的方式却完全不同', W / 2, 740, 42, 'serif_black', GOLD2, b, t0=144.6, stag=0.04,
           mode='E', glow=0.4)
    f.text('苹果：产品溢价  ·  Costco：低毛利 + 会员费', W / 2, 820, 30, 'sans_light', WHITE, b, t0=145.8, stag=0.025)
    # part 2: costco membership donut
    s2 = env(t, 149.8, 159.9, 0.5, 0.3)
    if s2 > 0:
        cx, cy = 560, 560
        donut(f, t, cx, cy, 200, 0.52, GOLD, s2, 150.2)
        f.text(f'{52 * eo((t - 150.2) / 1.4):.0f}%', cx, cy - 20, 110, 'bebas', GOLD2, s2, mode='E', glow=0.5)
        f.text('会员费 ÷ 营业利润', cx, cy + 60, 26, 'sans_light', WHITE, s2)
        f.text('Costco FY2024：会员费约 48 亿美元，营业利润约 93 亿美元', cx, cy + 270, 22, 'sans_light', GREY, s2, t0=151)
        f.text('Costco 不靠商品的身份溢价赚钱', 900, 400, 42, 'serif_black', WHITE, s2, 'l', t0=150.6, stag=0.04, glow=0.2)
        f.text('而是靠会员的信任与续费', 900, 470, 42, 'serif_black', CYAN, s2, 'l', t0=151.8, stag=0.04, glow=0.3)
        c = env(t, 153.8, 159.9, 0.3, 0.3)
        f.text('身份认同 ≠ 高利润', 900, 600, 70, 'serif_black', GOLD2, c, 'l', t0=153.8, stag=0.07, mode='E', glow=0.6)
        d = env(t, 155.8, 159.9, 0.3, 0.3)
        f.text('真正要问：身份价值，', 902, 700, 36, 'sans_med', WHITE, d, 'l', t0=155.8, stag=0.03)
        f.text('能否变成可持续的经济利润？', 902, 752, 36, 'sans_med', GOLD2, d, 'l', t0=156.6, stag=0.03)
    implode(f, t, 157.6, 160.0, W / 2, H / 2, [WHITE, CYAN, SILVER, GOLD2, BLUE, WHITE], 0.8)


# ---------------------------------------------------------------- 04a 苹果 160–178
LAYERS = [('产品力', CYAN), ('生态系统', BLUE), ('可靠性', TEAL), ('转换成本', VIOLET), ('身份信号', GOLD)]

def sc_apple(f, t):
    if not (159.9 < t < 178.3): return
    a = env(t, 160.0, 177.9, 0.1, 0.4)
    cx, cy = 600, 560
    lp_ = env(t, 163.8, 177.9, 0.4, 0.4)
    for k, (lab, col) in enumerate(LAYERS):
        q = eo((t - 164.2 - k * 1.0) / 0.6)
        if q <= 0: continue
        d = 34 + k * 36
        hh = 420 + 2 * d; ww = 206 + 2 * d
        emph = 1.6 if k == 4 else 1.0
        f.rrect(cx - ww / 2, cy - hh / 2, cx + ww / 2, cy + hh / 2, 40 + d * 0.5, col, a * lp_ * q * 0.6 * emph, 2)
        n = 40
        for j in range(3):
            u = (t * (0.08 + 0.03 * k) + j / 3 + k * 0.13) % 1.0
            per = 2 * (ww + hh); s = u * per
            if s < ww: px, py = cx - ww / 2 + s, cy - hh / 2
            elif s < ww + hh: px, py = cx + ww / 2, cy - hh / 2 + s - ww
            elif s < 2 * ww + hh: px, py = cx + ww / 2 - (s - ww - hh), cy + hh / 2
            else: px, py = cx - ww / 2, cy + hh / 2 - (s - 2 * ww - hh)
            f.glow((px, py), 4, WHITE, a * lp_ * q, 'E'); f.glow((px, py), 12, col, a * lp_ * q * 0.6, 'B')
    burst(f, t, 160.0, cx, cy, [WHITE, SILVER, CYAN, GOLD2], 2, 600, 1400, 1.2, 2.4, 0.9)
    icon_phone(f, cx, cy, 420, SILVER, a * eo((t - 160.0) / 0.5), t, True, rim=1.0)
    f.text('苹果 · iPhone Pro', 1060, 200, 60, 'serif_black', WHITE, a, 'l', t0=160.3, stag=0.05, glow=0.3)
    q1 = env(t, 161.4, 166.2, 0.3, 0.4)
    f.text('「我拿着一部 iPhone——', 1060, 310, 38, 'serif_med', lerpc(SILVER, WHITE, .5), q1, 'l', t0=161.4, stag=0.04)
    f.text('别人可能觉得我有消费能力、重视品质。」', 1060, 370, 38, 'serif_med', GOLD2, q1, 'l', t0=162.4, stag=0.04)
    l2 = env(t, 164.0, 170.6, 0.3, 0.4)
    f.text('但它的护城河是多层叠加的：', 1060, 310, 38, 'serif_black', WHITE, l2 * eo((t - 166.2) / 0.4), 'l', t0=166.2, stag=0.03)
    for k, (lab, col) in enumerate(LAYERS):
        q = eo((t - 164.2 - k * 1.0) / 0.5)
        chip(f, lab, 1060, 410 + k * 82, 34, col, l2 * q, 'serif_black', anchor='l')
    l3 = env(t, 170.6, 177.9, 0.3, 0.4)
    if l3 > 0:
        f.text('全球智能手机（部分年份 · 机构估算 · 约数）', 1060, 310, 26, 'sans_light', GREY, l3, 'l')
        for k, (lab, v, col) in enumerate((('出货量份额', 0.2, SILVER), ('行业利润份额', 0.8, GOLD))):
            y = 400 + k * 120
            p = eo((t - 171.0 - k * 0.8) / 1.0)
            f.text(lab, 1060, y - 34, 28, 'sans_med', WHITE, l3, 'l')
            f.rrect(1060, y - 12, 1760, y + 22, 10, GREY, l3 * 0.25, 1)
            if p > 0:
                f.rrect_fill(1060, y - 12, 1060 + 700 * v * p, y + 22, 10, col, l3 * 0.4, 'L')
                f.glow((1060 + 700 * v * p, y + 5), 16, col, l3 * 0.7, 'B')
            f.text(f'≈ {int(round(v * 10 * p))} 成', 1780, y - 34, 40, 'sans_black', col, l3 * eo((t - 171.0 - k * 0.8) / 0.4), 'r',
                   mode='L', glow=0.3)
        g = env(t, 173.6, 177.9, 0.3, 0.4)
        f.text('身份动机确实存在，', 1060, 680, 36, 'serif_black', GOLD2, g, 'l', t0=173.6, stag=0.04, mode='E', glow=0.4)
        f.text('但没有消费者研究数据时，不应断言它占主导', 1060, 735, 30, 'sans_light', WHITE, g, 'l', t0=174.4, stag=0.02)

# ---------------------------------------------------------------- 04b 山姆中国 178–198
_SR = np.random.default_rng(55)
SAM_X = _SR.uniform(0, 1, 500); SAM_Y = _SR.uniform(0, 1, 500); SAM_P = _SR.uniform(0, 6.28, 500); SAM_S = _SR.uniform(.5, 1.5, 500)

def sc_sam(f, t):
    if not (178 < t < 198.3): return
    a = env(t, 178.1, 197.9, 0.4, 0.4)
    alarm = eo((t - 190.0) / 0.3)
    hdr = a * (1 - alarm)
    f.text('山姆中国 · 会员店', W / 2, 140, 56, 'serif_black', WHITE, hdr, t0=178.2, stag=0.05, glow=0.25)
    f.text('2025 · 一场「巧克力派」风波', W / 2, 140, 56, 'serif_black', lerpc(RED, WHITE, .3), a * alarm, t0=190.0,
           stag=0.05, mode='E', glow=0.5)
    gx, gy, gw, gh = W / 2, 520, 260, 420
    gate_col = lerpc(GOLD2, RED, alarm * (0.6 + 0.4 * math.sin(t * 8) ** 2) if t < 194 else alarm * 0.4)
    icon_gate(f, gx, gy, gw, gh, gate_col, a)
    f.text('会员门槛', gx, gy - gh / 2 - 80, 28, 'sans_light', GREY, a, mode='L')
    f.text('¥260', gx - 22, gy - gh / 2 - 34, 50, 'bebas', GOLD, a, mode='L', glow=0.4)
    f.text('/ 年', gx + 48, gy - gh / 2 - 30, 30, 'sans_black', GOLD, a, mode='L', glow=0.3)
    # particles: outside (left) grey wander, inside (right) gold calm
    leak = eo((t - 190.2) / 2.5)
    n = 500
    ox = 220 + SAM_X[:n] * 470 + 18 * np.sin(t * SAM_S[:n] + SAM_P[:n])
    oy = 330 + SAM_Y[:n] * 400 + 14 * np.cos(t * SAM_S[:n] * 1.3 + SAM_P[:n])
    ix = 1230 + SAM_X[:n] * 470 + 10 * np.sin(t * 0.6 * SAM_S[:n] + SAM_P[:n])
    iy = 330 + SAM_Y[:n] * 400 + 8 * np.cos(t * 0.5 * SAM_S[:n] + SAM_P[:n])
    move = (SAM_P[:n] < 6.28 * 0.35)
    k = np.clip(leak * 1.4 - SAM_X[:n] * 0.4, 0, 1)
    ox2 = np.where(move, ox + (ix - ox) * k, ox)
    oy2 = np.where(move, oy + (iy - oy) * k + np.sin(k * math.pi) * (gy - oy) * 0.8, oy)
    pa = a * eo((t - 178.6) / 0.8)
    f.dots(ox2, oy2, SILVER, pa * 1.3 * (0.6 + 0.4 * np.sin(SAM_P[:n] + t)), 1, 'E')
    f.dots(ix, iy, GOLD2, pa * 1.5 * (0.6 + 0.4 * np.sin(SAM_P[:n] + t * 1.3)) * (1 - 0.3 * alarm), 1, 'E')
    f.glow((1460, 530), 260, GOLD, pa * 0.12, 'B')
    f.text('外面', 455, 780, 26, 'sans_light', GREY, pa * (1 - alarm))
    f.text('里面', 1465, 780, 26, 'sans_light', GOLD2, pa * (1 - alarm))
    if 190.0 < t < 193:
        ripple(f, t, 190.0, gx, gy, RED, a, 3, 600, 1.2, 3)
        ripple(f, t, 191.0, gx, gy, RED, a * 0.6, 2, 500, 1.2, 2)
    s1 = env(t, 179.6, 186.0, 0.3, 0.4)
    f.text('不是「我买得起贵东西」，', W / 2, 860, 38, 'sans_med', lerpc(GREY, WHITE, .4), s1, t0=179.6, stag=0.04)
    f.text('而是「我属于注重品质、懂得挑选的城市中产家庭」', W / 2, 930, 44, 'serif_black', GOLD2, s1 * eo((t - 181.4) / 0.4),
           t0=181.4, stag=0.04, mode='E', glow=0.45)
    s2 = env(t, 186.0, 190.0, 0.3, 0.2)
    f.text('会员费 + 商品筛选 + 服务体验 = 区分感', W / 2, 890, 44, 'serif_black', WHITE, s2, t0=186.0, stag=0.04, glow=0.3)
    s3 = env(t, 190.4, 197.9, 0.3, 0.4)
    f.text('大众化零食上架 → 部分会员强烈不满', W / 2, 830, 38, 'sans_med', lerpc(RED, WHITE, .35), s3, t0=190.4, stag=0.03)
    s4 = env(t, 192.6, 197.9, 0.3, 0.4)
    f.dim(220, 870, 1700, 1000, 0.7 * s4, 30)
    f.text('他们担心的不是一块零食，而是自己的「身份区分」被稀释', W / 2, 912, 44, 'serif_black', GOLD2, s4, t0=192.6,
           stag=0.035, mode='E', glow=0.5)
    s5 = env(t, 195.2, 197.9, 0.3, 0.4)
    f.text('（地位感有地域与群体差异：山姆中国 ≠ 美国 Costco）', W / 2, 970, 24, 'sans_light', GREY, s5, t0=195.2, stag=0.01)

# ---------------------------------------------------------------- 04c 筛选散点图 198–216
BRANDS = [  # name, accessibility, status signal, category, label side
    ('iPhone Pro', .76, .84, 0, 'r'), ('山姆中国', .84, .74, 0, 'r'), ('lululemon', .62, .68, 1, 'l'),
    ('始祖鸟', .45, .82, 1, 'l'), ('戴森', .58, .56, 2, 'l'), ('星巴克', .93, .50, 2, 'l'),
    ('喜诗糖果', .74, .44, 2, 'l'), ('Costco 美国', .82, .30, 3, 'r'), ('小米', .88, .18, 3, 'l'),
    ('名创优品', .96, .09, 3, 'l'), ('乐高', .60, .24, 3, 'l')]
CATS = [(GOLD, '高度符合'), (CYAN, '符合'), (VIOLET, '候选 / 部分 / 场景性'), (GREY, '不符合核心定义')]

def sc_scatter(f, t):
    if not (198 < t < 216.3): return
    a = env(t, 198.1, 215.9, 0.4, 0.4)
    f.text('按严格标准，重新筛选', W / 2, 135, 52, 'serif_black', WHITE, a, t0=198.2, stag=0.05, glow=0.25)
    X0, Y0, X1, Y1 = 330, 220, 1500, 900
    pa = a * eo((t - 198.5) / 0.6)
    f.line((X0, Y1), (X1, Y1), GREY, pa * 0.8, 2); f.line((X0, Y1), (X0, Y0), GREY, pa * 0.8, 2)
    arrow(f, (X1 - 2, Y1), (X1 + 14, Y1), GREY, pa * 0.8, 2, 12); arrow(f, (X0, Y0 + 2), (X0, Y0 - 14), GREY, pa * 0.8, 2, 12)
    f.text('大众可及性 →', X1, Y1 + 38, 28, 'sans_med', WHITE, pa, 'r')
    f.text('↑ 地位信号强度', X0 + 14, Y0 - 6, 28, 'sans_med', WHITE, pa, 'l')
    for g in (0.25, 0.5, 0.75):
        f.line((X0 + 4, Y1 - g * (Y1 - Y0)), (X1, Y1 - g * (Y1 - Y0)), GREY, pa * 0.08, 1)
        f.line((X0 + g * (X1 - X0), Y0), (X0 + g * (X1 - X0), Y1 - 4), GREY, pa * 0.08, 1)
    z = env(t, 199.4, 215.9, 0.6, 0.4)
    zx0, zy0 = X0 + 0.58 * (X1 - X0), Y1 - 0.62 * (Y1 - Y0)
    f.rrect_fill(zx0, Y0 + 10, X1 - 10, zy0, 20, GOLD, z * 0.06 * (1 + 0.5 * bar_pulse(t)), 'L')
    f.rrect(zx0, Y0 + 10, X1 - 10, zy0, 20, GOLD, z * 0.5, 1)
    f.text('核心区：大众可及 × 地位信号', (zx0 + X1) / 2, Y0 + 38, 24, 'sans_med', GOLD2, z, mode='L')
    focus = eo((t - 210.6) / 0.6)
    for i, (nm, x, y, cat, side) in enumerate(BRANDS):
        t0 = 199.8 + i * 0.5
        p = cl((t - t0) / 0.35)
        if p <= 0: continue
        col = CATS[cat][0]
        px, py = X0 + x * (X1 - X0), Y1 - y * (Y1 - Y0)
        da = a * eo(p) * (1 - 0.6 * focus if cat >= 2 else 1)
        sc = 1 + 0.6 * (1 - eback(p, 2.5))
        r = (11 if cat < 2 else 8) * sc * (1 + 0.25 * focus * beat_pulse(t) if cat == 0 else 1)
        f.circle((px, py), r, col, da, 2 if cat < 3 else 1)
        f.glow((px, py), r * 0.6, lerpc(col, WHITE, .4), da, 'E')
        f.glow((px, py), r * 2.4, col, da * 0.45, 'B')
        if p < 1: ripple(f, t, t0, px, py, col, da, 1, 60, 0.5)
        fs = 30 if cat < 2 else 24
        f.text(nm, px + (r + 14) * (1 if side == 'r' else -1), py, fs, 'sans_med' if cat < 2 else 'sans_light',
               lerpc(col, WHITE, .35), da, 'l' if side == 'r' else 'r', mode='L')
        if nm == '星巴克' and t > 206:
            q = eo((t - 206) / 0.8)
            arrow(f, (px + 22, py + 4), (px + 22, py + 4 + 70 * q), VIOLET, da * q, 2, 10)
            f.text('地位属性弱化', px + 10, py + 96, 20, 'sans_light', VIOLET, da * q, 'r')
    lg = env(t, 207.6, 215.9, 0.4, 0.4)
    for k, (col, lab) in enumerate(CATS):
        y = 380 + k * 56
        f.circle((1570, y), 9, col, lg, 2); f.glow((1570, y), 5, col, lg, 'E')
        f.text(lab, 1592, y, 24, 'sans_light', lerpc(col, WHITE, .4), lg, 'l')
    fn = env(t, 210.6, 215.9, 0.4, 0.4)
    for k, (s_, sz, col, fn_) in enumerate((('优先研究：', 26, GOLD2, 'sans_med'), ('苹果 · 山姆中国', 28, WHITE, 'serif_black'),
                                       ('lululemon · 高端户外', 28, WHITE, 'serif_black'),
                                       ('而不是把所有高端、有粉丝、', 22, GREY, 'sans_light'), ('高复购的品牌都算进来', 22, GREY, 'sans_light'))):
        f.text(s_, 1560, 700 + k * 46 + (12 if k > 2 else 0), sz, fn_, col, fn, 'l', t0=210.6 + k * 0.3, stag=0.015)
    f.text('定性筛选示意 · 非消费者实验排名', X1, 975, 22, 'sans_light', GREY, a * eo((t - 201) / 0.5), 'r')


# ---------------------------------------------------------------- 05 普及悖论 216–252
CX0, CX1, CYB, CH = 300, 1620, 860, 560

def curve_v(u, m=0.0):
    u = np.asarray(u, np.float64)
    left = 0.12 + 0.76 * np.exp(-((u - 0.5) / 0.27) ** 2)
    d = np.maximum(u - 0.5 - 0.14 * m, 0)
    right = 0.12 + 0.76 * np.exp(-(d / (0.36 + 0.08 * m)) ** 2)
    return np.where(u <= 0.5, left, right)

def cpt(u, m=0.0):
    return (CX0 + u * (CX1 - CX0), CYB - float(curve_v(u, m)) * CH)

_UR = np.random.default_rng(66)
CROWD_U = np.sort(_UR.uniform(0.01, 0.99, 1500)); CROWD_W = _UR.uniform(0.02, 0.98, 1500) ** 1.3

def sc_paradox(f, t):
    if not (216 < t < 252.3): return
    a = env(t, 216.1, 251.9, 0.5, 0.4)
    q = env(t, 216.2, 222.2, 0.5, 0.4)
    f.text('用户越多，品牌越强——', W / 2, 430, 64, 'serif_black', WHITE, q, t0=216.3, stag=0.06, glow=0.2)
    f.text('还是越弱？', W / 2, 580, 110, 'serif_black', MAGENTA, q * eo((t - 218.4) / 0.4), t0=218.4, stag=0.15,
           dur=0.6, mode='E', glow=0.7)
    if t < 222: return
    m = eio((t - 241.6) / 2.0)
    forces = env(t, 236.0, 241.6, 0.3, 0.4)
    ca = a * (1 - 0.55 * forces) * eo((t - 222.0) / 0.6)
    # axes
    f.line((CX0, CYB), (CX1 + 30, CYB), GREY, ca * 0.8, 2); f.line((CX0, CYB), (CX0, CYB - CH - 30), GREY, ca * 0.8, 2)
    f.text('身份象征价值', CX0 + 12, CYB - CH - 36, 28, 'sans_med', WHITE, ca * (1 - eo((t - 241.6) / 0.4)), 'l')
    f.text('少数人使用', CX0, CYB + 36, 26, 'sans_light', GREY, ca, 'l')
    f.text('人人都使用', CX1, CYB + 36, 26, 'sans_light', GREY, ca, 'r')
    f.text('品牌普及程度 →', (CX0 + CX1) / 2, CYB + 40, 28, 'sans_med', WHITE, ca)
    f.text('理论假设示意，不是实际估计的需求曲线', CX1, 975, 22, 'sans_light', GREY, ca, 'r')
    dp = eo((t - 222.6) / 2.2)
    us = np.linspace(0, dp, max(2, int(140 * dp)))
    pts = [cpt(u, m) for u in us]
    lc = lerpc(CYAN, MAGENTA, 0.0)
    if len(pts) > 1:
        cols = [CYAN, VIOLET, MAGENTA]
        for k in range(len(pts) - 1):
            col = grad_color(cols, us[k])
            f.line(pts[k], pts[k + 1], col, ca, 5)
    if m > 0:   # extended sweet spot glow
        for u in np.linspace(0.42, 0.5 + 0.14 * m + 0.05, 30):
            f.glow(cpt(u, m), 14, GOLD, a * m * 0.45, 'B')
    # traveling dot
    u = eio((t - 225.0) / 8.0) if t < 236 else 0.5 + 0.07 * math.sin((t - 236) * 2.6) * forces
    if t >= 236 and t > 241.6: u = 0.5 + 0.14 * m * (0.5 + 0.5 * math.sin((t - 241.6) * 1.2))
    if t > 225:
        # crowd under curve
        k = np.searchsorted(CROWD_U, u)
        cu = CROWD_U[:k]; cw = CROWD_W[:k]
        xs = CX0 + cu * (CX1 - CX0); ys = CYB - cw * curve_v(cu, m) * CH
        cc = np.array([grad_color([CYAN, VIOLET, MAGENTA], x) for x in cu], np.float32) if k else np.zeros((0, 3), np.float32)
        f.splat(xs, ys, cc, ca * 0.9, 'E')
        p = cpt(u, m)
        f.glow(p, 8, WHITE, a, 'E'); f.glow(p, 30, grad_color([CYAN, VIOLET, MAGENTA], u), a * 0.9, 'B')
        f.circle(p, 16 + 4 * beat_pulse(t), WHITE, a * 0.8, 2)
    # region labels
    hide = 1 - eo((t - 236.0) / 0.4)
    for (uu, title, sub, col, tt0) in ((0.17, '认知不足', '没人认得出，信号无效', CYAN, 226.4),
                                      (0.5, '最佳社会识别区间', '', GOLD2, 229.0),
                                      (0.84, '过度普及', '人人都有，就不再特别', MAGENTA, 231.6)):
        la = ca * eo((t - tt0) / 0.5) * (hide if uu != 0.5 else 1 - eo((t - 241.6) / 0.4))
        if la <= 0: continue
        if uu == 0.5:
            px, py = cpt(0.5, m)
            dashed(f, (px, py + 20), (px, CYB), GOLD, la * 0.6, 2, 10, 8, t * 0.5)
            f.text(title, px, py - 48, 40, 'serif_black', GOLD2, la, mode='E', glow=0.5)
        else:
            px, py = cpt(uu, 0)
            ox = 150 if uu < 0.5 else -150
            f.text(title, px + ox, py - 10, 38, 'serif_black', lerpc(col, WHITE, .3), la, mode='L', glow=0.3)
            f.text(sub, px + ox, py + 38, 26, 'sans_light', WHITE, la * 0.9)
    h1 = env(t, 233.2, 236.0, 0.3, 0.2)
    f.text('先增强，后削弱', W / 2, 175, 66, 'serif_black', GOLD2, h1, t0=233.2, stag=0.08, mode='E', glow=0.6)
    # forces
    if forces > 0:
        p = cpt(u, m)
        f.text('两股力量的拉扯', W / 2, 175, 60, 'serif_black', WHITE, forces, t0=236.1, stag=0.06, glow=0.3)
        for k in range(14):
            v = ((t * 0.9 + k / 14) % 1.0)
            f.glow((p[0] - 420 + 380 * v, p[1] + 90 + 8 * math.sin(k)), 4, CYAN, forces * (1 - v) * 0.9 + 0.1, 'E')
            f.glow((p[0] + 420 - 380 * v, p[1] + 150 + 8 * math.sin(k)), 4, MAGENTA, forces * (1 - v) * 0.9 + 0.1, 'E')
        arrow(f, (p[0] - 420, p[1] + 90), (p[0] - 30, p[1] + 90), CYAN, forces, 4, 18)
        arrow(f, (p[0] + 420, p[1] + 150), (p[0] + 30, p[1] + 150), MAGENTA, forces, 4, 18)
        f.text('从众动机 → 推动普及', p[0] - 430, p[1] + 40, 36, 'serif_black', lerpc(CYAN, WHITE, .3), forces, 'l', t0=236.4,
               stag=0.03, glow=0.3)
        f.text('「我也想属于那个群体」', p[0] - 430, p[1] + 132, 26, 'sans_light', CYAN, forces, 'l', t0=237.0, stag=0.02)
        f.text('差异化动机 ← 要求区分', p[0] + 430, p[1] + 205, 36, 'serif_black', lerpc(MAGENTA, WHITE, .3), forces, 'r',
               t0=237.4, stag=0.03, glow=0.3)
        f.text('「我要和别人不一样」', p[0] + 430, p[1] + 250, 26, 'sans_light', MAGENTA, forces, 'r', t0=238.0, stag=0.02)
    s = env(t, 241.6, 251.9, 0.4, 0.4)
    if s > 0:
        f.text('聪明的品牌，会想办法留在山顶', W / 2, 175, 56, 'serif_black', WHITE, s, t0=241.7, stag=0.05, glow=0.3)
        for k, (x0, nm, items, col, t0) in enumerate(((330, '山姆', '会员费 · 商品筛选 · 服务体验', CYAN, 243.4),
                                                      (1050, '苹果', 'Pro 产品线 · 设计 · 品牌形象', SILVER, 245.4))):
            c = s * eo((t - t0) / 0.5)
            if c <= 0: continue
            y0 = 560 if k == 0 else 600
            f.dim(x0, y0, x0 + 540, y0 + 170, 0.75 * c, 22)
            f.rrect(x0, y0, x0 + 540, y0 + 170, 22, col, c * 0.8, 2)
            f.text(nm, x0 + 30, y0 + 50, 40, 'serif_black', lerpc(col, WHITE, .3), c, 'l', mode='L', glow=0.3)
            f.text(items, x0 + 30, y0 + 115, 30, 'sans_med', WHITE, c, 'l', t0=t0 + 0.2, stag=0.02)
        g = env(t, 247.6, 251.9, 0.4, 0.4)
        f.text('→ 在规模很大时，仍保留一部分区分感，延长「最佳区间」', W / 2, 260, 32, 'sans_med', GOLD2, g, t0=247.6, stag=0.02)
        f.text('（解释性假设，不能证明企业这样设计就是为了阶层区分）', W / 2, 930, 22, 'sans_light', GREY, g, t0=248.4, stag=0.01)

# ---------------------------------------------------------------- 06a 五个条件 252–270
COND = [('可识别', CYAN, '外人能认出这个品牌，', '以及它代表的社会信号'),
        ('有地位溢价', GOLD, '在特定群体里，用了它，', '自觉获得了更高的社会评价'),
        ('有适度门槛', MAGENTA, '价格或会员资格形成区分，', '但不像顶级奢侈品只服务极少数人'),
        ('有社会传播', TEAL, '目标人群在用，', '会让更多人想要拥有它'),
        ('能兑现经济利润', ORANGE, '更高支付意愿 · 稳定复购 · 会员留存', '定价权 · 资本回报率')]

def sc_conditions(f, t):
    if not (252 < t < 270.2): return
    a = env(t, 252.1, 269.9, 0.4, 0.3)
    f.text('一家公司要算「大众地位象征型护城河」，至少满足五个条件', W / 2, 135, 42, 'serif_black', WHITE, a, t0=252.2, stag=0.03,
           glow=0.2)
    cx, cy, R = 600, 590, 300
    V = [(cx + R * math.cos(-math.pi / 2 + k * 2 * math.pi / 5), cy + R * math.sin(-math.pi / 2 + k * 2 * math.pi / 5))
         for k in range(5)]
    ts = [253.0 + 2.8 * k for k in range(5)]
    cur = max([k for k in range(5) if t >= ts[k]], default=-1)
    allp = eo((t - 267.0) / 0.6)
    for k in range(5):
        p = eo((t - ts[k]) / 0.6)
        if p <= 0: continue
        nxt = (k + 1) % 5
        if t >= ts[nxt] or (k == 4 and allp > 0):
            q = eo((t - (ts[nxt] if k < 4 else 267.0)) / 0.5)
            e = (V[k][0] + (V[nxt][0] - V[k][0]) * q, V[k][1] + (V[nxt][1] - V[k][1]) * q)
            f.line(V[k], e, lerpc(COND[k][1], COND[nxt][1], 0.5), a * 0.8, 3)
        f.line((cx, cy), V[k], COND[k][1], a * p * 0.25, 1)
    if allp > 0:
        f.fillpoly(V, GOLD, a * allp * 0.08 * (1 + bar_pulse(t)))
    for k in range(5):
        p = eo((t - ts[k]) / 0.6)
        if p <= 0: continue
        col = COND[k][1]
        on = 1.0 if k == cur else 0.55
        if allp > 0: on = 1.6 if k == 4 else 0.7
        r = 26 * (1 + 0.5 * (1 - eback(cl((t - ts[k]) / 0.6), 2)))
        f.circle(V[k], r, col, a * p, 3)
        f.glow(V[k], 9, WHITE, a * p * on, 'E'); f.glow(V[k], 34 * on, col, a * p * 0.6 * on, 'B')
        f.text(str(k + 1), V[k][0], V[k][1] + 2, 28, 'bebas', WHITE, a * p, mode='L')
        lx = V[k][0] + (0 if k == 0 else 60 if V[k][0] > cx else -60)
        ly = V[k][1] + (-60 if k == 0 else 50 if k in (2, 3) else 0)
        f.text(COND[k][0], lx, ly, 32, 'serif_black', lerpc(col, WHITE, .3), a * p * min(on, 1),
               'm' if k == 0 or k in (2, 3) else ('l' if V[k][0] > cx else 'r'), mode='L', glow=0.3)
        if 0 < t - ts[k] < 0.8: ripple(f, t, ts[k], V[k][0], V[k][1], col, a, 2, 120, 0.8)
    # right panel: current item
    if 0 <= cur and allp < 1:
        k = cur
        pa = a * env(t, ts[k], ts[k + 1] if k < 4 else 267.0, 0.3, 0.25)
        col = COND[k][1]
        f.text(f'0{k + 1}', 1170, 420, 120, 'bebas', col, pa, 'l', mode='L', glow=0.5)
        f.text(COND[k][0], 1310, 405, 60, 'serif_black', WHITE, pa, 'l', t0=ts[k], stag=0.05, glow=0.3)
        f.text(COND[k][2], 1172, 560, 34, 'sans_med', WHITE, pa, 'l', t0=ts[k] + 0.3, stag=0.025)
        f.text(COND[k][3], 1172, 616, 34, 'sans_med', lerpc(col, WHITE, .4), pa, 'l', t0=ts[k] + 0.8, stag=0.025)
    e = env(t, 267.0, 269.9, 0.3, 0.3)
    f.text('第五条，最重要', 1170, 450, 70, 'serif_black', ORANGE, e, 'l', t0=267.0, stag=0.08, mode='L', glow=0.5)
    f.text('身份感要能变成钱，', 1172, 560, 34, 'sans_med', WHITE, e, 'l', t0=267.8, stag=0.03)
    f.text('并且留在股东手里', 1172, 612, 34, 'sans_med', GOLD2, e, 'l', t0=268.4, stag=0.03)

# ---------------------------------------------------------------- 06b 经济利润 270–290
_GR = np.random.default_rng(88)
NET = _GR.uniform(0, 1, (220, 2)); NET_T = np.sort(_GR.uniform(0, 1, 220))

def sc_econ(f, t):
    if not (270 < t < 290.2): return
    a = env(t, 270.0, 289.6, 0.1, 0.3)
    f.text('认同 ≠ 护城河：关键看能否赚到「经济利润」', W / 2, 135, 46, 'serif_black', WHITE, a, t0=270.1, stag=0.03, glow=0.25)
    panels = [(150, RED, 'A · 补贴买来的认同', lambda u: 0.15 + 0.8 * u ** 2.2, '获客成本 ↑', 271.0),
              (1010, GOLD, 'B · 口碑带来的认同', lambda u: 0.75 * math.exp(-2.4 * u) + 0.12, '获客成本 ↓', 272.6)]
    for (x0, col, title, fn, tag, t0) in panels:
        pa = a * eo((t - t0) / 0.5)
        if pa <= 0: continue
        w, y0, h = 760, 300, 330
        f.rrect(x0 - 20, 210, x0 + w + 20, 820, 26, col, pa * 0.45, 2)
        f.text(title, x0 + w / 2, 255, 40, 'serif_black', lerpc(col, WHITE, .3), pa, mode='L', glow=0.3)
        f.line((x0 + 40, y0 + h), (x0 + w - 20, y0 + h), GREY, pa * 0.6, 2)
        f.line((x0 + 40, y0 + h), (x0 + 40, y0 + 10), GREY, pa * 0.6, 2)
        f.text('用户规模 →', x0 + w - 20, y0 + h + 28, 22, 'sans_light', GREY, pa, 'r')
        f.text('每新增一位用户的成本', x0 + 52, y0 + 4, 22, 'sans_light', GREY, pa, 'l')
        dp = eo((t - t0 - 0.4) / 2.5)
        us = np.linspace(0, dp, 60)
        pts = [(x0 + 40 + u * (w - 70), y0 + h - fn(u) * (h - 30)) for u in us]
        if dp > 0.02:
            f.poly(pts, col, pa, 4)
            f.glow(pts[-1], 14, col, pa, 'B'); f.glow(pts[-1], 4, WHITE, pa, 'E')
        if dp > 0.95:
            f.text(tag, pts[-1][0] - 10, pts[-1][1] + (-36 if col == RED else -40), 30, 'sans_black', col, pa, 'r', mode='L',
                   glow=0.4)
        # users visual under the chart
        k = int(220 * dp)
        xs = x0 + 60 + NET[:k, 0] * (w - 100); ys = 700 + NET[:k, 1] * 90
        if col == RED:
            f.dots(xs, ys, SILVER, pa * 0.5, 1, 'E')
            for j in range(0, k, 9):   # coins needed per user
                cy_ = ys[j] - 30 * ((t * 1.5 + j * 0.13) % 1.0)
                f.text('¥', xs[j], cy_, 18, 'sans_black', RED, pa * 0.7, mode='L')
        else:
            f.dots(xs, ys, GOLD2, pa * 0.55, 1, 'E')
            for j in range(1, k, 3):
                i2 = int(j * 0.6)
                f.line((xs[j], ys[j]), (xs[i2], ys[i2]), GOLD, pa * 0.12, 1)
    c = env(t, 276.4, 289.6, 0.3, 0.3)
    f.text('用户越多，花得越多 → 股东回报薄', 150 + 380, 860, 30, 'sans_med', lerpc(RED, WHITE, .4), c, t0=276.4, stag=0.025)
    f.text('用户带来用户，还愿付溢价 → 高质量护城河', 1010 + 380, 860, 30, 'sans_med', GOLD2, c, t0=277.6, stag=0.025)
    d = env(t, 280.6, 289.6, 0.3, 0.3)
    f.text('最终都要落到：', 420, 950, 30, 'sans_light', WHITE, d, 'r', t0=280.6)
    x = 450
    for k, (s_, col) in enumerate((('定价权', GOLD), ('复购率', CYAN), ('会员留存', TEAL), ('资本回报率 ROIC', ORANGE))):
        q = d * eo((t - 281.2 - k * 0.5) / 0.4)
        x += chip(f, s_, x, 950, 30, col, q, 'serif_black', anchor='l') + 24


# ---------------------------------------------------------------- 07 隐形测试 290–312
def spotlight(f, cx, top, bottom, w0, w1, col, a):
    if a <= 0.003: return
    for k in range(8):
        y0 = top + (bottom - top) * k / 8; y1 = top + (bottom - top) * (k + 1) / 8
        ww0 = lerp(w0, w1, k / 8); ww1 = lerp(w0, w1, (k + 1) / 8)
        f.fillpoly([(cx - ww0, y0), (cx + ww0, y0), (cx + ww1, y1), (cx - ww1, y1)], col, a * 0.05 * (0.4 + 0.6 * k / 8), 'L')
    f.glow((cx, bottom), w1 * 0.7, col, a * 0.18, 'B')

def sc_invisible_test(f, t):
    if not (290 < t < 312.2): return
    a = env(t, 290.1, 311.9, 0.6, 0.2)
    q0 = env(t, 290.4, 293.8, 0.6, 0.4)
    f.text('最后，一个能拆穿一切的问题', W / 2, 540, 50, 'serif_med', lerpc(GREY, WHITE, .6), q0, t0=290.5, stag=0.08, dur=0.7)
    q1 = env(t, 294.0, 301.0, 0.5, 0.4)
    spotlight(f, W / 2, 0, 900, 60, 420, WHITE, q1 * (0.7 + 0.3 * math.sin(t * 2.0) ** 2))
    f.text('如果你使用这个品牌时，', W / 2, 400, 52, 'serif_med', WHITE, q1, t0=294.1, stag=0.06)
    f.text('没有任何人知道——', W / 2, 480, 52, 'serif_med', WHITE, q1 * eo((t - 295.4) / 0.4), t0=295.4, stag=0.07)
    f.text('你还愿意，多付同样多的钱吗？', W / 2, 640, 84, 'serif_black', GOLD2, q1 * eo((t - 297.0) / 0.4), t0=297.0,
           stag=0.09, dur=0.6, mode='E', glow=0.7)
    s = env(t, 301.0, 311.9, 0.4, 0.3)
    if s > 0:
        off = eio((t - 303.0) / 1.0)
        f.text('把「被看见」拿掉，看溢价还剩多少', W / 2, 150, 46, 'serif_black', WHITE, s, t0=301.1, stag=0.04, glow=0.3)
        for k, (cx, keep, col, l1, l2) in enumerate(((560, 0.25, MAGENTA, '溢价大幅下降', '→ 地位信号是品牌价值的核心'),
                                                    (1360, 0.92, CYAN, '几乎不变', '→ 消费者更看重质量与体验'))):
            spotlight(f, cx, 210, 760, 40, 230, GOLD2, s * (1 - 0.85 * off))
            icon_person(f, cx - 90, 640, 90, lerpc(SILVER, GOLD2, 1 - off), s * (0.9 - 0.4 * off), fill=0.06)
            f.text('有人看见' if off < 0.5 else '无人看见', cx - 90, 790, 26, 'sans_light', GOLD2 if off < 0.5 else GREY, s)
            v = 1 - (1 - keep) * eio((t - 303.4) / 1.6)
            bx, by, bh = cx + 90, 760, 400
            f.rrect(bx - 32, by - bh, bx + 32, by, 10, col, s * 0.3, 1)
            f.rrect_fill(bx - 32, by - bh * v, bx + 32, by, 10, col, s * 0.35, 'L')
            f.rrect(bx - 32, by - bh * v, bx + 32, by, 10, col, s, 2)
            f.glow((bx, by - bh * v), 18, col, s * 0.7, 'B')
            f.text(f'{v * 100:.0f}%', bx, by - bh * v - 34, 48, 'bebas', lerpc(col, WHITE, .3), s, mode='L', glow=0.3)
            f.text('愿付溢价', bx, by + 30, 24, 'sans_light', GREY, s)
            r = s * eo((t - 305.2 - k * 0.6) / 0.4)
            f.text(l1, cx, 860, 40, 'serif_black', lerpc(col, WHITE, .3), r, t0=305.2 + k * 0.6, stag=0.05, mode='E', glow=0.4)
            f.text(l2, cx, 915, 28, 'sans_med', WHITE, r, t0=305.6 + k * 0.6, stag=0.025)
        g = env(t, 307.4, 311.9, 0.3, 0.2)
        f.text('可通过盲测、不同使用可见度下的支付意愿实验来验证', W / 2, 975, 22, 'sans_light', GREY, g, t0=307.4, stag=0.01)
    implode(f, t, 309.4, 312.0, W / 2, H / 2, [GOLD, GOLD2, MAGENTA, CYAN, WHITE, ORANGE], 0.9)

# ---------------------------------------------------------------- 08a 三角张力 312–328
TRI = [((960, 300), GOLD, '社会认可', '「拥有它，别人会高看我」'),
       ((540, 820), CYAN, '大众可及', '「足够多的人买得起」'),
       ((1380, 820), MAGENTA, '身份区分', '「普及之后，优越感不消失」')]

def string(f, p0, p1, col, a, t, amp, ph):
    pts = []
    for u in np.linspace(0, 1, 40):
        x = lerp(p0[0], p1[0], u); y = lerp(p0[1], p1[1], u)
        nx, ny = -(p1[1] - p0[1]), p1[0] - p0[0]
        L = math.hypot(nx, ny); nx, ny = nx / L, ny / L
        d = amp * math.sin(u * math.pi) * math.sin(t * 9 + ph)
        pts.append((x + nx * d, y + ny * d))
    f.poly(pts, col, a, 3)
    for k in range(3):
        u = (t * 0.4 + k / 3 + ph) % 1.0
        f.glow(pts[int(u * 39)], 4, WHITE, a, 'E')

def sc_triangle(f, t):
    if not (311.9 < t < 328.3): return
    a = env(t, 312.0, 327.9, 0.1, 0.4)
    burst(f, t, 312.0, W / 2, 600, [GOLD, GOLD2, CYAN, MAGENTA, WHITE, ORANGE], 3, 900, 1700, 1.3, 2.2, 1.0, 2)
    f.text('终极命题', W / 2, 170, 30, 'sans_light', GREY, a, track=0.5, t0=312.2)
    ts = [312.6, 314.2, 315.8]
    tension = env(t, 317.6, 323.6, 0.5, 0.8)
    for k in range(3):
        p0, c0 = TRI[k][0], TRI[k][1]; p1, c1 = TRI[(k + 1) % 3][0], TRI[(k + 1) % 3][1]
        q = eo((t - ts[(k + 1) % 3]) / 0.6) if k < 2 else eo((t - 317.0) / 0.6)
        if q > 0:
            e = (lerp(p0[0], p1[0], q), lerp(p0[1], p1[1], q))
            string(f, p0, e, lerpc(c0, c1, 0.5), a * 0.8, t, 4 + 14 * tension, k * 1.7)
    # the ball
    cen = (sum(p[0] for p, *_ in TRI) / 3, sum(p[1] for p, *_ in TRI) / 3)
    bp = env(t, 316.6, 327.9, 0.4, 0.4)
    if bp > 0:
        tug = (t - 317.6)
        k = int(tug / 1.5) % 3 if 317.6 < t < 323.6 else -1
        tgt = TRI[k][0] if k >= 0 else cen
        w = 0.35 * math.sin(min(max(tug % 1.5, 0), 1.5) / 1.5 * math.pi) if k >= 0 else 0
        settle = eo((t - 323.6) / 1.2)
        bx = lerp(cen[0], tgt[0], w) + 10 * math.sin(t * 5) * (1 - settle)
        by = lerp(cen[1], tgt[1], w) + 8 * math.cos(t * 6) * (1 - settle)
        for j in range(3):
            f.line((bx, by), TRI[j][0], TRI[j][1], a * bp * 0.22, 1)
        r = 22 + 18 * settle + 5 * beat_pulse(t)
        f.glow((bx, by), r * 0.5, WHITE, a * bp, 'E')
        f.glow((bx, by), r * 1.8, lerpc(GOLD, WHITE, 0.2), a * bp * (0.35 + 0.2 * settle), 'B')
        f.circle((bx, by), r, GOLD2, a * bp, 2)
        if settle > 0:
            ripple(f, t, 323.6, bx, by, GOLD2, a, 3, 380, 1.4)
            moat(f, t, bx, by, 150 * settle, 60 * settle, a * settle * 0.8, 600)
    for k, (p, col, title, quote) in enumerate(TRI):
        q = eo((t - ts[k]) / 0.5)
        if q <= 0: continue
        f.circle(p, 18, col, a * q, 3); f.glow(p, 6, WHITE, a * q, 'E'); f.glow(p, 40, col, a * q * 0.6, 'B')
        if 0 < t - ts[k] < 0.8: ripple(f, t, ts[k], p[0], p[1], col, a, 2, 140, 0.8)
        if k == 0:
            f.text(title, p[0] + 50, p[1] - 22, 46, 'serif_black', lerpc(col, WHITE, .3), a * q, 'l', mode='E', glow=0.4)
            f.text(quote, p[0] + 52, p[1] + 30, 28, 'sans_med', WHITE, a * q, 'l', t0=ts[k] + 0.2, stag=0.02)
        else:
            al = 'r' if k == 1 else 'l'
            dx = -40 if k == 1 else 40
            f.text(title, p[0] + dx, p[1] - 22, 46, 'serif_black', lerpc(col, WHITE, .3), a * q, al, mode='E', glow=0.4)
            f.text(quote, p[0] + dx, p[1] + 30, 28, 'sans_med', WHITE, a * q, al, t0=ts[k] + 0.2, stag=0.02)
    c = env(t, 318.0, 323.4, 0.3, 0.4)
    f.text('三个条件之间，存在天然的矛盾', W / 2, 920, 46, 'serif_black', WHITE, c, t0=318.0, stag=0.05, glow=0.3)
    d = env(t, 323.6, 327.9, 0.3, 0.4)
    f.dim(260, 880, 1660, 1000, 0.6 * d, 26)
    f.text('能长期管理好这三者关系的企业，', W / 2, 912, 38, 'serif_med', WHITE, d, t0=323.6, stag=0.04)
    f.text('才拥有真正的身份象征型护城河', W / 2, 968, 44, 'serif_black', GOLD2, d * eo((t - 324.8) / 0.4), t0=324.8,
           stag=0.05, mode='E', glow=0.6)

# ---------------------------------------------------------------- 08b 最高境界 328–344
_HR = np.random.default_rng(99)
HALO_T = _HR.uniform(0, 2 * math.pi, 600); HALO_R = _HR.uniform(0.85, 1.15, 600)

def sc_highest(f, t):
    if not (328 < t < 344.2): return
    a = env(t, 328.1, 343.9, 0.4, 0.4)
    f.text('品牌的最高境界', W / 2, 150, 56, 'serif_black', WHITE, a, t0=328.2, stag=0.06, glow=0.3)
    m = eio((t - 333.0) / 1.4)
    px, py = W / 2, 560
    # brand ring: starts outside, flies into the person
    rx = lerp(1340, px, m); ry = lerp(470, py + 10, m); rr = lerp(80, 175, m)
    th = HALO_T + t * 0.6
    xs = rx + rr * HALO_R * np.cos(th); ys = ry + rr * HALO_R * np.sin(th) * lerp(1, 0.9, m)
    f.splat(xs, ys, np.array(lerpc(GOLD2, GOLD, m)), a * 1.4 * eo((t - 328.6) / 0.6), 'E')
    f.circle((rx, ry), rr, GOLD, a * 0.6 * eo((t - 328.6) / 0.6), 2)
    f.text('品牌', rx, ry, int(lerp(34, 1, m)) if m < 0.95 else 1, 'serif_black', GOLD2, a * (1 - m), mode='L')
    icon_person(f, px, py, 150, lerpc(SILVER, GOLD2, m), a * eo((t - 328.4) / 0.6), fill=0.06 + 0.12 * m)
    if m > 0:
        f.glow((px, py), 160, GOLD, a * m * 0.35 * (1 + 0.5 * bar_pulse(t)), 'B')
        if 334.2 < t < 336: ripple(f, t, 334.3, px, py, GOLD2, a, 3, 520, 1.3)
    s1 = a * env(t, 329.4, 334.0, 0.3, 0.4)
    f.text('「我拥有这个品牌」', W / 2, 820, 60, 'serif_med', lerpc(GREY, WHITE, .5), s1, t0=329.4, stag=0.06)
    s2 = a * env(t, 334.2, 343.9, 0.3, 0.4)
    f.text('「这个品牌代表我」', W / 2, 820, 76, 'serif_black', GOLD2, s2, t0=334.2, stag=0.08, mode='E', glow=0.7)
    s3 = a * env(t, 336.8, 340.8, 0.3, 0.4)
    f.text('当产品成为一个人自我认同的一部分，竞争者要改变的', W / 2, 920, 32, 'sans_med', WHITE, s3, t0=336.8, stag=0.02)
    f.text('就不只是产品选择——而是消费者对自己的理解', W / 2, 970, 32, 'sans_med', lerpc(GOLD2, WHITE, .3), s3, t0=338.0, stag=0.02)
    s4 = a * env(t, 340.8, 343.9, 0.3, 0.4)
    f.dim(400, 880, 1520, 1000, 0.6 * s4, 26)
    f.text('这是价格战无法复制的优势', W / 2, 940, 54, 'serif_black', WHITE, s4, t0=340.8, stag=0.07, mode='E', glow=0.5,
           grad=[GOLD2, WHITE, GOLD2])

# ---------------------------------------------------------------- 终章 五条教训 344–364
LESSONS = [('人买的不只是商品，更是「我是谁」', CYAN),
           ('身份溢价 ≠ 高利润：要看能否留住经济收益', ORANGE),
           ('普及是双刃剑：先增强，后削弱', MAGENTA),
           ('隐形测试：没人看见时，溢价还剩多少？', VIOLET),
           ('最好的品牌，不是「我拥有它」，而是「它代表我」', GOLD)]

def sc_lessons(f, t):
    if not (344 < t < 364.2): return
    a = env(t, 344.1, 363.6, 0.5, 0.6)
    flow(f, t, a * 0.35, [GOLD, GOLD2, ORANGE, CYAN, GOLD, WHITE], 60, n=1200, rise=1.0)
    f.text('看完，记住这五句话', W / 2, 150, 50, 'serif_black', WHITE, a, t0=344.2, stag=0.06, glow=0.3)
    ts = [345.0, 348.0, 351.0, 354.0, 357.0]
    allon = eo((t - 360.0) / 0.6)
    for i, ((s, col), t0) in enumerate(zip(LESSONS, ts)):
        p = eo((t - t0) / 0.5)
        if p <= 0: continue
        nxt = ts[i + 1] if i < 4 else 999
        dim_ = 1 - 0.45 * eo((t - nxt) / 0.5)
        dim_ = lerp(dim_, 1.0 if i == 4 else 0.8, allon)
        y = 300 + i * 125
        x0 = 330
        f.text(f'0{i + 1}', x0, y, 64, 'bebas', col, a * p * dim_, 'l', mode='E', glow=0.5 * dim_)
        f.line((x0 + 78, y - 26), (x0 + 78, y + 26), col, a * p * dim_ * 0.6, 2)
        sz = 50 if i == 4 else 46
        f.text(s, x0 + 104, y, sz, 'serif_black', lerpc(col, WHITE, 0.55 if i < 4 else 0.25), a * p * dim_, 'l', t0=t0,
               stag=0.035, glow=0.3 * dim_, mode='E' if i == 4 else 'L')
        if 0 < t - t0 < 0.7:
            burst(f, t, t0, x0 + 30, y, [col, WHITE], 5, 150, 380, 0.5, 3.5, 0.8)
    if allon > 0:
        f.glow((W / 2, 300 + 4 * 125), 420, GOLD, a * allon * 0.12 * (1 + bar_pulse(t)), 'B')

# ---------------------------------------------------------------- 片尾 364–376
def sc_end(f, t):
    if t < 363.8: return
    e = env(t, 364.0, 377, 0.8, 0.1)
    rgb, m = END_LOGO
    hgt = m.shape[0]
    X0, Y0 = int(W / 2 - hgt / 2), int(390 - hgt / 2)
    sc = eo((t - 364.0) / 1.0)
    f.over.append((m, X0, Y0, rgb, e * sc))
    f.glow((W / 2, 390), 150, C(110, 175, 255), e * 0.22, 'B')
    f.text('巴芒价值', W / 2, 620, 112, 'serif_black', GOLD2, e, t0=364.3, stag=0.12, dur=0.6,
           grad=[GOLD2, GOLD, GOLDD], mode='O', glow=.5)
    f.text('BUFFETT · MUNGER', W / 2, 712, 30, 'corm', C(214, 178, 112), e, track=0.46, t0=364.9, stag=0.03, mode='O')
    f.text('看懂人心，才看得懂护城河', W / 2, 810, 34, 'sans_light', lerpc(GREY, WHITE, .5), e, track=0.25, t0=365.6, stag=0.06)
    burst(f, t, 364.2, W / 2, 390, [C(110, 175, 255), CYAN, GOLD2, WHITE], 7, 500, 900, 1.6, 1.6, 0.8)
    flow(f, t, e * 0.25, [GOLD, GOLD2, ORANGE, GOLD, GOLD2, WHITE], 40, n=800, rise=1.2)


SCENES = [sc_prologue, sc_title, sc_questions, sc_social, sc_invisible, sc_peacock, sc_price, sc_forces, sc_formula,
          sc_veblen, sc_luxury, sc_margin, sc_apple, sc_sam, sc_scatter, sc_paradox, sc_conditions, sc_econ,
          sc_invisible_test, sc_triangle, sc_highest, sc_lessons, sc_end]

def render(i):
    t = i / FPS
    f = Frame(t)
    bg = bg_at(t)
    draw_stars(f, t, 1.0 if not (290 < t < 311) else 0.4)
    for s in SCENES:
        s(f, t)
    shockwaves(f, t)
    if 190.0 <= t < 190.6:
        k = math.exp(-(t - 190.0) / 0.12)
        f.shake = (int(round(7 * k * math.sin(t * 90))), int(round(9 * k * math.cos(t * 77))))
    draw_chrome(f, t)
    img = finish(f, bg, bloom_k=1.0 + 0.3 * beat_pulse(t), vignette=VIGNETTE)
    draw_hud_post(img, t, env(t, 0.4, 363.8, 1.0, 0.6))
    fade = cl(t / 1.0) * (1 - eio((t - 374.4) / 1.6))
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
            cv2.imwrite(os.path.join(out, 'f_%07.2f.png' % float(tt)), img[..., ::-1])
    elif mode == 'chunk':
        a, b, path = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
                              '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                              '-pix_fmt', 'yuv420p', '-tune', 'animation', path], stdin=subprocess.PIPE)
        for i in range(a, b):
            p.stdin.write(render(i).tobytes())
            if (i - a) % 300 == 0: print(path, i, flush=True)
        p.stdin.close(); p.wait()
