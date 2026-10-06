"""《爱的本质》3 分钟粒子叙事视频渲染器。

所有画面都是时间 t 的纯函数：粒子在不同"队形"之间变形，文字按音乐节拍出现。
用法：
    python3 render.py preview 12.5 30 70        # 输出若干时间点的预览帧
    python3 render.py render                     # 4 进程并行渲染 + 合成音频
"""
import json
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
W, H, FPS = 1920, 1080, 30
CX, CY = 960, 470
N = 2600

MUSIC = json.load(open(os.path.join(BUILD, "music.json")))
DUR = MUSIC["duration"]
ENV = np.array(MUSIC["env"])
ONS = np.array(MUSIC["onset"])

SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"
SERIF_B = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"
SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
SC = 2  # ttc 中简体中文字形的索引

GOLD = np.array([1.0, 0.70, 0.40])
ROSE = np.array([1.0, 0.42, 0.48])
TEAL = np.array([0.36, 0.70, 0.96])
VIOLET = np.array([0.72, 0.56, 1.0])
WHITE = np.array([0.86, 0.88, 0.95])
INK = np.array([0.92, 0.90, 0.86])
GREY = np.array([0.55, 0.56, 0.60])

# ---------------------------------------------------------------- 工具函数


def clip01(x):
    return np.clip(x, 0.0, 1.0)


def ease(x):
    x = clip01(x)
    return x * x * (3 - 2 * x)


def ease_io(x):
    x = clip01(x)
    return np.where(x < 0.5, 4 * x ** 3, 1 - (-2 * x + 2) ** 3 / 2)


def mix(a, b, k):
    k = np.asarray(k, dtype=np.float64)
    if k.ndim == 1:
        k = k[:, None]
    return a * (1 - k) + b * k


def env_at(t):
    return float(ENV[min(int(t * FPS), len(ENV) - 1)])


def onset_at(t):
    i = int(t * FPS)
    seg = ONS[max(0, i - 4):i + 1]
    # 带衰减的节拍脉冲
    w = np.exp(-np.arange(len(seg))[::-1] / 2.0)
    return float(min(1.5, (seg * w).max())) if len(seg) else 0.0


# ---------------------------------------------------------------- 粒子随机属性

rng = np.random.default_rng(20261004)
R = rng.random((8, N))
G = rng.standard_normal((6, N))
IDX = np.arange(N)
DX = R[0] * (W + 200) - 100
DY = R[1] * (H + 100) - 50

STAR_N = 700
STAR = np.c_[rng.random(STAR_N) * W, rng.random(STAR_N) * H]
STAR_A = rng.random(STAR_N) ** 3 * 0.35 + 0.03
STAR_PH = rng.random(STAR_N) * 6.28
STAR_F = 0.3 + rng.random(STAR_N) * 1.5


def F(P, A, C):
    return np.asarray(P, float), np.broadcast_to(np.asarray(A, float), (N,)).copy(), \
        np.broadcast_to(np.asarray(C, float), (N, 3)).copy()


# ---------------------------------------------------------------- 粒子队形


def f_dust(t, a=0.2):
    x = DX + 26 * np.sin(0.07 * t + R[2] * 6.28)
    y = DY + 18 * np.cos(0.09 * t + R[3] * 6.28)
    A = a * (0.55 + 0.45 * np.sin(1.4 * t * (0.3 + R[4]) + R[5] * 6.28))
    C = mix(WHITE, GOLD, (R[6] < 0.18).astype(float) * 0.8)
    return F(np.c_[x, y], A, C)


def f_halo(t):
    ang = 2 * np.pi * R[0] + 0.05 * t * (1 + R[1] * 0.6)
    rad = 320 + 55 * G[0]
    P = np.c_[CX + rad * np.cos(ang), CY + rad * np.sin(ang)]
    Pd, Ad, Cd = f_dust(t, 0.18)
    sel = R[5] < 0.35
    P[sel] = Pd[sel]
    A = np.where(sel, Ad, 0.26 + 0.12 * np.sin(2 * t + R[3] * 6))
    C = mix(WHITE, GOLD, R[2] * 0.9)
    return F(P, A, C)


CHEM_T = [22.18, 27.24, 32.81, 38.92]
CHEM_POS = np.array([[CX, CY - 245], [CX + 285, CY], [CX, CY + 245], [CX - 285, CY]], float)
CHEM_COL = [GOLD, ROSE, TEAL, VIOLET]
CHEM_NAME = [("多巴胺", "Dopamine"), ("去甲肾上腺素", "Norepinephrine"),
             ("催产素 · 加压素", "Oxytocin · Vasopressin"), ("内啡肽", "Endorphins")]
SYS_T = 43.44


def f_chem(t):
    k = IDX % 5
    P = np.zeros((N, 2))
    A = np.zeros(N)
    C = np.zeros((N, 3))
    # 尚未出场的粒子在外圈缓慢盘旋
    ang = 2 * np.pi * R[0] + 0.06 * t
    rad = 430 + 110 * G[0]
    latent = np.c_[CX + rad * np.cos(ang), CY + rad * np.sin(ang) * 0.75]
    for c in range(4):
        m = k == c
        off = G[1:3, m].T * 30
        d = np.linalg.norm(off, axis=1)
        om = 0.9 / (1 + d / 28) * t
        rot = np.c_[off[:, 0] * np.cos(om) - off[:, 1] * np.sin(om),
                    off[:, 0] * np.sin(om) + off[:, 1] * np.cos(om)]
        breathe = 1 + 0.12 * onset_at(t)
        tgt = CHEM_POS[c] + rot * breathe
        p = ease((t - CHEM_T[c] + 0.5 - R[3, m] * 0.6) / 1.1)[:, None]
        P[m] = latent[m] * (1 - p) + tgt * p
        hot = 0.45 + 0.4 * math.exp(-max(0.0, t - CHEM_T[c]) / 3.0) if t > CHEM_T[c] else 0.45
        A[m] = 0.14 * (1 - p[:, 0]) + hot * p[:, 0]
        C[m] = mix(WHITE, CHEM_COL[c], p[:, 0])
    # 第 5 组：先是中心的金色漩涡，SYS_T 后展开成外圈"四个系统"的环
    m = k == 4
    a2 = 2 * np.pi * R[0, m] + 0.35 * t
    r2 = 70 + 45 * np.abs(G[0, m])
    core = np.c_[CX + r2 * np.cos(a2), CY + r2 * np.sin(a2)]
    a3 = 2 * np.pi * R[0, m] + 0.07 * t
    ring = np.c_[CX + (440 + 6 * G[0, m]) * np.cos(a3), CY + (350 + 6 * G[0, m]) * np.sin(a3)]
    p = ease((t - SYS_T + 0.3 - R[3, m] * 0.7) / 1.4)[:, None]
    P[m] = core * (1 - p) + ring * p
    A[m] = 0.32 + 0.1 * p[:, 0]
    C[m] = mix(GOLD, WHITE, p[:, 0] * 0.5)
    return F(P, A, C)


def f_collapse(t):
    a = 2.0 * t
    off = G[0:2].T * 16
    P = np.c_[CX + off[:, 0] * np.cos(a) - off[:, 1] * np.sin(a),
              CY - 60 + off[:, 0] * np.sin(a) + off[:, 1] * np.cos(a)]
    return F(P, 0.035, mix(GOLD, WHITE, R[2]))


def f_chaos(t):
    jx = 7 * np.sin(3.1 * t * (0.5 + R[4]) + R[5] * 6.28)
    jy = 7 * np.cos(2.7 * t * (0.5 + R[6]) + R[7] * 6.28)
    P = np.c_[CX + G[0] * 430 + jx, CY + G[1] * 230 + jy]
    C = np.where((R[6] < 0.33)[:, None], TEAL, np.where((R[6] < 0.66)[:, None], GOLD, ROSE))
    return F(P, 0.95 + 0.6 * (R[2] < 0.08), C)


def _net_nodes():
    r = np.random.default_rng(3)
    nodes = []
    while len(nodes) < 46:
        x, y = r.uniform(-1, 1, 2)
        if x * x + y * y > 1:
            continue
        p = np.array([CX + x * 720, CY + y * 300])
        if all(np.linalg.norm(p - q) > 92 for q in nodes):
            nodes.append(p)
    nodes = np.array(nodes)
    edges = set()
    for i, p in enumerate(nodes):
        d = np.linalg.norm(nodes - p, axis=1)
        for j in np.argsort(d)[1:4]:
            edges.add((min(i, j), max(i, j)))
    return nodes, np.array(sorted(edges))


NET_N, NET_E = _net_nodes()
NET_T = 60.98
# 四个概念词挂在最左、最上、最右、最下的节点
NET_WORDS = [("记忆", int(np.argmin(NET_N[:, 0]))), ("人格", int(np.argmin(NET_N[:, 1]))),
             ("经历", int(np.argmax(NET_N[:, 0]))), ("社会关系", int(np.argmax(NET_N[:, 1])))]
NET_WT = [63.9, 64.97, 66.0, 67.08]


def net_on(t):
    return ease((t - NET_T - np.arange(len(NET_N)) / len(NET_N) * 2.4) / 0.6)


def f_network(t):
    M = len(NET_N)
    sig = R[5] < 0.38
    node = IDX % M
    on = net_on(t)
    P = NET_N[node] + G[0:2].T * 8
    A = 0.12 + 0.42 * on[node]
    C = mix(TEAL, GOLD, (node % 3 == 0).astype(float))
    e = (R[6] * len(NET_E)).astype(int)
    s = (R[0] + 0.32 * t * (0.5 + R[1])) % 1.0
    a, b = NET_N[NET_E[e, 0]], NET_N[NET_E[e, 1]]
    Ps = a + (b - a) * s[:, None]
    eon = np.minimum(on[NET_E[e, 0]], on[NET_E[e, 1]])
    P[sig] = Ps[sig]
    A[sig] = (0.6 * eon * np.sin(np.pi * s) ** 0.6)[sig]
    C[sig] = GOLD
    return F(P, A, C)


def heart_xy(u):
    hx = 16 * np.sin(u) ** 3
    hy = 13 * np.cos(u) - 5 * np.cos(2 * u) - 2 * np.cos(3 * u) - np.cos(4 * u)
    return hx, -hy


def _heart_u():
    u = np.linspace(0, 2 * np.pi, 4001)
    x, y = heart_xy(u)
    seg = np.r_[0, np.cumsum(np.hypot(np.diff(x), np.diff(y)))]
    return np.interp(R[0] * seg[-1], seg, u)


def f_heart(t):
    u = HEART_U
    hx, hy = heart_xy(u)
    fill = R[5] > 0.7
    k = np.where(fill, np.sqrt(R[1]) * 0.95, 1.0)
    s = 16.5 * (1 + 0.035 * onset_at(t))
    sway = 0.9 + 0.1 * np.cos(0.7 * t)
    P = np.c_[CX + hx * k * s * sway + G[0] * 3, CY - 40 + hy * k * s + G[1] * 3]
    A = np.where(fill, 0.25, 0.62)
    C = mix(ROSE, GOLD, clip01((hy + 13) / 30))
    return F(P, A, C)


HEART_U = _heart_u()
FIRE_T = 79.83


def f_fire(t):
    bottom, top = 900.0, CY - 70
    if t < FIRE_T:
        k = ease((t - 78.55 - R[3] * 0.35) / 1.15)
        P = np.c_[CX + G[0] * 4 * (1 + 3 * (1 - k)), bottom - (bottom - top) * k + G[1] * 5]
        return F(P, 0.55, mix(GOLD, WHITE, R[2] * 0.5))
    dt = t - FIRE_T
    ang = 2 * np.pi * R[0]
    sp = 160 + 420 * np.sqrt(R[1])
    kd = 1.5
    disp = sp * (1 - math.exp(-kd * dt)) / kd
    ground = 948 - 26 * R[4]
    x = CX + np.cos(ang) * disp - 5 * max(0.0, dt - 4) * (0.5 + R[2])
    y = np.minimum(top + np.sin(ang) * disp + 52 * dt * dt * (0.6 + 0.6 * R[6]), ground)
    A = 0.11 + 0.85 * math.exp(-dt / 1.5)
    C = mix(mix(WHITE, GOLD, min(1.0, dt / 0.8)), ROSE * 0.6 + GREY * 0.4, min(1.0, dt / 4.0))
    return F(np.c_[x, y], A * (0.7 + 0.3 * R[3]), C)


RING_T = [95.25, 100.03, 104.81]
RING_R = [150, 265, 380]
RING_SQ = [0.40, 0.44, 0.48]
RING_W = [0.32, -0.2, 0.13]
RING_COL = [GOLD, ROSE, TEAL]
RING_C = (CX - 190, CY + 10)


def f_rings(t):
    g = IDX % 4
    Pd, Ad, Cd = f_dust(t, 0.12)
    P, A, C = Pd.copy(), Ad.copy(), Cd.copy()
    for k in range(3):
        m = g == k
        th = 2 * np.pi * R[0, m] + RING_W[k] * t
        r = RING_R[k] * (1 + 0.012 * G[0, m])
        tgt = np.c_[RING_C[0] + r * np.cos(th), RING_C[1] + r * np.sin(th) * RING_SQ[k] + G[1, m] * 2]
        p = ease((t - RING_T[k] + 0.4 - R[3, m] * 0.7) / 1.2)[:, None]
        P[m] = Pd[m] * (1 - p) + tgt * p
        front = 0.75 + 0.25 * np.sin(th)  # 前半圈更亮，营造纵深
        A[m] = Ad[m] * (1 - p[:, 0]) + (0.55 * front * (1 + 0.25 * onset_at(t))) * p[:, 0]
        C[m] = mix(Cd[m], RING_COL[k], p[:, 0])
    return F(P, A, C)


EX_A = np.array([CX - 190, CY + 10.0])
EX_B = np.array([CX + 190, CY + 10.0])
VALUES = ["情绪支持", "陪伴", "性", "资源", "育儿", "社会支持", "认同", "共同目标", "风险共担"]
VAL_T = [115.73 + i * 0.94 for i in range(9)]
VAL_ANG = np.radians(-90 + np.arange(9) * 40)
VAL_POS = np.c_[CX + 620 * np.cos(VAL_ANG), CY + 10 + 300 * np.sin(VAL_ANG)]


def f_exchange(t):
    g = IDX % 10
    Pd, Ad, Cd = f_dust(t, 0.1)
    P, A, C = Pd.copy(), Ad.copy(), Cd.copy()
    flow = g < 4
    s = (R[0] + 0.24 * t) % 1.0
    fwd = R[1] < 0.5
    arc = np.sin(np.pi * s) * (95 + 20 * G[0])
    base = np.where(fwd[:, None], EX_A + (EX_B - EX_A) * s[:, None], EX_B + (EX_A - EX_B) * s[:, None])
    base[:, 1] += np.where(fwd, -arc, arc)
    P[flow] = base[flow]
    A[flow] = (0.12 + 0.5 * np.sin(np.pi * s) ** 0.5)[flow]
    C[flow] = np.where(fwd[:, None], GOLD, TEAL)[flow]
    for gg, ctr, col in ((4, EX_A, GOLD), (5, EX_B, TEAL)):
        m = g == gg
        P[m] = ctr + G[2:4, m].T * 15
        A[m] = 0.6
        C[m] = col
    m = g >= 6
    node = (IDX // 10) % 9
    on = ease((t - np.array(VAL_T)[node] + 0.3 - R[3] * 0.4) / 0.8)
    tgt = VAL_POS[node] + G[4:6].T * 9
    P[m] = (Pd * (1 - on[:, None]) + tgt * on[:, None])[m]
    A[m] = (Ad * (1 - on) + 0.5 * on)[m]
    C[m] = mix(Cd, mix(GOLD, ROSE, (node % 2).astype(float) * 0.7), on)[m]
    return F(P, A, C)


def scale_theta(t):
    th = 0.0
    for t0, v in ((128.48, 0.15), (130.87, -0.15), (132.98, 0.0)):
        if t >= t0:
            k = float(ease_io((t - t0) / 0.9))
            th = th * (1 - k) + v * k
    return th + 0.01 * math.sin(1.7 * t)


PIVOT = np.array([CX, CY - 70.0])
BEAM_L = 340


def scale_geom(t):
    th = scale_theta(t)
    d = np.array([math.cos(th), math.sin(th)])
    el, er = PIVOT - d * BEAM_L, PIVOT + d * BEAM_L
    return th, el, er, el + [0, 170], er + [0, 170]


def f_scale(t):
    th, el, er, pl, pr = scale_geom(t)
    d = np.array([math.cos(th), math.sin(th)])
    nrm = np.array([-d[1], d[0]])
    g = IDX % 10
    Pd, Ad, Cd = f_dust(t, 0.1)
    P, A, C = Pd.copy(), Ad.copy(), Cd.copy()
    m = g < 3
    u = R[0] * 2 - 1
    P[m] = (PIVOT + np.outer(u * BEAM_L, d) + np.outer(G[0] * 1.5, nrm))[m]
    A[m], C[m] = 0.5, WHITE
    for gg, e, pc, col in ((3, el, pl, GOLD), (4, er, pr, TEAL)):
        mm = g == gg
        a = np.pi * R[1]
        pan = np.c_[pc[0] + 80 * np.cos(a), pc[1] + 26 * np.sin(a)]
        load = np.c_[pc[0] + G[2] * 18, pc[1] - 16 + np.abs(G[3]) * -9]
        q = np.where((R[2] < 0.55)[:, None], pan, load)
        P[mm] = q[mm]
        A[mm] = np.where(R[2] < 0.55, 0.45, 0.62)[mm]
        C[mm] = np.where((R[2] < 0.55)[:, None], WHITE, col)[mm]
    m = g == 5
    P[m] = np.c_[CX + G[0] * 1.5, PIVOT[1] + R[0] * 330][m]
    A[m], C[m] = 0.35, WHITE
    # 信任之线：从 132.98 起在两个秤盘之间亮起一条金色的弧
    m = g == 6
    on = ease((t - 132.98 + 0.2 - R[0] * 0.9) / 0.8)
    s = R[0]
    arc = pl + (pr - pl) * s[:, None]
    arc[:, 1] += 150 * np.sin(np.pi * s)
    P[m] = (Pd * (1 - on[:, None]) + arc * on[:, None])[m]
    A[m] = (Ad * (1 - on) + 0.7 * on)[m]
    C[m] = mix(Cd, GOLD, on)[m]
    return F(P, A, C)


FLOW_T = 137.25


def f_flow(t):
    lanes = 7
    ln = IDX % lanes
    sp = 0.03 * (1 + 0.18 * ln)
    x = (R[0] + sp * t) % 1.0 * 2300 - 190
    div = float(ease((t - 140.97) / 2.0))
    gap = 58 + 34 * div
    amp = 36 + 40 * div * np.abs(ln - 3) / 3
    y = CY + (ln - 3) * gap + amp * np.sin(0.0048 * x + 0.9 * t + ln * 0.9) + G[0] * 5
    edge = clip01(x / 260) * clip01((W - x) / 260)
    C = np.where((ln < 2)[:, None], GOLD, np.where((ln < 5)[:, None], ROSE, TEAL))
    C = mix(C, WHITE, R[2] * 0.3)
    return F(np.c_[x, y], 0.45 * edge, C)


BIN_T = 144.68


def binary_pos(t):
    phi = 1.45 * (t - BIN_T)
    rx, ry, tilt = 230, 82, math.radians(-12)

    def rot(x, y):
        return np.c_[CX + x * math.cos(tilt) - y * math.sin(tilt), CY + x * math.sin(tilt) + y * math.cos(tilt)]
    return phi, rx, ry, rot


def f_binary(t):
    phi, rx, ry, rot = binary_pos(t)
    g = IDX % 5
    Pd, Ad, Cd = f_dust(t, 0.1)
    P, A, C = Pd.copy(), Ad.copy(), Cd.copy()
    br = 1 + 0.15 * onset_at(t)
    ca = rot(np.array([rx * math.cos(phi)]), np.array([ry * math.sin(phi)]))[0]
    cb = rot(np.array([-rx * math.cos(phi)]), np.array([-ry * math.sin(phi)]))[0]
    for gg, ctr, col in ((0, ca, GOLD), (1, cb, TEAL)):
        m = g == gg
        P[m] = ctr + G[0:2, m].T * 13 * br
        A[m], C[m] = 0.6, col
    for gg, off, col in ((2, 0.0, GOLD), (3, np.pi, TEAL)):
        m = g == gg
        th = phi + off - R[0, m] * 2.6
        P[m] = rot(rx * np.cos(th) + G[1, m] * 3, ry * np.sin(th) + G[2, m] * 3)
        A[m] = 0.55 * (1 - R[0, m]) ** 1.5 + 0.05
        C[m] = col
    return F(P, A, C)


def f_galaxy(t):
    arm = IDX % 2
    rr = R[0] ** 0.8
    th = np.pi * arm + 3.4 * rr + 0.09 * t
    rad = 40 + 470 * rr
    sp = G[0] * (12 + 40 * rr)
    x = rad * np.cos(th) + sp * np.cos(th + 1.57)
    y = (rad * np.sin(th) + sp * np.sin(th + 1.57)) * 0.42
    C = mix(GOLD, mix(ROSE, TEAL, clip01(rr * 2 - 1)), clip01(rr * 2))
    return F(np.c_[CX + x, CY + 20 + y], 0.22 + 0.15 * (1 - rr), C)


def _glyph_points(ch, size, cx, cy):
    font = ImageFont.truetype(SERIF_B, size, index=SC)
    img = Image.new("L", (W, H), 0)
    ImageDraw.Draw(img).text((cx, cy), ch, font=font, fill=255, anchor="mm")
    a = np.asarray(img, dtype=np.float64)
    ys, xs = np.nonzero(a > 40)
    r = np.random.default_rng(11)
    pick = r.choice(len(xs), N, replace=len(xs) < N, p=a[ys, xs] / a[ys, xs].sum())
    return np.c_[xs[pick] + r.random(N), ys[pick] + r.random(N)]


AI_PTS = _glyph_points("爱", 560, CX, CY - 10)


def f_ai(t):
    P = AI_PTS + np.c_[1.4 * np.sin(2.2 * t + R[0] * 6.28), 1.4 * np.cos(1.9 * t + R[1] * 6.28)]
    C = mix(GOLD, ROSE, clip01((AI_PTS[:, 1] - 230) / 470))
    tw = 0.5 + 0.3 * np.sin(3 * t * (0.4 + R[2]) + R[3] * 6.28)
    return F(P, tw * (1 + 0.2 * onset_at(t)), C)


# ---------------------------------------------------------------- 巴芒价值品牌（统一使用仓库根目录 brand/）

sys.path.insert(0, os.path.join(HERE, "..", "brand"))
import brand as _brand  # noqa: E402
from brand import Hud, load_logo  # noqa: E402

HUD = Hud()
LOGO_BLUE = np.array([110, 175, 255], np.float32) / 255   # 品牌规范里 logo 光晕的淡蓝
GOLD_STOPS = _brand.GOLD_STOPS
SUB_GOLD = np.array(_brand.SUB_GOLD, np.float32) / 255

END_LOGO_SIZE = 220          # 品牌规范：片尾 logo 约 220px 居中
END_LOGO_C = (CX, 390)
END_LOGO = load_logo(END_LOGO_SIZE)
LOGO_T = 173.9        # 粒子"爱"开始重组为 logo
LOGO_SHOW = 175.2     # 清晰 logo 浮现
BRAND_T = 175.78      # "巴芒价值"在重拍上出现


def _logo_points():
    rgb, a = END_LOGO
    a = a.astype(np.float64)
    ys, xs = np.nonzero(a > 0.3)
    r = np.random.default_rng(13)
    pick = r.choice(len(xs), N, replace=len(xs) < N, p=a[ys, xs] / a[ys, xs].sum())
    pts = np.c_[xs[pick] + r.random(N) - END_LOGO_SIZE / 2 + END_LOGO_C[0],
                ys[pick] + r.random(N) - END_LOGO_SIZE / 2 + END_LOGO_C[1]]
    return pts, rgb[ys[pick], xs[pick]].astype(np.float64)


LOGO_PTS, LOGO_COL = _logo_points()


def f_logo(t):
    P = LOGO_PTS + np.c_[1.2 * np.sin(2.4 * t + R[0] * 6.28), 1.2 * np.cos(2.1 * t + R[1] * 6.28)]
    # 清晰 logo 出现后，粒子慢慢化作四散的微尘
    k = float(ease((t - LOGO_SHOW - 0.6) / 2.5))
    drift = np.c_[G[0], G[1]] * 140 * k
    fade = float(clip01((179.4 - t) / 1.8))
    return F(P + drift, (0.75 - 0.55 * k) * fade, mix(LOGO_COL, WHITE, R[2] * 0.25))


def blit_rgba(out, rgb, a, x0, y0, alpha=1.0, wipe=1.0, shine=None):
    """把 (rgb, a) 贴到 out 的 (x0, y0) 处；shine 为 0~1 的流光位置。"""
    if alpha <= 0.003:
        return
    h, w = a.shape
    x0, y0 = int(round(x0)), int(round(y0))
    a = a * alpha
    if wipe < 1.0:
        soft = 0.35 * w + 30
        a = a * clip01((wipe * (w + soft) - np.arange(w)) / soft).astype(np.float32)[None, :]
    if shine is not None and 0 < shine < 1:
        xs = np.arange(w)[None, :] + np.arange(h)[:, None] * 0.6
        pos = -60 + (0.5 - 0.5 * math.cos(shine * math.pi)) * (w + 120)
        rgb = np.clip(rgb + np.exp(-((xs - pos) / (0.06 * w + 10)) ** 2)[..., None] * 0.6, 0, 1.25)
    xs, ys = max(0, x0), max(0, y0)
    xe, ye = min(W, x0 + w), min(H, y0 + h)
    if xe <= xs or ye <= ys:
        return
    a = a[ys - y0:ye - y0, xs - x0:xe - x0, None]
    reg = out[ys:ye, xs:xe]
    reg *= 1 - a
    reg += a * rgb[ys - y0:ye - y0, xs - x0:xe - x0]


_BRAND_TEXT = {}


def brand_text(text, size, fontname, track=0.0, gold=True):
    """用品牌字体（思源宋体 Black / Cormorant）渲染文字，金色竖向渐变。"""
    key = (text, size, fontname, track, gold)
    if key not in _BRAND_TEXT:
        f = _brand._font(fontname, size)
        widths = [f.getlength(c) for c in text]
        w = int(sum(widths) + track * size * (len(text) - 1)) + 20
        h = int(size * 1.6)
        im = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(im)
        x = 10.0
        for c, cw in zip(text, widths):
            d.text((x, int(size * 1.25)), c, font=f, fill=255, anchor="ls")
            x += cw + track * size
        m = np.asarray(im, np.float32) / 255
        ys, xs = np.where(m > 0.01)
        m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        if gold:
            rgb = np.broadcast_to(_brand._ramp(m.shape[0], GOLD_STOPS)[:, None, :].astype(np.float32),
                                  m.shape + (3,)).copy()
        else:
            rgb = np.broadcast_to(SUB_GOLD, m.shape + (3,)).copy()
        _BRAND_TEXT[key] = (rgb, m)
    return _BRAND_TEXT[key]


KEYS = [
    (0.0, 0.0, f_dust),
    (10.2, 1.6, f_halo),
    (17.14, 1.4, f_chem),
    (48.48, 0.7, f_collapse),
    (53.8, 1.3, f_chaos),
    (60.98, 2.6, f_network),
    (69.75, 2.2, f_heart),
    (78.51, 0.5, f_fire),
    (94.6, 1.2, f_rings),
    (111.2, 1.4, f_exchange),
    (128.2, 1.0, f_scale),
    (137.25, 1.6, f_flow),
    (144.68, 1.6, f_binary),
    (148.93, 1.8, f_galaxy),
    (161.96, 2.4, f_ai),
    (LOGO_T, 1.6, f_logo),
]


def particles(t):
    k = max(i for i, key in enumerate(KEYS) if key[0] <= t)
    t0, dur, fn = KEYS[k]
    Pb, Ab, Cb = fn(t)
    if k == 0 or t >= t0 + dur:
        return Pb, Ab, Cb
    Pa, Aa, Ca = KEYS[k - 1][2](t)
    p = ease((t - t0 - R[7] * 0.3 * dur) / (0.7 * dur))
    d = Pb - Pa
    nrm = np.c_[-d[:, 1], d[:, 0]]
    curl = (np.sin(np.pi * p) * G[5] * 0.22)[:, None]
    P = Pa + d * p[:, None] + nrm * curl
    A = Aa * (1 - p) + Ab * p
    C = mix(Ca, Cb, p)
    return P, A, C


# ---------------------------------------------------------------- 文字

_FONTS = {}
_SPRITES = {}


def font(path, size):
    key = (path, size)
    if key not in _FONTS:
        _FONTS[key] = ImageFont.truetype(path, size, index=SC)
    return _FONTS[key]


def sprite(text, path, size, track):
    """返回 (全部文字遮罩, 基线高度, 高亮文字遮罩)；【】包住的字会被高亮。"""
    key = (text, path, size, track)
    if key in _SPRITES:
        return _SPRITES[key]
    chars, hot, on = [], [], False
    for ch in text:
        if ch in "【】":
            on = ch == "【"
            continue
        chars.append(ch)
        hot.append(on)
    f = font(path, size)
    asc, desc = f.getmetrics()
    widths = [f.getlength(ch) for ch in chars]
    w = int(sum(widths) + track * max(0, len(chars) - 1)) + 8
    h = asc + desc + 8
    img = Image.new("L", (w, h), 0)
    img_h = Image.new("L", (w, h), 0)
    d, dh = ImageDraw.Draw(img), ImageDraw.Draw(img_h)
    x = 4.0
    for ch, cw, hh in zip(chars, widths, hot):
        d.text((x, 4 + asc), ch, font=f, fill=255, anchor="ls")
        if hh:
            dh.text((x, 4 + asc), ch, font=f, fill=255, anchor="ls")
        x += cw + track
    arr = np.asarray(img, dtype=np.float32) / 255.0
    hl = np.asarray(img_h, dtype=np.float32) / 255.0 if any(hot) else None
    _SPRITES[key] = (arr, asc, hl)
    return _SPRITES[key]


HL = np.array([255, 212, 120], np.float32) / 255  # 品牌金


def blit(out, text, x, y, size=40, path=SERIF, color=INK, alpha=1.0, anchor="m", track=None,
         wipe=1.0):
    """anchor: m 居中 / l 左对齐 / r 右对齐；y 为文字视觉中线。"""
    if alpha <= 0.003:
        return
    track = size * 0.12 if track is None else track
    arr, asc, hl = sprite(text, path, size, track)
    h, w = arr.shape
    x0 = {"m": x - w / 2, "l": x - 4, "r": x - w + 4}[anchor]
    y0 = y - 4 - asc * 0.62
    x0, y0 = int(round(x0)), int(round(y0))
    a = arr * alpha
    if wipe < 1.0:
        soft = 0.35 * w + 30
        col = clip01((wipe * (w + soft) - np.arange(w)) / soft).astype(np.float32)
        a = a * col[None, :]
    xs, ys = max(0, x0), max(0, y0)
    xe, ye = min(W, x0 + w), min(H, y0 + h)
    if xe <= xs or ye <= ys:
        return
    a = a[ys - y0:ye - y0, xs - x0:xe - x0, None]
    reg = out[ys:ye, xs:xe]
    reg *= 1 - a
    if hl is None:
        reg += a * np.asarray(color, np.float32)
    else:
        k = hl[ys - y0:ye - y0, xs - x0:xe - x0, None]
        reg += a * (np.asarray(color, np.float32) * (1 - k) + HL * k)


def text_alpha(t, t0, t1, fin=0.8, fout=0.6):
    if t < t0 or t > t1 + fout:
        return 0.0, 0.0
    a = float(ease((t1 + fout - t) / fout)) if t > t1 else 1.0
    return a, float(clip01((t - t0) / fin))


# 旁白：(开始, 结束, 文本)
NARRATION = [
    (18.46, 21.9, "当你爱上一个人，大脑里正在发生什么？"),
    (22.18, 26.9, "【多巴胺】—— 渴望与奖赏预期，让你忍不住想见 TA"),
    (27.24, 32.5, "【去甲肾上腺素】—— 心跳加速，注意力只追随一个人"),
    (32.81, 38.6, "【催产素】与【加压素】—— 依恋与联结，让你想靠近、想守护"),
    (38.92, 43.1, "【内啡肽】—— 舒适与安心，是长久亲密的底色"),
    (43.44, 48.1, "奖赏、依恋、性动机、认知评价 —— 【四个系统】共同驱动"),
    (53.8, 57.2, "一个神经元，【不会思考】"),
    (57.52, 60.7, "一个分子，也【不会去爱】"),
    (60.98, 63.6, "可当亿万个连接彼此交织……"),
    (63.9, 69.4, "再与记忆、人格、经历和社会关系融为一体"),
    (74.0, 78.2, "【化学】是音符，【爱】是整首乐曲"),
    (79.83, 82.8, "心动，是一场化学的【烟火】"),
    (83.03, 87.0, "可烟火，【终会落下】"),
    (87.28, 91.2, "激情会退潮，新鲜感会褪色"),
    (95.25, 99.7, "每一段关系，都要回答【三个问题】"),
    (109.06, 111.0, "靠近容易，难的是【留下】"),
    (112.27, 115.5, "婚姻的底层，是长期的【价值互惠】"),
    (124.23, 128.2, "不是即时的等价交易，而是一场【长期的合作】"),
    (128.48, 130.6, "你低谷时，我多扛一点"),
    (130.87, 132.7, "我脆弱时，你多给一点"),
    (132.98, 137.0, "【信任与承诺】，允许短期的不对称"),
    (137.25, 140.7, "但所有这些条件，都【不是永久的】"),
    (140.97, 144.4, "吸引力会变，价值会变，人也会变"),
    (144.68, 148.6, "关系不是建好的房子，而是需要维护的【动态均衡】"),
    (164.35, 166.5, "爱不是一个【名词】，而是一个【动词】"),
    (166.74, 168.9, "是每一天，重新【选择】彼此"),
    (169.13, 171.5, "好的关系，就像一笔好的投资"),
    (171.78, 174.3, "【长期】、【互惠】，然后交给时间去【复利】"),
]

CHAPTERS = [
    (17.14, 48.48, "01", "心动", "ATTRACTION · 神经化学"),
    (48.48, 78.51, "02", "涌现", "EMERGENCE · 整体大于部分之和"),
    (78.51, 95.25, "03", "退潮", "EBB · 激情的半衰期"),
    (95.25, 111.2, "04", "模型", "THE MODEL · 关系的三层结构"),
    (111.2, 137.25, "05", "互惠", "RECIPROCITY · 长期合作"),
    (137.25, 148.93, "06", "流动", "FLUX · 动态均衡"),
    (148.93, 169.13, "07", "本质", "ESSENCE · 化学与选择"),
]


# ---------------------------------------------------------------- 画面组件

BG = None


def background():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - CX) / W) ** 2 + ((yy - CY) / H) ** 2)
    v = np.exp(-d * d * 5.0)[..., None]
    base = np.array([0.020, 0.022, 0.034], np.float32)
    lift = np.array([0.030, 0.026, 0.040], np.float32)
    return base + lift * v


def splat(buf, P, Wt):
    """双线性 + 2x2 亚像素叠加绘制点（加法混合）。"""
    ok = (P[:, 0] > 1) & (P[:, 0] < W - 2) & (P[:, 1] > 1) & (P[:, 1] < H - 2) & (Wt.sum(1) > 1e-4)
    P, Wt = P[ok], Wt[ok]
    if not len(P):
        return
    idx_all, w_all = [], []
    for ox, oy in ((-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5)):
        x, y = P[:, 0] + ox, P[:, 1] + oy
        x0, y0 = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
        fx, fy = x - x0, y - y0
        for dx, dy, ww in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
                           (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            idx_all.append((y0 + dy) * W + (x0 + dx))
            w_all.append(ww * 0.25)
    idx = np.concatenate(idx_all)
    ww = np.concatenate(w_all)
    reps = len(idx_all)
    flat = buf.reshape(-1, 3)
    for c in range(3):
        wc = ww * np.tile(Wt[:, c], reps)
        flat[:, c] += np.bincount(idx, weights=wc, minlength=W * H)[:W * H].astype(np.float32)


def glow_point(lo, x, y, color, k):
    """在 1/4 分辨率的辉光缓冲里加一个光点。"""
    xi, yi = int(x / 4), int(y / 4)
    if 0 <= xi < lo.shape[1] and 0 <= yi < lo.shape[0]:
        lo[yi, xi] += np.asarray(color, np.float32) * k


def line(layer, p, q, color, a, th=1):
    c = tuple(float(v * a) for v in color)
    cv2.line(layer, (int(p[0] * 16), int(p[1] * 16)), (int(q[0] * 16), int(q[1] * 16)), c, th,
             cv2.LINE_AA, shift=4)


def decor(t, lay, lo, out_texts):
    """每个章节的连线、光点和标注文字。"""
    # 开场：两束光从两侧靠近，相遇处成为标题中间的点
    if t < 18.5:
        k = float(ease_io((t - 1.2) / 9.55))
        fade = float(clip01((t - 0.8) / 1.5))
        if t < 10.75:
            for s, col in ((-1, GOLD), (1, TEAL)):
                x = CX + s * (760 - 760 * k)
                y = CY + 30 * math.sin(t * 1.3 + s)
                glow_point(lo, x, y, col, 2.2 * fade)
                lay[int(y) - 1:int(y) + 2, int(x) - 1:int(x) + 2] += col * 0.9 * fade
        else:
            flash = math.exp(-(t - 10.75) / 0.6) * 6
            burst = float(clip01((17.14 - t) / 0.4)) if t > 16.7 else 1.0
            glow_point(lo, CX, CY, GOLD, (1.6 + flash + 0.6 * onset_at(t)) * burst)
            lay[CY - 1:CY + 2, CX - 1:CX + 2] += GOLD * burst
    # 01 化学：中心到四个分子簇的连线 + 名称
    if 17.14 <= t < 49.0:
        fo = float(clip01((48.6 - t) / 0.5))
        glow_point(lo, CX, CY, GOLD, (0.8 + 0.8 * onset_at(t)) * fo)
        for c in range(4):
            on = float(ease((t - CHEM_T[c] + 0.2) / 1.0)) * fo
            if on <= 0:
                continue
            p = CHEM_POS[c]
            line(lay, (CX, CY), p, CHEM_COL[c], 0.25 * on)
            glow_point(lo, p[0], p[1], CHEM_COL[c], 1.4 * on * (1 + 0.5 * onset_at(t)))
            name, en = CHEM_NAME[c]
            sys_fade = float(clip01((SYS_T + 0.6 - t) / 0.6))
            a = on * (0.15 + 0.85 * sys_fade)
            if c == 0:
                xy, an = (p[0], p[1] - 85), "m"
            elif c == 1:
                xy, an = (p[0] + 70, p[1]), "l"
            elif c == 2:
                xy, an = (p[0], p[1] + 85), "m"
            else:
                xy, an = (p[0] - 70, p[1]), "r"
            out_texts.append((name, xy[0], xy[1] - 12, 28, SERIF, CHEM_COL[c] * 0.5 + 0.5, a, an))
            out_texts.append((en, xy[0], xy[1] + 22, 15, SANS, GREY, a * 0.9, an))
        sys_on = float(ease((t - SYS_T) / 1.2)) * fo
        if sys_on > 0:
            names = ["奖赏系统", "依恋系统", "性动机系统", "认知评价系统"]
            for i, nm in enumerate(names):
                ang = math.radians(-135 + 90 * i)
                x, y = CX + 470 * math.cos(ang), CY + 380 * math.sin(ang)
                k2 = float(ease((t - SYS_T - i * 0.5) / 0.8)) * fo
                glow_point(lo, CX + 440 * math.cos(ang), CY + 350 * math.sin(ang), WHITE, 1.2 * k2)
                out_texts.append((nm, x + (30 if i in (1, 2) else -30), y, 26, SERIF, INK, k2,
                                  "l" if i in (1, 2) else "r"))
    # 02 网络：节点连线 + 四个概念词
    if 60.98 <= t < 72.5:
        on = net_on(t)
        fo = float(clip01((71.8 - t) / 1.2))
        for a_, b_ in NET_E:
            k = min(on[a_], on[b_]) * fo
            if k > 0:
                line(lay, NET_N[a_], NET_N[b_], TEAL, 0.2 * k)
        for (w_, n_), t0 in zip(NET_WORDS, NET_WT):
            k = float(ease((t - t0) / 0.7)) * fo
            p = NET_N[n_]
            glow_point(lo, p[0], p[1], GOLD, 2.5 * k)
            dy = -40 if p[1] < CY else 40
            out_texts.append((w_, p[0], p[1] + dy, 28, SERIF, GOLD * 0.6 + 0.4, k, "m"))
    # 03 烟火爆开的一瞬
    if FIRE_T - 0.1 <= t < FIRE_T + 1.5:
        glow_point(lo, CX, CY - 70, WHITE, 12 * math.exp(-(t - FIRE_T) / 0.25))
    # 04 三层同心环 + 右侧标签
    if 94.8 <= t < 111.9:
        fo = float(clip01((111.6 - t) / 0.6))
        heads = [("吸引力", "决定我们 为什么靠近"), ("价值互惠", "决定我们 为什么留下"),
                 ("信任与承诺", "决定我们在波动时 为什么不立刻离开")]
        for k in range(3):
            on = float(ease((t - RING_T[k]) / 0.9)) * fo
            if on <= 0:
                continue
            cv2.ellipse(lay, (RING_C[0] * 16, RING_C[1] * 16),
                        (int(RING_R[k] * 16), int(RING_R[k] * RING_SQ[k] * 16)), 0, 0, 360,
                        tuple(float(v) * 0.13 * on for v in RING_COL[k]), 1, cv2.LINE_AA, 4)
            ly = 300 + k * 135
            ex = (RING_C[0] + RING_R[k] * 0.94, RING_C[1] - RING_R[k] * RING_SQ[k] * 0.34)
            line(lay, ex, (1300, ly), RING_COL[k], 0.35 * on)
            glow_point(lo, ex[0], ex[1], RING_COL[k], 1.5 * on)
            out_texts.append((heads[k][0], 1320, ly - 16, 44, SERIF, RING_COL[k] * 0.55 + 0.45, on, "l"))
            out_texts.append((heads[k][1], 1322, ly + 30, 22, SANS, GREY * 1.3, on * 0.95, "l"))
        glow_point(lo, RING_C[0] - 14 * math.cos(t), RING_C[1], GOLD, 1.6 * fo)
        glow_point(lo, RING_C[0] + 14 * math.cos(t), RING_C[1], TEAL, 1.6 * fo)
    # 05 互惠：两个人 + 九种价值
    if 111.2 <= t < 128.8:
        fi = float(ease((t - 111.4) / 1.2)) * float(clip01((128.6 - t) / 0.5))
        glow_point(lo, *EX_A, GOLD, 2.4 * fi)
        glow_point(lo, *EX_B, TEAL, 2.4 * fi)
        out_texts.append(("你", EX_A[0], EX_A[1] + 52, 24, SERIF, GOLD * 0.6 + 0.4, fi * 0.8, "m"))
        out_texts.append(("我", EX_B[0], EX_B[1] + 52, 24, SERIF, TEAL * 0.6 + 0.4, fi * 0.8, "m"))
        for i, v in enumerate(VALUES):
            on = float(ease((t - VAL_T[i]) / 0.6)) * fi
            if on <= 0:
                continue
            p = VAL_POS[i]
            line(lay, p, EX_A, GOLD, 0.10 * on)
            line(lay, p, EX_B, TEAL, 0.10 * on)
            glow_point(lo, p[0], p[1], GOLD * 0.5 + ROSE * 0.5, 1.6 * on)
            c, s = math.cos(VAL_ANG[i]), math.sin(VAL_ANG[i])
            if abs(c) < 0.35:
                xy, an = (p[0], p[1] + (-46 if s < 0 else 46)), "m"
            else:
                xy, an = (p[0] + (40 if c > 0 else -40), p[1]), ("l" if c > 0 else "r")
            out_texts.append((v, xy[0], xy[1], 26, SERIF, INK, on, an))
    # 05 天平
    if 128.2 <= t < 138.0:
        fo = float(ease((t - 128.3) / 0.8)) * float(clip01((137.8 - t) / 0.6))
        th, el, er, pl, pr = scale_geom(t)
        for e, pc in ((el, pl), (er, pr)):
            line(lay, e, (pc[0] - 80, pc[1]), WHITE, 0.22 * fo)
            line(lay, e, (pc[0] + 80, pc[1]), WHITE, 0.22 * fo)
            glow_point(lo, e[0], e[1], WHITE, 0.8 * fo)
        glow_point(lo, PIVOT[0], PIVOT[1], GOLD, 2.0 * fo)
        trust = float(ease((t - 132.98) / 1.0)) * fo
        if trust > 0:
            out_texts.append(("信任 · 承诺", CX, (pl[1] + pr[1]) / 2 + 190, 26, SERIF, GOLD * 0.6 + 0.4,
                              trust, "m"))
    # 06 双星
    if 144.68 <= t < 151.5:
        fo = float(ease((t - 145.2) / 1.0)) * float(clip01((151.0 - t) / 1.2))
        phi, rx, ry, rot = binary_pos(t)
        glow_point(lo, *rot(np.array([rx * math.cos(phi)]), np.array([ry * math.sin(phi)]))[0], GOLD, 2.5 * fo)
        glow_point(lo, *rot(np.array([-rx * math.cos(phi)]), np.array([-ry * math.sin(phi)]))[0], TEAL,
                   2.5 * fo)
        glow_point(lo, CX, CY, WHITE, 0.7 * fo)
    # 07 银河中心 & 爱
    if 148.93 <= t < 175.0:
        glow_point(lo, CX, CY + 20, GOLD, 1.2 * float(ease((t - 149.5) / 2)) * float(clip01((162.5 - t) / 1)))
    if t >= LOGO_T:
        k = float(ease((t - LOGO_T) / 1.6)) * float(clip01((179.6 - t) / 2.0))
        flash = math.exp(-(t - BRAND_T) / 0.35) * 5 if t >= BRAND_T else 0.0
        glow_point(lo, END_LOGO_C[0], END_LOGO_C[1], LOGO_BLUE, (2.5 + flash) * k)


def brand_alpha(t):
    """右上角品牌角标：开场淡入，片尾大 logo 出现前淡出。"""
    return float(clip01((t - 0.3) / 1.5)) * float(clip01((LOGO_T + 0.6 - t) / 0.8))


def hud(t, out, lay):
    """左上标题、右上品牌、右下章节号、底部带章节名的时间轴。"""
    fade = float(clip01((t - 1.0) / 2.0)) * float(clip01((LOGO_T + 0.5 - t) / 1.2))
    blit(out, "爱的本质", 60, 46, 22, SERIF, INK, 0.75 * fade, "l", track=6)
    blit(out, "THE NATURE OF LOVE", 60, 76, 12, SANS, GREY, 0.7 * fade, "l", track=4)
    # 时间轴：章节名常显，当前章节点亮，让观众知道"走到哪了、后面还有什么"
    x0, x1, y = 60, 1860, 1040
    prog = t / DUR
    cv2.line(lay, (x0, y), (x1, y), tuple(float(v) * 0.10 * fade for v in WHITE), 1, cv2.LINE_AA)
    xp = x0 + (x1 - x0) * prog
    cv2.line(lay, (x0, y), (int(xp), y), tuple(float(v) * 0.45 * fade for v in GOLD), 1, cv2.LINE_AA)
    pulse = 0.0
    for (c0, c1, num, name, en) in CHAPTERS:
        x = x0 + (x1 - x0) * c0 / DUR
        cur = c0 <= t < c1
        done = t >= c1
        cv2.line(lay, (int(x), y - 9), (int(x), y),
                 tuple(float(v) * (0.6 if cur or done else 0.25) * fade for v in (GOLD if cur or done else WHITE)), 1)
        col = HL if cur else (GREY * 1.25 if done else GREY * 0.9)
        blit(out, f"{num} {name}", x + 6, y - 15, 13, SERIF, col, (1.0 if cur else 0.75) * fade, "l", track=2)
        if t >= c0:
            pulse = max(pulse, math.exp(-(t - c0) / 0.4))
        a, w = text_alpha(t, c0 + 0.3, c1 - 0.6, 1.0, 0.6)
        if a > 0:
            blit(out, num, 1860, 828, 64, SERIF, INK, a * 0.9, "r", track=4, wipe=w)
            blit(out, name, 1860, 890, 28, SERIF, INK, a * 0.9, "r", track=8, wipe=w)
            blit(out, en, 1860, 924, 14, SANS, GREY, a * 0.85, "r", track=2, wipe=w)
            ln = int(110 * float(ease(w)))
            cv2.line(lay, (1860 - ln, 907), (1860, 907), tuple(float(v) * 0.6 * a for v in GOLD), 1, cv2.LINE_AA)
    r = 2 + int(5 * pulse)
    lay[y - r:y + r + 1, int(xp) - r:int(xp) + r + 1] += GOLD * (0.8 + 0.6 * pulse) * fade


def center_texts(t, out):
    """不跟随旁白位置的居中大字。"""
    items = [
        (1.18, 5.1, "人类写了几千年的诗", CY + 2, 46),
        (5.43, 9.9, "只为回答同一个问题", CY + 2, 46),
        (48.48, 49.3, "但", CY + 120, 96),
        (49.55, 53.3, "爱，并不等于几种化学物质", CY + 120, 50),
        (91.53, 94.9, "那么，是什么让两个人【留下来】？", CY - 60, 50),
        (148.93, 150.3, "所以，爱是什么？", CY + 20, 52),
    ]
    for t0, t1, s, y, sz in items:
        a, w = text_alpha(t, t0, t1, 0.9, 0.5)
        if a > 0:
            blit(out, s, CX, y - 10 * (1 - w), sz, SERIF, INK, a, "m", track=sz * 0.18, wipe=w)
    # 标题：爱 · 是什么（两束光在中点相遇），下方一句"承诺"让人愿意看完
    a, w = text_alpha(t, 10.95, 16.9, 1.4, 0.35)
    if a > 0:
        blit(out, "爱", CX - 54, CY, 120, SERIF, INK, a, "r", track=0, wipe=w)
        blit(out, "是什么", CX + 54, CY, 120, SERIF, INK, a, "l", track=14, wipe=w)
        a2, w2 = text_alpha(t, 12.89, 16.9, 1.2, 0.35)
        blit(out, "3 分钟，从【一次心跳】，到【一生的选择】", CX, CY + 118, 26, SERIF, INK * 0.9, a2, "m",
             track=6, wipe=w2)
    # 涌现
    a, w = text_alpha(t, 69.75, 73.6, 1.2, 0.5)
    if a > 0:
        blit(out, "爱，是一种【涌现】", CX, 930, 54, SERIF, INK, a, "m", track=12, wipe=w)
    # 四句对仗
    lines = [(150.53, "心动，是【化学】"), (153.72, "相守，是【选择】"), (156.11, "被爱，是【幸运】"),
             (159.03, "去爱，是【能力】")]
    for i, (t0, s) in enumerate(lines):
        a, w = text_alpha(t, t0, 161.4, 0.8, 0.6)
        if a > 0:
            hl = 1.0 if i == max(j for j, (tt, _) in enumerate(lines) if tt <= t) or t > 160.5 else 0.55
            blit(out, s, CX, 300 + i * 112, 52, SERIF, INK, a * hl, "m", track=14, wipe=w)
    # 片尾（品牌规范）：大号 logo + 金色「巴芒价值」+「BUFFETT · MUNGER」
    end = float(clip01((179.8 - t) / 1.3))
    if t >= LOGO_SHOW:
        k = float(ease((t - LOGO_SHOW) / 0.9)) * end
        rgb, m = END_LOGO
        blit_rgba(out, rgb, m, END_LOGO_C[0] - END_LOGO_SIZE / 2, END_LOGO_C[1] - END_LOGO_SIZE / 2, k)
    if t >= BRAND_T:
        w = float(clip01((t - BRAND_T) / 0.9))
        sh = float(clip01((t - 176.7) / 1.4))
        rgb, m = brand_text("巴芒价值", 112, "serif_black", track=0.08)
        ty = 620
        blit_rgba(out, rgb, m, CX - m.shape[1] / 2, ty - m.shape[0] / 2, end, wipe=w, shine=sh)
        hw = m.shape[1] / 2 + 44
        ln = 170 * float(ease((t - BRAND_T - 0.3) / 1.0))
        for sgn in (-1, 1):
            xa, xb = CX + sgn * hw, CX + sgn * (hw + ln)
            cv2.line(out, (int(min(xa, xb)), ty), (int(max(xa, xb)), ty), tuple(float(v) * 0.7 * end for v in SUB_GOLD),
                     1, cv2.LINE_AA)
        w2 = float(clip01((t - 176.3) / 0.9))
        rgb, m = brand_text("BUFFETT · MUNGER", 30, "corm", track=0.46, gold=False)
        blit_rgba(out, rgb, m, CX - m.shape[1] / 2, 712 - m.shape[0] / 2, end, wipe=w2)
        a3, w3 = text_alpha(t, 176.9, 179.0, 1.0, 0.8)
        blit(out, "长期  ·  互惠  ·  复利", CX, 800, 28, SERIF, INK * 0.8, a3 * end, "m", track=8, wipe=w3)


def render_frame(t):
    global BG
    if BG is None:
        BG = background()
    buf = np.zeros((H, W, 3), np.float32)
    lay = np.zeros((H, W, 3), np.float32)
    lo = np.zeros((H // 4, W // 4, 3), np.float32)
    texts = []

    gfade = float(clip01(t / 1.2)) * float(clip01((DUR - t) / 0.8))
    tw = STAR_A * (0.6 + 0.4 * np.sin(STAR_F * t + STAR_PH))
    splat(buf, STAR, (tw[:, None] * WHITE[None, :]))

    P, A, C = particles(t)
    gain = 1.0 + 0.3 * onset_at(t) * min(1.0, env_at(t))
    splat(buf, P, (A * gain)[:, None] * C * 2.2)

    decor(t, lay, lo, texts)
    buf += lay
    buf *= gfade

    small = cv2.resize(buf, (W // 4, H // 4), interpolation=cv2.INTER_AREA) * 7.0 + lo * gfade
    g1 = cv2.GaussianBlur(small, (0, 0), 2.2)
    g2 = cv2.GaussianBlur(cv2.resize(small, (W // 8, H // 8), interpolation=cv2.INTER_AREA), (0, 0), 4.5)
    glow = cv2.resize(g1, (W, H), interpolation=cv2.INTER_LINEAR) * 0.55 + \
        cv2.resize(g2, (W, H), interpolation=cv2.INTER_LINEAR) * 0.9
    out = BG + buf + glow
    # 柔和高光压缩
    hi = out > 0.8
    out[hi] = 0.8 + 0.2 * (1 - np.exp(-(out[hi] - 0.8) / 0.2))

    hl = np.zeros((H, W, 3), np.float32)
    hud(t, out, hl)
    out += hl
    HUD.draw(out, t, brand_alpha(t) * gfade)
    for (s, x, y, sz, fp, col, a, an) in texts:
        blit(out, s, x, y, sz, fp, col, a * gfade, an)
    for (t0, t1, s) in NARRATION:
        a, w = text_alpha(t, t0, t1, 0.7, 0.45)
        if a > 0:
            blit(out, s, CX, 966 - 8 * (1 - w), 36, SERIF, INK, a, "m", track=5, wipe=w)
    center_texts(t, out)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


# ---------------------------------------------------------------- 渲染


def render_chunk(args):
    ci, f0, f1 = args
    path = os.path.join(BUILD, f"chunk_{ci}.mp4")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                          "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-threads", "2",
                          path], stdin=subprocess.PIPE)
    for f in range(f0, f1):
        p.stdin.write(render_frame(f / FPS).tobytes())
        if (f - f0) % 300 == 0:
            print(f"chunk {ci}: {f - f0}/{f1 - f0}", flush=True)
    p.stdin.close()
    p.wait()
    return path


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "render"
    if mode == "preview":
        os.makedirs(os.path.join(BUILD, "preview"), exist_ok=True)
        for s in sys.argv[2:]:
            t = float(s)
            Image.fromarray(render_frame(t)).save(os.path.join(BUILD, "preview", f"t{t:06.2f}.png"))
        return
    total = int(math.ceil(DUR * FPS))
    workers = int(os.environ.get("WORKERS", 4))
    step = math.ceil(total / workers)
    jobs = [(i, i * step, min(total, (i + 1) * step)) for i in range(workers)]
    with Pool(workers) as pool:
        paths = pool.map(render_chunk, jobs)
    lst = os.path.join(BUILD, "chunks.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{p}'\n" for p in paths)
    out = os.path.join(HERE, "..", "爱的本质.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-i", os.path.join(BUILD, "bgm_ext.wav"), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", out], check=True)
    print("done:", os.path.abspath(out))


if __name__ == "__main__":
    main()
