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


HOOK = [0.0, B(4), B(8), B(12), T_TITLE]


def hwin(t, k, fi=0.22, fo=0.2):
    """开场第 k 屏的可见度：上一屏完全淡出后下一屏才出现，画面里永远只有一个信息"""
    return env(t, HOOK[k], HOOK[k + 1] - 0.02, fi, fo)


def pop(t, t0, k=0.3, d=0.14):
    return 1 + k * math.exp(-max(t - t0, 0) / d)


def halo(F, c, r, t, a, col, n=3, th=3):
    """旋转的光环：几段弧线以不同速度绕圈 + 柔光"""
    if a <= 0.01: return
    F.blob(c, r * 1.1, col, 0.10 * a)
    for k in range(n):
        rr = r * (1 + 0.12 * k)
        a0 = t * (0.6 - 0.35 * k) + k * 2.1
        for s in range(3):
            q0 = a0 + s * 2 * math.pi / 3
            pts = [(c[0] + rr * math.cos(q), c[1] + rr * math.sin(q)) for q in np.linspace(q0, q0 + 1.5 - 0.3 * k, 40)]
            F.poly(pts, col, a * (0.75 - 0.2 * k), th - k * 0.8 if th - k * 0.8 > 1 else 1, glow=0.9)


def wan_str(x):
    num, unit = fmt_wan(x)
    return num, unit


def big_money(F, x, cx, y, size, col, a, glow=0.4):
    num, unit = fmt_wan(x) if abs(x - 1) > 1e-9 else ('10', '万')
    nw = text_w(num, 'num', int(size)); uw = text_w(unit, 'sans_black', int(size * 0.5))
    x0 = cx - (nw + uw + 10) / 2
    F.text(num, x0, y, size, 'num', col, a, anchor='l', glow=glow, shadow=0.4)
    F.text(unit, x0 + nw + 10, y + size * 0.12, size * 0.5, 'sans_black', col, a, anchor='l', glow=glow * 0.6)


def sc_hook(F, t):
    """0 – 12.9 s：结果先行的悬念钩子。四屏，每屏只讲一件事，严格前后衔接"""
    UT, CT = STORY['us_total'], STORY['cn_total']
    BASE = 1330; K = 300                        # 光柱基线 / 每 10 倍的高度
    # ① 同样的起点
    a = hwin(t, 0, fi=0.06)
    if a > 0:
        F.text_chars('同样的 10 万本金', 540, 380, 72, 'serif_black', INK, a, t0=0.02, stag=0.05)
        two_tone(F, [('同一个策略，坚持 ', INK), ('10 年', GOLD_GRAD)], 540, 490, 56, 'serif_black', B(1.2), a, glow=0.25)
        for j in range(2):
            cx = 300 + j * 480; cy = 930
            ca = a * eo(ramp(t, B(2) + j * 0.15, B(2) + 0.5 + j * 0.15))
            if ca <= 0: continue
            halo(F, (cx, cy), 165 * (0.85 + 0.15 * eo(ramp(t, B(2), B(2) + 0.6))), t + j, ca, GOLD)
            F.text(f'账户 {"①②"[j]}', cx, cy - 70, 34, 'sans_bold', SUBGOLD, ca)
            spin = ramp(t, B(3), B(3) + 0.2)
            if spin <= 0:
                big_money(F, 1.0, cx, cy + 20, 84, GOLD_L, ca)
            else:
                num = spin_number(t, j)
                F.text(num, cx, cy + 20, 76, 'num', GOLD_L, ca, glow=0.5)
            F.text('十年后 = ?', cx, cy + 105, 28, 'sans_med', DIM, ca)
    # ② 十年后：一个冲上云霄，一个跌穿地板
    a = hwin(t, 1)
    if a > 0:
        F.text('十年后', 540, 300, 56, 'serif_black', INK, a)
        F.line((80, BASE), (1000, BASE), GOLD, a * 0.7, 2, glow=0.6)
        F.text('起点 10 万', 1000, BASE + 30, 22, 'sans_reg', GOLD, a * 0.8, anchor='r')
        for j, (tot, col, t0) in enumerate([(UT, US, B(4) + 0.1), (CT, CN, B(5))]):
            cx = 300 + j * 480
            p = eio(ramp(t, t0, t0 + 1.6))
            cur = 10 ** (math.log10(tot) * p)
            h = K * math.log10(cur)
            x0, x1 = cx - 80, cx + 80
            if h >= 0:
                F.fill([(x0, BASE - h), (x1, BASE - h), (x1, BASE), (x0, BASE)], col, a * 0.55, glow=0.5)
                F.line((x0, BASE - h), (x1, BASE - h), lerpc(col, WHITE, 0.6), a, 4, glow=1.5)
                F.blob((cx, BASE - h), 110, col, 0.35 * a)
                ny = BASE - h - 80
            else:
                F.fill([(x0, BASE), (x1, BASE), (x1, BASE - h), (x0, BASE - h)], mix(CN2, 0.8), a * 0.5, glow=0.4)
                F.line((x0, BASE - h), (x1, BASE - h), CN2, a, 4, glow=1.2)
                ny = BASE - h + 80
            done = ramp(t, t0 + 1.6, t0 + 1.7)
            sz = 96 * pop(t, t0 + 1.6, 0.35) if done > 0 else 84
            big_money(F, cur, cx, ny, sz, lerpc(col, WHITE, 0.35), a, glow=0.5 + 0.4 * done)
            F.text(f'账户 {"①②"[j]}', cx, BASE + (40 if h >= 0 else -40), 30, 'sans_bold', col, a)
            if 0 < t - t0 - 1.6 < 0.6:
                u = (t - t0 - 1.6) / 0.6
                F.circle((cx, ny), 60 + 260 * eo(u), col, a * (1 - u), 3, glow=1.0)
    # ③ 相差 1,332 倍
    a = hwin(t, 2, fi=0.08)
    if a > 0:
        u = t - B(8)
        F.text('两个账户相差', 540, 700, 52, 'serif_black', INK, a)
        F.text3d(f"{STORY['gap']:,.0f}", 470, 900, 230 * pop(t, B(8), 0.4), 'num', face=GOLD_GRAD, a=a, glow=0.55, spec=ramp(u, 0.2, 1.4))
        F.text('倍', 470 + text_w(f"{STORY['gap']:,.0f}", 'num', 230) / 2 + 70, 930, 110, 'serif_black', a=a, grad=GOLD_GRAD, glow=0.4)
        if u < 0.8:
            F.circle((540, 900), 100 + 800 * eo(u / 0.8), GOLD, a * (1 - u / 0.8), 5, glow=1.2)
            F.zoom = 1 + 0.03 * math.exp(-u / 0.15)
            F.shake = (math.sin(u * 90) * 10 * math.exp(-u / 0.12), 0.0)
        F.text('规则只有一条', 540, 1130, 36, 'sans_med', DIM, a * eo(ramp(t, B(10), B(10) + 0.4)))
        two_tone(F, [('每年买入上一年的', INK), ('涨幅冠军', GOLD_GRAD)], 540, 1215, 58, 'serif_black', B(10) + 0.25, a, glow=0.25)
    # ④ 一个美股，一个 A 股 —— 你猜？
    a = hwin(t, 3, fi=0.08, fo=0.12)
    if a > 0:
        two_tone(F, [('一个投 ', INK), ('美股', [(0, US), (1, US2)]), ('，一个投 ', INK), ('A 股', [(0, CN), (1, CN2)])],
                 540, 780, 62, 'serif_black', B(12) + 0.02, a, stag=0.035, glow=0.3)
        qa = a * eo(ramp(t, B(13.5), B(13.5) + 0.35))
        F.text3d('你猜，哪个是 A 股？', 540, 960, 88 * pop(t, B(13.5), 0.25), 'serif_black', face=GOLD_GRAD, a=qa, glow=0.45,
                 spec=ramp(t, B(13.5) + 0.2, B(13.5) + 1.2))
        F.text('答案和背后的原因，马上揭晓', 540, 1090, 36, 'sans_med', DIM, a * eo(ramp(t, B(14.5), B(14.5) + 0.4)))


def sc_title(F, t):
    """12.91 s 重击：标题"""
    u = t - T_TITLE
    a = env(t, T_TITLE, T_RULES - 0.02, 0.05, 0.35)
    if a <= 0: return
    F.flash = 0.9 * math.exp(-u / 0.12) if u >= 0 else 0
    # 冲击波环
    for k, d in enumerate((0, 0.18)):
        uu = u - d
        if uu > 0:
            r = 80 + 1400 * eo(uu / 1.6)
            F.circle((540, 900), r, GOLD, a * 0.7 * (1 - ramp(uu, 0, 1.6)), 4, glow=1.0)
    sc = 1 + 0.25 * math.exp(-u / 0.25)
    F.text3d('追涨十年', 540, 860, 230 * sc, 'serif_black', face=GOLD_GRAD, a=a, track=0.04,
             glow=0.45, spec=ramp(u, 0.3, 1.8))
    F.text_chars('每年只买去年的涨幅冠军', 540, 1090, 54, 'sans_bold', INK, a, t0=T_TITLE + 0.35, stag=0.035)
    w = 360 * eo(ramp(u, 0.9, 1.8))
    F.line((540 - w, 1215), (540 + w, 1215), GOLD, a * 0.7, 2, glow=0.6)
    F.text('美股 vs A股 · 2016—2025', 540, 1268, 34, 'sans_med', SUBGOLD, a * ramp(u, 1.2, 1.9))
    F.text('一场用真实数据完成的十年投资实验', 540, 1320, 30, 'sans_reg', DIM, a * ramp(u, 1.4, 2.1))
    F.zoom = 1 + 0.03 * math.exp(-u / 0.3)


def sc_rules(F, t):
    a = env(t, T_RULES, year_t0(0) - 0.03, 0.35, 0.3)
    if a <= 0: return
    F.text_chars('实验规则', 540, 300, 64, 'serif_black', GOLD, a, t0=T_RULES + 0.05, stag=0.06, grad=GOLD_GRAD)
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
    a_sec = env(t, year_t0(0), T_RACE_END + 0.15, 0.3, 0.45)
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
    a = env(t, T_FINAL + 0.15, T_BREAK + 0.3, 0.4, 0.5)
    if a <= 0: return
    F.text_chars('十年后，10 万变成了……', 540, 250, 58, 'serif_black', INK, a, t0=T_FINAL + 0.25, stag=0.05)
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
    F.text_chars('为什么差距这么大？', 540, 860, 80, 'serif_black', INK, a, t0=T_BREAK + 0.5, stag=0.08, dur=0.6)
    two_tone(F, [('答案，藏在「', DIM), ('冠军', GOLD_GRAD), ('」是怎么来的', DIM)], 540, 1000, 44, 'serif', B(132), a, stag=0.05)


# ================================================================ why：从第一性原理讲清差异（v5：12 个整屏镜头，每 4 拍一个）
# 每个原因拆成两个镜头；每个镜头只有一个标题 + 一个主视觉 + 一句结论，前一个镜头完全淡出后下一个才出现。
WHY_SHOT_T = [T_WHY] + [B(k) for k in range(140, 181, 4)] + [T_INSIGHT]      # 13 个边界 → 12 个镜头
CH_COL = [GOLD, GOLD_L, UP, CN, US, hexc('#E040FB')]


def gbar(F, x0, x1, yb, h, col, a, glow=0.5, refl=True):
    """发光渐变柱：顶端亮、根部暗，顶部一道亮线，正柱在地面有倒影"""
    if a <= 0.01 or abs(h) < 1: return
    w = int(round(x1 - x0)); hh = int(abs(h)) + 1
    top, bot = lerpc(col, WHITE, 0.4), mix(col, 0.5)
    if h > 0:
        g = vgrad(hh, [(0, top), (0.35, col), (1, bot)]); al = np.linspace(1, 0.5, hh); y0 = yb - hh
    else:
        g = vgrad(hh, [(0, bot), (0.65, col), (1, top)]); al = np.linspace(0.5, 1, hh); y0 = yb
    m = np.repeat(al[:, None], w, 1).astype(np.float32)
    F.over(m, x0, y0, np.repeat(g, w, 1), a * 0.92, glow)
    cy = yb - h
    F.line((x0, cy), (x1, cy), lerpc(col, WHITE, 0.7), a, 3, glow=1.4)
    F.blob(((x0 + x1) / 2, cy), (x1 - x0) * 0.7, col, 0.18 * a)
    if refl and h > 0:
        rh = min(hh, 90)
        F.add(np.repeat(np.linspace(0.16, 0, rh)[:, None], w, 1).astype(np.float32), x0, yb + 3, col, a)


def ring_gauge(F, c, r, frac, col, a, th=20):
    if a <= 0.01: return
    full = [(c[0] + r * math.cos(q), c[1] + r * math.sin(q)) for q in np.linspace(0, 2 * math.pi, 180)]
    F.poly(full, col, a * 0.12, th)
    if frac > 0.002:
        qs = np.linspace(-math.pi / 2, -math.pi / 2 + 2 * math.pi * frac, max(4, int(180 * frac)))
        F.poly([(c[0] + r * math.cos(q), c[1] + r * math.sin(q)) for q in qs], col, a, th, glow=0.9)
        q = qs[-1]
        F.blob((c[0] + r * math.cos(q), c[1] + r * math.sin(q)), 40, lerpc(col, WHITE, 0.5), 0.6 * a)


def arrow(F, p0, p1, col, a, th=4, head=18):
    if a <= 0.01: return
    F.line(p0, p1, col, a, th, glow=0.8)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for s in (-1, 1):
        q = ang + math.pi - s * 0.5
        F.line(p1, (p1[0] + head * math.cos(q), p1[1] + head * math.sin(q)), col, a, th, glow=0.8)


def pct0(v):
    return f'{v * 100:+,.0f}%'.replace('-', '−')


def why_frame(F, t, ch, a):
    """章节标识：原因 0X / 06 + 六段进度条（同一原因的两个镜头之间保持不动）"""
    col = CH_COL[ch]
    F.text(f'原因  {ch + 1:02d}  /  06', 540, 180, 26, 'sans_med', col, a, track=0.15)
    for j in range(6):
        x = 540 - 3 * 64 + j * 64 + 6
        F.line((x, 218), (x + 50, 218), col if j == ch else (FAINT if j > ch else mix(col, 0.6)), a * (1 if j <= ch else 0.6),
               4 if j == ch else 2, glow=0.8 if j == ch else 0)


def why_head(F, t0, s, a, sub=None, size=62, col=INK):
    F.text_chars(s, 540, 305, size, 'serif_black', col, a, t0=t0 + 0.05, stag=0.035, dur=0.45)
    if sub:
        F.text(sub, 540, 385, 28, 'sans_reg', DIM, a * eo(ramp(F.t, t0 + 0.4, t0 + 0.8)))


def big_stat(F, num, unit, line, y, col, a, nsize=130, pre=None):
    """大号数据 + 单位 + 下方一行说明（pre：上方一行引导语）"""
    if a <= 0.01: return
    if pre:
        F.text(pre, 540, y - nsize * 0.78, 36, 'sans_bold', INK, a)
    nw = text_w(num, 'num', nsize); uw = text_w(unit, 'serif_black', int(nsize * 0.42))
    x0 = 540 - (nw + uw + 14) / 2
    F.text(num, x0, y, nsize, 'num', a=a, anchor='l', grad=[(0, lerpc(col, WHITE, 0.55)), (1, col)], glow=0.45, shadow=0.4)
    F.text(unit, x0 + nw + 14, y + nsize * 0.12, nsize * 0.42, 'serif_black', col, a, anchor='l', glow=0.3)
    if line:
        F.text(line, 540, y + nsize * 0.78, 36, 'sans_bold', INK, a)


# ---------------------------------------------------------------- 镜头
def shot_bars(F, t, u, a, g, us):
    lab, col, vals, bench = STORY['why'][0]['groups'][0 if us else 1]
    why_head(F, F.t - u, '美股冠军的下一年' if us else 'A股冠军的下一年', a, '每根柱子 = 买入当年的实际收益（扣成本）　白线 = 同期指数')
    base = 1150 if us else 960
    K = 300
    F.line((90, base), (990, base), WHITE, a * 0.35, 1)
    for k, (v, b) in enumerate(zip(vals, bench)):
        tk = 0.25 + k * 0.07
        p = eo(ramp(u, tk, tk + 0.6)); ba = a * eo(ramp(u, tk, tk + 0.25))
        x = 112 + k * 88
        h = max(-0.75, min(v, 1.75)) * K * p
        gbar(F, x, x + 60, base, h, col if v >= 0 else DOWN, ba, refl=us)
        F.text(pct0(v * p), x + 30, base - max(h, 0) - 30 if (h >= 0 or us) else base - h + 30, 22, 'num_semi', lerpc(col if v >= 0 else DOWN, WHITE, 0.3), ba)
        F.text(str(2016 + k), x + 30, base + (40 if us else 270), 20, 'num_reg', DIM, ba)
        bh = max(-0.75, min(b, 1.75)) * K
        F.line((x - 6, base - bh), (x + 66, base - bh), WHITE, ba * 0.9 * eo(ramp(u, tk + 0.5, tk + 0.8)), 2, glow=0.6)
    sa = a * eo(ramp(u, 1.4, 1.8))
    if us:
        n = sum(v > b for v, b in zip(vals, bench))
        big_stat(F, f'{n}', ' 年跑赢标普500', None, 1480, GOLD, sa, pre='10 年里')
    else:
        n = sum(v < 0 for v in vals); m = sum(v > b for v, b in zip(vals, bench))
        big_stat(F, f'{n}', ' 年亏损', f'只有 {m} 年跑赢沪深300', 1480, DOWN, sa, pre='10 年里')


def shot_formula(F, t, u, a, g):
    why_head(F, F.t - u, '股价从长期看，由什么决定？', a)
    tiles = [('股价', INK, 150), ('利润', UP, 540), ('估值', GOLD, 930)]
    for k, (s, c, x) in enumerate(tiles):
        tk = 0.2 + k * 0.25
        ia = a * eo(ramp(u, tk, tk + 0.35))
        dy = (1 - eback(ramp(u, tk, tk + 0.5))) * -80
        wob = 1 + (0.05 * math.sin(u * 7.5) * ramp(u, 1.4, 1.8) if s == '估值' else 0)
        w = 128 * wob
        F.glass(x - w, 640 - 92 * wob + dy, x + w, 640 + 92 * wob + dy, 34, ia, tint=c, tint_a=0.16, shadow=0.35, blur=16, spec=ramp(u, tk, tk + 1))
        F.text(s, x, 640 + dy, 84 * wob, 'serif_black', c if s != '股价' else INK, ia, glow=0.45)
    for s, x, tk in (('=', 345, 0.45), ('×', 735, 0.7)):
        F.text(s, x, 640, 84, 'num', DIM, a * eo(ramp(u, tk, tk + 0.3)))
    F.text('每股利润', 540, 770, 26, 'sans_reg', DIM, a * eo(ramp(u, 0.8, 1.1)))
    F.text('市盈率', 930, 770, 26, 'sans_reg', DIM, a * eo(ramp(u, 0.9, 1.2)))
    for k, (c, x, l1, l2) in enumerate([(UP, 540, '企业真实赚到的钱', '长期决定股价的方向'), (GOLD, 930, '市场愿意出的倍数', '短期随情绪剧烈摇摆')]):
        tk = 1.2 + k * 0.45
        ka = a * eo(ramp(u, tk, tk + 0.35))
        x0 = 70 + k * 480; x1 = x0 + 460; cx = (x0 + x1) / 2
        q = eo(ramp(u, tk - 0.15, tk + 0.25))
        arrow(F, (x, 800), (x + (cx - x) * q, 800 + (905 - 800) * q), c, ka * 0.85, 3, 14)
        F.glass(x0, 920, x1, 1120, 34, ka, tint=c, tint_a=0.12, shadow=0.25, blur=12, spec=ramp(u, tk, tk + 1))
        F.text(l1, cx, 990, 38, 'sans_black', c, ka, glow=0.25)
        F.text(l2, cx, 1060, 28, 'sans_reg', INK, ka)
    fa = a * eo(ramp(u, 2.1, 2.5))
    F.text3d('长期看利润，短期看情绪', 540, 1330, 62, 'serif_black', face=GOLD_GRAD, a=fa, glow=0.45, spec=ramp(u, 2.3, 3.2))


def shot_weigh(F, t, u, a, g):
    why_head(F, F.t - u, '价格，围绕价值波动', a, '金线 = 内在价值（随利润增长）　蓝线 = 股价')
    gx0, gx1 = 90, 990
    n = 260
    xx = np.linspace(0, 1, n)
    trend = 1130 - xx * 420
    noise = (np.sin(xx * 37) * 0.6 + np.sin(xx * 91 + 1) * 0.35 + np.sin(xx * 13 + 2) * 0.8) * 110 * (0.4 + 0.6 * np.sin(xx * 3.1) ** 2)
    pp = eio(ramp(u, 0.2, 2.0)); m = max(2, int(n * pp))
    X = gx0 + xx * (gx1 - gx0)
    pr = trend + noise
    # 高估（价格在价值上方）红色、低估绿色：两线之间填色
    for i in range(0, m - 1, 2):
        up = pr[i] < trend[i]
        F.fill([(X[i], trend[i]), (X[i + 2 if i + 2 < m else i + 1], trend[min(i + 2, m - 1)]),
                (X[i + 2 if i + 2 < m else i + 1], pr[min(i + 2, m - 1)]), (X[i], pr[i])], UP if up else DOWN, a * 0.22, mode='add')
    PRICE = (0.55, 0.78, 1.0)
    F.glow_line(list(zip(X[:m], pr[:m])), PRICE, a * 0.95, 3, glow=0.8)
    F.glow_line(list(zip(X[:m], trend[:m])), GOLD, a, 6, glow=1.2)
    if pp < 1:
        F.blob((X[m - 1], pr[m - 1]), 30, PRICE, a); F.blob((X[m - 1], trend[m - 1]), 30, GOLD, a)
    la = a * eo(ramp(u, 1.0, 1.4))
    F.text('高估', 300, 560, 30, 'sans_bold', UP, la); F.text('低估', 760, 1120, 30, 'sans_bold', DOWN, la)
    qa = a * eo(ramp(u, 1.7, 2.1))
    F.text3d('短期是投票机，长期是称重机', 540, 1380, 58, 'serif_black', face=GOLD_GRAD, a=qa, glow=0.45, spec=ramp(u, 2.0, 3.2))
    F.text('—— 本杰明 · 格雷厄姆（巴菲特的老师）', 540, 1470, 28, 'serif_med', SUBGOLD, qa)


def stock_card(F, y, row, a, u, tk, gold=False):
    name, yr, price, desc, nxt = row
    ka = a * eo(ramp(u, tk, tk + 0.35))
    if ka <= 0: return
    dx = (1 - eo(ramp(u, tk, tk + 0.45))) * 90
    F.glass(70 + dx, y - 110, 1010 + dx, y + 110, 36, ka, tint=GOLD if gold else (0.6, 0.7, 1.0), tint_a=0.14 if gold else 0.06,
            shadow=0.3, blur=14, spec=ramp(u, tk, tk + 1.0) if gold else 0)
    F.text(name, 110 + dx, y - 58, 44, 'sans_black', GOLD_L if gold else INK, ka, anchor='l')
    F.text(desc, 970 + dx, y - 56, 28, 'sans_med', GOLD if gold else DIM, ka, anchor='r')
    F.text(f'{yr} 年股价', 110 + dx, y + 18, 24, 'sans_reg', DIM, ka, anchor='l')
    p = eo(ramp(u, tk + 0.2, tk + 0.9))
    F.text(pct0(price * p), 110 + dx, y + 66, 64, 'num', UP, ka, anchor='l', glow=0.45)
    q = eo(ramp(u, tk + 0.6, tk + 1.0))
    arrow(F, (560 + dx, y + 50), (560 + dx + 140 * q, y + 50), WHITE, ka * 0.7, 3, 14)
    F.text('次年', 970 + dx, y + 18, 24, 'sans_reg', DIM, ka * q, anchor='r')
    F.text(pct0(nxt * q), 970 + dx, y + 66, 64, 'num', ret_col(nxt), ka * q, anchor='r', glow=0.45)


def shot_profit(F, t, u, a, g, part):
    rows = STORY['why'][2]['rows']
    if part == 0:
        why_head(F, F.t - u, '利润是真的，但已到顶', a, '一次性景气：疫情、政策、周期')
        for k, r in enumerate(rows[0][1]):
            stock_card(F, 600 + k * 260, r, a, u, 0.25 + k * 0.4)
        fa = a * eo(ramp(u, 1.9, 2.3))
        F.text('高点买入的，是一次性的利润', 540, 1470, 42, 'sans_black', GOLD_L, fa, glow=0.25)
    else:
        why_head(F, F.t - u, '股价跑在利润前面', a, '题材驱动 vs 价值兑现')
        for k, r in enumerate(rows[1][1]):
            stock_card(F, 600 + k * 260, r, a, u, 0.25 + k * 0.4)
        stock_card(F, 1120, rows[2][1][0], a, u, 1.05, gold=True)
        F.text('利润追上来，股价才站得住', 540, 1300, 30, 'sans_bold', GOLD, a * eo(ramp(u, 1.6, 2.0)))
        fa = a * eo(ramp(u, 2.0, 2.4))
        F.text('价格跑在利润前面越远，回落就越狠', 540, 1470, 42, 'sans_black', GOLD_L, fa, glow=0.25)


def shot_ipo(F, t, u, a, g):
    p = STORY['why'][3]
    why_head(F, F.t - u, '涨幅榜前 50 名，几只是新股？', a, '每年 A 股涨幅前 50 名中，当年新上市的股票数量')
    base, K = 1200, 11.0
    F.line((90, base), (990, base), WHITE, a * 0.35, 1)
    F.line((90, base - 50 * K), (990, base - 50 * K), WHITE, a * 0.18, 1)
    F.text('50', 80, base - 50 * K, 20, 'num_reg', DIM, a, anchor='r')
    for k, (yv, n) in enumerate(zip(p['years'], p['new'])):
        tk = 0.2 + k * 0.07
        q = eo(ramp(u, tk, tk + 0.6)); ba = a * eo(ramp(u, tk, tk + 0.25))
        x = 112 + k * 88
        col = CN if yv < 2019 else lerpc(CN, US, min(1, (yv - 2018) / 5))
        gbar(F, x, x + 60, base, n * K * q, col, ba)
        F.text(f'{n * q:.0f}', x + 30, base - n * K * q - 30, 28, 'num', lerpc(col, WHITE, 0.3), ba)
        F.text(str(yv), x + 30, base + 120, 19, 'num_reg', DIM, ba)
    ra = a * eo(ramp(u, 1.0, 1.4))
    x19 = 112 + 4 * 88 - 14
    F.line((x19, base - 50 * K - 30), (x19, base + 40), US, ra * 0.7, 2, glow=0.6)
    F.text('2019 起注册制 →', x19 + 12, base - 50 * K - 30, 22, 'sans_med', US, ra, anchor='l')
    big_stat(F, f"{p['share'] * 100:.0f}", '%', '十年平均：前 50 名里是当年新股', 1470, CN, a * eo(ramp(u, 1.5, 1.9)), nsize=140)


def shot_ipo_why(F, t, u, a, g):
    p = STORY['why'][3]
    why_head(F, F.t - u, '新股为什么霸占涨幅榜？', a, '核准制时代的定价机制')
    steps = [('①', '发行价被压在约 23 倍市盈率', '上市即「便宜」'), ('②', '首日涨幅封顶 44%', '涨不够的，留到后面'),
             ('③', '上市后连续一字涨停', '散户几乎买不到'), ('④', '稀缺 + 连板', '霸占全年涨幅榜')]
    for k, (n, l1, l2) in enumerate(steps):
        tk = 0.25 + k * 0.4
        ka = a * eo(ramp(u, tk, tk + 0.3))
        y = 560 + k * 175
        if k:
            F.line((150, y - 175 + 55), (150, y - 175 + 55 + 65 * eo(ramp(u, tk - 0.2, tk))), CN, ka, 3, glow=1.0)
        F.circle((150, y), 44, CN, ka, 3, glow=1.0)
        F.text(n, 150, y, 40, 'sans_black', CN, ka)
        F.text(l1, 230, y - 18, 42, 'sans_black', INK, ka, anchor='l')
        F.text(l2, 230, y + 36, 28, 'sans_reg', DIM, ka, anchor='l')
    fa = a * eo(ramp(u, 2.0, 2.3))
    F.text('而这些「涨幅王」的下一年：', 540, 1340, 34, 'sans_med', INK, fa)
    F.text3d(f"10 年中 {p['worse']} 年跑输全市场", 540, 1440, 66, 'serif_black', face=[(0, lerpc(DOWN, WHITE, 0.5)), (1, DOWN)], a=fa, glow=0.45)
    F.text('注册制推行后，新股占比明显下降', 540, 1530, 26, 'sans_reg', DIM, fa)


def shot_players(F, t, u, a, g):
    why_head(F, F.t - u, 'A股：散户主导交易', a)
    C = (540, 760)
    fr = 0.6135 * eio(ramp(u, 0.2, 1.4))
    ring_gauge(F, C, 220, fr, CN, a, th=22)
    F.text(f'{fr * 100:.0f}%', 540, 740, 128, 'num', a=a, grad=[(0, lerpc(CN, WHITE, 0.5)), (1, CN)], glow=0.5)
    F.text('个人投资者交易占比', 540, 845, 30, 'sans_bold', INK, a)
    F.text('2022 年前三季度 · 监管数据', 540, 1010, 22, 'sans_reg', DIM, a)
    for j, (lab, col, items) in enumerate([('A股', CN, ['涨跌停 10% / 20%', '小盘、题材股多', '情绪容易走向极端']),
                                           ('美股', US, ['机构定价为主', '有做空机制约束', '标普500 须持续盈利'])]):
        tk = 1.2 + j * 0.35
        ca = a * eo(ramp(u, tk, tk + 0.35))
        x0 = 70 + j * 480; x1 = x0 + 460
        F.glass(x0, 1110, x1, 1460, 34, ca, tint=col, tint_a=0.10, shadow=0.25, blur=14)
        F.text(lab, (x0 + x1) / 2, 1170, 44, 'sans_black', col, ca, glow=0.3)
        for q, s in enumerate(items):
            F.text(s, (x0 + x1) / 2, 1260 + q * 62, 30, 'sans_med', INK, ca * eo(ramp(u, tk + 0.2 + q * 0.12, tk + 0.5 + q * 0.12)))


def shot_momentum(F, t, u, a, g):
    p = STORY['why'][4]
    why_head(F, F.t - u, '涨幅前 10 名，下一年会怎样？', a, '相对全市场的超额收益 · 十年平均')
    zero = 540
    F.line((zero, 560), (zero, 1180), GOLD, a * 0.6, 2, glow=0.8)
    for j, (lab, v, col, tag) in enumerate([('美股', p['us_top10'], US, '动量：强者恒强'), ('A股', p['cn_top10'], CN, '反转：物极必反')]):
        tk = 0.3 + j * 0.5
        y = 720 + j * 300
        q = eo(ramp(u, tk, tk + 0.8)); ba = a * eo(ramp(u, tk, tk + 0.2))
        L = v * 2800 * q
        x0, x1 = (zero, zero + L) if L >= 0 else (zero + L, zero)
        w = int(abs(x1 - x0)) + 1
        if w > 2:
            gx = np.linspace(0.35, 1, w) if L >= 0 else np.linspace(1, 0.35, w)
            m = np.repeat(gx[None, :], 110, 0).astype(np.float32)
            F.over(m, x0, y - 55, lerpc(col, WHITE, 0.15), ba * 0.9, glow=0.6)
            ex = zero + L
            F.line((ex, y - 55), (ex, y + 55), lerpc(col, WHITE, 0.7), ba, 4, glow=1.5)
            F.blob((ex, y), 90, col, 0.35 * ba)
        F.text(lab, zero + (-30 if v >= 0 else 30), y, 44, 'sans_black', col, ba, anchor='r' if v >= 0 else 'l')
        F.text(f'{v * q * 100:+.1f}%'.replace('-', '−'), zero + L / 2 if abs(L) > 1 else zero, y - 110, 76, 'num', a=ba,
               grad=[(0, lerpc(col, WHITE, 0.5)), (1, col)], glow=0.5)
        F.text(tag, zero + v * 1400, y + 100, 34, 'sans_bold', col, a * eo(ramp(u, tk + 0.8, tk + 1.1)))
    fa = a * eo(ramp(u, 1.9, 2.3))
    F.text('散户主导 + 涨跌停 + 小盘题材', 540, 1380, 40, 'sans_black', INK, fa)
    F.text('暴涨之后，更容易均值回归', 540, 1460, 46, 'serif_black', a=fa, grad=GOLD_GRAD, glow=0.35)


def shot_loop(F, t, u, a, g, brk_part):
    p = STORY['why'][5]
    cx, cy, R = 540, 900, 300
    nodes = p['nodes']; n = len(nodes)
    if not brk_part:
        why_head(F, F.t - u, '上涨本身，会吸引更多人追涨', a, '价格反过来改变人们的预期 —— 反身性')
        heat = ramp(u, 0, 3.0)
        col = lerpc(GOLD, UP, heat)
        # 加速旋转的彗星
        ph = u * (1.2 + 2.8 * heat)
        for k in range(14):
            q = -math.pi / 2 + ph - k * 0.06
            F.blob((cx + R * math.cos(q), cy + R * math.sin(q)), 22 - k, col, a * (1 - k / 14))
        F.poly([(cx + R * math.cos(q), cy + R * math.sin(q)) for q in np.linspace(0, 2 * math.pi, 160)], col, a * 0.35, 3, glow=0.6)
        for k, lab in enumerate(nodes):
            ang = -math.pi / 2 + k / n * 2 * math.pi
            ka = a * eo(ramp(u, 0.2 + k * 0.3, 0.5 + k * 0.3))
            x, y = cx + R * math.cos(ang), cy + R * math.sin(ang)
            F.glass(x - 130, y - 48, x + 130, y + 48, 48, ka, tint=col, tint_a=0.14, shadow=0.3, blur=12)
            F.text(lab, x, y, 34, 'sans_black', INK, ka)
        sc = 1 + 0.1 * math.sin(u * (6 + 10 * heat)) * heat
        F.blob((cx, cy), 160 * sc, col, 0.25 * a * (0.5 + heat))
        F.text(p['center'], cx, cy, 52 * sc, 'serif_black', a=a * eo(ramp(u, 1.0, 1.4)), grad=GOLD_GRAD, glow=0.5)
        F.text('股价越涨 → 关注越多 → 买的人越多', 540, 1400, 34, 'sans_bold', INK, a * eo(ramp(u, 1.8, 2.2)))
    else:
        brk = eo(ramp(u, 0.0, 0.9))
        # 环断裂：节点带着碎片坠落
        for k, lab in enumerate(nodes):
            ang = -math.pi / 2 + k / n * 2 * math.pi
            x, y = cx + R * math.cos(ang), cy + R * math.sin(ang)
            fall = 600 * ei(ramp(u, 0.1 + k * 0.08, 1.4 + k * 0.08))
            ka = a * (1 - ramp(u, 0.15, 0.55))
            F.glass(x - 130, y - 48 + fall, x + 130, y + 48 + fall, 48, ka, tint=DOWN, tint_a=0.14, shadow=0.3, blur=12)
            F.text(lab, x, y + fall, 34, 'sans_black', INK, ka)
        for k in range(12):
            q0 = k / 12 * 2 * math.pi
            fall = 700 * ei(ramp(u, 0.05 + (k % 5) * 0.05, 1.3))
            pts = [(cx + R * math.cos(q) + math.sin(k) * 60 * brk, cy + R * math.sin(q) + fall) for q in np.linspace(q0, q0 + 0.4, 10)]
            F.poly(pts, DOWN, a * (1 - ramp(u, 0.2, 0.6)), 3, glow=0.8)
        if u < 0.5:
            F.flash = max(F.flash, 0.25 * (1 - u / 0.5))
        ha = a * eo(ramp(u, 0.55, 0.9))
        F.text3d('直到：预期透支，泡沫破裂', 540, 820, 70 * pop(F.t, F.t - u + 0.55, 0.2), 'serif_black',
                 face=[(0, lerpc(DOWN, WHITE, 0.5)), (1, DOWN)], a=ha, glow=0.5)
        F.text('冠军的涨幅，变成了下一年的跌幅', 540, 930, 34, 'sans_med', INK, ha)
        ca = a * eo(ramp(u, 1.4, 1.8))
        F.glass(70, 1180, 1010, 1440, 36, ca, tint=US, tint_a=0.10, shadow=0.25, blur=14)
        F.text('美股这十年，也有运气', 540, 1250, 40, 'sans_black', US, ca, glow=0.3)
        F.text('5 笔芯片 / AI 交易，贡献了约 77% 的复利', 540, 1330, 34, 'sans_med', INK, ca)
        F.text('英伟达 ×2 · AMD ×2 · Palantir', 540, 1390, 26, 'sans_reg', DIM, ca)


WHY_SHOTS = [(0, lambda F, t, u, a: shot_bars(F, t, u, a, 0, True)), (0, lambda F, t, u, a: shot_bars(F, t, u, a, 0, False)),
             (1, lambda F, t, u, a: shot_formula(F, t, u, a, 1)), (1, lambda F, t, u, a: shot_weigh(F, t, u, a, 1)),
             (2, lambda F, t, u, a: shot_profit(F, t, u, a, 2, 0)), (2, lambda F, t, u, a: shot_profit(F, t, u, a, 2, 1)),
             (3, lambda F, t, u, a: shot_ipo(F, t, u, a, 3)), (3, lambda F, t, u, a: shot_ipo_why(F, t, u, a, 3)),
             (4, lambda F, t, u, a: shot_players(F, t, u, a, 4)), (4, lambda F, t, u, a: shot_momentum(F, t, u, a, 4)),
             (5, lambda F, t, u, a: shot_loop(F, t, u, a, 5, False)), (5, lambda F, t, u, a: shot_loop(F, t, u, a, 5, True))]


def sc_why(F, t):
    if t >= T_WHY:
        F.flash = max(F.flash, 0.6 * math.exp(-(t - T_WHY) / 0.12))
    for k, (ch, fn) in enumerate(WHY_SHOTS):
        t0, t1 = WHY_SHOT_T[k], WHY_SHOT_T[k + 1]
        if not (t0 <= t < t1): continue
        a = env(t, t0, t1 - 0.02, 0.3, 0.28)
        ch0 = WHY_SHOT_T[2 * ch]; ch1 = WHY_SHOT_T[2 * ch + 2]
        why_frame(F, t, ch, env(t, ch0, ch1 - 0.02, 0.3, 0.28))
        fn(F, t, t - t0, a)


# ================================================================ 投资启示：金色粒子汇聚成字的转场（音乐抽空段）
INS_SIZE, INS_Y = 190, 900


def _text_particles(s, fname, size, cx, cy, n, seed):
    """在文字 mask 内按亮度采样 n 个点，返回 (x, y, 竖向位置 0..1)"""
    rng = np.random.default_rng(seed)
    m, base, pad, w = text_mask(s, fname, size)
    ys, xs = np.where(m > 0.5)
    k = rng.choice(len(xs), n, replace=len(xs) < n)
    x = xs[k] + rng.random(n) - 0.5 + cx - w / 2 - pad
    y = ys[k] + rng.random(n) - 0.5 + cy + size * 0.36 - base
    return x, y, (ys[k] - ys.min()) / max(1, ys.max() - ys.min())


def _gold_at(v):
    """品牌金竖向渐变上的颜色（v=0 顶部 → 1 底部）"""
    P = np.array([p for p, _ in GOLD_GRAD]); C = np.array([c for _, c in GOLD_GRAD])
    return np.stack([np.interp(v, P, C[:, k]) for k in range(3)], -1)


N_IP = 7000
_IP = None


def _insight_particles():
    rng = np.random.default_rng(7)
    tx, ty, tv = _text_particles('投资启示', 'serif_black', INS_SIZE, 540, INS_Y, N_IP, 7)
    r = 280 + 520 * rng.random(N_IP) ** 0.7; q = rng.random(N_IP) * 2 * math.pi
    sx, sy = 540 + r * np.cos(q), INS_Y + r * np.sin(q) * 1.4
    return tx, ty, sx, sy, _gold_at(tv), rng.uniform(0, 0.6, N_IP)


def splat(F, x, y, c, dens, glow=1.2):
    ok = (x >= 0) & (x < W - 1) & (y >= 0) & (y < H - 1)
    if not ok.any(): return
    xi, yi = x[ok].astype(int), y[ok].astype(int)
    v = c[ok] * dens[ok, None] if np.ndim(dens) else c[ok] * dens
    np.add.at(F.img, (yi, xi), v)
    np.add.at(F.glow, (yi, xi), v * glow)
    np.add.at(F.img, (yi, xi + 1), v * 0.5)
    np.add.at(F.img, (yi + 1, xi), v * 0.5)


def sc_insight(F, t):
    """147.5 – 154.0：金色「投资启示」。粒子从四周旋转汇聚成字 → 实体金字 + 流光 → 冲击点上穿过镜头"""
    global _IP
    if _IP is None:
        _IP = _insight_particles()
    tx, ty, sx, sy, col, delay = _IP
    u = t - T_INSIGHT
    out = eio(ramp(t, T_VALUE - 0.55, T_VALUE))          # 冲击前 0.55 s：整体放大穿过镜头
    sc = 1 + 0.06 * ramp(t, T_INSIGHT + 2.5, T_VALUE - 0.55) + 2.2 * out ** 2
    A = 1 - out
    def S(x, y):                                           # 以字中心缩放
        return 540 + (x - 540) * sc, INS_Y + (y - INS_Y) * sc
    # 1) 粒子汇聚
    p = np.clip((u - 0.2 - delay) / 1.8, 0, 1); e = p * p * (3 - 2 * p)
    sw = (1 - e) * 2.2
    dx, dy = sx - 540, sy - INS_Y
    rx = dx * np.cos(sw) - dy * np.sin(sw); ry = dx * np.sin(sw) + dy * np.cos(sw)
    x = 540 + rx * (1 - e) + (tx - 540) * e; y = INS_Y + ry * (1 - e) + (ty - INS_Y) * e
    pa = ramp(u, 0, 0.3) * (1 - 0.85 * ramp(u, 2.0, 2.6)) * A
    if pa > 0:
        splat(F, *S(x, y), col, (1.3 + 0.9 * (1 - e)) * pa)
    # 2) 实体金字：汇聚完成时显现，随后流光扫过
    ta = eo(ramp(u, 1.9, 2.5)) * A
    if ta > 0:
        F.blob((540, INS_Y), 420 * sc, GOLD_D, 0.16 * ta)
        F.text3d('投资启示', 540, INS_Y, INS_SIZE * sc, 'serif_black', face=GOLD_GRAD, a=ta, glow=0.55, spec=ramp(u, 2.6, 4.2), track=0.08)
        if 1.9 < u < 2.9:
            uu = (u - 1.9) / 1.0
            F.circle((540, INS_Y), 200 + 700 * eo(uu), GOLD, ta * (1 - uu), 3, glow=1.2)
    # 3) 英文小标 + 两侧金线 + 副标题
    la = eo(ramp(u, 2.5, 3.3)) * A
    if la > 0:
        F.text('INVESTMENT  INSIGHTS', 540, INS_Y - 170 * sc, 30, 'corm', SUBGOLD, la, track=0.25)
        w = 330 * eo(ramp(u, 2.6, 3.6)) * sc
        F.line((540 - w, INS_Y + 150 * sc), (540 + w, INS_Y + 150 * sc), GOLD, la * 0.8, 2, glow=0.8)
        F.blob((540 - w, INS_Y + 150 * sc), 10, GOLD, la); F.blob((540 + w, INS_Y + 150 * sc), 10, GOLD, la)
        F.text_chars('巴菲特与芒格：价值投资的真谛', 540, INS_Y + 225 * sc, 44 * sc, 'serif_bold', SUBGOLD, A, t0=T_INSIGHT + 3.2, stag=0.06)
    if out > 0:
        F.flash = max(F.flash, 0.5 * out ** 3)


# ================================================================ 价值投资：巴菲特与芒格（拼接后的高潮乐段）
def vwin(t, t0, t1, fi=0.3, fo=0.3):
    return env(t, t0, t1 - 0.02, fi, fo)


def x_mark(F, c, r, col, a):
    F.line((c[0] - r, c[1] - r), (c[0] + r, c[1] + r), col, a, 4, glow=0.8)
    F.line((c[0] - r, c[1] + r), (c[0] + r, c[1] - r), col, a, 4, glow=0.8)


def sc_value(F, t):
    u = t - T_VALUE
    if u >= 0:
        F.flash = max(F.flash, 0.45 * math.exp(-u / 0.12))
        if u < 0.6:
            F.zoom = 1 + 0.035 * math.exp(-u / 0.18)
    # ---- 1) 同一个市场，换一种方法（冲击点）
    a1 = vwin(t, T_VALUE, T_BUFFETT, 0.15)
    if a1 > 0:
        F.text_chars('同一个市场，', 540, 300, 58, 'serif_black', INK, a1, t0=T_VALUE + 0.05, stag=0.04)
        two_tone(F, [('换一种方法，', INK), ('结果天差地别', GOLD_GRAD)], 540, 385, 58, 'serif_black', T_VALUE + 0.4, a1, stag=0.04, glow=0.25)
        for j, (lab, col, items) in enumerate(STORY['value_cmp']):
            y0 = 540 + j * 400
            F.glass(60, y0 - 50, 1020, y0 + 300, 34, a1 * eo(ramp(t, T_VALUE + 0.5 + j * 0.4, T_VALUE + 0.9 + j * 0.4)), tint=col, tint_a=0.09)
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
                       [(zero + L, y - 4), (zero, y - 4), (zero, y + 34), (zero + L, y + 34)], cc, ia * 0.85, glow=0.45)
                F.text(fmt_pct(mult - 1, 0), (zero + L + 18) if L >= 0 else (zero + 18), y + 15, 40, 'num', ret_col(mult - 1), ia, anchor='l', glow=0.3)
            F.line((400, y0 + 60), (400, y0 + 270), GOLD, a1 * 0.5, 2)
        ma = a1 * eo(ramp(t, T_VALUE + 2.6, T_VALUE + 3.1))
        F.text('利润支撑的上涨会延续，情绪推动的上涨终会回落', 540, 1400, 34, 'sans_black', GOLD_L, ma, glow=0.25)
        F.text('A股同样奖励价值：寒武纪利润兑现的那一年，股价 +107%', 540, 1470, 28, 'sans_reg', INK, ma * eo(ramp(t, T_VALUE + 3.3, T_VALUE + 3.8)))
        F.text('长期持有沪深300（含分红），十年也有 +56%', 540, 1520, 28, 'sans_reg', INK, ma * eo(ramp(t, T_VALUE + 3.6, T_VALUE + 4.1)))
    # ---- 2) 巴菲特：价格与价值
    a2 = vwin(t, T_BUFFETT, T_MUNGER)
    if a2 > 0:
        uq = t - T_BUFFETT
        halo(F, (540, 900), 400, t, a2 * 0.7, GOLD_D, th=2)
        F.text('“', 170, 600, 220, 'serif_black', a=a2 * 0.55, grad=GOLD_GRAD)
        F.text_chars('价格是你付出的，', 540, 800, 80, 'serif_black', INK, a2, t0=T_BUFFETT + 0.05, stag=0.05, dur=0.45)
        va = a2 * eo(ramp(uq, 0.75, 1.15))
        F.text3d('价值是你得到的。', 540, 940, 80 * pop(t, T_BUFFETT + 0.75, 0.15), 'serif_black', face=GOLD_GRAD, a=va, glow=0.5,
                 spec=ramp(uq, 1.2, 2.6))
        F.text('—— 沃伦 · 巴菲特', 900, 1060, 34, 'serif_med', SUBGOLD, a2 * eo(ramp(uq, 1.6, 2.1)), anchor='r')
        F.text('Price is what you pay. Value is what you get.', 540, 1160, 30, 'corm', SUBGOLD, a2 * 0.8 * eo(ramp(uq, 2.2, 2.8)))
        F.text('看清价值，才知道价格是贵还是便宜', 540, 1300, 36, 'sans_bold', INK, a2 * eo(ramp(uq, 3.2, 3.7)))
    # ---- 3) 芒格：反过来想
    a3 = vwin(t, T_MUNGER, T_PRIN)
    if a3 > 0:
        um = t - T_MUNGER
        F.text3d('反过来想，', 540, 430, 92 * pop(t, T_MUNGER, 0.2), 'serif_black', face=GOLD_GRAD, a=a3, glow=0.45)
        F.text3d('总是反过来想。', 540, 560, 92, 'serif_black', face=GOLD_GRAD, a=a3 * eo(ramp(um, 0.4, 0.8)), glow=0.45, spec=ramp(um, 0.9, 2.3))
        F.text('—— 查理 · 芒格', 900, 670, 34, 'serif_med', SUBGOLD, a3 * eo(ramp(um, 1.0, 1.4)), anchor='r')
        F.text('先想清楚：怎样最容易亏大钱？', 540, 820, 46, 'serif_bold', INK, a3 * eo(ramp(um, 1.6, 2.0)))
        for k, s in enumerate(['只看过去涨了多少', '在一片狂热中追高', '为情绪支付过高的价格']):
            tk = 2.4 + k * 0.8
            ka = a3 * eo(ramp(um, tk, tk + 0.35))
            if ka <= 0: continue
            y = 960 + k * 130; dx = (1 - eo(ramp(um, tk, tk + 0.4))) * 60
            F.glass(170 + dx, y - 50, 910 + dx, y + 50, 50, ka, tint=UP, tint_a=0.10, shadow=0.2, blur=12)
            x_mark(F, (240 + dx, y), 16, UP, ka)
            F.text(s, 300 + dx, y, 40, 'sans_bold', INK, ka, anchor='l')
        fa = a3 * eo(ramp(um, 5.0, 5.4))
        F.text('然后，避开它们。', 540, 1400, 56, 'serif_black', a=fa, grad=GOLD_GRAD, glow=0.4)
    # ---- 4) 四个原则：围绕「价值投资」光环逐拍点亮
    a4 = vwin(t, T_PRIN, T_TRUTH)
    if a4 > 0:
        up = t - T_PRIN
        C0 = (540, 1000)
        F.text('巴菲特与芒格的四条原则', 540, 400, 52, 'serif_black', INK, a4 * eo(ramp(up, 0, 0.4)))
        halo(F, C0, 150, t, a4, GOLD, th=3)
        F.text3d('价值', 540, C0[1] - 34, 66, 'serif_black', face=GOLD_GRAD, a=a4, glow=0.5)
        F.text3d('投资', 540, C0[1] + 44, 66, 'serif_black', face=GOLD_GRAD, a=a4, glow=0.5)
        pos = [(60, 540), (590, 540), (60, 1250), (590, 1250)]
        for k, ((hh, d), (x0, y0)) in enumerate(zip(STORY['principles'], pos)):
            tk = 0.4 + 0.8 * k
            pa = a4 * eo(ramp(up, tk, tk + 0.35))
            if pa <= 0: continue
            cx, cy = x0 + 215, y0 + 105
            # 从光环射向卡片的一道光
            q = eo(ramp(up, tk - 0.1, tk + 0.3))
            L0 = math.hypot(cx - C0[0], cy - C0[1]); ux, uy = (cx - C0[0]) / L0, (cy - C0[1]) / L0
            p0 = (C0[0] + ux * 185, C0[1] + uy * 185)               # 从光环外缘射出，不压住中间的字
            F.line(p0, (p0[0] + (cx - p0[0]) * q, p0[1] + (cy - p0[1]) * q), GOLD, pa * 0.6, 2, glow=1.0)
            F.glass(x0, y0, x0 + 430, y0 + 210, 34, pa, tint=GOLD, tint_a=0.10, spec=ramp(up, tk, tk + 1))
            F.text(hh, cx, y0 + 68, 50, 'serif_black', a=pa, grad=GOLD_GRAD, glow=0.35)
            for qn, ln in enumerate(d.split('\n')):
                F.text(ln, cx, y0 + 132 + qn * 38, 28, 'sans_reg', INK, pa)
            if up - tk < 0.5:
                F.circle((cx, cy), 60 + 260 * eo((up - tk) / 0.5), GOLD, pa * (1 - (up - tk) / 0.5), 2, glow=1.0)
    # ---- 5) 价值投资的真谛（尾段重拍，全片高潮，停留 10 秒）
    a5 = env(t, T_TRUTH, T_END + 0.2, 0.25, 0.45)
    if a5 > 0:
        ut = t - T_TRUTH
        if ut < 0.5:
            F.flash = max(F.flash, 0.35 * math.exp(-ut / 0.12))
        F.text('价值投资的真谛', 540, 480, 40, 'serif_bold', SUBGOLD, a5 * eo(ramp(ut, 0, 0.4)), track=0.3)
        w = 220 * eo(ramp(ut, 0.1, 0.9))
        F.line((540 - w, 545), (540 + w, 545), GOLD, a5 * 0.7, 2, glow=0.8)
        lines = STORY['final_msg']
        for q, ln in enumerate(lines):
            F.text_chars(ln, 540, 680 + q * 100, 56, 'serif_black', INK if q < 2 else GOLD_L, a5, t0=T_TRUTH + 0.3 + q * 1.6, stag=0.045, dur=0.5)
        tk = B(232)                                        # 185.72：最后一句金句
        ia = a5 * eo(ramp(t, tk, tk + 0.35))
        if ia > 0:
            uu = t - tk
            F.blob((540, 1150), 360, GOLD_D, 0.18 * ia)
            F.text3d('独立思考', 540, 1100, 120 * pop(t, tk, 0.25), 'serif_black', face=GOLD_GRAD, a=ia, glow=0.6, spec=ramp(uu, 0.3, 1.8), track=0.06)
            F.text3d('在狂热中保持理性', 540, 1250, 76, 'serif_black', face=GOLD_GRAD, a=a5 * eo(ramp(uu, 0.5, 0.9)), glow=0.5,
                     spec=ramp(uu, 0.9, 2.4))
            if uu < 0.9:
                F.circle((540, 1160), 120 + 900 * eo(uu / 0.9), GOLD, ia * (1 - uu / 0.9), 4, glow=1.4)
                F.shake = (math.sin(uu * 80) * 6 * math.exp(-uu / 0.12), 0.0)
        F.text('数据：Yahoo Finance、腾讯证券、东方财富、中证指数；回测脚本与明细见项目目录', 540, 1840, 19, 'sans_reg', FAINT, a5 * eo(ramp(ut, 2, 3)))


# ================================================================ end card（品牌片尾，参考诺贝尔经济学奖视频的片尾）
LOGO_PX = 220
LOGO_RGB, LOGO_A = load_logo(LOGO_PX)          # 官方 logo（brand/logo_baman.png）
LOGO_Y = 760
N_LP = 6000
_LP = None


def _logo_particles():
    """起点 = 上一幕金句「独立思考 / 在狂热中保持理性」的字形像素（金句化作金粒子），终点 = 官方 logo 透明通道采样"""
    rng = np.random.default_rng(42)
    ys, xs = np.where(LOGO_A > 0.4)
    w = LOGO_A[ys, xs].astype(np.float64)
    k = rng.choice(len(xs), N_LP, replace=len(xs) < N_LP, p=w / w.sum())
    tx = xs[k] + rng.random(N_LP) - 0.5 + (540 - LOGO_PX / 2)
    ty = ys[k] + rng.random(N_LP) - 0.5 + (LOGO_Y - LOGO_PX / 2)
    col = LOGO_RGB[ys[k], xs[k]]
    n1 = N_LP * 3 // 5
    x1, y1, v1 = _text_particles('独立思考', 'serif_black', 120, 540, 1100, n1, 1)
    x2, y2, v2 = _text_particles('在狂热中保持理性', 'serif_black', 76, 540, 1250, N_LP - n1, 2)
    sx, sy = np.r_[x1, x2], np.r_[y1, y2]
    scol = _gold_at(np.r_[v1, v2])
    return tx, ty, sx, sy, col, scol, rng.uniform(0, 0.5, N_LP), rng.normal(0, 1, (N_LP, 2))


def sc_end(F, t):
    global _LP
    if _LP is None:
        _LP = _logo_particles()
    tx, ty, sx, sy, col, scol, delay, drift = _LP
    u = t - T_END
    # 顶部聚光
    BGR.beams(F, t, (0.55, 0.7, 1.0), a=0.7 * ramp(u, 0, 1.5), n=3, spread=0.25, seed=11)
    # 1) 金句化作粒子，旋转汇聚成官方 logo
    dur = T_LOGO - T_END
    p = np.clip((u - delay) / (dur - 0.55), 0, 1)
    e = p * p * (3 - 2 * p)
    sw = np.sin(np.pi * e) * 1.4                          # 起止都不旋转：粒子从金句原位出发，精确落到 logo 上
    cxp, cyp = sx - 540, sy - LOGO_Y
    rx = cxp * np.cos(sw) - cyp * np.sin(sw); ry = cxp * np.sin(sw) + cyp * np.cos(sw)
    x = 540 + rx * (1 - e) + (tx - 540) * e; y = LOGO_Y + ry * (1 - e) + (ty - LOGO_Y) * e
    k = eo(ramp(t, T_LOGO + 0.2, T_LOGO + 2.5))
    x = x + drift[:, 0] * 140 * k; y = y + drift[:, 1] * 140 * k
    pa = ramp(u, 0, 0.3) * (1 - 0.8 * ramp(t, T_LOGO - 0.1, T_LOGO + 0.4)) * (1 - ramp(t, T_LOGO + 1.5, T_FADE))
    if pa > 0:
        c = scol * (1 - e[:, None]) + col * e[:, None]
        splat(F, x, y, c, (1.0 - 0.45 * e) * pa)
    # 2) 官方 logo：由虚到实浮现
    la = eo(ramp(t, T_LOGO - 0.15, T_LOGO + 0.6))
    if la > 0:
        sc = 1 + 0.05 * (1 - eo(ramp(t, T_LOGO - 0.15, T_LOGO + 1.4)))
        px = int(LOGO_PX * sc)
        rgb, al = load_logo(px) if px != LOGO_PX else (LOGO_RGB, LOGO_A)
        bl = (1 - eo(ramp(t, T_LOGO - 0.15, T_LOGO + 0.5))) * 12
        if bl > 0.5:
            al = cv2.GaussianBlur(al, (0, 0), bl)
        F.blob((540, LOGO_Y), 120, (110 / 255, 175 / 255, 1.0), 0.14 * la)     # 很淡的蓝色光晕（品牌规范）
        F.over(al, 540 - px // 2, LOGO_Y - px // 2, rgb, la)
        if t > T_LOGO:
            uu = t - T_LOGO
            F.circle((540, LOGO_Y), 130 + 380 * eo(uu / 1.4), (110 / 255, 175 / 255, 1.0), la * (1 - ramp(uu, 0, 1.4)) * 0.7, 3, glow=1.0)
            F.flash = max(F.flash, 0.14 * math.exp(-uu / 0.1))
    # 3) 金色「巴芒价值」：重拍上擦出，流光扫过；两侧细金线
    if t >= T_GOLD - 0.02:
        w = eo(ramp(t, T_GOLD, T_GOLD + 0.8))
        sp = ramp(t, T_GOLD + 0.9, T_GOLD + 2.3)
        tw = F.text('巴芒价值', 540, 1010, 124, 'serif_black', a=1.0, grad=GOLD_GRAD, glow=0.35, wipe=w, shine=sp, shadow=0.5, track=0.06)
        hw = tw / 2 + 36
        ln = 120 * eo(ramp(t, T_GOLD + 0.3, T_GOLD + 1.3))
        for sg in (-1, 1):
            F.line((540 + sg * hw, 1008), (540 + sg * (hw + ln), 1008), SUBGOLD, 0.8, 2, glow=0.4)
        ws = eo(ramp(t, T_SUB, T_SUB + 0.8))
        sub = 'BUFFETT · MUNGER'
        fs = 32
        f = font('corm', fs)
        nat = sum(f.getlength(ch) for ch in sub)
        tr = (tw - nat) / (len(sub) - 1)
        xc = 540 - tw / 2
        for ch in sub:
            ca = cl((ws * (tw + 120) - (xc - (540 - tw / 2))) / 120)
            F.text(ch, xc, 1108, fs, 'corm', SUBGOLD, ca, anchor='l')
            xc += f.getlength(ch) + tr
    # 4) 细金线 + 一行金色关注语
    la2 = ramp(t, T_FOLLOW, T_FOLLOW + 0.6)
    if la2 > 0:
        w = 60 * eo(la2)
        F.line((540 - w, 1190), (540 + w, 1190), GOLD, 0.85, 2, glow=0.8)
        parts = [('关注', SUBGOLD), ('「巴芒价值」', GOLD_GRAD), ('，传承大师智慧，领悟投资真谛', SUBGOLD)]
        two_tone(F, parts, 540, 1262, 38, 'serif_med', T_FOLLOW + 0.25, 1.0, stag=0.03, glow=0.15)


# ================================================================ frame
SCENES = [(0, T_TITLE + 0.1, sc_hook), (T_TITLE - 0.05, T_RULES + 0.1, sc_title), (T_RULES, year_t0(0) + 0.1, sc_rules),
          (year_t0(0) - 0.1, T_RACE_END + 0.3, sc_race), (T_FINAL, T_BREAK + 0.5, sc_final),
          (T_BREAK - 0.1, T_WHY + 0.1, sc_break), (T_WHY - 0.1, T_INSIGHT + 0.1, sc_why),
          (T_INSIGHT - 0.1, T_VALUE + 0.05, sc_insight), (T_VALUE - 0.1, T_END + 0.5, sc_value), (T_END - 0.1, T_TOTAL + 1, sc_end)]


# 每段的星云配色（关键帧之间平滑过渡）
CRIMSON, MAGENTA, TEAL, AMBER = hexc('#C2185B'), hexc('#B5179E'), hexc('#00B3A4'), hexc('#E08A1E')
PALETTE = [(0, VIOLET, CRIMSON), (T_TITLE, GOLD_D, CRIMSON), (T_RULES, US2, TEAL), (year_t0(0), US2, CN2), (T_BREAK, VIOLET, US2),
           (T_WHY, GOLD_D, TEAL), (WHY_T[1], VIOLET, TEAL), (WHY_T[2], CRIMSON, MAGENTA), (WHY_T[3], AMBER, CRIMSON), (WHY_T[4], US2, TEAL), (WHY_T[5], MAGENTA, VIOLET), (T_INSIGHT, GOLD_D, AMBER), (T_VALUE, AMBER, US2), (T_BUFFETT, GOLD_D, MAGENTA),
           (T_MUNGER, AMBER, CRIMSON), (T_PRIN, GOLD_D, TEAL), (T_TRUTH, GOLD, AMBER), (T_END, US2, VIOLET)]


def bg_colors(t):
    k = max(i for i, p in enumerate(PALETTE) if p[0] <= t + 1e-6)
    _, a1, a2 = PALETTE[k]
    if k:
        x = eio(ramp(t, PALETTE[k][0] - 0.1, PALETTE[k][0] + 0.9))
        a1, a2 = lerpc(PALETTE[k - 1][1], a1, x), lerpc(PALETTE[k - 1][2], a2, x)
    return a1, a2


def scene_fx(F, t):
    """全片的炫光层：粒子地面 / 体积光 / 金尘 / 转场光晕（各段配色不同）"""
    H0 = HOOK[1]
    if t < T_TITLE:
        BGR.field(F, t, GOLD, CN, a=0.9 * (1 - 0.6 * (H0 <= t < HOOK[2])), horizon=1330 if H0 <= t < HOOK[2] else 1420)
        BGR.beams(F, t, GOLD_D, a=0.35)
        BGR.dust(F, t, GOLD, a=0.8)
    elif t < T_RULES:
        u = t - T_TITLE
        BGR.beams(F, t, GOLD, a=0.4 + 0.8 * math.exp(-u / 1.2), n=6)
        BGR.field(F, t, GOLD, CN2, a=0.9, horizon=1420, speed=1.0)
        BGR.dust(F, t, GOLD, a=1.0, rise=40)
    elif t < year_t0(0):
        BGR.field(F, t, US, TEAL, a=0.6, horizon=1650)
        BGR.dust(F, t, US, a=0.5)
    elif t < T_FINAL:
        BGR.dust(F, t, (0.7, 0.85, 1.0), a=0.45)
    elif t < T_BREAK:
        BGR.beams(F, t, US2, a=0.45, n=4, seed=4)
        BGR.dust(F, t, (0.7, 0.85, 1.0), a=0.5)
    elif t < T_WHY:
        BGR.beams(F, t, VIOLET, a=0.4 * ramp(t, T_BREAK, T_BREAK + 1.5), n=4)
    elif t < T_INSIGHT:
        c1, c2 = bg_colors(t)
        BGR.beams(F, t, c2, a=0.4, n=4, seed=6)
        BGR.field(F, t, c1, c2, a=0.55, horizon=1720, speed=0.4)
        BGR.dust(F, t, (0.6, 1.0, 0.95), a=0.45)
    elif t < T_VALUE:
        u = t - T_INSIGHT
        BGR.beams(F, t, GOLD, a=ramp(u, 0.3, 2.5) * 1.1, n=6, seed=5)
        BGR.field(F, t, GOLD, AMBER, a=ramp(u, 0, 2.0), horizon=1450, speed=0.5 + 6 * ramp(t, T_VALUE - 0.6, T_VALUE))
        BGR.dust(F, t, GOLD, a=ramp(u, 0, 1.5), rise=25 + 120 * ramp(t, T_VALUE - 0.6, T_VALUE))
    elif t < T_END:
        hi = t >= T_BUFFETT
        BGR.field(F, t, GOLD, US if not hi else AMBER, a=0.5 if t < T_BUFFETT else 0.85, horizon=1620 if t < T_BUFFETT else 1500,
                  speed=0.6 + 0.8 * (t >= T_TRUTH))
        if hi:
            BGR.beams(F, t, GOLD, a=0.6 + 0.6 * (t >= T_TRUTH) * math.exp(-max(t - T_TRUTH, 0) / 4), n=5, seed=8)
        BGR.dust(F, t, GOLD, a=0.9, rise=30 + 20 * (t >= T_TRUTH))
    else:
        BGR.dust(F, t, (0.85, 0.8, 0.6), a=0.6 * (1 - ramp(t, T_FOLLOW, T_FADE)))
    # 转场光晕：章节切换的重拍上扫过一道横向光
    for tb, y, col in [(T_TITLE, 860, GOLD), (T_RULES, 300, GOLD), (year_t0(0), 190, US), (T_FINAL, 250, GOLD), (T_WHY, 305, GOLD), (WHY_T[1], 305, GOLD_L), (WHY_T[2], 305, UP), (WHY_T[3], 305, CN), (WHY_T[4], 305, US), (WHY_T[5], 305, MAGENTA),
                       (T_VALUE, 900, GOLD), (T_BUFFETT, 900, GOLD), (T_MUNGER, 430, GOLD), (T_PRIN, 1000, GOLD), (T_TRUTH, 545, GOLD)]:
        u = t - tb
        if -0.05 < u < 0.7:
            BGR.flare(F, y, col, a=math.exp(-max(u, 0) / 0.22) * 0.9, length=0.4 + 0.8 * eo(cl(u / 0.4)))


def render(t, idx=0):
    c1, c2 = bg_colors(t)
    base = BGR.nebula(t, c1, c2, amt=1.5)
    F = Frame(t, base)
    BGR.stars(F, t, speed=0.015, a=0.8, warp=max(0.0, 1 - abs(t - T_TITLE) / 0.6) * 1.5)
    scene_fx(F, t)
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
