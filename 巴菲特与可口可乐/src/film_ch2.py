"""第二章 · 一瓶糖水的护城河（商业模式的第一性原理）"""
from common import *  # noqa


def shot_ch2(cv, t):
    scenes(cv, t)
    rail(cv, t)                     # 七要素进度条画在最上层（不被糖浆滴等前景遮住）


def scenes(cv, t):
    # ---- s14：一瓶糖水
    t0, t1 = S('s14') - 0.5, S('s15') + 0.2
    a = env(t, t0, t1, 0.6, 0.4)
    if a > 0:
        p = t - t0
        bottle_layer(cv, t, a, rot=1.8 + p * 0.35, fill=0.8, camd=lerp(9.0, 7.8, eio(p / 4)), camy=1.4,
                     shift=(0.0, -0.05), ex=1.1, bub=1.4)
        cv.text('一瓶糖水', W / 2, 1180, 110, 'serif_black', gold=True, a=a * eo((p - 0.3) / 0.6), glow=0.2)
        cv.text('凭什么成为持续创造现金的机器？', W / 2, 1310, 40, 'sans_light', col=CREAM, a=a * eo((p - 1.2) / 0.6))
        km = eo((t - WT('s14', '芒格')) / 0.5)
        cv.text('CHARLIE MUNGER · 1996 · 思想实验', W / 2, 1385, 24, 'corm', col=GOLD, a=a * km, track=0.25)
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
    t0, t1 = S('s16') - 0.3, S('s17a') + 0.1
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
    # ---- s17a–s17d：三种心理力量 → 多因素合奏效应（芒格 1996）
    t0, t1 = S('s17a') - 0.3, S('s18') + 0.1
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        three_forces(cv, t, a)
    # ---- s18：无处不在
    t0, t1 = S('s18') - 0.3, S('s19') + 0.1
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        p = t - t0
        globe(cv, t, W / 2, 740, 360, rot=1.6 + p * 0.25, a=a, arcs=1.0, city_glow=1.0)
        tc0 = WT('s18', '每天') - 0.6
        kc = eo((t - tc0) / 0.3)
        v = counter(0, 22, t, tc0, 1.4, lambda v: f'{v:.0f}亿')
        cv.text(v, W / 2 - 40, 1200, 130, 'sans_bold', gold=True, a=a * kc, glow=0.3)
        cv.text('份 / 每天', W / 2 + 230, 1225, 38, 'sans_med', col=CREAM, a=a * kc, anchor='l')
        cv.text('200 多个国家和地区', W / 2, 1310, 34, 'sans_light', col=CREAM, a=a * eo((t - WT('s18', '200')) / 0.5))
        cv.text('无处不在', W / 2, 300, 64, 'serif_black', gold=True, a=a * eo(p / 0.5), glow=0.2)
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
    # ---- s22：规模经济——销量摊薄单位广告与分销成本（示意）
    t0, t1 = S('s22') - 0.3, S('s23') + 0.1
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        x0, x1, y0, y1 = 150, 960, 520, 1150
        cv.line((x0, y1), (x1, y1), GREY, a, 2); cv.line((x0, y0 - 20), (x0, y1), GREY, a, 2)
        cv.text('销量 →', x1, y1 + 40, 26, 'sans_med', col=GREY, a=a, anchor='r')
        cv.text('每份分摊的广告 + 分销成本', x0 + 10, y0 - 50, 26, 'sans_med', col=GREY, a=a, anchor='l')
        xs = np.linspace(0.06, 1.0, 240)
        ys = y1 - (y1 - y0) * (0.08 + 0.92 * (0.06 / xs) ** 0.85)
        px = x0 + xs * (x1 - x0)
        n = max(2, int(240 * eio(p / 1.6)))
        cv.poly(np.stack([px[:n], ys[:n]], 1), GOLD, a, 4)
        k1 = eo((p - 1.4) / 0.5)
        kx = x0 + 0.92 * (x1 - x0); ky = y1 - (y1 - y0) * (0.08 + 0.92 * (0.06 / 0.92) ** 0.85)
        cv.glow_dot((kx, ky), 16, GOLD_L, a * k1)
        cv.text('可口可乐', kx, ky - 60, 40, 'serif_black', col=GOLD_L, a=a * k1)
        cv.text('巨大销量 · 单位成本极低', kx - 10, ky + 50, 24, 'sans_light', col=CREAM, a=a * k1, anchor='r')
        tr = WT('s22', '对手') - t0
        k2 = eo((p - tr) / 0.5)
        rx = x0 + 0.13 * (x1 - x0); ry = y1 - (y1 - y0) * (0.08 + 0.92 * (0.06 / 0.13) ** 0.85)
        cv.glow_dot((rx, ry), 14, RED, a * k2)
        cv.text('追赶者', rx + 30, ry - 10, 36, 'serif_black', col=RED, a=a * k2, anchor='l')
        cv.text('销量小 · 每一份都更贵', rx + 30, ry + 40, 24, 'sans_light', col=CREAM, a=a * k2, anchor='l')
        cv.text('每份赚不到 1 美分（1994），靠的是规模', W / 2, 360, 32, 'sans_med', col=CREAM, a=a * eo(p / 0.5))
        cv.text('示意图', x1, y0 - 50, 20, 'sans_light', col=DIM, a=a, anchor='r')
        source(cv, '出处：巴菲特 1994 年致股东信；芒格 1996（广告的规模劣势、分销的成本优势）', a)
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
                a=a * eo((p - 2.2) / 0.6), shadow=0.8)
        source(cv, '七要素为本片对芒格 1996 年演讲的归纳，并非芒格原文给出的编号清单', a * eo((p - 1.0) / 0.6))


# ------------------------------------------------------------------ 芒格配方：七要素进度条
RAIL = [('商标', 's16'), ('操作性条件反射', 's17a'), ('巴甫洛夫条件反射', 's17b'), ('社会认同', 's17c'),
        ('多因素合奏', 's17d'), ('无处不在', 's18'), ('规模经济', 's22')]


def rail(cv, t):
    a = env(t, S('s16') - 0.4, CH['ch3'][0] + 0.05, 0.5, 0.4)
    if a <= 0.004: return
    cv.text('芒格的配方 · 七个要素', 52, 132, 22, 'sans_med', col=GOLD, a=a, anchor='l', track=0.1)
    rows = [RAIL[:4], RAIL[4:]]
    for r, row in enumerate(rows):
        x = 52
        for name, sid in row:
            i = RAIL.index((name, sid))
            on = eo((t - S(sid) + 0.15) / 0.4)
            nxt = S(RAIL[i + 1][1]) if i + 1 < len(RAIL) else CH['ch3'][0]
            cur = 1.0 if S(sid) - 0.15 <= t < nxt - 0.15 else 0.0
            if t >= S('s23') - 0.3: cur = 0.0
            tw = text_size(name, 'sans_med', 22)[0]
            w = tw + 34
            colr = GOLD_L if cur else (GOLD * 0.75 if on > 0.5 else (0.38, 0.36, 0.36))
            fill = (0.22, 0.15, 0.06) if cur else (0.06, 0.05, 0.05)
            cv.rrect(x, 172 + r * 48 - 17, x + w, 172 + r * 48 + 17, 17, fill, a * 0.92)
            cv.rrect(x, 172 + r * 48 - 17, x + w, 172 + r * 48 + 17, 17, colr, a * (0.5 + 0.5 * on), fill=False, th=2)
            cv.text(f'{name}', x + w / 2, 172 + r * 48, 22, 'sans_med', col=colr, a=a)
            x += w + 12


def circle_photo(cv, name, cx, cy, r, a, focus=(0.5, 0.5), zoom=1.0):
    im = asset(name)
    ih, iw = im.shape[:2]
    s = 2 * r / min(ih, iw) * zoom
    cw = 2 * r / s
    ox, oy = cl(focus[0] * iw - cw / 2, 0, iw - cw), cl(focus[1] * ih - cw / 2, 0, ih - cw)
    M = np.array([[s, 0, -ox * s], [0, s, -oy * s]], np.float32)
    crop = cv2.warpAffine(im, M, (2 * r, 2 * r), flags=cv2.INTER_AREA)
    yy, xx = np.mgrid[0:2 * r, 0:2 * r].astype(np.float32)
    m = np.clip(r - np.sqrt((xx - r) ** 2 + (yy - r) ** 2), 0, 1.5) / 1.5
    cv.over(crop, m * a, cx - r, cy - r)


def three_forces(cv, t, a):
    """操作性条件反射 / 巴甫洛夫条件反射 / 社会认同 → 互相放大 → 多因素合奏效应"""
    N = {'op': (W / 2, 535), 'pv': (260, 895), 'sp': (820, 895)}
    R = 118
    ta, tb, tc, td = S('s17a'), S('s17b'), S('s17c'), S('s17d')
    cv.text('三种心理力量', W / 2, 300, 40, 'serif_black', gold=True, a=a, shadow=0.6)
    # 连线（合奏阶段点亮）
    kd = eo((t - td) / 0.8)
    for u, v in (('op', 'pv'), ('pv', 'sp'), ('sp', 'op')):
        p0, p1 = np.array(N[u]), np.array(N[v])
        d = (p1 - p0) / np.linalg.norm(p1 - p0)
        q0, q1 = p0 + d * (R + 8), p1 - d * (R + 8)
        cv.line(q0, q1, (0.3, 0.27, 0.25), a * (1 - kd) * 0.6, 2)
        if kd > 0:
            cv.line(q0, q0 + (q1 - q0) * kd, GOLD, a, 3)
            for j in range(4):
                f = ((t - td) * 0.7 + j / 4) % 1.0
                cv.glow_dot(q0 + (q1 - q0) * f, 9, GOLD_L, a * kd)
    # 1) 操作性条件反射：奖励回路
    k = eo((t - ta + 0.15) / 0.5)
    c = N['op']
    cv.circle(c, R, GOLD if k > 0.5 else GREY, a * (0.35 + 0.65 * k), 4)
    cv.text('操作性', c[0], c[1] - 22, 34, 'serif_black', col=WHITE if k > 0.5 else GREY, a=a)
    cv.text('条件反射', c[0], c[1] + 24, 30, 'serif_semi', col=CREAM if k > 0.5 else GREY, a=a)
    if k > 0:
        for j, wd in enumerate(['甜', '冰', '提神']):
            ang = -math.pi / 2 + j * 2 * math.pi / 3 + (t - ta) * 0.6
            kk = eo((t - WT('s17a', wd) + 0.1) / 0.3)
            chip(cv, wd, c[0] + math.cos(ang) * (R + 72), c[1] + math.sin(ang) * (R + 40), 26, a * kk, col=GOLD_L)
        cv.arc(c, R + 14, (t - ta) * 2.0, (t - ta) * 2.0 + 4.6, GOLD_L, a * k * 0.6, 2)
        kk = eo((t - WT('s17a', '喝了') + 0.1) / 0.4)
        cv.text('喝 → 满足 → 再喝', c[0], c[1] + R + 115, 28, 'sans_med', col=GOLD_L, a=a * kk * (1 - kd))
    # 2) 巴甫洛夫条件反射：1890 年代广告 + 联想
    k = eo((t - tb + 0.15) / 0.5)
    c = N['pv']
    if k > 0:
        circle_photo(cv, 'coke_ad_1890s', int(c[0]), int(c[1]), R - 4, a * k * (1 - 0.65 * kd), focus=(0.5, 0.33), zoom=1.15)
    cv.circle(c, R, RED if k > 0.5 else GREY, a * (0.35 + 0.65 * k), 4)
    if k <= 0.5 or kd > 0.5:
        cv.text('巴甫洛夫', c[0], c[1] - 22, 34, 'serif_black', col=WHITE if k > 0.5 else GREY, a=a)
        cv.text('条件反射', c[0], c[1] + 24, 30, 'serif_semi', col=CREAM if k > 0.5 else GREY, a=a)
    else:
        cv.text('巴甫洛夫条件反射', c[0], c[1] + R + 40, 30, 'serif_black', col=WHITE, a=a * k * (1 - kd))
        cv.text('1890 年代广告（公有领域）', c[0], c[1] + R + 78, 18, 'sans_light', col=DIM, a=a * k * (1 - kd))
    for j, wd in enumerate(['快乐', '青春', '庆祝']):
        kk = eo((t - WT('s17b', wd) + 0.1) / 0.3) * (1 - kd)
        if kk <= 0: continue
        px, py = c[0] - 60 + j * 150, c[1] - R - 120 + (j % 2) * 30
        if j == 2: px, py = c[0] + R + 70, c[1] - 40
        cv.line((px, py + 20), (c[0] + (px - c[0]) * 0.35, c[1] + (py - c[1]) * 0.35 + 30), GOLD_D, a * kk * 0.7, 2)
        chip(cv, wd, px, py, 26, a * kk, col=GOLD_L)
    # 3) 社会认同：人群被一个个点亮
    k = eo((t - tc + 0.15) / 0.5)
    c = N['sp']
    cv.circle(c, R, TEAL if k > 0.5 else GREY, a * (0.35 + 0.65 * k), 4)
    cv.text('社会认同', c[0], c[1] - 22, 34, 'serif_black', col=WHITE if k > 0.5 else GREY, a=a)
    cv.text('别人在喝，我也想', c[0], c[1] + 24, 22, 'sans_light', col=CREAM if k > 0.5 else GREY, a=a)
    if k > 0:
        rng = np.random.default_rng(21)
        ppl = 70
        ang = rng.uniform(0, 2 * np.pi, ppl); rad = rng.uniform(R + 35, R + 150, ppl)
        order = np.argsort(rad)
        lit = (t - tc) / 2.2 * ppl
        for n_, idx in enumerate(order):
            x = c[0] + math.cos(ang[idx]) * rad[idx]; y = c[1] + math.sin(ang[idx]) * rad[idx] * 0.75
            if x > W - 30 or y > 1120: continue
            on = cl(lit - n_)
            col = TEAL * (0.4 + 0.6 * on) if on > 0 else (0.25, 0.25, 0.27)
            cv.glow_dot((x, y - 7), 4.5, col, a * (0.5 + 0.5 * on) * (1 - 0.6 * kd))
            cv.line((x, y - 1), (x, y + 9), col, a * (0.5 + 0.5 * on) * (1 - 0.6 * kd), 3)
    # 4) 多因素合奏效应
    if kd > 0:
        ctr = (W / 2, 770)
        cv.glow_dot(ctr, 110 + 20 * math.sin((t - td) * 4), GOLD, a * kd * 0.55)
        km = eo((t - WT('s17d', '芒格') + 0.1) / 0.5)
        cv.text('×', ctr[0], ctr[1] - 4, 90, 'sans_light', col=GOLD_L, a=a * kd * (1 - km))
        cv.text('多因素合奏效应', ctr[0], ctr[1] - 14, 42, 'serif_black', gold=True, a=a * km, shadow=0.8)
        cv.text('LOLLAPALOOZA', ctr[0], ctr[1] + 38, 24, 'corm', col=GOLD_L, a=a * km, track=0.3, shadow=0.8)
        quote_card(cv, 'qauto', t, td + 0.6, S('s18') + 0.1, cy=1225, en_size=25, cn_size=30, w=1000, typing=1.6)
