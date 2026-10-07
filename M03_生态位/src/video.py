"""M03《不当行业第一，也能做成好生意吗？》—— 生态位理论 · 竖屏 3 分半动态视觉短片（1080×1920）

纯字幕叙事（无人声）、大字号，适合手机竖屏观看。画面切换、字幕出入都落在 112.5 BPM 的拍点上（1 拍 = 16 帧）。
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
    (0, (60, 20, 30), (20, 40, 50), .75), (b(4) - .05, (60, 20, 30), (20, 40, 50), .6),
    (b(4), (40, 160, 110), (170, 120, 30), 1.4), (b(5), (25, 110, 80), (90, 80, 30), 1.0),
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
CHAPTERS = [(0, '序', '序章', 'PROLOGUE'), (b(9), '01', '同一棵树，不同的饭碗', 'SAME TREE, DIFFERENT TABLES'),
            (b(25), '02', '生态位，是一组选择', 'A NICHE IS A SET OF CHOICES'), (b(41), '03', '不当第一，当最合适', 'BEST FIT, NOT FIRST'),
            (b(57), '·', '两个提醒', 'TWO CAVEATS'), (b(69), '04', '取舍，才守得住', 'TRADE-OFFS DEFEND'),
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


# ---- 生态位卡片 / 三问
QUESTIONS = [('服务谁', CYAN), ('怎样交付', VIOLET), ('放弃什么', AMBER)]

# ================================================================ 场景
_HR = np.random.default_rng(3)
SWARM = (_HR.normal(0, 1, (260, 2)), _HR.uniform(0, 6.28, 260))


def sc_hook(f, t):
    if t > b(4) + 0.3: return
    a = env(t, 0, b(4), 0.3, 0.25)
    # 拥挤的「第一」：红色粒子挤在皇冠周围
    cx, cy = CX, 380
    crown = [(cx - 70, cy + 30), (cx - 80, cy - 40), (cx - 35, cy), (cx, cy - 60), (cx + 35, cy), (cx + 80, cy - 40), (cx + 70, cy + 30)]
    f.poly(crown, CRIMSON, a, 4, closed=True)
    f.text('第一', cx, cy + 70, 34, 'sans_black', CRIMSON, a, mode='O')
    P, ph = SWARM
    xs = cx + P[:, 0] * 150 + np.sin(t * 7 + ph) * 18
    ys = cy + P[:, 1] * 70 + np.cos(t * 6 + ph) * 14
    for k, dt in enumerate((0.0, 0.04, 0.08, 0.12)):   # 拖尾
        xs_ = cx + P[:, 0] * 150 + np.sin((t - dt) * 7 + ph) * 18
        ys_ = cy + P[:, 1] * 70 + np.cos((t - dt) * 6 + ph) * 14
        f.splat(xs_, ys_, CRIMSON, a * 1.6 * (1 - k * 0.24), 'E')
    f.splat(xs + 1, ys, lerpc(CRIMSON, WHITE, .3), a * 0.8, 'E')
    spin_ring(f, cx, cy, 250, t, CRIMSON, a * 0.45, 30, 0.9)
    spin_ring(f, cx, cy, 290, -t, lerpc(CRIMSON, AMBER, .4), a * 0.25, 12, 0.5, 1, 0.7)
    f.glow((cx, cy), 200, CRIMSON, a * 0.18 * (1 + beat_pulse(t)), 'B')
    # 安静的好位置：金色光点在自己的圈里
    gx, gy = 780, 1340
    al = a * env(t, b(1), b(4), 0.5, 0.25)
    f.circle((gx, gy), 110 + 6 * math.sin(t * 2), BGOLD, al * 0.7, 2)
    comet(f, gx, gy, 24, BGOLD, al)
    lens_flare(f, gx, gy, BGOLD, al * (0.7 + 0.3 * math.sin(t * 3)), t)
    spin_ring(f, gx, gy, 140, t, BGOLD_L, al * 0.5, 20, 0.4)
    f.text('自己的位置', gx, gy + 150, 32, 'sans_black', BGOLD, al, mode='O')
    implode(f, t, b(3), b(4), CX, 900, [BGOLD, TEAL, CYAN, WHITE, BGOLD_L, GREEN], 0.8)


TREE_Z = [(260, 480, '树冠', CYAN), (480, 700, '树干', BGOLD), (700, 900, '灌木', PINK), (900, 1080, '地面', VIOLET)]


def forest_tree(f, t, a, scale=1.0, cy0=0.0):
    """竖屏正中的一棵针叶树：层层三角树冠 + 树干 + 两侧灌木 + 地面"""
    if a <= 0.003: return
    def Y(y): return cy0 + y * scale
    def X(x): return CX + (x - CX) * scale
    for k, (yt, w) in enumerate(((260, 120), (360, 190), (460, 260), (560, 320))):
        f.poly([(X(CX - w), Y(yt + 140)), (X(CX), Y(yt)), (X(CX + w), Y(yt + 140))], lerpc(TEAL, GREEN, k / 4), a * 0.85, 3)
    f.line((X(CX - 14), Y(700)), (X(CX - 14), Y(1080)), lerpc(AMBER, GREY, .4), a * 0.8, 3)
    f.line((X(CX + 14), Y(700)), (X(CX + 14), Y(1080)), lerpc(AMBER, GREY, .4), a * 0.8, 3)
    for sx in (-1, 1):
        for k in range(3):
            f.arc((X(CX + sx * (260 + k * 70)), Y(960)), 60 * scale, math.pi, 2 * math.pi, lerpc(GREEN, TEAL, k / 3), a * 0.7, 2, 24)
    f.line((X(80), Y(1080)), (X(1000), Y(1080)), lerpc(VIOLET, GREY, .3), a * 0.8, 2)


BIRDS = [(z, k) for z in range(4) for k in range(3)]


def sc_title(f, t):
    if not (b(4) - 0.1 < t < b(7) + 0.5): return
    a = env(t, b(4), b(7) - 0.05, 0.25, 0.4)
    burst(f, t, b(4), CX, 860, [TEAL, BGOLD, BGOLD_L, CYAN, WHITE, GREEN], 0, 800, 1800, 1.5)
    forest_tree(f, t, a * 0.3, 1.0, 120)
    for k, (r, sp, col) in enumerate(((420, 0.25, BGOLD), (480, -0.18, TEAL), (540, 0.12, CYAN))):
        ra = a * eo((t - b(4) - k * 0.15) / 0.6)
        spin_ring(f, CX, 830, r, t, col, ra * (0.35 - k * 0.07), 36 - k * 8, sp, 2, 0.35 + k * 0.1)
    t0 = b(4)
    rich_line(f, '生态位 · ECOLOGICAL NICHE', CX, 560, 34, 'sans_med', BGOLD, a=a, t0=t0 + 0.1, stag=0.02, track=0.1, underline=False)
    rich_line(f, '不当行业第一，', CX, 700, 104, 'serif_black', TXT, a=a, t0=t0 + 0.2, stag=0.05)
    rich_line(f, '也能做成', CX, 830, 104, 'serif_black', TXT, a=a, t0=t0 + 0.5, stag=0.05)
    rich_line(f, '{好生意}吗？', CX, 960, 104, 'serif_black', TXT, a=a, t0=t0 + 0.8, stag=0.05, glow_hl=0.6)
    rich_line(f, '《50个自然法则，看懂商业世界》M03', CX, 1110, 36, 'sans_med', lerpc(BSUB, WHITE, .3), a=a, t0=t0 + 1.3, stag=0.015, underline=False)
    rich_line(f, '50 个来自自然、数学与复杂系统的思维模型', CX, 1168, 28, 'sans_light', lerpc(GREY, WHITE, .3), a=a, t0=t0 + 1.6, stag=0.01, underline=False)


def sc_promise(f, t):
    if not (b(7) - 0.1 < t < b(9)): return
    a = env(t, b(7), b(9), 0.4, 0.3)
    for i, (q, col) in enumerate(QUESTIONS):
        chip(f, q, CX, 640 + i * 150, 50, col, a * eo((t - b(7, 2) - i * BEAT) / 0.4), 'sans_black', 0.14)


def sc_card1(f, t):
    if not (b(9) - 0.1 < t < b(10) + 0.1): return
    mirror_card(f, t, b(9), b(10), '01', '同一棵树，不同的饭碗', 'SAME TREE, DIFFERENT TABLES', TEAL)


def sc_forest(f, t):
    if not (b(10) - 0.1 < t < b(25) + 0.1): return
    a = env(t, b(10), b(25), 0.4, 0.35)
    for k in range(5):   # 透过树冠的光束
        x0 = 180 + k * 180 + 30 * math.sin(t * 0.3 + k)
        sh = (0.5 + 0.5 * math.sin(t * 0.8 + k * 1.7))
        f.fillpoly([(x0 - 18, 180), (x0 + 18, 180), (x0 + 120, 1080), (x0 + 30, 1080)], lerpc(BGOLD_L, TEAL, .3), a * 0.05 * sh, 'B')
    forest_tree(f, t, a, 1.0, 0)
    fireflies(f, t, a * 0.8, lerpc(BGOLD_L, GREEN, .3))
    f.text('示意图 · 非实测数据', CX, 215, 26, 'sans_light', GREY, a, mode='O')
    part = env(t, b(21, 2), b(25), 0.5, 0.4)
    for zi, (y0, y1, name, col) in enumerate(TREE_Z):
        if part > 0:
            f.fillpoly([(70, y0 + 6), (1010, y0 + 6), (1010, y1 - 6), (70, y1 - 6)], col, a * part * 0.10)
            f.line((70, y1), (1010, y1), col, a * part * 0.6, 1)
        al = a * env(t, b(13) + zi * BEAT / 2, b(25), 0.4, 0.3)
        f.text(name, 120, (y0 + y1) / 2, 34, 'sans_black', col, al, mode='O')
    for (zi, k) in BIRDS:   # 每种鸟只在自己的树层活动
        y0, y1, name, col = TREE_Z[zi]
        u = (t * (0.12 + 0.03 * k) + k * 0.33 + zi * 0.17) % 1.0
        x = 260 + 560 * (0.5 + 0.5 * math.sin(u * 2 * math.pi + k))
        y = y0 + 40 + (y1 - y0 - 80) * (0.5 + 0.5 * math.sin(u * 4 * math.pi + zi))
        ba = a * eo((t - b(11, 2) - zi * BEAT / 2) / 0.5)
        bird(f, x, y, 20, col, ba, t, k + zi)
        tr = [(260 + 560 * (0.5 + 0.5 * math.sin(((u - d * 0.004) % 1) * 2 * math.pi + k)),
               y0 + 40 + (y1 - y0 - 80) * (0.5 + 0.5 * math.sin(((u - d * 0.004) % 1) * 4 * math.pi + zi))) for d in range(12)]
        f.splat(np.array([p[0] for p in tr]), np.array([p[1] for p in tr]), col, ba * np.linspace(1.2, 0.1, 12), 'E')
    s2 = env(t, b(18), b(21, 2) + 0.2, 0.4, 0.35)   # 生态位 ≠ 地点
    if s2 > 0:
        for i, (lab, col) in enumerate((('吃什么', CYAN), ('需要什么环境', BGOLD), ('和谁互动', PINK))):
            p = eo((t - b(19, 2) - i * BEAT) / 0.4) * a * s2
            chip(f, lab, 820, 360 + i * 200, 34, col, p, 'sans_black', 0.16)


# ---- 三问维恩图
VENN = [(CX, 470, CYAN, '服务谁', '哪些人 · 什么场景'), (CX - 150, 720, VIOLET, '怎样交付', '方式 · 成本'),
        (CX + 150, 720, AMBER, '放弃什么', '不做的客户和生意')]
VR = 230
_vy, _vx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32) * 2
VMASK = np.ones((H // 2, W // 2), np.float32)
for (vx, vy, *_r) in VENN:
    VMASK *= (((_vx - vx) ** 2 + (_vy - vy) ** 2) < VR * VR)
VMASK = cv2.GaussianBlur(VMASK, (0, 0), 1.5)
VMASK_BIG = cv2.resize(VMASK, (W, H), interpolation=cv2.INTER_LINEAR)
del _vy, _vx


def sc_card2(f, t):
    if not (b(25) - 0.1 < t < b(26) + 0.1): return
    mirror_card(f, t, b(25), b(26), '02', '生态位，是一组选择', 'A NICHE IS A SET OF CHOICES', AMBER)


def sc_venn(f, t):
    if not (b(26) - 0.1 < t < b(41) + 0.1): return
    a = env(t, b(26), b(41) - 0.2, 0.35, 0.2)
    s1 = env(t, b(26), b(29, 2) + 0.3, 0.4, 0.35)
    if s1 > 0:   # 一门生意 = 在约束下，为某些人完成某件事
        icon_person(f, 320, 600, 90, CYAN, a * s1)
        arrow(f, (420, 600), (640, 600), BGOLD, a * s1 * eo((t - b(27, 2)) / 0.5), 3, 16)
        f.rrect(670, 530, 830, 670, 14, BGOLD, a * s1 * eo((t - b(27, 2)) / 0.5), 3)
        f.text('一件事', 750, 600, 34, 'sans_black', BGOLD, a * s1 * eo((t - b(27, 3)) / 0.5), mode='O')
        f.rrect(200, 430, 900, 780, 30, lerpc(GREY, WHITE, .2), a * s1 * 0.5 * eo((t - b(28)) / 0.5), 2)
        f.text('约束', 860, 460, 28, 'sans_med', GREY, a * s1 * eo((t - b(28)) / 0.5), mode='O')
    t_in = [b(31), b(32, 2), b(34)]
    for i, (vx, vy, col, name, sub) in enumerate(VENN):
        p = eo((t - (b(29, 2) + 0.3 + i * BEAT)) / 0.5) * a
        if p <= 0: continue
        hl = env(t, t_in[i], t_in[i] + BAR * 1.5, 0.2, 0.3)
        f.circle((vx, vy), VR, col, p, 3 + int(hl > 0.5))
        q = t * (0.5 + 0.12 * i) * (1 if i != 1 else -1) + i * 2.1 + np.linspace(0, 0.9, 40)
        f.splat(vx + VR * np.cos(q), vy + VR * np.sin(q), lerpc(col, WHITE, .4), p * np.linspace(0.1, 2.2, 40), 'E')
        f.glow((vx + VR * math.cos(q[-1]), vy + VR * math.sin(q[-1])), 16, col, p * 0.8, 'B')
        spin_ring(f, vx, vy, VR + 22, t * (1 if i % 2 else -1), col, p * 0.22, 40, 0.15, 1)
        f.fillpoly([(vx + VR * math.cos(q), vy + VR * math.sin(q)) for q in np.linspace(0, 2 * math.pi, 48)], col, p * (0.05 + 0.08 * hl))
        ox, oy = (0, -110) if i == 0 else ((-110, 70) if i == 1 else (110, 70))
        f.text(name, vx + ox, vy + oy, 38, 'sans_black', lerpc(col, WHITE, .3), p, mode='O', glow=0.3)
        f.text(sub, vx + ox, vy + oy + 46, 24, 'sans_light', TXT, p * (0.5 + 0.5 * hl), mode='O')
    g = env(t, b(35, 2), b(39) + 0.2, 0.4, 0.4)
    if g > 0:   # 三问的交集 = 生态位
        f.L += VMASK_BIG[..., None] * np.array(BGOLD, np.float32) * (0.35 * g * a * (1 + 0.4 * beat_pulse(t)))
        f.text('生态位', CX, 640, 40, 'serif_black', BGOLD_L, a * g, mode='O', glow=0.5)
        f.text('✓ 可检验', CX, 690, 24, 'sans_med', BGOLD, a * g * eo((t - b(36, 2)) / 0.4), mode='O')
    if t > b(37, 2):
        p = env(t, b(37, 2), b(39, 2), 0.4, 0.3) * a
        f.text('#1 ?', CX, 250, 56, 'orb', lerpc(CRIMSON, WHITE, .3), p, mode='O', glow=0.4)
    implode(f, t, b(39), b(41), CX, 700, [BGOLD, TEAL, CYAN, WHITE, BGOLD_L, AMBER], 0.7, R0=1100)


def sc_fit(f, t):
    if not (b(41) - 0.1 < t < b(49, 2) + 0.2): return
    a = env(t, b(41), b(49, 2), 0.15, 0.35)
    burst(f, t, b(41), CX, 700, [BGOLD, BGOLD_L, TEAL, WHITE, CYAN, AMBER], 1, 900, 1900, 1.6)
    s1 = env(t, b(41), b(43, 2) + 0.2, 0.2, 0.35)
    if s1 > 0:   # 领奖台（红，拥挤）vs 一个刚好合适的位置（金）
        for k, (x, h) in enumerate(((CX - 230, 140), (CX - 80, 220), (CX + 70, 110))):
            f.rrect(x - 60, 720 - h, x + 60, 720, 8, CRIMSON if k == 1 else lerpc(CRIMSON, GREY, .5), a * s1 * 0.7, 2)
        f.text('1', CX - 80, 470, 40, 'orb', CRIMSON, a * s1 * 0.8, mode='O')
        hx, hy = CX + 300, 560
        f.fillpoly(hexagon(hx, hy, 90, math.pi / 6), BGOLD, a * s1 * 0.18)
        f.poly(hexagon(hx, hy, 90, math.pi / 6), BGOLD, a * s1, 3, closed=True)
        f.glow((hx, hy), 110, BGOLD, a * s1 * 0.3 * (1 + beat_pulse(t)), 'B')
        f.text('最合适', hx, hy, 34, 'sans_black', BGOLD_L, a * s1, mode='O')
    s2 = env(t, b(43, 2), b(49, 2), 0.4, 0.3)
    if s2 > 0:
        for i, (lab, col, tt) in enumerate((('需求够大', CYAN, b(45)), ('交付更好/更省', VIOLET, b(46, 2)), ('对手难进', AMBER, b(48)))):
            v = eo((t - tt) / 0.6)
            meter_v(f, CX - 300 + i * 300, 330, 900, 0.15 + 0.75 * v, col, a * s2, lab, 30)
            if v > 0.95:
                f.text('✓', CX - 300 + i * 300, 280, 44, 'sans_black', col, a * s2, mode='O', glow=0.4)


def sc_case(f, t):
    if not (b(49, 2) - 0.1 < t < b(57) + 0.1): return
    a = env(t, b(49, 2), b(57) - 0.2, 0.35, 0.2)
    f.rrect(CX - 330, 200, CX + 330, 256, 12, AMBER, a, 2)
    f.text('假设情景 · 教学用，不是真实公司', CX, 228, 30, 'sans_black', AMBER, a, mode='O')
    icon_factory(f, 300, 560, 150, lerpc(CYAN, WHITE, .2), a * eo((t - b(51)) / 0.5), t, stopped=t < b(54, 3))
    f.text('停线的工厂', 300, 720, 30, 'sans_med', CYAN, a * eo((t - b(53)) / 0.4), mode='O')
    bx, by = 780, 560
    pb = eo((t - b(51, 1)) / 0.5) * a
    f.rrect(bx - 110, by - 80, bx + 110, by + 80, 14, BGOLD, pb, 3)
    for k in range(3):
        f.line((bx - 110, by - 80 + 40 * (k + 1)), (bx + 110, by - 80 + 40 * (k + 1)), BGOLD, pb * 0.5, 1)
    f.text('急用零件', bx, by + 120, 30, 'sans_med', BGOLD, pb, mode='O')
    if t > b(54, 2):   # 24 小时送达
        u = cl((t - b(54, 2)) / (BAR * 0.6))
        px = bx - 120 - (bx - 120 - 460) * eio(u)
        f.line((bx - 120, by), (460, by), BGOLD, a * 0.4, 2)
        f.rrect(px - 26, by - 20, px + 26, by + 20, 6, BGOLD_L, a, 2)
        f.glow((px, by), 30, BGOLD, a * 0.5, 'B')
        f.circle((CX, 860), 70, BGOLD, a * eo((t - b(54, 2)) / 0.4), 3)
        q = -math.pi / 2 + 2 * math.pi * cl((t - b(54, 2)) / BAR)
        f.line((CX, 860), (CX + 55 * math.cos(q), 860 + 55 * math.sin(q)), BGOLD_L, a, 3)
        f.text('24h', CX, 970, 40, 'orb', BGOLD, a * eo((t - b(54, 2)) / 0.4), mode='O')
    if t > b(56) - 0.1:
        p = eo((t - b(56) + 0.1) / 0.3) * a
        chip(f, '大单价格战', CX, 1080 - 20, 40, CRIMSON, p, 'sans_black', 0.12)
        w2 = text_width('大单价格战', 'sans_black', 40) / 2 + 40
        f.line((CX - w2, 1060), (CX + w2, 1060), CRIMSON, p, 4)


def sc_limits(f, t):
    if not (b(57) - 0.1 < t < b(67) + 0.2): return
    a = env(t, b(57), b(67), 0.5, 0.3)
    burst(f, t, b(57), CX, 700, [BLUE, CYAN, WHITE, VIOLET, BLUE, BGOLD], 2, 500, 900, 1.6)
    s1 = env(t, b(57), b(61) + 0.2, 0.4, 0.35)
    if s1 > 0:   # ① 很独特，但需求太小
        hx, hy = 380, 600
        f.fillpoly(hexagon(hx, hy, 120, math.pi / 6), BGOLD, a * s1 * 0.15)
        f.poly(hexagon(hx, hy, 120, math.pi / 6), BGOLD, a * s1, 3, closed=True)
        f.text('很独特', hx, hy, 36, 'sans_black', BGOLD_L, a * s1, mode='O')
        meter_v(f, 760, 360, 860, 0.08 + 0.03 * math.sin(t * 3), CRIMSON, a * s1 * eo((t - b(58, 2)) / 0.5), '需求', 30)
        f.text('利润？', 760, 300, 40, 'sans_black', CRIMSON, a * s1 * eo((t - b(59, 2)) / 0.5), mode='O')
    s2 = env(t, b(61), b(67), 0.4, 0.3)
    if s2 > 0:   # ② 基本生态位 vs 实际生态位
        cx, cy, R = 470, 620, 300
        ts = np.linspace(0, 2 * math.pi, 120)
        for k in range(0, 120, 4):
            f.line((cx + R * math.cos(ts[k]), cy + R * math.sin(ts[k])), (cx + R * math.cos(ts[k + 2]), cy + R * math.sin(ts[k + 2])), TEAL, a * s2, 2)
        f.text('基本生态位', cx - 40, cy - R - 40, 32, 'sans_black', TEAL, a * s2, mode='O')
        u = eio((t - b(62)) / (BAR * 2))
        rx = 1180 - 330 * u
        f.circle((rx, cy + 40), 260, CRIMSON, a * s2 * eo((t - b(62)) / 0.5), 3)
        f.text('对手', rx + 60, cy + 40, 34, 'sans_black', CRIMSON, a * s2 * eo((t - b(62)) / 0.5), mode='O')
        yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32) * 4
        m = (((xx - cx) ** 2 + (yy - cy) ** 2) < (R * 0.92) ** 2) & (((xx - rx) ** 2 + (yy - cy - 40) ** 2) > 260 ** 2)
        mm = cv2.resize(cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.0), (W, H), interpolation=cv2.INTER_LINEAR)
        f.L += mm[..., None] * np.array(BGOLD, np.float32) * (0.22 * a * s2)
        f.text('实际生态位', cx - 120, cy + 20, 32, 'sans_black', BGOLD_L, a * s2 * eo((t - b(61, 2)) / 0.5), mode='O')


def sc_q2(f, t):
    if not (b(67) - 0.1 < t < b(69) + 0.1): return
    implode(f, t, b(67), b(69), CX, 900, [TEAL, CYAN, BGOLD, WHITE, BGOLD_L, AMBER], 1.0, R0=1100)


OPTIONS = ['全品类', '最低价', '所有客户', '大单', '定制', '全国铺开', '最快', '最全']


def sc_porter(f, t):
    if not (b(69) - 0.1 < t < b(71, 2) + 0.2): return
    a = env(t, b(69), b(71, 2), 0.15, 0.3)
    burst(f, t, b(69), CX, 500, [TEAL, BGOLD, CYAN, WHITE, BGOLD_L, GREEN], 4, 900, 1900, 1.6)
    for i, s_ in enumerate(OPTIONS):
        x = CX + (i % 4 - 1.5) * 230; y = 380 + (i // 4) * 140
        keep = (i == 6)
        cross = eo((t - b(69, 2) - i * 0.12) / 0.3)
        col = BGOLD if keep else lerpc(GREY, CRIMSON, .2)
        chip(f, s_, x, y, 34, col, a * (1.0 if keep else 1 - 0.6 * cross), 'sans_black', 0.12)
        if not keep and cross > 0:
            w2 = text_width(s_, 'sans_black', 34) / 2 + 26
            f.line((x - w2, y), (x - w2 + 2 * w2 * cross, y), CRIMSON, a * 0.8, 3)
        if keep:
            f.glow((x, y), 80, BGOLD, a * 0.3 * cross * (1 + beat_pulse(t)), 'B')


def sc_tradeoff(f, t):
    if not (b(71, 2) - 0.1 < t < b(75, 2) + 0.2): return
    a = env(t, b(71, 2), b(75, 2), 0.35, 0.3)
    L, R_ = (220, 560), (860, 560)
    for (p, lab, col) in ((L, '便宜', CYAN), (R_, '近和快', BGOLD)):
        f.circle(p, 80, col, a, 3); f.circle(p, 40, col, a * 0.5, 2)
        f.text(lab, p[0], p[1] + 120, 34, 'sans_black', col, a, mode='O')
    dim = eo((t - b(73, 2)) / 0.6)
    x = CX + math.sin(t * 6) * 220
    comet(f, x, 560, 18, lerpc(WHITE, GREY, dim), a * (1 - 0.5 * dim))
    f.text('两头都要', CX, 470, 30, 'sans_med', lerpc(WHITE, GREY, dim), a, mode='O')
    if t > b(73, 2):
        f.text('两头都不精', CX, 660, 30, 'sans_black', CRIMSON, a * dim, mode='O')
        comet(f, R_[0], R_[1], 22, BGOLD, a * dim)
        f.glow(R_, 120, BGOLD, a * dim * 0.3, 'B')


def sc_shop(f, t):
    if not (b(75, 2) - 0.1 < t < b(79, 2) + 0.2): return
    a = env(t, b(75, 2), b(79, 2), 0.35, 0.3)
    f.text('示意', CX + 400, 220, 26, 'sans_light', GREY, a, mode='O')
    f.rrect(110, 250, 430, 450, 16, lerpc(GREY, CYAN, .3), a * 0.5, 2)
    f.text('大超市', 270, 320, 34, 'sans_black', lerpc(GREY, CYAN, .3), a * 0.7, mode='O')
    f.text('品类 · 价格', 270, 380, 26, 'sans_light', GREY, a * 0.7, mode='O')
    sx, sy = 640, 700
    icon_shop(f, sx, sy, 110, BGOLD, a)
    f.text('社区小店', sx, sy + 150, 34, 'sans_black', BGOLD, a, mode='O')
    for k in range(3):   # 步行 5 分钟半径
        r = 200 + k * 60 + 10 * math.sin(t * 2 + k)
        f.circle((sx, sy + 20), r, BGOLD, a * (0.5 - k * 0.12) * eo((t - b(77, 2)) / 0.6), 2)
    if t > b(77, 2):
        f.text('下楼 5 分钟', sx, sy - 260, 40, 'sans_black', BGOLD_L, a * eo((t - b(77, 2)) / 0.5), mode='O', glow=0.4)
    for i in range(10):
        q = i / 10 * 2 * math.pi + 0.3
        bxx, byy = sx + 290 * math.cos(q), sy + 20 + 260 * math.sin(q)
        f.rrect(bxx - 22, byy - 30, bxx + 22, byy + 30, 4, lerpc(TEAL, GREY, .4), a * 0.6, 1)


def sc_card(f, t):
    if not (b(79, 2) - 0.1 < t < b(85) + 0.2): return
    a = env(t, b(79, 2), b(85), 0.35, 0.3)
    x0, x1, y0, y1 = 130, 950, 250, 1020
    f.rrect_fill(x0, y0, x1, y1, 30, BGOLD, a * 0.05)
    f.rrect(x0, y0, x1, y1, 30, BGOLD, a, 3)
    f.text('生态位卡片', CX, y0 + 70, 46, 'serif_black', BGOLD, a, mode='O', glow=0.4)
    for i, (q, col) in enumerate(QUESTIONS):
        y = y0 + 210 + i * 210
        p = eo((t - b(80) - i * BEAT) / 0.4) * a
        f.text(q, x0 + 60, y, 40, 'sans_black', col, p, 'l', mode='O')
        fill = eo((t - b(80, 2) - i * BEAT) / 0.8)
        f.line((x0 + 60, y + 60), (x0 + 60 + (x1 - x0 - 200) * fill, y + 60), lerpc(col, WHITE, .2), p * 0.8, 3)
        ok = eo((t - b(82) - i * BEAT) / 0.4)
        if ok > 0:
            f.circle((x1 - 80, y + 20), 30, TEAL, a * ok, 3)
            f.poly([(x1 - 94, y + 20), (x1 - 82, y + 34), (x1 - 62, y + 4)], TEAL, a * ok, 3)
    f.text('能用事实验证', x1 - 80, y1 - 40, 22, 'sans_light', TEAL, a * eo((t - b(82, 2)) / 0.5), 'r', mode='O')


# ---- 终章：满屏的小生态位（片尾粒子从这些六边形出发）
HEX = []
for r_ in range(5):          # 只铺在上半屏，下方留给大字问题
    for c_ in range(7):
        hx_ = 120 + c_ * 140 + (70 if r_ % 2 else 0); hy_ = 270 + r_ * 100
        if hx_ < 1000: HEX.append((hx_, hy_))
HEX = np.array(HEX)
_HO = np.random.default_rng(8).permutation(len(HEX))


def sc_outro(f, t):
    if not (b(85) - 0.1 < t < T_GATHER0 + 0.1): return
    a = env(t, b(85), T_GATHER0, 0.5, 0.05)
    n_on = int(len(HEX) * cl((t - b(85)) / (BAR * 5)))
    ph = ((t - b(85)) / BAR) % 1.0              # 每小节从中心荡开一圈
    for k, (hx, hy) in enumerate(HEX):
        on = _HO[k] < n_on
        d = math.hypot(hx - CX, hy - 470) / 650
        rip = math.exp(-((ph - d * 0.6) / 0.06) ** 2)
        col = BGOLD if on else lerpc(GREY, TEAL, .3)
        f.poly(hexagon(hx, hy, 52 + 6 * rip, math.pi / 6), lerpc(col, WHITE, 0.5 * rip), a * min(1, (0.85 if on else 0.25) + rip * 0.6), 2, closed=True)
        if on:
            f.fillpoly(hexagon(hx, hy, 46, math.pi / 6), BGOLD, a * (0.05 + 0.12 * rip))
            f.glow((hx, hy), 10 + 14 * rip, BGOLD_L, a * (0.6 + 0.6 * rip), 'E')




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
# 画面元素汇聚：粒子的起点取自终章那棵生命之树的枝干
# 画面元素汇聚：粒子的起点取自终章满屏六边形的边
_hi = _er.integers(0, len(HEX), 5200); _hk = _er.integers(0, 6, 5200); _hu = _er.uniform(0, 1, 5200)
_q0 = math.pi / 6 + _hk * math.pi / 3; _q1 = _q0 + math.pi / 3
LP_SX = HEX[_hi, 0] + 52 * (np.cos(_q0) * (1 - _hu) + np.cos(_q1) * _hu)
LP_SY = HEX[_hi, 1] + 52 * (np.sin(_q0) * (1 - _hu) + np.sin(_q1) * _hu)
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
SCENES = [sc_hook, sc_title, sc_promise, sc_card1, sc_forest, sc_card2, sc_venn, sc_fit, sc_case, sc_limits, sc_q2,
          sc_porter, sc_tradeoff, sc_shop, sc_card, sc_outro, sc_end]


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
