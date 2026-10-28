"""《伯克希尔股东大会投资智慧录》第三集 · 巴菲特：最怕的不是熊市 —— 逐帧渲染（1080×1920，30fps）。

画面风格：与第二集相同，以“暗夜星图编年”为底（近乎纯黑的宇宙、发光的点与细线），
叠加与第一集一致的系列语言：片头用 1994 年大会原始录像 + 金色系列片名，“投资启示”标题转场、砸入 / 爆开 / HUD 圆环 / 光柱火花 / 故障，
以及泛光、横向光晕、重拍推镜 + 闪光 + 色散的电影后期。解读段每个论点一张直观的数据图（真实数据，示意图另行标注），收尾是星图穿梭。
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
from script import BROLL, CLIP_LEN, QUOTE_ID, CAPE, NQBK, BRK_TABLE

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


I = {k: V(k) for k in ('I1', 'I2', 'I3', 'I7', 'I7B', 'I8', 'I10', 'I11')}
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


def stage(t, b_in, b_out, delay=0.0, up=0.6):
    u = 1.0 if b_in <= 0 else eio((t - (b_in + 0.4 + delay)) / up)
    return u * (1 - eio((t - (b_out - 0.85)) / 0.85))


def A3(t, b_in, b_out):
    """图解 / 排印卡 / 读数 三段错开"""
    return stage(t, b_in, b_out), stage(t, b_in, b_out, 0.5), stage(t, b_in, b_out, 1.0)


# ================================================================ 面板与图表（不用玻璃：深色实底 + 细边 + 发光的角标折线）
PANEL_BG = C(8, 10, 17)


def chapter_tag(img, t, title, a=1.0):
    """左上章节标签（与第一集一致）"""
    if a <= 0.003: return
    text(img, '第三集 · 最怕的不是熊市', 72, 66, 26, 'sans_med', SUB_GOLD, a * 0.95, 'l', track=0.12, shadow=0.3)
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
    # 录像四周：一层随原声能量跳动的冰青粒子
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
    foot(img, QA_CLIP, min(max(src, 0.0), CLIP_LEN - 1.0), W / 2, 760, a, zoom=z, pan=(0.03, -0.02), blur=0.55)
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
        hw = text_w('第三集 · 最怕的不是熊市', 'sans_med', 38, 0.14) / 2 + 40
        rrect(img, W / 2 - hw, 1196, W / 2 + hw, 1268, 6, SUB_GOLD, ea * 0.55, 1)
        text(img, '第三集 · 最怕的不是熊市', W / 2, 1232, 38, 'sans_med', INK, ea, track=0.14)
    fx.burst(img, t, T_TITLE, (W / 2, 900), a * 0.8, n=70, speed=640, life=1.4, seed=2)


# ================================================================ 开场钩子（第 0 秒）+ 开场口播：上方是 1994 年大会影像，下方是图表面板
FOOT_Y = 540


def intro_a(t):
    return env(t, V('S2')['t0'] - 0.4, T_CTX - 0.3, 0.5, 0.6)


def hook_a(t):
    return 1.0 - eio((t - (T_TITLE - 0.45)) / 0.4)


# 钩子：市场低迷、账户缩水——还要不要继续买？（先共情，再给视角；第 0 帧即可读，克制，不做故障与砸入）
_rh = np.random.default_rng(31)
HOOK_ACC = np.r_[np.linspace(0, 0.06, 8), np.linspace(0.06, -0.34, 34), np.linspace(-0.34, -0.30, 8)] + _rh.normal(0, 0.012, 50)
HOOK_BOX = (110, 660, 970, 1140)


def dia_s1(L, t):
    a = hook_a(t)
    if a <= 0: return
    ta = wt('S1', '巴菲特')
    shock(L, (W / 2, 1290), t, ta - 0.05, GOLD_H, a * 0.7, rmax=520, life=1.3, flatten=0.3)
    rng = np.random.default_rng(4)                       # 缓缓上升的金色微粒
    ph = (t * 0.10 + rng.random(160)) % 1.0
    cloud(L, np.c_[rng.uniform(60, W - 60, 160), 1500 - ph * 1200], GOLD_H, 0.3 * a, w=np.sin(ph * math.pi))


def txt_s1(img, t, subs):
    a = intro_a(t)
    if a > 0:
        clip = CLIPS[5200] if t < V('S3')['t0'] - 0.2 else CLIPS[700]
        ct = (t - V('S2')['t0'] + 1.0) % 15.5
        foot(img, clip, ct, W / 2, FOOT_Y, a, zoom=1.05 + 0.006 * ct, blur=0.5)
        text(img, '1994 · 奥马哈 · 伯克希尔股东大会上午场实况', 72, FOOT_Y - WIN_H / 2 - 30, 22, 'sans', INK2, a * 0.85, 'l', track=0.06, shadow=0.5)
    ap = hook_a(t)
    if ap <= 0: return
    zs = 1.0 + 0.04 * (1 - eo(t / 0.6))
    tq = wt('S1', '还要不要')
    text(img, '市场低迷，账户缩水——', W / 2, 400, int(46 * zs), 'sans_med', INK2, ap, track=0.12, shadow=0.6)
    text(img, '还要不要继续买？', W / 2, 530, int(92 * zs), 'serif_black', a=ap, gold=True,
         glow=0.2 + 0.3 * math.exp(-max(t - tq, 0) / 0.8) * (t > tq), shadow=0.7)
    # 账户曲线：缓慢下滑，末端一个呼吸的光点（示意）
    x0, y0, x1, y1 = HOOK_BOX
    panel(img, x0, y0, x1, y1, ap, col=ICE, title='你的账户', en='your portfolio', fill=0.78)
    k = 0.45 + 0.55 * eio((t - 0.1) / max(tq - 0.1, 1.0))
    n = max(2, int(len(HOOK_ACC) * k))
    xs = np.linspace(x0 + 50, x1 - 50, len(HOOK_ACC))[:n]
    yb, yt = y1 - 70, y0 + 140
    ys = yt + (HOOK_ACC.max() - HOOK_ACC[:n]) / (HOOK_ACC.max() - HOOK_ACC.min()) * (yb - yt)
    dashed(img, (x0 + 40, yt + (HOOK_ACC.max() - 0) / (HOOK_ACC.max() - HOOK_ACC.min()) * (yb - yt)), (x1 - 40, yt + (HOOK_ACC.max() - 0) / (HOOK_ACC.max() - HOOK_ACC.min()) * (yb - yt)),
           INK2, ap * 0.45)
    text(img, '买入成本', x0 + 50, yt + HOOK_ACC.max() / (HOOK_ACC.max() - HOOK_ACC.min()) * (yb - yt) - 22, 20, 'sans', INK2, ap * 0.8, 'l')
    area(img, np.c_[xs, ys], yb, ICE, ap * 0.6, top=0.2)
    gline(img, np.c_[xs, ys], ICE, ap, th=4)
    pulse = 0.6 + 0.4 * math.sin(t * 3.2)
    glow(img, (xs[-1], ys[-1]), 22 * pulse + 8, AMBER, ap * 0.7)
    circle(img, (xs[-1], ys[-1]), 7, GOLD_HI, ap, fill=True)
    text(img, '示意', x1 - 10, y1 - 16, 18, 'sans', INK3 * 1.5, ap * 0.8, 'r')
    ta = wt('S1', '巴菲特')
    kb = ke(t, ta - 0.15, 0.6)
    if kb > 0:
        panel(img, 110, 1210, 970, 1380, ap * kb, col=GOLD_C, fill=0.8)
        text(img, '巴菲特看待下跌的方式——', W / 2, 1255, 32, 'sans_med', INK2, ap * kb, track=0.12)
        kc = ke(t, wt('S1', '换个角度') - 0.2, 0.7)
        text(img, '也许能帮你换个角度', W / 2, 1325, 56, 'serif_black', a=ap * kc, gold=True, glow=0.25, wipe=kc)


# ---------------------------------------------------------------- S2：1994 年春天，美联储两个半月里三次加息，债市重挫
FED = [(0.0, 3.00), (34.0, 3.25), (80.0, 3.50), (107.0, 3.75)]          # 1994 年内第几天 → 联邦基金目标利率（%）
GS10 = [(15.0, 5.75), (45.0, 5.97), (74.0, 6.48), (105.0, 6.97)]          # 月均十年期美债收益率（%），点在月中
MEET_D = 114.0                                                          # 4 月 25 日


def s2_a(t): return env(t, V('S2')['t0'] - 0.1, V('S3')['t0'] - 0.2, 0.35, 0.35)


def s2_x(d): return 190 + d / 120.0 * 700


def dia_s2(L, t):
    a = s2_a(t)
    if a <= 0: return
    shock(L, (W / 2, 1405), t, wt('S2', '重挫') - 0.05, AMBER, a, rmax=420, life=1.0, flatten=0.35)


def txt_s2(img, t, subs):
    a = s2_a(t)
    if a <= 0: return
    panel(img, 110, 800, 970, 1340, a, col=ICE, title='1994 年初', en='federal reserve · bond market')
    t0 = V('S2')['t0']; tj = wt('S2', '三次'); tz = wt('S2', '重挫')
    # 上：十年期美债收益率（琥珀），1 月 5.75% → 4 月 6.97%
    y_hi = lambda v: 1080 - (v - 5.5) / 1.7 * 150
    kb = eio((t - tj - 0.3) / 1.6)
    pts = [(s2_x(d), y_hi(v)) for d, v in GS10]
    n = 1 + kb * (len(pts) - 1)
    Q = pts[:int(n)] + ([tuple(np.array(pts[int(n) - 1]) + (np.array(pts[min(int(n), 3)]) - np.array(pts[int(n) - 1])) * (n - int(n)))] if n < 4 else [])
    text(img, '十年期美债收益率', 190, 930, 24, 'sans_med', AMBER, a, 'l', track=0.06)
    if len(Q) >= 2:
        gline(img, Q, AMBER, a, th=3)
    for i, (d, v) in enumerate(GS10):
        if i <= n - 1 + 1e-6 and i in (0, 3):
            glow(img, (s2_x(d), y_hi(v)), 10, AMBER, a)
            text(img, f'{v:.2f}%', s2_x(d) + (18 if i == 0 else -22), y_hi(v) + (30 if i == 0 else 0), 30, 'corm_med', AMBER, a, 'l' if i == 0 else 'r')
    # 下：联邦基金目标利率（冰青阶梯）
    y_lo = lambda v: 1290 - (v - 2.9) / 1.0 * 150
    text(img, '联邦基金目标利率', 190, 1140, 24, 'sans_med', ICE, a, 'l', track=0.06)
    steps = []
    for i, (d, v) in enumerate(FED):
        ti = t0 + 0.3 + i * (tj + 0.6 - t0) / 3 if i else t0
        if t < ti: break
        d1 = FED[i + 1][0] if i + 1 < len(FED) else MEET_D
        if i + 1 < len(FED):
            ti1 = t0 + 0.3 + (i + 1) * (tj + 0.6 - t0) / 3
            d1 = d + (d1 - d) * eio((t - ti) / max(ti1 - ti, 0.1))
        else:
            d1 = d + (MEET_D - d) * eio((t - ti) / 0.8)
        if steps: steps.append((s2_x(d), steps[-1][1]))
        steps += [(s2_x(d), y_lo(v)), (s2_x(d1), y_lo(v))]
        if i:
            fx.slam(img, '+0.25', s2_x(d) + 6, y_lo(v) - 28, 24, 'inter_semi', t, ti, a, gold=False, col=ICE, glow_=0.2)
    if len(steps) >= 2: gline(img, steps, ICE, a, th=3)
    for d, lab in ((0.0, '1 月'), (31.0, '2 月'), (59.0, '3 月'), (90.0, '4 月')):
        text(img, lab, s2_x(d) + 6, 1318, 18, 'sans', INK3 * 1.6, a, 'l')
    km = ke(t, tj + 0.8)
    dashed(img, (s2_x(MEET_D), 930), (s2_x(MEET_D), 1300), GOLD_C, a * km * 0.8)
    text(img, '4 月 25 日', s2_x(MEET_D) + 4, 1318, 18, 'sans_med', GOLD_C, a * km, 'l')
    text(img, '股东大会', s2_x(MEET_D) + 4, 1295, 18, 'sans_med', GOLD_C, a * km, 'l')
    fx.slam(img, '债市重挫', W / 2, 1405, 84, 'serif_black', t, tz - 0.05, a, gold=False, col=AMBER, glow_=0.45)
    if tz - 0.05 < t < tz + 0.45: fx.glitch(img, (110, 900, 970, 1100), t, 0.7 * (1 - (t - tz + 0.05) / 0.5), seed=6)


# ---------------------------------------------------------------- S3：年份落到 1994 + 股东的提问
def s3_a(t): return env(t, V('S3')['t0'] - 0.2, T_CTX - 0.3, 0.4, 0.6)


def dia_s3(L, t):
    a = s3_a(t)
    if a <= 0: return
    tq = wt('S3', '看涨')
    shock(L, (W / 2, 1230), t, tq - 0.05, GOLD_H, a, rmax=560, life=1.2, flatten=0.3)


def txt_s3(img, t, subs):
    a = s3_a(t)
    if a <= 0: return
    year_rewind(img, t, wt('S3', '那年') - 0.3, W / 2, 960, a, y_from=2026, y_to=1994, size=170)
    tq, tb = wt('S3', '看涨'), wt('S3', '看跌')
    fx.slam(img, '“你们看涨，', W / 2, 1180, 72, 'serif_black', t, tq - 0.05, a, glow_=0.35)
    fx.slam(img, '还是看跌？”', W / 2, 1280, 72, 'serif_black', t, tb - 0.05, a, glow_=0.35)
    for kw, s, x, col, sgn in (('看涨', 'BULLISH  ↑', 330, ICE, -1), ('看跌', 'BEARISH  ↓', 750, AMBER, 1)):
        k = ke(t, wt('S3', kw) + 0.1, 0.4)
        if k > 0:
            rrect(img, x - 150, 1360, x + 150, 1430, 8, col, a * k * 0.8, 1)
            text(img, s, x, 1395, 30, 'inter_semi', col, a * k, track=0.12)


# ---------------------------------------------------------------- 回到 1994：背景卡（与前两集同款）
def txt_ctx(img, t, subs):
    a = env(t, T_CTX, T_Q + 0.3, 0.6, 0.7)
    if a <= 0: return
    k = t - T_CTX
    text(img, '1994', W / 2, 760, 330, 'corm_med', GOLD * 0.55, a * 0.22, track=0.02, shadow=0)
    text(img, '1994 年 4 月 25 日 · 美国奥马哈', W / 2, 640, 34, 'sans_med', SUB_GOLD, a * eo(k / 0.6), track=0.12)
    gold_title(img, '伯克希尔·哈撒韦年度股东大会', W / 2, 750, 58, a * eo((k - 0.2) / 0.7), track=0.04, glow_=0.12)
    text(img, '上午场 · 股东问答', W / 2, 840, 44, 'serif_med', INK2, a * eo((k - 0.4) / 0.7), track=0.2)
    line(img, (W / 2 - 160, 905), (W / 2 + 160, 905), SUB_GOLD, a * 0.5 * eo((k - 0.5) / 0.6), 1)
    text(img, 'CNBC 巴菲特档案 · 第 47 章', W / 2, 965, 28, 'sans', INK2, a * eo((k - 0.7) / 0.7), track=0.06)
    text(img, 'Why we have no short-term opinion on stocks', W / 2, 1025, 32, 'ebg_i', INK, a * eo((k - 0.8) / 0.7))
    text(img, '以下为原始录像节选，画面与声音均为 1994 年现场原始记录', W / 2, 1120, 26, 'sans', INK2, a * eo((k - 1.2) / 0.8), track=0.02)


def dia_ctx(L, t):
    a = env(t, T_CTX, T_Q + 0.3, 0.6, 0.7)
    if a <= 0: return
    shock(L, (W / 2, 760), t, T_CTX, GOLD_H, a * 0.7, rmax=700, life=1.6, flatten=0.5)


# ================================================================ 原始问答：原始录像窗口 + 关键观点面板（克制：不做卡点特效）
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
    s = qa_env(t, 'never') * a
    if s > 0: shock(L, (W / 2, 1080), t, qs('A1', 1.2), GOLD_H, s, rmax=420, life=1.1, flatten=0.3)
    s = qa_env(t, 'fear') * a                                          # 本集标题的出处：“我们真正害怕的，是长期持续的非理性牛市”
    if s > 0: shock(L, (W / 2, 1305), t, qs('A19', 1.4), AMBER, s, rmax=420, life=1.1, flatten=0.3)
    s = qa_env(t, 'holder') * a                                        # 对股东：股票更便宜，对你们更有利
    if s > 0: shock(L, (W / 2, 1185), t, qs('O4B', 0.1), GOLD_H, s, rmax=420, life=1.1, flatten=0.3)


def munger_zoom(t):
    return eio((t - QA['munger_t'] + 1.0) / 2.5) * (1 - eio((t - QA['munger_end'] + 0.4) / 1.6))


def txt_qa(img, t, subs):
    a = qa_a(t)
    if a <= 0: return
    chapter_tag(img, t, '原始问答 · 1994 上午场原始录像（节选）', a)
    fr = grade(QA_CLIP.get(qa_src(t)), sat=0.62, gain=0.98)
    mz = munger_zoom(t)                                              # 芒格开口时，镜头缓缓推向芒格；巴菲特接话时拉回
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
    mt, me, at = QA['munger_t'], QA['munger_end'], QA['answer_t']
    spk = '查理·芒格' if mt - 0.3 <= t < me - 0.3 else ('沃伦·巴菲特' if t >= at - 0.2 else '提问 · 来自加州的股东')
    circle(img, (84, 786), 6, GOLD, a, fill=True)
    text(img, spk, 104, 786, 30, 'sans_med', INK, a, 'l', track=0.04)
    waveform(img, t, 860, 786, 260, 22, a)
    qa_panels(img, t, a)
    if subs:
        for s in QA['subs']:
            sa = env(t, s['t0'], s['t1'], 0.07, 0.07)
            if sa > 0: orig_sub(img, s, sa * a)
        for lg in TL['laughs']:
            la = env(t, lg['t0'], lg['t1'], 0.15, 0.2)
            if la > 0: text(img, '（现场笑声）', W / 2, 1405, 30, 'sans', INK2, la * a * 0.85, track=0.1)


PX0, PY0, PX1, PY1 = 110, 860, 970, 1350


def arrow_v(img, x, y, size, col, a, down=True):
    """竖直箭头"""
    if a <= 0.003: return
    s = 1 if down else -1
    line(img, (x, y - s * size / 2), (x, y + s * size / 2), col, a, 4)
    poly(img, [(x - size * 0.28, y + s * size * 0.22), (x, y + s * size / 2 + 2), (x + size * 0.28, y + s * size * 0.22)], col, a, 4)


def qa_panels(img, t, a):
    """关键观点面板（y 860–1350）"""
    # 提问：看涨还是看跌？
    ka = qa_env(t, 'ask') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='股东的问题', en='the question')
        k0 = ke(t, qs('Q1', 0.3))
        text(img, '您不看别人对市场、经济的评论——', W / 2, 1000, 36, 'sans_med', INK2, ka * k0, track=0.04)
        k1 = ke(t, qs('Q2', 0.3))
        text(img, '可你们自己，怎么看后市？', W / 2, 1080, 52, 'serif_bold', INK, ka * k1)
        for x, s, col, dn, kw in ((330, '看涨', ICE, False, 'Q3'), (750, '看跌', AMBER, True, 'Q3')):
            k = ke(t, qs(kw, 0.0 if not dn else 0.7), 0.4)
            if k <= 0: continue
            panel(img, x - 170, 1160, x + 170, 1310, ka * k, col=col, fill=0.55)
            arrow_v(img, x - 85, 1235, 64, col, ka * k, down=dn)
            fx.slam(img, s, x + 30, 1235, 64, 'serif_black', t, qs(kw, 0.0 if not dn else 0.7), ka, gold=False, col=col, glow_=0.25)
    # 回答：对市场从来没有看法
    ka = qa_env(t, 'never') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='巴菲特的回答', en="buffett's answer")
        k = ke(t, qs('A1', 1.0), 0.8)
        text(img, '对市场：', W / 2, 990, 38, 'sans_med', INK2, ka * k, track=0.2)
        text(img, '从来没有看法', W / 2, 1085, 88, 'serif_black', a=ka * k, gold=True, glow=0.25, wipe=k)
        k2 = ke(t, qs('A2', 0.3), 0.6)
        if k2 > 0:
            line(img, (W / 2 - 300 * k2, 1155), (W / 2 + 300 * k2, 1155), ICE, ka * 0.5, 1)
            text(img, '①  不会有什么用', W / 2, 1210, 38, 'sans_med', ICE, ka * k2, track=0.04)
            text(img, '②  还会干扰真正有用的判断', W / 2, 1280, 38, 'sans_med', AMBER, ka * ke(t, qs('A2', 1.6), 0.6), track=0.04)
    # 1942 → 1994：11 岁买下 3 股，此后的战争、核武器、总统辞职、通胀
    ka = qa_env(t, 'history') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='1942 → 1994', en='fifty-two years')
        xa, xb, yl = 200, 880, 1130
        kl = eio((t - qs('A8')) / 1.6)
        line(img, (xa, yl), (xa + (xb - xa) * kl, yl), INK2, ka * 0.7, 2)
        k3 = ke(t, qs('A3', 0.5), 0.6)
        circle(img, (xa, yl), 9, GOLD_HI, ka * k3, fill=True); glow(img, (xa, yl), 22, GOLD, ka * k3 * 0.6)
        text(img, '1942', xa, 975, 64, 'corm_med', GOLD_HI, ka * k3, glow=0.2)
        text(img, '11 岁 · 3 股', xa, 1035, 28, 'sans_med', INK, ka * ke(t, qs('A3', 2.5)), track=0.06)
        kw = env(t, qs('A4'), qs('A8', -0.2), 0.4, 0.4)
        if kw > 0:
            panel(img, 330, 960, 900, 1080, ka * kw, col=AMBER, fill=0.6)
            text(img, '二战 · 太平洋战场节节失利', 615, 1000, 34, 'serif_bold', AMBER, ka * kw)
            text(img, '前景确实不乐观', 615, 1048, 26, 'sans', INK2, ka * kw * ke(t, qs('A5')), track=0.1)
        if kl > 0:
            circle(img, (xb, yl), 9, INK, ka * ke(t, qs('A8', 1.0)), fill=True)
            text(img, '1994', xb, 990, 64, 'corm_med', INK, ka * ke(t, qs('A8', 1.0)))
        ev = [('核武器', 370, -1), ('几场大战', 500, 1), ('总统辞职', 640, -1), ('严重通胀', 775, 1)]
        d9 = max(QSUB['A9']['t1'] - QSUB['A9']['t0'], 1.0)
        for i, (s, x, sg) in enumerate(ev):
            ti = qs('A9', 0.2 + i * d9 * 0.22)
            k = ke(t, ti, 0.3)
            if k <= 0: continue
            circle(img, (x, yl), 7, AMBER, ka * k, fill=True)
            line(img, (x, yl), (x, yl + sg * 40 * k), AMBER, ka * k * 0.7, 1)
            text(img, s, x, yl + sg * 62, 30, 'sans_med', AMBER, ka * k, track=0.04)
        k10 = ke(t, qs('A10', 0.6), 0.6)
        if k10 > 0:
            text(img, '因为猜测宏观，放弃自己擅长的事？', W / 2, 1258, 34, 'sans_med', INK, ka * k10, track=0.04)
            fx.slam(img, '毫无道理', W / 2, 1312, 44, 'serif_black', t, qs('A10', 4.6), ka, glow_=0.25)
    # 最好的事：市场大幅下跌——长期的买家希望价格下跌
    ka = qa_env(t, 'buyer') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='从伯克希尔的角度看', en="from berkshire's standpoint")
        k = ke(t, qs('A11', 0.8), 0.6); k12 = ke(t, qs('A12', 1.0), 0.5)
        text(img, '最好的事：', 330, 985, 36, 'sans_med', INK2, ka * k, 'r', track=0.1)
        text(img, '市场大幅下跌', 350, 985, 56, 'serif_black', a=ka * k12, gold=True, anchor='l', glow=0.2)
        if k12 > 0: arrow_v(img, 760, 985, 54, GOLD_HI, ka * k12, down=True)
        rows = (('A14', '买菜的人', '希望菜价', INK), ('A15', '买车的人', '希望车价', INK), ('A16', '买企业（股票）的人', '希望股价', None))
        for i, (sid, who, want, col) in enumerate(rows):
            kk = ke(t, qs(sid, 0.6 if i < 2 else 1.4), 0.4)
            if kk <= 0: continue
            y = 1080 + i * 78
            text(img, who, 520, y, 38, 'serif_bold', INK if col is not None else GOLD_HI, ka * kk, 'r', glow=0.15 if col is None else 0.0)
            text(img, want, 560, y, 38, 'sans_med', INK2, ka * kk, 'l')
            arrow_v(img, 760, y, 46, GOLD_HI if col is None else ICE, ka * kk, down=True)
            text(img, '下跌', 800, y, 38, 'serif_black', GOLD_HI if col is None else ICE, ka * kk, 'l')
        k17 = ke(t, qs('A17', 0.5), 0.6)
        text(img, '能以有吸引力的价格买到——处境好得多', W / 2, 1312, 30, 'sans_med', GOLD_C, ka * k17, track=0.06)
    # 真正害怕的：长期持续的非理性牛市
    ka = qa_env(t, 'fear') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='真正害怕的', en='what we fear')
        k = ke(t, qs('A18'), 0.5)
        text(img, '下跌？一点也不怕', W / 2, 990, 44, 'serif_bold', INK, ka * k * (1 - 0.6 * ke(t, qs('A19', 0.5))))
        kb = eio((t - qs('A19', 0.4)) / max(QSUB['A19']['t1'] - QSUB['A19']['t0'], 1.0))
        if kb > 0:
            xs = np.linspace(200, 880, 60)
            u = np.linspace(0, 1, 60)
            ys = 1240 - 180 * u ** 2.2 + 6 * np.sin(u * 40)
            n = max(2, int(60 * kb))
            area(img, np.c_[xs[:n], ys[:n]], 1250, AMBER, ka * 0.6, top=0.22)
            gline(img, np.c_[xs[:n], ys[:n]], AMBER, ka, th=3)
            glow(img, (xs[n - 1], ys[n - 1]), 14, GOLD_HI, ka)
            text(img, 'IRRATIONAL BULL MARKET', 200, 1060, 20, 'inter_semi', AMBER, ka * kb, 'l', track=0.2)
        fx.slam(img, '长期持续的非理性牛市', W / 2, 1305, 52, 'serif_black', t, qs('A19', 1.4), ka, gold=False, col=AMBER, glow_=0.3)
    # 对伯克希尔的股东：除非借钱持股、或很快要卖——股票更便宜，对你们更有利
    ka = qa_env(t, 'holder') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='对伯克希尔的股东', en='to berkshire shareholders')
        d4 = QSUB['O4A']['t1'] - QSUB['O4A']['t0']
        k0 = ke(t, qs('O4A', 0.1 * d4), 0.5)
        text(img, '除非——', W / 2, 975, 34, 'sans_med', INK2, ka * k0, track=0.2)
        for x, s_, en, d in ((330, '借钱持股', 'on borrowed money', 0.3), (750, '很快就要卖', 'sell in a very short time', 0.55)):
            kk = ke(t, qs('O4A', d * d4), 0.4)
            if kk <= 0: continue
            panel(img, x - 190, 1015, x + 190, 1115, ka * kk, col=AMBER, fill=0.55)
            cross(img, (x - 135, 1050), 13, AMBER, ka * kk)
            text(img, s_, x + 15, 1050, 40, 'serif_black', AMBER, ka * kk)
            text(img, en, x, 1094, 19, 'ebg_i', INK2, ka * kk)
        fx.slam(img, '股票更便宜，对你们更有利', W / 2, 1190, 56, 'serif_black', t, qs('O4B', 0.1), ka, glow_=0.35)
        k3 = ke(t, qs('O4C', 0.8), 0.6)
        text(img, '因为我们能替你们做更多明智的事', W / 2, 1282, 32, 'sans_med', GOLD_C, ka * k3, track=0.06)
    # 芒格：对宏观持不可知的态度 → 把时间全用在具体的企业上
    ka = qa_env(t, 'munger') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='芒格的补充', en="munger's addendum")
        k1 = ke(t, qs('M1', 1.6), 0.6)
        text(img, '宏观因素：不可知', W / 2, 990, 52, 'serif_bold', ICE, ka * k1)
        text(img, 'AGNOSTIC ABOUT MACRO FACTORS', W / 2, 1045, 20, 'inter_semi', INK2, ka * k1, track=0.2)
        k2 = ke(t, qs('M2', 0.8), 0.6)
        arrow_v(img, W / 2, 1100, 40, INK2, ka * k2, down=True)
        text(img, '把全部时间用在', W / 2, 1150, 30, 'sans_med', INK2, ka * k2, track=0.1)
        text(img, '具体的企业 · 具体的机会', W / 2, 1210, 50, 'serif_black', a=ka * ke(t, qs('M2', 2.5), 0.6), gold=True, glow=0.2)
        fx.slam(img, '高效得多', W / 2, 1292, 48, 'serif_black', t, qs('M3', 0.6), ka, gold=False, col=ICE, glow_=0.25)
    # 回到企业本身：对企业的判断对了，结果就不会差
    ka = qa_env(t, 'right') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='巴菲特：回到企业本身', en='if you’re right about the businesses')
        fx.slam(img, '对企业的判断对了，', W / 2, 1040, 60, 'serif_black', t, qs('A20', 0.2), ka, gold=False, col=INK, glow_=0.2)
        fx.slam(img, '最后的结果就不会差', W / 2, 1150, 60, 'serif_black', t, qs('A20', 1.8), ka, glow_=0.35)
        text(img, '“If you’re right about the businesses, you’ll end up doing fine.”', W / 2, 1250, 26, 'ebg_i', INK2, ka * ke(t, qs('A20', 2.6)))
    # 可口可乐：1890 年 2000 美元 → 1994 年 500 多亿美元
    ka = qa_env(t, 'coke') * a * (1 - ke(t, T_QUOTE - 0.4, 0.3))
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='这家公司：可口可乐', en='coca-cola')
        k1 = ke(t, qs('A25', 1.0), 0.6)
        text(img, '1890 年前后 · 整个公司', 330, 975, 26, 'sans_med', INK2, ka * k1, track=0.04)
        text(img, '2,000 美元', 330, 1040, 56, 'corm_med', INK, ka * k1)
        k2 = ke(t, qs('A26', 0.8), 0.6)
        if k2 > 0:
            text(img, '1994 年 · 市值', 750, 975, 26, 'sans_med', INK2, ka * k2, track=0.04)
            v = 2000 * (25_000_000 ** eio((t - qs('A26', 0.8)) / 1.6))
            s = f'{v / 1e8:,.0f} 亿美元' if v >= 1e8 else (f'{v / 1e4:,.0f} 万美元' if v >= 1e4 else f'{v:,.0f} 美元')
            if v >= 4.99e10: s = '500 多亿美元'
            text(img, s, 750, 1040, 56, 'corm_med', a=ka * k2, gold=True, glow=0.2)
            arrow = 420 + 120 * k2
            line(img, (480, 1040), (min(arrow, 560), 1040), GOLD_C, ka * k2 * 0.7, 2)
        tags = (('两次世界大战', 330, 'A28', 0.6), ('1907 年大恐慌', 750, 'A28', 3.6))
        for s, x, sid, d in tags:
            k = env(t, qs(sid, d), qs('A29', 1.6), 0.3, 0.4)
            if k <= 0: continue
            rrect(img, x - 170, 1110, x + 170, 1180, 8, AMBER, ka * k * 0.8, 1)
            text(img, s, x, 1145, 34, 'sans_med', AMBER, ka * k, track=0.04)
        fx.slam(img, '“是不是等等再买？”', W / 2, 1265, 52, 'serif_black', t, qs('A29'), ka, gold=False, col=INK, glow_=0.2)


# ---------------------------------------------------------------- 问答收尾的金句卡：“这种错误，我们可犯不起。”（停留 2 秒以上）
T_QUOTE = qs(QUOTE_ID)


def quote_a(t):
    return env(t, T_QUOTE - 0.3, T_INS - 0.1, 0.25, 0.35)


def txt_quote(img, t, subs):
    a = quote_a(t)
    if a <= 0: return
    panel(img, 80, 830, 1000, 1390, a, col=GOLD_C, title='巴菲特 · 1994', en='warren buffett', fill=0.9)
    text(img, '“是不是该等等再买？”', W / 2, 970, 34, 'sans_med', INK2, a, track=0.06)
    fx.slam(img, '这种错误，', W / 2, 1065, 80, 'serif_black', t, T_QUOTE - 0.2, a, glow_=0.3)
    fx.slam(img, '我们可犯不起。', W / 2, 1170, 80, 'serif_black', t, T_QUOTE + 0.6, a, glow_=0.45)
    k = ke(t, T_QUOTE + 1.2, 0.6)
    text(img, '“We can’t afford that mistake.”', W / 2, 1262, 32, 'ebg_i', INK, a * k, shadow=0.6)
    text(img, '—— 沃伦·巴菲特，1994 年伯克希尔股东大会', W / 2, 1325, 24, 'sans', INK2, a * k, track=0.06)


def dia_quote(L, t):
    a = quote_a(t)
    if a <= 0: return
    shock(L, (W / 2, 1170), t, T_QUOTE + 0.6, GOLD_H, a, rmax=560, life=1.1, flatten=0.3)


# ================================================================ 投资启示（本片解读）：与前两集同款的标题转场
NOTE = '本片解读，非巴菲特或芒格原话'
T_INS_END = I['I11']['t1'] + 0.3


def sc(t, b_in, b_out):
    """启示段内的换镜：0.5 秒暗下 → 0.15 秒黑 → 0.45 秒亮起（不硬切）"""
    u = eio((t - (b_in + 0.15)) / 0.45)
    return u * (1 - eio((t - (b_out - 0.5)) / 0.5))


def ins_bg(img, t):
    """整段启示的背景（与前两集一致）：透视网格 + 3D 金色微粒 + 漏光"""
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
    chapter_tag(img, t, '投资启示 · 本片解读', env(t, I['I1']['t0'] - 0.4, T_INS_END, 0.6, 0.6))


def header(img, s, a, y=330):
    text(img, s, W / 2, y, 26, 'sans_med', SUB_GOLD, a, track=0.2)


B_I1 = I['I1']['t0'] - 0.45
B_CAPE = NV['entry'] - 0.4                  # 配乐大段落回归的重拍上亮起（I2 开口）
B_BUB = wt('I7', '纳斯达克') - 0.55           # “历史上最贵的一次，正是 1999 年”仍停在散点图上，说到纳斯达克再换成两条线
B_COND = I['I10']['t0'] + 1.2                # 泡沫图多停一拍（“前提”的第一个关键词约在 2 秒后），让 2000–2002 的对比看得清
B_TODAY = b_before(I['I11']['t0'])
B_CLOSE = I['I11']['t1'] + 0.4               # 最后一句说完，卡片淡出
B_FLY = I['I11']['t1'] - 1.2                 # 星图穿梭从最后半句下面升起，推向高潮

# ---------------------------------------------------------------- I1：对一直在买的人，下跌是打折；真正可怕的是长期的非理性牛市
_r1 = np.random.default_rng(23)
I1_DOWN = np.r_[np.linspace(0, -0.55, 40)] + _r1.normal(0, 0.03, 40)
I1_UP = np.linspace(0, 1, 60) ** 3.0 + _r1.normal(0, 0.012, 60)


def i1_a(t): return sc(t, B_I1 if t > I['I1']['t0'] - 1 else 0, B_CAPE) * env(t, I['I1']['t0'] - 0.3, 1e9, 0.4, 0.1)


def dia_i1(L, t):
    a = i1_a(t)
    if a <= 0: return
    shock(L, (W / 2, 690), t, wt('I1', '打折') - 0.05, GOLD_H, a, rmax=420, life=1.0, flatten=0.3)
    shock(L, (W / 2, 1335), t, wt('I1', '非理性') - 0.05, AMBER, a, rmax=420, life=1.0, flatten=0.3)


def txt_i1(img, t, subs):
    a = i1_a(t)
    if a <= 0: return
    tb, td, tf = wt('I1', '买家'), wt('I1', '打折'), wt('I1', '害怕')
    kd = ke(t, I['I1']['t0'] + 0.2)
    panel(img, 90, 280, 990, 760, a * max(kd, 0.55), col=GOLD_C, title='对一直在买的人', en='for a buyer over time')
    if kd > 0:
        n = max(2, int(40 * eio((t - I['I1']['t0'] - 0.2) / (tb - I['I1']['t0'] + 1.0))))
        xs = np.linspace(150, 930, 40)[:n]
        ys = 470 - I1_DOWN[:n] * 330
        gline(img, np.c_[xs, ys], ICE, a * kd, th=3)
        for i in range(0, n, 6):                        # 每一段都在买：价格越低，同样的钱买到的越多（金点越大）
            r = 9 + 20 * (-I1_DOWN[i] / 0.55)
            glow(img, (xs[i], ys[i]), r * 1.6, GOLD * 0.6, a * kd * 0.6)
            circle(img, (xs[i], ys[i]), r * 0.55, GOLD_HI, a * kd, fill=True)
        text(img, '价格', 160, 440, 24, 'sans_med', ICE, a * kd, 'l', track=0.1)
        text(img, '● 持续买入', 930, 420, 24, 'sans_med', GOLD_C, a * kd, 'r', track=0.06)
        fx.slam(img, '下跌 ＝ 打折', W / 2, 705, 60, 'serif_black', t, td - 0.05, a * kd, glow_=0.4)
    kf = ke(t, tf - 0.3)
    panel(img, 90, 820, 990, 1400, a * max(kf, 0.55), col=AMBER, title='真正让他害怕的', en='what he really fears')
    if kf > 0:
        n = max(2, int(60 * eio((t - tf + 0.2) / 2.2)))
        xs = np.linspace(150, 930, 60)[:n]
        ys = 1240 - I1_UP[:n] * 300
        area(img, np.c_[xs, ys], 1250, AMBER, a * kf * 0.8, top=0.25)
        gline(img, np.c_[xs, ys], AMBER, a * kf, th=4)
        glow(img, (xs[-1], ys[-1]), 16, GOLD_HI, a * kf)
        tn = wt('I1', '非理性')
        fx.slam(img, '长期持续的非理性牛市', W / 2, 1335, 56, 'serif_black', t, tn - 0.05, a * kf, gold=False, col=AMBER, glow_=0.4)
        if tn - 0.05 < t < tn + 0.45: fx.glitch(img, (90, 950, 990, 1280), t, 0.6 * (1 - (t - tn + 0.05) / 0.5), seed=21)


# ---------------------------------------------------------------- I2–I3：第一性原理——回报来自企业赚的钱，也取决于买入价；Shiller 1881–2013 每月的 CAPE 与此后十年回报
_CJ = json.load(open(os.path.join(HERE, '..', 'data', CAPE)))
CA_X = np.array(_CJ['cape'], float); CA_Y = np.array(_CJ['fwd'], float) * 100
CA_D = _CJ['date']
CA_Q20, CA_Q80, CA_LO, CA_HI = _CJ['q20'], _CJ['q80'], _CJ['mean_lo'] * 100, _CJ['mean_hi'] * 100
I_82, I_99 = CA_D.index('1982.07'), CA_D.index('1999.12')
KX0, KX1, KYT, KYB = 200, 930, 978, 1372                  # 散点图绘图区
KXV0, KXV1, KYV0, KYV1 = 4.0, 46.0, -7.0, 21.0


def kx(v): return KX0 + (v - KXV0) / (KXV1 - KXV0) * (KX1 - KX0)
def ky(v): return KYB - (v - KYV0) / (KYV1 - KYV0) * (KYB - KYT)


# 点的颜色随买入时的估值从金（便宜）过渡到琥珀（贵）
_u = np.clip((CA_X - CA_Q20) / (CA_Q80 - CA_Q20), 0, 1)[:, None]
CA_COL = GOLD_H * (1 - _u) + AMBER * _u


def cape_a(t): return sc(t, B_CAPE, B_BUB)


def dia_cape(L, t):
    a = cape_a(t)
    if a <= 0: return
    shock(L, (W / 2, 590), t, B_CAPE + 0.4, GOLD_H, a, rmax=640, life=1.2, flatten=0.45)    # 配乐大段落回归的重拍
    t3 = I['I3']['t0']
    kp = eio((t - t3 - 0.1) / 2.2)                                       # 按时间顺序（1881 → 2013）一个月一个点地落下
    n = int(len(CA_X) * kp)
    if n <= 0: return
    tc, te, t99 = wt('I3', '最便宜'), wt('I3', '最贵'), wt('I7', '最贵')
    lo, hi = CA_X[:n] <= CA_Q20, CA_X[:n] >= CA_Q80
    dim_mid = 1 - 0.55 * ke(t, tc - 0.1, 0.5)
    w = np.where(lo, 1.0, np.where(hi, 1.0 - 0.45 * ke(t, tc - 0.1, 0.5) * (1 - ke(t, te - 0.1, 0.5)), dim_mid))
    w = w * (1 - 0.5 * ke(t, t99 - 0.2, 0.5))
    cloud(L, np.c_[kx(CA_X[:n]), ky(CA_Y[:n])], CA_COL[:n], 1.5 * a, w=w, sig=1.5)
    for i, tt in ((I_82, tc + 0.9), (I_99, t99 - 0.05)):
        shock(L, (kx(CA_X[i]), ky(CA_Y[i])), t, tt, GOLD_H if i == I_82 else AMBER, a, rmax=180, life=0.9, flatten=0.9)


def txt_cape(img, t, subs):
    a = cape_a(t)
    if a <= 0: return
    header(img, '第一性原理 · 回报从哪里来', a)
    # 上：股票是企业的一部分；回报 = 企业赚的钱（你得到的）× 你付的价格
    panel(img, 90, 380, 990, 795, a, col=GOLD_C, title='回报从哪里来', en='where returns come from')
    k0 = ke(t, wt('I2', '股票') - 0.15, 0.5)
    text(img, '股票  ＝  企业的一部分', W / 2, 500, 40, 'serif_bold', INK, a * k0, track=0.06)
    text(img, '“We buy pieces of businesses: stocks.”  —— 巴菲特，1994', W / 2, 545, 20, 'ebg_i', INK2, a * ke(t, wt('I2', '一部分') + 0.3), track=0.02)
    for x, kw, big, en, col, gold_ in ((310, '企业赚', '企业赚的钱', 'VALUE · 你得到的', GOLD_C, True),
                                       (770, '价格', '你买入的价格', 'PRICE · 你付出的', ICE, False)):
        kk = ke(t, wt('I2', kw) - 0.2, 0.45)
        if kk <= 0: continue
        rrect(img, x - 200, 585, x + 200, 685, 10, col, a * kk * 0.85, 1)
        if gold_: fx.slam(img, big, x, 621, 44, 'serif_black', t, wt('I2', kw) - 0.2, a, glow_=0.3)
        else: fx.slam(img, big, x, 621, 44, 'serif_black', t, wt('I2', kw) - 0.2, a, gold=False, col=ICE, glow_=0.3)
        text(img, en, x, 665, 20, 'inter_semi', col, a * kk, track=0.16)
    kq = ke(t, wt('I2', '价格') + 0.9, 0.4)
    if kq > 0:
        fx.typewriter(img, '“Price is what you pay; value is what you get.”', W / 2, 727, 30, 'ebg_i', INK, a * kq, t,
                      wt('I2', '价格') + 0.9, cps=34)
        text(img, '—— 巴菲特 2008 年致股东信，引述老师格雷厄姆', W / 2, 765, 21, 'sans', INK2,
             a * ke(t, wt('I2', '价格') + 2.3, 0.5), track=0.02)
    # 下：1881–2013 每个月——买入时的估值 vs 此后十年的年化实际回报
    t3 = I['I3']['t0']
    kc = ke(t, t3 - 0.4, 0.5)
    if kc <= 0: return
    panel(img, 90, 825, 990, 1480, a * kc, col=GOLD_C, title='买入时的估值  vs  此后十年的回报', en='us stocks · every month 1881–2013')
    ac = a * kc
    text(img, '此后十年 · 年化实际回报（含股息、扣除通胀）', KX0, KYT - 28, 19, 'sans', INK2, ac, 'l', track=0.04)
    for v in (-5, 0, 5, 10, 15, 20):
        y = ky(v)
        if v == 0: line(img, (KX0, y), (KX1, y), INK2, ac * 0.55, 1)
        else: dashed(img, (KX0, y), (KX1, y), INK3, ac * 0.4, dash=5, gap=8)
        text(img, f'{v:+d}%'.replace('-', '−') if v else '0', KX0 - 10, y, 19, 'inter', INK2, ac, 'r')
    for v in (10, 20, 30, 40):
        text(img, f'{v}', kx(v), KYB + 24, 21, 'corm_med', INK2, ac)
    text(img, '买入时的估值：股价 ÷ 过去十年平均利润（CAPE，倍）', (KX0 + KX1) / 2, KYB + 58, 20, 'sans', INK2, ac, track=0.04)
    tc, te, t99 = wt('I3', '最便宜'), wt('I3', '最贵'), wt('I7', '最贵')
    # 最便宜的五分之一
    kl = ke(t, tc - 0.15, 0.45)
    if kl > 0:
        rect(img, KX0, KYT, kx(CA_Q20), KYB, GOLD, ac * kl * 0.09)
        y = ky(CA_LO)
        line(img, (KX0, y), (kx(CA_Q20), y), GOLD_HI, ac * kl, 3)
        rrect(img, 232, 1250, 560, 1350, 10, GOLD_C, ac * kl * 0.85, 1, fill=False)
        text(img, '最便宜的两成时段买入', 396, 1278, 22, 'sans_med', INK2, ac * kl, track=0.04)
        text(img, f'平均每年 +{CA_LO:.1f}%', 396, 1320, 38, 'corm_med', a=ac * kl, gold=True, glow=0.2)
        k82 = ke(t, tc + 0.9, 0.4) * (1 - ke(t, te - 0.45, 0.35))           # 说到“最贵”时让位给右上角的标注
        if k82 > 0:
            p = (kx(CA_X[I_82]), ky(CA_Y[I_82]))
            circle(img, p, 9, GOLD_HI, ac * k82, 2)
            text(img, f'1982.07 · {CA_X[I_82]:.1f} 倍 → 此后十年每年 +{CA_Y[I_82]:.1f}%', p[0] + 16, p[1] - 4, 20, 'sans_med', GOLD_HI, ac * k82, 'l')
    # 最贵的五分之一
    kh = ke(t, te - 0.15, 0.45)
    if kh > 0:
        rect(img, kx(CA_Q80), KYT, KX1, KYB, AMBER, ac * kh * 0.09)
        y = ky(CA_HI)
        line(img, (kx(CA_Q80), y), (KX1, y), AMBER, ac * kh, 3)
        rrect(img, 598, 965, 920, 1065, 10, AMBER, ac * kh * 0.85, 1)
        text(img, '最贵的两成时段买入', 759, 993, 22, 'sans_med', INK2, ac * kh, track=0.04)
        text(img, f'平均每年 +{CA_HI:.1f}%', 759, 1035, 38, 'corm_med', AMBER, ac * kh, glow=0.2)
    # I7 开头：历史上最贵的一次——1999 年 12 月
    k9 = ke(t, t99 - 0.1, 0.4)
    if k9 > 0:
        p = (kx(CA_X[I_99]), ky(CA_Y[I_99]))
        r = 12 + 26 * math.exp(-max(t - t99, 0) / 0.35)
        circle(img, p, r, AMBER, ac * k9, 3)
        glow(img, p, 30, AMBER, ac * k9 * 0.7)
        text(img, '1999.12 · 史上最贵', p[0] - 20, p[1] - 58, 26, 'serif_bold', AMBER, ac * k9, 'r')
        text(img, f'{CA_X[I_99]:.1f} 倍 → 此后十年每年 {CA_Y[I_99]:.1f}%'.replace('-', '−'), p[0] - 20, p[1] - 26, 21, 'sans_med', INK, ac * k9, 'r')
    text(img, '数据：Robert Shiller（ie_data.xls），1881.01–2013.09 共 1,593 个月；每个点是一个月份', W / 2, 1462, 16, 'sans', INK3 * 1.5, ac * 0.9)


# ---------------------------------------------------------------- I7–I8：两条路——纳斯达克（科技股）与伯克希尔股价，1994.04.25 = 1
# 一张图讲完因果：连涨五年、科技股最疯 → 巴菲特一股科技股都没买 → 1999 年伯克希尔 −19.9%、被质疑落伍 → 泡沫破裂、纳指 −78%、15 年才回到原位 → 同期伯克希尔不跌反涨
_NB = json.load(open(os.path.join(HERE, '..', 'data', NQBK)))
NB_D = _NB['date']; NB_Q = np.array(_NB['ixic'], float); NB_B = np.array(_NB['brka'], float)
NB_I = {d: i for i, d in enumerate(NB_D)}
NB_Y = np.array([int(d[:4]) + (int(d[5:7]) - 1) / 12 + (int(d[8:]) - 1) / 365 for d in NB_D])
I_MEET, I_PEAK, I_LOW, I_REC = NB_I['1994-04-25'], NB_I['2000-03-10'], NB_I['2002-10-09'], NB_I['2015-04-23']
NQ1 = NB_Q / NB_Q[I_MEET]; BK1 = NB_B / NB_B[I_MEET]                   # 都以 1994 年 4 月 25 日为 1
NX0, NX1, NYB, NYT = 175, 925, 1110, 540


_VMAX = [7.5]


def nx(y): return NX0 + (y - 1994.3) / (2016.0 - 1994.3) * (NX1 - NX0)
def ny(v): return NYB - v / _VMAX[0] * (NYB - NYT)


def bub_vmax(t):
    """纵轴上限：先 7.5（看清 1995–2000 的狂飙），画到 2003 年之后再平滑放大到 15（容下伯克希尔后来的上涨）"""
    tr = wt('I8', '原位')
    return lerp(7.5, 15.0, eio((t - tr) / 1.6))


def bub_a(t): return sc(t, B_BUB, B_COND)


def bub_year(t):
    """两条线画到哪一年：I7（从说到纳斯达克起）画到 1999 年底，I7B 停住（聚焦 1999），I8 画过高点、崩塌、一直画到 2015"""
    t7 = B_BUB; t1 = wt('I7', '一股')
    tb, t78, tr = wt('I8', '破'), wt('I8', '七十八'), wt('I8', '原位')
    if t < tb: return 1994.31 + (2000.0 - 1994.31) * eio((t - t7 - 0.3) / max(t1 - t7 - 0.3, 0.8))
    if t < t78: return 2000.0 + 0.2 * eio((t - tb + 0.2) / 0.5)
    if t < tr: return 2000.2 + (2002.8 - 2000.2) * eio((t - t78 + 0.3) / 0.8)
    return 2002.8 + (2015.9 - 2002.8) * eio((t - tr + 0.1) / 1.8)


def dia_bub(L, t):
    a = bub_a(t)
    if a <= 0: return
    _VMAX[0] = bub_vmax(t)
    t78 = wt('I8', '七十八')
    if t78 - 0.6 < t < t78 + 2.2:                                   # 崩塌时从高点洒落的碎屑
        dt = t - t78 + 0.6
        rng = np.random.default_rng(19)
        n = 320
        ang = rng.uniform(-math.pi, 0, n); sp = rng.uniform(60, 260, n)
        cx, cy = nx(NB_Y[I_PEAK]), ny(NQ1[I_PEAK])
        x = cx + np.cos(ang) * sp * dt; y = cy - np.sin(ang) * sp * dt * 0.4 + 160 * dt * dt
        ok = y < NYB
        cloud(L, np.c_[x[ok], y[ok]], AMBER, 0.6 * a * max(0.0, 1 - dt / 2.6) ** 1.5)
    shock(L, (nx(NB_Y[I_LOW]), ny(NQ1[I_LOW])), t, t78 + 0.3, AMBER, a, rmax=200, life=0.9, flatten=0.6)
    tu = wt('I8', '不跌反涨')
    shock(L, (nx(2015.5), ny(BK1[-1])), t, tu, GOLD_H, a, rmax=200, life=0.9, flatten=0.7)


def txt_bub(img, t, subs):
    a = bub_a(t)
    if a <= 0: return
    _VMAX[0] = bub_vmax(t)
    header(img, '1994–2015 · 每日收盘 · 1994 年 4 月 25 日 ＝ 1', a)
    panel(img, 90, 380, 990, 1180, a, col=GOLD_C, title='两条路', en='nasdaq (tech) vs. berkshire')
    zoom = (_VMAX[0] - 7.5) / 7.5
    for vals, ka in (((1, 2, 3, 4, 5, 6, 7), 1 - zoom), ((1, 5, 10, 15), zoom)):
        if ka <= 0.02: continue
        for v in vals:
            y = ny(v)
            if y < NYT - 5: continue
            dashed(img, (NX0, y), (NX1, y), INK3, a * 0.45 * ka, dash=6, gap=8)
            text(img, f'{v}', NX0 - 10, y, 20, 'inter', INK2, a * ka, 'r')
    for yr in (1995, 2000, 2005, 2010, 2015):
        text(img, str(yr), nx(yr), NYB + 28, 22, 'corm_med', INK2, a)
    yv = bub_year(t)
    n = int(np.searchsorted(NB_Y, yv))
    sl = slice(I_MEET, max(n, I_MEET + 2))
    xs = nx(NB_Y[sl])
    # 纳斯达克：冰青细线（崩塌只用 −78% 的琥珀标注）；伯克希尔：金色粗线
    hot = NB_Y[sl] <= NB_Y[I_PEAK]
    q = ny(NQ1[sl])
    gline(img, np.c_[xs, q], ICE, a, th=3)
    # 伯克希尔：金色；1999 年这一段在 I7B 里标成琥珀
    b = ny(BK1[sl])
    gline(img, np.c_[xs, b], GOLD_HI, a, th=5, halo=9.0)
    glow(img, (xs[-1], q[-1]), 12, ICE, a)
    glow(img, (xs[-1], b[-1]), 14, GOLD_HI, a)
    ktag = a * ke(t, B_BUB + 0.8, 0.4) * (1 - ke(t, wt('I8', '破') - 0.2, 0.3))
    if ktag > 0:
        lq, lb = q[-1], b[-1]
        if abs(lq - lb) < 34: lq, lb = (min(lq, lb) - 18, max(lq, lb) + 18) if lq < lb else (max(lq, lb) + 18, min(lq, lb) - 18)
        text(img, '纳斯达克（科技股）', xs[-1] + 16, lq, 24, 'sans_med', ICE, ktag, 'l')
        text(img, '伯克希尔股价', xs[-1] + 16, lb, 24, 'sans_med', GOLD_HI, ktag, 'l')
    k0 = ke(t, wt('I7', '一股') - 0.1, 0.4)
    if k0 > 0 and t < wt('I8', '破'):
        bx, by = nx(2003.6), NYT + 60
        rrect(img, bx - 14, by - 30, bx + 420, by + 30, 8, GOLD_C, a * k0 * 0.8, 1)
        text(img, '巴菲特：看不懂科技公司，一股也不碰', bx + 6, by, 26, 'sans_med', GOLD_HI, a * k0, 'l')
    # I7–I7B：1999 年——纳斯达克 +85.6%，伯克希尔股价 −19.9%，被质疑落伍
    t99 = wt('I7', '一九九九')
    k9 = env(t, t99 - 0.2, wt('I8', '破') + 0.6, 0.4, 0.5)
    if k9 > 0:
        x0, x1 = nx(1999.0), nx(2000.0)
        rect(img, x0, NYT, x1, NYB, AMBER, a * k9 * 0.10)
        i0, i1 = NB_I['1998-12-31'], min(NB_I['1999-12-31'], n)        # 只高亮已经画出来的那一段
        if i1 - i0 > 1: gline(img, np.c_[nx(NB_Y[i0:i1 + 1]), ny(BK1[i0:i1 + 1])], AMBER, a * k9, th=5)
        text(img, '1999', (x0 + x1) / 2, NYB - 24, 24, 'corm_med', AMBER, a * k9)
    nq99 = (NB_Q[NB_I['1999-12-31']] / NB_Q[NB_I['1998-12-31']] - 1) * 100
    for (sid, kw), x, lab, v, col in ((('I7', '八十六'), 300, '1999 年 · 纳斯达克', nq99, ICE),
                                     (('I7B', '股价'), 780, '1999 年 · 伯克希尔股价', BRK_TABLE[1999][0], AMBER)):
        kk = env(t, wt(sid, kw) - 0.15, wt('I8', '破') - 0.1, 0.35, 0.4)
        if kk <= 0: continue
        rrect(img, x - 205, 1215, x + 205, 1320, 10, col, a * kk * 0.85, 1)
        text(img, lab, x, 1245, 24, 'sans_med', INK2, a * kk, track=0.04)
        text(img, f'{v:+.1f}%', x, 1290, 46, 'corm_med', col if col is AMBER else ICE, a * kk, glow=0.2)
    kl = env(t, wt('I7B', '落伍') - 0.2, wt('I8', '破') - 0.1, 0.35, 0.4)
    if kl > 0:
        text(img, '《巴伦周刊》1999.12.27', W / 2, 1352, 22, 'sans_med', INK2, a * kl, track=0.06)
        fx.typewriter(img, '“What’s Wrong, Warren?”', W / 2, 1398, 36, 'ebg_i', INK, a * kl, t, wt('I7B', '落伍') - 0.1, cps=22)
    # I8：泡沫破裂——高点、−78%、15 年才回到原位；同一时期伯克希尔不跌反涨
    tb, t78, tr, tu = wt('I8', '破'), wt('I8', '七十八'), wt('I8', '原位'), wt('I8', '不跌反涨')
    kp = ke(t, tb + 0.2, 0.4)
    if kp > 0:
        p = (nx(NB_Y[I_PEAK]), ny(NQ1[I_PEAK]))
        circle(img, p, 10, GOLD_HI, a * kp, 2)
        text(img, '2000.03 泡沫见顶', p[0] + 16, p[1] - 6, 24, 'sans_med', GOLD_HI, a * kp, 'l')
    kl8 = ke(t, t78 + 0.2, 0.4)
    if kl8 > 0:
        y0, y1 = ny(NQ1[I_PEAK]), ny(NQ1[I_LOW])
        xb = nx(NB_Y[I_LOW]) + 34
        dashed(img, (nx(NB_Y[I_PEAK]) + 12, y0), (xb, y0), AMBER, a * kl8 * 0.6, dash=5, gap=6)
        line(img, (xb, y0), (xb, y0 + (y1 - y0) * kl8), AMBER, a, 2)
        text(img, '−78%', xb + 12, (y0 + y1) / 2, int(56 * (1 + 0.4 * math.exp(-max(t - t78 - 0.2, 0) / 0.15))), 'corm_med', AMBER,
             a * kl8, 'l', glow=0.35)
    kr = ke(t, tr + 0.4, 0.6)
    if kr > 0:
        yp = ny(NQ1[I_PEAK]); x0, x1 = nx(NB_Y[I_PEAK]), nx(NB_Y[I_REC])
        dashed(img, (x0, yp), (x0 + (x1 - x0) * kr, yp), AMBER, a * 0.7)
        text(img, '15 年才回到原位', (x0 + x1) / 2 + 80, yp - 26, 26, 'serif_bold', AMBER, a * kr)
    ku = ke(t, tu - 0.1, 0.4)
    if ku > 0:
        text(img, '纳斯达克', nx(2015.6) + 6, ny(NQ1[-1]) + 30, 24, 'sans_med', ICE, a * ku, 'r')
        text(img, '伯克希尔股价', nx(2015.6) + 6, ny(BK1[-1]) - 30, 24, 'sans_med', GOLD_HI, a * ku, 'r')
        sp = np.prod([1 + BRK_TABLE[y][1] / 100 for y in (2000, 2001, 2002)]) - 1
        bk = np.prod([1 + BRK_TABLE[y][0] / 100 for y in (2000, 2001, 2002)]) - 1
        text(img, '泡沫破裂的三年（2000–2002）', W / 2, 1238, 26, 'sans_med', INK2, a * ku, track=0.12)
        for x, lab, v, col in ((310, '标普 500', sp, AMBER), (770, '伯克希尔股价', bk, GOLD_C)):
            rrect(img, x - 205, 1268, x + 205, 1368, 10, col, a * ku * 0.85, 1)
            text(img, lab, x - 70, 1318, 30, 'sans_med', INK2, a * ku)
            text(img, f'{v * 100:+.1f}%', x + 95, 1318, 46, 'corm_med', col if col is AMBER else GOLD_HI, a * ku, glow=0.2)
    text(img, '数据：Yahoo Finance 每日收盘（价格，不含股息）；年度涨跌取自伯克希尔 2018 年致股东信附表', W / 2, 1160, 16, 'sans',
         INK3 * 1.5, a * 0.9)


# ---------------------------------------------------------------- I10：前提——看懂企业；不借钱；不急着卖。否则下跌是灾难
def i10_a(t): return sc(t, B_COND, B_TODAY)


def dia_i10(L, t):
    a = i10_a(t)
    if a <= 0: return
    tz = wt('I10', '灾难')
    shock(L, (W / 2, 1180), t, tz - 0.05, AMBER, a, rmax=520, life=1.0, flatten=0.3)


def txt_i10(img, t, subs):
    a = i10_a(t)
    if a <= 0: return
    header(img, '前提 · CONDITIONS', a)
    rows = (('不借钱', '不借钱', '“…unless you own your shares on borrowed money…”'),
            ('不急着卖', '不急着卖', '“…or are going to sell them in a very short period of time”'),
            ('看懂', '真正看懂企业', '“If you’re right about the businesses…”'))
    for i, (kw, s, en) in enumerate(rows):
        k = max(ke(t, wt('I10', kw) - 0.15, 0.4), 0.3)
        y = 520 + i * 165
        panel(img, 110, y - 70, 970, y + 70, a * k, col=GOLD_C, fill=0.6)
        text(img, f'0{i + 1}', 180, y, 44, 'corm_med', SUB_GOLD, a * k)
        text(img, s, 250, y - 14, 54, 'serif_black', a=a * k, gold=True, anchor='l', glow=0.25 * math.exp(-max(t - wt('I10', kw), 0) / 0.4))
        text(img, en, 252, y + 38, 22, 'ebg_i', INK2, a * k, 'l')
        kt = ke(t, wt('I10', kw) - 0.15, 0.4)
        circle(img, (905, y), 24, GOLD_HI, a * k, 2); tick(img, (905, y), 20, GOLD_HI, a * kt)
    text(img, '英文均为巴菲特在上面这段问答里的原话', W / 2, 1000, 20, 'sans', INK3 * 1.6, a * ke(t, wt('I10', '看懂') + 0.4), track=0.04)
    to, tz = wt('I10', '否则'), wt('I10', '灾难')
    ko = ke(t, to - 0.1, 0.4)
    if ko > 0:
        panel(img, 110, 1080, 970, 1300, a * ko, col=AMBER, fill=0.75)
        text(img, '否则——', W / 2, 1130, 34, 'sans_med', INK2, a * ko, track=0.2)
        text(img, '下跌不是机会', W / 2, 1200, 50, 'serif_black', INK, a * ke(t, wt('I10', '下跌') - 0.1, 0.4))
        fx.slam(img, '而是灾难', W / 2, 1262, 56, 'serif_black', t, tz - 0.05, a, gold=False, col=AMBER, glow_=0.4)
        if tz - 0.05 < t < tz + 0.5: fx.glitch(img, (110, 1080, 970, 1300), t, 0.8 * (1 - (t - tz + 0.05) / 0.55), seed=31)


# ---------------------------------------------------------------- I11：下一次市场大跌，先问——是这门生意变了，还是只是价格打了折？
_rt = np.random.default_rng(37)
TODAY_DROP = np.r_[np.linspace(0, 0.05, 10), np.linspace(0.05, -0.30, 22)] + _rt.normal(0, 0.012, 32)


def i11_a(t): return sc(t, B_TODAY, B_CLOSE)


def dia_i11(L, t):
    a = i11_a(t)
    if a <= 0: return
    for kw, y in (('生意变了', 1000), ('打了折', 1210)):
        shock(L, (W / 2, y), t, wt('I11', kw) - 0.05, AMBER if kw == '生意变了' else GOLD_H, a, rmax=520, life=0.9, flatten=0.22)


def txt_i11(img, t, subs):
    a = i11_a(t)
    if a <= 0: return
    header(img, 'TODAY · 下一次大跌', a)
    panel(img, 90, 380, 990, 760, a, col=AMBER, title='下一次市场大跌', en='the next big decline')
    xs = np.linspace(150, 930, 32)
    ys = 520 - TODAY_DROP * 600
    k = eio((t - B_TODAY - 0.2) / 1.6)
    n = max(2, int(32 * k))
    area(img, np.c_[xs[:n], ys[:n]], 740, AMBER, a * 0.6, top=0.18)
    gline(img, np.c_[xs[:n], ys[:n]], ICE, a, th=4)
    fx.slam(img, '−30%', 850, 570, 60, 'corm_med', t, B_TODAY + 1.7, a, gold=False, col=AMBER, glow_=0.3)
    text(img, '示意', 960, 745, 18, 'sans', INK3 * 1.5, a * 0.8, 'r')
    tf = wt('I11', '先问')
    text(img, '先别急着害怕，问问自己', W / 2, 840, 36, 'sans_med', INK2, a * ke(t, tf - 0.1), track=0.2)
    for i, (kw, s_, sub, col, y) in enumerate((('生意变了', '是这门生意变了？', '护城河、利润、管理层还在不在', AMBER, 1000),
                                               ('打了折', '还是只是价格打了折？', '生意没变——同样的钱买到更多', GOLD_C, 1210))):
        kk = ke(t, wt('I11', kw) - 0.35, 0.4)
        if kk <= 0: continue
        panel(img, 110, y - 85, 970, y + 85, a * kk, col=col, fill=0.6)
        text(img, f'0{i + 1}', 175, y - 10, 44, 'corm_med', SUB_GOLD, a * kk)
        fx.slam(img, s_, W / 2 + 40, y - 18, 60, 'serif_black', t, wt('I11', kw) - 0.35, a, gold=col is GOLD_C, col=None if col is GOLD_C else AMBER,
                glow_=0.35)
        text(img, sub, W / 2 + 40, y + 46, 26, 'sans', INK2, a * ke(t, wt('I11', kw) + 0.6), track=0.06)


# ---------------------------------------------------------------- 收尾：在星图里向前飞行，越来越快；高潮重拍上全部亮起
_rn = np.random.default_rng(55)
NET3 = np.c_[_rn.uniform(-5, 5, 1400), _rn.uniform(-8, 8, 1400), _rn.uniform(-90, 2, 1400)]
NET3_C = _rn.random(1400)
NET3_E = []
for _i in range(0, 1400, 3):
    _dd = np.linalg.norm(NET3 - NET3[_i], axis=1); _dd[_i] = 1e9
    NET3_E.append((_i, int(np.argmin(_dd))))
CLOSE_T1 = T_SUM - 0.4


def fly_z(t):
    u = max(0.0, t - B_FLY)
    U = CLOSE_T1 - B_FLY
    wd = min(6.0, U)
    return 4.0 - (1.2 * u + 34.0 * max(0.0, (u - (U - wd)) / wd) ** 3)


def fly_cam(t):
    return Cam((0.3 * math.sin(t * 0.2), 0.0, fly_z(t)), yaw=0.03 * math.sin(t * 0.3), cy=880, f=900)


def dia_close(L, t):
    a = env(t, B_FLY, CLOSE_T1, 0.9, 0.12) * (1 - 0.6 * i11_a(t))
    if a <= 0: return
    cam = fly_cam(t); pc = fly_cam(t - 2.5 / 30)
    gold = NET3_C > 0.72
    pts3d(L, cam, NET3[gold], GOLD_H, 1.4 * a, ref=6.0, prev_cam=pc, trail=1.2)
    pts3d(L, cam, NET3[~gold], ICE, 1.1 * a, ref=6.0, prev_cam=pc, trail=1.2)
    xy, d = cam.proj(NET3)
    for i, j in NET3_E:
        if 0.6 < d[i] < 16 and 0.6 < d[j] < 16:
            hair(L, [xy[i], xy[j]], FOG, 0.22 * a * min(1, 6 / d[i]))


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


# ================================================================ 一句话总结 + 品牌片尾（系列固定片尾）
SUM_LINES = (('最怕的不是熊市，', 880), ('而是长期的疯狂。', 1010))


def summary_masks():
    out = []
    for s, y in SUM_LINES:
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
    w1 = eo((t - VOD['M']['t0'] + 0.1) / 1.0); w2 = eo((t - wt('M', '而是') + 0.05) / 1.0)
    sh = cl((t - VOD['M']['t1'] - 0.2) / 1.4) if VOD['M']['t1'] + 0.2 < t < VOD['M']['t1'] + 1.6 else None
    for (s, y), w in zip(SUM_LINES, (w1, w2)):
        gold_title(img, s, W / 2, y, 96, a, wipe=w, shine=sh, track=0.04)
    text(img, '伯克希尔股东大会投资智慧录 · 第三集', W / 2, 1150, 26, 'sans', INK2, a * eo((k - 1.2) / 0.8), track=0.1)


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





# ---------------------------------------------------------------- 片尾互动问题（在品牌片尾之前）
def txt_endq(img, t, subs):
    a = env(t, ENDQ_T['t0'] - 0.3, END['t_particles'] + 0.2, 0.4, 0.5)
    if a <= 0: return
    panel(img, 90, 1220, 990, 1470, a, col=GOLD_C, fill=0.85)
    fx.slam(img, '如果明天市场大跌三成，', W / 2, 1290, 46, 'serif_bold', t, ENDQ_T['t0'] - 0.05, a, gold=False, col=INK, glow_=0.15)
    fx.slam(img, '你会害怕，还是高兴？', W / 2, 1368, 56, 'serif_black', t, wt('Q', '你会') - 0.05, a, glow_=0.3)
    text(img, '在评论区说说你的答案', W / 2, 1430, 24, 'sans', INK2, a * ke(t, ENDQ_T['t0'] + 3.0), track=0.2)


# ================================================================ 合成一帧
DIAS = [dia_cold, dia_title, dia_s1, dia_s2, dia_s3, dia_ctx, dia_qa, dia_quote, dia_i1, dia_cape, dia_bub, dia_i10, dia_i11,
        dia_close, dia_sum]
TXTS = [txt_cold, txt_title, txt_s1, txt_s2, txt_s3, txt_ctx, txt_qa, txt_quote, txt_card, txt_i1, txt_cape, txt_bub, txt_i10,
        txt_i11, txt_sum, txt_endq]


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
        narr_sub(img, t, INS['subs'])
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
