"""v2：02 诺奖（旧模型失灵 → 微观基础）→ 03 霍尔：家庭的预期（发现①花钱看一辈子；发现②消费只为意外而变）"""
import math

import numpy as np

from common import *          # noqa: F401,F403
from registry import scene
from timeline import CAP, HITS, SEC, T
from scenes_a import cw, two, chip, num_unit, rich, bar_glass
import portraits

CX = W / 2


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


# ================================================================ 旧模型失灵 → 微观基础 82–98
OX, OY = 190, 1040
XW, YH = 720, 500
PTS60 = [(0.08, 0.80), (0.16, 0.62), (0.25, 0.50), (0.34, 0.41), (0.43, 0.34), (0.53, 0.28), (0.63, 0.23),
         (0.74, 0.19), (0.86, 0.16)]
PTS70 = [(0.45, 0.62), (0.62, 0.72), (0.55, 0.85), (0.78, 0.70), (0.70, 0.93), (0.88, 0.84), (0.95, 0.97)]
_SR = np.random.default_rng(8)
SHARD_V = _SR.normal(0, 1, (40, 2)) * np.array([420, 340]) + np.array([0, -120])
SHARD_W = _SR.normal(0, 5, 40)
LAT_N = 84
LAT = np.array([(150 + (i % 14) * 60 + (30 if (i // 14) % 2 else 0), 1130 - (i // 14) * 52) for i in range(LAT_N)],
               np.float64)
LAT_KIND = _SR.random(LAT_N) < 0.25


def p2s(u, v):
    return OX + u * XW, OY - v * YH


def curve60(n=60):
    u = np.linspace(0.05, 0.92, n)
    v = np.clip(0.12 + 0.065 / (u + 0.02), 0, 1.0)
    return u, v


@scene(82.0, 98.0, 0.3, 0.4)
def sc_oldmodel(fr, t, a):
    t0 = SEC['oldmodel'][0]
    lt = t - t0
    draw_dust(fr, t, a * 0.5)
    brk = t - HITS['break70s']
    if 0 < brk < 1.2:
        sh = 14 * math.exp(-brk / 0.25)
        fr.cam = (sh * math.sin(brk * 70), sh * math.cos(brk * 53))
    k_chart = a * (1 - ss((t - (CAP['o_why'][0] + 1.4)) / 0.8))
    if k_chart > 0.01:
        fr.line((OX, OY), (OX + XW + 20, OY), GREY, k_chart * 0.6, 2)
        fr.line((OX, OY), (OX, OY - YH - 30), GREY, k_chart * 0.6, 2)
        fr.text('失业率 →', OX + XW, OY + 42, 32, 'sans_med', 'grey', k_chart, anchor='r', glow=0)
        fr.text('通胀率 ↑', OX + 10, OY - YH - 60, 32, 'sans_med', 'grey', k_chart, anchor='l', glow=0)
        for i, (u, v) in enumerate(PTS60):
            kk = k_chart * eo((lt - 0.4 - i * 0.24) / 0.25)
            x, y = p2s(u, v)
            fr.disc((x, y), 9, GOLD, kk, glow=0.8)
        u, v = curve60()
        xs, ys = p2s(u, v)
        if brk < 0:
            m = int(len(u) * cl((lt - 1.4) / 1.2))
            if m > 1:
                fr.stroke(list(zip(xs[:m], ys[:m])), GOLD_HI, k_chart * 0.9, 3, glow=1.0)
            kk = k_chart * cl((lt - 2.2) / 0.4)
            fr.text('通胀高一点，失业就低一点', OX + XW * 0.6, OY - YH * 0.55, 36, 'sans_bold', 'gold', kk, glow=0.2)
        else:
            seg = np.array_split(np.arange(len(u)), 20)
            for j, idx in enumerate(seg):
                d = SHARD_V[j] * brk + np.array([0, 700]) * brk ** 2
                ang = SHARD_W[j] * brk
                cx_, cy_ = xs[idx].mean(), ys[idx].mean()
                px = (xs[idx] - cx_) * math.cos(ang) - (ys[idx] - cy_) * math.sin(ang) + cx_ + d[0]
                py = (xs[idx] - cx_) * math.sin(ang) + (ys[idx] - cy_) * math.cos(ang) + cy_ + d[1]
                fr.stroke(list(zip(px, py)), GOLD_HI, k_chart * max(0, 1 - brk / 1.5), 3, glow=1.2)
            for i, (uu, vv) in enumerate(PTS70):
                kk = k_chart * eback((brk - i * 0.08) / 0.3)
                x, y = p2s(uu, vv)
                fr.disc((x, y), 11 * kk, CORAL, cl(kk), glow=1.2)
    k = a * cw('o_old', t, 0.35, 0.35)
    fr.text('过去的宏观模型，', CX, 270, 56, 'serif_bold', 'grey', k, stagger=(t - CAP['o_old'][0], 0.04, 0.4))
    fr.text('只看数字之间的统计规律', CX, 365, 64, 'serif_black', 'white', k, glow=0.25,
            stagger=(t - CAP['o_old'][0] - 0.25, 0.04, 0.4))
    k = a * cw('o_break', t, 0.2, 0.3)
    chip(fr, '1970年代：通胀与失业一起飙升，规律失灵', CX, 1170, k, CORAL, 38, base='coral')
    # 人会预判：碎片慢慢聚拢 → 家庭与企业的格点，托起宏观
    k = a * cw('o_why', t, 0.35, 0.35)
    fr.text('人会预判未来，', CX, 270, 58, 'serif_bold', 'white', k, glow=0.2, stagger=(t - CAP['o_why'][0], 0.04, 0.4))
    fr.text('规律就会【跟着变】', CX, 365, 66, 'serif_black', 'white', k, glow=0.3, stagger=(t - CAP['o_why'][0] - 0.25, 0.05, 0.45))
    t_r = CAP['o_why'][0] + 1.0
    kr = a * cl((t - t_r) / 0.6)
    if kr > 0.01:
        p = eio((t - t_r) / 2.4)
        r = np.random.default_rng(1)
        src = np.c_[r.uniform(100, 980, LAT_N), r.uniform(500, 1100, LAT_N)]
        P = src * (1 - p) + LAT * p
        for i in range(LAT_N):
            fr.disc(tuple(P[i]), 7, ICE if LAT_KIND[i] else GOLD, kr, glow=0.9)
        if p > 0.6:
            kl = kr * cl((p - 0.6) / 0.4)
            for i in range(LAT_N):
                j = i + 1
                if j < LAT_N and j % 14:
                    fr.line(tuple(P[i]), tuple(P[j]), GOLD, kl * 0.25, 1)
                if i + 14 < LAT_N:
                    fr.line(tuple(P[i]), tuple(P[i + 14]), GOLD, kl * 0.2, 1)
        kb = kr * eo((t - CAP['o_new'][0]) / 0.8)
        roof = [(170, 810), (540, 630), (910, 810)]
        fr.stroke(roof, GOLD_HI, kb, 3, closed=True, glow=1.0)
        fr.fill(roof, GOLD * 0.06, kb)
        fr.text('宏观经济', CX, 758, 48, 'serif_black', 'gold', kb, glow=0.4)
        for xx in np.linspace(230, 850, 8):
            fr.line((xx, 820), (xx, 870), GOLD, kb * 0.5, 2, glow=0.4)
        fr.line((150, 875), (930, 875), GOLD, kb * 0.7, 2, glow=0.6)
        fr.text('家庭', 150, 1195, 32, 'sans_bold', 'gold', kb, anchor='l', glow=0)
        fr.text('企业', 300, 1195, 32, 'sans_bold', 'ice', kb, anchor='l', glow=0)
        fr.disc((134, 1195), 8, GOLD, kb)
        fr.disc((284, 1195), 8, ICE, kb)
        kt = a * win(t, CAP['o_new'][0] + 1.0, SEC['oldmodel'][1] + 0.2, 0.5, 0.3)
        fr.text('微观基础  MICROFOUNDATIONS', CX, 560, 30, 'sans_bold', 'gold', kt, track=0.12, glow=0.3)
    k = a * cw('o_new', t, 0.4, 0.35)
    fr.text('他们从【每个家庭和企业】出发，', CX, 1285, 56, 'serif_bold', 'white', k, glow=0.25,
            stagger=(t - CAP['o_new'][0], 0.035, 0.4))
    fr.text('重建宏观模型', CX, 1375, 64, 'serif_black', 'white', k, glow=0.3, stagger=(t - CAP['o_new'][0] - 0.3, 0.05, 0.45))


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


# ================================================================ 03 霍尔 98–146
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


@scene(98.0, 146.0, 0.3, 0.3)
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
