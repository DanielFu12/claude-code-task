"""第五章 · 卖与不卖（可口可乐 vs 苹果 → 1998 与 2024 → 段永平也在减持 → 库克 → 四条道理 → 主题）"""
from common import *  # noqa
import media as M


def shot_ch5(cv, t):
    # ---- c5a：可口可乐 38 年一股未卖；苹果十年卖掉四分之三
    t0, t1 = win('c5a')
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        M.frame(cv, 'coke_bottles', t, t0, t1, cy=520, w=1000, h=520, a=a, bg=False, cap='可口可乐')
        M.frame(cv, 'iphone11_cam', t, t0, t1, cy=1150, w=1000, h=520, a=a, bg=False, cap='iPhone')
        k1 = eo((t - WT('c5a', '三十八年') + 0.1) / 0.5)
        cv.text('38 年 · 一股未卖', W / 2, 520, 64, 'serif_black', gold=True, a=a * k1, glow=0.25, shadow=0.9)
        k2 = eo((t - WT('c5a', '四分之三') + 0.1) / 0.5)
        cv.text('10 年 · 卖掉 3/4', W / 2, 1150, 64, 'serif_black', col=CREAM, a=a * k2, shadow=0.9)
    # ---- c5b：1998 年可口可乐 47 倍没卖；“我说了，却没有做”
    t0, t1 = win('c5b')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        M.full(cv, 'coke_bottles', t, t0, t1, z0=1.2, z1=1.3, dark=0.6, a=a, sat=0.4, credit=False)
        k = eo((t - WT('c5b', '一九九八') + 0.1) / 0.5)
        cv.text('1998 · 可口可乐', W / 2, 460, 52, 'sans_med', col=CREAM, a=a * k, shadow=0.8)
        cv.text('市盈率 ≈ 47 倍', W / 2, 580, 80, 'serif_black', col=RED, a=a * eo((t - WT('c5b', '四十七倍') + 0.1) / 0.5), shadow=0.8)
        cv.text('没有卖', W / 2, 690, 50, 'serif_semi', col=CREAM, a=a * eo((t - WT('c5b', '没有卖') + 0.1) / 0.5), shadow=0.8)
        quote_card(cv, 'q2004', t, WT('c5b', '后来') - 0.3, t1, cy=1050, en_size=40, cn_size=46, a=a)
    # ---- c5c：2024 年苹果：近 30 倍、近一半仓位 → 这一次，他卖了
    t0, t1 = win('c5c')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        M.full(cv, 'apple_5th_displays', t, t0, t1, z0=1.1, z1=1.2, dark=0.6, a=a, sat=0.5, cap='苹果店内')
        cv.text('2024 · 苹果', W / 2, 460, 52, 'sans_med', col=CREAM, a=a, shadow=0.8)
        cv.text('市盈率 ≈ 30 倍', W / 2, 580, 80, 'serif_black', col=CREAM, a=a * eo((t - WT('c5c', '三十倍') + 0.1) / 0.5), shadow=0.8)
        cv.text('占股票投资近一半', W / 2, 690, 50, 'serif_semi', col=CREAM, a=a * eo((t - WT('c5c', '近一半') + 0.1) / 0.5), shadow=0.8)
        k = eo((t - WT('c5c', '他卖了') + 0.05) / 0.4)
        cv.text('这一次，他卖了', W / 2, 960, 96, 'serif_black', gold=True, a=a * k, glow=0.35, shadow=0.8, scale=1.08 - 0.08 * k)
    # ---- c5d：段永平也在减持（H&H：6400 万股 → 2700 万股）
    t0, t1 = win('c5d')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('段永平基金（H&H）持有的苹果', W / 2, 420, 36, 'sans_med', col=CREAM, a=a)
        bars(cv, [('2024 年中', 6392, GOLD * 0.75, WT('c5d', '六千四百万') - 0.2), ('2026 年中', 2710, RED, WT('c5d', '两千七百万') - 0.2)],
             t, t0, a, x0=200, x1=880, base=1220, hmax=620, fmt=lambda v: f'{v:,.0f}万股', label_size=30)
        k = eo((t - WT('c5d', '近六成') + 0.1) / 0.5)
        cv.text('−58%', W / 2, 640, 100, 'sans_bold', col=RED, a=a * k, glow=0.2)
        source(cv, 'SEC 13F（H&H International，外界普遍认为由段永平管理）：2024-06-30 63,924,255 股 → 2026-06-30 27,098,707 股', a, y=1392)
    # ---- c5d2：“水果已经比较成熟了”；卖出的钱买了短期国债
    t0, t1 = win('c5d2')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        M.full(cv, 'treasury', t, t0, t1, z0=1.2, z1=1.3, dark=0.6, a=a, sat=0.45, credit=False)
        k = eo((t - WT('c5d2', '水果') + 0.1) / 0.5)
        cv.text('“水果”', W / 2, 720, 130, 'serif_black', gold=True, a=a * k, glow=0.3, shadow=0.8)
        cv.text('已经比较成熟了', W / 2, 860, 56, 'serif_semi', col=CREAM, a=a * k, shadow=0.8)
        k2 = eo((t - WT('c5d2', '短期国债') + 0.1) / 0.5)
        chip(cv, '卖出所得 → 美国短期国债', W / 2, 1060, 34, a * k2, col=GOLD)
        source(cv, '澎湃新闻 2026-07-23（香港01 同日报道相同内容）', a, y=1392)
    # ---- c5e：库克为伯克希尔赚的钱，比我为伯克希尔赚的还多
    t0, t1 = win('c5e')
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        M.full(cv, 'cook_2017', t, t0, t1, z0=1.05, z1=1.14, focus=(0.5, 0.35), dark=0.4, a=a, sat=0.6, cap='蒂姆·库克 · 2017')
        quote_card(cv, 'q2025', t, WT('c5e', '说来') - 0.4, t1, cy=1060, en_size=30, cn_size=36, a=a)
    # ---- c5f–c5j：四条道理
    t0, t1 = S('c5f') - 0.3, S('c5k') + 0.1
    a = env(t, t0, t1, 0.5, 0.5)
    if a > 0:
        M.full(cv, 'apple_park_aerial', t, t0, t1, z0=1.5, z1=1.65, dark=0.7, a=a, sat=0.4, credit=False)
        cv.text('这十年，留下了四条朴素的道理', W / 2, 400, 44, 'sans_med', col=CREAM, a=a * eo((t - t0) / 0.6), shadow=0.8)
        rules = [('c5g', '看得懂，才下重注'), ('c5h', '买股票，就是买生意'), ('c5i', '再好的生意，也要看价格'), ('c5j', '仓位和税，都要算进账里')]
        for k, (lid, txt) in enumerate(rules):
            kk = eo((t - S(lid) + 0.1) / 0.5)
            if kk <= 0: continue
            y = 640 + k * 190
            cur = (t >= S(lid) - 0.1) and (k == 3 or t < S(rules[k + 1][0]) - 0.1)
            cv.text(f'0{k + 1}', 170, y, 56, 'oswald', col=GOLD, a=a * kk, shadow=0.8)
            cv.text(txt, 250, y, 62 if cur else 54, 'serif_black', gold=cur, col=CREAM, a=a * kk * (1 if cur else 0.75), anchor='l',
                    glow=0.25 if cur else 0, shadow=0.8)
    # ---- c5k：比起卖在最高点……
    t0, t1 = win('c5k')
    a = env(t, t0, t1, 0.5, 0.5)
    if a > 0:
        M.full(cv, 'v_dundee_drone', t, t0, t1, z0=1.0, z1=1.06, dark=0.4, a=a, src_t0=30.0, cap='奥马哈 Dundee 街区航拍（巴菲特住了几十年的街区）')
        k = eo((t - WT('c5k', '更值得学的') + 0.1) / 0.6)
        cv.text('不是卖在最高点', W / 2, 720, 60, 'serif_semi', col=GREY, a=a * eo((t - WT('c5k', '最高点') + 0.1) / 0.5), shadow=0.8)
        cv.text('而是每一个决定', W / 2, 860, 70, 'serif_black', col=CREAM, a=a * k, shadow=0.8)
        cv.text('算得清 · 讲得通', W / 2, 990, 90, 'serif_black', gold=True, a=a * eo((t - WT('c5k', '算得清') + 0.1) / 0.5), glow=0.3, shadow=0.8)
    # ---- c5l：主题句
    t0, t1 = S('c5l') - 0.3, CH['end'][0] + 0.3
    a = env(t, t0, t1, 0.6, 0.6)
    if a > 0:
        M.full(cv, 'buffett_2015', t, t0, t1, z0=1.18, z1=1.28, focus=(0.55, 0.38), dark=0.35, a=a, sat=0.5, credit=False)
        k = eo((t - WT('c5l', '伟大的企业') + 0.1) / 0.7)
        cv.text('伟大的企业，值得长期陪伴', W / 2, 1060, 58, 'serif_black', col=CREAM, a=a * k, shadow=0.9)
        k2 = eo((t - WT('c5l', '但没有') + 0.1) / 0.7)
        cv.text('但没有任何一只股票', W / 2, 1180, 58, 'serif_black', gold=True, a=a * k2, glow=0.25, shadow=0.9)
        cv.text('值得不计价格、不计仓位地拥有', W / 2, 1280, 52, 'serif_black', gold=True, a=a * eo((t - WT('c5l', '不计价格') + 0.1) / 0.7), glow=0.25, shadow=0.9)
