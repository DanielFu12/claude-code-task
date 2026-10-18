"""第一章 · 迟到52年的买入（1936 → 1989）"""
from common import *  # noqa


def shot_ch1(cv, t):
    # ---- s07：1936 年的美国小店（沃克·埃文斯 1936 摄；与巴菲特家杂货店无关，仅作时代示意）
    t0, t1 = S('s07') - 0.3, S('s08') + 0.05
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        p = t - t0
        photo(cv, 'evans_sandwich_shop_1936', t, t0, t1, W / 2, 760, 1000, 720, z0=1.0, z1=1.22, fi=0.5, fo=0.4,
              pan=(0.06, 0.05, -0.04, 0.12), mode='sepia',
              caption='1936.2 · 路易斯安那州的路边小店 · 沃克·埃文斯 摄（美国国会图书馆 FSA，公有领域）· 时代示意')
        cv.text('1936', 110, 240, 110, 'oswald', col=GOLD, a=a * eo(p / 0.8), anchor='l', glow=0.2)
        cv.text('奥马哈 · 巴菲特家的杂货店', 112, 320, 30, 'sans_light', col=CREAM, a=a * eo((p - 0.3) / 0.8), anchor='l')
        k = eo((p - 3.0) / 0.6)
        if k > 0:
            y = 1255
            cv.rrect(90, y - 62, 990, y + 88, 16, (0.05, 0.04, 0.03), a * k * 0.85)
            cv.text('6 瓶 = 25¢', 300, y - 8, 52, 'sans_bold', col=CREAM, a=a * k)
            k2 = eo((p - 4.2) / 0.5)
            cv.text('→', 540, y - 8, 52, 'sans_light', col=GOLD, a=a * k2)
            cv.text('6 × 5¢ = 30¢', 770, y - 8, 52, 'sans_bold', gold=True, a=a * k2)
            cv.text('每卖 6 瓶，赚 5 美分 —— 一次“高毛利零售”的初体验', W / 2, y + 52, 26, 'sans_light', col=GREY, a=a * k2)
        source(cv, '出处：巴菲特 1989 年致股东信', a)
    # ---- s08：52 年里他买了什么
    t0, t1 = S('s08') - 0.3, S('s09') + 0.1
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        photo(cv, 'evans_coke_shack_1935', t, t0, t1, W / 2, 900, 1080, 1100, z0=1.15, z1=1.3, mode='sepia', a=0.13,
              fi=0.4, fo=0.4, frame=False)
        cv.text('背景：可口可乐小屋，阿拉巴马 1935 · 沃克·埃文斯（公有领域）', W / 2, 1300, 20, 'sans_light', col=DIM, a=a)
        yr = int(lerp(1936, 1988, eio(p / 4.0)))
        cv.text(str(yr), W / 2, 470, 200, 'oswald', col=CREAM, a=a, glow=0.1)
        L = 820 * eio(p / 4.0)
        cv.line((130, 600), (130 + L, 600), GOLD, a, 3)
        cv.text('1936', 130, 640, 24, 'oswald', col=GREY, a=a, anchor='l')
        cv.text('1988', 950, 640, 24, 'oswald', col=GREY, a=a * eo((p - 3.5) / 0.5), anchor='r')
        items = ['电车公司', '风车制造商', '无烟煤矿', '纺织厂', '印花票公司']
        for i, s in enumerate(items):
            k = env(p, 0.4 + i * 0.55, 99, 0.35, 0)
            x = 200 + (i % 3) * 340 if i < 3 else 370 + (i - 3) * 340
            y = 760 + (i // 3) * 110
            chip(cv, s, x, y, 34, a * k * (1 - 0.55 * eo((p - 3.3) / 0.6)), col=CREAM)
        k = eo((p - 3.3) / 0.6)
        cv.text('可口可乐：0 股', W / 2, 1060, 70, 'serif_black', col=RED, a=a * k, glow=0.25)
        cv.text('“如果你觉得我在编故事，我可以把公司名字都列出来。”—— 1989年致股东信', W / 2, 1160, 24,
                'sans_light', col=GREY, a=a * k)
    # ---- s09：原文卡
    quote_card(cv, 'q1989', t, S('s09') - 0.4, S('s10') + 0.1, cy=800)
    # ---- s10：郭思达时代：海外销量爆发
    t0, t1 = S('s10') - 0.3, S('s11') + 0.1
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        p = t - t0
        globe(cv, t, W / 2, 760, 400, rot=1.05 + p * 0.12, a=a, arcs=eio((p - 0.8) / 4.5))
        cv.text('1981', 110, 260, 90, 'oswald', col=GOLD, a=a, anchor='l')
        cv.text('郭思达（Roberto Goizueta）出任 CEO', 112, 340, 32, 'sans_med', col=CREAM, a=a * eo((p - 0.3) / 0.6), anchor='l')
        cv.text('与唐·基奥（Don Keough）搭档，重新聚焦主业', 112, 390, 28, 'sans_light', col=GREY, a=a * eo((p - 0.6) / 0.6), anchor='l')
        k = eo((p - 2.5) / 0.6)
        cv.text('海外销量 · 几乎爆炸式增长', W / 2, 1250, 44, 'serif_black', gold=True, a=a * k)
        source(cv, '出处：巴菲特 1989 年致股东信', a)
    # ---- s11：高回报 vs 低估值
    t0, t1 = S('s11') - 0.3, S('s12') + 0.1
    a = env(t, t0, t1, 0.45, 0.4)
    if a > 0:
        p = t - t0
        cv.text('1988 年的可口可乐', W / 2, 330, 40, 'sans_med', col=CREAM, a=a)
        for i, (cx, val, mx, lab, sub, colr, fm) in enumerate([
                (300, 34.7, 50, '净资产收益率', 'ROE', GOLD, lambda v: f'{v:.1f}%'),
                (780, 15.1, 50, '市盈率', 'P/E', RED, lambda v: f'{v:.0f}倍')]):
            k = eexp((p - 0.4 - i * 1.2) / 1.6)
            R = 190
            cv.arc((cx, 720), R, -math.pi / 2, 3 * math.pi / 2, (0.25, 0.22, 0.2), a, 14)
            cv.arc((cx, 720), R, -math.pi / 2, -math.pi / 2 + 2 * math.pi * val / mx * k, colr, a, 14)
            cv.text(fm(val * k), cx, 715, 76, 'sans_light', col=WHITE, a=a * eo((p - 0.4 - i * 1.2) / 0.4))
            cv.text(lab, cx, 970, 38, 'sans_med', col=colr, a=a)
            cv.text(sub, cx, 1020, 24, 'corm', col=GREY, a=a, track=0.2)
        k = eo((p - 3.2) / 0.5)
        cv.text('一流的生意 · 合理的价格', W / 2, 1170, 52, 'serif_black', gold=True, a=a * k)
        source(cv, '数据：可口可乐 1993/1998 年 10-K 财务摘要（1988 年末股价 ÷ 持续经营每股收益）', a)
    # ---- s12：重仓
    t0, t1 = S('s12') - 0.3, CH['ch2'][0] + 0.05
    a = env(t, t0, t1, 0.45, 0.4)
    if a > 0:
        p = t - t0
        x0, x1, y = 120, 960, 760
        k = eo(p / 0.8)
        cv.text('伯克希尔 1988 年末净资产  $34亿', x0, y - 110, 32, 'sans_light', col=CREAM, a=a * k, anchor='l')
        cv.rrect(x0, y - 50, x0 + (x1 - x0) * k, y + 50, 10, (0.22, 0.2, 0.2), a)
        k2 = eexp((p - 1.0) / 1.4)
        cv.rrect(x0, y - 50, x0 + (x1 - x0) * 0.301 * k2, y + 50, 10, RED, a, glow=0.3)
        cv.text(f'可口可乐 ${10.2 * k2:.1f}亿', x0 + 10, y + 110, 40, 'sans_med', col=RED, a=a * k2, anchor='l')
        cv.text(f'{30 * k2:.0f}%', x0 + (x1 - x0) * 0.301 * k2 + 20, y, 56, 'sans_bold', col=WHITE, a=a * k2, anchor='l')
        k3 = eo((p - 2.6) / 0.5)
        cv.text('重仓', W / 2, 1080, 150, 'serif_black', gold=True, a=a * k3, glow=0.3, scale=1.1 - 0.1 * k3)
        cv.text('1988 年 1,417 万股 · 1989 年末 2,335 万股（当时股数）', W / 2, 1220, 28, 'sans_light', col=GREY, a=a * k3)
        source(cv, '数据：伯克希尔 1988、1989 年报持仓表；1991 年致股东信', a)
