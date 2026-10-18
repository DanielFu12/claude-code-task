"""小型电影级动态图形引擎（numpy + numba + OpenCV + Pillow），竖屏 1080×1920。

- 3D 相机 + 粒子点精灵（按深度做景深/大小）
- 解析光线追踪的玻璃方块（菲涅尔反射、程序化环境光、边缘高光、厚度吸收、背景折射）
- 文字图层缓存、逐字显现、辉光
- 后期：多尺度辉光、暗角、色差、颗粒、色调映射
"""
import math, os
from functools import lru_cache
import numpy as np, cv2
from numba import njit, prange
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
FONT_DIR = os.path.join(ROOT, 'fonts')

# ------------------------------------------------------------------ 颜色
def hexc(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255

GOLD = hexc('#FFD478'); GOLD_HI = hexc('#FFF3C8'); GOLD_DEEP = hexc('#E2A03C'); GOLD_SUB = hexc('#D6B270')
CYAN = hexc('#5CC8FF'); BLUE = hexc('#3D7BFF'); RED = hexc('#FF5A48'); TEAL = hexc('#3FE0C5'); GREEN = hexc('#7BE38A')
WHITE = np.ones(3, np.float32); INK = hexc('#05070D'); GREY = hexc('#8A93A6')


# ------------------------------------------------------------------ 缓动
def clamp01(x): return min(max(x, 0.0), 1.0)
def smooth(x): x = clamp01(x); return x * x * (3 - 2 * x)
def ease_out(x): x = clamp01(x); return 1 - (1 - x) ** 3
def ease_in(x): x = clamp01(x); return x ** 3
def ease_io(x): x = clamp01(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def ease_back(x, s=1.4): x = clamp01(x) - 1; return 1 + (s + 1) * x ** 3 + s * x ** 2
def win(t, a, b, fi=0.4, fo=0.4):
    """在 [a,b] 内为 1，前后各 fi/fo 秒淡入淡出"""
    if t < a or t > b: return 0.0
    return min(smooth((t - a) / fi) if fi > 0 else 1, smooth((b - t) / fo) if fo > 0 else 1)
def lerp(a, b, u): return a + (b - a) * u


# ------------------------------------------------------------------ 字体 / 文字
FONTS = {'serif': 'serif_black.ttf', 'serif_m': 'serif_med.ttf', 'serif_l': 'serif_light.ttf',
         'sans': 'sans_med.ttf', 'sans_l': 'sans_light.ttf', 'sans_b': 'sans_bold.ttf',
         'corm': 'corm.ttf', 'corm_sb': 'corm_sb.ttf', 'mono': 'mono.ttf'}

@lru_cache(None)
def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, FONTS[name]), int(size))


@lru_cache(None)
def _cmap(name):
    from fontTools.ttLib import TTFont
    return set(TTFont(os.path.join(FONT_DIR, FONTS[name])).getBestCmap())


def _fallback(ch, name):
    if ord(ch) in _cmap(name): return name
    for alt in ('corm_sb', 'mono', 'sans'):
        if ord(ch) in _cmap(alt): return alt
    return name


@lru_cache(4096)
def glyph(ch, name, size):
    """单字符 alpha 图 + 前进宽度 + 基线偏移（缺字时自动回退字体）"""
    name = _fallback(ch, name)
    f = font(name, size)
    asc, desc = f.getmetrics()
    w = max(int(f.getlength(ch)) + 4, 1)
    im = Image.new('L', (w + size // 2, asc + desc + 8), 0)
    ImageDraw.Draw(im).text((2, 4), ch, font=f, fill=255)
    return np.asarray(im, np.float32) / 255, f.getlength(ch), asc


def adv(c, name, size):
    return font(_fallback(c, name), size).getlength(c)


def wrap(text, name, size, maxw):
    """按像素宽度换行；中文逐字可断，英文按词断"""
    f = font(name, size)
    lines, cur = [], ''
    tokens = []
    buf = ''
    for ch in text:
        if ch == '\n':
            if buf: tokens.append(buf); buf = ''
            tokens.append('\n'); continue
        if ord(ch) < 0x2E80 and ch not in '，。、；：？！“”（）《》':
            buf += ch
            if ch == ' ': tokens.append(buf); buf = ''
        else:
            if buf: tokens.append(buf); buf = ''
            tokens.append(ch)
    if buf: tokens.append(buf)
    for tok in tokens:
        if tok == '\n': lines.append(cur.rstrip()); cur = ''; continue
        if f.getlength(cur + tok) <= maxw or not cur:
            cur += tok
        else:
            if tok in '，。、；：？！”）》"' and f.getlength(cur + tok) <= maxw + size * 1.8:   # 标点不放行首
                cur += tok; continue
            lines.append(cur.rstrip()); cur = tok.lstrip()
    if cur: lines.append(cur.rstrip())
    return lines


class TextBlock:
    """排好版的一段文字：逐字位置，可以做逐字动画"""
    def __init__(self, text, name='sans', size=44, maxw=900, align='center', lh=1.45, track=0):
        size = int(round(size))
        self.size = size
        self.lines = wrap(text, name, size, maxw)
        f = font(name, size)
        self.chars = []   # (ch, x, y)
        y = 0
        self.w = 0
        for ln in self.lines:
            lw = sum(adv(c, name, size) + track for c in ln) - track
            x0 = {'center': -lw / 2, 'left': 0, 'right': -lw}[align]
            x = x0
            for c in ln:
                self.chars.append((c, x, y)); x += adv(c, name, size) + track
            self.w = max(self.w, lw)
            y += size * lh
        self.h = y - size * (lh - 1)
        self.name = name

    def render(self, cx, cy, reveal=1.0, mode='fade', stagger=0.6, rise=18, pad=None):
        """返回局部 mask 及其左上角 (x0, y0)；只在文字包围盒内计算"""
        n = len(self.chars)
        pad = int(self.size * 0.8) if pad is None else pad
        x0 = int(cx + min((c[1] for c in self.chars), default=0)) - pad
        x1 = int(cx + max((c[1] + self.size * 1.1 for c in self.chars), default=0)) + pad
        y0 = int(cy - self.h / 2) - pad - 8
        y1 = int(cy + self.h / 2) + pad + rise + 8
        mask = np.zeros((max(y1 - y0, 1), max(x1 - x0, 1)), np.float32)
        for i, (c, x, y) in enumerate(self.chars):
            if c == ' ': continue
            if mode == 'type':
                u = clamp01(reveal * (n + 2) - i)
                a = u
            else:
                u = clamp01((reveal * (1 + stagger) - stagger * i / max(n - 1, 1)))
                a = smooth(u)
            if u <= 0: continue
            g, adv, asc = glyph(c, self.name, self.size)
            dy = (1 - ease_out(u)) * rise if mode == 'fade' else 0
            px, py = int(round(cx + x - 2)) - x0, int(round(cy + y - 4 + dy - self.h / 2)) - y0
            blit_max(mask, g * a, px, py)
        return mask, x0, y0

    def draw(self, layer, cx, cy, color, alpha=1.0, reveal=1.0, mode='fade', glow=0.0, stagger=0.6, rise=18, t=0.0):
        """兼容接口：返回全帧 mask，并在 layer 上加辉光"""
        if len(self.chars) == 0 or alpha <= 0: return None
        m, x0, y0 = self.render(cx, cy, reveal, mode, stagger, rise)
        full = np.zeros(layer.shape[:2], np.float32)
        paste(full, m * alpha, x0, y0)
        if glow > 0:
            gl = cv2.GaussianBlur(full, (0, 0), self.size * 0.35)
            layer += gl[..., None] * (np.asarray(color) * glow)
        return full


def paste(dst, src, x, y):
    h, w = src.shape[:2]
    H_, W_ = dst.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W_), min(y + h, H_)
    if x1 <= x0 or y1 <= y0: return
    dst[y0:y1, x0:x1] = src[y0 - y:y1 - y, x0 - x:x1 - x]


def blit_max(dst, src, x, y):
    h, w = src.shape
    H_, W_ = dst.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W_), min(y + h, H_)
    if x1 <= x0 or y1 <= y0: return
    d = dst[y0:y1, x0:x1]
    np.maximum(d, src[y0 - y:y1 - y, x0 - x:x1 - x], out=d)


def comp_mask(frame, mask, color, alpha=1.0):
    """把 mask 用颜色 over 合成到 frame（color 可以是 3 向量或 H×W×3 图）"""
    a = (mask * alpha)[..., None]
    frame *= (1 - a)
    frame += a * color


def gold_fill(h, top=None):
    """品牌金色竖向渐变（取自 brand.GOLD_STOPS）"""
    import brand_bridge
    return brand_bridge.gold_ramp(h)


# ------------------------------------------------------------------ 3D 相机
class Camera:
    def __init__(self, pos, target, fov=50.0, roll=0.0):
        self.pos = np.asarray(pos, np.float32); self.target = np.asarray(target, np.float32)
        self.fov = fov
        f = self.target - self.pos; f /= np.linalg.norm(f)
        up = np.array([math.sin(roll), math.cos(roll), 0], np.float32)
        r = np.cross(up, f); r /= np.linalg.norm(r)
        u = np.cross(f, r)
        self.R = np.stack([r, u, f]).astype(np.float32)   # 世界→相机
        self.focal = 0.5 * H / math.tan(math.radians(fov) / 2)

    def project(self, P):
        """P: N×3 → (x, y, z_cam)"""
        Q = (P - self.pos) @ self.R.T
        z = np.maximum(Q[:, 2], 1e-3)
        return W / 2 + Q[:, 0] / z * self.focal, H / 2 - Q[:, 1] / z * self.focal, Q[:, 2]

    def rays(self, scale=1.0):
        """每像素光线方向（相机坐标→世界），返回 (h,w,3)"""
        w, h = int(W * scale), int(H * scale)
        xs = (np.arange(w) + 0.5) / scale - W / 2
        ys = H / 2 - (np.arange(h) + 0.5) / scale
        d = np.empty((h, w, 3), np.float32)
        d[..., 0] = xs[None, :]; d[..., 1] = ys[:, None]; d[..., 2] = self.focal
        d /= np.linalg.norm(d, axis=2, keepdims=True)
        return d @ self.R


# ------------------------------------------------------------------ 粒子
@njit(cache=True)
def _splat(buf, xs, ys, rs, cr, cg, cb, al):
    H_, W_ = buf.shape[0], buf.shape[1]
    for i in range(xs.shape[0]):
        r = rs[i]
        if r <= 0 or al[i] <= 0.002: continue
        x, y = xs[i], ys[i]
        R = int(r * 2.6) + 1
        xi, yi = int(x), int(y)
        if xi + R < 0 or xi - R >= W_ or yi + R < 0 or yi - R >= H_: continue
        inv = 1.0 / (r * r)
        # 面积守恒：大半径（失焦）时亮度降低
        peak = al[i] * min(1.0, 1.2 / r)
        for yy in range(max(yi - R, 0), min(yi + R + 1, H_)):
            dy = yy + 0.5 - y
            for xx in range(max(xi - R, 0), min(xi + R + 1, W_)):
                dx = xx + 0.5 - x
                g = math.exp(-(dx * dx + dy * dy) * inv) * peak
                if g > 0.003:
                    buf[yy, xx, 0] += g * cr[i]; buf[yy, xx, 1] += g * cg[i]; buf[yy, xx, 2] += g * cb[i]


def splat(buf, xs, ys, rs, cols, al):
    cols = np.asarray(cols, np.float32)
    if cols.ndim == 1: cols = np.broadcast_to(cols, (len(xs), 3))
    _splat(buf, xs.astype(np.float32), ys.astype(np.float32), rs.astype(np.float32),
           np.ascontiguousarray(cols[:, 0]), np.ascontiguousarray(cols[:, 1]), np.ascontiguousarray(cols[:, 2]),
           np.broadcast_to(np.asarray(al, np.float32), (len(xs),)).astype(np.float32))


def particles3d(buf, cam, P, cols, size=2.0, alpha=1.0, focus=None, dof=0.0, near=0.5):
    """3D 点 → 屏幕 splat，size 为世界尺寸（会按距离缩放），dof 景深强度"""
    x, y, z = cam.project(P)
    ok = z > near
    x, y, z = x[ok], y[ok], z[ok]
    cols = np.asarray(cols, np.float32)
    if cols.ndim == 2: cols = cols[ok]
    al = np.broadcast_to(np.asarray(alpha, np.float32), ok.shape)[ok] if np.ndim(alpha) else np.full(len(x), alpha, np.float32)
    r = np.asarray(size, np.float32)
    r = (r[ok] if r.ndim else r) * cam.focal / z
    if focus is not None and dof > 0:
        r = np.sqrt(r ** 2 + (dof * np.abs(1 / z - 1 / focus) * cam.focal) ** 2)
    r = np.clip(r, 0.6, 48)
    al = al * np.clip(1.6 - z / 120, 0, 1)   # 远处渐隐
    big = r > 3.5
    if (~big).any():
        splat(buf, x[~big], y[~big], r[~big], cols[~big] if cols.ndim == 2 else cols, al[~big])
    if big.any():   # 失焦的大光斑在 1/4 分辨率上画，再放大
        q = np.zeros((H // 4, W // 4, 3), np.float32)
        splat(q, x[big] / 4, y[big] / 4, r[big] / 4, cols[big] if cols.ndim == 2 else cols, al[big] * 0.55)
        buf += cv2.resize(q, (W, H), interpolation=cv2.INTER_LINEAR)


# ------------------------------------------------------------------ 玻璃方块（解析光追）
# box 数组：每行 [cx,cy,cz, hx,hy,hz, R00..R22(9), r,g,b(染色), density, edge, opacity]
BOX_FIELDS = 21

@njit(cache=True, parallel=True)
def _boxes(dirs, org, boxes, bb, out_add, out_cov, out_off, light_dir, t_env):
    h, w = dirs.shape[0], dirs.shape[1]
    nb = boxes.shape[0]
    for j in prange(h):
        ts = np.empty(16, np.float32); idx = np.empty(16, np.int64)
        tfs = np.empty(16, np.float32)
        nxs = np.empty((16, 3), np.float32)
        for i in range(w):
            dx, dy, dz = dirs[j, i, 0], dirs[j, i, 1], dirs[j, i, 2]
            nh = 0
            for b in range(nb):
                if i < bb[b, 0] or i > bb[b, 2] or j < bb[b, 1] or j > bb[b, 3]: continue
                # 世界 → 盒子局部
                ox = org[0] - boxes[b, 0]; oy = org[1] - boxes[b, 1]; oz = org[2] - boxes[b, 2]
                lox = boxes[b, 6] * ox + boxes[b, 7] * oy + boxes[b, 8] * oz
                loy = boxes[b, 9] * ox + boxes[b, 10] * oy + boxes[b, 11] * oz
                loz = boxes[b, 12] * ox + boxes[b, 13] * oy + boxes[b, 14] * oz
                ldx = boxes[b, 6] * dx + boxes[b, 7] * dy + boxes[b, 8] * dz
                ldy = boxes[b, 9] * dx + boxes[b, 10] * dy + boxes[b, 11] * dz
                ldz = boxes[b, 12] * dx + boxes[b, 13] * dy + boxes[b, 14] * dz
                tn = -1e9; tf = 1e9; ax = 0; sg = 1.0
                ok = True
                for a in range(3):
                    o = lox if a == 0 else (loy if a == 1 else loz)
                    d = ldx if a == 0 else (ldy if a == 1 else ldz)
                    hs = boxes[b, 3 + a]
                    if abs(d) < 1e-8:
                        if o < -hs or o > hs: ok = False; break
                        continue
                    t1 = (-hs - o) / d; t2 = (hs - o) / d
                    s = -1.0
                    if t1 > t2: t1, t2 = t2, t1; s = 1.0
                    if t1 > tn: tn = t1; ax = a; sg = s
                    if t2 < tf: tf = t2
                    if tn > tf: ok = False; break
                if not ok or tf <= 0.0 or tn <= 0.0: continue
                if nh < 16:
                    ts[nh] = tn; tfs[nh] = tf; idx[nh] = b
                    # 局部法线
                    nxs[nh, 0] = sg if ax == 0 else 0.0
                    nxs[nh, 1] = sg if ax == 1 else 0.0
                    nxs[nh, 2] = sg if ax == 2 else 0.0
                    nh += 1
            if nh == 0: continue
            # 按距离排序（插入排序）
            for a in range(1, nh):
                k = a
                while k > 0 and ts[k - 1] > ts[k]:
                    ts[k - 1], ts[k] = ts[k], ts[k - 1]; tfs[k - 1], tfs[k] = tfs[k], tfs[k - 1]
                    idx[k - 1], idx[k] = idx[k], idx[k - 1]
                    for q in range(3):
                        tmp = nxs[k - 1, q]; nxs[k - 1, q] = nxs[k, q]; nxs[k, q] = tmp
                    k -= 1
            T = 1.0; ar = 0.0; ag = 0.0; ab = 0.0; ox_ = 0.0; oy_ = 0.0
            for q in range(nh):
                b = idx[q]
                tn = ts[q]; tf = tfs[q]
                op = boxes[b, 20]
                # 世界法线 = R^T · n_local
                lnx, lny, lnz = nxs[q, 0], nxs[q, 1], nxs[q, 2]
                nx = boxes[b, 6] * lnx + boxes[b, 9] * lny + boxes[b, 12] * lnz
                ny = boxes[b, 7] * lnx + boxes[b, 10] * lny + boxes[b, 13] * lnz
                nz = boxes[b, 8] * lnx + boxes[b, 11] * lny + boxes[b, 14] * lnz
                cosi = -(nx * dx + ny * dy + nz * dz)
                if cosi < 0: cosi = 0.0
                fres = 0.04 + 0.96 * (1 - cosi) ** 5
                # 反射方向 & 程序化环境（顶部柔光箱 + 侧面光条）
                rx = dx + 2 * cosi * nx; ry = dy + 2 * cosi * ny; rz = dz + 2 * cosi * nz
                env = 0.10 + 0.5 * max(ry, 0.0) ** 2
                strip = math.exp(-((rx - 0.55) ** 2) / 0.004) * (1.0 if ry > -0.2 else 0.3)
                strip += 0.7 * math.exp(-((rx + 0.6 + 0.1 * math.sin(t_env)) ** 2) / 0.01) * (1.0 if ry > 0.1 else 0.0)
                top = math.exp(-((ry - 0.9) ** 2) / 0.02) * 1.2
                envv = env + strip + top
                spec = max(rx * light_dir[0] + ry * light_dir[1] + rz * light_dir[2], 0.0) ** 60 * 3.0
                # 入射点局部坐标 → 到边缘的距离（边缘高光）
                ox = org[0] - boxes[b, 0] + dx * tn; oy = org[1] - boxes[b, 1] + dy * tn; oz = org[2] - boxes[b, 2] + dz * tn
                px = boxes[b, 6] * ox + boxes[b, 7] * oy + boxes[b, 8] * oz
                py = boxes[b, 9] * ox + boxes[b, 10] * oy + boxes[b, 11] * oz
                pz = boxes[b, 12] * ox + boxes[b, 13] * oy + boxes[b, 14] * oz
                hx, hy, hz = boxes[b, 3], boxes[b, 4], boxes[b, 5]
                ex = hx - abs(px); ey = hy - abs(py); ez = hz - abs(pz)
                # 当前面的两条轴上取最小距离
                if lnx != 0: e = min(ey, ez)
                elif lny != 0: e = min(ex, ez)
                else: e = min(ex, ey)
                ew = boxes[b, 19] * (tn * 0.0025 + 0.004)
                edge = math.exp(-e / ew) * 1.6
                # 出射点的背面边（较暗）
                ox2 = ox + dx * (tf - tn); oy2 = oy + dy * (tf - tn); oz2 = oz + dz * (tf - tn)
                qx = boxes[b, 6] * ox2 + boxes[b, 7] * oy2 + boxes[b, 8] * oz2
                qy = boxes[b, 9] * ox2 + boxes[b, 10] * oy2 + boxes[b, 11] * oz2
                qz = boxes[b, 12] * ox2 + boxes[b, 13] * oy2 + boxes[b, 14] * oz2
                fx = hx - abs(qx); fy = hy - abs(qy); fz = hz - abs(qz)
                e2 = min(min(fx + fy, fx + fz), fy + fz)
                edge2 = math.exp(-e2 / ew) * 0.55
                thick = tf - tn
                absorb = 1.0 - math.exp(-boxes[b, 18] * thick)
                cr, cg, cb = boxes[b, 15], boxes[b, 16], boxes[b, 17]
                rf = fres * envv * 0.45 + spec * 0.6
                ee = (edge + edge2) * 0.55
                lr = rf + ee * (0.35 + 0.65 * cr) + absorb * cr * 0.22
                lg = rf + ee * (0.35 + 0.65 * cg) + absorb * cg * 0.22
                lb = rf + ee * (0.35 + 0.65 * cb) + absorb * cb * 0.22
                ar += T * lr * op; ag += T * lg * op; ab += T * lb * op
                # 折射偏移（按法线和厚度）
                ox_ += T * nx * thick * 0.9 * op; oy_ += T * -ny * thick * 0.9 * op
                T *= 1.0 - op * (0.10 + 0.35 * absorb)
            out_add[j, i, 0] = ar; out_add[j, i, 1] = ag; out_add[j, i, 2] = ab
            out_cov[j, i] = 1.0 - T
            out_off[j, i, 0] = ox_; out_off[j, i, 1] = oy_


def rot_matrix(rx=0.0, ry=0.0, rz=0.0):
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]); Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return (Rz @ Ry @ Rx).astype(np.float32)   # 局部→世界


def make_box(center, half, rot=(0, 0, 0), tint=(0.5, 0.8, 1.0), density=0.4, edge=1.0, opacity=1.0):
    R = rot_matrix(*rot)
    row = np.zeros(BOX_FIELDS, np.float32)
    row[0:3] = center; row[3:6] = half; row[6:15] = R.T.reshape(-1)   # 存 世界→局部
    row[15:18] = tint; row[18] = density; row[19] = edge; row[20] = opacity
    return row


def render_boxes(bg, cam, boxes, scale=1.0, t=0.0, refract=14.0):
    """在 bg（H×W×3）上合成玻璃方块；返回新帧。scale<1 时以低分辨率追踪再放大。"""
    if len(boxes) == 0: return bg
    boxes = np.ascontiguousarray(np.stack(boxes).astype(np.float32))
    w, h = int(W * scale), int(H * scale)
    # 屏幕包围盒
    bb = np.zeros((len(boxes), 4), np.int64)
    sgn = np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)], np.float32)
    for k, b in enumerate(boxes):
        Rw = b[6:15].reshape(3, 3).T
        corners = b[0:3] + (sgn * b[3:6]) @ Rw.T
        x, y, z = cam.project(corners)
        if (z < 0.05).any(): bb[k] = (0, 0, w - 1, h - 1)
        else: bb[k] = (int(x.min() * scale) - 2, int(y.min() * scale) - 2, int(x.max() * scale) + 2, int(y.max() * scale) + 2)
    dirs = cam.rays(scale)
    add = np.zeros((h, w, 3), np.float32); cov = np.zeros((h, w), np.float32); off = np.zeros((h, w, 2), np.float32)
    L = np.array([0.4, 0.8, -0.45], np.float32); L /= np.linalg.norm(L)
    _boxes(dirs, cam.pos.astype(np.float32), boxes, bb, add, cov, off, L, np.float32(t))
    if scale != 1.0:
        add = cv2.resize(add, (W, H), interpolation=cv2.INTER_LINEAR)
        cov = cv2.resize(cov, (W, H), interpolation=cv2.INTER_LINEAR)
        off = cv2.resize(off, (W, H), interpolation=cv2.INTER_LINEAR)
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    refr = cv2.remap(bg, gx + off[..., 0] * refract, gy + off[..., 1] * refract, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    c = cov[..., None]
    return bg * (1 - c) + refr * c * 0.85 + add


# ------------------------------------------------------------------ 2D 工具
def blur(x, s):
    return cv2.GaussianBlur(x, (0, 0), s) if s > 0.3 else x


def glow_line(layer, pts, color, width=2.0, glow=1.0, alpha=1.0):
    """抗锯齿折线 + 辉光（pts: N×2 屏幕坐标）"""
    if len(pts) < 2 or alpha <= 0: return
    m = np.zeros(layer.shape[:2], np.float32)
    p = np.round(np.asarray(pts) * 16).astype(np.int32).reshape(-1, 1, 2)
    cv2.polylines(m, [p], False, 1.0, max(1, int(round(width))), cv2.LINE_AA, shift=4)
    g = m + blur(m, width * 3) * glow * 1.5 + blur(m, width * 10) * glow * 0.8
    layer += g[..., None] * (np.asarray(color, np.float32) * alpha)


def ring(layer, cx, cy, r, color, width=2.0, alpha=1.0, glow=1.0):
    m = np.zeros(layer.shape[:2], np.float32)
    cv2.circle(m, (int(cx * 16), int(cy * 16)), int(r * 16), 1.0, max(1, int(width)), cv2.LINE_AA, shift=4)
    g = m + blur(m, width * 3) * glow + blur(m, width * 12) * glow * 0.6
    layer += g[..., None] * (np.asarray(color, np.float32) * alpha)


def rect_panel(frame, x0, y0, x1, y1, alpha=1.0, tint=(0.06, 0.08, 0.13), border=(0.6, 0.75, 1.0), radius=26, blur_bg=18):
    """毛玻璃面板：背景模糊 + 暗色叠加 + 细边框 + 顶部高光"""
    if alpha <= 0: return
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    x0c, y0c, x1c, y1c = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if x1c <= x0c or y1c <= y0c: return
    m = np.zeros((y1 - y0, x1 - x0), np.float32)
    cv2.rectangle(m, (radius, 0), (x1 - x0 - radius, y1 - y0), 1, -1)
    cv2.rectangle(m, (0, radius), (x1 - x0, y1 - y0 - radius), 1, -1)
    for cx_, cy_ in [(radius, radius), (x1 - x0 - radius, radius), (radius, y1 - y0 - radius), (x1 - x0 - radius, y1 - y0 - radius)]:
        cv2.circle(m, (cx_, cy_), radius, 1, -1, cv2.LINE_AA)
    m = blur(m, 1.0)[y0c - y0:y1c - y0, x0c - x0:x1c - x0] * alpha
    reg = frame[y0c:y1c, x0c:x1c]
    pad = blur_bg * 2
    big = frame[max(y0c - pad, 0):min(y1c + pad, H), max(x0c - pad, 0):min(x1c + pad, W)]
    bl = blur(big, blur_bg)[y0c - max(y0c - pad, 0):y0c - max(y0c - pad, 0) + (y1c - y0c),
                            x0c - max(x0c - pad, 0):x0c - max(x0c - pad, 0) + (x1c - x0c)]
    mm = m[..., None]
    reg[:] = reg * (1 - mm) + (bl * 0.45 + np.asarray(tint, np.float32) * 0.9) * mm
    # 边框
    e = np.zeros_like(m)
    em = cv2.Canny((m / max(alpha, 1e-3) * 255).astype(np.uint8), 50, 150).astype(np.float32) / 255
    e = blur(em, 0.8) * alpha
    hi = np.linspace(1.0, 0.35, e.shape[0])[:, None]
    reg += (e * hi)[..., None] * np.asarray(border, np.float32) * 0.55


def vignette_mask():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((x - W / 2) / (W * 0.62)) ** 2 + ((y - H / 2) / (H * 0.58)) ** 2)
    return np.clip(1.15 - 0.55 * d ** 2, 0.25, 1)[..., None].astype(np.float32)

VIG = None
GRAIN = None

def post(frame, t, bloom=1.0, vig=1.0, grain=0.018, ca=0.0, exposure=1.0):
    """frame: 线性-ish HDR → 显示空间 0..1"""
    global VIG, GRAIN
    if VIG is None:
        VIG = vignette_mask()
        rng = np.random.default_rng(7)
        GRAIN = [cv2.resize(rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32), (W, H)) for _ in range(6)]
    f = frame * exposure
    if bloom > 0:
        small = cv2.resize(f, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        br = np.maximum(small - 0.55, 0)
        b = blur(br, 3) * 0.5 + blur(br, 9) * 0.6 + blur(br, 24) * 0.7
        f = f + cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR) * bloom
    if ca > 0:
        k = int(ca)
        f[..., 0] = np.roll(f[..., 0], k, axis=1); f[..., 2] = np.roll(f[..., 2], -k, axis=1)
    f = f * (1 - vig + vig * VIG)
    # 色调映射（柔和肩部，保持暗部）
    f = np.maximum(f, 0)
    f = f * (2.51 * f + 0.03) / (f * (2.43 * f + 0.59) + 0.14)
    if grain > 0:
        g = GRAIN[int(t * 24) % 6]
        lum = f.mean(axis=2, keepdims=True)
        f = f + g[..., None] * grain * (0.35 + 0.65 * np.sqrt(np.clip(lum, 0, 1)))
    return np.clip(f, 0, 1)


def to_u8(frame):
    return (np.clip(frame, 0, 1) * 255 + 0.5).astype(np.uint8)
