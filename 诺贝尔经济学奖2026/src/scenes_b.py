"""02 地基（诺奖、旧模型失灵、微观基础）→ 03 霍尔：家庭的预期 → 04 伍德福德：企业与央行"""
import math

import numpy as np

from common import *          # noqa: F401,F403
from registry import scene
from timeline import CAP, HITS
from scenes_a import caption, chip, num_unit, rich, bar_glass
import portraits

CX = W / 2


def cw(key, t, fi=0.35, fo=0.3):
    t0, t1, _ = CAP[key]
    return win(t, t0, t1, fi, fo)


def two_lines(fr, l1, l2, y, k, t0, t, s1=58, s2=66, f1='serif_bold', f2='serif_black', gap=1.32):
    fr.text(l1, CX, y, s1, f1, 'white', k, glow=0.2, stagger=(t - t0, 0.035, 0.4))
    fr.text(l2, CX, y + s2 * gap, s2, f2, 'white', k, glow=0.3, stagger=(t - t0 - 0.2, 0.035, 0.45))


# ================================================================ 诺奖 60–64
_MR = np.random.default_rng(3)
RING_N = 1600
RING_A = _MR.random(RING_N) * 2 * np.pi
RING_R = 1 + _MR.normal(0, 0.03, RING_N)
RING_Z = _MR.normal(0, 0.05, RING_N)


@scene(60.0, 64.0, 0.0, 0.4)
def sc_nobel(fr, t, a):
    lt = t - 60.0
    fr.flash = max(fr.flash, 0.8 * math.exp(-lt / 0.06) * a)
    fr.ca = max(fr.ca, 6 * math.exp(-lt / 0.2))
    c = (CX, 760)
    p = eo(lt / 1.2)
    R = 300 * (0.6 + 0.4 * p)
    rot = lt * 0.5
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
    # 光束
    for k in range(12):
        q = rot * 0.3 + k * np.pi / 6
        L = 900
        p0 = (c[0] + R * 0.9 * math.cos(q), c[1] + R * 0.9 * math.sin(q))
        p1 = (c[0] + L * math.cos(q - 0.03), c[1] + L * math.sin(q - 0.03))
        p2 = (c[0] + L * math.cos(q + 0.03), c[1] + L * math.sin(q + 0.03))
        fr.fill([p0, p1, p2], GOLD * 0.05, a * p, layer='B')
    fr.glow(c, 240, GOLD, a * 0.18 * p)
    fr.text('2026', CX, 735, 150, 'inter_light', 'gold', a * p, glow=0.5, track=0.05)
    fr.text('ECONOMIC SCIENCES', CX, 840, 30, 'corm_bold', 'subgold', a * p, track=0.32, glow=0.2)
    draw_dust(fr, t, a * 0.7, speed=1.5)
    k = a * cw('nb_head', t)
    fr.text('今年的诺贝尔经济学奖，', CX, 1185, 56, 'serif_bold', 'white', k, stagger=(t - 60.2, 0.035, 0.4))
    fr.text('回答的正是【这个问题】', CX, 1280, 64, 'serif_black', 'white', k, glow=0.3, stagger=(t - 60.6, 0.04, 0.45))


# ================================================================ 旧模型失灵 → 微观基础 64–72
OX, OY = 190, 1060          # 坐标原点
XW, YH = 720, 500
PTS60 = [(0.08, 0.80), (0.16, 0.62), (0.25, 0.50), (0.34, 0.41), (0.43, 0.34), (0.53, 0.28), (0.63, 0.23),
         (0.74, 0.19), (0.86, 0.16)]
PTS70 = [(0.45, 0.62), (0.62, 0.72), (0.55, 0.85), (0.78, 0.70), (0.70, 0.93), (0.88, 0.84), (0.95, 0.97)]
_SR = np.random.default_rng(8)
SHARD_V = _SR.normal(0, 1, (40, 2)) * np.array([520, 420]) + np.array([0, -150])
SHARD_W = _SR.normal(0, 6, 40)
LAT_N = 84
LAT = np.array([(150 + (i % 14) * 60 + (30 if (i // 14) % 2 else 0), 1150 - (i // 14) * 52) for i in range(LAT_N)],
               np.float64)
LAT_KIND = _SR.random(LAT_N) < 0.25


def p2s(u, v):
    return OX + u * XW, OY - v * YH


def curve60(n=60):
    u = np.linspace(0.05, 0.92, n)
    v = 0.12 + 0.065 / (u + 0.02)
    v = np.clip(v, 0, 1.0)
    return u, v


@scene(64.0, 72.0, 0.3, 0.4)
def sc_oldmodel(fr, t, a):
    draw_dust(fr, t, a * 0.5)
    brk = t - HITS['break70s']
    if brk > 0:
        sh = 14 * math.exp(-brk / 0.25)
        fr.cam = (sh * math.sin(brk * 70), sh * math.cos(brk * 53))
    k_chart = a * (1 - ss((t - 68.2) / 0.8))
    # 坐标轴
    if k_chart > 0.01:
        fr.line((OX, OY), (OX + XW + 20, OY), GREY, k_chart * 0.6, 2)
        fr.line((OX, OY), (OX, OY - YH - 30), GREY, k_chart * 0.6, 2)
        fr.text('失业率 →', OX + XW, OY + 42, 32, 'sans_med', 'grey', k_chart, anchor='r', glow=0)
        fr.text('通胀率 ↑', OX + 10, OY - YH - 60, 32, 'sans_med', 'grey', k_chart, anchor='l', glow=0)
        for i, (u, v) in enumerate(PTS60):
            kk = k_chart * eo((t - 64.2 - i * 0.26) / 0.25)
            x, y = p2s(u, v)
            fr.disc((x, y), 9, GOLD, kk, glow=0.8)
        # 拟合曲线（1970 年代碎裂）
        u, v = curve60()
        xs, ys = p2s(u, v)
        if brk < 0:
            m = int(len(u) * cl((t - 65.0) / 1.0))
            if m > 1:
                fr.stroke(list(zip(xs[:m], ys[:m])), GOLD_HI, k_chart * 0.9, 3, glow=1.0)
            kk = k_chart * cl((t - 65.4) / 0.4)
            fr.text('通胀高一点，失业就低一点', OX + XW * 0.62, OY - YH * 0.52, 34, 'sans_bold', 'gold', kk, glow=0.2)
        else:
            seg = np.array_split(np.arange(len(u)), 20)
            for j, idx in enumerate(seg):
                if len(idx) < 2:
                    continue
                d = SHARD_V[j] * brk + np.array([0, 900]) * brk ** 2
                ang = SHARD_W[j] * brk
                cx_, cy_ = xs[idx].mean(), ys[idx].mean()
                px = (xs[idx] - cx_) * math.cos(ang) - (ys[idx] - cy_) * math.sin(ang) + cx_ + d[0]
                py = (xs[idx] - cx_) * math.sin(ang) + (ys[idx] - cy_) * math.cos(ang) + cy_ + d[1]
                fr.stroke(list(zip(px, py)), GOLD_HI, k_chart * max(0, 1 - brk / 1.3), 3, glow=1.2)
            for i, (uu, vv) in enumerate(PTS70):
                kk = k_chart * eback((brk - i * 0.07) / 0.3)
                x, y = p2s(uu, vv)
                fr.disc((x, y), 11 * kk, CORAL, cl(kk), glow=1.2)
            kk = a * win(t, 66.6, 68.5, 0.2, 0.3)
            chip(fr, '1970年代 · 滞胀：规律失灵', CX, 1180, kk, CORAL, 40, base='coral')
    k = a * cw('om_old', t, 0.35, 0.35)
    fr.text('过去的模型，', CX, 270, 56, 'serif_bold', 'grey', k, stagger=(t - 64.2, 0.04, 0.4))
    fr.text('只看数字间的统计规律', CX, 360, 64, 'serif_black', 'white', k, glow=0.25, stagger=(t - 64.4, 0.04, 0.4))
    # 重建：碎片汇成「家庭与企业」的格点，托起宏观
    kr = a * cl((t - 68.3) / 0.5)
    if kr > 0.01:
        p = eio((t - 68.3) / 1.4)
        r = np.random.default_rng(1)
        src = np.c_[r.uniform(100, 980, LAT_N), r.uniform(500, 1100, LAT_N)]
        P = src * (1 - p) + LAT * p
        for i in range(LAT_N):
            col = ICE if LAT_KIND[i] else GOLD
            fr.disc(tuple(P[i]), 7, col, kr, glow=0.9)
        # 网格连线
        if p > 0.6:
            kl = kr * cl((p - 0.6) / 0.4)
            for i in range(LAT_N):
                j = i + 1
                if j < LAT_N and j % 14:
                    fr.line(tuple(P[i]), tuple(P[j]), GOLD, kl * 0.25, 1)
                if i + 14 < LAT_N:
                    fr.line(tuple(P[i]), tuple(P[i + 14]), GOLD, kl * 0.2, 1)
        # 上方的「宏观经济」
        kb = kr * eo((t - 69.4) / 0.7)
        y_top = 760 - 40 * (1 - kb)
        roof = [(170, 820), (540, 640), (910, 820)]
        fr.stroke(roof, GOLD_HI, kb, 3, closed=True, glow=1.0)
        fr.fill(roof, GOLD * 0.06, kb)
        fr.text('宏观经济', CX, 768, 48, 'serif_black', 'gold', kb, glow=0.4)
        for xx in np.linspace(230, 850, 8):
            fr.line((xx, 830), (xx, 880), GOLD, kb * 0.5, 2, glow=0.4)
        fr.line((150, 885), (930, 885), GOLD, kb * 0.7, 2, glow=0.6)
        fr.text('家庭', 150, 1210, 30, 'sans_bold', 'gold', kb, anchor='l', glow=0)
        fr.text('企业', 300, 1210, 30, 'sans_bold', 'ice', kb, anchor='l', glow=0)
        fr.disc((136, 1210), 7, GOLD, kb)
        fr.disc((286, 1210), 7, ICE, kb)
        kt = a * win(t, 69.6, 72.2, 0.5, 0.3)
        fr.text('微观基础  MICROFOUNDATIONS', CX, 560, 30, 'sans_bold', 'gold', kt, track=0.12, glow=0.3)
    k = a * cw('om_new', t, 0.4, 0.35)
    fr.text('从【每个家庭和企业】出发，', CX, 1285, 58, 'serif_bold', 'white', k, glow=0.25,
            stagger=(t - 68.4, 0.035, 0.4))
    fr.text('重新搭建宏观模型', CX, 1370, 62, 'serif_black', 'white', k, glow=0.3, stagger=(t - 68.7, 0.045, 0.45))


# ================================================================ 名片（霍尔 / 伍德福德）
def name_card(fr, t, t0, t1, who, en, zh, badge, a):
    k = a * win(t, t0, t1, 0.5, 0.45)
    if k <= 0.01:
        return
    rgb, al = portraits.lineart(who)
    p = (t - t0) / (t1 - t0)
    sc = 1.06 - 0.06 * ss(p)
    fr.image(rgb, al, CX, 700, k * 0.26, scale=sc)
    fr.glow((CX, 700), 380, GOLD, k * 0.06)
    fr.text(en, CX, 1185, 70, 'corm_bold', 'gold', k * eo((t - t0 - 0.2) / 0.6), track=0.1, glow=0.35)
    fr.text(zh, CX, 1262, 38, 'sans_med', 'grey', k * eo((t - t0 - 0.4) / 0.6), track=0.08, glow=0)
    ln = 260 * eo((t - t0 - 0.3) / 0.8)

    def rule(img, k=k, ln=ln):
        if ln > 2:
            y = 1225
            img[y:y + 2, int(CX - ln / 2):int(CX + ln / 2)] = img[y:y + 2, int(CX - ln / 2):int(CX + ln / 2)] * \
                (1 - 0.7 * k) + 0.7 * k * GOLD
    fr.overlay_fn(rule)
    chip(fr, badge, CX, 1340, k * eo((t - t0 - 0.6) / 0.5), GOLD, 32, fname='sans_med')


# ================================================================ 霍尔 72–94
def income(age):
    age = np.asarray(age, np.float64)
    work = 0.28 + 0.72 * np.sin(np.pi * np.clip((age - 20) / 58, 0, 1)) ** 0.9
    ret = 1 / (1 + np.exp((age - 63) / 0.9))
    return work * ret + 0.24 * (1 - ret)


def consumption(age):
    age = np.asarray(age, np.float64)
    return 0.50 + 0.10 * (age - 20) / 65


AX0, AX1, AY0, AYH = 150, 930, 1090, 470


def a2s(age, v):
    return AX0 + (np.asarray(age) - 20) / 65 * (AX1 - AX0), AY0 - np.asarray(v) * AYH


H_FIELD_CAM = lambda t: Cam((0, 7.5, -46 + (t - 88) * 0.5), (0, 0.0, 6 + (t - 88) * 0.5), fov=56, cy=H * 0.40)


@scene(72.0, 94.0, 0.3, 0.3)
def sc_hall(fr, t, a):
    lt = t - 72.0
    fr.flash = max(fr.flash, 0.3 * math.exp(-lt / 0.1) * a)
    draw_dust(fr, t, a * 0.5)
    # ---- A 名片
    name_card(fr, t, 72.0, 76.2, 'hall', 'ROBERT E. HALL', '罗伯特·霍尔 · 斯坦福大学', '1978 · 消费与预期', a)
    k = a * cw('ha_q', t, 0.4, 0.4)
    fr.text('你今天花多少，', CX, 250, 60, 'serif_bold', 'white', k, glow=0.2, stagger=(t - 73.0, 0.04, 0.4))
    fr.text('不只看【今天赚多少】', CX, 345, 66, 'serif_black', 'white', k, glow=0.3, stagger=(t - 73.3, 0.04, 0.45))
    # ---- B 一生的收入
    kb = a * win(t, 76.0, 82.2, 0.45, 0.4)
    if kb > 0.01:
        life_chart(fr, t, kb)
    k = a * cw('ha_life', t, 0.4, 0.4)
    fr.text('人们按【一辈子的收入】，', CX, 1265, 58, 'serif_bold', 'white', k, glow=0.25, stagger=(t - 76.0, 0.035, 0.4))
    fr.text('安排今天的消费', CX, 1350, 62, 'serif_black', 'white', k, glow=0.3, stagger=(t - 76.3, 0.045, 0.45))
    # ---- C 同样月入一万
    kc = a * win(t, 82.0, 88.2, 0.4, 0.4)
    if kc > 0.01:
        two_people(fr, t, kc)
    # ---- D 坏消息还没发生
    kd = a * win(t, 88.0, 94.0, 0.6, 0.3)
    if kd > 0.01:
        news_wave(fr, t, kd)


def life_chart(fr, t, k):
    fr.text('永久收入  ×  理性预期', CX, 395, 32, 'sans_bold', 'gold', k, track=0.12, glow=0.3)
    fr.line((AX0, AY0), (AX1 + 10, AY0), GREY, k * 0.55, 2)
    fr.text('年龄', AX1, AY0 + 40, 30, 'sans_med', 'grey', k, anchor='r', glow=0)
    for age in (20, 40, 60, 80):
        x, _ = a2s(age, 0)
        fr.text(str(age), x, AY0 + 40, 28, 'inter_med', 'dim', k, glow=0)
    draw = cl((t - 76.2) / 2.0)
    ages = np.linspace(20, 85, 200)
    shock = ss((t - 80.0) / 0.9)                 # 预期未来收入下降
    today = 35.0
    fut = ages > today
    inc = income(ages) * np.where(fut, 1 - 0.28 * shock * ss((ages - today) / 14), 1.0)
    con = consumption(ages) - 0.08 * shock * ss((ages - today + 3) / 5)
    m = max(2, int(len(ages) * draw))
    xi, yi = a2s(ages[:m], inc[:m])
    xc, yc = a2s(ages[:m], con[:m])
    # 区域填充：借 / 存 / 花积蓄
    fk = k * cl((t - 78.3) / 0.6)
    if fk > 0.01:
        for sel, col in (((ages < 28.5), GOLD), ((ages >= 28.5) & (ages < 61.5), ICE), ((ages >= 61.5), GOLD)):
            idx = np.where(sel)[0]
            xa, ya = a2s(ages[idx], inc[idx])
            xb, yb = a2s(ages[idx], con[idx])
            poly = list(zip(xa, ya)) + list(zip(xb[::-1], yb[::-1]))
            fr.fill(poly, col * 0.16, fk)
        lab = [(23.5, '借', 'gold'), (46, '存', 'ice'), (73, '花积蓄', 'gold')]
        for age, s, base in lab:
            x, y = a2s(age, (income(age) + consumption(age)) / 2)
            fr.text(s, x, y + (40 if s == '存' else 0), 38, 'sans_bold', base, fk, glow=0.2)
    fr.stroke(list(zip(xi, yi)), GOLD, k, 4, glow=1.0)
    fr.stroke(list(zip(xc, yc)), WHITE, k, 3, glow=0.6)
    if draw > 0.98:
        x, y = a2s(84, inc[-1])
        fr.text('收入', x - 10, y - 34, 32, 'sans_bold', 'gold', k, anchor='r', glow=0.1)
        x, y = a2s(84, con[-1])
        fr.text('消费', x - 10, y - 34, 32, 'sans_bold', 'white', k, anchor='r', glow=0.1)
    # 「今天」
    kt = k * cl((t - 79.2) / 0.5)
    if kt > 0.01:
        x, _ = a2s(today, 0)
        for yy in range(int(AY0 - AYH * 1.05), AY0, 22):
            fr.line((x, yy), (x, yy + 11), WHITE, kt * 0.6, 2)
        fr.text('今天', x, AY0 - AYH * 1.05 - 30, 34, 'serif_bold', 'white', kt, glow=0.2)
        ks = k * cl((t - 80.3) / 0.4)
        if ks > 0.01:
            _, yc0 = a2s(today, consumption(today) - 0.08 * shock)
            fr.text('↓', x + 34, yc0 + 6, 54, 'inter_bold', 'coral', ks, glow=0.4)
            chip(fr, '预期未来收入↓  →  今天就少花', CX, 478, ks, CORAL, 36, base='coral')


def two_people(fr, t, k):
    fr.text('同样月入一万', CX, 270, 84, 'serif_black', 'white', k, glow=0.3, stagger=(t - 82.0, 0.06, 0.45))
    for j, (x, base, col, lab, spend, save) in enumerate(((290, 'gold', GOLD, '相信明天更好', 0.8, 0.2),
                                                          (790, 'ice', ICE, '担心明天失业', 0.55, 0.45))):
        kk = k * eo((t - 82.4 - j * 0.25) / 0.5)
        # 卡片：他心里「预期的未来收入」
        cx0, cy0, cw_, ch_ = x - 215, 345, 430, 175
        fr.card(cx0, cy0, cx0 + cw_, cy0 + ch_, 22, kk, tint=col, border=col, border_a=0.5, fill_a=0.05, blur=8)
        fr.text('预期的未来收入', cx0 + 24, cy0 + 32, 28, 'sans_bold', base, kk, anchor='l', glow=0)
        us = np.linspace(0, 1, 60)
        draw = eo((t - 82.6 - j * 0.25) / 1.0)
        m = max(2, int(60 * draw))
        px = cx0 + 30 + (cw_ - 60) * us
        if j == 0:
            py = cy0 + 148 - 82 * us ** 0.8
            fr.stroke(list(zip(px[:m], py[:m])), GOLD, kk, 6, layer='B')
            fr.overlay_draw(lambda cv, px=px, py=py, m=m, kk=kk: cv.stroke(list(zip(px[:m], py[:m])), GOLD_HI, kk, 4.5))
            fr.glow((px[m - 1], py[m - 1]), 14, GOLD_HI, kk * 1.2)
        else:
            py = cy0 + 100 + 12 * np.sin(us * 9) + 40 * np.clip((us - 0.45) * 2, 0, 1) ** 1.5

            def dashes(cv, px=px, py=py, m=m, kk=kk):
                for i in range(0, m - 2, 4):
                    cv.line((px[i], py[i]), (px[i + 2], py[i + 2]), ICE_HI, kk, 4.5)
            fr.overlay_draw(dashes)
            fr.stroke(list(zip(px[:m], py[:m])), ICE, kk * 0.6, 6, layer='B')
            if draw > 0.9:
                fr.text('?', cx0 + cw_ - 34, cy0 + 70, 46, 'inter_bold', 'ice', kk * (0.6 + 0.4 * math.sin(t * 8)), glow=0.3)
        icon(fr, 'person', (x, 640), 170, col, kk, 4, glow=1.0)
        fr.text(lab, x, 790, 44, 'sans_bold', base, kk, glow=0.15)
        fr.text('收入 ¥10,000', x, 848, 32, 'sans_med', 'grey', kk, glow=0)
        g = eo((t - 83.5 - 0.2 * j) / 0.9)
        base_y, hmax = 1170, 290
        for i, (v, c2, nm) in enumerate(((spend, col, '消费'), (save, ICE if j == 0 else ICE_HI, '储蓄'))):
            bx = x - 70 + i * 140
            hh = hmax * v * g
            bar_glass(fr, bx - 48, base_y - hh, bx + 48, base_y, GOLD if i == 0 else ICE, kk, 2)
            fr.text(nm, bx, base_y + 36, 30, 'sans_med', 'grey', kk, glow=0)
    k2 = k * cw('ha_diff', t, 0.35, 0.3)
    fr.text('今天的消费，【完全不同】', CX, 1290, 64, 'serif_black', 'white', k2, glow=0.3, stagger=(t - 85.4, 0.045, 0.4))
    footnote(fr, '示意：收入相同，对未来的预期不同', k)


_VR = np.random.default_rng(12)
VOTE_IDX = _VR.choice(FIELD.n, 700, replace=False)
VOTE_T = 91.6 + _VR.random(700) * 1.6


def news_wave(fr, t, k):
    cam = H_FIELD_CAM(t)
    z = FIELD.P[:, 2]
    front = 48 - (t - 88.4) / 2.4 * 100          # 波前从远处（明天）向近处（今天）推进
    passed = ss((z - front) / 6)                 # 1 = 已被坏消息波及
    warm = 0.92 - 0.8 * passed
    bright = 1.0 - 0.45 * passed
    res = FIELD.draw(fr, cam, t, k, warm=warm, bright=bright)
    hx, hy, _, _ = cam.project([[0, 0, 60]])
    hx, hy = float(hx[0]), float(hy[0])
    kn = k * win(t, 88.2, 90.5, 0.1, 0.8)
    fr.glow((hx, hy), 70, CORAL, kn * 1.2)
    fr.glow((hx, hy), 250, CORAL, kn * 0.25)
    if front > -48:
        P = np.c_[np.linspace(-48, 48, 80), np.zeros(80), np.full(80, front)]
        x, y, zz, s = cam.project(P)
        ok = zz > 0.5
        fr.stroke(list(zip(x[ok], y[ok])), ICE_HI, k * 0.6 * kn, 2, glow=1.4)
    k1 = k * cw('ha_news', t, 0.4, 0.35)
    fr.text('坏消息还没发生，', CX, 250, 60, 'serif_bold', 'white', k1, glow=0.2, stagger=(t - 88.2, 0.04, 0.4))
    fr.text('今天的消费，〔已经先变了〕', CX, 345, 66, 'serif_black', 'white', k1, glow=0.3, stagger=(t - 88.5, 0.04, 0.45))
    # 投票：光点升向地平线
    if t > 91.4 and res is not None:
        x, y, zz, s, ok = res
        dt = np.clip((t - VOTE_T) / 1.4, 0, 1)
        sel = VOTE_IDX[(dt > 0) & ok[VOTE_IDX]]
        dts = dt[(dt > 0) & ok[VOTE_IDX]]
        px = x[sel] * (1 - eo(dts)) + hx * eo(dts)
        py = y[sel] * (1 - eo(dts)) + (hy - 10) * eo(dts)
        col = np.where(passed[sel, None] > 0.5, ICE_HI[None], GOLD_HI[None])
        fr.dots(px, py, 1.6, col, k * np.sin(np.pi * dts) * 1.2)
        fr.splat(px, py, col, k * np.sin(np.pi * dts) * 2.5, layer='B')
        fr.glow((hx, hy), 120, GOLD, k * 0.3 * cl((t - 92.2) / 1.0))
    k2 = k * cw('ha_vote', t, 0.35, 0.3)
    fr.text('消费，是对【未来】投出的一票', CX, 300, 64, 'serif_black', 'white', k2, glow=0.35, stagger=(t - 91.5, 0.04, 0.4))


# ================================================================ 伍德福德 94–116
@scene(94.0, 116.0, 0.3, 0.0)
def sc_woodford(fr, t, a):
    lt = t - 94.0
    fr.flash = max(fr.flash, 0.3 * math.exp(-lt / 0.1) * a)
    draw_dust(fr, t, a * 0.5)
    name_card(fr, t, 94.0, 98.2, 'woodford', 'MICHAEL WOODFORD', '迈克尔·伍德福德 · 哥伦比亚大学', '《利息与价格》· 2003', a)
    k = a * cw('wo_q', t, 0.4, 0.4)
    fr.text('企业，也【活在未来】', CX, 300, 72, 'serif_black', 'white', k, glow=0.3, stagger=(t - 95.0, 0.05, 0.45))
    kp = a * win(t, 98.0, 104.2, 0.45, 0.4)
    if kp > 0.01:
        price_scene(fr, t, kp)
    kf = a * win(t, 104.0, 108.2, 0.4, 0.4)
    if kf > 0.01:
        factory_scene(fr, t, kf)
    kc = a * win(t, 108.0, 112.2, 0.4, 0.4)
    if kc > 0.01:
        cbank_scene(fr, t, kc)
    kd = a * win(t, 112.0, 116.0, 0.3, 0.15)
    if kd > 0.01:
        draghi_scene(fr, t, kd)
    fr.zoom = 1 + 0.07 * ei((t - 114.8) / 1.2)


MONTHS = ['1月', '2月', '3月', '4月', '5月', '6月']


def price_scene(fr, t, k):
    # 日历
    for i, m in enumerate(MONTHS):
        on = cl((t - 99.0 - i * 0.5) / 0.15)
        x = 165 + i * 150
        fr.card(x - 62, 410, x + 62, 500, 14, k, tint=GOLD if on else GREY, border=GOLD if on else GREY,
                border_a=0.3 + 0.5 * on, fill_a=0.05 + 0.08 * on, blur=8)
        fr.text(m, x, 455, 36, 'sans_bold', 'gold' if on > 0.5 else 'dim', k, glow=0.1 * on)
    # 价签
    c = (CX, 720)
    ang = -0.08 + 0.015 * math.sin(t * 1.3)

    def rot(px, py):
        return (c[0] + px * math.cos(ang) - py * math.sin(ang), c[1] + px * math.sin(ang) + py * math.cos(ang))
    tag = [rot(-250, -140), rot(170, -140), rot(270, 0), rot(170, 140), rot(-250, 140)]
    fr.stroke(tag, GOLD, k, 3.5, closed=True, glow=1.0)
    fr.fill(tag, GOLD * 0.07, k)
    fr.circle(rot(190, 0), 16, GOLD, k, 3, glow=0.8)
    fr.text('¥18', c[0] - 40, c[1] + 6, 170, 'inter_xbold', 'gold', k, glow=0.35)
    fr.text('一碗面', c[0] - 40, c[1] - 112, 30, 'sans_med', 'grey', k, glow=0)
    icon(fr, 'lock', rot(-205, -95), 56, GOLD_HI, k, 3, glow=0.8)
    # 未来的不确定性扇面
    x0, y0 = 220, 1040
    fr.line((x0, y0), (900, y0), GREY, k * 0.4, 2)
    fr.text('今天', x0, y0 + 36, 28, 'sans_med', 'grey', k, glow=0)
    fr.text('半年后', 900, y0 + 36, 28, 'sans_med', 'grey', k, glow=0)
    us = np.linspace(0, 1, 40)
    for j, sp in enumerate(np.linspace(-1, 1, 7)):
        py = y0 - 20 - 110 * us * sp * cl((t - 99.5) / 1.2) - 15 * np.sin(us * 6 + j)
        px = x0 + 680 * us
        fr.stroke(list(zip(px, py)), ICE if sp < 0 else GOLD, k * 0.45, 2, glow=0.6)
    fr.text('成本？  需求？  通胀？', 600, 900, 34, 'sans_bold', 'white', k * cl((t - 100.0) / 0.5), glow=0.1)
    k2 = k * cw('wo_price', t, 0.4, 0.35)
    fr.text('价格不会天天改，', CX, 1250, 58, 'serif_bold', 'white', k2, glow=0.2, stagger=(t - 98.0, 0.04, 0.4))
    fr.text('定价时就要预判【未来的成本与需求】', CX, 1340, 54, 'serif_black', 'white', k2, glow=0.3,
            stagger=(t - 98.3, 0.03, 0.4))


_FR = np.random.default_rng(14)
WIN_POS = [(x, y) for y in (0, 1) for x in range(6)]
WIN_OFF = _FR.random(len(WIN_POS)) * 0.9


def factory_scene(fr, t, k):
    c = (CX, 700)
    s = 520
    icon(fr, 'factory', c, s, ICE_HI, k, 4, glow=1.0)
    dim = ss((t - 105.6) / 1.2)
    for i, (gx, gy) in enumerate(WIN_POS):
        x = c[0] - 0.42 * s + gx * 0.14 * s
        y = c[1] + 0.08 * s + gy * 0.15 * s
        on = 1 - cl((dim * 1.4 - WIN_OFF[i]) / 0.3)
        fr.rrect_fill(x - 22, y - 18, x + 22, y + 18, 4, GOLD * (0.2 + 0.8 * on), k, glow=0.8 * on)
    # 烟囱的烟
    r = np.random.default_rng(3)
    n = 120
    ph = (r.random(n) + (t - 104) * 0.3) % 1.0
    xs = c[0] + 0.43 * s + ph * 80 + r.normal(0, 14, n) * ph
    ys = c[1] - 0.55 * s - ph * 260
    fr.splat(xs, ys, GREY, k * (1 - ph) * 0.5 * (1 - 0.6 * dim), layer='B')
    k1 = k * cw('wo_invest', t, 0.4, 0.35)
    fr.text('建厂、招人、扩产，', CX, 270, 60, 'serif_bold', 'white', k1, glow=0.2, stagger=(t - 104.0, 0.04, 0.4))
    fr.text('也都【押注未来】', CX, 365, 66, 'serif_black', 'white', k1, glow=0.3, stagger=(t - 104.3, 0.05, 0.45))
    kc = k * cl((t - 105.4) / 0.4)
    chip(fr, '2026年1—8月  民间投资 −10.1%', CX, 1110, kc, CORAL, 40, base='coral')
    fr.text('利率再低，看不到订单的工厂也不会扩建', CX, 1215, 40, 'sans_med', 'grey', kc, glow=0)
    footnote(fr, '来源：国家统计局 全国固定资产投资数据', kc)


_TR = np.random.default_rng(15)
THREAD_IDX = _TR.choice(FIELD.n, 320, replace=False)
THREAD_PH = _TR.random(320)


def cbank_scene(fr, t, k):
    k1 = k * cw('wo_cb', t, 0.4, 0.35)
    fr.text('央行真正撬动的，', CX, 250, 58, 'serif_bold', 'white', k1, glow=0.2, stagger=(t - 108.0, 0.04, 0.4))
    fr.text('是人们对【未来】的预期', CX, 345, 66, 'serif_black', 'white', k1, glow=0.3, stagger=(t - 108.3, 0.045, 0.45))
    cam = Cam((0, 30, -30), (0, 0, 8), fov=60, cy=H * 0.52)
    lt = t - 108.0
    ring = 60 * max(lt, 0)
    d = np.hypot(FIELD.P[:, 0], FIELD.P[:, 2])
    wave = np.exp(-((d - ring) / 4.0) ** 2) * (lt > 0)
    res = FIELD.draw(fr, cam, t, k * 0.8, warm=np.full(FIELD.n, 0.8), bright=0.8 + 1.2 * wave)
    c = (CX, 640)
    R = 150
    # 丝线
    if res is not None:
        x, y, z, s, ok = res
        sel = THREAD_IDX[ok[THREAD_IDX]]
        ph = THREAD_PH[ok[THREAD_IDX]]
        for i, j in enumerate(sel[:150]):
            al = k * (0.07 + 0.25 * math.exp(-((lt * 1.6 - ph[i]) % 1.6) * 3) * (lt > 0))
            fr.line((c[0], c[1] + R * 0.6), (x[j], y[j]), GOLD, al, 1)
    # 旋钮
    fr.disc(c, R + 6, C(10, 14, 26), k)
    fr.circle(c, R, GOLD, k, 3, glow=1.0)
    fr.circle(c, R * 0.78, GOLD, k * 0.4, 1.5)
    for i in range(41):
        q = math.radians(140 + i * 6.5)
        r0 = R * (0.86 if i % 5 else 0.8)
        fr.line((c[0] + r0 * math.cos(q), c[1] + r0 * math.sin(q)),
                (c[0] + R * 0.95 * math.cos(q), c[1] + R * 0.95 * math.sin(q)), GOLD, k * 0.7, 2)
    q = math.radians(lerp(320, 250, eback(lt / 0.5, 2.0)))
    fr.line(c, (c[0] + R * 0.72 * math.cos(q), c[1] + R * 0.72 * math.sin(q)), GOLD_HI, k, 5, glow=1.5)
    fr.disc(c, 12, GOLD_HI, k, glow=1.0)
    fr.text('利率', CX, c[1] + 70, 40, 'serif_bold', 'gold', k, glow=0.2)
    fr.circle(c, R + ring * 6, GOLD_HI, k * max(0, 0.8 - lt * 0.5) * (lt > 0), 3, glow=1.0)
    chip(fr, '货币政策 ≈ 管理预期', CX, 850, k * cl((t - 109.0) / 0.4), GOLD, 36)
    chip(fr, '前瞻指引：提前讲清未来的利率路径', CX, 935, k * cl((t - 109.8) / 0.4), GOLD, 32, fname='sans_med')


YIELD = [5.4, 5.1, 5.2, 5.8, 6.2, 6.6, 7.4, 6.6, 5.9, 5.6, 5.7, 5.3]


def draghi_scene(fr, t, k):
    chip(fr, '2012 · 欧债危机', CX, 260, k, GREY, 34, base='white')
    p = eo((t - 112.1) / 0.5)
    fr.text('「不惜一切代价」', CX, 440, 100, 'serif_black', 'white', k * p, scale=1.08 - 0.08 * p, glow=0.4)
    fr.text('—— 欧洲央行行长 德拉吉，2012年7月', CX, 545, 32, 'sans_reg', 'grey', k * cl((t - 112.6) / 0.4), glow=0)
    x0, x1, yb, yt = 170, 910, 1080, 720
    fr.line((x0, yb), (x1, yb), GREY, k * 0.4, 2)
    y7 = yb - (7.0 - 4.8) / (7.6 - 4.8) * (yb - yt)
    for xx in range(x0, x1, 24):
        fr.line((xx, y7), (xx + 12, y7), CORAL, k * 0.5, 2)
    fr.text('7%', x0 - 16, y7, 30, 'inter_bold', 'coral', k, anchor='r', glow=0)
    xs = np.linspace(x0 + 20, x1 - 20, 12)
    ys = yb - (np.array(YIELD) - 4.8) / (7.6 - 4.8) * (yb - yt)
    m = 6 + cl((t - 113.0) / 1.6) * 5
    j = int(m)
    pts = list(zip(xs[:j + 1], ys[:j + 1]))
    if j < 11:
        pts.append((lerp(xs[j], xs[j + 1], m - j), lerp(ys[j], ys[j + 1], m - j)))
    col_pts = pts
    fr.stroke(col_pts, ICE, k, 4, glow=1.2)
    fr.glow(col_pts[-1], 14, ICE_HI, k)
    fr.text('讲话', xs[6], ys[6] - 44, 30, 'sans_bold', 'gold', k, glow=0.2)
    fr.disc((xs[6], ys[6]), 9, GOLD_HI, k, glow=1.0)
    fr.text('西班牙10年期国债收益率 · 2012年走势示意', CX, yb + 42, 28, 'sans_reg', 'dim', k, glow=0)
    k2 = k * cw('wo_draghi2', t, 0.35, 0.2)
    fr.text('工具一次没用，【市场先平静了】', CX, 1260, 60, 'serif_black', 'white', k2, glow=0.3,
            stagger=(t - 113.4, 0.04, 0.4))
    footnote(fr, '欧洲央行 OMT（直接货币交易）计划 2012 年宣布，至今从未启用', k2)
