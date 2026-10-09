"""序章 + 标题 + 第一幕「上山 · 贪婪」+ 山顶。"""
from common import *  # noqa

# ======================================================================== 序章：一条你一定见过的线
CO_N = 420
_u = np.linspace(0, 1, CO_N)
_n = smooth_noise(CO_N, 5, 9) * 0.035 + smooth_noise(CO_N, 6, 3) * 0.010


def _co_price(u):
    up = 100 * np.exp(0.815 * (u / 0.62) ** 1.7)                       # 0..0.62：加速上涨到 +126%
    dn = 226 * (1 - 0.41 * eio_np((u - 0.62) / 0.24))                     # 0.62..0.86：跌 41%
    rb = 133.3 * (1 + 0.36 * eio_np((u - 0.86) / 0.14))                   # 0.86..1：反弹
    return np.where(u <= 0.62, up, np.where(u <= 0.86, dn, rb))


def eio_np(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


CO_P = _co_price(_u) * (1 + _n * np.minimum(1, _u * 3))
CO_P[0] = 100
CO_PI = int(0.62 * (CO_N - 1))
CO_P[CO_PI] = 226
CO_X = 170 + _u * 1580
CO_Y = 860 - (CO_P - 80) * 3.35
CO_T0, CO_TPEAK, CO_TLOW, CO_TEND = 0.4, 10.76, 15.45, 17.0
CO_ULOW = 0.86


def co_u(t):
    if t < CO_TPEAK:
        return 0.62 * cl((t - CO_T0) / (CO_TPEAK - CO_T0))
    if t < CO_TLOW:
        return 0.62 + 0.24 * eio((t - CO_TPEAK) / (CO_TLOW - CO_TPEAK)) ** 0.9
    return 0.86 + 0.14 * eo((t - CO_TLOW - 0.55) / (CO_TEND - CO_TLOW - 0.55))


def co_cam(t):
    """相机：起初贴近线头，逐渐拉远到全景"""
    s = keys(t, [(0, 2.3), (3.0, 2.0), (8.5, 1.05), (10.76, 1.0), (16.0, 1.0), (17.14, 1.22)], eio)
    _, head = polyline_upto(CO_X, CO_Y, co_u(t))
    full = (960, 560)
    k = eio((t - 2.0) / 7.5)
    fx = lerp(head[0] - 120, full[0], k); fy = lerp(head[1] - 60, full[1], k)
    # 重拍前一秒：镜头缓缓推向山顶
    q = eio((t - 16.0) / 1.14) * 0.6
    fx = lerp(fx, CO_X[CO_PI], q); fy = lerp(fy, CO_Y[CO_PI] + 60, q)
    return s, fx, fy


def cam_apply(p, cam):
    s, fx, fy = cam
    p = np.asarray(p, np.float64)
    return np.c_[(p[..., 0] - fx) * s + W / 2, (p[..., 1] - fy) * s + H / 2 - 20] if p.ndim == 2 else \
        np.array([(p[0] - fx) * s + W / 2, (p[1] - fy) * s + H / 2 - 20])


_r = np.random.default_rng(12)
CROWD_N = 520
CR_T = CO_T0 + 1.0 + (np.sort(_r.random(CROWD_N)) ** 0.55) * (CO_TPEAK - CO_T0 - 1.2)
CR_SRC = np.c_[_r.random(CROWD_N) * 2200 - 140, 1000 + _r.random(CROWD_N) * 300]
CR_OFF = _r.standard_normal((CROWD_N, 2)) * np.c_[np.full(CROWD_N, 10), np.full(CROWD_N, 8)]
CR_FALL = _r.random(CROWD_N)
CR_PH = _r.random(CROWD_N) * 6.28


def s_cold_open(f, t):
    if t > T_D1 + 0.3: return
    cam = co_cam(t)
    u = co_u(t)
    pts, head = polyline_upto(CO_X, CO_Y, u)
    a_all = cl(t / 0.6) * (1 - eio((t - T_D1 + 0.05) / 0.3))
    # 网格
    for k in range(7):
        py = 860 - k * 100
        p0 = cam_apply((100, py), cam); p1 = cam_apply((1820, py), cam)
        f.line(p0, p1, WHITE, 0.06 * a_all, 1, buf='L')
        val = 80 + (860 - py) / 3.35
        f.text(f'{(val / 100 - 1) * 100:+.0f}%', p0[0] + 6, p0[1] - 12, 12, 'mono', GREY, 0.45 * a_all, 'l', mode='L')
    # 价格线 + 面积
    sp = cam_apply(pts, cam)
    if len(sp) > 2:
        base_y = cam_apply((0, 900), cam)[1]
        poly = np.r_[sp, [[sp[-1, 0], base_y], [sp[0, 0], base_y]]]
        f.vgrad_fill(poly, UP if t < CO_TPEAK else DOWN, 0.10 * a_all, 0.0, sp[:, 1].min(), base_y, xfade=120)
        draw_price(f, sp, a_all, 3, smooth=25)
    hs = cam_apply(head, cam)
    hc = UP if t < CO_TPEAK + 0.1 else (DOWN if t < CO_TLOW + 0.3 else UP)
    f.disc(hs, 5, WHITE, a_all)
    f.glow(hs, 16, hc, 0.9 * a_all)
    # 人群：涨得越多，涌进来的人越多；见顶后四散
    k_in = eio(np.clip((t - CR_T) / 1.3, 0, 1))
    tgt = np.c_[np.full(CROWD_N, head[0]), np.full(CROWD_N, head[1])] + CR_OFF * (1 + 0.6 * np.sin(t * 2 + CR_PH))[:, None]
    P = CR_SRC + (tgt - CR_SRC) * k_in[:, None]
    fall = np.clip((t - CO_TPEAK - CR_FALL * 2.0) / 2.2, 0, 1)
    P = P + np.c_[(CR_FALL - 0.5) * 300 * fall, 600 * fall ** 2]
    A = (t > CR_T) * (0.25 + 0.75 * k_in) * (1 - fall) * 0.8 * a_all
    col = np.where(fall[:, None] > 0.01, np.array(DOWN, np.float32), np.array(UP2, np.float32))
    SP = cam_apply(P, cam)
    f.dots(SP[:, 0], SP[:, 1], col, A, 1.0)
    # 涨幅计数
    p_now = float(np.interp(u * (CO_N - 1), np.arange(CO_N), CO_P))
    if t < CO_TPEAK + 0.15:
        txt = f'{(p_now / 100 - 1) * 100:+.0f}%'
        f.text(txt, hs[0] + 26, hs[1] - 34, 40, 'mono_med', UP, a_all * cl((t - 1.2) / 0.5), 'l', mode='O')
    else:
        r = p_now / 226 - 1
        if t < 15.5:
            f.text('你的收益', hs[0] + 28, hs[1] - 70, 16, 'sans_med', GREY, a_all, 'l', mode='O')
            f.text(f'{r * 100:+.0f}%', hs[0] + 26, hs[1] - 36, 40, 'mono_med', DOWN, a_all, 'l', mode='O')
    # 「你」：先在场边观望，追进去，跟着跌，最后割肉
    if t > 2.0:
        aa = cl((t - 2.0) / 0.6) * a_all
        watch = np.array([head[0] - 40, 880.0])
        if t < 8.64:
            y = watch
        elif t < CO_TPEAK:
            k = eio3((t - 8.64) / (CO_TPEAK - 8.64))
            start = np.array([CO_X[int(8.64 / CO_TPEAK * CO_PI * 0.93)] - 40, 880.0])
            y = start + (np.array(head) - start) * k + np.array([0, -140]) * math.sin(k * math.pi)
        elif t < 15.0:
            y = np.array(head)
        else:
            k = (t - 15.0) / 1.2
            y = np.array(head) + np.array([30 * k, 260 * eio(k)])
            aa *= 1 - cl(k)
        ys = cam_apply(y, cam)
        colr = WHITE if t < CO_TPEAK else mixc(WHITE, DOWN, cl((t - CO_TPEAK) / 3))
        draw_you(f, ys[0], ys[1], aa, tuple(colr), '你', t, 5.5, t < CO_TPEAK, lab_dy=-30 if t < 8.64 else 32)
        if t >= CO_TPEAK:
            heart_ring(f, ys[0], ys[1], t, tuple(colr), aa)
        if 15.0 < t < 16.4:
            f.text('割肉', ys[0] + 26, ys[1], 20, 'serif_bold', DOWN, aa, 'l', mode='O')
    if t > 10.76:
        # 山顶标记
        pk = cam_apply((CO_X[CO_PI], CO_Y[CO_PI]), cam)
        a2 = env(t, 10.9, 16.9, 0.5, 0.3)
        f.dashed((pk[0], pk[1] - 8), (pk[0], 900), WHITE, 0.25 * a2, 1)
        f.text('你买入的位置', pk[0], pk[1] - 40, 16, 'sans_med', GREY, a2, 'm', mode='O')


narr(0.55, 2.1, '这条线，你一定见过。')
narr(2.26, 4.25, '它涨的时候，你在观望。')
narr(4.39, 6.4, '它还在涨，你开始坐立不安。')
narr(6.51, 8.5, '身边的人，都赚到了钱。')
narr(8.64, 10.6, '于是，你终于冲了进去——')
narr(10.76, 12.75, '然后，它开始跌。')
narr(12.89, 14.9, '你告诉自己：会涨回来的。')
narr(15.01, 15.95, '你割肉离场。')
narr(16.08, 17.05, '它涨了回去。')


# ======================================================================== 标题：粒子山
def ridge(x):
    x = np.asarray(x, np.float64)
    y = 780 - 330 * np.exp(-((x - 960) / 330) ** 2) - 110 * np.exp(-((x - 560) / 190) ** 2) \
        - 90 * np.exp(-((x - 1370) / 210) ** 2) - 30 * np.exp(-((x - 760) / 70) ** 2) \
        - 40 * np.exp(-((x - 1160) / 90) ** 2)
    return y + 7 * np.sin(x * 0.031 + 0.4) * np.sin(x * 0.007) + 4 * np.sin(x * 0.093 + 1)


SUMMIT = (960.0, float(ridge(960)))
_r = np.random.default_rng(33)
MT_N = 16000
_mx = _r.random(MT_N) * 2100 - 90
_depth = _r.exponential(1.0, MT_N) ** 1.35 * 70
MT_P = np.c_[_mx, ridge(_mx) + _depth]
MT_EDGE = np.exp(-_depth / 25)
MT_COL = mixc(C(150, 80, 170), UP, MT_EDGE[:, None] * 0.7) * 0.75 + np.array(GOLD, np.float32) * (MT_EDGE[:, None] ** 3) * 0.5
MT_A = 0.35 + 0.75 * MT_EDGE
MT_START = np.c_[CO_X[(_r.random(MT_N) * (CO_N - 1)).astype(int)], CO_Y[(_r.random(MT_N) * (CO_N - 1)).astype(int)]] + \
    _r.standard_normal((MT_N, 2)) * 60
MT_PH = _r.random(MT_N) * 6.28
# 山顶上的人群
TOP_N = 600
_ang = _r.random(TOP_N) * math.pi
_rad = _r.random(TOP_N) ** 0.7
TOP_P = np.c_[SUMMIT[0] + (_r.random(TOP_N) - 0.5) * 2 * 120 * _rad, np.zeros(TOP_N)]
TOP_P[:, 1] = ridge(TOP_P[:, 0]) - 4 - _r.exponential(1, TOP_N) * 7
TOP_ARR = _r.random(TOP_N)          # 到达山顶的先后
TOP_SRC = np.c_[_r.random(TOP_N) * 1900 + 10, 900 + _r.random(TOP_N) * 200]


def draw_mountain(f, t, a, push=1.0, wind=0.0, explode=0.0, crowd=1.0, crowd_arrive=None):
    if a <= 0.003: return
    P = MT_P.copy()
    P[:, 1] += np.sin(t * 0.8 + MT_PH) * 1.2
    if wind > 0:
        P[:, 0] += wind * (300 + 900 * MT_EDGE) * (0.5 + np.sin(MT_PH) * 0.5)
        P[:, 1] -= wind * 120 * MT_EDGE
    cx, cy = SUMMIT
    P = (P - [cx, cy + 120]) * push + [cx, cy + 120]
    A = MT_A * a * (0.85 + 0.3 * bar_pulse(t) * energy(t))
    f.splat(P[:, 0], P[:, 1], MT_COL, A)
    xs = np.linspace(-80, 2000, 300)
    rp = (np.c_[xs, ridge(xs)] - [cx, cy + 120]) * push + [cx, cy + 120]
    f.poly(rp, mixc(UP, GOLD, 0.5), 0.55 * a * (1 - wind), 2)
    if crowd > 0:
        if crowd_arrive is None:
            k = np.ones(TOP_N)
        else:
            k = eio_np((crowd_arrive - TOP_ARR) / 0.15)
        TP = TOP_SRC + (TOP_P - TOP_SRC) * k[:, None]
        TP = (TP - [cx, cy + 120]) * push + [cx, cy + 120]
        jig = np.c_[np.sin(t * 3 + MT_PH[:TOP_N]), np.cos(t * 2.6 + MT_PH[:TOP_N])] * 1.5
        f.dots(TP[:, 0] + jig[:, 0], TP[:, 1] + jig[:, 1], UP2, 0.75 * a * crowd * (k > 0.01), 1.0)


def s_title(f, t):
    if not (T_D1 - 0.1 <= t <= 24.0): return
    k = eo((t - T_D1) / 0.9)
    a = 1 - eio((t - 22.9) / 0.8)
    if t < T_D1 + 1.0:
        # 价格线炸成粒子，再聚成山
        P = MT_START + (MT_P - MT_START) * k
        f.splat(P[:, 0], P[:, 1], MT_COL, MT_A * (0.5 + 0.5 * k))
    else:
        draw_mountain(f, t, a, push=1.0 + 0.04 * (t - T_D1), wind=eio((t - 22.8) / 1.0) * 1.2)
    draw_you(f, SUMMIT[0], SUMMIT[1] - 38, a * cl((t - T_D1 - 0.6) / 0.5), WHITE, '你', t, 4.5, True, lab_dy=-28)
    f.text('你为什么总买在【山顶】？', W / 2, 205, 104, 'serif_black', INK, a, 'm', track=0.06, mode='O',
           t0=T_D1 + 0.05, stag=0.045, dur=0.55, rise=26, hl=GOLD)
    f.glow((W / 2 + 230, 205), 90, GOLD, 0.25 * a * k)
    f.text('WHY DO WE ALWAYS BUY AT THE TOP?', W / 2, 300, 26, 'corm_sb', GOLD, 0.9 * a, 'm', track=0.32, mode='O',
           t0=T_D1 + 0.7, stag=0.012, dur=0.4)
    f.text('一场从贪婪、恐惧到理性觉醒的认知旅程', W / 2, 352, 22, 'sans_light', GREY, a, 'm', track=0.3, mode='O',
           t0=19.27, stag=0.03, dur=0.5)


# ======================================================================== 1A 2026：AI 点燃科技股
# 科创50 走势示意（非真实数据，仅标注已核实的数据点）
_DAYS = 281                             # 1/1 ~ 10/8
_d = np.arange(_DAYS)
def _star(d):
    d = np.asarray(d, np.float64)
    v = 1180 + 70 * eio_np(d / 25) - 90 * eio_np((d - 32) / 40) + 520 * eio_np((d - 80) / 95) ** 1.15
    v += 95 * eio_np((d - 150) / 30)                  # 6 月冲顶
    v -= 210 * eio_np((d - 182) / 13)                 # 7 月回调约 11%
    v += 70 * eio_np((d - 200) / 40) - 30 * eio_np((d - 245) / 30)
    v -= 90 * eio_np((d - 278) / 2)                   # 10/8 -4.82%
    return v
STAR = _star(_d) * (1 + smooth_noise(_DAYS, 41, 3) * 0.012 + smooth_noise(_DAYS, 42, 9) * 0.01)
STAR[130] = STAR[130]  # 5/11 = 第 130 天
SC_X0, SC_X1, SC_Y0, SC_Y1 = 250, 1690, 300, 800
def sc_xy(d, v):
    x = SC_X0 + (SC_X1 - SC_X0) * np.asarray(d) / (_DAYS - 1)
    y = SC_Y1 - (np.asarray(v) - 1000) / (1800 - 1000) * (SC_Y1 - SC_Y0)
    return x, y
SC_PX, SC_PY = sc_xy(_d, STAR)
MONTHS = [(0, '1月'), (31, '2月'), (59, '3月'), (90, '4月'), (120, '5月'), (151, '6月'), (181, '7月'), (212, '8月'),
          (243, '9月'), (273, '10月')]


def draw_star_chart(f, t, a, upto_day, callouts):
    if a <= 0.003: return
    for d, m in MONTHS:
        x, _ = sc_xy(d, 0)
        f.line((x, SC_Y1 + 10), (x, SC_Y1 + 18), WHITE, 0.3 * a, 1, buf='L')
        f.text(m, x + 4, SC_Y1 + 34, 13, 'sans_med', GREY, 0.7 * a, 'l', mode='L')
    for k in range(5):
        y = SC_Y0 + k * (SC_Y1 - SC_Y0) / 4
        f.line((SC_X0, y), (SC_X1, y), WHITE, 0.05 * a, 1, buf='L')
    f.line((SC_X0, SC_Y1 + 10), (SC_X1, SC_Y1 + 10), WHITE, 0.25 * a, 1, buf='L')
    f.text('科创50 · 2026 走势示意', SC_X0, SC_Y0 - 40, 16, 'sans_med', INK, 0.8 * a, 'l', track=0.1, mode='L')
    f.text('示意图，仅标注的数据点为真实数据', SC_X0, SC_Y0 - 16, 11, 'sans_light', GREY, 0.6 * a, 'l', mode='L')
    u = cl(upto_day / (_DAYS - 1))
    pts, head = polyline_upto(SC_PX, SC_PY, u)
    if len(pts) > 2:
        poly = np.r_[pts, [[pts[-1, 0], SC_Y1 + 10], [pts[0, 0], SC_Y1 + 10]]]
        f.vgrad_fill(poly, UP, 0.12 * a, 0.0, SC_Y0, SC_Y1)
        draw_price(f, pts, a, 2, smooth=7)
        f.disc(head, 4, WHITE, a)
        f.glow(head, 14, UP, 0.8 * a)
        # 成交额柱（随行情放大）
        n = len(pts)
        for i in range(0, n, 4):
            d = i / (len(SC_PX) - 1) * (_DAYS - 1)
            vol = 18 + 70 * eio((d - 85) / 60) * (1 - 0.5 * eio((d - 185) / 30)) + 10 * math.sin(d * 1.7) ** 2
            f.line((pts[i, 0], SC_Y1 + 8), (pts[i, 0], SC_Y1 + 8 - vol * 0.55), UP if d < 182 else DOWN, 0.35 * a, 1,
                   buf='L')
    for (tc, d, lines, side, colr) in callouts:
        ca = a * env(t, tc, 1e9, 0.5, 0)
        if ca <= 0.003 or d > upto_day + 0.5: continue
        x, y = sc_xy(d, STAR[int(d)])
        ln = 70 * eo((t - tc) / 0.5)
        if side == 'left':
            f.line((x, y), (x - ln * 1.6, y), colr, ca * 0.8, 1)
            f.disc((x, y), 4, colr, ca)
            f.circle((x, y), 9 + 6 * beat_pulse(t), colr, ca * 0.6, 1)
            for j, s in enumerate(lines):
                f.text(s, x - 125, y - 12 + j * 28, 20 if j == 0 else 15, 'sans_bold' if j == 0 else 'sans_med',
                       colr if j == 0 else INK, ca, 'r', mode='O', t0=tc + 0.1 * j, stag=0.015, dur=0.35)
            continue
        ty = y - ln if side == 'up' else y + ln
        f.line((x, y), (x, ty), colr, ca * 0.8, 1)
        f.disc((x, y), 4, colr, ca)
        f.circle((x, y), 9 + 6 * beat_pulse(t), colr, ca * 0.6, 1)
        for j, s in enumerate(lines):
            yy = ty - 14 - (len(lines) - 1 - j) * 28 if side == 'up' else ty + 18 + j * 28
            f.text(s, x + 10, yy, 20 if j == 0 else 15, 'sans_bold' if j == 0 else 'sans_med', colr if j == 0 else INK,
                   ca, 'l', mode='O', t0=tc + 0.1 * j, stag=0.015, dur=0.35)


def s_2026_rise(f, t):
    if not (23.3 <= t <= 34.6): return
    a = env(t, 23.6, 33.9, 0.6, 0.6)
    day = keys(t, [(24.3, 0), (33.2, 181)], eio)
    draw_star_chart(f, t, a, day, [
        (25.4, 18, ['1 月新开户 492 万户', '高于 2025 年任何一个月'], 'down', GOLD),
        (28.6, 130, ['5.11 收于 1716.69 点', '科创50 历史新高'], 'left', UP),
    ])
    # 统计卡
    ca = a * env(t, 30.0, 40, 0.5, 0)
    if ca > 0:
        f.panel(1240, 560, 1660, 690, ca)
        f.text('2026 上半年 新开 A 股账户', 1264, 595, 16, 'sans_med', GREY, ca, 'l', mode='O')
        n = 2016 * eo((t - 30.0) / 1.2)
        f.text(f'{n:,.0f} 万户', 1264, 645, 40, 'mono_med', INK, ca, 'l', mode='O')
        f.text('同比 +60%', 1520, 650, 20, 'sans_bold', UP, ca * cl((t - 31) / 0.4), 'l', mode='O')
    wa = env(t, 32.1, 33.9, 0.8, 0.5)
    f.text('这次不一样', 760, 420, 110, 'serif_black', UP2, 0.22 * wa, 'm', track=0.3, mode='E', glow=0.6)


narr(23.9, 27.6, '2026 年春天，AI 算力点燃了 A 股的科技股。')
narr(27.77, 31.9, '科创50 创下历史新高，上半年新开户同比大增六成。')
narr(32.02, 34.0, '人们开始相信：【这次不一样】。')


# ======================================================================== 1B 错失恐惧 FOMO
_r = np.random.default_rng(55)
GX, GZ = np.meshgrid(np.arange(-13, 14), np.arange(0, 12))
GX = GX.ravel().astype(float); GZ = GZ.ravel().astype(float)
G_N = len(GX)
YOU_I = int(np.where((GX == 0) & (GZ == 2))[0][0])
_ord = _r.permutation(G_N)
G_T = np.zeros(G_N)
G_T[_ord] = 35.0 + (np.arange(G_N) / G_N) ** 0.6 * 8.0
G_T[YOU_I] = 1e9
G_GAIN = _r.integers(8, 160, G_N)


def grid_proj(gx, gz, t):
    sway = 0.6 * math.sin((t - 34) * 0.3)
    d = 1.0 + gz * 0.42 - 0.012 * (t - 34)
    sx = 760 + (gx + sway * (gz / 11)) * 118 / d
    sy = 250 + 560 / d
    return sx, sy, np.minimum(2.2 / d, 1.3)


def s_fomo(f, t):
    if not (33.9 <= t <= 45.1): return
    a = env(t, 34.15, 44.6, 0.5, 0.4)
    scene_tag(f, t, 34.25, '错失恐惧', 'FOMO · FEAR OF MISSING OUT', 44.4)
    sx, sy, d = grid_proj(GX, GZ, t)
    lit = np.clip((t - G_T) / 0.35, 0, 1)
    col = mixc(np.array(DIM) * 1.6, UP2, lit[:, None])
    col = mixc(col, GOLD, (lit * (0.5 + 0.5 * np.sin(t * 4 + GX)))[:, None] * 0.3)
    sz = d
    A = a * (0.45 + 0.55 * lit)
    m = (np.arange(G_N) != YOU_I) & (sy < 900) & (sx > -20) & (sx < W + 20)
    far = m & (sz < 0.45)
    f.dots(sx[far], sy[far], col[far], A[far] * 1.4, 0.8)
    for i in np.nonzero(m & (sz >= 0.45))[0]:
        f.disc((sx[i], sy[i]), 1.2 + 3.2 * sz[i], tuple(col[i]), A[i])
    # 收益飘字（只给部分点）
    for i in _ord[:60]:
        p = (t - G_T[i]) / 1.4
        if 0 < p < 1 and i != YOU_I and 0 < sx[i] < W and sy[i] < 860:
            f.text(f'+{G_GAIN[i]}%', sx[i], sy[i] - 18 - 40 * eo(p), int(11 + 9 * sz[i]), 'mono_med', UP2,
                   a * (1 - p) * 0.9, 'm', mode='L')
    frac = float((lit[m] > 0.5).mean())
    yx, yy = sx[YOU_I], sy[YOU_I]
    draw_you(f, yx, yy, a, WHITE, '你', t, 6, False, lab_dy=34)
    # 焦虑环：别人赚得越多，越难受
    rr = 34 + 6 * beat_pulse(t, 0.2)
    f.arc((yx, yy), rr, -math.pi / 2, -math.pi / 2 + 2 * math.pi * frac, UP, a * 0.9, 3)
    f.circle((yx, yy), rr, WHITE, a * 0.12, 1)
    f.text(f'身边赚钱的人 {frac * 100:.0f}%', yx + 52, yy - 4, 16, 'sans_med', UP2, a * cl((t - 35.5) / 0.5), 'l',
           mode='O')
    # 右侧：实际损失 vs 感受到的损失
    ba = a * env(t, 38.3, 50, 0.5, 0)
    if ba > 0:
        x0, y0 = 1330, 520
        f.panel(x0 - 30, y0 - 70, x0 + 440, y0 + 230, ba)
        f.text('踏空时，你的账户', x0, y0 - 30, 18, 'sans_med', GREY, ba, 'l', mode='O')
        f.text('实际亏损', x0, y0 + 20, 20, 'sans_bold', INK, ba, 'l', mode='O')
        f.line((x0 + 110, y0 + 20), (x0 + 112, y0 + 20), WHITE, ba, 3)
        f.text('0 元', x0 + 130, y0 + 20, 22, 'mono_med', INK, ba, 'l', mode='O')
        k = eo((t - 39.6) / 2.6)
        f.text('大脑感受到的', x0, y0 + 90, 20, 'sans_bold', INK, ba * cl((t - 39.4) / 0.4), 'l', mode='O')
        f.text('「亏损」', x0, y0 + 122, 20, 'sans_bold', UP, ba * cl((t - 39.4) / 0.4), 'l', mode='O')
        bw = 270 * k * (1 + 0.04 * beat_pulse(t))
        f.rrect_fill(x0 + 132, y0 + 92, x0 + 132 + bw, y0 + 118, 4, UP, 0.75 * ba, 'E')
        f.glow((x0 + 132 + bw, y0 + 105), 20, UP, 0.5 * ba * k)


narr(36.27, 38.3, '踏空，并不会让你少一分钱。')
narr(38.40, 42.5, '可大脑会把「别人在赚钱」，记成「我在亏钱」。')
narr(42.65, 44.6, '看着别人赚钱，有时比自己亏钱还难受。')


# ======================================================================== 1C 羊群效应：信息瀑布
_r = np.random.default_rng(77)
HD_N = 1600
HD_HOME = np.c_[180 + _r.random(HD_N) * 1080, 270 + _r.random(HD_N) * 560]
HD_PH = _r.random((HD_N, 2)) * 6.28
HD_TGT = np.array([1560.0, 520.0])
_seed = np.array([430.0, 600.0])
HD_HOME[0] = _seed
HD_HOME[1] = _seed + [110, -70]
HD_HOME[2] = _seed + [230, 30]
_dist = np.linalg.norm(HD_HOME - HD_HOME[2], axis=1)
HD_T = 50.3 + (_dist / 1100) ** 0.75 * 3.6 + _r.random(HD_N) * 0.35
HD_T[0], HD_T[1], HD_T[2] = 46.95, 49.05, 49.7
HD_STAY = np.zeros(HD_N, bool); HD_STAY[:3] = True       # 前三个人留在原地，方便标注
HD_ORDER = np.argsort(HD_T)
HD_100 = HD_ORDER[99]
HD_TRAV = 1.5 + _r.random(HD_N) * 1.2
HD_ORB_R = 30 + _r.random(HD_N) ** 0.6 * 120
HD_ORB_W = (1.2 + _r.random(HD_N)) * np.where(_r.random(HD_N) < 0.5, 1, 1)


def herd_pos(t):
    wander = HD_HOME + np.c_[np.sin(t * 0.7 + HD_PH[:, 0]), np.cos(t * 0.6 + HD_PH[:, 1])] * 10
    p = np.clip((t - HD_T) / HD_TRAV, 0, 1)
    p[HD_STAY] = 0
    pe = p * p * (3 - 2 * p)
    ang = HD_PH[:, 0] + (t - HD_T - HD_TRAV) * HD_ORB_W
    orbit = HD_TGT + np.c_[np.cos(ang) * HD_ORB_R, np.sin(ang) * HD_ORB_R * 0.55]
    # 弧线前进
    mid = (wander + orbit) / 2 + np.c_[np.zeros(HD_N), -120 - 80 * np.sin(HD_PH[:, 1])]
    q = (1 - pe)[:, None] ** 2 * wander + 2 * ((1 - pe) * pe)[:, None] * mid + (pe ** 2)[:, None] * orbit
    return q, p


def s_herd(f, t):
    if not (44.5 <= t <= 55.9): return
    a = env(t, 44.77, 55.2, 0.5, 0.5)
    scene_tag(f, t, 44.85, '羊群效应', 'HERDING · INFORMATION CASCADE', 55.0)
    P, p = herd_pos(t)
    conv = (t >= HD_T)
    col = np.where(conv[:, None], np.array(UP2, np.float32), np.array(C(170, 180, 205), np.float32))
    A = a * np.where(conv, 0.7 + 0.4 * (1 - p), 0.6)
    f.dots(P[:, 0], P[:, 1], col, A, 1.5)
    # 拖尾
    P2, _ = herd_pos(t - 0.08)
    mv = conv & (p < 1)
    f.splat(P2[mv, 0], P2[mv, 1], UP, A[mv] * 0.5)
    # 热门赛道
    ga = a * cl((t - 46.0) / 1.0)
    f.glow(HD_TGT, 30 + 6 * beat_pulse(t), UP, 0.5 * ga)
    f.circle(HD_TGT, 40 + 8 * bar_pulse(t), UP2, 0.5 * ga, 1)
    f.text('热门赛道', HD_TGT[0], HD_TGT[1] - 160, 24, 'serif_bold', UP2, ga, 'm', mode='O')
    # 信息链
    labs = [(0, 46.95, '第 1 人：只是猜测'), (1, 49.05, '第 2 人：看到他买了'), (2, 49.7, '第 3 人：看到他们都买了')]
    for k, (i, tc, s) in enumerate(labs):
        la = a * env(t, tc, 52.6, 0.4, 0.6)
        if la <= 0: continue
        x, y = P[i]
        f.disc((x, y), 6, GOLD, la)
        f.circle((x, y), 12 + 4 * beat_pulse(t), GOLD, la * 0.6, 1)
        f.text(s, x - 10, y + 34 + k * 0, 17, 'sans_bold', GOLD, la, 'l', mode='O')
        if k > 0:
            q = P[labs[k - 1][0]]
            kk = eo((t - tc) / 0.5)
            f.line(q, (q[0] + (x - q[0]) * kk, q[1] + (y - q[1]) * kk), GOLD, la * 0.7, 1)
    tc = HD_T[HD_100]
    la = a * env(t, max(tc, 51.2), 53.4, 0.4, 0.5)
    if la > 0:
        x, y = P[HD_100]
        f.disc((x, y), 6, WHITE, la)
        f.circle((x, y), 14, WHITE, la * 0.7, 1)
        f.text('第 100 人：「大家都在买，不会错」', x + 18, y - 26, 18, 'sans_bold', INK, la, 'l', mode='O')
    # 计数
    n = int(conv.sum())
    f.text(f'已入场 {n:,} 人', 1560, 760, 18, 'mono_med', UP2, a * cl((t - 47) / 0.5), 'm', mode='O')


narr(46.90, 48.9, '第一个人买入，也许只是猜测。')
narr(49.02, 51.0, '第二个、第三个人，看见别人买了……')
narr(51.15, 53.1, '到第一百个人，猜测变成了「共识」。')
narr(53.28, 55.3, '其实，大家只是在看彼此。')


# ======================================================================== 1D 近因偏差：把最近当成永远
REC_X = np.linspace(330, 900, 10)
REC_V = np.array([0, 0.03, 0.02, 0.08, 0.1, 0.18, 0.22, 0.34, 0.45, 0.6])
REC_Y = 760 - REC_V * 500
# Greenwood & Shleifer 示意：预期跟随过去涨幅，随后回报与之相反
GS_X = np.linspace(260, 1660, 260)
_ph = np.linspace(0, 2 * math.pi * 2.2, 260)
GS_PRICE = np.sin(_ph) + 0.25 * np.sin(_ph * 2.3 + 1)
GS_EXP = np.sin(_ph - 0.55)
GS_RET = -np.sin(_ph - 0.55) * 0.95 + 0.1 * np.sin(_ph * 3.1)


def s_recency(f, t):
    if not (55.2 <= t <= 64.3): return
    a = env(t, 55.40, 63.7, 0.5, 0.5)
    scene_tag(f, t, 55.5, '近因偏差', 'RECENCY BIAS · EXTRAPOLATION', 63.6)
    a1 = a * (1 - eio((t - 59.3) / 0.6))
    if a1 > 0.003:
        n = int(cl((t - 55.6) / 1.4) * 10)
        for i in range(n):
            f.disc((REC_X[i], REC_Y[i]), 5, UP, a1)
            if i: f.line((REC_X[i - 1], REC_Y[i - 1]), (REC_X[i], REC_Y[i]), UP, a1 * 0.8, 2)
        f.line((300, 770), (950, 770), WHITE, 0.2 * a1, 1, buf='L')
        f.text('过去 10 周', 620, 800, 15, 'sans_med', GREY, a1, 'm', mode='L')
        k = eo((t - 57.2) / 1.4)
        if k > 0:
            p0 = np.array([REC_X[7], REC_Y[7]]); p1 = np.array([REC_X[9], REC_Y[9]])
            dvec = (p1 - p0) / np.linalg.norm(p1 - p0)
            end = p1 + dvec * 1100 * k
            f.dashed(p1, end, GOLD, a1 * 0.9, 2, 14, 10, phase=t * 60)
            f.glow(end, 20, GOLD, 0.6 * a1 * k)
            f.text('照这个速度……明年翻倍？', 1180, 300, 30, 'serif_bold', GOLD, a1 * cl((t - 57.8) / 0.5), 'm',
                   mode='O')
            f.text('大脑会把最近的趋势，画成一条直线', 1180, 345, 17, 'sans_med', GREY, a1 * cl((t - 58.2) / 0.5),
                   'm', mode='O')
    a2 = a * eio((t - 59.5) / 0.6)
    if a2 > 0.003:
        u = eo((t - 59.6) / 1.6)
        f.line((250, 560), (1670, 560), WHITE, 0.15 * a2, 1, buf='L')
        e_pts, _ = polyline_upto(GS_X, 560 - GS_EXP * 170, u)
        r_pts, _ = polyline_upto(GS_X, 560 - GS_RET * 170, u)
        f.poly(e_pts, UP, a2, 3)
        f.poly(r_pts, CYAN, a2 * 0.9, 2)
        f.text('投资者的预期', 290, 300, 18, 'sans_bold', UP, a2, 'l', mode='O')
        f.text('此后的实际回报', 290, 330, 18, 'sans_bold', CYAN, a2, 'l', mode='O')
        f.text('示意 · 依据 Greenwood & Shleifer (2014) 对投资者调查数据的研究', 1660, 840, 12, 'sans_light', GREY,
               a2 * 0.8, 'r', mode='O')
        # 标出最乐观的时刻
        i = int(np.argmax(GS_EXP[:130]))
        ka = a2 * env(t, 61.4, 1e9, 0.5, 0)
        if ka > 0:
            x = GS_X[i]
            f.dashed((x, 330), (x, 800), GOLD, ka * 0.8, 1, 8, 6)
            ye, yr = 560 - GS_EXP[i] * 170, 560 - GS_RET[i] * 170
            f.disc((x, ye), 7, UP, ka); f.circle((x, ye), 15 + 5 * beat_pulse(t), UP, ka * 0.6, 1)
            f.disc((x, yr), 7, CYAN, ka); f.circle((x, yr), 15 + 5 * beat_pulse(t), CYAN, ka * 0.6, 1)
            f.text('最乐观', x + 22, ye - 22, 22, 'serif_bold', UP, ka, 'l', mode='O')
            f.text('此后回报偏低', x + 22, yr + 24, 22, 'serif_bold', CYAN, ka, 'l', mode='O')


narr(57.53, 59.5, '大脑会把最近发生的，当成将要发生的。')
narr(59.65, 61.7, '研究发现：投资者对未来最乐观的时候，')
narr(61.78, 63.8, '往往正是此后回报偏低的时候。')


# ======================================================================== 1E 反身性飞轮 + Lollapalooza
RING_C = np.array([960.0, 500.0]); RING_R = 220.0
_r = np.random.default_rng(91)
RG_N = 700
RG_A0 = _r.random(RG_N) * 2 * math.pi
RG_DR = _r.standard_normal(RG_N) * 7


def ring_theta(t, t0, w0, w1, T, sign=1):
    x = cl((t - t0) / T)
    th = w0 * (t - t0) + (w1 - w0) * T * (x ** 3 - x ** 4 / 2)
    if t > t0 + T:
        th += (w1 - w0) * (t - t0 - T)
    return sign * th


def draw_flywheel(f, t, a, labels, colA, colB, t0, w0, w1, T, sign=1, heat=None, center=None, R=None):
    if a <= 0.003: return
    RING_C = np.array(center if center is not None else (960.0, 500.0)); RING_R = R or 220.0
    th = ring_theta(t, t0, w0, w1, T, sign)
    w = w0 + (w1 - w0) * eio((t - t0) / T)
    h = cl((w - w0) / (w1 - w0 + 1e-6)) if heat is None else heat
    col = mixc(colA, colB, h)
    f.circle(RING_C, RING_R, col, a * 0.35, 1)
    trail = int(2 + 10 * h)
    for k in range(trail):
        ang = RG_A0 + th - sign * k * 0.025 * (1 + w * 0.4)
        x = RING_C[0] + (RING_R + RG_DR) * np.cos(ang)
        y = RING_C[1] + (RING_R + RG_DR) * np.sin(ang)
        f.splat(x, y, col, a * (0.7 if k == 0 else 0.35 * (1 - k / trail)))
    pos = [(-math.pi / 2, 'm', 0, -1), (0, 'l', 1, 0), (math.pi / 2, 'm', 0, 1), (math.pi, 'r', -1, 0)]
    for i, ((ang, anc, dx, dy), (l1, l2)) in enumerate(zip(pos, labels)):
        x = RING_C[0] + math.cos(ang) * RING_R; y = RING_C[1] + math.sin(ang) * RING_R
        f.disc((x, y), 7, col, a)
        f.glow((x, y), 22, col, 0.5 * a * (0.5 + h))
        tx = x + dx * 34; ty = y + dy * 44
        f.text(l1, tx, ty - (8 if dy == 0 else (0 if dy > 0 else 10)), 26, 'serif_bold', INK, a, anc, mode='O')
        if l2:
            f.text(l2, tx, ty + (24 if dy >= 0 else 20), 15, 'sans_med', GREY, a, anc, mode='O')
    # 方向箭头
    for i in range(4):
        ang = -math.pi / 2 + i * math.pi / 2 + sign * math.pi / 4
        x = RING_C[0] + math.cos(ang) * RING_R; y = RING_C[1] + math.sin(ang) * RING_R
        tang = np.array([-math.sin(ang), math.cos(ang)]) * sign
        nrm = np.array([math.cos(ang), math.sin(ang)])
        p = np.array([x, y])
        f.line(p, p - tang * 12 + nrm * 7, col, a * 0.8, 2)
        f.line(p, p - tang * 12 - nrm * 7, col, a * 0.8, 2)


def s_reflexivity(f, t):
    if not (63.6 <= t <= 79.2): return
    a = env(t, 63.90, 78.5, 0.5, 0.4)
    scene_tag(f, t, 64.0, '反身性', 'REFLEXIVITY · GEORGE SOROS', 74.3)
    fa = a * (1 - eio((t - 74.4) / 0.8))
    draw_flywheel(f, t, fa, [('价格上涨', ''), ('赚钱效应', '故事更动听'), ('新资金入场', '借钱加杠杆'), ('更多买入', '')],
                  GOLD, UP, 64.2, 0.5, 5.0, 10.0, 1)
    # 中心：上涨本身成了买入的理由 → 杠杆让飞轮越转越快
    f.text('上涨本身', RING_C[0], RING_C[1] - 18, 30, 'serif_black', INK, fa * env(t, 70.3, 72.3, 0.5, 0.3), 'm',
           mode='O')
    f.text('成了买入的理由', RING_C[0], RING_C[1] + 24, 22, 'serif_med', UP2, fa * env(t, 70.5, 72.3, 0.5, 0.3),
           'm', mode='O')
    la_ = fa * env(t, 72.5, 1e9, 0.4, 0)
    if la_ > 0:
        f.text('杠杆', RING_C[0], RING_C[1] - 14, 40, 'serif_black', UP2, la_, 'm', mode='O', glow=0.4)
        f.text('让飞轮越转越快', RING_C[0], RING_C[1] + 30, 18, 'sans_med', INK, la_, 'm', mode='O')
        bx = RING_C[0] + math.cos(math.pi / 2) * 220
        f.circle((RING_C[0], RING_C[1] + 220), 16 + 20 * eo(((t - 72.5) % 0.53) / 0.5), UP, la_ * 0.7, 2)

    # Lollapalooza：四股力量拧成一股
    la = a * eio((t - 74.4) / 0.6)
    if la > 0.003:
        srcs = [((300, 260), '错失恐惧', UP), ((300, 760), '羊群效应', UP2), ((1620, 260), '近因偏差', GOLD),
                ((1620, 760), '反身性', C(255, 110, 180))]
        k = eo((t - 74.5) / 1.6)
        ctr = np.array([960.0, 520.0])
        for j, (p0, nm, col) in enumerate(srcs):
            p0 = np.array(p0, float)
            f.text(nm, p0[0], p0[1] + (-34 if p0[1] < 500 else 34), 22, 'serif_bold', col, la, 'm', mode='O')
            ts = np.linspace(0, 1, 60) * k
            mid = (p0 + ctr) / 2 + np.array([0, (-1 if j % 2 else 1) * 90])
            pts = (1 - ts)[:, None] ** 2 * p0 + 2 * ((1 - ts) * ts)[:, None] * mid + (ts ** 2)[:, None] * ctr
            # 绳子扭转
            tw = np.sin(ts * 18 - t * 6 + j * 1.57) * 6 * ts
            nrm = np.gradient(pts, axis=0)[:, ::-1] * [1, -1]
            nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9
            f.poly(pts + nrm * tw[:, None], col, la * 0.9, 2)
            f.disc(p0, 5, col, la)
        # 合力光柱
        b = eo((t - 75.9) / 0.9)
        if b > 0:
            for w_, aa in ((10, 0.25), (4, 0.6), (1.5, 1.0)):
                f.line(ctr, (ctr[0], ctr[1] - 520 * b), WHITE, la * aa, int(w_))
            f.glow(ctr, 60, GOLD, la * b)
        ca = la * env(t, 76.6, 78.4, 0.4, 0.4)
        f.text('LOLLAPALOOZA', 960, 700, 64, 'corm_sb', GOLD, ca, 'm', track=0.25, mode='O', t0=76.6, stag=0.03,
               dur=0.4, glow=0.5)
        f.text('芒格：多种心理倾向同时发力，效果不是简单相加，而是成倍放大', 960, 760, 19, 'sans_med', INK, ca, 'm',
               mode='O', t0=76.9, stag=0.01)


narr(66.03, 68.0, '索罗斯：价格不只反映现实，也在改变现实。')
narr(68.16, 70.2, '上涨让故事更动听，故事吸引更多资金，')
narr(70.28, 72.3, '上涨本身，成了买入的理由。')
narr(72.41, 74.4, '借来的钱，也在加速涌入——')
narr(74.53, 76.5, '四种偏差，彼此放大——')
narr(76.66, 78.6, '芒格称之为「Lollapalooza 效应」。')


# ======================================================================== 山顶 · 2026.6.25 创业板指
# 创业板指 2026.5.6–7.30 日 K（示意形状；标注的点位与涨跌幅为真实数据）
_CY_ANCH = [(0, 3780), (3, 3928.97), (5, 4010), (12, 4060), (17, 4120), (20, 4150), (27, 4080), (31, 4190),
            (35, 4251.42), (36, 4371.99), (38, 4300), (40, 4240), (45, 4050), (49, 3720), (52, 3790), (55, 3640),
            (58, 3590.99), (59, 3327.03), (60, 3255), (61, 3188)]
CY_N = 62
_ix = np.arange(CY_N)
_rr = np.random.default_rng(625)
CY_C = np.interp(_ix, [a for a, _ in _CY_ANCH], [v for _, v in _CY_ANCH]) * (1 + _rr.standard_normal(CY_N) * 0.006)
for _i, _v in _CY_ANCH:
    CY_C[_i] = _v
CY_O = np.r_[3760, CY_C[:-1]] * (1 + _rr.standard_normal(CY_N) * 0.004)
CY_H = np.maximum(CY_O, CY_C) * (1 + np.abs(_rr.standard_normal(CY_N)) * 0.005)
CY_L = np.minimum(CY_O, CY_C) * (1 - np.abs(_rr.standard_normal(CY_N)) * 0.005)
CY_O[36], CY_H[36], CY_L[36] = 4262, 4380.41, 4248          # 6.25：盘中历史新高
CY_O[59], CY_H[59], CY_L[59] = 3560, 3575, 3316.89          # 7.28：收跌 7.35%
CY_HI, CY_23, CY_28 = 36, 34, 59
CY_LAB = {0: '5.6', 3: '5.11', 20: '6.3', 34: '6.23', 49: '7.14', 59: '7.28'}


def s_summit_card(f, t):
    if not (78.5 <= t <= 87.6): return
    a = env(t, 78.78, 87.1, 0.5, 0.4)
    q = env(t, 78.85, 80.75, 0.4, 0.4)
    f.text('山顶，长什么样？', W / 2, 470, 72, 'serif_black', INK, a * q, 'm', track=0.2, mode='O', t0=78.85, stag=0.06,
           dur=0.5)
    b = a * eio((t - 80.8) / 0.5)
    if b <= 0.003: return
    x0, x1, y0, y1 = 220, 1560, 270, 760
    def yv(v): return y1 - (v - 3100) / (4500 - 3100) * (y1 - y0)
    def xv(i): return x0 + (i + 0.5) * (x1 - x0) / CY_N
    f.text('创业板指 · 2026.5–7 日K 示意', x0, y0 - 64, 17, 'sans_med', INK, b * 0.85, 'l', mode='O')
    f.text('走势为示意，标注的点位与涨跌幅为真实数据', x0, y0 - 38, 12, 'sans_light', GREY, b * 0.7, 'l', mode='O')
    f.line((x0, y1 + 12), (x1, y1 + 12), WHITE, 0.2 * b, 1, buf='L')
    # 先画到 6.25 山顶，停一拍，再画出之后的下跌
    show = keys(t, [(80.9, 0), (82.7, CY_HI + 1), (85.0, CY_HI + 1), (86.6, CY_N)], eio)
    for i in range(CY_N):
        if i >= show: break
        ka = b * cl(show - i)
        x = xv(i)
        col = UP if CY_C[i] >= CY_O[i] else DOWN
        big = i in (CY_HI, CY_28)
        f.line((x, yv(CY_H[i])), (x, yv(CY_L[i])), col, ka * (1 if big else 0.8), 1)
        top, bot = yv(max(CY_O[i], CY_C[i])), yv(min(CY_O[i], CY_C[i]))
        w = 8 if big else 6
        f.rrect_fill(x - w, top, x + w, max(bot, top + 2), 1, col, (0.95 if big else 0.75) * ka, 'E')
        if i in CY_LAB:
            f.text(CY_LAB[i], x, y1 + 34, 13, 'mono', GOLD if i == CY_23 else GREY, ka * 0.85, 'm', mode='O')
    # 6.25 历史新高
    ka = b * env(t, 82.6, 1e9, 0.4, 0)
    if ka > 0:
        hx, hy = xv(CY_HI), yv(CY_H[CY_HI])
        f.disc((hx, hy), 5, WHITE, ka)
        f.circle((hx, hy), 12 + 5 * beat_pulse(t), UP, ka * 0.8, 1)
        f.glow((hx, hy), 22, UP, 0.6 * ka)
        f.text('6.25 盘中 4380.41', hx - 18, hy - 44, 22, 'mono_med', INK, ka, 'r', mode='O')
        f.text('创业板指 历史新高', hx - 18, hy - 16, 16, 'sans_bold', UP2, ka, 'r', mode='O')
        k = eo((t - 85.0) / 1.6)
        f.dashed((hx, hy), (hx + (x1 + 140 - hx) * k, hy), GOLD, ka * 0.7, 1, 8, 6)
    # 6.23 两融余额首破 3 万亿
    ka = b * env(t, 83.1, 1e9, 0.4, 0)
    if ka > 0:
        mx = xv(CY_23)
        f.line((mx, y1 + 12), (mx, yv(CY_C[CY_23]) + 30), GOLD, ka * 0.6, 1)
        f.disc((mx, y1 + 12), 4, GOLD, ka)
        f.text('两融余额首破 3 万亿元', mx - 10, y1 - 16, 15, 'sans_bold', GOLD, ka, 'r', mode='O')
    # 7.28 单日 −7.35%；较高点 −24%；7.30 抹平全年涨幅
    ka = b * env(t, 86.1, 1e9, 0.3, 0)
    if ka > 0:
        cx_, cy_ = xv(CY_28), yv(CY_L[CY_28])
        f.text('7.28 单日 −7.35%', cx_ - 16, cy_ + 30, 16, 'mono_med', DOWN2, ka, 'r', mode='O')
        bx = x1 + 70
        hy, ly = yv(4380.41), yv(3316.89)
        k = eo((t - 86.1) / 0.6)
        f.line((bx, hy), (bx, hy + (ly - hy) * k), DOWN, ka, 2)
        f.line((bx - 8, hy), (bx + 8, hy), DOWN, ka, 2)
        if k > 0.95: f.line((bx - 8, ly), (bx + 8, ly), DOWN, ka, 2)
        f.text('−24%', bx + 18, (hy + ly) / 2 - 10, 44, 'mono_med', DOWN, ka, 'l', mode='O', glow=0.3)
        f.text('较高点 · 7.28', bx + 20, (hy + ly) / 2 + 30, 15, 'sans_med', INK, ka, 'l', mode='O')
        f.text('7.30 抹平全年涨幅', bx + 20, (hy + ly) / 2 + 56, 15, 'sans_med', GREY, ka, 'l', mode='O')


narr(80.91, 82.9, '6 月 25 日，创业板指创下历史新高。')
narr(83.03, 85.0, '两天前，两融余额刚刚首破 3 万亿。')
narr(85.16, 87.1, '一个月后，它较高点跌去 24%。')


# ---------------------------------------------------------------- 抽空段：增量买盘衰竭
_r = np.random.default_rng(871)
FL_N = 1400
FL_SIDE = np.where(_r.random(FL_N) < 0.5, -1, 1)
FL_PH = _r.random(FL_N)
FL_V = 0.28 + _r.random(FL_N) * 0.22
FL_H = _r.random(FL_N)
FL_J = _r.standard_normal(FL_N)


def buy_rate(ts):
    """t 时刻新进场的买盘强度：越来越弱，但不为零"""
    return 0.08 + 0.92 * np.exp(-np.clip(ts - 87.3, 0, None) / 1.5)


def sell_rate(ts):
    return 0.10 + 0.30 * eio_np((ts - 89.0) / 3.5)


def slope_xy(side, s):
    x0 = np.where(side < 0, 90.0, 1830.0)
    x = x0 + (SUMMIT[0] - x0) * s
    return x, ridge(x) - 7


def draw_flows(f, t, a, push):
    if a <= 0.003: return
    cx, cy = SUMMIT
    # 买盘：沿山坡向上
    s = (FL_PH + FL_V * t) % 1.0
    born = t - s / FL_V
    vis = FL_H < buy_rate(born)
    x, y = slope_xy(FL_SIDE, s)
    y = y - 22 + FL_J * 6
    P = (np.c_[x, y] - [cx, cy + 120]) * push + [cx, cy + 120]
    A = a * vis * np.clip((1 - s) * 6, 0, 1) * np.clip(s * 10, 0, 1)
    f.dots(P[:, 0], P[:, 1], mixc(UP, GOLDL, 0.35), A, 1.6)
    Pt = P - np.c_[np.sign(SUMMIT[0] - P[:, 0]) * 8, np.zeros(FL_N)]
    f.splat(Pt[:, 0], Pt[:, 1], UP, A * 0.5)
    # 卖盘：从山顶往下
    s2 = (FL_PH * 1.7 + FL_V * 0.8 * t) % 1.0
    born2 = t - s2 / (FL_V * 0.8)
    vis2 = FL_H < sell_rate(born2)
    x2, y2 = slope_xy(-FL_SIDE, 1 - s2)
    y2 = y2 - 44 + FL_J * 6
    P2 = (np.c_[x2, y2] - [cx, cy + 120]) * push + [cx, cy + 120]
    f.dots(P2[:, 0], P2[:, 1], DOWN2, a * vis2 * np.clip(s2 * 6, 0, 1) * np.clip((1 - s2) * 10, 0, 1), 1.6)


def s_summit_break(f, t):
    if not (86.9 <= t <= T_D2 + 0.05): return
    a = env(t, 87.29, T_D2, 0.8, 0.0)
    arrive = keys(t, [(87.3, 0.35), (89.4, 0.97), (90.4, 1.1)], eio)
    push = 1.0 + 0.03 * (t - 87.3) - 0.06 * eio((t - 93.0) / 0.66)
    draw_mountain(f, t, a, push=push, crowd=1.0, crowd_arrive=arrive)
    draw_flows(f, t, a * (1 - eio((t - 93.2) / 0.4)), push)
    # 你：最后一批买家之一
    yk = eio3((t - 88.9) / 1.4)
    start = np.array([300.0, 980.0]); end = np.array([SUMMIT[0], SUMMIT[1] - 36])
    p = start + (end - start) * yk + np.array([0, -120]) * math.sin(yk * math.pi)
    p = (p - [SUMMIT[0], SUMMIT[1] + 120]) * push + [SUMMIT[0], SUMMIT[1] + 120]
    draw_you(f, p[0], p[1], a * cl((t - 88.6) / 0.4), WHITE, '你', t, 5, False, lab_dy=-28)
    heart_ring(f, p[0], p[1], t, WHITE, a * cl((t - 88.6) / 0.4))
    f.glow((SUMMIT[0], (SUMMIT[1] - 20 - 120) * push + 120 + 0), 60, UP, 0.12 * heart(t) * a)
    # 买盘 vs 卖盘：任何时候都有买有卖，变的是力量对比
    ga = a * env(t, 87.6, T_D2 - 0.2, 0.6, 0.3)
    if ga > 0:
        gx, gy = 160, 250
        br, sr = float(buy_rate(t)), float(sell_rate(t))
        f.text('新增买盘', gx, gy, 16, 'sans_bold', UP2, ga, 'l', mode='O')
        f.text('卖盘', gx, gy + 40, 16, 'sans_bold', DOWN2, ga, 'l', mode='O')
        for k, (v, col) in enumerate(((br, UP), (sr, DOWN))):
            yy = gy + k * 40
            f.rrect(gx + 90, yy - 9, gx + 390, yy + 9, 4, WHITE, ga * 0.25, 1, buf='L')
            f.rrect_fill(gx + 92, yy - 7, gx + 92 + 296 * v, yy + 7, 3, col, 0.8 * ga, 'E')
        if br < sr:
            f.text('买盘接不上了', gx, gy + 86, 22, 'serif_bold', INK, ga * cl((t - 91.0) / 0.4), 'l', mode='O')
    f.dark = 0.25 * eio((t - 92.4) / 1.2)


narr(87.5, 89.3, '山顶，往往不是某个价格，')
narr(89.41, 91.4, '而是买盘开始衰竭的时刻——')
narr(91.54, 93.5, '新的买盘接不住卖盘，价格靠什么上涨？')

SCENES_A = [s_cold_open, s_title, s_2026_rise, s_fomo, s_herd, s_recency, s_reflexivity, s_summit_card,
            s_summit_break]
