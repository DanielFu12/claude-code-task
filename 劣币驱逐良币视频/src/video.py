"""谁杀死了好东西？—— 劣币驱逐良币 · 柠檬市场
竖屏 1080×1920 · 30fps · 约 3 分 52 秒，全片画面对齐配乐节拍（见 timeline.py）。"""
import math, os, sys
import numpy as np, cv2
from engine import *
from timeline import B, P, O, DUR, SFX

NFR = int(DUR * FPS)

# ============================================================== 节拍工具
def bdt(t):
    """距离上一拍的秒数"""
    k = math.floor((t - B(0)) / P)
    return t - B(k) if k >= 0 else 9.0

def beat_pulse(t, decay=0.12):
    return math.exp(-bdt(t) / decay)

def bar_pulse(t, decay=0.25):
    k = math.floor((t - B(0)) / P)
    if k < 0: return 0.0
    return math.exp(-(t - B(k - k % 4)) / decay)

def win(t, n0, n1, fi=0.35, fo=0.35):
    return env(t, B(n0), B(n1), fi, fo)

def since(t, n):
    return t - B(n)

def ENERGY(t):
    return keys(t, [(0, .35), (B(31.5), .45), (B(32), 1), (B(80), 1), (B(80.3), .55), (B(132), .6), (B(132.3), .9),
                    (B(160), .9), (B(160.3), .6), (B(164), 1), (B(232), 1), (B(232.5), .3), (B(268), .3), (B(268.3), 1),
                    (B(428), 1), (B(436), .3)])

# 重击：(拍号, 强度, 颜色)
IMPACTS = [(32, 1.0, GOLD), (80, 0.35, CYAN), (132, 0.6, GOLD), (164, 0.55, CYAN), (196, 0.7, RED),
           (216, 1.0, RED), (268, 1.0, GOLD), (296, 0.8, GOLD), (324, 1.0, GOLD), (416, 0.9, C(110, 175, 255))]

LEMON = C(186, 214, 72)          # 劣质 / 柠檬
LEMOND = C(120, 140, 60)
FOGC = C(120, 135, 160)
SOFT = lerpc(GREY, WHITE, 0.45)

# ============================================================== 背景
RNG = np.random.default_rng(2026)
NB1 = fbm(270, 480, 11, 6, 3); NB2 = fbm(270, 480, 22, 6, 3); NB3 = fbm(270, 480, 33, 5, 5)
# (时刻, 颜色A, 颜色B, 强度)
BGK = [
    (0, (8, 14, 40), (25, 10, 45), .55), (B(30), (10, 16, 46), (30, 12, 55), .7),
    (B(32), (120, 80, 20), (40, 30, 90), 1.4), (B(40), (20, 40, 95), (60, 25, 90), 1.0),
    (B(78), (20, 40, 95), (60, 25, 90), .95), (B(80), (10, 60, 90), (30, 30, 90), .9),
    (B(130), (12, 55, 85), (40, 30, 85), .85), (B(132), (90, 70, 25), (25, 35, 95), 1.1),
    (B(160), (30, 40, 90), (50, 30, 80), .9), (B(164), (15, 60, 110), (60, 25, 110), 1.05),
    (B(196), (60, 30, 40), (40, 20, 60), .8), (B(200), (130, 25, 35), (60, 15, 70), 1.15),
    (B(228), (110, 20, 30), (50, 12, 50), 1.0), (B(232), (25, 18, 30), (18, 14, 34), .45),
    (B(266), (25, 20, 34), (20, 16, 40), .5), (B(268), (150, 105, 30), (40, 60, 120), 1.4),
    (B(276), (80, 65, 30), (25, 55, 110), 1.0), (B(300), (40, 70, 110), (90, 70, 30), 1.0),
    (B(323.5), (20, 16, 10), (10, 10, 20), .3), (B(324), (190, 130, 30), (90, 60, 20), 1.6), (B(328), (70, 55, 25), (25, 40, 90), .95), (B(334), (30, 45, 95), (60, 40, 90), .9), (B(396), (60, 45, 22), (30, 30, 70), .85),
    (B(412), (20, 30, 70), (25, 20, 50), .7), (DUR, (8, 10, 25), (10, 8, 20), .4)]

def bg_at(t):
    a = keys(t, [(k[0], k[1]) for k in BGK]); b = keys(t, [(k[0], k[2]) for k in BGK])
    I = keys(t, [(k[0], k[3]) for k in BGK]) * (1 + 0.15 * beat_pulse(t, 0.2) * ENERGY(t))
    s = 1.0 + 0.05 * math.sin(t * 0.06)
    M = np.float32([[s, 0, -10 - 9 * math.sin(t * 0.045)], [0, s, -16 - 14 * math.cos(t * 0.037)]])
    n1 = cv2.warpAffine(NB1, M, (270, 480), borderMode=cv2.BORDER_REFLECT)
    M2 = np.float32([[s, 0, -10 + 9 * math.sin(t * 0.05 + 1)], [0, s, -16 + 14 * math.sin(t * 0.03)]])
    n2 = cv2.warpAffine(NB2, M2, (270, 480), borderMode=cv2.BORDER_REFLECT)
    n3 = cv2.warpAffine(NB3, M, (270, 480), borderMode=cv2.BORDER_REFLECT)
    img = ((n1 ** 3)[..., None] * np.array(a, np.float32) + (n2 ** 3.2)[..., None] * np.array(b, np.float32)) * (0.55 + 0.8 * n3)[..., None]
    img *= I * 0.5 / 255.0
    return cv2.resize(img, (W, H), interpolation=cv2.INTER_LINEAR)

_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W * 0.62)) ** 2 + ((_yy - H / 2) / (H * 0.55)) ** 2)
VIGNETTE = np.clip(1 - 0.45 * _r ** 2.3, 0.22, 1)[..., None].astype(np.float32)
del _yy, _xx, _r
GRAINS = [make_grain(s, 0.006) for s in range(6)]

# ---------------------------------------------------------------- 尘埃星场（带视差，重击时跃迁）
NST = 900
ST_X = RNG.uniform(-1.0, 1.0, NST); ST_Y = RNG.uniform(-1.8, 1.8, NST); ST_Z0 = RNG.uniform(0, 1, NST)
ST_COL = np.array([lerpc(WHITE, [CYAN, GOLD2, WHITE, VIOLET][i % 4], 0.35) for i in range(NST)], np.float32)

def star_speed(t):
    v = 0.03
    for n, k, _ in IMPACTS:
        ti = B(n)
        if t >= ti: v += k * 1.3 * math.exp(-(t - ti) / 0.5)
    for a, b in [(28, 32), (262, 268), (321, 324), (410, 416)]:
        if B(a) <= t <= B(b): v += 0.3 * ei((t - B(a)) / (B(b) - B(a)))
    return v

_ts = np.arange(NFR + 2) / FPS
ST_S = np.concatenate([[0], np.cumsum([star_speed(x) / FPS for x in _ts])])

def draw_stars(f, t, a=1.0):
    if a <= 0: return
    d = ST_S[min(int(t * FPS), NFR)]
    z = (ST_Z0 - d) % 1.0 + 0.04
    sp = star_speed(t)
    x = W / 2 + ST_X / z * 300; y = H / 2 + ST_Y / z * 300
    al = np.clip((1 - z) * 1.3, 0, 1) * 0.55 * a * (0.8 + 0.2 * math.sin(t))
    f.splat(x, y, ST_COL, al, 'E')
    if sp > 0.25:   # 跃迁拖尾
        for k in range(1, 6):
            z2 = z + sp * 0.012 * k
            f.splat(W / 2 + ST_X / z2 * 300, H / 2 + ST_Y / z2 * 300, ST_COL, al * (1 - k / 6) * 0.8, 'E')

def shockwaves(f, t):
    for n, k, col in IMPACTS:
        dt = t - B(n)
        if 0 <= dt < 1.4:
            for j in range(2):
                r = (dt - j * 0.1) * 1500 * k
                if r > 0:
                    f.circle((W / 2, H / 2), r, col, k * 0.6 * (1 - dt / 1.4) ** 2, 3)
            if dt < 0.3: f.flash = max(f.flash, k * 0.32 * (1 - dt / 0.3) ** 2)
            if dt < 0.35: f.ca = max(f.ca, k * 9 * (1 - dt / 0.35))

def burst(f, t, t0, cx, cy, cols, seed=0, n=600, speed=1300, life=1.5, drag=2.3, a=1.0):
    dt = t - t0
    if dt < 0 or dt > life: return
    rng = np.random.default_rng(seed)
    ang = rng.uniform(0, 2 * np.pi, n); v = speed * rng.uniform(0.15, 1.0, n) ** 1.5
    dist = v * (1 - np.exp(-drag * dt)) / drag
    x = cx + np.cos(ang) * dist; y = cy + np.sin(ang) * dist + 60 * dt * dt
    cs = np.array(cols, np.float32)[rng.integers(0, len(cols), n)]
    al = (1 - dt / life) ** 1.6 * a * rng.uniform(0.5, 1, n)
    f.dots(x, y, cs, al, 1, 'E')

def god_rays(f, t, cx, cy, col, a, n=90, seed=7, L=1500):
    """体积光：从一点放射的光束（低分辨率绘制后模糊）"""
    if a <= 0.003: return
    k = 4
    S = np.zeros((H // k, W // k, 3), np.float32)
    rng = np.random.default_rng(seed)
    ang = rng.uniform(0, 2 * np.pi, n); br = rng.uniform(0.2, 1.0, n); ln = rng.uniform(0.4, 1.0, n)
    for i in range(n):
        th = ang[i] + 0.04 * math.sin(t * 0.7 + i)
        b = br[i] * (0.6 + 0.4 * math.sin(t * 1.3 + i * 2.1))
        x1, y1 = cx + math.cos(th) * L * ln[i], cy + math.sin(th) * L * ln[i]
        cv2.line(S, (int(cx / k), int(cy / k)), (int(x1 / k), int(y1 / k)), tuple(float(c * b) for c in col), 2, cv2.LINE_AA)
    S = cv2.GaussianBlur(S, (0, 0), 3)
    yy, xx = np.mgrid[0:H // k, 0:W // k].astype(np.float32)
    fall = np.exp(-np.sqrt((xx - cx / k) ** 2 + (yy - cy / k) ** 2) / (L / k * 0.45))[..., None]
    f.B += cv2.resize(S * fall, (W, H), interpolation=cv2.INTER_LINEAR) * a * 0.5

def implode(f, t, t0, t1, cx, cy, cols, a=1.0, R0=1100, seed=3, n=900):
    if not (t0 <= t <= t1): return
    p = (t - t0) / (t1 - t0)
    rng = np.random.default_rng(seed)
    ang0 = rng.uniform(0, 2 * np.pi, n); r0 = R0 * rng.uniform(0.4, 1.0, n)
    r = r0 * (1 - ei(p)) ** 1.3 + 4
    ang = ang0 + ei(p) * 2.4
    cs = np.array(cols, np.float32)[rng.integers(0, len(cols), n)]
    f.dots(cx + np.cos(ang) * r, cy + np.sin(ang) * r, cs, a * (0.3 + 0.7 * p), 1, 'E')

# ============================================================== 品牌角标（仓库根目录 brand/）
sys.path.insert(0, os.path.join(HERE, '..', '..', 'brand'))
import brand as BR
from brand import Hud, load_logo
HUD = Hud(scale=1.0, frame_w=W)

def draw_hud_post(img, t, a):
    """tone-map 之后合成右上角角标（品牌原色）"""
    if a <= 0.003: return img
    h = HUD.y0 + HUD.h + HUD.P + 2
    reg = img[:h].astype(np.float32) / 255
    HUD.draw(reg, t, a)
    img[:h] = (np.clip(reg, 0, 1) * 255 + 0.5).astype(np.uint8)
    return img

CHAPTERS = [(0, '', ''), (44, '01', '格雷欣法则'), (80, '02', '柠檬市场'), (132, '03', '真相'), (232, '04', '劣币会传染'),
            (268, '05', '破局'), (328, '06', '投资启示'), (396, '', ''), (999, '', '')]

def draw_chrome(f, t):
    for (a, num, zh), (b, *_r) in zip(CHAPTERS, CHAPTERS[1:]):
        if num and B(a) <= t < B(b):
            al = env(t, B(a), B(b), 0.6, 0.4) * 0.85
            f.text(num, 60, 66, 34, 'oswald', GOLD, al, 'l', mode='O')
            x = 60 + text_width(num, 'oswald', 34) + 14
            f.line((x, 50), (x, 82), GOLD, al * 0.6, 1)
            f.text(zh, x + 14, 66, 28, 'sans_med', WHITE, al * 0.9, 'l', mode='O')

# ============================================================== 通用组件
def card(f, x0, y0, x1, y1, col, a, fill=0.07, r=26, th=2, buf='L'):
    if a <= 0.003: return
    f.rrect_fill(x0, y0, x1, y1, r, col, a * fill, buf)
    f.rrect(x0, y0, x1, y1, r, col, a * 0.7, th)

def rich(f, s, y, size, t0, a=1.0, col=WHITE, fnt='serif_black', glow=0.3, stag=0.05, x=W / 2, anchor='m',
         dur=0.55, kin=True, grad=None, track=0.02, rise=22, hlcol=None):
    """动态字：【】里的词用金色渐变 + 辉光 + 下划线扫光强调"""
    segs, cur, on = [], '', False
    for ch in s:
        if ch in '【】':
            if cur: segs.append((cur, on))
            cur, on = '', ch == '【'
        else:
            cur += ch
    if cur: segs.append((cur, on))
    ws = [text_width(sg, fnt, size, track) for sg, _ in segs]
    total = sum(ws) + track * size * (len(segs) - 1)
    xs = x - total / 2 if anchor == 'm' else (x if anchor == 'l' else x - total)
    i0 = 0
    for (sg, hl), w in zip(segs, ws):
        hg = [GOLD2, GOLD] if hlcol is None else [lerpc(hlcol, WHITE, 0.3), hlcol]
        f.text(sg, xs, y, size, fnt, col, a, 'l', mode='O', grad=hg if hl else grad, glow=glow * (2.2 if hl else 1),
               t0=t0 + i0 * stag, stag=stag, dur=dur, rise=rise, kin=kin, track=track)
        if hl and a > 0.003:
            te = t0 + (i0 + len(sg)) * stag + 0.1
            p = eo((f.t - te) / 0.45)
            if p > 0:
                uy = y + size * 0.62
                c = hg[1]
                f.line((xs, uy), (xs + w * p, uy), c, a * 0.9, 3)
                f.glow((xs + w * p, uy), 6, c, a * (1 - p * 0.6), 'E')
                f.glow((xs + w * p, uy), 26, c, a * 0.4 * (1 - p), 'B')
        xs += w + track * size
        i0 += len(sg)

def headline(f, s, y, size, t0, a=1.0, col=WHITE, grad=None, fnt='serif_black', glow=0.35, out=None, stag=0.05, track=0.02,
             hlcol=None):
    rich(f, s, y, size, t0, a, col, fnt, glow, stag, grad=grad, track=track, hlcol=hlcol)

def body(f, s, y, size, t0, a=1.0, col=None, fnt='sans_med', x=W / 2, anchor='m', stag=0.025, out=None, track=0.03, glow=0.0):
    rich(f, s, y, size, t0, a, col or lerpc(WHITE, GREY, 0.12), fnt, glow, stag, x=x, anchor=anchor, dur=0.42,
         track=track, rise=14)

def note(f, s, y, t0, a=1.0, size=25):
    f.text(s, W / 2, y, size, 'sans_light', lerpc(GREY, WHITE, 0.15), a * 0.85, 'm', mode='O', t0=t0, stag=0.01, dur=0.4,
           rise=8)

def gline(f, x0, x1, y, col, a, p=1.0, th=2):
    """从中间向两侧展开的细线"""
    if a <= 0.003 or p <= 0: return
    cx = (x0 + x1) / 2; hw = (x1 - x0) / 2 * eo(p)
    f.line((cx - hw, y), (cx + hw, y), col, a, th)
    f.glow((cx - hw, y), 5, col, a * 0.5, 'E'); f.glow((cx + hw, y), 5, col, a * 0.5, 'E')

def number(f, v, x, y, size, col, a, fmt='{:.0f}', fnt='oswald', anchor='m', glow=0.5, prefix='', suffix='', mode='O'):
    s = prefix + fmt.format(v) + suffix
    f.text(s, x, y, size, fnt, col, a, anchor, mode=mode, glow=glow)

def tick_val(t, n0, vals, step=2):
    """从第 n0 拍开始，每 step 拍切换一个数值；返回 (值, 距切换秒数)"""
    k = int(math.floor((t - B(n0)) / (P * step)))
    k = max(0, min(k, len(vals) - 1))
    return vals[k], t - B(n0 + k * step), k

def SCENE(n0, n1):
    """装饰器：仅在 [B(n0)-0.5, B(n1)+0.5] 内调用"""
    def deco(fn):
        def w(f, t):
            if B(n0) - 0.6 <= t <= B(n1) + 0.6: fn(f, t)
        w.__name__ = fn.__name__
        return w
    return deco


# ============================================================== 市场粒子（贯穿全片的「卖家」）
NM = 760
_i = np.arange(NM) + 0.5
_phi = np.arccos(1 - 2 * _i / NM); _th = math.pi * (1 + 5 ** 0.5) * _i
MK_P = np.stack([np.sin(_phi) * np.cos(_th), np.cos(_phi), np.sin(_phi) * np.sin(_th)], 1)
MK_P *= RNG.uniform(0.82, 1.08, NM)[:, None]
MK_Q = RNG.uniform(0, 1, NM)                      # 质量 0..1（卖家保留价值 = 100q）
MK_SEED = RNG.uniform(0, 1, NM)
QGRAD = [C(95, 110, 55), LEMON, C(230, 220, 120), GOLD, GOLD2]

def qcol(q):
    q = np.clip(np.asarray(q), 0, 1)
    k = len(QGRAD) - 1
    i = np.minimum((q * k).astype(int), k - 1)
    u = (q * k - i)[..., None]
    G = np.array(QGRAD, np.float32)
    return G[i] * (1 - u) + G[i + 1] * u

MK_COL = qcol(MK_Q)

def draw_sphere(f, t, cam, a=1.0, col=None, alive=None, R=1.0, size=1, glowk=0.0, offs=None):
    P3 = MK_P * R
    if offs is not None: P3 = P3 + offs
    x, y, z, s = cam.project(P3)
    dep = np.clip((cam.dist + 1.2 - z) / 2.4, 0.15, 1)   # 前亮后暗
    al = a * dep * (0.55 + 0.45 * np.sin(t * 2 + MK_SEED * 40) ** 2)
    if alive is not None: al = al * alive
    cs = MK_COL if col is None else col
    near = z < cam.dist - 0.25 * R                     # 近处粒子更大更亮（景深）
    cs = np.broadcast_to(np.asarray(cs, np.float32), (len(x), 3))
    al = np.broadcast_to(al, x.shape)
    f.dots(x[~near], y[~near], cs[~near], al[~near] * 0.8, size, 'E')
    f.dots(x[near], y[near], cs[near], al[near], size * 1.8, 'E')
    f.soft(x, y, cs, al * (0.35 + glowk), 2.2 * size + 1.5, 'E')
    f.soft(x[near], y[near], cs[near], al[near] * 0.25, 9 * size, 'B')
    return x, y, z, al


# ============================================================== 0 · 序章：五条真实热点 → 「你看不见」
from PIL import Image as PImage, ImageDraw as PDraw, ImageFont as PFont

def _pf(name, size):
    return PFont.truetype(FONTS[name], size)

def make_card(tag, date, title, fact, src, accent, w=920, h=370):
    """深色玻璃质感的新闻卡片（RGBA 直通色）"""
    k = 2                                    # 2 倍超采样
    im = PImage.new('RGBA', (w * k, h * k), (0, 0, 0, 0))
    d = PDraw.Draw(im)
    ac = tuple(int(c * 255) for c in accent)
    d.rounded_rectangle((0, 0, w * k - 1, h * k - 1), 30 * k, fill=(12, 14, 24, 215), outline=ac + (230,), width=3 * k)
    d.rounded_rectangle((0, 0, 12 * k, h * k - 1), 6 * k, fill=ac + (255,))
    tf = _pf('sans_med', 26 * k)
    tw = d.textlength(tag, font=tf)
    d.rounded_rectangle((52 * k, 40 * k, 52 * k + tw + 36 * k, 84 * k), 22 * k, fill=ac + (255,))
    d.text((70 * k, 62 * k), tag, font=tf, fill=(255, 255, 255, 255), anchor='lm')
    d.text((52 * k + tw + 60 * k, 62 * k), date, font=_pf('oswald', 40 * k), fill=ac + (255,), anchor='lm')
    d.text((52 * k, 160 * k), title, font=_pf('serif_black', 74 * k), fill=(255, 255, 255, 255), anchor='lm')
    d.text((52 * k, 258 * k), fact, font=_pf('sans_med', 33 * k), fill=(226, 230, 240, 255), anchor='lm')
    d.text((52 * k, 322 * k), src, font=_pf('sans_light', 22 * k), fill=(150, 158, 178, 255), anchor='lm')
    im = im.resize((w, h), PImage.LANCZOS)
    return np.asarray(im, np.float32) / 255

CASES = [  # (出场拍, 标签, 日期, 标题, 一句话事实, 来源, 强调色, 「看不见的是什么」, 「结果」)
    (8.3, '热议', '2026.4', '幽灵外卖', '无证、无堂食的「幽灵店铺」，在平台上照样接单', '新华社 · 7 家平台被罚 35.97 亿元', MAGENTA,
     '后厨', '有真厨房的店，拼不过没厨房的'),
    (11.5, '热议', '2026.8', '甲醛白菜', '收购商用甲醛溶液蘸菜根，只为运输「保鲜」', '河北康保县通报情况属实 · 国务院食安办等三部门督办', RED,
     '菜根里泡了什么', '老实保鲜的，成本反而更高'),
    (14.7, '热议', '2026.10', '刹车踏板支架断裂', '媒体测试中，3 辆车的踏板支架接连断裂', '工信部等三部门已成立联合调查组 · 结论尚未公布', ORANGE,
     '零件的安全余量', '多花的安全成本，顾客看不出来'),
]
CARD_IMG = [make_card(c[1], c[2], c[3], c[4], c[5], c[6]) for c in CASES]

def quad(cam, cx3, cy3, cz3, yaw, pitch, roll, hw, hh):
    P = np.array([[-hw, hh, 0], [hw, hh, 0], [hw, -hh, 0], [-hw, -hh, 0]], np.float64)
    cr, sr = math.cos(roll), math.sin(roll)
    P = P @ np.array([[cr, sr, 0], [-sr, cr, 0], [0, 0, 1]])
    cyw, syw = math.cos(yaw), math.sin(yaw)
    P = P @ np.array([[cyw, 0, -syw], [0, 1, 0], [syw, 0, cyw]])
    cp, sp = math.cos(pitch), math.sin(pitch)
    P = P @ np.array([[1, 0, 0], [0, cp, sp], [0, -sp, cp]])
    P += np.array([cx3, cy3, cz3])
    x, y, z, s_ = cam.project(P)
    return list(zip(x, y)), z.min()

def floor_grid(f, t, a, col=CYAN, speed=0.6, hy=1250):
    """透视地面网格，缓缓向镜头流动"""
    if a <= 0.003: return
    cam = Cam(yaw=0, pitch=0.32, dist=4, f=1100, cy=hy)
    off = (t * speed) % 1.0
    for k in range(-12, 13):
        x, y, z, _ = cam.project(np.array([[k * 0.6, -1.2, -1.0], [k * 0.6, -1.2, 14.0]]))
        f.line((x[0], y[0]), (x[1], y[1]), col, a * 0.22, 1)
    for j in range(16):
        zz = j - off
        if zz < -1: continue
        x, y, z, _ = cam.project(np.array([[-8, -1.2, zz], [8, -1.2, zz]]))
        fade = cl(1 - zz / 14)
        f.line((x[0], y[0]), (x[1], y[1]), col, a * 0.28 * fade, 1)

@SCENE(8, 32)
def sc_hook(f, t):
    floor_grid(f, t, win(t, 7, 24, 0.5, 1.0) * 0.8, col=C(90, 120, 200))
    rich(f, '最近的热搜', 300, 40, B(8.1), win(t, 7, 18, 0.2, 0.4), col=SOFT, fnt='sans_med')
    # --- 三张卡片：从远处飞入，旧卡片层层退后
    cam = Cam(dist=3.0, f=1380, cy=900)
    ac = win(t, 7, 18.3, 0.05, 0.4)
    for i, c in enumerate(CASES):
        n0 = c[0]
        if t < B(n0) - 0.05: continue
        pin = eo((t - B(n0)) / 0.4)
        dep = sum(1 for cc in CASES if cc[0] > n0 and t > B(cc[0]))
        z = 5.5 * (1 - pin) + 0.9 * min(dep, 4)
        y3 = -1.1 * (1 - pin) + 0.36 * min(dep, 4)
        yaw = 0.55 * (1 - pin) * (1 if i % 2 else -1)
        al = ac * pin * max(0.0, 1 - 0.3 * dep)
        if al <= 0.01: continue
        corners, zmin = quad(cam, 0, y3, z, yaw, 0.1 * (1 - pin), 0.03 * (1 - pin) * (1 if i % 2 else -1), 1.0, 0.402)
        warp_sprite(f, CARD_IMG[i], corners, al, glow=0.3 if dep == 0 else 0.0, glow_col=c[6])
        if dep == 0 and t - B(n0) < 0.25:
            f.ca = max(f.ca, 9 * (1 - (t - B(n0)) / 0.25))
    # --- 钩子：为什么越来越差？
    a2 = win(t, 18, 31.5, 0.2, 0.4)
    if a2 > 0:
        fg = fog(t * 1.2) * eo((t - B(18)) / 1.2)
        f.L += (fg * a2)[..., None] * np.array(FOGC, np.float32) * 0.16
        headline(f, '为什么，我们买到的东西', 760, 74, B(18), a2)
        rich(f, '越来越【差】了？', 930, 132, B(19.5), a2, glow=0.6, stag=0.08, hlcol=RED)
        body(f, '不是你的错觉，', 1180, 46, B(24), a2, col=SOFT)
        body(f, '也不只是商家的良心问题。', 1250, 46, B(25.5), a2, col=SOFT)
        headline(f, '答案，藏在一条古老的经济学定律里——', 1440, 52, B(27.5), a2, col=GOLD2, fnt='serif_semi')
    implode(f, t, B(28), B(32), W / 2, 960, [GOLD, GOLD2, LEMON, WHITE], 0.9)


# ============================================================== 1 · 标题：劣币驱逐良币
@SCENE(32, 44)
def sc_title(f, t):
    a = win(t, 32, 44, 0.05, 0.5)
    if a <= 0: return
    dt = t - B(32)
    cam = Cam(yaw=0.4 + dt * 0.25, pitch=0.25, dist=3.0, f=1150, cy=960)
    R = 1.0 + 1.4 * math.exp(-dt / 0.5)
    draw_sphere(f, t, cam, a * 0.45, R=R, glowk=0.6, size=1.5)
    burst(f, t, B(32), W / 2, 960, [GOLD, GOLD2, LEMON, WHITE], seed=1, n=900, speed=1700)
    sc = 1 + 0.06 * math.exp(-dt / 0.25)
    body(f, '为什么我们买到的东西越来越差？', 770, 42, B(32.5), a, col=SOFT)
    rich(f, '劣币驱逐良币', 930, int(140 * sc), B(32), a, grad=[GOLD2, GOLD, GOLDD], glow=0.7, stag=0.07)
    gline(f, 200, 880, 1080, GOLD, a * 0.8, (t - B(34)) / 0.5)
    body(f, '格雷欣法则 · 柠檬市场 · 逆向选择', 1140, 40, B(34), a, col=GOLD2)
    f.text('BAD MONEY DRIVES OUT GOOD', W / 2, 1200, 28, 'corm', SOFT, a * 0.9 * eo((t - B(35)) / 0.6), 'm', track=0.3, mode='O')


# ============================================================== 道具
SHRIMP_C = C(255, 128, 92)

def shrimp(f, cx, cy, s, ang, col, a, th=3):
    """线描虾仁：一段 C 形弧 + 体节 + 尾扇"""
    if a <= 0.003: return
    ts = np.linspace(0.15 * math.pi, 1.55 * math.pi, 26) + ang
    r = s * (1 - 0.35 * (ts - ts[0]) / (ts[-1] - ts[0]))
    pts = np.stack([cx + r * np.cos(ts), cy + r * np.sin(ts)], 1)
    rin = r * 0.48
    pin = np.stack([cx + rin * np.cos(ts), cy + rin * np.sin(ts)], 1)
    f.poly(pts, col, a, th); f.poly(pin, col, a * 0.8, th)
    for k in range(3, 24, 4):
        f.line(tuple(pts[k]), tuple(pin[k]), col, a * 0.6, 2)
    e, ei_ = pts[-1], pin[-1]
    tip = (e + ei_) / 2 + (e - pts[-3]) * 1.2
    f.poly([tuple(e), tuple(tip), tuple(ei_)], col, a * 0.9, th)
    f.glow((cx, cy), s * 0.9, col, a * 0.18, 'B')

def ice_cube(f, cam, sc, col, a, t):
    V = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], np.float64) * sc
    x, y, z, s_ = cam.project(V)
    faces = [(0, 1, 3, 2), (4, 5, 7, 6), (0, 1, 5, 4), (2, 3, 7, 6), (0, 2, 6, 4), (1, 3, 7, 5)]
    for fc in faces:
        f.fillpoly([(x[i], y[i]) for i in fc], col, a * 0.035, 'L')
    for i0, i1 in [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]:
        f.line((x[i0], y[i0]), (x[i1], y[i1]), col, a * 0.85, 2)
    for i in range(8):
        f.glow((x[i], y[i]), 4, WHITE, a * 0.8, 'E')

def bag(f, cx, cy, col, a, scan, contents, t, seed):
    w, h = 300, 420
    f.rrect_fill(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, 30, col, a * 0.06, 'L')
    f.rrect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, 30, col, a * 0.8, 2)
    f.line((cx - w / 2 + 20, cy - h / 2 + 40), (cx + w / 2 - 20, cy - h / 2 + 40), col, a * 0.6, 2)
    f.text('虾仁 500g', cx, cy - h / 2 + 100, 40, 'serif_black', WHITE, a * (1 - 0.6 * (scan > cy - h / 2 + 100)), 'm', mode='O')
    rng = np.random.default_rng(seed)
    if contents == 'full':
        for k in range(9):
            r_, c_ = divmod(k, 3)
            px, py = cx - 85 + c_ * 85, cy - 20 + r_ * 85
            if py < scan: shrimp(f, px, py, 30, k * 0.7 + t * 0.3, SHRIMP_C, a, 2)
    else:
        for k in range(3):
            px, py = cx - 70 + k * 70, cy + 120
            if py < scan: shrimp(f, px, py, 30, k * 0.9 + t * 0.3, SHRIMP_C, a, 2)
        xs = rng.uniform(cx - 120, cx + 120, 70); ys = rng.uniform(cy - 70, cy + 180, 70)
        ok = ys < scan
        f.dots(xs[ok], ys[ok], C(170, 230, 255), a * 0.8, 1, 'E')
        f.soft(xs[ok], ys[ok], C(170, 230, 255), a * 0.35, 7, 'E')

# ============================================================== 3 · 线索：嫌疑人 → 格雷欣法则 → 区分
def coin(f, cx, cy, R, ang, col, a, label, sub=None, dark=False):
    """3D 旋转硬币：正面椭圆（宽度随 cos 变化）+ 厚度边"""
    if a <= 0.003: return
    c = math.cos(ang); w = max(abs(c), 0.06) * R
    th = 16 * math.sin(ang)
    ts = np.linspace(0, 2 * np.pi, 64)
    rim = np.stack([cx + th + w * np.cos(ts), cy + R * np.sin(ts)], 1)
    face = np.stack([cx + w * np.cos(ts), cy + R * np.sin(ts)], 1)
    f.fillpoly(rim, lerpc(col, (0, 0, 0), 0.55), a * 0.6, 'L')
    f.fillpoly(face, col, a * (0.22 if dark else 0.32), 'E')
    f.poly(face, col, a, 3, closed=True)
    inner = np.stack([cx + w * 0.8 * np.cos(ts), cy + R * 0.8 * np.sin(ts)], 1)
    f.poly(inner, col, a * 0.6, 2, closed=True)
    if abs(c) > 0.35:
        f.text(label, cx, cy - 8, int(R * 0.62), 'oswald' if label.isdigit() else 'serif_black', lerpc(col, WHITE, 0.4), a * cl((abs(c) - 0.35) * 2.5), 'm', mode='O')
    f.glow((cx, cy), R * 0.8, col, a * 0.25, 'B')

def person(f, cx, cy, s, col, a):
    f.circle((cx, cy - s * 0.35), s * 0.22, col, a, 3)
    f.arc((cx, cy + s * 0.45), s * 0.42, math.pi, 2 * math.pi, col, a, 3)

def stamp(f, t, n0, cx, cy, txt='法定同价', a=1.0):
    st = cl((t - B(n0)) / 0.22)
    if st <= 0: return
    sc = 1 + 1.5 * (1 - eo(st))
    hit = math.exp(-max(0, t - B(n0) - 0.22) / 0.15) if t > B(n0) + 0.22 else 0
    w_, h_ = 280 * sc, 116 * sc
    f.rrect(cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2, 14, RED, a * st, 4)
    f.text(txt, cx, cy, int(56 * sc), 'serif_black', RED, a * st, 'm', mode='O', glow=0.5 + hit)
    if hit > 0.05: f.ca = max(f.ca, 6 * hit)

@SCENE(44, 80)
def sc_gresham(f, t):
    # --- 格雷欣：两枚硬币
    a = win(t, 44, 72, 0.35, 0.4)
    if a > 0:
        body(f, '先看一个两千年前就有的选择', 300, 40, B(44), a, col=GOLD)
        sp = (t - B(44)) * 1.4
        p = eo((t - B(44)) / 0.5)
        flow = 0
        # 硬币上移给流动动画让位
        cy = 640
        coin(f, 300, cy, 150 * p, sp, GOLD, a * p, '100')
        coin(f, 780, cy, 150 * p, sp + 1.3, C(170, 150, 110), a * p, '80', dark=True)
        f.text('良币 · 含金 100', 300, cy + 210, 38, 'sans_med', GOLD2, a * p, 'm', mode='O')
        f.text('劣币 · 含金 80', 780, cy + 210, 38, 'sans_med', C(200, 185, 150), a * p, 'm', mode='O')
        ab = win(t, 62, 72, 0.3, 0.4)
        ap = win(t, 46, 72, 0.3, 0.4) * (1 - ab)
        card(f, 150, 940, 930, 1060, WHITE, ap, 0.05)
        f.text('法律规定：两枚都当 100 用', W / 2, 1000, 48, 'serif_black', WHITE, ap, 'm', mode='O', t0=B(46), stag=0.03)
        aq = win(t, 50, 54, 0.3, 0.3)
        headline(f, '你会先花掉【哪一枚】？', 1220, 76, B(50), aq)
        # 流动：劣币进入流通（右下），良币被收藏（左下的金库）
        af = win(t, 54, 72, 0.3, 0.4) * (1 - ab)
        if af > 0.003 or ab > 0:
            rng = np.random.default_rng(9)
            n = 140
            ph = rng.uniform(0, 1, n); lane = rng.uniform(-1, 1, n)
            u = ((t - B(54)) * 0.45 + ph) % 1.0
            # 劣币：从右侧硬币流向底部「流通」并四散
            x = 780 + lane * 60 + u * u * lane * 300; y = cy + 160 + u * 700
            f.dots(x, y, C(190, 175, 130), af * (1 - u) * 0.9, 1, 'E')
            f.soft(x, y, C(190, 175, 130), af * (1 - u) * 0.5, 5, 'E')
            # 良币：落入金库并停住
            u2 = np.clip((t - B(54)) * 0.5 - ph * 0.8, 0, 1)
            x2 = 300 + lane * 50; y2 = cy + 160 + (1 - (1 - u2) ** 3) * 560
            f.dots(x2, y2, GOLD, af * (u2 > 0) * 0.9, 1, 'E')
            f.soft(x2, y2, GOLD, af * (u2 > 0) * 0.6, 5, 'E')
            f.rrect(170, 1330, 430, 1460, 14, GOLD, af * 0.8, 2)
            f.text('收藏起来', 300, 1500, 36, 'sans_med', GOLD2, af, 'm', mode='O')
            f.text('花出去', 780, 1500, 36, 'sans_med', C(200, 185, 150), af, 'm', mode='O')
            if ab > 0:
                card(f, 90, 1040, 990, 1640, GOLD, ab, 0.12)
                f.text('「奸钱日繁，正钱日亡」', W / 2, 1160, 66, 'serif_black', GOLD2, ab, 'm', mode='O', glow=0.3)
                f.text('—— 西汉 · 贾谊《新书 · 铸钱》', W / 2, 1260, 34, 'serif_reg', SOFT, ab, 'm', mode='O')
                f.text('1558 · 格雷欣向英国女王进言', W / 2, 1400, 38, 'sans_med', WHITE, ab * eo((t - B(65)) / 0.3), 'm', mode='O')
                f.text('1965 · 美国含银硬币迅速退出流通', W / 2, 1490, 38, 'sans_med', WHITE, ab * eo((t - B(67)) / 0.3), 'm', mode='O')
        stamp(f, t, 47, W / 2, cy, a=win(t, 47, 54, 0.05, 0.3))
        headline(f, '劣币在流通，良币被藏起来', 1630, 60, B(57), win(t, 57, 62, 0.3, 0.3))
    # --- 前提
    a = win(t, 72, 80, 0.3, 0.4)
    if a > 0:
        body(f, '但格雷欣法则有个前提：', 520, 44, B(72), a, col=SOFT)
        headline(f, '法律强制【好坏同价】', 660, 80, B(73), a)
        headline(f, '今天，没人强制同价——', 900, 66, B(75), a, col=SOFT)
        rich(f, '为什么【劣币】还能赢？', 1040, 88, B(76.5), a, hlcol=LEMON, glow=0.4)


# ============================================================== 4 · 阿克洛夫与二手车
LEMON_MESH = None
def lemon_mesh():
    """柠檬形线框：两端带尖的椭球"""
    us = np.linspace(0, np.pi, 15); vs = np.linspace(0, 2 * np.pi, 25)
    rings = []
    for u in us[1:-1]:
        r = np.sin(u) ** 0.85 * 0.62
        rings.append(np.stack([np.cos(u) * 1.05 * np.ones_like(vs), r * np.cos(vs), r * np.sin(vs)], 1))
    mer = []
    for v in vs[:-1]:
        mer.append(np.stack([np.cos(us) * 1.05 + np.sign(np.cos(us)) * (np.abs(np.cos(us)) > .97) * 0.12,
                             np.sin(us) ** 0.85 * 0.62 * np.cos(v), np.sin(us) ** 0.85 * 0.62 * np.sin(v)], 1))
    return rings, mer

def car_mesh():
    prof = [(-2.0, 0.3), (-2.0, 0.72), (-1.75, 0.82), (-0.75, 0.9), (-0.25, 1.38), (0.95, 1.38), (1.55, 0.92), (2.0, 0.86),
            (2.0, 0.3), (1.68, 0.3), (1.62, 0.55), (1.25, 0.72), (0.88, 0.55), (0.82, 0.3), (-0.82, 0.3), (-0.88, 0.55),
            (-1.25, 0.72), (-1.62, 0.55), (-1.68, 0.3)]
    pr = np.array(prof)
    L = []
    for z in (-0.8, 0.8):
        L.append(np.c_[pr, np.full(len(pr), z)][list(range(len(pr))) + [0]])
        for wx in (-1.25, 1.25):
            ts = np.linspace(0, 2 * np.pi, 20)
            L.append(np.stack([wx + 0.36 * np.cos(ts), 0.36 + 0.36 * np.sin(ts), np.full(20, z)], 1))
    for (x, y) in [prof[i] for i in (1, 2, 3, 4, 5, 6, 7, 8)]:
        L.append(np.array([[x, y, -0.8], [x, y, 0.8]]))
    # 车窗
    win_ = np.array([(-0.62, 0.95), (-0.2, 1.3), (0.88, 1.3), (1.35, 0.95)])
    for z in (-0.81, 0.81):
        L.append(np.c_[win_, np.full(4, z)][[0, 1, 2, 3, 0]])
    return L
CAR = car_mesh()

def draw_car(f, cam, L, col, a, off=(0, 0, 0), th=2):
    if a <= 0.003: return
    for seg in L:
        x, y, z, s = cam.project(seg + np.array(off))
        f.poly(np.stack([x, y], 1), col, a, th)

@SCENE(80, 132)
def sc_lemons(f, t):
    # --- 阿克洛夫
    a = win(t, 80, 88, 0.2, 0.4)
    if a > 0:
        cam = Cam(yaw=(t - B(80)) * 0.6, pitch=0.35, dist=5, f=1000, cy=760)
        rings, mer = lemon_mesh()
        sc = eback((t - B(80)) / 0.6)
        for r in rings + mer:
            x, y, z, s_ = cam.project(r * 1.3 * sc)
            f.poly(np.stack([x, y], 1), LEMON, a * 0.7, 2)
        f.glow((W / 2, 760), 200, LEMON, a * 0.18, 'B')
        f.text('1970', W / 2, 330, 60, 'oswald', LEMON, a, 'm', mode='O', glow=0.4)
        headline(f, '阿克洛夫《柠檬市场》', 1080, 72, B(80.5), a)
        body(f, 'lemon：美国俚语，买到手才发现的问题车', 1180, 34, B(81.5), a, col=SOFT)
        body(f, '曾被三家顶级期刊拒稿：「太浅显」', 1330, 44, B(83), a, col=WHITE)
        headline(f, '31 年后，诺贝尔经济学奖', 1450, 60, B(85), a, grad=[GOLD2, GOLD])
        note(f, 'Akerlof, G. (1970). Quarterly Journal of Economics；2001 年诺贝尔经济学奖', 1600, B(85.5), a, 24)
    # --- 两辆车
    a = win(t, 88, 112, 0.3, 0.4)
    if a > 0:
        tt = t - B(88)
        fogk = eo((t - B(94)) / 0.8)
        exitp = ei(cl((t - B(100.5)) / 1.4))
        for j, (yy, col, n0, lab, res) in enumerate([(720, GOLD, 88, '好车 · 车主心理底价 10 万', 10),
                                                     (1180, LEMON, 90, '问题车 · 车主心理底价 5 万', 5)]):
            p = eo((t - B(n0)) / 0.5)
            cam = Cam(yaw=0.55 + 0.12 * math.sin(tt * 0.7 + j), pitch=0.12, dist=6.4, f=1000, cy=yy)
            c2 = lerpc(col, FOGC, fogk * 0.85 if t < B(100) else fogk * 0.85 * (1 - eo((t - B(100)) / 0.4)))
            dx = (-8 * exitp if j == 0 else 0)
            aa = a * p * (1 - exitp if j == 0 else 1)
            draw_car(f, cam, CAR, c2, aa * 0.9, (dx, -0.7, 0))
            f.glow((W / 2 + dx * 150, yy), 160, c2, aa * 0.12, 'B')
            ly = yy + 200
            f.text(lab, W / 2, ly, 40, 'sans_med', lerpc(c2, WHITE, 0.35), aa, 'm', mode='O')
            if j == 1 and t > B(104):     # 问题车复制
                for k in range(1, 3):
                    q = eo((t - B(104) - k * 0.3) / 0.5)
                    draw_car(f, cam, CAR, LEMON, a * q * 0.4, ((-1) ** k * 3.2 * q, -0.7, 2.5 * k))
        if fogk > 0:
            fg = fog(t * 1.6) * a * fogk * (1 - eo((t - B(100)) / 0.6))
            f.L += fg[..., None] * np.array(FOGC, np.float32) * 0.16
        ab = win(t, 94, 100, 0.3, 0.3)
        headline(f, '买家：看起来一模一样', 380, 64, B(94), ab)
        ap = win(t, 96, 100, 0.25, 0.3)
        if ap > 0:
            card(f, 200, 1490, 880, 1630, GOLD, ap, 0.18)
            f.text('只肯出均价  7.5 万', W / 2, 1560, 58, 'serif_black', GOLD2, ap, 'm', mode='O', glow=0.4)
        ae = win(t, 100, 108, 0.3, 0.3)
        body(f, '10 万的车卖 7.5 万？不卖了。', 380, 50, B(100), ae, col=GOLD2)
        body(f, '5 万的车卖 7.5 万？赚了！', 1560, 50, B(104), ae, col=LEMON)
        ag = win(t, 108, 112, 0.25, 0.35)
        headline(f, '好车开始离场', 380, 80, B(108), ag)
        body(f, '留下来的，问题车越来越多', 1560, 46, B(109), ag, col=LEMON)



    # --- 回到那三件事
    a = win(t, 112, 132, 0.3, 0.45)
    if a > 0:
        headline(f, '回到开头那三件事', 330, 66, B(112), a)
        for i, c in enumerate(CASES):
            n0 = 113.5 + i * 3
            p = eo((t - B(n0)) / 0.4)
            y = 560 + i * 270
            card(f, 80 + 40 * (1 - p), y - 110, 1000, y + 110, c[6], a * p, 0.07)
            f.text(c[3], 130, y - 52, 48, 'serif_black', WHITE, a * p, 'l', mode='O')
            f.text('看不见：' + c[7], 130, y + 12, 36, 'sans_med', lerpc(c[6], WHITE, 0.3), a * p, 'l', mode='O')
            f.text('结果：' + c[8], 130, y + 68, 34, 'sans_light', SOFT, a * eo((t - B(n0 + 1)) / 0.4), 'l', mode='O')
        ac = win(t, 124, 132, 0.3, 0.45)
        if ac > 0:
            f.L *= 1 - 0.6 * ac; f.E *= 1 - 0.6 * ac
            card(f, 60, 1330, 1020, 1660, GOLD, ac, 0.22)
            rich(f, '质量看不见，', 1410, 62, B(124), ac)
            rich(f, '好东西就【卖不出好价】。', 1510, 62, B(125.5), ac)
            body(f, '格雷欣靠法令，柠檬市场靠信息差', 1610, 34, B(128), ac, col=SOFT)


# ============================================================== 3b · 真相：为什么偷工减料能赢
COST = [  # (名称, 看得见?, 初始份额, 最终份额, 开始变化的拍) —— 自下而上：底层是看不见的，表面是看得见的
    ('原料品质', False, 30, 16, 148), ('安全冗余', False, 18, 7, 148.5), ('质量检测', False, 16, 6, 149), ('售后服务', False, 14, 9, 150),
    ('广告营销', True, 12, 24, 151), ('包装', True, 10, 18, 151.5)]

def cost_stack(f, t, a):
    """一件商品的成本柱：看不见的部分逐拍被压缩，看得见的部分越做越大"""
    x0, x1, base, k = 260, 520, 1250, 7.5
    y = base
    tot = 0
    for name, vis, v0, v1, n0 in COST:
        u = eio(cl((t - B(n0)) / 0.7))
        v = v0 + (v1 - v0) * u
        h = v * k
        col = GOLD if vis else C(110, 190, 255)
        p = eo((t - B(146.5)) / 0.5)
        f.fillpoly([(x0, y), (x1, y), (x1, y - h * p), (x0, y - h * p)], col, a * (0.55 if vis else 0.22), 'E' if vis else 'L')
        f.rrect(x0, y - h * p, x1, y, 4, col, a * 0.8 * p, 2)
        cut = u if not vis else 0
        lab = name + ('  ↑' if vis and u > 0.05 else ('  ↓' if cut > 0.05 else ''))
        f.text(lab, x1 + 40, y - h * p / 2, 36, 'sans_med', lerpc(col, WHITE, 0.3) if vis else lerpc(col, RED, cut * 0.8),
               a * p, 'l', mode='O')
        if cut > 0 and t < B(n0) + 0.5:
            f.glow((x1, y - h / 2), 30, RED, a * (1 - (t - B(n0)) / 0.5), 'B')
        y -= h * p
    # 左侧标注：看得见 / 看不见
    f.text('看得见', x0 - 30, y + 50, 32, 'serif_black', GOLD2, a * eo((t - B(147)) / 0.4), 'r', mode='O')
    f.text('看不见', x0 - 30, base - 60, 32, 'serif_black', C(130, 200, 255), a * eo((t - B(147)) / 0.4), 'r', mode='O')
    f.line((x0 - 10, base), (x0 - 10, y), SOFT, a * 0.3, 1)

@SCENE(132, 164)
def sc_truth(f, t):
    # --- 一道算术题
    a = win(t, 132, 146, 0.35, 0.4)
    if a > 0:
        body(f, '一道算术题', 320, 44, B(132), a, col=GOLD)
        base, k = 1300, 6.0
        for j, (cx, cost, col, name) in enumerate([(330, 80, GOLD, '认真做'), (750, 40, LEMON, '偷工减料')]):
            p = eo((t - B(132 + j)) / 0.5)
            hc = cost * k * p; hp = (100 - cost) * k * eo((t - B(135)) / 0.5)
            f.fillpoly([(cx - 110, base), (cx + 110, base), (cx + 110, base - hc), (cx - 110, base - hc)], col, a * 0.18, 'L')
            f.rrect(cx - 110, base - hc, cx + 110, base, 6, col, a * 0.6 * p, 2)
            f.text('成本 %d' % cost, cx, base - hc / 2, 40, 'sans_med', SOFT, a * p, 'm', mode='O')
            if hp > 1:
                f.fillpoly([(cx - 110, base - hc), (cx + 110, base - hc), (cx + 110, base - hc - hp), (cx - 110, base - hc - hp)], col, a * 0.6, 'E')
                f.text('毛利 %d' % (100 - cost), cx, base - 600 - 60, 60, 'sans_black', col, a * eo((t - B(135.5)) / 0.4), 'm', mode='O', glow=0.5)
            f.text(name, cx, base + 50, 44, 'serif_black', col, a * p, 'm', mode='O')
        gy = base - 100 * k
        f.line((150, gy), (930, gy), WHITE, a * 0.5 * eo((t - B(134)) / 0.4), 2)
        f.text('同样卖 100', 540, gy - 150, 34, 'sans_med', WHITE, a * eo((t - B(134)) / 0.4), 'm', mode='O')
        body(f, '多赚的 40 → 广告 · 渠道 · 打价格战', 1480, 42, B(137), a, col=WHITE)
        headline(f, '越敢牺牲质量，越有钱扩张', 1590, 58, B(139), a, col=LEMON)
    # --- 成本结构：先砍掉的，永远是看不见的部分
    a = win(t, 146, 160, 0.3, 0.4)
    if a > 0:
        headline(f, '成本从哪里省？', 330, 76, B(146), a)
        cost_stack(f, t, a)
        rich(f, '看得见的越来越【好】，', 1400, 66, B(155), a)
        rich(f, '看不见的越来越【差】。', 1510, 66, B(156.5), a, hlcol=RED)
    a = win(t, 160, 164, 0.25, 0.3)
    if a > 0:
        headline(f, '一个健康的市场，', 820, 76, B(160), a)
        headline(f, '会怎样一步步【变坏】？', 950, 76, B(161.5), a, hlcol=RED)


# ============================================================== 5 · 动态模拟：市场如何滑向柠檬市场
NR = 8
SIM_AVG, SIM_P, SIM_N = [], [], []
_present = np.ones(NM, bool)
MK_EXIT = np.full(NM, 99)
for k in range(NR):
    avg = 100 * MK_Q[_present].mean(); pk = 1.5 * avg
    SIM_AVG.append(avg); SIM_P.append(pk); SIM_N.append(_present.mean())
    leave = _present & (100 * MK_Q > pk)
    MK_EXIT[leave] = k
    _present &= ~leave
SIM_FINAL_N = _present.mean()

def sim_state(t, n0=164):
    """返回 (轮次 k, 每个卖家的离场进度 0..1)"""
    k = int(math.floor((t - B(n0)) / (4 * P)))
    k = max(0, min(k, NR - 1))
    st = B(n0) + MK_EXIT * 4 * P + 0.35 + MK_SEED * 1.1
    u = np.clip((t - st) / 1.3, 0, 1)
    u[MK_EXIT == 99] = 0
    return k, u

def exit_offsets(u):
    d = MK_P / np.linalg.norm(MK_P, axis=1, keepdims=True)
    e = ei(1) if False else None
    s = (u ** 1.6)[:, None]
    return d * s * 3.2 + np.array([0, 1, 0]) * s * 2.2

@SCENE(164, 200)
def sc_sim(f, t):
    a = win(t, 164, 200, 0.25, 0.12)
    if a <= 0: return
    k, u = sim_state(t)
    frz = eo((t - B(196)) / 0.3)            # 断拍：冻结 + 褪色
    tt = min(t, B(196) + (t - B(196)) * 0.15) if t > B(196) else t
    cam = Cam(yaw=0.6 + tt * 0.22, pitch=0.28, dist=3.4, f=1150, cy=860)
    alive = 1 - u
    offs = exit_offsets(u)
    col = MK_COL * (1 - frz * 0.7) + np.array(GREY, np.float32) * frz * 0.5
    x, y, z, al = draw_sphere(f, t, cam, a, col=col, alive=alive, size=1.3, glowk=0.5, offs=offs)
    # 离场拖尾
    mv = (u > 0.02) & (u < 0.98)
    if mv.any():
        for kk in range(1, 6):
            o2 = exit_offsets(np.clip(u - 0.03 * kk, 0, 1))
            x2, y2, z2, s2 = cam.project(MK_P[mv] + o2[mv])
            f.splat(x2, y2, MK_COL[mv], a * (1 - u[mv]) * (1 - kk / 6) * 0.8, 'E')
    # 顶部标题
    at = a * (1 - frz)
    headline(f, '模拟：一个看不清质量的市场', 300, 56, B(164), at)
    body(f, '买家分不出好坏，只按「平均质量」出价', 380, 34, B(165), at, col=SOFT)
    # 数据面板
    dt = t - B(164 + 4 * k)
    kick = math.exp(-dt / 0.15)
    f.text('第 %d 轮' % (k + 1), W / 2, 1270, 34, 'sans_med', GOLD, at, 'm', mode='O')
    cols3 = [(220, '买家出价', '%.0f' % SIM_P[k], GOLD2), (540, '平均质量', '%.0f' % SIM_AVG[k], CYAN),
             (860, '留下的卖家', '%.0f%%' % (100 * (1 - (u > 0.5).mean())), WHITE)]
    for (cx, lab, val, c) in cols3:
        f.text(lab, cx, 1340, 30, 'sans_light', SOFT, at, 'm', mode='O')
        f.text(val, cx, 1420 - 10 * kick, 86 + 10 * kick * (cx < 400), 'oswald', c, at, 'm', mode='O', glow=0.5)
    # 曲线：出价（金）与平均质量（青）逐轮下降
    gx0, gx1, gy0, gy1 = 160, 920, 1500, 1640
    f.line((gx0, gy1), (gx1, gy1), GREY, at * 0.4, 1)
    pr = cl((t - B(164)) / (4 * P * NR))
    for arr, c in [(SIM_P, GOLD), (SIM_AVG, CYAN)]:
        pts = [(gx0 + (gx1 - gx0) * i / (NR - 1), gy1 - (gy1 - gy0) * v / 80) for i, v in enumerate(arr[:k + 1])]
        if len(pts) > 1: f.poly(pts, c, at * 0.9, 3)
        for (px, py) in pts: f.glow((px, py), 5, c, at, 'E')
    note(f, '设定：卖家底价 = 质量，买家估值 = 1.5 × 质量（阿克洛夫，1970）', 1700, B(166), at, 23)
    # 断拍文字
    ab = win(t, 196, 200, 0.2, 0.12)
    if ab > 0:
        f.L *= 1 - 0.5 * ab; f.E *= 1 - 0.5 * ab
        headline(f, '好车不是被坏车打败的，', 1250, 70, B(196), ab)
        headline(f, '是被「看不见」淘汰的。', 1380, 70, B(197.5), ab, grad=[GOLD2, GOLD])


# ============================================================== 6 · 真凶 · 恶性循环 · 信任崩塌
CYC = ['信息不对称', '看不清质量', '优质无溢价', '好卖家退出', '平均质量下降', '信任崩塌']

@SCENE(200, 232)
def sc_cycle(f, t):
    a = win(t, 200, 204, 0.05, 0.3)
    if a > 0:
        dt = t - B(200)
        burst(f, t, B(200), W / 2, 900, [RED, GOLD, WHITE], seed=4, n=700, speed=1500)
        body(f, '真凶', 720, 54, B(200), a, col=SOFT)
        sc = 1 + 0.2 * math.exp(-dt / 0.2)
        headline(f, '信息不对称', 880, int(150 * sc), B(200), a, grad=[WHITE, C(255, 140, 140), RED], glow=0.6, stag=0.04)
        body(f, '卖家知道，买家不知道', 1060, 48, B(201), a, col=WHITE)
    # --- 恶性循环
    a = win(t, 204, 216, 0.2, 0.05)
    cx, cy, R = W / 2, 940, 250
    if a > 0:
        spin = ei(cl((t - B(210)) / (B(216) - B(210)))) * 5.0
        red = cl((t - B(210)) / (B(216) - B(210)))
        base = -math.pi / 2 + spin * 1.2
        ring_col = lerpc(GOLD, RED, red)
        f.circle((cx, cy), R, ring_col, a * 0.5, 2)
        # 环上流动的粒子
        n = 220
        ang = np.linspace(0, 2 * np.pi, n, endpoint=False) + (t - B(204)) * (1.2 + 6 * red)
        f.dots(cx + R * np.cos(ang), cy + R * np.sin(ang), ring_col, a * (0.3 + 0.4 * (np.sin(ang * 3) > 0)), 1, 'E')
        for i, lab in enumerate(CYC):
            th = base + i * 2 * math.pi / 6
            px, py = cx + R * math.cos(th), cy + R * math.sin(th)
            on = eo((t - B(204 + i)) / 0.25)
            kick = math.exp(-(t - B(204 + i)) / 0.15) if t >= B(204 + i) else 0
            c = lerpc(GOLD, RED, max(red, i / 10))
            f.glow((px, py), 16 + 20 * kick, c, a * on, 'E')
            f.glow((px, py), 50, c, a * on * 0.4, 'B')
            lx, ly = cx + (R + 70) * math.cos(th), cy + (R + 70) * math.sin(th)
            anc = 'm' if abs(math.cos(th)) < 0.3 else ('l' if math.cos(th) > 0 else 'r')
            lx = lx if anc == 'm' else lx + (-30 if anc == 'l' else 30)
            ly = ly + (math.sin(th) * 20)
            f.text(lab, lx, ly, 34, 'sans_med', WHITE, a * on * (1 - 0.6 * red), anc, mode='O')
            # 箭头（沿圆弧到下一个节点）
            if t > B(204 + i) + 0.2:
                th2 = th + 2 * math.pi / 6
                q = eo((t - B(204 + i) - 0.2) / 0.4)
                ts = np.linspace(th + 0.16, th + 0.16 + (th2 - th - 0.32) * q, 20)
                f.poly(np.stack([cx + R * np.cos(ts), cy + R * np.sin(ts)], 1), c, a * on * 0.9, 4)
        headline(f, '恶性循环', cy - 10, 84, B(206), a * (1 - red * 0.3), col=lerpc(WHITE, RED, red))
        body(f, '越转越快', cy + 80, 40, B(211), a, col=RED)
        headline(f, '逆向选择', 330, 64, B(204), a)
    # --- 崩塌
    a = win(t, 216, 232, 0.02, 0.15)
    if a > 0:
        dt = t - B(216)
        rng = np.random.default_rng(12)
        for j in range(36):    # 碎片
            th = j / 36 * 2 * math.pi + rng.uniform(-0.05, 0.05)
            v = rng.uniform(300, 900); sp = rng.uniform(-3, 3)
            d = v * (1 - math.exp(-1.8 * dt)) / 1.8
            px, py = cx + (R + d) * math.cos(th), cy + (R + d) * math.sin(th) + 120 * dt * dt
            ts = np.linspace(th - 0.08, th + 0.08, 6) + sp * dt * 0.2
            pts = np.stack([px - R * math.cos(th) + R * np.cos(ts), py - R * math.sin(th) + R * np.sin(ts)], 1)
            f.poly(pts, RED, a * max(0, 1 - dt / 3), 3)
        burst(f, t, B(216), cx, cy, [RED, C(255, 120, 90), GOLD], seed=8, n=900, speed=1800, life=2.2)
        headline(f, '信任崩塌', 900, 140, B(216), a, grad=[WHITE, RED], glow=0.6, stag=0.06)
        body(f, '最后，连好东西也没人信了', 1060, 50, B(218), a, col=WHITE)
        ac = win(t, 221, 232, 0.3, 0.6)
        if ac > 0:
            card(f, 100, 1200, 980, 1580, RED, ac, 0.07)
            f.text('信任的代价', 150, 1270, 36, 'sans_med', RED, ac, 'l', mode='O')
            f.text('一车「甲醛白菜」被曝光，', 150, 1360, 44, 'sans_med', WHITE, ac, 'l', mode='O')
            f.text('全国白菜都要专项抽检', 150, 1450, 54, 'serif_black', GOLD2, ac * eo((t - B(222.5)) / 0.3), 'l', mode='O')
            f.text('坏的一车，连累所有诚实的菜农', 150, 1530, 34, 'sans_light', SOFT, ac * eo((t - B(224)) / 0.3), 'l', mode='O')


# ============================================================== 7 · 第一性原理（音乐落入空白）
@SCENE(232, 268)
def sc_first(f, t):
    a = win(t, 232, 242, 0.2, 0.4)
    if a > 0:
        # 心跳光环
        bp = math.exp(-((t - B(232)) % (2 * P)) / 0.18)
        f.circle((W / 2, 960), 360 + 30 * bp, GOLD, a * 0.18 * bp, 2)
        headline(f, '没有人做错决定。', 760, 84, B(232), a)
        headline(f, '每个人，都很理性。', 900, 84, B(234.5), a)
        headline(f, '合在一起，却杀死了市场。', 1100, 70, B(237), a, grad=[GOLD2, GOLD])
    # --- 不等式
    a = win(t, 242, 254, 0.3, 0.4)
    if a > 0:
        tilt = 0.32 * eo((t - B(243)) / 0.8)
        cx, cy = W / 2, 900
        L = 330
        lx, ly = cx - L * math.cos(tilt), cy + L * math.sin(tilt)
        rx, ry = cx + L * math.cos(tilt), cy - L * math.sin(tilt)
        f.line((cx, cy), (cx, cy + 260), SOFT, a * 0.7, 3)
        f.line((lx, ly), (rx, ry), SOFT, a * 0.9, 4)
        f.glow((cx, cy), 10, WHITE, a, 'E')
        for (px, py, lab, c) in [(lx, ly, '作假收益', LEMON), (rx, ry, '被抓概率 × 代价', CYAN)]:
            f.line((px, py), (px - 90, py + 130), c, a * 0.6, 2); f.line((px, py), (px + 90, py + 130), c, a * 0.6, 2)
            f.arc((px, py + 130), 110, 0, math.pi, c, a * 0.9, 3)
            f.text(lab, px, py + 290, 38, 'sans_med', c, a, 'm', mode='O')
        headline(f, '当作假收益 ＞ 被抓概率 × 代价', 470, 54, B(242), a)
        headline(f, '坏行为就会自我复制', 1450, 76, B(245), a, col=LEMON)
    # --- 劣币会传染
    a = win(t, 254, 268, 0.3, 0.15)
    if a > 0:
        nx, ny = 12, 16
        rng = np.random.default_rng(42)
        seeds = [(3, 4), (8, 11), (5, 13)]
        prog = cl((t - B(255)) / (B(265) - B(255))) * 14
        for ix in range(nx):
            for iy in range(ny):
                d = min(math.hypot(ix - sx, iy - sy) for sx, sy in seeds) + rng.uniform(0, 1.5)
                turn = cl(prog - d)
                x, y = 160 + ix * 69, 560 + iy * 52
                col = lerpc(GOLD, LEMON, turn)
                f.glow((x, y), 5, col, a * (0.8 - 0.3 * turn), 'E')
                f.glow((x, y), 14, col, a * 0.18, 'B')
        headline(f, '当诚实吃亏，', 380, 72, B(255), a)
        headline(f, '诚实的人，也会动摇。', 1460, 72, B(258), a, col=SOFT)
        rich(f, '劣币，会【传染】。', 1600, 92, B(261), a, hlcol=LEMON, glow=0.5)
    implode(f, t, B(264), B(268), W / 2, 960, [GOLD, GOLD2, WHITE], 0.7, seed=21, n=700)


# ============================================================== 8 · 破局：改变激励
def slider(f, y, lab, v0, v1, fmt, n0, a, sub, col):
    p = eo((t_now[0] - B(n0)) / 0.6) if t_now[0] >= B(n0) else 0
    v = v0 + (v1 - v0) * p
    f.text(lab, 150, y - 38, 38, 'sans_med', WHITE, a, 'l', mode='O')
    f.text(fmt.format(v), 930, y - 38, 44, 'oswald', col, a, 'r', mode='O', glow=0.4 * p)
    f.line((150, y + 14), (930, y + 14), GREY, a * 0.5, 2)
    kx = 150 + 780 * (0.25 + 0.5 * p)
    f.line((150, y + 14), (kx, y + 14), col, a, 4)
    f.glow((kx, y + 14), 10, col, a, 'E'); f.glow((kx, y + 14), 30, col, a * (0.3 + 0.7 * math.exp(-max(0, t_now[0] - B(n0)) / 0.3) * (p > 0)), 'B')
    f.text(sub, 150, y + 60, 28, 'sans_light', SOFT, a * 0.9, 'l', mode='O')
    return v

t_now = [0.0]

@SCENE(268, 300)
def sc_fix(f, t):
    t_now[0] = t
    a = win(t, 268, 276, 0.05, 0.4)
    if a > 0:
        dt = t - B(268)
        burst(f, t, B(268), W / 2, 900, [GOLD, GOLD2, WHITE, CYAN], seed=31, n=900, speed=1700)
        god_rays(f, t, W / 2, 960, GOLD, a * (0.5 + 0.8 * math.exp(-dt / 0.6)))
        headline(f, '问题不在人心，', 780, 84, B(268), a)
        headline(f, '在激励。', 960, int(170 * (1 + 0.15 * math.exp(-max(dt - P * 2, 0) / 0.2))), B(270), a, grad=[GOLD2, GOLD, GOLDD], glow=0.7, stag=0.08)
        body(f, '怎样让好东西活下来？', 1180, 54, B(272), a, col=WHITE)
        body(f, '不是呼吁讲良心，而是让诚实更赚钱', 1270, 40, B(273.5), a, col=GOLD2)
    a = win(t, 276, 300, 0.35, 0.4)
    if a <= 0: return
    ag = win(t, 296, 300, 0.05, 0.4)
    a0 = a
    a = a * (1 - 0.85 * ag)
    headline(f, '设计一个「良币胜出」的市场', 310, 56, B(276), a)
    pa = eo((t - B(276)) / 0.5)
    prem = 20 + 10 * eo((t - B(284)) / 0.6) * (t >= B(284))
    prob = 0.2 + 0.2 * eo((t - B(288)) / 0.6) * (t >= B(288))
    fine = 50 + 50 * eo((t - B(292)) / 0.6) * (t >= B(292))
    bad = 60 - prob * fine; good = 20 + prem
    for (x0, x1, col, ttl, form, val, n0) in [(80, 520, LEMON, '偷工减料', '60 − 查处概率 × 罚金', bad, 276),
                                              (560, 1000, GOLD, '认真做好', '20 + 质量溢价', good, 277)]:
        p = eo((t - B(n0)) / 0.45)
        win_ = (good > bad + 0.5) if col == GOLD else (bad > good + 0.5)
        card(f, x0, 400, x1, 880, col, a * p, 0.1 if win_ else 0.04, th=3 if win_ else 2)
        cx = (x0 + x1) / 2
        f.text(ttl, cx, 470, 52, 'serif_black', col, a * p, 'm', mode='O')
        f.text(form, cx, 545, 30, 'sans_light', SOFT, a * p, 'm', mode='O')
        f.text('%.0f' % val, cx, 720, 170, 'oswald', lerpc(col, WHITE, 0.25), a * p, 'm', mode='O', glow=0.6 if win_ else 0.15)
        f.text('预期收益', cx, 840, 28, 'sans_light', GREY, a * p, 'm', mode='O')
        if win_: f.glow((cx, 700), 160, col, a * 0.18, 'B')
    as_ = a * eo((t - B(280)) / 0.5)
    slider(f, 1010, '质量溢价', 20, 30, '{:.0f}', 284, as_, '信息透明 · 质量认证 · 品牌信誉', GOLD)
    slider(f, 1170, '查处概率', 20, 40, '{:.0f}%', 288, as_, '抽检 · 追溯 · 用户反馈', CYAN)
    slider(f, 1330, '罚金', 50, 100, '{:.0f}', 292, as_, '惩罚性赔偿：《食品安全法》第 148 条（价款十倍）', RED)
    d = good - bad
    if abs(d) < 0.5: txt, col = '两者持平', WHITE
    elif d < 0: txt, col = '劣币多赚 %.0f' % -d, LEMON
    else: txt, col = ('良币胜出 · 多赚 %.0f' % d), GOLD2
    av = a * eo((t - B(280)) / 0.5)
    card(f, 160, 1480, 920, 1600, col, av, 0.12)
    kick = max([math.exp(-(t - B(n)) / 0.2) for n in (284, 288, 292) if t >= B(n)] + [0])
    f.text(txt, W / 2, 1540, int(58 + 8 * kick), 'serif_black', col, av, 'm', mode='O', glow=0.4)
    note(f, '简化模型：未计入声誉损失、风险偏好等因素', 1680, B(281), a, 24)
    if ag > 0:
        f.L *= 1 - 0.6 * ag; f.E *= 1 - 0.6 * ag
        card(f, 60, 760, 1020, 1160, GOLD, ag, 0.2)
        headline(f, '不必消灭逐利，', 880, 72, B(296), ag)
        headline(f, '只需改变逐利的方向。', 1030, 72, B(297), ag, grad=[GOLD2, GOLD])


# ============================================================== 8b · 六种机制 + 证据 + 市场复苏
MECH = ['信息透明', '质量认证', '品牌信誉', '重复博弈', '用户反馈', '惩罚追责']

@SCENE(300, 324)
def sc_mech(f, t):
    a = win(t, 300, 316, 0.3, 0.4)
    if a > 0:
        cx, cy, R = W / 2, 760, 270
        rot = (t - B(300)) * 0.08
        for i, lab in enumerate(MECH):
            th = -math.pi / 2 + i * math.pi / 3 + rot
            th2 = th + math.pi / 3
            px, py = cx + R * math.cos(th), cy + R * math.sin(th)
            on = eo((t - B(300 + i)) / 0.3)
            kick = math.exp(-(t - B(300 + i)) / 0.15) if t >= B(300 + i) else 0
            c = [CYAN, GOLD, GOLD2, VIOLET, TEAL, RED][i]
            f.line((px, py), (cx + R * math.cos(th2), cy + R * math.sin(th2)), GOLD, a * on * 0.4, 2)
            f.line((px, py), (cx, cy), c, a * on * 0.18, 1)
            f.circle((px, py), 92 + 8 * kick, c, a * on, 3)
            f.rrect_fill(px - 88, py - 88, px + 88, py + 88, 88, c, a * on * 0.08, 'L')
            f.glow((px, py), 60, c, a * on * (0.2 + 0.4 * kick), 'B')
            f.text(lab, px, py, 34, 'sans_med', WHITE, a * on, 'm', mode='O')
        f.text('让质量', cx, cy - 34, 40, 'serif_black', GOLD2, a * eo((t - B(306)) / 0.4), 'm', mode='O')
        f.text('看得见 · 有回报 · 骗不起', cx, cy + 30, 28, 'sans_med', WHITE, a * eo((t - B(306.5)) / 0.4), 'm', mode='O')
        ev = [(306, '惩罚追责 · 「幽灵外卖」7 家平台被罚 35.97 亿元', '2026.6 起，平台须实地核验外卖商家资质'),
              (309, '用户反馈 · Yelp 评分每 +1 星', '独立餐厅营收 +5%～9%（Luca，2011）'),
              (312, '重复博弈 · 一锤子买卖靠骗', '回头客生意，靠的是信誉')]
        for j, (n0, l1, l2) in enumerate(ev):
            p = eo((t - B(n0)) / 0.4)
            y = 1170 + j * 165
            f.line((110, y - 30), (110, y + 50), GOLD, a * p, 3)
            f.text(l1, 140, y - 8, 36, 'sans_med', WHITE, a * p, 'l', mode='O')
            f.text(l2, 140, y + 44, 30, 'sans_light', SOFT, a * p, 'l', mode='O')
    # --- 复苏：让质量被看见
    a = win(t, 316, 324, 0.3, 0.4)
    if a > 0:
        p = cl((t - B(316)) / (B(321) - B(316)))
        cam = Cam(yaw=0.6 + t * 0.22, pitch=0.28, dist=3.4, f=1150, cy=860)
        ret = 1 - eio(np.clip(p * 1.6 - MK_SEED * 0.6, 0, 1))
        u = np.where(MK_EXIT < 99, ret, 0)
        draw_sphere(f, t, cam, a, alive=np.clip(1 - u * 0.9, 0, 1), size=1.3, glowk=0.6, offs=exit_offsets(u))
        sy = 300 + (1500 - 300) * eio(cl((t - B(316)) / (4 * P)))
        f.L[int(max(sy - 3, 0)):int(sy + 3)] += np.array(CYAN, np.float32) * 0.5 * a
        f.B[int(max(sy - 40, 0)):int(sy + 40)] += np.array(CYAN, np.float32) * 0.06 * a
        god_rays(f, t, W / 2, 860, C(150, 220, 255), a * eo((t - B(317)) / 1.0), seed=11)
        headline(f, '当质量能被看见，', 1340, 74, B(317), a)
        headline(f, '好东西就会回来。', 1470, 74, B(319), a, grad=[GOLD2, GOLD])


# ============================================================== 9 · 投资启示
def castle(f, cx, cy, s, col, a, t):
    pts = [(-1.6, 0), (-1.6, -1.3), (-1.4, -1.3), (-1.4, -1.15), (-1.2, -1.15), (-1.2, -1.3), (-1.0, -1.3), (-1.0, -0.8),
           (-0.45, -0.8), (-0.45, -1.7), (-0.25, -1.7), (-0.25, -1.55), (-0.08, -1.55), (-0.08, -1.7), (0.08, -1.7), (0.08, -1.55),
           (0.25, -1.55), (0.25, -1.7), (0.45, -1.7), (0.45, -0.8), (1.0, -0.8), (1.0, -1.3), (1.2, -1.3), (1.2, -1.15),
           (1.4, -1.15), (1.4, -1.3), (1.6, -1.3), (1.6, 0)]
    P2 = [(cx + x * s, cy + y * s) for x, y in pts]
    f.fillpoly(P2 + [P2[0]], col, a * 0.08, 'L')
    f.poly(P2, col, a, 3)
    f.arc((cx, cy), s * 0.28, math.pi, 2 * math.pi, col, a * 0.9, 3)
    ts = np.linspace(0, 2 * np.pi, 120)
    for k in range(3):
        rx, ry = s * (2.3 + 0.12 * k), s * (0.42 + 0.03 * k)
        wob = 0.02 * s * np.sin(ts * 9 + t * 3 + k)
        f.poly(np.stack([cx + rx * np.cos(ts), cy + 0.05 * s + ry * np.sin(ts) + wob], 1), CYAN, a * (0.7 - 0.2 * k), 2)
    f.glow((cx, cy + 0.05 * s), s * 1.2, CYAN, a * 0.12, 'B')

QUAD = [  # (象限, 出场拍, 标题, 说明, 举例, 颜色)
    ((-1, 1), 339, '柠檬陷阱', '做得再好，也被劣币驱逐', '如：部分装修、维修、二手交易', LEMON),
    ((-1, -1), 341, '拼信誉', '靠品牌、认证把质量「翻译」出来', '如：餐饮、母婴、医疗服务', CYAN),
    ((1, 1), 343, '拼效率', '质量透明，比的是真实成本', '如：标准化工业品', VIOLET),
    ((1, -1), 345, '良币行业', '越竞争越优秀，好公司拿走溢价', '如：高频复购的品牌消费品', GOLD),
]
GOLD_RAMP = [tuple(c / 255 for c in st[1]) for st in BR.GOLD_STOPS]   # 品牌金色渐变

# ============================================================== 9a · 「投资启示」金色转场
@SCENE(320, 329)
def sc_invest_title(f, t):
    implode(f, t, B(321), B(324), W / 2, 900, [GOLD, GOLD2, WHITE], 1.0, seed=57, n=1100, R0=1300)
    a = win(t, 324, 328.5, 0.02, 0.45)
    if a <= 0: return
    dt = t - B(324)
    f.L *= 0.6
    god_rays(f, t, W / 2, 900, GOLD, a * (0.7 + 1.2 * math.exp(-dt / 0.5)), n=120, seed=41, L=1700)
    burst(f, t, B(324), W / 2, 900, [GOLD, GOLD2, WHITE], seed=43, n=1300, speed=2000, life=2.0)
    # 上升的金色火花
    rng = np.random.default_rng(44)
    n = 260; ph = rng.uniform(0, 1, n); xs = rng.uniform(80, 1000, n)
    u = (dt * 0.35 + ph) % 1.0
    f.dots(xs + 20 * np.sin(u * 9 + ph * 20), 1500 - u * 1100, GOLD2, a * (1 - u) * 0.8, 1, 'E')
    sc = 1 + 0.35 * math.exp(-dt / 0.18)
    f.text('06', W / 2, 700, 64, 'oswald', GOLD, a * eo(dt / 0.4), 'm', mode='O', glow=0.6, track=0.2)
    sh = (dt - 0.5) / 1.1
    f.text('投资启示', W / 2, 900, int(176 * sc), 'serif_black', GOLD2, a, 'm', mode='O', grad=GOLD_RAMP, glow=0.9,
           t0=B(324), stag=0.06, dur=0.45, rise=0, kin=True, track=0.06, shine=sh if 0 <= sh <= 1 else None)
    p = eo((dt - 0.3) / 0.7)
    gline(f, 120, 960, 1050, GOLD, a, p, th=2)
    f.text('INVESTMENT  INSIGHT', W / 2, 1110, 32, 'corm', GOLD2, a * eo((dt - 0.5) / 0.6), 'm', mode='O', track=0.4)
    body(f, '劣币驱逐良币，对选股意味着什么？', 1220, 40, B(325.5), a, col=SOFT)


# ============================================================== 9 · 投资启示
@SCENE(328, 396)
def sc_invest(f, t):
    # --- 核心观点：先选行业
    a = win(t, 328.5, 337, 0.3, 0.45)
    if a > 0:
        body(f, '第一条，也是最重要的一条：', 560, 42, B(328.5), a, col=GOLD)
        headline(f, '先选行业，再选公司。', 690, 84, B(329.5), a)
        headline(f, '在柠檬市场里，', 920, 70, B(331.5), a, col=SOFT)
        rich(f, '做得再好，也会被【劣币驱逐】。', 1040, 70, B(332.5), a, hlcol=LEMON, glow=0.4)
        gline(f, 240, 840, 1180, GOLD, a * 0.8, (t - B(334)) / 0.5)
        body(f, '好公司要的是：质量分得出来、信息对称的赛道', 1260, 38, B(334), a, col=WHITE)
    # --- 行业四象限
    a = win(t, 337, 352, 0.3, 0.45)
    if a > 0:
        headline(f, '把行业放进这张图', 300, 62, B(337), a)
        cx, cy, R = W / 2, 900, 400
        p = eo((t - B(337.5)) / 0.6)
        f.line((cx - R * p, cy), (cx + R * p, cy), SOFT, a * 0.7, 2)
        f.line((cx, cy - R * p), (cx, cy + R * p), SOFT, a * 0.7, 2)
        for (x, y, s_, anc) in [(cx + R, cy + 46, '质量分得出 →', 'r'), (cx - R, cy + 46, '← 分不出', 'l'),
                                (cx + 16, cy - R + 20, '↑ 口碑能积累', 'l'), (cx + 16, cy + R - 20, '↓ 一锤子买卖', 'l')]:
            f.text(s_, x, y, 28, 'sans_med', SOFT, a * p, anc, mode='O')
        for (qx, qy), n0, ttl, dsc, ex, col in QUAD:
            q = eo((t - B(n0)) / 0.4)
            if q <= 0: continue
            x0 = cx + (16 if qx > 0 else -R); x1 = cx + (R if qx > 0 else -16)
            y0 = cy + (16 if qy > 0 else -R + 70); y1 = cy + (R - 70 if qy > 0 else -16)
            kick = math.exp(-(t - B(n0)) / 0.2)
            hi = 0.0
            if ttl == '良币行业' and t > B(347):
                hi = eo((t - B(347)) / 0.4) * (0.6 + 0.4 * math.sin((t - B(347)) * 6))
            if ttl == '柠檬陷阱' and t > B(347):
                q *= 1 - 0.5 * eo((t - B(347)) / 0.4)
            f.rrect_fill(x0, y0, x1, y1, 20, col, a * q * (0.08 + 0.15 * kick + 0.12 * hi), 'E')
            f.rrect(x0, y0, x1, y1, 20, col, a * q * (0.8 + 0.2 * hi), 2 + int(2 * hi))
            if hi > 0: f.glow(((x0 + x1) / 2, (y0 + y1) / 2), 160, col, a * 0.18 * hi, 'B')
            mx = (x0 + x1) / 2; my = (y0 + y1) / 2
            f.text(ttl, mx, my - 70, 46, 'serif_black', col, a * q, 'm', mode='O', glow=0.4)
            f.text(dsc, mx, my + 5, 24, 'sans_med', WHITE, a * q, 'm', mode='O')
            f.text(ex, mx, my + 60, 22, 'sans_light', SOFT, a * q, 'm', mode='O')
        rich(f, '优先下注右上角：【质量看得出，口碑能积累】', 1430, 46, B(347), a)
        body(f, '例外：能把质量「变得看得见」的公司，本身就是护城河', 1530, 34, B(349), a, col=CYAN)
        note(f, '示意：行业归类仅为举例，具体公司需单独验证', 1660, B(348), a, 23)
    # --- 柠檬行业的四个信号
    a = win(t, 352, 362, 0.3, 0.45)
    if a > 0:
        headline(f, '柠檬行业的四个信号', 320, 66, B(352), a, hlcol=LEMON)
        flags = ['买之前，看不出好坏', '一锤子买卖，顾客很少回头', '靠低价和营销抢份额', '违规成本低，维权难']
        for j, s_ in enumerate(flags):
            n0 = 353 + 1.5 * j
            p = eo((t - B(n0)) / 0.35)
            y = 520 + j * 170
            card(f, 100 + 40 * (1 - p), y - 65, 980, y + 65, LEMON, a * p, 0.06)
            f.glow((165, y), 12, RED, a * p, 'E'); f.glow((165, y), 30, RED, a * p * 0.4, 'B')
            f.text(s_, 210, y, 46, 'sans_med', WHITE, a * p, 'l', mode='O')
        rich(f, '中得越多，【越要远离】。', 1280, 70, B(359.5), a, hlcol=RED)
        body(f, '反过来找：可检测、可追溯、有评级、复购高', 1390, 40, B(360.5), a, col=GOLD2)
    # --- 看公司：三个问题
    a = win(t, 362, 375, 0.3, 0.45)
    if a > 0:
        headline(f, '看公司：再问三个问题', 300, 62, B(362), a)
        items = [('钱从哪来？', '靠创造客户价值，还是靠信息差？', GOLD),
                 ('管理层考核什么？', '只考核规模和份额，就会牺牲质量', CYAN),
                 ('数据能不能验证？', '复购率 · 毛利率稳定 · 投诉与召回 · 现金流', TEAL)]
        for j, (q1, q2, col) in enumerate(items):
            n0 = 363 + 3 * j
            p = eo((t - B(n0)) / 0.4)
            y = 520 + j * 260
            card(f, 80 + 40 * (1 - p), y - 100, 1000, y + 100, col, a * p, 0.07)
            f.text(str(j + 1), 140, y, 96, 'oswald', col, a * p, 'm', mode='O', glow=0.5)
            f.text(q1, 210, y - 34, 50, 'serif_black', WHITE, a * p, 'l', mode='O')
            f.text(q2, 210, y + 40, 32, 'sans_med', lerpc(col, WHITE, 0.4), a * eo((t - B(n0 + 0.8)) / 0.4), 'l', mode='O')
        rich(f, '份额增长 ≠ 【股东价值】', 1400, 70, B(372.5), a)
        body(f, '用低价和牺牲质量换来的份额，最终会还回去', 1500, 36, B(374), a, col=SOFT)
    # --- 两个案例：定价权 vs 品牌 ≠ 质量
    a = win(t, 375, 390, 0.3, 0.45)
    if a > 0:
        p1 = eo((t - B(375)) / 0.45)
        card(f, 70, 300, 1010, 760, GOLD, a * p1, 0.07)
        f.text('定价权 · 喜诗糖果', 120, 370, 48, 'serif_black', GOLD2, a * p1, 'l', mode='O', glow=0.3)
        f.text('1972 年，伯克希尔以 2500 万美元买下', 120, 450, 34, 'sans_med', WHITE, a * p1, 'l', mode='O')
        pv = cl((t - B(376)) / (4 * P))
        xs = np.linspace(560, 960, 40); g = np.linspace(0, 1, 40) ** 2.2
        mm = max(2, int(40 * eo(pv)))
        f.poly(list(zip(xs[:mm], 720 - 200 * g[:mm])), GOLD2, a * p1, 3)
        f.glow((xs[mm - 1], 720 - 200 * g[mm - 1]), 8, GOLD2, a * p1, 'E')
        f.text('%.1f' % (13.5 * eo(pv)), 120, 580, 96, 'oswald', GOLD2, a * p1, 'l', mode='O', glow=0.5)
        f.text('亿美元', 145 + text_width('%.1f' % (13.5 * eo(pv)), 'oswald', 96), 596, 40, 'sans_med', GOLD2, a * p1, 'l', mode='O')
        f.text('到 2007 年累计税前利润，追加资本仅 3200 万', 120, 700, 28, 'sans_light', SOFT, a * p1, 'l', mode='O')
        p2 = eo((t - B(379)) / 0.45)
        card(f, 70, 820, 1010, 1240, LEMON, a * p2, 0.07)
        f.text('品牌 ≠ 质量 · 卡夫亨氏', 120, 890, 48, 'serif_black', LEMON, a * p2, 'l', mode='O', glow=0.3)
        f.text('2019 年，品牌减值', 120, 980, 34, 'sans_med', WHITE, a * p2, 'l', mode='O')
        f.text('154 亿美元', 120, 1080, 84, 'sans_black', RED, a * p2, 'l', mode='O', glow=0.4)
        f.text('巴菲特：「我们为卡夫付了太高的价格」', 120, 1180, 30, 'sans_light', SOFT, a * p2, 'l', mode='O')
        drop = eo((t - B(380)) / 0.8)
        f.rrect(820, 950, 940, 1180, 8, GOLD, a * p2 * 0.3, 1)
        f.fillpoly([(820, 950 + 230 * 0.45 * drop), (940, 950 + 230 * 0.45 * drop), (940, 1180), (820, 1180)], LEMON, a * p2 * 0.4, 'E')
        headline(f, '真正的护城河：', 1360, 62, B(383), a, col=SOFT)
        headline(f, '让顾客认得出你的好，', 1470, 66, B(384.5), a)
        rich(f, '并且【愿意为它付钱】。', 1580, 66, B(386), a)
        note(f, '来源：伯克希尔 2007 年致股东信；Kraft Heinz 2019 年公告；CNBC 访谈', 1680, B(381), a, 22)


    # --- 投资结语
    a = win(t, 390, 396, 0.3, 0.4)
    if a > 0:
        god_rays(f, t, W / 2, 960, GOLD, a * 0.5, seed=61)
        headline(f, '选质量看得见的行业，', 840, 74, B(390), a)
        rich(f, '投让质量被看见的【公司】。', 980, 74, B(391.5), a, glow=0.5)


# ============================================================== 10 · 终章
@SCENE(396, 414)
def sc_epilogue(f, t):
    a = win(t, 396, 410, 0.4, 0.5)
    if a <= 0: return
    headline(f, '当好的行为得不到奖励，', 640, 66, B(396), a)
    headline(f, '坏的行为不必付出代价，', 760, 66, B(398.5), a)
    headline(f, '问题就不再只是个人的道德，', 920, 62, B(401), a, col=SOFT)
    headline(f, '而是整个系统的激励。', 1060, 82, B(403.5), a, grad=[GOLD2, GOLD, GOLDD], glow=0.6)
    gline(f, 300, 780, 1190, GOLD, a * 0.8, (t - B(406)) / 0.6)
    body(f, '有效的市场，不只需要竞争，', 1280, 42, B(407), a, col=WHITE)
    body(f, '还需要识别质量、奖励诚实、惩罚欺骗的制度', 1350, 40, B(408), a, col=WHITE)


# ============================================================== 11 · 片尾品牌动画（官方 logo + 品牌字体/金色/间距均取自 brand/）
END_LOGO_PX = 260
END_LOGO = load_logo(END_LOGO_PX)                     # (rgb, alpha) 官方 logo，预乘缩放
END_CY = 760

def _brand_text(title_px):
    """按 brand.build() 的同一套规则生成大号文字：主标题金色渐变 + 小字两端对齐到主标题等宽"""
    S = BR.SPEC
    k = title_px / S['title_px']
    from PIL import Image as _I, ImageDraw as _D
    f1 = BR._font(S['title_font'], int(S['title_px'] * k))
    im = _I.new('L', (int(f1.getlength(S['title']) + 40 * k), int(S['title_px'] * k * 1.6)), 0)
    _D.Draw(im).text((10 * k, int(S['title_px'] * k * 1.25)), S['title'], font=f1, fill=255, anchor='ls')
    t1 = BR._ink(im)
    f2 = BR._font(S['sub_font'], int(S['sub_px'] * k))
    nat = sum(f2.getlength(c) for c in S['sub'])
    tr = (t1.shape[1] - nat) / (len(S['sub']) - 1)
    w2 = int(nat + tr * len(S['sub']) + 20 * k)
    im = _I.new('L', (w2, int(S['sub_px'] * k * 2)), 0)
    d = _D.Draw(im); x = 5 * k
    for c in S['sub']:
        d.text((x, int(S['sub_px'] * k * 1.4)), c, font=f2, fill=255, anchor='ls'); x += f2.getlength(c) + tr
    t2 = BR._ink(im)[:, :t1.shape[1]]
    rgb1 = np.broadcast_to(BR._ramp(t1.shape[0], BR.GOLD_STOPS)[:, None, :], t1.shape + (3,)).astype(np.float32)
    rgb2 = np.broadcast_to(np.array(BR.SUB_GOLD, np.float32) / 255, t2.shape + (3,))
    return (rgb1, t1.astype(np.float32)), (rgb2, t2.astype(np.float32)), int(S['sub_gap_px'] * k)

END_T1, END_T2, END_GAP = _brand_text(118)

def _logo_targets(n=2600, seed=5):
    rgb, al = END_LOGO
    ys, xs = np.where(al > 0.35)
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(xs), n, replace=len(xs) < n)
    return xs[idx] - END_LOGO_PX / 2, ys[idx] - END_LOGO_PX / 2, rgb[ys[idx], xs[idx]]
LT_X, LT_Y, LT_C = _logo_targets()

def blit_over(f, rgb, al, x0, y0, a):
    h, w = al.shape
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if X1 <= X0 or Y1 <= Y0 or a <= 0.003: return
    f.over_rgb.append((rgb[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0], al[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0], X0, Y0, a))

def shimmer_rgb(rgb, al, u):
    """与 brand.Hud 同款流光：一条斜向高光带扫过文字"""
    if u is None or u < 0 or u > 1: return rgb
    h, w = al.shape
    xs = np.arange(w)[None, :] + np.arange(h)[:, None] * 0.6
    pos = -60 + (0.5 - 0.5 * math.cos(u * math.pi)) * (w + 120)
    band = np.exp(-((xs - pos) / (0.07 * w + 10)) ** 2)[..., None]
    return np.clip(rgb + band * 0.6, 0, 1.25)

@SCENE(408, 438)
def sc_end(f, t):
    if t < B(410.3): return
    # 粒子汇聚成 logo
    p = cl((t - B(410.3)) / (B(416) - B(410.3)))
    n = len(LT_X)
    rng = np.random.default_rng(77)
    ang = rng.uniform(0, 2 * np.pi, n); r0 = rng.uniform(380, 1100, n)
    sw = (1 - eio(p)) * 2.2
    ex = W / 2 + np.cos(ang + sw) * r0 * (1 - eio(p)) + LT_X * eio(p)
    ey = END_CY + np.sin(ang + sw) * r0 * (1 - eio(p)) * 1.4 + LT_Y * eio(p)
    pa = (0.25 + 0.75 * p) * (1 - eo((t - B(416)) / 0.6))
    cols = LT_C * eio(p) + np.array(GOLD2, np.float32) * (1 - eio(p))
    if pa > 0.003:
        dens = 1 / (1 + 6 * eio(p) ** 2)          # 汇聚时粒子密集，降低单粒子亮度避免过曝
        f.dots(ex, ey, cols, pa * 0.7 * dens, 1, 'E')
        f.soft(ex, ey, cols, pa * 0.35 * dens, 4, 'E')
    # 官方 logo 清晰浮现（重拍 B384）
    la = eo((t - B(415.6)) / 0.5)
    god_rays(f, t, W / 2, END_CY, C(110, 175, 255), la * 0.7 * (1 - eo((t - (DUR - 3)) / 2)), seed=19, L=1200)
    if la > 0:
        rgb, al = END_LOGO
        sc = 1 + 0.04 * math.exp(-max(0, t - B(416)) / 0.4)
        f.glow((W / 2, END_CY), 150, np.array(BR.SPEC['glow_rgb']) / 255, la * BR.SPEC['glow_strength'] * 1.2, 'B')
        blit_over(f, rgb, al, int(W / 2 - END_LOGO_PX / 2), int(END_CY - END_LOGO_PX / 2), la)
        if t >= B(416) and t < B(416) + 0.6:
            f.glow((W / 2, END_CY), 260, C(110, 175, 255), 0.5 * (1 - (t - B(416)) / 0.6), 'B')
    # 金色「巴芒价值」+ BUFFETT · MUNGER（重拍 B386 / B387 出现，B388 流光扫过）
    (r1, a1), (r2, a2), gap = END_T1, END_T2, END_GAP
    ty = END_CY + END_LOGO_PX // 2 + 90
    p1 = eo((t - B(418)) / 0.6)
    if p1 > 0:
        u = (t - B(420)) / BR.SPEC['shimmer_dur']
        rr = shimmer_rgb(r1, a1, u if 0 <= u <= 1 else None)
        blit_over(f, rr, a1, int(W / 2 - a1.shape[1] / 2), int(ty + 20 * (1 - p1)), p1)
        f.glow((W / 2, ty + a1.shape[0] / 2), 200, GOLD, p1 * 0.08, 'B')
    p2 = eo((t - B(419)) / 0.6)
    if p2 > 0:
        u = (t - B(420.3)) / BR.SPEC['shimmer_dur']
        rr = shimmer_rgb(r2, a2, u if 0 <= u <= 1 else None)
        blit_over(f, rr, a2, int(W / 2 - a2.shape[1] / 2), int(ty + a1.shape[0] + gap), p2)
    # 细金线引出关注语
    ly = ty + a1.shape[0] + gap + a2.shape[0] + 70
    gline(f, 190, 890, ly, C(214, 178, 112), 0.85, (t - B(422)) / 0.8)
    f.text('关注「巴芒价值」，传承大师智慧，领悟投资真谛', W / 2, ly + 70, 37, 'serif_reg',
           lerpc(np.array(BR.SUB_GOLD) / 255, (1, 1, 1), 0.35), 1.0, 'm', mode='O', t0=B(423), stag=0.035, dur=0.5, rise=12)


# ============================================================== 渲染
CUTS = [0, 8.3, 11.5, 14.7, 18, 32, 44, 54, 62, 72, 80, 88, 94, 100, 104, 112, 124, 132, 146, 160, 164, 196, 200, 204, 216,
        232, 242, 254, 268, 276, 296, 300, 316, 324, 328.5, 337, 352, 362, 375, 390, 396, 410, 999]

def camera_move(img, t):
    """镜头呼吸：每个镜头内缓慢推近 + 重击时的冲击缩放（HUD 不受影响，之后再画）"""
    k = max(i for i, c in enumerate(CUTS) if B(c) <= t) if t >= B(0) else 0
    a, b = B(CUTS[k]), B(CUTS[k + 1])
    u = cl((t - a) / max(b - a, 0.1))
    sc = 1.0 + 0.025 * eio(u)
    for n, kk, _ in IMPACTS:
        dt = t - B(n)
        if 0 <= dt < 0.6: sc += 0.05 * kk * math.exp(-dt / 0.12)
    sc += 0.004 * beat_pulse(t, 0.1) * ENERGY(t)
    if abs(sc - 1) < 1e-3: return img
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, sc)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

SCENES = []   # 在文件末尾汇总

def render(i):
    t = i / FPS
    f = Frame(t)
    bg = bg_at(t)
    draw_stars(f, t, 0.9)
    for s in SCENES:
        s(f, t)
    shockwaves(f, t)
    draw_chrome(f, t)
    img = finish(f, bg, bloom_k=1.0 + 0.25 * beat_pulse(t) * ENERGY(t), vignette=VIGNETTE, grain=GRAINS[i % 6])
    img = camera_move(img, t)
    fade = cl(t / 0.25) * (1 - eio((t - (DUR - 2.4)) / 2.4))
    draw_hud_post(img, t, 1.0)
    if fade < 1:
        img = (img.astype(np.float32) * fade).astype(np.uint8)
    return img
