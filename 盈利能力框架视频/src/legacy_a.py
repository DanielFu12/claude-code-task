"""场景 A：冷开场、标题、核心命题、统一公式、六层结构、为什么分层。"""
from common import *

RNG = np.random.default_rng(2024)
DRAW = {}


def reg(name):
    def d(f):
        DRAW[name] = f
        return f
    return d


# ================================================================ 冷开场
HX0, HX1, HY = 210, 1710, 690
YRS = np.linspace(0, 1, 160)
UP_Y = HY - (np.power(1.15, YRS * 20) - 1) / (1.15 ** 20 - 1) * 400
_dn = np.where(YRS < 0.62, (np.power(1.28, YRS * 20 / 0.62 * 0.62 * 1.0) - 1) / (1.28 ** (20 * 0.62) - 1) * 380,
               380 * np.exp(-((YRS - 0.62) / 0.12) ** 2) - 520 * np.clip((YRS - 0.62) / 0.38, 0, 1) ** 1.2)
DN_Y = HY - _dn
NP = 2200
SP_A = RNG.uniform(0, 2 * np.pi, NP); SP_R = RNG.uniform(500, 1300, NP); SP_S = RNG.uniform(0.6, 1.4, NP)
SP_C = np.array([lerpc(GOLD, [ICE, GOLD2, VIOLET, WHITE][i % 4], 0.5) for i in range(NP)], np.float32)


@reg('hook')
def hook(fr, S):
    t = fr.t
    xs = HX0 + YRS * (HX1 - HX0)
    dim = 1 - 0.75 * S.a('why', 0.6)
    gone = 1 - S.a('bm', 0.5) * 0.85
    # 前导：打字机式小标题
    pa = env(t, 0.6, 4.6, 0.4, 0.6)
    if pa > 0:
        s0 = '二十年 · 两家公司'
        n = int(cl((t - 0.8) * 7, 0, len(s0)))
        fr.text(s0[:n], W / 2, 470, 34, 'serif_med', GOLD2, pa * 0.9, glow=0.2, track=0.3)
        if int(t * 2.5) % 2 == 0:
            cxp = W / 2 + text_width(s0, 'serif_med', 34, 0.3) / 2 * (2 * n / len(s0) - 1) + 14
            fr.line((cxp, 452), (cxp, 488), GOLD, pa * 0.8, 2)
    # 时间轴
    ax = ramp(t, 1.2, 2.2, eio)
    fr.line((HX0, HY), (HX0 + (HX1 - HX0) * ax, HY), GREY, 0.5 * gone, 2)
    for k in range(21):
        x = HX0 + k / 20 * (HX1 - HX0)
        if k / 20 <= ax:
            fr.line((x, HY), (x, HY + (12 if k % 5 == 0 else 6)), GREY, 0.45 * gone, 1)
            if k % 5 == 0:
                fr.text(f'{k}年', x, HY + 34, 20, 'sans_light', GREY, 0.6 * gone * ax)
    # 复利曲线
    pu = S.a('up', 2.2, eio)
    if pu > 0:
        a = dim * gone
        pts = draw_line_chart(fr, xs, UP_Y, GOLD, a, 4, pu)
        fr.glow(tuple(pts[-1]), 30, GOLD, 0.6 * a)
        mult = 1.15 ** (20 * pu)
        fr.text(f'×{mult:.1f}', pts[-1][0] + 18, pts[-1][1] - 28, 34, 'orb', GOLD2, a * cl(pu * 4), anchor='l', mode='E', glow=0.3)
        fr.text('二十年复利不止', HX0 + 40, 330, 30, 'serif_med', GOLD, a * S.a('up', 0.5), anchor='l', glow=0.2)
    pd = S.a('down', 2.6, eio)
    if pd > 0:
        a = dim * gone
        k = int(pd * (len(xs) - 1))
        pts = draw_line_chart(fr, xs, DN_Y, RED, a, 4, pd)
        ip = int(0.62 * (len(xs) - 1))
        if k >= ip:
            px, py = xs[ip], DN_Y[ip]
            fr.glow((px, py), 26, RED, a * 0.7)
            fr.circle((px, py), 14 + 8 * pulse(t, S.c('down') + 1.6, 0.5), RED, a, 2)
            fr.text('利润最高的那一年', px, py - 52, 28, 'sans_bold', C(255, 150, 150), a * ramp(t, S.c('down') + 1.6, 0.4), glow=0.2)
        if pd > 0.9:
            ex = ramp(t, S.c('down') + 2.35, 1.2)
            if ex > 0:
                ang = RNG.uniform(0, 6.28, 300)
                rr = ex * RNG.uniform(20, 200, 300)
                fr.dots(xs[-1] + np.cos(ang) * rr, DN_Y[-1] + np.sin(ang) * rr * 0.6 + ex * 60, RED, (1 - ex) * a, 1)
            fr.text('死亡的伏笔', xs[-1] - 10, DN_Y[-1] + 40, 30, 'serif_black', RED, a * ramp(t, S.c('down') + 2.4, 0.5),
                    anchor='r', glow=0.4)
    # 问题
    q = S.a('why', 0.5)
    if q > 0:
        qa = q * (1 - S.a('bm', 0.6))
        gl = pulse(t, S.c('why'), 0.25)
        fr.ca = max(fr.ca, gl * 6)
        headline(fr, '差别，究竟在哪里？', W / 2 + gl * 8, 470, 96, WHITE, qa, t0=S.c('why'), stag=0.05)
    # 巴菲特 & 芒格
    b = S.a('bm', 0.7)
    if b > 0:
        ba = b * (1 - S.a('today', 0.8))
        for side, (zh, en) in ((-1, ('巴菲特', 'WARREN  BUFFETT')), (1, ('芒格', 'CHARLIE  MUNGER'))):
            x = W / 2 + side * 380
            off = (1 - b) * 120 * side
            fr.circle((x + off, 470), 158 + 6 * kick_pulse(t), GOLD, ba * 0.55, 2)
            fr.circle((x + off, 470), 176, GOLD, ba * 0.18, 1)
            headline(fr, zh, x + off, 450, 80, GOLD, ba)
            fr.text(en, x + off, 525, 20, 'corm', GOLD2, ba * 0.85, track=0.12)
        lw = 190 * b
        fr.line((W / 2 - lw, 470), (W / 2 + lw, 470), GOLD2, ba * 0.5, 2)
        fr.glow((W / 2, 470), 10 + 6 * beat_pulse(t), GOLD, ba)
        fr.text('一生的答案', W / 2, 610, 30, 'serif_med', GOLD2, ba * S.a('bm', 0.6, off=0.6), track=0.3)
    # 粒子汇聚 -> 标题
    p = S.a('today', 23.85 - S.c('today'), lambda x: cl(x))
    if p > 0:
        e = p ** 1.6
        r = SP_R * (1 - e) ** 1.4 + 2
        ang = SP_A + e * 5.0 * SP_S + t * 0.3
        x = W / 2 + np.cos(ang) * r
        y = 520 + np.sin(ang) * r * 0.62
        al = cl(p * 3) * (0.5 + 0.8 * e)
        fr.dots(x, y, SP_C, al * 0.8, 1)
        fr.glow((W / 2, 520), 20 + 60 * e, GOLD, 0.25 + 0.9 * e ** 3)
        fr.glow((W / 2, 520), 8 + 14 * e, WHITE, 0.2 + 1.5 * e ** 4, 'E')
        if t > 23.5:
            fr.flash = max(fr.flash, ei((t - 23.5) / 0.4) * 0.15)


# ================================================================ 标题
TITLE = '企业盈利能力评估框架'
TP_X, TP_Y, TP_M = particle_text_points(TITLE, 'serif_black', 124, 3, 0.06)
NTP = len(TP_X)
TP_A = RNG.uniform(0, 2 * np.pi, NTP); TP_V = RNG.uniform(300, 1300, NTP)
TP_C = np.array([lerpc(GOLD, GOLD2, RNG.random()) for _ in range(NTP)], np.float32)


@reg('title')
def title(fr, S):
    t = fr.t
    lt = S.lt
    cx, cy = W / 2, 470
    # 光芒
    ra = cl(lt / 0.3) * (0.10 + 0.05 * kick_pulse(t)) * S.fade_out(0.6)
    light_rays(fr, (cx, cy), 18, 1300, GOLD, ra, t, 0.035)
    fr.glow((cx, cy), 260, GOLD, 0.12 * ra / 0.12)
    # 粒子：爆开 -> 聚成标题
    form = eio((lt - 0.25) / 1.1)
    burst = eo(lt / 0.35)
    if lt < 2.2:
        bx = cx + np.cos(TP_A) * TP_V * burst * (1 - form)
        by = cy + np.sin(TP_A) * TP_V * burst * (1 - form) * 0.6
        x = bx * (1 - form) + (cx + TP_X) * form
        y = by * (1 - form) + (cy + TP_Y) * form
        fr.splat(x, y, TP_C, (1 - eio((lt - 1.4) / 0.8)) * 0.9, 'E')
    sa = eio((lt - 1.1) / 0.7)
    if sa > 0:
        headline(fr, TITLE, cx, cy, 124, GOLD, sa * S.fade_out(0.6), glow=0.45, track=0.06)
    # 横向光条
    st = cl(lt / 0.9)
    if st < 1:
        fr.fillpoly([(cx - 900, cy - 3), (cx + 900, cy - 3), (cx + 900, cy + 3), (cx - 900, cy + 3)], GOLD2, (1 - st) * 0.9, 'E')
        fr.glow((cx, cy), 60, WHITE, (1 - st) * 1.2)
    a2 = ramp(t, S.start + 1.4, 0.6) * S.fade_out(0.6)
    fr.text('A  FRAMEWORK  FOR  BUSINESS  PROFITABILITY', cx, cy - 115, 24, 'corm', GOLD2, a2 * 0.85, track=0.25)
    w = 560 * eo((lt - 1.3) / 0.8)
    fr.line((cx - w, cy + 92), (cx + w, cy + 92), GOLD, a2 * 0.6, 2)
    fr.text('从巴菲特、芒格出发', cx, cy + 140, 40, 'serif_med', GOLD2, a2, track=0.18, glow=0.15)
    # 四个关键词
    words = ['创造价值', '留住价值', '维持价值', '复利下去']
    cols = [GOLD, CYAN, ORANGE, TEAL]
    xs = [cx - 510, cx - 170, cx + 170, cx + 510]
    for i, (wd, col) in enumerate(zip(words, cols)):
        try:
            tw = S.w(wd)
        except KeyError:
            tw = S.c('sub') + i
        k = ramp(t, tw, 0.4, eback) * S.fade_out(0.6)
        if k > 0:
            label_pill(fr, wd, xs[i], cy + 250 - (1 - cl(k)) * 30, col, cl(k), 40, 'sans_bold', 30)
            fr.glow((xs[i], cy + 250), 40, col, pulse(t, tw, 0.3) * 0.8)
    fr.zoom *= 1 + 0.04 * eio((lt - 8) / 4)


# ================================================================ 五件事
FIVE = [('01', 'bars', '超额回报', 'ROIC 持续高于 WACC', 'L1'),
        ('02', 'cycle', '维持代价', '保住回报要花多少', 'L2'),
        ('03', 'branch', '再投资', '回报 · 规模 · 能否不投', 'L3'),
        ('04', 'hourglass', '持续多久', '优势能维持多长时间', 'L5'),
        ('05', 'pulse', '会不会死', '永久性资本损失', 'L0')]


@reg('five')
def five(fr, S):
    t = fr.t
    fr.text('一家企业对股东的长期价值，取决于五件事', W / 2, 225, 38, 'serif_med', GOLD2,
            ramp(t, S.start + 1.4, 0.6) * S.fade_out(0.4), glow=0.15, track=0.05)
    last = -1
    for i in range(5):
        if t >= S.c(f'q{i + 1}'): last = i
    for i, (num, icon, ttl, sub, lk) in enumerate(FIVE):
        tc = S.c(f'q{i + 1}')
        k = ramp(t, tc, 0.55, eback)
        if k <= 0: continue
        col = LAYER_COL[lk]
        cx = 240 + i * 360
        cy = 560 + (1 - cl(k)) * 80
        a = cl(k) * (1.0 if i == last else 0.72) * S.fade_out(0.4)
        x0, y0, x1, y1 = cx - 150, cy - 220, cx + 150, cy + 220
        fr.panel(x0, y0, x1, y1, col, a, r=18, fill=0.07 + 0.08 * pulse(t, tc, 0.4), dark=0.55)
        fr.text(num, x0 + 26, y0 + 44, 40, 'orb', col, a, anchor='l', mode='E', glow=0.4)
        draw_icon(fr, icon, cx, cy - 60, 110, col, a, 4, t)
        fr.glow((cx, cy - 60), 70, col, a * (0.15 + 0.5 * pulse(t, tc, 0.5)))
        fr.text(ttl, cx, cy + 62, 44, 'sans_black', lerpc(col, WHITE, 0.6), a)
        hl = S.a('q3b', 0.4) if i == 2 else 0
        subc = lerpc(GREY, col, hl) if i == 2 else GREY
        fr.text(sub, cx, cy + 118, 24, 'sans_med', lerpc(subc, WHITE, 0.3), a)
        if hl > 0:
            fr.line((cx + 15, cy + 140), (cx + 15 + 100 * hl, cy + 140), col, a, 3)
            fr.glow((cx + 65, cy + 140), 30, col, a * pulse(t, S.c('q3b'), 0.5))
        label_pill(fr, lk, cx, y1 - 40, col, a, 24, 'orb', 16)
        # 扫光
        sw = (t - tc) / 0.6
        if 0 < sw < 1:
            xx = x0 + sw * 300
            fr.fillpoly([(xx - 30, y0), (xx + 10, y0), (xx - 30 + 40 - 80, y1), (xx - 70 - 40, y1)], WHITE, 0.10 * (1 - sw), 'L')
        fr.glow((cx, y0), 50, col, pulse(t, tc, 0.3) * 0.9)


# ================================================================ 统一公式
F1 = [('经济利润', GOLD, 'ep'), ('=', WHITE, 'ep'), ('(', GREY, 'r'), ('ROIC', TEAL, 'r'), ('−', WHITE, 'w'),
      ('WACC', C(255, 120, 120), 'w'), (')', GREY, 'w'), ('×', WHITE, 'ic'), ('投入资本', C(110, 170, 255), 'ic')]
F2 = [('每股内在价值', GOLD, 'iv'), ('≈', WHITE, 'iv'), ('[', GREY, 'iv1'), ('投入资本', C(110, 170, 255), 'iv1'),
      ('+', WHITE, 'iv2'), ('Σ 未来经济利润的现值', GOLD, 'iv2'), (']', GREY, 'iv2'), ('÷', WHITE, 'iv3'), ('稀释后股数', VIOLET, 'iv3')]


def formula_row(fr, S, toks, y, size, a, gap=22, fnt_map=None, bright=None):
    ws = []
    for s, col, cue in toks:
        f = 'orb' if s in ('ROIC', 'WACC') else ('sans_light' if s in '=()[]≈×÷+−' else 'sans_black')
        sz = int(size * (0.82 if f == 'orb' else 1.0))
        ws.append((f, sz, text_width(s, f, sz)))
    total = sum(w for _, _, w in ws) + gap * (len(toks) - 1)
    x = W / 2 - total / 2
    for (s, col, cue), (f, sz, w) in zip(toks, ws):
        k = S.a(cue, 0.4, eback)
        if k > 0:
            fr.text(s, x + w / 2, y - (1 - cl(k)) * 24, sz, f, col, a * cl(k), mode='E' if f == 'orb' else 'L',
                    glow=0.35 if col in (GOLD, TEAL) else 0.15)
            fr.glow((x + w / 2, y), 40, col, a * pulse(fr.t, S.c(cue), 0.35) * 0.7)
        x += w + gap
    return total


@reg('formula')
def formula(fr, S):
    t = fr.t
    up = S.a('pos', 0.8, eio)
    a1 = S.fade_out(0.4)
    y1 = lerp(390, 200, up)
    s1 = lerp(72, 50, up)
    formula_row(fr, S, F1, y1, s1, a1)
    a2 = (1 - up) * a1
    if a2 > 0:
        formula_row(fr, S, F2, 560, 54, a2, 14)
        hk = S.a('iv2', 0.5)
        if hk > 0:
            fr.text('↑ 价值的核心：超额回报能持续多久、多大', W / 2 + 120, 640, 26, 'sans_bold', GOLD, a2 * hk * (1 - S.a('iv3', 0.4, off=0.6)))
        fr.text('经济利润法 ≡ 自由现金流折现（假设一致时）', W / 2, 700, 26, 'sans_light', GREY, a2 * S.a('iv3', 0.6, off=0.8))
    if up <= 0: return
    # 图表：左 ROIC>WACC，右 ROIC<WACC 且规模越大毁灭越多
    a = up * a1
    base = 700
    for side in (-1, 1):
        cx = W / 2 + side * 420
        fr.line((cx - 330, base), (cx + 330, base), C(255, 120, 120), a * 0.9, 2)
        for k in range(22):
            xx = cx - 330 + k * 30
            fr.line((xx, base), (xx + 14, base), C(255, 120, 120), a * 0.5, 2)
        fr.text('WACC', cx + 330, base - 22, 22, 'orb', C(255, 140, 140), a, anchor='r')
    # 左
    cx = W / 2 - 420
    g = S.a('pos', 1.0, eo)
    for i in range(5):
        x = cx - 240 + i * 120
        hh = (180 + 40 * math.sin(i * 1.7)) * g
        top = base + 140 - (140 + hh)
        fr.rrect_fill(x - 34, top, x + 34, base + 140, 6, TEAL, a * 0.10)
        fr.rrect(x - 34, top, x + 34, base + 140, 6, TEAL, a * 0.6, 2)
        fr.rrect_fill(x - 34, top, x + 34, base, 6, GOLD, a * (0.35 + 0.25 * kick_pulse(t)), 'E')
    fr.text('ROIC > WACC', cx, 885, 30, 'orb', TEAL, a, mode='E', glow=0.3)
    headline(fr, '创造价值', cx, 430, 54, GOLD, a * g)
    # 右
    cx = W / 2 + 420
    n = S.a('neg', 3.0, eio)
    if n > 0:
        for i in range(5):
            wscale = 0.45 + n * (0.4 + i * 0.32)
            x = cx - 250 + i * 125
            hh = 110
            fr.rrect_fill(x - 30 * wscale, base, x + 30 * wscale, base + hh * (0.4 + 0.6 * eo(n * 2)), 4, RED, a * 0.45, 'E')
            fr.rrect(x - 30 * wscale, base - 60, x + 30 * wscale, base + hh, 4, RED, a * 0.35, 1)
        fr.text('ROIC < WACC', cx, 885, 30, 'orb', RED, a * cl(n * 3), mode='E', glow=0.3)
        headline(fr, '规模越大，毁灭越多', cx, 430, 50, RED, a * cl(n * 3))
        fr.arrow((cx - 260, 560), (cx + 260, 560), C(255, 130, 130), a * cl(n * 3) * 0.7, 3, 18)
        fr.text('规模 →', cx + 270, 530, 22, 'sans_med', C(255, 150, 150), a * cl(n * 3), anchor='r')


# ================================================================ 六层结构（3D 叠层）
SLAB_W, SLAB_D, SLAB_H, GAP = 560, 250, 40, 52
LDESC = ['会不会永久损失 · 一票否决', '凭什么赚到超额回报，且不被拿走', '保住现在的利润，要花多少',
         '投多少 · 回报多高 · 能否不投', '钱从哪来 · 谁在配置 · 激励指向', '能持续多久 · 有多大把握']


def slab(fr, yaw, pitch, cx, cy, y, col, a, glow=0.0, scale=1.0, label=None):
    w, d, h = SLAB_W / 2 * scale, SLAB_D / 2 * scale, SLAB_H * scale
    P = np.array([[-w, y, -d], [w, y, -d], [w, y, d], [-w, y, d],
                  [-w, y + h, -d], [w, y + h, -d], [w, y + h, d], [-w, y + h, d]])
    S2, _ = proj3(P, yaw, pitch, cx, cy)
    top = [S2[4], S2[5], S2[6], S2[7]]
    front = [S2[3], S2[2], S2[6], S2[7]]
    side = [S2[1], S2[2], S2[6], S2[5]]
    fr.fillpoly(front, (0, 0, 0), a * 0.7, 'O')
    fr.fillpoly(side, (0, 0, 0), a * 0.75, 'O')
    fr.fillpoly(top, (0, 0, 0), a * 0.6, 'O')
    fr.fillpoly(top, col, a * (0.22 + glow * 0.3), 'L')
    fr.fillpoly(front, col, a * (0.30 + glow * 0.3), 'L')
    fr.fillpoly(side, col, a * (0.20 + glow * 0.2), 'L')
    fr.poly(top, col, a, 2, closed=True)
    fr.poly(front, lerpc(col, WHITE, 0.3), a, 2, closed=True)
    fr.poly(side, col, a * 0.8, 2, closed=True)
    return S2


@reg('layers')
def layers(fr, S):
    t = fr.t
    cx, cy = 600, 600
    yaw = -0.55 + 0.08 * math.sin(t * 0.25)
    pitch = 0.30
    a0 = S.fade_out(0.45)
    fr.text('每一项，都对应一层', W / 2, 190, 34, 'serif_med', GOLD2, ramp(t, S.start + 1.4, 0.5) * a0 * (1 - S.a('l0', 0.6)), glow=0.15)
    cues = ['l0', 'l1', 'l2', 'l3', 'l4', 'l5']
    done = ramp(t, S.c('l5') + 1.0, 1.0)
    for i, (lk, nm) in enumerate(LAYERS):
        tc = S.c(cues[i])
        k = ramp(t, tc - 0.25, 0.5, eo)
        if k <= 0: continue
        col = LAYER_COL[lk]
        y = -250 + i * (SLAB_H + GAP) + (1 - k) * 500
        land = pulse(t, tc + 0.25, 0.3)
        P = slab(fr, yaw, pitch, cx, cy, y, col, a0 * cl(k * 1.5), glow=land + done * 0.3 * (0.5 + 0.5 * math.sin(t * 3 - i)))
        if land > 0.05:
            fr.glow(tuple(P[6]), 50, col, land * a0)
        # 标签
        la = ramp(t, tc, 0.5) * a0
        ly = 868 - i * 116
        lx = 1080
        anchor_pt = (P[5] + P[6]) / 2
        fr.poly([tuple(anchor_pt), (lx - 40, ly), (lx - 12, ly)], col, la * 0.6, 2)
        fr.disc(tuple(anchor_pt), 4, col, la)
        fr.text(lk, lx, ly - 4, 44, 'orb', col, la, anchor='l', mode='E', glow=0.4)
        fr.text(nm, lx + 100, ly - 18, 36, 'sans_black', lerpc(col, WHITE, 0.6), la, anchor='l')
        fr.text(LDESC[i], lx + 100, ly + 24, 24, 'sans_light', lerpc(col, WHITE, 0.4), la * 0.95, anchor='l')
    if done > 0:
        top_y = -250 + 6 * (SLAB_H + GAP)
        P, _ = proj3(np.array([[0, -260, 0], [0, top_y + 200, 0]]), yaw, pitch, cx, cy)
        fr.line(tuple(P[0]), tuple(P[1]), GOLD2, done * 0.35 * a0, 2)
        fr.glow(tuple(P[1]), 40, GOLD, done * 0.6 * a0)


# ================================================================ 为什么分层
TAGS = [('冲浪模型', 1), ('护城河', 1), ('周期景气', 5), ('现金牛', 3), ('并购整合', 3), ('3G 资本', 4), ('浮存金', 4)]
TAG_P = RNG.uniform(0, 6.28, (len(TAGS), 4))


@reg('why')
def why(fr, S):
    t = fr.t
    a0 = S.fade_out(0.45)
    srt = S.a('sort', 1.0, eio)
    fin = S.a('tag', 0.8, eio)
    # 层条
    rows_y = {i: 790 - i * 92 for i in range(6)}
    if srt > 0:
        for i, (lk, nm) in enumerate(LAYERS):
            col = LAYER_COL[lk]
            y = rows_y[i]
            k = cl(srt * 1.6 - i * 0.1)
            a = k * a0 * (1 - 0.9 * fin)
            fr.panel(250, y - 36, 250 + 300 * k, y + 36, col, a, r=10, fill=0.18, dark=0.5)
            fr.text(f'{lk}  {nm}', 270, y, 28, 'sans_bold', lerpc(col, WHITE, 0.5), a * k, anchor='l')
            fr.line((560, y), (1700, y), col, a * 0.15, 1)
    # 标签：先乱飞交叉，后归位
    count = {}
    pos = []
    for j, (s, li) in enumerate(TAGS):
        k = ramp(t, S.c('tags') + j * 0.25, 0.4, eback)
        if k <= 0:
            pos.append(None); continue
        p = TAG_P[j]
        fx = W / 2 + 520 * math.sin(t * 0.5 * (0.6 + p[0] / 6) + p[1]) * (0.6 + 0.4 * math.sin(p[2]))
        fy = 520 + 230 * math.sin(t * 0.43 * (0.6 + p[2] / 6) + p[3])
        n = count.get(li, 0); count[li] = n + 1
        tx, ty = 640 + n * 250, rows_y[li]
        e = cl(srt * 1.3 - j * 0.05)
        e = eio(e)
        x, y = lerp(fx, tx, e) + 110, lerp(fy, ty, e)
        col = LAYER_COL[LAYERS[li][0]]
        tc = lerpc(GREY, col, e)
        pos.append((x, y, tc))
        label_pill(fr, s, x, y, tc, cl(k) * a0 * (1 - 0.9 * fin), 32, 'sans_bold', 22)
    # 交叉连线（混乱）
    mess = (1 - srt)
    if mess > 0.01:
        for j in range(len(pos)):
            for k2 in range(j + 1, len(pos)):
                if pos[j] and pos[k2] and (j + k2) % 2 == 0:
                    fr.line(pos[j][:2], pos[k2][:2], RED, 0.22 * mess * a0, 1)
        fr.text('互相交叉 · 包含 · 打架', W / 2, 200, 30, 'sans_med', C(255, 150, 150), mess * a0 * S.a('tags', 0.6, off=1.5))
    if srt > 0:
        fr.text('回答的根本不是同一个问题', W / 2, 200, 34, 'serif_med', GOLD2, srt * a0 * (1 - fin), glow=0.2)
    # 公司画像公式
    if fin > 0:
        headline(fr, '描述一家公司  =', W / 2, 400, 54, GOLD, fin * a0)
        chips = [('主要机制', 'f1', LAYER_COL['L1']), ('辅助机制', 'f2', GOLD2), ('维持与再投资', 'f3', TEAL),
                 ('资本与治理', 'f4', LAYER_COL['L4']), ('时间位置', 'f5', VIOLET)]
        ws = [text_width(c[0], 'sans_bold', 38) + 52 for c in chips]
        tot = sum(ws) + 56 * 4
        x = W / 2 - tot / 2
        for (s, cue, col), w in zip(chips, ws):
            k = S.a(cue, 0.4, eback)
            if k > 0:
                label_pill(fr, s, x + w / 2, 560 - (1 - cl(k)) * 20, col, cl(k) * a0, 38, 'sans_bold', 26)
                fr.glow((x + w / 2, 560), 40, col, pulse(t, S.c(cue), 0.3) * a0)
            if cue != 'f5' and S.a(cue, 0.3) > 0:
                fr.text('+', x + w + 28, 556, 40, 'sans_light', WHITE, a0 * S.a(cue, 0.3))
            x += w + 56
        fr.text('而不是只贴一个标签', W / 2, 690, 30, 'sans_light', GREY, fin * a0 * S.a('f5', 0.6))
