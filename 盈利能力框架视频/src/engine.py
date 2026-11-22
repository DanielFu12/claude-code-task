"""加色光动态图形引擎（numpy + OpenCV + Pillow）。

缓冲区：
  L  清晰加色（不参与辉光）
  E  加色 + 辉光
  B  只有辉光
  U  OpenCV 抗锯齿线条（合成时并入 E）
  over  延迟的 alpha 覆盖（实心字、卡片底色）
全局 fr.k 是当前绘制的整体透明度（用于场景交叉淡化）。
"""
import math, os
from functools import lru_cache
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, '..', 'fonts')


# ---------------------------------------------------------------- easing
def cl(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x
def eo(x):
    x = cl(x); return 1 - (1 - x) ** 3
def eo5(x):
    x = cl(x); return 1 - (1 - x) ** 5
def ei(x):
    x = cl(x); return x ** 3
def eio(x):
    x = cl(x); return x * x * (3 - 2 * x)
def eback(x, s=1.7):
    x = cl(x); x -= 1; return x * x * ((s + 1) * x + s) + 1
def eel(x):
    """弹性回弹"""
    x = cl(x)
    if x in (0, 1): return x
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * 2 * math.pi / 3) + 1
def lerp(a, b, x):
    return a + (b - a) * x
def lerpc(c1, c2, x):
    return tuple(lerp(p, q, x) for p, q in zip(c1, c2))
def env(t, a, b, fi=0.35, fo=0.35):
    if t < a or t > b: return 0.0
    return eo((t - a) / max(fi, 1e-3)) * (eo((b - t) / max(fo, 1e-3)) if fo > 0 else 1.0)
def ramp(t, a, d=0.4, f=eo):
    return f((t - a) / max(d, 1e-4))
def pulse(t, t0, d=0.35):
    """t0 时刻起的一次衰减脉冲"""
    if t < t0: return 0.0
    return math.exp(-(t - t0) / d)
def keys(t, kf):
    if t <= kf[0][0]: return kf[0][1]
    for (t0, v0), (t1, v1) in zip(kf, kf[1:]):
        if t <= t1:
            x = eio((t - t0) / max(t1 - t0, 1e-6))
            if isinstance(v0, tuple): return lerpc(v0, v1, x)
            return lerp(v0, v1, x)
    return kf[-1][1]


def C(r, g, b):
    return (r / 255.0, g / 255.0, b / 255.0)


GOLD = C(255, 204, 110); GOLD2 = C(255, 236, 185); GOLDD = C(214, 146, 50)
CYAN = C(80, 210, 255); ICE = C(170, 230, 255); VIOLET = C(160, 120, 255); MAGENTA = C(255, 80, 190)
RED = C(255, 72, 88); TEAL = C(60, 235, 180); ORANGE = C(255, 145, 60); GREEN = C(110, 240, 140)
WHITE = (1.0, 1.0, 1.0); BLUE = C(80, 140, 255); GREY = C(150, 162, 190); DIM = C(90, 100, 125)


# ---------------------------------------------------------------- glyphs
@lru_cache(64)
def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name + '.ttf'), size)


@lru_cache(30000)
def glyph(ch, name, size):
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


def text_width(s, name, size, track=0.0):
    return sum(glyph(ch, name, size)[1] for ch in s) + track * size * max(len(s) - 1, 0)


@lru_cache(512)
def text_mask(s, name, size, track=0.0):
    """整行文字的 alpha 掩膜（用于粒子文字、描边等）"""
    tw = int(text_width(s, name, size, track)) + 40
    f = font(name, size)
    asc, desc = f.getmetrics()
    h = asc + desc + 40
    im = Image.new('L', (tw, h), 0)
    d = ImageDraw.Draw(im)
    x = 20
    for ch in s:
        d.text((x, 20 + asc), ch, font=f, fill=255, anchor='ls')
        x += f.getlength(ch) + track * size
    return np.asarray(im, np.float32) / 255.0, 20 + asc * 0.62


def grad_color(grad, u):
    u = cl(u)
    k = len(grad) - 1
    i = min(int(u * k), k - 1)
    return lerpc(grad[i], grad[i + 1], u * k - i)


# ---------------------------------------------------------------- frame
class Frame:
    def __init__(self, t):
        self.t = t
        self.L = np.zeros((H, W, 3), np.float32)
        self.E = np.zeros((H, W, 3), np.float32)
        self.B = np.zeros((H, W, 3), np.float32)
        self.U = np.zeros((H, W, 3), np.uint8)
        self.over = []
        self.post_over = []
        self.k = 1.0
        self.ca = 0.0
        self.flash = 0.0
        self.zoom = 1.0
        self.cam = (0.0, 0.0)
        self.rot = 0.0
        self.shake = (0.0, 0.0)
        self.bloom = 1.0

    # ------------------------------------------------ strokes
    def _c(self, col, a):
        a *= self.k
        return tuple(float(cl(c * a) * 255) for c in col)

    def line(self, p0, p1, col, a=1.0, th=2):
        if a * self.k <= 0.003: return
        cv2.line(self.U, (int(p0[0] * 16), int(p0[1] * 16)), (int(p1[0] * 16), int(p1[1] * 16)),
                 self._c(col, a), max(1, int(th)), cv2.LINE_AA, 4)

    def poly(self, pts, col, a=1.0, th=2, closed=False):
        if a * self.k <= 0.003 or len(pts) < 2: return
        p = (np.asarray(pts, np.float64) * 16).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(self.U, [p], closed, self._c(col, a), max(1, int(th)), cv2.LINE_AA, 4)

    def fillpoly(self, pts, col, a=1.0, buf='L'):
        a *= self.k
        if a <= 0.003: return
        p = (np.asarray(pts, np.float64) * 16).astype(np.int32).reshape(-1, 1, 2)
        x0, y0 = np.clip(p[:, 0, :].min(0) // 16 - 2, 0, None)
        x1, y1 = p[:, 0, 0].max() // 16 + 3, p[:, 0, 1].max() // 16 + 3
        x1, y1 = min(x1, W), min(y1, H)
        if x1 <= x0 or y1 <= y0: return
        m = np.zeros((y1 - y0, x1 - x0), np.uint8)
        q = p.copy(); q[:, 0, 0] -= x0 * 16; q[:, 0, 1] -= y0 * 16
        cv2.fillPoly(m, [q], 255, cv2.LINE_AA, 4)
        mm = m.astype(np.float32) / 255 * a
        if buf == 'O':
            self.over.append((mm, x0, y0, np.array(col, np.float32), 1.0))
        else:
            getattr(self, buf)[y0:y1, x0:x1] += mm[..., None] * np.array(col, np.float32)

    def rect(self, x0, y0, x1, y1, col, a=1.0, buf='L'):
        a *= self.k
        X0, Y0, X1, Y1 = max(int(x0), 0), max(int(y0), 0), min(int(x1), W), min(int(y1), H)
        if X1 <= X0 or Y1 <= Y0 or a <= 0.003: return
        if buf == 'O':
            self.over.append((np.full((Y1 - Y0, X1 - X0), a, np.float32), X0, Y0, np.array(col, np.float32), 1.0))
        else:
            getattr(self, buf)[Y0:Y1, X0:X1] += np.array(col, np.float32) * a

    def vgrad_rect(self, x0, y0, x1, y1, col, a_top, a_bot, buf='L'):
        X0, Y0, X1, Y1 = max(int(x0), 0), max(int(y0), 0), min(int(x1), W), min(int(y1), H)
        if X1 <= X0 or Y1 <= Y0: return
        g = np.linspace(a_top, a_bot, int(y1) - int(y0))[Y0 - int(y0):Y1 - int(y0)] * self.k
        getattr(self, buf)[Y0:Y1, X0:X1] += g[:, None, None] * np.array(col, np.float32)

    def circle(self, c, r, col, a=1.0, th=2):
        if a * self.k <= 0.003 or r <= 0: return
        cv2.circle(self.U, (int(c[0] * 16), int(c[1] * 16)), int(r * 16), self._c(col, a), int(th), cv2.LINE_AA, 4)

    def disc(self, c, r, col, a=1.0, buf='E'):
        if r <= 0: return
        n = max(12, int(r * 0.8))
        ts = np.linspace(0, 2 * np.pi, n, endpoint=False)
        self.fillpoly(np.stack([c[0] + r * np.cos(ts), c[1] + r * np.sin(ts)], 1), col, a, buf)

    def arc(self, c, r, a0, a1, col, a=1.0, th=2, n=None):
        n = n or max(8, int(abs(a1 - a0) * r / 6))
        ts = np.linspace(a0, a1, n)
        self.poly(np.stack([c[0] + r * np.cos(ts), c[1] + r * np.sin(ts)], 1), col, a, th)

    def rrect_pts(self, x0, y0, x1, y1, r):
        pts = []
        r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
        for cx, cy, s in ((x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, math.pi / 2), (x0 + r, y0 + r, math.pi)):
            for k in range(7):
                ang = s + k / 6 * math.pi / 2
                pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        return pts

    def rrect(self, x0, y0, x1, y1, r, col, a=1.0, th=2):
        self.poly(self.rrect_pts(x0, y0, x1, y1, r), col, a, th, closed=True)

    def rrect_fill(self, x0, y0, x1, y1, r, col, a=0.1, buf='L'):
        self.fillpoly(self.rrect_pts(x0, y0, x1, y1, r), col, a, buf)

    def panel(self, x0, y0, x1, y1, col, a=1.0, r=14, fill=0.10, dark=0.55, th=2, glow=0.5):
        """玻璃卡片：暗色底 + 主题色淡填充 + 描边 + 顶部高光"""
        if a * self.k <= 0.003: return
        self.rrect_fill(x0, y0, x1, y1, r, (0.0, 0.0, 0.0), dark * a, 'O')
        self.rrect_fill(x0, y0, x1, y1, r, col, fill * a, 'L')
        self.rrect(x0, y0, x1, y1, r, col, a * 0.9, th)
        if glow > 0:
            self.line((x0 + r, y0), (x1 - r, y0), col, a * glow, th + 1)

    def glow(self, c, r, col, a=1.0, buf='B'):
        a *= self.k
        if a <= 0.003 or r <= 0.5: return
        R = int(r * 3)
        x0, y0 = int(c[0]) - R, int(c[1]) - R
        X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + 2 * R + 1, W), min(y0 + 2 * R + 1, H)
        if X1 <= X0 or Y1 <= Y0: return
        g = _gauss(R, round(r, 1))[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] * a
        getattr(self, buf)[Y0:Y1, X0:X1] += g[..., None] * np.array(col, np.float32)

    def splat(self, xs, ys, cols, a, buf='E'):
        xs = np.asarray(xs, np.float64); ys = np.asarray(ys, np.float64)
        xi = np.round(xs).astype(np.int64); yi = np.round(ys).astype(np.int64)
        ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
        if not ok.any(): return
        a = np.broadcast_to(np.asarray(a, np.float32), xs.shape)[ok] * self.k
        cols = np.asarray(cols, np.float32)
        cols = cols[ok] if cols.ndim == 2 else np.broadcast_to(cols, (int(ok.sum()), 3))
        idx = yi[ok] * W + xi[ok]
        b = getattr(self, buf).reshape(-1, 3)
        np.add.at(b, idx, cols * a[:, None])

    def dots(self, xs, ys, cols, a, rad=1, buf='E'):
        xs = np.asarray(xs); ys = np.asarray(ys); a = np.asarray(a, np.float32)
        for dx, dy, w in ((0, 0, 1.0), (1, 0, .45), (-1, 0, .45), (0, 1, .45), (0, -1, .45),
                          (1, 1, .18), (-1, -1, .18), (1, -1, .18), (-1, 1, .18)):
            self.splat(xs + dx * rad, ys + dy * rad, cols, a * w, buf)

    def arrow(self, p0, p1, col, a=1.0, th=3, head=16):
        self.line(p0, p1, col, a, th)
        ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
        for s in (-1, 1):
            q = (p1[0] - head * math.cos(ang + s * 0.45), p1[1] - head * math.sin(ang + s * 0.45))
            self.line(p1, q, col, a, th)

    # ------------------------------------------------ text
    def text(self, s, x, y, size, fnt='sans_med', col=WHITE, a=1.0, anchor='m', track=0.0,
             mode='L', glow=0.0, grad=None, t0=None, stag=0.035, dur=0.45, rise=18, out=None,
             chars_alpha=None, scale=1.0, shadow=0.0):
        """单行文字。anchor: m 居中 / l 左 / r 右；y 为视觉中心。
        mode: L 加色清晰 / E 加色+辉光 / O 实心覆盖"""
        a *= self.k
        if a <= 0.003 or not s: return 0
        size = int(round(size * scale))
        if size < 2: return 0
        tw = text_width(s, fnt, size, track)
        xs = x - tw / 2 if anchor == 'm' else (x if anchor == 'l' else x - tw)
        base = y + size * 0.36
        cx = xs
        for i, ch in enumerate(s):
            m, adv, pad, bl = glyph(ch, fnt, size)
            ai = a
            dy = 0.0
            if t0 is not None:
                p = (self.t - t0 - i * stag) / dur
                ai *= eo(p)
                dy = (1 - eo(p)) * rise
            if out is not None:
                p = (self.t - out[0] - i * stag * 0.5) / out[1]
                ai *= 1 - eio(p)
                dy -= eio(p) * rise
            if chars_alpha is not None:
                ai *= chars_alpha[i] if i < len(chars_alpha) else 1
            if ai > 0.003 and ch != ' ':
                colc = grad_color(grad, (cx + adv / 2 - xs) / max(tw, 1)) if grad is not None else col
                if shadow > 0:
                    self.over.append((cv2.GaussianBlur(m, (0, 0), size * 0.08) * 0.85, int(round(cx - pad + 2)),
                                      int(round(base - bl + dy + 3)), np.zeros(3, np.float32), ai * shadow))
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
            self.over.append((mm, X0, Y0, colv, a))
        elif mode == 'P':
            self.post_over.append((mm, X0, Y0, colv, a))
        else:
            getattr(self, mode)[Y0:Y1, X0:X1] += (mm * a)[..., None] * colv
        if glow > 0:
            self.B[Y0:Y1, X0:X1] += (mm * a * glow)[..., None] * colv

    def mask(self, m, x, y, col, a=1.0, buf='E'):
        """把任意 alpha 掩膜按左上角 (x, y) 加到缓冲区"""
        a *= self.k
        if a <= 0.003: return
        self._blit(m, x, y, col, a, buf, 0.0)


@lru_cache(64)
def _gauss(R, r):
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
    return np.exp(-(xx ** 2 + yy ** 2) / (2 * r * r))


# ---------------------------------------------------------------- noise
def fbm(w, h, seed, octaves=6, base=4, gain=0.55):
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        n = base * 2 ** o
        r = rng.random((max(2, n * h // w), n)).astype(np.float32)
        acc += cv2.resize(r, (w, h), interpolation=cv2.INTER_CUBIC) * amp
        tot += amp; amp *= gain
    acc /= tot
    acc = (acc - acc.min()) / (acc.max() - acc.min())
    return acc


# ---------------------------------------------------------------- compose
_VIG = None
_GRAIN = None


def vignette():
    global _VIG
    if _VIG is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.72)) ** 2)
        _VIG = np.clip(1.08 - 0.42 * d ** 2.2, 0.35, 1.0)[..., None].astype(np.float32)
    return _VIG


def grain(seed):
    """静态抖动（约 ±1 LSB）：消除暗部渐变色带，且不随帧变化，不浪费码率"""
    global _GRAIN
    if _GRAIN is None:
        rng = np.random.default_rng(5)
        _GRAIN = ((rng.random((H, W, 1)) + rng.random((H, W, 1)) - 1.0) * (1.2 / 255)).astype(np.float32)
    return _GRAIN


def bloom(src, k=1.0):
    s4 = cv2.resize(src, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    b1 = cv2.GaussianBlur(s4, (0, 0), 2.2)
    s16 = cv2.resize(s4, (W // 16, H // 16), interpolation=cv2.INTER_AREA)
    b2 = cv2.GaussianBlur(s16, (0, 0), 3.0)
    s32 = cv2.resize(s16, (W // 32, H // 32), interpolation=cv2.INTER_AREA)
    b3 = cv2.GaussianBlur(s32, (0, 0), 3.0)
    b = b1 * 0.8 + cv2.resize(b2, (W // 4, H // 4), interpolation=cv2.INTER_LINEAR) * 0.9 + \
        cv2.resize(b3, (W // 4, H // 4), interpolation=cv2.INTER_LINEAR) * 0.7
    return cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR) * k


def apply_over(out, lst):
    for (mm, X0, Y0, colv, a) in lst:
        h, w = mm.shape
        X1, Y1 = min(X0 + w, W), min(Y0 + h, H)
        if X0 < 0 or Y0 < 0:
            dx, dy = max(-X0, 0), max(-Y0, 0)
            mm = mm[dy:, dx:]; X0 += dx; Y0 += dy
        if X1 <= X0 or Y1 <= Y0: continue
        mm = mm[:Y1 - Y0, :X1 - X0]
        reg = out[Y0:Y1, X0:X1]
        m3 = (mm * a)[..., None]
        reg *= (1 - m3)
        reg += m3 * colv


def compose(fr, bg):
    E = fr.E
    E += fr.U.astype(np.float32) * (1 / 255.0)
    out = bg + fr.L
    apply_over(out, fr.over)
    out += E
    out += bloom(E + fr.B, fr.bloom)
    if fr.flash > 0:
        out += fr.flash
    # 柔和高光压缩，保留色彩
    np.minimum(out, 4.0, out=out)
    hi = out > 0.82
    out[hi] = 0.82 + (1 - np.exp(-(out[hi] - 0.82) * 3.2)) * 0.18
    # 镜头：缩放 / 平移 / 旋转 / 抖动
    if abs(fr.zoom - 1) > 1e-4 or fr.cam != (0.0, 0.0) or fr.rot != 0 or fr.shake != (0.0, 0.0):
        M = cv2.getRotationMatrix2D((W / 2, H / 2), fr.rot, fr.zoom)
        M[0, 2] += fr.cam[0] + fr.shake[0]
        M[1, 2] += fr.cam[1] + fr.shake[1]
        out = cv2.warpAffine(out, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if fr.ca >= 0.5:
        d = max(1, int(round(fr.ca)))
        out[:, d:, 0] = out[:, :-d, 0].copy()
        out[:, :-d, 2] = out[:, d:, 2].copy()
    out *= vignette()
    return out


def to_u8(out, seed=0):
    out = out + grain(seed)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
