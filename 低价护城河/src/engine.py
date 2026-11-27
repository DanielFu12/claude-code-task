"""竖屏 1080×1920 动态图形小引擎：文字、图片、线条、辉光、调色、颗粒。画布为 float32 RGB 0..1。"""
import os, math, functools
import numpy as np, cv2
cv2.setNumThreads(1)
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
FONTS = os.path.join(ROOT, 'fonts'); MEDIA = os.path.join(ROOT, 'media')

# ── 调色板 ──
GOLD = (0.95, 0.76, 0.42); GOLD_HI = (1.0, 0.90, 0.66); RED = (0.90, 0.30, 0.27); BLUE = (0.45, 0.64, 0.80)
TEAL = (0.40, 0.80, 0.72); WHITE = (0.96, 0.95, 0.92); GREY = (0.56, 0.58, 0.62); INK = (0.035, 0.04, 0.055)


def hexc(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


# ── 缓动 ──
def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def lin(t, t0, t1): return clamp((t - t0) / max(1e-6, t1 - t0))
def ease(x): x = clamp(x); return x * x * (3 - 2 * x)
def eout(x): x = clamp(x); return 1 - (1 - x) ** 3
def ein(x): x = clamp(x); return x ** 3
def eback(x, s=1.6): x = clamp(x) - 1; return 1 + x * x * ((s + 1) * x + s)
def fade(t, t0, t1, d0=0.35, d1=0.35):
    """t0 渐入、t1 渐出的不透明度"""
    return ease(lin(t, t0, t0 + d0)) * (1 - ease(lin(t, t1 - d1, t1)))
def mix(a, b, k): return tuple(x + (y - x) * k for x, y in zip(a, b))


# ── 字体与文字贴片 ──
@functools.lru_cache(None)
def font(name, size): return ImageFont.truetype(os.path.join(FONTS, name + '.ttf'), int(size))


@functools.lru_cache(4096)
def text_patch(s, fname, size, color=WHITE, track=0.0, stroke=0, grad=None):
    """返回 (rgb, alpha) float32；grad=(top,bottom) 竖向渐变"""
    f = font(fname, size); pad = int(size * 0.35) + stroke * 2
    ws = [f.getbbox(c)[2] - f.getbbox(c)[0] if c != ' ' else size * 0.3 for c in s]
    adv = [f.getlength(c) for c in s]
    tw = int(sum(adv) + track * size * max(0, len(s) - 1)) + 2 * pad
    asc, desc = f.getmetrics(); th = asc + desc + 2 * pad
    im = Image.new('L', (max(1, tw), th), 0); d = ImageDraw.Draw(im); x = pad
    for c, a in zip(s, adv):
        d.text((x, pad), c, font=f, fill=255, stroke_width=stroke, stroke_fill=255); x += a + track * size
    al = np.asarray(im, np.float32) / 255
    if grad:
        k = np.linspace(0, 1, th, dtype=np.float32)[:, None, None]
        rgb = np.asarray(grad[0], np.float32) * (1 - k) + np.asarray(grad[1], np.float32) * k
        rgb = np.broadcast_to(rgb, (th, max(1, tw), 3)).copy()
    else:
        rgb = np.broadcast_to(np.asarray(color, np.float32), (th, max(1, tw), 3)).copy()
    return rgb, al


def blit(cv, rgb, al, x, y, anchor='c', alpha=1.0, scale=1.0, add=False):
    """把贴片合成到画布。anchor: c 中心 / l 左中 / r 右中 / tl 左上"""
    if alpha <= 0.003: return
    if abs(scale - 1) > 1e-3:
        h0, w0 = al.shape; nw, nh = max(1, int(w0 * scale)), max(1, int(h0 * scale))
        rgb = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
        al = cv2.resize(al, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    h, w = al.shape
    if anchor == 'c': x0, y0 = x - w / 2, y - h / 2
    elif anchor == 'l': x0, y0 = x, y - h / 2
    elif anchor == 'r': x0, y0 = x - w, y - h / 2
    else: x0, y0 = x, y
    x0, y0 = int(round(x0)), int(round(y0))
    ax0, ay0 = max(0, x0), max(0, y0); ax1, ay1 = min(cv.shape[1], x0 + w), min(cv.shape[0], y0 + h)
    if ax1 <= ax0 or ay1 <= ay0: return
    a = al[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0, None] * alpha
    c = rgb[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0]
    reg = cv[ay0:ay1, ax0:ax1]
    if add: reg += c * a
    else: reg *= (1 - a); reg += c * a


def text(cv, s, x, y, fname='sans_med', size=48, color=WHITE, anchor='c', alpha=1.0, scale=1.0, track=0.0,
         shadow=0.0, glow=0.0, grad=None, stroke=0):
    rgb, al = text_patch(s, fname, int(size), tuple(color), track, stroke, grad)
    if shadow > 0:
        sh = cv2.GaussianBlur(al, (0, 0), size * 0.12)
        blit(cv, np.zeros_like(rgb), np.clip(sh * 1.4, 0, 1), x, y + size * 0.04, anchor, alpha * shadow, scale)
    if glow > 0:
        g = cv2.GaussianBlur(al, (0, 0), size * 0.25)
        blit(cv, rgb, g, x, y, anchor, alpha * glow, scale, add=True)
    blit(cv, rgb, al, x, y, anchor, alpha, scale)
    h, w = al.shape
    return w * scale, h * scale


def text_w(s, fname, size, track=0.0):
    f = font(fname, size); return sum(f.getlength(c) for c in s) + track * size * max(0, len(s) - 1)


# ── 图片 ──
@functools.lru_cache(64)
def load_img(name, maxw=2200):
    p = os.path.join(MEDIA, name)
    im = cv2.imread(p, cv2.IMREAD_COLOR)
    if im is None: raise FileNotFoundError(p)
    if im.shape[1] > maxw: im = cv2.resize(im, (maxw, int(im.shape[0] * maxw / im.shape[1])), interpolation=cv2.INTER_AREA)
    return im[..., ::-1].astype(np.float32) / 255


def cover(img, w, h, zoom=1.0, cx=0.5, cy=0.5, rot=0.0):
    """Ken Burns：以 (cx,cy)（相对坐标）为中心按 cover 方式裁出 w×h，zoom>1 推近"""
    ih, iw = img.shape[:2]; s = max(w / iw, h / ih) * zoom
    px, py = cx * iw, cy * ih
    px = clamp(px, w / s / 2, iw - w / s / 2); py = clamp(py, h / s / 2, ih - h / s / 2)
    M = cv2.getRotationMatrix2D((px, py), rot, s); M[0, 2] += w / 2 - px; M[1, 2] += h / 2 - py
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def grade(x, sat=0.85, warm=0.0, contrast=1.08, lift=0.0, gain=1.0, tint=None):
    """调色（显示空间）：饱和度、冷暖、对比、暗部抬升"""
    y = x
    l = y.mean(2, keepdims=True); y = l + (y - l) * sat
    if warm: y = y * np.array([1 + 0.10 * warm, 1 + 0.02 * warm, 1 - 0.12 * warm], np.float32)
    if tint is not None: y = y * (1 - tint[1]) + np.asarray(tint[0], np.float32) * y.mean(2, keepdims=True) * tint[1] * 1.6
    y = (y - 0.5) * contrast + 0.5 + lift
    return np.clip(y * gain, 0, 1)


class Clip:
    """顺序读取视频片段（裁成竖屏中心区域），按秒取帧；用于 ABC 档案画面（4:3 内容居中于 16:9）"""
    def __init__(self, name, crop_w=608, cx=0.5):
        self.p = os.path.join(MEDIA, 'clips', name); self.cap = None; self.idx = -1; self.frame = None
        self.crop_w = crop_w; self.cx = cx
        c = cv2.VideoCapture(self.p); self.fps = c.get(cv2.CAP_PROP_FPS); self.n = int(c.get(cv2.CAP_PROP_FRAME_COUNT)); c.release()

    def get(self, t):
        i = int(clamp(t, 0, (self.n - 1) / self.fps) * self.fps)
        if self.cap is None or i < self.idx or i > self.idx + 40:
            if self.cap is None: self.cap = cv2.VideoCapture(self.p)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, i); self.idx = i - 1
        while self.idx < i:
            ok, f = self.cap.read()
            if not ok: break
            self.frame = f; self.idx += 1
        f = self.frame; hh, ww = f.shape[:2]
        x0 = int(ww * self.cx - self.crop_w / 2)
        return f[:, x0:x0 + self.crop_w, ::-1].astype(np.float32) / 255


# ── 形状（cv2 抗锯齿，画在单独的 alpha 层上再上色合成）──
def layer(): return np.zeros((H, W), np.float32)


def stroke_layer(cv, lay, color, alpha=1.0, glow=0.0, add=False):
    if glow > 0:
        small = cv2.resize(lay, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        g = cv2.resize(cv2.GaussianBlur(small, (0, 0), 6), (W, H))
        cv += np.asarray(color, np.float32) * g[..., None] * glow * alpha
    a = np.clip(lay, 0, 1)[..., None] * alpha
    c = np.asarray(color, np.float32)
    if add: cv += c * a
    else: cv *= (1 - a); cv += c * a


def S(x): return int(round(x * 16))  # cv2 亚像素坐标（shift=4）


def line(lay, p0, p1, w=3, v=1.0):
    if abs(p1[0] - p0[0]) + abs(p1[1] - p0[1]) < 1.0: return   # 零长度不画（否则会留一个点）
    cv2.line(lay, (S(p0[0]), S(p0[1])), (S(p1[0]), S(p1[1])), v, max(1, int(w)), cv2.LINE_AA, 4)


def poly(lay, pts, w=3, v=1.0, closed=False):
    p = np.array([[S(x), S(y)] for x, y in pts], np.int32)
    cv2.polylines(lay, [p], closed, v, max(1, int(w)), cv2.LINE_AA, 4)


def fpoly(lay, pts, v=1.0):
    p = np.array([[S(x), S(y)] for x, y in pts], np.int32)
    cv2.fillPoly(lay, [p], v, cv2.LINE_AA, 4)


def circle(lay, c, r, w=3, v=1.0, fill=False):
    cv2.circle(lay, (S(c[0]), S(c[1])), S(r), v, -1 if fill else max(1, int(w)), cv2.LINE_AA, 4)


def arc(lay, c, r, a0, a1, w=3, v=1.0):
    """角度（度），0 在正上方顺时针"""
    n = max(2, int(abs(a1 - a0) / 2))
    pts = [(c[0] + r * math.sin(math.radians(a)), c[1] - r * math.cos(math.radians(a))) for a in np.linspace(a0, a1, n)]
    poly(lay, pts, w, v)


def rect(lay, x0, y0, x1, y1, v=1.0, fill=True, w=2, r=0):
    if r <= 0:
        cv2.rectangle(lay, (S(x0), S(y0)), (S(x1), S(y1)), v, -1 if fill else w, cv2.LINE_AA, 4); return
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, 0), (x1 - r, y1 - r, 90), (x0 + r, y1 - r, 180), (x0 + r, y0 + r, 270)):
        for a in np.linspace(a0, a0 + 90, 8):
            pts.append((cx + r * math.sin(math.radians(a)), cy - r * math.cos(math.radians(a))))
    (fpoly if fill else poly)(lay, pts, *(() if fill else (w,)), **({'v': v} if fill else {'v': v, 'closed': True}))


def fill(cv, mask, color, alpha=1.0):
    a = np.clip(mask, 0, 1)[..., None] * alpha; cv *= (1 - a); cv += np.asarray(color, np.float32) * a


# ── 全局质感 ──
_rng = np.random.default_rng(3)
GRAIN = [cv2.resize(_rng.standard_normal((H // 2, W // 2)).astype(np.float32), (W, H)) for _ in range(6)]
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.55 * (((_xx - W / 2) / (W * 0.72)) ** 2 + ((_yy - H * 0.47) / (H * 0.62)) ** 2)).clip(0.25, 1)[..., None]


def bloom(cv, thr=0.72, k=0.35):
    small = cv2.resize(cv, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    hi = np.clip(small - thr, 0, None)
    b = cv2.GaussianBlur(hi, (0, 0), 7) + cv2.GaussianBlur(hi, (0, 0), 22) * 0.6
    cv += cv2.resize(b, (W, H)) * k


def finish(cv, fi, grain=0.016, vig=True):
    bloom(cv)
    if vig: cv *= VIG
    cv += GRAIN[fi % len(GRAIN)][..., None] * grain * (0.4 + 0.6 * np.sqrt(np.clip(cv.mean(2, keepdims=True), 0, 1)))
    np.clip(cv, 0, 1, out=cv)
    return cv


def bg(cv, t, tint=(0.07, 0.08, 0.11), k=1.0):
    """深色径向渐变底"""
    g = (1 - np.clip(np.sqrt(((_xx - W / 2) / W) ** 2 + ((_yy - H * 0.42) / (H * 0.8)) ** 2) * 1.5, 0, 1))[..., None]
    cv[:] = np.asarray(INK, np.float32) + np.asarray(tint, np.float32) * g * k


class Dust:
    """缓慢漂浮的金色尘埃"""
    def __init__(self, n=70, seed=1):
        r = np.random.default_rng(seed); self.p = r.random((n, 2)) * [W, H]; self.v = (r.random((n, 2)) - 0.5) * [14, 22] - [0, 8]
        self.s = r.random(n) * 2.4 + 0.8; self.ph = r.random(n) * 6.28

    def draw(self, cv, t, color=GOLD, alpha=0.5):
        lay = layer()
        for (x, y), (vx, vy), s, ph in zip(self.p, self.v, self.s, self.ph):
            px = (x + vx * t) % W; py = (y + vy * t) % H
            circle(lay, (px, py), s, v=0.5 + 0.5 * math.sin(t * 0.9 + ph), fill=True)
        stroke_layer(cv, lay, color, alpha, glow=1.2, add=True)


@functools.lru_cache(64)
def graded(name, sat=0.85, warm=0.0, contrast=1.08, lift=0.0, gain=1.0, tint=None, maxw=2200):
    return grade(load_img(name, maxw), sat, warm, contrast, lift, gain, tint).astype(np.float32)
