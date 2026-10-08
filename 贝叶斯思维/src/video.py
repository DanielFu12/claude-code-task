"""《贝叶斯思维》分镜与渲染。

python3 src/video.py preview 12.5 40.2 ...   → work/preview/t*.png
python3 src/video.py render                  → work/video.mp4（无声，4 进程并行）
"""
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "brand"))

import timeline as T  # noqa: E402
from engine import *  # noqa: E402,F401,F403
from engine import _SPR  # noqa: E402
import engine as E  # noqa: E402
import brand as _brand  # noqa: E402
from brand import Hud, load_logo  # noqa: E402

WORK = os.path.join(HERE, "..", "work")
FPS = T.FPS
HUD = Hud()
HIT_TIMES = sorted(T.HITS.values())
RNG = np.random.default_rng(1763)
T_NOW = [0.0]


def bar(n, b=0.0):
    return T.bar(n, b)


def since_hit(t):
    """距离最近一次（已发生的）重拍的时间"""
    d = [t - h for h in HIT_TIMES if t >= h]
    return min(d) if d else 99.0


def hit_k(t, tau=0.35):
    return math.exp(-since_hit(t) / tau)


# ================================================================ 背景
class Background:
    def __init__(self):
        r = np.random.default_rng(3)
        # 低频星云（两层），后面按章节着色
        def noise(sz, sig):
            n = r.normal(0, 1, (sz[1], sz[0])).astype(np.float32)
            n = cv2.GaussianBlur(n, (0, 0), sig)
            return (n - n.min()) / (n.max() - n.min())
        self.neb1 = noise((W // 4 + 200, H // 4 + 120), 22)
        self.neb2 = noise((W // 4 + 200, H // 4 + 120), 9)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - CX) / W) ** 2 + ((yy - CY * 0.92) / H) ** 2)
        self.base = (np.array([0.010, 0.013, 0.026], np.float32) +
                     np.exp(-d * 3.2)[..., None] * np.array([0.020, 0.026, 0.045], np.float32))
        n = 900
        self.star = np.c_[r.random(n) * W, r.random(n) * H]
        self.star_z = r.random(n) ** 2
        self.star_a = 0.10 + 0.5 * r.random(n) ** 3
        self.star_f = 0.5 + 2.5 * r.random(n)
        self.star_ph = r.random(n) * 6.28

    def tint(self, t):
        keys = [(0, (0.35, 0.55, 1.0)), (38, (0.35, 0.55, 1.0)), (41, (1.0, 0.78, 0.4)), (58, (0.5, 0.6, 1.0)),
                (61, (1.0, 0.8, 0.45)), (68, (0.35, 0.6, 1.0)), (100, (1.0, 0.78, 0.4)), (112, (0.9, 0.7, 0.45)),
                (135, (0.95, 0.45, 0.45)), (170, (1.0, 0.8, 0.45)), (190, (0.35, 0.85, 0.8)), (207, (0.4, 0.55, 1.0)),
                (222, (1.0, 0.78, 0.45)), (245, (0.5, 0.6, 1.0)), (250, (1.0, 0.8, 0.45)), (265, (0.45, 0.62, 1.0))]
        ts = [k[0] for k in keys]
        return np.array([np.interp(t, ts, [k[1][c] for k in keys]) for c in range(3)], np.float32)

    def draw(self, t, energy=1.0):
        out = self.base.copy()
        ox = int(100 + 60 * math.sin(t * 0.021)) % 200
        oy = int(60 + 40 * math.cos(t * 0.017)) % 120
        n1 = self.neb1[oy:oy + H // 4, ox:ox + W // 4]
        n2 = self.neb2[(oy * 2) % 120:(oy * 2) % 120 + H // 4, (ox * 3) % 200:(ox * 3) % 200 + W // 4]
        neb = np.clip(n1 * 1.4 - 0.55, 0, 1) ** 2 * 0.9 + np.clip(n2 - 0.5, 0, 1) * 0.35
        neb = cv2.resize(neb, (W, H), interpolation=cv2.INTER_CUBIC)
        out += neb[..., None] * self.tint(t) * 0.055 * energy
        # 星尘（视差缓慢漂移）
        P = self.star.copy()
        P[:, 0] = (P[:, 0] - t * (3 + 14 * self.star_z)) % W
        P[:, 1] = (P[:, 1] + np.sin(t * 0.1 + self.star_ph) * 4) % H
        tw = self.star_a * (0.6 + 0.4 * np.sin(self.star_f * t + self.star_ph))
        splat(out, P, tw[:, None] * np.array([0.8, 0.85, 1.0], np.float32) * 0.6)
        return out


BG = None

# ================================================================ 通用部件
TITLE_GRAD = [(0.0, (255, 243, 200)), (0.35, (255, 212, 120)), (0.62, (226, 160, 60)), (1.0, (255, 214, 130))]


def narration(out, t):
    for (t0, t1, s) in T.NARRATION:
        if t0 - 0.1 <= t <= t1 + 0.1:
            anim_text(out, s, CX, 972, 34, t, t0, t1, "serif_med", INK, track=0.06, fin=0.6, fout=0.4, rise_px=10,
                      blur_px=5)


def chapter_tag(out, lay, t):
    for (c0, c1, num, name, en) in T.CHAPTERS:
        if c0 <= t < c1:
            a = window(t, c0 + 0.6, c1, 1.0, 0.6)
            if t > T.LOGO_GATHER - 1:
                a *= clip01((T.LOGO_GATHER - t) / 1.0)
            if a <= 0:
                return
            text(out, num, 64, 58, 30, "inter_light", GOLD, a * 0.9, "l", track=0.05)
            text(out, name, 112, 56, 22, "serif_med", INK, a * 0.85, "l", track=0.25)
            text(out, en, 112, 84, 11, "inter_semi", GREY, a * 0.7, "l", track=0.32)
            line(lay, (64, 104), (64 + 60 * float(eout(prog(t, c0 + 0.6, 1.2))), 104), GOLD, 0.5 * a, 1)


def progress_bar(out, lay, t):
    a = clip01(t / 2.0) * clip01((T.LOGO_GATHER - t) / 1.0)
    if a <= 0:
        return
    x0, x1, y = 64, W - 64, 1046
    line(lay, (x0, y), (x1, y), WHITE, 0.08 * a, 1)
    xp = x0 + (x1 - x0) * t / T.DUR
    line(lay, (x0, y), (xp, y), GOLD, 0.35 * a, 1)
    for (c0, *_rest) in T.CHAPTERS:
        x = x0 + (x1 - x0) * c0 / T.DUR
        line(lay, (x, y - 4), (x, y + 4), GOLD if t >= c0 else WHITE, (0.5 if t >= c0 else 0.15) * a, 1)
    circle(lay, (xp, y), 2.5, GOLD, 0.9 * a)


def shockwave(lay, c, t, t0, color=GOLD, rmax=900, dur=1.2, k=1.0):
    u = (t - t0) / dur
    if 0 <= u <= 1:
        r = 20 + rmax * eout(u, 3)
        a = (1 - u) ** 2 * k
        circle(lay, c, r, color, 0.6 * a, th=3 + 10 * (1 - u))
        circle(lay, c, r * 0.82, color, 0.25 * a, th=2)


def frac_text(out, num, den, x, y, size, color, alpha=1.0, fname="inter_thin", glow_buf=None, glow=0.0):
    """大号分数：num / den，斜线"""
    sp1 = text_sprite(num, fname, size, color)
    sp2 = text_sprite(den, fname, size, color)
    gap = size * 0.18
    w1, w2 = sp1.w - 2 * sp1.ox, sp2.w - 2 * sp2.ox
    tot = w1 + w2 + gap * 2 + size * 0.3
    xa = x - tot / 2
    blit(out, sp1, xa + w1 / 2, y - size * 0.18, alpha)
    blit(out, sp2, xa + tot - w2 / 2, y + size * 0.22, alpha)
    xs = xa + w1 + gap
    line(out, (xs, y + size * 0.48), (xs + size * 0.3, y - size * 0.46), color, alpha, max(1.5, size / 60), "over")
    if glow_buf is not None and glow > 0:
        blit(glow_buf, sp1, xa + w1 / 2, y - size * 0.18, alpha * glow, mode="add")
        blit(glow_buf, sp2, xa + tot - w2 / 2, y + size * 0.22, alpha * glow, mode="add")


# ================================================================ 三扇门（3D 门板）
FOCAL = 1500.0


def door_geom(cx, base_y, w, h, theta):
    """门板绕左侧铰链向观众转开 theta（弧度）。返回门框四点与门板四点"""
    xl, xr = cx - w / 2, cx + w / 2
    yt, yb = base_y - h, base_y
    ymid = (yt + yb) / 2
    frame = np.array([[xl, yt], [xr, yt], [xr, yb], [xl, yb]])
    dz = w * math.sin(theta)                       # 向观众靠近
    s = FOCAL / (FOCAL - dz)
    xf = xl + w * math.cos(theta) * s + (xl - CX) * (s - 1)
    panel = np.array([[xl, yt], [xf, ymid + (yt - ymid) * s], [xf, ymid + (yb - ymid) * s], [xl, yb]])
    return frame, panel


def draw_door(out, lay, cx, base_y, w, h, theta, num, alpha=1.0, frame_col=GOLD, frame_k=0.6, inside=None,
              inside_k=0.0, fill=0.0, fill_col=GOLD, label_a=1.0, draw_k=1.0, num_size=None):
    """inside: ('goat'|'car', 颜色)；fill: 门内概率光柱高度 0..1"""
    if alpha <= 0.003:
        return
    frame, panel = door_geom(cx, base_y, w, h, theta)
    xl, yt, xr, yb = frame[0, 0], frame[0, 1], frame[1, 0], frame[2, 1]
    # 门洞：内部（门打开后可见）
    open_k = clip01(theta / 0.6)
    if inside is not None and open_k > 0:
        kind, col = inside
        glow_rect(lay, xl + 6, yt + 6, xr - 6, yb - 6, col, 0.06 * open_k * alpha * inside_k, 22)
        poly(out, frame, np.array([0.02, 0.025, 0.04]) + col * 0.04, alpha * open_k)
        sp = icon(kind, h * (0.2 if kind == "car" else 0.42), col * 0.48)
        blit_icon(out, sp, cx, base_y - h * 0.32, alpha * open_k * inside_k)
        blit_icon(lay, sp, cx, base_y - h * 0.32, alpha * open_k * inside_k * 0.12, mode="add")
    # 概率光柱（液态光：底部更亮，液面一条亮线，带轻微波动）
    if fill > 0.001:
        fh = (h - 12) * fill
        ytop = yb - 6 - fh
        n = 24
        xs = np.linspace(xl + 6, xr - 6, n)
        wave = 2.2 * np.sin(xs * 0.05 + T_NOW[0] * 3.0) * min(1.0, fill * 6)
        surf = np.c_[xs, ytop + wave]
        body = np.vstack([surf, [[xr - 6, yb - 6], [xl + 6, yb - 6]]])
        poly(out, body, fill_col * 0.16, alpha, mode="add")
        glow_rect(lay, xl + 8, ytop + fh * 0.35, xr - 8, yb - 6, fill_col, 0.10 * alpha, 10)
        polyline(lay, surf, fill_col, 0.95 * alpha, 2.0)
        glow_rect(lay, xl + 6, ytop - 2, xr - 6, ytop + 2, fill_col, 0.35 * alpha, 6)
    # 门框（描边动画）
    per = np.vstack([frame[3], frame[0], frame[1], frame[2]])
    pp = path_partial(per, draw_k)
    polyline(lay, pp, frame_col, alpha * frame_k, 2.0)
    polyline(out, pp, frame_col * 0.9, alpha * min(1, frame_k * 1.2), 1.2, mode="over")
    # 门板
    if draw_k >= 1:
        shade = 0.55 + 0.45 * math.cos(theta)
        pa = alpha * clip01((draw_k - 0.6) / 0.4) if draw_k < 1 else alpha
        poly(out, panel, np.array([0.035, 0.042, 0.068]) * shade * 1.4 + 0.005, pa * (0.96 if fill <= 0 else 0.45))
        polyline(lay, panel, frame_col * 0.8, pa * frame_k * 0.55 * shade, 1.5, closed=True)
        # 门板内框与门把
        inset = 0.12
        q = panel
        def P(u, v):
            top = q[0] + (q[1] - q[0]) * u
            bot = q[3] + (q[2] - q[3]) * u
            return top + (bot - top) * v
        inner = np.array([P(inset, 0.06), P(1 - inset, 0.06), P(1 - inset, 0.94), P(inset, 0.94)])
        polyline(out, inner, frame_col * 0.35 * shade, pa * 0.8, 1.0, closed=True)
        hx, hy = P(0.86, 0.55)
        circle(lay, (hx, hy), 4 * (0.6 + 0.4 * shade), frame_col, pa * 0.7)
        if num is not None and label_a > 0 and theta < 0.9:
            cx_, cy_ = P(0.5, 0.36)
            sc = (q[1][0] - q[0][0]) / w
            text(out, str(num), cx_, cy_, num_size or h * 0.2, "inter_thin", frame_col * 0.95 + 0.05,
                 pa * label_a * clip01(sc * 1.4), scale=max(0.05, min(1.0, abs(sc))))


# ---------------------------------------------------------------- 场景 1：三扇门（0–47.5）
D3_X = [600, 960, 1320]
D3_Y = 780
D3_W, D3_H = 230, 380


_BEAM = None


def beam(lay, cx, top_y, bot_y, col, k):
    """舞台顶光：上窄下宽的柔和光锥"""
    global _BEAM
    if k <= 0.003:
        return
    if _BEAM is None:
        bh, bw = 520, 420
        yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
        v = yy / bh
        half = 18 + v * 150
        m = np.clip((half - np.abs(xx - bw / 2)) / 30, 0, 1)
        m *= (v ** 0.8) * (1 - 0.35 * v)
        _BEAM = cv2.GaussianBlur(m, (0, 0), 6)
    hgt = int(bot_y - top_y)
    b = cv2.resize(_BEAM, (_BEAM.shape[1], hgt))
    composite(lay, np.broadcast_to(np.asarray(col, np.float32), b.shape + (3,)), b * k, cx - b.shape[1] / 2,
              top_y, "add")


def floor_grid(lay, t, a):
    if a <= 0:
        return
    vy = 420
    for i in range(-12, 13):
        x = CX + i * 160
        line(lay, (CX + (x - CX) * 0.08, vy + 30), (CX + (x - CX) * 3.2, H + 200), BLUE, 0.05 * a, 1)
    for k in range(8):
        u = ((k + (t * 0.15) % 1) / 8) ** 2
        y = D3_Y + 4 + u * 420
        line(lay, (0, y), (W, y), BLUE, 0.06 * a * (1 - u * 0.6), 1)
    line(lay, (180, D3_Y + 2), (W - 180, D3_Y + 2), GOLD, 0.22 * a, 1)


def scene_doors(out, lay, t):
    if t > 47.5:
        return
    A = clip01((47.2 - t) / 0.9)
    floor_grid(lay, t, A * clip01((t - 0.5) / 2))
    # 镜头：开场缓慢推近
    sel = prog(t, 10.0, 0.8)
    pulse2 = 0.5 + 0.5 * math.sin((t - 20) * math.pi / T.BEAT / 2) if 21 <= t < 30 else 0
    # 每扇门的状态
    for i in range(3):
        cx = D3_X[i]
        draw_k = float(ease(prog(t, 0.8 + i * 0.35, 2.0)))
        theta = 0.0
        inside = None
        inside_k = 0.0
        frame_col, fk = GOLD, 0.55
        if i == 2:
            theta = 1.75 * eback(prog(t, bar(7) - 0.15, 1.0), 0.9)
            inside = ("goat", np.array([0.75, 0.82, 1.0]))
            inside_k = eout(prog(t, bar(7), 0.8))
            frame_col = mixc(GOLD, BLUE, eout(prog(t, bar(7), 0.6)))
        if i == 0:
            fk = 0.55 + 0.6 * sel
        if i == 1:
            fk = 0.55 + 0.5 * pulse2 * (1 - prog(t, 29.0, 1.0))
        # 概率光柱：直觉 50/50 → 揭晓 1/3 vs 2/3
        fill, fcol = 0.0, GOLD
        if i < 2 and t >= 30.2:
            f50 = 0.5 * eout(prog(t, 30.4 + 0.3 * i, 1.2))
            if t < T.HITS["reveal"]:
                fill, fcol = f50, CORAL
                if t > 37.5:   # 裂开、抖动
                    fill *= 1 + 0.06 * math.sin(t * 70 + i * 2) * prog(t, 37.5, 1.5)
            else:
                u = eback(prog(t, T.HITS["reveal"], 0.9), 1.2)
                target = 1 / 3 if i == 0 else 2 / 3
                fill = 0.5 + (target - 0.5) * u
                fcol = mixc(CORAL, GREY * 1.1 if i == 0 else GOLD, eout(prog(t, T.HITS["reveal"], 0.5)))
        a = A
        if 39.4 <= t < 40:
            a *= 0.35
        bk = clip01((t - 1.5 - i * 0.35) / 1.5) * 0.16 * (1 + 1.2 * (fk - 0.55))
        beam(lay, cx, D3_Y - 640, D3_Y + 10, mixc(GOLD, frame_col, 0.5), bk * a)
        draw_door(out, lay, cx, D3_Y, D3_W, D3_H, theta, i + 1, a, frame_col, fk, inside, inside_k, fill, fcol,
                  draw_k=draw_k)
        # 镜面倒影
        if draw_k > 0.9:
            glow_rect(lay, cx - D3_W / 2, D3_Y + 4, cx + D3_W / 2, D3_Y + 40, frame_col, 0.025 * fk * a, 14)
    # x 光：门后藏着什么（5.4–9.4）
    xr = window(t, 5.3, 9.4, 0.6, 0.8)
    if xr > 0:
        perm = [(0, 1, 2), (1, 2, 0), (2, 0, 1), (1, 0, 2), (0, 2, 1)]
        k = int((t - 5.3) / T.BEAT) % len(perm)
        car_at = perm[k][0]
        for i in range(3):
            kind = "car" if i == car_at else "goat"
            col = GOLD if kind == "car" else np.array([0.7, 0.78, 0.95])
            sp = icon(kind, 54 if kind == "car" else 96, col)
            blit_icon(out, sp, D3_X[i], D3_Y - D3_H * 0.36, xr * 0.5)
            blit_icon(lay, sp, D3_X[i], D3_Y - D3_H * 0.36, xr * 0.1, mode="add")
    # 三扇门上方小标签
    a = window(t, 1.2, 4.6, 0.8, 0.6)
    if a > 0:
        anim_text(out, "三扇门", CX, 250, 92, t, 1.0, 4.6, "serif_bold", INK, track=0.5, fin=1.2, glow=0.3,
                  glow_buf=lay)
        anim_text(out, "THE MONTY HALL PROBLEM", CX, 330, 16, t, 1.6, 4.6, "inter_semi", GREY, track=0.6)
    # 你的选择
    a = window(t, 10.0, 46.5, 0.6, 1.0)
    if a > 0:
        y = D3_Y + 52
        text(out, "你的选择", D3_X[0], y, 22, "serif_med", GOLD, a * 0.95, track=0.3)
        tri_y = D3_Y - D3_H - 34 - 10 * (1 - eout(prog(t, 10.0, 0.6)))
        poly(out, [(D3_X[0] - 9, tri_y - 8), (D3_X[0] + 9, tri_y - 8), (D3_X[0], tri_y + 6)], GOLD,
             a * clip01((29.6 - t) / 0.5))
        glow_spot(lay, (D3_X[0], D3_Y + 10), 60, GOLD, 0.18 * a)
    a = window(t, bar(7) + 0.4, 46.5, 0.6, 1.0)
    if a > 0:
        text(out, "山羊", D3_X[2], D3_Y + 52, 22, "serif_med", np.array([0.7, 0.78, 0.95]), a * 0.9, track=0.3)
    # 换门的弧线箭头（20.6–29.5）
    k = eout(prog(t, 20.6, 1.2))
    a = window(t, 20.6, 30.4, 0.3, 0.6)
    if a > 0 and k > 0:
        x0, x1 = D3_X[0] + 30, D3_X[1] - 30
        top = D3_Y - D3_H - 70
        us = np.linspace(0, 1, 60)
        pts = np.c_[x0 + (x1 - x0) * us, D3_Y - D3_H - 20 - (top - (D3_Y - D3_H - 20)) * -1 * np.sin(us * math.pi)]
        pts[:, 1] = D3_Y - D3_H - 20 - 70 * np.sin(us * math.pi)
        pp = path_partial(pts, k)
        polyline(lay, pp, GOLD, 0.8 * a, 2)
        polyline(out, pp, GOLD, 0.8 * a, 1.5, mode="over")
        if k > 0.98:
            e = pts[-1]
            poly(out, [(e[0] + 2, e[1] + 8), (e[0] - 12, e[1] - 6), (e[0] + 6, e[1] - 10)], GOLD, a)
        text(out, "换？", CX - 180, D3_Y - D3_H - 112, 26, "serif_med", GOLD, a * k)
    # 换，还是不换？
    anim_text(out, "换，还是不换？", CX, 200, 64, t, 25.0, 29.6, "serif_bold", INK, track=0.3, glow=0.25,
              glow_buf=lay)
    # 50% / 50%（直觉）
    a = window(t, 30.6, T.HITS["reveal"], 0.6, 0.05)
    if a > 0:
        jit = prog(t, 37.5, 1.6)
        for i in range(2):
            dx = (RNG.random() - 0.5) * 18 * jit if jit > 0 else 0
            text(out, "50%", D3_X[i] + dx, D3_Y - D3_H - 60, 76, "inter_thin", CORAL, a * (1 - 0.5 * jit * (RNG.random() > 0.5)))
        for i in range(2):
            text(out, "直觉", D3_X[i], D3_Y - D3_H - 132, 22, "serif_med", CORAL, a * 0.85, track=0.4)
    anim_text(out, "真的吗？", CX, 200, 56, t, 35.2, 39.3, "serif_bold", INK, track=0.3, glow=0.2, glow_buf=lay)
    # 揭晓：2/3
    if t >= T.HITS["reveal"]:
        u = prog(t, T.HITS["reveal"], 0.7)
        a = eout(u) * A
        text(out, "1/3", D3_X[0], D3_Y - D3_H - 64, 76, "inter_thin", GREY * 1.25, a * 0.95)
        text(out, "2/3", D3_X[1], D3_Y - D3_H - 76, 120, "inter_light", GOLD, a, glow=0.5, glow_buf=lay)
        text(out, "坚持", D3_X[0], D3_Y - D3_H - 132, 22, "serif_med", GREY, a * 0.9, track=0.4)
        text(out, "换门", D3_X[1], D3_Y - D3_H - 164, 24, "serif_med", GOLD, a, track=0.4)
        shockwave(lay, (D3_X[1], D3_Y - D3_H / 2), t, T.HITS["reveal"], GOLD, 1100, 1.4)
        glow_spot(lay, (D3_X[1], D3_Y - D3_H / 2), 170, GOLD, 0.16 * a * (0.6 + 0.4 * hit_k(t, 0.8)))


# ================================================================ 粒子工具
def text_points(s, fname, size, cx, cy, n, rng, track=0.0, anchor="c"):
    sp = text_sprite(s, fname, size, INK, track)
    pts, pick, _ = mask_points(sp.a, n, rng, 0.35)
    x0 = cx - sp.w / 2 if anchor == "c" else cx - sp.ox
    y0 = cy - sp.oy + 0.38 * (sp.oy - sp.ox)
    return pts + [x0, y0]


def morph(P0, P1, u, R, swirl=0.25, spread=0.35):
    """P0 → P1，u 0..1；R 每个粒子的随机数（延迟 / 旋涡方向）"""
    p = ease(clip01((u - R[:, 0] * spread) / (1 - spread)))
    d = P1 - P0
    nrm = np.c_[-d[:, 1], d[:, 0]]
    curl = (np.sin(np.pi * p) * (R[:, 1] - 0.5) * 2 * swirl)[:, None]
    return P0 + d * p[:, None] + nrm * curl, p


_MATH = {}


def math_sprite(tex, px, color=INK):
    key = (tex, int(px), tuple(np.round(color, 3)))
    if key not in _MATH:
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        fig = Figure(figsize=(12, 3), dpi=100)
        fig.patch.set_alpha(0)
        FigureCanvasAgg(fig)
        fig.text(0.02, 0.35, f"${tex}$", fontsize=px * 72 / 100, color="white", math_fontfamily="stix")
        fig.canvas.draw()
        a = np.asarray(fig.canvas.buffer_rgba())[..., 3].astype(np.float32) / 255
        ys, xs = np.where(a > 0.01)
        a = np.pad(a[ys.min():ys.max() + 1, xs.min():xs.max() + 1], 4)
        sp = Sprite(np.broadcast_to(np.asarray(color, np.float32), a.shape + (3,)).copy(), a)
        sp.ox, sp.oy = sp.w / 2, sp.h / 2
        _MATH[key] = sp
    return _MATH[key]


def blit_c(out, sp, x, y, alpha=1.0, mode="over", scale=1.0, blur=0.0):
    """以精灵几何中心对齐"""
    a, col = sp.a, sp.rgb
    if scale != 1.0:
        nw, nh = max(1, int(sp.w * scale)), max(1, int(sp.h * scale))
        a = cv2.resize(a, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
        col = cv2.resize(np.ascontiguousarray(col), (nw, nh))
    if blur > 0.3:
        a = cv2.GaussianBlur(a, (0, 0), blur)
    composite(out, col, a * alpha, x - a.shape[1] / 2, y - a.shape[0] / 2, mode)


def fmt(n):
    return f"{int(round(n)):,}"


# ================================================================ 场景 2：1990 年的风波（46.5–60）
ENV_N = 24 * 14
_er = np.random.default_rng(90)
ENV_GRID = np.array([[1090 + (i % 24) * 30 + (i // 24 % 2) * 6, 250 + (i // 24) * 36] for i in range(ENV_N)], float)
ENV_FROM = np.c_[np.where(_er.random(ENV_N) < 0.5, -100, W + 100) * 0 + W + 80 + _er.random(ENV_N) * 400,
                 _er.random(ENV_N) * H * 1.4 - H * 0.2]
ENV_T = 50.9 + np.sort(_er.random(ENV_N)) ** 0.7 * 2.6
ENV_PHD = _er.random(ENV_N) < 0.1
ENV_ROT = (_er.random(ENV_N) - 0.5) * 1.2


def scene_history(out, lay, t):
    if not (46.4 <= t <= 60.3):
        return
    A = clip01((59.4 - t) / 0.35) if t < 60 else 0
    if A <= 0:
        return
    # 1990
    a = window(t, 47.1, 59.4, 1.0, 0.4)
    if a > 0:
        sc = 1 + 0.03 * prog(t, 46.7, 13)
        anim_text(out, "1990", 520, 340, 190, t, 47.1, 59.4, "inter_thin", GOLD, gradient=TITLE_GRAD, fin=1.2,
                  track=0.04, glow=0.25, glow_buf=lay, blur_px=10)
        anim_text(out, "《Parade》杂志 ·「Ask Marilyn」专栏", 520, 470, 26, t, 47.3, 55.0, "serif_med", GREY,
                  track=0.12)
        anim_text(out, "专栏作家的答案：【应该换门】", 520, 520, 26, t, 48.3, 55.0, "serif_med", INK, track=0.12)
    # 计数器
    a = window(t, 51.0, 55.1, 0.5, 0.4)
    if a > 0:
        k = eout(prog(t, 51.0, 2.4), 3)
        text(out, "≈ " + fmt(10000 * k), 520, 640, 64, "inter_light", INK, a)
        text(out, "封读者来信，大多认为她错了", 520, 704, 22, "serif_med", GREY, a, track=0.2)
        a2 = window(t, 52.8, 55.1, 0.5, 0.4)
        text(out, "≈ " + fmt(1000 * eout(prog(t, 52.8, 1.6), 3)), 520, 790, 46, "inter_light", GOLD, a2)
        text(out, "封来自博士", 520, 840, 22, "serif_med", GOLD, a2 * 0.9, track=0.2)
    # 埃尔德什
    a = window(t, 55.4, 59.4, 0.7, 0.4)
    if a > 0:
        anim_text(out, "保罗·埃尔德什", 520, 640, 52, t, 55.4, 59.4, "serif_bold", INK, track=0.15)
        anim_text(out, "PAUL ERDŐS · 1913–1996", 520, 704, 18, t, 55.7, 59.4, "inter_semi", GREY, track=0.4)
        anim_text(out, "一生发表约 1500 篇论文的数学家", 520, 770, 24, t, 56.1, 59.4, "serif_med", GREY, track=0.12)
    # 信封墙
    if t >= 50.9:
        k_out = prog(t, 55.0, 1.2)
        for i in range(ENV_N):
            u = (t - ENV_T[i]) / 0.9
            if u <= 0:
                continue
            e = eout(min(u, 1), 3)
            p = ENV_FROM[i] + (ENV_GRID[i] - ENV_FROM[i]) * e
            col = GOLD if (ENV_PHD[i] and t > 52.8) else np.array([0.75, 0.8, 0.92])
            al = (0.85 if col is GOLD else 0.55) * (1 - k_out) * A
            if al <= 0.003:
                continue
            if k_out > 0:   # 散成"模拟数据流"
                p = p + np.array([0, -60 * ein(k_out, 2) * ((i % 7) - 3) / 3])
            sp = icon("envelope", 18, col)
            blit_icon(out, sp, p[0], p[1], al * clip01(u * 3))
            if ENV_PHD[i] and t > 52.8:
                blit_icon(lay, sp, p[0], p[1], 0.3 * al, mode="add")
    # 计算机模拟：字符流
    a = window(t, 56.3, 59.4, 0.6, 0.3)
    if a > 0:
        r = np.random.default_rng(int(t * 12))
        for row in range(12):
            y = 260 + row * 44
            s = " ".join("赢" if r.random() < 2 / 3 else "输" for _ in range(14))
            al = a * (0.15 + 0.5 * (row == int(t * 8) % 12))
            text(out, s, 1450, y, 24, "sans_light", GOLD if row % 3 == 0 else GREY, al)
        text(out, "> 计算机模拟：换门，胜率 2/3", 1450, 820, 24, "sans_reg", TEAL, a, track=0.05)


# ================================================================ 场景 3：标题（60–67.5）
TITLE_N = 9000
_tr = np.random.default_rng(60)
TITLE_PTS = None
TITLE_R = _tr.random((TITLE_N, 3))
TITLE_FROM = None


def _title_init():
    global TITLE_PTS, TITLE_FROM
    if TITLE_PTS is None:
        TITLE_PTS = text_points("贝叶斯思维", "serif_black", 168, CX, 470, TITLE_N, _tr, track=0.12)
        ang = _tr.random(TITLE_N) * 6.283
        rad = 40 + _tr.random(TITLE_N) ** 0.5 * 1100
        TITLE_FROM = np.c_[CX + np.cos(ang) * rad, 470 + np.sin(ang) * rad * 0.6]


_RAYS = None


def rays(lay, c, k, rot, color):
    global _RAYS
    if k <= 0.003:
        return
    if _RAYS is None:
        r = np.random.default_rng(8)
        yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
        ang = np.arctan2(yy - H / 4, xx - W / 4)
        d = np.hypot(yy - H / 4, xx - W / 4) / (W / 4)
        fr = np.zeros_like(ang)
        for f, a in zip(r.integers(5, 40, 9), r.random(9)):
            fr += a * np.cos(ang * f + r.random() * 6)
        _RAYS = (ang, d, fr)
    ang, d, fr = _RAYS
    v = np.clip(fr * 0.5 + 0.2 * np.cos(ang * 23 + rot * 3), 0, None) * np.exp(-d * 1.6) * (1 - np.exp(-d * 12))
    big = cv2.resize(v.astype(np.float32), (W, H))
    M = np.float32([[1, 0, c[0] - CX], [0, 1, c[1] - CY]])
    big = cv2.warpAffine(big, M, (W, H))
    lay += big[..., None] * np.asarray(color, np.float32) * k


def scene_title(out, lay, t):
    T0 = T.HITS["title"]
    if not (T0 - 0.05 <= t <= 68.2):
        return
    _title_init()
    u = prog(t, T0, 1.5)
    P, p = morph(TITLE_FROM, TITLE_PTS, u, TITLE_R, 0.35, 0.4)
    k_out = prog(t, 66.6, 1.2)
    if k_out > 0:
        dirv = TITLE_PTS - [CX, 470]
        P = P + dirv * ein(k_out, 2) * (0.6 + TITLE_R[:, 2:3]) * 1.5 + np.c_[np.zeros(TITLE_N), -200 * ein(k_out, 2) * TITLE_R[:, 1]]
    crisp = eout(prog(t, T0 + 1.0, 0.8)) * (1 - ein(k_out, 1.5))
    pa = (0.5 + 0.5 * (1 - p)) * (1 - crisp * 0.75) * (1 - k_out)
    col = mixc(np.array([1.0, 0.95, 0.85]), GOLD, TITLE_R[:, 2:3])
    dots(lay, P, col * (pa * 0.32)[:, None], 1.0)
    rays(lay, (CX, 470), 0.12 * eout(prog(t, T0, 0.5)) * (1 - prog(t, 64.5, 3)), t * 0.05, GOLD)
    glow_spot(lay, (CX, 470), 380, GOLD, 0.07 * eout(prog(t, T0, 0.6)) * (1 - k_out))
    if crisp > 0:
        text(out, "贝叶斯思维", CX, 470, 168, "serif_black", GOLD, crisp, track=0.12, gradient=TITLE_GRAD,
             blur=3 * (1 - crisp), glow=0.12, glow_buf=lay)
    anim_text(out, "BAYESIAN  THINKING", CX, 610, 34, t, T0 + 1.4, 67.2, "corm6", np.array([0.84, 0.70, 0.44]),
              track=0.55, fin=1.0)
    anim_text(out, "一场关于【改变想法】的认知之旅", CX, 690, 30, t, T0 + 2.2, 67.2, "serif_light", INK, track=0.3,
              fin=1.0)
    shockwave(lay, (CX, 470), t, T0, GOLD, 1300, 1.6, 1.2)


# ================================================================ 场景 4：计算机模拟 3000 局（67.5–82.5）
SIM_N = 3000
_sr = np.random.default_rng(1990)
SIM_CAR = _sr.integers(0, 3, SIM_N)
SIM_PICK = _sr.integers(0, 3, SIM_N)
SIM_STAY = (SIM_CAR == SIM_PICK).astype(np.int64)
SIM_CUM = np.cumsum(SIM_STAY)
SIM_T0, SIM_T1 = 69.0, T.HITS["sim"]
SIM_L, SIM_R = 560, 1360
CH_X0, CH_X1, CH_Y0, CH_Y1 = 330, 1590, 560, 840


def sim_games(t):
    u = clip01((t - SIM_T0) / (SIM_T1 - SIM_T0))
    return float(SIM_N * u ** 2.6)


def game_time(i):
    return SIM_T0 + (SIM_T1 - SIM_T0) * ((i + 1) / SIM_N) ** (1 / 2.6)


def chart_xy(i, p):
    x = CH_X0 + (CH_X1 - CH_X0) * math.log10(max(i, 1)) / math.log10(SIM_N) if np.isscalar(i) else \
        CH_X0 + (CH_X1 - CH_X0) * np.log10(np.maximum(i, 1)) / math.log10(SIM_N)
    return x, CH_Y1 - (CH_Y1 - CH_Y0) * p


def scene_sim(out, lay, t):
    if not (67.3 <= t <= 84.5):
        return
    A = window(t, 67.6, 83.1, 0.8, 0.7)
    n = sim_games(t)
    ni = int(n)
    stay_w = int(SIM_CUM[ni - 1]) if ni > 0 else 0
    sw_w = ni - stay_w
    hk = hit_k(t, 0.5) if t >= SIM_T1 else 0
    for x, name, wins, col in ((SIM_L, "坚持不换", stay_w, BLUE), (SIM_R, "换门", sw_w, GOLD)):
        anim_text(out, name, x, 226, 30, t, 67.8, 83.1, "serif_bold", col if col is GOLD else INK, track=0.3)
        pct = wins / ni * 100 if ni > 0 else 0.0
        a = A * clip01((t - 68.6) / 0.5)
        text(out, f"{pct:.1f}%", x, 320, 104, "inter_light", col, a, glow=0.3 + 0.6 * hk, glow_buf=lay)
        bw = 520
        x0 = x - bw / 2
        rect(out, x0, 412, x0 + bw, 420, WHITE * 0.12, a, r=4)
        if ni > 0:
            fw = bw * wins / ni
            rect(out, x0, 412, x0 + fw, 420, col, a, r=4)
            glow_rect(lay, x0, 412, x0 + fw, 420, col, 0.2 * a, 6)
        text(out, f"赢 {fmt(wins)}   ·   输 {fmt(ni - wins)}", x, 456, 22, "sans_light", GREY, a, track=0.05)
    # 中间：局数
    a = A * clip01((t - 68.6) / 0.5)
    text(out, fmt(max(ni, 0)), CX, 318, 46, "inter_light", INK, a * 0.9)
    text(out, "局", CX, 368, 20, "serif_med", GREY, a * 0.8, track=0.3)
    # 飞行粒子：每局两个
    if SIM_T0 <= t <= SIM_T1 + 0.6:
        lo = max(0, int(sim_games(t - 0.45)) - 1)
        idx = np.arange(lo, min(ni + 1, SIM_N))
        if len(idx) > 400:
            idx = idx[np.linspace(0, len(idx) - 1, 400).astype(int)]
        if len(idx):
            gt = np.array([game_time(i) for i in idx])
            u = clip01((t - gt) / 0.45)
            ok = (u > 0) & (u < 1)
            idx, u = idx[ok], u[ok]
            for side, x, col in ((0, SIM_L, BLUE), (1, SIM_R, GOLD)):
                win = SIM_STAY[idx] == (1 if side == 0 else 0)
                tx = np.where(win, x - 160, x + 160)
                ty = np.full(len(idx), 416.0)
                e = eout(u, 2)
                px = CX + (tx - CX) * e
                py = 380 + (ty - 380) * e - np.sin(u * math.pi) * 80
                c = np.where(win[:, None], col[None, :], np.array([[0.5, 0.52, 0.6]]))
                dots(lay, np.c_[px, py], c * 0.9, 1.4)
    # 折线图（对数横轴）
    a = A * clip01((t - 68.8) / 0.6)
    if a > 0:
        line(out, (CH_X0, CH_Y1), (CH_X1, CH_Y1), WHITE, 0.25 * a, 1, "over")
        for frac, lab in ((1 / 3, "1/3"), (2 / 3, "2/3")):
            _, y = chart_xy(1, frac)
            dashed(out, (CH_X0, y), (CH_X1, y), WHITE, 0.22 * a, 1, 6, 6, mode="over")
            text(out, lab, CH_X1 + 34, y, 22, "inter_light", GREY, a)
        for g in (1, 10, 100, 1000, 3000):
            x, _ = chart_xy(g, 0)
            line(out, (x, CH_Y1), (x, CH_Y1 + 6), WHITE, 0.3 * a, 1, "over")
            text(out, fmt(g), x, CH_Y1 + 26, 16, "inter_light", GREY, a * 0.8)
        text(out, "局数（对数刻度）", CH_X0, CH_Y1 + 58, 16, "sans_light", GREY, a * 0.7, anchor="l")
        text(out, "胜率", CH_X0 - 6, CH_Y0 - 24, 16, "sans_light", GREY, a * 0.7, anchor="l")
        if ni >= 2:
            ii = np.unique(np.geomspace(1, ni, min(ni, 400)).astype(int))
            ps = SIM_CUM[ii - 1] / ii
            for prob, col in ((ps, BLUE), (1 - ps, GOLD)):
                xs, ys = chart_xy(ii, prob)
                pts = np.c_[xs, ys]
                polyline(lay, pts, col, 0.9 * a, 2)
                polyline(out, pts, col * 0.6, 0.6 * a, 1.2, mode="over")
                circle(lay, pts[-1], 4, col, a)
                glow_spot(lay, pts[-1], 14, col, 0.3 * a)
    if t >= SIM_T1:
        shockwave(lay, (SIM_R, 320), t, SIM_T1, GOLD, 600, 1.0, 0.8)


# ================================================================ 场景 5：100 扇门（82.5–112.5）
G_W, G_H = 54, 84
OPEN_AT = {d: tt for tt, d in T.CASCADE}


def gdoor_pos(d):
    i = d - 1
    c, r = i % 20, i // 20
    return 960 + (c - 9.5) * 72, 330 + r * 106 + G_H


def scene_100(out, lay, t):
    if not (82.3 <= t <= 113.0):
        return
    A = window(t, 82.5, 112.8, 0.8, 1.0)
    hk = T.HITS["door74"]
    after = prog(t, hk + 1.0, 1.6)            # 98 扇门淡出，两扇门移到中央
    for d in range(1, 101):
        cx, by = gdoor_pos(d)
        appear = eout(prog(t, 83.0 + ((d - 1) % 20) * 0.03 + ((d - 1) // 20) * 0.06, 0.6))
        if appear <= 0:
            continue
        theta, inside, ik = 0.0, None, 0.0
        col, fk, a = GOLD, 0.45, A * appear
        if d in OPEN_AT:
            u = prog(t, OPEN_AT[d], 0.28)
            theta = 1.6 * eout(u)
            inside, ik = ("goat", np.array([0.7, 0.78, 0.95])), u
            col = mixc(GOLD, BLUE, u)
            if t > 95.6:
                a *= 1 - 0.65 * prog(t, 95.6, 0.8)
            a *= 1 - after
        if d == 1:
            fk = 0.45 + 0.7 * prog(t, 87.1, 0.5)
        if d == T.CAR_DOOR:
            fk = 0.45 + 0.8 * prog(t, 95.6, 0.8)
            col = mixc(GOLD, GOLD_HI, prog(t, hk, 0.4))
        if d in (1, T.CAR_DOOR) and after > 0:
            tx = CX - 300 if d == 1 else CX + 300
            cx = cx + (tx - cx) * ease(after)
            by = by + (780 - by) * ease(after)
            sc = 1 + 1.6 * ease(after)
            draw_door(out, lay, cx, by, G_W * sc, G_H * sc, 0.0, d, a, col, fk, num_size=G_H * sc * 0.22)
            continue
        if a > 0.01:
            draw_door(out, lay, cx, by, G_W, G_H, theta, d, a, col, fk, inside, ik, num_size=17)
    # 标签
    c1 = np.array(gdoor_pos(1), float)
    c74 = np.array(gdoor_pos(T.CAR_DOOR), float)
    if after > 0:
        c1 = c1 + (np.array([CX - 300, 780]) - c1) * ease(after)
        c74 = c74 + (np.array([CX + 300, 780]) - c74) * ease(after)
    s_now = 1 + 1.6 * ease(after)
    a = window(t, 87.1, 112.6, 0.5, 0.8)
    if a > 0:
        text(out, "1%", c1[0], c1[1] - G_H * s_now - 34 - 36 * after, 30 + 34 * after, "inter_light",
             GREY * 1.2 if t > hk else GOLD, a)
        if t < 95:
            text(out, "你的选择", c1[0], c1[1] + 24, 18, "serif_med", GOLD, a, track=0.2)
    if t >= hk:
        u = prog(t, hk, 0.6)
        text(out, "99%", c74[0], c74[1] - G_H * s_now - 46 - 46 * after, 52 + 50 * after, "inter_light", GOLD,
             eout(u) * A, glow=0.5, glow_buf=lay)
        glow_spot(lay, (c74[0], c74[1] - G_H * s_now / 2), 60 + 80 * after, GOLD, 0.25 * A)
        shockwave(lay, (c74[0], c74[1] - G_H / 2), t, hk, GOLD, 900, 1.3)
    a = window(t, 95.8, 99.4, 0.5, 0.3)
    if a > 0:
        dashed(lay, (c1[0] + 30, c1[1] - G_H / 2), (c74[0] - 30, c74[1] - G_H / 2), GOLD, 0.5 * a, 1.5, 8, 8,
               phase=t * 40)
    # 回放：主持人依次打开的 98 扇门（淡影涟漪），74 号门始终没被碰
    if 101.0 <= t <= 109.5:
        ghost = window(t, 101.0, 109.5, 0.6, 1.0)
        for (td, d) in T.CASCADE:
            x, y = gdoor_pos(d)
            rt = 101.4 + (td - T.CASCADE_T0) * 0.8
            flash = math.exp(-max(0.0, t - rt) / 0.5) if t >= rt else 0.0
            rect(lay, x - G_W / 2, y - G_H, x + G_W / 2, y, mixc(BLUE, TEAL, flash), ghost * (0.06 + 0.4 * flash),
                 th=1, mode="add")
        ka = eout(prog(t, 102.6, 0.6)) * window(t, 102.6, 109.5, 0.3, 1.0)
        rc = (c74[0], c74[1] - G_H * s_now / 2)
        circle(lay, rc, G_H * s_now * 0.72, CORAL, 0.7 * ka, th=2)
        text(out, "他绝不会打开它", rc[0], rc[1] + G_H * s_now * 0.72 + 34, 22, "serif_med", CORAL, ka, track=0.2)
    # 证据
    anim_text(out, "证据", CX, 236, 110, t, 105.3, 112.0, "serif_black", TEAL, track=0.3, glow=0.4, glow_buf=lay,
              fin=0.9)
    anim_text(out, "EVIDENCE", CX, 312, 18, t, 105.6, 112.0, "inter_semi", TEAL * 0.8, track=0.8)
    a = window(t, 109.0, 112.2, 0.5, 0.8)
    if a > 0:
        # 证据流向 99%
        r = np.random.default_rng(3)
        n = 140
        ph = (t * 0.6 + r.random(n)) % 1.0
        src = np.c_[CX + (r.random(n) - 0.5) * 160, 236 + (r.random(n) - 0.5) * 60]
        dst = np.array([CX + 300, 470])
        P = src + (dst - src) * ph[:, None] ** 1.5
        P[:, 0] += np.sin(ph * 6 + r.random(n) * 6) * 20
        dots(lay, P, TEAL[None, :] * (np.sin(ph * math.pi) * a * 0.9)[:, None], 1.3)


# ================================================================ 场景 6：1763 与贝叶斯定理（112.5–135）
def scene_bayes(out, lay, t):
    if not (112.3 <= t <= 135.2):
        return
    # 1763
    if t < 122.6:
        A = clip01((121.9 - t) / 0.3) if t < 122 else 0
        if A > 0:
            sc = 1 + 0.03 * prog(t, 112.5, 9)
            anim_text(out, "1763", CX, 360, 240, t, 112.6, 121.9, "inter_thin", GOLD, gradient=TITLE_GRAD,
                      track=0.08, fin=1.4, glow=0.3, glow_buf=lay, blur_px=12)
            anim_text(out, "托马斯·贝叶斯", CX, 540, 54, t, 113.2, 121.9, "serif_bold", INK, track=0.3)
            anim_text(out, "THOMAS BAYES  ·  c.1701 – 1761", CX, 600, 18, t, 113.6, 121.9, "inter_semi", GREY,
                      track=0.5)
            # 羽毛笔写出论文标题
            k = prog(t, 114.4, 2.6)
            title = "An Essay towards solving a Problem in the Doctrine of Chances"
            sp = text_sprite(title, "corm", 30, np.array([0.84, 0.74, 0.55]), 0.02)
            a = window(t, 114.4, 121.9, 0.2, 0.4)
            if a > 0:
                blit(out, sp, CX, 676, a, reveal=k, soft=0.02)
                qx = CX - sp.w / 2 + sp.w * k
                if k < 1:
                    qs = icon("quill", 44, GOLD)
                    blit_icon(out, qs, qx + 12, 650, a)
                    glow_spot(lay, (qx, 680), 10, GOLD, 0.6 * a)
            anim_text(out, "去世两年后，由好友理查德·普莱斯整理，在英国皇家学会宣读", CX, 734, 22, t, 116.6, 121.9,
                      "serif_med", GREY, track=0.12)
            glow_spot(lay, (CX, 360), 300, GOLD, 0.05 * A)
    # 公式
    T0 = T.HITS["formula"]
    if t >= T0 - 0.02:
        A = clip01((134.9 - t) / 0.6)
        mk = prog(t, 127.5, 1.2)             # 公式上移缩小，人话版出现
        fy = 400 - 170 * ease(mk)
        fs = 1 - 0.38 * ease(mk)
        a = eout(prog(t, T0, 0.6)) * A
        sz = 92
        parts = [("P(A\\,|\\,B)", GOLD), ("=", INK), ("P(B\\,|\\,A)", TEAL), ("\\cdot", INK), ("P(A)", BLUE),
                 ("P(B)", GREY * 1.3)]
        sps = [math_sprite(p, sz, c) for p, c in parts]
        gap = 26
        num_w = sps[2].w + sps[3].w + sps[4].w + 2 * gap
        total = sps[0].w + gap + sps[1].w + gap + num_w
        x = CX - total * fs / 2
        cx_post = x + sps[0].w * fs / 2
        blit_c(out, sps[0], cx_post, fy, a, scale=fs)
        x += (sps[0].w + gap) * fs
        blit_c(out, sps[1], x + sps[1].w * fs / 2, fy, a, scale=fs)
        x += (sps[1].w + gap) * fs
        bar_x0, bar_x1 = x, x + num_w * fs
        ny, dy = fy - 62 * fs, fy + 62 * fs
        xx = x
        cx_lik = xx + sps[2].w * fs / 2
        blit_c(out, sps[2], cx_lik, ny, a, scale=fs)
        xx += (sps[2].w + gap) * fs
        blit_c(out, sps[3], xx + sps[3].w * fs / 2, ny, a, scale=fs)
        xx += (sps[3].w + gap) * fs
        cx_pri = xx + sps[4].w * fs / 2
        blit_c(out, sps[4], cx_pri, ny, a, scale=fs)
        cx_den = (bar_x0 + bar_x1) / 2
        blit_c(out, sps[5], cx_den, dy, a, scale=fs)
        line(out, (bar_x0, fy), (bar_x1, fy), INK, a, 2.2 * fs, "over")
        # 发光
        for sp_, cx_, cy_, c_ in ((sps[0], cx_post, fy, GOLD), (sps[2], cx_lik, ny, TEAL), (sps[4], cx_pri, ny, BLUE)):
            blit_c(lay, sp_, cx_, cy_, 0.25 * a, mode="add", scale=fs, blur=3)
        # 标注（逐拍出现）
        la = A * (1 - ease(mk))
        notes = [(T0 + 0.6, cx_post, fy + 110, "后验", "看到证据后的判断", GOLD, 1),
                 (T0 + 1.25, cx_pri, ny - 120, "先验", "看到证据前的判断", BLUE, -1),
                 (T0 + 1.9, cx_lik, ny - 120, "似然", "如果 A 成立，出现证据 B 的概率", TEAL, -1),
                 (T0 + 2.55, cx_den, dy + 110, "证据出现的总概率", "（用来归一化）", GREY * 1.3, 1)]
        for (t0, x_, y_, h1, h2, c_, sgn) in notes:
            k = eout(prog(t, t0, 0.5))
            if k <= 0 or la <= 0:
                continue
            al = la * k
            y_anchor = (fy + 52) if sgn > 0 and h1 == "后验" else ((dy + 50) if sgn > 0 else (ny - 52))
            line(lay, (x_, y_anchor), (x_, (y_ - 30) if sgn > 0 else (y_ + 58)), c_, 0.6 * al, 1)
            text(out, h1, x_, y_, 30, "serif_bold", c_, al, track=0.2)
            text(out, h2, x_, y_ + 38 * (1 if sgn > 0 else 1), 18, "sans_light", GREY, al, track=0.1)
        shockwave(lay, (CX, fy), t, T0, GOLD, 1000, 1.3)
        # 人话版
        if mk > 0:
            a2 = eout(prog(t, 127.7, 0.8)) * A
            y = 560
            segs = [("新判断", GOLD, "后验 Posterior"), ("=", INK, None), ("旧判断", BLUE, "先验 Prior"),
                    ("×", INK, None), ("证据的力度", TEAL, "似然比 Likelihood Ratio")]
            sps2 = [text_sprite(s_, "serif_black", 84, c_, 0.08) for s_, c_, _ in segs]
            ws = [sp_.w - 2 * sp_.ox for sp_ in sps2]
            g2 = 40
            tot = sum(ws) + g2 * (len(ws) - 1)
            x = CX - tot / 2
            for i, ((s_, c_, sub), sp_, w_) in enumerate(zip(segs, sps2, ws)):
                ki = eout(prog(t, 127.7 + i * 0.32, 0.6))
                xc = x + w_ / 2
                blit(out, sp_, xc, y, a2 * ki, rise=-14 * (1 - ki), blur=6 * (1 - ki))
                if c_ is not INK:
                    blit(lay, sp_, xc, y, 0.25 * a2 * ki, mode="add", blur=4)
                if sub:
                    ks = eout(prog(t, 129.2 + i * 0.25, 0.6))
                    text(out, sub, xc, y + 84, 20, "sans_light", c_, a2 * ks, track=0.12)
                x += w_ + g2
            anim_text(out, "严格地说：后验赔率 = 先验赔率 × 似然比", CX, 780, 20, t, 130.6, 134.9, "sans_light", GREY,
                      track=0.15)


# ================================================================ 场景 7：一万个人（135–190）
M_COLS, M_ROWS, M_SP = 125, 80, 8.6
_mr = np.random.default_rng(10000)
_ix = np.arange(M_COLS * M_ROWS)
M_POS = np.c_[CX + ((_ix % M_COLS) - (M_COLS - 1) / 2) * M_SP, 548 + ((_ix // M_COLS) - (M_ROWS - 1) / 2) * M_SP]
M_SICK = _mr.choice(_ix, 100, replace=False)
M_TP = M_SICK[:99]                                    # 99 个病人呈阳性
M_FN = M_SICK[99:]
_healthy = np.setdiff1d(_ix, M_SICK)
M_FP = _mr.choice(_healthy, 99, replace=False)        # 9900 × 1% = 99 个误报
M_DIST = np.hypot(M_POS[:, 0] - CX, M_POS[:, 1] - 548)
M_R = _mr.random((len(_ix), 3))
# 阳性的人汇聚成两块：左 99 个病人，右 99 个误报
def _block(cx, cy, n, cols=11, sp=17.0):
    i = np.arange(n)
    return np.c_[cx + ((i % cols) - (cols - 1) / 2) * sp, cy + ((i // cols) - (math.ceil(n / cols) - 1) / 2) * sp]


BLK_TP = _block(CX - 230, 560, 99)
BLK_FP = _block(CX + 230, 560, 99)
# 第二次检测：病人 98/99 仍阳性，误报 1/99 仍阳性
RE_TP_KEEP = np.ones(99, bool)
RE_TP_KEEP[_mr.integers(0, 99)] = False
RE_FP_KEEP = np.zeros(99, bool)
RE_FP_KEEP[_mr.integers(0, 99)] = True

HEALTHY_C = np.array([0.42, 0.46, 0.56], np.float32)


def stat_chip(out, lay, x, y, big, label, col, a):
    if a <= 0:
        return
    text(out, big, x, y, 92, "inter_light", col, a, glow=0.3, glow_buf=lay)
    text(out, label, x, y + 78, 24, "serif_med", INK, a * 0.9, track=0.2)


def scene_medical(out, lay, t):
    if not (135.0 <= t <= 190.3):
        return
    # 题目
    a = window(t, 135.4, 149.6, 0.7, 0.6)
    if a > 0:
        up = ease(prog(t, 144.0, 0.8))
        anim_text(out, "一道真实的题", CX, 200 - 40 * up, 30, t, 135.4, 149.6, "serif_med", GREY, track=0.5)
        for x, t0, big, lab, col in ((CX - 460, 135.6, "1%", "发病率", CORAL), (CX, 139.8, "99%", "病人 → 阳性", TEAL),
                                     (CX + 460, 141.2, "99%", "健康人 → 阴性", TEAL)):
            k = eout(prog(t, t0, 0.7))
            stat_chip(out, lay, x, 380 - 120 * up, big, lab, col, a * k * (1 - 0.5 * up))
    # 阳性
    a = window(t, 144.1, 149.6, 0.6, 0.5)
    if a > 0:
        k = eback(prog(t, 144.1, 0.7))
        circle(lay, (CX, 560), 78 * k, CORAL, 0.8 * a, th=3)
        circle(out, (CX, 560), 78 * k, CORAL * 0.25, 0.6 * a, mode="add")
        line(out, (CX - 30 * k, 560), (CX + 30 * k, 560), INK, a, 6, "over")
        line(out, (CX, 560 - 30 * k), (CX, 560 + 30 * k), INK, a, 6, "over")
        text(out, "你的结果：阳性", CX, 690, 30, "serif_bold", INK, a, track=0.3)
    # 直觉 99%？
    a = window(t, 147.5, 149.9, 0.25, 0.4)
    if a > 0:
        text(out, "99%?", CX + 330, 520, 120, "inter_light", CORAL, a, glow=0.4, glow_buf=lay)
        text(out, "直觉", CX + 330, 610, 24, "serif_med", CORAL, a * 0.9, track=0.4)
    # 点阵
    if t < 149.9:
        return
    appear = clip01((t - 150.0 - M_DIST / 900) / 0.5)
    A = clip01((189.9 - t) / 0.5)
    col = np.broadcast_to(HEALTHY_C, (len(_ix), 3)).copy()
    alpha = appear * 0.55
    sick_k = eout(prog(t, 152.6, 0.8))
    col[M_SICK] = mixc(HEALTHY_C, CORAL, sick_k)
    alpha[M_SICK] = appear[M_SICK] * (0.55 + 0.45 * sick_k)
    tp_k = eout(prog(t, 157.6, 0.8))
    fp_k = eout(prog(t, 162.6, 0.8))
    col[M_FP] = mixc(HEALTHY_C, BLUE, fp_k)
    alpha[M_FP] = appear[M_FP] * (0.55 + 0.6 * fp_k)
    alpha[M_TP] = alpha[M_TP] * (1 + 0.5 * tp_k)
    # 汇聚
    gk = prog(t, 167.4, 2.4)
    rest_fade = 1 - 0.9 * eout(prog(t, 167.4, 1.2))
    if t > 174.5:
        rest_fade = mixc(rest_fade, 0.35, eout(prog(t, 174.6, 1.0)) * (1 - prog(t, 177.4, 0.8)))
    P = M_POS.copy()
    pos_mask = np.zeros(len(_ix), bool)
    pos_mask[M_TP] = True
    pos_mask[M_FP] = True
    alpha[~pos_mask] *= rest_fade
    if gk > 0:
        P[M_TP], _ = morph(M_POS[M_TP], BLK_TP, gk, M_R[M_TP], 0.3, 0.35)
        P[M_FP], _ = morph(M_POS[M_FP], BLK_FP, gk, M_R[M_FP], 0.3, 0.35)
    # 第二次检测
    rk = prog(t, 178.4, 1.8)
    if rk > 0:
        scan_x = CX - 420 + 840 * rk
        a_tp = np.where(RE_TP_KEEP | (BLK_TP[:, 0] > scan_x), 1.0, 0.12)
        a_fp = np.where(RE_FP_KEEP | (BLK_FP[:, 0] > scan_x), 1.0, 0.12)
        alpha[M_TP] *= a_tp
        alpha[M_FP] *= a_fp
        if rk < 1:
            line(lay, (scan_x, 440), (scan_x, 680), TEAL, 0.9, 2)
            glow_rect(lay, scan_x - 3, 440, scan_x + 3, 680, TEAL, 0.5, 12)
    cyc = prog(t, 184.3, 0.9)                     # 循环图
    bf = prog(t, 183.3, 0.8)                      # 点阵先淡出
    alpha = alpha * A * (1 - bf)
    if alpha.max() > 0.003:
        big = np.zeros(len(_ix), bool)
        big[M_TP] = big[M_FP] = True
        sig_small = 1.15
        dots(lay, P[~big], col[~big] * alpha[~big, None] * 0.9, sig_small)
        sz = 1.15 + 1.4 * eout(gk)
        dots(lay, P[big], col[big] * alpha[big, None] * (1.0 + 0.4 * eout(gk)), sz)
        if tp_k > 0 and gk < 1:
            for i in M_TP:
                circle(lay, P[i], 5.5, CORAL, 0.35 * tp_k * A * (1 - gk) * (1 - cyc), th=1)
            for i in M_FP:
                circle(lay, P[i], 5.5, BLUE, 0.45 * fp_k * A * (1 - gk) * (1 - cyc), th=1)
    # 图例
    la = window(t, 152.6, 167.4, 0.6, 0.6) * A
    if la > 0:
        x0 = 1560
        items = [(152.6, CORAL, "患病", "100"), (152.9, HEALTHY_C * 1.6, "健康", "9,900"),
                 (157.6, CORAL, "阳性 · 真病人", "99"), (162.6, BLUE, "阳性 · 误报", "99")]
        for k_, (t0, c_, lab, num) in enumerate(items):
            kk = eout(prog(t, t0, 0.6)) * la
            y = 360 + k_ * 92 + (20 if k_ >= 2 else 0)
            circle(lay, (x0, y), 7, c_, kk)
            if k_ >= 2:
                circle(lay, (x0, y), 12, c_, 0.5 * kk, th=1)
            text(out, lab, x0 + 26, y - 14, 20, "serif_med", GREY, kk, anchor="l", track=0.1)
            text(out, num, x0 + 26, y + 18, 34, "inter_light", c_, kk, anchor="l")
    text(out, "10,000", 330, 360, 40, "inter_light", INK, window(t, 150.1, 167.4, 0.6, 0.6) * A)
    text(out, "每个点 = 1 个人", 360, 404, 18, "sans_light", GREY, window(t, 150.6, 167.4, 0.6, 0.6) * A)
    # 50%
    hk = T.HITS["fifty"]
    a = window(t, hk, 189.7, 0.25, 0.5) * A
    if a > 0:
        sl = ease(prog(t, 181.3, 1.0))
        text(out, "50%", CX - 200 * sl, 330 - 70 * ease(cyc), 150 - 60 * sl, "inter_light", mixc(GOLD, GOLD * 0.7, sl),
             a * (1 - 0.0 * sl), glow=0.5 * (1 - sl), glow_buf=lay)
        lab_a = a * (1 - prog(t, 177.6, 0.6)) * (1 - bf)
        text(out, "真病人 99", CX - 230, 700, 26, "serif_med", CORAL, lab_a, track=0.15)
        text(out, "误报 99", CX + 230, 700, 26, "serif_med", BLUE, lab_a, track=0.15)
        text(out, "99 ÷ (99 + 99) = 50%", CX, 790, 30, "inter_light", GREY * 1.3, lab_a, track=0.05)
        shockwave(lay, (CX, 330), t, hk, GOLD, 1000, 1.3)
    # 再测一次 → 99%
    hk2 = T.HITS["iter"]
    a = window(t, 180.3, 189.9, 0.6, 0.6) * A
    if a > 0:
        text(out, "真病人 98", CX - 230, 700, 26, "serif_med", CORAL, a * (1 - bf), track=0.15)
        text(out, "误报 1", CX + 230, 700, 26, "serif_med", BLUE, a * (1 - bf), track=0.15)
        text(out, "98 ÷ (98 + 1) ≈ 99%", CX, 790, 30, "inter_light", GREY * 1.3, a * (1 - bf), track=0.05)
    if t >= hk2:
        u = eout(prog(t, hk2, 0.8))
        a2 = A * clip01((189.7 - t) / 0.5)
        text(out, "→", CX + 10, 330 - 70 * ease(cyc), 60, "inter_thin", INK, a2 * u)
        text(out, "99%", CX + 220 * u, 330 - 70 * ease(cyc), 150, "inter_light", GOLD, a2, glow=0.5, glow_buf=lay)
        shockwave(lay, (CX + 220, 330), t, hk2, GOLD, 900, 1.2)
    # 循环图：后验 → 先验
    if cyc > 0:
        ac = eout(cyc) * A
        c = np.array([CX, 640])
        R0 = 150
        rot = t * 0.9
        arc(lay, c, R0, 0, 2 * math.pi, WHITE, 0.10 * ac, 1)
        nodes = [(-math.pi / 2, "先验", BLUE), (math.pi / 6, "证据", TEAL), (5 * math.pi / 6, "后验", GOLD)]
        for k_, (ang, lab, c_) in enumerate(nodes):
            a0 = ang + 0.32
            a1 = nodes[(k_ + 1) % 3][0] - 0.32 + (2 * math.pi if k_ == 2 else 0)
            arc(lay, c, R0, a0, a1, c_, 0.75 * ac, 2)
            e = np.array([c[0] + R0 * math.cos(a1), c[1] + R0 * math.sin(a1)])
            tang = np.array([-math.sin(a1), math.cos(a1)])
            nrm = np.array([math.cos(a1), math.sin(a1)])
            poly(lay, [e + tang * 10, e - tang * 2 + nrm * 7, e - tang * 2 - nrm * 7], c_, ac, mode="add")
            p = c + R0 * np.array([math.cos(ang), math.sin(ang)])
            circle(lay, p, 36, c_, 0.9 * ac, th=2)
            circle(out, p, 35, c_ * 0.12, ac, mode="add")
            text(out, lab, p[0], p[1], 24, "serif_bold", c_, ac, track=0.1)
        r = np.random.default_rng(4)
        ph = (rot * 0.25 + r.random(90)) % 1.0
        angs = -math.pi / 2 + ph * 2 * math.pi
        P = np.c_[c[0] + (R0 + (r.random(90) - 0.5) * 10) * np.cos(angs), c[1] + (R0 + (r.random(90) - 0.5) * 10) * np.sin(angs)]
        dots(lay, P, np.broadcast_to(GOLD, (90, 3)) * 0.5 * ac, 1.2)
        text(out, "今天的后验", c[0] - 330, c[1] + 120, 22, "serif_med", GOLD, ac, track=0.2)
        text(out, "明天的先验", c[0] + 330, c[1] - 120, 22, "serif_med", BLUE, ac, track=0.2)


# ================================================================ 场景 8：证据的力度（190–207.5）
G_C = np.array([CX, 760.0])
G_R = 300


def lr_angle(lr):
    v = clip01((math.log10(max(lr, 1e-3)) + 2) / 4)       # 1/100 .. 100
    return math.pi + v * math.pi


def scene_evidence(out, lay, t):
    if not (190.0 <= t <= 207.9):
        return
    A = window(t, 190.2, 207.6, 0.6, 0.5)
    # 定义（分式）
    a = eout(prog(t, 190.5, 0.8)) * A
    y0 = 250
    text(out, "证据的力度", CX - 420, y0, 40, "serif_bold", TEAL, a, track=0.15, glow=0.3, glow_buf=lay)
    text(out, "LIKELIHOOD RATIO", CX - 420, y0 + 44, 14, "inter_semi", TEAL * 0.8, a, track=0.5)
    text(out, "=", CX - 250, y0, 44, "inter_thin", INK, a)
    fx = CX + 90
    k1 = eout(prog(t, 191.2, 0.7)) * A
    k2 = eout(prog(t, 192.2, 0.7)) * A
    text(out, "我是对的时，看到这个证据的概率", fx, y0 - 42, 30, "serif_med", INK, k1, track=0.06)
    line(out, (fx - 300, y0), (fx + 300, y0), INK, max(k1, k2) * 0.8, 1.5, "over")
    hl = eout(prog(t, 194.6, 0.6)) * (1 - prog(t, 199.2, 0.6))
    text(out, "我是错的时，看到这个证据的概率", fx, y0 + 44, 30, "serif_med", mixc(INK, CORAL, hl), k2, track=0.06,
         glow=0.6 * hl, glow_buf=lay)
    if hl > 0:
        rect(lay, fx - 310, y0 + 18, fx + 310, y0 + 72, CORAL, 0.6 * hl * A, th=1.2, r=8, mode="add")
        text(out, "关键在分母", fx + 400, y0 + 44, 22, "serif_med", CORAL, hl * A, track=0.2)
    # 仪表盘
    ga = eout(prog(t, 190.9, 1.2)) * A
    if ga > 0:
        n = 120
        for i in range(n):
            a0 = math.pi + i / n * math.pi
            a1 = math.pi + (i + 1) / n * math.pi
            v = i / (n - 1)
            c_ = mixc(CORAL, GREY, clip01(v * 2)) if v < 0.5 else mixc(GREY, TEAL, clip01(v * 2 - 1))
            arc(lay, G_C, G_R, a0, a1 + 0.002, c_, 0.75 * ga * float(clip01((ga * n - i) / 6)), 3, n=4)
        for lr, lab in ((0.01, "1/100"), (0.1, "1/10"), (1, "1"), (10, "10"), (100, "100")):
            ang = lr_angle(lr)
            p0 = G_C + (G_R - 14) * np.array([math.cos(ang), math.sin(ang)])
            p1 = G_C + (G_R + 14) * np.array([math.cos(ang), math.sin(ang)])
            line(out, p0, p1, INK, 0.6 * ga, 1.5, "over")
            pl = G_C + (G_R + 46) * np.array([math.cos(ang), math.sin(ang)])
            if lr in (0.01, 100):
                pl = pl + np.array([0, -28])
            text(out, "×" + lab, pl[0], pl[1], 22, "inter_light", GREY * 1.2, ga)
        text(out, "反向证据", G_C[0] - G_R - 10, G_C[1] + 40, 22, "serif_med", CORAL, ga, track=0.2)
        text(out, "支持证据", G_C[0] + G_R + 10, G_C[1] + 40, 22, "serif_med", TEAL, ga, track=0.2)
        text(out, "×1 = 废证据：对错两种情况下一样常见", G_C[0], G_C[1] + 118, 22, "serif_med", GREY,
             ga * (1 - prog(t, 199.4, 0.4)), track=0.12)
        # 指针
        lr = 1.0
        e1, e2 = prog(t, 200.6, 0.9), prog(t, 204.4, 1.1)
        if t < 203.6:
            lr = 1.0 + 0.2 * eback(e1, 2.0)
        else:
            lr = 1.2 * (20 / 1.2) ** eback(e2, 1.3)
        lr = max(lr, 1e-3)
        ang = lr_angle(lr) + 0.006 * math.sin(t * 9)
        tip = G_C + (G_R - 30) * np.array([math.cos(ang), math.sin(ang)])
        col = TEAL if lr > 3 else INK
        line(lay, G_C, tip, col, 0.95 * ga, 3)
        line(out, G_C, tip, col, 0.9 * ga, 2, "over")
        circle(lay, G_C, 9, col, ga)
        glow_spot(lay, tip, 18, col, 0.6 * ga)
        text(out, f"×{lr:.1f}" if lr < 10 else f"×{lr:.0f}", G_C[0], G_C[1] + 56, 46, "inter_light", col,
             ga * clip01((t - 200.6) / 0.4))
    # 两个例子
    for (t0, t1, quote, p1, p2, verdict, vc) in (
            (199.6, 203.5, "「产品挺有意思」", "想买的人这么说：60%", "不想买的人也这么说：50%", "几乎是废证据", GREY * 1.3),
            (203.6, 207.4, "「在哪付款？」", "想买的人会问：40%", "不想买的人会问：2%", "强证据", TEAL)):
        a = window(t, t0, t1, 0.5, 0.4) * A
        if a <= 0:
            continue
        anim_text(out, quote, CX, 380, 46, t, t0, t1, "serif_bold", INK, track=0.12)
        text(out, p1, CX - 240, 440, 22, "sans_light", INK, a * eout(prog(t, t0 + 0.3, 0.5)), track=0.08)
        text(out, p2, CX + 240, 440, 22, "sans_light", INK, a * eout(prog(t, t0 + 0.6, 0.5)), track=0.08)
        text(out, verdict, CX, G_C[1] + 118, 26, "serif_bold", vc, a * eout(prog(t, t0 + 1.4, 0.5)), track=0.3)
    text(out, "（数字为示意）", 1700, 880, 16, "sans_light", GREY, window(t, 199.8, 207.3, 0.5, 0.4) * A * 0.8)


# ================================================================ 场景 9：回到三扇门（207.5–222.5）
def scene_solve(out, lay, t):
    if not (207.3 <= t <= 223.0):
        return
    A = window(t, 207.6, 222.6, 0.8, 0.6)
    hk = T.HITS["solve"]
    pri = [1 / 3, 1 / 3, 1 / 3]
    lik = [0.5, 1.0, 0.0]
    post = [1 / 3, 2 / 3, 0.0]
    mk = ease(prog(t, 215.0, 1.0))
    nk = eback(prog(t, hk, 0.8), 1.0)
    labs_pre = ["1/3", "1/3", "1/3"]
    labs_mul = ["1/6", "1/3", "0"]
    labs_post = ["1/3", "2/3", "0"]
    by = 800
    for i in range(3):
        cx = D3_X[i]
        mult = pri[i] * (1 - mk) + pri[i] * lik[i] * mk
        f = mult + (post[i] - pri[i] * lik[i]) * nk if t >= hk else mult
        fcol = mixc(BLUE, TEAL, mk) if t < hk else mixc(mixc(BLUE, TEAL, 1.0), GOLD if i == 1 else GREY * 1.2, eout(prog(t, hk, 0.5)))
        theta = 1.75 if i == 2 else 0.0
        inside = ("goat", np.array([0.5, 0.56, 0.7])) if i == 2 else None
        draw_door(out, lay, cx, by, 200, 330, theta, i + 1, A * eout(prog(t, 207.6 + i * 0.15, 0.8)),
                  GOLD if i < 2 else BLUE, 0.55, inside, 1.0, max(f, 0.0), fcol)
        # 概率标签
        if t < 215.4:
            lab, c_ = labs_pre[i], BLUE
        elif t < hk:
            lab, c_ = labs_mul[i], TEAL
        else:
            lab, c_ = labs_post[i], (GOLD if i == 1 else GREY * 1.2)
        size = 64 if not (t >= hk and i == 1) else 64 + 40 * nk
        text(out, lab, cx, by - 330 - 58 - (12 * nk if i == 1 and t >= hk else 0), size, "inter_light", c_,
             A * eout(prog(t, 208.2, 0.6)), glow=(0.5 if i == 1 and t >= hk else 0.1), glow_buf=lay)
        # 似然因子
        t0 = 211.7 + i * 1.25
        k = eout(prog(t, t0, 0.5)) * (1 - prog(t, hk - 0.6, 0.5))
        if k > 0:
            fac = ["×1/2", "×1", "×0"][i]
            cap = ["车在 1 号：他随机开 2 或 3", "车在 2 号：他只能开 3", "车在 3 号：他绝不开 3"][i]
            rect(out, cx - 66, by + 26, cx + 66, by + 80, TEAL * 0.12, A * k, r=10, mode="add")
            rect(lay, cx - 66, by + 26, cx + 66, by + 80, TEAL, 0.5 * A * k, th=1.2, r=10, mode="add")
            text(out, fac, cx, by + 53, 34, "inter_light", TEAL, A * k)
            text(out, cap, cx, by + 112, 18, "sans_light", GREY * 1.2, A * k, track=0.05)
    # 行标题
    a = A * eout(prog(t, 208.2, 0.6))
    text(out, "先验", 300, by - 388, 24, "serif_bold", BLUE, a * (1 - prog(t, 215.0, 0.5)), track=0.3)
    text(out, "× 似然", 300, by + 53, 24, "serif_bold", TEAL, A * eout(prog(t, 211.7, 0.5)) * (1 - prog(t, hk - 0.6, 0.5)),
         track=0.3)
    text(out, "相乘", 300, by - 388, 24, "serif_bold", TEAL, A * window(t, 215.2, hk, 0.4, 0.3), track=0.3)
    text(out, "归一化 → 后验", 300, by - 388, 24, "serif_bold", GOLD, A * window(t, hk, 222.6, 0.3, 0.6), track=0.3)
    text(out, "主持人开了 3 号门", 1660, by - 388, 22, "serif_med", BLUE, a * 0.9, track=0.2)
    if t >= hk:
        shockwave(lay, (D3_X[1], by - 165), t, hk, GOLD, 1000, 1.3)
        glow_spot(lay, (D3_X[1], by - 165), 170, GOLD, 0.12 * A)


# ================================================================ 场景 10：生活与投资（222.5–245）
def corridor(out, lay, t, a):
    """两侧无尽的门：透视走廊，镜头缓慢前进"""
    if a <= 0:
        return
    vp = np.array([CX, 470.0])
    f = 700.0
    z0 = (t - 222.5) * 2.2
    for side in (-1, 1):
        for k in range(14):
            z = 2.0 + k * 1.8 - (z0 % 1.8)
            if z < 0.6:
                continue
            fade = clip01((22 - z) / 8) * clip01((z - 0.6) / 0.8)
            def P(x, y, zz):
                return vp + np.array([x, y]) * f / zz
            x = side * 3.2
            q = [P(x, -1.6, z), P(x, -1.6, z + 0.9), P(x, 2.2, z + 0.9), P(x, 2.2, z)]
            polyline(lay, q, GOLD, 0.55 * a * fade, 1.5, closed=True)
            glow_rect(lay, min(q[0][0], q[1][0]), q[1][1], max(q[0][0], q[1][0]), q[2][1], GOLD, 0.02 * a * fade, 10)
    for y in (-1.6, 2.2):
        for side in (-1, 1):
            line(lay, vp + np.array([side * 3.2, y]) * f / 0.9, vp + np.array([side * 3.2, y]) * f / 30, BLUE,
                 0.12 * a, 1)
    glow_spot(lay, vp, 120, GOLD, 0.15 * a)


INV_P0 = 0.60
INV_EV = [(232.6, "连续提价，销量不降", 3.0, "×3"), (234.6, "自由现金流常年为正", 2.0, "×2"),
          (236.6, "核心高管集体减持", 0.25, "×1/4")]


def inv_probs():
    ps = [INV_P0]
    for _, _, lr, _ in INV_EV:
        o = ps[-1] / (1 - ps[-1]) * lr
        ps.append(o / (1 + o))
    return ps


INV_PS = inv_probs()           # 60% → 81.8% → 90.0% → 69.2%
IC_X0, IC_X1, IC_Y0, IC_Y1 = 420, 1500, 330, 790


def ic_xy(x, p):
    return x, IC_Y1 - (IC_Y1 - IC_Y0) * p


def scene_life(out, lay, t):
    if not (222.4 <= t <= 245.3):
        return
    corridor(out, lay, t, window(t, 222.5, 227.0, 0.8, 0.8))
    # 习惯一
    a = window(t, 226.8, 231.1, 0.6, 0.5)
    if a > 0:
        anim_text(out, "①  用概率说话", CX, 230, 40, t, 226.8, 231.1, "serif_bold", INK, track=0.2)
        k = prog(t, 227.6, 0.6)
        text(out, "肯定", CX - 300, 560, 110, "serif_black", CORAL, a * (1 - 0.6 * prog(t, 228.6, 0.5)))
        sk = eout(prog(t, 228.4, 0.4))
        if sk > 0:
            line(out, (CX - 420, 568), (CX - 420 + 240 * sk, 552), CORAL, a, 4, "over")
        text(out, "→", CX - 30, 560, 70, "inter_thin", INK, a * eout(prog(t, 228.8, 0.4)))
        rk = eout(prog(t, 229.0, 1.2))
        if rk > 0:
            c = (CX + 270, 560)
            arc(lay, c, 110, -math.pi / 2, -math.pi / 2 + 2 * math.pi, WHITE, 0.12 * a, 6)
            arc(lay, c, 110, -math.pi / 2, -math.pi / 2 + 2 * math.pi * 0.7 * rk, GOLD, 0.95 * a, 6)
            text(out, f"{int(round(70 * rk))}%", c[0], c[1], 64, "inter_light", GOLD, a)
            text(out, "我有七成把握", c[0], c[1] + 160, 24, "serif_med", INK, a * rk, track=0.2)
    # 习惯二、三：投资信念曲线
    a = window(t, 231.3, 244.8, 0.7, 0.6)
    if a > 0:
        title = "②  给证据称重" if t < 240.0 else "③  主动寻找反证"
        if t < 240.0:
            anim_text(out, "②  给证据称重", CX, 200, 40, t, 231.3, 240.0, "serif_bold", INK, track=0.2, fout=0.3)
        else:
            anim_text(out, "③  主动寻找反证", CX, 200, 40, t, 240.0, 244.8, "serif_bold", CORAL, track=0.2, fin=0.5)
        text(out, "假设：这是一家好公司", IC_X0, IC_Y0 - 60, 24, "serif_med", INK, a, anchor="l", track=0.15)
        line(out, (IC_X0, IC_Y1), (IC_X1, IC_Y1), WHITE, 0.25 * a, 1, "over")
        for p in (0.5, 1.0):
            _, y = ic_xy(0, p)
            dashed(out, (IC_X0, y), (IC_X1, y), WHITE, 0.12 * a, 1, 4, 6, mode="over")
            text(out, f"{int(p * 100)}%", IC_X0 - 40, y, 18, "inter_light", GREY, a)
        xs = [IC_X0 + 40, 700, 980, 1260]
        # 曲线：逐段平滑过渡
        pts = []
        cur_p = INV_PS[0]
        for k_ in range(len(xs)):
            if k_ == 0:
                pts.append(ic_xy(xs[0], INV_PS[0]))
                continue
            t0 = INV_EV[k_ - 1][0]
            u = prog(t, t0, 0.9)
            if u <= 0:
                break
            x_end = xs[k_ - 1] + (xs[k_] - xs[k_ - 1]) * eout(u, 2)
            us = np.linspace(0, 1, 30)
            pp = INV_PS[k_ - 1] + (INV_PS[k_] - INV_PS[k_ - 1]) * ease(us)
            xx = xs[k_ - 1] + (x_end - xs[k_ - 1]) * us
            pts += [ic_xy(xx_, pp_) for xx_, pp_ in zip(xx[1:], ease(us[1:]) * 0 + pp[1:])]
            cur_p = INV_PS[k_ - 1] + (INV_PS[k_] - INV_PS[k_ - 1]) * ease(u)
        pts = np.array(pts, float)
        kd = eout(prog(t, 231.6, 0.8))
        if len(pts) >= 2:
            polyline(lay, pts, GOLD, 0.95 * a, 2.5)
        for k_ in range(len(xs)):
            if k_ > 0 and t < INV_EV[k_ - 1][0] + 0.6:
                break
            x_, y_ = ic_xy(xs[k_], INV_PS[k_])
            c_ = BLUE if k_ == 0 else GOLD
            circle(lay, (x_, y_), 6, c_, a * kd)
            glow_spot(lay, (x_, y_), 16, c_, 0.4 * a * kd)
            text(out, f"{INV_PS[k_] * 100:.0f}%", x_, y_ - 40, 34, "inter_light", c_, a * kd)
            if k_ == 0:
                text(out, "先验", x_, y_ + 36, 20, "serif_med", BLUE, a * kd, track=0.2)
        for k_, (t0, lab, lr, chip) in enumerate(INV_EV):
            ka = eout(prog(t, t0 - 0.5, 0.5)) * a
            if ka <= 0:
                continue
            x_ = (xs[k_] + xs[k_ + 1]) / 2
            c_ = TEAL if lr > 1 else CORAL
            y_ = IC_Y1 + 50
            text(out, lab, x_, y_, 22, "serif_med", INK, ka, track=0.08)
            rect(out, x_ - 42, y_ + 26, x_ + 42, y_ + 64, c_ * 0.12, ka, r=8, mode="add")
            text(out, chip, x_, y_ + 45, 24, "inter_light", c_, ka)
            line(lay, (x_, IC_Y1 - 4), (x_, IC_Y1 + 22), c_, 0.5 * ka, 1)
        text(out, "（示意）", IC_X1 + 60, IC_Y1 + 95, 16, "sans_light", GREY, a * 0.7)
        # 反证：如果我错了
        rk = prog(t, 240.6, 1.6)
        if rk > 0:
            x_, y_ = ic_xy(xs[-1], INV_PS[-1])
            tgt = ic_xy(IC_X1 + 40, 0.18)
            e = np.array([x_, y_]) + (np.array(tgt) - [x_, y_]) * eout(rk)
            dashed(lay, (x_, y_), e, CORAL, 0.9 * a, 2, 10, 7, phase=-t * 30)
            ka = eout(prog(t, 241.4, 0.6)) * a
            text(out, "如果我错了，会先看到：", 1480, 470, 22, "serif_bold", CORAL, ka, anchor="l", track=0.1)
            for j, s_ in enumerate(["· 毛利率持续下滑", "· 老客户开始流失", "· 管理层回避坏消息"]):
                kj = eout(prog(t, 241.9 + j * 0.45, 0.5)) * a
                text(out, s_, 1480, 516 + j * 40, 21, "serif_med", INK, kj, anchor="l", track=0.08)


# ================================================================ 场景 11：终章与片尾 logo（245–265）
END_LOGO_SIZE = 220
END_LOGO_C = np.array([CX, 400.0])
END_LOGO = load_logo(END_LOGO_SIZE)
FIN_N = 8000
_fr = np.random.default_rng(250)
FIN_R = _fr.random((FIN_N, 3))
FIN_SRC = None
FIN_DST = None
FIN_COL = None


def _fin_init():
    global FIN_SRC, FIN_DST, FIN_COL
    if FIN_SRC is None:
        n1 = FIN_N // 2
        FIN_SRC = np.vstack([text_points("观点是用来迭代的，", "serif_black", 84, CX, 450, n1, _fr, 0.12),
                             text_points("不是用来捍卫的。", "serif_black", 84, CX, 580, FIN_N - n1, _fr, 0.12)])
        rgb_, a_ = END_LOGO
        pts, pick, (ys, xs) = mask_points(a_, FIN_N, _fr, 0.3)
        FIN_DST = pts + END_LOGO_C - END_LOGO_SIZE / 2
        FIN_COL = rgb_[ys[pick], xs[pick]].astype(np.float32)


def brand_text(s, size, fname, gold=True, width=None):
    """品牌字（brand 模块的字体与金色）。width: 两端对齐到指定宽度（小字与主标题等宽）"""
    key = ("brand", s, size, fname, gold, width)
    if key in _SPR:
        return _SPR[key]
    f = _brand._font(fname, size)
    widths = [f.getlength(c) for c in s]
    tr = 0.0 if width is None else (width - sum(widths)) / (len(s) - 1)
    w = int(sum(widths) + tr * (len(s) - 1)) + 40
    hgt = int(size * 1.7)
    im = Image.new("L", (w, hgt), 0)
    d = ImageDraw.Draw(im)
    x = 20.0
    for c, cw in zip(s, widths):
        d.text((x, int(size * 1.3)), c, font=f, fill=255, anchor="ls")
        x += cw + tr
    m_ = np.asarray(im, np.float32) / 255
    ys, xs = np.where(m_ > 0.01)
    m_ = m_[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    if gold:
        col = np.broadcast_to(_brand._ramp(m_.shape[0], _brand.GOLD_STOPS)[:, None, :].astype(np.float32),
                              m_.shape + (3,)).copy()
    else:
        col = np.broadcast_to(np.array(_brand.SUB_GOLD, np.float32) / 255, m_.shape + (3,)).copy()
    sp = Sprite(col, m_)
    sp.ox, sp.oy = sp.w / 2, sp.h / 2
    _SPR[key] = sp
    return sp


def blit_brand(out, sp, cx, cy, alpha, wipe=1.0, shine=None):
    a = sp.a * alpha
    col = sp.rgb
    w, h = sp.w, sp.h
    if wipe < 1.0:
        soft = 0.35 * w + 30
        a = a * clip01((wipe * (w + soft) - np.arange(w)) / soft).astype(np.float32)[None, :]
    if shine is not None and 0 < shine < 1:
        xs = np.arange(w)[None, :] + np.arange(h)[:, None] * 0.6
        pos = -60 + (0.5 - 0.5 * math.cos(shine * math.pi)) * (w + 120)
        col = np.clip(col + np.exp(-((xs - pos) / (0.06 * w + 10)) ** 2)[..., None] * 0.6, 0, 1.25)
    composite(out, col, a, cx - w / 2, cy - h / 2)


def scene_finale(out, lay, t):
    if t < 244.8:
        return
    end = final_fade(t)
    # 两句箴言
    for (t0, s_, en, y) in ((245.0, "大胆地持有一个判断，", "Boldly hold a tentative belief.", 420),
                            (247.5, "再用新证据，无情地修正它。", "Update it ruthlessly with new evidence.", 590)):
        anim_text(out, s_, CX, y, 64, t, t0, 249.4, "serif_bold", INK, track=0.15, fin=0.9, fout=0.3, glow=0.15,
                  glow_buf=lay)
        anim_text(out, en, CX, y + 64, 28, t, t0 + 0.4, 249.4, "corm", np.array([0.84, 0.72, 0.5]), track=0.08,
                  fin=0.9, fout=0.3)
    hk = T.HITS["final"]
    if hk - 0.02 <= t < 257.0:
        _fin_init()
        g = prog(t, T.LOGO_GATHER, 2.2)
        crisp = eout(prog(t, hk, 0.5)) * (1 - eout(prog(t, T.LOGO_GATHER, 0.7)))
        if crisp > 0:
            text(out, "观点是用来迭代的，", CX, 450, 84, "serif_black", GOLD, crisp, track=0.12, gradient=TITLE_GRAD,
                 glow=0.3, glow_buf=lay)
            text(out, "不是用来捍卫的。", CX, 580, 84, "serif_black", GOLD, crisp, track=0.12, gradient=TITLE_GRAD,
                 glow=0.3, glow_buf=lay)
        shockwave(lay, (CX, 515), t, hk, GOLD, 1300, 1.6, 1.2)
        rays(lay, (CX, 515), 0.12 * eout(prog(t, hk, 0.4)) * (1 - prog(t, 252.5, 2.0)), t * 0.05, GOLD)
        if t >= T.LOGO_GATHER - 0.2:
            P, p = morph(FIN_SRC, FIN_DST, g, FIN_R, 0.45, 0.45)
            P = P + np.c_[np.sin(2.4 * t + FIN_R[:, 0] * 6.28), np.cos(2.1 * t + FIN_R[:, 1] * 6.28)] * 1.2
            col = mixc(GOLD[None, :], FIN_COL, p[:, None])
            # 清晰 logo 出现后，粒子化作四散的微尘
            k = eout(prog(t, T.LOGO_SHOW + 0.4, 2.0))
            drift = (FIN_DST - END_LOGO_C) * 0.9 * k + np.c_[FIN_R[:, 2] - 0.5, FIN_R[:, 0] - 0.5] * 260 * k
            fade = (1 - k) * clip01(prog(t, T.LOGO_GATHER - 0.2, 0.4))
            dots(lay, P + drift, col * ((0.32 + 0.25 * (1 - p)) * fade * (1 - 0.5 * prog(t, T.LOGO_SHOW - 0.6, 0.8)))[:, None], 1.0)
    if t >= T.LOGO_GATHER:
        k = eout(prog(t, T.LOGO_GATHER, 2.4))
        flash = math.exp(-(t - T.BRAND_T) / 0.35) * 2.5 if t >= T.BRAND_T else 0.0
        glow_spot(lay, END_LOGO_C, 160, BLUE, (0.07 + 0.04 * flash) * k * end)
    # 品牌字的柔光（真正的 logo 与文字在 finale_post 中、辉光之后绘制，保证显示原始 logo）
    if t >= T.BRAND_T:
        sp = brand_text("巴芒价值", 112, "serif_black")
        blit_brand(lay, sp, CX, 620, 0.12 * end * float(clip01((t - T.BRAND_T) / 0.9)))


def finale_post(out, t):
    """辉光 / 色调映射之后再画：官方 logo 原图 + 金色品牌字，不被后期改色"""
    if t < T.LOGO_SHOW:
        return
    end = 1.0          # 整片最终淡出由 render_frame 统一处理
    # 清晰的官方 logo
    if t >= T.LOGO_SHOW:
        k = eout(prog(t, T.LOGO_SHOW, 0.9)) * end
        rgb_, a_ = END_LOGO
        composite(out, rgb_, a_ * k, END_LOGO_C[0] - END_LOGO_SIZE / 2, END_LOGO_C[1] - END_LOGO_SIZE / 2)
    # 金色「巴芒价值」+「BUFFETT · MUNGER」：在重拍上出现，扫过流光
    if t >= T.BRAND_T:
        w = float(clip01((t - T.BRAND_T) / 0.9))
        sh = prog(t, T.SHIMMER_T, 1.4)
        sp = brand_text("巴芒价值", 112, "serif_black")
        ty = 620
        blit_brand(out, sp, CX, ty, end, wipe=w, shine=sh)
        hw = sp.w / 2 + 44
        ln = 170 * float(eout(prog(t, T.BRAND_T + 0.3, 1.0)))
        sub_c = np.array(_brand.SUB_GOLD, np.float32) / 255
        for sgn in (-1, 1):
            line(out, (CX + sgn * hw, ty), (CX + sgn * (hw + ln), ty), sub_c, 0.7 * end, 1, "over")
        w2 = float(clip01((t - T.BRAND_T - 0.5) / 0.9))
        sp2 = brand_text("BUFFETT · MUNGER", 30, "corm", gold=False, width=sp.w)
        blit_brand(out, sp2, CX, 712, end, wipe=w2)
        anim_text(out, "先验  ·  证据  ·  更新", CX, 800, 26, t, T.BRAND_T + 1.2, T.DUR, "serif_med", INK * 0.8,
                  track=0.4, fin=1.0, fout=0.01, alpha=end)


# ================================================================ 合成
SCENES = []


def scene(fn):
    SCENES.append(fn)
    return fn


for _fn in (scene_doors, scene_history, scene_title, scene_sim, scene_100, scene_bayes, scene_medical,
            scene_evidence, scene_solve, scene_life, scene_finale):
    scene(_fn)


def final_fade(t):
    return float(clip01((T.DUR - t) / (T.DUR - T.FADE_OUT))) ** 1.3


def render_frame(t):
    global BG
    if BG is None:
        BG = Background()
    out = BG.draw(t)
    lay = np.zeros((H, W, 3), np.float32)       # 发光层（加色，参与辉光）
    T_NOW[0] = t
    for fn in SCENES:
        fn(out, lay, t)
    out += lay
    hk = hit_k(t, 0.3)
    bloom(out, 1.0 + 0.8 * hk)
    # 重拍：闪白 + 推镜 + 色差
    if hk > 0.01:
        out += hk * 0.10
        out[:] = zoom(out, 1 + 0.018 * hk)
        chroma(out, 3.0 * hk)
    tonemap(out)
    vignette(out)
    finale_post(out, t)
    chapter_tag(out, lay, t)
    progress_bar(out, out, t)
    narration(out, t)
    grain(out, t)
    out *= final_fade(t)
    HUD.draw(out, t, final_fade(t))
    return to_u8(out)


def render_chunk(args):
    ci, f0, f1 = args
    cv2.setNumThreads(1)
    path = os.path.join(WORK, f"chunk_{ci}.mp4")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                          "-pix_fmt", "yuv420p", "-threads", "1", path], stdin=subprocess.PIPE)
    for f in range(f0, f1):
        p.stdin.write(render_frame(f / FPS).tobytes())
        if (f - f0) % 150 == 0:
            print(f"chunk {ci}: {f - f0}/{f1 - f0}", flush=True)
    p.stdin.close()
    p.wait()
    return path


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "render"
    os.makedirs(WORK, exist_ok=True)
    if mode == "preview":
        d = os.path.join(WORK, "preview")
        os.makedirs(d, exist_ok=True)
        for s in sys.argv[2:]:
            t = float(s)
            Image.fromarray(render_frame(t)).save(os.path.join(d, f"t{t:06.2f}.png"))
        return
    if mode == "clip":      # 渲染片段：clip t0 t1 out.mp4
        t0, t1, path = float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
        f0, f1 = int(t0 * FPS), int(t1 * FPS)
        workers = int(os.environ.get("WORKERS", 4))
        step = math.ceil((f1 - f0) / workers)
        jobs = [(i, f0 + i * step, min(f1, f0 + (i + 1) * step)) for i in range(workers)]
        with Pool(workers) as pool:
            paths = pool.map(render_chunk, jobs)
        lst = os.path.join(WORK, "chunks.txt")
        open(lst, "w").writelines(f"file '{os.path.abspath(p)}'\n" for p in paths)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-ss", str(t0),
                        "-i", os.path.join(WORK, "score.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", path], check=True)
        return
    total = int(round(T.DUR * FPS))
    workers = int(os.environ.get("WORKERS", 4))
    step = math.ceil(total / workers)
    jobs = [(i, i * step, min(total, (i + 1) * step)) for i in range(workers)]
    with Pool(workers) as pool:
        paths = pool.map(render_chunk, jobs)
    lst = os.path.join(WORK, "chunks.txt")
    open(lst, "w").writelines(f"file '{os.path.abspath(p)}'\n" for p in paths)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    os.path.join(WORK, "video.mp4")], check=True)
    print("done", os.path.join(WORK, "video.mp4"))


if __name__ == "__main__":
    main()
