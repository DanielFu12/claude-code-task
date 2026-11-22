"""场景 C：L2 维持成本、L3 再投资、莱特兄弟、L4 资本与治理、L5 时间与演化。"""
from common import *

RNG = np.random.default_rng(303)
DRAW = {}


def reg(name):
    def d(f):
        DRAW[name] = f
        return f
    return d


def bar(fr, x, y_base, h, w, col, a, label=None, val=None, up=True, fill=0.45, sub=None):
    y0, y1 = (y_base - h, y_base) if up else (y_base, y_base + h)
    if h > 1:
        fr.rrect_fill(x - w / 2, y0, x + w / 2, y1, 5, col, a * fill, 'E')
        fr.rrect(x - w / 2, y0, x + w / 2, y1, 5, lerpc(col, WHITE, 0.3), a * 0.9, 2)
    if val:
        fr.text(val, x, (y0 - 30) if up else (y1 + 30), 32, 'sans_black', lerpc(col, WHITE, 0.4), a, glow=0.2)
    if label:
        fr.text(label, x, 820, 28, 'sans_bold', lerpc(col, WHITE, 0.5), a)
    if sub:
        fr.text(sub, x, 860, 20, 'sans_light', GREY, a)


# ================================================================ L2 维持成本
@reg('L2')
def L2(fr, S):
    t = fr.t
    a0 = S.fade_out(0.45)
    oe = S.a('oe', 0.5)
    see = S.a('see', 0.6)
    gp = S.a('gap', 0.6)
    ha = ramp(t, S.start + 1.6, 0.5) * (1 - oe)
    if ha > 0:
        headline(fr, '不能只看回报率', W / 2, 440, 76, ORANGE, ha * a0)
        fr.text('还要看 —— 维持它的代价', W / 2, 560, 44, 'serif_med', WHITE, ha * a0 * ramp(t, S.start + 2.6, 0.5), glow=0.15)
    # 所有者盈余瀑布图
    wa = oe * (1 - see) * a0
    if wa > 0.01:
        headline(fr, '所有者盈余', W / 2, 220, 60, ORANGE, wa)
        fr.text('OWNER  EARNINGS', W / 2, 282, 22, 'corm', GOLD2, wa, track=0.3)
        fr.text('巴菲特 · 1986 年致股东信', W / 2, 318, 22, 'sans_light', GREY, wa)
        base = 760
        fr.line((360, base), (1560, base), GREY, wa * 0.5, 2)
        k1 = S.a('oe1', 0.5, eback); k2 = S.a('oe2', 0.5, eback); k3 = S.a('oe3', 0.5, eback)
        k4 = S.a('oe3', 0.6, eback, off=1.0)
        h1, h2, h3 = 280, 110, 170
        if k1 > 0: bar(fr, 520, base, h1 * cl(k1), 170, GOLD, wa * cl(k1), '报告利润')
        if k2 > 0:
            bar(fr, 800, base - h1, h2 * cl(k2), 170, TEAL, wa * cl(k2), '+ 折旧摊销', '+')
            fr.line((605, base - h1), (715, base - h1), GREY, wa * 0.5, 1)
        if k3 > 0:
            bar(fr, 1080, base - h1 - h2, h3 * cl(k3), 170, RED, wa * cl(k3), '− 维持性资本开支', '−', up=False)
            fr.line((885, base - h1 - h2), (995, base - h1 - h2), GREY, wa * 0.5, 1)
        if k4 > 0:
            bar(fr, 1360, base, (h1 + h2 - h3) * cl(k4), 170, ORANGE, wa * cl(k4), '= 所有者盈余', fill=0.65)
            fr.line((1165, base - h1 - h2 + h3), (1275, base - h1 - h2 + h3), GREY, wa * 0.5, 1)
            fr.glow((1360, base - 100), 90, ORANGE, wa * pulse(t, S.c('oe3') + 1.0, 0.5))
    # 喜诗糖果
    sa = see * (1 - gp) * a0
    if sa > 0.01:
        headline(fr, '喜诗糖果', 520, 230, 64, GOLD, sa)
        fr.text("SEE'S  CANDIES   1972 - 2007", 520, 295, 24, 'corm', GOLD2, sa, track=0.2)
        base = 830
        fr.line((300, base), (1620, base), GREY, sa * 0.5, 2)
        scale = 470 / 1350
        k1 = S.a('s1', 0.5, eback); k2 = S.a('s2', 0.5, eback); k3 = S.a('s3', 1.4, eo)
        if k1 > 0:
            bar(fr, 470, base, 25 * scale * cl(k1) + 2, 200, GOLD2, sa * cl(k1), None, None)
            fr.text('2500 万美元', 470, base - 70, 40, 'sans_black', GOLD2, sa * cl(k1))
            fr.text('1972 年买入价', 470, base + 40, 26, 'sans_bold', GREY, sa * cl(k1))
        if k2 > 0:
            bar(fr, 860, base, 32 * scale * cl(k2) + 2, 200, TEAL, sa * cl(k2))
            fr.text('+3200 万', 860, base - 70, 40, 'sans_black', TEAL, sa * cl(k2))
            fr.text('35 年追加资本', 860, base + 40, 26, 'sans_bold', GREY, sa * cl(k2))
        if k3 > 0:
            h = 1350 * scale * k3
            bar(fr, 1350, base, h, 240, GOLD, sa, None, None, fill=0.28 + 0.08 * kick_pulse(t))
            v = 13.5 * k3
            fr.text(f'{v:.1f} 亿美元', 1350, base - h - 60, 64, 'sans_black', GOLD, sa, mode='E', glow=0.4)
            fr.text('累计税前利润', 1350, base + 40, 26, 'sans_bold', GREY, sa)
            fr.glow((1350, base - h), 90, GOLD, sa * 0.35 * k3)
            fr.text('约 54 倍', 1110, 520, 36, 'serif_black', GOLD2, sa * S.a('s3', 0.5, off=1.4), glow=0.2)
    # 重置成本缺口
    if gp > 0:
        a = gp * a0
        headline(fr, '重置成本缺口', W / 2, 210, 60, RED, a)
        fr.text('先进制程制造：维持代际位置的资本开支 − 会计折旧', W / 2, 280, 28, 'sans_med', WHITE, a)
        x0, x1, base = 320, 1600, 800
        xs = np.linspace(x0, x1, 120)
        u = (xs - x0) / (x1 - x0)
        pr = S.a('gap', 2.0, lambda x: cl(x))
        dep = base - 120 - 90 * u
        cap = base - 140 - 380 * u ** 1.5
        k = max(2, int(pr * 119))
        poly = list(zip(xs[:k], cap[:k])) + list(zip(xs[:k][::-1], dep[:k][::-1]))
        if k > 2: fr.fillpoly(poly, RED, a * 0.22, 'E')
        draw_line_chart(fr, xs, dep, GREY, a, 3, pr)
        draw_line_chart(fr, xs, cap, RED, a, 4, pr)
        fr.text('会计折旧', x1 + 10, dep[-1], 26, 'sans_bold', GREY, a * cl(pr * 2 - 1), anchor='l')
        fr.text('维持性资本开支', x1 + 10, cap[-1], 26, 'sans_bold', RED, a * cl(pr * 2 - 1), anchor='l')
        fr.text('报表利润 > 真实所有者盈余', W / 2 + 80, 540, 40, 'sans_black', C(255, 160, 160), a * S.a('gap', 0.5, off=2.0), glow=0.2)


# ================================================================ L3 再投资（3D 立方体）
KP = {'k1': ((1, 1, -1), '复利机器', 'Costco（扩张期）', GOLD),
      'k2': ((1, 1, 1), '高回报跑步机', '先进制程代工', TEAL),
      'k3': ((1, -1, -1), '优质现金牛', '喜诗糖果', ORANGE),
      'k4': ((0.1, 1, 1), '优秀生意', '公用事业 · 铁路', BLUE),
      'k5': ((-1, 1, 1), '毁灭价值的跑步机', '航空', RED)}
KDESC = {'k1': '回报高 · 容量大 · 可不投', 'k2': '回报高 · 必须一直投', 'k3': '存量回报高 · 容量小',
         'k4': '略高于资本成本 · 监管要求投', 'k5': '回报低 · 还必须不停投'}


@reg('L3')
def L3(fr, S):
    t = fr.t
    a0 = S.fade_out(0.45)
    ax = S.a('axes', 0.8)
    qa = ramp(t, S.start + 1.6, 0.6) * (1 - ax)
    if qa > 0:
        fr.text('“', 300, 330, 150, 'serif_black', TEAL, qa * 0.5, mode='E', glow=0.3)
        typeline(fr, '最值得拥有的生意，', W / 2, 420, 66, WHITE, qa * a0, S.start + 1.8, 8, 'serif_black')
        typeline(fr, '能长期把大量增量资本，以高回报投出去。', W / 2, 530, 56, TEAL, qa * a0, S.start + 3.4, 9, 'serif_black', glow=0.3)
        fr.text('—— 巴菲特 · 1992 年致股东信', W / 2 + 520, 640, 28, 'serif_med', GREY, qa * a0 * ramp(t, S.start + 6, 0.5), anchor='r')
    if ax <= 0: return
    a = ax * a0
    cx, cy = 700, 590
    yaw = 0.65 + 0.12 * math.sin(t * 0.3) + 0.25 * eio((t - S.c('k1')) / 20)
    pitch = 0.32
    R = 230
    corners = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float) * R
    P, Z = proj3(corners, yaw, pitch, cx, cy, 1400, 1500)
    for i in range(8):
        for j in range(i + 1, 8):
            if np.sum(np.abs(corners[i] - corners[j]) > 1) == 1:
                fr.line(tuple(P[i]), tuple(P[j]), ICE, a * 0.28, 1)
    # 坐标轴
    axes = [((-1, -1, -1), (1.35, -1, -1), '回报', GOLD, 'a1'), ((-1, -1, -1), (-1, 1.35, -1), '容量', TEAL, 'a2'),
            ((-1, -1, -1), (-1, -1, 1.35), '强制性', RED, 'a3')]
    for p0, p1, nm, col, cue in axes:
        k = S.a(cue, 0.5)
        if k <= 0: continue
        Q, _ = proj3(np.array([p0, p1]) * R, yaw, pitch, cx, cy, 1400, 1500)
        q1 = Q[0] + (Q[1] - Q[0]) * k
        fr.arrow(tuple(Q[0]), tuple(q1), col, a * k, 3, 16)
        fr.text(nm, q1[0] + (Q[1][0] - Q[0][0]) * 0.12, q1[1] + (Q[1][1] - Q[0][1]) * 0.12, 38, 'sans_black', col, a * k, glow=0.3)
        fr.glow(tuple(q1), 30, col, a * pulse(t, S.c(cue), 0.4))
    fr.text('能不能选择不投？', cx, 930 - 30, 1, 'sans_med', WHITE, 0)
    # 五种组合
    last = None
    for key in ('k1', 'k2', 'k3', 'k4', 'k5'):
        if t >= S.c(key) - 0.05: last = key
    for idx, key in enumerate(('k1', 'k2', 'k3', 'k4', 'k5')):
        k = S.a(key, 0.45, eback)
        if k <= 0: continue
        pos, nm, ex, col = KP[key]
        Q, _ = proj3(np.array([pos]) * R, yaw, pitch, cx, cy, 1400, 1500)
        q = tuple(Q[0])
        on = key == last
        ka = cl(k) * a
        fr.disc(q, 10 + 6 * pulse(t, S.c(key), 0.4), col, ka)
        fr.glow(q, 30 + (20 if on else 0), col, ka * (0.9 if on else 0.5))
        # 右侧列表
        ly = 300 + idx * 128
        lx = 1180
        fr.panel(lx, ly - 52, lx + 600, ly + 52, col, ka * (1 if on else 0.55), 12, fill=0.12 if on else 0.04)
        fr.text(nm, lx + 24, ly - 16, 34, 'sans_black', lerpc(col, WHITE, 0.5), ka * (1 if on else 0.6), anchor='l')
        fr.text(KDESC[key], lx + 24, ly + 24, 22, 'sans_med', lerpc(col, WHITE, 0.3), ka * (1 if on else 0.6), anchor='l')
        fr.text(ex, lx + 580, ly - 14, 24, 'sans_bold', col, ka * (1 if on else 0.6), anchor='r')
        if on:
            fr.line(q, (lx, ly), col, ka * 0.5, 1)


# ================================================================ 莱特兄弟 + 现金牛
SMOKE = RNG.uniform(0, 1, (160, 2))


@reg('kitty')
def kitty(fr, S):
    t = fr.t
    a0 = S.fade_out(0.45)
    cw = S.a('cow', 0.6)
    pa = a0 * (1 - cw)
    if pa > 0.01:
        fr.text('1903 · 基蒂霍克', 300, 220, 34, 'serif_med', GOLD2, pa * S.a('kh', 0.5), anchor='l')
        ts = S.c('shot')
        fly = cl((t - S.c('kh') + 0.5) / 5.5)
        px = lerp(160, 1700, fly) if t < ts else lerp(160, 1700, cl((ts - S.c('kh') + 0.5) / 5.5))
        py = 430 + 18 * math.sin(t * 2.2)
        ang = 0
        if t >= ts:
            d = t - ts
            px += d * 160
            py += d * d * 260 + d * 40
            ang = d * 4
        # 机身（旋转）
        sc = 1.0
        base = [(-60, 0), (50, -4), (62, 0), (50, 5), (-60, 4)]
        wing = [(-5, 0), (10, -45), (22, -45), (15, 0)]
        wing2 = [(-5, 3), (10, 45), (22, 45), (15, 3)]
        tail = [(-50, 0), (-62, -18), (-55, -18), (-42, 0)]
        for shp in (base, wing, wing2, tail):
            pts = [(px + 1.4 * (x * math.cos(ang) - y * math.sin(ang)), py + 1.4 * (x * math.sin(ang) + y * math.cos(ang))) for x, y in shp]
            fr.poly(pts, ICE, pa, 3, closed=True)
        if t >= ts:
            d = t - ts
            n = int(min(d, 2) * 80)
            sx = px - SMOKE[:n, 0] * d * 160
            sy = py - SMOKE[:n, 0] * (d * d * 260 + d * 40) * 0.95
            fr.dots(sx, sy, GREY, pa * 0.4 * (1 - SMOKE[:n, 0] * 0.5), 1, 'L')
            fr.flash = max(fr.flash, 0.4 * pulse(t, ts, 0.06))
            bang = ramp(t, ts, 0.25, eback) * (1 - ramp(t, ts + 1.2, 0.4))
            headline(fr, '砰！', 1250, 300, int(130 * cl(bang)), RED, pa * cl(bang))
        else:
            # 准星锁定
            lk = ramp(t, ts - 1.2, 1.0, eio)
            if lk > 0:
                r = lerp(260, 70, lk)
                fr.circle((px, py), r, RED, pa * lk, 2)
                for k in range(4):
                    an = k * math.pi / 2
                    fr.line((px + math.cos(an) * r * 0.6, py + math.sin(an) * r * 0.6),
                            (px + math.cos(an) * r * 1.25, py + math.sin(an) * r * 1.25), RED, pa * lk, 2)
        fr.text('“他应该把飞机打下来。”', W / 2, 780, 46, 'serif_black', GOLD2, pa * ramp(t, ts + 0.3, 0.5), glow=0.2)
        fr.text('—— 巴菲特 · 2007 年致股东信（大意）', W / 2, 850, 24, 'sans_light', GREY, pa * ramp(t, ts + 0.8, 0.5))
    if cw <= 0: return
    a = cw * a0
    headline(fr, '现金牛：钱去哪？', W / 2, 220, 60, GOLD, a)
    src = (420, 560)
    draw_icon(fr, 'coins', src[0], src[1], 150, GOLD, a, 3)
    fr.glow(src, 90, GOLD, a * 0.35)
    fr.text('盈余现金', src[0], src[1] + 120, 30, 'sans_bold', GOLD2, a)
    for cue, end, col, t1, t2, good in (('cow1', (1350, 400), GOLD, '优秀的配置者', '伯克希尔', True),
                                         ('cow2', (1350, 720), GREY, '低回报多元化', '机构惯性', False)):
        k = S.a(cue, 0.6)
        if k <= 0: continue
        mid = (900, end[1])
        pts = [src, (src[0] + 120, src[1]), (700, end[1]), end]
        cur = [src[0] + 120 + (end[0] - src[0] - 120) * u for u in np.linspace(0, 1, 50)]
        xs = np.array([src[0] + 90] + [x for x in np.linspace(src[0] + 120, end[0] - 60, 50)])
        ys = np.array([src[1]] + [src[1] + (end[1] - src[1]) * eio((x - src[0] - 120) / 280) for x in np.linspace(src[0] + 120, end[0] - 60, 50)])
        draw_line_chart(fr, xs, ys, col, a * k, 4 if good else 3, k, head=False)
        if good:
            ph = (t * 0.5 + np.linspace(0, 1, 26)) % 1.0
            idx = (ph * (len(xs) - 1)).astype(int)
            fr.dots(xs[idx], ys[idx], GOLD2, a * k * 0.9, 1)
        kk = ramp(t, S.c(cue) + 0.4, 0.5, eback)
        if kk > 0:
            fr.panel(end[0], end[1] - 70, end[0] + 400, end[1] + 70, col, a * cl(kk), 14, fill=0.12 if good else 0.03)
            fr.text(t1, end[0] + 30, end[1] - 22, 30, 'sans_bold', WHITE if good else GREY, a * cl(kk), anchor='l')
            fr.text(t2, end[0] + 30, end[1] + 26, 40, 'sans_black', GOLD if good else GREY, a * cl(kk), anchor='l', glow=0.3 if good else 0)
            if good:
                for b in range(5):
                    hh = 18 * (1.45 ** b) * eo((t - S.c(cue) - 0.6 - b * 0.15) / 0.5)
                    fr.rect(end[0] + 300 + b * 16, end[1] + 50 - hh, end[0] + 312 + b * 16, end[1] + 50, GOLD, a * 0.6, 'E')
            else:
                fr.text('↓', end[0] + 340, end[1], 50, 'sans_black', GREY, a * cl(kk))


# ================================================================ L4 资本与治理
@reg('L4')
def L4(fr, S):
    t = fr.t
    a0 = S.fade_out(0.45)
    am = S.at(min(S.c('amp'), S.start + 1.8), 0.6)
    br = S.a('bridge', 0.6)
    fl = S.a('fl', 0.6)
    bb = S.a('bb', 0.6)
    # 放大器
    aa = am * (1 - br) * a0
    if aa > 0.01:
        headline(fr, '只放大，不创造', W / 2, 230, 68, BLUE, aa)
        cy = 590
        # 输入
        bar_h = 120
        fr.text('经营结果', 380, 400, 30, 'sans_bold', TEAL, aa)
        fr.rrect_fill(330, cy - bar_h / 2, 430, cy + bar_h / 2, 6, TEAL, aa * 0.45, 'E')
        fr.text('ROIC', 380, cy + 110, 30, 'orb', TEAL, aa, mode='E')
        # 杠杆透镜
        fr.poly([(760, cy - 80), (1060, cy - 200), (1060, cy + 200), (760, cy + 80)], BLUE, aa, 3, closed=True)
        fr.fillpoly([(760, cy - 80), (1060, cy - 200), (1060, cy + 200), (760, cy + 80)], BLUE, aa * 0.12, 'L')
        fr.text('杠杆', 910, cy, 46, 'sans_black', lerpc(BLUE, WHITE, 0.4), aa, glow=0.3)
        ph = (t * 0.8 + np.linspace(0, 1, 40)) % 1
        fr.dots(430 + ph * 330, cy + np.sin(ph * 20) * 6, TEAL, aa * 0.7, 1)
        # 输出：上下都被放大
        sw = math.sin(t * 1.6)
        hu = 160 + 120 * max(sw, 0)
        hd = 160 + 120 * max(-sw, 0)
        fr.rrect_fill(1200, cy - hu, 1300, cy, 6, GREEN, aa * 0.45, 'E')
        fr.rrect_fill(1200, cy, 1300, cy + hd, 6, RED, aa * 0.45, 'E')
        fr.text('好时更好', 1330, cy - 120, 30, 'sans_bold', GREEN, aa, anchor='l')
        fr.text('坏时更坏', 1330, cy + 120, 30, 'sans_bold', RED, aa, anchor='l')
        fr.text('ROE', 1250, cy - hu - 40, 30, 'orb', WHITE, aa, mode='E')
    # ROE 桥
    ba = br * (1 - fl) * a0
    if ba > 0.01:
        fr.text('ROE 与 ROIC 之间的桥', W / 2, 250, 34, 'serif_med', GOLD2, ba, glow=0.15)
        toks = [('ROE', WHITE, 'orb'), ('≈', GREY, 'sans_light'), ('ROIC', TEAL, 'orb'), ('+', GREY, 'sans_light'),
                ('(ROIC − 税后债务成本)', BLUE, 'sans_black'), ('×', GREY, 'sans_light'), ('净负债 / 股东权益', BLUE, 'sans_black')]
        sz = 48
        ws = [text_width(s, f, int(sz * (0.85 if f == 'orb' else 1))) for s, _, f in toks]
        x = W / 2 - (sum(ws) + 24 * 6) / 2
        xs = []
        for i, ((s, col, f), w_) in enumerate(zip(toks, ws)):
            k = ramp(t, S.c('bridge') + i * 0.35, 0.4, eback)
            fr.text(s, x + w_ / 2, 470 - (1 - cl(k)) * 20, int(sz * (0.85 if f == 'orb' else 1)), f, col, ba * cl(k),
                    mode='E' if f == 'orb' else 'L', glow=0.2)
            xs.append((x, x + w_))
            x += w_ + 24
        lv = S.a('lev', 0.5)
        if lv > 0:
            x0, x1 = xs[4][0], xs[6][1]
            fr.poly([(x0, 520), (x0, 545), (x1, 545), (x1, 520)], RED, ba * lv, 3)
            fr.line(((x0 + x1) / 2, 545), ((x0 + x1) / 2, 590), RED, ba * lv, 3)
            headline(fr, '来自杠杆 ≠ 经营能力', (x0 + x1) / 2, 650, 50, RED, ba * lv)
            fr.poly([(xs[2][0], 520), (xs[2][0], 545), (xs[2][1], 545), (xs[2][1], 520)], TEAL, ba * lv, 3)
            fr.text('经营', (xs[2][0] + xs[2][1]) / 2, 590, 30, 'sans_bold', TEAL, ba * lv)
    # 浮存金
    fa = fl * (1 - bb) * a0
    if fa > 0.01:
        headline(fr, '保险浮存金', W / 2, 230, 64, BLUE, fa)
        fr.text('一种特别的杠杆：成本取决于承保结果', W / 2, 300, 28, 'sans_med', WHITE, fa)
        # 储水罐
        cx, cy = W / 2, 590
        fr.rrect(cx - 110, cy - 150, cx + 110, cy + 150, 20, ICE, fa, 3)
        lvl = cy + 150 - 220 - 12 * math.sin(t * 2)
        xs = np.linspace(cx - 106, cx + 106, 40)
        wave = lvl + 6 * np.sin(xs * 0.05 + t * 4)
        fr.fillpoly(list(zip(xs, wave)) + [(cx + 106, cy + 146), (cx - 106, cy + 146)], BLUE, fa * 0.35, 'E')
        fr.text('浮存金', cx, cy + 40, 34, 'sans_black', WHITE, fa)
        for cue, side, col, t1, t2 in (('fl1', -1, GREEN, '承保盈利', '成本为负'), ('fl2', 1, RED, '承保亏损', '比债务还贵')):
            k = S.a(cue, 0.5, eback)
            if k <= 0: continue
            x = cx + side * 480
            fr.panel(x - 230, cy - 120, x + 230, cy + 120, col, fa * cl(k), 16, fill=0.1)
            fr.text(t1, x, cy - 50, 36, 'sans_bold', WHITE, fa * cl(k))
            headline(fr, t2, x, cy + 30, 56, col, fa * cl(k))
            fr.arrow((cx + side * 120, cy), (x - side * 235, cy), col, fa * cl(k), 3, 14)
    # 回购
    if bb > 0:
        a = bb * a0
        headline(fr, '回购', W / 2, 220, 64, BLUE, a)
        x0, x1, iv = 300, 1620, 600
        xs = np.linspace(x0, x1, 300)
        u = (xs - x0) / (x1 - x0)
        price = iv - 150 * np.sin(u * 2 * np.pi * 1.5 + math.pi) * (0.7 + 0.3 * np.sin(u * 13))
        pr = S.a('bb', 1.6, lambda x: cl(x))
        fr.line((x0, iv), (x1, iv), GOLD, a, 3)
        fr.text('内在价值', x1 + 12, iv, 26, 'sans_bold', GOLD, a, anchor='l')
        draw_line_chart(fr, xs, price, ICE, a * 0.9, 2, pr)
        fr.text('股价', x0, price[0] - 30, 24, 'sans_med', ICE, a * 0.8, anchor='l')
        k1 = S.a('bb1', 0.5)
        if k1 > 0:
            m = (price > iv) & (u < pr)
            for i in np.where(m)[0][::3]:
                fr.line((xs[i], iv), (xs[i], price[i]), GREEN, a * k1 * 0.5, 2)
            fr.text('低于内在价值回购：增厚每股价值', W / 2 - 300, 860, 32, 'sans_black', GREEN, a * k1)
        k2 = S.a('bb2', 0.5)
        if k2 > 0:
            m = (price < iv) & (u < pr)
            for i in np.where(m)[0][::3]:
                fr.line((xs[i], iv), (xs[i], price[i]), RED, a * k2 * 0.5, 2)
            fr.text('高于内在价值：把价值送给卖出者', W / 2 + 330, 340, 32, 'sans_black', RED, a * k2)


# ================================================================ 激励与 3G
@reg('gov')
def gov(fr, S):
    t = fr.t
    a0 = S.fade_out(0.45)
    g3 = S.a('g3', 0.6)
    ia = a0 * (1 - g3)
    if ia > 0.01:
        fr.text('“', 360, 230, 120, 'serif_black', BLUE, ia * 0.5, mode='E', glow=0.3)
        typeline(fr, '给我看激励，我就告诉你结果。', W / 2, 270, 62, WHITE, ia * S.a('inc', 0.3), S.c('inc'), 10, 'serif_black', glow=0.25)
        fr.text('—— 查理 · 芒格', W / 2 + 430, 350, 26, 'serif_med', GREY, ia * S.a('inc', 0.5, off=1.6), anchor='r')
        for cue, y, col, k1t, res in (('inc1', 520, RED, '按规模 · 每股收益考核', '低回报并购'),
                                       ('inc2', 720, GREEN, '按 ROIC · 每股内在价值考核', '与股东站在一起')):
            k = S.a(cue, 0.5, eback)
            if k <= 0: continue
            ka = cl(k) * ia
            fr.panel(260, y - 60, 900, y + 60, col, ka, 14, fill=0.06)
            fr.text(k1t, 580, y, 36, 'sans_bold', WHITE, ka)
            ar = S.a(cue, 0.6, off=0.3)
            fr.arrow((920, y), (920 + 200 * ar, y), col, ka, 4, 18)
            if ar > 0.5:
                headline(fr, res, 1420, y, 56, col, ka * cl(ar * 2 - 1))
    if g3 <= 0: return
    a = g3 * a0
    kr = S.a('kr', 0.5)
    ga = a * (1 - kr)
    if ga > 0.01:
        headline(fr, '3G 模式 · 零基预算', W / 2, 220, 58, BLUE, ga)
        base = 760
        bars_ = [('冗余', 230, GREY), ('冗余', 200, GREY), ('冗余', 260, GREY), ('维持成本', 240, ORANGE), ('品牌投入', 210, ORANGE), ('研发', 250, ORANGE)]
        cut_y = 520
        sweep = S.a('g3', 2.2, eio, off=0.5)
        sweep2 = S.a('cut', 1.8, eio)
        for i, (nm, h, col) in enumerate(bars_):
            x = 420 + i * 220
            done = sweep * 3 > i if i < 3 else sweep2 * 3 > i - 3
            hh = min(h, base - cut_y) if done else h
            if i < 3 and done: hh = h * 0.35
            c2 = RED if (i >= 3 and done) else col
            bar(fr, x, base, hh, 120, c2, ga, None)
            fr.text(nm, x, base + 40, 28, 'sans_bold', lerpc(c2, WHITE, 0.4), ga)
        sx = 300 + sweep * 660 + sweep2 * 660
        if 0 < sweep < 1 or 0 < sweep2 < 1:
            fr.line((sx, cut_y - 140), (sx, base + 10), WHITE, ga * 0.8, 2)
            fr.glow((sx, cut_y), 30, WHITE, ga)
        if sweep > 0.95:
            fr.text('去掉冗余 ✓', 640, 400, 36, 'sans_black', GREEN, ga * cl((sweep - 0.95) * 20))
        if sweep2 > 0.5:
            headline(fr, '拿未来换现在', 1300, 400, 52, RED, ga * cl(sweep2 * 2 - 1))
    if kr > 0:
        lt = t - S.c('kr')
        headline(fr, '卡夫亨氏 · 2019', W / 2, 300, 56, RED, a * kr)
        v = 154 * eo(lt / 1.2)
        fr.text(f'−{v:.0f} 亿美元', W / 2, 520, 150, 'sans_black', RED, a * kr, mode='E', glow=0.45)
        fr.text('商誉与无形资产减值（约）', W / 2, 660, 34, 'sans_med', C(255, 170, 170), a * ramp(t, S.c('kr') + 0.6, 0.5))
        fr.text('“我们为卡夫付了太高的价格。” —— 巴菲特', W / 2, 760, 32, 'serif_med', GREY, a * ramp(t, S.c('kr') + 1.6, 0.5))
        fr.shake = (5 * pulse(t, S.c('kr'), 0.1) * math.sin(t * 90), 0)


# ================================================================ L5 时间与演化
@reg('L5')
def L5(fr, S):
    t = fr.t
    a0 = S.fade_out(0.45)
    fd = S.at(min(S.c('fade'), S.start + 1.8), 0.6)
    cy_ = S.a('cyc', 0.6)
    mg = S.a('mig', 0.6)
    cf = S.a('conf', 0.6)
    # 衰减曲线
    fa = fd * (1 - cy_) * a0
    if fa > 0.01:
        headline(fr, '超额回报终会回落', W / 2, 220, 58, VIOLET, fa)
        x0, x1, wacc, top = 320, 1600, 780, 360
        fr.line((x0, wacc), (x1, wacc), C(255, 120, 120), fa, 2)
        fr.text('WACC', x1 + 10, wacc, 22, 'orb', C(255, 140, 140), fa, anchor='l')
        fr.line((x0, wacc), (x0, top - 40), GREY, fa * 0.5, 2)
        fr.text('超额 ROIC', x0 - 14, top - 40, 22, 'sans_med', GREY, fa, anchor='r')
        xs = np.linspace(x0, x1, 200)
        u = (xs - x0) / (x1 - x0)
        pr = S.a('fade', 2.2, lambda x: cl(x))
        for rate, col, nm in ((1.2, GOLD, '强护城河：慢衰减'), (3.5, TEAL, ''), (9, RED, '弱优势：快衰减')):
            ys = wacc - (wacc - top) * np.exp(-u * rate)
            if rate == 1.2:
                k = max(2, int(pr * 199))
                fr.fillpoly(list(zip(xs[:k], ys[:k])) + [(xs[k - 1], wacc), (x0, wacc)], GOLD, fa * 0.16, 'E')
            draw_line_chart(fr, xs, ys, col, fa, 3, pr)
            if nm:
                j = 70 if rate == 1.2 else 40
                fr.text(nm, xs[j] + 20, ys[j] - 26 if rate == 1.2 else wacc - 30, 26, 'sans_bold', col, fa * cl(pr * 3 - 1), anchor='l')
        k2 = S.a('fade2', 0.6)
        if k2 > 0:
            fr.poly([(x0, wacc + 40), (x0, wacc + 56), (x1 * 0.82 + x0 * 0.18, wacc + 56), (x1 * 0.82 + x0 * 0.18, wacc + 40)], GOLD2, fa * k2, 2)
            fr.text('竞争优势期 = 求和的长度', (x0 + x1 * 0.82 + x0 * 0.18) / 2, wacc + 92, 30, 'sans_black', GOLD2, fa * k2)
    # 周期位置
    ca = cy_ * (1 - mg) * a0
    if ca > 0.01:
        headline(fr, '周期位置会骗人', W / 2, 220, 58, VIOLET, ca)
        x0, x1, mid = 300, 1620, 600
        xs = np.linspace(x0, x1, 300)
        u = (xs - x0) / (x1 - x0)
        ys = mid - 190 * np.sin(u * 2 * np.pi * 1.25)
        draw_line_chart(fr, xs, ys, VIOLET, ca, 3, S.a('cyc', 1.6, lambda x: cl(x)))
        px = x0 + (x1 - x0) * 0.2
        k = S.a('cyc', 0.5, off=0.6)
        if k > 0:
            fr.circle((px, mid - 190), 16, GOLD, ca * k, 3)
            fr.text('高点：平庸的生意看起来很伟大', px + 30, mid - 250, 32, 'sans_black', GOLD, ca * k, anchor='l')
        tx = x0 + (x1 - x0) * 0.6
        k = S.a('cyc2', 0.5)
        if k > 0:
            fr.circle((tx, mid + 190), 16, TEAL, ca * k, 3)
            fr.text('低点：好生意显得平庸', tx - 30, mid + 250, 32, 'sans_black', TEAL, ca * k, anchor='r')
    # 模型迁移
    ma = mg * (1 - cf) * a0
    if ma > 0.01:
        headline(fr, '优势会迁移', W / 2, 200, 58, VIOLET, ma)
        src = (480, 470)
        fr.panel(src[0] - 170, src[1] - 60, src[0] + 170, src[1] + 60, VIOLET, ma, 14, fill=0.15)
        fr.text('技术领先', src[0], src[1], 40, 'sans_black', WHITE, ma)
        for cue, dst, col, t1, t2 in (('m1', (1300, 340), GOLD, '标准 · 生态锁定', '英特尔 x86 · 英伟达 CUDA'),
                                        ('m2', (1300, 600), RED, '被追上 → 商品周期', '存储芯片 · 多数光伏')):
            k = S.a(cue, 0.6)
            if k <= 0: continue
            p1 = (src[0] + 170, src[1])
            p2 = (lerp(p1[0], dst[0] - 230, k), lerp(p1[1], dst[1], k))
            fr.arrow(p1, p2, col, ma, 4, 18)
            if k > 0.7:
                kk = cl(k * 3.3 - 2.3)
                fr.panel(dst[0] - 230, dst[1] - 70, dst[0] + 330, dst[1] + 70, col, ma * kk, 14, fill=0.12)
                fr.text(t1, dst[0] + 50, dst[1] - 20, 36, 'sans_black', lerpc(col, WHITE, 0.4), ma * kk, glow=0.2)
                fr.text(t2, dst[0] + 50, dst[1] + 30, 24, 'sans_med', lerpc(col, WHITE, 0.2), ma * kk)
                ph = (t * 0.7 + np.linspace(0, 1, 12)) % 1
                fr.dots(p1[0] + (p2[0] - p1[0]) * ph, p1[1] + (p2[1] - p1[1]) * ph, col, ma * 0.8, 1)
        k3 = S.a('m3', 0.6)
        if k3 > 0:
            y = 820
            fr.panel(310, y - 55, 650, y + 55, ORANGE, ma * k3, 14, fill=0.1)
            fr.text('收费桥', 480, y, 38, 'sans_black', WHITE, ma * k3)
            fr.arrow((660, y), (660 + 400 * k3, y), RED, ma * k3, 4, 18)
            # 被绕过：弧线
            fr.arc((480, y - 10), 220, math.pi * 1.05, math.pi * 1.95, ICE, ma * k3 * 0.6, 2)
            fr.text('被技术绕过 → 收割', 1300, y - 18, 36, 'sans_black', RED, ma * k3, glow=0.2)
            fr.text('互联网之于地方报纸', 1300, y + 32, 24, 'sans_med', C(255, 170, 170), ma * k3)
    # 把握程度 → 安全边际
    if cf > 0:
        a = cf * a0
        headline(fr, '标注把握程度', W / 2, 220, 58, VIOLET, a)
        levels = [('高', 0.25, TEAL), ('中', 0.5, GOLD), ('低', 0.85, RED)]
        for i, (nm, mos, col) in enumerate(levels):
            k = ramp(t, S.c('conf') + 0.8 + i * 0.5, 0.5, eback)
            if k <= 0: continue
            y = 420 + i * 130
            fr.text(f'把握 {nm}', 470, y, 40, 'sans_black', col, a * cl(k), anchor='r')
            fr.rect(510, y - 22, 510 + 900, y + 22, (1, 1, 1), a * 0.05, 'L')
            fr.rect(510, y - 22, 510 + 900 * mos * eo(k), y + 22, col, a * 0.5, 'E')
            fr.text('安全边际', 510 + 900 * mos * eo(k) + 16, y, 26, 'sans_bold', lerpc(col, WHITE, 0.4), a * cl(k), anchor='l')
        hk = S.a('hard', 0.5, eback)
        if hk > 0:
            bx, by = 1560, 640
            fr.panel(bx - 130, by - 20, bx + 130, by + 160, GREY, a * cl(hk), 10, fill=0.05)
            fr.text('太难', bx, by + 90, 52, 'serif_black', WHITE, a * cl(hk), glow=0.2)
            for j in range(3):
                d = ramp(t, S.c('hard') + 0.3 + j * 0.35, 0.4, eo)
                if d > 0:
                    yy = lerp(300, by + 10 - j * 10, d)
                    fr.rrect(bx - 70 + j * 20, yy - 30, bx + 30 + j * 20, yy + 30, 6, GREY, a * 0.8, 2)
