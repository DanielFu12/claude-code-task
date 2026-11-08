"""第三期《东京下注》全部镜头：开场、片名、第一至六章。

版式：上方画窗（M.full → 1000×562，y 279–841）放真实影像；下方 y 900–1420 放动画解读；y≈1462 出处；y≈1555 字幕。
没有影像的镜头，动画可以占用 300–1420。
"""
import math
import numpy as np, cv2
from common import *          # noqa
import media as M
import fx

C5 = ['mitsubishi', 'mitsui', 'itochu', 'marubeni', 'sumitomo']
CN5 = {'mitsubishi': '三菱商事', 'mitsui': '三井物产', 'itochu': '伊藤忠', 'marubeni': '丸红', 'sumitomo': '住友商事'}
ORDER_ALPHA = ['itochu', 'marubeni', 'mitsubishi', 'mitsui', 'sumitomo']
YEN = np.array((0.95, 0.30, 0.28), np.float32)


# ======================================================================== 通用构件
def coin_stack(cv, x, base, n, a, col=GOLD, w=120, th=14, label=None, lab_col=CREAM, size=40):
    """一摞硬币（椭圆片叠起来），n 可为小数（最上面一枚半透明）"""
    if a <= 0.004: return base
    col = np.asarray(col, np.float32)
    full = int(n); frac = n - full
    y = base
    for k in range(full + (1 if frac > 0.02 else 0)):
        aa = a * (frac if k == full else 1.0)
        cv.fillpoly(ellipse_pts(x, y, w / 2, th * 0.55), col * 0.55, aa)
        cv.rect(x - w / 2, y - th, x + w / 2, y, col * 0.75, aa)
        cv.fillpoly(ellipse_pts(x, y - th, w / 2, th * 0.55), col * 1.0, aa, glow=0.15)
        y -= th
    if label: cv.text(label, x, y - 50, size, 'sans_bold', col=lab_col, a=a, shadow=0.7)
    return y


def ellipse_pts(cx, cy, rx, ry, n=40):
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return list(zip(cx + rx * np.cos(ang), cy + ry * np.sin(ang)))


def line_chart(cv, ys, vs, x0, x1, y0, y1, y_from, y_to, lo, hi, reveal=1.0, a=1.0, col=GOLD_L, lw=3, log=False,
               ticks=(), xticks=(), tick_fmt=lambda v: f'{v:,.0f}', glow=0.35, tip=True):
    if a <= 0.004: return None
    col = np.asarray(col, np.float32)
    f = (lambda v: math.log(v)) if log else (lambda v: v)
    def X(y): return x0 + (y - y_from) / (y_to - y_from) * (x1 - x0)
    def Y(v): return y1 - (f(v) - f(lo)) / (f(hi) - f(lo)) * (y1 - y0)
    for v in ticks:
        cv.line((x0, Y(v)), (x1, Y(v)), (0.3, 0.3, 0.34), a * 0.5, 1)
        cv.text(tick_fmt(v), x0 - 12, Y(v), 20, 'sans_light', col=DIM, a=a, anchor='r')
    for yr in xticks:
        cv.text(str(yr), X(yr), y1 + 32, 22, 'oswald', col=DIM, a=a)
    m = (ys >= y_from) & (ys <= y_to)
    Ys, Vs = ys[m], vs[m]
    if len(Ys) < 2: return None
    yend = y_from + (y_to - y_from) * cl(reveal)
    k = Ys <= yend
    Ys, Vs = Ys[k], Vs[k]
    if len(Ys) < 2: return None
    step = max(1, len(Ys) // 900)
    pts = np.stack([X(Ys[::step]), np.array([Y(v) for v in Vs[::step]])], 1)
    cv.poly(pts, col * 0.6, a * 0.6, lw + 4)
    cv.poly(pts, col, a, lw)
    if glow: cv.glow_dot(tuple(pts[-1]), 18, col, a * glow * 2)
    return X, Y, pts[-1]


def hbar_rows(cv, rows, t, a, x0=330, x1=930, y0=1000, dy=86, vmax=None, fmt=lambda v: f'{v:.1f}%', size=36, lab_size=34,
              hl=None, col=GOLD):
    """横条：rows = [(标签, 数值, 出现时刻)]"""
    vmax = vmax or max(r[1] for r in rows)
    for j, (lab, v, ts) in enumerate(rows):
        e = eexp((t - ts) / 1.0)
        if e <= 0: continue
        y = y0 + j * dy
        cv.text(lab, x0 - 24, y, lab_size, 'sans_med', col=CREAM, a=a * min(1, e * 2), anchor='r')
        L = (x1 - x0) * v / vmax * e
        cc = hl if (hl is not None and j == 0) else col
        cv.rect(x0, y - 16, x0 + L, y + 16, cc, a * 0.92, glow=0.15)
        cv.text(fmt(v * e if e < 1 else v), x0 + L + 16, y, size, 'sans_bold', col=GOLD_L, a=a * min(1, e * 2), anchor='l')


def stake_bars(cv, t, a, vals, x0=300, x1=900, y0=980, dy=78, vmax=12.0, line=None, line_lab=None, line_dash=False):
    """五家持股横条（百分比），vals = {公司: 数值}；line = 竖线位置（如 5% / 9.9%）"""
    def X(v): return x0 + (x1 - x0) * v / vmax
    for j, c in enumerate(ORDER_ALPHA):
        y = y0 + j * dy
        v = vals.get(c, 0)
        cv.text(CN5[c], x0 - 24, y, 32, 'sans_med', col=CREAM, a=a, anchor='r')
        cv.rect(x0, y - 15, x1, y + 15, (0.16, 0.15, 0.16), a * 0.8)
        cv.rect(x0, y - 15, X(v), y + 15, GOLD, a * 0.95, glow=0.15)
        cv.text(f'{v:.1f}%', X(v) + 14, y, 30, 'sans_bold', col=GOLD_L, a=a, anchor='l')
    if line is not None:
        xl = X(line)
        yy0, yy1 = y0 - 50, y0 + dy * 4 + 40
        if line_dash:
            for yy in np.arange(yy0, yy1, 22): cv.line((xl, yy), (xl, min(yy + 12, yy1)), RED, a, 3)
        else:
            cv.line((xl, yy0), (xl, yy1), RED, a, 3)
        if line_lab: cv.text(line_lab, xl, yy0 - 30, 28, 'sans_bold', col=RED, a=a)


def flow(cv, t, p0, p1, width, col, a, speed=180.0, dens=0.08, seed=1, curve=0.0):
    """粒子水流：从 p0 流向 p1（宽度 width，密度 dens 每像素）"""
    if a <= 0.004: return
    rng = np.random.default_rng(seed)
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    n = int(L * dens * max(width / 20, 1))
    u = (rng.uniform(0, 1, n) + t * speed / max(L, 1)) % 1.0
    off = rng.normal(0, width / 3, n)
    dx, dy = (p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L
    nx, ny = -dy, dx
    bend = curve * np.sin(u * np.pi) * L
    xs = p0[0] + (p1[0] - p0[0]) * u + nx * (off + bend)
    ys = p0[1] + (p1[1] - p0[1]) * u + ny * (off + bend)
    cv.splat(xs, ys, col, a * 0.9, glow=1.0)


def check_list(cv, t, a, items, x=150, y0=920, dy=92, size=40, states=None, t_states=None):
    """三条标准：states[i] in (None, True, False)，t_states[i] 为打勾/打叉时刻"""
    for j, s in enumerate(items):
        y = y0 + j * dy
        cv.rrect(x, y - 24, x + 48, y + 24, 8, GOLD_D, a * 0.8, fill=False, th=2)
        cv.text(s, x + 80, y, size, 'sans_med', col=CREAM, a=a, anchor='l', shadow=0.6)
        st = states[j] if states else None
        if st is None: continue
        k = eo((t - t_states[j]) / 0.35)
        if k <= 0: continue
        if st:
            cv.poly([(x + 10, y), (x + 21, y + 12), (x + 21 + 22 * k, y + 12 - 30 * k)], GREEN, a, 5)
        else:
            cv.line((x + 8, y - 16), (x + 8 + 32 * k, y - 16 + 32 * k), RED, a, 5)
            cv.line((x + 40, y - 16), (x + 40 - 32 * k, y - 16 + 32 * k), RED, a, 5)


def battleship(cv, cx, cy, ang, a, s=1.0):
    """战舰线稿（俯视），ang 为航向角"""
    pts = np.array([(-260, 0), (-200, -46), (180, -46), (300, 0), (180, 46), (-200, 46)], float) * s
    deck = [np.array(r, float) * s for r in ([(-120, -22), (40, -22), (40, 22), (-120, 22)], [(60, -16), (120, -16), (120, 16), (60, 16)])]
    c, sn = math.cos(ang), math.sin(ang)
    R = lambda P: [(cx + x * c - y * sn, cy + x * sn + y * c) for x, y in P]
    cv.fillpoly(R(pts), (0.10, 0.10, 0.12), a)
    cv.poly(R(pts) + [R(pts)[0]], GOLD_L, a * 0.9, 3)
    for d in deck: cv.poly(R(d) + [R(d)[0]], GOLD_D, a * 0.8, 2)
    # 船尾航迹
    for k in range(1, 9):
        r = 40 + k * 26
        tail = (-270 * s - k * 24 * s, 0)
        p = R([tail])[0]
        cv.circle(p, 6 + k * 3, (0.5, 0.6, 0.7), a * 0.25 * (1 - k / 9), 2)


def house(cv, cx, cy, s, a, col=GOLD):
    body = [(cx - 90 * s, cy), (cx + 90 * s, cy), (cx + 90 * s, cy - 110 * s), (cx - 90 * s, cy - 110 * s)]
    roof = [(cx - 115 * s, cy - 105 * s), (cx, cy - 190 * s), (cx + 115 * s, cy - 105 * s)]
    cv.fillpoly(body, col * 0.45, a); cv.fillpoly(roof, col * 0.8, a, glow=0.1)
    cv.poly(body + [body[0]], GOLD_L, a * 0.8, 2); cv.poly(roof + [roof[0]], GOLD_L, a * 0.8, 2)
    cv.rect(cx - 22 * s, cy - 60 * s, cx + 22 * s, cy, (0.08, 0.06, 0.05), a)


def balance(cv, cx, cy, tilt, a, lw=(None, None), labs=('', ''), cols=(GOLD, GREY)):
    """天平：tilt>0 左低"""
    L = 280
    cv.line((cx, cy), (cx, cy + 260), GOLD_D, a, 4)
    cv.fillpoly([(cx - 80, cy + 270), (cx + 80, cy + 270), (cx, cy + 230)], GOLD_D, a)
    dx, dy = L * math.cos(tilt), L * math.sin(tilt)
    pl, pr = (cx - dx, cy + dy), (cx + dx, cy - dy)
    cv.line(pl, pr, GOLD_L, a, 4)
    cv.glow_dot((cx, cy), 8, GOLD_L, a)
    for p, lab, col in ((pl, labs[0], cols[0]), (pr, labs[1], cols[1])):
        cv.line(p, (p[0], p[1] + 70), GOLD_D, a * 0.7, 2)
        cv.arc((p[0], p[1] + 70), 70, 0, math.pi, GOLD_D, a * 0.9, 3)
        if lab: cv.text(lab, p[0], p[1] + 30, 56, 'sans_bold', col=col, a=a, shadow=0.6)
    return pl, pr


def fireworks(cv, t, t0, a, centers, seed=3):
    rng = np.random.default_rng(seed)
    for k, (x, y) in enumerate(centers):
        tt = t - t0 - k * 0.45
        if tt < 0 or tt > 2.2: continue
        n = 70
        ang = rng.uniform(0, 2 * np.pi, n); sp = rng.uniform(120, 260, n)
        r = sp * (1 - math.exp(-tt * 2.2))
        xs = x + np.cos(ang) * r; ys = y + np.sin(ang) * r + 40 * tt * tt
        col = [GOLD_L, RED, BLUE][k % 3]
        cv.splat(xs, ys, col, a * max(0, 1 - tt / 2.2) * 1.2, glow=1.6)


def logo_tile(cv, name, x, y, a, size=46, sub=None):
    cv.text(name, x, y, size, 'serif_black', gold=True, a=a, glow=0.2, shadow=0.8)
    if sub: cv.text(sub, x, y + size * 0.85, 22, 'corm', col=GOLD, a=a * 0.9, track=0.2)


EN5 = {'itochu': 'ITOCHU', 'marubeni': 'MARUBENI', 'mitsubishi': 'MITSUBISHI', 'mitsui': 'MITSUI', 'sumitomo': 'SUMITOMO'}


# ======================================================================== 开场
def shot_hook(cv, t):
    # ---- h1：这样的钱，你借不借？——两摞硬币：利息 1.2 vs 分红 5.6
    t0, t1 = win('h1', pre=1.0)
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        p = t - t0
        k1 = eo((t - WT('h1', '一块二') + 0.2) / 0.6)
        k2 = eo((t - WT('h1', '五块多') + 0.2) / 0.8)
        cv.text('借 100 块', W / 2, 520, 64, 'serif_black', col=CREAM, a=a * eo(p / 0.6), shadow=0.7)
        coin_stack(cv, 330, 1180, 1.2 * 5 * k1, a * min(1, k1 * 3), col=GREY, w=180, th=19, label='利息 1.2' if k1 > 0.1 else None, lab_col=GREY, size=52)
        coin_stack(cv, 750, 1180, 5.6 * 5 * k2, a * min(1, k2 * 3), col=GOLD, w=180, th=19, label='分红 5.6' if k2 > 0.1 else None, lab_col=GOLD_L, size=52)
        cv.text('每年', 330, 1240, 28, 'sans_light', col=GREY, a=a * k1); cv.text('每年', 750, 1240, 28, 'sans_light', col=GREY, a=a * k2)
        kq = eo((t - WT('h1', '你借不借') + 0.1) / 0.4)
        cv.text('？', W / 2, 860, 220, 'serif_black', gold=True, a=a * kq, glow=0.4, scale=1.2 - 0.2 * kq)
    # ---- h2：巴菲特借了：两万多亿日元，≈ 150 亿美元
    t0, t1 = win('h2')
    a = env(t, t0, t1, 0.35, 0.35)
    if a > 0:
        p = t - t0
        M.full(cv, 'x_bwbi_a', t, t0, t1, a=a, src_t0=2.0, cap='巴菲特')
        for j in range(14):                                  # 日元纸币从两侧飘落（不压住中间的数字）
            r = np.random.default_rng(j * 7 + 1)
            side = -1 if j % 2 else 1
            x = W / 2 + side * r.uniform(330, 480); sp = r.uniform(140, 260); ph = r.uniform(0, 3)
            y = 900 + ((p * sp + ph * 200) % 480)
            ang = math.sin(p * 2 + j) * 0.6
            w_, h_ = 56, 28
            c, s = math.cos(ang), math.sin(ang)
            pts = [(x + dx * c - dy * s, y + dx * s + dy * c) for dx, dy in ((-w_, -h_), (w_, -h_), (w_, h_), (-w_, h_))]
            cv.fillpoly(pts, (0.75, 0.70, 0.55), a * 0.28)
            cv.poly(pts + [pts[0]], GOLD_D, a * 0.35, 1)
        k = eo((t - WT('h2', '两万多亿') + 0.15) / 0.5)
        cv.rrect(140, 1010, 940, 1300, 22, (0.03, 0.025, 0.025), a * k * 0.85)
        cv.text('¥ 2.3 万亿', W / 2, 1100, 110, 'sans_bold', gold=True, a=a * k, glow=0.35, shadow=0.7)
        k2 = eo((t - WT('h2', '一百五十亿') + 0.15) / 0.5)
        cv.text('≈ $150 亿', W / 2, 1225, 64, 'sans_bold', col=CREAM, a=a * k2, shadow=0.7)
        source(cv, '伯克希尔 2025 年报：日元债账面 $149.14 亿（2025 年底，约 2.3 万亿日元）', a, y=1462)
    # ---- h3：五家日本老公司 + 三十年没爬起来的指数
    t0, t1 = win('h3')
    a = env(t, t0, t1, 0.35, 0.35)
    if a > 0:
        p = t - t0
        M.full(cv, 'j_cine_osaka', t, t0, t1, a=a, speed=0.8, cap='日本')
        ys, vs = SER['n225']
        line_chart(cv, ys, vs, 140, 940, 1190, 1400, 1989.0, 2019.5, 7000, 40000, reveal=eio((t - WT('h3', '日本股市')) / 2.5),
                   a=a * 0.85, col=(0.75, 0.70, 0.68), lw=2, xticks=(1990, 2000, 2010, 2019), glow=0.2)
        kk = eo((t - WT('h3', '冷落')) / 0.6)
        cv.text('日经指数 1989–2019：30 年没回到高点', W / 2, 1150, 26, 'sans_light', col=GREY, a=a * kk)
        pos = [(230, 940), (540, 940), (850, 940), (385, 1050), (695, 1050)]
        for j, c in enumerate(ORDER_ALPHA):
            tj = WT('h3', '五家日本老公司') + j * 0.22
            k = eo((t - tj) / 0.5)
            x, y = pos[j]
            cv.text(CN5[c], x, y + 20 * (1 - k), 54, 'serif_black', gold=True, a=a * k, glow=0.2, shadow=0.8)
    # ---- h4：154 → 354；分红 ≈ 利息 × 5
    t0, t1 = win('h4')
    a = env(t, t0, t1, 0.35, 0.35)
    if a > 0:
        tl_ = WT('h4', '一百五十四亿'); tr_ = WT('h4', '三百五十四亿')
        fx.bars3d(cv, t, t0, t1, ('买入成本', 154, '$154 亿', tl_ - 0.3), ('2025 年底市值', 354, '$354 亿', tr_ - 0.3), a=a,
                  title='伯克希尔持有的日本五大商社', sub='2025 年底 · 美元', hmax=1.15)
        k = eo((t - WT('h4', '五倍') + 0.3) / 0.5)
        if k > 0:
            cv.rrect(170, 1240, 910, 1360, 18, (0.03, 0.025, 0.025), a * k * 0.85)
            cv.text('每年分红 ≈ 利息 × 5', W / 2, 1300, 52, 'sans_bold', gold=True, a=a * k, glow=0.25)
        source(cv, '伯克希尔 2025 年致股东信（持仓表）；分红 $8.62 亿 ÷ 日元债利息估算约 $1.8 亿', a, y=1462)
    # ---- h5：芒格：上帝打开箱子往里倒钱
    t0, t1 = win('h5')
    a = env(t, t0, t1, 0.35, 0.35)
    if a > 0:
        M.full(cv, 'x_bwbm_munger', t, t0, t1, a=a, src_t0=1.0, speed=0.8, cap='查理·芒格')
        quote_card(cv, 'qgod', t, t0 + 0.1, t1, cy=1130, en_size=36, cn_size=44, a=a)
    # ---- h6：一边卖苹果，一边买商社
    t0, t1 = win('h6')
    a = env(t, t0, t1, 0.35, 0.35)
    if a > 0:
        p = t - t0
        ks = eio((t - WT('h6', '大笔卖出苹果')) / 2.2)
        kb = eio((t - WT('h6', '越买越多')) / 2.0)
        # 左：苹果持股（亿股）9.16 → 2.28
        cv.text('苹果', 300, 470, 56, 'serif_black', col=CREAM, a=a)
        cv.text('伯克希尔持股（亿股）', 300, 530, 24, 'sans_light', col=GREY, a=a)
        v = lerp(9.16, 2.28, ks)
        h = 640 * v / 9.16
        cv.rect(230, 1250 - h, 370, 1250, RED, a * 0.9, glow=0.1)
        cv.text(f'{v:.2f}', 300, 1250 - h - 40, 44, 'sans_bold', col=(1.0, 0.55, 0.5), a=a)
        cv.text('2023 秋 → 2025 底', 300, 1295, 24, 'sans_light', col=GREY, a=a)
        cv.text('卖', 300, 1370, 64, 'serif_black', col=RED, a=a * eo((t - WT('h6', '大笔卖出苹果')) / 0.4))
        # 右：五大商社平均持股（%）≈8.5 → 10+
        cv.text('日本五大商社', 780, 470, 56, 'serif_black', gold=True, a=a)
        cv.text('伯克希尔平均持股（%）', 780, 530, 24, 'sans_light', col=GREY, a=a)
        v2 = lerp(8.5, 10.2, kb)
        h2 = 640 * v2 / 11.0
        cv.rect(710, 1250 - h2, 850, 1250, GOLD, a * 0.9, glow=0.15)
        cv.text(f'{v2:.1f}%', 780, 1250 - h2 - 40, 44, 'sans_bold', col=GOLD_L, a=a)
        cv.text('2023 中 → 2025 底', 780, 1295, 24, 'sans_light', col=GREY, a=a)
        cv.text('买', 780, 1370, 64, 'serif_black', gold=True, a=a * eo((t - WT('h6', '越买越多')) / 0.4), glow=0.3)
        source(cv, '伯克希尔 13F（苹果，2023Q3 9.16 亿股 → 2025Q4 2.28 亿股）；2023-06 声明与 2025 年致股东信（五家平均）', a, y=1462)
    # ---- h7：一边卖，一边买 → 片名
    t0, t1 = S('h7') - 0.3, CH['title'][0] + 0.2
    a = env(t, t0, t1, 0.35, 0.3)
    if a > 0:
        p = t - t0
        k1 = eo(p / 0.5); k2 = eo((t - WT('h7', '一边买')) / 0.5)
        cv.text('一边卖', W / 2 - 200, 820, 96, 'serif_black', col=RED, a=a * k1, shadow=0.8)
        cv.text('一边买', W / 2 + 200, 820, 96, 'serif_black', gold=True, a=a * k2, glow=0.3, shadow=0.8)
        k3 = eo((t - WT('h7', '为什么')) / 0.5)
        cv.text('为什么偏偏在东京下注？', W / 2, 1000, 56, 'serif_semi', col=CREAM, a=a * k3, shadow=0.8)
        fx.flare(cv, W / 2, 900, a * math.exp(-max(t - WT('h7', '东京下注') - 0.4, 0) * 3) * (t > WT('h7', '东京下注') - 0.1), length=700)


# ======================================================================== 片名
def shot_title(cv, t):
    t0, t1 = CH['title'][0], CH['ch1'][0] + 0.6
    a = env(t, t0, t1, 0.02, 0.6)
    if a <= 0: return
    p = t - t0
    flash = math.exp(-p * 5.0)
    k0 = eo(p / 0.6)
    # 一轮红日（品牌金描边）从光点放大
    R = 230 * (0.6 + 0.4 * k0)
    cv.glow_dot((W / 2, 700), R * 1.3, RED, a * 0.55 * k0)
    cv.fillpoly(ellipse_pts(W / 2, 700, R, R, 96), (0.78, 0.10, 0.10), a * k0 * 0.95, glow=0.25)
    cv.circle((W / 2, 700), R, GOLD, a * k0 * 0.8, 3)
    cv.circle((W / 2, 700), 60 + p * 900, GOLD, a * math.exp(-p * 2.2) * 0.8, 3)
    cv.glow_dot((W / 2, 700), 240, GOLD, a * flash * 0.9)
    k = eo((p - 0.15) / 0.6)
    cv.text('东京下注', W / 2, 1150, 170, 'serif_black', gold=True, a=a * k, glow=0.3, scale=1.08 - 0.08 * k, shadow=0.8)
    cv.text('巴菲特与日本五大商社', W / 2, 1320, 60, 'serif_semi', col=CREAM, a=a * eo((p - 0.5) / 0.6), shadow=0.8)
    cv.text('THE TOKYO BET', W / 2, 1420, 26, 'corm', col=GOLD, a=a * eo((p - 1.0) / 0.6), track=0.35)


# ======================================================================== 第一章：被遗忘的市场
def shot_ch1(cv, t):
    # ---- c1a：回到三十多年前：年份倒翻
    t0, t1 = win('c1a', pre=0.5)
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = cl((t - t0) / max(t1 - t0 - 0.4, 0.5))
        yr = int(round(lerp(2019, 1989, eio(p))))
        M.full(cv, 'j_cine_city', t, t0, t1, a=a, speed=0.6, cap='日本夜景')
        cv.text(str(yr), W / 2, 1120, 200, 'oswald', gold=True, a=a, glow=0.3, shadow=0.8)
        cv.text(str(yr + 1), W / 2, 930, 90, 'oswald', col=DIM, a=a * 0.35)
    # ---- c1b–c1d：日经指数 1985 → 2026：山顶、山谷、34 年
    t0, t1 = S('c1b') - 0.3, S('c1e') + 0.1
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        ys, vs = SER['n225']
        rv = 0.12 + 0.30 * eio((t - S('c1b')) / 3.0) + 0.58 * eio((t - WT('c1c', '二零二四年')) / 2.2)
        y_to = 2026.9
        r = line_chart(cv, ys, vs, 140, 960, 560, 1250, 1985.0, y_to, 5000, 60000, reveal=rv, a=a, log=True,
                       ticks=(10000, 20000, 40000), xticks=(1990, 2000, 2010, 2020), col=GOLD_L)
        cv.text('日经 225 指数（对数坐标）', 140, 470, 30, 'sans_med', col=CREAM, a=a, anchor='l')
        if r:
            X, Y, _ = r
            k = eo((t - WT('c1b', '最高点')) / 0.5)
            if k > 0:
                px, py = X(1989.99), Y(38915.87)
                cv.glow_dot((px, py), 14, RED, a * k)
                cv.text('1989 年底  38,916', px + 20, py - 50, 30, 'sans_bold', col=(1.0, 0.55, 0.5), a=a * k, anchor='l')
            k2 = eo((t - WT('c1c', '二零二四年')) / 0.6) * (rv > 0.85)
            if k2 > 0:
                qx, qy = X(2024.14), Y(39098.68)
                cv.line((px, py), (qx, py), RED, a * k2 * 0.8, 2)
                cv.glow_dot((qx, qy), 14, GOLD, a * k2)
                cv.text('2024 年 2 月', qx, qy - 60, 28, 'sans_bold', col=GOLD_L, a=a * k2)
            k3 = eo((t - WT('c1c', '整整三十四年')) / 0.5)
            if k3 > 0:
                cv.text('34 年', (px + qx) / 2 if k2 > 0 else W / 2, 400 + 0, 110, 'sans_bold', gold=True, a=a * k3, glow=0.35, shadow=0.7)
        kd = eo((t - S('c1d')) / 0.6)
        if kd > 0:
            cv.rrect(140, 1330, 940, 1420, 16, (0.03, 0.025, 0.025), a * kd * 0.85)
            cv.text('一代人的时间，投资日本几乎就等于亏钱', W / 2, 1375, 34, 'sans_med', col=CREAM, a=a * kd)
        source(cv, 'Yahoo Finance：日经 225 日线；1989-12-29 收 38,915.87，2024-02-22 收 39,098.68', a, y=1462)
    # ---- c1e：综合商社
    t0, t1 = win('c1e')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        M.full(cv, 'v_tokyo', t, t0, t1, a=a, src_t0=6.0, speed=0.7, cap='东京丸之内')
        k = eo((t - WT('c1e', '综合商社')) / 0.6)
        cv.text('综合商社', W / 2, 1060, 120, 'serif_black', gold=True, a=a * k, glow=0.3, shadow=0.8)
        cv.text('SOGO SHOSHA', W / 2, 1170, 30, 'corm', col=GOLD, a=a * k, track=0.4)
    # ---- c1f：贸易起家：东京连向全世界
    t0, t1 = win('c1f')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        globe(cv, t, W / 2, 860, 360, rot=-math.radians(139.7) + math.pi + p * 0.05, tilt=0.45, a=a, arcs=eio(p / 4.0))
        for j, (s_, tw) in enumerate((('铁矿', '铁矿'), ('石油', '石油'), ('粮食', '粮食'))):
            k = eo((t - WT('c1f', tw)) / 0.4)
            chip(cv, s_ + ' → 日本', 260 + j * 280, 1330, 30, a * k, col=GOLD)
    # ---- c1g：自己投资矿山、气田……全家、罗森
    t0, t1 = win('c1g')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        tl_ = WT('c1g', '全家')
        if t < tl_ - 0.3:
            for j, s_ in enumerate(['矿山', '气田', '农场', '电厂', '化工', '机械', '物流', '金融']):
                ang = -math.pi / 2 + j * 2 * math.pi / 8 + p * 0.05
                k = eo((p - j * 0.18) / 0.5)
                x, y = W / 2 + math.cos(ang) * 330 * k, 820 + math.sin(ang) * 330 * k
                cv.line((W / 2, 820), (x, y), GOLD_D, a * k * 0.5, 2)
                cv.rrect(x - 75, y - 34, x + 75, y + 34, 14, (0.06, 0.05, 0.04), a * k)
                cv.text(s_, x, y, 36, 'sans_med', col=CREAM, a=a * k)
            cv.text('商社', W / 2, 820, 72, 'serif_black', gold=True, a=a * eo(p / 0.4), glow=0.3)
        else:
            a2 = a * eo((t - tl_ + 0.3) / 0.5)
            M.full(cv, 'j_lawson', t, tl_ - 0.3, t1, a=a2, src_t0=0.5, speed=0.8, cap='日本的便利店')
            kf = eo((t - tl_) / 0.4); kl = eo((t - WT('c1g', '罗森')) / 0.4)
            cv.text('全家便利店', 290, 1010, 50, 'serif_black', col=CREAM, a=a2 * kf)
            cv.text('→ 伊藤忠', 290, 1090, 44, 'sans_bold', gold=True, a=a2 * kf)
            cv.text('罗森', 790, 1010, 50, 'serif_black', col=CREAM, a=a2 * kl)
            cv.text('→ 三菱商事', 790, 1090, 44, 'sans_bold', gold=True, a=a2 * kl)
            source(cv, '伊藤忠 2020 年私有化全家；罗森 2024 年起由 KDDI 与三菱商事各持 50%', a2, y=1462)
    # ---- c1h：有点像伯克希尔
    t0, t1 = win('c1h')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        L = ['保险', '铁路', '能源', '制造', '零售']; R_ = ['资源', '能源', '食品', '机械', '零售']
        for side, (nm, items, x) in enumerate((('伯克希尔', L, 290), ('综合商社', R_, 790))):
            k = eo((p - side * 0.4) / 0.6)
            cv.text(nm, x, 440, 56, 'serif_black', gold=side == 1, col=CREAM, a=a * k, glow=0.2 if side else 0)
            for j, s_ in enumerate(items):
                kk = eo((p - side * 0.4 - 0.2 - j * 0.12) / 0.4)
                yy = 540 + j * 92
                cv.rrect(x - 140, yy - 34, x + 140, yy + 34, 12, (0.06, 0.05, 0.04), a * kk)
                cv.rrect(x - 140, yy - 34, x + 140, yy + 34, 12, GOLD_D, a * kk * 0.5, fill=False, th=2)
                cv.text(s_, x, yy, 34, 'sans_med', col=CREAM, a=a * kk)
        cv.text('≈', W / 2, 720, 90, 'sans_bold', gold=True, a=a * eo((p - 1.2) / 0.4))
        quote_card(cv, 'qsimilar', t, WT('c1h', '巴菲特说') - 0.3, t1, cy=1230, en_size=32, cn_size=38, a=a)
    # ---- c1i：几家看得懂的公司，价格呢？
    t0, t1 = S('c1i') - 0.3, CH['tk_ch1'][0] + 0.2
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        M.full(cv, 'j_tower', t, t0, t1, a=a, speed=0.5, cap='东京')
        for j, c in enumerate(ORDER_ALPHA):
            k = eo((p - j * 0.12) / 0.5)
            y = 930 + j * 96
            cv.rrect(190, y - 38, 890, y + 38, 14, (0.05, 0.045, 0.04), a * k)
            cv.text(CN5[c], 250, y, 38, 'serif_black', col=CREAM, a=a * k, anchor='l')
            q = eo((t - WT('c1i', '价格')) / 0.5)
            cv.text('¥ ????', 850, y, 38, 'oswald', col=GOLD, a=a * k * (0.4 + 0.6 * q), anchor='r')


# ======================================================================== 第二章：便宜得离谱
def shot_ch2(cv, t):
    # ---- c2a：翻翻财务报表，就被股价之低惊到了
    t0, t1 = win('c2a')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        M.full(cv, 'x_bwb_desk', t, t0, t1, a=a, src_t0=0.5, speed=0.6, cap='巴菲特在奥马哈的办公室')
        quote_card(cv, 'qamazed', t, t0 + 0.3, t1, cy=1130, en_size=34, cn_size=42, a=a)
    # ---- c2b–c2c：100 块，每年赚回 14 块，七年多回本
    t0, t1 = S('c2b') - 0.3, S('c2d') + 0.1
    a = env(t, t0, t1, 0.4, 0.35)
    if a > 0:
        p = t - t0
        k2 = eo((t - S('c2c')) / 0.5)
        if k2 <= 0:
            M.full(cv, 'j_market', t, t0, S('c2c') + 0.3, a=a, speed=0.7, cap='东京街头')
            cv.text('花 100 块', 300, 920, 50, 'serif_black', col=CREAM, a=a * eo(p / 0.5))
            coin_stack(cv, 300, 1380, 20 * eo(p / 0.8), a, col=GREY, w=140, th=18)
            k = eo((t - WT('c2b', '十四块')) / 0.6)
            cv.text('每年赚回', 780, 920, 40, 'sans_med', col=CREAM, a=a * k)
            coin_stack(cv, 780, 1380, 14 * k, a * k, col=GOLD, w=140, th=18)
            cv.text('14 块', 780, 1380 - 14 * 18 - 60, 64, 'sans_bold', gold=True, a=a * k, glow=0.3)
        else:
            cv.text('花 100 块', 300, 450, 56, 'serif_black', col=CREAM, a=a)
            coin_stack(cv, 300, 1050, 20, a, col=GREY, w=150, th=20)
            cv.text('每年赚回', 780, 450, 40, 'sans_med', col=CREAM, a=a)
            coin_stack(cv, 780, 1050, 14, a, col=GOLD, w=150, th=20)
            cv.text('14 块', 780, 1050 - 14 * 20 - 70, 72, 'sans_bold', gold=True, a=a, glow=0.3)
        if k2 > 0:
            yrs = cl((t - S('c2c')) / 2.4) * 7.1
            cv.rrect(140, 1130, 940, 1400, 20, (0.03, 0.025, 0.025), a * k2 * 0.85)
            for j in range(8):
                f = cl(yrs - j)
                cv.rect(190 + j * 88, 1180, 190 + j * 88 + 70, 1250, (0.2, 0.18, 0.16), a * k2)
                cv.rect(190 + j * 88, 1250 - 70 * f, 190 + j * 88 + 70, 1250, GOLD, a * k2, glow=0.1)
                cv.text(f'{j + 1}', 225 + j * 88, 1280, 22, 'oswald', col=DIM, a=a * k2)
            cv.text('≈ 7 年回本', W / 2, 1350, 50, 'sans_bold', gold=True, a=a * k2 * eo((yrs - 6.5) / 0.6), glow=0.2)
        source(cv, '巴菲特 CNBC 2023-04：“an earnings yield maybe 14%… but dividends would grow”；100 ÷ 14 ≈ 7.1', a, y=1462)
    # ---- c2d–c2e：天平：14 vs 不到 1
    t0, t1 = S('c2d') - 0.3, S('c2f') + 0.1
    a = env(t, t0, t1, 0.4, 0.35)
    if a > 0:
        p = t - t0
        kb = eo((t - WT('c2d', '不到一块')) / 0.8)
        tilt = 0.32 * kb
        cv.text('同样的 100 块', W / 2, 400, 48, 'serif_black', col=CREAM, a=a)
        pl, pr = balance(cv, W / 2, 620, tilt, a, labs=('14', '<1' if kb > 0.3 else ''), cols=(GOLD_L, GREY))
        cv.text('五大商社（每年赚回）', pl[0], 990, 28, 'sans_light', col=GOLD, a=a)
        cv.text('美国十年期国债', pr[0], 990, 28, 'sans_light', col=GREY, a=a * kb)
        kn = eo((t - WT('c2d', '负的')) / 0.5)
        cv.text('日本国债：负利率', pr[0], 1040, 28, 'sans_bold', col=RED, a=a * kn)
        kq = eo((t - WT('c2e', '低得离谱')) / 0.5)
        if kq > 0: quote_card(cv, 'qridic', t, WT('c2e', '巴菲特说') - 0.2, t1, cy=1250, en_size=28, cn_size=36, a=a)
        source(cv, '巴菲特 2020 年致股东信：2020 年底 10 年期美债收益率 0.93%，日本等国数万亿主权债为负收益', a * (1 - kq), y=1462)
    # ---- c2f–c2h：买不快：战舰掉头
    t0, t1 = S('c2f') - 0.3, S('c2i') + 0.1
    a = env(t, t0, t1, 0.4, 0.35)
    if a > 0:
        p = t - t0
        kh = eo((t - S('c2g')) / 0.5)
        kf = env(t, S('c2f') - 0.2, S('c2g') + 0.2, 0.3, 0.3)
        if kf > 0:
            cv.text('看准了', W / 2 - 170, 800, 80, 'serif_black', gold=True, a=a * kf, glow=0.25)
            cv.text('≠', W / 2, 800, 80, 'sans_bold', col=RED, a=a * kf)
            cv.text('买得够', W / 2 + 170, 800, 80, 'serif_black', col=CREAM, a=a * kf)
        if t < WT('c2h', '每天') - 0.2:
            M.full(cv, 'j_night_crossing', t, S('c2g') - 0.3, WT('c2h', '每天'), a=a, speed=0.7, cap='东京新宿')
            cv.text('$ 几十亿', W / 2, 950, 80, 'sans_bold', gold=True, a=a * kh, glow=0.3)
            ys = np.linspace(2019.5, 2020.5, 60); vv = 100 + np.cumsum(np.random.default_rng(4).normal(0, 1, 60))
            push = eio((t - WT('c2g', '推上去')) / 1.0)
            vv = vv + np.linspace(0, 40, 60) * push
            line_chart(cv, ys, vv, 160, 920, 1060, 1330, 2019.5, 2020.5, 80, 150, reveal=1.0, a=a * kh, col=(1.0, 0.55, 0.5), glow=0.3)
            cv.text('买得太急 → 股价被自己推高', W / 2, 1390, 34, 'sans_med', col=CREAM, a=a * push)
        else:
            k = eo((t - WT('c2h', '每天') + 0.2) / 0.5)
            ang = -0.15 + 1.2 * eio((t - WT('c2h', '战舰')) / 3.5)
            battleship(cv, W / 2, 720, ang, a * k, s=1.05)
            prog_ = cl((t - WT('c2h', '每天')) / 6.0)
            cv.rect(160, 1100, 920, 1130, (0.2, 0.18, 0.16), a * k)
            for j in range(int(prog_ * 40)):
                cv.rect(160 + j * 19, 1100, 160 + j * 19 + 15, 1130, GOLD, a * k, glow=0.1)
            cv.text('每天买一点，再买一点', W / 2, 1180, 36, 'sans_med', col=CREAM, a=a * k)
            kq = eo((t - WT('c2h', '巴菲特说')) / 0.5)
            cv.text('“这就像让一艘战舰掉头”', W / 2, 1290, 44, 'serif_semi', col=GOLD_L, a=a * kq, shadow=0.6)
            source(cv, '巴菲特 2023 年致股东信：“The process is like turning a battleship.”', a * kq, y=1462)
    # ---- c2i：2019-07-04 独立日，88 岁
    t0, t1 = win('c2i')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        fireworks(cv, t, t0 + 0.2, a * 0.8, [(260, 520), (820, 460), (540, 380), (300, 700)])
        cv.rrect(330, 560, 750, 980, 26, (0.95, 0.94, 0.9), a)
        cv.rect(330, 560, 750, 660, RED, a)
        cv.text('2019 · JULY', W / 2, 610, 38, 'oswald', col=WHITE, a=a)
        cv.text('4', W / 2, 820, 220, 'oswald', col=(0.12, 0.1, 0.1), a=a)
        k = eo((t - WT('c2i', '八十八岁')) / 0.5)
        cv.text('88 岁的巴菲特，在东京悄悄开始买入', W / 2, 1100, 40, 'sans_med', col=CREAM, a=a * k, shadow=0.6)
        source(cv, '巴菲特 2023 年致股东信：“Our Japanese purchases began on July 4, 2019.”', a, y=1462)
    # ---- c2j：持股超过 5% 就必须公开 → 90 岁生日宣布
    t0, t1 = win('c2j')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        f = eio(p / max(WT('c2j', '越过了') - t0, 1.0))
        vals = {c: 5.1 * f * (0.9 + 0.1 * (j % 3) / 2) for j, c in enumerate(ORDER_ALPHA)}
        stake_bars(cv, t, a, vals, y0=520, dy=96, vmax=10.0, line=5.0, line_lab='5%：必须公开')
        k = eo((t - WT('c2j', '九十岁生日')) / 0.5)
        if k > 0:
            cv.rrect(140, 1050, 940, 1400, 22, (0.03, 0.025, 0.025), a * k * 0.9)
            for j in range(9):
                x = 300 + j * 60
                cv.rect(x - 8, 1170, x + 8, 1250, CREAM, a * k)
                cv.glow_dot((x, 1155), 12 + 3 * math.sin(t * 9 + j), GOLD, a * k)
            cv.text('2020 年 8 月 30 日 · 巴菲特 90 岁生日', W / 2, 1300, 36, 'sans_med', col=CREAM, a=a * k)
            cv.text('宣布：五家各持有 5% 以上', W / 2, 1360, 40, 'sans_bold', gold=True, a=a * k)
        source(cv, '伯克希尔 2020-08-31 新闻稿（东京时间 8:30）；日本大量保有报告制度（持股超过 5% 须公开）', a, y=1462)
    # ---- c2k：最多只买到 9.9%
    t0, t1 = win('c2k')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        vals = {c: 5.1 for c in ORDER_ALPHA}
        k = eo((t - WT('c2k', '百分之九点九')) / 0.5)
        stake_bars(cv, t, a, vals, y0=560, dy=96, vmax=11.0, line=9.9 if k > 0 else None, line_lab='9.9% 上限')
        kk = eo((t - WT('c2k', '董事会点头')) / 0.5)
        cv.text('除非对方董事会同意', W / 2, 1150, 44, 'sans_med', col=CREAM, a=a * kk)
        source(cv, '伯克希尔 2020-08-31 新闻稿', a, y=1462)
    # ---- c2l：赚的都是日元，日元一直在跌
    t0, t1 = S('c2l') - 0.3, CH['tk_ch2'][0] + 0.2
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        M.full(cv, 'j_night_711', t, t0, t1, a=a, speed=0.6, cap='东京车站')
        cv.text('¥', W / 2 - 60, 1120, 240, 'serif_black', col=YEN, a=a * eo((t - t0) / 0.5), glow=0.3)
        k = eio((t - WT('c2l', '日元一直在跌')) / 1.5)
        cv.line((W / 2 + 110, 990), (W / 2 + 110, 990 + 230 * k), RED, a, 8)
        cv.fillpoly([(W / 2 + 80, 990 + 230 * k), (W / 2 + 140, 990 + 230 * k), (W / 2 + 110, 1040 + 230 * k)], RED, a * (k > 0.05))
        cv.text('赚的都是日元', W / 2, 1360, 50, 'serif_black', col=CREAM, a=a, shadow=0.7)


# ======================================================================== 第三章：借日元，买日本
def shot_ch3(cv, t):
    # ---- c3a：106 → 157
    t0, t1 = win('c3a')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        ys, vs = SER['usdjpy']
        rv = eio((t - t0 - 0.2) / max(WT('c3a', '一百五十七') - t0, 1.0))
        r = line_chart(cv, ys, vs, 150, 950, 520, 1150, 2020.5, 2026.9, 100, 165, reveal=rv, a=a, ticks=(110, 130, 150),
                       xticks=(2021, 2023, 2025), col=YEN, tick_fmt=lambda v: f'¥{v:.0f}')
        cv.text('1 美元能换多少日元', 150, 440, 32, 'sans_med', col=CREAM, a=a, anchor='l')
        if r:
            X, Y, last = r
            cv.text('106', X(2020.66) + 10, Y(105.5) + 40, 40, 'sans_bold', col=CREAM, a=a, anchor='l')
            k = eo((t - WT('c3a', '一百五十七')) / 0.4)
            cv.text('157', last[0] - 10, last[1] - 50, 52, 'sans_bold', col=YEN, a=a * k, anchor='r')
        k2 = eo((t - WT('c3a', '三分之一')) / 0.5)
        cv.text('日元贬值约 1/3', W / 2, 1290, 60, 'sans_bold', col=YEN, a=a * k2, glow=0.2)
        source(cv, 'Yahoo Finance：USD/JPY 日线（2020-08-31 约 106 → 2026-11-06 约 157）', a, y=1462)
    # ---- c3b：拿美元直接买：被汇率吃掉一块
    t0, t1 = win('c3b')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        k = eio((p - 1.0) / 2.0)
        cv.text('$ → ¥ → $', W / 2, 520, 80, 'sans_bold', gold=True, a=a, glow=0.2)
        w0 = 520; wv = w0 * (1 - k / 3)
        cv.rrect(W / 2 - w0 / 2, 700, W / 2 + w0 / 2, 1100, 30, (0.2, 0.18, 0.16), a * 0.6)
        cv.rrect(W / 2 - wv / 2, 1100 - 400 * (1 - k / 3), W / 2 + wv / 2, 1100, 30, GOLD, a * 0.9, glow=0.15)
        cv.text('换回美元时缩水约 1/3', W / 2, 1220, 44, 'sans_med', col=CREAM, a=a * eo((p - 1.5) / 0.6))
    # ---- c3c：买日本的股票，就用日本的钱
    t0, t1 = win('c3c')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        nodes = [('日本债券市场', 320), ('伯克希尔', 760), ('五大商社', 1200)]
        for j, (nm, y) in enumerate(nodes):
            k = eo((p - j * 0.6) / 0.5)
            cv.rrect(260, y - 70, 820, y + 70, 22, (0.06, 0.05, 0.04), a * k)
            cv.rrect(260, y - 70, 820, y + 70, 22, GOLD_D if j != 1 else GOLD, a * k * 0.8, fill=False, th=2)
            cv.text(nm, W / 2, y, 50, 'serif_black', gold=j == 1, col=CREAM, a=a * k, glow=0.2 if j == 1 else 0)
        kf1 = eo((t - WT('c3c', '借日元')) / 0.5); kf2 = eo((t - WT('c3c', '再拿借来的')) / 0.5)
        flow(cv, t, (W / 2, 400), (W / 2, 680), 26, YEN, a * kf1, seed=2)
        flow(cv, t, (W / 2, 840), (W / 2, 1120), 26, YEN, a * kf2, seed=3)
        cv.text('发债借 ¥', W / 2 + 230, 540, 32, 'sans_bold', col=YEN, a=a * kf1, anchor='l')
        cv.text('用 ¥ 买股票', W / 2 + 230, 980, 32, 'sans_bold', col=YEN, a=a * kf2, anchor='l')
    # ---- c3d–c3e：日本买房、日本贷款：一起缩水，抵消
    t0, t1 = S('c3d') - 0.3, S('c3f') + 0.1
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        kh = eo(p / 0.6); km = eo((t - WT('c3d', '房贷')) / 0.5)
        shrink = eio((t - WT('c3e', '日元跌了')) / 2.5)
        s = 1.25 * (1 - 0.33 * shrink)
        house(cv, 300, 1000, s, a * kh)
        cv.text('房子（股票）', 300, 1080, 34, 'sans_med', col=GOLD_L, a=a * kh)
        mw = 300 * (1 - 0.33 * shrink)
        cv.rrect(780 - mw / 2, 1000 - mw * 0.75, 780 + mw / 2, 1000, 12, (0.85, 0.82, 0.76), a * km)
        for j in range(4): cv.line((780 - mw / 2 + 24, 1000 - mw * 0.75 + 40 + j * mw * 0.14), (780 + mw / 2 - 24, 1000 - mw * 0.75 + 40 + j * mw * 0.14), (0.4, 0.38, 0.36), a * km, 2)
        cv.text('¥ 房贷', 780, 1000 - mw * 0.75 - 40, 40, 'sans_bold', col=YEN, a=a * km)
        cv.text('房贷（日元债）', 780, 1080, 34, 'sans_med', col=CREAM, a=a * km)
        cv.text('日元跌了 → 两边换成美元一起变少', W / 2, 480, 38, 'sans_med', col=CREAM, a=a * eo((t - WT('c3e', '日元跌了')) / 0.5))
        ko = eo((t - WT('c3e', '正好抵消')) / 0.5)
        if ko > 0:
            cv.text('一边亏  一边赚  =  抵消', W / 2, 1250, 56, 'sans_bold', gold=True, a=a * ko, glow=0.25)
        source(cv, '巴菲特 2023 年致股东信：日元走弱为伯克希尔累计带来约 $19 亿收益；2024 年信：累计税后 $23 亿', a * ko, y=1462)
    # ---- c3f：不赌汇率
    t0, t1 = win('c3f')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        M.full(cv, 'x_bwbi_b', t, t0, t1, a=a, src_t0=3.0, cap='巴菲特')
        quote_card(cv, 'qfx', t, t0 + 0.3, t1, cy=1130, en_size=32, cn_size=40, a=a)
    # ---- c3g–c3h：房租减房贷：8.62 vs 1.8
    t0, t1 = S('c3g') - 0.3, S('c3i') + 0.1
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        kr = eo((t - WT('c3h', '房租')) / 0.5); kd = eo((t - WT('c3h', '房贷')) / 0.5)
        cv.text('每年的账', W / 2, 400, 60, 'serif_black', col=CREAM, a=a)
        kg = env(t, S('c3g'), WT('c3h', '房租') + 0.3, 0.3, 0.3)
        cv.text('房租  −  房贷', W / 2, 820, 90, 'serif_black', gold=True, a=a * kg, glow=0.25)
        flow(cv, t, (280, 500), (280, 1150), 90, GOLD, a * kr * 1.5, dens=0.3, seed=5)
        flow(cv, t, (800, 500), (800, 1150), 20, YEN, a * kd * 1.5, dens=0.2, seed=6)
        cv.text('分红（房租）', 280, 1220, 36, 'sans_med', col=GOLD_L, a=a * kr)
        v = counter(0, 8.62, t, WT('c3h', '八点六二亿') - 0.2, 0.9, lambda v: f'${v:.2f} 亿')
        cv.text(v, 280, 1300, 64, 'sans_bold', gold=True, a=a * kr, glow=0.3)
        cv.text('利息（房贷）', 800, 1220, 36, 'sans_med', col=CREAM, a=a * kd)
        cv.text('≈ $1.8 亿', 800, 1300, 64, 'sans_bold', col=YEN, a=a * eo((t - WT('c3h', '一点八亿')) / 0.4))
        cv.text('平均年利率 1.2%', 800, 1370, 28, 'sans_light', col=GREY, a=a * eo((t - WT('c3h', '一点二')) / 0.4))
        source(cv, '伯克希尔 2025 年致股东信（2025 年分红 $8.62 亿；日元借款平均利率 1.2%）；利息估算 $149 亿 × 1.2%', a, y=1462)
    # ---- c3i：≈ 5 倍 + 芒格
    t0, t1 = win('c3i')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        k = eo((t - WT('c3i', '五倍')) / 0.5)
        tm = WT('c3i', '芒格说')
        if t < tm:
            cv.text('收进来 ≈ 付出去 × 5', W / 2, 800, 80, 'sans_bold', gold=True, a=a * k * env(t, t0, tm + 0.2, 0.3, 0.3), glow=0.3)
        else:
            M.full(cv, 'x_bwbm_munger2', t, tm - 0.3, t1, a=a, speed=0.6, cap='查理·芒格')
            quote_card(cv, 'qmunger', t, tm - 0.1, t1, cy=1150, en_size=30, cn_size=36, a=a)
        source(cv, '芒格，Acquired 播客 2023-10（据 Fortune 2023-11-01 刊出的文字）', a, y=1462)
    # ---- c3j：算不算好生意？
    t0, t1 = S('c3j') - 0.3, CH['tk_ch3'][0] + 0.2
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        cv.text('价格便宜 ✓', W / 2, 560, 52, 'sans_bold', col=GREEN, a=a * eo(p / 0.4))
        cv.text('钱几乎不要成本 ✓', W / 2, 660, 52, 'sans_bold', col=GREEN, a=a * eo((t - WT('c3j', '钱也')) / 0.4))
        k = eo((t - WT('c3j', '好生意')) / 0.5)
        cv.text('好生意？', W / 2, 950, 130, 'serif_black', gold=True, a=a * k, glow=0.35, scale=1.1 - 0.1 * k)


# ======================================================================== 第四章：是不是好生意
FR_ITEMS = ['人们需要它', '没有别的东西能替代它', '价格不受管制']


def shot_ch4(cv, t):
    # ---- c4a–c4b：三条标准
    t0, t1 = S('c4a') - 0.3, S('c4c') + 0.1
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        cv.text('最好的生意', W / 2, 420, 80, 'serif_black', gold=True, a=a * eo(p / 0.5), glow=0.3)
        cv.text('别人替代不了 · 想涨价就能涨价', W / 2, 520, 36, 'sans_med', col=CREAM, a=a * eo((p - 0.5) / 0.5))
        tt = [WT('c4b', '人们需要'), WT('c4b', '没有别的'), WT('c4b', '价格不受')]
        vis = eo((t - S('c4b')) / 0.5)
        check_list(cv, t, a * vis, FR_ITEMS, x=180, y0=700, dy=110, size=46, states=[True, True, True], t_states=tt)
        kq = eo((t - WT('c4b', '三条都占')) / 0.5)
        cv.text('→ 能经常涨价，赚大钱', W / 2, 1100, 44, 'sans_bold', gold=True, a=a * kq)
        source(cv, '巴菲特 1991 年致股东信：经济特许权三条件（needed or desired / no close substitute / not subject to price regulation）', a, y=1462)
    # ---- c4c：可口可乐
    t0, t1 = win('c4c')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        M.full(cv, 'x_bwb_cherrycoke', t, t0, t1, a=a, cap='巴菲特与可口可乐')
        check_list(cv, t, a, FR_ITEMS, x=180, y0=990, dy=96, size=40, states=[True, True, True], t_states=[t0, t0, t0])
        cv.text('可口可乐', W / 2, 1330, 50, 'serif_black', col=RED, a=a)
    # ---- c4d：商社：大宗商品 → 第二条打叉
    t0, t1 = win('c4d')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        M.full(cv, 'j_lng_ship', t, t0, t1, a=a, speed=0.6, cap='液化天然气运输船')
        tt = [S('c4d'), WT('c4d', '钢厂只看'), S('c4d')]
        check_list(cv, t, a, FR_ITEMS, x=180, y0=990, dy=96, size=40, states=[True, False, None], t_states=tt)
        k = eo((t - WT('c4d', '谁也说了不算')) / 0.5)
        cv.text('价格由全世界的买卖决定', W / 2, 1330, 40, 'sans_bold', col=(1.0, 0.55, 0.5), a=a * k)
    # ---- c4e：资源占利润四到五成
    t0, t1 = win('c4e')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        cv.text('利润跟着商品价格坐过山车', W / 2, 420, 50, 'serif_black', col=CREAM, a=a)
        k = eio((t - WT('c4e', '四到五成')) / 1.0)
        for j, (nm, x) in enumerate((('三菱商事', 300), ('三井物产', 780))):
            cv.arc((x, 820), 170, -math.pi / 2, 1.5 * math.pi, (0.25, 0.24, 0.26), a, 46)
            cv.arc((x, 820), 170, -math.pi / 2, -math.pi / 2 + 2 * math.pi * 0.45 * k, GOLD_D, a, 46)
            cv.text('40–50%' if k > 0.5 else '', x, 800, 50, 'sans_bold', gold=True, a=a * k)
            cv.text('来自资源', x, 860, 28, 'sans_light', col=CREAM, a=a * k)
            cv.text(nm, x, 1060, 44, 'serif_black', col=CREAM, a=a)
        source(cv, '日本信用评级机构 JCR 2025-06：“40 to 50% of net income is accounted for by the resource sector for Mitsubishi and MITSUI”', a, y=1462)
    # ---- c4f：2016：历史上第一次年度亏损
    t0, t1 = win('c4f')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        k = eexp((t - WT('c4f', '第一次年度亏损') + 0.3) / 1.0)
        cv.text('截至 2016 年 3 月的财年', W / 2, 420, 36, 'sans_med', col=CREAM, a=a)
        cv.line((160, 760), (920, 760), GREY, a, 2)
        cv.text('0', 140, 760, 26, 'oswald', col=DIM, a=a, anchor='r')
        for j, (nm, v, x) in enumerate((('三菱商事', 1494, 330), ('三井物产', 834, 750))):
            h = 420 * v / 1494 * k
            cv.rect(x - 90, 760, x + 90, 760 + h, RED, a * 0.9, glow=0.1)
            cv.text(f'−{v:,.0f} 亿日元', x, 760 + h + 46, 40, 'sans_bold', col=(1.0, 0.55, 0.5), a=a * min(1, k * 2))
            cv.text(nm, x, 700, 40, 'serif_black', col=CREAM, a=a)
        cv.text('都是公司历史上第一次年度亏损', W / 2, 1360, 40, 'sans_bold', col=CREAM, a=a * eo((t - WT('c4f', '历史上')) / 0.5))
        source(cv, 'Reuters 2016-04；Mining.com 2016-05（截至 2016-03 财年净亏损：三菱商事 1,494 亿日元，三井物产 834 亿日元）', a, y=1462)
    # ---- c4g：不是印钞机；护城河长在别处
    t0, t1 = win('c4g')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        moat(cv, t, W / 2, 820, a, lit=[None] * 4)
        k = eo((t - WT('c4g', '护城河')) / 0.5)
        cv.text('不是“印钞机”', W / 2, 400, 64, 'serif_black', col=CREAM, a=a, shadow=0.7)
        cv.text('但护城河，长在别的地方', W / 2, 1320, 44, 'sans_bold', gold=True, a=a * k)
    # ---- c4h：①低成本：成本曲线
    t0, t1 = win('c4h')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        moat_badge(cv, '①', '成本低', a)
        costs = [22, 26, 30, 35, 42, 50, 58, 68, 80, 95]
        drop = eio((t - WT('c4h', '价格跌的时候')) / 2.0)
        price = lerp(100, 45, drop)
        x0, x1, base, top = 140, 940, 1300, 600
        def Y(v): return base - (base - top) * v / 110
        bw = (x1 - x0) / len(costs)
        for j, c in enumerate(costs):
            on = c <= price
            k = eo((p - j * 0.05) / 0.4)
            col = GOLD if j < 3 else (GOLD_D if on else (0.25, 0.22, 0.22))
            cv.rect(x0 + j * bw + 6, Y(c * k), x0 + (j + 1) * bw - 6, base, col, a * (0.95 if on else 0.6), glow=0.12 if j < 3 else 0)
        cv.line((x0, Y(price)), (x1, Y(price)), RED, a, 3)
        cv.text(f'商品价格', x1, Y(price) - 26, 28, 'sans_bold', col=RED, a=a, anchor='r')
        cv.text('成本最低', x0 + bw * 1.5, base + 40, 30, 'sans_bold', col=GOLD_L, a=a)
        cv.text('成本最高', x1 - bw, base + 40, 30, 'sans_light', col=GREY, a=a)
        cv.text('例：澳大利亚皮尔巴拉铁矿', W / 2, 510, 30, 'sans_light', col=CREAM, a=a * eo((t - WT('c4h', '澳大利亚')) / 0.4))
        source(cv, '三井物产持有澳大利亚皮尔巴拉铁矿权益（JCR 2025-06）；示意图，非实际成本数据', a, y=1462)
    # ---- c4i：②收费站
    t0, t1 = win('c4i')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        M.full(cv, 'j_lng_plant', t, t0, t1, a=a, speed=0.6, cap='液化天然气接收站')
        moat_badge(cv, '②', '像收费站', a, y=920)
        toll(cv, t, a, cy=1210)
        cv.text('长期合同 · 用多少收多少', W / 2, 1400, 36, 'sans_bold', gold=True, a=a * eo((t - WT('c4i', '长期合同')) / 0.5))
        source(cv, '本片解读：液化天然气项目、发电厂常以长期合同锁定买家', a, y=1462)
    # ---- c4j：③街角的生意
    t0, t1 = win('c4j')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        M.full(cv, 'j_crossing', t, t0, t1, a=a, speed=0.7, cap='东京街头')
        moat_badge(cv, '③', '街角的生意', a, y=1000)
        cv.text('加盟连锁 · 天天有人进门', W / 2, 1180, 44, 'sans_bold', col=CREAM, a=a * eo((t - WT('c4j', '加盟连锁')) / 0.5))
    # ---- c4k：④关系与信用
    t0, t1 = win('c4k')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        M.full(cv, 'j_commuters', t, t0, t1, a=a, speed=0.7, cap='东京')
        moat_badge(cv, '④', '关系和信用', a, y=920)
        globe(cv, t, W / 2, 1170, 170, rot=-math.radians(139.7) + math.pi + p * 0.06, tilt=0.45, a=a, arcs=eio(p / 3.5))
        cv.text('信用好 → 借钱也便宜', W / 2, 1400, 36, 'sans_bold', gold=True, a=a * eo((t - WT('c4k', '信用好')) / 0.5))
    # ---- c4l：股东每投 100 块，一年赚回 10–16 块
    t0, t1 = win('c4l')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        M.full(cv, 'v_tokyo', t, t0, t1, a=a, src_t0=36.0, speed=0.5, cap='东京丸之内')
        cv.text('股东每投进去 100 块，一年赚回', W / 2, 910, 34, 'sans_med', col=CREAM, a=a)
        roe = [('伊藤忠', 15.7), ('丸红', 14.2), ('住友商事', 12.4), ('三井物产', 11.9), ('三菱商事', 10.3)]
        ts = WT('c4l', '十到十六块') - 0.6
        hbar_rows(cv, [(n, v, ts + j * 0.15) for j, (n, v) in enumerate(roe)], t, a, x0=330, x1=860, y0=990, dy=86, vmax=18,
                  fmt=lambda v: f'{v:.1f} 块', size=32, lab_size=30)
        source(cv, '截至 2025-03 财年净资产收益率（IR Tracker 五社比较）', a, y=1462)
    # ---- c4m：赚来的钱大部分再投回去
    t0, t1 = win('c4m')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        M.full(cv, 'j_cine_skyline', t, t0, t1, a=a, speed=0.7, cap='东京')
        cv.text('六大商社 · 一年', W / 2, 910, 36, 'sans_med', col=CREAM, a=a)
        ki = eo((t - WT('c4m', '一年赚')) / 0.5); ko = eo((t - WT('c4m', '新的投资')) / 0.5)
        flow(cv, t, (200, 1080), (540, 1170), 40, GOLD, a * ki * 1.6, dens=0.3, seed=7)
        flow(cv, t, (540, 1170), (880, 1260), 36, GOLD_D, a * ko * 1.6, dens=0.3, seed=8)
        cv.text('赚 3.9 万亿日元', 280, 1010, 40, 'sans_bold', gold=True, a=a * ki)
        cv.text('再投 3.7 万亿', 800, 1330, 40, 'sans_bold', col=CREAM, a=a * ko)
        cv.text('赚来的钱，大部分得再投回去', W / 2, 1400, 32, 'sans_med', col=CREAM, a=a * eo((p - 0.8) / 0.5))
        source(cv, 'JCR 2025-06：截至 2025-03 财年六大商社（含双日）净利润合计 39,368 亿日元，新投资约 3.7 万亿日元', a, y=1462)
    # ---- c4n：三等生意
    t0, t1 = win('c4n')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        steps = [('最好的', '喜诗糖果：几乎不用再投钱', WT('c4n', '最好的'), GOLD),
                 ('第二等', '电力公司：不断投钱才能多赚', WT('c4n', '第二等'), GOLD_D),
                 ('最差的', '航空公司：越投越亏', WT('c4n', '最差的'), (0.5, 0.3, 0.3))]
        for j, (nm, desc, tj, col) in enumerate(steps):
            col = np.asarray(col, np.float32)
            k = eo((t - tj) / 0.5)
            y = 520 + j * 230; x0_ = 160 + j * 60
            cv.rect(x0_, y - 70, 920, y + 70, col * 0.35, a * k)
            cv.rect(x0_, y - 70, x0_ + 10, y + 70, col, a * k)
            cv.text(nm, x0_ + 40, y - 22, 50, 'serif_black', col=CREAM, a=a * k, anchor='l')
            cv.text(desc, x0_ + 40, y + 34, 30, 'sans_light', col=CREAM, a=a * k, anchor='l')
        ks = eo((t - WT('c4n', '商社，属于')) / 0.5)
        if ks > 0:
            cv.rrect(200, 680, 940, 840, 14, GOLD, a * ks, fill=False, th=4, glow=0.3)
            cv.text('← 商社', 900, 760, 44, 'sans_bold', gold=True, a=a * ks, anchor='r')
        source(cv, '巴菲特 2007 年致股东信：Businesses – The Great, the Good and the Gruesome（归类为本片解读）', a, y=1462)
    # ---- c4o：普通生意会被糟糕的管理拖垮
    t0, t1 = win('c4o')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        M.full(cv, 'x_bwbi_c', t, t0, t1, a=a, src_t0=1.0, cap='巴菲特')
        quote_card(cv, 'qmanage', t, t0 + 0.3, t1, cy=1140, en_size=32, cn_size=40, a=a)
    # ---- c4p：看管事的人
    t0, t1 = S('c4p') - 0.3, CH['tk_ch4'][0] + 0.2
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        M.full(cv, 'v_tokyo', t, t0, t1, a=a, src_t0=22.0, speed=0.6, cap='东京丸之内')
        k = eo((t - WT('c4p', '管事的人')) / 0.5)
        cv.text('价格  +  管事的人', W / 2, 1080, 72, 'serif_black', gold=True, a=a * k, glow=0.3)


def moat_badge(cv, num, txt, a, y=400):
    cv.text(num, W / 2 - 170, y, 70, 'serif_black', gold=True, a=a, glow=0.25)
    cv.text(txt, W / 2 - 110, y, 64, 'serif_black', col=CREAM, a=a, anchor='l', shadow=0.7)


def moat(cv, t, cx, cy, a, lit):
    """城堡 + 四段护城河"""
    for j in range(4):
        a0 = -math.pi / 2 + j * math.pi / 2 + 0.06; a1 = a0 + math.pi / 2 - 0.12
        cv.arc((cx, cy), 300, a0, a1, (0.35, 0.55, 0.75), a * 0.7, 26)
    cv.rect(cx - 150, cy - 90, cx + 150, cy + 130, (0.14, 0.12, 0.11), a)
    for k in range(5): cv.rect(cx - 150 + k * 66, cy - 120, cx - 150 + k * 66 + 36, cy - 90, (0.14, 0.12, 0.11), a)
    cv.rect(cx - 40, cy + 40, cx + 40, cy + 130, (0.05, 0.04, 0.04), a)
    cv.poly([(cx - 150, cy - 90), (cx + 150, cy - 90), (cx + 150, cy + 130), (cx - 150, cy + 130), (cx - 150, cy - 90)], GOLD_D, a * 0.8, 2)


def toll(cv, t, a, cy=860, s=1.0):
    """收费站：船（货车）一辆辆经过，计数器跳动"""
    cx = W / 2
    cv.rect(160, cy + 70, 920, cy + 80, GREY, a * 0.6)
    cv.rect(cx - 50, cy - 110, cx + 50, cy + 70, (0.12, 0.11, 0.10), a)
    cv.rect(cx - 80, cy - 140, cx + 80, cy - 110, GOLD_D, a)
    cv.text('TOLL', cx, cy - 125, 22, 'oswald', col=(0.1, 0.08, 0.06), a=a)
    gate = 0.5 + 0.5 * math.sin(t * 2.4)
    cv.line((cx + 50, cy - 20), (cx + 50 + 180 * math.cos(-gate * 1.2), cy - 20 + 180 * math.sin(-gate * 1.2)), RED, a, 6)
    period = 2.6
    n = int(t / period)
    for k in range(3):
        u = ((t / period) - n + k / 3) % 1.0
        x = lerp(80, 1000, u)
        cv.rrect(x - 70, cy + 10, x + 70, cy + 66, 10, GOLD if k % 2 == 0 else BLUE, a * 0.9)
        cv.rect(x + 30, cy - 20, x + 70, cy + 10, GOLD_L, a * 0.8)
    cv.text(f'¥ {(n * 3) % 1000 * 1250:,}', cx + 260, cy - 120, 40, 'oswald', gold=True, a=a, glow=0.2)


# ======================================================================== 第五章：管事的人
def shot_ch5(cv, t):
    # ---- c5a–c5b：2023 年春，92 岁，东京
    t0, t1 = S('c5a') - 0.3, S('c5c') + 0.1
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        M.full(cv, 'v_tokyo', t, t0, t1, a=a, src_t0=104.0, speed=0.35, cap='东京站丸之内一侧')
        k = eo((t - WT('c5a', '二零二三年春天')) / 0.5)
        cv.text('2023 年 4 月 · 东京', W / 2, 980, 60, 'serif_black', gold=True, a=a * k, glow=0.25)
        cv.text('92 岁的巴菲特与阿贝尔，挨个拜访五家公司', W / 2, 1070, 36, 'sans_med', col=CREAM, a=a * eo((t - WT('c5a', '九十二岁')) / 0.5))
        kb = eo((t - S('c5b')) / 0.5)
        cv.text('回来以后，他在信里写下了自己看到的东西', W / 2, 1200, 34, 'sans_light', col=GREY, a=a * kb)
        source(cv, '巴菲特 2023 年致股东信：“after Greg Abel and I made a trip to Tokyo to talk with their managements”', a, y=1462)
    # ---- c5c–c5e：三条
    t0, t1 = S('c5c') - 0.3, S('c5f') + 0.1
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        items = [('01', '赚了钱不乱花', '只拿约 1/3 利润分红，其余发展生意、回购', S('c5c')),
                 ('02', '股份越来越值钱', '持续回购，股数减少，不靠增发', S('c5d')),
                 ('03', '老板不贪', '薪酬远没有美国同行夸张', S('c5e'))]
        M.full(cv, 'v_tokyo', t, t0, t1, a=a, src_t0=58.0, speed=0.45, cap='东京丸之内')
        for j, (n_, h_, d_, tj) in enumerate(items):
            k = eo((t - tj) / 0.5)
            y = 950 + j * 160
            cur = tj <= t < (items[j + 1][3] if j < 2 else S('c5f'))
            cv.text(n_, 170, y, 52, 'oswald', col=GOLD, a=a * k)
            cv.text(h_, 240, y - 18, 48 if cur else 42, 'serif_black', gold=cur, col=CREAM, a=a * k, anchor='l', glow=0.2 if cur else 0)
            cv.text(d_, 240, y + 40, 28, 'sans_light', col=GREY, a=a * k, anchor='l')
        source(cv, '巴菲特 2023 年致股东信（三条均为信中原意）', a, y=1462)
    # ---- c5f：5% → 7.4% → 8.5%
    t0, t1 = win('c5f')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        k1 = eio((t - WT('c5f', '百分之七点四')) / 0.8); k2 = eio((t - WT('c5f', '百分之八点五')) / 0.8)
        v = 5.1 + 2.3 * k1 + 1.1 * k2
        M.full(cv, 'j_night_towers', t, t0, t1, a=a, speed=0.6, cap='东京')
        cv.text('价格便宜，人也靠得住', W / 2, 920, 44, 'serif_black', col=CREAM, a=a)
        stake_bars(cv, t, a, {c: v for c in ORDER_ALPHA}, y0=1010, dy=72, vmax=11.0)
        cv.text('2023 年 4 月 7.4% → 6 月超过 8.5%', W / 2, 1400, 30, 'sans_med', col=GOLD_L, a=a * k1)
        source(cv, 'Reuters 2023-04-11（对日经称 7.4%）；伯克希尔 2023-06 声明（超过 8.5%）', a, y=1462)
    # ---- c5g：9.9% 线放宽 → 2025 年底各家持股
    t0, t1 = win('c5g')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        kd = eo((t - WT('c5g', '主动同意')) / 0.5)
        kr = eio((t - WT('c5g', '主动同意') - 0.3) / 1.2)
        h25 = CALC['holdings2025']
        vals = {c: lerp(8.6, h25[c], kr) for c in ORDER_ALPHA}
        stake_bars(cv, t, a, vals, y0=560, dy=100, vmax=12.0, line=9.9, line_lab='9.9%', line_dash=kd > 0.5)
        cv.text('2025 年底', W / 2, 1150, 34, 'sans_med', col=GOLD_L, a=a * kr)
        source(cv, '伯克希尔 2024 年致股东信（五家同意适度放宽上限）；2025 年致股东信持仓表', a, y=1462)
    # ---- c5h：账本
    t0, t1 = S('c5h') - 0.3, CH['tk_ch5'][0] + 0.2
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        cv.text('没人看的市场', W / 2 - 220, 700, 46, 'sans_med', col=GREY, a=a * eo(p / 0.4))
        cv.text('→', W / 2, 700, 60, 'sans_bold', gold=True, a=a * eo((p - 0.4) / 0.4))
        cv.text('主动请他多买', W / 2 + 220, 700, 46, 'sans_bold', gold=True, a=a * eo((p - 0.8) / 0.4))
        k = eo((t - WT('c5h', '到底赚了多少')) / 0.5)
        cv.text('六年下来，赚了多少？', W / 2, 950, 70, 'serif_black', col=CREAM, a=a * k, shadow=0.7)


# ======================================================================== 第六章：五十年不卖
def shot_ch6(cv, t):
    # ---- c6a：成本 154 / 市值 354 / 分红 8.6
    t0, t1 = win('c6a')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        fx.bars3d(cv, t, t0, t1, ('买入成本', 154, '$154 亿', WT('c6a', '一百五十四亿') - 0.3),
                  ('2025 年底市值', 354, '$354 亿', WT('c6a', '三百五十四亿') - 0.3), a=a, title='算一下账', hmax=1.15)
        k = eo((t - WT('c6a', '八点六亿')) / 0.5)
        if k > 0:
            cv.rrect(220, 1250, 860, 1370, 18, (0.03, 0.025, 0.025), a * k * 0.85)
            cv.text('2025 年分红 $8.6 亿', W / 2, 1310, 50, 'sans_bold', gold=True, a=a * k)
        source(cv, '伯克希尔 2025 年致股东信（持仓表：成本 $153.82 亿、市值 $353.68 亿、2025 年分红 $8.62 亿）', a, y=1462)
    # ---- c6b：股价赛跑
    t0, t1 = win('c6b')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        rv = eio((t - t0 - 0.2) / max(WT('c6b', '丸红') - t0, 2.0))
        base = 2020.66
        x0, x1, y0, y1 = 150, 930, 480, 1250
        cv.text('股价倍数（宣布前一天 = 1，日元计）', 150, 420, 28, 'sans_med', col=CREAM, a=a, anchor='l')
        cols = {'marubeni': GOLD_L, 'mitsubishi': GOLD, 'mitsui': GOLD_D, 'sumitomo': (0.9, 0.7, 0.4), 'itochu': (0.8, 0.6, 0.35), 'n225': GREY}
        for k_ in ['n225', 'itochu', 'sumitomo', 'mitsui', 'mitsubishi', 'marubeni']:
            ys, vs = SER[k_]
            b = ser_at(k_, base)
            r = line_chart(cv, ys, vs / b, x0, x1, y0, y1, base, 2026.86, 0.5, 9.0, reveal=rv, a=a, col=cols[k_], lw=3 if k_ != 'n225' else 2,
                           ticks=(1, 2, 4, 6, 8) if k_ == 'n225' else (), xticks=(2021, 2023, 2025) if k_ == 'n225' else (),
                           tick_fmt=lambda v: f'×{v:.0f}', glow=0.25)
            if r and rv > 0.97:
                m_ = CALC['mult'][k_]
                lab = ('日经 225' if k_ == 'n225' else CN5[k_]) + f'  ×{m_:.1f}'
                cv.text(lab, r[2][0] + 10, r[2][1], 24 if k_ != 'marubeni' else 28, 'sans_bold', col=cols[k_], a=a, anchor='l')
        k = eo((t - WT('c6b', '将近六倍')) / 0.5)
        cv.text('五家平均 ×5.8', W / 2, 1340, 50, 'sans_bold', gold=True, a=a * k, glow=0.25)
        source(cv, 'Yahoo Finance：2020-08-28 → 2026-11-06 收盘价，拆股调整，日元计，不含分红', a, y=1462)
    # ---- c6c：会卖吗？
    t0, t1 = win('c6c')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        M.full(cv, 'j_night_street', t, t0, t1, a=a, speed=0.6, cap='东京新宿')
        cv.text('苹果：涨多了 → 卖掉大半', W / 2, 980, 44, 'sans_bold', col=(1.0, 0.55, 0.5), a=a * eo(p / 0.5))
        k = eo((t - WT('c6c', '他会卖吗')) / 0.5)
        cv.text('日本这五家，会卖吗？', W / 2, 1180, 76, 'serif_black', gold=True, a=a * k, glow=0.3)
    # ---- c6d：未来 50 年都不会考虑卖出
    t0, t1 = win('c6d')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        M.full(cv, 'x_bwb_meeting', t, t0, t1, a=a, src_t0=18.0, speed=0.7, cap='伯克希尔股东大会')
        quote_card(cv, 'q50', t, WT('c6d', '未来五十年') - 0.3, t1, cy=1130, en_size=36, cn_size=46, a=a)
        cv.text('2025 年 5 月 · 作为 CEO 的最后一次股东大会', W / 2, 920, 30, 'sans_med', col=GOLD_L, a=a)
    # ---- c6e：阿贝尔：与美国核心持仓并列
    t0, t1 = win('c6e')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        cv.text('阿贝尔的第一封股东信 · 2026 年 2 月', W / 2, 400, 32, 'sans_med', col=GOLD_L, a=a)
        us = ['苹果', '美国运通', '可口可乐', '穆迪']
        for j, s_ in enumerate(us):
            k = eo((p - j * 0.12) / 0.4)
            cv.rrect(140, 500 + j * 100, 500, 580 + j * 100, 12, (0.06, 0.05, 0.04), a * k)
            cv.text(s_, 320, 540 + j * 100, 38, 'sans_med', col=CREAM, a=a * k)
        kj = eo((t - WT('c6e', '日本这五家')) / 0.5)
        for j, c in enumerate(ORDER_ALPHA):
            cv.rrect(580, 470 + j * 85, 940, 540 + j * 85, 12, (0.08, 0.06, 0.04), a * kj)
            cv.text(CN5[c], 760, 505 + j * 85, 36, 'sans_bold', gold=True, a=a * kj)
        cv.text('美国核心持仓', 320, 960, 28, 'sans_light', col=GREY, a=a)
        cv.text('日本五大商社', 760, 960, 28, 'sans_light', col=GOLD, a=a * kj)
        quote_card(cv, 'qcomparable', t, WT('c6e', '排在了一起') - 0.2, t1, cy=1210, en_size=28, cn_size=36, a=a)
    # ---- c6f：阿贝尔访东京；考虑提高到 15%
    t0, t1 = win('c6f')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        M.full(cv, 'j_aerial_city', t, t0, t1, a=a, speed=0.6, cap='东京')
        cv.text('2026 年 9 月 · 阿贝尔访问东京', W / 2, 960, 40, 'sans_med', col=CREAM, a=a)
        cv.text('“持有几十年”', W / 2, 1050, 50, 'serif_semi', col=GOLD_L, a=a * eo((t - WT('c6f', '几十年')) / 0.5))
        k = eo((t - WT('c6f', '百分之十五')) / 0.5)
        cv.text('10%  →  15%？', W / 2, 1200, 80, 'sans_bold', gold=True, a=a * k, glow=0.3)
        source(cv, 'Quartz / Yahoo Finance 2026-09（阿贝尔访日表态）；Bloomberg 2026-09-17（据报道考虑提高到 15%）', a, y=1462)
    # ---- c6g：风险
    t0, t1 = win('c6g')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        M.full(cv, 'j_lng_ship', t, t0, t1, a=a, speed=0.5, cap='液化天然气运输船')
        cv.text('风险，一直都在', W / 2, 920, 56, 'serif_black', col=CREAM, a=a)
        xs = np.linspace(150, 930, 200)
        ys = 1080 + 70 * np.sin(xs / 80 + p * 1.5) * np.cos(xs / 230)
        cv.poly(np.stack([xs, ys], 1), (1.0, 0.55, 0.5), a, 4)
        cv.text('商品价格起伏 → 利润波动', W / 2, 1200, 34, 'sans_med', col=CREAM, a=a * eo((p - 0.3) / 0.5))
        k = eo((t - WT('c6g', '日本的利率')) / 0.5)
        cv.text('日本利率上行 → 新借日元变贵 ↗', W / 2, 1320, 34, 'sans_med', col=YEN, a=a * k)
    # ---- c6h：苹果太贵 vs 日本便宜得离谱
    t0, t1 = win('c6h')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        ka = eo((t - WT('c6h', '苹果后来太贵了')) / 0.5); kj = eo((t - WT('c6h', '便宜得离谱')) / 0.5)
        cv.rect(80, 380, 520, 1300, (0.12, 0.04, 0.04), a * 0.6)
        cv.rect(560, 380, 1000, 1300, (0.12, 0.09, 0.03), a * 0.6)
        cv.text('苹果', 300, 520, 70, 'serif_black', col=CREAM, a=a)
        cv.text('太贵了', 300, 760, 64, 'serif_black', col=RED, a=a * ka)
        cv.text('→ 卖', 300, 900, 60, 'sans_bold', col=RED, a=a * ka)
        cv.text('日本商社', 780, 520, 70, 'serif_black', gold=True, a=a)
        cv.text('便宜得离谱', 780, 740, 56, 'serif_black', gold=True, a=a * kj)
        cv.text('+ 几乎免费的钱', 780, 830, 40, 'sans_med', col=CREAM, a=a * eo((t - WT('c6h', '几乎不要成本')) / 0.5))
        cv.text('→ 买，拿五十年', 780, 940, 50, 'sans_bold', gold=True, a=a * eo((t - WT('c6h', '几乎不要成本') - 0.4) / 0.5))
        cv.text('同一个道理：价格决定一切', W / 2, 1220, 46, 'serif_semi', col=GOLD_L, a=a * eo((p - 3.0) / 0.6))
    # ---- c6i–c6m：四条道理
    t0, t1 = S('c6i') - 0.3, S('c6n') + 0.1
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        M.full(cv, 'j_cine_miyajima', t, t0, t1, a=a, speed=0.35, cap='日本')
        cv.text('这笔东京的投资，留下了四条朴素的道理', W / 2, 905, 32, 'sans_med', col=CREAM, a=a)
        L = [('01', '找好价格', '每年能赚回多少，和存银行比一比', 'c6j'), ('02', '用对的钱', '买哪里的资产，就借哪里的钱', 'c6k'),
             ('03', '看清成色', '不是最好的生意，就更要看价格、看人', 'c6l'), ('04', '有耐心', '花一年慢慢买，用几十年慢慢拿', 'c6m')]
        for j, (n_, h_, d_, i_) in enumerate(L):
            k = eo((t - S(i_)) / 0.5)
            cur = S(i_) <= t < (S(L[j + 1][3]) if j < 3 else S('c6n'))
            y = 990 + j * 118
            cv.text(n_, 170, y, 48, 'oswald', col=GOLD, a=a * k)
            cv.text(h_, 240, y - 16, 46 if cur else 40, 'serif_black', gold=cur, col=CREAM, a=a * k * (1 if cur else 0.75), anchor='l', glow=0.25 if cur else 0)
            cv.text(d_, 240, y + 30, 26, 'sans_light', col=CREAM if cur else GREY, a=a * k, anchor='l')
    # ---- c6n：三十年前追日本，三十年后不看日本
    t0, t1 = S('c6n') - 0.3, CH['end'][0] + 0.3
    a = env(t, t0, t1, 0.4, 0.5)
    if a > 0:
        M.full(cv, 'j_bay', t, t0, t1, a=a, src_t0=4.0, speed=0.6, cap='东京')
        k1 = eo((t - S('c6n')) / 0.5); k2 = eo((t - WT('c6n', '三十年后')) / 0.5); k3 = eo((t - WT('c6n', '巴菲特，就是')) / 0.6)
        cv.text('三十年前，全世界都在追日本', W / 2, 960, 42, 'sans_med', col=CREAM, a=a * k1)
        cv.text('三十年后，全世界都不看日本了', W / 2, 1040, 42, 'sans_med', col=CREAM, a=a * k2)
        cv.text('他在没人看的时候，走了进去', W / 2, 1190, 58, 'serif_black', gold=True, a=a * k3, glow=0.3)
