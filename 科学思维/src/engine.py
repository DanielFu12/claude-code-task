"""小型动态图形引擎：skia 矢量绘制 + numpy 粒子/辉光后期。

所有绘制都在 1920×1080、30 fps 下进行；画面是时间 t 的纯函数。
"""
import math
import os
import sys

import cv2
import numpy as np
import skia

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "..", "brand"))
import brand as BRAND  # noqa: E402  仓库根目录 brand/：官方角标、logo、金色

W, H, FPS = 1920, 1080, 30
CX, CY = W / 2, H / 2

# ---------------------------------------------------------------- 色板
INK = (0.93, 0.94, 0.97)
DIM = (0.62, 0.65, 0.72)
GREY = (0.42, 0.45, 0.52)
CYAN = (0.38, 0.80, 1.00)
BLUE = tuple(v / 255 for v in BRAND.SPEC["glow_rgb"])          # 品牌 logo 光晕蓝
GOLD = tuple(v / 255 for v in BRAND.GOLD_STOPS[1][1])           # 品牌主金 #FFD478
GOLD_D = tuple(v / 255 for v in BRAND.GOLD_STOPS[2][1])         # 深金 #E2A03C
SUBGOLD = tuple(v / 255 for v in BRAND.SUB_GOLD)                # 小字金 #D6B270
RED = (1.00, 0.36, 0.36)
GREEN = (0.36, 0.92, 0.62)
FIRE = (1.00, 0.55, 0.20)

# ---------------------------------------------------------------- 工具


def clip01(x):
    if isinstance(x, np.ndarray):
        return np.clip(x, 0.0, 1.0)
    return max(0.0, min(1.0, x))


def ease(x):
    x = clip01(x)
    return x * x * (3 - 2 * x)


def ease_out(x, p=3):
    x = clip01(x)
    return 1 - (1 - x) ** p


def ease_in(x, p=3):
    return clip01(x) ** p


def ease_io(x):
    x = clip01(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def back_out(x, s=1.7):
    x = clip01(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def lerp(a, b, k):
    return a + (b - a) * k


def mixc(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def win(t, t0, t1, fi=0.5, fo=0.5):
    """t0 处淡入、t1 处淡出的窗口（0..1）。"""
    if t < t0 or t > t1 + fo:
        return 0.0
    return ease((t - t0) / fi if fi > 0 else 1) * (1 - ease((t - t1) / fo) if fo > 0 else 1.0)


# ---------------------------------------------------------------- 字体与绘制
FONT_DIR = os.path.join(ROOT, "fonts")
_TF, _FONT = {}, {}


def typeface(name):
    if name not in _TF:
        _TF[name] = skia.Typeface.MakeFromFile(os.path.join(FONT_DIR, name + ".ttf"))
    return _TF[name]


def font(name, size):
    key = (name, round(size * 4) / 4)
    if key not in _FONT:
        f = skia.Font(typeface(name), key[1])
        f.setEdging(skia.Font.Edging.kAntiAlias)
        f.setSubpixel(True)
        f.setHinting(skia.FontHinting.kNone)
        _FONT[key] = f
    return _FONT[key]


def c4(rgb, a=1.0):
    return skia.Color4f(float(rgb[0]), float(rgb[1]), float(rgb[2]), float(max(0.0, min(1.0, a))))


def paint(rgb=INK, a=1.0, stroke=None, blur=0.0, shader=None, cap="round", blend=None, dash=None, trim=None):
    p = skia.Paint(AntiAlias=True)
    p.setColor4f(c4(rgb, a))
    if stroke is not None:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap if cap == "round" else skia.Paint.kButt_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur > 0:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if shader is not None:
        p.setShader(shader)
        p.setAlphaf(float(max(0.0, min(1.0, a))))
    if blend == "add":
        p.setBlendMode(skia.BlendMode.kPlus)
    elif blend == "screen":
        p.setBlendMode(skia.BlendMode.kScreen)
    if dash is not None:
        p.setPathEffect(skia.DashPathEffect.Make(dash[0], dash[1]))
    if trim is not None:
        t0, t1 = float(max(0.0, trim[0])), float(min(1.0, trim[1]))
        if t1 <= t0 + 1e-4:
            p.setAlphaf(0.0)
        elif t0 > 0 or t1 < 1:
            fx = skia.TrimPathEffect.Make(t0, t1)
            if fx is not None:
                p.setPathEffect(fx)
    return p


def gold_shader(y_top, y_bot):
    """品牌金色竖向渐变（brand.GOLD_STOPS）。"""
    stops = BRAND.GOLD_STOPS
    return skia.GradientShader.MakeLinear(
        [skia.Point(0, y_top), skia.Point(0, y_bot)],
        [c4(tuple(v / 255 for v in s[1])) for s in stops], [s[0] for s in stops])


FALLBACK = {"inter_thin": "sans_light", "inter_light": "sans_light", "inter_med": "sans_med", "inter_bold": "sans_bold",
            "mono": "sans_reg", "corm": "serif_med", "corm6": "serif_med"}
_HAS = {}


def _has(fn, ch):
    key = (fn, ch)
    if key not in _HAS:
        _HAS[key] = typeface(fn).unicharToGlyph(ord(ch)) != 0
    return _HAS[key]


def _fonts_for(s, fn, size):
    """逐字选择字体：拉丁字体缺字时回退到思源黑/宋。"""
    fb = FALLBACK.get(fn)
    out = []
    for ch in s:
        use = fn if (fb is None or _has(fn, ch)) else fb
        out.append(font(use, size))
    return out


MIN_TEXT = 22


def measure(s, size, fn="sans_reg", track=0.0):
    size = max(size, MIN_TEXT)
    fs = _fonts_for(s, fn, size)
    return sum(f.measureText(ch) for f, ch in zip(fs, s)) + track * max(0, len(s) - 1)


def text(c, s, x, y, size, fn="sans_reg", rgb=INK, a=1.0, align="c", track=0.0, reveal=None,
         rise=0.0, shader=None, blur=0.0, glow=0.0, glow_rgb=None, spread=3.0, baseline="m"):
    """画一行字。align: l/c/r；baseline 'm' 表示 y 为视觉中线；reveal 0..1 逐字显现。"""
    if a <= 0.002 or not s:
        return 0.0
    size = max(size, MIN_TEXT)          # 手机上也要看得清：全片最小字号
    fs = _fonts_for(s, fn, size)
    ws = [f.measureText(ch) for f, ch in zip(fs, s)]
    tw = sum(ws) + track * (len(s) - 1)
    x0 = x - (tw / 2 if align == "c" else tw if align == "r" else 0)
    yb = y + size * 0.36 if baseline == "m" else y
    n = len(s)
    if glow > 0:
        gp = paint(glow_rgb or rgb, a * glow, blur=size * 0.18)
        _draw_chars(c, s, ws, x0, yb, fs, gp, track, reveal, rise, n, spread)
    p = paint(rgb, a, blur=blur, shader=shader)
    _draw_chars(c, s, ws, x0, yb, fs, p, track, reveal, rise, n, spread)
    return tw


def _draw_chars(c, s, ws, x0, yb, fs, p, track, reveal, rise, n, spread):
    if reveal is None and track == 0 and all(f is fs[0] for f in fs):
        c.drawString(s, x0, yb, fs[0], p)
        return
    x = x0
    base_a = p.getAlphaf()
    for i, ch in enumerate(s):
        k = 1.0 if reveal is None else ease((reveal * (n + spread) - i) / spread)
        if k > 0.003 and ch != " ":
            p.setAlphaf(base_a * k)
            c.drawString(ch, x, yb + rise * (1 - k), fs[i], p)
        x += ws[i] + track
    p.setAlphaf(base_a)


def rrect(c, x, y, w, h, r, p):
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), p)


def line(c, x0, y0, x1, y1, rgb=INK, a=1.0, w=2.0, k=1.0, blur=0.0, dash=None):
    """k: 从起点画出的比例（描线动画）。"""
    if a <= 0.002 or k <= 0:
        return
    c.drawLine(x0, y0, lerp(x0, x1, k), lerp(y0, y1, k), paint(rgb, a, stroke=w, blur=blur, dash=dash))


def arrow(c, x0, y0, x1, y1, rgb=INK, a=1.0, w=3.0, k=1.0, head=16, gap0=0, gap1=0):
    if a <= 0.002 or k <= 0:
        return
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1
    ux, uy = dx / L, dy / L
    sx, sy = x0 + ux * gap0, y0 + uy * gap0
    ex, ey = x1 - ux * gap1, y1 - uy * gap1
    ex, ey = lerp(sx, ex, k), lerp(sy, ey, k)
    p = paint(rgb, a, stroke=w)
    c.drawLine(sx, sy, ex - ux * head * 0.5, ey - uy * head * 0.5, p)
    pa = skia.Path()
    pa.moveTo(ex, ey)
    pa.lineTo(ex - ux * head - uy * head * 0.55, ey - uy * head + ux * head * 0.55)
    pa.lineTo(ex - ux * head + uy * head * 0.55, ey - uy * head - ux * head * 0.55)
    pa.close()
    c.drawPath(pa, paint(rgb, a))


def glow_dot(c, x, y, r, rgb, a=1.0, halo=3.0):
    if a <= 0.002:
        return
    c.drawCircle(x, y, r * halo, paint(rgb, a * 0.35, blur=r * halo * 0.6))
    c.drawCircle(x, y, r, paint(rgb, a))


def check(c, x, y, s, rgb=GREEN, a=1.0, k=1.0, w=None):
    pa = skia.Path()
    pa.moveTo(x - s * 0.5, y)
    pa.lineTo(x - s * 0.12, y + s * 0.38)
    pa.lineTo(x + s * 0.55, y - s * 0.42)
    c.drawPath(pa, paint(rgb, a, stroke=w or s * 0.14, trim=(0, k)))


def cross(c, x, y, s, rgb=RED, a=1.0, k=1.0, w=None):
    k1, k2 = clip01(k * 2), clip01(k * 2 - 1)
    p = paint(rgb, a, stroke=w or s * 0.14)
    if k1 > 0:
        c.drawLine(x - s / 2, y - s / 2, x - s / 2 + s * k1, y - s / 2 + s * k1, p)
    if k2 > 0:
        c.drawLine(x + s / 2, y - s / 2, x + s / 2 - s * k2, y - s / 2 + s * k2, p)


def image_from(arr_rgba_u8):
    return skia.Image.fromarray(np.ascontiguousarray(arr_rgba_u8), colorType=skia.kRGBA_8888_ColorType)


# ---------------------------------------------------------------- 粒子（numpy 加色）


def splat(buf, P, Wt):
    """双线性加色点。P: N×2 像素坐标，Wt: N×3 颜色权重。"""
    Hh, Ww = buf.shape[:2]
    ok = (P[:, 0] > 0) & (P[:, 0] < Ww - 1.01) & (P[:, 1] > 0) & (P[:, 1] < Hh - 1.01)
    P, Wt = P[ok], Wt[ok]
    if not len(P):
        return
    x0 = np.floor(P[:, 0]).astype(np.int64)
    y0 = np.floor(P[:, 1]).astype(np.int64)
    fx, fy = P[:, 0] - x0, P[:, 1] - y0
    idx = np.concatenate([y0 * Ww + x0, y0 * Ww + x0 + 1, (y0 + 1) * Ww + x0, (y0 + 1) * Ww + x0 + 1])
    ww = np.concatenate([(1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy])
    flat = buf.reshape(-1, 3)
    for ch in range(3):
        flat[:, ch] += np.bincount(idx, weights=ww * np.tile(Wt[:, ch], 4), minlength=Ww * Hh)[:Ww * Hh].astype(np.float32)


# ---------------------------------------------------------------- 背景


def _blob_field(seed, n=7):
    r = np.random.default_rng(seed)
    return r.random((n, 2)), 0.12 + r.random(n) * 0.25, r.random((n, 2)) * 6.28


_BG_YY, _BG_XX = np.mgrid[0:H // 8, 0:W // 8].astype(np.float32)
_BG_YY /= (H // 8)
_BG_XX /= (W // 8)
_BLOBS = _blob_field(7)


def nebula(t, tint, strength=1.0):
    """缓慢流动的星云（低分辨率计算再放大）。"""
    pos, rad, ph = _BLOBS
    acc = np.zeros_like(_BG_XX)
    for (px, py), r, (a, b) in zip(pos, rad, ph):
        x = px + 0.06 * math.sin(0.05 * t + a)
        y = py + 0.05 * math.cos(0.04 * t + b)
        acc += np.exp(-(((_BG_XX - x) * 1.78) ** 2 + (_BG_YY - y) ** 2) / (r * r))
    acc = acc / acc.max()
    small = acc[..., None] * np.asarray(tint, np.float32)[None, None, :] * strength
    return cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC)


_VY, _VX = np.mgrid[0:H, 0:W].astype(np.float32)
VIGNETTE = (1 - 0.42 * (((_VX - CX) / CX) ** 2 * 0.55 + ((_VY - CY) / CY) ** 2 * 0.45)).clip(0, 1)[..., None]
BASE = np.array([0.016, 0.020, 0.036], np.float32)
_GRAIN = np.random.default_rng(3).normal(0, 1, (6, H // 2, W // 2)).astype(np.float32)


def post(img, t, bloom=1.0, vign=1.0, grain=1.0, ca=0.0):
    """辉光、暗角、色差、颗粒。img: float32 H×W×3（原地修改并返回）。"""
    if bloom > 0:
        hi = np.maximum(img - 0.55, 0)
        s4 = cv2.resize(hi, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        g1 = cv2.GaussianBlur(s4, (0, 0), 3.0)
        s8 = cv2.resize(s4, (W // 16, H // 16), interpolation=cv2.INTER_AREA)
        g2 = cv2.GaussianBlur(s8, (0, 0), 3.5)
        img += bloom * (cv2.resize(g1, (W, H), interpolation=cv2.INTER_LINEAR) * 0.55 +
                        cv2.resize(g2, (W, H), interpolation=cv2.INTER_LINEAR) * 0.75)
    if ca > 0.01:
        sh = int(round(ca * 6))
        if sh:
            img[:, sh:, 0] = img[:, :-sh, 0]
            img[:, :-sh, 2] = img[:, sh:, 2]
    if vign > 0:
        img *= 1 - vign * (1 - VIGNETTE)
    # 柔和高光压缩
    hi = img > 0.85
    img[hi] = 0.85 + 0.15 * (1 - np.exp(-(img[hi] - 0.85) / 0.15))
    if grain > 0:
        g = _GRAIN[int(t * FPS) % len(_GRAIN)]
        img += cv2.resize(g, (W, H), interpolation=cv2.INTER_NEAREST)[..., None] * (0.010 * grain)
    return img
