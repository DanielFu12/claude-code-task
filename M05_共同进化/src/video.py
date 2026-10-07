"""M05《最好的产品，为什么不是一家公司做出来的？》—— 共同进化 · 竖屏 3 分 44 秒动态视觉短片（1080×1920）

纯字幕叙事（无人声）、大字号，适合手机竖屏观看。画面切换、字幕出入都落在拍点上（1 拍 = 17 帧，105.88 BPM）。
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
    (0, (15, 50, 80), (70, 20, 60), .75), (b(4) - .05, (15, 50, 80), (70, 20, 60), .6),
    (b(4), (30, 150, 180), (190, 80, 140), 1.4), (b(5), (25, 100, 130), (110, 50, 100), 1.0),
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
CHAPTERS = [(0, '序', '序章', 'PROLOGUE'), (b(9), '01', '一朵花，一只虫', 'FLOWER & POLLINATOR'),
            (b(25), '02', '双向，才算共同进化', 'IT TAKES TWO WAYS'), (b(41), '03', '最好的产品，是一起改出来的', 'BUILT TOGETHER'),
            (b(57), '·', '三个提醒', 'THREE CAVEATS'), (b(69), '04', '画一条双向时间线', 'A TWO-WAY TIMELINE'),
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


# ---- 配色：平台 = 青，伙伴 = 粉；花 = 品红，传粉昆虫 = 青绿；双向 / 结论 = 品牌金
CP, CQ = CYAN, PINK
CFL, CIN = MAGENTA, TEAL
CHECK = [('双方变化的时间线', '谁先变？谁后变？', CP), ('反向影响的证据', '伙伴改变了平台吗？', BGOLD),
         ('关系类型', '互利，还是对抗？', PINK), ('换个市场', '结果还一样吗？', TEAL)]

# ---- 双螺旋（两条链 = 双方，金色横档 = 互相作用）
HX_K = 2 * math.pi / 430


def helix(f, t, p0, p1, amp, a, speed=1.0, c1=CP, c2=CQ, n=160, pulses=True):
    if a <= 0.003: return
    u = np.linspace(0, 1, n)
    ax = p0[0] + (p1[0] - p0[0]) * u; ay = p0[1] + (p1[1] - p0[1]) * u
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    nx, ny = -(p1[1] - p0[1]) / L, (p1[0] - p0[0]) / L
    q = u * L * HX_K + t * speed
    s1, s2, z = np.sin(q), np.sin(q + math.pi), np.cos(q)
    X1, Y1 = ax + nx * amp * s1, ay + ny * amp * s1
    X2, Y2 = ax + nx * amp * s2, ay + ny * amp * s2
    for k in range(0, n, 10):     # 横档
        al = a * 0.4 * (0.35 + 0.65 * abs(z[k]))
        f.line((X1[k], Y1[k]), (X2[k], Y2[k]), BGOLD, al, 2)
        f.glow((X1[k], Y1[k]), 3, BGOLD_L, al, 'E'); f.glow((X2[k], Y2[k]), 3, BGOLD_L, al, 'E')
    for X, Y, col, zz in ((X1, Y1, c1, z), (X2, Y2, c2, -z)):
        f.poly(np.stack([X, Y], 1), col, a * 0.55, 2)
        f.dots(X[::2], Y[::2], col, a * (0.25 + 0.75 * (0.5 + 0.5 * zz[::2])) * 0.7, 1, 'E')
    if pulses:
        for k in range(3):
            i = int(((t * 0.22 + k / 3) % 1.0) * (n - 1))
            comet(f, X1[i], Y1[i], 10, c1, a * 0.9)
            j = n - 1 - i
            comet(f, X2[j], Y2[j], 10, c2, a * 0.9)
    return X1, Y1, X2, Y2


def watch(f, cx, cy, s, col, a, t):
    f.rrect(cx - s * 0.62, cy - s * 0.72, cx + s * 0.62, cy + s * 0.72, s * 0.22, col, a, 3)
    f.rrect(cx - s * 0.36, cy - s * 1.3, cx + s * 0.36, cy - s * 0.72, s * 0.1, col, a * 0.6, 2)
    f.rrect(cx - s * 0.36, cy + s * 0.72, cx + s * 0.36, cy + s * 1.3, s * 0.1, col, a * 0.6, 2)
    f.line((cx, cy), (cx + s * 0.32 * math.cos(t * 2), cy + s * 0.32 * math.sin(t * 2)), lerpc(col, WHITE, .4), a, 2)
    f.line((cx, cy), (cx + s * 0.22 * math.cos(t * 0.3 - 1), cy + s * 0.22 * math.sin(t * 0.3 - 1)), lerpc(col, WHITE, .4), a, 3)


def flower(f, cx, cy, s, depth, a, t):
    """示意花：花瓣 + 向下的花管（深度 = 花的形状）+ 底部的花蜜"""
    f.line((cx, cy + depth + 10), (cx, cy + s * 3.0), GREEN, a * 0.8, 3)
    for sd in (-1, 1):
        f.arc((cx + sd * s * 0.45, cy + s * 2.2), s * 0.45, math.pi * (1.0 if sd < 0 else 1.5), math.pi * (1.5 if sd < 0 else 2.0), GREEN, a * 0.7, 2, 16)
    f.line((cx - 12, cy), (cx - 7, cy + depth), CFL, a, 2); f.line((cx + 12, cy), (cx + 7, cy + depth), CFL, a, 2)
    f.glow((cx, cy + depth - 4), 10, BGOLD, a * 0.9, 'E'); f.glow((cx, cy + depth - 4), 24, BGOLD, a * 0.3, 'B')
    for k in range(6):
        q = k * math.pi / 3 + 0.15 * math.sin(t * 0.8)
        px, py = cx + s * 0.55 * math.cos(q), cy - s * 0.15 + s * 0.4 * math.sin(q)
        ts = np.linspace(0, 2 * math.pi, 18)
        pts = np.stack([px + s * 0.42 * np.cos(ts) * math.cos(q) - s * 0.2 * np.sin(ts) * math.sin(q),
                        py + s * 0.42 * np.cos(ts) * math.sin(q) * 0.7 + s * 0.2 * np.sin(ts) * math.cos(q)], 1)
        f.poly(pts, lerpc(CFL, PINK, k / 6), a * 0.9, 2, closed=True)
    f.glow((cx, cy - s * 0.1), s * 0.5, CFL, a * 0.25 * (1 + 0.4 * beat_pulse(t)), 'B')


def insect(f, x, y, s, prob, a, t, tip=None):
    """示意传粉昆虫：头胸腹 + 扇动的翅 + 口器（长度 = 采蜜方式）"""
    for (dx, r) in ((-s * 0.9, s * 0.28), (-s * 0.35, s * 0.34), (s * 0.45, s * 0.5)):
        ts = np.linspace(0, 2 * math.pi, 18)
        f.poly(np.stack([x + dx + r * 1.2 * np.cos(ts), y + r * 0.8 * np.sin(ts)], 1), CIN, a, 2, closed=True)
    fl = 0.5 + 0.5 * math.sin(t * 22)
    for sd in (-1, 1):
        ts = np.linspace(0, 2 * math.pi, 18)
        wx, wy = x - s * 0.2 + sd * s * 0.25, y - s * (0.6 + 0.3 * fl)
        f.poly(np.stack([wx + s * 0.35 * np.cos(ts), wy + s * 0.5 * np.sin(ts) * (0.6 + 0.4 * fl)], 1), lerpc(CIN, WHITE, .5), a * 0.5, 1, closed=True)
    hx, hy = x - s * 1.15, y + s * 0.1
    if tip is None: tip = (hx - prob * 0.7, hy + prob * 0.7)
    d = math.hypot(tip[0] - hx, tip[1] - hy)
    tx, ty = hx + (tip[0] - hx) * prob / max(d, 1), hy + (tip[1] - hy) * prob / max(d, 1)
    f.line((hx, hy), (tx, ty), lerpc(CIN, WHITE, .3), a, 2)
    f.glow((tx, ty), 5, CIN, a, 'E')
    f.glow((x, y), s * 1.2, CIN, a * 0.15, 'B')


def curved_arrow(f, p0, pm, p2, col, a, prog=1.0, th=3):
    s = np.linspace(0, cl(prog), 30)[:, None]
    pts = (1 - s) ** 2 * np.array(p0) + 2 * (1 - s) * s * np.array(pm) + s ** 2 * np.array(p2)
    if len(pts) < 2 or prog <= 0.02: return
    f.poly(pts, col, a, th)
    arrow(f, tuple(pts[-4]), tuple(pts[-1]), col, a, th, 14)
    f.glow(tuple(pts[-1]), 8, lerpc(col, WHITE, .5), a, 'E')


# ================================================================ 场景
_HK = np.random.default_rng(4)
NODES = [(CX + 330 * math.cos(-math.pi / 2 + k * math.pi / 4), 420 + 210 * math.sin(-math.pi / 2 + k * math.pi / 4)) for k in range(8)]
NCOL = [PINK, VIOLET, TEAL, AMBER, PINK, GREEN, VIOLET, TEAL]


def sc_hook(f, t):
    if t > b(4) + 0.3: return
    a = env(t, 0, b(4), 0.3, 0.25)
    cx, cy = CX, 420
    inward = eo((t - b(2)) / 1.0)
    for k, (nx, ny) in enumerate(NODES):
        p = a * eo((t - 0.2 - k * 0.12) / 0.4)
        if p <= 0: continue
        f.line((cx, cy), (nx, ny), lerpc(NCOL[k], GREY, .4), p * 0.35, 1)
        f.poly(hexagon(nx, ny, 34, t * 0.4 + k), NCOL[k], p, 2, closed=True)
        f.glow((nx, ny), 14, NCOL[k], p * 0.7, 'E')
        for j in range(2):   # 往外的信号 + 往回的改进
            u = (t * 0.7 + k * 0.13 + j * 0.5) % 1.0
            f.glow((cx + (nx - cx) * u, cy + (ny - cy) * u), 4, CP, p * 0.9, 'E')
            v = (t * 0.7 + k * 0.17 + j * 0.5 + 0.25) % 1.0
            f.glow((nx + (cx - nx) * v, ny + (cy - ny) * v), 5, NCOL[k], p * inward, 'E')
    s = 1 + 0.12 * inward + 0.04 * beat_pulse(t)
    watch(f, cx, cy, 70 * s, CP, a, t)
    for k in range(8):   # 伙伴的颜色，一点点“长”进核心产品
        q = k * math.pi / 4 + t * 0.9
        f.glow((cx + 40 * math.cos(q), cy + 40 * math.sin(q)), 6, NCOL[k], a * inward, 'E')
    spin_ring(f, cx, cy, 120, t, CP, a * 0.45, 24, 0.8)
    spin_ring(f, cx, cy, 145, -t, BGOLD, a * 0.35 * inward, 16, 0.5)
    f.glow((cx, cy), 120, CP, a * 0.2 * (1 + beat_pulse(t)), 'B')
    implode(f, t, b(3), b(4), CX, 900, [BGOLD, CP, CQ, WHITE, BGOLD_L, VIOLET], 0.8)


def sc_title(f, t):
    if not (b(4) - 0.1 < t < b(7) + 0.5): return
    a = env(t, b(4), b(7) - 0.05, 0.25, 0.4)
    burst(f, t, b(4), CX, 860, [CP, CQ, BGOLD, BGOLD_L, WHITE, VIOLET], 0, 800, 1800, 1.5)
    helix(f, t, (CX, 300), (CX, 1300), 300, a * 0.45 * eo((t - b(4)) / 0.8), 1.4)
    t0 = b(4)
    rich_line(f, '共同进化 · COEVOLUTION', CX, 560, 32, 'sans_med', BGOLD, a=a, t0=t0 + 0.1, stag=0.02, track=0.1, underline=False)
    rich_line(f, '最好的产品，', CX, 700, 100, 'serif_black', TXT, a=a, t0=t0 + 0.2, stag=0.05)
    rich_line(f, '为什么不是', CX, 830, 100, 'serif_black', TXT, a=a, t0=t0 + 0.5, stag=0.05)
    rich_line(f, '{一家公司}做的？', CX, 960, 100, 'serif_black', TXT, a=a, t0=t0 + 0.8, stag=0.05, glow_hl=0.6)
    rich_line(f, '《50个自然法则，看懂商业世界》M05', CX, 1110, 36, 'sans_med', lerpc(BSUB, WHITE, .3), a=a, t0=t0 + 1.3, stag=0.015, underline=False)
    rich_line(f, '50 个来自自然、数学与复杂系统的思维模型', CX, 1168, 28, 'sans_light', lerpc(GREY, WHITE, .3), a=a, t0=t0 + 1.6, stag=0.01, underline=False)


def lanes(f, t, a, yp, yq, x0=120, x1=960, prog=1.0, labels=True):
    xe = x0 + (x1 - x0) * cl(prog)
    for y, col, lab in ((yp, CP, '平台'), (yq, CQ, '伙伴')):
        f.line((x0, y), (xe, y), col, a * 0.8, 3)
        f.glow((xe, y), 8, lerpc(col, WHITE, .5), a, 'E')
        if labels: f.text(lab, x0, y - 44, 30, 'sans_black', col, a, 'l', mode='O')
    f.text('时间 →', x1, yq + 44, 22, 'sans_light', GREY, a, 'r', mode='O')


def sc_promise(f, t):
    if not (b(7) - 0.1 < t < b(9)): return
    a = env(t, b(7), b(9), 0.4, 0.3)
    lanes(f, t, a, 560, 820, 160, 920, eo((t - b(7)) / 0.8))
    xs = [260, 420, 580, 740, 880]
    for k, x in enumerate(xs[:-1]):
        p = a * eo((t - b(7, 1) - k * BEAT * 0.5) / 0.3)
        y0, y1 = (560, 820) if k % 2 == 0 else (820, 560)
        f.glow((x, y0), 9, CP if y0 == 560 else CQ, p, 'E')
        if p > 0.05:
            arrow(f, (x + 10, y0 + (12 if y0 < y1 else -12)), (xs[k + 1] - 10, y1 + (-12 if y0 < y1 else 12)), BGOLD, p, 3, 14)


def sc_card1(f, t):
    if not (b(9) - 0.1 < t < b(10) + 0.1): return
    mirror_card(f, t, b(9), b(10), '01', '一朵花，一只虫', 'FLOWER & POLLINATOR', CFL)


FL_C, IN_C = (330, 520), (770, 470)


def coev_steps(t):
    """“你改一步，我跟一步”：b(21,2) 起每拍一步，花和昆虫交替加码"""
    if t < b(21, 2): return 0.0, 0.0
    x = (t - b(21, 2)) / BEAT
    k = int(x); fr = eio((x - k) / 0.6)
    nf = (k + 1) // 2 + (fr if k % 2 == 0 else 0)
    ni = k // 2 + (fr if k % 2 == 1 else 0)
    return min(nf, 3.0), min(ni, 3.0)


def sc_flower(f, t):
    if not (b(10) - 0.1 < t < b(25) + 0.1): return
    a = env(t, b(10), b(25), 0.4, 0.35)
    f.text('机制示意 · 不对应具体物种', CX, 228, 26, 'sans_light', lerpc(GREY, WHITE, .3), a, mode='O')
    nf, ni = coev_steps(t)
    depth = 70 + 30 * nf; prob = 80 + 30 * ni
    flower(f, FL_C[0], FL_C[1], 90, depth, a * eo((t - b(10)) / 0.6), t)
    hov = 10 * math.sin(t * 2.3)
    ix, iy = IN_C[0] + 20 * math.sin(t * 0.7), IN_C[1] + hov
    insect(f, ix, iy, 46, prob * 1.1, a * eo((t - b(10, 2)) / 0.6), t, tip=(FL_C[0] + 10, FL_C[1] + depth))
    p1 = eo((t - b(11, 2)) / 0.7); p2 = eo((t - b(13, 2)) / 0.7)
    sel = env(t, b(15, 2), b(25), 0.3, 0.3) * (0.5 + 0.5 * beat_pulse(t))
    curved_arrow(f, (400, 400), (560, 250), (700, 390), CFL, a * (0.85 + 0.4 * sel), p1, 3)
    f.text('花的形状 → 谁能采到蜜', 560, 260, 26, 'sans_black', lerpc(CFL, WHITE, .3), a * p1, mode='O')
    curved_arrow(f, (700, 600), (560, 760), (410, 640), CIN, a * (0.85 + 0.4 * sel), p2, 3)
    f.text('采蜜方式 → 哪些花结籽', 560, 800, 26, 'sans_black', lerpc(CIN, WHITE, .3), a * p2, mode='O')
    if sel > 0:
        for (c, col) in ((FL_C, CFL), (IN_C, CIN)):
            f.circle(c, 150 + 30 * (1 - beat_pulse(t)), col, a * sel * 0.4, 2)
    cyc = env(t, b(17, 2), b(21, 2) + 0.3, 0.4, 0.4)
    if cyc > 0:   # 共同进化：中央旋转的双向环
        q = t * 1.6
        f.arc((CX, 520), 70, q, q + 2.6, BGOLD, a * cyc, 3, 24); f.arc((CX, 520), 70, q + math.pi, q + math.pi + 2.6, BGOLD, a * cyc, 3, 24)
        for qq in (q + 2.6, q + math.pi + 2.6):
            arrow(f, (CX + 70 * math.cos(qq - 0.2), 520 + 70 * math.sin(qq - 0.2)), (CX + 70 * math.cos(qq), 520 + 70 * math.sin(qq)), BGOLD, a * cyc, 3, 12)
        f.glow((CX, 520), 60, BGOLD, a * cyc * 0.3, 'B')
    sa = a * env(t, b(21, 2) - 0.2, b(25), 0.4, 0.3)
    if sa > 0:   # 台阶图：一方加码一步，另一方跟一步
        x0, x1, y0, y1 = 170, 910, 910, 1110
        f.line((x0, y1), (x1, y1), GREY, sa * 0.6, 2)
        f.text('一代又一代 →', x1, y1 + 30, 22, 'sans_light', GREY, sa, 'r', mode='O')
        xe = x0 + (x1 - x0) * cl((t - b(21, 2)) / (BEAT * 7))
        for (n_, col, lab, first, off) in ((nf, CFL, '花的形状', 0, 0), (ni, CIN, '采蜜方式', 1, 8)):
            base = y1 - 20 - off
            pts = [(x0, base)]
            for s_ in range(1, int(math.ceil(n_)) + 1):
                xs_ = x0 + (x1 - x0) * (2 * (s_ - 1) + first + 0.5) / 7
                if xs_ > xe: break
                pts.append((xs_, pts[-1][1])); pts.append((xs_, base - 50 * min(s_, n_)))
            pts.append((max(xe, pts[-1][0]), pts[-1][1]))
            f.poly(pts, col, sa, 3)
            f.glow(pts[-1], 8, lerpc(col, WHITE, .5), sa, 'E')
            f.text(lab, pts[-1][0] + 14, pts[-1][1] - (16 if first == 0 else -16), 22, 'sans_black', col, sa, 'l', mode='O')


def sc_card2(f, t):
    if not (b(25) - 0.1 < t < b(26) + 0.1): return
    mirror_card(f, t, b(25), b(26), '02', '双向，才算共同进化', 'IT TAKES TWO WAYS', VIOLET)


ROWS_Y = [400, 620, 840]
_MZ = np.random.default_rng(9).integers(0, 3, 6)


def sc_points(f, t):
    if not (b(26) - 0.1 < t < b(41) + 0.1): return
    a = env(t, b(26), b(41) - 0.2, 0.35, 0.2)
    ra = a * env(t, b(26), b(33, 2) + 0.3, 0.35, 0.4)
    if ra > 0:
        f.text('J. N. Thompson《Four Central Points About Coevolution》', CX, 236, 22, 'corm', lerpc(GREY, WHITE, .3), ra, mode='O')
        names = ['相互选择：双方都在变', '地理背景：换个地方，结果不同', '多种结果：互利，或对抗']
        t_on = [b(27, 2), b(29, 2), b(31, 2)]
        for i, y in enumerate(ROWS_Y):
            p = ra * eo((t - b(26, 2) - i * BEAT) / 0.4)
            on = eo((t - t_on[i]) / 0.4)
            col = lerpc(GREY, BGOLD, on * 0.7)
            f.rrect(90, y - 95, 990, y + 95, 26, col, p * (0.5 + 0.5 * on), 2)
            f.rrect_fill(90, y - 95, 990, y + 95, 26, BGOLD, p * (0.03 + 0.08 * on))
            f.text('①②③'[i], 135, y, 40, 'sans_black', col, p, mode='O')
            q = ra * on
            if q <= 0: continue
            ix = 270
            if i == 0:
                f.circle((ix - 55, y), 32, CP, q, 3); f.circle((ix + 55, y), 32, CQ, q, 3)
                arrow(f, (ix - 18, y - 14), (ix + 18, y - 14), BGOLD, q, 2, 10); arrow(f, (ix + 18, y + 14), (ix - 18, y + 14), BGOLD, q, 2, 10)
            elif i == 1:
                for k in range(6):
                    hx, hy = ix - 70 + (k % 3) * 70, y - 30 + (k // 3) * 60
                    c = [CP, CQ, BGOLD][(_MZ[k] + int(t * 1.5 + k)) % 3]
                    f.poly(hexagon(hx, hy, 30, math.pi / 6), c, q, 2, closed=True)
                    f.fillpoly(hexagon(hx, hy, 26, math.pi / 6), c, q * 0.12)
            else:
                f.circle((ix - 70, y), 28, CP, q, 3); f.circle((ix - 30, y), 28, CQ, q, 3)
                arrow(f, (ix + 20, y), (ix + 55, y), CRIMSON, q, 3, 10); arrow(f, (ix + 110, y), (ix + 75, y), CRIMSON, q, 3, 10)
            f.text(names[i], 380, y, 34, 'sans_black', lerpc(WHITE, col, .3), q, 'l', mode='O')
    fa = a * env(t, b(33, 2), b(41), 0.4, 0.2)
    if fa > 0:   # 用户价值 = 核心产品 + 互补品
        chip(f, '用户价值', CX, 320, 44, BGOLD, fa * eo((t - b(35, 2)) / 0.4), 'sans_black', 0.16)
        f.text('=', CX, 420, 64, 'sans_black', WHITE, fa * eo((t - b(35, 2) - 0.2) / 0.4), mode='O')
        pc = fa * eo((t - b(35, 2) - 0.3) / 0.4)
        watch(f, 300, 560, 60, CP, pc, t)
        f.text('核心产品', 300, 690, 32, 'sans_black', CP, pc, mode='O')
        f.text('+', CX, 560, 64, 'sans_black', WHITE, pc, mode='O')
        pq = fa * eo((t - b(35, 2) - 0.6) / 0.4)
        for k in range(7):
            hx = 780 + (0 if k == 0 else 70 * math.cos(k * math.pi / 3)); hy = 560 + (0 if k == 0 else 70 * math.sin(k * math.pi / 3))
            f.poly(hexagon(hx, hy, 32, math.pi / 6), NCOL[k], pq, 2, closed=True)
            f.fillpoly(hexagon(hx, hy, 28, math.pi / 6), NCOL[k], pq * 0.15)
        f.text('互补品', 780, 690, 32, 'sans_black', CQ, pq, mode='O')
        po = fa * eo((t - b(37, 2)) / 0.5)
        if po > 0:   # 别人做的
            for k in range(4):
                px = 640 + k * 95
                icon_person(f, px, 900, 34, NCOL[k], po)
                u = (t * 0.8 + k * 0.25) % 1.0
                f.glow((px + (780 - px) * u, 860 + (620 - 860) * u), 6, NCOL[k], po * (1 - u), 'E')
            f.text('别人做的', 780, 990, 28, 'sans_black', CQ, po, mode='O')
            icon_person(f, 300, 900, 34, CP, po * 0.8)
            f.text('平台自己做', 300, 990, 28, 'sans_black', CP, po * 0.8, mode='O')
    implode(f, t, b(39, 2), b(41), CX, 700, [BGOLD, CP, CQ, WHITE, BGOLD_L, VIOLET], 0.7, R0=1100)


LP_Y, LQ_Y = 400, 720
EVENTS = [(250, 'P', '开放接口', b(46, 2)), (450, 'Q', '常用应用', b(48)), (650, 'P', '新传感器', b(49, 2)), (850, 'Q', '新功能', b(51))]


def ev_pos(e):
    return (e[0], LP_Y if e[1] == 'P' else LQ_Y)


def sc_spiral(f, t):
    if not (b(41) - 0.1 < t < b(57) + 0.1): return
    a = env(t, b(41), b(57) - 0.2, 0.15, 0.2)
    burst(f, t, b(41), CX, 450, [BGOLD, BGOLD_L, CP, CQ, WHITE, AMBER], 1, 900, 1900, 1.6)
    ha = a * env(t, b(41), b(43, 2) + 0.2, 0.1, 0.4)
    if ha > 0:
        helix(f, t, (60, 450), (1020, 450), 170, ha, 3.0)
        f.text('平台', 110, 250, 34, 'sans_black', CP, ha, mode='O'); f.text('伙伴', 970, 250, 34, 'sans_black', CQ, ha, mode='O')
    la = a * eo((t - b(43, 2)) / 0.5)
    if la <= 0: return
    f.rrect(CX - 330, 200, CX + 330, 256, 12, AMBER, la, 2)
    f.text('假设情景 · 教学用，不是真实公司', CX, 228, 30, 'sans_black', AMBER, la, mode='O')
    lanes(f, t, la, LP_Y, LQ_Y, 120, 960, eo((t - b(43, 2)) / 1.0))
    watch(f, 70, LP_Y, 26, CP, la * eo((t - b(45)) / 0.4), t)
    for k in range(4):
        f.rrect(52 + (k % 2) * 20, LQ_Y - 22 + (k // 2) * 22, 68 + (k % 2) * 20, LQ_Y - 6 + (k // 2) * 22, 3, CQ, la * eo((t - b(45, 1)) / 0.4), 2)
    for k, e in enumerate(EVENTS):
        p = la * eo((t - e[3]) / 0.4)
        if p <= 0: continue
        x, y = ev_pos(e)
        col = CP if e[1] == 'P' else CQ
        f.glow((x, y), 14, col, p, 'E'); f.glow((x, y), 40, col, p * 0.4 * (1 + beat_pulse(t)), 'B')
        chip(f, '①②③④'[k] + ' ' + e[2], x, y + (-80 if e[1] == 'P' else 80), 28, col, p, 'sans_black', 0.14)
        if k > 0:
            p0 = ev_pos(EVENTS[k - 1])
            pr = eo((t - e[3]) / 0.5)
            dy = 14 if p0[1] < y else -14
            arrow(f, (p0[0] + 10, p0[1] + dy), (p0[0] + 10 + (x - 20 - p0[0]) * pr, p0[1] + dy + (y - 2 * dy - p0[1]) * pr), BGOLD, p, 3, 14)
    if t > b(52, 2):   # 金色光点沿“双向螺旋”来回跑
        u = ((t - b(52, 2)) / (BAR * 1.0)) % 1.0
        seg = min(int(u * 3), 2); w = u * 3 - seg
        p0, p1 = ev_pos(EVENTS[seg]), ev_pos(EVENTS[seg + 1])
        comet(f, p0[0] + (p1[0] - p0[0]) * w, p0[1] + (p1[1] - p0[1]) * w, 16, BGOLD, la)
    ua = la * eo((t - b(54, 2)) / 0.5)
    if ua > 0:   # 用户体验：每次互相改变后上一个台阶（示意）
        x0, x1, yb = 120, 960, 1090
        pts = [(x0, yb)]
        for k, e in enumerate(EVENTS):
            h = 40 * (k + 1) * eo((t - b(54, 2)) / 0.8)
            pts.append((e[0], pts[-1][1])); pts.append((e[0], yb - h))
        pts.append((x1, pts[-1][1]))
        f.poly(pts, BGOLD, ua, 3)
        f.glow(pts[-1], 10, BGOLD_L, ua, 'E')
        f.text('用户体验（示意）', x0, yb - 190, 26, 'sans_black', BGOLD, ua, 'l', mode='O')


def sc_limits(f, t):
    if not (b(57) - 0.1 < t < b(67) + 0.2): return
    a = env(t, b(57), b(67), 0.5, 0.3)
    burst(f, t, b(57), CX, 600, [BLUE, CYAN, WHITE, VIOLET, BLUE, BGOLD], 2, 500, 900, 1.6)
    s1 = env(t, b(57), b(61) + 0.2, 0.4, 0.35)
    if s1 > 0:   # ① 对抗型：双方都在为对方改，只是互相防着
        q = a * s1 * eo((t - b(58, 2)) / 0.5)
        for (x, col, sd) in ((300, CP, 1), (780, CQ, -1)):
            f.circle((x, 560), 70, col, a * s1, 3)
            f.arc((x + sd * 110, 560), 90, math.pi * (-0.35 if sd > 0 else 0.65), math.pi * (0.35 if sd > 0 else 1.35), col, q, 4, 20)
        for k in range(3):
            u = ((t * 1.2 + k / 3) % 1.0)
            arrow(f, (390 + 120 * u, 520 + k * 40), (430 + 120 * u, 520 + k * 40), CRIMSON, q * (1 - u), 3, 10)
            arrow(f, (690 - 120 * u, 540 + k * 40), (650 - 120 * u, 540 + k * 40), CRIMSON, q * (1 - u), 3, 10)
        chip(f, '对抗型', CX, 360, 36, CRIMSON, q, 'sans_black', 0.14)
        f.text('示意', 960, 240, 22, 'sans_light', GREY, a * s1, 'r', mode='O')
    s2 = env(t, b(61), b(64) + 0.2, 0.4, 0.35)
    if s2 > 0:   # ② 单向依赖
        f.rrect(CX - 110, 330, CX + 110, 500, 24, CP, a * s2, 3)
        f.text('平台', CX, 415, 36, 'sans_black', CP, a * s2, mode='O')
        for k in range(3):
            x = 300 + k * 240
            f.circle((x, 820), 50, CQ, a * s2 * (0.7 + 0.3 * math.sin(t * 4 + k)), 3)
            arrow(f, (x, 760), (CX + (x - CX) * 0.3, 520), lerpc(GREY, WHITE, .3), a * s2 * 0.8, 2, 12)
        f.text('伙伴', 300, 900, 28, 'sans_black', CQ, a * s2, mode='O')
        chip(f, '单向依赖', CX, 640, 32, GREY, a * s2 * eo((t - b(61, 2)) / 0.4), 'sans_black', 0.14)
    s3 = env(t, b(64), b(67), 0.4, 0.3)
    if s3 > 0:   # ③ 同一阵风
        g = eo((t - b(64)) / 2.5)
        for (x, col) in ((420, CP), (660, CQ)):
            h = 120 + 330 * g
            f.rrect_fill(x - 45, 960 - h, x + 45, 960, 10, col, a * s3 * 0.55)
            f.rrect(x - 45, 960 - h, x + 45, 960, 10, col, a * s3, 2)
        f.text('平台', 420, 1000, 28, 'sans_black', CP, a * s3, mode='O'); f.text('伙伴', 660, 1000, 28, 'sans_black', CQ, a * s3, mode='O')
        for k in range(7):
            y = 380 + k * 80
            u = (t * 0.9 + k * 0.37) % 1.0
            x = -100 + 1300 * u
            f.line((x, y), (x + 160, y), BGOLD, a * s3 * 0.6 * math.sin(u * math.pi), 2)
        chip(f, '同一阵风：市场整体变大', CX, 300, 30, BGOLD, a * s3 * eo((t - b(65)) / 0.4), 'sans_black', 0.14)


def sc_q2(f, t):
    if not (b(67) - 0.1 < t < b(69) + 0.1): return
    implode(f, t, b(67), b(69), CX, 900, [CP, CQ, BGOLD, WHITE, BGOLD_L, VIOLET], 1.0, R0=1100)


TP_Y, TQ_Y = 380, 620
TL_P = [200, 420, 640, 860]
TL_Q = [300, 520, 740, 940]


def mini_lanes(f, cx, cy, a, two_way, t):
    x0, x1 = cx - 160, cx + 160
    f.line((x0, cy - 50), (x1, cy - 50), CP, a, 2); f.line((x0, cy + 50), (x1, cy + 50), CQ, a, 2)
    for k in range(3):
        xa = x0 + 30 + k * 100
        arrow(f, (xa, cy - 44), (xa + 40, cy + 44), lerpc(GREY, WHITE, .3), a, 2, 10)
        if two_way and k < 2:
            arrow(f, (xa + 50, cy + 44), (xa + 90, cy - 44), BGOLD, a, 2, 10)


def sc_timeline(f, t):
    if not (b(69) - 0.1 < t < b(85) + 0.2): return
    a = env(t, b(69), b(85), 0.15, 0.3)
    burst(f, t, b(69), CX, 500, [CP, BGOLD, CQ, WHITE, BGOLD_L, TEAL], 4, 900, 1900, 1.6)
    la = a * env(t, b(69), b(79, 2) + 0.2, 0.15, 0.4)
    if la > 0:
        lanes(f, t, la, TP_Y, TQ_Y, 120, 980, eo((t - b(69)) / 1.0))
        for k in range(4):
            p = la * eo((t - b(71, 2) - k * BEAT * 0.5) / 0.3)
            f.glow((TL_P[k], TP_Y), 12, CP, p, 'E'); f.glow((TL_Q[k], TQ_Y), 12, CQ, p, 'E')
            f.glow((TL_P[k], TP_Y), 30, CP, p * 0.4, 'B'); f.glow((TL_Q[k], TQ_Y), 30, CQ, p * 0.4, 'B')
            if p > 0.05:
                arrow(f, (TL_P[k] + 6, TP_Y + 14), (TL_Q[k] - 6, TQ_Y - 14), lerpc(GREY, WHITE, .3), p * 0.8, 2, 12)
        for k in range(3):   # 反向箭头（伙伴 → 平台）
            p = la * eo((t - b(73, 2) - k * BEAT) / 0.4)
            if p <= 0: continue
            arrow(f, (TL_Q[k] + 6, TQ_Y - 14), (TL_P[k + 1] - 6, TP_Y + 14), BGOLD, p, 4, 16)
            f.glow(((TL_Q[k] + TL_P[k + 1]) / 2, (TP_Y + TQ_Y) / 2), 26, BGOLD, p * 0.5 * (1 + beat_pulse(t)), 'B')
        chip(f, '反向箭头', CX, 290, 30, BGOLD, la * eo((t - b(73, 2)) / 0.4), 'sans_black', 0.14)
        for (cx, two, lab, col, tt) in ((300, False, '依赖', GREY, b(75, 2)), (780, True, '共同进化', BGOLD, b(77, 2))):
            p = la * eo((t - tt) / 0.4)
            if p <= 0: continue
            f.rrect(cx - 220, 760, cx + 220, 1090, 24, col, p, 2 + int(two))
            f.rrect_fill(cx - 220, 760, cx + 220, 1090, 24, col, p * 0.06)
            f.text('单向' if not two else '双向', cx, 800, 26, 'sans_med', GREY, p, mode='O')
            mini_lanes(f, cx, 920, p, two, t)
            f.text(lab, cx, 1045, 38, 'sans_black', lerpc(col, WHITE, .3), p, mode='O', glow=0.4 if two else 0)
    ca = a * eo((t - b(79, 2)) / 0.5)
    if ca > 0:   # 检查表
        x0, x1, y0, y1 = 110, 970, 230, 1110
        f.rrect_fill(x0, y0, x1, y1, 30, BGOLD, ca * 0.05)
        f.rrect(x0, y0, x1, y1, 30, BGOLD, ca, 3)
        spin_ring(f, x1 - 10, y0 + 10, 40, t, BGOLD_L, ca * 0.5, 16, 0.6)
        f.text('双向时间线 · 检查表', CX, y0 + 70, 46, 'serif_black', BGOLD, ca, mode='O', glow=0.4)
        hot = [None, None, b(79, 2), b(82)]
        for i, (q, sub, col) in enumerate(CHECK):
            y = y0 + 200 + i * 205
            p = eo((t - b(79, 2) - i * BEAT * 0.3) / 0.4) * ca
            hl = env(t, hot[i], b(85), 0.3, 0.3) if hot[i] else 0.0
            if hl > 0:
                f.rrect_fill(x0 + 30, y - 70, x1 - 30, y + 80, 18, col, ca * 0.10 * hl)
            f.text(q, x0 + 60, y - 18, 40, 'sans_black', col, p, 'l', mode='O', glow=0.3 * hl)
            f.text(sub, x0 + 60, y + 38, 28, 'sans_light', TXT, p, 'l', mode='O')
            ok = eo((t - b(80) - i * BEAT * 0.5) / 0.4)
            if ok > 0:
                f.circle((x1 - 90, y + 10), 30, TEAL, ca * ok, 3)
                f.poly([(x1 - 104, y + 10), (x1 - 92, y + 24), (x1 - 72, y - 6)], TEAL, ca * ok, 3)


# ---- 终章：双螺旋（片尾粒子从螺旋出发）
OH_Y, OH_AMP, OH_SPEED = 470, 170, 0.9


def sc_outro(f, t):
    if not (b(85) - 0.1 < t < T_GATHER0 + 0.1): return
    a = env(t, b(85), T_GATHER0, 0.5, 0.05)
    helix(f, t, (90, OH_Y), (990, OH_Y), OH_AMP, a, OH_SPEED)
    f.text('平台', 90, OH_Y - OH_AMP - 50, 30, 'sans_black', CP, a, 'l', mode='O')
    f.text('伙伴', 990, OH_Y - OH_AMP - 50, 30, 'sans_black', CQ, a, 'r', mode='O')
    g = env(t, b(89), T_GATHER0, 0.4, 0.2)
    if g > 0:   # 研究问题：伙伴有没有反过来改变它 —— 金色光点沿横档往返
        for k in range(5):
            x = 180 + k * 180
            q = (x - 90) * HX_K + t * OH_SPEED
            y1, y2 = OH_Y + OH_AMP * math.sin(q), OH_Y - OH_AMP * math.sin(q)
            u = 0.5 + 0.5 * math.sin(t * 3 + k)
            comet(f, x, y2 + (y1 - y2) * u, 9, BGOLD, a * g)



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
# 画面元素汇聚：粒子的起点取自终章那条双螺旋（两条链 + 金色横档）
_side = np.where(_er.uniform(0, 1, 5200) < 0.5, -1, 1)
_hx = _er.uniform(90, 990, 5200)
_hs = np.sin((_hx - 90) * HX_K + b(93) * OH_SPEED)
_rung = _er.uniform(0, 1, 5200) < 0.2
LP_SX = _hx
LP_SY = OH_Y + OH_AMP * _hs * np.where(_rung, _er.uniform(-1, 1, 5200), _side)
LP_DL = _er.uniform(0, 0.35, 5200)
LP_MIX = np.where(_rung[:, None], np.array(BGOLD, np.float32), np.where((_side < 0)[:, None], np.array(CP, np.float32), np.array(CQ, np.float32)))
T_GATHER0, T_GATHER1 = b(93), b(94, 2)    # 双螺旋化作粒子，汇聚成 logo
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
SCENES = [sc_hook, sc_title, sc_promise, sc_card1, sc_flower, sc_card2, sc_points, sc_spiral, sc_limits, sc_q2,
          sc_timeline, sc_outro, sc_end]


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
