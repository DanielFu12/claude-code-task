"""开场 v2：真实航拍 + 三维光轨股价、股东大会现场、三维金属柱、立方体阵列——更强的镜头运动与光效。"""
from common import *  # noqa
import media as M, fx
import shaders

_sh = {}
def S3(name):
    if name not in _sh: _sh[name] = Shader(getattr(shaders, name))
    return _sh[name]


def shot_hook(cv, t):
    # ---- 0 → h1：黑场金线心跳 → 横向光晕炸开，转入航拍
    a0 = env(t, 0, S('h1') + 0.5, 0.0, 0.5)
    if a0 > 0:
        L = 460 * eo(t / 1.0)
        hb = math.exp(-max(t - 0.25, 0) * 6) * (t >= 0.25)
        cv.line((W / 2 - L, 960), (W / 2 + L, 960), GOLD, a0 * (0.5 + 0.5 * hb), 2)
        fx.flare(cv, W / 2, 960, a0 * (0.35 + 0.65 * math.exp(-max(t - S('h1') + 0.3, 0) * 2.5) * (t > S('h1') - 0.3)))

    # ---- h1：Apple Park 航拍 + 倾斜平面上的十年光轨（逐一点亮 2026 年的收盘新高）
    t0, t1 = S('h1') - 0.4, S('h2') + 1.1
    a = env(t, t0, t1, 0.6, 0.5)
    if a > 0:
        p = t - t0
        M.full(cv, 'x_park_top', t, t0, t1, z0=1.0, z1=1.12, focus=(0.5, 0.5), dark=0.45, a=a, src_t0=8.3, speed=0.33, cap='Apple Park 航拍', sweep=False)
        tr = WT('h1', '市值')
        rv = eio5(cl((t - t0) / (tr - t0)))
        lay = cv
        r = aapl_chart(lay, t, 110, 980, 960, 1390, reveal=0.02 + 0.98 * rv, a=a, col=GOLD_L, lw=4, show_axis=True)
        recs = [y for y, pp, prev in zip(AA_Y[1:], AA_P[1:], np.maximum.accumulate(AA_P)[:-1]) if y >= 2026 and pp > prev]
        reveal_y = 2016 + (2026.9 - 2016) * (0.02 + 0.98 * rv)
        for y in recs:
            if y <= reveal_y:
                age = (reveal_y - y) * 30
                lay.glow_dot((ax_x(y, 110, 980), ax_y(aa_at(y), 960, 1390)), 8 + 22 * math.exp(-age), GOLD, 0.9 * a)
        if r: lay.glow_dot(r[0], 26 + 10 * beat_pulse(t), WHITE, 0.9 * a)
        cv.text('AAPL', 110, 900, 54, 'oswald', col=CREAM, a=a * eo((p - 0.5) / 0.6), anchor='l', track=0.12, shadow=0.8)
        cv.text('APPLE · 2016—2026', 270, 905, 22, 'corm', col=GOLD, a=a * eo((p - 0.8) / 0.6), anchor='l', track=0.2)
        k = eo((t - tr + 0.3) / 0.45)
        if k > 0:
            chip(cv, '2026 年 25 次收盘新高', 300, 990, 26, a * k, col=GOLD)
            cv.text('$348.91', 830, 900, 64, 'sans_bold', gold=True, a=a * k, glow=0.35, shadow=0.7)
        tm = WT('h1', '五万亿')
        k2 = eo((t - tm + 0.1) / 0.4)
        if k2 > 0:
            v = counter(1.0, 5.0, t, tm - 0.15, 0.9, lambda v: f'${v:.1f} 万亿' if v < 4.99 else '$5 万亿')
            cv.rrect(160, 690, 920, 820, 18, (0.03, 0.03, 0.04), a * k2 * 0.75)
            cv.text('市值', 260, 755, 38, 'sans_med', col=CREAM, a=a * k2, shadow=0.8)
            cv.text(v, W / 2 + 60, 755, 100, 'sans_bold', gold=True, a=a * k2, glow=0.45, scale=1.08 - 0.08 * k2, shadow=0.8)
            fx.flare(cv, W / 2 + 60, 755, a * math.exp(-max(t - tm - 0.75, 0) * 3) * (t > tm + 0.75), length=700)
        fx.dust(cv, t, a * 0.8, seed=1)
    fx.sweep(cv, t, S('h2') + 0.5, 0.8)

    # ---- h2：股东大会现场（推近 + 轻微横移），字距收拢的标题
    t0, t1 = S('h2') + 0.55, WT('h2', '最多时') + 0.2
    a = env(t, t0, t1, 0.45, 0.4)
    if a > 0:
        p = t - t0
        M.full(cv, 'x_bwb_meeting', t, t0, t1, z0=1.0, z1=1.1, focus=(0.55, 0.45), dark=0.15, a=a, src_t0=17.5, speed=0.8, cap='伯克希尔股东大会现场', sweep=False)
        k = eo((p - 0.4) / 1.4)
        cv.text('BERKSHIRE HATHAWAY', W / 2, 960, 50, 'oswald', col=GOLD_L, a=a * k, track=0.6 - 0.45 * k, shadow=0.9, glow=0.15)
        cv.line((W / 2 - 300 * k, 1010), (W / 2 + 300 * k, 1010), GOLD_D, a * k, 2)
        cv.text('伯克希尔·哈撒韦 · 巴菲特执掌 60 年', W / 2, 1065, 30, 'sans_med', col=CREAM, a=a * eo((p - 1.0) / 0.6), shadow=0.8)
        fx.dust(cv, t, a * 0.6, seed=2, drift=(6, -10))

    # ---- h3：三维金属柱：10.1 亿股（2018 峰值）vs 如今 2.28 亿股（右柱塌落、碎光下坠）
    t0, t1 = WT('h2', '最多时') - 0.25, S('h4') + 0.25
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        tk = WT('h2', '如今')
        up = eexp(p / 1.6)
        H1 = 1.3 * up
        drop = eio5(cl((t - tk) / 1.3))
        H2 = lerp(1.3 * up, 1.3 * 0.2257, drop)
        cam = lerp(-0.55, -0.15, eio(p / max(t1 - t0, 1)))
        camr = lerp(10.5, 8.6, eio(p / 4))
        img = S3('BARS')(t=t, cam=cam, camr=camr, h1=H1, h2=H2, ex=1.0, glow2=drop * (1 - drop) * 4, redk=eo(cl((t - tk) / 0.8)))
        fx.layer_over(cv, img, a)
        ro = (math.sin(cam) * camr, 2.0, math.cos(cam) * camr); ta = (0, 1.45, 0)
        x1, y1 = fx.project((0.85, 2 * H1 + 0.35, 0), ro, ta, 2.4)
        x2, y2 = fx.project((-0.85, 2 * H2 + 0.35, 0), ro, ta, 2.4)
        cv.text('2018 峰值', x1, y1 - 70, 26, 'sans_light', col=CREAM, a=a * eo((p - 0.8) / 0.5), shadow=0.8)
        cv.text('10.1亿股', x1, y1 - 20, 56, 'sans_bold', gold=True, a=a * eo((p - 0.6) / 0.5), glow=0.25, shadow=0.8)
        k2 = eo((t - tk - 1.35) / 0.4)                       # 柱子落定后才出标签
        cv.text('2026 年 6 月', x2, y2 - 70, 26, 'sans_light', col=CREAM, a=a * k2, shadow=0.8)
        cv.text('2.28亿股', x2, y2 - 20, 56, 'sans_bold', col=(1.0, 0.45, 0.4), a=a * k2, glow=0.25, shadow=0.8)
        if 0 < drop < 1:                                     # 塌落时的碎光
            rng = np.random.default_rng(int(t * 30))
            xs = x2 + rng.normal(0, 70, 60); ys = y2 + 40 + rng.uniform(0, 500, 60) * drop
            cv.splat(xs, ys, (1.0, 0.5, 0.35), a * 0.8 * math.sin(drop * math.pi), glow=1.5)
        cv.text('伯克希尔持有的苹果股票', W / 2, 330, 40, 'sans_med', col=CREAM, a=a, shadow=0.8)
        fx.dust(cv, t, a * 0.5, seed=3)
    fx.sweep(cv, t, S('h4') - 0.4, 0.7, a=0.8)

    # ---- h4：10×10 立方体（9.16 亿股）：四分之三升起化光 → 套现约 1340 亿美元
    t0, t1 = S('h4') - 0.25, WT('h4', '假如') + 0.25
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        tq = WT('h4', '四分之三')
        lift = cl((t - tq + 0.2) / 2.6)
        sold = cl((t - tq + 0.4) / 0.6)
        cam = 0.5 + p * 0.045
        img = S3('CUBES')(t=t, cam=cam, sold=sold, lift=lift, ex=1.0, frac_=0.75)
        fx.layer_over(cv, img, a)
        cv.rrect(170, 280, 910, 620, 24, (0.02, 0.015, 0.015), a * 0.72)      # 文字底板：升起的方块从其后穿过，不与文字叠在一起
        cv.text('2023 年秋', W / 2, 330, 40, 'sans_med', col=CREAM, a=a, shadow=0.8)
        cv.text('9.16 亿股', W / 2, 420, 84, 'sans_bold', gold=True, a=a * eo((p - 0.3) / 0.5), glow=0.25, shadow=0.8)
        cv.text('每格 ≈ 916 万股', W / 2, 490, 24, 'sans_light', col=GREY, a=a * eo((p - 0.6) / 0.5), shadow=0.8)
        k = eo((t - tq + 0.1) / 0.5)
        cv.text('卖出约 3/4', W / 2, 575, 56, 'serif_black', col=(1.0, 0.5, 0.42), a=a * k, glow=0.25, shadow=0.9)
        tm = WT('h4', '一千三百四十亿')
        k2 = eo((t - tm + 0.1) / 0.4)
        if k2 > 0:
            v = counter(0, 1340, t, tm - 0.1, 1.0, lambda v: f'${v:,.0f}亿')
            cv.rrect(150, 1160, 930, 1380, 24, (0.02, 0.015, 0.015), a * k2 * 0.8)
            cv.text('套现约', W / 2, 1215, 34, 'sans_med', col=CREAM, a=a * k2, shadow=0.8)
            cv.text(v, W / 2, 1310, 118, 'sans_bold', gold=True, a=a * k2, glow=0.45, shadow=0.8, scale=1.06 - 0.06 * k2)
            fx.flare(cv, W / 2, 1310, a * math.exp(-max(t - tm - 1.0, 0) * 3) * (t > tm + 1.0), length=650)
        source(cv, '估算：各季度减持股数 × 当季日均收盘价（税前）；伯克希尔 13F', a, y=1462)
        fx.dust(cv, t, a * 0.5, seed=4)

    # ---- h5 之后沿用原版（假如一股不卖 / 他是巴菲特）
    import common
    if t >= WT('h4', '假如') - 0.4: common.shot_hook_tail(cv, t)
