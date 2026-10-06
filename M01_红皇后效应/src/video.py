"""M01《产品越来越强，为什么优势却未必变大？》—— 红皇后效应 · 4 分钟动态视觉短片

纯字幕叙事（无人声）。所有画面切换、字幕出入都落在 100 BPM 的拍点上（1 拍 = 18 帧）。
时间轴 / 字幕见 timeline.py，配乐见 music.py，品牌角标与 logo 全部取自仓库根目录 brand/。
"""
import math, os, sys
import numpy as np, cv2
from PIL import Image, ImageDraw
from engine import *
from timeline import *

NFR = int(round(DUR * FPS))

# ================================================================ 品牌（只从 brand/ 读取）
sys.path.insert(0, os.path.join(HERE, '..', '..', 'brand'))
import brand
from brand import Hud, load_logo, GOLD_STOPS, SUB_GOLD, SPEC as BSPEC

HUD = Hud()
BGOLD = C(*GOLD_STOPS[1][1])       # 品牌主金 #FFD478 —— 关键词高亮
BGOLD_L = C(*GOLD_STOPS[0][1])     # #FFF3C8
BGOLD_D = C(*GOLD_STOPS[2][1])     # #E2A03C
BSUB = C(*SUB_GOLD)                # #D6B270
LOGO_GLOW = C(*BSPEC['glow_rgb'])  # logo 淡蓝光晕 (110,175,255)
TXT = (0.95, 0.96, 1.0)
CRIMSON = C(255, 50, 90); AMBER = C(255, 165, 60); INDIGO = C(110, 110, 255)

# ================================================================ 节拍
ENERGY = [(0, .3), (9.5, .3), (9.6, .9), (16.8, .6), (21.6, .4), (b(25), .5), (b(39), .85), (b(41), 1), (b(57) - .1, 1),
          (b(57), .3), (b(65), .4), (b(69) - .1, .7), (b(69), 1), (b(85) - .1, 1), (b(85), .45), (b(92), .8), (b(93) - .1, .8),
          (b(93), 1), (b(111) - .1, 1), (b(111), .9), (b(114), .5), (b(119), .35), (b(121), .8), (DUR, .2)]


def energy(t):
    return keys(t, ENERGY)


def beat_pulse(t, decay=0.13):
    return math.exp(-(t % BEAT) / decay)


def bar_pulse(t, decay=0.25):
    return math.exp(-(t % BAR) / decay)


# ================================================================ 背景：星云 + 星空
BGK = [
    (0, (90, 10, 30), (20, 10, 60), .7), (9.5, (90, 10, 30), (20, 10, 60), .6),
    (9.6, (170, 20, 60), (90, 20, 140), 1.35), (12.5, (120, 15, 50), (60, 20, 110), 1.0),
    (16.8, (60, 15, 60), (25, 25, 90), .85), (21.5, (60, 15, 60), (25, 25, 90), .85),
    (21.6, (80, 45, 170), (20, 30, 120), 1.15), (34.8, (90, 50, 170), (30, 20, 90), 1.0),
    (45.6, (30, 60, 120), (60, 30, 100), .9), (55.2, (100, 30, 60), (40, 30, 110), 1.0),
    (59.9, (100, 30, 60), (40, 30, 110), 1.0), (60.0, (10, 100, 95), (20, 40, 120), 1.15),
    (76.8, (20, 60, 110), (50, 30, 100), .9), (93.6, (25, 40, 90), (40, 20, 70), .75), (98.3, (20, 25, 60), (30, 15, 50), .6),
    (98.4, (190, 115, 30), (120, 40, 100), 1.45), (103, (140, 80, 25), (70, 30, 80), 1.0),
    (109.2, (150, 80, 20), (70, 30, 20), 1.0), (129.6, (60, 40, 30), (40, 20, 40), .7),
    (136.8, (15, 30, 85), (20, 15, 55), .75), (160.8, (20, 20, 50), (30, 15, 40), .55), (165.5, (20, 20, 50), (30, 15, 40), .5),
    (165.6, (150, 60, 50), (30, 90, 170), 1.45), (169, (110, 45, 45), (30, 70, 140), 1.05),
    (183.6, (150, 100, 30), (60, 40, 100), 1.1), (190.8, (120, 40, 40), (40, 30, 100), .95),
    (195.6, (20, 70, 130), (60, 30, 120), 1.0), (203.9, (20, 60, 120), (50, 30, 110), .9),
    (204.0, (15, 25, 70), (25, 15, 50), .65), (213.6, (120, 85, 25), (40, 30, 90), .95),
    (223.1, (30, 25, 50), (30, 20, 40), .6), (223.2, (200, 130, 40), (40, 110, 170), 1.5),
    (226, (120, 80, 30), (40, 70, 130), 1.05), (237.6, (30, 90, 120), (110, 70, 30), 1.0),
    (259.2, (110, 30, 50), (40, 30, 100), .95), (266.3, (60, 20, 40), (30, 20, 60), .7),
    (266.4, (210, 150, 50), (60, 120, 180), 1.5), (270, (130, 90, 30), (40, 60, 120), 1.05),
    (273.6, (30, 30, 95), (20, 40, 90), .8), (280.8, (120, 80, 25), (40, 25, 80), 1.0),
    (285.6, (20, 40, 100), (30, 20, 60), .7), (290.3, (20, 40, 100), (30, 20, 60), .6),
    (290.4, (40, 85, 170), (120, 85, 30), 1.15), (295, (25, 45, 100), (60, 45, 20), .8), (DUR, (10, 15, 30), (10, 10, 20), .4)]

NB1 = fbm(512, 288, 11, 6, 3); NB2 = fbm(512, 288, 22, 6, 3); NB3 = fbm(512, 288, 33, 5, 5)


def bg_at(t):
    a = keys(t, [(k[0], k[1]) for k in BGK]); bcol = keys(t, [(k[0], k[2]) for k in BGK])
    I = keys(t, [(k[0], k[3]) for k in BGK]) * (1 + 0.16 * beat_pulse(t, 0.2) * energy(t))
    s = 1.0 + 0.04 * math.sin(t * 0.07)
    M = np.float32([[s, 0, -16 - 14 * math.sin(t * 0.045)], [0, s, -9 - 8 * math.cos(t * 0.038)]])
    n1 = cv2.warpAffine(NB1, M, (480, 270), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    M2 = np.float32([[s, 0, -16 + 14 * math.sin(t * 0.05 + 1)], [0, s, -9 + 8 * math.sin(t * 0.03)]])
    n2 = cv2.warpAffine(NB2, M2, (480, 270), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    n3 = cv2.warpAffine(NB3, M, (480, 270), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    img = ((n1 ** 3)[..., None] * np.array(a, np.float32) + (n2 ** 3.2)[..., None] * np.array(bcol, np.float32)) * (0.6 + 0.8 * n3)[..., None]
    img *= I * 0.55 / 255.0
    return cv2.resize(img, (W, H), interpolation=cv2.INTER_LINEAR)


_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2)
VIGNETTE = np.clip(1 - 0.42 * _r ** 2.4, 0.25, 1)[..., None].astype(np.float32)
del _yy, _xx, _r

RNG = np.random.default_rng(1234)
NST = 1200
ST_X = RNG.uniform(-1.8, 1.8, NST); ST_Y = RNG.uniform(-1.1, 1.1, NST); ST_Z0 = RNG.uniform(0, 1, NST)
ST_COL = np.array([lerpc(WHITE, [CYAN, VIOLET, WHITE, BGOLD_L, PINK][i % 5], 0.4) for i in range(NST)], np.float32)
RISERS = [(b(3), b(4)), (b(39), b(41)), (b(67), b(69)), (b(91), b(93)), (b(110), b(111)), (b(119), b(121))]


def star_speed(t):
    v = 0.03
    for ti, k in IMPACTS:
        if t >= ti: v += k * 1.5 * math.exp(-(t - ti) / 0.55)
    for a, z in RISERS:
        if a <= t <= z: v += 0.3 * ei((t - a) / (z - a))
    if t < b(4): v += 0.12   # 钩子：一直在跑
    return v


_ts = np.arange(NFR + 2) / FPS
ST_S = np.concatenate([[0], np.cumsum([star_speed(x) / FPS for x in _ts])])


def draw_stars(f, t, a=1.0):
    S_ = ST_S[min(int(round(t * FPS)), NFR)]
    z = (ST_Z0 - S_) % 1.0 + 0.03
    fx = W * 0.32
    sx = W / 2 + ST_X / z * fx; sy = H / 2 + ST_Y / z * fx
    bb = np.clip((1.05 - z) ** 2.2, 0, 1) * (0.5 + 0.35 * beat_pulse(t, .18) * energy(t)) * a
    tw = 0.75 + 0.25 * np.sin(t * 3 + ST_X * 40)
    f.splat(sx, sy, ST_COL, bb * tw * 0.8, 'L')
    near = z < 0.25
    f.splat(sx[near], sy[near], ST_COL[near], bb[near] * 0.8, 'E')
    v = star_speed(t)
    if v > 0.25:
        z2 = z + min(v * 0.06, 0.25)
        sx2 = W / 2 + ST_X / z2 * fx; sy2 = H / 2 + ST_Y / z2 * fx
        al = cl((v - 0.25) / 1.0)
        idx = np.where((z < 0.7) & (abs(sx - W / 2) < W) & (abs(sy - H / 2) < H))[0][:420]
        for i in idx:
            f.line((sx2[i], sy2[i]), (sx[i], sy[i]), ST_COL[i], al * float(bb[i]) * 1.2, 1)


# ================================================================ 镜中棋盘地面
HOR = 600
FOCAL = 900.0
_FY = (np.arange((H - HOR) // 2) * 2 + 1.0)[:, None]
_FX = (np.arange(W // 2) * 2 - W / 2 + 1.0)[None, :]


def proj(xw, z, hor=HOR):
    return W / 2 + xw * FOCAL / z, hor + FOCAL / z, FOCAL / z


def floor(f, t, a, scroll, cline, cfill, tile=0.5, fill=0.16, fog=14.0, hor=HOR, lines_e=0.35):
    if a <= 0.003: return
    hh = H - hor
    ys = _FY[: hh // 2]
    z = FOCAL / ys
    u = _FX / ys / tile
    v = (z + scroll) / tile
    fpu = 2.0 / ys / tile                      # 每个（半分辨率）像素覆盖的格子宽度
    fpv = 2.0 * FOCAL / ys ** 2 / tile
    du = 0.5 - np.abs((u % 1.0) - 0.5)
    dv = 0.5 - np.abs((v % 1.0) - 0.5)
    lu = np.clip(1 - du / (0.018 + fpu), 0, 1) * np.clip(1.2 - fpu * 3, 0, 1)
    lv = np.clip(1 - dv / (0.018 + fpv), 0, 1) * np.clip(1.2 - fpv * 2.5, 0, 1)
    ln = np.maximum(lu, lv)
    chk = ((np.floor(u) + np.floor(v)) % 2 == 0).astype(np.float32) * np.clip(1 - fpv * 1.5, 0, 1)
    fogk = np.exp(-z / fog) * (0.25 + 0.75 * np.clip((ys - 2) / 60, 0, 1))
    Lc = (ln * fogk * a).astype(np.float32)
    Fc = (chk * fogk * a * fill).astype(np.float32)
    big_l = cv2.resize(Lc, (W, hh), interpolation=cv2.INTER_LINEAR)
    big_f = cv2.resize(Fc, (W, hh), interpolation=cv2.INTER_LINEAR)
    f.L[hor:] += big_l[..., None] * np.array(cline, np.float32) * 0.55 + big_f[..., None] * np.array(cfill, np.float32)
    f.E[hor:] += big_l[..., None] * np.array(cline, np.float32) * lines_e * 0.5
    # 地平线辉光
    band = np.exp(-((np.arange(-40, 41)) / 14.0) ** 2).astype(np.float32)
    y0 = hor - 40
    f.B[y0:y0 + 81] += band[:, None, None] * np.array(cline, np.float32) * 0.35 * a


# ================================================================ 通用特效
def shock_list():
    ev = [(t, k) for t, k in IMPACTS] + [(t, k) for t, k, _ in CUTS]
    return sorted(ev)


SHOCKS = shock_list()


def shockwaves(f, t):
    for ti, k in SHOCKS:
        dt = t - ti
        if 0 <= dt < 1.3:
            col = BGOLD if k >= 0.9 else lerpc(WHITE, CYAN, 0.4)
            for j, (dd, sc) in enumerate(((0, 1.0), (0.12, 0.6), (0.24, 0.35))):
                d2 = dt - dd
                if d2 < 0: continue
                r = 40 + 1250 * eo(d2 / 1.1)
                al = (1 - cl(d2 / 1.1)) ** 1.6 * k * sc
                f.circle((W / 2, H / 2), r, col if j else lerpc(col, WHITE, .5), al, 3 if j == 0 else 2)
            if k >= 0.4:
                f.flash += (k - 0.3) * 0.5 * math.exp(-dt / 0.16)
            f.ca += k * 8 * math.exp(-dt / 0.22)


def zoom_punch(t):
    s = 0.0
    for ti, k in SHOCKS:
        dt = t - ti
        if 0 <= dt < 0.9:
            s += k * 0.045 * math.exp(-dt / 0.16)
    return s


_BR = np.random.default_rng(77)
BURST = {s: (_BR.uniform(0, 2 * math.pi, 900), _BR.uniform(0.15, 1, 900) ** 0.6, _BR.uniform(0.4, 1.2, 900),
             _BR.integers(0, 6, 900)) for s in range(8)}


def burst(f, t, t0, cx, cy, cols, seed=0, n=700, speed=1500, life=1.4, drag=2.4, a=1.0):
    dt = t - t0
    if dt < 0 or dt > life * 2.4: return
    th, v, lf, ci = BURST[seed]
    th, v, lf, ci = th[:n], v[:n], lf[:n], ci[:n]
    cc = np.array(cols, np.float32)[ci % len(cols)]
    for k in range(4):
        d = max(dt - k * 0.018, 0)
        r = speed * v * (1 - math.exp(-drag * d)) / drag
        al = np.exp(-d / (life * lf)) * a * (1 - k * 0.22)
        f.splat(cx + r * np.cos(th), cy + r * np.sin(th) * 0.8, cc, al * 1.4, 'E')


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
    f.glow((cx, cy), 20 + 120 * ei(p), WHITE, (0.25 + 0.9 * ei(p)) * a, 'B')


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


def chip(f, s, cx, cy, size, col, a, fnt='sans_med', fill=0.10):
    if a <= 0.003: return
    tw = text_width(s, fnt, size)
    px, py = size * 0.75, size * 0.55
    f.rrect_fill(cx - tw / 2 - px, cy - size / 2 - py, cx + tw / 2 + px, cy + size / 2 + py, size * 0.6, col, fill * a)
    f.rrect(cx - tw / 2 - px, cy - size / 2 - py, cx + tw / 2 + px, cy + size / 2 + py, size * 0.6, col, a * 0.9, 2)
    f.text(s, cx, cy, size, fnt, lerpc(col, WHITE, 0.55), a, mode='O', glow=0.25)


# ================================================================ 富文本字幕（{…} 金色高亮）
def parse(s):
    out, hl = [], False
    for ch in s:
        if ch == '{': hl = True; continue
        if ch == '}': hl = False; continue
        out.append((ch, hl))
    return out


def rich_line(f, s, x, y, size, fnt='sans_med', col=TXT, hcol=BGOLD, a=1.0, t0=None, t_out=None, stag=0.03,
              anchor='m', mode='O', glow_hl=0.45, underline=True, track=0.0):
    chars = parse(s)
    if a <= 0.003 or not chars: return 0
    w = sum(glyph(ch, fnt, size)[1] for ch, _ in chars) + track * size * (len(chars) - 1)
    xs = x - w / 2 if anchor == 'm' else (x if anchor == 'l' else x - w)
    base = y + size * 0.36
    cx = xs
    runs, cur = [], None
    for i, (ch, hl) in enumerate(chars):
        m, adv, pad, bl = glyph(ch, fnt, size)
        ai, dy = a, 0.0
        if t0 is not None:
            p = (f.t - t0 - i * stag) / 0.42
            ai *= eo(p); dy = (1 - eo(p)) * size * 0.35
        if t_out is not None:
            q = (f.t - t_out - i * stag * 0.4) / 0.32
            ai *= 1 - eio(q); dy -= eio(q) * size * 0.25
        if ai > 0.003 and ch != ' ':
            c = hcol if hl else col
            f._blit(m, cx - pad, base - bl + dy, c, ai, mode, glow_hl if hl else 0.0)
        if hl:
            if cur is None: cur = [cx, cx + adv, i, ai]
            else: cur[1] = cx + adv; cur[3] = min(cur[3], ai) if ai > 0 else cur[3]
        elif cur is not None:
            runs.append(cur); cur = None
        cx += adv + track * size
    if cur is not None: runs.append(cur)
    if underline and t0 is not None:
        for (x0, x1, i0, ai) in runs:
            p = eo((f.t - t0 - i0 * stag - 0.25) / 0.5)
            al = a * p
            if t_out is not None: al *= 1 - eio((f.t - t_out) / 0.3)
            if al > 0.01:
                yy = y + size * 0.66
                f.line((x0, yy), (x0 + (x1 - x0) * p, yy), hcol, al * 0.85, 2)
                f.glow((x0 + (x1 - x0) * p, yy), 5, BGOLD_L, al * 0.8, 'E')
    return w


def rich_block(f, text, x, y, size, lh=1.5, row_delay=0.25, **kw):
    rows = text.split('\n')
    n = len(rows)
    t0 = kw.pop('t0', None)
    for i, r in enumerate(rows):
        rich_line(f, r, x, y + (i - (n - 1) / 2) * size * lh, size, t0=None if t0 is None else t0 + i * row_delay, **kw)
    return y + (n - 1) / 2 * size * lh


def draw_caps(f, t):
    for c in CAPS:
        if c['kind'] == 'list': continue
        if not (c['t0'] - 0.05 <= t <= c['t1'] + 0.05): continue
        k = c['kind']
        size = c['size']
        fnt = c['fnt'] or {'cap': 'sans_med', 'big': 'sans_black', 'quote': 'serif_med'}[k]
        rd = 0.35 if k == 'quote' else 0.22
        last = rich_block(f, c['text'], W / 2, c['y'], size, lh=1.45 if k != 'cap' else 1.4, row_delay=rd,
                          fnt=fnt, t0=c['t0'], t_out=c['t1'] - 0.32, stag=0.035 if k != 'cap' else 0.022,
                          glow_hl=0.5 if k != 'cap' else 0.35)
        yy = last + size * 0.95
        if c['en']:
            f.text(c['en'], W / 2, yy, 25 if len(c['en']) < 90 else 22, 'corm', lerpc(GREY, WHITE, .35),
                   env(t, c['t0'] + 0.5, c['t1'] - 0.1, 0.5, 0.3) * 0.9, mode='O')
            yy += 40
        if c['who']:
            f.text(c['who'], W / 2, yy, 24, 'sans_light', BSUB, env(t, c['t0'] + 0.8, c['t1'] - 0.1, 0.5, 0.3), mode='O')


# ================================================================ 章节标签与进度条
CHAPTERS = [(0, '序', '序章', 'PROLOGUE'), (b(9), '01', '镜中的奔跑', 'THROUGH THE LOOKING-GLASS'),
            (b(25), '02', '没有终点的赛跑', 'THE ENDLESS RACE'), (b(41), '03', '踮起脚尖的人群', 'THE TIPTOE PARADE'),
            (b(69), '04', '三种投入', 'THREE KINDS OF RUNNING'), (b(85), '05', '逃离跑步机', 'ESCAPE THE TREADMILL'),
            (b(114), '06', '边界与提问', 'LIMITS'), (b(119), '终', '片尾', 'END'), (DUR, '', '', '')]
CHROME_END = b(119)


def draw_chrome(f, t):
    for (a, num, zh, en), (z, *_r) in zip(CHAPTERS, CHAPTERS[1:]):
        if a <= t < z and a < CHROME_END:
            al = env(t, a, min(z, CHROME_END), 0.6, 0.4) * 0.9 * env(t, 0.6, CHROME_END, 0.8, 0.5)
            fn = 'orb' if num.isdigit() else 'serif_black'
            f.text(num, 70, 62, 30, fn, BGOLD, al, 'l', mode='O')
            x = 70 + text_width(num, fn, 30) + 16
            f.line((x, 50), (x, 76), BGOLD, al * 0.6, 1)
            f.text(zh, x + 16, 56, 24, 'sans_med', WHITE, al * 0.92, 'l', mode='O')
            f.text(en, x + 16, 84, 14, 'corm', GREY, al * 0.8, 'l', track=0.3, mode='O')
    pa = 0.5 * env(t, 1.0, CHROME_END, 1.0, 0.6)
    if pa > 0:
        x0, x1, y = 140, 1780, 1040
        f.L[y:y + 1, x0:x1] += np.float32(0.10 * pa)
        xc = x0 + (x1 - x0) * t / CHROME_END
        f.L[y:y + 1, x0:int(min(xc, x1))] += np.array(BGOLD, np.float32) * 0.35 * pa
        for (a, num, zh, en) in CHAPTERS[:-2]:
            xx = int(x0 + (x1 - x0) * a / CHROME_END)
            lit = t >= a
            f.L[y - 5:y + 6, xx:xx + 1] += np.array(BGOLD if lit else GREY, np.float32) * 0.5 * pa
            f.text(zh, xx + 8, y - 14, 15, 'sans_light', BGOLD if lit else GREY, pa * (0.9 if lit else 0.5), 'l', mode='L')
        f.glow((min(xc, x1), y), 4, BGOLD_L, 0.9 * pa, 'E')
        f.glow((min(xc, x1), y), 14, BGOLD, 0.5 * pa, 'B')


# ================================================================ 图形部件
QUEEN = [(0.40, 0.0), (0.40, -0.07), (0.30, -0.11), (0.33, -0.15), (0.22, -0.19), (0.15, -0.52), (0.25, -0.57), (0.22, -0.61),
         (0.13, -0.63), (0.27, -0.88), (0.17, -0.80), (0.13, -0.93), (0.06, -0.82), (0.0, -0.95)]
QUEEN = QUEEN + [(-x, y) for (x, y) in reversed(QUEEN[:-1])]
QBALLS = [(0.27, -0.9, .035), (-0.27, -0.9, .035), (0.13, -0.95, .035), (-0.13, -0.95, .035), (0, -1.0, .045)]
PAWN = [(0.34, 0.0), (0.34, -0.07), (0.24, -0.12), (0.13, -0.45), (0.22, -0.49), (0.10, -0.54), (0.0, -0.54)]
PAWN = PAWN + [(-x, y) for (x, y) in reversed(PAWN[:-1])]


def piece(f, kind, cx, by, h, col, a, fill=0.10, th=2, dark=0.0):
    if a <= 0.003: return
    pts = [(cx + x * h, by + y * h) for x, y in (QUEEN if kind == 'queen' else PAWN)]
    if dark > 0: f.darkpoly(pts, dark * a)
    f.fillpoly(pts, col, a * fill, 'L')
    f.poly(pts, col, a, th, closed=True)
    if kind == 'queen':
        for (x, y, r) in QBALLS:
            f.circle((cx + x * h, by + y * h), r * h, col, a, th)
            f.glow((cx + x * h, by + y * h), r * h * 1.2, col, a * 0.5, 'B')
    else:
        if dark > 0: f.darkcircle((cx, by - 0.71 * h), 0.17 * h, dark * a)
        f.circle((cx, by - 0.71 * h), 0.17 * h, col, a, th)
    f.glow((cx, by - 0.5 * h), h * 0.45, col, a * 0.22, 'B')


def tree(f, cx, by, h, col, a):
    if a <= 0.003: return
    f.line((cx, by), (cx, by - h * 0.55), col, a * 0.8, 2)
    f.circle((cx, by - h * 0.78), h * 0.24, col, a, 2)
    f.circle((cx, by - h * 0.78), h * 0.12, col, a * 0.45, 1)
    f.glow((cx, by - h * 0.78), h * 0.3, col, a * 0.25, 'B')


def comet(f, x, y, s, col, a):
    f.glow((x, y), s * 1.8, col, a * 0.55, 'B')
    f.glow((x, y), s * 0.55, lerpc(col, WHITE, .6), a, 'E')
    f.glow((x, y), s * 0.22, WHITE, a, 'E')


def gear(f, cx, cy, r, n, ang, col, a, th=2):
    pts = []
    for k in range(n * 4):
        q = ang + k / (n * 4) * 2 * math.pi
        rr = r if (k % 4) in (0, 1) else r * 0.8
        pts.append((cx + rr * math.cos(q), cy + rr * math.sin(q)))
    f.poly(pts, col, a, th, closed=True)
    f.circle((cx, cy), r * 0.32, col, a * 0.8, th)


def person(f, x, yb, s, col, a, rim=True, dark=0.95):
    """头肩剪影（不透明，挡住身后的光）+ 轮廓光"""
    head = (x, yb - 1.55 * s)
    sh = [(x - 0.75 * s, yb), (x - 0.72 * s, yb - 0.6 * s), (x - 0.55 * s, yb - 0.95 * s), (x - 0.2 * s, yb - 1.08 * s),
          (x + 0.2 * s, yb - 1.08 * s), (x + 0.55 * s, yb - 0.95 * s), (x + 0.72 * s, yb - 0.6 * s), (x + 0.75 * s, yb)]
    f.darkpoly(sh + [(x + 0.75 * s, H), (x - 0.75 * s, H)], dark * a)
    f.darkcircle(head, 0.36 * s, dark * a)
    if rim:
        f.top_poly(sh, col, a * 0.85, 2)
        ts = np.linspace(-math.pi * 0.95, -math.pi * 0.05, 20)
        f.top_poly(np.stack([head[0] + 0.36 * s * np.cos(ts), head[1] + 0.36 * s * np.sin(ts)], 1), col, a, 2)


def arrow(f, p0, p1, col, a, th=3, head=16):
    f.line(p0, p1, col, a, th)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for s_ in (-1, 1):
        q = (p1[0] - head * math.cos(ang + s_ * 0.45), p1[1] - head * math.sin(ang + s_ * 0.45))
        f.line(p1, q, col, a, th)


def bez(p0, p1, p2, p3, s):
    s = s[..., None] if isinstance(s, np.ndarray) else s
    return ((1 - s) ** 3) * np.array(p0) + 3 * ((1 - s) ** 2) * s * np.array(p1) + 3 * (1 - s) * s * s * np.array(p2) + s ** 3 * np.array(p3)


# ================================================================ 场景
def sc_hook(f, t):
    if t > b(4) + 0.6: return
    a = env(t, 0, b(4), 0.3, 0.25)
    # 高速滚动的红色棋盘地面：一直在跑
    floor(f, t, a, t * 7.0, CRIMSON, C(70, 20, 120), tile=0.5, fill=0.13)
    # 两个奔跑者：你 / 对手（同样快，所以距离不变）
    for i, (xw, col, name) in enumerate(((-0.75, CYAN, '你'), (0.75, CRIMSON, '对手'))):
        z = 4.0
        bob = abs(math.sin(math.pi * t / (BEAT / 2))) * 10
        x, y, s = proj(xw, z)
        y -= 70 + bob
        for k in range(26):   # 光迹：被抛在身后（更靠近镜头）
            zz = z - 0.12 * (k + 1)
            if zz < 0.7: break
            xx, yy, ss = proj(xw, zz)
            f.glow((xx, yy - 70 * ss / s), 6 * ss / s, col, a * 0.5 * (1 - k / 26) ** 1.5, 'E')
        comet(f, x, y, 26, col, a)
        al = a * env(t, b(1), b(4), 0.4, 0.2)
        f.text(name, x, y - 70, 30, 'sans_med', lerpc(col, WHITE, .5), al, mode='O')
        if t > b(2):   # 速度一样在涨
            sp = 1 + 1.4 * eio((t - b(2)) / BAR)
            f.text('速度 ×%.1f' % sp, x, y + 64, 24, 'sans_med', lerpc(col, WHITE, .3), al * 0.9, mode='O')
    # 差距：不变
    al = a * env(t, b(1), b(3, 2), 0.4, 0.3)
    xl, yl, _ = proj(-0.75, 4.0); xr, _, _ = proj(0.75, 4.0)
    yl -= 160
    f.line((xl, yl), (xr, yl), BGOLD, al * 0.8, 2)
    for xx in (xl, xr): f.line((xx, yl - 10), (xx, yl + 10), BGOLD, al * 0.8, 2)
    f.text('差距：没变', W / 2, yl - 26, 26, 'sans_med', BGOLD, al, mode='O')
    implode(f, t, b(3), b(4), W / 2, 720, [CRIMSON, CYAN, BGOLD, WHITE, MAGENTA, BGOLD_L], 0.9)


def sc_title(f, t):
    if not (b(4) - 0.1 < t < b(7) + 0.5): return
    a = env(t, b(4), b(7) - 0.05, 0.25, 0.4)
    burst(f, t, b(4), W / 2, 500, [CRIMSON, MAGENTA, BGOLD, BGOLD_L, WHITE, CYAN], 0, 800, 1700, 1.5)
    floor(f, t, a * 0.8, t * 1.2, MAGENTA, C(90, 20, 80), tile=0.5, fill=0.1)
    # 巨大的红皇后棋子剪影
    h = 640 * (1 + 0.012 * beat_pulse(t, 0.2))
    piece(f, 'queen', W / 2, 880, h, lerpc(CRIMSON, MAGENTA, .3), a * 0.33, fill=0.04, th=3)
    t0 = b(4)
    rich_line(f, '红皇后效应 · RED QUEEN EFFECT', W / 2, 285, 30, 'sans_med', BGOLD, a=a, t0=t0 + 0.1, stag=0.02, track=0.12, underline=False)
    rich_line(f, '产品越来越强，', W / 2, 420, 96, 'serif_black', TXT, a=a, t0=t0 + 0.2, stag=0.05)
    rich_line(f, '为什么优势却{未必变大}？', W / 2, 545, 96, 'serif_black', TXT, a=a, t0=t0 + 0.6, stag=0.05, glow_hl=0.6)
    rich_line(f, '《50个自然法则，看懂商业世界》  M01', W / 2, 675, 34, 'sans_med', lerpc(BSUB, WHITE, .3), a=a, t0=t0 + 1.2, stag=0.015, underline=False)
    rich_line(f, '50 个来自自然、数学与复杂系统的思维模型 · 第 01 个', W / 2, 728, 24, 'sans_light', lerpc(GREY, WHITE, .3), a=a, t0=t0 + 1.5, stag=0.01, underline=False)


def sc_promise(f, t):
    if not (b(7) - 0.1 < t < b(9)): return
    a = env(t, b(7), b(9), 0.4, 0.3)
    floor(f, t, a * 0.6, t * 0.8, VIOLET, C(40, 20, 90), tile=0.5, fill=0.08)
    for i, col in enumerate((CRIMSON, CYAN, BGOLD)):  # 预告：三种投入
        ang = t * 0.9 + i * 2 * math.pi / 3
        x, y = W / 2 + 230 * math.cos(ang), 720 + 34 * math.sin(ang)
        comet(f, x, y, 16, col, a * eo((t - b(7, 2) - i * BEAT) / 0.4))


def mirror_card(f, t, t0, t1, num, zh, en, col):
    a = env(t, t0, t1, 0.25, 0.3)
    if a <= 0: return
    burst(f, t, t0, W / 2, 470, [col, BGOLD, WHITE, BGOLD_L, col, CYAN], 3, 500, 1100, 1.2)
    rich_line(f, num, W / 2, 330, 120, 'orb', BGOLD, a=a, t0=t0, stag=0.08, underline=False, mode='E', glow_hl=0)
    rich_line(f, zh, W / 2, 478, 88, 'serif_black', TXT, a=a, t0=t0 + 0.15, stag=0.06)
    rich_line(f, en, W / 2, 568, 28, 'corm', BSUB, a=a, t0=t0 + 0.35, stag=0.012, track=0.3, underline=False)
    # 镜中世界：把标题字形翻转，画在地平线下作倒影
    m_y = 618
    f.line((W / 2 - 520 * eo((t - t0) / 0.6), m_y), (W / 2 + 520 * eo((t - t0) / 0.6), m_y), col, a * 0.7, 2)
    f.glow((W / 2, m_y), 40, col, a * 0.3, 'B')
    w = text_width(zh, 'serif_black', 88)
    x = W / 2 - w / 2
    for ch in zh:
        m, adv, pad, bl = glyph(ch, 'serif_black', 88)
        mr = (m[::-1] * np.linspace(1, 0, m.shape[0])[:, None] ** 2.2).astype(np.float32)
        f._blit(mr, x - pad, m_y + 2, lerpc(col, WHITE, .2), a * 0.28, 'L', 0)
        x += adv


def sc_card1(f, t):
    if not (b(9) - 0.1 < t < b(10) + 0.1): return
    floor(f, t, env(t, b(9), b(10), 0.3, 0.3), 0.0, INDIGO, C(50, 30, 120), tile=0.5)
    mirror_card(f, t, b(9), b(10), '01', '镜中的奔跑', 'THROUGH THE LOOKING-GLASS', VIOLET)


def sc_alice(f, t):
    if not (b(10) - 0.2 < t < b(14, 2) + 0.4): return
    a = env(t, b(10) - 0.1, b(14, 2), 0.35, 0.35)
    floor(f, t, a, 0.0, INDIGO, C(70, 40, 150), tile=0.5, fill=0.2)   # 地面不动：跑了也在原地
    # 两侧的树：一动不动
    tg = 1 + 0.6 * env(t, b(13), b(14, 2), 0.3, 0.3) * (0.6 + 0.4 * beat_pulse(t, 0.25))
    for side in (-1, 1):
        for z in (4.0, 5.6, 7.8, 11.0, 15.0):
            x, y, s = proj(side * 2.0, z)
            tree(f, x, y, 1.1 * s, lerpc(TEAL, GREEN, .3), a * min(1, 4.5 / z + 0.2) * tg)
    # 红皇后拉着爱丽丝：疯狂奔跑（上下颠簸 + 速度线），位置却不变
    run = env(t, b(11, 2), b(14, 2), 0.3, 0.3)
    for (xw, kind, col, ph) in ((-0.42, 'queen', CRIMSON, 0.0), (0.42, 'pawn', lerpc(CYAN, WHITE, .4), 0.5)):
        x, y, s = proj(xw, 5.0)
        bob = abs(math.sin(math.pi * (t / (BEAT / 2) + ph))) * 14 * run
        h = (1.6 if kind == 'queen' else 1.15) * s
        piece(f, kind, x, y - bob, h, col, a, fill=0.14, th=3, dark=0.8)
        if run > 0:
            for k in range(7):   # 速度线
                yy = y - h * (0.15 + 0.12 * k) - bob
                ph2 = (t * 3.2 + k * 0.37) % 1.0
                xx = x - h * 0.45 - 30 - ph2 * 180
                f.line((xx, yy), (xx - 70, yy), lerpc(col, WHITE, .4), a * run * (1 - ph2) * 0.7, 2)
    xq, yq, sq = proj(-0.42, 5.0); xa, ya, sa = proj(0.42, 5.0)
    f.line((xq + 0.3 * sq, yq - 0.7 * sq), (xa - 0.25 * sa, ya - 0.6 * sa), BGOLD, a * run * 0.7, 2)   # 牵着的手
    if t > b(13):
        al = a * env(t, b(13), b(14, 2), 0.3, 0.3)
        f.text('位移 = 0', W / 2, 220, 40, 'sans_black', BGOLD, al, mode='O')


def frame_oval(f, t, a, col, rx=700, ry=330, cy=500):
    if a <= 0: return
    for k, (dx, al) in enumerate(((0, 1.0), (16, 0.5), (30, 0.25))):
        ts = np.linspace(0, 2 * math.pi, 180)
        pts = np.stack([W / 2 + (rx + dx) * np.cos(ts), cy + (ry + dx * 0.6) * np.sin(ts)], 1)
        f.poly(pts, col, a * al, 2 if k == 0 else 1, closed=True)
    for k in range(12):   # 镜框上的珠饰
        q = k / 12 * 2 * math.pi + t * 0.05
        p = (W / 2 + (rx + 16) * math.cos(q), cy + (ry + 10) * math.sin(q))
        f.glow(p, 4, BGOLD_L, a * 0.9, 'E'); f.glow(p, 14, BGOLD, a * 0.35, 'B')


_KR = np.random.default_rng(17)
KAL = (_KR.uniform(0, 1, 500), _KR.uniform(0, 2 * math.pi, 500), _KR.uniform(0.3, 1, 500))


def sc_quote1(f, t):
    if not (b(14, 2) - 0.2 < t < b(19) + 0.3): return
    a = env(t, b(14, 2), b(19), 0.4, 0.4)
    floor(f, t, a * 0.5, 0.0, INDIGO, C(40, 30, 110), tile=0.5, fill=0.1)
    frame_oval(f, t, a * eo((t - b(14, 2)) / 0.8), lerpc(BGOLD, VIOLET, .35))
    # 镜面万花筒粒子（左右对称）
    r, th, sp = KAL
    rr = (r + t * 0.04 * sp) % 1.0
    ang = th + t * 0.15 * sp
    x = 660 * rr * np.cos(ang); y = 300 * rr * np.sin(ang)
    al = a * 0.5 * np.sin(rr * math.pi)
    cols = np.array([lerpc(VIOLET, PINK, u) for u in sp], np.float32)
    f.splat(W / 2 + x, 500 + y, cols, al, 'E'); f.splat(W / 2 - x, 500 + y, cols, al, 'E')


def sc_vanvalen(f, t):
    if not (b(19) - 0.2 < t < b(23) + 0.3): return
    a1 = env(t, b(19), b(20, 2), 0.3, 0.35)
    if a1 > 0:
        rich_line(f, '1973', W / 2, 420, 200, 'orb', BGOLD, a=a1, t0=b(19), stag=0.08, underline=False, mode='E')
        f.text('Leigh Van Valen', W / 2, 590, 44, 'corm_semi', BGOLD_L, a1 * eo((t - b(19, 1)) / 0.4), mode='O', track=0.1)
        burst(f, t, b(19), W / 2, 420, [BGOLD, BGOLD_L, WHITE, AMBER, CYAN, BGOLD], 5, 400, 900, 1.2)
    a2 = env(t, b(20, 2), b(23), 0.35, 0.35)
    if a2 > 0:   # 存续曲线（对数坐标下近似直线）—— 示意
        x0, x1, y0, y1 = 520, 1400, 250, 700
        f.line((x0, y1), (x1 + 20, y1), GREY, a2 * 0.8, 2); f.line((x0, y1), (x0, y0 - 20), GREY, a2 * 0.8, 2)
        arrow(f, (x1, y1), (x1 + 30, y1), GREY, a2 * 0.8, 2, 10); arrow(f, (x0, y0), (x0, y0 - 30), GREY, a2 * 0.8, 2, 10)
        f.text('类群已存在的时间 →', x1 - 120, y1 + 34, 22, 'sans_light', GREY, a2, mode='O')
        f.text('仍存活的类群数（对数）', x0 + 10, y0 - 36, 22, 'sans_light', GREY, a2, 'l', mode='O')
        f.text('示意', x1 - 20, y0, 22, 'sans_med', lerpc(GREY, WHITE, .3), a2 * 0.8, mode='O')
        cols = [CYAN, VIOLET, TEAL, PINK, BGOLD]
        slopes = [0.9, 0.55, 0.7, 1.25, 0.4]
        for i, (col, sl) in enumerate(zip(cols, slopes)):
            p = eo((t - b(20, 2) - i * BEAT * 0.5) / 1.6)
            if p <= 0: continue
            ya = y0 + 20 + i * 18
            yb = min(ya + sl * (x1 - x0) * 0.42, y1 - 6)
            xe = x0 + (x1 - x0) * p * (1 if yb < y1 - 6 else (y1 - 6 - ya) / (sl * (x1 - x0) * 0.42))
            ye = ya + (xe - x0) * sl * 0.42
            f.line((x0, ya), (xe, ye), col, a2, 3)
            f.glow((xe, ye), 8, col, a2, 'E')
        al3 = a2 * env(t, b(21, 2), b(23), 0.4, 0.3)
        f.text('直线 = 每段时间被淘汰的概率大致不变', (x0 + x1) / 2 + 80, 330, 28, 'sans_med', BGOLD, al3, mode='O')


RING = [(W / 2 + 330 * math.cos(q), 470 + 230 * math.sin(q)) for q in np.linspace(-math.pi / 2, 1.5 * math.pi, 8)[:-1]]


def sc_ring(f, t):
    if not (b(23) - 0.2 < t < b(25) + 0.2): return
    a = env(t, b(23), b(25), 0.35, 0.3)
    t0 = b(23)
    cols = [CYAN, TEAL, VIOLET, PINK, BGOLD, GREEN, BLUE]
    for i, p in enumerate(RING):   # 物种之间的相互作用
        for j in (i + 1, i + 3):
            q = RING[j % 7]
            f.line(p, q, GREY, a * 0.18, 1)
    # 连锁反应：每拍一个物种"进步"，冲击波让邻居的环境变差（变红）
    for i, p in enumerate(RING):
        hit = 0.0
        for k in range(12):
            src = (k * 3) % 7
            tk = t0 + k * BEAT
            if t < tk: break
            d = math.hypot(p[0] - RING[src][0], p[1] - RING[src][1])
            arr = tk + d / 900
            if src != i and t >= arr: hit = max(hit, math.exp(-(t - arr) / 0.35))
            if src == i:
                dt = t - tk
                f.circle(p, 30 + 900 * dt, cols[i], a * max(0, 1 - dt / 0.9) * 0.8, 2)
                f.glow(p, 40, cols[i], a * math.exp(-dt / 0.3), 'B')
        col = lerpc(cols[i], RED, cl(hit * 1.4))
        f.circle(p, 30, col, a, 3)
        f.glow(p, 8 + 6 * hit, lerpc(col, WHITE, .5), a, 'E')
        f.glow(p, 46, col, a * (0.25 + 0.5 * hit), 'B')
    f.text('一方进步 = 别人的环境变差', W / 2, 470, 30, 'sans_med', lerpc(RED, WHITE, .5), a * env(t, b(23, 2), b(25), .4, .3), mode='O')


def sc_card2(f, t):
    if not (b(25) - 0.1 < t < b(26) + 0.1): return
    floor(f, t, env(t, b(25), b(26), 0.3, 0.3), t * 2, TEAL, C(10, 70, 70), tile=0.5)
    mirror_card(f, t, b(25), b(26), '02', '没有终点的赛跑', 'THE ENDLESS RACE', TEAL)


_HR = np.random.default_rng(23)
LOCKS = _HR.uniform(0.15, 1.0, (12, 5))


def sc_host(f, t):
    if not (b(26) - 0.2 < t < b(32) + 0.2): return
    a = env(t, b(26), b(32), 0.4, 0.35)
    t0 = b(26)
    g = int((t - t0) // BAR)
    u = ((t - t0) % BAR) / BAR
    g = max(0, min(g, 10))
    L0, L1 = LOCKS[g], LOCKS[g + 1]
    Kp = LOCKS[g - 1] if g > 0 else LOCKS[11]
    # 病原体：钥匙演化到匹配当前的锁 → 对接；宿主：换锁 → 弹开
    key = Kp + (L0 - Kp) * eio(u / 0.3)
    lock = L0 + (L1 - L0) * eio((u - 0.55) / 0.25)
    dock = eio((u - 0.28) / 0.2) * (1 - eio((u - 0.62) / 0.25))
    HX = 790
    PX = HX + 6 + 300 * (1 - dock)
    infect = math.exp(-max(0, (u - 0.48)) * BAR / 0.25) if u >= 0.48 else 0
    defend = math.exp(-max(0, (u - 0.62)) * BAR / 0.3) if u >= 0.62 else 0
    ys = [340 + i * 56 for i in range(5)]
    # 宿主细胞
    hc = lerpc(CYAN, RED, 0.6 * infect)
    f.arc((HX - 240, 480), 250, -1.25, 1.25, hc, a, 3, 80)
    f.arc((HX - 240, 480), 270, -1.2, 1.2, hc, a * 0.35, 1, 80)
    for k in range(9):
        q = k * 0.7 + t * 0.4
        f.glow((HX - 330 + 70 * math.cos(q), 480 + 120 * math.sin(q * 1.3)), 6, lerpc(TEAL, WHITE, .3), a * 0.7, 'E')
    pts = [(HX, 320)]
    for i, y in enumerate(ys):
        d = lock[i] * 60
        pts += [(HX, y), (HX - d, y + 8), (HX - d, y + 48), (HX, y + 56)]
    pts.append((HX, 640))
    f.poly(pts, lerpc(CYAN, WHITE, 0.3 + 0.5 * defend), a, 3)
    f.glow((HX - 30, 480), 120, CYAN, a * (0.12 + 0.45 * defend), 'B')
    # 病原体
    pc = RED
    kp = [(PX, 320)]
    for i, y in enumerate(ys):
        d = key[i] * 60
        kp += [(PX, y + 6), (PX - d, y + 12), (PX - d, y + 44), (PX, y + 50)]
    kp.append((PX, 640))
    f.poly(kp, pc, a, 3)
    cx = PX + 170
    f.circle((cx, 480), 120, pc, a, 3)
    for k in range(14):
        q = k / 14 * 2 * math.pi + t * 0.3
        f.line((cx + 120 * math.cos(q), 480 + 120 * math.sin(q)), (cx + 150 * math.cos(q), 480 + 150 * math.sin(q)), pc, a * 0.8, 2)
        f.glow((cx + 155 * math.cos(q), 480 + 155 * math.sin(q)), 5, lerpc(pc, WHITE, .4), a * 0.8, 'E')
    f.glow((cx, 480), 130, RED, a * (0.15 + 0.5 * infect), 'B')
    f.text('宿主 · 锁', HX - 260, 250, 28, 'sans_med', CYAN, a, mode='O')
    f.text('病原体 · 钥匙', cx + 60, 290, 28, 'sans_med', RED, a, mode='O')
    f.text('第 %d 代' % (g + 1), W / 2, 160, 36, 'sans_black', BGOLD, a, mode='O')
    f.text('GENERATION', W / 2, 196, 16, 'orb', GREY, a * 0.7, mode='O', track=0.3)
    f.text('简化机制示意 · 非实验录像', W / 2, 700, 22, 'sans_light', lerpc(GREY, WHITE, .3), a * 0.9, mode='O')
    f.text('注：1973 年原始讨论与后来的宿主—病原体模型并不相同，此处借后者建立直觉', W / 2, 740, 20, 'sans_light', GREY,
           a * 0.75, mode='O')


def sc_firstp(f, t):
    if not (b(32) - 0.1 < t < b(33) + 0.2): return
    a = env(t, b(32), b(33), 0.3, 0.3)
    for k in range(3):   # 原子：拆到最基本
        q = k * math.pi / 3 + t * 0.6
        ts = np.linspace(0, 2 * math.pi, 120)
        ex, ey = 420 * np.cos(ts), 120 * np.sin(ts)
        pts = np.stack([W / 2 + ex * math.cos(q) - ey * math.sin(q), 520 + ex * math.sin(q) + ey * math.cos(q)], 1)
        f.poly(pts, [CYAN, BGOLD, VIOLET][k], a * 0.4, 2, closed=True)
        e = t * 2.2 + k * 2.1
        f.glow((W / 2 + 420 * math.cos(e) * math.cos(q) - 120 * math.sin(e) * math.sin(q),
                520 + 420 * math.cos(e) * math.sin(q) + 120 * math.sin(e) * math.cos(q)), 6, WHITE, a, 'E')
    f.glow((W / 2, 520), 160, BGOLD, a * 0.25, 'B')


def sc_compare(f, t):
    if not (b(33) - 0.1 < t < b(36) + 0.2): return
    a = env(t, b(33), b(36), 0.35, 0.3)
    me, ri = 0.78, 0.6
    for i, (x, name, col, v) in enumerate(((640, '你', CYAN, me), (1280, '对手', RED, ri))):
        p = eo((t - b(33) - i * BEAT) / 0.5)
        al = a * p
        f.rrect_fill(x - 170, 300, x + 170, 700, 26, col, al * 0.08)
        f.rrect(x - 170, 300, x + 170, 700, 26, col, al, 2)
        f.text(name, x, 350, 40, 'sans_black', lerpc(col, WHITE, .4), al, mode='O')
        f.text('产品力', x, 650, 24, 'sans_light', GREY, al, mode='O')
        hh = 230 * v * eo((t - b(33) - 0.4 - i * BEAT) / 0.8)
        f.fillpoly([(x - 50, 620), (x + 50, 620), (x + 50, 620 - hh), (x - 50, 620 - hh)], col, al * 0.35)
        f.poly([(x - 50, 620), (x - 50, 620 - hh), (x + 50, 620 - hh), (x + 50, 620)], col, al, 2)
        f.glow((x, 620 - hh), 30, col, al * 0.5, 'B')
    # 顾客的眼睛：来回比较
    ex, ey = W / 2, 320
    look = math.sin(t * 2.6) * 22
    al = a * eo((t - b(33)) / 0.5)
    f.arc((ex, ey + 40), 70, -math.pi * 0.8, -math.pi * 0.2, WHITE, al, 2)
    f.arc((ex, ey - 40), 70, math.pi * 0.2, math.pi * 0.8, WHITE, al, 2)
    f.circle((ex + look, ey), 18, BGOLD, al, 2); f.glow((ex + look, ey), 7, WHITE, al, 'E')
    f.text('顾客', ex, ey + 70, 22, 'sans_light', GREY, al, mode='O')
    # 差值
    if t > b(34, 2):
        p = eo((t - b(34, 2)) / 0.6) * a
        y1, y2 = 620 - 230 * me, 620 - 230 * ri
        f.line((690, y1), (1330, y1), BGOLD, p * 0.6, 1)
        f.line((1330, y1), (1330, y2), BGOLD, p, 3)
        f.glow((1330, (y1 + y2) / 2), 20, BGOLD, p * 0.6, 'B')
        f.text('差多少？', 1530, (y1 + y2) / 2, 30, 'sans_black', BGOLD, p, mode='O')


def sc_graph(f, t):
    if not (b(36) - 0.1 < t < b(41) + 0.1): return
    a = env(t, b(36), b(41) - 0.25, 0.35, 0.2)
    x0, x1, y0, y1 = 420, 1500, 230, 740
    f.line((x0, y1), (x1, y1), GREY, a * 0.7, 2); f.line((x0, y1), (x0, y0), GREY, a * 0.7, 2)
    f.text('时间', x1 - 20, y1 + 30, 22, 'sans_light', GREY, a, mode='O')
    f.text('产品力', x0 - 10, y0 - 26, 22, 'sans_light', GREY, a, 'l', mode='O')
    acc = eio((t - b(39)) / (BAR * 2))   # 对手一样快：两条线一起变陡

    def curve(off, p):
        xs = np.linspace(x0, x0 + (x1 - x0) * p, 80)
        u = (xs - x0) / (x1 - x0)
        ys = y1 - 60 - off - (u * 260 + acc * u ** 2.2 * 180)
        return np.stack([xs, ys], 1)
    pm = eo((t - b(36)) / (BAR * 1.2))
    pr = eo((t - b(37, 2)) / (BAR * 0.9))
    me = curve(110, pm)
    f.poly(me, CYAN, a, 4); f.glow(tuple(me[-1]), 10, WHITE, a, 'E'); f.glow(tuple(me[-1]), 30, CYAN, a * 0.6, 'B')
    f.text('你', me[-1][0] + 34, me[-1][1], 28, 'sans_black', CYAN, a * pm, mode='O')
    if pm > 0.2:   # 绝对进步
        al = a * env(t, b(36, 1), b(41), 0.4, 0.2)
        xa = x0 + (x1 - x0) * 0.3
        ya0 = y1 - 60 - 110
        ya1 = me[int(0.3 / max(pm, 0.3) * 79)][1] if pm >= 0.3 else ya0
        arrow(f, (xa - 40, y1 - 40), (xa - 40, ya1 + 10), CYAN, al * 0.8, 2, 12)
        f.text('绝对进步', xa - 60, (y1 - 40 + ya1) / 2, 26, 'sans_med', CYAN, al, 'r', mode='O')
    if pr > 0:
        rv = curve(0, pr)
        mm = curve(110, pr)
        f.fillpoly(np.concatenate([mm, rv[::-1]]), BGOLD, a * 0.16 * (1 + 0.4 * beat_pulse(t)))
        f.poly(rv, RED, a, 4); f.glow(tuple(rv[-1]), 10, WHITE, a, 'E'); f.glow(tuple(rv[-1]), 30, RED, a * 0.6, 'B')
        f.text('对手', rv[-1][0] + 44, rv[-1][1], 28, 'sans_black', RED, a * pr, mode='O')
        i = int(0.65 * 79 * pr)
        xm, ym1, ym2 = mm[i][0], mm[i][1], rv[i][1]
        f.line((xm, ym1), (xm, ym2), BGOLD, a * pr, 3)
        for yy in (ym1, ym2): f.line((xm - 10, yy), (xm + 10, yy), BGOLD, a * pr, 3)
        f.text('相对优势', xm + 20, (ym1 + ym2) / 2, 30, 'sans_black', BGOLD, a * pr, 'l', mode='O')
        if acc > 0:
            f.text('差距：还是这么多', xm + 20, (ym1 + ym2) / 2 + 40, 22, 'sans_light', BGOLD_L, a * acc, 'l', mode='O')
    implode(f, t, b(39, 2), b(41), W / 2, 470, [BGOLD, CYAN, RED, WHITE, BGOLD_L, AMBER], 0.6, R0=900)


def sc_formula(f, t):
    if not (b(41) - 0.1 < t < b(44, 2) + 0.3): return
    a = env(t, b(41), b(44, 2), 0.15, 0.35)
    burst(f, t, b(41), W / 2, 470, [BGOLD, BGOLD_L, AMBER, WHITE, CYAN, RED], 1, 900, 1900, 1.6)
    toks = [('相对优势', BGOLD, True), ('=', WHITE, False), ('你的进步', CYAN, True), ('−', WHITE, False), ('对手的进步', RED, True)]
    appear = [b(41) + i * BEAT for i in range(5)]
    size = 64
    fnt = 'serif_black'
    pads = size * 0.55
    widths = [text_width(s, fnt, size) + (2 * pads if term else 0) for s, c, term in toks]
    gap = 0.45 * size
    x = W / 2 - (sum(widths) + gap * 4) / 2
    cy = 430
    centers = []
    for i, ((s, col, term), w) in enumerate(zip(toks, widths)):
        p = cl((t - appear[i]) / 0.35)
        xc = x + w / 2
        centers.append(xc)
        if p > 0:
            al = a * eo(p)
            sc_ = 1 + 0.35 * (1 - eback(p, 2.2))
            sz = max(8, int(round(size * sc_)))
            if term:
                hw = w / 2 * sc_; hh = size * 0.9 * sc_
                f.rrect_fill(xc - hw, cy - hh, xc + hw, cy + hh, hh * 0.9, col, 0.14 * al)
                f.rrect(xc - hw, cy - hh, xc + hw, cy + hh, hh * 0.9, col, al, 3)
                f.glow((xc, cy), hw * 0.5, col, 0.2 * al * (1 + bar_pulse(t)), 'B')
                f.text(s, xc, cy, sz, fnt, lerpc(col, WHITE, 0.55), al, mode='O', glow=0.3)
            else:
                f.text(s, xc, cy, sz, fnt, col, al, mode='O', glow=0.4)
        x += w + gap
    # 复制：你的进步 → 对手的进步（粒子流），对手的条追上来，结果 → 0
    tc = b(42, 2)
    if t > tc:
        p = eo((t - tc) / (BAR * 0.8))
        s_ = (np.arange(260) / 260 + t * 0.6) % 1.0
        pts = bez((centers[2], cy + 70), (centers[2] + 60, cy + 230), (centers[4] - 60, cy + 230), (centers[4], cy + 70), s_)
        f.splat(pts[:, 0], pts[:, 1], BGOLD, a * p * np.sin(s_ * math.pi) * 1.8, 'E')
        f.text('复制', (centers[2] + centers[4]) / 2, cy + 230, 26, 'sans_med', BGOLD_L, a * p, mode='O')
        bw = 140
        for (cxx, col, v) in ((centers[2], CYAN, 1.0), (centers[4], RED, 0.45 + 0.55 * p)):
            f.fillpoly([(cxx - bw / 2, cy + 120), (cxx - bw / 2 + bw * v, cy + 120), (cxx - bw / 2 + bw * v, cy + 132), (cxx - bw / 2, cy + 132)], col, a * 0.8, 'E')
        if t > b(43):
            q = eo((t - b(43)) / 0.4)
            f.text('≈ 0', centers[0], cy + 140, 72, 'sans_black', lerpc(RED, WHITE, .2), a * q, mode='O', glow=0.6)


def loom(f, t, cx, cy, w, h, a, col=AMBER, speed=1.0, tag=None):
    if a <= 0.003: return
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    f.rrect(x0 - 20, y0 - 20, x1 + 20, y1 + 20, 14, col, a * 0.6, 2)
    yf = y0 + h * 0.55
    n = 26
    ph = int((t * speed) / BEAT) % 2
    for i in range(n):
        x = x0 + (i + 0.5) * w / n
        sh = (10 if (i % 2) == ph else -10) * (w / 700)
        f.poly([(x, y0), (x, (y0 + yf) / 2 + sh), (x, yf)], lerpc(col, WHITE, .2), a * 0.55, 1)
    u = ((t * speed) / BEAT) % 2
    sx = x0 + w * (u if u < 1 else 2 - u)
    sy = (y0 + yf) / 2
    f.line((sx - 22 * w / 700, sy), (sx + 22 * w / 700, sy), WHITE, a, 5)
    f.glow((sx, sy), 14 * w / 700 + 4, col, a * 0.9, 'B'); f.glow((sx, sy), 5, WHITE, a, 'E')
    off = (t * speed * 14) % 8
    for k in range(int((y1 - yf) / 8)):   # 织好的布
        yy = yf + 4 + k * 8 + off
        if yy > y1: break
        f.line((x0, yy), (x1, yy), col, a * 0.35, 1)
    f.glow(((x0 + x1) / 2, (yf + y1) / 2), w * 0.3, col, a * 0.12, 'B')
    gear(f, x0 - 10, y1 + 30, 38 * w / 700, 9, t * speed * 1.5, col, a * 0.8)
    gear(f, x1 + 10, y1 + 30, 30 * w / 700, 7, -t * speed * 1.9, col, a * 0.8)
    if tag:
        f.text(tag, cx, y0 - 50, int(28 * max(w / 700, 0.7)), 'sans_med', lerpc(col, WHITE, .4), a, mode='O')


def sc_textile(f, t):
    if not (b(44, 2) - 0.2 < t < b(50) + 0.3): return
    a = env(t, b(44, 2), b(50), 0.4, 0.3)
    flow(f, t, a * 0.25 * env(t, b(44, 2), b(45, 2), 0.3, 0.4), [AMBER, BGOLD, BGOLD_L, ORANGE, AMBER, WHITE], 90, 1400)
    al = a * env(t, b(45, 2) - 0.2, b(50), 0.4, 0.3)
    side = eo((t - b(48, 2)) / 0.8)
    wM = 700 - 260 * side
    loom(f, t, W / 2, 470, wM, 360 - 120 * side, al, AMBER, 1.0, '伯克希尔 · 纺织厂' if side < 0.5 else '伯克希尔')
    if side > 0:
        for k, x in enumerate((W / 2 - 560, W / 2 + 560)):
            loom(f, t + k * 0.3, x - (1 - side) * 400 * (1 if k == 0 else -1), 470, 440, 240, al * side, lerpc(AMBER, RED, .35), 1.0, '同行')
    if t > b(47):   # 降本设备投资：每一笔都划算
        for k in range(4):
            tk = b(47) + k * BEAT
            p = eo((t - tk) / 0.4)
            if p <= 0: continue
            xs = [W / 2 - 200, W / 2 - 70, W / 2 + 70, W / 2 + 200][k] * (1 - side) + (W / 2 + (k - 1.5) * 90) * side
            yy = 196 - 20 * p + 24 * side
            chip(f, '+效率', xs, yy, 22, BGOLD, al * p)
            if side > 0:
                for x2 in (W / 2 - 560, W / 2 + 560):
                    chip(f, '+效率', x2 + (k - 1.5) * 90, yy + 60, 18, lerpc(BGOLD, RED, .3), al * side * p)


def sc_crowd(f, t):
    if not (b(50) - 0.2 < t < b(54) + 0.3): return
    a = env(t, b(50), b(54), 0.4, 0.3)
    # 游行队伍：远处一条流光带（被人群挡住）
    py = 640
    for k in range(60):
        x = (k * 70 + t * 120) % (W + 200) - 100
        col = [BGOLD, RED, CYAN, MAGENTA, BGOLD_L][k % 5]
        f.glow((x, py + 10 * math.sin(k + t * 2)), 9, col, a * 0.9, 'E')
        f.glow((x, py), 22, col, a * 0.14, 'B')
    f.B[py - 60:py + 60] += (np.exp(-((np.arange(120) - 60) / 30.0) ** 2)[:, None, None] * np.array(AMBER, np.float32) * 0.12 * a)
    t1, t2 = b(51), b(52)
    n = 13
    for i in range(n):
        x = 90 + i * (W - 180) / (n - 1)
        me = (i == 6)
        lift = 0.0
        if me: lift = eback(cl((t - t1) / 0.45), 2.0)
        else: lift = eback(cl((t - t2 - abs(i - 6) * 0.04) / 0.45), 2.0)
        wob = math.sin(t * 9 + i) * 2 * cl((t - t2 - 0.6) / 0.5)
        yb = 1050 - 55 * lift + wob
        s = 92 + (i % 3) * 6
        col = CYAN if me else lerpc(AMBER, WHITE, .3)
        person(f, x, yb, s, col, a, True)
    # 视线：踮脚的那个人先看到了，大家都踮脚后，又看不到了
    me_x = 90 + 6 * (W - 180) / (n - 1)
    eye_y = 1050 - 55 * eback(cl((t - t1) / 0.45), 2.0) - 98 * 1.55
    see = env(t, t1 + 0.3, t2 + 0.3, 0.3, 0.25)
    if see > 0:
        f.line((me_x, eye_y), (me_x + 380, py), BGOLD, a * see, 2)
        f.glow((me_x + 380, py), 30, BGOLD, a * see, 'B')
        f.text('看到了！', me_x + 240, eye_y - 60, 30, 'sans_black', BGOLD, a * see, mode='O')
    if t > t2 + 0.6:
        al = a * env(t, t2 + 0.6, b(54), 0.4, 0.3)
        f.text('人人踮脚 = 谁也没看得更清楚，只是更累', W / 2, 740, 28, 'sans_med', BGOLD_L, al, mode='O')


def sc_y1985(f, t):
    if not (b(54) - 0.2 < t < b(57) + 0.1): return
    a = env(t, b(54), b(55, 1), 0.3, 0.3)
    if a > 0:
        loom(f, t * 0.2, W / 2, 560, 600, 300, a * 0.35, lerpc(AMBER, GREY, .6), 0.2)
        f.text('1985', W / 2, 330, 150, 'orb', lerpc(AMBER, GREY, .3), a * 0.35, mode='E')
    a2 = env(t, b(55, 1), b(57), 0.3, 0.2)
    if a2 > 0:   # 钱：飘走
        rng = np.random.default_rng(4)
        n = 420
        x0 = rng.uniform(0, W, n); y0 = rng.uniform(250, 800, n); sp = rng.uniform(0.5, 1.5, n)
        dt = t - b(55, 1)
        xs = x0 + dt * 260 * sp
        ys = y0 - dt * 60 * sp + 12 * np.sin(dt * 3 + x0)
        f.splat(xs % (W + 100), ys, BGOLD, a2 * 1.2, 'E')
    implode(f, t, b(56), b(57), W / 2, 520, [BGOLD, BLUE, CYAN, WHITE, BGOLD_L, VIOLET], 0.7)


def sc_mloom(f, t):
    if not (b(57) - 0.1 < t < b(62) + 0.2): return
    a = env(t, b(57), b(62), 0.5, 0.35)
    burst(f, t, b(57), W / 2, 520, [BLUE, CYAN, WHITE, VIOLET, BLUE, BGOLD], 2, 500, 900, 1.6)
    newp = eo((t - b(58, 2)) / 0.7)
    loom(f, t, W / 2 - 330 * newp, 470, 520 - 80 * newp, 300, a, lerpc(BLUE, GREY, .3 * newp), 1.0, '旧织机')
    if newp > 0:
        loom(f, t, W / 2 + 330, 470, 440 + 60 * newp, 300, a * newp, CYAN, 2.0, '新织机  产能 ×2')
    if t > b(60):   # 巴菲特：要是管用，就得关掉工厂
        p = env(t, b(60, 2), b(62), 0.4, 0.3)
        f.text('?', W / 2, 260, 80, 'serif_black', BGOLD, p, mode='O', glow=0.5)


def sc_sankey(f, t):
    if not (b(62) - 0.2 < t < b(65) + 0.2): return
    a = env(t, b(62), b(65), 0.4, 0.3)
    L = (430, 800); R1 = (1480, 720); R2 = (1480, 930)
    f.circle(L, 52, CYAN, a, 3); f.glow(L, 70, CYAN, a * 0.4, 'B')
    f.text('生产率提升', L[0], L[1] + 82, 26, 'sans_med', CYAN, a, mode='O')
    big = 60 + 10 * beat_pulse(t, 0.2)
    f.circle(R1, big, BGOLD, a, 3); f.glow(R1, 110, BGOLD, a * 0.5, 'B')
    f.text('买家', R1[0] + 110, R1[1], 32, 'sans_black', BGOLD, a, 'l', mode='O')
    f.circle(R2, 30, GREY, a * 0.6, 2)
    f.text('所有者：0', R2[0] + 60, R2[1], 28, 'sans_med', GREY, a, 'l', mode='O')
    p = eo((t - b(62, 1)) / 1.0)
    s_ = (np.arange(900) / 900 * 3 + t * 0.35) % 1.0
    jit = np.sin(np.arange(900) * 12.9898) * 18
    pts = bez(L, (L[0] + 450, L[1]), (R1[0] - 450, R1[1]), R1, s_ * p)
    f.splat(pts[:, 0], pts[:, 1] + jit, BGOLD, a * np.sin(np.clip(s_ * p, 0, 1) * math.pi) * 1.5, 'E')
    # 流向所有者：几乎没有
    pts2 = bez(L, (L[0] + 450, L[1] + 40), (R2[0] - 450, R2[1]), R2, s_[:40] * p * 0.35)
    f.splat(pts2[:, 0], pts2[:, 1], GREY, a * 0.5, 'L')


def sc_tech(f, t):
    if not (b(65) - 0.2 < t < b(67) + 0.2): return
    a = env(t, b(65), b(67), 0.4, 0.3)
    c = (W / 2, 220)
    f.rrect(c[0] - 46, c[1] - 46, c[0] + 46, c[1] + 46, 10, WHITE, a * 0.8, 2)
    for k in range(5):
        for s_ in (-1, 1):
            f.line((c[0] - 36 + k * 18, c[1] + s_ * 46), (c[0] - 36 + k * 18, c[1] + s_ * 62), WHITE, a * 0.6, 2)
            f.line((c[0] + s_ * 46, c[1] - 36 + k * 18), (c[0] + s_ * 62, c[1] - 36 + k * 18), WHITE, a * 0.6, 2)
    f.text('技术', c[0], c[1], 28, 'sans_black', WHITE, a, mode='O')
    p = eo((t - b(65, 2)) / 0.6)
    arrow(f, (c[0] - 70, c[1] + 50), (c[0] - 70 - 520 * p, 740), TEAL, a * p, 3, 18)
    arrow(f, (c[0] + 70, c[1] + 50), (c[0] + 70 + 520 * p, 740), RED, a * p, 3, 18)
    f.text('帮你', c[0] - 640, 790, 40, 'sans_black', TEAL, a * p, mode='O', glow=0.4)
    f.text('杀死你', c[0] + 640, 790, 40, 'sans_black', RED, a * p, mode='O', glow=0.4)


def sc_q2(f, t):
    if not (b(67) - 0.1 < t < b(69) + 0.1): return
    implode(f, t, b(67), b(69), W / 2, 520, [CRIMSON, CYAN, BGOLD, WHITE, BGOLD_L, AMBER], 1.0)


PILLARS = [('①', '保住资格', CRIMSON, 480), ('②', '改善用户价值', CYAN, 960), ('③', '积累可持续能力', BGOLD, 1440)]


def pillar_icon(f, t, i, cx, cy, col, a):
    if i == 0:   # 跑步机：原地打转
        f.arc((cx, cy), 80, 0.3, 2 * math.pi - 0.3, col, a, 3, 60)
        q = 2 * math.pi - 0.3
        arrow(f, (cx + 80 * math.cos(q - 0.2), cy + 80 * math.sin(q - 0.2)), (cx + 80 * math.cos(q), cy + 80 * math.sin(q)), col, a, 3, 14)
        e = t * 4.2
        comet(f, cx + 80 * math.cos(e), cy + 80 * math.sin(e), 12, col, a)
    elif i == 1:  # 价值流向用户
        f.rrect(cx - 110, cy - 30, cx - 50, cy + 30, 8, col, a, 2)
        s_ = (np.arange(60) / 60 + t * 0.7) % 1.0
        xs = cx - 50 + s_ * 140; ys = cy + np.sin(s_ * 6 + t * 3) * 10
        f.splat(xs, ys, BGOLD, a * np.sin(s_ * math.pi) * 2, 'E')
        f.circle((cx + 105, cy - 30), 18, col, a, 2)
        f.arc((cx + 105, cy + 30), 34, math.pi, 2 * math.pi, col, a, 2)
    else:         # 护城河：越积越厚
        f.rrect(cx - 24, cy - 24, cx + 24, cy + 24, 4, col, a, 3)
        nring = 1 + int(cl((t - b(74, 2)) / (BAR * 2)) * 4) if t > b(74, 2) else 1
        for k in range(nring + 1):
            r = 42 + k * 16
            f.circle((cx, cy), r, col, a * (0.9 - k * 0.12), 2 + (1 if k < nring else 0))
        f.glow((cx, cy), 60, col, a * 0.16 * (1 + 0.5 * beat_pulse(t)), 'B')


def sc_three(f, t):
    if not (b(69) - 0.1 < t < b(79, 2) + 0.3): return
    a = env(t, b(69), b(79, 2), 0.2, 0.4)
    burst(f, t, b(69), W / 2, 470, [CRIMSON, CYAN, BGOLD, WHITE, BGOLD_L, CYAN], 4, 900, 1900, 1.6)
    ta = env(t, b(69), b(70, 2) + 0.3, 0.1, 0.5)
    if ta > 0:   # 重拍后：三颗光球环绕（三种投入的预告）
        for i, col in enumerate((CRIMSON, CYAN, BGOLD)):
            ang = (t - b(69)) * 1.6 + i * 2 * math.pi / 3
            r = 260 * eo((t - b(69)) / 0.8)
            x, y = W / 2 + r * math.cos(ang), 450 + r * 0.42 * math.sin(ang)
            comet(f, x, y, 26, col, ta)
            for k in range(1, 14):
                q = ang - k * 0.06
                f.glow((W / 2 + r * math.cos(q), 450 + r * 0.42 * math.sin(q)), 7, col, ta * (1 - k / 14) * 0.7, 'E')
        f.glow((W / 2, 450), 90, BGOLD_L, ta * 0.25 * (1 + beat_pulse(t)), 'B')
    focus = None
    for i, tt in enumerate((b(70, 2), b(72, 2), b(74, 2))):
        if tt <= t < tt + 2 * BAR: focus = i
    quote = t >= b(76, 2)
    for i, (num, name, col, x) in enumerate(PILLARS):
        p = eo((t - (b(70, 2), b(72, 2), b(74, 2))[i]) / 0.45)
        if p <= 0: continue
        dim = 1.0 if focus in (None, i) else 0.45
        if quote: dim = 1.0 if i == 2 else 0.35
        al = a * p * dim
        y0, y1 = 220 - 40 * (1 - p), 660 - 40 * (1 - p)
        f.rrect_fill(x - 200, y0, x + 200, y1, 24, col, al * 0.07)
        f.rrect(x - 200, y0, x + 200, y1, 24, col, al, 3 if focus == i else 2)
        f.text(num, x, y0 + 60, 44, 'serif_black', col, al, mode='O', glow=0.4)
        pillar_icon(f, t, i, x, (y0 + y1) / 2 + 10, col, al)
        f.text(name, x, y1 - 70, 38, 'sans_black', lerpc(col, WHITE, .45), al, mode='O', glow=0.3)
        if focus == i:
            f.glow((x, (y0 + y1) / 2), 180, col, a * 0.1 * (1 + 0.5 * bar_pulse(t)), 'B')
    if quote:   # 巴菲特：优势的持久性 —— 护城河光环
        p = eo((t - b(76, 2)) / 1.2) * a
        for k in range(3):
            r = 230 + k * 40 + 10 * math.sin(t * 2 + k)
            f.circle((1440, 440), r, BGOLD, p * (0.6 - k * 0.15), 2)
        f.glow((1440, 440), 260, BGOLD, p * 0.06, 'B')


def loop_nodes(f, t, cx, cy, rx, ry, labels, cols, t0, a, speed=0.35, size=30, chip_fill=0.12, ang0=-math.pi / 2):
    """环形流程图：节点按拍依次出现，箭头首尾相接，一颗光点沿环奔跑"""
    n = len(labels)
    P = [(cx + rx * math.cos(ang0 + k * 2 * math.pi / n), cy + ry * math.sin(ang0 + k * 2 * math.pi / n)) for k in range(n)]
    for k in range(n):
        p = eo((t - t0 - k * BEAT) / 0.4) * a
        if p <= 0: continue
        q0 = ang0 + k * 2 * math.pi / n + 0.32; q1 = ang0 + (k + 1) * 2 * math.pi / n - 0.32
        qs = np.linspace(q0, q0 + (q1 - q0) * p, 30)
        pts = np.stack([cx + rx * np.cos(qs), cy + ry * np.sin(qs)], 1)
        f.poly(pts, lerpc(cols[k], WHITE, .2), p * 0.7, 2)
        if p > 0.95:
            arrow(f, tuple(pts[-3]), tuple(pts[-1]), lerpc(cols[k], WHITE, .2), p * 0.8, 2, 12)
        chip(f, labels[k], P[k][0], P[k][1], size, cols[k], p, 'sans_black', chip_fill)
    if t > t0 + n * BEAT * 0.6:
        e = ang0 + (t - t0) * speed * 2 * math.pi
        comet(f, cx + rx * math.cos(e), cy + ry * math.sin(e), 12, WHITE, a * 0.9)
    return P


def sc_cycle(f, t):
    if not (b(79, 2) - 0.2 < t < b(81, 2) + 0.2): return
    a = env(t, b(79, 2), b(81, 2), 0.35, 0.3)
    labels = ['创新', '模仿', '标配化', '优势消失']
    cols = [BGOLD, ORANGE, CRIMSON, GREY]
    loop_nodes(f, t, W / 2, 450, 380, 190, labels, cols, b(79, 2), a, 0.45, 34)
    f.text('红皇后循环', W / 2, 440, 34, 'serif_black', lerpc(CRIMSON, WHITE, .3), a * eo((t - b(80)) / 0.5), mode='O', glow=0.4)
    f.text('↻ 转一圈，回到原点', W / 2, 490, 22, 'sans_light', GREY, a * eo((t - b(80, 2)) / 0.5), mode='O')
    f.glow((W / 2, 450), 160, CRIMSON, a * 0.12 * (1 + beat_pulse(t)), 'B')


def sc_ai(f, t):
    """大模型竞赛：五家厂商的资本开支同步上涨，一家领先，其余很快跟上"""
    if not (b(81, 2) - 0.2 < t < b(85) + 0.2): return
    a = env(t, b(81, 2), b(85), 0.35, 0.3)
    t0 = b(81, 2)
    n = 5
    xs = [W / 2 + (i - 2) * 230 for i in range(n)]
    base_y = 700
    f.line((xs[0] - 140, base_y), (xs[-1] + 140, base_y), GREY, a * 0.6, 1)
    f.text('资本开支 · 算力投入', W / 2, 205, 30, 'sans_black', lerpc(CYAN, WHITE, .4), a, mode='O')
    f.text('示意', xs[-1] + 120, 205, 20, 'sans_light', GREY, a * 0.8, mode='O')
    k = int(max(t - t0, 0) / BEAT)
    for i, x in enumerate(xs):
        grow = 90 + 300 * eio(cl((t - t0) / (BAR * 3.2)))
        lead = 0.0
        for j in range(k + 1):     # 每拍一家发布新模型、领先一截，其余在一拍内跟上
            if j % n == i:
                dt = t - (t0 + j * BEAT)
                lead = max(lead, 60 * math.exp(-max(dt - 0.15, 0) / 0.35) * cl(dt / 0.1))
        h = grow + lead
        p = eo((t - t0 - i * 0.1) / 0.5) * a
        col = lerpc(CYAN, VIOLET, i / 4)
        f.rrect_fill(x - 55, base_y - h, x + 55, base_y, 8, col, p * 0.22)
        f.rrect(x - 55, base_y - h, x + 55, base_y, 8, col, p, 2)
        for r in range(int(h // 34)):   # 机柜里的 GPU
            yy = base_y - 20 - r * 34
            f.line((x - 38, yy), (x + 38, yy), lerpc(col, WHITE, .4), p * 0.5, 2)
            f.glow((x + 30, yy), 2.5, TEAL if (r + i + int(t * 6)) % 3 else WHITE, p, 'E')
        if lead > 20:
            f.text('新模型', x, base_y - h - 34, 24, 'sans_black', BGOLD, p * cl(lead / 60), mode='O', glow=0.4)
            f.glow((x, base_y - h), 40, BGOLD, p * cl(lead / 60) * 0.6, 'B')
        f.text('厂商', x, base_y + 30, 22, 'sans_light', GREY, p, mode='O')
    if t > b(83):
        al = a * eo((t - b(83)) / 0.5)
        arrow(f, (xs[-1] + 150, base_y - 40), (xs[-1] + 150, 300), CRIMSON, al, 3, 16)
        f.text('不投就掉队', xs[-1] + 150, 270, 24, 'sans_black', CRIMSON, al, mode='O')


MOATS = ['强品牌', '网络效应', '低成本结构', '独占渠道', '高切换成本', '专利', '监管牌照', '独特生态']


def moat_pos(i):
    return W / 2 + (i % 4 - 1.5) * 330, 420 + (i // 4) * 130


def sc_moats(f, t):
    if not (b(85) - 0.1 < t < b(90, 2) + 0.2): return
    a1 = env(t, b(85), b(86, 2), 0.3, 0.3)
    if a1 > 0:   # 循环被打破
        for k in range(10):
            q0 = k / 10 * 2 * math.pi + t * 0.3
            d = 40 * eo((t - b(85)) / 1.2)
            cx, cy = W / 2 + d * math.cos(q0 + 0.3), 520 + d * math.sin(q0 + 0.3) * 0.5
            qs = np.linspace(q0, q0 + 0.45, 12)
            f.poly(np.stack([cx + 420 * np.cos(qs), cy + 210 * np.sin(qs)], 1), CRIMSON, a1 * 0.6, 3)
    a = env(t, b(86, 2), b(90, 2), 0.3, 0.5)
    if a <= 0: return
    merge = eio((t - b(89, 2)) / (BAR * 0.9))
    for i, name in enumerate(MOATS):
        p = eo((t - b(86, 2) - i * BEAT / 2) / 0.35) * a
        x, y = moat_pos(i)
        x = lerp(x, W / 2, merge); y = lerp(y, 470, merge)
        col = lerpc(BGOLD, [CYAN, VIOLET, TEAL, ORANGE][i % 4], 0.35)
        chip(f, name, x, y, 36 * (1 - 0.6 * merge), col, p * (1 - merge * 0.9), 'sans_black', 0.14)
    f.glow((W / 2, 470), 120 + 120 * merge, BGOLD, a * (0.1 + 0.35 * merge), 'B')


def sc_flywheel(f, t):
    if not (b(90, 2) - 0.1 < t < b(93) + 0.1): return
    a = env(t, b(90, 2), b(93) - 0.2, 0.3, 0.25)
    grow = 1 + 0.25 * eio((t - b(90, 2)) / (BAR * 2.5))
    labels = ['优势', '更多用户', '更多资源', '更大优势']
    cols = [BGOLD, CYAN, TEAL, BGOLD_L]
    loop_nodes(f, t, W / 2, 470, 360 * grow, 175 * grow, labels, cols, b(90, 2), a, 0.3 + 0.4 * (grow - 1) * 4, 32, 0.16)
    f.text('马太效应', W / 2, 470, 40, 'serif_black', BGOLD, a * eo((t - b(91, 2)) / 0.5), mode='O', glow=0.5)
    for k in range(3):   # 越转越大
        f.circle((W / 2, 470), (120 + 40 * k) * grow, BGOLD, a * 0.15, 1)
    implode(f, t, b(92), b(93), W / 2, 470, [BGOLD, CYAN, WHITE, BGOLD_L, TEAL, AMBER], 0.6, R0=800)


def treadmill(f, t, cx, cy, w, a, col=GREY, belt_speed=1.0):
    """侧视跑步机：两个滚轮 + 移动的皮带纹路；返回皮带顶面的 y"""
    if a <= 0.003: return cy - 18
    x0, x1 = cx - w / 2, cx + w / 2
    r = 18
    f.arc((x0, cy), r, math.pi / 2, 1.5 * math.pi, col, a, 2, 20)
    f.arc((x1, cy), r, -math.pi / 2, math.pi / 2, col, a, 2, 20)
    f.line((x0, cy - r), (x1, cy - r), col, a, 3)
    f.line((x0, cy + r), (x1, cy + r), col, a * 0.6, 2)
    off = (t * belt_speed * 160) % 40
    for k in range(int(w // 40) + 1):
        xx = x1 - k * 40 - off
        if x0 < xx < x1:
            f.line((xx, cy - r - 3), (xx - 12, cy - r - 3), lerpc(col, WHITE, .3), a * 0.7, 2)
    for xx in (x0, x1):
        f.circle((xx, cy), r * 0.45, col, a * 0.8, 2)
    f.line((x1 - 20, cy - r), (x1 + 20, cy - 150), col, a * 0.7, 2)   # 扶手
    f.line((x1 + 20, cy - 150), (x1 - 40, cy - 150), col, a * 0.7, 2)
    return cy - r


def runner_on(f, t, x, ytop, col, a, s=16):
    bob = abs(math.sin(math.pi * t / (BEAT / 2))) * 10
    comet(f, x, ytop - s - 6 - bob, s, col, a)
    for k in range(6):   # 速度线
        ph = (t * 3 + k * 0.17) % 1
        yy = ytop - s - 14 - bob + (k - 2.5) * 6
        f.line((x - s - 10 - ph * 70, yy), (x - s - 40 - ph * 70, yy), lerpc(col, WHITE, .3), a * (1 - ph) * 0.6, 2)


def jump_runner(f, t, tj, x0, y0, col, a, dist=620, s=18):
    """tj 时刻从跑步机跳下，落到地面继续向前"""
    u = cl((t - tj) / (BEAT * 1.5))
    if t < tj:
        runner_on(f, t, x0, y0, col, a, s); return
    x = x0 + dist * eio(u) + (t - tj - BEAT * 1.5) * 90 * (u >= 1)
    y = y0 - s - 6 - math.sin(u * math.pi) * 160 + (u * 60)
    for k in range(18):   # 光迹
        uu = cl(u - k * 0.03)
        xx = x0 + dist * eio(uu); yy = y0 - s - 6 - math.sin(uu * math.pi) * 160 + uu * 60
        f.glow((xx, yy), 6, col, a * (1 - k / 18) * 0.6, 'E')
    comet(f, min(x, W - 120), y, s, col, a)


def sc_escape(f, t):
    if not (b(93) - 0.1 < t < b(94) + 0.2): return
    a = env(t, b(93), b(94), 0.15, 0.3)
    burst(f, t, b(93), W / 2, 560, [BGOLD, CYAN, WHITE, BGOLD_L, TEAL, AMBER], 6, 900, 1900, 1.6)
    rich_line(f, '最重要的一点', W / 2, 190, 30, 'sans_med', BGOLD, a=a, t0=b(93), stag=0.03, underline=False, track=0.2)
    ytop = treadmill(f, t, W / 2 - 200, 720, 560, a, lerpc(CRIMSON, GREY, .3), 2.0)
    floor(f, t, a * eo((t - b(93, 2)) / 0.6), t * 3, BGOLD, C(80, 55, 20), tile=0.5, fill=0.08, hor=760)
    jump_runner(f, t, b(93, 2), W / 2 - 200, ytop, BGOLD, a)


def sc_systems(f, t):
    if not (b(94) - 0.1 < t < b(99) + 0.2): return
    a = env(t, b(94), b(99), 0.3, 0.3)
    # 左：红皇后型（闭环，原地打转）
    aL = a * (0.45 + 0.55 * (t < b(96, 2) + 0.2))
    f.text('红皇后型', 520, 205, 40, 'serif_black', CRIMSON, aL * eo((t - b(94)) / 0.4), mode='O', glow=0.4)
    loop_nodes(f, t, 520, 470, 270, 175, ['投入', '创新', '对手跟进', '优势归零'], [GREY, BGOLD, ORANGE, CRIMSON],
               b(94, 1), aL, 0.4, 26, 0.12)
    f.text('地位：不变', 520, 470, 26, 'sans_med', lerpc(CRIMSON, WHITE, .4), aL * eo((t - b(95, 1)) / 0.4), mode='O')
    # 右：复利型（螺旋向外，每圈留下资产）
    t1 = b(96, 2)
    aR = a * eo((t - t1) / 0.5)
    if aR <= 0: return
    cx, cy = 1400, 470
    f.text('复利型', cx, 205, 40, 'serif_black', BGOLD, aR, mode='O', glow=0.4)
    p = eio((t - t1) / (BAR * 2))
    th = np.linspace(0, 4.2 * math.pi * p + 0.01, 220)
    r = 18 + th * 14
    pts = np.stack([cx + r * np.cos(th - math.pi / 2), cy + r * 0.62 * np.sin(th - math.pi / 2)], 1)
    f.poly(pts, BGOLD, aR, 3)
    f.glow(tuple(pts[-1]), 10, WHITE, aR, 'E'); f.glow(tuple(pts[-1]), 30, BGOLD, aR * 0.6, 'B')
    labels = [('投入', (cx - 230, cy - 120)), ('品牌·网络·规模·数据', (cx + 175, cy + 40)),
              ('护城河加深', (cx - 120, cy + 150)), ('下一轮更容易', (cx + 40, cy - 215))]
    for i, (s_, (x, y)) in enumerate(labels):
        chip(f, s_, x, y, 24, [GREY, CYAN, BGOLD, BGOLD_L][i], aR * eo((t - t1 - i * BEAT) / 0.4), 'sans_black', 0.14)
    n_layers = int(cl((t - t1) / (BAR * 2.2)) * 6)   # 每圈留下一层资产
    for k in range(n_layers):
        yy = 690 - k * 14
        f.rrect_fill(cx - 140, yy - 10, cx + 140, yy, 3, BGOLD, aR * 0.5)
    if n_layers:
        f.text('留下的资产', cx + 220, 690 - n_layers * 7, 22, 'sans_med', BGOLD, aR, 'l', mode='O')
    f.line((W / 2 + 40, 230), (W / 2 + 40, 700), GREY, a * 0.3, 1)


PATHS = [('换生态位', b(99)), ('切换成本', b(101)), ('网络效应', b(103, 2)), ('品牌心智', b(105, 2))]
_NR2 = np.random.default_rng(31)
CROWD = (_NR2.normal(0, 1, (46, 2)), _NR2.uniform(0, 6.28, 46))
NET = _NR2.uniform(-1, 1, (60, 2)) * np.array([380, 190])


def sc_paths(f, t):
    if not (b(99) - 0.1 < t < b(108) + 0.2): return
    a = env(t, b(99), b(108), 0.3, 0.3)
    cur = max(i for i, (_, tt) in enumerate(PATHS) if t >= tt - 0.01)
    for i, (name, tt) in enumerate(PATHS):   # 顶部四步进度
        x = W / 2 + (i - 1.5) * 260
        on = i == cur
        col = BGOLD if on else (lerpc(BGOLD, GREY, .5) if i < cur else GREY)
        f.circle((x - 64, 180), 16, col, a, 2)
        f.text(str(i + 1), x - 64, 180, 18, 'orb', col, a, mode='O')
        f.text(name, x + 14, 180, 26, 'sans_black' if on else 'sans_med', col, a, mode='O')
        if i < 3: f.line((x + 78, 180), (x + 120, 180), GREY, a * 0.4, 1)
    t0 = PATHS[cur][1]
    t1 = PATHS[cur + 1][1] if cur < 3 else b(108)
    al = a * env(t, t0, t1, 0.3, 0.25)
    if al <= 0: return
    if cur == 0:   # 生态位：离开拥挤的同一维度
        cx, cy = 720, 470
        f.circle((cx, cy), 190, CRIMSON, al * 0.5, 2)
        f.text('同一维度：拼 SKU 数量', cx, cy - 225, 24, 'sans_med', CRIMSON, al, mode='O')
        P, ph = CROWD
        xs = cx + P[:, 0] * 70 + np.sin(t * 6 + ph) * 6; ys = cy + P[:, 1] * 60 + np.cos(t * 5 + ph) * 6
        for x_, y_ in zip(xs, ys):
            f.glow((x_, y_), 4, lerpc(CRIMSON, WHITE, .3), al * 0.9, 'E')
        u = eio((t - t0 - 0.4) / 1.4)
        gx, gy = lerp(cx, 1300, u), lerp(cy, 440, u) - math.sin(u * math.pi) * 90
        comet(f, gx, gy, 20, BGOLD, al)
        f.circle((1300, 440), 150, BGOLD, al * u * 0.6, 2)
        f.text('新生态位', 1300, 250, 28, 'sans_black', BGOLD, al * u, mode='O')
        for i, s_ in enumerate(('会员制', '精选商品', '低毛利')):
            chip(f, s_, 1300 + (i - 1) * 150, 640, 24, BGOLD, al * eo((t - t0 - 1.6 - i * BEAT) / 0.4), 'sans_black', 0.14)
    elif cur == 1:  # 切换成本：根系越扎越深
        cx, cy = 900, 470
        f.rrect_fill(cx - 120, cy - 60, cx + 120, cy + 60, 16, CYAN, al * 0.14)
        f.rrect(cx - 120, cy - 60, cx + 120, cy + 60, 16, CYAN, al, 3)
        f.text('企业软件', cx, cy, 34, 'sans_black', lerpc(CYAN, WHITE, .5), al, mode='O')
        g = eio((t - t0) / (BAR * 1.6))
        for i, (s_, (x, y)) in enumerate((('流程', (cx - 360, cy - 150)), ('数据', (cx - 400, cy + 40)), ('培训', (cx - 330, cy + 210)))):
            for k in range(3):
                q = bez((cx - 120, cy - 30 + k * 30), (cx - 220, cy - 30 + k * 30), (x + 150, y), (x + 60, y), np.linspace(0, g, 30))
                f.poly(q, TEAL, al * 0.55, 1 + int(2 * g))
            chip(f, s_, x, y, 28, TEAL, al * eo((t - t0 - i * BEAT) / 0.4), 'sans_black', 0.14)
        k = int(max(t - t0 - 1.0, 0) // (BAR * 0.75))
        u = ((t - t0 - 1.0) % (BAR * 0.75)) / (BAR * 0.75) if t > t0 + 1.0 else 0
        rx = 1500 - 330 * math.sin(u * math.pi)
        if t > t0 + 1.0:
            f.rrect(rx - 100, cy - 45, rx + 100, cy + 45, 14, RED, al, 2)
            f.text('功能 +10%', rx, cy, 28, 'sans_black', RED, al, mode='O')
            if u > 0.4 and u < 0.6:
                f.glow((cx + 120, cy), 60, CYAN, al * 0.6, 'B')
        f.text('客户：留下', cx, cy + 110, 24, 'sans_med', CYAN, al * eo((t - t0 - 2) / 0.5), mode='O')
    elif cur == 2:  # 网络效应：节点越多，连线越多
        cx, cy = 820, 460
        nn = 4 + int(56 * eio(cl((t - t0) / (BAR * 1.8))))
        Pn = NET[:nn] + np.array([cx, cy])
        for i in range(1, nn):
            d = np.hypot(*(Pn[:i] - Pn[i]).T)
            for j in np.argsort(d)[:2]:
                f.line(tuple(Pn[i]), tuple(Pn[j]), lerpc(CYAN, VIOLET, i / 60), al * 0.45, 1)
        for i in range(nn):
            f.glow(tuple(Pn[i]), 4, WHITE, al, 'E'); f.glow(tuple(Pn[i]), 12, CYAN, al * 0.4, 'B')
        val = (nn / 60) ** 2
        bx = 1450
        f.rrect(bx - 40, 250, bx + 40, 680, 10, GREY, al * 0.6, 2)
        f.rrect_fill(bx - 34, 674 - 418 * val, bx + 34, 674, 8, BGOLD, al * 0.7)
        f.text('产品价值', bx, 715, 24, 'sans_med', BGOLD, al, mode='O')
        f.text('用户数 ↑', cx, 230, 26, 'sans_med', CYAN, al, mode='O')
        f.text('示意', bx + 90, 250, 20, 'sans_light', GREY, al * 0.8, mode='O')
    else:            # 品牌与心智：参数竞赛绕开它
        cx, cy = W / 2, 470
        bag = [(cx - 150, cy - 60), (cx + 150, cy - 60), (cx + 185, cy + 150), (cx - 185, cy + 150)]
        f.fillpoly(bag, BGOLD, al * 0.1)
        f.poly(bag, BGOLD, al, 3, closed=True)
        f.arc((cx, cy - 60), 90, math.pi, 2 * math.pi, BGOLD, al, 3, 40)
        f.glow((cx, cy + 40), 170, BGOLD, al * 0.18 * (1 + 0.5 * beat_pulse(t)), 'B')
        f.text('心智位置', cx, cy + 50, 34, 'serif_black', BGOLD_L, al, mode='O', glow=0.4)
        for i, s_ in enumerate(('参数 +20%', '新款', '更多功能', '参数 +20%', '更低价')):
            ph = ((t - t0) * 0.35 + i / 5) % 1.0
            ang = i * 1.3 + 0.4
            r = 520 - 200 * math.sin(ph * math.pi)
            x, y = cx + r * math.cos(ang), cy + r * 0.55 * math.sin(ang)
            chip(f, s_, x, y, 22, RED, al * math.sin(ph * math.pi) * 0.9, 'sans_med', 0.08)


def sc_emphasis(f, t):
    if not (b(108) - 0.1 < t < b(111) + 0.1): return
    a = env(t, b(108), b(111) - 0.15, 0.35, 0.2)
    sp = 1 + 2.5 * eio((t - b(108)) / (BAR * 3))
    for i in range(5):   # 每个人都在加速，位置却没变
        cx = W / 2 + (i - 2) * 340
        col = [CYAN, CRIMSON, VIOLET, TEAL, ORANGE][i]
        ytop = treadmill(f, t * sp, cx, 760, 240, a * 0.9, lerpc(col, GREY, .5), 1.5)
        runner_on(f, t * sp, cx, ytop, col, a, 13)
        f.text('进步 ×%.1f' % sp, cx, 820, 20, 'sans_med', lerpc(col, WHITE, .3), a * 0.9, mode='O')
    f.text('位置：都没变', W / 2, 890, 26, 'sans_black', BGOLD, a * env(t, b(109, 2), b(111), 0.4, 0.2), mode='O')
    implode(f, t, b(110), b(111), W / 2, 600, [BGOLD, WHITE, CYAN, BGOLD_L, CRIMSON, AMBER], 0.5, R0=900)


def sc_treadmill(f, t):
    if not (b(111) - 0.1 < t < b(114) + 0.1): return
    a = env(t, b(111), b(114), 0.15, 0.35)
    burst(f, t, b(111), W / 2, 600, [BGOLD, BGOLD_L, WHITE, CYAN, AMBER, BGOLD], 0, 800, 1700, 1.5)
    floor(f, t, a * eo((t - b(111, 2)) / 0.8), max(t - b(111, 2), 0) * 4.5, BGOLD, C(90, 60, 20), tile=0.5, fill=0.1, hor=700)
    ytop = treadmill(f, t, 620, 760, 520, a, lerpc(CRIMSON, GREY, .3), 2.2)
    for i, col in enumerate((CRIMSON, GREY)):   # 还在跑步机上的人
        runner_on(f, t, 480 + i * 150, ytop, col, a * 0.8, 14)
    jump_runner(f, t, b(111, 2), 800, ytop, BGOLD, a, dist=700, s=20)


LIMITS = [(b(114, 2), '市场还在快速扩张时，大家可能一起变好'),
          (b(115, 2), '变化也来自技术、需求和制度，不只来自对手')]


def sc_limits(f, t):
    if not (b(114) - 0.2 < t < b(117) + 0.2): return
    a = env(t, b(114), b(117), 0.4, 0.35)
    floor(f, t, a * 0.6, t * 0.6, INDIGO, C(30, 30, 90), tile=0.5, fill=0.08)
    x0, y0 = 450, 420
    f.rrect(x0 - 70, y0 - 70, W - x0 + 70, y0 + 170, 20, lerpc(INDIGO, WHITE, .2), a * 0.5 * eo((t - b(114)) / 0.8), 1)
    for i, (tt, s_) in enumerate(LIMITS):
        p = eo((t - tt) / 0.4)
        if p <= 0: continue
        y = y0 + i * 100
        cur = tt <= t
        col = BGOLD if i == len([1 for q, _ in LIMITS if t >= q]) - 1 else lerpc(INDIGO, WHITE, .5)
        f.circle((x0, y), 24, col, a * p, 2)
        f.text(str(i + 1), x0, y, 26, 'orb', col, a * p, mode='O')
        rich_line(f, s_, x0 + 50, y, 40, 'sans_med', TXT, a=a, t0=tt, stag=0.02, anchor='l')


def sc_final(f, t):
    if not (b(117) - 0.2 < t < b(119) + 0.3): return
    a = env(t, b(117), b(119), 0.4, 0.3)
    floor(f, t, a, t * 3.5, lerpc(BGOLD, AMBER, .4), C(80, 50, 20), tile=0.5, fill=0.1)
    ytop = treadmill(f, t, 620, 880, 300, a * 0.8, lerpc(CRIMSON, GREY, .3), 2.0)
    runner_on(f, t, 620, ytop, CRIMSON, a, 14)
    f.text('原地奔跑', 620, 935, 24, 'sans_med', CRIMSON, a, mode='O')
    u = eio((t - b(117, 2)) / (BAR * 1.4))
    x2 = 1180 + 420 * u
    comet(f, x2, 850, 20, BGOLD, a)
    for k in range(20):
        f.glow((x2 - k * 14 * (0.3 + u), 850), 6, BGOLD, a * (1 - k / 20) * 0.6, 'E')
    f.text('离开跑步机', x2, 935, 24, 'sans_med', BGOLD, a, mode='O')


# ================================================================ 片尾：粒子汇聚成官方 logo
END_LOGO_PX = 220                    # BRAND.md：片尾 logo 约 220px
END_LOGO = load_logo(END_LOGO_PX)    # (rgb, alpha) —— brand/logo_baman.png 原图
LOGO_C = (W / 2, 400)
_er = np.random.default_rng(99)
_la = END_LOGO[1]
_ys, _xs = np.nonzero(_la > 0.25)
_pick = _er.choice(len(_ys), 5200, p=_la[_ys, _xs] / _la[_ys, _xs].sum())
LP_TX = _xs[_pick] + LOGO_C[0] - END_LOGO_PX / 2 + _er.uniform(-0.5, 0.5, 5200)
LP_TY = _ys[_pick] + LOGO_C[1] - END_LOGO_PX / 2 + _er.uniform(-0.5, 0.5, 5200)
LP_COL = np.clip(END_LOGO[0][_ys[_pick], _xs[_pick]] * 1.15, 0, 1).astype(np.float32)
_ang = _er.uniform(0, 2 * math.pi, 5200); _rad = _er.uniform(500, 1300, 5200)
LP_SX = LOGO_C[0] + _rad * np.cos(_ang); LP_SY = LOGO_C[1] + _rad * np.sin(_ang) * 0.7
LP_DL = _er.uniform(0, 0.35, 5200)
LP_MIX = np.array([lerpc(BGOLD, CYAN, u) for u in _er.uniform(0, 1, 5200)], np.float32)
T_GATHER0, T_GATHER1 = b(119), b(120, 2)   # 汇聚
T_LOGO = b(120, 2)                    # 清晰 logo 浮现
T_WORD = b(121)                       # 重拍：金色「巴芒价值」+「BUFFETT · MUNGER」
T_SHIMMER = T_WORD + 0.35
T_FADE0 = b(122, 2)                   # 整片最终淡出


def _brand_word(title_px=120):
    """按 brand.build() 的方式渲染片尾大字：Noto Serif SC Black + 金色竖向渐变；小字两端对齐到与主标题等宽"""
    k = title_px / BSPEC['title_px']
    f1 = brand._font(BSPEC['title_font'], int(title_px))
    im = Image.new('L', (int(f1.getlength(BSPEC['title']) + 40 * k), int(title_px * 1.6)), 0)
    ImageDraw.Draw(im).text((10 * k, int(title_px * 1.25)), BSPEC['title'], font=f1, fill=255, anchor='ls')
    t1 = brand._ink(im)
    f2 = brand._font(BSPEC['sub_font'], int(BSPEC['sub_px'] * k))
    sub = BSPEC['sub']
    nat = sum(f2.getlength(c) for c in sub)
    tr = (t1.shape[1] - nat) / (len(sub) - 1)
    w2 = int(nat + tr * len(sub) + 20 * k)
    im = Image.new('L', (w2, int(BSPEC['sub_px'] * k * 2)), 0)
    d = ImageDraw.Draw(im); x = 5 * k
    for c in sub:
        d.text((x, int(BSPEC['sub_px'] * k * 1.4)), c, font=f2, fill=255, anchor='ls'); x += f2.getlength(c) + tr
    t2 = brand._ink(im)[:, :t1.shape[1]]
    rgb1 = np.broadcast_to(brand._ramp(t1.shape[0], GOLD_STOPS)[:, None, :], t1.shape + (3,)).astype(np.float32)
    rgb2 = np.broadcast_to(np.array(SUB_GOLD, np.float32) / 255, t2.shape + (3,)).astype(np.float32)
    return (rgb1, t1.astype(np.float32)), (rgb2, t2.astype(np.float32)), int(BSPEC['sub_gap_px'] * k)


WORD, SUBW, SUBGAP = _brand_word(120)


def post_over(img, rgb, alpha, cx, cy, a):
    """在 tone-map 之后按原色合成（保证 logo / 品牌字的颜色就是原始颜色）"""
    if a <= 0.003: return
    h, w = alpha.shape
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    reg = img[y0:y0 + h, x0:x0 + w].astype(np.float32) / 255
    m = (alpha * a)[..., None]
    reg = reg * (1 - m) + np.clip(rgb, 0, 1.3) * m
    img[y0:y0 + h, x0:x0 + w] = (np.clip(reg, 0, 1) * 255 + 0.5).astype(np.uint8)


def shimmer_rgb(rgb, alpha, u, scale):
    """与 brand.Hud 相同的流光：斜向高光带扫过文字"""
    if u is None or not (0 <= u <= 1): return rgb
    h, w = alpha.shape
    xs = np.arange(w)[None, :] + np.arange(h)[:, None] * 0.6
    span = w + 80 * scale
    pos = -40 * scale + (0.5 - 0.5 * math.cos(u * math.pi)) * span
    band = np.exp(-((xs - pos) / (16 * scale)) ** 2)[..., None]
    return np.clip(rgb + band * 0.6, 0, 1.25)


def sc_end(f, t):
    if t < T_GATHER0 - 0.1: return
    # 汇聚粒子
    p = np.clip((t - T_GATHER0 - LP_DL * (T_GATHER1 - T_GATHER0)) / ((T_GATHER1 - T_GATHER0) * 0.75), 0, 1)
    e = eio(p) if np.isscalar(p) else p * p * (3 - 2 * p)
    swirl = (1 - e) * 2.4
    dx = LP_SX - LOGO_C[0]; dy = LP_SY - LOGO_C[1]
    rx = dx * np.cos(swirl) - dy * np.sin(swirl); ry = dx * np.sin(swirl) + dy * np.cos(swirl)
    x = LOGO_C[0] + rx * (1 - e) + (LP_TX - LOGO_C[0]) * e
    y = LOGO_C[1] + ry * (1 - e) + (LP_TY - LOGO_C[1]) * e
    col = LP_MIX * (1 - e[:, None]) + LP_COL * e[:, None]
    fade = 1 - cl((t - T_LOGO) / 0.8)
    al = np.minimum((t - T_GATHER0) / 0.5, 1) * fade * (0.75 + 0.25 * e)
    if fade > 0 and t >= T_GATHER0:
        f.dots(x, y, col, al * 1.3, 1, 'E')
    # 汇聚前：上一幕的金色流光被吸进来
    flow(f, t, 0.35 * env(t, T_GATHER0 - 0.2, T_GATHER0 + 1.2, 0.3, 0.8), [BGOLD, CYAN, BGOLD_L, BLUE, WHITE, BGOLD], 120, 1200)
    # logo 后面的淡蓝光晕（BRAND.md：很淡的蓝色光晕）
    ga = cl((t - T_GATHER0) / 3.0) * (1 - cl((t - T_FADE0) / 3))
    ga *= cl((t - T_GATHER1 + 1.2) / 1.2)
    f.glow(LOGO_C, 120, LOGO_GLOW, 0.2 * ga * (1 + 0.6 * math.exp(-max(0, t - T_LOGO) / 0.5)), 'B')
    if t >= T_WORD:
        burst(f, t, T_WORD, LOGO_C[0], 640, [LOGO_GLOW, CYAN, BGOLD, BGOLD_L, WHITE, BLUE], 7, 600, 1300, 1.5)
        f.glow((W / 2, 640), 300, BGOLD, 0.25 * math.exp(-(t - T_WORD) / 0.6), 'B')


def end_post(img, t):
    """片尾的原始 logo 与品牌字（tone-map 后合成）"""
    if t < T_LOGO - 0.4: return
    la = eo((t - T_LOGO + 0.3) / 1.0)
    sc = 1.0
    post_over(img, END_LOGO[0], END_LOGO[1], LOGO_C[0], LOGO_C[1], la)
    if t >= T_WORD - 0.05:
        wa = eo((t - T_WORD) / 0.35)
        (r1, a1), (r2, a2) = WORD, SUBW
        u = (t - T_SHIMMER) / BSPEC['shimmer_dur']
        rr1 = shimmer_rgb(r1, a1, u, 120 / BSPEC['title_px'])
        ty = 640
        post_over(img, rr1, a1, W / 2, ty, wa)
        sa = eo((t - T_WORD - 0.15) / 0.45)
        post_over(img, r2, a2, W / 2, ty + a1.shape[0] / 2 + SUBGAP + a2.shape[0] / 2, sa)


# ================================================================ 渲染
SCENES = [sc_hook, sc_title, sc_promise, sc_card1, sc_alice, sc_quote1, sc_vanvalen, sc_ring, sc_card2, sc_host,
          sc_firstp, sc_compare, sc_graph, sc_formula, sc_textile, sc_crowd, sc_y1985, sc_mloom, sc_sankey, sc_tech, sc_q2,
          sc_three, sc_cycle, sc_ai, sc_moats, sc_flywheel, sc_escape, sc_systems, sc_paths, sc_emphasis, sc_treadmill,
          sc_limits, sc_final, sc_end]


def draw_hud_post(img, t, a=1.0):
    h = HUD.y0 + HUD.h + HUD.P + 2
    reg = img[:h].astype(np.float32) / 255
    HUD.draw(reg, t, a)
    img[:h] = (np.clip(reg, 0, 1) * 255 + 0.5).astype(np.uint8)


def render(i):
    t = i / FPS
    f = Frame(t)
    bg = bg_at(t)
    draw_stars(f, t, 1.0 - 0.5 * cl((t - T_GATHER0) / 2))
    for s in SCENES:
        s(f, t)
    draw_caps(f, t)
    shockwaves(f, t)
    draw_chrome(f, t)
    img = finish(f, bg, bloom_k=1.0 + 0.3 * beat_pulse(t) * energy(t), vignette=VIGNETTE)
    z = zoom_punch(t)
    if z > 0.002:
        M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, 1 + z)
        img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    end_post(img, t)
    fin = cl(t / 0.5)
    if fin < 1:
        img = (img.astype(np.float32) * fin).astype(np.uint8)
    draw_hud_post(img, t)     # 右上角官方角标：全程保持
    fade = 1 - eio((t - T_FADE0) / (DUR - T_FADE0))
    if fade < 1:              # 整片最终淡出（含角标）
        img = (img.astype(np.float32) * max(fade, 0)).astype(np.uint8)
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
        a, z, path = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
                              '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                              '-pix_fmt', 'yuv420p', '-tune', 'animation', path], stdin=subprocess.PIPE)
        for i in range(a, min(z, NFR)):
            p.stdin.write(render(i).tobytes())
            if (i - a) % 150 == 0: print(path, i, flush=True)
        p.stdin.close(); p.wait()
