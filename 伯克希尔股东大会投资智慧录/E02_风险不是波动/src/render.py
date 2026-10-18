"""《伯克希尔股东大会投资智慧录》第二集 · 风险不是波动 —— 逐帧渲染（1080×1920，30fps）。

画面风格：以“暗夜星图编年”为底（近乎纯黑的宇宙、发光的点与细线、底部贯穿全片的时间刻度尺），
叠加与第一集一致的系列语言：片头用 1994 年大会原始录像 + 金色系列片名，“投资启示”标题转场、砸入 / 爆开 / HUD 圆环 / 光柱火花 / 故障，
以及泛光、横向光晕、重拍推镜 + 闪光 + 色散的电影后期。解读段是 3D 粒子镜头：透视相机环绕与推进、景深、运动拖尾、冲击波、爆炸碎屑、星图穿梭。
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
BARS = BEATS[::4]
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
    """只让点线溢光（阈值泛光），柔和压缩高光，叠加到背景上（暗角与颗粒在整帧后期里统一加）"""
    hi = np.maximum(L - 0.55, 0)
    s = cv2.resize(hi, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    bl = cv2.GaussianBlur(s, (0, 0), 2.5) * 0.6 + cv2.GaussianBlur(s, (0, 0), 8) * 0.4
    x = L + cv2.resize(bl, (W, H), interpolation=cv2.INTER_LINEAR) * 0.9
    x = 1 - np.exp(-x * 1.25)
    img = BGI + x
    stardust(img, t)
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


# ================================================================ 3D 粒子引擎：透视相机、景深分层、运动拖尾
class Cam:
    """世界坐标 y 向上；相机先绕 y 轴偏航、再绕 x 轴俯仰，看向 -z"""
    def __init__(self, pos, yaw=0.0, pitch=0.0, f=1100.0, cx=W / 2, cy=H / 2):
        self.p = np.asarray(pos, np.float64); self.f, self.cx, self.cy = f, cx, cy
        cy_, sy = math.cos(-yaw), math.sin(-yaw); cp, sp = math.cos(-pitch), math.sin(-pitch)
        Ry = np.array([[cy_, 0, sy], [0, 1, 0], [-sy, 0, cy_]]); Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
        self.R = Rx @ Ry

    def proj(self, P):
        v = (np.asarray(P, np.float64) - self.p) @ self.R.T
        d = -v[:, 2]
        ds = np.maximum(d, 1e-3)
        return np.c_[self.cx + self.f * v[:, 0] / ds, self.cy - self.f * v[:, 1] / ds], d


def pts3d(L, cam, P, col, k=1.0, w=None, ref=6.0, focus=None, dof=0.0, prev=None, trail=0.6, prev_cam=None):
    """3D 点云：越近越亮越大；离焦点越远越虚（景深）；prev 为上一时刻的位置时画运动拖尾"""
    if k <= 0.003 or len(P) == 0: return
    xy, d = cam.proj(P)
    ok = d > 0.25
    if not ok.any(): return
    wt_ = np.clip(ref / np.maximum(d, 0.25), 0.25, 3.0)
    if w is not None: wt_ = wt_ * np.asarray(w)
    c = np.asarray(col, np.float32)
    if focus is not None and dof > 0:
        coc = np.abs(d - focus) * dof
        for lo, hi, sig in ((0, 1.2, 1.0), (1.2, 3.0, 2.6), (3.0, 1e9, 5.5)):
            m = ok & (coc >= lo) & (coc < hi)
            if m.any(): cloud(L, xy[m], c if c.ndim == 1 else c[m], k * (1.0 if sig < 2 else 0.8), w=wt_[m], sig=sig)
    else:
        near = ok & (d < ref * 0.55)
        far = ok & ~near
        if far.any(): cloud(L, xy[far], c if c.ndim == 1 else c[far], k, w=wt_[far], sig=1.0)
        if near.any(): cloud(L, xy[near], c if c.ndim == 1 else c[near], k, w=wt_[near], sig=2.0)
    if prev is not None or prev_cam is not None:
        xy0, d0 = (prev_cam or cam).proj(prev if prev is not None else P)
        m = ok & (d0 > 0.25)
        seg = []; ww = []
        for u in (0.15, 0.3, 0.45, 0.6, 0.75, 0.9):
            seg.append(xy[m] + (xy0[m] - xy[m]) * u); ww.append(wt_[m] * (1 - u) * trail)
        if seg:
            cc = c if c.ndim == 1 else np.concatenate([c[m]] * len(seg))
            cloud(L, np.concatenate(seg), cc, k * 0.7, w=np.concatenate(ww), sig=1.0)


def shock(L, c, t, t0, col, k=1.0, rmax=520, life=1.1, flatten=1.0):
    """冲击波：一圈细光环快速扩张、变淡"""
    dt = t - t0
    if dt < 0 or dt > life or k <= 0.003: return
    u = dt / life
    r = rmax * (1 - (1 - u) ** 2.4)
    n = max(48, int(r * 0.6))
    a = np.linspace(0, 2 * math.pi, n + 1)
    pts = np.c_[c[0] + r * np.cos(a), c[1] + r * np.sin(a) * flatten]
    hair(L, pts, col, k * 1.6 * (1 - u) ** 1.5, th=2)
    hair(L, pts * 1.0 + 0, col, k * 0.5 * (1 - u), th=6)


def beam(L, x, y0, y1, col, k=1.0, wd=10.0):
    """竖直光柱：底部最亮，向上衰减"""
    if k <= 0.003: return
    x0_, x1_ = int(max(x - wd * 4, 0)), int(min(x + wd * 4, W))
    ya, yb = int(max(min(y0, y1), 0)), int(min(max(y0, y1), H))
    if x1_ <= x0_ or yb <= ya: return
    xs = np.arange(x0_, x1_) - x; ys = np.arange(ya, yb)
    gx = np.exp(-(xs / wd) ** 2) + 0.25 * np.exp(-(xs / (wd * 3)) ** 2)
    gy = ((ys - min(y0, y1)) / max(abs(y1 - y0), 1)) if y1 < y0 else 1 - (ys - y0) / max(abs(y1 - y0), 1)
    gy = np.clip(gy, 0, 1) ** 1.5
    L[ya:yb, x0_:x1_] += (gy[:, None] * gx[None, :])[..., None] * np.asarray(col, np.float32) * k


def brackets(img, box, a, col=None, L_=28, th=2):
    """瞄准框：四角的折线"""
    if a <= 0.003: return
    x0, y0, x1, y1 = box
    c = GOLD_C if col is None else col
    for (x, y), (dx, dy) in (((x0, y0), (1, 1)), ((x1, y0), (-1, 1)), ((x0, y1), (1, -1)), ((x1, y1), (-1, -1))):
        line(img, (x, y), (x + L_ * dx, y), c, a, th); line(img, (x, y), (x, y + L_ * dy), c, a, th)


def scanline(img, box, t, t0, a, col=None, dur=1.2):
    """扫描线：一道细亮线从上到下扫过区域"""
    k = (t - t0) / dur
    if not 0 < k < 1 or a <= 0.003: return
    x0, y0, x1, y1 = box
    y = y0 + (y1 - y0) * eio(k)
    c = ICE if col is None else col
    line(img, (x0, y), (x1, y), c, a * math.sin(math.pi * k), 1)
    glow(img, (x0 + (x1 - x0) * 0.5, y), 60, c * 0.4, a * 0.25 * math.sin(math.pi * k))


def year_rewind(img, t, t0, x, y, a, y_from=2026, y_to=1994, dur=1.4, size=200):
    """年份倒带：数字飞速回卷，带运动残影；落定时爆开"""
    if a <= 0.003 or t < t0 - 0.05: return
    p = eio((t - t0) / dur)
    yr = int(round(y_from - (y_from - y_to) * p))
    for g in range(3 if p < 1 else 1):
        text(img, str(yr + g * (1 if p < 1 else 0)), x, y - g * 26, size, 'corm_med', a=a * (1 - 0.35 * g) * (0.6 if g else 1),
             gold=True, glow=0.3 if yr == y_to else 0.15, shadow=0.3)
    fx.burst(img, t, t0 + dur, (x, y), a * 0.7, n=40, speed=420, life=1.1, seed=11)


def gold_title(img, s, x, y, size, a, wipe=None, shine=None, glow_=0.18, track=0.06):
    text(img, s, x, y, size, 'serif_black', a=a, gold=True, wipe=wipe, shine=shine, track=track, glow=glow_)


# ================================================================ 片头：冷开场（原声 + 原始录像）
WIN_W, WIN_H = 1000, 405


def foot(img, clip, t_src, cx, cy, a, zoom=1.04, blur=0.5, pan=(0.0, 0.0), gain=0.9, sat=0.5):
    """1994 年大会的原始录像（E01 同款：宽银幕窗口 + 同画面模糊补满）"""
    if a <= 0.003: return
    window(img, grade(clip.get(t_src), sat=sat, gain=gain), cx, cy, WIN_W, WIN_H, zoom=zoom, pan=pan, a=a, blur_bg=blur)


_rc = np.random.default_rng(11)
HAY = np.c_[_rc.uniform(-1, 1, 420), _rc.uniform(-1, 1, 420), _rc.uniform(-1, 1, 420)]
HAY_F = _rc.uniform(3, 11, (420, 3)); HAY_PH = _rc.uniform(0, 6.3, (420, 3))


def dia_cold(L, t):
    a = env(t, 0.25, B_TITLE + 0.1, 1.6, 0.55)
    if a <= 0: return
    # 录像四周：一层随原声能量乱跳的冰青粒子——“风险的衡量乱了套”
    e = float(np.mean(ofr(t))) if len(ofr(t)) else 0.2
    j = np.sin(t * HAY_F + HAY_PH) * (0.05 + 0.25 * min(e * 2.5, 1.0))
    P = HAY * [3.2, 2.6, 1.5] + j
    P[:, 1] = np.where(np.abs(P[:, 1]) < 0.75, np.sign(P[:, 1] + 1e-6) * (0.75 + np.abs(P[:, 1]) * 0.6), P[:, 1])
    cam = Cam((0.25 * math.sin(t * 0.2), 0.0, 4.5 - 0.25 * t), yaw=0.04 * math.sin(t * 0.3), cy=760)
    Pp = HAY * [3.2, 2.6, 1.5] + np.sin((t - 0.05) * HAY_F + HAY_PH) * (0.05 + 0.25 * min(e * 2.5, 1.0))
    Pp[:, 1] = np.where(np.abs(Pp[:, 1]) < 0.75, np.sign(Pp[:, 1] + 1e-6) * (0.75 + np.abs(Pp[:, 1]) * 0.6), Pp[:, 1])
    pts3d(L, cam, P, ICE, 0.55 * a, ref=4.5, prev=Pp, trail=1.0)


def txt_cold(img, t, subs):
    a = env(t, 0.25, B_TITLE + 0.1, 1.6, 0.55)
    if a <= 0: return
    src = COLD['src_in'] + (t - COLD['t0'])
    z = 1.0 + 0.06 * eio(t / 7.0)
    foot(img, QA_CLIP, min(max(src, 0.0), 309.0), W / 2, 760, a, zoom=z, pan=(0.03, -0.02), blur=0.55)
    brackets(img, (W / 2 - WIN_W / 2 + 20, 760 - WIN_H / 2 + 20, W / 2 + WIN_W / 2 - 20, 760 + WIN_H / 2 - 20), a * 0.55, col=GOLD_H, L_=34)
    scanline(img, (40, 760 - WIN_H / 2, W - 40, 760 + WIN_H / 2), t, 0.6, a * 0.8)
    text(img, '1994 · 伯克希尔股东大会 · 巴菲特原声', W / 2, 470, 28, 'sans_med', SUB_GOLD, a * 0.9, track=0.12, shadow=0.4)
    line(img, (W / 2 - 300, 510), (W / 2 + 300, 510), SUB_GOLD, a * 0.35, 1)
    if subs:
        for s in TL['cold_subs']:
            sa = env(t, s['t0'] - 0.1, s['t1'] + 0.1, 0.15, 0.2) * a
            if sa > 0: orig_sub(img, s, sa, bottom=1300)


# ================================================================ 片名（与第一集同款：系列片名 + 本集集名）
def title_a(t): return env(t, T_TITLE - 0.05, V('S1')['t0'] + 0.55, 0.05, 0.6)


def dia_title(L, t):
    a = title_a(t)
    if a <= 0: return
    k = max(0.0, t - T_TITLE)
    shock(L, (W / 2, 900), t, T_TITLE, GOLD_H, a * 0.8, rmax=620, life=1.4, flatten=0.35)
    # 金色微粒从景深里飘过
    cam = Cam((0, 0, 3.0 - 0.4 * k), cy=900)
    rng = np.random.default_rng(3)
    P = np.c_[rng.uniform(-3, 3, 300), rng.uniform(-4, 4, 300), rng.uniform(-6, 2.4, 300)]
    pts3d(L, cam, P, GOLD_H, 0.2 * a, ref=3.0)


def txt_title(img, t, subs):
    a = title_a(t)
    if a <= 0: return
    k = t - T_TITLE
    glow(img, (W / 2, 880), 260, GOLD * 0.25, math.exp(-max(k, 0) / 1.3) * a * 0.9)
    text(img, '巴菲特与芒格', W / 2, 700, 42, 'serif_bold', SUB_GOLD, a * eo((k - 0.1) / 0.6), track=0.32, shadow=0.4)
    for sg in (-1, 1):
        L_ = 110 * eo((k - 0.2) / 0.8)
        line(img, (W / 2 + sg * 190, 700), (W / 2 + sg * (190 + L_), 700), SUB_GOLD, a * 0.6, 1)
    sh = cl((k - 1.2) / 1.2) if 1.2 < k < 2.4 else None
    gold_title(img, '伯克希尔股东大会', W / 2, 830, 96, a, wipe=eo(k / 0.7), shine=sh, track=0.04)
    gold_title(img, '投资智慧录', W / 2, 980, 132, a, wipe=eo((k - 0.15) / 0.7), shine=sh, track=0.08)
    text(img, 'BERKSHIRE HATHAWAY · ANNUAL MEETING WISDOM', W / 2, 1100, 26, 'corm', SUB_GOLD * 0.9, a * eo((k - 0.5) / 0.8), track=0.2, shadow=0.3)
    ea = a * eo((k - 0.9) / 0.6)
    if ea > 0:
        rrect(img, W / 2 - 210, 1196, W / 2 + 210, 1268, 6, SUB_GOLD, ea * 0.55, 1)
        text(img, '第二集 · 风险不是波动', W / 2, 1232, 38, 'sans_med', INK, ea, track=0.14)
    fx.burst(img, t, T_TITLE, (W / 2, 900), a * 0.8, n=70, speed=640, life=1.4, seed=2)


# ================================================================ 开场口播：上方是 1994 年大会影像，下方是 3D 动态图解
FOOT_Y = 540
PRICE = [100, 103, 99, 104, 108, 102, 105, 96, 90, 84, 78, 75]
P3 = np.c_[np.linspace(-3.0, 3.0, 12), (np.array(PRICE) - 92) / 9.0, np.zeros(12)]


def intro_a(t):
    return env(t, V('S1')['t0'] - 0.3, T_CTX - 0.3, 0.5, 0.6)


def dia_s1(L, t):
    a = env(t, V('S1')['t0'] - 0.3, V('S2')['t0'] - 0.1, 0.4, 0.4)
    if a <= 0: return
    td = wt('S1', '跌掉')
    u = t - V('S1')['t0']
    cam = Cam((-1.2 + 0.35 * u, 0.6, 7.2 - 0.18 * u), yaw=-0.18 + 0.05 * u, pitch=-0.05, cy=1080, f=900)
    head = 1 + 11 * eio((t - V('S1')['t0'] + 0.2) / (td + 0.8 - V('S1')['t0']))
    n = int(head)
    # 地面参考网格（透视）
    for gx in np.linspace(-3.5, 3.5, 15):
        xy, _ = cam.proj(np.c_[np.full(2, gx), np.full(2, -2.6), [-3, 3]])
        hair(L, xy, FOG, 0.10 * a)
    for gz in np.linspace(-3, 3, 7):
        xy, _ = cam.proj(np.c_[[-3.5, 3.5], np.full(2, -2.6), np.full(2, gz)])
        hair(L, xy, FOG, 0.10 * a)
    xy, d = cam.proj(P3)
    for i in range(n):
        col = ICE if i < 7 else AMBER
        node(L, xy[i], col, a * (1.0 if i < 7 else 1.2), 0.9)
        if i: hair(L, [xy[i - 1], xy[i]], col, 0.45 * a, th=2)
        # 每个节点落到地面的细投影线
        g, _ = cam.proj(np.c_[P3[i, 0], -2.6, 0.0][None, :] if False else np.array([[P3[i, 0], -2.6, 0.0]]))
        hair(L, [xy[i], g[0]], FOG, 0.12 * a)
    if n < 12:
        f = head - n
        q = xy[n - 1] + (xy[n] - xy[n - 1]) * f
        hair(L, [xy[n - 1], q], ICE if n < 7 else AMBER, 0.45 * a, th=2)
        node(L, q, GOLD_C, a, 1.1)
    kd = ke(t, td + 0.6)
    if kd > 0:
        shock(L, tuple(xy[-1]), t, td + 0.6, AMBER, a, rmax=260, life=0.9)
        ring(L, xy[-1], 24, AMBER, 0.6 * a * kd, th=2)
        # 下跌段向下洒落的火花
        rng = np.random.default_rng(4)
        ph = (t * 0.8 + rng.random(60)) % 1.0
        sp = np.c_[xy[7, 0] + (xy[-1, 0] - xy[7, 0]) * rng.random(60), np.zeros(60)]
        sp[:, 1] = np.interp(sp[:, 0], xy[7:, 0], xy[7:, 1]) + ph * 220
        cloud(L, sp, AMBER, 0.5 * a * kd, w=(1 - ph))


def txt_s1(img, t, subs):
    a = intro_a(t)
    ap = env(t, V('S1')['t0'] - 0.3, V('S2')['t0'] - 0.1, 0.4, 0.4)
    if a > 0:
        ct = (t - V('S1')['t0'] + 2.0) % 15.5
        foot(img, CLIPS[1500] if t < V('S2')['t0'] - 0.1 else (CLIPS[6000] if t < V('S3')['t0'] - 0.2 else CLIPS[200]),
             ct, W / 2, FOOT_Y, a * (1 - 0.0), zoom=1.05 + 0.006 * ct, blur=0.5)
        text(img, '1994 · 奥马哈 · 伯克希尔股东大会上午场实况', 72, FOOT_Y - WIN_H / 2 - 30, 22, 'sans', INK2, a * 0.85, 'l', track=0.06, shadow=0.5)
    if ap > 0:
        td = wt('S1', '百分之')
        fx.slam(img, '−25%', 760, 1420, 130, 'corm_med', t, td - 0.05, ap, gold=False, col=AMBER, glow_=0.35)
        text(img, '一年', 560, 1420, 34, 'sans_med', INK2, ap * ke(t, td), track=0.3)
        for i, (s, kw, x, col) in enumerate((('更危险？', '更危险', 290, ICE), ('更便宜？', '更便宜', 790, None))):
            tk = wt('S1', kw)
            fx.slam(img, s, x, 880, 64, 'serif_black', t, tk - 0.05, ap, gold=col is None, col=col, glow_=0.3)
            if t > tk - 0.05: brackets(img, (x - 150, 830, x + 150, 930), ap * ke(t, tk, 0.4), col=col if col is not None else GOLD_C, L_=18)


# ---------------------------------------------------------------- S2：倾斜网格平面上的 3D 点云，分界线转到斜率 β
_rb = np.random.default_rng(4)
BX = np.clip(_rb.normal(0, 0.42, 220), -0.98, 0.98)
BY = np.clip(1.6 * BX + _rb.normal(0, 0.28, 220), -0.98, 0.98)


def beta3d(L, t, a, cam, s0=None, R=2.6, n_pts=None):
    g = np.linspace(-1, 1, 11) * R
    for v in g:
        xy, _ = cam.proj(np.c_[np.linspace(-R, R, 16), np.zeros(16), np.full(16, v)]); hair(L, xy, FOG, 0.32 * a)
        xy, _ = cam.proj(np.c_[np.full(16, v), np.zeros(16), np.linspace(-R, R, 16)]); hair(L, xy, FOG, 0.32 * a)
    m = len(BX) if n_pts is None else n_pts
    P = np.c_[BX[:m] * R, np.zeros(m) + 0.02, -BY[:m] * R]
    pts3d(L, cam, P, ICE, 1.4 * a, ref=6.0)
    k = 0.0 if s0 is None else eio((t - s0) / 1.6)
    s = 1.6 * k
    u = np.linspace(-1, 1, 40); v = u * s; ok = np.abs(v) <= 1
    if ok.sum() > 1:
        xy, _ = cam.proj(np.c_[u[ok] * R, np.full(ok.sum(), 0.03), -v[ok] * R])
        hair(L, xy, GOLD_C, 1.1 * a, th=3); hair(L, xy, GOLD_H, 0.35 * a, th=9)


def dia_s2(L, t):
    a = env(t, V('S2')['t0'] - 0.1, V('S3')['t0'] - 0.2, 0.35, 0.35)
    if a <= 0: return
    u = t - V('S2')['t0']
    cam = Cam((5.5 * math.sin(-0.5 + 0.12 * u), 4.2, 5.5 * math.cos(-0.5 + 0.12 * u)), yaw=-(-0.5 + 0.12 * u), pitch=-0.62, cy=1110, f=820)
    beta3d(L, t, a, cam, s0=V('S2')['t0'] + 0.2)


def txt_s2(img, t, subs):
    a = env(t, V('S2')['t0'] - 0.1, V('S3')['t0'] - 0.2, 0.35, 0.35)
    if a <= 0: return
    text(img, '教科书 · 贝塔理论', W / 2, 840, 30, 'sans_med', INK2, a * ke(t, V('S2')['t0']), track=0.3)
    fx.slam(img, 'β ↑  ＝  风险 ↑', W / 2, 920, 70, 'inter_semi', t, wt('S2', '贝塔') - 0.05, a, gold=True, glow_=0.25)
    te = wt('S2', '更危险')
    fx.slam(img, '更危险', W / 2, 1420, 104, 'serif_black', t, te - 0.05, a, gold=False, col=AMBER, glow_=0.4)


# ---------------------------------------------------------------- S3：年份倒带回 1994 + 股东的追问
def dia_s3(L, t):
    a = env(t, V('S3')['t0'] - 0.2, T_CTX - 0.3, 0.4, 0.6)
    if a <= 0: return
    tq = wt('S3', '你们')
    shock(L, (W / 2, 1300), t, tq, GOLD_H, a, rmax=560, life=1.2, flatten=0.3)


def txt_s3(img, t, subs):
    a = env(t, V('S3')['t0'] - 0.2, T_CTX - 0.3, 0.4, 0.6)
    if a <= 0: return
    year_rewind(img, t, wt('S3', '一九九四') - 0.3, W / 2, 1000, a, size=170)
    tq = wt('S3', '你们')
    fx.slam(img, '“你们说的风险，', W / 2, 1250, 72, 'serif_black', t, tq - 0.05, a, glow_=0.35)
    fx.slam(img, '到底是什么？”', W / 2, 1350, 72, 'serif_black', t, wt('S3', '到底') - 0.05, a, glow_=0.35)


# ---------------------------------------------------------------- 回到 1994：背景卡（与第一集同款）
def txt_ctx(img, t, subs):
    a = env(t, T_CTX, T_Q + 0.3, 0.6, 0.7)
    if a <= 0: return
    k = t - T_CTX
    text(img, '1994', W / 2, 760, 330, 'corm_med', GOLD * 0.55, a * 0.22, track=0.02, shadow=0)
    text(img, '1994 年 4 月 25 日 · 美国奥马哈', W / 2, 640, 34, 'sans_med', SUB_GOLD, a * eo(k / 0.6), track=0.12)
    gold_title(img, '伯克希尔·哈撒韦年度股东大会', W / 2, 750, 58, a * eo((k - 0.2) / 0.7), track=0.04, glow_=0.12)
    text(img, '上午场 · 股东问答', W / 2, 840, 44, 'serif_med', INK2, a * eo((k - 0.4) / 0.7), track=0.2)
    line(img, (W / 2 - 160, 905), (W / 2 + 160, 905), SUB_GOLD, a * 0.5 * eo((k - 0.5) / 0.6), 1)
    text(img, 'CNBC 巴菲特档案 · 第 50 章', W / 2, 965, 28, 'sans', INK2, a * eo((k - 0.7) / 0.7), track=0.06)
    text(img, 'Risk is “inextricably wound up” in how long an asset is held', W / 2, 1025, 30, 'ebg_i', INK, a * eo((k - 0.8) / 0.7))
    text(img, '以下为原始录像节选，画面与声音均为 1994 年现场原始记录', W / 2, 1120, 26, 'sans', INK2, a * eo((k - 1.2) / 0.8), track=0.02)


def dia_ctx(L, t):
    a = env(t, T_CTX, T_Q + 0.3, 0.6, 0.7)
    if a <= 0: return
    shock(L, (W / 2, 760), t, T_CTX, GOLD_H, a * 0.7, rmax=700, life=1.6, flatten=0.5)


# ---------------------------------------------------------------- 原始录像“展柜”：很淡的细边框
def frame_box(img, cx, cy, w, h, a):
    x0, y0, x1, y1 = cx - w / 2 - 12, cy - h / 2 - 12, cx + w / 2 + 12, cy + h / 2 + 12
    for p, q in (((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))):
        line(img, p, q, RULE * 1.6, a, 1)
    for (x, y), (dx, dy) in (((x0, y0), (1, 1)), ((x1, y0), (-1, 1)), ((x0, y1), (1, -1)), ((x1, y1), (-1, -1))):
        line(img, (x, y), (x + 22 * dx, y), DESC, a * 0.8, 1); line(img, (x, y), (x, y + 22 * dy), DESC, a * 0.8, 1)


def archival(img, fr, cx, cy, w, h, a, zoom=1.0, pan=(0.0, 0.0)):
    if a <= 0.003: return
    window(img, grade(fr, sat=0.45, gain=0.9, lift=0.0), cx, cy, w, h, zoom=zoom, pan=pan, a=a, feather=18)
    frame_box(img, cx, cy, w, h, a)


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
        u = t - QSC['beta']['t0']
        cam = Cam((5.5 * math.sin(-0.4 + 0.02 * u), 4.2, 5.5 * math.cos(-0.4 + 0.02 * u)), yaw=-(-0.4 + 0.02 * u), pitch=-0.62, cy=1000, f=560)
        beta3d(L, t, s, cam, s0=qs('A14'))
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


# ================================================================ 投资启示（本片解读）：与第一集同款的标题转场 + 3D 粒子镜头
NOTE = '本片解读，非巴菲特或芒格原话'
T_INS_END = I['I13']['t1'] + 0.3


def sc(t, b_in, b_out):
    """启示段内的换镜：0.5 秒暗下 → 0.15 秒黑 → 0.45 秒亮起（不硬切）"""
    u = eio((t - (b_in + 0.15)) / 0.45)
    return u * (1 - eio((t - (b_out - 0.5)) / 0.5))


def ins_bg(img, t):
    """整段启示的背景（与第一集一致）：透视网格 + 3D 金色微粒 + 漏光"""
    a = env(t, T_INS - 0.3, T_INS_END, 0.8, 0.8)
    if a <= 0: return
    fx.grid_floor(img, t, a)
    fx.starfield(img, t, a * 0.9)
    fx.light_leak(img, t, a)


def txt_card(img, t, subs):
    """标题卡：与第一集完全一致"""
    a = env(t, T_INS - 0.05, I['I1']['t0'] - 0.25, 0.05, 0.5)
    if a <= 0: return
    k = t - T_INS
    fx.hud_ring(img, t, (W / 2, 880), 300 + 30 * eo(k / 0.8), a * eo(k / 0.6))
    fx.burst(img, t, T_INS, (W / 2, 880), a, n=70, speed=640, life=1.4, seed=2)
    text(img, 'INSIGHT', W / 2, 760, 32, 'corm_med', SUB_GOLD, a * eo(k / 0.6), track=0.5)
    fx.slam(img, '投资启示', W / 2, 880, 124, 'serif_black', t, T_INS, a, glow_=0.5)
    text(img, '以下为本片解读，非巴菲特或芒格原话', W / 2, 1010, 28, 'sans', INK2, a * eo((k - 0.6) / 0.8), track=0.04)


def ins_tag(img, t):
    ta = env(t, I['I1']['t0'] - 0.4, T_INS_END, 0.6, 0.6)
    chapters = [(I['I1']['t0'] - 0.4, 'III · Insight'), (B_WAPO, 'IV · The Washington Post'), (B_DEX, 'V · Dexter Shoe'),
                (B_LEV, 'VI · Leverage'), (B_TODAY, 'VII · Today'), (B_CLOSE, 'VIII · In one sentence')]
    for i, (c0, s) in enumerate(chapters):
        c1 = chapters[i + 1][0] if i + 1 < len(chapters) else T_INS_END
        seg_label(img, s, ta * env(t, c0, c1, 0.4, 0.4), NOTE)


def ycap(img, s, a, y=1340, col=None):
    text(img, s, W / 2, y, 28, 'sans_med', INK2 if col is None else col, a, track=0.1, shadow=0.6)


# ---------------------------------------------------------------- I1：两种风险——剧烈乱跳的冰青粒子群 vs 稳定发光、粒子环绕的金色内核
_ri = np.random.default_rng(21)
SW = _ri.normal(0, 1, (300, 3)) * [0.75, 0.6, 0.6]
SW_F = _ri.uniform(4, 13, (300, 3)); SW_PH = _ri.uniform(0, 6.3, (300, 3))
RING = np.c_[np.cos(np.linspace(0, 2 * math.pi, 180, endpoint=False)), np.zeros(180), np.sin(np.linspace(0, 2 * math.pi, 180, endpoint=False))]
B_I1 = I['I1']['t0'] - 0.45


def i1_cam(t):
    u = t - B_I1
    return Cam((0.6 * math.sin(u * 0.1), 0.2, 7.0 - 0.06 * u), yaw=0.08 * math.sin(u * 0.1), cy=820, f=950)


def i1_pos(t):
    return SW + np.sin(t * SW_F + SW_PH) * 0.32 + [-1.5, 1.4, 0]


def dia_i1(L, t):
    a = sc(t, B_I1 if t > I['I1']['t0'] - 1 else 0, B_I2)
    a *= env(t, I['I1']['t0'] - 0.3, 1e9, 0.4, 0.1)
    if a <= 0: return
    cam = i1_cam(t)
    kc = ke(t, wt('I1', '教科书') - 0.3, 0.8); kg = ke(t, wt('I1', '受到伤害') - 0.3, 0.8)
    pts3d(L, cam, i1_pos(t), ICE, 0.75 * a * (0.25 + 0.75 * kc), ref=7.0, prev=i1_pos(t - 0.06), trail=1.0)
    c = np.array([1.4, -1.3, 0.0])
    ang = t * 0.6
    R3 = RING * 1.1
    rot = np.c_[R3[:, 0] * math.cos(ang) - R3[:, 2] * math.sin(ang), R3[:, 0] * math.sin(ang) * 0.35, R3[:, 0] * math.sin(ang) + R3[:, 2] * math.cos(ang)]
    pts3d(L, cam, rot + c, GOLD_H, 0.9 * a * kg, ref=7.0)
    xy, _ = cam.proj(c[None, :])
    node(L, xy[0], GOLD_C, a * kg * (1.6 + 0.2 * math.sin(t * 1.3)), 2.0)
    shock(L, tuple(xy[0]), t, wt('I1', '受到伤害') - 0.1, GOLD_H, a, rmax=380, life=1.0)


def txt_i1(img, t, subs):
    a = sc(t, B_I1 if t > I['I1']['t0'] - 1 else 0, B_I2) * env(t, I['I1']['t0'] - 0.3, 1e9, 0.4, 0.1)
    if a <= 0: return
    cam = i1_cam(t)
    xy, _ = cam.proj(np.array([[1.4, -1.3, 0.0]]))
    kg = ke(t, wt('I1', '受到伤害') - 0.3)
    fx.hud_ring(img, t, tuple(xy[0]), 150, a * kg * 0.8, spin=0.4)
    fx.slam(img, '价格的波动 · β', 330, 450, 50, 'serif_black', t, wt('I1', '教科书') - 0.05, a, gold=False, col=ICE, glow_=0.25)
    text(img, '教科书的风险', 330, 515, 26, 'sans_med', INK2, a * ke(t, wt('I1', '教科书')), track=0.2)
    fx.slam(img, '损失的可能性', 760, 1210, 60, 'serif_black', t, wt('I1', '受到伤害') - 0.05, a, glow_=0.35)
    text(img, '巴菲特的风险', 760, 1280, 26, 'sans_med', INK2, a * kg, track=0.2)
    readout(img, 'σ , β    vs    P( loss )', a * ke(t, wt('I1', '贝塔')))


# ---------------------------------------------------------------- I2：持有期——一颗彗星沿着起伏的路径奔向远方的终点，落在“当初的购买力”之上
_r2 = np.random.default_rng(8)
I2_N = 90
I2_Z = np.linspace(2.0, -16.0, I2_N)
I2_Y = np.cumsum(_r2.normal(0.004, 0.16, I2_N)); I2_Y -= I2_Y[0]; I2_Y = I2_Y * 0.9 + np.linspace(0, 0.9, I2_N) * 0.3
I2_Y[-1] = 0.55
I2_X = 1.3 * np.sin(np.linspace(0, 4.0, I2_N)) - np.linspace(0, 2.5, I2_N)
I2_P = np.c_[I2_X, I2_Y - 0.6, I2_Z]
I2_CAM = Cam((3.6, 3.4, 5.5), yaw=0.42, pitch=-0.30, cy=820, f=900)


def i2_head(t):
    return eio((t - wt('I2', '持有期') + 0.4) / (wt('I2', '购买力') - wt('I2', '持有期') + 0.4))


def dia_i2(L, t):
    a = sc(t, B_I2, B_I3)
    if a <= 0: return
    cam = I2_CAM
    # 当初的购买力：一条暗金色基准线伸向远方
    xy, _ = cam.proj(np.c_[np.zeros(2), np.full(2, -0.6), [2.0, -16.0]])
    hair(L, xy, GOLD_H, 0.28 * a, th=1)
    h = i2_head(t)
    n = max(2, int(I2_N * h))
    xy, d = cam.proj(I2_P[:n])
    hair(L, xy, ICE, 0.8 * a, th=2)
    hair(L, xy, ICE, 0.25 * a, th=7)
    cloud(L, xy[::2], ICE, 0.8 * a, sig=1.2)
    if n < I2_N:                                    # 彗星头 + 拖尾
        node(L, xy[-1], GOLD_C, a * 1.4, 1.4)
        tail = xy[max(0, n - 12):]
        cloud(L, tail, GOLD_H, 0.6 * a, w=np.linspace(0.1, 1.0, len(tail)), sig=2.0)
    kp = ke(t, wt('I2', '购买力') - 0.1)
    end, _ = cam.proj(I2_P[-1:])
    if kp > 0:
        node(L, end[0], GOLD_C, a * 1.6, 1.8)
        shock(L, tuple(end[0]), t, wt('I2', '购买力') - 0.1, GOLD_H, a, rmax=300, life=1.0)
        beam(L, end[0][0], end[0][1], end[0][1] - 520, GOLD_H, 0.55 * a * kp, wd=6)
    start, _ = cam.proj(I2_P[:1])
    node(L, start[0], GOLD_C, a * 0.9, 1.1)


def txt_i2(img, t, subs):
    a = sc(t, B_I2, B_I3)
    if a <= 0: return
    cam = I2_CAM
    start, _ = cam.proj(I2_P[:1]); end, _ = cam.proj(I2_P[-1:])
    text(img, '买入', start[0][0] + 70, start[0][1] + 10, 30, 'sans_med', INK, a * ke(t, wt('I2', '持有期') - 0.4), 'l', track=0.2)
    text(img, '持有期结束', end[0][0], end[0][1] - 70, 28, 'sans_med', INK, a * ke(t, wt('I2', '拿回') - 0.3), track=0.2)
    if t > wt('I2', '购买力') - 0.3: fx.burst(img, t, wt('I2', '购买力') - 0.1, tuple(end[0]), a, n=50, speed=420, life=1.2, seed=5)
    tp = wt('I2', '购买力')
    fx.slam(img, '拿回的钱  ≥  当初的购买力', W / 2, 1180, 56, 'serif_black', t, tp - 0.05, a, glow_=0.35)
    fx.typewriter(img, '“…at least as much purchasing power as he had to begin with…”', W / 2, 1265, 26, 'ebg_i', INK2, a, t, tp + 0.6, cps=40)
    text(img, '—— 巴菲特 1993 年致股东信', W / 2, 1315, 24, 'sans', INK2, a * ke(t, tp + 1.8), track=0.06)
    text(img, '1993 · 致股东信', W / 2, 400, 30, 'sans_med', SUB_GOLD, a * ke(t, I['I2']['t0']), track=0.3)


# ---------------------------------------------------------------- I3：一排节点上下乱跳（波动）；一颗金色内核升起光柱（钱还在不在）
def dia_i3(L, t):
    a = sc(t, B_I3, B_WAPO)
    if a <= 0: return
    for i in range(13):
        x = 150 + i * 65
        ph = t * 2.6 + i * 1.7
        y = 640 + 150 * math.sin(ph) * math.sin(t * 0.9 + i)
        yp = 640 + 150 * math.sin(ph - 0.16) * math.sin((t - 0.06) * 0.9 + i)
        cloud(L, np.c_[np.full(6, x), np.linspace(yp, y, 6)], ICE, 0.4 * a, w=np.linspace(0.2, 1, 6))
        node(L, (x, y), ICE, a, 0.9)
    hair(L, [(120, 640), (960, 640)], FOG, 0.25 * a)
    kg = ke(t, wt('I3', '风险') - 0.1)
    if kg > 0:
        node(L, (540, 1000), GOLD_C, a * kg * 1.6, 2.0)
        beam(L, 540, 1000, 300, GOLD_H, 0.5 * a * kg, wd=7)
        shock(L, (540, 1000), t, wt('I3', '风险') - 0.1, GOLD_H, a, rmax=420, life=1.1, flatten=0.4)


def txt_i3(img, t, subs):
    a = sc(t, B_I3, B_WAPO)
    if a <= 0: return
    fx.slam(img, '波动 ＝ 价格摆动的幅度', W / 2, 430, 50, 'serif_black', t, I['I3']['t0'] - 0.05, a, gold=False, col=ICE, glow_=0.2)
    kg = wt('I3', '风险')
    fx.slam(img, '风险 ＝ 钱还在不在', W / 2, 1200, 72, 'serif_black', t, kg - 0.05, a, glow_=0.4)
    if t > kg: fx.sparks_up(img, t, 470, 610, 1000, a * ke(t, kg), n=40, seed=8)


# ---------------------------------------------------------------- 华盛顿邮报：风暴里的价格 vs 越长越大的金色生意
SPH = fib_sphere(1400, 5)
WAPO_V = [1.06, 0.80, 0.9, 1.1, 1.3, 1.6, 2.0, 2.4, 3.0, 3.6, 4.4, 5.5, 7.0, 8.6, 10.5, 13.0, 16.5, 20.5, 26.0, 33.0, 44.0]
WP = np.c_[np.linspace(-2.6, 2.6, 21), -2.8 + np.log10(np.array(WAPO_V) / 0.8) * 0.75, np.full(21, 1.2)]


def wapo_cam(t):
    u = t - B_WAPO
    ang = -0.18 + 0.02 * u
    r = 8.6 - 0.05 * u
    return Cam((r * math.sin(ang), 0.9, r * math.cos(ang)), yaw=ang, pitch=-0.02, cy=680, f=1000)


def dia_wapo(L, t):
    a = sc(t, B_WAPO, B_DEX)
    if a <= 0: return
    cam = wapo_cam(t)
    t6 = I['I6']['t0']
    g = eio((t - t6) / 5.5)
    R = 0.9 + 1.3 * g
    spin = t * 0.25
    S = SPH * R
    rot = np.c_[S[:, 0] * math.cos(spin) - S[:, 2] * math.sin(spin), S[:, 1], S[:, 0] * math.sin(spin) + S[:, 2] * math.cos(spin)] + [0, 0.9, 0]
    pts3d(L, cam, rot, GOLD_H, (0.45 + 0.35 * g) * a, ref=8.0)
    xy, _ = cam.proj(np.array([[0, 0.9, 0]]))
    node(L, xy[0], GOLD_C, a * (0.8 + 1.2 * g), 2.2)
    shock(L, tuple(xy[0]), t, B_WAPO + 0.4, GOLD_H, a, rmax=640, life=1.3, flatten=0.45)
    shock(L, tuple(xy[0]), t, wt('I6', '超过') - 0.05, GOLD_H, a, rmax=560, life=1.2, flatten=0.45)
    # 价格：1973 → 1974 下跌 25%，在风暴里剧烈抖动；I6 起一路走到 1993
    storm = (1 - eio((t - t6) / 1.5)) * ke(t, B_WAPO + 0.4, 0.3)
    n = 1 + int(t > wt('I4', '一九七四') - 0.1) + int(19 * eio((t - t6 - 0.4) / 4.6))
    P = WP[:n].copy()
    P[:, 1] += storm * 0.28 * np.sin(t * 11 + np.arange(n) * 2.3)
    Pp = WP[:n].copy(); Pp[:, 1] += storm * 0.28 * np.sin((t - 0.05) * 11 + np.arange(n) * 2.3)
    xy, _ = cam.proj(P)
    if n > 1: hair(L, xy, ICE, 0.8 * a, th=2); hair(L, xy, ICE, 0.25 * a, th=7)
    for i in range(n):
        node(L, xy[i], AMBER if i == 1 else ICE, a * (1.4 + 0.5 * (i == 1)), 1.2)
    pts3d(L, cam, P, ICE, 0.5 * a * storm, prev=Pp, trail=1.2, ref=8.0)


def txt_wapo(img, t, subs):
    a = sc(t, B_WAPO, B_DEX)
    if a <= 0: return
    tb, td, tg, t6 = wt('I4', '一千零六十'), wt('I4', '八百万'), wt('I6', '超过'), I['I6']['t0']
    yr = '1973' if t < td - 0.2 else str(1974 + int(round(19 * eio((t - t6 - 0.4) / 4.6))))        # 价格线走到哪一年，年份就滚到哪一年
    text(img, yr, W / 2, 330, 110, 'corm_med', a=a * 0.9, gold=True, glow=0.15, shadow=0.3)
    text(img, 'THE WASHINGTON POST · 华盛顿邮报', W / 2, 410, 24, 'sans_med', SUB_GOLD, a, track=0.2)
    k1 = 1 - ke(t, td - 0.25, 0.3)
    fx.slam(img, '1,060 万美元', W / 2, 1300, 96, 'corm_med', t, tb - 0.05, a * k1, glow_=0.3)
    ycap(img, '1973 年 · 伯克希尔买入成本', a * k1 * ke(t, tb), y=1385)
    k2 = 1 - ke(t, t6 - 0.3, 0.4)
    fx.slam(img, '800 万美元', W / 2, 1300, 96, 'corm_med', t, td - 0.05, a * k2, gold=False, col=AMBER, glow_=0.3)
    fx.slam(img, '−25%', 900, 1215, 54, 'corm_med', t, td + 0.4, a * k2, gold=False, col=AMBER, glow_=0.3)
    ycap(img, '1974 年底 · 市值', a * k2 * ke(t, td), y=1385)
    k5 = env(t, I['I5']['t0'] - 0.1, t6 - 0.2, 0.3, 0.4)
    if k5 > 0:
        fx.slam(img, '按贝塔理论：“更危险”', W / 2, 1460, 46, 'serif_black', t, I['I5']['t0'] - 0.05, a * k5, gold=False, col=AMBER, glow_=0.25)
        brackets(img, (W / 2 - 280, 1418, W / 2 + 280, 1502), a * k5, col=AMBER, L_=20)
    if t > td - 0.1 and t < td + 0.6:
        fx.glitch(img, (0, 1200, W, 1400), t, 0.8 * (1 - (t - td + 0.1) / 0.7), seed=3)
    k6 = env(t, t6 - 0.1, tg - 0.1, 0.4, 0.3)
    fx.slam(img, '生意一直在增长', W / 2, 1300, 72, 'serif_black', t, t6 - 0.05, a * k6, glow_=0.35)
    if t > tg - 0.1:
        v = 0.106 + (4.40 - 0.106) * eio((t - tg) / 1.4)
        fx.slam(img, f'{v:.2f} 亿美元', W / 2, 1300, 110, 'corm_med', t, tg - 0.05, a, glow_=0.4)
        ycap(img, '1993 年 · 持股市值（二十年后）', a * ke(t, tg), y=1385)
        fx.sparks_up(img, t, 300, 780, 1200, a * ke(t, tg + 1.2), n=50, seed=6)
    counter(img, f'$ {(10.6 if t < td - 0.2 else (8.0 if t < tg else 8.0 + 432 * eio((t - tg) / 1.4))) * 1e6:,.0f}', a,
            col=AMBER if td - 0.2 <= t < tg else NUM)


# ---------------------------------------------------------------- 德克斯特：一动不动的金色球（没有股价）→ 海外竞争 → 炸成碎屑，价值归零 → 付出去的股票长成 57 亿
_rd = np.random.default_rng(31)
DEX = fib_sphere(1400, 9)
DEX_V = DEX / (np.linalg.norm(DEX, axis=1, keepdims=True) + 1e-6) * _rd.uniform(1.5, 4.5, (len(DEX), 1)) + _rd.normal(0, 0.6, (len(DEX), 3))
DEX_V[:, 2] += 2.5                                  # 碎屑朝镜头飞来
DEX_CAM = Cam((0, 0.9, 8.0), pitch=-0.02, cy=800, f=1000)


def dex_pos(t):
    tz = wt('I9', '价值归零') - 0.1
    dt = max(0.0, t - tz)
    P = DEX * 1.8 + [0, 0.9, 0]
    return P + DEX_V * dt + np.array([0, -1.2, 0]) * dt * dt


def dia_dex(L, t):
    a = sc(t, B_DEX, B_LEV)
    if a <= 0: return
    cam = DEX_CAM
    ts, tz, t57 = wt('I9', '海外'), wt('I9', '价值归零') - 0.1, wt('I10', '五十七')
    crack = eio((t - ts) / (tz - ts))
    fade = 1 - eio((t - tz) / 2.6)
    if fade > 0:
        n = len(DEX)
        col = np.tile(GOLD_H, (n, 1))
        bad = (np.arange(n) % 7 == 0)
        col[bad] = GOLD_H * (1 - crack) + AMBER * crack
        jit = (np.sin(t * 40 + np.arange(n))[:, None] * 0.02 * crack) if crack > 0 and t < tz else 0
        P = dex_pos(t) + jit
        pts3d(L, cam, P, col, 0.55 * a * fade, ref=8.0, prev=dex_pos(t - 0.05) if t > tz else None, trail=1.4)
        xy, _ = cam.proj(np.array([[0, 0.9, 0]]))
        node(L, xy[0], GOLD_C, a * (1 - crack * 0.6) * (1 - eo((t - tz) / 0.3)) * 1.5, 2.0)
    xy, _ = cam.proj(np.array([[0, 0.9, 0]]))
    shock(L, tuple(xy[0]), t, tz, AMBER, a, rmax=760, life=1.4)
    k8 = ke(t, wt('I8', '波动') - 0.2, 0.8) * (1 - eio((t - ts) / 0.8))
    if k8 > 0:                                       # 没有股价，也就没有波动：一条完全平直的线
        line_ = np.c_[np.linspace(-3.0, 3.0, 26), np.full(26, -2.4), np.full(26, 2.5)]
        xy2, _ = cam.proj(line_)
        hair(L, xy2, ICE, 0.6 * a * k8, th=2)
        for p in xy2: node(L, p, ICE, a * k8 * 0.7, 0.6)
    k10 = eio((t - t57 + 0.1) / 1.6)
    if k10 > 0:                                      # 付出去的伯克希尔股票：一团琥珀色粒子越长越大
        S = SPH * (0.2 + 2.1 * k10)
        sp = t * 0.3
        rot = np.c_[S[:, 0] * math.cos(sp) - S[:, 2] * math.sin(sp), S[:, 1], S[:, 0] * math.sin(sp) + S[:, 2] * math.cos(sp)] + [0, 0.9, 0]
        pts3d(L, cam, rot, AMBER, 0.6 * a * k10, ref=8.0)
        shock(L, tuple(xy[0]), t, t57 - 0.05, AMBER, a, rmax=600, life=1.2, flatten=0.5)


def txt_dex(img, t, subs):
    a = sc(t, B_DEX, B_LEV)
    if a <= 0: return
    ts, tz, t57 = wt('I9', '海外'), wt('I9', '价值归零') - 0.1, wt('I10', '五十七')
    text(img, '2014' if t > t57 - 0.2 else '1993', W / 2, 330, 110, 'corm_med', a=a * 0.9, gold=True, glow=0.15, shadow=0.3)
    text(img, 'DEXTER SHOE · 德克斯特鞋业', W / 2, 410, 24, 'sans_med', SUB_GOLD, a, track=0.2)
    k7 = 1 - ke(t, I['I8']['t0'] - 0.3, 0.4)
    fx.slam(img, '4.33 亿美元', W / 2, 1250, 96, 'corm_med', t, wt('I7', '四亿') - 0.05, a * k7, glow_=0.3)
    ycap(img, '以伯克希尔股票支付 · 全资收购', a * k7 * ke(t, wt('I7', '四亿')))
    k8 = env(t, I['I8']['t0'] - 0.1, ts - 0.1, 0.4, 0.3)
    fx.slam(img, '没有股价', W / 2, 1180, 72, 'serif_black', t, I['I8']['t0'] - 0.05, a * k8, gold=False, col=INK, glow_=0.2)
    fx.slam(img, 'σ ＝ 0', W / 2, 1290, 64, 'corm_med', t, wt('I8', '波动') - 0.05, a * k8, gold=False, col=ICE, glow_=0.25)
    k9 = env(t, ts - 0.1, tz, 0.3, 0.2)
    fx.slam(img, '海外竞争 · 优势荡然无存', W / 2, 1250, 56, 'serif_black', t, ts - 0.05, a * k9, gold=False, col=INK, glow_=0.2)
    kz = env(t, tz - 0.05, t57 - 0.25, 0.1, 0.4)
    fx.slam(img, '价值 → 0', W / 2, 1250, 120, 'serif_black', t, tz - 0.05, a * kz, gold=False, col=AMBER, glow_=0.45)
    if tz - 0.05 < t < tz + 0.7:
        fx.glitch(img, (0, 1100, W, 1400), t, 1.0 - (t - tz + 0.05) / 0.75, seed=5)
        fx.glitch(img, (100, 450, 980, 1050), t, 0.8 - (t - tz + 0.05) / 0.9, seed=6)
    if t > t57 - 0.1:
        v = 4.33 + (57 - 4.33) * eio((t - t57) / 1.4)
        fx.slam(img, f'{v:.1f} 亿美元' if v < 56.9 else '57 亿美元', W / 2, 1210, 104, 'corm_med', t, t57 - 0.05, a, gold=False, col=AMBER, glow_=0.4)
        ycap(img, '当初付出的股票 · 2014 年的价值', a * ke(t, t57), y=1300)
        kq = ke(t, t57 + 1.3, 0.8)
        text(img, '“To date, Dexter is the worst deal that I’ve made.”', W / 2, 1390, 30, 'ebg_i', INK, a * kq, shadow=0.6)
        text(img, '—— 巴菲特 2007 年致股东信', W / 2, 1440, 24, 'sans', INK2, a * kq, track=0.06)


# ---------------------------------------------------------------- 杠杆：价格的浪 + 被拴住的光点；被迫在低点卖出时，脚下被撕开一个永久的坑
GX, GZ = np.meshgrid(np.linspace(-4.5, 4.5, 46), np.linspace(-9, 2.5, 34))
GX, GZ = GX.ravel(), GZ.ravel()
LEV_CAM = Cam((0, 2.6, 5.4), pitch=-0.33, cy=760, f=1000)
NX, NZ = 0.0, -1.5


def lev_amp(t):
    return 0.55 * (1 - 0.8 * eio((t - wt('I11', '暂时') - 0.6) / 3.0))


def lev_h(x, z, t, tear):
    h = lev_amp(t) * np.sin(0.9 * z - 2.1 * t + 0.35 * x)
    return h - tear * 1.9 * np.exp(-((x - NX) ** 2 + (z - NZ) ** 2) / 0.9)


def dia_lev(L, t):
    a = sc(t, B_LEV, B_TODAY)
    if a <= 0: return
    cam = LEV_CAM
    tp = wt('I11', '低点卖出')
    tear = eio((t - tp - 0.25) / 1.1)
    P = np.c_[GX, lev_h(GX, GZ, t, tear) - 0.6, GZ]
    pts3d(L, cam, P, ICE, 0.95 * a, ref=6.0)
    # 光点：随浪起伏；卖出那一刻定格在浪谷，然后坠进坑底熄灭
    tt = min(t, tp)
    ride = float(lev_h(NX, NZ, tt, 0.0)) - 0.6 + 0.35
    trough = -lev_amp(tp) - 0.6 + 0.2
    y = lerp(ride, trough, eio((t - tp) / 0.25))
    fall = eio((t - tp - 0.3) / 1.0)
    y = lerp(y, -2.6, fall)
    xy, _ = cam.proj(np.array([[NX, y, NZ]]))
    col = GOLD_C * (1 - fall) + np.array([0.3, 0.3, 0.33], np.float32) * fall
    node(L, xy[0], col, a * (1.6 - 1.2 * fall), 1.6)
    kt = ke(t, wt('I11', '借了钱') - 0.1) * (1 - eio((t - tp - 1.2) / 0.5))
    anc, _ = cam.proj(np.array([[NX, -2.9, NZ + 0.6]]))
    if kt > 0:
        hair(L, [xy[0], xy[0] + (anc[0] - xy[0]) * kt], AMBER, 0.7 * a, th=2)
        node(L, anc[0], AMBER, a * kt, 1.0)
    shock(L, tuple(xy[0]), t, tp, AMBER, a * 0.7, rmax=360, life=0.9, flatten=0.4)
    kp = ke(t, wt('I11', '永久') - 0.1)
    if kp > 0:
        hole, _ = cam.proj(np.array([[NX, -2.5, NZ]]))
        ring(L, hole[0], 70, AMBER, 0.9 * a * kp, th=2)
        glow_pt(L, hole[0], 40, AMBER, 0.5 * a * kp)


def txt_lev(img, t, subs):
    a = sc(t, B_LEV, B_TODAY)
    if a <= 0: return
    tp = wt('I11', '低点卖出')
    text(img, 'LEVERAGE · 杠杆与被迫卖出', W / 2, 330, 26, 'sans_med', SUB_GOLD, a, track=0.2)
    fx.slam(img, '借来的钱', 300, 450, 60, 'serif_black', t, wt('I11', '借了钱') - 0.05, a, gold=False, col=AMBER, glow_=0.25)
    fx.slam(img, '被迫在低点卖出', 760, 450, 60, 'serif_black', t, tp - 0.05, a, gold=False, col=AMBER, glow_=0.25)
    if tp < t < tp + 0.6: fx.glitch(img, (0, 380, W, 1200), t, 0.9 * (1 - (t - tp) / 0.6), seed=9)
    fx.slam(img, '暂时的下跌', W / 2, 1210, 64, 'serif_black', t, wt('I11', '暂时') - 0.05, a, gold=False, col=ICE, glow_=0.25)
    fx.slam(img, '永久的损失', W / 2, 1330, 88, 'serif_black', t, wt('I11', '永久') - 0.05, a, gold=False, col=AMBER, glow_=0.45)
    if t > wt('I11', '锁定') - 0.1:
        text(img, '↓  被锁定成', W / 2, 1268, 24, 'sans_med', INK2, a * ke(t, wt('I11', '锁定') - 0.1), track=0.2)


# ---------------------------------------------------------------- 今天：账户回撤时的两个问题
def i12_path():
    n = 40
    xs = np.linspace(150, 930, n)
    ys = 480 + 300 * np.clip(np.linspace(0, 1.5, n), 0, 1) ** 0.75 + 12 * np.sin(np.arange(n) * 1.9)
    return np.c_[xs, ys]


def dia_today(L, t):
    a = sc(t, B_TODAY, B_CLOSE)
    if a <= 0: return
    P = i12_path()
    k = eio((t - B_TODAY - 0.2) / 1.8)
    m = max(2, int(len(P) * k))
    hair(L, P[:m], ICE, 0.55 * a, th=2)
    cloud(L, P[:m], ICE, 0.5 * a)
    node(L, P[m - 1], ICE if m < len(P) else GOLD_C, a * 1.2, 1.1)
    for kw, x in (('这门生意', 560), ('我会', 860)):
        kk = ke(t, wt('I12', kw) - 0.1)
        if kk > 0:
            y = float(np.interp(x, P[:, 0], P[:, 1]))
            node(L, (x, y), GOLD_C, a * kk * 1.6, 1.6)
            shock(L, (x, y), t, wt('I12', kw) - 0.1, GOLD_H, a, rmax=200, life=0.8)
            beam(L, x, y, y - 220, GOLD_H, 0.35 * a * kk, wd=4)


def txt_today(img, t, subs):
    a = sc(t, B_TODAY, B_CLOSE)
    if a <= 0: return
    P = i12_path()
    text(img, 'TODAY · 账户大幅回撤时', W / 2, 330, 26, 'sans_med', SUB_GOLD, a, track=0.2)
    for i, (kw, x, s, y) in enumerate((('这门生意', 560, '这门生意还在吗？', 1150), ('我会', 860, '我会被迫卖出吗？', 1300))):
        kk = ke(t, wt('I12', kw) - 0.1)
        yy = float(np.interp(x, P[:, 0], P[:, 1]))
        if kk > 0:
            brackets(img, (x - 40, yy - 40, x + 40, yy + 40), a * kk, L_=14)
            text(img, f'0{i + 1}', x, yy - 60, 26, 'corm_med', SUB_GOLD, a * kk)
        fx.slam(img, s, W / 2, y, 76, 'serif_black', t, wt('I12', kw) - 0.05, a, glow_=0.4)
    fx.typewriter(img, 'Drawdown  ≠  Permanent loss', W / 2, 1030, 32, 'ebg', INK2, a, t, B_TODAY + 0.6, cps=30, cursor=False)


# ---------------------------------------------------------------- 收尾：在全片节点组成的星图里向前飞行，越来越快；高潮重拍上全部亮起
_rn = np.random.default_rng(55)
NET3 = np.c_[_rn.uniform(-5, 5, 1400), _rn.uniform(-8, 8, 1400), _rn.uniform(-90, 2, 1400)]
NET3_C = _rn.random(1400)
NET3_E = []
for _i in range(0, 1400, 3):
    _dd = np.linalg.norm(NET3 - NET3[_i], axis=1); _dd[_i] = 1e9
    NET3_E.append((_i, int(np.argmin(_dd))))
CLOSE_T1 = T_SUM - 0.4


def fly_z(t):
    """相机沿 -z 前进：先慢后快（蓄力），到高潮前接近“曲速”"""
    u = max(0.0, t - B_CLOSE)
    U = CLOSE_T1 - B_CLOSE
    return 4.0 - (1.2 * u + 34.0 * max(0.0, (u - (U - 6.0)) / 6.0) ** 3)


def fly_cam(t):
    return Cam((0.3 * math.sin(t * 0.2), 0.0, fly_z(t)), yaw=0.03 * math.sin(t * 0.3), cy=880, f=900)


def dia_close(L, t):
    a = env(t, B_CLOSE + 0.15, CLOSE_T1, 0.6, 0.12)
    if a <= 0: return
    cam = fly_cam(t); pc = fly_cam(t - 2.5 / 30)
    gold = NET3_C > 0.72
    pts3d(L, cam, NET3[gold], GOLD_H, 1.4 * a, ref=6.0, prev_cam=pc, trail=1.2)
    pts3d(L, cam, NET3[~gold], ICE, 1.1 * a, ref=6.0, prev_cam=pc, trail=1.2)
    xy, d = cam.proj(NET3)
    for i, j in NET3_E:
        if 0.6 < d[i] < 16 and 0.6 < d[j] < 16:
            hair(L, [xy[i], xy[j]], FOG, 0.22 * a * min(1, 6 / d[i]))


def txt_close(img, t, subs):
    a = env(t, I['I13']['t0'] - 0.3, I['I13']['t1'] + 1.2, 0.5, 0.6)
    if a <= 0: return
    for kw, s_, y, gold_, sz in (('价格', '价格的剧烈波动，', 760, False, 52), ('不必然', '不必然意味着真正的风险；', 840, False, 52),
                                 ('真正值得', '真正值得警惕的，', 970, True, 64), ('本金', '是本金永久损失的可能性。', 1060, True, 64)):
        k = eio((t - wt('I13', kw) + 0.15) / 0.9)
        if gold_: gold_title(img, s_, W / 2, y, sz, a * k, wipe=k, glow_=0.2, track=0.06)
        else: text(img, s_, W / 2, y, sz, 'serif_bold', INK, a * k, track=0.08, wipe=k, shadow=0.8)


def dia_sum(L, t):
    """高潮：前 0.4 秒纯黑，重拍上整片星图同时亮起、冲击波扩散，再缓缓暗下"""
    if t < T_SUM: return
    k = t - T_SUM
    fade = 1 - eio((t - END['t_particles'] + 0.4) / 1.4)
    surge = math.exp(-k / 1.4)
    cam = Cam((0, 0, 6.0 - 0.5 * k), cy=900, f=900)
    gold = NET3_C > 0.55
    P = NET3 * [1, 1, 0.25] + [0, 0, -3]
    pts3d(L, cam, P[gold], GOLD_H, fade * (0.3 + 2.6 * surge), ref=6.0)
    pts3d(L, cam, P[~gold], ICE, fade * (0.2 + 1.8 * surge), ref=6.0)
    shock(L, (W / 2, 950), t, T_SUM, GOLD_H, fade * 0.6, rmax=1100, life=1.0, flatten=0.5)


# ================================================================ 一句话总结 + 品牌片尾（系列固定片尾，与第一集一致）
def summary_masks():
    out = []
    for s, y in (('波动不是风险，', 880), ('永久损失才是。', 1010)):
        m, w, base, pad = text_mask(s, 'serif_black', 96, 0.04)
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


def dust(img, t, a=1.0, n=70, seed=5, col=None):
    """缓慢漂浮的金色微尘（与第一集一致）"""
    if a <= 0.003: return
    r = np.random.default_rng(seed)
    P = r.random((n, 6))
    for i in range(n):
        x = (P[i, 0] * W + 14 * math.sin(0.11 * t + P[i, 1] * 6.28)) % W
        y = (P[i, 2] * H - t * (6 + 10 * P[i, 3])) % H
        tw = 0.5 + 0.5 * math.sin(t * (0.6 + P[i, 4]) + P[i, 5] * 6.28)
        glow(img, (x, y), 1.2 + 1.6 * P[i, 3], col if col is not None else GOLD, a * 0.35 * tw)


def txt_sum(img, t, subs):
    tp = END['t_particles']
    a = env(t, T_SUM - 0.05, tp + 0.4, 0.05, 0.4)
    if a <= 0: return
    k = t - T_SUM
    glow(img, (W / 2, 950), 300, GOLD * 0.22, math.exp(-max(k, 0) / 1.4) * a)
    dust(img, t, a * 0.8)
    text(img, '一句话总结', W / 2, 740, 28, 'sans_med', SUB_GOLD, a * eo(k / 0.6), track=0.4)
    for sg in (-1, 1):
        line(img, (W / 2 + sg * 110, 740), (W / 2 + sg * (110 + 90 * eo(k / 1.0)), 740), SUB_GOLD, a * 0.6, 1)
    w1 = eo((t - VOD['M']['t0'] + 0.1) / 1.0); w2 = eo((t - wt('M', '永久') + 0.05) / 1.0)
    sh = cl((t - VOD['M']['t1'] - 0.2) / 1.4) if VOD['M']['t1'] + 0.2 < t < VOD['M']['t1'] + 1.6 else None
    gold_title(img, '波动不是风险，', W / 2, 880, 96, a, wipe=w1, shine=sh, track=0.04)
    gold_title(img, '永久损失才是。', W / 2, 1010, 96, a, wipe=w2, shine=sh, track=0.04)
    text(img, '伯克希尔股东大会投资智慧录 · 第二集', W / 2, 1150, 26, 'sans', INK2, a * eo((k - 1.2) / 0.8), track=0.1)


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
DIAS = [dia_cold, dia_title, dia_s1, dia_s2, dia_s3, dia_ctx, dia_qa, dia_i1, dia_i2, dia_i3, dia_wapo, dia_dex, dia_lev, dia_today,
        dia_close, dia_sum]
TXTS = [txt_cold, txt_title, txt_s1, txt_s2, txt_s3, txt_ctx, txt_qa, txt_card, txt_i1, txt_i2, txt_i3, txt_wapo, txt_dex, txt_lev,
        txt_today, txt_close, txt_sum]


def frame(t, subs=True):
    L = np.zeros((H, W, 3), np.float32)
    for d in DIAS: d(L, t)
    img = finish(L, t)
    ins_bg(img, t)
    for tx in TXTS: tx(img, t, subs)
    ins_tag(img, t)
    if subs:
        narr_sub(img, t, INTRO['subs'])
        narr_sub(img, t, INS['subs'], hide=('I13',))
    ruler(img, t)
    s_end(img, t)
    # 后期（与第一集一致）：泛光、横向光晕；有配乐的段落在重拍上推镜 / 闪光 / 色散，小节强拍轻微脉动（原声问答段减弱）
    img = fx.post(img, t, HITS, BARS, strength=0.6 if T_Q + 1 < t < T_QE else 1.0)
    img = img * vignette() + GRAIN[int(t * FPS) % len(GRAIN)]
    fade_all = 1 - eio((t - END['t_fade0']) / (END['t_fade1'] - END['t_fade0']))
    HUD.draw(img, t, alpha=float(fade_all * env(t, 0.0, 1e9, 0.8, 0.01)))
    if t < 0.3: img *= t / 0.3
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
