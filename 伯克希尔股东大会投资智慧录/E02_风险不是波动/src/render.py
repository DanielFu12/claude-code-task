"""《伯克希尔股东大会投资智慧录》第二集 · 风险不是波动 —— 逐帧渲染（1080×1920，30fps）。

画面风格：“暗夜星图编年”——近乎纯黑的宇宙里只有发光的点和细线：节点、点云、倾斜网格平面在黑暗中逐个亮起又熄灭，
底部一条贯穿全片的时间刻度尺；排印卡（灰白衬线大数字 → 短横线 → 中文衬线名 → 英文斜体名 → 灰色说明）与图解对角放置；
左上段落标签（罗马数字 · 全大写英文），右上衬线读数，右下等宽状态读数。场景之间先整体暗到黑、停顿，再按“图解 → 排印卡 → 读数”错开亮起。
全部为 2D 合成（numpy / OpenCV / PIL），不需要 GPU。
用法：
    python3 render.py nframes WORK
    python3 render.py chunk A B OUT.mp4 WORK
    python3 render.py stills OUT_DIR t1 t2 … WORK
所有画面都是时间 t 的纯函数；时间点全部来自 WORK/timeline.json。
"""
import json, math, os, subprocess, sys
import numpy as np, cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'brand'))
from gfx import *                      # noqa: F401,F403
import gfx
import fx
import brand as B
from script import BROLL

WORK = sys.argv[-1] if len(sys.argv) > 2 else os.path.join(HERE, '..', 'work')
TL = json.load(open(os.path.join(WORK, 'timeline.json')))
FPS = TL['fps']
ENV = np.load(os.path.join(WORK, 'orig_env.npy'))

# ---------------------------------------------------------------- 色板与字体（S2：暖金 + 冰青两套光，灰白衬线排印）
gfx.FONTS.update(serif_light='serif_light', serif_reg='serif_reg', mono='mono')
gfx.LATIN_FALLBACK.update(mono='sans')
BG0 = C(1, 2, 4)                                   # 背景 #010204
GOLD_C, GOLD_H = C(255, 217, 160), C(224, 160, 96)  # 暖金：核心 / 外晕（被点亮、被选中的）
AMBER = C(217, 127, 91)                            # 琥珀（次暖）：亏损、付出去的
ICE = C(111, 195, 223)                             # 冰青：数据、价格
FOG = C(99, 109, 154)                              # 雾蓝紫：远景连线
NUM = C(201, 201, 206)                             # 年份 / 大数字（不发光）
DESC = C(140, 140, 146)                            # 说明文字
RULE = C(42, 42, 46)                               # 刻度 / 细线
TXT = C(226, 226, 230)                             # 字幕

# ---------------------------------------------------------------- 品牌（只用 brand/ 里的官方资产）
HUD = B.Hud(scale=1.0, frame_w=W)
LOGO_PX = 240
LOGO_RGB, LOGO_A = B.load_logo(LOGO_PX)
_lay = json.load(open(B.LAYOUT))
_lock = np.asarray(Image.open(B.LOCKUP_4X).convert('RGBA')).astype(np.float32) / 255
_tb = _lay['text_box']
_txt = _lock[_tb[1]:_tb[3], _tb[0]:_tb[2]]
_rows = np.where(_txt[..., 3].max(1) > 0.02)[0]
_gap = np.where(np.diff(_rows) > 3)[0]
_split = int(_rows[_gap[0]] + 2) if len(_gap) else int(_txt.shape[0] * 0.75)
END_SCALE = 0.78


def _lock_part(a, b):
    p = _txt[a:b]
    w, h = int(p.shape[1] * END_SCALE), int(p.shape[0] * END_SCALE)
    rgb, al = B._resize_rgba(p[..., :3], p[..., 3], w, h)
    return rgb.astype(np.float32), al.astype(np.float32)


END_TITLE = _lock_part(0, _split)
END_SUB = _lock_part(_split, _txt.shape[0])

QA_CLIP = Clip(os.path.join(WORK, 'qa_c.mp4'))
CLIPS = {k: Clip(os.path.join(WORK, f'broll_{k}_c.mp4')) for k in BROLL}

# ---------------------------------------------------------------- 时间点
INTRO, INS, SUM, END, QA = TL['intro'], TL['insight'], TL['summary'], TL['end'], TL['qa']
COLD = TL['cold']
T_TITLE = TL['t_title']
VOD = {v['id']: v for part in (INTRO, INS, SUM) for v in part['vo']}
WORDS = {}
for part in (INTRO, INS, SUM):
    for w in part['words']:
        WORDS.setdefault(w['id'], []).append(w)
QSC = {s['scene']: s for s in QA['scenes']}
QSUB = {s['id']: s for s in QA['subs']}
T_CTX = TL['ctx']['t0']; T_Q = QA['t0']; T_QE = QA['t1']; T_INS = INS['t_card']; T_SUM = SUM['t0']
HITS = [tuple(h) for h in TL['hits']]
BEATS = np.array(TL['beats'])
NV = TL['nerves']


def wt(sid, sub, dflt=None):
    """口播 sid 中子串 sub 开始被读出的时刻"""
    ws = WORDS[sid]
    s = ''.join(w['w'] for w in ws)
    k = s.find(sub)
    if k < 0:
        assert dflt is not None, (sid, sub)
        return dflt
    n = 0
    for w in ws:
        if n + len(w['w']) > k: return w['t']
        n += len(w['w'])
    return ws[-1]['t']


def V(sid): return VOD[sid]


def qs(sid, d=0.0): return QSUB[sid]['t0'] + d


def ofr(t):
    i = min(max(int(t * FPS), 0), len(ENV) - 1)
    return ENV[i]


def qa_src(t):
    """片内时刻 → 原声片段里的源时间（秒，相对 CLIP_IN）"""
    for sg in QA['segs']:
        if sg['t0'] - 0.6 <= t <= sg['t1'] + 0.6:
            return min(max(sg['src_in'] + t - sg['t0'], sg['src_in']), sg['src_out'])
    return QA['segs'][-1]['src_out'] if t > T_QE else QA['segs'][0]['src_in']


I = {k: V(k) for k in ('I1', 'I2', 'I3', 'I4', 'I5', 'I6', 'I7', 'I8', 'I9', 'I10', 'I11', 'I12', 'I13')}


def ke(t, t0, d=0.6): return eo((t - t0) / d)


# ================================================================ 发光的点与细线（线性缓冲区，之后统一泛光）
def node(L, p, col, k=1.0, r=1.0):
    """发光节点：小而亮的核 + 很淡的外晕"""
    if k <= 0.003: return
    c = np.asarray(col, np.float32)
    g = soft_dot(round(2.0 * r, 1)); R_ = g.shape[0] // 2
    add(L, c * 1.0 + 0.35, g * 2.0 * k, int(p[0]) - R_, int(p[1]) - R_)
    g = soft_dot(round(9.0 * r, 1)); R_ = g.shape[0] // 2
    add(L, c, g * 0.24 * k, int(p[0]) - R_, int(p[1]) - R_)


def hair(L, pts, col, k=0.35, th=1):
    """1px 细线（加色）"""
    if k <= 0.003 or len(pts) < 2: return
    P = np.asarray(pts, np.float64)
    x0, y0 = int(max(P[:, 0].min() - 4, 0)), int(max(P[:, 1].min() - 4, 0))
    x1, y1 = int(min(P[:, 0].max() + 5, W)), int(min(P[:, 1].max() + 5, H))
    if x1 <= x0 or y1 <= y0: return
    m = np.zeros((y1 - y0, x1 - x0), np.float32)
    cv2.polylines(m, [((P - [x0, y0]) * 16).astype(np.int32).reshape(-1, 1, 2)], False, 1.0, th, cv2.LINE_AA, 4)
    L[y0:y1, x0:x1] += m[..., None] * (np.asarray(col, np.float32) * k)


def ring(L, c, r, col, k=0.5, th=1):
    n = max(24, int(r * 0.8))
    a = np.linspace(0, 2 * math.pi, n + 1)
    hair(L, np.c_[c[0] + r * np.cos(a), c[1] + r * np.sin(a)], col, k, th)


def cloud(L, xy, col, k=1.0, w=None, sig=1.0):
    """点云：单个点很暗，靠叠加出亮度"""
    if k <= 0.003 or len(xy) == 0: return
    xy = np.asarray(xy, np.float64)
    ok = (xy[:, 0] > 2) & (xy[:, 0] < W - 3) & (xy[:, 1] > 2) & (xy[:, 1] < H - 3)
    if not ok.any(): return
    xy = xy[ok]
    x0, y0 = int(xy[:, 0].min()) - 8, int(xy[:, 1].min()) - 8
    x1, y1 = int(xy[:, 0].max()) + 9, int(xy[:, 1].max()) + 9
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    buf = np.zeros((y1 - y0, x1 - x0, 3), np.float32)
    c = np.asarray(col, np.float32)
    c = np.broadcast_to(c, (len(xy), 3)) if c.ndim == 1 else c[ok]
    if w is not None: c = c * np.asarray(w, np.float32)[ok][:, None]
    np.add.at(buf, (xy[:, 1].astype(int) - y0, xy[:, 0].astype(int) - x0), c)
    buf = cv2.GaussianBlur(buf, (0, 0), sig) * (2 * math.pi * sig * sig) + cv2.GaussianBlur(buf, (0, 0), 5) * 2.0
    L[y0:y1, x0:x1] += buf * (k * 1.6)


def proj_plane(u, v, cx, cy, R=330.0, pitch=1.0, yaw=0.0, D=3.0, h=0.0):
    """倾斜网格平面：平面坐标 (u, v)（-1..1），高度 h → 屏幕像素"""
    X = u * np.cos(yaw) - v * np.sin(yaw)
    Z = u * np.sin(yaw) + v * np.cos(yaw)
    Yc = -Z * math.sin(pitch) + h * math.cos(pitch)
    Zc = D + Z * math.cos(pitch) + h * math.sin(pitch)
    f = R * D
    return np.c_[cx + f * X / Zc, cy - f * Yc / Zc]


def fib_sphere(n, seed=0):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n); th = math.pi * (1 + 5 ** 0.5) * i
    rng = np.random.default_rng(seed)
    r = rng.uniform(0.55, 1.0, n) ** 0.5                      # 体积点云：内部也有点
    return np.c_[np.cos(th) * np.sin(phi) * r, np.cos(phi) * r, np.sin(th) * np.sin(phi) * r]


SPHERE = fib_sphere(900, 3)


def sphere_xy(c, R, t, spin=0.12, tilt=0.35):
    a = t * spin
    x = SPHERE[:, 0] * math.cos(a) - SPHERE[:, 2] * math.sin(a)
    z = SPHERE[:, 0] * math.sin(a) + SPHERE[:, 2] * math.cos(a)
    y = SPHERE[:, 1] * math.cos(tilt) - z * math.sin(tilt)
    z2 = SPHERE[:, 1] * math.sin(tilt) + z * math.cos(tilt)
    depth = 0.55 + 0.45 * (z2 + 1) / 2
    return np.c_[c[0] + x * R, c[1] + y * R], depth


# ---------------------------------------------------------------- 背景：近乎纯黑，中心略亮，四周暗角；极稀疏、极暗的星尘
def make_bg():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d2 = ((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.45) / (H * 0.5)) ** 2
    lift = C(11, 13, 19)
    return BG0 + lift * np.exp(-d2 * 1.6)[..., None]


BGI = make_bg()
_r = np.random.default_rng(7)
STARS = np.c_[_r.uniform(0, W, 520), _r.uniform(0, H, 520)]
STAR_B = _r.uniform(0.05, 0.14, 520).astype(np.float32)
STAR_V = _r.normal(0, 1, (520, 2)) * 1.2
_VIG = None
GRAIN = [(cv2.resize(np.random.default_rng(100 + i).normal(0, 1, (H // 2, W // 2)).astype(np.float32), (W, H)) * 0.006)[..., None]
         for i in range(6)]


def vignette():
    global _VIG
    if _VIG is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 * 0.7 + ((yy - H * 0.47) / (H / 2)) ** 2)
        _VIG = (1 - 0.48 * np.clip(r - 0.35, 0, 1) ** 1.4)[..., None].astype(np.float32)
    return _VIG


def stardust(img, t):
    p = (STARS + STAR_V * t) % [W, H]
    tw = STAR_B * (0.8 + 0.2 * np.sin(t * 0.7 + STARS[:, 0]))
    np.add.at(img, (p[:, 1].astype(int), p[:, 0].astype(int)), tw[:, None] * np.array([0.9, 0.92, 1.0], np.float32))


def finish(L, t):
    """只让点线溢光（阈值泛光），柔和压缩高光，叠加到背景上，暗角 + 极轻颗粒"""
    hi = np.maximum(L - 0.55, 0)
    s = cv2.resize(hi, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    bl = cv2.GaussianBlur(s, (0, 0), 2.5) * 0.6 + cv2.GaussianBlur(s, (0, 0), 8) * 0.4
    x = L + cv2.resize(bl, (W, H), interpolation=cv2.INTER_LINEAR) * 0.9
    x = 1 - np.exp(-x * 1.25)
    img = BGI + x
    stardust(img, t)
    img = img * vignette() + GRAIN[int(t * FPS) % len(GRAIN)]
    return img.astype(np.float32)


# ================================================================ 排印
def seg_label(img, s, a, note=None):
    """左上段落标签：罗马数字 · 全大写英文（字距 0.4em）+ 下方一小段细线"""
    if a <= 0.003: return
    text(img, s.upper(), 72, 98, 17, 'sans', DESC, a, 'l', track=0.4, shadow=0.0)
    line(img, (72, 122), (132, 122), DESC, a * 0.6, 1)
    if note: text(img, note, 72, 152, 21, 'serif_med', DESC, a * 0.9, 'l', track=0.08, shadow=0.0)


def card(img, x, y, big, zh, en, desc, a, big_size=96, desc_col=None, desc_size=25, rise=None):
    """节点卡：灰白衬线大数字（不发光）→ 短横线 → 中文衬线名 → 英文斜体名 → 灰色说明"""
    if a <= 0.003: return
    r = 6 * (1 - a) if rise is None else rise
    text(img, big, x, y + r, big_size, 'serif_light', NUM, a, 'l', track=0.04, shadow=0.0)
    yy = y + big_size * 0.62 + 18
    line(img, (x + 2, yy + r), (x + 122, yy + r), DESC, a * 0.7, 1)
    yy += 52
    if zh:
        text(img, zh, x, yy + r, 40, 'serif_med', NUM, a, 'l', track=0.1, shadow=0.0); yy += 46
    if en:
        text(img, en, x, yy + r, 25, 'ebg_i', DESC, a, 'l', shadow=0.0); yy += 50
    for ln in desc:
        if not ln: continue
        it = ln.startswith('“') and all(ord(c) < 0x2e80 for c in ln.strip('“”—’ '))
        text(img, ln, x, yy + r, desc_size if not it else desc_size + 1, 'ebg_i' if it else 'serif_med',
             desc_col if desc_col is not None else DESC, a, 'l', track=0.0 if it else 0.12, shadow=0.0)
        yy += desc_size * 1.6


def readout(img, s, a, y=212, col=None, size=32, x=1008, anchor='r'):
    """右上衬线读数（字符间带空格），灰色，不发光"""
    if a <= 0.003: return
    text(img, s, x, y, size, 'ebg', DESC if col is None else col, a, anchor, track=0.12, shadow=0.0)


def counter(img, s, a, y=272, col=None):
    if a <= 0.003: return
    text(img, s, 1008, y, 40, 'ebg', NUM if col is None else col, a, 'r', track=0.06, shadow=0.0)


def status(img, s, a, y=1500):
    """右下等宽全大写状态读数（数字实时跳动）"""
    if a <= 0.003: return
    text(img, s, 1008, y, 15, 'mono', DESC, a * 0.85, 'r', track=0.3, shadow=0.0)


def narr_sub(img, t, subs, hide=()):
    for s in subs:
        if s['id'] in hide: continue
        if s['t0'] <= t <= s['t1']:
            a = env(t, s['t0'], s['t1'], 0.07, 0.07)
            size = 44
            while text_w(s['text'], 'serif_med', size, 0.1) > 980: size -= 2
            text(img, s['text'], W / 2, 1626, size, 'serif_med', TXT, a, 'm', track=0.1, shadow=0.9)


def orig_sub(img, s, a, bottom=1490):
    """原声字幕：中文衬线在上（46px），英文衬线斜体在下"""
    zl = wrap(s['zh'], 'serif_med', 46, 960, track=0.06)
    el = wrap(s['en'], 'ebg_i', 31, 960, cjk=False)
    hh = len(zl) * 60 + 12 + len(el) * 40
    y = bottom - hh + 28
    for ln in zl:
        text(img, ln, W / 2, y, 46, 'serif_med', TXT, a, 'm', track=0.06, shadow=0.9); y += 60
    y += 12 - 28 + 20
    for ln in el:
        text(img, ln, W / 2, y, 31, 'ebg_i', DESC * 1.15, a, 'm', shadow=0.9); y += 40


def dots_wave(L, t, x0, x1, y, hmax, k, col=None):
    """原声“波形”：一排细小的点柱，高度随原声能量起伏"""
    if k <= 0.003: return
    e = ofr(t); n = 26
    xs = np.linspace(x0, x1, n)
    pts, w = [], []
    for i, x in enumerate(xs):
        v = float(e[int(i * (len(e) - 1) / (n - 1))]) if len(e) else 0.0
        m = 1 + int(min(v, 1.0) * hmax / 7)
        for j in range(-m, m + 1):
            pts.append((x, y + j * 7)); w.append(1.0 - abs(j) / (m + 1) * 0.6)
    cloud(L, pts, GOLD_H if col is None else col, k * 0.55, w=np.array(w), sig=0.8)


# ================================================================ 场景时间表：先整体暗到黑（0.85 秒）→ 停 0.4 秒 → 图解 / 排印卡 / 读数错开 0.5 秒亮起
def b_before(t0, d=0.45): return t0 - d


B_TITLE = T_TITLE - 0.4
B_S1 = b_before(V('S1')['t0'])
B_S2 = b_before(V('S2')['t0'])
B_S3 = b_before(V('S3')['t0'])
B_CTX = b_before(T_CTX)
B_QA = b_before(T_Q)
B_INS = b_before(T_INS)
B_I2 = b_before(I['I2']['t0'])
B_I3 = b_before(I['I3']['t0'])
B_WAPO = NV['entry'] - 0.4                 # 配乐大段落进入的重拍上亮起
B_DEX = b_before(I['I7']['t0'])
B_LEV = b_before(I['I11']['t0'])
B_TODAY = b_before(I['I12']['t0'])
B_CLOSE = b_before(I['I13']['t0'])
B_SUM = T_SUM - 0.4                        # 高潮重拍前的 0.4 秒纯黑
B_END = 1e9


def stage(t, b_in, b_out, delay=0.0, up=0.6):
    u = 1.0 if b_in <= 0 else eio((t - (b_in + 0.4 + delay)) / up)
    return u * (1 - eio((t - (b_out - 0.85)) / 0.85))


def A3(t, b_in, b_out):
    """图解 / 排印卡 / 读数 三段错开"""
    return stage(t, b_in, b_out), stage(t, b_in, b_out, 0.5), stage(t, b_in, b_out, 1.0)


# 底部时间刻度尺的节点（片中各章的起点）
RULER = [('序', 0.0), ('问', B_S1 + 0.4), ('1994', B_CTX + 0.4), ('启示', B_INS + 0.4), ('1973', B_WAPO + 0.4), ('1993', B_DEX + 0.4),
         ('杠杆', B_LEV + 0.4), ('今', B_TODAY + 0.4), ('终', T_SUM)]
RX0, RX1, RY = 96, 984, 1560


def ruler(img, t):
    a = env(t, 0.6, END['t_particles'] + 0.2, 1.0, 0.8)
    if a <= 0.003: return
    n = len(RULER)
    xs = [RX0 + (RX1 - RX0) * i / (n - 1) for i in range(n)]
    # 当前位置：在每个节点时刻前后 0.4 秒内滑过去（ease-in-out）
    pos = 0.0
    for i in range(1, n):
        pos += eio((t - (RULER[i][1] - 0.4)) / 0.8)
    xc = RX0 + (RX1 - RX0) * pos / (n - 1)
    line(img, (RX0, RY), (RX1, RY), RULE * 1.25, a, 1)
    line(img, (RX0, RY), (xc, RY), C(92, 92, 100), a, 1)
    for i, (lab, _) in enumerate(RULER):
        past = pos >= i - 0.02
        circle(img, (xs[i], RY), 3.2, C(120, 120, 128) if past else RULE * 1.8, a, fill=True)
        text(img, lab, xs[i], RY - 24, 20, 'serif_med', NUM if past else DESC * 0.75, a * (1.0 if past else 0.8), 'm', track=0.06, shadow=0.0)
    glow(img, (xc, RY), 10, np.array([0.9, 0.9, 1.0], np.float32), a * 0.35)
    circle(img, (xc, RY), 4.2, np.array([1, 1, 1], np.float32), a, fill=True)


# ================================================================ 各场景：dia_* 画进线性缓冲区（会泛光），txt_* 画排印（不发光）
# ---------------------------------------------------------------- 冷开场：一团冰青点云在剧烈地乱跳（金融界的风险度量“乱了套”）
_rc = np.random.default_rng(11)
COLD_P = np.c_[_rc.normal(0, 1, 260), _rc.normal(0, 1, 260)]
COLD_F = _rc.uniform(2, 9, (260, 2)); COLD_PH = _rc.uniform(0, 6.3, (260, 2))


def dia_cold(L, t):
    a = stage(t, 0, B_TITLE) * eio((t - 0.3) / 1.2)
    if a <= 0: return
    j = np.sin(t * COLD_F + COLD_PH) * 26 * (0.4 + ofr(t).mean() * 2.0 if len(ofr(t)) else 1.0)
    xy = np.c_[540 + COLD_P[:, 0] * 210, 760 + COLD_P[:, 1] * 120] + j
    cloud(L, xy, ICE, 0.55 * a)
    node(L, (540, 760), GOLD_C, a * (0.7 + 0.3 * math.sin(t * 1.3)), 1.2)


def txt_cold(img, t, subs):
    a = stage(t, 0, B_TITLE) * eio((t - 0.5) / 1.0)
    if a <= 0: return
    seg_label(img, '序 · Prologue', a)
    text(img, '声音：1994 年伯克希尔股东大会原始录音', W / 2, 1060, 22, 'serif_med', DESC, a, track=0.12, shadow=0.0)
    if subs:
        for s in TL['cold_subs']:
            sa = env(t, s['t0'] - 0.1, s['t1'] + 0.1, 0.35, 0.3) * a
            if sa > 0: orig_sub(img, s, sa)


# ---------------------------------------------------------------- 片名：黑场中央衬线大字亮起、呼吸
def title_a(t): return eo((t - (T_TITLE - 0.05)) / 0.45) * (1 - eio((t - (B_S1 - 0.85)) / 0.85))


def dia_title(L, t):
    a = title_a(t)
    if a <= 0: return
    k = max(0.0, t - T_TITLE)
    # 片名下方一行很淡的点：一条细细的“地平线”
    xs = np.linspace(200, 880, 70)
    cloud(L, np.c_[xs, np.full_like(xs, 1015)], GOLD_H, a * 0.35 * (0.6 + 0.4 * math.exp(-k / 0.8)))
    node(L, (540, 1015), GOLD_C, a * (0.6 + 1.2 * math.exp(-k / 0.6)), 1.4)


def txt_title(img, t, subs):
    a = title_a(t)
    if a <= 0: return
    k = max(0.0, t - T_TITLE)
    br = 0.18 + 0.12 * (0.5 - 0.5 * math.cos(2 * math.pi * k / 1.4)) + 0.4 * math.exp(-k / 0.5)    # 呼吸
    text(img, '巴菲特与芒格 · 伯克希尔股东大会投资智慧录', W / 2, 680, 26, 'serif_med', DESC, a * eo((k - 0.2) / 0.8), track=0.16, shadow=0.0)
    text(img, '风险不是波动', W / 2, 840, 124, 'serif_med', TXT, a, track=0.12, shadow=0.0, glow=br, glow_col=GOLD_H)
    text(img, 'RISK IS NOT VOLATILITY', W / 2, 960, 17, 'sans', DESC, a * eo((k - 0.4) / 0.9), track=0.7, shadow=0.0)
    text(img, '第 二 集', W / 2, 1090, 26, 'serif_med', NUM, a * eo((k - 0.8) / 0.8), track=0.3, shadow=0.0)


# ---------------------------------------------------------------- S1：一年跌掉 25% 的价格节点
PRICE = [100, 103, 99, 104, 108, 102, 105, 96, 90, 84, 78, 75]
PXY = np.c_[200 + np.arange(12) * 62, 860 - (np.array(PRICE) - 72) / 38 * 400]


def dia_s1(L, t):
    a = stage(t, B_S1, B_S2)
    if a <= 0: return
    td = wt('S1', '跌掉')
    head = 1 + 11 * eio((t - (B_S1 + 0.5)) / (td + 0.6 - B_S1 - 0.5))
    n = int(head)
    for i in range(n):
        node(L, PXY[i], ICE, a * 0.8, 0.8)
        if i: hair(L, [PXY[i - 1], PXY[i]], ICE, 0.32 * a)
    if n < 12:
        f = head - n
        q = PXY[n - 1] + (PXY[n] - PXY[n - 1]) * f
        hair(L, [PXY[n - 1], q], ICE, 0.32 * a)
    kd = ke(t, td + 0.5)
    if kd > 0:
        node(L, PXY[-1], GOLD_C, a * kd * (0.9 + 0.2 * math.sin(t * 1.4)), 1.3)
        ring(L, PXY[-1], 22, GOLD_H, 0.45 * a * kd)
        hair(L, [(PXY[0][0], PXY[0][1]), (PXY[-1][0] + 40, PXY[0][1])], FOG, 0.18 * a * kd)       # 起点的水平参考线


def txt_s1(img, t, subs):
    ad, ac, ar = A3(t, B_S1, B_S2)
    seg_label(img, 'I · The question', ad)
    card(img, 72, 1150, '−25%', '一年', 'One year', ['它是变得更危险了，', '还是更便宜了？'][:1 + (t > wt('S1', '更便宜') - 0.2)],
         ac * ke(t, wt('S1', '百分之') - 0.2), desc_col=NUM)
    readout(img, 'P₁ ⁄ P₀  =  0.75', ar * ke(t, wt('S1', '百分之')))
    status(img, f'NODE 01 / 08   T+{max(0.0, t - B_S1 - 0.4):04.1f}', ad)


# ---------------------------------------------------------------- S2：倾斜网格平面 + 点云 + 转动到 β 的分界线
_rb = np.random.default_rng(4)
BX = _rb.normal(0, 0.38, 140); BY = np.clip(1.6 * BX + _rb.normal(0, 0.25, 140), -0.98, 0.98); BX = np.clip(BX, -0.98, 0.98)


def beta_plane(L, t, a, c=(540, 700), R=340, slope=1.6, t_rot=None, pts_k=1.0):
    yaw = 0.10 * math.sin(t * 0.12)
    g = np.linspace(-1, 1, 11)
    for v in g:
        hair(L, proj_plane(np.linspace(-1, 1, 20), np.full(20, v), *c, R=R, yaw=yaw), FOG, 0.2 * a)
        hair(L, proj_plane(np.full(20, v), np.linspace(-1, 1, 20), *c, R=R, yaw=yaw), FOG, 0.2 * a)
    xy = proj_plane(BX, BY, *c, R=R, yaw=yaw)
    cloud(L, xy, ICE, 0.75 * a * pts_k)
    k = 0.0 if t_rot is None else eio((t - t_rot) / 2.2)
    s = slope * k
    u = np.linspace(-1, 1, 30); v = np.clip(u * s, -1, 1)
    ok = np.abs(u * s) <= 1.0
    if ok.sum() > 1:
        hair(L, proj_plane(u[ok], v[ok], *c, R=R, yaw=yaw), GOLD_C, 0.9 * a, th=2)


def dia_s2(L, t):
    a = stage(t, B_S2, B_S3)
    if a <= 0: return
    beta_plane(L, t, a, t_rot=B_S2 + 0.6)


def txt_s2(img, t, subs):
    ad, ac, ar = A3(t, B_S2, B_S3)
    seg_label(img, 'I · The question', ad)
    card(img, 72, 1150, 'β', '贝塔', 'Beta, the textbook measure', ['股价相对大盘的波动越大，', '就被认为风险越高'], ac)
    readout(img, 'β  =  Cov( r , rₘ )  ⁄  Var( rₘ )', ar)
    kd = ke(t, wt('S2', '更危险') - 0.1)
    readout(img, 'β ↑  ⇒  更危险', ar * kd, y=272, col=NUM)
    text(img, '市场收益 rₘ', 860, 1010, 20, 'ebg_i', DESC, ad * 0.9, 'm', shadow=0.0)
    status(img, f'NODE 01 / 08   T+{max(0.0, t - B_S1 - 0.4):04.1f}', ad)


# ---------------------------------------------------------------- S3：1994 年的大会影像，放在一个很淡的细边框“展柜”里
def frame_box(img, cx, cy, w, h, a):
    x0, y0, x1, y1 = cx - w / 2 - 12, cy - h / 2 - 12, cx + w / 2 + 12, cy + h / 2 + 12
    for p, q in (((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))):
        line(img, p, q, RULE * 1.6, a, 1)
    for (x, y), (dx, dy) in (((x0, y0), (1, 1)), ((x1, y0), (-1, 1)), ((x0, y1), (1, -1)), ((x1, y1), (-1, -1))):
        line(img, (x, y), (x + 22 * dx, y), DESC, a * 0.8, 1); line(img, (x, y), (x, y + 22 * dy), DESC, a * 0.8, 1)


def archival(img, fr, cx, cy, w, h, a, zoom=1.0, pan=(0.0, 0.0)):
    if a <= 0.003: return
    window(img, grade(fr, sat=0.38, gain=0.86, lift=0.0), cx, cy, w, h, zoom=zoom, pan=pan, a=a, feather=18)
    frame_box(img, cx, cy, w, h, a)


def txt_s3(img, t, subs):
    ad, ac, ar = A3(t, B_S3, B_CTX)
    seg_label(img, 'I · The question', ad)
    if ad > 0:
        archival(img, CLIPS[200].get((t - B_S3) % 15.5), W / 2, 600, 1000, 405, ad)
        text(img, '画面：1994 年伯克希尔股东大会现场', 52, 838, 20, 'serif_med', DESC, ad, 'l', track=0.08, shadow=0.0)
    card(img, 72, 1080, '1994', '伯克希尔股东大会', 'Berkshire Hathaway Annual Meeting', ['一位股东当面追问巴菲特：', '你们说的风险，到底是什么？'][:1 + (t > wt('S3', '你们') - 0.2)],
         ac, desc_col=NUM, desc_size=30)
    status(img, f'NODE 01 / 08   T+{max(0.0, t - B_S1 - 0.4):04.1f}', ad)


# ---------------------------------------------------------------- 背景卡
def dia_ctx(L, t):
    a = stage(t, B_CTX, B_QA)
    if a <= 0: return
    c = (540, 600)
    node(L, c, GOLD_C, a * (0.9 + 0.15 * math.sin(t * 1.2)), 1.4)
    ring(L, c, 26, GOLD_H, 0.5 * a); ring(L, c, 150, FOG, 0.16 * a)
    rng = np.random.default_rng(2)
    ang = rng.uniform(0, 2 * math.pi, 9)
    for i, an in enumerate(ang):                          # 扇入：九个点沿曲线汇向中心
        p0 = np.array([c[0] + 330 * math.cos(an), c[1] + 260 * math.sin(an)])
        mid = (p0 + np.array(c)) / 2 + np.array([-math.sin(an), math.cos(an)]) * 60
        k = eio((t - B_CTX - 0.4 - i * 0.12) / 1.4)
        u = np.linspace(0, k, 24)[:, None]
        bz = (1 - u) ** 2 * p0 + 2 * (1 - u) * u * mid + u ** 2 * np.array(c)
        hair(L, bz, ICE, 0.28 * a); node(L, p0, ICE, 0.6 * a, 0.7)


def txt_ctx(img, t, subs):
    ad, ac, ar = A3(t, B_CTX, B_QA)
    seg_label(img, 'II · 1994 · Omaha', ad)
    card(img, 72, 940, '1994 · 04 · 25', '伯克希尔·哈撒韦年度股东大会', 'Omaha, Nebraska · Morning session',
         ['上午场 · 股东问答 · CNBC 巴菲特档案第 50 章', '以下为原始录像节选，画面与声音均为现场原始记录'], ac, big_size=80)


# ---------------------------------------------------------------- 原始问答：细边框里的原始录像 + 每段一个小图解与读数
WIN_W, WIN_H, WIN_Y = 1000, 405, 470


def qa_a(t):
    return stage(t, B_QA, B_INS)


def qa_env(t, sc, post=0.0):
    s = QSC.get(sc)
    if not s: return 0.0
    return env(t, s['t0'] + 0.15, s['t1'] - 0.05 + post, 0.5, 0.6)


def dia_qa(L, t):
    a = qa_a(t)
    if a <= 0: return
    dots_wave(L, t, 700, 1000, 742, 18, a)
    # 提问：两种风险观
    s = qa_env(t, 'ask') * a
    if s > 0:
        k2 = ke(t, qs('Q2')); k3 = ke(t, qs('Q3'))
        node(L, (300, 940), GOLD_C, s * k2, 1.3); ring(L, (300, 940), 22, GOLD_H, 0.45 * s * k2)
        cc = np.random.default_rng(1).normal(0, 1, (40, 2)) * 26 + (780, 940) + np.sin(t * 7 + np.arange(80).reshape(40, 2)) * 9
        cloud(L, cc, ICE, 0.6 * s * k3)
        hair(L, [(340, 940), (730, 940)], FOG, 0.22 * s * ke(t, qs('Q3', 1.0)))
    # 定义：一圈 36 个点，其中几个变成琥珀色——“受到伤害或损失的可能性”
    s = qa_env(t, 'define') * a
    if s > 0:
        c = (540, 950)
        an = np.linspace(0, 2 * math.pi, 36, endpoint=False) + t * 0.05
        xy = np.c_[c[0] + 150 * np.cos(an), c[1] + 110 * np.sin(an)]
        bad = np.array([3, 11, 17, 26, 31])
        kb = ke(t, qs('A1', 1.0), 1.0)
        for i, p in enumerate(xy):
            isb = i in bad
            node(L, p, AMBER if (isb and kb > 0.5) else ICE, s * (0.55 + 0.35 * (isb * kb)), 0.6 + 0.3 * isb * kb)
        node(L, c, GOLD_C, s * 0.9, 1.2)
        kt = ke(t, qs('A2', 1.5), 1.0)
        if kt > 0:
            hair(L, [(200, 1110), (200 + 680 * kt, 1110)], FOG, 0.35 * s)
            for i in range(9):
                if 200 + i * 85 <= 200 + 680 * kt: node(L, (200 + i * 85, 1110), FOG, 0.5 * s, 0.5)
    # 持有一天
    s = qa_env(t, 'horizon') * a
    if s > 0:
        x0, x1, y0 = 180, 900, 990
        hair(L, [(x0, y0), (x1, y0)], FOG, 0.3 * s)
        k = eio((t - qs('A3', 2.0)) / 6.0) if t < qs('A4') else 0.7 + 0.3 * ke(t, qs('A4'), 1.0)
        n = int(48 * k)
        rng = np.random.default_rng(6)
        ys = y0 - np.cumsum(rng.normal(0, 9, 48)); ys -= ys[0] - y0
        for i in range(n):
            node(L, (x0 + i * 15, ys[i]), ICE, 0.55 * s, 0.55)
        k6 = ke(t, qs('A6'))
        if k6 > 0:
            node(L, (x1 + 20, y0 - 70), GOLD_C, s * k6, 1.1); node(L, (x1 + 20, y0 + 70), AMBER, s * k6, 1.1)
            hair(L, [(x0 + (n - 1) * 15, ys[max(n - 1, 0)]), (x1 + 20, y0 - 70)], GOLD_H, 0.3 * s * k6)
            hair(L, [(x0 + (n - 1) * 15, ys[max(n - 1, 0)]), (x1 + 20, y0 + 70)], AMBER, 0.3 * s * k6)
    # 可口可乐：同一家公司，两个持有期
    s = qa_env(t, 'coke') * a
    if s > 0:
        k1 = ke(t, qs('A8'), 1.0); k2 = ke(t, qs('A10'), 1.0)
        n = int(26 * eio((t - qs('A8')) / 4.0))
        for i in range(n):
            node(L, (180 + i * 27, 930 - i * 4.2 + 6 * math.sin(i * 1.7)), GOLD_C if i == n - 1 else GOLD_H, s * 0.7 * k1, 0.6)
        hair(L, [(180, 950), (900, 950)], FOG, 0.2 * s * k1)
        if k2 > 0:
            for i in range(8):
                node(L, (180 + i * 14, 1110 + 30 * math.sin(t * 6 + i * 2.1)), ICE, s * 0.7 * k2, 0.6)
            hair(L, [(180, 1110), (900, 1110)], FOG, 0.2 * s * k2)
    # 贝塔：倾斜网格 + 点云
    s = qa_env(t, 'beta') * a
    if s > 0:
        beta_plane(L, t, s, c=(540, 980), R=230, t_rot=qs('A14'))
    # 荒谬：A 每年 +20%～+80%，B 每年稳定 +5%；零线
    s = qa_env(t, 'absurd') * a
    if s > 0:
        y0 = 1130
        hair(L, [(150, y0), (930, y0)], FOG, 0.35 * s)
        kA = eio((t - qs('A17')) / 2.0); kB = eio((t - qs('A18')) / 2.0)
        va = [62, 25, 78, 41, 20, 70, 33, 55]
        for i in range(int(8 * kA + 0.01)):
            x = 190 + i * 50; y = y0 - va[i] * 3.0
            node(L, (x, y), ICE, s * 0.85, 0.8); hair(L, [(x, y0), (x, y)], ICE, 0.12 * s)
        for i in range(int(8 * kB + 0.01)):
            x = 590 + i * 45; y = y0 - 5 * 3.0
            node(L, (x, y), GOLD_C, s * 0.85, 0.8)
    # 期望：一组同类、相互独立的交易
    s = qa_env(t, 'expect') * a
    if s > 0:
        rng = np.random.default_rng(9)
        outs = rng.normal(0.35, 1.0, 60)
        n = int(60 * eio((t - qs('A21')) / 9.0))
        for i in range(n):
            x = 190 + (i % 20) * 37; y = 920 + (i // 20) * 58
            node(L, (x, y), GOLD_C if outs[i] > 0 else AMBER, s * (0.5 + 0.25 * min(abs(outs[i]), 1.5)), 0.6)
        if t > qs('A24'):
            k = ke(t, qs('A25'), 1.0)
            node(L, (540, 1140), GOLD_C, s * k * 1.2, 1.4); ring(L, (540, 1140), 24, GOLD_H, 0.5 * s * k)
            for i in range(0, 60, 6):
                x = 190 + (i % 20) * 37; y = 920 + (i // 20) * 58
                if i < n: hair(L, [(x, y), (540, 1140)], FOG, 0.12 * s * k)
    # 芒格：概率树（费马与帕斯卡的“点数问题”）
    s = qa_env(t, 'munger', post=0.6) * a
    if s > 0:
        k = eio((t - qs('M1', 1.5)) / 2.0)
        root = np.array([660, 880])
        lv = [[root]]
        for d in range(3):
            nxt = []
            for p in lv[-1]:
                for sgn in (-1, 1):
                    nxt.append(p + np.array([sgn * 200 / (d + 1), 95]))
            lv.append(nxt)
        node(L, root, GOLD_C, s, 1.2)
        for d in range(1, 4):
            kd = cl(k * 3 - (d - 1))
            if kd <= 0: continue
            for j, p in enumerate(lv[d]):
                par = lv[d - 1][j // 2]
                hair(L, [par, par + (p - par) * kd], FOG, 0.3 * s)
                if kd > 0.9: node(L, p, GOLD_C if (d == 3 and j % 3 != 1) else ICE, s * 0.7, 0.7)


def txt_qa(img, t, subs):
    a = qa_a(t)
    if a <= 0: return
    seg_label(img, 'II · 1994 · Original Q&A', a)
    src = qa_src(t)
    fr = QA_CLIP.get(src)
    mz = eio((t - QA['munger_t'] + 1.0) / 2.5)
    wa = 1.0
    for ct in QA['cuts']:                                       # 省略处：画面暗下去再亮起，不硬切
        wa = min(wa, 1 - 0.9 * math.exp(-((t - ct) / 0.28) ** 2))
    archival(img, fr, W / 2, WIN_Y, WIN_W, WIN_H, a * wa, zoom=1.0 + 0.32 * mz + 0.02 * math.sin((t - T_Q) * 0.05),
             pan=(0.17 * mz, -0.03 * mz))
    for ct in QA['cuts']:
        k = env(t, ct - 0.5, ct + 0.7, 0.25, 0.35)
        if k > 0: text(img, '· 节选 ·', W / 2, WIN_Y, 30, 'serif_med', NUM, a * k, track=0.3, shadow=0.0)
    mt, at = QA['munger_t'], QA['answer_t']
    if t >= mt - 0.3: spk = ('查理·芒格', 'Charlie Munger')
    elif t >= at - 0.2: spk = ('沃伦·巴菲特', 'Warren Buffett')
    else: spk = ('提问 · 来自密歇根州的股东', 'Shareholder from Michigan')
    text(img, spk[0], 52, 726, 30, 'serif_med', NUM, a, 'l', track=0.08, shadow=0.0)
    text(img, spk[1], 52, 764, 22, 'ebg_i', DESC, a, 'l', shadow=0.0)
    text(img, '画面与声音：1994 年上午场原始录像（节选）', 1008, 790, 19, 'serif_med', DESC, a * 0.85, 'r', track=0.06, shadow=0.0)
    # 各段的读数与标签
    s = qa_env(t, 'ask') * a
    if s > 0:
        text(img, '您的风险观', 300, 1010, 30, 'serif_med', NUM, s * ke(t, qs('Q2')), track=0.08, shadow=0.0)
        text(img, '传统的风险观', 780, 1010, 30, 'serif_med', NUM, s * ke(t, qs('Q3')), track=0.08, shadow=0.0)
        text(img, '≠', W / 2 + 0, 925, 40, 'ebg', DESC, s * ke(t, qs('Q3', 1.0)), shadow=0.0)
        readout(img, 'β  =  Cov( r , rₘ )  ⁄  Var( rₘ )', s * ke(t, qs('Q5')))
        readout(img, '自相矛盾？', s * ke(t, qs('Q5', 1.6)), y=272, col=NUM, size=30)
    s = qa_env(t, 'define') * a
    if s > 0:
        readout(img, 'Risk  =  P( harm or injury )', s * ke(t, qs('A1', 0.3)))
        text(img, '受到伤害或损失的可能性', W / 2, 950, 28, 'serif_med', NUM, s * ke(t, qs('A1', 1.2)), track=0.1, shadow=0.0)
        readout(img, 'Risk  =  f ( T )', s * ke(t, qs('A2', 1.5)), y=272, col=NUM)
        text(img, '持有期 T', 900, 1150, 22, 'serif_med', DESC, s * ke(t, qs('A2', 2.0)), 'r', track=0.1, shadow=0.0)
    s = qa_env(t, 'horizon') * a
    if s > 0:
        text(img, '11:30 买入', 180, 1040, 24, 'serif_med', NUM, s * ke(t, qs('A3', 2.0)), 'l', shadow=0.0)
        text(img, '收盘前卖出', 900, 1040, 24, 'serif_med', NUM, s * ke(t, qs('A4')), 'r', shadow=0.0)
        readout(img, 'P( loss )  ≈  50 %', s * ke(t, qs('A6')))
    s = qa_env(t, 'coke') * a
    if s > 0:
        text(img, '以当初的买入价 · 长期持有可口可乐', 180, 875, 24, 'serif_med', NUM, s * ke(t, qs('A8')), 'l', shadow=0.0)
        text(img, 'Risk ≈ 0', 900, 830, 30, 'ebg', NUM, s * ke(t, qs('A9', 0.8)), 'r', shadow=0.0)
        text(img, '今天上午买入 · 明天上午卖出', 180, 1060, 24, 'serif_med', NUM, s * ke(t, qs('A10')), 'l', shadow=0.0)
        text(img, 'Risk ≫ 0', 900, 1060, 30, 'ebg', AMBER, s * ke(t, qs('A11')), 'r', shadow=0.0)
    s = qa_env(t, 'beta') * a
    if s > 0:
        k15 = ke(t, qs('A15'), 0.6)
        readout(img, 'Risk  ≡  σ', s * ke(t, qs('A14')) * (1 - k15))
        readout(img, 'Risk  ≠  σ', s * k15, col=NUM)
        text(img, '学术界 → 金融市场：用波动定义风险，贝塔衡量波动', W / 2, 1200, 22, 'serif_med', DESC, s * ke(t, qs('A13')), track=0.06, shadow=0.0)
    s = qa_env(t, 'absurd') * a
    if s > 0:
        text(img, '投资 A · 每年 +20% ～ +80%', 365, 870, 22, 'serif_med', ICE, s * ke(t, qs('A17')), track=0.04, shadow=0.0)
        text(img, '投资 B · 每年稳定 +5%', 750, 1060, 22, 'serif_med', GOLD_H, s * ke(t, qs('A18')), track=0.04, shadow=0.0)
        text(img, '0%', 140, 1130, 20, 'ebg', DESC, s, 'r', shadow=0.0)
        k4 = ke(t, qs('A19'), 0.6)
        readout(img, 'σ( A )  >  σ( B )   ⇒   Risk( A )  >  Risk( B ) ?', s * ke(t, qs('A18', 2.0)) * (1 - k4), size=28)
        readout(img, 'haywire  ·  乱了套', s * k4, col=NUM)
    s = qa_env(t, 'expect') * a
    if s > 0:
        text(img, '单笔交易：可以亏', 190, 870, 24, 'serif_med', NUM, s * ke(t, qs('A21')), 'l', track=0.06, shadow=0.0)
        n = int(60 * eio((t - qs('A21')) / 9.0))
        counter(img, f'N = {n}', s * ke(t, qs('A22')), y=272)
        readout(img, 'E[ Σ Xₖ ]  >  0', s * ke(t, qs('A25')))
    s = qa_env(t, 'munger', post=0.6) * a
    if s > 0:
        k1 = ke(t, qs('M1', 1.0), 0.9)
        text(img, 'Fermat  ·  Pascal', 72, 880, 40, 'ebg_i', NUM, s * k1, 'l', shadow=0.0)
        text(img, '费马 · 帕斯卡', 72, 928, 24, 'serif_med', DESC, s * k1, 'l', track=0.1, shadow=0.0)
        text(img, '像从没听说过现代金融理论那样，用概率思考', W / 2, 1210, 22, 'serif_med', DESC, s * ke(t, qs('M2')), 'm', track=0.04, shadow=0.0)
        readout(img, 'E  =  Σ pᵢ xᵢ', s * ke(t, qs('M1', 2.0)))
    if subs:
        for sb in QA['subs']:
            sa = env(t, sb['t0'], sb['t1'], 0.07, 0.07)
            if sa > 0: orig_sub(img, sb, sa * a)
        la = env(t, TL['laugh']['t0'], TL['laugh']['t1'], 0.15, 0.2)
        if la > 0: text(img, '（现场笑声）', W / 2, 1290, 26, 'serif_med', DESC, la * a, track=0.1, shadow=0.0)


# ================================================================ 投资启示（本片解读）
NOTE = '本片解读，非巴菲特或芒格原话'
CARD_Y = 1130


def ins_status(img, t, k, b, a):
    status(img, f'NODE {k:02d} / 08   T+{max(0.0, t - b - 0.4):04.1f}', a)


# ---------------------------------------------------------------- 启示标题 + I1：剧烈抖动的冰青点云（教科书：波动 β）vs 稳定发光的金色节点（巴菲特：损失的可能性）
_ri = np.random.default_rng(21)
I1_P = _ri.normal(0, 1, (90, 2)); I1_F = _ri.uniform(3, 11, (90, 2)); I1_PH = _ri.uniform(0, 6.3, (90, 2))


def dia_i1(L, t):
    a = stage(t, B_INS, B_I2)
    if a <= 0: return
    kc = ke(t, wt('I1', '教科书') - 0.2, 0.8); kg = ke(t, wt('I1', '受到伤害') - 0.2, 0.8)
    xy = np.c_[330 + I1_P[:, 0] * 70, 560 + I1_P[:, 1] * 55] + np.sin(t * I1_F + I1_PH) * 22
    cloud(L, xy, ICE, 0.6 * a * (0.25 + 0.75 * kc))
    c = (760, 860)
    node(L, c, GOLD_C, a * (0.35 + 0.75 * kg) * (0.92 + 0.08 * math.sin(t * 1.1)), 1.5)
    ring(L, c, 26, GOLD_H, 0.5 * a * kg); ring(L, c, 120, FOG, 0.14 * a * kg)


def txt_i1(img, t, subs):
    ad, ac, ar = A3(t, B_INS, B_I2)
    seg_label(img, 'III · Insight', ad, NOTE)
    k0 = env(t, B_INS + 0.4, I['I1']['t0'] + 0.3, 0.6, 0.6)
    text(img, '投资启示', W / 2, 1180, 80, 'serif_med', TXT, ad * k0, track=0.2, shadow=0.0, glow=0.18, glow_col=GOLD_H)
    text(img, 'INSIGHT', W / 2, 1265, 16, 'sans', DESC, ad * k0, track=0.8, shadow=0.0)
    kc = ke(t, wt('I1', '教科书') - 0.2); kg = ke(t, wt('I1', '受到伤害') - 0.2)
    text(img, '价格的波动', 330, 710, 26, 'serif_med', NUM, ad * kc, track=0.1, shadow=0.0)
    text(img, 'volatility · σ, β', 330, 748, 21, 'ebg_i', DESC, ad * kc, shadow=0.0)
    text(img, '损失的可能性', 760, 1005, 26, 'serif_med', NUM, ad * kg, track=0.1, shadow=0.0)
    text(img, 'possibility of loss', 760, 1043, 21, 'ebg_i', DESC, ad * kg, shadow=0.0)
    kk = ac * ke(t, I['I1']['t0'] + 0.3)
    card(img, 72, CARD_Y + 110, 'Risk', '两种风险', 'Two definitions of risk', ['教科书：价格的波动（贝塔）', '巴菲特：受到伤害或损失的可能性'], kk, big_size=80)
    readout(img, 'σ , β    vs    P( loss )', ar * ke(t, wt('I1', '贝塔')))
    ins_status(img, t, 3, B_INS, ad)


# ---------------------------------------------------------------- I2：持有期——一串点从“买入”走到“持有期结束”，终点落在购买力那条线之上
_r2 = np.random.default_rng(8)
I2_Y = 760 - np.cumsum(_r2.normal(-1.6, 16, 33)); I2_Y += 760 - I2_Y[0]; I2_Y[-1] = 690


def dia_i2(L, t):
    a = stage(t, B_I2, B_I3)
    if a <= 0: return
    x0, x1, y0 = 150, 900, 760
    hair(L, [(x0, y0), (x1 + 60, y0)], FOG, 0.3 * a)                             # 当初的购买力
    k = eio((t - wt('I2', '持有期') + 0.3) / (wt('I2', '购买力') - wt('I2', '持有期') + 0.3))
    n = max(1, int(33 * k))
    xs = np.linspace(x0, x1, 33)
    for i in range(n):
        node(L, (xs[i], I2_Y[i]), ICE, a * 0.7, 0.6)
        if i: hair(L, [(xs[i - 1], I2_Y[i - 1]), (xs[i], I2_Y[i])], ICE, 0.22 * a)
    node(L, (x0, y0), GOLD_C, a * 0.9, 1.0)
    kp = ke(t, wt('I2', '购买力') - 0.1)
    if kp > 0:
        node(L, (x1, I2_Y[-1]), GOLD_C, a * kp * 1.1, 1.4); ring(L, (x1, I2_Y[-1]), 24, GOLD_H, 0.5 * a * kp)
        hair(L, [(x1, I2_Y[-1]), (x1, y0)], GOLD_H, 0.3 * a * kp)


def txt_i2(img, t, subs):
    ad, ac, ar = A3(t, B_I2, B_I3)
    seg_label(img, 'III · Insight', ad, NOTE)
    text(img, '买入', 150, 805, 24, 'serif_med', NUM, ad, 'm', track=0.1, shadow=0.0)
    text(img, '持有期结束', 900, 620, 24, 'serif_med', NUM, ad * ke(t, wt('I2', '拿回') - 0.3), 'm', track=0.1, shadow=0.0)
    text(img, '当初的购买力', 960, 795, 20, 'serif_med', DESC, ad * ke(t, wt('I2', '购买力') - 0.2), 'r', track=0.08, shadow=0.0)
    card(img, 72, CARD_Y, '1993', '致股东信', 'Berkshire letter to shareholders',
         ['真正的风险：持有期结束时，', '能否保住当初的购买力', '“…at least as much purchasing power as he had to begin with…”'], ac)
    readout(img, 'W( T ) ⁄ P( T )   ≥   W( 0 ) ⁄ P( 0 )', ar * ke(t, wt('I2', '购买力') - 0.1))
    ins_status(img, t, 3, B_INS, ad)


# ---------------------------------------------------------------- I3：一排点上下乱跳（波动）；一颗金色节点始终亮着（钱还在不在）
def dia_i3(L, t):
    a = stage(t, B_I3, B_WAPO)
    if a <= 0: return
    for i in range(11):
        x = 180 + i * 72
        y = 600 + 120 * math.sin(t * 2.3 + i * 1.7) * math.sin(t * 0.9 + i)
        node(L, (x, y), ICE, a * 0.8, 0.7)
        hair(L, [(x, 600), (x, y)], ICE, 0.10 * a)
    hair(L, [(150, 600), (930, 600)], FOG, 0.2 * a)
    kg = ke(t, wt('I3', '风险') - 0.1)
    node(L, (540, 920), GOLD_C, a * kg * (0.95 + 0.1 * math.sin(t * 1.2)), 1.5); ring(L, (540, 920), 26, GOLD_H, 0.5 * a * kg)


def txt_i3(img, t, subs):
    ad, ac, ar = A3(t, B_I3, B_WAPO)
    seg_label(img, 'III · Insight', ad, NOTE)
    text(img, '波动：价格摆动的幅度', W / 2, 780, 26, 'serif_med', NUM, ad, track=0.1, shadow=0.0)
    text(img, '风险：钱还在不在', W / 2, 1010, 30, 'serif_med', TXT, ad * ke(t, wt('I3', '风险') - 0.1), track=0.12, shadow=0.0)
    card(img, 72, CARD_Y + 60, '≠', '波动不是风险', 'Volatility is not risk', [], ac)
    readout(img, 'σ   ≠   P( loss )', ar)
    ins_status(img, t, 3, B_INS, ad)


# ---------------------------------------------------------------- 华盛顿邮报：生意（金色点云）越长越大，价格（冰青节点）先跌 25% 再涨
WAPO_V = [1.06, 0.80, 0.9, 1.1, 1.3, 1.6, 2.0, 2.4, 3.0, 3.6, 4.4, 5.5, 7.0, 8.6, 10.5, 13.0, 16.5, 20.5, 26.0, 33.0, 44.0]


def wapo_xy(i):
    return 160 + i * 38, 1000 - math.log10(WAPO_V[i] / 0.8) * 150


def dia_wapo(L, t):
    a = stage(t, B_WAPO, B_DEX)
    if a <= 0: return
    g = eio((t - I['I6']['t0']) / 5.5)
    R = 90 + 130 * g
    xy, dep = sphere_xy((540, 480), R, t)
    cloud(L, xy, GOLD_H, 0.42 * a, w=dep * (0.6 + 0.4 * g))
    node(L, (540, 480), GOLD_C, a * (0.5 + 0.6 * g), 1.2)
    # 价格：1973 → 1974（−25%）在风暴里抖动；I6 起一路走到 1993
    storm = (1 - eio((t - I['I6']['t0']) / 1.5)) * ke(t, B_WAPO + 0.4, 0.3)
    n = 1 + int(ke(t, wt('I4', '一九七四') - 0.2, 0.6) > 0.5) + int(19 * eio((t - I['I6']['t0'] - 0.5) / 4.5))
    prev = None
    for i in range(min(n, len(WAPO_V))):
        x, y = wapo_xy(i)
        y += storm * 14 * math.sin(t * 9 + i * 2.3)
        node(L, (x, y), AMBER if i == 1 else ICE, a * 0.8, 0.7 + 0.3 * (i == 1))
        if prev: hair(L, [prev, (x, y)], ICE, 0.25 * a)
        prev = (x, y)
    hair(L, [(150, 1000), (940, 1000)], FOG, 0.16 * a)


def txt_wapo(img, t, subs):
    ad, ac, ar = A3(t, B_WAPO, B_DEX)
    seg_label(img, 'IV · The Washington Post', ad, NOTE)
    td, t6, tg = wt('I4', '八百万'), I['I6']['t0'], wt('I6', '超过')
    text(img, '1973', 160, 1040, 20, 'ebg', DESC, ad, 'm', shadow=0.0)
    text(img, '1974', 198, 1068, 20, 'ebg', AMBER, ad * ke(t, wt('I4', '一九七四')), 'm', shadow=0.0)
    text(img, '1993', 920, 700, 20, 'ebg', DESC, ad * ke(t, t6 + 4.0), 'm', shadow=0.0)
    text(img, '生意', 540, 355 - 130 * eio((t - t6) / 5.5), 22, 'serif_med', DESC, ad * ke(t, t6), 'm', track=0.2, shadow=0.0)
    # 节点卡随叙述换页：旧卡淡出（不位移），新卡淡入并上移
    pages = [(B_WAPO, '1973', ['伯克希尔买入，成本 1,060 万美元']),
             (td - 0.2, '1974', ['年底市值只剩 800 万美元，−25%', '按贝塔理论：它反而“更危险”了']),
             (tg - 0.2, '1993', ['二十年后，持股市值 4.40 亿美元', '生意一直在增长'])]
    for j, (p0, big, desc) in enumerate(pages):
        p1 = pages[j + 1][0] if j + 1 < len(pages) else 1e9
        kin = 1.0 if j == 0 else ke(t, p0, 0.6)
        kout = 1 - eio((t - p1) / 0.35)
        if j == 1 and t < I['I5']['t0'] - 0.1: desc = desc[:1]
        card(img, 72, CARD_Y, big, '华盛顿邮报', 'The Washington Post', desc, ac * kin * kout, rise=6 * (1 - kin))
    v = 10.6 if t < td - 0.2 else (8.0 if t < tg else 8.0 + (440 - 8.0) * eio((t - tg) / 1.8))
    counter(img, f'$ {v * 1e6:,.0f}', ar, col=AMBER if td - 0.2 <= t < tg else NUM)
    readout(img, 'β ↑   ⇒   “risk” ↑', ar * env(t, I['I5']['t0'] - 0.1, t6, 0.4, 0.4))
    ins_status(img, t, 4, B_WAPO, ad)


# ---------------------------------------------------------------- 德克斯特：一动不动的金色点云（没有股价）→ 海外竞争让它散成星尘（价值归零）→ 付出去的股票长成 57 亿
_rd = np.random.default_rng(31)
DEX_V = _rd.normal(0, 1, (len(SPHERE), 2))


def dia_dex(L, t):
    a = stage(t, B_DEX, B_LEV)
    if a <= 0: return
    ts, tz, t57 = wt('I9', '海外'), wt('I9', '价值归零'), wt('I10', '五十七')
    sc = eio((t - ts) / (tz - ts + 1.2))
    xy, dep = sphere_xy((540, 600), 200, 0.0, spin=0.0)                   # 完全静止
    xy = xy + DEX_V * 260 * sc ** 1.5 + np.c_[np.zeros(len(xy)), np.full(len(xy), 120 * sc ** 2)]
    cloud(L, xy, GOLD_H, 0.42 * a * (1 - 0.85 * sc), w=dep)
    node(L, (540, 600), GOLD_C, a * (1 - sc) * 0.9, 1.2)
    k8 = ke(t, wt('I8', '波动') - 0.1, 0.8) * (1 - eio((t - ts) / 1.0))
    if k8 > 0:
        xs = np.linspace(160, 920, 21)
        for x in xs: node(L, (x, 960), ICE, a * k8 * 0.6, 0.5)
        hair(L, [(150, 960), (930, 960)], ICE, 0.25 * a * k8)
    k10 = eio((t - t57 + 0.1) / 1.6)
    if k10 > 0:
        xy2, dep2 = sphere_xy((540, 600), 40 + 230 * k10, t, spin=0.08)
        cloud(L, xy2, AMBER, 0.6 * a * k10, w=dep2)


def txt_dex(img, t, subs):
    ad, ac, ar = A3(t, B_DEX, B_LEV)
    seg_label(img, 'V · Dexter Shoe', ad, NOTE)
    ts, tz, t57 = wt('I9', '海外'), wt('I9', '价值归零'), wt('I10', '五十七')
    pages = [(B_DEX, '1993', ['以价值 4.33 亿美元的伯克希尔股票，', '全资收购德克斯特鞋业']),
             (I['I8']['t0'] - 0.2, '1993', ['全资收购，没有股价，', '也就没有一天的波动']),
             (ts - 0.2, '1990s', ['几年之内，海外竞争', '让它的优势荡然无存——价值归零']),
             (t57 - 0.2, '2014', ['当初付出的股票，2014 年值 57 亿美元', '“To date, Dexter is the worst deal that I’ve made.”', '—— 巴菲特，2007 年致股东信'])]
    for j, (p0, big, desc) in enumerate(pages):
        p1 = pages[j + 1][0] if j + 1 < len(pages) else 1e9
        kin = 1.0 if j == 0 else ke(t, p0, 0.6)
        kout = 1 - eio((t - p1) / 0.35)
        card(img, 72, CARD_Y, big, '德克斯特鞋业', 'Dexter Shoe', desc, ac * kin * kout, rise=6 * (1 - kin))
    if t < t57 - 0.2:
        v = 433e6 * (1 - eio((t - ts) / (tz - ts + 0.6)))
        counter(img, f'$ {v:,.0f}', ar, col=AMBER if t > ts else NUM)
    else:
        v = 433e6 + (5.7e9 - 433e6) * eio((t - t57) / 1.6)
        counter(img, f'$ {v:,.0f}', ar, col=AMBER)
    readout(img, 'σ  =  0', ar * env(t, wt('I8', '波动') - 0.1, ts, 0.4, 0.4))
    readout(img, 'value  →  0', ar * env(t, tz - 0.1, t57 - 0.2, 0.4, 0.4), col=AMBER)
    text(img, '所付出的伯克希尔股票', W / 2, 885, 22, 'serif_med', AMBER, ad * ke(t, t57 + 0.6), track=0.1, shadow=0.0)
    ins_status(img, t, 5, B_DEX, ad)


# ---------------------------------------------------------------- 杠杆：节点骑在价格的浪上，一根琥珀细线把它拴向下方（借来的钱）；被迫在低点卖出时被拉下去，熄灭
def lev_wave(x, t, amp):
    return 780 + amp * math.sin(x * 0.012 - t * 2.0)


def dia_lev(L, t):
    a = stage(t, B_LEV, B_TODAY)
    if a <= 0: return
    tp = wt('I11', '低点卖出'); tc = wt('I11', '暂时')
    amp = 110 * (1 - 0.8 * eio((t - tc - 1.0) / 3.0))
    xs = np.linspace(120, 960, 64)
    ys = np.array([lev_wave(x, t, amp) for x in xs])
    cloud(L, np.c_[xs, ys], ICE, 0.75 * a)
    anc = (540, 1080)
    # 节点：在卖出时刻定格在浪谷（钉在最低处），随后被拉到下方、熄灭
    tt = min(t, tp)
    yr = lev_wave(540, tt, 110) - 28
    trough = 780 + 110 - 28
    yf = lerp(yr, trough, eio((t - tp) / 0.4))
    fall = eio((t - tp - 0.4) / 1.0)
    y = lerp(yf, anc[1] - 18, fall)
    col = GOLD_C * (1 - fall) + np.array([0.35, 0.35, 0.38], np.float32) * fall
    node(L, (540, y), col, a * (1.0 - 0.75 * fall), 1.3)
    kt = ke(t, wt('I11', '借了钱') - 0.1) * (1 - eio((t - tp - 1.4) / 0.6))
    if kt > 0:
        hair(L, [(540, y + 10), anc], AMBER, 0.45 * a * kt)
        node(L, anc, AMBER, a * kt * 0.8, 0.9)
    kp = ke(t, wt('I11', '永久') - 0.1)
    if kp > 0: ring(L, (540, anc[1] - 18), 30, AMBER, 0.4 * a * kp)


def txt_lev(img, t, subs):
    ad, ac, ar = A3(t, B_LEV, B_TODAY)
    seg_label(img, 'VI · Leverage', ad, NOTE)
    text(img, '借来的钱', 600, 1080, 24, 'serif_med', AMBER, ad * ke(t, wt('I11', '借了钱')), 'l', track=0.1, shadow=0.0)
    text(img, '被迫在低点卖出', 600, 930, 24, 'serif_med', NUM, ad * env(t, wt('I11', '低点卖出') - 0.1, wt('I11', '暂时'), 0.4, 0.4), 'l', track=0.1, shadow=0.0)
    card(img, 72, CARD_Y + 30, 'Leverage', '杠杆与被迫卖出', 'Leverage & forced selling',
         ['暂时的下跌，', '被锁定成永久的损失'][:1 + (t > wt('I11', '永久') - 0.2)], ac * ke(t, wt('I11', '暂时') - 0.3), big_size=80, desc_col=NUM)
    readout(img, 'temporary   ⇒   permanent', ar * ke(t, wt('I11', '锁定')))
    ins_status(img, t, 6, B_LEV, ad)


# ---------------------------------------------------------------- 今天：一条回撤的点线，两个检查点
def dia_today(L, t):
    a = stage(t, B_TODAY, B_CLOSE)
    if a <= 0: return
    n = 30
    xs = np.linspace(160, 920, n)
    ys = 520 + 330 * np.clip(np.linspace(0, 1.6, n), 0, 1) ** 0.8 + 10 * np.sin(np.arange(n) * 1.9)
    k = eio((t - B_TODAY - 0.4) / 2.0)
    m = max(1, int(n * k))
    for i in range(m):
        node(L, (xs[i], ys[i]), ICE, a * 0.65, 0.6)
        if i: hair(L, [(xs[i - 1], ys[i - 1]), (xs[i], ys[i])], ICE, 0.2 * a)
    for kw, (x, y) in (('这门生意', (560, 760)), ('我会', (860, 760))):
        kk = ke(t, wt('I12', kw) - 0.1)
        if kk > 0:
            node(L, (x, y), GOLD_C, a * kk, 1.2); ring(L, (x, y), 24, GOLD_H, 0.5 * a * kk)
            hair(L, [(x, y + 24), (x, 880)], GOLD_H, 0.25 * a * kk)


def txt_today(img, t, subs):
    ad, ac, ar = A3(t, B_TODAY, B_CLOSE)
    seg_label(img, 'VII · Today', ad, NOTE)
    q1, q2 = ke(t, wt('I12', '这门生意') - 0.1), ke(t, wt('I12', '我会') - 0.1)
    text(img, '生意还在吗', 560, 700, 22, 'serif_med', NUM, ad * q1, track=0.1, shadow=0.0)
    text(img, '会被迫卖出吗', 860, 700, 22, 'serif_med', NUM, ad * q2, track=0.1, shadow=0.0)
    desc = ['这门生意还在吗？'] + (['我会被迫卖出吗？'] if q2 > 0 else [])
    card(img, 72, CARD_Y, '2', '先问两个问题', 'Two questions, when the account is down', desc if q1 > 0 else [], ac, desc_col=TXT, desc_size=34)
    readout(img, 'Drawdown   ≠   Permanent loss', ar)
    ins_status(img, t, 7, B_TODAY, ad)


# ---------------------------------------------------------------- 收尾 + 高潮：全片的节点汇成一片星图，高潮重拍上全部亮起、连线暴涨，再缓缓暗下
_rn = np.random.default_rng(55)
NET = np.c_[_rn.uniform(110, 970, 120), _rn.uniform(330, 1400, 120)]
NET_C = _rn.random(120)
NET_T = np.sort(_rn.uniform(0, 1, 120))
_d = np.linalg.norm(NET[:, None] - NET[None], axis=2)
NET_E = [(i, j) for i in range(120) for j in np.argsort(_d[i])[1:3] if i < j]


def dia_close(L, t):
    a = stage(t, B_CLOSE, B_SUM)
    if a <= 0: return
    i13 = I['I13']['t0']
    u = eio((t - i13) / (B_SUM - i13 - 0.3))                           # 节点逐个亮起，越往后越多
    for i, p in enumerate(NET):
        k = ke(t, i13 + NET_T[i] * (B_SUM - i13 - 1.0), 0.8)
        if k <= 0: continue
        br = 0.35 + 0.25 * math.sin(t * 1.3 + i)
        node(L, p, GOLD_C if NET_C[i] > 0.7 else ICE, a * k * br, 0.6)
    for i, j in NET_E:
        k = min(ke(t, i13 + NET_T[i] * (B_SUM - i13 - 1.0), 0.8), ke(t, i13 + NET_T[j] * (B_SUM - i13 - 1.0), 0.8))
        if k > 0: hair(L, [NET[i], NET[j]], FOG, 0.18 * a * k * u)


def txt_close(img, t, subs):
    ad, ac, ar = A3(t, B_CLOSE, B_SUM)
    seg_label(img, 'VIII · In one sentence', ad, NOTE)
    for kw, s_, y, col in (('价格', '价格的剧烈波动，', 720, NUM), ('不必然', '不必然意味着真正的风险；', 800, NUM),
                           ('真正值得', '真正值得警惕的，', 930, GOLD_C), ('本金', '是本金永久损失的可能性。', 1010, GOLD_C)):
        k = eio((t - wt('I13', kw) + 0.15) / 1.0)
        text(img, s_, W / 2, y + 6 * (1 - k), 50, 'serif_med', col, ad * k, track=0.12, shadow=0.6,
             glow=0.12 if col is GOLD_C else 0.0, glow_col=GOLD_H)


def dia_sum(L, t):
    """高潮：全屏节点同时亮起、连线暴涨 2~3 秒后缓缓暗下"""
    if t < B_SUM: return
    k = t - T_SUM
    on = eo(k / 0.08) if k >= 0 else 0.0
    surge = math.exp(-max(k, 0) / 1.6)
    fade = 1 - eio((t - END['t_particles'] + 0.4) / 1.4)
    a = on * fade
    if a <= 0: return
    for i, p in enumerate(NET):
        node(L, p, GOLD_C if NET_C[i] > 0.55 else ICE, a * (0.35 + 1.6 * surge), 0.7)
    for i, j in NET_E:
        hair(L, [NET[i], NET[j]], GOLD_H if NET_C[i] > 0.55 else FOG, a * (0.12 + 0.6 * surge))


# ================================================================ 一句话总结 + 品牌片尾（系列固定片尾）
def summary_masks():
    out = []
    for s, y in (('波动不是风险，', 880), ('永久损失才是。', 1010)):
        m, w, base, pad = text_mask(s, 'serif_med', 96, 0.06)
        out.append((m, int(W / 2 - w / 2 - pad), int(y + 96 * 0.36 - base)))
    return out


SUM_MASKS = summary_masks()
LOGO_CY = 760


def _particles():
    r = np.random.default_rng(13)
    pts = []
    for m, x0_, y0_ in SUM_MASKS:
        ys, xs = np.nonzero(m > 0.5)
        pts.append(np.c_[xs + x0_, ys + y0_])
    src = np.concatenate(pts).astype(np.float64)
    N = 2600
    src = src[r.choice(len(src), N, replace=len(src) < N)] + r.normal(0, 0.6, (N, 2))
    ys, xs = np.nonzero(LOGO_A > 0.35)
    pick = r.choice(len(xs), N, replace=len(xs) < N, p=LOGO_A[ys, xs] / LOGO_A[ys, xs].sum())
    dst = np.c_[xs[pick] - LOGO_PX / 2 + W / 2, ys[pick] - LOGO_PX / 2 + LOGO_CY].astype(np.float64) + r.random((N, 2)) - 0.5
    col = LOGO_RGB[ys[pick], xs[pick]].astype(np.float32)
    delay = r.random(N) * 0.6
    swirl = r.normal(0, 1, (N, 2)) * 90
    return src, dst, col, delay, swirl


PSRC, PDST, PCOL, PDEL, PSW = _particles()


def txt_sum(img, t, subs):
    tp = END['t_particles']
    a = env(t, T_SUM - 0.05, tp + 0.4, 0.05, 0.4)
    if a <= 0: return
    k = t - T_SUM
    seg_label(img, 'VIII · In one sentence', a * eo(k / 1.0))
    w1 = eio((t - VOD['M']['t0'] + 0.15) / 1.1); w2 = eio((t - wt('M', '永久') + 0.1) / 1.1)
    br = 0.16 + 0.12 * (0.5 - 0.5 * math.cos(2 * math.pi * max(0.0, t - VOD['M']['t1']) / 1.6))   # 呼吸两次
    text(img, '波动不是风险，', W / 2, 880, 96, 'serif_med', GOLD_C, a, wipe=w1, track=0.06, shadow=0.0, glow=br, glow_col=GOLD_H)
    text(img, '永久损失才是。', W / 2, 1010, 96, 'serif_med', GOLD_C, a, wipe=w2, track=0.06, shadow=0.0, glow=br, glow_col=GOLD_H)
    text(img, 'VOLATILITY IS NOT RISK · PERMANENT LOSS IS', W / 2, 1110, 15, 'sans', DESC, a * eo((t - wt('M', '永久') - 0.6) / 0.8), track=0.5, shadow=0.0)


def s_end(img, t):
    tp, tl_, tb = END['t_particles'], END['t_logo'], END['t_brand']
    if t < tp: return
    fade = 1 - eio((t - END['t_fade0']) / (END['t_fade1'] - END['t_fade0']))
    u = np.clip((t - tp - PDEL) / 2.9, 0, 1)
    e = u * u * (3 - 2 * u)
    P = PSRC + (PDST - PSRC) * e[:, None] + PSW * np.sin(np.pi * e)[:, None] * (1 - e[:, None])
    gold_c = np.array([1.0, 0.82, 0.5], np.float32)
    colmix = (1 - e)[:, None] * gold_c + e[:, None] * PCOL
    pa = (0.75 - 0.75 * eio((t - tl_ - 0.4) / 1.2)) * fade
    if pa > 0.003:
        buf = np.zeros((H, W, 3), np.float32)
        xi = np.clip(P[:, 0].astype(int), 0, W - 1); yi = np.clip(P[:, 1].astype(int), 0, H - 1)
        np.add.at(buf, (yi, xi), colmix * pa)
        y0_, y1_ = 300, 1250
        sub = buf[y0_:y1_]
        sub = cv2.GaussianBlur(sub, (0, 0), 1.1) * 2.2 + cv2.GaussianBlur(sub, (0, 0), 6) * 6
        img[y0_:y1_] += sub
    gk = eo((t - tl_) / 1.2) * fade
    glow(img, (W / 2, LOGO_CY), 120, BLUE * 0.35, gk * 0.6)
    if t >= tb: glow(img, (W / 2, LOGO_CY), 160, GOLD * 0.3, math.exp(-(t - tb) / 0.5) * fade)
    la = eo((t - tl_) / 1.0) * fade
    if la > 0:
        over(img, LOGO_RGB.astype(np.float32), LOGO_A.astype(np.float32) * la, int(W / 2 - LOGO_PX / 2), int(LOGO_CY - LOGO_PX / 2))
    if t >= tb - 0.05:
        w1 = eo((t - tb + 0.05) / 0.9)
        rgb, al = END_TITLE
        sh = cl((t - END['t_shine']) / 1.4) if END['t_shine'] < t < END['t_shine'] + 1.4 else None
        rgb2 = rgb
        if sh is not None:
            hh, ww = al.shape
            xs = np.arange(ww)[None, :] + np.arange(hh)[:, None] * 0.6
            pos = -60 + (0.5 - 0.5 * math.cos(sh * math.pi)) * (ww + 120)
            rgb2 = np.clip(rgb + np.exp(-((xs - pos) / (0.06 * ww + 10)) ** 2)[..., None] * 0.6, 0, 1.25)
        soft = 0.3 * al.shape[1] + 30
        g = np.clip((w1 * (al.shape[1] + soft) - np.arange(al.shape[1])) / soft, 0, 1).astype(np.float32)
        ty = 1010
        over(img, rgb2, al * g[None, :] * fade, int(W / 2 - al.shape[1] / 2), int(ty - al.shape[0] / 2))
        hw = al.shape[1] / 2 + 40
        L = 150 * eo((t - tb - 0.3) / 1.0)
        for sg in (-1, 1):
            line(img, (W / 2 + sg * hw, ty), (W / 2 + sg * (hw + L), ty), SUB_GOLD * 0.8, fade * 0.8, 1)
        w2 = eo((t - tb - 0.35) / 0.9)
        rgb, al = END_SUB
        g = np.clip((w2 * (al.shape[1] + soft) - np.arange(al.shape[1])) / soft, 0, 1).astype(np.float32)
        over(img, rgb, al * g[None, :] * fade, int(W / 2 - al.shape[1] / 2), int(ty + 70 + 26 - al.shape[0] / 2))
        kf = eo((t - END['t_follow']) / 0.9)
        if kf > 0:
            text(img, '关注「巴芒价值」，传承大师智慧，领悟投资真谛', W / 2, 1225 + 10 * (1 - kf), 36, 'sans_med', a=fade * kf,
                 gold=True, track=0.04, glow=0.2)
            ln = 300 * eo((t - END['t_follow'] - 0.3) / 0.9)
            line(img, (W / 2 - ln, 1285), (W / 2 + ln, 1285), SUB_GOLD * 0.7, fade * kf * 0.6, 1)


# ================================================================ 合成一帧
SCENES = [(dia_cold, txt_cold), (dia_title, txt_title), (dia_s1, txt_s1), (dia_s2, txt_s2), (None, txt_s3), (dia_ctx, txt_ctx),
          (dia_qa, txt_qa), (dia_i1, txt_i1), (dia_i2, txt_i2), (dia_i3, txt_i3), (dia_wapo, txt_wapo), (dia_dex, txt_dex),
          (dia_lev, txt_lev), (dia_today, txt_today), (dia_close, txt_close), (dia_sum, txt_sum)]


def frame(t, subs=True):
    L = np.zeros((H, W, 3), np.float32)
    for d, _ in SCENES:
        if d is not None: d(L, t)
    L *= 1.0 + 0.45 * fx.hit_env(t, HITS)                     # 重拍上节点整体亮一下
    img = finish(L, t)
    for _, tx in SCENES:
        tx(img, t, subs)
    if subs:
        narr_sub(img, t, INTRO['subs'])
        narr_sub(img, t, INS['subs'], hide=('I13',))
    ruler(img, t)
    s_end(img, t)
    fade_all = 1 - eio((t - END['t_fade0']) / (END['t_fade1'] - END['t_fade0']))
    HUD.draw(img, t, alpha=float(fade_all * env(t, 0.0, 1e9, 0.8, 0.01)))
    if t < 0.4: img *= t / 0.4
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    cmd = sys.argv[1]
    if cmd == 'nframes':
        print(TL['nframes']); return
    if cmd == 'stills':
        out = sys.argv[2]; os.makedirs(out, exist_ok=True)
        for ts in sys.argv[3:-1]:
            tt = float(ts)
            Image.fromarray(frame(tt)).save(os.path.join(out, f'f_{tt:07.2f}.png'))
            print('still', tt, flush=True)
        return
    if cmd == 'chunk':
        a, b, path = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                              '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16',
                              '-pix_fmt', 'yuv420p', '-tune', 'film', path], stdin=subprocess.PIPE)
        for i in range(a, b):
            p.stdin.write(frame(i / FPS).tobytes())
            if (i - a) % 150 == 0: print(f'[{a}-{b}] {i - a}/{b - a}', flush=True)
        p.stdin.close(); p.wait()


if __name__ == '__main__':
    main()
