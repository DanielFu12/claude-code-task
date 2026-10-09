"""第三幕「清醒 · 巴菲特与芒格」+ 纪律 + 终章 + 片尾品牌。"""
from common import *  # noqa
from scenes_a import ridge, CO_X, CO_Y, CO_PI, polyline_upto
from scenes_b import chapter_stamp
import brand as _brand                                   # 仓库根目录 brand/（film.py 已加入 sys.path）
from brand import load_logo

# ======================================================================== 两个人
_r = np.random.default_rng(157)
BU_N = 1600
BU_A = _r.random(BU_N) * 2 * math.pi
BU_V = 300 + _r.random(BU_N) ** 0.5 * 1300


def s_names(f, t):
    if not (T_D3 - 0.05 <= t <= 162.2): return
    x = t - T_D3
    if x < 3.0:
        r = BU_V * (1 - math.exp(-x * 2.5)) / 2.5
        px = 960 + np.cos(BU_A) * r; py = 500 + np.sin(BU_A) * r * 0.7
        f.dots(px, py, mixc(GOLD, GOLDL, 0.5), (1 - eio(x / 3.0)) * 0.9, 1.0)
        if x < 1.0:
            f.circle((960, 500), 1600 * eo(x), GOLD, (1 - x) * 0.8, 3)
    a = env(t, T_D3 + 0.05, 161.4, 0.5, 0.6)
    chapter_stamp(f, t, T_D3 + 0.1, 161.4, '03', '清醒', '巴菲特与芒格的答案', y=250)
    for i, (cn, en, cx) in enumerate((('沃伦·巴菲特', 'WARREN BUFFETT', 600), ('查理·芒格', 'CHARLIE MUNGER', 1320))):
        t0 = T_D3 + 0.3 + i * 0.25
        f.text(en, cx, 470, 50, 'corm_sb', GOLD, a, 'm', track=0.22, mode='O', t0=t0, stag=0.03, dur=0.5, glow=0.3)
        f.text(cn, cx, 540, 30, 'serif_bold', INK, a, 'm', track=0.25, mode='O', t0=t0 + 0.3, stag=0.05, dur=0.5)
    f.text('&', 960, 478, 64, 'corm', GOLD, a * 0.8, 'm', mode='O', t0=T_D3 + 0.5, dur=0.6)
    ln = 520 * eo((t - T_D3 - 0.6) / 1.2)
    f.line((960 - ln, 620), (960 + ln, 620), GOLD, a * 0.4, 1, buf='L')


narr(157.7, 161.5, '有两个人，用一生回答了这个问题。')


# ======================================================================== 价格与价值 · 市场先生
PV_X = np.linspace(200, 1720, 380)
_u = np.linspace(0, 1, 380)
PV_V = 640 - 240 * _u - 12 * np.sin(_u * 9)
PV_P = PV_V - 150 * np.sin(_u * 13.0 + 0.6) * (0.6 + 0.4 * np.sin(_u * 3.1)) - smooth_noise(380, 61, 5) * 40


def s_price_value(f, t):
    if not (161.4 <= t <= 172.7): return
    a = env(t, 161.66, 172.1, 0.5, 0.4)
    scene_tag(f, t, 161.75, '价格与价值', 'PRICE IS WHAT YOU PAY · VALUE IS WHAT YOU GET', 172.0)
    u = eo((t - 161.9) / 4.5)
    n = max(2, int(u * 379))
    # 两条线之间：便宜处金色，昂贵处红色
    for i in range(0, n, 3):
        cheap = PV_P[i] > PV_V[i]
        f.line((PV_X[i], PV_V[i]), (PV_X[i], PV_P[i]), GOLD if cheap else UP, a * (0.16 if cheap else 0.10), 1,
               buf='L')
    vp, vh = polyline_upto(PV_X, PV_V, u)
    pp, ph = polyline_upto(PV_X, PV_P, u)
    f.poly(vp, GOLD, a, 3)
    draw_price(f, pp, a * 0.9, 2, smooth=5)
    f.text('价值', vh[0] + 14, vh[1] - 4, 22, 'serif_bold', GOLD, a, 'l', mode='O')
    # 市场先生每拍报一个价
    k = np.searchsorted(BEATS, t)
    ma = a * env(t, 165.9, 170.0, 0.4, 0.4)
    if ma > 0:
        price = 60 + 55 * math.sin(k * 2.39) + 25 * math.sin(k * 0.71)
        cheap = PV_P[n - 1] > PV_V[n - 1]
        x0, y0 = ph[0] - 250, ph[1] - 92 if ph[1] > 330 else ph[1] + 40
        f.panel(x0, y0, x0 + 230, y0 + 62, ma, UP if not cheap else DOWN, r=10)
        f.text(f'市场先生：今天 {price:.0f} 元！', x0 + 115, y0 + 31, 19, 'sans_bold', INK, ma, 'm', mode='O')
        f.line((x0 + 200, y0 + 62 if y0 < ph[1] else y0), ph, GREY, ma * 0.6, 1)
    # 只在低得离谱时出手
    ba = a * env(t, 169.9, 1e9, 0.4, 0)
    if ba > 0:
        gap = PV_P - PV_V
        idx = [i for i in range(5, 374) if gap[i] > 90 and gap[i] >= gap[i - 5:i + 6].max()]
        for j, i in enumerate(idx):
            kk = ba * cl((t - 170.0 - j * 0.15) / 0.3)
            f.disc((PV_X[i], PV_P[i]), 7, GOLD, kk)
            f.circle((PV_X[i], PV_P[i]), 14 + 4 * beat_pulse(t), GOLD, kk * 0.7, 1)
            f.text('买', PV_X[i], PV_P[i] + 34, 22, 'serif_black', GOLD, kk, 'm', mode='O')


narr(163.79, 165.8, '巴菲特：价格是你付出的，价值是你得到的。')
narr(165.91, 168.0, '格雷厄姆：「市场先生」每天给你报一个价。')
narr(168.04, 170.1, '你不必理他——')
narr(170.17, 172.2, '只在他报价低得离谱时，和他做生意。')


# ======================================================================== 安全边际：桥
BR_X0, BR_X1, BR_Y = 330, 1450, 520


def s_margin(f, t):
    if not (172.1 <= t <= 181.2): return
    a = env(t, 172.29, 180.6, 0.5, 0.4)
    scene_tag(f, t, 172.4, '安全边际', 'MARGIN OF SAFETY · BENJAMIN GRAHAM', 180.5)
    u = eo((t - 172.4) / 1.6)
    xs = np.linspace(BR_X0, BR_X0 + (BR_X1 - BR_X0) * u, 120)
    f.line((BR_X0 - 40, BR_Y), (BR_X0 + (BR_X1 - BR_X0 + 80) * u - 40, BR_Y), GOLD, a, 3)
    ay = BR_Y + 230 - 230 * (1 - ((xs - (BR_X0 + BR_X1) / 2) / ((BR_X1 - BR_X0) / 2)) ** 2)
    f.poly(np.c_[xs, ay], GOLD, a * 0.9, 2)
    for x in np.arange(BR_X0 + 56, BR_X0 + (BR_X1 - BR_X0) * u, 56):
        yy = BR_Y + 230 - 230 * (1 - ((x - (BR_X0 + BR_X1) / 2) / ((BR_X1 - BR_X0) / 2)) ** 2)
        f.line((x, BR_Y), (x, yy), GOLD, a * 0.45, 1)
    for x in (BR_X0, BR_X1):
        f.line((x, BR_Y), (x, BR_Y + 260), GOLD, a * 0.8 * u, 2)
    for k in range(5):
        wy = BR_Y + 280 + k * 18
        wx = np.linspace(200, 1580, 120)
        f.poly(np.c_[wx, wy + 4 * np.sin(wx * 0.02 + t * 2 + k)], BLUE, a * 0.18 * (1 - k * 0.15), 1, buf='L')
    f.text('设计承重 30,000 磅', (BR_X0 + BR_X1) / 2, BR_Y - 150, 30, 'serif_bold', GOLD, a * cl((t - 173.4) / 0.5),
           'm', mode='O')
    # 卡车
    tk = cl((t - 174.0) / 3.6)
    if 174.0 < t < 178.6:
        tx = lerp(BR_X0 - 120, BR_X1 + 40, eio(tk))
        f.rrect(tx, BR_Y - 54, tx + 92, BR_Y - 6, 4, INK, a, 2)
        f.rrect(tx + 92, BR_Y - 40, tx + 124, BR_Y - 6, 4, INK, a, 2)
        f.circle((tx + 20, BR_Y - 4), 6, INK, a, 2); f.circle((tx + 104, BR_Y - 4), 6, INK, a, 2)
        f.text('10,000 磅', tx + 56, BR_Y - 80, 20, 'mono_med', INK, a, 'm', mode='O')
    # 承重计：价值、价格与中间的余量
    ga = a * env(t, 176.4, 1e9, 0.5, 0)
    if ga > 0:
        gx, gy0, gy1 = 1640, 280, 760
        f.rrect(gx - 30, gy0, gx + 30, gy1, 6, GOLD, ga, 1)
        hv = (gy1 - gy0)
        hp = hv / 3 * eo((t - 176.6) / 0.8)
        f.rrect_fill(gx - 26, gy1 - hp, gx + 26, gy1 - 4, 4, INK, 0.7 * ga, 'L')
        f.text('能承受的', gx + 46, gy0 + 4, 16, 'sans_med', GOLD, ga, 'l', mode='O')
        f.text('实际承受的', gx + 46, gy1 - hv / 3, 16, 'sans_med', INK, ga, 'l', mode='O')
        ka = ga * env(t, 177.4, 1e9, 0.5, 0)
        f.line((gx - 50, gy0 + 4), (gx - 50, gy1 - hv / 3), GOLD, ka, 2)
        f.text('安全边际', gx - 66, (gy0 + gy1 - hv / 3) / 2 - 14, 26, 'serif_black', GOLD, ka, 'r', mode='O', glow=0.3)
        f.text('= 你犯错的空间', gx - 66, (gy0 + gy1 - hv / 3) / 2 + 22, 17, 'sans_med', INK, ka, 'r', mode='O')


narr(174.42, 176.4, '能承重 3 万磅的桥，只让 1 万磅的车通过。')
narr(176.54, 178.6, '安全边际，不是为了赚得更多，')
narr(178.67, 180.7, '而是为了在你看错的时候，依然能活下来。')


# ======================================================================== 能力圈
HOT = ['AI 算力', '光模块', '存储芯片', '机器人', '某某概念', '小道消息', '群里推荐', '翻倍牛股', '内部消息', '题材炒作',
       '大V荐股', '神秘资金']
_r = np.random.default_rng(181)
HOT_R = 330 + _r.random(len(HOT)) * 360
HOT_A = _r.random(len(HOT)) * 2 * math.pi
HOT_W = (0.25 + _r.random(len(HOT)) * 0.4) * np.where(_r.random(len(HOT)) < 0.5, 1, -1)
IN = [('看得懂的生意', 0, -20, 30), ('现金流清楚', -110, 70, 17), ('十年后还在', 110, 70, 17), ('护城河', 0, 135, 17),
      ('合理的价格', 0, -115, 17)]


def s_circle(f, t):
    if not (180.6 <= t <= 189.7): return
    a = env(t, 180.77, 189.1, 0.5, 0.4)
    scene_tag(f, t, 180.85, '能力圈', 'CIRCLE OF COMPETENCE', 189.0)
    c = (960, 520); R = 230 * eo((t - 180.9) / 0.9)
    f.circle(c, R, GOLD, a, 3)
    f.circle(c, R + 10 + 6 * beat_pulse(t), GOLD, a * 0.25, 1)
    f.glow(c, R * 0.5, GOLD, 0.10 * a)
    for i, (s, dx, dy, sz) in enumerate(IN):
        f.text(s, c[0] + dx, c[1] + dy, sz, 'serif_bold' if i == 0 else 'sans_med', INK if i == 0 else GOLDL,
               a * cl((t - 181.6 - i * 0.15) / 0.4), 'm', mode='O')
    for i, s in enumerate(HOT):
        ang = HOT_A[i] + HOT_W[i] * (t - 181)
        r = HOT_R[i] + 18 * math.sin(t * 1.3 + i)
        x = c[0] + math.cos(ang) * r * 1.45; y = c[1] + math.sin(ang) * r * 0.82
        if not (-50 < x < W + 50): continue
        ha = a * cl((t - 181.4 - i * 0.08) / 0.4) * (0.55 + 0.45 * math.sin(t * 5 + i * 2) ** 2)
        f.text(s, x, y, 20, 'sans_bold', UP2 if i % 3 else UP, ha, 'm', mode='O')
        f.glow((x, y), 30, UP, 0.12 * ha)
    qa = a * env(t, 185.0, 1e9, 0.5, 0)
    if qa > 0:
        f.panel(1360, 780, 1800, 850, qa, UP)
        f.text('它五年后，靠什么赚钱？', 1580, 815, 24, 'serif_bold', INK, qa, 'm', mode='O')


narr(182.9, 185.0, '巴菲特：能力圈多大不重要，知道边界才重要。')
narr(185.02, 187.1, '说不清它五年后靠什么赚钱？')
narr(187.15, 189.2, '那你买的不是公司，而是别人的情绪。')


# ======================================================================== 逆向思考
NQ_M = np.linspace(0, 5, 200)
NQ = np.interp(NQ_M, [0, 1.0, 1.6, 2.2, 2.6, 3.2, 3.8, 4.4, 5.0],
               [1800, 2700, 4100, 5048, 3300, 2000, 1400, 1114, 1600]) * (1 + smooth_noise(200, 9, 3) * 0.03)
NQ[int(2.2 / 5 * 199)] = 5048
NQ[int(4.4 / 5 * 199)] = 1114
DONTS = ['借钱炒股', '追最热的股票', '满仓押注一只', '听消息买卖', '越跌越补，却说不出理由']


def s_invert(f, t):
    if not (189.1 <= t <= 200.3): return
    a = env(t, 189.28, 199.8, 0.5, 0.4)
    scene_tag(f, t, 189.4, '逆向思考', 'INVERT, ALWAYS INVERT · CHARLIE MUNGER', 199.7)
    # 山被倒转过来
    ra = a * (1 - eio((t - 191.3) / 0.6))
    if ra > 0.003:
        th = math.pi * eio3((t - 189.6) / 1.4)
        xs = np.linspace(200, 1720, 200)
        ys = ridge(xs) - 100
        cy = 540
        Y = cy + (ys - cy) * math.cos(th)
        f.poly(np.c_[xs, Y], GOLD, ra, 2)
        f.text('山顶', 960, cy + (ridge(960) - 100 - 40 - cy) * math.cos(th), 22, 'serif_bold', UP2, ra, 'm', mode='O')
        f.text('倒过来想', 960, 820, 40, 'serif_black', GOLD, ra * cl((t - 190.4) / 0.4), 'm', track=0.3, mode='O')
    la = a * env(t, 191.3, 195.5, 0.5, 0.5)
    if la > 0.003:
        f.text('「我只想知道我会死在哪里，这样我就永远不去那儿。」', 960, 255, 32, 'serif_bold', GOLD, la, 'm', mode='O',
               t0=191.4, stag=0.02, dur=0.4)
        f.text('—— 查理·芒格', 1300, 305, 18, 'sans_med', GREY, la, 'm', mode='O')
        f.text('怎样才能保证亏钱？', 960, 395, 30, 'serif_black', INK, la * cl((t - 192.6) / 0.4), 'm', mode='O')
        for i, s in enumerate(DONTS):
            t0 = 192.9 + i * 0.27
            ia = la * cl((t - t0) / 0.3)
            y = 465 + i * 64
            k = eo((t - 193.6 - i * 0.27) / 0.35)
            f.text(s, 960, y, 28, 'sans_med', mixc(INK, GREY, k * 0.6), ia, 'm', mode='O')
            w = text_width(s, 'sans_med', 28) / 2 + 20
            f.line((960 - w, y + 2), (960 - w + 2 * w * k, y + 2), GOLD, ia, 2)
    # 1999 年的巴菲特
    na = a * eio((t - 195.5) / 0.5)
    if na > 0.003:
        x0, x1, y0, y1 = 300, 1620, 360, 790
        def yv(v): return y1 - (v - 800) / (5400 - 800) * (y1 - y0)
        u = eo((t - 195.7) / 2.4)
        xs = x0 + (x1 - x0) * NQ_M / 5
        pts, head = polyline_upto(xs, yv(NQ), u)
        draw_price(f, pts, na, 2, smooth=5)
        f.text('纳斯达克综合指数 1998–2003 · 示意', x0, y0 - 50, 16, 'sans_med', INK, na * 0.8, 'l', mode='O')
        for yr in range(6):
            x = x0 + (x1 - x0) * yr / 5
            f.text(str(1998 + yr), x, y1 + 30, 13, 'mono', GREY, na * 0.7, 'm', mode='L')
        f.line((x0, y1 + 10), (x1, y1 + 10), WHITE, na * 0.2, 1, buf='L')
        xb = x0 + (x1 - x0) * 1.95 / 5
        ba = na * cl((t - 196.0) / 0.4)
        f.dashed((xb, y0 - 10), (xb, y1), GOLD, ba * 0.7, 1, 6, 5)
        f.text('1999.12', xb - 12, y0 + 10, 16, 'mono_med', GOLD, ba, 'r', mode='O')
        f.text('《巴伦周刊》：「沃伦，你怎么了？」', xb - 12, y0 + 40, 18, 'serif_bold', INK, ba, 'r', mode='O')
        f.text('巴菲特拒绝追逐看不懂的科技股', xb - 12, y0 + 68, 15, 'sans_med', GREY, ba, 'r', mode='O')
        if u > 0.45:
            i = int(2.2 / 5 * 199); px, py = xs[i], yv(NQ[i])
            ka = na * cl((u - 0.45) / 0.05)
            f.disc((px, py), 5, UP, ka)
            f.text('2000.3  5048 点', px + 16, py - 6, 18, 'mono_med', UP2, ka, 'l', mode='O')
        if u > 0.88:
            i = int(4.4 / 5 * 199); px, py = xs[i], yv(NQ[i])
            ka = na * cl((u - 0.88) / 0.05)
            f.disc((px, py), 5, DOWN, ka)
            f.text('2002.10  1114 点', px, py + 30, 18, 'mono_med', DOWN2, ka, 'm', mode='O')
            f.text('−78%', px, py + 64, 30, 'mono_med', DOWN, ka, 'm', mode='O')


narr(191.4, 193.4, '芒格说：反过来想，总是反过来想。')
narr(193.53, 195.5, '先问：怎样才能保证亏钱？然后，一件都不做。')
narr(195.65, 197.7, '1999 年，巴菲特因不买科技股被嘲「过时」。')
narr(197.78, 199.8, '此后不到三年，纳斯达克跌去近八成。')


# ======================================================================== 概率与赔率：赛马彩池
_r = np.random.default_rng(200)
BET_N = 900
BET_SIDE = np.where(_r.random(BET_N) < 0.8, 0, 1)            # 八成的钱押明星股
BET_T = 200.5 + np.sort(_r.random(BET_N)) ** 0.8 * 2.6
BET_SRC = np.c_[100 + _r.random(BET_N) * 500, 900 + _r.random(BET_N) * 150]
BET_J = _r.standard_normal((BET_N, 2))


def s_odds(f, t):
    if not (199.7 <= t <= 208.8): return
    a = env(t, 199.90, 208.2, 0.5, 0.4)
    scene_tag(f, t, 200.0, '概率与赔率', 'ODDS, NOT STORIES · PARI-MUTUEL', 208.1)
    lanes = [(420, '明星股 · 人人都押', 0.60, 3.0, 1.3, UP), (640, '冷门股 · 无人问津', 0.25, 1.6, 6.0, GOLD)]
    xs0, xs1 = 230, 1000
    px0, pw = 1110, 330                                    # 奖池
    f.line((xs1, 340), (xs1, 720), WHITE, a * 0.45, 1)
    f.text('终点', xs1, 318, 14, 'sans_med', GREY, a, 'm', mode='O')
    f.text('奖池（谁押得多，谁的赔率就低）', px0, 318, 14, 'sans_med', GREY, a * cl((t - 200.6) / 0.4), 'l', mode='O')
    # 下注的钱：从人群涌入两个奖池
    p = np.clip((t - BET_T) / 0.9, 0, 1)
    pe = p * p * (3 - 2 * p)
    tgt = np.c_[px0 + 20 + np.abs(BET_J[:, 0]) * 40, np.where(BET_SIDE == 0, 420, 640) + BET_J[:, 1] * 6]
    P = BET_SRC + (tgt - BET_SRC) * pe[:, None] + np.c_[np.zeros(BET_N), -160 * np.sin(np.pi * pe)]
    fly = (t > BET_T) & (p < 1)
    col = np.where(BET_SIDE[:, None] == 0, np.array(UP2, np.float32), np.array(GOLD, np.float32))
    f.dots(P[fly, 0], P[fly, 1], col[fly], a * 0.8, 1.0)
    filled = (p >= 1)
    tot = max(1, filled.sum())
    for j, (y, nm, pw_, od0, od1, col_) in enumerate(lanes):
        la = a * cl((t - 200.3 - j * 0.3) / 0.4)
        f.line((xs0, y + 36), (xs1, y + 36), WHITE, la * 0.12, 1, buf='L')
        f.text(nm, xs0, y - 46, 22, 'serif_bold', col_, la, 'l', mode='O')
        f.text(f'胜率 {pw_ * 100:.0f}%', xs0, y - 18, 15, 'sans_med', INK, la, 'l', mode='O')
        # 奖池条
        share = (filled & (BET_SIDE == j)).sum() / BET_N
        f.rrect(px0, y - 16, px0 + pw, y + 16, 6, col_, la * 0.5, 1, buf='L')
        f.rrect_fill(px0 + 2, y - 14, px0 + 2 + (pw - 4) * share / 0.8, y + 14, 5, col_, 0.55 * la, 'L')
        k = eio((t - 200.6) / 2.6)
        od = od0 + (od1 - od0) * k
        f.text(f'赔率 {od:.1f} 倍', px0 + pw + 22, y, 26, 'mono_med', col_, la, 'l', mode='O')
        # 赛跑
        sp = 1.0 if j == 0 else 0.9
        kk = eio((t - 202.6) / 1.8) * sp
        hx = lerp(xs0 + 20, xs1 - 10, kk) + 2 * math.sin(t * 9 + j)
        hy = y + 3 * math.sin(t * 12 + j * 2)
        run = 202.6 < t < 204.4
        for q in range(10):
            f.disc((hx - q * 9 * (1 if run else 0.15), hy), 5 - q * 0.4, col_, la * (1 - q / 10) * 0.85)
        f.glow((hx, hy), 18, col_, la * 0.6)
        # 期望值
        ea = la * env(t, 204.2 + j * 0.45, 1e9, 0.4, 0)
        if ea > 0:
            ev = pw_ * od1
            f.text(f'{pw_:.2f} × {od1:.1f} = {ev:.2f}', px0, y + 64, 28, 'mono_med', col_, ea, 'l', mode='O')
            f.text('长期下注，注定亏钱' if ev < 1 else '长期下注，占据优势', px0 + 300, y + 66, 17, 'sans_bold',
                   DOWN2 if ev < 1 else GOLD, ea, 'l', mode='O')
    ha = a * env(t, 204.0, 1e9, 0.4, 0)
    f.text('期望 = 胜率 × 赔率', px0, 780, 18, 'sans_med', GREY, ha, 'l', mode='O')
    f.text('示意：数字仅用于说明「赔率」的含义', 1720, 830, 13, 'sans_light', GREY, ha * 0.8, 'r', mode='O')
    f.text('人群', 330, 880, 16, 'sans_med', GREY, a * env(t, 200.4, 203.4, 0.4, 0.5), 'm', mode='O')


narr(202.03, 204.0, '芒格说，股市就像赛马场的彩池：')
narr(204.15, 206.2, '最好的马，未必是最好的下注。')
narr(206.28, 208.3, '问题不是它好不好，而是这个价格划不划算。')


# ======================================================================== 奥德修斯与桅杆
SIRENS = ['再不上车就晚了', '这次不一样', '翻倍只是开始', '群里都赚了', '满仓干！', 'AI 改变一切', '最后的机会', '别人都在买',
          '跌了就是机会，补！', '内部消息']
_r = np.random.default_rng(208)
SI_A = np.linspace(0, 2 * math.pi, len(SIRENS), endpoint=False) + _r.random(len(SIRENS)) * 0.4
SI_T = 208.6 + _r.random(len(SIRENS)) * 3.5
MAST_X = 960


def s_ulysses(f, t):
    if not (208.2 <= t <= 218.2): return
    a = env(t, 208.40, 217.2, 0.6, 0.8)
    scene_tag(f, t, 208.5, '奥德修斯的绳子', 'THE ULYSSES CONTRACT', 216.6, big_dur=1.6)
    deck = 640
    hull = [(700, deck), (1220, deck), (1160, deck + 70), (760, deck + 70)]
    f.poly(hull, GOLD, a, 2, closed=True)
    f.line((MAST_X, deck), (MAST_X, 270), GOLD, a, 3)
    f.line((MAST_X - 170, 330), (MAST_X + 170, 330), GOLD, a * 0.7, 2)
    f.fillpoly([(MAST_X - 160, 335), (MAST_X + 160, 335), (MAST_X + 190, 560), (MAST_X - 190, 560)], GOLD, 0.05 * a)
    f.poly([(MAST_X - 160, 335), (MAST_X - 190, 560)], GOLD, a * 0.35, 1)
    f.poly([(MAST_X + 160, 335), (MAST_X + 190, 560)], GOLD, a * 0.35, 1)
    # 人
    f.circle((MAST_X, 420), 13, INK, a, 2)
    f.line((MAST_X, 434), (MAST_X, 520), INK, a, 2)
    # 绳子：一圈圈缠上
    rk = eio((t - 210.5) / 1.6)
    for i in range(5):
        if rk * 5 < i: break
        y = 450 + i * 16
        kk = cl(rk * 5 - i)
        f.arc((MAST_X, y), 22, -0.2, -0.2 + math.pi * 2 * kk, GOLDL, a * (0.7 + 0.3 * (t > 214.7)), 3)
    if t > 214.7:
        f.glow((MAST_X, 485), 36, GOLD, a * 0.25 * env(t, 214.7, 1e9, 0.5, 0))
    # 海浪
    for k in range(6):
        wx = np.linspace(260, 1660, 160)
        wy = deck + 60 + k * 20 + 6 * np.sin(wx * 0.015 + t * 1.6 + k * 0.8)
        f.poly(np.c_[wx, wy], BLUE, a * (0.35 - k * 0.04), 1, buf='L')
    # 塞壬的歌声：涌向桅杆，在绳子外碎掉
    for i, s in enumerate(SIRENS):
        p = (t - SI_T[i]) / 3.2
        if p <= 0 or p > 1.4: continue
        r = lerp(820, 330, eo(min(p, 1)))
        ang = SI_A[i] + 0.3 * p
        x = MAST_X + math.cos(ang) * r * 1.1; y = 460 + math.sin(ang) * r * 0.55
        sa = a * cl(p / 0.15) * (1 - cl((p - 1.0) / 0.4))
        f.text(s, x, y, 22, 'serif_bold', UP2, sa, 'm', mode='O')
        f.glow((x, y), 26, UP, 0.15 * sa)


narr(208.5, 210.4, '人性改不了。所以，奥德修斯在出海之前，')
narr(210.53, 212.5, '让水手把自己牢牢绑在桅杆上。')
narr(212.65, 214.7, '他依然听得见塞壬的歌声，却碰不到船舵。')
narr(214.78, 216.8, '纪律就是那根绳子：冷静时写下，疯狂时执行。')

RULES = [
    ('写下来，再买入', '为什么买？值多少？什么情况证明我错了？写不出来，就不买。'),
    ('只买打折的价值', '价格明显低于你保守估算的价值，才出手；没有安全边际，就等。'),
    ('不借钱，设上限', '不加杠杆；单只股票设仓位上限；只用三年内用不到的钱。'),
    ('越想冲，越要等', '心跳加速时先冷静 72 小时；成交天量、两融新高时，只检查，不加仓。'),
    ('让规则替你高抛低吸', '定好股债比例，定期再平衡：涨多了卖一点，跌多了买一点。'),
]
RULE_T = [219.03 + i * 3.19 for i in range(5)]


def s_checklist(f, t):
    if not (216.5 <= t <= 236.6): return
    a = env(t, 216.91, 235.8, 0.6, 0.5)
    mx = 330
    f.text('你的「桅杆清单」', 960, 175, 46, 'serif_black', INK, a, 'm', track=0.15, mode='O', t0=217.0, stag=0.05)
    f.text('在冷静时写下 · 在疯狂时执行', 960, 228, 17, 'sans_med', GOLD, a, 'm', track=0.4, mode='O', t0=217.4,
           stag=0.02)
    mk = eo((t - 217.2) / 1.2)
    f.line((mx, 280), (mx, 280 + 600 * mk), GOLD, a, 3)
    f.glow((mx, 280 + 600 * mk), 16, GOLD, a * 0.6)
    # 每个小节，一道光沿桅杆向下
    k = np.searchsorted(DOWNBEATS, t) - 1
    if k >= 0 and t > 218.5:
        u = (t - DOWNBEATS[k]) / (PER * 4)
        f.glow((mx, 280 + 600 * eio(u)), 10, GOLDL, a * 0.7 * (1 - u))
    cur = max([i for i, t0 in enumerate(RULE_T) if t >= t0] or [-1])
    for i, ((h, d), t0) in enumerate(zip(RULES, RULE_T)):
        ra = a * cl((t - t0) / 0.3)
        if ra <= 0.003: continue
        y = 330 + i * 118
        hi = 1.0 if (i == cur or t > 234.0) else 0.62
        k = eo((t - t0) / 0.45)
        xs_ = np.linspace(mx, mx + 80 * k, 16)
        sag = 5 * np.sin(np.linspace(0, math.pi, 16)) * (0.6 + 0.4 * math.sin(t * 1.7 + i))
        f.poly(np.c_[xs_, y + sag], GOLD, ra * hi, 2)
        f.disc((mx, y), 6, GOLDL, ra)
        f.text(f'{i + 1:02d}', mx + 110, y, 44, 'corm_sb', GOLD, ra * hi, 'l', mode='O')
        f.text(h, mx + 200, y - 20, 34, 'serif_black', INK, ra * hi, 'l', mode='O', t0=t0 + 0.05, stag=0.04, dur=0.35)
        f.text(d, mx + 202, y + 26, 21, 'sans_med', GREY if hi < 1 else INK, ra * hi * 0.95, 'l', mode='O',
               t0=t0 + 0.4, stag=0.008, dur=0.3)
        if i == cur and t < 234.0:
            f.glow((mx + 130, y), 40, GOLD, 0.25 * ra)


# ======================================================================== 终章
def s_coda(f, t):
    if not (235.8 <= t <= 247.0): return
    a = env(t, 236.04, 239.7, 0.5, 0.55)
    if a > 0.003:
        u = eo((t - 236.1) / 2.4)
        X = 260 + (CO_X - 170) / 1580 * 1400; Y = 330 + (CO_Y - 300) * 0.75
        pts, head = polyline_upto(X, Y, u)
        draw_price(f, pts, a * 0.85, 2, smooth=25)
        pk = (X[CO_PI], Y[CO_PI])
        if u > 0.62:
            ka = a * cl((u - 0.62) / 0.05)
            f.circle(pk, 16 + 4 * beat_pulse(t), UP, ka * 0.8, 1)
            f.text('山顶：只检查，不追', pk[0], pk[1] - 40, 20, 'serif_bold', UP2, ka, 'm', mode='O')
        lo = int(0.86 * (len(X) - 1))
        yp = np.array([lerp(300, X[lo], eio((t - 238.5) / 1.2)), lerp(780, Y[lo], eio((t - 238.5) / 1.2))])
        draw_you(f, yp[0], yp[1], a, GOLD, '你', t, 5, True, lab_dy=32)
        if t > 239.6:
            f.text('价值低估：按计划买入', yp[0] + 20, yp[1] + 70, 20, 'serif_bold', GOLD, a * cl((t - 239.6) / 0.4),
                   'm', mode='O')
    lines = [(240.29, '优秀的投资者，不是能预测每一次涨跌的人，'),
             (241.35, '而是在【狂热时保持清醒】、在【恐慌时独立思考】，'),
             (242.41, '始终依据【价值、证据和概率】做决定的人。')]
    for i, (t0, s) in enumerate(lines):
        la = env(t, t0, 246.1, 0.6, 0.5)
        f.text(s, 960, 410 + i * 82, 44, 'serif_med', INK, la, 'm', track=0.06, mode='O', t0=t0, stag=0.025, dur=0.4,
               hl=GOLD)


narr(236.2, 238.0, '下一次，当这条线再出现——')
narr(238.16, 240.1, '你会认出：哪里是山顶，哪里是机会。')

# ---------------------------------------------------------------- 最后一句 → 粒子 → 官方 logo
FINAL = ['投资最大的敌人，往往不是市场，', '而是自己【未经审视的直觉】。']
LOGO_SIZE = 220                                   # 品牌规范：片尾 logo 约 220px 居中
LOGO_C = (960.0, 400.0)
LOGO_RGB, LOGO_A = load_logo(LOGO_SIZE)
LG_N = 5200
_ys, _xs = np.nonzero(LOGO_A > 0.35)
_rr = np.random.default_rng(250)
_pick = _rr.choice(len(_xs), LG_N, p=LOGO_A[_ys, _xs] / LOGO_A[_ys, _xs].sum())
LG_TGT = np.c_[_xs[_pick] + _rr.random(LG_N) - LOGO_SIZE / 2 + LOGO_C[0], _ys[_pick] + _rr.random(LG_N) - LOGO_SIZE / 2 + LOGO_C[1]]
LG_COL = LOGO_RGB[_ys[_pick], _xs[_pick]].astype(np.float32)
# 文字粒子的起点：从最后一句话的字形里取样
_m1 = text_mask(strip(FINAL[0]), 'serif_black', 54, 0.08)
_m2 = text_mask(strip(FINAL[1]), 'serif_black', 54, 0.08)
_p1 = sample_mask_points(_m1, LG_N // 2, 1, 0.4)
_p2 = sample_mask_points(_m2, LG_N - LG_N // 2, 2, 0.4)
_p1 += [960 - _m1.shape[1] / 2, 460 - _m1.shape[0] / 2]
_p2 += [960 - _m2.shape[1] / 2, 560 - _m2.shape[0] / 2]
LG_SRC = np.r_[_p1, _p2]
_rr.shuffle(LG_SRC)
LG_DEL = _rr.random(LG_N) * 0.5
LG_CURL = _rr.standard_normal(LG_N)
LG_DRIFT = _rr.standard_normal((LG_N, 2))
T_CONV0, T_CONV1, T_LOGO = 248.25, 250.1, 249.75


def s_final_line(f, t):
    if not (244.3 <= t <= 252): return
    for i, s in enumerate(FINAL):
        t0 = 246.66 + i * 0.5
        la = env(t, t0, T_CONV0, 0.6, 0.35)
        f.text(s, 960, 460 + i * 100, 54, 'serif_black', INK, la, 'm', track=0.08, mode='O', t0=t0, stag=0.04, dur=0.45,
               hl=GOLD)


def s_logo_particles(f, t):
    if not (T_CONV0 - 0.1 <= t <= 256): return
    p = np.clip((t - T_CONV0 - LG_DEL) / (T_CONV1 - T_CONV0 - 0.5), 0, 1)
    pe = p * p * (3 - 2 * p)
    d = LG_TGT - LG_SRC
    nrm = np.c_[-d[:, 1], d[:, 0]]
    P = LG_SRC + d * pe[:, None] + nrm * (np.sin(np.pi * pe) * LG_CURL * 0.25)[:, None]
    P += np.c_[np.sin(t * 2.3 + LG_CURL * 6), np.cos(t * 2.1 + LG_CURL * 5)] * 1.0
    # 清晰 logo 出现后，粒子化作四散的微尘
    k = eio((t - T_LOGO - 0.2) / 2.2)
    P += LG_DRIFT * 220 * k
    col = mixc(np.broadcast_to(np.array(GOLD, np.float32), (LG_N, 3)), LG_COL * 1.3, cl(pe)[:, None] ** 1.5)
    A = (1.0 - 0.85 * k) * (1 - eio((t - 253.5) / 1.5)) * cl((t - T_CONV0) / 0.2) * (1 - 0.5 * eio((t - T_LOGO) / 0.8))
    f.dots(P[:, 0], P[:, 1], col, A * 0.6, 0.7, buf='E' if t < T_LOGO else 'L')
    if t > T_CONV1 - 0.6:
        # 品牌规范：logo 后一层很淡的蓝色光晕
        f.glow(LOGO_C, 70, BLUE, 0.12 * env(t, T_CONV1 - 0.6, 1e9, 0.6, 0))


# ---------------------------------------------------------------- 片尾：官方 logo + 巴芒价值 + BUFFETT · MUNGER
_BT = {}


def brand_text(text, size, fontname, track=0.0, gold=True):
    """品牌字体（brand.py 里的思源宋体 Black / Cormorant）+ 品牌金色竖向渐变"""
    key = (text, size, fontname, track, gold)
    if key not in _BT:
        fnt = _brand._font(fontname, size)
        widths = [fnt.getlength(c) for c in text]
        w = int(sum(widths) + track * size * (len(text) - 1)) + 20
        h = int(size * 1.6)
        from PIL import Image, ImageDraw
        im = Image.new('L', (w, h), 0)
        dr = ImageDraw.Draw(im)
        x = 10.0
        for c, cw in zip(text, widths):
            dr.text((x, int(size * 1.25)), c, font=fnt, fill=255, anchor='ls')
            x += cw + track * size
        m = np.asarray(im, np.float32) / 255
        ys, xs = np.where(m > 0.01)
        m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        if gold:
            rgb = np.broadcast_to(_brand._ramp(m.shape[0], _brand.GOLD_STOPS)[:, None, :].astype(np.float32),
                                  m.shape + (3,)).copy()
        else:
            rgb = np.broadcast_to(np.array(_brand.SUB_GOLD, np.float32) / 255, m.shape + (3,)).copy()
        _BT[key] = (rgb, m)
    return _BT[key]


def shine(rgb, u):
    h, w = rgb.shape[:2]
    xs = np.arange(w)[None, :] + np.arange(h)[:, None] * 0.6
    pos = -60 + (0.5 - 0.5 * math.cos(u * math.pi)) * (w + 120)
    return np.clip(rgb + np.exp(-((xs - pos) / (0.06 * w + 10)) ** 2)[..., None] * 0.6, 0, 1.25)


def wipe_alpha(m, w):
    soft = 0.35 * m.shape[1] + 30
    return m * np.clip((w * (m.shape[1] + soft) - np.arange(m.shape[1])) / soft, 0, 1).astype(np.float32)[None, :]


def s_endcard(f, t):
    if t < T_LOGO: return
    k = eio((t - T_LOGO) / 1.1)
    f.rgba(LOGO_RGB, LOGO_A, LOGO_C[0] - LOGO_SIZE / 2, LOGO_C[1] - LOGO_SIZE / 2, k)
    if t >= T_D4:
        w = cl((t - T_D4) / 0.8)
        rgb, m = brand_text('巴芒价值', 112, 'serif_black', track=0.08)
        u = cl((t - 251.6) / 1.4)
        if 0 < u < 1: rgb = shine(rgb, u)
        ty = 640
        f.rgba(rgb, wipe_alpha(m, w), 960 - m.shape[1] / 2, ty - m.shape[0] / 2, 1.0)
        f.glow((960, ty), 160, GOLD, 0.12 * env(t, T_D4, 1e9, 0.3, 0))
        hw = m.shape[1] / 2 + 44
        ln = 170 * eo((t - T_D4 - 0.3) / 1.0)
        sg = np.array(_brand.SUB_GOLD, np.float32) / 255
        for sgn in (-1, 1):
            f.line((960 + sgn * hw, ty), (960 + sgn * (hw + ln), ty), tuple(sg), 0.7, 1, buf='L')
        w2 = cl((t - T_D4 - 0.4) / 0.9)
        rgb, m = brand_text('BUFFETT · MUNGER', 30, 'corm', track=0.46, gold=False)
        f.rgba(rgb, wipe_alpha(m, w2), 960 - m.shape[1] / 2, 735 - m.shape[0] / 2, 1.0)
        ta = env(t, 253.0, 1e9, 1.0, 0)
        f.text('在狂热时清醒  ·  在恐慌时独立', 960, 820, 24, 'serif_med', INK, ta * 0.85, 'm', track=0.2, mode='O')
        sa = env(t, 254.5, 1e9, 1.0, 0)
        f.text('本视频仅为投资者教育，不构成任何投资建议。市场有风险，投资需谨慎。', 960, 950, 14, 'sans_med', GREY, sa * 0.8,
               'm', mode='O')
        f.text('数据来源：上交所、财联社、证券时报、北京商报、新浪财经等公开报道；'
               'Greenwood & Shleifer (2014)；Tversky & Kahneman (1992)；Odlyzko (2019)', 960, 978, 12, 'sans_light', GREY,
               sa * 0.7, 'm', mode='O')


SCENES_C = [s_names, s_price_value, s_margin, s_circle, s_invert, s_odds, s_ulysses, s_checklist, s_coda,
            s_final_line, s_logo_particles, s_endcard]
