"""《国家队去哪了？》分镜渲染。python3 video.py chunk <起始帧> <结束帧> <输出.mp4> | still <秒> <输出.png>"""
import math, os, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from engine import *  # noqa
from timeline import BAR, BEAT, DURATION, HITS, QSCHED, YTD_BREAK, PRE_DROP, TICKER, b, load_stats

S = load_stats()
# 本期主线：两个主体直接对比——中央汇金资产管理有限责任公司 vs 中国证券金融股份有限公司
QL = S["quarters"]; NQ = len(QL)
HJ = S["duo"]["huijin_am"]; ZJ = S["duo"]["csf"]; UN = S["duo"]["union"]
PRES = S["duo"]["presence"]
NA, NB = "中央汇金资管", "中国证金"
import csv
IDX = {}
with open(os.path.join(HERE, "..", "data", "index_quarter_end.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        IDX[r["quarter"]] = float(r["上证指数"])
SH = [IDX[q] for q in QL]
UNIVERSE_LAST = S["universe"][-1]
COVER_LAST = S["universe_like"][-1]


def qtxt(q):
    return q[:4] + " Q" + q[-1]


def fmt_d(v):
    return ("+" if v > 0 else "−" if v < 0 else "±") + str(abs(v))


# ================================================================ 全局：背景 / 节拍 / 重拍
rng0 = np.random.default_rng(7)
_yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
_xx = np.linspace(0, 1, W, dtype=np.float32)[None, :]
BG = np.zeros((H, W, 3), np.float32)
BG[:] = (np.array([0.020, 0.024, 0.052], np.float32)[None, None, :] * (1 - _yy[..., None]) +
         np.array([0.007, 0.008, 0.018], np.float32)[None, None, :] * _yy[..., None])
_vig = 1 - 0.55 * np.clip(((_xx - 0.5) ** 2 * 1.4 + (_yy - 0.48) ** 2 * 1.1) * 2.2, 0, 1)
BG *= _vig[..., None]

# 星尘（3D，用于视差）
NST = 900
STAR = np.stack([rng0.uniform(-30, 30, NST), rng0.uniform(-8, 40, NST), rng0.uniform(-20, 140, NST)], 1)
STAR_C = np.where(rng0.random(NST)[:, None] < 0.5, BA, BB) * 0.6 + 0.4
STAR_A = rng0.uniform(0.15, 0.6, NST)


def beat_pulse(t):
    ph = (t % BEAT) / BEAT
    return math.exp(-ph * 5)


def hit_env(t, width=0.6):
    """最近一次重拍后的衰减（0..1），以及强度"""
    v = 0.0
    for ht, s, k in HITS:
        if 0 <= t - ht < 3:
            v = max(v, s * math.exp(-(t - ht) / width))
    return v


def nebula(F, t, cols=(BA, BB), amt=1.0, cy=0.45):
    """缓慢漂移的星云：低分辨率计算后放大"""
    if amt <= 0.01: return
    h, w = 60, 34
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]; xx = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    acc = np.zeros((h, w, 3), np.float32)
    for k, (px, py, r, c) in enumerate(((0.25, cy - 0.1, 0.35, cols[0]), (0.78, cy + 0.12, 0.4, cols[1]),
                                        (0.5, cy + 0.35, 0.3, cols[0]))):
        x0 = px + 0.08 * math.sin(t * 0.07 + k * 2); y0 = py + 0.05 * math.cos(t * 0.05 + k)
        g = np.exp(-((xx - x0) ** 2 * 3.2 + (yy - y0) ** 2) / (2 * r * r * 0.5))
        acc += g[..., None] * np.asarray(c, np.float32)
    big = cv2.resize(acc, (W, H), interpolation=cv2.INTER_CUBIC)
    F.C += big * (0.05 * amt)


def stars(F, t, cam=None, amt=1.0, drift=0.0):
    if amt <= 0.01: return
    if cam is None:
        cam = Cam(pos=(0, 6, -20 + drift), f=900)
    x, y, z = cam.project(STAR)
    ok = z > 0.5
    a = STAR_A * amt * np.clip(1.2 - z / 140, 0, 1) * (0.75 + 0.25 * np.sin(t * 2 + STAR[:, 0]))
    F.splat(x[ok], y[ok], STAR_C[ok] * 0.55, a[ok], buf="G")


def chapter(F, t, num, name, t0, t1):
    a = win(t, t0, t1, 0.6, 0.5)
    if a <= 0: return
    F.text(num, 64, 110, 30, "numb", BA * 0.5 + BB * 0.5 + 0.25, a * 0.95, anchor="l", track=0.08)
    F.text(name, 64 + text_width(num, "numb", 30, 0.08) + 18, 111, 30, "med", INK2, a, anchor="l", track=0.12)
    F.fill([(64, 140), (64 + 120 * eo((t - t0) / 0.8), 140), (64 + 120 * eo((t - t0) / 0.8), 142.5), (64, 142.5)],
           BA, a * 0.8, buf="G", mode="add")


def footnote(F, t, a, s="数据：上市公司定期报告｜东方财富数据中心整理｜口径：前十大股东 ∪ 前十大流通股东"):
    F.text(s, W / 2, 1838, 21, "reg", INK3 + 0.08, a * 0.9)


def tag(F, kind, x, y, a=1.0, size=26):
    """事实 / 背景 / 推测 / 注意 标签胶囊，返回宽度"""
    lab, col = {"fact": ("事实", INK), "ctx": ("背景", ICE), "guess": ("推测", WARN), "warn": ("注意", RED),
                "corr": ("相关", VIO)}[kind]
    tw = text_width(lab, "bold", size)
    pts = F.rrect_pts(x, y - size * 0.72, x + tw + size * 1.1, y + size * 0.72, size * 0.7)
    F.fill(pts, col * 0.16, a, buf="C")
    F.poly(pts + [pts[0]], col, a * 0.8, 1.5, buf="G")
    F.text(lab, x + size * 0.55, y, size, "bold", col, a, anchor="l")
    return tw + size * 1.1


def glass_num(F, s, x, y, size, col, a=1.0, anchor="m", fnt="numb", glow=0.35):
    """玻璃质感数字：上亮下透的竖向渐变 + 内部高光 + 投影 + 辉光"""
    if a <= 0.003: return 0
    top = np.minimum(np.asarray(col) * 0.35 + 0.75, 1.0)
    bot = np.asarray(col) * 0.85
    tw = F.text(s, x, y, size, fnt, col, a, anchor=anchor, tab=True, grad=(top, bot), shadow=0.6)
    F.text(s, x, y, size, fnt, col, a * glow * 0.5, anchor=anchor, tab=True, glow=glow)
    return tw


def roll(v0, v1, t, t0, dur=0.55):
    p = eo((t - t0) / dur)
    return int(round(v0 + (v1 - v0) * p))


# ================================================================ 粒子矩阵：5565 家 A 股公司
COLS_M = 75
ROWS_M = int(math.ceil(UNIVERSE_LAST / COLS_M))
_gx, _gy = np.meshgrid(np.arange(COLS_M), np.arange(ROWS_M))
GRID = np.stack([_gx.ravel(), _gy.ravel()], 1)[:UNIVERSE_LAST].astype(np.float32)
M_STEP = 12.0
M_X0, M_Y0 = W / 2 - (COLS_M - 1) * M_STEP / 2, 330
_perm = rng0.permutation(UNIVERSE_LAST)
EVER_SLOT = _perm[:len(PRES)]                      # 19 季里曾出现的公司在矩阵中的位置
EVER_P = np.array([p["p"] for p in PRES])           # (公司数, 19)
ALWAYS = np.all(EVER_P > 0, 1)
SER_COL = {1: GOLD, 2: ICE, 3: VIO}


def pres_cols(qi):
    v = EVER_P[:, qi]
    c = np.zeros((len(v), 3), np.float32)
    for k, col in SER_COL.items():
        c[v == k] = col
    return c, v > 0


def matrix_xy(scale=1.0, cx=W / 2, cy=None, t=0.0, wob=0.0):
    x = M_X0 + GRID[:, 0] * M_STEP
    y = M_Y0 + GRID[:, 1] * M_STEP
    if cy is not None:
        mx, my = W / 2, M_Y0 + (ROWS_M - 1) * M_STEP / 2
        x = cx + (x - mx) * scale; y = cy + (y - my) * scale
    if wob:
        x = x + wob * np.sin(t * 1.3 + GRID[:, 1] * 0.3)
    return x, y


# ================================================================ 场景 1：钩子（0 – 10）
def sc_open(F, t):
    nebula(F, t, amt=0.5 * eo(t / 2))
    x, y = matrix_xy()
    a_all = 0.18 * eo((t - 0.1) / 1.4) * (1 - 0.6 * eo((t - b(4)) / 1.2))
    d = np.hypot(x - W / 2, y - 1000) / 900
    appear = np.clip((t - 0.05) * 1.8 - d, 0, 1)
    F.dots(x, y, INK2 * 0.8, a_all * appear * 1.4, sigma=1.1, buf="C")
    F.text_reveal(f"{UNIVERSE_LAST} 家 A 股公司", W / 2, 1380, 64, 0.3, "bold", INK, win(t, 0.3, b(1) + 0.05, 0.25, 0.3), stag=0.04)
    F.text_reveal("每季度都要公布「十大股东」名单", W / 2, 1465, 40, 0.7, "reg", INK2, win(t, 0.7, b(1) + 0.05, 0.25, 0.3), stag=0.025)
    exs, eys = x[EVER_SLOT], y[EVER_SLOT]
    col0, on0 = pres_cols(0)
    col1, on1 = pres_cols(NQ - 1)
    lit = eo((t - b(1)) / 0.5)
    die = np.clip((t - b(3) - _ORDER * 1.5) / 0.22, 0, 1)
    die = np.where(on1, 0, die)
    al = lit * on0 * (1 - die)
    al = np.where(on1 & (t > b(3) + 1.6), np.maximum(al, 1.0), al)
    pulse = 1 + 0.5 * beat_pulse(t) * (t > b(1))
    F.dots(exs, eys, col0 * 1.3, al * pulse, sigma=2.2, buf="G")
    F.dots(exs, eys, col0 * 0.9, al * 0.8, sigma=1.4, buf="C")
    falling = (die > 0) & (die < 1) & on0
    if falling.any():
        F.dots(exs[falling], eys[falling] + die[falling] * 60, col0[falling], (1 - die[falling]) * 0.9, sigma=2.0)
    n = UN[0] if t < b(3) else int(on1.sum() + ((on0 & ~on1) & (die < 1)).sum())
    ca = win(t, b(1), b(4), 0.3, 0.3)
    glass_num(F, str(n), W / 2, 1450, 180, VIO, ca)
    # 两个名字（金 / 冰蓝）
    na = win(t, b(1), b(3) - 0.1, 0.3, 0.3)
    F.text(NA, W / 2 - 18, 1250, 46, "black", GOLD, na, anchor="r", glow=0.2)
    F.text("×", W / 2, 1250, 40, "numl", INK2, na)
    F.text(NB, W / 2 + 18, 1250, 46, "black", ICE, na, anchor="l", glow=0.2)
    F.text("2022 年一季度，出现在", W / 2, 1325, 36, "reg", INK2, na)
    F.text("家公司的十大股东名单里", W / 2, 1585, 38, "reg", INK2, na)
    nb = win(t, b(3), b(4), 0.3, 0.25)
    F.text("2026 年三季度，只剩", W / 2, 1300, 40, "reg", INK2, nb)
    F.text("家", W / 2, 1585, 40, "reg", INK2, nb)
    qa = win(t, b(4), b(5) + 0.25, 0.25, 0.12)
    F.text_reveal("国家队，去哪了？", W / 2, 1450, 96, b(4), "black", INK, qa, stag=0.06, dur=0.35, glow=0.25)
    F.bloom = 1.0 + 0.5 * eo((t - b(4)) / 2.0)


_ORDER = np.random.default_rng(3).random(len(PRES))


# ================================================================ 场景 2：标题（12.5 – 20）
def tunnel_rings(F, t, speed=6.0, amt=1.0, cy=1000, col_a=BA, col_b=BB, n=14):
    cam = Cam(pos=(0, 0, 0), f=900, cy=cy)
    zoff = (t * speed) % 4.0
    for k in range(n):
        z = 4.0 * k + 4.0 - zoff
        if z < 0.6: continue
        fade = np.clip(1 - z / (4.0 * n), 0, 1) * np.clip((z - 0.6) / 2, 0, 1)
        r = 3.2
        pts = [(r * 0.62 * math.cos(a), r * math.sin(a), z) for a in np.linspace(0, 2 * math.pi, 64)]
        x, y, _ = cam.project(np.array(pts))
        u = (k % 4) / 3
        col = col_a * (1 - u) + col_b * u
        F.poly(list(zip(x, y)), col, amt * fade * 0.55, 2.0)


def sc_title(F, t):
    t0 = b(5)
    lt = t - t0
    he = hit_env(t, 0.5)
    nebula(F, t, amt=1.0)
    tunnel_rings(F, t, speed=3 + 10 * math.exp(-lt / 0.8), amt=0.5 * eo(lt / 0.3), cy=980)
    # 爆散粒子（35 家的光点冲向镜头）
    x, y = matrix_xy()
    col1, on1 = pres_cols(NQ - 1)
    ex, ey = x[EVER_SLOT][on1], y[EVER_SLOT][on1]
    c = col1[on1]
    k = eo(lt / 1.2)
    sx = W / 2 + (ex - W / 2) * (1 + 6 * k); sy = 980 + (ey - 980) * (1 + 6 * k)
    F.dots(sx, sy, c * 1.6, (1 - k) * 1.5, sigma=2.5 + 6 * k)
    # 冲击环
    for j, dl in enumerate((0.0, 0.12)):
        p = eo((lt - dl) / 0.9)
        if 0 < p < 1:
            F.poly([(W / 2 + 900 * p * math.cos(a), 980 + 900 * p * math.sin(a)) for a in np.linspace(0, 6.3, 90)],
                   VIO if j else INK, (1 - p) * 0.9, 3)
    F.flash = 0.45 * math.exp(-lt / 0.15)
    F.ca = 5 * math.exp(-lt / 0.3)
    F.zoom = 1 + 0.035 * math.exp(-lt / 0.4)
    a = win(t, t0 + 0.05, b(7) + 0.15, 0.2, 0.35)
    s = 1.0 + 0.06 * math.exp(-lt / 0.35)
    F.text("国家队", W / 2, 830, int(190 * s) // 2 * 2, "black", INK, a, grad=(INK, BA * 0.4 + INK * 0.6), glow=0.25, shadow=0.5)
    F.text("去哪了？", W / 2, 1050, int(190 * s) // 2 * 2, "black", INK, a, grad=(BB * 0.35 + INK * 0.65, BB * 0.8 + 0.2),
           glow=0.25, shadow=0.5)
    # 分割线 + 副标题
    w = 380 * eo((lt - 0.5) / 0.8)
    F.fill([(W / 2 - w, 1203), (W / 2 + w, 1203), (W / 2 + w, 1206), (W / 2 - w, 1206)], VIO, a * 0.8, buf="G", mode="add")
    F.text_reveal("汇金资管 vs 中国证金", W / 2, 1282, 60, t0 + 0.5, "bold", INK, a, stag=0.04)
    F.text_reveal("19 个季度的持仓足迹", W / 2, 1370, 48, t0 + 0.9, "med", INK2, a, stag=0.03)
    F.text("2022 Q1  ——  2026 Q3", W / 2, 1480, 38, "numm", INK3 + 0.25, a * eo((lt - 1.3) / 0.5), track=0.08)
    F.text(str(UN[0]), W / 2 - 170, 1610, 64, "numb", VIO, a * eo((lt - 1.5) / 0.4), tab=True, glow=0.4)
    F.text("→", W / 2, 1606, 56, "numm", INK2, a * eo((lt - 1.75) / 0.4))
    F.text(str(UN[-1]), W / 2 + 170, 1610, 64, "numb", RED * 0.6 + INK * 0.4, a * eo((lt - 2.0) / 0.4), tab=True, glow=0.4)


# ================================================================ 场景 3/4：两支国家队
def orb(F, t, cx, cy, col, r=170, n=1400, seed=1, a=1.0, spin=0.4):
    """粒子球：代表一个机构"""
    rg = np.random.default_rng(seed)
    u = rg.random(n); v = rg.random(n)
    th = 2 * math.pi * u; ph = np.arccos(2 * v - 1)
    ang = th + t * spin
    x = np.sin(ph) * np.cos(ang); z = np.sin(ph) * np.sin(ang); y = np.cos(ph)
    rr = r * (1 + 0.04 * np.sin(t * 3 + ph * 6))
    zz = 3 + z
    px = cx + rr * x * 3 / zz; py = cy + rr * y * 3 / zz
    al = a * (0.25 + 0.75 * (z + 1) / 2) * 0.55
    F.splat(px, py, col, al, size=1)
    F.glow_dot(cx, cy, r * 0.55, col * 0.25, a)


def card_lines(F, t, lines, x, y0, t0, gap=78, size=42, alpha=1.0):
    for i, (s, kind) in enumerate(lines):
        ti = t0 + i * BEAT * 2
        a = eo((t - ti) / 0.45) * alpha
        if a <= 0: continue
        dx = (1 - eo5((t - ti) / 0.5)) * 40
        yy = y0 + i * gap
        if kind:
            tw = tag(F, kind, x + dx, yy, a, 24)
            F.text(s, x + dx + tw + 18, yy, size, "med", INK, a, anchor="l")
        else:
            F.glow_dot(x + 10 + dx, yy, 4, INK2, a * 0.9, buf="G")
            F.text(s, x + dx + 34, yy, size, "med", INK, a, anchor="l")


def entity_tree(F, t, t0, root, kids, col, y=1530, a=1.0):
    a = a * eo((t - t0) / 0.5)
    if a <= 0: return
    F.glass(80, y - 70, W - 80, y + 230, 30, a, tint=col)
    F.text(root, 120, y - 18, 36, "bold", col, a, anchor="l")
    F.text("统计名单", W - 120, y - 18, 26, "med", INK3 + 0.2, a, anchor="r")
    for i, (nm, sub) in enumerate(kids):
        p = eo((t - t0 - 0.3 - i * 0.25) / 0.4)
        yy = y + 50 + i * 54
        F.line((130, y + 10), (130, yy), col, a * p * 0.6, 2)
        F.line((130, yy), (160, yy), col, a * p * 0.6, 2)
        F.text(nm, 178, yy, 33, "med", INK, a * p, anchor="l")
        F.text(sub, W - 120, yy, 26, "reg", INK2, a * p, anchor="r")


# 上证指数日线（市场背景）与汇金公开出手的日期（均为公告日，见 DATA_README）
import json as _json
_IDX = _json.load(open(os.path.join(HERE, "..", "data", "raw", "idx_sh000001.json"), encoding="utf-8"))
IDX_D = [(r["day"], float(r["close"])) for r in _IDX if "2022-01-01" <= r["day"] <= "2026-09-30"]
HJ_EVENTS = [("2023-10-23", "2023.10", "增持四大行 · 买入 ETF"),
             ("2024-02-06", "2024.2", "扩大 ETF 增持范围"),
             ("2025-04-07", "2025.4", "增持 ETF ·「类平准基金」")]


def _idx_pos(day):
    for k, (d, v) in enumerate(IDX_D):
        if d >= day: return k
    return len(IDX_D) - 1


def sc_who_hj(F, t):
    t0 = b(40)
    lt = t - t0
    a = win(t, t0, b(45) + 0.15, 0.12, 0.3)
    F.zoom = 1 + 0.035 * math.exp(-lt / 0.3)
    nebula(F, t, cols=(GOLD * 0.6, BB), amt=0.8)
    stars(F, t, amt=0.5, drift=t * 0.6)
    chapter(F, t, "02", "它们是谁", t0, b(51))
    F.text_reveal("中央汇金资管", 90, 300, 96, t0, "black", GOLD, a, anchor="l", stag=0.04, dur=0.3, glow=0.25)
    F.text("母公司中央汇金：国家金融股东 · 关键时刻的稳定器", 94, 395, 34, "med", INK, a * eo((lt - 0.4) / 0.4), anchor="l")
    # 指数日线：画线速度按时间分段，让三次出手正好落在节拍上
    X0, X1, Y0, Y1 = 90, 990, 560, 1080
    vals = np.array([v for d, v in IDX_D]); lo, hi = vals.min() * 0.97, vals.max() * 1.02
    n = len(IDX_D)
    ev = [_idx_pos(d) for d, _, _ in HJ_EVENTS]
    anchors_t = [0.4, BEAT * 3, BEAT * 5, BEAT * 7, BEAT * 8.6]   # 起点 → 三次出手（第 3、5、7 拍）→ 终点
    anchors_i = [0, ev[0], ev[1], ev[2], n - 1]
    head = np.interp(lt, anchors_t, anchors_i)
    xs = X0 + (X1 - X0) * np.arange(n) / (n - 1)
    ys = Y1 - (Y1 - Y0) * (vals - lo) / (hi - lo)
    F.glass(60, Y0 - 70, W - 60, Y1 + 120, 30, a * 0.9, tint=GOLD)
    F.text("上证指数 · 日线", X0 + 10, Y0 - 30, 26, "med", INK2, a, anchor="l")
    F.text(f"{int(lo / 0.97)} – {int(hi / 1.02)}", X1 - 10, Y0 - 30, 24, "numm", INK3 + 0.25, a, anchor="r", tab=True)
    m = int(head) + 1
    if m > 1:
        pts = list(zip(xs[:m:2], ys[:m:2]))
        F.poly(pts, INK2 * 0.9, a * 0.9, 2.2)
        F.glow_dot(xs[m - 1], ys[m - 1], 6, INK * 1.5, a)
    for y in ("2022", "2023", "2024", "2025", "2026"):
        k = _idx_pos(y + "-01-01")
        F.text(y, xs[k], Y1 + 40, 24, "numm", INK3 + 0.25, a, tab=True)
    for j, (k, (d, lab, txt)) in enumerate(zip(ev, HJ_EVENTS)):
        te = anchors_t[j + 1]
        e = eo((lt - te) / 0.25) * a
        if e <= 0: continue
        x, y = xs[k], ys[k]
        ring = eo((lt - te) / 0.6)
        F.line((x, y + 14), (x, Y1), GOLD, e * 0.5, 1.5)
        F.glow_dot(x, y, 10, GOLD * 2.2, e)
        if ring < 1:
            F.poly([(x + (12 + 50 * ring) * math.cos(u), y + (12 + 50 * ring) * math.sin(u)) for u in np.linspace(0, 6.3, 40)],
                   GOLD, e * (1 - ring), 2.5)
        ly = 1260 + j * 92
        F.glass(70, ly - 38, W - 70, ly + 38, 22, e * 0.9, tint=GOLD)
        F.text(lab, 110, ly, 34, "numb", GOLD, e, anchor="l", tab=True)
        F.text(txt, 290, ly, 34, "med", INK, e, anchor="l")
        F.line((x, Y1 + 60), (x, ly - 40), GOLD, e * 0.25, 1.2)
    fa = eo((lt - 4.6) / 0.4) * a
    F.text("汇金买的 ETF 不在个股名单里——名单上看到的，主要是汇金资管", W / 2, 1600, 30, "med", INK2, fa)
    F.text("中投公司  →  中央汇金  →  汇金资管（2015 年设立）", W / 2, 1660, 28, "reg", INK3 + 0.3, fa)


def sc_who_zj(F, t):
    t0 = b(45)
    lt = t - t0
    a = win(t, t0, b(49) + 0.15, 0.12, 0.3)
    F.zoom = 1 + 0.035 * math.exp(-lt / 0.3)
    nebula(F, t, cols=(ICE * 0.6, BA), amt=0.8)
    stars(F, t, amt=0.5, drift=t * 0.6)
    chapter(F, t, "02", "它们是谁", b(40), b(51))
    F.text_reveal("中国证金", 90, 300, 104, t0, "black", ICE, a, anchor="l", stag=0.04, dur=0.3, glow=0.25)
    F.text("2011 年经国务院同意、证监会批准设立", 94, 395, 34, "med", INK, a * eo((lt - 0.4) / 0.4), anchor="l")
    # 转融通：证金 → 券商 → 投资者，粒子沿箭头流动
    nodes = [(W / 2, 560, "中国证金", ICE), (W / 2, 790, "证券公司", INK2), (W / 2, 1020, "两融投资者", INK2)]
    for j, (x, y, nm, col) in enumerate(nodes):
        e = eo((lt - 0.5 - j * BEAT) / 0.3) * a
        F.glass(x - 220, y - 60, x + 220, y + 60, 30, e, tint=col, edge=col)
        F.text(nm, x, y, 44, "bold", col if j == 0 else INK, e)
    for j in range(2):
        e = eo((lt - 1.0 - j * BEAT) / 0.3) * a
        y0, y1 = nodes[j][1] + 62, nodes[j + 1][1] - 62
        F.line((W / 2, y0), (W / 2, y1), ICE, e * 0.6, 2)
        F.fill([(W / 2 - 12, y1 - 16), (W / 2 + 12, y1 - 16), (W / 2, y1)], ICE, e, buf="G", mode="add")
        ph = (lt * 1.6 + np.arange(6) / 6) % 1
        F.splat(np.full(6, W / 2), y0 + (y1 - y0) * ph, ICE * 2, e * 0.9, size=2)
    F.text("转融通：给券商「批发」资金和证券，支撑融资融券", W / 2, 1140, 30, "med", INK2, eo((lt - 2.0) / 0.4) * a)
    # 2015 年的维稳仓位 → 名单里的蓝线
    e = eo((lt - 3.0) / 0.4) * a
    if e > 0:
        F.glass(70, 1230, W - 70, 1590, 30, e, tint=ICE)
        tw = tag(F, "fact", 110, 1290, e, 24)
        F.text("2015 年股市异常波动时入场维稳", 110 + tw + 18, 1290, 34, "med", INK, e, anchor="l")
        F.text("当年的部分持仓，就是名单里那条蓝线", 110, 1350, 32, "reg", INK2, e, anchor="l")
        X0, X1, Y0, Y1 = 190, 900, 1420, 1545
        p = eio((lt - 3.3) / 1.6)
        npts = 1 + int(p * (NQ - 1))
        pts = [(X0 + (X1 - X0) * i / (NQ - 1), Y1 - (Y1 - Y0) * ZJ[i] / 160) for i in range(npts)]
        if len(pts) > 1:
            F.poly(pts, ICE, e, 4)
        F.glow_dot(pts[-1][0], pts[-1][1], 8, ICE * 2, e)
        F.text(str(ZJ[npts - 1]), pts[-1][0] + 16, pts[-1][1], 34, "numb", ICE, e, anchor="l", tab=True)
        F.text(str(ZJ[0]), X0 - 16, pts[0][1], 28, "numb", ICE * 0.7 + 0.2, e, anchor="r", tab=True)
    F.text("本片只统计证金自有账户；10 个证金资管计划与转融通担保账户不计入", W / 2, 1640, 26, "reg", INK3 + 0.3,
           eo((lt - 5.0) / 0.4) * a)


def sc_compare(F, t):
    t1 = b(49)
    lt = t - t1
    ca = win(t, t1, b(51) + 0.05, 0.15, 0.2)
    F.zoom = 1 + 0.03 * math.exp(-lt / 0.3)
    nebula(F, t, amt=0.8)
    stars(F, t, amt=0.6, drift=t * 0.6)
    chapter(F, t, "02", "它们是谁", b(40), b(51))
    F.zoom = F.zoom * (1 + 0.04 * eio(lt / 4.0))
    F.text_reveal("一句话区分", W / 2, 620, 56, t1, "black", INK, ca, stag=0.05, dur=0.3)
    for j, (nm, l1, l2, col) in enumerate((("汇金", "国家金融股东", "危机时的稳定器", GOLD),
                                            ("证金", "两融「中枢」", "2015 年的维稳仓位", ICE))):
        x = W / 2 + (-1 if j == 0 else 1) * 230
        p = eo5((t - t1 - 0.15 - j * BEAT) / 0.5)
        F.glass(x - 205, 760, x + 205, 1240, 34, ca * p, tint=col, edge=col)
        F.text(nm, x, 880, 92, "black", col, ca * p, glow=0.2)
        F.text(l1, x, 1030, 40, "bold", INK, ca * p)
        F.text(l2, x, 1110, 34, "reg", INK2, ca * p)
    F.text("vs", W / 2, 1000, 40, "numl", INK3 + 0.3, ca)


# ================================================================ 对决：逐季生长的折线图（14 – 72）
QSTART = {i: b(s) for i, s, d, n in QSCHED}
QEND = {i: b(s + d) for i, s, d, n in QSCHED}
QNOTE = {i: n for i, s, d, n in QSCHED}
DX0, DX1, DY0, DY1 = 130, 990, 730, 1400        # 折线图区域（y 向下）
DYMAX = 170
NOTE_Y = 1560                                   # 注释卡顶边：在季度标签（DY1+74）下方留出间距
# 每季变化幅度（两家中较大者）——驱动画面冲击力；音频端用同一公式
MAG = [0] + [max(abs(HJ[i] - HJ[i - 1]), abs(ZJ[i] - ZJ[i - 1])) for i in range(1, NQ)]


def cur_q(t):
    k = 0
    for i, s, d, n in QSCHED:
        if t >= b(s) - (0.3 if i == 17 else 0): k = i   # 断崖季提前 0.3 秒开始下坠，重拍时落地
    return k


def focus_w(t):
    """进入「今年以来」后横轴放大 2026：旧季度压缩到左侧"""
    return eio((t - b(25)) / 1.6)


def dxq(i, w):
    lin = DX0 + (DX1 - DX0) * i / (NQ - 1)
    if i <= 15:
        foc = DX0 + (DX1 - DX0) * 0.42 * i / 15
    else:
        foc = DX0 + (DX1 - DX0) * (0.42 + 0.58 * (i - 15) / 3)
    return lin * (1 - w) + foc * w


def dyv(v):
    return DY1 - (DY1 - DY0) * v / DYMAX


def head_progress(k, t):
    """当前季度线头的推进比例（0→1）。断崖季：重拍前 0.3 秒开始加速下坠，正好在重拍落地"""
    t0 = QSTART[k]
    if k == 17:
        return ei(cl((t - (t0 - 0.3)) / 0.3)) if t < t0 else 1.0
    if k == 0:
        return 1.0
    return eo5((t - t0) / 0.42)


def series_pts(arr, k, p, w):
    pts = [(dxq(i, w), dyv(arr[i])) for i in range(k)]
    if k == 0:
        return [(dxq(0, w), dyv(arr[0]))]
    x = dxq(k - 1, w) + (dxq(k, w) - dxq(k - 1, w)) * p
    y = dyv(arr[k - 1] + (arr[k] - arr[k - 1]) * p)
    return pts + [(x, y)]


def duel_chart(F, t, k=None, amt=1.0, tt=None):
    """画折线对决图。tt 用于冻结时间（总结页背景）"""
    tt = t if tt is None else tt
    k = cur_q(tt) if k is None else k
    w = focus_w(tt)
    p = head_progress(k, tt)
    # 网格与刻度
    for v in (0, 50, 100, 150):
        y = dyv(v)
        F.line((DX0, y), (DX1, y), INK3, amt * (0.45 if v == 0 else 0.22), 1.3 if v == 0 else 1.0)
        F.text(str(v), DX0 - 16, y, 24, "numm", INK3 + 0.2, amt * 0.9, anchor="r", tab=True)
    for i, q in enumerate(QL):
        x = dxq(i, w)
        if q.endswith("Q1"):
            F.text(q[:4], x, DY1 + 38, 26, "numm", INK2, amt, tab=True)
        F.line((x, DY1), (x, DY1 + (9 if q.endswith("Q1") else 5)), INK3, amt * 0.6, 1.2)
    # 「今年」高亮带
    ya = eo((tt - b(25) - 1.0) / 0.6) * amt
    if ya > 0:
        xa = (dxq(15, w) + dxq(16, w)) / 2
        F.fill([(xa, DY0 - 40), (DX1 + 25, DY0 - 40), (DX1 + 25, DY1), (xa, DY1)], RED, ya * 0.7, buf="G", mode="add",
               grad=(RED * 0.0, RED * 0.10, DY0, DY1))
        F.text("今年", (xa + DX1 + 25) / 2, DY0 + 8, 30, "black", RED * 0.6 + INK * 0.4, ya)
    # 当前季度游标
    xk = dxq(k - 1, w) + (dxq(k, w) - dxq(k - 1, w)) * p if k > 0 else dxq(0, w)
    F.line((xk, DY0 - 20), (xk, DY1), INK, amt * 0.18, 1.2)
    F.text(QL[k].replace("Q", " Q"), xk, DY1 + 74, 28, "numb", INK, amt * eo((tt - QSTART[k]) / 0.3), tab=True)
    # 两条线：宽辉光 + 细亮线 + 面积
    heads = []
    for arr, col in ((HJ, GOLD), (ZJ, ICE)):
        pts = series_pts(arr, k, p, w)
        if len(pts) > 1:
            area = pts + [(pts[-1][0], DY1), (pts[0][0], DY1)]
            F.fill(area, col, amt * 0.55, buf="G", mode="add", grad=(col * 0.16, col * 0.0, DY0, DY1))
            F.poly(pts, col, amt * 0.22, 12)
            F.poly(pts, col, amt, 4.5)
        for i in range(k):
            F.glow_dot(dxq(i, w), dyv(arr[i]), 4.5, col * 1.6, amt * 0.9)
        hx, hy = pts[-1]
        heads.append((hx, hy, col, arr))
    # 线头：光点 + 到达脉冲环 + 数值
    arrive = (tt - QSTART[k]) if k != 17 else (tt - QSTART[k])
    ring = eo(arrive / 0.6) if arrive >= 0 else 0
    hy_a, hy_b = heads[0][1], heads[1][1]
    for j, (hx, hy, col, arr) in enumerate(heads):
        F.glow_dot(hx, hy, 9 + 4 * beat_pulse(tt), col * 2.2, amt)
        F.glow_dot(hx, hy, 26, col * 0.5, amt)
        if 0 < ring < 1 and MAG[k] >= 3:
            r = 12 + (40 + MAG[k] * 1.2) * ring
            F.poly([(hx + r * math.cos(u), hy + r * math.sin(u)) for u in np.linspace(0, 6.3, 48)], col, amt * (1 - ring), 2.5)
        v = int(round(arr[k - 1] + (arr[k] - arr[k - 1]) * p)) if k > 0 else arr[0]   # 与线头同步
        above = (hy <= (hy_b if j == 0 else hy_a))
        ly = hy - 50 if above else hy + 52
        lx = min(hx + 18, DX1 - 10) if hx < DX1 - 120 else hx - 18
        anc = "l" if hx < DX1 - 120 else "r"
        glass_num(F, str(v), lx, ly, 52, col, amt, anchor=anc, glow=0.35)
    return heads, w


def burst(F, t, k, heads):
    """到达新季度时，从线头迸出粒子：数量与速度随变化幅度增长"""
    m = MAG[k]
    lt = t - QSTART[k]
    if m < 3 or lt < 0 or lt > 1.6: return
    rg = np.random.default_rng(100 + k)
    n = int(40 + m * 16)
    for hx, hy, col, arr in heads:
        ang = rg.uniform(0, 2 * math.pi, n)
        sp = rg.uniform(80, 220 + m * 8, n)
        x = hx + np.cos(ang) * sp * lt
        y = hy + np.sin(ang) * sp * lt + 260 * lt * lt
        F.splat(x, y, col * 1.6, np.exp(-lt / 0.45) * 0.9, size=2)


def data_panel(F, t, k, a=1.0):
    """顶部玻璃数据面板"""
    if a <= 0.003: return
    y0, y1 = 210, 640
    F.glass(60, y0, W - 60, y1, 36, a)
    t0 = QSTART[k]
    p = eo5((t - t0) / 0.45)
    if k > 0 and p < 1:
        F.text(qtxt(QL[k - 1]), W / 2, 300 - 60 * p, 76, "numb", INK, a * (1 - p), tab=True)
    glass_num(F, qtxt(QL[k]), W / 2, 300 + 60 * (1 - p), 76, INK * 0.9 + VIO * 0.1, a * p, glow=0.25)
    for which, (cx, nm, col, arr) in enumerate(((290, NA, GOLD, HJ), (W - 290, NB, ICE, ZJ))):
        v0 = arr[k - 1] if k > 0 else arr[0]
        v = int(round(v0 + (arr[k] - v0) * head_progress(k, t))) if k == 17 else roll(v0, arr[k], t, t0 + 0.05 + which * 0.08, 0.5)
        F.text(nm, cx, 400, 32, "bold", col, a)
        glass_num(F, str(v), cx, 495, 104, col, a)
        if k > 0:
            dv = arr[k] - arr[k - 1]
            dc = RED if dv > 0 else GRN if dv < 0 else INK3 + 0.2
            big = abs(dv) >= 10
            sz = 36 if not big else int(min(44 + abs(dv) * 0.2, 64)) // 2 * 2
            F.text(fmt_d(dv), cx, 585, sz, "numb", dc, a * eo((t - t0 - 0.2) / 0.3), tab=True, glow=0.4 if big else 0)
        else:
            F.text("起点", cx, 585, 30, "med", INK3 + 0.2, a)
    v0 = UN[k - 1] if k > 0 else UN[0]
    v = roll(v0, UN[k], t, t0 + 0.1, 0.5)
    F.text("合并去重", W / 2, 452, 26, "med", INK2, a)
    glass_num(F, str(v), W / 2, 515, 64, VIO, a, glow=0.25)
    F.text("家", W / 2, 572, 26, "med", INK2, a)


def note_card(F, t, t0, t1, rows, y=NOTE_Y, a=1.0, h=None):
    """注释卡片：rows = [(tag, 文字, 字号)]"""
    aa = win(t, t0, t1, 0.3, 0.3) * a
    if aa <= 0: return
    hh = h or (54 + 62 * len(rows))
    dy = (1 - eo5((t - t0) / 0.45)) * 30
    F.glass(70, y + dy, W - 70, y + hh + dy, 30, aa)
    for j, (kind, s, size) in enumerate(rows):
        pj = eo((t - t0 - 0.1 - j * 0.25) / 0.35)
        yy = y + dy + 58 + j * 62
        xx = 110
        if kind:
            xx += tag(F, kind, xx, yy, aa * pj, 24) + 18
        F.text(s, xx, yy, size, "med", INK, aa * pj, anchor="l")


def ticker(F, t, a=1.0):
    for s0, s1, kind, txt in TICKER:
        aa = win(t, b(s0), b(s1), 0.25, 0.3) * a
        if aa <= 0: continue
        dx = (1 - eo5((t - b(s0)) / 0.5)) * 60
        F.glass(70 + dx, NOTE_Y, W - 70 + dx, NOTE_Y + 110, 26, aa, tint=ICE)
        tw = tag(F, kind, 105 + dx, NOTE_Y + 55, aa, 24)
        F.text(txt, 105 + dx + tw + 18, NOTE_Y + 55, 32, "med", INK, aa, anchor="l")


def impact(F, t, k):
    """季度切换冲击：幅度越大，推镜、闪光、色差、震动越强"""
    m = MAG[k]
    lt = t - QSTART[k]
    if lt < 0: return
    s = cl(m / 40.0)
    F.zoom = 1 + (0.008 + 0.05 * s) * math.exp(-lt / (0.22 + 0.25 * s))
    if m >= 8:
        F.flash = max(F.flash, (0.08 + 0.4 * s) * math.exp(-lt / 0.12))
        F.ca = max(F.ca, (1 + 7 * s) * math.exp(-lt / 0.3))
    if m >= 15:
        A = 18 * s * math.exp(-lt / 0.3)
        F.shake = (A * math.sin(lt * 70), A * 0.7 * math.cos(lt * 53))


def sc_tunnel(F, t):
    t0 = b(7)
    k = cur_q(t)
    note = QNOTE[k]
    a = eo((t - t0) / 0.4)
    in_ytd = b(YTD_BREAK[0]) <= t < b(YTD_BREAK[1])
    in_pre = b(PRE_DROP[0]) <= t < b(PRE_DROP[1])
    dark = 0.0
    if in_ytd:
        dark = eio((t - b(YTD_BREAK[0])) / 0.6) * (1 - eio((t - b(YTD_BREAK[1]) + 0.35) / 0.35)) * 0.8
    if in_pre:
        dark = eio((t - b(PRE_DROP[0])) / 0.5) * 0.55
    nebula(F, t, amt=0.6 * (1 - dark))
    stars(F, t, amt=0.5 * (1 - 0.5 * dark), drift=t * 0.8)
    chapter(F, t, "01", "19 个季度对决", t0, b(36))
    data_panel(F, t, k, a * (1 - 0.8 * dark))
    heads, w = duel_chart(F, t, k, amt=a * (1 - (0.95 if in_ytd else 0.7) * dark))
    burst(F, t, k, heads)
    impact(F, t, k)
    # 图例
    for j, (nm, col) in enumerate(((NA, GOLD), (NB, ICE))):
        x = 150 + j * 330
        F.fill([(x, 682), (x + 44, 682), (x + 44, 687), (x, 687)], col, a * (1 - dark), buf="G", mode="add")
        F.text(nm, x + 58, 684, 28, "med", INK, a * (1 - dark), anchor="l")
    F.text("十大股东名单中出现的公司数", W - 70, 684, 24, "reg", INK2, a * (1 - dark), anchor="r")
    footnote(F, t, a * (1 - dark))
    ticker(F, t, 1 - dark)
    if t - t0 < 0.4:
        F.flash = max(F.flash, 0.3 * math.exp(-(t - t0) / 0.12))
    if note == "start":
        note_card(F, t, QSTART[k] + 0.4, QEND[k] - 0.1, [(None, "两条线 = 每季出现在十大股东名单中的公司数", 32),
                                                         (None, "两张表合并，同一公司只计 1 次", 30)])
    elif note == "cross":
        note_card(F, t, QSTART[k] + 0.3, QEND[k] - 0.05, [("fact", f"{NB}单季 −19，被{NA}拉开差距", 34)], h=130)
    elif note == "q1":
        note_card(F, t, QSTART[k] + 0.3, QEND[k] - 0.05, [
            ("fact", f"{NB} 111 → 76，单季 −35", 34),
            ("fact", f"{NA} 140 → 139，几乎没动", 34)])
    if in_ytd:
        lb = t - b(YTD_BREAK[0])
        ya = win(t, b(YTD_BREAK[0]) + 0.1, b(YTD_BREAK[1]), 0.3, 0.2)
        F.text("过去四年，两条线只是缓慢下滑", W / 2, 860, 40, "med", INK2, ya * eo((lb - 0.2) / 0.4))
        glass_num(F, "2026", W / 2, 1040, 200, INK, ya * eo((lb - 1.0) / 0.4), fnt="numk", glow=0.35)
        F.text_reveal("今年以来", W / 2, 1220, 80, b(YTD_BREAK[0]) + 1.5, "black", RED * 0.5 + INK * 0.5, ya, stag=0.08, dur=0.3,
                      glow=0.25)
    if in_pre:
        lb = t - b(PRE_DROP[0])
        F.text_reveal("二季度", W / 2, 1000, 90, b(PRE_DROP[0]) + 0.1, "black", INK, win(t, b(PRE_DROP[0]), b(PRE_DROP[1]) - 0.3, 0.2, 0.1),
                      stag=0.12, dur=0.25)
        hb = beat_pulse(t * 2)
        F.glow_dot(W / 2, 1050, 380, RED * 0.14 * hb * eo(lb / 1.0), 1.0, buf="C")
    if note == "collapse":
        lt = t - QSTART[17]
        note_card(F, t, QSTART[17] + 0.3, QSTART[17] + 3.9, [
            ("fact", f"{NA}  139 → 17", 40),
            ("fact", f"{NB}  76 → 23", 40)], h=200)
        note_card(F, t, QSTART[17] + 4.0, QEND[17] - 0.1, [
            ("fact", "退出名单：贵州茅台 · 万科A · 平安银行", 30),
            ("corr", "同季末上证指数 4094，五年季末最高", 30),
            ("warn", "退出前十 ≠ 清仓，只是低于门槛", 30)])
    if note == "latest":
        note_card(F, t, QSTART[k] + 0.3, QEND[k] + 0.2, [
            ("fact", "三季度：17 · 23，与上季持平", 32),
            (None, f"数据截至 2026-10-31 · 已披露 {COVER_LAST:.1f}%", 28),
            ("fact", f"留下的 {UN[-1]} 家，19 个季度从未离开", 32)])


# ================================================================ 场景：今年以来（总结）
def sc_ytd(F, t):
    t0 = b(36)
    lt = t - t0
    a = win(t, t0, b(40) + 0.1, 0.15, 0.3)
    nebula(F, t, amt=0.7)
    duel_chart(F, t, NQ - 1, amt=0.2, tt=b(35.9))
    F.C *= 0.6; F.G *= 0.55
    F.flash = 0.3 * math.exp(-lt / 0.12)
    F.zoom = 1 + 0.04 * math.exp(-lt / 0.35) + 0.02 * eio(lt / 8)
    chapter(F, t, "01", "19 个季度对决", b(7), b(40))
    F.text_reveal("今年以来", W / 2, 300, 96, t0, "black", INK, a, stag=0.06, dur=0.3, glow=0.3)
    F.text("2025 年末  →  2026 年三季度", W / 2, 395, 32, "med", INK2, a * eo((lt - 0.4) / 0.4))
    rows = ((NA, GOLD, HJ[15], HJ[-1], 0.6), (NB, ICE, ZJ[15], ZJ[-1], 2.6))
    for j, (nm, col, v0, v1, tj) in enumerate(rows):
        p = eo5((lt - tj) / 0.5)
        if p <= 0: continue
        y0 = 480 + j * 430
        F.glass(70, y0, W - 70, y0 + 390, 34, a * p, tint=col, edge=col * 0.8)
        F.text(nm, 120, y0 + 70, 44, "black", col, a * p, anchor="l", glow=0.15)
        v = roll(v0, v1, t, t0 + tj + 0.5, 1.0)
        glass_num(F, str(v), 120, y0 + 190, 150, col, a * p, anchor="l", fnt="numk")
        F.text(f"/ {v0}", 120 + text_width(str(v), "numk", 150, tab=True) + 24, y0 + 215, 52, "numm", INK2, a * p,
               anchor="l", tab=True)
        pct = round((v1 - v0) / v0 * 100)
        pe = eo((lt - tj - 1.5) / 0.3)
        glass_num(F, f"−{abs(pct)}%", W - 120, y0 + 190, 120, GRN, a * pe, anchor="r", fnt="numk", glow=0.5)
        bx0, bx1, by = 120, W - 120, y0 + 320
        frac = v / v0
        F.fill([(bx0, by - 8), (bx1, by - 8), (bx1, by + 8), (bx0, by + 8)], INK3 * 0.6, a * p, buf="C")
        F.fill([(bx0, by - 8), (bx0 + (bx1 - bx0) * frac, by - 8), (bx0 + (bx1 - bx0) * frac, by + 8), (bx0, by + 8)],
               col, a * p, buf="G", mode="add")
    pt = eo5((lt - 5.0) / 0.5)
    if pt > 0:
        F.glass(70, 1360, W - 70, 1600, 34, a * pt, tint=VIO, edge=VIO)
        F.text("两家合计（去重）", W / 2, 1420, 34, "med", INK2, a * pt)
        pct = round((UN[-1] - UN[15]) / UN[15] * 100)
        glass_num(F, f"{UN[15]} → {UN[-1]}   −{abs(pct)}%", W / 2, 1520, 84, VIO, a * pt, fnt="numb", glow=0.4)
    footnote(F, t, a)


# ================================================================ 场景 8：启示（150 – 167.5）
LESSONS = [
    ("1", "国家队是「稳定器」", "不是「荐股人」", "官方定位：维护市场平稳运行的「类平准」力量"),
    ("2", "名单只是季末快照", "滞后，而且只截前十", "披露滞后 1—4 个月；ETF 与前十之外的持仓都看不见"),
    ("3", "别把「名单」当「信号」", "进 ≠ 买入，出 ≠ 卖出", "看懂企业价值，才是自己的护城河"),
]


def lesson_icon(F, t, i, cx, cy, a, ti):
    """右侧小图标：1 阻尼波（稳定器） 2 取景框里的前十名（快照） 3 被划掉的信号"""
    if a <= 0.01: return
    col = VIO * 0.9 + 0.1
    if i == 0:
        xs = np.linspace(-80, 80, 60)
        ph = (t - ti) * 3
        ys = 38 * np.exp(-(xs + 80) / 55) * np.sin(xs / 9 - ph)
        F.poly(list(zip(cx + xs, cy + ys)), col, a, 3)
        F.line((cx - 80, cy + 55), (cx + 80, cy + 55), INK3, a * 0.6, 1.5)
    elif i == 1:
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            x0, y0 = cx + sx * 80, cy + sy * 60
            F.line((x0, y0), (x0 - sx * 22, y0), col, a, 3); F.line((x0, y0), (x0, y0 - sy * 22), col, a, 3)
        for k in range(10):
            h = 70 * (0.95 - k * 0.07)
            x = cx - 58 + k * 13
            F.fill([(x, cy + 42 - h), (x + 8, cy + 42 - h), (x + 8, cy + 42), (x, cy + 42)], col * (1.0 if k < 10 else 0.3), a * 0.8, buf="G", mode="add")
        F.text("TOP 10", cx, cy - 40, 18, "numb", INK2, a)
    else:
        for r in (22, 44, 66):
            pts = [(cx - 40 + r * math.cos(u), cy + 30 + r * math.sin(u)) for u in np.linspace(-math.pi / 2 + 0.15, -0.15, 20)]
            F.poly(pts, col, a, 3)
        F.glow_dot(cx - 40, cy + 30, 6, col * 1.5, a)
        F.line((cx - 75, cy + 55), (cx + 55, cy - 55), RED, a, 4)


def sc_lessons(F, t):
    t0 = b(51)
    lt = t - t0
    nebula(F, t, cols=(BA, BB), amt=0.8 + 0.3 * beat_pulse(t))
    stars(F, t, amt=0.7, drift=t * 1.2)
    chapter(F, t, "03", "给普通投资者", t0, b(61))
    F.flash = 0.35 * math.exp(-lt / 0.14)
    F.ca = 4 * math.exp(-lt / 0.3)
    F.text_reveal("看懂国家队，记住三件事", W / 2, 330, 62, t0, "black", INK, win(t, t0, b(61), 0.12, 0.4), stag=0.035, dur=0.3)
    F.zoom = 1 + 0.03 * math.exp(-lt / 0.3)
    starts = [b(52), b(55), b(58)]                # 每条启示踩在小节线上「砸」进来
    for i, (n, h1, h2, s_) in enumerate(LESSONS):
        ti = starts[i]
        a = eo((t - ti) / 0.25) * win(t, t0, b(61), 0.3, 0.4)
        if a <= 0: continue
        li = t - ti
        if 0 <= li < 0.6:
            F.flash = max(F.flash, 0.22 * math.exp(-li / 0.1))
            F.ca = max(F.ca, 3.5 * math.exp(-li / 0.25))
            F.zoom = max(F.zoom, 1 + 0.03 * math.exp(-li / 0.25))
        y = 480 + i * 400
        act = 1.0 if ti <= t < (starts[i + 1] if i < 2 else b(61) + 1) else 0.55
        pulse = beat_pulse(t) * act
        sc = 1 + 0.12 * (1 - eo5(li / 0.3))
        dx = (1 - eo5(li / 0.35)) * 80
        F.glass(70 + dx, y, W - 70 + dx, y + 340, 34, a, tint=VIO if act > 0.9 else INK3,
                edge=VIO * (act * (0.8 + 0.6 * pulse)))
        if act > 0.9:
            F.glow_dot(150 + dx, y + 105, 90, VIO * (0.18 + 0.2 * pulse), a)
        glass_num(F, n, 150 + dx, y + 105, int(110 * sc) // 2 * 2, VIO, a * act + 0.2 * a, fnt="numk", glow=0.3 + 0.4 * pulse)
        F.text(h1, 240 + dx, y + 85, 56, "black", INK, a * (0.6 + 0.4 * act), anchor="l", glow=0.15 * pulse)
        F.text(h2, 240 + dx, y + 162, 44, "bold", VIO * 0.4 + INK * 0.6, a * (0.6 + 0.4 * act), anchor="l")
        F.text(s_, 110 + dx, y + 268, 31, "reg", INK2, a * (0.5 + 0.5 * act), anchor="l")
        lesson_icon(F, t, i, 905 + dx, y + 120, a * (0.45 + 0.55 * act), ti)
    # 高潮段背景：随节拍呼吸的光带
    for k in range(3):
        yy = 1780 - ((t * 260 + k * 640) % 1920)
        F.glow_dot(W / 2, yy, 260, VIO * 0.05 * (0.6 + 0.4 * beat_pulse(t)), 1.0)
    F.text("本视频仅为数据解读，不构成任何投资建议", W / 2, 1745, 26, "reg", INK3 + 0.15, win(t, t0 + 2, b(61), 0.5, 0.4))


# ================================================================ 场景 9：片尾（167.5 – 177.5）
LOGO = load_logo("blue", "logo-dark", 230)
MARK = load_logo("blue", "mark", 300)


def sc_end(F, t):
    t0 = b(61)
    lt = t - t0
    nebula(F, t, amt=1.0, cy=0.42)
    stars(F, t, amt=0.8, drift=t * 0.4)
    F.flash = 0.35 * math.exp(-lt / 0.15)
    tunnel_rings(F, t, speed=2.0, amt=0.35 * eo(lt / 1.0), cy=760)
    # logo：先 mark 光弧扫过，再整体出现
    rgb, al = LOGO
    h, w = al.shape
    a = eo((lt - 0.2) / 0.9) * (1 - eo((t - (DURATION - 0.8)) / 0.8))
    x0, y0 = (W - w) // 2, 560
    # 光晕
    F.glow_dot(W / 2 - w * 0.33, y0 + h / 2, 160, BB * 0.22, a)
    F.glow_dot(W / 2 - w * 0.33, y0 + h / 2, 60, BA * 0.3, a)
    # 擦除式揭示（左→右）
    rev = eo5((lt - 0.2) / 1.4)
    m = al.copy()
    cut = int(w * rev)
    m[:, cut:] = 0
    edge = np.zeros_like(m)
    if 0 < cut < w:
        lo = max(cut - 30, 0)
        edge[:, lo:cut] = al[:, lo:cut] * np.linspace(0, 1, cut - lo)[None, :]
    F.blit(m, x0, y0, (1, 1, 1), a, colimg=rgb)
    F.blit(edge, x0, y0, (1, 1, 1), a * 1.5, buf="G", mode="add")
    w2 = 300 * eo((lt - 1.2) / 0.8)
    F.fill([(W / 2 - w2, y0 + h + 90), (W / 2 + w2, y0 + h + 90), (W / 2 + w2, y0 + h + 92.5), (W / 2 - w2, y0 + h + 92.5)],
           VIO, a * 0.8, buf="G", mode="add")
    F.text_reveal("关注 MastersTao", W / 2, 1110, 68, t0 + 1.5, "black", INK, a, stag=0.05, glow=0.2)
    F.text_reveal("看懂机构持仓背后的投资逻辑。", W / 2, 1210, 46, t0 + 2.0, "med", INK2, a, stag=0.04)
    F.text("masterstao.com", W / 2, 1420, 28, "numm", INK3 + 0.2, a * eo((lt - 2.6) / 0.5), track=0.08)


# ================================================================ 调度
SCENE_FUN = [
    (b(0), b(5), sc_open), (b(5), b(7), sc_title), (b(7), b(36), sc_tunnel), (b(36), b(40), sc_ytd),
    (b(40), b(45), sc_who_hj), (b(45), b(49), sc_who_zj), (b(49), b(51), sc_compare),
    (b(51), b(61), sc_lessons), (b(61), DURATION + 1, sc_end),
]
HUD = Hud(width=W, series=None)          # 只用官方 logo，不显示系列名


def render(t):
    F = Frame(t, BG)
    for a0, a1, fn in SCENE_FUN:
        if a0 <= t < a1:
            fn(F, t)
            break
    # 全局节拍辉光呼吸
    F.bloom *= 1.0 + 0.14 * beat_pulse(t) * (b(7) <= t < b(25) or b(36) <= t < b(40) or b(51) <= t < b(61)) \
        + 0.06 * beat_pulse(t) * (b(40) <= t < b(51))
    # 片头片尾淡入淡出
    F.fade = eo(t / 0.6) * (1 - eio((t - (DURATION - 1.25)) / 1.25))     # 与原曲尾音同步淡出
    hud_a = eo((t - 0.8) / 0.8) * (1 - eo((t - b(61)) / 0.6))
    return F.finish(hud=(lambda img: HUD.draw(img, t, hud_a)) if hud_a > 0 else None, grain_seed=int(t * FPS))


def chunk(f0, f1, out):
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-threads", "2", "-crf", "14", "-pix_fmt", "yuv420p", "-tune", "film", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        p.stdin.write(render(fi / FPS).tobytes())
        if (fi - f0) % 150 == 0:
            print(f"[{out}] {fi}/{f1}", flush=True)
    p.stdin.close(); p.wait()


if __name__ == "__main__":
    if sys.argv[1] == "still":
        from PIL import Image
        for s in sys.argv[2].split(","):
            t = float(s)
            Image.fromarray(render(t)).save(sys.argv[3].replace("%", f"{t:06.2f}"))
    else:
        chunk(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
