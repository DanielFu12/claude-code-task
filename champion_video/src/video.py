"""《追涨十年》全部分镜。每个 sc_* 函数绘制一段时间内的画面；时间点全部来自 timeline.py（对齐配乐节拍）。

用法:
  python3 video.py frame <t> <out.png>          # 单帧预览
  python3 video.py sheet <t0> <t1> <n> <out.png> # 联系表
  python3 video.py chunk <f0> <f1> <out.mp4>     # 渲染帧区间（无声）
"""
import json, math, os, sys
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
from engine import *
from bg import Background
from timeline import *
from brand.brand import Hud, load_logo, SPEC as BRAND_SPEC, GOLD_STOPS, SUB_GOLD

STORY = json.load(open(os.path.join(HERE, 'story.json')))
BGR = Background()
HUD = Hud(scale=1.0, frame_w=W)
GOLD_GRAD = [(p, tuple(c / 255 for c in rgb)) for p, rgb in GOLD_STOPS]   # 品牌金（取自 brand/brand.py）
SUBGOLD = tuple(c / 255 for c in SUB_GOLD)


def fmt_pct(r, nd=1, sign=True):
    v = r * 100
    s = f'{abs(v):,.{nd}f}%'
    if not sign: return s
    return ('+' if v >= 0 else '−') + s


def fmt_wan(x):
    """资金（以 10 万为本金）→ ('xx.x', '万')"""
    v = x * 10
    if v >= 100: return f'{v:,.0f}', '万'
    if v >= 10: return f'{v:.1f}', '万'
    if v >= 1: return f'{v:.2f}', '万'
    return f'{v * 10000:,.0f}', '元'


def money(F, x, xr, y, size, col=INK, a=1.0, glow=0.2, anchor='r'):
    """右对齐（或居中）绘制『数字 + 万/元』，数字用 Inter，单位用思源黑体"""
    num, unit = fmt_wan(x)
    uw = text_w(unit, 'sans_bold', int(size * 0.6))
    nw = text_w(num, 'num', int(size))
    if anchor == 'm':
        xr = xr + (nw + uw + 6) / 2
    F.text(unit, xr, y + size * 0.08, size * 0.6, 'sans_bold', col, a, anchor='r')
    F.text(num, xr - uw - 6, y, size, 'num', col, a, anchor='r', glow=glow)


def ret_col(r):
    return UP if r >= 0 else DOWN


# ================================================================ scenes
def sc_hook(F, t):
    """0 – 19.3 s：热帖 → 两个震撼数字 → 真的吗？"""
    P = STORY['post']
    a_all = 1 - ramp(t, T_TITLE - 0.25, T_TITLE)
    # 心电式细光线
    p = ramp(t, 0.1, 1.6)
    if t < 5:
        w = 520 * eo(p)
        F.line((540 - w, 960), (540 + w, 960), US, 0.5 * (1 - ramp(t, 1.4, 2.4)), 2, glow=1.5)
    # 帖子卡片
    ca = env(t, 1.0, T_TITLE, 0.6, 0.3) * a_all
    lift = (1 - eo(ramp(t, 1.0, 1.9))) * 60
    up = eio(ramp(t, B(7), B(8))) * 0    # 卡片位置固定
    y0 = 300 + lift - up
    F.glass(70, y0, 1010, y0 + 470, 44, ca, tint=(0.5, 0.7, 1.0), spec=ramp(t, 1.2, 2.6))
    if ca > 0.01:
        F.circle((150, y0 + 82), 34, US, ca * 0.9, 3, glow=0.4)
        F.text('热', 150, y0 + 82, 34, 'sans_bold', US, ca)
        F.text('一条刷屏的投资热帖', 205, y0 + 66, 34, 'sans_bold', INK, ca, anchor='l')
        F.text('近期热门帖子 · 未注明数据来源与算法', 205, y0 + 108, 24, 'sans_reg', DIM, ca, anchor='l')
        lines = P['text_lines']
        n_all = sum(len(s) for s in lines)
        n = int(n_all * ramp(t, 1.6, 5.4))
        y = y0 + 200
        for s in lines:
            k = max(0, min(len(s), n)); n -= len(s)
            if k:
                F.text(s[:k], 120, y, 46, 'sans_med', INK, ca, anchor='l')
            if 0 < k < len(s) or (k == len(s) and n <= 0 and int(t * 2.5) % 2 == 0 and t < 6.5):
                tw = text_w(s[:k], 'sans_med', 46) if k else 0
                F.line((124 + tw, y - 25), (124 + tw, y + 25), US, ca, 3)
            y += 72
    # 两个数字
    for i, (lab, val, col, lane, tk) in enumerate([('美股 · 累计收益', P['us_claim'], UP, US, B(8)), ('A股 · 累计收益', P['cn_claim'], DOWN, CN, B(12))]):
        a = env(t, tk - 0.1, T_TITLE, 0.25, 0.3) * a_all * (1 - 0.8 * ramp(t, B(20), B(20) + 0.3))
        if a <= 0: continue
        yb = 980 + i * 300
        u = ramp(t, tk, tk + 1.6)
        v = val * eo5(u)
        F.text(lab, 540, yb - 105, 36, 'sans_med', lane, a, glow=0.3)
        sc = 1 + 0.35 * (1 - eo(ramp(t, tk, tk + 0.35)))
        s = fmt_pct(v, 1 if abs(val) < 10 else 0)
        F.text3d(s, 540, yb + 10, 150 * sc, 'num', face=[(0, lerpc(col, WHITE, 0.55)), (0.55, col), (1, mix(col, 0.6))],
                 side=mix(col, 0.22), depth=12, a=a, spec=ramp(t, tk + 0.3, tk + 1.3), glow=0.35)
        if t >= tk:
            F.blob((540, yb), 260, col, 0.35 * a * (1 - ramp(t, tk, tk + 1.2)) + 0.08 * a)
    # 天堂与地狱
    a = env(t, B(16), T_TITLE, 0.4, 0.3) * a_all * (1 - ramp(t, B(20), B(20) + 0.3))
    F.text_chars('同一个策略，十年后：天堂与地狱？', 540, 1640, 48, 'serif', INK, a, t0=B(16), stag=0.035)
    # 真的吗？
    a = env(t, B(20), T_TITLE, 0.15, 0.2)
    if a > 0:
        g = 1 - ramp(t, B(20), B(20) + 0.5)
        F.darken(np.ones((H, W), np.float32), 0, 0, 0.6 * a)
        F.text3d('真的吗？', 540 + (np.sin(t * 90) * 10 * g), 1420, 190, 'serif_black',
                 face=[(0, WHITE), (1, (0.75, 0.8, 0.9))], side=(0.05, 0.07, 0.12), depth=10, a=a, glow=0.2)
        F.text('我们用真实历史数据，把这场实验完整重做了一遍', 540, 1610, 34, 'sans_reg', INK, a * ramp(t, B(21), B(22)))
        F.ca = 6 * g


def sc_title(F, t):
    """19.31 s 重击：标题"""
    u = t - T_TITLE
    a = env(t, T_TITLE, T_RULES + 0.4, 0.05, 0.5)
    if a <= 0: return
    F.flash = 0.9 * math.exp(-u / 0.12) if u >= 0 else 0
    # 冲击波环
    for k, d in enumerate((0, 0.18)):
        uu = u - d
        if uu > 0:
            r = 80 + 1400 * eo(uu / 1.6)
            F.circle((540, 900), r, GOLD, a * 0.7 * (1 - ramp(uu, 0, 1.6)), 4, glow=1.0)
    sc = 1 + 0.25 * math.exp(-u / 0.25)
    F.text3d('追涨十年', 540, 860, 230 * sc, 'serif_black', face=GOLD_GRAD, side=(0.32, 0.18, 0.04), depth=16, a=a,
             glow=0.45, spec=ramp(u, 0.3, 1.8))
    F.text_chars('每年只买去年的涨幅冠军，', 540, 1060, 50, 'sans_bold', INK, a, t0=T_TITLE + 0.35, stag=0.03)
    F.text_chars('10 年后会怎样？', 540, 1135, 50, 'sans_bold', INK, a, t0=T_TITLE + 0.75, stag=0.04)
    w = 360 * eo(ramp(u, 0.9, 1.8))
    F.line((540 - w, 1215), (540 + w, 1215), GOLD, a * 0.7, 2, glow=0.6)
    F.text('美股 vs A股 · 2016—2025', 540, 1268, 34, 'sans_med', SUBGOLD, a * ramp(u, 1.2, 1.9))
    F.text('一场用真实数据重做的十年实验', 540, 1320, 30, 'sans_reg', DIM, a * ramp(u, 1.4, 2.1))
    F.zoom = 1 + 0.03 * math.exp(-u / 0.3)


def sc_rules(F, t):
    a = env(t, T_RULES, year_t0(0) + 0.05, 0.35, 0.3)
    if a <= 0: return
    F.text_chars('实验规则', 540, 300, 64, 'serif_black', GOLD, a, t0=T_RULES, stag=0.06)
    rules = STORY['rules']
    for i, (num, s1, s2) in enumerate(rules):
        tk = B(31 + i)
        ai = a * eo(ramp(t, tk, tk + 0.45))
        if ai <= 0: continue
        y = 470 + i * 170
        dx = (1 - eo(ramp(t, tk, tk + 0.5))) * 80
        F.glass(60 + dx, y - 70, 1020 + dx, y + 70, 32, ai, tint=(0.6, 0.7, 1.0), shadow=0.3, blur=14, spec=ramp(t, tk, tk + 0.9))
        F.text(num, 118 + dx, y, 56, 'num', GOLD, ai, glow=0.4)
        F.text(s1, 170 + dx, y - 22, 36, 'sans_bold', INK, ai, anchor='l')
        F.text(s2, 170 + dx, y + 28, 26, 'sans_reg', DIM, ai, anchor='l')
    # 股票池
    for j, (lab, l1, l2, col) in enumerate(STORY['universe']):
        tk = B(36) + j * 0.25
        ai = a * eo(ramp(t, tk, tk + 0.5))
        x0 = 60 + j * 490
        F.glass(x0, 1190, x0 + 470, 1440, 32, ai, tint=col, tint_a=0.10, shadow=0.3, blur=14)
        F.circle((x0 + 46, 1246), 10, col, ai, fill=True, glow=0.8)
        F.text(lab, x0 + 70, 1246, 40, 'sans_bold', col, ai, anchor='l')
        F.text(l1, x0 + 34, 1316, 31, 'sans_bold', INK, ai, anchor='l')
        for q, part in enumerate(l2.split('；')):
            F.text(part, x0 + 34, 1366 + q * 36, 24, 'sans_reg', DIM, ai, anchor='l')
    ai = a * eo(ramp(t, B(38), B(38) + 0.5))
    F.text('起点：两地各投入 10 万（本币）', 540, 1540, 38, 'sans_bold', GOLD_L, ai, glow=0.2)
    F.text('十年不加仓、不止损、不择时', 540, 1600, 30, 'sans_reg', DIM, ai)



# ================================================================ race
LANES = [dict(key='us', x0=40, x1=530, col=US, col2=US2, label='美股', sub='标普 500 冠军'),
         dict(key='cn', x0=550, x1=1040, col=CN, col2=CN2, label='A股', sub='沪深全市场冠军')]
FLOOR = 1700            # 塔基 = 本金线（10 万）
TK = 120                # 每 10 倍对应的塔高（像素）
YB4 = YEAR_BEATS // 2 * SPB       # 第 4 拍：收益揭晓（3.2 s）


def cap_at(lane, i, u):
    """第 i 年、年内时间 u 时的资金（相对 10 万的倍数）"""
    Y = STORY['years']
    d = Y[i].get(lane)
    if d is None: return 1.0
    prev = Y[i - 1][lane]['cap'] if i else 1.0
    path = d['path']
    p = ramp(u, 0.6, YB4)
    if p >= 1: return d['cap']
    k = p * (len(path) - 1)
    j = int(k); f = k - j
    v = path[j] * (1 - f) + path[min(j + 1, len(path) - 1)] * f
    return prev * v * (d['cap'] / prev) / path[-1] if path[-1] else prev * v


def tower_h(c):
    return TK * math.log10(max(c, 1e-4))


def draw_towers(F, t, a, i_now, u_now, xs=(285, 795), floor=FLOOR, label=True):
    Y = STORY['years']
    # 本金线
    F.line((60, floor), (1020, floor), GOLD, 0.55 * a, 2, glow=0.5)
    F.text('本金线 10 万', 70, floor + 26, 22, 'sans_reg', GOLD, 0.8 * a, anchor='l')
    for li, L in enumerate(LANES):
        if L['key'] not in Y[0]: continue
        c = cap_at(L['key'], i_now, u_now)
        h = tower_h(c)
        cx = xs[li]
        col = L['col']
        if h >= 0:
            F.prism(cx - 20, floor, 220, max(h, 2), 56, col, a, glow=0.35)
        else:
            F.prism(cx - 20, floor - h, 220, -h, 56, mix(DOWN, 0.9), a * 0.85, glow=0.3, crack=min(1, -h / 120), top_glow=0.4)
        # 年度刻度：每年末的位置
        for j in range(i_now + (1 if u_now >= YB4 else 0)):
            hj = tower_h(Y[j][L['key']]['cap'])
            F.line((cx - 130, floor - hj), (cx - 135, floor - hj), col, 0.5 * a, 2)
        if label:
            yy = floor - max(h, 0) - 60 if h >= 0 else floor + 70 - h
            F.text(f'×{c:,.2f}' if c < 10 else f'×{c:,.1f}', cx - 20, yy, 40, 'num', lerpc(col, WHITE, 0.3), a, glow=0.3)


def sc_race(F, t):
    i = int((t - year_t0(0)) // (YEAR_BEATS * SPB))
    i = max(0, min(9, i))
    u = t - year_t0(i)
    D = YEAR_BEATS * SPB
    Y = STORY['years']; yd = Y[i]
    a_sec = env(t, year_t0(0) - 0.05, T_RACE_END + 0.6, 0.3, 0.6)
    # 年份 + 进度
    ain = eo(ramp(u, 0, 0.35)) if i else eo(ramp(u, -0.2, 0.4))
    sc = 1 + 0.25 * math.exp(-max(u, 0) / 0.18)
    F.text3d(str(yd['year']), 540, 190, 118 * sc, 'num', face=[(0, WHITE), (1, (0.72, 0.78, 0.9))], side=(0.06, 0.08, 0.14),
             depth=8, a=a_sec * ain, glow=0.25)
    F.text(f'第 {i + 1} 年 / 共 10 年', 540, 275, 26, 'sans_reg', DIM, a_sec * ain)
    for j in range(10):
        x = 160 + j * 84
        done = j < i or (j == i and u >= YB4)
        F.line((x, 318), (x + 70, 318), GOLD if done else (FAINT if j > i else GOLD_D), a_sec * (1 if done else 0.6), 5 if j == i else 3,
               glow=0.6 if j == i else 0)
    for li, L in enumerate(LANES):
        d = yd.get(L['key'])
        if d is None: continue
        x0, x1, col = L['x0'], L['x1'], L['col']; cx = (x0 + x1) / 2
        # 卡片进出
        p_in = eo(ramp(u, 0.05 + li * 0.12, 0.55 + li * 0.12))
        p_out = eio(ramp(u, D - 0.45, D - 0.05)) if i < 9 else eio(ramp(t, T_RACE_END - 0.2, T_RACE_END + 0.4))
        a = a_sec * p_in * (1 - p_out)
        dy = (1 - p_in) * 40 - p_out * 30
        F.circle((x0 + 26, 372), 8, col, a_sec, fill=True, glow=0.8)
        F.text(L['label'], x0 + 44, 372, 34, 'sans_bold', col, a_sec, anchor='l')
        F.text(L['sub'], x1 - 6, 374, 22, 'sans_reg', DIM, a_sec, anchor='r')
        # 冠军卡
        F.glass(x0, 410 + dy, x1, 690 + dy, 34, a, tint=col, tint_a=0.08, blur=16, shadow=0.35, spec=ramp(u, 0.3, 1.2))
        code = d['code']
        F.text(code, x0 + 30, 456 + dy, 28, 'num_semi', DIM, a, anchor='l')
        F.text('上一年冠军', x1 - 26, 456 + dy, 22, 'sans_reg', GOLD, a, anchor='r')
        nm = d['name']
        fs = 54 if len(nm) <= 6 else (44 if len(nm) <= 9 else 36)
        F.text(nm, x0 + 30, 528 + dy, fs, 'sans_black', INK, a, anchor='l', glow=0.1)
        if L['key'] == 'us':
            F.text(d['en'], x0 + 30, 584 + dy, 24, 'num_reg', DIM, a, anchor='l')
        pv = d['prev']
        F.text('去年涨幅', x0 + 30, 640 + dy, 24, 'sans_reg', DIM, a, anchor='l')
        F.text(fmt_pct(pv), x1 - 26, 638 + dy, 46, 'num', UP, a, anchor='r', glow=0.45)
        # 当年走势
        cy0, cy1 = 760, 1000
        px0, px1 = x0 + 24, x1 - 24
        path = np.asarray(d['path'])
        lo, hi = min(path.min(), 1.0), max(path.max(), 1.0)
        span = max(hi - lo, 0.05)
        lo -= span * 0.08; hi += span * 0.08
        def yv(v): return cy1 - (v - lo) / (hi - lo) * (cy1 - cy0)
        ap = a_sec * env(u, 0.3, D, 0.3, 0.45) if i < 9 else a_sec * (1 - ramp(t, T_RACE_END - 0.2, T_RACE_END + 0.4)) * eo(ramp(u, 0.3, 0.6))
        y1 = yv(1.0)
        for xx in range(int(px0), int(px1), 18):
            F.line((xx, y1), (xx + 9, y1), DIM, 0.45 * ap, 1)
        F.text('买入价', px0, y1 - 16, 20, 'sans_reg', DIM, 0.8 * ap, anchor='l')
        pp = ramp(u, 0.6, YB4)
        n = max(2, int(len(path) * pp))
        xs = np.linspace(px0, px1, len(path))[:n]
        pts = list(zip(xs, [yv(v) for v in path[:n]]))
        cur = path[n - 1]
        lc = UP if cur >= 1 else DOWN
        F.area(pts, cy1 + 10, lc, 0.28 * ap)
        F.glow_line(pts, lc, ap, 4, glow=0.9)
        if pp < 1 and ap > 0:
            F.circle(pts[-1], 7, WHITE, ap, fill=True, glow=1.2)
            F.blob(pts[-1], 18, lc, ap * 0.8)
        # 月份刻度
        F.text('1月', px0, cy1 + 34, 20, 'sans_reg', DIM, 0.7 * ap, anchor='l')
        F.text('12月', px1, cy1 + 34, 20, 'sans_reg', DIM, 0.7 * ap, anchor='r')
        # 结果揭晓（第 4 拍）
        r = d['ret']
        ar = a_sec * eo(ramp(u, YB4 - 0.05, YB4 + 0.2)) * (1 - p_out)
        live = cur - 1
        if u < YB4:
            F.text(fmt_pct(live), cx, 1110, 64, 'num', lc, ap * 0.85, glow=0.3)
        else:
            s2 = 1 + 0.4 * math.exp(-(u - YB4) / 0.15)
            rc = ret_col(r)
            F.text3d(fmt_pct(r), cx, 1110, 92 * s2, 'num', face=[(0, lerpc(rc, WHITE, 0.6)), (0.55, rc), (1, mix(rc, 0.65))],
                     side=mix(rc, 0.22), depth=9, a=ar, glow=0.45, spec=ramp(u, YB4 + 0.1, YB4 + 1.1))
            if u < YB4 + 0.9:
                F.circle((cx, 1110), 60 + 260 * eo((u - YB4) / 0.9), rc, ar * (1 - (u - YB4) / 0.9), 3, glow=0.8)
        F.text('全年收益（扣成本）', cx, 1186, 22, 'sans_reg', DIM, a * 0.9)
        # 资金
        c = cap_at(L['key'], i, u)
        F.text('资金', x0 + 30, 1262, 26, 'sans_reg', DIM, a_sec, anchor='l')
        money(F, c, x1 - 26, 1258, 50, INK, a_sec)
        bk = yd.get(L['key'] + '_bench')
        if bk is not None:
            F.text(('同期标普500 ' if li == 0 else '同期沪深300 ') + fmt_pct(bk), cx, 1322, 22, 'sans_reg', DIM, a * 0.85)
        notes = d.get('notes') or []
        if notes and u > 0.6:
            F.text('⚠ ' + notes[0][:16], cx, 664 + dy + 50, 20, 'sans_reg', GOLD, a * 0.0)
    # 透视地面网格（塔基所在的「地面」）
    BGR.grid(F, t, US2, a=0.55 * a_sec, horizon=FLOOR, speed=0.5)
    # 每年重拍：一道横扫的光
    if u < 0.7:
        sx = -200 + 1500 * eo(u / 0.7)
        F.blob((sx, 190), 120, GOLD, 0.25 * a_sec * (1 - u / 0.7))
    draw_towers(F, t, a_sec, i, u)
    if u < 0.5 and i:
        F.zoom = 1 + 0.012 * math.exp(-u / 0.12)


# ================================================================ final：两条资金曲线对撞
def series(lane, bench=False):
    """把十年逐日净值拼成一条资金曲线：返回 (x∈[0,10], cap)"""
    xs, ys, prev = [0.0], [1.0], 1.0
    for i, y in enumerate(STORY['years']):
        if bench:
            path = y.get(lane + '_bench_path'); end = y.get(lane + '_bench_cap')
        else:
            d = y.get(lane)
            if d is None: return None
            path, end = d['path'], d['cap']
        if not path: return None
        path = np.asarray(path, float)
        scale = end / prev / path[-1]
        n = len(path)
        xs += list(i + (np.arange(1, n + 1) / n))
        ys += list(prev * path * scale)
        prev = end
    return np.asarray(xs), np.asarray(ys)


SER = {k: series(*k) for k in [('us', False), ('cn', False), ('us', True), ('cn', True)]}


def sc_final(F, t):
    a = env(t, T_FINAL - 0.2, T_BREAK + 0.4, 0.5, 0.5)
    if a <= 0: return
    F.text_chars('十年后，10 万变成了……', 540, 250, 58, 'serif_black', INK, a, t0=T_FINAL + 0.1, stag=0.05)
    gx0, gx1, gy0, gy1 = 140, 820, 420, 1280
    lo, hi = -2, 3          # log10 倍数：0.01 ~ 1000
    def X(x): return gx0 + x / 10 * (gx1 - gx0)
    def Yv(c): return gy1 - (math.log10(max(c, 10 ** lo)) - lo) / (hi - lo) * (gy1 - gy0)
    ga = a * eo(ramp(t, T_FINAL + 0.2, T_FINAL + 1.0))
    labels = {-2: '1000 元', -1: '1 万', 0: '10 万', 1: '100 万', 2: '1000 万', 3: '1 亿'}
    for k in range(lo, hi + 1):
        y = Yv(10 ** k)
        F.line((gx0, y), (gx1, y), GOLD if k == 0 else FAINT, ga * (0.7 if k == 0 else 0.45), 2 if k == 0 else 1, glow=0.4 if k == 0 else 0)
        F.text(labels[k], gx0 - 14, y, 22, 'sans_reg', GOLD if k == 0 else DIM, ga, anchor='r')
    for j in range(0, 11, 1):
        F.line((X(j), gy1), (X(j), gy1 + 8), DIM, ga * 0.6, 1)
        if j % 2 == 0 and j < 10:
            F.text(str(2016 + j), X(j + 0.5), gy1 + 34, 22, 'num_reg', DIM, ga)
    p = eio(ramp(t, B(121), B(129)))
    order = [(('us', True), WHITE, 0.55, 3, '标普500'), (('cn', True), (0.75, 0.75, 0.8), 0.45, 3, '沪深300'),
             (('us', False), US, 1.0, 5, '美股冠军策略'), (('cn', False), CN, 1.0, 5, 'A股冠军策略')]
    for key, col, al, th, name in order:
        sv = SER.get(key)
        if sv is None: continue
        xs, ys = sv
        n = max(2, int(len(xs) * p))
        step = max(1, n // 400)
        pts = [(X(x), Yv(c)) for x, c in zip(xs[:n:step], ys[:n:step])] + [(X(xs[n - 1]), Yv(ys[n - 1]))]
        if key[1]:
            F.poly(pts, col, a * al, th)
        else:
            F.area(pts, Yv(1.0), col, 0.18 * a)
            F.glow_line(pts, col, a, th, glow=1.0)
            if p < 1:
                F.circle(pts[-1], 8, WHITE, a, fill=True, glow=1.5)
        if p >= 1:
            la = a * eo(ramp(t, B(129), B(130)))
            yl = pts[-1][1]
            yl = {'美股冠军策略': min(yl, Yv(ys[-1])) , }.get(name, yl)
            F.circle(pts[-1], 6, col, la, fill=True, glow=1.0)
    # 终点标签
    la = a * eo(ramp(t, B(129), B(130)))
    tags = []
    for key, col, name in [(('us', False), US, '美股冠军'), (('us', True), WHITE, '标普500'), (('cn', True), (0.8, 0.8, 0.85), '沪深300'), (('cn', False), CN, 'A股冠军')]:
        sv = SER.get(key)
        if sv is None: continue
        tags.append([Yv(sv[1][-1]), col, name, sv[1][-1]])
    tags.sort()
    for k in range(1, len(tags)):            # 避免标签重叠
        if tags[k][0] - tags[k - 1][0] < 64: tags[k][0] = tags[k - 1][0] + 64
    for y, col, name, c in tags:
        num, unit = fmt_wan(c)
        F.text(f'{name} {num}{unit}', gx1 + 4, y, 24, 'sans_bold', col, la, anchor='r' if False else 'l') if False else None
        F.line((gx1 + 6, y), (gx1 + 22, y), col, la * 0.8, 2)
        F.text(name, gx1 + 30, y - 18, 22, 'sans_med', col, la, anchor='l')
        num, unit = fmt_wan(c)
        nw = text_w(num, 'num', 30)
        F.text(num, gx1 + 30, y + 14, 30, 'num', col, la, anchor='l', glow=0.3)
        F.text(unit, gx1 + 36 + nw, y + 16, 20, 'sans_bold', col, la, anchor='l')
    # 结果卡
    for j, (key, col, lab, bkey, bname) in enumerate([('us', US, '美股 · 冠军策略', 'us_bench_total', '标普500'), ('cn', CN, 'A股 · 冠军策略', 'cn_bench_total', '沪深300')]):
        tk = B(130) + j * 0.8
        ca = a * eo(ramp(t, tk, tk + 0.5))
        if ca <= 0 or key + '_total' not in STORY: continue
        x0 = 60 + j * 490; x1 = x0 + 470
        F.glass(x0, 1390, x1, 1760, 34, ca, tint=col, tint_a=0.10, spec=ramp(t, tk, tk + 1.0))
        tot = STORY[key + '_total']
        F.text(lab, (x0 + x1) / 2, 1440, 30, 'sans_bold', col, ca)
        money(F, tot, (x0 + x1) / 2, 1520, 76, INK, ca, glow=0.3, anchor='m')
        F.text(fmt_pct(tot - 1, 1 if abs(tot - 1) < 10 else 0), (x0 + x1) / 2, 1600, 46, 'num', ret_col(tot - 1), ca, glow=0.4)
        F.text('年化 ' + fmt_pct(tot ** 0.1 - 1), (x0 + x1) / 2, 1655, 30, 'sans_med', INK, ca)
        bt = STORY.get(bkey)
        if bt:
            num, unit = fmt_wan(bt)
            F.text(f'同期{bname}：{num}{unit}（年化 {fmt_pct(bt ** 0.1 - 1)}）', (x0 + x1) / 2, 1715, 22, 'sans_reg', DIM, ca)


def sc_break(F, t):
    a = env(t, T_BREAK, T_VERDICT + 0.05, 0.5, 0.05)
    if a <= 0: return
    F.darken(np.ones((H, W), np.float32), 0, 0, 0.75 * a)
    F.text_chars('等一下。', 540, 860, 80, 'serif_black', INK, a, t0=T_BREAK + 0.5, stag=0.12, dur=0.6)
    F.text_chars('热帖里的那两个数字，对得上吗？', 540, 1010, 46, 'serif', GOLD_L, a, t0=B(140), stag=0.06)


# ================================================================ verdict：推翻热帖
def sc_verdict(F, t):
    a = env(t, T_VERDICT - 0.05, T_WHY + 0.05, 0.05, 0.35)
    if a <= 0: return
    u = t - T_VERDICT
    F.flash = max(F.flash, 0.7 * math.exp(-u / 0.12)) if u >= 0 else F.flash
    P = STORY['post']
    # ---- 1) 热帖 vs 实测
    a1 = a * (1 - eio(ramp(t, B(151) - 0.2, B(151) + 0.2)))
    if a1 > 0:
        F.text3d('热帖 vs 真实回测', 540, 260, 84 * (1 + 0.2 * math.exp(-u / 0.2)), 'serif_black', face=GOLD_GRAD, side=(0.3, 0.17, 0.04), depth=8, a=a1, glow=0.35)
        rows = [('美股', US, P['us_claim'], STORY['us_total'] - 1, '标普 500 口径'),
                ('A股', CN, P['cn_claim'], STORY.get('cn_total', 1) - 1, '沪深全市场口径')]
        for j, (lab, col, claim, real, note) in enumerate(rows):
            tk = T_VERDICT + 0.25 + j * 0.8
            ra = a1 * eo(ramp(t, tk, tk + 0.4))
            y0 = 420 + j * 560
            F.glass(60, y0, 1020, y0 + 500, 40, ra, tint=col, tint_a=0.08, spec=ramp(t, tk, tk + 1))
            F.circle((112, y0 + 62), 10, col, ra, fill=True, glow=0.8)
            F.text(lab, 136, y0 + 62, 44, 'sans_black', col, ra, anchor='l')
            F.text(note, 990, y0 + 64, 24, 'sans_reg', DIM, ra, anchor='r')
            F.text('热帖', 290, y0 + 150, 32, 'sans_med', DIM, ra)
            F.text('实测', 790, y0 + 150, 32, 'sans_med', GOLD, ra)
            F.text(fmt_pct(claim, 1 if abs(claim) < 10 else 0), 290, y0 + 250, 78, 'num', mix(ret_col(claim), 0.75), ra)
            # 删除线
            sa = ra * eo(ramp(t, tk + 0.6, tk + 0.9))
            w = text_w(fmt_pct(claim, 1 if abs(claim) < 10 else 0), 'num', 78)
            F.line((290 - w / 2 - 10, y0 + 250), (290 - w / 2 - 10 + (w + 20) * eo(ramp(t, tk + 0.6, tk + 0.9)), y0 + 250), WHITE, sa, 6, glow=0.5)
            ra2 = ra * eo(ramp(t, tk + 0.4, tk + 0.8))
            F.text3d(fmt_pct(real, 1 if abs(real) < 10 else 0), 790, y0 + 250, 84, 'num', face=[(0, lerpc(ret_col(real), WHITE, 0.6)), (0.6, ret_col(real)), (1, mix(ret_col(real), 0.7))],
                     side=mix(ret_col(real), 0.25), depth=8, a=ra2, glow=0.45)
            F.line((540, y0 + 120), (540, y0 + 330), FAINT, ra, 1)
            F.text(f'{1 + claim:,.1f} 倍' if claim > 0 else f'剩 {(1 + claim) * 100:.1f}%', 290, y0 + 330, 28, 'sans_reg', DIM, ra)
            F.text(f'{1 + real:,.0f} 倍' if real > 1 else f'剩 {(1 + real) * 100:.1f}%', 790, y0 + 330, 28, 'sans_reg', INK, ra2)
            msg = STORY['verdict_msgs'][j]
            F.text(msg, 540, y0 + 420, 34, 'sans_bold', GOLD_L, ra2 * eo(ramp(t, tk + 0.9, tk + 1.3)), glow=0.2)
    # ---- 2) 可疑的巧合
    a2 = a * env(t, B(151), B(159) + 0.2, 0.35, 0.35)
    if a2 > 0:
        F.text_chars('一个可疑的巧合', 540, 300, 64, 'serif_black', GOLD, a2, t0=B(151), stag=0.06)
        F.glass(60, 420, 1020, 900, 40, a2, tint=US, tint_a=0.06)
        F.text('热帖：美股十年 +85,470%', 540, 500, 40, 'sans_bold', INK, a2)
        F.text('相当于连续十年，每年都要翻一倍左右：', 540, 570, 30, 'sans_reg', DIM, a2)
        F.text('年化', 300, 700, 50, 'sans_black', UP, a2 * eo(ramp(t, B(152), B(152) + 0.4)))
        F.text3d('+' + f"{P['us_claim_cagr'] * 100:.1f}%", 600, 700, 110, 'num', face=[(0, (1, 0.9, 0.9)), (0.6, UP), (1, mix(UP, 0.7))], side=mix(UP, 0.25), depth=8, a=a2 * eo(ramp(t, B(152), B(152) + 0.4)), glow=0.4)
        F.text('(1 + 854.70)^(1/10) - 1 = 96.4%', 540, 820, 28, 'mono', DIM, a2 * eo(ramp(t, B(152), B(153))))
        a3 = a2 * eo(ramp(t, B(154), B(154) + 0.4))
        F.glass(60, 960, 1020, 1300, 40, a3, tint=DOWN, tint_a=0.06)
        F.text('热帖：A股十年', 540, 1030, 40, 'sans_bold', INK, a3)
        F.text3d('−96.4%', 540, 1160, 110, 'num', face=[(0, (0.85, 1, 0.95)), (0.6, DOWN), (1, mix(DOWN, 0.7))], side=mix(DOWN, 0.25), depth=8, a=a3, glow=0.4)
        a4 = a2 * eo(ramp(t, B(156), B(156) + 0.4))
        for yy in (700, 1160):
            F.circle((835 if yy == 700 else 700, yy), 0, GOLD, 0)
        F.text_chars('同一个「96.4」，出现在两个结论里', 540, 1400, 42, 'serif', GOLD_L, a4, t0=B(156), stag=0.04)
        F.text('原帖没有给出数据来源与计算口径，我们无法复现它', 540, 1470, 28, 'sans_reg', INK, a4 * eo(ramp(t, B(157), B(158))))
        F.text('而真实回测的结果，与它都对不上', 540, 1520, 28, 'sans_reg', INK, a4 * eo(ramp(t, B(157), B(158))))
    # ---- 3) 稳健性：换个口径
    a5 = a * env(t, B(159), T_WHY + 0.3, 0.35, 0.4)
    if a5 > 0:
        F.text_chars('换个口径，结论会变吗？', 540, 270, 58, 'serif_black', GOLD, a5, t0=B(159), stag=0.05)
        for j, (lab, col, items) in enumerate(STORY['robust']):
            y0 = 380 + j * 690
            F.text(lab, 80, y0 + 20, 36, 'sans_black', col, a5, anchor='l')
            for k, (name, mult, hl) in enumerate(items):
                tk = B(160) + j * 1.0 + k * 0.18
                ia = a5 * eo(ramp(t, tk, tk + 0.4))
                y = y0 + 95 + k * 108
                F.text(name, 80, y, 28, 'sans_med', INK if hl else DIM, ia, anchor='l')
                v = math.log10(max(mult, 0.01))
                zero = 480
                L = v * 125 * eo(ramp(t, tk, tk + 0.8))
                cc = UP if v >= 0 else DOWN
                if hl: cc = col
                F.fill([(zero, y - 16), (zero + L, y - 16), (zero + L, y + 16), (zero, y + 16)] if L >= 0 else
                       [(zero + L, y - 16), (zero, y - 16), (zero, y + 16), (zero + L, y + 16)], cc, ia * 0.85, glow=0.3)
                F.text(fmt_pct(mult - 1, 0), (zero + L + 14) if L >= 0 else (zero + 14), y, 28, 'num', cc, ia, anchor='l')   # 负值标签放在零线右侧，避免压住左侧名称
            F.line((480, y0 + 50), (480, y0 + 95 + len(items) * 108 - 60), GOLD, a5 * 0.6, 2)
        F.text(STORY['robust_msg'], 540, 1790, 30, 'sans_bold', GOLD_L, a5 * eo(ramp(t, B(163), B(164))))


# ================================================================ why
def sc_why(F, t):
    a = env(t, T_WHY, T_STATEMENT + 0.1, 0.3, 0.4)
    if a <= 0: return
    panels = STORY['why']
    ts = [T_WHY, B(174), B(180), B(185), T_STATEMENT]
    for k, pnl in enumerate(panels):
        pa = a * env(t, ts[k] - 0.05, ts[k + 1] + 0.1, 0.35, 0.35)
        if pa <= 0: continue
        u = t - ts[k]
        F.text(f'0{k + 1}', 540, 250, 40, 'num', GOLD, pa, glow=0.4)
        F.text_chars(pnl['title'], 540, 330, 56, 'serif_black', INK, pa, t0=ts[k], stag=0.04)
        if pnl.get('sub'):
            F.text(pnl['sub'], 540, 405, 28, 'sans_reg', DIM, pa * eo(ramp(u, 0.4, 0.9)))
        WHY_DRAW[pnl['kind']](F, t, u, pa, pnl)


def why_twocol(F, t, u, a, p):
    for j, (lab, col, lines) in enumerate(p['cols']):
        x0 = 60 + j * 490; x1 = x0 + 470
        ca = a * eo(ramp(u, 0.3 + j * 0.3, 0.8 + j * 0.3))
        F.glass(x0, 490, x1, 1390, 36, ca, tint=col, tint_a=0.08)
        F.text(lab, (x0 + x1) / 2, 565, 42, 'sans_black', col, ca, glow=0.2)
        F.line((x0 + 40, 625), (x1 - 40, 625), col, ca * 0.4, 1)
        for q, ln in enumerate(lines):
            qa = ca * eo(ramp(u, 0.7 + j * 0.3 + q * 0.18, 1.1 + j * 0.3 + q * 0.18))
            y = 720 + q * 175
            if isinstance(ln, (list, tuple)):
                F.text(ln[0], x0 + 32, y - 22, 34, 'sans_bold', INK, qa, anchor='l')
                F.text(ln[1], x0 + 32, y + 28, 25, 'sans_reg', DIM, qa, anchor='l')
            else:
                F.text(ln, x0 + 34, y, 28, 'sans_med', INK, qa, anchor='l')
    if p.get('foot'):
        F.text(p['foot'], 540, 1500, 34, 'sans_bold', GOLD_L, a * eo(ramp(u, 2.2, 2.8)), glow=0.2)
    if p.get('foot2'):
        F.text(p['foot2'], 540, 1655, 26, 'sans_reg', DIM, a * eo(ramp(u, 3.0, 3.6)))


def why_bars(F, t, u, a, p):
    """冠军的次年：两地十年里每一年的冠军次年收益条形图"""
    for j, (lab, col, vals, bench) in enumerate(p['groups']):
        y0 = 520 + j * 600
        F.text(lab, 80, y0, 34, 'sans_black', col, a, anchor='l')
        F.line((80, y0 + 250), (1000, y0 + 250), FAINT, a, 1)
        for k, v in enumerate(vals):
            tk = 0.3 + j * 0.5 + k * 0.08
            ba = a * eo(ramp(u, tk, tk + 0.4))
            x = 110 + k * 90
            h = max(-1.0, min(v, 1.8)) * 120 * eo(ramp(u, tk, tk + 0.6))
            cc = ret_col(v)
            F.fill([(x, y0 + 250 - max(h, 0)), (x + 60, y0 + 250 - max(h, 0)), (x + 60, y0 + 250 - min(h, 0)), (x, y0 + 250 - min(h, 0))], cc, ba * 0.85, glow=0.3)
            F.text(f'{v * 100:+.0f}%', x + 30, y0 + 250 - h + (-24 if h >= 0 else 24), 20, 'num_semi', cc, ba)
            F.text(str(2016 + k)[2:], x + 30, y0 + 250 + (30 if h >= 0 else -30) if False else y0 + 420, 20, 'num_reg', DIM, ba)
            if bench is not None:
                bh = bench[k] * 120
                F.line((x - 4, y0 + 250 - bh), (x + 64, y0 + 250 - bh), WHITE, ba * 0.8, 2)
        F.text(p['notes'][j], 540, y0 + 480, 30, 'sans_bold', GOLD_L, a * eo(ramp(u, 1.6 + j * 0.4, 2.1 + j * 0.4)))
    F.text('白线 = 同期指数', 1000, 470, 22, 'sans_reg', DIM, a, anchor='r')


def why_loop(F, t, u, a, p):
    """FOMO 与反身性：上涨 → 关注 → 买入 → 再上涨 …… → 透支 → 回落"""
    cx, cy, R = 540, 900, 300
    nodes = p['nodes']
    n = len(nodes)
    rot = u * 0.35
    for k, lab in enumerate(nodes):
        ang = -math.pi / 2 + k / n * 2 * math.pi
        ka = a * eo(ramp(u, 0.3 + k * 0.25, 0.7 + k * 0.25))
        x, y = cx + R * math.cos(ang), cy + R * math.sin(ang)
        F.glass(x - 120, y - 46, x + 120, y + 46, 46, ka, tint=UP, tint_a=0.1, shadow=0.2, blur=10)
        F.text(lab, x, y, 32, 'sans_bold', INK, ka)
        a0, a1 = ang + 0.32, ang + 2 * math.pi / n - 0.32
        pts = [(cx + R * math.cos(q), cy + R * math.sin(q)) for q in np.linspace(a0, a1, 24)]
        F.poly(pts, UP, ka * 0.7, 3, glow=0.6)
    # 流动的光点
    q = -math.pi / 2 + (u * 1.4) % (2 * math.pi)
    F.blob((cx + R * math.cos(q), cy + R * math.sin(q)), 16, UP, a)
    F.text(p['center'], cx, cy, 40, 'serif_black', GOLD, a * eo(ramp(u, 1.2, 1.8)), glow=0.3)
    # 断裂
    ba = a * eo(ramp(u, 2.6, 3.0))
    F.text(p['break'], 540, 1340, 40, 'sans_black', DOWN, ba, glow=0.4)
    F.text(p['foot'], 540, 1420, 28, 'sans_reg', INK, ba)
    F.text(p['foot2'], 540, 1470, 28, 'sans_reg', INK, ba)


WHY_DRAW = dict(twocol=why_twocol, bars=why_bars, loop=why_loop)


# ================================================================ statement / value
def sc_statement(F, t):
    a = env(t, T_STATEMENT, T_VALUE + 0.2, 0.3, 0.4)
    if a <= 0: return
    F.darken(np.ones((H, W), np.float32), 0, 0, 0.6 * a)
    F.text_chars('过去涨得最多，', 540, 820, 82, 'serif_black', INK, a, t0=T_STATEMENT + 0.2, stag=0.09, dur=0.6)
    F.text_chars('不代表未来最值得买。', 540, 960, 82, 'serif_black', GOLD, a, t0=T_STATEMENT + 1.6, stag=0.09, dur=0.6, grad=GOLD_GRAD)
    w = 380 * eo(ramp(t, T_STATEMENT + 3.0, T_STATEMENT + 4.0))
    F.line((540 - w, 1080), (540 + w, 1080), GOLD, a * 0.7, 2, glow=0.6)


def sc_value(F, t):
    a = env(t, T_VALUE - 0.05, T_END + 0.3, 0.2, 0.5)
    if a <= 0: return
    u = t - T_VALUE
    F.flash = max(F.flash, 0.4 * math.exp(-u / 0.12)) if u >= 0 else F.flash
    # 巴菲特
    qa = a
    F.text('“', 120, 330, 160, 'serif_black', GOLD, qa * 0.6)
    F.text_chars('价格是你付出的，', 540, 430, 66, 'serif_black', INK, qa, t0=T_VALUE + 0.1, stag=0.05)
    F.text_chars('价值是你得到的。', 540, 530, 66, 'serif_black', GOLD_L, qa, t0=T_VALUE + 0.6, stag=0.05)
    F.text('—— 沃伦 · 巴菲特', 980, 620, 30, 'serif_med', SUBGOLD, qa * eo(ramp(u, 1.2, 1.7)), anchor='r')
    # 四个原则
    prin = STORY['principles']
    for k, (h, d) in enumerate(prin):
        tk = B(202) + k * 0.4
        pa = a * eo(ramp(t, tk, tk + 0.5))
        x0 = 60 + (k % 2) * 490; y0 = 720 + (k // 2) * 250
        F.glass(x0, y0, x0 + 470, y0 + 220, 34, pa, tint=GOLD, tint_a=0.07, spec=ramp(t, tk, tk + 1))
        F.text(h, x0 + 235, y0 + 75, 46, 'serif_black', GOLD, pa, glow=0.3)
        for q, ln in enumerate(d.split('\n')):
            F.text(ln, x0 + 235, y0 + 138 + q * 38, 27, 'sans_reg', INK, pa)
    # 最终启示
    fa = a * eo(ramp(t, B(206), B(206) + 0.6))
    lines = STORY['final_msg']
    for q, ln in enumerate(lines):
        F.text_chars(ln, 540, 1310 + q * 70, 40, 'serif', GOLD_L if q == len(lines) - 1 else INK, fa, t0=B(206) + q * 0.55, stag=0.03)
    F.text('数据：Yahoo Finance、腾讯证券、东方财富；回测脚本与明细见项目目录', 540, 1830, 20, 'sans_reg', FAINT, a * eo(ramp(u, 2, 3)))


# ================================================================ end card（品牌片尾）
LOGO_PX = 300
LOGO_RGB, LOGO_A = load_logo(LOGO_PX)          # 官方 logo（brand/logo_baman.png），透明通道
LOGO_Y = 720


def _logo_particles(n=9000):
    rng = np.random.default_rng(42)
    ys, xs = np.where(LOGO_A > 0.5)
    k = rng.choice(len(xs), n, replace=len(xs) < n)
    tx, ty = xs[k] + (540 - LOGO_PX / 2), ys[k] + (LOGO_Y - LOGO_PX / 2)
    col = LOGO_RGB[ys[k], xs[k]]
    ang = rng.uniform(0, 2 * np.pi, n); rad = 120 + rng.uniform(0, 1, n) ** 0.7 * 820
    sx, sy = 540 + np.cos(ang) * rad, LOGO_Y + np.sin(ang) * rad * 1.3
    delay = rng.uniform(0, 0.6, n)
    return tx, ty, sx, sy, col, delay, ang


LP = _logo_particles()


def sc_end(F, t):
    u = t - T_END
    a = ramp(t, T_END - 0.2, T_END + 0.4)
    F.darken(np.ones((H, W), np.float32), 0, 0, 0.5 * a)
    tx, ty, sx, sy, col, delay, ang = LP
    # 1) 粒子汇聚成 logo（以官方 logo 透明通道为遮罩采样）
    dur = T_LOGO - T_END
    p = np.clip((u - delay) / (dur - 0.6), 0, 1)
    e = p * p * (3 - 2 * p)
    swirl = (1 - e) * 1.6
    cxp, cyp = sx - 540, sy - LOGO_Y
    rx = cxp * np.cos(swirl) - cyp * np.sin(swirl); ry = cxp * np.sin(swirl) + cyp * np.cos(swirl)
    x = 540 + rx * (1 - e) + (tx - 540) * e
    y = LOGO_Y + ry * (1 - e) + (ty - LOGO_Y) * e
    pa = np.clip(u / 0.3, 0, 1) * (1 - np.clip((t - T_LOGO) / 0.45, 0, 1))
    if pa > 0:
        mixc = col * e[:, None] + np.array(GOLD) * (1 - e[:, None])
        # 运动拖尾：沿上一时刻位置画 4 个点
        for k, w in enumerate((1.0, 0.55, 0.3, 0.15)):
            if k:
                p2 = np.clip((u - k * 0.03 - delay) / (dur - 0.6), 0, 1); e2 = p2 * p2 * (3 - 2 * p2); sw2 = (1 - e2) * 1.6
                rx2 = cxp * np.cos(sw2) - cyp * np.sin(sw2); ry2 = cxp * np.sin(sw2) + cyp * np.cos(sw2)
                xx = 540 + rx2 * (1 - e2) + (tx - 540) * e2; yy = LOGO_Y + ry2 * (1 - e2) + (ty - LOGO_Y) * e2
            else:
                xx, yy = x, y
            ok = (xx >= 0) & (xx < W - 1) & (yy >= 0) & (yy < H - 1)      # 屏幕外的粒子直接丢弃
            dens = 0.55 - 0.3 * e[ok, None]                               # 汇聚时降低单粒子亮度，避免过曝
            for ox, oy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                idx = ((yy[ok] + oy).astype(int), (xx[ok] + ox).astype(int))
                np.add.at(F.img, idx, mixc[ok] * dens * pa * w)
                np.add.at(F.glow, idx, mixc[ok] * dens * 1.2 * pa * w)
    # 2) 清晰的官方 logo 居中浮现
    la = eo(ramp(t, T_LOGO - 0.15, T_LOGO + 0.5))
    if la > 0:
        sc = 1 + 0.06 * (1 - eo(ramp(t, T_LOGO - 0.15, T_LOGO + 1.2)))
        px = int(LOGO_PX * sc)
        rgb, al = load_logo(px) if px != LOGO_PX else (LOGO_RGB, LOGO_A)
        x0, y0 = 540 - px // 2, LOGO_Y - px // 2
        F.blob((540, LOGO_Y), 110, (110 / 255, 175 / 255, 1.0), 0.12 * la)   # 很淡的蓝色光晕（品牌规范）
        F.over(al, x0, y0, rgb, la)
        if t > T_LOGO:
            uu = t - T_LOGO
            F.circle((540, LOGO_Y), 170 + 420 * eo(uu / 1.4), (110 / 255, 175 / 255, 1.0), la * (1 - ramp(uu, 0, 1.4)) * 0.8, 3, glow=1.0)
            F.flash = 0.18 * math.exp(-uu / 0.1)
    # 3) 金色「巴芒价值」+ BUFFETT · MUNGER（随重拍出现，流光扫过）
    ga = eo(ramp(t, T_GOLD - 0.05, T_GOLD + 0.5))
    if ga > 0:
        sp = ramp(t, T_GOLD + 0.5, T_GOLD + 1.9)
        sc = 1 + 0.12 * (1 - eo(ramp(t, T_GOLD - 0.05, T_GOLD + 0.4)))
        tw = F.text3d('巴芒价值', 540, 1010, 128 * sc, 'serif_black', face=GOLD_GRAD, side=(0.3, 0.17, 0.04), depth=7, a=ga,
                      glow=0.4, spec=sp if 0 < sp < 1 else 0)
        sub = 'BUFFETT · MUNGER'
        fs = 34
        f = font('corm', fs)
        nat = sum(f.getlength(c) for c in sub)
        tw = text_w('巴芒价值', 'serif_black', 128)
        tr = (tw - nat) / (len(sub) - 1)
        x = 540 - tw / 2
        for c in sub:
            F.text(c, x, 1112, fs, 'corm', SUBGOLD, ga * eo(ramp(t, T_GOLD + 0.2, T_GOLD + 0.8)), anchor='l')
            x += f.getlength(c) + tr
    # 4) 细金线引出关注语
    la2 = ramp(t, T_FOLLOW, T_FOLLOW + 0.7)
    if la2 > 0:
        w = 330 * eo(la2)
        F.line((540 - w, 1205), (540 + w, 1205), GOLD, 0.8, 2, glow=0.8)
        F.blob((540 + w, 1205), 8, GOLD, 0.8 * (1 - la2))
        F.blob((540 - w, 1205), 8, GOLD, 0.8 * (1 - la2))
        F.text_chars('关注「巴芒价值」', 540, 1290, 44, 'serif', GOLD_L, 1.0, t0=T_FOLLOW + 0.35, stag=0.05)
        F.text_chars('传承大师智慧，领悟投资真谛', 540, 1370, 38, 'serif_med', INK, 1.0, t0=T_FOLLOW + 0.8, stag=0.05)


# ================================================================ frame
SCENES = [(0, T_TITLE + 0.1, sc_hook), (T_TITLE - 0.05, T_RULES + 0.5, sc_title), (T_RULES, year_t0(0) + 0.4, sc_rules),
          (year_t0(0) - 0.3, T_RACE_END + 0.7, sc_race), (T_FINAL - 0.3, T_BREAK + 0.5, sc_final),
          (T_BREAK - 0.1, T_VERDICT + 0.1, sc_break), (T_VERDICT - 0.1, T_WHY + 0.4, sc_verdict), (T_WHY - 0.2, T_STATEMENT + 0.2, sc_why),
          (T_STATEMENT - 0.1, T_VALUE + 0.3, sc_statement), (T_VALUE - 0.1, T_END + 0.4, sc_value), (T_END - 0.2, T_TOTAL + 1, sc_end)]


def bg_colors(t):
    if t < T_TITLE: return US2, (0.25, 0.1, 0.35)
    return US2, CN2


def render(t, idx=0):
    c1, c2 = bg_colors(t)
    base = BGR.nebula(t, c1, c2, amt=1.0)
    F = Frame(t, base)
    BGR.stars(F, t, speed=0.015, a=0.8, warp=max(0.0, 1 - abs(t - T_TITLE) / 0.6) * 1.5)
    for a, b, fn in SCENES:
        if a <= t < b:
            fn(F, t)
    out = finish(F, idx)
    HUD.draw(out, t)                     # 官方角标：全片保留（片尾淡出时随整体一起淡出）
    if t > T_FADE:
        out *= 1 - eio(ramp(t, T_FADE, T_TOTAL - 0.15))
    return out


def to8(img):
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'frame':
        t = float(sys.argv[2])
        cv2.imwrite(sys.argv[3], to8(render(t, int(t * FPS)))[..., ::-1])
    elif cmd == 'sheet':
        t0, t1, n = float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
        ts = np.linspace(t0, t1, n)
        ims = [cv2.resize(to8(render(t, int(t * FPS))), (270, 480), interpolation=cv2.INTER_AREA) for t in ts]
        for im, t in zip(ims, ts):
            cv2.putText(im, f'{t:.2f}', (6, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        cols = min(n, 6)
        rows = [np.hstack(ims[i:i + cols] + [np.zeros_like(ims[0])] * (cols - len(ims[i:i + cols]))) for i in range(0, n, cols)]
        cv2.imwrite(sys.argv[5], np.vstack(rows)[..., ::-1])
    elif cmd == 'chunk':
        import subprocess
        cv2.setNumThreads(1)
        f0, f1, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                              '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '8', '-threads', '2',
                              '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)   # 近无损中间文件，最终统一再编码
        for i in range(f0, f1):
            p.stdin.write(to8(render(i / FPS, i)).tobytes())
            if i % 60 == 0:
                print(out, i, flush=True)
        p.stdin.close(); p.wait()
