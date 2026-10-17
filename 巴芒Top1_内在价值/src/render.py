"""《内在价值：没有把握，就不知道它值多少》—— 巴芒精华库 Top 1 · 竖屏 1080×1920 动态图形短片。

画面时间全部取自 WORK/timeline.json（旁白逐句起止）和 WORK/music.json（重拍、片长、节拍）。
品牌：右上角全程 brand.Hud；片尾 logo 只用 brand/logo_baman.png（load_logo），
文字「巴芒价值 / BUFFETT · MUNGER」直接取自 brand/hud_lockup@4x.png 的文字区（官方预渲染，含品牌金色渐变），
颜色、光晕参数取自 brand.py 的 SPEC / GOLD_STOPS / SUB_GOLD。

用法：
  python3 src/render.py stills OUT_DIR t1 t2 ... WORK
  python3 src/render.py chunk FRAME_A FRAME_B OUT.mp4 WORK
"""
import json, math, os, sys
import numpy as np, cv2
from PIL import Image
from engine import *
from script import SOURCE_ZH, SOURCE_EN, DISCLOSE

REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'brand'))
import brand
from brand import Hud, load_logo, SPEC, GOLD_STOPS, SUB_GOLD

WORK = sys.argv[-1] if len(sys.argv) > 2 else os.path.join(HERE, '..', 'work')
TL = json.load(open(os.path.join(WORK, 'timeline.json')))['items']
MU = json.load(open(os.path.join(WORK, 'music.json')))
BEATS = np.array(MU['beats'])
HIT0 = MU['first_hit']          # 第一个重拍（巴菲特原话开始）
HIT = MU['hit']                 # 片尾重拍（「巴芒价值」出现）
DUR = MU['end']
NFR = int(round(DUR * FPS))
S = [it['start'] for it in TL]
E = [it['end'] for it in TL]

# ---------------------------------------------------------------- 品牌色（来自 brand.py）
GOLDS = [C(*c) for _, c in GOLD_STOPS]            # #FFF3C8 #FFD478 #E2A03C #FFD682
G_LIGHT, G_MAIN, G_DEEP = GOLDS[0], GOLDS[1], GOLDS[2]
G_GRAD = [GOLDS[0], GOLDS[1], GOLDS[3]]
SUBG = C(*SUB_GOLD)                               # #D6B270
BLUE = C(*SPEC['glow_rgb'])                       # logo 光晕蓝 (110,175,255)
WHITE = (1.0, 1.0, 1.0)
GREY = C(150, 160, 185)
DIM = C(95, 105, 130)
RED = C(235, 95, 85)
CX = W / 2

# ---------------------------------------------------------------- 段落时间
PARTS = []
for it in TL:
    if not PARTS or PARTS[-1][0] != it['part']:
        PARTS.append([it['part'], it['start'], it['end']])
    PARTS[-1][2] = it['end']
WIN = {}
for k, (p, a, b) in enumerate(PARTS):
    a0 = 0.0 if k == 0 else a - 0.45
    if p == 'dcf': a0 = HIT0 - 0.05
    WIN[p] = [a0, None]
for k, (p, a, b) in enumerate(PARTS[:-1]):
    WIN[p][1] = WIN[PARTS[k + 1][0]][0] + 0.25
CONV0, CONV1 = HIT - 4.2, HIT - 2.0     # 粒子汇聚
WIN['motto'][1] = CONV0 + 1.0
FADE0 = DUR - 1.4                        # 整片最终淡出

def vis(p, fi=0.5, fo=0.45):
    a, b = WIN[p]
    return env(time_now[0], a, b, fi, fo)

time_now = [0.0]

def beat_pulse(t, decay=0.14):
    i = np.searchsorted(BEATS, t, 'right') - 1
    return math.exp(-(t - BEATS[i]) / decay) if i >= 0 else 0.0


# ---------------------------------------------------------------- 背景
NB1 = fbm(270, 480, 11, 6, 3); NB2 = fbm(270, 480, 23, 6, 3)
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H * 0.45) / (H / 2)) ** 2)
VIGNETTE = np.clip(1 - 0.35 * _r ** 2.2, 0.3, 1)[..., None].astype(np.float32)
BASE = (np.array(C(9, 13, 28), np.float32) * (1 - _yy / H)[..., None] +
        np.array(C(4, 6, 14), np.float32) * (_yy / H)[..., None])
BASE += np.exp(-(_r ** 2) / 0.35)[..., None] * np.array(C(14, 22, 48), np.float32)
# 字幕区压暗带
SUBBAND = (1 - 0.45 * np.exp(-((_yy - 1440) / 170) ** 2))[..., None].astype(np.float32)
del _yy, _xx, _r

TINT = [  # 时间, 颜色 A, 颜色 B
    (0, C(40, 60, 150), C(90, 50, 150)), (8, C(30, 70, 160), C(40, 40, 120)),
    (18, C(30, 110, 170), C(60, 50, 160)), (29, C(70, 70, 110), C(60, 40, 90)),
    (37.5, C(30, 90, 170), C(40, 60, 140)), (49, C(150, 100, 40), C(70, 50, 110)),
    (61, C(30, 80, 160), C(80, 60, 130)), (82, C(30, 130, 140), C(50, 60, 140)),
    (97, C(160, 110, 40), C(70, 50, 120)), (111, C(170, 120, 40), C(90, 60, 30)),
    (HIT - 2, C(40, 80, 170), C(60, 40, 120)), (DUR, C(30, 60, 140), C(40, 30, 90))]

def keyc(t, kf, idx):
    if t <= kf[0][0]: return kf[0][idx]
    for k0, k1 in zip(kf, kf[1:]):
        if t <= k1[0]:
            return lerpc(k0[idx], k1[idx], eio((t - k0[0]) / (k1[0] - k0[0])))
    return kf[-1][idx]

def bg_at(t):
    a, b = keyc(t, TINT, 1), keyc(t, TINT, 2)
    I = 0.32 * (1 + 0.15 * beat_pulse(t, 0.25))
    s = 1.0 + 0.05 * math.sin(t * 0.06)
    M = np.float32([[s, 0, -8 - 7 * math.sin(t * 0.05)], [0, s, -16 - 14 * math.cos(t * 0.04)]])
    n1 = cv2.warpAffine(NB1, M, (240, 427), borderMode=cv2.BORDER_REFLECT)
    M2 = np.float32([[s, 0, -8 + 7 * math.sin(t * 0.04 + 1)], [0, s, -16 + 14 * math.sin(t * 0.03)]])
    n2 = cv2.warpAffine(NB2, M2, (240, 427), borderMode=cv2.BORDER_REFLECT)
    img = ((n1 ** 3)[..., None] * np.array(a, np.float32) + (n2 ** 3.2)[..., None] * np.array(b, np.float32)) * I
    return (BASE + cv2.resize(img, (W, H), interpolation=cv2.INTER_LINEAR)) * SUBBAND

RNG = np.random.default_rng(7)
ND = 240
D_X = RNG.uniform(0, W, ND); D_Y = RNG.uniform(0, H, ND); D_V = RNG.uniform(8, 30, ND)
D_PH = RNG.uniform(0, 6.28, ND)
D_COL = np.array([G_MAIN if i % 3 else BLUE for i in range(ND)], np.float32)

def dust_pos(t):
    return (D_X + 18 * np.sin(t * 0.3 + D_PH)) % W, (D_Y - D_V * t) % H

def draw_dust(f, t, a):
    x, y = dust_pos(t)
    tw = 0.5 + 0.5 * np.sin(t * 1.7 + D_PH * 3)
    f.dots(x, y, D_COL, a * (0.12 + 0.25 * tw), 1, 'E')


# ---------------------------------------------------------------- 通用组件
def shock(f, t, t0, cx, cy, col, a=1.0, R=900, life=0.9):
    p = (t - t0) / life
    if 0 <= p <= 1:
        r = R * eo(p)
        f.circle((cx, cy), r, col, a * (1 - p) ** 1.5, 3)
        f.circle((cx, cy), r * 0.82, col, a * 0.5 * (1 - p) ** 2, 2)

def implode(f, t, t0, t1, cx, cy, cols, n=900, R0=900, seed=0, a=1.0):
    if not (t0 <= t <= t1 + 0.1): return
    rng = np.random.default_rng(seed)
    ang = rng.uniform(0, 6.283, n); rad = rng.uniform(0.35, 1.0, n) * R0
    dl = rng.uniform(0, 0.35, n)
    p = np.clip((t - t0 - dl * (t1 - t0)) / ((t1 - t0) * 0.65), 0, 1)
    e = p ** 2.2
    r = rad * (1 - e); th = ang + e * 2.0
    col = np.array(cols, np.float32)[np.arange(n) % len(cols)]
    f.dots(cx + r * np.cos(th), cy + r * np.sin(th) * 1.2, col, a * (0.15 + 0.6 * e) * (p < 1), 1)

def burst(f, t, t0, cx, cy, cols, n=600, speed=1300, life=1.5, seed=3, a=1.0):
    dt = t - t0
    if not (0 <= dt <= life): return
    rng = np.random.default_rng(seed)
    ang = rng.uniform(0, 6.283, n); sp = rng.uniform(0.25, 1.0, n) * speed
    d = sp * (1 - np.exp(-2.6 * dt)) / 2.6
    col = np.array(cols, np.float32)[np.arange(n) % len(cols)]
    f.dots(cx + d * np.cos(ang), cy + d * np.sin(ang), col, a * (1 - dt / life) ** 1.4, 1)

def header(f, zh, en, y, a, t0=None):
    f.text(zh, CX, y, 60, 'serif_black', G_MAIN, a, grad=G_GRAD, mode='O', glow=0.35, t0=t0, stag=0.05)
    if en:
        f.text(en, CX, y + 64, 27, 'en_reg', GREY, a, track=0.08, t0=None if t0 is None else t0 + 0.2)


# ---------------------------------------------------------------- 字幕
SUB_TOP = 1330
_shadow_cache = {}

def shadow_of(m):
    k = id(m)
    if k not in _shadow_cache:
        p = 12
        mm = np.pad(m, p)
        _shadow_cache[k] = (cv2.GaussianBlur(cv2.dilate(mm, np.ones((5, 5), np.uint8)), (0, 0), 5) * 1.2, p)
    return _shadow_cache[k]

def put_line(f, s, fnt, size, y, col, a):
    m, bl = line_mask(s, fnt, size)
    x = CX - m.shape[1] / 2
    top = y - bl + size * 0.36
    sh, p = shadow_of(m)
    f.mask(np.clip(sh, 0, 1), x - p, top - p + 3, (0, 0, 0), a * 0.65)
    f.mask(m, x, top, col, a)

def sub_layout(it):
    zr = wrap(it['zh'], 'sans_med', 50, 920)
    er = wrap(it['en'], 'en_reg', 33, 940)
    return zr, er

def draw_subs(f, t):
    for k, it in enumerate(TL):
        nxt = TL[k + 1]['start'] if k + 1 < len(TL) else 1e9
        b = nxt - 0.06 if nxt - it['end'] < 1.3 else it['end'] + 0.45
        if not (it['start'] - 0.1 <= t <= b): continue
        a = cl((t - it['start'] + 0.1) / 0.14) * cl((b - t) / 0.14)
        zr, er = sub_layout(it)
        y = SUB_TOP + 33
        for r in zr:
            put_line(f, r, 'sans_med', 50, y, WHITE, a); y += 68
        y += 6
        for r in er:
            put_line(f, r, 'en_reg', 33, y, C(232, 214, 168), a); y += 46


# ---------------------------------------------------------------- 常驻元素
def draw_chrome(f, t):
    a = env(t, 0.3, CONV0 + 0.6, 0.6, 0.6)
    f.text('巴芒精华 · TOP 1', 52, 50, 30, 'sans_bold', G_MAIN, a, anchor='l', mode='O')
    f.text('1994 · 内在价值', 52, 88, 24, 'sans_light', GREY, a, anchor='l', track=0.05)
    # 出处（底部）
    a2 = env(t, S[2] - 0.3, CONV0, 0.5, 0.5)
    f.text(SOURCE_ZH, CX, 1700, 24, 'sans_light', GREY, a2 * 0.75)
    f.text(SOURCE_EN, CX, 1736, 24, 'sans_light', GREY, a2 * 0.75)
    # 原话段：人物与配音说明
    a3 = env(t, HIT0 + 0.1, WIN['check'][1], 0.5, 0.5)
    f.text('巴菲特原话 · WARREN BUFFETT', CX, 205, 32, 'sans_bold', G_MAIN, a3, track=0.06, mode='O')
    f.text(DISCLOSE, CX, 250, 23, 'sans_light', GREY, a3)
    # 进度条
    p = cl(t / HIT)
    f.rect(52, 1800, 52 + (W - 104) * p, 1803, SUBG, 0.55 * a, 'L')
    f.rect(52, 1800, W - 52, 1803, DIM, 0.15 * a, 'L')


# ---------------------------------------------------------------- 分镜
def sc_title(f, t):
    a = vis('title')
    if a <= 0: return
    implode(f, t, 0.0, 1.5, CX, 760, [G_MAIN, G_LIGHT, BLUE], 700, 900, 1, a)
    f.text('巴芒精华库 · TOP 100', CX, 540, 34, 'sans_light', GREY, a, track=0.3, t0=0.3)
    pulse = beat_pulse(t, 0.2)
    f.text('No.1', CX, 690, 210, 'corm', G_MAIN, a, grad=G_GRAD, mode='E', glow=0.6 + 0.3 * pulse, t0=0.8, stag=0.08, dur=0.6)
    f.text('内在价值', CX, 900, 150, 'serif_black', G_MAIN, a, grad=G_GRAD, mode='O', glow=0.45, t0=1.5, stag=0.1, dur=0.6)
    f.text('没有把握，就不知道它值多少', CX, 1050, 48, 'sans_med', WHITE, a, t0=2.4, stag=0.03)
    f.text('INTRINSIC VALUE', CX, 1125, 40, 'corm', SUBG, a, track=0.35, t0=2.9, stag=0.03)


def sc_ask(f, t):
    a = vis('ask', 0.5, 0.15)
    if a <= 0: return
    t0 = S[2]
    f.text('1994', CX, 600, 230, 'corm', lerpc(WHITE, BLUE, 0.35), a, mode='E', glow=0.5, t0=t0 - 0.2, stag=0.08, dur=0.6)
    f.text('BERKSHIRE HATHAWAY ANNUAL MEETING', CX, 760, 25, 'en_med', GREY, a, track=0.22, t0=t0 + 0.3, stag=0.01)
    f.text('伯克希尔·哈撒韦股东大会 · 下午场', CX, 812, 34, 'sans_light', WHITE, a, track=0.08, t0=t0 + 0.5, stag=0.02)
    f.text('股东提问', CX, 900, 30, 'sans_bold', SUBG, a, track=0.5, t0=t0 + 0.8)
    q0 = S[3]
    pulse = beat_pulse(t, 0.25)
    f.text('内在价值 ＝ ？', CX, 1060, 100, 'serif_black', G_MAIN, a, grad=G_GRAD, mode='O',
           glow=0.4 + 0.4 * pulse, t0=q0 + 0.6, stag=0.08, dur=0.5)
    f.text('HOW DO YOU FIGURE OUT INTRINSIC VALUE?', CX, 1150, 25, 'en_med', GREY, a, track=0.12, t0=q0 + 1.2, stag=0.01)
    # 上扬：粒子向中心坍缩，重拍时冲击波
    implode(f, t, HIT0 - 2.2, HIT0, CX, 900, [G_MAIN, BLUE, WHITE], 1200, 1000, 2, 1.0)


# 柱状图：8 年现金流
NBAR = 8
BX = [170 + i * 80 for i in range(NBAR)]
BW = 52
BASEY = 1110
CF = [1.06 ** (i + 1) for i in range(NBAR)]
PV = [c / 1.10 ** (i + 1) for i, c in enumerate(CF)]
UNIT = 260
STACK = 0.17
COLX = 930

def draw_bars(f, t, a, disc, fly, fog):
    """disc: 0→1 折现收缩；fly: 0→1 现值飞入右侧总柱；fog: 0→1 不确定（抖动+问号）"""
    f.line((130, BASEY), (COLX + 60, BASEY), GREY, a * 0.6 * eo((t - S[4] + 0.2) / 0.4), 2)
    total = 0.0
    for i in range(NBAR):
        ap = a * eo((t - (S[4] + 0.15 + i * 0.22)) / 0.4)
        if ap <= 0: continue
        x0 = BX[i]
        nz = 0.6 * math.sin(t * 2.3 + i * 1.7) + 0.4 * math.sin(t * 3.7 + i * 2.9)
        hcf = CF[i] * UNIT * (1 + fog * nz * 0.45)
        hpv = lerp(CF[i], PV[i], eio(disc)) * UNIT * (1 + fog * nz * 0.45)
        # 未折现：蓝色描边
        f.rrect(x0, BASEY - hcf, x0 + BW, BASEY, 4, lerpc(BLUE, GREY, fog), ap * (0.75 - 0.4 * fog), 2)
        # 折现后：金色实心（飞入总柱）
        fi = cl(fly * NBAR - i)
        if fi < 1:
            xx = lerp(x0, COLX - BW / 2, eio(fi)); yy = lerp(0, -total * STACK * UNIT, eio(fi))
            f.rrect_fill(xx, BASEY - hpv + yy, xx + BW, BASEY + yy, 4, lerpc(G_MAIN, GREY, fog),
                         ap * (0.55 - 0.3 * fog) * (1 - fi * 0.3), 'L')
        total += PV[i] * fi
        f.text(str(i + 1), x0 + BW / 2, BASEY + 30, 24, 'en_reg', GREY, ap * 0.8)
        if fog > 0.02:
            f.text('?', x0 + BW / 2, BASEY - CF[i] * UNIT - 50 + 10 * math.sin(t * 3 + i), 54, 'serif_black', G_LIGHT,
                   ap * fog * (0.6 + 0.4 * math.sin(t * 5 + i * 1.7)), mode='E', glow=0.3)
    f.text('未来第 N 年的现金流', 130 + (BX[-1] + BW - 130) / 2, BASEY + 70, 24, 'sans_light', GREY,
           a * 0.8 * eo((t - S[4] - 0.15) / 0.4))
    # 右侧：现值总和
    if total > 0.01:
        h = total * STACK * UNIT
        f.rrect_fill(COLX - BW / 2 - 4, BASEY - h, COLX + BW / 2 + 4, BASEY, 5, lerpc(G_MAIN, GREY, fog), a * 0.85, 'E')
        f.text('现值', COLX, BASEY + 30, 26, 'sans_bold', G_MAIN, a * cl(fly * 3))
        f.glow((COLX, BASEY - h), 26, G_MAIN, a * 0.4 * (1 - fog))
        if fog > 0.02:
            f.text('?', COLX, BASEY - h - 70, 110, 'serif_black', G_MAIN, a * fog, mode='E', glow=0.6)


def sc_dcf(f, t):
    a1 = env(t, WIN['dcf'][0], WIN['fog'][1], 0.4, 0.5)
    if a1 <= 0: return
    shock(f, t, HIT0, CX, 900, G_MAIN, 1.0)
    shock(f, t, HIT0 + 0.08, CX, 900, BLUE, 0.6, 1100)
    ah = vis('dcf')
    header(f, '内在价值 ＝ 未来现金流的现值', 'Value = present value of all future cash flows', 410, ah, t0=HIT0 + 0.2)
    pa = env(t, S[5] + 0.3, WIN['dcf'][1], 0.4, 0.4)
    f.text('÷ (1 + r)', CX - 22, 580, 54, 'en_med', G_LIGHT, pa, mode='E', glow=0.3)
    f.text('t', CX + 98, 560, 32, 'en_med', G_LIGHT, pa, mode='E', glow=0.3)
    f.text('按适当的利率逐年折现', CX, 645, 28, 'sans_light', GREY, pa)
    disc = eio((t - S[5] - 0.6) / 1.6)
    fly = cl((t - S[6] - 0.3) / 2.6)
    fog = eio((t - S[7] + 0.1) / 1.0)
    # fog 段：未折现柱子留着、现值柱抖动
    draw_bars(f, t, a1, disc, fly, fog)


def sc_fog(f, t):
    a = vis('fog')
    if a <= 0: return
    f.text('看不清未来的现金流', CX, 410, 62, 'serif_black', GREY, a, mode='O', t0=S[7], stag=0.05)
    f.text('＝ 不知道它现在值多少', CX, 500, 52, 'serif_black', G_MAIN, a, grad=G_GRAD, mode='O', glow=0.3, t0=S[8], stag=0.05)
    f.text('No idea of the cash, no idea of the value', CX, 560, 27, 'en_reg', GREY, a, t0=S[8] + 0.6)


def sc_range(f, t):
    a = vis('range')
    if a <= 0: return
    header(f, '有把握地预测一个区间', 'Within a range, with a fairly high probability', 410, a, t0=S[9])
    ox, oy = 170, 1010
    x1 = 920
    xs = np.linspace(ox, x1, 60)
    yc = oy - (xs - ox) * 0.28
    # 宽：看不清的
    aw = a * env(t, S[9] + 0.4, 1e9, 0.8, 0)
    hw = 8 + (xs - ox) / (x1 - ox) * 250
    f.fillpoly(list(zip(xs, yc - hw)) + list(zip(xs[::-1], (yc + hw)[::-1])), GREY, aw * 0.07)
    f.poly(list(zip(xs, yc - hw)), GREY, aw * 0.35, 1); f.poly(list(zip(xs, yc + hw)), GREY, aw * 0.35, 1)
    f.text('看不清：放弃', x1 - 100, yc[-1] - hw[-1] + 55, 28, 'sans_light', GREY, aw)
    # 窄：可把握的区间（从左往右画出）
    rv = eio((t - S[10]) / 2.2)
    if rv > 0:
        n = max(2, int(60 * rv))
        hn = 6 + (xs - ox) / (x1 - ox) * 58
        pts = list(zip(xs[:n], yc[:n] - hn[:n])) + list(zip(xs[:n][::-1], (yc[:n] + hn[:n])[::-1]))
        f.fillpoly(pts, G_MAIN, a * 0.3, 'E')
        f.poly(list(zip(xs[:n], yc[:n] - hn[:n])), G_MAIN, a * 0.9, 2)
        f.poly(list(zip(xs[:n], yc[:n] + hn[:n])), G_MAIN, a * 0.9, 2)
        f.text('可把握的区间', x1 - 60, yc[-1] + 110, 30, 'sans_bold', G_MAIN, a * cl(rv * 3 - 2), mode='O')
    f.glow((ox, oy), 12, WHITE, a * 0.8, 'E')
    f.text('今天', ox, oy + 45, 28, 'sans_med', WHITE, a)
    f.text('时间 →', x1 - 20, oy + 140, 24, 'sans_light', GREY, a * 0.8)
    # 折现回来：弧线从未来各点回到今天
    bk = (t - S[11] + 0.1)
    if bk > 0:
        for j, xx in enumerate((520, 700, 880)):
            k = int((xx - ox) / (x1 - ox) * 59)
            p0 = (xs[k], yc[k]); p1 = (ox, oy)
            pr = eio((bk - j * 0.18) / 0.9)
            if pr <= 0: continue
            arc = [(lerp(p0[0], p1[0], u), lerp(p0[1], p1[1], u) - math.sin(u * math.pi) * (60 + j * 40))
                   for u in np.linspace(0, pr, 30)]
            f.poly(arc, G_LIGHT, a * 0.8, 2)
            f.glow(arc[-1], 7, G_LIGHT, a * (1 - pr * 0.5), 'E')
        f.text('折现回今天', ox + 150, oy - 230, 30, 'sans_bold', G_LIGHT, a * cl(bk / 0.5), mode='O')


def sc_cert(f, t):
    a = vis('cert')
    if a <= 0: return
    header(f, '确定性 ＞ 便宜', 'Certainty over cheapness', 410, a, t0=S[12])
    px, py = CX, 640
    th = -0.12 * eio((t - S[12] - 0.3) / 1.2) - 0.08 * eio((t - S[14] - 0.3) / 1.2)
    th += 0.01 * math.sin(t * 2.0)
    L = 330
    lx, ly = px - L * math.cos(th), py - L * math.sin(th)
    rx, ry = px + L * math.cos(th), py + L * math.sin(th)
    # 支架
    f.line((px, py), (px, 1060), GREY, a * 0.7, 3)
    f.fillpoly([(px - 90, 1070), (px + 90, 1070), (px, 1030)], GREY, a * 0.25)
    f.line((lx, ly), (rx, ry), lerpc(GREY, WHITE, 0.5), a, 4)
    f.glow((px, py), 10, WHITE, a * 0.7, 'E')
    for (bx, by), side in (((lx, ly), 0), ((rx, ry), 1)):
        hy = by + 230                      # 托盘
        f.line((bx, by), (bx, hy - 124), GREY, a * 0.6, 2)
        f.line((bx - 135, hy), (bx + 135, hy), lerpc(GREY, WHITE, 0.4), a, 3)
        if side == 0:
            ap = a * eo((t - S[12]) / 0.5)
            f.rrect_fill(bx - 120, hy - 124, bx + 120, hy - 6, 10, G_MAIN, ap * 0.35, 'E')
            f.rrect(bx - 120, hy - 124, bx + 120, hy - 6, 10, G_MAIN, ap, 2)
            f.text('确定性', bx, hy - 78, 46, 'serif_black', G_LIGHT, ap, mode='O')
            f.text('CERTAINTY', bx, hy - 32, 22, 'en_med', G_MAIN, ap, track=0.15)
        else:
            ap = a * eo((t - S[13]) / 0.5)
            fade = 1 - 0.5 * eio((t - S[14] - 0.4) / 1.0)
            jit = 4 * math.sin(t * 23) * eio((t - S[14]) / 0.5)
            f.rrect(bx - 120 + jit, hy - 124, bx + 120 + jit, hy - 6, 10, GREY, ap * fade, 2)
            f.text('看起来最便宜', bx + jit, hy - 78, 34, 'sans_bold', WHITE, ap * fade)
            f.text('CHEAPEST-LOOKING', bx + jit, hy - 32, 20, 'en_med', GREY, ap * fade, track=0.1)
            aq = a * eo((t - S[14] - 0.2) / 0.5)
            f.text('建立在没把握的数字上', bx, hy + 45, 26, 'sans_light', RED, aq)


def sc_report(f, t):
    a = vis('report')
    if a <= 0: return
    # 财务报表卡片
    x0, y0, x1, y1 = 290, 360, 790, 760
    ad = a * eo((t - S[15] + 0.3) / 0.5)
    f.rrect_fill(x0, y0, x1, y1, 16, C(30, 40, 70), ad * 0.6, 'L')
    f.rrect(x0, y0, x1, y1, 16, GREY, ad * 0.8, 2)
    f.text('财务报表', CX, y0 + 50, 38, 'sans_bold', WHITE, ad)
    f.text('FINANCIAL STATEMENTS', CX, y0 + 92, 20, 'en_med', GREY, ad, track=0.15)
    for k in range(6):
        yy = y0 + 140 + k * 40
        f.rect(x0 + 40, yy, x0 + 40 + 150 + (k * 37) % 70, yy + 10, GREY, ad * 0.35)
        f.rect(x1 - 40 - 90 - (k * 53) % 50, yy, x1 - 40, yy + 10, BLUE, ad * 0.35)
    # 印章：没有答案
    sp = (t - S[15] - 0.5) / 0.3
    if sp > 0:
        s = 1 + 0.6 * (1 - eo(sp))
        aa = ad * eo(sp)
        f.rrect(CX - 190 * s, 560 - 62 * s, CX + 190 * s, 560 + 62 * s, 12, RED, aa, 4)
        f.text('没有答案', CX, 560, int(76 * s), 'serif_black', RED, aa, mode='O')
    # 只有指引
    ag = a * eo((t - S[16] - 0.2) / 0.5)
    f.text('只有指引', CX, 840, 52, 'serif_black', G_LIGHT, ag, mode='O', glow=0.3)
    f.text('Guidelines, not answers', CX, 900, 26, 'en_reg', GREY, ag)
    # 懂生意 vs 数学
    ab = a * eo((t - S[17] - 0.5) / 0.5)
    pulse = beat_pulse(t, 0.25) * cl((t - S[19]) / 0.2)
    f.text('懂生意', CX, 1040, 120, 'serif_black', G_MAIN, ab, grad=G_GRAD, mode='O', glow=0.5 + 0.5 * pulse, t0=S[17] + 0.5, stag=0.1)
    am = a * eo((t - S[18] - 0.2) / 0.5)
    f.text('不必精通数学 · 数学并不复杂', CX, 1170, 32, 'sans_light', GREY, am)


CARDS = [('现在付出多少', 'What you lay out now'), ('将来能收回多少', 'What you get back over time'),
         ('有多大把握', 'How certain you are'), ('和其他选择比', 'Versus other alternatives')]

def sc_check(f, t):
    a = vis('check')
    if a <= 0: return
    header(f, '估值四问', 'FOUR QUESTIONS', 400, a, t0=S[20] - 0.3)
    allg = eo((t - S[24]) / 0.5)
    for k, (zh, en) in enumerate(CARDS):
        p = eo((t - S[20 + k]) / 0.45)
        if p <= 0: continue
        y = 540 + k * 150
        dx = (1 - p) * 120
        ap = a * p
        col = lerpc(GREY, G_MAIN, max(allg, 1 - cl((t - S[20 + k] - 1.0) / 0.6)))
        f.rrect_fill(110 + dx, y, 970 + dx, y + 122, 18, C(25, 35, 60), ap * 0.55, 'L')
        f.rrect(110 + dx, y, 970 + dx, y + 122, 18, col, ap * 0.9, 2)
        f.circle((180 + dx, y + 61), 36, col, ap, 3)
        f.text(str(k + 1), 180 + dx, y + 61, 40, 'en_med', col, ap)
        f.text(zh, 250 + dx, y + 44, 44, 'sans_bold', WHITE, ap, anchor='l')
        f.text(en, 252 + dx, y + 92, 25, 'en_reg', GREY, ap, anchor='l')
    f.text('我们做的就是这些，只不过对象是大企业', CX, 1170, 34, 'sans_med', SUBG, a * allg, t0=S[24] + 0.3, stag=0.02)


def sc_lesson(f, t):
    a = vis('lesson')
    if a <= 0: return
    header(f, '投资启示', 'TAKEAWAY', 400, a, t0=S[25] - 0.3)
    # 第一步 ≠ 选折现率
    a1 = a * eo((t - S[25]) / 0.4)
    w1 = text_width('第一步不是', 'sans_med', 40); w2 = text_width('选折现率', 'serif_black', 48)
    x = CX - (w1 + 20 + w2) / 2
    f.text('第一步不是', x, 560, 40, 'sans_med', GREY, a1, anchor='l')
    f.text('选折现率', x + w1 + 20, 560, 48, 'serif_black', WHITE, a1, anchor='l', mode='O')
    sk = eio((t - S[25] - 1.2) / 0.5)
    if sk > 0:
        f.line((x + w1 + 14, 562), (x + w1 + 14 + (w2 + 12) * sk, 562), RED, a1, 4)
    # 判断框
    a2 = a * eo((t - S[26] - 0.3) / 0.5)
    f.rrect_fill(170, 650, 910, 830, 20, G_MAIN, a2 * 0.12, 'E')
    f.rrect(170, 650, 910, 830, 20, G_MAIN, a2, 3)
    f.text('能否有合理把握', CX, 708, 50, 'serif_black', G_LIGHT, a2, mode='O')
    f.text('预测现金流的区间？', CX, 776, 50, 'serif_black', G_LIGHT, a2, mode='O')
    # 不能 / 能
    for side, (k, lab, zh, en, col) in enumerate(((27, '不能', '放进「太难」', 'TOO HARD', GREY),
                                                  (28, '能', '再和价格比较', 'VS. PRICE', G_MAIN))):
        p = eo((t - S[k]) / 0.5)
        if p <= 0: continue
        ap = a * p
        bx = 300 if side == 0 else 780
        f.line((CX + (-1 if side == 0 else 1) * 120, 830), (lerp(CX, bx, p), lerp(830, 950, p)), col, ap, 3)
        f.text(lab, 290 if side == 0 else 790, 890, 32, 'sans_bold', col, ap)
        f.rrect_fill(bx - 175, 960, bx + 175, 1120, 18, col, ap * 0.12, 'E')
        f.rrect(bx - 175, 960, bx + 175, 1120, 18, col, ap, 2)
        f.text(zh, bx, 1020, 42, 'sans_bold', WHITE if side else GREY, ap)
        f.text(en, bx, 1076, 24, 'en_med', col, ap, track=0.15)


MOTTO = [('确定性', 830, 150, 'serif_black'), ('优先于便宜', 1000, 110, 'serif_black')]
MOTTO_EN = ('CERTAINTY BEFORE CHEAPNESS', 1110, 36)

def draw_motto(f, t, a, t0=None):
    for s, y, size, fnt in MOTTO:
        f.text(s, CX, y, size, fnt, G_MAIN, a, grad=G_GRAD, mode='O', glow=0.45, t0=t0, stag=0.09, dur=0.5)
    f.text(MOTTO_EN[0], CX, MOTTO_EN[1], MOTTO_EN[2], 'corm', SUBG, a, track=0.25,
           t0=None if t0 is None else t0 + 0.6, stag=0.02)

def sc_motto(f, t):
    a = env(t, S[29] - 0.2, CONV0 + 0.5, 0.4, 0.5)
    if a <= 0: return
    draw_motto(f, t, a, S[29])


# ---------------------------------------------------------------- 片尾：汇聚成官方 logo
LOGO_PX = 240                       # BRAND.md：片尾 logo 约 220px 居中
LOGO_CY = 800
LRGB, LA = load_logo(LOGO_PX)       # brand/logo_baman.png，预乘 alpha 缩放
LX0, LY0 = int(CX - LOGO_PX / 2), int(LOGO_CY - LOGO_PX / 2)
# 淡蓝光晕（SPEC：σ≈11px/60px logo、强度 0.2，按 logo 尺寸等比放大）
_gs = SPEC['glow_sigma'] * LOGO_PX / SPEC['logo_px']
_gp = int(_gs * 3)
LGLOW = cv2.GaussianBlur(np.pad(LA, _gp), (0, 0), _gs)[..., None] * np.array(BLUE, np.float32) * SPEC['glow_strength']

# 官方文字：hud_lockup@4x.png 的文字区（巴芒价值 + BUFFETT · MUNGER）
_lay = json.load(open(os.path.join(REPO, 'brand', 'hud_layout.json')))
_im = np.asarray(Image.open(os.path.join(REPO, 'brand', 'hud_lockup@4x.png')).convert('RGBA')).astype(np.float32) / 255
_tb = _lay['text_box']
_txt = _im[_tb[1]:_tb[3], _tb[0]:_tb[2]]
_rows = np.where(_txt[..., 3].max(1) > 0.03)[0]
_gap = [r for r in range(_rows[0], _rows[-1]) if _txt[r, :, 3].max() <= 0.03]
_split = (_gap[0] + _gap[-1]) // 2
WM_SCALE = 0.95

def _scaled(part):
    h, w = part.shape[:2]
    rgb, al = brand._resize_rgba(part[..., :3], part[..., 3], int(w * WM_SCALE), int(h * WM_SCALE))
    return rgb, al

WM_T = _scaled(_txt[:_split])       # 巴芒价值
WM_S = _scaled(_txt[_split:])       # BUFFETT · MUNGER
WM_W = WM_T[0].shape[1]
WM_X = int(CX - WM_W / 2)
WM_TY = LY0 + LOGO_PX + 64
WM_SY = WM_TY + WM_T[0].shape[0]

# 粒子：起点 = 画面元素（金句文字像素 + 漂浮金尘），终点 = logo alpha 遮罩
NP = 16000
def _particles():
    rng = np.random.default_rng(42)
    fr = Frame(1e6)
    for s, y, size, fnt in MOTTO:
        fr.text(s, CX, y, size, fnt, G_MAIN, 1.0, grad=G_GRAD, mode='L')
    fr.text(MOTTO_EN[0], CX, MOTTO_EN[1], MOTTO_EN[2], 'corm', SUBG, 1.0, track=0.25, mode='L')
    lum = fr.L.sum(2)
    ys, xs = np.where(lum > 0.6)
    k = rng.choice(len(xs), int(NP * 0.75), replace=len(xs) < NP)
    sx = np.concatenate([xs[k], rng.uniform(0, W, NP - len(k))]).astype(np.float32)
    sy = np.concatenate([ys[k], rng.uniform(150, H - 150, NP - len(k))]).astype(np.float32)
    scol = np.concatenate([fr.L[ys[k], xs[k]], np.tile(np.array(G_MAIN, np.float32), (NP - len(k), 1))])
    w = (LA > 0.35).ravel().astype(np.float64); w /= w.sum()
    idx = rng.choice(LA.size, NP, p=w)
    ty, tx = np.divmod(idx, LOGO_PX)
    tcol = LRGB[ty, tx]
    tx = (tx + LX0 + rng.uniform(-0.5, 0.5, NP)).astype(np.float32)
    ty = (ty + LY0 + rng.uniform(-0.5, 0.5, NP)).astype(np.float32)
    delay = rng.uniform(0, 0.55, NP).astype(np.float32)
    # 文字像素先走、金尘后走；离中心远的稍晚
    delay[int(NP * 0.75):] += 0.25
    swirl = rng.uniform(1.2, 2.4, NP).astype(np.float32) * rng.choice([-1, 1], NP)
    return sx, sy, scol, tx, ty, tcol, delay, swirl
P_SX, P_SY, P_SC, P_TX, P_TY, P_TC, P_DL, P_SW = _particles()

def sc_converge(f, t):
    if not (CONV0 - 0.2 <= t <= HIT + 0.6): return
    span = CONV1 - CONV0 - 0.55
    p = np.clip((t - CONV0 - P_DL) / span, 0, 1)
    e = p * p * (3 - 2 * p)
    # 绕 logo 中心旋入
    cx, cy = CX, LOGO_CY
    ang0 = np.arctan2(P_SY - cy, P_SX - cx); r0 = np.hypot(P_SX - cx, P_SY - cy)
    ang1 = np.arctan2(P_TY - cy, P_TX - cx); r1 = np.hypot(P_TX - cx, P_TY - cy)
    dang = (ang1 - ang0 + np.pi) % (2 * np.pi) - np.pi
    ang = ang0 + dang * e + P_SW * np.sin(e * np.pi) * 0.6
    r = r0 + (r1 - r0) * e
    x = cx + r * np.cos(ang); y = cy + r * np.sin(ang)
    x = np.where(p >= 1, P_TX, x); y = np.where(p >= 1, P_TY, y)
    col = P_SC * (1 - e[:, None]) + P_TC * e[:, None]
    # 到位后随清晰 logo 浮现而淡出
    fade = 1 - eio((t - CONV1 + 0.2) / 1.1)
    a = (0.55 + 0.45 * e) * fade * cl((t - CONV0 + 0.2) / 0.3)
    f.splat(x, y, col, a * 1.1, 'E')
    f.splat(x + 1, y, col, a * 0.4, 'E'); f.splat(x, y + 1, col, a * 0.4, 'E')
    if CONV1 - 0.6 <= t:
        f.glow((cx, cy), 120, BLUE, 0.25 * eo((t - CONV1 + 0.6) / 0.8) * fade, 'B')


def endcard_post(img, t):
    """tone-map 之后合成原始 logo 和官方文字（颜色与品牌稿一致）"""
    la = eio((t - (CONV1 - 0.3)) / 1.1)          # 清晰 logo 浮现
    if la <= 0: return img
    rise = (1 - eo((t - CONV1 + 0.3) / 1.4)) * 18
    y0 = int(round(LY0 + rise))
    gh = LGLOW.shape[0]
    reg = img[y0 - _gp:y0 - _gp + gh, LX0 - _gp:LX0 - _gp + gh]
    reg += LGLOW * la
    a = (LA * la)[..., None]
    reg = img[y0:y0 + LOGO_PX, LX0:LX0 + LOGO_PX]
    reg *= (1 - a); reg += a * LRGB
    # 文字：在片尾重拍上出现，随后扫过流光
    ta = eo((t - HIT) / 0.22)
    if ta > 0:
        sc = 1 + 0.06 * (1 - eo((t - HIT) / 0.5))
        for (rgb, al), yy, dt in ((WM_T, WM_TY, 0.0), (WM_S, WM_SY, 0.12)):
            aa = eo((t - HIT - dt) / 0.25)
            if aa <= 0: continue
            if sc != 1:
                h, w = al.shape
                rgb, al = brand._resize_rgba(rgb, al, int(w * sc), int(h * sc))
            h, w = al.shape
            x0 = int(CX - w / 2); yc = int(yy)
            col = rgb.copy()
            u = (t - HIT - 0.3) / SPEC['shimmer_dur']      # 流光：1.4s 扫一次
            if 0 <= u <= 1:
                xs = np.arange(w)[None, :] + np.arange(h)[:, None] * 0.6
                pos = -60 + (0.5 - 0.5 * math.cos(u * math.pi)) * (w + 120)
                col = np.clip(col + np.exp(-((xs - pos) / 34) ** 2)[..., None] * 0.6, 0, 1.25)
            r = img[yc:yc + h, x0:x0 + w]
            m = (al * aa)[..., None]
            r *= (1 - m); r += m * col
    return img


# ---------------------------------------------------------------- 合成
HUD = Hud(scale=1.0, frame_w=W)
SCENES = [sc_title, sc_ask, sc_dcf, sc_fog, sc_range, sc_cert, sc_report, sc_check, sc_lesson, sc_motto, sc_converge]

def render(i):
    t = i / FPS
    time_now[0] = t
    f = Frame(t)
    bg = bg_at(t)
    draw_dust(f, t, 1.0 - 0.7 * eio((t - CONV0) / 1.5))
    for s in SCENES:
        s(f, t)
    if HIT0 <= t < HIT0 + 0.25:
        f.flash = 0.22 * math.exp(-(t - HIT0) / 0.07)
    if HIT <= t < HIT + 0.3:
        f.flash = 0.16 * math.exp(-(t - HIT) / 0.08)
    shock(f, t, HIT, CX, LOGO_CY, BLUE, 0.8, 800)
    burst(f, t, HIT, CX, LOGO_CY, [BLUE, G_MAIN, G_LIGHT, WHITE], 500, 1100, 1.4, 9, 0.7)
    draw_chrome(f, t)
    draw_subs(f, t)
    img = finish(f, bg, bloom_k=1.0 + 0.25 * beat_pulse(t), vignette=VIGNETTE)
    img = endcard_post(img, t)
    HUD.draw(img, t)                               # 右上角官方角标：全程保留
    fade = 1 - eio((t - FADE0) / 1.4)              # 只有整片最终淡出
    img = np.clip(img * fade, 0, 1)
    return (img * 255 + 0.5).astype(np.uint8)


if __name__ == '__main__':
    import subprocess
    mode = sys.argv[1]
    if mode == 'stills':
        out = sys.argv[2]; os.makedirs(out, exist_ok=True)
        for tt in sys.argv[3:-1]:
            img = render(int(round(float(tt) * FPS)))
            cv2.imwrite(os.path.join(out, 'f_%07.2f.png' % float(tt)), img[..., ::-1])
    elif mode == 'chunk':
        a, b, path = int(sys.argv[2]), min(int(sys.argv[3]), NFR), sys.argv[4]
        p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                              '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow',
                              '-crf', '17', '-pix_fmt', 'yuv420p', '-tune', 'animation', path], stdin=subprocess.PIPE)
        for i in range(a, b):
            p.stdin.write(render(i).tobytes())
            if (i - a) % 300 == 0: print(path, i, flush=True)
        p.stdin.close(); p.wait()
    elif mode == 'nframes':
        print(NFR)
