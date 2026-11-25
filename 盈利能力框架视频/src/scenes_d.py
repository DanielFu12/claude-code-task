"""场景 D（第二版）：六层合一（价值体形变对比）、八步流程（穿越光环）、五个测试、五条规则、结语、片尾。"""
from common import *
import three as T3
from three import BlockSpec, draw_block, grid_plane, particles3d
import legacy_d as LD
import scenes_a as SA

DRAW = {}
LD.QLINES = ['伟大的企业，能以合理的代价，', '守住一块别人拿不走的价值，', '并在机会出现时，', '把资本变成更高的每股价值。',
             '而且这一切，是你能够理解、能够判断的。']
RNG = np.random.default_rng(909)
VORT = RNG.random((900, 3))


def reg(name):
    def d(f):
        DRAW[name] = f
        return f
    return d


# ================================================================ 六层合一
PAIRS = [
    ('c1', 'c2', '技术领先 + 生态锁定', '价值一直延伸', '技术领先，没有锁定', '停不下来的跑步机',
     BlockSpec(T=28, h0=3.2, d0=3, fade=0.015), BlockSpec(T=28, h0=2.2, d0=2, fade=0.22, grow=0.07)),
    ('c3', 'c4', '现金牛 + 优秀的配置者', '伯克希尔', '现金牛 + 糟糕的配置者', '价值黑洞',
     BlockSpec(T=28, h0=2.6, d0=3, fade=0.0, grow=0.05), BlockSpec(T=28, h0=2.6, d0=3, fade=0.0)),
    ('c5', 'c6', '强周期 + 低成本 + 低杠杆', '底部收割对手', '强周期 + 高杠杆', '迟早出局',
     BlockSpec(T=28, h0=2.4, d0=3, cyc=1.2, cyc_f=0.14), BlockSpec(T=28, h0=1.0, d0=3, cyc=1.2, cyc_f=0.14, lev=2.2)),
]


@reg('combo')
def combo(fr, S):
    t = fr.t
    a0 = S.fade_out(0.4)
    cam = keycam(t, [(S.start, ((14, 2, 0), 54, 0.5, 0.3, 40)), (S.c('c1') - 0.4, ((14, 2, 0), 50, 0.62, 0.32, 40)),
                     (S.end, ((14, 2, 0), 52, 0.4, 0.28, 40))])
    fr.k = a0
    grid_plane(fr, cam, 0, x0=-2, x1=30, z0=-12, z1=12, step=1, col=GOLD, a=0.38, fog=90)
    fr.k = 1.0
    kA = S.a('all', 0.6) * (1 - S.a('c1', 0.4, off=-0.5))
    if kA > 0:
        fr.k = kA * a0
        B = BlockSpec(T=24, h0=3.6, d0=4, grow=0.03, disc=0.04)
        draw_block(fr, cam, B, t)
        fr.k = 1.0
        SA.map_labels(fr, cam, B, S, [S.c('all') + 0.15 * i for i in range(6)], kA * a0, t)
        headline(fr, '六层合一', W / 2, 190, 76, GOLD, kA * a0)
    for i, (cg, cb, g1, g2, b1, b2, BG, BB) in enumerate(PAIRS):
        t_in = S.c(cg) - 0.4
        t_out = PAIRS[i + 1][0] if i < 2 else None
        t_out = S.c(t_out) - 0.45 if t_out else S.end + 1
        if t < t_in or t > t_out + 0.4: continue
        a = a0 * cl((t - t_in) / 0.4) * (1 - cl((t - t_out) / 0.4))
        fr.k = a
        gk = S.a(cg, 1.2, eio)
        bk = S.a(cb, 1.6, eio)
        bg = BG.copy(extend=gk, col=GOLD)
        draw_block(fr, cam, bg, t, origin=(0, 0, -4.5))
        bb = BB.copy(extend=gk, col=lerpc(GOLD, RED, bk), neg_col=RED)
        if i == 1 and bk > 0:
            bb.h0 = 2.6 * (1 - bk) - 0.6 * bk
        if i == 2 and bk > 0:
            bb.cut = lerp(28, 9, cl(bk * 2))
            bb.shatter = cl((t - S.c(cb) - 0.8) / 2.0)
        fr.k = a * S.a(cb, 0.5)
        draw_block(fr, cam, bb, t, origin=(0, 0, 4.5))
        fr.k = a
        if i == 1:
            ph = (t * 0.5 + VORT[:, 0]) % 1.0
            P = np.stack([10 + ph * 16, 3 + np.sin(ph * 3.14) * 4, -4.5 + (VORT[:, 1] - 0.5) * 2], 1)
            particles3d(fr, cam, P, GOLD2, gk * 0.7 * np.sin(ph * np.pi), 1)
            if bk > 0:
                ang = VORT[:, 1] * 6.28 + t * 2.5
                r = (1 - ((t * 0.4 + VORT[:, 2]) % 1.0)) * 6
                P = np.stack([14 + np.cos(ang) * r, 1.5 + np.sin(ang) * r * 0.3, 4.5 + np.sin(ang) * r], 1)
                particles3d(fr, cam, P, RED, bk * 0.8, 1)
        fr.k = 1.0
        headline(fr, g2, 1280, 190, 64, GOLD, a * S.a(cg, 0.4))
        fr.text(g1, 1280, 260, 34, 'sans_bold', GOLD2, a * S.a(cg, 0.4))
        draw_icon(fr, 'check', 900, 190, 56, GOLD, a * S.a(cg, 0.4), 5)
        if bk > 0:
            headline(fr, b2, 620, 870, 64, RED, a * S.a(cb, 0.4))
            fr.text(b1, 620, 800, 34, 'sans_bold', C(255, 160, 160), a * S.a(cb, 0.4))
            draw_icon(fr, 'cross', 1000, 870, 56, RED, a * S.a(cb, 0.4), 5)
        fr.text(f'{i + 1} / 3', 140, 240, 30, 'orb', GOLD2, a, anchor='l', mode='E')
        for c in (cg, cb):
            pl = pulse(t, S.c(c), 0.25)
            fr.zoom *= 1 + 0.02 * pl
            fr.ca = max(fr.ca, 4 * pl)


# ================================================================ 八步：穿越光环
STEPS = [('排雷', RED), ('价值杆', C(255, 200, 90)), ('拆开回报', C(255, 200, 90)), ('维持成本', ORANGE),
         ('再投资', TEAL), ('资本与治理', C(90, 170, 255)), ('时间', VIOLET), ('估值', GOLD)]


@reg('proc')
def proc(fr, S):
    t = fr.t
    a0 = S.fade_out(0.4)
    gap = 12.0
    cues = [S.c(f'p{i + 1}') for i in range(8)]
    zt = float(np.interp(t, [S.start] + cues + [S.end], [16] + [-gap * i + 9 for i in range(8)] + [-gap * 7 + 4]))
    cam = T3.Cam((0.6 * math.sin(t * 0.7), 0.4 + 0.3 * math.cos(t * 0.5), zt), (0, 0, zt - 20), 60)
    fr.k = a0
    grid_plane(fr, cam, -3, x0=-14, x1=14, z0=-100, z1=20, step=2, col=CYAN, a=0.3, fog=40)
    fr.k = 1.0
    for i, (nm, col) in enumerate(STEPS):
        zc = -gap * i
        lit = t >= cues[i] - 0.05
        k = pulse(t, cues[i], 0.5)
        n = 64
        ts = np.linspace(0, 2 * np.pi, n)
        R = 4.2 if i < 7 else 5.5
        P = np.stack([np.cos(ts) * R, np.sin(ts) * R, np.full(n, zc)], 1)
        Q, Z = cam.project(P)
        if (Z < 0.5).any(): continue
        zz = Z.mean()
        fog = math.exp(-zz / 70)
        c2 = col if lit else lerpc(GREY, col, 0.45)
        al = a0 * fog * (1.0 if lit else 0.6)
        fr.poly(Q, c2, al, 4 if lit else 2, closed=True)
        if lit:
            fr.poly(Q, lerpc(col, WHITE, 0.5), al * (0.3 + 0.7 * k), 8, closed=True)
            fr.glow(tuple(Q.mean(0)), 30 / max(zz / 20, 0.3), col, al * 0.6 * k)
        T3.text3d(fr, f'{i + 1}', (0, R + 1.2, zc), cam, 56, 'orb', c2, al, mode='E', glow=0.4)
        T3.text3d(fr, nm, (0, 0, zc), cam, 60, 'sans_black', lerpc(c2, WHITE, 0.4), al, glow=0.2)
    fr.text('八个步骤', 140, 240, 32, 'serif_black', CYAN, a0 * S.a('p0', 0.5), anchor='l', glow=0.3)
    if t >= cues[7]:
        slam(fr, '最后，才是估值', cues[7], W / 2, 220, 80, GOLD, a=a0)


@reg('tests')
def tests(fr, S):
    LD.tests(fr, S)


@reg('rules')
def rules(fr, S):
    LD.rules(fr, S)


@reg('quote')
def quote(fr, S):
    LD.quote(fr, S)


@reg('outro')
def outro(fr, S):
    LD.outro(fr, S)
