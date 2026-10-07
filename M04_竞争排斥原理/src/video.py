"""M04《产品越来越像，竞争会走向哪里？》—— 竞争排斥原理 · 竖屏 3 分 18 秒动态视觉短片（1080×1920）

纯字幕叙事（无人声）、大字号，适合手机竖屏观看。画面切换、字幕出入都落在 120 BPM 的拍点上（1 拍 = 15 帧）。
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

HUD = Hud(frame_w=W)               # 竖屏：按 1080 宽定位到右上角（BRAND.md 边距 52/30）
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
    (0, (70, 15, 60), (10, 50, 75), .75), (b(4) - .05, (70, 15, 60), (10, 50, 75), .6),
    (b(4), (30, 140, 170), (170, 40, 130), 1.4), (b(5), (25, 90, 120), (100, 40, 90), 1.0),
    (b(7), (20, 70, 60), (40, 40, 70), .85), (b(9) - .05, (20, 70, 60), (40, 40, 70), .85),
    (b(9), (20, 110, 80), (20, 50, 90), 1.1), (b(16), (30, 90, 70), (60, 40, 90), .95),
    (b(21, 2), (90, 80, 30), (30, 60, 100), 1.0), (b(25) - .05, (90, 80, 30), (30, 60, 100), .95),
    (b(25), (170, 100, 30), (60, 30, 100), 1.15), (b(29, 2), (40, 70, 130), (90, 40, 110), 1.0),
    (b(35, 2), (130, 100, 30), (40, 60, 120), 1.05), (b(41) - .05, (30, 25, 50), (30, 20, 40), .6),
    (b(41), (200, 140, 40), (40, 130, 140), 1.45), (b(45), (90, 70, 40), (40, 60, 110), 1.0),
    (b(49, 2), (120, 80, 30), (30, 70, 100), 1.0), (b(57) - .05, (120, 80, 30), (30, 70, 100), .95),
    (b(57), (15, 30, 85), (20, 15, 55), .75), (b(61), (20, 60, 70), (60, 20, 50), .8),
    (b(67), (20, 20, 50), (30, 15, 40), .55), (b(69) - .05, (20, 20, 50), (30, 15, 40), .5),
    (b(69), (40, 160, 130), (170, 120, 40), 1.45), (b(71, 2), (80, 40, 60), (40, 80, 120), 1.0),
    (b(75, 2), (130, 90, 30), (40, 70, 100), 1.05), (b(79, 2), (60, 50, 30), (40, 40, 90), .95),
    (b(85), (40, 100, 70), (120, 90, 25), 1.0), (b(93), (20, 40, 100), (30, 20, 60), .7),
    (b(95) - .05, (20, 40, 100), (30, 20, 60), .6), (b(95), (40, 85, 170), (120, 85, 30), 1.15),
    (b(97), (25, 45, 100), (60, 45, 20), .8), (DUR, (10, 15, 30), (10, 10, 20), .4)]

NB1 = fbm(288, 512, 11, 6, 3); NB2 = fbm(288, 512, 22, 6, 3); NB3 = fbm(288, 512, 33, 5, 5)


def bg_at(t):
    a = keys(t, [(k[0], k[1]) for k in BGK]); bcol = keys(t, [(k[0], k[2]) for k in BGK])
    I = keys(t, [(k[0], k[3]) for k in BGK]) * (1 + 0.16 * beat_pulse(t, 0.2) * energy(t))
    s = 1.0 + 0.04 * math.sin(t * 0.07)
    M = np.float32([[s, 0, -9 - 8 * math.sin(t * 0.045)], [0, s, -16 - 14 * math.cos(t * 0.038)]])
    n1 = cv2.warpAffine(NB1, M, (270, 480), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    M2 = np.float32([[s, 0, -9 + 8 * math.sin(t * 0.05 + 1)], [0, s, -16 + 14 * math.sin(t * 0.03)]])
    n2 = cv2.warpAffine(NB2, M2, (270, 480), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    n3 = cv2.warpAffine(NB3, M, (270, 480), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    img = ((n1 ** 3)[..., None] * np.array(a, np.float32) + (n2 ** 3.2)[..., None] * np.array(bcol, np.float32)) * (0.6 + 0.8 * n3)[..., None]
    img *= I * 0.75 / 255.0
    return cv2.resize(img, (W, H), interpolation=cv2.INTER_LINEAR)


_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2)
VIGNETTE = np.clip(1 - 0.42 * _r ** 2.4, 0.25, 1)[..., None].astype(np.float32)
del _yy, _xx, _r

RNG = np.random.default_rng(1234)
NST = 1200
ST_X = RNG.uniform(-1.1, 1.1, NST); ST_Y = RNG.uniform(-1.9, 1.9, NST); ST_Z0 = RNG.uniform(0, 1, NST)
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
                r = 40 + 1500 * eo(d2 / 1.1)
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
            f.text(c['en'], W / 2, yy, 32 if len(c['en']) < 60 else 26, 'corm', lerpc(GREY, WHITE, .35),
                   env(t, c['t0'] + 0.5, c['t1'] - 0.1, 0.5, 0.3) * 0.9, mode='O')
            yy += 50
        if c['who']:
            f.text(c['who'], W / 2, yy, 32, 'sans_light', BSUB, env(t, c['t0'] + 0.8, c['t1'] - 0.1, 0.5, 0.3), mode='O')


# ================================================================ 章节标签与进度条
CHAPTERS = [(0, '序', '序章', 'PROLOGUE'), (b(9), '01', '一支试管，两种草履虫', 'ONE TUBE, TWO SPECIES'),
            (b(25), '02', '排斥发生的三个条件', 'THREE CONDITIONS'), (b(41), '03', '分不出区别，就只比价格', 'NO DIFFERENCE, ONLY PRICE'),
            (b(57), '·', '两个提醒', 'TWO CAVEATS'), (b(69), '04', '分化，才能共存', 'PARTITION TO COEXIST'),
            (b(85), '终', '一个研究问题', 'ONE QUESTION'), (b(93), '终', '片尾', 'END'), (DUR, '', '', '')]
CHROME_END = b(93)


def draw_chrome(f, t):
    """竖屏：左上角章节标签 + 其下一条细进度线（底部留给手机端按钮和文案）"""
    for (a, num, zh, en), (z, *_r) in zip(CHAPTERS, CHAPTERS[1:]):
        if a <= t < z and a < CHROME_END:
            al = env(t, a, min(z, CHROME_END), 0.6, 0.4) * 0.92 * env(t, 0.6, CHROME_END, 0.8, 0.5)
            fn = 'orb' if num.isdigit() else 'serif_black'
            f.text(num, 52, 66, 36, fn, BGOLD, al, 'l', mode='O')
            x = 52 + text_width(num, fn, 36) + 16
            f.line((x, 50), (x, 84), BGOLD, al * 0.6, 1)
            f.text(zh, x + 16, 60, 30, 'sans_med', WHITE, al * 0.95, 'l', mode='O')
            f.text(en, x + 16, 92, 16, 'corm', GREY, al * 0.8, 'l', track=0.3, mode='O')
    pa = 0.55 * env(t, 1.0, CHROME_END, 1.0, 0.6)
    if pa > 0:
        x0, x1, y = 52, W - 52, 140
        f.L[y:y + 2, x0:x1] += np.float32(0.10 * pa)
        xc = x0 + (x1 - x0) * t / CHROME_END
        f.L[y:y + 2, x0:int(min(xc, x1))] += np.array(BGOLD, np.float32) * 0.4 * pa
        for (a, num, zh, en) in CHAPTERS[:-2]:
            xx = int(x0 + (x1 - x0) * a / CHROME_END)
            f.L[y - 6:y + 8, xx:xx + 2] += np.array(BGOLD if t >= a else GREY, np.float32) * 0.5 * pa
        f.glow((min(xc, x1), y + 1), 5, BGOLD_L, 0.9 * pa, 'E')
        f.glow((min(xc, x1), y + 1), 16, BGOLD, 0.5 * pa, 'B')


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
    burst(f, t, t0, W / 2, 820, [col, BGOLD, WHITE, BGOLD_L, col, CYAN], 3, 500, 1100, 1.2)
    rich_line(f, num, W / 2, 680, 140, 'orb', BGOLD, a=a, t0=t0, stag=0.08, underline=False, mode='E', glow_hl=0)
    rich_line(f, zh, W / 2, 850, 84, 'serif_black', TXT, a=a, t0=t0 + 0.15, stag=0.06)
    rich_line(f, en, W / 2, 950, 28, 'corm', BSUB, a=a, t0=t0 + 0.35, stag=0.012, track=0.25, underline=False)
    m_y = 1010   # 镜面：标题字形翻转作倒影
    f.line((W / 2 - 440 * eo((t - t0) / 0.6), m_y), (W / 2 + 440 * eo((t - t0) / 0.6), m_y), col, a * 0.7, 2)
    f.glow((W / 2, m_y), 40, col, a * 0.3, 'B')
    w = text_width(zh, 'serif_black', 84)
    x = W / 2 - w / 2
    for ch in zh:
        m, adv, pad, bl = glyph(ch, 'serif_black', 84)
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


# ================================================================ 炫光层：氛围、地面、光束、景深、调色
def sec_cols(t):
    """当前段落的两种主色（取自背景色表，提亮成霓虹色）"""
    a = np.array(keys(t, [(k[0], k[1]) for k in BGK]), np.float32)
    bcol = np.array(keys(t, [(k[0], k[2]) for k in BGK]), np.float32)
    na = a / max(a.max(), 1); nb = bcol / max(bcol.max(), 1)
    return tuple(0.35 + 0.65 * na), tuple(0.35 + 0.65 * nb)


# ---- 竖屏霓虹透视地面（底部，随节拍滚动）
FHOR = 1450
_PFY = (np.arange((H - FHOR) // 2) * 2 + 1.0)[:, None]
_PFX = (np.arange(W // 2) * 2 - W / 2 + 1.0)[None, :]


def neon_floor(f, t, a, cline, cfill):
    if a <= 0.003: return
    ys = _PFY
    z = 520.0 / ys
    u = _PFX / ys * 1.6
    v = z * 1.6 + t * BPM / 60 * 1.0          # 每拍滚过一格
    fpu = 2.0 / ys * 1.6; fpv = 2.0 * 520 / ys ** 2 * 1.6
    du = 0.5 - np.abs((u % 1.0) - 0.5); dv = 0.5 - np.abs((v % 1.0) - 0.5)
    lu = np.clip(1 - du / (0.02 + fpu), 0, 1) * np.clip(1.2 - fpu * 3, 0, 1)
    lv = np.clip(1 - dv / (0.02 + fpv), 0, 1) * np.clip(1.2 - fpv * 2.5, 0, 1)
    fog = np.exp(-z / 9.0) * np.clip((ys - 2) / 40, 0, 1)
    ln = (np.maximum(lu, lv) * fog * a).astype(np.float32)
    chk = (((np.floor(u) + np.floor(v)) % 2 == 0) * fog * a * 0.10).astype(np.float32)
    hh = H - FHOR
    L = cv2.resize(ln, (W, hh), interpolation=cv2.INTER_LINEAR)
    Fc = cv2.resize(chk, (W, hh), interpolation=cv2.INTER_LINEAR)
    f.L[FHOR:] += L[..., None] * np.array(cline, np.float32) * 0.6 + Fc[..., None] * np.array(cfill, np.float32)
    f.E[FHOR:] += L[..., None] * np.array(cline, np.float32) * 0.25
    band = np.exp(-((np.arange(-50, 51)) / 18.0) ** 2).astype(np.float32)
    f.B[FHOR - 50:FHOR + 51] += band[:, None, None] * np.array(cline, np.float32) * 0.45 * a


# ---- 极光丝带 + 顶部光束（四分之一分辨率计算）
_QY, _QX = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32) * 4
_RAY_ANG = np.arctan2(_QX - W / 2, _QY + 400)
_RAY_FALL = np.clip(1 - _QY / (H * 0.75), 0, 1) ** 1.6


def aurora_rays(f, t, a, c1, c2):
    if a <= 0.003: return
    acc = np.zeros((H // 4, W // 4, 3), np.float32)
    for k, (col, ph, y0) in enumerate(((c1, 0.0, 420), (c2, 2.1, 760), (c1, 4.2, 1100))):
        yc = y0 + 70 * np.sin(_QX * 0.006 + t * 0.5 + ph) + 40 * np.sin(_QX * 0.017 - t * 0.8 + ph)
        band = np.exp(-((_QY - yc) / (55 + 25 * math.sin(t * 0.3 + k))) ** 2)
        shimmer = 0.6 + 0.4 * np.sin(_QX * 0.05 + t * 2 + ph)
        acc += (band * shimmer)[..., None] * np.array(col, np.float32) * 0.10
    rays = (0.5 + 0.5 * np.sin(_RAY_ANG * 34 + t * 0.6)) ** 6 * (0.5 + 0.5 * np.sin(_RAY_ANG * 13 - t * 0.4)) ** 2
    acc += (rays * _RAY_FALL)[..., None] * np.array(lerpc(c1, WHITE, .3), np.float32) * 0.09
    f.B += cv2.resize(acc * a, (W, H), interpolation=cv2.INTER_LINEAR)


# ---- 景深光斑（大而柔的漂浮光点）
_BK = np.random.default_rng(21)
BOKEH = (_BK.uniform(0, W, 26), _BK.uniform(0, H, 26), _BK.uniform(18, 70, 26), _BK.uniform(0, 6.28, 26), _BK.uniform(0.3, 1, 26))


def bokeh(f, t, a, c1, c2):
    if a <= 0.003: return
    X, Y, R, P, S_ = BOKEH
    for i in range(len(X)):
        x = (X[i] + math.sin(t * 0.2 * S_[i] + P[i]) * 60) % W
        y = (Y[i] - t * 14 * S_[i]) % H
        col = c1 if i % 2 else c2
        f.glow((x, y), R[i], col, a * 0.10 * (0.6 + 0.4 * math.sin(t + P[i])), 'B')


# ---- 节拍光环 + 重拍横向光晕（变形镜头光）
def beat_fx(f, t):
    e = energy(t)
    bp = bar_pulse(t, 0.35)
    if bp > 0.02 and e > 0.45:
        r = 200 + 900 * (1 - bp)
        f.circle((W / 2, H * 0.42), r, BGOLD, 0.22 * bp * e, 2)
    for ti, k in SHOCKS:
        dt = t - ti
        if 0 <= dt < 0.9 and k >= 0.4:
            al = k * math.exp(-dt / 0.25)
            y = H * 0.42
            band = np.exp(-((np.arange(-60, 61)) / 9.0) ** 2).astype(np.float32)
            xs = np.exp(-((np.arange(W) - W / 2) / (W * 0.45)) ** 2).astype(np.float32)
            f.B[int(y) - 60:int(y) + 61] += (band[:, None] * xs[None, :])[..., None] * np.array(lerpc(CYAN, WHITE, .4), np.float32) * al * 0.9
            f.glow((W / 2, y), 60, WHITE, al * 0.8, 'B')


def atmosphere(f, t):
    """所有场景共用的氛围层（片尾汇聚时逐渐收起）"""
    k = 1 - cl((t - T_GATHER0) / 1.5)
    if k <= 0: return
    c1, c2 = sec_cols(t)
    e = energy(t)
    aurora_rays(f, t, k * (0.55 + 0.45 * e), c1, c2)
    bokeh(f, t, k, c1, c2)
    neon_floor(f, t, k * (0.45 + 0.4 * e) * (1 + 0.3 * beat_pulse(t)), lerpc(c1, BGOLD, .25), c2)
    beat_fx(f, t)


# ---- 调色：青金分离色调 + 饱和度
def grade(img):
    x = img.astype(np.float32) / 255
    lum = x @ np.array([0.299, 0.587, 0.114], np.float32)
    x = lum[..., None] + (x - lum[..., None]) * 1.18
    sh = np.clip(1 - lum * 2.2, 0, 1)[..., None]; hi = np.clip((lum - 0.45) * 1.8, 0, 1)[..., None]
    x += sh * np.array([-0.004, 0.012, 0.022], np.float32) + hi * np.array([0.03, 0.012, -0.02], np.float32)
    return (np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8)


# ================================================================ 共用图形
CX = W / 2


def spin_ring(f, cx, cy, r, t, col, a, n=24, speed=0.6, th=2, gap=0.45):
    """旋转的虚线光环（扫描仪风格）"""
    if a <= 0.003: return
    for k in range(n):
        q0 = k / n * 2 * math.pi + t * speed
        f.arc((cx, cy), r, q0, q0 + (1 - gap) * 2 * math.pi / n, col, a, th, 6)


def lens_flare(f, x, y, col, a, t=0.0):
    """光点的镜头光：十字星芒 + 光晕 + 沿画面中心对称的小光斑"""
    if a <= 0.003: return
    f.glow((x, y), 70, col, a * 0.35, 'B')
    for L, th in ((260, 9.0), (150, 7.0)):
        xs = np.arange(-L, L + 1)
        g = np.exp(-(xs / (L * 0.45)) ** 2).astype(np.float32)
        y0, x0 = int(y), int(x)
        X = np.clip(xs + x0, 0, W - 1); Y = np.clip(xs + y0, 0, H - 1)
        bw = np.exp(-(np.arange(-3, 4) / (th / 4)) ** 2).astype(np.float32)
        for d, w in zip(range(-3, 4), bw):
            f.B[np.clip(y0 + d, 0, H - 1), X] += g[:, None] * np.array(col, np.float32) * a * 0.55 * w
            f.B[Y, np.clip(x0 + d, 0, W - 1)] += g[:, None] * np.array(col, np.float32) * a * 0.30 * w
    vx, vy = W / 2 - x, H * 0.45 - y
    for k, (u, r) in enumerate(((0.6, 26), (1.2, 14), (1.6, 40), (2.0, 18))):
        f.glow((x + vx * u, y + vy * u), r, lerpc(col, CYAN, k / 4), a * 0.12, 'B')


_FF = np.random.default_rng(5)
FIREFLY = (_FF.uniform(80, 1000, 70), _FF.uniform(240, 1100, 70), _FF.uniform(0, 6.28, 70), _FF.uniform(0.5, 1.5, 70))


def fireflies(f, t, a, col, n=70):
    if a <= 0.003: return
    X, Y, P, S_ = FIREFLY
    x = X[:n] + 40 * np.sin(t * 0.5 * S_[:n] + P[:n]); y = Y[:n] + 30 * np.sin(t * 0.7 * S_[:n] + 2 * P[:n])
    tw = np.clip(np.sin(t * 2.2 * S_[:n] + P[:n]), 0, 1) ** 3
    f.dots(x, y, col, a * tw * 1.5, 1, 'E')
    f.splat(x, y, col, a * tw * 6, 'B')


def bird(f, x, y, s, col, a, t, ph=0.0):
    """简笔小鸟：扇动的 V 形翅膀 + 身体光点"""
    flap = math.sin(t * 9 + ph) * 0.6
    f.poly([(x - s, y - s * (0.4 + flap)), (x, y), (x + s, y - s * (0.4 + flap))], col, a, 2)
    f.glow((x, y + 2), 3, lerpc(col, WHITE, .5), a, 'E')


def hexagon(cx, cy, r, rot=0.0):
    return [(cx + r * math.cos(rot + k * math.pi / 3), cy + r * math.sin(rot + k * math.pi / 3)) for k in range(6)]


def meter_v(f, x, y0, y1, v, col, a, label, size=30):
    f.rrect(x - 34, y0, x + 34, y1, 12, GREY, a * 0.6, 2)
    h = (y1 - y0 - 14) * cl(v)
    f.rrect_fill(x - 27, y1 - 7 - h, x + 27, y1 - 7, 10, col, a * 0.75)
    f.glow((x, y1 - 7 - h), 30, col, a * 0.5, 'B')
    tt = f.t
    if h > 20:
        top = y1 - 7 - h
        f.line((x - 27, top + 3 * math.sin(tt * 5 + x)), (x + 27, top - 3 * math.sin(tt * 5 + x)), lerpc(col, WHITE, .6), a, 2)
        sy = top + (h - 10) * ((tt * 0.9 + x * 0.001) % 1)
        f.fillpoly([(x - 27, sy), (x + 27, sy - 18), (x + 27, sy - 8), (x - 27, sy + 10)], WHITE, a * 0.12)
        for k in range(6):
            u = (tt * (0.5 + 0.13 * k) + k * 0.37 + x * 0.003) % 1
            f.glow((x - 18 + (k * 7) % 36, y1 - 12 - u * (h - 10)), 3.5, lerpc(col, WHITE, .6), a * 0.8 * (1 - u), 'E')
    f.text(label, x, y1 + 42, size, 'sans_black', col, a, mode='O')


def icon_person(f, cx, cy, s, col, a):
    f.circle((cx, cy - s * 0.55), s * 0.28, col, a, 3)
    f.arc((cx, cy + s * 0.45), s * 0.55, math.pi, 2 * math.pi, col, a, 3, 30)


def icon_factory(f, cx, cy, s, col, a, t, stopped=True):
    pts = [(cx - s, cy + s * 0.6), (cx - s, cy - s * 0.1), (cx - s * 0.5, cy - s * 0.4), (cx - s * 0.5, cy - s * 0.1),
           (cx, cy - s * 0.4), (cx, cy - s * 0.1), (cx + s * 0.5, cy - s * 0.4), (cx + s * 0.5, cy - s * 0.9),
           (cx + s * 0.8, cy - s * 0.9), (cx + s * 0.8, cy - s * 0.1), (cx + s, cy - s * 0.1), (cx + s, cy + s * 0.6)]
    f.poly(pts, col, a, 3, closed=True)
    gear(f, cx - s * 0.2, cy + s * 0.22, s * 0.28, 8, 0 if stopped else t * 2, CRIMSON if stopped else TEAL, a, 2)


def icon_shop(f, cx, cy, s, col, a):
    f.rrect(cx - s, cy - s * 0.2, cx + s, cy + s * 0.9, 8, col, a, 3)
    for k in range(5):
        x0 = cx - s + k * s * 0.4
        f.poly([(x0, cy - s * 0.2), (x0 + s * 0.2, cy - s * 0.55), (x0 + s * 0.4, cy - s * 0.2)], col, a, 2)
    f.line((cx - s * 1.05, cy - s * 0.55), (cx + s * 1.05, cy - s * 0.55), col, a, 3)
    f.rrect(cx - s * 0.25, cy + s * 0.3, cx + s * 0.25, cy + s * 0.9, 4, col, a * 0.8, 2)


# ---- 两个对手的颜色（全片统一）：A = 青，B = 品红；分化 / 结论 = 品牌金
CA, CB = CYAN, MAGENTA
CHECK = [('客户选择维度', '客户靠什么选？', CYAN), ('成本', '谁的成本更低？', VIOLET),
         ('空间', '地段、时段分开了吗？', TEAL), ('容量', '市场还在变大吗？', AMBER)]


def cup(f, cx, cy, s, col, a):
    """咖啡杯：杯身 + 把手 + 两缕热气"""
    f.poly([(cx - s, cy - s * 0.6), (cx - s * 0.8, cy + s * 0.7), (cx + s * 0.8, cy + s * 0.7), (cx + s, cy - s * 0.6)], col, a, 3, closed=True)
    f.arc((cx + s * 1.05, cy), s * 0.35, -math.pi / 2, math.pi / 2, col, a, 3, 16)
    for k in (-1, 1):
        ys = np.linspace(0, 1, 12)
        f.poly(np.stack([cx + k * s * 0.3 + 6 * np.sin(ys * 6 + f.t * 3 + k), cy - s * 0.8 - ys * s * 0.7], 1), col, a * 0.6, 2)


def store(f, cx, cy, s, col, a, label=None, size=28):
    icon_shop(f, cx, cy, s, col, a)
    cup(f, cx, cy + s * 0.15, s * 0.22, lerpc(col, WHITE, .3), a)
    f.glow((cx, cy + s * 0.3), s * 0.9, col, a * 0.18 * (1 + 0.5 * beat_pulse(f.t)), 'B')
    if label: f.text(label, cx, cy + s * 1.25, size, 'sans_black', col, a, mode='O')


def paramecium(f, x, y, ang, s, col, a):
    """草履虫：鞋底形的发光轮廓 + 体内光点"""
    q = np.linspace(0, 2 * math.pi, 18)
    px = s * np.cos(q); py = s * 0.42 * np.sin(q) * (1 + 0.28 * np.cos(q))
    ca, sa = math.cos(ang), math.sin(ang)
    f.poly(np.stack([x + px * ca - py * sa, y + px * sa + py * ca], 1), col, a, 2, closed=True)
    f.glow((x, y), s * 0.35, lerpc(col, WHITE, .4), a * 0.9, 'E')


# ---- 高斯实验（教材示意）：种群曲线
def _lg(u, k, u0):
    return 1 / (1 + math.exp(-k * (u - u0)))


def pop_alone_a(u): return 0.97 * (_lg(u, 11, 0.32) - _lg(0, 11, 0.32)) / (1 - _lg(0, 11, 0.32))
def pop_alone_b(u): return 0.80 * (_lg(u, 10, 0.38) - _lg(0, 10, 0.38)) / (1 - _lg(0, 10, 0.38))
def pop_mix_a(u): return 0.92 * (_lg(u, 9, 0.42) - _lg(0, 9, 0.42)) / (1 - _lg(0, 9, 0.42))
def pop_mix_b(u): return 0.62 * (_lg(u, 10, 0.25) - _lg(0, 10, 0.25)) / (1 - _lg(0, 10, 0.25)) * (1 - eio((u - 0.3) / 0.62))


TUBES = [(230, CA, '双小核草履虫', '单独养'), (540, CB, '大草履虫', '单独养'), (850, WHITE, '两种混养', '同一支试管')]
TY0, TY1 = 330, 720
_PR = np.random.default_rng(31)
PARA = {k: (_PR.uniform(0, 6.28, (40, 4)), _PR.uniform(0.5, 1.4, (40, 2))) for k in range(6)}


def tube_pop(f, t, k, cx, frac, col, a, zone=(0.0, 1.0)):
    P, S_ = PARA[k]
    n = frac * 40
    y0 = TY0 + 60 + (TY1 - TY0 - 90) * zone[0]; y1 = TY0 + 60 + (TY1 - TY0 - 90) * zone[1]
    for i in range(int(math.ceil(n))):
        al = a * min(1.0, n - i)
        x = cx + 50 * math.sin(t * 0.6 * S_[i, 0] + P[i, 0]) * math.cos(t * 0.23 + P[i, 1])
        y = y0 + (y1 - y0) * (0.5 + 0.5 * math.sin(t * 0.45 * S_[i, 1] + P[i, 2]))
        ang = math.atan2(math.cos(t * 0.45 * S_[i, 1] + P[i, 2]) * S_[i, 1] * (y1 - y0) * 0.2,
                         math.cos(t * 0.6 * S_[i, 0] + P[i, 0]) * S_[i, 0] * 30 + 1e-3)
        paramecium(f, x, y, ang, 13, col, al)


# ================================================================ 场景
def sc_hook(f, t):
    if t > b(4) + 0.3: return
    a = env(t, 0, b(4), 0.3, 0.25)
    cy = 420
    u = eio(t / b(2))
    xa, xb = 200 + 260 * u, 880 - 260 * u          # 两个一模一样的产品，越靠越近
    lose = eo((t - b(2, 1)) / 1.6)                  # 后半段：其中一家被挤出去
    # 中间的资源：一堆金色光点，被两边来回拉扯
    n = np.arange(160)
    rr = 70 * np.sqrt((n * 0.618) % 1.0); qq = n * 2.39996 + t * 0.6
    pull = 0.35 * np.sin(t * 5 + n) * u * (1 - lose) - 0.6 * lose
    px = CX + rr * np.cos(qq) + pull * 60; py = cy + rr * 0.8 * np.sin(qq)
    f.splat(px, py, BGOLD, a * 1.6, 'E'); f.glow((CX, cy), 90, BGOLD, a * 0.25, 'B')
    for (x, col, k) in ((xa, CA, 0), (xb, CB, 1)):
        al = a * (1 - 0.8 * lose * k)
        yy = cy + 150 * lose * k
        f.rrect(x - 85, yy - 110, x + 85, yy + 110, 20, col, al, 3)
        f.rrect_fill(x - 85, yy - 110, x + 85, yy + 110, 20, col, al * 0.08)
        cup(f, x, yy - 10, 36, lerpc(col, WHITE, .3), al)
        spin_ring(f, x, yy, 150, t * (1 if k else -1), col, al * 0.35, 24, 0.7)
    if 0.35 < u and lose < 0.9:   # 两家之间的摩擦火花
        for j in range(6):
            s_ = math.sin(t * 37 + j * 11.3)
            y0 = cy - 90 + j * 36
            f.line((xa + 85, y0), (CX + 30 * s_, y0 + 18 * math.cos(t * 29 + j)), lerpc(CA, WHITE, .5), a * 0.5 * (u - 0.35) * (1 - lose), 2)
            f.line((xb - 85, y0 + 10), (CX + 30 * s_, y0 + 18 * math.cos(t * 29 + j)), lerpc(CB, WHITE, .5), a * 0.5 * (u - 0.35) * (1 - lose), 2)
    if lose > 0:
        lens_flare(f, xa, cy, CA, a * lose * 0.8, t)
    implode(f, t, b(3), b(4), CX, 900, [BGOLD, CA, CB, WHITE, BGOLD_L, VIOLET], 0.8)


def sc_title(f, t):
    if not (b(4) - 0.1 < t < b(7) + 0.5): return
    a = env(t, b(4), b(7) - 0.05, 0.25, 0.4)
    burst(f, t, b(4), CX, 860, [CA, CB, BGOLD, BGOLD_L, WHITE, VIOLET], 0, 800, 1800, 1.5)
    d = 70 + 20 * math.sin(t * 1.5)
    for k, (sgn, col) in enumerate(((-1, CA), (1, CB))):
        ra = a * eo((t - b(4) - k * 0.15) / 0.6)
        f.circle((CX + sgn * d, 830), 400, col, ra * 0.35, 2)
        spin_ring(f, CX + sgn * d, 830, 440, t * sgn, col, ra * 0.3, 40, 0.2, 2, 0.4)
    spin_ring(f, CX, 830, 520, t, BGOLD, a * 0.2, 28, 0.12, 2, 0.5)
    t0 = b(4)
    rich_line(f, '竞争排斥原理 · COMPETITIVE EXCLUSION', CX, 560, 30, 'sans_med', BGOLD, a=a, t0=t0 + 0.1, stag=0.02, track=0.08, underline=False)
    rich_line(f, '产品越来越像，', CX, 700, 100, 'serif_black', TXT, a=a, t0=t0 + 0.2, stag=0.05)
    rich_line(f, '竞争会', CX, 830, 100, 'serif_black', TXT, a=a, t0=t0 + 0.5, stag=0.05)
    rich_line(f, '{走向哪里}？', CX, 960, 100, 'serif_black', TXT, a=a, t0=t0 + 0.8, stag=0.05, glow_hl=0.6)
    rich_line(f, '《50个自然法则，看懂商业世界》M04', CX, 1110, 36, 'sans_med', lerpc(BSUB, WHITE, .3), a=a, t0=t0 + 1.3, stag=0.015, underline=False)
    rich_line(f, '50 个来自自然、数学与复杂系统的思维模型', CX, 1168, 28, 'sans_light', lerpc(GREY, WHITE, .3), a=a, t0=t0 + 1.6, stag=0.01, underline=False)


def sc_promise(f, t):
    if not (b(7) - 0.1 < t < b(9)): return
    a = env(t, b(7), b(9), 0.4, 0.3)
    for i, (q, sub, col) in enumerate(CHECK):
        chip(f, q, CX, 520 + i * 125, 44, col, a * eo((t - b(7, 2) - i * BEAT * 0.5) / 0.4), 'sans_black', 0.14)


def sc_card1(f, t):
    if not (b(9) - 0.1 < t < b(10) + 0.1): return
    mirror_card(f, t, b(9), b(10), '01', '一支试管，两种草履虫', 'ONE TUBE, TWO SPECIES', TEAL)


def sc_gause(f, t):
    if not (b(10) - 0.1 < t < b(25) + 0.1): return
    a = env(t, b(10), b(25), 0.4, 0.35)
    f.text('G. F. Gause · 1934《生存竞争》', CX, 228, 26, 'sans_light', lerpc(GREY, WHITE, .3), a * eo((t - b(10, 1)) / 0.6), mode='O')
    u12 = cl((t - b(13, 2)) / (BAR * 4)); u3 = cl((t - b(15, 2)) / (BAR * 4))
    sp = eio((t - b(23, 2)) / 1.2)                 # 条件一变：试管分成上下两层（示意）
    foc = env(t, b(17, 2), b(21, 2), 0.4, 0.4)       # 定义段：聚焦混养试管
    for k, (cx, col, name, sub) in enumerate(TUBES):
        p = a * eo((t - b(10) - k * BEAT) / 0.5)
        dim = 1 - 0.55 * foc * (k < 2)
        f.rrect(cx - 78, TY0, cx + 78, TY1, 66, lerpc(col, GREY, .5) if k < 2 else lerpc(BGOLD, WHITE, .2), p * dim * 0.9, 2)
        f.line((cx - 92, TY0), (cx + 92, TY0), lerpc(col, GREY, .4), p * dim * 0.7, 3)
        f.rrect_fill(cx - 72, TY0 + 50, cx + 72, TY1 - 6, 60, TEAL, p * dim * 0.05)
        if k == 2 and sp > 0:
            f.fillpoly([(cx - 72, TY0 + 50), (cx + 72, TY0 + 50), (cx + 72, (TY0 + TY1) / 2 + 20), (cx - 72, (TY0 + TY1) / 2 + 20)], CB, p * sp * 0.08)
            f.line((cx - 76, (TY0 + TY1) / 2 + 20), (cx + 76, (TY0 + TY1) / 2 + 20), BGOLD, p * sp * 0.8, 2)
        f.text(name, cx, TY1 + 46, 28, 'sans_black', col if k < 2 else BGOLD_L, p * dim, mode='O')
        f.text(sub, cx, TY1 + 86, 22, 'sans_light', GREY, p * dim, mode='O')
        # 食物（同一种）落入试管
        fa = p * env(t, b(12), b(25), 0.5, 0.3) * dim
        if fa > 0:
            u = (t * 0.25 + np.arange(14) / 14) % 1.0
            f.splat(cx - 55 + (np.arange(14) * 37) % 110, TY0 + 50 + u * (TY1 - TY0 - 70), BGOLD, fa * 1.4 * (1 - u), 'E')
        if k == 0: tube_pop(f, t, 0, cx, 0.06 + 0.94 * pop_alone_a(u12), CA, p * dim)
        if k == 1: tube_pop(f, t, 1, cx, 0.06 + 0.94 * pop_alone_b(u12), CB, p * dim)
        if k == 2:
            ga = 0.06 + 0.94 * pop_mix_a(u3)
            gb = 0.06 * (1 - u3) + 0.94 * pop_mix_b(u3) + 0.42 * sp
            tube_pop(f, t, 2, cx, ga, CA, p, (0.0 + 0.5 * sp, 1.0))
            tube_pop(f, t, 3, cx, gb, CB, p, (0.0, 1.0 - 0.55 * sp))
            if foc > 0:
                spin_ring(f, cx, (TY0 + TY1) / 2, 250, t, BGOLD, a * foc * 0.5, 28, 0.5)
                f.glow((cx, (TY0 + TY1) / 2), 160, BGOLD, a * foc * 0.12 * (1 + beat_pulse(t)), 'B')
    if sp > 0:
        f.text('示意：换一种环境条件', 850, TY0 - 40, 24, 'sans_med', BGOLD, a * sp, mode='O')
    # 种群曲线（教材示意）
    ca_ = a * env(t, b(13, 2), b(21, 2) + 0.2, 0.5, 0.4)
    if ca_ > 0:
        x0, x1, y0, y1 = 150, 930, 900, 1120
        f.line((x0, y1), (x1, y1), GREY, ca_ * 0.7, 2); f.line((x0, y0 - 10), (x0, y1), GREY, ca_ * 0.7, 2)
        f.text('数量', x0 - 10, y0 - 34, 22, 'sans_med', GREY, ca_, 'l', mode='O')
        f.text('时间 →', x1, y1 + 30, 22, 'sans_med', GREY, ca_, 'r', mode='O')
        f.text('教材示意 · 非实测数据', x1, y0 - 34, 22, 'sans_light', GREY, ca_, 'r', mode='O')
        def curve(fn, u, col, al, th, dash=False):
            if u <= 0: return
            us = np.linspace(0, u, max(2, int(60 * u)))
            pts = np.stack([x0 + (x1 - x0) * us, y1 - (y1 - y0) * np.array([fn(v) for v in us])], 1)
            if dash:
                for j in range(0, len(pts) - 1, 2): f.line(tuple(pts[j]), tuple(pts[j + 1]), col, al, th)
            else:
                f.poly(pts, col, al, th)
            f.glow(tuple(pts[-1]), 6, lerpc(col, WHITE, .5), al, 'E')
        curve(pop_alone_a, u12, CA, ca_ * 0.55, 2, True); curve(pop_alone_b, u12, CB, ca_ * 0.55, 2, True)
        if t >= b(15, 2):
            curve(pop_mix_a, u3, CA, ca_, 4); curve(pop_mix_b, u3, CB, ca_, 4)
            if u3 > 0.95:
                f.text('混养', x0 + 30, y0 + 10, 22, 'sans_black', WHITE, ca_, 'l', mode='O')
                f.text('虚线：单独养', x0 + 110, y0 + 10, 22, 'sans_light', GREY, ca_, 'l', mode='O')
    # 一点优势，被时间放大（示意）
    adv = a * env(t, b(21, 2), b(23, 2) + 0.1, 0.4, 0.35)
    if adv > 0:
        u = eio((t - b(21, 2) - 0.3) / (BAR * 0.9))
        s = 0.52 + 0.45 * u
        x0, x1, y = 160, 920, 1000
        xm = x0 + (x1 - x0) * s
        f.rrect_fill(x0, y - 34, xm, y + 34, 14, CA, adv * 0.55)
        f.rrect_fill(xm, y - 34, x1, y + 34, 14, CB, adv * 0.55 * (1 - 0.6 * u))
        f.rrect(x0, y - 34, x1, y + 34, 14, lerpc(GREY, WHITE, .3), adv, 2)
        f.glow((xm, y), 40, WHITE, adv * 0.5, 'B')
        f.text('示意：每一代只多一点点', CX, y - 74, 24, 'sans_med', GREY, adv, mode='O')
        for g in range(12):
            gx = x0 + (x1 - x0) * g / 11
            f.line((gx, y + 50), (gx, y + 60), GREY, adv * 0.5 * (g / 11 <= u + 0.01), 2)
        f.text('一代又一代 →', x1, y + 92, 22, 'sans_light', GREY, adv, 'r', mode='O')


def sc_card2(f, t):
    if not (b(25) - 0.1 < t < b(26) + 0.1): return
    mirror_card(f, t, b(25), b(26), '02', '排斥发生的三个条件', 'THREE CONDITIONS', VIOLET)


ROWS_Y = [400, 620, 840]


def sc_cond(f, t):
    if not (b(26) - 0.1 < t < b(41) + 0.1): return
    a = env(t, b(26), b(41) - 0.2, 0.35, 0.2)
    t_eco = [b(29, 2), b(31), b(32, 2)]
    t_biz = [b(35, 2), b(37), b(38, 2)]
    eco = ['同一种资源', '需求完全重叠', '资源有限 · 条件稳定']
    biz = ['同一批客户 · 同一种需求', '客户看不出区别', '市场容量有限']
    allon = env(t, b(40), b(41), 0.15, 0.1)
    for i, y in enumerate(ROWS_Y):
        p = a * eo((t - b(27, 2) - i * BEAT) / 0.4)
        on = eo((t - t_eco[i]) / 0.4)
        col = lerpc(GREY, BGOLD, on * 0.6 + allon * 0.4)
        f.rrect(90, y - 95, 990, y + 95, 26, col, p * (0.5 + 0.5 * on), 2 + int(allon > 0.5))
        f.rrect_fill(90, y - 95, 990, y + 95, 26, BGOLD, p * (0.03 + 0.08 * on + 0.15 * allon * (1 + beat_pulse(t))))
        f.text('①②③'[i], 135, y, 40, 'sans_black', col, p, mode='O')
        ix, iy = 260, y
        q = a * on
        if q > 0:
            if i == 0:   # 一堆食物，两个箭头
                f.splat(ix + np.cos(np.arange(30) * 2.4) * (np.arange(30) % 7) * 5, iy + np.sin(np.arange(30) * 2.4) * (np.arange(30) % 7) * 4, BGOLD, q * 1.5, 'E')
                f.glow((ix, iy), 26, BGOLD, q * 0.5, 'B')
                arrow(f, (ix - 95, iy - 40), (ix - 30, iy - 8), CA, q, 3, 12)
                arrow(f, (ix + 95, iy - 40), (ix + 30, iy - 8), CB, q, 3, 12)
            elif i == 1:   # 两个圆，完全重叠
                d = 70 * (1 - eio((t - t_eco[1]) / 1.0))
                f.circle((ix - d, iy), 58, CA, q, 3); f.circle((ix + d, iy), 58, CB, q, 3)
                f.glow((ix, iy), 50, WHITE, q * 0.3 * (1 - d / 70), 'B')
            else:   # 封口的容器，水位固定
                f.poly([(ix - 60, iy - 60), (ix - 60, iy + 60), (ix + 60, iy + 60), (ix + 60, iy - 60)], lerpc(GREY, WHITE, .3), q, 3, closed=True)
                f.line((ix - 70, iy - 60), (ix + 70, iy - 60), BGOLD, q, 4)
                lv = iy + 5 + 3 * math.sin(t * 2)
                f.fillpoly([(ix - 56, lv), (ix + 56, lv), (ix + 56, iy + 56), (ix - 56, iy + 56)], TEAL, q * 0.25)
                f.line((ix - 56, lv), (ix + 56, lv), TEAL, q, 2)
            f.text(eco[i], 360, y - 34, 36, 'sans_black', lerpc(WHITE, col, .3), q, 'l', mode='O')
        bq = a * eo((t - t_biz[i]) / 0.4)
        if bq > 0:
            arrow(f, (360, y + 34), (400, y + 34), BGOLD, bq, 2, 10)
            f.text(biz[i], 418, y + 34, 32, 'sans_black', BGOLD, bq, 'l', mode='O', glow=0.3)
    if t > b(34) - 0.1:
        f.text('生态', 360, ROWS_Y[0] - 140, 24, 'sans_med', GREY, a * eo((t - b(34)) / 0.4), 'l', mode='O')
        f.text('→ 商业', 440, ROWS_Y[0] - 140, 24, 'sans_med', BGOLD, a * eo((t - b(34)) / 0.4), 'l', mode='O')
    implode(f, t, b(39), b(41), CX, 700, [BGOLD, CA, CB, WHITE, BGOLD_L, VIOLET], 0.7, R0=1100)


def product_card(f, cx, cy, col, a, cut=0.0):
    f.rrect(cx - 130, cy - 170, cx + 130, cy + 170, 24, col, a, 3)
    f.rrect_fill(cx - 130, cy - 170, cx + 130, cy + 170, 24, col, a * 0.06)
    cup(f, cx, cy - 40, 50, lerpc(col, WHITE, .3), a)
    f.line((cx - 80, cy + 70), (cx + 80, cy + 70), col, a * 0.6, 2)
    f.line((cx - 80, cy + 105), (cx + 40, cy + 105), col, a * 0.4, 2)


def sc_price(f, t):
    if not (b(41) - 0.1 < t < b(45) + 0.2): return
    a = env(t, b(41), b(45), 0.15, 0.3)
    burst(f, t, b(41), CX, 500, [BGOLD, BGOLD_L, CA, CB, WHITE, AMBER], 1, 900, 1900, 1.6)
    for k, (cx, col) in enumerate(((310, CA), (770, CB))):
        cy = 470 + 10 * math.sin(t * 2 + k * 3)
        product_card(f, cx, cy, col, a)
        # 价格标签：每拍往下掉一格（不写具体数字）
        ph = beat_pulse(t, 0.18)
        tag_y = 250 + 10 * ph
        chip(f, '价格 ↓', cx, tag_y, 32, CRIMSON, a, 'sans_black', 0.16)
        for j in range(3):
            yy = 690 + j * 26 + ((t * 2) % 1) * 26
            f.line((cx - 18, yy), (cx, yy + 14), CRIMSON, a * 0.6 * (1 - j / 3), 3); f.line((cx + 18, yy), (cx, yy + 14), CRIMSON, a * 0.6 * (1 - j / 3), 3)
    f.text('=', CX, 470, 90, 'sans_black', WHITE, a, mode='O', glow=0.4)
    cs = a * eo((t - b(43, 2)) / 0.5)   # 比价格，最后比的是成本
    if cs > 0:
        for k, (cx, col, h) in enumerate(((310, CA, 0.45), (770, CB, 0.8))):
            f.rrect(cx - 40, 760, cx + 40, 1060, 10, GREY, cs * 0.7, 2)
            hh = 290 * h * eo((t - b(43, 2) - 0.2) / 0.8)
            f.rrect_fill(cx - 34, 1054 - hh, cx + 34, 1054, 8, col, cs * 0.7)
            f.text('成本', cx, 1100, 28, 'sans_black', col, cs, mode='O')
        f.glow((310, 900), 120, BGOLD, cs * 0.25 * (1 + beat_pulse(t)), 'B')
        f.text('更低', 420, 960, 30, 'sans_black', BGOLD, cs, 'l', mode='O', glow=0.4)


ROAD_Y = 720
SHOPS = [(330, 460), (750, 460)]
_CR = np.random.default_rng(55)
CUST = (_CR.uniform(0, 1, 44), _CR.uniform(0.07, 0.12, 44), _CR.integers(0, 2, 44), _CR.uniform(-14, 14, 44))


def customers(f, t, a, mode=0.0, speedk=1.0):
    """街上的顾客：从两端走来，拐进其中一家。mode=0 随机进店；mode=1 按偏好（青→A，品红→B）"""
    if a <= 0.003: return
    ph, sp, side, dy = CUST
    for i in range(len(ph)):
        u = (t * sp[i] * speedk + ph[i]) % 1.0
        pref = i % 2
        tgt = int((i * 7 + int(t * sp[i] + ph[i])) % 2) if mode < 0.5 else pref
        sx = SHOPS[tgt][0]
        x_start = -30 if side[i] == 0 else W + 30
        col = WHITE if mode < 0.5 else (CA if pref == 0 else CB)
        if u < 0.7:
            x = x_start + (sx - x_start) * (u / 0.7); y = ROAD_Y + dy[i]
        elif u < 0.85:
            x = sx; y = ROAD_Y + dy[i] - (ROAD_Y - 545) * ((u - 0.7) / 0.15)
        else:
            continue
        al = a * min(1, (0.85 - u) * 10)
        f.glow((x, y), 7, col, al * 0.9, 'E'); f.glow((x, y), 3, WHITE, al, 'E')


def street(f, t, a, label=True):
    f.line((0, ROAD_Y - 40), (W, ROAD_Y - 40), lerpc(GREY, VIOLET, .3), a * 0.7, 2)
    f.line((0, ROAD_Y + 40), (W, ROAD_Y + 40), lerpc(GREY, VIOLET, .3), a * 0.7, 2)
    for k in range(12):
        x = (k * 110 - (t * 60) % 110)
        f.line((x, ROAD_Y), (x + 50, ROAD_Y), lerpc(GREY, WHITE, .2), a * 0.35, 2)
    if label:
        f.rrect(CX - 330, 200, CX + 330, 256, 12, AMBER, a, 2)
        f.text('假设情景 · 教学用，不是真实公司', CX, 228, 30, 'sans_black', AMBER, a, mode='O')


def sc_street(f, t):
    if not (b(45) - 0.1 < t < b(57) + 0.1): return
    a = env(t, b(45), b(57) - 0.2, 0.35, 0.2)
    sd = 1 - 0.6 * eo((t - b(51)) / 0.6)
    street(f, t, a * sd)
    for k, ((sx, sy), col, name) in enumerate(zip(SHOPS, (CA, CB), ('咖啡店 A', '咖啡店 B'))):
        store(f, sx, sy, 100, col, a * sd * eo((t - b(45) - k * BEAT) / 0.5), name, 28)
    if t > b(47):
        for j, lab in enumerate(('豆子', '菜单', '价格')):
            p = a * sd * eo((t - b(47) - j * BEAT) / 0.4)
            f.text(lab, CX, 330 + j * 70, 28, 'sans_black', GREY, p, mode='O')
            f.text('=', CX - 80, 330 + j * 70, 34, 'sans_black', WHITE, p, mode='O'); f.text('=', CX + 80, 330 + j * 70, 34, 'sans_black', WHITE, p, mode='O')
    customers(f, t, a * sd * eo((t - b(49)) / 0.6), 0.0)
    # 三种走向
    outs = [('价格战', CRIMSON, b(53)), ('退出', GREY, b(54, 2)), ('分化', BGOLD, b(56))]
    for j, (lab, col, tt) in enumerate(outs):
        cx = 200 + j * 340; cy = 920
        p = a * eo((t - b(51) - j * BEAT * 0.5) / 0.5)
        if p <= 0: continue
        hi = env(t, tt, b(57), 0.2, 0.2)
        f.rrect(cx - 140, cy - 130, cx + 140, cy + 130, 22, col, p * (0.45 + 0.55 * hi), 2 + int(hi > 0.5))
        f.rrect_fill(cx - 140, cy - 130, cx + 140, cy + 130, 22, col, p * 0.12 * hi)
        f.text(lab, cx, cy + 90, 34, 'sans_black', lerpc(col, WHITE, .3), p, mode='O', glow=0.3 * hi)
        if j == 0:   # 两家利润一起变薄
            for m, c2 in ((-40, CA), (40, CB)):
                hh = 110 * (1 - 0.7 * eo((t - tt) / 1.2) * (t > tt))
                f.rrect_fill(cx + m - 22, cy + 40 - hh, cx + m + 22, cy + 40, 6, c2, p * 0.6)
        elif j == 1:   # 一家熄灭
            f.circle((cx - 50, cy - 20), 34, CA, p, 3)
            f.circle((cx + 50, cy - 20), 34, lerpc(CB, GREY, eo((t - tt) / 0.8) * (t > tt)), p * (1 - 0.6 * eo((t - tt) / 0.8) * (t > tt)), 3)
            if t > tt:
                e = eo((t - tt) / 0.4)
                f.line((cx + 25, cy - 45), (cx + 25 + 50 * e, cy + 5 * e - 45 + 50 * e), CRIMSON, p, 4)
                f.line((cx + 75, cy - 45), (cx + 75 - 50 * e, cy - 45 + 50 * e), CRIMSON, p, 4)
        else:   # 两家朝不同方向走开
            d = 50 * eo((t - tt) / 0.8) * (t > tt)
            f.circle((cx - 30 - d, cy - 20), 30, CA, p, 3); f.circle((cx + 30 + d, cy - 20), 30, CB, p, 3)
            if d > 1:
                arrow(f, (cx - 70, cy - 20), (cx - 70 - d, cy - 20), BGOLD, p, 2, 10)
                arrow(f, (cx + 70, cy - 20), (cx + 70 + d, cy - 20), BGOLD, p, 2, 10)


_LR = np.random.default_rng(66)
MIXP = (_LR.uniform(150, 930, 120), _LR.uniform(330, 820, 120), _LR.integers(0, 3, 120), _LR.uniform(0, 6.28, 120))
CL3 = [(260, 450, '地段'), (820, 450, '时段'), (540, 760, '口味')]


def sc_limits(f, t):
    if not (b(57) - 0.1 < t < b(67) + 0.2): return
    a = env(t, b(57), b(67), 0.5, 0.3)
    burst(f, t, b(57), CX, 600, [BLUE, CYAN, WHITE, VIOLET, BLUE, BGOLD], 2, 500, 900, 1.6)
    s1 = env(t, b(57), b(61) + 0.2, 0.4, 0.35)
    if s1 > 0:   # ① 客户按地段 / 时段 / 口味自然分开
        X, Y, G, P = MIXP
        u = eio((t - b(58, 2)) / 1.6)
        tx = np.array([CL3[g][0] for g in G]) + 90 * np.cos(P) * (0.4 + 0.6 * (np.arange(120) % 5) / 5)
        ty = np.array([CL3[g][1] for g in G]) + 80 * np.sin(P) * (0.4 + 0.6 * (np.arange(120) % 5) / 5)
        x = X + (tx - X) * u + 6 * np.sin(t * 2 + P); y = Y + (ty - Y) * u + 6 * np.cos(t * 2 + P)
        cols = np.array([[CA, VIOLET, CB][g] for g in G], np.float32)
        cols = np.array(WHITE, np.float32) * (1 - u) + cols * u
        f.dots(x, y, cols, a * s1 * 1.2, 2, 'E')
        for k, (cx, cy, lab) in enumerate(CL3):
            p = a * s1 * eo((t - b(59) - k * BEAT) / 0.4)
            f.circle((cx, cy), 150, [CA, VIOLET, CB][k], p * 0.7, 2)
            f.text(lab, cx, cy - 175, 34, 'sans_black', [CA, VIOLET, CB][k], p, mode='O')
    s2 = env(t, b(61), b(64) + 0.2, 0.4, 0.35)
    if s2 > 0:   # ② 条件会变：新客户流入、需求波动
        for k, ((sx, sy), col) in enumerate(zip(SHOPS, (CA, CB))):
            store(f, sx, 520, 90, col, a * s2)
        u = (t * 0.35 + np.arange(60) / 60) % 1.0
        xs = 120 + (np.arange(60) * 131) % 840
        f.dots(xs, 230 + u * 220, BGOLD, a * s2 * eo((t - b(61, 2)) / 0.5) * (1 - u) * 1.3, 2, 'E')
        f.text('新客户进来', CX, 270, 30, 'sans_black', BGOLD, a * s2 * eo((t - b(61, 2)) / 0.5), mode='O')
        xs = np.linspace(100, 980, 120)
        ys = 820 + 60 * np.sin(xs * 0.012 + t * 2.4) * (0.6 + 0.4 * np.sin(t * 0.8))
        p2 = a * s2 * eo((t - b(62)) / 0.5)
        f.poly(np.stack([xs, ys], 1), TEAL, p2, 3)
        f.text('需求波动', 160, 720, 30, 'sans_black', TEAL, p2, 'l', mode='O')
        f.text('两家都能活', CX, 960, 30, 'sans_black', BGOLD_L, a * s2 * eo((t - b(63)) / 0.5), mode='O')
    s3 = env(t, b(64), b(67), 0.4, 0.3)
    if s3 > 0:   # 长得像 ≠ 必然价格战；先查需求重叠
        cup(f, 250, 380, 60, CA, a * s3); cup(f, 400, 380, 60, CB, a * s3)
        f.text('长得像', 325, 490, 32, 'sans_black', WHITE, a * s3, mode='O')
        f.text('≠', CX, 380, 90, 'sans_black', BGOLD, a * s3, mode='O', glow=0.4)
        chip(f, '必然价格战', 800, 380, 34, CRIMSON, a * s3, 'sans_black', 0.12)
        w2 = text_width('必然价格战', 'sans_black', 34) / 2 + 26
        e = eo((t - b(64, 2)) / 0.4)
        f.line((800 - w2, 380), (800 - w2 + 2 * w2 * e, 380), CRIMSON, a * s3, 4)
        q = a * s3 * eo((t - b(65, 2)) / 0.5)
        f.circle((CX - 90, 760), 170, CA, q, 3); f.circle((CX + 90, 760), 170, CB, q, 3)
        f.text('重叠多少？', CX, 760, 34, 'sans_black', BGOLD_L, q, mode='O', glow=0.4)


def sc_q2(f, t):
    if not (b(67) - 0.1 < t < b(69) + 0.1): return
    implode(f, t, b(67), b(69), CX, 900, [CA, CB, BGOLD, WHITE, BGOLD_L, VIOLET], 1.0, R0=1100)


def sc_partition(f, t):
    if not (b(69) - 0.1 < t < b(73, 2) + 0.2): return
    a = env(t, b(69), b(73, 2), 0.15, 0.3)
    burst(f, t, b(69), CX, 500, [CA, BGOLD, CB, WHITE, BGOLD_L, TEAL], 4, 900, 1900, 1.6)
    x0, x1, yb, hmax = 120, 960, 720, 330
    u = eio((t - b(69, 2)) / (BAR * 1.6))
    xs = np.linspace(x0, x1, 200)
    ca_, cb_ = CX - 190 * u, CX + 190 * u
    sw = 150 - 55 * u
    ga = np.exp(-((xs - ca_) / sw) ** 2); gb = np.exp(-((xs - cb_) / sw) ** 2)
    ov = np.minimum(ga, gb)
    for g, col in ((ga, CA), (gb, CB)):
        pts = np.stack([xs, yb - hmax * g], 1)
        f.fillpoly(list(map(tuple, pts)) + [(x1, yb), (x0, yb)], col, a * 0.16)
        f.poly(pts, col, a, 3)
    f.fillpoly(list(map(tuple, np.stack([xs, yb - hmax * ov], 1))) + [(x1, yb), (x0, yb)], CRIMSON, a * 0.25 * (1 - u * 0.6))
    f.line((x0, yb), (x1, yb), GREY, a * 0.8, 2)
    f.text('资源维度：时间 · 空间 · 种类', CX, yb + 40, 26, 'sans_med', GREY, a, mode='O')
    f.text('示意', x1, 250, 22, 'sans_light', GREY, a, 'r', mode='O')
    f.text('重叠区', CX, yb - hmax * float(ov.max()) - 30, 28, 'sans_black', CRIMSON, a * (1 - 0.8 * u), mode='O')
    for k, (xx, col) in enumerate(((ca_, CA), (cb_, CB))):
        comet(f, xx, yb - hmax, 12, col, a * 0.9)
    if t > b(71, 2) - 0.1:
        for j, lab in enumerate(('时间', '空间', '种类')):
            chip(f, lab, 270 + j * 270, 300, 34, BGOLD, a * eo((t - b(71, 2) - j * BEAT) / 0.4), 'sans_black', 0.14)


def sc_cafe2(f, t):
    if not (b(73, 2) - 0.1 < t < b(81) + 0.2): return
    a = env(t, b(73, 2), b(81), 0.35, 0.3)
    street(f, t, a)
    pa = eo((t - b(75, 2)) / 0.5); pb = eo((t - b(77, 2)) / 0.5)
    store(f, SHOPS[0][0], SHOPS[0][1], 100, CA, a, '咖啡店 A', 28)
    store(f, SHOPS[1][0], SHOPS[1][1], 100, CB, a, '咖啡店 B', 28)
    if pa > 0:   # A：早高峰外带（太阳 + 快速箭头）
        sx, sy = SHOPS[0][0], 330
        f.circle((sx, sy), 30, AMBER, a * pa, 3)
        for k in range(8):
            q = k * math.pi / 4 + t * 0.8
            f.line((sx + 40 * math.cos(q), sy + 40 * math.sin(q)), (sx + 54 * math.cos(q), sy + 54 * math.sin(q)), AMBER, a * pa, 2)
        chip(f, '早高峰外带', sx, 830, 32, CA, a * pa, 'sans_black', 0.14)
        for k in range(3):
            xx = sx - 60 + ((t * 300 + k * 60) % 180)
            arrow(f, (xx, 910), (xx + 40, 910), CA, a * pa * 0.7, 2, 10)
    if pb > 0:   # B：午后座位（月牙 + 椅子）
        sx, sy = SHOPS[1][0], 330
        f.arc((sx, sy), 30, math.pi * 0.3, math.pi * 1.7, VIOLET, a * pb, 3, 24)
        chip(f, '午后的座位', sx, 830, 32, CB, a * pb, 'sans_black', 0.14)
        for k in (-1, 0, 1):
            cx = sx + k * 60
            f.line((cx - 14, 920), (cx - 14, 880), CB, a * pb * 0.8, 2); f.line((cx - 14, 905), (cx + 14, 905), CB, a * pb * 0.8, 2)
            f.line((cx + 14, 905), (cx + 14, 925), CB, a * pb * 0.8, 2)
    customers(f, t, a * eo((t - b(74)) / 0.6), 1.0 if t > b(77, 2) else 0.0, 1.0)
    ov = a * eo((t - b(79, 2)) / 0.5)
    if ov > 0:   # 需求重叠：从满格缩到很小（示意）
        u = eio((t - b(79, 2) - 0.2) / 1.6)
        f.text('需求重叠（示意）', CX, 990, 28, 'sans_black', WHITE, ov, mode='O')
        f.rrect(200, 1030, 880, 1070, 14, GREY, ov, 2)
        f.rrect_fill(206, 1036, 206 + 668 * (1 - 0.85 * u), 1064, 10, lerpc(CRIMSON, BGOLD, u), ov * 0.8)


def sc_check(f, t):
    if not (b(81) - 0.1 < t < b(85) + 0.2): return
    a = env(t, b(81), b(85), 0.35, 0.3)
    x0, x1, y0, y1 = 110, 970, 230, 1110
    f.rrect_fill(x0, y0, x1, y1, 30, BGOLD, a * 0.05)
    f.rrect(x0, y0, x1, y1, 30, BGOLD, a, 3)
    spin_ring(f, x1 - 10, y0 + 10, 40, t, BGOLD_L, a * 0.5, 16, 0.6)
    f.text('重叠度检查表', CX, y0 + 70, 48, 'serif_black', BGOLD, a, mode='O', glow=0.4)
    for i, (q, sub, col) in enumerate(CHECK):
        y = y0 + 200 + i * 205
        p = eo((t - b(81, 1) - i * BEAT * 0.5) / 0.4) * a
        f.text(q, x0 + 60, y - 18, 40, 'sans_black', col, p, 'l', mode='O')
        f.text(sub, x0 + 60, y + 38, 28, 'sans_light', TXT, p * eo((t - b(83) - i * BEAT * 0.5) / 0.4), 'l', mode='O')
        # 重叠度刻度：低（分开）← → 高（同质）
        mx0, mx1 = x1 - 330, x1 - 70
        f.line((mx0, y + 70), (mx1, y + 70), GREY, p * 0.6, 2)
        v = 0.25 + 0.5 * (0.5 + 0.5 * math.sin(t * 1.3 + i * 1.7))
        f.glow((mx0 + (mx1 - mx0) * v, y + 70), 9, lerpc(BGOLD, CRIMSON, v), p, 'E')
        f.glow((mx0 + (mx1 - mx0) * v, y + 70), 22, lerpc(BGOLD, CRIMSON, v), p * 0.5, 'B')
        if i == 0:
            f.text('分开', mx0, y + 100, 20, 'sans_light', GREY, p, mode='O'); f.text('重叠', mx1, y + 100, 20, 'sans_light', GREY, p, mode='O')
        ok = eo((t - b(83, 2) - i * BEAT * 0.5) / 0.4)
        if ok > 0:
            f.circle((x1 - 200, y - 18), 26, TEAL, a * ok, 3)
            f.text('?', x1 - 200, y - 18, 30, 'sans_black', TEAL, a * ok, mode='O')


# ---- 终章：A、B 两家的客户圈（片尾粒子从两个圈出发）
OC_Y, OC_R = 470, 220


def outro_sep(t):
    return 80 + 150 * eio((t - b(89)) / (BAR * 2.5))


_OR = np.random.default_rng(12)
OCP = (_OR.uniform(0, 6.28, 160), np.sqrt(_OR.uniform(0, 1, 160)), _OR.uniform(0.3, 1.0, 160))


def sc_outro(f, t):
    if not (b(85) - 0.1 < t < T_GATHER0 + 0.1): return
    a = env(t, b(85), T_GATHER0, 0.5, 0.05)
    d = outro_sep(t)
    q, r, s = OCP
    for k, (sgn, col) in enumerate(((-1, CA), (1, CB))):
        cx = CX + sgn * d
        f.circle((cx, OC_Y), OC_R, col, a, 3)
        spin_ring(f, cx, OC_Y, OC_R + 24, t * sgn, col, a * 0.3, 36, 0.3)
        f.fillpoly([(cx + OC_R * math.cos(v), OC_Y + OC_R * math.sin(v)) for v in np.linspace(0, 2 * math.pi, 48)], col, a * 0.05)
        qq = q + t * s * 0.6 * sgn
        f.dots(cx + OC_R * 0.88 * r * np.cos(qq), OC_Y + OC_R * 0.88 * r * np.sin(qq), lerpc(col, WHITE, .3), a * 0.9, 1, 'E')
        f.text('A 的客户' if k == 0 else 'B 的客户', cx + sgn * 80, OC_Y - OC_R - 40, 28, 'sans_black', col, a, mode='O')
    ovw = max(0.0, OC_R - d)   # 重叠区：随节拍发光
    if ovw > 1:
        g = env(t, b(87), T_GATHER0, 0.4, 0.3)
        f.glow((CX, OC_Y), ovw * 0.9, BGOLD, a * (0.25 + 0.35 * g) * (1 + 0.5 * beat_pulse(t)), 'B')
        f.text('?', CX, OC_Y, 60 * (0.6 + 0.4 * ovw / OC_R), 'sans_black', BGOLD_L, a * g * cl(ovw / 60), mode='O', glow=0.5)



# ================================================================ 片尾：粒子汇聚成官方 logo
END_LOGO_PX = 220                    # BRAND.md：片尾 logo 约 220px
END_LOGO = load_logo(END_LOGO_PX)    # (rgb, alpha) —— brand/logo_baman.png 原图
LOGO_C = (W / 2, 800)
_er = np.random.default_rng(99)
_la = END_LOGO[1]
_ys, _xs = np.nonzero(_la > 0.25)
_pick = _er.choice(len(_ys), 5200, p=_la[_ys, _xs] / _la[_ys, _xs].sum())
LP_TX = _xs[_pick] + LOGO_C[0] - END_LOGO_PX / 2 + _er.uniform(-0.5, 0.5, 5200)
LP_TY = _ys[_pick] + LOGO_C[1] - END_LOGO_PX / 2 + _er.uniform(-0.5, 0.5, 5200)
LP_COL = np.clip(END_LOGO[0][_ys[_pick], _xs[_pick]] * 1.15, 0, 1).astype(np.float32)
# 画面元素汇聚：粒子的起点取自终章 A、B 两个客户圈（圈边 + 圈内客户）
_side = np.where(_er.uniform(0, 1, 5200) < 0.5, -1, 1); _q = _er.uniform(0, 2 * math.pi, 5200)
_rr = np.where(_er.uniform(0, 1, 5200) < 0.7, 1.0, np.sqrt(_er.uniform(0, 1, 5200)) * 0.88)
LP_SX = CX + _side * outro_sep(b(93)) + OC_R * _rr * np.cos(_q)
LP_SY = OC_Y + OC_R * _rr * np.sin(_q)
LP_DL = _er.uniform(0, 0.35, 5200)
LP_MIX = np.where((_side < 0)[:, None], np.array(CA, np.float32), np.array(CB, np.float32)) * 0.7 + np.array(BGOLD, np.float32) * 0.3
T_GATHER0, T_GATHER1 = b(93), b(94, 2)    # 两个客户圈化作粒子，汇聚成 logo
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
        burst(f, t, T_WORD, LOGO_C[0], 1060, [LOGO_GLOW, CYAN, BGOLD, BGOLD_L, WHITE, BLUE], 7, 600, 1300, 1.5)
        f.glow((W / 2, 1060), 300, BGOLD, 0.25 * math.exp(-(t - T_WORD) / 0.6), 'B')


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
        ty = 1060
        post_over(img, rr1, a1, W / 2, ty, wa)
        sa = eo((t - T_WORD - 0.15) / 0.45)
        post_over(img, r2, a2, W / 2, ty + a1.shape[0] / 2 + SUBGAP + a2.shape[0] / 2, sa)


# ================================================================ 渲染
SCENES = [sc_hook, sc_title, sc_promise, sc_card1, sc_gause, sc_card2, sc_cond, sc_price, sc_street, sc_limits, sc_q2,
          sc_partition, sc_cafe2, sc_check, sc_outro, sc_end]


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
    atmosphere(f, t)
    for s in SCENES:
        s(f, t)
    draw_caps(f, t)
    shockwaves(f, t)
    draw_chrome(f, t)
    img = finish(f, bg, bloom_k=1.15 + 0.4 * beat_pulse(t) * energy(t), vignette=VIGNETTE)
    img = grade(img)
    # 镜头"呼吸"：缓慢推拉 + 每拍轻微一推 + 重拍冲击
    z = 0.012 * (0.5 + 0.5 * math.sin(t * 0.35)) + 0.006 * beat_pulse(t, 0.12) * energy(t) + zoom_punch(t)
    M = cv2.getRotationMatrix2D((W / 2, H * 0.45), 0.25 * math.sin(t * 0.21), 1 + z)
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
