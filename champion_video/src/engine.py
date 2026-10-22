"""竖屏 1080×1920 动态图形引擎（numpy + OpenCV + Pillow/RAQM）。

画面模型：
  F.img  —— 主画面（float32 RGB, 0..1 显示空间），所有元素按 alpha 叠加或加色叠加
  F.glow —— 发光缓冲，只参与辉光（bloom），不直接显示
最终 finish(): img + bloom(glow + 高光) → 柔和高光压缩 → 暗角 → 颗粒 → uint8
"""
import math, os
from functools import lru_cache
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, '..', 'fonts')


# ---------------------------------------------------------------- easing / helpers
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
def eio5(x):
    x = cl(x); return x ** 3 * (x * (6 * x - 15) + 10)
def eback(x, s=1.70158):
    x = cl(x) - 1; return x * x * ((s + 1) * x + s) + 1
def eelastic(x):
    x = cl(x)
    if x in (0, 1): return x
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi / 3)) + 1
def lerp(a, b, x):
    return a + (b - a) * x
def lerpc(c1, c2, x):
    return tuple(lerp(p, q, x) for p, q in zip(c1, c2))
def ramp(t, a, b):
    return cl((t - a) / max(b - a, 1e-6))
def env(t, a, b, fi=0.4, fo=0.4):
    """a..b 之间可见，淡入 fi 秒、淡出 fo 秒"""
    if t < a or t > b: return 0.0
    return eo((t - a) / max(fi, 1e-3)) * (eio((b - t) / fo) if fo > 0 else 1.0)
def hexc(s):
    s = s.lstrip('#'); return tuple(int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))
def mix(c, k):
    return tuple(min(1.0, v * k) for v in c)


# ---------------------------------------------------------------- palette
BG0 = hexc('#03050B'); BG1 = hexc('#0A1222')
WHITE = (1.0, 1.0, 1.0); INK = hexc('#E9EEF7'); DIM = hexc('#8C97AD'); FAINT = hexc('#4A556B')
US = hexc('#4FD1FF'); US2 = hexc('#2A7BFF')          # 美股 冰蓝
CN = hexc('#FF9A3C'); CN2 = hexc('#FF5E3A')          # A 股 琥珀橙
UP = hexc('#FF4057'); DOWN = hexc('#22D49A')          # 中国习惯：红涨绿跌
GOLD = hexc('#FFD478'); GOLD_L = hexc('#FFF3C8'); GOLD_D = hexc('#E2A03C')
VIOLET = hexc('#8F7BFF')


# ---------------------------------------------------------------- fonts & text sprites
FONTS = {
    'serif': 'serif_bold', 'serif_black': 'serif_black', 'serif_med': 'serif_med',
    'sans': 'sans_med', 'sans_light': 'sans_light', 'sans_reg': 'sans_reg', 'sans_bold': 'sans_bold', 'sans_black': 'sans_black',
    'num': 'inter_xbold', 'num_semi': 'inter_semi', 'num_reg': 'inter_reg', 'num_black': 'intert_black',
    'corm': 'corm', 'mono': 'mono',
}


@lru_cache(128)
def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, FONTS.get(name, name) + '.ttf'), int(size),
                              layout_engine=ImageFont.Layout.RAQM)


@lru_cache(4096)
def text_mask(s, fname, size, track=0.0, tnum=True):
    """整行文字 → (mask float32, 基线 y, 宽)；数字用等宽 tnum，便于计数器不抖动。track 为字距(×字号)"""
    f = font(fname, size)
    feats = ['tnum', 'kern'] if tnum else ['kern']
    asc, desc = f.getmetrics()
    if track == 0:
        w = int(math.ceil(f.getlength(s, features=feats))) + 4
        pad = int(size * 0.25) + 4
        im = Image.new('L', (w + 2 * pad, asc + desc + 2 * pad), 0)
        ImageDraw.Draw(im).text((pad, pad + asc), s, font=f, fill=255, anchor='ls', features=feats)
        return np.asarray(im, np.float32) / 255, pad + asc, pad, w
    adv = [f.getlength(c, features=feats) for c in s]
    w = int(math.ceil(sum(adv) + track * size * (len(s) - 1))) + 4
    pad = int(size * 0.25) + 4
    im = Image.new('L', (w + 2 * pad, asc + desc + 2 * pad), 0)
    d = ImageDraw.Draw(im); x = pad
    for c, a in zip(s, adv):
        d.text((x, pad + asc), c, font=f, fill=255, anchor='ls', features=feats); x += a + track * size
    return np.asarray(im, np.float32) / 255, pad + asc, pad, w


def text_w(s, fname, size, track=0.0):
    return text_mask(s, fname, size, track)[3]


def vgrad(h, stops):
    """竖向渐变 (h,1,3)；stops=[(pos,(r,g,b)),...]"""
    y = np.linspace(0, 1, h)
    return np.stack([np.interp(y, [p for p, _ in stops], [c[k] for _, c in stops]) for k in range(3)], 1)[:, None, :].astype(np.float32)


# ---------------------------------------------------------------- frame
class Frame:
    def __init__(self, t, bg=None):
        self.t = t
        self.img = bg.copy() if bg is not None else np.zeros((H, W, 3), np.float32)
        self.glow = np.zeros((H, W, 3), np.float32)
        self.flash = 0.0
        self.shake = (0.0, 0.0)
        self.zoom = 1.0
        self.ca = 0.0
        self.bloom = 1.0
        self.fade = 1.0          # 整体亮度（转场黑场）

    # ---------------- low-level compositing
    def _roi(self, x0, y0, w, h):
        X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
        if X1 <= X0 or Y1 <= Y0: return None
        return (slice(Y0, Y1), slice(X0, X1)), (slice(Y0 - y0, Y1 - y0), slice(X0 - x0, X1 - x0))

    def over(self, m, x0, y0, col, a=1.0, glow=0.0):
        """mask m 以颜色 col（3-tuple 或与 m 同尺寸的 HxWx3）alpha 叠加在 (x0,y0)"""
        if a <= 0.002: return
        r = self._roi(int(round(x0)), int(round(y0)), m.shape[1], m.shape[0])
        if r is None: return
        (dy, dx), (sy, sx) = r
        mm = m[sy, sx][..., None] * a
        c = col[sy, sx] if isinstance(col, np.ndarray) and col.ndim == 3 and col.shape[0] > 1 else np.asarray(col, np.float32).reshape(1, 1, 3)
        reg = self.img[dy, dx]
        reg *= (1 - mm); reg += mm * c
        if glow > 0:
            self.glow[dy, dx] += mm * c * glow

    def add(self, m, x0, y0, col, a=1.0, glow=0.0):
        if a <= 0.002: return
        r = self._roi(int(round(x0)), int(round(y0)), m.shape[1], m.shape[0])
        if r is None: return
        (dy, dx), (sy, sx) = r
        c = col[sy, sx] if isinstance(col, np.ndarray) and col.ndim == 3 and col.shape[0] > 1 else np.asarray(col, np.float32).reshape(1, 1, 3)
        v = m[sy, sx][..., None] * a * c
        self.img[dy, dx] += v
        if glow > 0:
            self.glow[dy, dx] += v * glow

    def darken(self, m, x0, y0, a=0.5):
        r = self._roi(int(round(x0)), int(round(y0)), m.shape[1], m.shape[0])
        if r is None: return
        (dy, dx), (sy, sx) = r
        self.img[dy, dx] *= (1 - m[sy, sx][..., None] * a)

    # ---------------- text
    def text(self, s, x, y, size, fname='sans', col=INK, a=1.0, anchor='m', track=0.0, glow=0.0,
             grad=None, mode='over', shadow=0.0, scale=1.0, clip=None):
        """y 是文字视觉中心（约为 x-height 中部）；anchor: m/l/r。grad=[(pos,col)] 竖向渐变"""
        if a <= 0.002 or not s: return 0
        if scale != 1.0:
            size = max(4, size * scale)
        size = int(round(size))
        m, base, pad, w = text_mask(s, fname, size, track)
        x0 = x - w / 2 - pad if anchor == 'm' else (x - pad if anchor == 'l' else x - w - pad)
        y0 = y + size * 0.36 - base
        if clip is not None:   # clip=(0..1) 从左到右擦除显现
            m = m.copy(); cut = int(pad + w * cl(clip)); m[:, cut:] = 0
        col_arr = col
        if grad is not None:
            g = vgrad(m.shape[0] - 2 * pad, grad)
            col_arr = np.concatenate([np.repeat(g[:1], pad, 0), g, np.repeat(g[-1:], pad, 0)], 0)
            col_arr = np.repeat(col_arr, m.shape[1], 1)
        if shadow > 0:
            sh = cv2.GaussianBlur(m, (0, 0), max(2, size * 0.08))
            self.darken(sh, x0, y0 + size * 0.05, shadow * a)
        (self.over if mode == 'over' else self.add)(m, x0, y0, col_arr, a, glow)
        return w

    def text_chars(self, s, x, y, size, fname='sans', col=INK, a=1.0, anchor='m', track=0.0, t0=0.0,
                   stag=0.04, dur=0.5, rise=24, glow=0.0, grad=None, blur_in=False, out=None):
        """逐字显现（每个字独立淡入上浮）"""
        if a <= 0.002: return
        f = font(fname, int(size))
        tw = text_w(s, fname, int(size), track)
        xs = x - tw / 2 if anchor == 'm' else (x if anchor == 'l' else x - tw)
        cx = xs
        for i, ch in enumerate(s):
            adv = f.getlength(ch, features=['tnum', 'kern'])
            p = (self.t - t0 - i * stag) / dur
            ai = a * eo(p)
            dy = (1 - eo(p)) * rise
            if out is not None:
                q = (self.t - out[0] - i * stag * 0.5) / out[1]
                ai *= 1 - eio(q); dy -= eio(q) * rise
            if ai > 0.002 and ch.strip():
                self.text(ch, cx, y + dy, size, fname, col, ai, anchor='l', glow=glow, grad=grad)
            cx += adv + track * size

    def text3d(self, s, x, y, size, fname='num', face=None, side=(0.08, 0.10, 0.16), a=1.0, depth=14,
               ang=(0.6, 0.9), glow=0.25, anchor='m', spec=0.0, track=0.0):
        """伪三维挤出文字：沿 ang 方向叠 depth 层暗色侧面，再叠正面渐变与高光"""
        if a <= 0.002: return
        size = int(round(size))
        m, base, pad, w = text_mask(s, fname, size, track)
        x0 = x - w / 2 - pad if anchor == 'm' else (x - pad if anchor == 'l' else x - w - pad)
        y0 = y + size * 0.36 - base
        # 投影
        sh = cv2.GaussianBlur(m, (0, 0), size * 0.06)
        self.darken(sh, x0 + depth * ang[0] * 1.6, y0 + depth * ang[1] * 1.6, 0.6 * a)
        n = max(2, int(depth))
        for k in range(n, 0, -1):
            sc = 0.55 + 0.45 * (1 - k / n)
            self.over(m, x0 + k * ang[0], y0 + k * ang[1], mix(side, sc * 1.4), a)
        face = face or [(0, WHITE), (1, INK)]
        g = vgrad(m.shape[0], [(0, face[0][1]), (pad / m.shape[0], face[0][1]), (1 - pad / m.shape[0], face[-1][1]), (1, face[-1][1])]) \
            if len(face) == 2 else vgrad(m.shape[0], face)
        col = np.repeat(g, m.shape[1], 1)
        if spec > 0:   # 斜向流光
            xx = np.arange(m.shape[1])[None, :] + np.arange(m.shape[0])[:, None] * 0.5
            pos = -0.3 * m.shape[1] + spec * 1.6 * m.shape[1]
            band = np.exp(-((xx - pos) / (size * 0.35)) ** 2)[..., None]
            col = np.clip(col + band * 0.7, 0, 1.4)
        self.over(m, x0, y0, col, a, glow)
        # 顶边细高光
        edge = np.clip(m - np.roll(m, 2, 0), 0, 1) * 0.5
        self.add(edge, x0, y0, WHITE, a * 0.6)
        return w

    # ---------------- shapes (cv2, 4 bit subpixel)
    def _poly_mask(self, pts, closed=True, fill=True, th=2):
        p = np.asarray(pts, np.float64)
        x0, y0 = np.floor(p.min(0) - th - 2).astype(int)
        x1, y1 = np.ceil(p.max(0) + th + 2).astype(int)
        m = np.zeros((y1 - y0, x1 - x0), np.uint8)
        q = ((p - (x0, y0)) * 16).astype(np.int32).reshape(-1, 1, 2)
        if fill:
            cv2.fillPoly(m, [q], 255, cv2.LINE_AA, 4)
        else:
            cv2.polylines(m, [q], closed, 255, max(1, int(round(th))), cv2.LINE_AA, 4)
        return m.astype(np.float32) / 255, x0, y0

    def poly(self, pts, col, a=1.0, th=2, closed=False, glow=0.0, mode='add'):
        if a <= 0.002 or len(pts) < 2: return
        m, x0, y0 = self._poly_mask(pts, closed, False, th)
        (self.add if mode == 'add' else self.over)(m, x0, y0, col, a, glow)

    def fill(self, pts, col, a=1.0, glow=0.0, mode='over'):
        if a <= 0.002 or len(pts) < 3: return
        m, x0, y0 = self._poly_mask(pts, True, True)
        (self.over if mode == 'over' else self.add)(m, x0, y0, col, a, glow)

    def line(self, p0, p1, col, a=1.0, th=2, glow=0.0, mode='add'):
        self.poly([p0, p1], col, a, th, False, glow, mode)

    def circle(self, c, r, col, a=1.0, th=2, glow=0.0, fill=False, mode='add'):
        if a <= 0.002 or r <= 0.3: return
        R = int(r + th + 3)
        m = np.zeros((2 * R + 1, 2 * R + 1), np.uint8)
        cc = (int((R + c[0] % 1) * 16), int((R + c[1] % 1) * 16))
        cv2.circle(m, cc, int(r * 16), 255, -1 if fill else max(1, int(th)), cv2.LINE_AA, 4)
        (self.add if mode == 'add' else self.over)(m.astype(np.float32) / 255, int(c[0]) - R, int(c[1]) - R, col, a, glow)

    def blob(self, c, r, col, a=1.0, target='glow'):
        """高斯光斑（加到 glow 或 img）"""
        if a <= 0.002 or r < 0.5: return
        g = gauss_sprite(int(min(r, 600)))
        R = g.shape[0] // 2
        m = g * a
        if target == 'glow':
            rr = self._roi(int(c[0]) - R, int(c[1]) - R, g.shape[1], g.shape[0])
            if rr is None: return
            (dy, dx), (sy, sx) = rr
            self.glow[dy, dx] += m[sy, sx][..., None] * np.asarray(col, np.float32)
        else:
            self.add(m, int(c[0]) - R, int(c[1]) - R, col, 1.0)

    def rrect_pts(self, x0, y0, x1, y1, r, n=8):
        pts = []
        r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
        for cx, cy, s in ((x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, math.pi / 2), (x0 + r, y0 + r, math.pi)):
            for k in range(n + 1):
                ang = s + k / n * math.pi / 2
                pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        return pts

    # ---------------- glass panel
    def glass(self, x0, y0, x1, y1, r=36, a=1.0, tint=(0.55, 0.7, 1.0), tint_a=0.07, blur=22, edge=None,
              edge_a=0.55, shadow=0.55, spec=None, lift=0.04):
        """毛玻璃卡片：背景模糊 + 提亮 + 着色 + 渐变描边 + 顶部高光 + 投影"""
        if a <= 0.002: return
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        w, h = x1 - x0, y1 - y0
        if w < 4 or h < 4: return
        m, mx, my = self._poly_mask(self.rrect_pts(0, 0, w, h, r), True, True)
        # 投影
        if shadow > 0:
            pad = 60
            sm = np.zeros((h + 2 * pad, w + 2 * pad), np.float32)
            sm[pad:pad + h, pad:pad + w] = 1
            sm = cv2.GaussianBlur(cv2.resize(sm, None, fx=0.25, fy=0.25), (0, 0), 6)
            sm = cv2.resize(sm, (w + 2 * pad, h + 2 * pad))
            self.darken(sm, x0 - pad, y0 - pad + 24, shadow * a)
        rr = self._roi(x0 + mx, y0 + my, m.shape[1], m.shape[0])
        if rr is None: return
        (dy, dx), (sy, sx) = rr
        reg = self.img[dy, dx]
        if blur > 0:
            k = 4
            small = cv2.resize(reg, (max(1, reg.shape[1] // k), max(1, reg.shape[0] // k)), interpolation=cv2.INTER_AREA)
            small = cv2.GaussianBlur(small, (0, 0), blur / k)
            bl = cv2.resize(small, (reg.shape[1], reg.shape[0]), interpolation=cv2.INTER_LINEAR)
        else:
            bl = reg
        mm = m[sy, sx][..., None] * a
        gy = np.linspace(1, 0, m.shape[0], dtype=np.float32)[sy][:, None, None]
        glass_col = bl * 0.85 + np.asarray(tint, np.float32) * tint_a + lift * (0.6 + 0.6 * gy)
        reg *= (1 - mm); reg += mm * glass_col
        # 描边：上亮下暗的渐变
        em, ex, ey = self._poly_mask(self.rrect_pts(0, 0, w, h, r), True, False, 2)
        edge = edge or (0.75, 0.85, 1.0)
        ge = np.linspace(1.0, 0.25, em.shape[0], dtype=np.float32)[:, None]
        self.add(em * ge, x0 + ex, y0 + ey, edge, edge_a * a)
        # 顶部弧形高光
        hl = np.zeros_like(m); hh = max(2, int(h * 0.45))
        hl[:hh] = np.linspace(0.10, 0, hh, dtype=np.float32)[:, None]
        self.add(hl * m, x0 + mx, y0 + my, WHITE, a)
        if spec is not None and 0 < spec < 1:   # 斜向扫光
            xx = np.arange(m.shape[1])[None, :] + np.arange(m.shape[0])[:, None] * 0.7
            pos = -0.4 * w + spec * 1.8 * w
            band = np.exp(-((xx - pos) / 60.0) ** 2) * m * 0.22
            self.add(band, x0 + mx, y0 + my, WHITE, a)

    # ---------------- glass prism (3D block for asset towers)
    def prism(self, cx, base_y, w, h, d, col, a=1.0, glow=0.3, crack=0.0, top_glow=1.0):
        """等轴测玻璃块：正面 w×h，向右上方 d 深度。base_y 为正面底边"""
        if a <= 0.002 or h <= 0.5: return
        dx, dy = d * 0.9, -d * 0.55
        x0, x1 = cx - w / 2, cx + w / 2
        yb, yt = base_y, base_y - h
        front = [(x0, yt), (x1, yt), (x1, yb), (x0, yb)]
        side = [(x1, yt), (x1 + dx, yt + dy), (x1 + dx, yb + dy), (x1, yb)]
        top = [(x0, yt), (x0 + dx, yt + dy), (x1 + dx, yt + dy), (x1, yt)]
        c = np.asarray(col, np.float32)
        # 内部体积感：正面竖向渐变
        m, mx, my = self._poly_mask(front, True, True)
        g = vgrad(m.shape[0], [(0, tuple(c * 0.55)), (1, tuple(c * 0.18))])
        self.over(m, mx, my, np.repeat(g, m.shape[1], 1), 0.78 * a, glow * 0.4)
        self.fill(side, tuple(c * 0.22), 0.8 * a)
        self.fill(top, tuple(np.clip(c * 0.9 + 0.15, 0, 1)), 0.85 * a * top_glow, glow * top_glow)
        # 棱线
        for p, q in [(front[0], front[1]), (front[1], front[2]), (front[0], front[3]), (top[1], top[2]), (top[0], top[1]), (side[1], side[2])]:
            self.line(p, q, tuple(np.clip(c + 0.25, 0, 1)), 0.75 * a, 2, glow)
        self.line(front[3], front[2], tuple(c * 0.6), 0.5 * a, 2)
        # 正面竖向反光条
        rx = x0 + w * 0.18
        self.fill([(rx, yt + 4), (rx + w * 0.07, yt + 4), (rx + w * 0.07, yb - 4), (rx, yb - 4)], WHITE, 0.07 * a, 0, 'add')
        if crack > 0:   # 裂纹（亏损年份）
            rng = np.random.default_rng(int(cx * 7 + base_y))
            for k in range(5):
                px, py = cx + rng.uniform(-w * 0.3, w * 0.3), yt + rng.uniform(0.2, 0.8) * h
                pts = [(px, py)]
                for j in range(4):
                    px += rng.uniform(-w * 0.18, w * 0.18); py += rng.uniform(-h * 0.25, h * 0.25)
                    pts.append((px, py))
                self.poly(pts, DOWN, crack * a * 0.8, 2, glow=0.6)

    # ---------------- glowing chart line
    def glow_line(self, pts, col, a=1.0, th=4, glow=1.2, core=True):
        if a <= 0.002 or len(pts) < 2: return
        self.poly(pts, col, a, th, glow=glow)
        if core:
            self.poly(pts, mix(col, 1.6) if max(col) < 0.7 else lerpc(col, WHITE, 0.55), a * 0.9, max(1, th // 2))

    def area(self, pts, base_y, col, a=0.35):
        """折线下方渐变填充"""
        if a <= 0.002 or len(pts) < 2: return
        poly = list(pts) + [(pts[-1][0], base_y), (pts[0][0], base_y)]
        m, mx, my = self._poly_mask(poly, True, True)
        top = min(p[1] for p in pts)
        yy = (np.arange(m.shape[0]) + my - top) / max(base_y - top, 1)
        fade = np.clip(1 - yy, 0, 1) ** 1.6
        self.add(m * fade[:, None].astype(np.float32), mx, my, col, a)


@lru_cache(64)
def gauss_sprite(r):
    R = int(r * 3)
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
    return np.exp(-(xx * xx + yy * yy) / (2 * r * r))


# ---------------------------------------------------------------- finishing
_VIG = None
def vignette():
    global _VIG
    if _VIG is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
        _VIG = (1 - 0.55 * np.clip(d - 0.35, 0, 1) ** 1.5)[..., None].astype(np.float32)
    return _VIG


_GRAIN = None
def grain(i):
    global _GRAIN
    if _GRAIN is None:
        rng = np.random.default_rng(7)
        _GRAIN = [cv2.resize(cv2.GaussianBlur(rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32), (0, 0), 0.6),
                             (W, H), interpolation=cv2.INTER_LINEAR)[..., None] * 0.012 for _ in range(6)]
    return _GRAIN[i % 6]


def bloom(src, k=1.0):
    s4 = cv2.resize(src, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    b1 = cv2.GaussianBlur(s4, (0, 0), 2.5)
    s16 = cv2.resize(s4, (W // 16, H // 16), interpolation=cv2.INTER_AREA)
    b2 = cv2.GaussianBlur(s16, (0, 0), 3.0)
    b2 = cv2.resize(b2, (W // 4, H // 4), interpolation=cv2.INTER_LINEAR)
    return cv2.resize(b1 * 0.8 + b2 * 1.3, (W, H), interpolation=cv2.INTER_LINEAR) * k


def finish(F, idx=0):
    img = F.img
    out = img + bloom(F.glow, F.bloom)
    if F.flash > 0:
        out += F.flash
    # 柔和高光压缩
    m = out > 0.82
    if m.any():
        out[m] = 0.82 + (1 - np.exp(-(out[m] - 0.82) * 3.2)) * 0.18 / 0.97
    out *= vignette()
    if F.zoom != 1.0 or F.shake != (0.0, 0.0):
        M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, F.zoom)
        M[0, 2] += F.shake[0]; M[1, 2] += F.shake[1]
        out = cv2.warpAffine(out, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if F.ca >= 0.5:
        d = int(round(F.ca))
        out[:, d:, 0] = out[:, :-d, 0].copy(); out[:, :-d, 2] = out[:, d:, 2].copy()
    out += grain(idx)
    out *= F.fade
    return out
