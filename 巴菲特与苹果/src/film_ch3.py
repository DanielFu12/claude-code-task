"""第三章 · 十年账本（一半的仓位 → 2020 的小卖 → 真正的减持 → 交棒 → 总账 → 与标普 500 对比）"""
from common import *  # noqa
import media as M


def donut(cv, cx, cy, R, frac, a, col=GOLD, th=40, label=None):
    cv.arc((cx, cy), R, -math.pi / 2, 3 * math.pi / 2, (0.2, 0.2, 0.22), a, th)
    if frac > 0: cv.arc((cx, cy), R, -math.pi / 2, -math.pi / 2 + 2 * math.pi * frac, col, a, th)
    if label: cv.text(label, cx, cy, 96, 'sans_bold', gold=True, a=a, glow=0.25)


def shot_ch3(cv, t):
    # ---- c3a：好生意 + 好价格
    t0, t1 = win('c3a')
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        M.full(cv, 'v_omaha_drone', t, t0, t1, z0=1.0, z1=1.06, dark=0.35, a=a, src_t0=200.0, cap='奥马哈航拍')
        headline(cv, '好生意 + 好价格', 860, a, 80, k=eo((t - t0 - 0.3) / 0.6))
    # ---- c3b：2023 年底市值约 1743 亿，几乎占股票投资的一半
    t0, t1 = win('c3b')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        k = eio((t - WT('c3b', '一半') + 1.2) / 1.4)
        donut(cv, W / 2, 800, 270, 0.49 * k, a, label=f'{49 * k:.0f}%')
        cv.text('2023 年底 · 伯克希尔股票投资组合', W / 2, 420, 36, 'sans_med', col=CREAM, a=a)
        k2 = eo((t - WT('c3b', '一千七百四十三亿') + 0.1) / 0.5)
        cv.text('苹果 $1743亿 / 全部 $3538亿', W / 2, 1160, 46, 'sans_bold', col=GOLD_L, a=a * k2)
        source(cv, '伯克希尔 2023 年报 K-84/85', a, y=1392)
    # ---- c3c：2020 年小卖 110 亿；“那是个愚蠢的决定”
    t0, t1 = win('c3c')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        M.full(cv, 'x_bwbi_c', t, t0, t1, z0=1.0, z1=1.08, focus=(0.42, 0.42), dark=0.45, a=a)
        k = eo((t - WT('c3c', '一百一十亿') + 0.1) / 0.5)
        cv.text('2020 · 卖出一小部分 · 落袋 $110亿', W / 2, 400, 40, 'sans_med', col=CREAM, a=a * k, shadow=0.8)
        quote_card(cv, 'q2023c', t, WT('c3c', '三年后') - 0.3, t1, cy=1250, en_size=34, cn_size=40, a=a)
    # ---- c3d–c3f：持股曲线（真正的减持 → 2024Q2 → 只剩 2.28 亿股 → 交棒）
    t0, t1 = S('c3d') - 0.3, S('c3g') + 0.1
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        p = t - t0
        rv = lerp(0.72, 1.0, eio((t - S('c3d')) / max(WT('c3f', '只剩') - S('c3d'), 1)))
        q2 = lambda y: 2024.25 <= y < 2024.5
        hl = q2 if t >= WT('c3e', '二零二四') - 0.2 else None
        holdings_chart(cv, t, 160, 980, 560, 1150, reveal=rv, a=a, hl=hl)
        cv.text('伯克希尔持有的苹果（亿股，季度末）', W / 2, 440, 34, 'sans_med', col=CREAM, a=a)
        k = eo((t - WT('c3e', '三点八九亿') + 0.1) / 0.5)
        if k > 0:
            cv.text('2024 Q2：一个季度卖出 3.89 亿股', W / 2, 510, 40, 'sans_bold', col=RED, a=a * k, shadow=0.6)
        k2 = eo((t - WT('c3f', '两点二八亿') + 0.1) / 0.5)
        cv.text('2.28 亿股', W / 2 + 280, 1060, 40, 'sans_bold', col=CREAM, a=a * k2)
        k3 = eo((t - WT('c3f', '格雷格') + 0.1) / 0.6)
        if k3 > 0:
            cv.rrect(140, 1210, 940, 1360, 16, (0.05, 0.05, 0.06), a * k3 * 0.9)
            cv.text('2026 · 格雷格·阿贝尔 出任 CEO', W / 2, 1255, 38, 'sans_med', col=GOLD_L, a=a * k3)
            cv.text('巴菲特留任董事长 · 2026 年两季持仓未变', W / 2, 1315, 30, 'sans_light', col=CREAM, a=a * k3)
        source(cv, '伯克希尔 13F（2016Q1–2026Q2）；伯克希尔 2025 年致股东信（署名 Gregory E. Abel, CEO）', a, y=1440)
    # ---- c3g–c3h：总账：买入 410 亿 → 合计 2300 亿（5.6 倍）
    t0, t1 = S('c3g') - 0.3, S('c3i') + 0.1
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('十年总账（估算 · 税前）', W / 2, 400, 40, 'sans_med', col=CREAM, a=a)
        base = 1250; sc = 650 / 2300
        x_in, x_out = 300, 760
        k = eexp((t - WT('c3g', '四百一十亿') + 0.2) / 0.8)
        cv.rect(x_in - 110, base - 410 * sc * k, x_in + 110, base, GREY * 0.8, a)
        cv.text('$410亿', x_in, base - 410 * sc * k - 44, 44, 'sans_bold', col=CREAM, a=a * k)
        cv.text('累计买入', x_in, base + 40, 28, 'sans_light', col=GREY, a=a * k)
        y = base
        for lab, v, col, w_ in [('卖出所得', 1470, GOLD * 0.75, '卖出所得'), ('股息', 60, GOLD_L, '股息'), ('剩余持股', 770, GOLD, '剩下的股票')]:
            kk = eexp((t - WT('c3h', w_) + 0.2) / 0.7)
            if kk <= 0: continue
            h = v * sc * kk
            cv.rect(x_out - 110, y - h, x_out + 110, y, col, a, glow=0.1)
            cv.text(f'{lab} ${v}亿', x_out - 130, y - h / 2, 28, 'sans_med', col=CREAM, a=a * kk, anchor='r')
            y -= h
        k2 = eo((t - WT('c3h', '五点六倍') + 0.1) / 0.5)
        if k2 > 0:
            cv.text('$2300亿', x_out, y - 50, 52, 'sans_bold', gold=True, a=a * k2, glow=0.3)
            cv.text('× 5.6', W / 2 - 60, 600, 120, 'oswald', col=GOLD_L, a=a * k2, glow=0.3)
        source(cv, 'data/calc.py：各季度持股变动 × 当季日均价；股息按每股股息 × 持股；剩余 2.28 亿股 × $338.32', a, y=1392)
    # ---- c3i：年化约 29% vs 标普 500 约 15%
    t0, t1 = win('c3i', post=0.0)
    t1 = CH['ch4'][0] + 0.2
    a = env(t, t0, t1, 0.4, 0.5)
    if a > 0:
        import fx
        fx.bars3d(cv, t, t0, t1, ('苹果（资金加权）', 29.2, '29%', WT('c3i', '百分之二十九') - 0.2),
                  ('标普 500（含股息）', 14.8, '15%', WT('c3i', '百分之十五') - 0.2), a=a, title='年化回报 · 同样的钱、同样的时间')
        k = eo((t - WT('c3i', '一千三百九十亿') + 0.1) / 0.5)
        cv.text('同额买入标普并持有至今 ≈ $1390亿', W / 2, 1270, 32, 'sans_med', col=CREAM, a=a * k, shadow=0.8)
        k2 = eo((t - WT('c3i', '两倍') + 0.1) / 0.4)
        cv.text('≈ 2 倍', W / 2, 1360, 90, 'serif_black', gold=True, a=a * k2, glow=0.35, shadow=0.8)
        source(cv, '年化 = 内部收益率（按每季度买卖与股息的实际时间，估算，税前）；标普 500 全收益指数 ^SP500TR', a, y=1392)
