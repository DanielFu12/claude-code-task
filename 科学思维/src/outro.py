"""片尾：最后一句「真相，从不害怕被检验」化作粒子 → 以官方 logo 的透明通道为遮罩汇聚 →
原始 logo 清晰浮现 → 金色「巴芒价值」+「BUFFETT · MUNGER」在重拍上划入、扫过流光 → 整片淡出。

品牌资产全部来自仓库根目录 brand/：logo 用 brand.load_logo（官方 logo_baman.png），
字体用 brand._font（思源宋体 Black / Cormorant Garamond），金色用 brand.GOLD_STOPS / SUB_GOLD。
右上角 brand.Hud 由 video.py 全程绘制，片尾不隐藏，只随整片最终淡出。
"""
import math

import numpy as np
import skia
from PIL import Image, ImageDraw

import engine as E
import timeline as T
from engine import W, H, CX, INK, GOLD, clip01, ease, ease_out, ease_io, lerp

BR = E.BRAND
LOGO_PX = 220                      # BRAND.md：片尾 logo 约 220px 居中
LOGO_C = (CX, 405)
LOGO_RGB, LOGO_A = BR.load_logo(LOGO_PX)
TITLE_Y, SUB_Y = 628, 722
FINAL_LINE = "真相，从不害怕被检验"
FINAL_Y = 520
FINAL_SIZE = 84
N = 7000


def _brand_text(txt, size, fontname, width=None, gold=True):
    """品牌字：brand._font 渲染；width 给定时两端对齐到该宽度（小字与主标题等宽）。"""
    f = BR._font(fontname, size)
    ws = [f.getlength(ch) for ch in txt]
    track = 0.0 if width is None else (width - sum(ws)) / (len(txt) - 1)
    im = Image.new("L", (int(sum(ws) + track * (len(txt) - 1) + 4 * size), int(size * 2)), 0)
    d = ImageDraw.Draw(im)
    x = size
    for ch, w in zip(txt, ws):
        d.text((x, int(size * 1.4)), ch, font=f, fill=255, anchor="ls")
        x += w + track
    m = np.asarray(im, np.float32) / 255
    ys, xs = np.where(m > 0.01)
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    if width is not None and m.shape[1] != int(round(width)):
        import cv2
        m = cv2.resize(m, (int(round(width)), m.shape[0]), interpolation=cv2.INTER_AREA)
    if gold:
        rgb = np.broadcast_to(BR._ramp(m.shape[0], BR.GOLD_STOPS)[:, None, :].astype(np.float32), m.shape + (3,)).copy()
    else:
        rgb = np.broadcast_to(np.array(BR.SUB_GOLD, np.float32) / 255, m.shape + (3,)).copy()
    return rgb, m


TITLE_RGB, TITLE_M = _brand_text("巴芒价值", 118, "serif_black")
SUB_RGB, SUB_M = _brand_text("BUFFETT · MUNGER", 34, "corm", width=TITLE_M.shape[1], gold=False)


def _sample(mask, n, seed, ox, oy):
    r = np.random.default_rng(seed)
    ys, xs = np.nonzero(mask > 0.3)
    w = mask[ys, xs].astype(np.float64)
    pick = r.choice(len(xs), n, replace=len(xs) < n, p=w / w.sum())
    return np.c_[xs[pick] + r.random(n) + ox, ys[pick] + r.random(n) + oy], pick, ys, xs


def _final_mask():
    arr = np.zeros((H, W, 4), np.uint8)
    surf = skia.Surface(arr, colorType=skia.kRGBA_8888_ColorType)
    E.text(surf.getCanvas(), FINAL_LINE, CX, FINAL_Y, FINAL_SIZE, "serif_bold", (1, 1, 1), 1.0, "c", 14)
    del surf
    return arr[..., 0].astype(np.float32) / 255


SRC_PTS, _, _, _ = _sample(_final_mask(), N, 21, 0, 0)
DST_PTS, pick, ly, lx = _sample(LOGO_A, N, 13, LOGO_C[0] - LOGO_PX / 2, LOGO_C[1] - LOGO_PX / 2)
DST_COL = LOGO_RGB[ly[pick], lx[pick]].astype(np.float32)
_r = np.random.default_rng(5)
RND = _r.random((4, N))
GN = _r.standard_normal((3, N))


def scene_final_line(ctx):
    """终句：先以文字出现，LOGO_T 时化作粒子。"""
    t, c = ctx.t, ctx.c
    t0 = T.s("e3")
    a = ease((t - t0 + 0.1) / 0.6) * (1 - ease((t - T.LOGO_T) / 0.35))
    if a > 0:
        E.text(c, FINAL_LINE, CX, FINAL_Y, FINAL_SIZE, "serif_bold", INK, a, "c", 14,
               reveal=ease((t - t0 + 0.1) / 1.4), glow=0.25, glow_rgb=GOLD)
    if t < T.LOGO_T - 0.1:
        return
    # 粒子：文字 → logo
    k = (t - T.LOGO_T) / (T.LOGO_SHOW - T.LOGO_T + 0.3)
    p = np.clip((k - RND[0] * 0.25) / 0.75, 0, 1)
    p = p * p * (3 - 2 * p)
    d = DST_PTS - SRC_PTS
    nrm = np.c_[-d[:, 1], d[:, 0]]
    curl = (np.sin(np.pi * p) * GN[0] * 0.28)[:, None]
    P = SRC_PTS + d * p[:, None] + nrm * curl
    P += np.c_[np.sin(t * 2.3 + RND[1] * 6.28), np.cos(t * 2.0 + RND[2] * 6.28)] * 1.2
    # logo 出现后粒子化作微尘散去
    ks = ease((t - T.LOGO_SHOW - 0.4) / 2.2)
    P += np.c_[GN[1], GN[2]] * 160 * ks
    col = np.array(INK, np.float32) * (1 - p[:, None]) + DST_COL * p[:, None]
    al = (0.55 + 0.25 * p) * (1 - 0.85 * ks) * clip01((T.DUR - 1.5 - t) / 1.5)
    ctx.splat(P, al[:, None] * col * 1.4)


def draw_logo(img, t):
    """后期之后合成：原始 logo + 品牌字（numpy，颜色不经过辉光/调色）。"""
    if t < T.LOGO_SHOW - 0.05:
        return
    k = ease((t - T.LOGO_SHOW) / 0.9)
    # 淡蓝光晕（BRAND.md：RGB 110,175,255）
    flash = math.exp(-(t - T.BRAND_T) / 0.35) * 1.6 if t >= T.BRAND_T else 0.0
    _halo(img, LOGO_C, 230, np.array(E.BLUE, np.float32), (0.20 + 0.15 * flash) * k)
    _blit(img, LOGO_RGB, LOGO_A, LOGO_C[0] - LOGO_PX / 2, LOGO_C[1] - LOGO_PX / 2, k)
    if t >= T.BRAND_T:
        w = clip01((t - T.BRAND_T) / 0.7)
        sh = clip01((t - T.BRAND_T - 0.9) / 1.4)      # 一次流光
        _blit(img, TITLE_RGB, TITLE_M, CX - TITLE_M.shape[1] / 2, TITLE_Y - TITLE_M.shape[0] / 2, 1.0, wipe=w,
              shine=sh)
        w2 = clip01((t - T.BRAND_T - 0.35) / 0.8)
        _blit(img, SUB_RGB, SUB_M, CX - SUB_M.shape[1] / 2, SUB_Y - SUB_M.shape[0] / 2, 1.0, wipe=w2)


_YY, _XX = None, None


def _halo(img, c, r, rgb, k):
    if k <= 0.003:
        return
    x0, x1 = int(c[0] - 2 * r), int(c[0] + 2 * r)
    y0, y1 = int(max(0, c[1] - 2 * r)), int(min(H, c[1] + 2 * r))
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    g = np.exp(-((xx - c[0]) ** 2 + (yy - c[1]) ** 2) / (2 * (r * 0.55) ** 2))
    img[y0:y1, x0:x1] += g[..., None] * rgb[None, None, :] * k


def _blit(out, rgb, a, x0, y0, alpha=1.0, wipe=1.0, shine=None):
    if alpha <= 0.003:
        return
    h, w = a.shape
    x0, y0 = int(round(x0)), int(round(y0))
    a = a * alpha
    if wipe < 1.0:
        soft = 0.35 * w + 30
        a = a * np.clip((wipe * (w + soft) - np.arange(w)) / soft, 0, 1).astype(np.float32)[None, :]
    if shine is not None and 0 < shine < 1:
        xs = np.arange(w)[None, :] + np.arange(h)[:, None] * 0.6
        pos = -60 + (0.5 - 0.5 * math.cos(shine * math.pi)) * (w + 120)
        rgb = np.clip(rgb + np.exp(-((xs - pos) / (0.06 * w + 10)) ** 2)[..., None] * 0.6, 0, 1.25)
    reg = out[y0:y0 + h, x0:x0 + w]
    reg *= 1 - a[..., None]
    reg += a[..., None] * rgb


SCENES = [
    (T.s("e3") - 0.2, T.DUR, scene_final_line),
]
