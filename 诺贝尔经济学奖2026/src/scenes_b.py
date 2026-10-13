"""v3：02 诺奖（回到半个世纪前：旧模型 → 石油危机与滞胀 → 旧模型失灵 → 新凯恩斯主义）→ 03 霍尔：家庭的预期（发现①花钱看一辈子；发现②消费只为意外而变）"""
import math

import numpy as np

from common import *          # noqa: F401,F403
from registry import scene
from timeline import CAP, HITS, SEC, T
from scenes_a import cw, two, chip, num_unit, rich, bar_glass
import portraits

CX = W / 2
CORAL_HI = C(255, 190, 180)


def law_card(fr, t, t0, t1, tag, line, a, y=760, out_to=None):
    """「发现」卡片：居中玻璃卡 + 金色标签 + 大字规律；结束前缩成页眉（out_to = 页眉 y）"""
    k = a * win(t, t0, t1, 0.45, 0.4)
    if k <= 0.01:
        return
    p = eo((t - t0) / 0.6)
    fr.card(80, y - 210, 1000, y + 190, 36, k, tint=GOLD, border=GOLD, border_a=0.75, fill_a=0.08, blur=16)
    fr.glow((CX, y), 360, GOLD, k * 0.10)
    fr.text(tag, CX, y - 105, 38, 'sans_bold', 'gold', k * p, track=0.16, glow=0.3)
    fr.text(line, CX, y + 30, 82 if len(line) <= 10 else 68, 'serif_black', 'white', k, glow=0.4,
            stagger=(t - t0 - 0.25, 0.07, 0.5))


def header(fr, s, k, y=225, size=46):
    """章节内的小页眉（规律名常驻页顶，帮观众记住「现在讲到哪一条」）"""
    fr.text(s, CX, y, size, 'serif_bold', 'gold', k, glow=0.25)


# ================================================================ 02 诺奖 76–82
_MR = np.random.default_rng(3)
RING_N = 1600
RING_A = _MR.random(RING_N) * 2 * np.pi
RING_R = 1 + _MR.normal(0, 0.03, RING_N)
RING_Z = _MR.normal(0, 0.05, RING_N)


@scene(76.0, 82.0, 0.0, 0.4)
def sc_nobel(fr, t, a):
    lt = t - SEC['nobel'][0]
    fr.flash = max(fr.flash, 0.8 * math.exp(-lt / 0.06) * a)
    fr.ca = max(fr.ca, 6 * math.exp(-lt / 0.2))
    c = (CX, 740)
    p = eo(lt / 1.2)
    R = 300 * (0.6 + 0.4 * p)
    rot = lt * 0.45
    tilt = 0.32
    ang = RING_A + rot
    x = c[0] + R * RING_R * np.cos(ang)
    y = c[1] + R * RING_R * np.sin(ang) * math.cos(tilt) + RING_Z * R
    depth = (np.sin(ang) + 1) / 2
    fr.splat(x, y, GOLD_HI, a * (0.35 + 0.65 * depth) * p)
    fr.splat(x, y, GOLD, a * (0.5 + 0.8 * depth) * p, layer='B')
    for rr, al in ((R * 0.86, 0.5), (R * 1.12, 0.25)):
        ts = np.linspace(0, 2 * np.pi, 160)
        fr.stroke(list(zip(c[0] + rr * np.cos(ts), c[1] + rr * np.sin(ts) * math.cos(tilt))), GOLD, a * al * p, 1.5,
                  closed=True, glow=0.8)
    for k in range(12):
        q = rot * 0.3 + k * np.pi / 6
        L = 900
        p0 = (c[0] + R * 0.9 * math.cos(q), c[1] + R * 0.9 * math.sin(q))
        p1 = (c[0] + L * math.cos(q - 0.03), c[1] + L * math.sin(q - 0.03))
        p2 = (c[0] + L * math.cos(q + 0.03), c[1] + L * math.sin(q + 0.03))
        fr.fill([p0, p1, p2], GOLD * 0.05, a * p, layer='B')
    fr.glow(c, 240, GOLD, a * 0.18 * p)
    fr.text('2026', CX, 715, 150, 'inter_light', 'gold', a * p, glow=0.5, track=0.05)
    fr.text('ECONOMIC SCIENCES', CX, 820, 30, 'corm_bold', 'subgold', a * p, track=0.32, glow=0.2)
    draw_dust(fr, t, a * 0.7, speed=1.5)
    k = a * cw('n_q', t, 0.35, 0.3)
    fr.text('预期，真能左右', CX, 1190, 60, 'serif_bold', 'white', k, glow=0.2, stagger=(t - CAP['n_q'][0], 0.04, 0.4))
    fr.text('我们的【钱包】？', CX, 1290, 70, 'serif_black', 'white', k, glow=0.3, stagger=(t - CAP['n_q'][0] - 0.25, 0.05, 0.45))
    k = a * cw('n_a', t, 0.35, 0.35)
    fr.text('今年的诺贝尔经济学奖，', CX, 1190, 58, 'serif_bold', 'white', k, glow=0.2, stagger=(t - CAP['n_a'][0], 0.035, 0.4))
    fr.text('给出了【答案】', CX, 1290, 70, 'serif_black', 'white', k, glow=0.3, stagger=(t - CAP['n_a'][0] - 0.3, 0.05, 0.45))


# ================================================================ 回到半个世纪前：旧模型 → 滞胀 → 新凯恩斯主义（82–132）
OM0 = SEC['oldmodel'][0]
OX, OY = 190, 1060            # 菲利普斯图：左下角
XW, YH = 720, 520
U0, U1, PI1 = 3.0, 9.0, 14.0  # 失业率 3%–9%，通胀率 0–14%
# 美国年均数据：(年份, 失业率 %, CPI 涨幅 %)；BLS（CPI 年均涨幅按明尼阿波利斯联储整理的 BLS 表）
D60 = [(1960, 5.5, 1.7), (1961, 6.7, 1.0), (1962, 5.5, 1.0), (1963, 5.7, 1.3), (1964, 5.2, 1.3),
       (1965, 4.5, 1.6), (1966, 3.8, 3.0), (1967, 3.8, 2.8), (1968, 3.6, 4.3), (1969, 3.5, 5.5)]
D70 = [(1970, 4.9, 5.7), (1971, 5.9, 4.4), (1972, 5.6, 3.2), (1973, 4.9, 6.2), (1974, 5.6, 11.1), (1975, 8.5, 9.1),
       (1976, 7.7, 5.7), (1977, 7.1, 6.5), (1978, 6.1, 7.6), (1979, 5.8, 11.3), (1980, 7.1, 13.5), (1981, 7.6, 10.3)]
OIL = [('2.9', 2.9, '1973 年', '10 月前'), ('5.1', 5.11, '1973 年', '10 月'), ('11.65', 11.65, '1974 年', '1 月')]
NK_BLOCKS = [('微观基础', '从家庭、企业的决策出发', GOLD, 'gold'),
             ('理性预期', '人会预判未来，提前行动', ICE, 'ice'),
             ('价格黏性', '价格不能天天改，调整要时间', CORAL, 'coral')]
_SR = np.random.default_rng(8)
SHARD_V = _SR.normal(0, 1, (80, 2)) * np.array([420, 340]) + np.array([0, -120])
SHARD_W = _SR.normal(0, 5, 80)
LAT_N = 84
LAT = np.array([(150 + (i % 14) * 60 + (30 if (i // 14) % 2 else 0), 1080 - (i // 14) * 52) for i in range(LAT_N)],
               np.float64)
LAT_KIND = _SR.random(LAT_N) < 0.25
SRC_RND = np.c_[_SR.uniform(120, 960, LAT_N), _SR.uniform(450, 1100, LAT_N)]


def om(off):
    return OM0 + off


def p2s(u, v):
    u, v = np.asarray(u, np.float64), np.asarray(v, np.float64)
    return OX + (u - U0) / (U1 - U0) * XW, OY - v / PI1 * YH


def phillips(u, shift=0.0):
    """1960 年代美国数据的拟合曲线：通胀 ≈ 0.3 + 1.9 / (失业率 − 3.1)；shift = 预期通胀上升带来的整体上移（示意）"""
    return 0.3 + shift + 1.9 / (np.asarray(u) - 3.1)


def curve_pts(shift=0.0, n=80):
    u = np.linspace(3.42, 7.6, n)
    v = phillips(u, shift)
    ok = v <= PI1 + 0.2
    return p2s(u[ok], v[ok])


def chart_axes(fr, k):
    fr.line((OX, OY), (OX + XW + 20, OY), GREY, k * 0.6, 2)
    fr.line((OX, OY), (OX, OY - YH - 20), GREY, k * 0.6, 2)
    for u in (3, 5, 7, 9):
        x, _ = p2s(u, 0)
        fr.text(f'{u}%', x, OY + 36, 26, 'inter_med', 'dim', k, glow=0)
    for v in (5, 10):
        _, y = p2s(U0, v)
        fr.text(f'{v}%', OX - 18, y, 26, 'inter_med', 'dim', k, anchor='r', glow=0)
        for xx in range(OX, OX + XW, 22):
            fr.line((xx, y), (xx + 8, y), GREY, k * 0.18, 1)
    fr.text('失业率 →', OX + XW + 10, OY + 74, 30, 'sans_med', 'grey', k, anchor='r', glow=0)
    fr.text('通胀率 ↑', OX - 10, OY - YH - 46, 30, 'sans_med', 'grey', k, anchor='l', glow=0)
    fr.text('美国 · 通胀率与失业率（年均）', CX, 360, 32, 'sans_med', 'grey', k, glow=0)


def shards(fr, xs, ys, brk, k, col, seed=0, n=20):
    seg = np.array_split(np.arange(len(xs)), n)
    for j, idx in enumerate(seg):
        q = (j + seed * n) % len(SHARD_V)
        d = SHARD_V[q] * brk + np.array([0, 700]) * brk ** 2
        ang = SHARD_W[q] * brk
        cx_, cy_ = xs[idx].mean(), ys[idx].mean()
        px = (xs[idx] - cx_) * math.cos(ang) - (ys[idx] - cy_) * math.sin(ang) + cx_ + d[0]
        py = (xs[idx] - cx_) * math.sin(ang) + (ys[idx] - cy_) * math.cos(ang) + cy_ + d[1]
        fr.stroke(list(zip(px, py)), col, k * max(0, 1 - brk / 1.5), 3, glow=1.2)


@scene(*SEC['oldmodel'], 0.3, 0.4)
def sc_oldmodel(fr, t, a):
    lt = t - OM0
    draw_dust(fr, t, a * 0.5)
    # ---------------- 1) 回到半个多世纪前：年份倒转
    kr = a * win(t, om(0.0), om(3.7), 0.3, 0.45)
    if kr > 0.01:
        p = eio(cl((lt - 0.4) / 2.3))
        yr = int(round(2026 - (2026 - 1960) * p))
        fr.glow((CX, 700), 300, GOLD, kr * 0.10)
        fr.text(str(yr), CX, 700, 190, 'inter_light', 'gold', kr, glow=0.5, track=0.04, blur=3 * (1 - abs(2 * p - 1)) * (p < 1))
        for i in range(-6, 7):                                 # 滚动的时间刻度
            x = CX + i * 80 + ((lt * 260) % 80) * (p < 1)
            fr.line((x, 860), (x, 880 if i % 2 else 892), GOLD, kr * 0.4 * (1 - abs(i) / 7), 2)
        fr.line((CX - 520, 860), (CX + 520, 860), GOLD, kr * 0.25, 1)
    two(fr, 'o_back', t, 1265, split=('要读懂这个奖，', '得先回到【半个多世纪前】'))
    # ---------------- 2) 菲利普斯图（1960 年代 → 1970 年代）
    shatter = t - HITS['shatter']
    k_chart = a * win(t, om(3.4), om(13.2), 0.5, 0.35) + a * win(t, om(17.8), om(33.4), 0.4, 0.6)
    k_chart = min(k_chart, a)
    if k_chart > 0.01:
        chart_axes(fr, k_chart)
        # 1960 年代的点
        dim60 = 1 - 0.4 * cl((t - HITS['stag']) / 0.6)
        for i, (yr, u, v) in enumerate(D60):
            kk = k_chart * eo((t - om(3.9) - i * 0.25) / 0.25) * dim60
            x, y = p2s(u, v)
            fr.disc((x, y), 9, GOLD, kk, glow=0.8)
            if yr in (1960, 1969):
                fr.text(str(yr), x + (26 if yr == 1969 else 0), y + (30 if yr == 1960 else -30), 24, 'inter_med', 'gold', kk,
                        glow=0)
        # 拟合曲线（旧规律）与上移的曲线（示意）
        xs, ys = curve_pts()
        if shatter < 0:
            m = int(len(xs) * cl((t - om(6.4)) / 1.2))
            if m > 1:
                fr.stroke(list(zip(xs[:m], ys[:m])), GOLD_HI, k_chart * 0.9 * dim60, 3, glow=1.0)
            kl = k_chart * win(t, om(7.0), HITS['stag'], 0.4, 0.4)
            fr.text('通胀高一点，失业就低一点', OX + XW * 0.62, OY - YH * 0.52, 34, 'sans_bold', 'gold', kl, glow=0.2)
            for j, (off, tt) in enumerate(((3.5, om(24.6)), (6.5, om(25.4)), (9.5, om(26.2)))):
                kc = k_chart * cl((t - tt) / 0.5)
                if kc > 0.01:
                    sx, sy = curve_pts(off * eo((t - tt) / 0.7))
                    col = lerp(np.asarray(GOLD), np.asarray(CORAL), (j + 1) / 3)
                    for i in range(0, len(sx) - 2, 3):
                        fr.line((sx[i], sy[i]), (sx[i + 1], sy[i + 1]), col, kc * 0.8, 3, glow=0.8)
            ka = k_chart * cl((t - om(26.8)) / 0.4)
            if ka > 0.01:
                x0, y0 = p2s(7.3, phillips(7.3, 0.6))
                fr.line((x0, y0 - 10), (x0, y0 - 160), CORAL_HI, ka, 4, glow=1.0)
                for s_ in (-1, 1):
                    fr.line((x0, y0 - 160), (x0 + s_ * 18, y0 - 138), CORAL_HI, ka, 4, glow=1.0)
                fr.text('预期通胀 ↑', x0 + 44, y0 - 96, 30, 'sans_bold', 'coral', ka, anchor='l', glow=0.2)
        else:
            shards(fr, xs, ys, shatter, k_chart, GOLD_HI, 0)
            for j, off in enumerate((3.5, 6.5, 9.5)):
                sx, sy = curve_pts(off)
                shards(fr, sx, sy, shatter * (1 + 0.15 * j), k_chart * 0.8, CORAL, j + 1, 12)
        # 菜单：沿曲线滑动的点
        km = k_chart * win(t, om(8.8), om(13.0), 0.3, 0.3)
        if km > 0.01:
            pm = eio(cl((t - om(9.0)) / 2.0))
            u = lerp(6.4, 3.65, pm)
            x, y = p2s(u, phillips(u))
            for xx in np.arange(OX, x, 18):
                fr.line((xx, y), (min(xx + 8, x), y), WHITE, km * 0.45, 2)
            for yy in np.arange(y, OY, 18):
                fr.line((x, yy), (x, min(yy + 8, OY)), WHITE, km * 0.45, 2)
            fr.glow((x, y), 40, GOLD_HI, km * 0.8)
            fr.disc((x, y), 13, GOLD_HI, km, glow=1.2)
            fr.circle((x, y), 24 + 6 * math.sin(t * 6), GOLD_HI, km * 0.6, 2)
            chip(fr, '被当成一份政策「菜单」', CX, 432, km * cl((t - om(9.2)) / 0.4), GOLD, 34, fname='sans_bold')
        # 1970 年代：两次石油危机后的点一路飞向右上
        if t > HITS['stag'] - 0.2:
            pts = []
            for i, (yr, u, v) in enumerate(D70):
                g = eback((t - HITS['stag'] - 0.18 * i) / 0.4)
                if g <= 0:
                    continue
                x, y = p2s(u, v)
                pts.append((x, y))
                kk = k_chart * cl(g)
                fr.disc((x, y), 10 * g, CORAL, kk, glow=1.2)
                lab = {1974: ('1974 / 1979', 0, -36), 1975: ('1975', 46, 0), 1980: ('1980', 0, -34)}.get(yr)
                if lab:
                    fr.text(lab[0], x + lab[1], y + lab[2], 26, 'inter_bold', 'coral',
                            kk * cl((t - HITS['stag'] - 0.18 * i - 0.3) / 0.3), glow=0.1)
        ks = k_chart * win(t, om(19.2), om(24.0), 0.3, 0.3)
        chip(fr, '滞胀 = 高通胀 + 经济停滞', CX, 432, ks, CORAL, 36, fname='sans_bold', base='coral')
        kc = k_chart * win(t, om(20.4), om(32.0), 0.4, 0.4)
        fr.text('成因：1973、1979 年两次石油危机，叠加此前多年的宽松政策', CX, OY + 120, 28, 'sans_med', 'grey', kc, glow=0)
        chip(fr, '示意：通胀预期上升，曲线整体上移', CX, 432, k_chart * win(t, om(24.8), om(28.6), 0.3, 0.3),
             GREY, 32, base='white')
        chip(fr, '卢卡斯批判（1976）：政策一变，人的预期和行为也会变', CX, 432,
             k_chart * win(t, om(29.0), om(32.6), 0.3, 0.3), ICE, 30, fname='sans_bold', base='ice')
        footnote(fr, '美国年均 CPI 涨幅与年均失业率 · 数据：美国劳工统计局', k_chart * (1 - cl((t - om(32.0)) / 0.5)))
    # ---------------- 3) 1973 年石油危机：油价约 4 倍
    ko = a * win(t, HITS['oil'], om(18.0), 0.25, 0.35)
    if ko > 0.01:
        lo = t - HITS['oil']
        fr.flash = max(fr.flash, 0.16 * math.exp(-lo / 0.1) * (lo > 0))
        fr.text('中东原油标价（美元 / 桶）', CX, 360, 36, 'sans_med', 'grey', ko, glow=0)
        zero = 1040
        for i, (lab, v, y1, y2) in enumerate(OIL):
            x = 300 + i * 240
            g = eback((lo - 0.4 - 0.6 * i) / 0.55, 1.4)
            if g <= 0:
                continue
            hh = v * 46 * g
            col = [GOLD, C(240, 160, 70), CORAL][i]
            bar_glass(fr, x - 70, zero - hh, x + 70, zero, col, ko, 2.5)
            if i == 0:
                rich(fr, [('约', 'sans_bold', 30, 'gold'), (lab, 'inter_xbold', 44, 'gold')], x, zero - hh - 44, ko * cl(g), gap=6)
            else:
                fr.text(lab, x, zero - hh - 44, 52 if i == 2 else 44, 'inter_xbold', 'coral' if i == 2 else 'gold',
                        ko * cl(g), glow=0.3)
            fr.text(y1, x, zero + 40, 30, 'sans_bold', 'grey', ko, glow=0)
            fr.text(y2, x, zero + 78, 28, 'sans_med', 'grey', ko, glow=0)
        fr.line((180, zero), (900, zero), WHITE, ko * 0.35, 2)
        k4 = ko * eback((lo - 2.4) / 0.4)
        if k4 > 0.01:
            p0, p1 = np.array([300.0, zero - 2.9 * 46 - 90]), np.array([780.0 - 90, zero - 11.65 * 46 - 10])
            m = cl((lo - 2.4) / 0.5)
            for u in np.arange(0, m, 0.06):
                q0, q1 = p0 + (p1 - p0) * u, p0 + (p1 - p0) * min(u + 0.035, m)
                fr.line(tuple(q0), tuple(q1), CORAL, ko * 0.8, 3, glow=0.8)
            fr.text('≈ × 4', 500, zero - 470, 66, 'inter_xbold', 'coral', cl(k4) * ko, glow=0.5, scale=0.8 + 0.2 * cl(k4))
        footnote(fr, '1973 年 10 月中东战争后，产油国大幅提高原油标价 · 资料：OPEC', ko)
    # ---------------- 4) 碎片聚拢 → 家庭与企业的格点
    t_r = HITS['rebuild']
    kl = a * win(t, t_r - 0.2, om(37.2), 0.4, 0.6)
    if kl > 0.01:
        p = eio((t - t_r) / 2.4)
        P = SRC_RND * (1 - p) + LAT * p
        for i in range(LAT_N):
            fr.disc(tuple(P[i]), 7, ICE if LAT_KIND[i] else GOLD, kl, glow=0.9)
        if p > 0.6:
            kq = kl * cl((p - 0.6) / 0.4)
            for i in range(LAT_N):
                j = i + 1
                if j < LAT_N and j % 14:
                    fr.line(tuple(P[i]), tuple(P[j]), GOLD, kq * 0.25, 1)
                if i + 14 < LAT_N:
                    fr.line(tuple(P[i]), tuple(P[i + 14]), GOLD, kq * 0.2, 1)
        kg = kl * cl((t - t_r - 1.2) / 0.5)
        fr.disc((360, 1150), 8, GOLD, kg)
        fr.text('家庭', 376, 1150, 30, 'sans_bold', 'gold', kg, anchor='l', glow=0)
        fr.disc((620, 1150), 8, ICE, kg)
        fr.text('企业', 636, 1150, 30, 'sans_bold', 'ice', kg, anchor='l', glow=0)
    two(fr, 'o_new', t, 1265, split=('经济学家从家庭和企业出发，', '【重建宏观模型】'))
    # ---------------- 5) 新凯恩斯主义模型的三块基石
    kn = a * cw('o_nk', t, 0.5, 0.4)
    if kn > 0.01:
        fr.text('新凯恩斯主义模型', CX, 330, 78, 'serif_black', 'gold', kn, glow=0.45,
                stagger=(t - CAP['o_nk'][0], 0.06, 0.45))
        fr.text('New Keynesian Model', CX, 420, 32, 'corm_bold', 'subgold', kn * cl((t - CAP['o_nk'][0] - 0.6) / 0.5),
                track=0.12, glow=0.2)
        for i, (nm, sub, col, base) in enumerate(NK_BLOCKS):
            p = eback((t - HITS['blocks'] - 1.5 * i) / 0.6, 1.4)
            y = 520 + i * 160 + (1 - cl(p)) * 100
            kk = kn * cl(p)
            if kk <= 0.01:
                continue
            fr.card(110, y, 970, y + 130, 26, kk, tint=col, border=col, border_a=0.75, fill_a=0.08, blur=12)
            fr.text(f'{"①②③"[i]}', 158, y + 65, 40, 'sans_bold', base, kk, glow=0.2)
            fr.text(nm, 200, y + 65, 52, 'serif_black', base, kk, anchor='l', glow=0.25)
            fr.text(sub, 930, y + 65, 32, 'sans_med', 'white', kk, anchor='r', glow=0)
        kf = kn * cl((t - HITS['blocks'] - 3.8) / 0.6)
        if kf > 0.01:
            fr.rrect(96, 506, 984, 1004, 34, GOLD, kf * 0.5, 2, glow=0.8)
        chip(fr, '经济冲击  →  模型推演  →  政策应对', CX, 1090, kn * win(t, om(42.4), om(46.2), 0.4, 0.3), GOLD, 34,
             fname='sans_bold')
        kb = kn * cl((t - HITS['base'] - 0.4) / 0.6)
        if kb > 0.01:
            fr.line((110, 1036), (970, 1036), GOLD_HI, kb, 4, glow=1.2)
            fr.glow((CX, 1036), 300, GOLD, kb * 0.12)
            for x, s_, col, base, d in ((330, '霍尔：家庭怎么花钱', GOLD, 'gold', 0.0), (760, '伍德福德：企业定价 · 央行', ICE, 'ice', 0.35)):
                kp = kb * eo((t - HITS['base'] - 0.6 - d) / 0.5)
                fr.line((x, 1040), (x, 1068), col, kp * 0.7, 2)
                chip(fr, s_, x, 1104, kp, col, 32, fname='sans_bold', base=base)
    two(fr, 'o_tool', t, 1265, split=('成为现代央行', '分析冲击、制定政策的【重要工具】'))
    two(fr, 'o_base', t, 1265, split=('今年两位得主的研究，', '正是这套框架的【基石】'))
    two(fr, 'o_old', t, 1265, split=('二战后的宏观模型，', '靠总量数据之间的【统计规律】'))
    two(fr, 'o_menu', t, 1265, split=('政府以为：多容忍一点通胀，', '就能换来【更多就业】'))
    two(fr, 'o_oil', t, 1265, split=('1973 年石油危机：', '几个月里，油价涨了约【4 倍】'))
    two(fr, 'o_stag', t, 1265, split=('物价飞涨，经济却停滞不前：', '这就是〖「滞胀」〗'))
    two(fr, 'o_fail', t, 1265, split=('沿用旧模型刺激需求，', '往往只换来〖更高的通胀〗'))
    two(fr, 'o_why', t, 1265, split=('因为人会预判未来：', '预期一变，【旧规律就失灵】'))
    if 0 < shatter < 1.2:
        sh = 12 * math.exp(-shatter / 0.25)
        fr.cam = (sh * math.sin(shatter * 70), sh * math.cos(shatter * 53))


# ================================================================ 名片
def name_card(fr, t, t0, t1, who, en, zh, badge, a):
    k = a * win(t, t0, t1, 0.5, 0.45)
    if k <= 0.01:
        return
    rgb, al = portraits.lineart(who)
    p = (t - t0) / (t1 - t0)
    fr.image(rgb, al, CX, 720, k * 0.28, scale=1.06 - 0.06 * ss(p))
    fr.glow((CX, 720), 380, GOLD, k * 0.06)
    fr.text(en, CX, 1190, 70, 'corm_bold', 'gold', k * eo((t - t0 - 0.2) / 0.6), track=0.1, glow=0.35)
    fr.text(zh, CX, 1266, 38, 'sans_med', 'grey', k * eo((t - t0 - 0.4) / 0.6), track=0.08, glow=0)
    ln = 260 * eo((t - t0 - 0.3) / 0.8)

    def rule(img, k=k, ln=ln):
        if ln > 2:
            y = 1229
            img[y:y + 2, int(CX - ln / 2):int(CX + ln / 2)] = img[y:y + 2, int(CX - ln / 2):int(CX + ln / 2)] * \
                (1 - 0.7 * k) + 0.7 * k * GOLD
    fr.overlay_fn(rule)
    chip(fr, badge, CX, 1345, k * eo((t - t0 - 0.6) / 0.5), GOLD, 32, fname='sans_med')


# ================================================================ 03 霍尔 132–180
def income(age):
    age = np.asarray(age, np.float64)
    work = 0.28 + 0.72 * np.sin(np.pi * np.clip((age - 20) / 58, 0, 1)) ** 0.9
    ret = 1 / (1 + np.exp((age - 63) / 0.9))
    return work * ret + 0.24 * (1 - ret)


AX0, AX1, AY0, AYH = 150, 930, 1080, 500
TODAY = 35.0


def a2s(age, v):
    return AX0 + (np.asarray(age) - 20) / 65 * (AX1 - AX0), AY0 - np.asarray(v) * AYH


H_FIELD_CAM = lambda t: Cam((0, 7.5, -46 + (t - 140) * 0.6), (0, 0.0, 6 + (t - 140) * 0.6), fov=56, cy=H * 0.42)


@scene(*SEC['hall'], 0.3, 0.3)
def sc_hall(fr, t, a):
    t0 = SEC['hall'][0]
    lt = t - t0
    fr.flash = max(fr.flash, 0.3 * math.exp(-lt / 0.1) * a)
    draw_dust(fr, t, a * 0.5)
    # ---- A 名片 + 第一个问题
    name_card(fr, t, t0, t0 + 6.2, 'hall', 'ROBERT E. HALL', '罗伯特·霍尔 · 斯坦福大学', '1978 · 消费与预期', a)
    k = a * cw('h_q', t, 0.4, 0.4)
    fr.text('第一个问题：', CX, 250, 48, 'serif_bold', 'gold', k, glow=0.2, stagger=(t - CAP['h_q'][0], 0.05, 0.4))
    fr.text('家庭，到底按什么花钱？', CX, 345, 66, 'serif_black', 'white', k, glow=0.3, stagger=(t - CAP['h_q'][0] - 0.3, 0.045, 0.45))
    # ---- B 发现①
    law_card(fr, t, CAP['h_l1'][0], CAP['h_l1'][1] + 0.3, '霍尔的发现 ①', '花钱，看的是一辈子', a)
    kb = a * win(t, CAP['h_l1'][1], CAP['h_l1cap'][1] + 0.2, 0.45, 0.4)
    if kb > 0.01:
        header(fr, '① 花钱，看的是一辈子', kb)
        life_chart(fr, t, kb)
    for key in ('h_bonus', 'h_raise'):
        k = a * cw(key, t, 0.3, 0.3)
        fr.text(CAP[key][2].replace('：', '：【', 1) + '】', CX, 1290, 60, 'serif_black', 'white', k, glow=0.3,
                stagger=(t - CAP[key][0], 0.045, 0.4))
    k = a * cw('h_l1cap', t, 0.35, 0.4)
    fr.text('决定今天花多少的，', CX, 1250, 56, 'serif_bold', 'white', k, glow=0.2, stagger=(t - CAP['h_l1cap'][0], 0.04, 0.4))
    fr.text('是对【未来收入】的判断', CX, 1345, 66, 'serif_black', 'white', k, glow=0.3,
            stagger=(t - CAP['h_l1cap'][0] - 0.3, 0.045, 0.45))
    # ---- C 同样月入一万
    kc = a * win(t, CAP['h_two'][0], CAP['h_two'][1], 0.4, 0.4)
    if kc > 0.01:
        header(fr, '① 花钱，看的是一辈子', kc * 0.8, y=200, size=38)
        two_people(fr, t, kc)
    # ---- D 发现②
    law_card(fr, t, CAP['h_l2'][0], CAP['h_l2'][1] + 0.3, '霍尔的发现 ②', '消费，只为「意外」而变', a)
    kd = a * win(t, CAP['h_l2'][1], CAP['h_surp'][1] + 0.3, 0.45, 0.4)
    if kd > 0.01:
        header(fr, '② 消费，只为「意外」而变', kd)
        random_walk(fr, t, kd)
    ke = a * win(t, CAP['h_vote'][0] - 0.3, SEC['hall'][1] + 0.3, 0.5, 0.3)
    if ke > 0.01:
        vote_field(fr, t, ke)


def life_chart(fr, t, k):
    t0 = CAP['h_l1'][1]
    fr.line((AX0, AY0), (AX1 + 10, AY0), GREY, k * 0.55, 2)
    for age in (20, 40, 60, 80):
        x, _ = a2s(age, 0)
        fr.text(f'{age}岁', x, AY0 + 40, 28, 'sans_med', 'dim', k, glow=0)
    draw = cl((t - t0) / 2.0)
    ages = np.linspace(20, 85, 260)
    bonus = ss((t - HITS['bonus']) / 0.6) * (1 - ss((t - HITS['raise']) / 0.5))
    rai = ss((t - HITS['raise']) / 1.0)
    inc = income(ages) + 0.42 * bonus * np.exp(-((ages - TODAY) / 0.9) ** 2) \
        + 0.17 * rai * ss((ages - TODAY) / 1.5) * (ages < 62.5)
    con0 = 0.50 + 0.10 * (ages - 20) / 65
    con = con0 + 0.012 * bonus * (ages >= TODAY) + 0.085 * rai * ss((ages - TODAY) / 1.0)
    m = max(2, int(len(ages) * draw))
    xi, yi = a2s(ages[:m], inc[:m])
    xc, yc = a2s(ages[:m], con[:m])
    if rai > 0.01 or bonus > 0.01:       # 原消费线（虚影）作对照
        xo, yo = a2s(ages, con0)
        fr.stroke(list(zip(xo, yo)), GREY, k * 0.35, 2)
    fr.stroke(list(zip(xi, yi)), GOLD, k, 4, glow=1.0)
    fr.stroke(list(zip(xc, yc)), WHITE, k, 3.5, glow=0.7)
    if draw > 0.98:
        x, y = a2s(84, inc[-1])
        fr.text('收入', x - 10, y - 34, 34, 'sans_bold', 'gold', k, anchor='r', glow=0.1)
        x, y = a2s(84, con[-1])
        fr.text('消费', x - 10, y - 36, 34, 'sans_bold', 'white', k, anchor='r', glow=0.1)
    kt = k * cl((t - t0 - 1.6) / 0.5)
    x, _ = a2s(TODAY, 0)
    for yy in range(int(AY0 - AYH * 1.05), int(AY0), 22):
        fr.line((x, yy), (x, yy + 11), WHITE, kt * 0.5, 2)
    fr.text('今天', x - 16, AY0 - 34, 34, 'serif_bold', 'white', kt, anchor='r', glow=0.2)
    if bonus > 0.05:
        xb, yb = a2s(TODAY, income(TODAY) + 0.42)
        chip(fr, '一次性奖金', xb + 150, yb - 10, k * bonus, GOLD, 32, fname='sans_bold')
    if rai > 0.05:
        xr, yr = a2s(48, income(48) + 0.17)
        chip(fr, '长期涨薪', xr + 40, yr - 60, k * rai, GOLD, 32, fname='sans_bold')
        xc2, yc2 = a2s(60, 0.50 + 0.1 * 40 / 65 + 0.085)
        fr.text('↑', xc2, yc2 - 34, 50, 'inter_bold', 'gold', k * rai, glow=0.3)


def two_people(fr, t, k):
    t0 = CAP['h_two'][0]
    fr.text('同样月入一万', CX, 320, 84, 'serif_black', 'white', k, glow=0.3, stagger=(t - t0, 0.06, 0.45))
    for j, (x, base, col, lab, spend, save) in enumerate(((290, 'gold', GOLD, '相信明天更好', 0.8, 0.2),
                                                          (790, 'ice', ICE, '担心明天失业', 0.55, 0.45))):
        kk = k * eo((t - t0 - 0.4 - j * 0.25) / 0.5)
        cx0, cy0, cw_, ch_ = x - 215, 410, 430, 175
        fr.card(cx0, cy0, cx0 + cw_, cy0 + ch_, 22, kk, tint=col, border=col, border_a=0.5, fill_a=0.05, blur=8)
        fr.text('预期的未来收入', cx0 + 24, cy0 + 32, 28, 'sans_bold', base, kk, anchor='l', glow=0)
        us = np.linspace(0, 1, 60)
        draw = eo((t - t0 - 0.6 - j * 0.25) / 1.0)
        m = max(2, int(60 * draw))
        px = cx0 + 30 + (cw_ - 60) * us
        if j == 0:
            py = cy0 + 148 - 82 * us ** 0.8
            fr.stroke(list(zip(px[:m], py[:m])), GOLD, kk, 6, layer='B')
            fr.overlay_draw(lambda cv, px=px, py=py, m=m, kk=kk: cv.stroke(list(zip(px[:m], py[:m])), GOLD_HI, kk, 4.5))
        else:
            py = cy0 + 100 + 12 * np.sin(us * 9) + 40 * np.clip((us - 0.45) * 2, 0, 1) ** 1.5

            def dashes(cv, px=px, py=py, m=m, kk=kk):
                for i in range(0, m - 2, 4):
                    cv.line((px[i], py[i]), (px[i + 2], py[i + 2]), ICE_HI, kk, 4.5)
            fr.overlay_draw(dashes)
            if draw > 0.9:
                fr.text('?', cx0 + cw_ - 34, cy0 + 70, 46, 'inter_bold', 'ice', kk * (0.6 + 0.4 * math.sin(t * 8)), glow=0.3)
        icon(fr, 'person', (x, 712), 150, col, kk, 4, glow=1.0)
        fr.text(lab, x, 846, 44, 'sans_bold', base, kk, glow=0.15)
        fr.text('收入 ¥10,000', x, 900, 32, 'sans_med', 'grey', kk, glow=0)
        g = eo((t - t0 - 1.6 - 0.2 * j) / 0.9)
        base_y, hmax = 1170, 220
        for i, (v, nm) in enumerate(((spend, '消费'), (save, '储蓄'))):
            bx = x - 70 + i * 140
            hh = hmax * v * g
            bar_glass(fr, bx - 48, base_y - hh, bx + 48, base_y, GOLD if i == 0 else ICE, kk, 2)
            fr.text(nm, bx, base_y + 36, 30, 'sans_med', 'grey', kk, glow=0)
    k2 = k * cw('h_twocap', t, 0.35, 0.3)
    fr.text('对明天的判断不同，', CX, 1300, 56, 'serif_bold', 'white', k2, glow=0.2, stagger=(t - CAP['h_twocap'][0], 0.04, 0.4))
    fr.text('今天的消费就【不同】', CX, 1395, 64, 'serif_black', 'white', k2, glow=0.3,
            stagger=(t - CAP['h_twocap'][0] - 0.3, 0.05, 0.45))
    footnote(fr, '示意：收入相同，对未来的预期不同', k, y=1500)


RW_X0, RW_X1, RW_Y = 130, 950, 820
EV_KNOWN = 0.25     # 时间轴上的位置（0~1）
EV_SURP = 0.68


def random_walk(fr, t, k):
    """消费随时间的路径：预料之中的事件不改变它，意外消息让它跳变"""
    t0 = CAP['h_l2'][1]
    prog = cl((t - t0 - 0.2) / ((HITS['surprise'] - t0 - 0.2) / EV_SURP))   # 意外正好落在重拍上
    fr.line((RW_X0, RW_Y + 220), (RW_X1, RW_Y + 220), GREY, k * 0.5, 2)
    fr.text('时间 →', RW_X1, RW_Y + 258, 30, 'sans_med', 'grey', k, anchor='r', glow=0)
    fr.text('消费', RW_X0, RW_Y - 170, 34, 'sans_bold', 'white', k, anchor='l', glow=0)
    xs = np.linspace(RW_X0, RW_X1, 300)
    u = (xs - RW_X0) / (RW_X1 - RW_X0)
    r = np.random.default_rng(5)
    wob = np.cumsum(r.normal(0, 1, 300)) * 0.6
    wob -= np.linspace(0, wob[-1], 300)
    drop = 110 * ss((u - EV_SURP) / 0.012)
    ys = RW_Y + wob + drop
    m = max(2, int(300 * prog))
    fr.stroke(list(zip(xs[:m], ys[:m])), WHITE, k, 4, glow=0.8)
    fr.glow((xs[m - 1], ys[m - 1]), 12, WHITE, k)
    # 事件 1：预料之中
    xk = RW_X0 + EV_KNOWN * (RW_X1 - RW_X0)
    kk = k * cl((prog - EV_KNOWN + 0.02) / 0.03)
    if kk > 0.01:
        fr.line((xk, RW_Y - 120), (xk, RW_Y + 200), GOLD, kk * 0.5, 2)
        fr.card(xk - 125, RW_Y - 300, xk + 125, RW_Y - 150, 22, kk, tint=GOLD, border=GOLD, border_a=0.6, fill_a=0.06, blur=8)
        fr.text('如期涨薪', xk, RW_Y - 250, 40, 'serif_bold', 'gold', kk, glow=0.1)
        fr.text('早就知道', xk, RW_Y - 192, 30, 'sans_med', 'grey', kk, glow=0)
        fr.text('→ 消费不动', xk, RW_Y + 160, 30, 'sans_bold', 'gold', kk * cl((prog - EV_KNOWN - 0.04) / 0.04), glow=0)
    # 事件 2：意外
    xs2 = RW_X0 + EV_SURP * (RW_X1 - RW_X0)
    kk = k * cl((prog - EV_SURP + 0.02) / 0.03)
    if kk > 0.01:
        fr.line((xs2, RW_Y - 120), (xs2, RW_Y + 200), CORAL, kk * 0.6, 2)
        fr.card(xs2 - 125, RW_Y - 300, xs2 + 125, RW_Y - 150, 22, kk, tint=CORAL, border=CORAL, border_a=0.7,
                fill_a=0.07, blur=8)
        fr.text('裁员传闻', xs2, RW_Y - 250, 40, 'serif_bold', 'coral', kk, glow=0.2)
        fr.text('没想到', xs2, RW_Y - 192, 30, 'sans_med', 'grey', kk, glow=0)
        if prog > EV_SURP + 0.02:
            fr.flash = max(fr.flash, 0.12 * math.exp(-(t - HITS['surprise']) / 0.1) * (t > HITS['surprise']))
            fr.text('↓ 消费立刻下调', min(xs2 + 150, 930), RW_Y + 160, 30, 'sans_bold', 'coral', kk, glow=0.1)
    fr.text('经济学上称为「随机游走」（Hall, 1978）', CX, RW_Y + 330, 30, 'sans_med', 'dim',
            k * cl((prog - 0.75) / 0.1), glow=0)
    for key in ('h_known', 'h_surp'):
        kc = k * cw(key, t, 0.3, 0.3)
        s = CAP[key][2]
        l1, l2 = s.split('，', 1)
        fr.text(l1 + '，', CX, 1265, 56, 'serif_bold', 'white', kc, glow=0.2, stagger=(t - CAP[key][0], 0.04, 0.4))
        l2 = l2.replace('今天的消费', '【今天的消费】') if key == 'h_known' else l2.replace('突然转向', '〖突然转向〗')
        fr.text(l2, CX, 1360, 62, 'serif_black', 'white', kc, glow=0.3, stagger=(t - CAP[key][0] - 0.3, 0.04, 0.45))


_VR = np.random.default_rng(12)
VOTE_IDX = _VR.choice(FIELD.n, 800, replace=False)
VOTE_T = _VR.random(800) * 1.8


def vote_field(fr, t, k):
    t0 = CAP['h_vote'][0]
    cam = H_FIELD_CAM(t)
    res = FIELD.draw(fr, cam, t, k, warm=np.full(FIELD.n, 0.85))
    hx, hy, _, _ = cam.project([[0, 0, 60]])
    hx, hy = float(hx[0]), float(hy[0])
    if res is not None:
        x, y, zz, s, ok = res
        dt = np.clip((t - t0 - VOTE_T) / 1.4, 0, 1)
        sel = (dt > 0) & ok[VOTE_IDX]
        idx = VOTE_IDX[sel]
        d = dt[sel]
        px = x[idx] * (1 - eo(d)) + hx * eo(d)
        py = y[idx] * (1 - eo(d)) + (hy - 10) * eo(d)
        fr.dots(px, py, 1.6, GOLD_HI, k * np.sin(np.pi * d) * 1.2)
        fr.splat(px, py, GOLD, k * np.sin(np.pi * d) * 2.5, layer='B')
    fr.glow((hx, hy), 140, GOLD, k * 0.35 * cl((t - t0 - 0.8) / 1.0))
    xs = np.linspace(-80, W + 80, 60)
    fr.stroke(list(zip(xs, np.full(60, hy))), GOLD_HI, k * 0.5, 2, glow=1.2)
    kc = k * cw('h_vote', t, 0.35, 0.3)
    fr.text('所以，消费是', CX, 290, 58, 'serif_bold', 'white', kc, glow=0.2, stagger=(t - t0, 0.04, 0.4))
    fr.text('对未来最诚实的【投票】', CX, 390, 70, 'serif_black', 'white', kc, glow=0.35, stagger=(t - t0 - 0.3, 0.05, 0.45))
