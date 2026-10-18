"""第三章 · 38年复利账本（买入批次、拆股、市值、股息、回报拆解）"""
from common import *  # noqa

DIV = {int(k): v for k, v in CALC['dividends_by_year'].items()}
DIV[2026] = CALC['annual_dividend_run_rate']        # 2026 全年预计（第 4 季尚未支付）
TR = CALC['tranches']


def shot_ch3(cv, t):
    # ---- s25 / s26：三批买入
    t0, t1 = S('s25') - 0.3, S('s27') - 0.05
    a = env(t, t0, t1, 0.4, 0.35)
    if a > 0:
        p = t - t0
        base_y, x0, x1 = 1060, 140, 940
        cv.line((x0 - 20, base_y), (x1 + 20, base_y), GREY, a, 2)
        items = [(TR[0], '1988', '首次买入', '1,417万股', S('s25') + 0.4),
                 (TR[1], '1989', '继续增持', '+918万股', E('s25') + 0.1),
                 (TR[2], '1994', '最后一次（8月）', '+660万股', WT('s26', '1994') + 0.2)]
        xs = [250, W / 2, 830]
        for (tr, yr, lab, shs, ta), x in zip(items, xs):
            k = eback((t - ta) / 0.7, 1.2)
            if k <= 0: continue
            hpx = tr['add_cost'] / 1e8 * 72 * cl(k, 0, 1.2)
            cv.rrect(x - 95, base_y - hpx, x + 95, base_y, 8, GOLD * 0.75, a, glow=0.15)
            cv.rrect(x - 95, base_y - hpx, x + 95, base_y, 8, GOLD_L, a * 0.8, fill=False, th=2)
            ka = eo((t - ta) / 0.5)
            cv.text(f'${tr["add_cost"] / 1e8:.2f}亿', x, base_y - hpx - 50, 44, 'sans_bold', col=WHITE, a=a * ka)
            cv.text(yr, x, base_y + 50, 40, 'oswald', col=GOLD, a=a * ka)
            cv.text(lab, x, base_y + 100, 26, 'sans_med', col=CREAM, a=a * ka)
            cv.text(shs, x, base_y + 142, 24, 'sans_light', col=GREY, a=a * ka)
        kt = eo((t - WT('s26', '总成本') + 0.1) / 0.5)
        cv.text('总成本', W / 2, 360, 32, 'sans_light', col=CREAM, a=a * kt)
        cv.text('$12.99亿', W / 2, 460, 120, 'sans_bold', gold=True, a=a * kt, glow=0.25)
        cv.text('股数为当时口径；1994 年为 1992 年拆股后的股数', W / 2, 1300, 22, 'sans_light', col=DIM, a=a)
        source(cv, '数据：伯克希尔 1988、1989、1994 年报持仓表；2022 年致股东信（1994 年 8 月完成）', a)
    # ---- s27：拆股 1 → 16，4 亿股，均价 $3.25
    t0, t1 = S('s27') - 0.1, WT('s27', '4亿股') + 0.3
    a = env(t, t0, t1, 0.3, 0.3)
    if a > 0:
        p = t - t0
        span = WT('s27', '4亿股') - S('s27') - 0.5
        step_t = [0.5 + k * span / 4 for k in range(4)]
        n_split = sum(1 for s in step_t if p > s)
        years = ['1990', '1992', '1996', '2012']
        n = 2 ** n_split
        cols, rows = {1: (1, 1), 2: (2, 1), 4: (2, 2), 8: (4, 2), 16: (4, 4)}[n]
        sz = {1: 240, 2: 190, 4: 150, 8: 120, 16: 110}[n]
        gap = sz * 1.25
        pop = math.exp(-max(p - (step_t[n_split - 1] if n_split else 0), 0) * 8) if n_split else 0
        for r in range(rows):
            for c in range(cols):
                x = W / 2 + (c - (cols - 1) / 2) * gap - sz * 0.15
                y = 690 + (r - (rows - 1) / 2) * gap
                cube(cv, x, y, sz * (1 + 0.08 * pop), a)
        cv.text(f'1 股 → {n} 股', W / 2, 290, 64, 'sans_bold', col=WHITE, a=a)
        for k, yr in enumerate(years):
            kk = eo((p - step_t[k]) / 0.3)
            chip(cv, yr + ' 拆股', 180 + k * 240, 1020, 26, a * (0.35 + 0.65 * kk), col=GOLD if kk > 0.5 else GREY)

    # ---- 过渡（s27 结束 → s28）：均价线与股价曲线
    t0, t1 = WT('s27', '4亿股') - 0.1, S('s28') + 0.3
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        x0, x1, y0, y1 = 120, 980, 420, 1180
        ko_chart(cv, t, t0, x0, x1, y0, y1, reveal=eio(p / max(t1 - t0 - 0.6, 1.0)), a=a, col=GOLD)
        lo, hi = math.log(2.0), math.log(110)
        yc = y1 - (math.log(3.247) - lo) / (hi - lo) * (y1 - y0)
        cv.line((x0, yc), (x1, yc), RED, a, 2)
        cv.text('平均成本 $3.25', x1, yc + 30, 26, 'sans_med', col=RED, a=a, anchor='r')
        cv.text('$93.90', x1, y0 - 30, 52, 'sans_bold', col=GOLD_L, a=a * eo((p - 1.8) / 0.4), anchor='r')
        cv.text('4 亿股', 140, 300, 72, 'sans_bold', gold=True, a=a * eo(p / 0.4), anchor='l')
        cv.text('平均成本 $3.25 / 股', 140, 370, 36, 'sans_med', col=CREAM, a=a * eo((p - 0.3) / 0.4), anchor='l')
    # ---- s28：市值揭晓
    t0, t1 = S('s28') - 0.05, S('s29') + 0.1
    a = env(t, t0, t1, 0.15, 0.4)
    if a > 0:
        p = t - t0
        burst = math.exp(-p * 3)
        cv.glow_dot((W / 2, 700), 300, GOLD, a * burst * 0.8)
        rng = np.random.default_rng(9)
        n = 900; ang = rng.uniform(0, 2 * np.pi, n); sp = rng.uniform(200, 900, n)
        r = sp * (1 - math.exp(-p * 2.2))
        cv.splat(W / 2 + np.cos(ang) * r, 700 + np.sin(ang) * r * 1.2, GOLD_L, a * math.exp(-p * 1.2) * 0.8, glow=1.5)
        cv.text('今日市值', W / 2, 470, 40, 'sans_light', col=CREAM, a=a)
        cv.text('$376亿', W / 2, 640, 230, 'sans_bold', gold=True, a=a, glow=0.4, scale=1.06 - 0.06 * eo(p / 0.6))
        k = eo((p - 1.6) / 0.5)
        cv.text('账面浮盈', W / 2 - 220, 900, 34, 'sans_light', col=CREAM, a=a * k)
        cv.text('$363亿', W / 2 - 220, 990, 84, 'sans_light', col=WHITE, a=a * k)
        cv.text('是成本的', W / 2 + 230, 900, 34, 'sans_light', col=CREAM, a=a * k)
        cv.text('28.9 倍', W / 2 + 230, 990, 84, 'sans_light', col=WHITE, a=a * k)
        source(cv, '4 亿股 × $93.90（2026-10-16 收盘）；浮盈未扣税；伯克希尔 13F（2026-06-30）仍持有 4 亿股', a)
    # ---- s29：股息曲线
    t_cum = WT('s29', '38年累计')
    t0, t1 = S('s29') - 0.2, t_cum + 0.25
    a = env(t, t0, t1, 0.3, 0.3)
    if a > 0:
        p = t - t0
        yrs = sorted(DIV)
        x0, x1, yb, hmax = 110, 970, 1180, 620
        bw = (x1 - x0) / len(yrs)
        vmax = 900e6
        for i, y in enumerate(yrs):
            k = eo((p - 0.2 - i * 0.045) / 0.35)
            if k <= 0: continue
            h = DIV[y] / vmax * hmax * k
            colr = GOLD if y != 2026 else GOLD_L
            cv.rect(x0 + i * bw + 2, yb - h, x0 + (i + 1) * bw - 2, yb, colr * (0.55 + 0.45 * i / len(yrs)), a, glow=0.12)
        for y, lab in ((1994, '$0.75亿'), (2022, '$7.04亿'), (2026, '$8.48亿')):
            i = yrs.index(y)
            k = eo((p - 0.4 - i * 0.045) / 0.4)
            xx = x0 + (i + 0.5) * bw; h = DIV[y] / vmax * hmax
            cv.line((xx, yb - h - 10), (xx, yb - h - 70), GOLD_L, a * k, 1)
            cv.text(lab, xx, yb - h - 95, 34 if y == 2026 else 28, 'sans_bold', col=WHITE, a=a * k, anchor='m' if y != 2026 else 'r')
            cv.text(str(y) + ('E' if y == 2026 else ''), xx, yb + 30, 22, 'oswald', col=GREY, a=a * k)
        cv.text('伯克希尔每年收到的可口可乐股息', W / 2, 360, 36, 'sans_med', col=CREAM, a=a)
        k = eo((t - WT('s29', '8.48') - 0.3) / 0.5)
        cv.text('相当于当初成本的 65%/年', W / 2, 450, 52, 'sans_bold', gold=True, a=a * k)
        source(cv, '1994、2022：伯克希尔致股东信；其余按每股股息 × 持股估算；2026 为全年预计（$0.53 × 4）', a)
    # ---- s29 后半：股价回报 vs 股息回报
    t0, t1 = t_cum - 0.15, S('s31') + 0.15
    a = env(t, t0, t1, 0.3, 0.4)
    if a > 0:
        p = t - t0
        yb = 1120; hmax = 640
        for i, (x, val, lab, sub, colr) in enumerate([(330, 363, '股价回报', '未实现浮盈', GOLD), (750, 130, '股息回报', '38 年累计现金', RED)]):
            k = eexp((p - 0.2 - i * 0.8) / 1.0)
            h = val / 380 * hmax * k
            cv.rrect(x - 120, yb - h, x + 120, yb, 10, colr * 0.8, a, glow=0.2)
            cv.text(f'${val * k:.0f}亿', x, yb - h - 60, 70, 'sans_bold', col=WHITE, a=a * eo((p - 0.2 - i * 0.8) / 0.4))
            cv.text(lab, x, yb + 50, 40, 'sans_med', col=colr, a=a)
            cv.text(sub, x, yb + 100, 26, 'sans_light', col=GREY, a=a)
        cv.text('两条回报，分开看', W / 2, 340, 44, 'serif_black', gold=True, a=a)
        source(cv, '股息为保守估算：1988 年股息未计入；股息未再投资（伯克希尔拿现金另作他用）', a)
    # ---- s31：年化不到 10%
    t_dec = WT('s31', '每股利润')
    t0, t1 = S('s31') - 0.2, t_dec + 0.2
    a = env(t, t0, t1, 0.3, 0.3)
    if a > 0:
        p = t - t0
        cv.text('股价年化', W / 2, 470, 44, 'sans_light', col=CREAM, a=a)
        cv.text(f'{counter(0, 9.9, t, t0 + 0.2, 1.4, lambda v: f"{v:.1f}")}%', W / 2, 640, 220, 'sans_light', col=WHITE, a=a)
        k = eo((p - 1.2) / 0.5)
        rows = [('可口可乐 含股息再投资', '12.6%'), ('同期 标普500 含股息', '11.4%')]
        for i, (l, v) in enumerate(rows):
            y = 900 + i * 90
            cv.text(l, 160, y, 34, 'sans_med', col=CREAM, a=a * k, anchor='l')
            cv.text(v, 920, y, 44, 'sans_bold', col=GOLD if i == 0 else GREY, a=a * k, anchor='r')
            cv.line((160, y + 40), (920, y + 40), (0.25, 0.22, 0.2), a * k, 1)
        source(cv, '口径：1988 年下半年均价起至 2026-10-16；数据 Yahoo Finance（KO 复权价、^SP500TR）', a)
    # ---- s31 后半：回报拆解
    t0, t1 = t_dec - 0.1, CH['ch4'][0] + 0.05
    a = env(t, t0, t1, 0.3, 0.4)
    if a > 0:
        p = t - t0
        y = 620
        cells = [('股价', '×34', CREAM, 0.0), ('=', '', GREY, 0.4), ('每股利润', '×16', GOLD, 0.6),
                 ('×', '', GREY, 1.6), ('市盈率', '15→31倍', RED, 1.9)]
        xs = [150, 300, 500, 690, 870]
        for (lab, val, colr, d), x in zip(cells, xs):
            k = eo((p - d) / 0.5)
            if val:
                cv.text(val, x, y, 76 if len(val) <= 3 else 58, 'sans_bold', col=colr, a=a * k)
                cv.text(lab, x, y + 90, 32, 'sans_med', col=CREAM, a=a * k)
            else:
                cv.text(lab, x, y, 70, 'sans_light', col=colr, a=a * k)
        k = eo((p - 3.6) / 0.6)
        cv.text('复利，靠的是生意本身', W / 2, 950, 64, 'serif_black', gold=True, a=a * k, glow=0.3)
        source(cv, '1988：年末股价 $2.79、持续经营 EPS $0.185（复权口径，KO 1998 10-K）；2025：摊薄 EPS $3.04（KO 2025 10-K）', a)
