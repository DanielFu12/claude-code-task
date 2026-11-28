"""《多付的钱，买的是什么｜身份成为护城河的三道关》全部分镜（1080×1920 · 30fps）。
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
    s = ('视频' if key.startswith('v_') else '图') + '：%s · %s · Wikimedia Commons' % (c.get('artist', '')[:34], c.get('license', ''))
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
GOLDG = ((1.0, 0.93, 0.72), (0.90, 0.62, 0.26))
REDG = ((1.0, 0.55, 0.48), (0.78, 0.18, 0.16))
TEALG = ((0.70, 0.98, 0.90), (0.30, 0.72, 0.64))


def card(cv, x0, y0, x1, y1, col=(0.12, 0.13, 0.16), a=1.0, edge=None, r=16, glow=0.6):
    import engine as _e; _e.rec_box('card', x0, y0, x1, y1, '', a)
    L = layer(); rect(L, x0, y0, x1, y1, r=r); fill(cv, L, col, a)
    if edge is not None:
        L = layer(); rect(L, x0, y0, x1, y1, fill=False, w=2, r=r); stroke_layer(cv, L, edge, a, glow=glow)


def wrap(s, n):
    out, cur = [], ''
    for ch in s:
        cur += ch
        if len(cur) >= n and ch in '，。；：、？！”' or len(cur) >= n + 3: out.append(cur); cur = ''
    if cur: out.append(cur)
    return out


def quote_block(cv, lines, x, y, size, a, fname='serif_semi', color=WHITE, lh=1.45, anchor='l', reveal=1.0):
    tot = sum(len(l) for l in lines); n = int(tot * reveal + 0.999)
    for i, l in enumerate(lines):
        k = max(0, min(len(l), n)); n -= len(l)
        if k > 0: text(cv, l[:k], x, y + i * size * lh, fname, size, color, anchor=anchor, alpha=a, shadow=0.5)


def check(cv, x, y, kind, a, size=44):
    col = {'✓': TEAL, '✗': RED, '?': (0.98, 0.78, 0.35)}[kind]
    L = layer(); circle(L, (x, y), size * 0.62, fill=True); fill(cv, L, col, 0.9 * a)
    label(cv, {'✗': '×'}.get(kind, kind), x, y, size * (0.95 if kind == '✗' else 0.8), INK, a, 'sans_black')



# ── 通用小部件 ──
def panel(cv, name, x0, y0, x1, y1, a=1.0, zoom=1.0, cx=0.5, cy=0.5, edge=None, **g):
    """图片放进一个矩形框（cover 裁切）"""
    if a <= 0.003: return
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    fr = cover(graded(name, **g), x1 - x0, y1 - y0, zoom, cx, cy)
    sub = cv[y0:y1, x0:x1]; sub *= (1 - a); sub += fr * a
    if edge is not None:
        L = layer(); rect(L, x0, y0, x1, y1, fill=False, w=2); stroke_layer(cv, L, edge, 0.75 * a, glow=0.4)


def vpanel(cv, clip, t, t0, x0, y0, x1, y1, a=1.0, zoom=1.0, z1=None, dur=6.0, edge=GOLD, **g):
    """视频片段放进矩形框"""
    if a <= 0.003: return
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    f = grade(clip.get(t - t0), **g); zz = zoom if z1 is None else zoom + (z1 - zoom) * ease(lin(t, t0, t0 + dur))
    fr = cover(f, x1 - x0, y1 - y0, zz)
    sub = cv[y0:y1, x0:x1]; sub *= (1 - a); sub += fr * a
    if edge is not None:
        L = layer(); rect(L, x0, y0, x1, y1, fill=False, w=2); stroke_layer(cv, L, edge, 0.75 * a, glow=0.4)


def vframe(cv, clip, t, t0, y0, a=1.0, z0=1.0, z1=1.06, dur=6.0, **g):
    """横屏视频竖排：背后铺同一画面的虚化放大版，中间放 16:9 清晰画面（不放大低清素材）"""
    if a <= 0.003: return
    f = grade(clip.get(t - t0), **g); zz = z0 + (z1 - z0) * ease(lin(t, t0, t0 + dur))
    small = cover(f, W // 6, H // 6, 1.0)
    bg = cv2.resize(cv2.GaussianBlur(small, (0, 0), 7), (W, H), interpolation=cv2.INTER_LINEAR) * 0.42
    cv *= (1 - a); cv += bg * a
    h = int(round(W * f.shape[0] / f.shape[1])); fr = cover(f, W, h, zz)
    sub = cv[y0:y0 + h]; sub *= (1 - a); sub += fr * a
    L = layer(); L[max(0, y0 - 1):y0 + 1] = 1; L[y0 + h - 1:y0 + h + 1] = 1
    stroke_layer(cv, L, GOLD, 0.35 * a)


def source(cv, s, a=1.0, y=1330):
    text(cv, s, 56, y, 'sans_light', 24, GREY, anchor='l', alpha=0.8 * a)


def stat(cv, x, y, num, unit, a, col=GOLD, size=150, usize=56, fname='oswald', grad=None):
    """数字 + 单位分开渲染（Oswald 没有中文）"""
    if a <= 0.003: return
    gap = 0.35 * (size - usize) + 0.08 * size; wn = text_w(num, fname, size); wu = text_w(unit, 'sans_black', usize) if unit else 0
    x0 = x - (wn + wu + gap) / 2
    text(cv, num, x0, y, fname, size, col, anchor='l', alpha=a, shadow=0.6, glow=0.4, grad=grad)
    if unit: text(cv, unit, x0 + wn + gap, y + size * 0.18, 'sans_black', usize, col, anchor='l', alpha=a, shadow=0.6)


def gates(cv, t, a, active=-1, y=300, done=()):
    """三道关：三座拱门，active 高亮，done 已通过"""
    names = ('认得出', '仿不了', '稀释不了')
    for i, n in enumerate(names):
        x = 210 + i * 330; on = i == active; ok = i in done
        col = GOLD if on else (TEAL if ok else (0.42, 0.44, 0.50))
        L = layer(); arc(L, (x, y), 62, -90, 90, 4); line(L, (x - 62, y), (x - 62, y + 70), 4); line(L, (x + 62, y), (x + 62, y + 70), 4)
        stroke_layer(cv, L, col, a * (1.0 if on or ok else 0.6), glow=1.2 if on else 0.2)
        label(cv, n, x, y + 118, 36 if on else 30, col, a * (1.0 if on or ok else 0.7), 'sans_black' if on else 'sans_med')


def chip(cv, s, x, y, a, col=GOLD, size=36, fill_=(0.10, 0.10, 0.12), anchor='c'):
    if a <= 0.003: return
    w = text_w(s, 'sans_bold', size) + 48; h = size + 34
    x0 = x - w / 2 if anchor == 'c' else x if anchor == 'l' else x - w
    card(cv, x0, y - h / 2, x0 + w, y + h / 2, fill_, 0.92 * a, col, r=h / 2, glow=0.3)
    label(cv, s, x0 + w / 2, y, size, col, a, 'sans_bold')


def arrow(lay, p0, p1, w=4, head=18):
    line(lay, p0, p1, w)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for d in (2.6, -2.6):
        line(lay, p1, (p1[0] + head * math.cos(ang + d), p1[1] + head * math.sin(ang + d)), w)


ORANGE = (1.0, 0.52, 0.18); ORANGEG = ((1.0, 0.74, 0.45), (0.95, 0.40, 0.12))
COLD = (0.62, 0.70, 0.82)


# ═══════════════════════ 引子 · 一年两半 ═══════════════════════
def sc_intro(cv, t):
    """o1 九颗尖牙 → 香港机场 7 米 Labubu → 门店长队；o2 拍卖 108 万"""
    bg(cv, t, (0.06, 0.05, 0.07))
    if t < T('o2') - 0.15:
        # 九颗尖牙：线稿一笔画出
        k = eout(lin(t, 0.2, 1.6)); fade_ = 1 - ease(lin(t, 1.9, 2.5))
        if fade_ > 0:
            L = layer(); n = 9; x0, x1, yb = 190, 890, 820
            pts = []
            for i in range(n + 1):
                pts.append((x0 + (x1 - x0) * i / n, yb + 18 * math.sin(math.pi * i / n)))
                if i < n: pts.append((x0 + (x1 - x0) * (i + 0.5) / n, yb + 105 + 26 * math.sin(math.pi * (i + 0.5) / n)))
            m = max(2, int(len(pts) * k)); poly(L, pts[:m], 5)
            stroke_layer(cv, L, WHITE, fade_, glow=1.6)
        # 7 米 Labubu（香港机场）
        if t > 1.9:
            a = ease(lin(t, 1.9, 2.5)) * (1 - ease(lin(t, WT('o1', '门店') - 0.5, WT('o1', '门店'))))
            vframe(cv, CLIPS['airport'], t, 1.9, 560, a, 1.0, 1.08, 4, sat=0.95, warm=0.2, contrast=1.08, gain=0.95)
            label(cv, '2025.09 · 香港国际机场 · 7 米高的特别版 LABUBU', W / 2, 1250, 30, WHITE, a * 0.9, 'sans_med')
            credit(cv, 'v_airport', a)
        tq = WT('o1', '门店') - 0.5
        if t > tq:
            a = ease(lin(t, tq, tq + 0.5))
            photo(cv, 'queue1.jpg', t, tq, T('o2'), 1.06, 1.18, 0.5, 0.5, 0.5, 0.5, a=a, sat=0.9, warm=0.2, contrast=1.08, gain=0.85)
            shade(cv, 0.35, 0.85, 0.1)
            ql = ease(lin(t, tq + 0.5, tq + 0.8))     # 机场标注淡完再出
            label(cv, '香港将军澳 · 泡泡玛特门前的长队 · 2025.04', W / 2, 1250, 30, WHITE, ql * 0.9, 'sans_med')
            credit(cv, 'queue1', ql)
        return
    # o2 拍卖：背景纽约门店照片虚化，拍卖槌落下，数字滚到 108 万
    photo(cv, 'browsing.jpg', t, T('o2') - 0.3, T('o3'), 1.15, 1.25, 0.5, 0.5, 0.5, 0.5, sat=0.6, warm=0.4, contrast=1.05, gain=0.32)
    cv[:] = cv2.GaussianBlur(cv, (0, 0), 6)
    th = HIT['auction']; u = t - th
    ang = -38 * (1 - ein(lin(t, th - 0.55, th))) + (4 * math.exp(-u * 9) * math.sin(u * 40) if u > 0 else 0)
    L = layer(); cx, cy = 600, 520; ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    def R(x, y): return (cx + x * ca - y * sa, cy + x * sa + y * ca)
    poly(L, [R(-150, -46), R(-10, -46), R(-10, 46), R(-150, 46)], 5, closed=True)
    line(L, R(-80, 46), R(-80, 300), 9)
    line(L, (390, 640), (780, 640), 6)
    a0 = ease(lin(t, T('o2') - 0.1, T('o2') + 0.4))
    stroke_layer(cv, L, GOLD, a0, glow=1.0)
    if 0 <= u < 0.9:
        L = layer(); circle(L, (585, 640), 30 + 120 * eout(u / 0.9), 4 * (1 - u / 0.9) + 1); stroke_layer(cv, L, GOLD_HI, (1 - u / 0.9) * 0.9, glow=2, add=True)
    n = 1080000 * eout(lin(t, th - 0.6, th + 0.1))
    o = ease(lin(t, th - 0.6, th - 0.3))
    stat(cv, W / 2, 900, '¥' + counter(n), '', o, size=150, grad=GOLDG)
    label(cv, '1.31 米 · 薄荷色 · 全球仅此一只', W / 2, 1050, 38, WHITE, ease(lin(t, th, th + 0.4)), 'sans_bold')
    label(cv, '北京永乐拍卖 · 2025.06.10 · 成交价含佣金', W / 2, 1110, 28, GREY, ease(lin(t, th + 0.2, th + 0.6)), 'sans_med')
    credit(cv, 'browsing', a0)


def sc_orange(cv, t):
    """o3 爱马仕橙 → o4 借名字 → o5 价格里的那一截"""
    bg(cv, t, (0.09, 0.06, 0.04))
    if t < T('o4') - 0.1:
        photo(cv, 'iphone_orange.jpg', t, T('o3') - 0.4, T('o4'), 1.05, 1.18, 0.5, 0.5, 0.5, 0.45, sat=1.0, warm=0.15, contrast=1.08, gain=0.85)
        shade(cv, 0.4, 0.85, 0.12)
        tw = WT('o3', '爱马仕橙'); s, o = pop(t, tw - 0.1, 0.5)
        big(cv, '“爱马仕橙”', W / 2, 1060, 128, a=o, scale=0.9 + 0.1 * s, grad=ORANGEG, glow=0.6)
        label(cv, 'iPhone 17 Pro · 宇宙橙 · 2025 秋', W / 2, 1200, 32, WHITE, ease(lin(t, T('o3'), T('o3') + 0.5)), 'sans_med')
        credit(cv, 'iphone_orange', 1)
        return
    if t < T('o5') - 0.1:
        k = eout(lin(t, T('o4') - 0.1, T('o4') + 0.6))
        panel(cv, 'iphone_back.jpg', 0, 0, W // 2, H, 1, 1.15, 0.5, 0.45, sat=1.0, warm=0.15, gain=0.8)
        panel(cv, 'hermes_ginza.jpg', W // 2, 0, W, H, k, 1.1, 0.5, 0.5, sat=0.95, warm=0.3, gain=0.8)
        shade(cv, 0.35, 0.85, 0.12)
        L = layer(); line(L, (W / 2, 0), (W / 2, 1290 * k), 3); stroke_layer(cv, L, ORANGE, 0.9, glow=1.4)
        o = ease(lin(t, WT('o4', '皮具品牌') - 0.2, WT('o4', '皮具品牌') + 0.3))
        label(cv, 'iPhone', W / 4, 1150, 52, WHITE, 1, 'playfair')
        label(cv, 'HERMÈS', W * 3 / 4, 1150, 52, ORANGE, o, 'playfair', track=0.1)
        label(cv, '手机', W / 4, 1220, 30, GREY, 1, 'sans_med'); label(cv, '东京银座 · 爱马仕之家', W * 3 / 4, 1220, 30, GREY, o, 'sans_med')
        text(cv, '图：%s · %s ／ %s · %s' % (CREDIT['iphone_back']['artist'][:16], CREDIT['iphone_back']['license'],
                                         CREDIT['hermes_ginza']['artist'][:16], CREDIT['hermes_ginza']['license']), 56, 1330, 'sans_light', 22, GREY, anchor='l', alpha=0.75)
        return
    # o5：一张价签，三截；最上面一截变成金色，打上问号
    a = ease(lin(t, T('o5') - 0.1, T('o5') + 0.4)); x0, x1, yb = 330, 750, 1180
    segs = [(0.0, 0.42, (0.36, 0.38, 0.42), '东西本身'), (0.42, 0.70, (0.40, 0.52, 0.66), ''), (0.70, 1.0, GOLD, '这一截？')]
    tg = WT('o5', '有一截'); hh = 820
    for i, (s0, s1, col, lab) in enumerate(segs):
        y0 = yb - hh * s1; y1 = yb - hh * s0
        c = col if i < 2 else mix((0.40, 0.52, 0.66), GOLD, ease(lin(t, tg - 0.2, tg + 0.5)))
        card(cv, x0, y0 + 3, x1, y1 - 3, mix(c, INK, 0.25), 0.95 * a, c, r=10, glow=1.2 if i == 2 else 0.2)
    label(cv, '价格', W / 2, yb + 60, 40, WHITE, a, 'sans_black')
    o = ease(lin(t, tg, tg + 0.5))
    big(cv, '?', W / 2, yb - hh * 0.85, 120, a=o, color=INK, glow=0.0)
    label(cv, '东西本身', W / 2, yb - hh * 0.21, 40, WHITE, a, 'sans_bold')


def sc_halves(cv, t):
    """o6 一分为二 → o7 泡泡玛特 → o8 老铺黄金 → o9 爱马仕 → o10 1 年 vs 189 年"""
    bg(cv, t, (0.07, 0.06, 0.07))
    if t < T('o7') - 0.1:
        k = eout(lin(t, T('o6') - 0.1, T('o6') + 0.8)); off = int((1 - k) * 260)
        left = cover(graded('nyc_store.jpg', sat=0.35, warm=-0.6, contrast=1.15, gain=0.55), W // 2, H, 1.25, 0.5, 0.5)
        right = cover(graded('birkin.jpg', sat=1.0, warm=0.5, contrast=1.1, gain=0.85), W // 2, H, 1.2, 0.5, 0.5)
        cv[:, :W // 2] = np.roll(left, off, 0) * k; cv[:, W // 2:] = np.roll(right, -off, 0) * k
        shade(cv, 0.3, 0.8, 0.1)
        L = layer(); line(L, (W / 2, 0), (W / 2, 1290 * k), 3); stroke_layer(cv, L, GOLD, 0.9, glow=1.5)
        s, o = pop(t, WT('o6', '两半'))
        label(cv, '泡泡玛特 · 老铺黄金', W / 4, 1200, 34, (1.0, 0.70, 0.62), o, 'sans_black')
        label(cv, '爱马仕', W * 3 / 4, 1200, 34, GOLD_HI, o, 'sans_black')
        return
    if t < T('o8') - 0.1:
        photo(cv, 'nyc_store.jpg', t, T('o7') - 0.3, T('o8'), 1.1, 1.2, 0.5, 0.5, 0.5, 0.5, sat=0.35, warm=-0.5, contrast=1.1, gain=0.35)
        a = ease(lin(t, T('o7') - 0.1, T('o7') + 0.4))
        big(cv, '泡泡玛特', W / 2, 290, 96, a=a, color=(1.0, 0.72, 0.64), glow=0.2)
        t1 = WT('o7', '收入'); o1 = ease(lin(t, t1 - 0.2, t1 + 0.3))
        card(cv, 110, 420, 970, 720, (0.10, 0.07, 0.08), 0.9 * o1, RED, glow=0.4)
        label(cv, '2026 年第三季度 · 收入同比', W / 2, 480, 34, WHITE, o1, 'sans_bold')
        stat(cv, W / 2, 620, '−45%~−50%', '', ease(lin(t, WT('o7', '将近一半') - 0.3, WT('o7', '将近一半'))), col=RED, size=120, grad=REDG)
        t2 = WT('o7', '隐藏款'); o2 = ease(lin(t, t2 - 0.2, t2 + 0.3))
        card(cv, 110, 770, 970, 1180, (0.10, 0.07, 0.08), 0.9 * o2, RED, glow=0.4)
        label(cv, '最火的隐藏款 · 二手价较峰值', W / 2, 830, 34, WHITE, o2, 'sans_bold')
        kk = eout(lin(t, t2, WT('o7', '近九成', end=True)))
        L = layer(); pts = []
        for i in range(41):
            x = 170 + 740 * i / 40; u = i / 40
            v = 0.15 + 0.85 * (u / 0.25) ** 0.6 if u < 0.25 else 1.0 - 0.88 * ((u - 0.25) / 0.75) ** 0.7
            pts.append((x, 1140 - 230 * v))
        m = max(2, int(len(pts) * kk)); poly(L, pts[:m], 5); stroke_layer(cv, L, RED, o2, glow=1.0)
        stat(cv, 780, 920, '−88%', '', ease(lin(t, WT('o7', '近九成') - 0.3, WT('o7', '近九成'))), col=RED, size=92, grad=REDG)
        source(cv, '公司公告 2026.10.27 ／ 隐藏款“本我”：得物二手成交价，据媒体报道', a)
        return
    if t < T('o9') - 0.1:
        photo(cv, 'gold_bracelet.jpg', t, T('o8') - 0.3, T('o9'), 1.1, 1.25, 0.5, 0.5, 0.5, 0.5, sat=0.9, warm=0.4, contrast=1.1, gain=0.42)
        a = ease(lin(t, T('o8') - 0.1, T('o8') + 0.4))
        big(cv, '老铺黄金', W / 2, 290, 96, a=a, grad=GOLDG, glow=0.4)
        label(cv, '被媒体称作“黄金界爱马仕”', W / 2, 390, 34, WHITE, ease(lin(t, WT('o8', '黄金界') - 0.2, WT('o8', '黄金界') + 0.3)), 'sans_med')
        t1 = WT('o8', '股价'); o1 = ease(lin(t, t1 - 0.2, t1 + 0.3))
        card(cv, 110, 480, 970, 980, (0.10, 0.08, 0.06), 0.9 * o1, GOLD, glow=0.3)
        label(cv, '股价 · 较 2025 年 7 月高点', W / 2, 540, 34, WHITE, o1, 'sans_bold')
        kk = eout(lin(t, t1, WT('o8', '七成', end=True)))
        L = layer(); pts = []
        for i in range(41):
            u = i / 40; v = 1.0 - 0.73 * (u ** 0.8) + 0.05 * math.sin(u * 19)
            pts.append((170 + 740 * u, 930 - 300 * v))
        m = max(2, int(len(pts) * kk)); poly(L, pts[:m], 5); stroke_layer(cv, L, RED, o1, glow=1.0)
        stat(cv, 780, 640, '−73%', '', ease(lin(t, WT('o8', '七成') - 0.3, WT('o8', '七成'))), col=RED, size=92, grad=REDG)
        s, o = pop(t, WT('o8', '促销') - 0.1)
        chip(cv, '门店开始促销', W / 2, 1090, o, RED, 40, (0.16, 0.06, 0.06))
        source(cv, '股价：2026.07.29 收盘，较历史高点约 −73% ／ 促销：21 世纪经济报道 2026.11 门店走访', a)
        credit(cv, 'gold_bracelet', a, y=1380)
        return
    if t < T('o10') - 0.1:
        photo(cv, 'birkin.jpg', t, T('o9') - 0.3, T('o10'), 1.08, 1.2, 0.5, 0.5, 0.5, 0.5, sat=1.0, warm=0.45, contrast=1.08, gain=0.62)
        shade(cv, 0.4, 0.85, 0.15)
        a = ease(lin(t, T('o9') - 0.1, T('o9') + 0.4))
        big(cv, 'HERMÈS', W / 2, 300, 110, a=a, fname='playfair', grad=GOLDG, glow=0.5, track=0.12)
        t1 = WT('o9', '百分之十三'); s, o = pop(t, t1 - 0.25, 0.5)
        stat(cv, W / 2, 760, '+13%', '', o, size=210, grad=GOLDG)
        label(cv, '2025 年 · 皮具与马具 · 销售增长（固定汇率）', W / 2, 920, 34, WHITE, ease(lin(t, T('o9'), T('o9') + 0.5)), 'sans_bold')
        source(cv, '爱马仕 2025 年度业绩公告（2026.02.12）', a)
        credit(cv, 'birkin', a, y=1380)
        return
    # o10：1 年 vs 189 年
    a = ease(lin(t, T('o10') - 0.1, T('o10') + 0.4))
    panel(cv, 'nyc_store.jpg', 0, 0, W // 2, H, a, 1.3, sat=0.3, warm=-0.6, gain=0.28)
    panel(cv, 'birkin.jpg', W // 2, 0, W, H, a, 1.3, sat=0.9, warm=0.5, gain=0.4)
    L = layer(); line(L, (W / 2, 140), (W / 2, 1270), 3); stroke_layer(cv, L, GOLD, 0.8 * a, glow=1.2)
    t1 = WT('o10', '一年'); s1, o1 = pop(t, t1 - 0.15)
    stat(cv, W / 4, 640, '1', '年', o1, col=(1.0, 0.62, 0.55), size=200, usize=70)
    label(cv, '就退潮', W / 4, 820, 44, WHITE, o1, 'sans_black')
    t2 = WT('o10', '两百年'); s2, o2 = pop(t, t2 - 0.15)
    yrs = int(round(189 * eout(lin(t, t2 - 0.3, t2 + 0.5))))
    stat(cv, W * 3 / 4, 640, '%d' % yrs, '年', o2, size=200, usize=70, grad=GOLDG)
    label(cv, '还在涨价', W * 3 / 4, 820, 44, WHITE, ease(lin(t, WT('o10', '涨价') - 0.2, WT('o10', '涨价') + 0.2)), 'sans_black')
    label(cv, '创立于 1837 年', W * 3 / 4, 890, 28, GREY, o2, 'sans_med')
    label(cv, '2026.01 铂金包提价约 6%~9%', W * 3 / 4, 940, 28, GREY, ease(lin(t, WT('o10', '涨价'), WT('o10', '涨价') + 0.4)), 'sans_med')
    source(cv, '提价幅度：Sotheby’s、Pursebop 等对美国 / 欧洲门店价格的整理', ease(lin(t, WT('o10', '涨价'), WT('o10', '涨价') + 0.4)))


def sc_question(cv, t):
    bg(cv, t, (0.08, 0.07, 0.06)); DUST.draw(cv, t, GOLD, 0.3)
    a = ease(lin(t, T('o11') - 0.1, T('o11') + 0.4)) * (1 - ease(lin(t, T('o12') - 0.3, T('o12'))))
    label(cv, '一个更老的问题', W / 2, CY, 56, GREY, a, 'serif_semi', track=0.1)
    s, o = pop(t, T('o12') - 0.1, 0.6)
    big(cv, '多付的那部分钱，', W / 2, CY - 90, 92, a=o, color=WHITE, glow=0.2, scale=0.95 + 0.05 * s)
    big(cv, '到底买到了什么？', W / 2, CY + 60, 92, a=ease(lin(t, WT('o12', '到底') - 0.2, WT('o12', '到底') + 0.3)), grad=GOLDG, glow=0.5)


def sc_title(cv, t):
    """片名：多付的钱，买的是什么 ｜ 身份成为护城河的三道关"""
    bg(cv, t, (0.10, 0.08, 0.06)); t0 = HIT['title']; u = t - t0
    DUST.draw(cv, t, GOLD, 0.35)
    if 0 <= u < 1.2:
        L = layer(); circle(L, (W / 2, CY), 60 + 900 * eout(u / 1.2), 6 * (1 - u / 1.2) + 1)
        stroke_layer(cv, L, GOLD_HI, (1 - u / 1.2) * 0.8, glow=2.0, add=True)
    L = layer(); R = 470; brk = ease(lin(u, 0.9, 2.6))
    for i in range(12):
        a0 = i * 30 + 3; a1 = a0 + 24
        dx = math.sin(math.radians(a0 + 12)) * 60 * brk; dy = -math.cos(math.radians(a0 + 12)) * 60 * brk
        arc(L, (W / 2 + dx, CY + dy), R + 14 * brk, a0 + 6 * brk * ((i % 2) - 0.5), a1 - 3 * brk, 5)
    stroke_layer(cv, L, GOLD, ease(lin(u, 0, 0.5)) * (1 - 0.45 * brk), glow=1.6, add=True)
    s, o = pop(t, t0, 0.5); sc_ = 1.12 - 0.12 * s + 0.02 * u / 3
    big(cv, '多付的钱，', W / 2, CY - 150, 112, a=o, scale=sc_, grad=GOLDG, glow=0.7, track=0.04)
    big(cv, '买的是什么', W / 2, CY - 10, 112, a=o, scale=sc_, grad=GOLDG, glow=0.7, track=0.04)
    s2, o2 = pop(t, t0 + 0.6, 0.5)
    big(cv, '身份成为护城河的三道关', W / 2, CY + 130, 54, a=o2, scale=0.9 + 0.1 * s2, color=WHITE, fname='serif_semi', glow=0.15, track=0.08)
    label(cv, 'STATUS AS A MOAT · FIRST PRINCIPLES', W / 2, CY + 215, 26, GOLD, o2 * 0.85, 'corm_med', track=0.25)
    if 0 <= u < 0.35: cv += np.asarray((1.0, 0.85, 0.6), np.float32) * (1 - u / 0.35) ** 2 * 0.55


# ═══════════════════════ 01 · 第一性原理 ═══════════════════════
RC = (W / 2, 720)


def sc_three(cv, t):
    """p1–p5 三个问题：功能 / 认同 / 地位 三个同心环"""
    bg(cv, t, (0.06, 0.07, 0.10))
    rings = [(150, '功能', 'FUNCTION', COLD, 'p2'), (290, '认同', 'IDENTITY', TEAL, 'p3'), (430, '地位', 'STATUS', GOLD, 'p4')]
    hl = ease(lin(t, T('p5') - 0.1, T('p5') + 0.5))
    hl2 = ease(lin(t, T('p5') - 0.1, T('p5') + 0.25))
    for i, (r, n, en, col, lid) in enumerate(rings):
        s, o = pop(t, WT(lid, '这是') - 0.1, 0.5)
        dimk = (1 - 0.6 * hl) if i == 0 else (1 + 0.4 * hl)
        L = layer(); circle(L, RC, r * (0.85 + 0.15 * s), 4 if i else 5)
        stroke_layer(cv, L, col, o * min(1, dimk), glow=0.8 * dimk)
        if i == 0:
            label(cv, n, RC[0], RC[1] - 14, 56, col, o * min(1, dimk), 'sans_black')
            label(cv, en, RC[0], RC[1] + 44, 22, GREY, o * min(1, dimk), 'corm_med', track=0.2)
        else:
            yy = RC[1] - (r - 70)
            label(cv, n, RC[0], yy - 6, 52, col, o, 'sans_black', glow=0.3 * hl)
            label(cv, en, RC[0], yy + 44, 22, GREY, o, 'corm_med', track=0.2)
    a = ease(lin(t, T('p1') - 0.2, T('p1') + 0.4))
    label(cv, '人买东西，在回答三个问题', W / 2, 1250, 36, WHITE, a * (1 - ease(lin(t, T('p5') - 0.45, T('p5') - 0.15))), 'sans_med')
    label(cv, '品牌溢价，很大一部分来自外面两圈', W / 2, 1250, 38, GOLD_HI, hl2, 'sans_bold')
    # p5b：不全是虚荣（认同圈：归属、审美、生活方式）→ 只看“别人怎样看我”
    tf = WT('p5b', '最微妙'); off = ease(lin(t, tf - 0.3, tf + 0.2))
    for i, w_ in enumerate(('归属感', '审美', '生活方式')):
        tw = WT('p5b', w_); s, o = pop(t, tw - 0.15, 0.4)
        chip(cv, w_, (300, 540, 780)[i], 1340, o * (1 - off), TEAL, 34)
    s, o = pop(t, tf, 0.5)
    label(cv, '这一期：别人怎样看我', W / 2, 1340, 40, GOLD, o, 'serif_black', glow=0.3)


def sc_envy(cv, t):
    """p6–p7 芒格：驱动世界的是嫉妒；p8 1956 年车展人群围着新车"""
    bg(cv, t, (0.07, 0.065, 0.06))
    if t < T('p8') - 0.1:
        a = ease(lin(t, T('p6') - 0.2, T('p6') + 0.5))
        panel(cv, 'munger.jpg', 0, 0, W, 900, a, 1.15, 0.5, 0.32, sat=0.2, warm=0.45, contrast=1.1, gain=0.75)
        y = np.linspace(0, 1, 900, dtype=np.float32)[:, None, None]; cv[:900] *= (1 - 0.9 * np.clip((y - 0.55) / 0.45, 0, 1))
        label(cv, '查理 · 芒格', 80, 820, 46, GOLD, a, 'serif_black', anchor='l')
        label(cv, 'Charlie Munger', 80, 872, 26, GREY, a, 'corm_med', anchor='l', track=0.1)
        tq = T('p7'); o = ease(lin(t, tq - 0.1, tq + 0.4))
        card(cv, 80, 950, 1000, 1290, (0.10, 0.09, 0.08), 0.92 * o, GOLD, glow=0.4)
        label(cv, '“The world is not driven by greed.', 120, 1010, 34, GREY, o, 'playfair', anchor='l')
        label(cv, ' It’s driven by envy.”', 120, 1060, 34, GREY, o, 'playfair', anchor='l')
        o2 = ease(lin(t, WT('p7', '不是贪婪') - 0.2, WT('p7', '不是贪婪') + 0.2)); o3 = ease(lin(t, WT('p7', '嫉妒') - 0.2, WT('p7', '嫉妒') + 0.2))
        label(cv, '驱动这个世界的，不是贪婪，', 120, 1140, 46, WHITE, o2, 'serif_semi', anchor='l')
        label(cv, '而是嫉妒。', 120, 1210, 46, GOLD_HI, o3, 'serif_black', anchor='l')
        source(cv, '芒格 · 2022 年 Daily Journal 股东会', o, y=1330)
        credit(cv, 'munger', a, y=1380)
        return
    # p8：1956 年通用汽车 Motorama：人群围着新车
    a = ease(lin(t, T('p8') - 0.2, T('p8') + 0.3))
    tsw = WT('p8', '在乎地位') - 0.3
    clip, t0 = (CLIPS['dfd_crowd'], T('p8') - 0.2) if t < tsw else (CLIPS['dfd_car'], tsw)
    vpanel(cv, clip, t, t0, 60, 260, 1020, 980, a, zoom=1.02, z1=1.1, dur=5, edge=(0.75, 0.66, 0.50), sat=0.85, warm=0.35, contrast=1.08, gain=0.95)
    label(cv, '1956 · 通用汽车 Motorama 车展', W / 2, 1030, 32, WHITE, a, 'sans_bold')
    for i, (w_, key) in enumerate((('合作', '合作'), ('机会', '机会'), ('资源', '资源'))):
        s, o = pop(t, WT('p8', key) - 0.1, 0.4)
        chip(cv, w_, 300 + i * 240, 1150, o, GOLD, 40)
    source(cv, '影片：Design for Dreaming（1956），Prelinger Archives，公有领域', a)


def silhouette(lay, cx, cy, s=1.0):
    circle(lay, (cx, cy - 250 * s), 90 * s, 5)
    pts = [(cx - 200 * s, cy + 260 * s), (cx - 190 * s, cy - 40 * s), (cx - 120 * s, cy - 130 * s), (cx + 120 * s, cy - 130 * s),
           (cx + 190 * s, cy - 40 * s), (cx + 200 * s, cy + 260 * s)]
    poly(lay, pts, 5)


def sc_signal(cv, t):
    """p9 地位看不见 → p10 信号 → p11 装不起 → p12 孔雀开屏"""
    bg(cv, t, (0.06, 0.06, 0.09))
    if t < T('p12') - 0.15:
        a = ease(lin(t, T('p9') - 0.2, T('p9') + 0.4))
        L = layer(); silhouette(L, W / 2, 760); stroke_layer(cv, L, (0.70, 0.74, 0.82), a * 0.85, glow=0.4)
        for i, w_ in enumerate(('收入', '能力', '品位')):
            tw = WT('p9', w_); o = ease(lin(t, tw - 0.1, tw + 0.3)) * (1 - 0.85 * ease(lin(t, WT('p9', '藏在'), WT('p9', '藏在') + 0.8)))
            label(cv, w_, W / 2, 700 + i * 90, 42, GOLD_HI, o, 'sans_bold')
        k = lin(t, T('p10') - 0.1, T('p11'))
        if k > 0:
            for j in range(3):
                ph = (k * 1.6 + j / 3) % 1
                L = layer(); circle(L, (W / 2, 510), 30 + 380 * ph, 3); stroke_layer(cv, L, GOLD, (1 - ph) * 0.8 * ease(k * 4), glow=1.2)
            L = layer(); circle(L, (W / 2, 510), 18, fill=True); stroke_layer(cv, L, GOLD_HI, ease(k * 4), glow=2)
            label(cv, '信号', W / 2, 1150, 64, GOLD, ease(lin(t, WT('p10', '信号') - 0.2, WT('p10', '信号') + 0.2)) * (1 - ease(lin(t, HIT['costly'] - 0.4, HIT['costly'] - 0.15))), 'serif_black', glow=0.4)
        s, o = pop(t, HIT['costly'] - 0.1, 0.5)
        if o > 0:
            dim(cv, 1 - 0.55 * o)
            big(cv, '装不起', W / 2, 1150, 150, a=o, scale=0.9 + 0.1 * s, grad=GOLDG, glow=0.7)
        return
    # p12：孔雀开屏（实拍）
    a = ease(lin(t, T('p12') - 0.15, T('p12') + 0.3))
    vframe(cv, CLIPS['peacock'], t, T('p12') - 0.15, 560, a, 1.25, 1.35, 6, sat=1.0, warm=0.1, contrast=1.08, gain=0.95)
    for i, (w_, key) in enumerate((('又长', '又长'), ('又重', '又重'), ('招惹天敌', '天敌'))):
        s, o = pop(t, WT('p12', key) - 0.1, 0.4)
        chip(cv, w_, (250, 470, 760)[i], 300, o, WHITE, 38, (0.06, 0.06, 0.08))
    o = ease(lin(t, WT('p12', '可信') - 0.4, WT('p12', '可信')))
    label(cv, '扎哈维 1975 · 累赘原理（Handicap Principle）', W / 2, 1250, 30, GOLD_HI, o, 'sans_bold')
    credit(cv, 'v_peacock', a)


def sc_price(cv, t):
    """p14–p15 价格拆三截：成本 / 功能 / 信号；对手能复制前两截"""
    bg(cv, t, (0.07, 0.07, 0.09))
    yb, hh = 1180, 760
    segs = [(0.0, 0.38, (0.36, 0.38, 0.42), '成本', '成本'), (0.38, 0.70, (0.40, 0.52, 0.66), '功能', '功能'), (0.70, 1.0, GOLD, '信号', '信号')]
    a = ease(lin(t, T('p14') - 0.2, T('p14') + 0.3))
    label(cv, '你的品牌', 265, 345, 40, WHITE, a, 'sans_black')
    for i, (s0, s1, col, n, key) in enumerate(segs):
        s, o = pop(t, WT('p14', key) - 0.1, 0.45)
        y0 = yb - hh * s1; y1 = yb - hh * s0
        card(cv, 150, y0 + 3, 380, y1 - 3, mix(col, INK, 0.25), 0.95 * o, col, r=8, glow=1.2 if i == 2 else 0.2)
        label(cv, n, W / 2, (y0 + y1) / 2, 44, col if i == 2 else WHITE, o, 'sans_black')
    t2 = T('p15'); o2 = ease(lin(t, t2 - 0.1, t2 + 0.3))
    label(cv, '对手', 815, 345, 40, GREY, o2, 'sans_black')
    for i, (s0, s1, col, n, key) in enumerate(segs[:2]):
        s, o = pop(t, WT('p15', '复制') - 0.4 + 0.25 * i, 0.45)
        y0 = yb - hh * s1; y1 = yb - hh * s0
        card(cv, 700, y0 + 3, 930, y1 - 3, mix(col, INK, 0.35), 0.9 * o, col, r=8, glow=0.1)
    tq = WT('p15', '最难复制'); o3 = ease(lin(t, tq - 0.2, tq + 0.3))
    y0 = yb - hh; y1 = yb - hh * 0.70; L = layer()
    for x in range(700, 930, 22): line(L, (x, y0 + 3), (x + 11, y0 + 3), 3); line(L, (x, y1 - 3), (x + 11, y1 - 3), 3)
    for y in range(int(y0), int(y1), 22): line(L, (700, y), (700, y + 11), 3); line(L, (930, y), (930, y + 11), 3)
    stroke_layer(cv, L, GOLD, o3 * 0.8, glow=0.5)
    label(cv, '?', 815, (y0 + y1) / 2, 80, GOLD, o3, 'serif_black')
    label(cv, '最难复制：别人看你的那一眼', W / 2, 1260, 40, GOLD_HI, ease(lin(t, WT('p15', '那一眼') - 0.3, WT('p15', '那一眼'))), 'sans_bold')


def sc_paradox(cv, t):
    """p16 地位是相对的 → p16b–p17 信号的矛盾 → p17b 第三股力：买得起 → p18 认可 · 可及 · 区分 三角"""
    bg(cv, t, (0.07, 0.06, 0.08))
    tb = T('p16b')
    if t < tb + 0.2:
        # 地位是相对的：一人出众 → 人人都有 → 谁都没有
        a = ease(lin(t, T('p16') - 0.2, T('p16') + 0.4)) * (1 - ease(lin(t, tb - 0.3, tb + 0.1)))
        label(cv, '地位是相对的', W / 2, 300, 72, WHITE, a, 'serif_black', glow=0.2)
        k1 = ease(lin(t, WT('p16', '人人都有') - 0.2, WT('p16', '人人都有') + 0.4)); k2 = ease(lin(t, WT('p16', '谁都没有') - 0.2, WT('p16', '谁都没有') + 0.5))
        for i in range(7):
            x = 180 + i * 120; me = i == 3
            up = (1.0 if me else k1) * (1 - k2); y = 780 - 70 * up
            col = mix(mix((0.42, 0.44, 0.50), GOLD, up), (0.42, 0.44, 0.50), k2)
            L = layer(); circle(L, (x, y - 60), 26, fill=True); rect(L, x - 30, y - 24, x + 30, y + 80, r=14)
            fill(cv, L, col, a * (0.9 if (me or k1 > 0.5) and k2 < 0.5 else 0.55))
        t1, t2 = WT('p16', '人人都有'), WT('p16', '谁都没有')
        la = 1 - ease(lin(t, t1 - 0.5, t1 - 0.25)); lb = ease(lin(t, t1 - 0.25, t1)) * (1 - ease(lin(t, t2 - 0.5, t2 - 0.25))); lc = ease(lin(t, t2 - 0.25, t2))
        label(cv, '一个人出众', W / 2, 1000, 40, GOLD_HI, a * la, 'sans_bold')
        label(cv, '人人都有', W / 2, 1000, 44, GOLD, a * lb, 'sans_black')
        label(cv, '= 谁都没有', W / 2, 1000, 44, GREY, a * lc, 'sans_black')
        if t < tb - 0.25: return
    a = ease(lin(t, tb - 0.2, tb + 0.4))
    big(cv, '信号的矛盾', W / 2, 300, 84, a=a, color=WHITE, glow=0.2)
    lx, rx, cy, bx, by = 260, 820, 620, W / 2, 1070
    rng = np.random.default_rng(3); n = int(160 * ease(lin(t, WT('p17', '很多人') - 0.3, WT('p17', '知道'))))
    L = layer()
    for i in range(160):
        x = lx + rng.normal(0, 85); y = cy + rng.normal(0, 58)
        if i < n: circle(L, (x, y), 5, fill=True)
    stroke_layer(cv, L, COLD, 0.9, glow=0.6)
    o1 = ease(lin(t, WT('p17', '认出来') - 0.2, WT('p17', '认出来') + 0.3))
    label(cv, '要被认出来', lx, 880, 44, COLD, o1, 'sans_black'); label(cv, '→ 很多人知道', lx, 945, 34, WHITE, o1, 'sans_med')
    o2 = ease(lin(t, WT('p17', '特别') - 0.2, WT('p17', '特别') + 0.3))
    L = layer(); circle(L, (rx, cy), 16, fill=True); stroke_layer(cv, L, GOLD_HI, o2, glow=3.0)
    label(cv, '要显得特别', rx, 880, 44, GOLD, o2, 'sans_black'); label(cv, '→ 很少人拥有', rx, 945, 34, WHITE, o2, 'sans_med')
    # 第三股力：要做得大，就得很多人买得起
    o3 = ease(lin(t, WT('p17b', '做得大') - 0.3, WT('p17b', '做得大') + 0.3)); k3 = eout(lin(t, WT('p17b', '很多人') - 0.2, WT('p17b', '买得起', end=True)))
    L = layer()
    for i in range(45):
        r_, c_ = divmod(i, 15); x = bx - 210 + c_ * 30; y = by - 30 + r_ * 30
        if i < int(45 * k3): circle(L, (x, y), 6, fill=True)
    stroke_layer(cv, L, TEAL, o3 * 0.9, glow=0.6)
    label(cv, '要做得大', bx, 1175, 44, TEAL, o3, 'sans_black'); label(cv, '→ 很多人买得起', bx, 1240, 34, WHITE, o3, 'sans_med')
    # 三条边：认可—区分（绷紧的弦）、认可—可及、区分—可及
    th = HIT['paradox']; ten = ease(lin(t, T('p17'), th)); u = t - th
    vib = 10 * math.exp(-max(0, u) * 3) * math.sin(u * 45) if u > 0 else 3 * ten * math.sin(t * 30)
    L = layer(); pts = [(380 + (780 - 380) * i / 30, cy + vib * math.sin(math.pi * i / 30) - 40 * (1 - ten) * math.sin(math.pi * i / 30)) for i in range(31)]
    poly(L, pts, 3 + 2 * ten); stroke_layer(cv, L, mix(GOLD, RED, ten), min(o1, o2), glow=1.0 + ten)
    ke = eout(lin(t, T('p18') - 0.2, WT('p18', '互相拉扯', end=True)))
    if ke > 0:
        L = layer()
        for (x0, y0), (x1, y1) in (((330, 700), (470, 1030)), ((750, 680), (610, 1030))):
            line(L, (x0, y0), (x0 + (x1 - x0) * ke, y0 + (y1 - y0) * ke), 3 + 2 * ten)
        stroke_layer(cv, L, mix(GOLD, RED, ease(lin(t, th - 0.3, th + 0.2))), ke, glow=1.0 + ten)
    for i, (w_, col) in enumerate((('认可', COLD), ('可及', TEAL), ('区分', GOLD))):
        s, o = pop(t, WT('p18', w_) - 0.15, 0.4)
        label(cv, w_, W / 2 + (i - 1) * 200, 1345, 52, col, o, 'serif_black', glow=0.3, scale=0.9 + 0.1 * s)
    od = ease(lin(t, WT('p18', '三股力') - 0.2, WT('p18', '三股力') + 0.2))
    for x in (W / 2 - 100, W / 2 + 100): label(cv, '·', x, 1345, 52, GREY, od, 'serif_black')


# ═══════════════════════ 02 · 一把尺子 ═══════════════════════
def sc_ruler(cv, t):
    bg(cv, t, (0.07, 0.07, 0.08))
    if t < T('d2') - 0.1:
        a = ease(lin(t, T('d1') - 0.2, T('d1') + 0.4))
        big(cv, '身份', 250, CY, 110, a=a, grad=GOLDG)
        label(cv, '→', 440, CY, 80, GREY, a, 'sans_med')
        big(cv, '护城河？', 750, CY, 110, a=ease(lin(t, WT('d1', '护城河') - 0.2, WT('d1', '护城河') + 0.2)), color=WHITE, glow=0.2)
        return
    if t < T('d4') - 0.1:
        a = ease(lin(t, T('d2') - 0.2, T('d2') + 0.4))
        panel(cv, 'buffett_2015.jpg', 0, 0, W, 860, a, 1.2, 0.36, 0.33, sat=0.25, warm=0.5, contrast=1.1, gain=0.8)
        y = np.linspace(0, 1, 860, dtype=np.float32)[:, None, None]; cv[:860] *= (1 - 0.9 * np.clip((y - 0.55) / 0.45, 0, 1))
        label(cv, '沃伦 · 巴菲特', 80, 780, 46, GOLD, a, 'serif_black', anchor='l')
        label(cv, 'Warren Buffett', 80, 832, 26, GREY, a, 'corm_med', anchor='l', track=0.1)
        o = ease(lin(t, WT('d2', '评估') - 0.2, WT('d2', '评估') + 0.3))
        card(cv, 70, 900, 1010, 1290, (0.10, 0.09, 0.08), 0.92 * o, GOLD, glow=0.4)
        label(cv, '评估一家企业，最重要的是', 110, 960, 42, WHITE, o, 'serif_semi', anchor='l')
        big(cv, '定价权', 110 + text_w('评估一家企业，最重要的是', 'serif_semi', 42) + 96, 960, 52,
            a=ease(lin(t, WT('d2', '定价权') - 0.2, WT('d2', '定价权') + 0.2)), grad=GOLDG, glow=0.4)
        o2 = ease(lin(t, T('d3') - 0.1, T('d3') + 0.3))
        label(cv, '如果涨价十分之一美分，都得先祷告一番，', 110, 1060, 38, GREY, o2, 'serif_semi', anchor='l')
        label(cv, '那就是糟糕的生意。', 110, 1120, 38, (1.0, 0.65, 0.58), ease(lin(t, WT('d3', '糟糕') - 0.2, WT('d3', '糟糕') + 0.2)), 'serif_semi', anchor='l')
        source(cv, '巴菲特 · 2010 年 5 月接受美国金融危机调查委员会（FCIC）访谈', o, y=1240)
        credit(cv, 'buffett_2015', a, y=1330)
        return
    a = ease(lin(t, T('d4') - 0.1, T('d4') + 0.4))
    label(cv, '身份溢价', W / 2, 420, 56, WHITE, a, 'serif_black')
    o1 = ease(lin(t, WT('d4', '守住') - 0.2, WT('d4', '守住') + 0.2)); o2 = ease(lin(t, WT('d4', '往上提') - 0.2, WT('d4', '往上提') + 0.2))
    chip(cv, '长期守住', 380, 540, o1, TEAL, 38); chip(cv, '还能往上提', 700, 540, o2, GOLD, 38)
    o3 = ease(lin(t, WT('d4', '三道关') - 0.3, WT('d4', '三道关') + 0.2))
    gates(cv, t, o3, -1, y=860)
    label(cv, '三道关', W / 2, 1200, 64, GOLD, o3, 'serif_black', glow=0.4)


# ═══════════════════════ 03 · 三道关 ═══════════════════════
def gate_title(cv, t, i, lid, compact_after):
    """关卡标题：先居中大字，随后缩到顶部"""
    k = ease(lin(t, compact_after - 0.3, compact_after + 0.3))
    s, o = pop(t, HIT['gate_' + lid] - 0.15, 0.5)
    name = ('认得出', '仿不了', '稀释不了')[i]; num = ('第一关', '第二关', '第三关')[i]
    y = CY - 40 + (230 - (CY - 40)) * k; sz = 150 - 70 * k
    label(cv, num, W / 2, y - sz * 0.85, 44 - 12 * k, GREY, o, 'sans_bold', track=0.2)
    big(cv, name, W / 2, y + 10, sz, a=o, scale=0.9 + 0.1 * s, grad=GOLDG, glow=0.6 - 0.3 * k)


def sc_gate1(cv, t):
    """k1–k5 认得出：目光扫过；藏在家里的东西不亮；爱马仕橙"""
    bg(cv, t, (0.06, 0.07, 0.09))
    gate_title(cv, t, 0, 'k1', T('k2'))
    if t < T('k4') - 0.1:
        a = ease(lin(t, T('k2') + 0.1, T('k2') + 0.5))
        # 眼睛 + 光锥
        ex, ey = W / 2, 450
        L = layer(); poly(L, [(ex - 90, ey), (ex, ey - 46), (ex + 90, ey), (ex, ey + 46)], 4, closed=True); circle(L, (ex, ey), 22, fill=True)
        stroke_layer(cv, L, WHITE, a, glow=0.8)
        sweep = math.sin((t - T('k2')) * 1.6) * 0.5
        tx = W / 2 + 330 * sweep
        L = layer(); fpoly(L, [(ex, ey + 40), (tx - 170, 1180), (tx + 170, 1180)]); fill(cv, cv2.GaussianBlur(L, (0, 0), 18), GOLD, 0.16 * a)
        # 街上的手机与包（看得见），抽屉里的东西（看不见）
        objs = [(220, '手机'), (420, '包')]
        for x, n in objs:
            lit = 0.35 + 0.65 * math.exp(-((x - tx) / 160) ** 2)
            L = layer(); rect(L, x - 55, 980, x + 55, 1110, fill=False, w=4, r=12); stroke_layer(cv, L, GOLD, a * lit, glow=lit)
            label(cv, n, x, 1160, 30, WHITE, a * lit, 'sans_med')
        o3 = ease(lin(t, T('k3') - 0.2, T('k3') + 0.3))
        card(cv, 640, 940, 960, 1140, (0.05, 0.05, 0.06), 0.95 * o3, (0.30, 0.32, 0.36), r=8, glow=0.0)
        L = layer(); line(L, (760, 1040), (840, 1040), 5); stroke_layer(cv, L, (0.30, 0.32, 0.36), o3)
        label(cv, '藏在家里', 800, 1190, 30, GREY, o3, 'sans_med')
        label(cv, '再贵，也没人看见', W / 2, 1270, 40, GREY, ease(lin(t, WT('k3', '再贵') - 0.2, WT('k3', '再贵') + 0.3)), 'sans_bold')
        return
    if t < T('k5') - 0.1:
        a = ease(lin(t, T('k4') - 0.2, T('k4') + 0.3))
        panel(cv, 'iphone_line.jpg', 60, 380, 1020, 1100, a, 1.05, 0.5, 0.5, edge=ORANGE, sat=0.9, warm=0.1, gain=0.85)
        o = ease(lin(t, WT('k4', '一眼') - 0.2, WT('k4', '一眼') + 0.3))
        label(cv, '一眼认出：今年的新款 Pro', W / 2, 1170, 44, ORANGE, o, 'sans_black')
        label(cv, '有分析认为：一眼能认出新款，是“爱马仕橙”走红的原因之一', W / 2, 1240, 28, GREY, a, 'sans_med')
        credit(cv, 'iphone_line', a)
        return
    a = ease(lin(t, T('k5') - 0.2, T('k5') + 0.3))
    gates(cv, t, a, 0, y=700)
    label(cv, '✓ 入场券', W / 2, 1060, 56, TEAL, ease(lin(t, WT('k5', '入场券') - 0.2, WT('k5', '入场券') + 0.2)), 'sans_black')
    label(cv, '后面还有两道', W / 2, 1140, 34, GREY, a, 'sans_med')


def sc_gate2(cv, t):
    """k6–k15 仿不了：挤出来的稀缺 vs 结构性的稀缺"""
    bg(cv, t, (0.07, 0.06, 0.07))
    gate_title(cv, t, 1, 'k6', T('k7'))
    if t < T('k9') - 0.1:
        a = ease(lin(t, T('k7') - 0.2, T('k7') + 0.3))
        o1 = ease(lin(t, WT('k7', '两种') - 0.2, WT('k7', '两种') + 0.3))
        label(cv, '挤出来的稀缺', W / 4, 420, 42, (1.0, 0.62, 0.55), o1, 'sans_black')
        label(cv, '结构性的稀缺', W * 3 / 4, 420, 42, GOLD, o1 * 0.45, 'sans_black')
        L = layer(); line(L, (W / 2, 380), (W / 2, 1250), 2); stroke_layer(cv, L, GREY, o1 * 0.5)
        o2 = ease(lin(t, T('k8') - 0.2, T('k8') + 0.3))
        panel(cv, 'no_labubu.jpg', 50, 480, 515, 980, o2, 1.15, 0.5, 0.5, edge=RED, sat=0.8, warm=0.1, gain=0.85)
        chip(cv, '产能跟不上', W / 4, 1060, ease(lin(t, WT('k8', '产能') - 0.2, WT('k8', '产能') + 0.2)), RED, 34, (0.14, 0.06, 0.06))
        chip(cv, '黄牛在囤货', W / 4, 1150, ease(lin(t, WT('k8', '黄牛') - 0.2, WT('k8', '黄牛') + 0.2)), RED, 34, (0.14, 0.06, 0.06))
        label(cv, '门店告示：“我们不卖 Labubu”', W / 4, 1230, 24, GREY, o2, 'sans_med')
        L = layer(); rect(L, 565, 480, 1030, 980, fill=False, w=2); stroke_layer(cv, L, GREY, o1 * 0.35)
        label(cv, '？', W * 3 / 4, 730, 90, GREY, o1 * 0.4, 'serif_black')
        credit(cv, 'no_labubu', o2)
        return
    if t < T('k10') - 0.1:
        # 6·18 补货：二手价断崖
        a = ease(lin(t, T('k9') - 0.2, T('k9') + 0.3))
        label(cv, '2025.6.18 · LABUBU 3.0 全渠道补货', W / 2, 420, 38, WHITE, a, 'sans_black')
        x0, x1, y0, y1 = 140, 940, 560, 1150
        L = layer(); line(L, (x0, y1), (x1, y1), 2); line(L, (x0, y0), (x0, y1), 2); stroke_layer(cv, L, GREY, a * 0.6)
        tc = HIT['crash']; kk = eout(lin(t, T('k9') + 0.4, tc + 0.3))
        def Y(v): return y1 - (v / 3000) * (y1 - y0)
        hi = [(x0 + 20, Y(2600)), (x0 + 140, Y(2300)), (x0 + 260, Y(2750)), (x0 + 380, Y(2450)), (x0 + 460, Y(2500))]
        lo = [(x0 + 520, Y(800)), (x0 + 620, Y(720)), (x0 + 740, Y(690)), (x0 + 800, Y(660))]
        pts = hi + lo; m = max(2, int(len(pts) * kk))
        L = layer(); poly(L, pts[:m], 5); stroke_layer(cv, L, mix(GOLD, RED, ease(lin(t, tc - 0.4, tc))), a, glow=1.0)
        L = layer()
        for y in range(y0, y1, 24): line(L, (x0 + 490, y), (x0 + 490, y + 12), 2)
        stroke_layer(cv, L, WHITE, a * 0.5)
        label(cv, '补货前', x0 + 230, y1 + 40, 28, GREY, a, 'sans_med'); label(cv, '补货当天', x0 + 660, y1 + 40, 28, GREY, a, 'sans_med')
        label(cv, '1500~2800 元', x0 + 240, Y(2900) - 30, 32, GOLD_HI, a, 'sans_bold')
        o = ease(lin(t, tc - 0.3, tc + 0.1))
        label(cv, '650~800 元', x0 + 660, Y(1100), 32, (1.0, 0.65, 0.58), o, 'sans_bold')
        s, o2 = pop(t, tc - 0.1)
        label(cv, '当天跌去一半以上', W / 2, 1270, 46, RED, o2, 'sans_black', glow=0.3)
        source(cv, '热门款二手成交价，据媒体统计（第一财经、财联社等）', a, y=1330)
        return
    if t < T('k11') - 0.1:
        a = ease(lin(t, T('k10') - 0.2, T('k10') + 0.3))
        panel(cv, 'lafufu.jpg', 60, 380, 500, 1000, a, 1.05, 0.5, 0.45, edge=RED, sat=0.85, gain=0.85)
        label(cv, '假 Labubu（俗称 Lafufu）', 280, 1040, 26, GREY, a, 'sans_med')
        tn = WT('k10', '九成'); n = int(100 * ease(lin(t, T('k10') + 0.5, tn)))
        L1 = layer(); L2 = layer()
        for i in range(100):
            x = 590 + (i % 10) * 40; y = 450 + (i // 10) * 50
            if i < n: circle(L1 if i < 90 else L2, (x, y), 13, fill=True)
        fill(cv, L1, (0.85, 0.30, 0.27), 0.9 * a); fill(cv, L2, (0.60, 0.62, 0.66), 0.9 * a)
        o = ease(lin(t, tn - 0.2, tn + 0.3))
        stat(cv, 770, 1030, '90%', '', o, col=RED, size=110, grad=REDG)
        label(cv, '英国边境查获的假冒玩具', 770, 1130, 30, WHITE, o, 'sans_bold')
        label(cv, '是假 Labubu（23.6 万件）', 770, 1180, 30, WHITE, o, 'sans_bold')
        source(cv, '英国知识产权局（IPO）2025 年 9 月数据', a, y=1260)
        credit(cv, 'lafufu', a)
        return
    if t < T('k12') - 0.1:
        # 反身性循环：二手价↓ → 信号↓ → 想要的人↓ → 价格↓
        a = ease(lin(t, T('k11') - 0.2, T('k11') + 0.3)); c = (W / 2, 800); R = 300
        nodes = ['二手价 ↓', '信号打折', '想要的人 ↓', '更没人炒']
        spin = (t - T('k11')) * 0.25
        for i, n in enumerate(nodes):
            ang = -math.pi / 2 + i * math.pi / 2
            x, y = c[0] + R * math.cos(ang), c[1] + R * math.sin(ang)
            o = ease(lin(t, T('k11') + i * 0.5, T('k11') + i * 0.5 + 0.4)) * a
            card(cv, x - 130, y - 44, x + 130, y + 44, (0.14, 0.06, 0.06), 0.95 * o, RED, r=44, glow=0.4)
            label(cv, n, x, y, 34, WHITE, o, 'sans_bold')
        L = layer()
        for i in range(4):
            a0 = i * 90 + 26; a1 = a0 + 38
            arc(L, c, R, a0, a1, 4)
            e = math.radians(a1); e0 = math.radians(a1 - 4)
            arrow(L, (c[0] + R * math.sin(e0), c[1] - R * math.cos(e0)), (c[0] + R * math.sin(e), c[1] - R * math.cos(e)), 4, 16)
        stroke_layer(cv, L, RED, a * 0.9, glow=0.8)
        label(cv, '当二手价本身就是信号', W / 2, 1250, 40, (1.0, 0.65, 0.58), a, 'sans_bold')
        return
    # 结构性稀缺：爱马仕
    if t < T('k14') - 0.1:
        a = ease(lin(t, T('k12') - 0.2, T('k12') + 0.3))
        label(cv, '结构性的稀缺', W / 2, 390, 48, GOLD, a, 'sans_black')
        panel(cv, 'birkin2.jpg', 60, 450, 1020, 860, a, 1.1, 0.5, 0.5, edge=GOLD, sat=0.95, warm=0.45, gain=0.85)
        t1 = WT('k13', '十八个月'); o1 = ease(lin(t, t1 - 0.4, t1))
        stat(cv, 300, 990, '18', '个月+', o1, size=110, usize=40, grad=GOLDG)
        label(cv, '工匠入职培训', 300, 1080, 30, WHITE, o1, 'sans_med')
        t2 = WT('k13', '工坊'); o2 = ease(lin(t, t2 - 0.2, t2 + 0.3))
        label(cv, '新皮具工坊', 780, 920, 32, WHITE, o2, 'sans_bold')
        for i, (yr, place, key) in enumerate((('2026', 'Loupes', '一座'), ('2027', 'Charleville', '一座'), ('2028', 'Colombelles', '计划'), ('2030', 'Les Andelys', '二零三零'))):
            tt = t2 + 0.35 * i if key != '二零三零' else WT('k13', '二零三零') - 0.2
            oo = ease(lin(t, tt, tt + 0.3)) * o2
            label(cv, yr, 640, 985 + i * 62, 34, GOLD_HI, oo, 'oswald', anchor='l')
            label(cv, place, 740, 985 + i * 62, 28, GREY, oo, 'corm_med', anchor='l')
        source(cv, '爱马仕官网（École Hermès des savoir-faire）、2025 年度业绩公告', a, y=1270)
        credit(cv, 'birkin2', a, y=1320)
        return
    if t < T('k15') - 0.1:
        a = ease(lin(t, T('k14') - 0.2, T('k14') + 0.3))
        panel(cv, 'hermes_paris.jpg', 0, 0, W, H, a, 1.2, 0.5, 0.5, sat=0.6, warm=0.4, gain=0.3)
        card(cv, 80, 560, 1000, 1080, (0.10, 0.09, 0.08), 0.92 * a, GOLD, glow=0.5)
        label(cv, '“Scarcity is not a goal for us.”', W / 2, 650, 44, GREY, a, 'playfair')
        o = ease(lin(t, WT('k14', '稀缺') - 0.2, WT('k14', '稀缺') + 0.3))
        big(cv, '稀缺，从来不是', W / 2, 790, 72, a=o, color=WHITE, glow=0.1)
        big(cv, '我们的目标', W / 2, 900, 72, a=ease(lin(t, WT('k14', '目标') - 0.3, WT('k14', '目标'))), grad=GOLDG, glow=0.5)
        label(cv, '— 纪尧姆 · 德塞纳（爱马仕执行副总裁）· The National，2025.10', W / 2, 1020, 26, GREY, a, 'sans_med')
        credit(cv, 'hermes_paris', a)
        return
    a = ease(lin(t, T('k15') - 0.2, T('k15') + 0.3))
    big(cv, '稀缺只是结果', W / 2, 420, 84, a=a, grad=GOLDG, glow=0.4)
    o1 = ease(lin(t, WT('k15', '想多做') - 0.2, WT('k15', '想多做') + 0.2)); o2 = ease(lin(t, WT('k15', '想仿') - 0.2, WT('k15', '想仿') + 0.2))
    chip(cv, '想多做：快不起来', W / 2, 600, o1, GOLD, 40); chip(cv, '想仿：买不来时间', W / 2, 720, o2, GOLD, 40)
    kk = eout(lin(t, WT('k15', '两百年') - 1.2, WT('k15', '时间', end=True)))
    L = layer(); line(L, (140, 980), (140 + 800 * kk, 980), 5); stroke_layer(cv, L, GOLD, a * o2, glow=1.4)
    label(cv, '1837', 140, 1040, 40, GOLD_HI, o2, 'oswald'); label(cv, '2026', 940, 1040, 40, WHITE, o2 * ease(kk * 3 - 2), 'oswald')
    label(cv, '将近两百年', W / 2, 920, 40, WHITE, o2 * ease(kk * 2 - 1), 'sans_bold')


def sc_gate3(cv, t):
    """k16–k23 稀释不了：倒 U、分层的门、会员卡、山姆选品风波"""
    bg(cv, t, (0.06, 0.07, 0.08))
    gate_title(cv, t, 2, 'k16', T('k17'))
    if t < T('k19') - 0.1:
        a = ease(lin(t, T('k17') - 0.2, T('k17') + 0.3))
        x0, x1, y0, y1 = 140, 940, 470, 1110
        L = layer(); line(L, (x0, y1), (x1, y1), 2); line(L, (x0, y0), (x0, y1), 2); stroke_layer(cv, L, GREY, a * 0.6)
        label(cv, '用户越来越多 →', x1, y1 + 40, 28, GREY, a, 'sans_med', anchor='r')
        k = eout(lin(t, T('k17') + 0.2, WT('k17', '越少', end=True)))
        def curve(f):
            return [(x0 + (x1 - x0) * u, y1 - (y1 - y0) * f(u)) for u in np.linspace(0, k, 40)]
        rec = curve(lambda u: 0.05 + 0.85 * (1 - math.exp(-3.2 * u)))
        spc = curve(lambda u: 0.92 * math.exp(-2.2 * u) + 0.03)
        val = curve(lambda u: 0.05 + 0.85 * (1 - math.exp(-3.2 * u)) * (0.92 * math.exp(-2.2 * u) + 0.03) * 2.4)
        if len(rec) > 1:
            for pts, col, aa in ((rec, COLD, a * 0.8), (spc, RED, a * 0.8)):
                L = layer(); poly(L, pts, 3); stroke_layer(cv, L, col, aa, glow=0.4)
        ov = ease(lin(t, T('k18') - 0.2, T('k18') + 0.4))
        if len(val) > 1 and ov > 0:
            L = layer(); poly(L, val, 6); stroke_layer(cv, L, GOLD, ov, glow=1.4)
            label(cv, '最佳区间', x0 + (x1 - x0) * 0.33, y0 + 10, 34, GOLD_HI, ease(lin(t, WT('k18', '先增强'), WT('k18', '先增强') + 0.4)), 'sans_black')
        lg = [('— 认得出的人', COLD, a), ('— 特别感', RED, a), ('— 信号价值', GOLD, ov)]
        for i, (s_, col, aa) in enumerate(lg): label(cv, s_, 170 + i * 270, 1230, 30, col, aa, 'sans_bold', anchor='l')
        label(cv, '理论示意', 940, 470, 24, GREY, a, 'sans_light', anchor='r')
        # k18b：多一个用户，下一个人是更想要，还是更不想要？
        oq = ease(lin(t, T('k18b') - 0.2, T('k18b') + 0.3))
        label(cv, '投资者该问：多一个用户，下一个人……', W / 2, 1330, 34, WHITE, oq, 'sans_bold')
        def V_(u): return 0.05 + 0.85 * (1 - math.exp(-3.2 * u)) * (0.92 * math.exp(-2.2 * u) + 0.03) * 2.4
        for u0, w_, col, dy in ((0.10, '更想要 ↑', GOLD_HI, -70), (0.80, '更不想要 ↓', (1.0, 0.62, 0.55), 62)):
            tw = WT('k18b', w_[:-2]); s_, o = pop(t, tw - 0.15, 0.4)
            label(cv, w_, x0 + (x1 - x0) * u0, y1 - (y1 - y0) * V_(u0) + dy, 36, col, o, 'sans_black', scale=0.9 + 0.1 * s_)
        return
    if t < T('k20') - 0.1:
        a = ease(lin(t, T('k19') - 0.2, T('k19') + 0.3))
        panel(cv, 'hermes_lutetia.jpg', 0, 0, W, H, a, 1.15, 0.5, 0.5, sat=0.7, warm=0.4, gain=0.3)
        tiers = [('最受追捧的包', '往往要等', WT('k19', '最受追捧'), 420, GOLD), ('丝巾 · 香水', '很多人买得到', WT('k19', '丝巾'), 820, WHITE)]
        for n, d, ts, w_, col in tiers:
            s, o = pop(t, ts - 0.15, 0.45); y = 620 if col == GOLD else 1000
            card(cv, W / 2 - w_ / 2, y - 120, W / 2 + w_ / 2, y + 120, (0.10, 0.09, 0.08), 0.92 * o, col, r=12, glow=0.8 if col == GOLD else 0.2)
            label(cv, n, W / 2, y - 30, 44, col, o, 'sans_black'); label(cv, d, W / 2, y + 40, 32, GREY, o, 'sans_med')
        label(cv, '把门分成几层', W / 2, 400, 48, WHITE, a, 'serif_black')
        o = ease(lin(t, T('k19b') - 0.2, T('k19b') + 0.3))
        label(cv, '一条路：产量跟着工匠走 · 长得慢 · 门槛一直在', W / 2, 1250, 32, GOLD_HI, o, 'sans_bold')
        credit(cv, 'hermes_lutetia', a)
        return
    if t < T('k21') - 0.1:
        # 另一条路：先让很多人买得起，再在里面留出层次
        a = ease(lin(t, T('k20') - 0.2, T('k20') + 0.3))
        label(cv, '另一条路', W / 2, 390, 52, WHITE, a, 'serif_black')
        label(cv, '先让很多人买得起，再在里面留出层次', W / 2, 455, 32, GREY, a, 'sans_med')
        o1 = ease(lin(t, WT('k20', '苹果') - 0.2, WT('k20', '苹果') + 0.3)); o2 = ease(lin(t, WT('k20', '山姆') - 0.2, WT('k20', '山姆') + 0.3))
        panel(cv, 'iphone_line.jpg', 60, 510, 1020, 880, o1, 1.05, 0.5, 0.5, edge=ORANGE, sat=0.9, warm=0.1, gain=0.75)
        panel(cv, 'sams_sz.jpg', 60, 920, 1020, 1290, o2, 1.35, 0.29, 0.40, edge=GOLD, sat=0.75, warm=0.2, gain=0.55)
        s, o = pop(t, WT('k20b', 'Pro') - 0.15, 0.45)
        chip(cv, 'Pro ｜ 标准版', W / 2, 830, o, ORANGE, 36, (0.10, 0.07, 0.05))
        s, o = pop(t, WT('k20b', '会员卡') - 0.15, 0.45)
        chip(cv, '会员卡 · 260 元 / 年', 330, 1240, o, GOLD, 32, (0.12, 0.10, 0.06))
        s, o = pop(t, WT('k20b', '货架') - 0.15, 0.45)
        chip(cv, '挑过的货架', 790, 1240, o, GOLD, 32, (0.12, 0.10, 0.06))
        text(cv, '图：%s · %s ／ %s · %s' % (CREDIT['iphone_line']['artist'][:16], CREDIT['iphone_line']['license'],
                                         CREDIT['sams_sz']['artist'][:16], CREDIT['sams_sz']['license']), 56, 1335, 'sans_light', 22, GREY, anchor='l', alpha=0.75 * a)
        return
    if t < T('k23') - 0.1:
        a = ease(lin(t, T('k21') - 0.2, T('k21') + 0.3))
        label(cv, '2025 年 7 月 · 山姆选品风波', W / 2, 400, 42, WHITE, a, 'sans_black')
        swap = ease(lin(t, WT('k21', '换上') - 0.3, WT('k21', '零食', end=True)))
        for i in range(24):
            r_, c_ = divmod(i, 6); x = 180 + c_ * 144; y = 520 + r_ * 120
            gone = (i * 7) % 24 < 22 * swap and i % 3 != 1
            col = (0.55, 0.57, 0.60) if gone else GOLD
            card(cv, x - 55, y - 45, x + 55, y + 45, mix(col, INK, 0.6), 0.92 * a, col, r=8, glow=0.0 if gone else 0.4)
        label(cv, '■ 口碑商品', 330, 1050, 30, GOLD, a, 'sans_bold')
        label(cv, '■ 到处都买得到', 740, 1050, 30, GREY, a * swap, 'sans_bold')
        if t > T('k22') - 0.2:
            o = ease(lin(t, T('k22') - 0.2, T('k22') + 0.1))
            dim(cv, 1 - 0.85 * o)
            chip(cv, '热搜 · 部分会员称要退卡', W / 2, 700, ease(lin(t, T('k22') + 0.1, T('k22') + 0.4)), RED, 40, (0.16, 0.06, 0.06))
            o2 = ease(lin(t, WT('k22', '山姆下架') - 0.2, WT('k22', '山姆下架') + 0.3))
            card(cv, 110, 820, 970, 1100, (0.10, 0.10, 0.12), 0.95 * o2, WHITE, glow=0.2)
            label(cv, '山姆：争议商品已下架', W / 2, 890, 38, WHITE, o2, 'sans_bold')
            label(cv, '“已关注到社交网络上的讨论，', W / 2, 965, 32, GREY, o2, 'serif_semi')
            label(cv, '将纳入后续选品策略考量”', W / 2, 1025, 32, GREY, o2, 'serif_semi')
        source(cv, '36 氪、澎湃新闻、钛媒体等 2025 年 7 月报道', a, y=1260)
        return
    a = ease(lin(t, T('k23') - 0.2, T('k23') + 0.3))
    panel(cv, 'sams_bj.jpg', 0, 0, W, H, a, 1.2, 0.5, 0.5, sat=0.6, warm=0.3, gain=0.28)
    fo = 1 - ease(lin(t, T('k23b') - 0.45, T('k23b') - 0.1))      # 先让“挑过的生活”淡出，再推门
    s, o = pop(t, WT('k23', '这张卡') - 0.2, 0.5)
    card(cv, 240, 560, 840, 900, (0.16, 0.13, 0.08), 0.95 * o * fo, GOLD, r=24, glow=1.2)
    big(cv, '“挑过的生活”', W / 2, 730, 66, a=ease(lin(t, WT('k23', '挑过') - 0.3, WT('k23', '挑过'))) * fo, grad=GOLDG, glow=0.5)
    label(cv, '不只是一块派', W / 2, 1020, 40, WHITE, ease(lin(t, WT('k23', '一块派') - 0.2, WT('k23', '一块派') + 0.2)) * fo, 'sans_bold')
    door(cv, t, W / 2, 800, 220, 380, ease(lin(t, T('k23b') - 0.15, T('k23b') + 0.35)), 'k23b')
    credit(cv, 'sams_bj', a)


def door(cv, t, cx, cy, w, h, a, lid, top=None, bot=None):
    """一扇门：人流从两侧进门，门里的金光随人数增加而变淡（每多一批人进门，门里人的身份就淡一点）"""
    if a <= 0.003: return
    dim(cv, 1 - 0.55 * a)
    t0 = T(lid); k = ease(lin(t, t0 + 0.3, SE(lid)))
    glow_ = 1.0 - 0.75 * k
    L = layer(); rect(L, cx - w / 2 + 10, cy - h / 2 + 10, cx + w / 2 - 10, cy + h / 2); fill(cv, cv2.GaussianBlur(L, (0, 0), 14), GOLD, 0.55 * a * glow_)
    L = layer(); rect(L, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, fill=False, w=5, r=6); stroke_layer(cv, L, GOLD, a, glow=1.0 * glow_ + 0.2)
    rr = np.random.default_rng(17); L = layer()
    for i in range(60):
        side = -1 if i % 2 else 1; ph = rr.random(); sp = 0.25 + rr.random() * 0.25
        u = (max(0.0, t - t0) * sp + ph) % 1.0
        if i / 60 > 0.25 + 0.75 * k: continue
        x = cx + side * (w / 2 + 340 * (1 - u)); y = cy + h / 2 - 30 - 40 * rr.random()
        circle(L, (x, y), 9, fill=True)
    fill(cv, L, (0.70, 0.72, 0.78), 0.85 * a)
    label(cv, top or '这条路：市场更大，也更难走', cx, cy - h / 2 - 90, 44, WHITE, a, 'serif_black')
    label(cv, bot or '每多一批人进门，门里人的身份就淡一点', cx, cy + h / 2 + 80, 34, (1.0, 0.70, 0.62), ease(lin(t, WT(lid, '稀释') - 0.3, WT(lid, '稀释') + 0.2)), 'sans_bold')


def ring_stat(cv, c, r, frac, num, lab, a, col=GOLD):
    L = layer(); circle(L, c, r, 14); stroke_layer(cv, L, (0.20, 0.21, 0.24), a)
    if frac > 0:
        L = layer(); arc(L, c, r, 0, 360 * frac, 14); stroke_layer(cv, L, col, a, glow=1.0)
    stat(cv, c[0], c[1] - 10, num, '', a, size=74, grad=GOLDG if col == GOLD else None, col=col)
    label(cv, lab, c[0], c[1] + r + 50, 32, WHITE, a, 'sans_bold')


def sc_math(cv, t):
    """m1–m4 最后一道算术：身份 → 利润"""
    bg(cv, t, (0.08, 0.07, 0.06))
    if t < T('m2') - 0.1:
        a = ease(lin(t, T('m1') - 0.2, T('m1') + 0.3))
        gates(cv, t, a, -1, y=420, done=(0, 1, 2))
        o = ease(lin(t, WT('m1', '算术') - 0.2, WT('m1', '算术') + 0.3))
        big(cv, '身份', 330, 900, 100, a=o, grad=GOLDG); label(cv, '→', W / 2, 900, 70, GREY, o, 'sans_med')
        big(cv, '利润？', 760, 900, 100, a=ease(lin(t, WT('m1', '利润') - 0.2, WT('m1', '利润') + 0.2)), color=WHITE, glow=0.2)
        label(cv, '最后一道算术', W / 2, 1100, 44, GOLD, o, 'serif_black')
        return
    if t < T('m3') - 0.1:
        a = ease(lin(t, T('m2') - 0.2, T('m2') + 0.3))
        big(cv, 'HERMÈS', W / 2, 360, 90, a=a, fname='playfair', grad=GOLDG, track=0.12)
        label(cv, '把身份变成价格 · 2025 年', W / 2, 460, 36, WHITE, a, 'sans_bold')
        f1 = 0.711 * eout(lin(t, WT('m2', '七十一') - 0.5, WT('m2', '七十一') + 0.3)); f2 = 0.41 * eout(lin(t, WT('m2', '四十一') - 0.5, WT('m2', '四十一') + 0.3))
        ring_stat(cv, (300, 800), 170, f1, '%d%%' % round(f1 * 100), '毛利率', ease(lin(t, WT('m2', '毛利率') - 0.3, WT('m2', '毛利率'))))
        ring_stat(cv, (780, 800), 170, f2, '%d%%' % round(f2 * 100), '经营利润率', ease(lin(t, WT('m2', '经营利润率') - 0.3, WT('m2', '经营利润率'))))
        source(cv, '爱马仕 2025 年度业绩：毛利率 71.1%，经常性经营利润率 41%', a, y=1250)
        return
    if t < T('m3b') - 0.1:
        a = ease(lin(t, T('m3') - 0.2, T('m3') + 0.3))
        apple_share(cv, t, a, W / 2, 360, 460, 120, 960, (700, 920), 1250)
        return
    if t < T('m4') - 0.1:
        why_more(cv, t, ease(lin(t, T('m3b') - 0.2, T('m3b') + 0.3)), W / 2, 420, 620, 240, 700, 900, 1040)
        return
    if t > T('m5') - 0.3:
        acquire(cv, t, ease(lin(t, T('m5') - 0.3, T('m5') + 0.2)), (300, 780), 520, 1000)
        return
    a = ease(lin(t, T('m4') - 0.2, T('m4') + 0.3))
    label(cv, '爱马仕', 260, 490, 48, GOLD, a, 'serif_black'); label(cv, '苹果', 820, 490, 48, (0.85, 0.88, 0.95), a, 'serif_black')
    o1 = ease(lin(t, WT('m4', '少数人') - 0.2, WT('m4', '少数人') + 0.3)); o2 = ease(lin(t, WT('m4', '很多人') - 0.2, WT('m4', '很多人') + 0.3))
    label(cv, '少数人 · 付很高的价', 260, 548, 30, WHITE, o1, 'sans_med'); label(cv, '很多人 · 都多付一些', 820, 548, 30, WHITE, o2, 'sans_med')
    k = eout(lin(t, WT('m4', '少数人') - 0.2, WT('m4', '多付一些', end=True)))
    L = layer(); line(L, (260, 600), (260 + (540 - 260) * k, 600 + 260 * k), 5); line(L, (820, 600), (820 + (540 - 820) * k, 600 + 260 * k), 5)
    stroke_layer(cv, L, GOLD, a, glow=1.0)
    s, o = pop(t, WT('m4', '多付一些', end=True) - 0.1, 0.5)
    chip(cv, '定价权', W / 2, 920, o, GOLD, 54, (0.16, 0.13, 0.08))
    o2 = ease(lin(t, WT('m4', '热闹') - 0.3, WT('m4', '热闹')))
    label(cv, '认同留不住钱  =  热闹  ≠  护城河', W / 2, 1150, 42, (1.0, 0.65, 0.58), o2, 'sans_bold')


def apple_share(cv, t, a, cx, y_title, y_sub, x0, x1, ys, y_src):
    """m3 苹果：2025 年第四季度，出货量约占全球四分之一，收入却将近六成（Counterpoint）"""
    if a <= 0.003: return
    big(cv, 'iPhone', cx, y_title, 96, a=a, fname='playfair', color=(0.92, 0.93, 0.96), glow=0.2)
    label(cv, '另一条路 · 2025 年第四季度 · 全球手机', cx, y_sub, 34, WHITE, a, 'sans_bold')
    for (name, frac, col, key, val), y in zip((('出货量份额', 0.25, COLD, '四分之一', '≈ 25%'), ('收入份额', 0.59, GOLD, '六成', '≈ 59%')), ys):
        tk = WT('m3', key); k = eout(lin(t, tk - 0.6, tk + 0.3)); o = ease(lin(t, tk - 0.8, tk - 0.4)) * a
        label(cv, name, x0, y - 62, 36, WHITE, o, 'sans_bold', anchor='l')
        L = layer(); rect(L, x0, y - 24, x1, y + 24, r=24); fill(cv, L, (0.20, 0.21, 0.24), 0.9 * o)
        if k > 0.01:
            L = layer(); rect(L, x0, y - 24, x0 + (x1 - x0) * frac * k, y + 24, r=24); fill(cv, L, col, 0.95 * o)
        label(cv, val, x1, y - 62, 44, col, ease(lin(t, tk - 0.1, tk + 0.3)) * a, 'oswald', anchor='r')
    source(cv, 'Counterpoint 2025 Q4：出货量份额约 25%（IDC 24.2%），收入份额约 59%', a, y=y_src)


def why_more(cv, t, a, cx, y_title, y_chips, dx, y_note, y_big, y_end):
    """m3b 多出来的钱：产品、生态、身份（只是其中一份）× 一年两亿多部 = 另一种定价权"""
    if a <= 0.003: return
    label(cv, '多出来的钱，为什么付？', cx, y_title, 48, WHITE, a, 'serif_black')
    for i, (w_, col, key, nth) in enumerate((('产品', (0.62, 0.66, 0.74), '产品', 0), ('生态', (0.62, 0.66, 0.74), '生态', 0), ('身份', GOLD, '身份', 1))):
        s, o = pop(t, WT('m3b', key, nth=nth) - 0.15, 0.45)
        chip(cv, w_, cx + (i - 1) * dx, y_chips, o * a, col, 44, (0.10, 0.10, 0.12) if i < 2 else (0.16, 0.13, 0.08))
    label(cv, '只是其中一份', cx + dx, y_note, 30, GOLD_HI, ease(lin(t, WT('m3b', '其中一份') - 0.2, WT('m3b', '其中一份') + 0.2)) * a, 'sans_med')
    s, o = pop(t, WT('m3b', '两亿多部') - 0.2, 0.5)
    big(cv, '× 一年两亿多部', cx, y_big, 76, a=o * a, scale=0.92 + 0.08 * s, color=WHITE, glow=0.2)
    label(cv, '= 另一种定价权', cx, y_end, 50, GOLD, ease(lin(t, WT('m3b', '定价权') - 0.3, WT('m3b', '定价权') + 0.1)) * a, 'serif_black', glow=0.3)


def acquire(cv, t, a, xs, y_head, y_floor):
    """m5 认同是怎么来的：左边口碑（用户自己长出来，几乎不花钱），右边广告 / 补贴（每来一个用户都掉一枚硬币）"""
    if a <= 0.003: return
    t0 = T('m5'); tl_ = WT('m5', '口碑'); tr_ = WT('m5', '广告')
    label(cv, '认同是怎么来的？', W / 2, y_head - 130, 56, WHITE, a, 'serif_black')
    xl, xr = xs; rr = np.random.default_rng(5)
    for side, (x, head, col, ts) in enumerate(((xl, '口碑', TEAL, tl_), (xr, '广告 · 补贴', RED, tr_))):
        o = ease(lin(t, ts - 0.2, ts + 0.3)) * a
        label(cv, head, x, y_head, 46, col, o, 'sans_black')
        n = int(24 * ease(lin(t, ts + 0.2, SE('m5'))))
        L = layer(); Lc = layer()
        for i in range(24):
            px = x - 150 + (i % 6) * 60; py = y_head + 110 + (i // 6) * 64
            if i < n:
                circle(L, (px, py - 12), 12, fill=True); rect(L, px - 16, py + 2, px + 16, py + 30, r=8)
                if side == 1:
                    circle(Lc, (px + 22, py - 30), 9, fill=True)
        fill(cv, L, (0.78, 0.80, 0.86), 0.9 * o)
        if side == 1: stroke_layer(cv, Lc, GOLD_HI, 0.95 * o, glow=1.0)
        lab = '新用户几乎不花钱' if side == 0 else '每个新用户，再花一次钱'
        oo = ease(lin(t, (WT('m5', '几乎不花钱') if side == 0 else WT('m5', '再花一次钱')) - 0.3, (WT('m5', '几乎不花钱') if side == 0 else WT('m5', '再花一次钱')) + 0.2)) * a
        label(cv, lab, x, y_floor, 32, col, oo, 'sans_bold')
    L = layer(); line(L, (W / 2, y_head - 40), (W / 2, y_floor + 30), 2); stroke_layer(cv, L, GREY, 0.4 * a)


# ═══════════════════════ 04 · 中国考题 ═══════════════════════
def scorecard(cv, t, x0, y0, rows, a):
    """体检表：rows=[(关卡, 标记, 说明, 出现时刻)]"""
    card(cv, x0, y0, x0 + 960, y0 + 60 + 104 * len(rows), (0.08, 0.09, 0.11), 0.92 * a, GOLD, glow=0.4)
    for i, (n, mk, note_, ts) in enumerate(rows):
        y = y0 + 82 + i * 104; o = ease(lin(t, ts - 0.2, ts + 0.3)) * a
        label(cv, n, x0 + 36, y, 36, WHITE, a, 'sans_black', anchor='l')
        if o > 0:
            check(cv, x0 + 240, y, mk, o, 46)
            label(cv, note_, x0 + 290, y, 28, GREY, o, 'sans_med', anchor='l')


def sc_china(cv, t):
    bg(cv, t, (0.09, 0.06, 0.05))
    if t < T('g2') - 0.1:
        a = ease(lin(t, T('g1') - 0.2, T('g1') + 0.3))
        big(cv, '中国考题', W / 2, 520, 110, a=a, grad=GOLDG)
        gates(cv, t, a * 0.9, -1, y=780)
        label(cv, '老铺黄金  ·  泡泡玛特', W / 2, 1120, 44, WHITE, ease(lin(t, WT('g1', '两家') - 0.2, WT('g1', '两家') + 0.3)), 'sans_black')
        return
    if t < T('g6') - 0.1:
        a = ease(lin(t, T('g2') - 0.2, T('g2') + 0.3))
        panel(cv, 'gold_bracelet.jpg', 0, 0, W, H, a, 1.3, 0.5, 0.5, sat=0.8, warm=0.4, gain=0.22)
        big(cv, '老铺黄金', W / 2, 300, 88, a=a, grad=GOLDG)
        rows = [('认得出', '✓', '商场门口排过长队', WT('g2', '认得出')),
                ('仿不了', '?', '32 家商场里 ≥19 家也有古法金对手', WT('g3', '三十二')),
                ('稀释不了', '?', '11 月促销，手镯立减近 2 万元', WT('g4', '手镯')),
                ('利润', '✓', '2026 上半年利润 +88%', WT('g5', '八成'))]
        scorecard(cv, t, 60, 400, rows, a)
        # 32 家商场：19 家亮起第二个品牌
        o = ease(lin(t, WT('g3', '三十二') - 0.2, WT('g3', '三十二') + 0.3)); k = ease(lin(t, WT('g3', '十九') - 0.4, WT('g3', '十九') + 0.4))
        for i in range(32):
            r_, c_ = divmod(i, 16); x = 120 + c_ * 56; y = 1000 + r_ * 64
            hit_ = i % 32 in (0, 1, 3, 4, 6, 7, 9, 10, 12, 13, 15, 17, 18, 20, 22, 24, 26, 28, 30)
            col = RED if hit_ and k > 0.5 else GOLD
            L = layer(); rect(L, x - 20, y - 22, x + 20, y + 22, r=4); fill(cv, L, col, o * (0.85 if col == RED else 0.6))
        label(cv, '■ 进驻商场  ■ 同场有其他古法金品牌', W / 2, 1150, 26, GREY, o, 'sans_med')
        source(cv, '界面新闻（截至 2026.04）；21 世纪经济报道（2026.11）；公司 2026 中期报告', a, y=1240)
        return
    if t < T('g7') - 0.1:
        a = ease(lin(t, T('g6') - 0.2, T('g6') + 0.3))
        panel(cv, 'nyc_store.jpg', 0, 0, W, H, a, 1.3, 0.5, 0.5, sat=0.5, warm=0.1, gain=0.22)
        big(cv, '泡泡玛特', W / 2, 300, 88, a=a, color=(1.0, 0.75, 0.66), glow=0.2)
        rows = [('认得出', '✓', '全球门店排长队', T('g6') + 0.2),
                ('仿不了', '?', '补货当天，二手价腰斩', WT('g6', '稀缺')),
                ('稀释不了', '?', '三季度收入同比 −45%~−50%', WT('g6', '三季度'))]
        scorecard(cv, t, 60, 400, rows, a)
        o = ease(lin(t, WT('g6', '公司') - 0.2, WT('g6', '公司') + 0.3))
        card(cv, 60, 840, 1020, 1060, (0.10, 0.10, 0.12), 0.95 * o, WHITE, glow=0.2)
        label(cv, '公司的解释', 100, 895, 30, GREY, o, 'sans_bold', anchor='l')
        label(cv, '去年同期基数太高；正在优化海外库存', 100, 970, 36, WHITE, o, 'sans_bold', anchor='l')
        label(cv, '预计中国市场全年仍正增长', 100, 1022, 28, GREY, o, 'sans_med', anchor='l')
        source(cv, '泡泡玛特 2026 年第三季度经营数据公告（2026.10.27）', a, y=1240)
        credit(cv, 'nyc_store', a, y=1300)
        return
    if t < T('g9') - 0.1:
        a = ease(lin(t, T('g7') - 0.2, T('g7') + 0.3))
        L = layer(); rect(L, 60, 180, 1020, 760, r=16); fill(cv, L, (0.14, 0.10, 0.10), 0.95 * a)
        big(cv, '段', 300, 470, 300, a=a * 0.9, color=(0.85, 0.40, 0.32), fname='serif_black', glow=0.3)
        label(cv, '段永平', 680, 400, 56, (1.0, 0.60, 0.50), a, 'serif_black')
        label(cv, 'Duan Yongping', 680, 460, 28, GREY, a, 'corm_med', track=0.1)
        # 股价下行线 + 一支逆向的金色箭头
        L = layer(); pts = [(560 + 400 * u, 560 + 140 * u ** 0.8 + 18 * math.sin(u * 14)) for u in np.linspace(0, 1, 30)]
        poly(L, pts, 3); stroke_layer(cv, L, RED, a * 0.8, glow=0.4)
        kk = eout(lin(t, WT('g7', '买下') - 0.2, WT('g7', '股份', end=True)))
        L = layer(); arrow(L, (760, 720), (760 + 120 * kk, 720 - 150 * kk), 5, 20); stroke_layer(cv, L, GOLD, a * ease(kk * 3), glow=1.2)
        o1 = ease(lin(t, WT('g7', '百分之五') - 0.3, WT('g7', '百分之五') + 0.2))
        label(cv, '2026.05 举牌 5.69% → 7 月增至 7.65%', W / 2, 850, 36, GOLD_HI, o1, 'sans_bold')
        o2 = ease(lin(t, WT('g7', '十年') - 0.3, WT('g7', '十年') + 0.2))
        label(cv, '“我猜 10 年内大概率是不会卖的。”', W / 2, 950, 42, WHITE, o2, 'serif_semi')
        o3 = ease(lin(t, T('g8') - 0.2, T('g8') + 0.3))
        label(cv, '看好的是：创始人王宁', W / 2, 1060, 38, WHITE, o3, 'sans_bold')
        label(cv, '“没想到盈利如此之好”', W / 2, 1120, 34, GREY, ease(lin(t, WT('g8', '没想到') - 0.2, WT('g8', '没想到') + 0.2)), 'serif_semi')
        source(cv, '港交所权益披露；财联社、上海证券报、中证网报道', a, y=1240)
        return
    a = ease(lin(t, T('g9') - 0.2, T('g9') + 0.3))
    o1 = ease(lin(t, WT('g9', '热度') - 0.2, WT('g9', '热度') + 0.3)) * (1 - 0.6 * ease(lin(t, WT('g9', '一家公司') - 0.2, WT('g9', '一家公司') + 0.3)))
    label(cv, '一只玩偶的热度，会退', W / 2, 420, 48, GREY, o1, 'sans_bold')
    o2 = ease(lin(t, WT('g9', '一次又一次') - 0.2, WT('g9', '一次又一次') + 0.3))
    for i in range(5):
        oo = ease(lin(t, WT('g9', '一次又一次') + i * 0.18, WT('g9', '一次又一次') + i * 0.18 + 0.3))
        L = layer(); circle(L, (220 + i * 160, 640), 50, 4); stroke_layer(cv, L, GOLD, oo * 0.9, glow=1.0)
        label(cv, 'IP', 220 + i * 160, 640, 30, GOLD_HI, oo, 'oswald')
    label(cv, '一次又一次，造出让人想拥有的身份', W / 2, 780, 40, WHITE, o2, 'sans_bold')
    blink = 0.6 + 0.4 * math.sin(t * 5)
    s, o3 = pop(t, WT('g9', '答案') - 0.2, 0.5)
    check(cv, W / 2, 960, '?', o3 * blink, 90)
    big(cv, '答案，交给时间', W / 2, 1150, 76, a=o3, grad=GOLDG, glow=0.5)


# ═══════════════════════ 05 · 失守 ═══════════════════════
class Fireworks:
    def __init__(self, seed=11):
        r = np.random.default_rng(seed); self.b = []
        for i in range(26):
            self.b.append((r.uniform(180, 900), r.uniform(540, 760), i * 0.42 + r.uniform(0, 0.25), r.uniform(0, 6.28)))
        self.dirs = r.normal(0, 1, (140, 2)); self.dirs /= np.linalg.norm(self.dirs, axis=1, keepdims=True); self.sp = r.uniform(0.55, 1.0, 140)

    def draw(self, cv, u, a):
        L = layer()
        for x, y, d, ph in self.b:
            v = u - d
            if v < 0 or v > 2.2: continue
            rr = 200 * eout(v / 1.2); fade_ = (1 - v / 2.2) ** 1.5
            for (dx, dy), sp in zip(self.dirs, self.sp):
                px = x + dx * rr * sp; py = y + dy * rr * sp + 25 * v * v
                circle(L, (px, py), 3.2, v=fade_, fill=True)
        stroke_layer(cv, L, (1.0, 0.74, 0.46), a, glow=2.4, add=True)


FW = Fireworks()


def sc_betray(cv, t):
    bg(cv, t, (0.07, 0.05, 0.06))
    if t < T('q2') - 0.1:
        a = ease(lin(t, T('q1') - 0.2, T('q1') + 0.3))
        label(cv, '还有一种失守，比什么都快', W / 2, 560, 44, GREY, a, 'sans_bold')
        s, o = pop(t, WT('q1', '背叛') - 0.2, 0.5)
        big(cv, '品牌背叛了', W / 2, 760, 100, a=o, color=(1.0, 0.65, 0.58), glow=0.3)
        big(cv, '用户的身份', W / 2, 900, 100, a=o, grad=REDG, glow=0.5)
        L = layer(); line(L, (140, 1040), (140 + 800 * ease(lin(t, WT('q1', '背叛'), WT('q1', '身份', end=True))), 1040), 4); stroke_layer(cv, L, RED, o, glow=1.0)
        return
    a = ease(lin(t, T('q2') - 0.2, T('q2') + 0.4))
    photo(cv, 'himalaya.jpg', t, T('q2') - 0.2, T('q4'), 1.05, 1.18, 0.5, 0.5, 0.45, 0.42, a=a, sat=0.6, warm=-0.2, contrast=1.1, gain=0.55)
    shade(cv, 0.45, 0.85, 0.08)
    tf = WT('q2', '烟花') - 0.3
    if t > tf: FW.draw(cv, t - tf, a * (1 - ease(lin(t, T('q4') - 0.3, T('q4') + 0.3))))
    label(cv, '2025.09.19 · 喜马拉雅山脊 · 始祖鸟 × 蔡国强“升龙”', W / 2, 215, 30, WHITE, a, 'sans_bold')
    label(cv, '烟花为示意动画，背景为喜马拉雅道拉吉里峰（非事发地）', W / 2, 262, 24, GREY, a, 'sans_light')
    if t < T('q4') - 0.1:
        o = ease(lin(t, WT('q3', '敬畏自然') - 0.3, WT('q3', '敬畏自然') + 0.2))
        crack = ease(lin(t, HIT['fire'] - 0.1, HIT['fire'] + 0.4))
        card(cv, 250, 1110, 830, 1230, (0.08, 0.10, 0.10), 0.92 * o, mix(TEAL, RED, crack), r=12, glow=0.5)
        label(cv, '“敬畏自然”', W / 2, 1170, 54, mix(TEAL, RED, crack), o, 'serif_black')
        if crack > 0:
            L = layer(); poly(L, [(560, 1112), (540, 1145), (575, 1180), (545, 1228)], 3); stroke_layer(cv, L, RED, crack, glow=1.0)
        o2 = ease(lin(t, WT('q3', '两天后') - 0.2, WT('q3', '两天后') + 0.3))
        chip(cv, '9.21 · 双方先后道歉', W / 2 - 200, 1300, o2, WHITE, 30, (0.08, 0.08, 0.10))
        chip(cv, '日喀则成立调查组', W / 2 + 230, 1300, ease(lin(t, WT('q3', '调查组') - 0.3, WT('q3', '调查组'))), WHITE, 30, (0.08, 0.08, 0.10))
        source(cv, '新华网、中新网、澎湃新闻 2025.09.21–22', o2, y=1365)
    else:
        o = ease(lin(t, T('q4') - 0.1, T('q4') + 0.3)); dim(cv, 1 - 0.6 * o)
        big(cv, '为身份多付钱，', W / 2, 760, 84, a=o, grad=GOLDG, glow=0.4)
        big(cv, '也会因为身份，转身离开', W / 2, 890, 70, a=ease(lin(t, WT('q4', '转身') - 0.4, WT('q4', '转身'))), color=WHITE, glow=0.2)
    credit(cv, 'himalaya', a, y=1400)


# ═══════════════════════ 06 · 答案 ═══════════════════════
def sc_answer(cv, t):
    bg(cv, t, (0.07, 0.065, 0.06))
    if t < T('z3') - 0.1:
        # 隐形测试：聚光灯下一只包，周围的目光一盏盏熄灭
        a = ease(lin(t, T('z1') - 0.2, T('z1') + 0.4))
        L = layer(); fpoly(L, [(W / 2 - 60, 120), (W / 2 + 60, 120), (W / 2 + 330, 980), (W / 2 - 330, 980)]); fill(cv, cv2.GaussianBlur(L, (0, 0), 30), (1.0, 0.92, 0.75), 0.12 * a)
        L = layer(); poly(L, [(420, 960), (440, 760), (640, 760), (660, 960)], 5, closed=True); arc(L, (540, 760), 70, 180, 360, 5)
        stroke_layer(cv, L, GOLD, a, glow=1.2)
        off = lin(t, WT('z2', '没有任何人') - 0.3, WT('z2', '知道', end=True) + 0.3)
        for i in range(8):
            ang = math.pi * (0.1 + 0.8 * i / 7); x = W / 2 + 430 * math.cos(ang) * 1.05; y = 1180 - 120 * math.sin(ang)
            on = 1 - ease(lin(off, i / 8, i / 8 + 0.15))
            L = layer(); poly(L, [(x - 26, y), (x, y - 14), (x + 26, y), (x, y + 14)], 3, closed=True); circle(L, (x, y), 6, fill=True)
            stroke_layer(cv, L, WHITE, a * (0.15 + 0.85 * on), glow=0.6 * on)
        o = ease(lin(t, WT('z2', '还愿意') - 0.3, WT('z2', '还愿意') + 0.2))
        big(cv, '你还愿意，', W / 2, 330, 72, a=o, color=WHITE, glow=0.2)
        big(cv, '多付同样多的钱吗？', W / 2, 440, 72, a=o, grad=GOLDG, glow=0.5)
        label(cv, '隐形测试', W / 2, 1310, 34, GOLD, a, 'serif_semi', track=0.3)
        return
    if t < T('z4') - 0.1:
        a = ease(lin(t, T('z3') - 0.2, T('z3') + 0.3))
        for i, (q, ans, col, key) in enumerate((('愿意', '你买的是品质', TEAL, '愿意'), ('不愿意', '你买的是别人的目光', GOLD, '不愿意'))):
            s, o = pop(t, WT('z3', key, nth=0) - 0.1, 0.45); y = 560 + i * 280
            card(cv, 110, y - 110, 970, y + 110, (0.10, 0.10, 0.11), 0.92 * o, col, glow=0.5)
            label(cv, q, 200, y, 52, col, o, 'sans_black', anchor='l')
            label(cv, ans, 930, y, 46, WHITE, o, 'serif_semi', anchor='r')
        o = ease(lin(t, WT('z3', '两种') - 0.2, WT('z3', '两种') + 0.3))
        big(cv, '两种，都没有错', W / 2, 1180, 72, a=o, color=(1.0, 0.92, 0.80), glow=0.4)
        return
    if t < T('z5b') - 0.1:
        a = ease(lin(t, T('z4') - 0.1, T('z4') + 0.3))
        label(cv, '对投资者来说', W / 2, 340, 40, GREY, a, 'sans_bold')
        s, o = pop(t, WT('z4', '贵') - 0.1, 0.45)
        card(cv, 340, 430, 740, 650, (0.12, 0.11, 0.10), 0.92 * o, GREY, r=16, glow=0.2)
        big(cv, '贵', W / 2, 540, 130, a=o, color=WHITE, glow=0.1)
        k = ease(lin(t, WT('z4', '标价') - 0.1, WT('z4', '标价') + 0.3))
        L = layer(); line(L, (330, 650), (330 + 420 * k, 430 + 0 * k), 6); stroke_layer(cv, L, RED, k * 0.9, glow=0.8)
        label(cv, '只是一个标价，谁都能标', W / 2, 720, 40, GREY, ease(lin(t, WT('z4', '谁都能标') - 0.3, WT('z4', '谁都能标'))), 'sans_bold')
        o2 = ease(lin(t, T('z5') - 0.2, T('z5') + 0.3))
        gates(cv, t, o2, -1, y=880, done=(0, 1, 2))
        chip(cv, '+ 变成利润', W / 2, 1110, ease(lin(t, WT('z5', '利润') - 0.3, WT('z5', '利润'))), GOLD, 38)
        s3, o3 = pop(t, HIT['answer'] - 0.1, 0.5)
        big(cv, '= 护城河', W / 2, 1240, 84, a=o3, scale=0.9 + 0.1 * s3, grad=GOLDG, glow=0.6)
        return
    if t < T('z6') - 0.1:
        z5b(cv, t, (W / 2, 900), 1.0, (W / 2, 330), (W / 2, 440), (W / 2, 1230))
        return
    a = ease(lin(t, T('z6') - 0.1, T('z6') + 0.4)) * (1 - ease(lin(t, HIT['logo'] - 0.5, HIT['logo'])))
    DUST.draw(cv, t, GOLD, 0.35)
    label(cv, '品牌的最高境界', W / 2, 560, 48, GREY, a, 'sans_bold')
    o1 = ease(lin(t, WT('z6', '我拥有它') - 0.3, WT('z6', '我拥有它') + 0.2)) * a / max(a, 1e-3) * (1 - ease(lin(t, HIT['logo'] - 0.5, HIT['logo'])))
    big(cv, '不是“我拥有它”', W / 2, FINAL_Y[0], 84, a=o1, color=(0.85, 0.85, 0.88), glow=0.1)
    o2 = ease(lin(t, WT('z6', '它代表我') - 0.3, WT('z6', '它代表我') + 0.2)) * (1 - ease(lin(t, HIT['logo'] - 0.5, HIT['logo'])))
    big(cv, FINAL_LINE, W / 2, FINAL_Y[1], 96, a=o2, grad=GOLDG, glow=0.7)


def z5b(cv, t, body, sc, p_lab, p_chip, p_big):
    """z5b：品牌成了你的一部分——对手要抢走的不是一笔订单，而是你对自己的理解"""
    a = ease(lin(t, T('z5b') - 0.2, T('z5b') + 0.4))
    L = layer(); silhouette(L, body[0], body[1], sc); stroke_layer(cv, L, (0.62, 0.66, 0.74), a * 0.7, glow=0.3)
    kc = ease(lin(t, WT('z5b', '一部分') - 0.3, WT('z5b', '一部分') + 0.4))
    cy_ = body[1] - 20 * sc
    L = layer(); circle(L, (body[0], cy_), 46 * sc, 5); circle(L, (body[0], cy_), 12 * sc, fill=True); stroke_layer(cv, L, GOLD, a * kc, glow=1.6)
    o1 = ease(lin(t, WT('z5b', '对手') - 0.2, WT('z5b', '对手') + 0.3))
    label(cv, '对手要抢走的', p_lab[0], p_lab[1], 42, GREY, o1, 'sans_bold')
    s, o2 = pop(t, WT('z5b', '订单') - 0.25, 0.4)
    chip(cv, '一笔订单', p_chip[0], p_chip[1], o2, WHITE, 40, (0.10, 0.10, 0.12))
    ks = ease(lin(t, WT('z5b', '而是') - 0.2, WT('z5b', '而是') + 0.2)); w_ = text_w('一笔订单', 'sans_bold', 40) + 60
    L = layer(); line(L, (p_chip[0] - w_ / 2, p_chip[1]), (p_chip[0] - w_ / 2 + w_ * ks, p_chip[1]), 5); stroke_layer(cv, L, RED, ks * o2, glow=0.6)
    s3, o3 = pop(t, WT('z5b', '理解') - 0.4, 0.5)
    big(cv, '而是你对自己的理解', p_big[0], p_big[1], 68, a=o3, scale=0.92 + 0.08 * s3, grad=GOLDG, glow=0.6)


FINAL_LINE = '而是“它代表我”'
FINAL_Y = (780, 930)


LOGO_PX = 340; LOGO_Y = 720
LOGO = load_logo(LOGO_PX)


def shimmer_text(cv, s_, x, y, fname, size, a, grad=None, color=WHITE, track=0.0, scale=1.0, sweep=-1.0, glow=0.5):
    """文字 + 一道斜向流光（sweep 0→1 从左扫到右；<0 不扫）"""
    if a <= 0.003: return
    rgb, al = text_patch(s_, fname, int(size), tuple(color), track, 0, grad)
    if 0 <= sweep <= 1:
        h, w = al.shape; xs = np.arange(w, dtype=np.float32)[None, :]; ys = np.arange(h, dtype=np.float32)[:, None]
        pos = (-0.25 + 1.5 * sweep) * w
        band = np.exp(-(((xs + 0.35 * ys) - pos) / (0.06 * w + 8)) ** 2)[..., None]
        rgb = np.clip(rgb + (np.asarray((1.0, 0.97, 0.88), np.float32) - rgb) * band * 0.9, 0, 1)
        g = cv2.GaussianBlur(al * band[..., 0], (0, 0), size * 0.15)
        blit(cv, np.ones_like(rgb) * np.asarray((1.0, 0.9, 0.7), np.float32), g, x, y, alpha=a * 0.9, scale=scale, add=True)
    sh = cv2.GaussianBlur(al, (0, 0), size * 0.12)
    blit(cv, np.zeros_like(rgb), np.clip(sh * 1.3, 0, 1), x, y + size * 0.04, alpha=a * 0.6, scale=scale)
    if glow > 0: blit(cv, rgb, cv2.GaussianBlur(al, (0, 0), size * 0.25), x, y, alpha=a * glow, scale=scale, add=True)
    blit(cv, rgb, al, x, y, alpha=a, scale=scale)


class Gather:
    """片尾粒子：从上一画面的金句字形出发，旋转汇聚成官方 logo"""
    def __init__(self, n=3200, seed=5):
        rng = np.random.default_rng(seed)
        lrgb, lal = LOGO
        ys, xs = np.nonzero(lal > 0.5)
        pick = rng.choice(len(xs), n, replace=len(xs) < n)
        self.tx = xs[pick] + W / 2 - lal.shape[1] / 2 + rng.normal(0, 0.6, n)
        self.ty = ys[pick] + LOGO_Y - lal.shape[0] / 2 + rng.normal(0, 0.6, n)
        self.tc = lrgb[ys[pick], xs[pick]].astype(np.float32)
        # 起点：z6 金句的两行字形 + 少量来自整幅画面的尘埃
        src = []
        for line_, yy, sz in (('不是“我拥有它”', FINAL_Y[0], 84), (FINAL_LINE, FINAL_Y[1], 96)):
            rgb, al = text_patch(line_, 'serif_black', sz, GOLD, 0.02, 0, GOLDG)
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

    def draw(self, cv, u, dur):
        """u：距汇聚开始的秒数"""
        k = np.clip((u - self.delay) / dur, 0, 1)
        e = np.where(k < 0.5, 4 * k ** 3, 1 - (-2 * k + 2) ** 3 / 2)
        dx, dy = self.tx - self.sx, self.ty - self.sy
        ang = self.swirl * np.sin(np.pi * k) * 0.9
        ca, sa = np.cos(ang), np.sin(ang)
        # 绕 logo 中心旋转的弧线轨迹
        cx, cy = self.sx + dx * e - W / 2, self.sy + dy * e - LOGO_Y
        x = W / 2 + cx * ca - cy * sa; y = LOGO_Y + cx * sa + cy * ca
        m = (e ** 3)[:, None]   # 飞行途中保持金色，接近落点才变成 logo 的蓝
        col = np.asarray(GOLD, np.float32)[None] * (1 - m) + self.tc * m
        bright = (0.45 + 0.55 * np.sin(np.pi * k)) * np.clip(u / 0.25, 0, 1)
        acc = np.zeros((H, W, 3), np.float32)
        xi = np.clip(x.astype(int), 0, W - 2); yi = np.clip(y.astype(int), 0, H - 2)
        v = col * (bright * self.size)[:, None]
        for ox, oy, wgt in ((0, 0, 1.0), (1, 0, 0.5), (0, 1, 0.5), (1, 1, 0.3)):
            np.add.at(acc, (yi + oy, xi + ox), v * wgt)
        # 拖尾：沿速度方向再打两点
        k2 = np.clip((u - 0.05 - self.delay) / dur, 0, 1); e2 = np.where(k2 < 0.5, 4 * k2 ** 3, 1 - (-2 * k2 + 2) ** 3 / 2)
        ang2 = self.swirl * np.sin(np.pi * k2) * 0.9; c2, s2 = np.cos(ang2), np.sin(ang2)
        cx2, cy2 = self.sx + dx * e2 - W / 2, self.sy + dy * e2 - LOGO_Y
        x2 = np.clip((W / 2 + cx2 * c2 - cy2 * s2).astype(int), 0, W - 1); y2 = np.clip((LOGO_Y + cx2 * s2 + cy2 * c2).astype(int), 0, H - 1)
        np.add.at(acc, (y2, x2), v * 0.45)
        acc = cv2.GaussianBlur(acc, (0, 0), 1.1)
        glow = cv2.resize(cv2.GaussianBlur(cv2.resize(acc, (W // 4, H // 4), interpolation=cv2.INTER_AREA), (0, 0), 5), (W, H))
        cv += acc * 1.25 + glow * 1.3


GATHER = None


def sc_end(cv, t):
    global GATHER
    if GATHER is None: GATHER = Gather()
    bg(cv, t, (0.07, 0.07, 0.09))
    t0, land, brand, slogan, fade_t = HIT['logo'], HIT['logo_land'], HIT['brand'], HIT['slogan'], HIT['fade']
    u = t - t0; out = 1 - ease(lin(t, fade_t, TOTAL - 0.15))
    DUST.draw(cv, t, GOLD, 0.35 * out)
    # 1 汇聚
    dur = land - t0 - 0.55
    pk = 1 - ease(lin(t, land - 0.15, land + 0.55))
    if pk > 0:
        tmp = np.zeros_like(cv); GATHER.draw(tmp, u, dur); cv += tmp * pk
    # 2 logo 落定：清晰浮现 + 柔光 + 一圈淡蓝光环
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
        cv += np.asarray((0.55, 0.75, 1.0), np.float32) * (np.exp(-(((_XX - W / 2) ** 2 + (_YY - LOGO_Y) ** 2) / (2 * 260.0 ** 2))))[..., None] * f * 0.55
        L = layer(); circle(L, (W / 2, LOGO_Y), 190 + 420 * eout(v / 1.1), 3 * (1 - v / 1.1) + 1); stroke_layer(cv, L, (0.55, 0.78, 1.0), f * 0.8, glow=2, add=True)
    # 3 重拍：金色「巴芒价值」+ 流光；BUFFETT · MUNGER 紧随
    w_ = t - brand
    if w_ > -0.05:
        a1 = ease(lin(w_, -0.05, 0.2)) * out; s1 = 1.10 - 0.10 * eout(lin(w_, -0.05, 0.6))
        shimmer_text(cv, '巴芒价值', W / 2, 1010, 'serif_black', 118, a1, grad=((1.0, 0.95, 0.78), (0.88, 0.62, 0.24)), track=0.12,
                     scale=s1, sweep=lin(w_, 0.15, 1.35) if w_ < 1.4 else -1, glow=0.6)
        a2 = ease(lin(w_, 0.25, 0.6)) * out
        tw = text_w('巴芒价值', 'serif_black', 118, 0.12); tr_ = max(0.1, (tw - text_w('BUFFETT · MUNGER', 'corm_med', 40)) / (40 * 15))
        shimmer_text(cv, 'BUFFETT · MUNGER', W / 2, 1112, 'corm_med', 40, a2, color=(0.84, 0.70, 0.44), track=tr_,
                     sweep=lin(w_, 0.45, 1.5) if w_ < 1.6 else -1, glow=0.25)
        if 0 <= w_ < 0.5:
            cv += np.asarray((1.0, 0.82, 0.5), np.float32) * (np.exp(-(((_XX - W / 2) / 420.0) ** 2 + ((_YY - 1010) / 140.0) ** 2)))[..., None] * (1 - w_ / 0.5) ** 2 * 0.2
    # 4 细金线引出关注语
    z = t - slogan
    if z > -0.6:
        kl = eout(lin(z, -0.6, 0.3)); a3 = out
        L = layer(); line(L, (W / 2 - 290 * kl, 1185), (W / 2 + 290 * kl, 1185), 2); stroke_layer(cv, L, GOLD, 0.85 * a3, glow=1.0)
        L = layer(); circle(L, (W / 2 - 290 * kl, 1185), 3, fill=True); circle(L, (W / 2 + 290 * kl, 1185), 3, fill=True); stroke_layer(cv, L, GOLD_HI, kl * a3, glow=1.5, add=True)
        o1 = ease(lin(z, 0.05, 0.6)) * a3; o2 = ease(lin(z, 0.35, 0.9)) * a3
        text(cv, '关注「巴芒价值」', W / 2, 1262 + 14 * (1 - o1), 'serif_semi', 48, (0.96, 0.94, 0.90), alpha=o1, track=0.10, shadow=0.6)
        text(cv, '传承大师智慧，领悟投资真谛', W / 2, 1340 + 14 * (1 - o2), 'serif_semi', 42, (0.93, 0.82, 0.60), alpha=o2, track=0.14, shadow=0.6, glow=0.25)
    if t > fade_t: cv *= out


_YY, _XX = np.mgrid[0:H, 0:W].astype(np.float32)


# ═══════════════════════════ 编排 ═══════════════════════════
CLIPS = {}


def load_clips():
    CLIPS['airport'] = Clip('airport.mp4', 1080, 0.5)   # 1080×608，已在 fetch_clips 里裁掉烧录字幕
    CLIPS['peacock'] = Clip('peacock.mp4', 1080, 0.5)
    for k in ('crowd', 'car', 'turn'): CLIPS['dfd_' + k] = Clip('dfd_%s.mp4' % k, 640, 0.5)


SC = [  # (start, end, fn)
    (0.0, T('o3') - 0.3, sc_intro), (T('o3') - 0.3, T('o6') - 0.3, sc_orange), (T('o6') - 0.3, T('o11') - 0.3, sc_halves),
    (T('o11') - 0.3, HIT['title'], sc_question), (HIT['title'], T('p1') - 0.25, sc_title),
    (T('p1') - 0.25, T('p6') - 0.3, sc_three), (T('p6') - 0.3, T('p9') - 0.3, sc_envy), (T('p9') - 0.3, T('p14') - 0.3, sc_signal),
    (T('p14') - 0.3, T('p16') - 0.3, sc_price), (T('p16') - 0.3, T('d1') - 0.3, sc_paradox), (T('d1') - 0.3, T('k1') - 0.3, sc_ruler),
    (T('k1') - 0.3, T('k6') - 0.3, sc_gate1), (T('k6') - 0.3, T('k16') - 0.3, sc_gate2), (T('k16') - 0.3, T('m1') - 0.3, sc_gate3),
    (T('m1') - 0.3, T('g1') - 0.25, sc_math), (T('g1') - 0.25, T('q1') - 0.3, sc_china), (T('q1') - 0.3, T('z1') - 0.3, sc_betray),
    (T('z1') - 0.3, HIT['logo'], sc_answer), (HIT['logo'], TOTAL + 1, sc_end)]
XF = 0.45   # 场景间交叉溶解
XF_END = 1.0
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
NOSUB = {'o12', 'p7', 'd2', 'd3', 'k14', 'z2', 'z6'}
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
        if t0 - 0.04 <= t <= t1:
            a = ease(lin(t, t0 - 0.04, t0 + 0.1)) * (1 - ease(lin(t, t1 - 0.1, t1)))
            n = sum(0.55 if ch.isdigit() or ch in '.%' else 1 for ch in s)
            size = 52 if n <= 16 else int(52 * 16 / n)
            w = text_w(s, 'sans_bold', size) + 70
            L = layer(); rect(L, W / 2 - w / 2, SUB_Y - 46, W / 2 + w / 2, SUB_Y + 46, r=14); fill(cv, L, (0, 0, 0), 0.42 * a)
            text(cv, s, W / 2, SUB_Y, 'sans_bold', size, WHITE, alpha=a, shadow=0.5)


def render(fi):
    t = fi / FPS; cv = np.zeros((H, W, 3), np.float32)
    act = []
    for s0, s1, fn in SC:
        xf0 = XF_END if s0 == HIT['logo'] else XF; xf1 = XF_END if s1 == HIT['logo'] else XF
        lead = 0 if s0 in HARD else xf0 / 2; tail = 0 if s1 in HARD else xf1 / 2
        if s0 - lead <= t < s1 + tail:
            w = 1.0
            if t < s0 + lead and lead: w = min(w, ease((t - (s0 - lead)) / (2 * lead)))
            if t > s1 - tail and tail: w = min(w, 1 - ease((t - (s1 - tail)) / (2 * tail)))
            act.append((w, fn))
    tot = sum(w for w, _ in act) or 1
    import engine as _e
    for w, fn in act:
        _e.CUR_W = w / tot if len(act) > 1 else w
        if _e.REC is not None: _e.SCENE_START = [len(_e.REC), len(_e.TXT_INK)]
        tmp = np.zeros_like(cv); fn(tmp, t); cv += tmp * _e.CUR_W
    _e.CUR_W = 1.0
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
                              '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
        for fi in range(f0, f1):
            p.stdin.write(to8(render(fi)).tobytes())
            if (fi - f0) % 150 == 0: print('chunk', f0, fi, flush=True)
        p.stdin.close(); p.wait()
    elif mode == 'nf': print(NF)
    elif mode == 'audit':   # python3 src/video.py WORK audit t0 t1 step out.json：记录版面，找重叠
        import engine as _e
        t0, t1, step, out = float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), sys.argv[6]; res = []
        for t in np.arange(t0, t1, step):
            _e.REC = []; _e.GMASK = np.zeros((H, W), np.float32); _e.TXT_INK = []
            render(int(round(t * FPS)))
            hits = []
            for s_, x0, y0, m, a in _e.TXT_INK:      # 文字字形落在描边图形上的像素
                h, w = m.shape; xa, ya = max(0, x0), max(0, y0); xb, yb = min(W, x0 + w), min(H, y0 + h)
                if xb <= xa or yb <= ya: continue
                mm = m[ya - y0:yb - y0, xa - x0:xb - x0]; g = _e.GMASK[ya:yb, xa:xb] > 0.3
                n = int((mm & g).sum()); tot = int(mm.sum())
                if a >= 0.35 and (n >= 60 or n >= 0.008 * max(1, tot)) and n >= 20: hits.append(('onGraphic', s_, n, round(n / max(1, tot), 3), a))
            res.append((round(float(t), 2), _e.REC + hits)); _e.REC = None; _e.GMASK = None; _e.TXT_INK = None
        json.dump(res, open(out, 'w'), ensure_ascii=False)
