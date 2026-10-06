"""Tiny additive-light motion-graphics engine (numpy + cv2 + PIL)."""
import math, os
from functools import lru_cache
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, '..', 'fonts')
FONTS = {k: os.path.join(FONT_DIR, k + '.ttf') for k in
         ['serif_light', 'serif_med', 'serif_black', 'sans_light', 'sans_med', 'sans_black', 'corm', 'orb', 'mono']}

# ---------------------------------------------------------------- easing
def cl(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x
def eo(x):  # ease out cubic
    x = cl(x); return 1 - (1 - x) ** 3
def ei(x):
    x = cl(x); return x ** 3
def eio(x):
    x = cl(x); return x * x * (3 - 2 * x)
def eback(x, s=1.7):
    x = cl(x); x -= 1; return x * x * ((s + 1) * x + s) + 1
def env(t, a, b, fi=0.35, fo=0.35):
    if t < a or t > b: return 0.0
    return eo((t - a) / max(fi, 1e-3)) * (eo((b - t) / max(fo, 1e-3)) if fo > 0 else 1.0)
def lerp(a, b, x):
    return a + (b - a) * x
def lerpc(c1, c2, x):
    return tuple(lerp(p, q, x) for p, q in zip(c1, c2))
def keys(t, kf):
    """piecewise smooth interpolation of (time, value-tuple-or-float) keyframes"""
    if t <= kf[0][0]: return kf[0][1]
    for (t0, v0), (t1, v1) in zip(kf, kf[1:]):
        if t <= t1:
            x = eio((t - t0) / max(t1 - t0, 1e-6))
            if isinstance(v0, tuple): return lerpc(v0, v1, x)
            return lerp(v0, v1, x)
    return kf[-1][1]

def C(r, g, b):
    return (r / 255.0, g / 255.0, b / 255.0)

GOLD = C(255, 204, 110); GOLD2 = C(255, 236, 180); GOLDD = C(214, 146, 50)
CYAN = C(70, 220, 255); VIOLET = C(150, 100, 255); MAGENTA = C(255, 70, 185)
RED = C(255, 64, 82); TEAL = C(60, 235, 195); ORANGE = C(255, 140, 50)
WHITE = (1.0, 1.0, 1.0); BLUE = C(70, 130, 255); GREEN = C(120, 255, 150); PINK = C(255, 130, 200)
GREY = C(150, 160, 185)

# ---------------------------------------------------------------- glyphs
@lru_cache(64)
def font(name, size):
    return ImageFont.truetype(FONTS[name], size)

@lru_cache(20000)
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


class Frame:
    def __init__(self, t):
        self.t = t
        self.L = np.zeros((H, W, 3), np.float32)   # crisp additive (no bloom)
        self.E = np.zeros((H, W, 3), np.float32)   # crisp additive + bloom
        self.B = np.zeros((H, W, 3), np.float32)   # bloom only
        self.U = np.zeros((H, W, 3), np.uint8)     # cv2 AA strokes -> E
        self.over = []                             # deferred alpha-over glyphs
        self.ca = 0.0                              # chromatic aberration px
        self.flash = 0.0
        self.shake = (0, 0)

    # ------------------------------------------------ primitive helpers
    def _c(self, col, a):
        return tuple(float(cl(c * a) * 255) for c in col)

    def line(self, p0, p1, col, a=1.0, th=2):
        if a <= 0.003: return
        cv2.line(self.U, (int(p0[0] * 16), int(p0[1] * 16)), (int(p1[0] * 16), int(p1[1] * 16)),
                 self._c(col, a), th, cv2.LINE_AA, 4)

    def poly(self, pts, col, a=1.0, th=2, closed=False):
        if a <= 0.003 or len(pts) < 2: return
        p = (np.asarray(pts, np.float64) * 16).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(self.U, [p], closed, self._c(col, a), th, cv2.LINE_AA, 4)

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

    def circle(self, c, r, col, a=1.0, th=2):
        if a <= 0.003 or r <= 0: return
        cv2.circle(self.U, (int(c[0] * 16), int(c[1] * 16)), int(r * 16), self._c(col, a), th, cv2.LINE_AA, 4)

    def arc(self, c, r, a0, a1, col, a=1.0, th=2, n=64):
        ts = np.linspace(a0, a1, n)
        self.poly(np.stack([c[0] + r * np.cos(ts), c[1] + r * np.sin(ts)], 1), col, a, th)

    def rrect(self, x0, y0, x1, y1, r, col, a=1.0, th=2):
        pts = []
        for cx, cy, s in ((x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, math.pi / 2), (x0 + r, y0 + r, math.pi)):
            for k in range(9):
                ang = s + k / 8 * math.pi / 2
                pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        self.poly(pts, col, a, th, closed=True)
        return pts

    def rrect_fill(self, x0, y0, x1, y1, r, col, a=0.1, buf='L'):
        pts = []
        for cx, cy, s in ((x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, math.pi / 2), (x0 + r, y0 + r, math.pi)):
            for k in range(9):
                ang = s + k / 8 * math.pi / 2
                pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        self.fillpoly(pts, col, a, buf)

    def glow(self, c, r, col, a=1.0, buf='B'):
        """soft radial blob (gaussian) added to buffer"""
        if a <= 0.003 or r <= 0.5: return
        R = int(r * 3)
        x0, y0, x1, y1 = int(c[0]) - R, int(c[1]) - R, int(c[0]) + R + 1, int(c[1]) + R + 1
        X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
        if X1 <= X0 or Y1 <= Y0: return
        yy, xx = np.mgrid[Y0:Y1, X0:X1].astype(np.float32)
        g = np.exp(-((xx - c[0]) ** 2 + (yy - c[1]) ** 2) / (2 * r * r)) * a
        getattr(self, buf)[Y0:Y1, X0:X1] += g[..., None] * np.array(col, np.float32)

    def splat(self, xs, ys, cols, a, buf='E'):
        xs = np.asarray(xs); ys = np.asarray(ys)
        xi = np.round(xs).astype(np.int64); yi = np.round(ys).astype(np.int64)
        ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
        if not ok.any(): return
        a = np.broadcast_to(np.asarray(a, np.float32), xs.shape)[ok]
        cols = np.asarray(cols, np.float32)
        cols = cols[ok] if cols.ndim == 2 else np.broadcast_to(cols, (ok.sum(), 3))
        idx = yi[ok] * W + xi[ok]
        b = getattr(self, buf).reshape(-1, 3)
        np.add.at(b, idx, cols * a[:, None])

    def dots(self, xs, ys, cols, a, rad, buf='E'):
        """bigger particles: splat to a 3x3 kernel"""
        for dx, dy, w in ((0, 0, 1.0), (1, 0, .5), (-1, 0, .5), (0, 1, .5), (0, -1, .5),
                          (1, 1, .2), (-1, -1, .2), (1, -1, .2), (-1, 1, .2)):
            self.splat(np.asarray(xs) + dx * rad, np.asarray(ys) + dy * rad, cols, np.asarray(a) * w, buf)

    # ------------------------------------------------ text
    def text(self, s, x, y, size, fnt='sans_med', col=WHITE, a=1.0, anchor='m', track=0.0,
             mode='L', glow=0.0, grad=None, t0=None, stag=0.035, dur=0.45, rise=18, out=None,
             scale_in=0.0, blur_in=False, chars_alpha=None):
        """draw a single line. anchor: 'm' centre, 'l' left, 'r' right. y = visual centre.
        mode: 'L' additive crisp, 'E' additive+bloom, 'O' alpha-over (deferred)."""
        if a <= 0.003 or not s: return
        tw = text_width(s, fnt, size, track)
        xs = x - tw / 2 if anchor == 'm' else (x if anchor == 'l' else x - tw)
        base = y + size * 0.36
        n = len(s)
        cx = xs
        for i, ch in enumerate(s):
            m, adv, pad, bl = glyph(ch, fnt, size)
            ai = a
            dy = 0.0
            if t0 is not None:
                p = (self.t - t0 - i * stag) / dur
                ai *= eo(p)
                dy = (1 - eo(p)) * rise
            if out is not None:   # (t_out_start, duration) per-char dissolve upwards
                p = (self.t - out[0] - i * stag * 0.5) / out[1]
                ai *= 1 - eio(p)
                dy -= eio(p) * rise
            if chars_alpha is not None:
                ai *= chars_alpha[i]
            if ai > 0.003 and ch != ' ':
                if grad is not None:
                    u = (cx + adv / 2 - xs) / max(tw, 1)
                    colc = grad_color(grad, u)
                else:
                    colc = col
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
        else:
            getattr(self, mode)[Y0:Y1, X0:X1] += (mm * a)[..., None] * colv
        if glow > 0:
            self.B[Y0:Y1, X0:X1] += (mm * a * glow)[..., None] * colv

    def lines(self, rows, x, y, size, lh=1.55, **kw):
        n = len(rows)
        for i, r in enumerate(rows):
            kw2 = dict(kw)
            if 't0' in kw2 and kw2['t0'] is not None:
                kw2['t0'] = kw2['t0'] + i * kw2.pop('row_delay', 0.25)
            else:
                kw2.pop('row_delay', None)
            self.text(r, x, y + (i - (n - 1) / 2) * size * lh, size, **kw2)


def grad_color(grad, u):
    u = cl(u)
    k = len(grad) - 1
    i = min(int(u * k), k - 1)
    return lerpc(grad[i], grad[i + 1], u * k - i)


# ---------------------------------------------------------------- noise / backgrounds
def fbm(w, h, seed, octaves=6, base=4):
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        n = base * 2 ** o
        r = rng.random((max(2, n * h // w), n)).astype(np.float32)
        acc += cv2.resize(r, (w, h), interpolation=cv2.INTER_CUBIC) * amp
        tot += amp; amp *= 0.55
    acc /= tot
    acc = (acc - acc.min()) / (acc.max() - acc.min())
    return acc


def finish(fr, bg, bloom_k=1.0, vignette=None, grain=None):
    """compose buffers into uint8 RGB"""
    E = fr.E
    E += fr.U.astype(np.float32) * (1 / 255.0)
    src = E + fr.B
    s4 = cv2.resize(src, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    b1 = cv2.GaussianBlur(s4, (0, 0), 3.0)
    s16 = cv2.resize(s4, (W // 16, H // 16), interpolation=cv2.INTER_AREA)
    b2 = cv2.GaussianBlur(s16, (0, 0), 3.5)
    bl = cv2.resize(b1 * 0.9 + cv2.resize(b2, (W // 4, H // 4), interpolation=cv2.INTER_LINEAR) * 1.1,
                    (W, H), interpolation=cv2.INTER_LINEAR)
    out = bg + fr.L + E + bl * bloom_k
    if fr.flash > 0:
        out += fr.flash
    for (mm, X0, Y0, colv, a) in fr.over:
        h, w = mm.shape
        reg = out[Y0:Y0 + h, X0:X0 + w]
        m3 = (mm * a)[..., None]
        reg *= (1 - m3)
        reg += m3 * colv
    # soft shoulder tone-map (keeps colours from clipping to flat white)
    out = np.where(out > 0.8, 0.8 + (1 - np.exp(-(out - 0.8) * 3.5)) * 0.2 / 1.0, out)
    if vignette is not None:
        out *= vignette
    if fr.ca >= 0.5:
        d = max(1, int(round(fr.ca)))
        out[:, d:, 0] = out[:, :-d, 0].copy()
        out[:, :-d, 2] = out[:, d:, 2].copy()
    if fr.shake != (0, 0):
        out = np.roll(out, fr.shake, axis=(0, 1))
    if grain is not None:
        out += grain
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
