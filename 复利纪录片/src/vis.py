"""第三版画面的基础组件：局部区域的抗锯齿辉光线 / 点 / 填充、角框面板、动态文字、背景氛围、解说字幕。
所有绘制都只在元素包围盒附近计算（不做整帧模糊），保证逐帧渲染速度。"""
import math
import numpy as np, cv2
from engine import (W, H, GOLD, GOLD_HI, GOLD_DEEP, GOLD_SUB, CYAN, BLUE, RED, WHITE, GREY, smooth, clamp01, ease_out,
                    ease_io, ease_back, win, lerp, splat)
from common import backdrop, put_text, gold_text, TextBlock, draw_block

INK_T = np.array([0.93, 0.91, 0.86], np.float32)        # 正文暖白
DIM = np.array([0.62, 0.64, 0.70], np.float32)


# ------------------------------------------------------------------ 局部辉光绘制
def _roi(pts, pad):
    p = np.asarray(pts, np.float32).reshape(-1, 2)
    x0 = int(max(math.floor(p[:, 0].min() - pad), 0)); x1 = int(min(math.ceil(p[:, 0].max() + pad), W))
    y0 = int(max(math.floor(p[:, 1].min() - pad), 0)); y1 = int(min(math.ceil(p[:, 1].max() + pad), H))
    return x0, y0, x1, y1


def _glowmask(m, width, glow):
    if glow <= 0: return m
    return m + cv2.GaussianBlur(m, (0, 0), max(width * 2.5, 1.5)) * glow * 1.2 + cv2.GaussianBlur(m, (0, 0), max(width * 8, 4)) * glow * 0.6


def line(F, pts, color, width=2.0, alpha=1.0, glow=0.8, closed=False):
    """抗锯齿折线（亚像素）+ 局部辉光"""
    pts = np.asarray(pts, np.float32).reshape(-1, 2)
    if len(pts) < 2 or alpha <= 0.003: return
    pad = width * 10 * (1 if glow > 0 else 0.2) + 4
    x0, y0, x1, y1 = _roi(pts, pad)
    if x1 <= x0 or y1 <= y0: return
    m = np.zeros((y1 - y0, x1 - x0), np.float32)
    p = np.round((pts - [x0, y0]) * 16).astype(np.int32).reshape(-1, 1, 2)
    cv2.polylines(m, [p], closed, 1.0, max(1, int(round(width))), cv2.LINE_AA, shift=4)
    if width < 1: m *= width
    g = _glowmask(m, width, glow)
    F[y0:y1, x0:x1] += g[..., None] * (np.asarray(color, np.float32) * alpha)


def dashed(F, p0, p1, color, width=1.5, alpha=1.0, dash=14, gap=10, glow=0.3, phase=0.0):
    p0, p1 = np.asarray(p0, np.float32), np.asarray(p1, np.float32)
    L = float(np.linalg.norm(p1 - p0))
    if L < 1: return
    d = (p1 - p0) / L
    s = -phase % (dash + gap) - (dash + gap)
    segs = []
    while s < L:
        a, b = max(s, 0), min(s + dash, L)
        if b > a: segs.append((p0 + d * a, p0 + d * b))
        s += dash + gap
    for a, b in segs:
        line(F, [a, b], color, width, alpha, glow)


def dot(F, x, y, r, color, alpha=1.0, glow=1.0):
    if alpha <= 0.003: return
    pad = r * (16 if glow > 0 else 1.5) + 3
    x0, y0, x1, y1 = _roi([[x, y]], pad)
    if x1 <= x0 or y1 <= y0: return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d2 = (xx - x) ** 2 + (yy - y) ** 2
    core = np.clip(r + 0.5 - np.sqrt(d2), 0, 1)
    g = core + np.exp(-d2 / (2 * (r * 2.2) ** 2)) * glow * 0.9 + np.exp(-d2 / (2 * (r * 6) ** 2)) * glow * 0.35
    F[y0:y1, x0:x1] += g[..., None] * (np.asarray(color, np.float32) * alpha)


def fill_poly(F, pts, color, alpha=1.0, top=None, bottom=None, grad=(1.0, 0.0)):
    """多边形填充，可加竖向渐变（top..bottom 之间不透明度从 grad[0] 到 grad[1]）"""
    pts = np.asarray(pts, np.float32).reshape(-1, 2)
    if alpha <= 0.003 or len(pts) < 3: return
    x0, y0, x1, y1 = _roi(pts, 2)
    if x1 <= x0 or y1 <= y0: return
    m = np.zeros((y1 - y0, x1 - x0), np.float32)
    cv2.fillPoly(m, [np.round((pts - [x0, y0]) * 16).astype(np.int32)], 1.0, cv2.LINE_AA, shift=4)
    if top is not None:
        ys = np.arange(y0, y1, dtype=np.float32)
        k = np.clip((ys - top) / max(bottom - top, 1), 0, 1)
        m *= (grad[0] + (grad[1] - grad[0]) * k)[:, None]
    F[y0:y1, x0:x1] += m[..., None] * (np.asarray(color, np.float32) * alpha)


def darken_box(F, x0, y0, x1, y1, amt, feather=40):
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    X0, Y0, X1, Y1 = max(x0 - feather, 0), max(y0 - feather, 0), min(x1 + feather, W), min(y1 + feather, H)
    if X1 - X0 < 2 or Y1 - Y0 < 2: return                     # 完全在画面外
    m = np.zeros((Y1 - Y0, X1 - X0), np.float32)
    m[max(y0 - Y0, 0):max(y1 - Y0, 0), max(x0 - X0, 0):max(x1 - X0, 0)] = 1
    m = cv2.GaussianBlur(m, (0, 0), feather / 2.5)
    F[Y0:Y1, X0:X1] *= (1 - amt * m)[..., None]


def bracket(F, x0, y0, x1, y1, color=GOLD, alpha=1.0, L=34, width=1.6, glow=0.4, plate=0.0):
    """科技感角框（四个角各一段折线），可加暗底"""
    if alpha <= 0.003: return
    if plate > 0: darken_box(F, x0, y0, x1, y1, plate * alpha, 30)
    for (x, y, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        line(F, [(x + dx * L, y), (x, y), (x, y + dy * L)], color, width, alpha, glow)
    line(F, [(x0 + L + 8, y0), (x1 - L - 8, y0)], color, 0.8, alpha * 0.28, 0)
    line(F, [(x0 + L + 8, y1), (x1 - L - 8, y1)], color, 0.8, alpha * 0.28, 0)


# ------------------------------------------------------------------ 文字动效
def rise(F, text, x, y, size, t, t0, name='serif_m', color=INK_T, a=1.0, maxw=980, dur=0.55, glow=0.0, align='center', lh=1.4):
    """淡入 + 轻微上浮（逐字错开）"""
    k = clamp01((t - t0) / dur)
    if k <= 0 or a <= 0.003: return None
    return put_text(F, text, x, y + 16 * (1 - ease_out(k)), size, name, color, a * smooth(k * 1.2), maxw, align,
                    reveal=clamp01((t - t0) / (dur + 0.02 * len(text))), glow=glow, lh=lh, shadow=0.6)


def slam(F, text, x, y, size, t, t0, a=1.0, gold=True, color=None, name='serif', dur=0.32, maxw=1000):
    """重拍砸入：从 1.35 倍缩到 1 倍，伴随辉光衰减"""
    k = ease_out(clamp01((t - t0) / dur))
    if k <= 0 or a <= 0.003: return
    sz = int(size * (1 + 0.35 * (1 - k)))
    g = 0.35 + 1.2 * (1 - k) + 0.6 * math.exp(-max(t - t0, 0) * 3)
    if gold:
        gold_text(F, text, x, y, sz, name, a * min(1, k * 1.8), 1.0, glow=g, maxw=maxw)
    else:
        put_text(F, text, x, y, sz, name, color if color is not None else WHITE, a * min(1, k * 1.8), maxw, glow=g * 0.5, shadow=0.5)


def counter(v, fmt):
    return fmt(v)


# ------------------------------------------------------------------ 背景
_r = np.random.default_rng(31)
STARS = np.c_[_r.uniform(-1, 1, 260), _r.uniform(-1, 1, 260), _r.uniform(0.1, 1, 260), _r.uniform(0, 1, 260)].astype(np.float32)


def starfield(F, t, a=1.0, speed=0.035, cy=900, warm=0.75):
    """缓慢飘向镜头的微粒（视差景深）"""
    if a <= 0.003: return
    z = (STARS[:, 2] - t * speed) % 1.0 + 0.06
    px = W / 2 + STARS[:, 0] * 560 / z
    py = cy + STARS[:, 1] * 980 / z
    ok = (px > -10) & (px < W + 10) & (py > -10) & (py < H + 10)
    s = np.minimum(1.0, 0.22 / z)
    col = np.where(STARS[:, 3:4] < warm, GOLD_HI[None, :] * 0.9, CYAN[None, :] * 0.8)
    al = a * 0.32 * s * np.clip(1 - z, 0, 1) * (0.6 + 0.4 * np.sin(t * 1.3 + STARS[:, 3] * 20))
    splat(F, px[ok], py[ok], (0.9 + 2.0 * s[ok]).astype(np.float32), col[ok], al[ok].astype(np.float32))


def grid_floor(F, t, a, horizon=1230, speed=0.25, color=GOLD):
    if a <= 0.003: return
    vx = W / 2
    for k in range(-9, 10):
        line(F, [(vx + k * 8, horizon), (vx + k * 170, H)], color, 1.0, a * 0.09 * (1 - abs(k) / 11), 0)
    ph = (t * speed) % 1.0
    for i in range(12):
        z = (i + 1 - ph) / 12.0
        y = horizon + (H - horizon) * z ** 2.2
        line(F, [(0, y), (W, y)], color, 1.0, a * 0.10 * z, 0)
    line(F, [(0, horizon), (W, horizon)], color, 1.0, a * 0.16, 0.6)


MOODS = {
    'cool': dict(c1=(0.008, 0.012, 0.03), c2=(0.02, 0.04, 0.09), neb=(0.05, 0.12, 0.30), neb_amt=0.35),
    'warm': dict(c1=(0.012, 0.010, 0.010), c2=(0.045, 0.035, 0.025), neb=(0.20, 0.14, 0.07), neb_amt=0.28),
    'neutral': dict(c1=(0.010, 0.011, 0.016), c2=(0.03, 0.032, 0.045), neb=(0.10, 0.11, 0.16), neb_amt=0.25),
    'red': dict(c1=(0.014, 0.008, 0.008), c2=(0.05, 0.02, 0.02), neb=(0.22, 0.06, 0.05), neb_amt=0.3),
}


def bg(t, mood='neutral', stars=1.0, drift=0.5):
    F = backdrop(t, drift=drift, **MOODS[mood])
    starfield(F, t, stars)
    return F


# ------------------------------------------------------------------ 解说字幕
SUB_Y = 1585
SUB_COL = np.array([0.97, 0.96, 0.93], np.float32)


def balance(text, size, maxw=960, name='sans_b'):
    from engine import font
    f = font(name, size)
    if f.getlength(text) <= maxw: return text
    best = None
    for i, ch in enumerate(text[:-1]):
        if ch in '，、：；—':
            a_, b_ = text[:i + 1], text[i + 1:]
            if f.getlength(a_) <= maxw and f.getlength(b_) <= maxw:
                d = abs(f.getlength(a_) - f.getlength(b_))
                if best is None or d < best[0]: best = (d, i + 1)
    if best is None:                       # 没有合适的标点：在中点附近找一个不拆开专有名词的位置
        mid = len(text) // 2
        bad = set()
        for term in KEEP:
            i = text.find(term)
            while i >= 0:
                bad.update(range(i + 1, i + len(term))); i = text.find(term, i + 1)
        cands = [k for k in range(4, len(text) - 3) if k not in bad and f.getlength(text[:k]) <= maxw and f.getlength(text[k:]) <= maxw]
        if not cands: return text
        k = min(cands, key=lambda k: abs(k - mid))
        return text[:k] + '\n' + text[k:]
    k = best[1]
    return text[:k] + '\n' + text[k:].lstrip('—')


KEEP = ['格雷厄姆与多德', '格雷厄姆', '哥伦比亚商学院', '哥伦比亚', '伯克希尔', '巴菲特', '芒格', '李录', '诺贝尔经济学奖',
        '长期资本管理公司', '对冲基金', '年度活动', '喜马拉雅资本', '复利', '股东大会', '致股东信', '前所未有', '三十出头']


def vo_sub(F, t, sents, hide=()):
    """当前句解说字幕：整句淡入（70ms），句间几乎硬切；超过两行时按语义拆成两屏"""
    for sid, s in sents.items():
        if sid in hide: continue
        if s['t0'] - 0.07 <= t <= s['t1'] + 0.12:
            txt = s['text']
            al = min(smooth((t - s['t0'] + 0.07) / 0.07), smooth((s['t1'] + 0.12 - t) / 0.08))
            parts = _screens(txt)
            if len(parts) > 1:                      # 长句按字数比例分屏
                n = sum(len(p) for p in parts); acc = 0
                for p in parts:
                    a_ = s['t0'] + (s['t1'] - s['t0']) * acc / n; acc += len(p)
                    b_ = s['t0'] + (s['t1'] - s['t0']) * acc / n
                    if a_ - 0.07 <= t <= b_ + 0.05:
                        txt = p; break
            tb = TextBlock(balance(txt, 46), 'sans_b', 46, 1000, 'center', 1.42)
            draw_block(F, tb, W / 2, SUB_Y, SUB_COL, al, shadow=1.0)
            return


def _screens(txt):
    """超过约 40 字的句子，在中间附近的句读处拆成两屏"""
    if len(txt) <= 40: return [txt]
    best = None
    for i, ch in enumerate(txt):
        if ch in '：；，。—' and 10 < i < len(txt) - 8:
            d = abs(i - len(txt) / 2)
            if best is None or d < best[0]: best = (d, i + 1)
    if not best: return [txt]
    return [txt[:best[1]].rstrip('，'), txt[best[1]:].lstrip('—')]
