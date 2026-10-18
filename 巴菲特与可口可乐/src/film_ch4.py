"""第四章 · 他为什么不卖（泡沫、16 年、机会成本、持有的条件）"""
from common import *  # noqa

B = CALC['bubble']


def tr_series(Y, V, start):
    m = Y >= start
    return Y[m], V[m] / V[m][0]


def shot_ch4(cv, t):
    # ---- s34：并不平坦
    t0, t1 = max(S('s34') - 0.6, CH['ch4'][0] + 2.0), S('s35') + 0.3
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        ko_chart(cv, t, t0, 120, 980, 520, 1180, reveal=1.0, a=a * 0.8, col=RED)
        cv.text('并不平坦', W / 2, 340, 110, 'serif_black', col=CREAM, a=a * eo(p / 0.6))
    # ---- s35：1998 泡沫 → 16 年
    t0, t1 = S('s35') - 0.1, S('s37') + 0.1
    a = env(t, t0, t1, 0.3, 0.4)
    if a > 0:
        p = t - t0
        x0, x1, y0, y1 = 120, 980, 700, 1250
        yf, yt = 1994.0, 2017.0
        r = ko_chart(cv, t, t0, x0, x1, y0, y1, y_from=yf, y_to=yt, reveal=1.0, a=a, col=RED, log=False,
                     tip_label=False)
        P = KO_P[(KO_Y >= yf) & (KO_Y <= yt)]
        hi = P.max() * 1.1
        px = x0 + (PEAK98 - yf) / (yt - yf) * (x1 - x0)
        py = y1 - B['peak_close_now_basis'] / hi * (y1 - y0)
        # 泡沫：一个膨胀的玻璃球，随后破裂
        k = eio(p / 1.8); pop = p - 2.2
        if pop < 0:
            R = 40 + 120 * k
            cv.circle((px, py), R, GOLD_L, a * 0.8, 2)
            cv.glow_dot((px - R * 0.35, py - R * 0.35), R * 0.25, WHITE, a * 0.25)
            cv.text('市盈率 47 倍', px + R + 20, py - 20, 44, 'sans_bold', col=GOLD_L, a=a * k, anchor='l')
            cv.text('1998 年末', px + R + 20, py + 30, 26, 'sans_light', col=GREY, a=a * k, anchor='l')
        else:
            rng = np.random.default_rng(4)
            n = 400; ang = rng.uniform(0, 2 * np.pi, n); sp = rng.uniform(150, 450, n)
            rr = 160 + sp * (1 - math.exp(-pop * 3))
            cv.splat(px + np.cos(ang) * rr, py + np.sin(ang) * rr + pop * pop * 200, GOLD_L, a * math.exp(-pop * 1.5), glow=1.2)
            # 16 年回本线
            rx = x0 + (2014 + 281 / 366 - yf) / (yt - yf) * (x1 - x0)
            L = eio((pop - 0.3) / 1.6)
            cv.line((px, py), (px + (rx - px) * L, py), GOLD, a, 2)
            if L > 0.98:
                cv.glow_dot((rx, py), 12, GOLD_L, a)
            k2 = eo((pop - 1.6) / 0.5)
            by = py - 110
            cv.line((px, by), (rx, by), GOLD_L, a * k2, 2)
            cv.line((px, by - 15), (px, by + 15), GOLD_L, a * k2, 2); cv.line((rx, by - 15), (rx, by + 15), GOLD_L, a * k2, 2)
            cv.text('16 年', (px + rx) / 2, by - 50, 80, 'sans_bold', col=WHITE, a=a * k2)
            cv.text('1998.7 → 2014.10 股价才回到高点', (px + rx) / 2, by - 115, 26, 'sans_light', col=CREAM, a=a * k2)
        cv.text('伯克希尔这笔持仓市值', W / 2, 220, 32, 'sans_light', col=CREAM, a=a)
        cv.text('$134亿 → $81亿', W / 2, 300, 84, 'sans_bold', col=RED, a=a * eo((p - 0.6) / 0.5))
        cv.text('1998 年末 → 2005 年末', W / 2, 368, 26, 'sans_light', col=GREY, a=a * eo((p - 0.6) / 0.5))
        source(cv, '市盈率：KO 1998 10-K（年末价 $67.00 ÷ 摊薄 EPS $1.42）；市值：伯克希尔 1998 年报、2005 年致股东信', a)
    # ---- s37：坦承错误
    quote_card(cv, 'q2003', t, S('s37') - 0.3, S('s38') + 0.1, cy=560, en_size=32, cn_size=36)
    t0, t1 = S('s37') + 1.2, S('s38') + 0.1
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        p = t - t0
        clear_glow(cv, 40, 950, W - 40, 1200, a)
        cv.text('“I talked when I should have walked.”', W / 2, 1000, 44, 'typewriter', col=GOLD_L, a=a, reveal=eio(p / 1.4), shadow=0.7)
        cv.text('我只是说了，却没有做。', W / 2, 1090, 56, 'serif_black', col=CREAM, a=a * eo((p - 1.2) / 0.5))
        cv.text('Warren Buffett · 2004 Chairman’s Letter', W / 2, 1170, 24, 'corm', col=GOLD, a=a * eo((p - 1.4) / 0.5))
    # ---- s38：机会成本
    t0, t1 = S('s38') - 0.3, S('s39') + 0.1
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        x0, x1, y0, y1 = 140, 960, 480, 1180
        ky, kv = tr_series(KO_Y, KO_A, PEAK98)
        sy, sv = tr_series(SP_Y, SP_V, PEAK98)
        rev = eio((p - 0.3) / 3.2)
        lo, hi = math.log(0.6), math.log(13)
        for Y, V, colr, lab, fin in ((sy, sv, GREY, '标普500（含股息）', B['sp_tr_since_peak']),
                                     (ky, kv, RED, '可口可乐（含股息）', B['ko_tr_since_peak'])):
            xs = x0 + (Y - PEAK98) / (2026.8 - PEAK98) * (x1 - x0)
            ys = y1 - (np.log(V) - lo) / (hi - lo) * (y1 - y0)
            n = max(2, int(len(xs) * rev)); st = max(1, n // 700)
            pts = np.stack([xs[:n:st], ys[:n:st]], 1)
            cv.poly(pts, colr, a, 3)
            if rev > 0.97:
                # 标普标签在线上方；可口可乐标签放到红线下方的空白处（不压线）
                cv.text(f'×{fin:.1f}', xs[-1] - 6, ys[-1] + (-42 if colr is GREY else 190), 52, 'sans_bold', col=colr if colr is not GREY else WHITE, a=a, anchor='r', shadow=0.7)
                cv.text(lab, xs[-1] - 6, ys[-1] + (-100 if colr is GREY else 248), 26, 'sans_med', col=colr, a=a, anchor='r', shadow=0.7)
        cv.line((x0, y1 - (0 - lo) / (hi - lo) * (y1 - y0)), (x1, y1 - (0 - lo) / (hi - lo) * (y1 - y0)), DIM, a * 0.6, 1)
        cv.text('1998.7 高点买入，持有至今', W / 2, 330, 36, 'sans_med', col=CREAM, a=a)
        cv.text('机会成本', W / 2, 410, 64, 'serif_black', gold=True, a=a * eo((p - 3.4) / 0.5))
        source(cv, '口径：1998-07-14 收盘 → 2026-10-16 收盘；KO 复权价、^SP500TR（Yahoo Finance）', a)
    # ---- s39：那他为什么还不卖？
    t0, t1 = S('s39') - 0.25, S('s40') + 0.1
    a = env(t, t0, t1, 0.2, 0.3)
    if a > 0:
        cv.text('那他为什么', W / 2, 760, 96, 'serif_black', col=CREAM, a=a)
        cv.text('还不卖？', W / 2, 900, 130, 'serif_black', gold=True, a=a, glow=0.3)
    # ---- s40：生意没有变坏
    t0, t1 = S('s40') - 0.2, S('s41') + 0.1
    a = env(t, t0, t1, 0.3, 0.3)
    if a > 0:
        p = t - t0
        n = 64
        x0, x1, yb = 110, 970, 1100
        bw = (x1 - x0) / n
        for i in range(n):
            k = eo((p - 0.1 - i * 0.03) / 0.25)
            h = (40 + 520 * (i / n) ** 1.6) * k
            cv.rect(x0 + i * bw + 1, yb - h, x0 + (i + 1) * bw - 1, yb, GOLD * (0.45 + 0.55 * i / n), a)
        cv.text(counter(0, 64, t, t0 + 0.1, 2.0, lambda v: f'{v:.0f}'), 200, 420, 200, 'sans_bold', gold=True, a=a, anchor='l', glow=0.25)
        cv.text('连续 64 年提高股息', 420, 430, 44, 'sans_med', col=CREAM, a=a, anchor='l')
        cv.text('2026 年：每股 $2.12', 420, 490, 30, 'sans_light', col=GREY, a=a, anchor='l')
        k = eo((p - 2.6) / 0.5)
        cv.text('2025 年每股收益 $3.04 · 利润仍在增长', W / 2, 1200, 34, 'sans_med', col=GOLD_L, a=a * k)
        source(cv, '数据：可口可乐 2025 年 10-K', a)
    # ---- s41：卖出的代价 vs 替代品
    t0, t1 = S('s41') - 0.2, S('s42') + 0.1
    a = env(t, t0, t1, 0.3, 0.3)
    if a > 0:
        p = t - t0
        for i, (x, title, big, sub, colr) in enumerate([(290, '如果卖出', '≈$76亿', '按 21% 联邦企业所得税\n估算的税款', RED),
                                                        (790, '换成什么？', '极少', '同样优秀、能长期\n持有的企业', GOLD)]):
            k = eo((p - 0.2 - i * 0.9) / 0.5)
            cv.rrect(x - 220, 520, x + 220, 1080, 22, (0.06, 0.05, 0.05), a * k * 0.9)
            cv.rrect(x - 220, 520, x + 220, 1080, 22, colr, a * k * 0.7, fill=False, th=2)
            cv.text(title, x, 600, 40, 'sans_med', col=CREAM, a=a * k)
            cv.text(big, x, 780, 96, 'sans_bold', col=colr, a=a * k, glow=0.2)
            for j, l in enumerate(sub.split('\n')):
                cv.text(l, x, 930 + j * 44, 28, 'sans_light', col=GREY, a=a * k)
        source(cv, '本片估算：$363亿未实现收益 × 21%；实际税负取决于税法与州税，并非巴菲特原话', a)
    # ---- s42：持有是有条件的（阿贝尔 2025 年报致股东信）
    t0, t1 = S('s42') - 0.3, CH['ch5'][0] + 0.05
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        if os.path.exists(os.path.join(ROOT, 'assets', 'archive', 'buffett_2015.jpg')):
            photo(cv, 'buffett_2015', t, t0, t1, W / 2, 470, 560, 420, z0=1.05, z1=1.15, mode='bw', fi=0.5, fo=0.5)
            cv.text('Warren Buffett, 2015 · 美国国际贸易管理局（公有领域）', W / 2, 700, 18, 'sans_light', col=DIM, a=a)
        quote_card(cv, 'qabel', t, t0 + 0.6, t1, cy=1000, en_size=32, cn_size=38, a=1.0)
        k = eo((p - 6.2) / 0.5)
        cv.text('持有，是有条件的', W / 2, 1290, 52, 'serif_black', gold=True, a=a * k, glow=0.25)
