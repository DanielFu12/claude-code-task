"""第一章 · 看懂一部手机（能力圈 → 段永平 → 首次买入 → 身边的小事 → 大行动 → 2018 → 换上 iPhone）"""
from common import *  # noqa
import media as M


def shot_ch1(cv, t):
    # ---- c1a：能力圈
    t0, t1 = win('c1a')
    a = env(t, t0, t1, 0.6, 0.4)
    if a > 0:
        p = t - t0
        M.full(cv, 'x_bwb_desk', t, t0, t1, z0=1.0, z1=1.08, focus=(0.55, 0.45), dark=0.35, a=a, speed=0.8, cap='巴菲特在奥马哈的办公室')
        R = 200 * eo((p - 0.8) / 1.2)
        if R > 1:
            cv.circle((W / 2, 1210), R, GOLD, a * 0.9, 3)
            for k, (s, ang) in enumerate([('保险', -2.4), ('铁路', -0.5), ('消费品', 1.6)]):
                kk = eo((p - 1.6 - k * 0.25) / 0.5)
                cv.text(s, W / 2 + 105 * math.cos(ang), 1210 + 95 * math.sin(ang), 36, 'sans_med', col=CREAM, a=a * kk, shadow=0.8)
            kk = eo((p - 2.6) / 0.6)
            cv.text('科技股', W / 2 + 330, 1110, 40, 'sans_med', col=GREY, a=a * kk * 0.85, shadow=0.8)
            cv.text('×', W / 2 + 330, 1180, 60, 'sans_light', col=RED, a=a * kk, shadow=0.8)
        headline(cv, '能力圈', 925, a, 90, k=eo((t - WT('c1a', '能力圈') + 0.1) / 0.5))
        cv.text('CIRCLE OF COMPETENCE', W / 2, 990, 24, 'corm', col=GOLD, a=a * eo((t - WT('c1a', '能力圈')) / 0.6), track=0.3, shadow=0.8)
    # ---- c1b：少有的例外：IBM（2011 → 2018）
    t0, t1 = win('c1b')
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        p = t - t0
        M.frame(cv, 'ibm_chq', t, t0, t1, cy=560, w=1000, h=562, a=a, cap='IBM 总部 · 纽约州阿蒙克')
        x0, x1, y = 160, 920, 1230
        L = (x1 - x0) * eio((t - WT('c1b', '二零一一')) / 1.0)
        cv.line((x0, y), (x0 + L, y), GOLD_D, a, 3)
        cv.glow_dot((x0, y), 10, GOLD, a * eo((t - WT('c1b', '二零一一')) / 0.4))
        cv.text('2011', x0, y - 50, 40, 'oswald', col=GOLD, a=a * eo((t - WT('c1b', '二零一一')) / 0.4))
        cv.text('买入 IBM · 逾 $100亿', x0, y + 50, 26, 'sans_light', col=CREAM, a=a * eo((t - WT('c1b', '一百多亿')) / 0.4), anchor='l')
        k = eo((t - WT('c1b', '二零一八')) / 0.4)
        cv.glow_dot((x1, y), 10, RED, a * k)
        cv.text('2018', x1, y - 50, 40, 'oswald', col=RED, a=a * k)
        cv.text('清仓', x1, y + 50, 26, 'sans_light', col=CREAM, a=a * k, anchor='r')
        source(cv, '伯克希尔 2011 年起买入 IBM；巴菲特 2018 年 5 月称已全部卖出（Bloomberg）', a, y=1462)
    # ---- c1c：他自己用的，一直是翻盖机
    t0, t1 = win('c1c')
    a = env(t, t0, t1, 0.4, 0.5)
    if a > 0:
        p = t - t0
        op = eo((p - 0.3) / 0.8)                              # 一部翻盖手机：线稿动画，屏幕亮起
        cx, cy = W / 2, 760
        cv.rrect(cx - 110, cy - 250, cx + 110, cy - 10, 26, (0.12, 0.12, 0.14), a * 0.95)
        cv.rrect(cx - 110, cy - 250, cx + 110, cy - 10, 26, GREY, a * 0.8, fill=False, th=3)
        cv.rrect(cx - 80, cy - 220, cx + 80, cy - 70, 10, (0.25, 0.45, 0.6), a * op)
        cv.text('12:00', cx, cy - 150, 34, 'oswald', col=WHITE, a=a * op)
        cv.rrect(cx - 110, cy + 10, cx + 110, cy + 250, 26, (0.12, 0.12, 0.14), a * 0.95)
        cv.rrect(cx - 110, cy + 10, cx + 110, cy + 250, 26, GREY, a * 0.8, fill=False, th=3)
        for r_ in range(4):
            for c_ in range(3):
                cv.rrect(cx - 75 + c_ * 55, cy + 50 + r_ * 45, cx - 35 + c_ * 55, cy + 80 + r_ * 45, 6, GREY, a * 0.5)
        cv.text('巴菲特的手机', W / 2, 1120, 52, 'serif_black', col=CREAM, a=a * eo((p - 0.6) / 0.6), shadow=0.6)
        cv.text('一部老式翻盖机，用了很多年', W / 2, 1200, 32, 'sans_light', col=GREY, a=a * eo((p - 0.9) / 0.6))
    # ---- c1d：而另一个人……
    t0, t1 = win('c1d', pre=0.2)
    a = env(t, t0, t1, 0.4, 0.5)
    if a > 0:
        p = t - t0                                           # 时间轴：2011 段永平买入 → 2016 巴菲特买入，早了 5 年
        x0, x1, y = 170, 910, 640
        L = (x1 - x0) * eio(p / 1.2)
        cv.line((x0, y), (x0 + L, y), GREY, a * 0.8, 3)
        for yr in range(2011, 2017):
            xx = x0 + (yr - 2011) / 5 * (x1 - x0)
            if xx <= x0 + L + 1: cv.text(str(yr), xx, y + 44, 24, 'oswald', col=DIM, a=a)
        kd = eo((p - 0.4) / 0.5)
        cv.glow_dot((x0, y), 16, GOLD, a * kd)
        cv.text('段永平开始买入', x0, y - 60, 32, 'sans_med', col=GOLD_L, a=a * kd)
        kb = eo((p - 1.1) / 0.5)
        cv.glow_dot((x1, y), 16, CREAM, a * kb)
        cv.text('巴菲特首次买入', x1, y - 60, 32, 'sans_med', col=CREAM, a=a * kb)
        ke = eo((p - 1.6) / 0.5)
        if ke > 0:
            cv.line((x0, y + 90), (x1, y + 90), GOLD_D, a * ke, 2)
            cv.text('早了 5 年', W / 2, y + 130, 40, 'serif_black', gold=True, a=a * ke, glow=0.2)
        headline(cv, '另一个人', 1060, a, 100, k=eo((t - WT('c1d', '另一个人') + 0.1) / 0.6))
        cv.text('比巴菲特更早看懂了苹果', W / 2, 1170, 40, 'sans_med', col=CREAM, a=a * eo((t - WT('c1d', '另一个人') - 0.4) / 0.6))
    # ---- c1e：2006 年慈善午餐拍卖
    t0, t1 = win('c1e')
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        p = t - t0
        cv.text('2006 · eBay 慈善拍卖 · 与巴菲特共进午餐', W / 2, 560, 34, 'sans_med', col=CREAM, a=a)
        k = eo((t - WT('c1e', '六十二万') + 0.1) / 0.5)
        cv.text('$620,100', W / 2, 720, 130, 'sans_bold', gold=True, a=a * k, glow=0.3)
        k2 = eo((t - WT('c1e', '只比') + 0.1) / 0.5)
        cv.text('第二名  $620,000', W / 2, 850, 34, 'sans_light', col=GREY, a=a * k2)
        cv.text('+$100', W / 2 + 270, 850, 34, 'sans_bold', col=GOLD, a=a * k2)
        k3 = eo((t - WT('c1e', '快即是慢') + 0.1) / 0.5)
        if k3 > 0:
            chip(cv, '竞拍账户：fastisslow', W / 2, 990, 30, a * k3, col=GOLD)
            cv.text('快即是慢', W / 2, 1110, 64, 'serif_black', gold=True, a=a * k3, glow=0.2)
    # ---- c1f：段永平，步步高创始人；“想当面谢谢巴菲特”
    t0, t1 = win('c1f')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        k = eo((t - WT('c1f', '段永平') + 0.1) / 0.6)
        cv.text('段永平', W / 2, 520, 120, 'serif_black', gold=True, a=a * k, glow=0.25, shadow=0.8)
        cv.text('步步高创始人', W / 2, 640, 40, 'sans_med', col=CREAM, a=a * eo((t - WT('c1f', '步步高') + 0.1) / 0.5), shadow=0.8)
        quote_card(cv, 'qduan2006a', t, WT('c1f', '学到') - 0.3, t1, cy=1000, a=a * 1.0, en_size=34, cn_size=38)
    # ---- c1g：他还准备了一个问题
    t0, t1 = win('c1g')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('段永平准备的问题', W / 2, 640, 34, 'sans_light', col=GREY, a=a, shadow=0.8)
        k = eo((t - WT('c1g', '钱太多') + 0.1) / 0.6)
        cv.text('钱太多，', W / 2, 820, 72, 'serif_black', col=CREAM, a=a * k, shadow=0.8)
        cv.text('又找不到好的投资对象，', W / 2, 920, 56, 'serif_semi', col=CREAM, a=a * eo((t - WT('c1g', '又找不到') + 0.1) / 0.6), shadow=0.8)
        cv.text('该怎么办？', W / 2, 1030, 72, 'serif_black', gold=True, a=a * eo((t - WT('c1g', '该怎么办') + 0.1) / 0.5), glow=0.25, shadow=0.8)
        source(cv, '美联社 2006-06-23 报道', a, y=1462)
    # ---- c1h：2011 年初，段永平开始买入苹果
    t0, t1 = win('c1h')
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        k = eo((t - WT('c1h', '二零一一') + 0.1) / 0.5)
        cv.text('2011 年 1 月 · 段永平', W / 2, 330, 46, 'serif_black', gold=True, a=a * k, shadow=0.8)
        quote_card(cv, 'qduan2024', t, t0 + 0.2, t1, cy=560, cn_size=40, a=a)
        cv.text('他当年写下的理由', W / 2, 840, 30, 'sans_light', col=GREY, a=a * eo((t - WT('c1h', '用户体验') + 0.4) / 0.5))
        rs = [('用户体验', '用户体验，做到极致'), ('护城河', '平台与生意模式，形成护城河'), (None, '还处在成长的早期，空间很大')]
        tl_ = WT('c1h', '护城河')
        for j, (w_, s_) in enumerate(rs):
            tj = WT('c1h', w_) if w_ else tl_ + 0.9
            kk = eo((t - tj + 0.1) / 0.5)
            y = 930 + j * 100
            cv.text(f'0{j + 1}', 150, y, 40, 'oswald', col=GOLD, a=a * kk)
            cv.text(s_, 210, y, 44, 'serif_semi', col=CREAM if j != 1 else GOLD_L, a=a * kk, anchor='l', shadow=0.6)
        source(cv, '段永平网络问答（2011-01-22、2024-09-12），收录于《大道：段永平投资问答录》', a, y=1462)
    # ---- c1i：苹果成了他组合里最重的股票（H&H 13F 占比）
    t0, t1 = win('c1i')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        cv.text('段永平基金（H&H）组合中苹果的占比', W / 2, 420, 34, 'sans_med', col=CREAM, a=a)
        data = [('2018', 50.9), ('2019', 48.5), ('2020', 53.1), ('2021', 65.9), ('2022', 73.4), ('2023', 79.5), ('2024.6', 81.0)]
        bars(cv, [(y, v, GOLD * 0.75, t0 + 0.3 + k * 0.18) for k, (y, v) in enumerate(data)], t, t0, a,
             fmt=lambda v: f'{v:.0f}%', dur=0.8, label_size=24)
        source(cv, 'SEC 13F（H&H International，外界普遍认为由段永平管理）；占比 = 苹果市值 ÷ 申报总市值', a, y=1462)
    # ---- c1j：2016 年一季度，伯克希尔首次买入
    t0, t1 = win('c1j')
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        M.full(cv, 'x_bwb_office', t, t0, t1, z0=1.0, z1=1.08, focus=(0.6, 0.45), dark=0.45, a=a, src_t0=2.0, speed=0.45, cap='伯克希尔总部 · 奥马哈')
        k = eo((t - WT('c1j', '二零一六') + 0.1) / 0.5)
        cv.text('2016 Q1', W / 2, 925, 84, 'oswald', col=GOLD, a=a * k, shadow=0.8, glow=0.15)
        cv.text('首次买入苹果 · 约 $10亿', W / 2, 1020, 42, 'sans_med', col=CREAM, a=a * eo((t - WT('c1j', '投入') + 0.1) / 0.5), shadow=0.8)
        k2 = eo((t - WT('c1j', '投资经理之一') + 0.1) / 0.6)
        if k2 > 0:
            for j, nm in enumerate(['托德·库姆斯', '特德·韦施勒']):
                cv.text(nm, W / 2 + (j * 2 - 1) * 230, 1130, 46, 'serif_semi', col=CREAM, a=a * k2, shadow=0.8)
            cv.text('？', W / 2, 1130, 60, 'serif_black', col=GOLD, a=a * k2, shadow=0.8)
            cv.text('Todd Combs  ·  Ted Weschler', W / 2, 1200, 26, 'corm', col=GOLD, a=a * k2, track=0.1, shadow=0.8)
        source(cv, '13F 2016Q1：980 万股（拆股前）；CNBC 2017-08-30：巴菲特确认由两位投资经理之一买入、未透露是谁', a, y=1462)
    # ---- c1o：当时的苹果被市场看淡
    t0, t1 = win('c1o')
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        cv.text('苹果 2016 财年', W / 2, 400, 40, 'sans_med', col=CREAM, a=a, shadow=0.8)
        bars(cv, [('FY15 销量', 231.2, GOLD * 0.6, WT('c1o', 'iPhone') - 0.2), ('FY16 销量', 211.9, RED, WT('c1o', '第一次') - 0.2)],
             t, t0, a, x0=140, x1=540, base=1150, hmax=520, fmt=lambda v: f'{v:.0f}M', label_size=22)
        bars(cv, [('FY15 营收', 233.7, GOLD * 0.6, WT('c1o', '全年营收') - 0.2), ('FY16 营收', 215.6, RED, WT('c1o', '首次下降') - 0.2)],
             t, t0, a, x0=560, x1=960, base=1150, hmax=520, fmt=lambda v: f'${v:.0f}B', label_size=22)
        source(cv, '苹果 2016 财年 10-K：iPhone 销量 2.119 亿部（上年 2.312 亿部）；营收 $2156亿（上年 $2337亿）', a, y=1462)
    # ---- c1k：那年年底巴菲特亲自出手；市盈率约 14 倍
    t0, t1 = win('c1k')
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        p = t - t0
        r = aapl_chart(cv, t, 130, 990, 560, 1150, y_from=2015.0, y_to=2018.9, reveal=eio(p / 2.0), a=a, lo=20, hi=60,
                       ticks=(20, 30, 40, 50), col=CREAM)
        cv.text('AAPL 2015–2018', 130, 450, 30, 'oswald', col=GREY, a=a, anchor='l')
        xq = ax_x(2016.83, 130, 990, 2015.0, 2018.9)
        k = eo((t - WT('c1k', '大举买入') + 0.1) / 0.5)
        cv.rect(xq - 4, 560, xq + 4, 1150, GOLD, a * k * 0.6)
        cv.text('巴菲特开始大举买入', xq + 20, 600, 28, 'sans_med', col=GOLD, a=a * k, anchor='l')
        k2 = eo((t - WT('c1k', '十四倍') + 0.1) / 0.5)
        if k2 > 0:
            cv.text('市盈率 ≈ 14 倍', W / 2, 1290, 80, 'serif_black', gold=True, a=a * k2, glow=0.25)
            cv.text('股价 ÷ 每股年利润', W / 2, 1380, 30, 'sans_light', col=GREY, a=a * k2)
        source(cv, '2016 年四季度日均收盘价 $28.35 ÷ 2016 财年摊薄每股收益 $2.08（拆股调整）≈ 13.6 倍', a, y=1462)
    # ---- c1l：冰雪皇后的孩子们
    t0, t1 = win('c1l')
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        tsplit = WT('c1l', '周日')
        M.full(cv, 'v_dq_sign', t, t0, tsplit + 3.5, z0=1.0, z1=1.05, dark=0.2, a=a, fo=0.8, cap='冰雪皇后招牌')
        M.full(cv, 'dairy_queen', t, tsplit + 2.7, t1, z0=1.1, z1=1.22, focus=(0.5, 0.5), dark=0.3, a=a, fi=0.8, cap='冰雪皇后门店（伯克希尔旗下）')
        quote_card(cv, 'q2017dq', t, WT('c1l', '孩子们') - 0.6, t1, cy=1170, en_size=28, cn_size=34, a=a)
    # ---- c1m：内布拉斯加家具城
    t0, t1 = win('c1m')
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        M.frame(cv, 'nfm_kc', t, t0, t1, cy=560, w=1000, h=562, a=a, cap='内布拉斯加家具城（伯克希尔旗下）')
        quote_card(cv, 'q2024nfm', t, WT('c1m', '可只要') - 0.2, t1, cy=1130, en_size=30, cn_size=36, a=a)
    # ---- c1n：统觉团 → 大行动
    t0, t1 = win('c1n')
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        M.full(cv, 'x_bwbi_b', t, t0, t1, z0=1.0, z1=1.08, focus=(0.42, 0.42), dark=0.4, a=a)
        quote_card(cv, 'q2024am', t, t0 + 0.2, WT('c1n', '大行动') - 0.2, cy=1250, en_size=30, cn_size=36, a=a)
        k = eo((t - WT('c1n', '大行动') + 0.05) / 0.35)
        if k > 0:
            cv.text('大行动', W / 2, 1210, 150, 'serif_black', gold=True, a=a * k, glow=0.4, scale=1.12 - 0.12 * k, shadow=0.8)
            cv.text('BIG ACTION', W / 2, 1335, 32, 'corm', col=GOLD, a=a * k, track=0.4, shadow=0.8)
    # ---- c1p：2018 年 7 月：10 亿股、成本 360 亿、第一大持仓
    t0, t1 = win('c1p')
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        p = t - t0
        holdings_chart(cv, t, 160, 980, 560, 1150, reveal=eio(p / 2.5) * 0.31, a=a)
        cv.text('伯克希尔持有的苹果（亿股）', W / 2, 440, 34, 'sans_med', col=CREAM, a=a)
        k = eo((t - WT('c1p', '十亿股') + 0.1) / 0.5)
        cv.text('> 10 亿股', W / 2, 1290, 80, 'sans_bold', gold=True, a=a * k, glow=0.25)
        k2 = eo((t - WT('c1p', '三百六十亿') + 0.1) / 0.5)
        cv.text('成本 ≈ $360亿', W / 2 - 200, 1390, 40, 'sans_med', col=CREAM, a=a * k2)
        k3 = eo((t - WT('c1p', '第一大持仓') + 0.1) / 0.5)
        chip(cv, '第一大持仓', W / 2 + 230, 1390, 32, a * k3, col=GOLD)
        source(cv, '巴菲特 2020 年致股东信；伯克希尔 13F', a, y=1470)
    # ---- c1q：2018 年，段永平专程见巴菲特
    t0, t1 = win('c1q')
    a = env(t, t0, t1, 0.6, 0.4)
    if a > 0:
        M.full(cv, 'v_omaha_drone', t, t0, t1, z0=1.0, z1=1.06, dark=0.45, a=a, src_t0=40.0, cap='奥马哈航拍（2016）')
        cv.text('2018', W / 2, 955, 90, 'oswald', col=GOLD, a=a * eo((t - t0 - 0.4) / 0.6), shadow=0.8)
        quote_card(cv, 'qduan2018', t, WT('c1q', '我觉得') - 0.4, t1, cy=1175, cn_size=42, a=a)
        k = eo((t - WT('c1q', 'I got it') + 0.05) / 0.4)
        cv.text('“I got it.”', W / 2, 1400, 70, 'typewriter', col=GOLD_L, a=a * k, glow=0.2, shadow=0.8)
    # ---- c1r：那时巴菲特已经买了两年
    t0, t1 = win('c1r')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        cv.text('2016', 260, 760, 90, 'oswald', col=GOLD, a=a)
        cv.text('巴菲特买入', 260, 860, 32, 'sans_light', col=CREAM, a=a)
        L = 380 * eio(p / 1.0)
        cv.line((360, 760), (360 + L, 760), GOLD_D, a, 3)
        cv.text('2018', 820, 760, 90, 'oswald', col=CREAM, a=a * eo((p - 0.8) / 0.4))
        cv.text('二人晚餐', 820, 860, 32, 'sans_light', col=CREAM, a=a * eo((p - 0.8) / 0.4))
        k = eo((t - WT('c1r', '跟我没关系') + 0.1) / 0.5)
        cv.text('“他买苹果，跟我没关系。”', W / 2, 1100, 58, 'serif_semi', col=GOLD_L, a=a * k, shadow=0.6)
        cv.text('—— 段永平', W / 2 + 260, 1185, 30, 'sans_light', col=GREY, a=a * k)
        source(cv, '段永平 2025-01-05 浙江大学讲座（IT之家、证券之星文字实录）', a, y=1462)
    # ---- c1s：2020 年，换上 iPhone
    t0, t1 = win('c1s', 'ch2' if False else None)
    t1 = CH['ch2'][0] + 0.2
    a = env(t, t0, t1, 0.5, 0.5)
    if a > 0:
        tsw = WT('c1s', 'iPhone')
        M.full(cv, 'x_iphone_hand', t, t0, t1, z0=1.0, z1=1.08, dark=0.3, a=a, speed=0.3, cap='iPhone')
        cv.text('2020', W / 2, 955, 90, 'oswald', col=GOLD, a=a * eo((t - t0) / 0.6), shadow=0.8)
        quote_card(cv, 'q2020flip', t, WT('c1s', '我的翻盖') - 0.4, t1, cy=1190, en_size=38, cn_size=42, a=a)
