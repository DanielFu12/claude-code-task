"""加色光 + 辉光的小型动态图形引擎（numpy + OpenCV + Pillow）。

所有画面都是时间 t 的纯函数，每帧在几层 float32 缓冲上叠加，最后统一做辉光、色调压缩、暗角和颗粒：
    L  清晰加色层（不发光）       E  清晰加色层（参与辉光）
    B  只发光层                    U/UL  OpenCV 抗锯齿线条（分别并入 E / L）
    over  延后贴上的不透明文字（旁白、卡片标题等，保证在亮画面上也清楚）
"""
import math, os
from functools import lru_cache
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, '..', 'fonts')


# ---------------------------------------------------------------- 缓动
def cl(x, a=0.0, b=1.0):
    if isinstance(x, np.ndarray): return np.clip(x, a, b)
    return a if x < a else b if x > b else x
def eo(x):
    x = cl(x); return 1 - (1 - x) ** 3
def eo5(x):
    x = cl(x); return 1 - (1 - x) ** 5
def ei(x):
    x = cl(x); return x ** 3
def eio(x):
    x = cl(x); return x * x * (3 - 2 * x)
def eio3(x):
    x = cl(x)
    if isinstance(x, np.ndarray): return np.where(x < 0.5, 4 * x ** 3, 1 - (-2 * x + 2) ** 3 / 2)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
def eback(x, s=1.7):
    x = cl(x); x -= 1; return x * x * ((s + 1) * x + s) + 1
def env(t, a, b, fi=0.35, fo=0.35):
    """a..b 之间为 1，前后各有淡入 fi / 淡出 fo"""
    if t < a or t > b + fo: return 0.0
    k = eo((t - a) / max(fi, 1e-3))
    if t > b: k *= 1 - eio((t - b) / max(fo, 1e-3))
    return k
def lerp(a, b, x):
    return a + (b - a) * x
def lerpc(c1, c2, x):
    return tuple(lerp(p, q, x) for p, q in zip(c1, c2))
def mixc(c1, c2, x):
    return np.asarray(c1, np.float32) * (1 - x) + np.asarray(c2, np.float32) * x
def keys(t, kf, ease=eio):
    if t <= kf[0][0]: return kf[0][1]
    for (t0, v0), (t1, v1) in zip(kf, kf[1:]):
        if t <= t1:
            x = ease((t - t0) / max(t1 - t0, 1e-6))
            if isinstance(v0, tuple): return lerpc(v0, v1, x)
            return lerp(v0, v1, x)
    return kf[-1][1]
def C(r, g, b):
    return (r / 255.0, g / 255.0, b / 255.0)
def scale(c, k):
    return tuple(v * k for v in c)


# 调色板：A 股习惯「红涨绿跌」；金色来自品牌规范（brand/brand.py 的 GOLD_STOPS）
UP = C(255, 74, 82)          # 上涨红
UP2 = C(255, 140, 110)
DOWN = C(30, 220, 150)       # 下跌绿
DOWN2 = C(120, 255, 200)
GOLD = C(255, 212, 120)      # 品牌金 #FFD478
GOLDL = C(255, 243, 200)     # 品牌金高光 #FFF3C8
GOLDD = C(226, 160, 60)      # 品牌金暗部 #E2A03C
SUBG = C(214, 178, 112)      # 品牌小字金 #D6B270
BLUE = C(110, 175, 255)      # 品牌 logo 光晕蓝
CYAN = C(80, 210, 255)
INK = C(238, 234, 226)
WHITE = (1.0, 1.0, 1.0)
GREY = C(140, 146, 160)
DIM = C(80, 86, 100)
VIOLET = C(160, 120, 255)


# ---------------------------------------------------------------- 字形
@lru_cache(64)
def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name + '.ttf'), size)


LATIN_ONLY = ('mono', 'mono_med', 'corm', 'corm_sb', 'inter_light', 'inter_sb')


@lru_cache(30000)
def glyph(ch, name, size):
    if name in LATIN_ONLY and ord(ch) > 0x2000 and ch not in '·—–':
        name = 'sans_med'                      # 西文字体没有中文字形，回退到思源黑体
    f = font(name, size)
    asc, desc = f.getmetrics()
    adv = f.getlength(ch)
    pad = int(size * 0.15) + 2
    w = int(math.ceil(adv)) + 2 * pad + int(size * 0.2)
    h = asc + desc + 2 * pad
    im = Image.new('L', (w, h), 0)
    ImageDraw.Draw(im).text((pad, pad + asc), ch, font=f, fill=255, anchor='ls')
    m = np.asarray(im, np.float32) / 255.0
    return m, adv, pad, pad + asc


def strip(s):
    return s.replace('【', '').replace('】', '')


def text_width(s, name, size, track=0.0):
    s = strip(s)
    return sum(glyph(ch, name, size)[1] for ch in s) + track * size * max(len(s) - 1, 0)


def text_mask(s, name, size, track=0.0):
    """整行文字的 alpha 遮罩（用于粒子取样）"""
    tw = int(text_width(s, name, size, track)) + size
    h = int(size * 1.6)
    m = np.zeros((h, tw), np.float32)
    x = size * 0.5
    for ch in strip(s):
        g, adv, pad, bl = glyph(ch, name, size)
        y0 = int(h * 0.5 + size * 0.36 - bl)
        x0 = int(round(x - pad))
        gh, gw = g.shape
        ys, xs = max(0, y0), max(0, x0)
        ye, xe = min(h, y0 + gh), min(tw, x0 + gw)
        if ye > ys and xe > xs:
            m[ys:ye, xs:xe] = np.maximum(m[ys:ye, xs:xe], g[ys - y0:ye - y0, xs - x0:xe - x0])
        x += adv + track * size
    return m


class Frame:
    def __init__(self, t):
        self.t = t
        self.L = np.zeros((H, W, 3), np.float32)
        self.E = np.zeros((H, W, 3), np.float32)
        self.B = np.zeros((H, W, 3), np.float32)
        self.U = np.zeros((H, W, 3), np.uint8)
        self.UL = np.zeros((H, W, 3), np.uint8)
        self.over = []
        self.ca = 0.0
        self.flash = 0.0
        self.flash_col = (1.0, 1.0, 1.0)
        self.shake = (0, 0)
        self.dark = 0.0          # 全局压暗（转场用）
        self.bloom = 1.0

    # ------------------------------------------------ 线条
    def _c(self, col, a):
        return tuple(float(cl(c * a) * 255) for c in col)

    def _U(self, buf):
        return self.U if buf == 'E' else self.UL

    def line(self, p0, p1, col, a=1.0, th=2, buf='E'):
        if a <= 0.003: return
        cv2.line(self._U(buf), (int(p0[0] * 16), int(p0[1] * 16)), (int(p1[0] * 16), int(p1[1] * 16)),
                 self._c(col, a), th, cv2.LINE_AA, 4)

    def poly(self, pts, col, a=1.0, th=2, closed=False, buf='E'):
        if a <= 0.003 or len(pts) < 2: return
        p = (np.asarray(pts, np.float64) * 16).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(self._U(buf), [p], closed, self._c(col, a), th, cv2.LINE_AA, 4)

    def dashed(self, p0, p1, col, a=1.0, th=1, dash=10, gap=8, buf='E', phase=0.0):
        p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
        L = np.linalg.norm(p1 - p0)
        if L < 1: return
        d = (p1 - p0) / L
        s = -phase % (dash + gap)
        s -= dash + gap
        while s < L:
            a0, a1 = max(s, 0), min(s + dash, L)
            if a1 > a0: self.line(p0 + d * a0, p0 + d * a1, col, a, th, buf)
            s += dash + gap

    def fillpoly(self, pts, col, a=1.0, buf='L'):
        if a <= 0.003: return
        p = (np.asarray(pts, np.float64) * 16).astype(np.int32).reshape(-1, 1, 2)
        x0, y0 = np.clip(p[:, 0, :].min(0) // 16 - 2, 0, None)
        x1, y1 = p[:, 0, 0].max() // 16 + 3, p[:, 0, 1].max() // 16 + 3
        x1, y1 = min(x1, W), min(y1, H)
        if x1 <= x0 or y1 <= y0: return
        m = np.zeros((y1 - y0, x1 - x0), np.uint8)
        q = p.copy(); q[:, 0, 0] -= x0 * 16; q[:, 0, 1] -= y0 * 16
        cv2.fillPoly(m, [q], 255, cv2.LINE_AA, 4)
        getattr(self, buf)[y0:y1, x0:x1] += (m.astype(np.float32) / 255 * a)[..., None] * np.array(col, np.float32)

    def vgrad_fill(self, pts, col, a0, a1, ytop, ybot, buf='L', xfade=0):
        """多边形填充，透明度从 ytop 处 a0 渐变到 ybot 处 a1（面积图用）"""
        p = (np.asarray(pts, np.float64) * 16).astype(np.int32).reshape(-1, 1, 2)
        x0, y0 = np.clip(p[:, 0, :].min(0) // 16 - 2, 0, None)
        x1, y1 = min(p[:, 0, 0].max() // 16 + 3, W), min(p[:, 0, 1].max() // 16 + 3, H)
        if x1 <= x0 or y1 <= y0: return
        m = np.zeros((y1 - y0, x1 - x0), np.uint8)
        q = p.copy(); q[:, 0, 0] -= x0 * 16; q[:, 0, 1] -= y0 * 16
        cv2.fillPoly(m, [q], 255, cv2.LINE_AA, 4)
        ys = np.arange(y0, y1, dtype=np.float32)
        g = np.clip((ys - ytop) / max(ybot - ytop, 1), 0, 1)
        g = (a0 + (a1 - a0) * g)[:, None]
        if xfade > 0:
            xs_ = np.arange(x0, x1, dtype=np.float32)
            g = g * np.clip((p[:, 0, 0].max() / 16 - xs_) / xfade, 0, 1)[None, :]
        getattr(self, buf)[y0:y1, x0:x1] += (m.astype(np.float32) / 255 * g)[..., None] * np.array(col, np.float32)

    def circle(self, c, r, col, a=1.0, th=2, buf='E'):
        if a <= 0.003 or r <= 0: return
        cv2.circle(self._U(buf), (int(c[0] * 16), int(c[1] * 16)), int(r * 16), self._c(col, a), th, cv2.LINE_AA, 4)

    def disc(self, c, r, col, a=1.0, buf='E'):
        if a <= 0.003 or r <= 0: return
        R = int(r + 2)
        x0, y0 = int(c[0]) - R, int(c[1]) - R
        X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + 2 * R + 1, W), min(y0 + 2 * R + 1, H)
        if X1 <= X0 or Y1 <= Y0: return
        yy, xx = np.mgrid[Y0:Y1, X0:X1].astype(np.float32)
        d = np.sqrt((xx - c[0]) ** 2 + (yy - c[1]) ** 2)
        m = np.clip(r + 0.5 - d, 0, 1) * a
        getattr(self, buf)[Y0:Y1, X0:X1] += m[..., None] * np.array(col, np.float32)

    def arc(self, c, r, a0, a1, col, a=1.0, th=2, n=None, buf='E'):
        n = n or max(8, int(abs(a1 - a0) * r / 6))
        ts = np.linspace(a0, a1, n)
        self.poly(np.stack([c[0] + r * np.cos(ts), c[1] + r * np.sin(ts)], 1), col, a, th, buf=buf)

    def rrect_pts(self, x0, y0, x1, y1, r):
        pts = []
        for cx, cy, s in ((x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, math.pi / 2),
                          (x0 + r, y0 + r, math.pi)):
            for k in range(9):
                ang = s + k / 8 * math.pi / 2
                pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        return pts

    def rrect(self, x0, y0, x1, y1, r, col, a=1.0, th=1, buf='E'):
        self.poly(self.rrect_pts(x0, y0, x1, y1, r), col, a, th, closed=True, buf=buf)

    def rrect_fill(self, x0, y0, x1, y1, r, col, a=0.1, buf='L'):
        self.fillpoly(self.rrect_pts(x0, y0, x1, y1, r), col, a, buf)

    def panel(self, x0, y0, x1, y1, a, col=GOLD, r=14):
        """毛玻璃风格卡片：压暗背景 + 细边框"""
        if a <= 0.003: return
        self.darken_rect(x0, y0, x1, y1, 0.55 * a, r)
        self.rrect(x0, y0, x1, y1, r, scale(col, 0.55), a, 1, buf='L')

    def darken_rect(self, x0, y0, x1, y1, k, r=0):
        self.over.append(('dark', (int(x0), int(y0), int(x1), int(y1), k, r)))

    def glow(self, c, r, col, a=1.0, buf='B'):
        if a <= 0.003 or r <= 0.5: return
        R = int(r * 3)
        x0, y0, x1, y1 = int(c[0]) - R, int(c[1]) - R, int(c[0]) + R + 1, int(c[1]) + R + 1
        X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
        if X1 <= X0 or Y1 <= Y0: return
        yy, xx = np.mgrid[Y0:Y1, X0:X1].astype(np.float32)
        g = np.exp(-((xx - c[0]) ** 2 + (yy - c[1]) ** 2) / (2 * r * r)) * a
        getattr(self, buf)[Y0:Y1, X0:X1] += g[..., None] * np.array(col, np.float32)

    # ------------------------------------------------ 粒子（双线性亚像素）
    def splat(self, xs, ys, cols, a, buf='E'):
        xs = np.asarray(xs, np.float64); ys = np.asarray(ys, np.float64)
        a = np.broadcast_to(np.asarray(a, np.float32), xs.shape)
        cols = np.asarray(cols, np.float32)
        if cols.ndim == 1: cols = np.broadcast_to(cols, xs.shape + (3,))
        ok = (xs >= 0) & (xs < W - 1) & (ys >= 0) & (ys < H - 1) & (a > 0.002)
        if not ok.any(): return
        xs, ys, a, cols = xs[ok], ys[ok], a[ok], cols[ok]
        x0 = np.floor(xs).astype(np.int64); y0 = np.floor(ys).astype(np.int64)
        fx = (xs - x0).astype(np.float32); fy = (ys - y0).astype(np.float32)
        b = getattr(self, buf).reshape(-1, 3)
        v = cols * a[:, None]
        for dx, dy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            np.add.at(b, (y0 + dy) * W + x0 + dx, v * w[:, None])

    def dots(self, xs, ys, cols, a, rad=1.0, buf='E'):
        """较大的粒子：中心 + 一圈"""
        xs = np.asarray(xs, np.float64); ys = np.asarray(ys, np.float64)
        a = np.asarray(a, np.float32)
        self.splat(xs, ys, cols, a, buf)
        if rad > 0.4:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                self.splat(xs + dx * rad, ys + dy * rad, cols, a * 0.45, buf)
            for dx, dy in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
                self.splat(xs + dx * rad * 0.8, ys + dy * rad * 0.8, cols, a * 0.18, buf)

    # ------------------------------------------------ 文字
    def text(self, s, x, y, size, fnt='sans_med', col=INK, a=1.0, anchor='m', track=0.0,
             mode='L', glow=0.0, t0=None, stag=0.03, dur=0.45, rise=14, out=None, hl=GOLD,
             grad=None, wipe=None, blur_in=False):
        """单行文字；y 为视觉中线。【】包住的字用 hl 颜色高亮。
        mode: L 加色清晰 / E 加色并发光 / O 不透明覆盖（最后贴）"""
        if a <= 0.003 or not s: return 0
        hot = []
        on = False
        chars = []
        for ch in s:
            if ch == '【': on = True; continue
            if ch == '】': on = False; continue
            chars.append(ch); hot.append(on)
        tw = text_width(s, fnt, size, track)
        xs = x - tw / 2 if anchor == 'm' else (x if anchor == 'l' else x - tw)
        base = y + size * 0.36
        cx = xs
        for i, ch in enumerate(chars):
            m, adv, pad, bl = glyph(ch, fnt, size)
            ai = a; dy = 0.0
            if t0 is not None:
                p = (self.t - t0 - i * stag) / dur
                ai *= eo(p); dy = (1 - eo(p)) * rise
            if out is not None:
                p = (self.t - out[0] - i * stag * 0.5) / out[1]
                ai *= 1 - eio(p); dy -= eio(p) * rise * 0.6
            if wipe is not None:
                u = (cx + adv / 2 - xs) / max(tw, 1)
                ai *= cl((wipe * 1.3 - u) / 0.3)
            if ai > 0.003 and ch != ' ':
                if grad is not None:
                    colc = grad
                    colc = grad_color(grad, (cx + adv / 2 - xs) / max(tw, 1))
                else:
                    colc = hl if hot[i] else col
                self._blit(m, cx - pad, base - bl + dy, colc, ai, mode, glow)
            cx += adv + track * size
        return tw

    def _blit(self, m, x, y, col, a, mode, glow):
        x0, y0 = int(round(x)), int(round(y))
        h, w = m.shape
        X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
        if X1 <= X0 or Y1 <= Y0: return
        mm = m[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
        colv = np.array(col, np.float32)
        if mode == 'O':
            self.over.append(('txt', (mm, X0, Y0, colv, a)))
        else:
            getattr(self, mode)[Y0:Y1, X0:X1] += (mm * a)[..., None] * colv
        if glow > 0:
            self.B[Y0:Y1, X0:X1] += (mm * a * glow)[..., None] * colv

    def rgba(self, rgb, al, x0, y0, a=1.0, mode='O'):
        """贴 RGBA 图（rgb float 0..1, al 0..1）"""
        if a <= 0.003: return
        x0, y0 = int(round(x0)), int(round(y0))
        h, w = al.shape
        X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
        if X1 <= X0 or Y1 <= Y0: return
        self.over.append(('rgba', (rgb[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0], al[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] * a,
                                   X0, Y0)))


def grad_color(grad, u):
    u = cl(u)
    k = len(grad) - 1
    i = min(int(u * k), k - 1)
    return lerpc(grad[i], grad[i + 1], u * k - i)


# ---------------------------------------------------------------- 背景
def fbm(w, h, seed, octaves=6, base=3):
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        n = base * 2 ** o
        r = rng.random((max(2, n * h // w), n)).astype(np.float32)
        acc += cv2.resize(r, (w, h), interpolation=cv2.INTER_CUBIC) * amp
        tot += amp; amp *= 0.55
    acc /= tot
    return (acc - acc.min()) / (acc.max() - acc.min())


_YY, _XX = np.mgrid[0:H, 0:W].astype(np.float32)
VIGNETTE = (1 - 0.55 * np.clip(((_XX - W / 2) / (W * 0.62)) ** 2 + ((_YY - H / 2) / (H * 0.70)) ** 2, 0, 1.4) ** 1.3)[..., None]
VIGNETTE = np.clip(VIGNETTE, 0.25, 1).astype(np.float32)
_rng = np.random.default_rng(7)
# 静态抖动（约 ±1/255）：消除暗部渐变的色带；不逐帧变化，编码器几乎不为它花码率
GRAIN = [(_rng.random((H, W)).astype(np.float32) - 0.5)[..., None] * (1.6 / 255)]
# 底部旁白区的柔和压暗带
BAND = np.ones((H, 1, 1), np.float32)
_y = np.arange(H, dtype=np.float32)
BAND[:, 0, 0] = 1 - 0.42 * np.clip((_y - 820) / 160, 0, 1) ** 1.5


def finish(fr, bg, frame_idx=0, band=0.0):
    E = fr.E
    E += fr.U.astype(np.float32) * (1 / 255.0)
    L = fr.L + fr.UL.astype(np.float32) * (1 / 255.0)
    src = E + fr.B
    s4 = cv2.resize(src, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    b1 = cv2.GaussianBlur(s4, (0, 0), 2.6)
    s16 = cv2.resize(s4, (W // 16, H // 16), interpolation=cv2.INTER_AREA)
    b2 = cv2.GaussianBlur(s16, (0, 0), 3.2)
    bl = cv2.resize(b1 * 0.85 + cv2.resize(b2, (W // 4, H // 4), interpolation=cv2.INTER_LINEAR) * 1.2,
                    (W, H), interpolation=cv2.INTER_LINEAR)
    out = bg + L + E + bl * fr.bloom
    if fr.flash > 0:
        out += np.array(fr.flash_col, np.float32) * fr.flash
    out = np.where(out > 0.82, 0.82 + (1 - np.exp(-(out - 0.82) * 3.2)) * 0.18 / 0.98, out)
    out *= VIGNETTE
    if band > 0:
        out *= 1 - (1 - BAND) * band
    if fr.dark > 0:
        out *= 1 - fr.dark
    for kind, d in fr.over:
        if kind == 'dark':
            x0, y0, x1, y1, k, r = d
            x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
            if x1 > x0 and y1 > y0:
                m = np.zeros((y1 - y0, x1 - x0), np.float32)
                cv2.rectangle(m, (0, 0), (x1 - x0 - 1, y1 - y0 - 1), 1.0, -1)
                m = cv2.GaussianBlur(m, (0, 0), 6)
                out[y0:y1, x0:x1] *= (1 - k * m)[..., None]
        elif kind == 'txt':
            mm, X0, Y0, colv, a = d
            h, w = mm.shape
            reg = out[Y0:Y0 + h, X0:X0 + w]
            m3 = (mm * a)[..., None]
            reg *= (1 - m3 * 0.92)
            reg += m3 * colv
        elif kind == 'rgba':
            rgb, al, X0, Y0 = d
            h, w = al.shape
            reg = out[Y0:Y0 + h, X0:X0 + w]
            m3 = al[..., None]
            reg *= 1 - m3
            reg += m3 * rgb
    if fr.ca >= 0.5:
        d = max(1, int(round(fr.ca)))
        out[:, d:, 0] = out[:, :-d, 0].copy()
        out[:, :-d, 2] = out[:, d:, 2].copy()
    if fr.shake != (0, 0):
        out = np.roll(out, fr.shake, axis=(0, 1))
    out += GRAIN[frame_idx % len(GRAIN)]
    return out
