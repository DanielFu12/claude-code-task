"""场景 A（第二版）：冷开场（印钞机 vs 碎钞机）、标题、公式、价值体、六层地图。"""
from common import *
import three as T3
from three import BlockSpec, draw_block, grid_plane, text3d, particles3d, axis_arrow, block_point
import legacy_a as LA

RNG = np.random.default_rng(2026)
DRAW = {}


def reg(name):
    def d(f):
        DRAW[name] = f
        return f
    return d


def label3d(fr, cam, P, s, col, a, size=34, dx=60, dy=-50, sub=None):
    """3D 锚点 + 引线 + 2D 标签"""
    if a <= 0.01: return
    p, z = cam.project(np.asarray(P)[None])
    if z[0] < 0.5: return
    x, y = p[0]
    q = (x + dx, y + dy)
    fr.disc((x, y), 4, col, a)
    fr.glow((x, y), 12, col, a * 0.7)
    fr.poly([(x, y), q, (q[0] + (30 if dx > 0 else -30), q[1])], col, a * 0.7, 2)
    anc = 'l' if dx > 0 else 'r'
    tx = q[0] + (40 if dx > 0 else -40)
    fr.text(s, tx, q[1], size, 'sans_black', lerpc(col, WHITE, 0.45), a, anchor=anc, glow=0.2)
    if sub:
        fr.text(sub, tx, q[1] + size * 0.95, int(size * 0.62), 'sans_med', lerpc(col, WHITE, 0.3), a * 0.9, anchor=anc)


# ================================================================ 冷开场：印钞机 vs 碎钞机
FOUNT = RNG.random((1600, 4))
RAIN = RNG.random((1400, 4))


@reg('hook')
def hook(fr, S):
    t = fr.t
    a0 = 1.0
    # 相机：先看喜诗（左），塔升起时上仰后退，再平移到航空（右），最后拉远看两者
    cam = keycam(t, [
        (0.0, ((-6, 1.5, 0), 26, 0.55, 0.10, 42)),
        (9.0, ((-6, 1.5, 0), 20, 0.35, 0.12, 42)),
        (14.0, ((-6, 2.5, 0), 22, 0.25, 0.10, 42)),
        (18.5, ((-6, 13, 0), 52, 0.15, 0.08, 42)),
        (21.5, ((7, 3, 0), 30, -0.25, 0.22, 42)),
        (29.5, ((7, 3, 0), 26, -0.35, 0.25, 42)),
        (32.0, ((0.5, 10, 0), 62, 0.0, 0.10, 42)),
        (38.0, ((0.5, 10, 0), 70, 0.05, 0.12, 42)),
    ])
    dim = 1 - 0.8 * S.a('why', 0.6)
    gone = 1 - S.a('today', 1.2)
    a = dim * gone
    if a > 0.01:
        fr.k = a
        grid_plane(fr, cam, 0, x0=-20, x1=22, z0=-14, z1=14, step=2, col=ICE, a=0.35, fog=90, major=5)
        # 喜诗糖果：小金块 + 追加资本薄片 + 冲天的利润塔
        k1 = S.a('see', 0.8, eback)
        if k1 > 0:
            B = BlockSpec(T=2.0, h0=1.6 * cl(k1), d0=2.0, disc=0, col=GOLD)
            draw_block(fr, cam, B, t, origin=(-7, 0, 0), particles=False)
            label3d(fr, cam, (-6, 1.6, 1), '喜诗糖果 · 1972', GOLD2, a * cl(k1), 34, -80, -120, '买入价 2500 万美元')
        k2 = S.a('see2', 0.6, eback)
        if k2 > 0:
            B2 = BlockSpec(T=2.0, h0=0.5 * cl(k2), d0=2.0, disc=0, col=TEAL)
            draw_block(fr, cam, B2, t, origin=(-7, 1.6, 0), particles=False)
            label3d(fr, cam, (-5, 2.1, 1), '+3200 万', TEAL, a * cl(k2), 34, 90, -40, '35 年追加的资本')
        k3 = S.a('see3', 3.2, eio)
        if k3 > 0:
            hgt = 2.1 + 22 * k3
            B3 = BlockSpec(T=2.0, h0=hgt, d0=2.0, disc=0, col=GOLD)
            draw_block(fr, cam, B3, t, origin=(-7, 0, 0), particles=True)
            # 顶部喷泉
            ph = (t * 0.6 + FOUNT[:, 0]) % 1.0
            ang = FOUNT[:, 1] * 6.28
            r = ph * (2 + 4 * FOUNT[:, 2])
            P = np.stack([-6 + np.cos(ang) * r, hgt + ph * 5 - ph * ph * 7, np.sin(ang) * r], 1)
            particles3d(fr, cam, P, GOLD2, a * (1 - ph) * cl(k3 * 3) * 0.9, 1)
            v = 13.5 * k3
            fr.k = 1.0
            fr.text(f'{v:.1f} 亿美元', 560, 300, 92, 'sans_black', GOLD, a * cl(k3 * 4) * (1 - S.a('air', 0.6)), mode='E', glow=0.45)
            fr.text('累计税前利润', 560, 390, 34, 'sans_bold', GOLD2, a * cl(k3 * 4) * (1 - S.a('air', 0.6)))
            fr.text('约 54 倍', 560, 450, 30, 'serif_black', GOLD2, a * S.a('see3', 0.5, off=2.5) * (1 - S.a('air', 0.6)))
            fr.k = a
        # 航空：资本像雨一样落进来，又被碾碎
        ka = S.a('air', 0.8, eback)
        if ka > 0:
            B4 = BlockSpec(T=8.0, h0=0.25, d0=7.0 * cl(ka), disc=0, col=RED, neg_col=RED)
            draw_block(fr, cam, B4, t, origin=(3, 0, 0), particles=False)
            ph = (t * 0.8 + RAIN[:, 0]) % 1.0
            P = np.stack([3 + RAIN[:, 1] * 8, 14 * (1 - ph) + 0.3, (RAIN[:, 2] - 0.5) * 7], 1)
            particles3d(fr, cam, P, C(150, 220, 255), a * cl(ka) * 0.8 * np.minimum(1, (1 - ph) * 4), 1)
            # 被碾碎：落到底部变成红色碎屑横向飞散
            ph2 = (t * 0.8 + RAIN[:, 3]) % 1.0
            P2 = np.stack([3 + RAIN[:, 1] * 8 + (RAIN[:, 2] - 0.5) * 6 * ph2, 0.3 + ph2 * 0.6, (RAIN[:, 2] - 0.5) * 7 + (RAIN[:, 0] - .5) * 8 * ph2], 1)
            particles3d(fr, cam, P2, RED, a * cl(ka) * 0.6 * (1 - ph2), 1)
            fr.k = 1.0
            la = a * (1 - S.a('vs', 0.5))
            items = [('增长迅速', S.w('增长迅速')), ('需要大量资本', S.w('需要大量资本')), ('几乎不赚钱', S.w('几乎不赚钱'))]
            for i, (s, tw) in enumerate(items):
                kk = ramp(t, tw, 0.4, eback)
                label_pill(fr, s, 1320, 300 + i * 90, RED if i == 2 else C(150, 220, 255), la * cl(kk), 38, 'sans_black', 26)
            ka2 = S.a('air2', 0.5)
            if ka2 > 0:
                draw_icon(fr, 'plane', lerp(1100, 1700, S.a('air2', 2.5, eio)), 640, 150, ICE, la * ka2, 3)
                fr.text('想想航空公司', 1320, 560, 46, 'serif_black', ICE, la * ka2, glow=0.25)
            fr.k = a
        # 印钞机 / 碎钞机
        kv = S.a('vs', 0.4)
        if kv > 0:
            fr.k = 1.0
            slam(fr, '印钞机', S.c('vs'), 380, 200, 96, GOLD, a=a)
            slam(fr, '碎钞机', S.c('vs') + 1.25, 1540, 200, 96, RED, a=a)
            fr.k = a
        fr.k = 1.0
    # 问题
    if S.a('why', 0.3) > 0:
        slam(fr, '差别，究竟在哪里？', S.c('why'), W / 2, 500, 100, WHITE, a=1 - S.a('today', 0.8))
    # 粒子汇聚 -> 标题
    p = cl((t - S.c('today')) / (45.85 - S.c('today')))
    if p > 0:
        e = p ** 1.6
        r = LA.SP_R * (1 - e) ** 1.4 + 2
        ang = LA.SP_A + e * 5.0 * LA.SP_S + t * 0.3
        x = W / 2 + np.cos(ang) * r
        y = 520 + np.sin(ang) * r * 0.62
        fr.dots(x, y, LA.SP_C, cl(p * 3) * (0.5 + 0.8 * e) * 0.8, 1)
        fr.glow((W / 2, 520), 20 + 60 * e, GOLD, 0.25 + 0.9 * e ** 3)
        fr.glow((W / 2, 520), 8 + 14 * e, WHITE, 0.2 + 1.5 * e ** 4, 'E')
        typeline(fr, '一张完整的地图', W / 2, 760, 40, GOLD2, (1 - e) * cl(p * 4), S.c('today') + 2.5, 8, 'serif_med')
        if t > 45.5:
            fr.flash = max(fr.flash, ei((t - 45.5) / 0.4) * 0.15)


# ================================================================ 标题
@reg('title')
def title(fr, S):
    t = fr.t
    lt = S.lt
    cx, cy = W / 2, 400
    ra = cl(lt / 0.3) * (0.10 + 0.05 * kick_pulse(t)) * S.fade_out(0.6)
    light_rays(fr, (cx, cy), 18, 1300, GOLD, ra, t, 0.035)
    form = eio((lt - 0.25) / 1.1)
    burst = eo(lt / 0.35)
    if lt < 2.2:
        bx = cx + np.cos(LA.TP_A) * LA.TP_V * burst * (1 - form)
        by = cy + np.sin(LA.TP_A) * LA.TP_V * burst * (1 - form) * 0.6
        x = bx * (1 - form) + (cx + LA.TP_X) * form
        y = by * (1 - form) + (cy + LA.TP_Y) * form
        fr.splat(x, y, LA.TP_C, (1 - eio((lt - 1.4) / 0.8)) * 0.9, 'E')
    sa = eio((lt - 1.1) / 0.7) * S.fade_out(0.6)
    if sa > 0:
        headline(fr, LA.TITLE, cx, cy, 124, GOLD, sa, glow=0.45, track=0.06)
    st = cl(lt / 0.9)
    if st < 1:
        fr.fillpoly([(cx - 900, cy - 3), (cx + 900, cy - 3), (cx + 900, cy + 3), (cx - 900, cy + 3)], GOLD2, (1 - st) * 0.9, 'E')
        fr.glow((cx, cy), 60, WHITE, (1 - st) * 1.2)
    a2 = ramp(t, S.start + 1.4, 0.6) * S.fade_out(0.6)
    fr.text('A  FRAMEWORK  FOR  BUSINESS  PROFITABILITY', cx, cy - 115, 24, 'corm', GOLD2, a2 * 0.85, track=0.25)
    w = 560 * eo((lt - 1.3) / 0.8)
    fr.line((cx - w, cy + 92), (cx + w, cy + 92), GOLD, a2 * 0.6, 2)
    fr.text('从巴菲特、芒格出发', cx, cy + 140, 40, 'serif_med', GOLD2, a2, track=0.18, glow=0.15)
    # 一句话命题：今天赚多少 ✗ / 回报 × 时间 ✓
    y = 720
    k1 = S.a('sub', 0.5)
    if k1 > 0:
        fr.text('今天赚多少', cx - 420, y, 46, 'sans_black', GREY, k1 * S.fade_out(0.6))
        sk = S.a('sub', 0.5, off=1.6)
        tw = text_width('今天赚多少', 'sans_black', 46)
        fr.line((cx - 420 - tw / 2 - 10, y), (cx - 420 - tw / 2 - 10 + (tw + 20) * sk, y), RED, k1 * S.fade_out(0.6), 4)
    k2 = S.a('sub2', 0.5, eback)
    if k2 > 0:
        label_pill(fr, '多高的回报 × 多长的时间', cx + 210, y, GOLD, cl(k2) * S.fade_out(0.6), 44, 'sans_black', 30)
    k3 = S.a('sub3', 0.5)
    if k3 > 0:
        headline(fr, '持续赚到超过资本成本的钱', cx, y + 120, 52, GOLD, k3 * S.fade_out(0.6))
    fr.zoom *= 1 + 0.04 * eio((lt - 8) / 6)


# ================================================================ 公式
F1 = [('经济利润', GOLD, 'ep'), ('=', WHITE, 'ep'), ('(', GREY, 'ep'), ('ROIC', TEAL, 'ep'), ('−', WHITE, 'ep'),
      ('WACC', C(255, 120, 120), 'ep'), (')', GREY, 'ep'), ('×', WHITE, 'ic'), ('投入资本', C(110, 170, 255), 'ic')]
F2 = [('每股内在价值', GOLD, 'ps'), ('≈', WHITE, 'ps'), ('[', GREY, 'iv'), ('投入资本', C(110, 170, 255), 'iv'),
      ('+', WHITE, 'sum'), ('Σ 经济利润现值', GOLD, 'sum'), (']', GREY, 'iv'), ('÷', WHITE, 'ps'), ('股数', VIOLET, 'ps')]


def fly_row(fr, S, toks, y, size, a, gap=20, stag=0.12):
    """公式各项从镜头前飞入落位"""
    ws = []
    for s, col, cue in toks:
        f = 'orb' if s in ('ROIC', 'WACC') else ('sans_light' if s in '=()[]≈×÷+−' else 'sans_black')
        sz = int(size * (0.82 if f == 'orb' else 1.0))
        ws.append((f, sz, text_width(s, f, sz)))
    total = sum(w for _, _, w in ws) + gap * (len(toks) - 1)
    x = W / 2 - total / 2
    order = {}
    for i, ((s, col, cue), (f, sz, w)) in enumerate(zip(toks, ws)):
        j = order.get(cue, 0); order[cue] = j + 1
        t0 = S.c(cue) + j * stag
        k = cl((fr.t - t0) / 0.5)
        if k > 0:
            e = eo(k)
            sc = lerp(3.0, 1.0, e)
            cx = x + w / 2
            yy = y + (1 - e) * (y - 540) * 0.6
            fr.text(s, cx, yy, int(sz * sc), f, col, a * cl(k * 2), mode='E' if f == 'orb' else 'L',
                    glow=0.35 if col in (GOLD, TEAL) else 0.15)
            fr.glow((cx, y), 40, col, a * pulse(fr.t, t0 + 0.5, 0.3) * 0.7)
        x += w + gap
    return total


@reg('formula')
def formula(fr, S):
    t = fr.t
    a0 = S.fade_out(0.5)
    fr.text('一 个 公 式', W / 2, 200, 34, 'serif_med', GOLD2, a0 * S.a('f0', 0.6), track=0.3, glow=0.2)
    fly_row(fr, S, F1, 330, 74, a0)
    # 未来每一年的经济利润 → 折现 → 加总
    sk = S.a('sum', 0.6)
    if sk > 0:
        n = 12
        base = 830
        for i in range(n):
            ki = ramp(t, S.c('sum') + i * 0.1, 0.4, eback)
            if ki <= 0: continue
            h = 150 * 0.9 ** i * cl(ki)
            x = 420 + i * 90
            col = lerpc(GOLD, GOLD2, i / n)
            fr.rrect_fill(x - 30, base - h, x + 30, base, 5, col, a0 * (0.25 + 0.5 * 0.9 ** i), 'E')
            fr.text(f'{i + 1}', x, base + 26, 20, 'mono', GREY, a0 * cl(ki))
        fr.text('未来每一年的经济利润（折现后越来越小）', 420 + 5.5 * 90, base + 70, 26, 'sans_med', GREY, a0 * sk)
        ik = S.a('iv', 0.6)
        fr.text('Σ', 300, base - 70, 110, 'serif_black', GOLD, a0 * sk, glow=0.4)
        if ik > 0:
            fr.rrect_fill(1560 - 40, base - 170 * ik, 1560 + 40, base, 6, C(110, 170, 255), a0 * 0.55, 'E')
            fr.text('今天的投入资本', 1560, base + 26, 22, 'sans_bold', C(140, 190, 255), a0 * ik)
    fly_row(fr, S, F2, 500, 54, a0, 14, 0.15)


# ================================================================ 价值体
B_BASE = BlockSpec(T=20.0, h0=3.0, d0=4.0, disc=0.045)


def block_state(S, t):
    """价值体在 block 场景里的形变：五个问题"""
    B = B_BASE.copy()
    B.extend = S.a('vol', 2.6, eio)
    B.h0 = 3.0 + 1.4 * S.a('h', 0.6, eback) - 1.4 * S.a('m', 0.5)
    B.grow = 0.045 * S.a('d', 0.9, eio)
    B.T = 20 + 8 * S.a('l', 1.0, eio)
    if S.cq.get('cut', FAR) <= t:
        B.cut = 9.0
        B.shatter = cl((t - S.c('cut') - 0.35) / 2.2)
    return B


@reg('block')
def block(fr, S):
    t = fr.t
    a0 = S.fade_out(0.5)
    cam = keycam(t, [
        (S.start, ((8, 2, 0), 34, 0.0, 0.05, 40)),
        (S.c('x'), ((9, 2, 0), 32, 0.35, 0.20, 40)),
        (S.c('vol'), ((10, 2.5, 0), 34, 0.55, 0.28, 40)),
        (S.c('five'), ((12, 3, 0), 38, 0.75, 0.32, 40)),
        (S.c('l'), ((14, 3, 0), 44, 0.6, 0.30, 40)),
        (S.end, ((14, 3, 0), 46, 0.5, 0.28, 40)),
    ])
    fr.k = a0 * S.a('draw', 0.8)
    grid_plane(fr, cam, 0, x0=-2, x1=30, z0=-10, z1=10, step=1, col=RED, a=0.45, fog=80)
    if fr.k > 0.01:
        P, Z = cam.project(np.array([[-2, 0, 6]]))
        fr.text('资本成本 WACC', P[0][0], P[0][1] + 30, 26, 'sans_bold', C(255, 140, 140), fr.k, anchor='l')
    # 三根坐标轴
    axis_arrow(fr, cam, (0, 0, 5.5), (24, 0, 5.5), ICE, fr.k, 3, '时间', 36, S.a('x', 1.0, eio))
    axis_arrow(fr, cam, (0, 0, 5.5), (0, 5.5, 5.5), TEAL, fr.k, 3, 'ROIC − WACC', 32, S.a('y', 0.8, eio))
    axis_arrow(fr, cam, (0, 0, 5.5), (0, 0, -6), C(110, 170, 255), fr.k, 3, '投入资本', 32, S.a('z', 0.8, eio))
    if S.a('x', 0.5) > 0:
        for yr in range(0, 25, 5):
            P, Z = cam.project(np.array([[yr, 0, 5.5]]))
            fr.text(f'{yr}年', P[0][0], P[0][1] + 28, 20, 'sans_med', ICE, fr.k * S.a('x', 0.5, off=yr * 0.04))
    B = block_state(S, t)
    draw_block(fr, cam, B, t)
    fr.k = 1.0
    va = S.a('vol', 0.6, off=1.2) * (1 - S.a('five', 0.5))
    if va > 0:
        headline(fr, '体积 = 价值', W / 2, 210, 72, GOLD, va * a0)
        fr.text('未来经济利润的现值之和', W / 2, 280, 30, 'sans_med', GOLD2, va * a0)
    # 五个问题
    fk = S.a('five', 0.5)
    if fk > 0:
        qs = [('h', '多高？', '超额回报', GOLD), ('m', '代价？', '维持成本', ORANGE), ('d', '多厚？', '再投资', TEAL),
              ('l', '多远？', '持续时间', VIOLET), ('cut', '截断？', '会不会死', RED)]
        for i, (cue, q, sub, col) in enumerate(qs):
            x = 230 + i * 365
            on = S.a(cue, 0.4, eback)
            cur = t >= S.c(cue) - 0.05 and (i == 4 or t < S.c(qs[i + 1][0]) - 0.05)
            al = a0 * fk * (0.35 + 0.65 * cl(on))
            fr.text(f'{i + 1}', x - 120, 180, 44, 'orb', col, al, mode='E', glow=0.4)
            fr.text(q, x, 165, 50 if cur else 44, 'sans_black', lerpc(col, WHITE, 0.5), al, glow=0.3 if cur else 0)
            fr.text(sub, x, 222, 26, 'sans_med', lerpc(col, WHITE, 0.2), al)
            if cur:
                fr.line((x - 90, 250), (x + 90, 250), col, al, 3)
        # 维持成本：被削掉的顶层飘走
        mk = S.a('m', 1.4, eio)
        if 0 < mk < 1:
            fr.k = a0 * (1 - mk)
            peel = BlockSpec(T=B.T * B.extend, h0=1.4, d0=4.0, grow=B.grow, disc=0.045, col=ORANGE)
            draw_block(fr, cam, peel, t, origin=(0, B.h0 + mk * 3, 0), particles=False)
            fr.k = 1.0
        # 截断：红色激光刀
        ck = S.a('cut', 0.35)
        if ck > 0:
            P, Z = cam.project(np.array([[9, 12 - 12 * ck, -6], [9, 12 - 12 * ck, 6], [9, 0, 6], [9, 0, -6]]))
            fr.poly([tuple(P[0]), tuple(P[1])], RED, a0 * (1 - S.a('cut', 0.6, off=0.6)), 4)
            fr.fillpoly([tuple(p) for p in P], RED, 0.25 * a0 * pulse(t, S.c('cut') + 0.35, 0.5), 'E')


# ================================================================ 六层地图：每一层对应价值体的一个维度
MAPL = [('l0', '生存', '会不会被截断', RED), ('l1', '价值创造与获取', '高度：超额回报', C(255, 200, 90)),
        ('l2', '维持成本', '顶上被削掉多少', ORANGE), ('l3', '再投资', '厚度：能否越做越厚', TEAL),
        ('l4', '资本与治理', '地板：资本成本 · 杠杆 · 股数', C(90, 170, 255)), ('l5', '时间与演化', '长度：能持续多久', VIOLET)]


def map_labels(fr, cam, B, S, cues, a0, t):
    hT = float(B.h(np.array([B.T]))[0])
    pts = [(B.T + 0.1, hT * 0.5, 0), (2, B.h0 * 0.6, -2), (9, B.h0, -1), (6, B.h0 * 0.4, B.d0 * (1 + B.grow) ** 6 / 2),
           (14, 0, 6.5), (19, hT, 0)]
    offs = [(110, -40), (-220, -150), (60, -230), (-200, 170), (150, 150), (140, -200)]
    for i, (cue, nm, sub, col) in enumerate(MAPL):
        k = ramp(t, cues[i], 0.45, eback)
        if k <= 0: continue
        dx, dy = offs[i]
        label3d(fr, cam, pts[i], f'第{"一二三四五六"[i]}层 · {nm}', col, a0 * cl(k), 32, dx, dy, sub)


@reg('map')
def map_(fr, S):
    t = fr.t
    a0 = S.fade_out(0.4)
    dive = S.a('ord', 7.5, ei)
    cam = keycam(t, [
        (S.start, ((14, 3, 0), 46, 0.5, 0.28, 40)),
        (S.c('l0'), ((11, 3, 0), 44, 0.62, 0.30, 40)),
        (S.c('ord'), ((11, 3, 0), 46, 0.75, 0.32, 40)),
        (S.end, ((20, 2, 0), 16, 1.25, 0.12, 40)),
    ])
    fr.k = a0
    grid_plane(fr, cam, 0, x0=-2, x1=30, z0=-10, z1=10, step=1, col=RED, a=0.45, fog=80)
    B = B_BASE.copy(h0=3.6, grow=0.03, T=24)
    draw_block(fr, cam, B, t)
    fr.k = 1.0
    hk = S.a('map', 0.6) * (1 - dive)
    headline(fr, '六层 = 价值体的六个维度', W / 2, 190, 60, GOLD, hk * a0)
    cues = [S.c(c) for c in ('l0', 'l1', 'l2', 'l3', 'l4', 'l5')]
    cues = [max(c, cues[0] + i * 0.4) for i, c in enumerate(cues)]
    map_labels(fr, cam, B, S, cues, a0 * (1 - dive), t)
    ok = S.a('ord', 0.6)
    if ok > 0:
        fr.text('顺序很重要', W / 2, 900, 40, 'serif_black', RED, ok * a0 * (1 - dive * 0.5), glow=0.3)
    # 冲向截断面：转红
    fr.flash = max(fr.flash, 0.0)
    if dive > 0:
        fr.rect(0, 0, W, H, (0.5, 0.02, 0.05), 0.35 * dive, 'L')
