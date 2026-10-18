"""渲染引擎：GLSL（llvmpipe 无头 OpenGL）负责三维与光效，numpy/PIL 负责排版、图表与合成。

帧格式：float32 RGB，0..1（线性近似），尺寸 1080×1920（9:16）。
"""
import math, os, sys
from functools import lru_cache
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
FONT_DIR = os.path.join(ROOT, 'fonts')
sys.path.insert(0, os.path.join(ROOT, '..', 'brand'))  # 仓库根目录 brand/brand.py（官方角标模块）
from brand import Hud, load_logo, GOLD_STOPS, SUB_GOLD, SPEC as BRAND_SPEC   # noqa: E402

# ------------------------------------------------------------------ 调色板
def C(r, g, b): return np.array((r / 255, g / 255, b / 255), np.float32)
INK = C(6, 6, 9)
RED = C(214, 32, 44)          # 可口可乐红（偏电影化的深红）
RED_D = C(120, 10, 18)
GOLD = C(255, 212, 120)       # 品牌金（BRAND GOLD_STOPS 中段）
GOLD_L = C(255, 243, 200)
GOLD_D = C(226, 160, 60)
CREAM = C(244, 236, 220)
WHITE = C(255, 255, 255)
GREY = C(150, 150, 160)
DIM = C(95, 95, 105)
TEAL = C(90, 200, 210)
BLUE = C(110, 175, 255)
GREEN = C(120, 220, 150)
SEPIA = C(196, 160, 112)

# ------------------------------------------------------------------ 缓动
def cl(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def eo(x): x = cl(x); return 1 - (1 - x) ** 3
def ei(x): x = cl(x); return x ** 3
def eio(x): x = cl(x); return x * x * (3 - 2 * x)
def eio5(x): x = cl(x); return x * x * x * (x * (6 * x - 15) + 10)
def eexp(x): x = cl(x); return 1 - 2 ** (-10 * x) if x < 1 else 1.0
def eback(x, s=1.5): x = cl(x) - 1; return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, x): return a + (b - a) * x
def env(t, a, b, fi=0.4, fo=0.4):
    """在 [a,b] 内为 1，两端渐入渐出"""
    if t < a or t > b: return 0.0
    i = eio((t - a) / fi) if fi > 0 else 1.0
    o = eio((b - t) / fo) if fo > 0 else 1.0
    return min(i, o)
def prog(t, a, b): return cl((t - a) / max(b - a, 1e-6))


# ------------------------------------------------------------------ GL
_ctx = None
def gl():
    global _ctx
    if _ctx is None:
        import moderngl
        _ctx = moderngl.create_standalone_context(backend='egl')
    return _ctx


GLSL_HEAD = """#version 330
uniform vec2 res; uniform float t;
in vec2 uv; out vec4 o;
float hash(vec2 p){ p=fract(p*vec2(123.34,456.21)); p+=dot(p,p+45.32); return fract(p.x*p.y); }
float hash3(vec3 p){ return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453); }
float vnoise(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f);
  return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y); }
float fbm(vec2 p){ float a=.5,s=0.; for(int i=0;i<5;i++){ s+=a*vnoise(p); p=p*2.03+vec2(1.7,9.2); a*=.5;} return s; }
"""


class Shader:
    """全屏片元着色器 → numpy (h,w,4) float32"""
    _vs = """#version 330
in vec2 p; out vec2 uv; void main(){ uv=p*.5+.5; gl_Position=vec4(p,0,1); }"""

    def __init__(self, frag, size=(W, H)):
        import moderngl
        ctx = gl()
        self.prog = ctx.program(vertex_shader=self._vs, fragment_shader=GLSL_HEAD + frag)
        vbo = ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], 'f4'))
        self.vao = ctx.vertex_array(self.prog, [(vbo, '2f', 'p')])
        self.size = size
        self.tex = ctx.texture(size, 4, dtype='f4')
        self.fbo = ctx.framebuffer(color_attachments=[self.tex])
        self.textures = {}

    def set_texture(self, name, arr, unit):
        """arr: (h,w,c) float32 → sampler2D"""
        ctx = gl()
        h, w = arr.shape[:2]; c = arr.shape[2] if arr.ndim == 3 else 1
        key = name
        tex = self.textures.get(key)
        if tex is None or tex.size != (w, h) or tex.components != c:
            tex = ctx.texture((w, h), c, dtype='f4'); tex.repeat_x = tex.repeat_y = False
            self.textures[key] = tex
        tex.write(np.ascontiguousarray(arr[::-1], np.float32).tobytes())
        tex.use(unit)
        if name in self.prog: self.prog[name].value = unit

    def __call__(self, **u):
        import moderngl
        self.fbo.use()
        if 'res' in self.prog: self.prog['res'].value = self.size
        for k, v in u.items():
            if k in self.prog:
                self.prog[k].value = tuple(v) if isinstance(v, (list, tuple, np.ndarray)) else v
        self.vao.render(moderngl.TRIANGLE_STRIP)
        a = np.frombuffer(self.fbo.read(components=4, dtype='f4'), np.float32)
        return a.reshape(self.size[1], self.size[0], 4)[::-1]


# ------------------------------------------------------------------ 文字
FONTS = {k: os.path.join(FONT_DIR, k + '.ttf') for k in
         ['serif_reg', 'serif_semi', 'serif_black', 'sans_light', 'sans_med', 'sans_bold', 'sans_black',
          'corm', 'corm_med', 'mono', 'typewriter', 'oswald', 'playfair']}


@lru_cache(128)
def font(name, size): return ImageFont.truetype(FONTS[name], int(size))


@lru_cache(4096)
def text_mask(s, fnt, size, track=0.0):
    """整行文字 → (mask float32, 基线偏移)。track = 字距（相对字号）"""
    f = font(fnt, size)
    asc, desc = f.getmetrics()
    adv = [f.getlength(c) for c in s]
    w = int(sum(adv) + track * size * max(len(s) - 1, 0) + size * 0.6) + 4
    h = int((asc + desc) * 1.25) + 4
    im = Image.new('L', (w, h), 0); d = ImageDraw.Draw(im)
    x = size * 0.3
    for c, a in zip(s, adv):
        d.text((x, asc + 2), c, font=f, fill=255, anchor='ls'); x += a + track * size
    m = np.asarray(im, np.float32) / 255
    ys, xs = np.nonzero(m > 0.003)
    if len(xs) == 0: return np.zeros((1, 1), np.float32), 0, 0, 0
    x0, x1 = xs.min(), xs.max() + 1
    # 保留统一的上下边界（按字体度量），只裁左右，保证不同文字基线一致
    return m[:, x0:x1], asc + 2, x1 - x0, h


def text_size(s, fnt, size, track=0.0):
    m, base, w, h = text_mask(s, fnt, size, track)
    return w, h


def grad_rgb(h, stops):
    y = np.linspace(0, 1, h)
    return np.stack([np.interp(y, [s[0] for s in stops], [s[1][c] / 255 for s in stops]) for c in range(3)], 1).astype(np.float32)


# ------------------------------------------------------------------ 画布
class Canvas:
    """一帧画面。img: 底图（线性 RGB）；glow: 需要辉光的加色层"""

    def __init__(self, t, bg=None):
        self.t = t
        self.img = np.zeros((H, W, 3), np.float32) if bg is None else bg.astype(np.float32, copy=True)
        self.glow = np.zeros((H, W, 3), np.float32)
        self.U = np.zeros((H, W, 3), np.uint8)      # cv2 抗锯齿线条（加色，带辉光）
        self.post = []                              # 最后叠加（不进辉光、不受暗角）的元素

    # -------------------------------------------- 基础合成
    def over(self, rgb, a, x0, y0):
        """alpha 合成 rgb(h,w,3 或 3) + a(h,w) 到 (x0,y0)"""
        h, w = a.shape
        X0, Y0 = max(int(x0), 0), max(int(y0), 0)
        X1, Y1 = min(int(x0) + w, W), min(int(y0) + h, H)
        if X1 <= X0 or Y1 <= Y0: return
        sa = a[Y0 - int(y0):Y1 - int(y0), X0 - int(x0):X1 - int(x0)][..., None]
        reg = self.img[Y0:Y1, X0:X1]
        if np.ndim(rgb) == 1:
            reg *= 1 - sa; reg += sa * rgb
        else:
            src = rgb[Y0 - int(y0):Y1 - int(y0), X0 - int(x0):X1 - int(x0)]
            reg *= 1 - sa; reg += sa * src

    def add(self, rgb, a, x0, y0, glow=0.0):
        h, w = a.shape
        X0, Y0 = max(int(x0), 0), max(int(y0), 0)
        X1, Y1 = min(int(x0) + w, W), min(int(y0) + h, H)
        if X1 <= X0 or Y1 <= Y0: return
        sa = a[Y0 - int(y0):Y1 - int(y0), X0 - int(x0):X1 - int(x0)][..., None]
        col = rgb if np.ndim(rgb) == 1 else rgb[Y0 - int(y0):Y1 - int(y0), X0 - int(x0):X1 - int(x0)]
        self.img[Y0:Y1, X0:X1] += sa * col
        if glow: self.glow[Y0:Y1, X0:X1] += sa * col * glow

    def dim(self, k):
        self.img *= k

    def fill(self, col, a=1.0):
        self.img = self.img * (1 - a) + np.asarray(col, np.float32) * a

    # -------------------------------------------- 文字
    def text(self, s, x, y, size, fnt='sans_med', col=WHITE, a=1.0, anchor='m', track=0.0, glow=0.0,
             gold=False, shadow=0.0, mode='over', reveal=None, blur=0.0, scale=1.0):
        """y = 文字视觉中心；anchor m/l/r；gold=True 用品牌金色竖向渐变；
        reveal=(0..1) 从左到右擦除显现；blur>0 做柔焦入场"""
        if a <= 0.004 or not s: return 0
        m, base, w, h = text_mask(s, fnt, int(size * scale) if scale != 1 else int(size), track)
        if reveal is not None:
            r = cl(reveal)
            if r <= 0: return w
            xs = np.arange(m.shape[1], dtype=np.float32)
            edge = r * (m.shape[1] + 40) - 20
            m = m * np.clip((edge - xs) / 20, 0, 1)[None, :]
        if blur > 0.3: m = cv2.GaussianBlur(m, (0, 0), blur)
        fsz = int(size * scale) if scale != 1 else int(size)
        ascn, descn = font(fnt, fsz).getmetrics()
        yc = base - ascn * 0.40                              # 文字视觉中心（中日韩字形近似）
        x0 = x - w / 2 if anchor == 'm' else (x if anchor == 'l' else x - w)
        y0 = y - yc
        if gold:
            g = grad_rgb(m.shape[0], GOLD_STOPS)
            ys, = np.nonzero(m.max(1) > 0.01)
            if len(ys):
                gg = grad_rgb(ys[-1] - ys[0] + 1, GOLD_STOPS)
                g[ys[0]:ys[-1] + 1] = gg; g[:ys[0]] = gg[0]; g[ys[-1] + 1:] = gg[-1]
            col_img = np.repeat(g[:, None, :], m.shape[1], 1)
        else:
            col_img = np.asarray(col, np.float32)
        if shadow > 0:
            sh = cv2.GaussianBlur(m, (0, 0), max(size * 0.08, 2)) * shadow * a
            self.img_mul(1 - sh, x0 + size * 0.03, y0 + size * 0.05)
        if mode == 'add':
            self.add(col_img, m * a, x0, y0, glow)
        else:
            self.over(col_img, m * a, x0, y0)
            if glow: self.add(col_img, m * a * 0, x0, y0); self._glow(col_img, m * a * glow, x0, y0)
        return w

    def _glow(self, rgb, a, x0, y0):
        h, w = a.shape
        X0, Y0 = max(int(x0), 0), max(int(y0), 0)
        X1, Y1 = min(int(x0) + w, W), min(int(y0) + h, H)
        if X1 <= X0 or Y1 <= Y0: return
        sa = a[Y0 - int(y0):Y1 - int(y0), X0 - int(x0):X1 - int(x0)][..., None]
        col = rgb if np.ndim(rgb) == 1 else rgb[Y0 - int(y0):Y1 - int(y0), X0 - int(x0):X1 - int(x0)]
        self.glow[Y0:Y1, X0:X1] += sa * col

    def img_mul(self, k, x0, y0):
        h, w = k.shape
        X0, Y0 = max(int(x0), 0), max(int(y0), 0)
        X1, Y1 = min(int(x0) + w, W), min(int(y0) + h, H)
        if X1 <= X0 or Y1 <= Y0: return
        self.img[Y0:Y1, X0:X1] *= k[Y0 - int(y0):Y1 - int(y0), X0 - int(x0):X1 - int(x0)][..., None]

    def paragraph(self, lines, x, y, size, lh=1.5, **kw):
        n = len(lines)
        for i, s in enumerate(lines):
            self.text(s, x, y + (i - (n - 1) / 2) * size * lh, size, **kw)

    # -------------------------------------------- 线条 / 形状（cv2，亚像素抗锯齿）
    def _c(self, col, a): return tuple(float(cl(c * a) * 255) for c in col)

    def line(self, p0, p1, col, a=1.0, th=2):
        if a <= 0.004: return
        cv2.line(self.U, (int(p0[0] * 16), int(p0[1] * 16)), (int(p1[0] * 16), int(p1[1] * 16)),
                 self._c(col, a), th, cv2.LINE_AA, 4)

    def poly(self, pts, col, a=1.0, th=2, closed=False):
        if a <= 0.004 or len(pts) < 2: return
        p = (np.asarray(pts, np.float64) * 16).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(self.U, [p], closed, self._c(col, a), th, cv2.LINE_AA, 4)

    def circle(self, c, r, col, a=1.0, th=2):
        if a <= 0.004 or r <= 0: return
        cv2.circle(self.U, (int(c[0] * 16), int(c[1] * 16)), int(r * 16), self._c(col, a), th, cv2.LINE_AA, 4)

    def arc(self, c, r, a0, a1, col, a=1.0, th=2, n=96):
        ts = np.linspace(a0, a1, n)
        self.poly(np.stack([c[0] + r * np.cos(ts), c[1] + r * np.sin(ts)], 1), col, a, th)

    def fillpoly(self, pts, col, a=1.0, glow=0.0):
        if a <= 0.004: return
        p = (np.asarray(pts, np.float64) * 16).astype(np.int32).reshape(-1, 1, 2)
        x0, y0 = np.clip(p[:, 0, :].min(0) // 16 - 2, 0, None)
        x1, y1 = min(p[:, 0, 0].max() // 16 + 3, W), min(p[:, 0, 1].max() // 16 + 3, H)
        if x1 <= x0 or y1 <= y0: return
        m = np.zeros((y1 - y0, x1 - x0), np.uint8)
        q = p.copy(); q[:, 0, 0] -= x0 * 16; q[:, 0, 1] -= y0 * 16
        cv2.fillPoly(m, [q], 255, cv2.LINE_AA, 4)
        self.over(np.asarray(col, np.float32), m.astype(np.float32) / 255 * a, x0, y0)
        if glow: self._glow(np.asarray(col, np.float32), m.astype(np.float32) / 255 * a * glow, x0, y0)

    def rect(self, x0, y0, x1, y1, col, a=1.0, glow=0.0):
        self.fillpoly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], col, a, glow)

    def rrect(self, x0, y0, x1, y1, r, col, a=1.0, fill=True, th=2, glow=0.0):
        pts = []
        for cx, cy, s in ((x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, math.pi / 2), (x0 + r, y0 + r, math.pi)):
            for k in range(10):
                ang = s + k / 9 * math.pi / 2
                pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        if fill: self.fillpoly(pts, col, a, glow)
        else: self.poly(pts, col, a, th, closed=True)

    def glow_dot(self, c, r, col, a=1.0):
        """柔和光斑（加到 glow 层与底图）"""
        if a <= 0.004 or r <= 0.5: return
        R = int(r * 3)
        X0, Y0 = max(int(c[0]) - R, 0), max(int(c[1]) - R, 0)
        X1, Y1 = min(int(c[0]) + R + 1, W), min(int(c[1]) + R + 1, H)
        if X1 <= X0 or Y1 <= Y0: return
        yy, xx = np.mgrid[Y0:Y1, X0:X1].astype(np.float32)
        g = np.exp(-((xx - c[0]) ** 2 + (yy - c[1]) ** 2) / (2 * r * r)) * a
        self.img[Y0:Y1, X0:X1] += g[..., None] * np.asarray(col, np.float32) * 0.5
        self.glow[Y0:Y1, X0:X1] += g[..., None] * np.asarray(col, np.float32)

    def splat(self, xs, ys, col, a, glow=1.0):
        """点粒子（亚像素双线性分布）"""
        xs = np.asarray(xs, np.float32); ys = np.asarray(ys, np.float32)
        a = np.broadcast_to(np.asarray(a, np.float32), xs.shape)
        cols = np.asarray(col, np.float32)
        if cols.ndim == 1: cols = np.broadcast_to(cols, (len(xs), 3))
        x0 = np.floor(xs).astype(np.int64); y0 = np.floor(ys).astype(np.int64)
        fx = xs - x0; fy = ys - y0
        for dx, dy, wgt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            xi = x0 + dx; yi = y0 + dy
            ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
            idx = yi[ok] * W + xi[ok]
            v = cols[ok] * (a[ok] * wgt[ok])[:, None]
            np.add.at(self.img.reshape(-1, 3), idx, v)
            if glow: np.add.at(self.glow.reshape(-1, 3), idx, v * glow)

    # -------------------------------------------- 图片
    def image(self, rgb, x, y, w, h=None, a=1.0, alpha=None, anchor='m'):
        """把 rgb (任意尺寸) 缩放到宽 w 贴到 (x,y)；返回实际高度"""
        ih, iw = rgb.shape[:2]
        if h is None: h = w * ih / iw
        w, h = int(round(w)), int(round(h))
        if w < 2 or h < 2: return h
        im = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA if w < iw else cv2.INTER_CUBIC)
        al = np.ones((h, w), np.float32) if alpha is None else cv2.resize(alpha, (w, h))
        x0 = x - w / 2 if anchor == 'm' else x; y0 = y - h / 2 if anchor == 'm' else y
        self.over(im, al * a, x0, y0)
        return h


# ------------------------------------------------------------------ 后期
_grain = None
def _grain_tiles():
    global _grain
    if _grain is None:
        rng = np.random.default_rng(7)
        _grain = [cv2.GaussianBlur(rng.standard_normal((H // 2, W // 2)).astype(np.float32), (0, 0), 0.6) for _ in range(8)]
    return _grain


_vig = None
def vignette():
    global _vig
    if _vig is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = ((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.47) / (H * 0.62)) ** 2
        _vig = (1 - 0.55 * np.clip(d, 0, 1.6) ** 1.4).clip(0.25, 1)[..., None].astype(np.float32)
    return _vig


def bloom(src, k=1.0):
    s2 = cv2.resize(src, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    s8 = cv2.resize(s2, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
    s32 = cv2.resize(s8, (W // 32, H // 32), interpolation=cv2.INTER_AREA)
    b = cv2.resize(cv2.GaussianBlur(s2, (0, 0), 3), (W, H)) * 0.35 \
        + cv2.resize(cv2.GaussianBlur(s8, (0, 0), 3), (W, H)) * 0.45 \
        + cv2.resize(cv2.GaussianBlur(s32, (0, 0), 2.5), (W, H)) * 0.35
    return b * k


HUD = None
def finish(cv, frame_idx, bloom_k=1.0, grain=0.018, vig=True, hud_alpha=1.0, fade=1.0, post=None):
    """合成：线条层 + 辉光 + 色调映射 + 暗角 + 颗粒 + 品牌角标 → uint8"""
    global HUD
    img = cv.img
    if cv.U.any():
        u = cv.U.astype(np.float32) / 255
        img += u; cv.glow += u * 0.8
    if bloom_k > 0 and cv.glow.any():
        img = img + bloom(cv.glow, bloom_k)
    # 柔肩色调映射：高光不硬切
    img = np.where(img > 0.82, 0.82 + 0.18 * (1 - np.exp(-(img - 0.82) / 0.18)), img)
    if vig: img = img * vignette()
    if grain > 0:
        g = _grain_tiles()[frame_idx % 8]
        g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)
        lum = img.mean(2, keepdims=True)
        img = img + g[..., None] * grain * (0.35 + 0.65 * np.sqrt(np.clip(lum, 0, 1)))
    if post is not None: post(img)
    img *= fade
    if HUD is None: HUD = Hud(scale=1.0, frame_w=W)
    HUD.draw(img, frame_idx / FPS, alpha=hud_alpha * fade)
    return (np.clip(np.nan_to_num(img), 0, 1) * 255 + 0.5).astype(np.uint8)
