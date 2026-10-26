"""投资的教训 —— 无配音动态视觉短片（音乐 + 动态图形 + 关键文字 + 数据可视化）。

全片 296 秒，所有分镜对齐到配乐的 120 BPM 小节线：
  partA 的小节线 = 0.06 + 2k 秒；partB 从 135.96s 接入，小节线 = 136.06 + 2k 秒。
"""
import math, os, sys
import numpy as np, cv2
from engine import *
from engine import glitch

DUR = 296.0
NFR = int(DUR * FPS)


# ============================================================== music grid
def _beats():
    a = 0.06 + 0.5 * np.arange(0, 272)                     # partA: 120 BPM
    b = 135.96 + 0.1005 + (60 / 120.04) * np.arange(0, 320)  # partB
    return np.concatenate([a[a < 136.0], b[b < DUR]])
BEATS = _beats()

T_PEAK, T_CRASH, T_TITLE = 16.06, 18.0, 24.06
T_FP, T_L1, T_L2, T_L3C, T_L3, T_L4 = 32.06, 48.06, 96.06, 136.06, 144.06, 176.06
T_STOP, T_PSY, T_SYS, T_FIN, T_END = 208.26, 211.76, 228.06, 260.06, 286.06

IMPACTS = [  # time, strength, colour
    (T_PEAK, 0.55, GOLD), (T_TITLE, 1.0, GOLD2), (T_FP, 0.3, CYAN), (T_L1, 0.6, ORANGE), (60.06, 0.45, RED),
    (T_L2, 0.6, CYAN), (T_L3, 1.0, MAGENTA), (T_L4, 0.7, ORANGE), (204.06, 0.6, RED), (T_SYS, 0.45, GOLD),
    (T_FIN, 1.0, GOLD), (T_END, 0.5, C(110, 175, 255))]
RISERS = [(22.2, T_TITLE), (140.06, T_L3), (256.06, T_FIN)]
ENERGY = [(0, .35), (14, .7), (16.06, .8), (18, .1), (23.9, .1), (24.06, 1), (116, 1), (118, .35), (135.5, .3),
          (144.06, 1), (208.2, 1), (208.3, 0), (211.7, 0), (212, .35), (227.9, .4), (228.06, .7), (259.9, .8),
          (260.06, 1), (284, 1), (288, .4), (296, .2)]

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


# ============================================================== stars / nebula / vignette
RNG = np.random.default_rng(2026)
NST = 1300
ST_X = RNG.uniform(-1.8, 1.8, NST); ST_Y = RNG.uniform(-1.1, 1.1, NST); ST_Z0 = RNG.uniform(0, 1, NST)
ST_COL = np.array([lerpc(WHITE, [CYAN, GOLD2, WHITE, VIOLET, PINK][i % 5], 0.4) for i in range(NST)], np.float32)

def star_speed(t):
    v = 0.03 + 0.05 * energy(t)
    for ti, k, _ in IMPACTS:
        if t >= ti: v += k * 1.5 * math.exp(-(t - ti) / 0.55)
    for a, b in RISERS:
        if a <= t <= b: v += 0.4 * ei((t - a) / (b - a))
    if T_CRASH <= t < 19.6: v -= 0.6 * math.sin(math.pi * (t - T_CRASH) / 1.6)  # fall backwards
    return v

_ts = np.arange(NFR + 2) / FPS
ST_S = np.concatenate([[0], np.cumsum([star_speed(x) / FPS for x in _ts])])

def star_dist(t):
    return ST_S[min(int(t * FPS), NFR)]

NB1 = fbm(512, 288, 11, 6, 3); NB2 = fbm(512, 288, 22, 6, 3); NB3 = fbm(512, 288, 33, 5, 5)
BGK = [  # time, colour A, colour B, intensity
    (0, (60, 40, 10), (60, 15, 50), .55), (12, (130, 70, 10), (120, 20, 60), .9), (16.06, (190, 90, 15), (160, 25, 70), 1.3),
    (17.9, (150, 60, 15), (130, 20, 60), 1.0), (18.6, (10, 80, 50), (90, 10, 20), .9), (20, (5, 30, 25), (40, 5, 10), .35),
    (23.9, (10, 15, 40), (20, 10, 40), .4), (24.3, (150, 100, 30), (25, 70, 170), 1.35), (28, (40, 60, 140), (110, 70, 25), 1.0),
    (32, (20, 60, 130), (60, 25, 120), .95), (47.9, (20, 60, 130), (60, 25, 120), .95),
    (48.3, (170, 70, 15), (90, 20, 120), 1.25), (52, (110, 50, 20), (60, 20, 110), 1.0), (59.9, (110, 50, 20), (60, 20, 110), 1.0),
    (60.3, (170, 20, 40), (80, 10, 60), 1.2), (64, (110, 30, 40), (50, 20, 90), .95), (68, (40, 40, 120), (100, 50, 20), 1.0),
    (80, (40, 40, 120), (100, 50, 20), 1.0), (82, (25, 50, 110), (110, 30, 50), 1.0), (95.9, (90, 60, 20), (40, 30, 90), .95),
    (96.3, (15, 100, 140), (120, 25, 120), 1.25), (100, (15, 70, 110), (100, 20, 100), 1.0), (116, (15, 60, 100), (80, 20, 90), .9),
    (118, (15, 30, 70), (40, 20, 70), .6), (135.5, (15, 25, 60), (35, 15, 60), .5),
    (140, (60, 10, 50), (20, 10, 60), .6), (144.3, (180, 20, 110), (60, 20, 160), 1.4), (150, (120, 20, 80), (50, 20, 120), 1.05),
    (152.5, (40, 90, 60), (60, 15, 60), 1.0), (156, (110, 20, 50), (40, 20, 100), 1.0), (164, (60, 30, 120), (120, 30, 40), 1.0),
    (175.9, (60, 30, 120), (120, 30, 40), 1.0), (176.3, (180, 80, 15), (120, 20, 40), 1.3), (180, (110, 55, 20), (70, 20, 80), 1.0),
    (192, (110, 55, 20), (70, 20, 80), 1.0), (192.5, (20, 100, 70), (120, 15, 30), 1.0), (196, (120, 40, 20), (60, 20, 70), 1.0),
    (204, (150, 20, 30), (20, 80, 60), 1.2), (208.2, (150, 20, 30), (20, 80, 60), 1.2), (208.3, (5, 5, 10), (5, 5, 10), .1),
    (211.5, (5, 5, 10), (5, 5, 10), .1), (213, (20, 30, 80), (50, 20, 80), .6), (227.8, (30, 40, 90), (70, 50, 30), .7),
    (228.3, (150, 100, 25), (20, 90, 110), 1.15), (244, (110, 80, 25), (20, 80, 110), 1.0), (256, (140, 100, 30), (40, 60, 140), 1.1),
    (260.3, (200, 130, 30), (150, 60, 20), 1.45), (270, (140, 90, 25), (60, 40, 120), 1.05), (276, (150, 100, 30), (120, 60, 20), 1.0),
    (286.3, (40, 70, 150), (110, 80, 25), .9), (296, (20, 25, 50), (30, 20, 10), .4)]

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


# ============================================================== 品牌角标（见仓库根目录 brand/）
sys.path.insert(0, os.path.join(HERE, '..', '..', 'brand'))
from brand import Hud, load_logo as brand_logo
HUD = Hud()
END_LOGO = brand_logo(220)

def draw_hud_post(img, t, a):
    """在 tone-map 之后合成右上角角标（颜色与品牌稿一致）"""
    if a <= 0.003: return img
    h = HUD.y0 + HUD.h + HUD.P + 2
    reg = img[:h].astype(np.float32) / 255
    HUD.draw(reg, t, a)
    img[:h] = (np.clip(reg, 0, 1) * 255 + 0.5).astype(np.uint8)
    return img

CHAPTERS = [(0, '序', '序章', 'PROLOGUE'), (T_FP, '00', '第一性原理', 'FIRST PRINCIPLES'),
            (T_L1, '01', '周期与估值', 'CYCLE & VALUATION'), (T_L2, '02', '能力圈与证伪', 'CIRCLE & FALSIFICATION'),
            (T_L3C, '03', '仓位与相关性', 'POSITION & CORRELATION'), (T_L4, '04', '题材与监管', 'THEMES & REGULATION'),
            (T_STOP, '05', '心理陷阱', 'THE MIND TRAP'), (T_SYS, '06', '决策系统', 'THE SYSTEM'),
            (T_FIN, '终', '总纲', 'EPILOGUE'), (T_END, '', '', '')]

def draw_chrome(f, t):
    for (a, num, zh, en), (b, *_r) in zip(CHAPTERS, CHAPTERS[1:]):
        if a <= t < b and a > 0:
            al = env(t, a, b, 0.6, 0.4) * 0.9
            fn = 'orb' if num.isdigit() else 'serif_black'
            f.text(num, 70, 62, 30, fn, GOLD, al, 'l', mode='O')
            x = 70 + text_width(num, fn, 30) + 16
            f.line((x, 50), (x, 76), GOLD, al * 0.6, 1)
            f.text(zh, x + 16, 56, 24, 'sans_med', WHITE, al * 0.92, 'l', mode='O')
            f.text(en, x + 16, 84, 14, 'corm', GREY, al * 0.8, 'l', track=0.35, mode='O')
    pa = 0.5 * env(t, 26.0, T_END - 0.4, 1.0, 0.6)
    if pa > 0:
        x0, x1, y = 140, 1780, 1040
        f.L[y:y + 1, x0:x1] += np.float32(0.10 * pa)
        xc = x0 + (x1 - x0) * t / T_END
        f.L[y:y + 1, x0:int(xc)] += np.array(GOLD, np.float32) * 0.35 * pa
        for (a, num, zh, en) in CHAPTERS[:-1]:
            xx = int(x0 + (x1 - x0) * a / T_END)
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
    b = np.clip((1.05 - z) ** 2.2, 0, 1) * (0.5 + 0.35 * beat_pulse(t, .18) * energy(t))
    if T_STOP <= t < 211.5: b = b * 0.15
    tw = 0.75 + 0.25 * np.sin(t * 3 + ST_X * 40)
    f.splat(sx, sy, ST_COL, b * tw * 0.9, 'L')
    near = z < 0.25
    f.splat(sx[near], sy[near], ST_COL[near], b[near] * 0.8, 'E')
    v = abs(star_speed(t))
    if v > 0.25:
        z2 = z + math.copysign(min(v * 0.06, 0.25), star_speed(t))
        sx2 = W / 2 + ST_X / z2 * fx; sy2 = H / 2 + ST_Y / z2 * fx
        al = cl((v - 0.25) / 1.0)
        idx = np.where((z < 0.7) & (abs(sx - W / 2) < W) & (abs(sy - H / 2) < H))[0][:450]
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

def burst(f, t, t0, cx, cy, cols, seed=0, n=700, speed=1500, life=1.4, drag=2.4, a=1.0, size=1, grav=0.0):
    dt = t - t0
    if dt < 0 or dt > life * 2.4: return
    th, v, lf, ci = BURST[seed % 8]
    th, v, lf, ci = th[:n], v[:n], lf[:n], ci[:n]
    cc = np.array(cols, np.float32)[ci % len(cols)]
    for k in range(4):
        d = max(dt - k * 0.018, 0)
        r = speed * v * (1 - math.exp(-drag * d)) / drag
        al = np.exp(-d / (life * lf)) * a * (1 - k * 0.22)
        xs = cx + r * np.cos(th); ys = cy + r * np.sin(th) * 0.8 + grav * d * d
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

def flow(f, t, a, cols, speed=140, n=2200, rise=0.0):
    if a <= 0.003: return
    cc = np.array(cols, np.float32)[FL_C[:n] % len(cols)]
    for k in range(5):
        tt = t - k * 0.035
        x = (FL_X[:n] + FL_S[:n] * speed * tt) % (W + 300) - 150
        y = FL_Y[:n] + 70 * np.sin(x * 0.0035 + FL_P[:n] + tt * 0.5) + 28 * np.sin(x * 0.011 - tt * 0.9 + FL_P[:n] * 2)
        y = (y - rise * tt * FL_S[:n] * 60) % (H + 120) - 60
        al = a * (0.55 + 0.45 * np.sin(FL_P[:n] + t)) * (1 - k * 0.18)
        f.splat(x, y, cc, al * 2.4, 'E')

def chip(f, s, cx, cy, size, col, a, fnt='sans_med', fill=0.10, sc=1.0):
    if a <= 0.003: return
    size = max(8, int(round(size * sc)))
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

def pop(t, t0, d=0.35):
    """0→1 with overshoot, for scale-in"""
    p = cl((t - t0) / d)
    return eo(p), 1 + 0.4 * (1 - eback(p, 2.4))

def slam(f, t, s, x, y, size, t0, col=WHITE, a=1.0, fnt='serif_black', grad=None, glow=0.5, mode='E', anchor='m'):
    """text that slams in from 1.6x scale with a flash"""
    p = cl((t - t0) / 0.28)
    if p <= 0: return
    sc = 1 + 0.6 * (1 - eo(p))
    sz = max(8, int(round(size * sc)))
    f.text(s, x, y, sz, fnt, col, a * eo(p), anchor, grad=grad, mode=mode, glow=glow)

def caption(f, t, s, y, t0, t1, size=40, col=WHITE, fnt='sans_med', glow=0.15, x=W / 2, anchor='m', stag=0.03):
    a = env(t, t0, t1, 0.35, 0.4)
    if a > 0: f.text(s, x, y, size, fnt, col, a, anchor, t0=t0, stag=stag, glow=glow)

def card(f, t, t0, t1, num, title, sub, col, col2):
    """chapter card: giant number + title + rule"""
    a = env(t, t0, t1, 0.08, 0.45)
    if a <= 0: return
    burst(f, t, t0, W / 2, 420, [col, col2, WHITE, GOLD2], 3, 800, 1500, 1.2, 2.3, 0.9, 2)
    p, sc = pop(t, t0, 0.4)
    f.text('LESSON', W / 2, 270, 26, 'corm', lerpc(col, WHITE, .4), a * p, track=1.0, t0=t0 + 0.1, stag=0.03)
    f.text(num, W / 2, 420, int(230 * sc), 'orb', col, a * p, grad=[col2, col, lerpc(col, WHITE, .5)], mode='E', glow=0.7)
    w = 560 * eo((t - t0 - 0.3) / 0.7)
    f.line((W / 2 - w, 585), (W / 2 + w, 585), col, a * 0.7, 1)
    f.glow((W / 2, 585), 60, col, a * 0.3 * eo((t - t0) / 0.6), 'B')
    f.text(title, W / 2, 680, 76, 'serif_black', WHITE, a, t0=t0 + 0.3, stag=0.05, dur=0.4, rise=30, mode='E', glow=0.35)
    f.text(sub, W / 2, 780, 24, 'corm', lerpc(col, WHITE, .5), a * 0.9, track=0.5, t0=t0 + 0.8, stag=0.02)

def counter_text(v, fmt):
    return fmt.format(v)

def arrow(f, p0, p1, col, a, th=2, head=12):
    f.line(p0, p1, col, a, th)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for s in (-1, 1):
        f.line(p1, (p1[0] - head * math.cos(ang + s * 0.45), p1[1] - head * math.sin(ang + s * 0.45)), col, a, th)

def comet(f, pts_fn, u, col, a, n=14, du=0.012):
    for k in range(n):
        x, y = pts_fn(u - k * du)
        f.glow((x, y), 4 + 6 * (1 - k / n), lerpc(col, WHITE, 0.6 if k == 0 else 0), a * (1 - k / n) ** 1.5, 'E')
    x, y = pts_fn(u)
    f.glow((x, y), 22, col, a * 0.6, 'B')


# ============================================================== 序章：狂热与崩塌  (0 – 24.06)
_PR = np.random.default_rng(8)
NPTS = 240
_u = np.linspace(0, 1, NPTS)
_noise = np.cumsum(_PR.normal(0, 1, NPTS)); _noise -= np.linspace(_noise[0], _noise[-1], NPTS)
PRICE_X = 140 + _u * 1500
PRICE_Y = 860 - 600 * (np.exp(3.4 * _u) - 1) / (np.exp(3.4) - 1) - _noise * 9 * (0.3 + _u)
PRICE_Y[-1] = 250
CRASH_X = np.linspace(PRICE_X[-1], 1790, 60)
_cu = np.linspace(0, 1, 60)
CRASH_Y = 250 + (920 - 250) * (1 - (1 - _cu) ** 3) ** 0.6 + _PR.normal(0, 8, 60) * (1 - _cu)
CRASH_Y[-12:] = 920 + _PR.normal(0, 3, 12)

HYPE = [(2.06, '景气高峰', 520, 640, GOLD), (4.06, '业绩爆发', 820, 560, ORANGE), (6.06, '估值 60 倍', 1080, 470, MAGENTA),
        (8.06, '这次不一样', 760, 330, GOLD2), (10.06, '满仓科技', 1330, 520, RED), (12.06, '再加一点', 1120, 260, PINK),
        (14.06, '永远上涨', 1450, 360, GOLD)]

def rise_progress(t):
    return cl((t - 0.3) / (T_PEAK - 0.3)) ** 1.25

def sc_open(f, t):
    if t > 24.3: return
    a = env(t, 0.0, 23.0, 0.8, 1.2)
    crash = cl((t - T_CRASH) / 1.5)
    # grid
    for k in range(9):
        y = 180 + k * 95
        f.line((120, y), (1800, y), CYAN if crash == 0 else GREEN, a * 0.07, 1)
    off = (t * 60) % 120
    for k in range(15):
        x = 120 + k * 120 - off
        if x > 120: f.line((x, 160), (x, 940), CYAN, a * 0.05, 1)
    p = rise_progress(t)
    m = max(2, int(p * (NPTS - 1)) + 1)
    pts = np.stack([PRICE_X[:m], PRICE_Y[:m]], 1)
    hot = lerpc(GOLD, RED, cl((p - 0.55) / 0.45))
    fade_line = 1 - 0.8 * cl((t - 19.4) / 1.2)
    # fill under curve
    if m > 3:
        poly = np.vstack([pts, [[pts[-1, 0], 940], [pts[0, 0], 940]]])
        f.fillpoly(poly, hot, a * 0.07 * fade_line, 'L')
    f.neon(pts, hot, a * fade_line, 3, 16)
    if crash > 0:
        n2 = max(2, int(eo(crash) * 59) + 1)
        cpts = np.stack([CRASH_X[:n2], CRASH_Y[:n2]], 1)
        f.neon(cpts, GREEN, a, 4, 22)
        tip = cpts[-1]
    else:
        tip = pts[-1]
    col_tip = GREEN if crash > 0 else hot
    f.glow(tuple(tip), 30 + 20 * beat_pulse(t), col_tip, a * 0.9, 'B')
    f.glow(tuple(tip), 5, WHITE, a, 'E')
    f.line((tip[0], 150), (tip[0], 950), col_tip, a * 0.18, 1)
    # rising gold dust
    flow(f, t, a * 0.35 * (1 - crash) * (0.4 + 0.6 * p), [GOLD, GOLD2, ORANGE, GOLD, RED, WHITE], 120, n=1400, rise=2.0 + 4 * p)
    # hype chips
    for i, (t0, s, x, y, col) in enumerate(HYPE):
        if t < t0: continue
        al, sc = pop(t, t0, 0.35)
        dy = 0.0
        if t > T_CRASH:       # fall with the crash
            d = t - T_CRASH - i * 0.05
            dy = max(d, 0) ** 2 * 700
            al *= 1 - cl(d / 1.4)
        chip(f, s, x, y + dy, 34, col if t < T_CRASH else GREEN, al * a, 'sans_black', 0.14, sc)
        burst(f, t, t0, x, y, [col, GOLD2, WHITE], i, 260, 700, 0.7, 2.6, 0.8)
    # account counter
    if t < T_CRASH:
        v = 186 * (p ** 1.3)
        s, col = '+%d%%' % round(v), lerpc(GOLD, RED, cl(p * 1.2))
    else:
        v = 186 + (-8 - 186) * eo(crash)
        s, col = ('%+d%%' % round(v)), lerpc(RED, GREEN, cl(crash * 2))
    ca = a * env(t, 0.5, 23.0, 0.6, 1.5)
    f.text('账户收益', 160, 300, 26, 'sans_med', GREY, ca * 0.9, 'l')
    f.text(s, 160, 370, int(84 + 30 * p * (t < T_CRASH)), 'orb', col, ca, 'l', mode='E', glow=0.6)
    if t >= T_CRASH:
        dd = 68 * eo(crash)
        f.text('最大回撤', 160, 470, 26, 'sans_med', GREY, ca * 0.9 * eo(crash), 'l')
        f.text('-%d%%' % round(dd), 160, 530, 64, 'orb', GREEN, ca * eo(crash), 'l', mode='E', glow=0.5)
    caption(f, t, '当所有人都在狂欢……', 160, 13.06, 17.6, 46, WHITE, 'serif_med', x=140, anchor='l', stag=0.06)
    # silence after the crash
    a2 = env(t, 19.6, 23.2, 0.4, 0.5)
    if a2 > 0:
        f.text('没有横盘。没有反复。', W / 2, 430, 64, 'serif_black', WHITE, a2, t0=19.6, stag=0.09, dur=0.5, glow=0.2)
        f.text('一次性，回撤到底部。', W / 2, 540, 64, 'serif_black', lerpc(GREEN, WHITE, 0.3), a2, t0=20.7, stag=0.09, dur=0.5, glow=0.3)
    implode(f, t, 22.2, T_TITLE, W / 2, H / 2, [GOLD, GOLD2, CYAN, ORANGE, WHITE, MAGENTA], 1.0)

def glitch_amt(t):
    k = 0.0
    if T_CRASH <= t < 19.9: k = max(k, 0.9 * (1 - cl((t - T_CRASH) / 1.9)) * (0.6 + 0.4 * math.sin(t * 40)))
    if 16.06 <= t < 16.4: k = max(k, 0.5 * (1 - (t - 16.06) / 0.34))
    for t0 in (204.06, 206.06):
        if t0 <= t < t0 + 0.5: k = max(k, 0.8 * (1 - (t - t0) / 0.5))
    if 207.3 <= t < T_STOP: k = max(k, 0.3 + 0.6 * (t - 207.3))
    if 152.06 <= t < 152.5: k = max(k, 0.5 * (1 - (t - 152.06) / 0.44))
    return k


# ============================================================== 标题 (24.06 – 32.06)
def sc_title(f, t):
    if not (24.0 < t < 32.4): return
    burst(f, t, T_TITLE, W / 2, H / 2, [GOLD, GOLD2, CYAN, ORANGE, WHITE, MAGENTA], 0, 900, 1800, 1.3, 2.2, 1.0, 2)
    a = env(t, T_TITLE, 31.9, 0.05, 0.5)
    f.text('LESSONS  OF  INVESTING', W / 2, 330, 28, 'corm', GOLD2, a * 0.85, track=0.5, t0=24.4, stag=0.02)
    f.text('投资的教训', W / 2, 470, 176, 'serif_black', WHITE, a, t0=T_TITLE, stag=0.06, dur=0.35, rise=50,
           grad=[GOLD2, GOLD, ORANGE, MAGENTA], mode='E', glow=0.6)
    w = 560 * eo((t - 24.8) / 0.8)
    if w > 300:
        f.line((W / 2 - w, 610), (W / 2 - 300, 610), GOLD, a * 0.8, 1)
        f.line((W / 2 + 300, 610), (W / 2 + w, 610), GOLD, a * 0.8, 1)
    f.text('一次惨痛回撤的第一性原理复盘', W / 2, 610, 34, 'sans_light', GOLD2, a, t0=25.0, stag=0.04)
    tags = [('估值纪律', ORANGE), ('认知纪律', CYAN), ('仓位纪律', MAGENTA), ('风险纪律', RED)]
    for i, (s, col) in enumerate(tags):
        t0 = 28.06 + i * 0.5
        al, sc = pop(t, t0)
        chip(f, s, W / 2 + (i - 1.5) * 300, 760, 34, col, a * al, 'sans_black', 0.12, sc)
        burst(f, t, t0, W / 2 + (i - 1.5) * 300, 760, [col, WHITE], i + 2, 220, 600, 0.6, 2.5, 0.8)


# ============================================================== 00 第一性原理 (32.06 – 48.06)
def price_rect(f, x0, yb, wpx, hpx, col, a, lab_e=None, lab_pe=None, lab_area=None, area_col=WHITE, grid=True):
    """price = EPS × PE drawn as a rectangle (width = 盈利, height = 估值)"""
    if a <= 0.003: return
    x1, y1 = x0 + wpx, yb - hpx
    f.fillpoly([(x0, yb), (x1, yb), (x1, y1), (x0, y1)], col, a * 0.16, 'L')
    if grid:
        for k in range(1, 8):
            yy = yb - hpx * k / 8
            f.line((x0, yy), (x1, yy), col, a * 0.12, 1)
            xx = x0 + wpx * k / 8
            f.line((xx, yb), (xx, y1), col, a * 0.12, 1)
    f.neon([(x0, yb), (x1, yb), (x1, y1), (x0, y1)], col, a, 3, 14, closed=True)
    if lab_e: f.text(lab_e, x0 + wpx / 2, yb + 44, 30, 'sans_med', CYAN, a, mode='L', glow=0.3)
    if lab_pe: f.text(lab_pe, x0 - 24, yb - hpx / 2, 30, 'sans_med', MAGENTA, a, 'r', mode='L', glow=0.3)
    if lab_area: f.text(lab_area, x0 + wpx / 2, yb - hpx / 2, 46, 'sans_black', area_col, a, mode='E', glow=0.5)

def sc_first(f, t):
    if not (31.8 < t < 48.3): return
    a = env(t, T_FP, 47.9, 0.4, 0.4)
    # phase 1: P = E × PE (32 – 40)
    a1 = env(t, T_FP, 40.0, 0.4, 0.35)
    if a1 > 0:
        f.text('回到第一性原理', 140, 230, 30, 'sans_light', GOLD2, a1, 'l', track=0.3, t0=T_FP)
        f.text('股价', 140, 330, 84, 'serif_black', WHITE, a1, 'l', t0=32.3, glow=0.3)
        f.text('= 每股盈利 × 市盈率', 330, 330, 64, 'serif_black', WHITE, a1, 'l', t0=32.7, stag=0.05,
               grad=[CYAN, VIOLET, MAGENTA], mode='E', glow=0.4)
        f.text('P  =  E  ×  PE', 140, 430, 44, 'mono', GREY, a1 * 0.9, 'l', t0=33.3, stag=0.03)
        # animated rectangle: double-click then double-kill
        E = keys(t, [(33.06, 3.0), (34.06, 5.0), (36.06, 9.0), (37.06, 9.0), (38.06, 4.0), (40, 4.0)])
        P = keys(t, [(33.06, 4.0), (35.06, 6.0), (36.56, 10.0), (37.06, 10.0), (38.56, 5.0), (40, 5.0)])
        hot = cl((E * P - 12) / 78)
        col = lerpc(GOLD, RED, cl((t - 37.3) / 0.8)) if t > 37.06 else lerpc(CYAN, GOLD, hot)
        price_rect(f, 1080, 880, E * 66, P * 60, col, a1 * eo((t - 32.6) / 0.6), '盈利 E', '估值 PE',
                   '价格 P', WHITE)
        lab = '戴维斯双击' if t < 37.06 else '戴维斯双杀'
        lc = GOLD if t < 37.06 else RED
        la = env(t, 35.06, 39.9, 0.2, 0.3) * (1 - 0.7 * env(t, 36.95, 37.3, 0.05, 0.05))
        f.text(lab, 140, 600, 72, 'serif_black', lc, la, 'l', mode='E', glow=0.6)
        f.text('盈利 ↑ × 估值 ↑ ＝ 股价飞涨' if t < 37.06 else '盈利 ↓ × 估值 ↓ ＝ 股价崩塌',
               140, 690, 34, 'sans_med', lerpc(lc, WHITE, .5), la, 'l')
    # phase 2: return decomposition (40 – 44)
    a2 = env(t, 40.06, 44.0, 0.3, 0.3)
    if a2 > 0:
        f.text('投资回报', W / 2, 330, 44, 'sans_light', GREY, a2, t0=40.06)
        toks = [('回报', WHITE, False), ('=', GREY, False), ('(1+盈利增长)', CYAN, True), ('×', GREY, False),
                ('(1+估值变化)', MAGENTA, True), ('−1', GREY, False)]
        tokens(f, toks, W / 2, 450, 54, a2, appear=[40.06, 40.3, 40.56, 40.8, 41.06, 41.3])
        e2 = env(t, 42.06, 44.0, 0.3, 0.3)
        f.text('例：盈利 +20%   ×   估值 −50%   =   ', W / 2 - 110, 610, 44, 'sans_med', WHITE, a2 * e2, t0=42.06, stag=0.02)
        slam(f, t, '−40%', W / 2 + 470, 610, 70, 42.8, RED, a2, 'sans_black')
        f.text('利润在增长，账户却可能大幅亏损', W / 2, 720, 36, 'sans_light', lerpc(RED, WHITE, .5), a2 * e2, t0=43.0, stag=0.03)
    # phase 3: three variables (44 – 48)
    a3 = env(t, 44.06, 47.9, 0.3, 0.4)
    if a3 > 0:
        f.text('账户回报  =  Σ  仓位  ×  个股回报', W / 2, 300, 50, 'serif_black', WHITE, a3, t0=44.06, stag=0.03, mode='E', glow=0.3)
        orbs = [('盈利', '周期决定分母', CYAN), ('估值', '情绪决定倍数', MAGENTA), ('仓位', '决定能否活下来', GOLD)]
        for i, (s, sub, col) in enumerate(orbs):
            t0 = 44.56 + i * 0.5
            al, sc = pop(t, t0)
            cx = W / 2 + (i - 1) * 420; cy = 560 + 10 * math.sin(t * 2 + i)
            r = 110 * sc
            f.glow((cx, cy), r * 0.8, col, a3 * al * 0.35 * (1 + 0.5 * bar_pulse(t)), 'B')
            f.circle((cx, cy), r, col, a3 * al, 3)
            f.circle((cx, cy), r * 0.8, col, a3 * al * 0.3, 1, g=True)
            f.text(s, cx, cy, int(56 * sc), 'serif_black', lerpc(col, WHITE, .5), a3 * al, mode='E', glow=0.4)
            f.text(sub, cx, cy + 170, 28, 'sans_light', lerpc(col, WHITE, .5), a3 * al)
        f.text('所有教训，都藏在这三个变量里', W / 2, 830, 40, 'sans_med', GOLD2, a3, t0=46.06, stag=0.05, glow=0.2)


# ============================================================== 01 周期与估值 (48.06 – 96.06)
def sc_l1_card(f, t):
    if 48.0 < t < 52.5:
        card(f, t, T_L1, 52.0, '01', '远离没有护城河的高估值周期股', 'CYCLICAL  ·  NO  MOAT  ·  HIGH  VALUATION', ORANGE, RED)

def sc_davis(f, t):
    if not (51.9 < t < 68.3): return
    a = env(t, 52.06, 68.0, 0.4, 0.4)
    f.text('戴维斯双杀', 140, 200, 60, 'serif_black', WHITE, a, 'l', t0=52.06, stag=0.06, grad=[ORANGE, RED], mode='E', glow=0.5)
    f.text('一家典型的周期性化工企业', 140, 270, 30, 'sans_light', GREY, a, 'l', t0=52.5, stag=0.03)
    E = keys(t, [(52.06, 0.0), (53.0, 20.0), (56.06, 20.0), (57.6, 8.0)])
    P = keys(t, [(52.06, 0.0), (53.4, 20.0), (58.06, 20.0), (59.6, 12.0)])
    kx, ky = 30, 24
    x0, yb = 320, 900
    f.poly([(x0, yb), (x0 + 20 * kx, yb), (x0 + 20 * kx, yb - 20 * ky), (x0, yb - 20 * ky)], GREY, a * 0.35 * cl((t - 56) / 0.5), 1, True)
    col = ORANGE if t < 56.06 else lerpc(ORANGE, RED, cl((t - 56.06) / 3.5))
    cap = E * P
    price_rect(f, x0, yb, max(E, 0.01) * kx, max(P, 0.01) * ky, col, a, '净利润 %.0f 亿' % E, 'PE %.0f 倍' % P,
               None)
    # market cap readout
    xc = x0 + E * kx / 2; yc = yb - P * ky / 2
    if E > 3:
        f.text('市值', xc, yc - 50, 26, 'sans_light', WHITE, a * 0.8)
        f.text('%d' % round(cap), xc, yc + 10, 72 if cap > 150 else 54, 'orb', WHITE, a, mode='E', glow=0.5)
        f.text('亿', xc + text_width('%d' % round(cap), 'orb', 72 if cap > 150 else 54) / 2 + 22, yc + 18, 26, 'sans_med', WHITE, a)
    # right column: the story
    rows = [(54.06, '景气高峰：利润 20 亿 × 20 倍 = 400 亿', GOLD), (56.06, '供给释放，价格下跌 → 利润回归 8 亿', ORANGE),
            (58.06, '市场重新定价 → 只给 12 倍', RED)]
    for t0, s, c in rows:
        f.text(s, 1060, 300 + (t0 - 54.06) / 2 * 70, 32, 'sans_med', lerpc(c, WHITE, .4), a, 'l', t0=t0, stag=0.02)
    if t >= 60.06:
        p, sc = pop(t, 60.06, 0.3)
        f.text('-76%', 1060, 600, int(170 * sc), 'orb', RED, a * p, 'l', mode='E', glow=0.8)
        f.text('400 亿  →  96 亿', 1070, 720, 40, 'sans_black', lerpc(RED, WHITE, .5), a * p, 'l')
    caption(f, t, '不需要破产，不需要造假，甚至仍在盈利——', 860, 62.06, 68.0, 38, WHITE, 'sans_med', x=1060, anchor='l', stag=0.03)
    caption(f, t, '只需要「业绩回归常态 + 估值收缩」。', 920, 64.06, 68.0, 38, GOLD2, 'sans_black', x=1060, anchor='l', stag=0.03)

CYCLE = ['高价格 · 高利润', '资本涌入', '产能扩张', '供给过剩', '价格暴跌', '产能出清']
def sc_cycle(f, t):
    if not (67.9 < t < 80.3): return
    a = env(t, 68.06, 80.0, 0.4, 0.4)
    move = eio((t - 74.06) / 1.2)
    cx, cy, R = lerp(W / 2, 600, move), 580, lerp(300, 270, move)
    f.text('周期股的长期利润，取决于供需，而不是短期增速', W / 2, 190, 40, 'serif_black', WHITE,
           a * (1 - move), t0=68.06, stag=0.03, glow=0.2)
    n = len(CYCLE)
    ang = lambda k: -math.pi / 2 + k * 2 * math.pi / n
    pos = [(cx + R * math.cos(ang(k)), cy + R * math.sin(ang(k)) * 0.86) for k in range(n)]
    path = lambda u: (cx + R * math.cos(-math.pi / 2 + u * 2 * math.pi), cy + R * math.sin(-math.pi / 2 + u * 2 * math.pi) * 0.86)
    ring = [path(u) for u in np.linspace(0, 1, 160)]
    f.neon(ring, VIOLET, a * 0.5 * eo((t - 68.06) / 1.0), 2, 10, closed=True)
    u = (t - 68.06) / 4.0
    comet(f, path, u % 1.0, GOLD, a, 18, 0.01)
    for k, s in enumerate(CYCLE):
        t0 = 68.06 + k * 0.5
        al, sc = pop(t, t0)
        hot = math.exp(-((u % 1.0 - k / n + 0.5) % 1.0 - 0.5) ** 2 / 0.003)
        col = [GOLD, ORANGE, ORANGE, RED, RED, CYAN][k]
        x, y = pos[k]
        f.glow((x, y), 30, col, a * al * (0.3 + 0.7 * hot), 'B')
        f.circle((x, y), 12 * sc, col, a * al, 3)
        dx = 1 if math.cos(ang(k)) > 0.1 else (-1 if math.cos(ang(k)) < -0.1 else 0)
        tx = x + dx * 34; ty = y + (0 if dx else (-44 if k == 0 else 44))
        f.text(s, tx, ty, int(32 * sc), 'sans_black', lerpc(col, WHITE, 0.4 + 0.4 * hot), a * al, 'l' if dx > 0 else ('r' if dx < 0 else 'm'),
               mode='E', glow=0.3 * hot)
    ca = env(t, 70.06, 80.0, 0.4, 0.4)
    f.text('供给', cx, cy - 30, 54, 'serif_black', WHITE, a * ca, mode='E', glow=0.3)
    f.text('能被约束吗？', cx, cy + 40, 40, 'serif_black', GOLD2, a * ca, mode='E', glow=0.3)
    # moats
    moats = ['稀缺资源 / 准入许可', '客户认证 · 高转换成本', '难以复制的工艺', '长期合同 · 稳定成本优势', '对手扩产受资本、资源、政策约束']
    if t > 74.3:
        f.text('值得付钱的护城河', 1080, 300, 44, 'serif_black', GOLD2, a, 'l', t0=74.6, glow=0.3)
        for i, s in enumerate(moats):
            t0 = 75.06 + i * 0.5
            al, sc = pop(t, t0)
            y = 400 + i * 84
            f.circle((1100, y), 16, TEAL, a * al, 2)
            if al > 0.5:
                f.line((1092, y), (1099, y + 7), TEAL, a * al, 3); f.line((1099, y + 7), (1110, y - 8), TEAL, a * al, 3)
            f.text(s, 1140, y, 34, 'sans_med', WHITE, a * al, 'l', t0=t0, stag=0.02)
        caption(f, t, '低谷能活下来，高峰有超额利润，扩产也抢不走优势', 860, 77.06, 80.0, 30, lerpc(TEAL, WHITE, .5), 'sans_light',
                x=1080, anchor='l', stag=0.02)

def sc_pe10(f, t):
    if not (79.9 < t < 96.3): return
    a = env(t, 80.06, 96.0, 0.4, 0.4)
    f.text('「10 倍 PE」，也可能很贵', W / 2, 190, 60, 'serif_black', WHITE, a, t0=80.06, stag=0.06, grad=[CYAN, GOLD, RED], mode='E', glow=0.4)
    f.text('同一家公司 · 市值 200 亿 · 三种利润假设', W / 2, 262, 30, 'sans_light', GREY, a, t0=80.6, stag=0.03)
    cols = [('顶峰利润', '20 亿', 10.0, CYAN, '看起来很便宜'), ('周期中枢利润', '8 亿', 25.0, GOLD, '真实的价格'),
            ('悲观利润', '3 亿', 66.7, RED, '低谷时的真相')]
    yb = 840
    shift = eio((t - 90.06) / 1.0)
    for i, (lab, prof, pe, col, note) in enumerate(cols):
        t0 = 82.06 + i * 2.0
        g = eo((t - t0) / 1.2)
        if t < t0: continue
        x = lerp(560 + i * 400, 300 + i * 240, shift)
        bw = lerp(200, 150, shift)
        h = pe * 7.0 * g
        f.fillpoly([(x - bw / 2, yb), (x + bw / 2, yb), (x + bw / 2, yb - h), (x - bw / 2, yb - h)], col, a * 0.22, 'L')
        f.neon([(x - bw / 2, yb), (x - bw / 2, yb - h), (x + bw / 2, yb - h), (x + bw / 2, yb)], col, a, 3, 14)
        f.glow((x, yb - h), 50, col, a * 0.35 * (1 + bar_pulse(t)), 'B')
        val = pe * g
        f.text(('%.1f' % val if pe % 1 else '%d' % round(val)) + 'x', x, yb - h - 50, 60 if shift < 0.5 else 46, 'orb', col, a, mode='E', glow=0.6)
        f.text(lab, x, yb + 44, 30, 'sans_med', WHITE, a)
        f.text(prof, x, yb + 86, 30, 'sans_black', lerpc(col, WHITE, .4), a)
        f.text(note, x, yb - h + 34, 26, 'sans_light', lerpc(col, WHITE, .5), a * env(t, t0 + 0.8, 90.0, 0.3, 0.3))
    f.line((300, yb), (1620, yb), GREY, a * 0.3 * (1 - shift), 1)
    caption(f, t, '表面 10 倍，实际支付的是 25 倍正常盈利', 980, 88.06, 90.0, 40, GOLD2, 'sans_black', stag=0.03)
    a2 = env(t, 90.3, 96.0, 0.4, 0.4)
    if a2 > 0:
        x0 = 1080
        f.text('周期股估值，三把尺子一起量：', x0, 360, 34, 'sans_med', GREY, a2, 'l', t0=90.3, stag=0.02)
        for i, (s, c) in enumerate([('顶峰 PE', CYAN), ('中枢 PE', GOLD), ('低谷生存能力', RED)]):
            chip(f, s, x0 + 90 + i * 230 + (40 if i == 2 else 0), 440, 30, c, a2 * eo((t - 90.8 - i * 0.25) / 0.3), 'sans_black', 0.12)
        f.text('不要用周期顶峰的利润，', x0, 580, 50, 'serif_black', WHITE, a2, 'l', t0=92.06, stag=0.05, glow=0.3)
        f.text('为公司的长期价值定价。', x0, 660, 50, 'serif_black', GOLD2, a2, 'l', t0=93.0, stag=0.05, grad=[GOLD2, ORANGE], mode='E', glow=0.5)
        f.text('更不要为不可持续的高增长，支付高溢价。', x0, 750, 30, 'sans_light', lerpc(GOLD2, WHITE, .4), a2, 'l', t0=94.06, stag=0.03)


# ============================================================== 02 能力圈与证伪 (96.06 – 136)
PAIRS = [('国产替代空间巨大', '替代 ≠ 利润？'), ('客户验证成功', '能规模化采购吗？'), ('技术壁垒很高', '对手两年内能突破吗？'),
         ('市场空间巨大', '最终能拿多少份额？'), ('盈利快速增长', '估值是否已透支？'), ('龙头地位稳固', '能维持高 ROIC 吗？')]

def sc_l2_card(f, t):
    if 96.0 < t < 100.5:
        card(f, t, T_L2, 100.0, '02', '不懂不做：先学会反驳自己', 'CIRCLE OF COMPETENCE  ·  FALSIFICATION', CYAN, VIOLET)

def sc_bullbear(f, t):
    if not (99.9 < t < 116.3): return
    a = env(t, 100.06, 116.0, 0.4, 0.4)
    lx, rx = 560, 1360
    f.text('看多逻辑', lx, 200, 48, 'serif_black', CYAN, a, t0=100.06, mode='E', glow=0.5)
    f.text('必须回答的反证问题', rx, 200, 48, 'serif_black', MAGENTA, a, t0=100.3, mode='E', glow=0.5)
    f.line((W / 2, 170), (W / 2, 900), GREY, a * 0.25, 1)
    for i, (bull, bear) in enumerate(PAIRS):
        t0 = 100.56 + i * 1.5
        if t < t0: continue
        y = 300 + i * 92
        al = eo((t - t0) / 0.3)
        f.text(bull, lx, y, 36, 'sans_med', lerpc(CYAN, WHITE, .5), a * al, mode='L', glow=0.2)
        # lightning connector
        u = eo((t - t0 - 0.2) / 0.4)
        if u > 0:
            xa, xb = lx + 210, rx - 230
            pts = [(lerp(xa, xb, s), y + (8 * math.sin(s * 40 + t * 30) if 0 < s < 1 else 0)) for s in np.linspace(0, u, 30)]
            f.neon(pts, lerpc(CYAN, MAGENTA, u), a * 0.8, 2, 8)
        bb = eo((t - t0 - 0.5) / 0.3)
        f.text(bear, rx, y, 36, 'sans_black', lerpc(MAGENTA, WHITE, .3), a * bb, mode='E', glow=0.3)
        burst(f, t, t0 + 0.55, rx - 220, y, [MAGENTA, WHITE], i, 120, 400, 0.4, 3, 0.6)
    a2 = env(t, 109.56, 116.0, 0.3, 0.4)
    if a2 > 0:
        f.text('每次买入前，强制写两份材料', W / 2, 870, 40, 'sans_black', WHITE, a2, t0=109.56, stag=0.04, glow=0.2)
        for i, (s, col) in enumerate([('为什么可以买', CYAN), ('为什么绝对不该买', MAGENTA)]):
            al, sc = pop(t, 111.06 + i * 1.0)
            cx = W / 2 + (i * 2 - 1) * 300
            chip(f, s, cx, 960, 34, col, a2 * al, 'sans_black', 0.16, sc)

def gauge(f, cx, cy, R, v, col, a, th=14):
    f.arc((cx, cy), R, -math.pi / 2, 1.5 * math.pi, GREY, a * 0.18, th, 120)
    if v > 0.001:
        f.arc((cx, cy), R, -math.pi / 2, -math.pi / 2 + 2 * math.pi * v, col, a, th, max(8, int(160 * v)))
        f.arc((cx, cy), R, -math.pi / 2, -math.pi / 2 + 2 * math.pi * v, col, a * 0.5, th + 18, max(8, int(160 * v)), g=True)
        e = (cx + R * math.cos(-math.pi / 2 + 2 * math.pi * v), cy + R * math.sin(-math.pi / 2 + 2 * math.pi * v))
        f.glow(e, 24, WHITE, a * 0.7, 'B'); f.glow(e, 6, WHITE, a, 'E')

def sc_bayes(f, t):
    if not (115.9 < t < 136.3): return
    a = env(t, 116.06, 127.6, 0.5, 0.6)
    if a > 0:
        f.text('用贝叶斯思维，让事实改变观点', W / 2, 190, 52, 'serif_black', WHITE, a, t0=116.06, stag=0.05, grad=[CYAN, VIOLET], mode='E', glow=0.4)
        cx, cy = 1360, 590
        v = keys(t, [(116.5, 0.0), (118.0, 0.70), (121.6, 0.70), (123.6, 0.4375)])
        col = lerpc(CYAN, MAGENTA, cl((t - 121.6) / 2))
        gauge(f, cx, cy, 230, v, col, a)
        f.text('%.2f%%' % (v * 100) if t > 121.6 else '%d%%' % round(v * 100), cx, cy - 10, 74, 'orb', WHITE, a, mode='E', glow=0.5)
        f.text('投资逻辑成立的概率', cx, cy + 70, 28, 'sans_light', GREY, a)
        f.text('先验：竞争优势能持续五年', 160, 360, 36, 'sans_med', CYAN, a, 'l', t0=117.0, stag=0.03)
        f.text('P(H) = 70%', 160, 420, 40, 'mono', lerpc(CYAN, WHITE, .4), a, 'l', t0=117.5, stag=0.03)
        # evidence comet
        if 119.06 < t < 121.8:
            u = eo((t - 119.06) / 2.4)
            ex = lerp(-100, cx - 240, u); ey = lerp(200, cy, u)
            f.glow((ex, ey), 30, RED, a, 'B'); f.glow((ex, ey), 8, WHITE, a, 'E')
            f.line((ex - 160 * (1 - u * .3), ey - 60), (ex, ey), RED, a * 0.6, 2)
        if 121.5 < t < 122.4:
            burst(f, t, 121.6, cx - 230, cy, [RED, MAGENTA, WHITE], 5, 400, 900, 0.7, 2.5, 0.9)
        f.text('新证据：对手取得关键技术突破', 160, 520, 36, 'sans_black', lerpc(RED, WHITE, .3), a, 'l', t0=119.5, stag=0.03, glow=0.2)
        e2 = env(t, 121.6, 127.6, 0.3, 0.5)
        f.text('P(E|H)=30%     P(E|¬H)=90%', 160, 590, 32, 'mono', GREY, a * e2, 'l', t0=121.6, stag=0.02)
        f.text('P(H|E) = 0.7×0.3 / (0.7×0.3 + 0.3×0.9)', 160, 650, 32, 'mono', WHITE, a * e2, 'l', t0=122.1, stag=0.02)
        slam(f, t, '= 43.75%', 160, 730, 64, 123.6, MAGENTA, a, 'sans_black', anchor='l')
        caption(f, t, '概率下降 ≠ 立刻卖出：重算预期价值、价格与下行风险，再定仓位', 900, 124.5, 127.6, 32, lerpc(GOLD2, WHITE, .3),
                'sans_light', stag=0.02)
    b = env(t, 128.06, 135.6, 0.6, 0.8)
    if b > 0:
        flow(f, t, b * 0.25, [CYAN, VIOLET, WHITE, CYAN, MAGENTA, WHITE], 40, n=900, rise=0.5)
        f.text('最危险的不是不懂，', W / 2, 450, 84, 'serif_black', lerpc(GREY, WHITE, .6), b, t0=128.06, stag=0.12, dur=0.7, glow=0.2)
        f.text('而是自以为懂。', W / 2, 590, 100, 'serif_black', WHITE, b, t0=130.06, stag=0.16, dur=0.8,
               grad=[CYAN, VIOLET, MAGENTA], mode='E', glow=0.6)
        f.text('能解释 · 能估值 · 能反驳 · 能写出退出条件，才考虑买入', W / 2, 730, 32, 'sans_light', GOLD2, b, t0=132.06, stag=0.04)


# ============================================================== 03 仓位与相关性 (136 – 176)
STOCKS = ['光模块', 'PCB', '半导体设备', '存储', 'AI 服务器']

def sc_l3_card(f, t):
    if 136.0 < t < 144.3:
        a = env(t, T_L3C, 144.2, 0.6, 0.15)
        p, _ = pop(t, T_L3C, 0.6)
        f.text('LESSON', W / 2, 330, 26, 'corm', lerpc(MAGENTA, WHITE, .4), a * p, track=1.0, t0=T_L3C)
        f.text('03', W / 2, 470, 230, 'orb', MAGENTA, a * p * (0.6 + 0.4 * beat_pulse(t)), grad=[RED, MAGENTA, PINK], mode='E', glow=0.6)
        f.text('绝不满仓押注一个方向', W / 2, 680, 76, 'serif_black', WHITE, a, t0=137.06, stag=0.08, dur=0.5, mode='E', glow=0.35)
        f.text('POSITION  SIZING  ·  CORRELATION', W / 2, 780, 24, 'corm', lerpc(MAGENTA, WHITE, .5), a, track=0.5, t0=138.06, stag=0.02)
        implode(f, t, 140.06, T_L3, W / 2, H / 2, [MAGENTA, RED, PINK, VIOLET, WHITE, GOLD2], 1.0)

def sc_onebet(f, t):
    if not (144.0 < t < 156.3): return
    a = env(t, T_L3, 156.0, 0.05, 0.4)
    burst(f, t, T_L3, W / 2, 560, [MAGENTA, RED, PINK, WHITE, GOLD2, VIOLET], 1, 900, 1800, 1.3, 2.2, 1.0, 2)
    cx, cy, R = W / 2, 580, 340
    core = eo((t - 148.06) / 0.6)
    drop = eo((t - 152.06) / 1.2)
    f.text('看起来：分散在 5 个行业' if t < 148.06 else ('实际上：只有 1 个赌注' if t < 152.06 else '预期一旦下调 → 同时下跌'),
           W / 2, 180, 52, 'serif_black', WHITE if t < 148.06 else (MAGENTA if t < 152.06 else GREEN), a,
           t0=T_L3 if t < 148.06 else (148.06 if t < 152.06 else 152.06), stag=0.05, mode='E', glow=0.4)
    pos = []
    for k, s in enumerate(STOCKS):
        ang = -math.pi / 2 + k * 2 * math.pi / 5 + 0.15 * math.sin(t * 0.5)
        x = cx + R * math.cos(ang) * (1 - 0.25 * core); y = cy + R * math.sin(ang) * 0.8 * (1 - 0.25 * core) + drop * 110
        pos.append((x, y))
    for k, s in enumerate(STOCKS):
        t0 = 144.56 + k * 0.5
        al, sc = pop(t, t0)
        x, y = pos[k]
        col = [CYAN, VIOLET, BLUE, TEAL, PINK][k]
        col = lerpc(col, MAGENTA, core * 0.5)
        col = lerpc(col, GREEN, drop)
        if core > 0:
            f.neon([(x, y), (cx, cy + drop * 110)], MAGENTA if drop < 0.5 else GREEN, a * core * (0.5 + 0.5 * beat_pulse(t)), 2, 10)
        f.glow((x, y), 60 * sc, col, a * al * 0.4, 'B')
        f.circle((x, y), 62 * sc, col, a * al, 3)
        f.text(s, x, y, int(32 * sc), 'sans_black', lerpc(col, WHITE, .5), a * al, mode='E', glow=0.3)
        if drop > 0.05:
            f.text('▼', x + 80, y - 40, 30, 'sans_black', GREEN, a * drop)
    if core > 0:
        yc = cy + drop * 110
        r = 120 * eback(cl((t - 148.06) / 0.5), 2)
        f.glow((cx, yc), r, MAGENTA if drop < 0.5 else GREEN, a * core * 0.6 * (1 + bar_pulse(t)), 'B')
        f.circle((cx, yc), r, RED if drop < 0.5 else GREEN, a * core, 4)
        f.text('AI 资本开支', cx, yc - 22, 38, 'serif_black', WHITE, a * core, mode='E', glow=0.4)
        f.text('持续高增长预期', cx, yc + 28, 30, 'sans_med', lerpc(MAGENTA, WHITE, .5), a * core)
    caption(f, t, '分散的效果取决于相关性，而不是持股数量', 985, 153.06, 156.0, 36, GOLD2, 'sans_black', stag=0.03)

CORR = np.array([[1.0, .91, .84, .78, .88], [.91, 1.0, .86, .80, .90], [.84, .86, 1.0, .87, .83],
                 [.78, .80, .87, 1.0, .81], [.88, .90, .83, .81, 1.0]])

def heat_col(v):
    return grad_color([C(40, 30, 120), MAGENTA, RED, ORANGE, GOLD2], cl((v - 0.3) / 0.7))

def sc_stress(f, t):
    if not (155.9 < t < 164.3): return
    a = env(t, 156.06, 164.0, 0.3, 0.4)
    x0, y0, s = 240, 330, 104
    f.text('相关性矩阵', x0, 230, 40, 'serif_black', WHITE, a, 'l', t0=156.06, glow=0.3)
    labs = ['光模块', 'PCB', '设备', '存储', '服务器']
    for i in range(5):
        f.text(labs[i], x0 + i * s + s / 2, y0 - 26, 20, 'sans_light', GREY, a)
        f.text(labs[i], x0 - 12, y0 + i * s + s / 2, 20, 'sans_light', GREY, a, 'r')
        for j in range(5):
            t0 = 156.3 + (i + j) * 0.18
            g = eo((t - t0) / 0.3)
            if g <= 0: continue
            v = CORR[i, j] * g
            col = heat_col(v)
            cx, cy = x0 + j * s + s / 2, y0 + i * s + s / 2
            hs = s / 2 - 4
            f.fillpoly([(cx - hs, cy - hs), (cx + hs, cy - hs), (cx + hs, cy + hs), (cx - hs, cy + hs)], col, a * 0.32 * g, 'L')
            f.text('%.2f' % v, cx, cy, 24, 'mono', WHITE, a * g)
    # stress test
    xr = 1000
    f.text('压力测试', xr, 230, 40, 'serif_black', WHITE, a, 'l', t0=158.06, glow=0.3)
    e = env(t, 158.06, 164.0, 0.3, 0.4)
    f.text('科技仓位', xr, 340, 32, 'sans_med', GREY, a * e, 'l')
    f.text('70%', xr + 360, 340, 56, 'orb', MAGENTA, a * e, 'l', mode='E', glow=0.4)
    f.text('板块下跌', xr, 430, 32, 'sans_med', GREY, a * eo((t - 159.06) / 0.3), 'l')
    f.text('-30%', xr + 360, 430, 56, 'orb', GREEN, a * eo((t - 159.06) / 0.3), 'l', mode='E', glow=0.4)
    f.line((xr, 490), (xr + 640, 490), GREY, a * 0.5 * eo((t - 160.06) / 0.3), 1)
    f.text('组合直接损失', xr, 570, 34, 'sans_black', WHITE, a * eo((t - 160.06) / 0.3), 'l')
    if t > 160.06:
        v = 21 * eo((t - 160.06) / 0.8)
        f.text('-%d%%' % round(v), xr + 360, 570, 96, 'orb', RED, a, 'l', mode='E', glow=0.8)
    # draining bar
    bw = 640; fill = 1 - 0.21 * eo((t - 160.06) / 0.8)
    f.rrect(xr, 660, xr + bw, 700, 8, GREY, a * 0.5, 1)
    f.fillpoly([(xr + 2, 662), (xr + 2 + (bw - 4) * fill, 662), (xr + 2 + (bw - 4) * fill, 698), (xr + 2, 698)],
               lerpc(TEAL, RED, 1 - fill), a * 0.7, 'E')
    f.text('还没算其他资产的波动、融资和流动性冲击', xr, 750, 26, 'sans_light', GREY, a * eo((t - 161.06) / 0.4), 'l')

def sc_asym(f, t):
    if not (163.9 < t < 172.3): return
    a = env(t, 164.06, 172.0, 0.3, 0.4)
    f.text('亏损是不对称的', 160, 200, 56, 'serif_black', WHITE, a, 'l', t0=164.06, stag=0.05, grad=[GOLD2, RED], mode='E', glow=0.4)
    ox, oy, xw, yh = 300, 900, 1100, 600
    f.line((ox, oy), (ox + xw + 40, oy), GREY, a * 0.6, 1)
    f.line((ox, oy), (ox, oy - yh - 40), GREY, a * 0.6, 1)
    f.text('亏损', ox + xw + 60, oy, 26, 'sans_light', GREY, a, 'l')
    f.text('回本所需涨幅', ox, oy - yh - 70, 26, 'sans_light', GREY, a)
    for k in range(1, 5):
        yy = oy - yh * k * 100 / 400
        f.line((ox, yy), (ox + xw, yy), GREY, a * 0.08, 1)
        f.text('%d%%' % (k * 100), ox - 14, yy, 20, 'mono', GREY, a * 0.8, 'r')
    for k in range(1, 9):
        xx = ox + xw * k * 10 / 85
        f.text('-%d%%' % (k * 10), xx, oy + 26, 18, 'mono', GREY, a * 0.7)
    X = lambda L: ox + xw * L / 85
    Y = lambda L: oy - yh * min(1 / (1 - L / 100) - 1, 4.4) * 100 / 400
    u = eo((t - 164.5) / 3.6)
    Ls = np.linspace(0, 81.5 * u, 120)
    pts = [(X(L), Y(L)) for L in Ls]
    if len(pts) > 1:
        f.neon(pts, lerpc(GOLD, RED, u), a, 3, 18)
        f.glow(pts[-1], 26, RED, a, 'B')
    marks = [(10, 11), (30, 43), (50, 100), (80, 400)]
    for i, (L, g) in enumerate(marks):
        t0 = 165.06 + i * 1.0
        if t < t0 or L > 81.5 * u + 0.1: continue
        al, sc = pop(t, t0)
        x, y = X(L), Y(L)
        f.circle((x, y), 10, WHITE, a * al, 2)
        f.line((x, y), (x, oy), GREY, a * al * 0.3, 1)
        txt = '-%d%%  →  +%d%%' % (L, g)
        f.text(txt, x - 24, y - 44, int(30 * sc), 'sans_black', lerpc(GOLD if i < 2 else RED, WHITE, .3), a * al, 'r' if i == 3 else 'm',
               mode='E', glow=0.3)
    caption(f, t, '一次致命亏损，足以抹掉多年复利', 990, 169.06, 172.0, 40, RED, 'sans_black', stag=0.04)

def sc_sizing(f, t):
    if not (171.9 < t < 176.3): return
    a = env(t, 172.06, 176.0, 0.3, 0.3)
    f.text('仓位上限  =  可承受的组合损失  ÷  压力情景跌幅', W / 2, 330, 48, 'serif_black', WHITE, a, t0=172.06, stag=0.03, mode='E', glow=0.3)
    f.text('2%  ÷  40%  =', W / 2 - 90, 470, 70, 'orb', GREY, a, t0=172.6, stag=0.03)
    slam(f, t, '5%', W / 2 + 300, 470, 110, 173.06, GOLD, a, 'orb')
    f.text('看对方向，决定潜在收益；', W / 2, 650, 56, 'serif_black', WHITE, a, t0=173.56, stag=0.05, glow=0.3)
    f.text('仓位管理，决定你能否长期留在市场。', W / 2, 750, 56, 'serif_black', GOLD2, a, t0=174.56, stag=0.04, grad=[GOLD2, ORANGE], mode='E', glow=0.5)


# ============================================================== 04 题材与监管 (176 – 208.26)
def sc_l4_card(f, t):
    if 176.0 < t < 180.5:
        card(f, t, T_L4, 180.0, '04', '少碰题材股，盯住监管的「刀」', 'THEMES  ·  REGULATION  ·  LIQUIDITY', ORANGE, GOLD)

def sc_forces(f, t):
    if not (179.9 < t < 188.3): return
    a = env(t, 180.06, 188.0, 0.3, 0.4)
    f.text('股价的三种驱动力', 160, 200, 52, 'serif_black', WHITE, a, 'l', t0=180.06, stag=0.05, glow=0.3)
    layers = [('基本面', '订单 · 利润 · 竞争力', TEAL, 150, '业绩低于预期'), ('情绪与估值', '市场愿意付更高 PE', MAGENTA, 170, '风险偏好骤降'),
              ('资金与交易结构', '集中买入 · 杠杆 · 趋势强化', ORANGE, 190, '去杠杆 · 集中卖出')]
    x0, x1, yb = 300, 900, 900
    y = yb
    shatter = cl((t - 186.06) / 1.0)
    for i, (s, sub, col, hgt, risk) in enumerate(layers):
        t0 = 180.56 + i * 1.0
        g = eo((t - t0) / 0.5)
        if g <= 0: continue
        dy = (1 - g) * -300
        fall = 0.0; al = a * g
        if i > 0 and shatter > 0:
            fall = shatter ** 2 * (500 + i * 200); al *= 1 - shatter
        yt = y - hgt
        q = [(x0, y + dy + fall), (x1, y + dy + fall), (x1, yt + dy + fall), (x0, yt + dy + fall)]
        f.fillpoly(q, col, al * 0.22, 'L')
        f.neon(q, col, al, 2, 10, closed=True)
        f.text(s, (x0 + x1) / 2, (y + yt) / 2 - 16 + dy + fall, 40, 'sans_black', lerpc(col, WHITE, .5), al, mode='E', glow=0.3)
        f.text(sub, (x0 + x1) / 2, (y + yt) / 2 + 30 + dy + fall, 24, 'sans_light', WHITE, al * 0.85)
        f.text('风险：' + risk, 1040, (y + yt) / 2 + dy, 32, 'sans_med', lerpc(col, WHITE, .4), a * g * (1 - shatter * (i > 0)), 'l')
        y = yt
    # price marker on top
    top = keys(t, [(180.56, yb - 150), (181.56, yb - 320), (182.56, yb - 510), (186.06, yb - 510), (187.2, yb - 150)])
    f.neon([(x0 - 40, top), (x1 + 40, top)], WHITE, a, 2, 12)
    f.text('股价', x0 - 60, top, 30, 'sans_black', WHITE, a, 'r')
    ca = env(t, 184.06, 186.0, 0.3, 0.2)
    f.text('三者叠加：增长被高度乐观预期 + 估值透支 + 交易拥挤', 1040, 260, 30, 'sans_black', RED, a * ca, 'l', t0=184.06, stag=0.02)
    caption(f, t, '基本面没有被证伪，股价依然可以崩塌', 980, 186.3, 188.0, 44, GOLD2, 'serif_black', stag=0.04)

def sc_reflex(f, t):
    if not (187.9 < t < 196.3): return
    a = env(t, 188.06, 196.0, 0.3, 0.4)
    rev = t >= 192.06
    f.text('反身性：同一台机器，两个方向', W / 2, 190, 52, 'serif_black', WHITE, a, t0=188.06, stag=0.05, glow=0.3)
    up = ['价格上涨', '吸引资金', '推动上涨', '强化乐观']
    dn = ['价格下跌', '资金撤离', '加速下跌', '恐慌踩踏']
    labs = dn if rev else up
    col = GREEN if rev else GOLD
    cx, cy, rx, ry = W / 2, 590, 470, 250
    path = lambda u: (cx + rx * math.cos(2 * math.pi * u - math.pi / 2), cy + ry * math.sin(2 * math.pi * u - math.pi / 2))
    ring = [path(u) for u in np.linspace(0, 1, 160)]
    f.neon(ring, col, a * 0.5, 2, 12, closed=True)
    # accelerating comet (reversed direction when falling)
    tt = t - (192.06 if rev else 188.06)
    ph = 0.25 * tt + 0.08 * tt * tt
    u = (-ph if rev else ph) % 1.0
    comet(f, lambda q: path(q), u, col, a, 22, -0.008 if rev else 0.008)
    for k, s in enumerate(labs):
        x, y = path(k / 4)
        t0 = (192.06 if rev else 188.06) + 0.25 + k * 0.5
        al, sc = pop(t, t0)
        f.glow((x, y), 70, col, a * al * 0.35, 'B')
        f.rrect_fill(x - 120, y - 40, x + 120, y + 40, 20, col, a * al * 0.2)
        f.rrect(x - 120, y - 40, x + 120, y + 40, 20, col, a * al, 2)
        f.text(s, x, y, int(36 * sc), 'sans_black', lerpc(col, WHITE, .5), a * al, mode='E', glow=0.3)
    for k in range(4):   # arrows on the ring
        uu = k / 4 + (0.125 if not rev else -0.125)
        p0 = path(uu - 0.01); p1 = path(uu + (0.01 if not rev else -0.03))
        p0 = path(uu - 0.02 if not rev else uu + 0.02)
        arrow(f, p0, p1, col, a * 0.8, 2, 16)
    if rev and t < 192.6:
        f.flash += 0.3 * (1 - (t - 192.06) / 0.54)
    caption(f, t, '上涨时它让你相信趋势；逆转时，同一机制加速下跌', 960, 193.06, 196.0, 34, lerpc(GREEN, WHITE, .4), 'sans_med', stag=0.025)

SIGNALS = [('交易所监管', '异常波动 · 重点监控 · 停牌核查'), ('风险提示公告', '异动公告 · 估值偏离 · 澄清'),
           ('官方媒体舆情', '集中提示炒作与泡沫风险'), ('「国家队」资金', 'ETF 持仓变化 · 增减持')]

def sc_signals(f, t):
    if not (195.9 < t < 204.3): return
    a = env(t, 196.06, 204.0, 0.3, 0.3)
    f.text('A 股必须监控的四类信号', W / 2, 190, 52, 'serif_black', WHITE, a, t0=196.06, stag=0.05, glow=0.3)
    cx, cy, R = W / 2, 720, 230
    # gauge zones
    zones = [(math.pi, math.pi * 1.4, GOLD, '关注'), (math.pi * 1.4, math.pi * 1.7, ORANGE, '警惕'), (math.pi * 1.7, math.pi * 2, RED, '高风险')]
    for a0, a1, c, s in zones:
        f.arc((cx, cy), R, a0 + 0.02, a1 - 0.02, c, a * 0.85, 16, 40)
        f.arc((cx, cy), R, a0 + 0.02, a1 - 0.02, c, a * 0.3, 34, 40, g=True)
        am = (a0 + a1) / 2
        f.text(s, cx + (R + 50) * math.cos(am), cy + (R + 50) * math.sin(am), 26, 'sans_black', c, a)
    lit = sum(1 for i in range(4) if t >= 196.56 + i * 1.0)
    need = keys(t, [(196.06, 0.05), (197.56, 0.2), (199.56, 0.55), (200.56, 0.9), (204, 0.92)])
    need += 0.015 * math.sin(t * 30) * (t > 200.56)
    ang = math.pi + math.pi * need
    f.neon([(cx, cy), (cx + (R - 30) * math.cos(ang), cy + (R - 30) * math.sin(ang))], WHITE, a, 3, 12)
    f.glow((cx, cy), 20, WHITE, a, 'B')
    pos = [(360, 380), (1560, 380), (360, 640), (1560, 640)]
    for i, (s, sub) in enumerate(SIGNALS):
        t0 = 196.56 + i * 1.0
        al, sc = pop(t, t0)
        x, y = pos[i]
        col = [GOLD, ORANGE, ORANGE, RED][i]
        f.rrect_fill(x - 230, y - 70, x + 230, y + 70, 18, col, a * al * 0.12)
        f.rrect(x - 230, y - 70, x + 230, y + 70, 18, col, a * al * (0.6 + 0.4 * beat_pulse(t)), 2)
        f.text('%d' % (i + 1), x - 200, y - 30, 30, 'orb', col, a * al, 'l', mode='E', glow=0.5)
        f.text(s, x, y - 18, int(36 * sc), 'sans_black', WHITE, a * al, mode='E', glow=0.2)
        f.text(sub, x, y + 32, 22, 'sans_light', lerpc(col, WHITE, .5), a * al)
        if al > 0.5:
            f.line((x + (230 if x < W / 2 else -230), y), (cx, cy), col, a * 0.2, 1)
    caption(f, t, '多个独立且经核实的信号叠加 → 主动降低风险暴露，不必等业绩证伪', 1000, 200.56, 204.0, 30, WHITE, 'sans_med', stag=0.02)

def sc_extreme(f, t):
    if not (203.9 < t < T_STOP + 0.02): return
    a = 1.0 if t < T_STOP else 0.0
    # violent chart behind
    n = 80
    xs = np.linspace(100, 1820, n)
    u = cl((t - 204.06) / 4.0)
    m = max(2, int(u * n))
    rng = np.random.default_rng(int(t * 30))
    ys = 700 - 300 * np.sin(np.linspace(0, math.pi, n)) ** 0.6 + np.random.default_rng(3).normal(0, 25, n)
    ys[n // 2:] += np.linspace(0, 520, n - n // 2) ** 1.0
    f.neon(np.stack([xs[:m], ys[:m]], 1), lerpc(GOLD, RED, u), a * 0.5, 3, 18)
    slam(f, t, '极端的乐观，', W / 2, 440, 120, 204.06, GOLD2, a, 'serif_black', grad=[GOLD2, ORANGE], glow=0.6)
    slam(f, t, '必然导致极端的溃败。', W / 2, 620, 120, 206.06, RED, a, 'serif_black', grad=[RED, MAGENTA], glow=0.7)
    if t > 206.06: f.ca += 6
    burst(f, t, 206.06, W / 2, 620, [RED, MAGENTA, ORANGE, WHITE], 6, 700, 1600, 1.0, 2.0, 0.9, 2, grav=400)


# ============================================================== 05 心理陷阱 (208.26 – 228.06)
def sc_silence(f, t):
    if not (T_STOP < t < 212.4): return
    a = env(t, 208.6, 212.2, 0.4, 0.5)
    f.text('盈利，', W / 2, 480, 64, 'serif_med', lerpc(GREY, WHITE, .5), a, t0=208.6, stag=0.15, dur=0.6)
    f.text('会暂时掩盖错误。', W / 2, 590, 64, 'serif_black', WHITE, a, t0=209.6, stag=0.12, dur=0.6, glow=0.25)

CHAIN = [('连续盈利', GOLD), ('把奖励当成能力', ORANGE), ('仓位越放越大', MAGENTA), ('风控越来越松', RED), ('一次回撤，致命', RED)]

def sc_chain(f, t):
    if not (211.7 < t < 220.3): return
    a = env(t, 211.76, 220.0, 0.5, 0.4)
    f.text('当某个方向连续赚钱时……', W / 2, 220, 48, 'serif_black', WHITE, a, t0=211.76, stag=0.06, glow=0.2)
    xs = [260 + i * 350 for i in range(5)]
    y = 540
    for i, (s, col) in enumerate(CHAIN):
        t0 = 212.56 + i * 1.25
        al, sc = pop(t, t0, 0.45)
        if al <= 0: continue
        r = (60 + i * 8) * sc
        f.glow((xs[i], y), r, col, a * al * 0.4 * (1 + 0.5 * (i == 4) * math.sin(t * 12)), 'B')
        f.circle((xs[i], y), r, col, a * al, 3)
        f.text('%d' % (i + 1), xs[i], y, int(48 * sc), 'orb', lerpc(col, WHITE, .4), a * al, mode='E', glow=0.5)
        f.text(s, xs[i], y + 130, 32, 'sans_black', lerpc(col, WHITE, .4), a * al, mode='E', glow=0.2)
        if i < 4:
            u = eo((t - t0 - 0.4) / 0.6)
            if u > 0:
                arrow(f, (xs[i] + 80, y), (lerp(xs[i] + 80, xs[i + 1] - 85, u), y), col, a * 0.8, 2, 14)
    burst(f, t, 217.56, xs[4], y, [RED, MAGENTA, WHITE], 4, 500, 1100, 0.9, 2.3, 0.9)
    caption(f, t, '盈利会暂时掩盖错误的风险管理方式', 840, 218.3, 220.0, 36, GOLD2, 'sans_med', stag=0.03)

def sc_grid(f, t):
    if not (219.9 < t < 228.2): return
    a = env(t, 220.06, 227.9, 0.4, 0.3)
    f.text('好决策也可能亏钱，坏决策也可能赚钱', W / 2, 190, 48, 'serif_black', WHITE, a, t0=220.06, stag=0.04, glow=0.3)
    cx, cy, cw, ch = W / 2 + 60, 560, 420, 190
    f.text('赚钱', cx - cw / 2, cy - ch - 40, 32, 'sans_black', RED, a)
    f.text('亏钱', cx + cw / 2, cy - ch - 40, 32, 'sans_black', GREEN, a)
    f.text('好决策', cx - cw - 40, cy - ch / 2, 32, 'sans_black', TEAL, a, 'r')
    f.text('坏决策', cx - cw - 40, cy + ch / 2, 32, 'sans_black', ORANGE, a, 'r')
    cells = [(0, 0, '应得的回报', TEAL), (1, 0, '运气不好，但没做错', CYAN), (0, 1, '危险的运气', RED), (1, 1, '应得的教训', ORANGE)]
    for k, (i, j, s, col) in enumerate(cells):
        t0 = 220.8 + k * 0.6
        al, sc = pop(t, t0)
        x = cx - cw + i * cw; y = cy - ch + j * ch
        danger = (i == 0 and j == 1)
        pul = (0.5 + 0.5 * math.sin(t * 8)) if danger and t > 223.5 else 0
        f.rrect_fill(x + 8, y + 8, x + cw - 8, y + ch - 8, 16, col, a * al * (0.12 + 0.2 * pul))
        f.rrect(x + 8, y + 8, x + cw - 8, y + ch - 8, 16, col, a * al * (0.7 + 0.3 * pul), 2 + 2 * danger)
        f.text(s, x + cw / 2, y + ch / 2, int((40 if danger else 34) * sc), 'sans_black', lerpc(col, WHITE, .5), a * al,
               mode='E', glow=0.3 + 0.5 * pul)
    caption(f, t, '复盘的是决策当时的信息、赔率与风险预算，而不是结果', 900, 223.56, 227.9, 34, GOLD2, 'sans_med', stag=0.025)
    caption(f, t, '保留每笔重要投资的原始备忘录', 960, 225.06, 227.9, 28, GREY, 'sans_light', stag=0.03)


# ============================================================== 06 决策系统 (228.06 – 260.06)
CHECK = [('能力圈', '能用大白话讲清商业模式吗？'), ('护城河', '凭什么长期高于资本成本？'), ('周期', '业绩在低谷、中枢还是顶部？'),
         ('估值', '悲观 / 基准 / 乐观都算过吗？'), ('预期', '股价隐含了什么增长？'), ('证伪', '能说出三个推翻逻辑的因素吗？'),
         ('概率赔率', '预期收益够补偿下行风险吗？'), ('政策监管', '有政策、流动性、拥挤风险吗？'), ('组合仓位', '与现有持仓相关吗？扛得住吗？'),
         ('退出条件', '什么证据出现就减仓、退出？')]

def sc_check(f, t):
    if not (227.9 < t < 244.3): return
    a = env(t, T_SYS, 244.0, 0.3, 0.4)
    burst(f, t, T_SYS, W / 2, 200, [GOLD, GOLD2, TEAL, WHITE], 2, 500, 1200, 1.0, 2.4, 0.8)
    f.text('芒格式 · 投资前十问', W / 2, 180, 60, 'serif_black', WHITE, a, t0=T_SYS, stag=0.06, grad=[GOLD2, GOLD], mode='E', glow=0.5)
    done = 0
    for i, (s, q) in enumerate(CHECK):
        col_i, row = i // 5, i % 5
        x = 230 + col_i * 760; y = 320 + row * 128
        t0 = 228.56 + i * 0.25
        al = eo((t - t0) / 0.3)
        tick = 230.56 + i * 1.25
        g = eo((t - tick) / 0.25)
        done += t >= tick
        f.rrect(x - 30, y - 30, x + 30, y + 30, 10, GOLD if g > 0 else GREY, a * al, 2)
        if g > 0:
            f.rrect_fill(x - 30, y - 30, x + 30, y + 30, 10, GOLD, a * g * 0.25)
            p1 = (x - 16, y + 2); p2 = (x - 4, y + 15); p3 = (x + 20, y - 18)
            u = g
            if u < 0.4: f.neon([p1, (lerp(p1[0], p2[0], u / .4), lerp(p1[1], p2[1], u / .4))], GOLD2, a, 4, 10)
            else: f.neon([p1, p2, (lerp(p2[0], p3[0], (u - .4) / .6), lerp(p2[1], p3[1], (u - .4) / .6))], GOLD2, a, 4, 10)
            burst(f, t, tick, x, y, [GOLD, GOLD2, WHITE], i, 160, 500, 0.5, 3, 0.7)
        f.text('%02d' % (i + 1), x + 60, y - 18, 24, 'orb', GOLD if g > 0 else GREY, a * al, 'l')
        f.text(s, x + 120, y - 18, 38, 'sans_black', WHITE if g > 0 else lerpc(GREY, WHITE, .4), a * al, 'l', mode='E', glow=0.3 * g)
        f.text(q, x + 120, y + 26, 26, 'sans_light', lerpc(GOLD2, WHITE, .4) if g > 0 else GREY, a * al, 'l')
    caption(f, t, '核心不是凑齐十个「是」，而是不被叙事、短期业绩和情绪带偏', 990, 241.06, 244.0, 32, GOLD2, 'sans_med', stag=0.02)

LAWS = [('周期与估值', '不把顶峰盈利当永续盈利'), ('能力圈与证伪', '能解释 · 能估值 · 能反驳'), ('分散与风控', '按底层风险因子分散'),
        ('政策与资金', '区分基本面与拥挤交易'), ('概率与赔率', '赔率匹配才下注'), ('纪律与纠错', '不被沉没成本绑架')]

def sc_laws(f, t):
    if not (243.9 < t < 260.2): return
    a = env(t, 244.06, 259.9, 0.4, 0.2)
    f.text('四条教训 → 六条投资铁律', W / 2, 170, 52, 'serif_black', WHITE, a, t0=244.06, stag=0.05, glow=0.3)
    cx, cy, R = W / 2, 620, 280
    rot = (t - 244.06) * 0.04
    V = [(cx + R * math.cos(-math.pi / 2 + k * math.pi / 3 + rot), cy + R * 0.95 * math.sin(-math.pi / 2 + k * math.pi / 3 + rot)) for k in range(6)]
    allin = eo((t - 256.06) / 0.6)
    cols = [ORANGE, CYAN, MAGENTA, RED, GOLD, TEAL]
    for k in range(6):
        t0 = 244.56 + k * 1.5
        if t < t0: continue
        g = eo((t - t0) / 0.5)
        nxt = V[(k + 1) % 6]
        if k < 5 or t > 253.0:
            u = eo((t - t0 - 0.3) / 0.8)
            f.neon([V[k], (lerp(V[k][0], nxt[0], u), lerp(V[k][1], nxt[1], u))], lerpc(cols[k], GOLD2, allin), a * g, 2, 12)
        f.line(V[k], (cx, cy), cols[k], a * g * (0.15 + 0.35 * allin), 1)
        al, sc = pop(t, t0)
        f.glow(V[k], 40, cols[k], a * al * (0.5 + 0.5 * allin), 'B')
        f.circle(V[k], 14 * sc, cols[k], a * al, 3)
        dx = V[k][0] - cx; dy = V[k][1] - cy
        d = math.hypot(dx, dy)
        lx = V[k][0] + dx / d * 70; ly = V[k][1] + dy / d * 60
        anc = 'l' if dx > 40 else ('r' if dx < -40 else 'm')
        if anc == 'm': ly += (-20 if dy < 0 else 20)
        f.text(LAWS[k][0], lx, ly - 20, int(38 * sc), 'sans_black', lerpc(cols[k], WHITE, .45), a * al, anc, mode='E', glow=0.3)
        f.text(LAWS[k][1], lx, ly + 26, 24, 'sans_light', WHITE, a * al * 0.85, anc)
    ca = eo((t - 245.0) / 0.6)
    f.glow((cx, cy), 120 + 80 * allin, GOLD, a * ca * (0.25 + 0.4 * allin) * (1 + bar_pulse(t)), 'B')
    f.text('投资', cx, cy - 34, 52, 'serif_black', WHITE, a * ca, mode='E', glow=0.4)
    f.text('决策系统', cx, cy + 34, 52, 'serif_black', GOLD2, a * ca, mode='E', glow=0.5)
    implode(f, t, 256.6, T_FIN, cx, cy, [GOLD, GOLD2, ORANGE, WHITE, TEAL, CYAN], 0.8, 900)


# ============================================================== 终章 (260.06 – 296)
CORE = [('不懂不做', CYAN), ('不贵买', GOLD), ('不重押', MAGENTA), ('不追狂热', RED)]

def sc_core(f, t):
    if not (260.0 < t < 276.3): return
    a = env(t, T_FIN, 276.0, 0.05, 0.4)
    burst(f, t, T_FIN, W / 2, H / 2, [GOLD, GOLD2, ORANGE, WHITE, CYAN, MAGENTA], 0, 900, 1900, 1.4, 2.0, 1.0, 2)
    flow(f, t, a * 0.3, [GOLD, GOLD2, ORANGE, GOLD, GOLD2, WHITE], 90, n=1400, rise=1.0)
    row_y = 250
    ws = [text_width(s, 'serif_black', 64) for s, _ in CORE]
    sep = 80
    tot = sum(ws) + sep * 3
    xs = []; x = W / 2 - tot / 2
    for w in ws: xs.append(x + w / 2); x += w + sep
    for i, (s, col) in enumerate(CORE):
        t0 = T_FIN + i * 2.0
        if t < t0: continue
        p = eio((t - t0 - 1.3) / 0.6)          # big centre → row
        x = lerp(W / 2, xs[i], p); y = lerp(560, row_y, p); size = lerp(220, 64, p)
        sl = cl((t - t0) / 0.25)
        size *= 1 + 0.5 * (1 - eo(sl))
        f.text(s, x, y, int(size), 'serif_black', col, a * eo(sl), grad=[lerpc(col, WHITE, .5), col], mode='E', glow=0.6)
        if p < 0.05: burst(f, t, t0, W / 2, 560, [col, WHITE, GOLD2], i + 1, 400, 1300, 0.8, 2.5, 0.8)
        if i < 3 and p > 0.9:
            f.glow((xs[i] + ws[i] / 2 + sep / 2, row_y), 5, GOLD2, a, 'E')
    # four questions (268 – 276)
    qs = [('买什么？', '有竞争优势、未来现金流可判断的企业'), ('什么价格买？', '情景概率 + 安全边际，而非短期增速'),
          ('买多少？', '由组合风险决定，而不是由信心决定'), ('什么时候卖？', '逻辑破坏 · 价格透支 · 风险超预算')]
    for i, (q, ans) in enumerate(qs):
        t0 = 268.06 + i * 1.0
        al, sc = pop(t, t0)
        if al <= 0: continue
        col_i, row = i % 2, i // 2
        x = 300 + col_i * 700; y = 470 + row * 210
        f.rrect_fill(x - 30, y - 70, x + 640, y + 80, 18, GOLD, a * al * 0.07)
        f.rrect(x - 30, y - 70, x + 640, y + 80, 18, GOLD, a * al * 0.6, 1)
        f.text(q, x, y - 20, int(48 * sc), 'serif_black', GOLD2, a * al, 'l', mode='E', glow=0.4)
        f.text(ans, x, y + 40, 28, 'sans_med', WHITE, a * al, 'l', t0=t0 + 0.2, stag=0.015)

def sc_final(f, t):
    if not (275.9 < t < 288): return
    a = env(t, 276.06, 287.6, 0.5, 1.0)
    flow(f, t, a * 0.45, [GOLD, GOLD2, ORANGE, GOLD, GOLD2, WHITE], 50, n=1600, rise=1.2)
    f.text('投资的终极目标，', W / 2, 330, 60, 'serif_med', lerpc(GREY, WHITE, .6), a, t0=276.06, stag=0.08, dur=0.5)
    f.text('不是每一次都判断正确，', W / 2, 440, 72, 'serif_black', WHITE, a, t0=277.06, stag=0.07, dur=0.5, glow=0.2)
    f.text('而是在判断错误时，', W / 2, 560, 72, 'serif_black', WHITE, a, t0=278.56, stag=0.07, dur=0.5, glow=0.2)
    f.text('不会遭受致命损失。', W / 2, 690, 96, 'serif_black', GOLD2, a, t0=280.06, stag=0.12, dur=0.6,
           grad=[GOLD2, GOLD, ORANGE], mode='E', glow=0.7)
    f.text('并在真正有把握、赔率有利的机会出现时，依然有资本参与长期复利。', W / 2, 820, 32, 'sans_light', lerpc(GOLD2, WHITE, .5), a,
           t0=282.06, stag=0.03)

def sc_end(f, t):
    e = env(t, T_END, DUR + 1, 0.8, 0.1)
    if e <= 0: return
    rgb, m = END_LOGO
    hgt = m.shape[0]
    X0, Y0 = int(W / 2 - hgt / 2), int(380 - hgt / 2)
    sc = eo((t - T_END) / 1.0)
    f.over.append((m, X0, Y0, rgb, e * sc))
    f.glow((W / 2, 380), 150, C(110, 175, 255), e * 0.22, 'B')
    f.text('巴芒价值', W / 2, 610, 112, 'serif_black', GOLD2, e, t0=T_END + 0.3, stag=0.12, dur=0.6,
           grad=[GOLD2, GOLD, GOLDD], mode='O', glow=.5)
    f.text('BUFFETT · MUNGER', W / 2, 702, 30, 'corm', C(214, 178, 112), e, track=0.46, t0=T_END + 0.9, stag=0.03, mode='O')
    f.text('不懂不做 · 不贵买 · 不重押 · 不追狂热', W / 2, 800, 32, 'sans_light', lerpc(GREY, WHITE, .4), e, track=0.2,
           t0=T_END + 1.5, stag=0.04)
    burst(f, t, T_END + 0.1, W / 2, 380, [C(110, 175, 255), CYAN, GOLD2, WHITE], 7, 500, 900, 1.6, 1.6, 0.8)


SCENES = [sc_open, sc_title, sc_first, sc_l1_card, sc_davis, sc_cycle, sc_pe10, sc_l2_card, sc_bullbear, sc_bayes,
          sc_l3_card, sc_onebet, sc_stress, sc_asym, sc_sizing, sc_l4_card, sc_forces, sc_reflex, sc_signals, sc_extreme,
          sc_silence, sc_chain, sc_grid, sc_check, sc_laws, sc_core, sc_final, sc_end]

def render(i):
    t = i / FPS
    f = Frame(t)
    bg = bg_at(t)
    draw_stars(f, t)
    for s in SCENES:
        s(f, t)
    shockwaves(f, t)
    for t0, k in ((T_PEAK, 6), (60.06, 8), (T_L3, 10), (204.06, 9), (206.06, 12), (T_FIN, 8)):
        if t0 <= t < t0 + 0.5:
            q = math.exp(-(t - t0) / 0.12)
            f.shake = (int(round(k * q * math.sin(t * 90))), int(round(k * 1.2 * q * math.cos(t * 77))))
    draw_chrome(f, t)
    img = finish(f, bg, bloom_k=1.0 + 0.3 * beat_pulse(t) * energy(t), vignette=VIGNETTE)
    img = glitch(img, glitch_amt(t), i)
    if T_STOP <= t < 208.6:       # hard cut to black on the music stop
        img = (img.astype(np.float32) * ((t - T_STOP) / 0.34) * 0.0).astype(np.uint8)
    draw_hud_post(img, t, env(t, 0.4, T_END - 0.2, 1.0, 0.6))
    fade = cl(t / 0.8) * (1 - eio((t - (DUR - 1.6)) / 1.6))
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
