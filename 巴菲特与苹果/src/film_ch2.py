"""第二章 · 买的是生意（第三大生意 → 最好的生意 → 第二辆车 → 信条 → 股息与应占利润 → 回购 → 透视盈余 → 每股收益）"""
from common import *  # noqa
import media as M

BUYBACK = [(2016, 29.7), (2017, 32.9), (2018, 72.7), (2019, 66.9), (2020, 72.4), (2021, 86.0), (2022, 89.4), (2023, 77.5),
           (2024, 94.9), (2025, 90.7)]                        # 苹果各财年回购（十亿美元，10-K 现金流量表）
SHARES = [(2016, 22.0), (2017, 21.0), (2018, 20.0), (2019, 18.6), (2020, 17.5), (2021, 16.9), (2022, 16.3), (2023, 15.8),
          (2024, 15.4), (2025, 15.0)]                          # 摊薄加权股数（十亿股，拆股调整）


def shot_ch2(cv, t):
    # ---- c2a：不只是一家卖手机的公司
    t0, t1 = win('c2a')
    a = env(t, t0, t1, 0.6, 0.4)
    if a > 0:
        M.full(cv, 'x_park_ring2', t, t0, t1, z0=1.0, z1=1.06, dark=0.2, a=a, src_t0=3.0, cap='Apple Park 航拍')
    # ---- c2b：伯克希尔的第三大生意（仅次于保险和铁路）
    t0, t1 = win('c2b')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        M.full(cv, 'x_park_ring1', t, t0 - 1.0, t1, z0=1.0, z1=1.06, dark=0.6, a=a, src_t0=3.0, speed=0.7, credit=False)
        items = [('保险', 'INSURANCE', '保险'), ('铁路', 'BNSF', '铁路'), ('苹果', 'APPLE', '第三大生意')]
        for k, (nm, en, w_) in enumerate(items):
            kk = eback((t - WT('c2b', w_) + 0.1) / 0.5)
            if kk <= 0: continue
            cx = 220 + k * 320; cy = 820
            col = GOLD if k == 2 else CREAM
            cv.rrect(cx - 140, cy - 140 * kk, cx + 140, cy + 140 * kk, 18, (0.06, 0.05, 0.05), a * 0.9)
            cv.rrect(cx - 140, cy - 140 * kk, cx + 140, cy + 140 * kk, 18, col, a * 0.8, fill=False, th=3 if k == 2 else 2)
            cv.text(f'0{k + 1}', cx, cy - 70, 30, 'oswald', col=GOLD_D, a=a * min(kk, 1))
            cv.text(nm, cx, cy + 10, 60, 'serif_black', col=col, a=a * min(kk, 1), glow=0.2 if k == 2 else 0)
            cv.text(en, cx, cy + 85, 22, 'corm', col=GREY, a=a * min(kk, 1), track=0.2)
        quote_card(cv, 'q2020third', t, WT('c2b', '我不把') - 0.4, t1, cy=1230, en_size=30, cn_size=36, a=a, w=960)
    # ---- c2c：世界上最好的生意
    t0, t1 = win('c2c')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        M.full(cv, 'x_i6s_store', t, t0, t1, z0=1.0, z1=1.06, dark=0.45, a=a, src_t0=0.0, speed=0.8, cap='苹果店 · 新 iPhone 首发日')
        quote_card(cv, 'q2020best', t, t0 + 0.1, t1, cy=860, en_size=40, cn_size=46, a=a)
    # ---- c2d：第二辆车 vs iPhone
    t0, t1 = win('c2d')
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        M.full(cv, 'v_cars_night', t, t0, t1, z0=1.0, z1=1.05, dark=0.45, a=a, src_t0=10.0, cap='夜间公路车流')
        k1 = eo((t - WT('c2d', '第二辆车') + 0.1) / 0.5); k2 = eo((t - WT('c2d', 'iPhone') + 0.1) / 0.5)
        cv.text('第二辆车', W / 2 - 230, 620, 66, 'serif_black', col=CREAM, a=a * k1, shadow=0.8)
        cv.text('vs', W / 2, 620, 40, 'corm', col=GREY, a=a * k2, shadow=0.8)
        cv.text('iPhone', W / 2 + 230, 620, 66, 'sans_bold', col=GOLD_L, a=a * k2, shadow=0.8)
        k3 = eo((t - WT('c2d', '他们会放弃') + 0.1) / 0.4)
        if k3 > 0:
            cv.line((W / 2 - 360, 620), (W / 2 - 360 + 260 * k3, 620), RED, a, 6)
        quote_card(cv, 'q2023a', t, WT('c2d', '如果让') - 0.4, t1, cy=1050, en_size=30, cn_size=36, a=a)
    # ---- c2e：一生的信条
    t0, t1 = win('c2e')
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        M.full(cv, 'x_bwb_desk', t, t0, t1, z0=1.0, z1=1.08, focus=(0.55, 0.45), dark=0.45, a=a, src_t0=1.0, speed=0.75)
        k = eo((t - WT('c2e', '买股票') + 0.1) / 0.6)
        cv.text('买股票，', W / 2, 760, 90, 'serif_black', col=CREAM, a=a * k, shadow=0.8)
        cv.text('就是买下一门生意的一部分', W / 2, 880, 60, 'serif_black', gold=True, a=a * eo((t - WT('c2e', '就是') + 0.1) / 0.6), glow=0.2, shadow=0.8)
        k2 = eo((t - WT('c2e', '股价每天') + 0.1) / 0.6)
        cv.text('股价每天在变', W / 2 - 220, 1120, 38, 'sans_light', col=GREY, a=a * k2, shadow=0.8)
        cv.text('→', W / 2, 1120, 38, 'sans_light', col=GREY, a=a * k2)
        cv.text('价值取决于未来能赚多少', W / 2 + 250, 1120, 38, 'sans_med', col=GOLD_L, a=a * eo((t - WT('c2e', '取决于') + 0.1) / 0.6), shadow=0.8)
    # ---- c2f：2021 年：股息 7.85 亿 vs 应占利润 56 亿
    t0, t1 = win('c2f')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        import fx
        fx.bars3d(cv, t, t0, t1, ('收到的股息', 7.85, '$7.85亿', WT('c2f', '股息是') - 0.1),
                  ('应占的苹果利润', 56.0, '$56亿', WT('c2f', '应占') - 0.1), a=a, title='2021 年 · 苹果之于伯克希尔')
        source(cv, '巴菲特 2021 年致股东信：“Apple paid us $785 million… our “share” of Apple’s earnings amounted to $5.6 billion”', a, y=1392)
    # ---- c2g：剩下的利润用于回购
    t0, t1 = win('c2g')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        cv.rrect(240, 520, 840, 640, 20, (0.07, 0.06, 0.05), a * 0.9)
        cv.text('苹果的利润', W / 2 - 60, 580, 48, 'serif_black', col=CREAM, a=a)
        for k, (lab, y, col, w_) in enumerate([('分红', 860, GREY, '没有发下来'), ('回购股票', 1080, GOLD, '回购')]):
            kk = eo((t - WT('c2g', w_) + 0.2) / 0.6)
            cv.line((540, 640), (300 + k * 480, y - 60), col, a * kk, 3 + k * 4)
            cv.text(lab, 300 + k * 480, y, 54 if k else 40, 'serif_black' if k else 'sans_light', col=col, a=a * kk, glow=0.2 if k else 0)
    # ---- c2h：2016–2025 财年回购 7130 亿美元，股数减少约三成
    t0, t1 = win('c2h')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        x0, x1, base = 150, 960, 1150
        bw = (x1 - x0) / 10 * 0.6
        for k, (fy, v) in enumerate(BUYBACK):
            e = eexp((p - 0.3 - k * 0.22) / 0.8)
            cx = x0 + (x1 - x0) * (k + 0.5) / 10
            h = 480 * v / 100 * e
            cv.rect(cx - bw / 2, base - h, cx + bw / 2, base, GOLD * 0.7, a, glow=0.1)
            cv.text(f'{fy % 100:02d}', cx, base + 30, 20, 'oswald', col=DIM, a=a)
        pts = [(x0 + (x1 - x0) * (k + 0.5) / 10, 520 + (22.0 - s_) / 8 * 300) for k, (fy, s_) in enumerate(SHARES)]
        n = max(2, int(len(pts) * eio((p - 0.5) / 2.5)))
        cv.poly(pts[:n], RED, a, 4)
        for q in pts[:n]: cv.glow_dot(q, 6, RED, a * 0.7)
        cv.text('总股本', pts[0][0], pts[0][1] - 40, 26, 'sans_light', col=RED, a=a)
        k = eo((t - WT('c2h', '七千一百三十亿') + 0.1) / 0.5)
        cv.text('回购合计 ≈ $7130亿', W / 2, 1300, 70, 'serif_black', gold=True, a=a * k, glow=0.25)
        k2 = eo((t - WT('c2h', '三成') + 0.1) / 0.5)
        cv.text('股数 −31.8%', W / 2, 1390, 44, 'sans_bold', col=RED, a=a * k2)
        cv.text('苹果各财年回购（十亿美元）与摊薄股数', W / 2, 420, 30, 'sans_med', col=CREAM, a=a)
        source(cv, '苹果 10-K（2016–2025 财年）现金流量表与摊薄加权股数（拆股调整）', a, y=1470)
    # ---- c2i：5.39% → 5.55%，“苹果的回购替我们做到了”
    t0, t1 = win('c2i')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        k = eio((t - WT('c2i', '持股比例') + 0.2) / 1.6)
        v = lerp(5.39, 5.55, k)
        cv.arc((W / 2, 720), 230, -math.pi / 2, 3 * math.pi / 2, (0.2, 0.2, 0.22), a, 18)
        cv.arc((W / 2, 720), 230, -math.pi / 2, -math.pi / 2 + 2 * math.pi * v / 100 * 6, GOLD, a, 18)
        cv.text(f'{v:.2f}%', W / 2, 720, 110, 'sans_bold', gold=True, a=a, glow=0.25)
        cv.text('伯克希尔在苹果的持股比例 · 2020 → 2021（示意放大）', W / 2, 1000, 26, 'sans_light', col=GREY, a=a)
        quote_card(cv, 'q2021', t, WT('c2i', '巴菲特写道') - 0.4, t1, cy=1220, en_size=30, cn_size=36, a=a)
    # ---- c2j：透视盈余
    t0, t1 = win('c2j')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        headline(cv, '透视盈余', 760, a, 120, k=eo((t - WT('c2j', '透视盈余') + 0.1) / 0.6))
        cv.text('LOOK-THROUGH EARNINGS', W / 2, 870, 30, 'corm', col=GOLD, a=a * eo((t - WT('c2j', '透视盈余')) / 0.6), track=0.3)
        cv.text('没有发下来，却实实在在属于股东的利润', W / 2, 1000, 40, 'sans_light', col=CREAM, a=a * eo(p / 0.8))
    # ---- c2k：同样的利润由更少的股票来分：净利润 ×2.9，每股收益 ×4.3
    t0, t1 = win('c2k', post=0.0)
    t1 = CH['ch3'][0] + 0.2
    a = env(t, t0, t1, 0.4, 0.5)
    if a > 0:
        import fx
        fx.bars3d(cv, t, t0, t1, ('净利润', 2.9, '×2.9', WT('c2k', '净利润') - 0.1), ('每股收益', 4.3, '×4.3', WT('c2k', '每股收益') - 0.1),
                  a=a, title='2016 → 2026 财年')
        k = eo((t - WT('c2k', '四百五十七亿') + 0.1) / 0.4)
        cv.text('净利润 $457亿 → $1322亿', W / 2, 1290, 32, 'sans_med', col=CREAM, a=a * k, shadow=0.8)
        k2 = eo((t - WT('c2k', '二点零八') + 0.1) / 0.4)
        cv.text('每股收益 $2.08 → $8.98', W / 2, 1350, 32, 'sans_med', col=GOLD_L, a=a * k2, shadow=0.8)
        source(cv, '苹果 10-K：2016 财年 vs 2026 财年（每股收益为摊薄、拆股调整）', a, y=1392)
