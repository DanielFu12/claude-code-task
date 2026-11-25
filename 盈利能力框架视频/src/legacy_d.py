"""场景 D：组合规则、评估流程、五个测试、五条规则、结语、片尾。"""
from common import *
from brand import load_logo

RNG = np.random.default_rng(404)
DRAW = {}


def reg(name):
    def d(f):
        DRAW[name] = f
        return f
    return d


# ================================================================ 组合规则
PAIRS = [
    (['技术领先', '生态锁定'], '结构性优势', ['技术领先', '没有锁定'], '停不下的跑步机'),
    (['现金牛', '优秀配置者'], '伯克希尔', ['现金牛', '糟糕配置者'], '价值黑洞'),
    (['强周期', '低成本', '低杠杆'], '底部收割对手', ['强周期', '高杠杆'], '迟早出局'),
    (['规模分享', '克制'], '飞轮越转越快', ['规模优势', '收割利润率'], '自毁护城河'),
]


def combo_row(fr, toks, result, y, col, t0, a, good):
    t = fr.t
    k = ramp(t, t0 - 0.35, 0.35, eo)
    if k <= 0: return
    hit = ramp(t, t0, 0.35, eback)
    ws = [text_width(s, 'sans_black', 40) + 50 for s in toks]
    gap = 70
    total = sum(ws) + gap * (len(toks) - 1)
    x = 760 - total
    for i, (s, w) in enumerate(zip(toks, ws)):
        cx = x + w / 2
        side = -1 if i == 0 else 1
        off = (1 - k) * 600 * (-1 if i < len(toks) - 1 else -1) * (1 + i * 0.3)
        label_pill(fr, s, cx + off, y, lerpc(GREY, col, 0.4), a * k, 40, 'sans_black', 25, fill=0.12)
        if i < len(toks) - 1:
            fr.text('+', x + w + gap / 2 + off, y - 4, 48, 'sans_light', WHITE, a * k)
        x += w + gap
    fr.arrow((800, y), (800 + 140 * cl(hit), y), col, a * cl(hit), 5, 20)
    if hit > 0:
        sc = lerp(1.6, 1.0, cl(hit))
        rx = 1340
        fr.panel(rx - 330 * sc, y - 64 * sc, rx + 330 * sc, y + 64 * sc, col, a * cl(hit), 18, fill=0.18, th=3)
        headline(fr, result, rx - 20, y, int(56 * sc), col, a * cl(hit), fnt='sans_black', glow=0.45, track=0.02)
        draw_icon(fr, 'check' if good else 'cross', rx + 270 * sc, y, 50 * sc, col, a * cl(hit), 5)
        shockwave(fr, (rx, y), t0, col, t, 1600, 0.6, 3, a)
        fr.glow((rx, y), 160, col, a * pulse(t, t0, 0.3) * 0.8)


@reg('combo')
def combo(fr, S):
    t = fr.t
    a0 = S.fade_out(0.4)
    ha = ramp(t, S.start + 1.4, 0.5) * (1 - S.a('c1', 0.3, off=-0.6))
    if ha > 0:
        headline(fr, '一张作战地图', W / 2, 520, 96, GOLD, ha * a0)
    cues = [('c1', 'c2'), ('c3', 'c4'), ('c5', 'c6'), ('c7', 'c8')]
    for i, (p, n) in enumerate(cues):
        t_in = S.c(p)
        t_out = S.c(cues[i + 1][0]) - 0.45 if i < 3 else S.end + 1
        if t < t_in - 0.5 or t > t_out + 0.45: continue
        out = ramp(t, t_out, 0.4, ei)
        a = a0 * (1 - out)
        dx = -out * 300
        good, res, bad, res2 = PAIRS[i]
        fr.text(f'{i + 1} / 4', 140, 240, 30, 'orb', GOLD2, a * ramp(t, t_in - 0.4, 0.3), anchor='l', mode='E')
        fr.cam = (dx, 0)
        combo_row(fr, good, res, 420, GOLD if i != 1 else GOLD, t_in, a, True)
        combo_row(fr, bad, res2, 680, RED, S.c(n), a, False)
        fr.line((260, 550), (1660, 550), GREY, a * 0.15 * ramp(t, t_in, 0.4), 1)
        for c in (p, n):
            pl = pulse(t, S.c(c), 0.25)
            fr.zoom *= 1 + 0.02 * pl
            fr.ca = max(fr.ca, 4 * pl)


# ================================================================ 评估流程
STEPS = [('生存排雷', '能活下来吗', RED), ('价值杆', '谁拿走价值', LAYER_COL['L1']), ('拆分 ROIC', '剔除周期还剩多少', LAYER_COL['L1']),
         ('维持成本', '保住要花多少', ORANGE), ('再投资', '能不能不投', TEAL), ('资本与治理', '激励指向哪里', LAYER_COL['L4']),
         ('时间', '能持续多久', VIOLET), ('估值', '安全边际多大', GOLD)]


@reg('proc')
def proc(fr, S):
    t = fr.t
    a0 = S.fade_out(0.4)
    headline(fr, '八步评估流程', W / 2, 230, 64, CYAN, a0 * ramp(t, S.start + 1.4, 0.5))
    xs = [190 + i * 220 for i in range(8)]
    y = 560
    lit = -1
    for i in range(8):
        if t >= S.c(f'p{i + 1}'): lit = i
    # 轨道
    fr.line((xs[0], y), (xs[-1], y), GREY, a0 * 0.25 * ramp(t, S.start + 1.6, 0.6), 2)
    if lit >= 0:
        tl = S.c(f'p{lit + 1}')
        nxt = S.c(f'p{min(lit + 2, 8)}')
        u = cl((t - tl) / max(nxt - tl, 0.3)) if lit < 7 else 0
        xe = xs[lit] + (xs[min(lit + 1, 7)] - xs[lit]) * u * 0.0
        fr.line((xs[0], y), (xs[lit], y), GOLD2, a0 * 0.8, 4)
        fr.glow((xs[lit], y), 30, GOLD, a0)
    for i, (nm, q, col) in enumerate(STEPS):
        tc = S.c(f'p{i + 1}')
        k = ramp(t, tc, 0.4, eback)
        base_a = 0.25 * ramp(t, S.start + 1.6 + i * 0.06, 0.4)
        r = 54 if i < 7 else 70
        if k <= 0:
            fr.circle((xs[i], y), r, GREY, a0 * base_a, 2)
            continue
        cur = (i == lit)
        a = a0 * cl(k) * (1.0 if cur or t > S.c('p8') + 0.6 else 0.55)
        em = 1.0 + (0.22 if cur else 0.0) * (0.6 + 0.4 * pulse(t, tc, 0.6))
        rr = r * em
        fr.disc((xs[i], y), rr, col, a * (0.14 + 0.3 * pulse(t, tc, 0.4)), 'L')
        fr.circle((xs[i], y), rr * (0.8 + 0.2 * cl(k)), col, a, 3 + (1 if cur else 0))
        if cur:
            fr.glow((xs[i], y), rr * 1.2, col, a0 * 0.5)
        fr.text(f'{i + 1}', xs[i], y - 2, int((44 if i < 7 else 54) * em), 'orb', lerpc(col, WHITE, 0.4), a, mode='E', glow=0.4)
        fr.text(nm, xs[i], y + 110 + (rr - r), int((32 if i < 7 else 40) * (1.12 if cur else 1.0)), 'sans_black', lerpc(col, WHITE, 0.5), a)
        fr.text(q, xs[i], y + 158 + (rr - r), 22, 'sans_med', lerpc(col, WHITE, 0.25), a * 0.9)
        shockwave(fr, (xs[i], y), tc, col, t, 500, 0.5, 2, a)
    if t >= S.c('p8'):
        fr.text('最后，才是估值', xs[7] - 40, y - 140, 34, 'serif_black', GOLD, a0 * S.a('p8', 0.5, off=0.3), glow=0.3)


# ================================================================ 五个测试
TESTS = [('t1', '提价测试', 'tag', '提价之前，要不要先开个祈祷会？', '定价权，是评估企业最重要的因素', GOLD),
         ('t2', '资本测试', 'coins', '给对手再多的钱，能夺走它的地位吗？', '可口可乐：再多的钱也做不到', CYAN),
         ('t3', '织布机测试', 'gear', '效率提升的好处，归股东还是归客户？', '芒格 · 1994 年南加州大学演讲', ORANGE),
         ('t4', '傻瓜测试', 'person', '换一个平庸的管理层，五年后它还在吗？', '好到傻瓜都能经营的生意', TEAL),
         ('t5', '停投测试', 'pause', '停止投入，份额和回报衰减得多快？', '衡量投入的强制性', VIOLET)]


@reg('tests')
def tests(fr, S):
    t = fr.t
    a0 = S.fade_out(0.4)
    ha = ramp(t, S.start, 0.5) * (1 - S.a('t1', 0.4, off=-0.3))
    if ha > 0:
        headline(fr, '五个随手可用的测试', W / 2, 520, 84, CYAN, ha * a0)
    cur = -1
    for i, x in enumerate(TESTS):
        if t >= S.c(x[0]) - 0.3: cur = i
    # 顶部已完成的测试
    for i in range(5):
        cue, nm, icon, q, src, col = TESTS[i]
        if i < cur:
            k = ramp(t, S.c(TESTS[i + 1][0]) - 0.3, 0.5, eo)
            cx = 400 + i * 280
            label_pill(fr, nm, cx, 230 + (1 - k) * 60, col, a0 * k, 30, 'sans_bold', 22)
    if cur < 0: return
    cue, nm, icon, q, src, col = TESTS[cur]
    tc = S.c(cue)
    k = ramp(t, tc - 0.3, 0.45, eo)
    a = a0 * k
    dx = (1 - k) * 500
    x0, y0, x1, y1 = 300 + dx, 340, 1620 + dx, 800
    fr.panel(x0, y0, x1, y1, col, a, 22, fill=0.08 + 0.1 * pulse(t, tc, 0.4), th=3)
    draw_icon(fr, icon, x0 + 220, (y0 + y1) / 2, 200, col, a, 5, t * 1.5)
    fr.glow((x0 + 220, (y0 + y1) / 2), 140, col, a * (0.25 + 0.5 * pulse(t, tc, 0.4)))
    fr.text(f'TEST 0{cur + 1}', x0 + 420, y0 + 80, 28, 'orb', col, a, anchor='l', mode='E', glow=0.3)
    headline(fr, nm, x0 + 420, y0 + 165, 84, col, a, anchor='l')
    fr.text(q, x0 + 420, y0 + 290, 42, 'sans_black', WHITE, a, anchor='l')
    fr.text(src, x0 + 420, y0 + 370, 26, 'sans_light', lerpc(col, WHITE, 0.3), a, anchor='l')


# ================================================================ 五条规则
RULES = [('利润不会超过附加值', LAYER_COL['L1']), ('只为结构性回报付长期的价', GOLD2), ('看维持的代价，看再投资是否被迫', TEAL),
         ('杠杆只放大，不创造', LAYER_COL['L4']), ('生存，一票否决', RED)]


@reg('rules')
def rules(fr, S):
    t = fr.t
    a0 = S.fade_out(0.4)
    bz = S.a('biz', 0.6)
    ra = a0 * (1 - bz)
    if ra > 0.01:
        headline(fr, '记住五条规则', W / 2, 220, 64, GOLD, ra * ramp(t, S.start + 1.3, 0.5))
        for i, (s, col) in enumerate(RULES):
            tc = S.c(f'r{i + 1}')
            k = ramp(t, tc, 0.45, eback)
            if k <= 0: continue
            y = 350 + i * 112
            a = ra * cl(k)
            x = 540 - (1 - cl(k)) * 80
            fr.text(f'{i + 1}', x, y, 70, 'orb', col, a, mode='E', glow=0.5)
            fr.line((x + 60, y), (x + 60 + 40 * cl(k), y), col, a * 0.6, 2)
            fr.text(s, x + 130, y, 50, 'sans_black', lerpc(col, WHITE, 0.55), a, anchor='l', glow=0.12)
            fr.glow((x, y), 60, col, a * pulse(t, tc, 0.4))
    if bz > 0:
        a = bz * a0
        headline(fr, '框架评价的是生意，不是股票', W / 2, 260, 64, GOLD, a)
        bk = S.a('biz2', 0.8, eio)
        cx, cy = W / 2, 600
        tilt = 0.12 * bk
        fr.line((cx, cy - 140), (cx, cy + 180), GREY, a * 0.8, 3)
        fr.fillpoly([(cx - 60, cy + 190), (cx + 60, cy + 190), (cx, cy + 150)], GREY, a * 0.5)
        L = 380
        p1 = (cx - L * math.cos(tilt), cy - 140 + L * math.sin(tilt))
        p2 = (cx + L * math.cos(tilt), cy - 140 - L * math.sin(tilt))
        fr.line(p1, p2, GOLD2, a, 4)
        for p, nm, col, h in ((p1, '每股内在价值', GOLD, 1.0), (p2, '价格', CYAN, 0.6)):
            fr.line(p, (p[0] - 90, p[1] + 150), GREY, a * 0.6, 2)
            fr.line(p, (p[0] + 90, p[1] + 150), GREY, a * 0.6, 2)
            fr.arc((p[0], p[1] + 150), 110, 0, math.pi, col, a, 3)
            fr.text(nm, p[0], p[1] + 305, 36, 'sans_black', col, a)
        if bk > 0.5:
            k = cl(bk * 2 - 1)
            fr.text('安全边际', cx, cy - 210, 40, 'serif_black', GOLD, a * k, glow=0.3)
            fr.arrow((p2[0] - 60, p2[1] + 120), (p2[0] - 60, p1[1] + 120), GOLD2, a * k, 3, 14)


# ================================================================ 结语
QLINES = ['伟大的企业，能以合理的代价，', '守住一块别人拿不走的价值，', '并在机会出现时，', '把资本转化为更高的每股价值；', '而且这一切，是你能够理解和判断的。']
RISE = RNG.uniform(0, 1, (700, 3))


@reg('quote')
def quote(fr, S):
    t = fr.t
    a0 = S.fade_out(0.6)
    # 金色上升粒子
    ph = (t * 0.05 * (0.5 + RISE[:, 2]) + RISE[:, 1]) % 1.0
    x = RISE[:, 0] * W + np.sin(t * 0.5 + RISE[:, 1] * 9) * 20
    y = H * (1.05 - ph * 1.1)
    fr.dots(x, y, GOLD, a0 * np.sin(ph * np.pi) * 0.55 * cl(S.lt / 1.5), 1)
    light_rays(fr, (W / 2, -200), 14, 1500, GOLD, a0 * 0.05, t, 0.03)
    # 逐字随旁白显现
    full = ''.join(u['text'] for u in S.sc['utts'])
    ct = sum((u['ct'][:len(u['text'])] for u in S.sc['utts']), [])
    pos = 0
    lines_t = []
    for ln in QLINES:
        i = full.find(ln.rstrip('，；。'), pos)
        if i < 0: i = pos
        lines_t.append((ln, [ct[min(i + j, len(ct) - 1)] for j in range(len(ln))]))
        pos = i + len(ln) - 1
    for li, (ln, ts) in enumerate(lines_t):
        y = 290 + li * 110
        chars = [eo((t - tt + 0.08) / 0.35) for tt in ts]
        col = GOLD if li in (1, 3) else WHITE
        if li == 4: col = GOLD2
        grad = [lerpc(col, WHITE, 0.5), col, lerpc(col, (0.6, 0.35, 0.1), 0.3)] if col != WHITE else None
        fr.text(ln, W / 2, y, 60, 'serif_black', col, a0, chars_alpha=chars, glow=0.35 if col != WHITE else 0.12, grad=grad, track=0.04)
    fr.zoom *= 1 + 0.03 * eio(S.lt / S.dur)


# ================================================================ 片尾
_LOGO = None


def logo_rgba():
    global _LOGO
    if _LOGO is None:
        rgb, al = load_logo(240)
        _LOGO = (rgb.astype(np.float32), al.astype(np.float32))
    return _LOGO


@reg('outro')
def outro(fr, S):
    t = fr.t
    lt = S.lt
    rgb, al = logo_rgba()
    k = eback(cl((lt - 0.1) / 0.8))
    a = cl((lt - 0.1) / 0.5) * (1 - eio((lt - 8.6) / 1.4))
    cx, cy = W / 2, 400
    if a > 0:
        s = 0.7 + 0.3 * k
        sz = int(240 * s)
        if sz > 8:
            r2 = cv2.resize(rgb, (sz, sz), interpolation=cv2.INTER_AREA)
            a2 = cv2.resize(al, (sz, sz), interpolation=cv2.INTER_AREA) * a * fr.k
            x0, y0 = int(cx - sz / 2), int(cy - sz / 2)
            fr.glow((cx, cy), 120, C(110, 175, 255), a * 0.35)
            fr.over.append((a2, x0, y0, r2, 1.0))
        shockwave(fr, (cx, cy), S.start + 0.1, C(110, 175, 255), t, 1200, 1.2, 3, 0.8)
    ta = cl((lt - 0.7) / 0.6) * (1 - eio((lt - 8.6) / 1.4))
    if ta > 0:
        headline(fr, '巴芒价值', cx, 640, 120, GOLD, ta, glow=0.4, track=0.08)
        tw = text_width('巴芒价值', 'serif_black', 120, 0.08)
        sub = 'BUFFETT · MUNGER'
        fr.text(sub, cx, 738, 30, 'corm', C(214, 178, 112), ta, track=(tw - text_width(sub, 'corm', 30)) / 30 / (len(sub) - 1))
        # 流光
        sw = cl((lt - 1.6) / 1.4)
        if 0 < sw < 1:
            xx = cx - tw / 2 - 80 + sw * (tw + 160)
            for wd, al_ in ((60, 0.03), (30, 0.04), (12, 0.05)):
                fr.fillpoly([(xx - wd, 575), (xx + wd, 575), (xx + wd - 40, 705), (xx - wd - 40, 705)], GOLD2, al_ * ta * math.sin(sw * math.pi), 'E')
        fr.text('企业盈利能力评估框架', cx, 830, 30, 'serif_med', GOLD2, ta * cl((lt - 1.4) / 0.6) * 0.85, track=0.3)
        fr.text('本片为方法示范，案例仅用于说明框架，不构成任何投资建议', cx, 960, 22, 'sans_light', GREY,
                ta * cl((lt - 2.0) / 0.6) * 0.8)
