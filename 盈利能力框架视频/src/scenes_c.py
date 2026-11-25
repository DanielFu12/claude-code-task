"""场景 C（第二版）：第三层 维持成本、第四层 再投资、第五层 资本与治理、第六层 时间。
主线都回到价值体：削顶（维持）、加厚（再投资）、放大与翻到地板下（杠杆）、衰减与长度（时间）。"""
from common import *
from three import BlockSpec, draw_block, grid_plane, particles3d, Canvas
import legacy_c as LC

DRAW = {}


def reg(name):
    def d(f):
        DRAW[name] = f
        return f
    return d


def gated(fr, k, fn, *args):
    if k <= 0.003: return
    old = fr.k
    fr.k = old * k
    fn(*args)
    fr.k = old


def stage(fr, cam, a, col=RED):
    fr.k = a
    grid_plane(fr, cam, 0, x0=-2, x1=30, z0=-12, z1=12, step=1, col=col, a=0.42, fog=80)


# ================================================================ 第三层：维持成本
@reg('L2')
def L2(fr, S):
    t = fr.t
    a0 = S.fade_out(0.4)
    # 回到开头的喜诗糖果：维持几乎不花钱
    kS = S.a('see', 0.6) * (1 - S.a('oe', 0.5))
    if kS > 0:
        cam = keycam(t, [(S.start, ((0, 6, 0), 40, 0.4, 0.12, 42)), (S.c('oe'), ((0, 6, 0), 34, 0.2, 0.1, 42))])
        stage(fr, cam, kS * a0, ICE)
        draw_block(fr, cam, BlockSpec(T=2, h0=13, d0=2, disc=0), t, origin=(-1, 0, 0))
        ck = S.a('cheap', 0.5)
        if ck > 0:
            draw_block(fr, cam, BlockSpec(T=2, h0=0.35, d0=2.05, disc=0, col=ORANGE), t, origin=(-1, 13 + 0.6 * (1 - ck), 0), particles=False)
        fr.k = 1.0
        headline(fr, '还记得喜诗糖果吗？', 560, 300, 56, GOLD, kS * a0)
        if ck > 0:
            fr.text('维持这份回报，几乎不花钱', 560, 380, 36, 'sans_bold', ORANGE, ck * kS * a0)
    # 所有者盈余（旧组件的瀑布图）
    kO = S.a('oe', 0.5) * (1 - S.a('shave', 0.5))
    gated(fr, kO * a0, LC.L2, fr, remap(S, see=FAR, s1=FAR, s2=FAR, s3=FAR, gap=FAR))
    # 价值体被削顶：喜诗薄薄一片，芯片厂厚厚一层
    kV = S.a('shave', 0.6)
    if kV > 0:
        cam = keycam(t, [(S.c('shave'), ((10, 2.5, 0), 40, 0.7, 0.3, 40)), (S.end, ((10, 2.5, 0), 44, 0.45, 0.26, 40))])
        a = kV * a0 * (1 - S.a('next', 0.5))
        stage(fr, cam, a)
        fab = S.a('fab', 1.0, eio)
        thin = S.a('thin', 0.6)
        # 上：喜诗（z 往后），下：芯片厂（z 往前）
        hs = 3.2
        peel_s = 0.25
        B1 = BlockSpec(T=20, h0=hs - peel_s * cl(S.a('shave', 1.2, off=0.6)), d0=3, disc=0.04)
        draw_block(fr, cam, B1, t, origin=(0, 0, -4.5))
        lift = S.a('shave', 1.6, eio, off=0.6)
        if 0 < lift < 1:
            fr.k = a * (1 - lift)
            draw_block(fr, cam, BlockSpec(T=20, h0=peel_s, d0=3, disc=0.04, col=ORANGE), t, origin=(0, hs - peel_s + lift * 2.5, -4.5), particles=False)
            fr.k = a
        if fab > 0:
            pf = 2.3
            B2 = BlockSpec(T=20, h0=hs - pf * cl(S.a('gap', 1.2)), d0=3, disc=0.04, col=GOLD)
            fr.k = a * fab
            draw_block(fr, cam, B2, t, origin=(0, 0, 4.5))
            lg = S.a('gap', 1.8, eio)
            if lg < 1:
                fr.k = a * fab * (1 - lg)
                draw_block(fr, cam, BlockSpec(T=20, h0=pf, d0=3, disc=0.04, col=ORANGE), t, origin=(0, hs - pf + lg * 3.5, 4.5), particles=False)
            fr.k = a
        fr.k = 1.0
        P, Z = cam.project(np.array([[20, hs, -4.5], [20, 1.2, 4.5]]))
        if thin > 0:
            fr.text('喜诗：削掉薄薄一片', P[0][0] + 30, P[0][1] - 20, 34, 'sans_black', GOLD2, a * thin, anchor='l', glow=0.2)
        if fab > 0:
            fr.text('芯片制造：维持开支 > 会计折旧', P[1][0] + 30, P[1][1] + 10, 34, 'sans_black', ORANGE, a * fab, anchor='l', glow=0.2)
        gk = S.a('gap', 0.6, off=1.2)
        if gk > 0:
            headline(fr, '报表利润 ≠ 所有者盈余', W / 2, 200, 60, ORANGE, a * gk)
        else:
            headline(fr, '维持成本 = 从顶上削掉的一层', W / 2, 200, 56, ORANGE, a)
    bridge(fr, S, 'next', '剩下的钱，怎么办？', TEAL)


# ================================================================ 第四层：再投资
@reg('L3')
def L3(fr, S):
    t = fr.t
    a0 = S.fade_out(0.4)
    th = S.a('thick', 0.6)
    ax = S.a('axes', 0.6)
    # 巴菲特 1992 名言（旧组件里的引言部分）
    gated(fr, a0 * (1 - th), LC.L3, fr, remap(S, axes=FAR))
    # 价值体越做越厚
    kT = th * (1 - ax)
    if kT > 0:
        cam = keycam(t, [(S.c('thick'), ((10, 2, 0), 40, 0.25, 0.42, 40)), (S.c('axes'), ((11, 2, 0), 44, 0.55, 0.5, 40))])
        stage(fr, cam, kT * a0, TEAL)
        g = S.a('thick', 2.5, eio)
        draw_block(fr, cam, BlockSpec(T=20, h0=3.0, d0=2.5, grow=0.075 * g, disc=0.03, col=GOLD), t)
        fr.k = 1.0
        headline(fr, '复利 = 厚度一年比一年大', W / 2, 200, 60, TEAL, kT * a0)
    # 回报 × 容量 × 强制性 立方体（旧组件）
    if ax > 0:
        gated(fr, ax * a0, LC.L3, fr, remap(S, k3=FAR, k4=FAR))


@reg('kitty')
def kitty(fr, S):
    gated(fr, 1 - S.a('next', 0.4), LC.kitty, fr, remap(S, cow2=FAR))
    bridge(fr, S, 'next', '钱从哪来？谁来分配？', C(110, 170, 255))


# ================================================================ 第五层：资本与治理
@reg('L4')
def L4(fr, S):
    t = fr.t
    a0 = S.fade_out(0.4)
    kL = S.a('amp', 0.6) * (1 - S.a('fl', 0.5))
    if kL > 0:
        cam = keycam(t, [(S.start, ((10, 1, 0), 42, 0.65, 0.18, 40)), (S.c('fl'), ((10, 1, 0), 38, 0.45, 0.14, 40))])
        a = kL * a0
        stage(fr, cam, a, C(255, 120, 120))
        lev = 1 + 0.8 * S.a('lev', 1.0, eio)
        rk = S.a('risk', 1.4, eio)
        # 经营：同样的生意（后排）；杠杆：被放大的同一个生意（前排）
        base = BlockSpec(T=20, h0=1.8 - 0.5 * rk, d0=3, cyc=1.9 * rk, cyc_f=0.16, disc=0.03, col=TEAL, neg_col=RED)
        draw_block(fr, cam, base, t, origin=(0, 0, -4))
        levd = base.copy(lev=lev, col=C(110, 170, 255))
        if lev > 1.01:
            draw_block(fr, cam, levd, t, origin=(0, 0, 4))
        fr.k = 1.0
        P, Z = cam.project(np.array([[0, 1.8, -4], [0, 1.8 * lev, 4]]))
        fr.text('经营本身', P[0][0] - 24, P[0][1] - 20, 32, 'sans_black', TEAL, a, anchor='r')
        if lev > 1.01:
            fr.text('加了杠杆', P[1][0] - 24, P[1][1], 32, 'sans_black', C(140, 190, 255), a * S.a('lev', 0.5), anchor='r')
        headline(fr, '只放大，不创造', W / 2, 190, 68, C(110, 170, 255), a)
        if rk > 0:
            fr.text('好时更好，坏时跌穿地板', W / 2, 270, 36, 'sans_bold', C(255, 150, 150), a * cl(rk * 2))
    # 浮存金、回购（旧组件）
    kF = S.a('fl', 0.5)
    if kF > 0:
        gated(fr, kF * a0, LC.L4, fr, remap(S, amp=-FAR, bridge=-FAR))


@reg('gov')
def gov(fr, S):
    gated(fr, 1 - S.a('next', 0.4), LC.gov, fr, S)
    bridge(fr, S, 'next', '最难的变量：时间', VIOLET)


# ================================================================ 第六层：时间
@reg('L5')
def L5(fr, S):
    t = fr.t
    a0 = S.fade_out(0.4)
    kF = S.a('fade', 0.6) * (1 - S.a('cyc', 0.5))
    if kF > 0:
        cam = keycam(t, [(S.start, ((14, 2, 0), 50, 0.55, 0.3, 40)), (S.c('cyc'), ((16, 2, 0), 54, 0.4, 0.26, 40))])
        a = kF * a0
        stage(fr, cam, a, VIOLET)
        ext = S.a('fade', 2.5, eio)
        slow = BlockSpec(T=30, h0=3.4, d0=3, fade=0.05, disc=0.03, extend=ext, col=GOLD)
        fast = BlockSpec(T=30, h0=3.4, d0=3, fade=0.35, disc=0.03, extend=ext, col=C(255, 120, 120))
        draw_block(fr, cam, slow, t, origin=(0, 0, -3.5))
        draw_block(fr, cam, fast, t, origin=(0, 0, 3.5))
        fr.k = 1.0
        P, Z = cam.project(np.array([[30 * ext, 0.8, -3.5], [8, 0.3, 3.5]]))
        sk = S.a('slow', 0.5)
        fr.text('回落得慢：延伸得远', P[0][0] + 20, P[0][1] - 40, 34, 'sans_black', GOLD, a * sk, anchor='l', glow=0.2)
        fr.text('回落得快', P[1][0], P[1][1] + 60, 34, 'sans_black', C(255, 150, 150), a * sk)
        ck = S.a('cap', 0.6)
        if ck > 0:
            Q, _ = cam.project(np.array([[0, 0, -6], [24, 0, -6]]))
            fr.line(tuple(Q[0]), tuple(Q[0] + (Q[1] - Q[0]) * ck), VIOLET, a, 4)
            headline(fr, '竞争优势期', W / 2, 190, 68, VIOLET, a * ck)
        else:
            headline(fr, '超额回报，终会回落', W / 2, 190, 60, VIOLET, a)
    kR = S.a('cyc', 0.5)
    if kR > 0:
        gated(fr, kR * a0, LC.L5, fr, remap(S, fade=FAR, fade2=FAR))
