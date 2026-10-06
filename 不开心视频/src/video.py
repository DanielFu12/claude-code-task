"""人为什么会感到不开心 —— 3-minute motion-graphics film synced to the BGM."""
import math, os, sys
import numpy as np, cv2
from PIL import Image, ImageDraw
from engine import *

DUR = 180.0
NFR = int(DUR * FPS)
BEATS = np.load(os.path.join(HERE, 'beats180.npy'))

# ============================================================== music structure
IMPACTS = [  # time, strength, colour
    (18.18, 1.0, MAGENTA), (35.19, 0.35, RED), (56.44, 0.75, VIOLET), (103.20, 1.0, GOLD),
    (110.60, 0.30, RED), (149.97, 1.0, TEAL), (152.09, 0.55, CYAN)]
RISERS = [(16.07, 18.18), (101.09, 103.20), (147.85, 149.97)]
ENERGY = [(0, .5), (9.6, .5), (9.8, .25), (16.0, .3), (18.18, 1), (86.0, 1), (86.3, .6), (96.7, .6),
          (96.9, .2), (101.0, .2), (103.2, 1), (132.9, 1), (133.1, .6), (143.5, .6), (143.7, .2),
          (147.8, .2), (149.97, 1), (171.0, 1), (172.0, .45), (180, .3)]

def energy(t):
    return keys(t, ENERGY)

def beat_dt(t):
    i = np.searchsorted(BEATS, t, 'right') - 1
    return t - BEATS[i] if i >= 0 else 9.0

def beat_pulse(t, decay=0.13):
    return math.exp(-beat_dt(t) / decay)

def bar_pulse(t, decay=0.25):
    i = np.searchsorted(BEATS, t, 'right') - 1
    if i < 0: return 0.0
    j = i - (i % 4)
    return math.exp(-(t - BEATS[j]) / decay)

# ============================================================== static precompute
RNG = np.random.default_rng(1234)
NST = 1300
ST_X = RNG.uniform(-1.8, 1.8, NST); ST_Y = RNG.uniform(-1.1, 1.1, NST); ST_Z0 = RNG.uniform(0, 1, NST)
ST_COL = np.array([lerpc(WHITE, [CYAN, VIOLET, WHITE, GOLD2, PINK][i % 5], 0.4) for i in range(NST)], np.float32)

def star_speed(t):
    v = 0.035
    for ti, k, _ in IMPACTS:
        if t >= ti: v += k * 1.5 * math.exp(-(t - ti) / 0.55)
    for a, b in RISERS:
        if a <= t <= b: v += 0.35 * ei((t - a) / (b - a))
    return v

_ts = np.arange(NFR + 2) / FPS
ST_S = np.concatenate([[0], np.cumsum([star_speed(x) / FPS for x in _ts])])

def star_dist(t):
    i = min(int(t * FPS), NFR)
    return ST_S[i]

# nebula fields
NB1 = fbm(512, 288, 11, 6, 3); NB2 = fbm(512, 288, 22, 6, 3); NB3 = fbm(512, 288, 33, 5, 5)
BGK = [
    (0, (10, 22, 75), (40, 12, 70), .9), (9.6, (10, 22, 75), (40, 12, 70), .75), (16, (30, 10, 60), (60, 10, 80), .6),
    (18.2, (110, 25, 160), (20, 70, 180), 1.35), (24, (25, 55, 130), (70, 25, 130), 1.0),
    (35.0, (25, 55, 130), (70, 25, 130), 1.0), (35.4, (140, 15, 45), (70, 10, 60), 1.2), (39, (110, 15, 40), (60, 10, 60), .9),
    (40.2, (15, 70, 100), (55, 20, 120), 1.0), (56.2, (15, 70, 100), (55, 20, 120), 1.0),
    (56.6, (140, 25, 140), (45, 25, 170), 1.3), (73, (90, 25, 120), (30, 25, 130), 1.0),
    (74, (22, 45, 100), (55, 22, 90), .95), (96.5, (22, 35, 80), (45, 22, 70), .75),
    (98, (10, 10, 30), (22, 10, 40), .45), (103.0, (12, 10, 30), (22, 10, 40), .5),
    (103.4, (170, 100, 20), (130, 45, 20), 1.35), (107, (120, 75, 22), (95, 32, 30), .95),
    (116, (45, 45, 120), (95, 55, 30), .9), (132.8, (45, 45, 120), (95, 55, 30), .9),
    (133.4, (10, 90, 100), (22, 45, 110), .95), (143.4, (22, 45, 100), (55, 22, 100), .75),
    (144, (35, 28, 55), (60, 45, 20), .65), (149.8, (35, 28, 55), (60, 45, 20), .65),
    (150.2, (10, 140, 125), (125, 30, 170), 1.35), (156.3, (20, 110, 130), (100, 45, 160), 1.15),
    (164.8, (70, 45, 130), (120, 85, 30), 1.0), (171.2, (100, 65, 22), (45, 22, 65), .9),
    (180, (30, 20, 10), (20, 10, 30), .4)]

def bg_at(t):
    a = keys(t, [(k[0], k[1]) for k in BGK]); b = keys(t, [(k[0], k[2]) for k in BGK])
    I = keys(t, [(k[0], k[3]) for k in BGK])
    I *= 1 + 0.18 * beat_pulse(t, 0.2) * energy(t)
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

# ---------------------------------------------------------------- logo / HUD
def gold_ramp(h):
    y = np.linspace(0, 1, h)[:, None]
    stops = [(0, (255, 243, 200)), (0.35, (255, 212, 120)), (0.62, (226, 160, 60)), (1, (255, 214, 130))]
    out = np.zeros((h, 3), np.float32)
    for c in range(3):
        out[:, c] = np.interp(y[:, 0], [s[0] for s in stops], [s[1][c] for s in stops]) / 255
    return out

def make_emblem(size):
    S = size * 4
    im = Image.new('L', (S, S), 0); d = ImageDraw.Draw(im)
    u = lambda v: v * S
    # outer + inner ring
    d.ellipse([u(.04), u(.04), u(.96), u(.96)], outline=255, width=int(u(.055)))
    d.ellipse([u(.13), u(.13), u(.87), u(.87)], outline=255, width=int(u(.018)))
    cx, hy = .5, .60
    # rising sun + rays (芒)
    d.pieslice([u(cx - .15), u(hy - .15), u(cx + .15), u(hy + .15)], 180, 360, fill=255)
    for k in range(7):
        ang = math.radians(-165 + k * 25)
        r0, r1 = .2, (.34 if k % 2 == 0 else .30)
        d.line([u(cx + r0 * math.cos(ang)), u(hy + r0 * math.sin(ang)),
                u(cx + r1 * math.cos(ang)), u(hy + r1 * math.sin(ang))], fill=255, width=int(u(.035)))
    # horizon + reflections (steady value)
    d.line([u(.17), u(hy), u(.83), u(hy)], fill=255, width=int(u(.035)))
    d.line([u(.30), u(hy + .09), u(.70), u(hy + .09)], fill=255, width=int(u(.026)))
    d.line([u(.39), u(hy + .17), u(.61), u(hy + .17)], fill=255, width=int(u(.022)))
    im = im.resize((size, size), Image.LANCZOS)
    m = np.asarray(im, np.float32) / 255
    rgb = np.repeat(gold_ramp(size)[:, None, :], size, 1)
    return m, rgb

def load_logo(size):
    p = os.environ.get('LOGO_PATH')
    if p and os.path.exists(p):
        im = Image.open(p).convert('RGBA')
        im.thumbnail((size * 3, size), Image.LANCZOS)
        a = np.asarray(im, np.float32) / 255
        return a[..., 3], a[..., :3]
    return make_emblem(size)

def make_hud():
    lh = 66
    lm, lrgb = load_logo(lh)
    f = font('serif_black', 42)
    tw = int(f.getlength('巴芒价值')) + 8
    asc, desc = f.getmetrics()
    th = asc + desc
    tim = Image.new('L', (tw, th), 0)
    ImageDraw.Draw(tim).text((2, asc), '巴芒价值', font=f, fill=255, anchor='ls')
    tm = np.asarray(tim, np.float32) / 255
    # crop text vertically to ink
    rows = np.where(tm.max(1) > 0.02)[0]; tm = tm[rows[0]:rows[-1] + 1]
    gap = 16
    hh = max(lm.shape[0], tm.shape[0]) + 12
    ww = lm.shape[1] + gap + tm.shape[1] + 12
    A = np.zeros((hh, ww), np.float32); RGB = np.zeros((hh, ww, 3), np.float32)
    oy = (hh - lm.shape[0]) // 2
    A[oy:oy + lm.shape[0], 6:6 + lm.shape[1]] = lm
    RGB[oy:oy + lm.shape[0], 6:6 + lm.shape[1]] = lrgb
    ty = (hh - tm.shape[0]) // 2 + 1
    x0 = 6 + lm.shape[1] + gap
    A[ty:ty + tm.shape[0], x0:x0 + tm.shape[1]] = tm
    RGB[ty:ty + tm.shape[0], x0:x0 + tm.shape[1]] = gold_ramp(tm.shape[0])[:, None, :]
    shadow = cv2.GaussianBlur(A, (0, 0), 6) * 0.75
    return A, RGB, shadow

HUD_A, HUD_RGB, HUD_SH = make_hud()
END_EMB = make_emblem(210)

def draw_hud(f, t, a):
    if a <= 0.003: return
    h, w = HUD_A.shape
    X0, Y0 = W - w - 52, 34
    # shimmer sweep every 7 s
    ph = ((t + 2.0) % 7.0) / 1.4
    rgb = HUD_RGB
    if ph < 1.0:
        xs = np.arange(w)[None, :] + np.arange(h)[:, None] * 0.6
        band = np.exp(-((xs - (-60 + ph * (w + 120))) / 22.0) ** 2)[..., None]
        rgb = np.clip(HUD_RGB + band * 0.55, 0, 1.3)
    f.over.append((HUD_SH, X0, Y0, np.zeros(3, np.float32), a * 0.8))
    f.over.append((HUD_A, X0, Y0, rgb, a))
    f.B[Y0:Y0 + h, X0:X0 + w] += (HUD_A * a * 0.22)[..., None] * rgb

CHAPTERS = [(0, '序', '序章', 'PROLOGUE'), (18.18, '01', '第一性原理', 'FIRST PRINCIPLES'),
            (56.44, '02', '不开心公式', 'THE FORMULA'), (73.44, '03', '三种不如愿', 'THREE CASES'),
            (96.83, '04', '三层修炼', 'THE PRACTICE'), (149.97, '05', '幸福公式', 'THE ANSWER'),
            (171.22, '终', '终章', 'EPILOGUE'), (180, '', '', '')]

def draw_chrome(f, t):
    hud_a = env(t, 0.4, 175.6, 1.0, 0.6)
    draw_hud(f, t, hud_a)
    # chapter label (top-left)
    for (a, num, zh, en), (b, *_r) in zip(CHAPTERS, CHAPTERS[1:]):
        if a <= t < b:
            al = env(t, a, b, 0.6, 0.4) * 0.9 * env(t, 0.8, 175.4, 0.8, 0.5)
            f.text(num, 70, 62, 30, 'orb' if num.isdigit() else 'serif_black', GOLD, al, 'l', mode='O')
            x = 70 + text_width(num, 'orb' if num.isdigit() else 'serif_black', 30) + 16
            f.line((x, 50), (x, 76), GOLD, al * 0.6, 1)
            f.text(zh, x + 16, 56, 24, 'sans_med', WHITE, al * 0.92, 'l', mode='O')
            f.text(en, x + 16, 84, 14, 'corm', GREY, al * 0.8, 'l', track=0.35, mode='O')
    # progress line (bottom)
    pa = 0.55 * env(t, 1.0, 175.2, 1.0, 0.6)
    if pa > 0:
        x0, x1, y = 140, 1780, 1040
        f.L[y:y + 1, x0:x1] += np.float32(0.10 * pa)
        xc = x0 + (x1 - x0) * t / DUR
        f.L[y:y + 1, x0:int(xc)] += np.array(GOLD, np.float32) * 0.35 * pa
        for (a, num, zh, en) in CHAPTERS[:-1]:
            xx = int(x0 + (x1 - x0) * a / DUR)
            lit = t >= a
            f.L[y - 5:y + 6, xx:xx + 1] += np.array(GOLD if lit else GREY, np.float32) * 0.5 * pa
            f.text(zh, xx + 8, y - 14, 15, 'sans_light', GOLD if lit else GREY, pa * (0.9 if lit else 0.5), 'l', mode='L')
        f.glow((xc, y), 4, GOLD2, 0.9 * pa, 'E')
        f.glow((xc, y), 14, GOLD, 0.5 * pa, 'B')


# ============================================================== reusable FX
def draw_stars(f, t):
    S = star_dist(t)
    z = (ST_Z0 - S) % 1.0 + 0.03
    fx = W * 0.32
    sx = W / 2 + ST_X / z * fx; sy = H / 2 + ST_Y / z * fx
    b = np.clip((1.05 - z) ** 2.2, 0, 1) * (0.55 + 0.35 * beat_pulse(t, .18) * energy(t))
    tw = 0.75 + 0.25 * np.sin(t * 3 + ST_X * 40)
    f.splat(sx, sy, ST_COL, b * tw * 0.9, 'L')
    near = z < 0.25
    f.splat(sx[near], sy[near], ST_COL[near], b[near] * 0.8, 'E')
    v = star_speed(t)
    if v > 0.25:   # warp streaks
        z2 = z + min(v * 0.06, 0.25)
        sx2 = W / 2 + ST_X / z2 * fx; sy2 = H / 2 + ST_Y / z2 * fx
        al = cl((v - 0.25) / 1.0)
        idx = np.where((z < 0.7) & (abs(sx - W / 2) < W) & (abs(sy - H / 2) < H))[0][:500]
        for i in idx:
            f.line((sx2[i], sy2[i]), (sx[i], sy[i]), ST_COL[i], al * float(b[i]) * 1.2, 1)

def shockwaves(f, t):
    for ti, k, col in IMPACTS:
        dt = t - ti
        if 0 <= dt < 1.3:
            for j, (dd, sc) in enumerate(((0, 1.0), (0.12, 0.6), (0.24, 0.35))):
                d2 = dt - dd
                if d2 < 0: continue
                r = 40 + 1250 * eo(d2 / 1.1)
                al = (1 - cl(d2 / 1.1)) ** 1.6 * k * sc
                f.circle((W / 2, H / 2), r, col if j else lerpc(col, WHITE, .5), al, 3 if j == 0 else 2)
            f.flash += k * 0.42 * math.exp(-dt / 0.16)
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
IMP = (_IR.uniform(0, 2 * math.pi, 1400), _IR.uniform(0.35, 1.25, 1400), _IR.uniform(0, 0.45, 1400), _IR.integers(0, 6, 1400))

def implode(f, t, t0, t1, cx, cy, cols, a=1.0, R0=950, turns=2.2):
    if t < t0 or t > t1: return
    p = (t - t0) / (t1 - t0)
    th, rr, dl, ci = IMP
    cc = np.array(cols, np.float32)[ci % len(cols)]
    for k in range(4):
        pk = np.clip((p - k * 0.008 - dl) / (1 - dl), 0, 1)
        r = R0 * rr * (1 - (pk ** 3) ** 0.9)
        ang = th + turns * pk ** 3
        al = np.where(pk > 0, np.minimum(pk * 6, 1), 0) * (1 - pk ** 8) * a * (1 - k * 0.2)
        f.splat(cx + r * np.cos(ang), cy + r * np.sin(ang) * 0.75, cc, al * 1.3, 'E')
    f.glow((cx, cy), 20 + 120 * ei(p), WHITE, 0.25 + 0.9 * ei(p), 'B')
    f.glow((cx, cy), 6 + 14 * ei(p), WHITE, 0.6 * ei(p), 'E')

_FR = np.random.default_rng(5)
FL_X = _FR.uniform(0, W + 300, 2200); FL_Y = _FR.uniform(-60, H + 60, 2200)
FL_P = _FR.uniform(0, 6.28, 2200); FL_S = _FR.uniform(0.4, 1.4, 2200); FL_C = _FR.integers(0, 6, 2200)

def flow(f, t, a, cols, speed=140, n=2200, rise=0.0, inward=0.0):
    if a <= 0.003: return
    cc = np.array(cols, np.float32)[FL_C[:n] % len(cols)]
    for k in range(5):
        tt = t - k * 0.035
        x = (FL_X[:n] + FL_S[:n] * speed * tt) % (W + 300) - 150
        y = FL_Y[:n] + 70 * np.sin(x * 0.0035 + FL_P[:n] + tt * 0.5) + 28 * np.sin(x * 0.011 - tt * 0.9 + FL_P[:n] * 2)
        y = (y - rise * tt * FL_S[:n] * 60) % (H + 120) - 60
        if inward > 0:
            x = W / 2 + (x - W / 2) * (1 - inward); y = H / 2 + (y - H / 2) * (1 - inward)
        al = a * (0.55 + 0.45 * np.sin(FL_P[:n] + t)) * (1 - k * 0.18)
        f.splat(x, y, cc, al * 2.4, 'E')
        if k == 0: f.splat(x + 1, y, cc, al * 1.2, 'E')

def chip(f, s, cx, cy, size, col, a, fnt='sans_med', fill=0.10):
    if a <= 0.003: return
    tw = text_width(s, fnt, size)
    px, py = size * 0.75, size * 0.55
    f.rrect_fill(cx - tw / 2 - px, cy - size / 2 - py, cx + tw / 2 + px, cy + size / 2 + py, size * 0.6, col, fill * a)
    f.rrect(cx - tw / 2 - px, cy - size / 2 - py, cx + tw / 2 + px, cy + size / 2 + py, size * 0.6, col, a * 0.9, 2)
    f.text(s, cx, cy, size, fnt, lerpc(col, WHITE, 0.55), a, mode='L', glow=0.25)

def tokens(f, toks, cx, cy, size, a, gap=0.4, pill=True, appear=None, fnt='serif_black'):
    """toks: list of (str, colour, is_term). appear: list of times per token (or None)"""
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


# ============================================================== icons
def icon_cup(f, cx, cy, s, a, t):
    if a <= 0: return
    col = PINK
    top, bot = cy - s * 0.55, cy + s * 0.65
    f.poly([(cx - s * .45, top), (cx - s * .33, bot), (cx + s * .33, bot), (cx + s * .45, top)], col, a, 3)
    f.poly([(cx - s * .52, top), (cx + s * .52, top)], col, a, 3)
    f.arc((cx, top), s * .5, math.pi, 2 * math.pi, col, a * .9, 3)
    f.line((cx + s * .06, top - s * .5), (cx + s * .28, top - s * 1.0), col, a, 3)
    for k in range(7):
        bx = cx - s * .22 + (k % 4) * s * .15 + (k // 4) * s * .07
        by = bot - s * .14 - (k // 4) * s * .15
        f.circle((bx, by), s * .055, GOLD, a * .9, 2)
    # closed sign
    sx, sy = cx + s * 0.95, cy - s * 0.1
    sw = 0.5 + 0.5 * math.sin(t * 2.2)
    f.line((sx, sy - s * .5), (sx - s * .2, sy - s * .25), GREY, a * .7, 1)
    f.line((sx, sy - s * .5), (sx + s * .2, sy - s * .25), GREY, a * .7, 1)
    f.rrect(sx - s * .42, sy - s * .25, sx + s * .42, sy + s * .2, 6, RED, a * (0.6 + 0.4 * sw), 2)
    f.text('已打烊', sx, sy - s * .02, int(s * .2), 'sans_black', RED, a, mode='E', glow=.5)

def icon_two(f, cx, cy, s, a, p, t):
    if a <= 0: return
    d = s * 0.35 + s * 0.85 * eo(p)
    A = (cx - d, cy); B = (cx + d, cy + math.sin(t * 1.5) * 6)
    cb = lerpc(PINK, BLUE, eo(p))
    f.glow(A, s * .2, PINK, a * .5, 'B'); f.circle(A, s * .14, PINK, a, 3); f.glow(A, 5, WHITE, a * .8, 'E')
    f.glow(B, s * .2, cb, a * .5 * (1 - .5 * p), 'B'); f.circle(B, s * .14, cb, a * (1 - .4 * p), 3)
    gap = cl((p - 0.45) / 0.3) * 0.5
    for u0, u1 in ((0.0, 0.5 - gap / 2), (0.5 + gap / 2, 1.0)):
        if u1 <= u0: continue
        pts = []
        for u in np.linspace(u0, u1, 24):
            x = lerp(A[0] + s * .14, B[0] - s * .14, u)
            y = lerp(A[1], B[1], u) + math.sin(u * math.pi) * s * 0.12 * (1 - p)
            pts.append((x, y))
        f.poly(pts, VIOLET, a * (1 - 0.6 * p), 2)

CHART = np.array([.15, .3, .24, .45, .4, .62, .55, .78, .7, .45, .52, .2, .28, -.05, .02, -.3])
def icon_chart(f, cx, cy, s, a, p):
    if a <= 0: return
    n = len(CHART)
    xs = cx - s * 1.3 + np.arange(n) / (n - 1) * s * 2.6
    ys = cy + s * 0.5 - CHART * s * 1.1
    for k in range(5):
        yy = cy - s * .55 + k * s * .3
        f.line((cx - s * 1.35, yy), (cx + s * 1.35, yy), GREY, a * .12, 1)
    m = p * (n - 1)
    k = int(m)
    pts = [(xs[i], ys[i]) for i in range(min(k + 1, n))]
    if k < n - 1:
        u = m - k; pts.append((lerp(xs[k], xs[k + 1], u), lerp(ys[k], ys[k + 1], u)))
    peak = int(np.argmax(CHART))
    if len(pts) > 1:
        f.poly(pts[:peak + 1], TEAL, a, 3)
        if len(pts) > peak + 1:
            f.poly(pts[peak:], RED, a, 4)
        f.glow(pts[-1], 14, RED if len(pts) > peak + 1 else TEAL, a * .9, 'B')
        f.glow(pts[-1], 4, WHITE, a, 'E')

def molecule(f, cx, cy, R, col, a, t, var=0):
    if a <= 0: return
    rot = t * 0.35 + var
    V = [(cx + R * math.cos(rot + k * math.pi / 3), cy + R * math.sin(rot + k * math.pi / 3)) for k in range(6)]
    f.poly(V, col, a, 3, closed=True)
    f.circle((cx, cy), R * 0.55, col, a * 0.5, 2)
    chains = [(0, [1.0, 0.8, 1.0]), (3, [0.9]), (2, [0.8])] if var == 0 else \
             [(0, [0.9, 0.9]), (2, [1.0]), (4, [0.8, 0.8])] if var == 1 else [(1, [1.0, 0.7]), (3, [0.9, 0.9, 0.6]), (5, [0.8])]
    for vi, segs in chains:
        p = V[vi]; ang = rot + vi * math.pi / 3
        for j, L in enumerate(segs):
            a2 = ang + (0.5 if j % 2 == 0 else -0.5)
            q = (p[0] + R * L * math.cos(a2), p[1] + R * L * math.sin(a2))
            f.line(p, q, col, a * 0.85, 2)
            p = q
        f.circle(p, 7, lerpc(col, WHITE, .4), a, 2)
        f.glow(p, 10, col, a * .6, 'B')
    for v in V:
        f.glow(v, 3.5, WHITE, a * .8, 'E')
    f.glow((cx, cy), R * 1.1, col, a * 0.22 * (1 + 0.8 * beat_pulse(t)), 'B')
    for k in range(3):   # orbiting electrons
        ang = t * (1.6 + k * .4) + k * 2.1
        ex, ey = cx + R * 1.75 * math.cos(ang), cy + R * 0.7 * math.sin(ang + k)
        f.glow((ex, ey), 3, WHITE, a * .9, 'E'); f.glow((ex, ey), 9, col, a * .7, 'B')


# ---- neural network
_NR = np.random.default_rng(3)
NN = []
while len(NN) < 78:
    x, y = _NR.uniform(-1, 1, 2)
    if x * x + y * y < 1: NN.append((x, y))
NN = np.array(NN)
NE = []
for i in range(len(NN)):
    d = np.hypot(*(NN - NN[i]).T); js = np.argsort(d)[1:4]
    for j in js:
        if (j, i) not in NE: NE.append((i, j))
NE_PH = _NR.uniform(0, 1, len(NE)); NE_SP = _NR.uniform(0.5, 1.4, len(NE))

def network(f, t, cx, cy, rx, ry, a, t0):
    if a <= 0: return
    P = np.stack([cx + NN[:, 0] * rx, cy + NN[:, 1] * ry], 1)
    P[:, 1] += np.sin(t * 0.8 + NN[:, 0] * 4) * 6
    for k, (i, j) in enumerate(NE):
        ap = eo((t - t0 - 0.008 * k) / 0.5) * a
        if ap <= 0: continue
        f.line(P[i], P[j], lerpc(CYAN, VIOLET, (NN[i, 0] + 1) / 2), ap * 0.35, 1)
        ph = (t * NE_SP[k] * 0.9 + NE_PH[k]) % 1.0
        q = P[i] + (P[j] - P[i]) * ph
        f.glow(tuple(q), 2.5, WHITE, ap * 0.9, 'E')
    bp = beat_pulse(t)
    for i in range(len(NN)):
        ap = eo((t - t0 - 0.01 * i) / 0.4) * a
        col = lerpc(CYAN, VIOLET, (NN[i, 0] + 1) / 2)
        f.glow(tuple(P[i]), 3 + 2 * bp, lerpc(col, WHITE, .5), ap, 'E')
        f.glow(tuple(P[i]), 12, col, ap * 0.35, 'B')


# ============================================================== SCENES
def sc_hook(f, t):
    if t > 18.3: return
    # 3 quick moments
    a0 = env(t, 1.17, 3.30, 0.3, 0.3)
    f.text('你有没有过这样的时刻——', W / 2, 540, 62, 'serif_med', WHITE, a0, t0=1.17, stag=0.06, dur=0.5, glow=0.15)
    a1 = env(t, 3.30, 5.42, 0.25, 0.3)
    icon_cup(f, W / 2 - 40, 430, 130 * (1 + 0.04 * beat_pulse(t)), a1, t)
    f.text('想喝的奶茶，店却关门了。', W / 2, 720, 54, 'sans_med', WHITE, a1, t0=3.4, stag=0.04)
    a2 = env(t, 5.42, 7.55, 0.25, 0.3)
    icon_two(f, W / 2, 440, 200, a2, cl((t - 5.6) / 1.6), t)
    f.text('期待的那个人，忽然冷淡了。', W / 2, 720, 54, 'sans_med', WHITE, a2, t0=5.5, stag=0.04)
    a3 = env(t, 7.55, 9.67, 0.25, 0.3)
    icon_chart(f, W / 2, 430, 190, a3, eo((t - 7.6) / 1.7))
    f.text('看好的股票，一路下跌。', W / 2, 720, 54, 'sans_med', WHITE, a3, t0=7.65, stag=0.04)
    # the question
    a4 = env(t, 9.67, 16.6, 0.4, 0.5)
    f.text('明明只是「不如愿」，', W / 2, 440, 66, 'serif_med', lerpc(GREY, WHITE, 0.6), a4, t0=9.75, stag=0.07, dur=0.6)
    a5 = env(t, 11.81, 16.7, 0.5, 0.6)
    f.text('为什么，心会这么难受？', W / 2, 600, 88, 'serif_black', WHITE, a5, t0=11.85, stag=0.11, dur=0.8, glow=0.3)
    if 11.8 < t < 16.6:   # heartbeat ring
        for b in BEATS[(BEATS > 11.8) & (BEATS < t)][-3:]:
            dt = t - b
            f.circle((W / 2, 600), 260 + dt * 380, RED, 0.35 * math.exp(-dt / 0.5) * a5, 2)
    implode(f, t, 15.6, 18.18, W / 2, H / 2, [MAGENTA, VIOLET, CYAN, GOLD2, PINK, WHITE], a=1.0)

def sc_title(f, t):
    if not (18.0 < t < 22.6): return
    burst(f, t, 18.18, W / 2, H / 2, [MAGENTA, VIOLET, CYAN, GOLD2, PINK, WHITE], 0, 900, 1700, 1.3, 2.2, 1.0, 2)
    a = env(t, 18.18, 22.44, 0.05, 0.5)
    f.text('WHY  DO  WE  FEEL  UNHAPPY', W / 2, 400, 26, 'corm', GOLD2, a * 0.85, track=0.45, t0=18.5, stag=0.02, mode='L')
    f.text('人为什么会感到不开心', W / 2, 520, 128, 'serif_black', WHITE, a, t0=18.18, stag=0.045, dur=0.35, rise=40,
           grad=[CYAN, VIOLET, MAGENTA, ORANGE], mode='E', glow=0.55)
    w = 520 * eo((t - 18.9) / 0.8)
    f.line((W / 2 - w, 640), (W / 2 - 160, 640), GOLD, a * 0.8, 1) if w > 160 else None
    f.line((W / 2 + 160, 640), (W / 2 + w, 640), GOLD, a * 0.8, 1) if w > 160 else None
    f.text('从「开心」的第一性原理说起', W / 2, 640, 34, 'sans_light', GOLD2, a, t0=19.0, stag=0.04)

def sc_brain(f, t):
    if not (22.3 < t < 26.9): return
    a = env(t, 22.44, 26.69, 0.4, 0.4)
    network(f, t, 1300, 540, 430, 330, a, 22.44)
    f.text('大脑，', 190, 430, 84, 'serif_black', WHITE, a, 'l', t0=22.5, stag=0.08)
    f.text('是一台预测机器。', 190, 550, 84, 'serif_black', WHITE, a, 'l', t0=22.9, stag=0.06, grad=[CYAN, VIOLET], mode='E', glow=0.4)
    f.text('它每时每刻都在猜：接下来，会发生什么？', 194, 670, 32, 'sans_light', GREY, a, 'l', t0=23.8, stag=0.025)

def sc_gap(f, t):
    if not (26.5 < t < 39.7): return
    a = env(t, 26.69, 39.44, 0.4, 0.35)
    Ev = keys(t, [(26.69, 0.0), (27.6, 0.55), (33.0, 0.55), (34.0, 0.86)])
    Rv = keys(t, [(26.69, 0.0), (27.8, 0.55), (30.94, 0.55), (31.7, 0.8), (35.19, 0.8), (35.5, 0.36)])
    base, Hm, bw = 880, 520, 150
    xs = {'E': 700, 'R': 1020}
    for key, v, col, zh, en in (('E', Ev, VIOLET, '预期', 'EXPECTATION'), ('R', Rv, CYAN, '现实', 'REALITY')):
        x = xs[key]; top = base - v * Hm
        if v > 0.01:
            f.rrect_fill(x - bw / 2, top, x + bw / 2, base, 10, col, 0.16 * a)
            f.rrect(x - bw / 2, top, x + bw / 2, base, 10, col, a * 0.9, 2)
            f.line((x - bw / 2 + 6, top), (x + bw / 2 - 6, top), lerpc(col, WHITE, .5), a, 3)
            f.glow((x, top), 50, col, a * 0.35 * (1 + bar_pulse(t)), 'B')
        f.text(zh, x, base + 46, 40, 'serif_black', lerpc(col, WHITE, .4), a, glow=0.2)
        f.text(en, x, base + 86, 16, 'corm', GREY, a, track=0.35)
    f.line((560, base), (1160, base), GREY, a * 0.5, 1)
    # gap
    eT, rT = base - Ev * Hm, base - Rv * Hm
    xR = xs['R']
    if Ev > 0.05 and Rv > 0.05:
        for xx in np.arange(xs['E'] + bw / 2 + 8, xR + bw / 2, 16):
            f.line((xx, eT), (xx + 8, eT), VIOLET, a * 0.6, 1)
        if abs(rT - eT) > 6:
            surplus = rT < eT
            colg = GOLD if surplus else RED
            y0, y1 = min(rT, eT), max(rT, eT)
            pul = 0.5 + 0.5 * math.sin(t * 9) if not surplus else 0.7
            f.fillpoly([(xR - bw / 2, y0), (xR + bw / 2, y0), (xR + bw / 2, y1), (xR - bw / 2, y1)], colg, 0.25 * a * pul, 'E')
            f.rrect(xR - bw / 2 - 4, y0, xR + bw / 2 + 4, y1, 4, colg, a * 0.9, 2)
            if surplus and 31.0 < t < 33.5:
                burst(f, t, 31.5, xR, rT, [GOLD, GOLD2, ORANGE], 1, 260, 500, 0.9, 3.0, 0.9)
    # formula on top
    fa = a * env(t, 28.82, 40, 0.4, 0.3)
    tokens(f, [('开心', GOLD2, False), ('≈', WHITE, False), ('现实', CYAN, False), ('−', WHITE, False), ('预期', VIOLET, False)],
           W / 2, 210, 74, fa, gap=0.45, pill=False, appear=[28.82, 29.1, 29.35, 29.6, 29.85])
    # annotations (right column)
    X = 1260
    s1 = a * env(t, 30.94, 33.0, 0.3, 0.3)
    f.text('现实 > 预期', X, 470, 50, 'serif_black', GOLD, s1, 'l', t0=30.94, glow=.4)
    f.text('惊喜 —— 多巴胺上升', X, 545, 32, 'sans_light', WHITE, s1, 'l', t0=31.2)
    s2 = a * env(t, 33.07, 35.19, 0.3, 0.25)
    f.text('得到之后，', X, 430, 48, 'serif_black', WHITE, s2, 'l', t0=33.07)
    f.text('预期也会悄悄上调', X, 500, 48, 'serif_black', VIOLET, s2, 'l', t0=33.3, glow=.3)
    f.text('享乐适应 · Hedonic Adaptation', X, 570, 24, 'sans_light', GREY, s2, 'l', t0=33.6)
    s3 = a * env(t, 35.19, 39.44, 0.15, 0.35)
    f.text('现实 < 预期', X, 400, 60, 'serif_black', RED, s3, 'l', t0=35.19, stag=0.03, glow=.5, mode='E')
    f.text('大脑把它解读为：', X, 485, 32, 'sans_light', WHITE, s3, 'l', t0=35.6)
    for i, w in enumerate(['损失', '威胁', '失控', '价值受挫']):
        ca = s3 * eo((t - 36.0 - i * 0.27) / 0.3)
        cx = X + 60 + (i % 2) * 190 + (30 if i == 3 else 0)
        chip(f, w, cx, 580 + (i // 2) * 90, 32, RED, ca)

def sc_chem(f, t):
    if not (39.3 < t < 50.3): return
    a = env(t, 39.44, 50.06, 0.4, 0.4)
    f.text('不开心，本质上是一场身体里的化学反应', W / 2, 200, 54, 'serif_med', WHITE, a, t0=39.5, stag=0.035, glow=.15)
    items = [(420, ORANGE, '多巴胺', 'DOPAMINE', '预期中的奖励落空', '→ 失落、提不起劲', 41.56, 1, 0),
             (960, TEAL, '血清素', 'SEROTONIN', '稳定感、满足感下降', '→ 低落、心神不宁', 43.69, 1, 1),
             (1500, RED, '皮质醇', 'CORTISOL', '感知到失控与不确定', '→ 压力警报拉响', 45.81, -1, 2)]
    for x, col, zh, en, d1, d2, ta, dirn, var in items:
        p = cl((t - ta) / 0.6)
        ia = a * eo(p)
        if ia <= 0: continue
        R = 95 * eback(p, 2.0)
        molecule(f, x, 490, R, col, ia, t, var)
        # level arrow
        ax, ay = x + 170, 490
        ph = (t * 1.2) % 1.0
        for k in range(3):
            yy = ay + dirn * (-40 + k * 40 + ph * 40)
            f.poly([(ax - 14, yy - dirn * 10), (ax, yy + dirn * 6), (ax + 14, yy - dirn * 10)], col, ia * (0.3 + 0.25 * k), 3)
        f.text(zh, x, 680, 56, 'serif_black', lerpc(col, WHITE, 0.25), ia, t0=ta + 0.15, glow=.35, mode='E')
        f.text(en, x, 735, 20, 'corm', GREY, ia, track=0.4)
        f.text(d1, x, 800, 32, 'sans_light', WHITE, ia, t0=ta + 0.4, stag=0.02)
        f.text(d2, x, 848, 32, 'sans_med', col, ia, t0=ta + 0.7, stag=0.02)

def sc_munger(f, t):
    if not (49.9 < t < 56.6): return
    a = env(t, 50.06, 56.44, 0.35, 0.3)
    f.text('查理·芒格 · 人类误判心理学', W / 2, 190, 32, 'sans_light', GOLD2, a, track=0.15, t0=50.06)
    for (x0, x1, ta, title, l1, l2, col) in ((200, 920, 50.2, '被剥夺超级反应倾向', '失去已经拥有的东西，', '痛感会被成倍放大', ORANGE),
                                             (1000, 1720, 52.19, '避免怀疑倾向', '原本确定的事忽然不确定，', '大脑会本能地抗拒与焦虑', CYAN)):
        p = cl((t - ta) / 0.5); ca = a * eo(p)
        if ca <= 0: continue
        dy = (1 - eo(p)) * 40
        f.rrect_fill(x0, 280 + dy, x1, 780 + dy, 22, col, 0.06 * ca)
        f.rrect(x0, 280 + dy, x1, 780 + dy, 22, col, ca * 0.75, 2)
        cx = (x0 + x1) / 2; vy = 430 + dy
        lt = t - ta
        if col == ORANGE:  # orb torn away from its socket
            f.circle((cx, vy), 70, lerpc(GOLD, RED, cl(lt / 1.5)), ca, 3)
            ox = cx + 190 * eo((lt - 0.4) / 1.4)
            f.glow((ox, vy), 30, GOLD, ca * 0.9, 'B'); f.glow((ox, vy), 12, GOLD2, ca, 'E')
            if lt > 0.9:
                for k in range(6):
                    ang = k * 1.05 + 0.3
                    f.line((cx + 70 * math.cos(ang), vy + 70 * math.sin(ang)),
                           (cx + 92 * math.cos(ang + .12), vy + 92 * math.sin(ang + .12)), RED, ca * .8, 2)
        else:  # a certain circle dissolving into noise
            jit = cl((lt - 0.5) / 1.5)
            n = 90
            ang = np.linspace(0, 2 * math.pi, n)
            rng = np.random.default_rng(int(t * 30) % 1000)
            rr = 70 + rng.normal(0, 1, n) * 22 * jit
            f.poly(np.stack([cx + rr * np.cos(ang), vy + rr * np.sin(ang)], 1), col, ca * (1 - .4 * jit), 2, closed=True)
            ps = rng.normal(0, 1, (160, 2)) * (60 + 60 * jit)
            f.splat(cx + ps[:, 0], vy + ps[:, 1], col, ca * jit * 0.9)
            f.text('?', cx, vy, 56, 'serif_black', WHITE, ca * jit, mode='E', glow=.4)
        f.text(title, cx, 590 + dy, 48, 'serif_black', lerpc(col, WHITE, .3), ca, t0=ta + .1, stag=0.04, glow=.3, mode='E')
        f.text(l1, cx, 670 + dy, 30, 'sans_light', WHITE, ca, t0=ta + .35, stag=0.02)
        f.text(l2, cx, 716 + dy, 30, 'sans_light', WHITE, ca, t0=ta + .5, stag=0.02)
    b = a * env(t, 54.31, 60, 0.4, 0.3)
    f.text('失去，比得到更痛；不确定，比坏消息更难熬。', W / 2, 880, 44, 'serif_med', GOLD2, b, t0=54.31, stag=0.03, glow=.35, mode='E')

FTERMS = [('预期落差', RED, 'GAP'), ('主观重要性', ORANGE, 'WEIGHT'), ('失控感', MAGENTA, 'CONTROL'),
          ('不确定性', VIOLET, 'UNCERTAINTY'), ('损失厌恶', CYAN, 'LOSS AVERSION')]

def sc_formula(f, t):
    if not (56.3 < t < 73.6): return
    a = env(t, 56.44, 73.44, 0.1, 0.35)
    fy = keys(t, [(64.7, 540.0), (65.4, 330.0)])
    toks = [('不开心', WHITE, False), ('=', GOLD, False)]
    app = [56.44, 56.75]
    for i, (s, col, en) in enumerate(FTERMS):
        if i: toks.append(('×', GOLD, False)); app.append(57.5 + i * 1.066 - 0.25)
        toks.append((s, col, True)); app.append(57.5 + i * 1.066)
    dim = 1 - 0.65 * eio((t - 69.2) / 0.6)
    cs = tokens(f, toks, W / 2, fy, 46, a * dim, gap=0.32, appear=app)
    k = 0
    for i, (s, col, en) in enumerate(FTERMS):
        idx = 2 + i * 2
        ea = a * dim * eo((t - app[idx] - 0.2) / 0.4)
        f.text(en, cs[idx], fy - 78, 15, 'corm', col, ea * 0.9, track=0.3)
    # orbiting colour souls
    oa = a * env(t, 58, 73.44, 1, .4)
    for i, (s, col, en) in enumerate(FTERMS):
        ang = t * 0.9 + i * 2 * math.pi / 5
        p = (W / 2 + 880 * math.cos(ang), fy + 150 * math.sin(ang))
        f.glow(p, 40, col, oa * 0.35, 'B'); f.glow(p, 4, WHITE, oa * 0.8, 'E')
    sa = a * env(t, 62.82, 64.9, 0.35, 0.3)
    f.text('不开心，从来不是单一原因造成的', W / 2, 680, 36, 'sans_light', GREY, sa, t0=62.82, stag=0.03)
    # add vs multiply
    ca = a * env(t, 64.95, 69.3, 0.35, 0.35)
    f.text('相加', 560, 520, 40, 'sans_med', GREY, ca * 0.7, 'r', t0=65.2)
    f.text('2 + 2 + 2 + 2 + 2  =  10', 600, 520, 46, 'mono', GREY, ca * 0.7, 'l', t0=65.2, stag=0.012)
    n = int(round(2 * 2 ** (4 * eo((t - 66.3) / 1.2)))) if t > 66.3 else 2
    ma = ca * eo((t - 65.9) / .3)
    f.text('相乘', 560, 620, 48, 'sans_black', RED, ma, 'r', mode='E', glow=.4)
    f.text('2 × 2 × 2 × 2 × 2  =  %2d' % n, 600, 620, 58, 'mono', RED, ma, 'l', mode='E', glow=.5)
    f.text('任何一项被放大，痛苦就会成倍放大。', W / 2, 770, 46, 'serif_med', WHITE, ca, t0=67.2, stag=0.03)
    # any factor -> 0
    za = a * env(t, 69.2, 73.44, 0.35, 0.35)
    f.text('× 0', W / 2, 500, 120, 'serif_black', TEAL, za * eo((t - 69.25) / .3), mode='E', glow=.7)
    f.text('只要有一项趋近于零，', W / 2, 650, 50, 'serif_med', WHITE, za, t0=69.6, stag=0.04)
    f.text('痛苦就会烟消云散。', W / 2, 740, 64, 'serif_black', TEAL, za, t0=70.3, stag=0.06, glow=.45, mode='E')
    f.text('—— 这，就是我们可以下手的地方', W / 2, 850, 30, 'sans_light', GOLD2, za, t0=71.4, stag=0.03)
    if 69.2 < t < 71:
        burst(f, t, 69.25, W / 2, 500, [TEAL, CYAN, WHITE], 2, 400, 900, 0.8, 3.0, 0.9)

CASES = [
    (73.44, 79.83, '情况一', '小事不如愿', '想喝奶茶，店却关门了', [.6, .12, .2, .15, .2],
     ['重要性很低 → 只是有点扫兴'], TEAL),
    (79.83, 88.32, '情况二', '重要关系不如愿', '期待被重视，对方却变冷淡', [.85, .95, .85, .9, .9],
     ['五项同时拉满 → 痛苦被放大很多倍'], RED),
    (88.32, 96.83, '情况三', '投资不如愿', '你认为逻辑很强，股价却大跌', [.9, .9, .8, .95, .95],
     ['痛的不只是钱，', '而是「认知模型」被现实挑战'], ORANGE)]

def sc_cases(f, t):
    if not (73.3 < t < 97.0): return
    A = env(t, 73.44, 96.83, 0.4, 0.4)
    kf = [(CASES[0][0], CASES[0][5])]
    for c in CASES:
        kf.append((c[0] + 0.25, c[5])) if c is not CASES[0] else None
    vals = []
    for i in range(5):
        vk = [(73.44, 0.0), (74.4, CASES[0][5][i]), (79.83, CASES[0][5][i]), (80.8, CASES[1][5][i]),
              (88.32, CASES[1][5][i]), (89.3, CASES[2][5][i])]
        vals.append(keys(t, vk))
    # right panel: factor bars
    for i, (s, col, en) in enumerate(FTERMS):
        y = 300 + i * 92
        f.text(s, 1010, y, 32, 'sans_med', lerpc(col, WHITE, .35), A, 'l')
        x0, x1 = 1230, 1770
        f.L[int(y) - 3:int(y) + 3, x0:x1] += np.float32(0.06 * A)
        xe = x0 + (x1 - x0) * vals[i]
        if vals[i] > 0.005:
            f.line((x0, y), (xe, y), col, A, 7)
            f.glow((xe, y), 18, col, A * 0.6 * (1 + bar_pulse(t)), 'B'); f.glow((xe, y), 4, WHITE, A, 'E')
    prod = float(np.prod(np.clip(vals, 1e-4, 1)))
    pain = cl((math.log10(prod) + 4.0) / 3.9)
    y = 820
    f.text('痛苦指数', 1010, y, 34, 'serif_black', WHITE, A, 'l')
    x0, x1 = 1230, 1770
    f.rrect(x0 - 6, y - 20, x1 + 6, y + 20, 18, GREY, A * 0.5, 1)
    xe = x0 + (x1 - x0) * pain
    n = 40
    for k in range(n):
        u0, u1 = k / n, (k + 1) / n
        if u0 > pain: break
        c = grad_color([TEAL, GOLD, ORANGE, RED], u0)
        f.line((x0 + (x1 - x0) * u0 + 2, y), (min(x0 + (x1 - x0) * u1, xe) - 2, y), c, A, 22)
    f.glow((xe, y), 40 * (0.5 + pain), grad_color([TEAL, GOLD, ORANGE, RED], pain), A * 0.8 * (1 + beat_pulse(t)), 'B')
    f.text('乘积', 1770, y + 50, 20, 'sans_light', GREY, A, 'r')
    # left panel
    for (ta, tb, tag, title, scen, v, verdict, vcol), idx in zip(CASES, range(3)):
        ca = A * env(t, ta, tb, 0.35, 0.35)
        if ca <= 0: continue
        f.text(tag, 150, 230, 28, 'sans_med', GOLD, ca, 'l', track=0.2, t0=ta)
        f.line((150, 262), (150 + 120 * eo((t - ta) / .5), 262), GOLD, ca, 2)
        f.text(title, 150, 330, 70, 'serif_black', WHITE, ca, 'l', t0=ta + 0.05, stag=0.05, glow=.2)
        f.text(scen, 152, 420, 36, 'sans_light', lerpc(GREY, WHITE, .5), ca, 'l', t0=ta + 0.4, stag=0.025)
        lt = t - ta
        if idx == 0:
            icon_cup(f, 420, 630, 105, ca, t)
        elif idx == 1:
            icon_two(f, 450, 630, 170, ca, cl((lt - 0.5) / 2.5), t)
            for j, w in enumerate(['关系损失', '被剥夺感', '价值受挫', '失控感']):
                chip(f, w, [200, 690, 230, 680][j], [540, 540, 740, 740][j], 26, RED, ca * eo((lt - 2.2 - j * .3) / .3))
        else:
            icon_chart(f, 460, 630, 150, ca, eo((lt - 0.3) / 2.2))
            for j, w in enumerate(['判断力被怀疑', '财富损失', '未来不确定', '机会成本', '市场否定感']):
                chip(f, w, [230, 680, 200, 470, 720][j], [520, 520, 760, 780, 760][j], 24, ORANGE, ca * eo((lt - 2.0 - j * .25) / .3))
        for j, line in enumerate(verdict):
            vt = ta + (3.0 if idx == 0 else 4.25)
            f.text(line, 150, 880 + j * 62, 46 if j == 0 else 44, 'serif_black', vcol if j == len(verdict) - 1 else WHITE,
                   ca, 'l', t0=vt + j * 0.5, stag=0.04, glow=.35, mode='E')

def sc_question(f, t):
    if not (96.7 < t < 103.4): return
    a = env(t, 96.83, 101.4, 0.6, 0.6)
    f.text('那么，', W / 2, 440, 56, 'serif_light', GREY, a, t0=96.9, stag=0.15, dur=0.8)
    f.text('怎样才能，少一点不开心？', W / 2, 570, 80, 'serif_black', WHITE, a, t0=98.96, stag=0.09, dur=0.7, glow=.35,
           out=(100.7, 0.7), rise=24)
    implode(f, t, 100.7, 103.2, W / 2, H / 2, [GOLD, GOLD2, ORANGE, WHITE, PINK, GOLD], a=1.0)

def sc_munger_quote(f, t):
    if not (103.1 < t < 107.7): return
    burst(f, t, 103.2, W / 2, H / 2, [GOLD, GOLD2, ORANGE, WHITE, PINK, GOLD], 3, 900, 1800, 1.4, 2.0, 1.0, 2)
    a = env(t, 103.2, 107.45, 0.1, 0.4)
    # sunburst rays (芒)
    for k in range(28):
        ang = k * 2 * math.pi / 28 + t * 0.12
        L1 = 1500
        w = 0.035
        pts = [(W / 2, H / 2 + 20), (W / 2 + L1 * math.cos(ang - w), H / 2 + 20 + L1 * math.sin(ang - w)),
               (W / 2 + L1 * math.cos(ang + w), H / 2 + 20 + L1 * math.sin(ang + w))]
        f.fillpoly(pts, GOLD, a * 0.05 * (1 + 0.6 * beat_pulse(t)), 'B')
    f.text('THE  FIRST  RULE  OF  A  HAPPY  LIFE', W / 2, 330, 24, 'corm', GOLD2, a, track=0.4, t0=103.4, stag=0.015)
    f.text('幸福生活的第一条法则，', W / 2, 470, 80, 'serif_black', WHITE, a, t0=103.3, stag=0.05, glow=.25)
    f.text('是降低预期。', W / 2, 610, 108, 'serif_black', GOLD2, a, t0=104.1, stag=0.1, dur=0.5,
           grad=[GOLD2, GOLD, GOLDD], mode='E', glow=.7)
    f.text('—— 查理·芒格', 1380, 750, 34, 'sans_light', GREY, a, 'r', t0=105.0)

def sc_elastic(f, t):
    if not (107.3 < t < 116.1): return
    a = env(t, 107.45, 115.96, 0.4, 0.35)
    f.text('真正的修炼，不是没有期待，而是——', W / 2, 200, 48, 'serif_med', WHITE, a, t0=107.5, stag=0.035)
    # rigid rod
    cx, cy = 520, 500
    snap = 110.6
    lt = t - 107.8
    if t < snap:
        bend = 8 * eo(lt / 2.5) * (1 + 0.3 * math.sin(t * 30) * cl((t - 109.5) / 1))
        pts = [(cx - 240 + u * 480, cy + bend * math.sin(u * math.pi)) for u in np.linspace(0, 1, 30)]
        f.poly(pts, lerpc(GREY, RED, cl(lt / 2.5)), a, 10)
        crack = cl((t - 109.2) / 1.4)
        if crack > 0:
            zz = [(cx, cy - 6)]
            for k in range(6):
                zz.append((cx + (8 if k % 2 else -8), cy - 6 - (k + 1) * 9 * crack))
            f.poly(zz, WHITE, a, 2)
    else:
        dt = t - snap
        for sgn in (-1, 1):
            ang = 0.5 * eo(dt / 0.6)
            ox = cx + sgn * (10 + 60 * eo(dt / 0.6)); oy = cy + 120 * ei(cl(dt / 1.5))
            p0 = (ox, oy); p1 = (ox + sgn * 240 * math.cos(ang), oy + 240 * math.sin(ang))
            f.line(p0, p1, RED, a * (1 - 0.5 * cl(dt / 2)), 10)
        burst(f, t, snap, cx, cy, [RED, ORANGE, WHITE], 4, 300, 700, 0.6, 3.5, a)
    for k in range(3):  # pressure arrows
        ax = cx - 120 + k * 120; ay = cy - 110 + 10 * math.sin(t * 6 + k)
        f.line((ax, ay - 50), (ax, ay), GREY, a * 0.6, 2)
        f.poly([(ax - 10, ay - 12), (ax, ay), (ax + 10, ay - 12)], GREY, a * 0.6, 2)
    f.text('刚性预期', cx, 690, 58, 'serif_black', RED, a, t0=108.0, glow=.35, mode='E')
    f.text('「必须如此」', cx, 770, 36, 'sans_med', WHITE, a, t0=108.4)
    # elastic spring
    ex = 1400
    amp = 40 + 40 * math.sin((t - 107.45) * 2 * math.pi / 2.135) + 25 * beat_pulse(t)
    pts = []
    for u in np.linspace(0, 1, 140):
        x = ex - 260 + u * 520
        y = cy + amp * math.sin(u * math.pi) * math.sin(u * 7 * math.pi + t * 2.5) * 0.6 + amp * 0.5 * math.sin(u * math.pi)
        pts.append((x, y))
    ea = a * eo((t - 108.6) / 0.6)
    for k, (p0, p1) in enumerate(zip(pts, pts[1:])):
        f.line(p0, p1, grad_color([TEAL, CYAN, GOLD], k / len(pts)), ea, 4)
    f.glow((ex - 260, cy), 10, TEAL, ea, 'B'); f.glow((ex + 260, cy), 10, GOLD, ea, 'B')
    f.text('弹性预期', ex, 690, 58, 'serif_black', TEAL, ea, t0=108.7, glow=.4, mode='E')
    f.text('「我希望如此，也接受变化」', ex, 770, 36, 'sans_med', WHITE, ea, t0=109.1)
    f.text('→', W / 2 + 0, 500, 60, 'sans_light', GOLD, ea)
    f.text('认真做事，但不执着结果；有期待，但不把期待变成「必须」。', W / 2, 910, 38, 'serif_med', GOLD2, a, t0=111.71,
           stag=0.03, glow=.3, mode='E')

def icon_people(f, cx, cy, s, col, a):
    for dx, sc in ((-s * .45, .8), (s * .45, .8), (0, 1)):
        f.circle((cx + dx, cy - s * .25 * sc), s * .2 * sc, col, a, 2)
        f.arc((cx + dx, cy + s * .45 * sc), s * .38 * sc, math.pi, 2 * math.pi, col, a, 2)

def icon_target(f, cx, cy, s, col, a, t):
    for k in range(3):
        f.circle((cx, cy), s * (0.2 + 0.2 * k), col, a * (1 - 0.2 * k), 2)
    ang = -0.6
    ox = cx + s * 0.9 * math.cos(ang) * (1 - 0.3 * beat_pulse(t)); oy = cy + s * 0.9 * math.sin(ang)
    f.line((ox, oy), (cx + 12, cy - 8), lerpc(col, WHITE, .4), a, 3)
    f.glow((cx, cy), 6, WHITE, a, 'E')

def icon_scale(f, cx, cy, s, col, a, t):
    tilt = 0.18 * math.sin(t * 1.8)
    f.line((cx, cy - s * .6), (cx, cy + s * .55), col, a, 2)
    f.line((cx - s * .35, cy + s * .55), (cx + s * .35, cy + s * .55), col, a, 2)
    L = s * .75
    p0 = (cx - L * math.cos(tilt), cy - s * .45 - L * math.sin(tilt)); p1 = (cx + L * math.cos(tilt), cy - s * .45 + L * math.sin(tilt))
    f.line(p0, p1, col, a, 3)
    for p in (p0, p1):
        f.line(p, (p[0] - s * .22, p[1] + s * .45), col, a * .7, 1)
        f.line(p, (p[0] + s * .22, p[1] + s * .45), col, a * .7, 1)
        f.arc((p[0], p[1] + s * .45), s * .22, 0, math.pi, col, a, 2)

def sc_layer1(f, t):
    if not (115.8 < t < 133.1): return
    a = env(t, 115.96, 132.96, 0.4, 0.35)
    f.text('LAYER  01', W / 2, 135, 22, 'orb', GOLD, a, track=0.3, t0=115.96)
    f.text('第一层 · 降低三类不合理的预期', W / 2, 200, 56, 'serif_black', WHITE, a, t0=116.1, stag=0.04, glow=.2)
    cards = [(400, VIOLET, '对他人的期待', '不默认别人永远理解你、', '支持你、按你的方式回应你', 118.09, 0),
             (960, ORANGE, '对结果的期待', '不默认努力立刻有回报、', '逻辑马上兑现、投入等价回收', 122.33, 1),
             (1520, CYAN, '对公平的期待', '不默认好人必有好报、', '正确马上被认可、真心必被珍惜', 126.60, 2)]
    for cx, col, title, l1, l2, ta, k in cards:
        p = cl((t - ta) / 0.55); ca = a * eo(p)
        if ca <= 0: continue
        dy = (1 - eback(p, 1.4)) * 80
        x0, x1, y0, y1 = cx - 250, cx + 250, 300 + dy, 800 + dy
        f.rrect_fill(x0, y0, x1, y1, 26, col, 0.07 * ca)
        f.rrect(x0, y0, x1, y1, 26, col, ca * 0.8, 2)
        f.line((x0 + 40, y0), (x0 + 40 + 120 * eo((t - ta - .3) / .5), y0), lerpc(col, WHITE, .5), ca, 4)
        f.text('0%d' % (k + 1), x1 - 40, y0 + 46, 28, 'orb', col, ca * 0.7, 'r')
        iy = y0 + 140
        if k == 0: icon_people(f, cx, iy, 90, col, ca)
        elif k == 1: icon_target(f, cx, iy, 85, col, ca, t)
        else: icon_scale(f, cx, iy, 85, col, ca, t)
        f.glow((cx, iy), 70, col, ca * 0.25, 'B')
        f.text(title, cx, y0 + 285, 46, 'serif_black', lerpc(col, WHITE, .35), ca, t0=ta + .15, stag=0.05, glow=.3, mode='E')
        f.text(l1, cx, y0 + 375, 29, 'sans_light', WHITE, ca, t0=ta + .45, stag=0.02)
        f.text(l2, cx, y0 + 420, 29, 'sans_light', WHITE, ca, t0=ta + .6, stag=0.02)
    f.text('这不是悲观，而是更接近现实。', W / 2, 900, 48, 'serif_med', GOLD2, a * env(t, 130.84, 140, .3, .3), t0=130.84,
           stag=0.05, glow=.4, mode='E')

def sc_layer2(f, t):
    if not (132.8 < t < 139.5): return
    a = env(t, 132.96, 139.33, 0.4, 0.35)
    f.text('LAYER  02', W / 2, 135, 22, 'orb', TEAL, a, track=0.3, t0=133.0)
    f.text('第二层 · 训练大脑对落差的反应', W / 2, 200, 56, 'serif_black', WHITE, a, t0=133.1, stag=0.04, glow=.2)
    cx, cy = W / 2, 500
    calm = eio((t - 133.6) / 3.6)
    # ECG
    pts = []
    for x in np.arange(0, W + 1, 6):
        u = x / W
        ph = (x * 0.012 - t * 6)
        jag = (np.sin(ph * 3.1) * 0.5 + np.sin(ph * 7.3 + 1) * 0.35) * (1 + 2.5 * (abs((ph % 6.0) - 3) < 0.25))
        smooth = math.sin(x * 0.006 - t * 2.0)
        y = cy + 70 * ((1 - calm) * jag * 1.3 + calm * smooth * 0.6)
        pts.append((x, y))
    f.poly(pts, lerpc(RED, TEAL, calm), a * 0.55, 2)
    # breathing ring (one cycle ~ 2 bars)
    ph = (t - 132.96) / 4.27 * 2 * math.pi
    br = 0.5 - 0.5 * math.cos(ph)
    R = 120 + 70 * br
    col = lerpc(RED, TEAL, calm)
    for k in range(5):
        f.circle((cx, cy), R + k * 22, col, a * (0.8 - k * 0.15), 2 if k else 3)
    f.glow((cx, cy), R * 0.9, col, a * 0.22, 'B')
    f.fillpoly([(cx + R * math.cos(q), cy + R * math.sin(q)) for q in np.linspace(0, 2 * math.pi, 64)], (0, 0, 0), 0)
    f.text('吸' if math.sin(ph) > 0 else '呼', cx, cy - 8, 60, 'serif_black', WHITE, a * 0.9, glow=.3)
    f.text('INHALE' if math.sin(ph) > 0 else 'EXHALE', cx, cy + 50, 16, 'corm', GREY, a, track=0.4)
    a1 = a * env(t, 133.2, 137.0, 0.35, 0.35)
    f.text('情绪高峰期，大脑不是在思考，而是在防御。', W / 2, 800, 42, 'serif_med', WHITE, a1, t0=133.3, stag=0.03)
    a2 = a * env(t, 135.08, 139.33, 0.35, 0.35)
    f.text('先降生理唤醒，再做认知重构', W / 2, 900, 52, 'serif_black', TEAL, a2, t0=135.08, stag=0.05, glow=.4, mode='E')
    a3 = a * env(t, 137.21, 139.33, 0.35, 0.35)
    f.text('先别急着判断、追问、发消息、做决定', W / 2, 800, 40, 'sans_light', GREY, a3, t0=137.21, stag=0.025)

def sc_layer3(f, t):
    if not (139.2 < t < 150.1): return
    a = env(t, 139.33, 149.97, 0.5, 0.1)
    inward = ei(cl((t - 148.3) / 1.67))
    flow(f, t, a * (0.9 - 0.5 * env(t, 143.6, 147.8, .6, .6)), [TEAL, VIOLET, CYAN, BLUE, PINK, TEAL], 160, inward=inward)
    ha = env(t, 139.33, 143.4, 0.4, 0.4)
    f.text('LAYER  03', W / 2, 135, 22, 'orb', VIOLET, ha, track=0.3, t0=139.33)
    f.text('第三层 · 从「占有心」到「流动心」', W / 2, 200, 56, 'serif_black', WHITE, ha, t0=139.4, stag=0.04, glow=.2)
    words = [('关系会变', 470, 430), ('市场会变', 1420, 400), ('人心会变', 760, 640), ('身体会变', 1240, 700),
             ('环境会变', 430, 820), ('认知也会变', 1500, 590)]
    cols = [TEAL, VIOLET, CYAN, PINK, BLUE, GOLD2]
    for i, (w, x, y) in enumerate(words):
        tb = BEATS[np.searchsorted(BEATS, 140.1)] + i * 0.534
        wa = env(t, tb, tb + 1.9, 0.2, 0.01)
        if wa <= 0: continue
        drift = 120 * ei(cl((t - tb - 0.9) / 1.0))
        f.text(w, x + drift, y, 52, 'serif_med', cols[i], wa, t0=tb, stag=0.05, out=(tb + 1.0, 0.8), rise=-30, glow=.35, mode='E')
    qa = env(t, 143.59, 147.6, 0.5, 0.5)
    f.text('凡所有相，皆是虚妄', W / 2, 500, 112, 'serif_black', GOLD2, qa, t0=143.65, stag=0.14, dur=0.9, rise=10,
           grad=[GOLD2, GOLD, GOLDD, GOLD], mode='E', glow=.6)
    f.text('不是一切都没有意义，而是不要把暂时的现象，当成永恒的归属', W / 2, 650, 30, 'sans_light', GREY, qa, t0=145.0, stag=0.02)
    pa = env(t, 147.85, 149.97, 0.3, 0.1)
    f.text('可以认真珍惜，但不要执着占有。', W / 2, 540, 60, 'serif_black', WHITE, pa, t0=147.85, stag=0.05, glow=.3)
    implode(f, t, 148.2, 149.97, W / 2, H / 2, [TEAL, MAGENTA, CYAN, GOLD2, VIOLET, WHITE], a=0.9, R0=800)

# ---- alley -> plain
def corridor_segments(t):
    VP = (W / 2, 540)
    segs = []
    near = (600, 140, 1320, 940)
    def rect(s):
        x0 = VP[0] + (near[0] - VP[0]) * s; x1 = VP[0] + (near[2] - VP[0]) * s
        y0 = VP[1] + (near[1] - VP[1]) * s; y1 = VP[1] + (near[3] - VP[1]) * s
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for k in range(9):
        d = (k / 9 + t * 0.35) % 1.0
        s = 0.12 + 0.88 * d ** 2
        r = rect(s)
        for i in range(4):
            segs.append((r[i], r[(i + 1) % 4], 0.25 + 0.75 * d))
    a, b = rect(0.12), rect(1.0)
    for i in range(4):
        segs.append((a[i], b[i], 1.0))
    return segs

_SH = np.random.default_rng(8)
SHARDS = None
def shards():
    global SHARDS
    if SHARDS is None:
        out = []
        for p0, p1, w in corridor_segments(152.09):
            n = max(1, int(math.hypot(p1[0] - p0[0], p1[1] - p0[1]) / 70))
            for k in range(n):
                q0 = (lerp(p0[0], p1[0], k / n), lerp(p0[1], p1[1], k / n))
                q1 = (lerp(p0[0], p1[0], (k + 1) / n), lerp(p0[1], p1[1], (k + 1) / n))
                c = ((q0[0] + q1[0]) / 2, (q0[1] + q1[1]) / 2)
                d = np.array([c[0] - W / 2, c[1] - 540]); d /= (np.linalg.norm(d) + 1e-3)
                d += _SH.normal(0, 0.35, 2)
                out.append((q0, q1, c, d, _SH.uniform(600, 1600), _SH.uniform(-6, 6), w))
        SHARDS = out
    return SHARDS

PATHS = [(-880, 0.2, TEAL), (-560, 0.35, CYAN), (-250, 0.5, VIOLET), (0, 0.0, GOLD2), (240, 0.45, PINK), (540, 0.3, GOLD),
         (860, 0.15, GREEN), (-1100, 0.6, BLUE), (1150, 0.55, MAGENTA)]

def plain(f, t, a, hy):
    VP = (W / 2, hy)
    for k in range(-16, 17):
        xb = W / 2 + k * 260
        f.line(VP, (xb, H + 40), lerpc(CYAN, VIOLET, (k + 16) / 32), a * 0.35, 1)
    for i in range(1, 22):
        z = i - (t * 1.6) % 1.0
        if z <= 0.2: continue
        y = hy + 900 / z
        if y > H + 5: continue
        f.line((0, y), (W, y), CYAN, a * cl(0.6 / z * 3) * 0.45, 1)
    f.line((0, hy), (W, hy), lerpc(TEAL, WHITE, .3), a * 0.8, 2)
    f.glow((W / 2, hy), 260, TEAL, a * 0.25, 'B')
    # many glowing paths
    for j, (xh, bend, col) in enumerate(PATHS):
        p = eo((t - 152.3 - j * 0.12) / 1.4)
        if p <= 0: continue
        P0 = np.array([W / 2, H + 20.0]); P2 = np.array([W / 2 + xh, hy + 8.0])
        P1 = np.array([W / 2 + xh * bend * 2.2 - (300 if j % 2 else -300) * bend, (H + hy) / 2])
        us = np.linspace(0, p, 50)[:, None]
        pts = (1 - us) ** 2 * P0 + 2 * (1 - us) * us * P1 + us ** 2 * P2
        f.poly(pts, col, a * 0.9, 3)
        u = (t * 0.35 + j * 0.13) % 1.0
        if u < p:
            q = (1 - u) ** 2 * P0 + 2 * (1 - u) * u * P1 + u ** 2 * P2
            f.glow(tuple(q), 5, WHITE, a, 'E'); f.glow(tuple(q), 18, col, a * 0.7, 'B')
        f.glow(tuple(P2), 6 * p, col, a * p, 'E')

def sc_alley(f, t):
    if not (149.9 < t < 157.0): return
    sh = 152.09
    a = env(t, 149.97, 156.34, 0.15, 0.6)
    if t < sh:
        for p0, p1, w in corridor_segments(t):
            f.line(p0, p1, RED if w > 0.9 else lerpc(RED, ORANGE, 0.4), a * w * 0.8, 2)
        z = 0.5 + 0.45 * math.sin((t - 149.97) * 3.0)
        s = 0.2 + 0.8 * z ** 2
        dp = (W / 2, 540 + 300 * s)
        f.glow(dp, 10 + 18 * s, WHITE, a, 'E'); f.glow(dp, 50 * s, GOLD, a * 0.6, 'B')
        f.text('⇅', dp[0] + 90 * s + 30, dp[1], int(40 + 30 * s), 'sans_med', GOLD2, a * 0.8)
        f.text('小巷思维', W / 2, 170, 62, 'serif_black', RED, a, t0=150.0, stag=0.06, glow=.4, mode='E')
        f.text('只有前进或后退 · 非成即败', W / 2, 245, 34, 'sans_light', WHITE, a, t0=150.4, stag=0.03)
    else:
        dt = t - sh
        for q0, q1, c, d, v, w, ww in shards():
            r = v * (1 - math.exp(-2.6 * dt)) / 2.6
            ang = w * dt * 0.4
            ox, oy = d[0] * r, d[1] * r
            def rot(q):
                x, y = q[0] - c[0], q[1] - c[1]
                return (c[0] + ox + x * math.cos(ang) - y * math.sin(ang), c[1] + oy + x * math.sin(ang) + y * math.cos(ang))
            f.line(rot(q0), rot(q1), lerpc(RED, GOLD, cl(dt * 2)), a * ww * (1 - cl(dt / 1.3)) * 0.9, 2)
        hy = keys(t, [(sh, 980.0), (sh + 1.2, 560.0)])
        pa = env(t, sh, 157.5, 0.4, 0.8)
        plain(f, t, pa, hy)
        burst(f, t, sh, W / 2, 540, [TEAL, CYAN, GOLD2, WHITE, PINK, VIOLET], 5, 600, 1500, 1.0, 2.4, 1.0)
        b = env(t, 152.3, 156.34, 0.3, 0.4)
        f.text('大平原思维', W / 2, 170, 62, 'serif_black', WHITE, b, t0=152.3, stag=0.06, grad=[TEAL, CYAN, GOLD2], mode='E', glow=.45)
        f.text('方向很多 · 路径很多 · 选择很多', W / 2, 245, 34, 'sans_light', WHITE, b, t0=152.7, stag=0.03)
        c = env(t, 154.22, 156.34, 0.3, 0.4)
        f.text('这条路走不通，不代表人生走不通。', W / 2, 380, 48, 'serif_med', GOLD2, c, t0=154.22, stag=0.04, glow=.3, mode='O')

HTERMS = [('低执念', TEAL), ('高行动力', ORANGE), ('弹性预期', CYAN), ('情绪调节能力', VIOLET), ('接受无常', PINK)]

def aurora(f, t, a):
    for k, col in enumerate([TEAL, VIOLET, GREEN, CYAN]):
        pts = []
        for x in np.linspace(-50, W + 50, 60):
            y = 760 + k * 55 + 90 * math.sin(x * 0.003 + t * 0.4 + k * 1.3) + 40 * math.sin(x * 0.009 - t * 0.7 + k)
            pts.append((x, y))
        p = (np.asarray(pts) * 16).astype(np.int32).reshape(-1, 1, 2)
        tmp = np.zeros((H // 4, W // 4), np.uint8)
        cv2.polylines(tmp, [(p // 4)], False, 255, 6, cv2.LINE_AA, 4)
        m = cv2.GaussianBlur(tmp.astype(np.float32) / 255, (0, 0), 6)
        m = cv2.resize(m, (W, H))
        f.B += m[..., None] * np.array(col, np.float32) * a * 0.32

def sc_happy(f, t):
    if not (156.2 < t < 165.0): return
    a = env(t, 156.34, 164.85, 0.3, 0.35)
    aurora(f, t, a)
    toks = [('幸福', GOLD2, False), ('=', GOLD, False)]
    app = [156.34, 156.6]
    for i, (s, col) in enumerate(HTERMS):
        if i: toks.append(('+', GOLD, False)); app.append(157.4 + i * 1.066 - 0.25)
        toks.append((s, col, True)); app.append(157.4 + i * 1.066)
    fy = keys(t, [(162.4, 470.0), (163.0, 360.0)])
    tokens(f, toks, W / 2, fy, 44, a, gap=0.3, appear=app)
    for i in range(5):
        ti = app[2 + 2 * i]
        if 0 < t - ti < 1.0:
            burst(f, t, ti, W / 2 - 700 + i * 350, fy, [HTERMS[i][1], WHITE], 6, 160, 420, 0.5, 3.5, 0.9)
    b = env(t, 162.73, 164.85, 0.25, 0.35)
    tokens(f, [('痛苦是乘法，', RED, False), ('幸福是加法。', GOLD2, False)], W / 2, 560, 78, b, gap=0.1, pill=False,
           appear=[162.73, 163.2])
    f.text('乘法里一项失控就全盘失衡；加法里，每一项都能一点一点练出来。', W / 2, 680, 30, 'sans_light', WHITE, b, t0=163.4, stag=0.018)

def sc_notbut(f, t):
    if not (164.7 < t < 171.4): return
    a = env(t, 164.85, 171.22, 0.3, 0.35)
    flow(f, t, a * 0.45, [GOLD, GOLD2, ORANGE, PINK, GOLD, WHITE], 60, n=1200, rise=1.0)
    rows = [(164.85, '我可以想要，', '但不要求世界必须满足我。'), (166.97, '我尽力提高胜率，', '但接受结果的随机性。'),
            (169.10, '我在乎，', '但不让它摧毁我的内在秩序。')]
    for i, (ta, p1, p2) in enumerate(rows):
        later = [r[0] for r in rows[i + 1:]]
        dim = 1.0
        for tl in later:
            dim -= 0.32 * eo((t - tl) / 0.4)
        ra = a * dim * eo((t - ta) / 0.3)
        if ra <= 0: continue
        y = 390 + i * 150
        tokens(f, [(p1, WHITE, False), (p2, GOLD2, False)], W / 2, y, 54, ra, gap=0.05, pill=False, appear=[ta, ta + 0.45],
               fnt='serif_black')

def sc_epilogue(f, t):
    if not (171.1 < t < 180): return
    a = env(t, 171.22, 175.47, 0.3, 0.4)
    flow(f, t, a * 0.55, [GOLD, GOLD2, ORANGE, GOLD, GOLD2, WHITE], 50, n=1400, rise=1.2)
    f.text('最好的状态', W / 2, 400, 30, 'sans_light', GREY, a, track=0.4, t0=171.3)
    phr = ['心中有方向', '手上有行动', '结果随缘', '内心不乱']
    ts = [171.22, 172.29, 173.35, 174.41]
    sizes = 62
    ws = [text_width(p, 'serif_black', sizes) for p in phr]
    sep = 70
    x = W / 2 - (sum(ws) + sep * 3) / 2
    for i, (p, w) in enumerate(zip(phr, ws)):
        f.text(p, x + w / 2, 540, sizes, 'serif_black', GOLD2, a * eo((t - ts[i]) / 0.3), t0=ts[i], stag=0.05,
               grad=[GOLD2, GOLD], mode='E', glow=.5)
        if i < 3:
            f.glow((x + w + sep / 2, 540), 4, GOLD2, a * eo((t - ts[i + 1]) / 0.3), 'E')
        x += w + sep
    # end card
    e = env(t, 175.47, 181, 0.8, 0.1)
    if e > 0:
        m, rgb = END_EMB
        hgt = m.shape[0]
        X0, Y0 = int(W / 2 - hgt / 2), int(410 - hgt / 2)
        sc = eo((t - 175.47) / 1.0)
        f.over.append((m, X0, Y0, rgb, e * sc))
        f.B[Y0:Y0 + hgt, X0:X0 + hgt] += (m * e * 0.5)[..., None] * rgb
        f.glow((W / 2, 410), 200, GOLD, e * 0.25, 'B')
        f.text('巴芒价值', W / 2, 640, 112, 'serif_black', GOLD2, e, t0=175.7, stag=0.12, dur=0.6,
               grad=[GOLD2, GOLD, GOLDD], mode='O', glow=.5)
        f.text('来之则安 · 去之则顺', W / 2, 760, 34, 'sans_light', lerpc(GREY, WHITE, .4), e, track=0.3, t0=176.6, stag=0.05)
        burst(f, t, 175.6, W / 2, 410, [GOLD, GOLD2, ORANGE, WHITE], 7, 500, 900, 1.6, 1.6, 0.8)


SCENES = [sc_hook, sc_title, sc_brain, sc_gap, sc_chem, sc_munger, sc_formula, sc_cases, sc_question, sc_munger_quote,
          sc_elastic, sc_layer1, sc_layer2, sc_layer3, sc_alley, sc_happy, sc_notbut, sc_epilogue]

def render(i):
    t = i / FPS
    f = Frame(t)
    bg = bg_at(t)
    draw_stars(f, t)
    for s in SCENES:
        s(f, t)
    shockwaves(f, t)
    # alarm shake on the red impact
    if 35.19 <= t < 35.7:
        k = math.exp(-(t - 35.19) / 0.12)
        f.shake = (int(round(7 * k * math.sin(t * 90))), int(round(9 * k * math.cos(t * 77))))
    draw_chrome(f, t)
    img = finish(f, bg, bloom_k=1.0 + 0.3 * beat_pulse(t) * energy(t), vignette=VIGNETTE)
    fade = cl(t / 1.0) * (1 - eio((t - 178.6) / 1.4))
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
            if (i - a) % 150 == 0: print(path, i, flush=True)
        p.stdin.close(); p.wait()
