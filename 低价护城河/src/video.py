"""《低价格，不是护城河》全部分镜（1080×1920 · 30fps）。
python3 src/video.py WORK still t1 t2 ...    → WORK/still_<t>.png（抽帧检查）
python3 src/video.py WORK chunk f0 f1 out.mp4 → 渲染 [f0,f1) 帧
"""
import os, sys, json, math, subprocess
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'brand'))
from engine import *
from timeline import TL, BEAT
from brand import Hud, load_logo

WORK = sys.argv[1]; tl = TL(WORK); HIT = json.load(open(os.path.join(WORK, 'hits.json')))
T, E, SP, SE, WT = tl.T, tl.E, tl.S, tl.SE, tl.WT
TOTAL = tl.total; NF = int(round(TOTAL * FPS))
HUD = Hud(scale=1.0, frame_w=W)
CY = 790          # 画面主体中心
SUB_Y = 1470      # 字幕基线中心
DUST = Dust(80, 1); DUST2 = Dust(40, 9)
CREDIT = json.load(open(os.path.join(MEDIA, 'credits.json')))


def credit(cv, key, a=1.0, y=1330):
    c = CREDIT.get(key)
    if not c: return
    s = '图：%s · %s' % (c.get('artist', '')[:34], c.get('license', '')) if not key.startswith('abc') else '画面：ABC News《20/20》2005 年报道（archive.org）'
    text(cv, s, 56, y, 'sans_light', 22, GREY, anchor='l', alpha=0.75 * a)


def photo(cv, name, t, t0, t1, z0=1.04, z1=1.14, cx0=0.5, cx1=0.5, cy0=0.5, cy1=0.5, a=1.0, **g):
    k = ease(lin(t, t0, t1))
    img = graded(name, **g)
    fr = cover(img, W, H, z0 + (z1 - z0) * k, cx0 + (cx1 - cx0) * k, cy0 + (cy1 - cy0) * k)
    if a >= 0.999: cv[:] = fr
    else: cv *= (1 - a); cv += fr * a


def clipframe(cv, clip, t, t0, z0=1.0, z1=1.08, dur=6.0, a=1.0, sat=0.8, warm=0.25, contrast=1.1, gain=0.95):
    f = clip.get(t - t0)
    f = grade(f, sat=sat, warm=warm, contrast=contrast, gain=gain)
    k = ease(lin(t, t0, t0 + dur)); fr = cover(f, W, H, z0 + (z1 - z0) * k)
    if a >= 0.999: cv[:] = fr
    else: cv *= (1 - a); cv += fr * a


def shade(cv, top=0.35, bottom=0.85, mid=0.15):
    """上下压暗，给标题和字幕留出可读性"""
    y = np.linspace(0, 1, H, dtype=np.float32)
    m = top * np.clip(1 - y / 0.22, 0, 1) + bottom * np.clip((y - 0.55) / 0.45, 0, 1) ** 1.3 + mid
    cv *= (1 - np.clip(m, 0, 0.95))[:, None, None]


def counter(v, fmt='{:,.0f}'): return fmt.format(v)


def label(cv, s, x, y, size=34, color=WHITE, a=1.0, fname='sans_med', anchor='c', **kw):
    return text(cv, s, x, y, fname, size, color, anchor=anchor, alpha=a, shadow=0.6, **kw)


def big(cv, s, x, y, size=120, color=GOLD, a=1.0, fname='serif_black', scale=1.0, glow=0.5, grad=None, track=0.02):
    return text(cv, s, x, y, fname, size, color, alpha=a, scale=scale, shadow=0.7, glow=glow, grad=grad, track=track)


GOLDG = ((1.0, 0.93, 0.72), (0.90, 0.62, 0.26))
REDG = ((1.0, 0.55, 0.48), (0.78, 0.18, 0.16))


def pop(t, t0, d=0.45): return eback(lin(t, t0, t0 + d)), ease(lin(t, t0, t0 + d * 0.6))


# ═══════════════════════════ 场景 ═══════════════════════════
def sc_open(cv, t):
    """冷开场：$1.50 的热狗（暖）→ 白骑的小黄车（冷）→ 一千多万人排队"""
    bg(cv, t)
    if t < T('h2') + 0.2:
        a = ease(lin(t, 0.2, 1.6))
        photo(cv, 'hotdog_drink.jpg', t, 0, T('h2'), 1.22, 1.08, 0.5, 0.5, 0.62, 0.58, a=a, sat=0.95, warm=0.55, contrast=1.12, gain=0.92)
        shade(cv, 0.4, 0.9, 0.12)
        t1 = WT('h1', '一块五'); s, o = pop(t, t1)
        big(cv, '$1.50', W / 2, 1000, 210, a=o, scale=0.8 + 0.2 * s, fname='playfair', grad=GOLDG, glow=0.6)
        ty = WT('h1', '一九八五'); te = WT('h1', '今天', end=True)
        yr = 1985 + (2026 - 1985) * eout(lin(t, ty + 0.2, te))
        o2 = ease(lin(t, ty, ty + 0.4))
        label(cv, '1985', W / 2 - 170, 1185, 56, GOLD_HI, o2, 'oswald')
        label(cv, '→', W / 2, 1185, 48, GOLD, o2 * ease(lin(t, ty + 0.2, ty + 0.6)), 'sans_med')
        label(cv, '%d' % yr, W / 2 + 170, 1185, 56, WHITE, o2 * ease(lin(t, ty + 0.3, ty + 0.7)), 'oswald')
        label(cv, 'COSTCO 热狗套餐 · 价格 40 多年没变', W / 2, 1265, 30, GREY, o2 * 0.9, 'sans_light', track=0.05)
        credit(cv, 'hotdog_drink', o2)
    if t >= T('h2'):
        a = ease(lin(t, T('h2') - 0.05, T('h2') + 0.35))
        tmp = np.empty_like(cv)
        name = 'ofo_station.jpg' if t < T('h3') else 'ofo_hq.jpg'
        if t < T('h3'):
            photo(tmp, name, t, T('h2'), T('h3'), 1.05, 1.16, 0.45, 0.5, 0.6, 0.6, sat=0.55, warm=-0.7, contrast=1.15, gain=0.85)
        else:
            photo(tmp, name, t, T('h3'), T('h4'), 1.1, 1.22, 0.5, 0.55, 0.45, 0.4, sat=0.35, warm=-0.8, contrast=1.2, gain=0.62)
        shade(tmp, 0.35, 0.9, 0.12)
        cv *= (1 - a); cv += tmp * a
        if t < T('h3'):
            s, o = pop(t, WT('h2', '几乎白骑'))
            big(cv, '¥0', W / 2, 600, 220, a=o, scale=0.85 + 0.15 * s, fname='oswald', color=WHITE, glow=0.25)
            label(cv, '补贴大战 · 几乎白骑', W / 2, 760, 38, (0.85, 0.9, 1.0), o * 0.9, 'sans_bold', track=0.1)
            credit(cv, 'ofo_station', o)
        else:
            t3 = WT('h3', '一千多万'); o = ease(lin(t, t3 - 0.3, t3 + 0.2))
            n = 11190000 * eout(lin(t, t3 - 0.3, WT('h3', '押金', end=True)))
            big(cv, counter(n), W / 2, 560, 120, a=o, fname='oswald', color=(1.0, 0.86, 0.80), glow=0.2)
            label(cv, '人在线排队 · 等着退押金', W / 2, 680, 40, WHITE, o, 'sans_bold', track=0.06)
            label(cv, 'ofo 小黄车 · 2018 年 12 月', W / 2, 740, 28, GREY, o * 0.8, 'sans_light', track=0.06)
            # 排队的人：一列列点阵逐渐填满
            lay = layer(); k = lin(t, t3 - 0.3, E('h3'))
            cols, rows = 26, 14; m = int(cols * rows * eout(k))
            for i in range(m):
                x = 120 + (i % cols) * 32.5; y = 880 + (i // cols) * 30
                circle(lay, (x, y), 5.2, fill=True)
            stroke_layer(cv, lay, (0.95, 0.80, 0.30), 0.85, glow=0.6)
            credit(cv, 'ofo_hq', o)


def sc_split(cv, t):
    """同样是便宜：上暖（护城河）下冷（坟墓）；然后发问"""
    bg(cv, t)
    k = eout(lin(t, T('h4') - 0.1, T('h4') + 0.6))
    top = np.empty((H // 2, W, 3), np.float32); bot = np.empty_like(top)
    top[:] = cover(graded('hotdog_drink.jpg', sat=0.95, warm=0.55, contrast=1.12, gain=0.9), W, H // 2, 1.25 + 0.05 * lin(t, T('h4'), T('h5')), 0.5, 0.62)
    bot[:] = cover(graded('ofo_station.jpg', sat=0.3, warm=-0.8, contrast=1.15, gain=0.7), W, H // 2, 1.2 + 0.05 * lin(t, T('h4'), T('h5')), 0.45, 0.62)
    off = int((1 - k) * 220)
    cv[:H // 2] = np.roll(top, -off, 1) * k; cv[H // 2:] = np.roll(bot, off, 1) * k
    dim = 1 - 0.72 * ease(lin(t, T('h5') - 0.1, T('h5') + 0.5))
    cv *= dim
    lay = layer(); line(lay, (0, H / 2), (W * k, H / 2), 3); stroke_layer(cv, lay, GOLD, 0.9, glow=1.5)
    s, o = pop(t, WT('h4', '护城河'))
    hide = 1 - ease(lin(t, T('h5') - 0.15, T('h5') + 0.25))
    big(cv, '护城河', W / 2, H / 4 + 60, 128, a=o * hide, scale=0.9 + 0.1 * s, grad=GOLDG)
    s2, o2 = pop(t, WT('h4', '坟墓'))
    big(cv, '坟　墓', W / 2, H * 3 / 4 - 60, 128, a=o2 * hide, scale=0.9 + 0.1 * s2, color=(0.72, 0.78, 0.86), glow=0.15)
    if t > T('h5') - 0.1:
        s3, o3 = pop(t, WT('h5', '差别'), 0.6)
        big(cv, '差别在哪？', W / 2, H / 2, 132, a=o3, scale=0.92 + 0.08 * s3 + 0.03 * lin(t, T('h5'), HIT['title']), color=WHITE, fname='serif_black', glow=0.3)


def sc_title(cv, t):
    """片名：低价格 ≠ 护城河。金色护城河光环在「不是」处断裂"""
    bg(cv, t, (0.10, 0.08, 0.06))
    t0 = HIT['title']; u = t - t0
    DUST.draw(cv, t, GOLD, 0.35)
    # 冲击波
    if 0 <= u < 1.2:
        lay = layer(); circle(lay, (W / 2, CY), 60 + 900 * eout(u / 1.2), 6 * (1 - u / 1.2) + 1)
        stroke_layer(cv, lay, GOLD_HI, (1 - u / 1.2) * 0.8, glow=2.0, add=True)
    # 护城河光环：完整 → 断成碎片缓缓散开
    lay = layer(); R = 380
    brk = ease(lin(u, 0.9, 2.6))
    for i in range(12):
        a0 = i * 30 + 3; a1 = a0 + 24
        dx = math.sin(math.radians(a0 + 12)) * 60 * brk; dy = -math.cos(math.radians(a0 + 12)) * 60 * brk
        arc(lay, (W / 2 + dx, CY + dy), R + 14 * brk, a0 + 6 * brk * ((i % 2) - 0.5), a1 - 3 * brk, 5)
    stroke_layer(cv, lay, GOLD, ease(lin(u, 0, 0.5)) * (1 - 0.45 * brk), glow=1.6, add=True)
    s, o = pop(t, t0, 0.5)
    big(cv, '低价格', W / 2, CY - 70, 190, a=o, scale=1.12 - 0.12 * s + 0.02 * u / 3, grad=GOLDG, glow=0.7, track=0.08)
    s2, o2 = pop(t, t0 + 0.55, 0.5)
    big(cv, '不是护城河', W / 2, CY + 110, 96, a=o2, scale=0.9 + 0.1 * s2, color=WHITE, fname='serif_semi', glow=0.2, track=0.18)
    label(cv, 'LOW PRICE IS NOT A MOAT', W / 2, CY + 215, 30, GOLD, o2 * 0.85, 'corm_med', track=0.3)
    # 片名闪光（暖色、短）
    if 0 <= u < 0.35: cv += np.asarray((1.0, 0.85, 0.6), np.float32) * (1 - u / 0.35) ** 2 * 0.55


def sc_intuition(cv, t):
    """价格谁都能降：一条条价格线竞相下探，穿过「低价」这堵墙"""
    bg(cv, t, (0.06, 0.07, 0.10))
    x0, x1, y0, y1 = 110, 970, 420, 1180
    lay = layer()
    for i in range(7): line(lay, (x0, y0 + i * (y1 - y0) / 6), (x1, y0 + i * (y1 - y0) / 6), 1)
    stroke_layer(cv, lay, GREY, 0.18)
    label(cv, '价格', x0, y0 - 50, 30, GREY, 0.8, 'sans_med', anchor='l')
    label(cv, '时间 →', x1, y1 + 46, 26, GREY, 0.7, 'sans_light', anchor='r')
    # 你的价格标签
    s, o = pop(t, SP('b1'))
    tw = WT('b1', '谁都能降')
    rng = np.random.default_rng(4)
    n = 6; cols = [GOLD, (0.60, 0.70, 0.85), (0.75, 0.62, 0.85), (0.55, 0.80, 0.75), (0.85, 0.60, 0.55), (0.70, 0.70, 0.70)]
    for j in range(n):
        st = tw + j * 0.18 - (0.6 if j == 0 else 0)
        if j == 0: st = SP('b1') + 0.3
        k = lin(t, st, SE('b2') + 0.4)
        if k <= 0: continue
        drops = np.cumsum(rng.random(9) * 0.12 + 0.03); drops = drops / drops[-1] * (0.80 + 0.12 * rng.random())
        pts = []; ny = y0 + 40 + j * 12
        steps = 9
        for i in range(steps):
            fx = i / (steps - 1)
            if fx > k: break
            px = x0 + fx * (x1 - x0); py = y0 + 40 + drops[i] * (y1 - y0 - 80) * (0.25 if j == 0 and t < tw else 1)
            if pts: pts.append((px, pts[-1][1]))
            pts.append((px, py))
        if len(pts) > 1:
            L = layer(); poly(L, pts, 4 if j == 0 else 3); stroke_layer(cv, L, cols[j], 0.95 if j == 0 else 0.7, glow=1.0)
            px, py = pts[-1]
            price = 100 - 70 * (py - y0 - 40) / (y1 - y0 - 80)
            label(cv, '¥%d' % max(1, price), px + 12, py - 26, 30 if j == 0 else 24, cols[j], 0.95, 'oswald', anchor='l')
    big(cv, '谁都能降', W / 2, 300, 96, a=ease(lin(t, tw, tw + 0.4)), color=WHITE, glow=0.2)
    # 墙：「低价」挡不住任何人
    tb = WT('b2', '挡不住')
    if t > tb - 0.6:
        a = ease(lin(t, tb - 0.6, tb))
        L = layer(); rect(L, 560, y0 - 10, 600, y1 + 10, fill=True); fill(cv, L, (0.95, 0.76, 0.42), 0.16 * a)
        L = layer(); line(L, (560, y0 - 10), (560, y1 + 10), 2); line(L, (600, y0 - 10), (600, y1 + 10), 2)
        stroke_layer(cv, L, GOLD, 0.6 * a, glow=0.8)
        label(cv, '「低价」', 580, y1 + 46, 30, GOLD, a, 'serif_semi')
        big(cv, '挡不住任何人', W / 2, 1290, 70, a=ease(lin(t, tb, tb + 0.4)), color=GOLD_HI, glow=0.3)


def sc_test(cv, t):
    """试金石：同一个价格下，谁还活着？——A/B 两家店"""
    bg(cv, t, (0.06, 0.07, 0.09))
    base = 1180; top = 380; ppu = (base - top) / 110.0   # 每元像素
    yv = lambda v: base - v * ppu
    if t < T('c2'):
        # 两家店，价格牌一路降到同一个数
        tq = WT('c1', '同一个价格'); k = eout(lin(t, SP('c1') + 1.2, tq + 0.3))
        for nm, x, p0, col in (('A', 300, 128, GOLD), ('B', 780, 116, RED)):
            o = ease(lin(t, T('c1') - 0.1, T('c1') + 0.5))
            L = layer(); rect(L, x - 190, 520, x + 190, 1000, r=18); fill(cv, L, (0.12, 0.13, 0.16), 0.9 * o)
            L = layer(); rect(L, x - 190, 520, x + 190, 1000, fill=False, w=3, r=18); stroke_layer(cv, L, col, 0.8 * o, glow=0.8)
            L = layer(); fpoly(L, [(x - 210, 560), (x, 470), (x + 210, 560)]); fill(cv, L, col, 0.85 * o)
            label(cv, '店 ' + nm, x, 620, 46, col, o, 'sans_black')
            v = p0 + (90 - p0) * k
            big(cv, '¥%d' % round(v), x, 800, 128, a=o, fname='oswald', color=WHITE if k < 1 else GOLD_HI, glow=0.2)
            label(cv, '售价', x, 920, 30, GREY, o, 'sans_med')
        kk = ease(lin(t, tq + 0.1, tq + 0.5))
        L = layer(); line(L, (100, 800), (980, 800), 2); stroke_layer(cv, L, GOLD_HI, 0.0 * kk)
        label(cv, '同一个价格', W / 2, 1080, 44, GOLD_HI, kk, 'sans_bold')
        tw = WT('c1', '谁还活着'); s2, o2 = pop(t, tw, 0.5)
        big(cv, '谁还活着？', W / 2, 1230, 120, a=o2, scale=0.9 + 0.1 * s2, color=WHITE, glow=0.3)
        label(cv, '不是你卖得多便宜', W / 2, 330, 46, GREY, fade(t, SP('c1'), tw, 0.4, 0.4), 'sans_med')
        return
    # 柱图
    pa = ease(lin(t, T('c2'), T('c2') + 0.5))
    L = layer(); line(L, (120, base), (960, base), 2); stroke_layer(cv, L, GREY, 0.6 * pa)
    py = yv(90); tp = WT('c2', '九十块')
    kp = eout(lin(t, tp - 0.2, tp + 0.4))
    L = layer()
    for x in range(120, int(120 + 840 * kp), 28): line(L, (x, py), (x + 16, py), 3)
    stroke_layer(cv, L, WHITE, 0.9, glow=0.6)
    label(cv, '售价 ¥90', 124, py - 34, 34, WHITE, kp, 'sans_bold', anchor='l')
    bars = [('A', 340, 75, GOLD, WT('c2', '七十五'), WT('c2', '赚十五'), '+15', TEAL),
            ('B', 740, 95, RED, WT('c3', '九十五'), WT('c3', '亏五块'), '−5', RED)]
    for nm, cx, cost, col, tc, tr, res, rc in bars:
        kb = eout(lin(t, tc - 0.25, tc + 0.5)); h = cost * ppu * kb
        L0 = layer(); rect(L0, cx - 110, yv(cost), cx + 110, base, fill=False, w=2, r=6); stroke_layer(cv, L0, col, 0.25 * pa)
        L = layer(); rect(L, cx - 110, base - h, cx + 110, base, r=6); fill(cv, L, col, 0.85)
        L2 = layer(); rect(L2, cx - 110, base - h, cx + 110, base, fill=False, w=2, r=6); stroke_layer(cv, L2, mix(col, (1, 1, 1), 0.4), 0.7, glow=0.8)
        label(cv, nm, cx, base + 60, 54, col, pa, 'oswald')
        label(cv, '成本 ¥%d' % cost, cx, base - h + 44, 36, INK, kb, 'sans_bold')
        kr = ease(lin(t, tr - 0.15, tr + 0.3))
        if kr > 0:
            y_a, y_b = sorted((yv(cost), py))
            L = layer(); rect(L, cx - 110, y_a, cx + 110, y_b); fill(cv, L, rc, 0.45 * kr)
            s, o = pop(t, tr - 0.1)
            big(cv, res, cx, y_a - 70, 92, a=o, scale=0.8 + 0.2 * s, fname='oswald', color=mix(rc, (1, 1, 1), 0.2), glow=0.5)
    # B 在失血：红色滴落
    tb = WT('c3', '亏五块')
    if t > tb:
        L = layer(); rr = np.random.default_rng(11)
        for i in range(26):
            ph = rr.random(); sp = 90 + rr.random() * 120; x = 640 + rr.random() * 200
            y = yv(90) + ((t - tb) * sp + ph * 600) % 700
            if y < base: circle(L, (x, y), 3 + rr.random() * 3, fill=True)
        stroke_layer(cv, L, RED, 0.8 * ease(lin(t, tb, tb + 0.5)), glow=1.0)
    ta = WT('c4', '武器'); tbl = WT('c4', '失血')
    s, o = pop(t, ta); big(cv, '武器', 340, 300, 108, a=o, scale=0.85 + 0.15 * s, grad=GOLDG)
    s, o = pop(t, tbl); big(cv, '失血', 740, 300, 108, a=o, scale=0.85 + 0.15 * s, grad=REDG)


def sc_buffett(cv, t):
    """巴菲特 2007 年致股东信：low-cost producer"""
    bg(cv, t, (0.07, 0.065, 0.06))
    a = ease(lin(t, T('d1') - 0.3, T('d1') + 0.6))
    img = graded('buffett_2015.jpg', sat=0.25, warm=0.5, contrast=1.1, gain=0.85)
    ph = cover(img, W, 760, 1.1 + 0.08 * lin(t, T('d1'), E('d2')), 0.36, 0.40)
    fadeb = np.clip((760 - np.arange(760)) / 220, 0, 1).astype(np.float32)[:, None, None]
    cv[80:840] = cv[80:840] * (1 - fadeb * a) + ph * fadeb * a
    label(cv, '巴菲特 · 2007 年致股东信', 60, 180, 32, GOLD, a, 'serif_semi', anchor='l')
    credit(cv, 'buffett_2015', a, 770)
    # 信纸
    px0, py0, px1, py1 = 70, 800, 1010, 1100
    L = layer(); rect(L, px0, py0, px1, py1, r=10); fill(cv, L, (0.93, 0.89, 0.80), 0.95 * a)
    q = ['"...a formidable barrier such as a', "company's being the low-cost producer", '(GEICO, Costco) or possessing a powerful', 'world-wide brand ... is essential for', 'sustained success."']
    tot = sum(len(s) for s in q); k = lin(t, SP('d1') + 0.4, SE('d1') + 0.8); shown = int(tot * k)
    y = py0 + 50
    for s in q:
        n = max(0, min(len(s), shown)); shown -= len(s)
        if n > 0: text(cv, s[:n], px0 + 40, y, 'typewriter', 33, (0.16, 0.13, 0.10), anchor='l', alpha=a)
        y += 52
    # 「low-cost producer」高亮
    th = HIT['lowcost']
    if t > th - 0.3:
        kh = eout(lin(t, th - 0.3, th + 0.4))
        xs = px0 + 40 + text_w("company's being the ", 'typewriter', 33); xe = xs + text_w('low-cost producer', 'typewriter', 33)
        L = layer(); rect(L, xs - 4, py0 + 50 + 52 - 22, xs + (xe - xs) * kh + 4, py0 + 50 + 52 + 22, r=4)
        fill(cv, L, (0.98, 0.78, 0.30), 0.45)
    # 中文结论
    tn = WT('d2', '不是价格最低')
    # 叠在照片上的两行对比（放在上半区，避开字幕）
    ya = 1190; yb = 1320
    if t > tn - 0.1:
        k1 = ease(lin(t, tn, tn + 0.35))
        big(cv, '价格最低', W / 2, ya, 84, a=k1 * (1 - 0.55 * ease(lin(t, th - 0.2, th + 0.3))), color=WHITE, glow=0.1)
        ks = eout(lin(t, WT('d2', '而是') - 0.2, WT('d2', '而是') + 0.25))
        if ks > 0:
            L = layer(); line(L, (W / 2 - 220, ya + 4), (W / 2 - 220 + 440 * ks, ya - 4), 8); stroke_layer(cv, L, RED, 0.95, glow=1)
    s, o = pop(t, th, 0.5)
    big(cv, '成本最低的生产者', W / 2, yb, 86, a=o, scale=0.9 + 0.1 * s, grad=GOLDG, glow=0.7)


def chip_stack(cv, t, x, y, active, alphas):
    """被让出去的 10 元：三块来源"""
    names = [('补贴', '自己掏钱', RED), ('转移', '供应商让利', (0.95, 0.60, 0.25)), ('效率', '成本真的降了', GOLD)]
    for i, (n, d, c) in enumerate(names):
        a = alphas[i]
        if a <= 0: continue
        yy = y + i * 128
        on = active == i
        L = layer(); rect(L, x, yy, x + 560, yy + 108, r=12); fill(cv, L, c, (0.85 if on else 0.18) * a)
        L = layer(); rect(L, x, yy, x + 560, yy + 108, fill=False, w=2, r=12); stroke_layer(cv, L, c, 0.9 * a, glow=1.2 if on else 0.2)
        label(cv, '%d  %s' % (i + 1, n), x + 30, yy + 54, 48, INK if on else c, a, 'sans_black', anchor='l')
        label(cv, d, x + 530, yy + 54, 30, INK if on else GREY, a, 'sans_med', anchor='r')


def sc_sources(cv, t):
    bg(cv, t, (0.07, 0.07, 0.08))
    te1 = SP('e1')
    # 价格柱：100 → 90，让出的 10 元高亮
    k = eout(lin(t, te1, te1 + 1.0))
    L = layer(); rect(L, 150, 330, 330, 1130, r=8); fill(cv, L, (0.30, 0.32, 0.36), 0.9)
    cut = 330 + 80 * k
    L = layer(); rect(L, 150, cut, 330, 1130, r=8); fill(cv, L, (0.42, 0.50, 0.62), 0.9)
    label(cv, '售价', 240, 1080, 30, WHITE, 0.9, 'sans_bold')
    label(cv, '¥%d' % round(100 - 10 * k), 240, 1180, 44, WHITE, 1, 'oswald')
    if k > 0.1:
        L = layer(); rect(L, 150, 330, 330, cut, fill=False, w=3, r=8); stroke_layer(cv, L, GOLD, k, glow=1.5)
        label(cv, '让出去的钱', 240, 290, 30, GOLD, k, 'sans_med')
        L = layer(); poly(L, [(335, (330 + cut) / 2), (390, (330 + cut) / 2), (390, 560), (420, 560)], 2)
        stroke_layer(cv, L, GOLD, ease(lin(t, te1 + 0.8, te1 + 1.4)) * 0.8)
    al = [ease(lin(t, te1 + 1.2 + i * 0.25, te1 + 1.6 + i * 0.25)) for i in range(3)]
    act = -1
    for i, l in enumerate(('e2', 'e3', 'e4')):
        if t >= HIT[l] - 0.1: act = i
    if act == 2: al = [a * (1 - 0.6 * ease(lin(t, HIT['eff'], HIT['eff'] + 0.6))) if i < 2 else a for i, a in enumerate(al)]
    chip_stack(cv, t, 430, 470, act, al)
    yb = 980
    if act == 0:  # 补贴：烧钱的火星
        L = layer(); rr = np.random.default_rng(5)
        for i in range(60):
            ph = rr.random(); x = 470 + rr.random() * 480; life = ((t - HIT['e2']) * 0.7 + ph) % 1
            circle(L, (x + math.sin(life * 9 + ph * 6) * 12, yb + 220 - life * 260), 2 + 3 * (1 - life), v=1 - life, fill=True)
        stroke_layer(cv, L, (1.0, 0.45, 0.20), 0.9, glow=1.6, add=True)
        label(cv, '钱烧完 → 客户就走', 710, yb + 40, 40, (1.0, 0.7, 0.6), ease(lin(t, WT('e2', '钱烧完'), WT('e2', '钱烧完') + 0.3)), 'sans_bold')
    elif act == 1:  # 转移：供应商被挤压
        tq = WT('e3', '挤得太狠'); kq = eout(lin(t, tq - 0.3, tq + 0.6))
        cx = 710; w = 300 - 120 * kq
        L = layer(); rect(L, cx - w / 2, yb + 20, cx + w / 2, yb + 160, r=10); fill(cv, L, (0.95, 0.60, 0.25), 0.8)
        label(cv, '供应商', cx, yb + 90, 36, INK, 1, 'sans_black')
        L = layer()
        for sgn in (-1, 1):
            xa = cx + sgn * (w / 2 + 90); xb = cx + sgn * (w / 2 + 10)
            line(L, (xa, yb + 90), (xb, yb + 90), 8); line(L, (xb, yb + 90), (xb + sgn * 26, yb + 66), 8); line(L, (xb, yb + 90), (xb + sgn * 26, yb + 114), 8)
        stroke_layer(cv, L, WHITE, 0.9)
        tc = WT('e3', '质量和创新'); o = ease(lin(t, tc - 0.2, tc + 0.3))
        label(cv, '质量 ↓   创新 ↓', cx, yb + 230, 44, RED, o, 'sans_black')
    elif act == 2:  # 效率：齿轮 + 护城河光环
        tg = HIT['eff']; kg = ease(lin(t, tg - 0.2, tg + 0.5))
        L = layer(); c = (710, yb + 110); r = 90; ang = (t - tg) * 40
        for i in range(12):
            a0 = ang + i * 30
            p0 = (c[0] + r * math.sin(math.radians(a0)), c[1] - r * math.cos(math.radians(a0)))
            p1 = (c[0] + (r + 28) * math.sin(math.radians(a0)), c[1] - (r + 28) * math.cos(math.radians(a0)))
            line(L, p0, p1, 16)
        circle(L, c, r, 10); circle(L, c, 34, 8)
        stroke_layer(cv, L, GOLD, kg, glow=1.5)
        tm = WT('e4', '撑得起护城河'); km = eout(lin(t, tm - 0.2, tm + 0.8))
        if km > 0:
            L = layer(); circle(L, c, 150 + 40 * km, 6); stroke_layer(cv, L, GOLD_HI, km, glow=2.0, add=True)
            label(cv, '护城河的地基', c[0], c[1] + 230, 40, GOLD_HI, km, 'serif_black')


def flywheel(cv, t, c, R, labels, tstarts, col=GOLD, spin=0.0, alpha=1.0, rev=False, red=0.0):
    n = len(labels); colr = mix(col, RED, red)
    L = layer(); circle(L, c, R, 3); stroke_layer(cv, L, colr, 0.35 * alpha)
    for i, (lab, ts) in enumerate(zip(labels, tstarts)):
        ang = i * 360 / n + spin
        on = ease(lin(t, ts - 0.1, ts + 0.35))
        p = (c[0] + R * math.sin(math.radians(ang)), c[1] - R * math.cos(math.radians(ang)))
        # 弧形箭头（到下一个节点）
        if on > 0:
            a0 = ang + 22; a1 = ang + 360 / n - 22
            L = layer(); arc(L, c, R, a0, a0 + (a1 - a0) * eout(lin(t, ts, ts + 0.6)), 7)
            if lin(t, ts, ts + 0.6) >= 1:
                da = -1 if rev else 1
                tip = a1 if not rev else a0
                pt = (c[0] + R * math.sin(math.radians(tip)), c[1] - R * math.cos(math.radians(tip)))
                b = math.radians(tip + da * 90)
                for s in (-1, 1):
                    q = (pt[0] - 26 * math.sin(b + s * 0.5) * (-1 if rev else 1) * -1, pt[1] + 26 * math.cos(b + s * 0.5) * -1)
                    line(L, pt, (pt[0] - 24 * math.sin(math.radians(tip + 90 * da) + s * 0.55), pt[1] + 24 * math.cos(math.radians(tip + 90 * da) + s * 0.55)), 6)
            stroke_layer(cv, L, colr, 0.9 * alpha, glow=1.3)
        L = layer(); circle(L, p, 92, fill=True); fill(cv, L, INK, 0.85 * alpha * max(0.3, on))
        L = layer(); circle(L, p, 92, 4); stroke_layer(cv, L, colr, alpha * (0.3 + 0.7 * on), glow=1.4 * on)
        s, o = pop(t, ts)
        for j, part in enumerate(lab.split('\n')):
            label(cv, part, p[0], p[1] + (j - (len(lab.split('\n')) - 1) / 2) * 44, 38, mix(WHITE, colr, 0.3), alpha * max(0.25, o), 'sans_black', scale=0.9 + 0.1 * s)


def sc_costco(cv, t):
    bg(cv, t, (0.08, 0.07, 0.06))
    if t < T('f2'):
        clipframe(cv, CLIPS['cans'], t, T('f1') - 0.6, 1.0, 1.1, 7)
        shade(cv, 0.35, 0.9, 0.15)
        label(cv, 'COSTCO', W / 2, 520, 64, WHITE, ease(lin(t, T('f1'), T('f1') + 0.6)), 'oswald', track=0.3)
        tp = WT('f1', '百分之十四'); s, o = pop(t, tp - 0.15)
        big(cv, '加价 ≤ 14%', W / 2, 760, 118, a=o, scale=0.85 + 0.15 * s, grad=GOLDG)
        label(cv, '据多家媒体报道（Costco 未正式披露）', W / 2, 880, 28, GREY, o, 'sans_light')
        credit(cv, 'abc_2005', 1)
        return
    if t < T('f4'):
        # 背景：叉车与整托盘（虚化压暗）
        clip = CLIPS['fork'] if t < T('f3') else CLIPS['crowd']
        clipframe(cv, clip, t, T('f2') if t < T('f3') else T('f3') - 3.0, 1.1, 1.18, 7, sat=0.5, gain=0.45)
        cv[:] = cv2.GaussianBlur(cv, (0, 0), 6)
        shade(cv, 0.3, 0.8, 0.2)
        c = (W / 2, 760 if t < T('f3') else 600); R = 300 if t < T('f3') else 230
        ts = [WT('f2', '便宜'), WT('f2', '会员越多'), WT('f2', '采购量'), WT('f2', '规模压低成本')]
        sp = 30 * max(0, t - WT('f2', '成本又换来')) ** 1.6
        a_w = 1 - 0.0 * ease(lin(t, T('f3'), T('f3') + 0.5))
        flywheel(cv, t, c, R, ['低价', '会员\n更多', '采购量\n更大', '成本\n更低'], ts, GOLD, spin=sp, alpha=a_w)
        if t < T('f3'):
            label(cv, '飞轮', c[0], c[1], 64, GOLD_HI, ease(lin(t, ts[0], ts[0] + 0.5)), 'serif_black')
        if t >= T('f3') - 0.2:
            a = ease(lin(t, T('f3') - 0.2, T('f3') + 0.4))
            # 两张数据卡
            tm = WT('f3', '会员费'); tr = WT('f3', '续费率')
            for k_, (x, ts_, val, frac, l1, l2) in enumerate(((290, tm, '≈50%', 0.506, '会员费', '占经营利润'), (790, tr, '89.8%', 0.898, '全球', '续费率'))):
                kk = eout(lin(t, ts_ - 0.2, ts_ + 0.9))
                cy = 1080
                L = layer(); circle(L, (x, cy), 150, 18); stroke_layer(cv, L, (0.3, 0.3, 0.32), a * 0.8)
                L = layer(); arc(L, (x, cy), 150, 0, 360 * frac * kk, 18); stroke_layer(cv, L, GOLD, a * ease(lin(t, ts_ - 0.2, ts_)), glow=1.4)
                label(cv, val, x, cy - 10, 64, WHITE, a * ease(lin(t, ts_ - 0.2, ts_ + 0.2)), 'oswald')
                label(cv, l1 + l2, x, cy + 230, 34, GOLD_HI, a * ease(lin(t, ts_ - 0.2, ts_ + 0.2)), 'sans_bold')
            label(cv, 'Costco 2026 财年：会员费 59 亿美元 / 经营利润约 117 亿美元；美加续费率 92.3%', W / 2, 1378, 22, GREY, a, 'sans_light')
        return
    if t < T('f5'):
        bg(cv, t, (0.09, 0.08, 0.06)); DUST.draw(cv, t, GOLD, 0.35)
        s, o = pop(t, WT('f4', '规模经济分享'), 0.6)
        label(cv, '投资人 尼克·斯利普 Nick Sleep', W / 2, 560, 34, GREY, ease(lin(t, T('f4'), T('f4') + 0.5)), 'sans_med')
        big(cv, '规模经济分享', W / 2, 760, 124, a=o, scale=0.92 + 0.08 * s, grad=GOLDG, glow=0.6)
        label(cv, 'SCALE  ECONOMIES  SHARED', W / 2, 900, 40, GOLD, o, 'corm_med', track=0.15)
        L = layer(); line(L, (W / 2 - 300 * o, 960), (W / 2 + 300 * o, 960), 2); stroke_layer(cv, L, GOLD, o * 0.7, glow=1)
        label(cv, '把效率省下的钱，让给顾客 → 换来更大的规模', W / 2, 1030, 34, WHITE, o * 0.9, 'sans_med')
        return
    clipframe(cv, CLIPS['floor'] if t < HIT['scale'] else CLIPS['aisle'], t, T('f5') if t < HIT['scale'] else HIT['scale'], 1.0, 1.1, 4)
    shade(cv, 0.35, 0.9, 0.2)
    label(cv, '想和它一样便宜？', W / 2, 600, 64, WHITE, ease(lin(t, T('f5'), T('f5') + 0.4)), 'sans_black')
    s, o = pop(t, HIT['scale'], 0.5)
    big(cv, '先拥有它的规模', W / 2, 780, 110, a=o, scale=0.88 + 0.12 * s, grad=GOLDG, glow=0.7)
    u = t - HIT['scale']
    if 0 <= u < 0.3: cv += np.asarray((1.0, 0.85, 0.6), np.float32) * (1 - u / 0.3) ** 2 * 0.4
    credit(cv, 'abc_2005', 1)


def sc_china(cv, t):
    bg(cv, t, (0.10, 0.05, 0.05))
    if t < T('g2'):
        DUST2.draw(cv, t, (1.0, 0.55, 0.40), 0.35)
        s, o = pop(t, T('g1'), 0.5)
        big(cv, '中国考题', W / 2, 700, 150, a=o, scale=0.9 + 0.1 * s, grad=((1.0, 0.85, 0.7), (0.85, 0.30, 0.22)), glow=0.6)
        label(cv, '比亚迪　·　拼多多', W / 2, 880, 50, WHITE, ease(lin(t, T('g1') + 0.4, T('g1') + 0.9)), 'serif_semi', track=0.1)
        return
    if t < T('g5'):
        # 比亚迪
        if t < T('g3'):
            photo(cv, 'byd_seal.jpg', t, T('g2') - 0.3, T('g3'), 1.0, 1.12, 0.62, 0.58, 0.55, 0.55, sat=0.85, warm=-0.1, contrast=1.15, gain=0.85)
            shade(cv, 0.45, 0.92, 0.22); credit(cv, 'byd_seal', 1)
        else:
            photo(cv, 'byd_seagull.jpg', t, T('g3'), T('g5'), 1.12, 1.26, 0.5, 0.48, 0.55, 0.55, sat=0.6, warm=0.1, contrast=1.12, gain=0.7)
            shade(cv, 0.4, 0.92, 0.5); credit(cv, 'byd_seagull', 1)
        label(cv, 'BYD · 比亚迪', 60, 190, 40, WHITE, 1, 'sans_black', anchor='l')
        if t < T('g3') + 0.3:
            a_out = 1 - ease(lin(t, T('g3') - 0.55, T('g3') - 0.1))
            for i, (w_, key) in enumerate((('电池', '电池'), ('电机', '电机'), ('芯片', '芯片'))):
                ts = WT('g2', key); s, o = pop(t, ts - 0.1)
                x = 200 + i * 340; y = 420
                L = layer(); rect(L, x - 130, y - 60, x + 130, y + 60, r=60); fill(cv, L, GOLD, 0.88 * o * a_out)
                label(cv, w_, x, y, 54, INK, o * a_out, 'sans_black', scale=0.85 + 0.15 * s)
            tz = WT('g2', '自己造'); label(cv, '垂直整合 · 大量自研自产', W / 2, 530, 36, GOLD_HI, ease(lin(t, tz, tz + 0.4)) * a_out, 'sans_bold')
            tn = WT('g2', '四百六十万'); kn = eout(lin(t, tn - 0.3, tn + 0.9))
            on = ease(lin(t, tn - 0.3, tn)) * a_out
            big(cv, '%d' % round(460 * kn), W / 2 - 60, 760, 130, a=on, fname='oswald', grad=GOLDG)
            big(cv, '万辆', W / 2 + 130, 776, 60, a=on, fname='sans_black', color=GOLD_HI, glow=0.2)
            label(cv, '2025 年销量（含商用车约 460.2 万辆）', W / 2, 870, 30, WHITE, ease(lin(t, tn, tn + 0.4)) * a_out, 'sans_light')
            te = WT('g2', '实打实的效率'); s, o = pop(t, te)
            label(cv, '✓ 真实的效率', W / 2, 990, 50, TEAL, o * a_out, 'sans_black', scale=0.9 + 0.1 * s)
        if t > T('g3'):
            a = ease(lin(t, T('g3'), T('g3') + 0.4))
            # 供应链：供应商 → 比亚迪
            L = layer(); rect(L, 80, 380, 440, 520, r=14); fill(cv, L, (0.95, 0.6, 0.25), 0.85 * a)
            L = layer(); rect(L, 640, 380, 1000, 520, r=14); fill(cv, L, (0.92, 0.92, 0.95), 0.85 * a)
            label(cv, '供应商', 260, 450, 50, INK, a, 'sans_black'); label(cv, '比亚迪', 820, 450, 50, INK, a, 'sans_black')
            L = layer(); line(L, (450, 450), (630, 450), 6); line(L, (630, 450), (604, 430), 6); line(L, (630, 450), (604, 470), 6)
            stroke_layer(cv, L, WHITE, a)
            tc = WT('g3', '百分之十'); s, o = pop(t, tc - 0.1)
            big(cv, '−10%', 260, 640, 110, a=o, scale=0.85 + 0.15 * s, fname='oswald', grad=REDG)
            label(cv, '年降目标（2024.11）', 260, 740, 30, WHITE, o, 'sans_med')
            label(cv, '比亚迪回应：行业惯例，可协商', 260, 790, 24, GREY, o, 'sans_light')
            tz = WT('g3', '账期'); kz = ease(lin(t, tz - 0.2, tz + 0.3))
            # 账期时钟：长 → 承诺 60 天
            t60 = HIT['d60']; k6 = eout(lin(t, t60 - 0.4, t60 + 0.6))
            days = 275 + (60 - 275) * k6 if t > T('g4') - 0.3 else 275 * eout(lin(t, tz - 0.2, tz + 1.0))
            c = (820, 720)
            L = layer(); circle(L, c, 110, 10); stroke_layer(cv, L, (0.3, 0.3, 0.32), kz)
            col = mix(RED, TEAL, k6)
            L = layer(); arc(L, c, 110, 0, 360 * min(1, days / 365), 12); stroke_layer(cv, L, col, kz, glow=1.3)
            label(cv, '%d' % round(days), c[0] - 14, c[1], 58, WHITE, kz, 'oswald'); label(cv, '天', c[0] + 52, c[1] + 6, 30, WHITE, kz, 'sans_bold')
            label(cv, '账期', c[0], c[1] + 160, 34, col, kz, 'sans_bold')
            label(cv, '2023 年平均约 275 天（彭博汇总）' if k6 < 0.5 else '2025.06 承诺：60 天内付款', c[0], c[1] + 205, 24, GREY, kz, 'sans_light')
            if t > T('g4') - 0.2:
                s, o = pop(t, t60 - 0.2)
                big(cv, '60 天内付款', W / 2, 1000, 96, a=o, scale=0.9 + 0.1 * s, color=TEAL, glow=0.4)
                label(cv, '与多家车企一起承诺 · 2025 年 6 月', W / 2, 1100, 30, WHITE, o, 'sans_med')
        return
    if t < T('g8'):
        # 拼多多：双边平台
        # 先给 1.6 秒门店实拍（自提柜 · 0 运费），再压暗虚化，叠上双边平台示意
        kd = ease(lin(t, T('g5') + 1.4, T('g5') + 2.2))
        photo(cv, 'pdd_boxes.jpg', t, T('g5') - 0.3, T('g8'), 1.05, 1.2, 0.45, 0.5, 0.42, 0.45, sat=0.9 - 0.4 * kd, warm=0.1, contrast=1.1, gain=0.9 - 0.62 * kd)
        if kd > 0:
            b_ = cv2.GaussianBlur(cv, (0, 0), 6); cv *= (1 - kd); cv += b_ * kd
        shade(cv, 0.4, 0.9, 0.1)
        credit(cv, 'pdd_boxes', 1 - kd)
        if kd < 1:
            label(cv, '0 运费 · 低价心智', W / 2, 1290, 40, WHITE, fade(t, T('g5') + 0.2, T('g5') + 2.0, 0.3, 0.4), 'sans_black')
        label(cv, 'PDD · 拼多多', 60, 190, 40, WHITE, 1, 'sans_black', anchor='l')
        c = (W / 2, 760)
        rr = np.random.default_rng(21)
        tb = max(WT('g5', '海量买家'), T('g5') + 1.6); kb = eout(lin(t, tb - 0.4, tb + 0.8))
        tm = max(WT('g5', '商家彼此竞争'), T('g5') + 2.0); km = eout(lin(t, tm - 0.4, tm + 0.8))
        L = layer(); Lm = layer()
        for i in range(150):
            ang = rr.random() * math.pi; rad = 0.55 + rr.random() * 0.45
            if rr.random() < kb:
                circle(L, (c[0] + math.cos(ang) * 420 * rad, c[1] - 140 - math.sin(ang) * 300 * rad), 5, fill=True)
        for i in range(70):
            ang = rr.random() * math.pi; rad = 0.5 + rr.random() * 0.5
            jit = math.sin(t * 7 + i) * 6 * km
            if rr.random() < km:
                circle(Lm, (c[0] + math.cos(ang) * 400 * rad + jit, c[1] + 160 + math.sin(ang) * 260 * rad), 8, fill=True)
        stroke_layer(cv, L, BLUE, 0.9, glow=0.9); stroke_layer(cv, Lm, (0.95, 0.6, 0.25), 0.9, glow=0.9)
        label(cv, '买家', c[0], c[1] - 470, 40, BLUE, kb, 'sans_black')
        label(cv, '商家', c[0], c[1] + 470, 40, (0.95, 0.6, 0.25), km, 'sans_black')
        kp = ease(lin(t, T('g5') + 1.5, T('g5') + 2.0))
        L = layer(); circle(L, c, 90, fill=True); fill(cv, L, (0.85, 0.20, 0.18), 0.95 * kp)
        label(cv, '平台', c[0], c[1], 48, WHITE, kp, 'sans_black')
        # 收入从商家流向平台
        tr = WT('g5', '收入'); kr = ease(lin(t, tr - 0.2, tr + 0.4))
        if kr > 0:
            L = layer()
            for i in range(24):
                ph = (t * 0.8 + i / 24) % 1; ang = (i * 0.618 % 1) * math.pi
                sx = c[0] + math.cos(ang) * 330; sy = c[1] + 160 + math.sin(ang) * 200
                circle(L, (sx + (c[0] - sx) * ph, sy + (c[1] - sy) * ph), 4, v=1 - ph * 0.6, fill=True)
            stroke_layer(cv, L, GOLD_HI, kr, glow=1.6, add=True)
            label(cv, '收入主要来自商家：营销服务 + 交易服务', W / 2, 1310, 26, GOLD_HI, kr, 'sans_med')
        if t > T('g6') - 0.2:
            a = ease(lin(t, T('g6') - 0.2, T('g6') + 0.3))
            cv *= 1 - 0.82 * a
            tq = WT('g6', '商家还赚不赚得到钱'); s, o = pop(t, tq)
            big(cv, '商家还赚得到钱吗？', W / 2, 640, 92, a=o, scale=0.9 + 0.1 * s, color=WHITE, glow=0.3)
            label(cv, '不是：消费者能买多便宜', W / 2, 500, 40, GREY, a * (1 - 0.0), 'sans_med')
            L = layer(); line(L, (W / 2 - 230, 500), (W / 2 - 230 + 460 * ease(lin(t, WT('g6', '而是') - 0.2, WT('g6', '而是') + 0.2)), 500), 4)
            stroke_layer(cv, L, RED, a)
            if t > T('g7') - 0.2:
                tk = WT('g7', '一千亿'); s, o = pop(t, tk - 0.1)
                big(cv, '千亿扶持', W / 2, 850, 110, a=o, scale=0.9 + 0.1 * s, grad=GOLDG)
                label(cv, '2025.04 宣布：未来 3 年投入超 1000 亿元资金、流量等资源', W / 2, 960, 28, WHITE, o, 'sans_med')
                label(cv, 'PDD 2026Q3：营收 1083 亿元 · 经营利润 312 亿元', W / 2, 1010, 24, GREY, o, 'sans_light')
        return
    # g8：天平 → 护城河加宽 / 透支
    DUST2.draw(cv, t, GOLD, 0.25)
    te = WT('g8', '效率'); tr = WT('g8', '让利')
    tilt = 0.0
    c = (W / 2, 520)
    a = ease(lin(t, T('g8') - 0.2, T('g8') + 0.3))
    L = layer(); line(L, (c[0], c[1] - 40), (c[0], c[1] + 170), 5)
    k1 = ease(lin(t, te - 0.1, te + 0.3)); k2 = ease(lin(t, tr - 0.1, tr + 0.3))
    tilt = math.sin(t * 2.2) * 6 * k2 + 0
    ra = math.radians(tilt); dx = 300 * math.cos(ra); dy = 300 * math.sin(ra)
    line(L, (c[0] - dx, c[1] - 40 + dy), (c[0] + dx, c[1] - 40 - dy), 5)
    stroke_layer(cv, L, WHITE, a * 0.8)
    label(cv, '效率', c[0] - dx, c[1] + 40 + dy, 60, GOLD, k1, 'sans_black')
    label(cv, '别人的让利', c[0] + dx, c[1] + 40 - dy, 52, RED, k2, 'sans_black')
    # 俯视护城河：加宽（金）/ 干涸（红）
    tw = WT('g8', '加宽'); tt = HIT['overdraw']
    km = ease(lin(t, WT('g8', '护城河') - 0.2, WT('g8', '护城河') + 0.3))
    cc = (W / 2, 1010)
    L = layer(); x0, x1, y0, y1 = cc[0] - 62, cc[0] + 62, cc[1] - 40, cc[1] + 60
    fpoly(L, [(x0, y1), (x0, y0 - 30), (x0 + 24, y0 - 30), (x0 + 24, y0 - 8), (cc[0] - 12, y0 - 8), (cc[0] - 12, y0 - 30), (cc[0] + 12, y0 - 30),
              (cc[0] + 12, y0 - 8), (x1 - 24, y0 - 8), (x1 - 24, y0 - 30), (x1, y0 - 30), (x1, y1)])
    fill(cv, L, (0.88, 0.84, 0.76), km * 0.95)
    L = layer(); rect(L, cc[0] - 18, y1 - 50, cc[0] + 18, y1, r=14); fill(cv, L, INK, km)
    label(cv, '护城河', cc[0], cc[1] + 260, 36, GREY, km, 'sans_med')
    widen = eout(lin(t, tw - 0.1, tw + 0.6)); dry = eout(lin(t, tt - 0.1, tt + 0.6))
    rw = 150 + 40 * widen
    L = layer(); circle(L, cc, rw, 26 + 30 * widen * (1 - dry)); stroke_layer(cv, L, mix((0.35, 0.65, 0.95), RED, dry), km * (1 - 0.6 * dry), glow=1.5)
    if dry > 0:
        L = layer(); rr = np.random.default_rng(2)
        for i in range(14):
            a0 = rr.random() * 360; arc(L, cc, rw, a0, a0 + 10, 4)
        stroke_layer(cv, L, (0.3, 0.1, 0.08), dry)
    label(cv, '加宽', cc[0] - 300, cc[1], 54, (0.55, 0.78, 1.0), ease(lin(t, tw - 0.1, tw + 0.3)), 'serif_black')
    label(cv, '透支', cc[0] + 300, cc[1], 54, RED, ease(lin(t, tt - 0.1, tt + 0.3)), 'serif_black')


def sc_quality(cv, t):
    bg(cv, t, (0.10, 0.05, 0.05) if t > WT('q1', '倒转') else (0.07, 0.07, 0.08))
    if t < T('q3'):
        tr = WT('q1', '倒转'); red = ease(lin(t, tr - 0.3, tr + 0.6))
        c = (W / 2, 800); R = 300
        s, o = pop(t, WT('q1', '质量'))
        if t < T('q2'):
            big(cv, '底线：质量', W / 2, 290, 96, a=o, scale=0.9 + 0.1 * s, color=WHITE, glow=0.2)
            ts = [T('q1') + 0.2 + i * 0.12 for i in range(4)]
            labs = ['低价', '会员\n更多', '采购量\n更大', '成本\n更低']
            spin = -60 * max(0, t - tr) ** 1.5
            flywheel(cv, t, c, R, labs, ts, GOLD, spin=spin, red=red)
            label(cv, '偷工减料', W / 2, 1230, 44, RED, ease(lin(t, WT('q1', '偷工减料'), WT('q1', '偷工减料') + 0.3)), 'sans_black')
        else:
            ts = [WT('q2', '质量下滑'), WT('q2', '信任流失'), WT('q2', '复购减少'), WT('q2', '再降价')]
            spin = -30 * (t - T('q2')) - 60 * max(0, T('q2') - tr) ** 1.5
            flywheel(cv, t, c, R, ['质量\n下滑', '信任\n流失', '复购\n减少', '再降价'], ts, RED, spin=spin, rev=True)
            label(cv, '恶性循环', W / 2, 290, 80, RED, ease(lin(t, T('q2'), T('q2') + 0.4)), 'serif_black')
        return
    tw = HIT['worth']
    a = ease(lin(t, T('q3') - 0.1, T('q3') + 0.4))
    label(cv, '消费者买的，从来不是', W / 2, 520, 50, GREY, a, 'sans_med')
    L = layer(); line(L, (W / 2 - 170, 640), (W / 2 - 170 + 340 * ease(lin(t, WT('q3', '而是') - 0.2, WT('q3', '而是') + 0.2)), 640), 8)
    big(cv, '便宜', W / 2, 640, 110, a=a, color=WHITE, glow=0.1); stroke_layer(cv, L, RED, a, glow=1)
    s, o = pop(t, tw, 0.5)
    big(cv, '值不值', W / 2, 860, 160, a=o, scale=0.9 + 0.1 * s, grad=GOLDG, glow=0.8)
    ko = ease(lin(t, tw + 0.8, tw + 1.3))
    label(cv, '值  =  效用  −  价格  −  麻烦', W / 2, 1060, 46, WHITE, ko, 'serif_semi')
    label(cv, '（质量、售后、风险都算在「麻烦」里）', W / 2, 1130, 28, GREY, ko, 'sans_light')


def sc_answer(cv, t):
    bg(cv, t, (0.09, 0.075, 0.05))
    if t < T('z2'):
        photo(cv, 'costco_int2.jpg', t, T('z1'), T('z2'), 1.1, 1.22, 0.5, 0.5, 0.5, 0.45, sat=0.7, warm=0.5, contrast=1.05, gain=0.42)
        cv[:] = cv2.GaussianBlur(cv, (0, 0), 4)
        rows = [('低价', '吸引顾客', '低价吸引'), ('质量', '留住顾客', '质量留住'), ('效率', '支撑低价', '效率支撑'), ('规模', '强化优势', '规模强化')]
        for i, (k_, v_, key) in enumerate(rows):
            ts = WT('z1', key); s, o = pop(t, ts - 0.05)
            y = 470 + i * 200
            big(cv, k_, 330, y, 110, a=o, scale=0.9 + 0.1 * s, grad=GOLDG, glow=0.5)
            label(cv, v_, 450, y + 6, 66, WHITE, o, 'serif_semi', anchor='l')
        credit(cv, 'costco_int2', 1)
        return
    DUST.draw(cv, t, GOLD, 0.4)
    if t < T('z3'):
        a = ease(lin(t, T('z2') - 0.1, T('z2') + 0.4))
        label(cv, '真正的护城河，不是', W / 2, 470, 50, GREY, a, 'sans_med')
        big(cv, '“这家最便宜”', W / 2, 590, 100, a=a, color=WHITE, glow=0.1)
        tq = WT('z2', '在这里'); s, o = pop(t, tq - 0.1, 0.6)
        lines = ['“在这里，我总能', '用更少的钱，', '买到靠得住的东西。”']
        for i, l in enumerate(lines):
            oo = ease(lin(t, tq - 0.1 + i * 0.55, tq + 0.4 + i * 0.55))
            big(cv, l, W / 2, 800 + i * 140, 92, a=oo, grad=GOLDG, glow=0.6)
        return
    a = ease(lin(t, T('z3') - 0.1, T('z3') + 0.4)) * (1 - ease(lin(t, HIT['logo'] - 0.5, HIT['logo'])))
    big(cv, '哪家公司的低价，', W / 2, 640, 84, a=a, color=WHITE, glow=0.15)
    big(cv, '才是真正的护城河？', W / 2, 770, 84, a=a * ease(lin(t, WT('z3', '才是') - 0.1, WT('z3', '才是') + 0.3)), grad=GOLDG, glow=0.5)
    label(cv, '评论区聊聊 ↓', W / 2, 950, 44, GOLD, a * ease(lin(t, WT('z3', '护城河') , WT('z3', '护城河') + 0.4)), 'sans_bold')


LOGO = load_logo(300)


def sc_end(cv, t):
    bg(cv, t, (0.07, 0.07, 0.09)); DUST.draw(cv, t, GOLD, 0.45)
    t0 = HIT['logo']; u = t - t0
    a = ease(lin(u, 0, 0.8)) * (1 - ease(lin(t, TOTAL - 0.8, TOTAL)))
    rgb, al = LOGO
    blit(cv, rgb.astype(np.float32), al.astype(np.float32), W / 2, 740, alpha=a, scale=0.94 + 0.06 * eout(lin(u, 0, 1.2)))
    if 0 <= u < 1.0:
        L = layer(); circle(L, (W / 2, 740), 170 + 500 * eout(u), 4 * (1 - u) + 1); stroke_layer(cv, L, (0.5, 0.75, 1.0), (1 - u) * 0.6, glow=2, add=True)
    big(cv, '巴芒价值', W / 2, 1010, 110, a=a * ease(lin(u, 0.3, 1.0)), grad=((1.0, 0.95, 0.78), (0.88, 0.62, 0.24)), glow=0.6, track=0.12)
    label(cv, 'BUFFETT · MUNGER', W / 2, 1110, 40, (0.84, 0.70, 0.44), a * ease(lin(u, 0.5, 1.2)), 'corm_med', track=0.32)


# ═══════════════════════════ 编排 ═══════════════════════════
CLIPS = {}


def load_clips():
    for k in ('crowd', 'floor', 'aisle', 'cans', 'fork'):
        CLIPS[k] = Clip('abc_%s.mp4' % k, 600, 0.5)


SC = [  # (start, end, fn)
    (0.0, T('h4'), sc_open), (T('h4'), HIT['title'], sc_split), (HIT['title'], T('b1') - 0.25, sc_title),
    (T('b1') - 0.25, T('c1') - 0.2, sc_intuition), (T('c1') - 0.2, T('d1') - 0.3, sc_test), (T('d1') - 0.3, T('e1') - 0.3, sc_buffett),
    (T('e1') - 0.3, T('f1') - 0.3, sc_sources), (T('f1') - 0.3, T('g1') - 0.2, sc_costco), (T('g1') - 0.2, T('q1') - 0.3, sc_china),
    (T('q1') - 0.3, T('z1') - 0.3, sc_quality), (T('z1') - 0.3, HIT['logo'], sc_answer), (HIT['logo'], TOTAL + 1, sc_end)]
XF = 0.45   # 场景间交叉溶解
HARD = {HIT['title']}  # 硬切


def chapter_tag(cv, t):
    chs = tl.d['chapters']; cur = None
    for c in chs:
        if c['name'] and t >= c['start'] - 0.2: cur = c
    if not cur or t > HIT['logo'] - 0.3: return
    nxt = [c['start'] for c in chs if c['start'] > cur['start']] + [HIT['logo']]
    a = fade(t, cur['start'] - 0.2, nxt[0] - 0.2, 0.5, 0.4)
    label(cv, cur['name'], 56, 78, 32, GOLD, a, 'serif_semi', anchor='l')
    label(cv, cur['en'], 58, 122, 20, GREY, a * 0.85, 'corm_med', anchor='l', track=0.3)


# 字幕：按标点切成不超过 15 字的短句，按逐字时间戳显示
NOSUB = {'h5', 'z2', 'z3'}
PUN = '，。：；？！、'


def build_subs():
    out = []
    for s in tl.d['segs']:
        if s['id'] in NOSUB: continue
        tts, sub = s['text'], s['sub'].rstrip('。')
        def clauses(x):
            res = []; cur = ''
            for ch in x:
                cur += ch
                if ch in PUN: res.append(cur); cur = ''
            if cur: res.append(cur)
            return res
        cs, ss = clauses(tts), clauses(sub)
        if len(cs) == len(ss):
            pos = 0; starts = []
            for c in cs: starts.append(pos); pos += len(c)
            pairs = list(zip(ss, starts))
        else:
            pos = 0; pairs = []
            for c in ss: pairs.append((c, int(pos / len(sub) * len(tts)))); pos += len(c)
        # 合并短句
        def ln(x): return sum(0.55 if ch.isdigit() or ch in '.%' else 1 for ch in x.strip(PUN))
        merged = []; carry = None
        for i, (c, k) in enumerate(pairs):
            if carry: c, k = carry[0] + c, carry[1]; carry = None
            n1 = ln(c); n0 = ln(merged[-1][0]) if merged else 99
            sent_end = (not merged) or merged[-1][0][-1] in '。？！：'
            if n1 <= 4 and i + 1 < len(pairs) and sent_end and c[-1] in '，、':
                carry = (c, k); continue          # 句首短语：并到后一句
            if merged and not sent_end and ((n0 + n1 <= 14) or (n1 <= 3 and n0 + n1 <= 18)):
                merged[-1] = (merged[-1][0] + c, merged[-1][1])
            elif merged and n1 <= 3 and n0 + n1 <= 18:
                merged[-1] = (merged[-1][0] + c, merged[-1][1])
            else: merged.append((c, k))
        if carry: merged.append(carry)
        for i, (c, k) in enumerate(merged):
            t0 = s['start'] + s['chars'][min(k, len(s['chars']) - 1)][1] - 0.08
            t1 = (s['start'] + s['chars'][merged[i + 1][1]][1] - 0.1) if i + 1 < len(merged) else s['start'] + s['speech'][1] + 0.25
            txt = c.strip('，。：；、 ')
            if txt: out.append((t0, t1, txt))
    for i in range(len(out) - 1):  # 不重叠
        if out[i][1] > out[i + 1][0] - 0.05: out[i] = (out[i][0], out[i + 1][0] - 0.05, out[i][2])
    return out


SUBS = build_subs()


def subtitle(cv, t):
    for t0, t1, s in SUBS:
        if t0 - 0.1 <= t <= t1 + 0.1:
            a = ease(lin(t, t0 - 0.1, t0 + 0.08)) * (1 - ease(lin(t, t1, t1 + 0.1)))
            n = sum(0.55 if ch.isdigit() or ch in '.%' else 1 for ch in s)
            size = 52 if n <= 16 else int(52 * 16 / n)
            w = text_w(s, 'sans_bold', size) + 70
            L = layer(); rect(L, W / 2 - w / 2, SUB_Y - 46, W / 2 + w / 2, SUB_Y + 46, r=14); fill(cv, L, (0, 0, 0), 0.42 * a)
            text(cv, s, W / 2, SUB_Y, 'sans_bold', size, WHITE, alpha=a, shadow=0.5)


def render(fi):
    t = fi / FPS; cv = np.zeros((H, W, 3), np.float32)
    act = []
    for s0, s1, fn in SC:
        lead = 0 if s0 in HARD else XF / 2; tail = 0 if s1 in HARD else XF / 2
        if s0 - lead <= t < s1 + tail:
            w = 1.0
            if t < s0 + lead and lead: w = min(w, ease((t - (s0 - lead)) / (2 * lead)))
            if t > s1 - tail and tail: w = min(w, 1 - ease((t - (s1 - tail)) / (2 * tail)))
            act.append((w, fn))
    tot = sum(w for w, _ in act) or 1
    for w, fn in act:
        tmp = np.zeros_like(cv); fn(tmp, t); cv += tmp * (w / tot if len(act) > 1 else w)
    chapter_tag(cv, t)
    finish(cv, fi)
    subtitle(cv, t)
    if t < HIT['logo'] - 0.2: HUD.draw(cv, t)
    if t < 0.35: cv *= ease(t / 0.35)
    return cv


def to8(cv): return (np.clip(cv, 0, 1) * 255 + 0.5).astype(np.uint8)


if __name__ == '__main__':
    mode = sys.argv[2]; load_clips()
    if mode == 'still':
        for x in sys.argv[3:]:
            t = float(x); cv2.imwrite(os.path.join(WORK, 'still_%06.2f.png' % t), to8(render(int(round(t * FPS))))[..., ::-1]); print('still', t)
    elif mode == 'chunk':
        f0, f1, out = int(sys.argv[3]), min(int(sys.argv[4]), NF), sys.argv[5]
        p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS),
                              '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
        for fi in range(f0, f1):
            p.stdin.write(to8(render(fi)).tobytes())
            if (fi - f0) % 150 == 0: print('chunk', f0, fi, flush=True)
        p.stdin.close(); p.wait()
    elif mode == 'nf': print(NF)
