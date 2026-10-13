"""v2：冷开场 → 标题 → 01 谨慎（储户调查、每赚 100 元花多少、消费分化、企业观望、原因 → 预期）
数据全部取最新可得值（见 README「数据与出处」）。"""
import math

import numpy as np

from common import *          # noqa: F401,F403
from registry import scene
from timeline import CAP, HITS, SEC, T

CX = W / 2


def cw(key, t, fi=0.35, fo=0.3):
    t0, t1, _ = CAP[key]
    return win(t, t0, t1, fi, fo)


def rich(fr, parts, cx, y, a=1.0, anchor='c', gap=10):
    """一行混排：parts = [(文字, 字体, 字号, 底色), ...]，整体按 anchor 对齐，竖直居中于 y"""
    ws = [text_size(s, f, z)[0] for s, f, z, _ in parts]
    total = sum(ws) + gap * (len(parts) - 1)
    x = cx - total / 2 if anchor == 'c' else (cx if anchor == 'l' else cx - total)
    for (s, f, z, base), w in zip(parts, ws):
        dy = z * 0.04 if f.startswith('inter') else 0
        fr.text(s, x + w / 2, y + dy, z, f, base, a, 'c', glow=0.2, shadow=0.5)
        x += w + gap
    return total


def num_unit(fr, x, y, num, unit, nsize, usize, base='gold', a=1.0, nfont='inter_xbold', ufont='sans_med',
             anchor='c', glow=0.25):
    wn = text_size(num, nfont, nsize)[0]
    wu = text_size(unit, ufont, usize)[0] if unit else 0
    gap = nsize * 0.08
    total = wn + (gap + wu if unit else 0)
    x0 = x - total / 2 if anchor == 'c' else x
    fr.text(num, x0 + wn / 2, y, nsize, nfont, base, a, 'c', glow=glow, shadow=0.5)
    if unit:
        fr.text(unit, x0 + wn + gap + wu / 2, y + nsize * 0.18, usize, ufont, base, a, 'c', glow=glow * 0.6,
                shadow=0.5)
    return total


def two(fr, key, t, y, s1=58, s2=66, split=None, f1='serif_bold', f2='serif_black', gap=1.36, base='white'):
    """把一条文案按 split 分成两行逐字浮现"""
    t0, t1, s = CAP[key]
    k = win(t, t0, t1, 0.35, 0.3)
    if k <= 0:
        return 0.0
    l1, l2 = split if split else s.split('，', 1)
    if not split:
        l1 += '，'
    fr.text(l1, CX, y, s1, f1, base, k, glow=0.2, stagger=(t - t0, 0.035, 0.4))
    fr.text(l2, CX, y + s2 * gap, s2, f2, base, k, glow=0.3, stagger=(t - t0 - 0.25, 0.035, 0.45))
    return k


def bar_glass(fr, x0, y0, x1, y1, col, a, th=2.5):
    """2D 发光玻璃柱（y0 < y1）"""
    if y1 - y0 < 1:
        fr.line((x0, y1), (x1, y1), col, a, th, glow=1.0)
        return
    fr.rrect_fill(x0, y0, x1, y1, 6, col * 0.22, a, glow=0.15)
    n = 12
    for k in range(n):
        yy0 = y0 + (y1 - y0) * k / n
        yy1 = y0 + (y1 - y0) * (k + 1) / n
        fr.fill([(x0 + 3, yy0), (x1 - 3, yy0), (x1 - 3, yy1), (x0 + 3, yy1)], col * 0.10 * (1 - k / n), a)
    fr.rrect(x0, y0, x1, y1, 6, col, a * 0.9, th, glow=0.8)
    hi = GOLD_HI if col is GOLD else (ICE_HI if col is ICE else col)
    fr.line((x0 + 8, y0 + 2), (x1 - 8, y0 + 2), hi, a, 3, glow=1.5)


# ================================================================ 冷开场 0–28
LPR = [4.85, 4.65, 4.45, 4.30, 4.20, 3.95, 3.60, 3.50]
LPR_PATH = [4.85, 4.80, 4.75, 4.65, 4.65, 4.60, 4.45, 4.30, 4.20, 3.95, 3.85, 3.60, 3.50]
LOAN_LBL = ['2021', '2022', '2023', '2024', '2025', '2026']
LOAN_SUB = ['', '', '', '', '', '1—8月']
LOAN_V = [7.92, 3.83, 4.33, 2.72, 0.44, -1.03]


def cold_cam(t):
    z = -52 + t * 0.8
    return Cam((0, 5.5, z), (0, 0.4, z + 50), fov=58, cy=H * 0.80)


@scene(0.0, 28.0, 0.0, 0.25)
def sc_cold(fr, t, a):
    dim = 1 - 0.55 * ss((t - 24.0) / 2.0)
    FIELD.draw(fr, cold_cam(t), t, a * 0.5 * dim, warm=np.full(FIELD.n, 0.85))
    draw_dust(fr, t, a * 0.6)
    # -------- 利率降到历史最低
    k = a * win(t, 0.0, 6.6, 0.3, 0.4)
    if k > 0:
        fr.text('贷款利率', CX, 600, 46, 'sans_med', 'grey', k, track=0.2, glow=0)
        steps = [0.5 + 0.36 * i for i in range(8)]
        i = max([j for j, tt in enumerate(steps) if t >= tt] + [0])
        p = eo((t - steps[i]) / 0.22) if t >= steps[0] else 1.0
        fr.text(f'{LPR[i]:.2f}%', CX, 790 + (1 - p) * 60, 240, 'inter_xbold', 'ice', k * p, glow=0.35)
        if i > 0 and p < 1:
            fr.text(f'{LPR[i - 1]:.2f}%', CX, 790 - p * 60, 240, 'inter_xbold', 'ice', k * (1 - p), glow=0.3)
        kl = a * cw('c_low', t, 0.4, 0.4)
        fr.text('降到了【历史最低】', CX, 975, 78, 'serif_black', 'white', kl, glow=0.3, stagger=(t - CAP['c_low'][0], 0.06, 0.4))
        n = len(LPR_PATH)
        xs = np.linspace(200, 880, n)
        ys = 1100 + (4.85 - np.array(LPR_PATH)) / (4.85 - 3.5) * 120
        upto = cl((t - 0.5) / 2.6) * (n - 1)
        m = int(upto)
        pts = list(zip(xs[:m + 1], ys[:m + 1]))
        if m < n - 1:
            f = upto - m
            pts.append((lerp(xs[m], xs[m + 1], f), lerp(ys[m], ys[m + 1], f)))
        fr.stroke(pts, ICE, k * 0.9, 3, glow=0.8)
        fr.glow(pts[-1], 10, ICE_HI, k * 1.2)
        fr.disc(pts[-1], 5, ICE_HI, k)
        footnote(fr, '5年期以上 LPR · 2019年8月 → 2026年9月 · 来源：全国银行间同业拆借中心', k)
    # -------- 按常理……
    k = a * cw('c_common', t, 0.35, 0.3)
    if k > 0:
        fr.text('按常理，钱便宜了，', CX, 560, 60, 'serif_bold', 'grey', k, stagger=(t - 6.8, 0.04, 0.4))
        fr.text('大家该【多借、多花】', CX, 660, 72, 'serif_black', 'white', k, glow=0.3, stagger=(t - 7.1, 0.05, 0.45))
        # 「想象中」的上升箭头（虚线）
        p = eo((t - 7.4) / 1.2)
        x0, y0, y1 = CX, 1150, 1150 - 330 * p
        for yy in np.arange(y0, y1, -26):
            fr.line((x0, yy), (x0, max(yy - 14, y1)), GOLD, k * 0.7, 6, glow=0.8)
        if p > 0.9:
            for s in (-1, 1):
                fr.line((x0, y1), (x0 + s * 46, y1 + 46), GOLD, k * 0.8, 6, glow=0.8)
        fr.text('想象中', x0 + 120, 1000, 34, 'sans_med', 'gold', k * cl((t - 8.2) / 0.4), glow=0)
    # -------- 可是：居民新增贷款
    k = a * win(t, HITS['kesh'], 20.0, 0.15, 0.35)
    if k > 0:
        lt = t - HITS['kesh']
        fr.flash = max(fr.flash, 0.12 * math.exp(-lt / 0.1))
        k1 = a * cw('c_less', t, 0.3, 0.3)
        fr.text('可是，', CX, 330, 60, 'serif_bold', 'grey', k1, stagger=(t - 10.8, 0.06, 0.35))
        fr.text('大家借的钱，反而越来越少', CX, 430, 70, 'serif_black', 'white', k1, glow=0.3, stagger=(t - 11.1, 0.04, 0.4))
        zero, scale = 980, 52
        xs = np.linspace(170, 910, 6)
        for i, (x, v) in enumerate(zip(xs, LOAN_V)):
            g = eback((lt - 0.3 - 0.45 * i) / 0.5, 1.2)
            if g <= 0:
                continue
            hh = v * scale * g
            col = GOLD if v > 0 else CORAL
            if v > 0:
                bar_glass(fr, x - 46, zero - hh, x + 46, zero, col, k, 2.2)
                fr.text(f'{v:.2f}', x, zero - hh - 34, 40, 'inter_bold', 'gold', k * cl(g), glow=0.2)
            else:
                bar_glass(fr, x - 46, zero, x + 46, zero - hh, col, k * (0.8 + 0.4 * pulse(t)), 2.2)
                fr.text(f'−{abs(v):.2f}', x, zero - hh + 40, 40, 'inter_bold', 'coral', k * cl(g), glow=0.3)
            fr.text(LOAN_LBL[i], x, zero + 150, 30, 'inter_med',
                    'coral' if v < 0 else 'grey', k, glow=0)
            if LOAN_SUB[i]:
                fr.text(LOAN_SUB[i], x, zero + 186, 26, 'sans_med', 'coral', k, glow=0)
        fr.line((120, zero), (960, zero), WHITE, k * 0.35, 2)
        fr.text('居民新增贷款（万亿元）', CX, 1230, 34, 'sans_med', 'grey', k, track=0.08, glow=0)
        k2 = a * cw('c_neg', t, 0.3, 0.3)
        if k2 > 0:
            chip(fr, '今年前 8 个月：还的比借的多', CX, 1320, k2, CORAL, 44, fname='sans_bold', base='coral',
                 scale=0.9 + 0.1 * eo((t - 15.6) / 0.3))
        footnote(fr, '2026年为1—8月累计 · 来源：中国人民银行《金融统计数据报告》', k)
    # -------- 钱去哪了
    k = a * cw('c_where', t, 0.35, 0.3)
    if k > 0:
        fr.text('钱去哪了？', CX, 330, 80, 'serif_black', 'white', k, glow=0.3, stagger=(t - 20.0, 0.07, 0.4))
        fr.text('2026年1—8月 · 居民部门', CX, 440, 34, 'sans_med', 'grey', k, glow=0)
        for j, (lbl, num, base, col, y) in enumerate((('存款', '+6.99', 'ice', ICE, 640),
                                                     ('贷款', '−1.03', 'coral', CORAL, 900))):
            kk = k * eo((t - 20.4 - 0.5 * j) / 0.5)
            fr.card(110, y - 110, 970, y + 110, 30, kk, tint=col, border=col, border_a=0.6, fill_a=0.07, blur=12)
            fr.text(lbl, 200, y, 56, 'serif_bold', 'white', kk, anchor='l', glow=0)
            num_unit(fr, 690, y, num, '万亿', 130, 50, base, kk)
        k3 = k * cl((t - 21.6) / 0.4)
        fr.text('一边存钱，一边【还贷】', CX, 1130, 64, 'serif_black', 'white', k3, glow=0.3, stagger=(t - 21.6, 0.05, 0.4))
        footnote(fr, '来源：中国人民银行《2026年8月金融统计数据报告》', k)
    # -------- 为什么
    k = a * win(t, 24.0, 28.2, 0.35, 0.05)
    if k > 0:
        p = eo((t - 24.0) / 0.6)
        fr.text('钱更便宜了，', CX, 820, 76, 'serif_bold', 'white', k, scale=1.1 - 0.1 * p, blur=(1 - p) * 6, glow=0.3)
        p2 = eo((t - 24.8) / 0.6)
        fr.text('为什么反而【更谨慎】？', CX, 940, 92, 'serif_black', 'white', k * cl((t - 24.8) / 0.3),
                scale=1.1 - 0.1 * p2, blur=(1 - p2) * 6, glow=0.4)
    fr.zoom = 1 + 0.05 * ei((t - 27.0) / 1.0)


# ================================================================ 标题 28–36
def title_cam(t):
    lt = t - SEC['title'][0]
    p = eo(lt / 2.2)
    z = lerp(-29.6, -8.0, p) + lt * 0.6
    y = lerp(5.5, 3.2, p)
    return Cam((0, y, z), (0, lerp(0.4, 2.2, p), z + 50), fov=58, cy=H * 0.70)


@scene(28.0, 36.0, 0.0, 0.5)
def sc_title(fr, t, a):
    t0 = SEC['title'][0]
    lt = t - t0
    fr.flash = max(fr.flash, 0.85 * math.exp(-lt / 0.055) * a)
    fr.ca = 7 * math.exp(-lt / 0.2)
    cam = title_cam(t)
    hx, hy, _, _ = cam.project([[0, 0, 400]])
    hy = float(hy[0])
    warm = np.clip(0.6 + 0.4 * (FIELD.P[:, 2] + 48) / 96, 0, 1)
    FIELD.draw(fr, cam, t, a * (0.9 - 0.3 * ss((lt - 6.5) / 1.5)), warm=warm, size=1.2)
    k = a * eo(lt / 1.2)
    for s_, al in ((900, 0.10), (380, 0.18), (120, 0.35)):
        fr.glow((CX, hy), s_, GOLD, k * al)
    xs = np.linspace(-80, W + 80, 80)
    fr.stroke(list(zip(xs, np.full(80, hy))), GOLD_HI, k * 0.8, 2, glow=1.5)
    r = 1500 * eo(lt / 1.1)
    fr.circle((CX, 900), r, GOLD_HI, a * 0.7 * (1 - cl(lt / 1.1)), 3, glow=1.5)
    draw_dust(fr, t, a * 0.8, speed=3.0 * math.exp(-lt / 1.5) + 0.5)
    k = a * win(t, t0 + 0.3, t0 + 7.6, 0.5, 0.4)
    fr.text('2026 诺贝尔经济学奖', CX, 610, 46, 'serif_med', 'gold', k, track=0.28, glow=0.35,
            stagger=(lt - 0.3, 0.05, 0.5))
    ln = 300 * eo((lt - 0.7) / 0.9)

    def rule(img, k=k, ln=ln):
        if ln > 2:
            y = 676
            x0, x1 = int(CX - ln / 2), int(CX + ln / 2)
            img[y:y + 2, x0:x1] = img[y:y + 2, x0:x1] * (1 - 0.8 * k) + 0.8 * k * GOLD
    fr.overlay_fn(rule)
    fr.text('为什么你的【预期】，', CX, 800, 100, 'serif_black', 'white', k, glow=0.3, stagger=(lt - 0.55, 0.06, 0.5))
    fr.text('决定了经济的【未来】？', CX, 935, 100, 'serif_black', 'white', k, glow=0.3, stagger=(lt - 0.95, 0.06, 0.5))
    k2 = a * win(t, t0 + 1.8, t0 + 7.6, 0.8, 0.4)
    fr.text('Robert E. Hall  ·  Michael Woodford', CX, 1075, 40, 'corm_bold', 'subgold', k2, track=0.06, glow=0.2)
    fr.zoom = 1 + 0.035 * ss(lt / 7.5)


# ================================================================ 01 储户调查 36–45
SURVEY = [('更多储蓄', 62.3, ICE, 'ice'), ('更多消费', 19.2, GOLD, 'gold'), ('更多投资', 18.5, VIOLET, 'white')]


@scene(36.0, 45.0, 0.3, 0.35)
def sc_survey(fr, t, a):
    t0 = SEC['survey'][0]
    lt = t - t0
    fr.flash = max(fr.flash, 0.2 * math.exp(-lt / 0.1) * a)
    draw_dust(fr, t, a * 0.5)
    k = a * cw('s_head', t, 0.35, 0.3)
    fr.text('这不是错觉', CX, 300, 84, 'serif_black', 'white', k, glow=0.3, stagger=(lt - 0.3, 0.08, 0.45))
    kk = a * win(t, t0 + 0.6, t0 + 9.2, 0.4, 0.35)
    fr.text('城镇储户：未来一段时间，你更倾向……', CX, 470, 38, 'sans_med', 'grey', kk, glow=0)
    x0, x1 = 120, 960
    for i, (lbl, v, col, base) in enumerate(SURVEY):
        y = 640 + i * 190
        g = eo((lt - 1.0 - 0.35 * i) / 1.0)
        fr.text(lbl, x0, y - 52, 44, 'serif_bold', base if base != 'white' else 'white', kk, anchor='l', glow=0.1)
        w = (x1 - x0) * v / 70 * g
        fr.rrect_fill(x0, y - 18, x1, y + 34, 26, GREY * 0.08, kk)
        if w > 4:
            fr.rrect_fill(x0, y - 18, x0 + w, y + 34, 26, col * 0.35, kk, glow=0.3)
            fr.rrect(x0, y - 18, x0 + w, y + 34, 26, col, kk, 2.5, glow=1.0)
        fr.text(f'{v * g:.1f}%', x1, y - 52, 56, 'inter_xbold', base if base != 'white' else 'white', kk, anchor='r',
                glow=0.3)
    k2 = a * cw('s_cap', t, 0.35, 0.3)
    fr.text('想多存钱的人，', CX, 1240, 58, 'serif_bold', 'white', k2, glow=0.2, stagger=(t - CAP['s_cap'][0], 0.04, 0.4))
    fr.text('是想多花钱的【3 倍多】', CX, 1335, 66, 'serif_black', 'white', k2, glow=0.3,
            stagger=(t - CAP['s_cap'][0] - 0.25, 0.04, 0.45))
    footnote(fr, '来源：中国人民银行《2025年第三季度城镇储户问卷调查报告》', kk)


# ================================================================ 每赚 100 元，花掉多少 45–54
@scene(45.0, 54.0, 0.3, 0.35)
def sc_spend(fr, t, a):
    t0 = SEC['spend'][0]
    lt = t - t0
    draw_dust(fr, t, a * 0.5)
    k = a * cw('p_head', t, 0.35, 0.3)
    fr.text('每赚 100 元，花掉多少？', CX, 270, 66, 'serif_black', 'white', k, glow=0.3, stagger=(lt - 0.3, 0.05, 0.45))
    sw = ss((lt - 4.0) / 0.8)              # 2019 → 2026
    val = lerp(67.5, 64.6, sw)
    yr = '2019年上半年' if lt < 4.4 else '2026年上半年'
    kk = a * win(t, t0 + 0.6, t0 + 9.2, 0.4, 0.35)
    num_unit(fr, CX, 420, f'{val:.1f}', '元', 120, 50, 'gold' if sw < 0.5 else 'coral', kk, ufont='serif_bold')
    fr.text(yr, CX, 505, 36, 'sans_med', 'grey', kk, glow=0)
    # 100 枚硬币
    r = 25
    gx0, gy0, gap = CX - 4.5 * 68, 600, 68
    lit_n = 67.5 * eo((lt - 0.8) / 2.0)
    for i in range(100):
        cx_, cy_ = gx0 + (i % 10) * gap, gy0 + (i // 10) * gap
        on = cl(lit_n - i)
        off_new = cl((67.5 - i)) - cl((val - i))      # 2019 有、2026 没有的那几枚
        if on > 0.01:
            if off_new > 0.01 and sw > 0:
                col = GOLD * (1 - sw) + CORAL * sw
                al = kk * (on - 0.75 * off_new * sw)
            else:
                col, al = GOLD, kk * on
            fr.disc((cx_, cy_), r, col * 0.28, al)
            fr.circle((cx_, cy_), r, col, al, 2.5, glow=0.8)
            fr.circle((cx_, cy_), r * 0.62, col, al * 0.5, 1.5)
        else:
            fr.circle((cx_, cy_), r, GREY, kk * 0.18, 1.5)
    k2 = a * cw('p_cap', t, 0.35, 0.3)
    rich(fr, [('收入涨了', 'serif_bold', 54, 'white'), ('5.2%', 'inter_xbold', 66, 'gold'), ('，消费只涨了', 'serif_bold', 54, 'white'),
              ('3.7%', 'inter_xbold', 66, 'coral')], CX, 1330, k2, gap=8)
    footnote(fr, '全国居民人均消费支出 ÷ 人均可支配收入（上半年）· 来源：国家统计局', kk)


# ================================================================ 消费分化 54–66
CARDS = [
    ('card', '社会消费品零售总额', '+1.1%', 'gold', '整体偏冷'),
    ('plane', '服务零售额', '+4.9%', 'gold', '商品零售 +1.0%'),
    ('wheat', '乡村消费品零售额', '+2.3%', 'gold', '城镇 +1.0%'),
    ('house', '新建商品房销售额', '−13.0%', 'coral', '二手房网签面积 +10.6%'),
]


@scene(54.0, 66.0, 0.3, 0.4)
def sc_split(fr, t, a):
    t0 = SEC['split'][0]
    lt = t - t0
    fr.flash = max(fr.flash, 0.2 * math.exp(-lt / 0.12) * a)
    draw_dust(fr, t, a * 0.5)
    k = a * cw('sp_head', t, 0.4, 0.3)
    fr.text('消费没有消失，而是在【分化】', CX, 285, 62, 'serif_black', 'white', k, glow=0.3, stagger=(lt - 0.3, 0.045, 0.45))
    for i, (ic, lbl, num, base, note) in enumerate(CARDS):
        kk = a * eo((lt - 0.8 - 0.5 * i) / 0.5) * win(t, t0 + 0.5, t0 + 12.2, 0.01, 0.4)
        if kk <= 0.01:
            continue
        col = CORAL if base == 'coral' else GOLD
        x0 = 56 if i % 2 == 0 else 552
        y0 = 420 if i < 2 else 800
        y0 += (1 - kk) * 60 + 6 * math.sin(t * 1.3 + i * 1.7)
        x1, y1 = x0 + 472, y0 + 340
        fr.card(x0, y0, x1, y1, 30, kk, tint=col, border=col, border_a=0.55, fill_a=0.07, blur=14)
        fr.overlay_draw(lambda cv, ic=ic, x0=x0, y0=y0, col=col, kk=kk: icon(cv, ic, (x0 + 62, y0 + 70), 50, col, kk, 3, glow=0))
        fr.text(lbl, x0 + 108, y0 + 70, 34 if len(lbl) > 7 else 38, 'sans_bold', 'white', kk, anchor='l', glow=0, shadow=0.3)
        val = float(num.replace('−', '-').replace('%', '').replace('+', ''))
        cnt = val * eo((lt - 0.9 - 0.5 * i) / 0.9)
        txt = ('+' if val > 0 else '−') + f'{abs(cnt):.1f}%'
        fr.text(txt, (x0 + x1) / 2, y0 + 190, 118, 'inter_xbold', base, kk, glow=0.35, shadow=0.3)
        fr.text(note, (x0 + x1) / 2, y0 + 292, 30, 'sans_med', 'grey', kk, glow=0, shadow=0.3)
    k = a * cw('sp_tail', t, 0.4, 0.4)
    fr.text('大额、长期的支出，【最先收缩】', CX, 1262, 62, 'serif_black', 'white', k, glow=0.3, stagger=(t - CAP['sp_tail'][0], 0.045, 0.45))
    footnote(fr, '2026年1—8月同比 · 来源：国家统计局', a * win(t, t0 + 0.5, t0 + 12.2, 0.4, 0.4))


# ================================================================ 企业观望 66–71
_FR = np.random.default_rng(14)
WIN_POS = [(x, y) for y in (0, 1) for x in range(6)]
WIN_OFF = _FR.random(len(WIN_POS)) * 0.9


@scene(66.0, 71.0, 0.3, 0.35)
def sc_firms(fr, t, a):
    t0 = SEC['firms'][0]
    lt = t - t0
    draw_dust(fr, t, a * 0.5)
    fr.text('企业，也在观望', CX, 290, 72, 'serif_black', 'white', a * win(t, t0 + 0.2, t0 + 5.2, 0.35, 0.3), glow=0.3,
            stagger=(lt - 0.2, 0.06, 0.45))
    c = (CX, 720)
    s = 480
    icon(fr, 'factory', c, s, ICE_HI, a, 4, glow=1.0)
    dim = ss((lt - 1.0) / 2.0)
    for i, (gx, gy) in enumerate(WIN_POS):
        x = c[0] - 0.42 * s + gx * 0.14 * s
        y = c[1] + 0.08 * s + gy * 0.15 * s
        on = 1 - cl((dim * 1.4 - WIN_OFF[i]) / 0.3)
        fr.rrect_fill(x - 21, y - 17, x + 21, y + 17, 4, GOLD * (0.2 + 0.8 * on), a, glow=0.8 * on)
    kc = a * eo((lt - 0.6) / 0.4)
    chip(fr, '民间投资  −10.1%', CX, 1090, kc, CORAL, 56, fname='sans_bold', base='coral')
    k = a * cw('f_cap', t, 0.35, 0.3)
    fr.text('看不清订单，企业就【不敢扩产】', CX, 1250, 60, 'serif_black', 'white', k, glow=0.3, stagger=(t - CAP['f_cap'][0], 0.04, 0.4))
    footnote(fr, '2026年1—8月民间固定资产投资同比 · 来源：国家统计局', kc)


# ================================================================ 原因 → 预期 71–76
WORDS = ['收入', '就业', '房价', '债务', '人口', '社保', '物价', '补贴']
_CR = np.random.default_rng(4)
CS_N = 600
CS_W = _CR.integers(0, 8, CS_N)
CS_U = _CR.random(CS_N)


@scene(71.0, 76.0, 0.3, 0.25)
def sc_causes(fr, t, a):
    t0 = SEC['causes'][0]
    lt = t - t0
    c = np.array([CX, 820.0])
    draw_dust(fr, t, a * 0.5)
    k = a * cw('cs_head', t, 0.3, 0.25)
    fr.text('原因很多', CX, 330, 64, 'serif_black', 'white', k, glow=0.25, stagger=(lt - 0.2, 0.06, 0.4))
    k = a * cw('cs_tail', t, 0.3, 0.2)
    fr.text('但最后，都落在一个词上', CX, 330, 60, 'serif_bold', 'white', k, glow=0.25, stagger=(t - CAP['cs_tail'][0], 0.04, 0.35))
    t_y = HITS['yuqi']
    shrink = eio((t - t_y - 0.3) / 1.5)
    rx, ry = 380 * (1 - 0.8 * shrink), 165 * (1 - 0.8 * shrink)
    ang0 = lt * 0.4
    pos = []
    for i, w in enumerate(WORDS):
        q = ang0 + i * 2 * np.pi / 8
        pos.append((c[0] + rx * math.cos(q), c[1] + ry * math.sin(q), (math.sin(q) + 1) / 2))
    for i in np.argsort([p[2] for p in pos]):
        x, y, d = pos[i]
        kk = a * eo((lt - 0.2 - 0.1 * i) / 0.4) * (1 - 0.85 * ss((t - t_y) / 0.6))
        fr.line((x, y), tuple(c), GOLD, kk * 0.18, 1.2, glow=0.4)
        fr.text(WORDS[i], x, y, int(40 + 22 * d), 'serif_bold', 'white', kk * (0.55 + 0.45 * d), glow=0.15)
    P = np.array([(p[0], p[1]) for p in pos])
    u = (CS_U + lt * 0.5) % 1.0
    xy = P[CS_W] * (1 - u[:, None]) + c[None, :] * u[:, None]
    fr.splat(xy[:, 0], xy[:, 1], GOLD, a * 0.6 * np.sin(np.pi * u) * cl((lt - 0.4) / 0.5))
    kk = a * cl((t - t_y) / 0.25)
    if kk > 0:
        p = eo((t - t_y) / 0.7)
        fr.glow(tuple(c), 260 * p, GOLD, kk * 0.25)
        fr.circle(tuple(c), 60 + 600 * eo((t - t_y) / 1.0), GOLD_HI, kk * (1 - cl((t - t_y) / 1.0)), 3, glow=1.2)
        fr.text('【预期】', CX, c[1], 190, 'serif_black', 'white', kk, scale=1.35 - 0.35 * p, blur=(1 - p) * 6, glow=0.55)
        fr.flash = max(fr.flash, 0.2 * math.exp(-(t - t_y) / 0.1))
    fr.zoom = 1 + 0.06 * ei((t - (SEC['causes'][1] - 0.8)) / 0.8)
