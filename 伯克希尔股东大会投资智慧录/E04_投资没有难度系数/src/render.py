"""《伯克希尔股东大会投资智慧录》第四集 · 投资没有难度系数 —— 逐帧渲染（1080×1920，30fps）。

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
from script import BROLL, CLIP_LEN, QUOTE_ID, BET, BET_FINAL

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


I = {k: V(k) for k in ('I1', 'I2', 'I3', 'I5', 'I6', 'I7', 'I8', 'I10', 'I11')}
HOOK = TL['hook']


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
    text(img, '第四集 · 投资没有难度系数', 72, 66, 26, 'sans_med', SUB_GOLD, a * 0.95, 'l', track=0.12, shadow=0.3)
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
        hw = text_w('第四集 · 投资没有难度系数', 'sans_med', 38, 0.14) / 2 + 40
        rrect(img, W / 2 - hw, 1196, W / 2 + hw, 1268, 6, SUB_GOLD, ea * 0.55, 1)
        text(img, '第四集 · 投资没有难度系数', W / 2, 1232, 38, 'sans_med', INK, ea, track=0.14)
    fx.burst(img, t, T_TITLE, (W / 2, 900), a * 0.8, n=70, speed=640, life=1.4, seed=2)


# ================================================================ 开场钩子（第 0 秒）+ 开场口播：上方是 1994 年大会影像，下方是图表面板
FOOT_Y = 540


def intro_a(t):
    return env(t, V('S2')['t0'] - 0.4, T_CTX - 0.3, 0.5, 0.6)


def hook_a(t):
    return 1.0 - eio((t - (T_TITLE - 0.45)) / 0.4)


# 钩子：研究得越复杂、模型越精密，就越能赚钱吗？（先共情，再给视角；第 0 帧即可读，克制）
_rh = np.random.default_rng(31)
HOOK_N = 14                                               # 示意：越堆越多、越缠越乱的模型曲线
HOOK_L = [np.cumsum(_rh.normal(0, 1, 60)) * (0.6 + 0.7 * _rh.random()) for _ in range(HOOK_N)]
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
        clip = CLIPS[BROLL[0]] if t < V('S3')['t0'] - 0.2 else CLIPS[BROLL[1]]
        ct = (t - V('S2')['t0'] + 1.0) % 15.5
        foot(img, clip, ct, W / 2, FOOT_Y, a, zoom=1.05 + 0.006 * ct, blur=0.5)
        text(img, '1994 · 奥马哈 · 伯克希尔股东大会上午场实况', 72, FOOT_Y - WIN_H / 2 - 30, 22, 'sans', INK2, a * 0.85, 'l', track=0.06, shadow=0.5)
    ap = hook_a(t)
    if ap <= 0: return
    zs = 1.0 + 0.04 * (1 - eo(t / 0.6))
    tq = wt('S1', '赚钱')
    text(img, '研究得越复杂、模型越精密——', W / 2, 400, int(44 * zs), 'sans_med', INK2, ap, track=0.1, shadow=0.6)
    text(img, '就越能赚钱？', W / 2, 530, int(92 * zs), 'serif_black', a=ap, gold=True,
         glow=0.2 + 0.3 * math.exp(-max(t - tq, 0) / 0.8) * (t > tq), shadow=0.7)
    # 选股功课：模型曲线越堆越多，缠成一团（示意）
    x0, y0, x1, y1 = HOOK_BOX
    panel(img, x0, y0, x1, y1, ap, col=ICE, title='你的选股功课', en='your homework', fill=0.78)
    k = 0.15 + 0.85 * eio((t - 0.1) / max(wt('S1', '精密') + 0.6, 1.0))
    xs = np.linspace(x0 + 50, x1 - 50, 60)
    yc = (y0 + 140 + y1 - 60) / 2
    nl = max(1, int(HOOK_N * k))
    for i in range(nl):
        ys = yc + HOOK_L[i] * 9 * (0.6 + 0.4 * k)
        ys = np.clip(ys, y0 + 120, y1 - 40)
        col = (ICE, FOG, AMBER)[i % 3]
        gline(img, np.c_[xs, ys], col, ap * (0.35 + 0.4 * (i == nl - 1)), th=2, halo=4.0)
    for j, (lab, kw) in enumerate((('研报', '研究'), ('模型', '模型'), ('变量', '精密'))):
        kk = ke(t, wt('S1', kw) - 0.1, 0.4)
        if kk > 0:
            rrect(img, x0 + 40 + j * 150, y0 + 70, x0 + 170 + j * 150, y0 + 110, 6, ICE, ap * kk * 0.7, 1)
            text(img, f'{lab} ＋', x0 + 105 + j * 150, y0 + 90, 22, 'sans_med', ICE, ap * kk)
    text(img, '示意', x1 - 10, y1 - 16, 18, 'sans', INK3 * 1.5, ap * 0.8, 'r')
    ta = wt('S1', '巴菲特')
    kb = ke(t, ta - 0.15, 0.6)
    if kb > 0:
        panel(img, 110, 1210, 970, 1380, ap * kb, col=GOLD_C, fill=0.8)
        text(img, '巴菲特的回答——', W / 2, 1255, 32, 'sans_med', INK2, ap * kb, track=0.12)
        kc = ke(t, wt('S1', '松一口气') - 0.2, 0.7)
        text(img, '也许会让你松一口气', W / 2, 1325, 56, 'serif_black', a=ap * kc, gold=True, glow=0.25, wipe=kc)


# ---------------------------------------------------------------- S2：1994 年春天，宝洁为两笔复杂的利率掉期平仓，一个季度亏掉 1.57 亿美元
def s2_a(t): return env(t, V('S2')['t0'] - 0.1, V('S3')['t0'] - 0.2, 0.35, 0.35)


def dia_s2(L, t):
    a = s2_a(t)
    if a <= 0: return
    shock(L, (W / 2, 1245), t, wt('S2', '一点五七') - 0.05, AMBER, a, rmax=460, life=1.0, flatten=0.35)


def swap_loop(img, cx, cy, r, t, a, k):
    """利率掉期示意：两条方向相反的弧线交换现金流；k 越大，弧线越多、越缠"""
    n = 1 + int(5 * k)
    for i in range(n):
        rr = r * (1 - 0.13 * i)
        ph = t * (0.9 + 0.35 * i) * (1 if i % 2 == 0 else -1) + i
        th = np.linspace(ph, ph + math.pi * 1.35, 40)
        pts = np.c_[cx + rr * np.cos(th), cy + rr * 0.55 * np.sin(th)]
        col = ICE if i % 2 == 0 else AMBER
        gline(img, pts, col, a * (0.9 - 0.1 * i), th=3 if i < 2 else 2, halo=5.0)
        tip, prev = pts[-1], pts[-4]
        d = (tip - prev) / (np.linalg.norm(tip - prev) + 1e-6)
        nrm = np.array([-d[1], d[0]])
        poly(img, [tuple(tip - d * 14 + nrm * 8), tuple(tip), tuple(tip - d * 14 - nrm * 8)], col, a * (0.9 - 0.1 * i), 2)


def txt_s2(img, t, subs):
    a = s2_a(t)
    if a <= 0: return
    panel(img, 110, 800, 970, 1340, a, col=ICE, title='1994 年 1–3 月 · 宝洁公司', en='procter & gamble · quarterly report')
    tc, tm = wt('S2', '复杂'), wt('S2', '一点五七')
    k = eio((t - tc + 0.2) / 1.2)
    swap_loop(img, W / 2, 1060, 200, t, a, k)
    text(img, '固定利率', W / 2 - 250, 1060, 26, 'sans_med', ICE, a, 'r')
    text(img, '浮动利率', W / 2 + 250, 1060, 26, 'sans_med', AMBER, a, 'l')
    kc = ke(t, tc - 0.1, 0.4)
    if kc > 0:
        for j, s_ in enumerate(('两笔利率掉期', '杠杆')):
            x = W / 2 + (j - 0.5) * 300
            rrect(img, x - 120, 900, x + 120, 950, 8, ICE, a * kc * 0.75, 1)
            text(img, s_, x, 925, 24, 'sans_med', ICE, a * kc, track=0.06)
    fx.slam(img, '−1.57 亿美元', W / 2, 1245, 76, 'corm_med', t, tm - 0.05, a, gold=False, col=AMBER, glow_=0.45)
    text(img, '税前 · 为两笔利率掉期平仓（宝洁 1994 年 1–3 月季度报告）', W / 2, 1312, 22, 'sans', INK2, a * ke(t, tm + 0.5), track=0.04)
    if tm - 0.05 < t < tm + 0.45: fx.glitch(img, (110, 880, 970, 1180), t, 0.7 * (1 - (t - tm + 0.05) / 0.5), seed=6)


# ---------------------------------------------------------------- S3：几周后的股东大会 + 股东的提问
def s3_a(t): return env(t, V('S3')['t0'] - 0.2, T_CTX - 0.3, 0.4, 0.6)


def dia_s3(L, t):
    a = s3_a(t)
    if a <= 0: return
    tq = wt('S3', '不确定')
    shock(L, (W / 2, 1230), t, tq - 0.05, GOLD_H, a, rmax=560, life=1.2, flatten=0.3)


def txt_s3(img, t, subs):
    a = s3_a(t)
    if a <= 0: return
    k0 = ke(t, V('S3')['t0'], 0.6)
    text(img, '1994.04.25', W / 2, 930, 120, 'corm_med', a=a * k0, gold=True, glow=0.15)
    text(img, '奥马哈 · 伯克希尔股东大会', W / 2, 1020, 30, 'sans_med', INK2, a * k0, track=0.2)
    tn, tq = wt('S3', '耐克'), wt('S3', '不确定')
    fx.slam(img, '“耐克、锐步这样的全球品牌，', W / 2, 1180, 56, 'serif_black', t, tn - 0.05, a, gold=False, col=INK, glow_=0.2)
    fx.slam(img, '前景有哪些不确定性？”', W / 2, 1280, 68, 'serif_black', t, tq - 0.05, a, glow_=0.35)
    for kw, s, x in (('耐克', 'NIKE', 360), ('锐步', 'REEBOK', 720)):
        kk = ke(t, wt('S3', kw) + 0.1, 0.4)
        if kk > 0:
            rrect(img, x - 130, 1360, x + 130, 1430, 8, ICE, a * kk * 0.8, 1)
            text(img, s, x, 1395, 30, 'inter_semi', ICE, a * kk, track=0.2)


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
    text(img, 'CNBC 巴菲特档案 · 第 38–39 章', W / 2, 965, 28, 'sans', INK2, a * eo((k - 0.7) / 0.7), track=0.06)
    text(img, '“You don’t have to do exceptional things to get exceptional results”', W / 2, 1025, 28, 'ebg_i', INK, a * eo((k - 0.8) / 0.7))
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
    for sc_, sid, d, y, col in (('ask', 'Q4A', 0.4, 1225, GOLD_H), ('pi', 'A11', 2.6, 1130, GOLD_H), ('labels', 'M3', 0.6, 1160, AMBER),
                                ('bar', 'A14', 0.3, 1300, GOLD_H), ('coke', 'A16', 1.0, 1065, GOLD_H), ('wrong', 'A21', 0.9, 1110, GOLD_H)):
        s = qa_env(t, sc_) * a
        if s > 0: shock(L, (W / 2, y), t, qs(sid, d), col, s, rmax=420, life=1.1, flatten=0.3)


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
    spk = '查理·芒格' if mt - 0.3 <= t < me - 0.3 else ('沃伦·巴菲特' if t >= at - 0.2 else '提问 · 来自纽约的股东')
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


def chip(img, x, y, s, col, a, w=None, size=28, font='inter_semi', track=0.16):
    if a <= 0.003: return
    hw = (w or (text_w(s, font, size, track) + 60)) / 2
    rrect(img, x - hw, y - 32, x + hw, y + 32, 8, col, a * 0.8, 1)
    text(img, s, x, y, size, font, col, a, track=track)


def qa_panels(img, t, a):
    """关键观点面板（y 860–1350）"""
    # 提问：伯克希尔偏爱的全球品牌 vs 制鞋业的全球品牌——它们有哪些不确定性？
    ka = qa_env(t, 'ask') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='股东的问题', en='the question')
        k2 = ke(t, qs('Q2', 0.6), 0.5)
        text(img, '伯克希尔偏爱的全球品牌', 310, 975, 26, 'sans_med', INK2, ka * k2, track=0.06)
        chip(img, 310, 1040, 'COCA-COLA', GOLD_C, ka * ke(t, qs('Q2', 5.0), 0.4), w=300)
        chip(img, 310, 1115, 'GILLETTE', GOLD_C, ka * ke(t, qs('Q2', 5.8), 0.4), w=300)
        k3 = ke(t, qs('Q3', 0.4), 0.5)
        text(img, '制鞋业的全球品牌', 770, 975, 26, 'sans_med', INK2, ka * k3, track=0.06)
        chip(img, 770, 1040, 'NIKE', ICE, ka * ke(t, qs('Q3', 2.4), 0.4), w=300)
        chip(img, 770, 1115, 'REEBOK', ICE, ka * ke(t, qs('Q3', 3.0), 0.4), w=300)
        fx.slam(img, '它们有哪些不确定性？', W / 2, 1225, 54, 'serif_black', t, qs('Q4A', 0.4), ka, glow_=0.3)
        text(img, '竞争优势 · 生意的经济特性 · 消费者行为 · 其他风险', W / 2, 1295, 24, 'sans', INK2, ka * ke(t, qs('Q4A', 2.2), 0.6), track=0.06)
    # 巴菲特：看不清耐克、锐步 10–20 年的竞争地位；看得懂布朗与德克斯特
    ka = qa_env(t, 'nike') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='巴菲特的回答', en="buffett's answer")
        text(img, '竞争地位能不能持续 10–20 年？', W / 2, 965, 30, 'sans_med', INK2, ka * ke(t, qs('A5A', 1.0)), track=0.06)
        for x, names, verdict, col, sid, d in ((310, ('NIKE', 'REEBOK'), '看不清', ICE, 'A5A', 2.4), (770, ('BROWN', 'DEXTER'), '看得懂', GOLD_C, 'A5B', 1.4)):
            kk = ke(t, qs(sid, d), 0.5)
            if kk <= 0: continue
            panel(img, x - 200, 1010, x + 200, 1200, ka * kk, col=col, fill=0.55)
            text(img, names[0], x, 1050, 30, 'inter_semi', col, ka * kk, track=0.2)
            text(img, names[1], x, 1092, 30, 'inter_semi', col, ka * kk, track=0.2)
            if col is ICE: text(img, verdict, x, 1155, 48, 'serif_black', ICE, ka * kk, glow=0.15)
            else: text(img, verdict, x, 1155, 48, 'serif_black', a=ka * kk, gold=True, glow=0.2)
        k8 = ke(t, qs('A8', 0.6), 0.5)
        text(img, '对我们：更难理解，更难拿准', W / 2, 1250, 30, 'sans_med', INK, ka * k8 * (1 - 0.5 * ke(t, qs('A9'), 0.4)), track=0.04)
        text(img, '对更懂那一行的人：也许更容易', W / 2, 1305, 30, 'sans_med', GOLD_C, ka * ke(t, qs('A9', 0.6), 0.5), track=0.04)
    # 宁可乘以 3，也不乘以 π
    ka = qa_env(t, 'pi') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='查理和我不喜欢难题', en="we don't like difficult problems")
        k0 = ke(t, qs('A10', 0.4), 0.5)
        text(img, '有些企业，比别的企业容易理解得多', W / 2, 975, 32, 'sans_med', INK2, ka * k0, track=0.04)
        t3 = qs('A11', 2.6)
        k3 = ke(t, t3, 0.4)
        if k3 > 0:
            text(img, '× 3', 330, 1130, 130, 'corm_med', a=ka * k3, gold=True, glow=0.3)
            dig = '3.14159265358979323846264338327950288'
            nd = min(len(dig), 4 + int(max(0.0, t - t3 - 0.6) * 9))
            kp = ke(t, t3 + 0.6, 0.4)
            text(img, '× π', 750, 1110, 110, 'corm_med', ICE, ka * kp * 0.75)
            text(img, '= ' + dig[:nd] + '…', 750, 1195, 24, 'inter', ICE, ka * kp * 0.7)
            text(img, '“宁可乘以 3，也不乘以 π”', W / 2, 1290, 34, 'serif_bold', INK, ka * ke(t, t3 + 1.6, 0.5))
    # 芒格：雇一个头衔合适的人，就能做成很难的事？——最危险的想法之一；保持简单，就不必把思考外包
    ka = qa_env(t, 'labels') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='芒格的补充', en="munger's addendum")
        k2 = ke(t, qs('M2', 1.0), 0.5)
        text(img, '雇一个头衔合适的人，就能做成很难的事？', W / 2, 975, 32, 'sans_med', INK2, ka * k2 * (1 - 0.5 * ke(t, qs('M7'), 0.4)), track=0.02)
        for i, s_ in enumerate(('博士', '顾问', '专家', '名校')):
            chip(img, 245 + i * 197, 1060, s_, ICE, ka * ke(t, qs('M2', 3.0 + 0.35 * i), 0.3) * (1 - 0.6 * ke(t, qs('M7'), 0.4)), w=160, size=28,
                 font='sans_med', track=0.1)
        fx.slam(img, '最危险的想法之一', W / 2, 1160, 60, 'serif_black', t, qs('M3', 0.6), ka * (1 - 0.65 * ke(t, qs('M7'), 0.4)), gold=False, col=AMBER, glow_=0.35)
        k7 = ke(t, qs('M7', 0.2), 0.5)
        if k7 > 0:
            line(img, (W / 2 - 300 * k7, 1215), (W / 2 + 300 * k7, 1215), GOLD_C, ka * 0.6, 1)
            text(img, '保持简单，就不必把思考外包', W / 2, 1275, 46, 'serif_black', a=ka * k7, gold=True, glow=0.2, wipe=k7)
    # 跨过一尺的栏 vs 跳过七尺的栏：在投资里，绶带一样值钱
    ka = qa_env(t, 'bar') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='投资没有难度系数', en='no degree-of-difficulty bonus')
        fx.slam(img, '不必做非凡的事，也能取得非凡的结果', W / 2, 965, 34, 'serif_bold', t, qs('A12B', 0.2), ka * (1 - ke(t, qs('A13', 2.2), 0.4)),
                gold=False, col=INK, glow_=0.15)
        yb = 1235
        tq = qs('A14', 0.3)
        same = ke(t, tq, 0.6)
        for x, hft, lab, col, sid, d in ((330, 1, '一尺', GOLD_C, 'A13', 6.4), (750, 7, '七尺', ICE, 'A13', 2.6)):
            kk = ke(t, qs(sid, d), 0.5)
            if kk <= 0: continue
            h = hft * 26 * kk
            line(img, (x - 110, yb), (x - 110, yb - h - 6), INK2, ka * 0.8, 3)
            line(img, (x + 110, yb), (x + 110, yb - h - 6), INK2, ka * 0.8, 3)
            line(img, (x - 115, yb - h), (x + 115, yb - h), col, ka, 6)
            glow(img, (x, yb - h), 40, col * 0.4, ka * 0.5)
            text(img, lab, x - 150, yb - 14, 28, 'serif_bold', col, ka * kk, 'r')
            # 绶带：人们以为七尺的更值钱（A13）→ 实际上一样（A14）
            r = (30 if hft == 1 else 30 + 26 * (1 - same)) * kk
            cy = 990
            circle(img, (x, cy), r, col, ka * kk, 3)
            glow(img, (x, cy), r * 1.3, col * 0.5, ka * kk * 0.5)
            text(img, '$', x, cy + 2, int(r * 1.1), 'corm_med', col, ka * kk)
        text(img, '人们以为：跳得越高，绶带越值钱', W / 2, 1300, 24, 'sans', INK2, ka * env(t, qs('A13', 3.0), tq + 0.2, 0.4, 0.3), track=0.06)
        fx.slam(img, '在投资里，完全不是这样', W / 2, 1300, 38, 'serif_black', t, tq, ka, glow_=0.3)
    # 可口可乐：几百万人都懂，只是没行动——却让伯克希尔多了 30 亿美元税前收益
    ka = qa_env(t, 'coke') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='“这有什么复杂的？”', en='coca-cola')
        k5 = ke(t, qs('A15', 2.4), 0.5)
        text(img, '可口可乐', W / 2, 975, 34, 'serif_bold', INK, ka * k5, track=0.1)
        k6 = ke(t, qs('A16', 1.0), 0.4)
        if k6 > 0:
            v = 30 * eio((t - qs('A16', 1.0)) / 1.4)
            text(img, f'+{v:.0f} 亿美元', W / 2, 1065, 80, 'corm_med', a=ka * k6, gold=True, glow=0.25)
            text(img, '税前 · 1993 年底持股成本 10.24 亿 → 市值 41.68 亿', W / 2, 1130, 22, 'sans', INK2, ka * ke(t, qs('A16', 2.6), 0.5), track=0.04)
        for i, s_ in enumerate(('产品', '分销体系', '财务')):
            chip(img, 290 + i * 250, 1200, s_, ICE, ka * ke(t, qs('A17A', 1.2 + 1.0 * i), 0.4) * (1 - 0.5 * ke(t, qs('A18'), 0.4)), w=200, size=28,
                 font='sans_med', track=0.1)
        text(img, '几十万、几百万人都懂', W / 2, 1265, 26, 'sans_med', INK2, ka * env(t, qs('A17B', 1.0), qs('A18', 0.2), 0.5, 0.3), track=0.06)
        fx.slam(img, '他们只是什么也没做', W / 2, 1275, 50, 'serif_black', t, qs('A18', 0.1), ka, glow_=0.3)
    # 复杂的生意：一千页的报告、一群博士——你还是看不懂它 10–15 年后的样子
    ka = qa_env(t, 'report') * a
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='一门复杂的生意', en='a complicated business')
        kp = eio((t - qs('A19A', 2.0)) / 3.0)
        n = int(1000 * kp)
        for i in range(int(18 * kp)):                       # 一摞越堆越厚的报告
            y = 1210 - i * 10
            rect(img, 250, y, 480, y + 8, ICE * (0.5 + 0.03 * i), ka * 0.55)
        text(img, f'{n:,} 页', 365, 960, 52, 'corm_med', ICE, ka * ke(t, qs('A19A', 2.0), 0.4))
        kd = ke(t, qs('A19A', 5.5), 0.4)
        text(img, '博士 × N', 365, 1250, 30, 'sans_med', ICE, ka * kd, track=0.1)
        k20 = ke(t, qs('A20', 0.8), 0.5)
        if k20 > 0:
            text(img, '10–15 年后', 760, 1010, 44, 'serif_black', INK, ka * k20)
            text(img, '它会是什么样子？', 760, 1075, 34, 'sans_med', INK2, ka * k20)
            fx.slam(img, '？', 760, 1185, 120, 'serif_black', t, qs('A20', 2.2), ka, gold=False, col=AMBER, glow_=0.35)
        text(img, '“可那说明不了什么”', W / 2, 1305, 30, 'serif_bold', AMBER, ka * ke(t, qs('A19B', 2.0), 0.5))
    # 最重要的，是避免犯错
    ka = qa_env(t, 'wrong') * a * (1 - ke(t, T_QUOTE + 0.9, 0.3))
    if ka > 0:
        panel(img, PX0, PY0, PX1, PY1, ka, title='巴菲特', en='the big thing')
        fx.slam(img, '避免犯错', W / 2, 1110, 110, 'serif_black', t, qs('A21', 0.9), ka, glow_=0.45)


# ---------------------------------------------------------------- 问答收尾的金句卡：“这种错误，我们可犯不起。”（停留 2 秒以上）
T_QUOTE = qs(QUOTE_ID)


def quote_a(t):
    return env(t, T_QUOTE - 0.3, T_INS - 0.1, 0.25, 0.35)


def txt_quote(img, t, subs):
    a = quote_a(t)
    if a <= 0: return
    panel(img, 80, 830, 1000, 1390, a, col=GOLD_C, title='巴菲特 · 1994', en='warren buffett', fill=0.9)
    text(img, '一千页的报告、一群博士，都不如——', W / 2, 970, 32, 'sans_med', INK2, a, track=0.04)
    fx.slam(img, '最重要的，', W / 2, 1065, 80, 'serif_black', t, T_QUOTE - 0.2, a, glow_=0.3)
    fx.slam(img, '是避免犯错。', W / 2, 1170, 80, 'serif_black', t, T_QUOTE + 0.6, a, glow_=0.45)
    k = ke(t, T_QUOTE + 1.2, 0.6)
    text(img, '“The big thing to do is avoid being wrong.”', W / 2, 1262, 32, 'ebg_i', INK, a * k, shadow=0.6)
    text(img, '—— 沃伦·巴菲特，1994 年伯克希尔股东大会', W / 2, 1325, 24, 'sans', INK2, a * k, track=0.06)


def dia_quote(L, t):
    a = quote_a(t)
    if a <= 0: return
    shock(L, (W / 2, 1170), t, T_QUOTE + 0.6, GOLD_H, a, rmax=560, life=1.1, flatten=0.3)


# ================================================================ 投资启示（本片解读）：与前两集同款的标题转场
NOTE = '本片解读，非巴菲特或芒格原话'
T_INS_END = I['I11']['t1'] + 0.6


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
B_PRIN = NV['entry'] - 0.4                  # 全奏进入的重拍上亮起（I2 开口）
B_BET = b_before(I['I5']['t0'])
B_DEX = NV['dip'] - 0.4                     # 低音撤走的低谷：代价
B_TODAY = NV['ret'] - 0.4                   # 全奏回归：今天
B_CLOSE = b_before(I['I11']['t0'])
B_FLY = I['I11']['t0'] - 0.6                # 收尾句下面升起星图，一路推向高潮


def hurdle(img, x, yb, h, lab, col, a, k=1.0, wpost=110):
    """一副栏架：两根立柱 + 一根发光的横杆"""
    if a <= 0.003: return
    h = h * k
    line(img, (x - wpost, yb), (x - wpost, yb - h - 8), INK2, a * 0.8, 3)
    line(img, (x + wpost, yb), (x + wpost, yb - h - 8), INK2, a * 0.8, 3)
    line(img, (x - wpost - 6, yb - h), (x + wpost + 6, yb - h), col, a, 7)
    glow(img, (x, yb - h), 46, col * 0.4, a * 0.5)
    line(img, (x - wpost - 40, yb), (x + wpost + 40, yb), INK3 * 1.5, a * 0.6, 1)
    text(img, lab, x, yb + 36, 34, 'serif_bold', col, a)


def ribbon(img, x, y, r, col, a):
    if a <= 0.003: return
    for dx in (-0.45, 0.45):                                   # 两条飘带
        poly(img, [(x + dx * r * 0.6, y + r * 0.7), (x + dx * r * 1.0, y + r * 2.1), (x + dx * r * 0.25, y + r * 1.75)], col, a * 0.8, 2, closed=True)
    circle(img, (x, y), r, col, a, 3)
    glow(img, (x, y), r * 1.4, col * 0.5, a * 0.5)
    text(img, '$', x, y + 2, int(r * 1.15), 'corm_med', col, a)


# ---------------------------------------------------------------- I1：投资不按难度给分——一尺与七尺，回报一样
def i1_a(t): return sc(t, B_I1 if t > I['I1']['t0'] - 1 else 0, B_PRIN) * env(t, I['I1']['t0'] - 0.3, 1e9, 0.4, 0.1)


def dia_i1(L, t):
    a = i1_a(t)
    if a <= 0: return
    shock(L, (W / 2, 640), t, wt('I1', '拿到') - 0.05, GOLD_H, a, rmax=520, life=1.0, flatten=0.3)


def txt_i1(img, t, subs):
    a = i1_a(t)
    if a <= 0: return
    header(img, '概括 · 巴菲特的原意', a)
    panel(img, 90, 380, 990, 1160, a, col=GOLD_C, title='投资不按难度给分', en='no points for difficulty')
    yb = 1050
    for x, hft, lab, col, kw in ((300, 1, '一尺', GOLD_C, '一尺'), (780, 7, '七尺', ICE, '七尺')):
        k = ke(t, wt('I1', kw) - 0.2, 0.6)
        k0 = ke(t, I['I1']['t0'] + 0.3, 0.6) * 0.3
        hurdle(img, x, yb, hft * 50, lab, col, a * max(k, k0), k=max(eio((t - wt('I1', kw) + 0.2) / 0.7), 0.15))
        kr = ke(t, wt('I1', '回报') - 0.1, 0.5)
        ribbon(img, x, 560, 46, GOLD_HI if col is GOLD_C else ICE, a * kr)
    tq = wt('I1', '拿到')
    fx.slam(img, '＝', W / 2, 560, 90, 'serif_black', t, tq - 0.05, a, glow_=0.4)
    fx.slam(img, '回报一样', W / 2, 680, 50, 'serif_black', t, tq + 0.1, a, glow_=0.3)
    # 回声：1989 年致股东信与 1998、2005 年大会
    ke1 = ke(t, I['I1']['t0'] + 1.0, 0.6)
    panel(img, 90, 1200, 990, 1450, a * ke1, col=SUB_GOLD, title='一以贯之', en='echoes', fill=0.75)
    fx.typewriter(img, '“…one-foot hurdles that we could step over rather than … seven-footers.”', W / 2, 1300, 26, 'ebg_i', INK, a * ke1, t,
                  I['I1']['t0'] + 1.4, cps=40)
    text(img, '—— 巴菲特 1989 年致股东信', W / 2, 1345, 22, 'sans', INK2, a * ke(t, I['I1']['t0'] + 3.6, 0.6), track=0.06)
    text(img, '1998、2005 年大会上，他又用奥运跳水的“难度系数”讲了同一个道理', W / 2, 1400, 22, 'sans', SUB_GOLD,
         a * ke(t, I['I1']['t0'] + 5.0, 0.6), track=0.02)


# ---------------------------------------------------------------- I2–I3：第一性原理——市场只为结果付钱；环节越多，越容易错
CHAIN = [0.9 ** n for n in range(1, 11)]


def prin_a(t): return sc(t, B_PRIN, B_BET)


def dia_prin(L, t):
    a = prin_a(t)
    if a <= 0: return
    shock(L, (W / 2, 570), t, B_PRIN + 0.4, GOLD_H, a, rmax=640, life=1.2, flatten=0.45)
    shock(L, (cx_bar(9), 1060), t, wt('I3', '三成五') - 0.05, AMBER, a, rmax=300, life=1.0, flatten=0.6)


def cx_bar(i): return 200 + i * 75


def txt_prin(img, t, subs):
    a = prin_a(t)
    if a <= 0: return
    header(img, '第一性原理 · 市场只为结果付钱', a)
    panel(img, 90, 380, 990, 790, a, col=GOLD_C, title='你的回报，取决于', en='what your return depends on')
    kr = 1 - ke(t, wt('I2', '将来') - 0.5, 0.4)
    if kr > 0: fx.slam(img, '市场只为结果付钱', W / 2, 600, 64, 'serif_black', t, wt('I2', '结果') - 0.4, a * kr, glow_=0.35)
    for x, kw, big, en, col in ((300, '将来', '企业将来赚多少', 'WHAT IT EARNS', GOLD_C), (780, '当初', '你当初付多少', 'WHAT YOU PAY', ICE)):
        kk = ke(t, wt('I2', kw) - 0.2, 0.45)
        if kk <= 0: continue
        rrect(img, x - 215, 470, x + 215, 580, 10, col, a * kk * 0.85, 1)
        fx.slam(img, big, x, 512, 44, 'serif_black', t, wt('I2', kw) - 0.2, a, gold=col is GOLD_C, col=None if col is GOLD_C else ICE, glow_=0.3)
        text(img, en, x, 556, 20, 'inter_semi', col, a * kk, track=0.2)
    kd = ke(t, wt('I2', '难度') - 0.2, 0.4)
    if kd > 0:
        rrect(img, W / 2 - 150, 625, W / 2 + 150, 715, 10, AMBER, a * kd * 0.8, 1)
        text(img, '难度', W / 2 - 20, 670, 46, 'serif_black', AMBER, a * kd * 0.8)
        cross(img, (W / 2 + 90, 670), 22, BRICK * 1.4, a * kd)
        text(img, '没有这一项', W / 2, 752, 24, 'sans_med', INK2, a * kd, track=0.1)
    # 下：环节越多，全对的概率越低（每一环九成把握）
    t3 = I['I3']['t0']
    kc = ke(t, t3 - 0.3, 0.5)
    if kc <= 0: return
    ac = a * kc
    panel(img, 90, 830, 990, 1460, ac, col=GOLD_C, title='要同时猜对的环节越多', en='every link must hold')
    text(img, '每一环都有九成把握', W / 2, 935, 28, 'sans_med', INK2, ac * ke(t, wt('I3', '九成') - 0.2, 0.4), track=0.08)
    yb, hmax = 1330, 330
    t_a, t_b = wt('I3', '环节'), wt('I3', '十环')
    for i, p in enumerate(CHAIN):
        ti = t_a + (t_b - t_a) * i / 9
        k = ke(t, ti, 0.35)
        if k <= 0: continue
        x = cx_bar(i)
        col = GOLD_C if i == 0 else (AMBER if i == 9 else ICE)
        bar(img, x, yb, 48, p * hmax * k, col, ac * (0.85 if i in (0, 9) else 0.6))
        text(img, f'{i + 1}', x, yb + 28, 22, 'inter_semi', INK2, ac * k)
        circle(img, (x, 990), 10, col, ac * k, 2)                               # 链条上的一环
        if i: line(img, (x - 65, 990), (x - 10, 990), INK2, ac * k * 0.7, 2)
        if i in (0, 4):
            text(img, f'{p * 100:.0f}%', x, yb - p * hmax * k - 26, 30, 'corm_med', col, ac * k)
    text(img, '环节数', cx_bar(0) - 40, yb + 60, 20, 'sans', INK2, ac, 'l')
    t35 = wt('I3', '三成五')
    fx.slam(img, '十环全对：35%', cx_bar(9) - 110, 1080, 50, 'serif_black', t, t35 - 0.05, ac, gold=False, col=AMBER, glow_=0.35)
    text(img, '示意 · 0.9 的 n 次方（各环独立）', 960, 1440, 18, 'sans', INK3 * 1.5, ac * 0.85, 'r')


# ---------------------------------------------------------------- I5–I6：十年赌局（2008–2017）：最简单的指数基金 vs 两百多家对冲基金
def _cum(r):
    v, out = 1.0, [1.0]
    for x in r:
        if x is None: break
        v *= 1 + x / 100; out.append(v)
    return np.array(out)


BET_C = {k: _cum(v) for k, v in BET.items()}
BX0, BX1, BYB, BYT = 190, 860, 1370, 960
BYMAX = 2.4


def bx(i): return BX0 + i / 10 * (BX1 - BX0)
def by(v): return BYB - (v - 0.5) / (BYMAX - 0.5) * (BYB - BYT)


def bet_a(t): return sc(t, B_BET, B_DEX)


def dia_bet(L, t):
    a = bet_a(t)
    if a <= 0: return
    k = ke(t, wt('I5', '两百多') - 0.2, 0.6)
    if k > 0:                                                  # 两百多家对冲基金：一团冰青的点
        rng = np.random.default_rng(12)
        ang = rng.uniform(0, 2 * math.pi, 220); rr = np.sqrt(rng.random(220)) * 120
        xy = np.c_[770 + rr * np.cos(ang + t * 0.2) * 1.2, 660 + rr * np.sin(ang + t * 0.2) * 0.45]
        cloud(L, xy, ICE, 0.9 * a * k)
    shock(L, (bx(10), by(BET_C['SP'][-1])), t, wt('I6', '一百二十五') - 0.05, GOLD_H, a, rmax=240, life=1.0, flatten=0.7)


def txt_bet(img, t, subs):
    a = bet_a(t)
    if a <= 0: return
    header(img, '十年赌局 · 2008–2017', a)
    tb, tf = wt('I5', '标普'), wt('I5', '母基金')
    kb = ke(t, tb - 0.2, 0.5)
    panel(img, 90, 380, 520, 800, a * max(kb, 0.4), col=GOLD_C, title='巴菲特押', en='buffett', fill=0.65)
    if kb > 0:
        fx.slam(img, '标普 500', 305, 560, 56, 'serif_black', t, tb - 0.2, a, glow_=0.3)
        text(img, '指数基金', 305, 630, 34, 'serif_bold', GOLD_C, a * kb)
        text(img, '最简单的一跳', 305, 710, 26, 'sans_med', INK2, a * ke(t, tb + 0.8, 0.5), track=0.1)
    kf = ke(t, tf - 0.2, 0.5)
    panel(img, 560, 380, 990, 800, a * max(kf, 0.4), col=ICE, title='对手押', en='protégé partners', fill=0.65)
    if kf > 0:
        text(img, '5 只母基金', 775, 500, 40, 'serif_black', ICE, a * kf)
        text(img, '→ 两百多家对冲基金', 775, 755, 26, 'sans_med', INK2, a * ke(t, wt('I5', '两百多') - 0.1, 0.5), track=0.04)
    # 下：十年累计（2007 年底 = 1）
    t6 = I['I6']['t0']
    kc = ke(t, t6 - 0.6, 0.5)
    k0 = env(t, I['I5']['t0'] + 0.2, t6 - 0.4, 0.5, 0.4)
    if k0 > 0:
        fx.slam(img, '2008  →  2017', W / 2, 1060, 96, 'corm_med', t, I['I5']['t0'] + 0.2, a * k0, glow_=0.3)
        text(img, '十年之后，看谁赚得多', W / 2, 1170, 32, 'sans_med', INK2, a * k0 * ke(t, wt('I5', '十年的赌'), 0.5), track=0.12)
    if kc <= 0: return
    ac = a * kc
    panel(img, 90, 840, 990, 1470, ac, col=GOLD_C, title='十年累计', en='cumulative, end-2007 = 1')
    for v in (1.0, 1.5, 2.0):
        dashed(img, (BX0, by(v)), (BX1, by(v)), INK3, ac * 0.45, dash=6, gap=8)
        text(img, f'{v:g}', BX0 - 12, by(v), 20, 'inter', INK2, ac, 'r')
    for i, y in enumerate((2008, 2010, 2012, 2014, 2016)):
        text(img, str(y), bx(y - 2007), BYB + 28, 20, 'corm_med', INK2, ac)
    u = eio((t - t6 - 0.2) / max(wt('I6', '最好') - t6 - 0.2, 1.0)) * 10
    for key in ('A', 'B', 'C', 'D', 'E', 'SP'):
        c = BET_C[key]
        n = min(len(c), int(u) + 1)
        fr = u - int(u)
        pts = [(bx(i), by(c[i])) for i in range(n)]
        if n < len(c) and n >= 1 and u < 10:
            pts.append((bx(n - 1 + fr), by(c[n - 1] + (c[n] - c[n - 1]) * fr)))
        if len(pts) < 2: continue
        if key == 'SP': gline(img, pts, GOLD_HI, ac, th=5, halo=9.0)
        else: gline(img, pts, ICE, ac * 0.75, th=2, halo=5.0)
    kend = ke(t, wt('I6', '一百二十五') - 0.1, 0.4)
    if kend > 0:
        text(img, f'+{BET_FINAL["SP"]:.1f}%', bx(10) + 14, by(BET_C['SP'][-1]), 36, 'corm_med', a=ac * kend, gold=True, anchor='l', glow=0.2)
        text(img, '指数基金', bx(10) + 14, by(BET_C['SP'][-1]) + 36, 20, 'sans_med', GOLD_C, ac * kend, 'l')
    for key, kw, dy in (('C', '最好', -10), ('D', '最差', 18)):
        kk = ke(t, wt('I6', kw) - 0.1, 0.4)
        if kk <= 0: continue
        c = BET_C[key]; i = len(c) - 1
        circle(img, (bx(i), by(c[-1])), 7, ICE, ac * kk, fill=True)
        text(img, f'+{BET_FINAL[key]:.1f}%', bx(10) + 14, by(c[-1]) + dy, 30, 'corm_med', ICE, ac * kk, 'l')
    text(img, '2008 年五只母基金都跑赢指数；此后九年，每一年整体都落后', W / 2, 1418, 20, 'sans', INK2, ac * ke(t, wt('I6', '最差') + 1.0, 0.6), track=0.02)
    text(img, '数据：伯克希尔 2017 年致股东信（母基金 D 于 2017 年清盘，按九年计）', W / 2, 1450, 16, 'sans', INK3 * 1.5, ac * 0.9)


# ---------------------------------------------------------------- I7–I8：代价——最难的是分辨一尺与七尺：德克斯特鞋厂
def dex_a(t): return sc(t, B_DEX, B_TODAY)


def dia_dex(L, t):
    a = dex_a(t)
    if a <= 0: return
    shock(L, (W / 2, 900), t, wt('I7', '击垮') - 0.05, AMBER, a, rmax=520, life=1.0, flatten=0.35)
    shock(L, (760, 1150), t, wt('I8', '五十七亿') - 0.05, AMBER, a, rmax=360, life=1.0, flatten=0.5)


def txt_dex(img, t, subs):
    a = dex_a(t)
    if a <= 0: return
    header(img, '代价 · 最难的是分辨', a)
    panel(img, 90, 380, 990, 770, a, col=SUB_GOLD, title='哪是一尺？哪是七尺？', en='which bar is which?', fill=0.7)
    for x, lab in ((300, '一尺？'), (780, '七尺？')):
        k = ke(t, wt('I7', '一尺' if x == 300 else '七尺') - 0.2, 0.5)
        hurdle(img, x, 690, 150, lab, INK2, a * k * 0.8, k=1.0, wpost=95)
        hh = 150 * (0.55 + 0.45 * math.sin(t * 2.1 + x))                      # 横杆的高度看不准：上下浮动
        line(img, (x - 101, 690 - hh), (x + 101, 690 - hh), SUB_GOLD, a * k * 0.5, 3)
    kd = ke(t, wt('I7', '德克斯特') - 0.2, 0.5)
    if kd <= 0: return
    panel(img, 90, 810, 990, 1470, a * kd, col=AMBER, title='1993 · 德克斯特鞋厂', en='dexter shoe', fill=0.78)
    tz = wt('I7', '击垮')
    k_ok = 1 - ke(t, tz - 0.1, 0.3)
    text(img, '“我自认为看得懂”', W / 2, 905, 34, 'serif_bold', INK, a * kd * (0.35 + 0.65 * k_ok))
    text(img, '“…as well as I think I understand the position of Brown and Dexter.” —— 本段原声', W / 2, 950, 20, 'ebg_i', INK2, a * kd * k_ok)
    kh = ke(t, wt('I7', '海外') - 0.2, 0.4)
    if kh > 0:
        fx.slam(img, '海外竞争 → 竞争优势没几年就消失', W / 2, 1000, 36, 'serif_black', t, wt('I7', '海外') - 0.2, a * kd, gold=False, col=AMBER, glow_=0.3)
    if t > tz - 0.1: fx.shards(img, t, tz - 0.05, (150, 870, 930, 970), AMBER, a * kd * 0.8, n=28, seed=5)
    # 付出的伯克希尔股票：1993 年 4.33 亿美元 → 2014 年约 57 亿美元
    ts, t57 = wt('I8', '股票'), wt('I8', '五十七亿')
    kb = ke(t, ts - 0.2, 0.5)
    if kb > 0:
        yb, s = 1340, 200 / 57.0
        text(img, '付出：25,203 股伯克希尔 A 股', W / 2, 1060, 26, 'sans_med', INK2, a * kb, track=0.04)
        bar(img, 320, yb, 120, 4.33 * s * kb, GOLD_C, a)
        text(img, '4.33 亿美元', 320, yb - 4.33 * s - 30, 30, 'corm_med', GOLD_C, a * kb)
        text(img, '1993 年', 320, yb + 30, 22, 'sans_med', INK2, a * kb)
        k5 = ke(t, t57 - 0.2, 0.3)
        h = 57 * s * eio((t - t57 + 0.2) / 0.9)
        bar(img, 760, yb, 120, h, AMBER, a * max(k5, 0.0))
        if k5 > 0:
            text(img, '约 57 亿美元', 760, yb - 57 * s - 30, 34, 'corm_med', AMBER, a * ke(t, t57 + 0.5, 0.4), glow=0.2)
            text(img, '2014 年', 760, yb + 30, 22, 'sans_med', INK2, a * k5)
    tc = wt('I8', '惨痛')
    fx.slam(img, '最惨痛的错误', W / 2, 1415, 44, 'serif_black', t, tc - 0.05, a * kd, gold=False, col=AMBER, glow_=0.35)
    text(img, '“The most gruesome was Dexter Shoe.” —— 2014 年致股东信', W / 2, 1455, 18, 'ebg_i', INK2, a * kd * ke(t, tc + 0.8, 0.5))


# ---------------------------------------------------------------- I10：今天——三个问题；答不上来就放进“太难”的篮子
def today_a(t): return sc(t, B_TODAY, B_CLOSE)


def dia_today(L, t):
    a = today_a(t)
    if a <= 0: return
    shock(L, (W / 2, 1340), t, wt('I10', '太难') - 0.05, AMBER, a, rmax=480, life=1.0, flatten=0.3)


def txt_today(img, t, subs):
    a = today_a(t)
    if a <= 0: return
    header(img, 'TODAY · 面对一只股票', a)
    text(img, '先问三个问题', W / 2, 410, 40, 'serif_bold', INK, a * ke(t, wt('I10', '三个问题') - 0.2, 0.5), track=0.1)
    qs_ = (('看得懂吗', '这门生意，我看得懂吗？', '能力圈'), ('十年后', '十年后，它大概什么样？', '“what it’s going to look like in 10 or 15 years”'),
           ('几件事', '要猜对几件事才能赚钱？', '环节越少越好'))
    tn = wt('I10', '答不上来')
    for i, (kw, s_, sub) in enumerate(qs_):
        kk = ke(t, wt('I10', kw) - 0.45, 0.4)
        if kk <= 0: continue
        y = 540 + i * 190
        drop = eio((t - tn - 0.2 - 0.15 * i) / 0.8) if i == 1 else 0.0     # 答不上来的那一张，掉进“太难”的篮子
        yy = y + drop * (1285 - y)
        sc_ = 1 - 0.5 * drop
        panel(img, W / 2 - 430 * sc_, yy - 75 * sc_, W / 2 + 430 * sc_, yy + 75 * sc_, a * kk, col=GOLD_C if not drop else AMBER, fill=0.6)
        text(img, f'0{i + 1}', W / 2 - 360 * sc_, yy - 8, int(44 * sc_), 'corm_med', SUB_GOLD, a * kk)
        fx.slam(img, s_, W / 2 + 30, yy - 16 * sc_, int(46 * sc_), 'serif_black', t, wt('I10', kw) - 0.45, a, gold=not drop, col=AMBER if drop else None,
                glow_=0.3)
        text(img, sub, W / 2 + 30, yy + 40 * sc_, int(22 * sc_), 'ebg_i' if '“' in sub else 'sans', INK2, a * kk * (1 - drop), track=0.04)
    kt = ke(t, wt('I10', '太难') - 0.3, 0.5)
    if kt > 0:
        x0, x1, y0, y1 = 250, 830, 1220, 1400
        poly(img, [(x0, y0), (x0 + 40, y1), (x1 - 40, y1), (x1, y0)], AMBER, a * kt, 3)
        line(img, (x0 - 20, y0), (x1 + 20, y0), AMBER, a * kt, 4)
        fx.slam(img, '太难', W / 2, 1345, 60, 'serif_black', t, wt('I10', '太难') - 0.1, a, gold=False, col=AMBER, glow_=0.35)
        text(img, 'TOO HARD', W / 2, 1395, 20, 'inter_semi', AMBER, a * kt, track=0.4)


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
    a = env(t, B_FLY, CLOSE_T1, 0.9, 0.12) * (1 - 0.6 * today_a(t))
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
    """I11：宁愿把看得懂的范围想得小一点；少犯错，比做难事重要得多（星图里逐句显现）"""
    a = env(t, I['I11']['t0'] - 0.3, I['I11']['t1'] + 1.0, 0.5, 0.6)
    if a <= 0: return
    for kw, s_, y, gold_, sz in (('小一点', '宁愿把看得懂的范围，想得小一点', 1290, False, 50), ('少犯错', '少犯错，比做难事重要得多', 1400, True, 60)):
        k = eio((t - wt('I11', kw) + 0.5) / 0.9)
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


# ================================================================ 一句话总结 + 品牌片尾（系列固定片尾）
SUM_LINES = (('投资没有难度系数：', 880), ('跨过一尺的栏，就够了。', 1010))


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
    w1 = eo((t - VOD['M']['t0'] + 0.1) / 1.0); w2 = eo((t - wt('M', '跨过') + 0.05) / 1.0)
    sh = cl((t - VOD['M']['t1'] - 0.2) / 1.4) if VOD['M']['t1'] + 0.2 < t < VOD['M']['t1'] + 1.6 else None
    for (s, y), w in zip(SUM_LINES, (w1, w2)):
        gold_title(img, s, W / 2, y, 96, a, wipe=w, shine=sh, track=0.04)
    text(img, '伯克希尔股东大会投资智慧录 · 第四集', W / 2, 1150, 26, 'sans', INK2, a * eo((k - 1.2) / 0.8), track=0.1)


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
DIAS = [dia_cold, dia_title, dia_s1, dia_s2, dia_s3, dia_ctx, dia_qa, dia_quote, dia_i1, dia_prin, dia_bet, dia_dex, dia_today,
        dia_close, dia_sum]
TXTS = [txt_cold, txt_title, txt_s1, txt_s2, txt_s3, txt_ctx, txt_qa, txt_quote, txt_card, txt_i1, txt_prin, txt_bet, txt_dex,
        txt_today, txt_close, txt_sum]


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
        narr_sub(img, t, INS['subs'], hide=('I11',))
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
