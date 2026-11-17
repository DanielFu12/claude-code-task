"""第七期全部镜头（开场、片名、第一至七章）。通用构件见 gg_base.py；时间全部挂在旁白句子与词锚点上（WT 用朗读文本）。"""
from gg_base import *          # noqa
from gg_base import _SAY        # noqa

AX_BLUE = C(70, 140, 220)       # 通用“卡蓝”（不是任何商标色的复刻，只作区分）
BANK_G = C(150, 160, 175)       # 银行的灰
WATER = C(60, 120, 190)
OIL = C(214, 170, 60)


def A(t, t0, t1, fi=0.4, fo=0.4): return env(t, t0, t1, fi, fo)


def win2(i, j=None, pre=0.3, post=0.2):
    """从 i 句开口前 pre 秒，到 j（或 i）句之后的下一句开口前 post 秒"""
    j = j or i
    nx = nxt(j)
    end = (S(nx) - post) if nx and SEG[nx].get('kind') != 'sot' else E(j) + 0.6
    return S(i) - pre, end


def appear(t, i, sub, d=0.45, lead=0.1):
    """词锚点 sub 开口前 lead 秒开始，用 d 秒缓入"""
    return eo((t - WT(i, sub) + lead) / d)


def tank(cv, cx, cy, w, h, a, water, oil, t, hidden=0.0, label=True):
    """示意：油罐剖面——下层是水，上面浮一层油；hidden>0 时显出罐内暗格"""
    if a <= 0.004: return
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    cv.rrect(x0, y0, x1, y1, 18, (0.09, 0.09, 0.10), a)
    lev_w = y1 - (h - 20) * water
    wob = 4 * math.sin(t * 2.0)
    cv.rect(x0 + 6, lev_w + wob * 0.3, x1 - 6, y1 - 6, WATER * 0.75, a * 0.9)
    if oil > 0:
        cv.rect(x0 + 6, lev_w - 26 * oil + wob * 0.3, x1 - 6, lev_w + wob * 0.3, OIL, a, glow=0.15)
    if hidden > 0:
        hx0, hx1 = cx + w * 0.08, x1 - 10
        cv.rect(hx0, y0 + 40, hx1, y1 - 10, (0.05, 0.05, 0.06), a * hidden)
        cv.rrect(hx0, y0 + 40, hx1, y1 - 10, 6, COST_R, a * hidden * 0.9, fill=False, th=3)
        cv.text('暗格', (hx0 + hx1) / 2, (y0 + y1) / 2 + 20, 30, 'sans_bold', col=COST_R, a=a * hidden)
    cv.rrect(x0, y0, x1, y1, 18, GREY, a * 0.9, fill=False, th=3)
    cv.arc((cx, y0), w / 2 - 6, math.pi, 2 * math.pi, GREY, a * 0.8, 3)
    if label:
        if oil > 0: cv.text('油', x0 - 40, lev_w - 14 * oil, 28, 'sans_bold', col=OIL, a=a)
        cv.text('水', x0 - 40, (lev_w + y1) / 2, 28, 'sans_bold', col=C(130, 180, 240), a=a)


def stock_line(cv, t, t0, pts, x0, x1, y0, y1, vmin, vmax, a, col=COST_R, dur=1.4, labels=None):
    """折线：pts = [(x 位置 0..1, 值)]，从左到右画出"""
    k = eexp((t - t0) / dur)
    if k <= 0 or a <= 0.004: return
    P = [(x0 + (x1 - x0) * u, y1 - (y1 - y0) * (v - vmin) / (vmax - vmin)) for u, v in pts]
    n = len(P) - 1; reach = k * n
    for j in range(n):
        f = cl(reach - j)
        if f <= 0: break
        p, q = P[j], P[j + 1]
        cv.line(p, (p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f), col, a, 5)
    if labels:
        for j, lb in labels.items():
            if reach >= j - 0.02:
                cv.glow_dot(P[j], 10, col, a)
                cv.text(lb, P[j][0], P[j][1] - 40, 40, 'sans_bold', col=CREAM if j == 0 else col, a=a * eo((reach - j + 0.02) / 0.3))


def coins(cv, t, t0, cx, cy, n, gold_n, a, r=34, per_row=3, stagger=0.06):
    """n 枚硬币（示意资产），其中 gold_n 枚为金色（股东自己的钱）"""
    for k in range(n):
        e = eo((t - t0 - k * stagger) / 0.35)
        if e <= 0: continue
        rr, c = divmod(k, per_row)
        x = cx + (c - (per_row - 1) / 2) * (2.4 * r); y = cy + (rr - (math.ceil(n / per_row) - 1) / 2) * (2.4 * r) - 20 * (1 - e)
        g = k < gold_n
        disc(cv, (x, y), r, GOLD if g else BANK_G * 0.6, a * e)
        cv.circle((x, y), r, GOLD_L if g else GREY, a * e, 2)
        cv.text('$', x, y, int(r * 1.1), 'sans_bold', col=(0.12, 0.10, 0.06) if g else (0.2, 0.2, 0.22), a=a * e)


def pct_bar(cv, t, t0, segs, x0, x1, y, h, a, dur=1.2, size=28):
    """一条按比例分段的横条：segs = [(标签, 数值, 颜色)]；从左到右生长"""
    tot = sum(s[1] for s in segs); k = eexp((t - t0) / dur)
    if k <= 0: return
    x = x0
    for lb, v, col in segs:
        w = (x1 - x0) * v / tot
        xe = min(x + w, x0 + (x1 - x0) * k)
        if xe > x:
            gbar(cv, x + 2, y - h / 2, xe - 2, y + h / 2, col, a, horizontal=True, glow=0.08, sheen_t=t - t0, reflect=False)
            if xe >= x + w - 1:
                cv.text(lb, x + w / 2, y + h / 2 + 34, size, 'sans_med', col=CREAM, a=a)
        x += w


def black_card(cv, cx, cy, s, a, rot=0.0, t=0.0, q=False):
    """示意：一张黑色卡片（不画任何商标）"""
    if a <= 0.004: return
    w, h = 400 * s, 250 * s
    cr, sr = math.cos(rot), math.sin(rot)
    def R(x, y): return (cx + x * cr - y * sr, cy + x * sr + y * cr)
    P = [R(-w / 2, -h / 2), R(w / 2, -h / 2), R(w / 2, h / 2), R(-w / 2, h / 2)]
    cv.fillpoly(P, (0.05, 0.05, 0.055), a)
    cv.poly(P + [P[0]], GOLD_D, a, 2)
    sweep = (t * 0.35) % 1.6 - 0.3
    if 0 <= sweep <= 1:
        p0 = R(-w / 2 + w * sweep, -h / 2); p1 = R(-w / 2 + w * sweep - 60 * s, h / 2)
        cv.line(p0, p1, GOLD_L, a * 0.35, int(10 * s))
    cv.fillpoly([R(-w / 2 + 34 * s, -30 * s), R(-w / 2 + 94 * s, -30 * s), R(-w / 2 + 94 * s, 14 * s), R(-w / 2 + 34 * s, 14 * s)], GOLD, a * 0.9)
    if q:
        p = R(60 * s, 0); cv.text('?', p[0], p[1], int(150 * s), 'serif_black', gold=True, a=a * 0.9, glow=0.2)


# ======================================================================== 开场
def shot_hook(cv, t):
    a0 = env(t, 0, S('h1') + 0.6, 0.0, 0.5)
    if a0 > 0:
        L = 420 * eo(t / 1.1); hb = math.exp(-max(t - 0.25, 0) * 6) * (t >= 0.25)
        cv.line((W / 2 - L, 960), (W / 2 + L, 960), GOLD, a0 * (0.5 + 0.5 * hb), 2)
        cv.glow_dot((W / 2, 960), 30 + 40 * hb, GOLD, a0 * 0.6)
    so = SEG['sot_open']; so_in = so['start'] - so['lead']
    # h1：2026 年 7 月，CNBC 专访
    t0, t1 = S('h1') - 0.3, so_in + 0.2
    a = A(t, t0, t1, 0.5, 0.35)
    if a > 0:
        seq(cv, t, t0, t1, ['ad89_city'], cy=520, h=480, a=a, cap='纽约（1989 年运通广告画面）')
        tag(cv, '2026 年 7 月 15 日 · CNBC 专访', t, t0 + 0.3, W / 2, 900, 30, GOLD, a)
        k = appear(t, 'h1', '九十五岁')
        if k > 0:
            cv.text('95 岁的巴菲特', W / 2, 1010, 56, 'serif_black', gold=True, a=a * k, glow=0.15)
        kb = appear(t, 'h1', '拿美国运通')
        if kb > 0:
            node(cv, 300, 1180, '银行', a * kb, col=BANK_G, size=40, w=300)
            cv.text('VS', W / 2, 1180, 44, 'oswald', col=GOLD, a=a * kb)
            node(cv, 780, 1180, '美国运通', a * kb, col=AX_BLUE, size=40, w=300)
        source(cv, 'CNBC Squawk Box · Becky Quick 专访巴菲特 · 2026-07-15', a, y=1462)
    # h2：1995 年基本买完，约 13 亿；二十多年一股没动
    t0, t1 = S('h2') - 0.5, S('h3') - 0.2
    a = A(t, t0, t1, 0.5, 0.4)
    if a > 0:
        pic(cv, ['buffett_2015', 'buffett_2010'], t, t0, t1, cy=520, h=480, a=a, cap='沃伦·巴菲特')
        y = 1060; xa, xb = 170, 910
        k = eexp((t - WT('h2', '一九九五') + 0.1) / 1.2)
        cv.line((xa, y), (xa + (xb - xa) * k, y), GOLD, a, 4)
        cv.text('1995', xa, y + 52, 34, 'oswald', col=GOLD_L, a=a * min(1, k * 4))
        cv.glow_dot((xa, y), 10, GOLD_L, a * min(1, k * 4))
        money(cv, t, WT('h2', '十三亿'), '约 13 亿美元', xa + 150, y - 80, 46, a, sub='买入基本完成')
        k2 = appear(t, 'h2', '最近')
        if k2 > 0:
            cv.text('今天', xb, y + 52, 32, 'sans_bold', col=GOLD_L, a=a * k2)
            cv.glow_dot((xb, y), 10, GOLD_L, a * k2)
            cv.text('二十多年', (xa + xb) / 2 + 120, y - 50, 40, 'sans_bold', col=CREAM, a=a * k2)
        for j, s_ in enumerate(('一股没买', '一股没卖')):
            chip(cv, s_, 380 + j * 320, 1240, 40, a * appear(t, 'h2', s_), col=GOLD_L)
        source(cv, '伯克希尔 2022 年信（“essentially completed in 1995 … $1.3 billion”）；2023 年信（“did not buy or sell a share … well over two decades”）', a, y=1462)
    # h3：回购 → 22.1%；成本 12.87 亿 vs 市值 560.88 亿；分红 4.79 亿
    t0, t1 = win2('h3')
    a = A(t, t0, t1)
    if a > 0:
        pic(cv, ['axp_tower', 'bldg65'], t, t0, t1, fb=['nyse_tick', 'nyse5', 'nyse4', 'nyse3'], fbcap='纽约证券交易所（1958 年资料画面）', cy=520, h=480, a=a, cap='纽约的美国运通大厦')
        kg = eexp((t - WT('h3', '百分之二十二点一') + 0.1) / 1.0)
        if kg > 0:
            gauge(cv, 230, 960, 78, 0.221 * kg, a * min(1, kg * 3), GOLD, None, size=40)
            cv.text('伯克希尔持股', 230, 1080, 26, 'sans_med', col=CREAM, a=a * min(1, kg * 3))
        hbar(cv, t, [('成本', 12.87, WT('h3', '这笔投资'), GOLD * 0.6), ('市值', 560.88, WT('h3', '五百六十一'), GOLD)], a,
             x0=470, x1=930, y0=920, dy=110, fmt=lambda v: f'${v:,.0f} 亿' if v > 100 else f'${v:.1f} 亿', size=36, lab=28, hl=1)
        k4 = appear(t, 'h3', '分红')
        if k4 > 0:
            cv.text(counter(0, 4.79, t, WT('h3', '四点七九'), 1.0, lambda v: f'${v:.2f} 亿'), W / 2, 1250, 72, 'sans_bold', gold=True, a=a * k4, glow=0.2)
            cv.text('2025 年一年的分红', W / 2, 1330, 28, 'sans_med', col=CREAM, a=a * k4)
        note(cv, '截至 2025-12-31', 1390, a * 0.8, 22)
        source(cv, '伯克希尔 2025 年致股东信持仓表：持股 22.1%，成本 $1,287M，市值 $56,088M，2025 年分红 $479M', a, y=1462)
    # h4：银行 13% vs 运通 30%+ → 三个问题
    t0, t1 = S('h4') - 0.3, CH['title'][0] + 0.1
    a = A(t, t0, t1, 0.4, 0.2)
    if a > 0:
        seq(cv, t, t0, t1 - 0.2, ['lg_logo', 'lg_wall', 'lg_window'], cy=520, h=480, a=a, cap='百夫长贵宾厅（2018）')
        kq = appear(t, 'h4', '这家做了')
        e1 = eexp((t - WT('h4', '银行赚') + 0.1) / 0.9); e2 = eexp((t - WT('h4', '它能赚') + 0.1) / 0.9)
        base = 1290; hm = 330
        if e1 > 0:
            gbar(cv, 300 - 80, base - hm * 13.5 / 32 * e1, 300 + 80, base, BANK_G, a * (1 - kq), sheen_t=t)
            cv.text('13%–14%', 300, base - hm * 13.5 / 32 * e1 - 40, 42, 'sans_bold', col=CREAM, a=a * (1 - kq) * min(1, e1 * 2))
            cv.text('大多数银行', 300, base + 40, 28, 'sans_med', col=CREAM, a=a * (1 - kq))
        if e2 > 0:
            gbar(cv, 780 - 80, base - hm * e2, 780 + 80, base, GOLD, a * (1 - kq), sheen_t=t, glow=0.2)
            cv.text('30%+', 780, base - hm * e2 - 44, 50, 'sans_bold', gold=True, a=a * (1 - kq) * min(1, e2 * 2), glow=0.2)
            cv.text('美国运通', 780, base + 40, 28, 'sans_med', col=GOLD_L, a=a * (1 - kq))
        big_q(cv, t, '凭什么？', 960, WT('h4', '凭什么'), 60, a * (1 - kq))
        big_q(cv, t, '护城河在哪里？', 1060, WT('h4', '护城河'), 60, a)
        big_q(cv, t, '哪些风险必须盯住？', 1190, WT('h4', '又有哪些'), 52, a, col=CREAM)
        source(cv, '巴菲特 CNBC 专访 2026-07-15（13%–14% vs 30%+ 为他的口头说法）', a * (1 - kq), y=1462)


def shot_title(cv, t):
    t0, t1 = CH['title'][0], CH['ch1'][0] + 0.6
    a = env(t, t0, t1, 0.02, 0.6)
    if a <= 0: return
    p = t - t0
    flash = math.exp(-p * 5.0)
    card(cv, W / 2 - 90, 640, 1.15, a * eo(p / 0.35), '', 'CHARGE CARD', col=C(120, 150, 190), rot=-0.12)
    cv.text('卡片为示意', W / 2, 845, 20, 'sans_light', col=GREY, a=a * eo((p - 0.4) / 0.5))
    black_card(cv, W / 2 + 110, 690, 1.05, a * eo((p - 0.15) / 0.4), rot=0.08, t=t)
    R = 60 + p * 900
    cv.circle((W / 2, 660), R, GOLD, a * math.exp(-p * 2.2) * 0.8, 3)
    cv.glow_dot((W / 2, 660), 220, GOLD, a * flash * 0.9)
    k = eo((p - 0.15) / 0.6)
    cv.text('银行赚 13%', W / 2, 1000, 100, 'serif_black', col=CREAM, a=a * k, scale=1.08 - 0.08 * k, shadow=0.8)
    cv.text('它凭什么赚 30%', W / 2, 1130, 110, 'serif_black', gold=True, a=a * eo((p - 0.35) / 0.6), glow=0.3)
    cv.text('巴菲特持有三十年的美国运通', W / 2, 1265, 52, 'serif_semi', col=CREAM, a=a * eo((p - 0.7) / 0.6))
    cv.text('THE 30% CARD', W / 2, 1355, 26, 'corm', col=GOLD, a=a * eo((p - 1.0) / 0.6), track=0.35)


# ======================================================================== 第一章：色拉油里的信任
def shot_ch1(cv, t):
    # c1a：1850 快运 → 1891 旅行支票
    t0, t1 = win2('c1a')
    a = A(t, t0, t1)
    if a > 0:
        tb = WT('c1a', '一八九一')
        if not pic(cv, ['wagon1913', 'ad1850', 'receipt1853'], t, t0, tb + 0.3, cy=520, h=480, a=a, cap='美国运通快运马车（新奥尔良，1913）'):
            seq(cv, t, t0, tb + 0.3, ['tc_bank'], cy=520, h=480, a=a)
        seq(cv, t, tb - 0.1, t1, ['tc_sign', 'tc_hand'], cy=520, h=480, a=a)
        y = 1080; xa, xb = 220, 860
        k = eexp((t - WT('c1a', '一八五零') + 0.1) / 1.4)
        cv.line((xa, y), (xa + (xb - xa) * k, y), GOLD, a, 4)
        for x, yr, lb, sub, tw in ((xa, '1850', '在纽约成立', '快运：货物、现金、贵重物品', WT('c1a', '一八五零')),
                                   (xb, '1891', '推出旅行支票', '出门不用揣大把现金', tb)):
            kk = eo((t - tw + 0.1) / 0.45)
            if kk <= 0: continue
            cv.glow_dot((x, y), 12, GOLD_L, a * kk)
            cv.text(yr, x, y - 60, 56, 'oswald', col=GOLD_L, a=a * kk)
            cv.text(lb, x, y + 54, 32, 'sans_bold', col=CREAM, a=a * kk)
            cv.text(sub, x, y + 100, 24, 'sans_light', col=GREY, a=a * kk)
        source(cv, '伯克希尔 2023 年信（“American Express began operations in 1850”）；维基百科 American Express（1891 年推出旅行支票）', a, y=1462)
    # c1b：卖的是信任
    t0, t1 = win2('c1b')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['tc_cheque', 'tc_beach'], cy=520, h=480, a=a, cap='美国运通旅行支票广告（1960 年代）')
        k = appear(t, 'c1b', '信任')
        if k > 0:
            cv.text('信任', W / 2, 1060, 170, 'serif_black', gold=True, a=a * k, glow=0.35, scale=1.1 - 0.1 * k)
        k2 = appear(t, 'c1b', '一九六三')
        if k2 > 0:
            chip(cv, '1963 · 一罐色拉油', W / 2, 1260, 36, a * k2, col=COST_R)
        source(cv, '本片概括', a * 0.6, y=1462)
    # c1c–c1d：骗局——仓单与油罐
    t0, t1 = S('c1c') - 0.3, S('c1e') - 0.2
    a = A(t, t0, t1)
    if a > 0:
        ph = pic(cv, ['bayonne'], t, t0, S('c1d') - 0.1, cy=520, h=480, a=a, cap='新泽西州贝永的油罐区（今日，仅示地点）')
        # 链条：商人 → 仓单（运通仓储子公司）→ 银行
        kc = 1 - eo((t - S('c1d') + 0.2) / 0.4)
        if kc > 0.004:
            yy = 1130
            k1 = appear(t, 'c1c', '商人'); k2 = appear(t, 'c1c', '替他证明'); k3 = appear(t, 'c1c', '向银行')
            node(cv, 180, yy, '商人', a * k1 * kc, col=CREAM, size=34, sub='植物油作抵押')
            node(cv, W / 2, yy, '仓单：油在罐里', a * k2 * kc, col=AX_BLUE, size=32, sub='运通旗下仓储子公司')
            node(cv, 900, yy, '银行', a * k3 * kc, col=BANK_G, size=34, sub='放出贷款')
            arrow(cv, (280, yy), (360, yy), a * kc, GOLD, k=eo((t - WT('c1c', '替他证明')) / 0.4))
            arrow(cv, (720, yy), (800, yy), a * kc, GOLD, k=k3)
            if not ph: tank(cv, W / 2, 520, 360, 400, a * kc, 0.9, 1.0, t, label=False)
        # 剖面：大多是水，油浮在上面；暗格；挪来挪去
        kd = eo((t - S('c1d') + 0.2) / 0.4)
        if kd > 0.004:
            w_ = eexp((t - WT('c1d', '大多是水') + 0.1) / 1.0)
            tank(cv, 330, 560, 300, 420, a * kd, 0.86 * w_, min(1, w_ * 1.5), t, hidden=0)
            tank(cv, 750, 560, 300, 420, a * kd, 0.86 * w_, min(1, w_ * 1.5), t, hidden=appear(t, 'c1d', '暗格'), label=False)
            km = appear(t, 'c1d', '挪来挪去')
            if km > 0:
                ph_ = (t * 0.6) % 1.0
                x = lerp(330, 750, eio(ph_)); y = 330 - 60 * math.sin(math.pi * ph_)
                cv.glow_dot((x, y), 18, OIL, a * km)
                cv.text('同一批油，重复点数', W / 2, 860, 30, 'sans_med', col=OIL, a=a * km)
            cv.text('示意', 960, 780, 20, 'sans_light', col=GREY, a=a * kd)
            kl = appear(t, 'c1d', '骗局败露')
            if kl > 0:
                chip(cv, '1963 年 11 月 · 骗局败露', W / 2, 1000, 32, a * kl, col=COST_R)
                kn = appear(t, 'c1d', '一点八', 0.3)
                if kn > 0: cv.text(counter(0, 1.8, t, WT('c1d', '一点八'), 1.0, lambda v: f'> {v:.1f} 亿美元'), W / 2, 1140, 92, 'sans_bold', col=COST_R, a=a * kn, glow=0.15)
                cv.text('贷款人的损失', W / 2, 1230, 32, 'sans_med', col=CREAM, a=a * kl)
        source(cv, '维基百科 Salad oil scandal（引 N. C. Miller《The Great Salad Oil Swindle》1965）：运通仓储子公司开具仓单；罐内多为水、暗格、重复点数；损失超过 1.8 亿美元', a, y=1462)
    # c1e：子公司破产，母公司主动和解 6000 万；股价 65 → 37
    t0, t1 = win2('c1e')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['nyse1', 'nyse2'], cy=520, h=480, a=a, cap='纽约证券交易所（1958 年资料画面）')
        k1 = appear(t, 'c1e', '破产'); k2 = appear(t, 'c1e', '六千万')
        chip(cv, '仓储子公司破产', 300, 900, 32, a * k1, col=GREY)
        if k2 > 0:
            cv.text('$6000 万', 760, 905, 56, 'sans_bold', gold=True, a=a * k2, glow=0.15)
            cv.text('母公司主动和解', 760, 960, 26, 'sans_med', col=CREAM, a=a * k2)
        ks = appear(t, 'c1e', '股价')
        if ks > 0:
            grid_lines(cv, 160, 920, 1360, 1060, a * ks * 0.6, n=3)
            stock_line(cv, t, WT('c1e', '六十五'), [(0, 65), (0.35, 61), (0.6, 48), (0.8, 40), (1, 37)], 200, 880, 1080, 1340, 30, 70, a * ks,
                       col=COST_R, dur=WT('c1e', '三十七') - WT('c1e', '六十五') + 0.3, labels={0: '$65', 4: '$37'})
            cv.text('1963 年 10 月', 200, 1395, 22, 'sans_light', col=GREY, a=a * ks)
            cv.text('1964 年 1 月', 880, 1395, 22, 'sans_light', col=GREY, a=a * ks)
        source(cv, '维基百科（子公司破产，运通代为和解 6000 万美元，股价跌去三分之一以上）；Fortune 2024-09-22 等（约 65 → 37 美元）', a, y=1462)
    # c1f：33 岁的巴菲特去餐馆看顾客结账
    t0, t1 = win2('c1f')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['tc_pisa'], cy=520, h=480, a=a, cap='同一时期的运通广告（1960 年代）')
        k1 = appear(t, 'c1f', '三十三岁')
        if k1 > 0:
            cv.text('33 岁的巴菲特', W / 2, 900, 52, 'serif_black', gold=True, a=a * k1)
            cv.text('去了奥马哈的餐馆', W / 2, 970, 34, 'sans_med', col=CREAM, a=a * appear(t, 'c1f', '奥马哈'))
        k2 = appear(t, 'c1f', '他想看')
        if k2 > 0:
            cv.rrect(140, 1060, 940, 1300, 18, (0.07, 0.06, 0.05), a * k2 * 0.9)
            cv.text('丑闻上了报纸——', W / 2, 1130, 40, 'sans_bold', col=CREAM, a=a * k2)
            cv.text('顾客还用不用运通的卡和旅行支票？', W / 2, 1220, 40, 'sans_bold', col=GOLD_L, a=a * appear(t, 'c1f', '顾客还用'))
        source(cv, 'Fortune 2024-09-22；InvestSmart《Salad oil: the making of Warren Buffett》（据传记与报道）', a, y=1462)
    # c1g：照用不误
    t0, t1 = win2('c1g')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['tc_bill'], cy=520, h=480, a=a, cap='美国运通旅行支票广告（1960 年代）')
        big_q(cv, t, '照用不误', 960, WT('c1g', '照用不误'), 96, a)
        k = appear(t, 'c1g', '丑闻伤的')
        if k > 0:
            node(cv, 300, 1180, '伤到了：公司的钱包', a * k, col=COST_R, size=32, w=420)
            node(cv, 780, 1180, '没伤到：顾客的信任', a * appear(t, 'c1g', '没有伤到'), col=GOLD, size=32, w=420)
        source(cv, '本片概括', a * 0.6, y=1462)
    # c1h：合伙基金约四成，最大一笔
    t0, t1 = win2('c1h')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['ax_logo60', 'tc_car'], cy=520, h=480, a=a, cap='美国运通广告（1960 年代）')
        g = eexp((t - WT('c1h', '四成') + 0.1) / 1.0)
        if g > 0:
            gauge(cv, 280, 1000, 100, 0.40 * g, a * min(1, g * 3), GOLD, '合伙基金的资金', fmt='约 {:.0f}%', size=44)
        k2 = appear(t, 'c1h', '有史以来')
        if k2 > 0:
            cv.text('有史以来', 700, 940, 40, 'sans_med', col=CREAM, a=a * k2)
            cv.text('最大的一笔投资', 700, 1010, 52, 'serif_black', gold=True, a=a * k2)
            cv.text('> 5% 股权 · 1300 万美元', 700, 1090, 28, 'sans_light', col=GREY, a=a * k2)
        source(cv, '伯克希尔 1994 年致股东信', a, y=1462)
    # c1i + 引语卡：2023 年信“毫无疑问的金融信任”
    t0, t1 = S('c1i') - 0.3, S('c1j') - 0.2
    a = A(t, t0, t1)
    if a > 0:
        cv.text('2023 年致股东信', W / 2, 420, 34, 'sans_med', col=GOLD, a=a)
        cv.text('“六十年后”', W / 2, 500, 56, 'serif_black', col=CREAM, a=a * appear(t, 'c1i', '六十年后'))
        qcard(cv, 'qtrust', t, E('c1i') - 0.3, t1, cy=900, en=38, cn=44, a=a, typing=2.4, w=980)
        source(cv, '伯克希尔 2023 年致股东信（原文比较可口可乐与美国运通）', a, y=1462)
    # c1j：信任，怎么变成钱？
    t0, t1 = S('c1j') - 0.3, CH['tk_ch1'][0] + 0.3
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['ad89_gold'], cy=520, h=480, a=a, cap='美国运通金卡（1989 年广告）')
        big_q(cv, t, '这份信任', 980, t0 + 0.4, 64, a, col=CREAM)
        big_q(cv, t, '是怎么变成钱的？', 1090, WT('c1j', '变成钱'), 72, a)


# ======================================================================== 第二章：一个闭环
def four_party(cv, t, a, y, ks, labels=None, dim=1.0):
    xs = [130, 345, 560, 775, 975]
    names = [('持卡人', CREAM, None), ('发卡银行', BANK_G, '如摩根大通'), ('Visa 网络', C(110, 140, 220), '只清算'), ('收单机构', BANK_G, '替商户收款'), ('商户', CREAM, None)]
    for j, (nm, col, sub) in enumerate(names):
        k = ks[j]
        if k <= 0: continue
        node(cv, xs[j], y + 12 * (1 - k), nm, a * k * dim, col=col, size=26, w=190, sub=sub)
        if j > 0 and ks[j] > 0.5: arrow(cv, (xs[j - 1] + 96, y), (xs[j] - 96, y), a * dim, GOLD_D, th=2, head=10, k=eo(ks[j]))
    if labels:
        for j, (lb, k) in labels.items():
            if k > 0: cv.text(lb, xs[j], y + 110, 26, 'sans_bold', col=GOLD_L, a=a * k * dim)


def shot_ch2(cv, t):
    # c2a–c2b：四方模式
    t0, t1 = S('c2a') - 0.3, S('c2c') - 0.2
    a = A(t, t0, t1)
    if a > 0:
        if not pic(cv, ['terminal', 'contactless'], t, t0, t1, cy=520, h=480, a=a, cap='刷卡支付'):
            ka = A(t, t0, t1, 0.5, 0.4)
            if ka > 0.004:                       # 示意：一张通用银行卡，刷卡后一笔钱沿四方流动
                u = (t - t0) % 6.0
                card(cv, 260 + 120 * eio(min(u / 1.2, 1)), 520, 1.0, a * ka, '', 'BANK CARD', col=C(110, 140, 220), rot=-0.08)
                cv.rrect(640, 400, 900, 660, 22, (0.08, 0.08, 0.09), a * ka); cv.rrect(640, 400, 900, 660, 22, GREY, a * ka, fill=False, th=2)
                cv.text('刷卡', 770, 470, 34, 'sans_bold', col=CREAM, a=a * ka)
                ok_ = eo((u - 1.3) / 0.3) * (1 - eo((u - 5.2) / 0.4))
                if ok_ > 0: cv.poly([(735, 570), (762, 600), (810, 540)], GREEN, a * ka * ok_, 8)
                cv.text('示意', 960, 740, 20, 'sans_light', col=GREY, a=a * ka)
        cv.text('一张普通 Visa 卡：一笔钱，经过四方', W / 2, 860, 34, 'sans_med', col=CREAM, a=a * appear(t, 'c2a', '四方'))
        ks = [appear(t, 'c2a', '先看'), appear(t, 'c2a', '发卡的银行'), appear(t, 'c2a', 'Visa 只管'), appear(t, 'c2a', '收单机构'), appear(t, 'c2a', '最后才是')]
        lab = {}
        if t > S('c2b') - 0.3:
            lab = {1: ('利息 · 年费', appear(t, 'c2b', '银行赚')), 2: ('过路费', appear(t, 'c2b', 'Visa 收')), 3: ('服务费', appear(t, 'c2b', '收单机构收'))}
        four_party(cv, t, a, 1040, ks, lab)
        if min(ks) > 0.99: flow_dots(cv, t, [(130, 1040), (975, 1040)], a, GOLD_L, n=4, speed=0.25, size=8)
        k = appear(t, 'c2b', '谁也拿不到')
        if k > 0: cv.text('谁也拿不到一笔交易的全部', W / 2, 1300, 46, 'serif_black', gold=True, a=a * k)
        note(cv, '示意（行业通行结构）', 1380, a * 0.8, 20)
        source(cv, '四方模式为信用卡行业通行结构；本片概括', a * 0.7, y=1462)
    # c2c–c2d：闭环
    t0, t1 = S('c2c') - 0.3, S('c2e') - 0.2
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['lg_front', 'lg_window', 'lg_seats', 'lg_conf'], cy=520, h=480, a=a, cap='百夫长贵宾厅（2018）')
        cx, cy, R = W / 2, 1110, 190
        ks = [appear(t, 'c2c', '自己发卡'), appear(t, 'c2c', '清算网络'), appear(t, 'c2c', '商户签约')]
        kd = eo((t - S('c2d') + 0.3) / 0.5)
        ring_cycle(cv, t, cx, cy, R, ['持卡人', '自己的网络', '商户'], a * (1 - 0.75 * kd), ks, col=AX_BLUE, size=30)
        k = appear(t, 'c2c', '闭环')
        if k > 0: cv.text('闭环', cx, cy, 64, 'serif_black', gold=True, a=a * k * (1 - 0.75 * kd), glow=0.3)
        if kd > 0.004:
            k1 = appear(t, 'c2d', '一是钱'); k2 = appear(t, 'c2d', '二是数据')
            node(cv, 290, 1030, '钱', a * k1, col=GOLD, size=40, w=380, sub='手续费 + 年费 + 利息')
            node(cv, 790, 1030, '数据', a * k2, col=AX_BLUE, size=40, w=380, sub='谁 · 在哪家店 · 花了多少')
            if k1 > 0: cv.text('进了同一个口袋', 290, 1160, 30, 'sans_med', col=CREAM, a=a * appear(t, 'c2d', '同一个口袋'))
            if k2 > 0: cv.text('看得一清二楚', 790, 1160, 30, 'sans_med', col=CREAM, a=a * appear(t, 'c2d', '一清二楚'))
        source(cv, '美国运通 2025 年报·致股东信：“our closed-loop network … direct relationships with millions of premium Card Members and merchants”', a, y=1462)
    # c2e：规模；闭环不是百分之百
    t0, t1 = win2('c2e')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['ad88_card', 'dl_cabin', 'dl_dusk'], cy=520, h=480, a=a, cap='运通卡（1988 年广告）/ 达美航空（2019）')
        for j, (num, unit, lb, tw, v1, fmt) in enumerate((
                ('八千六百六十万', '万张', '运通自己发的卡', '八千六百六十万', 8660, lambda v: f'{v:,.0f} 万'),
                ('一点六七万亿', '', '一年刷卡额', '一点六七万亿', 1.67, lambda v: f'${v:.2f} 万亿'),
                ('一点七亿', '', '全球受理点', '一点七亿', 1.7, lambda v: f'{v:.1f} 亿+'))):
            k = appear(t, 'c2e', tw)
            if k <= 0: continue
            x = 190 + j * 350
            cv.text(counter(0, v1, t, WT('c2e', tw), 1.0, fmt), x, 920, 54, 'sans_bold', gold=True, a=a * k, glow=0.15)
            cv.text(lb, x, 985, 26, 'sans_med', col=CREAM, a=a * k)
        kn = appear(t, 'c2e', '闭环也不是')
        if kn > 0:
            cv.rrect(110, 1080, 970, 1360, 18, (0.07, 0.06, 0.05), a * kn * 0.9)
            cv.text('闭环，不是百分之百', W / 2, 1140, 40, 'sans_bold', col=GOLD_L, a=a * kn)
            cv.text('· 别的银行发的运通卡：6620 万张', W / 2, 1215, 30, 'sans_med', col=CREAM, a=a * appear(t, 'c2e', '有些卡'))
            cv.text('· 有些小商户由第三方代签', W / 2, 1290, 30, 'sans_med', col=CREAM, a=a * appear(t, 'c2e', '有些小商户'))
        note(cv, '2025 年；受理点含第三方收单、支付机构与数字钱包', 1400, a * 0.8, 20)
        source(cv, '美国运通 2025 Form 10-K：billed business $1,670B；86.6M proprietary cards；66.2M third-party cards；170M+ merchant locations', a, y=1462)
    # c2f–c2g：飞轮
    t0, t1 = S('c2f') - 0.3, CH['tk_ch2'][0] + 0.3
    a = A(t, t0, t1)
    if a > 0:
        tg = S('c2g') - 0.2
        seq(cv, t, t0, tg + 0.3, ['dl_plane'], cy=520, h=480, a=a, cap='达美航空客机（2019）')
        seq(cv, t, tg, t1, ['lg_bar', 'lg_food', 'lg_canape'], cy=520, h=480, a=a, cap='百夫长贵宾厅（2018）')
        kf = 1 - eo((t - tg) / 0.5)
        if kf > 0.004:
            e1 = eexp((t - WT('c2f', '运通说') + 0.1) / 0.9); e2 = eexp((t - WT('c2f', '三倍') + 0.1) / 0.9)
            base, hm = 1300, 330
            gbar(cv, 300 - 90, base - hm / 3 * e1, 300 + 90, base, C(110, 140, 220), a * kf * min(1, e1 * 3), sheen_t=t)
            cv.text('1×', 300, base - hm / 3 * e1 - 40, 44, 'sans_bold', col=CREAM, a=a * kf * min(1, e1 * 3))
            cv.text('Visa、万事达卡', 300, base + 40, 26, 'sans_med', col=CREAM, a=a * kf * min(1, e1 * 3))
            gbar(cv, 780 - 90, base - hm * e2, 780 + 90, base, GOLD, a * kf * min(1, e2 * 3), sheen_t=t, glow=0.2)
            cv.text('≈ 3×', 780, base - hm * e2 - 44, 54, 'sans_bold', gold=True, a=a * kf * min(1, e2 * 3))
            cv.text('运通卡', 780, base + 40, 26, 'sans_med', col=GOLD_L, a=a * kf * min(1, e2 * 3))
            cv.text('平均每张卡一年的消费额', W / 2, 900, 34, 'sans_med', col=CREAM, a=a * kf * e1)
        kg = eo((t - tg) / 0.5)
        if kg > 0.004:
            ks = [appear(t, 'c2g', '花得多的客人'), appear(t, 'c2g', '手续费'), appear(t, 'c2g', '发积分'), appear(t, 'c2g', '吸引更多')]
            ring_cycle(cv, t, W / 2, 1130, 220, ['花得多的持卡人', '商户手续费更高', '积分 · 贵宾厅', '更多高消费会员'], a * kg, ks, col=GOLD, size=26)
            note(cv, '飞轮示意', 1395, a * kg * 0.8, 20)
        source(cv, '运通 2025 年报：每卡年消费约为 Visa、万事达卡的三倍（注 6）；商户费率高于 Visa/万事达：Nilson Report 2016（转引）', a, y=1462)


# ======================================================================== 第三章：七百二十二亿的账本
REV = dict(disc=374.01, fee=99.93, svc=74.71, nii=173.64, tot=722.29)


def shot_ch3(cv, t):
    # c3a：营收 722 亿
    t0, t1 = win2('c3a')
    a = A(t, t0, t1)
    if a > 0:
        doc_page(cv, t, t0 + 0.2, t1, 'AMERICAN EXPRESS · 2025 ANNUAL REPORT',
                 ['Discount revenue ........ $37,401M', 'Net card fees ............ $9,993M', 'Service fees and other ... $7,471M',
                  'Net interest income ..... $17,364M', 'Total revenues net of', '   interest expense ..... $72,229M'], cy=600, size=28,
                 hl='$72,229M', hl_t=WT('c3a', '七百二十二亿'), sub='截至 2025 年 12 月 31 日')
        big_num(cv, t, WT('c3a', '七百二十二亿'), '$722 亿', 1150, 140, a, sub='2025 年营收（扣除利息支出后）')
        source(cv, '美国运通 2025 年第四季度财报附表（Exhibit 99.2）', a, y=1462)
    # c3b–c3c：收入结构
    t0, t1 = S('c3b') - 0.3, S('c3d') - 0.2
    a = A(t, t0, t1)
    if a > 0:
        cv.text('2025 年营收从哪里来（亿美元）', W / 2, 340, 36, 'sans_med', col=CREAM, a=a)
        rows = [('商户手续费', REV['disc'], WT('c3b', '三百七十四'), GOLD), ('持卡人年费', REV['fee'], WT('c3b', '接近一百亿'), GOLD_L),
                ('服务费等', REV['svc'], WT('c3b', '七十五亿'), GOLD * 0.7), ('净利息收入', REV['nii'], WT('c3c', '一百七十四'), BANK_G)]
        hbar(cv, t, rows, a, x0=330, x1=880, y0=470, dy=105, vmax=400, fmt=lambda v: f'{v:,.0f}', size=40, lab=30, hl=0)
        k18 = appear(t, 'c3b', '百分之十八')
        if k18 > 0:
            chip(cv, '+18% · 连续 30 个季度两位数增长', 730, 575, 24, a * k18, col=GOLD_L)
        kc = appear(t, 'c3c', '四分之三')
        if kc > 0.004 or t > WT('c3c', '只占'):
            pct_bar(cv, t, WT('c3c', '只占') - 0.2, [('非利息收入 76%', 54.865, GOLD), ('利息 24%', 17.364, BANK_G)], 110, 970, 1000, 70, a, size=30)
        if kc > 0:
            cv.text('跟着刷卡和会员走', W / 2, 1170, 52, 'serif_black', gold=True, a=a * kc)
            cv.text('不靠放贷利差', W / 2, 1250, 40, 'sans_bold', col=CREAM, a=a * appear(t, 'c3c', '不靠放贷'))
        source(cv, '美国运通 2025 年第四季度财报附表：discount revenue $37,401M；net card fees $9,993M（+18%）；service fees $7,471M；net interest income $17,364M', a, y=1462)
    # c3d：银行的路
    t0, t1 = win2('c3d')
    a = A(t, t0, t1)
    if a > 0:
        cv.text('银行想多赚钱', W / 2, 420, 52, 'serif_black', col=BANK_G, a=a * appear(t, 'c3d', '银行想'))
        ys = [600, 790, 980]
        for j, (s_, sub, tw) in enumerate((('多放贷款', None, '多放贷款'), ('多押一份资本', '监管资本', '多押'), ('多担一份坏账风险', None, '多担'))):
            k = appear(t, 'c3d', tw)
            node(cv, W / 2, ys[j], s_, a * k, col=BANK_G if j == 0 else COST_R * 0.9 + 0.1, size=40, w=520, sub=sub)
            if j > 0: arrow(cv, (W / 2, ys[j - 1] + 60), (W / 2, ys[j] - 60), a, GREY, k=k)
        k2 = appear(t, 'c3d', '分水岭')
        if k2 > 0: chip(cv, '分水岭', W / 2, 1190, 38, a * k2, col=GOLD)
        source(cv, '本片解读', a * 0.6, y=1462)
    # c3e：每 100 美元资产赚多少
    t0, t1 = win2('c3e')
    a = A(t, t0, t1)
    if a > 0:
        cv.text('每 100 美元资产，一年赚多少钱', W / 2, 400, 44, 'sans_bold', col=CREAM, a=a * eo((t - t0 - 0.2) / 0.5))
        base, hm = 1150, 560
        e1 = eexp((t - WT('c3e', '全美银行业') + 0.1) / 0.9); e2 = eexp((t - WT('c3e', '运通是') + 0.1) / 0.9)
        if e1 > 0:
            gbar(cv, 300 - 100, base - hm * 1.2 / 3.8 * e1, 300 + 100, base, BANK_G, a, sheen_t=t)
            cv.text(f'${1.2 * e1:.1f}', 300, base - hm * 1.2 / 3.8 * e1 - 50, 64, 'sans_bold', col=CREAM, a=a * min(1, e1 * 2))
            cv.text('全美银行业平均', 300, base + 44, 30, 'sans_med', col=CREAM, a=a)
        if e2 > 0:
            gbar(cv, 780 - 100, base - hm * e2, 780 + 100, base, GOLD, a, sheen_t=t, glow=0.2)
            cv.text(f'${3.8 * e2:.1f}', 780, base - hm * e2 - 54, 76, 'sans_bold', gold=True, a=a * min(1, e2 * 2), glow=0.2)
            cv.text('美国运通', 780, base + 44, 30, 'sans_med', col=GOLD_L, a=a)
        k3 = appear(t, 'c3e', '三倍多')
        if k3 > 0: chip(cv, '三倍多', W / 2, 1290, 44, a * k3, col=GOLD_L)
        note(cv, '2025 年资产回报率（ROA）', 1380, a * 0.8, 22)
        source(cv, 'FDIC Quarterly Banking Profile 2025Q4（全年 ROA 1.20%）；运通：净利润 $10,833M ÷ 平均总资产 ≈ 3.8%（本片计算）', a, y=1462)
    # c3f：不靠杠杆；ROE 33.9%
    t0, t1 = win2('c3f')
    a = A(t, t0, t1)
    if a > 0:
        cv.text('不是靠多借钱', W / 2, 360, 48, 'serif_black', col=CREAM, a=a * appear(t, 'c3f', '没有靠'))
        coins(cv, t, WT('c3f', '每九美元'), W / 2, 600, 9, 1, a, r=46, per_row=3)
        k = appear(t, 'c3f', '一美元')
        if k > 0:
            cv.text('每 9 美元资产里，约 1 美元是股东自己的钱', W / 2, 840, 32, 'sans_med', col=GOLD_L, a=a * k)
        g = eexp((t - WT('c3f', '百分之三十三点九') + 0.1) / 1.0)
        if g > 0:
            gauge(cv, 300, 1110, 120, 0.339 * g, a * min(1, g * 3), GOLD, '净资产收益率 · 2025', size=52)
        k3 = appear(t, 'c3f', '近三年')
        if k3 > 0:
            for j, (yr, v) in enumerate((('2023', 31.5), ('2024', 34.6), ('2025', 33.9))):
                x = 640 + j * 130; hh = 230 * v / 40 * eexp((t - WT('c3f', '近三年') - j * 0.15) / 0.8)
                gbar(cv, x - 40, 1230 - hh, x + 40, 1230, GOLD if j == 2 else GOLD * 0.6, a * k3, reflect=False)
                cv.text(f'{v}%', x, 1230 - hh - 30, 28, 'sans_bold', col=CREAM, a=a * k3)
                cv.text(yr, x, 1268, 24, 'oswald', col=GREY, a=a * k3)
        source(cv, '运通 2025 年报：股东权益 $33,474M ÷ 总资产 $300,052M ≈ 11%；ROE 33.9%（2025）、34.6%（2024）、31.5%（2023）', a, y=1462)
    # c3g：核销率只有一半
    t0, t1 = win2('c3g')
    a = A(t, t0, t1)
    if a > 0:
        cv.text('风险呢？', W / 2, 380, 60, 'serif_black', gold=True, a=a * appear(t, 'c3g', '风险呢'))
        cv.text('信用卡贷款核销率 · 2025', W / 2, 470, 32, 'sans_med', col=CREAM, a=a * appear(t, 'c3g', '核销率'))
        base, hm = 1060, 460
        e1 = eexp((t - WT('c3g', '全美商业银行') + 0.1) / 0.9); e2 = eexp((t - WT('c3g', '运通卡贷款') + 0.1) / 0.9)
        if e1 > 0:
            gbar(cv, 300 - 100, base - hm * e1, 300 + 100, base, COST_R * 0.8, a, sheen_t=t)
            cv.text('4.1%–4.4%', 300, base - hm * e1 - 44, 50, 'sans_bold', col=CREAM, a=a * min(1, e1 * 2))
            cv.text('全美商业银行', 300, base + 40, 28, 'sans_med', col=CREAM, a=a)
        if e2 > 0:
            gbar(cv, 780 - 100, base - hm * 2.2 / 4.3 * e2, 780 + 100, base, GOLD, a, sheen_t=t, glow=0.2)
            cv.text('2.2%', 780, base - hm * 2.2 / 4.3 * e2 - 48, 60, 'sans_bold', gold=True, a=a * min(1, e2 * 2))
            cv.text('美国运通', 780, base + 40, 28, 'sans_med', col=GOLD_L, a=a)
        k3 = appear(t, 'c3g', '大约只有一半')
        if k3 > 0: chip(cv, '大约只有一半', 780, 1170, 34, a * k3, col=GOLD_L)
        k4 = appear(t, 'c3g', '赚得多')
        if k4 > 0:
            cv.text('赚得多，风险却不比银行大', W / 2, 1300, 50, 'serif_black', gold=True, a=a * k4, glow=0.15)
        source(cv, '美联储 FRED CORCCACBS（2025 年各季度 4.43%、4.18%、4.18%、4.11%）；运通 2025Q4 附表：卡贷款净核销率（仅本金）2.2%', a, y=1462)
    # c3h：代价——积分与服务 245 亿
    t0, t1 = win2('c3h')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['lg_wall', 'lg_conf'], cy=520, h=480, a=a, cap='百夫长贵宾厅（2018）')
        k = appear(t, 'c3h', '两百四十五')
        if k > 0:
            cv.text(counter(0, 245, t, WT('c3h', '两百四十五'), 1.0, lambda v: f'${v:,.0f} 亿'), 380, 1010, 96, 'sans_bold', gold=True, a=a * k, glow=0.2)
            cv.text('积分 184 亿 + 持卡人服务 61 亿', 380, 1100, 28, 'sans_med', col=CREAM, a=a * k)
        g = eexp((t - WT('c3h', '三分之一') + 0.1) / 1.0)
        if g > 0:
            gauge(cv, 830, 1030, 110, 0.34 * g, a * min(1, g * 3), COST_R, '相当于营收', fmt='≈{:.0f}%', size=46)
        k2 = appear(t, 'c3h', '不是白来的')
        if k2 > 0: cv.text('这些钱，不是白来的', W / 2, 1290, 44, 'serif_black', col=CREAM, a=a * k2)
        source(cv, '运通 2025Q4 附表：Card Member rewards $18,409M；Card Member services $6,057M（合计 ≈ 营收 34%）', a, y=1462)
    # c3i：76 亿还给股东；回购让伯克希尔持股上升
    t0, t1 = S('c3i') - 0.3, CH['tk_ch3'][0] + 0.3
    a = A(t, t0, t1)
    if a > 0:
        k = max(appear(t, 'c3i', '七十六亿'), eo((t - t0 - 0.3) / 0.5) * 0)
        cv.text('剩下的利润，大量还给了股东', W / 2, 330, 34, 'sans_med', col=CREAM, a=a * eo((t - t0 - 0.2) / 0.5))
        if k > 0:
            cv.text(counter(0, 76, t, WT('c3i', '七十六亿'), 1.0, lambda v: f'${v:,.0f} 亿'), W / 2, 450, 110, 'sans_bold', gold=True, a=a * k, glow=0.25)
            cv.text('2025 年分红 + 回购，还给股东', W / 2, 545, 32, 'sans_med', col=CREAM, a=a * k)
        kr = eexp((t - WT('c3i', '越回购越少') + 0.1) / 2.0)
        if kr > 0:
            n_all = 40; gone = int(round(3 * kr))
            for j in range(n_all):
                r, c = divmod(j, 10); x = 170 + c * 82; y = 700 + r * 70
                lit = j < 9
                fade = 1.0 if j < n_all - gone else 0.15
                cv.rect(x, y, x + 64, y + 50, GOLD if lit else BANK_G * 0.6, a * fade * min(1, kr * 3))
            cv.text('流通股：越回购越少', W / 2, 1010, 32, 'sans_med', col=CREAM, a=a * min(1, kr * 3))
            cv.text('伯克希尔那一份（金色）不变，占比却在变大', W / 2, 1060, 26, 'sans_light', col=GOLD_L, a=a * min(1, kr * 3))
        kb = appear(t, 'c3i', '开头')
        if kb > 0:
            hbar(cv, t, [('2024 年末', 702, WT('c3i', '开头'), BANK_G), ('2025 年末', 686, WT('c3i', '开头') + 0.4, GOLD)], a,
                 x0=330, x1=880, y0=1180, dy=95, vmax=720, fmt=lambda v: f'{v:.0f} 百万股', size=32, lab=28)
            note(cv, '示意：金色方块 = 伯克希尔持有的股份', 1395, a * kb * 0.8, 20)
        source(cv, '运通 2025 年报（$7.6B 分红与回购）；2025Q4 附表（流通股 702M → 686M）；伯克希尔 2022 年信', a, y=1462)


# ======================================================================== 第四章：Costco 走了以后
def shot_ch4(cv, t):
    # c4a：麻烦来自 Costco
    t0, t1 = win2('c4a')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['a_floor', 'a_aisle'], cy=520, h=480, a=a, cap='Costco 卖场（ABC 2005）')
        big_q(cv, t, '这台机器，也遇到过大麻烦', 980, t0 + 0.3, 50, a, col=CREAM)
        k = appear(t, 'c4a', 'Costco')
        if k > 0: cv.text('Costco', W / 2, 1150, 120, 'serif_black', gold=True, a=a * k, glow=0.25, scale=1.08 - 0.08 * k)
        cv.text('上一期的主角', W / 2, 1260, 32, 'sans_med', col=CREAM, a=a * appear(t, 'c4a', '上一期'))
    # c4b：1999 只收运通；2004 联名卡
    t0, t1 = win2('c4b')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['a_entrance', 'a_lot'], cy=520, h=480, a=a, cap='Costco（ABC 2005）')
        y = 1070; xa, xb = 220, 860
        k = eexp((t - WT('c4b', '一九九九') + 0.1) / 1.2)
        cv.line((xa, y), (xa + (xb - xa) * k, y), GOLD, a, 4)
        for x, yr, lb, tw in ((xa, '1999', '美国门店只收运通一种信用卡', '一九九九'), (xb, '2004', '一起发联名卡', '二零零四')):
            kk = appear(t, 'c4b', tw)
            if kk <= 0: continue
            cv.glow_dot((x, y), 12, GOLD_L, a * kk)
            cv.text(yr, x, y - 60, 56, 'oswald', col=GOLD_L, a=a * kk)
            for li, ln in enumerate(wrap_cn(lb, 'sans_med', 30, 380)):
                cv.text(ln, x, y + 56 + li * 40, 30, 'sans_med', col=CREAM, a=a * kk)
        source(cv, '维基百科 American Express（引 Bloomberg 2015-10-15：独家协议始于 1999 年，联名卡始于 2004 年）', a, y=1462)
    # c4c：2015-02 宣布不续约；20% 贷款、10% 发卡；当天 −6%
    t0, t1 = win2('c4c')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['a_crowd', 'a_cans', 'a_sign'], cy=520, h=480, a=a, cap='Costco（ABC 2005）')
        k = appear(t, 'c4c', '二零一五')
        if k > 0:
            chip(cv, '2015 年 2 月 · 宣布', 300, 880, 30, a * k, col=GOLD)
            chip(cv, '2016 年 3 月底 · 不再续约', 760, 880, 30, a * appear(t, 'c4c', '不再续约'), col=COST_R)
        g1 = eexp((t - WT('c4c', '百分之二十') + 0.1) / 1.0); g2 = eexp((t - WT('c4c', '一成') + 0.1) / 1.0)
        if g1 > 0: gauge(cv, 240, 1110, 100, 0.20 * g1, a * min(1, g1 * 3), COST_R, '全球卡贷款', fmt='约 {:.0f}%', size=44)
        if g2 > 0: gauge(cv, 540, 1110, 100, 0.10 * g2, a * min(1, g2 * 3), COST_R, '全球发卡量', fmt='约 {:.0f}%', size=44)
        ks = appear(t, 'c4c', '股价当天')
        if ks > 0:
            cv.text('−6%', 850, 1090, 96, 'sans_bold', col=COST_R, a=a * ks, glow=0.15)
            cv.text('运通股价 · 当天', 850, 1170, 26, 'sans_med', col=CREAM, a=a * ks)
        note(cv, 'Costco 联名卡在运通的占比（2015 年运通披露）', 1300, a * 0.8, 22)
        source(cv, '运通 8-K 及声明 2015-02-12（“about 20% of worldwide loans and about 10% of worldwide cards in force”）；Fortune、Motley Fool（当日约 −6%）', a, y=1462)
    # c4d：为什么谈不拢
    t0, t1 = win2('c4d')
    a = A(t, t0, t1)
    if a > 0:
        big_q(cv, t, '为什么谈不拢？', 400, t0 + 0.2, 64, a)
        k1 = appear(t, 'c4d', '百分之零点六')
        if k1 > 0:
            cv.text('≈0.6%', W / 2, 620, 150, 'sans_bold', gold=True, a=a * k1, glow=0.2)
            cv.text('Costco 接受运通卡的成本 · 每笔', W / 2, 730, 32, 'sans_med', col=CREAM, a=a * k1)
            cv.text('已经很低', W / 2, 790, 30, 'sans_light', col=GREY, a=a * k1)
        k2 = appear(t, 'c4d', '更多地方')
        if k2 > 0: node(cv, W / 2, 960, '希望会员手里的卡，能在更多地方刷', a * k2, col=CREAM, size=34, w=760)
        k3 = appear(t, 'c4d', '招标')
        if k3 > 0:
            arrow(cv, (W / 2, 1030), (W / 2, 1110), a, GOLD, k=k3)
            node(cv, W / 2, 1190, '向别家招标：花旗 + Visa', a * k3, col=C(110, 140, 220), size=36, w=640, sub='开出了更好的条件')
        source(cv, 'Bloomberg Businessweek 2015-10-15《How American Express Lost Costco》', a, y=1462)
    # c4e：谢诺：账算不过来；2016-06 改收 Visa
    t0, t1 = win2('c4e')
    a = A(t, t0, t1)
    if a > 0:
        pic(cv, ['chenault'], t, t0, t1, fb=['w_ext', 'a_shelf'], fbcap='Costco（WBZ 1991 / ABC 2005）', cy=520, h=480, a=a, cap='肯尼斯·谢诺（运通时任 CEO）')
        qcard(cv, 'qnumbers', t, WT('c4e', '这笔账') - 0.4, t1, cy=1000, en=40, cn=44, a=a, typing=0.8, w=900)
        k = appear(t, 'c4e', '二零一六年六月')
        if k > 0:
            chip(cv, '2016 年 6 月 · Costco 美国门店改收 Visa，花旗发卡', W / 2, 1270, 28, a * k, col=GOLD)
        source(cv, 'Kenneth Chenault 2015-03（Bloomberg 等报道）；CS Monitor 2016；维基百科', a, y=1462)
    # c4f：斯奎里：收年费的卡
    t0, t1 = win2('c4f')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['lg_family', 'lg_seats'], cy=520, h=480, a=a, cap='百夫长贵宾厅（2018）')
        k = appear(t, 'c4f', '收年费的卡')
        if k > 0: cv.text('更多力气：收年费的卡', W / 2, 880, 44, 'serif_black', gold=True, a=a * k)
        ks = appear(t, 'c4f', '二零一八')
        if ks > 0: cv.text('2018 年 · 斯奎里接任 CEO', W / 2, 960, 30, 'sans_med', col=CREAM, a=a * ks)
        for j, (s_, tw) in enumerate((('升级白金卡、金卡权益', '一次次升级'), ('2019 · 收购 Resy', '买下'), ('扩建机场贵宾厅', '扩建'))):
            node(cv, W / 2, 1080 + j * 110, s_, a * appear(t, 'c4f', tw), col=GOLD, size=32, w=560)
        source(cv, '运通 2025 年报（Framework for Winning，2018 年起）；Resy 2019 年收购（运通公告）', a, y=1462)
    # c4g：年费收入 34 亿 → 近 100 亿
    t0, t1 = win2('c4g')
    a = A(t, t0, t1)
    if a > 0:
        cv.text('净年费收入（亿美元）', W / 2, 420, 38, 'sans_med', col=CREAM, a=a)
        vbars(cv, t, [('2018', 34.41, WT('c4g', '二零一八'), GOLD * 0.6, None), ('2025', 99.93, WT('c4g', '二零二五'), GOLD, None)], a,
              x0=250, x1=830, base=1150, hmax=560, fmt=lambda v: f'{v:,.0f}', size=56, lab=32)
        k = appear(t, 'c4g', '差不多三倍')
        if k > 0: chip(cv, '差不多三倍', W / 2, 1280, 44, a * k, col=GOLD_L)
        source(cv, '运通 2019Q4 财报附表（SEC EX-99.2：2018 年 net card fees $3,441M）；2025Q4 附表（$9,993M）', a, y=1462)
    # c4h：事后看的结果
    t0, t1 = S('c4h') - 0.3, CH['tk_ch4'][0] + 0.3
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['ad89_gold', 'ad88_card', 'lg_window'], cy=520, h=480, a=a, cap='运通卡（1989 / 1988 年广告）')
        k1 = appear(t, 'c4h', '丢了')
        if k1 > 0:
            node(cv, 290, 1000, '丢了一个大客户', a * k1, col=COST_R, size=34, w=420)
            arrow(cv, (510, 1000), (570, 1000), a, GOLD, k=appear(t, 'c4h', '换来'))
            node(cv, 790, 1000, '更靠会员费的生意', a * appear(t, 'c4h', '换来'), col=GOLD, size=34, w=420)
        k2 = appear(t, 'c4h', '事后看')
        if k2 > 0:
            cv.text('这是事后看的结果', W / 2, 1180, 46, 'serif_black', col=CREAM, a=a * k2)
            cv.text('当年，谁也不敢打包票', W / 2, 1260, 36, 'sans_med', col=GREY, a=a * appear(t, 'c4h', '当年'))
        source(cv, '本片解读（不作因果断言）', a * 0.6, y=1462)


# ======================================================================== 第五章：面子与里子
def shot_ch5(cv, t):
    # c5a：矛与盾（呼应上期）
    t0, t1 = win2('c5a')
    a = A(t, t0, t1)
    if a > 0:
        chip(cv, '上一期的结论', W / 2, 400, 30, a, col=GOLD)
        k1 = appear(t, 'c5a', '名气')
        spear(cv, 330, 640, 1.4, a * k1, GOLD_L)
        cv.text('名气：拉新的矛', 330, 780, 38, 'sans_bold', col=GOLD_L, a=a * k1)
        k2 = appear(t, 'c5a', '商品和价格')
        shield(cv, 760, 640, 1.2, a * k2, GOLD)
        cv.text('商品和价格：留存的盾', 760, 800, 36, 'sans_bold', col=GOLD, a=a * k2)
        k3 = appear(t, 'c5a', '在运通身上')
        if k3 > 0: cv.text('在运通身上，这两样都看得到', W / 2, 1050, 48, 'serif_black', gold=True, a=a * k3)
        source(cv, '第六期第五章结论（本片解读）', a * 0.6, y=1462)
    # c5b：黑卡传说
    t0, t1 = win2('c5b')
    a = A(t, t0, t1)
    if a > 0:
        k = appear(t, 'c5b', '先说矛')
        spear(cv, W / 2, 380, 1.0, a * k, GOLD_L)
        kb = appear(t, 'c5b', '坊间')
        black_card(cv, W / 2, 620, 1.4, a * kb, rot=-0.06 + 0.02 * math.sin(t), t=t, q=True)
        cv.text('示意', W / 2 + 300, 820, 20, 'sans_light', col=GREY, a=a * kb)
        if kb > 0: cv.text('上世纪八十年代的传说：一张不做广告、只发给顶级富豪的黑卡', W / 2, 890, 28, 'sans_med', col=CREAM, a=a * kb)
        qcard(cv, 'qrumor', t, WT('c5b', '运通欧洲') - 0.2, t1, cy=1140, en=32, cn=38, a=a, typing=1.2, w=960)
        source(cv, '维基百科 Centurion Card（引 Snopes 对运通欧洲负责人的采访）', a, y=1462)
    # c5c：1999 百夫长卡；如今入会费 1 万、年费 5000
    t0, t1 = win2('c5c')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['lg_logo', 'lg_conf'], cy=520, h=480, a=a, cap='百夫长贵宾厅（2018）')
        k = appear(t, 'c5c', '一九九九')
        if k > 0:
            cv.text('1999', 280, 920, 72, 'oswald', col=GOLD_L, a=a * k)
            cv.text('百夫长卡推出', 280, 990, 30, 'sans_med', col=CREAM, a=a * k)
            chip(cv, '只能受邀办理', 760, 930, 34, a * appear(t, 'c5c', '受邀'), col=GOLD)
        k2 = appear(t, 'c5c', '入会费')
        if k2 > 0:
            cv.text('$10,000', 300, 1170, 76, 'sans_bold', gold=True, a=a * k2)
            cv.text('入会费', 300, 1240, 28, 'sans_med', col=CREAM, a=a * k2)
            k3 = appear(t, 'c5c', '年费')
            cv.text('$5,000', 780, 1170, 76, 'sans_bold', gold=True, a=a * k3)
            cv.text('年费', 780, 1240, 28, 'sans_med', col=CREAM, a=a * k3)
            note(cv, '如今的收费，据报道', 1320, a * k2 * 0.8, 22)
        source(cv, '维基百科 Centurion Card（1999）；The Points Guy、One Mile at a Time（现行收费，2020 年上调）', a, y=1462)
    # c5d：年轻人 65% / 75%
    t0, t1 = win2('c5d')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['lg_seats', 'lg_window', 'lg_front'], cy=520, h=480, a=a, cap='百夫长贵宾厅（2018）')
        k = appear(t, 'c5d', '老一辈')
        if k > 0: cv.text('“老一辈商界精英的卡”？', W / 2, 880, 40, 'serif_semi', col=GREY, a=a * k * (1 - appear(t, 'c5d', '年报却显示')))
        g1 = eexp((t - WT('c5d', '百分之六十五') + 0.1) / 1.0); g2 = eexp((t - WT('c5d', '百分之七十五') + 0.1) / 1.0)
        if g1 > 0: gauge(cv, 290, 1090, 120, 0.65 * g1, a * min(1, g1 * 3), GOLD, '全球新增个人账户', fmt='约 {:.0f}%', size=48)
        if g2 > 0: gauge(cv, 790, 1090, 120, 0.75 * g2, a * min(1, g2 * 3), GOLD_L, '美国新办金卡、白金卡', fmt='约 {:.0f}%', size=48)
        if g1 > 0: cv.text('来自千禧一代和 Z 世代 · 2025', W / 2, 1330, 30, 'sans_med', col=CREAM, a=a * min(1, g1 * 3))
        source(cv, '美国运通 2025 年报·致股东信', a, y=1462)
    # c5e：33 岁 / 29 岁
    t0, t1 = win2('c5e')
    a = A(t, t0, t1)
    if a > 0:
        card(cv, 300, 640, 1.05, a * appear(t, 'c5e', '白金卡'), '白金卡（示意）', 'PLATINUM', col=C(190, 195, 205), rot=-0.06)
        card(cv, 780, 640, 1.05, a * appear(t, 'c5e', '金卡'), '金卡（示意）', 'GOLD', col=C(210, 175, 90), rot=0.06)
        money(cv, t, WT('c5e', '三十三'), '33 岁', 300, 950, 96, a, sub='新办白金卡的人，平均')
        money(cv, t, WT('c5e', '二十九'), '29 岁', 780, 950, 96, a, sub='新办金卡的人，平均')
        note(cv, '美国个人卡 · 2025 年新客户', 1200, a * 0.8, 24)
        source(cv, '美国运通 2025 年报·致股东信（“33 and 29, respectively”）', a, y=1462)
    # c5f：面子 vs 里子
    t0, t1 = win2('c5f')
    a = A(t, t0, t1)
    if a > 0:
        k1 = appear(t, 'c5f', '面子')
        spear(cv, 300, 560, 1.2, a * k1, GOLD_L)
        cv.text('面子', 300, 700, 64, 'serif_black', gold=True, a=a * k1)
        cv.text('办下第一张卡', 300, 780, 32, 'sans_med', col=CREAM, a=a * k1)
        k2 = appear(t, 'c5f', '里子')
        shield(cv, 780, 560, 1.0, a * k2, GOLD)
        cv.text('里子', 780, 700, 64, 'serif_black', gold=True, a=a * k2)
        cv.text('第二年还续不续', 780, 780, 32, 'sans_med', col=CREAM, a=a * k2)
        k3 = appear(t, 'c5f', '值不值')
        if k3 > 0: cv.text('权益，值不值这份年费？', W / 2, 1000, 52, 'serif_black', col=CREAM, a=a * k3)
        source(cv, '本片解读', a * 0.6, y=1462)
    # c5g：$695 → $895；运通口径 $3,500；第三方测算更少
    t0, t1 = win2('c5g')
    a = A(t, t0, t1)
    if a > 0:
        chip(cv, '2025 年 9 月 · 美国白金卡', W / 2, 400, 30, a, col=GOLD)
        k = appear(t, 'c5g', '六百九十五')
        if k > 0:
            x = 330; cv.text('$695', x, 540, 80, 'sans_bold', col=GREY, a=a * k)
            kx = appear(t, 'c5g', '八百九十五')
            if kx > 0:
                cv.line((x - 90, 540), (x - 90 + 180 * kx, 540), COST_R, a, 5)
                arrow(cv, (450, 540), (580, 540), a, GOLD, k=kx)
                cv.text('$895', 760, 540, 100, 'sans_bold', gold=True, a=a * kx, glow=0.2)
                cv.text('年费', 760, 620, 28, 'sans_med', col=CREAM, a=a * kx)
        e1 = eexp((t - WT('c5g', '三千五百') + 0.1) / 1.0)
        if e1 > 0:
            hbar(cv, t, [('运通的说法', 3500, WT('c5g', '三千五百'), GOLD), ('第三方测算', 2000, WT('c5g', '有媒体估算'), C(110, 140, 220))], a,
                 x0=330, x1=880, y0=860, dy=130, vmax=3600, fmt=lambda v: '$3,500+' if v > 3000 else '$1,500–2,500', size=36, lab=28)
            cv.text('权益合计（需用满每一项额度）', W / 2, 1110, 26, 'sans_light', col=GREY, a=a * e1)
        k3 = appear(t, 'c5g', '普通人')
        if k3 > 0: cv.text('普通人实际用得上的，要少得多', W / 2, 1230, 42, 'serif_black', col=CREAM, a=a * k3)
        source(cv, 'The Points Guy、Fortune 2025-09-19（$695 → $895）；运通发言人（$3,500）；Kudos、Card Savvy 等测算（多数持卡人约 $1,500–2,500）', a, y=1462)
    # c5h：权益与合作品牌共建
    t0, t1 = win2('c5h')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['lg_canape', 'lg_food'], cy=520, h=480, a=a, cap='百夫长贵宾厅（2018）')
        k = appear(t, 'c5h', '二十多个')
        if k > 0:
            for j in range(20):
                ang = 2 * math.pi * j / 20 + t * 0.15
                kk = eo((t - WT('c5h', '二十多个') - j * 0.04) / 0.3)
                disc(cv, (W / 2 + 230 * math.cos(ang), 1060 + 150 * math.sin(ang)), 16, GOLD_D, a * kk)
            node(cv, W / 2, 1060, '运通会员权益', a * k, col=AX_BLUE, size=34, w=360, sub='和 20 多个合作品牌一起出')
        k2 = appear(t, 'c5h', '对这些品牌')
        if k2 > 0: cv.text('品牌花钱，接触运通那批花得多的客人', W / 2, 1300, 34, 'sans_bold', col=GOLD_L, a=a * k2)
        source(cv, '运通 2025 年报·致股东信（“over 20 leading brands with whom we co-create benefits”）；后半句为本片解读', a, y=1462)
    # c5i：交了年费，就想用回来
    t0, t1 = win2('c5i')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['dl_cabin', 'dl_dusk'], cy=520, h=480, a=a, cap='达美航空（2019）')
        ks = [appear(t, 'c5i', '交了'), appear(t, 'c5i', '订酒店'), appear(t, 'c5i', '刷得越多'), appear(t, 'c5i', '手续费也越多')]
        ring_cycle(cv, t, W / 2, 1110, 200, ['交了年费', '尽量都刷这张卡', '刷得越多', '商户手续费越多'], a, ks, col=GOLD, size=26)
        note(cv, '示意（本片解读）', 1395, a * 0.8, 20)
        source(cv, '本片解读；2025 年平均每张自营基础卡年消费 $25,453（运通 2025 年报）', a, y=1462)
    # c5j：1250 万新卡，七成收年费；白金卡超预期
    t0, t1 = win2('c5j')
    a = A(t, t0, t1)
    if a > 0:
        k = appear(t, 'c5j', '一千二百五十万')
        if k > 0:
            cv.text(counter(0, 1250, t, WT('c5j', '一千二百五十万'), 1.0, lambda v: f'{v:,.0f} 万张'), W / 2, 450, 100, 'sans_bold', gold=True, a=a * k, glow=0.2)
            cv.text('2025 年新发的自营卡', W / 2, 535, 30, 'sans_med', col=CREAM, a=a * k)
        kb = eexp((t - WT('c5j', '七成以上') + 0.1) / 1.2)
        if kb > 0:
            for j in range(10):
                r = j < 7
                x = 145 + j * 88
                card(cv, x, 720, 0.18, a * min(1, kb * 10 - j * 0.6), '', '', col=GOLD if r else BANK_G)
            cv.text('七成以上的新账户：收年费的卡', W / 2, 830, 36, 'sans_bold', col=GOLD_L, a=a * kb)
        qcard(cv, 'qplat', t, WT('c5j', '改版后') - 0.2, t1, cy=1100, en=34, cn=40, a=a, typing=1.0, w=920)
        source(cv, '美国运通 2025 年报·致股东信', a, y=1462)
    # c5k：面子请进门，里子留下来
    t0, t1 = S('c5k') - 0.3, CH['tk_ch5'][0] + 0.3
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['lg_family'], cy=520, h=480, a=a, cap='百夫长贵宾厅（2018）')
        big_q(cv, t, '面子把人请进门', 950, WT('c5k', '面子'), 60, a, col=CREAM)
        big_q(cv, t, '里子把人留下来', 1060, WT('c5k', '里子把人'), 72, a)
        k = appear(t, 'c5k', '年费涨得')
        if k > 0: cv.text('年费涨得越高，里子就得做得越足', W / 2, 1200, 36, 'sans_med', col=GOLD_L, a=a * k)


# ======================================================================== 第六章：要盯住的四件事
RISKS = [('信贷', '衰退：刷卡变少，坏账变多'), ('成本', '积分与服务 +14%，快过营收'), ('集中度', '达美：刷卡额约 13%、卡贷款约 21%'), ('费率', '受理越广、监管与诉讼，费率承压')]


def risk_list(cv, t, a, cur, ks):
    for j, (nm, sub) in enumerate(RISKS):
        k = ks[j]
        if k <= 0: continue
        y = 900 + j * 120; on = j == cur
        cv.rrect(110, y - 46, 970, y + 46, 14, (0.08, 0.07, 0.06) if on else (0.05, 0.05, 0.05), a * k * 0.9)
        cv.rrect(110, y - 46, 970, y + 46, 14, COST_R if on else GREY, a * k * (0.9 if on else 0.4), fill=False, th=2)
        cv.text(f'0{j + 1}', 165, y, 34, 'oswald', col=COST_R if on else GREY, a=a * k)
        cv.text(nm, 270, y, 36, 'sans_bold', col=CREAM if on else GREY, a=a * k, anchor='l')
        cv.text(sub, 950, y, 24, 'sans_light', col=CREAM if on else GREY, a=a * k, anchor='r')


def shot_ch6(cv, t):
    t0, t1 = S('c6a') - 0.3, S('c6f') - 0.2
    a = A(t, t0, t1)
    if a > 0:
        cur = 3 if t >= S('c6e') - 0.2 else 2 if t >= S('c6d') - 0.2 else 1 if t >= S('c6c') - 0.2 else 0 if t >= S('c6b') - 0.2 else -1
        ks = [appear(t, 'c6b', '第一'), appear(t, 'c6c', '第二'), appear(t, 'c6d', '第三'), appear(t, 'c6e', '第四')]
        if t < S('c6b') - 0.2:
            big_q(cv, t, '没有风险的生意？', 430, t0 + 0.3, 60, a, col=CREAM)
            big_q(cv, t, '不是。', 560, WT('c6a', '不是'), 80, a)
            k = appear(t, 'c6a', '四件事')
            if k > 0: cv.text('至少有四件事，要盯住', W / 2, 700, 44, 'sans_bold', col=GOLD_L, a=a * k)
        else:
            # 上方画窗：每件事一段画面
            if cur == 0:
                k = appear(t, 'c6b', '两千一百三十九')
                if k > 0:
                    cv.text(counter(0, 2139, t, WT('c6b', '两千一百三十九'), 1.0, lambda v: f'${v:,.0f} 亿'), W / 2, 480, 110, 'sans_bold', col=COST_R, a=a * k, glow=0.15)
                    cv.text('2025 年底 · 卡贷款和应收账款', W / 2, 580, 30, 'sans_med', col=CREAM, a=a * k)
                cv.text('它不像 Visa 那样完全不放贷', W / 2, 370, 34, 'sans_med', col=GREY, a=a * appear(t, 'c6b', '不像'))
                cv.text('经济衰退 → 刷卡变少 · 坏账变多', W / 2, 700, 34, 'sans_bold', col=GOLD_L, a=a * appear(t, 'c6b', '衰退'))
            elif cur == 1:
                e1 = eexp((t - WT('c6c', '增长了') + 0.1) / 0.9)
                for j, (lb, v, col) in enumerate((('积分与服务', 14.4, COST_R), ('营收', 9.5, GOLD * 0.7))):
                    x = 360 + j * 360; hh = 300 * v / 15 * e1
                    gbar(cv, x - 80, 720 - hh, x + 80, 720, col, a * min(1, e1 * 3), reflect=False)
                    cv.text(f'+{v:.0f}%' if j == 0 else '+10%', x, 720 - hh - 40, 52, 'sans_bold', col=CREAM, a=a * min(1, e1 * 3))
                    cv.text(lb, x, 760, 28, 'sans_med', col=CREAM, a=a * min(1, e1 * 3))
                cv.text('对手也在抢高端客人', W / 2, 340, 38, 'sans_bold', col=GOLD_L, a=a * appear(t, 'c6c', '摩根大通'))
            elif cur == 2:
                seq(cv, t, S('c6d') - 0.3, S('c6e') - 0.2, ['dl_plane'], cy=500, h=440, a=a, cap='达美航空（2019）')
            elif cur == 3:
                qcard(cv, 'qerode', t, S('c6e') - 0.2, t1, cy=520, en=28, cn=34, a=a, typing=1.4, w=960)
            risk_list(cv, t, a, cur, ks)
        src = {0: '运通 2025Q4 附表：Card Member loans and receivables $213,863M',
               1: '运通 2025Q4 附表：积分 + 服务 $24,466M（2024 年 $21,381M，+14%）；营收 +10%',
               2: '运通 2025 Form 10-K Item 1：Delta 联名卡约占全球刷卡额 13%、卡贷款 21%，协议到 2029 年底',
               3: '运通 2025 Form 10-K 风险因素'}.get(cur, '本片过渡')
        source(cv, src, a, y=1462)
    # c6f：三个数
    t0, t1 = S('c6f') - 0.3, CH['tk_ch6'][0] + 0.3
    a = A(t, t0, t1)
    if a > 0:
        cv.text('看运通，盯住三个数', W / 2, 420, 56, 'serif_black', gold=True, a=a * eo((t - t0 - 0.2) / 0.5))
        for j, (s_, sub, tw) in enumerate((('年费收入', '还能不能稳定增长', '年费收入'), ('核销率', '会不会抬头', '核销率'), ('积分与服务的花费', '会不会跑得比收入还快', '积分和服务'))):
            k = appear(t, 'c6f', tw)
            node(cv, W / 2, 620 + j * 200, s_, a * k, col=GOLD, size=40, w=640, sub=sub)
        source(cv, '本片解读', a * 0.6, y=1462)


# ======================================================================== 第七章：三家公司，一个答案
def shot_ch7(cv, t):
    # c7a–c7b：三家公司
    t0, t1 = S('c7a') - 0.3, S('c7c') - 0.2
    a = A(t, t0, t1)
    if a > 0:
        cols = [('喜诗糖果', '顾客愿意多付钱', '品牌定价权', WT('c7a', '喜诗糖果')),
                ('Costco', '把省下的钱让给会员', '规模经济共享', WT('c7a', 'Costco')),
                ('美国运通', '用信任和闭环，把会员费做成生意', '信任 · 闭环 · 会员费', WT('c7a', '美国运通'))]
        cv.text('把最近这三期放在一起', W / 2, 300, 34, 'sans_med', col=GOLD, a=a * eo((t - t0 - 0.2) / 0.5))
        for j, (nm, d1, d2, tw) in enumerate(cols):
            k = eo((t - tw + 0.1) / 0.5)
            if k <= 0: continue
            y = 450 + j * 230
            cv.rrect(110, y - 90, 970, y + 90, 18, (0.07, 0.06, 0.05), a * k * 0.9)
            cv.rrect(110, y - 90, 970, y + 90, 18, GOLD, a * k * 0.5, fill=False, th=2)
            cv.text(f'0{j + 5}', 170, y, 40, 'oswald', col=GOLD_D, a=a * k)
            cv.text(nm, 230, y - 28, 44, 'serif_black', gold=True, a=a * k, anchor='l')
            cv.text(d1, 230, y + 36, 28, 'sans_med', col=CREAM, a=a * k, anchor='l')
        k = appear(t, 'c7b', '同一个特点')
        if k > 0:
            cv.text('顾客一次又一次地回来', W / 2, 1180, 50, 'serif_black', gold=True, a=a * k, glow=0.15)
            cv.text('不用投太多钱，长期赚到很高的回报', W / 2, 1270, 38, 'sans_bold', col=CREAM, a=a * appear(t, 'c7b', '不用投'))
        source(cv, '第五、六、七期结论（本片解读）', a * 0.6, y=1462)
    # c7c：引入原声
    t0, t1 = S('c7c') - 0.3, S('sot_trick') - SEG['sot_trick']['lead'] + 0.2
    a = A(t, t0, t1, 0.4, 0.35)
    if a > 0:
        pic(cv, ['buffett_2010', 'buffett_2015'], t, t0, t1, cy=520, h=480, a=a, cap='沃伦·巴菲特')
        tag(cv, 'CNBC 专访 · 2026-07-15', t, t0 + 0.2, W / 2, 900, 30, GOLD, a)
    # c7d：六十年
    t0, t1 = S('c7d') - 0.3, CH['end'][0] + 0.4
    a = A(t, t0, t1, 0.4, 0.6)
    if a > 0:
        seq(cv, t, t0, t1, ['tc_logo2', 'tc_cheque', 'lg_logo', 'lg_window'], cy=520, h=480, a=a, cap='1960 年代广告 / 2018 年百夫长贵宾厅')
        y = 1060; xa, xb = 200, 880
        k = eexp((t - WT('c7d', '一九六四') + 0.1) / 2.0)
        cv.line((xa, y), (xa + (xb - xa) * k, y), GOLD, a, 4)
        for x, yr, lb, kk in ((xa, '1964', '合伙基金重仓', min(1, k * 4)), (xb, '今天', '伯克希尔持有 22.1%', appear(t, 'c7d', '今天'))):
            if kk <= 0: continue
            cv.glow_dot((x, y), 12, GOLD_L, a * kk)
            cv.text(yr, x, y - 60, 52 if yr.isdigit() else 46, 'oswald' if yr.isdigit() else 'sans_bold', col=GOLD_L, a=a * kk)
            cv.text(lb, x, y + 56, 28, 'sans_med', col=CREAM, a=a * kk)
        k2 = appear(t, 'c7d', '六十年')
        if k2 > 0 and t < CH['end'][0]:      # 落版字在片尾开始时交给 common.shot_end（同一位置），随后化作粒子
            cv.text('六十年，看的是同一件事', W / 2, 1260, 50, 'serif_black', gold=True, a=k2, glow=0.15)
        source(cv, '伯克希尔 1994 年信；伯克希尔 2025 年信持仓表', a, y=1462)
