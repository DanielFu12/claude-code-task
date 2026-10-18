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


I = {k: V(k) for k in ('I1', 'I2', 'I3', 'I4', 'I5', 'I6', 'I7', 'I8', 'I9', 'I10', 'I10b', 'I11', 'I12', 'I13')}
HOOK = TL['hook']; ENDQ_T = TL['endq']


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


def glow_pt(L, c, r, col, k):
    """柔和的光斑（加色）"""
    if k <= 0.003: return
    g = soft_dot(float(round(r, 1)))
    R_ = g.shape[0] // 2
    add(L, np.asarray(col, np.float32), g * k, int(c[0]) - R_, int(c[1]) - R_)


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


# ================================================================ 面板与图表（不用玻璃：深色实底 + 细边 + 发光的角标折线）
PANEL_BG = C(8, 10, 17)


def chapter_tag(img, t, title, a=1.0):
    """左上章节标签（与第一集一致）"""
    if a <= 0.003: return
    text(img, '第二集 · 风险不是波动', 72, 66, 26, 'sans_med', SUB_GOLD, a * 0.95, 'l', track=0.12, shadow=0.3)
    line(img, (72, 92), (72 + 64, 92), SUB_GOLD, a * 0.7, 1)
    text(img, title, 72, 116, 22, 'sans', INK2, a * 0.85, 'l', track=0.08, shadow=0.3)


def panel(img, x0, y0, x1, y1, a, col=None, title=None, en=None, fill=0.72):
    if a <= 0.003: return
    col = GOLD_C if col is None else col
    X0, Y0, X1, Y1 = int(max(x0, 0)), int(max(y0, 0)), int(min(x1, W)), int(min(y1, H))
    reg = img[Y0:Y1, X0:X1]
    k = fill * a
    reg *= (1 - k); reg += PANEL_BG * k
    rrect(img, x0, y0, x1, y1, 14, col * 0.75, a * 0.5, 1)
    line(img, (x0 + 30, y0), (x1 - 30, y0), col, a * 0.35, 1)
    brackets(img, (x0, y0, x1, y1), a * 0.95, col=col, L_=22, th=2)
    if title:
        text(img, title, (x0 + x1) / 2, y0 + 44, 26, 'sans_med', col, a, track=0.3, shadow=0.3)
        if en: text(img, en.upper(), (x0 + x1) / 2, y0 + 78, 15, 'corm', INK2, a * 0.85, track=0.3, shadow=0.0)


def gline(img, pts, col, a, th=3, halo=7.0, k=1.0):
    """发光的粗线（显示空间加色）"""
    if a <= 0.003 or len(pts) < 2: return
    P = np.asarray(pts, np.float64)
    pad = int(halo * 3 + th + 4)
    x0, y0 = int(max(P[:, 0].min() - pad, 0)), int(max(P[:, 1].min() - pad, 0))
    x1, y1 = int(min(P[:, 0].max() + pad, W)), int(min(P[:, 1].max() + pad, H))
    if x1 <= x0 or y1 <= y0: return
    m = np.zeros((y1 - y0, x1 - x0), np.float32)
    cv2.polylines(m, [((P - [x0, y0]) * 16).astype(np.int32).reshape(-1, 1, 2)], False, 1.0, th, cv2.LINE_AA, 4)
    g = cv2.GaussianBlur(m, (0, 0), halo) * 0.9 * k
    reg = img[y0:y1, x0:x1]
    c = np.asarray(col, np.float32)
    reg *= (1 - m[..., None] * a); reg += m[..., None] * a * (c * 0.75 + 0.25)
    reg += g[..., None] * c * a


def area(img, pts, ybase, col, a, top=0.32):
    """折线下方的渐变填充"""
    if a <= 0.003 or len(pts) < 2: return
    P = np.asarray(pts, np.float64)
    poly_ = np.vstack([P, [[P[-1, 0], ybase], [P[0, 0], ybase]]])
    x0, y0 = int(max(P[:, 0].min(), 0)), int(max(min(P[:, 1].min(), ybase), 0))
    x1, y1 = int(min(P[:, 0].max() + 1, W)), int(min(max(P[:, 1].max(), ybase) + 1, H))
    if x1 <= x0 or y1 <= y0: return
    m = np.zeros((y1 - y0, x1 - x0), np.float32)
    cv2.fillPoly(m, [((poly_ - [x0, y0]) * 16).astype(np.int32).reshape(-1, 1, 2)], 1.0, cv2.LINE_AA, 4)
    gy = np.linspace(top, 0.02, y1 - y0, dtype=np.float32)[:, None] if ybase >= P[:, 1].max() else np.linspace(0.02, top, y1 - y0, dtype=np.float32)[:, None]
    img[y0:y1, x0:x1] += (m * gy)[..., None] * np.asarray(col, np.float32) * a


def bar(img, x, ybase, w, h, col, a, k=1.0):
    """竖直柱：上亮下暗的渐变 + 顶部发光的边"""
    if a <= 0.003 or h <= 0.5: return
    h = h * k
    x0, x1 = int(x - w / 2), int(x + w / 2)
    y0, y1 = int(ybase - h), int(ybase)
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if X1 <= X0 or Y1 <= Y0: return
    c = np.asarray(col, np.float32)
    g = np.linspace(0.85, 0.28, y1 - y0, dtype=np.float32)[Y0 - y0:Y1 - y0, None, None]
    reg = img[Y0:Y1, X0:X1]
    reg *= (1 - 0.85 * a); reg += c * g * a
    line(img, (x0, y0), (x1, y0), c * 1.1 + 0.15, a, 2)
    glow(img, (x, y0), w * 0.55, c * 0.5, a * 0.5)


def dashed(img, p, q, col, a, dash=14, gap=10, th=1):
    if a <= 0.003: return
    p, q = np.array(p, float), np.array(q, float)
    L_ = np.linalg.norm(q - p); d = (q - p) / max(L_, 1e-6)
    s = 0.0
    while s < L_:
        e = min(s + dash, L_)
        line(img, tuple(p + d * s), tuple(p + d * e), col, a, th)
        s += dash + gap


def tick(img, c, r, col, a):
    """对勾"""
    if a <= 0.003: return
    x, y = c
    poly(img, [(x - r * 0.5, y), (x - r * 0.12, y + r * 0.4), (x + r * 0.55, y - r * 0.45)], col, a, 3)


def cross(img, c, r, col, a):
    if a <= 0.003: return
    x, y = c
    line(img, (x - r, y - r), (x + r, y + r), col, a, 3); line(img, (x - r, y + r), (x + r, y - r), col, a, 3)


def waveform(img, t, cx, cy, w, hmax, a=1.0, n=24, col=None):
    """原声波形（与第一集一致的竖条）"""
    if a <= 0.003: return
    e = ofr(t)
    bw = w / n
    for k in range(n):
        v = float(e[k]) if k < len(e) else 0.0
        hh = 2 + hmax * min(v, 1.0)
        x = cx - w / 2 + (k + 0.5) * bw
        rect(img, x - 1.5, cy - hh, x + 1.5, cy + hh, col if col is not None else SUB_GOLD, a * (0.35 + 0.65 * min(v * 1.2, 1)))


def narr_sub(img, t, subs, y=1610, hide=()):
    """口播字幕（与第一集一致）"""
    for s in subs:
        if s['id'] in hide: continue
        if s['t0'] <= t <= s['t1']:
            a = env(t, s['t0'], s['t1'], 0.06, 0.08)
            text(img, s['text'], W / 2, y, 46, 'sans_med', INK, a, 'm', track=0.04, shadow=0.95, rise=(1 - a) * 6)


def orig_sub(img, s, a, bottom=1650):
    """原声字幕（与第一集一致）：中文 46px 在上，英文 36px 在下"""
    zl = wrap(s['zh'], 'sans_med', 46, 940)
    el = wrap(s['en'], 'ebg', 34, 930, cjk=False)
    hh = len(zl) * 62 + 8 + len(el) * 44
    y = bottom - hh + 31
    for ln in zl:
        text(img, ln, W / 2, y, 46, 'sans_med', INK, a, 'm', track=0.03, shadow=0.9); y += 62
    y += 8 - 31 + 22
    for ln in el:
        text(img, ln, W / 2, y, 34, 'ebg', INK2 * 1.05, a * 0.95, 'm', shadow=0.9); y += 44


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


def cold_a(t):
    return env(t, COLD['t0'] - 0.25, COLD['t1'] + 0.45, 0.4, 0.5)


def dia_cold(L, t):
    a = cold_a(t)
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
    a = cold_a(t)
    if a <= 0: return
    src = COLD['src_in'] + (t - COLD['t0'])
    z = 1.0 + 0.06 * eio((t - COLD['t0']) / 6.0)
    foot(img, QA_CLIP, min(max(src, 0.0), 309.0), W / 2, 760, a, zoom=z, pan=(0.03, -0.02), blur=0.55)
    brackets(img, (W / 2 - WIN_W / 2 + 20, 760 - WIN_H / 2 + 20, W / 2 + WIN_W / 2 - 20, 760 + WIN_H / 2 - 20), a * 0.55, col=GOLD_H, L_=34)
    scanline(img, (40, 760 - WIN_H / 2, W - 40, 760 + WIN_H / 2), t, COLD['t0'] - 0.2, a * 0.8)
    text(img, '1994 · 伯克希尔股东大会 · 巴菲特原声', W / 2, 470, 28, 'sans_med', SUB_GOLD, a * 0.9, track=0.12, shadow=0.4)
    line(img, (W / 2 - 300, 510), (W / 2 + 300, 510), SUB_GOLD, a * 0.35, 1)
    if subs:
        for s in TL['cold_subs']:
            sa = env(t, s['t0'] - 0.1, s['t1'] + 0.1, 0.15, 0.2) * a
            if sa > 0: orig_sub(img, s, sa, bottom=1300)


# ================================================================ 片名（与第一集同款：系列片名 + 本集集名）
def title_a(t): return env(t, T_TITLE - 0.05, COLD['t0'] - 0.1, 0.05, 0.5)


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


# ================================================================ 开场口播：上方是 1994 年大会影像，下方是图表面板
FOOT_Y = 540
PRICE = [100, 103, 99, 104, 108, 102, 105, 96, 90, 84, 78, 75]


def intro_a(t):
    return env(t, V('S2')['t0'] - 0.4, T_CTX - 0.3, 0.5, 0.6)


def s1_pts():
    x0, x1, yb = 170, 910, 1230
    xs = np.linspace(x0, x1, 12)
    ys = yb - (np.array(PRICE) - 62) / 50 * 300
    return np.c_[xs, ys], yb


def hook_a(t):
    return 1.0 - eio((t - (T_TITLE - 0.45)) / 0.4)


def dia_s1(L, t):
    a = hook_a(t)
    if a <= 0: return
    P, yb = s1_pts()
    td = wt('S1', '跌掉')
    if t > td + 0.5:
        shock(L, tuple(P[-1]), t, td + 0.5, AMBER, a, rmax=240, life=0.9)
        rng = np.random.default_rng(4)                       # 下跌段洒落的火花
        ph = (t * 0.8 + rng.random(50)) % 1.0
        xs = P[6, 0] + (P[-1, 0] - P[6, 0]) * rng.random(50)
        ys = np.interp(xs, P[6:, 0], P[6:, 1]) + ph * 160
        cloud(L, np.c_[xs, ys], AMBER, 0.6 * a * ke(t, td + 0.5), w=(1 - ph))


def txt_s1(img, t, subs):
    a = intro_a(t)
    if a > 0:
        clip = CLIPS[1500] if t < V('S3')['t0'] - 0.2 else CLIPS[200]
        ct = (t - V('S2')['t0'] + 2.0) % 15.5
        foot(img, clip, ct, W / 2, FOOT_Y, a, zoom=1.05 + 0.006 * ct, blur=0.5)
        text(img, '1994 · 奥马哈 · 伯克希尔股东大会上午场实况', 72, FOOT_Y - WIN_H / 2 - 30, 22, 'sans', INK2, a * 0.85, 'l', track=0.06, shadow=0.5)
    ap = hook_a(t)
    if ap <= 0: return
    # 第 0 秒就有的中文大字钩子（不淡入，首帧即可读）
    zs = 1.0 + 0.06 * (1 - eo(t / 0.5))
    text(img, '跌 25%', W / 2, 400, int(170 * zs), 'corm_med', AMBER, ap, track=0.04, glow=0.3, glow_col=AMBER, shadow=0.6)
    text(img, '是更危险，还是更便宜？', W / 2, 590, int(74 * zs), 'serif_black', a=ap, gold=True, glow=0.25, shadow=0.7)
    panel(img, 110, 800, 970, 1290, ap, col=ICE, title='一只股票 · 一年', en='one stock · one year')
    P, yb = s1_pts()
    td = wt('S1', '跌掉')
    h = eio((t - V('S1')['t0'] + 0.2) / (td + 0.8 - V('S1')['t0']))
    n = max(2, int(1 + 11 * h))
    f = (1 + 11 * h) - n
    Q = P[:n].copy()
    if n < 12: Q = np.vstack([Q, P[n - 1] + (P[n] - P[n - 1]) * f])
    dashed(img, (150, P[0, 1]), (930, P[0, 1]), INK2, ap * 0.5)
    text(img, '买入价', 150, P[0, 1] - 22, 20, 'sans', INK2, ap * 0.8, 'l')
    area(img, Q, yb, ICE, ap)
    gline(img, Q[:min(len(Q), 8)], ICE, ap, th=4)
    if len(Q) > 7: gline(img, Q[6:], AMBER, ap, th=4)
    glow(img, tuple(Q[-1]), 14, GOLD_HI, ap * 0.9)
    text(img, '示意', 930, 1265, 18, 'sans', INK3 * 1.5, ap * 0.8, 'r')
    k = ke(t, wt('S1', '百分之') - 0.1)
    if k > 0:
        line(img, (P[-1, 0] + 30, P[0, 1]), (P[-1, 0] + 30, P[-1, 1]), AMBER, ap * k, 2)
        fx.slam(img, '−25%', 760, 905, 96, 'corm_med', t, wt('S1', '百分之') - 0.05, ap, gold=False, col=AMBER, glow_=0.35)
    for i, (s, kw, x, col) in enumerate((('更危险？', '更危险', 300, ICE), ('更便宜？', '更便宜', 780, None))):
        tk = wt('S1', kw)
        kk = ke(t, tk - 0.05, 0.4)
        if kk > 0:
            panel(img, x - 190, 1340, x + 190, 1470, ap * kk, col=col if col is not None else GOLD_C, fill=0.8)
            fx.slam(img, s, x, 1405, 64, 'serif_black', t, tk - 0.05, ap, gold=col is None, col=col, glow_=0.3)


# ---------------------------------------------------------------- S2：教科书的贝塔理论——波动越大，“风险”越高
def dia_s2(L, t):
    a = env(t, V('S2')['t0'] - 0.1, V('S3')['t0'] - 0.2, 0.35, 0.35)
    if a <= 0: return
    te = wt('S2', '更危险')
    shock(L, (W / 2, 1405), t, te - 0.05, AMBER, a, rmax=420, life=1.0, flatten=0.35)


def txt_s2(img, t, subs):
    a = env(t, V('S2')['t0'] - 0.1, V('S3')['t0'] - 0.2, 0.35, 0.35)
    if a <= 0: return
    panel(img, 110, 800, 970, 1290, a, col=ICE, title='教科书 · 贝塔理论', en='textbook beta theory')
    text(img, 'β  =  Cov( rᵢ , rₘ )  ⁄  Var( rₘ )', W / 2, 920, 40, 'ebg', INK, a * ke(t, V('S2')['t0']), shadow=0.4)
    # 两组波动：大盘 vs 这只股票
    rng = np.random.default_rng(7)
    k = eio((t - V('S2')['t0'] - 0.2) / 1.2)
    n = max(2, int(40 * k))
    xs = np.linspace(190, 890, 40)[:n]
    base = np.sin(np.arange(40) * 0.7) + rng.normal(0, 0.4, 40)
    gline(img, np.c_[xs, 1010 - 12 * base[:n]], INK2, a * 0.8, th=2)
    gline(img, np.c_[xs, 1125 - 26 * base[:n]], ICE, a, th=3)
    text(img, '大盘', 170, 1010, 22, 'sans_med', INK2, a, 'r')
    text(img, '这只股票', 170, 1125, 22, 'sans_med', ICE, a, 'r')
    fx.slam(img, 'β ↑   ＝   风险 ↑', W / 2, 1250, 48, 'serif_black', t, wt('S2', '贝塔') - 0.05, a, glow_=0.3)
    te = wt('S2', '更危险')
    fx.slam(img, '更危险', W / 2, 1405, 100, 'serif_black', t, te - 0.05, a, gold=False, col=AMBER, glow_=0.45)


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


# ================================================================ 原始问答：原始录像窗口 + 关键观点面板（与第一版同样直观，但不用玻璃）
WIN_Y = 500


def qa_env(t, sc_, fi=0.45, fo=0.45, pre=0.3, post=0.3):
    s = QSC.get(sc_)
    if not s: return 0.0
    return env(t, s['t0'] - pre, s['t1'] + post, fi, fo)


def qa_a(t):
    return env(t, T_Q - 0.4, T_QE + 0.6, 0.6, 0.9)


def dia_qa(L, t):
    a = qa_a(t)
    if a <= 0: return
    s = qa_env(t, 'expect') * a
    if s > 0 and t > qs('A25') - 0.1:
        shock(L, (W / 2, 1290), t, qs('A25'), GOLD_H, s, rmax=360, life=1.0, flatten=0.3)
    s = qa_env(t, 'define') * a
    if s > 0:
        shock(L, (W / 2, 1050), t, qs('A1', 0.6), GOLD_H, s, rmax=420, life=1.1, flatten=0.3)


def txt_qa(img, t, subs):
    a = qa_a(t)
    if a <= 0: return
    chapter_tag(img, t, '原始问答 · 1994 上午场原始录像（节选）', a)
    fr = grade(QA_CLIP.get(qa_src(t)), sat=0.62, gain=0.98)
    mz = eio((t - QA['munger_t'] + 1.0) / 2.5)                       # 芒格开口时，镜头缓缓推向芒格
    zoom = 1.0 + 0.32 * mz + 0.02 * math.sin((t - T_Q) * 0.05)
    wa = 1.0
    for ct in QA['cuts']:                                            # 省略处：画面暗下去再亮起
        wa = min(wa, 1 - 0.85 * math.exp(-((t - ct) / 0.28) ** 2))
    window(img, fr, W / 2, WIN_Y, WIN_W, WIN_H, zoom=zoom, pan=(0.17 * mz, -0.03 * mz), a=a * wa, feather=12, blur_bg=0.45)
    brackets(img, (W / 2 - WIN_W / 2 - 8, WIN_Y - WIN_H / 2 - 8, W / 2 + WIN_W / 2 + 8, WIN_Y + WIN_H / 2 + 8), a * 0.8, col=SUB_GOLD, L_=26)
    for ct in QA['cuts']:
        k = env(t, ct - 0.5, ct + 0.7, 0.25, 0.35)
        if k > 0: text(img, '· 节选 ·', W / 2, WIN_Y, 30, 'sans_med', INK, a * k, track=0.3)
    text(img, '画面与声音：1994 年上午场原始录像', 72, WIN_Y + WIN_H / 2 + 40, 22, 'sans', INK3 * 1.4, a * 0.95, 'l', track=0.04, shadow=0.5)
    mt, at = QA['munger_t'], QA['answer_t']
    spk = '查理·芒格' if t >= mt - 0.3 else ('沃伦·巴菲特' if t >= at - 0.2 else '提问 · 来自密歇根州的股东')
    circle(img, (84, 786), 6, GOLD, a, fill=True)
    text(img, spk, 104, 786, 30, 'sans_med', INK, a, 'l', track=0.04)
    waveform(img, t, 860, 786, 260, 22, a)
    qa_panels(img, t, a)
    if subs:
        for s in QA['subs']:
            sa = env(t, s['t0'], s['t1'], 0.07, 0.07)
            if sa > 0: orig_sub(img, s, sa * a)
        la = env(t, TL['laugh']['t0'], TL['laugh']['t1'], 0.15, 0.2)
        if la > 0: text(img, '（现场笑声）', W / 2, 1400, 30, 'sans', INK2, la * a * 0.85, track=0.1)


PX0, PY0, PX1, PY1 = 110, 860, 970, 1350


def qa_panels(img, t, a):
    """关键观点面板（y 860–1350）"""
    # 提问
    ka = qa_env(t, 'ask') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='股东的问题', en='the question')
        k0 = ke(t, qs('Q1', 0.4)) * (1 - ke(t, qs('Q2'), 0.5))
        text(img, '金融世界里的风险，', W / 2, 1060, 60, 'serif_bold', INK, ka * k0)
        text(img, '您怎么看？', W / 2, 1160, 60, 'serif_bold', a=ka * k0, gold=True)
        k2 = ke(t, qs('Q2')) * (1 - ke(t, qs('Q5'), 0.5))
        if k2 > 0:
            panel(img, 160, 990, 500, 1180, ka * k2, col=GOLD_C, fill=0.5)
            text(img, '您的风险观', 330, 1085, 48, 'serif_black', a=ka * k2, gold=True)
            k3 = ke(t, qs('Q3')) * (1 - ke(t, qs('Q5'), 0.5))
            panel(img, 580, 990, 920, 1180, ka * k3, col=ICE, fill=0.5)
            text(img, '传统的风险观', 750, 1085, 48, 'serif_black', ICE, ka * k3)
            fx.slam(img, '≠', W / 2, 1085, 70, 'inter_semi', t, qs('Q3', 1.0), ka * (1 - ke(t, qs('Q5'), 0.5)), gold=False, col=AMBER)
            text(img, '似乎有不少矛盾', W / 2, 1260, 36, 'sans_med', INK2, ka * ke(t, qs('Q3', 1.4)) * (1 - ke(t, qs('Q5'), 0.5)), track=0.1)
        kb = ke(t, qs('Q5'))
        if kb > 0:
            text(img, 'β  =  Cov( rᵢ , rₘ )  ⁄  Var( rₘ )', W / 2, 1020, 40, 'ebg', INK2, ka * kb)
            fx.slam(img, '用 β（贝塔）衡量风险，', W / 2, 1140, 52, 'serif_black', t, qs('Q5'), ka, glow_=0.25)
            fx.slam(img, '是否自相矛盾？', W / 2, 1240, 52, 'serif_black', t, qs('Q5', 1.4), ka, gold=False, col=AMBER, glow_=0.3)
    # 定义
    ka = qa_env(t, 'define') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='巴菲特对风险的定义', en="buffett's definition of risk")
        k = ke(t, qs('A1', 0.6), 0.8)
        text(img, '受到伤害或损失', W / 2, 1035, 84, 'serif_black', a=ka * k, gold=True, glow=0.25, wipe=k)
        text(img, '的可能性', W / 2, 1135, 58, 'serif_bold', INK, ka * ke(t, qs('A1', 1.4)))
        text(img, 'the possibility of harm or injury', W / 2, 1200, 30, 'ebg_i', INK2, ka * ke(t, qs('A1', 1.8)))
        k2 = ke(t, qs('A2', 2.0), 0.7)
        if k2 > 0:
            line(img, (W / 2 - 300 * k2, 1262), (W / 2 + 300 * k2, 1262), ICE, ka * 0.6, 1)
            text(img, '与“打算持有多久”密不可分', W / 2, 1302, 40, 'sans_med', ICE, ka * k2, track=0.04)
    # 持有一天：上午 11:30 买入，收盘前卖出
    ka = qa_env(t, 'horizon') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='持有一天', en='held for a single day')
        x0, x1, yc = 190, 890, 1080
        k = eio((t - qs('A3')) / 9.0) if t < qs('A4') else 0.6 + 0.4 * eio((t - qs('A4')) / 1.5)
        rng = np.random.default_rng(3)
        n = int(60 * k)
        if n > 1:
            xs = np.linspace(x0, x1, 60)[:n]
            ys = yc + np.array([55 * math.sin(i * 0.9) * rng.uniform(0.3, 1.0) for i in range(60)])[:n]
            gline(img, np.c_[xs, ys], ICE, ka, th=3)
        text(img, '11:30 买入', x0, yc - 85, 34, 'inter_semi', INK, ka * ke(t, qs('A3', 1.5)), 'l')
        text(img, '收盘前卖出', x1, yc - 85, 34, 'sans_med', INK, ka * ke(t, qs('A4')), 'r')
        k3 = ke(t, qs('A6'))
        if k3 > 0:
            # 一半的概率赚、一半的概率亏
            bar(img, 430, 1290, 120, 110 * k3, GOLD_C, ka)
            bar(img, 650, 1290, 120, 110 * k3, AMBER, ka)
            text(img, '50%', 430, 1160, 40, 'corm_med', GOLD_C, ka * k3)
            text(img, '50%', 650, 1160, 40, 'corm_med', AMBER, ka * k3)
            text(img, '赚', 430, 1318, 26, 'sans_med', INK2, ka * k3); text(img, '亏', 650, 1318, 26, 'sans_med', INK2, ka * k3)
            fx.slam(img, '风险非常高', 870, 1230, 40, 'serif_black', t, qs('A5', 0.4), ka * k3, gold=False, col=AMBER, glow_=0.2)
    # 可口可乐：同一家公司，持有期不同，风险完全不同
    ka = qa_env(t, 'coke') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='同一只可口可乐', en='the same coca-cola')
        k1 = ke(t, qs('A8'), 0.7); k2 = ke(t, qs('A10'), 0.7)
        for (x, title, sub, val, col, k) in ((330, '以当初的买入价', '长期持有', '≈ 0', GOLD_C, k1), (750, '今天上午买', '明天上午卖', '很高', AMBER, k2)):
            if k <= 0: continue
            panel(img, x - 190, 970, x + 190, 1320, ka * k, col=col, fill=0.55)
            text(img, title, x, 1030, 36, 'serif_bold', INK, ka * k)
            text(img, sub, x, 1080, 32, 'sans_med', INK2, ka * k, track=0.1)
            text(img, '风险', x, 1160, 30, 'sans_med', INK2, ka * k, track=0.3)
            fx.slam(img, val, x, 1245, 84 if val == '≈ 0' else 72, 'serif_black', t, qs('A9' if col is GOLD_C else 'A11'), ka * k,
                    gold=col is GOLD_C, col=None if col is GOLD_C else AMBER, glow_=0.3)
    # 贝塔：学术界的定义
    ka = qa_env(t, 'beta') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='学术界 → 金融市场', en='academia → wall street')
        k0 = ke(t, qs('A12')); k1 = ke(t, qs('A14'), 0.7)
        text(img, '“我在年报里也指出过”', W / 2, 990, 34, 'sans', INK2, ka * k0 * (1 - k1), track=0.04)
        text(img, '风险 ＝ 波动', W / 2, 1070, 84, 'serif_black', INK, ka * max(k1, 0.35 * ke(t, qs('A13'))))
        text(img, '贝塔（β）：衡量价格过去的波动', W / 2, 1160, 34, 'sans', INK2, ka * k1, track=0.04)
        k2 = ke(t, qs('A15'), 0.4)
        if k2 > 0:
            ww = text_w('风险 ＝ 波动', 'serif_black', 84)
            line(img, (W / 2 - ww / 2 - 10, 1070), (W / 2 - ww / 2 - 10 + (ww + 20) * k2, 1070), AMBER, ka, 5)
            fx.slam(img, '对我们来说，根本不是风险的衡量', W / 2, 1270, 44, 'serif_black', t, qs('A15'), ka, glow_=0.3)
    # 荒谬：+20%~+80% 比稳定 5% “风险更高”？
    ka = qa_env(t, 'absurd') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='按传统风险度量', en='by the conventional measure')
        yb, sc_ = 1250, 2.0
        kA = ke(t, qs('A17'), 0.8); kB = ke(t, qs('A18'), 0.8)
        for (x0_, title_, sub_, col, k, vals) in ((165, '投资 A', '每年 +20% ～ +80%', ICE, kA, [62, 25, 78, 41, 20, 70, 33, 55]),
                                                 (585, '投资 B', '每年稳定 +5%', GOLD_C, kB, [5] * 8)):
            if k <= 0: continue
            text(img, title_, x0_ + 165, 975, 38, 'serif_bold', INK, ka * k)
            text(img, sub_, x0_ + 165, 1020, 26, 'sans_med', col, ka * k)
            line(img, (x0_, yb), (x0_ + 330, yb), INK2, ka * 0.6 * k, 1)
            for i, v in enumerate(vals):
                bar(img, x0_ + 25 + i * 40, yb, 26, v * sc_ * eo(k * 1.4 - i * 0.05), col, ka * k)
            text(img, '0%', x0_ - 10, yb, 20, 'inter', INK2, ka * k, 'r')
        k3 = ke(t, qs('A18', 1.6), 0.5) * (1 - ke(t, qs('A19'), 0.5)); k4 = ke(t, qs('A19'), 0.5)
        text(img, '“A 的风险更高”？', W / 2, 1305, 44, 'serif_black', AMBER, ka * k3)
        if k4 > 0:
            fx.slam(img, '乱了套 · HAYWIRE', W / 2, 1305, 48, 'serif_black', t, qs('A19'), ka, glow_=0.3)
        if qs('A19') < t < qs('A19') + 0.5:
            fx.glitch(img, (PX0, 1180, PX1, 1340), t, 0.7 * (1 - (t - qs('A19')) / 0.5), seed=4)
    # 期望：单笔可以亏，一组的期望不能为负
    ka = qa_env(t, 'expect') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='伯克希尔的做法', en="berkshire's approach")
        text(img, '单笔交易：可以亏', W / 2, 990, 44, 'serif_bold', INK, ka * ke(t, qs('A21')))
        rng = np.random.default_rng(9)
        outs = rng.normal(0.35, 1.0, 36)
        n = int(36 * eio((t - qs('A22')) / 3.0))
        for i in range(n):
            x = 190 + (i % 18) * 41; y = 1070 + (i // 18) * 48
            v = outs[i]
            circle(img, (x, y), 13, GOLD_C if v > 0 else AMBER, ka * 0.9, fill=True)
            glow(img, (x, y), 18, (GOLD_C if v > 0 else AMBER) * 0.5, ka * 0.3)
        k2 = ke(t, qs('A24'), 0.7)
        if k2 > 0:
            text(img, '一系列相互独立、类型相似的交易：', W / 2, 1210, 34, 'sans_med', INK2, ka * k2)
            fx.slam(img, '期望值必须为正', W / 2, 1290, 60, 'serif_black', t, qs('A25'), ka, glow_=0.4)
    # 芒格
    ka = qa_env(t, 'munger', post=0.8) * a * (1 - ke(t, T_DISGUST - 0.4, 0.3))
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='芒格的补充', en="munger's addendum")
        k1 = ke(t, qs('M1', 1.2), 0.7)
        fx.slam(img, '费马　·　帕斯卡', W / 2, 1035, 70, 'serif_black', t, qs('M1', 1.2), ka, glow_=0.3)
        text(img, 'FERMAT · PASCAL', W / 2, 1105, 26, 'corm', INK2, ka * k1, track=0.3)
        k2 = ke(t, qs('M2'), 0.6)
        text(img, '像从没听说过现代金融理论那样', W / 2, 1200, 42, 'serif_bold', INK, ka * k2)
        text(img, '用概率思考', W / 2, 1270, 42, 'serif_bold', ICE, ka * k2)


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
    """左上章节标签（与第一集一致）"""
    chapter_tag(img, t, '投资启示 · 本片解读', env(t, I['I1']['t0'] - 0.4, T_INS_END, 0.6, 0.6))


def ycap(img, s, a, y=1340, col=None):
    text(img, s, W / 2, y, 28, 'sans_med', INK2 if col is None else col, a, track=0.1, shadow=0.6)


# ---------------------------------------------------------------- I1：两种风险——上：价格剧烈波动（σ, β）；下：持有期结束时结果的分布，亏损的那一截（损失的可能性）
B_I1 = I['I1']['t0'] - 0.45
_r1 = np.random.default_rng(12)
I1_PATH = np.cumsum(_r1.normal(0, 1, 70))
OUT_X = np.linspace(-3, 3, 41)
OUT_P = np.exp(-(OUT_X - 0.9) ** 2 / 2.2)                 # 结果分布：大部分在本金之上，左尾是亏损


def dia_i1(L, t):
    a = sc(t, B_I1 if t > I['I1']['t0'] - 1 else 0, B_I2) * env(t, I['I1']['t0'] - 0.3, 1e9, 0.4, 0.1)
    if a <= 0: return
    kg = wt('I1', '受到伤害')
    shock(L, (W / 2, 1150), t, kg - 0.1, GOLD_H, a, rmax=460, life=1.1, flatten=0.35)


def txt_i1(img, t, subs):
    a = sc(t, B_I1 if t > I['I1']['t0'] - 1 else 0, B_I2) * env(t, I['I1']['t0'] - 0.3, 1e9, 0.4, 0.1)
    if a <= 0: return
    kc = ke(t, wt('I1', '教科书') - 0.3); kg = ke(t, wt('I1', '受到伤害') - 0.3)
    # 上：教科书——价格的波动
    panel(img, 90, 280, 990, 720, a * kc, col=ICE, title='教科书的风险', en='textbook: price volatility')
    if kc > 0:
        n = max(2, int(70 * eio((t - wt('I1', '教科书') + 0.2) / 1.4)))
        xs = np.linspace(150, 930, 70)[:n]
        ys = 520 - I1_PATH[:n] * 14 + 30 * np.sin(np.arange(n) * 1.3 + t * 3) * 0.6
        sd = 60
        area(img, np.c_[xs, ys - sd], 520 + 120, ICE, a * kc * 0.4, top=0.15)
        gline(img, np.c_[xs, ys], ICE, a * kc, th=3)
        dashed(img, (150, 520 - 110), (930, 520 - 110), ICE * 0.8, a * kc * 0.5); dashed(img, (150, 520 + 110), (930, 520 + 110), ICE * 0.8, a * kc * 0.5)
        fx.slam(img, '价格的波动 · σ , β', W / 2, 670, 46, 'serif_black', t, wt('I1', '波动') - 0.05, a * kc, gold=False, col=ICE, glow_=0.25)
    # 下：巴菲特——受到伤害或损失的可能性
    panel(img, 90, 780, 990, 1450, a * kg, col=GOLD_C, title='巴菲特的风险', en="buffett: possibility of loss")
    if kg > 0:
        x0, x1, yb = 150, 930, 1250
        k = eio((t - kg + 0.1) / 1.2)
        xs = x0 + (OUT_X + 3) / 6 * (x1 - x0)
        hs = OUT_P * 260 * k
        xz = x0 + (0 + 3) / 6 * (x1 - x0)                  # 本金线
        for x, h, v in zip(xs, hs, OUT_X):
            bar(img, x, yb, 15, h, AMBER if v < 0 else GOLD_C, a * kg)
        dashed(img, (xz, yb + 10), (xz, 940), INK, a * kg * 0.7)
        text(img, '当初的本金', xz - 14, 925, 24, 'sans_med', INK, a * kg * k, 'r', track=0.1)
        text(img, '持有期结束时的结果', W / 2, yb + 34, 22, 'sans', INK2, a * kg * k, track=0.1)
        fx.slam(img, '损失的可能性', 330, 1360, 56, 'serif_black', t, wt('I1', '可能性') - 0.05, a * kg, gold=False, col=AMBER, glow_=0.35)
        text(img, '← 这一截', 330, 1412, 24, 'sans_med', AMBER, a * kg * ke(t, wt('I1', '可能性')), track=0.1)
        text(img, '示意', 930, 1425, 18, 'sans', INK3 * 1.5, a * kg * 0.8, 'r')


# ---------------------------------------------------------------- I2：持有期结束时，拿回的钱能否保住当初的购买力
_r2 = np.random.default_rng(8)
I2_V = np.cumsum(_r2.normal(0.012, 0.09, 60)); I2_V -= I2_V[0]; I2_V[-1] = max(I2_V[-1], 0.55)


def txt_i2(img, t, subs):
    a = sc(t, B_I2, B_I3)
    if a <= 0: return
    text(img, '1993 · 致股东信', W / 2, 330, 30, 'sans_med', SUB_GOLD, a, track=0.3)
    panel(img, 90, 390, 990, 1080, a, col=ICE, title='持有期', en='the holding period')
    x0, x1, y0 = 160, 920, 820
    h = eio((t - wt('I2', '持有期') + 0.4) / (wt('I2', '购买力') - wt('I2', '持有期') + 0.4))
    n = max(2, int(60 * h))
    xs = np.linspace(x0, x1, 60)[:n]; ys = y0 - I2_V[:n] * 260
    dashed(img, (x0, y0), (x1 + 30, y0), GOLD_C, a * 0.8, th=2)
    text(img, '当初的购买力', x1 + 30, y0 + 30, 22, 'sans_med', GOLD_C, a * ke(t, wt('I2', '购买力') - 0.4), 'r', track=0.06)
    area(img, np.c_[xs, ys], y0, ICE, a, top=0.25)
    gline(img, np.c_[xs, ys], ICE, a, th=4)
    glow(img, (xs[-1], ys[-1]), 14, GOLD_HI, a)
    text(img, '买入', x0, y0 + 40, 28, 'sans_med', INK, a * ke(t, wt('I2', '持有期') - 0.4), track=0.2)
    kp = ke(t, wt('I2', '购买力') - 0.1)
    if kp > 0:
        ye = y0 - I2_V[-1] * 260
        line(img, (x1, ye), (x1, y0), GOLD_C, a * kp, 2)
        circle(img, (x1, ye), 22, GOLD_C, a * kp, 2)
        tick(img, (x1, ye), 20, GOLD_HI, a * kp)
        text(img, '持有期结束', x1, ye - 50, 28, 'sans_med', INK, a * kp, track=0.2)
        fx.burst(img, t, wt('I2', '购买力') - 0.1, (x1, ye), a, n=40, speed=360, life=1.1, seed=5)
    tp = wt('I2', '购买力')
    fx.slam(img, '拿回的钱  ≥  当初的购买力', W / 2, 1180, 56, 'serif_black', t, tp - 0.05, a, glow_=0.35)
    fx.typewriter(img, '“…at least as much purchasing power as he had to begin with…”', W / 2, 1265, 26, 'ebg_i', INK2, a, t, tp + 0.6, cps=40)
    text(img, '—— 巴菲特 1993 年致股东信', W / 2, 1315, 24, 'sans', INK2, a * ke(t, tp + 1.8), track=0.06)


# ---------------------------------------------------------------- I3：波动是幅度，风险是钱还在不在
def txt_i3(img, t, subs):
    a = sc(t, B_I3, B_WAPO)
    if a <= 0: return
    panel(img, 90, 300, 990, 760, a, col=ICE, title='波动', en='volatility')
    xs = np.linspace(160, 920, 120)
    ys = 560 + 120 * np.sin((xs - 160) / 760 * 4 * math.pi + t * 2.4)
    gline(img, np.c_[xs, ys], ICE, a, th=4)
    xm = 160 + 760 * ((0.125 - (t * 2.4) / (4 * math.pi)) % 0.25)
    xm = 540
    for yy, dd in ((440, -1), (680, 1)):
        dashed(img, (150, yy), (930, yy), INK2, a * 0.5)
    line(img, (965, 440), (965, 680), GOLD_C, a, 2)
    poly(img, [(955, 455), (965, 440), (975, 455)], GOLD_C, a, 2); poly(img, [(955, 665), (965, 680), (975, 665)], GOLD_C, a, 2)
    fx.slam(img, '价格摆动的幅度', W / 2, 720, 40, 'serif_black', t, I['I3']['t0'] + 0.2, a, gold=False, col=ICE, glow_=0.2)
    kg = ke(t, wt('I3', '风险') - 0.1)
    panel(img, 90, 820, 990, 1400, a * kg, col=GOLD_C, title='风险', en='risk')
    if kg > 0:
        # 本金：一根完整的金色柱——钱还在
        bar(img, 540, 1230, 260, 250 * eio((t - wt('I3', '风险') + 0.1) / 0.8), GOLD_C, a * kg)
        text(img, '本金', 540, 1262, 26, 'sans_med', INK2, a * kg, track=0.3)
        fx.slam(img, '钱还在不在', W / 2, 1335, 64, 'serif_black', t, wt('I3', '钱还在') - 0.05, a * kg, glow_=0.4)
        if t > wt('I3', '钱还在'): fx.sparks_up(img, t, 420, 660, 1230, a * ke(t, wt('I3', '钱还在')), n=40, seed=8)


# ---------------------------------------------------------------- 华盛顿邮报：持股市值 1973 → 1974（−25%）→ 1993（4.40 亿，约 41 倍）
def txt_wapo(img, t, subs):
    a = sc(t, B_WAPO, B_DEX)
    if a <= 0: return
    tb, td, tg, t6 = wt('I4', '一千零六十'), wt('I4', '八百万'), wt('I6', '超过'), I['I6']['t0']
    text(img, 'THE WASHINGTON POST · 华盛顿邮报', W / 2, 330, 26, 'sans_med', SUB_GOLD, a, track=0.2)
    panel(img, 90, 380, 990, 1180, a, col=GOLD_C, title='伯克希尔的持股市值', en="berkshire's stake, market value")
    yb, hmax = 1080, 560
    # 纵轴刻度随 1993 年的柱子出现而重新缩放：前两根柱子被压成细条
    rs = eio((t - tg + 0.1) / 1.4)
    vmax = lerp(12.0, 470.0, rs)
    def hv(v): return min(v / vmax * hmax, hmax)               # 纵轴还没缩放完时，柱子不超出面板
    xs = (300, 540, 780)
    k1 = ke(t, tb - 0.1, 0.6); k2 = ke(t, td - 0.1, 0.6); k3 = rs
    line(img, (140, yb), (940, yb), INK2, a * 0.6, 1)
    bar(img, xs[0], yb, 150, hv(10.6) * k1, GOLD_C, a * (k1 > 0))
    bar(img, xs[1], yb, 150, hv(8.0) * k2, AMBER, a * (k2 > 0))
    bar(img, xs[2], yb, 150, hv(440.0) * k3, GOLD_C, a * (k3 > 0))
    for x, yr, lab, v, k, col in ((xs[0], '1973', '买入成本', '1,060 万', k1, GOLD_C), (xs[1], '1974 年底', '市值', '800 万', k2, AMBER),
                                   (xs[2], '1993', '市值', '4.40 亿', k3, GOLD_HI)):
        if k <= 0: continue
        text(img, yr, x, yb + 36, 26, 'corm_med', INK, a * k)
        text(img, lab, x, yb + 68, 20, 'sans', INK2, a * k)
        vy = yb - hv({'1973': 10.6, '1974 年底': 8.0, '1993': 440.0}[yr]) * k - 34
        text(img, v, x, max(vy, 470), 36 if x != xs[2] else 46, 'corm_med', col, a * k, glow=0.15)
    if k2 > 0 and t < tg:
        fx.slam(img, '−25%', xs[1] + 140, yb - hv(8.0) - 70, 54, 'corm_med', t, td + 0.3, a, gold=False, col=AMBER, glow_=0.3)
        if td - 0.1 < t < td + 0.5: fx.glitch(img, (xs[1] - 100, yb - 260, xs[1] + 100, yb), t, 0.8, seed=3)
    k5 = env(t, I['I5']['t0'] - 0.1, t6 - 0.1, 0.3, 0.4)
    if k5 > 0:
        panel(img, 200, 1230, 880, 1340, a * k5, col=AMBER, fill=0.8)
        fx.slam(img, '按贝塔理论：价格更低 → “更危险”', W / 2, 1285, 40, 'serif_black', t, I['I5']['t0'] - 0.05, a * k5, gold=False, col=AMBER, glow_=0.2)
    k6 = env(t, t6 - 0.1, 1e9, 0.4, 0.3)
    if k6 > 0:
        fx.slam(img, '生意一直在增长', W / 2, 1270, 66, 'serif_black', t, t6 - 0.05, a * k6, glow_=0.35)
    if k3 > 0:
        fx.slam(img, '≈ 41 倍', W / 2, 1380, 72, 'corm_med', t, tg + 1.3, a, glow_=0.4)
        fx.sparks_up(img, t, xs[2] - 70, xs[2] + 70, yb, a * ke(t, tg + 0.8), n=45, seed=6)
        fx.burst(img, t, tg + 1.3, (W / 2, 1380), a * 0.8, n=50, speed=420, life=1.1, seed=7)


def dia_wapo(L, t):
    a = sc(t, B_WAPO, B_DEX)
    if a <= 0: return
    shock(L, (W / 2, 760), t, B_WAPO + 0.4, GOLD_H, a, rmax=700, life=1.3, flatten=0.5)
    tg = wt('I6', '超过')
    if t > tg - 0.1: beam(L, 780, 1080, 430, GOLD_H, 0.45 * a * ke(t, tg + 0.6), wd=40)


# ---------------------------------------------------------------- 德克斯特：两笔账——买来的生意（价值归零）与付出的代价（那 2.5 万股后来值 57 亿）
def txt_dex(img, t, subs):
    a = sc(t, B_DEX, B_LEV)
    if a <= 0: return
    ts, tz = wt('I9', '海外'), wt('I9', '价值归零') - 0.1
    tc, t57, tb = I['I10']['t0'], wt('I10', '五十七'), wt('I8', '贝塔')
    text(img, 'DEXTER SHOE · 德克斯特鞋业 · 1993', W / 2, 330, 26, 'sans_med', SUB_GOLD, a, track=0.2)
    panel(img, 90, 380, 990, 1180, a, col=GOLD_C, title='两笔账', en='two ledgers')
    yb, hmax = 1060, 520
    rs = eio((t - t57 + 0.1) / 1.4)
    vmax = lerp(5.0, 60.0, rs)
    def hv(v): return min(v / vmax * hmax, hmax)
    x1, x2 = 330, 750
    line(img, (140, yb), (940, yb), INK2, a * 0.6, 1)
    # 左：买来的生意
    k1 = ke(t, wt('I7', '一九九三') - 0.1, 0.9)
    text(img, '买来的生意', x1, yb + 40, 30, 'serif_black', INK, a * k1)
    text(img, '德克斯特鞋业', x1, yb + 80, 22, 'sans', INK2, a * k1)
    gone = eio((t - tz) / 0.2)
    if k1 > 0 and gone < 1:
        bar(img, x1, yb, 190, hv(4.33) * k1, GOLD_C, a * (1 - gone))
        crack = env(t, ts, tz + 0.1, 0.3, 0.1)
        if crack > 0: fx.glitch(img, (x1 - 110, yb - hv(4.33) - 10, x1 + 110, yb), t, 0.35 * crack, seed=2)
        text(img, '4.33 亿美元', x1, yb - hv(4.33) * k1 - 40, 42, 'corm_med', GOLD_HI, a * ke(t, wt('I7', '四亿') - 0.1), glow=0.15)
    if t >= tz:
        fx.shards(img, t, tz, (x1 - 95, yb - hv(4.33), x1 + 95, yb), GOLD_C, a, n=32, seed=5)
        rrect(img, x1 - 95, yb - hv(4.33), x1 + 95, yb, 6, AMBER, a * 0.6 * ke(t, tz + 0.8), 2)
        fx.slam(img, '价值归零', x1, yb - hv(4.33) - 50, 52, 'serif_black', t, tz, a, gold=False, col=AMBER, glow_=0.4)
    # 没有股价 → 没有波动 → 按贝塔理论“风险为零”
    k8 = env(t, wt('I8', '波动') - 0.2, ts, 0.4, 0.4)
    if k8 > 0:
        gline(img, [(560, 640), (920, 640)], ICE, a * k8, th=3)
        text(img, '没有股价 · 波动 ＝ 0', 740, 590, 32, 'serif_black', ICE, a * k8)
        if t > tb - 0.1:
            fx.slam(img, '按贝塔理论：风险 ＝ 0', 740, 720, 36, 'serif_black', t, tb - 0.05, a * k8, gold=False, col=ICE, glow_=0.25)
    # 右：付出的代价——当初付出的 25,203 股伯克希尔股票
    kc = ke(t, tc - 0.1, 0.7)
    if kc > 0:
        text(img, '付出的代价', x2, yb + 40, 30, 'serif_black', AMBER, a * kc)
        text(img, '25,203 股伯克希尔股票', x2, yb + 80, 22, 'sans', INK2, a * kc)
        h0 = hv(4.33) * kc
        h1 = hv(57.0) * eio((t - t57 + 0.1) / 1.4)
        bar(img, x2, yb, 190, max(h0, h1), AMBER, a)
        v = 4.33 + (57 - 4.33) * eio((t - t57) / 1.4) if t > t57 else 4.33
        lab = '4.33 亿美元' if t <= t57 else (f'{v:.1f} 亿美元' if v < 56.9 else '57 亿美元')
        text(img, lab, x2, max(yb - max(h0, h1) - 40, 470), 46 if v > 5 else 40, 'corm_med', AMBER, a * kc, glow=0.2)
        if t > t57: text(img, '2014 年的价值', x2, max(yb - max(h0, h1) - 88, 430), 22, 'sans', INK2, a * ke(t, t57 + 0.6))
        fx.slam(img, '更痛的是代价', W / 2, 1270, 64, 'serif_black', t, tc - 0.05, a * (1 - ke(t, I['I10b']['t0'] - 0.3, 0.4)), gold=False, col=AMBER, glow_=0.35)
    else:
        k9 = env(t, ts - 0.1, tc - 0.2, 0.4, 0.3)
        fx.slam(img, '海外竞争 · 优势荡然无存', W / 2, 1270, 52, 'serif_black', t, ts - 0.05, a * k9, gold=False, col=INK, glow_=0.2)
    # 收束：没有波动，不等于没有风险
    tq = I['I10b']['t0']
    if t > tq - 0.1:
        fx.slam(img, '没有波动  ≠  没有风险', W / 2, 1290, 76, 'serif_black', t, tq - 0.05, a, glow_=0.45)
        text(img, '“To date, Dexter is the worst deal that I’ve made.”  —— 巴菲特 2007 年致股东信', W / 2, 1385, 22, 'ebg_i', INK2,
             a * ke(t, tq + 0.8))


def dia_dex(L, t):
    a = sc(t, B_DEX, B_LEV)
    if a <= 0: return
    tz, t57 = wt('I9', '价值归零') - 0.1, wt('I10', '五十七')
    shock(L, (330, 880), t, tz, AMBER, a, rmax=640, life=1.3, flatten=0.6)
    if tz <= t < tz + 2.5:                                     # 碎屑：一团金色粒子朝四周飞散
        dt = t - tz
        rng = np.random.default_rng(17)
        n = 500
        ang = rng.uniform(0, 2 * math.pi, n); sp = rng.uniform(150, 900, n)
        x = 330 + np.cos(ang) * sp * dt; y = 880 + np.sin(ang) * sp * dt * 0.8 + 500 * dt * dt
        xp = 330 + np.cos(ang) * sp * (dt - 0.05); yp = 880 + np.sin(ang) * sp * (dt - 0.05) * 0.8 + 500 * (dt - 0.05) ** 2
        f = (1 - dt / 2.5) ** 1.5
        cloud(L, np.c_[x, y], GOLD_H, 0.9 * a * f)
        cloud(L, np.c_[(x + xp) / 2, (y + yp) / 2], GOLD_H, 0.5 * a * f)
    if t > t57 - 0.1: beam(L, 750, 1060, 450, AMBER, 0.35 * a * ke(t, t57 + 0.6), wd=40)
    tq = I['I10b']['t0']
    shock(L, (W / 2, 1290), t, tq - 0.05, GOLD_H, a, rmax=560, life=1.0, flatten=0.25)


# ---------------------------------------------------------------- 杠杆：同一段下跌，有没有借钱、会不会被迫卖出，结局完全不同（示意）
_LV = np.r_[np.linspace(0, -0.42, 18) + 0.03 * np.sin(np.arange(18) * 1.7), np.linspace(-0.42, 0.25, 26) + 0.03 * np.sin(np.arange(26) * 1.3)]


def txt_lev(img, t, subs):
    a = sc(t, B_LEV, B_TODAY)
    if a <= 0: return
    tp, tc, tm = wt('I11', '低点卖出'), wt('I11', '暂时'), wt('I11', '永久')
    text(img, 'LEVERAGE · 杠杆与被迫卖出', W / 2, 330, 26, 'sans_med', SUB_GOLD, a, track=0.2)
    panel(img, 90, 380, 990, 1180, a, col=ICE, title='同一段下跌', en='the same decline')
    x0, x1, y0 = 150, 930, 640
    n_all = len(_LV)
    k = eio((t - B_LEV - 0.6) / (tc + 1.2 - B_LEV - 0.6))
    n = max(2, int(n_all * k))
    xs = np.linspace(x0, x1, n_all); ys = y0 - _LV * 520
    dashed(img, (x0, y0), (x1, y0), INK2, a * 0.5)
    text(img, '买入价', x0, y0 - 22, 20, 'sans', INK2, a * 0.8, 'l')
    gline(img, np.c_[xs[:n], ys[:n]], ICE, a, th=4)
    it = 17                                                     # 浪谷
    if n > it:
        circle(img, (xs[it], ys[it]), 10, AMBER, a, 2)
    kb = ke(t, wt('I11', '借了钱') - 0.1)
    if kb > 0:
        text(img, '借了钱', 250, 800, 30, 'serif_black', AMBER, a * kb)
    kp = ke(t, tp - 0.1)
    if kp > 0:
        cross(img, (xs[it], ys[it]), 18, AMBER, a * kp)
        fx.slam(img, '被迫在低点卖出', xs[it] - 20, ys[it] + 70, 40, 'serif_black', t, tp - 0.05, a, gold=False, col=AMBER, glow_=0.3)
        if tp < t < tp + 0.5: fx.glitch(img, (x0, 420, x1, 1170), t, 0.7 * (1 - (t - tp) / 0.5), seed=9)
    kl = ke(t, tm - 0.2, 0.8)
    if kl > 0:                                                  # 被锁定的亏损：价格涨回去了，账户停在了谷底
        xe = xs[it] + (x1 - xs[it]) * kl
        gline(img, [(xs[it], ys[it]), (xe, ys[it])], AMBER, a, th=4)
        area(img, [(xs[it], y0), (xe, y0)], ys[it], AMBER, a * 0.8, top=0.25)
        text(img, '永久的损失', (xs[it] + x1) / 2 + 60, ys[it] + 44, 30, 'serif_black', AMBER, a * kl)
    kc = ke(t, tc - 0.1)
    if kc > 0:
        text(img, '价格涨了回去', xs[-1] - 10, ys[-1] - 40, 26, 'sans_med', ICE, a * kc, 'r')
    text(img, '示意', 930, 1155, 18, 'sans', INK3 * 1.5, a * 0.8, 'r')
    fx.slam(img, '暂时的下跌', W / 2, 1260, 56, 'serif_black', t, tc - 0.05, a, gold=False, col=ICE, glow_=0.25)
    if t > wt('I11', '锁定') - 0.1:
        text(img, '↓  被锁定成', W / 2, 1320, 24, 'sans_med', INK2, a * ke(t, wt('I11', '锁定') - 0.1), track=0.2)
    fx.slam(img, '永久的损失', W / 2, 1390, 80, 'serif_black', t, tm - 0.05, a, gold=False, col=AMBER, glow_=0.45)


def dia_lev(L, t):
    a = sc(t, B_LEV, B_TODAY)
    if a <= 0: return
    tp = wt('I11', '低点卖出')
    xs = np.linspace(150, 930, len(_LV)); ys = 640 - _LV * 520
    shock(L, (xs[17], ys[17]), t, tp, AMBER, a, rmax=380, life=1.0, flatten=0.5)


# ---------------------------------------------------------------- 今天：账户大幅回撤时，先问两个问题
def txt_today(img, t, subs):
    a = sc(t, B_TODAY, B_CLOSE)
    if a <= 0: return
    text(img, 'TODAY · 账户大幅回撤时', W / 2, 330, 26, 'sans_med', SUB_GOLD, a, track=0.2)
    panel(img, 90, 380, 990, 760, a, col=ICE, title='账户回撤', en='drawdown')
    xs = np.linspace(150, 930, 40)
    ys = 520 + 190 * np.clip(np.linspace(0, 1.5, 40), 0, 1) ** 0.75 + 10 * np.sin(np.arange(40) * 1.9)
    k = eio((t - B_TODAY - 0.2) / 1.6)
    n = max(2, int(40 * k))
    area(img, np.c_[xs[:n], ys[:n]], 740, AMBER, a * 0.6, top=0.18)
    gline(img, np.c_[xs[:n], ys[:n]], ICE, a, th=4)
    fx.slam(img, '−35%', 850, 560, 60, 'corm_med', t, B_TODAY + 1.6, a, gold=False, col=AMBER, glow_=0.3)
    text(img, '示意', 930, 740, 18, 'sans', INK3 * 1.5, a * 0.8, 'r')
    text(img, '先问两个问题', W / 2, 840, 36, 'sans_med', INK2, a * ke(t, wt('I12', '两个')), track=0.2)
    for i, (kw, s_, y) in enumerate((('这门生意', '这门生意还在吗？', 1000), ('我会', '我会被迫卖出吗？', 1210))):
        kk = ke(t, wt('I12', kw) - 0.1, 0.4)
        if kk <= 0: continue
        panel(img, 110, y - 85, 970, y + 85, a * kk, col=GOLD_C, fill=0.6)
        text(img, f'0{i + 1}', 175, y, 44, 'corm_med', SUB_GOLD, a * kk)
        fx.slam(img, s_, W / 2 + 40, y, 66, 'serif_black', t, wt('I12', kw) - 0.05, a, glow_=0.4)
    text(img, 'Drawdown  ≠  Permanent loss', W / 2, 1360, 34, 'ebg', INK2, a * ke(t, wt('I12', '我会') + 1.0))


def dia_today(L, t):
    a = sc(t, B_TODAY, B_CLOSE)
    if a <= 0: return
    for kw, y in (('这门生意', 1000), ('我会', 1210)):
        shock(L, (W / 2, y), t, wt('I12', kw) - 0.05, GOLD_H, a, rmax=520, life=0.9, flatten=0.22)


def dia_none(L, t):
    return


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





# ---------------------------------------------------------------- 芒格金句卡：“很多现代金融理论，只能用‘令人作呕’来形容”（停留 2 秒以上，便于截图传播）
_lseg = QA['segs'][-1]
T_DISGUST = _lseg['t0'] + 301.12 - _lseg['src_in']          # 原声里 “disgusting” 的起点（逐词识别时间，相对 CLIP_IN）


def munger_a(t):
    return env(t, T_DISGUST - 0.25, T_INS - 0.1, 0.25, 0.35)


def txt_munger(img, t, subs):
    a = munger_a(t)
    if a <= 0: return
    panel(img, 80, 830, 1000, 1390, a, col=GOLD_C, title='芒格 · 1994', en='charlie munger', fill=0.9)
    fx.slam(img, '很多现代金融理论，', W / 2, 1000, 64, 'serif_black', t, T_DISGUST - 0.25, a, glow_=0.3)
    fx.slam(img, '只能用“令人作呕”来形容。', W / 2, 1100, 64, 'serif_black', t, T_DISGUST, a, glow_=0.4)
    k = ke(t, T_DISGUST + 0.5, 0.6)
    text(img, '“A lot of modern finance theory can only be described as disgusting.”', W / 2, 1200, 30, 'ebg_i', INK, a * k, shadow=0.6)
    text(img, '—— 查理·芒格，1994 年伯克希尔股东大会', W / 2, 1265, 24, 'sans', INK2, a * k, track=0.06)
    text(img, '（现场笑声）', W / 2, 1330, 24, 'sans', INK2, a * env(t, TL['laugh']['t0'], TL['laugh']['t1'], 0.15, 0.2), track=0.1)


def dia_munger(L, t):
    a = munger_a(t)
    if a <= 0: return
    shock(L, (W / 2, 1100), t, T_DISGUST, GOLD_H, a, rmax=560, life=1.1, flatten=0.3)


# ---------------------------------------------------------------- 片尾互动问题（在品牌片尾之前）
def txt_endq(img, t, subs):
    a = env(t, ENDQ_T['t0'] - 0.3, END['t_particles'] + 0.2, 0.4, 0.5)
    if a <= 0: return
    panel(img, 90, 1220, 990, 1470, a, col=GOLD_C, fill=0.85)
    fx.slam(img, '你持仓里跌得最惨的那一只，', W / 2, 1290, 44, 'serif_bold', t, ENDQ_T['t0'] - 0.05, a, gold=False, col=INK, glow_=0.15)
    fx.slam(img, '现在回头看——是波动，还是永久损失？', W / 2, 1365, 44, 'serif_black', t, ENDQ_T['t0'] + 1.4, a, glow_=0.3)
    text(img, '在评论区说说你的答案', W / 2, 1430, 24, 'sans', INK2, a * ke(t, ENDQ_T['t0'] + 3.0), track=0.2)


# ================================================================ 合成一帧
DIAS = [dia_cold, dia_title, dia_s1, dia_s2, dia_s3, dia_ctx, dia_qa, dia_munger, dia_i1, dia_wapo, dia_dex, dia_lev, dia_today, dia_close, dia_sum]
TXTS = [txt_cold, txt_title, txt_s1, txt_s2, txt_s3, txt_ctx, txt_qa, txt_munger, txt_card, txt_i1, txt_i2, txt_i3, txt_wapo, txt_dex, txt_lev,
        txt_today, txt_close, txt_sum, txt_endq]


def frame(t, subs=True):
    L = np.zeros((H, W, 3), np.float32)
    for d in DIAS: d(L, t)
    img = finish(L, t)
    ins_bg(img, t)
    for tx in TXTS: tx(img, t, subs)
    ins_tag(img, t)
    chapter_tag(img, t, '开场 · 一个问题', env(t, V('S2')['t0'] - 0.5, T_CTX - 0.3, 0.6, 0.6))
    if subs:
        narr_sub(img, t, INTRO['subs'])
        narr_sub(img, t, INS['subs'], hide=('I13',))
    s_end(img, t)
    # 后期（与第一集一致）：泛光、横向光晕；有配乐的段落在重拍上推镜 / 闪光 / 色散，小节强拍轻微脉动（原声问答段减弱）
    img = fx.post(img, t, HITS, BARS, strength=0.6 if T_Q + 1 < t < T_QE else 1.0)
    img = img * vignette() + GRAIN[int(t * FPS) % len(GRAIN)]
    fade_all = 1 - eio((t - END['t_fade0']) / (END['t_fade1'] - END['t_fade0']))
    HUD.draw(img, t, alpha=float(fade_all))                     # 角标从第 0 帧起就在
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
