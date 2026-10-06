"""M02《一家很强的公司，为什么也会失去时代？》—— 自然选择 · 4 分半动态视觉短片

纯字幕叙事（无人声）。所有画面切换、字幕出入都落在 90 BPM 的拍点上（1 拍 = 20 帧）。
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
ENERGY = [(0, .3), (b(4) - .05, .3), (b(4), .9), (b(7), .6), (b(9), .4), (b(25), .5), (b(39), .85), (b(41), 1),
          (b(57) - .1, 1), (b(57), .3), (b(65), .4), (b(69) - .1, .7), (b(69), 1), (b(85) - .1, 1), (b(85), .5),
          (b(93), .35), (b(95), .8), (DUR, .2)]


def energy(t):
    return keys(t, ENERGY)


def beat_pulse(t, decay=0.13):
    return math.exp(-(t % BEAT) / decay)


def bar_pulse(t, decay=0.25):
    return math.exp(-(t % BAR) / decay)


# ================================================================ 背景：星云 + 星空
BGK = [
    (0, (20, 40, 60), (10, 20, 40), .7), (b(4) - .05, (20, 40, 60), (10, 20, 40), .6),
    (b(4), (30, 150, 110), (150, 110, 30), 1.35), (b(5), (20, 100, 80), (80, 70, 30), 1.0),
    (b(7), (15, 60, 60), (30, 40, 60), .85), (b(9) - .05, (15, 60, 60), (30, 40, 60), .85),
    (b(9), (20, 90, 90), (20, 40, 90), 1.1), (b(12, 2), (40, 60, 50), (30, 40, 50), .7),
    (b(19), (90, 30, 30), (40, 20, 40), .9), (b(23), (30, 80, 70), (30, 30, 70), .9),
    (b(25) - .05, (30, 80, 70), (30, 30, 70), .9), (b(25), (160, 100, 30), (60, 30, 90), 1.15),
    (b(32), (30, 60, 120), (80, 40, 110), 1.0), (b(37), (110, 40, 60), (30, 70, 130), 1.05),
    (b(41) - .05, (30, 25, 50), (30, 20, 40), .6), (b(41), (190, 130, 40), (40, 120, 140), 1.45),
    (b(45), (110, 80, 30), (40, 60, 90), 1.0), (b(50), (30, 90, 140), (90, 40, 90), 1.05),
    (b(57) - .05, (30, 90, 140), (90, 40, 90), 1.0), (b(57), (15, 30, 80), (20, 15, 55), .75),
    (b(67), (20, 20, 50), (30, 15, 40), .55), (b(69) - .05, (20, 20, 50), (30, 15, 40), .5),
    (b(69), (40, 150, 130), (170, 120, 40), 1.45), (b(72), (30, 100, 100), (110, 80, 30), 1.05),
    (b(78), (150, 100, 30), (40, 80, 110), 1.1), (b(80, 2), (40, 60, 110), (60, 40, 90), .95),
    (b(85), (30, 90, 70), (110, 80, 25), 1.0), (b(93), (20, 40, 100), (30, 20, 60), .7),
    (b(95) - .05, (20, 40, 100), (30, 20, 60), .6), (b(95), (40, 85, 170), (120, 85, 30), 1.15),
    (b(97), (25, 45, 100), (60, 45, 20), .8), (DUR, (10, 15, 30), (10, 10, 20), .4)]

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
RISERS = [(b(3), b(4)), (b(39), b(41)), (b(67), b(69)), (b(93), b(95))]


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
CHAPTERS = [(0, '序', '序章', 'PROLOGUE'), (b(9), '01', '被选中的不是最强者', 'WHO GETS SELECTED'),
            (b(25), '02', '强，是一个过去时', 'STRENGTH IS PAST TENSE'), (b(41), '03', '失去的是条件', 'CONDITIONS, NOT ABILITIES'),
            (b(57), '04', '公司不是物种', 'A COMPANY IS NOT A SPECIES'), (b(69), '05', '先在内部选择自己', 'SELECT YOURSELF FIRST'),
            (b(85), '终', '一个问题', 'ONE QUESTION'), (b(93), '终', '片尾', 'END'), (DUR, '', '', '')]
CHROME_END = b(93)


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


# ================================================================ 共用图形：拼图（能力 / 环境匹配）
_PX = np.linspace(0, 1, 160)


def contour_piece(x):
    """能力（拼图块）顶部的轮廓：0..1 → 像素偏移"""
    return 38 * np.sin(x * 2 * math.pi * 2.0) + 22 * np.sin(x * 2 * math.pi * 5.0 + 1.0)


def contour_env2(x):
    return 34 * np.sin(x * 2 * math.pi * 1.0 + 2.2) + 30 * np.sin(x * 2 * math.pi * 3.5 + 0.3)


def fit_puzzle(f, t, cx, cy, w, morph, a, strength=1.0, label=True):
    """morph: 0=环境与能力完美契合，1=环境已变；返回匹配度 0..1"""
    if a <= 0.003: return 1.0
    x0 = cx - w / 2
    xs = x0 + _PX * w
    P = cy + contour_piece(_PX)
    E = cy + (1 - morph) * contour_piece(_PX) + morph * contour_env2(_PX) - 4 * morph
    hp = 160 * (0.75 + 0.25 * strength)
    # 环境（上方的世界）
    top = cy - 190
    env_poly = np.concatenate([np.stack([xs, E], 1), [[xs[-1], top], [xs[0], top]]])
    f.fillpoly(env_poly, CYAN, a * 0.10, 'L')
    f.poly(np.stack([xs, E - 2], 1), lerpc(CYAN, WHITE, .3), a, 2)
    f.text('环境', cx, top + 40, 26, 'sans_med', CYAN, a * 0.9, mode='O')
    # 能力（下方的拼图块）
    piece_poly = np.concatenate([np.stack([xs, P + 2], 1), [[xs[-1], P[-1] + hp], [xs[0], P[0] + hp]]])
    f.fillpoly(piece_poly, BGOLD, a * (0.10 + 0.06 * strength), 'L')
    f.poly(piece_poly, BGOLD, a, 2 + int(strength > 1.2), closed=True)
    f.text('能力', cx, cy + hp * 0.6, 30, 'sans_black', BGOLD_L, a, mode='O')
    gap = np.abs(E - P)
    for k in range(0, 160, 3):   # 不匹配的地方发红光
        if gap[k] > 3:
            f.line((xs[k], E[k]), (xs[k], P[k]), CRIMSON, a * min(gap[k] / 40, 1), 2)
    match = float(np.clip(1 - gap.mean() / 40, 0, 1))
    if morph < 0.05:
        f.glow((cx, cy), w * 0.35, BGOLD, a * 0.12 * (1 + beat_pulse(t)), 'B')
    return match


def meter(f, x, y0, y1, v, col, a, label):
    f.rrect(x - 26, y0, x + 26, y1, 10, GREY, a * 0.6, 2)
    h = (y1 - y0 - 12) * cl(v)
    f.rrect_fill(x - 20, y1 - 6 - h, x + 20, y1 - 6, 8, col, a * 0.75)
    f.glow((x, y1 - 6 - h), 26, col, a * 0.5, 'B')
    f.text(label, x, y1 + 32, 24, 'sans_med', col, a, mode='O')


# ================================================================ 共用图形：生命之树
_TR = np.random.default_rng(1859)
TREE = []   # (x0, y0, x1, y1, depth, birth, extinct_tip)


def _grow(x, y, ang, ln, d, t0):
    x1, y1 = x + ln * math.cos(ang), y + ln * math.sin(ang)
    tip = d >= 7 or (d >= 3 and _TR.random() < 0.22)
    TREE.append((x, y, x1, y1, d, t0, tip and d < 7))
    if tip: return
    n = 2 if _TR.random() < 0.85 else 3
    for k in range(n):
        da = (k - (n - 1) / 2) * _TR.uniform(0.32, 0.55) + _TR.normal(0, 0.08)
        _grow(x1, y1, ang + da, ln * _TR.uniform(0.70, 0.82), d + 1, t0 + _TR.uniform(0.08, 0.14))


_grow(0.0, 0.0, -math.pi / 2, 1.0, 0, 0.0)
TREE = np.array(TREE)
TREE_T1 = TREE[:, 5].max() + 0.12


def tree_pts(cx, by, scale):
    x0 = cx + TREE[:, 0] * scale; y0 = by + TREE[:, 1] * scale
    x1 = cx + TREE[:, 2] * scale; y1 = by + TREE[:, 3] * scale
    return x0, y0, x1, y1


def life_tree(f, t, cx, by, scale, grow, a, hue=0.0):
    """grow: 0..1 生长进度；灭绝的枝在末端变灰"""
    if a <= 0.003: return
    x0, y0, x1, y1 = tree_pts(cx, by, scale)
    g = grow * TREE_T1
    for i in range(len(TREE)):
        p = cl((g - TREE[i, 5]) / 0.12)
        if p <= 0: continue
        d = TREE[i, 4]
        col = lerpc(lerpc(TEAL, CYAN, hue), BGOLD, d / 7)
        xe, ye = x0[i] + (x1[i] - x0[i]) * p, y0[i] + (y1[i] - y0[i]) * p
        f.line((x0[i], y0[i]), (xe, ye), col, a * (0.9 - d * 0.06), max(1, 4 - int(d // 2)))
        if p >= 1 and TREE[i, 6]:
            f.glow((xe, ye), 4, GREY, a * 0.8, 'E')
        elif p >= 1 and d >= 7:
            f.glow((xe, ye), 3, lerpc(BGOLD_L, CYAN, hue), a, 'E')
            f.glow((xe, ye), 9, BGOLD, a * 0.25, 'B')


# ================================================================ 场景
def sc_hook(f, t):
    if t > b(4) + 0.3: return
    a = env(t, 0, b(4), 0.3, 0.25)
    morph = eio((t - b(2)) / 1.2)
    m = fit_puzzle(f, t, W / 2, 660, 760, morph, a)
    al = a * env(t, 0.6, b(4), 0.4, 0.25)
    f.text('匹配度 %d%%' % round(m * 100), W / 2 + 470, 660, 28, 'sans_black', lerpc(CRIMSON, BGOLD, m), al, mode='O')
    implode(f, t, b(3), b(4), W / 2, 640, [BGOLD, CYAN, TEAL, WHITE, BGOLD_L, CRIMSON], 0.8)


def sc_title(f, t):
    if not (b(4) - 0.1 < t < b(7) + 0.5): return
    a = env(t, b(4), b(7) - 0.05, 0.25, 0.4)
    burst(f, t, b(4), W / 2, 520, [TEAL, BGOLD, BGOLD_L, CYAN, WHITE, GREEN], 0, 800, 1700, 1.5)
    life_tree(f, t, W / 2, 1040, 300, eo((t - b(4)) / (BAR * 2.2)), a * 0.55)
    t0 = b(4)
    rich_line(f, '自然选择 · NATURAL SELECTION', W / 2, 285, 30, 'sans_med', BGOLD, a=a, t0=t0 + 0.1, stag=0.02, track=0.12, underline=False)
    rich_line(f, '一家很强的公司，', W / 2, 420, 96, 'serif_black', TXT, a=a, t0=t0 + 0.2, stag=0.05)
    rich_line(f, '为什么也会{失去时代}？', W / 2, 545, 96, 'serif_black', TXT, a=a, t0=t0 + 0.6, stag=0.05, glow_hl=0.6)
    rich_line(f, '《50个自然法则，看懂商业世界》  M02', W / 2, 675, 34, 'sans_med', lerpc(BSUB, WHITE, .3), a=a, t0=t0 + 1.2, stag=0.015, underline=False)
    rich_line(f, '50 个来自自然、数学与复杂系统的思维模型 · 第 02 个', W / 2, 728, 24, 'sans_light', lerpc(GREY, WHITE, .3), a=a, t0=t0 + 1.5, stag=0.01, underline=False)


def dep_table(f, t, x0, y0, cols, rows, a, t0, cw=None, rh=64, fills=None, qcol=None):
    """能力依赖清单的表格：cols 表头，rows 行标签；fills(i, j) → 0..1 的格子点亮度"""
    if a <= 0.003: return
    cw = cw or [220] * len(cols)
    xs = np.concatenate([[x0], x0 + np.cumsum(cw)])
    ytot = rh * (len(rows) + 1)
    f.rrect(xs[0] - 10, y0 - 10, xs[-1] + 10, y0 + ytot + 10, 14, lerpc(BGOLD, GREY, .4), a * 0.7, 2)
    for j, c in enumerate(cols):
        p = eo((t - t0 - j * 0.12) / 0.4) * a
        f.text(c, (xs[j] + xs[j + 1]) / 2, y0 + rh / 2, 26, 'sans_black', BGOLD, p, mode='O')
        if j: f.line((xs[j], y0), (xs[j], y0 + ytot), GREY, a * 0.35, 1)
    for i, r in enumerate(rows):
        yy = y0 + rh * (i + 1)
        f.line((xs[0], yy), (xs[-1], yy), GREY, a * 0.35, 1)
        p = eo((t - t0 - 0.4 - i * 0.15) / 0.4) * a
        f.text(r, (xs[0] + xs[1]) / 2, yy + rh / 2, 26, 'sans_med', TXT, p, mode='O')
        for j in range(1, len(cols)):
            v = fills(i, j) if fills else 0.0
            cxx, cyy = (xs[j] + xs[j + 1]) / 2, yy + rh / 2
            if qcol is not None and j == len(cols) - 1 and v > 0:
                f.text('?', cxx, cyy, 34, 'serif_black', qcol, p * v, mode='O', glow=0.5)
            elif v > 0:
                f.rrect_fill(cxx - cw[j] * 0.32, cyy - 9, cxx - cw[j] * 0.32 + cw[j] * 0.64 * v, cyy + 9, 6, TEAL, p * 0.6)


def sc_promise(f, t):
    if not (b(7) - 0.1 < t < b(9)): return
    a = env(t, b(7), b(9), 0.4, 0.3)
    dep_table(f, t, 560, 680, ['能力', '需求', '技术', '制度'], ['①', '②'], a * 0.8, b(7, 2), cw=[200, 200, 200, 200], rh=56,
              fills=lambda i, j: cl((t - b(8) - (i * 3 + j) * 0.12) / 0.4))


def sc_card1(f, t):
    if not (b(9) - 0.1 < t < b(10) + 0.1): return
    mirror_card(f, t, b(9), b(10), '01', '被选中的不是最强者', 'WHO GETS SELECTED', TEAL)


def sc_darwin(f, t):
    if not (b(10) - 0.1 < t < b(12, 2) + 0.2): return
    a = env(t, b(10), b(12, 2), 0.35, 0.3)
    life_tree(f, t, W / 2, 1000, 260, 0.35 + 0.65 * eo((t - b(10)) / (BAR * 2.5)), a * 0.3)
    u = eio((t - b(10) - 0.3) / (BAR * 1.35))
    for side, name, en, col in ((-1, '达尔文', 'Darwin', CYAN), (1, '华莱士', 'Wallace', BGOLD)):
        x = W / 2 + side * 620 * (1 - u)
        y = 470 - math.sin(u * math.pi) * 120
        for k in range(16):
            uu = cl(u - k * 0.02)
            f.glow((W / 2 + side * 620 * (1 - uu), 470 - math.sin(uu * math.pi) * 120), 6, col, a * (1 - k / 16) * 0.6, 'E')
        comet(f, x, y, 22, col, a * (1 - cl((t - b(11, 2)) / 0.3)))
        f.text(name, x, y - 64, 30, 'sans_black', col, a * (1 - u * 0.9), mode='O')
        f.text(en, x, y - 30, 20, 'corm', GREY, a * (1 - u * 0.9), mode='O')
    rich_line(f, '1858', W / 2, 250, 120, 'orb', BGOLD, a=a * env(t, b(10), b(11, 2), 0.3, 0.3), t0=b(10), stag=0.06, underline=False, mode='E')
    burst(f, t, b(11, 2), W / 2, 520, [CYAN, BGOLD, WHITE, TEAL, BGOLD_L, GREEN], 3, 700, 1400, 1.4)


# ---- 选择模拟（简化模拟，非实测数据）
SIM_X0, SIM_Y0, SIM_X1, SIM_Y1 = 200, 200, 1120, 720
_SR = np.random.default_rng(7)
NI = 140
_gx, _gy = np.meshgrid(np.arange(14), np.arange(10))
IN_X = SIM_X0 + 40 + _gx.ravel() * 60 + _SR.uniform(-16, 16, NI)
IN_Y = SIM_Y0 + 50 + _gy.ravel() * 46 + _SR.uniform(-12, 12, NI)
IN_RANK = _SR.permutation(NI)
IN_PH = _SR.uniform(0, 6.28, NI)
BARK = cv2.resize(fbm(230, 130, 99, 6, 4), (SIM_X1 - SIM_X0, SIM_Y1 - SIM_Y0), interpolation=cv2.INTER_CUBIC)
SIM_G0 = b(17)
N_GEN = int(round((b(25) - SIM_G0) / BEAT))


def bark_dark(t):
    return eio((t - b(19, 1)) / (BAR * 1.5))


GEN_P = [0.5]
for _g in range(N_GEN + 2):
    _bd = bark_dark(SIM_G0 + _g * BEAT)
    wd, wl = 1 - 0.25 * (1 - _bd), 1 - 0.25 * _bd
    _p = GEN_P[-1]
    GEN_P.append(_p * wd / (_p * wd + (1 - _p) * wl))


def gen_at(t):
    return int(max(t - SIM_G0, 0) // BEAT) if t >= SIM_G0 else -1


def p_dark(t):
    g = gen_at(t)
    return GEN_P[min(g + 1, len(GEN_P) - 1)] if g >= 0 else 0.5


LIGHT_INSECT = C(214, 190, 150); DARK_INSECT = C(40, 36, 44)
LIGHT_BARK = np.array(C(196, 172, 128), np.float32); DARK_BARK = np.array(C(46, 40, 44), np.float32)


def insect_poly(x, y, s, ang):
    ts = np.linspace(0, 2 * math.pi, 14, endpoint=False)
    ex, ey = 9 * s * np.cos(ts), 14 * s * np.sin(ts)
    ca, sa = math.cos(ang), math.sin(ang)
    return np.stack([x + ex * ca - ey * sa, y + ex * sa + ey * ca], 1)


def sc_sim(f, t):
    if not (b(12, 2) - 0.2 < t < b(25) + 0.2): return
    a = env(t, b(12, 2), b(25), 0.5, 0.35)
    bd = bark_dark(t)
    # 树皮（环境）
    col = LIGHT_BARK * (1 - bd) + DARK_BARK * bd
    patch = (0.55 + 0.6 * BARK)[..., None] * col * a * 0.95
    f.L[SIM_Y0:SIM_Y1, SIM_X0:SIM_X1] += patch.astype(np.float32)
    f.rrect(SIM_X0 - 6, SIM_Y0 - 6, SIM_X1 + 6, SIM_Y1 + 6, 10, lerpc(BGOLD, GREY, .5), a * 0.8, 2)
    f.text('简化模拟 · 非实测数据', (SIM_X0 + SIM_X1) / 2, SIM_Y0 - 30, 22, 'sans_light', GREY, a, mode='O')
    f.text('树皮：%s' % ('浅色' if bd < 0.5 else '深色'), SIM_X0 + 90, SIM_Y1 + 32, 22, 'sans_med', lerpc(BGOLD_L, GREY, bd), a, mode='O')
    # 昆虫
    pd = p_dark(t)
    nd = int(round(pd * NI))
    g = gen_at(t)
    dark_polys, light_polys, ring = [], [], []
    for i in range(NI):
        is_dark = IN_RANK[i] < nd
        wob = math.sin(t * 2 + IN_PH[i]) * 3
        pts = insect_poly(IN_X[i] + wob, IN_Y[i], 1.0, IN_PH[i] + math.sin(t + IN_PH[i]) * 0.2)
        (dark_polys if is_dark else light_polys).append(pts)
    f.darkpolys(dark_polys + light_polys, a)
    f.top_fills(dark_polys, DARK_INSECT, a)
    f.top_fills(light_polys, LIGHT_INSECT, a)
    # 捕食：每一代，鸟挑走最显眼的几只
    if t >= b(15, 2):
        step = BEAT if t >= SIM_G0 else BEAT * 2
        k = int((t - b(15, 2)) // step)
        u = ((t - b(15, 2)) % step) / step
        rng = np.random.default_rng(k + 11)
        vis_dark = bd < 0.5
        cand = [i for i in range(NI) if (IN_RANK[i] < nd) == vis_dark]
        if cand:
            for i in rng.choice(cand, min(3, len(cand)), replace=False):
                x, y = IN_X[i], IN_Y[i]
                al = a * math.sin(cl(u) * math.pi)
                f.circle((x, y), 18 + 22 * u, CRIMSON, al, 2)
                f.poly([(x - 26, y - 34 - 30 * (1 - u)), (x, y - 14), (x + 26, y - 34 - 30 * (1 - u))], WHITE, al * 0.9, 2)
    # 阶段标注
    if b(12, 2) <= t < b(14):
        al = a * env(t, b(12, 2) + 0.3, b(14), 0.3, 0.3)
        f.text('浅色', SIM_X1 + 70, 300, 26, 'sans_black', LIGHT_INSECT, al, mode='O')
        f.text('深色', SIM_X1 + 70, 350, 26, 'sans_black', lerpc(DARK_INSECT, WHITE, .5), al, mode='O')
    if b(14) <= t < b(15, 2):   # 遗传：亲代 → 子代
        al = a * env(t, b(14), b(15, 2), 0.3, 0.3)
        px, py = SIM_X1 + 200, 330
        for (xx, cc) in ((0, LIGHT_INSECT), (110, DARK_INSECT)):
            f.darkpolys([insect_poly(px + xx, py, 1.4, 0)], al)
            f.top_fills([insect_poly(px + xx, py, 1.4, 0)], cc, al)
            for dx in (-22, 22):
                arrow(f, (px + xx, py + 26), (px + xx + dx, py + 74), GREY, al, 2, 8)
                f.darkpolys([insect_poly(px + xx + dx, py + 100, 1.0, 0)], al)
                f.top_fills([insect_poly(px + xx + dx, py + 100, 1.0, 0)], cc, al)
        f.text('像父母', px + 55, py + 150, 24, 'sans_med', TXT, al, mode='O')
    # 代际比例图
    if t >= SIM_G0 - 0.2:
        cx0, cy0, cy1 = 1250, 260, 700
        bw = 13
        al = a * eo((t - SIM_G0 + 0.2) / 0.5)
        f.text('深色比例', cx0 + 200, cy0 - 40, 24, 'sans_med', TXT, al, mode='O')
        f.line((cx0 - 6, cy1), (cx0 + bw * N_GEN + 6, cy1), GREY, al * 0.7, 1)
        for gg in range(min(g + 1, N_GEN)):
            pp = GEN_P[gg + 1]
            x = cx0 + gg * bw
            hd = (cy1 - cy0) * pp
            f.fillpoly([(x, cy1 - hd), (x + bw - 3, cy1 - hd), (x + bw - 3, cy1), (x, cy1)], lerpc(DARK_INSECT, VIOLET, .45), al * 0.9, 'E')
            f.fillpoly([(x, cy0), (x + bw - 3, cy0), (x + bw - 3, cy1 - hd), (x, cy1 - hd)], LIGHT_INSECT, al * 0.35, 'L')
        f.text('第 %d 代' % max(g + 1, 1), cx0 + 200, cy1 + 36, 26, 'sans_black', BGOLD, al, mode='O')
    if b(19) <= t < b(21):
        al = env(t, b(19), b(21), 0.2, 0.4)
        f.text('环境改变', (SIM_X0 + SIM_X1) / 2, (SIM_Y0 + SIM_Y1) / 2, 64, 'serif_black', CRIMSON, al * a, mode='O', glow=0.5)


def sc_card2(f, t):
    if not (b(25) - 0.1 < t < b(26) + 0.1): return
    mirror_card(f, t, b(25), b(26), '02', '强，是一个过去时', 'STRENGTH IS PAST TENSE', AMBER)


def sc_match(f, t):
    if not (b(26) - 0.1 < t < b(32) + 0.2): return
    a = env(t, b(26), b(32), 0.35, 0.3)
    strength = 1 + 0.6 * eio((t - b(27, 2)) / BAR)
    morph = eio((t - b(29)) / (BAR * 0.9))
    m = fit_puzzle(f, t, 820, 500, 720, morph, a, strength)
    val = cl(strength / 1.6 * (0.25 + 0.75 * m))
    meter(f, 1380, 260, 700, strength / 1.6, BGOLD, a, '强度')
    meter(f, 1500, 260, 700, m, CYAN, a, '匹配')
    meter(f, 1640, 260, 700, val, lerpc(CRIMSON, BGOLD_L, val), a, '价值')
    f.text('×', 1440, 480, 34, 'sans_black', WHITE, a, mode='O')
    f.text('=', 1570, 480, 34, 'sans_black', WHITE, a, mode='O')
    if t > b(30, 2):
        p = eo((t - b(30, 2)) / 0.5) * a
        f.rrect(820 - 230, 640, 820 + 230, 700, 12, lerpc(AMBER, WHITE, .2), p, 2)
        f.text('「强」= 在旧环境里测出来的', 820, 670, 28, 'sans_black', AMBER, p, mode='O')


# ---- 适应度地形
LX, LZ = 52, 28
_lx = np.linspace(-1, 1, LX); _lz = np.linspace(0, 1, LZ)
LGX, LGZ = np.meshgrid(_lx, _lz)
_bumps = np.random.default_rng(3).uniform(-1, 1, (7, 3))


def land_h(t):
    u = eio((t - b(37)) / (BAR * 1.7))
    hA = 1.0 - 0.78 * u; hB = 0.25 + 0.9 * u
    Hh = hA * np.exp(-((LGX + 0.42) ** 2 / 0.06 + (LGZ - 0.5) ** 2 / 0.05))
    Hh += hB * np.exp(-((LGX - 0.5) ** 2 / 0.07 + (LGZ - 0.55) ** 2 / 0.06))
    for (bx, bz, bh) in _bumps:
        Hh += 0.12 * (bh + 1) / 2 * np.exp(-((LGX - bx) ** 2 + (LGZ - (bz + 1) / 2) ** 2) / 0.02)
    return Hh, hA, hB


def land_proj(xw, zw, hw):
    k = 1 / (1 + 1.1 * zw)
    return W / 2 + xw * 760 * k, 760 - zw * 320 - hw * 280 * k


def sc_landscape(f, t):
    if not (b(32) - 0.1 < t < b(41) + 0.1): return
    a = env(t, b(32), b(41) - 0.2, 0.35, 0.2)
    Hh, hA, hB = land_h(t)
    sweep = eo((t - b(32)) / (BAR * 0.9))
    SX, SY = land_proj(LGX, LGZ, Hh)
    for j in range(LZ - 1, -1, -1):
        if j / (LZ - 1) > sweep: continue
        hcol = [lerpc(lerpc(INDIGO, TEAL, cl(h * 1.6)), BGOLD, cl((h - 0.55) * 2.2)) for h in Hh[j, ::6]]
        f.poly(np.stack([SX[j], SY[j]], 1), hcol[len(hcol) // 2], a * (0.35 + 0.4 * (1 - j / LZ)), 1)
    for i in range(0, LX, 2):
        cols = Hh[:, i].max()
        f.poly(np.stack([SX[:int(sweep * (LZ - 1)) + 1, i], SY[:int(sweep * (LZ - 1)) + 1, i]], 1),
               lerpc(lerpc(INDIGO, TEAL, cl(cols * 1.6)), BGOLD, cl((cols - 0.55) * 2.2)), a * 0.45, 1)
    # 公司（光球）爬上 A 山顶
    climb = eio((t - b(34)) / (BAR * 1.2))
    xa, za = -0.42, 0.5
    xs_, zs_ = -0.95, 0.15
    xw, zw = xs_ + (xa - xs_) * climb, zs_ + (za - zs_) * climb
    hw = hA * math.exp(-((xw + 0.42) ** 2 / 0.06 + (zw - 0.5) ** 2 / 0.05)) + (0.25 if False else 0)
    hw += hB * math.exp(-((xw - 0.5) ** 2 / 0.07 + (zw - 0.55) ** 2 / 0.06))
    bx, by = land_proj(xw, zw, hw)
    if t > b(34) - 0.2:
        comet(f, bx, by - 16, 18 + 6 * cl((t - b(35, 2)) / BAR), BGOLD, a)
        f.text('公司', bx, by - 56, 26, 'sans_black', BGOLD, a, mode='O')
    if b(35, 2) <= t < b(37) + 0.5:   # 资源越堆越多
        rng = np.random.default_rng(int(t * 6))
        for k in range(10):
            ph = ((t - b(35, 2)) * 1.6 + k / 10) % 1
            x = bx + math.sin(k * 2.3) * 60 * (1 - ph)
            y = by - 260 * (1 - ph) - 20
            f.glow((x, y), 5, BGOLD_L, a * math.sin(ph * math.pi), 'E')
        f.text('资源', bx + 90, by - 120, 24, 'sans_med', BGOLD_L, a * env(t, b(35, 2), b(37) + 0.5, 0.3, 0.3), mode='O')
    if t > b(37):
        u = eo((t - b(37)) / 0.6)
        ax_, ay_ = land_proj(-0.42, 0.5, hA)
        bx2, by2 = land_proj(0.5, 0.55, hB)
        f.text('旧山顶', ax_ - 120, ay_ - 30, 28, 'sans_black', lerpc(CRIMSON, WHITE, .3), a * u, mode='O')
        f.text('新山顶', bx2, by2 - 70, 30, 'sans_black', CYAN, a * u, mode='O', glow=0.4)
        f.glow((bx2, by2), 60, CYAN, a * u * 0.14 * (1 + 0.5 * beat_pulse(t)), 'B')
        arrow(f, (ax_ + 140, ay_ - 140), (ax_ + 140, ay_ - 40), CRIMSON, a * u * (1 - cl((t - b(39)) / 1.5)), 3, 14)
    f.text('适应度地形 · 示意', W / 2 + 560, 230, 22, 'sans_light', GREY, a * 0.8, mode='O')
    implode(f, t, b(39, 2), b(41), W / 2, 470, [BGOLD, CYAN, TEAL, WHITE, BGOLD_L, AMBER], 0.6, R0=900)


def sc_formula(f, t):
    if not (b(41) - 0.1 < t < b(45) + 0.3): return
    a = env(t, b(41), b(45), 0.15, 0.35)
    burst(f, t, b(41), W / 2, 470, [BGOLD, BGOLD_L, TEAL, WHITE, CYAN, AMBER], 1, 900, 1900, 1.6)
    toks = [('能力价值', BGOLD, True), ('=', WHITE, False), ('能力', TEAL, True), ('×', WHITE, False), ('环境匹配度', CYAN, True)]
    size = 64; fnt = 'serif_black'; pads = size * 0.55
    widths = [text_width(s_, fnt, size) + (2 * pads if term else 0) for s_, c, term in toks]
    gap = 0.45 * size
    x = W / 2 - (sum(widths) + gap * 4) / 2
    cy = 430
    centers = []
    for i, ((s_, col, term), w) in enumerate(zip(toks, widths)):
        p = cl((t - b(41) - i * BEAT) / 0.35)
        xc = x + w / 2; centers.append(xc)
        if p > 0:
            al = a * eo(p); sc_ = 1 + 0.35 * (1 - eback(p, 2.2)); sz = max(8, int(round(size * sc_)))
            if term:
                hw = w / 2 * sc_; hh = size * 0.9 * sc_
                f.rrect_fill(xc - hw, cy - hh, xc + hw, cy + hh, hh * 0.9, col, 0.14 * al)
                f.rrect(xc - hw, cy - hh, xc + hw, cy + hh, hh * 0.9, col, al, 3)
                f.glow((xc, cy), hw * 0.5, col, 0.2 * al * (1 + bar_pulse(t)), 'B')
                f.text(s_, xc, cy, sz, fnt, lerpc(col, WHITE, 0.55), al, mode='O', glow=0.3)
            else:
                f.text(s_, xc, cy, sz, fnt, col, al, mode='O', glow=0.4)
        x += w + gap
    f.text('思维公式 · 示意，不是数学定律', W / 2, 300, 22, 'sans_light', GREY, a * eo((t - b(42)) / 0.5), mode='O')
    if t > b(42, 2):   # 匹配度下降 → 价值下降
        p = eo((t - b(42, 2)) / 0.4) * a
        drop = eio((t - b(42, 3)) / 1.2)
        bw = 160
        for cxx, col, v in ((centers[2], TEAL, 1.0), (centers[4], CYAN, 1 - 0.7 * drop), (centers[0], BGOLD, 1 - 0.7 * drop)):
            f.fillpoly([(cxx - bw / 2, cy + 120), (cxx - bw / 2 + bw * v, cy + 120), (cxx - bw / 2 + bw * v, cy + 134), (cxx - bw / 2, cy + 134)], col, p * 0.85, 'E')
            f.rrect(cxx - bw / 2 - 4, cy + 116, cxx + bw / 2 + 4, cy + 138, 6, GREY, p * 0.5, 1)


MAP_CAPS = [('测绘数据', 0.9), ('印刷工艺', 0.18), ('书店和加油站渠道', 0.14)]
MAP_DEPS = ['导航需求：还在', '纸质地图需求：缩水', '线下零售：分流']


def icon_map(f, cx, cy, s, a):
    pts = [(cx - s, cy - s * 0.6), (cx - s / 3, cy - s * 0.75), (cx + s / 3, cy - s * 0.6), (cx + s, cy - s * 0.75),
           (cx + s, cy + s * 0.6), (cx + s / 3, cy + s * 0.75), (cx - s / 3, cy + s * 0.6), (cx - s, cy + s * 0.75)]
    f.fillpoly(pts, BGOLD, a * 0.08)
    f.poly(pts, BGOLD, a, 2, closed=True)
    for xx in (cx - s / 3, cx + s / 3):
        f.line((xx, cy - s * 0.7), (xx, cy + s * 0.7), BGOLD, a * 0.5, 1)
    f.poly([(cx - s * 0.8, cy + s * 0.3), (cx - s * 0.3, cy - s * 0.1), (cx + s * 0.2, cy + s * 0.2), (cx + s * 0.75, cy - s * 0.35)], CRIMSON, a * 0.8, 3)


def icon_phone(f, cx, cy, s, a, t):
    f.rrect(cx - s * 0.5, cy - s, cx + s * 0.5, cy + s, s * 0.12, CYAN, a, 3)
    f.circle((cx, cy - s * 0.05), s * 0.16, CYAN, a, 2)
    f.poly([(cx - s * 0.12, cy + s * 0.02), (cx, cy + s * 0.3), (cx + s * 0.12, cy + s * 0.02)], CYAN, a, 2)
    f.circle((cx, cy - s * 0.05), s * (0.25 + 0.25 * ((t * 1.5) % 1)), CYAN, a * (1 - (t * 1.5) % 1) * 0.7, 2)


def sc_case(f, t):
    if not (b(45) - 0.1 < t < b(57) + 0.1): return
    a = env(t, b(45), b(57) - 0.2, 0.35, 0.2)
    dim = 1 - 0.65 * eo((t - b(54)) / 0.6)
    f.rrect(W / 2 - 260, 168, W / 2 + 260, 214, 10, AMBER, a, 2)
    f.text('假设情景 · 教学用，不是真实公司', W / 2, 191, 24, 'sans_black', AMBER, a, mode='O')
    shift = eio((t - b(50)) / 1.0)
    icon_map(f, 470, 470, 150, a * dim * (1 - 0.6 * shift))
    f.text('纸质地图公司', 470, 650, 28, 'sans_med', BGOLD, a * dim, mode='O')
    if shift > 0:
        icon_phone(f, 470 + 230, 430, 110 * eo(shift), a * dim * shift, t)
        f.text('手机定位 · 免费地图', 700, 580, 24, 'sans_med', CYAN, a * dim * shift, mode='O')
    for i, (name, v_after) in enumerate(MAP_CAPS):
        y = 330 + i * 140
        p = eo((t - b(46, 2) - i * BEAT) / 0.45) * a * dim
        if p <= 0: continue
        hl = env(t, b(48) + i * BEAT * 1.3, b(48) + i * BEAT * 1.3 + 1.2, 0.2, 0.5)
        chip(f, name, 1040, y, 30, lerpc(BGOLD, WHITE, hl * 0.4), p, 'sans_black', 0.12 + 0.1 * hl)
        v = 1.0 - (1.0 - v_after) * eio((t - b(50, 2) - i * 0.2) / 1.4)
        colb = BGOLD if v_after > 0.5 else lerpc(BGOLD, CRIMSON, eio((t - b(50, 2)) / 1.4))
        x0 = 1240
        f.rrect(x0, y - 16, x0 + 420, y + 16, 8, GREY, p * 0.5, 1)
        f.rrect_fill(x0 + 4, y - 12, x0 + 4 + 412 * v, y + 12, 6, colb, p * 0.75)
        if t > b(52):
            lab = '依然值钱' if v_after > 0.5 else '大幅缩水'
            f.text(lab, x0 + 470, y, 24, 'sans_black', BGOLD if v_after > 0.5 else CRIMSON, p * eo((t - b(52)) / 0.4), 'l', mode='O')
        if v_after > 0.5 and shift > 0.5:   # 数据流向新环境
            s_ = (np.arange(60) / 60 + t * 0.6) % 1.0
            pts = bez((1040 - 120, y), (900, y - 60), (800, 380), (700, 430), s_)
            f.splat(pts[:, 0], pts[:, 1], BGOLD, a * dim * np.sin(s_ * math.pi) * 2, 'E')
    if t > b(55, 2) - 0.3:   # 能力背后的条件
        p = eo((t - b(55, 2) + 0.3) / 0.5) * a
        for i, dep in enumerate(MAP_DEPS):
            x = W / 2 + (i - 1) * 470
            ok = i == 0
            chip(f, dep, x, 700, 28, TEAL if ok else CRIMSON, p, 'sans_black', 0.14)
            if not ok:
                w2 = text_width(dep, 'sans_black', 28) / 2 + 20
                f.line((x - w2, 700), (x + w2, 700), CRIMSON, p * 0.9, 3)


def sc_species(f, t):
    if not (b(57) - 0.1 < t < b(63) + 0.2): return
    a = env(t, b(57), b(63), 0.5, 0.3)
    burst(f, t, b(57), W / 2, 520, [BLUE, CYAN, WHITE, VIOLET, BLUE, BGOLD], 2, 500, 900, 1.6)
    s1 = env(t, b(57), b(60, 2) + 0.2, 0.4, 0.35)
    if s1 > 0:   # ① DNA 锁定 vs 公司可改写
        cx, cy = 560, 470
        for k in range(2):
            ys = np.linspace(cy - 220, cy + 220, 90)
            xs = cx + 70 * np.sin(ys * 0.03 + t * 1.2 + k * math.pi)
            f.poly(np.stack([xs, ys], 1), [CYAN, VIOLET][k], a * s1, 3)
        for yy in np.linspace(cy - 210, cy + 210, 14):
            x1 = cx + 70 * math.sin(yy * 0.03 + t * 1.2); x2 = cx + 70 * math.sin(yy * 0.03 + t * 1.2 + math.pi)
            f.line((x1, yy), (x2, yy), GREY, a * s1 * 0.5, 1)
        f.rrect(cx + 100, cy - 40, cx + 160, cy + 20, 8, CRIMSON, a * s1, 3)
        f.arc((cx + 130, cy - 40), 22, math.pi, 2 * math.pi, CRIMSON, a * s1, 3, 20)
        f.text('物种：基因不能主动改写', cx, cy + 270, 26, 'sans_med', CYAN, a * s1, mode='O')
        gx, gy = 1360, 470
        gear(f, gx, gy, 120, 12, t * 0.6, BGOLD, a * s1, 3)
        gear(f, gx + 150, gy - 120, 60, 8, -t * 1.2, BGOLD_L, a * s1, 2)
        e = (t * 1.3) % 1
        px, py = gx - 60 + 120 * e, gy + 150 - 40 * math.sin(e * math.pi)
        f.line((px, py), (px + 40, py - 70), WHITE, a * s1, 3)
        f.glow((px, py), 6, BGOLD_L, a * s1, 'E')
        f.text('公司：能力可以主动改变', gx, gy + 270, 26, 'sans_med', BGOLD, a * s1, mode='O')
    s2 = env(t, b(60, 2), b(63), 0.4, 0.3)
    if s2 > 0:   # ② 漂变 · 迁移 · 偶然
        boxes = [(420, '漂变', '纯属偶然的比例波动'), (960, '迁移', '个体进出种群'), (1500, '偶然事件', '一场意外改写结果')]
        for k, (cx, name, desc) in enumerate(boxes):
            p = eo((t - b(60, 2) - k * BEAT) / 0.4) * a * s2
            f.rrect(cx - 220, 270, cx + 220, 640, 18, lerpc(INDIGO, WHITE, .2), p * 0.6, 2)
            f.text(name, cx, 310, 32, 'sans_black', BGOLD, p, mode='O')
            f.text(desc, cx, 600, 22, 'sans_light', TXT, p, mode='O')
            if k == 0:
                for j in range(5):
                    rng = np.random.default_rng(j + 3)
                    walk = 450 + np.cumsum(rng.normal(0, 9, 60))
                    n = int(60 * cl((t - b(60, 2)) / 2.5))
                    if n > 1:
                        f.poly(np.stack([cx - 190 + np.arange(n) * 6.4, np.clip(walk[:n], 360, 560)], 1), [CYAN, TEAL, VIOLET, BGOLD, PINK][j], p * 0.8, 2)
            elif k == 1:
                f.circle((cx - 110, 450), 70, TEAL, p, 2); f.circle((cx + 110, 450), 70, VIOLET, p, 2)
                for j in range(6):
                    ph = ((t * 0.5) + j / 6) % 1
                    f.glow((cx - 110 + 220 * ph, 450 + 30 * math.sin(j + ph * math.pi)), 5, WHITE, p * math.sin(ph * math.pi), 'E')
            else:
                rng = np.random.default_rng(5)
                xs = cx + rng.uniform(-150, 150, 40); ys = 450 + rng.uniform(-90, 90, 40)
                hit = (t - b(61, 2)) % (BAR) < 0.4
                for x_, y_ in zip(xs, ys):
                    gone = hit and abs(x_ - cx - 40) < 70
                    f.glow((x_, y_), 4, CRIMSON if gone else TEAL, p * (0.3 if gone else 0.9), 'E')
                if hit:
                    f.poly([(cx + 60, 340), (cx + 20, 420), (cx + 60, 420), (cx + 20, 520)], BGOLD_L, p, 3)


CAUSES = ['需求', '技术', '制度', '竞争', '决策', '运气']


def sc_causes(f, t):
    if not (b(63) - 0.1 < t < b(67) + 0.2): return
    a = env(t, b(63), b(67), 0.35, 0.3)
    cx, cy = W / 2, 470
    f.circle((cx, cy), 80, BGOLD, a, 3)
    f.text('兴衰', cx, cy, 40, 'serif_black', BGOLD, a, mode='O', glow=0.4)
    for i, name in enumerate(CAUSES):
        q = -math.pi / 2 + i * 2 * math.pi / 6
        p = eo((t - b(63) - i * BEAT / 2) / 0.4) * a
        x, y = cx + 330 * math.cos(q), cy + 220 * math.sin(q)
        chip(f, name, x, y, 30, [CYAN, TEAL, VIOLET, CRIMSON, BGOLD_L, PINK][i], p, 'sans_black', 0.14)
        arrow(f, (cx + 250 * math.cos(q) * 0.8, cy + 170 * math.sin(q) * 0.8), (cx + 95 * math.cos(q), cy + 95 * math.sin(q)), GREY, p * 0.7, 2, 10)
    if t > b(65):
        p = eo((t - b(65)) / 0.5) * a
        for k in range(3):
            f.text('?', cx - 120 + k * 120, cy - 330, 54, 'serif_black', BGOLD, p * (0.6 + 0.4 * math.sin(t * 3 + k)), mode='O', glow=0.5)


def sc_q(f, t):
    if not (b(67) - 0.1 < t < b(69) + 0.1): return
    implode(f, t, b(67), b(69), W / 2, 520, [TEAL, CYAN, BGOLD, WHITE, BGOLD_L, GREEN], 1.0)


VSR = ['看见环境', '制造差异', '内部选择', '保留放大']


def vsr_icon(f, t, k, cx, cy, a, t0):
    if k == 0:   # 雷达
        f.circle((cx, cy), 110, TEAL, a, 2); f.circle((cx, cy), 60, TEAL, a * 0.5, 1)
        q = t * 2.2
        f.line((cx, cy), (cx + 110 * math.cos(q), cy + 110 * math.sin(q)), lerpc(TEAL, WHITE, .4), a, 2)
        for j, (rr, qq) in enumerate(((80, 0.6), (50, 2.4), (95, 4.0))):
            d = (q - qq) % (2 * math.pi)
            f.glow((cx + rr * math.cos(qq), cy + rr * math.sin(qq)), 6, BGOLD, a * math.exp(-d / 1.2), 'E')
    elif k == 1:  # 一个点分化成许多变体
        u = cl((t - t0) / 1.2)
        for j in range(14):
            q = -math.pi / 2 + (j - 6.5) * 0.16
            r = 130 * eo(u)
            col = [CYAN, TEAL, VIOLET, BGOLD, PINK, GREEN][j % 6]
            f.line((cx, cy + 70), (cx + r * math.cos(q), cy + 70 + r * math.sin(q)), col, a * 0.6, 2)
            f.glow((cx + r * math.cos(q), cy + 70 + r * math.sin(q)), 6, col, a, 'E')
    elif k == 2:  # 漏斗：留下少数
        f.poly([(cx - 130, cy - 90), (cx - 25, cy + 30), (cx - 25, cy + 110)], CYAN, a, 2)
        f.poly([(cx + 130, cy - 90), (cx + 25, cy + 30), (cx + 25, cy + 110)], CYAN, a, 2)
        for j in range(10):
            ph = ((t - t0) * 0.8 + j / 10) % 1
            keep = j % 3 == 0
            x = cx + (j - 4.5) * 24 * (1 - ph) if ph < 0.6 else (cx if keep else cx + (j - 4.5) * 30)
            y = cy - 100 + 230 * ph
            f.glow((x, y), 6, BGOLD if keep else GREY, a * (1 if keep or ph < 0.6 else 0.25 * (1 - ph)), 'E')
    else:         # 资源放大
        for j in range(4):
            hh = (40 + 40 * j) * eo((t - t0 - j * 0.15) / 0.6)
            x = cx - 90 + j * 60
            col = BGOLD if j == 3 else lerpc(BGOLD, GREY, .5)
            f.rrect_fill(x - 18, cy + 100 - hh, x + 18, cy + 100, 6, col, a * 0.7)
        arrow(f, (cx - 110, cy + 40), (cx + 110, cy - 110), BGOLD_L, a, 3, 16)


def sc_vsr(f, t):
    if not (b(69) - 0.1 < t < b(78) + 0.2): return
    a = env(t, b(69), b(78), 0.2, 0.35)
    burst(f, t, b(69), W / 2, 520, [TEAL, BGOLD, CYAN, WHITE, BGOLD_L, GREEN], 4, 900, 1900, 1.6)
    cols = [TEAL, VIOLET, CYAN, BGOLD]
    loop_nodes(f, t, W / 2, 560, 560, 200, VSR, cols, b(69, 0.5), a, 0.25, 32, 0.14)
    if t < b(70): return
    k = min(int((t - b(70)) // (BAR * 2)), 3)
    t0 = b(70) + k * BAR * 2
    al = a * env(t, t0, t0 + BAR * 2, 0.3, 0.3)
    vsr_icon(f, t, k, W / 2, 560, al, t0)
    q = -math.pi / 2 + k * math.pi / 2
    f.glow((W / 2 + 560 * math.cos(q), 560 + 200 * math.sin(q)), 80, cols[k], al * 0.35, 'B')


def sc_inner(f, t):
    if not (b(78) - 0.1 < t < b(80, 2) + 0.2): return
    a = env(t, b(78), b(80, 2), 0.25, 0.3)
    u = cl((t - b(78)) / (BAR * 2.5))
    r_out = 470 - 90 * u
    f.circle((W / 2, 520), r_out, CRIMSON, a * 0.7, 3)
    f.text('外部选择', W / 2 + r_out * 0.72, 520 - r_out * 0.72, 26, 'sans_black', CRIMSON, a, mode='O')
    for k in range(3):
        q0 = t * (1.2 + k * 0.3) + k * 2.1
        f.arc((W / 2, 520), 150 + k * 26, q0, q0 + 2.2, BGOLD, a * (0.9 - k * 0.2), 3, 40)
    f.text('内部选择', W / 2, 520 + 240, 26, 'sans_black', BGOLD, a, mode='O')


def sc_tool(f, t):
    if not (b(80, 2) - 0.1 < t < b(85) + 0.2): return
    a = env(t, b(80, 2), b(85), 0.35, 0.3)
    cols = ['能力', '依赖的需求', '依赖的技术', '依赖的制度', '条件消失后']
    dep_table(f, t, 300, 250, cols, ['能力 ①', '能力 ②', '能力 ③'], a, b(80, 2), cw=[230, 280, 280, 280, 250], rh=100,
              fills=lambda i, j: cl((t - b(81) - (i * 4 + j) * 0.18) / 0.4) if j < 4 else cl((t - b(82, 2) - i * 0.3) / 0.4),
              qcol=BGOLD)
    f.text('能力依赖清单', W / 2, 205, 32, 'serif_black', BGOLD, a, mode='O', glow=0.4)


def sc_outro(f, t):
    if not (b(85) - 0.1 < t < T_GATHER0 + 0.1): return
    a = env(t, b(85), T_GATHER0, 0.5, 0.05)
    life_tree(f, t, W / 2, 1040, 290, cl(0.3 + 0.7 * eo((t - b(85)) / (BAR * 5))), a * 0.42)
    flow(f, t, a * 0.18, [BGOLD, TEAL, BGOLD_L, CYAN, GREEN, WHITE], 50, n=900, rise=1.0)




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
# 画面元素汇聚：粒子的起点取自终章那棵生命之树的枝干
_tx0, _ty0, _tx1, _ty1 = tree_pts(W / 2, 1040, 290)
_seg_len = np.hypot(_tx1 - _tx0, _ty1 - _ty0)
_si = _er.choice(len(_seg_len), 5200, p=_seg_len / _seg_len.sum()); _su = _er.uniform(0, 1, 5200)
LP_SX = _tx0[_si] + (_tx1[_si] - _tx0[_si]) * _su; LP_SY = _ty0[_si] + (_ty1[_si] - _ty0[_si]) * _su
LP_DL = _er.uniform(0, 0.35, 5200)
LP_MIX = np.array([lerpc(BGOLD, CYAN, u) for u in _er.uniform(0, 1, 5200)], np.float32)
T_GATHER0, T_GATHER1 = b(93), b(94, 2)    # 生命之树化作粒子，汇聚成 logo
T_LOGO = b(94, 2)                     # 清晰 logo 浮现
T_WORD = b(95)                        # 重拍：金色「巴芒价值」+「BUFFETT · MUNGER」
T_SHIMMER = T_WORD + 0.35
T_FADE0 = b(97)                       # 整片最终淡出


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
    swirl = 3.0 * e * (1 - e)          # 起点 = 生命之树的枝干，终点 = logo，中途旋转
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
SCENES = [sc_hook, sc_title, sc_promise, sc_card1, sc_darwin, sc_sim, sc_card2, sc_match, sc_landscape, sc_formula,
          sc_case, sc_species, sc_causes, sc_q, sc_vsr, sc_inner, sc_tool, sc_outro, sc_end]


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
