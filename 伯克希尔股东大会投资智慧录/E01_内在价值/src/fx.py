"""电影感与科技感特效：后期（泛光、横向光晕、卡点推镜 / 闪光 / 色散）、透视网格、3D 粒子场、HUD 圆环、
粒子爆发、打字机文字、滚动计数、故障与碎裂。全部是时间 t 的纯函数（同一 t 永远得到同一帧）。"""
import math
import numpy as np, cv2
from gfx import W, H, GOLD, GOLD_HI, INK, INK2, INK3, BLUE, BRICK, cl, eo, eio, env, lerp, glow, line, circle, text, over, add

CYAN = np.array([0.45, 0.78, 1.0], np.float32)


# ---------------------------------------------------------------- 后期
def hit_env(t, hits, tau=0.32):
    """最近一个强重拍的衰减包络（0..1）"""
    e = 0.0
    for th, s in hits:
        if th <= t < th + 4 * tau:
            e = max(e, s * math.exp(-(t - th) / tau))
    return e


def beat_env(t, beats, tau=0.14):
    i = np.searchsorted(beats, t) - 1
    if i < 0: return 0.0
    return math.exp(-(t - beats[i]) / tau) if t - beats[i] < 0.6 else 0.0


def post(img, t, hits, bars, strength=1.0):
    """泛光 + 横向光晕 + 卡点推镜 / 闪光 / 色散。img 原地修改并返回新数组。"""
    # 泛光：亮部在 1/4 分辨率做两级模糊
    small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    bright = np.clip(small - 0.42, 0, None)
    b1 = cv2.GaussianBlur(bright, (0, 0), 3.0)
    b2 = cv2.GaussianBlur(cv2.resize(bright, (W // 16, H // 16), interpolation=cv2.INTER_AREA), (0, 0), 3.0)
    bloom = cv2.resize(b1 * 0.55 + cv2.resize(b2, (W // 4, H // 4), interpolation=cv2.INTER_LINEAR) * 0.9, (W, H),
                       interpolation=cv2.INTER_LINEAR)
    # 横向光晕（变形宽银幕镜头的拉丝），只取很亮的部分
    hot = np.clip(small - 0.72, 0, None).mean(2, keepdims=True)
    streak = cv2.GaussianBlur(hot, (0, 0), sigmaX=40, sigmaY=0.6)
    streak = cv2.resize(streak, (W, H), interpolation=cv2.INTER_LINEAR)[..., None] if streak.ndim == 2 else \
        cv2.resize(streak, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    out = img + bloom * 0.55 * strength + streak * np.array([0.55, 0.62, 0.8], np.float32) * 1.6 * strength
    e = hit_env(t, hits)
    be = beat_env(t, bars) * 0.35
    z = 1.0 + 0.042 * e + 0.006 * be
    if z > 1.0005:
        M = cv2.getRotationMatrix2D((W / 2, H * 0.47), 0, z)
        out = cv2.warpAffine(out, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if e > 0.02:
        out += np.array([1.0, 0.86, 0.62], np.float32) * 0.10 * e
        d = int(round(7 * e))
        if d >= 1:
            out[:, d:, 0] = out[:, :-d, 0].copy()
            out[:, :-d, 2] = out[:, d:, 2].copy()
    return out


# ---------------------------------------------------------------- 背景：透视网格 + 3D 粒子场 + 漏光
def grid_floor(img, t, a, horizon=1180, speed=0.35, col=None):
    if a <= 0.003: return
    col = GOLD * 0.75 if col is None else col
    vx = W / 2
    for k in range(-9, 10):                    # 汇聚到消失点的纵线
        x_bot = vx + k * 150
        line(img, (vx + k * 6, horizon), (x_bot, H), col, a * 0.10 * (1 - abs(k) / 11), 1)
    ph = (t * speed) % 1.0
    for i in range(14):                         # 向镜头移动的横线
        z = (i + 1 - ph) / 14.0
        y = horizon + (H - horizon) * (z ** 2.2)
        line(img, (0, y), (W, y), col, a * 0.11 * z, 1)
    line(img, (0, horizon), (W, horizon), col, a * 0.18, 1)


_rng = np.random.default_rng(21)
_STARS = np.c_[_rng.uniform(-1, 1, 160), _rng.uniform(-1, 1, 160), _rng.uniform(0.15, 1, 160)]


def starfield(img, t, a, speed=0.05, cy=900):
    """缓慢向镜头飘来的 3D 金色微粒（视差）"""
    if a <= 0.003: return
    for x, y, z0 in _STARS:
        z = (z0 - t * speed) % 1.0 + 0.08
        px, py = W / 2 + x * 520 / z, cy + y * 880 / z
        if 0 <= px < W and 0 <= py < H:
            s = min(1.0, 0.25 / z)
            glow(img, (px, py), 1.0 + 2.2 * s, GOLD_HI if z0 > 0.5 else CYAN, a * 0.35 * s * (1 - z))


def light_leak(img, t, a):
    if a <= 0.003: return
    cx = W * (0.15 + 0.7 * (0.5 + 0.5 * math.sin(t * 0.11)))
    cy = H * (0.2 + 0.1 * math.sin(t * 0.07))
    glow(img, (cx, cy), 380, np.array([1.0, 0.62, 0.25], np.float32) * 0.08, a)


def hud_ring(img, t, c, r, a, spin=0.25, ticks=72, col=None):
    """科技感 HUD 圆环：刻度 + 两段旋转弧"""
    if a <= 0.003: return
    col = GOLD if col is None else col
    for k in range(ticks):
        ang = k / ticks * 2 * math.pi + t * spin * 0.3
        L = 14 if k % 6 == 0 else 6
        p = (c[0] + r * math.cos(ang), c[1] + r * math.sin(ang))
        q = (c[0] + (r + L) * math.cos(ang), c[1] + (r + L) * math.sin(ang))
        line(img, p, q, col, a * (0.55 if k % 6 == 0 else 0.3), 1)
    for k, (span_, rr, sp) in enumerate(((1.2, r - 18, spin), (0.7, r + 30, -spin * 1.6))):
        a0 = t * sp + k * 2.1
        pts = [(c[0] + rr * math.cos(a0 + span_ * i / 30), c[1] + rr * math.sin(a0 + span_ * i / 30)) for i in range(31)]
        from gfx import poly
        poly(img, pts, CYAN if k else col, a * 0.7, 2)


def burst(img, t, t0, c, a=1.0, n=60, speed=520, life=1.3, seed=3, col=None):
    """粒子爆发（重拍时从中心向外炸开，带拖尾）"""
    dt = t - t0
    if dt < 0 or dt > life or a <= 0.003: return
    r = np.random.default_rng(seed)
    ang = r.uniform(0, 2 * math.pi, n); sp = r.uniform(0.3, 1.0, n) * speed
    k = 1 - (1 - dt / life) ** 2
    fade = (1 - dt / life) ** 1.5
    for i in range(n):
        d = sp[i] * k * 0.8
        p = (c[0] + d * math.cos(ang[i]), c[1] + d * math.sin(ang[i]))
        q = (c[0] + (d - 40 * fade) * math.cos(ang[i]), c[1] + (d - 40 * fade) * math.sin(ang[i]))
        line(img, q, p, col if col is not None else GOLD_HI, a * fade * 0.8, 1)
        glow(img, p, 2.2, col if col is not None else GOLD_HI, a * fade)


def sparks_up(img, t, x0, x1, ybase, a, n=40, seed=8):
    """向上升起的火花（数据柱生长时）"""
    if a <= 0.003: return
    r = np.random.default_rng(seed)
    P = r.random((n, 3))
    for i in range(n):
        ph = (t * (0.35 + 0.4 * P[i, 1]) + P[i, 2]) % 1.0
        x = x0 + (x1 - x0) * P[i, 0] + 6 * math.sin(t * 3 + i)
        y = ybase - ph * 420
        glow(img, (x, y), 1.6, GOLD_HI, a * (1 - ph) * 0.9)


# ---------------------------------------------------------------- 文字特效
def typewriter(img, s, x, y, size, name, col, a, t, t0, cps=26, anchor='m', cursor=True):
    n = int(cl((t - t0) * cps, 0, len(s)))
    if n <= 0 or a <= 0.003: return
    from gfx import text_w
    full = text_w(s, name, size)
    xl = x - full / 2 if anchor == 'm' else x
    text(img, s[:n], xl, y, size, name, col, a, 'l', shadow=0.5)
    if cursor and n < len(s) or (cursor and (t * 2) % 1 < 0.5 and t - t0 < len(s) / cps + 1.0):
        cx = xl + text_w(s[:n], name, size) + 4
        line(img, (cx, y - size * 0.45), (cx, y + size * 0.4), GOLD_HI, a, 2)


def slam(img, s, x, y, size, name, t, t0, a=1.0, gold=True, col=None, dur=0.35, glow_=0.3, track=0.0):
    """重拍砸入：从 1.45 倍缩到 1 倍，带闪光"""
    k = eo((t - t0) / dur)
    if k <= 0 or a <= 0.003: return
    sz = int(size * (1 + 0.45 * (1 - k)))
    text(img, s, x, y, sz, name, col if col is not None else INK, a * min(1, k * 1.6), 'm', gold=gold, glow=glow_ * (1 + 2 * (1 - k)),
         track=track)


def counter(v0, v1, k, fmt):
    return fmt(v0 + (v1 - v0) * eio(k))


def glitch(img, box, t, amt, seed=0):
    """横向错位 + RGB 分离的故障效果（只作用于 box 区域）"""
    if amt <= 0.01: return
    x0, y0, x1, y1 = [int(v) for v in box]
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    reg = img[y0:y1, x0:x1].copy()
    r = np.random.default_rng(int(t * 24) + seed)
    for _ in range(int(3 + 8 * amt)):
        ya = r.integers(0, max(1, reg.shape[0] - 8)); hh = r.integers(4, 26)
        sh = int(r.normal(0, 26 * amt))
        reg[ya:ya + hh] = np.roll(reg[ya:ya + hh], sh, axis=1)
    d = max(1, int(5 * amt))
    reg[:, d:, 0] = reg[:, :-d, 0]; reg[:, :-d, 2] = reg[:, d:, 2]
    img[y0:y1, x0:x1] = reg


def shards(img, t, t0, box, col, a=1.0, n=28, seed=5):
    """碎裂：矩形区域裂成碎片，受重力下坠、旋转、淡出"""
    dt = t - t0
    if dt < 0 or dt > 1.8 or a <= 0.003: return
    from gfx import poly
    x0, y0, x1, y1 = box
    r = np.random.default_rng(seed)
    cols, rows = 4, max(2, n // 4)
    w, h = (x1 - x0) / cols, (y1 - y0) / rows
    for i in range(cols):
        for j in range(rows):
            cx, cy = x0 + (i + 0.5) * w, y0 + (j + 0.5) * h
            vx, vy = r.normal(0, 140), r.uniform(-260, -40)
            rot = r.normal(0, 3)
            px, py = cx + vx * dt, cy + vy * dt + 900 * dt * dt
            ang = rot * dt
            pts = [(px + (dx * math.cos(ang) - dy * math.sin(ang)), py + (dx * math.sin(ang) + dy * math.cos(ang)))
                   for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]
            poly(img, pts, col, a * (1 - dt / 1.8), fill=True)


# ---------------------------------------------------------------- 3D 点阵球
def fib_sphere(n=260):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n); th = math.pi * (1 + 5 ** 0.5) * i
    return np.c_[np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)]


SPHERE = fib_sphere()


def sphere_points(t, c, R, tilt=0.35, spin=0.18):
    a = t * spin
    ca, sa, ct, st = math.cos(a), math.sin(a), math.cos(tilt), math.sin(tilt)
    x, y, z = SPHERE[:, 0], SPHERE[:, 1], SPHERE[:, 2]
    x1, z1 = x * ca + z * sa, -x * sa + z * ca
    y2, z2 = y * ct - z1 * st, y * st + z1 * ct
    persp = 1.9 / (2.6 - z2)
    return np.c_[c[0] + R * x1 * persp, c[1] + R * y2 * persp], z2, persp
