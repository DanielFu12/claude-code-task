"""《伯克希尔股东大会投资智慧录》第二集 · 风险不是波动 —— 逐帧渲染（1080×1920，30fps）。

画面风格：“流光诗意纪录片”——写实空镜（金色时刻的海面）→ 流动可视化（线积分卷积流线、辐射流线、变形网格曲面、粒子）
→ 公式屏（深底 + 极暗流线 + 发光公式），三类画面交替出现，相邻镜头 1.0–1.2 秒交叉溶解，只在片尾前做一段卡拍快闪回顾。
着色器在 s4gl.py（GLSL，moderngl + Mesa llvmpipe，需在 xvfb-run 下运行），后期在 s4post.py。
用法：
    python3 render.py nframes WORK
    python3 render.py chunk A B OUT.mp4 WORK
    python3 render.py stills OUT_DIR WORK t1 t2 …
所有画面都是时间 t 的纯函数；时间点全部来自 WORK/timeline.json。
"""
import io, json, math, os, subprocess, sys
from functools import lru_cache
import numpy as np, cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'brand'))
from gfx import *                      # noqa: F401,F403
import gfx
import fx
import s4post
import brand as B
from script import BROLL

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['mathtext.fontset'] = 'cm'

WORK = sys.argv[-1] if len(sys.argv) > 2 else os.path.join(HERE, '..', 'work')
TL = json.load(open(os.path.join(WORK, 'timeline.json')))
FPS = TL['fps']
ENV = np.load(os.path.join(WORK, 'orig_env.npy'))

# ---------------------------------------------------------------- 字体与色板（S4：书法片名、旧式数字衬线、衬线中文字幕、全大写英文）
gfx.FONTS.update(callig='callig', playfair='playfair_var', playfair_i='playfair_var_i', serif_reg='serif_reg', serif_light='serif_light')
gfx.LATIN_FALLBACK.update(playfair='serif_med', playfair_i='serif_med')
CHAMP, CHAMP_M, CHAMP_D = C(248, 217, 152), C(211, 176, 120), C(172, 127, 84)       # 香槟金
STEEL, STEEL_M, STEEL_D = C(107, 160, 190), C(80, 112, 155), C(59, 81, 125)         # 钢蓝
SUBW, SUBE = C(242, 240, 234), C(185, 188, 205)                                       # 字幕白 / 英文副字幕
WARMW = C(255, 240, 214)                                                               # 书法片名的暖白
LOSS = C(206, 104, 82)                                                                 # 少量警示色：只用于亏损与风险
LIN_CHAMP = np.array([1.0, 0.80, 0.50], np.float32)                                   # 线性空间里的发光颜色
LIN_STEEL = np.array([0.30, 0.55, 0.78], np.float32)
LIN_LOSS = np.array([1.0, 0.36, 0.22], np.float32)

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

# ---------------------------------------------------------------- GL 着色器（懒加载）
_G = None


def G():
    global _G
    if _G is None:
        from s4gl import GL
        _G = GL()
    return _G


def up(x):
    return x if x.shape[:2] == (H, W) else cv2.resize(x, (W, H), interpolation=cv2.INTER_CUBIC)


def ocean(t, wave=0.35, spd=1.0, sunh=0.05, az=0.2, camh=1.6, push=0.0, clouds=0.7, dusk=0.0, ex=0.8):
    return up(G().render('ocean', t, [wave, spd, sunh, az, camh, push, clouds, dusk, ex], 720, 1280))


FLOW_K = ('ty', 'spd', 'bri', 'warm', 'ax', 'ay', 'bx', 'by', 'sa', 'sb', 'turb', 'sink', 'dens', 'jit')


def flow(t, res=(540, 960), **k):
    d = dict(ty=0, spd=0.5, bri=0.2, warm=0.0, ax=0.3, ay=0.6, bx=0.7, by=0.4, sa=1.0, sb=1.0, turb=0.0, sink=0.0, dens=0.35, jit=0.0)
    d.update(k)
    return up(G().render('flow', t, [d[n] for n in FLOW_K], *res))


GRID_K = ('rip', 'wav', 'wspd', 'crat', 'cx', 'cz', 'cw', 'camh', 'camz', 'pitch', 'dens', 'dots', 'bri', 'warm', 'lx', 'ly', 'lz', 'li',
          'tear', 'camx', 'purple')
GRID_D = dict(rip=0.0, wav=0.0, wspd=1.0, crat=0.0, cx=0.0, cz=-8.0, cw=1.5, camh=1.6, camz=0.0, pitch=-0.42, dens=1.0, dots=0.0, bri=0.8,
              warm=0.0, lx=0.0, ly=1.2, lz=-6.0, li=0.0, tear=0.0, camx=0.0, purple=0.0)


def grid(t, res=(1080, 1920), **k):
    d = dict(GRID_D); d.update(k)
    return up(G().render('grid', t, [d[n] for n in GRID_K], *res))


def grid_h(d, x, z, t):
    """与着色器里 H() 相同的高度场（用来把光点放在曲面上）"""
    h = d['rip'] * (math.sin(x * 1.3 + t * 0.9) * 0.5 + math.sin(z * 1.7 - t * 0.7) * 0.35 + math.sin((x + z) * 2.3 + t * 1.3) * 0.15)
    h += d['wav'] * math.sin(z * 0.9 - t * d['wspd']) * (0.6 + 0.4 * math.sin(x * 0.5))
    r2 = (x - d['cx']) ** 2 + (z - d['cz']) ** 2
    h -= d['crat'] * math.exp(-r2 / d['cw'] ** 2) + d['tear'] * math.exp(-r2 / (d['cw'] ** 2 * 0.6))
    return h


def grid_proj(d, P):
    """网格场景的世界坐标 → 屏幕像素（与着色器的相机一致）"""
    dx, dy, dz = P[0] - d['camx'], P[1] - d['camh'], P[2] - d['camz']
    p = d['pitch']
    y = dy * math.cos(p) + dz * math.sin(p)
    z = -dy * math.sin(p) + dz * math.cos(p)
    if z > -1e-3: return None
    s = -1.1 / z
    qx, qy = dx * s, y * s
    return (qx / (W / H) + 0.5) * W, (0.5 - qy) * H


# ---------------------------------------------------------------- 线性空间里的发光线与粒子（之后统一做泛光）
def lpoly(lin, pts, col, k=1.0, th=3, halo=9.0):
    if k <= 0.003 or len(pts) < 2: return
    P = np.asarray(pts, np.float64)
    pad = int(halo * 3 + th + 4)
    x0, y0 = int(max(P[:, 0].min() - pad, 0)), int(max(P[:, 1].min() - pad, 0))
    x1, y1 = int(min(P[:, 0].max() + pad, W)), int(min(P[:, 1].max() + pad, H))
    if x1 <= x0 or y1 <= y0: return
    m = np.zeros((y1 - y0, x1 - x0), np.float32)
    q = ((P - [x0, y0]) * 16).astype(np.int32).reshape(-1, 1, 2)
    cv2.polylines(m, [q], False, 1.0, th, cv2.LINE_AA, 4)
    g = m + cv2.GaussianBlur(m, (0, 0), halo) * 0.9
    lin[y0:y1, x0:x1] += g[..., None] * (np.asarray(col, np.float32) * k)


def splat(lin, xy, col, k=1.0, sig=1.2, w=None):
    """把一组粒子以加色方式画进线性缓冲区（单个粒子很暗，靠叠加出亮度）"""
    if k <= 0.003 or len(xy) == 0: return
    xy = np.asarray(xy, np.float64)
    pad = int(sig * 4 + 2)
    ok = (xy[:, 0] > -pad) & (xy[:, 0] < W + pad) & (xy[:, 1] > -pad) & (xy[:, 1] < H + pad)
    xy = xy[ok]
    if len(xy) == 0: return
    x0, y0 = int(max(xy[:, 0].min() - pad, 0)), int(max(xy[:, 1].min() - pad, 0))
    x1, y1 = int(min(xy[:, 0].max() + pad, W)), int(min(xy[:, 1].max() + pad, H))
    if x1 <= x0 or y1 <= y0: return
    buf = np.zeros((y1 - y0, x1 - x0, 3), np.float32)
    xi = np.clip(xy[:, 0].astype(int) - x0, 0, x1 - x0 - 1); yi = np.clip(xy[:, 1].astype(int) - y0, 0, y1 - y0 - 1)
    c = np.asarray(col, np.float32)
    c = np.broadcast_to(c, (len(xy), 3)) if c.ndim == 1 else c[ok]
    if w is not None: c = c * np.asarray(w, np.float32)[ok][:, None]
    np.add.at(buf, (yi, xi), c)
    buf = cv2.GaussianBlur(buf, (0, 0), sig) * (2 * math.pi * sig * sig) * 0.6 + cv2.GaussianBlur(buf, (0, 0), sig * 5) * 3.0
    lin[y0:y1, x0:x1] += buf * k


def glow_pt(lin, c, r, col, k):
    if k <= 0.003: return
    g = soft_dot(float(round(r, 1)))
    R_ = g.shape[0] // 2
    add(lin, np.asarray(col, np.float32), g * k, int(c[0]) - R_, int(c[1]) - R_)


# ---------------------------------------------------------------- 显示空间里的排印：公式、双语标签、章节眉、字幕
@lru_cache(256)
def fmask(tex, size):
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f'${tex}$', fontsize=size * 0.72, color='white')
    buf = io.BytesIO()
    fig.savefig(buf, dpi=100, transparent=True, bbox_inches='tight', pad_inches=0.12)
    plt.close(fig)
    return np.ascontiguousarray(np.array(Image.open(buf))[..., 3].astype(np.float32) / 255)


def formula(img, tex, x, y, size=60, a=1.0, wipe=None, col=None, glow=0.45, anchor='m', glow_col=None):
    """发光的 LaTeX 公式（Computer Modern），wipe 为从左到右的擦除式显现"""
    if a <= 0.003: return
    m = fmask(tex, int(size))
    h, w = m.shape
    x0 = x - w / 2 if anchor == 'm' else (x if anchor == 'l' else x - w)
    x0, y0 = int(round(x0)), int(round(y - h / 2))
    if wipe is not None and wipe < 1:
        soft = 0.25 * w + 30
        m = m * np.clip((wipe * (w + soft) - np.arange(w)) / soft, 0, 1).astype(np.float32)[None, :]
    col = SUBW if col is None else col
    if glow > 0:
        add(img, glow_col if glow_col is not None else col, cv2.GaussianBlur(m, (0, 0), size * 0.22) * glow * a * 0.8, x0, y0)
    over(img, np.asarray(col, np.float32), m * a, x0, y0)


def caps(img, s, x, y, size, a, col=None, track=0.25, anchor='m', name='sans_med'):
    text(img, s.upper(), x, y, size, name, SUBE if col is None else col, a, anchor, track=track, shadow=0.45)


def label2(img, zh, en, x, y, a, size=36, col=None, anchor='m', name='serif_med', gold=False, glow=0.0, wipe=None, en_col=None):
    """物体标签：中文衬线 + 下方全大写英文小字"""
    if a <= 0.003: return
    text(img, zh, x, y, size, name, SUBW if col is None else col, a, anchor, track=0.08, shadow=0.7, gold=gold, glow=glow,
         glow_col=CHAMP if gold else None, wipe=wipe)
    if en:
        caps(img, en, x, y + size * 0.95, max(14, int(size * 0.42)), a * 0.9 * (1.0 if wipe is None else wipe), col=en_col, anchor=anchor)


def num(img, n, unit, x, y, size, a, col=None, gold=False, unit_size=None, anchor='m', glow=0.15):
    """旧式数字（Playfair）+ 中文单位（衬线）"""
    if a <= 0.003: return
    us = unit_size or int(size * 0.34)
    wn = text_w(n, 'playfair', size); wu = text_w(unit, 'serif_med', us) if unit else 0
    tot = wn + (12 + wu if unit else 0)
    x0 = x - tot / 2 if anchor == 'm' else (x if anchor == 'l' else x - tot)
    c = CHAMP if col is None else col
    text(img, n, x0, y, size, 'playfair', c, a, 'l', shadow=0.5, glow=glow, glow_col=c)
    if unit: text(img, unit, x0 + wn + 12, y + size * 0.16, us, 'serif_med', c, a, 'l', track=0.06, shadow=0.5)


def eyebrow(img, big, sub, a, note=None, y=148):
    """左上章节眉：旧式数字 / 衬线英文（香槟金）+ 全大写副行（字距 0.3em）"""
    if a <= 0.003: return
    text(img, big, 72, y, 60, 'playfair', CHAMP, a, 'l', shadow=0.4, glow=0.12, glow_col=CHAMP)
    caps(img, sub, 74, y + 58, 17, a * 0.78, col=SUBW, track=0.3, anchor='l')
    if note:
        text(img, note, 74, y + 92, 20, 'serif_med', SUBE, a * 0.8, 'l', track=0.06, shadow=0.4)


def narr_sub(img, t, subs, hide=()):
    for s in subs:
        if s['id'] in hide: continue
        if s['t0'] <= t <= s['t1']:
            a = env(t, s['t0'], s['t1'], 0.07, 0.07)
            size = 46
            while text_w(s['text'], 'serif_med', size, 0.12) > 980: size -= 2
            text(img, s['text'], W / 2, 1610, size, 'serif_med', SUBW, a, 'm', track=0.12, shadow=0.95)


def orig_sub(img, s, a, bottom=1652):
    """原声字幕：中文衬线在上（46px），全大写英文在下"""
    zl = wrap(s['zh'], 'serif_med', 46, 960, track=0.08)
    el = wrap(s['en'].upper(), 'sans_med', 24, 990, track=0.2, cjk=False)
    hh = len(zl) * 62 + 16 + len(el) * 37
    y = bottom - hh + 30
    for ln in zl:
        text(img, ln, W / 2, y, 46, 'serif_med', SUBW, a, 'm', track=0.08, shadow=0.95); y += 62
    y += 16 - 30 + 17
    for ln in el:
        text(img, ln, W / 2, y, 24, 'sans_med', SUBE, a * 0.95, 'm', track=0.2, shadow=0.9); y += 37


def scope(img, t, x0, x1, y, amp, a, col=None):
    """原声的“示波线”：一条细金线，振幅随原声能量起伏"""
    if a <= 0.003: return
    e = ofr(t)
    n = len(e)
    xs = np.linspace(x0, x1, 120)
    v = np.interp(np.linspace(0, n - 1, 120), np.arange(n), np.asarray(e, np.float64))
    win = np.sin(np.linspace(0, math.pi, 120)) ** 1.5
    ys = y + amp * np.minimum(v, 1.0) * win * np.sin(np.linspace(0, 26 * math.pi, 120) + t * 9)
    dglow(img, np.c_[xs, ys], CHAMP if col is None else col, a, th=2, halo=5)


def dglow(img, pts, col, a, th=2, halo=6.0):
    """显示空间里的发光细线（加色）"""
    if a <= 0.003: return
    P = np.asarray(pts, np.float64)
    pad = int(halo * 3 + th + 4)
    x0, y0 = int(max(P[:, 0].min() - pad, 0)), int(max(P[:, 1].min() - pad, 0))
    x1, y1 = int(min(P[:, 0].max() + pad, W)), int(min(P[:, 1].max() + pad, H))
    if x1 <= x0 or y1 <= y0: return
    m = np.zeros((y1 - y0, x1 - x0), np.float32)
    cv2.polylines(m, [((P - [x0, y0]) * 16).astype(np.int32).reshape(-1, 1, 2)], False, 1.0, th, cv2.LINE_AA, 4)
    g = m * 0.85 + cv2.GaussianBlur(m, (0, 0), halo) * 0.8
    img[y0:y1, x0:x1] += g[..., None] * np.asarray(col, np.float32) * a


# ================================================================ 背景镜头（线性 HDR）：每个函数返回 (画面, 曝光, 泛光强度)
def sc_cold(t):
    return ocean(t, wave=0.55, spd=0.9, sunh=0.045, az=0.18, camh=1.6, push=0.35 * t, clouds=0.8, ex=0.68), 1.0, 0.5


def sc_title(t):
    k = t - T_TITLE
    on = 0.25 + 0.75 * eo((k + 0.15) / 0.5)
    li = (0.4 + 1.6 * math.exp(-k / 0.8)) if k >= 0 else 0.4 * on
    lin = grid(t, dots=1.0, dens=2.0, camh=0.9, pitch=-0.12, camz=-0.25 * (t - 7.0), bri=0.8 * on, warm=0.65, lx=0.0, ly=0.32, lz=-16.0, li=li)
    return lin, 1.0, 0.6


PRICE = [100, 103, 99, 104, 108, 102, 105, 96, 90, 84, 78, 75]


def price_pts(head):
    """开场的价格线（一年跌掉 25%），head 0..1 为画到哪里"""
    n = len(PRICE) - 1
    xs = np.linspace(150, 930, n * 8 + 1)
    ps = np.interp(np.linspace(0, n, n * 8 + 1), np.arange(n + 1), PRICE)
    rng = np.random.default_rng(5)
    ps = ps + rng.normal(0, 0.9, len(ps)) * (np.arange(len(ps)) % 8 != 0)
    ys = 760 - (ps - 72) / 38 * 420
    m = max(2, int(len(xs) * head))
    return np.c_[xs[:m], ys[:m]]


def sc_s1(t):
    lin = grid(t, rip=0.10, wav=0.16, wspd=1.1, camh=1.25, pitch=-0.22, camz=-0.45 * (t - 10.0), bri=0.36, purple=1.0, dens=1.2)
    td = wt('S1', '跌掉')
    head = 0.05 + 0.95 * eio((t - (V('S1')['t0'] - 0.5)) / (td + 1.0 - V('S1')['t0'] + 0.5))
    P = price_pts(head)
    fade = 1 - eio((t - (V('S2')['t0'] - 0.2)) / 0.8)
    lpoly(lin, P, LIN_CHAMP, 0.9 * fade, th=3, halo=8)
    glow_pt(lin, P[-1], 9, LIN_CHAMP, 2.5 * fade)
    glow_pt(lin, P[-1], 40, LIN_CHAMP, 0.25 * fade)
    return lin, 1.0, 0.6


def sc_s2(t):
    return flow(t, res=(432, 768), ty=0, spd=0.6, bri=0.12, warm=0.0, turb=0.6), 1.0, 0.5


def sc_s3(t):
    return flow(t, res=(432, 768), ty=0, spd=0.4, bri=0.13, warm=0.25, turb=0.25), 1.0, 0.5


def sc_qa(t):
    return flow(t, res=(270, 480), ty=0, spd=0.25, bri=0.10, warm=0.15, turb=0.3), 1.0, 0.45


def sc_i1(t):
    """启示卡 + I1：一冷一暖两个光源（教科书的“波动” / 巴菲特的“损失的可能性”）"""
    sa = 0.10 + 0.65 * eo((t - wt('I1', '教科书')) / 0.8)
    sb = 0.10 + 0.65 * eo((t - wt('I1', '受到伤害')) / 0.8)
    return flow(t, ty=2, spd=0.6, bri=0.24, ax=0.30, ay=0.62, bx=0.70, by=0.40, sa=sa, sb=sb, jit=1.0), 1.0, 0.6


def i2_curve(t):
    """I2：持有期的价格路径（上下起伏，终点落在“购买力”刻线上）"""
    a0 = wt('I2', '持有期') - 0.4
    head = eio((t - a0) / (wt('I2', '购买力') - a0))
    n = 160
    xs = np.linspace(170, 860, n)
    u = np.linspace(0, 1, n)
    ys = 820 - 170 * u - 70 * np.sin(u * 17.0) * np.sin(u * 3.1 + 0.4) - 25 * np.sin(u * 41)
    m = max(2, int(n * head))
    return np.c_[xs[:m], ys[:m]], head


def sc_i2(t):
    lin = flow(t, ty=0, spd=0.45, bri=0.10, warm=0.8)
    P, head = i2_curve(t)
    lpoly(lin, P, LIN_CHAMP, 0.85, th=3, halo=8)
    glow_pt(lin, P[-1], 8, LIN_CHAMP, 2.2)
    return lin, 1.0, 0.6


I3_D = dict(rip=0.32, camh=1.5, pitch=-0.12, bri=0.5, warm=0.0, lx=0.0, ly=1.0, lz=-7.0)


def sc_i3(t):
    li = 1.6 * eo((t - wt('I3', '风险')) / 0.6)
    return grid(t, **dict(I3_D, camz=-0.3 * (t - I['I3']['t0']), li=li)), 1.0, 0.6


def sc_wapo(t):
    """华盛顿邮报：配乐大段落进入时海面起了风暴"""
    storm = eo((t - (TL['nerves']['entry'] - 0.1)) / 0.7)
    return ocean(t, wave=0.45 + 0.75 * storm, spd=1.3, sunh=0.07, az=0.38, camh=1.9, push=0.5 * (t - 244), clouds=0.95, dusk=0.35,
                 ex=0.6), 1.0, 0.5


def sc_i6(t):
    """I6：生意一直在增长——一个暖色光源的辐射流线越来越强"""
    g = eio((t - I['I6']['t0']) / 5.5)
    return flow(t, ty=4, spd=0.6, bri=0.22, bx=0.5, by=0.66, sb=0.35 + 0.6 * g), 1.0, 0.65


def dexter_d(t):
    """德克斯特：平静的网格（没有一天的波动）→ 海外竞争压出深坑 → 光点坠入，价值归零"""
    ts, tz = wt('I9', '海外'), wt('I9', '价值归零')
    c = eio((t - ts) / (tz - ts + 0.6))
    d = dict(GRID_D, rip=0.05 * (1 - eio((t - I['I8']['t0']) / 1.5)), camh=1.7, pitch=-0.15, camz=-0.2 * (t - I['I7']['t0']),
             cx=0.0, cz=-7.5, cw=1.7, crat=2.6 * c, warm=0.15, bri=0.5, lx=0.0, lz=-7.5)
    d['camz'] = min(d['camz'], 0.0)
    fall = eio((t - tz + 0.4) / 1.6)
    d['ly'] = lerp(0.9 + 0.05 * math.sin(t * 1.3), -2.4, fall)
    d['li'] = 1.5 * eo((t - I['I7']['t0'] + 0.3) / 1.0) * (1 - 0.85 * fall)
    return d


def sc_dexter(t):
    d = dexter_d(t)
    lin = grid(t, **d)
    # 价值归零时，金色微粒从光点处流进深坑
    tz = wt('I9', '价值归零')
    k = t - (tz - 0.2)
    if 0 < k < 6.0:
        c0 = grid_proj(d, (0.0, 0.9, -7.5)); c1 = grid_proj(d, (0.0, -2.2, -7.5))
        if c0 and c1:
            r = np.random.default_rng(21)
            n = 900
            ang = r.uniform(0, 2 * math.pi, n); rad = r.uniform(20, 260, n) * (1 + 0.5 * r.random(n))
            dl = r.uniform(0, 1.6, n)
            u = np.clip((k - dl) / 2.4, 0, 1)
            e = u * u
            sx = c0[0] + np.cos(ang) * rad; sy = c0[1] + np.sin(ang) * rad * 0.45
            px = sx + (c1[0] - sx) * e + np.sin(ang * 3 + k) * 20 * (1 - e)
            py = sy + (c1[1] - sy) * e
            wgt = np.sin(np.pi * np.clip(u * 1.1, 0, 1)) * (u > 0)
            splat(lin, np.c_[px, py], LIN_CHAMP, 0.6 * (1 - eio((k - 4.5) / 1.5)), sig=1.1, w=wgt)
    return lin, 1.0, 0.6


def lev_d(t):
    """杠杆：行波一道道推来，光点随浪起伏；被迫在低点卖出时，脚下被撕开一个永久的坑"""
    tp = wt('I11', '低点卖出')
    tear = 2.4 * eio((t - tp - 0.2) / 1.4)
    calm = eio((t - wt('I11', '暂时')) / 3.0)
    d = dict(GRID_D, wav=0.42 * (1 - 0.7 * calm), wspd=1.6, camh=1.8, pitch=-0.15, camz=0.0, cx=0.0, cz=-6.0, cw=1.3, tear=tear,
             warm=0.1, bri=0.5, lx=0.0, lz=-6.0)
    surf = grid_h(dict(d, tear=0.0), 0.0, -6.0, t if t < tp else tp)
    fall = eio((t - tp - 0.3) / 1.5)
    d['ly'] = lerp(surf + 0.35, -2.0, fall)
    d['li'] = 1.4 * eo((t - I['I11']['t0'] + 0.3) / 0.8) * (1 - 0.8 * fall)
    d['_surf'] = surf
    return d


def sc_lev(t):
    d = lev_d(t)
    lin = grid(t, **{k: v for k, v in d.items() if not k.startswith('_')})
    # 借来的钱：一根拴住光点的细线
    kc = eo((t - wt('I11', '借了钱')) / 0.6) * (1 - eio((t - wt('I11', '低点卖出') - 0.6) / 1.0))
    if kc > 0:
        p0 = grid_proj(d, (0.0, d['ly'], -6.0)); p1 = grid_proj(d, (0.0, -1.6, -6.0))
        if p0 and p1:
            lpoly(lin, [p0, (p0[0], p0[1] + (p1[1] - p0[1]) * kc)], LIN_LOSS, 0.5 * kc, th=2, halo=5)
    return lin, 1.0, 0.6


def sc_i12(t):
    return flow(t, res=(432, 768), ty=0, spd=0.4, bri=0.10, warm=0.1, turb=0.5), 1.0, 0.5


def sc_i13(t):
    return ocean(t, wave=0.16, spd=0.6, sunh=0.035, az=0.25, camh=1.3, push=0.25 * (t - 300), clouds=0.5, ex=0.62), 1.0, 0.5


def sc_sum(t):
    k = t - T_SUM
    fade = 1 - eio((t - END['t_particles'] + 0.3) / 1.6)
    li = (0.6 + 1.8 * math.exp(-k / 0.9)) * fade
    lin = grid(t, dots=1.0, dens=2.0, camh=0.9, pitch=-0.12, camz=-0.25 * k, bri=0.7 * fade, warm=0.85, lx=0.0, ly=0.32, lz=-16.0, li=li)
    return lin, 1.0, 0.6


def sc_dark(t):
    return np.zeros((H, W, 3), np.float32), 1.0, 0.5


M0 = float(BEATS[np.searchsorted(BEATS, I['I13']['t1'] + 0.2)])      # 快闪回顾从 I13 之后的第一个拍点开始
# (起点, 镜头, 溶入时长)
SCHED = [
    (0.0, sc_cold, 0.0),
    (T_TITLE - 0.55, sc_title, 1.0),
    (V('S1')['t0'] + 0.15, sc_s1, 1.0),
    (V('S2')['t0'] - 0.3, sc_s2, 1.0),
    (V('S3')['t0'] - 0.2, sc_s3, 1.0),
    (T_Q - 0.4, sc_qa, 1.2),
    (T_INS - 0.8, sc_i1, 1.2),
    (I['I2']['t0'] - 0.4, sc_i2, 1.2),
    (I['I3']['t0'] - 0.3, sc_i3, 1.0),
    (TL['nerves']['entry'] - 0.3, sc_wapo, 0.6),
    (I['I6']['t0'] - 0.4, sc_i6, 1.2),
    (I['I7']['t0'] - 0.3, sc_dexter, 1.2),
    (I['I11']['t0'] - 0.4, sc_lev, 1.0),
    (I['I12']['t0'] - 0.3, sc_i12, 1.0),
    (I['I13']['t0'] - 0.35, sc_i13, 1.2),
    (M0, None, 0.0),                       # 快闪回顾（frame() 里单独处理）
    (T_SUM, sc_sum, 0.0),
    (END['t_logo'] + 0.6, sc_dark, 0.0),
]


def background(t):
    """按时间表取镜头；镜头交界处做交叉溶解（溶入时长以交界为中心）"""
    out = []
    for i, (t0, fn, xf) in enumerate(SCHED):
        t1 = SCHED[i + 1][0] if i + 1 < len(SCHED) else 1e9
        xo = SCHED[i + 1][2] if i + 1 < len(SCHED) else 0.0
        lo, hi = t0 - xf / 2, t1 + xo / 2
        if fn is None or not (lo <= t < hi): continue
        w = 1.0
        if xf > 0: w *= eio((t - lo) / xf)
        if xo > 0: w *= 1 - eio((t - (t1 - xo / 2)) / xo)
        if w > 0.001: out.append((w, fn))
    lin = np.zeros((H, W, 3), np.float32); bk = 0.0; tw = 0.0
    for w, fn in out:
        l, ex, b = fn(t)
        lin += l * (w * ex); bk += b * w; tw += w
    return lin, (bk / tw if tw > 0 else 0.5)


# ================================================================ 叠加层（显示空间）
def ov_cold(img, t, subs=True):
    a = env(t, 0.5, T_TITLE - 0.5, 0.9, 0.6)
    if a <= 0: return
    eyebrow(img, '1994', 'Berkshire Hathaway Annual Meeting', a)
    text(img, '声音：1994 年股东大会原始录音', W / 2, 1300, 24, 'serif_med', SUBE, a * 0.9, track=0.1, shadow=0.7)
    scope(img, t, 300, 780, 1360, 26, a * 0.9)
    if subs:
        for s in TL['cold_subs']:
            sa = env(t, s['t0'] - 0.1, s['t1'] + 0.1, 0.4, 0.3) * a
            if sa > 0: orig_sub(img, s, sa)


def ov_title(img, t, subs=True):
    a = env(t, T_TITLE - 0.4, V('S1')['t0'] + 0.5, 0.3, 0.7)
    if a <= 0: return
    k = t - T_TITLE
    text(img, '巴菲特与芒格 · 伯克希尔股东大会投资智慧录', W / 2, 500, 30, 'serif_med', CHAMP, a * eo((k - 0.2) / 0.8), track=0.14, shadow=0.5)
    lit = eio((k + 0.4) / 0.45)
    gl = 0.35 + (0.9 * math.exp(-k / 0.7) if k > 0 else 0.0)
    text(img, '风险', W / 2, 760, 300, 'callig', WARMW, a * lit, shadow=0.0, glow=gl * lit, glow_col=CHAMP_M)
    w2 = eio((k - 0.35) / 1.4)                        # 英文字母从左到右逐个淡入
    text(img, 'RISK IS NOT VOLATILITY', W / 2, 975, 21, 'sans', SUBE, a * 0.9, track=1.0, wipe=w2, shadow=0.45)
    kt = eo((k - 0.9) / 0.8)
    text(img, '第二集 · 风险不是波动', W / 2, 1060, 32, 'serif_med', SUBW, a * kt, track=0.2, shadow=0.6)
    caps(img, 'Episode 02', W / 2, 1102, 15, a * kt * 0.85, track=0.5)


def ov_intro(img, t, subs=True):
    S1, S2, S3 = V('S1'), V('S2'), V('S3')
    ae = env(t, S1['t0'] - 0.2, S3['t0'] - 0.3, 0.6, 0.6)
    eyebrow(img, 'Prologue', '一个问题 · A Question', ae)
    # S1：价格线 + “−25%” + 两个问题
    a = env(t, S1['t0'] - 0.3, S2['t0'] - 0.2, 0.3, 0.6)
    if a > 0:
        caps(img, 'One year', 540, 830, 16, a * eo((t - S1['t0']) / 0.8), track=0.6)
        k = eo((t - wt('S1', '百分之') + 0.1) / 0.6)
        num(img, '−25%', '', 930, 900, 130, a * k, col=LOSS, anchor='r', glow=0.2)
        for zh, en, x, kw, col in (('更危险？', 'Riskier?', 300, '更危险', SUBW), ('更便宜？', 'Cheaper?', 780, '更便宜', CHAMP)):
            kk = eo((t - wt('S1', kw) + 0.05) / 0.5)
            label2(img, zh, en, x, 1170, a * kk, size=64, col=col, name='serif_bold', glow=0.15 if col is CHAMP else 0.0)
        kl = eo((t - wt('S1', '更便宜')) / 0.5)
        if kl > 0: line(img, (W / 2, 1110), (W / 2, 1110 + 120 * kl), SUBE, a * 0.4, 1)
    # S2：教科书的答案——贝塔
    a = env(t, S2['t0'] - 0.3, S3['t0'] - 0.25, 0.4, 0.6)
    if a > 0:
        k0 = eo((t - S2['t0'] + 0.2) / 0.6)
        label2(img, '教科书 · 贝塔理论', 'Textbook beta theory', W / 2, 640, a * k0, size=34, col=SUBE)
        tb = wt('S2', '贝塔') - 0.5
        formula(img, r'\beta=\frac{\mathrm{Cov}(r_i,\,r_m)}{\mathrm{Var}(r_m)}', W / 2, 860, 84, a, wipe=eio((t - tb) / 1.2))
        ke = eo((t - wt('S2', '更危险') + 0.1) / 0.6)
        formula(img, r'\beta\uparrow\;\;\Rightarrow\;\;\mathrm{Risk}\uparrow', W / 2, 1070, 64, a, wipe=eio((t - wt('S2', '贝塔') - 0.6) / 1.0))
        text(img, '更危险', W / 2, 1230, 92, 'serif_bold', LOSS, a * ke, track=0.12, glow=0.25 * ke, glow_col=LOSS, shadow=0.6)
    if subs: narr_sub(img, t, INTRO['subs'])


def ov_s3ctx(img, t, subs=True):
    S3 = V('S3')
    # S3：1994 年的大会影像
    a = env(t, S3['t0'] - 0.3, T_CTX, 0.8, 0.6)
    if a > 0:
        eyebrow(img, '1994', 'Omaha · Nebraska', a)
        ct = (t - S3['t0'] + 0.3) % 15.5
        fr = grade(CLIPS[200].get(ct), sat=0.55, gain=0.95)
        window(img, fr, W / 2, 640, 1000, 405, zoom=1.04 + 0.006 * (t - S3['t0']), a=a, feather=40, blur_bg=0.45)
        text(img, '画面：1994 年伯克希尔股东大会现场', 52 + 40, 878, 21, 'serif_med', SUBE, a * 0.9, 'l', track=0.06, shadow=0.6)
        k1 = eo((t - wt('S3', '你们') + 0.1) / 0.9); k2 = eo((t - wt('S3', '到底') + 0.1) / 0.9)
        text(img, '“你们说的风险，', W / 2, 1110, 74, 'serif_bold', SUBW, a * k1, track=0.06, wipe=k1, shadow=0.7)
        text(img, '到底是什么？”', W / 2, 1210, 74, 'serif_bold', a=a * k2, gold=True, track=0.06, wipe=k2, glow=0.15, shadow=0.7)
        caps(img, 'What is risk, really?', W / 2, 1290, 18, a * k2 * 0.9, track=0.4)
    # 背景卡：1994 年 4 月 25 日
    a = env(t, T_CTX, T_Q - 0.1, 0.6, 0.6)
    if a > 0:
        k = t - T_CTX
        blur_fill(img, grade(QA_CLIP.get(QA['segs'][0]['src_in']), sat=0.4, gain=0.7), 0.4 * a)
        eyebrow(img, '1994', 'Original Q&A', a)
        num(img, '1994', '', W / 2, 640, 230, a * eo(k / 0.8), glow=0.25)
        text(img, 'April 25 · Omaha, Nebraska', W / 2, 790, 34, 'playfair_i', SUBE, a * eo((k - 0.2) / 0.8), shadow=0.5)
        text(img, '伯克希尔·哈撒韦年度股东大会', W / 2, 900, 54, 'serif_bold', SUBW, a * eo((k - 0.35) / 0.8), track=0.06)
        text(img, '上午场 · 股东问答', W / 2, 985, 40, 'serif_med', CHAMP, a * eo((k - 0.5) / 0.8), track=0.24)
        line(img, (W / 2 - 150, 1040), (W / 2 + 150, 1040), CHAMP_D, a * 0.6 * eo((k - 0.6) / 0.8), 1)
        text(img, 'CNBC 巴菲特档案 · 第 50 章', W / 2, 1095, 28, 'serif_med', SUBE, a * eo((k - 0.7) / 0.8), track=0.08)
        text(img, '原始录像 · 节选', W / 2, 1170, 32, 'serif_med', CHAMP, a * eo((k - 0.9) / 0.8), track=0.2)
        text(img, '画面与声音均为 1994 年现场原始记录', W / 2, 1222, 24, 'serif_med', SUBE, a * eo((k - 1.0) / 0.8), track=0.06)
    if subs: narr_sub(img, t, INTRO['subs'])


def blur_fill(img, src, k):
    """同一画面的放大模糊版，铺满整屏（极淡）"""
    if k <= 0.003: return
    small = cv2.GaussianBlur(cv2.resize(src, (src.shape[1] // 12, src.shape[0] // 12), interpolation=cv2.INTER_AREA), (0, 0), 3)
    bs = max(W / small.shape[1], H / small.shape[0])
    big = cv2.resize(small, (int(small.shape[1] * bs) + 2, int(small.shape[0] * bs) + 2), interpolation=cv2.INTER_LINEAR)
    oy, ox = (big.shape[0] - H) // 2, (big.shape[1] - W) // 2
    img *= (1 - k)
    img += big[oy:oy + H, ox:ox + W] * (k * 0.38)


# ---------------------------------------------------------------- 原始问答：原始录像窗口 + 每段一个发光公式 / 图示
WIN_W, WIN_H, WIN_Y = 1000, 405, 520


def qa_env(t, sc, fi=0.5, fo=0.5, pre=0.3, post=0.2):
    s = QSC.get(sc)
    if not s: return 0.0
    return env(t, s['t0'] - pre, s['t1'] + post, fi, fo)


def ov_qa(img, t, subs=True):
    a = env(t, T_Q - 0.3, T_QE + 0.6, 0.6, 0.9)
    if a <= 0: return
    fr = grade(QA_CLIP.get(qa_src(t)), sat=0.62, gain=0.98)
    mz = eio((t - QA['munger_t'] + 1.0) / 2.5)                       # 芒格开口时，镜头缓缓推向芒格
    zoom = 1.0 + 0.32 * mz + 0.02 * math.sin((t - T_Q) * 0.05)
    window(img, fr, W / 2, WIN_Y, WIN_W, WIN_H, zoom=zoom, pan=(0.17 * mz, -0.03 * mz), a=a, feather=34, blur_bg=0.42)
    eyebrow(img, '1994', 'Original Q&A · 原始问答', a)
    # 省略处：一道柔光扫过画面，并标出“节选”
    for ct in QA['cuts']:
        k = (t - ct + 0.5) / 1.0
        if 0 < k < 1:
            x = lerp(80, W - 80, eio(k))
            s_ = math.sin(math.pi * k)
            dglow(img, [(x, WIN_Y - WIN_H / 2 + 10), (x, WIN_Y + WIN_H / 2 - 10)], CHAMP, a * 0.6 * s_, th=2, halo=14)
            label2(img, '· 节选 ·', 'Excerpt', W / 2, WIN_Y + WIN_H / 2 + 52, a * s_, size=26, col=CHAMP)
    # 说话人 + 示波线
    mt, at = QA['munger_t'], QA['answer_t']
    if t >= mt - 0.3: spk = ('查理·芒格', 'Charlie Munger')
    elif t >= at - 0.2: spk = ('沃伦·巴菲特', 'Warren Buffett')
    else: spk = ('提问 · 来自密歇根州的股东', 'Shareholder from Michigan')
    label2(img, spk[0], spk[1], 72, 778, a, size=30, col=SUBW, anchor='l')
    scope(img, t, 640, 1008, 790, 20, a * 0.85)
    text(img, '画面与声音：1994 年上午场原始录像（节选）', 72, 852, 20, 'serif_med', SUBE, a * 0.75, 'l', track=0.06, shadow=0.5)
    qa_panels(img, t, a)
    if subs:
        for s in QA['subs']:
            sa = env(t, s['t0'], s['t1'], 0.07, 0.07)
            if sa > 0: orig_sub(img, s, sa * a)
        la = env(t, TL['laugh']['t0'], TL['laugh']['t1'], 0.15, 0.2)
        if la > 0: text(img, '（现场笑声）', W / 2, 1380, 30, 'serif_med', SUBE, la * a * 0.85, track=0.1)


def ke(t, t0, d=0.6): return eo((t - t0) / d)


def qa_panels(img, t, a):
    """关键观点区（y≈900–1380）：发光公式 + 衬线标签，不用卡片"""
    # 提问
    s = qa_env(t, 'ask') * a
    if s > 0:
        label2(img, '股东的问题', 'The question', W / 2, 950, s, size=28, col=CHAMP)
        k0 = ke(t, qs('Q1', 0.4)) * (1 - ke(t, qs('Q2'), 0.5))
        text(img, '金融世界里的风险，', W / 2, 1110, 56, 'serif_bold', SUBW, s * k0, track=0.06)
        text(img, '您怎么看？', W / 2, 1200, 56, 'serif_bold', a=s * k0, gold=True, track=0.06)
        k2 = ke(t, qs('Q2')) * (1 - ke(t, qs('Q5'), 0.5))
        label2(img, '您的风险观', 'Your view', 290, 1120, s * k2, size=46, col=CHAMP, name='serif_bold')
        label2(img, '传统的风险观', 'Conventional view', 790, 1120, s * ke(t, qs('Q3')) * (1 - ke(t, qs('Q5'), 0.5)), size=46, name='serif_bold')
        formula(img, r'\neq', W / 2, 1120, 70, s * ke(t, qs('Q3', 1.0)) * (1 - ke(t, qs('Q5'), 0.5)))
        k5 = ke(t, qs('Q5'), 0.4)
        formula(img, r'\beta=\frac{\mathrm{Cov}(r_i,\,r_m)}{\mathrm{Var}(r_m)}', W / 2, 1100, 66, s * k5, wipe=eio((t - qs('Q5')) / 1.2))
        text(img, '自相矛盾？', W / 2, 1265, 50, 'serif_bold', LOSS, s * ke(t, qs('Q5', 1.6)), track=0.1)
    # 定义
    s = qa_env(t, 'define') * a
    if s > 0:
        label2(img, '巴菲特对风险的定义', "Buffett's definition", W / 2, 950, s, size=28, col=CHAMP)
        formula(img, r'\mathrm{Risk}=P\,(\,\mathrm{harm\ or\ injury}\,)', W / 2, 1060, 62, s, wipe=eio((t - qs('A1', 0.3)) / 1.3),
                glow_col=CHAMP)
        text(img, '受到伤害或损失的可能性', W / 2, 1150, 40, 'serif_med', CHAMP, s * ke(t, qs('A1', 1.4)), track=0.1)
        formula(img, r'\mathrm{Risk}=f\,(\,T_{\mathrm{hold}}\,)', W / 2, 1260, 56, s, wipe=eio((t - qs('A2', 1.5)) / 1.2))
        text(img, '与持有期限密不可分', W / 2, 1340, 32, 'serif_med', SUBE, s * ke(t, qs('A2', 2.6)), track=0.12)
    # 持有一天：上午 11:30 买入，收盘前卖出
    s = qa_env(t, 'horizon') * a
    if s > 0:
        label2(img, '持有一天', 'Held for a day', W / 2, 950, s, size=28, col=CHAMP)
        x0, x1, yc = 170, 910, 1100
        k = eio((t - qs('A3')) / 9.0) if t < qs('A4') else 0.6 + 0.4 * eio((t - qs('A4')) / 1.5)
        n = int(120 * k)
        if n > 2:
            xs = np.linspace(x0, x1, 120)[:n]
            u = np.linspace(0, 1, 120)[:n]
            ys = yc - 40 * np.sin(u * 37) * np.sin(u * 7 + 1) - 18 * np.sin(u * 93 + t * 0.5)
            dglow(img, np.c_[xs, ys], STEEL, s * 0.9, th=2, halo=6)
        num(img, '11:30', '买入', x0, 1190, 46, s * ke(t, qs('A3', 2.0)), col=SUBW, anchor='l', glow=0.05)
        text(img, '收盘前卖出', x1, 1190, 34, 'serif_med', SUBW, s * ke(t, qs('A4')), 'r', track=0.06)
        formula(img, r'P\,(\mathrm{loss})\approx 50\%', W / 2, 1300, 64, s, wipe=eio((t - qs('A6', 0.3)) / 1.2), col=SUBW, glow_col=LOSS)
    # 可口可乐：同一家公司，持有期不同，风险完全不同
    s = qa_env(t, 'coke') * a
    if s > 0:
        label2(img, '同一只可口可乐', 'The same Coca-Cola', W / 2, 950, s, size=28, col=CHAMP)
        text(img, '以当初的买入价 · 长期持有', W / 2, 1040, 36, 'serif_med', SUBW, s * ke(t, qs('A8')), track=0.08)
        formula(img, r'\mathrm{Risk}\;\approx\;0', W / 2, 1115, 64, s, wipe=eio((t - qs('A9', 0.8)) / 1.0), col=CHAMP, glow_col=CHAMP)
        text(img, '今天上午买入 · 明天上午卖出', W / 2, 1215, 36, 'serif_med', SUBW, s * ke(t, qs('A10', 1.0)), track=0.08)
        formula(img, r'\mathrm{Risk}\;\gg\;0', W / 2, 1295, 64, s, wipe=eio((t - qs('A11')) / 1.0), col=SUBW, glow_col=LOSS)
    # 贝塔：学术界的定义
    s = qa_env(t, 'beta') * a
    if s > 0:
        label2(img, '学术界 → 金融市场', 'Academia → Wall Street', W / 2, 950, s, size=28, col=CHAMP)
        k15 = ke(t, qs('A15'), 0.8)
        formula(img, r'\mathrm{Risk}\;\equiv\;\sigma', W / 2, 1080, 84, s * (1 - 0.6 * k15), wipe=eio((t - qs('A14', 0.2)) / 1.2))
        text(img, '用波动定义风险 · 贝塔衡量波动', W / 2, 1170, 32, 'serif_med', SUBE, s * ke(t, qs('A14', 1.6)) * (1 - 0.6 * k15), track=0.1)
        if k15 > 0:
            ww = 300
            line(img, (W / 2 - ww / 2, 1080), (W / 2 - ww / 2 + ww * eio((t - qs('A15')) / 0.6), 1080), LOSS, s, 3)
        formula(img, r'\mathrm{Risk}\;\neq\;\sigma', W / 2, 1290, 84, s, wipe=eio((t - qs('A15', 0.4)) / 1.2), col=CHAMP, glow_col=CHAMP)
    # 多线振动：每年 +20%~+80% 的 A，比稳定 +5% 的 B “风险更高”？
    s = qa_env(t, 'absurd') * a
    if s > 0:
        label2(img, '按传统的风险度量', 'By the conventional measure', W / 2, 950, s, size=28, col=CHAMP)
        u = np.linspace(0, 1, 140); xs = 170 + 740 * u
        kA = eio((t - qs('A17')) / 2.0); kB = eio((t - qs('A18')) / 2.0)
        nA, nB = int(140 * kA), int(140 * kB)
        if nA > 2:
            ys = 1080 - 55 * np.sin(u * 23 + t * 2.2) * (0.6 + 0.4 * np.sin(u * 5 + 1))
            dglow(img, np.c_[xs, ys][:nA], STEEL, s * 0.95, th=2, halo=7)
            label2(img, '投资 A · 每年 +20% ～ +80%', 'Investment A', 170, 1010, s * ke(t, qs('A17')), size=26, anchor='l', col=STEEL)
        if nB > 2:
            ys = 1215 - 3 * np.sin(u * 23 + t * 2.2)
            dglow(img, np.c_[xs, ys][:nB], CHAMP, s * 0.95, th=2, halo=7)
            label2(img, '投资 B · 每年稳定 +5%', 'Investment B', 170, 1165, s * ke(t, qs('A18')), size=26, anchor='l', col=CHAMP)
        k3 = ke(t, qs('A18', 2.0)) * (1 - ke(t, qs('A19'), 0.5))
        formula(img, r'\sigma_A>\sigma_B\;\Rightarrow\;\mathrm{Risk}_A>\mathrm{Risk}_B\;?', W / 2, 1310, 52, s * k3, glow_col=LOSS)
        k4 = ke(t, qs('A19', 0.3), 0.8)
        label2(img, '乱了套', 'Haywire', W / 2, 1300, s * k4, size=58, name='serif_bold', gold=True, glow=0.2)
    # 期望：单笔可以亏，一组同类独立交易的期望不能为负
    s = qa_env(t, 'expect') * a
    if s > 0:
        label2(img, '伯克希尔的做法', 'How Berkshire does it', W / 2, 950, s, size=28, col=CHAMP)
        text(img, '单笔交易：可以亏钱', W / 2, 1035, 40, 'serif_med', SUBW, s * ke(t, qs('A21')), track=0.08)
        rng = np.random.default_rng(9)
        outs = rng.normal(0.35, 1.0, 40)
        n = int(40 * eio((t - qs('A22')) / 3.5))
        for i in range(n):
            x = 195 + (i % 20) * 36.5; y = 1105 + (i // 20) * 46
            v = outs[i]
            r_ = 5 + 4 * min(abs(v), 1.5)
            ka = eo((t - qs('A22') - i * 0.0875) / 0.4)
            glow(img, (x, y), r_ * 1.6, CHAMP if v > 0 else LOSS, s * 0.25 * ka)
            circle(img, (x, y), r_, CHAMP if v > 0 else LOSS, s * 0.85 * ka, fill=True)
        text(img, '一系列相互独立、类型相似的交易', W / 2, 1215, 32, 'serif_med', SUBE, s * ke(t, qs('A24')), track=0.08)
        formula(img, r'\mathbb{E}\left[\,\sum_k X_k\right]\;>\;0', W / 2, 1300, 62, s, wipe=eio((t - qs('A25')) / 1.2), col=CHAMP,
                glow_col=CHAMP)
    # 芒格：费马与帕斯卡
    s = qa_env(t, 'munger', post=0.8) * a
    if s > 0:
        k1 = ke(t, qs('M1', 1.0), 0.9)
        text(img, 'Fermat · Pascal', W / 2, 1010, 78, 'playfair_i', CHAMP, s * k1, glow=0.18, glow_col=CHAMP, shadow=0.5)
        text(img, '费马 · 帕斯卡', W / 2, 1090, 32, 'serif_med', SUBE, s * k1, track=0.3)
        formula(img, r'E=\sum_i\,p_i\,x_i', W / 2, 1190, 62, s, wipe=eio((t - qs('M1', 2.0)) / 1.2))
        text(img, '像从没听说过现代金融理论那样，用概率思考', W / 2, 1290, 32, 'serif_med', SUBW, s * ke(t, qs('M2')), track=0.06)


# ---------------------------------------------------------------- 投资启示
NOTE = '本片解读，非巴菲特或芒格原话'


def ov_insight(img, t, subs=True):
    if t < T_INS - 0.3 or t > T_SUM: return
    # 启示卡
    a = env(t, T_INS - 0.1, I['I1']['t0'] + 0.9, 0.5, 0.7)
    if a > 0:
        k = t - T_INS
        text(img, '投资启示', W / 2, 860, 112, 'serif_bold', a=a * eo(k / 0.8), gold=True, glow=0.25, track=0.12)
        caps(img, 'Insight', W / 2, 975, 20, a * eo((k - 0.3) / 0.8), track=1.0, name='sans')
        text(img, NOTE, W / 2, 1035, 28, 'serif_med', SUBE, a * eo((k - 0.5) / 0.8), track=0.1)
    # 章节眉
    chapters = [(I['I1']['t0'] - 0.2, 'Insight', 'Risk vs. volatility · 风险与波动'),
                (I['I4']['t0'] - 0.3, '1973', 'The Washington Post · 华盛顿邮报'),
                (I['I7']['t0'] - 0.3, '1993', 'Dexter Shoe · 德克斯特鞋业'),
                (I['I11']['t0'] - 0.3, 'Leverage', 'Forced selling · 杠杆与被迫卖出'),
                (I['I12']['t0'] - 0.3, 'Today', 'What it means now · 今天的意义'),
                (I['I13']['t0'] - 0.3, 'Insight', 'In one sentence · 一句话')]
    for i, (c0, big, sub) in enumerate(chapters):
        c1 = chapters[i + 1][0] if i + 1 < len(chapters) else M0
        ea = env(t, c0, c1, 0.6, 0.5)
        eyebrow(img, big, sub, ea, note=NOTE)
    # I1：两个光源的标签
    a = env(t, I['I1']['t0'] - 0.2, I['I2']['t0'] - 0.4, 0.5, 0.5)
    if a > 0:
        k1 = ke(t, wt('I1', '受到伤害')); k2 = ke(t, wt('I1', '教科书'))
        label2(img, '巴菲特：损失的可能性', 'Possibility of loss', 756, 1300, a * k1, size=38, col=CHAMP)
        formula(img, r'P\,(\mathrm{loss})', 756, 1410, 58, a, wipe=eio((t - wt('I1', '可能性')) / 1.0), col=CHAMP, glow_col=CHAMP)
        label2(img, '教科书：价格的波动', 'Price volatility', 324, 470, a * k2, size=38, col=STEEL)
        formula(img, r'\sigma,\;\beta', 324, 575, 58, a, wipe=eio((t - wt('I1', '波动')) / 1.0), col=SUBW, glow_col=STEEL)
    # I2：持有期 + 购买力
    a = env(t, I['I2']['t0'] - 0.2, I['I3']['t0'] - 0.4, 0.5, 0.5)
    if a > 0:
        label2(img, '买入', 'Buy', 170, 900, a * ke(t, wt('I2', '持有期') - 0.3), size=32, col=SUBW, anchor='l')
        kc = ke(t, wt('I2', '购买力') - 0.2)
        for j, yy in enumerate(np.linspace(560, 760, 6)):          # 离散层级：右侧一组刻线
            line(img, (880, yy), (930, yy), CHAMP if j == 2 else SUBE, a * (0.35 + 0.5 * (j == 2) * kc), 1 + (j == 2))
        label2(img, '持有期结束', 'End of holding period', 930, 500, a * ke(t, wt('I2', '拿回') - 0.3), size=30, col=SUBW, anchor='r')
        formula(img, r'\frac{W_T}{P_T}\;\geq\;\frac{W_0}{P_0}', W / 2, 1060, 72, a, wipe=eio((t - wt('I2', '购买力') + 0.2) / 1.2),
                col=CHAMP, glow_col=CHAMP)
        text(img, '拿回的钱 ≥ 当初的购买力', W / 2, 1180, 40, 'serif_med', SUBW, a * kc, track=0.08)
        kq = ke(t, wt('I2', '购买力') + 0.8, 0.8)
        text(img, '“…at least as much purchasing power as he had to begin with…”', W / 2, 1270, 25, 'playfair_i', SUBE, a * kq)
        text(img, '—— 巴菲特，1993 年致股东信', W / 2, 1320, 22, 'serif_med', SUBE, a * kq, track=0.08)
    # I3：波动 vs 风险
    a = env(t, I['I3']['t0'] - 0.2, TL['nerves']['entry'] - 0.2, 0.4, 0.4)
    if a > 0:
        k2 = ke(t, wt('I3', '风险'))
        label2(img, '波动 ＝ 价格摆动的幅度', 'Volatility · how far the price swings', W / 2, 420, a * ke(t, I['I3']['t0'] - 0.1) * (1 - 0.45 * k2),
               size=44, col=STEEL)
        label2(img, '风险 ＝ 钱还在不在', 'Risk · is the money still there', W / 2, 560, a * k2, size=62, name='serif_bold', gold=True, glow=0.2)
    # 华盛顿邮报
    a = env(t, I['I4']['t0'] - 0.3, I['I7']['t0'] - 0.4, 0.4, 0.6)
    if a > 0:
        tb, td, tg = wt('I4', '一千零六十'), wt('I4', '八百万'), wt('I6', '超过')
        kb = ke(t, tb - 0.1) * (1 - ke(t, td - 0.3, 0.4))
        kd = ke(t, td - 0.1) * (1 - ke(t, I['I6']['t0'] - 0.2, 0.5))
        num(img, '1,060', '万美元', W / 2, 1060, 140, a * kb, col=SUBW)
        label2(img, '1973 年 · 买入成本', 'Cost, 1973', W / 2, 1180, a * kb, size=30, col=SUBE)
        num(img, '800', '万美元', W / 2, 1060, 140, a * kd, col=SUBW)
        label2(img, '1974 年底 · 市值', 'Market value, end of 1974', W / 2, 1180, a * kd, size=30, col=SUBE)
        num(img, '−25%', '', W / 2, 1300, 76, a * kd * ke(t, td + 0.5), col=LOSS, glow=0.2)
        k5 = env(t, I['I5']['t0'] - 0.1, I['I6']['t0'] - 0.1, 0.4, 0.4)
        if k5 > 0:
            formula(img, r'\beta\uparrow\;\Rightarrow\;', W / 2 - 110, 1420, 54, a * k5, col=SUBW, glow_col=LOSS)
            text(img, '“更危险”', W / 2 + 90, 1420, 48, 'serif_bold', LOSS, a * k5, track=0.08)
        k6 = env(t, I['I6']['t0'] - 0.1, I['I7']['t0'] - 0.4, 0.5, 0.5)
        if k6 > 0:
            label2(img, '生意一直在增长', 'The business kept growing', W / 2, 1180, a * k6 * (1 - ke(t, tg - 0.2, 0.5)), size=56,
                   name='serif_bold', gold=True, glow=0.2)
            kg = ke(t, tg - 0.1)
            v = 0.106 + (4.40 - 0.106) * eio((t - tg) / 1.8)
            num(img, f'{v:.2f}', '亿美元', W / 2, 1150, 150, a * k6 * kg, glow=0.25)
            label2(img, '1993 年 · 持股市值', 'Market value, 1993', W / 2, 1280, a * k6 * kg, size=30, col=SUBE)
    # 德克斯特
    a = env(t, I['I7']['t0'] - 0.3, I['I11']['t0'] - 0.4, 0.5, 0.6)
    if a > 0:
        t57 = wt('I10', '五十七')
        k7 = ke(t, wt('I7', '四亿') - 0.1) * (1 - ke(t, I['I8']['t0'] - 0.2, 0.5))
        num(img, '4.33', '亿美元', W / 2, 410, 140, a * k7, col=SUBW)
        label2(img, '以伯克希尔股票支付', 'Paid in Berkshire stock', W / 2, 530, a * k7, size=30, col=SUBE)
        k8 = env(t, I['I8']['t0'] - 0.1, I['I9']['t0'] + 0.2, 0.5, 0.5)
        if k8 > 0:
            label2(img, '全资收购 · 没有股价', 'Wholly owned · no quoted price', W / 2, 400, a * k8, size=46, name='serif_bold')
            formula(img, r'\sigma\;=\;0', W / 2, 530, 70, a * k8, wipe=eio((t - wt('I8', '波动') + 0.1) / 1.0), col=STEEL, glow_col=STEEL)
        k9 = env(t, wt('I9', '海外') - 0.1, wt('I9', '价值归零') - 0.1, 0.5, 0.3)
        label2(img, '海外竞争 · 优势荡然无存', 'Foreign competition', W / 2, 460, a * k9, size=44, col=SUBW, name='serif_bold')
        kz = env(t, wt('I9', '价值归零') - 0.1, t57 - 0.3, 0.5, 0.4)
        if kz > 0:
            text(img, '价值', W / 2 - 70, 460, 96, 'serif_bold', LOSS, a * kz, 'r', track=0.1, glow=0.2, glow_col=LOSS)
            formula(img, r'\rightarrow\;0', W / 2 - 40, 465, 110, a * kz, anchor='l', col=LOSS, glow_col=LOSS)
        k10 = ke(t, t57 - 0.1)
        if k10 > 0:
            num(img, '57', '亿美元', W / 2, 370, 150, a * k10, col=LOSS, glow=0.2)
            label2(img, '当初付出的股票 · 2014 年的价值', 'The stock paid, valued in 2014', W / 2, 475, a * k10, size=30, col=SUBE)
            kq = ke(t, t57 + 1.4, 0.9)
            text(img, '“To date, Dexter is the worst deal that I’ve made.”', W / 2, 560, 28, 'playfair_i', SUBW, a * kq)
            text(img, '“迄今为止，德克斯特是我做过的最糟糕的交易。”', W / 2, 610, 28, 'serif_med', SUBE, a * kq, track=0.04)
            text(img, '—— 巴菲特，2007 年致股东信', W / 2, 652, 22, 'serif_med', SUBE, a * kq, track=0.08)
    # 杠杆
    a = env(t, I['I11']['t0'] - 0.3, I['I12']['t0'] - 0.4, 0.5, 0.6)
    if a > 0:
        label2(img, '借来的钱', 'Leverage', 300, 400, a * ke(t, wt('I11', '借了钱')), size=44, col=LOSS, name='serif_bold')
        label2(img, '被迫在低点卖出', 'Forced selling', 780, 400, a * ke(t, wt('I11', '低点卖出')), size=44, col=LOSS, name='serif_bold')
        k3 = ke(t, wt('I11', '暂时') - 0.1)
        label2(img, '暂时的下跌', 'Temporary decline', 290, 545, a * k3, size=52, col=STEEL, name='serif_bold')
        formula(img, r'\Longrightarrow', W / 2 - 10, 540, 56, a * k3 * ke(t, wt('I11', '锁定')), col=SUBW)
        label2(img, '永久的损失', 'Permanent loss', 790, 545, a * ke(t, wt('I11', '永久') - 0.1), size=52, col=LOSS, name='serif_bold',
               glow=0.0)
    # 今天：两个问题
    a = env(t, I['I12']['t0'] - 0.3, I['I13']['t0'] - 0.35, 0.5, 0.6)
    if a > 0:
        formula(img, r'\mathrm{Drawdown}\;\neq\;\mathrm{Permanent\ Loss}', W / 2, 720, 58, a, wipe=eio((t - I['I12']['t0'] + 0.1) / 1.4))
        text(img, '账户大幅回撤时，先问两个问题', W / 2, 860, 36, 'serif_med', SUBE, a * ke(t, wt('I12', '两个')), track=0.1)
        for j, (kw, zh, en, y) in enumerate((('这门生意', '这门生意还在吗？', 'Is the business still intact?', 1030),
                                             ('我会', '我会被迫卖出吗？', 'Will I be forced to sell?', 1220))):
            k = ke(t, wt('I12', kw) - 0.1, 0.8)
            text(img, ('i.', 'ii.')[j], 170, y, 48, 'playfair_i', CHAMP_M, a * k, 'l')
            label2(img, zh, en, W / 2 + 30, y, a * k, size=64, name='serif_bold', gold=True, glow=0.18, wipe=k)
    # I13：整句（代替字幕）
    a = env(t, I['I13']['t0'] - 0.2, M0, 0.5, 0.25)
    if a > 0:
        for kw, s_, y, gold_, sz in (('价格', '价格的剧烈波动，', 1130, False, 52), ('不必然', '不必然意味着真正的风险；', 1215, False, 52),
                                     ('真正值得', '真正值得警惕的，', 1335, True, 60), ('本金', '是本金永久损失的可能性。', 1425, True, 60)):
            k = eio((t - wt('I13', kw) + 0.15) / 1.2)
            text(img, s_, W / 2, y, sz, 'serif_bold', SUBW, a * k, track=0.1, gold=gold_, wipe=k, glow=0.18 if gold_ else 0.0, shadow=0.8)
    if subs: narr_sub(img, t, INS['subs'], hide=('I13',))


# ---------------------------------------------------------------- 一句话总结 + 品牌片尾（系列固定片尾）
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


def ov_summary(img, t, subs=True):
    tp = END['t_particles']
    a = env(t, T_SUM - 0.05, tp + 0.4, 0.05, 0.4)
    if a <= 0: return
    k = t - T_SUM
    caps(img, 'In one sentence', W / 2, 740, 17, a * eo(k / 0.8), col=CHAMP, track=0.6)
    w1 = eio((t - VOD['M']['t0'] + 0.15) / 1.1); w2 = eio((t - wt('M', '永久') + 0.1) / 1.1)
    sh = cl((t - VOD['M']['t1'] - 0.2) / 1.4) if VOD['M']['t1'] + 0.2 < t < VOD['M']['t1'] + 1.6 else None
    text(img, '波动不是风险，', W / 2, 880, 96, 'serif_black', a=a, gold=True, wipe=w1, shine=sh, track=0.04, glow=0.18)
    text(img, '永久损失才是。', W / 2, 1010, 96, 'serif_black', a=a, gold=True, wipe=w2, shine=sh, track=0.04, glow=0.18)
    caps(img, 'Volatility is not risk · permanent loss is', W / 2, 1110, 17, a * eo((t - wt('M', '永久') - 0.6) / 0.8), track=0.3)
    text(img, '伯克希尔股东大会投资智慧录 · 第二集', W / 2, 1170, 24, 'serif_med', SUBE, a * eo((k - 1.5) / 0.8), track=0.12, shadow=0.6)


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
# 片尾前的快闪回顾：每个拍点换一个镜头（全片代表画面），最后一镜回到开场的海面
RECAP = [3.6, 8.6, 14.6, 19.4, 26.5, 61.5, 160.0, 224.5, 249.0, 262.5, 281.6, 297.0, 314.0]
RECAP_CUTS = [M0] + [float(b) for b in BEATS[(BEATS > M0 + 0.2) & (BEATS < T_SUM - 0.25)]]


def core(t, subs=True):
    lin, bk = background(t)
    lin *= 1.0 + 0.22 * fx.hit_env(t, HITS)                     # 重拍上的柔和光涌（不推镜、不闪白）
    img = s4post.finish(lin, int(t * FPS), bloom_k=bk).astype(np.float32)
    ov_cold(img, t, subs)
    ov_title(img, t, subs)
    ov_intro(img, t, subs)
    ov_s3ctx(img, t, subs)
    ov_qa(img, t, subs)
    ov_insight(img, t, subs)
    ov_summary(img, t, subs)
    s_end(img, t)
    return img


def frame(t):
    if M0 <= t < T_SUM:
        i = int(np.searchsorted(RECAP_CUTS, t, side='right')) - 1
        c0 = RECAP_CUTS[i]
        rep = RECAP[min(i, len(RECAP) - 1)] if i < len(RECAP_CUTS) - 1 else 316.5
        img = core(rep + (t - c0), subs=False)
        z = 1.0 + 0.03 * (t - c0)
        M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
        img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        img += CHAMP * 0.10 * math.exp(-(t - c0) / 0.12)
    else:
        img = core(t)
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
