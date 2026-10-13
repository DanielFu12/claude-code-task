"""v2：04 伍德福德（发现①今天的价格押注明天；发现②利率路径比这一次更重要；德拉吉；模型地基）
→ 05 回到中国（预期循环、降息为何不灵、推绳子、财政、霍尔的提醒）→ 06 真相 → 获奖者 → 品牌片尾"""
import math

import numpy as np

from common import *          # noqa: F401,F403
from registry import scene
from timeline import CAP, HITS, SEC, SHIMMER_T0, T
from scenes_a import cw, chip, rich, num_unit, bar_glass
from scenes_b import law_card, header, name_card
import portraits

CX = W / 2


def two_line(fr, key, t, y, s1=56, s2=64, l1=None, l2=None, gap=1.42):
    t0, t1, s = CAP[key]
    k = win(t, t0, t1, 0.35, 0.3)
    if k <= 0:
        return 0.0
    fr.text(l1, CX, y, s1, 'serif_bold', 'white', k, glow=0.2, stagger=(t - t0, 0.04, 0.4))
    fr.text(l2, CX, y + s2 * gap, s2, 'serif_black', 'white', k, glow=0.3, stagger=(t - t0 - 0.3, 0.045, 0.45))
    return k


# ================================================================ 04 伍德福德 180–236
@scene(*SEC['woodford'], 0.3, 0.0)
def sc_woodford(fr, t, a):
    t0 = SEC['woodford'][0]
    lt = t - t0
    fr.flash = max(fr.flash, 0.3 * math.exp(-lt / 0.1) * a)
    draw_dust(fr, t, a * 0.5)
    name_card(fr, t, t0, t0 + 6.2, 'woodford', 'MICHAEL WOODFORD', '迈克尔·伍德福德 · 哥伦比亚大学', '《利息与价格》· 2003', a)
    k = a * cw('w_q', t, 0.4, 0.4)
    fr.text('第二个问题：', CX, 250, 48, 'serif_bold', 'gold', k, glow=0.2, stagger=(t - CAP['w_q'][0], 0.05, 0.4))
    fr.text('企业和央行，又在看什么？', CX, 345, 66, 'serif_black', 'white', k, glow=0.3,
            stagger=(t - CAP['w_q'][0] - 0.3, 0.045, 0.45))
    # ---- 发现①
    law_card(fr, t, CAP['w_r1'][0], CAP['w_r1'][1] + 0.3, '伍德福德的发现 ①', '今天的价格，押注的是明天', a)
    kp = a * win(t, CAP['w_price'][0] - 0.2, CAP['w_self'][1] + 0.2, 0.45, 0.4)
    if kp > 0.01:
        header(fr, '① 今天的价格，押注的是明天', kp)
    kk = a * win(t, CAP['w_price'][0] - 0.2, CAP['w_price'][1] + 0.2, 0.45, 0.35)
    if kk > 0.01:
        price_scene(fr, t, kk)
    kk = a * win(t, CAP['w_self'][0] - 0.1, CAP['w_self'][1] + 0.2, 0.4, 0.4)
    if kk > 0.01:
        expect_split(fr, t, kk)
    # ---- 发现②
    t_r2 = CAP['w_r2'][0]
    law2_card(fr, t, t_r2, CAP['w_r2'][1] + 0.3, a)
    kr = a * win(t, CAP['w_loan'][0] - 0.3, CAP['w_path'][1] + 0.2, 0.45, 0.4)
    if kr > 0.01:
        header(fr, '② 利率的「路径」，比这一次更重要', kr)
        rate_path(fr, t, kr)
    km = a * win(t, CAP['w_manage'][0] - 0.1, CAP['w_manage'][1] + 0.2, 0.4, 0.4)
    if km > 0.01:
        cbank_scene(fr, t, km)
    # ---- 德拉吉
    kd = a * win(t, HITS['draghi'], CAP['w_calm'][1] + 0.2, 0.3, 0.4)
    if kd > 0.01:
        draghi_scene(fr, t, kd)
    # ---- 模型地基
    ks = a * win(t, HITS['synth'], CAP['w_synth'][1] + 0.3, 0.4, 0.4)
    if ks > 0.01:
        synth_scene(fr, t, ks)
    # ---- 问题
    kq = a * win(t, CAP['w_ask'][0], CAP['w_ask'][1] + 0.1, 0.4, 0.05)
    if kq > 0.01:
        p = eo((t - CAP['w_ask'][0]) / 0.6)
        fr.text('那么问题来了：', CX, 700, 54, 'serif_bold', 'gold', kq, glow=0.2, stagger=(t - CAP['w_ask'][0], 0.05, 0.4))
        fr.text('降息了，', CX, 830, 84, 'serif_black', 'white', kq * cl((t - CAP['w_ask'][0] - 0.6) / 0.3),
                scale=1.08 - 0.08 * p, glow=0.3)
        p2 = eo((t - CAP['w_ask'][0] - 1.2) / 0.6)
        fr.text('为什么大家还是【不敢花】？', CX, 960, 76, 'serif_black', 'white', kq * cl((t - CAP['w_ask'][0] - 1.2) / 0.3),
                scale=1.08 - 0.08 * p2, glow=0.4)
        fr.zoom = 1 + 0.06 * ei((t - (SEC['woodford'][1] - 1.2)) / 1.2)


def law2_card(fr, t, t0, t1, a):
    k = a * win(t, t0, t1, 0.45, 0.4)
    if k <= 0.01:
        return
    y = 760
    fr.card(80, y - 230, 1000, y + 230, 36, k, tint=GOLD, border=GOLD, border_a=0.75, fill_a=0.08, blur=16)
    fr.glow((CX, y), 360, GOLD, k * 0.10)
    fr.text('伍德福德的发现 ②', CX, y - 135, 38, 'sans_bold', 'gold', k * eo((t - t0) / 0.6), track=0.16, glow=0.3)
    fr.text('要紧的不是今天的利率，', CX, y, 60, 'serif_bold', 'white', k, glow=0.3, stagger=(t - t0 - 0.25, 0.05, 0.45))
    fr.text('而是【未来很多年】的利率', CX, y + 100, 66, 'serif_black', 'white', k, glow=0.4,
            stagger=(t - t0 - 0.7, 0.05, 0.45))


MONTHS = ['1月', '2月', '3月', '4月', '5月', '6月']


def price_scene(fr, t, k):
    t0 = CAP['w_price'][0]
    for i, m in enumerate(MONTHS):
        on = cl((t - t0 - 0.4 - i * 0.5) / 0.15)
        x = 165 + i * 150
        fr.card(x - 62, 380, x + 62, 470, 14, k, tint=GOLD if on else GREY, border=GOLD if on else GREY,
                border_a=0.3 + 0.5 * on, fill_a=0.05 + 0.08 * on, blur=8)
        fr.text(m, x, 425, 36, 'sans_bold', 'gold' if on > 0.5 else 'dim', k, glow=0.1 * on)
    c = (CX, 690)
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
    x0, y0 = 220, 1010
    fr.line((x0, y0), (900, y0), GREY, k * 0.4, 2)
    fr.text('今天', x0, y0 + 36, 28, 'sans_med', 'grey', k, glow=0)
    fr.text('半年后', 900, y0 + 36, 28, 'sans_med', 'grey', k, glow=0)
    us = np.linspace(0, 1, 40)
    for j, sp in enumerate(np.linspace(-1, 1, 7)):
        py = y0 - 20 - 110 * us * sp * cl((t - t0 - 0.8) / 1.2) - 15 * np.sin(us * 6 + j)
        fr.stroke(list(zip(x0 + 680 * us, py)), ICE if sp < 0 else GOLD, k * 0.45, 2, glow=0.6)
    fr.text('成本？  需求？  物价？', 600, 870, 34, 'sans_bold', 'white', k * cl((t - t0 - 1.2) / 0.5), glow=0.1)
    k2 = k * cw('w_price', t, 0.4, 0.35)
    fr.text('价格不能天天改，', CX, 1250, 58, 'serif_bold', 'white', k2, glow=0.2, stagger=(t - t0, 0.04, 0.4))
    fr.text('每次定价都要【预判未来】', CX, 1345, 64, 'serif_black', 'white', k2, glow=0.3, stagger=(t - t0 - 0.3, 0.04, 0.45))


def expect_split(fr, t, k):
    t0 = CAP['w_self'][0]
    for j, (x, col, base, top, act, arrow) in enumerate(((290, GOLD, 'gold', '预期会涨价', '现在就涨价', 1),
                                                         (790, ICE, 'ice', '预期会降价', '不敢涨、不敢扩产', -1))):
        kk = k * eo((t - t0 - 0.2 - 0.35 * j) / 0.5)
        fr.card(x - 230, 420, x + 230, 1060, 30, kk, tint=col, border=col, border_a=0.6, fill_a=0.06, blur=12)
        fr.text('如果大家', x, 500, 34, 'sans_med', 'grey', kk, glow=0)
        fr.text(top, x, 570, 50, 'serif_black', base, kk, glow=0.25)
        p = eo((t - t0 - 0.7 - 0.35 * j) / 0.6)
        ya, yb = (900, 900 - 230 * p) if arrow > 0 else (680, 680 + 230 * p)
        fr.line((x, ya), (x, yb), col, kk, 10, glow=1.0)
        if p > 0.85:
            for s in (-1, 1):
                fr.line((x, yb), (x + s * 44, yb + 44 * arrow), col, kk, 10, glow=1.0)
        fr.text('企业', x - 120, 790, 34, 'sans_med', 'grey', kk * cl(p * 2), glow=0)
        fr.text(act, x, 990, 40 if len(act) > 6 else 46, 'serif_bold', 'white', kk * cl((p - 0.5) * 2), glow=0.15)
    k2 = k * cw('w_self', t, 0.35, 0.3)
    fr.text('物价，也会被预期', CX, 1250, 58, 'serif_bold', 'white', k2, glow=0.2, stagger=(t - t0, 0.04, 0.4))
    fr.text('【「自我实现」】', CX, 1345, 70, 'serif_black', 'white', k2, glow=0.35, stagger=(t - t0 - 0.3, 0.06, 0.45))


RP_X0, RP_X1, RP_YB = 150, 940, 1050


def rate_path(fr, t, k):
    """利率路径示意：降一次就回去 vs 承诺长期偏低 —— 阴影面积 = 未来多年里少付的利息"""
    tA = CAP['w_loan'][0]
    tB = HITS['pathB']
    y_of = lambda r: RP_YB - (r - 2.4) / (4.0 - 2.4) * 460
    fr.line((RP_X0, RP_YB), (RP_X1, RP_YB), GREY, k * 0.5, 2)
    fr.text('利率', RP_X0, y_of(4.0) - 20, 32, 'sans_bold', 'white', k, anchor='l', glow=0)
    for yr, lb in ((0, '今天'), (5, '5 年后'), (10, '10 年后')):
        x = RP_X0 + yr / 10 * (RP_X1 - RP_X0)
        fr.text(lb, x, RP_YB + 42, 28, 'sans_med', 'grey', k, anchor='l' if yr == 0 else ('r' if yr == 10 else 'c'), glow=0)
    years = np.linspace(0, 10, 200)
    xs = RP_X0 + years / 10 * (RP_X1 - RP_X0)
    base = np.full_like(years, 3.5)
    fr.stroke(list(zip(xs, y_of(base))), GREY, k * 0.7, 3)
    fr.text('原来的利率', RP_X1, y_of(3.5) - 40, 28, 'sans_med', 'grey', k, anchor='r', glow=0)
    pa = eo((t - tA - 0.3) / 1.2)
    pathA = 3.5 - 0.5 * np.exp(-((years - 0.6) / 0.7) ** 2)
    pb = eo((t - tB) / 1.2)
    pathB = 3.5 - 0.5 * ss(years / 0.4)
    kA = k * (1 - 0.65 * pb)
    if pa > 0.01:
        m = max(2, int(200 * pa))
        ya = y_of(pathA)
        fr.fill(list(zip(xs[:m], ya[:m])) + list(zip(xs[:m][::-1], y_of(base)[:m][::-1])), GOLD * 0.25, kA)
        fr.stroke(list(zip(xs[:m], ya[:m])), GOLD, kA, 4, glow=1.0)
        chip(fr, '降一次就回去：长期成本几乎不变', CX, 520, kA * cl((t - tA - 1.5) / 0.4), GOLD, 34, fname='sans_bold')
    if pb > 0.01:
        m = max(2, int(200 * pb))
        yb = y_of(pathB)
        fr.fill(list(zip(xs[:m], yb[:m])) + list(zip(xs[:m][::-1], y_of(base)[:m][::-1])), ICE * 0.28, k)
        fr.stroke(list(zip(xs[:m], yb[:m])), ICE_HI, k, 4.5, glow=1.2)
        chip(fr, '相信会长期偏低：长期成本明显下降', CX, 520, k * cl((t - tB - 1.0) / 0.4), ICE, 34, fname='sans_bold',
             base='ice')
    footnote(fr, '示意：阴影面积 ≈ 未来多年里少付的利息', k)
    for key, l1, l2 in (('w_loan', '房贷要还 30 年，', '工厂要用 10 年'), ('w_path', '人们在意的，', '是【整条利率路径】')):
        two_line(fr, key, t, 1250, l1=l1, l2=l2)


_TR = np.random.default_rng(15)
THREAD_IDX = _TR.choice(FIELD.n, 320, replace=False)
THREAD_PH = _TR.random(320)


def cbank_scene(fr, t, k):
    t0 = CAP['w_manage'][0]
    lt = t - t0
    cam = Cam((0, 30, -30), (0, 0, 8), fov=60, cy=H * 0.60)
    ring = 60 * max(lt, 0)
    d = np.hypot(FIELD.P[:, 0], FIELD.P[:, 2])
    wave = np.exp(-((d - ring) / 4.0) ** 2) * (lt > 0)
    res = FIELD.draw(fr, cam, t, k * 0.8, warm=np.full(FIELD.n, 0.8), bright=0.8 + 1.2 * wave)
    c = (CX, 690)
    R = 140
    if res is not None:
        x, y, z, s, ok = res
        sel = THREAD_IDX[ok[THREAD_IDX]]
        ph = THREAD_PH[ok[THREAD_IDX]]
        for i, j in enumerate(sel[:150]):
            al = k * (0.07 + 0.25 * math.exp(-((lt * 1.6 - ph[i]) % 1.6) * 3) * (lt > 0))
            fr.line((c[0], c[1] + R * 0.6), (x[j], y[j]), GOLD, al, 1)
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
    fr.text('利率', CX, c[1] + 66, 38, 'serif_bold', 'gold', k, glow=0.2)
    fr.circle(c, R + ring * 6, GOLD_HI, k * max(0, 0.8 - lt * 0.5) * (lt > 0), 3, glow=1.0)
    chip(fr, '前瞻指引：提前讲清未来的利率路径', CX, 905, k * cl((lt - 0.8) / 0.4), GOLD, 34, fname='sans_med')
    two_line(fr, 'w_manage', t, 300, l1='所以央行真正要做的，', l2='是【管理预期】', s2=72)


YIELD = [5.4, 5.1, 5.2, 5.8, 6.2, 6.6, 7.4, 6.6, 5.9, 5.6, 5.7, 5.3]


def draghi_scene(fr, t, k):
    t0 = HITS['draghi']
    chip(fr, '2012 · 欧债危机', CX, 260, k, GREY, 36, base='white')
    p = eo((t - t0 - 0.1) / 0.5)
    fr.text('「不惜一切代价」', CX, 440, 100, 'serif_black', 'white', k * p, scale=1.08 - 0.08 * p, glow=0.4)
    fr.text('—— 欧洲央行行长 德拉吉，2012年7月', CX, 545, 32, 'sans_reg', 'grey', k * cl((t - t0 - 0.6) / 0.4), glow=0)
    x0, x1, yb, yt = 170, 910, 1060, 700
    fr.line((x0, yb), (x1, yb), GREY, k * 0.4, 2)
    y7 = yb - (7.0 - 4.8) / (7.6 - 4.8) * (yb - yt)
    for xx in range(x0, x1, 24):
        fr.line((xx, y7), (xx + 12, y7), CORAL, k * 0.5, 2)
    fr.text('7%', x0 - 16, y7, 30, 'inter_bold', 'coral', k, anchor='r', glow=0)
    xs = np.linspace(x0 + 20, x1 - 20, 12)
    ys = yb - (np.array(YIELD) - 4.8) / (7.6 - 4.8) * (yb - yt)
    m = 6 + cl((t - t0 - 1.5) / 3.0) * 5
    j = int(m)
    pts = list(zip(xs[:j + 1], ys[:j + 1]))
    if j < 11:
        pts.append((lerp(xs[j], xs[j + 1], m - j), lerp(ys[j], ys[j + 1], m - j)))
    fr.stroke(pts, ICE, k, 4, glow=1.2)
    fr.glow(pts[-1], 14, ICE_HI, k)
    fr.text('讲话', xs[6], ys[6] - 44, 30, 'sans_bold', 'gold', k, glow=0.2)
    fr.disc((xs[6], ys[6]), 9, GOLD_HI, k, glow=1.0)
    fr.text('西班牙10年期国债收益率 · 2012年走势示意', CX, yb + 42, 28, 'sans_reg', 'dim', k, glow=0)
    k2 = k * cw('w_calm', t, 0.35, 0.3)
    fr.text('一句可信的承诺，', CX, 1250, 58, 'serif_bold', 'white', k2, glow=0.2, stagger=(t - CAP['w_calm'][0], 0.04, 0.4))
    fr.text('【市场就平静了】', CX, 1345, 66, 'serif_black', 'white', k2, glow=0.3, stagger=(t - CAP['w_calm'][0] - 0.3, 0.05, 0.45))
    footnote(fr, '欧洲央行 OMT（直接货币交易）计划 2012 年宣布，至今从未启用', k2, y=1450)


BLOCKS = [('家庭', '霍尔：看一辈子、为意外而变', GOLD, 'gold'), ('企业', '伍德福德：价格押注明天', ICE, 'ice'),
          ('央行', '伍德福德：管理预期', BRANDBLUE, 'white')]


def synth_scene(fr, t, k):
    t0 = HITS['synth']
    p_roof = eo((t - t0 - 1.4) / 0.8)
    roof = [(150, 600), (540, 430), (930, 600)]
    fr.stroke(roof, GOLD_HI, k * p_roof, 3, closed=True, glow=1.0)
    fr.fill(roof, GOLD * 0.06, k * p_roof)
    fr.text('宏观经济', CX, 548, 50, 'serif_black', 'gold', k * p_roof, glow=0.4)
    for i, (nm, sub, col, base) in enumerate(BLOCKS):
        p = eback((t - t0 - 0.2 - 0.35 * i) / 0.6, 1.4)
        y = 700 + i * 150 + (1 - cl(p)) * 120
        kk = k * cl(p)
        fr.card(150, y, 930, y + 120, 24, kk, tint=col, border=col, border_a=0.7, fill_a=0.08, blur=10)
        fr.text(nm, 200, y + 60, 50, 'serif_black', base, kk, anchor='l', glow=0.2)
        fr.text(sub, 880, y + 60, 32, 'sans_med', 'white', kk, anchor='r', glow=0)
    fr.line((150, 668), (930, 668), GOLD, k * p_roof * 0.7, 2, glow=0.6)
    kc = k * cw('w_synth', t, 0.35, 0.3)
    fr.text('这成了今天各国央行', CX, 1250, 58, 'serif_bold', 'white', kc, glow=0.2, stagger=(t - CAP['w_synth'][0], 0.04, 0.4))
    fr.text('决策模型的【地基】', CX, 1345, 66, 'serif_black', 'white', kc, glow=0.3, stagger=(t - CAP['w_synth'][0] - 0.3, 0.05, 0.45))


# ================================================================ 05 回到中国 236–292
M0 = SEC['machine'][0]
NODES = ['预期', '消费·储蓄', '定价·投资', '需求·物价', '央行·政策']
NODE_T = [M0 + 0.5, M0 + 1.0, M0 + 1.5, M0 + 2.0, M0 + 2.5]
RC = np.array([CX, 790.0])
RR = 272.0
TILT = 0.42
T_GOOD = CAP['m_good'][0]
T_BAD = CAP['m_bad'][0]
T_RING_END = CAP['m_why'][0] - 0.2


def ring_xy(theta, rr=RR, c=RC, tilt=TILT):
    th = np.asarray(theta, np.float64)
    return c[0] + rr * np.cos(th), c[1] + rr * np.sin(th) * math.cos(tilt), (np.sin(th) + 1) / 2


def node_theta(i):
    return -np.pi / 2 + i * 2 * np.pi / 5


_RP = np.random.default_rng(23)
FLOW_N = 1100
FLOW_S = _RP.random(FLOW_N)
FLOW_O = _RP.normal(0, 7, FLOW_N)
FLOW_V = 0.8 + 0.4 * _RP.random(FLOW_N)


def flow_disp(t):
    pts = [(M0 + 3.0, 0.0), (T_GOOD, 0.10), (T_BAD, 0.22), (T_BAD + 0.6, -0.06), (T_RING_END, -0.06)]
    d = 0.0
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t <= t0:
            break
        tt = min(t, t1)
        v_tt = v0 + (v1 - v0) * (tt - t0) / (t1 - t0)
        d += (v0 + v_tt) / 2 * (tt - t0)
    if t > T_RING_END:
        d += -0.06 * (t - T_RING_END)
    return d


def _chain(start, labels, ni, step):
    return [(n, s, start + 0.3 + step * i) for i, (n, s) in enumerate(zip(ni, labels))]


CHIPS_GOOD = _chain(T_GOOD, ['降息', '更有信心', '敢花', '敢投', '需求回暖'], [4, 0, 1, 2, 3], 1.05)
CHIPS_BAD = _chain(T_BAD, ['悲观', '少花', '少投', '收入走弱'], [0, 1, 2, 3], 0.85)
MC_CAM = Cam((0, 36, -24), (0, 0, 9), fov=60, cy=H * 0.60)


@scene(*SEC['machine'], 0.0, 0.4)
def sc_machine(fr, t, a):
    lt = t - M0
    fr.flash = max(fr.flash, 0.85 * math.exp(-lt / 0.06) * a)
    fr.ca = max(fr.ca, 8 * math.exp(-lt / 0.22))
    draw_dust(fr, t, a * 0.6, speed=1.0 + 3 * math.exp(-lt / 1.0))
    kring = a * (1 - ss((t - T_RING_END) / 0.8))
    if kring > 0.01:
        machine_ring(fr, t, kring)
    kr = a * win(t, CAP['m_why'][0] - 0.2, CAP['m_real'][1] + 0.3, 0.5, 0.4)
    if kr > 0.01:
        real_rate(fr, t, kr)
    kp = a * win(t, CAP['m_rope'][0] - 0.2, CAP['m_fiscal'][1] + 0.3, 0.4, 0.4)
    if kp > 0.01:
        rope_fiscal(fr, t, kp)
    kc = a * win(t, CAP['m_hall'][0] - 0.2, CAP['m_pull'][1] + 0.3, 0.4, 0.4)
    if kc > 0.01:
        hall_callback(fr, t, kc)
    kl = a * win(t, CAP['m_long'][0] - 0.1, SEC['machine'][1] + 0.4, 0.4, 0.35)
    if kl > 0.01:
        long_term(fr, t, kl)


def machine_ring(fr, t, k):
    bad = ss((t - T_BAD) / 0.6) * (1 - ss((t - T_RING_END) / 0.5))
    good = ss((t - T_GOOD) / 0.5) * (1 - bad)
    col = GOLD * (1 - bad) + ICE * bad
    colhi = GOLD_HI * (1 - bad) + ICE_HI * bad
    lt = t - M0
    d = np.hypot(FIELD.P[:, 0], FIELD.P[:, 2])
    ripple = 0.5 + 0.5 * np.cos(d * 0.35 - lt * (3.0 + 3.0 * good - 1.5 * bad))
    warm = np.full(FIELD.n, 0.75 + 0.25 * good) * (1 - bad) + 0.08 * bad
    bright = (0.55 + 0.35 * good - 0.2 * bad) * (0.75 + 0.5 * ripple * cl((lt - 3) / 1.0))
    FIELD.draw(fr, MC_CAM, t, k * 0.85 * cl(lt / 0.6 + 0.3), warm=warm, bright=bright)
    if lt < 1.6:
        r = 60 + 1400 * eo(lt / 1.3)
        fr.circle(tuple(RC), r, GOLD_HI, k * 0.8 * (1 - cl(lt / 1.3)), 4, glow=1.6)
        for j in range(16):
            q = j * np.pi / 8 + 0.2
            L = 1300 * eo(lt / 0.8)
            p0 = (RC[0] + 40 * math.cos(q), RC[1] + 40 * math.sin(q))
            p1 = (RC[0] + L * math.cos(q - 0.02), RC[1] + L * math.sin(q - 0.02))
            p2 = (RC[0] + L * math.cos(q + 0.02), RC[1] + L * math.sin(q + 0.02))
            fr.fill([p0, p1, p2], GOLD * 0.12 * (1 - cl(lt / 1.6)), k, layer='B')
        fr.glow(tuple(RC), 220, GOLD, k * 0.6 * (1 - cl(lt / 1.2)))
    rot = 0.05 * math.sin(lt * 0.4)
    th = np.linspace(0, 2 * np.pi, 240)
    x, y, _ = ring_xy(th + rot)
    fr.stroke(list(zip(x, y)), col, k * 0.18, 2, closed=True)
    for i in range(5):
        p = cl((t - NODE_T[i] - 0.15) / 0.5)
        if p <= 0:
            continue
        th0, th1 = node_theta(i) + rot, node_theta(i + 1) + rot
        ts = np.linspace(th0 + 0.13, th0 + 0.13 + (th1 - th0 - 0.26) * p, 40)
        x, y, _ = ring_xy(ts)
        fr.stroke(list(zip(x, y)), col, k * 0.75, 3, glow=1.0)
        if p > 0.95:
            ang = math.atan2(y[-1] - y[-3], x[-1] - x[-3])
            for s in (-1, 1):
                fr.line((x[-1], y[-1]), (x[-1] - 18 * math.cos(ang + s * 0.5), y[-1] - 18 * math.sin(ang + s * 0.5)),
                        col, k * 0.8, 3, glow=0.8)
    fk = k * cl((lt - 3.0) / 0.8)
    if fk > 0.01:
        s = (FLOW_S + flow_disp(t) * FLOW_V) % 1.0
        x, y, d = ring_xy(-np.pi / 2 + s * 2 * np.pi + rot, RR + FLOW_O)
        sp = 1.0 + 1.2 * good - 0.3 * bad
        fr.splat(x, y, colhi, fk * (0.5 + 0.5 * d) * sp)
        fr.splat(x, y, col, fk * (0.6 + 0.6 * d) * 1.4 * sp, layer='B')
    for i, name in enumerate(NODES):
        p = eback((t - NODE_T[i]) / 0.45, 2.0)
        if p <= 0.01:
            continue
        x, y, _ = ring_xy(node_theta(i) + rot)
        x, y = float(x), float(y)
        hot = max([win(t, tt, tt + 0.9, 0.05, 0.6) for ch in (CHIPS_GOOD, CHIPS_BAD) for (ni, s_, tt) in ch if ni == i]
                  + [0.0])
        fr.glow((x, y), 46 * p, col, k * 0.5)
        fr.disc((x, y), 18 * p, colhi, k, glow=1.2 + pulse(t) * 0.5)
        fr.circle((x, y), 30 * p, col, k * 0.6, 2, glow=0.6)
        fr.glow((x, y), 90, col, k * 0.6 * hot)
        if i == 0:
            lx, ly, anc = x, y - 70, 'c'
        elif i == 1:
            lx, ly, anc = x + 40, y - 46, 'l'
        elif i == 4:
            lx, ly, anc = x - 40, y - 46, 'r'
        else:
            lx, ly, anc = x, y + 62, 'c'
        fr.text(name, lx, ly, 44 if i else 56, 'serif_bold' if i else 'serif_black', 'gold' if i == 0 else 'white',
                k * cl(p), anchor=anc, glow=0.25 + 0.4 * hot)
    for chips, t1, base, colc in ((CHIPS_GOOD, T_BAD, 'gold', GOLD), (CHIPS_BAD, CAP['m_self'][0], 'ice', ICE)):
        for j, (ni, s, tt) in enumerate(chips):
            tn = chips[j + 1][2] if j + 1 < len(chips) else t1
            kk = k * win(t, tt, tn, 0.15, 0.15)
            if kk > 0.01:
                chip(fr, s + (' ↑' if base == 'gold' else ' ↓'), RC[0], RC[1] + 20, kk, colc, 48, fname='sans_bold',
                     base=base, scale=0.85 + 0.15 * eo((t - tt) / 0.25))
    chip(fr, '预期向好时', CX, 300, k * cw('m_good', t, 0.3, 0.3), GOLD, 46, fname='serif_bold')
    chip(fr, '预期悲观时', CX, 300, k * cw('m_bad', t, 0.3, 0.3), ICE, 46, fname='serif_bold', base='ice')
    kq = k * cw('m_q', t, 0.4, 0.35)
    fr.text('答案，藏在', CX, 1265, 58, 'serif_bold', 'white', kq, glow=0.2, stagger=(t - CAP['m_q'][0], 0.05, 0.4))
    fr.text('这个【循环】里', CX, 1360, 70, 'serif_black', 'white', kq, glow=0.3, stagger=(t - CAP['m_q'][0] - 0.3, 0.06, 0.45))
    ks = k * cw('m_self', t, 0.2, 0.35)
    if ks > 0.01:
        p = eo((t - CAP['m_self'][0]) / 0.4)
        fr.text('预期，会〔自我实现〕', CX, 1300, 92, 'serif_black', 'white', ks, scale=1.15 - 0.15 * p, glow=0.45)
        tt = t - CAP['m_self'][0]
        fr.cam = (6 * math.exp(-tt / 0.2) * math.sin(t * 90), 0)


def real_rate(fr, t, k):
    t0 = CAP['m_why'][0]
    k1 = k * cw('m_why', t, 0.35, 0.3)
    fr.text('降息，为什么有时不灵？', CX, 300, 68, 'serif_black', 'white', k1, glow=0.3, stagger=(t - t0, 0.04, 0.45))
    ka = k * win(t, t0 + 0.2, t0 + 2.9, 0.4, 0.35)
    if ka > 0.01:
        for j, (x, s, col, base) in enumerate(((330, '利率', ICE, 'ice'), (750, '借钱', GOLD, 'gold'))):
            p = eo((t - t0 - 0.3 - 0.35 * j) / 0.6)
            y0, y1 = 520, 520 + 360 * p
            fr.line((x, y0), (x, y1), col, ka, 10, glow=1.0)
            for sgn in (-1, 1):
                fr.line((x, y1 + 6), (x + sgn * 52, y1 - 50), col, ka * cl(p * 3 - 2), 10, glow=1.0)
            fr.text(s, x, 980, 60, 'serif_black', base, ka * p, glow=0.3)
        fr.text('?', CX, 720, 130, 'inter_light', 'white', ka * cl((t - t0 - 1.2) / 0.4), glow=0.4)
    t2 = CAP['m_real'][0]
    k2 = k * win(t, t2, CAP['m_real'][1] + 0.3, 0.4, 0.4)
    if k2 <= 0.01:
        return
    fr.card(70, 420, 1010, 560, 26, k2, tint=WHITE, border=WHITE, border_a=0.35, fill_a=0.05, blur=10)
    rich(fr, [('真实借贷成本', 'serif_bold', 46, 'white'), ('≈', 'inter_bold', 50, 'grey'),
              ('利率', 'serif_bold', 46, 'ice'), ('−', 'inter_bold', 50, 'grey'),
              ('预期涨幅', 'serif_bold', 46, 'gold')], CX, 490, k2, gap=16)
    rows = [(t2 + 0.8, '利率 5%', '预期房价 每年 +5%', '≈ 0%', '借钱几乎「免费」', GOLD, 'gold', 620),
            (t2 + 2.2, '利率 3%', '预期房价 每年 −3%', '≈ 6%', '借钱反而更「贵」', CORAL, 'coral', 850)]
    for (tt, a1, a2, res, note, col, base, y0) in rows:
        kk = k2 * eo((t - tt) / 0.45)
        if kk <= 0.01:
            continue
        yy = y0 + (1 - kk) * 40
        fr.card(70, yy, 1010, yy + 190, 26, kk, tint=col, border=col, border_a=0.6, fill_a=0.06, blur=10)
        fr.text(a1, 120, yy + 70, 50, 'sans_bold', 'ice', kk, anchor='l', glow=0.1)
        fr.text(a2, 120, yy + 138, 34, 'sans_med', 'grey', kk, anchor='l', glow=0)
        kr = kk * eo((t - tt - 0.6) / 0.4)
        fr.text(res, 820, yy + 80, 92, 'inter_xbold', base, kr, glow=0.4)
        fr.text(note, 820, yy + 150, 32, 'sans_bold', base, kr, glow=0.1)
    k3 = k * cw('m_dear', t, 0.35, 0.35)
    fr.text('利率更低，', CX, 1220, 56, 'serif_bold', 'white', k3, glow=0.2, stagger=(t - CAP['m_dear'][0], 0.05, 0.4))
    fr.text('借钱却可能【更「贵」】', CX, 1315, 66, 'serif_black', 'white', k3, glow=0.3, stagger=(t - CAP['m_dear'][0] - 0.3, 0.05, 0.45))
    footnote(fr, '示意：按买房的持有成本简化计算（未计租金与税费）', k2)


HOUSES = [(150 + i * 130, 1050) for i in range(7)]


def rope_fiscal(fr, t, k):
    t0 = CAP['m_rope'][0]
    lt = t - t0
    kr = k * (1 - ss((t - CAP['m_fiscal'][0] + 0.4) / 0.5))
    if kr > 0.01:
        bank, box = (200, 720), (840, 720)
        icon(fr, 'bank', bank, 150, ICE_HI, kr, 3.5, glow=0.9)
        fr.text('央行', bank[0], bank[1] + 125, 40, 'serif_bold', 'ice', kr, glow=0.1)
        amp = 70 * ss(lt / 1.4)
        xs = np.linspace(bank[0] + 95, box[0] - 85, 80)
        u = (xs - xs[0]) / (xs[-1] - xs[0])
        fr.stroke(list(zip(xs, bank[1] + amp * np.sin(u * np.pi * 3) * np.sin(u * np.pi))), WHITE, kr * 0.85, 4, glow=0.6)
        fr.rrect(box[0] - 85, box[1] - 85, box[0] + 85, box[1] + 85, 16, GOLD, kr, 3, glow=0.8)
        fr.text('需求', box[0], box[1], 46, 'serif_bold', 'gold', kr, glow=0.2)
        fr.text('推 →', 520, 560, 40, 'sans_bold', 'grey', kr * win(t, t0 + 0.2, t0 + 2.0, 0.3, 0.4), glow=0)
        kf = kr * eo((lt - 1.8) / 0.5)
        if kf > 0.01:
            fx = (CX, 1010)
            fr.disc(fx, 42, GOLD_HI, kf, glow=1.5)
            fr.text('财政', fx[0], fx[1] + 82, 44, 'serif_black', 'gold', kf, glow=0.3)
            p = cl((lt - 2.1) / 0.6)
            fr.line(fx, (lerp(fx[0], box[0] - 40, p), lerp(fx[1], box[1] + 90, p)), GOLD, kf, 5, glow=1.4)
            if p > 0.98:
                fr.glow(box, 120, GOLD, kf * 0.5 * (0.8 + 0.4 * pulse(t)))
        k1 = k * cw('m_rope', t, 0.4, 0.35)
        fr.text('当降息像在推绳子，', CX, 1250, 58, 'serif_bold', 'white', k1, glow=0.2, stagger=(t - t0, 0.04, 0.4))
        fr.text('就需要【财政】出手', CX, 1345, 66, 'serif_black', 'white', k1, glow=0.3, stagger=(t - t0 - 0.4, 0.05, 0.45))
    tf = CAP['m_fiscal'][0]
    kf = k * cl((t - tf + 0.2) / 0.4)
    if kf > 0.01:
        cards = [(tf + 0.1, '以旧换新', '2500', '亿元', '2026年超长期特别国债支持', 400),
                 (tf + 0.6, '育儿补贴', '3600', '元', '每孩每年 · 3周岁以下', 650)]
        for (tt, lbl, num, unit, note, y0) in cards:
            kk = kf * eo((t - tt) / 0.45)
            if kk <= 0.01:
                continue
            yy = y0 + (1 - kk) * 40
            fr.card(110, yy, 970, yy + 200, 28, kk, tint=GOLD, border=GOLD, border_a=0.6, fill_a=0.07, blur=12)
            fr.text(lbl, 160, yy + 62, 42, 'serif_bold', 'white', kk, anchor='l', glow=0)
            fr.text(note, 160, yy + 140, 30, 'sans_med', 'grey', kk, anchor='l', glow=0)
            num_unit(fr, 790, yy + 100, num, unit, 96, 40, 'gold', kk)
        lt2 = t - tf - 0.8
        for i, (hx, hy) in enumerate(HOUSES):
            lit = cl((lt2 - 0.15 * i) / 0.5)
            icon(fr, 'house', (hx, hy), 70, GOLD if lit > 0.5 else GREY, kf * (0.5 + 0.5 * lit), 2.5, glow=lit)
        r = np.random.default_rng(6)
        n = 300
        ph = (r.random(n) + lt2 * 0.8) % 1.0
        tgt = np.array(HOUSES)[r.integers(0, 7, n)]
        sx = 540 + r.normal(0, 60, n)
        px = sx * (1 - ph) + tgt[:, 0] * ph
        py = 880.0 * (1 - ph) + (tgt[:, 1] - 40) * ph - 60 * np.sin(np.pi * ph)
        fr.splat(px, py, GOLD_HI, kf * np.sin(np.pi * ph) * cl(lt2 / 0.5) * 0.9)
        fr.splat(px, py, GOLD, kf * np.sin(np.pi * ph) * cl(lt2 / 0.5) * 1.2, layer='B')
        k1 = k * cw('m_fiscal', t, 0.35, 0.3)
        fr.text('把钱直接送到【需要的地方】', CX, 1290, 62, 'serif_black', 'white', k1, glow=0.3, stagger=(t - tf, 0.04, 0.4))
        footnote(fr, '来源：2026年政府工作报告；《育儿补贴制度实施方案》（2025年7月）', kf)


def hall_callback(fr, t, k):
    t0 = CAP['m_hall'][0]
    k1 = k * cw('m_hall', t, 0.35, 0.3)
    fr.text('但别忘了', CX, 280, 56, 'serif_bold', 'white', k1 * 0 + k, glow=0.2, stagger=(t - t0, 0.05, 0.4))
    fr.text('霍尔的发现 ①', CX, 380, 66, 'serif_black', 'gold', k, glow=0.35, stagger=(t - t0 - 0.3, 0.05, 0.45))
    chip(fr, '一次性的钱，大多存起来', CX, 490, k * cl((t - t0 - 1.0) / 0.4), GOLD, 38, fname='sans_bold')
    # 家电零售：2025 年补贴拉动 +11% → 2026 年 1—8 月 −5.6%
    zero = 960
    fr.line((180, zero), (900, zero), WHITE, k * 0.35, 2)
    fr.text('家电零售额 同比', CX, 590, 38, 'sans_med', 'grey', k * cl((t - t0 - 0.8) / 0.4), glow=0)
    for j, (x, v, lbl, sub, col, base, tt) in enumerate(((360, 11.0, '2025年', '以旧换新补贴', GOLD, 'gold', t0 + 1.0),
                                                         (720, -5.6, '2026年', '1—8月', CORAL, 'coral', t0 + 2.4))):
        g = eback((t - tt) / 0.6, 1.3)
        if g <= 0:
            continue
        hh = v * 20 * g
        if v > 0:
            bar_glass(fr, x - 70, zero - hh, x + 70, zero, col, k, 2.5)
            fr.text(f'+{v * cl(g):.0f}%', x, zero - hh - 50, 64, 'inter_xbold', base, k, glow=0.3)
        else:
            bar_glass(fr, x - 70, zero, x + 70, zero - hh, col, k, 2.5)
            fr.text(f'−{abs(v) * cl(g):.1f}%', x, zero - hh + 52, 64, 'inter_xbold', base, k, glow=0.3)
        fr.text(lbl, x, zero + (-92 if v < 0 else 46), 34, 'sans_bold', 'grey', k, glow=0)   # 负柱的标签放在零线上方
        fr.text(sub, x, zero + (-48 if v < 0 else 88), 28, 'sans_med', base, k, glow=0)
    k2 = k * cw('m_pull', t, 0.35, 0.3)
    fr.text('临时补贴，', CX, 1255, 58, 'serif_bold', 'white', k2, glow=0.2, stagger=(t - CAP['m_pull'][0], 0.05, 0.4))
    fr.text('常常只是把需求【提前】了', CX, 1350, 64, 'serif_black', 'white', k2, glow=0.3,
            stagger=(t - CAP['m_pull'][0] - 0.3, 0.045, 0.45))
    footnote(fr, '限额以上单位家用电器和音像器材类零售额 · 来源：国家统计局、商务部', k, y=1450)


def long_term(fr, t, k):
    t0 = CAP['m_long'][0]
    fr.glow((CX, 760), 420, GOLD, k * 0.12)
    p = eo((t - t0) / 0.6)
    fr.text('长期、可预期的政策，', CX, 700, 64, 'serif_bold', 'white', k, glow=0.3, stagger=(t - t0, 0.05, 0.45))
    fr.text('才能【改变预期】', CX, 820, 84, 'serif_black', 'white', k, glow=0.45, stagger=(t - t0 - 0.4, 0.07, 0.5))
    chip(fr, '时滞：政策见效，往往要几个季度', CX, 980, k * cl((t - t0 - 1.4) / 0.4), GREY, 36, base='white')


# ================================================================ 06 真相 292–306
TR0 = SEC['truth'][0]


def truth_cam(t):
    lt = t - TR0
    return Cam((0, 6.0 + lt * 0.25, -52 + lt * 0.5), (0, 0.6, 10 + lt * 0.5), fov=56, cy=H * 0.66)


_UR = np.random.default_rng(19)
RISE_N = 900
RISE_X = _UR.uniform(-48, 48, RISE_N)
RISE_Z = _UR.uniform(-48, 48, RISE_N)
RISE_T = _UR.random(RISE_N) * 6


@scene(*SEC['truth'], 0.4, 0.45)
def sc_truth(fr, t, a):
    lt = t - TR0
    cam = truth_cam(t)
    sun = ss((t - (HITS['keyline'] - 1.5)) / 2.0)
    FIELD.draw(fr, cam, t, a * (0.8 + 0.4 * sun), warm=np.full(FIELD.n, 0.25 + 0.7 * sun), size=1.1)
    hx, hy, _, _ = cam.project([[0, 0, 300]])
    hy = float(hy[0])
    for s_, al in ((1000, 0.10), (420, 0.20), (130, 0.4)):
        fr.glow((CX, hy), s_, GOLD, a * al * (0.3 + 0.7 * sun))
    xs = np.linspace(-80, W + 80, 60)
    fr.stroke(list(zip(xs, np.full(60, hy))), GOLD_HI, a * (0.3 + 0.6 * sun), 2, glow=1.4)
    ph = (lt * 0.25 + RISE_T / 6) % 1.0
    x, y, z, s = cam.project(np.c_[RISE_X, ph * 14, RISE_Z])
    ok = z > 0.5
    fr.splat(x[ok], y[ok], GOLD_HI, (a * np.sin(np.pi * ph) * (0.3 + 0.9 * sun))[ok])
    if t >= HITS['keyline']:
        fr.flash = max(fr.flash, 0.22 * math.exp(-(t - HITS['keyline']) / 0.12) * a)
    draw_dust(fr, t, a * 0.5)
    k = a * cw('tr_1', t, 0.4, 0.35)
    fr.text('宏观经济，', CX, 640, 70, 'serif_bold', 'white', k, glow=0.25, stagger=(t - CAP['tr_1'][0], 0.05, 0.45))
    fr.text('不是抽象的数字', CX, 750, 78, 'serif_black', 'white', k, glow=0.3, stagger=(t - CAP['tr_1'][0] - 0.3, 0.05, 0.45))
    k = a * cw('tr_2', t, 0.4, 0.35)
    fr.text('是亿万家庭和企业，', CX, 640, 70, 'serif_bold', 'white', k, glow=0.25, stagger=(t - CAP['tr_2'][0], 0.05, 0.45))
    fr.text('对【明天】做出的选择', CX, 750, 78, 'serif_black', 'white', k, glow=0.3, stagger=(t - CAP['tr_2'][0] - 0.3, 0.05, 0.45))
    k = a * cw('tr_3', t, 0.4, 0.4)
    t3 = CAP['tr_3'][0]
    fr.text('影响经济的，', CX, 520, 54, 'serif_med', 'grey', k, glow=0.2, stagger=(t - t3, 0.05, 0.4))
    fr.text('不只是我们今天拥有多少，', CX, 620, 62, 'serif_bold', 'white', k, glow=0.25, stagger=(t - t3 - 0.4, 0.04, 0.45))
    fr.text('更是我们', CX, 760, 62, 'serif_bold', 'white', k, glow=0.25, stagger=(t - t3 - 1.6, 0.06, 0.45))
    fr.text('【相信明天会发生什么】', CX, 875, 86, 'serif_black', 'white', k, glow=0.5, stagger=(t - t3 - 2.0, 0.07, 0.55))
    fr.zoom = 1 + 0.03 * ss(lt / 14)


# ================================================================ 获奖者 306–322
LA0 = SEC['laureates'][0]


def light_beams(fr, a, t):
    for k, (x, w, al) in enumerate(((CX, 520, 0.05), (CX - 220, 260, 0.03), (CX + 240, 300, 0.035))):
        sway = 30 * math.sin(t * 0.3 + k)
        pts = [(x - 60 + sway, -20), (x + 60 + sway, -20), (x + w + sway * 2, H * 0.75), (x - w + sway * 2, H * 0.75)]
        fr.fill(pts, GOLD * al, a, layer='B')


_GR = np.random.default_rng(29)
GD_N = 260
GD_X = _GR.uniform(0, W, GD_N)
GD_Y = _GR.uniform(0, H, GD_N)
GD_S = _GR.uniform(10, 40, GD_N)


def gold_dust(fr, t, a):
    y = (GD_Y - t * GD_S) % H
    x = GD_X + 20 * np.sin(t * 0.5 + GD_Y)
    tw = 0.5 + 0.5 * np.sin(t * 2 + GD_X)
    fr.dots(x, y, 1.2 + GD_S / 25, GOLD_HI, a * 0.35 * tw, layer='B')
    fr.splat(x, y, GOLD_HI, a * 0.25 * tw)


def portrait_card(fr, who, cx, cy, width, k, sweep=None):
    rgb, al = portraits.card(who, int(width))
    h, w = al.shape
    fr.glow((cx, cy), width * 0.55, GOLD, k * 0.08)
    fr.card(cx - w / 2 - 14, cy - h / 2 - 14, cx + w / 2 + 14, cy + h / 2 + 14, 24, k, tint=GOLD, border=GOLD,
            border_a=0.7, fill_a=0.05, blur=6)
    fr.image(rgb, al, cx, cy, k)
    if sweep is not None and 0 < sweep < 1:
        def band(img, cx=cx, cy=cy, w=w, h=h, s=sweep, k=k):
            x0, y0 = int(cx - w / 2), int(cy - h / 2)
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            pos = -0.3 * w + s * 1.6 * w
            b = np.exp(-((xx + yy * 0.5 - pos) / (0.08 * w)) ** 2) * 0.28 * k
            reg = img[max(y0, 0):y0 + h, max(x0, 0):x0 + w]
            reg += b[:reg.shape[0], :reg.shape[1], None] * al[:reg.shape[0], :reg.shape[1], None]
        fr.overlay_fn(band)


@scene(*SEC['laureates'], 0.4, 0.35)
def sc_laureates(fr, t, a):
    light_beams(fr, a, t)
    gold_dust(fr, t, a)
    T_END = SEC['laureates'][1]
    end = 1 - ss((t - T_END) / 0.5)
    kh = a * cl((t - LA0) / 0.8) * (1 - ss((t - T_END + 0.2) / 0.6))
    fr.text('2026 诺贝尔经济学奖', CX, 228, 42, 'serif_med', 'gold', kh, track=0.26, glow=0.35)
    fr.text('THE SVERIGES RIKSBANK PRIZE IN ECONOMIC SCIENCES IN MEMORY OF ALFRED NOBEL', CX, 280, 20, 'corm_bold',
            'subgold', kh * 0.9, track=0.12, glow=0.1)
    tW, tB = HITS['woodford_card'], HITS['both']
    for (who, t0, t1, en, zh, cap_key) in (
            ('hall', LA0, tW, 'Robert E. Hall', '罗伯特·霍尔 · 斯坦福大学 · 1943年生', 'la_hall'),
            ('woodford', tW, tB, 'Michael Woodford', '迈克尔·伍德福德 · 哥伦比亚大学 · 1955年生', 'la_wood')):
        kin = eo((t - t0) / 0.8)
        kout = ss((t - t1 + 0.35) / 0.55)
        k = a * kin * (1 - kout)
        if k <= 0.01:
            continue
        dx = (1 - kin) * 70 - kout * 90
        sc = 0.96 + 0.04 * kin
        portrait_card(fr, who, CX + dx, 740, 700 * sc, k, sweep=cl((t - t0 - 0.3) / 1.6))
        fr.text(en, CX + dx, 1180, 72, 'corm_bold', 'gold', k * eo((t - t0 - 0.3) / 0.6), glow=0.35, track=0.03)
        fr.text(zh, CX + dx, 1250, 32, 'sans_med', 'grey', k * eo((t - t0 - 0.5) / 0.6), glow=0, track=0.04)
        kc = a * cw(cap_key, t, 0.4, 0.3)
        fr.text(CAP[cap_key][2], CX, 1335, 44, 'serif_bold', 'white', kc * (1 - kout), glow=0.2,
                stagger=(t - CAP[cap_key][0], 0.035, 0.4))
    kb = a * eo((t - tB) / 0.8) * end
    if kb > 0.01:
        for j, (who, en, zh) in enumerate((('hall', 'Robert E. Hall', '斯坦福大学'),
                                            ('woodford', 'Michael Woodford', '哥伦比亚大学'))):
            cx = 290 + 500 * j
            kk = kb * eo((t - tB - 0.15 * j) / 0.7)
            portrait_card(fr, who, cx, 620 + (1 - kk) * 30, 440, kk)
            fr.text(en, cx, 885, 44, 'corm_bold', 'gold', kk, glow=0.3)
            fr.text(zh, cx, 935, 28, 'sans_med', 'grey', kk, glow=0)
        kq = a * win(t, tB + 0.4, T_END + 0.4, 0.6, 0.3)
        fr.text('“for microeconomic foundations', CX, 1035, 42, 'corm_bold', 'white', kq, glow=0.2)
        fr.text('of macroeconomic stabilisation”', CX, 1088, 42, 'corm_bold', 'white', kq, glow=0.2)
        kc = a * cw('la_cite', t, 0.5, 0.3)
        fr.text('表彰他们为【宏观经济稳定政策】', CX, 1190, 50, 'serif_bold', 'white', kc, glow=0.25,
                stagger=(t - CAP['la_cite'][0], 0.035, 0.4))
        fr.text('奠定微观经济学基础', CX, 1262, 50, 'serif_bold', 'white', kc, glow=0.25, stagger=(t - CAP['la_cite'][0] - 0.4, 0.04, 0.4))
        fr.text('瑞典皇家科学院 · 2026年10月12日', CX, 1340, 28, 'sans_reg', 'grey', kc, glow=0)
        fr.text('肖像插画：Niklas Elmehed © Nobel Prize Outreach', CX, 1392, 24, 'sans_light', 'dim', kc, glow=0)
    fr.zoom = 1 + 0.02 * ss((t - LA0) / 16)


# ================================================================ 品牌片尾 322–332
B0 = SEC['brand'][0]
END_LOGO_PX = 220                      # BRAND.md：片尾 logo 约 220px 居中
LOGO_C = (CX, 800)
K_SCALE = END_LOGO_PX / BR.SPEC['logo_px']
END_LOGO = BR.load_logo(END_LOGO_PX)


def _brand_word():
    """按 brand.build() 的做法渲染片尾大字：Noto Serif SC Black 金色竖向渐变；
    小字 BUFFETT · MUNGER（Cormorant Garamond）两端对齐到与主标题等宽。"""
    from PIL import Image, ImageDraw
    S = BR.SPEC
    k = K_SCALE
    f1 = BR._font(S['title_font'], int(S['title_px'] * k))
    im = Image.new('L', (int(f1.getlength(S['title']) + 40 * k), int(S['title_px'] * k * 1.6)), 0)
    ImageDraw.Draw(im).text((10 * k, int(S['title_px'] * k * 1.25)), S['title'], font=f1, fill=255, anchor='ls')
    t1 = BR._ink(im)
    f2 = BR._font(S['sub_font'], int(S['sub_px'] * k))
    nat = sum(f2.getlength(c) for c in S['sub'])
    tr = (t1.shape[1] - nat) / (len(S['sub']) - 1)
    w2 = int(nat + tr * len(S['sub']) + 20 * k)
    im = Image.new('L', (w2, int(S['sub_px'] * k * 2)), 0)
    d = ImageDraw.Draw(im)
    x = 5 * k
    for c in S['sub']:
        d.text((x, int(S['sub_px'] * k * 1.4)), c, font=f2, fill=255, anchor='ls')
        x += f2.getlength(c) + tr
    t2 = BR._ink(im)[:, :t1.shape[1]]
    rgb1 = np.broadcast_to(BR._ramp(t1.shape[0], BR.GOLD_STOPS)[:, None, :], t1.shape + (3,)).astype(np.float32)
    rgb2 = np.broadcast_to(np.array(BR.SUB_GOLD, np.float32) / 255, t2.shape + (3,)).astype(np.float32)
    return (rgb1.copy(), t1.astype(np.float32)), (rgb2.copy(), t2.astype(np.float32)), int(S['sub_gap_px'] * k)


WORD, SUBW, SUBGAP = _brand_word()
WORD_CY = LOGO_C[1] + END_LOGO_PX / 2 + 70 + WORD[1].shape[0] / 2
SUB_CY = WORD_CY + WORD[1].shape[0] / 2 + SUBGAP + SUBW[1].shape[0] / 2


def _logo_targets(n):
    rgb, al = END_LOGO
    ys, xs = np.nonzero(al > 0.35)
    r = np.random.default_rng(13)
    pick = r.choice(len(xs), n, replace=len(xs) < n, p=al[ys, xs] / al[ys, xs].sum())
    pts = np.c_[xs[pick] + r.random(n) - END_LOGO_PX / 2 + LOGO_C[0], ys[pick] + r.random(n) - END_LOGO_PX / 2 + LOGO_C[1]]
    return pts, rgb[ys[pick], xs[pick]].astype(np.float64)


def _card_sources(n):
    pts, cols = [], []
    r = np.random.default_rng(17)
    for j, who in enumerate(('hall', 'woodford')):
        rgb, al = portraits.card(who, 440)
        h, w = al.shape
        lum = rgb.mean(2)
        sat = rgb.max(2) - rgb.min(2)
        wgt = (np.clip(0.85 - lum, 0, 1) * 3 + np.clip(sat - 0.12, 0, 1) * 4 + 0.08) * (al > 0.5)
        flat = wgt.ravel() / wgt.sum()
        m = n // 2
        idx = r.choice(flat.size, m, p=flat)
        ys, xs = np.unravel_index(idx, wgt.shape)
        cx, cy = 290 + 500 * j, 620
        pts.append(np.c_[xs - w / 2 + cx + r.random(m) - 0.5, ys - h / 2 + cy + r.random(m) - 0.5])
        g = np.clip((sat[ys, xs] - 0.12) * 4, 0, 1)[:, None]
        ink = (lum[ys, xs] < 0.6)[:, None]
        c = np.where(ink, np.array([1.0, 0.96, 0.9]), np.array([1.0, 0.9, 0.7]) * 0.5)
        cols.append(c * (1 - g) + np.array([1.0, 0.8, 0.42]) * g)
    return np.concatenate(pts), np.concatenate(cols)


PN = 9000
P_TGT, P_TCOL = _logo_targets(PN)
P_SRC, P_SCOL = _card_sources(PN)
_ER = np.random.default_rng(31)
P_JIT = _ER.normal(0, 1, (PN, 2))
P_DEL = _ER.random(PN) * 0.35


def blit_rgba(img, rgb, a, cx, cy, alpha=1.0, wipe=1.0, shine=None, k_scale=1.0):
    if alpha <= 0.003:
        return
    h, w = a.shape
    a = a * alpha
    if wipe < 1.0:
        soft = 0.35 * w + 30
        a = a * np.clip((wipe * (w + soft) - np.arange(w)) / soft, 0, 1).astype(np.float32)[None, :]
    if shine is not None and 0 < shine < 1:
        # 与 brand.Hud.rgb_at 相同的流光：斜向高斯光带，宽度按比例放大
        xs = np.arange(w)[None, :] + np.arange(h)[:, None] * 0.6
        span = w + 80 * k_scale
        pos = -40 * k_scale + (0.5 - 0.5 * math.cos(shine * math.pi)) * span
        rgb = np.clip(rgb + np.exp(-((xs - pos) / (16 * k_scale)) ** 2)[..., None] * 0.6, 0, 1.25)
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if X1 <= X0 or Y1 <= Y0:
        return
    aa = a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0, None]
    reg = img[Y0:Y1, X0:X1]
    reg *= 1 - aa
    reg += aa * rgb[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]


@scene(*SEC['brand'], 0.0, 0.0)
def sc_brand(fr, t, a):
    draw_dust(fr, t, a * 0.4 * (1 - ss((t - B0 - 3) / 2)))
    T_LOGO = HITS['logo']
    u = np.clip((t - B0 - P_DEL) / (T_LOGO - B0 - P_DEL), 0, 1)
    e = u * u * (3 - 2 * u)
    mid = np.array(LOGO_C)
    ang = np.arctan2(P_SRC[:, 1] - mid[1], P_SRC[:, 0] - mid[0]) + 2.6 * e
    rad = np.hypot(P_SRC[:, 0] - mid[0], P_SRC[:, 1] - mid[1]) * (1 - e) + 40 * np.sin(np.pi * e)
    swirl = np.c_[mid[0] + rad * np.cos(ang), mid[1] + rad * np.sin(ang)]
    P = swirl * (1 - e[:, None] ** 3) + P_TGT * e[:, None] ** 3 + P_JIT * 6 * np.sin(np.pi * e)[:, None]
    col = P_SCOL * (1 - e[:, None]) + P_TCOL * e[:, None]
    after = ss((t - T_LOGO - 0.4) / 2.5)
    P = P + P_JIT * 160 * after
    al = a * (1.0 - 0.8 * after) * (1 - ss((t - (B0 + 6.5)) / 1.5)) * ss((t - B0 + 0.1) / 0.3)
    if al > 0.01:
        pa = al * (1 - 0.7 * e)
        sz = 0.8 + 1.4 * np.sin(np.pi * e)
        fr.splat(P[:, 0], P[:, 1], col, pa * 0.9)
        fr.dots(P[::6, 0], P[::6, 1], sz[::6], col[::6], pa[::6] * 0.6, layer='B')
        fr.splat(P[:, 0], P[:, 1], col, pa * 0.9, layer='B')
    kl = a * ss((t - T_LOGO) / 0.9)
    if kl > 0.01:
        fr.glow(LOGO_C, BR.SPEC['glow_sigma'] * K_SCALE, BRANDBLUE, kl * BR.SPEC['glow_strength'] * 2.2)
        rgb, al_ = END_LOGO
        fr.overlay_fn(lambda img, kl=kl: blit_rgba(img, rgb, al_, LOGO_C[0], LOGO_C[1], kl))
    T_W = HITS['brandword']
    if t >= T_W:
        w1 = cl((t - T_W) / 0.9)
        w2 = cl((t - T_W - 0.3) / 0.9)
        sh = (t - SHIMMER_T0) / BR.SPEC['shimmer_dur']
        rgb1, a1 = WORD
        rgb2, a2 = SUBW
        fr.overlay_fn(lambda img: blit_rgba(img, rgb1, a1, CX, WORD_CY, a, wipe=w1, shine=sh, k_scale=K_SCALE))
        fr.overlay_fn(lambda img: blit_rgba(img, rgb2, a2, CX, SUB_CY, a, wipe=w2, shine=sh, k_scale=K_SCALE))
        hw = a1.shape[1] / 2 + 40
        ln = 150 * eo((t - T_W - 0.3) / 1.0)

        def lines(img, hw=hw, ln=ln):
            y = int(WORD_CY)
            for s in (-1, 1):
                xa, xb = CX + s * hw, CX + s * (hw + ln)
                x0, x1 = int(min(xa, xb)), int(max(xa, xb))
                if x1 > x0:
                    img[y:y + 2, x0:x1] = img[y:y + 2, x0:x1] * 0.3 + 0.7 * SUBGOLD
        fr.overlay_fn(lines)
        fr.flash = max(fr.flash, 0.18 * math.exp(-(t - T_W) / 0.1))
