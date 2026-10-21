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
                    (B(396), 1), (B(404), .3)])

# 重击：(拍号, 强度, 颜色)
IMPACTS = [(32, 1.0, GOLD), (80, 0.35, CYAN), (132, 0.6, GOLD), (164, 0.55, CYAN), (196, 0.7, RED),
           (216, 1.0, RED), (268, 1.0, GOLD), (296, 0.8, GOLD), (384, 0.9, C(110, 175, 255))]

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
    (B(324), (70, 55, 25), (25, 40, 90), .95), (B(364), (60, 45, 22), (30, 30, 70), .85),
    (B(380), (20, 30, 70), (25, 20, 50), .7), (DUR, (8, 10, 25), (10, 8, 20), .4)]

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
    for a, b in [(28, 32), (262, 268), (378, 384)]:
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

CHAPTERS = [(0, '', ''), (44, '01', '现场'), (80, '02', '线索'), (132, '03', '柠檬市场'), (232, '04', '第一性原理'),
            (268, '05', '破局'), (324, '06', '投资启示'), (364, '', ''), (999, '', '')]

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

def headline(f, s, y, size, t0, a=1.0, col=WHITE, grad=None, fnt='serif_black', glow=0.35, out=None, stag=0.05, track=0.02):
    f.text(s, W / 2, y, size, fnt, col, a, 'm', mode='O', grad=grad, glow=glow, t0=t0, stag=stag, dur=0.5, rise=26,
           out=out, track=track)

def body(f, s, y, size, t0, a=1.0, col=None, fnt='sans_med', x=W / 2, anchor='m', stag=0.025, out=None, track=0.03, glow=0.0):
    f.text(s, x, y, size, fnt, col or lerpc(WHITE, GREY, 0.12), a, anchor, mode='O', t0=t0, stag=stag, dur=0.4, rise=16,
           out=out, track=track, glow=glow)

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


# ============================================================== 0 · 序章：价格越来越低
def price_tag(f, cx, cy, w, h, col, a):
    """价签外形：右侧圆角矩形 + 左侧尖角 + 穿孔"""
    if a <= 0.003: return
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    tip = h * 0.42; r = 26
    pts = [(x0 + tip, y0)]
    for k in range(9):
        an = -math.pi / 2 + k / 8 * math.pi / 2; pts.append((x1 - r + r * math.cos(an), y0 + r + r * math.sin(an)))
    for k in range(9):
        an = k / 8 * math.pi / 2; pts.append((x1 - r + r * math.cos(an), y1 - r + r * math.sin(an)))
    pts += [(x0 + tip, y1), (x0, cy)]
    f.fillpoly(pts, col, a * 0.08, 'L')
    f.poly(pts, col, a * 0.9, 3, closed=True)
    f.circle((x0 + tip * 0.75, cy), 12, col, a * 0.8, 2)

@SCENE(0, 32)
def sc_hook(f, t):
    # --- 价格一路下跌
    a1 = win(t, -1, 8, 0.6, 0.45)
    if a1 > 0:
        headline(f, '价格，越来越低', 560, 78, B(0) + 0.15, a1)
        vals = ['99', '59', '29', '9.9']
        v, dt, k = tick_val(t, 0, vals, 2)
        cx, cy = W / 2 + 30, 900
        kick = math.exp(-dt / 0.12)
        price_tag(f, cx, cy, 600 + 30 * kick, 270 + 14 * kick, GOLD, a1)
        f.text('¥', cx - 120, cy + 6, 70, 'sans_med', GOLD2, a1 * eo(dt / 0.2), 'r', mode='O')
        f.text(v, cx + 50, cy - 20 * (1 - eo(dt / 0.25)), 170, 'oswald', GOLD2, a1 * eo(dt / 0.2), 'm', mode='O', glow=0.6)
        if k > 0 and dt < 0.25:   # 旧数字向上溢出
            f.text(vals[k - 1], cx + 50, cy - 90 * eo(dt / 0.25), 170, 'oswald', GOLD, a1 * (1 - dt / 0.25), 'm', mode='E')
        f.glow((cx, cy), 220, GOLD, a1 * (0.12 + 0.25 * kick), 'B')
        # 背后的下跌折线
        xs = np.linspace(110, 970, 40)
        ys = 1180 + np.cumsum(RNG.normal(0, 1, 40) * 0 + np.linspace(0, 16, 40))
        ys = 1130 + (xs - 110) / 860 * 330 + 22 * np.sin(xs * 0.03)
        p = cl((t - B(0)) / (B(7) - B(0)))
        m = max(2, int(40 * p))
        f.poly(np.stack([xs[:m], ys[:m]], 1), GOLD, a1 * 0.5, 2)
        f.glow((xs[m - 1], ys[m - 1]), 7, GOLD2, a1, 'E')
        body(f, '竞争，越来越激烈', 1560, 44, B(4), a1 * 0.9)
    # --- 好东西却越来越难买到
    a2 = win(t, 8, 14, 0.4, 0.4)
    if a2 > 0:
        cam = Cam(yaw=0.35 + 0.15 * (t - B(8)), pitch=0.18, dist=7.5, f=1150, cy=1220)
        # 货架上的发光方块：一个接一个熄灭
        k = 0
        for r in range(4):
            for c in range(3):
                X, Y = (c - 1) * 1.15, (1.5 - r) * 1.0
                off = B(8.5) + ((r * 3 + c) * 7 % 12) * 0.32
                on = 1 - eo((t - off) / 0.25) * 0.85
                flick = 1 if t < off else (0.4 + 0.6 * (math.sin(t * 60 + k) > 0)) * on
                cub = np.array([[X + dx * .32, Y + dy * .32, dz * .32] for dx in (-1, 1) for dy in (-1, 1) for dz in (-1, 1)])
                x, y, z, s = cam.project(cub)
                col = lerpc(GREY, GOLD, on)
                for i0, i1 in [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]:
                    f.line((x[i0], y[i0]), (x[i1], y[i1]), col, a2 * flick * 0.85, 2)
                f.glow((x.mean(), y.mean()), 50, GOLD, a2 * 0.25 * on * flick, 'B')
                k += 1
        headline(f, '好东西，', 560, 96, B(8), a2, grad=[GOLD2, GOLD])
        headline(f, '却越来越难买到？', 690, 96, B(10), a2)
    # --- 新闻：两起真实事件
    a3 = win(t, 14, 22, 0.3, 0.12)
    if a3 > 0:
        for j, (n0, yr, ttl, l1, src) in enumerate([
                (14, '2008', '三聚氰胺奶粉事件', '29.6 万名婴幼儿受害', '来源：卫生部通报（截至 2008 年底）'),
                (18, '2024', '罐车混装食用油', '卸完煤制油，不清洗就装食用油', '来源：新京报调查报道，2024 年 7 月')]):
            aj = a3 * eo((t - B(n0)) / 0.3)
            if aj <= 0: continue
            lift = -330 * eo((t - B(17.4)) / 0.45) if j == 0 else 0
            cy = 1010 + lift + 80 * (1 - eo((t - B(n0)) / 0.35))
            gl = math.exp(-(t - B(n0)) / 0.15)
            card(f, 110, cy - 150, 970, cy + 150, RED, aj, 0.09)
            f.text(yr, 160, cy - 70, 74, 'oswald', RED, aj, 'l', mode='O', glow=0.6)
            f.text(ttl, 360, cy - 70, 54, 'serif_black', WHITE, aj, 'l', mode='O')
            f.text(l1, 160, cy + 30, 42, 'sans_med', lerpc(WHITE, RED, 0.2), aj, 'l', mode='O')
            f.text(src, 160, cy + 100, 24, 'sans_light', GREY, aj * 0.9, 'l', mode='O')
            if gl > 0.05: f.ca = max(f.ca, 10 * gl)
        headline(f, '现实里的「好东西」去哪了？', 470, 58, B(14.5), a3 * 0.95, col=SOFT, fnt='serif_semi')
    # --- 反直觉问题
    a4 = win(t, 22, 31, 0.15, 0.5)
    if a4 > 0:
        headline(f, '认真做产品的，', 760, 80, B(22), a4, grad=[GOLD2, GOLD])
        headline(f, '被低价淘汰；', 870, 80, B(23), a4)
        headline(f, '偷工减料的，', 1060, 80, B(25), a4, col=LEMON)
        headline(f, '却活了下来？', 1170, 80, B(26), a4)
    implode(f, t, B(26), B(32), W / 2, 960, [GOLD, GOLD2, LEMON, WHITE], 0.9)


# ============================================================== 1 · 标题
@SCENE(32, 44)
def sc_title(f, t):
    a = win(t, 32, 44, 0.05, 0.5)
    if a <= 0: return
    dt = t - B(32)
    cam = Cam(yaw=0.4 + dt * 0.25, pitch=0.25, dist=3.0, f=1150, cy=960)
    R = 1.0 + 1.4 * math.exp(-dt / 0.5)
    draw_sphere(f, t, cam, a * 0.55, R=R, glowk=0.6, size=1.5)
    burst(f, t, B(32), W / 2, 960, [GOLD, GOLD2, LEMON, WHITE], seed=1, n=900, speed=1700)
    sc = 1 + 0.25 * math.exp(-dt / 0.25)
    headline(f, '谁杀死了', 770, int(118 * sc), B(32), a, stag=0.04)
    headline(f, '好东西？', 960, int(196 * sc), B(32) + 0.12, a, grad=[GOLD2, GOLD, GOLDD], glow=0.7, stag=0.07)
    gline(f, 240, 840, 1110, GOLD, a * 0.8, (t - B(34)) / 0.5)
    body(f, '劣币驱逐良币 · 柠檬市场 · 逆向选择', 1170, 40, B(34), a, col=GOLD2)
    f.text('WHO KILLED THE GOOD STUFF', W / 2, 1230, 28, 'corm', SOFT, a * 0.9 * eo((t - B(35)) / 0.6), 'm', track=0.32, mode='O')



# ============================================================== 2 · 现场：真实数据
@SCENE(44, 80)
def sc_data(f, t):
    # --- 物价：CPI 几乎不涨，PPI 持续为负
    a = win(t, 44, 52, 0.4, 0.4)
    if a > 0:
        headline(f, '2023—2025 · 中国物价', 330, 62, B(44), a)
        y0 = 1010; k = 95
        f.line((110, y0), (970, y0), SOFT, a * 0.5, 2)
        f.text('0', 92, y0, 26, 'oswald', GREY, a, 'r', mode='O')
        for j, (yr, cpi, ppi) in enumerate([('2023', 0.2, -3.0), ('2024', 0.2, -2.2), ('2025', 0.0, -2.6)]):
            n0 = 44 + 2 * j
            p = eo((t - B(n0)) / 0.45)
            cx = 260 + j * 280
            # CPI（青）
            h = max(cpi * k * p, 3 * p)
            f.fillpoly([(cx - 70, y0), (cx - 10, y0), (cx - 10, y0 - h), (cx - 70, y0 - h)], CYAN, a * 0.9, 'E')
            f.text(('+%.1f%%' % cpi) if cpi > 0 else '0.0%', cx - 40, y0 - h - 34, 32, 'oswald', CYAN, a * p, 'm', mode='O')
            # PPI（红）
            h2 = -ppi * k * p
            f.fillpoly([(cx + 10, y0), (cx + 70, y0), (cx + 70, y0 + h2), (cx + 10, y0 + h2)], RED, a * 0.85, 'E')
            f.text('%.1f%%' % ppi, cx + 40, y0 + h2 + 38, 32, 'oswald', RED, a * p, 'm', mode='O')
            f.text(yr, cx, 1440, 36, 'oswald', SOFT, a * p, 'm', mode='O')
        for (cx, col, lab) in [(300, CYAN, 'CPI  居民消费价格'), (680, RED, 'PPI  工业品出厂价格')]:
            f.fillpoly([(cx - 110, 575), (cx - 86, 575), (cx - 86, 599), (cx - 110, 599)], col, a, 'L')
            f.text(lab, cx - 72, 587, 30, 'sans_med', SOFT, a, 'l', mode='O')
        body(f, '物价几乎不涨，出厂价格一路下跌', 1560, 44, B(49), a, col=WHITE)
        note(f, '数据：国家统计局，年度同比', 1640, B(49), a)
    # --- 41 个月
    a = win(t, 52, 60, 0.3, 0.4)
    if a > 0:
        headline(f, 'PPI 同比连续下降', 470, 66, B(52), a)
        p = cl((t - B(52)) / (B(56) - B(52)))
        v = int(round(41 * eo(p)))
        kick = beat_pulse(t, 0.1) if p < 1 else 0
        f.text(str(v), W / 2 - 40, 790, 300 + 20 * kick, 'oswald', RED, a, 'm', mode='O', glow=0.7)
        f.text('个月', W / 2 + 190, 860, 64, 'serif_black', WHITE, a, 'l', mode='O')
        # 41 个格子：7 列 × 6 行
        for i in range(41):
            r, c = divmod(i, 7)
            x, y = 255 + c * 95, 1060 + r * 70
            on = v > i
            col = RED if on else GREY
            f.rrect_fill(x - 34, y - 22, x + 34, y + 22, 8, col, a * (0.55 if on else 0.08), 'E' if on else 'L')
        body(f, '2022.10 — 2026.2', 1560, 44, B(54), a, fnt='oswald', col=SOFT, track=0.08)
        note(f, '2026 年 3 月起 PPI 由负转正（国家统计局）', 1640, B(56), a)
    # --- 利润与政策
    a = win(t, 60, 68, 0.3, 0.4)
    if a > 0:
        p1 = eo((t - B(60)) / 0.4)
        card(f, 100, 480, 980, 880, RED, a * p1, 0.07)
        f.text('2024', 160, 560, 56, 'oswald', RED, a * p1, 'l', mode='O', glow=0.5)
        f.text('规模以上工业企业利润', 160, 650, 46, 'sans_med', WHITE, a * p1, 'l', mode='O')
        f.text('−3.3%', 160, 780, 130, 'oswald', RED, a * p1, 'l', mode='O', glow=0.6)
        f.text('连续第三年下降', 600, 790, 36, 'sans_med', SOFT, a * eo((t - B(61)) / 0.4), 'l', mode='O')
        p2 = eo((t - B(63)) / 0.4)
        card(f, 100, 960, 980, 1360, GOLD, a * p2, 0.06)
        f.text('2024.7', 160, 1040, 56, 'oswald', GOLD, a * p2, 'l', mode='O', glow=0.4)
        f.text('中央政治局会议首次提出', 160, 1130, 44, 'sans_med', WHITE, a * p2, 'l', mode='O')
        f.text('防止「内卷式」恶性竞争', 160, 1250, 66, 'serif_black', GOLD2, a * p2, 'l', mode='O', glow=0.3)
        note(f, '来源：国家统计局；新华社', 1640, B(64), a)
    # --- 但要说清楚
    a = win(t, 68, 74, 0.3, 0.35)
    if a > 0:
        body(f, '但必须说清楚：', 560, 46, B(68), a, col=SOFT)
        headline(f, '便宜 ≠ 劣质', 760, 108, B(69), a)
        headline(f, '价格战 ≠ 柠檬市场', 960, 96, B(71), a)
        body(f, '低价可能来自效率提升，也可能来自偷工减料', 1180, 38, B(72.5), a, col=SOFT)
    a = win(t, 74, 80, 0.3, 0.4)
    if a > 0:
        fg = fog(t) * a * eo((t - B(74)) / 1.2)
        f.L += fg[..., None] * np.array(FOGC, np.float32) * 0.12
        headline(f, '真正危险的，', 780, 86, B(74), a, col=SOFT)
        headline(f, '是你看不见的质量，', 920, 86, B(75.5), a)
        headline(f, '被悄悄拿走。', 1060, 86, B(77), a, grad=[GOLD2, GOLD])


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
        f.text(label, cx, cy - 8, int(R * 0.62), 'oswald', lerpc(col, WHITE, 0.4), a * cl((abs(c) - 0.35) * 2.5), 'm', mode='O')
    f.glow((cx, cy), R * 0.8, col, a * 0.25, 'B')

def person(f, cx, cy, s, col, a):
    f.circle((cx, cy - s * 0.35), s * 0.22, col, a, 3)
    f.arc((cx, cy + s * 0.45), s * 0.42, math.pi, 2 * math.pi, col, a, 3)

@SCENE(80, 132)
def sc_clues(f, t):
    # --- 嫌疑人
    a = win(t, 80, 92, 0.3, 0.4)
    if a > 0:
        headline(f, '凶手是谁？', 390, 96, B(80), a)
        sus = [('偷工减料的商家？', LEMON), ('只认低价的顾客？', CYAN), ('缺位的监管？', VIOLET)]
        for j, (s_, col) in enumerate(sus):
            n0 = 82 + 2 * j
            p = eo((t - B(n0)) / 0.35)
            dim = 1 - 0.55 * eo((t - B(88.5)) / 0.5)
            y = 690 + j * 210
            card(f, 120 + 60 * (1 - p), y - 80, 960, y + 80, col, a * p * dim, 0.06)
            person(f, 220, y + 4, 90, col, a * p * dim)
            f.text(s_, 320, y, 50, 'sans_med', WHITE, a * p * dim, 'l', mode='O')
            if t > B(88.5):
                q = eo((t - B(88.5) - j * 0.1) / 0.3)
                f.line((300, y), (300 + 600 * q, y), RED, a * 0.8, 3)
        body(f, '都有份，但都不是根源', 1420, 50, B(89), a, col=GOLD2)
    # --- 格雷欣：两枚硬币
    a = win(t, 92, 112, 0.35, 0.4)
    if a > 0:
        body(f, '线索一 · 一枚硬币的选择', 300, 40, B(92), a, col=GOLD)
        sp = (t - B(92)) * 1.4
        p = eo((t - B(92)) / 0.5)
        flow = cl((t - B(104)) / (B(108) - B(104)))
        # 硬币上移给流动动画让位
        cy = 640 if t < B(104) else 640 - 0 * flow
        coin(f, 300, cy, 150 * p, sp, GOLD, a * p, '100')
        coin(f, 780, cy, 150 * p, sp + 1.3, C(170, 150, 110), a * p, '80', dark=True)
        f.text('良币 · 含金 100', 300, cy + 210, 38, 'sans_med', GOLD2, a * p, 'm', mode='O')
        f.text('劣币 · 含金 80', 780, cy + 210, 38, 'sans_med', C(200, 185, 150), a * p, 'm', mode='O')
        ab = win(t, 108, 112, 0.3, 0.4)
        ap = win(t, 96, 112, 0.3, 0.4) * (1 - ab)
        card(f, 150, 940, 930, 1060, WHITE, ap, 0.05)
        f.text('法律规定：两枚都当 100 用', W / 2, 1000, 48, 'serif_black', WHITE, ap, 'm', mode='O', t0=B(96), stag=0.03)
        aq = win(t, 100, 104, 0.3, 0.3)
        headline(f, '你会先花掉哪一枚？', 1220, 72, B(100), aq, col=GOLD2)
        # 流动：劣币进入流通（右下），良币被收藏（左下的金库）
        af = win(t, 104, 112, 0.3, 0.4) * (1 - ab)
        if af > 0.003 or ab > 0:
            rng = np.random.default_rng(9)
            n = 140
            ph = rng.uniform(0, 1, n); lane = rng.uniform(-1, 1, n)
            u = ((t - B(104)) * 0.45 + ph) % 1.0
            # 劣币：从右侧硬币流向底部「流通」并四散
            x = 780 + lane * 60 + u * u * lane * 300; y = cy + 160 + u * 700
            f.dots(x, y, C(190, 175, 130), af * (1 - u) * 0.9, 1, 'E')
            f.soft(x, y, C(190, 175, 130), af * (1 - u) * 0.5, 5, 'E')
            # 良币：落入金库并停住
            u2 = np.clip((t - B(104)) * 0.5 - ph * 0.8, 0, 1)
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
                f.text('1558 · 格雷欣向英国女王进言', W / 2, 1400, 38, 'sans_med', WHITE, ab * eo((t - B(109)) / 0.3), 'm', mode='O')
                f.text('1965 · 美国含银硬币迅速退出流通', W / 2, 1490, 38, 'sans_med', WHITE, ab * eo((t - B(110)) / 0.3), 'm', mode='O')
    # --- 区分：格雷欣 vs 柠檬
    a = win(t, 112, 132, 0.35, 0.45)
    if a > 0:
        p1 = eo((t - B(112)) / 0.4); p2 = eo((t - B(116)) / 0.4)
        card(f, 90, 330, 990, 790, GOLD, a * p1, 0.07)
        f.text('格雷欣法则', 150, 420, 66, 'serif_black', GOLD2, a * p1, 'l', mode='O', glow=0.3)
        f.text('前提：法律强制好坏同价', 150, 540, 44, 'sans_med', WHITE, a * p1, 'l', mode='O')
        f.text('人们看得出好坏 → 好币被藏起来', 150, 640, 38, 'sans_light', SOFT, a * p1, 'l', mode='O')
        f.text('（若允许自由定价，良币会有溢价）', 150, 720, 32, 'sans_light', GREY, a * p1, 'l', mode='O')
        card(f, 90, 850, 990, 1310, LEMON, a * p2, 0.07)
        f.text('柠檬市场', 150, 940, 66, 'serif_black', LEMON, a * p2, 'l', mode='O', glow=0.3)
        f.text('前提：买家看不清质量', 150, 1060, 44, 'sans_med', WHITE, a * p2, 'l', mode='O')
        f.text('好坏只能卖均价 → 好货主动退出', 150, 1160, 38, 'sans_light', SOFT, a * p2, 'l', mode='O')
        f.text('（没有法令，只有信息差）', 150, 1240, 32, 'sans_light', GREY, a * p2, 'l', mode='O')
        headline(f, '一个靠法令，一个靠信息差', 1440, 58, B(120), a, col=WHITE)
        body(f, '今天说的「劣币驱逐良币」，多半是后者', 1560, 40, B(124), a, col=GOLD2)


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

@SCENE(132, 164)
def sc_lemons(f, t):
    # --- 阿克洛夫
    a = win(t, 132, 140, 0.2, 0.4)
    if a > 0:
        cam = Cam(yaw=(t - B(132)) * 0.6, pitch=0.35, dist=5, f=1000, cy=760)
        rings, mer = lemon_mesh()
        sc = eback((t - B(132)) / 0.6)
        for r in rings + mer:
            x, y, z, s_ = cam.project(r * 1.3 * sc)
            f.poly(np.stack([x, y], 1), LEMON, a * 0.7, 2)
        f.glow((W / 2, 760), 200, LEMON, a * 0.18, 'B')
        f.text('1970', W / 2, 330, 60, 'oswald', LEMON, a, 'm', mode='O', glow=0.4)
        headline(f, '阿克洛夫《柠檬市场》', 1080, 72, B(132.5), a)
        body(f, 'lemon：美国俚语，买到手才发现的问题车', 1180, 34, B(133.5), a, col=SOFT)
        body(f, '曾被三家顶级期刊拒稿：「太浅显」', 1330, 44, B(135), a, col=WHITE)
        headline(f, '31 年后，诺贝尔经济学奖', 1450, 60, B(137), a, grad=[GOLD2, GOLD])
        note(f, 'Akerlof, G. (1970). Quarterly Journal of Economics；2001 年诺贝尔经济学奖', 1600, B(137.5), a, 24)
    # --- 两辆车
    a = win(t, 140, 164, 0.3, 0.4)
    if a > 0:
        tt = t - B(140)
        fogk = eo((t - B(146)) / 0.8)
        exitp = ei(cl((t - B(152.5)) / 1.4))
        for j, (yy, col, n0, lab, res) in enumerate([(720, GOLD, 140, '好车 · 车主心理底价 10 万', 10),
                                                     (1180, LEMON, 142, '问题车 · 车主心理底价 5 万', 5)]):
            p = eo((t - B(n0)) / 0.5)
            cam = Cam(yaw=0.55 + 0.12 * math.sin(tt * 0.7 + j), pitch=0.12, dist=6.4, f=1000, cy=yy)
            c2 = lerpc(col, FOGC, fogk * 0.85 if t < B(152) else fogk * 0.85 * (1 - eo((t - B(152)) / 0.4)))
            dx = (-8 * exitp if j == 0 else 0)
            aa = a * p * (1 - exitp if j == 0 else 1)
            draw_car(f, cam, CAR, c2, aa * 0.9, (dx, -0.7, 0))
            f.glow((W / 2 + dx * 150, yy), 160, c2, aa * 0.12, 'B')
            ly = yy + 200
            f.text(lab, W / 2, ly, 40, 'sans_med', lerpc(c2, WHITE, 0.35), aa, 'm', mode='O')
            if j == 1 and t > B(156):     # 问题车复制
                for k in range(1, 3):
                    q = eo((t - B(156) - k * 0.3) / 0.5)
                    draw_car(f, cam, CAR, LEMON, a * q * 0.4, ((-1) ** k * 3.2 * q, -0.7, 2.5 * k))
        if fogk > 0:
            fg = fog(t * 1.6) * a * fogk * (1 - eo((t - B(152)) / 0.6))
            f.L += fg[..., None] * np.array(FOGC, np.float32) * 0.16
        ab = win(t, 146, 152, 0.3, 0.3)
        headline(f, '买家：看起来一模一样', 380, 64, B(146), ab)
        ap = win(t, 148, 152, 0.25, 0.3)
        if ap > 0:
            card(f, 200, 1490, 880, 1630, GOLD, ap, 0.18)
            f.text('只肯出均价  7.5 万', W / 2, 1560, 58, 'serif_black', GOLD2, ap, 'm', mode='O', glow=0.4)
        ae = win(t, 152, 160, 0.3, 0.3)
        body(f, '10 万的车卖 7.5 万？不卖了。', 380, 50, B(152), ae, col=GOLD2)
        body(f, '5 万的车卖 7.5 万？赚了！', 1560, 50, B(156), ae, col=LEMON)
        ag = win(t, 160, 164, 0.25, 0.35)
        headline(f, '好车开始离场', 380, 80, B(160), ag)
        body(f, '留下来的，问题车越来越多', 1560, 46, B(161), ag, col=LEMON)



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
            card(f, 100, 1200, 980, 1560, RED, ac, 0.07)
            f.text('真实的代价', 150, 1270, 36, 'sans_med', RED, ac, 'l', mode='O')
            f.text('2008 年后，内地家长赴港抢购奶粉', 150, 1360, 42, 'sans_med', WHITE, ac, 'l', mode='O')
            f.text('2013 · 香港「限奶令」', 150, 1450, 52, 'serif_black', GOLD2, ac, 'l', mode='O')
            f.text('离境每人每天限带 1.8 公斤（约 2 罐）', 150, 1520, 34, 'sans_light', SOFT, ac * eo((t - B(223)) / 0.3), 'l', mode='O')


# ============================================================== 7 · 第一性原理（音乐落入空白）
def melamine(f, cx, cy, sc, ang, a, t):
    ring = []; sub = []
    for i in range(6):
        th = math.pi / 2 + i * math.pi / 3
        ring.append((math.cos(th), math.sin(th), 'C' if i % 2 == 0 else 'N'))
        if i % 2 == 0: sub.append((2.0 * math.cos(th), 2.0 * math.sin(th), 'N', i))
    cam = Cam(yaw=ang, pitch=0.5 * math.sin(ang * 0.7), dist=7, f=1500, cx=cx, cy=cy)
    pts = np.array([[x, y, 0] for x, y, _ in ring] + [[x, y, 0] for x, y, _, _ in sub]) * sc
    X, Y, Z, S = cam.project(pts)
    for i in range(6):
        j = (i + 1) % 6
        f.line((X[i], Y[i]), (X[j], Y[j]), SOFT, a * 0.7, 3)
    for k, (_, _, _, i) in enumerate(sub):
        f.line((X[i], Y[i]), (X[6 + k], Y[6 + k]), SOFT, a * 0.7, 3)
    kinds = [r[2] for r in ring] + ['N'] * 3
    for i, kd in enumerate(kinds):
        c = CYAN if kd == 'N' else GREY
        r = 26 if kd == 'N' else 20
        f.glow((X[i], Y[i]), r * 0.6, c, a, 'E')
        f.glow((X[i], Y[i]), r * 1.6, c, a * 0.35, 'B')
        f.text(kd, X[i], Y[i] - 4, 30, 'oswald', WHITE, a * 0.95, 'm', mode='O')

@SCENE(232, 268)
def sc_first(f, t):
    a = win(t, 232, 240, 0.2, 0.4)
    if a > 0:
        # 心跳光环
        bp = math.exp(-((t - B(232)) % (2 * P)) / 0.18)
        f.circle((W / 2, 960), 360 + 30 * bp, GOLD, a * 0.18 * bp, 2)
        headline(f, '没有人做错决定。', 760, 84, B(232), a)
        headline(f, '每个人，都很理性。', 900, 84, B(234.5), a)
        headline(f, '合在一起，却杀死了市场。', 1100, 70, B(237), a, grad=[GOLD2, GOLD])
    # --- 一道算术题
    a = win(t, 240, 250, 0.35, 0.4)
    if a > 0:
        body(f, '一道算术题', 320, 44, B(240), a, col=GOLD)
        base, k = 1300, 6.0
        for j, (cx, cost, col, name) in enumerate([(330, 80, GOLD, '认真做'), (750, 40, LEMON, '偷工减料')]):
            p = eo((t - B(240 + j)) / 0.5)
            hc = cost * k * p; hp = (100 - cost) * k * eo((t - B(243)) / 0.5)
            f.fillpoly([(cx - 110, base), (cx + 110, base), (cx + 110, base - hc), (cx - 110, base - hc)], col, a * 0.18, 'L')
            f.rrect(cx - 110, base - hc, cx + 110, base, 6, col, a * 0.6 * p, 2)
            f.text('成本 %d' % cost, cx, base - hc / 2, 40, 'sans_med', SOFT, a * p, 'm', mode='O')
            if hp > 1:
                f.fillpoly([(cx - 110, base - hc), (cx + 110, base - hc), (cx + 110, base - hc - hp), (cx - 110, base - hc - hp)], col, a * 0.6, 'E')
                f.text('毛利 %d' % (100 - cost), cx, base - 600 - 60, 60, 'sans_black', col, a * eo((t - B(243.5)) / 0.4), 'm', mode='O', glow=0.5)
            f.text(name, cx, base + 50, 44, 'serif_black', col, a * p, 'm', mode='O')
        gy = base - 100 * k
        f.line((150, gy), (930, gy), WHITE, a * 0.5 * eo((t - B(242)) / 0.4), 2)
        f.text('同样卖 100', 540, gy - 150, 34, 'sans_med', WHITE, a * eo((t - B(242)) / 0.4), 'm', mode='O')
        body(f, '多赚的 40 → 广告 · 渠道 · 打价格战', 1480, 42, B(245), a, col=WHITE)
        headline(f, '越敢牺牲质量，越有钱扩张', 1590, 58, B(247), a, col=LEMON)
    # --- 古德哈特：三聚氰胺
    a = win(t, 250, 258, 0.3, 0.4)
    if a > 0:
        body(f, '当年，奶粉检测蛋白质', 360, 46, B(250), a, col=SOFT)
        headline(f, '主要看「含氮量」', 460, 76, B(250.5), a, col=CYAN)
        melamine(f, W / 2, 850, 1.0, (t - B(250)) * 0.5, a * eo((t - B(250)) / 0.6), t)
        body(f, '三聚氰胺：含氮约 66%，却不是蛋白质', 1150, 40, B(252.5), a, col=SOFT)
        headline(f, '于是有人往奶里加它。', 1290, 70, B(254), a, col=WHITE)
        headline(f, '考核什么，就得到什么。', 1460, 70, B(256), a, grad=[GOLD2, GOLD])
    # --- 不等式
    a = win(t, 258, 264, 0.3, 0.12)
    if a > 0:
        tilt = 0.32 * eo((t - B(259)) / 0.8)
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
        headline(f, '当作假收益 ＞ 被抓概率 × 代价', 470, 54, B(258), a)
        headline(f, '坏行为就会自我复制', 1450, 76, B(261), a, col=LEMON)
    # --- 芒格
    a = win(t, 264, 268, 0.15, 0.15)
    if a > 0:
        headline(f, '「给我看激励，', 820, 82, B(264), a)
        headline(f, '我就告诉你结果。」', 950, 82, B(265), a)
        body(f, '—— 查理 · 芒格', 1090, 40, B(266), a, col=GOLD2)
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
        ev = [(306, '用户反馈 · Yelp 评分每 +1 星', '独立餐厅营收 +5%～9%（Luca，2011）'),
              (309, '信息透明 · 洛杉矶 1998 年起公示卫生等级', '餐厅卫生检查得分显著上升（Jin & Leslie，2003）'),
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

@SCENE(324, 364)
def sc_invest(f, t):
    a = win(t, 324, 332, 0.3, 0.4)
    if a > 0:
        castle(f, W / 2, 900, 190 * eo((t - B(324)) / 0.6), GOLD, a, t)
        headline(f, '真正的护城河，', 380, 80, B(324), a)
        headline(f, '是让顾客认得出你的好，', 1200, 64, B(326), a)
        headline(f, '并且愿意为它多付钱。', 1310, 64, B(328), a, grad=[GOLD2, GOLD])
    a = win(t, 332, 342, 0.3, 0.4)
    if a > 0:
        body(f, '案例 · 喜诗糖果', 320, 40, B(332), a, col=GOLD)
        f.text('1972', 150, 450, 70, 'oswald', GOLD, a * eo((t - B(332)) / 0.4), 'l', mode='O', glow=0.4)
        f.text('伯克希尔以 2500 万美元买下', 150, 540, 42, 'sans_med', WHITE, a * eo((t - B(332.5)) / 0.4), 'l', mode='O')
        # 累计利润面积图
        p = cl((t - B(334)) / (4 * P))
        xs = np.linspace(150, 930, 60); g = np.linspace(0, 1, 60) ** 2.2
        m = max(2, int(60 * eo(p)))
        top = 1180 - 420 * g
        poly = [(xs[0], 1180)] + list(zip(xs[:m], top[:m])) + [(xs[m - 1], 1180)]
        f.fillpoly(poly, GOLD, a * 0.18, 'L')
        f.poly(list(zip(xs[:m], top[:m])), GOLD2, a, 3)
        f.glow((xs[m - 1], top[m - 1]), 8, GOLD2, a, 'E')
        f.line((150, 1180), (930, 1180), GREY, a * 0.5, 1)
        f.text('1972', 150, 1215, 26, 'oswald', GREY, a, 'l', mode='O'); f.text('2007', 930, 1215, 26, 'oswald', GREY, a, 'r', mode='O')
        v = 13.5 * eo(p)
        f.text('累计税前利润', 160, 680, 34, 'sans_light', SOFT, a * (p > 0), 'l', mode='O')
        f.text('%.1f' % v, 160, 770, 96, 'oswald', GOLD2, a * (p > 0), 'l', mode='O', glow=0.5)
        f.text('亿美元', 180 + text_width('%.1f' % v, 'oswald', 96), 785, 48, 'sans_med', GOLD2, a * (p > 0), 'l', mode='O')
        f.text('追加资本仅 3200 万', 930, 1290, 36, 'sans_med', CYAN, a * eo((t - B(336)) / 0.4), 'r', mode='O')
        card(f, 90, 1380, 990, 1600, GOLD, a * eo((t - B(338)) / 0.4), 0.08)
        f.text('「评估一家企业，最重要的是定价权。」', W / 2, 1460, 44, 'serif_black', GOLD2, a * eo((t - B(338)) / 0.4), 'm', mode='O')
        f.text('—— 巴菲特（2010）', W / 2, 1540, 32, 'serif_reg', SOFT, a * eo((t - B(339)) / 0.4), 'm', mode='O')
        note(f, '来源：伯克希尔 2007 年致股东信；美国金融危机调查委员会访谈', 1680, B(336), a, 23)
    a = win(t, 342, 350, 0.3, 0.4)
    if a > 0:
        headline(f, '但是：品牌 ≠ 质量', 380, 76, B(342), a, col=LEMON)
        p = eo((t - B(344)) / 0.8)
        top = 760 + 340 * 0.45 * p
        f.rrect(400, 760, 680, 1100, 6, GOLD, a * 0.3, 1)
        f.fillpoly([(400, top), (680, top), (680, 1100), (400, 1100)], GOLD, a * 0.2, 'L')
        f.fillpoly([(400, 760), (680, 760), (680, top), (400, top)], RED, a * 0.25 * (p > 0), 'E')
        f.text('2019 · 卡夫亨氏', W / 2, 540, 44, 'sans_med', WHITE, a * eo((t - B(344)) / 0.4), 'm', mode='O')
        f.text('品牌减值 154 亿美元', W / 2, 650, 64, 'serif_black', RED, a * eo((t - B(344.5)) / 0.4), 'm', mode='O', glow=0.4)
        body(f, '巴菲特：「我们为卡夫付了太高的价格」', 1200, 42, B(346), a, col=WHITE)
        headline(f, '护城河，必须用事实验证', 1360, 66, B(348), a, grad=[GOLD2, GOLD])
        note(f, '来源：Kraft Heinz 2019 年 2 月公告；CNBC 访谈', 1680, B(346), a, 23)
    a = win(t, 350, 364, 0.3, 0.45)
    if a > 0:
        headline(f, '识别「靠牺牲质量」的增长', 380, 62, B(350), a)
        items = ['降价，来自效率还是偷工？', '份额增长，伴随回报还是失血？', '顾客，会不会主动回头？', '毛利与现金流，经得起检验吗？']
        for j, s_ in enumerate(items):
            n0 = 352 + 3 * j
            p = eo((t - B(n0)) / 0.4)
            y = 620 + j * 230
            card(f, 100, y - 85, 980, y + 85, GOLD, a * p, 0.05)
            f.rrect(140, y - 30, 200, y + 30, 8, GOLD, a * p, 3)
            q = cl((t - B(n0) - 0.3) / 0.35)
            if q > 0:
                ck = [(152, y), (166, y + 16), (192, y - 20)]
                m1 = min(q * 2, 1); f.line(ck[0], (ck[0][0] + (ck[1][0] - ck[0][0]) * m1, ck[0][1] + (ck[1][1] - ck[0][1]) * m1), GOLD2, a, 4)
                if q > 0.5:
                    m2 = (q - 0.5) * 2; f.line(ck[1], (ck[1][0] + (ck[2][0] - ck[1][0]) * m2, ck[1][1] + (ck[2][1] - ck[1][1]) * m2), GOLD2, a, 4)
            f.text(s_, 230, y, 44, 'sans_med', WHITE, a * p, 'l', mode='O')
        body(f, '份额增长 ≠ 股东价值', 1580, 44, B(362), a, col=GOLD2)


# ============================================================== 10 · 终章
@SCENE(364, 382)
def sc_epilogue(f, t):
    a = win(t, 364, 378, 0.4, 0.5)
    if a <= 0: return
    headline(f, '当好的行为得不到奖励，', 640, 66, B(364), a)
    headline(f, '坏的行为不必付出代价，', 760, 66, B(366.5), a)
    headline(f, '问题就不再只是个人的道德，', 920, 62, B(369), a, col=SOFT)
    headline(f, '而是整个系统的激励。', 1060, 82, B(371.5), a, grad=[GOLD2, GOLD, GOLDD], glow=0.6)
    gline(f, 300, 780, 1190, GOLD, a * 0.8, (t - B(374)) / 0.6)
    body(f, '有效的市场，不只需要竞争，', 1280, 42, B(375), a, col=WHITE)
    body(f, '还需要识别质量、奖励诚实、惩罚欺骗的制度', 1350, 40, B(376), a, col=WHITE)


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

@SCENE(376, 406)
def sc_end(f, t):
    if t < B(378.3): return
    # 粒子汇聚成 logo
    p = cl((t - B(378.3)) / (B(384) - B(378.3)))
    n = len(LT_X)
    rng = np.random.default_rng(77)
    ang = rng.uniform(0, 2 * np.pi, n); r0 = rng.uniform(380, 1100, n)
    sw = (1 - eio(p)) * 2.2
    ex = W / 2 + np.cos(ang + sw) * r0 * (1 - eio(p)) + LT_X * eio(p)
    ey = END_CY + np.sin(ang + sw) * r0 * (1 - eio(p)) * 1.4 + LT_Y * eio(p)
    pa = (0.25 + 0.75 * p) * (1 - eo((t - B(384)) / 0.6))
    cols = LT_C * eio(p) + np.array(GOLD2, np.float32) * (1 - eio(p))
    if pa > 0.003:
        dens = 1 / (1 + 6 * eio(p) ** 2)          # 汇聚时粒子密集，降低单粒子亮度避免过曝
        f.dots(ex, ey, cols, pa * 0.7 * dens, 1, 'E')
        f.soft(ex, ey, cols, pa * 0.35 * dens, 4, 'E')
    # 官方 logo 清晰浮现（重拍 B384）
    la = eo((t - B(383.6)) / 0.5)
    if la > 0:
        rgb, al = END_LOGO
        sc = 1 + 0.04 * math.exp(-max(0, t - B(384)) / 0.4)
        f.glow((W / 2, END_CY), 150, np.array(BR.SPEC['glow_rgb']) / 255, la * BR.SPEC['glow_strength'] * 1.2, 'B')
        blit_over(f, rgb, al, int(W / 2 - END_LOGO_PX / 2), int(END_CY - END_LOGO_PX / 2), la)
        if t >= B(384) and t < B(384) + 0.6:
            f.glow((W / 2, END_CY), 260, C(110, 175, 255), 0.5 * (1 - (t - B(384)) / 0.6), 'B')
    # 金色「巴芒价值」+ BUFFETT · MUNGER（重拍 B386 / B387 出现，B388 流光扫过）
    (r1, a1), (r2, a2), gap = END_T1, END_T2, END_GAP
    ty = END_CY + END_LOGO_PX // 2 + 90
    p1 = eo((t - B(386)) / 0.6)
    if p1 > 0:
        u = (t - B(388)) / BR.SPEC['shimmer_dur']
        rr = shimmer_rgb(r1, a1, u if 0 <= u <= 1 else None)
        blit_over(f, rr, a1, int(W / 2 - a1.shape[1] / 2), int(ty + 20 * (1 - p1)), p1)
        f.glow((W / 2, ty + a1.shape[0] / 2), 200, GOLD, p1 * 0.08, 'B')
    p2 = eo((t - B(387)) / 0.6)
    if p2 > 0:
        u = (t - B(388.3)) / BR.SPEC['shimmer_dur']
        rr = shimmer_rgb(r2, a2, u if 0 <= u <= 1 else None)
        blit_over(f, rr, a2, int(W / 2 - a2.shape[1] / 2), int(ty + a1.shape[0] + gap), p2)
    # 细金线引出关注语
    ly = ty + a1.shape[0] + gap + a2.shape[0] + 70
    gline(f, 190, 890, ly, C(214, 178, 112), 0.85, (t - B(390)) / 0.8)
    f.text('关注「巴芒价值」，传承大师智慧，领悟投资真谛', W / 2, ly + 70, 37, 'serif_reg',
           lerpc(np.array(BR.SUB_GOLD) / 255, (1, 1, 1), 0.35), 1.0, 'm', mode='O', t0=B(391), stag=0.035, dur=0.5, rise=12)


# ============================================================== 渲染
CUTS = [0, 8, 14, 22, 32, 44, 52, 60, 68, 74, 80, 92, 112, 132, 140, 164, 196, 200, 204, 216, 232, 240, 250, 258, 264,
        268, 276, 296, 300, 316, 324, 332, 342, 350, 364, 378, 999]

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
    fade = cl(t / 0.8) * (1 - eio((t - (DUR - 2.4)) / 2.4))
    draw_hud_post(img, t, 1.0)
    if fade < 1:
        img = (img.astype(np.float32) * fade).astype(np.uint8)
    return img
