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
def two_tone(F, parts, x, y, size, fname, t0, a=1.0, stag=0.045, glow=0.0, blur_in=False):
    """一行里不同颜色的几段文字，整体居中，逐字出现。parts=[(文字, 颜色或渐变), ...]"""
    total = sum(text_w(s, fname, int(size)) for s, _ in parts)
    cx = x - total / 2; k = 0
    for s, c in parts:
        grad = c if isinstance(c, list) else None
        F.text_chars(s, cx, y, size, fname, c if grad is None else WHITE, a, anchor='l', t0=t0 + k * stag, stag=stag,
                     glow=glow, grad=grad, blur_in=blur_in)
        cx += text_w(s, fname, int(size)); k += len(s)


def spin_number(t, seed):
    """账户余额「老虎机」：每帧随机跳动的数字"""
    rng = np.random.default_rng(int(t * FPS) * 7 + seed)
    v = 10 ** rng.uniform(-0.5, 3.4)
    return f'{v:,.1f}' if v < 100 else f'{v:,.0f}'


HOOK = [0.0, B(8), B(12), T_TITLE]          # 三屏：结果 / 差距 / 悬念（落在小节强拍）


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
    """0 – 12.9 s：结果先行的悬念钩子。三屏，落在音乐的强拍上，每屏只讲一件事并留足停留时间"""
    UT, CT = STORY['us_total'], STORY['cn_total']
    BASE = 1330; K = 300                        # 光柱基线 / 每 10 倍的高度
    # ① 同样的起点 → 十年后：一个冲上云霄，一个跌穿地板（0 – 6.5 s）
    a = hwin(t, 0, fi=0.06, fo=0.25)
    if a > 0:
        F.text_chars('同样的 10 万本金', 540, 330, 72, 'serif_black', INK, a, t0=0.05, stag=0.06)
        two_tone(F, [('同一个策略，坚持 ', INK), ('10 年', GOLD_GRAD)], 540, 440, 56, 'serif_black', B(1), a, stag=0.05, glow=0.25)
        ga = a * eo(ramp(t, B(2), B(2) + 0.5))
        F.line((80, BASE), (1000, BASE), GOLD, ga * 0.7, 2, glow=0.6)
        F.text('起点 10 万', 1000, BASE + 30, 22, 'sans_reg', GOLD, ga * 0.8, anchor='r')
        p = ramp(t, B(3), B(5) + 0.2)                  # 两根光柱按真实的逐年资金走完十年（约 1.8 s），在第 5 拍附近落定
        yi = p * 10
        if 0 < p < 1:
            F.text(str(2016 + min(9, int(yi))), 540, 1450, 48, 'num', GOLD, a, glow=0.4)
        for j, (key, col) in enumerate([('us', US), ('cn', CN)]):
            cx = 300 + j * 480
            caps = [1.0] + [yy[key]['cap'] for yy in STORY['years']]
            i0 = min(9, int(yi)); f = yi - i0
            cur = 10 ** (math.log10(caps[i0]) * (1 - f) + math.log10(caps[i0 + 1]) * f)
            h = K * math.log10(cur)
            x0, x1 = cx - 80, cx + 80
            if h >= 0:
                F.fill([(x0, BASE - max(h, 3)), (x1, BASE - max(h, 3)), (x1, BASE), (x0, BASE)], col, ga * 0.55, glow=0.5)
                F.line((x0, BASE - h), (x1, BASE - h), lerpc(col, WHITE, 0.6), ga, 4, glow=1.5)
                F.blob((cx, BASE - h), 110, col, 0.35 * ga)
                ny = BASE - h - 80
            else:
                F.fill([(x0, BASE), (x1, BASE), (x1, BASE - h), (x0, BASE - h)], mix(CN2, 0.8), ga * 0.5, glow=0.4)
                F.line((x0, BASE - h), (x1, BASE - h), CN2, ga, 4, glow=1.2)
                ny = BASE - h + 80
            done = ramp(t, B(5) + 0.2, B(5) + 0.3)
            big_money(F, cur, cx, ny, 96 * pop(t, B(5) + 0.2, 0.3) if done > 0 else 84, lerpc(col, WHITE, 0.35), ga, glow=0.5 + 0.4 * done)
            F.text(f'账户 {"①②"[j]}', cx, BASE + (40 if h >= 0 else -40), 30, 'sans_bold', col, ga)
            if 0 < t - B(5) < 0.6:
                u = (t - B(5)) / 0.6
                F.circle((cx, ny), 60 + 260 * eo(u), col, ga * (1 - u), 3, glow=1.0)
        F.text('十年后', 540, 1450, 40, 'sans_bold', INK, a * eo(ramp(t, B(5) + 0.2, B(5) + 0.5)))
    # ② 相差 1,332 倍（6.5 – 9.7 s）
    a = hwin(t, 1, fi=0.08, fo=0.25)
    if a > 0:
        u = t - HOOK[1]
        F.text('两个账户相差', 540, 700, 52, 'serif_black', INK, a)
        F.text3d(f"{STORY['gap']:,.0f}", 470, 900, 230 * pop(t, HOOK[1], 0.4), 'num', face=GOLD_GRAD, a=a, glow=0.55, spec=ramp(u, 0.2, 1.4))
        F.text('倍', 470 + text_w(f"{STORY['gap']:,.0f}", 'num', 230) / 2 + 70, 930, 110, 'serif_black', a=a, grad=GOLD_GRAD, glow=0.4)
        if u < 0.8:
            F.circle((540, 900), 100 + 800 * eo(u / 0.8), GOLD, a * (1 - u / 0.8), 5, glow=1.2)
            F.zoom = 1 + 0.03 * math.exp(-u / 0.15)
            F.shake = (math.sin(u * 90) * 10 * math.exp(-u / 0.12), 0.0)
        F.text('规则只有一条', 540, 1130, 36, 'sans_med', DIM, a * eo(ramp(u, 0.8, 1.2)))
        two_tone(F, [('每年买入上一年的', INK), ('涨幅冠军', GOLD_GRAD)], 540, 1215, 58, 'serif_black', HOOK[1] + 1.0, a, glow=0.25)
    # ③ 一个美股，一个 A 股 —— 你猜？（9.7 – 12.9 s）
    a = hwin(t, 2, fi=0.08, fo=0.12)
    if a > 0:
        two_tone(F, [('一个投 ', INK), ('美股', [(0, US), (1, US2)]), ('，一个投 ', INK), ('A 股', [(0, CN), (1, CN2)])],
                 540, 800, 64, 'serif_black', HOOK[2] + 0.02, a, stag=0.04, glow=0.3)
        tq = HOOK[2] + 1.2
        qa = a * eo(ramp(t, tq, tq + 0.35))
        F.text3d('你猜，哪个是 A 股？', 540, 990, 92 * pop(t, tq, 0.25), 'serif_black', face=GOLD_GRAD, a=qa, glow=0.45,
                 spec=ramp(t, tq + 0.2, tq + 1.2))


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
         dict(key='cn', x0=550, x1=1040, col=CN, col2=CN2, label='A股', sub='沪深全A冠军（剔除次新）')]
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
    F.text_chars('为什么差距这么大？', 540, 760, 80, 'serif_black', INK, a, t0=T_BREAK + 0.5, stag=0.08, dur=0.6, blur_in=True)
    two_tone(F, [('同样「追强」，美股是', INK), ('财富密码', GOLD_GRAD)], 540, 900, 46, 'serif_black', B(131), a, stag=0.05, blur_in=True)
    two_tone(F, [('A股却是', INK), ('绞肉机', [(0, lerpc(DOWN, WHITE, 0.4)), (1, DOWN)])], 540, 975, 46, 'serif_black', B(132.5), a, stag=0.05, blur_in=True)
    two_tone(F, [('答案，藏在冠军的「', DIM), ('第二年', GOLD_GRAD), ('」里', DIM)], 540, 1090, 36, 'serif', B(134), a, stag=0.04)


# ================================================================ why：从第一性原理讲清差异（v5：12 个整屏镜头，每 4 拍一个）
# 每个原因拆成两个镜头；每个镜头只有一个标题 + 一个主视觉 + 一句结论，前一个镜头完全淡出后下一个才出现。
WHY_SHOT_T = [T_WHY] + [B(k) for k in range(144, 201, 8)]      # 9 个边界 → 8 个镜头，每个 8 拍
WHY_SLOW = 1.4          # 镜头内动画放慢 1.4 倍：约 3 秒搭建完成，其余时间留给阅读
SHOT_T0 = 0.0
CH_COL = [US, GOLD, hexc('#FF5C7A'), GOLD_L]


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
    """顶部四步进度：第二年 · 代价 · 利润 · 真相（当前一步高亮）"""
    for j, nm in enumerate(STEP_NAMES):
        cx = 540 + (j - 1.5) * 230
        on = j == ch
        col = CH_COL[j] if j <= ch else FAINT
        F.text(nm, cx, 182, 28 if on else 24, 'sans_black' if on else 'sans_med', col, a * (1 if j <= ch else 0.7), glow=0.4 if on else 0)
        F.line((cx - 60, 218), (cx + 60, 218), col, a * (1 if j <= ch else 0.5), 4 if on else 2, glow=0.9 if on else 0)
        if j < 3:
            F.text('›', cx + 115, 182, 26, 'num', FAINT, a * 0.8)


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


def rich_head(F, t0, s, a, y=305, size=62):
    """标题：【】内为金色关键词；逐字由虚到实聚焦"""
    parts, gold = [], False
    for seg in s.replace('】', '【').split('【'):
        if seg:
            parts.append((seg, GOLD_GRAD if gold else INK))
        gold = not gold
    two_tone(F, parts, 540, y, size, 'serif_black', t0 + 0.05, a, stag=0.04, glow=0.2, blur_in=True)


def sub_line(F, t0, s, a, y=385):
    F.text(s, 540, y, 28, 'sans_reg', DIM, a * eo(ramp(F.t, t0 + 0.5, t0 + 0.9)))


def takeaway(F, s, y, a, size=46):
    """镜头底部的结论句：金色渐变 + 一道细金线自中间展开"""
    if a <= 0.01: return
    w = text_w(s, 'serif_black', size)
    F.text(s, 540, y, size, 'serif_black', a=a, grad=GOLD_GRAD, glow=0.35, shadow=0.4)
    lw = (w / 2 + 30) * eo(a)
    F.line((540 - lw, y + size * 0.85), (540 + lw, y + size * 0.85), GOLD, a * 0.6, 2, glow=0.8)


def pill(F, x, y, s, col, a, w=170):
    F.glass(x - w / 2, y - 34, x + w / 2, y + 34, 34, a, tint=col, tint_a=0.18, shadow=0.2, blur=10)
    F.text(s, x, y, 38, 'num', lerpc(col, WHITE, 0.25), a, glow=0.35)


# ---------------------------------------------------------------- 03 第一性原理
# ---------------------------------------------------------------- ① 第二年
def mini_bars(F, u, a, y0, lab, col, vals, bench, stat, stat_col, t0, hy):
    K = 130
    F.text(lab, 80, hy, 36, 'sans_black', col, a, anchor='l', glow=0.2)
    F.line((80, y0), (1000, y0), WHITE, a * 0.3, 1)
    for k, (v, b) in enumerate(zip(vals, bench)):
        tk = t0 + k * 0.06
        p = eo(ramp(u, tk, tk + 0.5)); ba = a * eo(ramp(u, tk, tk + 0.2))
        x = 112 + k * 88
        h = max(-0.6, min(v, 1.75)) * K * p
        big_loss = v <= -0.3
        gbar(F, x, x + 60, y0, h, DOWN if v < 0 else col, ba, refl=False, glow=0.7 if big_loss else 0.5)
        F.text(pct0(v * p), x + 30, y0 - max(h, 0) - 24 if v >= 0 else y0 - h + 26, 20, 'num_semi',
               lerpc(DOWN if v < 0 else col, WHITE, 0.3), ba)
        if big_loss:
            F.text('重挫', x + 30, y0 - h + 62, 22, 'sans_black', DOWN, ba * eo(ramp(u, t0 + 1.0, t0 + 1.3)), glow=0.6)
        bh = max(-0.6, min(b, 1.75)) * K
        F.line((x - 6, y0 - bh), (x + 66, y0 - bh), WHITE, ba * 0.8, 2, glow=0.5)
    F.text(stat, 1000, hy, 36, 'sans_black', stat_col, a * eo(ramp(u, t0 + 1.0, t0 + 1.4)), anchor='r', glow=0.35)


def shot_second_year(F, t, u, a):
    w = STORY['why']; st = STORY['stats']
    rich_head(F, SHOT_T0, '同样是冠军，第二年【天差地别】', a, size=58)
    sub_line(F, SHOT_T0, '柱子 = 买入那一年的实际收益　白线 = 同期指数', a)
    (_, uc, uy, ub), (_, cc, cy, cb) = w['groups']
    mini_bars(F, u, a, 800, '美股冠军', uc, uy, ub, f"10 年 {st['us_beat']} 年跑赢指数", UP, 0.2, 470)
    mini_bars(F, u, a, 1190, 'A股冠军', cc, cy, cb, f"10 年 {st['cn_loss']} 年亏损", DOWN, 0.9, 940)
    for k in range(10):
        F.text(str(2016 + k), 142 + k * 88, 1375, 18, 'num_reg', DIM, a)
    takeaway(F, f"美股冠军还在涨，A股冠军 {st['cn_big_loss']} 次跌掉三成以上", 1510, a * eo(ramp(u, 2.4, 2.8)), size=40)


# ---------------------------------------------------------------- ② 利润：第一性原理
def shot_formula(F, t, u, a):
    rich_head(F, SHOT_T0, '股价，长期只认一件事：【利润】', a, size=58)
    sub_line(F, SHOT_T0, '第一性原理：把股价拆开看', a)
    tiles = [('股价', INK, 150), ('利润', UP, 540), ('估值', GOLD, 930)]
    for k, (s, c, x) in enumerate(tiles):
        tk = 0.2 + k * 0.25
        ia = a * eo(ramp(u, tk, tk + 0.35))
        dy = (1 - eback(ramp(u, tk, tk + 0.5))) * -80
        wob = 1 + (0.06 * math.sin(u * 7.5) * ramp(u, 1.3, 1.7) if s == '估值' else 0)
        grow = 1 + (0.08 * eo(ramp(u, 1.3, 1.9)) if s == '利润' else 0)
        w = 128 * wob * grow
        F.glass(x - w, 640 - 92 * wob * grow + dy, x + w, 640 + 92 * wob * grow + dy, 34, ia, tint=c, tint_a=0.16, shadow=0.35, blur=16, spec=ramp(u, tk, tk + 1))
        F.text(s, x, 640 + dy, 84 * wob * grow, 'serif_black', c if s != '股价' else INK, ia, glow=0.45)
    for s, x, tk in (('=', 345, 0.45), ('×', 735, 0.7)):
        F.text(s, x, 640, 84, 'num', DIM, a * eo(ramp(u, tk, tk + 0.3)))
    for k, (c, x, l1, l2) in enumerate([(UP, 540, '利润：企业真实赚到的钱', '长期决定股价的方向'), (GOLD, 930, '估值：市场愿意出的倍数', '短期随情绪剧烈摇摆')]):
        tk = 1.2 + k * 0.4
        ka = a * eo(ramp(u, tk, tk + 0.35))
        x0 = 70 + k * 480; x1 = x0 + 460; cx = (x0 + x1) / 2
        q = eo(ramp(u, tk - 0.15, tk + 0.25))
        arrow(F, (x, 800), (x + (cx - x) * q, 800 + (905 - 800) * q), c, ka * 0.85, 3, 14)
        F.glass(x0, 920, x1, 1120, 34, ka, tint=c, tint_a=0.12, shadow=0.25, blur=12, spec=ramp(u, tk, tk + 1))
        F.text(l1, cx, 990, 32, 'sans_black', c, ka, glow=0.25)
        F.text(l2, cx, 1060, 28, 'sans_reg', INK, ka)
    takeaway(F, '情绪能把股价推上去，只有利润能托住它', 1320, a * eo(ramp(u, 2.1, 2.5)), size=44)


def shot_scatter(F, t, u, a):
    rich_head(F, SHOT_T0, '冠军的第二年，跟着【利润】走', a)
    sub_line(F, SHOT_T0, '20 只冠军：持有当年的利润变化（横）vs 股价收益（纵）', a)
    gx0, gx1, gy0, gy1 = 130, 990, 480, 1260
    def X(g): return gx0 + (cl((math.copysign(math.log1p(abs(g) * 2), g) + 1.2) / 4.6)) * (gx1 - gx0)
    def Y(r): return gy1 - cl((r + 0.75) / 2.55) * (gy1 - gy0)
    ga = a * eo(ramp(u, 0.1, 0.5))
    F.line((X(0), gy0), (X(0), gy1), WHITE, ga * 0.35, 1); F.line((gx0, Y(0)), (gx1, Y(0)), WHITE, ga * 0.35, 1)
    qa = a * eo(ramp(u, 0.4, 0.9))
    F.fill([(X(0), gy0), (gx1, gy0), (gx1, Y(0)), (X(0), Y(0))], UP, qa * 0.07, mode='add')
    F.fill([(gx0, Y(0)), (X(0), Y(0)), (X(0), gy1), (gx0, gy1)], DOWN, qa * 0.07, mode='add')
    F.text('利润涨 → 股价涨', gx1 - 10, gy0 + 24, 26, 'sans_bold', UP, qa, anchor='r')
    F.text('利润变化 →', gx1, Y(0) + 26, 20, 'sans_reg', DIM, ga, anchor='r')
    F.text('股价 ↑', X(0) + 10, gy0 + 10, 20, 'sans_reg', DIM, ga, anchor='l')
    lab = {('us', 2024): '英伟达', ('us', 2021): '特斯拉', ('us', 2023): '西方石油', ('cn', 2017): '四川双马：利润涨，股价跌',
           ('cn', 2023): '绿康生化：亏损扩大', ('cn', 2025): '寒武纪：扭亏', ('cn', 2021): '英科医疗'}
    for k, p in enumerate(STORY['why']['scatter']):
        tk = 0.6 + k * 0.07
        pa = a * eo(ramp(u, tk, tk + 0.3))
        if pa <= 0: continue
        g = 6.0 if p['turn'] else (-0.9 if p['loss'] else (p['growth'] if p['growth'] is not None else 0))
        col = US if p['mk'] == 'us' else CN
        x, y = X(g), Y(p['ret'])
        F.blob((x, y), 44, col, 0.35 * pa)
        F.circle((x, y), 13 * (1 + 0.6 * math.exp(-max(u - tk, 0) / 0.15)), lerpc(col, WHITE, 0.3), pa, fill=True, glow=1.0)
        s = lab.get((p['mk'], p['year']))
        if s:
            right = x > 700
            F.text(s, x + (-22 if right else 22), y - 24, 22, 'sans_bold', col, pa * eo(ramp(u, 2.0, 2.4)), anchor='r' if right else 'l')
    la = a * eo(ramp(u, 0.6, 1.0))
    F.circle((140, 1330), 10, US, la, fill=True, glow=1); F.text('美股冠军', 160, 1330, 26, 'sans_med', US, la, anchor='l')
    F.circle((360, 1330), 10, CN, la, fill=True, glow=1); F.text('A股冠军', 380, 1330, 26, 'sans_med', CN, la, anchor='l')
    takeaway(F, '利润跟不上的，股价都回去了', 1450, a * eo(ramp(u, 2.6, 3.0)), size=46)


def eq_row(F, y, col, lab, vals, a, u, tk):
    """一行拆解：[利润 x%] × [估值 y%] → [股价 z%]"""
    ka = a * eo(ramp(u, tk, tk + 0.35))
    if ka <= 0: return
    F.text(lab, 80, y - 120, 38, 'sans_black', col, ka, anchor='l', glow=0.25)
    xs = [190, 540, 890]
    for j, (nm, v) in enumerate(vals):
        q = eo(ramp(u, tk + 0.2 + j * 0.35, tk + 0.6 + j * 0.35))
        c = (UP if v >= 0 else DOWN) if j != 1 else (GOLD if v >= 0 else lerpc(DOWN, GOLD, 0.3))
        F.glass(xs[j] - 150, y - 75, xs[j] + 150, y + 85, 30, ka * q, tint=c, tint_a=0.14, shadow=0.25, blur=12)
        F.text(nm, xs[j], y - 38, 26, 'sans_med', DIM, ka * q)
        F.text(pct0(v * q), xs[j], y + 26, 60, 'num', c, ka * q, glow=0.45)
    F.text('×', 365, y + 10, 52, 'num', DIM, ka * eo(ramp(u, tk + 0.5, tk + 0.7)))
    F.text('→', 715, y + 10, 52, 'num', DIM, ka * eo(ramp(u, tk + 0.85, tk + 1.05)))


def shot_decomp(F, t, u, a):
    w = STORY['why']; d = w['decomp']; ex = w['examples']
    rich_head(F, SHOT_T0, '美股靠【利润】涨，A股被【估值】拖垮', a, size=56)
    sub_line(F, SHOT_T0, '冠军持有当年的收益拆解（10 只冠军的中位数）', a)
    eq_row(F, 640, US, '美股冠军', [('利润', d['us']['profit']), ('估值', d['us']['pe']), ('股价', d['us']['ret'])], a, u, 0.2)
    n, g, pe, r = ex['us'][0]
    F.text(f'例：{n} 2020 年，利润 ×{1 + g:.1f}，估值 {pct0(pe)}，股价 {pct0(r)}', 540, 765, 26, 'sans_reg', INK, a * eo(ramp(u, 1.4, 1.8)))
    eq_row(F, 1020, CN, 'A股冠军', [('利润', d['cn']['profit']), ('估值', d['cn']['pe']), ('股价', d['cn']['ret'])], a, u, 1.0)
    n, g, pe, r = ex['cn'][0]
    F.text(f'例：{n} 2017 年，利润 {pct0(g)}，估值 {pct0(pe)}，股价 {pct0(r)}', 540, 1145, 26, 'sans_reg', INK, a * eo(ramp(u, 2.2, 2.6)))
    takeaway(F, '利润跑得比估值回落更快，股价才能涨', 1300, a * eo(ramp(u, 2.6, 3.0)), size=44)
    F.text(f"美股冠军利润 10 年 {d['us']['up']} 年增长　·　A股冠军只有 {d['cn']['up']} 年", 540, 1400, 30, 'sans_bold', INK,
           a * eo(ramp(u, 2.9, 3.3)))


# ---------------------------------------------------------------- ③ 根源：为什么美股的利润能延续，A股不能
def spark_card(F, x0, y0, arc, col, unit, a, u, tk):
    ka = a * eo(ramp(u, tk, tk + 0.35))
    if ka <= 0: return
    dy = (1 - eo(ramp(u, tk, tk + 0.45))) * 50
    W_, H_ = 455, 205
    F.glass(x0, y0 + dy, x0 + W_, y0 + H_ + dy, 32, ka, tint=col, tint_a=0.10, shadow=0.25, blur=12)
    F.text(arc['name'], x0 + 24, y0 + 38 + dy, 32, 'sans_black', INK, ka, anchor='l')
    F.text(arc['note'], x0 + W_ - 22, y0 + 40 + dy, 20, 'sans_med', col, ka, anchor='r')
    vals = [v / 1e8 for v in arc['vals'] if v is not None]
    lo, hi = min(min(vals), 0), max(max(vals), 0.01)
    px0, px1, py0, py1 = x0 + 40, x0 + W_ - 40, y0 + 80 + dy, y0 + 160 + dy
    pts = [(px0 + (px1 - px0) * k / (len(vals) - 1), py1 - (v - lo) / (hi - lo) * (py1 - py0)) for k, v in enumerate(vals)]
    m = eio(ramp(u, tk + 0.2, tk + 1.0))
    seg = [pts[0]]
    for k in range(1, len(pts)):
        f = cl(m * (len(pts) - 1) - (k - 1))
        if f <= 0: break
        seg.append((pts[k - 1][0] + (pts[k][0] - pts[k - 1][0]) * f, pts[k - 1][1] + (pts[k][1] - pts[k - 1][1]) * f))
    rising = vals[-1] >= vals[0]
    lc = UP if rising else DOWN
    F.glow_line(seg, lc, ka, 4, glow=1.0)
    for k, (x, y) in enumerate(pts[:len(seg)]):
        F.circle((x, y), 6, WHITE, ka, fill=True, glow=1.0)
        F.text(f'{vals[k]:.1f}', x, y + (-22 if k != 1 or rising else -22), 20, 'num_semi', lerpc(lc, WHITE, 0.3), ka)
    F.text(f'夺冠年 → 持有年 → 再一年 · 净利润（{unit}）', x0 + W_ / 2, y0 + H_ - 18 + dy, 18, 'sans_reg', DIM, ka)


def shot_cycles(F, t, u, a):
    arcs = STORY['why']['arcs']
    rich_head(F, SHOT_T0, '利润能延续多久？【产业周期】说了算', a, size=54)
    sub_line(F, SHOT_T0, '美股：3–5 年的技术浪潮　A股：1 年的政策 / 事件脉冲', a)
    F.text('美股冠军', 297, 470, 34, 'sans_black', US, a * eo(ramp(u, 0.1, 0.4)), glow=0.25)
    F.text('A股冠军', 783, 470, 34, 'sans_black', CN, a * eo(ramp(u, 0.6, 0.9)), glow=0.25)
    for k, arc in enumerate(arcs['us']):
        spark_card(F, 70, 510 + k * 225, arc, US, '亿美元', a, u, 0.2 + k * 0.3)
    for k, arc in enumerate(arcs['cn'][:4]):
        spark_card(F, 555, 510 + k * 225, arc, CN, '亿元', a, u, 0.7 + k * 0.3)
    takeaway(F, '技术浪潮能连涨几年，事件脉冲只有一年', 1470, a * eo(ramp(u, 2.6, 3.0)), size=44)


def shot_flows(F, t, u, a):
    fl = STORY['why']['flows']
    rich_head(F, SHOT_T0, '谁在买？【被动资金】vs【存量博弈】', a, size=54)
    cards = [(US, '美股', ['2023 年底，美国被动基金规模首次超过主动基金', '市值越大 → 指数权重越高 → 被动买盘越多'], '晨星数据：被动约 13.3 万亿美元'),
             (CN, 'A股', ['个人投资者贡献约 61% 的交易量', f"10 只冠军里，只有 {fl['cn_in_csi300']} 只是沪深300成分股"], '2022 年前三季度 · 监管数据')]
    for j, (col, h, lines, src) in enumerate(cards):
        tk = 0.2 + j * 0.6
        ka = a * eo(ramp(u, tk, tk + 0.35))
        y0 = 430 + j * 300
        F.glass(70, y0, 1010, y0 + 270, 34, ka, tint=col, tint_a=0.10, shadow=0.25, blur=14, spec=ramp(u, tk, tk + 1))
        F.text(h, 110, y0 + 52, 40, 'sans_black', col, ka, anchor='l', glow=0.25)
        F.text(src, 970, y0 + 54, 20, 'sans_reg', DIM, ka, anchor='r')
        for q, ln in enumerate(lines):
            la = ka * eo(ramp(u, tk + 0.25 + q * 0.2, tk + 0.55 + q * 0.2))
            F.circle((122, y0 + 130 + q * 70), 7, col, la, fill=True, glow=1)
            F.text(ln, 145, y0 + 130 + q * 70, 32, 'sans_med', INK, la, anchor='l')
    # 动量 vs 反转
    ba = a * eo(ramp(u, 1.6, 2.0))
    F.text('上一年涨幅前 10 名，第二年相对市场的超额收益（十年平均）', 540, 1065, 26, 'sans_med', DIM, ba)
    zero = 540
    F.line((zero, 1110), (zero, 1330), GOLD, ba * 0.6, 2, glow=0.8)
    for j, (lab, v, col, tag) in enumerate([('美股', fl['us_top10'], US, '强者恒强'), ('A股', fl['cn_top10'], CN, '物极必反')]):
        y = 1165 + j * 115
        q = eo(ramp(u, 1.8 + j * 0.3, 2.4 + j * 0.3))
        L = v * 1800 * q
        x0, x1 = (zero, zero + L) if L >= 0 else (zero + L, zero)
        if abs(L) > 2:
            m = np.repeat((np.linspace(0.35, 1, int(abs(L))) if L >= 0 else np.linspace(1, 0.35, int(abs(L))))[None, :], 70, 0).astype(np.float32)
            F.over(m, x0, y - 35, lerpc(col, WHITE, 0.15), ba * 0.9, glow=0.6)
        F.text(f'{lab} {v * q * 100:+.1f}%'.replace('-', '−'), zero + L + (20 if L >= 0 else -20), y, 44, 'num' if False else 'sans_black', col, ba,
               anchor='l' if L >= 0 else 'r', glow=0.4)
        F.text(tag, zero + (-30 if L >= 0 else 30), y, 30, 'sans_bold', col, ba * q, anchor='r' if L >= 0 else 'l')
    takeaway(F, '一边是增量资金推着龙头走，一边是接最后一棒', 1450, a * eo(ramp(u, 2.7, 3.1)), size=40)


def shot_brakes(F, t, u, a):
    rich_head(F, SHOT_T0, '有没有刹车？【多空平衡】vs【单边亢奋】', a, size=52)
    sub_line(F, SHOT_T0, '能不能做空，决定了泡沫在哪里被纠正', a)
    for j, (col, h, l1, l2, wild) in enumerate([
            (US, '美股', '融券做空、个股期权都很成熟', '估值偏离，途中就被空头纠偏', False),
            (CN, 'A股', '融券余额只占流通市值约 0.05%', '没有刹车：涨到极端，再用跌停和阴跌回归', True)]):
        tk = 0.2 + j * 0.8
        ka = a * eo(ramp(u, tk, tk + 0.35))
        y0 = 470 + j * 480
        F.glass(70, y0, 1010, y0 + 440, 36, ka, tint=col, tint_a=0.10, shadow=0.25, blur=14)
        F.text(h, 110, y0 + 55, 40, 'sans_black', col, ka, anchor='l', glow=0.25)
        F.text(l1, 110, y0 + 115, 30, 'sans_bold', INK, ka, anchor='l')
        F.text(l2, 110, y0 + 165, 28, 'sans_reg', INK, ka, anchor='l')
        # 价值线（金）与价格线
        xs = np.linspace(110, 970, 150)
        val = y0 + 350 - (xs - 110) * 0.06
        if wild:
            bump = np.exp(-((xs - 640) / 140) ** 2) * 105
            crash = np.where(xs > 700, np.clip((xs - 700) / 30, 0, 1), 0)
            price = val - bump * (1 - crash) + 20 * np.sin(xs / 40) * 0.3
        else:
            price = val - 28 * np.sin(xs / 55) * np.exp(-((xs - 540) / 600) ** 2)
        m = max(2, int(150 * eio(ramp(u, tk + 0.3, tk + 1.4))))
        F.glow_line(list(zip(xs[:m], val[:m])), GOLD, ka, 4, glow=0.9)
        F.glow_line(list(zip(xs[:m], price[:m])), lerpc(col, WHITE, 0.2), ka, 3, glow=0.8)
        F.text('价值', 975, val[-1] + 28, 20, 'sans_bold', GOLD, ka, anchor='r')
    F.text('A股数据：证监会 2024 年 7 月暂停转融券时公布', 540, 1430, 20, 'sans_reg', DIM, a * eo(ramp(u, 1.2, 1.6)))
    takeaway(F, '没有刹车的上涨，只能靠撞墙停下', 1510, a * eo(ramp(u, 2.6, 3.0)), size=44)


# ---------------------------------------------------------------- ④ 真相：价格 vs 价值（承接巴菲特）
def shot_bridge(F, t, u, a):
    rich_head(F, SHOT_T0, '同一条规则，赢的永远是【利润】', a, size=56)
    sub_line(F, SHOT_T0, '这条规则只看过去的价格，不看企业的价值', a)
    la = a * eo(ramp(u, 0.3, 0.7))
    F.glass(70, 500, 520, 1100, 40, la, tint=(0.6, 0.65, 0.8), tint_a=0.06, shadow=0.3, blur=14)
    F.text('买涨幅', 295, 570, 44, 'serif_black', DIM, la)
    for k in range(5):
        fade = 1 - 0.6 * ramp(u, 1.6, 2.4) * (k > 0)
        y = 680 + k * 80
        F.text(f'No.{k + 1}', 120, y, 30, 'num', GOLD if k == 0 else DIM, la * fade, anchor='l')
        F.line((220, y), (220 + (260 - k * 40), y), lerpc(UP, WHITE, 0.2), la * fade * 0.8, 10)
    F.text('买到的是：价格', 295, 1060, 34, 'sans_black', INK, la)
    ra = a * eo(ramp(u, 1.0, 1.4))
    F.glass(560, 500, 1010, 1100, 40, ra, tint=GOLD, tint_a=0.12, shadow=0.3, blur=14, spec=ramp(u, 1.0, 2.2))
    F.text('看利润', 785, 570, 44, 'serif_black', a=ra, grad=GOLD_GRAD, glow=0.35)
    for k in range(6):
        g = eo(ramp(u, 1.2 + k * 0.12, 1.6 + k * 0.12))
        gbar(F, 610 + k * 64, 654 + k * 64, 980, (60 + k * 52) * g, GOLD, ra, refl=False)
    F.text('买到的才是：价值', 785, 1060, 34, 'sans_black', GOLD_L, ra)
    fa = a * eo(ramp(u, 2.3, 2.7))
    if fa > 0:
        F.text3d('利润，才是股价长期的发动机', 540, 1290, 64 * pop(F.t, SHOT_T0 + 2.3 * WHY_SLOW, 0.15), 'serif_black', face=GOLD_GRAD,
                 a=fa, glow=0.5, spec=ramp(u, 2.6, 3.6))
        F.text('那么，怎样才能买到价值？', 540, 1420, 36, 'sans_bold', INK, a * eo(ramp(u, 3.0, 3.4)))


STEP_NAMES = ['第二年', '利润', '根源', '真相']
WHY_SHOTS = [(0, shot_second_year), (1, shot_formula), (1, shot_scatter), (1, shot_decomp),
             (2, shot_cycles), (2, shot_flows), (2, shot_brakes), (3, shot_bridge)]


def sc_why(F, t):
    global SHOT_T0
    if t >= T_WHY:
        F.flash = max(F.flash, 0.6 * math.exp(-(t - T_WHY) / 0.12))
    for k, (ch, fn) in enumerate(WHY_SHOTS):
        t0, t1 = WHY_SHOT_T[k], WHY_SHOT_T[k + 1]
        if not (t0 <= t < t1): continue
        a = env(t, t0, t1 - 0.02, 0.35, 0.4)
        ks = [i for i, (c, _) in enumerate(WHY_SHOTS) if c == ch]          # 同一步的镜头之间，进度条保持不动
        why_frame(F, t, ch, env(t, WHY_SHOT_T[ks[0]], WHY_SHOT_T[ks[-1] + 1] - 0.02, 0.3, 0.28))
        SHOT_T0 = t0
        fn(F, t, (t - t0) / WHY_SLOW, a)


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
        F.text_chars('巴菲特与芒格：怎样买到真正的价值', 540, INS_Y + 225 * sc, 44 * sc, 'serif_bold', SUBGOLD, A, t0=T_INSIGHT + 3.2, stag=0.06)
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
        tk = B(248)                                        # 198.52：最后一句金句
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
        F.text('内容仅供参考，不构成投资建议。回测基于历史数据，不代表未来收益。', 540, 1345, 24, 'sans_reg', SUBGOLD,
               0.7 * eo(ramp(t, T_FOLLOW + 1.3, T_FOLLOW + 1.9)))


# ================================================================ frame
SCENES = [(0, T_TITLE + 0.1, sc_hook), (T_TITLE - 0.05, T_RULES + 0.1, sc_title), (T_RULES, year_t0(0) + 0.1, sc_rules),
          (year_t0(0) - 0.1, T_RACE_END + 0.3, sc_race), (T_FINAL, T_BREAK + 0.5, sc_final),
          (T_BREAK - 0.1, T_WHY + 0.1, sc_break), (T_WHY - 0.1, T_INSIGHT + 0.1, sc_why),
          (T_INSIGHT - 0.1, T_VALUE + 0.05, sc_insight), (T_VALUE - 0.1, T_END + 0.5, sc_value), (T_END - 0.1, T_TOTAL + 1, sc_end)]


# 每段的星云配色（关键帧之间平滑过渡）
CRIMSON, MAGENTA, TEAL, AMBER = hexc('#C2185B'), hexc('#B5179E'), hexc('#00B3A4'), hexc('#E08A1E')
PALETTE = [(0, VIOLET, CRIMSON), (T_TITLE, GOLD_D, CRIMSON), (T_RULES, US2, TEAL), (year_t0(0), US2, CN2), (T_BREAK, VIOLET, US2),
           (T_WHY, US2, TEAL), (WHY_T[1], AMBER, VIOLET), (WHY_T[2], CRIMSON, MAGENTA), (WHY_T[3], GOLD_D, US2), (T_INSIGHT, GOLD_D, AMBER), (T_VALUE, GOLD_D, MAGENTA),
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
    if t < T_TITLE:
        BGR.field(F, t, GOLD, CN, a=0.4 if t < HOOK[1] else 0.9, horizon=1330 if t < HOOK[1] else 1420)
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
    for tb, y, col in [(T_TITLE, 860, GOLD), (T_RULES, 300, GOLD), (year_t0(0), 190, US), (T_FINAL, 250, GOLD), (T_WHY, 305, GOLD), (WHY_T[1], 305, hexc('#FF5C7A')), (WHY_T[2], 305, GOLD), (WHY_T[3], 305, GOLD_L), (T_VALUE, 900, GOLD), (T_MUNGER, 430, GOLD), (T_PRIN, 1000, GOLD), (T_TRUTH, 545, GOLD)]:
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
