"""M06《大家都加码，为什么可能谁也没多赚？》—— 军备竞赛 · 竖屏 3 分 05 秒动态视觉短片（1080×1920）

纯字幕叙事（无人声）、大字号，适合手机竖屏观看。画面切换、字幕出入都落在拍点上（1 拍 = 14 帧，128.57 BPM）。
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
    (0, (90, 35, 10), (10, 50, 80), .75), (b(4) - .05, (90, 35, 10), (10, 50, 80), .6),
    (b(4), (200, 100, 30), (30, 140, 190), 1.4), (b(5), (120, 70, 25), (25, 90, 130), 1.0),
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
CHAPTERS = [(0, '序', '序章', 'PROLOGUE'), (b(9), '01', '矛与盾', 'SPEAR & SHIELD'),
            (b(25), '02', '加码的账，怎么算', 'DO THE MATH'), (b(41), '03', '大家都加，谁多赚了？', 'WHO GAINS?'),
            (b(57), '·', '三个提醒', 'THREE CAVEATS'), (b(69), '04', '先问：饼变大了吗', 'BIGGER PIE, OR SHIFTED SHARE?'),
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


def curved_arrow(f, p0, pm, p2, col, a, prog=1.0, th=3):
    s = np.linspace(0, cl(prog), 30)[:, None]
    pts = (1 - s) ** 2 * np.array(p0) + 2 * (1 - s) * s * np.array(pm) + s ** 2 * np.array(p2)
    if len(pts) < 2 or prog <= 0.02: return
    f.poly(pts, col, a, th)
    arrow(f, tuple(pts[-4]), tuple(pts[-1]), col, a, th, 14)
    f.glow(tuple(pts[-1]), 8, lerpc(col, WHITE, .5), a, 'E')


# ---- 配色：A / 防御 = 青，B / 攻击 = 橙；三本账：利润 = 琥珀，消费者 = 青绿，总需求 = 紫；结论 = 品牌金
CA, CB = CYAN, ORANGE
LEDGER = [('企业利润', AMBER), ('消费者收益', TEAL), ('总需求', VIOLET)]
CHECK = [('企业利润', '追加投入后，利润率变了吗？', AMBER), ('消费者收益', '用户多得到了什么？', TEAL),
         ('总需求', '市场有没有变大？', VIOLET), ('会不会停', '成本上限在哪？方向会变吗？', CYAN)]


def tower(f, x, yb, n, col, a, w=110, bh=30, gap=6):
    """堆叠的投入块：n 可以是小数（最上面那块正在落下）"""
    if a <= 0.003: return yb
    full = int(n); fr = n - full
    for k in range(full + (1 if fr > 0.01 else 0)):
        y1 = yb - k * (bh + gap)
        drop = 0 if k < full else (1 - eo(fr)) * 120
        al = a * (1 if k < full else eo(fr))
        f.rrect(x - w / 2, y1 - bh - drop, x + w / 2, y1 - drop, 6, col, al, 2)
        f.rrect_fill(x - w / 2, y1 - bh - drop, x + w / 2, y1 - drop, 6, col, al * 0.2)
    top = yb - n * (bh + gap)
    f.glow((x, top), 40, col, a * 0.3 * (1 + beat_pulse(f.t)), 'B')
    return top


def alt_levels(t, t0, nmax=99):
    """从 t0 开始每拍一步，A、B 交替加一块"""
    if t < t0: return 0.0, 0.0
    x = (t - t0) / BEAT
    k = int(x); fr = eio((x - k) / 0.5)
    na = (k + 1) // 2 + (fr if k % 2 == 0 else 0)
    nb = k // 2 + (fr if k % 2 == 1 else 0)
    return min(na, nmax), min(nb, nmax)


def book(f, cx, cy, s, col, a, label, size=30, hl=0.0):
    if a <= 0.003: return
    f.rrect(cx - s * 0.75, cy - s, cx + s * 0.75, cy + s, 10, col, a, 3 if hl > 0.5 else 2)
    f.rrect_fill(cx - s * 0.75, cy - s, cx + s * 0.75, cy + s, 10, col, a * (0.06 + 0.14 * hl))
    f.line((cx - s * 0.52, cy - s), (cx - s * 0.52, cy + s), col, a * 0.8, 2)
    for k in range(3):
        f.line((cx - s * 0.3, cy - s * 0.45 + k * s * 0.35), (cx + s * 0.55, cy - s * 0.45 + k * s * 0.35), col, a * 0.5, 2)
    if hl > 0:
        f.glow((cx, cy), s * 1.3, col, a * 0.3 * hl * (1 + beat_pulse(f.t)), 'B')
        spin_ring(f, cx, cy, s * 1.45, f.t, col, a * 0.45 * hl, 20, 0.6)
    f.text(label, cx, cy + s + 42, size, 'sans_black', lerpc(col, WHITE, .2), a, mode='O', glow=0.3 * hl)


def phone(f, cx, cy, col, a, nf, t):
    """手机：功能越加越多（摄像头 / 芯片 / 屏幕光）"""
    if a <= 0.003: return
    w, h = 170, 300
    f.rrect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, 28, col, a, 3)
    f.rrect_fill(cx - w / 2 + 10, cy - h / 2 + 10, cx + w / 2 - 10, cy + h / 2 - 10, 20, col, a * 0.06)
    f.line((cx - 24, cy - h / 2 + 18), (cx + 24, cy - h / 2 + 18), col, a * 0.7, 3)
    n = int(nf); fr = nf - n
    for k in range(n + (1 if fr > 0.01 else 0)):
        al = a * (1 if k < n else eo(fr))
        r, c = k // 2, k % 2
        x = cx - 38 + c * 76; y = cy - 90 + r * 62
        if k % 3 == 2:   # 芯片
            f.rrect(x - 22, y - 22, x + 22, y + 22, 4, lerpc(col, WHITE, .3), al, 2)
            for j in (-1, 0, 1): f.line((x + j * 10, y - 30), (x + j * 10, y - 22), col, al, 2)
        else:            # 摄像头
            f.circle((x, y), 22, lerpc(col, WHITE, .3), al, 2); f.circle((x, y), 9, col, al, 2)
        f.glow((x, y), 26, col, al * 0.3 * (1 if k < n else 1 + 2 * (1 - fr)), 'B')


def ledger_bar(f, x, yb, v, col, a, label, arrow_dir=0):
    """三本账的竖条：v ∈ [0,1]；arrow_dir 1 上 / -1 下 / 0 持平"""
    if a <= 0.003: return
    hmax = 230
    f.rrect(x - 40, yb - hmax, x + 40, yb, 12, lerpc(col, GREY, .4), a * 0.7, 2)
    hh = hmax * cl(v)
    f.rrect_fill(x - 34, yb - 6 - hh + 6, x + 34, yb - 6, 10, col, a * 0.7)
    f.glow((x, yb - hh), 26, col, a * 0.6, 'B')
    f.text(label, x, yb + 36, 28, 'sans_black', col, a, mode='O')
    ay = yb - hmax - 40
    if arrow_dir > 0: arrow(f, (x, ay + 20), (x, ay - 20), col, a, 4, 14)
    elif arrow_dir < 0: arrow(f, (x, ay - 20), (x, ay + 20), col, a, 4, 14)
    else: arrow(f, (x - 24, ay), (x + 24, ay), col, a, 4, 14)


def pie(f, cx, cy, r, frac_a, a, rot=-math.pi / 2):
    """A（青）/ B（橙）两块的饼"""
    if a <= 0.003: return
    qa = rot + 2 * math.pi * frac_a
    for (q0, q1, col) in ((rot, qa, CA), (qa, rot + 2 * math.pi, CB)):
        qs = np.linspace(q0, q1, max(3, int(48 * (q1 - q0) / math.pi)))
        pts = [(cx, cy)] + [(cx + r * math.cos(q), cy + r * math.sin(q)) for q in qs]
        f.fillpoly(pts, col, a * 0.22)
        f.poly(pts, col, a, 3, closed=True)
    f.glow((cx, cy), r * 0.9, BGOLD, a * 0.12, 'B')


# ================================================================ 场景
def sc_hook(f, t):
    if t > b(4) + 0.3: return
    a = env(t, 0, b(4), 0.3, 0.25)
    na, nb = alt_levels(t, 0.3, 8)
    ta = tower(f, 380, 640, na, CA, a, 120, 32, 6)
    tb = tower(f, 700, 640, nb, CB, a, 120, 32, 6)
    f.text('A', 380, 680, 30, 'orb', CA, a, mode='O'); f.text('B', 700, 680, 30, 'orb', CB, a, mode='O')
    if na > 0.5 and nb > 0.5:   # 差距：两塔顶部的连线几乎不动
        f.line((380 + 60, ta), (700 - 60, tb), BGOLD, a * 0.7, 2)
        f.text('差距', CX, min(ta, tb) - 40, 26, 'sans_black', BGOLD, a * 0.9, mode='O')
    n = np.arange(60)   # 花出去的钱：从塔底往外飘散
    u = (t * 0.6 + n / 60) % 1.0
    sd = np.where(n % 2 == 0, -1, 1)
    xs = np.where(n % 2 == 0, 380, 700) + sd * (40 + 260 * u) * (0.6 + 0.4 * np.sin(n))
    ys = 640 - 40 * np.sin(u * math.pi) * (0.5 + (n % 5) / 5) + 30 * u
    f.splat(xs, ys, BGOLD, a * (1 - u) * 1.4 * cl(t / 1.0), 'E')
    implode(f, t, b(3), b(4), CX, 900, [BGOLD, CA, CB, WHITE, BGOLD_L, AMBER], 0.8)


def sc_title(f, t):
    if not (b(4) - 0.1 < t < b(7) + 0.5): return
    a = env(t, b(4), b(7) - 0.05, 0.25, 0.4)
    burst(f, t, b(4), CX, 860, [CA, CB, BGOLD, BGOLD_L, WHITE, AMBER], 0, 800, 1800, 1.5)
    pr = eo((t - b(4)) / 1.6)   # 攻防交替上升的折线
    pts = [((260 if k % 2 == 0 else 820), 1320 - k * 90) for k in range(12)]
    m = pr * (len(pts) - 1)
    for k in range(int(m)):
        f.line(pts[k], pts[k + 1], CA if k % 2 == 0 else CB, a * 0.45, 3)
        f.glow(pts[k + 1], 10, CA if k % 2 == 0 else CB, a * 0.6, 'E')
    t0 = b(4)
    rich_line(f, '军备竞赛 · EVOLUTIONARY ARMS RACE', CX, 560, 30, 'sans_med', BGOLD, a=a, t0=t0 + 0.1, stag=0.02, track=0.08, underline=False)
    rich_line(f, '大家都加码，', CX, 700, 100, 'serif_black', TXT, a=a, t0=t0 + 0.2, stag=0.05)
    rich_line(f, '为什么可能', CX, 830, 100, 'serif_black', TXT, a=a, t0=t0 + 0.5, stag=0.05)
    rich_line(f, '{谁也没多赚}？', CX, 960, 100, 'serif_black', TXT, a=a, t0=t0 + 0.8, stag=0.05, glow_hl=0.6)
    rich_line(f, '《50个自然法则，看懂商业世界》M06', CX, 1110, 36, 'sans_med', lerpc(BSUB, WHITE, .3), a=a, t0=t0 + 1.3, stag=0.015, underline=False)
    rich_line(f, '50 个来自自然、数学与复杂系统的思维模型', CX, 1168, 28, 'sans_light', lerpc(GREY, WHITE, .3), a=a, t0=t0 + 1.6, stag=0.01, underline=False)


def sc_promise(f, t):
    if not (b(7) - 0.1 < t < b(9)): return
    a = env(t, b(7), b(9), 0.4, 0.3)
    for i, (lab, col) in enumerate(LEDGER):
        book(f, 250 + i * 290, 700, 90, col, a * eo((t - b(7, 1) - i * BEAT * 0.5) / 0.4), lab, 30, 1.0)


def sc_card1(f, t):
    if not (b(9) - 0.1 < t < b(10) + 0.1): return
    mirror_card(f, t, b(9), b(10), '01', '矛与盾', 'SPEAR & SHIELD', CB)


T_ATK = [b(11, 2), b(15, 2), b(19, 2)] + [b(21, 2) + k * BEAT for k in (0, 2, 4, 6)]
T_DEF = [b(13, 2), b(17, 2)] + [b(21, 2) + k * BEAT for k in (1, 3, 5, 7)]


def lvl(t, ts):
    return sum(eio((t - x) / 0.5) for x in ts)


def chase_phase(t):
    return 0.7 * t + 0.10 * sum(max(0.0, t - x) for x in T_ATK + T_DEF)


def sc_spear(f, t):
    if not (b(10) - 0.1 < t < b(25) + 0.1): return
    a = env(t, b(10), b(25), 0.4, 0.35)
    f.text('模型示意 · 不代表动物有意识地制定策略', CX, 228, 26, 'sans_light', lerpc(GREY, WHITE, .3), a, mode='O')
    cx, cy, rx, ry = CX, 470, 330, 150
    f.poly([(cx + rx * math.cos(q), cy + ry * math.sin(q)) for q in np.linspace(0, 2 * math.pi, 80)], lerpc(GREY, VIOLET, .3), a * 0.3, 1, closed=True)
    ph = chase_phase(t)
    la, ld = lvl(t, T_ATK), lvl(t, T_DEF)
    for k in range(10):   # 拖尾
        dt = k * 0.05
        q = chase_phase(t - dt)
        f.glow((cx + rx * math.cos(q), cy + ry * math.sin(q)), 6, CA, a * (1 - k / 10) * 0.8, 'E')
        q2 = q - 0.75
        f.glow((cx + rx * math.cos(q2), cy + ry * math.sin(q2)), 6, CB, a * (1 - k / 10) * 0.8, 'E')
    px, py = cx + rx * math.cos(ph), cy + ry * math.sin(ph)
    qx, qy = cx + rx * math.cos(ph - 0.75), cy + ry * math.sin(ph - 0.75)
    f.circle((px, py), 24, CA, a, 3)   # 猎物：带“盾”的圆
    tg = math.atan2(ry * math.cos(ph), -rx * math.sin(ph))
    f.arc((px, py), 36 + 3 * ld, tg + math.pi - 0.9, tg + math.pi + 0.9, CA, a, 3 + int(ld > 2), 16)
    comet(f, px, py, 12, CA, a)
    tq = math.atan2(ry * math.cos(ph - 0.75), -rx * math.sin(ph - 0.75))   # 捕食者：朝前的三角“矛”
    s = 30 + 3 * la
    f.poly([(qx + s * math.cos(tq), qy + s * math.sin(tq)), (qx + s * 0.6 * math.cos(tq + 2.5), qy + s * 0.6 * math.sin(tq + 2.5)),
            (qx + s * 0.6 * math.cos(tq - 2.5), qy + s * 0.6 * math.sin(tq - 2.5))], CB, a, 3, closed=True)
    comet(f, qx, qy, 12, CB, a)
    f.text('捕食者', qx, qy - 56, 26, 'sans_black', CB, a * eo((t - b(10, 2)) / 0.5), mode='O')
    f.text('猎物', px, py - 56, 26, 'sans_black', CA, a * eo((t - b(10, 2)) / 0.5), mode='O')
    pr = env(t, b(15, 2), b(19, 2) + 0.3, 0.3, 0.4)   # 选择压力：互相推着走
    if pr > 0:
        curved_arrow(f, (qx, qy + 30), ((qx + px) / 2, cy + 230), (px, py + 30), BGOLD, a * pr, 1.0, 3)
        f.text('选择压力', CX, cy + 250, 28, 'sans_black', BGOLD, a * pr, mode='O')
    sa = a * eo((t - b(11, 2) + 0.3) / 0.6)   # 攻防等级：交替上台阶
    x0, x1, y0, y1 = 160, 920, 820, 1110
    f.line((x0, y1), (x1, y1), GREY, sa * 0.6, 2)
    f.text('攻防等级（模型）', x0, y0 - 30, 24, 'sans_black', WHITE, sa, 'l', mode='O')
    f.text('时间 →', x1, y1 + 30, 22, 'sans_light', GREY, sa, 'r', mode='O')
    T0, T1 = b(10), b(25)
    for (ts, col, lab, off) in ((T_ATK, CB, '攻击', 0), (T_DEF, CA, '防御', 6)):
        pts = [(x0, y1 - 20 - off)]
        for x_ in sorted(ts):
            if x_ > t: break
            xx = x0 + (x1 - x0) * (x_ - T0) / (T1 - T0)
            pts.append((xx, pts[-1][1])); pts.append((xx, y1 - 20 - off - 32 * lvl(min(t, x_ + 0.5), [y for y in ts if y <= x_])))
        xe = x0 + (x1 - x0) * cl((t - T0) / (T1 - T0))
        pts.append((max(xe, pts[-1][0]), pts[-1][1]))
        f.poly(pts, col, sa, 3)
        f.glow(pts[-1], 8, lerpc(col, WHITE, .5), sa, 'E')
        f.text(lab, pts[-1][0] + 12, pts[-1][1] - (16 if col == CB else -16), 22, 'sans_black', col, sa, 'l', mode='O')
    ga = a * env(t, b(23, 2), b(25), 0.3, 0.3)
    if ga > 0:
        f.text('相对差距：没拉开', x1, y0 - 30, 26, 'sans_black', BGOLD, ga, 'r', mode='O', glow=0.3)


def sc_card2(f, t):
    if not (b(25) - 0.1 < t < b(26) + 0.1): return
    mirror_card(f, t, b(25), b(26), '02', '加码的账，怎么算', 'DO THE MATH', AMBER)


def sc_ledger(f, t):
    if not (b(26) - 0.1 < t < b(41) + 0.1): return
    a = env(t, b(26), b(41) - 0.2, 0.35, 0.2)
    ba = a * env(t, b(26, 2), b(33, 2) + 0.2, 0.4, 0.4)
    if ba > 0:   # 双方投入交替加码；相对位置几乎不动
        na, nb = alt_levels(t, b(27, 2), 9)
        tower(f, 380, 900, na, CA, ba, 130, 34, 6)
        tower(f, 700, 900, nb, CB, ba, 130, 34, 6)
        f.text('A 的投入', 380, 945, 28, 'sans_black', CA, ba, mode='O'); f.text('B 的投入', 700, 945, 28, 'sans_black', CB, ba, mode='O')
        s = 0.5 + 0.04 * math.sin(t * 2.3) * eo((t - b(29, 2)) / 0.5)
        x0, x1, y = 200, 880, 300
        f.text('相对位置', CX, y - 50, 26, 'sans_black', BGOLD, ba * eo((t - b(29, 2)) / 0.5), mode='O')
        f.rrect_fill(x0, y - 18, x0 + (x1 - x0) * s, y + 18, 9, CA, ba * 0.6)
        f.rrect_fill(x0 + (x1 - x0) * s, y - 18, x1, y + 18, 9, CB, ba * 0.6)
        f.rrect(x0, y - 18, x1, y + 18, 9, GREY, ba, 2)
        q = ba * eo((t - b(31, 2)) / 0.5)
        if q > 0:
            n = np.arange(80); u = (t * 0.5 + n / 80) % 1.0
            sx = np.where(n % 2 == 0, 380, 700); tx, ty = CX, 520
            f.splat(sx + (tx - sx) * u, 600 + (ty - 600) * u - 80 * np.sin(u * math.pi), BGOLD, q * 1.5 * (1 - u * 0.5), 'E')
            f.text('?', CX, 500, 110, 'serif_black', BGOLD_L, q, mode='O', glow=0.5)
    la = a * eo((t - b(33, 2)) / 0.5)
    if la > 0:   # 三本账
        tt = [b(35, 2), b(37), b(38, 2)]
        for i, (lab, col) in enumerate(LEDGER):
            hl = env(t, tt[i], tt[i] + BAR * 1.5, 0.2, 0.3) + 0.6 * env(t, b(40), b(41), 0.15, 0.1)
            book(f, 250 + i * 290, 620, 100, col, la * eo((t - b(33, 2) - i * BEAT * 0.5) / 0.4), lab, 32, min(hl, 1.0))
            if t > b(40) - 0.1:   # 三本账，常常不同
                d = [-1, 1, 0][i]; p = la * eo((t - b(40)) / 0.3)
                x, y = 250 + i * 290, 440
                if d > 0: arrow(f, (x, y + 30), (x, y - 30), col, p, 5, 16)
                elif d < 0: arrow(f, (x, y - 30), (x, y + 30), col, p, 5, 16)
                else: arrow(f, (x - 34, y), (x + 34, y), col, p, 5, 16)
    implode(f, t, b(39, 2), b(41), CX, 700, [BGOLD, CA, CB, WHITE, BGOLD_L, AMBER], 0.7, R0=1100)


T_FEAT_A = [b(46, 2), b(48, 2)] + [b(49, 2) + k * BEAT for k in (0, 2, 4, 6)]
T_FEAT_B = [b(47), b(48)] + [b(49, 2) + k * BEAT for k in (1, 3, 5, 7)]


def sc_phones(f, t):
    if not (b(41) - 0.1 < t < b(57) + 0.1): return
    a = env(t, b(41), b(57) - 0.2, 0.15, 0.2)
    burst(f, t, b(41), CX, 450, [BGOLD, BGOLD_L, CA, CB, WHITE, AMBER], 1, 900, 1900, 1.6)
    ha = a * env(t, b(41), b(43, 2) + 0.2, 0.1, 0.4)
    if ha > 0:   # 塔快速交替加高，份额箭头来回互抢
        na, nb = alt_levels(t, b(41), 12)
        tower(f, 330, 760, na, CA, ha, 140, 30, 5)
        tower(f, 750, 760, nb, CB, ha, 140, 30, 5)
        for k in range(3):
            u = ((t * 1.4 + k / 3) % 1.0)
            arrow(f, (420 + 240 * u, 380 + k * 60), (450 + 240 * u, 380 + k * 60), CRIMSON, ha * (1 - u), 3, 10)
            arrow(f, (660 - 240 * u, 410 + k * 60), (630 - 240 * u, 410 + k * 60), CRIMSON, ha * (1 - u), 3, 10)
        chip(f, '抢份额', CX, 300, 34, CRIMSON, ha, 'sans_black', 0.14)
    la = a * eo((t - b(43, 2)) / 0.5)
    if la <= 0: return
    f.rrect(CX - 330, 200, CX + 330, 256, 12, AMBER, la, 2)
    f.text('假设情景 · 教学用，不是真实公司', CX, 228, 30, 'sans_black', AMBER, la, mode='O')
    pa = la * eo((t - b(45)) / 0.5)
    fa = lvl(t, T_FEAT_A); fb = lvl(t, T_FEAT_B)
    phone(f, 330, 460, CA, pa, fa, t); phone(f, 750, 460, CB, pa, fb, t)
    f.text('手机 A', 330, 640, 28, 'sans_black', CA, pa, mode='O'); f.text('手机 B', 750, 640, 28, 'sans_black', CB, pa, mode='O')
    ra = la * eo((t - b(49, 2)) / 0.5)
    if ra > 0:   # 研发费用一起上涨 + 份额来回拉锯
        for (x, col, nf) in ((140, CA, fa), (940, CB, fb)):
            hh = 30 + 40 * nf
            f.rrect_fill(x - 22, 610 - hh, x + 22, 610, 8, col, ra * 0.6)
            f.rrect(x - 22, 330, x + 22, 610, 8, GREY, ra * 0.6, 2)
            f.text('研发', x, 645, 24, 'sans_black', col, ra, mode='O')
        s = 0.5 + 0.06 * math.sin((fa - fb) * math.pi)
        x0, x1, y = 220, 860, 700
        f.rrect_fill(x0, y - 16, x0 + (x1 - x0) * s, y + 16, 8, CA, ra * 0.6)
        f.rrect_fill(x0 + (x1 - x0) * s, y - 16, x1, y + 16, 8, CB, ra * 0.6)
        f.rrect(x0, y - 16, x1, y + 16, 8, GREY, ra, 2)
        f.text('份额', CX, y + 40, 24, 'sans_black', WHITE, ra, mode='O')
    ma = la * eo((t - b(51, 2)) / 0.5)
    if ma > 0:   # 三本账的指针
        yb = 1090
        vc = 0.35 + 0.5 * eo((t - b(51, 2)) / 1.5)
        vp = 0.6 - 0.35 * eo((t - b(53, 2)) / 1.5) * (t > b(53, 2))
        pd = eo((t - b(53, 2)) / 0.5)
        ledger_bar(f, 540, yb, vc, TEAL, ma, '消费者收益', 1)
        ledger_bar(f, 270, yb, vp, AMBER, ma * (0.4 + 0.6 * pd), '企业利润', -1 if pd > 0.5 else 0)
        ledger_bar(f, 810, yb, 0.45, VIOLET, ma * (0.4 + 0.6 * pd), '总需求', 0)
        fl = a * eo((t - b(55, 2)) / 0.5)
        if fl > 0:   # 多出的价值流向用户
            n = np.arange(50); u = (t * 0.8 + n / 50) % 1.0
            f.splat(270 + 270 * u, yb - 150 - 140 * np.sin(u * math.pi), BGOLD, fl * 1.6 * (1 - u * 0.3), 'E')


def sc_limits(f, t):
    if not (b(57) - 0.1 < t < b(67) + 0.2): return
    a = env(t, b(57), b(67), 0.5, 0.3)
    burst(f, t, b(57), CX, 600, [BLUE, CYAN, WHITE, VIOLET, BLUE, BGOLD], 2, 500, 900, 1.6)
    s1 = env(t, b(57), b(61) + 0.2, 0.4, 0.35)
    if s1 > 0:   # ① 研发不等于浪费：技术与用户都在进步
        u = eo((t - b(58, 2)) / 2.0)
        xs = np.linspace(160, 160 + 760 * max(u, 0.02), 60)
        ys = 760 - 380 * ((xs - 160) / 760) ** 1.6
        f.poly(np.stack([xs, ys], 1), TEAL, a * s1, 4)
        f.glow((xs[-1], ys[-1]), 14, WHITE, a * s1, 'E')
        f.text('技术进步', 200, 360, 30, 'sans_black', TEAL, a * s1, 'l', mode='O')
        for k in range(4):
            p = a * s1 * eo((t - b(59) - k * BEAT * 0.5) / 0.4)
            icon_person(f, 330 + k * 140, 860, 34, TEAL, p)
            f.glow((330 + k * 140, 840), 30, BGOLD, p * 0.3, 'B')
        f.text('用户受益', CX, 950, 28, 'sans_black', BGOLD, a * s1 * eo((t - b(59, 2)) / 0.4), mode='O')
    s2 = env(t, b(61), b(64) + 0.2, 0.4, 0.35)
    if s2 > 0:   # ② 总需求变大：饼变大，双方都多
        r = 150 + 110 * eo((t - b(61, 2)) / 1.6)
        pie(f, CX, 560, r, 0.5, a * s2, -math.pi / 2 + t * 0.2)
        f.text('总需求变大', CX, 300, 32, 'sans_black', VIOLET, a * s2, mode='O')
        f.text('大家都可能多赚', CX, 880, 30, 'sans_black', BGOLD, a * s2 * eo((t - b(62, 2)) / 0.4), mode='O')
    s3 = env(t, b(64), b(67), 0.4, 0.3)
    if s3 > 0:   # ③ 升级会停下：碰到成本上限后转弯
        ceil_y = 380
        f.line((120, ceil_y), (960, ceil_y), CRIMSON, a * s3, 3)
        f.text('成本上限', 960, ceil_y - 30, 28, 'sans_black', CRIMSON, a * s3, 'r', mode='O')
        pr = eo((t - b(64)) / 2.2)
        pts = []
        for k in range(9):
            x = 160 + k * 70; y = 900 - k * 70
            if y < ceil_y + 40: y = ceil_y + 40
            pts.append((x, y))
        pts += [(160 + 9 * 70 + k * 60, ceil_y + 40) for k in range(3)]
        m = pr * (len(pts) - 1)
        for k in range(int(m)):
            f.line(pts[k], pts[k + 1], CA if k % 2 == 0 else CB, a * s3, 3)
        if pr > 0.95:
            arrow(f, pts[-2], (pts[-1][0] + 40, pts[-1][1] + 60), BGOLD, a * s3, 4, 16)
            f.text('转弯', pts[-1][0], pts[-1][1] + 110, 30, 'sans_black', BGOLD, a * s3, mode='O')


def sc_q2(f, t):
    if not (b(67) - 0.1 < t < b(69) + 0.1): return
    implode(f, t, b(67), b(69), CX, 900, [CA, CB, BGOLD, WHITE, BGOLD_L, AMBER], 1.0, R0=1100)


def sc_pie(f, t):
    if not (b(69) - 0.1 < t < b(85) + 0.2): return
    a = env(t, b(69), b(85), 0.15, 0.3)
    burst(f, t, b(69), CX, 480, [CA, BGOLD, CB, WHITE, BGOLD_L, TEAL], 4, 900, 1900, 1.6)
    ba = a * env(t, b(69), b(71, 2) + 0.2, 0.1, 0.4)
    if ba > 0:
        pie(f, CX, 470, 230, 0.5, ba, -math.pi / 2 + t * 0.8)
        spin_ring(f, CX, 470, 270, t, BGOLD, ba * 0.5, 30, 0.6)
    pa = a * env(t, b(71, 2), b(77, 2) + 0.2, 0.3, 0.4)
    if pa > 0:   # 左：饼变大（创造新价值）；右：饼不变，换了手（转移份额）
        chip(f, '创造新价值', 300, 290, 32, BGOLD, pa, 'sans_black', 0.16)
        chip(f, '转移份额', 780, 290, 32, GREY, pa, 'sans_black', 0.12)
        r = 140 + 80 * eo((t - b(73, 2)) / 1.4)
        pie(f, 300, 560, r, 0.5, pa)
        if t > b(73, 2):
            f.text('饼变大', 300, 820, 34, 'sans_black', BGOLD, pa * eo((t - b(73, 2)) / 0.4), mode='O', glow=0.4)
        fa = 0.5 + 0.18 * eo((t - b(75, 2)) / 1.2)
        pie(f, 780, 560, 170, fa, pa)
        if t > b(75, 2):
            f.text('换了手', 780, 820, 34, 'sans_black', lerpc(GREY, WHITE, .3), pa * eo((t - b(75, 2)) / 0.4), mode='O')
            q = -math.pi / 2 + 2 * math.pi * fa
            curved_arrow(f, (780 + 200 * math.cos(q + 0.5), 560 + 200 * math.sin(q + 0.5)), (780 + 215 * math.cos(q + 0.25), 560 + 215 * math.sin(q + 0.25)),
                         (780 + 200 * math.cos(q), 560 + 200 * math.sin(q)), CRIMSON, pa, 1.0, 3)
    ca = a * eo((t - b(77, 2)) / 0.5)
    if ca > 0:   # 检查表
        x0, x1, y0, y1 = 110, 970, 230, 1110
        f.rrect_fill(x0, y0, x1, y1, 30, BGOLD, ca * 0.05)
        f.rrect(x0, y0, x1, y1, 30, BGOLD, ca, 3)
        spin_ring(f, x1 - 10, y0 + 10, 40, t, BGOLD_L, ca * 0.5, 16, 0.6)
        f.text('三本账 · 检查表', CX, y0 + 70, 46, 'serif_black', BGOLD, ca, mode='O', glow=0.4)
        hot = [b(79, 2), b(79, 2), b(79, 2), b(82)]
        for i, (q, sub, col) in enumerate(CHECK):
            y = y0 + 200 + i * 205
            p = eo((t - b(77, 2) - i * BEAT * 0.3) / 0.4) * ca
            hl = env(t, hot[i] + i * BEAT * 0.3, b(85), 0.3, 0.3)
            if hl > 0:
                f.rrect_fill(x0 + 30, y - 70, x1 - 30, y + 80, 18, col, ca * 0.10 * hl)
            f.text(q, x0 + 60, y - 18, 40, 'sans_black', col, p, 'l', mode='O', glow=0.3 * hl)
            f.text(sub, x0 + 60, y + 38, 28, 'sans_light', TXT, p, 'l', mode='O')
            ok = eo((t - hot[i] - i * BEAT * 0.5) / 0.4)
            if ok > 0:
                f.circle((x1 - 90, y + 10), 30, TEAL, ca * ok, 3)
                f.poly([(x1 - 104, y + 10), (x1 - 92, y + 24), (x1 - 72, y - 6)], TEAL, ca * ok, 3)


# ---- 终章：两座投入塔（片尾粒子从塔的方块出发）
OT_X, OT_YB, OT_N, OT_W, OT_BH, OT_G = (360, 720), 650, 9, 130, 30, 6


def sc_outro(f, t):
    if not (b(85) - 0.1 < t < T_GATHER0 + 0.1): return
    a = env(t, b(85), T_GATHER0, 0.5, 0.05)
    tops = []
    for x, col in zip(OT_X, (CA, CB)):
        tops.append(tower(f, x, OT_YB, OT_N, col, a, OT_W, OT_BH, OT_G))
    f.text('A', OT_X[0], OT_YB + 34, 26, 'orb', CA, a, mode='O'); f.text('B', OT_X[1], OT_YB + 34, 26, 'orb', CB, a, mode='O')
    g = env(t, b(87), T_GATHER0, 0.4, 0.2)
    if g > 0:   # 钱去了哪里：两塔的金色光点流向中间的问号
        n = np.arange(70); u = (t * 0.5 + n / 70) % 1.0
        sx = np.where(n % 2 == 0, OT_X[0], OT_X[1]); sy = OT_YB - 30 - (n % 9) * 36
        f.splat(sx + (CX - sx) * u, sy + (300 - sy) * u, BGOLD, a * g * 1.5 * (1 - u * 0.4), 'E')
        f.text('?', CX, 300, 90, 'serif_black', BGOLD_L, a * g, mode='O', glow=0.5)



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
# 画面元素汇聚：粒子的起点取自终章两座投入塔的方块轮廓
_side = np.where(_er.uniform(0, 1, 5200) < 0.5, 0, 1)
_blk = _er.integers(0, OT_N, 5200); _per = _er.uniform(0, 1, 5200)
_bx0 = np.array(OT_X)[_side] - OT_W / 2; _by1 = OT_YB - _blk * (OT_BH + OT_G); _by0 = _by1 - OT_BH
_L = 2 * (OT_W + OT_BH); _d = _per * _L
LP_SX = np.where(_d < OT_W, _bx0 + _d, np.where(_d < OT_W + OT_BH, _bx0 + OT_W, np.where(_d < 2 * OT_W + OT_BH, _bx0 + OT_W - (_d - OT_W - OT_BH), _bx0)))
LP_SY = np.where(_d < OT_W, _by0, np.where(_d < OT_W + OT_BH, _by0 + (_d - OT_W), np.where(_d < 2 * OT_W + OT_BH, _by1, _by1 - (_d - 2 * OT_W - OT_BH))))
_rung = np.zeros(5200, bool)
LP_DL = _er.uniform(0, 0.35, 5200)
LP_MIX = np.where((_side == 0)[:, None], np.array(CA, np.float32), np.array(CB, np.float32)) * 0.75 + np.array(BGOLD, np.float32) * 0.25
T_GATHER0, T_GATHER1 = b(93), b(94, 2)    # 两座投入塔化作粒子，汇聚成 logo
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
SCENES = [sc_hook, sc_title, sc_promise, sc_card1, sc_spear, sc_card2, sc_ledger, sc_phones, sc_limits, sc_q2,
          sc_pie, sc_outro, sc_end]


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
