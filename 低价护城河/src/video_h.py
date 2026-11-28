"""《便宜≠护城河》横版分镜（1920×1080 · 30fps）。
与竖版共用旁白、配乐、时间线、字幕切分和片尾粒子；每个场景按 16:9 重新构图。
python3 src/video_h.py work still t1 t2 ... / chunk f0 f1 out.mp4 / nf / audit t0 t1 step out.json
直接读竖版 work/ 里的时间线和 hits.json；抽帧输出为 work/hstill_*.png。
"""
import os, sys
os.environ['ORIENT'] = 'h'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import video as V
from video import *          # 引擎、时间线函数、通用小部件（W, H 已是 1920×1080）
import engine as _e

CY = 470
SUB_Y = 960
SRC_Y, CRED_Y = 1032, 1062


def credit(cv, key, a=1.0, y=None):
    c = CREDIT.get(key)
    if not c: return
    s = '图：%s · %s' % (c.get('artist', '')[:34], c.get('license', '')) if not key.startswith('abc') else '画面：ABC News《20/20》2005 年报道（archive.org）'
    text(cv, s, 56, CRED_Y, 'sans_light', 22, GREY, anchor='l', alpha=0.75 * a)


def src_note(cv, s, a=1.0):
    text(cv, s, 56, SRC_Y, 'sans_light', 24, GREY, anchor='l', alpha=0.8 * a)


# ── 引子 · 内卷 ──
def sc_involution(cv, t):
    bg(cv, t, (0.08, 0.07, 0.09))
    if t < T('o2'):
        DUST2.draw(cv, t, (1.0, 0.5, 0.4), 0.25)
        prices = ['¥199', '¥99', '¥49', '¥9.9']
        for i, p in enumerate(prices):
            ts = 0.25 + i * 0.55; s, o = pop(t, ts, 0.35)
            x = 420 + i * 360; dead = i < len(prices) - 1 and t > ts + 0.45
            big(cv, p, x, CY, 150 if i == len(prices) - 1 else 116, a=o * (0.45 if dead else 1), fname='oswald',
                color=RED if i == len(prices) - 1 else WHITE, glow=0.3, scale=0.9 + 0.1 * s)
            if dead:
                kk = eout(lin(t, ts + 0.45, ts + 0.6)); L = layer(); line(L, (x - 150, CY), (x - 150 + 300 * kk, CY), 8)
                stroke_layer(cv, L, RED, 0.9, glow=0.8)
        return
    if t < T('o3'):
        photo(cv, 'solar_wall.jpg', t, T('o2') - 0.3, T('o3'), 1.0, 1.1, 0.42, 0.45, 0.45, 0.45, sat=0.8, warm=-0.2, contrast=1.15, gain=0.75)
        shade(cv, 0.4, 0.92, 0.25)
        label(cv, '光伏组件 · 2024', 60, 200, 40, WHITE, 1, 'sans_black', anchor='l')
        credit(cv, 'solar_wall', 1)
        x0, x1, y0, y1 = 420, 1800, 290, 780; k = eout(lin(t, T('o2') + 0.3, WT('o2', '成本线附近', end=True)))
        L = layer(); line(L, (x0, y1), (x1, y1), 2); stroke_layer(cv, L, GREY, 0.6)
        yc = y0 + (y1 - y0) * 0.72
        L = layer()
        for x in range(x0, x1, 26): line(L, (x, yc), (x + 14, yc), 3)
        oc = ease(lin(t, WT('o2', '成本线'), WT('o2', '成本线') + 0.4))
        stroke_layer(cv, L, (1.0, 0.8, 0.4), oc, glow=0.8)
        label(cv, '行业测算成本线（2024.10 约 0.68 元/W）', x1, yc + 36, 26, GOLD_HI, oc, 'sans_med', anchor='r')
        pts = []
        for i in range(41):
            fx = i / 40
            if fx > k: break
            v = 1 - 0.80 * (1 - math.exp(-3.2 * fx)) / (1 - math.exp(-3.2)) + 0.03 * math.sin(fx * 23)
            pts.append((x0 + fx * (x1 - x0), y0 + (y1 - y0) * (1 - v) * 0.92))
        if len(pts) > 1:
            L = layer(); poly(L, pts, 6); stroke_layer(cv, L, WHITE, 0.95, glow=1.2)
            label(cv, '— 组件价格', x0, y0 - 44, 30, WHITE, 1, 'sans_bold', anchor='l')
        ts = WT('o2', '涉嫌违法'); s, o = pop(t, ts - 0.3, 0.4)
        if o > 0:
            card(cv, 1060, 290, 1800, 460, (0.55, 0.08, 0.07), 0.9 * o, RED)
            label(cv, '低于成本投标，涉嫌违法', 1430, 350, 50, WHITE, o, 'sans_black', scale=0.9 + 0.1 * s)
            label(cv, '—— 中国光伏行业协会', 1430, 420, 28, (1, 0.85, 0.8), o, 'sans_med')
        return
    if t < T('o4'):
        tc = T('o3'); tm = WT('o3', '外卖')
        for half, (t0, title, tags, col) in enumerate(((tc, '汽车 · 价格战', ['−10%', '−20%', '−34%'], (0.85, 0.88, 0.95)),
                                                        (tm, '外卖 · 补贴战 · 2025 夏', ['满减', '红包', '0元购'], (1.0, 0.62, 0.35)))):
            x0 = 80 + half * 900; o = ease(lin(t, t0 - 0.1, t0 + 0.4))
            card(cv, x0, 250, x0 + 860, 760, (0.10, 0.11, 0.14), 0.92 * o, col, glow=0.4)
            label(cv, title, x0 + 40, 320, 46, col, o, 'sans_black', anchor='l')
            for i, tg in enumerate(tags):
                s, oo = pop(t, t0 + 0.4 + i * 0.35)
                big(cv, tg, x0 + 150 + i * 280, 540, 96 if i == 2 else 78, a=oo * o, fname='sans_black',
                    color=RED if i == 2 else WHITE, glow=0.3, scale=0.85 + 0.15 * s)
        return
    if t < T('o5'):
        x0, x1 = 300, 1500; yz = 680
        L = layer(); line(L, (x0, yz), (x1, yz), 3); stroke_layer(cv, L, GREY, 0.8)
        label(cv, '0', x0 - 30, yz, 34, GREY, 1, 'oswald')
        k = eout(lin(t, T('o4'), SE('o4')))
        pp, pf = [], []
        for i in range(31):
            fx = i / 30
            if fx > k: break
            x = x0 + fx * (x1 - x0)
            pp.append((x, 300 + 200 * fx)); pf.append((x, 520 + 240 * fx ** 1.3))
        if len(pp) > 1:
            L = layer(); poly(L, pp, 6); stroke_layer(cv, L, WHITE, 0.95, glow=1)
            L = layer(); poly(L, pf, 6); stroke_layer(cv, L, RED if pf[-1][1] > yz else GOLD, 0.95, glow=1.2)
            kl = ease(lin(k, 0.9, 1.0))
            label(cv, '价格', pp[-1][0] + 14, pp[-1][1], 32, WHITE, kl, 'sans_bold', anchor='l')
            label(cv, '利润', pf[-1][0] + 14, pf[-1][1], 32, RED if pf[-1][1] > yz else GOLD, kl, 'sans_bold', anchor='l')
        s, o = pop(t, WT('o4', '越卖越亏'))
        big(cv, '越卖越亏', W / 2, 180, 116, a=o, scale=0.9 + 0.1 * s, grad=REDG, glow=0.5)
        return
    if t < T('o6'):
        docs = [(T('o5'), '2024.07 · 中央政治局会议', ['强化行业自律，', '防止“内卷式”恶性竞争']),
                (WT('o5', '价格法'), '2025.07 · 价格法修正草案（首次修订）', ['经营者不得以低于成本的', '价格倾销'])]
        for i, (t0, head, body) in enumerate(docs):
            x0 = 100 + i * 920; y0 = 260; s, o = pop(t, t0 - 0.1, 0.5)
            dy = (1 - s) * 60
            card(cv, x0, y0 + dy, x0 + 800, y0 + 400 + dy, (0.94, 0.91, 0.85), 0.95 * o, r=10)
            L = layer(); rect(L, x0, y0 + dy, x0 + 800, y0 + 96 + dy, r=10); fill(cv, L, (0.70, 0.10, 0.09), 0.95 * o)
            label(cv, head, x0 + 400, y0 + 48 + dy, 34, WHITE, o, 'sans_black')
            for j, b in enumerate(body):
                label(cv, b, x0 + 400, y0 + 190 + j * 80 + dy, 54, (0.15, 0.12, 0.10), o, 'serif_black', glow=0)
        tq = WT('o5', '低于成本倾销')
        if t > tq:
            kk = eout(lin(t, tq, tq + 0.5)); uw = text_w('价格倾销', 'serif_black', 54, 0.02) + 24; L = layer()
            line(L, (1420 - uw / 2, 576), (1420 - uw / 2 + uw * kk, 576), 5)
            stroke_layer(cv, L, RED, 0.9)
        return
    DUST.draw(cv, t, GOLD, 0.3)
    a = ease(lin(t, T('o6') - 0.1, T('o6') + 0.4))
    label(cv, '卷了这么多年', W / 2, 270, 48, GREY, a, 'sans_med')
    big(cv, '价格战打到最后，', W / 2, 410, 88, a=a, color=WHITE, glow=0.1)
    tq = HIT['q_moat']; s, o = pop(t, tq - 0.1, 0.5)
    big(cv, '谁建起了护城河？', W / 2, 560, 100, a=o, scale=0.9 + 0.1 * s, grad=GOLDG, glow=0.7)
    L = layer(); circle(L, (W / 2, 470), 420 + 8 * math.sin(t * 2), 4); stroke_layer(cv, L, GOLD, o * 0.35, glow=1.4)


def sc_open(cv, t):
    bg(cv, t)
    if t < T('o8') + 0.2:
        a = ease(lin(t, T('o7') - 0.4, T('o7') + 0.4))
        photo(cv, 'hotdog_drink.jpg', t, T('o7') - 0.4, T('o8'), 1.15, 1.04, 0.5, 0.5, 0.6, 0.56, a=a, sat=0.95, warm=0.55, contrast=1.12, gain=0.92)
        shade(cv, 0.4, 0.9, 0.15)
        t1 = WT('o7', '一块五'); s, o = pop(t, t1)
        big(cv, '$1.50', W / 2, 500, 210, a=o, scale=0.8 + 0.2 * s, fname='playfair', grad=GOLDG, glow=0.6)
        ty = WT('o7', '一九八五'); te = WT('o7', '今天', end=True)
        yr = 1985 + (2026 - 1985) * eout(lin(t, ty + 0.2, te)); o2 = ease(lin(t, ty, ty + 0.4))
        label(cv, '1985', W / 2 - 170, 690, 56, GOLD_HI, o2, 'oswald')
        label(cv, '→', W / 2, 690, 48, GOLD, o2 * ease(lin(t, ty + 0.2, ty + 0.6)), 'sans_med')
        label(cv, '%d' % yr, W / 2 + 170, 690, 56, WHITE, o2 * ease(lin(t, ty + 0.3, ty + 0.7)), 'oswald')
        label(cv, 'COSTCO 热狗套餐 · 价格 40 多年没变', W / 2, 770, 30, GREY, o2 * 0.9, 'sans_light', track=0.05)
        big(cv, '便宜了 40 年', W / 2, 200, 96, a=ease(lin(t, WT('o7', '便宜了'), WT('o7', '便宜了') + 0.4)), grad=GOLDG, glow=0.5)
        credit(cv, 'hotdog_drink', o2)
    if t >= T('o8'):
        a = ease(lin(t, T('o8') - 0.05, T('o8') + 0.35)); tmp = np.empty_like(cv)
        photo(tmp, 'ofo_hq.jpg', t, T('o8'), T('o9'), 1.05, 1.15, 0.5, 0.55, 0.45, 0.4, sat=0.35, warm=-0.8, contrast=1.2, gain=0.62)
        shade(tmp, 0.35, 0.9, 0.15); cv *= (1 - a); cv += tmp * a
        big(cv, '便宜到了最后', W / 2, 180, 90, a=ease(lin(t, T('o8'), T('o8') + 0.4)), color=(0.80, 0.86, 0.95), glow=0.2)
        t3 = WT('o8', '一千多万'); o = ease(lin(t, t3 - 0.3, t3 + 0.2))
        n = 11190000 * eout(lin(t, t3 - 0.3, WT('o8', '押金', end=True)))
        big(cv, counter(n), W / 2, 340, 120, a=o, fname='oswald', color=(1.0, 0.86, 0.80), glow=0.2)
        label(cv, '人在线排队 · 等着退押金', W / 2, 450, 40, WHITE, o, 'sans_bold', track=0.06)
        label(cv, 'ofo 小黄车 · 2018 年 12 月', W / 2, 505, 28, GREY, o * 0.8, 'sans_light', track=0.06)
        lay = layer(); k = lin(t, t3 - 0.3, E('o8')); cols, rows = 40, 9; m = int(cols * rows * eout(k))
        for i in range(m): circle(lay, (316 + (i % cols) * 33, 600 + (i // cols) * 30), 5.2, fill=True)
        stroke_layer(cv, lay, (0.95, 0.80, 0.30), 0.85, glow=0.6)
        credit(cv, 'ofo_hq', o)


def sc_split(cv, t):
    bg(cv, t)
    k = eout(lin(t, T('o9') - 0.1, T('o9') + 0.6))
    left = cover(graded('hotdog_drink.jpg', sat=0.95, warm=0.55, contrast=1.12, gain=0.9), W // 2, H, 1.15 + 0.05 * lin(t, T('o9'), T('o10')), 0.5, 0.6)
    right = cover(graded('ofo_station.jpg', sat=0.3, warm=-0.8, contrast=1.15, gain=0.7), W // 2, H, 1.1 + 0.05 * lin(t, T('o9'), T('o10')), 0.45, 0.6)
    off = int((1 - k) * 160)
    cv[:, :W // 2] = np.roll(left, -off, 0) * k; cv[:, W // 2:] = np.roll(right, off, 0) * k
    dim_ = 1 - 0.72 * ease(lin(t, T('o10') - 0.1, T('o10') + 0.5)); dim(cv, dim_)
    hide = 1 - ease(lin(t, T('o10') - 0.15, T('o10') + 0.25))
    L = layer(); line(L, (W / 2, 0), (W / 2, H * k), 3); stroke_layer(cv, L, GOLD, 0.9 * hide, glow=1.5)
    s, o = pop(t, WT('o9', '护城河')); big(cv, '护城河', W / 4, CY, 128, a=o * hide, scale=0.9 + 0.1 * s, grad=GOLDG)
    s2, o2 = pop(t, WT('o9', '坟墓')); big(cv, '坟　墓', W * 3 / 4, CY, 128, a=o2 * hide, scale=0.9 + 0.1 * s2, color=(0.72, 0.78, 0.86), glow=0.15)
    if t > T('o10') - 0.1:
        s3, o3 = pop(t, WT('o10', '差别'), 0.6)
        big(cv, '差别在哪？', W / 2, CY, 132, a=o3, scale=0.92 + 0.08 * s3 + 0.03 * lin(t, T('o10'), HIT['title']), color=WHITE, glow=0.3)


def sc_title(cv, t):
    bg(cv, t, (0.10, 0.08, 0.06)); t0 = HIT['title']; u = t - t0; cy = 500
    DUST.draw(cv, t, GOLD, 0.35)
    if 0 <= u < 1.2:
        L = layer(); circle(L, (W / 2, cy), 60 + 1100 * eout(u / 1.2), 6 * (1 - u / 1.2) + 1)
        stroke_layer(cv, L, GOLD_HI, (1 - u / 1.2) * 0.8, glow=2.0, add=True)
    L = layer(); R = 420; brk = ease(lin(u, 0.9, 2.6))
    for i in range(12):
        a0 = i * 30 + 3; a1 = a0 + 24
        dx = math.sin(math.radians(a0 + 12)) * 60 * brk; dy = -math.cos(math.radians(a0 + 12)) * 60 * brk
        arc(L, (W / 2 + dx, cy + dy), R + 14 * brk, a0 + 6 * brk * ((i % 2) - 0.5), a1 - 3 * brk, 5)
    stroke_layer(cv, L, GOLD, ease(lin(u, 0, 0.5)) * (1 - 0.45 * brk), glow=1.6, add=True)
    s, o = pop(t, t0, 0.5)
    big(cv, '便宜 ≠ 护城河', W / 2, cy - 60, 124, a=o, scale=1.12 - 0.12 * s + 0.02 * u / 3, grad=GOLDG, glow=0.7, track=0.04)
    s2, o2 = pop(t, t0 + 0.6, 0.5)
    big(cv, '低成本成为护城河的三个条件', W / 2, cy + 95, 56, a=o2, scale=0.9 + 0.1 * s2, color=WHITE, fname='serif_semi', glow=0.15, track=0.08)
    label(cv, 'CHEAP IS NOT A MOAT · FIRST PRINCIPLES', W / 2, cy + 180, 26, GOLD, o2 * 0.85, 'corm_med', track=0.25)
    if 0 <= u < 0.35: cv += np.asarray((1.0, 0.85, 0.6), np.float32) * (1 - u / 0.35) ** 2 * 0.55


# ── 01 第一性原理 ──
def sc_first(cv, t):
    bg(cv, t, (0.06, 0.07, 0.10))
    if t < T('p4'):
        a = ease(lin(t, T('p1') - 0.2, T('p1') + 0.4)); y = 210
        terms = [('利润', WT('p1', '利润'), GOLD), ('=', WT('p1', '等于'), GREY), ('价格', WT('p1', '价格'), WHITE), ('−', WT('p1', '减去'), GREY), ('成本', WT('p1', '成本'), (0.62, 0.78, 0.95))]
        xs = [620, 785, 960, 1135, 1300]
        for (s_, ts, col), x in zip(terms, xs):
            s, o = pop(t, ts - 0.1, 0.35)
            hl = 1.0
            if t > T('p2') - 0.1 and s_ == '价格': hl = 1.25
            if t > T('p3') - 0.1 and s_ == '成本': hl = 1.25
            big(cv, s_, x, y, 92 if len(s_) > 1 else 80, a=o * a, color=col, glow=0.3 * hl, scale=(0.85 + 0.15 * s) * (1 if hl == 1 else 1.08))
        if t > T('p2') - 0.2:
            o = ease(lin(t, T('p2') - 0.2, T('p2') + 0.3)); x0, x1, yy = 140, 860, 520
            label(cv, '价格 · 一个决定', 140, 390, 44, WHITE, o, 'sans_black', anchor='l')
            L = layer(); line(L, (x0, yy), (x1, yy), 6); stroke_layer(cv, L, GREY, o * 0.6)
            tk = WT('p2', '明天就能改'); kx = 0.75 - 0.5 * eout(lin(t, tk, tk + 0.25))
            L = layer(); circle(L, (x0 + (x1 - x0) * kx, yy), 26, fill=True); stroke_layer(cv, L, WHITE, o, glow=1.2)
            label(cv, '¥%d' % round(60 + 80 * kx), x0 + (x1 - x0) * kx, yy + 56, 36, WHITE, o, 'oswald')
            label(cv, '老板一句话，明天就能改', 860, 450, 30, GREY, o, 'sans_med', anchor='r')
        if t > T('p3') - 0.2:
            o = ease(lin(t, T('p3') - 0.2, T('p3') + 0.3))
            L = layer(); line(L, (W / 2, 360), (W / 2, 820), 2); stroke_layer(cv, L, GREY, o * 0.35)
            label(cv, '成本 · 一种结构', 1060, 390, 44, (0.62, 0.78, 0.95), o, 'sans_black', anchor='l')
            for i, w_ in enumerate(('工厂', '流程', '规模', '渠道')):
                ts = WT('p3', w_); s, oo = pop(t, ts - 0.1, 0.4)
                yb = 780 - i * 84 - (1 - s) * 40
                card(cv, 1120, yb - 37, 1680, yb + 37, (0.30, 0.42, 0.58), 0.9 * oo, (0.62, 0.78, 0.95), r=8, glow=0.3)
                label(cv, w_, 1400, yb, 40, WHITE, oo, 'sans_black')
            label(cv, '要很多年才能建起来', 1780, 450, 30, GREY, ease(lin(t, WT('p3', '很多年'), WT('p3', '很多年') + 0.3)), 'sans_med', anchor='r')
        return
    if t < T('p5'):
        for i, (h1, h2, col, ts) in enumerate((('低价格', '谁都能做', WHITE, WT('p4', '低价格')), ('低成本', '不是谁都有', GOLD, WT('p4', '低成本')))):
            s, o = pop(t, ts - 0.1, 0.45); y = 330 + i * 300
            card(cv, 300, y - 130, 1620, y + 130, (0.11, 0.12, 0.15), 0.92 * o, col, glow=0.5 if i else 0.2)
            big(cv, h1, 620, y, 96, a=o, color=col, grad=GOLDG if i else None, glow=0.4, scale=0.9 + 0.1 * s)
            label(cv, h2, 1200, y + 6, 56, WHITE if i else GREY, o, 'serif_semi')
        return
    base = 800; top = 260; n = 5; k = eout(lin(t, T('p5') + 0.3, HIT['zero'] + 0.3))
    label(cv, '内卷', W / 2, 150, 90, RED, ease(lin(t, T('p5'), T('p5') + 0.4)), 'serif_black', glow=0.4)
    for i in range(n):
        cx = 500 + i * 230; cost = 0.70 - 0.14 * k + 0.012 * math.sin(i * 1.7)
        price = 0.97 - (0.97 - cost - 0.004) * k + 0.012 * math.sin(i * 2.3)
        yc = base - (base - top) * cost; yp = base - (base - top) * price
        L = layer(); rect(L, cx - 62, yc, cx + 62, base, r=6); fill(cv, L, (0.42, 0.50, 0.62), 0.9)
        L = layer(); rect(L, cx - 62, min(yp, yc), cx + 62, max(yp, yc) + 1, r=4); fill(cv, L, mix(TEAL, RED, k), 0.75)
        L = layer(); line(L, (cx - 82, yp), (cx + 82, yp), 4); stroke_layer(cv, L, WHITE, 0.95, glow=0.8)
        label(cv, '公司%s' % 'ABCDE'[i], cx, base + 44, 28, GREY, 1, 'sans_med')
    y70 = base - (base - top) * 0.70; L = layer()
    for x in range(400, 1520, 24): line(L, (x, y70), (x + 12, y70), 2)
    oc = ease(lin(t, T('p5') + 0.8, T('p5') + 1.3))
    stroke_layer(cv, L, (0.62, 0.78, 0.95), 0.55 * oc)
    label(cv, '— 价格', 1580, 420, 28, WHITE, 1, 'sans_med', anchor='l')
    label(cv, '■ 成本', 1580, 480, 28, (0.62, 0.78, 0.95), 1, 'sans_med', anchor='l')
    label(cv, '- - 起点成本', 1580, 540, 28, (0.62, 0.78, 0.95), oc, 'sans_med', anchor='l')
    tg = WT('p5', '拉不开差距'); label(cv, '成本也在降，但大家一起降，差距拉不开', W / 2, 875, 32, (0.62, 0.78, 0.95), ease(lin(t, tg - 0.6, tg)), 'sans_bold')
    s, o = pop(t, HIT['zero'] - 0.1)
    big(cv, '利润 → 0', W / 2, 300, 84, a=o, scale=0.9 + 0.1 * s, grad=REDG, glow=0.5)


def sc_textile(cv, t):
    bg(cv, t, (0.08, 0.065, 0.05))
    photo(cv, 'weave_room.jpg', t, T('p6') - 0.5, T('p10'), 1.03, 1.15, 0.55, 0.45, 0.5, 0.48, sat=0.15, warm=0.6, contrast=1.1, gain=0.7)
    shade(cv, 0.45, 0.92, 0.18 if t < T('p7') else 0.42)
    credit(cv, 'weave_room', 1)
    a = ease(lin(t, T('p6') - 0.2, T('p6') + 0.5))
    label(cv, '巴菲特 · 纺织厂', 60, 200, 40, WHITE, a, 'sans_black', anchor='l')
    o85 = ease(lin(t, WT('p6', '一九八五'), WT('p6', '一九八五') + 0.4))
    big(cv, '1985', 60 + 170, 300, 96, a=o85, fname='oswald', grad=GOLDG)
    label(cv, '他在致股东信里复盘', 60, 390, 34, WHITE, o85, 'sans_med', anchor='l')
    if T('p7') - 0.2 < t < T('p8') - 0.05:
        o = fade(t, T('p7') - 0.2, T('p8') - 0.05, 0.4, 0.3)
        card(cv, 720, 180, 1850, 820, (0.93, 0.89, 0.80), 0.95 * o, r=10)
        q = ['"Viewed individually, each company\'s', 'capital investment decision appeared', 'cost-effective and reasonable; viewed', 'collectively, the decisions neutralized', 'each other and were irrational."']
        rv = lin(t, T('p7') + 0.1, T('p7') + 0.6 * (SE('p7') - T('p7')))
        quote_block(cv, q, 770, 250, 34, o, 'typewriter', (0.16, 0.13, 0.10), 1.55, reveal=rv)
        label(cv, '— Warren Buffett, 1985 Letter', 1810, 550, 28, (0.35, 0.28, 0.2), o * ease(lin(t, SE('p7') - 0.5, SE('p7'))), 'corm_med', anchor='r')
        ts = WT('p7', '单独看'); tc = WT('p7', '放在一起看')
        label(cv, '单独看：都很合理', 1285, 650, 46, (0.10, 0.45, 0.40), o * ease(lin(t, ts, ts + 0.3)), 'sans_black')
        label(cv, '放在一起：互相抵消，反而不理性', 1285, 740, 42, (0.70, 0.12, 0.10), o * ease(lin(t, tc, tc + 0.3)), 'sans_black')
    if t > T('p8'):
        o = ease(lin(t, T('p8') + 0.0, T('p8') + 0.45)) * (1 - ease(lin(t, T('p9') - 0.2, T('p9') + 0.2)))
        label(cv, '芒格：', 760, 250, 44, GOLD, o, 'serif_black', anchor='l')
        quote_block(cv, ['在同质化的生意里，换上更好的机器，', '省下的钱，最后全部流进了买家的口袋。'], 760, 340, 50, o, 'serif_semi', WHITE, 1.5,
                    reveal=lin(t, T('p8') + 0.2, T('p8') + 0.65 * (SE('p8') - T('p8'))))
        tb = HIT['buyer']; kb = ease(lin(t, tb - 1.2, tb))
        if kb > 0:
            L = layer()
            for i in range(30):
                ph = (t * 0.7 + i / 30) % 1
                circle(L, (820 + 900 * ph, 640 - 70 * math.sin(ph * math.pi)), 7, v=1 - 0.4 * ph, fill=True)
            stroke_layer(cv, L, GOLD_HI, kb * o, glow=1.6, add=True)
            label(cv, '织布机', 820, 710, 32, GREY, o * kb, 'sans_bold'); label(cv, '买家', 1720, 710, 32, GOLD_HI, o * kb, 'sans_bold')
    if t > T('p9') - 0.2:
        o = ease(lin(t, T('p9') - 0.2, T('p9') + 0.3))
        dim(cv, 1 - 0.5 * o)
        big(cv, '你能买到的效率，对手也能买到。', W / 2, 420, 76, a=o, color=WHITE, glow=0.1)
        s, oo = pop(t, WT('p9', '留不住'))
        big(cv, '省下来的钱，留不住', W / 2, 600, 84, a=oo, scale=0.9 + 0.1 * s, grad=REDG, glow=0.4)


def sc_test(cv, t):
    bg(cv, t, (0.06, 0.07, 0.09))
    base = 800; top = 200; ppu = (base - top) / 110.0
    yv = lambda v: base - v * ppu
    if t < T('p11'):
        tq = WT('p10', '同一个价格'); k = eout(lin(t, SP('p10') + 1.2, tq + 0.3))
        for nm, x, p0, col in (('A', 560, 128, GOLD), ('B', 1360, 116, RED)):
            o = ease(lin(t, T('p10') - 0.1, T('p10') + 0.5))
            L = layer(); rect(L, x - 190, 250, x + 190, 700, r=18); fill(cv, L, (0.12, 0.13, 0.16), 0.9 * o)
            L = layer(); rect(L, x - 190, 250, x + 190, 700, fill=False, w=3, r=18); stroke_layer(cv, L, col, 0.8 * o, glow=0.8)
            L = layer(); fpoly(L, [(x - 210, 290), (x, 200), (x + 210, 290)]); fill(cv, L, col, 0.85 * o)
            label(cv, '店 ' + nm, x, 350, 46, col, o, 'sans_black')
            big(cv, '¥%d' % round(p0 + (90 - p0) * k), x, 520, 128, a=o, fname='oswald', color=WHITE if k < 1 else GOLD_HI, glow=0.2)
            label(cv, '售价', x, 640, 30, GREY, o, 'sans_med')
        label(cv, '同一个价格', W / 2, 520, 44, GOLD_HI, ease(lin(t, tq + 0.1, tq + 0.5)), 'sans_bold')
        tw = WT('p10', '你还赚钱吗'); s2, o2 = pop(t, tw, 0.5)
        big(cv, '你还赚钱吗？', W / 2, 805, 100, a=o2, scale=0.9 + 0.1 * s2, color=WHITE, glow=0.3)
        label(cv, '第一道检验', W / 2, 140, 46, GREY, fade(t, SP('p10'), tw, 0.4, 0.4), 'sans_med')
        return
    pa = ease(lin(t, T('p11'), T('p11') + 0.5))
    L = layer(); line(L, (420, base), (1500, base), 2); stroke_layer(cv, L, GREY, 0.6 * pa)
    py = yv(90); tp = WT('p11', '九十块'); kp = eout(lin(t, tp - 0.2, tp + 0.4))
    L = layer()
    for x in range(420, int(420 + 1080 * kp), 28): line(L, (x, py), (x + 16, py), 3)
    stroke_layer(cv, L, WHITE, 0.9, glow=0.6)
    label(cv, '售价 ¥90', W / 2, py - 34, 34, WHITE, kp, 'sans_bold')
    bars_ = [('A', 700, 75, GOLD, WT('p11', '七十五'), WT('p11', '赚十五'), '+15', TEAL),
             ('B', 1220, 95, RED, WT('p11', '九十五'), WT('p11', '亏五块'), '−5', RED)]
    for nm, cx, cost, col, tc, tr, res, rc in bars_:
        kb = eout(lin(t, tc - 0.25, tc + 0.5)); h = cost * ppu * kb
        L0 = layer(); rect(L0, cx - 110, yv(cost), cx + 110, base, fill=False, w=2, r=6); stroke_layer(cv, L0, col, 0.25 * pa)
        L = layer(); rect(L, cx - 110, base - h, cx + 110, base, r=6); fill(cv, L, col, 0.85)
        label(cv, nm, cx, base + 56, 50, col, pa, 'oswald')
        label(cv, '成本 ¥%d' % cost, cx, base - h / 2, 36, INK, kb, 'sans_bold')
        kr = ease(lin(t, tr - 0.15, tr + 0.3))
        if kr > 0:
            y_a, y_b = sorted((yv(cost), py))
            L = layer(); rect(L, cx - 110, y_a, cx + 110, y_b); fill(cv, L, rc, 0.45 * kr)
            s, o = pop(t, tr - 0.1)
            big(cv, res, cx, y_a - 66, 88, a=o, scale=0.8 + 0.2 * s, fname='oswald', color=mix(rc, (1, 1, 1), 0.2), glow=0.5)
    tb = WT('p11', '亏五块')
    if t > tb:
        L = layer(); rr = np.random.default_rng(11)
        for i in range(26):
            ph = rr.random(); sp = 90 + rr.random() * 120; x = (1120 + rr.random() * 28) if i % 2 else (1292 + rr.random() * 28)
            y = yv(90) + ((t - tb) * sp + ph * 600) % 520
            if y < base: circle(L, (x, y), 3 + rr.random() * 3, fill=True)
        stroke_layer(cv, L, RED, 0.8 * ease(lin(t, tb, tb + 0.5)), glow=1.0)
    s, o = pop(t, WT('p12', '武器')); big(cv, '武器', 340, 480, 108, a=o, scale=0.85 + 0.15 * s, grad=GOLDG)
    s, o = pop(t, WT('p12', '失血')); big(cv, '失血', 1580, 480, 108, a=o, scale=0.85 + 0.15 * s, grad=REDG)


# ── 02 两位大师 ──
def master_panel(cv, t, side, a, hl=0.0):
    x0 = 0 if side == 0 else W // 2; hw = W // 2
    if side == 0:
        img = graded('buffett_2015.jpg', sat=0.25, warm=0.5, contrast=1.1, gain=0.8)
        ph = cover(img, hw - 80, 560, 1.15, 0.36, 0.36)
        cv[130:690, x0 + 40:x0 + hw - 40] = cv[130:690, x0 + 40:x0 + hw - 40] * (1 - a) + ph * a
        label(cv, '巴菲特', x0 + hw / 2, 750, 50, GOLD, a, 'serif_black')
        label(cv, 'Warren Buffett', x0 + hw / 2, 805, 28, GREY, a, 'corm_med', track=0.1)
    else:
        L = layer(); rect(L, x0 + 40, 130, x0 + hw - 40, 690, r=14); fill(cv, L, (0.14, 0.10, 0.10), 0.95 * a)
        big(cv, '段', x0 + hw / 2, 410, 300, a=a * 0.9, color=(0.85, 0.40, 0.32), fname='serif_black', glow=0.3)
        label(cv, '段永平', x0 + hw / 2, 750, 50, (1.0, 0.55, 0.45), a, 'serif_black')
        label(cv, 'Duan Yongping', x0 + hw / 2, 805, 28, GREY, a, 'corm_med', track=0.1)
    if hl > 0:
        L = layer(); rect(L, x0 + 24, 114, x0 + hw - 24, 850, fill=False, w=4, r=16)
        stroke_layer(cv, L, GOLD if side == 0 else RED, a * hl, glow=1.5)


def sc_clash(cv, t):
    bg(cv, t, (0.07, 0.06, 0.07))
    clash = HIT['clash']; u = t - clash
    shake = (math.sin(u * 90) * 14 * math.exp(-u * 7)) if 0 <= u < 0.6 else 0
    if t < T('d5'):
        a = ease(lin(t, T('d1') - 0.2, T('d1') + 0.5))
        qa = ease(lin(t, T('d2') - 0.2, T('d2') + 0.2)) * (1 - ease(lin(t, T('d3') - 0.3, T('d3'))))
        qd = ease(lin(t, T('d3') - 0.1, T('d3') + 0.25)) * (1 - ease(lin(t, T('d5') - 0.3, T('d5'))))
        master_panel(cv, t, 0, a * (1 - 0.92 * qd), hl=ease(lin(t, T('d2'), T('d2') + 0.3)) * (1 - ease(lin(t, T('d3'), T('d3') + 0.3))))
        master_panel(cv, t, 1, a * (1 - 0.92 * qa), hl=ease(lin(t, T('d3'), T('d3') + 0.3)))
        label(cv, 'VS', W / 2, 410, 64, WHITE, a * (1 - ease(lin(t, T('d2') - 0.2, T('d2')))), 'oswald', glow=0.5)
        if qa > 0.003:
            o = qa; x0 = W // 2 + 40
            card(cv, x0, 160, x0 + 880, 660, (0.93, 0.89, 0.80), 0.95 * o, r=10)
            quote_block(cv, ['"...being the low-cost producer', '(GEICO, Costco) ... is essential', 'for sustained success."'], x0 + 50, 280, 36, o, 'typewriter', (0.16, 0.13, 0.10), 1.6,
                        reveal=lin(t, T('d2') + 0.8, T('d2') + 0.75 * (SE('d2') - T('d2'))))
            label(cv, '— 2007 年致股东信', x0 + 830, 600, 26, (0.35, 0.28, 0.2), o, 'sans_med', anchor='r')
        if qd > 0.003:
            o = qd; dx = shake; x0 = 40 + dx
            card(cv, x0, 150, x0 + 880, 690, (0.20, 0.08, 0.07), 0.95 * o, RED, glow=0.8)
            if t < T('d4'):
                quote_block(cv, wrap('“还没见过成本优势可以成‘护城河’的，很少有企业能长期维持低成本的，制造业好像没见过。”', 17), x0 + 40, 250, 44, o, 'serif_semi', WHITE, 1.5,
                            reveal=lin(t, T('d3') + 0.2, T('d3') + 0.8 * (SE('d3') - T('d3'))))
                label(cv, '— 段永平，2010（答网友：比亚迪的成本优势是不是护城河）', x0 + 850, 650, 22, (1, 0.8, 0.75), o, 'sans_light', anchor='r')
            else:
                oo = ease(lin(t, T('d4') - 0.1, T('d4') + 0.3))
                quote_block(cv, wrap('“追求‘性价比’的公司，大多是在为自己的低价找借口。”', 15), x0 + 40, 280, 52, o * oo, 'serif_semi', WHITE, 1.5,
                            reveal=lin(t, T('d4') + 0.2, T('d4') + 0.75 * (SE('d4') - T('d4'))))
                label(cv, '— 段永平（据 2018 年斯坦福交流整理）', x0 + 850, 650, 22, (1, 0.8, 0.75), o * oo, 'sans_light', anchor='r')
        if 0 <= u < 0.25: cv += np.asarray((1.0, 0.5, 0.4), np.float32) * (1 - u / 0.25) ** 2 * 0.35
        return
    DUST.draw(cv, t, GOLD, 0.25)
    if t < T('d7'):
        a = ease(lin(t, T('d5') - 0.2, T('d5') + 0.4))
        big(cv, '谁对？', W / 2, 190, 110, a=a * (1 - ease(lin(t, T('d6') - 0.2, T('d6') + 0.2))), color=WHITE, glow=0.2)
        tq = WT('d5', '反问他'); o = ease(lin(t, tq - 0.6, tq))
        label(cv, '有人拿 GEICO 和 Costco 反问段永平', W / 2, 330, 40, GREY, o, 'sans_med')
        s, oo = pop(t, HIT['bizmodel'] - 0.1, 0.5)
        big(cv, '“它们靠的是商业模式”', W / 2, 450, 84, a=oo, scale=0.9 + 0.1 * s, grad=GOLDG, glow=0.4)
        label(cv, '（他说的是制造业的低成本，难以长期维持）', W / 2, 545, 30, GREY, oo, 'sans_light')
        if t > T('d6') - 0.2:
            s, o6 = pop(t, HIT['pricing'] - 0.15, 0.5)
            label(cv, '在他看来', W / 2, 660, 40, GREY, ease(lin(t, T('d6') - 0.2, T('d6') + 0.3)), 'sans_med')
            big(cv, '护城河 ≈ 定价权', W / 2, 785, 104, a=o6, scale=0.9 + 0.1 * s, grad=GOLDG, glow=0.7)
        return
    if t < T('d8'):
        a = ease(lin(t, T('d7') - 0.2, T('d7') + 0.4))
        big(cv, '并不矛盾', W / 2, 200, 104, a=a, color=WHITE, glow=0.2)
        rows = [('巴菲特看重', '能把低成本变成壁垒的商业模式', GOLD, WT('d7', '巴菲特看重')),
                ('段永平警惕', '只会卖便宜的公司', (1.0, 0.55, 0.45), WT('d7', '段永平警惕'))]
        for i, (h, b, col, ts) in enumerate(rows):
            s, o = pop(t, ts - 0.1, 0.45); x0 = 100 + i * 880
            card(cv, x0, 340, x0 + 840, 640, (0.11, 0.12, 0.15), 0.92 * o, col, glow=0.6)
            label(cv, h, x0 + 50, 430, 44, col, o, 'sans_black', anchor='l')
            label(cv, b, x0 + 50, 540, 44, WHITE, o, 'serif_semi', anchor='l')
        return
    a = ease(lin(t, T('d8') - 0.2, T('d8') + 0.4))
    label(cv, '低成本在什么条件下，才能成为护城河？', W / 2, 220, 56, WHITE, a, 'serif_semi')
    ts = WT('d8', '三个条件'); s, o = pop(t, ts - 0.1, 0.5)
    big(cv, '三个条件', W / 2, 440, 150, a=o, scale=0.9 + 0.1 * s, grad=GOLDG, glow=0.8)
    for i in range(3):
        oo = ease(lin(t, ts + 0.2 + i * 0.15, ts + 0.5 + i * 0.15))
        L = layer(); circle(L, (W / 2 - 220 + i * 220, 660), 56, 4); stroke_layer(cv, L, GOLD, oo, glow=1.2)
        label(cv, '%d' % (i + 1), W / 2 - 220 + i * 220, 660, 56, GOLD_HI, oo, 'oswald')


# ── 03 三个条件 ──
COND = V.COND


def cond_header(cv, t, i, t0, compact=False):
    s, o = pop(t, t0 - 0.15, 0.5)
    n, d = COND[i]
    if compact:
        label(cv, '条件%s · %s' % ('一二三'[i], n), 60, 200, 44, GOLD, 1, 'serif_black', anchor='l')
        for j in range(3):
            L = layer(); circle(L, (1680 + j * 64, 200), 22, fill=j <= i, w=3); stroke_layer(cv, L, GOLD, 0.9 if j <= i else 0.4)
        return
    label(cv, '条件%s' % '一二三'[i], W / 2, 270, 56, GOLD, o, 'serif_semi', track=0.2)
    big(cv, n, W / 2, 440, 170, a=o, scale=0.9 + 0.1 * s, grad=GOLDG, glow=0.8, track=0.1)
    label(cv, d, W / 2, 620, 52, WHITE, ease(lin(t, t0 + 0.4, t0 + 0.9)), 'sans_bold')


def sc_cond1(cv, t):
    bg(cv, t, (0.07, 0.07, 0.08))
    if t < T('k2') - 0.1:
        DUST.draw(cv, t, GOLD, 0.3); cond_header(cv, t, 0, HIT['cond_k1']); return
    cond_header(cv, t, 0, 0, compact=True)
    if t < T('k3'):
        o = ease(lin(t, T('k2') - 0.1, T('k2') + 0.3))
        img = graded('weave_room.jpg', sat=0.15, warm=0.6, contrast=1.1, gain=0.75)
        ph = cover(img, 900, 560, 1.15, 0.55, 0.5); y0, x0 = 270, 120
        cv[y0:y0 + 560, x0:x0 + 900] = cv[y0:y0 + 560, x0:x0 + 900] * (1 - o) + ph * o
        label(cv, '新织布机', 1440, 420, 64, WHITE, o, 'serif_black')
        label(cv, '¥ 谁都能买', 1440, 520, 46, GREY, o, 'sans_bold')
        tx = WT('k2', '所以不算'); s, oo = pop(t, tx - 0.1)
        check(cv, 1440, 680, '✗', oo, 80)
        return
    if t < T('k4'):
        o = ease(lin(t, T('k3') - 0.1, T('k3') + 0.3)); dx = 360
        label(cv, '老对手：保险公司 → 代理人 → 客户', 90 + dx, 270, 38, GREY, o, 'sans_bold', anchor='l')
        for x, n in ((200, '保险公司'), (540, '代理人'), (880, '客户')):
            card(cv, x + dx - 130, 370 - 56, x + dx + 130, 370 + 56, (0.20, 0.22, 0.26), 0.92 * o, GREY, r=12, glow=0.2); label(cv, n, x + dx, 370, 38, WHITE, o, 'sans_black')
        L = layer(); line(L, (330 + dx, 370), (410 + dx, 370), 5); line(L, (670 + dx, 370), (750 + dx, 370), 5); stroke_layer(cv, L, GREY, o)
        label(cv, '佣金 ＄', 540 + dx, 460, 32, (1.0, 0.7, 0.4), o, 'sans_bold')
        tg = WT('k3', '直接把保险卖给客户'); og = ease(lin(t, tg - 0.6, tg))
        label(cv, 'GEICO：保险公司 → 客户（直销）', 90 + dx, 560, 38, GOLD, og, 'sans_bold', anchor='l')
        for x, n in ((200, '保险公司'), (880, '客户')):
            card(cv, x + dx - 130, 660 - 56, x + dx + 130, 660 + 56, (0.45, 0.34, 0.14), 0.95 * og, GOLD, r=12); label(cv, n, x + dx, 660, 38, WHITE, og, 'sans_black')
        kl = eout(lin(t, tg - 0.4, tg + 0.4)); L = layer(); line(L, (330 + dx, 660), (330 + dx + 420 * kl, 660), 7); stroke_layer(cv, L, GOLD, og, glow=1.4)
        tc = WT('k3', '拆掉自己的销售体系'); kc = ease(lin(t, tc - 0.3, tc + 0.4))
        if kc > 0:
            L = layer(); line(L, (430 + dx, 320), (650 + dx, 420), 7); line(L, (650 + dx, 320), (430 + dx, 420), 7); stroke_layer(cv, L, RED, kc, glow=1)
            label(cv, '想学？先拆掉自己的销售体系', W / 2, 810, 46, RED, kc, 'sans_black')
        return
    for i, w_ in enumerate(('规模', '流程', '资源', '网络密度')):
        s, oo = pop(t, WT('k4', w_) - 0.1, 0.4); x = W / 2 + (i - 1.5) * 430; y = 440
        card(cv, x - 200, y - 95, x + 200, y + 95, (0.13, 0.14, 0.17), 0.92 * oo, GOLD, glow=0.6)
        big(cv, w_, x, y, 72, a=oo, scale=0.9 + 0.1 * s, grad=GOLDG, glow=0.3)
    label(cv, '都得是：对手难以复制的', W / 2, 700, 52, WHITE, ease(lin(t, WT('k4', '难以复制') - 0.3, WT('k4', '难以复制') + 0.2)), 'sans_black')


def sc_cond2(cv, t):
    bg(cv, t, (0.07, 0.07, 0.08))
    if t < T('k6') - 0.1:
        DUST.draw(cv, t, GOLD, 0.3); cond_header(cv, t, 1, HIT['cond_k5']); return
    if t < T('k7'):
        clipframe(cv, CLIPS['fork'], t, T('k6') - 0.3, 1.05, 1.12, 7, sat=0.5, gain=0.4)
        cv[:] = cv2.GaussianBlur(cv, (0, 0), 6); shade(cv, 0.3, 0.8, 0.2)
        cond_header(cv, t, 1, 0, compact=True)
        ts = [WT('k6', '让给会员'), WT('k6', '会员越多'), WT('k6', '采购量'), WT('k6', '成本越低')]
        sp = 30 * max(0, t - WT('k6', '价格再降')) ** 1.6
        V.flywheel(cv, t, (W / 2, 500), 270, ['低价', '会员\n更多', '采购量\n更大', '成本\n更低'], ts, GOLD, spin=sp, size=88)
        label(cv, 'Costco', W / 2, 500, 56, GOLD_HI, ease(lin(t, ts[0], ts[0] + 0.5)), 'oswald', track=0.1)
        credit(cv, 'abc_2005', 1)
        return
    cond_header(cv, t, 1, 0, compact=True)
    x0, x1, y0, y1 = 360, 1560, 310, 790; sy = (y1 - y0) / 760
    L = layer(); line(L, (x0, y1), (x1, y1), 2); line(L, (x0, y0), (x0, y1), 2); stroke_layer(cv, L, GREY, 0.6)
    label(cv, '单位成本', x0, y0 - 36, 30, GREY, 1, 'sans_med', anchor='l'); label(cv, '时间 →', x1, y1 + 36, 28, GREY, 1, 'sans_light', anchor='r')
    k = eout(lin(t, T('k7') + 0.2, HIT['gas'] + 0.8))
    you, rival = [], []
    for i in range(41):
        fx = i / 40
        if fx > k: break
        x = x0 + fx * (x1 - x0)
        rival.append((x, y0 + sy * (80 + 260 * fx ** 0.9))); you.append((x, y0 + sy * (200 + 500 * fx ** 0.8)))
    if len(you) > 1:
        pts = you + rival[::-1]; L = layer(); fpoly(L, pts); fill(cv, L, GOLD, 0.18)
        L = layer(); poly(L, rival, 5); stroke_layer(cv, L, GREY, 0.9, glow=0.6)
        L = layer(); poly(L, you, 6); stroke_layer(cv, L, GOLD, 0.95, glow=1.3)
        label(cv, '对手', rival[-1][0] + 14, rival[-1][1], 32, GREY, 1, 'sans_bold', anchor='l')
        label(cv, '你', you[-1][0] + 14, you[-1][1], 36, GOLD_HI, 1, 'sans_black', anchor='l')
        if k > 0.6:
            fx = 0.30; xm = x0 + fx * (x1 - x0); ym = y0 + sy * (200 + 500 * fx ** 0.8 + 80 + 260 * fx ** 0.9) / 2
            label(cv, '差距越拉越大', xm, ym, 38, GOLD_HI, ease((k - 0.6) / 0.3), 'sans_black')
    s, o = pop(t, HIT['gas'] - 0.15)
    big(cv, '油门踩到底', W / 2, 205, 92, a=o, scale=0.9 + 0.1 * s, grad=GOLDG, glow=0.5)
    tb = WT('k7', '行业标配'); kb = ease(lin(t, tb - 0.4, tb + 0.3))
    if kb > 0:
        pts = [(x0 + fx * (x1 - x0), y0 + sy * (200 + 500 * fx ** 0.8 if fx < 0.45 else 200 + 500 * 0.45 ** 0.8 + (fx - 0.45) * 120)) for fx in np.linspace(0, 1, 30)]
        L = layer()
        for a_, b_ in zip(pts[::2], pts[1::2]): line(L, a_, b_, 4)
        stroke_layer(cv, L, RED, kb * 0.9)
        label(cv, '一停下：优势变成行业标配', W / 2, 872, 36, RED, kb, 'sans_black')


def sc_cond3(cv, t):
    bg(cv, t, (0.08, 0.07, 0.06))
    if t < T('k9') - 0.1:
        DUST.draw(cv, t, GOLD, 0.3); cond_header(cv, t, 2, HIT['cond_k8']); return
    if t < T('k10') - 0.1:
        cond_header(cv, t, 2, 0, compact=True)
        bricks = [('会员锁定', '会员锁定'), ('品牌心智', '品牌心智'), ('网络效应', '网络效应'), ('定价权', '定价权')]
        for i, (n, key) in enumerate(bricks):
            s, o = pop(t, WT('k9', key) - 0.1, 0.45); y = 690 - i * 120 - (1 - s) * 60
            col = GOLD if i == 3 else (0.55, 0.50, 0.44)
            card(cv, 420, y - 54, 1000, y + 54, mix(col, INK, 0.35), 0.95 * o, col, r=6, glow=1.2 if i == 3 else 0.2)
            label(cv, n, 710, y, 50 if i == 3 else 44, WHITE if i < 3 else GOLD_HI, o, 'sans_black')
        L = layer(); line(L, (380, 765), (1040, 765), 3); stroke_layer(cv, L, GREY, 0.6)
        tf = HIT['fuel']; kf = ease(lin(t, tf - 0.3, tf + 0.3))
        if kf > 0:
            L = layer(); rr = np.random.default_rng(8)
            for i in range(70):
                ph = rr.random(); life = ((t - tf) * 0.9 + ph) % 1; x = 470 + rr.random() * 480
                circle(L, (x + math.sin(life * 8 + ph * 5) * 10, 880 - life * 100), 2 + 4 * (1 - life), v=1 - life, fill=True)
            stroke_layer(cv, L, (1.0, 0.55, 0.20), kf, glow=1.6, add=True)
            label(cv, '低成本 = 燃料', 1460, 440, 50, (1.0, 0.7, 0.4), kf, 'sans_black')
            tw = WT('k9', '才是城墙'); label(cv, '它换来的东西，才是城墙', 1460, 540, 40, WHITE, ease(lin(t, tw - 0.6, tw)), 'sans_bold')
        return
    if not (T('k12') - 0.45 < t < T('k13') - 0.1): cond_header(cv, t, 2, 0, compact=True)
    if t < T('k13') - 0.1:
        x0, x1 = 260, 1660
        a = ease(lin(t, T('k10') - 0.1, T('k10') + 0.4))
        yh = 330; xh = lambda yr: x0 + (yr - 1985) / (2026 - 1985) * (x1 - x0)
        label(cv, '热狗套餐', x0, yh - 80, 34, (1.0, 0.8, 0.5), a, 'sans_black', anchor='l')
        th = WT('k10', '热狗'); kh = eout(lin(t, th - 0.2, th + 1.0))
        L = layer(); line(L, (x0, yh), (x0 + (x1 - x0) * kh, yh), 6); stroke_layer(cv, L, (1.0, 0.75, 0.40), a, glow=1.2)
        label(cv, '$1.50 · 40 年未变', x1, yh - 40, 32, (1.0, 0.8, 0.5), ease(lin(t, th + 0.6, th + 1.0)), 'sans_bold', anchor='r')
        for yr in (1985, 2026): label(cv, str(yr), xh(yr), yh + 36, 26, GREY, a, 'oswald')
        tm = WT('k10', '百分之十四'); label(cv, '普通商品加价 ≤14%（据多家媒体报道）', x0, yh + 90, 28, GREY, ease(lin(t, tm - 0.3, tm + 0.2)), 'sans_med', anchor='l')
        tf = WT('k11', '六十美元'); kf = ease(lin(t, tf - 0.3, tf + 0.3))
        if kf > 0:
            yb = 760; xm = lambda yr: x0 + (yr - 2017) / (2026 - 2017) * (x1 - x0); ym = lambda v: yb - (v - 60) * 22
            label(cv, '美国基础会员费', x0, ym(65) - 70, 34, GOLD, kf, 'sans_black', anchor='l')
            yr_now = 2017 + (2024.67 - 2017) * eout(lin(t, tf - 0.3, tf + 0.6))
            pts = [(xm(2017), ym(60)), (xm(yr_now), ym(60))]
            if t > HIT['fee'] - 0.1:
                ku = eout(lin(t, HIT['fee'] - 0.1, HIT['fee'] + 0.4))
                pts += [(xm(2024.67), ym(60 + 5 * ku)), (xm(2024.67) + (x1 - xm(2024.67)) * ku, ym(60 + 5 * ku))]
            L = layer(); poly(L, pts, 7); stroke_layer(cv, L, GOLD, kf, glow=1.4)
            label(cv, '$60', xm(2020.5), ym(60) - 40, 36, GOLD, kf, 'oswald')
            for yr, s_ in ((2017, '2017'), (2024.67, '2024.09'), (2026, '2026')): label(cv, s_, xm(yr), yb + 38, 26, GREY, kf, 'oswald')
            s, o = pop(t, HIT['fee'] - 0.1)
            label(cv, '$65', (xm(2024.67) + x1) / 2, ym(65) - 40, 40, GOLD_HI, o, 'oswald', scale=0.9 + 0.1 * s)
        if t > T('k12') - 0.45:
            dim(cv, 1 - ease(lin(t, T('k12') - 0.45, T('k12') - 0.05)))
            a2 = ease(lin(t, T('k12') - 0.05, T('k12') + 0.35))
            cond_header(cv, t, 2, 0, compact=True)
            for x, ts_, val, frac, l1 in ((640, WT('k12', '续费率'), '89.8%', 0.898, '全球续费率（涨价后）'), (1280, WT('k12', '经营利润'), '≈50%', 0.506, '会员费 / 经营利润')):
                kk = eout(lin(t, ts_ - 0.3, ts_ + 0.9)); cy = 450
                L = layer(); circle(L, (x, cy), 160, 20); stroke_layer(cv, L, (0.3, 0.3, 0.32), a2 * 0.8)
                L = layer(); arc(L, (x, cy), 160, 0, 360 * frac * kk, 20); stroke_layer(cv, L, GOLD, a2 * ease(lin(t, ts_ - 0.3, ts_)), glow=1.4)
                label(cv, val, x, cy, 70, WHITE, a2 * ease(lin(t, ts_ - 0.3, ts_ + 0.1)), 'oswald')
                label(cv, l1, x, cy + 230, 34, GOLD_HI, a2 * ease(lin(t, ts_ - 0.3, ts_ + 0.1)), 'sans_bold')
            src_note(cv, 'Costco 2026 财年 10-K：会员费 59 亿美元 / 经营利润约 117 亿美元', a2)
        return
    if t < T('k14') - 0.1:
        DUST.draw(cv, t, GOLD, 0.3)
        a = ease(lin(t, T('k13') - 0.1, T('k13') + 0.4))
        card(cv, 380, 260, 920, 560, (0.12, 0.13, 0.16), 0.92 * a, GREY); card(cv, 1000, 260, 1540, 560, (0.20, 0.16, 0.08), 0.92 * a, GOLD)
        label(cv, '商品', 650, 340, 44, GREY, a, 'sans_bold'); big(cv, '坚持薄利', 650, 460, 72, a=a, color=WHITE, glow=0.1)
        tf = WT('k13', '却能涨价'); o = ease(lin(t, tf - 0.4, tf + 0.1))
        label(cv, '会员费', 1270, 340, 44, GOLD, o, 'sans_bold'); big(cv, '能涨价', 1270, 460, 72, a=o, grad=GOLDG, glow=0.4)
        s, oo = pop(t, HIT['power'] - 0.2, 0.5)
        big(cv, '= 低成本换来的定价权', W / 2, 720, 84, a=oo, scale=0.9 + 0.1 * s, grad=GOLDG, glow=0.7)
        return
    DUST.draw(cv, t, GOLD, 0.4)
    tz = WT('k14', '在这里'); km = eout(lin(t, tz - 0.35, HIT['meet']))
    for i, (n, sub, col) in enumerate((('低成本', '巴菲特', GOLD), ('定价权', '段永平', (1.0, 0.6, 0.45)))):
        x = W / 2 + (-1 if i == 0 else 1) * 330 * (1 - km)
        L = layer(); circle(L, (x, 470), 230, 5); stroke_layer(cv, L, col, 0.9, glow=1.3)
        gone = 1 - ease(lin(t, tz - 0.75, tz - 0.35))
        label(cv, sub, x + (-1 if i == 0 else 1) * 100 * (1 - km), 390, 36, GREY, gone, 'sans_med')
        big(cv, n, x + (-1 if i == 0 else 1) * 100 * (1 - km), 480, 64, a=gone, color=col, glow=0.3)
    s, o = pop(t, HIT['meet'] - 0.1, 0.5)
    big(cv, '护城河', W / 2, 470, 120, a=o, scale=0.9 + 0.1 * s, grad=GOLDG, glow=0.9)
    label(cv, '在这里会合', W / 2, 790, 46, WHITE, o, 'serif_semi')
    u = t - HIT['meet']
    if 0 <= u < 0.3: cv += np.asarray((1.0, 0.85, 0.6), np.float32) * (1 - u / 0.3) ** 2 * 0.4


# ── 04 中国考题 ──
def sc_china(cv, t):
    bg(cv, t, (0.10, 0.05, 0.05))
    if t < T('g2'):
        DUST2.draw(cv, t, (1.0, 0.55, 0.40), 0.35)
        s, o = pop(t, T('g1'), 0.5)
        big(cv, '中国考题', W / 2, 420, 150, a=o, scale=0.9 + 0.1 * s, grad=((1.0, 0.85, 0.7), (0.85, 0.30, 0.22)), glow=0.6)
        label(cv, '用三个条件体检', W / 2, 600, 50, WHITE, ease(lin(t, T('g1') + 0.4, T('g1') + 0.9)), 'serif_semi', track=0.1)
        return
    if t < T('g5'):
        if t < T('g3'):
            photo(cv, 'byd_seal.jpg', t, T('g2') - 0.3, T('g3'), 1.0, 1.08, 0.6, 0.56, 0.55, 0.55, sat=0.85, warm=-0.1, contrast=1.15, gain=0.85)
            shade(cv, 0.45, 0.92, 0.3); credit(cv, 'byd_seal', 1)
        else:
            photo(cv, 'byd_seagull.jpg', t, T('g3'), T('g5'), 1.05, 1.15, 0.5, 0.48, 0.55, 0.55, sat=0.6, warm=0.1, contrast=1.12, gain=0.6)
            shade(cv, 0.4, 0.92, 0.55); credit(cv, 'byd_seagull', 1)
        label(cv, 'BYD · 比亚迪', 60, 200, 40, WHITE, 1, 'sans_black', anchor='l')
        if t < T('g3'):
            a_out = 1 - ease(lin(t, T('g3') - 0.55, T('g3') - 0.1))
            for i, w_ in enumerate(('电池', '电机', '芯片')):
                s, o = pop(t, WT('g2', w_) - 0.1); x = W / 2 + (i - 1) * 340; y = 260
                L = layer(); rect(L, x - 130, y - 60, x + 130, y + 60, r=60); fill(cv, L, GOLD, 0.88 * o * a_out)
                label(cv, w_, x, y, 54, INK, o * a_out, 'sans_black', scale=0.85 + 0.15 * s)
            tz = WT('g2', '自己造'); label(cv, '垂直整合 · 大量自研自产', W / 2, 375, 36, GOLD_HI, ease(lin(t, tz, tz + 0.4)) * a_out, 'sans_bold')
            tn = WT('g2', '四百六十万'); kn = eout(lin(t, tn - 0.3, tn + 0.9)); on = ease(lin(t, tn - 0.3, tn)) * a_out
            big(cv, '%d' % round(460 * kn), W / 2 - 60, 540, 130, a=on, fname='oswald', grad=GOLDG)
            big(cv, '万辆', W / 2 + 130, 556, 60, a=on, fname='sans_black', color=GOLD_HI, glow=0.2)
            label(cv, '2025 年销量（含商用车约 460.2 万辆）', W / 2, 650, 30, WHITE, ease(lin(t, tn, tn + 0.4)) * a_out, 'sans_light')
            te = WT('g2', '实打实'); s, o = pop(t, te - 0.2)
            label(cv, '✓ 结构性优势', W / 2, 770, 50, TEAL, o * a_out, 'sans_black', scale=0.9 + 0.1 * s)
        elif t < T('g4'):
            a = ease(lin(t, T('g3'), T('g3') + 0.4))
            L = layer(); rect(L, 480, 230, 840, 370, r=14); fill(cv, L, (0.95, 0.6, 0.25), 0.85 * a)
            L = layer(); rect(L, 1080, 230, 1440, 370, r=14); fill(cv, L, (0.92, 0.92, 0.95), 0.85 * a)
            label(cv, '供应商', 660, 300, 50, INK, a, 'sans_black'); label(cv, '比亚迪', 1260, 300, 50, INK, a, 'sans_black')
            L = layer(); line(L, (855, 300), (1065, 300), 6); line(L, (1065, 300), (1039, 280), 6); line(L, (1065, 300), (1039, 320), 6); stroke_layer(cv, L, WHITE, a)
            tc = WT('g3', '百分之十'); s, o = pop(t, tc - 0.1)
            big(cv, '−10%', 660, 480, 110, a=o, scale=0.85 + 0.15 * s, fname='oswald', grad=REDG)
            label(cv, '年降目标（2024.11）', 660, 575, 30, WHITE, o, 'sans_med'); label(cv, '比亚迪回应：行业惯例，可协商', 660, 620, 24, GREY, o, 'sans_light')
            tz = WT('g3', '账期'); kz = ease(lin(t, tz - 0.2, tz + 0.3)); t60 = HIT['d60']; k6 = eout(lin(t, t60 - 0.4, t60 + 0.6))
            days = 275 + (60 - 275) * k6 if t > t60 - 0.5 else 275 * eout(lin(t, tz - 0.2, tz + 1.0))
            c = (1260, 500); L = layer(); circle(L, c, 100, 10); stroke_layer(cv, L, (0.3, 0.3, 0.32), kz)
            col = mix(RED, TEAL, k6); L = layer(); arc(L, c, 100, 0, 360 * min(1, days / 365), 12); stroke_layer(cv, L, col, kz, glow=1.3)
            label(cv, '%d' % round(days), c[0] - 14, c[1], 56, WHITE, kz, 'oswald'); label(cv, '天', c[0] + 50, c[1] + 6, 30, WHITE, kz, 'sans_bold')
            label(cv, '账期', c[0], c[1] + 145, 34, col, kz, 'sans_bold')
            label(cv, '2023 年平均约 275 天（彭博汇总）' if k6 < 0.5 else '2025.06 承诺：60 天内付款', c[0], c[1] + 190, 24, GREY, kz, 'sans_light')
            s, o = pop(t, t60 - 0.2)
            dim(cv, 1 - 0.55 * o)
            big(cv, '60 天内付款', W / 2, 760, 92, a=o, scale=0.9 + 0.1 * s, color=TEAL, glow=0.4)
            label(cv, '与多家车企一起承诺 · 2025 年 6 月', W / 2, 855, 30, WHITE, o, 'sans_med')
        else:
            a = ease(lin(t, T('g4') - 0.1, T('g4') + 0.4))
            label(cv, '比亚迪 · 三个条件体检', W / 2, 230, 50, WHITE, a, 'serif_black')
            V.scorecard(cv, t, 490, 300, [('结构性', '✓', '垂直整合、规模', T('g4') + 0.2),
                                          ('可持续', '?', '付款更公平后，差距还能拉大吗', WT('g4', '成本差距')),
                                          ('可转化', '?', '低成本能换来定价权吗', WT('g4', '换来定价权'))], a)
        return
    if t < T('g8'):
        kd = ease(lin(t, T('g5') + 1.4, T('g5') + 2.2))
        photo(cv, 'pdd_boxes.jpg', t, T('g5') - 0.3, T('g8'), 1.03, 1.12, 0.45, 0.5, 0.42, 0.45, sat=0.9 - 0.4 * kd, warm=0.1, contrast=1.1, gain=0.9 - 0.65 * kd)
        if kd > 0:
            b_ = cv2.GaussianBlur(cv, (0, 0), 6); cv *= (1 - kd); cv += b_ * kd
        shade(cv, 0.4, 0.9, 0.1); credit(cv, 'pdd_boxes', 1 - kd)
        label(cv, 'PDD · 拼多多', 60, 200, 40, WHITE, 1, 'sans_black', anchor='l')
        if kd < 1: label(cv, '0 运费 · 低价心智', W / 2, 840, 40, WHITE, fade(t, T('g5') + 0.2, T('g5') + 2.0, 0.3, 0.4), 'sans_black')
        c = (900, 470); rr = np.random.default_rng(21)
        tb = max(WT('g5', '海量买家'), T('g5') + 1.6); kb = eout(lin(t, tb - 0.4, tb + 0.8))
        tm = max(WT('g5', '商家彼此竞争'), T('g5') + 2.0); km = eout(lin(t, tm - 0.4, tm + 0.8))
        dimc = 1 - 0.8 * ease(lin(t, T('g6') - 0.2, T('g6') + 0.3))
        L = layer(); Lm = layer()
        for i in range(150):
            ang = rr.random() * math.pi; rad = 0.55 + rr.random() * 0.45
            if rr.random() < kb: circle(L, (c[0] + math.cos(ang) * 460 * rad, c[1] - 100 - math.sin(ang) * 210 * rad), 5, fill=True)
        for i in range(70):
            ang = rr.random() * math.pi; rad = 0.5 + rr.random() * 0.5; jit = math.sin(t * 7 + i) * 6 * km
            if rr.random() < km: circle(Lm, (c[0] + math.cos(ang) * 440 * rad + jit, c[1] + 110 + math.sin(ang) * 190 * rad), 8, fill=True)
        stroke_layer(cv, L, BLUE, 0.9 * dimc, glow=0.9); stroke_layer(cv, Lm, (0.95, 0.6, 0.25), 0.9 * dimc, glow=0.9)
        label(cv, '买家', c[0], c[1] - 345, 40, BLUE, kb * dimc, 'sans_black'); label(cv, '商家', c[0], c[1] + 345, 40, (0.95, 0.6, 0.25), km * dimc, 'sans_black')
        kp = ease(lin(t, T('g5') + 1.5, T('g5') + 2.0)) * dimc
        L = layer(); circle(L, c, 80, fill=True); fill(cv, L, (0.85, 0.20, 0.18), 0.95 * kp); label(cv, '平台', c[0], c[1], 44, WHITE, kp, 'sans_black')
        tn = WT('g5', '网络效应'); s, o = pop(t, tn - 0.1)
        label(cv, '✓ 网络效应', 1620, 430, 50, TEAL, o * dimc, 'sans_black', scale=0.9 + 0.1 * s)
        label(cv, '= 条件三', 1620, 510, 46, TEAL, o * dimc, 'sans_black', scale=0.9 + 0.1 * s)
        if t > T('g6') - 0.2:
            a = ease(lin(t, T('g6') - 0.2, T('g6') + 0.3))
            label(cv, '低价里，有一部分来自商家让利', W / 2, 240, 44, (0.95, 0.6, 0.25), a, 'sans_bold')
            tq = WT('g6', '商家还赚不赚得到钱'); s, o = pop(t, tq)
            big(cv, '商家还赚得到钱吗？', W / 2, 370, 92, a=o, scale=0.9 + 0.1 * s, color=WHITE, glow=0.3)
            if t > T('g7') - 0.2:
                tk = WT('g7', '一千亿'); s, o = pop(t, tk - 0.1)
                big(cv, '千亿扶持', W / 2, 555, 110, a=o, scale=0.9 + 0.1 * s, grad=GOLDG)
                label(cv, '2025.04 宣布：未来 3 年投入超 1000 亿元资金、流量等资源', W / 2, 670, 28, WHITE, o, 'sans_med')
                label(cv, 'PDD 2026Q3：营收 1083 亿元 · 经营利润 312 亿元', W / 2, 720, 24, GREY, o, 'sans_light')
        return
    a = ease(lin(t, T('g8') - 0.2, T('g8') + 0.3))
    label(cv, '只会降价的公司', W / 2, 190, 60, WHITE, a, 'serif_black')
    rows = [('结构性', '✗', '设备谁都能买', WT('g8', '设备')), ('可持续', '✗', '补贴谁都能发', WT('g8', '补贴')), ('可转化', '✗', '换不来定价权', WT('g8', '一个都不满足'))]
    V.scorecard(cv, t, 490, 260, rows, a)
    s, o = pop(t, HIT['involution'] - 0.15, 0.5)
    big(cv, '这就是内卷', W / 2, 790, 120, a=o, scale=0.9 + 0.1 * s, grad=REDG, glow=0.6)


def sc_quality(cv, t):
    bg(cv, t, (0.10, 0.05, 0.05) if t > WT('q1', '倒转') else (0.07, 0.07, 0.08))
    if t < T('q3'):
        tr = WT('q1', '倒转'); red = ease(lin(t, tr - 0.3, tr + 0.6)); c = (1160, 490); R = 270
        s, o = pop(t, WT('q1', '质量'))
        if t < T('q2'):
            big(cv, '底线：', 420, 400, 92, a=o, scale=0.9 + 0.1 * s, color=WHITE, glow=0.2)
            big(cv, '质量', 420, 520, 110, a=o, scale=0.9 + 0.1 * s, color=WHITE, glow=0.3)
            ts = [T('q1') + 0.2 + i * 0.12 for i in range(4)]
            V.flywheel(cv, t, c, R, ['低价', '会员\n更多', '采购量\n更大', '成本\n更低'], ts, GOLD, spin=-60 * max(0, t - tr) ** 1.5, red=red, size=88)
            label(cv, '偷工减料', 420, 680, 46, RED, ease(lin(t, WT('q1', '偷工减料'), WT('q1', '偷工减料') + 0.3)), 'sans_black')
        else:
            ts = [WT('q2', '质量下滑'), WT('q2', '信任流失'), WT('q2', '复购减少'), WT('q2', '再降价')]
            V.flywheel(cv, t, c, R, ['质量\n下滑', '信任\n流失', '复购\n减少', '再降价'], ts, RED, spin=-30 * (t - T('q2')) - 60 * max(0, T('q2') - tr) ** 1.5, size=88)
            label(cv, '恶性循环', 420, 470, 84, RED, ease(lin(t, T('q2'), T('q2') + 0.4)), 'serif_black')
        return
    tw = HIT['worth']; a = ease(lin(t, T('q3') - 0.1, T('q3') + 0.4))
    label(cv, '消费者买的，从来不是', W / 2, 200, 50, GREY, a, 'sans_med')
    big(cv, '便宜', W / 2, 320, 110, a=a, color=WHITE, glow=0.1)
    L = layer(); line(L, (W / 2 - 170, 320), (W / 2 - 170 + 340 * ease(lin(t, WT('q3', '而是') - 0.2, WT('q3', '而是') + 0.2)), 320), 8); stroke_layer(cv, L, RED, a, glow=1)
    s, o = pop(t, tw, 0.5)
    big(cv, '值不值', W / 2, 520, 160, a=o, scale=0.9 + 0.1 * s, grad=GOLDG, glow=0.8)
    ko = ease(lin(t, tw + 0.8, tw + 1.3))
    label(cv, '值  =  效用  −  价格  −  麻烦', W / 2, 710, 46, WHITE, ko, 'serif_semi')
    label(cv, '（质量、售后、风险都算在「麻烦」里）', W / 2, 785, 28, GREY, ko, 'sans_light')


FINAL_LINES = (('而是：哪天它涨价了，', 520), ('你还是愿意留下。', 650))


def sc_answer(cv, t):
    bg(cv, t, (0.09, 0.075, 0.05)); DUST.draw(cv, t, GOLD, 0.35)
    if t < T('z3') - 0.1:
        a = ease(lin(t, T('z1') - 0.1, T('z1') + 0.4))
        big(cv, '便宜 ≠ 护城河', W / 2, 180, 104, a=a, grad=GOLDG, glow=0.5)
        label(cv, '低成本要成为护城河，必须同时做到', W / 2, 300, 40, WHITE, ease(lin(t, WT('z1', '低成本'), WT('z1', '低成本') + 0.4)), 'sans_med')
        items = [('结构性', '对手买不到', '对手买不到'), ('可持续', '差距越拉越大', '差距越拉越大'), ('可转化', '换来定价权', '换来定价权')]
        for i, (n, d, key) in enumerate(items):
            s, o = pop(t, WT('z2', key) - 0.15, 0.45); y = 420 + i * 150
            card(cv, 400, y - 62, 1520, y + 62, (0.12, 0.11, 0.09), 0.92 * o, GOLD, glow=0.6)
            check(cv, 490, y, '✓', o, 60)
            label(cv, n, 570, y, 50, GOLD_HI, o, 'sans_black', anchor='l')
            label(cv, d, 1470, y, 46, WHITE, o, 'serif_semi', anchor='r')
        return
    if t < T('z4') - 0.1:
        steps = [('低价', '一种选择', '一种选择', (0.75, 0.75, 0.78)), ('低成本', '一种能力', '一种能力', (0.85, 0.75, 0.55)), ('定价权', '才是护城河', '变成定价权', GOLD)]
        for i, (n, d, key, col) in enumerate(steps):
            s, o = pop(t, WT('z3', key) - 0.3, 0.5)
            x0 = 480 + i * 340; y1 = 830; h = 200 + i * 190
            card(cv, x0, y1 - h * (0.6 + 0.4 * s), x0 + 300, y1, mix(col, INK, 0.65), 0.95 * o, col, r=10, glow=1.4 if i == 2 else 0.3)
            label(cv, n, x0 + 150, y1 - h * (0.6 + 0.4 * s) + 64, 52 if i == 2 else 44, col if i < 2 else GOLD_HI, o, 'sans_black')
            label(cv, d, x0 + 150, y1 - 56, 34, WHITE, o, 'serif_semi')
        return
    photo(cv, 'costco_int2.jpg', t, T('z4') - 0.3, HIT['logo'], 1.05, 1.15, 0.5, 0.5, 0.5, 0.45, sat=0.65, warm=0.55, contrast=1.05, gain=0.35)
    cv[:] = cv2.GaussianBlur(cv, (0, 0), 4); DUST.draw(cv, t, GOLD, 0.4)
    a = ease(lin(t, T('z4') - 0.1, T('z4') + 0.4)) * (1 - ease(lin(t, HIT['logo'] - 0.5, HIT['logo'])))
    label(cv, '真正的护城河，不是', W / 2, 220, 50, GREY, a, 'sans_med')
    big(cv, '“这家最便宜”', W / 2, 340, 100, a=a, color=WHITE, glow=0.1)
    tq = WT('z4', '哪天')
    for i, (l, yy) in enumerate(FINAL_LINES):
        oo = ease(lin(t, tq - 0.3 + i * 0.9, tq + 0.2 + i * 0.9)) * (1 - ease(lin(t, HIT['logo'] - 0.5, HIT['logo'])))
        big(cv, l, W / 2, yy, 84, a=oo, grad=GOLDG, glow=0.6)


# ── 片尾：沿用竖版的粒子与流光，只换纵向位置 ──
LOGO_Y = 330
LOGO = load_logo(300)
V.LOGO_Y = LOGO_Y; V.LOGO = LOGO
Y_BRAND, Y_EN, Y_LINE, Y_F1, Y_F2 = 590, 685, 752, 820, 892


class GatherH(V.Gather):
    """起点换成横版金句的位置"""
    def __init__(self, n=3200, seed=5):
        rng = np.random.default_rng(seed)
        lrgb, lal = LOGO
        ys, xs = np.nonzero(lal > 0.5)
        pick = rng.choice(len(xs), n, replace=len(xs) < n)
        self.tx = xs[pick] + W / 2 - lal.shape[1] / 2 + rng.normal(0, 0.6, n)
        self.ty = ys[pick] + LOGO_Y - lal.shape[0] / 2 + rng.normal(0, 0.6, n)
        self.tc = lrgb[ys[pick], xs[pick]].astype(np.float32)
        src = []
        for line_, yy in FINAL_LINES:
            rgb, al = text_patch(line_, 'serif_black', 84, GOLD, 0.02, 0, GOLDG)
            py, px = np.nonzero(al > 0.5)
            src.append(np.stack([px + W / 2 - al.shape[1] / 2, py + yy - al.shape[0] / 2], 1))
        src = np.concatenate(src); k = int(n * 0.85)
        sp = src[rng.choice(len(src), k)]
        dust = np.stack([rng.random(n - k) * W, rng.random(n - k) * H], 1)
        st = np.concatenate([sp, dust]); rng.shuffle(st)
        self.sx, self.sy = st[:, 0], st[:, 1]
        self.delay = rng.random(n) * 0.45 + (np.hypot(self.sx - W / 2, self.sy - LOGO_Y) / 1400) * 0.3
        self.swirl = (rng.random(n) - 0.5) * 2.2 + 1.1
        self.size = rng.random(n) * 1.2 + 0.6


GATHER = None


def sc_end(cv, t):
    global GATHER
    if GATHER is None: GATHER = GatherH()
    bg(cv, t, (0.07, 0.07, 0.09))
    t0, land, brand, slogan, fade_t = HIT['logo'], HIT['logo_land'], HIT['brand'], HIT['slogan'], HIT['fade']
    u = t - t0; out = 1 - ease(lin(t, fade_t, TOTAL - 0.15))
    DUST.draw(cv, t, GOLD, 0.35 * out)
    dur = land - t0 - 0.55
    pk = 1 - ease(lin(t, land - 0.15, land + 0.55))
    if pk > 0:
        tmp = np.zeros_like(cv); GATHER.draw(tmp, u, dur); cv += tmp * pk
    la = ease(lin(t, land - 0.35, land + 0.35)) * out
    if la > 0:
        rgb, al = LOGO; sc = 1.0 + 0.05 * (1 - eout(lin(t, land - 0.35, land + 1.2)))
        P = 60; g = cv2.GaussianBlur(np.pad(al.astype(np.float32), P), (0, 0), 16)
        blit(cv, np.ones((g.shape[0], g.shape[1], 3), np.float32) * np.asarray((0.43, 0.69, 1.0), np.float32), g, W / 2, LOGO_Y,
             alpha=la * (0.35 + 0.08 * math.sin(t * 2.2)), scale=sc, add=True)
        blit(cv, rgb.astype(np.float32), al.astype(np.float32), W / 2, LOGO_Y, alpha=la, scale=sc)
    v = t - land
    if 0 <= v < 1.1:
        f = (1 - v / 1.1) ** 2
        cv += np.asarray((0.55, 0.75, 1.0), np.float32) * (np.exp(-(((V._XX - W / 2) ** 2 + (V._YY - LOGO_Y) ** 2) / (2 * 240.0 ** 2))))[..., None] * f * 0.55
        L = layer(); circle(L, (W / 2, LOGO_Y), 170 + 520 * eout(v / 1.1), 3 * (1 - v / 1.1) + 1); stroke_layer(cv, L, (0.55, 0.78, 1.0), f * 0.8, glow=2, add=True)
    w_ = t - brand
    if w_ > -0.05:
        a1 = ease(lin(w_, -0.05, 0.2)) * out; s1 = 1.10 - 0.10 * eout(lin(w_, -0.05, 0.6))
        V.shimmer_text(cv, '巴芒价值', W / 2, Y_BRAND, 'serif_black', 112, a1, grad=((1.0, 0.95, 0.78), (0.88, 0.62, 0.24)), track=0.12,
                       scale=s1, sweep=lin(w_, 0.15, 1.35) if w_ < 1.4 else -1, glow=0.6)
        a2 = ease(lin(w_, 0.25, 0.6)) * out
        tw = text_w('巴芒价值', 'serif_black', 112, 0.12); tr_ = max(0.1, (tw - text_w('BUFFETT · MUNGER', 'corm_med', 38)) / (38 * 15))
        V.shimmer_text(cv, 'BUFFETT · MUNGER', W / 2, Y_EN, 'corm_med', 38, a2, color=(0.84, 0.70, 0.44), track=tr_,
                       sweep=lin(w_, 0.45, 1.5) if w_ < 1.6 else -1, glow=0.25)
        if 0 <= w_ < 0.5:
            cv += np.asarray((1.0, 0.82, 0.5), np.float32) * (np.exp(-(((V._XX - W / 2) / 420.0) ** 2 + ((V._YY - Y_BRAND) / 140.0) ** 2)))[..., None] * (1 - w_ / 0.5) ** 2 * 0.2
    z = t - slogan
    if z > -0.6:
        kl = eout(lin(z, -0.6, 0.3)); a3 = out
        L = layer(); line(L, (W / 2 - 290 * kl, Y_LINE), (W / 2 + 290 * kl, Y_LINE), 2); stroke_layer(cv, L, GOLD, 0.85 * a3, glow=1.0)
        L = layer(); circle(L, (W / 2 - 290 * kl, Y_LINE), 3, fill=True); circle(L, (W / 2 + 290 * kl, Y_LINE), 3, fill=True); stroke_layer(cv, L, GOLD_HI, kl * a3, glow=1.5, add=True)
        o1 = ease(lin(z, 0.05, 0.6)) * a3; o2 = ease(lin(z, 0.35, 0.9)) * a3
        text(cv, '关注「巴芒价值」', W / 2, Y_F1 + 14 * (1 - o1), 'serif_semi', 46, (0.96, 0.94, 0.90), alpha=o1, track=0.10, shadow=0.6)
        text(cv, '传承大师智慧，领悟投资真谛', W / 2, Y_F2 + 14 * (1 - o2), 'serif_semi', 40, (0.93, 0.82, 0.60), alpha=o2, track=0.14, shadow=0.6, glow=0.25)
    if t > fade_t: cv *= out


# ═══════════════════════════ 编排 ═══════════════════════════
CLIPS = V.CLIPS


def load_clips():
    for k in ('crowd', 'floor', 'aisle', 'cans', 'fork'):
        CLIPS[k] = Clip('abc_%s.mp4' % k, 1440, 0.5)     # 4:3 画面居中于 16:9，横版取整幅 4:3


SC = [
    (0.0, T('o7') - 0.3, sc_involution), (T('o7') - 0.3, T('o9'), sc_open), (T('o9'), HIT['title'], sc_split),
    (HIT['title'], T('p1') - 0.25, sc_title), (T('p1') - 0.25, T('p6') - 0.3, sc_first), (T('p6') - 0.3, T('p10') - 0.25, sc_textile),
    (T('p10') - 0.25, T('d1') - 0.3, sc_test), (T('d1') - 0.3, T('k1') - 0.3, sc_clash), (T('k1') - 0.3, T('k5') - 0.3, sc_cond1),
    (T('k5') - 0.3, T('k8') - 0.3, sc_cond2), (T('k8') - 0.3, T('g1') - 0.25, sc_cond3), (T('g1') - 0.25, T('q1') - 0.3, sc_china),
    (T('q1') - 0.3, T('z1') - 0.3, sc_quality), (T('z1') - 0.3, HIT['logo'], sc_answer), (HIT['logo'], TOTAL + 1, sc_end)]


def subtitle(cv, t):
    for t0, t1, s in SUBS:
        if t0 - 0.04 <= t <= t1:
            a = ease(lin(t, t0 - 0.04, t0 + 0.1)) * (1 - ease(lin(t, t1 - 0.1, t1)))
            n = sum(0.55 if ch.isdigit() or ch in '.%' else 1 for ch in s)
            size = 50 if n <= 24 else int(50 * 24 / n)
            w = text_w(s, 'sans_bold', size) + 70
            L = layer(); rect(L, W / 2 - w / 2, SUB_Y - 44, W / 2 + w / 2, SUB_Y + 44, r=14); fill(cv, L, (0, 0, 0), 0.42 * a)
            text(cv, s, W / 2, SUB_Y, 'sans_bold', size, WHITE, alpha=a, shadow=0.5)


def render(fi):
    t = fi / FPS; cv = np.zeros((H, W, 3), np.float32)
    act = []
    for s0, s1, fn in SC:
        xf0 = V.XF_END if s0 == HIT['logo'] else V.XF; xf1 = V.XF_END if s1 == HIT['logo'] else V.XF
        lead = 0 if s0 in V.HARD else xf0 / 2; tail = 0 if s1 in V.HARD else xf1 / 2
        if s0 - lead <= t < s1 + tail:
            w = 1.0
            if t < s0 + lead and lead: w = min(w, ease((t - (s0 - lead)) / (2 * lead)))
            if t > s1 - tail and tail: w = min(w, 1 - ease((t - (s1 - tail)) / (2 * tail)))
            act.append((w, fn))
    tot = sum(w for w, _ in act) or 1
    for w, fn in act:
        _e.CUR_W = w / tot if len(act) > 1 else w
        if _e.REC is not None: _e.SCENE_START = [len(_e.REC), len(_e.TXT_INK)]
        tmp = np.zeros_like(cv); fn(tmp, t); cv += tmp * _e.CUR_W
    _e.CUR_W = 1.0
    V.chapter_tag(cv, t)
    finish(cv, fi)
    subtitle(cv, t)
    if t < HIT['logo'] - 0.2: HUD.draw(cv, t)
    if t < 0.35: cv *= ease(t / 0.35)
    return cv


if __name__ == '__main__':
    mode = sys.argv[2]; load_clips()
    if mode == 'still':
        for x in sys.argv[3:]:
            t = float(x); cv2.imwrite(os.path.join(WORK, 'hstill_%06.2f.png' % t), to8(render(int(round(t * FPS))))[..., ::-1]); print('still', t)
    elif mode == 'chunk':
        f0, f1, out = int(sys.argv[3]), min(int(sys.argv[4]), NF), sys.argv[5]
        p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS),
                              '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
        for fi in range(f0, f1):
            p.stdin.write(to8(render(fi)).tobytes())
            if (fi - f0) % 150 == 0: print('chunk', f0, fi, flush=True)
        p.stdin.close(); p.wait()
    elif mode == 'nf': print(NF)
    elif mode == 'audit':
        t0, t1, step, out = float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), sys.argv[6]; res = []
        for t in np.arange(t0, t1, step):
            _e.REC = []; _e.GMASK = np.zeros((H, W), np.float32); _e.TXT_INK = []
            render(int(round(t * FPS)))
            hits = []
            for s_, x0, y0, m, a in _e.TXT_INK:
                h, w = m.shape; xa, ya = max(0, x0), max(0, y0); xb, yb = min(W, x0 + w), min(H, y0 + h)
                if xb <= xa or yb <= ya: continue
                mm = m[ya - y0:yb - y0, xa - x0:xb - x0]; g = _e.GMASK[ya:yb, xa:xb] > 0.3
                n = int((mm & g).sum()); tot = int(mm.sum())
                if a >= 0.35 and (n >= 60 or n >= 0.008 * max(1, tot)) and n >= 20: hits.append(('onGraphic', s_, n, round(n / max(1, tot), 3), a))
            res.append((round(float(t), 2), _e.REC + hits)); _e.REC = None; _e.GMASK = None; _e.TXT_INK = None
        json.dump(res, open(out, 'w'), ensure_ascii=False)
