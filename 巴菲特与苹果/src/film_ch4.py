"""第四章 · 他为什么卖（价格 → 税 → 现金 → 集中度 → 仍是最大投资 → 卖错了吗：账面差额、事后才知道的两件事）"""
from common import *  # noqa
import media as M

PE = [(2016.83, 13.6), (2018.12, 18.7), (2024.37, 30.4), (2026.84, 37.7)]   # 季度均价 ÷ 上一财年摊薄 EPS（data/calc.py）


def shot_ch4(cv, t):
    # ---- c4a：为什么卖？2024 年股东大会
    t0, t1 = win('c4a')
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        M.full(cv, 'x_bwb_meeting', t, t0, t1, z0=1.0, z1=1.08, focus=(0.5, 0.45), dark=0.4, a=a, src_t0=18.0, speed=0.9, cap='伯克希尔股东大会现场')
        headline(cv, '为什么卖？', 1190, a, 100, k=eo((t - t0 - 0.2) / 0.5))
    # ---- c4b：第一，价格：14 倍 → 30 倍
    t0, t1 = win('c4b')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        cv.text('第一 · 价格', 140, 380, 56, 'serif_black', gold=True, a=a, anchor='l')
        x0, x1, y0, y1 = 160, 960, 560, 1150
        pts = [(ax_x(y, x0, x1), y1 - v / 40 * (y1 - y0)) for y, v in PE]
        for yy in (10, 20, 30, 40):
            Y = y1 - yy / 40 * (y1 - y0)
            cv.line((x0, Y), (x1, Y), (0.2, 0.2, 0.22), a * 0.5, 1)
            cv.text(f'{yy}倍', x0 - 12, Y, 20, 'sans_light', col=DIM, a=a, anchor='r')
        for yr in range(2016, 2027, 2): cv.text(str(yr), ax_x(yr + 0.5, x0, x1), y1 + 30, 20, 'oswald', col=DIM, a=a)
        k1 = eo((t - WT('c4b', '十四倍') + 0.1) / 0.4)
        cv.glow_dot(pts[0], 14, GOLD, a * k1)
        cv.text('买入时 ≈ 14 倍', pts[0][0] + 20, pts[0][1] + 50, 34, 'sans_bold', col=GOLD_L, a=a * k1, anchor='l')
        k2 = eio((t - WT('c4b', '三十倍') + 0.9) / 1.0)
        if k2 > 0:
            q = (lerp(pts[0][0], pts[2][0], k2), lerp(pts[0][1], pts[2][1], k2))
            cv.line(pts[0], q, RED, a, 4)
            if k2 >= 1:
                cv.glow_dot(pts[2], 14, RED, a)
                cv.text('大举卖出时 ≈ 30 倍', pts[2][0] - 20, pts[2][1] - 50, 34, 'sans_bold', col=RED, a=a, anchor='r')
        k3 = eo((t - WT('c4b', '同样一块钱') + 0.1) / 0.5)
        cv.text('同样一块钱的利润，出价高了一倍多', W / 2, 1290, 44, 'serif_semi', col=CREAM, a=a * k3)
        source(cv, '季度日均价 ÷ 上一财年摊薄每股收益：2016Q4 13.6 倍、2024Q2 30.4 倍（data/calc.py）', a, y=1462)
    # ---- c4c：第二，税：21% / 35% / 52%
    t0, t1 = win('c4c')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('第二 · 税', 140, 380, 56, 'serif_black', gold=True, a=a, anchor='l', shadow=0.8)
        bars(cv, [('过去最高', 52, GREY * 0.7, WT('c4c', '百分之五十二') - 0.2), ('不久前', 35, GREY * 0.85, WT('c4c', '百分之三十五') - 0.2),
                  ('现在', 21, GOLD, WT('c4c', '百分之二十一') - 0.2)], t, t0, a, x0=160, x1=920, base=1230, hmax=560,
             fmt=lambda v: f'{v:.0f}%', label_size=30)
        cv.text('美国联邦企业所得税率', W / 2, 480, 32, 'sans_light', col=CREAM, a=a, shadow=0.8)
        source(cv, '巴菲特 2024 年股东大会：“we are paying a 21% federal rate on the gains we’re taking in Apple”', a, y=1462)
    # ---- c4d：未来税率可能上调
    t0, t1 = win('c4d')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        cv.text('21%', 300, 860, 120, 'sans_bold', col=GOLD, a=a)
        k = eio((t - WT('c4d', '上调') + 0.5) / 0.8)
        cv.line((440, 860), (440 + 240 * k, 860 - 120 * k), RED, a, 5)
        cv.text('？%', 800, 720, 120, 'sans_bold', col=RED, a=a * eo((t - WT('c4d', '上调') + 0.1) / 0.5))
        k2 = eo((t - WT('c4d', '言下之意') + 0.1) / 0.5)
        cv.text('与其将来按更高的税率缴，', W / 2, 1080, 46, 'serif_semi', col=CREAM, a=a * k2)
        cv.text('不如趁现在先卖一部分', W / 2, 1160, 52, 'serif_black', gold=True, a=a * eo((t - WT('c4d', '不如') + 0.1) / 0.5), glow=0.2)
        cv.text('（本片解读）', W / 2, 1240, 26, 'sans_light', col=GREY, a=a * k2)
    # ---- c4e：第三，现金；段永平当年的问题
    t0, t1 = win('c4e')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('第三 · 现金', 140, 380, 56, 'serif_black', gold=True, a=a, anchor='l', shadow=0.8)
        quote_card(cv, 'q2024b', t, t0 + 0.2, WT('c4e', '当年') + 0.2, cy=800, en_size=34, cn_size=40, a=a)
        k = env(t, WT('c4e', '当年') - 0.1, t1, 0.5, 0.3)
        if k > 0:
            cv.text('2006 年段永平想问的问题', W / 2, 720, 34, 'sans_light', col=GREY, a=a * k, shadow=0.8)
            cv.text('钱太多，好机会太少', W / 2, 840, 76, 'serif_black', gold=True, a=a * k, glow=0.25, shadow=0.8)
            cv.text('如今摆在了巴菲特自己面前', W / 2, 960, 40, 'sans_med', col=CREAM, a=a * eo((t - WT('c4e', '如今') + 0.1) / 0.5), shadow=0.8)
    # ---- c4f：没有明说的集中度
    t0, t1 = win('c4f')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('还有一点 · 集中度', 140, 380, 56, 'serif_black', col=CREAM, a=a, anchor='l')
        k = eio((t - WT('c4f', '一只股票') + 0.3) / 1.2)
        cv.arc((W / 2, 820), 260, -math.pi / 2, 3 * math.pi / 2, (0.2, 0.2, 0.22), a, 40)
        cv.arc((W / 2, 820), 260, -math.pi / 2, -math.pi / 2 + 2 * math.pi * 0.49 * k, RED, a, 40)
        cv.text('近一半', W / 2, 820, 80, 'serif_black', col=CREAM, a=a * k)
        k2 = eo((t - WT('c4f', '风险') + 0.1) / 0.5)
        cv.text('再好的生意，这样的集中度也是风险', W / 2, 1200, 40, 'serif_semi', col=GOLD_L, a=a * k2)
        cv.text('（本片解读，非巴菲特原话）', W / 2, 1270, 26, 'sans_light', col=GREY, a=a * k2)
    # ---- c4g：苹果仍会是我们最大的投资
    t0, t1 = win('c4g')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        M.full(cv, 'x_park_ring4', t, t0, t1, z0=1.0, z1=1.06, dark=0.45, a=a, speed=0.55, cap='Apple Park 航拍')
        quote_card(cv, 'q2024c', t, t0 + 0.1, t1, cy=1020, en_size=36, cn_size=42, a=a)
        k = eo((t - WT('c4g', '二零二五年底') + 0.1) / 0.5)
        if k > 0:
            cv.rrect(160, 1200, 920, 1360, 16, (0.05, 0.05, 0.06), a * k * 0.9)
            cv.text('2025 年底 · 伯克希尔第一大持仓', W / 2, 1250, 34, 'sans_med', col=CREAM, a=a * k)
            cv.text('苹果 $620亿', W / 2, 1315, 46, 'sans_bold', gold=True, a=a * k)
        source(cv, '2024 年股东大会；伯克希尔 2025 年致股东信持仓表（苹果市值 $61,962M）', a, y=1462)
    # ---- c4h–c4i：卖错了吗？卖出均价约 195 vs 今天 338；账面差额约 1000 亿（税前）
    t0, t1 = S('c4h') - 0.3, S('c4j') + 0.1
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        x0, x1, y0, y1 = 130, 990, 560, 1150
        r = aapl_chart(cv, t, x0, x1, y0, y1, y_from=2023.5, y_to=2026.9, reveal=eio(p / 2.0), a=a, lo=120, hi=400,
                       ticks=(150, 200, 300, 400), col=CREAM)
        k = eo((t - WT('c4h', '一百九十五') + 0.1) / 0.5)
        yy = ax_y(195.10, y0, y1, 120, 400)
        cv.line((ax_x(2023.75, x0, x1, 2023.5, 2026.9), yy), (ax_x(2025.99, x0, x1, 2023.5, 2026.9), yy), GOLD, a * k, 3)
        cv.text('卖出均价 ≈ $195', ax_x(2025.99, x0, x1, 2023.5, 2026.9) + 14, yy, 30, 'sans_bold', col=GOLD, a=a * k, anchor='l')
        k2 = eo((t - WT('c4h', '三百三十八') + 0.1) / 0.5)
        yn = ax_y(CLOSE, y0, y1, 120, 400)
        cv.text('今天 $338', x1, yn - 44, 34, 'sans_bold', col=CREAM, a=a * k2, anchor='r')
        k3 = eo((t - WT('c4i', '一千亿') + 0.2) / 0.6)
        if k3 > 0:
            cv.rect(x1 - 30, yn, x1 - 10, yy, RED, a * k3 * 0.8)
            cv.text('≈ $1000亿', W / 2, 1290, 90, 'serif_black', col=RED, a=a * k3, glow=0.2)
            cv.text('6.88 亿股 × ($338.32 − $195.10)，税前、未计卖出后现金的利息', W / 2, 1380, 26, 'sans_light', col=GREY, a=a * k3)
        cv.text('AAPL · 2023 年秋 → 今天', 130, 450, 30, 'sans_med', col=GREY, a=a, anchor='l')
    # ---- c4j：卖出后，每股收益 +46%，估值 30 → 38 倍；当时谁也无法确知
    t0, t1 = win('c4j')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('卖出之后的两年多', W / 2, 420, 40, 'sans_med', col=CREAM, a=a)
        k1 = eo((t - WT('c4j', '每股收益') + 0.1) / 0.5)
        cv.text('每股收益', 300, 700, 40, 'sans_light', col=GREY, a=a * k1)
        cv.text('+46%', 300, 820, 110, 'sans_bold', gold=True, a=a * k1, glow=0.25)
        cv.text('$6.13 → $8.98', 300, 930, 28, 'sans_light', col=GREY, a=a * k1)
        k2 = eo((t - WT('c4j', '估值') + 0.1) / 0.5)
        cv.text('市盈率', 780, 700, 40, 'sans_light', col=GREY, a=a * k2)
        cv.text('30→38', 780, 820, 100, 'sans_bold', gold=True, a=a * k2, glow=0.25)
        cv.text('2024Q2 → 今天', 780, 930, 28, 'sans_light', col=GREY, a=a * k2)
        k3 = eo((t - WT('c4j', '谁也无法确知') + 0.1) / 0.5)
        cv.text('在卖出的那一刻，谁也无法确知', W / 2, 1180, 50, 'serif_semi', col=CREAM, a=a * k3)
        source(cv, '苹果 10-K：2023 财年 vs 2026 财年摊薄每股收益；data/calc.py', a, y=1462)
    # ---- c4k：卖掉的是判断，不是否定
    t0 = S('c4k') - 0.3; t1 = CH['ch5'][0] + 0.2
    a = env(t, t0, t1, 0.5, 0.5)
    if a > 0:
        M.full(cv, 'x_bwb_walk', t, t0, t1, z0=1.0, z1=1.06, focus=(0.55, 0.45), dark=0.5, a=a, speed=0.4)
        k = eo((t - WT('c4k', '对价格') + 0.1) / 0.6)
        cv.text('卖掉的，是判断', W / 2, 1160, 72, 'serif_black', gold=True, a=a * k, glow=0.25, shadow=0.8)
        cv.text('不是对生意的否定', W / 2, 1275, 60, 'serif_black', col=CREAM, a=a * eo((t - WT('c4k', '而不是') + 0.1) / 0.6), shadow=0.8)
