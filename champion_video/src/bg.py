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
