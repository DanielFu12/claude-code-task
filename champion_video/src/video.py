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
def two_tone(F, parts, x, y, size, fname, t0, a=1.0, stag=0.045, glow=0.0):
    """一行里不同颜色的几段文字，整体居中，逐字出现。parts=[(文字, 颜色或渐变), ...]"""
    total = sum(text_w(s, fname, int(size)) for s, _ in parts)
    cx = x - total / 2; k = 0
    for s, c in parts:
        grad = c if isinstance(c, list) else None
        F.text_chars(s, cx, y, size, fname, c if grad is None else WHITE, a, anchor='l', t0=t0 + k * stag, stag=stag,
                     glow=glow, grad=grad)
        cx += text_w(s, fname, int(size)); k += len(s)


def spin_number(t, seed):
    """账户余额「老虎机」：每帧随机跳动的数字"""
    rng = np.random.default_rng(int(t * FPS) * 7 + seed)
    v = 10 ** rng.uniform(-0.5, 3.4)
    return f'{v:,.1f}' if v < 100 else f'{v:,.0f}'


def sc_hook(F, t):
    """0 – 12.9 s：一个问题 + 两个账户 + 悬念"""
    a_all = 1 - ramp(t, T_TITLE - 0.25, T_TITLE)
    F.flash = max(F.flash, 0.12 * math.exp(-t / 0.15))
    # 1) 问题
    a1 = a_all * (1 - 0.35 * ramp(t, B(8) - 0.2, B(8) + 0.3))
    two_tone(F, [('每年第一个交易日', INK)], 540, 300, 62, 'serif_black', -0.3, a1)
    two_tone(F, [('买入上一年的', INK), ('涨幅冠军', GOLD_GRAD)], 540, 400, 62, 'serif_black', 0.75, a1, glow=0.25)
    if t > B(2) - 0.1:
        u = t - B(2)
        sc = 1 + 0.35 * math.exp(-max(u, 0) / 0.15)
        F.text3d('连续 10 年', 540, 545, 120 * sc, 'serif_black', face=GOLD_GRAD, side=(0.32, 0.18, 0.04), depth=10,
                 a=a1 * eo(ramp(u, -0.1, 0.25)), glow=0.4, spec=ramp(u, 0.3, 1.4))
    # 2) 两个账户：同样的 10 万本金，十年后的余额在「老虎机」里翻滚
    for j, (lab, col, sub) in enumerate([('美股账户', US, '标普500 冠军'), ('A股账户', CN, '沪深全市场冠军')]):
        tk = B(4) + j * 0.25
        ca = a_all * eo(ramp(t, tk, tk + 0.45))
        if ca <= 0: continue
        x0 = 60 + j * 490; x1 = x0 + 470
        dy = (1 - eo(ramp(t, tk, tk + 0.5))) * 60
        F.glass(x0, 700 + dy, x1, 1130 + dy, 36, ca, tint=col, tint_a=0.10, spec=ramp(t, tk, tk + 1.0))
        cx = (x0 + x1) / 2
        F.circle((x0 + 44, 760 + dy), 10, col, ca, fill=True, glow=0.8)
        F.text(lab, x0 + 66, 760 + dy, 40, 'sans_black', col, ca, anchor='l')
        F.text(sub, x0 + 36, 815 + dy, 24, 'sans_reg', DIM, ca, anchor='l')
        F.text('本金', x0 + 36, 880 + dy, 26, 'sans_reg', DIM, ca, anchor='l')
        F.text('10 万', x1 - 36, 880 + dy, 36, 'sans_bold', INK, ca, anchor='r')
        F.line((x0 + 36, 925 + dy), (x1 - 36, 925 + dy), col, ca * 0.35, 1)
        F.text('10 年后', x0 + 36, 975 + dy, 26, 'sans_reg', DIM, ca, anchor='l')
        spin = ramp(t, B(5), B(6))
        if spin > 0:
            num = spin_number(t, j)
            F.text(num, cx + 10, 1050 + dy, 72, 'num', lerpc(col, WHITE, 0.4), ca * spin, glow=0.4)
            F.text('万', cx + 10 + text_w(num, 'num', 72) / 2 + 30, 1060 + dy, 36, 'sans_bold', lerpc(col, WHITE, 0.4), ca * spin)
        # 余额后面的「?」
        F.text('?', x1 - 50, 975 + dy, 40, 'num', GOLD, ca * (0.5 + 0.5 * math.sin(t * 9)))
    # 3) 差多少？
    a3 = a_all * env(t, B(8) - 0.05, T_TITLE, 0.2, 0.3)
    if a3 > 0:
        sc = 1 + 0.3 * math.exp(-max(t - B(8), 0) / 0.15)
        F.text3d('两个账户，会差多少？', 540, 1290, 72 * sc, 'serif_black', face=[(0, WHITE), (1, (0.78, 0.84, 0.95))],
                 side=(0.05, 0.07, 0.12), depth=8, a=a3, glow=0.25)
    # 4) 悬念：差距超过 1000 倍
    a4 = a_all * env(t, B(12) - 0.05, T_TITLE, 0.15, 0.25)
    if a4 > 0:
        u = t - B(12)
        sc = 1 + 0.5 * math.exp(-max(u, 0) / 0.12)
        F.text('答案是：', 540, 1430, 40, 'sans_med', DIM, a4)
        F.text3d('相差超过 1,000 倍', 540, 1560, 104 * sc, 'serif_black', face=GOLD_GRAD, side=(0.32, 0.18, 0.04), depth=12,
                 a=a4, glow=0.5, spec=ramp(u, 0.2, 1.2))
        F.text_chars('谁赢了？为什么？', 540, 1700, 44, 'sans_bold', INK, a4, t0=B(14), stag=0.06)
        if u < 0.6:
            F.circle((540, 1560), 80 + 600 * eo(u / 0.6), GOLD, a4 * (1 - u / 0.6), 4, glow=1.0)
            F.zoom = 1 + 0.025 * math.exp(-u / 0.15)
            F.shake = (math.sin(u * 90) * 8 * math.exp(-u / 0.12), 0.0)


def sc_title(F, t):
    """12.91 s 重击：标题"""
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
    F.text('一场用真实数据完成的十年投资实验', 540, 1320, 30, 'sans_reg', DIM, a * ramp(u, 1.4, 2.1))
    F.zoom = 1 + 0.03 * math.exp(-u / 0.3)


def sc_rules(F, t):
    a = env(t, T_RULES, year_t0(0) + 0.05, 0.35, 0.3)
    if a <= 0: return
    F.text_chars('实验规则', 540, 300, 64, 'serif_black', GOLD, a, t0=T_RULES, stag=0.06)
    rules = STORY['rules']
    for i, (num, s1, s2) in enumerate(rules):
        tk = B(23 + i)
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
        tk = B(28) + j * 0.25
        ai = a * eo(ramp(t, tk, tk + 0.5))
        x0 = 60 + j * 490
        F.glass(x0, 1190, x0 + 470, 1440, 32, ai, tint=col, tint_a=0.10, shadow=0.3, blur=14)
        F.circle((x0 + 46, 1246), 10, col, ai, fill=True, glow=0.8)
        F.text(lab, x0 + 70, 1246, 40, 'sans_bold', col, ai, anchor='l')
        F.text(l1, x0 + 34, 1316, 31, 'sans_bold', INK, ai, anchor='l')
        for q, part in enumerate(l2.split('；')):
            F.text(part, x0 + 34, 1366 + q * 36, 24, 'sans_reg', DIM, ai, anchor='l')
    ai = a * eo(ramp(t, B(30), B(30) + 0.5))
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
    p = eio(ramp(t, B(113), B(121)))
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
            F.circle(pts[-1], 6, col, a * eo(ramp(t, B(121), B(122))), fill=True, glow=1.0)
    # 终点标签
    la = a * eo(ramp(t, B(121), B(122)))
    tags = []
    for key, col, name in [(('us', False), US, '美股冠军'), (('us', True), WHITE, '标普500'), (('cn', True), (0.8, 0.8, 0.85), '沪深300'), (('cn', False), CN, 'A股冠军')]:
        sv = SER.get(key)
        if sv is None: continue
        tags.append([Yv(sv[1][-1]), col, name, sv[1][-1]])
    tags.sort()
    for k in range(1, len(tags)):            # 避免标签重叠
        if tags[k][0] - tags[k - 1][0] < 64: tags[k][0] = tags[k - 1][0] + 64
    for y, col, name, c in tags:
        F.line((gx1 + 6, y), (gx1 + 22, y), col, la * 0.8, 2)
        F.text(name, gx1 + 30, y - 18, 22, 'sans_med', col, la, anchor='l')
        num, unit = fmt_wan(c)
        nw = text_w(num, 'num', 30)
        F.text(num, gx1 + 30, y + 14, 30, 'num', col, la, anchor='l', glow=0.3)
        F.text(unit, gx1 + 36 + nw, y + 16, 20, 'sans_bold', col, la, anchor='l')
    # 结果卡
    for j, (key, col, lab, bkey, bname) in enumerate([('us', US, '美股 · 冠军策略', 'us_bench_total', '标普500'), ('cn', CN, 'A股 · 冠军策略', 'cn_bench_total', '沪深300')]):
        tk = B(122) + j * 0.4
        ca = a * eo(ramp(t, tk, tk + 0.5))
        if ca <= 0 or key + '_total' not in STORY: continue
        x0 = 60 + j * 490; x1 = x0 + 470
        F.glass(x0, 1400, x1, 1730, 34, ca, tint=col, tint_a=0.10, spec=ramp(t, tk, tk + 1.0))
        tot = STORY[key + '_total']
        F.text(lab, (x0 + x1) / 2, 1445, 30, 'sans_bold', col, ca)
        money(F, tot, (x0 + x1) / 2, 1520, 76, INK, ca, glow=0.3, anchor='m')
        F.text(fmt_pct(tot - 1, 1 if abs(tot - 1) < 10 else 0), (x0 + x1) / 2, 1598, 46, 'num', ret_col(tot - 1), ca, glow=0.4)
        F.text('年化 ' + fmt_pct(tot ** 0.1 - 1), (x0 + x1) / 2, 1650, 30, 'sans_med', INK, ca)
        bt = STORY.get(bkey)
        if bt:
            num, unit = fmt_wan(bt)
            F.text(f'同期{bname}：{num}{unit}（年化 {fmt_pct(bt ** 0.1 - 1)}）', (x0 + x1) / 2, 1700, 22, 'sans_reg', DIM, ca)
    # 相差多少倍（重拍）
    ga2 = a * eo(ramp(t, B(123), B(123) + 0.3))
    if ga2 > 0:
        u = t - B(123)
        sc = 1 + 0.4 * math.exp(-max(u, 0) / 0.15)
        F.text3d(f"相差 {STORY['gap']:,.0f} 倍", 540, 1800, 64 * sc, 'serif_black', face=GOLD_GRAD, side=(0.3, 0.17, 0.04),
                 depth=7, a=ga2, glow=0.5, spec=ramp(u, 0.2, 1.2))


def sc_break(F, t):
    a = env(t, T_BREAK, T_WHY + 0.05, 0.5, 0.05)
    if a <= 0: return
    F.darken(np.ones((H, W), np.float32), 0, 0, 0.75 * a)
    F.text_chars('为什么差距这么大？', 540, 860, 76, 'serif_black', INK, a, t0=T_BREAK + 0.4, stag=0.08, dur=0.6)
    two_tone(F, [('答案，藏在「', DIM), ('冠军', GOLD_GRAD), ('」是怎么来的', DIM)], 540, 1000, 44, 'serif', B(132), a, stag=0.05)


# ================================================================ why：从第一性原理讲清差异
def sc_why(F, t):
    a = env(t, T_WHY - 0.05, T_STATEMENT + 0.1, 0.05, 0.4)
    if a <= 0: return
    if t >= T_WHY:
        F.flash = max(F.flash, 0.6 * math.exp(-(t - T_WHY) / 0.12))
    panels = STORY['why']
    ts = WHY_T + [T_STATEMENT]
    for k, pnl in enumerate(panels):
        pa = a * env(t, ts[k] - 0.05, ts[k + 1] + 0.05, 0.3, 0.3)
        if pa <= 0: continue
        u = t - ts[k]
        F.text(f'0{k + 1}', 540, 215, 38, 'num', GOLD, pa, glow=0.4)
        sc = 1 + 0.12 * math.exp(-max(u, 0) / 0.15)
        F.text_chars(pnl['title'], 540, 295, 54 * sc, 'serif_black', INK, pa, t0=ts[k], stag=0.035)
        if pnl.get('sub'):
            F.text(pnl['sub'], 540, 370, 28, 'sans_reg', DIM, pa * eo(ramp(u, 0.3, 0.8)))
        WHY_DRAW[pnl['kind']](F, t, u, pa, pnl)


def why_bars(F, t, u, a, p):
    """冠军的下一年：两地十年里每一年的冠军当年收益条形图（白线 = 同期指数）"""
    for j, (lab, col, vals, bench) in enumerate(p['groups']):
        y0 = 470 + j * 640
        F.text(lab, 80, y0, 36, 'sans_black', col, a, anchor='l')
        base = y0 + 260
        F.line((80, base), (1000, base), FAINT, a, 1)
        for k, v in enumerate(vals):
            tk = 0.25 + j * 0.45 + k * 0.07
            ba = a * eo(ramp(u, tk, tk + 0.35))
            x = 110 + k * 90
            h = max(-1.0, min(v, 1.8)) * 125 * eo(ramp(u, tk, tk + 0.55))
            cc = ret_col(v)
            F.fill([(x, base - max(h, 0)), (x + 60, base - max(h, 0)), (x + 60, base - min(h, 0)), (x, base - min(h, 0))], cc, ba * 0.85, glow=0.3)
            F.text(f'{v * 100:+.0f}%', x + 30, base - h + (-24 if h >= 0 else 24), 21, 'num_semi', cc, ba)
            F.text(str(2016 + k), x + 30, y0 + 440, 19, 'num_reg', DIM, ba)
            if bench is not None:
                bh = max(-1.0, min(bench[k], 1.8)) * 125
                F.line((x - 4, base - bh), (x + 64, base - bh), WHITE, ba * 0.85, 2)
        F.text(p['notes'][j], 540, y0 + 510, 34, 'sans_bold', GOLD_L, a * eo(ramp(u, 1.4 + j * 0.4, 1.9 + j * 0.4)), glow=0.2)
    F.text('白线 = 同期指数', 1000, 470, 22, 'sans_reg', DIM, a, anchor='r')


def why_principle(F, t, u, a, p):
    """股价 = 利润 × 估值；长期是称重机，短期是投票机"""
    # 公式：三个玻璃块依次落下
    items = [('股价', INK, 200), ('=', DIM, 0), ('利润', UP, 0), ('×', DIM, 0), ('估值', GOLD, 0)]
    xs = [170, 330, 520, 700, 880]
    for k, (s, c, _) in enumerate(items):
        tk = 0.2 + k * 0.18
        ia = a * eo(ramp(u, tk, tk + 0.35))
        dy = (1 - eback(ramp(u, tk, tk + 0.45))) * -60
        if s in ('=', '×'):
            F.text(s, xs[k], 520 + dy, 80, 'num', c, ia)
        else:
            F.glass(xs[k] - 120, 450 + dy, xs[k] + 120, 590 + dy, 30, ia, tint=c, tint_a=0.10, shadow=0.25, blur=12)
            F.text(s, xs[k], 520 + dy, 58, 'serif_black', c, ia, glow=0.3)
    F.text('每股利润', 520, 625, 24, 'sans_reg', DIM, a * eo(ramp(u, 0.7, 1.1)))
    F.text('市盈率', 880, 625, 24, 'sans_reg', DIM, a * eo(ramp(u, 0.9, 1.3)))
    F.text('估值 = 市场愿意为每 1 元利润支付多少钱', 540, 680, 26, 'sans_med', GOLD_L, a * eo(ramp(u, 1.0, 1.4)))
    # 两条曲线：长期（利润）平滑上行，短期（情绪）剧烈波动
    gx0, gx1 = 100, 980
    ca = a * eo(ramp(u, 1.3, 1.8))
    pp = eio(ramp(u, 1.3, 4.0))
    n = 220
    xx = np.linspace(0, 1, n)
    trend = 1180 - xx * 330
    noise = (np.sin(xx * 37) * 0.6 + np.sin(xx * 91 + 1) * 0.35 + np.sin(xx * 13 + 2) * 0.8) * 90 * (0.4 + 0.6 * np.sin(xx * 3.1) ** 2)
    m = max(2, int(n * pp))
    pts_t = [(gx0 + x * (gx1 - gx0), y) for x, y in zip(xx[:m], trend[:m])]
    pts_p = [(gx0 + x * (gx1 - gx0), y) for x, y in zip(xx[:m], (trend + noise)[:m])]
    PRICE = (0.62, 0.78, 1.0)
    F.glow_line(pts_p, PRICE, ca * 0.9, 3, glow=0.7)
    F.glow_line(pts_t, GOLD, ca, 5, glow=1.0)
    F.text('股价：短期围绕价值剧烈波动', gx0, 760, 26, 'sans_med', PRICE, ca, anchor='l')
    F.text('内在价值：随利润增长而上升', gx1, 1250, 26, 'sans_med', GOLD, ca, anchor='r')
    # 格雷厄姆
    qa = a * eo(ramp(u, 2.6, 3.1))
    F.glass(60, 1340, 1020, 1640, 36, qa, tint=GOLD, tint_a=0.06)
    F.text_chars('市场短期是投票机，长期是称重机。', 540, 1420, 44, 'serif_black', GOLD_L, qa, t0=2.6 + (t - u), stag=0.03)
    F.text('—— 本杰明 · 格雷厄姆（巴菲特的老师）', 990, 1490, 26, 'serif_med', SUBGOLD, qa, anchor='r')
    F.text('所以要问：冠军的涨幅，来自利润，还是来自情绪？', 540, 1580, 30, 'sans_bold', INK, qa * eo(ramp(u, 3.4, 3.9)))


def why_profit(F, t, u, a, p):
    """A 股冠军：股价涨幅 vs 利润变化（三类典型）"""
    y = 450; k = 0
    gcols = [GOLD, CN, UP]
    for g, (glab, rows) in enumerate(p['rows']):
        ga = a * eo(ramp(u, 0.2 + g * 0.9, 0.6 + g * 0.9))
        F.text(glab, 70, y, 28, 'sans_black', gcols[g] if g < 2 else (0.45, 0.9, 0.6), ga, anchor='l')
        y += 82
        for name, yr, price, desc, nxt in rows:
            ra = a * eo(ramp(u, 0.35 + g * 0.9 + k * 0.12, 0.75 + g * 0.9 + k * 0.12))
            F.glass(60, y - 46, 1020, y + 52, 26, ra, tint=(0.6, 0.7, 1.0), tint_a=0.05, shadow=0.15, blur=10)
            F.text(name, 90, y - 12, 32, 'sans_bold', INK, ra, anchor='l')
            F.text(f'{yr} 年股价 {fmt_pct(price, 0)}', 90, y + 26, 22, 'sans_reg', UP, ra, anchor='l')
            F.text(desc, 330, y + 6, 26, 'sans_med', INK, ra, anchor='l')
            F.text('次年', 870, y - 14, 20, 'sans_reg', DIM, ra)
            F.text(fmt_pct(nxt, 0), 930, y + 14, 40, 'num', ret_col(nxt), ra, anchor='r', glow=0.3)
            y += 112; k += 1
        y += 20
    fa = a * eo(ramp(u, 3.6, 4.1))
    F.text('价格跑在利润前面越远，回落就越狠', 540, 1720, 36, 'sans_black', GOLD_L, fa, glow=0.25)
    F.text('利润追上来，股价才站得住', 540, 1780, 28, 'sans_reg', INK, fa)


def why_ipo(F, t, u, a, p):
    """炒新：每年涨幅前 50 名中的新股数量 + 制度注解"""
    years, new = p['years'], p['new']
    base, top = 1150, 520
    for k, (yv, n) in enumerate(zip(years, new)):
        tk = 0.25 + k * 0.08
        ba = a * eo(ramp(u, tk, tk + 0.35))
        x = 105 + k * 90
        h = n / 50 * (base - top) * eo(ramp(u, tk, tk + 0.6))
        col = CN if yv < 2019 else lerpc(CN, US, min(1, (yv - 2018) / 5))
        F.fill([(x, base - h), (x + 62, base - h), (x + 62, base), (x, base)], col, ba * 0.85, glow=0.35)
        F.fill([(x, base - (base - top)), (x + 62, base - (base - top)), (x + 62, base), (x, base)], WHITE, ba * 0.04)
        F.text(str(n), x + 31, base - h - 26, 26, 'num', INK, ba)
        F.text(str(yv)[2:], x + 31, base + 28, 22, 'num_reg', DIM, ba)
    F.text('/50', 1010, top - 10, 22, 'num_reg', DIM, a, anchor='r')
    F.line((80, base), (1000, base), FAINT, a, 1)
    # 制度时间线
    ma = a * eo(ramp(u, 1.3, 1.8))
    for yv, lab, dy in [(2019, '2019 科创板注册制', 0), (2020, '2020 创业板注册制', 38), (2023, '2023 全面注册制', 0)]:
        k = years.index(yv); x = 105 + k * 90 + 31
        F.line((x, base + 48), (x, base + 72 + dy), US, ma, 2)
        F.text(lab, x, base + 96 + dy, 20, 'sans_med', US, ma)
    # 解释
    ea = a * eo(ramp(u, 2.0, 2.5))
    F.glass(60, 1330, 1020, 1640, 34, ea, tint=CN, tint_a=0.07)
    F.text('核准制时代：新股发行价被压在约 23 倍市盈率，', 90, 1385, 28, 'sans_med', INK, ea, anchor='l')
    F.text('首日涨幅又封顶 44%，上市后往往连续一字涨停', 90, 1430, 28, 'sans_med', INK, ea, anchor='l')
    F.text('稀缺 + 连板，让新股天然霸占涨幅榜', 90, 1490, 30, 'sans_black', GOLD_L, ea, anchor='l')
    F.text(f"十年平均：前 50 名里 {p['share'] * 100:.0f}% 是当年新股", 90, 1545, 26, 'sans_reg', DIM, ea, anchor='l')
    F.text('注册制推行后，新股占比明显下降', 90, 1590, 26, 'sans_reg', DIM, ea, anchor='l')
    fa = a * eo(ramp(u, 3.4, 3.9))
    F.text(f"而这些「涨幅王」的下一年：10 年中 {p['worse']} 年跑输全市场", 540, 1720, 32, 'sans_bold', DOWN, fa, glow=0.25)


def why_players(F, t, u, a, p):
    """参与者与制度 → 动量 vs 反转"""
    cols = [('A股', CN, [('61%', '个人投资者交易占比', '2022 年前三季度，监管数据'),
                         ('≈90%', '散户持仓不足 25%，交易却近九成', '2014–15 年上交所账户研究')],
             ['涨跌停 10% / 20%', '小盘股多，资金易推动', '情绪更容易走向极端']),
            ('美股', US, [('机构', '定价以机构投资者为主', '有做空机制约束高估'),
                          ('盈利', '标普500 入选要求持续盈利', '冠军多是行业龙头')],
             ['涨跌幅不设限', '大盘股为主', '价格更快反映基本面'])]
    for j, (lab, col, stats, chips) in enumerate(cols):
        x0 = 60 + j * 490; x1 = x0 + 470
        ca = a * eo(ramp(u, 0.25 + j * 0.3, 0.7 + j * 0.3))
        F.glass(x0, 430, x1, 1150, 34, ca, tint=col, tint_a=0.08)
        F.text(lab, (x0 + x1) / 2, 490, 40, 'sans_black', col, ca, glow=0.2)
        for q, (big, l1, l2) in enumerate(stats):
            y = 600 + q * 200
            qa = ca * eo(ramp(u, 0.6 + j * 0.3 + q * 0.25, 1.0 + j * 0.3 + q * 0.25))
            F.text(big, (x0 + x1) / 2, y, 72 if len(big) <= 3 else 60, 'num' if big[0] in '0123456789≈' else 'sans_black', lerpc(col, WHITE, 0.3), qa, glow=0.35)
            F.text(l1, (x0 + x1) / 2, y + 62, 24, 'sans_med', INK, qa)
            F.text(l2, (x0 + x1) / 2, y + 96, 19, 'sans_reg', DIM, qa)
        for q, c in enumerate(chips):
            qa = ca * eo(ramp(u, 1.2 + q * 0.15, 1.6 + q * 0.15))
            F.text('· ' + c, x0 + 40, 1005 + q * 44, 24, 'sans_reg', INK, qa, anchor='l')
    # 动量 vs 反转：前 10 名涨幅股的下一年超额收益
    ba = a * eo(ramp(u, 2.2, 2.6))
    F.text('上一年涨幅前 10 名，下一年相对全市场的超额收益（十年平均）', 540, 1230, 25, 'sans_med', DIM, ba)
    zero = 540
    for j, (lab, v, col, tag) in enumerate([('美股', p['us_top10'], US, '动量：强者恒强'), ('A股', p['cn_top10'], CN, '反转：物极必反')]):
        y = 1320 + j * 110
        L = v * 2400 * eo(ramp(u, 2.4 + j * 0.3, 3.0 + j * 0.3))
        F.text(lab, 90, y, 32, 'sans_black', col, ba, anchor='l')
        F.fill([(zero, y - 26), (zero + L, y - 26), (zero + L, y + 26), (zero, y + 26)] if L >= 0 else
               [(zero + L, y - 26), (zero, y - 26), (zero, y + 26), (zero + L, y + 26)], ret_col(v), ba * 0.85, glow=0.35)
        F.text(fmt_pct(v), zero + L + (16 if L >= 0 else -16), y, 34, 'num', ret_col(v), ba, anchor='l' if L >= 0 else 'r')
        F.text(tag, 990 if L < 0 else 240, y, 26, 'sans_bold', col, ba * eo(ramp(u, 3.0 + j * 0.3, 3.4 + j * 0.3)), anchor='r' if L < 0 else 'l')
    F.line((zero, 1280), (zero, 1480), GOLD, ba * 0.6, 2)
    fa = a * eo(ramp(u, 3.8, 4.3))
    F.text('散户主导 + 涨跌停 + 小盘题材 → 暴涨之后更容易均值回归', 540, 1580, 28, 'sans_bold', GOLD_L, fa, glow=0.2)


def why_loop(F, t, u, a, p):
    """FOMO 与反身性：上涨 → 关注 → 买入 → 再上涨 …… → 透支 → 回落"""
    cx, cy, R = 540, 820, 300
    nodes = p['nodes']
    n = len(nodes)
    brk = eo(ramp(u, 3.0, 3.6))
    for k, lab in enumerate(nodes):
        ang = -math.pi / 2 + k / n * 2 * math.pi
        ka = a * eo(ramp(u, 0.3 + k * 0.25, 0.7 + k * 0.25))
        x, y = cx + R * math.cos(ang), cy + R * math.sin(ang)
        if k == 0 and brk > 0:        # 断裂：最上面的节点下坠变绿
            y += brk * 120; x += math.sin(u * 40) * 6 * (1 - brk)
        F.glass(x - 120, y - 46, x + 120, y + 46, 46, ka, tint=UP if not (k == 0 and brk > 0.5) else DOWN, tint_a=0.1, shadow=0.2, blur=10)
        F.text(lab, x, y, 32, 'sans_bold', INK, ka)
        a0, a1 = ang + 0.32, ang + 2 * math.pi / n - 0.32
        pts = [(cx + R * math.cos(q), cy + R * math.sin(q)) for q in np.linspace(a0, a1, 24)]
        F.poly(pts, UP if brk < 0.5 or k > 0 else DOWN, ka * 0.7 * (1 - 0.6 * brk if k == n - 1 else 1), 3, glow=0.6)
    q = -math.pi / 2 + (u * 1.6) % (2 * math.pi)
    F.blob((cx + R * math.cos(q), cy + R * math.sin(q)), 16, UP, a * (1 - brk))
    F.text(p['center'], cx, cy, 40, 'serif_black', GOLD, a * eo(ramp(u, 1.2, 1.8)), glow=0.3)
    ba = a * brk
    F.text(p['break'], 540, 1260, 42, 'sans_black', DOWN, ba, glow=0.4)
    F.text(p['foot'], 540, 1340, 28, 'sans_reg', INK, ba)
    fa = a * eo(ramp(u, 4.0, 4.6))
    F.glass(60, 1430, 1020, 1560, 30, fa, tint=US, tint_a=0.06)
    F.text(p['foot2'], 540, 1495, 27, 'sans_med', US, fa)


WHY_DRAW = dict(bars=why_bars, principle=why_principle, profit=why_profit, ipo=why_ipo, players=why_players, loop=why_loop)


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
    a = env(t, T_VALUE - 0.05, T_END + 0.6, 0.2, 0.7)
    if a <= 0: return
    u = t - T_VALUE
    if u >= 0:
        F.flash = max(F.flash, 0.12 * math.exp(-u / 0.10))
    # ---- 1) 同一个市场，换一种方法
    a1 = a * (1 - eio(ramp(t, T_QUOTE - 0.3, T_QUOTE + 0.1)))
    if a1 > 0:
        F.text_chars('同一个市场，', 540, 300, 58, 'serif_black', INK, a1, t0=T_VALUE + 0.05, stag=0.04)
        two_tone(F, [('换一种方法，', INK), ('结果天差地别', GOLD_GRAD)], 540, 385, 58, 'serif_black', T_VALUE + 0.4, a1, stag=0.04, glow=0.25)
        for j, (lab, col, items) in enumerate(STORY['value_cmp']):
            y0 = 540 + j * 400
            F.glass(60, y0 - 50, 1020, y0 + 300, 34, a1 * eo(ramp(t, T_VALUE + 0.5 + j * 0.4, T_VALUE + 0.9 + j * 0.4)), tint=col, tint_a=0.07)
            F.text(lab, 100, y0 + 5, 40, 'sans_black', col, a1, anchor='l')
            for k, (name, mult, hl) in enumerate(items):
                tk = T_VALUE + 0.6 + j * 0.5 + k * 0.2
                ia = a1 * eo(ramp(t, tk, tk + 0.4))
                y = y0 + 110 + k * 120
                F.text(name, 100, y - 36, 28, 'sans_med', INK if hl else GOLD_L, ia, anchor='l')
                v = math.log10(max(mult, 0.01))
                zero = 400
                L = v * 150 * eo(ramp(t, tk, tk + 0.7))
                cc = (col if hl else GOLD) if v >= 0 else DOWN
                F.fill([(zero, y - 4), (zero + L, y - 4), (zero + L, y + 34), (zero, y + 34)] if L >= 0 else
                       [(zero + L, y - 4), (zero, y - 4), (zero, y + 34), (zero + L, y + 34)], cc, ia * 0.85, glow=0.35)
                F.text(fmt_pct(mult - 1, 0), (zero + L + 18) if L >= 0 else (zero + 18), y + 15, 40, 'num', ret_col(mult - 1), ia, anchor='l', glow=0.3)
            F.line((400, y0 + 60), (400, y0 + 270), GOLD, a1 * 0.5, 2)
        ma = a1 * eo(ramp(t, T_VALUE + 2.6, T_VALUE + 3.1))
        F.text('利润支撑的上涨会延续，情绪推动的上涨终会回落', 540, 1400, 34, 'sans_black', GOLD_L, ma, glow=0.25)
        F.text('A股同样奖励价值：寒武纪利润兑现的那一年，股价 +107%', 540, 1470, 28, 'sans_reg', INK, ma * eo(ramp(t, T_VALUE + 3.3, T_VALUE + 3.8)))
        F.text('长期持有沪深300（含分红），十年也有 +56%', 540, 1520, 28, 'sans_reg', INK, ma * eo(ramp(t, T_VALUE + 3.6, T_VALUE + 4.1)))
    # ---- 2) 巴菲特 + 芒格（重复的尾段重拍）
    a2 = a * eo(ramp(t, T_QUOTE, T_QUOTE + 0.3))
    if a2 > 0:
        uq = t - T_QUOTE
        F.text('“', 110, 250, 150, 'serif_black', GOLD, a2 * 0.6)
        F.text_chars('价格是你付出的，', 540, 320, 64, 'serif_black', INK, a2, t0=T_QUOTE + 0.05, stag=0.045)
        F.text_chars('价值是你得到的。', 540, 415, 64, 'serif_black', GOLD_L, a2, t0=T_QUOTE + 0.5, stag=0.045)
        F.text('—— 沃伦 · 巴菲特', 980, 495, 28, 'serif_med', SUBGOLD, a2 * eo(ramp(uq, 1.0, 1.5)), anchor='r')
        ma = a2 * eo(ramp(uq, 1.8, 2.3))
        F.glass(60, 560, 1020, 700, 30, ma, tint=GOLD, tint_a=0.05, shadow=0.2)
        F.text('反过来想，总是反过来想。—— 查理 · 芒格', 540, 610, 32, 'serif', GOLD_L, ma)
        F.text('先想清楚怎样会亏大钱：在狂热中追高，就是其中之一', 540, 660, 25, 'sans_reg', INK, ma)
    # ---- 3) 四个原则 + 最终启示
    prin = STORY['principles']
    for k, (hh, d) in enumerate(prin):
        tk = T_PRIN + k * 0.3
        pa = a * eo(ramp(t, tk, tk + 0.45))
        if pa <= 0: continue
        x0 = 60 + (k % 2) * 490; y0 = 760 + (k // 2) * 240
        F.glass(x0, y0, x0 + 470, y0 + 215, 34, pa, tint=GOLD, tint_a=0.07, spec=ramp(t, tk, tk + 1))
        F.text(hh, x0 + 235, y0 + 70, 46, 'serif_black', GOLD, pa, glow=0.3)
        for q, ln in enumerate(d.split('\n')):
            F.text(ln, x0 + 235, y0 + 135 + q * 38, 27, 'sans_reg', INK, pa)
    fa = a * eo(ramp(t, B(208), B(208) + 0.5))
    lines = STORY['final_msg']
    for q, ln in enumerate(lines):
        F.text_chars(ln, 540, 1340 + q * 72, 42, 'serif', GOLD_L if q == len(lines) - 1 else INK, fa, t0=B(208) + q * 0.55, stag=0.03)
    ia = a * eo(ramp(t, B(211), B(211) + 0.5))
    F.text3d('独立思考，在狂热中保持理性', 540, 1610, 50, 'serif_black', face=GOLD_GRAD, side=(0.3, 0.17, 0.04), depth=5, a=ia, glow=0.4)
    F.text('数据：Yahoo Finance、腾讯证券、东方财富、中证指数；回测脚本与明细见项目目录', 540, 1840, 19, 'sans_reg', FAINT, a * eo(ramp(u, 2, 3)))


# ================================================================ end card（品牌片尾，参考 love_video/render.py）
LOGO_PX = 300
LOGO_RGB, LOGO_A = load_logo(LOGO_PX)          # 官方 logo（brand/logo_baman.png）
LOGO_Y = 700
N_LP = 9000
_LP = None


def _logo_particles():
    """起点 = 上一幕画面里的文字/图形像素（画面元素本身化作粒子），终点 = 官方 logo 透明通道采样"""
    rng = np.random.default_rng(42)
    ys, xs = np.where(LOGO_A > 0.4)
    w = LOGO_A[ys, xs].astype(np.float64)
    k = rng.choice(len(xs), N_LP, replace=len(xs) < N_LP, p=w / w.sum())
    tx = xs[k] + rng.random(N_LP) - 0.5 + (540 - LOGO_PX / 2)
    ty = ys[k] + rng.random(N_LP) - 0.5 + (LOGO_Y - LOGO_PX / 2)
    col = LOGO_RGB[ys[k], xs[k]]
    # 上一幕（投资启示）最后一帧的亮像素
    G = Frame(T_END, np.zeros((H, W, 3), np.float32))
    sc_value(G, T_END - 0.01)
    lum = G.img.max(2)
    sy, sx = np.where(lum > 0.35)
    j = rng.choice(len(sx), N_LP, replace=len(sx) < N_LP)
    sx, sy = sx[j] + rng.random(N_LP) - 0.5, sy[j] + rng.random(N_LP) - 0.5
    scol = np.clip(G.img[sy.astype(int), sx.astype(int)], 0, 1)
    delay = rng.uniform(0, 0.5, N_LP)
    drift = rng.normal(0, 1, (N_LP, 2))
    return tx, ty, sx, sy, col, scol, delay, drift


def sc_end(F, t):
    global _LP
    if _LP is None:
        _LP = _logo_particles()
    tx, ty, sx, sy, col, scol, delay, drift = _LP
    u = t - T_END
    a = ramp(t, T_END - 0.2, T_END + 0.5)
    F.darken(np.ones((H, W), np.float32), 0, 0, 0.55 * a)
    # 1) 画面元素化作粒子，旋转汇聚成官方 logo
    dur = T_LOGO - T_END
    p = np.clip((u - delay) / (dur - 0.55), 0, 1)
    e = p * p * (3 - 2 * p)
    def pos(e):
        sw = (1 - e) * 1.4
        cxp, cyp = sx - 540, sy - LOGO_Y
        rx = cxp * np.cos(sw) - cyp * np.sin(sw); ry = cxp * np.sin(sw) + cyp * np.cos(sw)
        return 540 + rx * (1 - e) + (tx - 540) * e, LOGO_Y + ry * (1 - e) + (ty - LOGO_Y) * e
    x, y = pos(e)
    # logo 出现后，粒子慢慢化作四散的微尘
    k = eo(ramp(t, T_LOGO + 0.3, T_LOGO + 3.0))
    x = x + drift[:, 0] * 160 * k; y = y + drift[:, 1] * 160 * k
    pa = ramp(u, 0, 0.25) * (1 - 0.7 * ramp(t, T_LOGO - 0.1, T_LOGO + 0.4)) * (1 - ramp(t, T_LOGO + 2.0, T_FADE))
    if pa > 0:
        c = scol * (1 - e[:, None]) + col * e[:, None]
        for kk, wgt in enumerate((1.0, 0.5, 0.25)):
            if kk:
                p2 = np.clip((u - kk * 0.035 - delay) / (dur - 0.55), 0, 1); xx, yy = pos(p2 * p2 * (3 - 2 * p2))
                xx = xx + drift[:, 0] * 160 * k; yy = yy + drift[:, 1] * 160 * k
            else:
                xx, yy = x, y
            ok = (xx >= 0) & (xx < W - 1) & (yy >= 0) & (yy < H - 1)
            dens = (0.6 - 0.32 * e[ok, None]) * pa * wgt
            for ox, oy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                idx = ((yy[ok] + oy).astype(int), (xx[ok] + ox).astype(int))
                np.add.at(F.img, idx, c[ok] * dens)
                np.add.at(F.glow, idx, c[ok] * dens * 1.2)
    # 2) 清晰的官方 logo 居中浮现
    la = eo(ramp(t, T_LOGO - 0.12, T_LOGO + 0.6))
    if la > 0:
        sc = 1 + 0.05 * (1 - eo(ramp(t, T_LOGO - 0.12, T_LOGO + 1.4)))
        px = int(LOGO_PX * sc)
        rgb, al = load_logo(px) if px != LOGO_PX else (LOGO_RGB, LOGO_A)
        F.blob((540, LOGO_Y), 110, (110 / 255, 175 / 255, 1.0), 0.12 * la)       # 很淡的蓝色光晕（品牌规范）
        F.over(al, 540 - px // 2, LOGO_Y - px // 2, rgb, la)
        if t > T_LOGO:
            uu = t - T_LOGO
            F.circle((540, LOGO_Y), 170 + 420 * eo(uu / 1.4), (110 / 255, 175 / 255, 1.0), la * (1 - ramp(uu, 0, 1.4)) * 0.7, 3, glow=1.0)
            F.flash = 0.16 * math.exp(-uu / 0.1)
    # 3) 金色「巴芒价值」：重拍上自左向右擦出，随后流光扫过；两侧细金线向外延伸
    if t >= T_GOLD - 0.02:
        w = eo(ramp(t, T_GOLD, T_GOLD + 0.8))
        sp = ramp(t, T_GOLD + 0.9, T_GOLD + 2.3)
        tw = F.text('巴芒价值', 540, 980, 132, 'serif_black', a=1.0, grad=GOLD_GRAD, glow=0.35, wipe=w, shine=sp,
                    shadow=0.5, track=0.06)
        hw = tw / 2 + 40
        ln = 150 * eo(ramp(t, T_GOLD + 0.3, T_GOLD + 1.3))
        for sg in (-1, 1):
            F.line((540 + sg * hw, 978), (540 + sg * (hw + ln), 978), SUBGOLD, 0.8, 2, glow=0.4)
        # BUFFETT · MUNGER：两端对齐到与「巴芒价值」等宽
        ws = eo(ramp(t, T_SUB, T_SUB + 0.8))
        sub = 'BUFFETT · MUNGER'
        fs = 34
        f = font('corm', fs)
        nat = sum(f.getlength(ch) for ch in sub)
        tr = (tw - nat) / (len(sub) - 1)
        xc = 540 - tw / 2
        for i, ch in enumerate(sub):
            cw = f.getlength(ch)
            ca = cl((ws * (tw + 120) - (xc - (540 - tw / 2))) / 120)
            F.text(ch, xc, 1082, fs, 'corm', SUBGOLD, ca, anchor='l')
            xc += cw + tr
    # 4) 细金线引出金色关注语
    la2 = ramp(t, T_FOLLOW, T_FOLLOW + 0.7)
    if la2 > 0:
        w = 300 * eo(la2)
        F.line((540 - w, 1170), (540 + w, 1170), GOLD, 0.8, 2, glow=0.8)
        for sg in (-1, 1):
            F.blob((540 + sg * w, 1170), 8, GOLD, 0.8 * (1 - la2))
        F.text('关注「巴芒价值」', 540, 1255, 46, 'serif_black', a=1.0, grad=GOLD_GRAD, glow=0.3,
               wipe=eo(ramp(t, T_FOLLOW + 0.3, T_FOLLOW + 1.0)))
        F.text('传承大师智慧，领悟投资真谛', 540, 1335, 38, 'serif', a=1.0, grad=GOLD_GRAD, glow=0.2,
               wipe=eo(ramp(t, T_FOLLOW + 0.7, T_FOLLOW + 1.5)))


# ================================================================ frame
SCENES = [(0, T_TITLE + 0.1, sc_hook), (T_TITLE - 0.05, T_RULES + 0.5, sc_title), (T_RULES, year_t0(0) + 0.4, sc_rules),
          (year_t0(0) - 0.3, T_RACE_END + 0.7, sc_race), (T_FINAL - 0.3, T_BREAK + 0.5, sc_final),
          (T_BREAK - 0.1, T_WHY + 0.1, sc_break), (T_WHY - 0.1, T_STATEMENT + 0.2, sc_why),
          (T_STATEMENT - 0.1, T_VALUE + 0.3, sc_statement), (T_VALUE - 0.1, T_END + 0.8, sc_value), (T_END - 0.2, T_TOTAL + 1, sc_end)]


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
