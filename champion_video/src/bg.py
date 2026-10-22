"""背景：深空星云（低分辨率噪声场平移/缩放）+ 三维星尘（透视投影）+ 透视网格地面。"""
import math
import numpy as np, cv2
from engine import W, H, BG0, BG1, Frame, cl, lerpc

QW, QH = W // 4, H // 4


def fbm(w, h, seed, octaves=5, base=3):
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32); amp, tot = 1.0, 0
    for o in range(octaves):
        n = base * 2 ** o
        r = rng.random((max(2, n * h // w), n)).astype(np.float32)
        acc += cv2.resize(r, (w, h), interpolation=cv2.INTER_CUBIC) * amp
        tot += amp; amp *= 0.55
    acc /= tot
    return (acc - acc.min()) / (acc.max() - acc.min())


class Background:
    def __init__(self):
        self.n1 = fbm(QW * 2, QH * 2, 11)
        self.n2 = fbm(QW * 2, QH * 2, 23, base=2)
        rng = np.random.default_rng(5)
        N = 900
        self.sx = rng.uniform(-1, 1, N).astype(np.float32)
        self.sy = rng.uniform(-1, 1, N).astype(np.float32)
        self.sz = rng.uniform(0.05, 1, N).astype(np.float32)
        self.sb = rng.uniform(0.3, 1, N).astype(np.float32)
        yy, xx = np.mgrid[0:QH, 0:QW].astype(np.float32)
        self.radial = np.exp(-(((xx - QW / 2) / (QW * 0.8)) ** 2 + ((yy - QH * 0.42) / (QH * 0.55)) ** 2))

    def nebula(self, t, c1, c2, amt=1.0, drift=1.0):
        ox = int((t * 3.0 * drift) % QW); oy = int((t * 1.7 * drift) % QH)
        a = self.n1[oy:oy + QH, ox:ox + QW]
        b = self.n2[(QH - oy // 2):(QH - oy // 2) + QH, (ox // 2):(ox // 2) + QW]
        m1 = np.clip(a - 0.45, 0, 1) ** 1.5 * 2.2
        m2 = np.clip(b - 0.5, 0, 1) ** 1.4 * 2.0
        img = np.empty((QH, QW, 3), np.float32)
        img[:] = BG0
        img += self.radial[..., None] * np.asarray(BG1, np.float32) * 1.3
        img += (m1 * self.radial)[..., None] * np.asarray(c1, np.float32) * 0.22 * amt
        img += (m2 * self.radial)[..., None] * np.asarray(c2, np.float32) * 0.16 * amt
        return cv2.resize(img, (W, H), interpolation=cv2.INTER_LINEAR)

    def stars(self, F, t, speed=0.02, col=(0.75, 0.85, 1.0), a=1.0, warp=0.0):
        """三维星尘：向镜头缓慢飞来；warp>0 时拉出光线（跃迁）"""
        if a <= 0.01: return
        z = (self.sz - t * speed - warp * 0.0) % 1.0 + 0.02
        f = 0.9
        x = W / 2 + self.sx / z * f * W * 0.5
        y = H * 0.45 + self.sy / z * f * H * 0.5
        br = self.sb * np.clip(1.2 - z, 0, 1) * a
        ok = (x > -50) & (x < W + 50) & (y > -50) & (y < H + 50) & (br > 0.02)
        xs, ys, bs, zs = x[ok], y[ok], br[ok], z[ok]
        if warp > 0.01:
            for xi, yi, bi, zi in zip(xs, ys, bs, zs):
                dx, dy = xi - W / 2, yi - H * 0.45
                L = warp * 0.25 / zi
                F.line((xi, yi), (xi - dx * L, yi - dy * L), col, bi * 0.8, 2, glow=0.5)
        idx = (np.clip(ys, 0, H - 1).astype(int), np.clip(xs, 0, W - 1).astype(int))
        np.add.at(F.img, idx, np.asarray(col, np.float32)[None, :] * bs[:, None] * 0.9)
        np.add.at(F.glow, idx, np.asarray(col, np.float32)[None, :] * bs[:, None] * 2.0)

    def grid(self, F, t, col, a=0.5, horizon=1180, speed=0.0, tilt=0.0):
        """透视网格地面"""
        if a <= 0.01: return
        cx = W / 2
        for i in range(-14, 15):
            F.line((cx + i * 22, horizon), (cx + i * 300, H + 40), col, a * 0.35, 1)
        off = (t * speed) % 1.0
        for j in range(16):
            u = (j + off) / 16
            yv = horizon + (u ** 2.2) * (H + 40 - horizon)
            F.line((0, yv), (W, yv), col, a * 0.35 * min(1, u * 3), 1)
        # 地平线光
        F.blob((cx, horizon), 140, col, a * 0.25)

    # ------------------------------------------------------------ v4：粒子地面 / 体积光 / 金尘 / 横向光晕
    _field = None

    def field(self, F, t, col1, col2=None, a=1.0, horizon=1240, speed=0.35, n=120, lift=None):
        """三维粒子地面：透视投影的光点网格向镜头缓慢流动，近处更大更亮，远处汇成地平线辉光"""
        if a <= 0.01: return
        if self._field is None:
            rng = np.random.default_rng(9)
            g = (np.arange(n) - (n - 1) / 2) / ((n - 1) / 2)
            X, Z = np.meshgrid(g, np.linspace(0, 1, n))
            jit = rng.uniform(-0.35, 0.35, (2, n, n)) / n * 2
            Background._field = ((X + jit[0]).ravel().astype(np.float32), (Z + jit[1] / 2).ravel().astype(np.float32),
                                 rng.random(n * n).astype(np.float32) * 6.28, rng.random(n * n).astype(np.float32))
        fx, fz, ph, sz = self._field
        z = (fz - t * speed * 0.05) % 1.0
        d = 0.06 + z * 2.4                                  # 深度（越大越远）
        x = W / 2 + fx * 900 / d
        y = horizon + (H - horizon) * 0.33 / d
        if lift is not None:
            y = y - lift(x, d) / d
        tw = 0.6 + 0.4 * np.sin(t * 2.2 + ph)
        br = tw * (0.35 + 0.65 * sz) * np.clip(1.1 - z, 0, 1) ** 1.2 * np.clip(z * 12, 0, 1) * a
        ok = (x > 1) & (x < W - 2) & (y > 1) & (y < H - 2) & (br > 0.01)
        x, y, br, z, sz = x[ok], y[ok], br[ok], z[ok], sz[ok]
        c1 = np.asarray(col1, np.float32); c2 = np.asarray(col2 if col2 is not None else col1, np.float32)
        w2 = (sz > 0.75).astype(np.float32)[:, None]
        col = c1[None] * (1 - w2) + c2[None] * w2
        xi, yi = x.astype(int), y.astype(int)
        v = col * br[:, None]
        np.add.at(F.img, (yi, xi), v * 2.0)
        np.add.at(F.glow, (yi, xi), v * 5.0)
        big = z < 0.3                                       # 近处光点画成 2×2
        for ox, oy in ((1, 0), (0, 1), (1, 1)):
            np.add.at(F.img, (yi[big] + oy, xi[big] + ox), v[big] * 1.2)
        F.blob((W / 2, horizon + 10), 260, c1, 0.10 * a)   # 地平线辉光
        F.blob((W / 2, horizon + 10), 90, c1, 0.10 * a)

    _beam_x = None

    def beams(self, F, t, col, a=1.0, n=5, src_y=-200, spread=0.55, seed=3):
        """自顶部斜射的体积光（1/4 分辨率计算后放大叠加）"""
        if a <= 0.01: return
        rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:QH, 0:QW].astype(np.float32)
        acc = np.zeros((QH, QW), np.float32)
        for k in range(n):
            sx = rng.uniform(0.15, 0.85) * QW
            ang = rng.uniform(-spread, spread) * 0.5 + 0.12 * math.sin(t * 0.25 + k * 1.7)
            wdt = rng.uniform(0.04, 0.10)
            amp = rng.uniform(0.5, 1.0) * (0.75 + 0.25 * math.sin(t * 0.9 + k * 2.3))
            dx, dy = math.sin(ang), math.cos(ang)
            px, py = xx - sx, yy - src_y / 4
            along = px * dx + py * dy
            perp = np.abs(px * dy - py * dx)
            acc += amp * np.exp(-(perp / (wdt * along.clip(1) + 2)) ** 2) * np.exp(-along / (QH * 0.9))
        img = cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR)[..., None] * np.asarray(col, np.float32)
        F.img += img * 0.22 * a
        F.glow += img * 0.10 * a

    _dust = None

    def dust(self, F, t, col, a=1.0, n=260, rise=18.0, seed=21):
        """漂浮的金色微尘（景深：大而虚的在前，小而亮的在后）"""
        if a <= 0.01: return
        if self._dust is None:
            rng = np.random.default_rng(seed)
            Background._dust = (rng.random(n) * W, rng.random(n) * (H + 200), rng.random(n), rng.random(n) * 6.28)
        x0, y0, s, ph = self._dust
        y = (y0 - t * rise * (0.4 + s)) % (H + 200) - 100
        x = x0 + 30 * np.sin(t * 0.3 + ph)
        tw = 0.5 + 0.5 * np.sin(t * 1.7 + ph * 3)
        for xi, yi, si, ti in zip(x, y, s, tw):
            if si > 0.93:
                F.blob((xi, yi), 10 + 18 * si, col, 0.10 * a * ti, target='glow')
            elif 0 <= xi < W - 1 and 0 <= yi < H - 1:
                v = np.asarray(col, np.float32) * (0.25 + 0.6 * ti) * a * (0.4 + si)
                F.img[int(yi), int(xi)] += v
                F.glow[int(yi), int(xi)] += v * 3

    def flare(self, F, y, col, a=1.0, x=W / 2, length=1.0):
        """横向变形镜头光晕：转场时一道扫过画面的光"""
        if a <= 0.01: return
        L = int(W * 0.9 * length)
        m = np.exp(-((np.arange(-L, L) / (L * 0.45)) ** 2)).astype(np.float32)[None, :]
        core = np.repeat(m, 3, 0) * np.array([[0.35], [1.0], [0.35]], np.float32)
        F.add(core, x - L, y - 1, col, a * 1.2, glow=2.0)
        F.blob((x, y), 70, col, 0.5 * a)
        F.blob((x, y), 18, (1, 1, 1), 0.6 * a)
