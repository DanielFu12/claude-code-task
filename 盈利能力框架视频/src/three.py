"""轻量 3D：相机、带遮挡的多边形画布、发光网格地面、3D 文字、以及全片的核心意象 ——「价值体」。

价值体（ValueBlock）
  x 轴 = 时间（年）           → 能持续多久（L5），会不会被截断（L0）
  y 轴 = ROIC − WACC         → 超额回报有多高（L1），维持成本削掉多少（L2），杠杆放大（L4）
  z 轴 = 投入资本             → 能不能越做越厚（L3）
  体积（折现后）= 经济利润现值之和 → 每股内在价值
"""
import math
import numpy as np, cv2
from engine import *


def _norm(v):
    v = np.asarray(v, np.float64)
    return v / (np.linalg.norm(v) + 1e-12)


class Cam:
    def __init__(self, eye, target, fov=42.0, roll=0.0):
        self.eye = np.asarray(eye, np.float64)
        self.target = np.asarray(target, np.float64)
        f = _norm(self.target - self.eye)
        up = np.array([math.sin(roll), math.cos(roll), 0.0])
        r = _norm(np.cross(f, up))
        u = np.cross(r, f)
        self.f, self.r, self.u = f, r, u
        self.fpx = (H / 2) / math.tan(math.radians(fov) / 2)

    def project(self, P):
        P = np.asarray(P, np.float64).reshape(-1, 3) - self.eye
        x = P @ self.r; y = P @ self.u; z = P @ self.f
        zc = np.maximum(z, 1e-3)
        sx = W / 2 + self.fpx * x / zc
        sy = H / 2 - self.fpx * y / zc
        return np.stack([sx, sy], 1), z

    def scale_at(self, z):
        return self.fpx / max(z, 1e-3)


def orbit(target, dist, yaw, pitch, fov=42.0):
    t = np.asarray(target, np.float64)
    eye = t + dist * np.array([math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch)])
    return Cam(eye, t, fov)


def lerp_cam(c1, c2, x):
    """在两组 (target, dist, yaw, pitch, fov) 参数之间平滑插值"""
    return tuple(lerp(a, b, x) if not isinstance(a, (tuple, list)) else tuple(lerp(p, q, x) for p, q in zip(a, b))
                 for a, b in zip(c1, c2))


class Canvas:
    """带遮挡的 3D 画布：按远到近绘制，后画的覆盖先画的（预乘 alpha）"""

    def __init__(self, fr):
        self.fr = fr
        self.P = np.zeros((H, W, 3), np.float32)
        self.A = np.zeros((H, W), np.float32)
        self.items = []   # (depth, kind, data)

    def face(self, pts2, depth, col, a=0.85, edge=None, edge_a=1.0, th=2, glow=0.0):
        self.items.append((depth, 0, (pts2, col, a, edge, edge_a, th, glow)))

    def line(self, p0, p1, depth, col, a=1.0, th=2):
        self.items.append((depth, 1, (p0, p1, col, a, th)))

    def flush(self):
        fr = self.fr
        k = fr.k
        if k <= 0.003 or not self.items:
            return
        self.items.sort(key=lambda it: -it[0])
        P, A = self.P, self.A
        G = fr.E
        for depth, kind, d in self.items:
            if kind == 0:
                pts2, col, a, edge, edge_a, th, glow = d
                p = (np.asarray(pts2, np.float64) * 16).astype(np.int32).reshape(-1, 1, 2)
                x0 = max(int(p[:, 0, 0].min() // 16) - 2, 0); y0 = max(int(p[:, 0, 1].min() // 16) - 2, 0)
                x1 = min(int(p[:, 0, 0].max() // 16) + 3, W); y1 = min(int(p[:, 0, 1].max() // 16) + 3, H)
                if x1 <= x0 or y1 <= y0: continue
                m = np.zeros((y1 - y0, x1 - x0), np.uint8)
                q = p.copy(); q[:, 0, 0] -= x0 * 16; q[:, 0, 1] -= y0 * 16
                cv2.fillPoly(m, [q], 255, cv2.LINE_AA, 4)
                mm = m.astype(np.float32) * (a * k / 255)
                Pr = P[y0:y1, x0:x1]; Ar = A[y0:y1, x0:x1]
                Pr *= (1 - mm)[..., None]
                Pr += mm[..., None] * np.array(col, np.float32)
                Ar *= (1 - mm); Ar += mm
                if glow > 0:
                    G[y0:y1, x0:x1] += (mm * glow)[..., None] * np.array(col, np.float32)
                if edge is not None:
                    cv2.polylines(P, [p], True, tuple(float(c * edge_a * k) for c in edge), int(th), cv2.LINE_AA, 4)
                    cv2.polylines(A, [p], True, float(edge_a * k), int(th), cv2.LINE_AA, 4)
            else:
                p0, p1, col, a, th = d
                c = tuple(float(v * a * k) for v in col)
                pa = (int(p0[0] * 16), int(p0[1] * 16)); pb = (int(p1[0] * 16), int(p1[1] * 16))
                cv2.line(P, pa, pb, c, int(th), cv2.LINE_AA, 4)
                cv2.line(A, pa, pb, float(a * k), int(th), cv2.LINE_AA, 4)
        # 边线也参与辉光
        np.minimum(A, 1.0, out=A)
        fr.layers.append((P, A))
        fr.B += P * 0.35


def shade(col, normal, light=(0.45, 0.8, 0.4), amb=0.35):
    l = _norm(light)
    d = max(float(np.dot(_norm(normal), l)), 0.0)
    s = amb + (1 - amb) * d
    return tuple(c * s for c in col)


def grid_plane(fr, cam, y=0.0, x0=-2, x1=32, z0=-12, z1=12, step=1.0, col=None, a=0.5, fog=60.0, major=5):
    """发光网格平面（远处淡出）"""
    col = col or ICE
    for i, xv in enumerate(np.arange(x0, x1 + 1e-6, step)):
        P, Z = cam.project(np.array([[xv, y, z0], [xv, y, z1]]))
        if (Z <= 0.5).any(): continue
        zz = Z.mean()
        al = a * math.exp(-zz / fog) * (1.6 if round(xv) % major == 0 else 0.7)
        fr.line(tuple(P[0]), tuple(P[1]), col, al, 1)
    for zv in np.arange(z0, z1 + 1e-6, step):
        n = 24
        xs = np.linspace(x0, x1, n)
        pts = np.stack([xs, np.full(n, y), np.full(n, zv)], 1)
        P, Z = cam.project(pts)
        ok = Z > 0.5
        for j in range(n - 1):
            if ok[j] and ok[j + 1]:
                al = a * math.exp(-(Z[j] + Z[j + 1]) / 2 / fog) * (1.6 if round(zv) % major == 0 else 0.7)
                fr.line(tuple(P[j]), tuple(P[j + 1]), col, al, 1)


def text3d(fr, s, P, cam, size, fnt='sans_black', col=WHITE, a=1.0, mode='L', glow=0.0, anchor='m', ref=20.0):
    """把文字放在 3D 点上，按透视缩放（ref 为参考距离，在此距离时字号 = size）"""
    p, z = cam.project(np.asarray(P)[None])
    if z[0] <= 0.5: return
    sz = min(size * ref / z[0], 110)
    if sz < 6: return
    fr.text(s, p[0][0], p[0][1], sz, fnt, col, a, anchor=anchor, mode=mode, glow=glow)


def particles3d(fr, cam, P, cols, a, rad=1, fog=80.0):
    p, z = cam.project(P)
    ok = z > 0.5
    if not ok.any(): return
    al = np.asarray(a, np.float32) * np.exp(-z / fog) if np.ndim(a) else a * np.exp(-z / fog)
    al = np.where(ok, al, 0)
    near = z < 14
    cols = np.asarray(cols, np.float32)
    fr.splat(p[:, 0], p[:, 1], cols if cols.ndim == 1 else cols, al, 'E')
    if near.any():
        fr.dots(p[near, 0], p[near, 1], cols if cols.ndim == 1 else cols[near], al[near] * 0.6, rad, 'E')


# ================================================================ 价值体
class BlockSpec:
    """价值体的参数（都可以随时间插值，做形变动画）"""

    def __init__(self, **kw):
        self.T = 20.0          # 显示的年数（长度）
        self.h0 = 3.0          # 初始超额回报高度
        self.fade = 0.0        # 衰减速率（L5）
        self.d0 = 3.0          # 初始厚度（投入资本）
        self.grow = 0.0        # 厚度年增长（L3）
        self.cyc = 0.0         # 周期波动幅度
        self.cyc_f = 0.35      # 周期频率
        self.shave = 0.0       # 维持成本削顶（L2）
        self.cut = 99.0        # 截断年份（L0）
        self.shatter = 0.0     # 截断后碎裂进度 0..1
        self.disc = 0.06       # 折现（远处变暗）
        self.lev = 1.0         # 杠杆放大（L4）
        self.extend = 1.0      # 长度生长进度 0..1
        self.col = GOLD
        self.neg_col = RED
        self.alpha = 1.0
        self.__dict__.update(kw)

    def copy(self, **kw):
        b = BlockSpec(**self.__dict__)
        b.__dict__.update(kw)
        return b

    def mix(self, other, x):
        out = self.copy()
        for k, v in self.__dict__.items():
            o = other.__dict__[k]
            if isinstance(v, (int, float)) and isinstance(o, (int, float)):
                out.__dict__[k] = lerp(v, o, x)
            elif isinstance(v, tuple):
                out.__dict__[k] = lerpc(v, o, x)
        return out

    def h(self, x):
        base = self.h0 * np.exp(-self.fade * x) + self.cyc * np.sin(x * self.cyc_f * 2 * np.pi)
        return (base - self.shave) * self.lev

    def d(self, x):
        return self.d0 * (1 + self.grow) ** x


def draw_block(fr, cam, B, t=0.0, origin=(0, 0, 0), n=None, particles=True, edges=True, labels=False):
    """把价值体画到一个遮挡画布上：玻璃质感的面 + 发光轮廓 + 体内流动的价值粒子"""
    if B.alpha * fr.k <= 0.003: return
    cv = Canvas(fr)
    ox, oy, oz = origin
    L = B.T * cl(B.extend)
    if L < 0.05: return
    n = n or max(4, int(L * 2))
    xs = np.linspace(0, L, n + 1)
    hs = B.h(xs); ds = B.d(xs)
    light = (0.35, 0.85, 0.55)
    keep = xs <= B.cut + 1e-6
    for i in range(n):
        xa, xb = xs[i], xs[i + 1]
        if xa >= B.cut - 1e-6: continue
        xb = min(xb, B.cut)
        ha, hb = float(B.h(np.array([xa]))[0]), float(B.h(np.array([xb]))[0])
        da, db = float(B.d(np.array([xa]))[0]) / 2, float(B.d(np.array([xb]))[0]) / 2
        neg = (ha + hb) < 0
        col = B.neg_col if neg else B.col
        disc = math.exp(-B.disc * (xa + xb) / 2)
        Q = lambda x, y, z: (ox + x, oy + y, oz + z)
        top = np.array([Q(xa, ha, -da), Q(xb, hb, -db), Q(xb, hb, db), Q(xa, ha, da)])
        front = np.array([Q(xa, 0, da), Q(xb, 0, db), Q(xb, hb, db), Q(xa, ha, da)])
        back = np.array([Q(xa, 0, -da), Q(xb, 0, -db), Q(xb, hb, -db), Q(xa, ha, -da)])
        for quad, nrm, br, base_a, gl in ((back, (0, 0, -1), 0.22, 0.6, 0.02), (front, (0, 0, 1), 0.42, 0.82, 0.05),
                                          (top, (0, 1 if not neg else -1, 0), 0.75, 0.88, 0.16)):
            P2, Z = cam.project(quad)
            if (Z < 0.3).any(): continue
            c = shade(tuple(v * br * (0.35 + 0.65 * disc) for v in col), nrm, light, 0.55)
            cv.face(P2, Z.mean(), c, base_a * B.alpha, None, 0, 2, glow=gl * disc)
        # 轮廓线：顶部前后沿、底部前沿、每年一条竖线
        ec = lerpc(col, WHITE, 0.45)
        segs = [(Q(xa, ha, da), Q(xb, hb, db), 1.0, 2), (Q(xa, ha, -da), Q(xb, hb, -db), 0.6, 2), (Q(xa, 0, da), Q(xb, 0, db), 0.5, 1)]
        if abs(xa - round(xa)) < 1e-6 or i == 0:
            segs.append((Q(xa, 0, da), Q(xa, ha, da), 0.28, 1))
        for p0, p1, aa, th in segs:
            P2, Z = cam.project(np.array([p0, p1]))
            if (Z < 0.3).any(): continue
            cv.line(tuple(P2[0]), tuple(P2[1]), Z.mean() - 0.05, ec, aa * disc * B.alpha, th)
    # 两端封面
    ends = [0.0, min(L, B.cut)]
    for j, x in enumerate(ends):
        h = float(B.h(np.array([x]))[0]); d = float(B.d(np.array([x]))[0]) / 2
        cap = np.array([(ox + x, oy, oz - d), (ox + x, oy, oz + d), (ox + x, oy + h, oz + d), (ox + x, oy + h, oz - d)])
        P2, Z = cam.project(cap)
        if (Z < 0.3).any(): continue
        col = B.col if h >= 0 else B.neg_col
        cut_face = j == 1 and x < L - 1e-6
        c = (1.0, 0.3, 0.3) if cut_face else col
        cv.face(P2, Z.mean() - 0.02, shade(tuple(v * 0.5 for v in c), (-1 if j == 0 else 1, 0, 0), light, 0.6),
                0.9 * B.alpha, lerpc(c, WHITE, 0.5), B.alpha, 2, glow=0.25 if cut_face else 0.08)
    cv.flush()
    # 扫光：一道亮光沿时间轴扫过价值体（每 5 秒一次）
    Lc = min(L, B.cut)
    ph = (t / 5.0) % 1.0
    xs_ = ph * (Lc + 4) - 2
    if 0 <= xs_ <= Lc:
        hh = float(B.h(np.array([xs_]))[0]); dd = float(B.d(np.array([xs_]))[0]) / 2
        Q, Z = cam.project(np.array([(ox + xs_, oy, oz + dd), (ox + xs_, oy + hh, oz + dd), (ox + xs_, oy + hh, oz - dd)]))
        if (Z > 0.3).all():
            al = 0.8 * B.alpha * math.sin(math.pi * xs_ / max(Lc, 1e-3))
            fr.poly(Q, lerpc(B.col, WHITE, 0.7), al, 3)
            fr.glow(tuple(Q[1]), 22, lerpc(B.col, WHITE, 0.5), al * 0.8)
    # 地面光晕（像倒影）
    for xg in np.linspace(0, Lc, 7)[1:-1]:
        Q, Z = cam.project(np.array([(ox + xg, oy, oz)]))
        if Z[0] > 0.3:
            fr.glow(tuple(Q[0]), 900 / max(Z[0], 5), B.col, 0.10 * B.alpha * math.exp(-B.disc * xg))
    # 截断后的碎片：被切掉的未来化为粒子坠落
    if B.cut < L and B.shatter > 0:
        rng = np.random.default_rng(5)
        N = 2500
        x = B.cut + rng.random(N) * (L - B.cut)
        hh = B.h(x); y = rng.random(N) * hh
        z = (rng.random(N) - 0.5) * B.d(x)
        s = B.shatter
        vx = (rng.random(N) - 0.3) * 3; vy = rng.random(N) * 2
        P = np.stack([ox + x + vx * s, oy + y + vy * s - 9 * s * s, oz + z + (rng.random(N) - 0.5) * 4 * s], 1)
        particles3d(fr, cam, P, lerpc(B.col, (1.0, 0.4, 0.3), s), 0.8 * (1 - s) * B.alpha, 1)
    # 体内的价值粒子
    if particles and L > 0.5:
        rng = np.random.default_rng(11)
        N = 1400
        sp = 0.5 + rng.random(N)
        u = (rng.random(N) + t * 0.04 * sp) % 1.0
        x = u * min(L, B.cut)
        hh = B.h(x)
        y = rng.random(N) * hh
        z = (rng.random(N) - 0.5) * B.d(x) * 0.9
        P = np.stack([ox + x, oy + y, oz + z], 1)
        al = 0.8 * B.alpha * np.exp(-B.disc * x) * np.sin(u * np.pi) ** 0.5
        particles3d(fr, cam, P, lerpc(B.col, WHITE, 0.6), al, 1)


def block_point(B, x, part='top', origin=(0, 0, 0)):
    """价值体上的锚点（用于标注引线）"""
    ox, oy, oz = origin
    h = float(B.h(np.array([x]))[0]); d = float(B.d(np.array([x]))[0])
    return {'top': (ox + x, oy + h, oz), 'front': (ox + x, oy + h * 0.5, oz + d / 2),
            'end': (ox + x, oy + h * 0.5, oz), 'base': (ox + x, oy, oz + d / 2)}[part]


def axis_arrow(fr, cam, p0, p1, col, a=1.0, th=3, label=None, size=40, prog=1.0):
    P, Z = cam.project(np.array([p0, p1]))
    if (Z < 0.5).any(): return
    q1 = P[0] + (P[1] - P[0]) * prog
    fr.arrow(tuple(P[0]), tuple(q1), col, a, th, 18)
    if label and prog > 0.6:
        d = P[1] - P[0]
        d = d / (np.linalg.norm(d) + 1e-6)
        fr.text(label, q1[0] + d[0] * 46, q1[1] + d[1] * 46, size, 'sans_black', col, a * cl((prog - 0.6) * 3), glow=0.3)
