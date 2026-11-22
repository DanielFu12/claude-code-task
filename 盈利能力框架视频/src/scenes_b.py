"""场景 B：L0 生存、L1 价值杆 / 织布机 / 谁拿走价值 / 护城河 / 周期陷阱。"""
from common import *

RNG = np.random.default_rng(77)
DRAW = {}


def reg(name):
    def d(f):
        DRAW[name] = f
        return f
    return d


# ================================================================ L0 生存
DEATH = [('周期 × 杠杆', '顶部扩产，底部断流', 'd1'), ('强制投入 × 杠杆', '投入停不下，利息也停不下', 'd2'),
         ('外部融资续命', '经营现金流长期为负', 'd3'), ('技术绕道', '赖以生存的桥被绕过', 'd4'),
         ('透支引擎', '为短期利润砍维持投入', 'd5'), ('客户集中', '依赖单一客户或政策', 'd6'),
         ('增长毁灭价值', '越增长，越亏钱', 'd7')]
SHARD = RNG.uniform(-1, 1, (600, 4))


@reg('L0')
def L0(fr, S):
    t = fr.t
    a0 = S.fade_out(0.4)
    # 芒格名言
    qa = S.a('m', 0.6) * (1 - S.a('d1', 0.5))
    if qa > 0:
        fr.text('“', 470, 360, 160, 'serif_black', RED, qa * 0.5, mode='E', glow=0.3)
        typeline(fr, '我只想知道我会死在哪里，', W / 2, 450, 64, WHITE, qa, S.c('m'), 9, 'serif_black', glow=0.25)
        typeline(fr, '这样我就永远不去那儿。', W / 2, 550, 64, C(255, 120, 120), qa, S.c('m') + 1.3, 9, 'serif_black', glow=0.35)
        fr.text('—— 查理 · 芒格', W / 2 + 330, 650, 30, 'serif_med', GREY, qa * S.a('m', 0.5, off=2.5), anchor='r')
    # 死法①：周期 × 杠杆
    d1 = S.a('d1', 0.6) * (1 - S.a('d2', 0.5))
    if d1 > 0:
        a = d1 * a0
        label_pill(fr, '死法 ①   周期 × 杠杆', W / 2, 250, RED, a, 34, 'sans_bold', 26)
        x0, x1, y0 = 300, 1620, 600
        fr.line((x0, y0), (x1, y0), GREY, a * 0.4, 1)
        fr.text('0', x0 - 16, y0, 22, 'mono', GREY, a * 0.6, anchor='r')
        prog = S.a('d1', 4.5, lambda x: cl(x))
        xs = np.linspace(x0, x1, 240)
        u = (xs - x0) / (x1 - x0)
        cyc = y0 - 170 * np.sin(u * 2 * np.pi * 1.25 + 0.3)
        draw_line_chart(fr, xs, cyc, GREY, a * 0.7, 2, prog, head=False)
        fr.text('行业景气', x0 + 10, 380, 24, 'sans_med', GREY, a * 0.8, anchor='l')
        # 杠杆 = 顶部借钱扩产，现金流在底部跌穿 0
        lev = 1 + 2.2 * np.clip((u - 0.14) / 0.1, 0, 1)
        cash = y0 - (y0 - cyc) * lev * 0.55 - 30
        cash = np.where(u > 0.14, cash, y0 - (y0 - cyc) * 0.55 - 30)
        draw_line_chart(fr, xs, np.clip(cash, 250, 880), C(255, 110, 110), a, 4, prog)
        pk = 0.14
        if prog > pk:
            xp = x0 + pk * (x1 - x0)
            fr.circle((xp, cyc[int(pk * 239)]), 12, GOLD, a, 2)
            fr.text('景气顶部：借钱扩产', xp - 20, cyc[int(pk * 239)] - 70, 26, 'sans_bold', GOLD, a * cl((prog - pk) * 8), anchor='l')
        tb = 0.52
        if prog > tb:
            xb = x0 + tb * (x1 - x0)
            k = cl((prog - tb) * 6)
            fr.glow((xb, 820), 60, RED, a * k * (0.6 + 0.4 * math.sin(t * 9)))
            headline(fr, '现金流断裂', xb + 330, 800, 50, RED, a * k)
    # 七种死法网格
    g = S.a('d2', 0.6)
    bfk = S.a('bf', 0.6)
    vt = S.a('veto', 0.3)
    if g > 0:
        ga = g * a0 * (1 - 0.96 * bfk) * (1 - vt)
        last_t = -1
        for i, (nm, sub, cue) in enumerate(DEATH):
            tc = S.c(cue) if i == 0 else max(S.c(cue), S.c(DEATH[i - 1][2]) + 0.6 * (cue == 'd7'))
            if i == 0: tc = S.c('d2') - 0.3
            k = ramp(t, tc, 0.45, eback)
            if k <= 0: continue
            row, col_ = (0, i) if i < 4 else (1, i - 4)
            cx = 330 + col_ * 420 + (210 if row == 1 else 0)
            cy = 380 + row * 260
            a = cl(k) * ga
            x0_, y0_, x1_, y1_ = cx - 190, cy - 100, cx + 190, cy + 100
            fr.panel(x0_, y0_ + (1 - cl(k)) * 30, x1_, y1_ + (1 - cl(k)) * 30, RED, a, 14, fill=0.06 + 0.12 * pulse(t, tc, 0.4))
            draw_icon(fr, 'warn', x0_ + 52, cy - 22, 50, RED, a, 3)
            fr.text(f'0{i + 1}', x1_ - 20, y0_ + 30, 24, 'orb', C(255, 120, 120), a * 0.8, anchor='r')
            fr.text(nm, x0_ + 96, cy - 24, 36, 'sans_black', C(255, 205, 205), a, anchor='l')
            fr.text(sub, cx, cy + 50, 24, 'sans_med', C(230, 160, 165), a)
            fr.glow((cx, cy), 120, RED, pulse(t, tc, 0.35) * a * 0.5)
    # 巴菲特：最糟糕的生意
    if bfk > 0:
        a = bfk * a0 * (1 - vt)
        headline(fr, '最糟糕的生意', W / 2, 300, 68, C(255, 140, 140), a)
        for i, s in enumerate(['增长迅速', '需要大量资本', '几乎不赚钱']):
            k = ramp(t, S.c('bf') + 0.8 + i * 0.9, 0.4, eback)
            label_pill(fr, s, W / 2 - 420 + i * 420, 440, RED, a * cl(k), 40, 'sans_bold', 30)
        ap = S.a('air', 1.6, eio)
        if ap > 0:
            px = lerp(380, 1500, ap)
            py = 640 + ap * ap * 180
            draw_icon(fr, 'plane', px, py, 150, ICE, a, 3)
            fr.poly([(380 + k * (px - 380) / 20, 640 + (k / 20 * ap) ** 2 * 180 + 30) for k in range(21)], RED, a * 0.6, 3)
            fr.text('航空公司', px, py + 90, 34, 'sans_black', ICE, a * cl(ap * 3))
    # 一票否决
    if vt > 0:
        lt = t - S.c('veto')
        a = a0
        cx, cy = W / 2, 560
        shatter = eo((lt - 0.55) / 1.0)
        for i in range(10):
            x = cx - 540 + i * 120
            hgt = 120 + 40 * math.sin(i * 1.3)
            if shatter < 1:
                fr.rrect_fill(x - 40, cy + 120 - hgt, x + 40, cy + 120, 6, GOLD, a * 0.5 * (1 - shatter) * cl(lt * 5), 'E')
        fr.text('Σ  未来经济利润', cx, cy + 175, 34, 'sans_bold', GOLD2, a * cl(lt * 4) * (1 - shatter * 0.7))
        if shatter > 0:
            sx = cx - 540 + (SHARD[:, 0] * 0.5 + 0.5) * 1080
            sy = cy + 60 + SHARD[:, 1] * 60 + shatter ** 1.5 * (300 + 200 * SHARD[:, 2])
            fr.dots(sx + SHARD[:, 3] * 80 * shatter, sy, GOLD, a * (1 - shatter), 1)
        st = eo((lt - 0.05) / 0.25)
        sc_ = lerp(2.4, 1.0, st)
        if st > 0:
            fr.text('× 0', cx + 300, cy - 30, int(170 * sc_), 'orb', RED, a * st, mode='E', glow=0.6)
            fr.line((cx - 600, cy + 200), (cx + 600, cy - 60), RED, a * st, 8)
            headline(fr, '一票否决', cx - 230, cy - 60, int(120 * sc_), RED, a * st)
            fr.shake = (8 * pulse(t, S.c('veto'), 0.12) * math.sin(t * 90), 6 * pulse(t, S.c('veto'), 0.12) * math.cos(t * 80))
            fr.ca = max(fr.ca, 8 * pulse(t, S.c('veto'), 0.2))


# ================================================================ L1 价值杆
SX, SW = 640, 130
LV = {'wtp': 230, 'p': 400, 'c': 640, 'wts': 830}


@reg('stick')
def stick(fr, S):
    t = fr.t
    a0 = S.fade_out(0.45)
    sa = S.at(min(S.c('stick'), S.start + 1.8), 0.6)
    ghost = S.a('av2', 0.5)
    if sa <= 0: return
    flick = 1 - ghost * (0.65 + 0.25 * math.sin(t * 23) * math.sin(t * 7))
    a = sa * a0 * flick
    fr.rrect(SX - SW / 2, LV['wtp'], SX + SW / 2, LV['wts'], 10, WHITE, a * 0.35, 2)
    # 分段填充
    segs = [('cs', 'wtp', 'p', CYAN, '客户剩余', '= 客户最高愿付价 − 价格'),
            ('fp', 'p', 'c', GOLD, '企业利润', '= 价格 − 成本'),
            ('ss', 'c', 'wts', VIOLET, '供应商与员工剩余', '= 成本 − 最低接受价')]
    for cue, top, bot, col, nm, sub in segs:
        k = S.a(cue, 0.6, eo)
        if k <= 0: continue
        y0, y1 = LV[top], LV[bot]
        yy = y1 - (y1 - y0) * k
        boost = 0.25 * pulse(t, S.c(cue), 0.5) + (0.12 * kick_pulse(t) if cue == 'fp' else 0)
        fr.rect(SX - SW / 2 + 4, yy, SX + SW / 2 - 4, y1, col, a * (0.32 + boost), 'E')
        bx = SX + SW / 2 + 40
        fr.poly([(bx, y0 + 6), (bx + 14, y0 + 6), (bx + 14, y1 - 6), (bx, y1 - 6)], col, a * k, 2)
        my = (y0 + y1) / 2
        fr.line((bx + 14, my), (bx + 40, my), col, a * k, 2)
        fr.text(nm, bx + 56, my - 18, 40 if cue == 'fp' else 34, 'sans_black', lerpc(col, WHITE, 0.4), a * k, anchor='l',
                glow=0.25 if cue == 'fp' else 0)
        fr.text(sub, bx + 56, my + 26, 24, 'sans_light', lerpc(col, WHITE, 0.3), a * k, anchor='l')
    # 刻度线与名称
    names = [('wtp', '客户最高愿付价', 'WTP'), ('p', '价格', 'PRICE'), ('c', '成本', 'COST'), ('wts', '供应商与员工最低接受价', 'WTS')]
    for cue, zh, en in names:
        k = S.a(cue, 0.4, eo)
        if k <= 0: continue
        y = LV[cue]
        w = (SW / 2 + 30) * k
        fr.line((SX - w, y), (SX + w, y), WHITE, a, 3)
        fr.glow((SX, y), 20, WHITE, a * pulse(t, S.c(cue), 0.3))
        fr.text(zh, SX - SW / 2 - 40, y - 12, 30, 'sans_bold', WHITE, a * k, anchor='r')
        fr.text(en, SX - SW / 2 - 40, y + 22, 20, 'orb', GREY, a * k, anchor='r')
    # 价值创造括号
    vc = S.a('fp', 0.6, off=0.8)
    if vc > 0:
        bx = 170
        fr.poly([(bx + 14, LV['wtp']), (bx, LV['wtp']), (bx, LV['wts']), (bx + 14, LV['wts'])], GOLD2, a * vc * 0.5, 2)
        fr.text('价值创造', bx - 10, 520, 26, 'sans_bold', GOLD2, a * vc * 0.8, anchor='r')
        fr.text('WTP − WTS', bx - 10, 556, 18, 'orb', GOLD2, a * vc * 0.6, anchor='r')
    # 附加值卡片
    av = S.a('av', 0.6, eback)
    if av > 0:
        aa = cl(av) * a0
        x0, y0, x1, y1 = 1180, 300, 1760, 760
        fr.panel(x0, y0, x1, y1, GOLD, aa, 18, fill=0.08)
        headline(fr, '附加值', (x0 + x1) / 2, y0 + 70, 64, GOLD, aa)
        fr.text('有它时体系创造的价值', (x0 + x1) / 2, y0 + 170, 30, 'sans_med', WHITE, aa)
        fr.text('−', (x0 + x1) / 2, y0 + 220, 40, 'sans_light', GOLD2, aa)
        fr.text('没有它时体系创造的价值', (x0 + x1) / 2, y0 + 270, 30, 'sans_med', WHITE, aa)
        fr.line((x0 + 60, y0 + 320), (x1 - 60, y0 + 320), GOLD, aa * 0.6, 2)
        fr.text('= 长期利润的上限', (x0 + x1) / 2, y0 + 380, 38, 'sans_black', GOLD, aa, glow=0.3)
        if ghost > 0:
            fr.text('假如它消失……', SX, 945 - 60, 30, 'serif_med', C(255, 140, 140), ghost * a0)


# ================================================================ 织布机
FX = [360 + i * 300 for i in range(5)]
CUSTP = RNG.uniform(0, 1, (240, 3))


@reg('loom')
def loom(fr, S):
    t = fr.t
    a0 = S.fade_out(0.45)
    pv = S.a('pv', 0.6)
    la = a0 * (1 - pv)
    if la > 0.01:
        fr.text('芒格的织布机', W / 2, 200, 44, 'serif_black', GOLD, la * ramp(t, S.start, 0.5), glow=0.2)
        for i, x in enumerate(FX):
            draw_icon(fr, 'factory', x, 420, 110, GREY, la, 3)
            tg = S.c('loom') if i == 0 else S.c('loom2') + (i - 1) * 0.12
            k = ramp(t, tg, 0.4, eback)
            if k > 0:
                draw_icon(fr, 'gear', x, 300, 64 * cl(k), GOLD, la * cl(k), 3, t * 2.5)
                fr.glow((x, 300), 40, GOLD, la * pulse(t, tg, 0.4))
        if S.a('loom', 0.5) > 0:
            fr.text('效率 ↑  行业创造的价值 ↑', W / 2, 560, 32, 'sans_bold', GOLD2, la * S.a('loom', 0.5))
        if S.a('loom2', 0.5) > 0:
            fr.text('每家工厂都买得到', W / 2, 240 + 0, 1, 'sans_bold', WHITE, 0)
            label_pill(fr, '人人都买得到 → 单个工厂的附加值 ≈ 0', W / 2, 620, RED, la * S.a('loom2', 0.5, off=0.5), 30, 'sans_bold', 22)
        dn = S.a('down', 0.8, eio)
        if dn > 0:
            # 价格下降、价值流向客户
            py = lerp(680, 760, dn)
            fr.line((260, py), (1660, py), CYAN, la * 0.8, 2)
            fr.text(f'价格 ↓', 1680, py, 28, 'sans_bold', CYAN, la, anchor='l')
            for k in range(6):
                draw_icon(fr, 'person', 460 + k * 200, 860, 60, CYAN, la * dn, 2)
            ph = (t * 0.6 + CUSTP[:, 0]) % 1.0
            sx = np.array(FX)[(CUSTP[:, 1] * 5).astype(int)]
            ex = 460 + (CUSTP[:, 2] * 6).astype(int) * 200
            x = sx + (ex - sx) * ph
            y = 470 + (850 - 470) * ph
            fr.dots(x, y, GOLD, la * dn * np.sin(ph * np.pi) * 0.9, 1)
            fr.text('好处最终流向了客户', W / 2, 940 - 15, 1, 'sans_bold', WHITE, 0)
    if pv <= 0: return
    cards = [('pv', '光伏制造', RED, '高度可替代', '价值让给下游', 0.12),
             ('nv', '英伟达', GOLD, 'GPU + CUDA 生态', '难以替代，拿走大头', 0.62),
             ('ap', '苹果 vs 代工', GOLD, '品牌与生态不可替换', '利润留在苹果', 0.70)]
    for i, (cue, nm, col, l1, l2, share) in enumerate(cards):
        k = S.a(cue, 0.55, eback)
        if k <= 0: continue
        a = cl(k) * a0
        cx = 400 + i * 560
        cy = 560 + (1 - cl(k)) * 50
        fr.panel(cx - 240, cy - 290, cx + 240, cy + 290, col, a, 18, fill=0.06 + 0.1 * pulse(t, S.c(cue), 0.4))
        headline(fr, nm, cx, cy - 220, 54, col, a)
        # 附加值圆环：拿走的份额
        r = 110
        fr.circle((cx, cy - 20), r, GREY, a * 0.25, 16)
        sh = share * eo((t - S.c(cue) - 0.2) / 0.9)
        fr.arc((cx, cy - 20), r, -math.pi / 2, -math.pi / 2 + sh * 2 * math.pi, col, a, 16)
        fr.text(f'{int(sh * 100)}%', cx, cy - 30, 54, 'orb', lerpc(col, WHITE, 0.4), a, mode='E', glow=0.3)
        fr.text('拿走的价值', cx, cy + 22, 22, 'sans_light', GREY, a)
        fr.text(l1, cx, cy + 160, 32, 'sans_bold', WHITE, a)
        fr.text(l2, cx, cy + 215, 30, 'sans_black', lerpc(col, WHITE, 0.3), a, glow=0.15)
    fr.text('示意，非实际份额', W / 2, 905, 20, 'sans_light', GREY, a0 * pv * 0.6)


# ================================================================ 谁拿走价值
WHO = ['客户', '竞争者', '供应商', '员工', '政府', '债权人']
WHO_SUB = ['产品可替代', '壁垒低', '关键投入被垄断', '人才附加值更大', '暴利税 · 集采', '高杠杆付利息']
WP = RNG.uniform(0, 1, (900, 2))


@reg('who')
def who(fr, S):
    t = fr.t
    a0 = S.fade_out(0.45)
    cx, cy = W / 2, 575
    headline(fr, '价值还会被谁拿走？', W / 2, 170, 52, GOLD, a0 * S.a('who', 0.5))
    n_on = sum(1 for i in range(6) if t >= S.c(f'w{i + 1}'))
    r0 = 95 * (1 - 0.09 * n_on) + 6 * kick_pulse(t)
    fr.disc((cx, cy), r0, GOLD, a0 * 0.16, 'L')
    fr.circle((cx, cy), r0, GOLD2, a0, 3)
    fr.glow((cx, cy), r0 * 1.1, GOLD, a0 * 0.3)
    fr.text('企业的价值', cx, cy, 30, 'sans_black', GOLD2, a0)
    for i, nm in enumerate(WHO):
        tc = S.c(f'w{i + 1}')
        k = ramp(t, tc, 0.45, eback)
        if k <= 0: continue
        ang = -math.pi / 2 + i * math.pi / 3
        nx, ny = cx + math.cos(ang) * 480, cy + math.sin(ang) * 285
        col = [CYAN, RED, ORANGE, TEAL, VIOLET, BLUE][i]
        a = cl(k) * a0
        fr.circle((nx, ny), 62, col, a, 3)
        fr.disc((nx, ny), 62, col, a * 0.12, 'L')
        fr.text(nm, nx, ny - 6, 34, 'sans_black', lerpc(col, WHITE, 0.5), a)
        fr.text(WHO_SUB[i], nx, ny + 92, 22, 'sans_med', lerpc(col, WHITE, 0.3), a * 0.9)
        # 吸走价值的粒子流
        sel = WP[i * 150:(i + 1) * 150]
        ph = (t * 0.9 + sel[:, 0]) % 1.0
        x = lerp(cx, nx, ph) + np.sin(ph * 9 + sel[:, 1] * 6) * 10
        y = lerp(cy, ny, ph) + np.cos(ph * 7 + sel[:, 1] * 6) * 10
        fr.dots(x, y, GOLD, a * np.sin(ph * np.pi) * 0.8, 1)
        fr.glow((nx, ny), 60, col, pulse(t, tc, 0.35) * a)


# ================================================================ 护城河
MOATS = [('品牌', '可口可乐 · 茅台 · See\'s'), ('转换成本', '企业软件 · 医疗器械'), ('网络效应', 'Visa · 交易所 · 微信'),
         ('有效规模', '评级机构 · 铁路 · 机场'), ('规模经济', 'Costco · GEICO'), ('反定位', 'GEICO 直销 · 指数基金'),
         ('流程文化', '丰田 · 丹纳赫'), ('稀缺资源', '低成本矿藏 · 牌照'), ('技术领先', '光刻机 · 领先 GPU'), ('轻资产', '特许经营 · 会员制')]


@reg('moat')
def moat(fr, S):
    t = fr.t
    a0 = S.fade_out(0.45)
    gk = S.a('g', 0.5)
    rk = S.a('rule', 0.6)
    # 经济特许权 + 提价测试
    fa = a0 * (1 - gk)
    if fa > 0.01:
        headline(fr, '经济特许权', 560, 260, 64, GOLD, fa * S.at(min(S.c('fr'), S.start + 1.2), 0.5))
        fr.text('巴菲特 · 1991 年致股东信', 560, 330, 24, 'sans_light', GREY, fa * S.a('fr', 0.5))
        for i, s in enumerate(['被需要或渴望', '没有相近的替代品', '不受价格管制']):
            k = S.a(f'fr{i + 1}', 0.45, eback)
            if k <= 0: continue
            y = 450 + i * 120
            fr.panel(300, y - 44, 840, y + 44, GOLD, fa * cl(k), 12, fill=0.06)
            draw_icon(fr, 'check', 350, y, 40, TEAL, fa * cl(k), 4)
            fr.text(s, 400, y, 36, 'sans_bold', WHITE, fa * cl(k), anchor='l')
            fr.glow((350, y), 30, TEAL, fa * pulse(t, S.c(f'fr{i + 1}'), 0.35))
        pk = S.a('px', 0.5, eback)
        if pk > 0:
            a = cl(pk) * fa
            draw_icon(fr, 'tag', 1340, 430, 220, GOLD, a, 4)
            fr.glow((1340, 430), 120, GOLD, a * 0.3)
            pr = 100 * (1 + 0.15 * eo((t - S.c('px') - 0.3) / 1.5))
            fr.text(f'¥ {pr:.0f}', 1340, 640, 84, 'sans_black', GOLD2, a, mode='E', glow=0.35)
            headline(fr, '能否经常大胆提价', 1340, 760, 44, GOLD, a)
    # 护城河网格
    if gk > 0:
        a = gk * a0 * (1 - 0.96 * rk)
        fr.text('护城河的十种来源', W / 2, 205, 34, 'serif_med', GOLD2, a, glow=0.15)
        for i, (nm, ex) in enumerate(MOATS):
            try:
                tc = S.w(nm)
            except KeyError:
                tc = S.c('g') + i * 0.8
            k = ramp(t, tc, 0.4, eback)
            if k <= 0: continue
            row, colm = divmod(i, 5)
            cx = 260 + colm * 350
            cy = 400 + row * 270
            col = [GOLD, CYAN, VIOLET, BLUE, TEAL, MAGENTA, ORANGE, GREEN, ICE, GOLD2][i]
            ka = cl(k) * a
            sb = 1 + 0.07 * pulse(t, tc, 0.45)
            fr.panel(cx - 160 * sb, cy - 110 * sb, cx + 160 * sb, cy + 110 * sb, col, ka, 16, fill=0.05 + 0.18 * pulse(t, tc, 0.5), th=2 + int(2 * pulse(t, tc, 0.5)))
            fr.text(f'{i + 1:02d}', cx - 132, cy - 80, 22, 'orb', col, ka * 0.8, anchor='l')
            pk = pulse(t, tc, 0.45)
            fr.text(nm, cx, cy - 10, int(44 * (1 + 0.28 * pk)), 'sans_black', lerpc(col, WHITE, 0.55 + 0.3 * pk), ka, glow=0.15 + 0.5 * pk)
            fr.text(ex, cx, cy + 58, 22, 'sans_med', lerpc(col, WHITE, 0.25), ka * 0.9)
            fr.glow((cx, cy), 120, col, pulse(t, tc, 0.4) * ka * 0.6)
    if rk > 0:
        a = rk * a0
        for i, (cue, ttl, sub, col) in enumerate([('rule1', '利益', '作用在价值杆的哪一端？', GOLD),
                                                  ('rule2', '壁垒', '竞争者为什么无法复制？', CYAN)]):
            k = S.a(cue, 0.5, eback)
            if k <= 0: continue
            cx = W / 2 + (i * 2 - 1) * 400
            ka = cl(k) * a
            fr.panel(cx - 340, 360, cx + 340, 760, col, ka, 20, fill=0.10, dark=0.75)
            headline(fr, ttl, cx, 450, 80, col, ka)
            fr.text(sub, cx, 560, 36, 'sans_bold', WHITE, ka)
            if i == 0:
                fr.rrect(cx - 30, 610, cx + 30, 730, 6, GOLD, ka * 0.7, 2)
                fr.arrow((cx + 100, 700), (cx + 100, 620), TEAL, ka, 3, 14)
                fr.text('抬高 WTP', cx + 120, 640, 22, 'sans_med', TEAL, ka, anchor='l')
                fr.arrow((cx - 100, 620), (cx - 100, 700), CYAN, ka, 3, 14)
                fr.text('压低成本', cx - 120, 690, 22, 'sans_med', CYAN, ka, anchor='r')
            else:
                for r in range(3):
                    for c in range(5):
                        x = cx - 150 + c * 60 + (30 if r % 2 else 0)
                        fr.rrect(x, 620 + r * 36, x + 56, 652 + r * 36, 3, CYAN, ka * 0.7, 2)
        fr.text('每一种机制，都要说清两件事', W / 2, 250, 36, 'serif_med', GOLD2, a, glow=0.15)


# ================================================================ 周期陷阱
@reg('cycle')
def cycle(fr, S):
    t = fr.t
    a0 = S.fade_out(0.45)
    ta = S.a('trap', 0.5)
    ek = S.a('eq', 0.6)
    mk = S.a('mid', 0.6)
    top = 1 - ek
    if ta > 0:
        tsz = int(lerp(76, 44, ek))
        draw_icon(fr, 'warn', W / 2 + 40 - text_width('把周期当成护城河', 'serif_black', tsz) / 2 - tsz * 0.8, lerp(480, 190, ek), tsz * 0.9, ORANGE, ta * a0, 4)
        headline(fr, '把周期当成护城河', W / 2 + 40, lerp(480, 190, ek), int(lerp(76, 44, ek)), ORANGE, ta * a0)
    if ek <= 0: return
    a = ek * a0
    # 公式
    fr.text('ROIC(t)  =  结构性 ROIC  +  周期偏离(t)', W / 2, 290, 40, 'sans_black', WHITE, a, glow=0.1)
    # 图表区
    x0, x1 = 300, 1620
    xs = np.linspace(x0, x1, 300)
    u = (xs - x0) / (x1 - x0)
    pr = S.a('eq', 2.0, lambda x: cl(x))
    def chart(base_y, struct, amp, col, label, alpha, split):
        wacc = base_y + 40
        fr.line((x0, wacc), (x1, wacc), C(255, 120, 120), alpha * 0.6, 2)
        fr.text('WACC', x1 + 10, wacc, 20, 'orb', C(255, 140, 140), alpha * 0.8, anchor='l')
        roic = base_y - struct - amp * np.sin(u * 2 * np.pi * 1.6)
        draw_line_chart(fr, xs, roic, col, alpha * (1 - 0.5 * split), 3, pr, head=pr < 1)
        if split > 0:
            sy = base_y - struct
            fr.line((x0, sy), (x0 + (x1 - x0) * split, sy), GOLD, alpha, 4)
            fr.text('结构性', x0 - 10, sy, 24, 'sans_bold', GOLD, alpha * split, anchor='r')
            dev = base_y + 200 - amp * 0.6 * np.sin(u * 2 * np.pi * 1.6)
            draw_line_chart(fr, xs, dev, CYAN, alpha * split * 0.8, 2, split, head=False)
            fr.text('周期偏离', x0 - 10, base_y + 200, 24, 'sans_bold', CYAN, alpha * split, anchor='r')
        fr.text(label, x1, 340, 30, 'sans_bold', col, alpha, anchor='r')
    av = S.a('avg', 1.0, eio)
    if mk < 1:
        chart(620, 120, 90, TEAL, '有优势、强周期：结构性部分高', a * (1 - mk), av)
        if av > 0:
            fr.text('至少一个完整周期（7–10 年）的平均值', W / 2, 900, 28, 'sans_med', GOLD2, a * av * (1 - mk))
    if mk > 0:
        chart(640, -20, 150, RED, '无优势、强周期：成本居中的商品生产者', a * mk, 0)
        pk_x = x0 + (0.25 / 1.6 % 1) * (x1 - x0) / 1
        pkx = x0 + (1 / 6.4) * (x1 - x0)
        fr.circle((pkx, 640 + 20 - 150), 16, RED, a * mk, 3)
        fr.text('景气高点 ROE', pkx + 34, 640 + 20 - 150 - 8, 28, 'sans_black', C(255, 170, 170), a * mk, anchor='l')
        headline(fr, '高点不能按长期去资本化', W / 2, 900, 46, RED, a * S.a('mid', 0.6, off=1.2))
