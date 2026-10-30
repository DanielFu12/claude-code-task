"""竖屏 1080×1920 动态图形引擎：线性光叠加 + 辉光 + 简易三维投影 + 玻璃面板（numpy / cv2 / PIL）。"""
import math, os, sys
from functools import lru_cache
import numpy as np, cv2
cv2.setNumThreads(1)
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))           # MastersTao/
FONT_DIR = os.path.join(ROOT, "fonts")
sys.path.insert(0, os.path.join(ROOT, "brand"))
from mt_brand import PALETTE, Hud, load_logo  # noqa: E402

FONTS = {
    "light": "sans_light.ttf", "reg": "sans_reg.ttf", "med": "sans_med.ttf", "bold": "sans_bold.ttf",
    "black": "sans_black.ttf", "serif": "serif_bold.ttf", "serifb": "serif_black.ttf",
    "num": "InterDisplay-SemiBold.otf", "numb": "InterDisplay-Bold.otf", "numk": "InterDisplay-Black.otf",
    "numl": "InterDisplay-Light.otf", "numm": "InterDisplay-Medium.otf", "mono": "mono.ttf",
}

P = PALETTE
GOLD, ICE, VIO = np.array(P["series_a"]), np.array(P["series_b"]), np.array(P["series_ab"])
INK, INK2, INK3 = np.array(P["ink"]), np.array(P["ink2"]), np.array(P["ink3"])
BA, BB = np.array(P["brand_a"]), np.array(P["brand_b"])
WARN = np.array(P["warn"]); RED = np.array(P["up"]); GRN = np.array(P["down"])


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
def eio5(x):
    x = cl(x); return 16 * x ** 5 if x < .5 else 1 - (-2 * x + 2) ** 5 / 2
def eback(x, s=1.6):
    x = cl(x) - 1; return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, x):
    return a + (b - a) * x
def win(t, a, b, fi=0.4, fo=0.4):
    """0→1→0 包络：a 时开始淡入，b 时淡出完成"""
    if t < a or t > b: return 0.0
    v = eo((t - a) / fi) if fi > 0 else 1.0
    if fo > 0: v *= eio((b - t) / fo)
    return v


# ---------------------------------------------------------------- text
@lru_cache(64)
def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, FONTS[name]), int(size))


@lru_cache(4096)
def text_mask(s, name, size, track=0.0, tab=False):
    """渲染一行文字为 alpha 掩码。返回 (mask, baseline_y, width)。tab=True 时数字等宽。"""
    f = font(name, size)
    asc, desc = f.getmetrics()
    pad = int(size * 0.25) + 2
    if tab:
        dw = max(f.getlength(d) for d in "0123456789")
        advs = [dw if ch.isdigit() else f.getlength(ch) for ch in s]
    else:
        advs = [f.getlength(ch) for ch in s]
    tw = sum(advs) + track * size * max(len(s) - 1, 0)
    im = Image.new("L", (int(math.ceil(tw)) + 2 * pad, asc + desc + 2 * pad), 0)
    d = ImageDraw.Draw(im)
    x = pad
    for ch, adv in zip(s, advs):
        off = (adv - f.getlength(ch)) / 2 if tab and ch.isdigit() else 0
        d.text((x + off, pad + asc), ch, font=f, fill=255, anchor="ls")
        x += adv + track * size
    return np.asarray(im, np.float32) / 255.0, pad + asc, tw, pad


def text_width(s, name, size, track=0.0, tab=False):
    return text_mask(s, name, size, track, tab)[2]


# ---------------------------------------------------------------- blur helpers
def blur(img, sigma):
    if sigma <= 0.3: return img
    return cv2.GaussianBlur(img, (0, 0), sigma, borderType=cv2.BORDER_CONSTANT)


class Cam:
    """透视相机：pos 世界坐标，yaw/pitch 弧度，f 焦距（像素），cx/cy 屏幕中心。"""

    def __init__(self, pos=(0, 0, -10), yaw=0.0, pitch=0.0, roll=0.0, f=1400, cx=W / 2, cy=H / 2):
        self.pos = np.array(pos, np.float64); self.f = f; self.cx = cx; self.cy = cy
        cy_, sy = math.cos(yaw), math.sin(yaw)
        cp, sp = math.cos(pitch), math.sin(pitch)
        cr, sr = math.cos(roll), math.sin(roll)
        Ry = np.array([[cy_, 0, -sy], [0, 1, 0], [sy, 0, cy_]])
        Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
        Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
        self.R = Rz @ Rx @ Ry

    def project(self, pts):
        p = (np.asarray(pts, np.float64) - self.pos) @ self.R.T
        z = p[..., 2]
        zs = np.maximum(z, 1e-3)
        x = self.cx + self.f * p[..., 0] / zs
        y = self.cy - self.f * p[..., 1] / zs
        return x, y, z


class Frame:
    def __init__(self, t, bg=None):
        self.t = t
        self.C = np.zeros((H, W, 3), np.float32) if bg is None else bg.copy()   # 主画面
        self.G = np.zeros((H, W, 3), np.float32)                                  # 自发光（参与辉光）
        self.flash = 0.0; self.ca = 0.0; self.shake = (0.0, 0.0); self.zoom = 1.0
        self.bloom = 1.0; self.fade = 1.0

    # ---------------------------------------------- 基础图元
    def _region(self, x0, y0, w, h):
        X0, Y0 = max(int(x0), 0), max(int(y0), 0)
        X1, Y1 = min(int(x0) + w, W), min(int(y0) + h, H)
        if X1 <= X0 or Y1 <= Y0: return None
        return (slice(Y0, Y1), slice(X0, X1)), (slice(Y0 - int(y0), Y1 - int(y0)), slice(X0 - int(x0), X1 - int(x0)))

    def blit(self, m, x0, y0, col, a=1.0, buf="C", mode="over", colimg=None):
        """把掩码 m 以颜色 col 画到 (x0,y0)。mode: over（遮盖）/ add（叠加）。"""
        if a <= 0.003: return
        r = self._region(x0, y0, m.shape[1], m.shape[0])
        if r is None: return
        dst, src = r
        mm = m[src] * a
        c = colimg[src] if colimg is not None else np.asarray(col, np.float32)
        B = self.C if buf == "C" else self.G
        if mode == "over":
            B[dst] = B[dst] * (1 - mm[..., None]) + c * mm[..., None]
        else:
            B[dst] += c * mm[..., None]

    def text(self, s, x, y, size, fnt="med", col=INK, a=1.0, anchor="m", track=0.0, glow=0.0,
             tab=False, grad=None, shadow=0.0, rise=0.0):
        """y 为文字视觉中线。grad=(top_col, bottom_col) 竖向渐变。glow>0 时同时写入辉光层。"""
        if a <= 0.003 or not s: return 0
        m, base, tw, pad = text_mask(s, fnt, size, track, tab)
        xs = x - tw / 2 if anchor == "m" else (x if anchor == "l" else x - tw)
        x0 = xs - pad
        y0 = y + size * 0.36 - base + rise
        colimg = None
        if grad is not None:
            u = np.linspace(0, 1, m.shape[0], dtype=np.float32)[:, None, None]
            u = np.clip((u - 0.25) / 0.5, 0, 1)
            colimg = np.broadcast_to(np.asarray(grad[0], np.float32) * (1 - u) + np.asarray(grad[1], np.float32) * u,
                                     (m.shape[0], m.shape[1], 3))
        if shadow > 0:
            sh = blur(m, size * 0.08)
            self.blit(sh, x0, y0 + size * 0.04, (0, 0, 0), a * shadow)
        self.blit(m, x0, y0, col, a, colimg=colimg)
        if glow > 0:
            self.blit(m, x0, y0, col if grad is None else grad[0], a * glow, buf="G", mode="add")
        return tw

    def text_reveal(self, s, x, y, size, t0, fnt="med", col=INK, a=1.0, anchor="m", track=0.0, stag=0.04,
                    dur=0.5, rise=26, glow=0.0, out=None, tab=False):
        """逐字上浮出现（每个字单独渲染，保证中英文排版一致）"""
        if a <= 0.003: return
        tw = text_width(s, fnt, size, track, tab)
        xs = x - tw / 2 if anchor == "m" else (x if anchor == "l" else x - tw)
        f = font(fnt, size)
        cx = xs
        for i, ch in enumerate(s):
            p = (self.t - t0 - i * stag) / dur
            ai = a * eo(p); dy = (1 - eo5(p)) * rise
            if out is not None:
                q = (self.t - out - i * stag * 0.5) / 0.4
                ai *= 1 - eio(q); dy -= eio(q) * rise * 0.6
            if ai > 0.003 and ch != " ":
                self.text(ch, cx, y + dy, size, fnt, col, ai, anchor="l", glow=glow, tab=tab)
            cx += (text_width(ch, fnt, size, 0, tab)) + track * size

    # ---------------------------------------------- 线 / 多边形
    def line(self, p0, p1, col, a=1.0, th=2, buf="G"):
        self.poly([p0, p1], col, a, th, buf=buf)

    def poly(self, pts, col, a=1.0, th=2, closed=False, buf="G"):
        if a <= 0.003 or len(pts) < 2: return
        p = np.asarray(pts, np.float64)
        x0, y0 = np.floor(p.min(0) - th - 2).astype(int)
        x1, y1 = np.ceil(p.max(0) + th + 2).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W), min(y1, H)
        if x1 <= x0 or y1 <= y0: return
        m = np.zeros((y1 - y0, x1 - x0), np.uint8)
        q = ((p - [x0, y0]) * 16).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(m, [q], closed, 255, max(1, int(round(th))), cv2.LINE_AA, 4)
        self._add_mask(m, x0, y0, col, a, buf)

    def fill(self, pts, col, a=1.0, buf="C", mode="over", grad=None):
        """填充多边形；grad=(col_top, col_bottom, y_top, y_bottom) 竖向渐变"""
        if a <= 0.003: return
        p = np.asarray(pts, np.float64)
        x0, y0 = np.floor(p.min(0) - 2).astype(int)
        x1, y1 = np.ceil(p.max(0) + 2).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W), min(y1, H)
        if x1 <= x0 or y1 <= y0: return
        m = np.zeros((y1 - y0, x1 - x0), np.uint8)
        q = ((p - [x0, y0]) * 16).astype(np.int32).reshape(-1, 1, 2)
        cv2.fillPoly(m, [q], 255, cv2.LINE_AA, 4)
        mm = m.astype(np.float32) / 255.0
        colimg = None
        if grad is not None:
            ys = np.arange(y0, y1, dtype=np.float32)[:, None, None]
            u = np.clip((ys - grad[2]) / max(grad[3] - grad[2], 1), 0, 1)
            colimg = np.broadcast_to(np.asarray(grad[0], np.float32) * (1 - u) + np.asarray(grad[1], np.float32) * u,
                                     (y1 - y0, x1 - x0, 3))
        self.blit(mm, x0, y0, col, a, buf=buf, mode=mode, colimg=colimg)

    def _add_mask(self, m, x0, y0, col, a, buf):
        B = self.C if buf == "C" else self.G
        B[y0:y0 + m.shape[0], x0:x0 + m.shape[1]] += (m.astype(np.float32) * (a / 255.0))[..., None] * np.asarray(col, np.float32)

    def rrect_pts(self, x0, y0, x1, y1, r, n=8):
        pts = []
        for cx, cy, s in ((x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, math.pi / 2), (x0 + r, y0 + r, math.pi)):
            for k in range(n + 1):
                ang = s + k / n * math.pi / 2
                pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        return pts

    def glass(self, x0, y0, x1, y1, r=28, a=1.0, tint=(0.55, 0.6, 0.9), edge=None, blur_s=18, dark=0.35):
        """磨砂玻璃面板：模糊背后的画面 + 压暗 + 微弱色调 + 顶部高光 + 发光描边"""
        if a <= 0.003: return
        X0, Y0, X1, Y1 = max(int(x0), 0), max(int(y0), 0), min(int(x1), W), min(int(y1), H)
        if X1 <= X0 or Y1 <= Y0: return
        pts = self.rrect_pts(x0, y0, x1, y1, r)
        m = np.zeros((Y1 - Y0, X1 - X0), np.uint8)
        q = ((np.asarray(pts) - [X0, Y0]) * 16).astype(np.int32).reshape(-1, 1, 2)
        cv2.fillPoly(m, [q], 255, cv2.LINE_AA, 4)
        mm = (m.astype(np.float32) / 255.0 * a)[..., None]
        reg = self.C[Y0:Y1, X0:X1]
        gl = self.G[Y0:Y1, X0:X1]
        src = reg + gl * 0.6
        b = cv2.GaussianBlur(src, (0, 0), blur_s)
        ys = np.linspace(0, 1, Y1 - Y0, dtype=np.float32)[:, None, None]
        sheen = (0.075 * np.exp(-ys * 5.0) + 0.018) * np.asarray(tint, np.float32)
        glassc = b * (1 - dark) + sheen
        reg[:] = reg * (1 - mm) + glassc * mm
        gl[:] = gl * (1 - mm * 0.7)
        ec = edge if edge is not None else (0.55, 0.6, 0.85)
        self.poly(pts + [pts[0]], ec, 0.35 * a, 1.6, buf="G")
        # 顶边高光
        self.poly(pts[-9:] + pts[:9], (1, 1, 1), 0.10 * a, 1.2, buf="G")

    def glow_dot(self, x, y, r, col, a=1.0, buf="G"):
        if a <= 0.003: return
        R = int(r * 3) + 1
        X0, Y0, X1, Y1 = max(int(x) - R, 0), max(int(y) - R, 0), min(int(x) + R + 1, W), min(int(y) + R + 1, H)
        if X1 <= X0 or Y1 <= Y0: return
        yy, xx = np.mgrid[Y0:Y1, X0:X1].astype(np.float32)
        g = np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * r * r)) * a
        B = self.C if buf == "C" else self.G
        B[Y0:Y1, X0:X1] += g[..., None] * np.asarray(col, np.float32)

    def splat(self, xs, ys, cols, a, buf="G", size=1):
        """粒子：双线性分配到 2×2 像素（亚像素平滑）；size>1 时额外加十字邻域"""
        xs = np.asarray(xs, np.float32).ravel(); ys = np.asarray(ys, np.float32).ravel()
        a = np.broadcast_to(np.asarray(a, np.float32), xs.shape).ravel()
        cols = np.asarray(cols, np.float32)
        cols = cols.reshape(-1, 3) if cols.ndim == 2 else np.broadcast_to(cols, (xs.size, 3))
        ok = (xs >= 1) & (xs < W - 2) & (ys >= 1) & (ys < H - 2) & (a > 0.002)
        if not ok.any(): return
        xs, ys, a, cols = xs[ok], ys[ok], a[ok], cols[ok]
        x0 = np.floor(xs).astype(np.int64); y0 = np.floor(ys).astype(np.int64)
        fx = xs - x0; fy = ys - y0
        B = (self.C if buf == "C" else self.G).reshape(-1, 3)
        offs = [(0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)]
        if size > 1:
            offs += [(-1, 0, 0.35 * (1 - fx)), (2, 0, 0.35 * fx), (0, -1, 0.35 * (1 - fy)), (0, 2, 0.35 * fy)]
        for dx, dy, w in offs:
            idx = (y0 + dy) * W + (x0 + dx)
            np.add.at(B, idx, cols * (a * w)[:, None])

    def dots(self, xs, ys, cols, a, sigma=1.6, buf="G", gain=None):
        """圆点粒子：在包围盒内单像素累加，再小半径高斯扩散（保持峰值亮度）"""
        xs = np.asarray(xs, np.float32).ravel(); ys = np.asarray(ys, np.float32).ravel()
        if xs.size == 0: return
        pad = int(sigma * 4) + 3
        x0 = max(int(xs.min()) - pad, 0); y0 = max(int(ys.min()) - pad, 0)
        x1 = min(int(xs.max()) + pad + 2, W); y1 = min(int(ys.max()) + pad + 2, H)
        if x1 - x0 < 4 or y1 - y0 < 4: return
        tmp = np.zeros((y1 - y0, x1 - x0, 3), np.float32)
        a = np.broadcast_to(np.asarray(a, np.float32), xs.shape).ravel()
        cols = np.asarray(cols, np.float32)
        cols = cols.reshape(-1, 3) if cols.ndim == 2 else np.broadcast_to(cols, (xs.size, 3))
        lx = xs - x0; ly = ys - y0
        ok = (lx >= 0) & (lx < x1 - x0 - 1) & (ly >= 0) & (ly < y1 - y0 - 1) & (a > 0.002)
        if not ok.any(): return
        lx, ly, a, cols = lx[ok], ly[ok], a[ok], cols[ok]
        ix = np.floor(lx).astype(np.int64); iy = np.floor(ly).astype(np.int64)
        fx = lx - ix; fy = ly - iy
        flat = tmp.reshape(-1, 3); ww = x1 - x0
        for dx, dy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            np.add.at(flat, (iy + dy) * ww + ix + dx, cols * (a * w)[:, None])
        tmp = cv2.GaussianBlur(tmp, (0, 0), sigma) * (gain if gain else 2 * math.pi * sigma * sigma * 0.85)
        (self.C if buf == "C" else self.G)[y0:y1, x0:x1] += tmp

    # ---------------------------------------------- 三维玻璃柱
    def bar3d(self, cam, x, z, w, d, h, col, a=1.0, y0=0.0, glow=1.0, glass=True):
        """以 (x, y0, z) 为底面中心、宽 w、深 d、高 h 的玻璃长方体"""
        if a <= 0.003 or h <= 1e-4: return
        hw, hd = w / 2, d / 2
        V = np.array([[x - hw, y0, z - hd], [x + hw, y0, z - hd], [x + hw, y0, z + hd], [x - hw, y0, z + hd],
                      [x - hw, y0 + h, z - hd], [x + hw, y0 + h, z - hd], [x + hw, y0 + h, z + hd], [x - hw, y0 + h, z + hd]])
        px, py, pz = cam.project(V)
        if (pz < 0.2).any(): return
        P2 = np.stack([px, py], 1)
        col = np.asarray(col, np.float32)
        faces = {  # 顶点序号, 亮度
            "front": ([0, 1, 5, 4], 0.85), "right": ([1, 2, 6, 5], 0.55), "left": ([3, 0, 4, 7], 0.55),
            "top": ([4, 5, 6, 7], 1.25), "back": ([2, 3, 7, 6], 0.4),
        }
        campos = cam.pos
        vis = []
        normals = {"front": (0, 0, -1), "right": (1, 0, 0), "left": (-1, 0, 0), "top": (0, 1, 0), "back": (0, 0, 1)}
        centers = {k: V[idx].mean(0) for k, (idx, _) in faces.items()}
        for k, (idx, lum) in faces.items():
            n = np.array(normals[k]); c = centers[k]
            if np.dot(campos - c, n) > 0:
                vis.append(k)
        ytop = py[4:].min(); ybot = py[:4].max()
        for k in vis:
            idx, lum = faces[k]
            pts = P2[idx]
            if glass:
                self.fill(pts, col * 0.06 * lum, a, buf="C", mode="add",
                          grad=None)
                self.fill(pts, col * lum, a * 0.22, buf="G", mode="add",
                          grad=(col * lum * 1.3, col * lum * 0.15, ytop, ybot))
            else:
                self.fill(pts, col * lum * 0.5, a, buf="C")
        # 棱线
        edges = [(4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7), (0, 1), (1, 2)]
        for i, j in edges:
            th = 2.2 if i >= 4 and j >= 4 else 1.4
            self.line(P2[i], P2[j], col * (1.0 if i >= 4 and j >= 4 else 0.55), a * 0.9 * glow, th)
        return P2

    # ---------------------------------------------- 合成
    def finish(self, hud=None, grain_seed=0):
        G = self.G
        # 辉光（1/4 分辨率多级模糊）
        small = cv2.resize(G, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        b1 = cv2.GaussianBlur(small, (0, 0), 3)
        b2 = cv2.GaussianBlur(small, (0, 0), 10)
        b3 = cv2.GaussianBlur(cv2.resize(small, (W // 16, H // 16), interpolation=cv2.INTER_AREA), (0, 0), 6)
        bl = 0.55 * b1 + 0.45 * b2 + 0.35 * cv2.resize(b3, (W // 4, H // 4))
        bl = cv2.resize(bl, (W, H), interpolation=cv2.INTER_LINEAR)
        img = self.C + G + bl * (0.9 * self.bloom)
        if self.flash > 0:
            # 曝光式闪光：提亮已有画面 + 极少量冷色，避免整屏灰白
            img = img * (1 + 2.2 * self.flash) + self.flash * 0.10 * np.array([0.7, 0.8, 1.0], np.float32)
        # 色差
        if self.ca > 0.3:
            s = max(1, int(round(self.ca)))
            img = img.copy()
            img[:, s:, 0] = img[:, :-s, 0]
            img[:, :-s, 2] = img[:, s:, 2]
        # 缩放 / 震动
        if self.zoom != 1.0 or self.shake != (0.0, 0.0):
            M = np.array([[self.zoom, 0, (1 - self.zoom) * W / 2 + self.shake[0]],
                          [0, self.zoom, (1 - self.zoom) * H / 2 + self.shake[1]]], np.float32)
            img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        # 柔和肩部色调映射
        img = np.where(img < 0.8, img, 0.8 + 0.2 * np.tanh((img - 0.8) / 0.2))
        img = np.clip(img, 0, 1) * self.fade
        if hud is not None:
            hud(img)
        # 颗粒（极轻，防止渐变色带）
        rng = np.random.default_rng(grain_seed)
        img += (rng.random((H, W, 1), dtype=np.float32) - 0.5) * (3.0 / 255)
        return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
