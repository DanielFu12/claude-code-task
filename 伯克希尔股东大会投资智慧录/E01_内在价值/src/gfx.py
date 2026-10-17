"""竖屏（1080×1920）合成用的小型图形库：文字、线条、图片窗口、粒子。帧为 float32 RGB（0..1）。"""
import math, os
from functools import lru_cache
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, '..', 'fonts')
BRAND_FONT_DIR = os.path.join(HERE, '..', '..', '..', 'brand', 'fonts')


def C(r, g, b): return np.array([r, g, b], np.float32) / 255.0


# ---------------------------------------------------------------- 配色（深黑 / 炭灰 / 品牌金）
INK = C(238, 232, 218)          # 主文字：暖白
INK2 = C(170, 164, 152)         # 次要文字：暖灰
INK3 = C(112, 108, 100)         # 弱化
GOLD = C(226, 178, 92)          # 品牌金（取自 GOLD_STOPS 中段）
GOLD_HI = C(255, 222, 150)
SUB_GOLD = C(214, 178, 112)     # brand.SUB_GOLD
BRICK = C(196, 98, 78)          # 少量警示色（只在“看错/亏损”处用）
BLUE = C(110, 175, 255)         # brand glow_rgb
GOLD_STOPS = [(0.0, (255, 243, 200)), (0.35, (255, 212, 120)), (0.62, (226, 160, 60)), (1.0, (255, 214, 130))]


def cl(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def eo(x): x = cl(x); return 1 - (1 - x) ** 3
def eio(x): x = cl(x); return x * x * (3 - 2 * x)
def lerp(a, b, x): return a + (b - a) * x


def env(t, a, b, fi=0.45, fo=0.45):
    """a..b 之间为 1，两端平滑淡入淡出"""
    if t < a or t > b: return 0.0
    return eio((t - a) / max(fi, 1e-3)) * eio((b - t) / max(fo, 1e-3))


# ---------------------------------------------------------------- 字体与文字
FONTS = {
    'serif_black': 'serif_black', 'serif_bold': 'serif_bold', 'serif_med': 'serif_med',
    'sans_light': 'sans_light', 'sans': 'sans_reg', 'sans_med': 'sans_med', 'sans_bold': 'sans_bold',
    'corm': 'corm', 'corm_med': 'corm_med', 'ebg': 'ebg_reg', 'ebg_i': 'ebg_ital', 'inter': 'inter_reg', 'inter_semi': 'inter_semi',
}


@lru_cache(128)
def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, FONTS[name] + '.ttf'), int(size))


LATIN_FALLBACK = {'inter': 'sans', 'inter_semi': 'sans_bold', 'ebg': 'serif_med', 'ebg_i': 'serif_med',
                  'corm': 'serif_med', 'corm_med': 'serif_med'}


@lru_cache(4000)
def text_mask(s, name, size, track=0.0):
    """整行文字的 alpha 蒙版；返回 (mask, 宽度, 基线 y)。西文字体遇到中文/全角字符时换用思源字体，避免缺字方块。"""
    if name in LATIN_FALLBACK and any(ord(c) > 0x2e80 for c in s):
        name = LATIN_FALLBACK[name]
    f = font(name, size)
    asc, desc = f.getmetrics()
    if track == 0:
        w = int(math.ceil(f.getlength(s))) + 4
    else:
        w = int(math.ceil(sum(f.getlength(c) for c in s) + track * size * max(len(s) - 1, 0))) + 4
    pad = int(size * 0.25)
    im = Image.new('L', (w + 2 * pad, asc + desc + 2 * pad), 0)
    d = ImageDraw.Draw(im)
    if track == 0:
        d.text((pad, pad + asc), s, font=f, fill=255, anchor='ls')
    else:
        x = pad
        for c in s:
            d.text((x, pad + asc), c, font=f, fill=255, anchor='ls'); x += f.getlength(c) + track * size
    m = np.asarray(im, np.float32) / 255.0
    return m, w, pad + asc, pad


def text_w(s, name, size, track=0.0):
    return text_mask(s, name, size, track)[1]


@lru_cache(64)
def ramp(h, stops=None):
    stops = stops or GOLD_STOPS
    y = np.linspace(0, 1, h)
    return np.stack([np.interp(y, [s[0] for s in stops], [s[1][c] for s in stops]) for c in range(3)], 1).astype(np.float32) / 255.0


def over(img, rgb, a, x0, y0):
    """alpha-over：rgb (h,w,3) 或 (3,)；a (h,w)。越界自动裁切。"""
    h, w = a.shape
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if X1 <= X0 or Y1 <= Y0: return
    aa = a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0][..., None]
    reg = img[Y0:Y1, X0:X1]
    if np.ndim(rgb) == 3:
        rgb = rgb[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
    reg *= (1 - aa)
    reg += aa * rgb


def add(img, rgb, a, x0, y0):
    h, w = a.shape
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if X1 <= X0 or Y1 <= Y0: return
    aa = a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0][..., None]
    if np.ndim(rgb) == 3: rgb = rgb[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
    img[Y0:Y1, X0:X1] += aa * rgb


def text(img, s, x, y, size, name='sans_med', col=INK, a=1.0, anchor='m', track=0.0, gold=False,
         shadow=0.55, wipe=None, rise=0.0, shine=None, glow=0.0, glow_col=None):
    """画一行字。y 为视觉中线；anchor：m 居中 / l 左对齐 / r 右对齐。
    gold=True 用品牌金色竖向渐变；wipe 0..1 为从左到右的柔和显现；shine 0..1 为流光位置。"""
    if a <= 0.003 or not s: return 0
    m, w, base, pad = text_mask(s, name, size, track)
    x0 = x - w / 2 if anchor == 'm' else (x if anchor == 'l' else x - w)
    x0 = int(round(x0 - pad)); y0 = int(round(y + size * 0.36 - base + rise))
    mm = m
    if wipe is not None and wipe < 1:
        ww = mm.shape[1]; soft = 0.3 * ww + 30
        g = np.clip((wipe * (ww + soft) - np.arange(ww)) / soft, 0, 1).astype(np.float32)
        mm = mm * g[None, :]
    if shadow > 0:
        sh = cv2.GaussianBlur(mm, (0, 0), max(1.5, size * 0.07))
        over(img, np.zeros(3, np.float32), sh * shadow * a, x0 + int(size * 0.02), y0 + int(size * 0.05))
    if glow > 0:
        gm = cv2.GaussianBlur(mm, (0, 0), size * 0.35)
        add(img, glow_col if glow_col is not None else GOLD, gm * glow * a, x0, y0)
    if gold:
        hh = mm.shape[0]
        top = max(0, int(base - size * 0.92)); bot = min(hh, int(base + size * 0.12))
        r = np.zeros((hh, 3), np.float32); rr = ramp(max(bot - top, 2))
        r[:top] = rr[0]; r[top:bot] = rr[:bot - top]; r[bot:] = rr[-1]
        rgb = np.broadcast_to(r[:, None, :], mm.shape + (3,)).copy()
    else:
        rgb = np.broadcast_to(np.asarray(col, np.float32), mm.shape + (3,)).copy()
    if shine is not None and 0 < shine < 1:
        hh, ww = mm.shape
        xs = np.arange(ww)[None, :] + np.arange(hh)[:, None] * 0.55
        pos = -80 + (0.5 - 0.5 * math.cos(shine * math.pi)) * (ww + 160)
        rgb = np.clip(rgb + np.exp(-((xs - pos) / (0.05 * ww + 14)) ** 2)[..., None] * 0.6, 0, 1.3)
    over(img, rgb, mm * a, x0, y0)
    return w


def wrap(s, name, size, maxw, track=0.0, cjk=None):
    """按像素宽度折行。cjk=True 时可在任意字处断行，否则按空格断。"""
    if cjk is None: cjk = any(ord(c) > 0x2e80 for c in s)
    out, cur = [], ''
    toks = list(s) if cjk else s.split(' ')
    sep = '' if cjk else ' '
    for tk in toks:
        cand = cur + (sep if cur else '') + tk
        if text_w(cand, name, size, track) <= maxw or not cur:
            cur = cand
        else:
            # 中文：标点不放行首
            if cjk and tk in '，。、；：？！”）》':
                cur = cand; continue
            out.append(cur); cur = tk
    if cur: out.append(cur)
    # 中文两行时尽量均衡
    if cjk and len(out) == 2:
        full = ''.join(out); best = None
        for k in range(len(full) // 2 - 8, len(full) // 2 + 9):
            if 0 < k < len(full) and full[k] not in '，。、；：？！”）》':
                a, b = full[:k], full[k:]
                if text_w(a, name, size) <= maxw and text_w(b, name, size) <= maxw:
                    sc = abs(text_w(a, name, size) - text_w(b, name, size))
                    # 断在标点后最好，其次在虚词后；硬断在词中间要付出代价
                    if a[-1] in '，、；：—': sc -= 400
                    elif a[-1] in '的了是和与就也都在把对从': sc -= 150
                    elif b[0] in '而却但就才': sc -= 120
                    else: sc += 60
                    if best is None or sc < best[0]: best = (sc, [a, b])
        if best: out = best[1]
    return out


# ---------------------------------------------------------------- 线条 / 形状（抗锯齿，alpha-over）
def _mask_draw(fn, box):
    x0, y0, x1, y1 = [int(v) for v in box]
    x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W), min(y1, H)
    if x1 <= x0 or y1 <= y0: return None, 0, 0
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    fn(m, x0, y0)
    return m.astype(np.float32) / 255.0, x0, y0


def line(img, p, q, col, a=1.0, th=2):
    if a <= 0.003: return
    pad = th + 3
    box = (min(p[0], q[0]) - pad, min(p[1], q[1]) - pad, max(p[0], q[0]) + pad + 1, max(p[1], q[1]) + pad + 1)
    m, x0, y0 = _mask_draw(lambda m, x0, y0: cv2.line(m, (int((p[0] - x0) * 16), int((p[1] - y0) * 16)),
                                                      (int((q[0] - x0) * 16), int((q[1] - y0) * 16)), 255, th, cv2.LINE_AA, 4), box)
    if m is not None: over(img, np.asarray(col, np.float32), m * a, x0, y0)


def poly(img, pts, col, a=1.0, th=2, closed=False, fill=False):
    if a <= 0.003 or len(pts) < 2: return
    P = np.asarray(pts, np.float64)
    pad = th + 3
    box = (P[:, 0].min() - pad, P[:, 1].min() - pad, P[:, 0].max() + pad + 1, P[:, 1].max() + pad + 1)

    def fn(m, x0, y0):
        q = ((P - [x0, y0]) * 16).astype(np.int32).reshape(-1, 1, 2)
        if fill: cv2.fillPoly(m, [q], 255, cv2.LINE_AA, 4)
        else: cv2.polylines(m, [q], closed, 255, th, cv2.LINE_AA, 4)
    m, x0, y0 = _mask_draw(fn, box)
    if m is not None: over(img, np.asarray(col, np.float32), m * a, x0, y0)


def rect(img, x0, y0, x1, y1, col, a=1.0):
    X0, Y0, X1, Y1 = int(max(x0, 0)), int(max(y0, 0)), int(min(x1, W)), int(min(y1, H))
    if X1 <= X0 or Y1 <= Y0 or a <= 0.003: return
    reg = img[Y0:Y1, X0:X1]; reg *= (1 - a); reg += a * np.asarray(col, np.float32)


def rrect(img, x0, y0, x1, y1, r, col, a=1.0, th=2, fill=False):
    pts = []
    for cx, cy, s in ((x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, math.pi / 2), (x0 + r, y0 + r, math.pi)):
        for k in range(9):
            ang = s + k / 8 * math.pi / 2
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    poly(img, pts, col, a, th, closed=True, fill=fill)


def circle(img, c, r, col, a=1.0, th=2, fill=False):
    if a <= 0.003: return
    box = (c[0] - r - th - 3, c[1] - r - th - 3, c[0] + r + th + 4, c[1] + r + th + 4)
    m, x0, y0 = _mask_draw(lambda m, x0, y0: cv2.circle(m, (int((c[0] - x0) * 16), int((c[1] - y0) * 16)), int(r * 16), 255,
                                                        -1 if fill else th, cv2.LINE_AA, 4), box)
    if m is not None: over(img, np.asarray(col, np.float32), m * a, x0, y0)


@lru_cache(32)
def soft_dot(r):
    R = int(r * 3) + 1
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
    return np.exp(-(xx ** 2 + yy ** 2) / (2 * r * r))


def glow(img, c, r, col, a=1.0):
    g = soft_dot(float(round(r, 1)))
    R = g.shape[0] // 2
    add(img, np.asarray(col, np.float32), g * a, int(c[0]) - R, int(c[1]) - R)


# ---------------------------------------------------------------- 背景
def make_background(seed=3):
    """深黑到炭灰的径向底色 + 极淡的暖色雾 + 暗角"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W * 0.5) / W) ** 2 + ((yy - H * 0.42) / H) ** 2 * 1.4)
    base = np.array([0.028, 0.026, 0.024], np.float32)
    lift = np.array([0.050, 0.045, 0.038], np.float32)
    bg = base + lift * np.exp(-d * d * 7)[..., None]
    rng = np.random.default_rng(seed)
    fog = cv2.resize(rng.random((12, 7)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
    fog = cv2.GaussianBlur(fog, (0, 0), 90)
    bg += (fog[..., None] - 0.5) * np.array([0.020, 0.016, 0.010], np.float32)
    return bg


def make_vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    return np.clip(1.08 - 0.55 * d ** 2.2, 0.35, 1.0)[..., None].astype(np.float32)


def make_grain(n=6, seed=11):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        g = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
        g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)
        out.append((g * 0.010)[..., None])
    return out


# ---------------------------------------------------------------- 历史影像
class Clip:
    """顺序读帧的视频源（每个渲染进程处理连续区间，所以基本只往前读）"""
    def __init__(self, path, fps=30):
        self.path, self.fps = path, fps
        self.cap = None; self.idx = -1; self.frame = None

    def get(self, t):
        i = max(0, int(t * self.fps))
        if self.cap is None or i < self.idx or i > self.idx + 60:
            if self.cap is not None: self.cap.release()
            self.cap = cv2.VideoCapture(self.path)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            self.idx = i - 1
            self.frame = None
        while self.idx < i:
            ok, f = self.cap.read()
            if not ok: break
            self.frame = f; self.idx += 1
        if self.frame is None:
            ok, self.frame = self.cap.read()
        return cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


def grade(img, sat=0.62, warm=(1.04, 1.0, 0.9), lift=0.025, contrast=1.08, gain=1.0):
    """历史影像调色：降饱和、偏暖、轻微抬黑、S 曲线"""
    lum = img @ np.array([0.299, 0.587, 0.114], np.float32)
    out = lum[..., None] + (img - lum[..., None]) * sat
    out = out * np.array(warm, np.float32) * gain
    out = (out - 0.5) * contrast + 0.5
    out = lift + out * (1 - lift)
    return np.clip(out, 0, 1)


def window(img, src, cx, cy, w, h, zoom=1.0, pan=(0.0, 0.0), a=1.0, feather=36, blur_bg=0.0):
    """把历史影像放进居中的宽银幕窗口（不拉伸，只等比缩放/裁切），上下边缘羽化。
    blur_bg>0 时，用同一画面的放大模糊版作为整屏底（模糊背景扩展）。"""
    if a <= 0.003: return
    sh, sw = src.shape[:2]
    s = max(w / sw, h / sh) * zoom
    M = np.array([[s, 0, w / 2 - s * (sw / 2 + pan[0] * sw)], [0, s, h / 2 - s * (sh / 2 + pan[1] * sh)]], np.float32)
    win = cv2.warpAffine(src, M, (int(w), int(h)), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    if blur_bg > 0:
        small = cv2.resize(src, (sw // 12, sh // 12), interpolation=cv2.INTER_AREA)
        small = cv2.GaussianBlur(small, (0, 0), 3)
        bs = max(W / small.shape[1], H / small.shape[0])
        big = cv2.resize(small, (int(small.shape[1] * bs) + 2, int(small.shape[0] * bs) + 2), interpolation=cv2.INTER_LINEAR)
        oy, ox = (big.shape[0] - H) // 2, (big.shape[1] - W) // 2
        big = big[oy:oy + H, ox:ox + W]
        img *= (1 - blur_bg * a)
        img += big * (blur_bg * a * 0.38)
    m = np.ones((int(h), int(w)), np.float32)
    ramp_ = np.linspace(0, 1, feather, dtype=np.float32) ** 1.5
    m[:feather] *= ramp_[:, None]; m[-feather:] *= ramp_[::-1, None]
    side = 14
    sr_ = np.linspace(0, 1, side, dtype=np.float32)
    m[:, :side] *= sr_[None, :]; m[:, -side:] *= sr_[None, ::-1]
    over(img, win, m * a, int(cx - w / 2), int(cy - h / 2))
