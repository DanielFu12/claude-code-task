"""05 传导（预期机器、正反循环、降息为何不灵、推绳子、财政）→ 06 真相 → 获奖者 → 品牌片尾"""
import math

import numpy as np

from common import *          # noqa: F401,F403
from registry import scene
from timeline import CAP, HITS, SHIMMER_T0
from scenes_a import chip, rich, num_unit
import portraits

CX = W / 2


def cw(key, t, fi=0.35, fo=0.3):
    t0, t1, _ = CAP[key]
    return win(t, t0, t1, fi, fo)


# ================================================================ 05 传导机器 116–152
NODES = ['预期', '消费·储蓄', '定价·投资', '需求·物价', '央行·政策']
NODE_T = [116.5, 117.0, 117.5, 118.0, 118.5]
RC = np.array([CX, 790.0])
RR = 272.0
TILT = 0.42


def ring_xy(theta, rr=RR, c=RC, tilt=TILT):
    th = np.asarray(theta, np.float64)
    x = c[0] + rr * np.cos(th)
    y = c[1] + rr * np.sin(th) * math.cos(tilt)
    depth = (np.sin(th) + 1) / 2            # 1 = 前（下方）
    return x, y, depth


def node_theta(i):
    return -np.pi / 2 + i * 2 * np.pi / 5


_RP = np.random.default_rng(23)
FLOW_N = 1100
FLOW_S = _RP.random(FLOW_N)
FLOW_O = _RP.normal(0, 7, FLOW_N)
FLOW_V = 0.8 + 0.4 * _RP.random(FLOW_N)


def flow_disp(t):
    """流动累计位移（圈数）：向好时顺时针加速，悲观时逆向变慢"""
    pts = [(119.0, 0.0), (124.0, 0.10), (129.0, 0.22), (129.6, -0.06), (134.0, -0.06)]
    d = 0.0
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t <= t0:
            break
        tt = min(t, t1)
        # 速度线性插值的积分
        v_tt = v0 + (v1 - v0) * (tt - t0) / (t1 - t0)
        d += (v0 + v_tt) / 2 * (tt - t0)
    if t > 134.0:
        d += -0.06 * (t - 134.0)
    return d


CHIPS_GOOD = [(4, '降息', 124.5), (0, '更有信心', 125.3), (1, '敢花', 126.1), (2, '敢投', 126.9), (3, '需求回暖', 127.7)]
CHIPS_BAD = [(0, '悲观', 129.3), (1, '少花', 129.9), (2, '少投', 130.5), (3, '收入走弱', 131.1), (0, '更悲观', 131.7)]


@scene(116.0, 152.0, 0.0, 0.4)
def sc_machine(fr, t, a):
    lt = t - 116.0
    fr.flash = max(fr.flash, 0.85 * math.exp(-lt / 0.06) * a)
    fr.ca = max(fr.ca, 8 * math.exp(-lt / 0.22))
    draw_dust(fr, t, a * 0.6, speed=1.0 + 3 * math.exp(-lt / 1.0))
    kring = a * (1 - ss((t - 134.0) / 0.8))
    if kring > 0.01:
        machine_ring(fr, t, kring)
    kr = a * win(t, 134.0, 142.2, 0.5, 0.4)
    if kr > 0.01:
        real_rate(fr, t, kr)
    kp = a * win(t, 142.0, 146.2, 0.4, 0.4)
    if kp > 0.01:
        rope(fr, t, kp)
    kf = a * win(t, 146.0, 152.0, 0.4, 0.4)
    if kf > 0.01:
        fiscal(fr, t, kf)


MC_CAM = Cam((0, 36, -24), (0, 0, 9), fov=60, cy=H * 0.60)


def machine_ring(fr, t, k):
    bad = ss((t - 129.0) / 0.6) * (1 - ss((t - 134.0) / 0.5))
    good = ss((t - 124.0) / 0.5) * (1 - bad)
    col = GOLD * (1 - bad) + ICE * bad
    colhi = GOLD_HI * (1 - bad) + ICE_HI * bad
    lt = t - 116.0
    # 背景：千万家庭光点场随循环变暖 / 变冷，并随流动一圈圈荡开
    d = np.hypot(FIELD.P[:, 0], FIELD.P[:, 2])
    ripple = 0.5 + 0.5 * np.cos(d * 0.35 - lt * (3.0 + 3.0 * good - 1.5 * bad))
    warm = np.full(FIELD.n, 0.75 + 0.25 * good) * (1 - bad) + 0.08 * bad
    bright = (0.55 + 0.35 * good - 0.2 * bad) * (0.75 + 0.5 * ripple * cl((t - 119) / 1.0))
    FIELD.draw(fr, MC_CAM, t, k * 0.85 * cl(lt / 0.6 + 0.3), warm=warm, bright=bright)
    # 重拍：冲击波 + 放射光
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
    rot = 0.05 * math.sin((t - 116) * 0.4)
    # 底环
    th = np.linspace(0, 2 * np.pi, 240)
    x, y, d = ring_xy(th + rot)
    fr.stroke(list(zip(x, y)), col, k * 0.18, 2, closed=True)
    # 逐段连线（节点出现后点亮）
    for i in range(5):
        p = cl((t - NODE_T[i] - 0.15) / 0.5)
        if p <= 0:
            continue
        th0, th1 = node_theta(i) + rot, node_theta(i + 1) + rot
        ts = np.linspace(th0 + 0.13, th0 + 0.13 + (th1 - th0 - 0.26) * p, 40)
        x, y, d = ring_xy(ts)
        fr.stroke(list(zip(x, y)), col, k * 0.75, 3, glow=1.0)
        if p > 0.95:      # 箭头
            ang = math.atan2(y[-1] - y[-3], x[-1] - x[-3])
            for s in (-1, 1):
                fr.line((x[-1], y[-1]), (x[-1] - 18 * math.cos(ang + s * 0.5), y[-1] - 18 * math.sin(ang + s * 0.5)),
                        col, k * 0.8, 3, glow=0.8)
    # 流动光粒
    fk = k * cl((t - 119.0) / 0.8)
    if fk > 0.01:
        disp = flow_disp(t)
        s = (FLOW_S + disp * FLOW_V) % 1.0
        ths = -np.pi / 2 + s * 2 * np.pi + rot
        x, y, d = ring_xy(ths, RR + FLOW_O)
        sp = 1.0 + 1.2 * good - 0.3 * bad
        fr.splat(x, y, colhi, fk * (0.5 + 0.5 * d) * sp)
        fr.splat(x, y, col, fk * (0.6 + 0.6 * d) * 1.4 * sp, layer='B')
    # 节点
    for i, name in enumerate(NODES):
        p = eback((t - NODE_T[i]) / 0.45, 2.0)
        if p <= 0.01:
            continue
        th = node_theta(i) + rot
        x, y, d = ring_xy(th)
        x, y = float(x), float(y)
        pul = pulse(t) * 0.5
        fr.glow((x, y), 46 * p, col, k * 0.5)
        fr.disc((x, y), 18 * p, colhi, k, glow=1.2 + pul)
        fr.circle((x, y), 30 * p, col, k * 0.6, 2, glow=0.6)
        # 标签：放在环外侧
        if i == 0:
            lx, ly, anc = x, y - 70, 'c'
        elif i == 1:
            lx, ly, anc = x + 40, y - 46, 'l'
        elif i == 4:
            lx, ly, anc = x - 40, y - 46, 'r'
        else:
            lx, ly, anc = x, y + 62, 'c'
        hot = max([win(t, tt, tt + 0.8, 0.05, 0.6) for ch in (CHIPS_GOOD, CHIPS_BAD) for (ni, s_, tt) in ch if ni == i]
                  + [0.0])
        fr.glow((x, y), 90, col, k * 0.6 * hot)
        fr.text(name, lx, ly, 44 if i else 56, 'serif_bold' if i else 'serif_black', 'gold' if i == 0 else 'white',
                k * cl(p), anchor=anc, glow=0.25 + 0.4 * hot)
    # 正 / 反循环的标签
    # 环心：当前这一步（与节点闪光、铃声同步）
    for chips, t0, t1, base, colc in ((CHIPS_GOOD, 124.0, 129.0, 'gold', GOLD), (CHIPS_BAD, 129.0, 132.0, 'ice', ICE)):
        for j, (ni, s, tt) in enumerate(chips):
            tn = chips[j + 1][2] if j + 1 < len(chips) else t1
            kk = k * win(t, tt, tn, 0.15, 0.15)
            if kk <= 0.01:
                continue
            arrow = ' ↑' if base == 'gold' else ' ↓'
            chip(fr, s + arrow, RC[0], RC[1] + 20, kk, colc, 46, fname='sans_bold', base=base,
                 scale=0.85 + 0.15 * eo((t - tt) / 0.25))
    kh = k * cw('mc_good', t, 0.3, 0.3)
    chip(fr, '预期向好时', CX, 300, kh, GOLD, 44, fname='serif_bold')
    kh = k * cw('mc_bad', t, 0.3, 0.3)
    chip(fr, '预期悲观时', CX, 300, kh, ICE, 44, fname='serif_bold', base='ice')
    kq = k * cw('mc_q', t, 0.4, 0.35)
    fr.text('一个利率，', CX, 1265, 58, 'serif_bold', 'white', kq, glow=0.2, stagger=(t - 120.0, 0.04, 0.4))
    fr.text('如何牵动【亿万个决定】？', CX, 1355, 64, 'serif_black', 'white', kq, glow=0.3, stagger=(t - 120.3, 0.04, 0.45))
    ks = k * cw('mc_self', t, 0.2, 0.35)
    if ks > 0.01:
        p = eo((t - 132.0) / 0.4)
        fr.text('预期，会〔自我实现〕', CX, 1300, 92, 'serif_black', 'white', ks, scale=1.15 - 0.15 * p, glow=0.45)
        fr.cam = (6 * math.exp(-(t - 132) / 0.2) * math.sin(t * 90), 0)


def real_rate(fr, t, k):
    k1 = k * cw('mc_why', t, 0.35, 0.3)
    fr.text('降息，为什么有时不灵？', CX, 300, 68, 'serif_black', 'white', k1, glow=0.3, stagger=(t - 134.0, 0.04, 0.45))
    # 回顾悖论：利率↓，借钱也↓
    ka = k * win(t, 134.3, 136.9, 0.4, 0.35)
    if ka > 0.01:
        for j, (x, s, col, base) in enumerate(((330, '利率', ICE, 'ice'), (750, '借钱', GOLD, 'gold'))):
            p = eo((t - 134.4 - 0.35 * j) / 0.6)
            y0, y1 = 520, 520 + 360 * p
            fr.line((x, y0), (x, y1), col, ka, 10, glow=1.0)
            for sgn in (-1, 1):
                fr.line((x, y1 + 6), (x + sgn * 52, y1 - 50), col, ka * cl(p * 3 - 2), 10, glow=1.0)
            fr.text(s, x, 980, 60, 'serif_black', base, ka * p, glow=0.3)
        fr.text('?', CX, 720, 130, 'inter_light', 'white', ka * cl((t - 135.4) / 0.4), glow=0.4)
    k2 = k * win(t, 136.6, 142.2, 0.4, 0.4)
    if k2 <= 0.01:
        return
    fr.card(70, 420, 1010, 560, 26, k2, tint=WHITE, border=WHITE, border_a=0.35, fill_a=0.05, blur=10)
    rich(fr, [('真实借贷成本', 'serif_bold', 46, 'white'), ('≈', 'inter_bold', 50, 'grey'),
              ('利率', 'serif_bold', 46, 'ice'), ('−', 'inter_bold', 50, 'grey'),
              ('预期涨幅', 'serif_bold', 46, 'gold')], CX, 490, k2, gap=16)
    rows = [(137.4, '利率 5%', '预期房价 每年 +5%', '≈ 0%', '借钱几乎「免费」', GOLD, 'gold', 620),
            (138.4, '利率 3%', '预期房价 每年 −3%', '≈ 6%', '借钱反而更「贵」', CORAL, 'coral', 850)]
    for (tt, a1, a2, res, note, col, base, y0) in rows:
        kk = k2 * eo((t - tt) / 0.45)
        if kk <= 0.01:
            continue
        yy = y0 + (1 - kk) * 40
        fr.card(70, yy, 1010, yy + 190, 26, kk, tint=col, border=col, border_a=0.6, fill_a=0.06, blur=10)
        fr.text(a1, 120, yy + 70, 50, 'sans_bold', 'ice', kk, anchor='l', glow=0.1)
        fr.text(a2, 120, yy + 138, 34, 'sans_med', 'grey', kk, anchor='l', glow=0)
        kr = kk * eo((t - tt - 0.5) / 0.4)
        fr.text(res, 820, yy + 80, 92, 'inter_xbold', base, kr, glow=0.4)
        fr.text(note, 820, yy + 150, 32, 'sans_bold', base, kr, glow=0.1)
    k3 = k * cw('mc_dear', t, 0.35, 0.35)
    fr.text('利率更低，借钱却可能【更「贵」】', CX, 1200, 60, 'serif_black', 'white', k3, glow=0.3,
            stagger=(t - 139.0, 0.04, 0.4))
    footnote(fr, '示意：按买房的持有成本简化计算（未计租金与税费）', k2)


def rope(fr, t, k):
    lt = t - 142.0
    bank = (200, 720)
    box = (840, 720)
    icon(fr, 'bank', bank, 150, ICE_HI, k, 3.5, glow=0.9)
    fr.text('央行', bank[0], bank[1] + 125, 40, 'serif_bold', 'ice', k, glow=0.1)
    # 被「推」的绳子：越推越弯，盒子纹丝不动
    amp = 70 * ss(lt / 1.4)
    xs = np.linspace(bank[0] + 95, box[0] - 85, 80)
    u = (xs - xs[0]) / (xs[-1] - xs[0])
    ys = bank[1] + amp * np.sin(u * np.pi * 3) * np.sin(u * np.pi)
    fr.stroke(list(zip(xs, ys)), WHITE, k * 0.85, 4, glow=0.6)
    fr.rrect(box[0] - 85, box[1] - 85, box[0] + 85, box[1] + 85, 16, GOLD, k, 3, glow=0.8)
    fr.text('需求', box[0], box[1], 46, 'serif_bold', 'gold', k, glow=0.2)
    fr.text('推 →', 520, 560, 40, 'sans_bold', 'grey', k * win(t, 142.2, 144.0, 0.3, 0.4), glow=0)
    # 财政出手：直接作用于需求
    kf = k * eo((t - 143.8) / 0.5)
    if kf > 0.01:
        fx = (CX, 1010)
        fr.disc(fx, 42, GOLD_HI, kf, glow=1.5)
        fr.text('财政', fx[0], fx[1] + 82, 44, 'serif_black', 'gold', kf, glow=0.3)
        p = cl((t - 144.1) / 0.6)
        end = (lerp(fx[0], box[0] - 40, p), lerp(fx[1], box[1] + 90, p))
        fr.line(fx, end, GOLD, kf, 5, glow=1.4)
        if p > 0.98:
            fr.glow(box, 120, GOLD, kf * 0.5 * (0.8 + 0.4 * pulse(t)))
    k1 = k * cw('mc_rope', t, 0.4, 0.35)
    fr.text('当降息像在推绳子，', CX, 1250, 58, 'serif_bold', 'white', k1, glow=0.2, stagger=(t - 142.0, 0.04, 0.4))
    fr.text('就需要【财政】出手', CX, 1345, 66, 'serif_black', 'white', k1, glow=0.3, stagger=(t - 142.4, 0.05, 0.45))


HOUSES = [(150 + i * 130, 1030) for i in range(7)]


def fiscal(fr, t, k):
    cards = [(146.2, '以旧换新', '2500', '亿元', '2026年超长期特别国债支持', 390),
             (146.7, '育儿补贴', '3600', '元', '每孩每年 · 3周岁以下', 640)]
    for (tt, lbl, num, unit, note, y0) in cards:
        kk = k * eo((t - tt) / 0.45)
        if kk <= 0.01:
            continue
        yy = y0 + (1 - kk) * 40
        fr.card(110, yy, 970, yy + 200, 28, kk, tint=GOLD, border=GOLD, border_a=0.6, fill_a=0.07, blur=12)
        fr.text(lbl, 160, yy + 62, 42, 'serif_bold', 'white', kk, anchor='l', glow=0)
        fr.text(note, 160, yy + 140, 30, 'sans_med', 'grey', kk, anchor='l', glow=0)
        num_unit(fr, 790, yy + 100, num, unit, 96, 40, 'gold', kk)
    # 资金流向家庭
    lt = t - 147.0
    for i, (hx, hy) in enumerate(HOUSES):
        lit = cl((lt - 0.15 * i) / 0.5)
        icon(fr, 'house', (hx, hy), 70, GOLD if lit > 0.5 else GREY, k * (0.5 + 0.5 * lit), 2.5, glow=lit)
        if lit > 0:
            fr.glow((hx, hy), 50, GOLD, k * 0.25 * lit)
    r = np.random.default_rng(6)
    n = 300
    ph = (r.random(n) + lt * 0.8) % 1.0
    tgt = np.array(HOUSES)[r.integers(0, 7, n)]
    sx = 540 + r.normal(0, 60, n)
    sy = np.full(n, 860.0)
    px = sx * (1 - ph) + tgt[:, 0] * ph
    py = sy * (1 - ph) + (tgt[:, 1] - 40) * ph - 60 * np.sin(np.pi * ph)
    fr.splat(px, py, GOLD_HI, k * np.sin(np.pi * ph) * cl(lt / 0.5) * 0.9)
    fr.splat(px, py, GOLD, k * np.sin(np.pi * ph) * cl(lt / 0.5) * 1.2, layer='B')
    k1 = k * cw('mc_fiscal', t, 0.35, 0.3)
    fr.text('把钱直接送到【需要的地方】', CX, 1260, 62, 'serif_black', 'white', k1, glow=0.3, stagger=(t - 146.0, 0.04, 0.4))
    k2 = k * cw('mc_once', t, 0.35, 0.35)
    fr.text('一次性补贴常被存起来，', CX, 1250, 56, 'serif_bold', 'white', k2, glow=0.2, stagger=(t - 148.5, 0.035, 0.4))
    fr.text('【长期可预期】，才改变预期', CX, 1340, 62, 'serif_black', 'white', k2, glow=0.3, stagger=(t - 148.8, 0.04, 0.45))
    kc = k * win(t, 149.4, 152.0, 0.4, 0.3)
    chip(fr, '时滞：政策见效，往往要几个季度', CX, 1150, kc, GREY, 34, base='white')
    footnote(fr, '来源：2026年政府工作报告；《育儿补贴制度实施方案》（2025年7月）', k)


# ================================================================ 06 真相 152–164
def truth_cam(t):
    lt = t - 152.0
    return Cam((0, 6.0 + lt * 0.25, -52 + lt * 0.5), (0, 0.6, 10 + lt * 0.5), fov=56, cy=H * 0.66)


_UR = np.random.default_rng(19)
RISE_N = 900
RISE_X = _UR.uniform(-48, 48, RISE_N)
RISE_Z = _UR.uniform(-48, 48, RISE_N)
RISE_T = _UR.random(RISE_N) * 6


@scene(152.0, 164.0, 0.4, 0.45)
def sc_truth(fr, t, a):
    lt = t - 152.0
    cam = truth_cam(t)
    sun = ss((t - 156.5) / 2.0)
    warm = np.full(FIELD.n, 0.25 + 0.7 * sun)
    FIELD.draw(fr, cam, t, a * (0.8 + 0.4 * sun), warm=warm, size=1.1)
    hx, hy, _, _ = cam.project([[0, 0, 300]])
    hy = float(hy[0])
    for s_, al in ((1000, 0.10), (420, 0.20), (130, 0.4)):
        fr.glow((CX, hy), s_, GOLD, a * al * (0.3 + 0.7 * sun))
    xs = np.linspace(-80, W + 80, 60)
    fr.stroke(list(zip(xs, np.full(60, hy))), GOLD_HI, a * (0.3 + 0.6 * sun), 2, glow=1.4)
    # 上升的光粒（亿万个选择）
    ph = ((t - 152.0) * 0.25 + RISE_T / 6) % 1.0
    P = np.c_[RISE_X, ph * 14, RISE_Z]
    x, y, z, s = cam.project(P)
    ok = z > 0.5
    fr.splat(x[ok], y[ok], GOLD_HI, (a * np.sin(np.pi * ph) * (0.3 + 0.9 * sun))[ok])
    fr.flash = max(fr.flash, 0.22 * math.exp(-max(t - HITS['keyline'], -9) / 0.12) * (t >= HITS['keyline']) * a)
    draw_dust(fr, t, a * 0.5)
    k = a * cw('tr_1', t, 0.4, 0.35)
    fr.text('宏观经济，', CX, 640, 70, 'serif_bold', 'white', k, glow=0.25, stagger=(t - 152.2, 0.05, 0.45))
    fr.text('不是抽象的数字', CX, 750, 78, 'serif_black', 'white', k, glow=0.3, stagger=(t - 152.5, 0.05, 0.45))
    k = a * cw('tr_2', t, 0.4, 0.35)
    fr.text('是亿万家庭和企业，', CX, 640, 70, 'serif_bold', 'white', k, glow=0.25, stagger=(t - 155.0, 0.05, 0.45))
    fr.text('对【明天】做出的选择', CX, 750, 78, 'serif_black', 'white', k, glow=0.3, stagger=(t - 155.3, 0.05, 0.45))
    k = a * cw('tr_3', t, 0.4, 0.4)
    fr.text('影响经济的，', CX, 520, 54, 'serif_med', 'grey', k, glow=0.2, stagger=(t - 158.0, 0.05, 0.4))
    fr.text('不只是我们今天拥有多少，', CX, 620, 62, 'serif_bold', 'white', k, glow=0.25, stagger=(t - 158.4, 0.04, 0.45))
    fr.text('更是我们', CX, 760, 62, 'serif_bold', 'white', k, glow=0.25, stagger=(t - 159.6, 0.06, 0.45))
    fr.text('【相信明天会发生什么】', CX, 875, 86, 'serif_black', 'white', k, glow=0.5, stagger=(t - 160.0, 0.07, 0.55))
    fr.zoom = 1 + 0.03 * ss(lt / 12)


# ================================================================ 获奖者 164–178
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


@scene(164.0, 178.0, 0.4, 0.35)
def sc_laureates(fr, t, a):
    light_beams(fr, a, t)
    gold_dust(fr, t, a)
    end = 1 - ss((t - 178.0) / 0.5)
    kh = a * cl((t - 164.0) / 0.8) * (1 - ss((t - 177.8) / 0.6))
    fr.text('2026 诺贝尔经济学奖', CX, 228, 42, 'serif_med', 'gold', kh, track=0.26, glow=0.35)
    fr.text('THE SVERIGES RIKSBANK PRIZE IN ECONOMIC SCIENCES IN MEMORY OF ALFRED NOBEL', CX, 280, 20, 'corm_bold',
            'subgold', kh * 0.9, track=0.12, glow=0.1)
    # 单人：霍尔
    for (who, t0, t1, en, zh, cap_key) in (
            ('hall', 164.0, 168.5, 'Robert E. Hall', '罗伯特·霍尔 · 斯坦福大学 · 1943年生', 'la_hall'),
            ('woodford', 168.5, 173.0, 'Michael Woodford', '迈克尔·伍德福德 · 哥伦比亚大学 · 1955年生', 'la_wood')):
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
    # 双人 + 获奖理由
    kb = a * eo((t - 173.0) / 0.8) * end
    if kb > 0.01:
        for j, (who, en, zh) in enumerate((('hall', 'Robert E. Hall', '斯坦福大学'),
                                            ('woodford', 'Michael Woodford', '哥伦比亚大学'))):
            cx = 290 + 500 * j
            kk = kb * eo((t - 173.0 - 0.15 * j) / 0.7)
            portrait_card(fr, who, cx, 620 + (1 - kk) * 30, 440, kk)
            fr.text(en, cx, 885, 44, 'corm_bold', 'gold', kk, glow=0.3)
            fr.text(zh, cx, 935, 28, 'sans_med', 'grey', kk, glow=0)
        kq = a * win(t, 173.4, 178.4, 0.6, 0.3)
        fr.text('“for microeconomic foundations', CX, 1035, 42, 'corm_bold', 'white', kq, glow=0.2)
        fr.text('of macroeconomic stabilisation”', CX, 1088, 42, 'corm_bold', 'white', kq, glow=0.2)
        kc = a * cw('la_cite', t, 0.5, 0.3)
        fr.text('表彰他们为【宏观经济稳定政策】', CX, 1190, 50, 'serif_bold', 'white', kc, glow=0.25,
                stagger=(t - 173.6, 0.035, 0.4))
        fr.text('奠定微观经济学基础', CX, 1262, 50, 'serif_bold', 'white', kc, glow=0.25, stagger=(t - 174.0, 0.04, 0.4))
        fr.text('瑞典皇家科学院 · 2026年10月12日', CX, 1340, 28, 'sans_reg', 'grey', kc, glow=0)
        fr.text('肖像插画：Niklas Elmehed © Nobel Prize Outreach', CX, 1392, 24, 'sans_light', 'dim', kc, glow=0)
    fr.zoom = 1 + 0.02 * ss((t - 164) / 14)


# ================================================================ 品牌片尾 178–188
END_LOGO_PX = 220                      # BRAND.md：片尾 logo 约 220px 居中
LOGO_C = (CX, 800)
K_SCALE = END_LOGO_PX / BR.SPEC['logo_px']          # 以角标规格等比放大，字号/间距均由 brand SPEC 推出
END_LOGO = BR.load_logo(END_LOGO_PX)                # brand/logo_baman.png 原图（预乘 alpha 缩放）


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
    """两张肖像卡（双人构图）上的像素 → 粒子起点与颜色：多取墨线与金箔，让粒子云保留肖像的样子"""
    pts, cols, als = [], [], []
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
        c = c * (1 - g) + np.array([1.0, 0.8, 0.42]) * g
        cols.append(c)
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


@scene(178.0, 188.0, 0.0, 0.0)
def sc_brand(fr, t, a):
    lt = t - 178.0
    draw_dust(fr, t, a * 0.4 * (1 - ss((t - 181) / 2)))
    # 粒子：肖像卡 → 漩涡 → 官方 logo 轮廓
    T_LOGO = HITS['logo']
    u = np.clip((t - 178.0 - P_DEL) / (T_LOGO - 178.0 - P_DEL), 0, 1)
    e = u * u * (3 - 2 * u)
    mid = np.array(LOGO_C)
    # 漩涡中间态
    ang = np.arctan2(P_SRC[:, 1] - mid[1], P_SRC[:, 0] - mid[0]) + 2.6 * e
    rad = np.hypot(P_SRC[:, 0] - mid[0], P_SRC[:, 1] - mid[1]) * (1 - e) + 40 * np.sin(np.pi * e)
    swirl = np.c_[mid[0] + rad * np.cos(ang), mid[1] + rad * np.sin(ang)]
    P = swirl * (1 - e[:, None] ** 3) + P_TGT * e[:, None] ** 3 + P_JIT * 6 * np.sin(np.pi * e)[:, None]
    col = P_SCOL * (1 - e[:, None]) + P_TCOL * e[:, None]
    # logo 出现后，粒子化作四散的微尘
    after = ss((t - T_LOGO - 0.4) / 2.5)
    P = P + P_JIT * 160 * after
    al = a * (1.0 - 0.8 * after) * (1 - ss((t - 184.5) / 1.5)) * ss((t - 177.9) / 0.3)
    if al > 0.01:
        pa = al * (1 - 0.7 * e)          # 越聚越密 → 单颗变暗，避免中心过曝发白
        sz = 0.8 + 1.4 * np.sin(np.pi * e)
        fr.splat(P[:, 0], P[:, 1], col, pa * 0.9)
        fr.dots(P[::6, 0], P[::6, 1], sz[::6], col[::6], pa[::6] * 0.6, layer='B')
        fr.splat(P[:, 0], P[:, 1], col, pa * 0.9, layer='B')
    # 清晰的官方 logo + 淡蓝光晕（BRAND.md：RGB 110,175,255，强度 0.2，σ 随尺寸放大）
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
