"""竖屏动态图形引擎（1080×1920）：加色光层 + 多级辉光、3D 相机、文字排版、玻璃卡片、粒子。

坐标单位是像素，颜色是 0..1 的 RGB 浮点。所有画面都是时间 t 的纯函数，便于并行分段渲染。
"""
import math
import os
import sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from timeline import W, H, FPS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
FONT_DIR = os.path.join(ROOT, 'fonts')
sys.path.insert(0, os.path.join(ROOT, '..', 'brand'))
import brand as BR                     # noqa: E402  品牌模块（只从仓库 brand/ 读取）

# ---------------------------------------------------------------- 颜色
def C(r, g, b):
    return np.array([r, g, b], np.float32) / 255.0


GOLD = C(255, 212, 120)        # 品牌主金 #FFD478
GOLD_HI = C(255, 243, 200)     # #FFF3C8
GOLD_DK = C(226, 160, 60)      # #E2A03C
SUBGOLD = np.array(BR.SUB_GOLD, np.float32) / 255
ICE = C(110, 200, 255)
ICE_HI = C(200, 238, 255)
ICE_DK = C(40, 110, 200)
CORAL = C(255, 96, 92)
WHITE = C(246, 243, 236)
GREY = C(150, 160, 182)
DIM = C(95, 105, 128)
VIOLET = C(150, 120, 255)
TEAL = C(80, 230, 200)
BRANDBLUE = np.array(BR.SPEC['glow_rgb'], np.float32) / 255
GOLD_RAMP = BR.GOLD_STOPS                         # 品牌金色竖向渐变
ICE_RAMP = [(0.0, (225, 246, 255)), (0.45, (140, 215, 255)), (1.0, (70, 150, 235))]
CORAL_RAMP = [(0.0, (255, 210, 200)), (0.5, (255, 120, 110)), (1.0, (230, 70, 70))]
WHITE_RAMP = [(0.0, (255, 255, 255)), (1.0, (222, 222, 230))]


# ---------------------------------------------------------------- 缓动
def cl(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ss(x):
    if isinstance(x, np.ndarray):
        x = np.clip(x, 0.0, 1.0)
    else:
        x = cl(x)
    return x * x * (3 - 2 * x)


def eo(x):
    x = np.clip(x, 0.0, 1.0) if isinstance(x, np.ndarray) else cl(x)
    return 1 - (1 - x) ** 3


def eo5(x):
    x = cl(x)
    return 1 - (1 - x) ** 5


def ei(x):
    x = cl(x)
    return x ** 3


def eio(x):
    x = cl(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def eback(x, s=1.6):
    x = cl(x)
    if x <= 0.0:          # 起点精确为 0（否则浮点误差会让「g > 0」的判断提前成立）
        return 0.0
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


def lerp(a, b, x):
    return a + (b - a) * x


def win(t, t0, t1, fi=0.4, fo=0.4):
    """t0..t1 的显隐包络（淡入 fi 秒、淡出 fo 秒）"""
    if t < t0 or t > t1:
        return 0.0
    a = ss((t - t0) / fi) if fi > 0 else 1.0
    b = ss((t1 - t) / fo) if fo > 0 else 1.0
    return min(a, b)


def prog(t, t0, dur):
    return cl((t - t0) / dur)


# ---------------------------------------------------------------- 字体与文字
FONTS = {k: os.path.join(FONT_DIR, k + '.ttf') for k in [
    'serif_black', 'serif_bold', 'serif_med', 'serif_light', 'sans_light', 'sans_reg', 'sans_med', 'sans_bold',
    'sans_black', 'inter_light', 'inter_med', 'inter_bold', 'inter_xbold', 'corm', 'corm_bold']}


@lru_cache(256)
def font(name, size):
    if name in ('brand_title', 'brand_sub'):
        return BR._font('serif_black' if name == 'brand_title' else 'corm', size)
    return ImageFont.truetype(FONTS[name], size)


HL = {'【': ('】', 'gold'), '〔': ('〕', 'ice'), '〖': ('〗', 'coral')}


def parse(s):
    """'借钱【明天】' → [(char, style), ...]"""
    out, style = [], None
    close = None
    for ch in s:
        if ch in HL and style is None:
            close, style = HL[ch]
            continue
        if style is not None and ch == close:
            style, close = None, None
            continue
        out.append((ch, style))
    return out


@lru_cache(4096)
def glyph(ch, fname, size):
    f = font(fname, size)
    asc, desc = f.getmetrics()
    adv = f.getlength(ch)
    pad = int(size * 0.2) + 2
    w = int(math.ceil(adv)) + 2 * pad
    h = asc + desc + 2 * pad
    im = Image.new('L', (w, h), 0)
    ImageDraw.Draw(im).text((pad, pad + asc), ch, font=f, fill=255, anchor='ls')
    return np.asarray(im, np.float32) / 255.0, adv, pad, pad + asc, asc, desc


def ramp_rows(h, stops):
    y = np.linspace(0, 1, h)
    return np.stack([np.interp(y, [s[0] for s in stops], [s[1][c] for s in stops]) for c in range(3)], 1).astype(
        np.float32) / 255.0


@lru_cache(512)
def text_block(s, fname, size, track=0.0, base='white', hlstyle=None):
    """渲染一行带高亮的文字 → (alpha HxW, rgb HxWx3, baseline_y, char_x_ranges)
    base: 'white' / 'grey' / 'gold' / 'ice' / 'coral' / 'dim' / 'subgold'；高亮字按 GOLD/ICE/CORAL 竖向渐变上色。"""
    items = parse(s)
    f = font(fname, size)
    asc, desc = f.getmetrics()
    tr = track * size
    widths = [glyph(c, fname, size)[1] for c, _ in items]
    total = sum(widths) + tr * max(len(items) - 1, 0)
    pad = int(size * 0.3) + 4
    Wd = int(math.ceil(total)) + 2 * pad
    Hd = asc + desc + 2 * pad
    A = np.zeros((Hd, Wd), np.float32)
    style_map = np.zeros((Hd, Wd), np.int8)
    ranges = []
    x = float(pad)
    codes = {None: 0, 'gold': 1, 'ice': 2, 'coral': 3}
    for (c, st), wdt in zip(items, widths):
        g, adv, gp, gb, _, _ = glyph(c, fname, size)
        ox = int(round(x)) - gp
        oy = pad + asc - gb
        y0, x0 = max(oy, 0), max(ox, 0)
        y1, x1 = min(oy + g.shape[0], Hd), min(ox + g.shape[1], Wd)
        sub = g[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
        A[y0:y1, x0:x1] = np.maximum(A[y0:y1, x0:x1], sub)
        if st:
            m = sub > 0.02
            style_map[y0:y1, x0:x1][m] = codes[st]
        ranges.append((x, x + adv))
        x += wdt + tr
    # 颜色：竖向渐变（只在字形高度内）
    ys = np.where(A.max(1) > 0.02)[0]
    gy0, gy1 = (ys.min(), ys.max() + 1) if len(ys) else (0, Hd)
    def col_for(stops):
        r = np.zeros((Hd, 3), np.float32)
        r[gy0:gy1] = ramp_rows(gy1 - gy0, stops)
        r[:gy0] = r[gy0] if gy0 < Hd else 0
        r[gy1:] = r[gy1 - 1]
        return r
    bases = {
        'white': WHITE_RAMP, 'grey': [(0, (165, 175, 196)), (1, (140, 150, 172))],
        'dim': [(0, (110, 120, 142)), (1, (95, 104, 125))],
        'gold': GOLD_RAMP, 'ice': ICE_RAMP, 'coral': CORAL_RAMP,
        'subgold': [(0, tuple(int(v) for v in BR.SUB_GOLD)), (1, tuple(int(v) for v in BR.SUB_GOLD))],
    }
    RGB = np.broadcast_to(col_for(bases[base])[:, None, :], (Hd, Wd, 3)).copy()
    for st, stops in ((1, GOLD_RAMP), (2, ICE_RAMP), (3, CORAL_RAMP)):
        m = style_map == st
        if m.any():
            # 高亮色按整段字形高度渐变；对 alpha 做轻微膨胀，避免边缘残留底色
            m = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
            RGB[m] = np.broadcast_to(col_for(stops)[:, None, :], (Hd, Wd, 3))[m]
    return A, RGB, pad + asc, tuple(ranges), pad


def text_size(s, fname, size, track=0.0):
    A, _, _, _, pad = text_block(s, fname, size, track)
    return A.shape[1] - 2 * pad, A.shape[0]


# ---------------------------------------------------------------- 帧
class Frame:
    def __init__(self, t):
        self.t = t
        self.L = np.zeros((H, W, 3), np.float32)     # 加色光（清晰 + 辉光）
        self.B = np.zeros((H, W, 3), np.float32)     # 只进辉光
        self.ov = []                                  # 辉光之后合成的覆盖层（文字、卡片）
        self.zoom = 1.0
        self.cam = (0.0, 0.0)                         # 画面平移（像素）
        self.rot = 0.0
        self.flash = 0.0
        self.ca = 0.0                                 # 色差像素
        self.bloom = 1.0
        self.bg_tint = None

    # ------------------------------------------------ 基础绘制（局部包围盒，抗锯齿）
    def _mask_poly(self, pts_list, closed, th, fill):
        allp = np.concatenate([np.asarray(p, np.float64).reshape(-1, 2) for p in pts_list], 0)
        m = th + 3
        x0, y0 = int(max(math.floor(allp[:, 0].min()) - m, 0)), int(max(math.floor(allp[:, 1].min()) - m, 0))
        x1, y1 = int(min(math.ceil(allp[:, 0].max()) + m, W)), int(min(math.ceil(allp[:, 1].max()) + m, H))
        if x1 <= x0 or y1 <= y0:
            return None
        mask = np.zeros((y1 - y0, x1 - x0), np.uint8)
        polys = [((np.asarray(p, np.float64).reshape(-1, 2) - [x0, y0]) * 16).astype(np.int32).reshape(-1, 1, 2)
                 for p in pts_list]
        if fill:
            cv2.fillPoly(mask, polys, 255, cv2.LINE_AA, 4)
        else:
            cv2.polylines(mask, polys, closed, 255, max(1, int(round(th))), cv2.LINE_AA, 4)
        return mask, x0, y0, x1, y1

    def stroke(self, pts, col, a=1.0, th=2.0, closed=False, glow=0.0, layer='L'):
        if a <= 0.003 or len(pts) < 2:
            return
        r = self._mask_poly([pts], closed, th, False)
        if r is None:
            return
        mask, x0, y0, x1, y1 = r
        v = (mask.astype(np.float32) / 255.0 * a)[..., None] * np.asarray(col, np.float32)
        getattr(self, layer)[y0:y1, x0:x1] += v
        if glow > 0:
            self.B[y0:y1, x0:x1] += v * glow

    def fill(self, pts, col, a=1.0, layer='L', glow=0.0):
        if a <= 0.003:
            return
        r = self._mask_poly([pts], True, 1, True)
        if r is None:
            return
        mask, x0, y0, x1, y1 = r
        v = (mask.astype(np.float32) / 255.0 * a)[..., None] * np.asarray(col, np.float32)
        getattr(self, layer)[y0:y1, x0:x1] += v
        if glow > 0:
            self.B[y0:y1, x0:x1] += v * glow

    def line(self, p0, p1, col, a=1.0, th=2.0, glow=0.0, layer='L'):
        self.stroke([p0, p1], col, a, th, False, glow, layer)

    def circle(self, c, r, col, a=1.0, th=2.0, glow=0.0, n=None, layer='L'):
        if r <= 0.5:
            return
        n = n or int(max(24, min(220, r * 0.8)))
        ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
        self.stroke(np.stack([c[0] + r * np.cos(ang), c[1] + r * np.sin(ang)], 1), col, a, th, True, glow, layer)

    def disc(self, c, r, col, a=1.0, glow=0.0, layer='L'):
        if r <= 0.4:
            return
        n = int(max(16, min(160, r * 1.2)))
        ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
        self.fill(np.stack([c[0] + r * np.cos(ang), c[1] + r * np.sin(ang)], 1), col, a, layer, glow)

    def arc(self, c, r, a0, a1, col, a=1.0, th=2.0, glow=0.0, layer='L'):
        if abs(a1 - a0) < 1e-3:
            return
        n = int(max(8, abs(a1 - a0) * r * 0.25))
        ang = np.linspace(a0, a1, n)
        self.stroke(np.stack([c[0] + r * np.cos(ang), c[1] + r * np.sin(ang)], 1), col, a, th, False, glow, layer)

    def rrect_pts(self, x0, y0, x1, y1, r):
        r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
        pts = []
        for cx, cy, s in ((x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, math.pi / 2),
                          (x0 + r, y0 + r, math.pi)):
            for k in range(10):
                ang = s + k / 9 * math.pi / 2
                pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        return np.array(pts)

    def rrect(self, x0, y0, x1, y1, r, col, a=1.0, th=2.0, glow=0.0, layer='L'):
        self.stroke(self.rrect_pts(x0, y0, x1, y1, r), col, a, th, True, glow, layer)

    def rrect_fill(self, x0, y0, x1, y1, r, col, a=1.0, layer='L', glow=0.0):
        self.fill(self.rrect_pts(x0, y0, x1, y1, r), col, a, layer, glow)

    def glow(self, c, r, col, a=1.0, layer='B'):
        """高斯光斑"""
        if a <= 0.003 or r <= 0.5:
            return
        R = int(r * 3)
        x0, y0, x1, y1 = int(c[0]) - R, int(c[1]) - R, int(c[0]) + R + 1, int(c[1]) + R + 1
        X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
        if X1 <= X0 or Y1 <= Y0:
            return
        if r > 30:      # 大光斑：在 1/4 网格上算再放大
            q = 4
            yy, xx = np.ogrid[Y0:Y1:q, X0:X1:q]
            g = np.exp(-((xx - c[0]) ** 2 + (yy - c[1]) ** 2) / (2 * r * r)).astype(np.float32) * a
            g = cv2.resize(g, (X1 - X0, Y1 - Y0), interpolation=cv2.INTER_LINEAR)
        else:
            yy, xx = np.ogrid[Y0:Y1, X0:X1]
            g = np.exp(-((xx - c[0]) ** 2 + (yy - c[1]) ** 2) / (2 * r * r)).astype(np.float32) * a
        getattr(self, layer)[Y0:Y1, X0:X1] += g[..., None] * np.asarray(col, np.float32)

    def splat(self, xs, ys, cols, a=1.0, layer='L'):
        """双线性点溅射（亚像素平滑）。cols: (N,3) 或 (3,)；a: 标量或 (N,)"""
        xs = np.asarray(xs, np.float64)
        ys = np.asarray(ys, np.float64)
        if xs.size == 0:
            return
        cols = np.broadcast_to(np.asarray(cols, np.float32), (xs.size, 3))
        aa = np.broadcast_to(np.asarray(a, np.float32), (xs.size,))
        x0 = np.floor(xs).astype(np.int64)
        y0 = np.floor(ys).astype(np.int64)
        fx = (xs - x0).astype(np.float32)
        fy = (ys - y0).astype(np.float32)
        buf = getattr(self, layer)
        flat = buf.reshape(-1, 3)
        for dx, dy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            xi, yi = x0 + dx, y0 + dy
            ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H) & (aa > 0.002)
            if not ok.any():
                continue
            idx = yi[ok] * W + xi[ok]
            np.add.at(flat, idx, cols[ok] * (w[ok] * aa[ok])[:, None])

    def dots(self, xs, ys, rad, cols, a=1.0, layer='L'):
        """一批小圆点（半径 1~6 像素）：按半径分组，用预计算的高斯核贴图"""
        xs = np.asarray(xs, np.float64)
        ys = np.asarray(ys, np.float64)
        rad = np.broadcast_to(np.asarray(rad, np.float64), xs.shape)
        cols = np.broadcast_to(np.asarray(cols, np.float32), (xs.size, 3))
        aa = np.broadcast_to(np.asarray(a, np.float32), (xs.size,))
        buf = getattr(self, layer)
        small = rad < 1.2
        if small.any():
            self.splat(xs[small], ys[small], cols[small], aa[small] * (rad[small] / 1.2) ** 2 * 1.6, layer)
        big = ~small
        for i in np.where(big & (aa > 0.004))[0]:
            r = rad[i]
            k = _disc_kernel(round(r * 2) / 2)
            hk = k.shape[0] // 2
            cx, cy = int(round(xs[i])), int(round(ys[i]))
            X0, Y0, X1, Y1 = cx - hk, cy - hk, cx + hk + 1, cy + hk + 1
            x0, y0, x1, y1 = max(X0, 0), max(Y0, 0), min(X1, W), min(Y1, H)
            if x1 <= x0 or y1 <= y0:
                continue
            buf[y0:y1, x0:x1] += k[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0, None] * (cols[i] * aa[i])

    # ------------------------------------------------ 文字（加入覆盖层，辉光之后合成）
    def text(self, s, x, y, size, fname='serif_bold', base='white', a=1.0, anchor='c', track=0.0,
             rise=0.0, wipe=None, glow=0.25, shadow=0.55, scale=1.0, blur=0.0, glowcol=None, stagger=None):
        """anchor: 'c' 中心 / 'l' 左 / 'r' 右（y 为文字竖直中心）
        rise: 整体上移像素；wipe: 0..1 从左到右的柔和擦除；stagger: (t_local, per_char_delay, dur) 逐字浮现"""
        if a <= 0.003:
            return
        self.ov.append(('text', s, x, y, size, fname, base, a, anchor, track, rise, wipe, glow, shadow, scale, blur,
                        glowcol, stagger))

    def card(self, x0, y0, x1, y1, r=28, a=1.0, tint=(1, 1, 1), border=None, border_a=0.5, fill_a=0.08,
             blur=18, glowb=0.0):
        """磨砂玻璃卡片：模糊背后画面 + 半透明提亮 + 渐变描边"""
        if a <= 0.003:
            return
        self.ov.append(('card', x0, y0, x1, y1, r, a, tint, border, border_a, fill_a, blur, glowb))

    def image(self, rgb, alpha, cx, cy, a=1.0, scale=1.0):
        if a <= 0.003:
            return
        self.ov.append(('image', rgb, alpha, cx, cy, a, scale))

    def overlay_fn(self, fn):
        self.ov.append(('fn', fn))

    def overlay_draw(self, fn):
        """fn(canvas)：在覆盖层阶段直接往成片上画线条（例如卡片上的图标）"""
        self.ov.append(('draw', fn))


@lru_cache(64)
def _disc_kernel(r):
    R = int(math.ceil(r * 2.2)) + 1
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
    d = np.sqrt(xx ** 2 + yy ** 2)
    core = np.clip(r + 0.5 - d, 0, 1)
    halo = np.exp(-(d / (r * 1.2)) ** 2) * 0.35
    return np.maximum(core, halo).astype(np.float32)


# ---------------------------------------------------------------- 覆盖层合成
def blit_text(img, B, item):
    (_, s, x, y, size, fname, base, a, anchor, track, rise, wipe, glow, shadow, scale, blur, glowcol, stagger) = item
    sz = max(6, int(round(size * scale)))
    A, RGB, basey, ranges, pad = text_block(s, fname, sz, track, base)
    A = A.copy()
    h, w = A.shape
    if stagger is not None:
        tl, dly, dur = stagger
        yoff = np.zeros(w, np.float32)
        alph = np.zeros(w, np.float32)
        for k, (cx0, cx1) in enumerate(ranges):
            p = eo((tl - k * dly) / dur)
            c0, c1 = int(cx0 - 2), int(math.ceil(cx1 + 2))
            alph[max(c0, 0):c1] = np.maximum(alph[max(c0, 0):c1], p)
            yoff[max(c0, 0):c1] = (1 - p) * sz * 0.35
        # 逐列竖向偏移
        if yoff.max() > 0.5:
            A2 = np.zeros_like(A)
            R2 = np.zeros_like(RGB)
            shifts = np.round(yoff).astype(int)
            for sh in np.unique(shifts):
                cols = shifts == sh
                if sh == 0:
                    A2[:, cols] = A[:, cols]
                    R2[:, cols] = RGB[:, cols]
                elif sh < h:
                    A2[sh:, cols] = A[:h - sh, cols]
                    R2[sh:, cols] = RGB[:h - sh, cols]
            A, RGB = A2, R2
        A *= alph[None, :]
    if wipe is not None and wipe < 1.0:
        soft = 0.25 * w + 20
        A *= np.clip((wipe * (w + soft) - np.arange(w)) / soft, 0, 1).astype(np.float32)[None, :]
    if blur > 0.3:
        A = cv2.GaussianBlur(A, (0, 0), blur)
    if anchor == 'c':
        ox = x - w / 2
    elif anchor == 'l':
        ox = x - pad
    else:
        ox = x - w + pad
    oy = y - h / 2 - rise
    ox, oy = int(round(ox)), int(round(oy))
    x0, y0 = max(ox, 0), max(oy, 0)
    x1, y1 = min(ox + w, W), min(oy + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    sa = A[y0 - oy:y1 - oy, x0 - ox:x1 - ox] * a
    sr = RGB[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
    reg = img[y0:y1, x0:x1]
    if shadow > 0:
        sh = cv2.GaussianBlur(sa, (0, 0), max(2.0, sz * 0.06)) * shadow
        reg *= (1 - sh)[..., None]
    if glow > 0:
        gc = sr if glowcol is None else np.asarray(glowcol, np.float32)
        gl = cv2.GaussianBlur(sa, (0, 0), max(3.0, sz * 0.12))[..., None] * gc * glow
        reg += gl
    reg *= (1 - sa)[..., None]
    reg += sa[..., None] * sr


def blit_card(img, item):
    (_, x0, y0, x1, y1, r, a, tint, border, border_a, fill_a, blur, glowb) = item
    X0, Y0, X1, Y1 = int(max(x0, 0)), int(max(y0, 0)), int(min(x1, W)), int(min(y1, H))
    if X1 <= X0 or Y1 <= Y0:
        return
    m = np.zeros((Y1 - Y0, X1 - X0), np.uint8)
    pts = Frame.rrect_pts(None, x0 - X0, y0 - Y0, x1 - X0, y1 - Y0, r)
    cv2.fillPoly(m, [(pts * 16).astype(np.int32).reshape(-1, 1, 2)], 255, cv2.LINE_AA, 4)
    mf = m.astype(np.float32) / 255 * a
    reg = img[Y0:Y1, X0:X1]
    if blur > 0:
        bl = cv2.GaussianBlur(reg, (0, 0), blur)
        reg[:] = reg * (1 - mf[..., None]) + bl * mf[..., None]
    # 半透明暗底 + 竖向提亮渐变
    gy = np.linspace(1.0, 0.45, Y1 - Y0, dtype=np.float32)[:, None, None]
    reg *= (1 - 0.35 * mf)[..., None]
    reg += mf[..., None] * gy * fill_a * np.asarray(tint, np.float32)
    # 描边（上亮下暗）
    bm = np.zeros_like(m)
    cv2.polylines(bm, [(pts * 16).astype(np.int32).reshape(-1, 1, 2)], True, 255, 2, cv2.LINE_AA, 4)
    bmf = bm.astype(np.float32) / 255 * a * border_a
    bc = np.asarray(border if border is not None else (1, 1, 1), np.float32)
    grad = np.linspace(1.0, 0.25, Y1 - Y0, dtype=np.float32)[:, None, None]
    reg += bmf[..., None] * bc * grad


def blit_image(img, item):
    (_, rgb, alpha, cx, cy, a, scale) = item
    if scale != 1.0:
        h, w = alpha.shape
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        rgb = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
        alpha = cv2.resize(alpha, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    h, w = alpha.shape
    ox, oy = int(round(cx - w / 2)), int(round(cy - h / 2))
    x0, y0, x1, y1 = max(ox, 0), max(oy, 0), min(ox + w, W), min(oy + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    sa = alpha[y0 - oy:y1 - oy, x0 - ox:x1 - ox, None] * a
    reg = img[y0:y1, x0:x1]
    reg *= 1 - sa
    reg += sa * rgb[y0 - oy:y1 - oy, x0 - ox:x1 - ox]


# ---------------------------------------------------------------- 3D 相机
class Cam:
    def __init__(self, pos, target, fov=50.0, cx=W / 2, cy=H / 2, roll=0.0):
        self.pos = np.asarray(pos, np.float64)
        self.target = np.asarray(target, np.float64)
        f = self.target - self.pos
        f /= np.linalg.norm(f)
        up = np.array([0.0, 1.0, 0.0])
        r = np.cross(up, f)
        if np.linalg.norm(r) < 1e-6:
            r = np.array([1.0, 0, 0])
        r /= np.linalg.norm(r)
        u = np.cross(f, r)
        if roll:
            cr, sr = math.cos(roll), math.sin(roll)
            r, u = r * cr + u * sr, -r * sr + u * cr
        self.R = np.stack([r, u, f], 0)
        self.focal = (H / 2) / math.tan(math.radians(fov) / 2)
        self.cx, self.cy = cx, cy

    def project(self, P):
        """P: (N,3) 世界坐标（y 向上）→ (x, y, z_depth, scale)"""
        P = np.asarray(P, np.float64).reshape(-1, 3)
        q = (P - self.pos) @ self.R.T
        z = q[:, 2]
        zz = np.maximum(z, 1e-3)
        s = self.focal / zz
        x = self.cx + q[:, 0] * s
        y = self.cy - q[:, 1] * s
        return x, y, z, s


# ---------------------------------------------------------------- 后期
_VIG = None
_GRAIN = None


def vignette():
    global _VIG
    if _VIG is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.58)) ** 2)
        _VIG = (1 - 0.55 * np.clip(d - 0.35, 0, 1) ** 1.6).astype(np.float32)[..., None]
    return _VIG


def grain(fi):
    global _GRAIN
    if _GRAIN is None:
        r = np.random.default_rng(9)
        _GRAIN = [cv2.resize(r.standard_normal((H // 2, W // 2)).astype(np.float32), (W, H),
                             interpolation=cv2.INTER_LINEAR) for _ in range(6)]
    return _GRAIN[fi % 6]


def bloom(src, strength=1.0):
    s2 = cv2.resize(src, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    s4 = cv2.resize(s2, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    s8 = cv2.resize(s4, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
    s16 = cv2.resize(s8, (W // 16, H // 16), interpolation=cv2.INTER_AREA)
    g4 = cv2.GaussianBlur(s4, (0, 0), 2.5)
    g8 = cv2.GaussianBlur(s8, (0, 0), 3.0)
    g16 = cv2.GaussianBlur(s16, (0, 0), 3.5)
    acc = cv2.resize(g16, (W // 8, H // 8), interpolation=cv2.INTER_LINEAR) * 0.9 + g8 * 0.8
    acc = cv2.resize(acc, (W // 4, H // 4), interpolation=cv2.INTER_LINEAR) + g4 * 0.7
    acc = cv2.GaussianBlur(cv2.resize(acc, (W // 2, H // 2), interpolation=cv2.INTER_LINEAR), (0, 0), 1.5) + \
        cv2.GaussianBlur(s2, (0, 0), 3.0) * 0.4
    return cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * (0.55 * strength)


def tonemap(x):
    hi = x > 0.78
    if hi.any():
        x[hi] = 0.78 + 0.22 * (1 - np.exp(-(x[hi] - 0.78) / 0.22))
    return x


def compose(fr, bg):
    img = bg + fr.L
    img += bloom(fr.L + fr.B, fr.bloom)
    tonemap(img)
    for item in fr.ov:
        k = item[0]
        if k == 'text':
            blit_text(img, None, item)
        elif k == 'card':
            blit_card(img, item)
        elif k == 'image':
            blit_image(img, item)
        elif k == 'fn':
            item[1](img)
        elif k == 'draw':
            cv = Frame.__new__(Frame)
            cv.L = img
            cv.B = img
            item[1](cv)
    # 镜头：缩放 / 平移 / 旋转
    if abs(fr.zoom - 1) > 1e-4 or abs(fr.cam[0]) > 0.05 or abs(fr.cam[1]) > 0.05 or abs(fr.rot) > 1e-4:
        M = cv2.getRotationMatrix2D((W / 2, H / 2), math.degrees(fr.rot), fr.zoom)
        M[:, 2] += fr.cam
        img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if fr.ca > 0.2:
        k = fr.ca
        Mr = cv2.getRotationMatrix2D((W / 2, H / 2), 0, 1 + k / W)
        Mb = cv2.getRotationMatrix2D((W / 2, H / 2), 0, 1 - k / W)
        img[..., 0] = cv2.warpAffine(img[..., 0], Mr, (W, H), borderMode=cv2.BORDER_REFLECT)
        img[..., 2] = cv2.warpAffine(img[..., 2], Mb, (W, H), borderMode=cv2.BORDER_REFLECT)
    if fr.flash > 0.003:
        img += fr.flash * np.array([1.0, 0.97, 0.92], np.float32)
    return img
