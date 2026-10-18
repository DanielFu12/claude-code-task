"""第二章 · 一瓶糖水的护城河（商业模式的第一性原理）"""
from common import *  # noqa


def shot_ch2(cv, t):
    # ---- s14：一瓶糖水
    t0, t1 = S('s14') - 0.5, S('s15') + 0.2
    a = env(t, t0, t1, 0.6, 0.4)
    if a > 0:
        p = t - t0
        bottle_layer(cv, t, a, rot=1.8 + p * 0.35, fill=0.8, camd=lerp(9.0, 7.8, eio(p / 4)), camy=1.4,
                     shift=(0.0, -0.05), ex=1.1, bub=1.4)
        cv.text('一瓶糖水', W / 2, 1180, 110, 'serif_black', gold=True, a=a * eo((p - 0.3) / 0.6), glow=0.2)
        cv.text('凭什么成为持续创造现金的机器？', W / 2, 1310, 40, 'sans_light', col=CREAM, a=a * eo((p - 1.2) / 0.6))
    # ---- s15：芒格的思想实验
    t0, t1 = S('s15') - 0.3, S('s16') + 0.1
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        if os.path.exists(os.path.join(ROOT, 'assets', 'archive', 'munger_2010.jpg')):
            photo(cv, 'munger_2010', t, t0, t1, 250, 470, 300, 360, z0=2.6, z1=2.8, mode='bw', fi=0.4, fo=0.4,
                  caption=None, focus=(0.37, 0.3))
            cv.text('Charlie Munger · 摄影 Nick Webb（CC BY 2.0）', 250, 680, 18, 'sans_light', col=DIM, a=a)
        cv.text('1884', 450, 380, 100, 'oswald', col=GOLD, a=a * eo(p / 0.6), anchor='l')
        cv.text('亚特兰大 · 思想实验', 455, 470, 34, 'sans_med', col=CREAM, a=a * eo((p - 0.3) / 0.6), anchor='l')
        cv.text('芒格《关于现实思维的现实思考？》1996', 455, 520, 24, 'sans_light', col=GREY, a=a * eo((p - 0.5) / 0.6), anchor='l')
        cv.text('$2,000,000', W / 2, 820, 96, 'sans_light', col=CREAM, a=a * eo((p - 0.8) / 0.5))
        cv.text('↓', W / 2, 920, 60, 'sans_light', col=GOLD, a=a * eo((p - 1.6) / 0.4))
        k = eo((p - 2.0) / 0.7)
        cv.text('$2,000,000,000,000', W / 2, 1040, 76, 'sans_bold', gold=True, a=a * k, glow=0.25 * k,
                scale=1.12 - 0.12 * k, blur=(1 - k) * 6)
        cv.text('（200 万美元 → 2 万亿美元）', W / 2, 1140, 30, 'sans_light', col=GREY, a=a * eo((p - 3.8) / 0.5))
    # ---- s16：商标
    t0, t1 = S('s16') - 0.3, S('s17') + 0.1
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        if os.path.exists(os.path.join(ROOT, 'assets', 'archive', 'bottle_patent_1915.jpg')):
            al = env(t, t0, t1, 0.8, 0.4) * 0.9
            im = asset('bottle_patent_1915'); hh0, ww0 = im.shape[:2]
            im = im[int(hh0 * 0.115):int(hh0 * 0.51), int(ww0 * 0.36):int(ww0 * 0.64)]   # 只取图 1 的瓶身
            inv = 1 - im.mean(2)                    # 白底蓝图 → 发光线稿
            hh = 820; ww = int(hh * im.shape[1] / im.shape[0])
            m = cv2.resize(inv, (ww, hh), interpolation=cv2.INTER_AREA)
            wipe = np.clip((np.arange(hh)[:, None] - (1 - eio(p / 2.5)) * hh) / 40, 0, 1)
            cv.add(GOLD, np.clip(m * 1.6, 0, 1) * wipe * al, 800 - ww / 2, 300, glow=0.4)
            cv.text('1915 年美国外观设计专利 D48,160（公有领域）', 800, 1150, 20, 'sans_light', col=DIM, a=a)
        k = eo(p / 0.5)
        y = 520
        cv.text('格罗茨牌', 270, y - 60, 40, 'serif_semi', col=CREAM, a=a * k)
        cv.text('含糖咖啡因水', 270, y, 40, 'serif_semi', col=CREAM, a=a * k)
        x = eo((p - 1.0) / 0.4)
        cv.line((120, y - 30), (120 + 300 * x, y - 30 + 20 * x), RED, a, 6)
        cv.text('芒格的玩笑：普通饮料，不可能值 2 万亿', 270, y + 70, 22, 'sans_light', col=GREY, a=a * k)
        k2 = eo((p - 1.6) / 0.6)
        cv.text('Coca-Cola', 270, 820, 82, 'playfair', col=RED, a=a * k2, glow=0.4)
        cv.text('®', 450, 770, 34, 'sans_med', col=RED, a=a * k2)
        cv.text('受法律保护的强大商标', 270, 920, 36, 'sans_med', col=GOLD, a=a * k2)
        cv.text('（品牌心智）', 270, 970, 28, 'sans_light', col=GREY, a=a * k2)
    # ---- s17：条件反射
    t0, t1 = S('s17') - 0.3, S('s18') + 0.1
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        c1, c2 = (260, 520), (820, 520)
        k = eo(p / 0.5)
        pulse = beat_pulse(t, 4)
        photo(cv, 'coke_ad_1890s', t, t0, t1, c1[0], c1[1] - 20, 270, 360, z0=1.0, z1=1.06, mode=None, fi=0.4, fo=0.4)
        cv.glow_dot(c1, 120, RED, a * k * 0.35 * (0.5 + 0.5 * pulse))
        cv.text('刺激', c1[0], c1[1] + 200, 40, 'serif_black', col=WHITE, a=a * k)
        cv.text('1890 年代广告（公有领域）', c1[0], c1[1] + 245, 18, 'sans_light', col=DIM, a=a * k)
        cv.circle(c2, 110, GOLD, a * eo((p - 1.0) / 0.5), 6)
        cv.text('反应', c2[0], c2[1] - 10, 44, 'serif_black', col=WHITE, a=a * eo((p - 1.0) / 0.5))
        cv.text('想喝一口冰凉', c2[0], c2[1] + 46, 24, 'sans_light', col=CREAM, a=a * eo((p - 1.0) / 0.5))
        for j in range(3):
            q = ((p * 0.9 + j / 3) % 1.0)
            x = lerp(c1[0] + 150, c2[0] - 120, q)
            cv.glow_dot((x, c1[1] + math.sin(q * math.pi * 2) * 18), 10, GOLD_L, a * k)
        cv.line((c1[0] + 150, c1[1]), (c2[0] - 120, c2[1]), GOLD_D, a * k * 0.6, 2)
        quote_card(cv, 'qmunger', t, t0 + 1.2, t1, cy=1080, en_size=32, cn_size=38)
    # ---- s18：无处不在
    t0, t1 = S('s18') - 0.3, S('s19') + 0.1
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        p = t - t0
        globe(cv, t, W / 2, 700, 380, rot=1.6 + p * 0.25, a=a, arcs=1.0, city_glow=1.0)
        v = counter(0, 22, t, t0 + 0.5, 2.5, lambda v: f'{v:.0f}亿')
        cv.text(v, W / 2 - 40, 1200, 130, 'sans_bold', gold=True, a=a, glow=0.3)
        cv.text('份 / 每天', W / 2 + 230, 1225, 38, 'sans_med', col=CREAM, a=a, anchor='l')
        cv.text('200 多个国家和地区', W / 2, 1310, 34, 'sans_light', col=CREAM, a=a * eo((p - 1.0) / 0.5))
        source(cv, '数据：可口可乐 2025 年 10-K', a)
    # ---- s19：浓缩液 + 装瓶伙伴
    t0, t1 = S('s19') - 0.3, S('s20') + 0.1
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        top = (W / 2, 360)
        k = eo(p / 0.5)
        cv.rrect(260, 300, 820, 420, 20, (0.25, 0.04, 0.05), a * k * 0.9)
        cv.rrect(260, 300, 820, 420, 20, RED, a * k, fill=False, th=3)
        cv.text('可口可乐公司', W / 2, 340, 40, 'serif_black', col=WHITE, a=a * k)
        cv.text('浓缩液 · 品牌 · 配方', W / 2, 392, 28, 'sans_med', col=GOLD_L, a=a * k)
        labels = ['装瓶伙伴', '装瓶伙伴', '装瓶伙伴', '装瓶伙伴', '装瓶伙伴']
        xs = np.linspace(150, 930, 5)
        for i, x in enumerate(xs):
            ki = eo((p - 0.5 - i * 0.15) / 0.5)
            cv.line((W / 2, 420), (x, 600), GOLD_D, a * ki * 0.8, 2)
            cv.rrect(x - 78, 600, x + 78, 680, 12, (0.12, 0.10, 0.08), a * ki)
            cv.text('装瓶厂', x, 640, 26, 'sans_med', col=CREAM, a=a * ki)
            for j in range(3):
                kj = eo((p - 1.2 - i * 0.1 - j * 0.1) / 0.5)
                xx = x + (j - 1) * 52
                cv.line((x, 680), (xx, 800), (0.4, 0.35, 0.3), a * kj * 0.6, 1)
                cv.glow_dot((xx, 806), 5, GOLD, a * kj)
        cv.text('工厂 · 卡车 · 冰柜 · 门店 —— 大多属于装瓶伙伴', W / 2, 880, 30, 'sans_light', col=GREY, a=a * eo((p - 1.6) / 0.5))
        k3 = eo((p - 2.2) / 0.5)
        cv.text('85%', W / 2 - 200, 1060, 130, 'sans_bold', gold=True, a=a * k3, glow=0.25)
        cv.text('销量来自浓缩液业务', W / 2 - 200, 1170, 28, 'sans_med', col=CREAM, a=a * k3)
        cv.text('59%', W / 2 + 230, 1060, 130, 'sans_light', col=CREAM, a=a * k3)
        cv.text('收入来自浓缩液业务', W / 2 + 230, 1170, 28, 'sans_med', col=CREAM, a=a * k3)
        source(cv, '数据：可口可乐 2025 年 10-K（按单位箱销量与净营业收入口径）', a)
    # ---- s20：真正的钱在糖浆里
    t0, t1 = S('s20') - 0.4, S('s21') + 0.1
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        d = sh('DROP')(t=t, ph=cl((p - 0.2) / 3.0), tint=(1.0, 0.62, 0.22))
        al = d[..., 3:4] * a
        cv.img = cv.img * (1 - al) + d[..., :3] * al
        cv.glow += np.clip(d[..., :3] * al - 0.4, 0, None)
        quote_card(cv, 'q1994', t, t0 + 0.6, t1, cy=470, en_size=34, cn_size=40)
    # ---- s21：毛利率与资本开支
    t0, t1 = S('s21') - 0.3, S('s22') + 0.1
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        cv.text('2025', W / 2, 330, 46, 'oswald', col=GOLD, a=a, track=0.2)
        for i, (y, val, lab, mx, colr) in enumerate([(560, 61.6, '毛利率', 100, GOLD), (930, 4.4, '资本开支 / 收入', 100, RED)]):
            k = eexp((p - 0.3 - i * 1.4) / 1.4)
            cv.text(f'{val * k:.1f}%', 110, y, 160, 'sans_light', col=WHITE, a=a * eo((p - 0.3 - i * 1.4) / 0.4), anchor='l')
            cv.text(lab, 112, y + 110, 36, 'sans_med', col=colr, a=a * eo((p - 0.3 - i * 1.4) / 0.4), anchor='l')
            cv.rrect(110, y + 160, 970, y + 172, 6, (0.22, 0.2, 0.2), a)
            cv.rrect(110, y + 160, 110 + 860 * val / mx * k, y + 172, 6, colr, a, glow=0.4)
        cv.text('轻资产：重的工厂与车队交给伙伴，自己守住品牌与配方', W / 2, 1290, 28, 'sans_light', col=CREAM, a=a * eo((p - 3.2) / 0.5))
        source(cv, '数据：可口可乐 2025 年 10-K（毛利 295.4 亿 ÷ 收入 479.4 亿；资本开支 21.1 亿）', a)
    # ---- s22：一分一分
    t0, t1 = S('s22') - 0.3, S('s23') + 0.1
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        rng = np.random.default_rng(5)
        N = 5000
        n = int(N * eio(p / 3.5))
        xs = rng.normal(W / 2, 200, N)[:n]
        hh = 420 * np.exp(-((xs - W / 2) / 260) ** 2) * min(1, n / N * 1.4)
        ys = 1200 - rng.random(n) * hh
        cv.splat(xs, ys, GOLD, a * 1.4, glow=1.4)
        cv.splat(xs + 1, ys, GOLD_L, a * 0.6, glow=0.8)
        cv.text('1994 年', W / 2, 330, 40, 'sans_med', col=CREAM, a=a)
        cv.text('约 2,800 亿份', W / 2, 450, 90, 'sans_light', col=WHITE, a=a * eo(p / 0.5))
        cv.text('每份赚 < 1 美分', W / 2, 570, 56, 'sans_med', col=GOLD, a=a * eo((p - 0.8) / 0.5))
        cv.text('伯克希尔占 7.8% → 每年约 2 亿美元“汽水利润”', W / 2, 670, 32, 'sans_light', col=CREAM, a=a * eo((p - 1.8) / 0.5))
        source(cv, '出处：巴菲特 1994 年致股东信', a)
    # ---- s23：护城河
    t0, t1 = S('s23') - 0.3, CH['ch3'][0] + 0.05
    a = env(t, t0, t1, 0.6, 0.4)
    if a > 0:
        p = t - t0
        bottle_layer(cv, t, a, rot=2.6 + p * 0.2, fill=0.8, camd=11.5, camy=2.6, shift=(0.0, 0.1), ex=1.0, bub=1.0,
                     ripple=1.0, floorr=1.6)
        labels = ['品牌心智', '全球渠道', '定价权', '轻资产', '高资本回报']
        for i, s in enumerate(labels):
            ang = -math.pi / 2 + i * 2 * math.pi / 5 + p * 0.12
            x = W / 2 + math.cos(ang) * 400; y = 760 + math.sin(ang) * 240
            chip(cv, s, x, y, 32, a * eo((p - 0.4 - i * 0.3) / 0.5), col=GOLD_L)
        cv.text('护城河', W / 2, 1180, 120, 'serif_black', gold=True, a=a * eo((p - 1.5) / 0.6), glow=0.3)
        cv.text('“……在经济城堡周围，筑起一道护城河。” —— 巴菲特 1993', W / 2, 1300, 28, 'serif_reg', col=CREAM,
                a=a * eo((p - 2.2) / 0.6))
