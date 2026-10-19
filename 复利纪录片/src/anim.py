"""第三版动画段（约 1 分 35 秒）：复利的第一性原理 → 人生的复利 → 总结 → 品牌片尾。
叙事：乘法 → 分叉（412 倍）→ 腰斩要翻倍 → 乘以零 → 先冲过终点 → 暂时 vs 永久 → 知识、信任、技能、健康 → 总结。
每个视觉都卡在解说关键词上（t3.wt）；数字全部来自 script.MATH（与 SOURCES.md 一致）。"""
import math
import numpy as np, cv2
from engine import W, H, GOLD, GOLD_HI, GOLD_SUB, CYAN, RED, WHITE, GREY, smooth, clamp01, ease_out, ease_io, ease_back, win, lerp, splat, blur
from common import put_text, gold_text, footnote, mask_points
import vis as V
import t3
import brand_bridge as BB
from script import MATH

S, wt = t3.SENTS, t3.wt
RED_S = np.array([1.0, 0.33, 0.28], np.float32)
GREEN_S = np.array([0.45, 1.0, 0.65], np.float32)


def st(sid): return S[sid]['t0']
def en(sid): return S[sid]['t1']


# ------------------------------------------------------------------ 图表坐标
CX0, CX1, CYB, CYT = 150, 950, 1300, 520           # 图表区（x0, x1, 底, 顶）


def axes(F, a, ymax, years=30, label_every=10):
    V.line(F, [(CX0, CYB), (CX1 + 20, CYB)], V.DIM, 1.2, a * 0.8, 0)
    V.line(F, [(CX0, CYB), (CX0, CYT - 30)], V.DIM, 1.2, a * 0.6, 0)
    for y in range(0, years + 1, label_every):
        x = CX0 + (CX1 - CX0) * y / years
        V.line(F, [(x, CYB), (x, CYB + 10)], V.DIM, 1, a * 0.7, 0)
        put_text(F, f'{y}', x, CYB + 36, 24, 'mono', V.DIM, a * 0.9, 100, shadow=0)
    put_text(F, '年', CX1 + 44, CYB + 36, 24, 'sans', V.DIM, a * 0.9, 100, shadow=0)
    for v in (1, 5, 10, 15):
        if v > ymax: continue
        y = CYB - (CYB - CYT) * v / ymax
        V.dashed(F, (CX0, y), (CX1, y), V.DIM, 1, a * 0.25, 6, 10, 0)
        put_text(F, f'{v}×', CX0 - 40, y, 22, 'mono', V.DIM, a * 0.8, 100, shadow=0)


def to_xy(year, v, ymax, years=30):
    return CX0 + (CX1 - CX0) * year / years, CYB - (CYB - CYT) * v / ymax


def curve(F, fn, y0, y1, ymax, color, a, width=3.2, fill=True, n=200):
    """画 year∈[y0,y1] 的曲线，返回末端坐标"""
    if y1 <= y0 + 1e-3 or a <= 0.003: return to_xy(y0, fn(y0), ymax)
    ys = np.linspace(y0, y1, n)
    pts = np.array([to_xy(y, fn(y), ymax) for y in ys], np.float32)
    if fill:
        poly = np.vstack([pts, [[pts[-1, 0], CYB], [pts[0, 0], CYB]]])
        V.fill_poly(F, poly, color * 0.22, a, top=pts[:, 1].min(), bottom=CYB, grad=(1.0, 0.0))
    V.line(F, pts, color, width, a, 0.9)
    return pts[-1]


def comet(F, x, y, color, a, t):
    V.dot(F, x, y, 6, color * 1.4, a, 1.4)
    r = np.random.default_rng(int(t * 30))
    n = 14
    splat(F, (x + r.normal(0, 8, n) - r.uniform(0, 40, n)).astype(np.float32), (y + r.normal(0, 8, n)).astype(np.float32),
          np.full(n, 1.2, np.float32), color, a * 0.5)


# ------------------------------------------------------------------ G10：乘法 → 分叉 → 412 倍
def g10(F, t):
    seg = t3.seg('G10')
    # A01：乘法链
    a = win(t, st('A01') - 0.2, st('A02') + 0.2, 0.35, 0.5)
    if a > 0:
        V.slam(F, '×', W / 2, 600, 260, t, wt('A01', '乘法'), a)
        k0 = wt('A01', '每一年')
        n = int(clamp01((t - k0) / max(en('A01') - k0, 0.6)) * 6)
        prod = 1.1 ** n
        for i in range(6):
            ai = a * smooth((t - k0 - i * (en('A01') - k0) / 6) / 0.25)
            if ai <= 0: continue
            x = 160 + i * 152; y = 930
            V.bracket(F, x - 62, y - 50, x + 62, y + 50, GOLD, ai, L=14, width=1.3, plate=0.3)
            put_text(F, '×1.1', x, y, 38, 'mono', GOLD_HI, ai, 200, shadow=0)
        put_text(F, f'= {prod:.2f}', W / 2, 1080, 64, 'mono', WHITE, a * smooth((t - k0) / 0.4), 600, shadow=0.4, glow=0.15)
    # A02–A03：两条曲线
    a = win(t, st('A02') - 0.3, seg['t1'] + 0.3, 0.5, 0.5)
    if a > 0:
        ymax = 18.5
        axes(F, a, ymax)
        ku, kd = wt('A02', '每年多'), wt('A02', '每年少')
        yu = 30 * ease_io(clamp01((t - ku) / max(kd - ku - 0.2, 1.0)))
        yd = 30 * ease_io(clamp01((t - kd) / max(en('A02') - kd - 0.2, 1.0)))
        pu = curve(F, lambda y: 1.1 ** y, 0, max(yu, 1e-3), ymax, GOLD, a)
        pdn = curve(F, lambda y: 0.9 ** y, 0, max(yd, 1e-3), ymax, CYAN, a, width=2.6)
        if yu > 0.05:
            comet(F, pu[0], pu[1], GOLD_HI, a * (1 if yu < 30 else 0.6), t)
            put_text(F, f'{1.1 ** yu:.1f}×', pu[0] - 20, pu[1] - 50, 52 if yu >= 30 else 40, 'mono', GOLD_HI, a, 300, 'right', shadow=0.4, glow=0.2)
        if yd > 0.05:
            comet(F, pdn[0], pdn[1], CYAN, a * 0.8, t)
            put_text(F, f'{0.9 ** yd:.2f}×', pdn[0] - 10, pdn[1] - 40, 34, 'mono', CYAN, a, 300, 'right', shadow=0.4)
        put_text(F, '每年 +10%', 300, 600, 36, 'serif', GOLD, a * smooth((t - ku) / 0.4), 400, shadow=0.4)
        put_text(F, '每年 −10%', 300, 660, 36, 'serif', CYAN, a * smooth((t - kd) / 0.4), 400, shadow=0.4)
        # A03：相差四百多倍
        k3 = wt('A03', '四百多倍')
        if t > k3 - 0.3:
            g = ease_out(clamp01((t - k3 + 0.3) / 0.5))
            xb = CX1 + 30
            yt_, yb_ = to_xy(30, MATH['up'], ymax)[1], to_xy(30, MATH['down'], ymax)[1]
            V.line(F, [(xb, yt_), (xb + 16, yt_), (xb + 16, yt_ + (yb_ - yt_) * g), (xb, yt_ + (yb_ - yt_) * g)], WHITE, 2, a, 0.6)
            V.slam(F, f'≈ {MATH["ratio"]:.0f} 倍', W / 2 + 40, 470, 120, t, k3, a)
            if t - k3 < 1.2:
                V.line(F, _circle(W / 2 + 40, 470, 60 + 900 * ease_out((t - k3) / 1.2)), GOLD_HI, 3, a * (1 - (t - k3) / 1.2), 1.0, closed=True)
        footnote(F, '数学示意：固定年化收益率，不计税费与通胀。1.1³⁰ ≈ 17.45，0.9³⁰ ≈ 0.042', a * 0.9, y=1400, size=20)


def _circle(cx, cy, r, n=96):
    th = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.c_[cx + r * np.cos(th), cy + r * np.sin(th)]


# ------------------------------------------------------------------ G11：腰斩要翻倍 → 乘以零
CRASH_Y = 12.0


def g11(F, t):
    seg = t3.seg('G11')
    a = win(t, seg['t0'], st('A05') + 0.1, 0.5, 0.45)
    if a > 0:
        ymax = 9.0
        axes(F, a, ymax, years=30)
        kc = wt('A04', '亏掉一半'); kr = wt('A04', '翻一倍'); k7 = wt('A04', '七年多')
        # 上升段
        y_up = CRASH_Y * ease_io(clamp01((t - seg['t0'] - 0.3) / max(kc - seg['t0'] - 0.5, 0.8)))
        p = curve(F, lambda y: 1.1 ** y, 0, max(y_up, 1e-3), ymax, GOLD, a)
        top = 1.1 ** CRASH_Y
        if t < kc:
            comet(F, p[0], p[1], GOLD_HI, a, t)
        else:
            u = t - kc
            xc, yc_top = to_xy(CRASH_Y, top, ymax); _, yc_bot = to_xy(CRASH_Y, top / 2, ymax)
            g = ease_out(clamp01(u / 0.25))
            V.line(F, [(xc, yc_top), (xc, yc_top + (yc_bot - yc_top) * g)], RED_S, 4, a, 1.2)
            V.slam(F, '−50%', xc - 150, (yc_top + yc_bot) / 2 - 10, 84, t, kc, a, gold=False, color=RED_S)
            # 没中断的路径（虚线）
            ghost_end = CRASH_Y + 18 * clamp01((t - kr) / 2.5)
            if t > kr:
                yy = np.linspace(CRASH_Y, ghost_end, 60); yy = yy[1.1 ** yy <= ymax * 0.98]
                pts = np.array([to_xy(y, 1.1 ** y, ymax) for y in yy], np.float32).reshape(-1, 2)
                for i in range(0, len(pts) - 1, 2):
                    V.line(F, pts[i:i + 2], GOLD_HI * 0.6, 1.6, a * 0.7, 0.2)
                # 恢复段：从 top/2 开始每年 +10%，7.27 年回到原高度
                yr = CRASH_Y + 18 * clamp01((t - kr) / 2.5)
                yr = min(yr, CRASH_Y + math.log(ymax * 0.98 / (top / 2)) / math.log(1.1))
                q = curve(F, lambda y: top / 2 * 1.1 ** (y - CRASH_Y), CRASH_Y, max(yr, CRASH_Y + 1e-3), ymax, GOLD, a, fill=False)
                comet(F, q[0], q[1], GOLD_HI, a, t)
                put_text(F, '+100%', xc + 170, yc_bot + 70, 54, 'mono', GREEN_S, a * smooth((t - kr) / 0.3), 300, shadow=0.4, glow=0.2)
                # 回到原点所需时间
                if t > k7 - 0.2:
                    x7, _ = to_xy(CRASH_Y + MATH['recover_years'], top, ymax)
                    V.dashed(F, (xc, yc_top), (x7, yc_top), WHITE, 1.6, a * 0.8, 10, 8, 0.3)
                    V.slam(F, '7.3 年', (xc + x7) / 2, yc_top - 50, 56, t, k7, a, gold=False, color=WHITE, name='mono')
        footnote(F, '假设：腰斩后仍按每年 +10% 增长；回到原点需 ln2 / ln1.1 ≈ 7.27 年', a * 0.9, y=1400, size=20)
    # A05–A06：一长串 ×1.1，最后乘以一个零
    a = win(t, st('A05') - 0.2, seg['t1'] + 0.3, 0.45, 0.5)
    if a > 0:
        k5 = st('A05'); k0 = wt('A06', '乘以一个零'); kz = wt('A06', '全部蒸发')
        n_lit = int(clamp01((t - k5) / max(k0 - k5 - 0.3, 1.0)) * 30)
        prod = 1.1 ** n_lit
        zero = t > k0
        die = clamp01((t - kz) / 1.6)
        for i in range(31):
            row, col = divmod(i, 6)
            x = 150 + col * 156; y = 560 + row * 118
            if i < 30:
                lit = i < n_lit
                ai = a * (0.25 + 0.75 * lit) * (1 - die)
                if ai <= 0.01: continue
                dx = (np.sin(i * 12.9) * 0.5) * 600 * die ** 1.5; dy = -500 * die ** 1.5 * (0.5 + 0.5 * np.cos(i * 7.3))
                V.bracket(F, x - 62 + dx, y - 44 + dy, x + 62 + dx, y + 44 + dy, GOLD if lit else V.DIM, ai, L=12, width=1.2, plate=0.25 * lit)
                put_text(F, '×1.1', x + dx, y + dy, 34, 'mono', GOLD_HI if lit else V.DIM, ai, 200, shadow=0)
                if die > 0:
                    r = np.random.default_rng(i)
                    P = r.normal(0, 1, (40, 2)) * 26 * (1 + 4 * die)
                    splat(F, (x + dx + P[:, 0]).astype(np.float32), (y + dy + P[:, 1] - 200 * die).astype(np.float32),
                          np.full(40, 1.3, np.float32), GOLD_HI, a * 0.6 * (1 - die) * die * 4)
            elif zero:
                V.slam(F, '×0', x, y, 64, t, k0, a, gold=False, color=RED_S, name='mono')
        val = '0' if zero else f'{prod:.2f}'
        put_text(F, '= ' + val, W / 2, 470, 90, 'mono', RED_S if zero else WHITE, a, 800, shadow=0.4, glow=0.2 if not zero else 0.5)
        if t > kz - 0.2:
            qa = a * smooth((t - kz + 0.2) / 0.6)
            put_text(F, '"…any series of positive numbers, however impressive the numbers may be,', W / 2, 1250, 26, 'corm_sb', V.INK_T, qa, 980, shadow=0)
            put_text(F, 'evaporates when multiplied by a single zero."', W / 2, 1290, 26, 'corm_sb', V.INK_T, qa, 980, shadow=0)
            put_text(F, '—— 巴菲特，2010 年致股东信', W / 2, 1345, 24, 'sans', GOLD_SUB * 1.1, qa, 980, shadow=0)


# ------------------------------------------------------------------ G12：先冲过终点 → 暂时 vs 永久
def g12(F, t):
    seg = t3.seg('G12')
    a = win(t, seg['t0'], st('A08') - 0.05, 0.45, 0.4)
    if a > 0:
        # 透视赛道：两道光迹冲向终点线，红色一道半路失控熄灭，金色一道冲过终点
        hz = 420; vx = W / 2
        for k in (-1, -0.33, 0.33, 1):
            edge = abs(k) == 1
            if edge:
                V.line(F, [(vx + k * 40, hz), (vx + k * 520, 1330)], GOLD * 0.8, 2.0, a * 0.8, 0.8)
            else:
                ph = (t * 2.2) % 1.0                              # 车道虚线向镜头飞来，制造速度感
                for j in range(8):
                    z0 = (j + ph) / 8; z1 = min(z0 + 0.045, 1)
                    pa = (vx + k * (40 + 480 * z0 ** 1.6), hz + (1330 - hz) * z0 ** 1.6)
                    pb = (vx + k * (40 + 480 * z1 ** 1.6), hz + (1330 - hz) * z1 ** 1.6)
                    V.line(F, [pa, pb], V.DIM * 1.3, 2.0, a * 0.7 * z0, 0.2)
        fin_y = 760
        fl = clamp01((t - seg['t0']) / 0.8)
        for i in range(10):                          # 终点线（黑白格的发光短线）
            x = vx - 150 + i * 30
            V.line(F, [(x, fin_y), (x + 15, fin_y)], WHITE if i % 2 == 0 else GOLD_HI, 5, a * fl, 0.6)
        u = clamp01((t - st('A07') - 0.3) / 3.0)
        # 金色：从底部冲到终点线
        def lane(off, uu):
            z = 1 - uu                               # 1=近处（屏幕下方）
            y = fin_y + (1330 - fin_y) * z ** 1.6
            x = vx + off * (40 + 480 * ((y - hz) / (1330 - hz)))
            return x, y
        tr = [lane(0.25, max(u - d, 0)) for d in np.linspace(0, 0.25, 12)]
        V.line(F, tr, GOLD_HI, 6, a, 1.6)
        V.dot(F, *tr[0], 10, GOLD_HI, a, 1.6)
        ur = min(u, 0.55)
        crash = clamp01((u - 0.55) / 0.2)
        trr = [lane(-0.25 - 0.6 * crash * (1 - d * 3), max(ur - d, 0)) for d in np.linspace(0, 0.25, 12)]
        V.line(F, trr, RED_S, 6, a * (1 - crash), 1.6)
        if crash > 0:
            V.dot(F, *trr[0], 14 * (1 - crash) + 2, RED_S, a * (1 - crash), 1.5)
        if u >= 1:
            V.dot(F, lane(0.25, 1.0)[0], fin_y, 10, GOLD_HI, a * math.exp(-(t - st('A07') - 3.3) * 3), 1.2)
        put_text(F, '要想第一个冲过终点，', W / 2, 1060, 56, 'serif', WHITE, a * smooth((t - wt('A07', '要想')) / 0.4), 980, shadow=0.6)
        V.slam(F, '首先得冲过终点', W / 2, 1160, 84, t, wt('A07', '首先得'), a)
        put_text(F, '"To finish first, you must first finish."  —— 巴菲特引用的赛车格言（2010 年致股东信）', W / 2, 1250, 24, 'corm', V.DIM,
                 a * smooth((t - wt('A07', '首先得') - 0.4) / 0.5), 980, shadow=0)
    a = win(t, st('A08') - 0.2, seg['t1'] + 0.3, 0.4, 0.5)
    if a > 0:
        V.line(F, [(W / 2, 560), (W / 2, 1300)], V.DIM, 1, a * 0.5, 0)
        kl, kr = st('A08'), wt('A08', '永久的损失')
        # 左：暂时的下跌（下探后回升）
        xs = np.linspace(110, 490, 80); fr = np.linspace(0, 1, 80)
        yv = 1150 - 260 * fr + 220 * np.exp(-((fr - 0.45) / 0.12) ** 2)
        nl = max(2, int(80 * clamp01((t - kl) / 1.8)))
        V.line(F, np.c_[xs[:nl], yv[:nl]], CYAN, 3, a, 0.8)
        put_text(F, '暂时的下跌', 300, 640, 52, 'serif', CYAN, a * smooth((t - kl) / 0.4), 460, shadow=0.5)
        put_text(F, '可以等待', 300, 720, 38, 'serif_m', V.INK_T, a * smooth((t - wt('A08', '可以等待')) / 0.4), 460, shadow=0.5)
        # 右：永久的损失（断崖后一路走平）
        xs2 = np.linspace(590, 970, 80)
        yv2 = np.where(fr < 0.4, 1150 - 260 * fr, 1150 - 260 * 0.4 + 330 + 30 * (fr - 0.4))
        nr = max(2, int(80 * clamp01((t - kr) / 1.6)))
        V.line(F, np.c_[xs2[:nr], yv2[:nr]], RED_S, 3, a, 0.8)
        put_text(F, '永久的损失', 780, 640, 52, 'serif', RED_S, a * smooth((t - kr) / 0.4), 460, shadow=0.5)
        put_text(F, '改写结局', 780, 720, 38, 'serif_m', V.INK_T, a * smooth((t - wt('A08', '改写结局')) / 0.4), 460, shadow=0.5)


# ------------------------------------------------------------------ G13：知识、信任、技能、健康
LIFE = [('知识', np.array([0.55, 0.78, 1.0], np.float32)), ('信任', np.array([1.0, 0.72, 0.40], np.float32)),
        ('技能', np.array([0.40, 0.95, 0.85], np.float32)), ('健康', np.array([0.55, 0.98, 0.55], np.float32))]
_rl = np.random.default_rng(17)
RIB = _rl.uniform(0, 1, (4, 420, 2)).astype(np.float32)
CONV = (W / 2, 520)


def ribbons(F, t, a, grow, conv, gap_k=None):
    for i, (name, col) in enumerate(LIFE):
        x0 = 210 + i * 220
        ph = RIB[i, :, 0]; sp = RIB[i, :, 1]
        u = (ph + t * (0.10 + 0.06 * sp)) % 1.0              # 沿光带向上流动
        top = 1300 - 700 * grow
        y = 1300 - u * (1300 - top)
        hel = np.sin(u * 14 + t * 2 + i) * 26 * (1 - conv)
        x = x0 + hel
        # 汇聚：越往上越靠向汇聚点
        k = conv * (u ** 1.5)
        x = x * (1 - k) + CONV[0] * k; y = y * (1 - k) + CONV[1] * k
        al = a * 0.8 * (1 - u * 0.4)
        if gap_k is not None and i == 1:
            al = al * np.where(np.abs(u - 0.5) < 0.12 * gap_k, 0.0, 1.0)
        splat(F, x.astype(np.float32), y.astype(np.float32), np.full(len(u), 2.6, np.float32), col * 1.6, al.astype(np.float32))
        splat(F, (x + 6).astype(np.float32), y.astype(np.float32), np.full(len(u), 7.0, np.float32), col * 0.5, (al * 0.35).astype(np.float32))
        V.line(F, [(x0, 1300), (x0, 1300 - (1300 - top) * (1 - conv))], col, 2, a * 0.35 * (1 - conv), 0.8)
        put_text(F, name, x0, 1360, 40, 'serif', col * 1.1, a * (1 - conv), 300, shadow=0.5)


def g13(F, t):
    seg = t3.seg('G13')
    a = win(t, seg['t0'], seg['t1'] + 0.4, 0.5, 0.3)
    if a <= 0: return
    k9 = wt('A09', '不只适用于钱')
    grow = ease_out(clamp01((t - wt('A10', '知识')) / 2.5))
    # A09：一枚金币（金钱）分成四道光
    split = clamp01((t - k9 - 0.5) / 1.0)
    if split < 1:
        V.dot(F, W / 2, 900, 40 * (1 - split) + 4, GOLD_HI, a * (1 - split), 1.6)
        put_text(F, '金钱', W / 2, 990, 40, 'serif', GOLD, a * (1 - split) * smooth((t - seg['t0']) / 0.4), 300, shadow=0.4)
    put_text(F, '不只适用于钱', W / 2, 700, 64, 'serif', WHITE, a * win(t, k9 - 0.1, wt('A10', '知识') - 0.1, 0.4, 0.4), 980, shadow=0.5)
    kd = wt('A10', '中断')
    gap = clamp01((t - kd) / 0.3) * (1 - clamp01((t - kd - 1.2) / 0.5))
    conv = ease_io(clamp01((t - (seg['t1'] - 2.4)) / 2.2))
    if grow > 0:
        ribbons(F, t, a * grow, grow, conv, gap_k=gap if gap > 0 else None)
    ke = wt('A10', '共同的敌人')
    if t > ke - 0.2:
        aa = a * (1 - conv)
        put_text(F, '共同的敌人', W / 2, 480, 44, 'serif_m', V.INK_T, aa * smooth((t - ke) / 0.4), 980, shadow=0.5)
        put_text(F, '不是慢', W / 2 - 170, 570, 64, 'serif', V.DIM, aa * smooth((t - wt('A10', '不是慢')) / 0.4), 400, shadow=0.5)
        if t > kd - 0.1:
            V.slam(F, '而是中断', W / 2 + 140, 570, 76, t, kd - 0.1, aa, gold=False, color=RED_S)


# ------------------------------------------------------------------ 总结（落在配乐高潮重拍上）
def summary(F, t):
    seg = t3.seg('G14')
    u = t - seg['t0']
    a = win(t, seg['t0'], seg['t1'] + 0.6, 0.05, 0.6)
    if a <= 0: return
    F += np.float32(1.1 * math.exp(-u * 7)) * np.array([1.0, 0.9, 0.72], np.float32)        # 重拍闪白
    V.dot(F, *CONV, 60 * math.exp(-u * 2) + 6, GOLD_HI, a * math.exp(-u * 1.2), 2.0)
    if u < 1.6:
        V.line(F, _circle(W / 2, 860, 80 + 1300 * ease_out(u / 1.6)), GOLD_HI, 4, a * (1 - u / 1.6) ** 1.5, 1.2, closed=True)
    r = np.random.default_rng(5)
    n = 900
    ang = r.uniform(0, 2 * math.pi, n); sp = r.gamma(2, 260, n)
    d = (1 - math.exp(-u * 1.8)) / 1.8
    splat(F, (W / 2 + np.cos(ang) * sp * d).astype(np.float32), (860 + np.sin(ang) * sp * d * 1.3 - 40 * u).astype(np.float32),
          np.full(n, 1.5, np.float32), GOLD_HI, a * 0.7 * math.exp(-u * 0.6))
    gold_text(F, 'AI 越快，', W / 2, 700, 130, 'serif', a, clamp01(u / 0.35), glow=0.4 + 0.8 * math.exp(-u * 3), sweep=(u - 1.6) / 1.3)
    gold_text(F, '越要慢', W / 2, 870, 170, 'serif', a, clamp01(u / 0.35 * 1.4 - 0.4), glow=0.5 + 0.9 * math.exp(-u * 3), sweep=(u - 1.75) / 1.3)
    # 第二句随解说逐段出现：复利的秘密 → 不是更快 → 而是不失去（金色、最重）
    k1, k2, k3 = wt('A11', '复利的秘密'), wt('A11', '不是更快'), wt('A11', '而是不失去')
    put_text(F, '复利的秘密', W / 2, 1060, 54, 'serif_m', np.array([1.0, 0.93, 0.8]), a * smooth((t - k1 + 0.1) / 0.5), 900, glow=0.1)
    put_text(F, '不是更快', W / 2 - 200, 1170, 60, 'serif_m', V.DIM * 1.2, a * smooth((t - k2 + 0.1) / 0.5), 500, shadow=0.5)
    if t > k3 - 0.1:
        V.slam(F, '而是不失去', W / 2 + 170, 1170, 76, t, k3 - 0.1, a)
        if t - k3 < 1.0:
            V.line(F, _circle(W / 2 + 170, 1170, 40 + 600 * ease_out((t - k3) / 1.0)), GOLD_HI, 3, a * (1 - (t - k3)), 1.0, closed=True)


# ------------------------------------------------------------------ 品牌片尾（系列准则第 8 节）
LOGO_PX = 240
LOGO_CY = 760
_LOCK = None


def _lockup_text():
    """从官方 hud_lockup@4x.png 取「巴芒价值 / BUFFETT · MUNGER」文字部分（RGBA）"""
    global _LOCK
    if _LOCK is None:
        import json, os
        im = cv2.imread(os.path.join(BB.REPO, 'brand', 'hud_lockup@4x.png'), cv2.IMREAD_UNCHANGED)
        lay = json.load(open(os.path.join(BB.REPO, 'brand', 'hud_layout.json')))
        x0, y0, x1, y1 = lay['text_box']
        crop = im[y0:y1, x0:x1].astype(np.float32) / 255
        rgb = cv2.cvtColor(crop[..., :3], cv2.COLOR_BGR2RGB); al = crop[..., 3]
        _LOCK = (rgb, al)
    return _LOCK


def _paste(F, rgb, a, x0, y0, alpha):
    h, w = a.shape
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if X1 <= X0 or Y1 <= Y0 or alpha <= 0: return
    aa = (a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] * alpha)[..., None]
    reg = F[Y0:Y1, X0:X1]
    src = rgb[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] if rgb.ndim == 3 else rgb
    reg[:] = reg * (1 - aa) + aa * src


_PTS = {}


def _logo_pts(n=5200):
    if 'logo' not in _PTS:
        rgb, a = BB.load_logo(LOGO_PX)
        ys, xs = np.nonzero(a > 0.5)
        r = np.random.default_rng(2)
        idx = r.choice(len(xs), n, replace=len(xs) < n)
        pts = np.c_[xs[idx] + W / 2 - LOGO_PX / 2, ys[idx] + LOGO_CY - LOGO_PX / 2].astype(np.float32)
        cols = rgb[ys[idx], xs[idx]].astype(np.float32)
        src = mask_points('复利的秘密，不是更快，而是不失去', 48, 'serif_m', n, W / 2, 1110)
        _PTS['logo'] = (pts, cols, np.asarray(src, np.float32))
    return _PTS['logo']


def brand(F, t, beat=None):
    """深色 → 总结文字化为微粒沿 logo 透明通道汇聚 → logo 原图（240px，淡蓝光晕）→ 重拍上浮现官方字标 →
    整句品牌金渐变关注语 → 流光扫过 → 整体（含右上角角标，由 render3 处理）淡出"""
    seg = t3.seg('brand')
    u = t - seg['t0']
    beat = seg['t0'] + t3.BRAND_BEAT if beat is None else beat
    pts, cols, src = _logo_pts()
    conv = ease_io(clamp01((u - 0.1) / 1.9))
    fade_p = 1 - smooth((u - 1.9) / 0.6)
    if fade_p > 0:
        swirl = (1 - conv) * 0.9
        c, s_ = math.cos(swirl), math.sin(swirl)
        cen = np.array([W / 2, (1110 + LOGO_CY) / 2], np.float32)
        mid = (src - cen) @ np.array([[c, -s_], [s_, c]], np.float32) * (1 + 0.3 * math.sin(conv * math.pi)) + cen
        xy = mid * (1 - conv) + pts * conv
        colp = cols * conv + GOLD_HI * (1 - conv)
        splat(F, xy[:, 0].copy(), xy[:, 1].copy(), np.full(len(xy), 1.1 + 1.2 * (1 - conv), np.float32), colp * 1.2, 0.85 * fade_p)
    la = smooth((u - 1.6) / 0.8)
    if la > 0:
        rgb, a = BB.load_logo(LOGO_PX)
        x0, y0 = int(W / 2 - LOGO_PX / 2), int(LOGO_CY - LOGO_PX / 2)
        S_ = BB.SPEC
        g = blur(np.pad(a, 160), S_['glow_sigma'] * LOGO_PX / S_['logo_px']) * S_['glow_strength'] * 1.8
        reg = F[y0 - 160:y0 - 160 + g.shape[0], x0 - 160:x0 - 160 + g.shape[1]]
        reg += g[:reg.shape[0], :reg.shape[1], None] * (np.array(S_['glow_rgb'], np.float32) / 255) * la
        _paste(F, rgb, a, x0, y0, la)
    bt = t - beat
    if bt > -0.05:
        lrgb, lal = _lockup_text()
        sc = 0.62 * (1.0 + 0.05 * (1 - ease_out(clamp01(bt / 0.6))))
        w, h = int(lal.shape[1] * sc), int(lal.shape[0] * sc)
        r2 = cv2.resize(lrgb, (w, h), interpolation=cv2.INTER_AREA); a2 = cv2.resize(lal, (w, h), interpolation=cv2.INTER_AREA)
        ta = smooth((bt + 0.05) / 0.35)
        ty = LOGO_CY + LOGO_PX / 2 + 50
        sh = blur(np.pad(a2, 20), 6) * 0.6 * ta
        x1, y1 = int(W / 2 - w / 2), int(ty)
        reg = F[y1 - 20:y1 - 20 + sh.shape[0], x1 - 20:x1 - 20 + sh.shape[1]]
        reg *= (1 - sh[:reg.shape[0], :reg.shape[1], None])
        _paste(F, r2 * 1.05, a2, x1, y1, ta)
        F += np.float32(0.10 * math.exp(-max(bt, 0) * 8)) * np.array([1.0, 0.9, 0.7], np.float32) * (bt > 0)
        # 关注语：整句品牌金渐变 + 流光扫过
        sy = ty + h + 110
        sa = smooth((bt - 1.0) / 0.6)
        lay_ = np.zeros((1, 1, 3), np.float32)
        gold_text(F, '关注「巴芒价值」，传承大师智慧，领悟投资真谛', W / 2, sy, 44, 'serif', sa, clamp01((bt - 1.0) / 0.9),
                  glow=0.15, sweep=(bt - 2.3) / 1.4, maxw=1040)
        lt = ease_out(clamp01((bt - 0.7) / 0.9))
        if lt > 0:
            V.line(F, [(W / 2 - 300 * lt, sy - 70), (W / 2 + 300 * lt, sy - 70)], GOLD, 1.2, 0.8, 0.6)


def brand_fade(t):
    """整体淡出（含角标）：片尾最后 2 秒"""
    seg = t3.seg('brand')
    return 1 - smooth((t - (seg['t1'] - 2.2)) / 2.0)


SCENES = {'G10': (g10, 'neutral'), 'G11': (g11, 'red'), 'G12': (g12, 'neutral'), 'G13': (g13, 'warm')}
