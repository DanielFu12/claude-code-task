"""第二幕「下山 · 恐惧」+ 镜子。"""
from common import *  # noqa
from scenes_a import (MT_P, MT_COL, MT_A, MT_EDGE, SUMMIT, draw_star_chart, draw_flywheel, CO_X, CO_Y, CO_P, eio_np,
                      polyline_upto)


def chapter_stamp(f, t, t0, t1, num, name, sub, y=150, big=False):
    a = env(t, t0, t1, 0.4, 0.5)
    if a <= 0.003: return
    if big:
        f.text(num, W / 2, 330, 40, 'corm_sb', GOLD, a, 'm', track=0.4, mode='O', t0=t0, stag=0.05, dur=0.4)
        f.text(name, W / 2, 440, 140, 'serif_black', INK, a, 'm', track=0.35, mode='O', t0=t0, stag=0.08, dur=0.5,
               rise=30)
        f.text(sub, W / 2, 560, 26, 'serif_med', GREY, a, 'm', track=0.3, mode='O', t0=t0 + 0.3, stag=0.03, dur=0.4)
        ln = 260 * eo((t - t0) / 0.8)
        f.line((W / 2 - ln, 515), (W / 2 + ln, 515), GOLD, a * 0.6, 1, buf='L')
    else:
        f.text(f'{num}  {name}', W / 2, y, 30, 'serif_black', INK, a, 'm', track=0.3, mode='O', t0=t0, stag=0.04)
        f.text(sub, W / 2, y + 40, 15, 'sans_med', GOLD, a * 0.9, 'm', track=0.4, mode='O', t0=t0 + 0.2, stag=0.02)


def s_stamp1(f, t):
    if 23.2 < t < 26.2:
        chapter_stamp(f, t, 23.55, 25.6, '01', '上山', '贪婪是怎样炼成的', y=150)


# ======================================================================== 崩塌
_r = np.random.default_rng(101)
_N = len(MT_P)
EX_V = (MT_P - [SUMMIT[0], SUMMIT[1] + 60]) / 240.0
EX_V = EX_V / np.maximum(np.linalg.norm(EX_V, axis=1, keepdims=True), 0.3) * (_r.random(_N)[:, None] ** 0.5 * 900 + 120)
EX_V[:, 1] -= _r.random(_N) * 500
EX_V *= 2.2
EX_COL = mixc(MT_COL, DOWN2, 0.75)


def s_crash(f, t):
    if not (T_D2 - 0.05 <= t <= 99.5): return
    x = t - T_D2
    # 山崩：粒子炸开后在重力下坠落
    if x < 4.0:
        drag = (1 - math.exp(-x * 2.2)) / 2.2
        P = MT_P + EX_V * drag + np.array([0, 1]) * 1400 * max(0, x - 0.12) ** 2
        k = cl(x / 0.4)
        col = mixc(MT_COL, EX_COL, k)
        A = MT_A * (1 - eio(x / 2.4)) * 1.3
        f.splat(P[:, 0], P[:, 1], col, A)
        if x < 1.2:
            r = 1800 * eo(x / 1.2)
            f.circle((SUMMIT[0], SUMMIT[1]), r, DOWN2, (1 - x / 1.2) * 0.8, 3)
            f.circle((SUMMIT[0], SUMMIT[1]), r * 0.7, WHITE, (1 - x / 1.2) * 0.4, 1)
    chapter_stamp(f, t, T_D2 + 0.05, 95.2, '02', '下山', '恐惧如何接管你', big=True)
    # 2026 科技股：7 月掉头，10 月 8 日科创50 −4.82%
    a = env(t, 95.1, 98.6, 0.6, 0.5)
    if a > 0.003:
        day = keys(t, [(95.2, 181), (98.0, 280)], eio)
        draw_star_chart(f, t, a, day, [
            (96.0, 196, ['7 月：科创50 半个月跌约 11%', '存储、光通信龙头较高点回撤超 30%'], 'down', DOWN2),
            (97.6, 279, ['10.8 单日 −4.82%', '长假后首个交易日'], 'up', DOWN2),
        ])


narr(95.15, 96.6, '科创50 也一样：7 月掉头向下，')
narr(96.7, 98.5, '10 月 8 日，单日又跌 4.82%。')


# ======================================================================== 反身性倒转 + 2015
# 上证指数 2014.7–2015.9 示意（标注点为真实数据）
_m = np.linspace(0, 14, 300)
SH15 = np.interp(_m, [0, 3, 5, 6, 8, 9, 10.5, 11.25, 11.6, 12.0, 12.6, 13.2, 14],
                 [2050, 2400, 3200, 3300, 4000, 4400, 5178, 3507, 3700, 4000, 3600, 2850, 3100])
SH15 = SH15 * (1 + smooth_noise(300, 7, 5) * 0.025)
SH15[int(10.5 / 14 * 299)] = 5178
MG15 = np.interp(_m, [0, 3, 6, 8, 10.6, 11.4, 12.5, 14], [0.42, 0.7, 1.1, 1.6, 2.27, 1.45, 1.2, 0.9])


def s_spiral_down(f, t):
    if not (98.2 <= t <= 106.8): return
    a = env(t, 98.5, 105.95, 0.5, 0.35)
    k = eio((t - 101.0) / 0.9)
    cx = lerp(960, 560, k)
    heat = cl((t - 98.6) / 6.0)
    draw_flywheel(f, t, a, [('价格下跌', ''), ('更多卖出', ''), ('强制平仓', '恐慌抛售'), ('账面亏损', '保证金告急')],
                  DOWN, C(200, 255, 235), 98.6, 0.6, 7.0, 7.0, sign=-1, heat=heat, center=(cx, 520),
                  R=lerp(220, 190, k))
    ca = a * k
    if ca <= 0.003: return
    x0, x1, y0, y1 = 950, 1730, 300, 760
    def yv(v): return y1 - (v - 1800) / (5400 - 1800) * (y1 - y0)
    xs = x0 + (x1 - x0) * _m / 14
    u = eo((t - 101.2) / 2.8)
    f.text('上证指数 2014.7–2015.9 · 示意', x0, y0 - 40, 16, 'sans_med', INK, ca * 0.8, 'l', mode='O')
    f.line((x0, y1 + 8), (x1, y1 + 8), WHITE, 0.2 * ca, 1, buf='L')
    pts, head = polyline_upto(xs, yv(SH15), u)
    draw_price(f, pts, ca, 2, smooth=9)
    f.disc(head, 4, WHITE, ca)
    mp, _ = polyline_upto(xs, y1 - MG15 / 2.5 * (y1 - y0) * 0.55, u)
    f.poly(mp, GOLD, ca * 0.55, 1)
    if u > 0.75:
        i = int(10.5 / 14 * 299); px, py = xs[i], yv(SH15[i])
        ka = ca * cl((u - 0.75) / 0.06)
        f.disc((px, py), 5, UP, ka); f.circle((px, py), 12, UP, ka * 0.6, 1)
        f.text('2015.6.12  5178 点', px - 14, py - 26, 18, 'mono_med', UP2, ka, 'r', mode='O')
        f.text('融资余额 6.18 达 2.27 万亿元', px - 14, py + 2, 14, 'sans_med', GOLD, ka, 'r', mode='O')
    if u > 0.93:
        i = int(13.2 / 14 * 299); px, py = xs[i], yv(SH15[i])
        ka = ca * cl((u - 0.93) / 0.05)
        f.disc((px, py), 5, DOWN, ka); f.circle((px, py), 12, DOWN, ka * 0.6, 1)
        f.text('8 月下旬 跌破 3000 点', px, py + 34, 18, 'sans_bold', DOWN2, ka, 'm', mode='O')
    f.text('— 融资余额', x1, y0 - 40, 13, 'sans_med', GOLD, ca * 0.7, 'r', mode='O')


narr(98.7, 100.9, '飞轮倒转：下跌、平仓、再下跌。')
narr(101.1, 103.2, '上一次杠杆牛市：2015 年，沪指 5178 点。')
narr(103.3, 104.9, '两个半月后，跌破 3000 点。')
narr(104.95, 106.35, '杠杆不改方向，只放大速度。')


# ======================================================================== 损失厌恶
def s_loss_aversion(f, t):
    if not (106.2 <= t <= 117.3): return
    a = env(t, 106.45, 116.9, 0.5, 0.4)
    scene_tag(f, t, 106.5, '损失厌恶', 'LOSS AVERSION · KAHNEMAN & TVERSKY', 116.8)
    # 天平
    ba = a * (1 - eio((t - 110.4) / 0.6))
    if ba > 0.003:
        piv = np.array([960.0, 430.0])
        drop = eback((t - 107.0) / 0.9, 2.2) * 15
        lev = eio((t - 108.9) / 1.0)
        ang = math.radians(drop * (1 - lev))
        L = 360
        d = np.array([math.cos(ang), math.sin(ang)])
        pl, pr = piv - d * L, piv + d * L
        f.line(pl, pr, GOLD, ba, 3)
        f.fillpoly([(piv[0], piv[1]), (piv[0] - 40, piv[1] + 300), (piv[0] + 40, piv[1] + 300)], GOLD, 0.10 * ba)
        f.line(piv, (piv[0] - 40, piv[1] + 300), GOLD, ba * 0.6, 1)
        f.line(piv, (piv[0] + 40, piv[1] + 300), GOLD, ba * 0.6, 1)
        f.disc(piv, 7, GOLDL, ba)
        gain = round((1000 + 1250 * eo((t - 108.9) / 1.0)) / 10) * 10
        for p, s, col, sub in ((pl, f'+{gain:,.0f} 元', UP, '赚到的快乐'), (pr, '−1,000 元', DOWN, '亏掉的痛苦')):
            f.line(p, p + [-70, 120], col, ba * 0.7, 1); f.line(p, p + [70, 120], col, ba * 0.7, 1)
            f.arc(p + [0, 120], 90, 0, math.pi, col, ba, 2)
            f.line(p + [-90, 120], p + [90, 120], col, ba, 2)
            f.text(s, p[0], p[1] + 252, 34, 'mono_med', col, ba, 'm', mode='O')
            f.text(sub, p[0], p[1] + 292, 17, 'sans_med', GREY, ba, 'm', mode='O')
        f.text('同样 1000 元，亏损的痛苦 ≈ 盈利快乐的 2 倍', 960, 300, 26, 'serif_bold', INK,
               ba * cl((t - 107.6) / 0.5), 'm', mode='O')
        f.text('Tversky & Kahneman (1992) 估计的损失厌恶系数约为 2.25', 960, 850, 13, 'sans_light', GREY,
               ba * cl((t - 108.0) / 0.5), 'm', mode='O')
    # 扛到极限，在底部割肉
    ca = a * eio((t - 110.6) / 0.6)
    if ca <= 0.003: return
    xs = np.linspace(260, 1500, 300)
    v = np.interp(xs, [260, 420, 560, 760, 980, 1180, 1260, 1500], [330, 300, 380, 470, 590, 760, 770, 560])
    v = v + smooth_noise(300, 17, 5) * 12
    u = cl((t - 110.8) / 4.1) * 0.86 + 0.14 * eo((t - 115.2) / 1.6)
    pts, head = polyline_upto(xs, v, u)
    draw_price(f, pts[:int(0.86 * 300) + 1] if u > 0.86 else pts, ca, 3, smooth=9)
    if u > 0.86:
        gp = pts[int(0.86 * 300):]
        for i in range(0, len(gp) - 1, 2):
            f.line(gp[i], gp[i + 1], UP, ca * 0.7, 2)
        f.text('然后……反弹', head[0] + 14, head[1] - 20, 20, 'serif_bold', UP2, ca * cl((t - 115.6) / 0.4), 'l',
               mode='O')
    # 你
    if t < 114.92:
        yp = head
        f.text('死扛', yp[0] + 16, yp[1] - 30, 18, 'serif_bold', INK, ca * cl((t - 111.4) / 0.4), 'l', mode='O')
        draw_you(f, yp[0], yp[1], ca, WHITE, '你', t, 5, True, lab_dy=30)
    else:
        i = int(0.86 * 299); yp = np.array([xs[i], v[i]])
        k = (t - 114.92) / 1.2
        draw_you(f, yp[0] + 30 * k, yp[1] + 120 * eio(k), ca * (1 - cl(k)), DOWN, '你', t, 5, False, lab_dy=30)
        f.text('割肉', yp[0] - 16, yp[1] + 34, 26, 'serif_black', DOWN2, ca * env(t, 114.95, 116.6, 0.2, 0.4), 'r',
               mode='O')
        f.circle(yp, 20 + 60 * eo(k), DOWN, ca * (1 - cl(k)), 2)
    # 痛苦计
    gx, gy0, gy1 = 1680, 300, 760
    pain = cl((t - 110.9) / 4.0) ** 1.6
    f.text('痛苦', gx, gy0 - 30, 18, 'serif_bold', INK, ca, 'm', mode='O')
    f.rrect(gx - 16, gy0, gx + 16, gy1, 14, WHITE, ca * 0.3, 1, buf='L')
    fy = gy1 - (gy1 - gy0) * pain
    f.rrect_fill(gx - 12, fy, gx + 12, gy1 - 4, 10, mixc(GOLD, DOWN, pain), ca * 0.85, 'E')
    ly = gy0 + 40
    f.dashed((gx - 40, ly), (gx + 40, ly), WHITE, ca * 0.7, 1, 5, 4)
    f.text('忍耐极限', gx - 46, ly, 14, 'sans_med', GREY, ca, 'r', mode='O')


narr(108.54, 110.6, '同样 1000 元，亏的痛苦约是赚的快乐的两倍。')
narr(110.67, 112.7, '于是我们：赚一点就跑，亏了就扛。')
narr(112.79, 114.8, '扛到痛苦越过极限——')
narr(114.92, 116.9, '在离底部最近的地方，交出筹码。')


# ======================================================================== 回本的数学
def s_asym(f, t):
    if not (116.8 <= t <= 123.8): return
    a = env(t, 117.02, 123.3, 0.4, 0.4)
    base = 600
    f.line((260, base), (1660, base), WHITE, 0.25 * a, 1, buf='L')
    pairs = [(10, 11.1), (30, 42.9), (50, 100), (80, 400)]
    for i, (dn, up) in enumerate(pairs):
        t0 = 117.15 + i * 1.06
        k1 = eo((t - t0) / 0.45); k2 = eo((t - t0 - 0.45) / 0.6)
        x = 420 + i * 360
        hd = dn * 3.0 * k1
        f.rrect_fill(x - 60, base, x - 8, base + hd, 3, DOWN, 0.8 * a, 'E')
        f.text(f'−{dn}%', x - 34, base + hd + 26, 24, 'mono_med', DOWN2, a * k1, 'm', mode='O')
        hu = min(up * 3.0 * k2, 450)
        f.rrect_fill(x + 8, base - hu, x + 60, base, 3, UP, 0.8 * a, 'E')
        if up * 3 > 450 and k2 > 0.8:
            for j in range(3):
                yy = base - 450 - 14 - j * 16
                f.line((x + 20, yy + 8), (x + 34, yy), UP, a * (0.9 - j * 0.25), 2)
                f.line((x + 48, yy + 8), (x + 34, yy), UP, a * (0.9 - j * 0.25), 2)
        f.text(f'+{up:.0f}%', x + 34, base - hu - (60 if up * 3 > 450 else 26), 26 if up < 100 else 32, 'mono_med', UP2,
               a * k2, 'm', mode='O')
        f.text(f'跌 {dn}%  →  要涨 {up:.0f}% 才回本', x, base + 300 - 50, 15, 'sans_med', GREY, a * k2, 'm', mode='O')


narr(117.1, 119.0, '跌 50%，要涨 100% 才能回本。')
narr(119.15, 123.3, '买在山顶的代价，往往不是一次下跌，而是很多年。')


# ======================================================================== 三座山顶
def _petro(u):
    return np.interp(u, [0, 0.02, 0.06, 0.12, 0.2, 0.35, 0.5, 0.65, 0.8, 1], [48.6, 44, 30, 18, 13, 10, 8, 4.5, 6, 11.2])


def _cisco(u):
    return np.interp(u, [0, 0.1, 0.16, 0.25, 0.4, 0.55, 0.7, 0.85, 0.95, 1], [10, 30, 80, 12, 9, 22, 30, 45, 62, 80.25])


def _newton(u):
    return np.interp(u, [0, 0.2, 0.35, 0.5, 0.62, 0.7, 0.8, 1], [130, 260, 380, 600, 1000, 900, 300, 150])


CARDS = [
    ('2007', '中国石油 A 股', _petro, (0, 50), [(0.0, '上市首日开盘 48.60 元', UP2, 'r'), (1.0, '2026.8  约 11 元', DOWN2, 'l')],
     '19 年后，股价仍不到当年的四分之一'),
    ('2000', '思科 Cisco', _cisco, (0, 90), [(0.16, '2000.3 全球市值第一', UP2, 'r'), (0.4, '跌去近九成', DOWN2, 'l')],
     '用了 25 年，股价才回到当年高点'),
    ('1720', '牛顿 · 南海泡沫', _newton, (0, 1050), [(0.35, '早早获利卖出', DOWN2, 'r'), (0.62, '顶部附近又买回', UP2, 'r')],
     '最终损失惨重'),
]


def s_three_tops(f, t):
    if not (123.2 <= t <= 132.3): return
    a = env(t, 123.40, 131.8, 0.4, 0.4)
    for i, (yr, nm, fn, rng, marks, foot) in enumerate(CARDS):
        t0 = 123.55 + i * 1.06
        ca = a * eo((t - t0) / 0.5)
        if ca <= 0.003: continue
        cx = 400 + i * 560
        x0, x1, y0, y1 = cx - 240, cx + 240, 250, 800
        f.panel(x0, y0 + 30 * (1 - ca), x1, y1, ca)
        f.text(yr, x0 + 28, y0 + 52, 44, 'corm_sb', GOLD, ca, 'l', mode='O')
        f.text(nm, x0 + 28, y0 + 102, 26, 'serif_bold', INK, ca, 'l', mode='O')
        u = eo((t - t0 - 0.2) / 1.6)
        xs = np.linspace(x0 + 40, x1 - 40, 160)
        uu = np.linspace(0, 1, 160)
        v = fn(uu)
        cy0, cy1 = y0 + 170, y1 - 120
        ys = cy1 - (v - rng[0]) / (rng[1] - rng[0]) * (cy1 - cy0)
        pts, head = polyline_upto(xs, ys, u)
        draw_price(f, pts, ca, 2, smooth=5)
        f.disc(head, 3, WHITE, ca)
        for (mu, s, col, anc) in marks:
            if u < mu - 0.01: continue
            j = int(mu * 159)
            ma = ca * cl((u - mu) / 0.08 + 0.01)
            f.disc((xs[j], ys[j]), 5, col, ma)
            f.circle((xs[j], ys[j]), 11, col, ma * 0.6, 1)
            dx = 14 if anc == 'l' else -14
            if j < 20: dx, anc = 14, 'l'
            f.text(s, xs[j] + dx, ys[j] - 20, 15, 'sans_bold', col, ma, anc, mode='O')
        f.text(foot, cx, y1 - 50, 17, 'serif_bold', INK, ca * cl((u - 0.85) / 0.15), 'm', mode='O')
        # 「只要买得太贵」：三张卡同时点亮各自的山顶
        ha = ca * env(t, 127.7, 1e9, 0.3, 0)
        if ha > 0:
            j = int([0.0, 0.16, 0.62][i] * 159)
            dt = t - 127.7
            f.dashed((x0 + 30, ys[j]), (x1 - 30, ys[j]), UP, ha * 0.5, 1, 6, 5)
            f.circle((xs[j], ys[j]), 10 + 40 * eo((dt % 1.0638) / 0.9), UP, ha * (1 - eo((dt % 1.0638) / 0.9)), 1)
            f.disc((xs[j], ys[j]), 6, WHITE, ha)
            f.text('买在这里', xs[j] + (14 if i == 0 else 0), ys[j] + 34, 17, 'serif_black', UP2, ha,
                   'l' if i == 0 else 'm', mode='O')


narr(123.5, 127.5, '公司可以很好，技术可以是真的，你也可以很聪明——')
narr(127.65, 131.8, '只要买得太贵，照样会输。')


# ======================================================================== 情绪周期 + 行为缺口
CYC_X = np.linspace(160, 1760, 400)
_ph = np.linspace(-0.35, 2 * math.pi - 0.35, 400)
CYC_Y = 520 - 230 * np.sin(_ph) - 30 * np.sin(2 * _ph)
_ip, _it = int(np.argmin(CYC_Y)) / 399, int(np.argmax(CYC_Y)) / 399
CYC_L = [(0.03, '怀疑'), (0.09, '希望'), (0.15, '乐观'), (_ip - 0.06, '兴奋'), (_ip, '【狂喜】'), (_ip + 0.1, '焦虑'),
         (_ip + 0.2, '否认'), (_it - 0.14, '恐慌'), (_it, '【投降】'), (_it + 0.09, '绝望'), (0.985, '希望')]


def s_cycle(f, t):
    if not (131.7 <= t <= 143.0): return
    a = env(t, 131.9, 142.4, 0.5, 0.5)
    ca = a * (1 - eio((t - 135.9) / 0.6))
    if ca > 0.003:
        u = eo((t - 132.0) / 2.6)
        pts, head = polyline_upto(CYC_X, CYC_Y, u)
        draw_price(f, pts, ca, 3, smooth=5)
        for (lu, s) in CYC_L:
            if u < lu: continue
            j = int(lu * 399); x, y = CYC_X[j], CYC_Y[j]
            la = ca * cl((u - lu) / 0.05)
            above = y < 520
            if abs(lu - _ip) < 1e-6 or abs(lu - _it) < 1e-6:
                above = lu == _it
            f.text(s, x, y + (-34 if above else 36), 22, 'serif_bold', INK, la, 'm', mode='O', hl=GOLD)
        ip = int(np.argmin(CYC_Y)); it = int(np.argmax(CYC_Y))
        if u > ip / 399:
            k = env(t, 133.0, 1e9, 0.3, 0)
            f.disc((CYC_X[ip], CYC_Y[ip]), 7, UP, ca * k)
            f.text('买入', CYC_X[ip], CYC_Y[ip] + 74, 30, 'serif_black', UP, ca * k, 'm', mode='O')
            f.circle((CYC_X[ip], CYC_Y[ip]), 16 + 4 * beat_pulse(t), UP, ca * k * 0.7, 1)
        if u > it / 399:
            k = env(t, 133.8, 1e9, 0.3, 0)
            f.disc((CYC_X[it], CYC_Y[it]), 7, DOWN, ca * k)
            f.text('卖出', CYC_X[it], CYC_Y[it] - 76, 30, 'serif_black', DOWN, ca * k, 'm', mode='O')
            f.circle((CYC_X[it], CYC_Y[it]), 16 + 4 * beat_pulse(t), DOWN, ca * k * 0.7, 1)
    ba = a * eio((t - 136.0) / 0.6)
    if ba <= 0.003: return
    # 晨星（中国）：五年期年化「投资者回报差」= 投资者年化回报 − 基金年化回报（截至 2024.12.31）
    f.text('投资者回报差', 960, 250, 40, 'serif_black', INK, ba, 'm', track=0.2, mode='O', t0=136.1, stag=0.05)
    f.text('投资者实际年化回报 − 基金年化回报 · 五年期', 960, 300, 17, 'sans_med', GREY, ba, 'm', track=0.1,
           mode='O')
    base = 400
    gaps = [('固收', -0.62), ('保守混合', -0.86), ('积极配置', -2.17), ('主动非行业股票', -2.65), ('行业基金', -3.59)]
    sc = 88
    f.line((380, base), (1540, base), WHITE, 0.4 * ba, 1, buf='L')
    f.text('0', 362, base, 14, 'mono', GREY, ba, 'r', mode='O')
    for i, (nm, g) in enumerate(gaps):
        t0 = 136.7 + i * 0.32 if i != 3 else 138.3
        k = eo((t - t0) / 0.7)
        x = 500 + i * 230
        hl = i == 3
        col = mixc(C(120, 170, 160), DOWN, i / 4)
        h = -g * sc * k
        f.rrect_fill(x - 52, base + 2, x + 52, base + 2 + h, 3, DOWN if hl else col, (0.75 if hl else 0.55) * ba * cl((t - t0) / 0.2),
                     'L')
        if hl:
            f.rrect(x - 52, base + 2, x + 52, base + 2 + h, 3, DOWN2, ba * k, 1)
        va = ba * cl((t - t0) / 0.25)
        f.text(nm, x, base - 30, 20 if hl else 18, 'serif_bold', INK if hl else GREY, va, 'm', mode='O')
        f.text(f'−{-g * k:.2f}', x, base + h + 30, 30 if hl else 24, 'mono_med', DOWN2 if hl else col, va, 'm', mode='O')
    ka = ba * env(t, 140.3, 1e9, 0.4, 0)
    if ka > 0:
        k = eo((t - 140.3) / 0.9)
        f.line((500, 800), (500 + 920 * k, 800), GOLD, ka, 2)
        f.line((1420 * 1 - 14 + 0 * k, 792), (1420, 800), GOLD, ka * cl(k * 3 - 2), 2)
        f.line((1420 - 14, 808), (1420, 800), GOLD, ka * cl(k * 3 - 2), 2)
        f.text('波动越大  ·  差距越大', 960, 832, 22, 'serif_bold', GOLD, ka, 'm', track=0.15, mode='O')
    f.text('单位：百分点 / 年。数据：晨星（中国）《中国公募基金投资者回报差研究报告》，截至 2024.12.31 的五年期', 960, 875, 13,
           'sans_light', GREY, ba * 0.85, 'm', mode='O')


narr(132.0, 134.0, '拼在一起，就是一张「亏钱地图」：')
narr(134.03, 136.0, '最兴奋时买入，最绝望时卖出。')
narr(136.16, 138.2, '晨星统计了中国公募基金五年的数据：')
narr(138.28, 140.3, '投资者每年少赚 2.65 个百分点——')
narr(140.41, 142.4, '输在买卖时机。波动越大，输得越多。')


# ======================================================================== 镜子
MR_X = 260 + (CO_X - 170) / 1580 * 1400
MR_Y = (CO_P - 80) / 160


def s_mirror(f, t):
    if not (142.3 <= t <= 151.4): return
    a = env(t, 142.53, 150.9, 0.6, 0.5)
    my = 500
    u = eo((t - 142.6) / 2.2)
    m = eio((t - 148.9) / 1.3)                  # 市场线下移，与情绪线重合
    f.line((200, my), (1720, my), WHITE, 0.30 * a * (1 - m), 1)
    top_y = my - 50 - MR_Y * 240 + m * 340
    pts, head = polyline_upto(MR_X, top_y, u)
    draw_price(f, pts, a * (1 - 0.6 * m), 3, smooth=25)
    emo_y = my + 290 - MR_Y * 240
    rp, rh = polyline_upto(MR_X, emo_y, u)
    f.poly(rp, mixc(GOLD, WHITE, 0.2), a * (0.75 + 0.25 * m), 2 + int(m * 1.5))
    f.text('市场', 220, my - 40, 26, 'serif_bold', INK, a * (1 - m), 'l', mode='O')
    f.text('你的情绪', 220, my + 44, 26, 'serif_bold', GOLD, a, 'l', mode='O')
    i = int(np.argmax(MR_Y)); j = int(np.argmin(MR_Y[i:])) + i
    if u > i / len(MR_X):
        k = a * env(t, 144.0, 1e9, 0.4, 0)
        f.text('贪婪', MR_X[i], emo_y[i] - 36, 24, 'serif_black', UP, k, 'm', mode='O')
    if u > j / len(MR_X):
        k = a * env(t, 144.5, 1e9, 0.4, 0)
        f.text('恐惧', MR_X[j], emo_y[j] + 36, 24, 'serif_black', DOWN, k, 'm', mode='O')
    ka = a * env(t, 149.6, 1e9, 0.6, 0)
    if ka > 0:
        f.text('它们，本是同一条线', 1500, my - 80, 28, 'serif_bold', INK, ka * 0.9, 'm', mode='O')


narr(142.7, 144.6, '我们总以为，敌人是市场。')
narr(144.66, 146.7, '是庄家，是消息，是运气。')
narr(146.78, 148.8, '可真正把你送上山顶的——')
narr(148.91, 150.9, '是你自己，【未经审视的直觉】。')

# 抽空段：人性很难改变 → 金色粒子向中心汇聚
_r = np.random.default_rng(141)
IM_N = 2400
IM_A = _r.random(IM_N) * 2 * math.pi
IM_R = 500 + _r.random(IM_N) * 700
IM_S = _r.random(IM_N)


def s_question(f, t):
    if not (150.9 <= t <= T_D3 + 0.05): return
    a = env(t, 151.1, T_D3, 0.6, 0.0)
    f.text('人性，很难改变。', W / 2, 470, 60, 'serif_black', INK, a * env(t, 151.2, 153.0, 0.6, 0.4), 'm', track=0.2,
           mode='O', t0=151.2, stag=0.06, dur=0.6)
    f.text('那么，我们还能做什么？', W / 2, 470, 60, 'serif_black', INK, a * env(t, 153.2, 155.6, 0.6, 0.5), 'm',
           track=0.2, mode='O', t0=153.2, stag=0.06, dur=0.6)
    k = eio3(cl((t - 154.6) / (T_D3 - 154.6)))
    if k > 0:
        r = IM_R * (1 - k) ** (0.8 + IM_S * 0.6)
        ang = IM_A + k * 3.0 * (1 + IM_S)
        x = 960 + np.cos(ang) * r; y = 500 + np.sin(ang) * r * 0.75
        f.dots(x, y, GOLD, a * (0.3 + 0.7 * k) * 0.9, 1.0)
        f.glow((960, 500), 8 + 26 * k, GOLDL, a * k * 0.55)
    draw_you(f, 960, 640, a * env(t, 151.2, 155.0, 0.8, 0.6), WHITE, '', t, 4, True)


SCENES_B = [s_stamp1, s_crash, s_spiral_down, s_loss_aversion, s_asym, s_three_tops, s_cycle, s_mirror, s_question]
