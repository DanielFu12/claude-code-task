"""场景 B（第二版）：第一层 生存（价值体被截断）、第二层 价值杆 / 织布机 / 护城河 / 周期陷阱。"""
from common import *
import three as T3
from three import BlockSpec, draw_block, grid_plane, particles3d
import legacy_b as LB

RNG = np.random.default_rng(77)
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


# ================================================================ 第一层：生存
@reg('L0')
def L0(fr, S):
    t = fr.t
    a0 = S.fade_out(0.4)
    slam(fr, '会不会死', S.c('die'), W / 2, 720, 140, RED, out=S.c('m') - 0.2)
    kA = S.a('m', 0.3) * (1 - S.a('knife', 0.5))
    gated(fr, kA * a0, LB.L0, fr, remap(S, d1=FAR, d2=FAR, bf=FAR, air=FAR, veto=FAR))
    kB = S.a('knife', 0.6) * (1 - S.a('d1', 0.5))
    if kB > 0:
        cam = keycam(t, [(S.c('knife'), ((8, 2, 0), 36, 0.85, 0.30, 40)), (S.c('d1'), ((6, 2, 0), 30, 0.6, 0.22, 40))])
        fr.k = kB * a0
        grid_plane(fr, cam, 0, x0=-2, x1=26, z0=-8, z1=8, step=1, col=RED, a=0.45, fog=70)
        B = BlockSpec(T=20, h0=3.4, d0=4.0, disc=0.04, grow=0.02)
        kc = S.c('k2')
        drop = cl((t - (kc - 0.5)) / 0.5)
        if t >= kc:
            B.cut = 3.0
            B.shatter = cl((t - kc) / 2.6)
        draw_block(fr, cam, B, t)
        if drop > 0:
            y = 9 - 9 * eio(drop)
            P, Z = cam.project(np.array([[3, y + 0.05, -5], [3, y + 0.05, 5], [3, 9, 5], [3, 9, -5]]))
            al = 1 - cl((t - kc - 0.3) / 0.8)
            fr.line(tuple(P[0]), tuple(P[1]), RED, al, 5)
            fr.fillpoly([tuple(p) for p in P], RED, 0.18 * al, 'E')
            fr.flash = max(fr.flash, 0.25 * pulse(t, kc, 0.08))
            fr.shake = (8 * pulse(t, kc, 0.12) * math.sin(t * 90), 0)
        fr.k = 1.0
        ka = S.a('k2', 0.5, off=0.5)
        if ka > 0:
            fr.text('第 3 年倒下', 560, 250, 48, 'sans_black', C(255, 140, 140), ka * kB * a0, glow=0.3)
            slam(fr, '之后全部归零', S.c('k2') + 1.0, 1320, 250, 64, RED, a=kB * a0)
    kC = S.a('d1', 0.5)
    if kC > 0:
        d4 = S.c('d4')
        S2 = remap(S, m=-FAR, d5=d4 + 0.7, d6=d4 + 1.4, d7=S.c('d5'), bf=FAR, air=FAR)
        gated(fr, kC * a0 * (1 - S.a('next', 0.5)), LB.L0, fr, S2)
    bridge(fr, S, 'next', '钱，到底从哪里来？', GOLD)


# ================================================================ 第二层：价值杆、织布机
@reg('stick')
def stick(fr, S):
    c3 = S.c('cut3')
    LB.stick(fr, remap(S, p=c3, c=c3 + 0.6))


@reg('loom')
def loom(fr, S):
    LB.loom(fr, S)


# ================================================================ 护城河
RING = ['品牌', '转换成本', '网络效应', '有效规模', '规模经济']
ATK = RNG.random((260, 3))


@reg('moat')
def moat(fr, S):
    t = fr.t
    a0 = S.fade_out(0.4)
    kM = S.a('moat', 0.6) * (1 - S.a('r1', 0.5, off=-0.4))
    if kM > 0:
        a = kM * a0
        cx, cy = 760, 560
        headline(fr, '护城河', cx, 190, 72, GOLD, a)
        core = 70 + 6 * kick_pulse(t)
        pts = [(cx + core * math.cos(k * math.pi / 3 + math.pi / 6), cy + core * 0.8 * math.sin(k * math.pi / 3 + math.pi / 6)) for k in range(6)]
        fr.fillpoly(pts, GOLD, a * 0.35, 'E')
        fr.poly(pts, GOLD2, a, 3, closed=True)
        fr.text('附加值', cx, cy, 30, 'sans_black', WHITE, a)
        R, ry = 340, 0.52
        for i, nm in enumerate(RING):
            try:
                tw = S.w(nm)
            except KeyError:
                tw = S.c('g') + i * 0.6
            on = ramp(t, tw, 0.4, eback)
            a1 = -math.pi / 2 + i * 2 * math.pi / 5 + 0.08
            a2 = a1 + 2 * math.pi / 5 - 0.16
            ts = np.linspace(a1, a2, 30)
            col = [GOLD, CYAN, VIOLET, BLUE, TEAL][i]
            ring = np.stack([cx + R * np.cos(ts), cy + R * ry * np.sin(ts)], 1)
            fr.poly(ring, GREY, a * 0.25, 10)
            if on > 0:
                fr.poly(ring, col, a * cl(on), 10)
                fr.glow(tuple(ring[15]), 40, col, a * pulse(t, tw, 0.4))
                am = (a1 + a2) / 2
                lx, ly = cx + (R + 120) * math.cos(am), cy + (R * ry + 70) * math.sin(am)
                fr.text(nm, lx, ly, int(34 * (1 + 0.25 * pulse(t, tw, 0.4))), 'sans_black', lerpc(col, WHITE, 0.4), a * cl(on), glow=0.25)
        ph = (t * 0.35 + ATK[:, 0]) % 1.0
        ang = ATK[:, 1] * 6.28
        rr = 520 - 300 * np.minimum(ph * 1.6, 1) + 300 * np.maximum(ph * 1.6 - 1, 0) * 1.6
        x = cx + rr * np.cos(ang); y = cy + rr * ry * np.sin(ang)
        fr.dots(x, y, RED, a * 0.55 * np.sin(ph * np.pi), 1)
        pk = S.a('px', 0.5, eback)
        if pk > 0:
            ka = cl(pk) * a
            draw_icon(fr, 'tag', 1450, 430, 200, GOLD, ka, 4)
            pr = 100 * (1 + 0.15 * eo((t - S.c('px') - 0.3) / 1.5))
            fr.text(f'¥ {pr:.0f}', 1450, 620, 84, 'sans_black', GOLD2, ka, mode='E', glow=0.35)
            headline(fr, '能否经常大胆提价', 1450, 730, 44, GOLD, ka)
    kR = S.a('r1', 0.4, off=-0.4) * (1 - S.a('trap', 0.5))
    if kR > 0:
        S2 = remap(S, fr=-FAR, px=-FAR, g=-FAR, rule=S.c('r1') - 0.4, rule1=S.c('r1'), rule2=S.c('r2'))
        gated(fr, kR, LB.moat, fr, S2)
    kT = S.a('trap', 0.5) * (1 - S.a('next', 0.5))
    if kT > 0:
        S3 = remap(S, eq=S.c('peak'), avg=S.c('base'), mid=FAR)
        gated(fr, kT, LB.cycle, fr, S3)
    bridge(fr, S, 'next', '保住它，要花多少钱？', ORANGE)
