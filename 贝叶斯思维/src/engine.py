"""小型动态图形引擎：线性光合成 + 辉光 + 抗锯齿矢量 + 文字精灵 + 粒子。

帧缓冲为 float32 RGB（0..1，线性叠加），最后统一做辉光、暗角、颗粒，再交给 brand.Hud 画角标。
"""
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
W, H = 1920, 1080
CX, CY = W / 2, H / 2

# ---------------------------------------------------------------- 色板
def rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255


INK = rgb("#F2EEE6")        # 暖白：正文
GREY = rgb("#8D93A3")       # 次要文字
DIM = rgb("#4A5063")
GOLD = rgb("#FFD478")       # 品牌金（brand.GOLD_STOPS 中段）：答案 / 后验
GOLD_HI = rgb("#FFF3C8")
GOLD_DEEP = rgb("#E2A03C")
BLUE = rgb("#6EAFFF")       # 品牌 logo 光晕蓝：先验 / 数据
TEAL = rgb("#5FE3C8")       # 证据
CORAL = rgb("#FF6F61")      # 直觉 / 患病 / 反证
WHITE = np.ones(3, np.float32)

# ---------------------------------------------------------------- 缓动
def clip01(x):
    return np.clip(x, 0.0, 1.0)


def ease(x):          # cubic in-out
    x = clip01(x)
    return np.where(x < 0.5, 4 * x ** 3, 1 - (-2 * x + 2) ** 3 / 2) if isinstance(x, np.ndarray) else \
        (4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2)


def eout(x, p=3):     # ease out
    x = clip01(x)
    return 1 - (1 - x) ** p


def ein(x, p=3):
    return clip01(x) ** p


def eback(x, s=1.6):  # ease out back（轻微回弹）
    x = float(clip01(x))
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def expo_out(x):
    x = float(clip01(x))
    return 1 - 2 ** (-10 * x) if x < 1 else 1.0


def prog(t, t0, dur):
    return float(clip01((t - t0) / dur))


def window(t, t0, t1, fin=0.5, fout=0.5):
    """t0 淡入、t1 淡出完毕：返回 0..1"""
    if t < t0 or t > t1:
        return 0.0
    a = 1.0 if fin <= 0 else float(eout((t - t0) / fin, 2))
    b = 1.0 if fout <= 0 else float(clip01((t1 - t) / fout))
    return a * (b * b * (3 - 2 * b))


def lerp(a, b, k):
    return a + (b - a) * k


def mixc(a, b, k):
    return np.asarray(a, np.float32) * (1 - k) + np.asarray(b, np.float32) * k


# ---------------------------------------------------------------- 字体与文字精灵
FONT_DIR = os.path.join(ROOT, "fonts")
_FONTS = {}


def font(name, size):
    key = (name, int(size))
    if key not in _FONTS:
        _FONTS[key] = ImageFont.truetype(os.path.join(FONT_DIR, name + ".ttf"), int(size))
    return _FONTS[key]


class Sprite:
    __slots__ = ("rgb", "a", "cols", "w", "h", "ox", "oy")

    def __init__(self, rgb_, a, cols=None, ox=0, oy=0):
        self.rgb, self.a = rgb_, a
        self.h, self.w = a.shape
        self.cols = cols            # 每个字符的列中心（用于逐字显现）
        self.ox, self.oy = ox, oy   # 锚点偏移（基线左端在精灵中的位置）


_SPR = {}


def parse_hl(s):
    """'普通【强调】普通' -> [(text, is_hl)]"""
    out, cur, hl = [], "", False
    for ch in s:
        if ch == "【":
            if cur:
                out.append((cur, hl))
            cur, hl = "", True
        elif ch == "】":
            if cur:
                out.append((cur, hl))
            cur, hl = "", False
        else:
            cur += ch
    if cur:
        out.append((cur, hl))
    return out


def text_sprite(s, fname, size, color=INK, track=0.0, hl=GOLD, gradient=None, pad=None):
    """渲染一行文字。track: 字距（字号的倍数）。gradient: [(pos,(r,g,b)),...] 竖向渐变（0..255）。"""
    key = (s, fname, int(size), tuple(np.round(color, 3)), track, tuple(np.round(hl, 3)), str(gradient))
    if key in _SPR:
        return _SPR[key]
    f = font(fname, size)
    segs = parse_hl(s)
    chars = [(c, h) for seg, h in segs for c in seg]
    pad = int(size * 0.5) if pad is None else pad
    widths = [f.getlength(c) for c, _ in chars]
    tw = sum(widths) + track * size * max(0, len(chars) - 1)
    asc, desc = f.getmetrics()
    wd, ht = int(tw + 2 * pad) + 2, int(asc + desc + 2 * pad)
    m = Image.new("L", (wd, ht), 0)
    mh = Image.new("L", (wd, ht), 0)
    d, dh = ImageDraw.Draw(m), ImageDraw.Draw(mh)
    x = float(pad)
    cols = []
    for (c, h), cw in zip(chars, widths):
        (dh if h else d).text((x, pad + asc), c, font=f, fill=255, anchor="ls")
        cols.append(x + cw / 2)
        x += cw + track * size
    a1 = np.asarray(m, np.float32) / 255
    a2 = np.asarray(mh, np.float32) / 255
    a = np.clip(a1 + a2, 0, 1)
    if gradient is not None:
        ys, xs = np.where(a > 0.01)
        y0, y1 = (ys.min(), ys.max()) if len(ys) else (0, ht - 1)
        yy = np.clip((np.arange(ht) - y0) / max(1, y1 - y0), 0, 1)
        ramp = np.stack([np.interp(yy, [p for p, _ in gradient], [c[k] for _, c in gradient]) for k in range(3)], 1) / 255
        col = np.broadcast_to(ramp[:, None, :], (ht, wd, 3)).astype(np.float32)
    else:
        col = (a1[..., None] * np.asarray(color, np.float32) + a2[..., None] * np.asarray(hl, np.float32)) / \
            np.maximum(a[..., None], 1e-4)
    sp = Sprite(col.astype(np.float32), a, np.array(cols, np.float32), ox=pad, oy=pad + asc)
    _SPR[key] = sp
    return sp


def blit(out, sp, x, y, alpha=1.0, anchor="c", reveal=1.0, blur=0.0, rise=0.0, scale=1.0, mode="over",
         soft=0.18, tint=None):
    """把精灵画到 out。anchor: c=水平居中（y 为字的视觉中线）, l=左对齐, r=右对齐。
    reveal: 0..1 逐字从左到右显现（带柔边）；blur: 高斯模糊 sigma；mode: over / add"""
    if alpha <= 0.003 or reveal <= 0:
        return
    a = sp.a
    col = sp.rgb if tint is None else np.broadcast_to(np.asarray(tint, np.float32), sp.rgb.shape)
    if reveal < 1.0 and sp.cols is not None and len(sp.cols):
        n = len(sp.cols)
        # 每个字符的显现进度
        per = clip01(reveal * (n + n * soft * 4) - np.arange(n)) if n > 1 else np.array([reveal])
        per = clip01(per / (1 + soft * 4))
        xs = np.arange(sp.w, dtype=np.float32)
        colw = np.interp(xs, sp.cols, per, left=per[0], right=per[-1])
        a = a * colw[None, :]
    if scale != 1.0:
        nw, nh = max(1, int(sp.w * scale)), max(1, int(sp.h * scale))
        a = cv2.resize(a, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
        col = cv2.resize(np.ascontiguousarray(col), (nw, nh), interpolation=cv2.INTER_LINEAR)
    if blur > 0.3:
        a = cv2.GaussianBlur(a, (0, 0), blur)
    h, w = a.shape
    if anchor == "c":
        x0 = x - w / 2
    elif anchor == "l":
        x0 = x - sp.ox * scale
    else:
        x0 = x - w + sp.ox * scale
    # 视觉中线：以基线上方 0.36 字高处为中心
    y0 = y - (sp.oy * scale) + 0.38 * (sp.oy - sp.ox) * scale - rise
    composite(out, col, a * alpha, x0, y0, mode)


def composite(out, col, a, x0, y0, mode="over"):
    """亚像素位置合成（对 alpha 做双线性平移）"""
    ix, iy = int(math.floor(x0)), int(math.floor(y0))
    fx, fy = x0 - ix, y0 - iy
    h, w = a.shape
    if fx > 0.02 or fy > 0.02:
        M = np.float32([[1, 0, fx], [0, 1, fy]])
        a = cv2.warpAffine(a, M, (w + 1, h + 1), flags=cv2.INTER_LINEAR)
        if col.ndim == 3 and col.shape[:2] == (h, w):
            col = cv2.warpAffine(np.ascontiguousarray(col), M, (w + 1, h + 1), flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_REPLICATE)
        h, w = a.shape
    xs, ys = max(0, ix), max(0, iy)
    xe, ye = min(W, ix + w), min(H, iy + h)
    if xe <= xs or ye <= ys:
        return
    aa = a[ys - iy:ye - iy, xs - ix:xe - ix, None]
    cc = col[ys - iy:ye - iy, xs - ix:xe - ix] if col.ndim == 3 else col
    reg = out[ys:ye, xs:xe]
    if mode == "add":
        reg += aa * cc
    else:
        reg *= 1 - aa
        reg += aa * cc


def text(out, s, x, y, size, fname="serif_med", color=INK, alpha=1.0, anchor="c", track=0.0, hl=GOLD,
         reveal=1.0, blur=0.0, rise=0.0, scale=1.0, mode="over", gradient=None, glow=0.0, glow_buf=None):
    sp = text_sprite(s, fname, size, color, track, hl, gradient)
    blit(out, sp, x, y, alpha, anchor, reveal, blur, rise, scale, mode)
    if glow > 0 and glow_buf is not None:
        blit(glow_buf, sp, x, y, alpha * glow, anchor, reveal, max(blur, 0), rise, scale, "add")
    return sp


def anim_text(out, s, x, y, size, t, t0, t1, fname="serif_med", color=INK, anchor="c", track=0.0, hl=GOLD,
              fin=0.7, fout=0.45, alpha=1.0, gradient=None, rise_px=14, glow=0.0, glow_buf=None, blur_px=6.0):
    """标准入场：逐字模糊浮现；出场：上浮淡出。"""
    if t < t0 or t > t1:
        return
    pin = prog(t, t0, fin)
    pout = prog(t, t1 - fout, fout)
    a = alpha * (1 - ein(pout, 2))
    rise = rise_px * (1 - eout(pin, 3)) * -1 + rise_px * 0.8 * ein(pout, 2)
    rv = float(eout(pin, 2)) if pin < 1 else 1.0
    bl = blur_px * (1 - eout(pin, 2)) + 4 * ein(pout, 2)
    text(out, s, x, y, size, fname, color, a, anchor, track, hl, rv, bl, rise, 1.0, "over", gradient, glow, glow_buf)


# ---------------------------------------------------------------- 矢量（抗锯齿，1/16 像素精度）
SH = 4
SC = 1 << SH


def _pts(p):
    return (np.asarray(p, np.float64) * SC).round().astype(np.int32)


def _local(pts, pad):
    pts = np.asarray(pts, np.float64).reshape(-1, 2)
    x0, y0 = np.floor(pts.min(0) - pad).astype(int)
    x1, y1 = np.ceil(pts.max(0) + pad).astype(int)
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, W), min(y1, H)
    return x0, y0, x1, y1


def _apply(out, mask, x0, y0, color, alpha, mode):
    if mask is None:
        return
    a = mask.astype(np.float32) * (alpha / 255.0)
    reg = out[y0:y0 + a.shape[0], x0:x0 + a.shape[1]]
    c = np.asarray(color, np.float32)
    if mode == "add":
        reg += a[..., None] * c
    else:
        reg *= 1 - a[..., None]
        reg += a[..., None] * c


def polyline(out, pts, color, alpha=1.0, th=2.0, closed=False, mode="add"):
    pts = np.asarray(pts, np.float64).reshape(-1, 2)
    if len(pts) < 2 or alpha <= 0.003:
        return
    x0, y0, x1, y1 = _local(pts, th + 3)
    if x1 <= x0 or y1 <= y0:
        return
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.polylines(m, [_pts(pts - [x0, y0])], closed, 255, max(1, int(round(th))), cv2.LINE_AA, SH)
    _apply(out, m, x0, y0, color, alpha, mode)


def line(out, p, q, color, alpha=1.0, th=2.0, mode="add"):
    polyline(out, [p, q], color, alpha, th, False, mode)


def poly(out, pts, color, alpha=1.0, mode="over"):
    pts = np.asarray(pts, np.float64).reshape(-1, 2)
    if alpha <= 0.003:
        return
    x0, y0, x1, y1 = _local(pts, 2)
    if x1 <= x0 or y1 <= y0:
        return
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillPoly(m, [_pts(pts - [x0, y0])], 255, cv2.LINE_AA, SH)
    _apply(out, m, x0, y0, color, alpha, mode)


def circle(out, c, r, color, alpha=1.0, th=-1, mode="add"):
    if alpha <= 0.003 or r <= 0:
        return
    pad = r + abs(th) + 3
    x0, y0, x1, y1 = _local([[c[0] - pad, c[1] - pad], [c[0] + pad, c[1] + pad]], 0)
    if x1 <= x0 or y1 <= y0:
        return
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.circle(m, tuple(_pts([c[0] - x0, c[1] - y0])), int(round(r * SC)), 255,
               -1 if th < 0 else max(1, int(round(th))), cv2.LINE_AA, SH)
    _apply(out, m, x0, y0, color, alpha, mode)


def arc(out, c, r, a0, a1, color, alpha=1.0, th=2.0, mode="add", n=None):
    """角度（弧度），0 = 正右，顺时针为正（屏幕坐标）"""
    if abs(a1 - a0) < 1e-4:
        return
    n = n or max(8, int(abs(a1 - a0) * r / 4))
    a = np.linspace(a0, a1, n)
    polyline(out, np.c_[c[0] + r * np.cos(a), c[1] + r * np.sin(a)], color, alpha, th, False, mode)


def rect(out, x0, y0, x1, y1, color, alpha=1.0, th=-1, mode="over", r=0):
    if r <= 0:
        pts = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
    else:
        pts = rounded_pts(x0, y0, x1, y1, r)
    if th < 0:
        poly(out, pts, color, alpha, mode)
    else:
        polyline(out, pts, color, alpha, th, True, mode)


def rounded_pts(x0, y0, x1, y1, r, n=8):
    r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    pts = []
    for cx, cy, a0 in [(x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, math.pi / 2),
                       (x0 + r, y0 + r, math.pi)]:
        for k in range(n + 1):
            a = a0 + k / n * math.pi / 2
            pts.append([cx + r * math.cos(a), cy + r * math.sin(a)])
    return pts


def path_partial(pts, k):
    """折线按长度取前 k 比例"""
    pts = np.asarray(pts, np.float64)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    L = seg.sum() * clip01(k)
    if L <= 0:
        return pts[:1]
    cum = np.concatenate([[0], np.cumsum(seg)])
    i = int(np.searchsorted(cum, L) - 1)
    i = min(max(i, 0), len(seg) - 1)
    u = (L - cum[i]) / max(seg[i], 1e-9)
    return np.vstack([pts[:i + 1], pts[i] + (pts[i + 1] - pts[i]) * u])


def dashed(out, p, q, color, alpha=1.0, th=1.5, dash=10, gap=8, phase=0.0, mode="add"):
    p, q = np.asarray(p, float), np.asarray(q, float)
    L = np.linalg.norm(q - p)
    if L < 1:
        return
    d = (q - p) / L
    s = -(phase % (dash + gap))
    while s < L:
        a, b = max(s, 0), min(s + dash, L)
        if b > a:
            line(out, p + d * a, p + d * b, color, alpha, th, mode)
        s += dash + gap


# ---------------------------------------------------------------- 粒子
def splat(buf, P, C):
    """双线性散点：P (n,2) 像素坐标，C (n,3) 强度"""
    if len(P) == 0:
        return
    x, y = P[:, 0], P[:, 1]
    ok = (x >= 0) & (x < W - 1) & (y >= 0) & (y < H - 1)
    x, y, C = x[ok], y[ok], C[ok]
    x0, y0 = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = (x - x0)[:, None], (y - y0)[:, None]
    flat = buf.reshape(-1, 3)
    for dx, dy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        np.add.at(flat, (y0 + dy) * W + (x0 + dx), C * w)


def dots(buf, P, C, sigma=1.3):
    """柔和圆点：散点后做一次局部高斯模糊（等效每个点一个高斯斑）"""
    if len(P) == 0:
        return
    pts = np.asarray(P)
    x0, y0, x1, y1 = _local(pts, sigma * 4 + 2)
    if x1 <= x0 or y1 <= y0:
        return
    sub = np.zeros((y1 - y0, x1 - x0, 3), np.float32)
    Pl = pts - [x0, y0]
    hh, ww = sub.shape[:2]
    x, y = Pl[:, 0], Pl[:, 1]
    ok = (x >= 0) & (x < ww - 1) & (y >= 0) & (y < hh - 1)
    x, y, Cc = x[ok], y[ok], np.asarray(C)[ok]
    xi, yi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = (x - xi)[:, None], (y - yi)[:, None]
    flat = sub.reshape(-1, 3)
    for dx, dy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        np.add.at(flat, (yi + dy) * ww + (xi + dx), Cc * w)
    sub = cv2.GaussianBlur(sub, (0, 0), sigma) * (2 * math.pi * sigma * sigma)
    buf[y0:y1, x0:x1] += sub


def glow_spot(buf, c, r, color, k):
    """径向柔光（加色）"""
    if k <= 0.003:
        return
    x0, y0, x1, y1 = _local([[c[0] - 3 * r, c[1] - 3 * r], [c[0] + 3 * r, c[1] + 3 * r]], 0)
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    g = np.exp(-((xx - c[0]) ** 2 + (yy - c[1]) ** 2) / (2 * r * r)) * k
    buf[y0:y1, x0:x1] += g[..., None] * np.asarray(color, np.float32)


def glow_rect(buf, x0, y0, x1, y1, color, k, sigma=30):
    """矩形柔光"""
    if k <= 0.003:
        return
    pad = int(sigma * 3)
    X0, Y0, X1, Y1 = _local([[x0 - pad, y0 - pad], [x1 + pad, y1 + pad]], 0)
    if X1 <= X0 or Y1 <= Y0:
        return
    xs = np.arange(X0, X1, dtype=np.float32)
    ys = np.arange(Y0, Y1, dtype=np.float32)
    from math import sqrt
    fxv = 0.5 * (_erf((xs - x0) / (sigma * sqrt(2))) - _erf((xs - x1) / (sigma * sqrt(2))))
    fyv = 0.5 * (_erf((ys - y0) / (sigma * sqrt(2))) - _erf((ys - y1) / (sigma * sqrt(2))))
    buf[Y0:Y1, X0:X1] += (fyv[:, None] * fxv[None, :] * k)[..., None] * np.asarray(color, np.float32)


def _erf(x):
    # Abramowitz-Stegun 近似，足够做柔光
    s = np.sign(x)
    x = np.abs(x)
    t = 1 / (1 + 0.3275911 * x)
    y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * np.exp(-x * x)
    return s * y


# ---------------------------------------------------------------- 图片资产
_IMG = {}


def icon(name, px, color=WHITE):
    """assets/*.png（白色 + alpha）按高度 px 缩放，返回 Sprite（居中锚点）"""
    key = (name, int(px), tuple(np.round(color, 3)))
    if key not in _IMG:
        im = np.asarray(Image.open(os.path.join(ROOT, "assets", name + ".png")).convert("RGBA")).astype(np.float32) / 255
        a = im[..., 3]
        ys, xs = np.where(a > 0.01)
        a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        s = px / a.shape[0]
        a = cv2.resize(a, (max(1, int(a.shape[1] * s)), int(px)), interpolation=cv2.INTER_AREA)
        col = np.broadcast_to(np.asarray(color, np.float32), a.shape + (3,)).copy()
        sp = Sprite(col, a)
        sp.ox, sp.oy = a.shape[1] / 2, a.shape[0] / 2
        _IMG[key] = sp
    return _IMG[key]


def blit_icon(out, sp, x, y, alpha=1.0, mode="over", scale=1.0):
    a = sp.a
    col = sp.rgb
    if scale != 1.0:
        nw, nh = max(1, int(sp.w * scale)), max(1, int(sp.h * scale))
        a = cv2.resize(a, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
        col = np.broadcast_to(sp.rgb[0, 0], a.shape + (3,))
    composite(out, col, a * alpha, x - a.shape[1] / 2, y - a.shape[0] / 2, mode)


def mask_points(a, n, rng, thresh=0.4):
    """从 alpha 蒙版按权重采样 n 个点（像素坐标，相对蒙版左上角）"""
    ys, xs = np.nonzero(a > thresh)
    w = a[ys, xs].astype(np.float64)
    pick = rng.choice(len(xs), n, replace=len(xs) < n, p=w / w.sum())
    return np.c_[xs[pick] + rng.random(n), ys[pick] + rng.random(n)], pick, (ys, xs)


# ---------------------------------------------------------------- 后期
def bloom(out, strength=1.0, thresh=0.55):
    small = cv2.resize(out, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    lum = small.max(axis=2, keepdims=True)
    hi = small * np.clip((lum - thresh) / (1 - thresh + 1e-6), 0, 1.5)
    g1 = cv2.GaussianBlur(hi, (0, 0), 2.5)
    s2 = cv2.resize(hi, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
    g2 = cv2.GaussianBlur(s2, (0, 0), 4.0)
    s3 = cv2.resize(s2, (W // 16, H // 16), interpolation=cv2.INTER_AREA)
    g3 = cv2.GaussianBlur(s3, (0, 0), 5.0)
    g = cv2.resize(g1, (W, H)) * 0.55 + cv2.resize(g2, (W, H)) * 0.6 + cv2.resize(g3, (W, H)) * 0.7
    out += g * strength
    return out


def tonemap(out):
    """柔和高光压缩，避免硬剪切"""
    hi = out > 0.82
    out[hi] = 0.82 + 0.18 * (1 - np.exp(-(out[hi] - 0.82) / 0.18))
    return out


_VIG = None
_GRAIN = None


def vignette(out, k=1.0):
    global _VIG
    if _VIG is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = ((xx - CX) / (W * 0.62)) ** 2 + ((yy - CY) / (H * 0.62)) ** 2
        _VIG = (1 - 0.42 * np.clip(d, 0, 1.6) ** 1.25).astype(np.float32)[..., None]
    out *= 1 - (1 - _VIG) * k
    return out


def grain(out, t, k=0.014):
    global _GRAIN
    if _GRAIN is None:
        r = np.random.default_rng(5)
        _GRAIN = [cv2.GaussianBlur(r.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 0.7) for _ in range(6)]
    g = _GRAIN[int(t * 24) % 6]
    out += (g * k)[..., None]
    return out


def chroma(out, k):
    """色差：R/B 通道从中心向外微移"""
    if k < 0.05:
        return out
    s = 1 + 0.0025 * k
    for ch, sc in ((0, s), (2, 1 / s)):
        M = np.float32([[sc, 0, CX * (1 - sc)], [0, sc, CY * (1 - sc)]])
        out[..., ch] = cv2.warpAffine(np.ascontiguousarray(out[..., ch]), M, (W, H), flags=cv2.INTER_LINEAR,
                                      borderMode=cv2.BORDER_REFLECT)
    return out


def zoom(out, s, cx=CX, cy=CY, dx=0.0, dy=0.0):
    if abs(s - 1) < 1e-4 and abs(dx) < 0.05 and abs(dy) < 0.05:
        return out
    M = np.float32([[s, 0, cx * (1 - s) + dx], [0, s, cy * (1 - s) + dy]])
    return cv2.warpAffine(out, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def to_u8(out):
    return (np.clip(out, 0, 1) ** (1 / 1.0) * 255 + 0.5).astype(np.uint8)
