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


# ================================================================ v4：卡点与质感组件
UP = (1.0, 0.27, 0.30)      # A 股习惯：红涨
DOWN = (0.18, 0.86, 0.52)   # 绿跌


def pop(x, s=2.2):
    """带回弹的出现（0→1，略冲过头再回落）。"""
    return back_out(x, s)


def slam(c, s, x, y, size, t, t0, fn="serif_black", rgb=INK, a=1.0, track=0.0, shader=None, glow=0.0,
         glow_rgb=None, align="c", dur=0.22):
    """砸入式大字：在拍点 t0 上从 1.5 倍缩回原大小，前 3 帧带残影。"""
    if t < t0 - 0.01 or a <= 0.003:
        return 0.0
    k = ease_out((t - t0) / dur, 3)
    sc = lerp(1.5, 1.0, k)
    al = a * clip01((t - t0) / 0.06 + 0.15)
    c.save()
    c.translate(x, y)
    c.scale(sc, sc)
    if k < 0.98:
        for j in (2, 1):
            c.save()
            c.scale(1 + 0.06 * j * (1 - k), 1 + 0.06 * j * (1 - k))
            text(c, s, 0, 0, size, fn, rgb, al * 0.18 * (1 - k), align, track, shader=shader)
            c.restore()
    w = text(c, s, 0, 0, size, fn, rgb, al, align, track, shader=shader, glow=glow, glow_rgb=glow_rgb)
    c.restore()
    return w


def gold8(c, x, y, size, t, a=1.0, spin=0.0, crack=0.0, glow=1.0):
    """主角：立体金色「8」。spin 为绕竖轴的旋转角（弧度），crack 0..1 为裂纹。"""
    if a <= 0.003:
        return
    f = font("serif_black", size)
    w = f.measureText("8")
    sx = math.cos(spin)
    c.save()
    c.translate(x, y)
    c.scale(max(abs(sx), 0.04) * (1 if sx >= 0 else -1), 1)
    # 光晕
    c.drawCircle(0, 0, size * 0.55, paint(GOLD, 0.16 * a * glow, blur=size * 0.25))
    yb = size * 0.36
    # 挤出的厚度（深金）
    for d in range(10, 0, -1):
        c.drawString("8", -w / 2 + d * 0.9, yb + d * 1.2, f, paint(mixc((0.35, 0.20, 0.05), GOLD_D, 1 - d / 10), a))
    # 正面：金色渐变
    c.drawString("8", -w / 2, yb, f, paint(shader=gold_shader(-size * 0.5, size * 0.5), a=a))
    # 扫光
    ph = (t * 0.45) % 1.6
    if ph < 1.0:
        sh = skia.GradientShader.MakeLinear(
            [skia.Point(-w + ph * 2 * w - size * 0.2, -size * 0.6), skia.Point(-w + ph * 2 * w + size * 0.2, size * 0.6)],
            [c4((1, 1, 1), 0), c4((1, 0.98, 0.9), 0.75), c4((1, 1, 1), 0)], [0, 0.5, 1])
        c.drawString("8", -w / 2, yb, f, paint(shader=sh, a=a))
    if crack > 0:
        r = np.random.default_rng(88)
        for k in range(6):
            pa = skia.Path()
            ang = r.random() * math.tau
            px, py = math.cos(ang) * size * 0.08, math.sin(ang) * size * 0.2
            pa.moveTo(px, py)
            for _ in range(5):
                ang += (r.random() - 0.5) * 1.2
                px += math.cos(ang) * size * 0.10
                py += math.sin(ang) * size * 0.12
                pa.lineTo(px, py)
            c.drawPath(pa, paint(RED, 0.9 * a, stroke=size * 0.06, blur=size * 0.03, trim=(0, crack)))
            c.drawPath(pa, paint((0.08, 0.03, 0.02), a, stroke=size * 0.026, trim=(0, crack)))
            c.drawPath(pa, paint((1, 0.85, 0.75), 0.9 * a, stroke=size * 0.008, trim=(0, crack)))
    c.restore()


def candles(c, x0, y0, w, h, data, k=1.0, a=1.0, vmin=None, vmax=None, glow=True):
    """K 线（红涨绿跌）。data: [(open, high, low, close), ...]；k 为从左到右长出的比例。"""
    if a <= 0.003:
        return
    n = len(data)
    lo = vmin if vmin is not None else min(d[2] for d in data)
    hi = vmax if vmax is not None else max(d[1] for d in data)

    def Y(v):
        return y0 + h - (v - lo) / (hi - lo + 1e-9) * h
    cw = w / n
    shown = k * n
    for i, (o, hh, ll, cl) in enumerate(data):
        if i >= shown:
            break
        kk = clip01(shown - i)
        col = UP if cl >= o else DOWN
        x = x0 + (i + 0.5) * cw
        c.drawLine(x, Y(hh), x, Y(ll), paint(col, a * kk, stroke=max(1.2, cw * 0.08)))
        top, bot = Y(max(o, cl)), Y(min(o, cl))
        rrect(c, x - cw * 0.32, top, cw * 0.64, max(bot - top, 2) * kk, 2, paint(col, a * kk))
        if glow:
            rrect(c, x - cw * 0.32, top, cw * 0.64, max(bot - top, 2) * kk, 2, paint(col, 0.35 * a * kk, blur=6))


def make_ohlc(n, seed, drift=0.6, vol=2.0, start=100.0):
    r = np.random.default_rng(seed)
    out, v = [], start
    for _ in range(n):
        o = v
        v = v * (1 + (drift + r.normal(0, vol)) / 100)
        hi, lo = max(o, v) * (1 + r.random() * vol / 200), min(o, v) * (1 - r.random() * vol / 200)
        out.append((o, hi, lo, v))
    return out


def pigeon(c, x, y, sc, a, t, mode="idle", rgb=(0.62, 0.66, 0.78), phase=0.0):
    """鸽子（侧视，朝右）。mode: idle / spin（逆时针转圈）/ corner（把头伸向角落）/ pendulum（钟摆晃头）。"""
    if a <= 0.003:
        return
    c.save()
    c.translate(x, y)
    flip, tilt, hx, hy = 1.0, 0.0, 0.0, 0.0
    tt = t + phase
    if mode == "spin":
        flip = math.cos(tt * 4.0)
    elif mode == "corner":
        k = 0.5 + 0.5 * math.sin(tt * 3.0)
        hx, hy, tilt = 18 * k, -26 * k, -10 * k
    elif mode == "pendulum":
        tilt = 16 * math.sin(tt * 4.2)
    bob = 2 * math.sin(tt * 7)
    c.scale(sc * (flip if abs(flip) > 0.05 else 0.05), sc)
    c.rotate(tilt)
    body = paint(rgb, a)
    # 尾巴
    tail = skia.Path()
    tail.moveTo(-48, 6)
    tail.lineTo(-112, -6)
    tail.lineTo(-108, 16)
    tail.lineTo(-46, 24)
    tail.close()
    c.drawPath(tail, paint(mixc(rgb, (0.2, 0.22, 0.3), 0.4), a))
    # 身体
    c.drawOval(skia.Rect.MakeLTRB(-66, -34 + bob, 58, 36 + bob), body)
    # 翅膀
    wing = skia.Path()
    wing.moveTo(-40, -10 + bob)
    wing.cubicTo(-10, -30 + bob, 30, -20 + bob, 40, 0 + bob)
    wing.cubicTo(10, 10 + bob, -20, 14 + bob, -40, -10 + bob)
    c.drawPath(wing, paint(mixc(rgb, (0.25, 0.27, 0.36), 0.45), a))
    for k_ in range(3):
        c.drawLine(-30 + k_ * 16, -2 + bob, -14 + k_ * 16, 6 + bob, paint((0.15, 0.16, 0.22), 0.7 * a, stroke=2.5))
    # 脖子与头（彩虹色颈羽）
    neck_sh = skia.GradientShader.MakeLinear([skia.Point(30, -50), skia.Point(60, -10)],
                                             [c4((0.35, 0.85, 0.75)), c4((0.62, 0.42, 0.9)), c4(rgb)], [0, 0.5, 1])
    neck = skia.Path()
    neck.moveTo(26, -24 + bob)
    neck.cubicTo(30 + hx * 0.5, -50 + hy * 0.5 + bob, 50 + hx, -66 + hy + bob, 62 + hx, -54 + hy + bob)
    neck.lineTo(56, -10 + bob)
    neck.close()
    c.drawPath(neck, paint(shader=neck_sh, a=a))
    hxp, hyp = 60 + hx, -60 + hy + bob
    c.drawCircle(hxp, hyp, 20, paint(mixc(rgb, (0.8, 0.82, 0.9), 0.2), a))
    beak = skia.Path()
    beak.moveTo(hxp + 16, hyp - 4)
    beak.lineTo(hxp + 34, hyp + 2)
    beak.lineTo(hxp + 16, hyp + 6)
    beak.close()
    c.drawPath(beak, paint((0.95, 0.75, 0.45), a))
    c.drawCircle(hxp + 6, hyp - 4, 4.5, paint((1.0, 0.55, 0.2), a))
    c.drawCircle(hxp + 6, hyp - 4, 2, paint((0.05, 0.05, 0.05), a))
    # 腿
    for lx in (-6, 12):
        c.drawLine(lx, 32 + bob, lx - 4, 60, paint((0.95, 0.45, 0.45), a, stroke=4))
    c.restore()


_BOKEH = np.random.default_rng(42).random((3, 70, 5))   # 三层景深光斑：x, y, 半径, 相位, 颜色


def bokeh(t, tint, pulse=0.0, strength=1.0):
    """景深光斑背景（四分之一分辨率绘制再模糊放大）。"""
    w4, h4 = W // 4, H // 4
    buf = np.zeros((h4, w4, 3), np.float32)
    for li, layer in enumerate(_BOKEH):
        sp = (li + 1) * 3.0
        for (x, y, r, ph, cc) in layer:
            px = (x * w4 + t * sp * (0.4 + ph)) % (w4 + 40) - 20
            py = (y * h4 + 6 * math.sin(t * 0.3 + ph * 6)) % h4
            rad = 2 + r * (3 + li * 4)
            col = np.array(tint, np.float32) * (0.8 + 0.6 * cc) * (0.25 + 0.15 * li)
            cv2.circle(buf, (int(px), int(py)), int(rad), tuple(float(v) for v in col), -1, cv2.LINE_AA)
    buf = cv2.GaussianBlur(buf, (0, 0), 2.2)
    return cv2.resize(buf, (W, H), interpolation=cv2.INTER_LINEAR) * strength * (1 + 0.6 * pulse)


def zoom_blur(img, amount, n=6):
    """径向变焦模糊（转场用）。"""
    if amount <= 0.002:
        return img
    acc = img.copy()
    for i in range(1, n):
        s = 1 + amount * i / n
        M = np.float32([[s, 0, CX * (1 - s)], [0, s, CY * (1 - s)]])
        acc += cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return acc / n


# ================================================================ v4：剪辑与通用部件
def cutin(t, t0, t1, fi=0.07, fo=0.10):
    """硬切窗口：t0 起 fi 秒内出现，t1 前 fo 秒内消失（节拍上的“切”）。"""
    if t < t0 or t >= t1:
        return 0.0
    ki = ease((t - t0) / fi) if fi > 0 else 1.0
    ko = 1 - ease((t - t1 + fo) / fo) if fo > 0 else 1.0
    return ki * ko


def punch(t, t0, amt=0.10, dur=0.32):
    """切入时的镜头冲击：从 1+amt 缩回 1。"""
    if t < t0:
        return 1 + amt
    return 1 + amt * (1 - ease_out((t - t0) / dur, 3))


def beats_since(t, t0):
    return (t - t0) / BEAT_


def beat_env(t, t0, n=64, every=1.0, tau=0.14):
    """t0 之后每 every 拍一次的衰减脉冲（0..1）。"""
    if t < t0:
        return 0.0
    k = (t - t0) / (BEAT_ * every)
    if k > n:
        return 0.0
    return math.exp(-(k - math.floor(k)) * BEAT_ * every / tau)


BEAT_ = 0.5314021732630634
_BR = np.random.default_rng(9).random((4, 900))


def burst(ctx, t, t0, x, y, rgb, n=500, speed=700, life=0.9, a=1.0, spread=(0, math.tau), gain=2.2):
    """粒子迸发（加色）：在拍点 t0 从 (x, y) 炸开。"""
    k = (t - t0) / life
    if k < 0 or k > 1 or a <= 0.003:
        return
    n = min(n, _BR.shape[1])
    ang = spread[0] + _BR[0, :n] * (spread[1] - spread[0])
    sp = speed * (0.15 + 0.85 * _BR[1, :n] ** 1.5)
    d = sp * (1 - (1 - k) ** 3) * life * 0.45
    P = np.c_[x + np.cos(ang) * d, y + np.sin(ang) * d + 120 * k * k]
    al = ((1 - k) ** 2 * (0.4 + 0.6 * _BR[2, :n]) * a * gain).astype(np.float32)
    ctx.splat(P, al[:, None] * np.asarray(rgb, np.float32)[None, :])


def glass(c, x, y, w, h, r=22, a=1.0, edge=INK, edge_a=0.22, fill=(0.05, 0.06, 0.10), fill_a=0.82, glow=0.0,
          glow_rgb=None):
    """深色玻璃卡片：底 + 上沿高光 + 描边。"""
    if a <= 0.003:
        return
    rrect(c, x + 6, y + 14, w, h, r, paint((0, 0, 0), 0.45 * a, blur=24))
    rrect(c, x, y, w, h, r, paint(fill, fill_a * a))
    sh = skia.GradientShader.MakeLinear([skia.Point(0, y), skia.Point(0, y + h)],
                                        [c4((1, 1, 1), 0.07), c4((1, 1, 1), 0.0)], [0, 0.45])
    rrect(c, x, y, w, h, r, paint(shader=sh, a=a))
    rrect(c, x, y, w, h, r, paint(edge, edge_a * a, stroke=1.4))
    if glow > 0:
        rrect(c, x, y, w, h, r, paint(glow_rgb or GOLD, glow * a, stroke=6, blur=14))


def code_text(c, code, x, y, size, a=1.0, align="c", fn="mono", base=INK, hl="8", glow=0.6):
    """股票代码：其中的 8 用品牌金色并发光。"""
    if a <= 0.003:
        return 0.0
    tw = measure(code, size, fn, size * 0.08)
    x0 = x - (tw / 2 if align == "c" else tw if align == "r" else 0)
    for ch in code:
        cw = measure(ch, size, fn)
        if ch in hl:
            text(c, ch, x0, y, size, fn, GOLD, a, "l", glow=glow, glow_rgb=GOLD)
        else:
            text(c, ch, x0, y, size, fn, base, a * (0.55 if ch == "•" else 1.0), "l")
        x0 += cw + size * 0.08
    return tw


def spark(c, x0, y0, w, h, vals, rgb, a=1.0, k=1.0, width=3.0, fill=True):
    """迷你走势线（vals 归一化到 0..1，k 为画出比例）。"""
    if a <= 0.003 or k <= 0:
        return
    n = len(vals)
    p = skia.Path()
    m = max(2, int(round(1 + (n - 1) * k)))
    for i in range(m):
        X = x0 + w * i / (n - 1)
        Y = y0 + h * (1 - vals[i])
        (p.moveTo if i == 0 else p.lineTo)(X, Y)
    if fill:
        q = skia.Path(p)
        q.lineTo(x0 + w * (m - 1) / (n - 1), y0 + h)
        q.lineTo(x0, y0 + h)
        q.close()
        sh = skia.GradientShader.MakeLinear([skia.Point(0, y0), skia.Point(0, y0 + h)],
                                            [c4(rgb, 0.35), c4(rgb, 0.0)], [0, 1])
        c.drawPath(q, paint(shader=sh, a=a))
    c.drawPath(p, paint(rgb, a, stroke=width))
    c.drawPath(p, paint(rgb, 0.4 * a, stroke=width * 3, blur=6))


def walk(n, seed, drift=0.02, vol=0.06, lo=0.08, hi=0.92):
    """归一化随机游走（0..1）。"""
    r = np.random.default_rng(seed)
    v = np.cumsum(r.normal(drift, vol, n))
    v = (v - v.min()) / (np.ptp(v) + 1e-9)
    return lo + v * (hi - lo)


def trade_card(c, x, y, a, code, pct, t=0.0, w=480, h=150, label="买入", glow=0.0, k_num=1.0, seed=1):
    """一笔交易记录（A 股红涨绿跌）。(x, y) 为卡片中心。"""
    if a <= 0.003:
        return
    up = pct >= 0
    col = UP if up else DOWN
    x0, y0 = x - w / 2, y - h / 2
    glass(c, x0, y0, w, h, 20, a, edge=col, edge_a=0.45, glow=glow, glow_rgb=col)
    text(c, label, x0 + 28, y0 + 36, 22, "sans_med", DIM, a, "l", 2)
    code_text(c, code, x0 + 28, y0 + 92, 38, a, "l")
    v = pct * k_num
    text(c, f"{v:+.1f}%", x0 + w - 28, y0 + 84, 48, "inter_bold", col, a, "r", glow=0.35, glow_rgb=col)
    vals = walk(24, seed, 0.03 if up else -0.03, 0.05)
    spark(c, x0 + w - 190, y0 + 112, 160, 26, vals, col, a * 0.8, 1.0, 2.0, fill=False)
