"""《多付的钱，买的是什么》横版分镜（1920×1080 · 30fps）。
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

CY = 470          # 画面主体中心
SUB_Y = 960       # 字幕中心
SRC_Y, CRED_Y = 1032, 1062
CX2 = 1440        # 右栏中心


def credit(cv, key, a=1.0, y=None):
    c = CREDIT.get(key)
    if not c: return
    s = ('视频' if key.startswith('v_') else '图') + '：%s · %s · Wikimedia Commons' % (c.get('artist', '')[:34], c.get('license', ''))
    text(cv, s, 56, CRED_Y, 'sans_light', 22, GREY, anchor='l', alpha=0.75 * a)


def source(cv, s, a=1.0, y=None):
    text(cv, s, 56, SRC_Y, 'sans_light', 24, GREY, anchor='l', alpha=0.8 * a)


def gates(cv, t, a, active=-1, y=300, done=(), cx=None):
    names = ('认得出', '仿不了', '稀释不了'); cx = W / 2 if cx is None else cx
    for i, n in enumerate(names):
        x = cx + (i - 1) * 330; on = i == active; ok = i in done
        col = GOLD if on else (TEAL if ok else (0.42, 0.44, 0.50))
        L = layer(); arc(L, (x, y), 62, -90, 90, 4); line(L, (x - 62, y), (x - 62, y + 70), 4); line(L, (x + 62, y), (x + 62, y + 70), 4)
        stroke_layer(cv, L, col, a * (1.0 if on or ok else 0.6), glow=1.2 if on else 0.2)
        label(cv, n, x, y + 118, 36 if on else 30, col, a * (1.0 if on or ok else 0.7), 'sans_black' if on else 'sans_med')


def side_fade(cv, x1, a0=0.55):
    """左侧人物照片的右缘渐隐到底色"""
    x = np.linspace(0, 1, x1, dtype=np.float32)[None, :, None]
    cv[:, :x1] *= (1 - 0.92 * np.clip((x - a0) / (1 - a0), 0, 1))


def vframe_h(cv, clip, t, t0, x0, y0, w, a=1.0, z0=1.0, z1=1.06, dur=6.0, edge=GOLD, **g):
    """视频放进 16:9 窗口，背后铺同一画面的虚化放大版"""
    if a <= 0.003: return
    f = grade(clip.get(t - t0), **g); zz = z0 + (z1 - z0) * ease(lin(t, t0, t0 + dur))
    small = cover(f, W // 6, H // 6, 1.0)
    bgi = cv2.resize(cv2.GaussianBlur(small, (0, 0), 7), (W, H), interpolation=cv2.INTER_LINEAR) * 0.38
    cv *= (1 - a); cv += bgi * a
    h = int(round(w * 9 / 16)); x0, y0 = int(x0), int(y0)
    fr = cover(f, w, h, zz)
    sub = cv[y0:y0 + h, x0:x0 + w]; sub *= (1 - a); sub += fr * a
    if edge is not None:
        L = layer(); rect(L, x0, y0, x0 + w, y0 + h, fill=False, w=2); stroke_layer(cv, L, edge, 0.45 * a, glow=0.3)


# ═══════════════════════ 引子 · 一年两半 ═══════════════════════
def sc_intro(cv, t):
    bg(cv, t, (0.06, 0.05, 0.07))
    if t < T('o2') - 0.15:
        k = eout(lin(t, 0.2, 1.6)); fade_ = 1 - ease(lin(t, 1.9, 2.5))
        if fade_ > 0:
            L = layer(); n = 9; x0, x1, yb = 560, 1360, 400
            pts = []
            for i in range(n + 1):
                pts.append((x0 + (x1 - x0) * i / n, yb + 18 * math.sin(math.pi * i / n)))
                if i < n: pts.append((x0 + (x1 - x0) * (i + 0.5) / n, yb + 115 + 28 * math.sin(math.pi * (i + 0.5) / n)))
            m = max(2, int(len(pts) * k)); poly(L, pts[:m], 5)
            stroke_layer(cv, L, WHITE, fade_, glow=1.6)
        if t > 1.9:
            a = ease(lin(t, 1.9, 2.5)) * (1 - ease(lin(t, WT('o1', '门店') - 0.5, WT('o1', '门店'))))
            vframe_h(cv, CLIPS['airport'], t, 1.9, 400, 110, 1120, a, 1.0, 1.06, 4, sat=0.95, warm=0.2, contrast=1.08, gain=0.95)
            label(cv, '2025.09 · 香港国际机场 · 7 米高的特别版 LABUBU', W / 2, 790, 30, WHITE, a * 0.9, 'sans_med')
            credit(cv, 'v_airport', a)
        tq = WT('o1', '门店') - 0.5
        if t > tq:
            a = ease(lin(t, tq, tq + 0.5))
            photo(cv, 'queue1.jpg', t, tq, T('o2'), 1.04, 1.12, 0.5, 0.5, 0.45, 0.45, a=a, sat=0.9, warm=0.2, contrast=1.08, gain=0.85)
            shade(cv, 0.3, 0.8, 0.08)
            ql = ease(lin(t, tq + 0.5, tq + 0.8))
            label(cv, '香港将军澳 · 泡泡玛特门前的长队 · 2025.04', W / 2, 840, 30, WHITE, ql * 0.9, 'sans_med')
            credit(cv, 'queue1', ql)
        return
    photo(cv, 'browsing.jpg', t, T('o2') - 0.3, T('o3'), 1.1, 1.2, 0.5, 0.5, 0.5, 0.5, sat=0.6, warm=0.4, contrast=1.05, gain=0.32)
    cv[:] = cv2.GaussianBlur(cv, (0, 0), 6)
    th = HIT['auction']; u = t - th
    ang = -38 * (1 - ein(lin(t, th - 0.55, th))) + (4 * math.exp(-u * 9) * math.sin(u * 40) if u > 0 else 0)
    L = layer(); cx, cy = 620, 360; ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    def R(x, y): return (cx + x * ca - y * sa, cy + x * sa + y * ca)
    poly(L, [R(-150, -46), R(-10, -46), R(-10, 46), R(-150, 46)], 5, closed=True)
    line(L, R(-80, 46), R(-80, 300), 9)
    line(L, (410, 480), (800, 480), 6)
    a0 = ease(lin(t, T('o2') - 0.1, T('o2') + 0.4))
    stroke_layer(cv, L, GOLD, a0, glow=1.0)
    if 0 <= u < 0.9:
        L = layer(); circle(L, (605, 480), 30 + 120 * eout(u / 0.9), 4 * (1 - u / 0.9) + 1); stroke_layer(cv, L, GOLD_HI, (1 - u / 0.9) * 0.9, glow=2, add=True)
    n = 1080000 * eout(lin(t, th - 0.6, th + 0.1))
    o = ease(lin(t, th - 0.6, th - 0.3))
    stat(cv, 1330, 380, '¥' + counter(n), '', o, size=140, grad=GOLDG)
    label(cv, '1.31 米 · 薄荷色 · 全球仅此一只', 1330, 530, 38, WHITE, ease(lin(t, th, th + 0.4)), 'sans_bold')
    label(cv, '北京永乐拍卖 · 2025.06.10 · 成交价含佣金', 1330, 590, 28, GREY, ease(lin(t, th + 0.2, th + 0.6)), 'sans_med')
    credit(cv, 'browsing', a0)


def sc_orange(cv, t):
    bg(cv, t, (0.09, 0.06, 0.04))
    if t < T('o4') - 0.1:
        photo(cv, 'iphone_orange.jpg', t, T('o3') - 0.4, T('o4'), 1.05, 1.15, 0.5, 0.5, 0.45, 0.42, sat=1.0, warm=0.15, contrast=1.08, gain=0.85)
        shade(cv, 0.35, 0.85, 0.12)
        tw = WT('o3', '爱马仕橙'); s, o = pop(t, tw - 0.1, 0.5)
        big(cv, '“爱马仕橙”', W / 2, 690, 128, a=o, scale=0.9 + 0.1 * s, grad=ORANGEG, glow=0.6)
        label(cv, 'iPhone 17 Pro · 宇宙橙 · 2025 秋', W / 2, 820, 32, WHITE, ease(lin(t, T('o3'), T('o3') + 0.5)), 'sans_med')
        credit(cv, 'iphone_orange', 1)
        return
    if t < T('o5') - 0.1:
        k = eout(lin(t, T('o4') - 0.1, T('o4') + 0.6))
        panel(cv, 'iphone_back.jpg', 0, 0, W // 2, H, 1, 1.1, 0.5, 0.45, sat=1.0, warm=0.15, gain=0.8)
        panel(cv, 'hermes_ginza.jpg', W // 2, 0, W, H, k, 1.05, 0.5, 0.5, sat=0.95, warm=0.3, gain=0.8)
        shade(cv, 0.3, 0.85, 0.12)
        L = layer(); line(L, (W / 2, 0), (W / 2, 880 * k), 3); stroke_layer(cv, L, ORANGE, 0.9, glow=1.4)
        o = ease(lin(t, WT('o4', '奢侈品牌') - 0.2, WT('o4', '奢侈品牌') + 0.3))
        label(cv, 'iPhone', W / 4, 740, 56, WHITE, 1, 'playfair')
        label(cv, 'HERMÈS', W * 3 / 4, 740, 56, ORANGE, o, 'playfair', track=0.1)
        label(cv, '手机', W / 4, 815, 30, GREY, 1, 'sans_med'); label(cv, '东京银座 · 爱马仕之家', W * 3 / 4, 815, 30, GREY, o, 'sans_med')
        text(cv, '图：%s · %s ／ %s · %s' % (CREDIT['iphone_back']['artist'][:16], CREDIT['iphone_back']['license'],
                                         CREDIT['hermes_ginza']['artist'][:16], CREDIT['hermes_ginza']['license']), 56, CRED_Y, 'sans_light', 22, GREY, anchor='l', alpha=0.75)
        return
    a = ease(lin(t, T('o5') - 0.1, T('o5') + 0.4)); x0, x1, yb = 790, 1130, 800
    segs = [(0.0, 0.42, (0.36, 0.38, 0.42)), (0.42, 0.70, (0.40, 0.52, 0.66)), (0.70, 1.0, GOLD)]
    tg = WT('o5', '有一部分'); hh = 620
    for i, (s0, s1, col) in enumerate(segs):
        y0 = yb - hh * s1; y1 = yb - hh * s0
        c = col if i < 2 else mix((0.40, 0.52, 0.66), GOLD, ease(lin(t, tg - 0.2, tg + 0.5)))
        card(cv, x0, y0 + 3, x1, y1 - 3, mix(c, INK, 0.25), 0.95 * a, c, r=10, glow=1.2 if i == 2 else 0.2)
    label(cv, '价格', W / 2, yb + 50, 40, WHITE, a, 'sans_black')
    o = ease(lin(t, tg, tg + 0.5))
    big(cv, '?', W / 2, yb - hh * 0.85, 110, a=o, color=INK, glow=0.0)
    label(cv, '东西本身', W / 2, yb - hh * 0.21, 40, WHITE, a, 'sans_bold')


def sc_halves(cv, t):
    """o6 一分为二 → o7 泡泡玛特 → o8 老铺黄金 → o9 iPhone 收入 +21% → o10 一年就退潮 vs 越卖越多"""
    bg(cv, t, (0.07, 0.06, 0.07))
    if t < T('o7') - 0.1:
        k = eout(lin(t, T('o6') - 0.1, T('o6') + 0.8)); off = int((1 - k) * 160)
        left = cover(graded('nyc_store.jpg', sat=0.35, warm=-0.6, contrast=1.15, gain=0.55), W // 2, H, 1.15, 0.5, 0.5)
        right = cover(graded('iphone_orange.jpg', sat=1.0, warm=0.2, contrast=1.1, gain=0.85), W // 2, H, 1.1, 0.5, 0.45)
        cv[:, :W // 2] = np.roll(left, off, 0) * k; cv[:, W // 2:] = np.roll(right, -off, 0) * k
        shade(cv, 0.3, 0.8, 0.1)
        L = layer(); line(L, (W / 2, 0), (W / 2, 880 * k), 3); stroke_layer(cv, L, GOLD, 0.9, glow=1.5)
        s, o = pop(t, WT('o6', '两半'))
        label(cv, '泡泡玛特 · 老铺黄金', W / 4, 780, 40, (1.0, 0.70, 0.62), o, 'sans_black')
        label(cv, 'iPhone', W * 3 / 4, 780, 44, GOLD_HI, o, 'sans_black')
        return
    if t < T('o8') - 0.1:
        photo(cv, 'nyc_store.jpg', t, T('o7') - 0.3, T('o8'), 1.05, 1.12, 0.5, 0.5, 0.5, 0.5, sat=0.35, warm=-0.5, contrast=1.1, gain=0.35)
        a = ease(lin(t, T('o7') - 0.1, T('o7') + 0.4))
        big(cv, '泡泡玛特', W / 2, 190, 92, a=a, color=(1.0, 0.72, 0.64), glow=0.2)
        t1 = WT('o7', '收入'); o1 = ease(lin(t, t1 - 0.2, t1 + 0.3))
        card(cv, 140, 300, 900, 760, (0.10, 0.07, 0.08), 0.9 * o1, RED, glow=0.4)
        label(cv, '2026 年第三季度 · 收入同比', 520, 370, 34, WHITE, o1, 'sans_bold')
        stat(cv, 520, 540, '−45%~−50%', '', ease(lin(t, WT('o7', '将近一半') - 0.3, WT('o7', '将近一半'))), col=RED, size=120, grad=REDG)
        t2 = WT('o7', '隐藏款'); o2 = ease(lin(t, t2 - 0.2, t2 + 0.3))
        card(cv, 1020, 300, 1780, 760, (0.10, 0.07, 0.08), 0.9 * o2, RED, glow=0.4)
        label(cv, '最火的隐藏款 · 二手价较峰值', 1400, 370, 34, WHITE, o2, 'sans_bold')
        kk = eout(lin(t, t2, WT('o7', '近九成', end=True)))
        L = layer(); pts = []
        for i in range(41):
            x = 1080 + 640 * i / 40; u = i / 40
            v = 0.15 + 0.85 * (u / 0.25) ** 0.6 if u < 0.25 else 1.0 - 0.88 * ((u - 0.25) / 0.75) ** 0.7
            pts.append((x, 720 - 260 * v))
        m = max(2, int(len(pts) * kk)); poly(L, pts[:m], 5); stroke_layer(cv, L, RED, o2, glow=1.0)
        stat(cv, 1600, 500, '−88%', '', ease(lin(t, WT('o7', '近九成') - 0.3, WT('o7', '近九成'))), col=RED, size=92, grad=REDG)
        source(cv, '公司公告 2026.10.27 ／ 隐藏款“本我”：得物二手成交价，据媒体报道', a)
        return
    if t < T('o9') - 0.1:
        photo(cv, 'gold_bracelet.jpg', t, T('o8') - 0.3, T('o9'), 1.05, 1.15, 0.5, 0.5, 0.5, 0.5, sat=0.9, warm=0.4, contrast=1.1, gain=0.42)
        a = ease(lin(t, T('o8') - 0.1, T('o8') + 0.4))
        big(cv, '老铺黄金', W / 2, 180, 92, a=a, grad=GOLDG, glow=0.4)
        label(cv, '被媒体称作“黄金界爱马仕”', W / 2, 275, 34, WHITE, ease(lin(t, WT('o8', '黄金界') - 0.2, WT('o8', '黄金界') + 0.3)), 'sans_med')
        t1 = WT('o8', '股价'); o1 = ease(lin(t, t1 - 0.2, t1 + 0.3))
        card(cv, 460, 330, 1460, 780, (0.10, 0.08, 0.06), 0.9 * o1, GOLD, glow=0.3)
        label(cv, '股价 · 较 2025 年 7 月高点', W / 2, 390, 34, WHITE, o1, 'sans_bold')
        kk = eout(lin(t, t1, WT('o8', '七成', end=True)))
        L = layer(); pts = []
        for i in range(41):
            u = i / 40; v = 1.0 - 0.73 * (u ** 0.8) + 0.05 * math.sin(u * 19)
            pts.append((540 + 840 * u, 740 - 290 * v))
        m = max(2, int(len(pts) * kk)); poly(L, pts[:m], 5); stroke_layer(cv, L, RED, o1, glow=1.0)
        stat(cv, 1290, 500, '−73%', '', ease(lin(t, WT('o8', '七成') - 0.3, WT('o8', '七成'))), col=RED, size=92, grad=REDG)
        s, o = pop(t, WT('o8', '促销') - 0.1)
        chip(cv, '门店开始促销', W / 2, 850, o, RED, 38, (0.16, 0.06, 0.06))
        source(cv, '股价：2026.07.29 收盘，较历史高点约 −73% ／ 促销：21 世纪经济报道 2026.11 门店走访', a)
        credit(cv, 'gold_bracelet', a)
        return
    if t < T('o10') - 0.1:
        photo(cv, V.img('iphone17_launch', 'iphone_line.jpg'), t, T('o9') - 0.3, T('o10'), 1.05, 1.15, 0.5, 0.5, 0.5, 0.5, sat=0.9, warm=0.1, contrast=1.05, gain=0.36)
        shade(cv, 0.4, 0.85, 0.15)
        a = ease(lin(t, T('o9') - 0.1, T('o9') + 0.4))
        big(cv, 'iPhone', W / 2, 200, 120, a=a, fname='playfair', color=(0.94, 0.95, 0.98), glow=0.3)
        t1 = WT('o9', '百分之二十一'); s, o = pop(t, t1 - 0.25, 0.5)
        stat(cv, W / 2, 480, '+21%', '', o, size=210, grad=GOLDG)
        label(cv, 'iPhone 收入 · 苹果 2026 财年（截至 9 月）', W / 2, 660, 34, WHITE, ease(lin(t, T('o9'), T('o9') + 0.5)), 'sans_bold')
        source(cv, '苹果 2026 财年年报（10-K）：iPhone 收入 2,541 亿美元，上年 2,096 亿美元', a)
        credit(cv, V.cred_key('iphone17_launch', 'iphone_line.jpg'), a)
        return
    a = ease(lin(t, T('o10') - 0.1, T('o10') + 0.4))
    panel(cv, 'nyc_store.jpg', 0, 0, W // 2, H, a, 1.15, sat=0.3, warm=-0.6, gain=0.28)
    panel(cv, V.img('iphone17_launch', 'iphone_line.jpg'), W // 2, 0, W, H, a, 1.15, sat=0.9, warm=0.1, gain=0.4)
    L = layer(); line(L, (W / 2, 140), (W / 2, 720), 3); stroke_layer(cv, L, GOLD, 0.8 * a, glow=1.2)
    t1 = WT('o10', '一年'); s1, o1 = pop(t, t1 - 0.15)
    stat(cv, W / 4, 380, '1', '年', o1, col=(1.0, 0.62, 0.55), size=200, usize=70)
    label(cv, '就退潮', W / 4, 560, 44, WHITE, o1, 'sans_black')
    label(cv, '泡泡玛特 · 老铺黄金', W / 4, 630, 28, GREY, o1, 'sans_med')
    t2 = WT('o10', '越卖越多'); s2, o2 = pop(t, t2 - 0.2)
    big(cv, '越卖越多', W * 3 / 4, 400, 120, a=o2, scale=0.9 + 0.1 * s2, grad=GOLDG, glow=0.5)
    label(cv, 'iPhone', W * 3 / 4, 560, 44, WHITE, o2, 'sans_black')
    label(cv, '同样是让人多付钱的身份', W / 2, 800, 40, WHITE, a, 'serif_semi')


def sc_question(cv, t):
    bg(cv, t, (0.08, 0.07, 0.06)); DUST.draw(cv, t, GOLD, 0.3)
    a = ease(lin(t, T('o11') - 0.1, T('o11') + 0.4)) * (1 - ease(lin(t, T('o12') - 0.3, T('o12'))))
    label(cv, '一个更基本的问题', W / 2, CY, 56, GREY, a, 'serif_semi', track=0.1)
    s, o = pop(t, T('o12') - 0.1, 0.6)
    big(cv, '多付的那部分钱，', W / 2, CY - 80, 96, a=o, color=WHITE, glow=0.2, scale=0.95 + 0.05 * s)
    big(cv, '到底买到了什么？', W / 2, CY + 70, 96, a=ease(lin(t, WT('o12', '到底') - 0.2, WT('o12', '到底') + 0.3)), grad=GOLDG, glow=0.5)


def sc_title(cv, t):
    bg(cv, t, (0.10, 0.08, 0.06)); t0 = HIT['title']; u = t - t0; cy = 520
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
    s, o = pop(t, t0, 0.5); sc_ = 1.12 - 0.12 * s + 0.02 * u / 3
    big(cv, '多付的钱，', W / 2, cy - 140, 112, a=o, scale=sc_, grad=GOLDG, glow=0.7, track=0.04)
    big(cv, '买的是什么', W / 2, cy - 5, 112, a=o, scale=sc_, grad=GOLDG, glow=0.7, track=0.04)
    s2, o2 = pop(t, t0 + 0.6, 0.5)
    big(cv, '身份成为护城河的三道关', W / 2, cy + 120, 54, a=o2, scale=0.9 + 0.1 * s2, color=WHITE, fname='serif_semi', glow=0.15, track=0.08)
    label(cv, 'STATUS AS A MOAT · FIRST PRINCIPLES', W / 2, cy + 200, 24, GOLD, o2 * 0.85, 'corm_med', track=0.25)
    if 0 <= u < 0.35: cv += np.asarray((1.0, 0.85, 0.6), np.float32) * (1 - u / 0.35) ** 2 * 0.55


# ═══════════════════════ 01 · 第一性原理 ═══════════════════════
RC = (720, 480)


def sc_three(cv, t):
    bg(cv, t, (0.06, 0.07, 0.10))
    rings = [(130, '功能', 'FUNCTION', COLD, 'p2'), (250, '认同', 'IDENTITY', TEAL, 'p3'), (370, '地位', 'STATUS', GOLD, 'p4')]
    hl = ease(lin(t, T('p5') - 0.1, T('p5') + 0.5))
    fo = ease(lin(t, WT('p6', '第三个问题') - 0.3, WT('p6', '第三个问题') + 0.3))
    for i, (r, n, en, col, lid) in enumerate(rings):
        s, o = pop(t, WT(lid, '这是') - 0.1, 0.5)
        dimk = (1 - 0.6 * hl) if i == 0 else (1 + 0.4 * hl)
        if i == 1: dimk *= 1 - 0.6 * fo
        L = layer(); circle(L, RC, r * (0.85 + 0.15 * s), 4 if i else 5)
        stroke_layer(cv, L, col, o * min(1, dimk), glow=0.8 * dimk)
        if i == 0:
            label(cv, n, RC[0], RC[1] - 14, 52, col, o * min(1, dimk), 'sans_black')
            label(cv, en, RC[0], RC[1] + 40, 22, GREY, o * min(1, dimk), 'corm_med', track=0.2)
        else:
            yy = RC[1] - (r - 62)
            label(cv, n, RC[0], yy - 6, 48, col, o * min(1, dimk), 'sans_black', glow=0.3 * hl)
            label(cv, en, RC[0], yy + 38, 22, GREY, o * min(1, dimk), 'corm_med', track=0.2)
    for i, (q, key, col) in enumerate((('我需要什么？', 'p2', COLD), ('我是谁？', 'p3', TEAL), ('别人怎么看我？', 'p4', GOLD))):
        o = ease(lin(t, T(key) - 0.2, T(key) + 0.3))
        label(cv, q, 1200, 330 + i * 110, 44, col, o * (1 - 0.5 * hl * (i == 0)) * (1 - 0.5 * fo * (i == 1)), 'sans_black', anchor='l')
    a = ease(lin(t, T('p1') - 0.2, T('p1') + 0.4))
    label(cv, '人买东西，在回答三个问题', 1200, 220, 36, WHITE, a * (1 - hl), 'sans_med', anchor='l')
    label(cv, '品牌溢价，很大一部分来自后两个问题', 1200, 690, 36, GOLD_HI, hl, 'sans_bold', anchor='l')
    for i, w_ in enumerate(('归属感', '审美')):
        tw = WT('p6', w_); s, o = pop(t, tw - 0.15, 0.4)
        chip(cv, w_, (1200, 1384)[i], 800, o * (1 - fo), TEAL, 34, anchor='l')
    s, o = pop(t, WT('p6', '第三个问题'), 0.5)
    label(cv, '这一期：别人怎么看我', 1200, 800, 40, GOLD, o, 'serif_black', glow=0.3, anchor='l')


def sc_envy(cv, t):
    bg(cv, t, (0.07, 0.065, 0.06))
    if t < T('p9') - 0.1:
        a = ease(lin(t, T('p7') - 0.2, T('p7') + 0.5))
        panel(cv, 'munger.jpg', 0, 0, 960, H, a, 1.1, 0.5, 0.35, sat=0.2, warm=0.45, contrast=1.1, gain=0.75)
        side_fade(cv, 960)
        label(cv, '查理 · 芒格', 1000, 230, 46, GOLD, a, 'serif_black', anchor='l')
        label(cv, 'Charlie Munger', 1002, 284, 26, GREY, a, 'corm_med', anchor='l', track=0.1)
        tq = T('p8'); o = ease(lin(t, tq - 0.1, tq + 0.4))
        card(cv, 980, 340, 1860, 720, (0.10, 0.09, 0.08), 0.92 * o, GOLD, glow=0.4)
        label(cv, '“The world is not driven by greed.', 1020, 410, 34, GREY, o, 'playfair', anchor='l')
        label(cv, ' It’s driven by envy.”', 1020, 460, 34, GREY, o, 'playfair', anchor='l')
        o2 = ease(lin(t, WT('p8', '不是贪婪') - 0.2, WT('p8', '不是贪婪') + 0.2)); o3 = ease(lin(t, WT('p8', '嫉妒') - 0.2, WT('p8', '嫉妒') + 0.2))
        label(cv, '驱动这个世界的，不是贪婪，', 1020, 560, 46, WHITE, o2, 'serif_semi', anchor='l')
        label(cv, '而是嫉妒。', 1020, 640, 46, GOLD_HI, o3, 'serif_black', anchor='l')
        label(cv, '芒格 · 2022 年 Daily Journal 股东会', 1000, 790, 26, GREY, o, 'sans_med', anchor='l')
        o7 = ease(lin(t, T('p7') - 0.2, T('p7') + 0.3)) * (1 - o)
        label(cv, '人为什么这么在乎别人的眼光？', 1410, 530, 44, WHITE, o7, 'serif_semi')
        credit(cv, 'munger', a)
        return
    a = ease(lin(t, T('p9') - 0.2, T('p9') + 0.3))
    tsw = WT('p9', '在乎地位') - 0.3
    clip, t0 = (CLIPS['dfd_crowd'], T('p9') - 0.2) if t < tsw else (CLIPS['dfd_car'], tsw)
    vpanel(cv, clip, t, t0, 120, 150, 1000, 810, a, zoom=1.02, z1=1.1, dur=5, edge=(0.75, 0.66, 0.50), sat=0.85, warm=0.35, contrast=1.08, gain=0.95)
    label(cv, '1956', CX2, 260, 64, GOLD, a, 'oswald')
    label(cv, '通用汽车 Motorama 车展', CX2, 350, 34, WHITE, a, 'sans_bold')
    for i, (w_, key) in enumerate((('被高看一眼', '高看一眼'), ('机会', '机会'), ('资源', '资源'))):
        s, o = pop(t, WT('p9', key) - 0.1, 0.4)
        chip(cv, w_, CX2, 480 + i * 110, o, GOLD, 40)
    source(cv, '影片：Design for Dreaming（1956），Prelinger Archives，公有领域', a)


def sc_signal(cv, t):
    bg(cv, t, (0.06, 0.06, 0.09))
    hx, hy = 680, 520
    if t < T('p13') - 0.15:
        a = ease(lin(t, T('p10') - 0.2, T('p10') + 0.4))
        L = layer(); V.silhouette(L, hx, hy, 0.85); stroke_layer(cv, L, (0.70, 0.74, 0.82), a * 0.85, glow=0.4)
        for i, w_ in enumerate(('收入', '能力', '品位')):
            tw = WT('p10', w_); o = ease(lin(t, tw - 0.1, tw + 0.3)) * (1 - 0.85 * ease(lin(t, WT('p10', '藏在'), WT('p10', '藏在') + 0.8)))
            label(cv, w_, hx, 470 + i * 76, 38, GOLD_HI, o, 'sans_bold')
        k = lin(t, T('p11') - 0.1, T('p12'))
        head = (hx, hy - 212)
        if k > 0:
            for j in range(3):
                ph = (k * 1.6 + j / 3) % 1
                L = layer(); circle(L, head, 30 + 380 * ph, 3); stroke_layer(cv, L, GOLD, (1 - ph) * 0.8 * ease(k * 4), glow=1.2)
            L = layer(); circle(L, head, 18, fill=True); stroke_layer(cv, L, GOLD_HI, ease(k * 4), glow=2)
            label(cv, '信号', 1360, 470, 72, GOLD, ease(lin(t, WT('p11', '信号') - 0.2, WT('p11', '信号') + 0.2)) * (1 - ease(lin(t, HIT['costly'] - 0.4, HIT['costly'] - 0.15))), 'serif_black', glow=0.4)
        o9 = ease(lin(t, WT('p10', '看不见') - 0.2, WT('p10', '看不见') + 0.3)) * (1 - ease(lin(t, T('p11') - 0.3, T('p11'))))
        label(cv, '地位，看不见', 1360, 470, 56, WHITE, o9, 'serif_black')
        s, o = pop(t, HIT['costly'] - 0.1, 0.5)
        if o > 0:
            dim(cv, 1 - 0.55 * o)
            big(cv, '有代价', 1360, 440, 150, a=o, scale=0.9 + 0.1 * s, grad=GOLDG, glow=0.7)
            label(cv, '谁都能轻松发出的信号，没人当真', 1360, 600, 36, WHITE, ease(lin(t, WT('p12', '谁都能') - 0.2, WT('p12', '谁都能') + 0.3)), 'sans_bold')
        return
    a = ease(lin(t, T('p13') - 0.15, T('p13') + 0.3))
    vframe_h(cv, CLIPS['peacock'], t, T('p13') - 0.15, 80, 150, 1120, a, 1.15, 1.25, 6, sat=1.0, warm=0.1, contrast=1.08, gain=0.95)
    for i, (w_, key) in enumerate((('又长', '又长'), ('又重', '又重'), ('招来天敌', '天敌'))):
        s, o = pop(t, WT('p13', key) - 0.1, 0.4)
        chip(cv, w_, 1560, 250 + i * 110, o, WHITE, 38, (0.06, 0.06, 0.08))
    o = ease(lin(t, WT('p13', '负担不起') - 0.3, WT('p13', '负担不起') + 0.2))
    label(cv, '扎哈维 1975 · 累赘原理', 1560, 640, 32, GOLD_HI, o, 'sans_bold')
    label(cv, 'Handicap Principle', 1560, 690, 28, GOLD, o, 'corm_med', track=0.1)
    credit(cv, 'v_peacock', a)


def sc_forces(cv, t):
    """p14–p17 三股力量：左半实拍（新机发售 / Labubu 快闪店人潮 / 会员店），右侧三张卡逐张点亮 → p18 不是凡勃伦效应"""
    bg(cv, t, (0.06, 0.06, 0.08))
    if t < T('p18') - 0.2:
        a = ease(lin(t, T('p14') - 0.2, T('p14') + 0.4))
        k, wk = V.force_bg(cv, t, a, 0, 0, W, H)
        L = layer(); x = np.linspace(0, 1, W, dtype=np.float32)[None, :, None]
        cv *= (1 - 0.75 * np.clip((x - 0.35) / 0.25, 0, 1))
        label(cv, '多付的钱，来自三股力量', 1360, 200, 52, WHITE, a, 'serif_black')
        for i, (lid, n, d, col, key) in enumerate(V.FORCES):
            s, o = pop(t, WT(lid, key) - 0.15, 0.45); y = 340 + i * 190
            card(cv, 900, y - 80, 1820, y + 80, (0.07, 0.07, 0.08), 0.9 * o, col, r=14, glow=0.6)
            label(cv, '第%s股' % '一二三'[i], 950, y - 30, 24, GREY, o, 'sans_med', anchor='l')
            label(cv, n, 950, y + 18, 46, col, o, 'sans_black', anchor='l')
            od = ease(lin(t, WT(lid, key) + 0.3, WT(lid, key) + 0.8))
            label(cv, d, 1790, y + 18, 28, WHITE, o * od, 'sans_med', anchor='r')
        credit(cv, k, a * wk)
        return
    a = ease(lin(t, T('p18') - 0.2, T('p18') + 0.4))
    if os.path.exists(os.path.join(MEDIA, 'veblen.jpg')):
        panel(cv, 'veblen.jpg', 0, 0, 760, H, a, 1.0, 0.5, 0.35, sat=0.0, contrast=1.1, gain=0.85)
        side_fade(cv, 760, 0.6)
        credit(cv, 'veblen', a)
    else:
        big(cv, '这不是', 400, 400, 90, a=a, color=WHITE, glow=0.2)
        big(cv, '凡勃伦效应', 400, 540, 100, a=a, grad=GOLDG, glow=0.5)
    label(cv, '托斯丹 · 凡勃伦（1857–1929）', 400, 860, 32, WHITE, a, 'serif_semi')
    o1 = ease(lin(t, WT('p18', '越贵越想买') - 0.3, WT('p18', '越贵越想买') + 0.2))
    card(cv, 820, 280, 1300, 640, (0.10, 0.09, 0.10), 0.92 * o1, RED, r=14, glow=0.4)
    label(cv, '凡勃伦效应', 1060, 360, 40, (1.0, 0.65, 0.58), o1, 'sans_black')
    label(cv, '越贵 → 越想买', 1060, 450, 36, WHITE, o1, 'sans_bold')
    label(cv, '贵本身就是目的', 1060, 530, 30, GREY, o1, 'sans_med')
    kx = ease(lin(t, WT('p18', '这里') - 0.2, WT('p18', '这里') + 0.3))
    if kx > 0:
        L = layer(); circle(L, (1290, 290), 30, fill=True); fill(cv, L, RED, kx * o1)
        L = layer(); cx_, cy_ = 1290, 290; line(L, (cx_ - 12, cy_ - 12), (cx_ + 12, cy_ + 12), 5); line(L, (cx_ - 12, cy_ + 12), (cx_ + 12, cy_ - 12), 5); fill(cv, L, WHITE, kx * o1)
    o2 = ease(lin(t, WT('p18', '为了信号') - 0.3, WT('p18', '为了信号') + 0.2))
    card(cv, 1360, 280, 1840, 640, (0.12, 0.10, 0.07), 0.92 * o2, GOLD, r=14, glow=0.6)
    label(cv, '这里的溢价', 1600, 360, 40, GOLD, o2, 'sans_black')
    label(cv, '为了信号', 1600, 450, 44, GOLD_HI, o2, 'sans_black')
    label(cv, '不是为了贵本身', 1600, 530, 30, GREY, o2, 'sans_med')
    label(cv, '凡勃伦效应：越贵越想买；这里：为了信号', 1330, 760, 34, GREY, ease(lin(t, WT('p18', '为了信号') - 0.1, WT('p18', '为了信号') + 0.4)), 'sans_med')


def sc_formula(cv, t):
    bg(cv, t, (0.07, 0.065, 0.06)); DUST.draw(cv, t, GOLD, 0.25)
    a = ease(lin(t, T('p19') - 0.2, T('p19') + 0.4))
    label(cv, '三股力量叠在一起', W / 2, 180, 34, GREY, a, 'sans_med')
    s, o = pop(t, WT('p19', '大众地位') - 0.15, 0.5)
    big(cv, '大众地位象征型品牌', W / 2, 270, 76, a=o, scale=0.94 + 0.06 * s, grad=GOLDG, glow=0.5)
    oc = ease(lin(t, WT('p20', '乘法') - 0.3, WT('p20', '乘法') + 0.2))
    for i, (lid, n, d, col, key) in enumerate(V.FORCES):
        chip(cv, n, W / 2 + (i - 1) * 320, 560, a * (1 - ease(lin(t, T('p20') - 0.4, T('p20')))), col, 44)
    label(cv, '护城河的强弱 =', 420, 380, 36, WHITE, oc, 'sans_bold', anchor='l')
    kd = V.factor_bars(cv, t, a, 420, 1500, (470, 560, 650, 740), 'p20', 'p21', 1, lab_w=260, size=38)
    ores = ease(lin(t, T('p21') - 0.3, T('p21') + 0.2)); vres = 0.53 * (1 - 0.94 * kd)
    label(cv, '护城河', 1600, 560, 40, GOLD, ores, 'serif_black')
    L = layer(); rect(L, 1570, 620, 1630, 820, r=12); fill(cv, L, (0.20, 0.21, 0.24), 0.9 * ores)
    L = layer(); rect(L, 1570, 820 - 200 * vres, 1630, 820, r=12); fill(cv, L, mix(GOLD, RED, kd), 0.95 * ores)
    label(cv, '任何一项接近零，整条护城河就接近零', W / 2, 860, 36, (1.0, 0.70, 0.62), ease(lin(t, WT('p21', '整条') - 0.3, WT('p21', '整条') + 0.2)), 'sans_bold')


def sc_paradox(cv, t):
    bg(cv, t, (0.07, 0.06, 0.08))
    if t < T('p23') + 0.1:
        a = ease(lin(t, T('p22') - 0.2, T('p22') + 0.4)) * (1 - ease(lin(t, T('p23') - 0.3, T('p23') + 0.1)))
        label(cv, '几项天生互相拉扯', W / 2, 180, 36, GREY, a, 'sans_med')
        big(cv, '地位是相对的', W / 2, 270, 72, a=a * ease(lin(t, WT('p22', '相对') - 0.3, WT('p22', '相对') + 0.2)), color=WHITE, glow=0.2)
        k1 = ease(lin(t, WT('p22', '人人都有') - 0.2, WT('p22', '人人都有') + 0.4)); k2 = ease(lin(t, WT('p22', '谁都没有') - 0.2, WT('p22', '谁都没有') + 0.5))
        for i in range(9):
            x = W / 2 + (i - 4) * 130; me = i == 4
            up = (1.0 if me else k1) * (1 - k2); y = 560 - 70 * up
            col = mix(mix((0.42, 0.44, 0.50), GOLD, up), (0.42, 0.44, 0.50), k2)
            L = layer(); circle(L, (x, y - 60), 26, fill=True); rect(L, x - 30, y - 24, x + 30, y + 80, r=14)
            fill(cv, L, col, a * (0.9 if (me or k1 > 0.5) and k2 < 0.5 else 0.55))
        t1, t2 = WT('p22', '人人都有'), WT('p22', '谁都没有')
        la = 1 - ease(lin(t, t1 - 0.5, t1 - 0.25)); lb = ease(lin(t, t1 - 0.25, t1)) * (1 - ease(lin(t, t2 - 0.5, t2 - 0.25))); lc = ease(lin(t, t2 - 0.25, t2))
        label(cv, '一个人出众', W / 2, 780, 40, GOLD_HI, a * la, 'sans_bold')
        label(cv, '人人都有', W / 2, 780, 44, GOLD, a * lb, 'sans_black')
        label(cv, '= 谁都没有', W / 2, 780, 44, GREY, a * lc, 'sans_black')
        return
    if t < T('p24') - 0.1:
        a = ease(lin(t, T('p23') - 0.1, T('p23') + 0.3))
        k = ease(lin(t, T('p23'), SE('p23')))
        n = int(8 + 150 * k); rng = np.random.default_rng(9)
        L = layer()
        for i in range(160):
            x = 640 + rng.normal(0, 230); y = 500 + rng.normal(0, 120)
            if i < n: circle(L, (x, y), 7, fill=True)
        fill(cv, L, (0.66, 0.70, 0.78), 0.85 * a)
        L = layer(); circle(L, (640, 500), 20, fill=True); stroke_layer(cv, L, GOLD_HI, a * (1 - 0.8 * k), glow=3.0 * (1 - 0.8 * k))
        label(cv, '买得起的人越多', 1400, 330, 40, TEAL, a, 'sans_bold')
        label(cv, '→ 拥有的人越多', 1400, 400, 40, TEAL, a, 'sans_bold')
        label(cv, '→ 区分越薄', 1400, 480, 48, (1.0, 0.70, 0.62), ease(lin(t, WT('p23', '区分') - 0.3, WT('p23', '区分') + 0.2)), 'sans_black')
        L = layer(); rect(L, 1180, 600, 1680, 630, r=15); fill(cv, L, (0.2, 0.21, 0.24), 0.9 * a)
        L = layer(); rect(L, 1180, 600, 1180 + 500 * (1 - 0.85 * k), 630, r=15); fill(cv, L, GOLD, 0.95 * a)
        label(cv, '区分', 1140, 615, 30, GOLD, a, 'sans_bold', anchor='r')
        return
    a = ease(lin(t, T('p24') - 0.2, T('p24') + 0.4))
    big(cv, '要同时管好三件事', W / 2, 190, 64, a=a, color=WHITE, glow=0.2)
    P = {'被认可': (560, 420, COLD), '有区分': (1360, 420, GOLD), '买得起': (960, 720, TEAL)}
    ke = eout(lin(t, T('p24'), T('p24') + 1.4)); u = t - T('p24')
    vib = 6 * math.sin(u * 30) * math.exp(-u * 1.2)
    L = layer()
    for p0, p1 in (('被认可', '有区分'), ('被认可', '买得起'), ('有区分', '买得起')):
        (x0, y0, _), (x1, y1, _) = P[p0], P[p1]
        pts = [(x0 + (x1 - x0) * s_ * ke, y0 + (y1 - y0) * s_ * ke + vib * math.sin(math.pi * s_)) for s_ in np.linspace(0, 1, 24)]
        poly(L, pts, 4)
    stroke_layer(cv, L, mix(GOLD, RED, 0.5), a, glow=1.2)
    for n, (x, y, col) in P.items():
        s, o = pop(t, WT('p24', n) - 0.15, 0.45)
        L = layer(); circle(L, (x, y), 56, fill=True); fill(cv, L, (0.07, 0.07, 0.09), 0.95 * o)
        L = layer(); circle(L, (x, y), 56, 4); stroke_layer(cv, L, col, o, glow=1.2)
        lx = x - 210 if n == '被认可' else (x + 210 if n == '有区分' else x + 220)
        label(cv, n, lx, y, 46, col, o, 'sans_black', scale=0.9 + 0.1 * s)
    s, o = pop(t, WT('p24', '护城河') - 0.3, 0.5)
    big(cv, '长期管好，才守得住', W / 2, 860, 50, a=o, grad=GOLDG, glow=0.4)


# ═══════════════════════ 02 · 一把尺子 ═══════════════════════
def sc_ruler(cv, t):
    bg(cv, t, (0.07, 0.07, 0.08))
    if t < T('d2') - 0.1:
        a = ease(lin(t, T('d1') - 0.2, T('d1') + 0.4))
        big(cv, '身份溢价', 620, CY, 120, a=a, grad=GOLDG)
        label(cv, '→', 960, CY, 80, GREY, a, 'sans_med')
        big(cv, '护城河？', 1290, CY, 120, a=ease(lin(t, WT('d1', '护城河') - 0.2, WT('d1', '护城河') + 0.2)), color=WHITE, glow=0.2)
        return
    if t < T('d4') - 0.1:
        a = ease(lin(t, T('d2') - 0.2, T('d2') + 0.4))
        panel(cv, 'buffett_2015.jpg', 0, 0, 960, H, a, 1.1, 0.36, 0.35, sat=0.25, warm=0.5, contrast=1.1, gain=0.8)
        side_fade(cv, 960)
        label(cv, '沃伦 · 巴菲特', 1000, 230, 46, GOLD, a, 'serif_black', anchor='l')
        label(cv, 'Warren Buffett', 1002, 284, 26, GREY, a, 'corm_med', anchor='l', track=0.1)
        o = ease(lin(t, WT('d2', '评估') - 0.2, WT('d2', '评估') + 0.3))
        card(cv, 980, 340, 1860, 720, (0.10, 0.09, 0.08), 0.92 * o, GOLD, glow=0.4)
        label(cv, '评估一家企业，最重要的是', 1020, 410, 42, WHITE, o, 'serif_semi', anchor='l')
        big(cv, '定价权', 1020 + text_w('评估一家企业，最重要的是', 'serif_semi', 42) + 96, 410, 52,
            a=ease(lin(t, WT('d2', '定价权') - 0.2, WT('d2', '定价权') + 0.2)), grad=GOLDG, glow=0.4)
        o2 = ease(lin(t, T('d3') - 0.1, T('d3') + 0.3))
        label(cv, '涨价十分之一美分之前，都得先祷告一番，', 1020, 540, 38, GREY, o2, 'serif_semi', anchor='l')
        label(cv, '那就是糟糕的生意。', 1020, 610, 38, (1.0, 0.65, 0.58), ease(lin(t, WT('d3', '糟糕') - 0.2, WT('d3', '糟糕') + 0.2)), 'serif_semi', anchor='l')
        label(cv, '巴菲特 · 2010 年 5 月接受美国金融危机调查委员会（FCIC）访谈', 1000, 790, 24, GREY, o, 'sans_med', anchor='l')
        credit(cv, 'buffett_2015', a)
        return
    a = ease(lin(t, T('d4') - 0.1, T('d4') + 0.4))
    label(cv, '身份溢价', W / 2, 200, 56, WHITE, a, 'serif_black')
    o1 = ease(lin(t, WT('d4', '守住') - 0.2, WT('d4', '守住') + 0.2)); o2 = ease(lin(t, WT('d4', '往上提') - 0.2, WT('d4', '往上提') + 0.2))
    chip(cv, '长期守住', 800, 310, o1, TEAL, 38); chip(cv, '还能往上提', 1120, 310, o2, GOLD, 38)
    o3 = ease(lin(t, WT('d4', '三道关') - 0.3, WT('d4', '三道关') + 0.2))
    gates(cv, t, o3, -1, y=480)
    for i, (txt, key) in enumerate((('可见性 · 识别度', '认得出'), ('溢价可不可信', '仿不了'), ('可及 vs 区分', '稀释不了'))):
        o = ease(lin(t, WT('d5', key) - 0.2, WT('d5', key) + 0.3))
        label(cv, txt, W / 2 + (i - 1) * 330, 680, 30, GOLD_HI, o, 'sans_bold')
    label(cv, '三道关', W / 2, 800, 60, GOLD, o3 * (1 - ease(lin(t, T('d5') - 0.3, T('d5')))), 'serif_black', glow=0.4)
    label(cv, '对应刚才的乘法', W / 2, 800, 34, GREY, ease(lin(t, T('d5') - 0.1, T('d5') + 0.4)), 'sans_med')


# ═══════════════════════ 03 · 三道关 ═══════════════════════
def gate_title(cv, t, i, lid, compact_after):
    k = ease(lin(t, compact_after - 0.3, compact_after + 0.3))
    s, o = pop(t, HIT['gate_' + lid] - 0.15, 0.5)
    name = ('认得出', '仿不了', '稀释不了')[i]; num = ('第一关', '第二关', '第三关')[i]
    y = CY + (150 - CY) * k; sz = 150 - 76 * k
    label(cv, num, W / 2, y - sz * 0.85, 44 - 14 * k, GREY, o, 'sans_bold', track=0.2)
    big(cv, name, W / 2, y + 10, sz, a=o, scale=0.9 + 0.1 * s, grad=GOLDG, glow=0.6 - 0.3 * k)


def sc_gate1(cv, t):
    bg(cv, t, (0.06, 0.07, 0.09))
    gate_title(cv, t, 0, 'k1', T('k2'))
    if t < T('k4') - 0.1:
        a = ease(lin(t, T('k2') + 0.1, T('k2') + 0.5))
        ex, ey = W / 2, 290
        L = layer(); poly(L, [(ex - 90, ey), (ex, ey - 46), (ex + 90, ey), (ex, ey + 46)], 4, closed=True); circle(L, (ex, ey), 22, fill=True)
        stroke_layer(cv, L, WHITE, a, glow=0.8)
        sweep = math.sin((t - T('k2')) * 1.6) * 0.5
        tx = W / 2 - 120 + 560 * sweep
        L = layer(); fpoly(L, [(ex, ey + 40), (tx - 170, 720), (tx + 170, 720)]); fill(cv, cv2.GaussianBlur(L, (0, 0), 18), GOLD, 0.16 * a)
        for x, n in ((660, '手机'), (860, '包')):
            lit = 0.35 + 0.65 * math.exp(-((x - tx) / 160) ** 2)
            L = layer(); rect(L, x - 55, 580, x + 55, 710, fill=False, w=4, r=12); stroke_layer(cv, L, GOLD, a * lit, glow=lit)
            label(cv, n, x, 755, 30, WHITE, a * lit, 'sans_med')
        o3 = ease(lin(t, T('k3') - 0.2, T('k3') + 0.3))
        card(cv, 1140, 570, 1460, 720, (0.05, 0.05, 0.06), 0.95 * o3, (0.30, 0.32, 0.36), r=8, glow=0.0)
        L = layer(); line(L, (1260, 645), (1340, 645), 5); stroke_layer(cv, L, (0.30, 0.32, 0.36), o3)
        label(cv, '放在家里', 1300, 765, 30, GREY, o3, 'sans_med')
        label(cv, '再贵，也没人看见', W / 2, 850, 40, GREY, ease(lin(t, WT('k3', '再贵') - 0.2, WT('k3', '再贵') + 0.3)), 'sans_bold')
        return
    if t < T('k5') - 0.1:
        a = ease(lin(t, T('k4') - 0.2, T('k4') + 0.3))
        panel(cv, 'iphone_line.jpg', 100, 250, 1120, 830, a, 1.05, 0.5, 0.5, edge=ORANGE, sat=0.9, warm=0.1, gain=0.85)
        o = ease(lin(t, WT('k4', '爱马仕橙') - 0.2, WT('k4', '爱马仕橙') + 0.3))
        label(cv, '一眼认出：', 1500, 430, 46, ORANGE, o, 'sans_black')
        label(cv, '今年的新款 Pro', 1500, 505, 46, ORANGE, o, 'sans_black')
        oa = ease(lin(t, WT('k4', '分析') - 0.2, WT('k4', '分析') + 0.3))
        label(cv, '有分析认为：一眼能认出新款，', 1500, 620, 28, GREY, oa, 'sans_med')
        label(cv, '是“爱马仕橙”走红的原因之一', 1500, 665, 28, GREY, oa, 'sans_med')
        credit(cv, 'iphone_line', a)
        return
    if t < T('k6') - 0.1:
        a = ease(lin(t, T('k5') - 0.2, T('k5') + 0.3))
        panel(cv, V.img('iphone17_launch2', 'iphone_back.jpg'), 0, 0, W, H, a, 1.05, 0.5, 0.5, sat=0.7, warm=0.1, gain=0.30)
        label(cv, '苹果传递的信号', W / 2, 230, 48, WHITE, a, 'serif_black')
        o1 = ease(lin(t, WT('k5', '不是') - 0.2, WT('k5', '不是') + 0.3))
        chip(cv, '“我很有钱”', W / 2, 350, o1, GREY, 44, (0.10, 0.10, 0.12))
        ks = ease(lin(t, WT('k5', '而是') - 0.3, WT('k5', '而是'))); wv = text_w('“我很有钱”', 'sans_bold', 44) + 60
        L = layer(); line(L, (W / 2 - wv / 2, 350), (W / 2 - wv / 2 + wv * ks, 350), 5); stroke_layer(cv, L, RED, ks * o1, glow=0.5)
        for i, (w_, key) in enumerate((('有一定的消费能力', '消费能力'), ('在乎品质', '品质'), ('过着体面的生活', '体面'))):
            s, o = pop(t, WT('k5', key) - 0.2, 0.45); x = W / 2 + (i - 1) * 560
            card(cv, x - 250, 520, x + 250, 660, (0.12, 0.10, 0.07), 0.9 * o, GOLD, r=14, glow=0.5)
            label(cv, w_, x, 590, 42, GOLD_HI, o, 'sans_black', scale=0.92 + 0.08 * s)
        credit(cv, V.cred_key('iphone17_launch2', 'iphone_back.jpg'), a)
        return
    a = ease(lin(t, T('k6') - 0.2, T('k6') + 0.3))
    label(cv, '多数人买苹果是为了面子？', W / 2, 300, 44, WHITE, a, 'sans_bold')
    o = ease(lin(t, WT('k6', '没有证据') - 0.3, WT('k6', '没有证据') + 0.2))
    big(cv, '没有证据', W / 2, 410, 72, a=o, color=(1.0, 0.65, 0.58), glow=0.2)
    for i, (w_, key) in enumerate((('好用的产品', '产品'), ('生态', '生态'))):
        s, oo = pop(t, WT('k6', key) - 0.15, 0.45)
        chip(cv, w_, (800, 1120)[i], 540, oo, (0.75, 0.78, 0.85), 40, (0.10, 0.10, 0.12))
    s, o2 = pop(t, WT('k6', '确实存在') - 0.4, 0.5)
    card(cv, 520, 650, 1400, 800, (0.12, 0.10, 0.07), 0.92 * o2, GOLD, r=16, glow=0.8)
    label(cv, '能确定的：身份这份动机，确实存在', W / 2, 725, 40, GOLD_HI, o2, 'sans_black')


def sc_gate2(cv, t):
    bg(cv, t, (0.07, 0.06, 0.07))
    gate_title(cv, t, 1, 'k7', T('k8'))
    if t < T('k10') - 0.1:
        o1 = ease(lin(t, WT('k8', '两种') - 0.2, WT('k8', '两种') + 0.3))
        label(cv, '暂时的', 480, 265, 42, (1.0, 0.62, 0.55), o1, 'sans_black')
        label(cv, '长久的', 1440, 265, 42, GOLD, o1 * 0.45, 'sans_black')
        L = layer(); line(L, (W / 2, 240), (W / 2, 860), 2); stroke_layer(cv, L, GREY, o1 * 0.5)
        o2 = ease(lin(t, T('k9') - 0.2, T('k9') + 0.3))
        panel(cv, 'no_labubu.jpg', 110, 330, 560, 800, o2, 1.15, 0.5, 0.5, edge=RED, sat=0.8, warm=0.1, gain=0.85)
        chip(cv, '产能跟不上', 760, 470, ease(lin(t, WT('k9', '产能') - 0.2, WT('k9', '产能') + 0.2)), RED, 34, (0.14, 0.06, 0.06))
        chip(cv, '黄牛在囤货', 760, 580, ease(lin(t, WT('k9', '黄牛') - 0.2, WT('k9', '黄牛') + 0.2)), RED, 34, (0.14, 0.06, 0.06))
        label(cv, '门店告示：“我们不卖 Labubu”', 335, 845, 24, GREY, o2, 'sans_med')
        L = layer(); rect(L, 1080, 330, 1800, 800, fill=False, w=2); stroke_layer(cv, L, GREY, o1 * 0.35)
        label(cv, '？', 1440, 565, 90, GREY, o1 * 0.4, 'serif_black')
        credit(cv, 'no_labubu', o2)
        return
    if t < T('k11') - 0.1:
        a = ease(lin(t, T('k10') - 0.2, T('k10') + 0.3))
        label(cv, '2025.6.18 · LABUBU 3.0 全渠道补货', W / 2, 255, 38, WHITE, a, 'sans_black')
        x0, x1, y0, y1 = 360, 1560, 330, 770; sx = (x1 - x0) / 800
        L = layer(); line(L, (x0, y1), (x1, y1), 2); line(L, (x0, y0), (x0, y1), 2); stroke_layer(cv, L, GREY, a * 0.6)
        tc = HIT['crash']; kk = eout(lin(t, T('k10') + 0.4, tc + 0.3))
        def Y(v): return y1 - (v / 3000) * (y1 - y0)
        hi = [(x0 + 20 * sx, Y(2600)), (x0 + 140 * sx, Y(2300)), (x0 + 260 * sx, Y(2750)), (x0 + 380 * sx, Y(2450)), (x0 + 460 * sx, Y(2500))]
        lo = [(x0 + 520 * sx, Y(800)), (x0 + 620 * sx, Y(720)), (x0 + 740 * sx, Y(690)), (x0 + 800 * sx, Y(660))]
        pts = hi + lo; m = max(2, int(len(pts) * kk))
        L = layer(); poly(L, pts[:m], 5); stroke_layer(cv, L, mix(GOLD, RED, ease(lin(t, tc - 0.4, tc))), a, glow=1.0)
        L = layer()
        for y in range(y0, y1, 24): line(L, (x0 + 490 * sx, y), (x0 + 490 * sx, y + 12), 2)
        stroke_layer(cv, L, WHITE, a * 0.5)
        label(cv, '补货前', x0 + 230 * sx, y1 + 38, 28, GREY, a, 'sans_med'); label(cv, '补货当天', x0 + 660 * sx, y1 + 38, 28, GREY, a, 'sans_med')
        label(cv, '1500~2800 元', x0 + 240 * sx, Y(2900) - 18, 32, GOLD_HI, a, 'sans_bold')
        o = ease(lin(t, tc - 0.3, tc + 0.1))
        label(cv, '650~800 元', x0 + 660 * sx, Y(1150), 32, (1.0, 0.65, 0.58), o, 'sans_bold')
        s, o2 = pop(t, tc - 0.1)
        label(cv, '当天跌去一半以上', 1700, 540, 46, RED, o2, 'sans_black', glow=0.3, anchor='r')
        source(cv, '热门款二手成交价，据媒体统计（第一财经、财联社等）', a)
        return
    if t < T('k12') - 0.1:
        a = ease(lin(t, T('k11') - 0.2, T('k11') + 0.3))
        panel(cv, 'lafufu.jpg', 140, 240, 620, 800, a, 1.05, 0.5, 0.45, edge=RED, sat=0.85, gain=0.85)
        label(cv, '假 Labubu（俗称 Lafufu）', 380, 845, 26, GREY, a, 'sans_med')
        tn = WT('k11', '九成'); n = int(100 * ease(lin(t, T('k11') + 0.5, tn)))
        L1 = layer(); L2 = layer()
        for i in range(100):
            x = 760 + (i % 10) * 46; y = 290 + (i // 10) * 50
            if i < n: circle(L1 if i < 90 else L2, (x, y), 14, fill=True)
        fill(cv, L1, (0.85, 0.30, 0.27), 0.9 * a); fill(cv, L2, (0.60, 0.62, 0.66), 0.9 * a)
        o = ease(lin(t, tn - 0.2, tn + 0.3))
        stat(cv, 1560, 450, '90%', '', o, col=RED, size=120, grad=REDG)
        label(cv, '英国边境查获的假冒玩具', 1560, 580, 30, WHITE, o, 'sans_bold')
        label(cv, '是假 Labubu（23.6 万件）', 1560, 630, 30, WHITE, o, 'sans_bold')
        source(cv, '英国知识产权局（IPO）2025 年 9 月数据', a)
        credit(cv, 'lafufu', a)
        return
    if t < T('k13') - 0.1:
        a = ease(lin(t, T('k12') - 0.2, T('k12') + 0.3)); c = (W / 2, 535); R = 250
        nodes = ['二手价 ↓', '信号贬值', '想要的人 ↓', '更没人炒']
        for i, n in enumerate(nodes):
            ang = -math.pi / 2 + i * math.pi / 2
            x, y = c[0] + R * 1.5 * math.cos(ang), c[1] + R * math.sin(ang)
            o = ease(lin(t, T('k12') + i * 0.5, T('k12') + i * 0.5 + 0.4)) * a
            card(cv, x - 130, y - 44, x + 130, y + 44, (0.14, 0.06, 0.06), 0.95 * o, RED, r=44, glow=0.4)
            label(cv, n, x, y, 34, WHITE, o, 'sans_bold')
        L = layer()
        for i in range(4):
            a0 = i * 90 + 30; a1 = a0 + 30
            pts = [(c[0] + 1.5 * R * math.sin(math.radians(d)), c[1] - R * math.cos(math.radians(d))) for d in np.linspace(a0, a1, 16)]
            poly(L, pts, 4); arrow(L, pts[-2], pts[-1], 4, 16)
        stroke_layer(cv, L, RED, a * 0.9, glow=0.8)
        label(cv, '当二手价本身就是信号', W / 2, c[1], 40, (1.0, 0.65, 0.58), a, 'sans_bold')
        return
    if t < T('k15') - 0.1:
        a = ease(lin(t, T('k13') - 0.2, T('k13') + 0.3))
        label(cv, '长久的：对手短期内追不上', W / 2, 250, 44, GOLD, a, 'sans_black')
        o0 = ease(lin(t, T('k13') + 0.4, T('k13') + 0.9))
        panel(cv, 'birkin2.jpg', 110, 320, 1050, 820, o0, 1.05, 0.5, 0.5, edge=GOLD, sat=0.95, warm=0.45, gain=0.85)
        t1 = WT('k14', '十八个月'); o1 = ease(lin(t, t1 - 0.4, t1))
        stat(cv, 1480, 390, '18', '个月+', o1, size=110, usize=40, grad=GOLDG)
        label(cv, '工匠入职培训', 1480, 480, 30, WHITE, o1, 'sans_med')
        t2 = WT('k14', '工坊'); o2 = ease(lin(t, t2 - 0.2, t2 + 0.3))
        label(cv, '新皮具工坊', 1480, 575, 32, WHITE, o2, 'sans_bold')
        for i, (yr, place, key) in enumerate((('2026', 'Loupes', '一座'), ('2027', 'Charleville', '一座'), ('2028', 'Colombelles', '计划'), ('2030', 'Les Andelys', '二零三零'))):
            tt = t2 + 0.35 * i if key != '二零三零' else WT('k14', '二零三零') - 0.2
            oo = ease(lin(t, tt, tt + 0.3)) * o2
            label(cv, yr, 1340, 640 + i * 55, 34, GOLD_HI, oo, 'oswald', anchor='l')
            label(cv, place, 1440, 640 + i * 55, 28, GREY, oo, 'corm_med', anchor='l')
        source(cv, '爱马仕官网（École Hermès des savoir-faire）、2025 年度业绩公告', o0)
        credit(cv, 'birkin2', o0)
        return
    if t < WT('k15', '稀缺只是结果') - 0.2:
        a = ease(lin(t, T('k15') - 0.2, T('k15') + 0.3))
        panel(cv, 'hermes_paris.jpg', 0, 0, W, H, a, 1.1, 0.5, 0.5, sat=0.6, warm=0.4, gain=0.3)
        card(cv, 400, 250, 1520, 760, (0.10, 0.09, 0.08), 0.92 * a, GOLD, glow=0.5)
        label(cv, '“Scarcity is not a goal for us.”', W / 2, 340, 44, GREY, a, 'playfair')
        o = ease(lin(t, WT('k15', '稀缺') - 0.2, WT('k15', '稀缺') + 0.3))
        big(cv, '稀缺，从来不是', W / 2, 480, 76, a=o, color=WHITE, glow=0.1)
        big(cv, '我们的目标', W / 2, 590, 76, a=ease(lin(t, WT('k15', '目标') - 0.3, WT('k15', '目标'))), grad=GOLDG, glow=0.5)
        label(cv, '— 纪尧姆 · 德塞纳（爱马仕执行副总裁）· The National，2025.10', W / 2, 705, 26, GREY, a, 'sans_med')
        credit(cv, 'hermes_paris', a)
        return
    if t < T('k16') - 0.1:
        tk = WT('k15', '稀缺只是结果'); a = ease(lin(t, tk - 0.2, tk + 0.3))
        big(cv, '稀缺只是结果', W / 2, 270, 84, a=a, grad=GOLDG, glow=0.4)
        o1 = ease(lin(t, WT('k15', '想多做') - 0.2, WT('k15', '想多做') + 0.2)); o2 = ease(lin(t, WT('k15', '想模仿') - 0.2, WT('k15', '想模仿') + 0.2))
        chip(cv, '想多做：快不起来', 700, 410, o1, GOLD, 40); chip(cv, '想模仿：买不来积累', 1220, 410, o2, GOLD, 40)
        kk = eout(lin(t, WT('k15', '两百年') - 1.2, WT('k15', '积累', end=True)))
        L = layer(); line(L, (460, 660), (460 + 1000 * kk, 660), 5); stroke_layer(cv, L, GOLD, a * o2, glow=1.4)
        label(cv, '1837', 460, 720, 40, GOLD_HI, o2, 'oswald'); label(cv, '2026', 1460, 720, 40, WHITE, o2 * ease(kk * 3 - 2), 'oswald')
        label(cv, '将近两百年', W / 2, 600, 40, WHITE, o2 * ease(kk * 2 - 1), 'sans_bold')
        return
    a = ease(lin(t, T('k16') - 0.2, T('k16') + 0.3))
    label(cv, '大众品牌也一样', W / 2, 250, 48, WHITE, a, 'serif_black')
    o1 = ease(lin(t, WT('k16', '外观') - 0.2, WT('k16', '外观') + 0.3)); o2 = ease(lin(t, WT('k16', '会员费') - 0.2, WT('k16', '会员费') + 0.3))
    panel(cv, V.img('iphone17_launch', 'iphone_line.jpg'), 100, 320, 940, 800, o1, 1.05, 0.5, 0.5, edge=ORANGE, sat=0.85, warm=0.1, gain=0.55)
    panel(cv, 'sams_sz.jpg', 980, 320, 1820, 800, o2, 1.25, 0.29, 0.40, edge=GOLD, sat=0.75, warm=0.2, gain=0.50)
    chip(cv, '外观：能仿', 520, 400, o1, (0.75, 0.78, 0.85), 32, (0.08, 0.08, 0.10))
    s, o = pop(t, WT('k16', '设计') - 0.2, 0.45)
    chip(cv, '设计 · 供应链 · 口碑：仿不来', 520, 730, o, GOLD, 34, (0.12, 0.10, 0.06))
    chip(cv, '会员费：谁都能收', 1400, 400, o2, (0.75, 0.78, 0.85), 32, (0.08, 0.08, 0.10))
    s, o = pop(t, WT('k16', '很难') - 0.5, 0.45)
    chip(cv, '“这里的东西都被挑过”：很难', 1400, 730, o, GOLD, 34, (0.12, 0.10, 0.06))
    k1 = V.cred_key('iphone17_launch', 'iphone_line.jpg')
    text(cv, '图：%s · %s ／ %s · %s' % (CREDIT[k1]['artist'][:16], CREDIT[k1]['license'], CREDIT['sams_sz']['artist'][:16], CREDIT['sams_sz']['license']),
         56, CRED_Y, 'sans_light', 22, GREY, anchor='l', alpha=0.75 * a)


def sc_gate3(cv, t):
    bg(cv, t, (0.06, 0.07, 0.08))
    gate_title(cv, t, 2, 'k17', T('k18'))
    if t < T('k20') - 0.1:
        a = ease(lin(t, T('k18') - 0.2, T('k18') + 0.3))
        x0, x1, y0, y1 = 360, 1560, 270, 760
        L = layer(); line(L, (x0, y1), (x1, y1), 2); line(L, (x0, y0), (x0, y1), 2); stroke_layer(cv, L, GREY, a * 0.6)
        label(cv, '用户越来越多 →', x1, y1 + 36, 28, GREY, a, 'sans_med', anchor='r')
        k = eout(lin(t, T('k18') + 0.2, WT('k18', '越少', end=True)))
        def curve(f):
            return [(x0 + (x1 - x0) * u, y1 - (y1 - y0) * f(u)) for u in np.linspace(0, k, 40)]
        rec = curve(lambda u: 0.05 + 0.85 * (1 - math.exp(-3.2 * u)))
        spc = curve(lambda u: 0.92 * math.exp(-2.2 * u) + 0.03)
        val = curve(lambda u: 0.05 + 0.85 * (1 - math.exp(-3.2 * u)) * (0.92 * math.exp(-2.2 * u) + 0.03) * 2.4)
        if len(rec) > 1:
            for pts, col, aa in ((rec, COLD, a * 0.8), (spc, RED, a * 0.8)):
                L = layer(); poly(L, pts, 3); stroke_layer(cv, L, col, aa, glow=0.4)
        ov = ease(lin(t, WT('k18', '普及') - 0.2, WT('k18', '普及') + 0.4))
        if len(val) > 1 and ov > 0:
            L = layer(); poly(L, val, 6); stroke_layer(cv, L, GOLD, ov, glow=1.4)
            label(cv, '最佳区间', x0 + (x1 - x0) * 0.33, y0 + 4, 34, GOLD_HI, ease(lin(t, WT('k18', '先增强'), WT('k18', '先增强') + 0.4)), 'sans_black')
        lg = [('— 认得出的人', COLD, a), ('— 特别感', RED, a), ('— 信号价值', GOLD, ov)]
        for i, (s_, col, aa) in enumerate(lg): label(cv, s_, 1640, 420 + i * 60, 30, col, aa, 'sans_bold', anchor='l')
        label(cv, '理论示意', 1640, 330, 24, GREY, a, 'sans_light', anchor='l')
        oq = ease(lin(t, T('k19') - 0.2, T('k19') + 0.3))
        label(cv, '投资者该问：多一个用户，下一个人……', W / 2, 862, 32, WHITE, oq, 'sans_bold')
        def V_(u): return 0.05 + 0.85 * (1 - math.exp(-3.2 * u)) * (0.92 * math.exp(-2.2 * u) + 0.03) * 2.4
        for u0, w_, key, col in ((0.14, '更想买 ↑', '更想买', GOLD_HI), (0.52, '更不想买 ↓', '更不想买', (1.0, 0.62, 0.55))):
            s_, o = pop(t, WT('k19', key) - 0.15, 0.4)
            label(cv, w_, x0 + (x1 - x0) * u0, y1 + 40, 34, col, o, 'sans_black', scale=0.9 + 0.1 * s_)
        return
    if t < T('k21') - 0.1:
        a = ease(lin(t, T('k20') - 0.2, T('k20') + 0.3))
        panel(cv, 'hermes_lutetia.jpg', 0, 0, W, H, a, 1.05, 0.5, 0.5, sat=0.7, warm=0.4, gain=0.3)
        label(cv, '奢侈品：靠少卖守住区分', 560, 250, 44, WHITE, a, 'serif_black')
        tiers = [('最受追捧的包', '往往要等', WT('k20', '最受追捧'), 460, GOLD, 420), ('丝巾 · 香水', '很多人买得到', WT('k20', '丝巾'), 800, WHITE, 680)]
        for n, d, ts, w_, col, y in tiers:
            s, o = pop(t, ts - 0.15, 0.45)
            card(cv, 560 - w_ / 2, y - 105, 560 + w_ / 2, y + 105, (0.10, 0.09, 0.08), 0.92 * o, col, r=12, glow=0.8 if col == GOLD else 0.2)
            label(cv, n, 560, y - 28, 44, col, o, 'sans_black'); label(cv, d, 560, y + 40, 32, GREY, o, 'sans_med')
        if os.path.exists(os.path.join(MEDIA, 'hermes_scarf.jpg')):
            o = ease(lin(t, WT('k20', '丝巾') - 0.2, WT('k20', '丝巾') + 0.3))
            panel(cv, 'hermes_scarf.jpg', 1120, 220, 1820, 820, o, 1.05, 0.5, 0.5, edge=(0.7, 0.65, 0.55), sat=0.9, warm=0.2, gain=0.8)
            text(cv, '图：%s · %s ／ %s · %s' % (CREDIT['hermes_lutetia']['artist'][:16], CREDIT['hermes_lutetia']['license'], CREDIT['hermes_scarf']['artist'][:16], CREDIT['hermes_scarf']['license']),
                 56, CRED_Y, 'sans_light', 22, GREY, anchor='l', alpha=0.75 * a)
        else:
            credit(cv, 'hermes_lutetia', a)
        return
    if t < T('k22') - 0.1:
        a = ease(lin(t, T('k21') - 0.2, T('k21') + 0.3))
        label(cv, '大众品牌：不能少卖，只能在规模里留出层次', W / 2, 250, 40, WHITE, a, 'serif_black')
        o1 = ease(lin(t, WT('k21', '苹果') - 0.2, WT('k21', '苹果') + 0.3)); o2 = ease(lin(t, WT('k21', '山姆') - 0.2, WT('k21', '山姆') + 0.3))
        panel(cv, 'iphone_line.jpg', 100, 320, 940, 800, o1, 1.05, 0.5, 0.5, edge=ORANGE, sat=0.9, warm=0.1, gain=0.75)
        panel(cv, 'sams_sz.jpg', 980, 320, 1820, 800, o2, 1.25, 0.29, 0.40, edge=GOLD, sat=0.75, warm=0.2, gain=0.55)
        s, o = pop(t, WT('k21', 'Pro') - 0.15, 0.45)
        chip(cv, 'Pro ｜ 标准版', 520, 745, o, ORANGE, 36, (0.10, 0.07, 0.05))
        s, o = pop(t, WT('k21', '会员卡') - 0.15, 0.45)
        chip(cv, '会员卡 · 260 元 / 年', 1230, 745, o, GOLD, 32, (0.12, 0.10, 0.06))
        s, o = pop(t, WT('k21', '货架') - 0.15, 0.45)
        chip(cv, '挑过的货架', 1610, 745, o, GOLD, 32, (0.12, 0.10, 0.06))
        text(cv, '图：%s · %s ／ %s · %s' % (CREDIT['iphone_line']['artist'][:16], CREDIT['iphone_line']['license'],
                                         CREDIT['sams_sz']['artist'][:16], CREDIT['sams_sz']['license']), 56, CRED_Y, 'sans_light', 22, GREY, anchor='l', alpha=0.75 * a)
        return
    if t < T('k23') - 0.1:
        a = ease(lin(t, T('k22') - 0.2, T('k22') + 0.3))
        panel(cv, 'sams_bj.jpg', 0, 0, W, H, a, 1.1, 0.5, 0.45, sat=0.6, warm=0.3, gain=0.30)
        label(cv, '山姆给会员的感觉', W / 2, 230, 46, WHITE, a, 'serif_black')
        o1 = ease(lin(t, WT('k22', '不是') - 0.2, WT('k22', '不是') + 0.3))
        chip(cv, '“我买得起贵东西”', W / 2, 360, o1, GREY, 42, (0.10, 0.10, 0.12))
        ks = ease(lin(t, WT('k22', '而是') - 0.3, WT('k22', '而是'))); wv = text_w('“我买得起贵东西”', 'sans_bold', 42) + 60
        L = layer(); line(L, (W / 2 - wv / 2, 360), (W / 2 - wv / 2 + wv * ks, 360), 5); stroke_layer(cv, L, RED, ks * o1, glow=0.5)
        s, o2 = pop(t, WT('k22', '注重品质') - 0.4, 0.5)
        card(cv, 360, 480, 1560, 740, (0.14, 0.11, 0.07), 0.94 * o2, GOLD, r=20, glow=1.0)
        label(cv, '“我属于注重品质、', W / 2, 560, 54, GOLD_HI, o2, 'serif_black')
        label(cv, '懂得挑选的城市家庭”', W / 2, 660, 54, GOLD_HI, o2, 'serif_black')
        credit(cv, 'sams_bj', a)
        return
    if t < T('k25') - 0.1:
        a = ease(lin(t, T('k23') - 0.2, T('k23') + 0.3))
        label(cv, '2025 年 7 月 · 山姆选品风波', W / 2, 250, 40, WHITE, a, 'sans_black')
        swap = ease(lin(t, WT('k23', '换上') - 0.3, WT('k23', '零食', end=True)))
        for i in range(24):
            r_, c_ = divmod(i, 8); x = W / 2 + (c_ - 3.5) * 150; y = 360 + r_ * 125
            gone = (i * 7) % 24 < 22 * swap and i % 3 != 1
            col = (0.55, 0.57, 0.60) if gone else GOLD
            card(cv, x - 58, y - 46, x + 58, y + 46, mix(col, INK, 0.6), 0.92 * a, col, r=8, glow=0.0 if gone else 0.4)
        label(cv, '■ 口碑商品', 760, 700, 30, GOLD, a, 'sans_bold')
        label(cv, '■ 到处都买得到', 1160, 700, 30, GREY, a * swap, 'sans_bold')
        if t > T('k24') - 0.2:
            o = ease(lin(t, T('k24') - 0.2, T('k24') + 0.1))
            dim(cv, 1 - 0.85 * o)
            chip(cv, '热搜 · 部分会员称要退卡', W / 2, 360, ease(lin(t, T('k24') + 0.1, T('k24') + 0.4)), RED, 40, (0.16, 0.06, 0.06))
            o2 = ease(lin(t, WT('k24', '随后') - 0.2, WT('k24', '随后') + 0.3))
            card(cv, 460, 450, 1460, 720, (0.10, 0.10, 0.12), 0.95 * o2, WHITE, glow=0.2)
            label(cv, '山姆：争议商品已下架', W / 2, 515, 38, WHITE, o2, 'sans_bold')
            label(cv, '“已关注到社交网络上的讨论，', W / 2, 595, 32, GREY, o2, 'serif_semi')
            label(cv, '将纳入后续选品策略考量”', W / 2, 655, 32, GREY, o2, 'serif_semi')
        source(cv, '36 氪、澎湃新闻、钛媒体等 2025 年 7 月报道', a)
        return
    a = ease(lin(t, T('k25') - 0.2, T('k25') + 0.3))
    panel(cv, 'sams_bj.jpg', 0, 0, W, H, a, 1.1, 0.5, 0.45, sat=0.6, warm=0.3, gain=0.28)
    V.door(cv, t, W / 2, 500, 200, 330, a, 'k25', top='会员担心的，不只是一块派', bot='而是这张卡给自己的那份区分，被稀释了')
    credit(cv, 'sams_bj', a)


def sc_math(cv, t):
    bg(cv, t, (0.08, 0.07, 0.06))
    if t < T('m2') - 0.1:
        a = ease(lin(t, T('m1') - 0.2, T('m1') + 0.3))
        gates(cv, t, a, -1, y=230, done=(0, 1, 2))
        o = ease(lin(t, WT('m1', '算术') - 0.2, WT('m1', '算术') + 0.3))
        big(cv, '身份', 690, 560, 110, a=o, grad=GOLDG); label(cv, '→', W / 2, 560, 70, GREY, o, 'sans_med')
        big(cv, '利润？', 1230, 560, 110, a=ease(lin(t, WT('m1', '利润') - 0.2, WT('m1', '利润') + 0.2)), color=WHITE, glow=0.2)
        label(cv, '最后一道算术', W / 2, 760, 44, GOLD, o, 'serif_black')
        return
    if t < T('m3') - 0.1:
        a = ease(lin(t, T('m2') - 0.2, T('m2') + 0.3))
        big(cv, 'HERMÈS', W / 2, 190, 90, a=a, fname='playfair', grad=GOLDG, track=0.12)
        label(cv, '把身份变成很高的价格 · 2025 年', W / 2, 285, 36, WHITE, a, 'sans_bold')
        f1 = 0.711 * eout(lin(t, WT('m2', '七十一') - 0.5, WT('m2', '七十一') + 0.3)); f2 = 0.41 * eout(lin(t, WT('m2', '四十一') - 0.5, WT('m2', '四十一') + 0.3))
        V.ring_stat(cv, (720, 540), 170, f1, '%d%%' % round(f1 * 100), '毛利率', ease(lin(t, WT('m2', '毛利率') - 0.3, WT('m2', '毛利率'))))
        V.ring_stat(cv, (1200, 540), 170, f2, '%d%%' % round(f2 * 100), '经营利润率', ease(lin(t, WT('m2', '经营利润率') - 0.3, WT('m2', '经营利润率'))))
        source(cv, '爱马仕 2025 年度业绩：毛利率 71.1%，经常性经营利润率 41%', a)
        return
    if t < T('m4') - 0.1:
        V.apple_share(cv, t, ease(lin(t, T('m3') - 0.2, T('m3') + 0.3)), W / 2, 190, 285, 360, 1560, (470, 690), SRC_Y, CRED_Y)
        return
    if t < T('m5') - 0.1:
        V.asp_bars(cv, t, ease(lin(t, T('m4') - 0.2, T('m4') + 0.3)), W / 2, 200, (760, 1160), 800, 400, SRC_Y)
        return
    if t < T('m6') - 0.1:
        am = ease(lin(t, T('m5') - 0.2, T('m5') + 0.3)); panel(cv, 'iphone_back.jpg', 0, 0, W, H, am, 1.1, 0.5, 0.5, sat=0.5, warm=0.1, gain=0.16)
        V.why_more(cv, t, ease(lin(t, T('m5') - 0.2, T('m5') + 0.3)), W / 2, 260, 480, 340, 560)
        text(cv, '图：%s · %s · Wikimedia Commons' % (CREDIT['iphone_back']['artist'][:34], CREDIT['iphone_back']['license']), 56, CRED_Y, 'sans_light', 22, GREY, anchor='l', alpha=0.75 * am)
        return
    if t < T('m7') - 0.1:
        a = ease(lin(t, T('m6') - 0.2, T('m6') + 0.3))
        label(cv, '爱马仕', 640, 220, 48, GOLD, a, 'serif_black'); label(cv, '苹果', 1280, 220, 48, (0.85, 0.88, 0.95), a, 'serif_black')
        o1 = ease(lin(t, WT('m6', '少数人') - 0.2, WT('m6', '少数人') + 0.3)); o2_ = ease(lin(t, WT('m6', '很多人') - 0.2, WT('m6', '很多人') + 0.3))
        label(cv, '少数人 · 付很高的价', 640, 278, 30, WHITE, o1, 'sans_med'); label(cv, '很多人 · 多付一截', 1280, 278, 30, WHITE, o2_, 'sans_med')
        k = eout(lin(t, WT('m6', '少数人') - 0.2, WT('m6', '多付一截', end=True)))
        L = layer(); line(L, (640, 320), (640 + 320 * k, 320 + 230 * k), 5); line(L, (1280, 320), (1280 - 320 * k, 320 + 230 * k), 5)
        stroke_layer(cv, L, GOLD, a, glow=1.0)
        s, o = pop(t, WT('m6', '定价权') - 0.3, 0.5)
        chip(cv, '定价权', W / 2, 620, o, GOLD, 54, (0.16, 0.13, 0.08))
        label(cv, '两条路，都把身份变成了定价权', W / 2, 760, 38, GOLD_HI, o, 'sans_bold')
        return
    if t < T('m8') - 0.1:
        V.acquire(cv, t, ease(lin(t, T('m7') - 0.3, T('m7') + 0.2)), (640, 1280), 300, 790, 'm7')
        return
    a = ease(lin(t, T('m8') - 0.2, T('m8') + 0.3))
    big(cv, '认同留不住钱', W / 2, CY - 80, 88, a=a, color=WHITE, glow=0.2)
    s, o = pop(t, WT('m8', '热闹') - 0.2, 0.5)
    big(cv, '= 热闹  ≠ 护城河', W / 2, CY + 70, 88, a=o, grad=REDG, glow=0.4)


# ═══════════════════════ 04 · 中国考题 ═══════════════════════
def scorecard(cv, t, x0, y0, rows, a, w=960):
    card(cv, x0, y0, x0 + w, y0 + 60 + 104 * len(rows), (0.08, 0.09, 0.11), 0.92 * a, GOLD, glow=0.4)
    for i, (n, mk, note_, ts) in enumerate(rows):
        y = y0 + 82 + i * 104; o = ease(lin(t, ts - 0.2, ts + 0.3)) * a
        label(cv, n, x0 + 36, y, 36, WHITE, a, 'sans_black', anchor='l')
        if o > 0:
            check(cv, x0 + 240, y, mk, o, 46)
            label(cv, note_, x0 + 290, y, 28, GREY, o, 'sans_med', anchor='l')


def moutai_h(cv, t):
    has = lambda k: os.path.exists(os.path.join(MEDIA, k + '.jpg'))
    if t < T('g3') - 0.1:
        a = ease(lin(t, T('g2') - 0.2, T('g2') + 0.3))
        if has('banquet'): photo(cv, 'banquet.jpg', t, T('g2') - 0.3, T('g3'), 1.03, 1.1, 0.5, 0.5, 0.5, 0.5, a=a, sat=0.7, warm=0.3, contrast=1.05, gain=0.32)
        if has('moutai_bottle'):
            panel(cv, 'moutai_bottle.jpg', 1240, 150, 1760, 880, a, 1.0, 0.5, 0.42, edge=GOLD, sat=0.95, warm=0.15, contrast=1.05, gain=0.9)
        big(cv, '茅台', 640, 260, 120, a=a, grad=((1.0, 0.85, 0.7), (0.85, 0.30, 0.22)), glow=0.4)
        label(cv, '中国最经典的身份消费品', 640, 380, 36, WHITE, a, 'sans_bold')
        s, o = pop(t, WT('g2', '宴席') - 0.2, 0.45)
        chip(cv, '摆上宴席 · 人人认得', 640, 560, o, GOLD, 40, (0.12, 0.09, 0.06))
        s, o = pop(t, WT('g2', '体面') - 0.4, 0.45)
        chip(cv, '拿去送礼 · 代表体面', 640, 680, o, GOLD, 40, (0.12, 0.09, 0.06))
        ks = [k for k in ('banquet', 'moutai_bottle') if has(k)]
        if len(ks) == 2:
            text(cv, '图：%s · %s ／ %s · %s' % (CREDIT[ks[0]]['artist'][:16], CREDIT[ks[0]]['license'], CREDIT[ks[1]]['artist'][:16], CREDIT[ks[1]]['license']),
                 56, CRED_Y, 'sans_light', 22, GREY, anchor='l', alpha=0.75 * a)
        elif ks: credit(cv, ks[0], a)
        return
    if t < T('g4') - 0.1:
        a = ease(lin(t, T('g3') - 0.2, T('g3') + 0.3))
        if has('maotai_town'):
            photo(cv, 'maotai_town.jpg', t, T('g3') - 0.3, T('g4'), 1.03, 1.1, 0.5, 0.5, 0.5, 0.5, a=a, sat=0.8, warm=0.15, contrast=1.05, gain=0.40)
            label(cv, '赤水河畔 · 茅台镇', W / 2, 280, 32, WHITE, a, 'sans_med')
            credit(cv, 'maotai_town', a)
        label(cv, '仿不了', W / 2, 200, 64, GOLD, a, 'serif_black', glow=0.3)
        k = eout(lin(t, WT('g3', '投料') - 0.2, WT('g3', '五年', end=True)))
        x0, x1, y = 360, 1560, 600
        L = layer(); line(L, (x0, y), (x0 + (x1 - x0) * k, y), 6); stroke_layer(cv, L, GOLD, a, glow=1.2)
        for i in range(6):
            o = ease(lin(k, i / 5 - 0.05, i / 5 + 0.05)) * a
            L = layer(); circle(L, (x0 + (x1 - x0) * i / 5, y), 12, fill=True); stroke_layer(cv, L, GOLD_HI, o, glow=1.2)
            label(cv, ('投料', '1 年', '2 年', '3 年', '4 年', '出厂')[i], x0 + (x1 - x0) * i / 5, y + 56, 30, WHITE, o, 'sans_bold')
        s, o = pop(t, WT('g3', '五年') - 0.1, 0.5)
        big(cv, '至少 5 年', W / 2, 460, 84, a=o, scale=0.9 + 0.1 * s, grad=GOLDG, glow=0.5)
        label(cv, '别人想追，也追不快', W / 2, 790, 40, WHITE, ease(lin(t, WT('g3', '追不快') - 0.4, WT('g3', '追不快'))), 'sans_bold')
        source(cv, '茅台官方介绍：生产周期一年，基酒贮存三年以上，勾兑后再贮存约一年', a)
        return
    if t < T('g5') - 0.1:
        a = ease(lin(t, T('g4') - 0.2, T('g4') + 0.3))
        if has('banquet'): panel(cv, 'banquet.jpg', 0, 0, W, H, a, 1.05, 0.5, 0.5, sat=0.4, warm=0.2, gain=0.22); credit(cv, 'banquet', a)
        o1 = ease(lin(t, WT('g4', '社会可见性') - 0.3, WT('g4', '社会可见性') + 0.2))
        label(cv, '乘法里的一项', 480, 380, 34, GREY, o1, 'sans_med')
        big(cv, '社会可见性', 480, 480, 80, a=o1, color=COLD, glow=0.3)
        o2 = ease(lin(t, WT('g4', '二零二五年') - 0.2, WT('g4', '二零二五年') + 0.3))
        card(cv, 900, 220, 1800, 760, (0.94, 0.91, 0.85), 0.95 * o2, r=10)
        L = layer(); rect(L, 900, 220, 1800, 310, r=10); fill(cv, L, (0.70, 0.10, 0.09), 0.95 * o2)
        label(cv, '2025.05 · 新修订', 1350, 265, 34, WHITE, o2, 'sans_black')
        label(cv, '《党政机关厉行节约', 1350, 410, 50, (0.15, 0.12, 0.10), o2, 'serif_black', glow=0)
        label(cv, '反对浪费条例》', 1350, 490, 50, (0.15, 0.12, 0.10), o2, 'serif_black', glow=0)
        o3 = ease(lin(t, WT('g4', '工作餐') - 0.2, WT('g4', '工作餐') + 0.3))
        label(cv, '工作餐不得提供高档酒水', 1350, 640, 46, (0.70, 0.12, 0.10), o3, 'sans_black', glow=0)
        source(cv, '中共中央、国务院 2025 年 5 月印发（新华社）', a)
        return
    if t < T('g7') - 0.1:
        a = ease(lin(t, T('g5') - 0.2, T('g5') + 0.3))
        label(cv, '宴席上的那份可见性，少了一块', 640, 200, 38, (1.0, 0.70, 0.62), a * (1 - ease(lin(t, T('g6') - 0.3, T('g6')))), 'sans_bold')
        label(cv, '但定价权并没有消失', 640, 200, 38, GOLD_HI, ease(lin(t, T('g6') - 0.1, T('g6') + 0.3)), 'sans_bold')
        V.moutai_price(cv, t, a, 140, 1180, 290, 760, 830)
        o = ease(lin(t, WT('g5', '双双下降') - 0.4, WT('g5', '双双下降'))) * (1 - ease(lin(t, T('g6') - 0.3, T('g6'))))
        card(cv, 1280, 330, 1820, 620, (0.14, 0.06, 0.06), 0.92 * o, RED, r=14, glow=0.4)
        label(cv, '2025 年', 1550, 400, 34, WHITE, o, 'sans_bold')
        label(cv, '营收 −1.21% · 净利 −4.53%', 1550, 470, 34, WHITE, o, 'sans_bold')
        label(cv, '上市以来第一次双双下降', 1550, 550, 30, (1.0, 0.70, 0.62), o, 'sans_med')
        o2 = ease(lin(t, WT('g6', '毛利率') - 0.3, WT('g6', '毛利率') + 0.2))
        card(cv, 1280, 330, 1820, 620, (0.14, 0.11, 0.06), 0.92 * o2, GOLD, r=14, glow=0.6)
        label(cv, '2025 年 · 茅台酒毛利率', 1550, 400, 32, WHITE, o2, 'sans_bold')
        stat(cv, 1550, 520, '93.5%', '', o2, size=100, grad=GOLDG)
        source(cv, '批价：第一财经等媒体报道；茅台 2025 年报、2026.03.30 调价公告', a)
        return
    a = ease(lin(t, T('g7') - 0.2, T('g7') + 0.3))
    label(cv, '乘法里有一项变小 → 溢价松动', 640, 230, 40, (1.0, 0.70, 0.62), a, 'sans_bold')
    vals = (0.40, 0.90, 0.78, 0.70)
    for i, ((n, key, col), y) in enumerate(zip(V.FACTORS, (360, 470, 580, 690))):
        on = ease(lin(t, WT('g7', '认得出') - 0.2, WT('g7', '认得出') + 0.3)) if i in (1, 2) else 0
        label(cv, n, 140, y, 38, col, a, 'sans_black', anchor='l')
        L = layer(); rect(L, 400, y - 16, 1100, y + 16, r=16); fill(cv, L, (0.20, 0.21, 0.24), 0.9 * a)
        L = layer(); rect(L, 400, y - 16, 400 + 700 * vals[i], y + 16, r=16); fill(cv, L, RED if i == 0 else col, 0.95 * a)
        if on > 0: label(cv, '✓', 1140, y, 38, TEAL, on, 'sans_black')
    s, o = pop(t, WT('g7', '定价权') - 0.3, 0.5)
    big(cv, '认得出、仿不了还在', 1530, 450, 54, a=o, color=WHITE, glow=0.2)
    big(cv, '定价权就还在', 1530, 560, 64, a=o, grad=GOLDG, glow=0.5)


def sc_china(cv, t):
    bg(cv, t, (0.09, 0.06, 0.05))
    if t < T('g2') - 0.1:
        a = ease(lin(t, T('g1') - 0.2, T('g1') + 0.3))
        big(cv, '中国考题', W / 2, 230, 110, a=a, grad=GOLDG)
        label(cv, '三道关 + 那道乘法', W / 2, 340, 36, GREY, a, 'sans_med')
        for i, (n, tag, key) in enumerate((('茅台', '老牌', '老牌'), ('老铺黄金', '新秀', '两家新秀'), ('泡泡玛特', '新秀', '两家新秀'))):
            o = ease(lin(t, WT('g1', key) - 0.35 + 0.12 * i * (i > 0), WT('g1', key) + 0.1 + 0.12 * i * (i > 0)))
            x = W / 2 + (i - 1) * 520; col = GOLD if i == 0 else (1.0, 0.65, 0.55)
            card(cv, x - 230, 470, x + 230, 720, (0.12, 0.09, 0.07), 0.9 * o, col, r=14, glow=0.5)
            label(cv, n, x, 570, 56, WHITE, o, 'serif_black')
            chip(cv, tag, x, 660, o, col, 30, (0.10, 0.08, 0.06))
        return
    if t < T('g8') - 0.1:
        return moutai_h(cv, t)
    if t < T('g12') - 0.1:
        a = ease(lin(t, T('g8') - 0.2, T('g8') + 0.3))
        panel(cv, 'gold_bracelet.jpg', 0, 0, W, H, a, 1.15, 0.5, 0.5, sat=0.8, warm=0.4, gain=0.22)
        big(cv, '老铺黄金', W / 2, 170, 88, a=a, grad=GOLDG)
        rows = [('认得出', '✓', '商场门口排过长队', WT('g8', '能')),
                ('仿不了', '?', '32 家商场里 ≥19 家也有古法金对手', WT('g9', '三十二')),
                ('稀释不了', '?', '11 月促销，手镯立减近 2 万元', WT('g10', '手镯')),
                ('利润', '✓', '2026 上半年利润 +88%', WT('g11', '八成'))]
        scorecard(cv, t, 100, 260, rows, a, w=940)
        o = ease(lin(t, WT('g9', '三十二') - 0.2, WT('g9', '三十二') + 0.3)); k = ease(lin(t, WT('g9', '十九') - 0.4, WT('g9', '十九') + 0.4))
        for i in range(32):
            r_, c_ = divmod(i, 8); x = 1480 + (c_ - 3.5) * 64; y = 340 + r_ * 76
            hit_ = i % 32 in (0, 1, 3, 4, 6, 7, 9, 10, 12, 13, 15, 17, 18, 20, 22, 24, 26, 28, 30)
            col = RED if hit_ and k > 0.5 else GOLD
            L = layer(); rect(L, x - 24, y - 26, x + 24, y + 26, r=4); fill(cv, L, col, o * (0.85 if col == RED else 0.6))
        label(cv, '■ 进驻商场', 1340, 680, 26, GOLD, o, 'sans_med')
        label(cv, '■ 同场有其他古法金品牌', 1560, 680, 26, (1.0, 0.65, 0.58), o * k, 'sans_med')
        source(cv, '界面新闻（截至 2026.04）；21 世纪经济报道（2026.11）；公司 2026 中期报告', a)
        credit(cv, 'gold_bracelet', a)
        return
    if t < T('g13') - 0.1:
        a = ease(lin(t, T('g12') - 0.2, T('g12') + 0.3))
        if 'labubu_hk' in CLIPS:
            vpanel(cv, CLIPS['labubu_hk'], t, T('g12') - 0.2, 0, 0, W, H, a, zoom=1.0, z1=1.05, dur=8, edge=None, sat=0.5, warm=0.1, contrast=1.05, gain=0.24)
        else:
            panel(cv, 'nyc_store.jpg', 0, 0, W, H, a, 1.1, 0.5, 0.5, sat=0.5, warm=0.1, gain=0.22)
        big(cv, '泡泡玛特', W / 2, 170, 88, a=a, color=(1.0, 0.75, 0.66), glow=0.2)
        rows = [('认得出', '✓', '全球门店排长队', T('g12') + 0.2),
                ('仿不了', '?', '补货当天，二手价腰斩', WT('g12', '稀缺')),
                ('稀释不了', '?', '三季度收入同比 −45%~−50%', WT('g12', '第三季度'))]
        scorecard(cv, t, 100, 260, rows, a, w=860)
        o = ease(lin(t, WT('g12', '公司') - 0.2, WT('g12', '公司') + 0.3))
        card(cv, 1060, 260, 1820, 632, (0.10, 0.10, 0.12), 0.95 * o, WHITE, glow=0.2)
        label(cv, '公司的解释', 1100, 320, 30, GREY, o, 'sans_bold', anchor='l')
        label(cv, '去年同期基数太高；', 1100, 400, 38, WHITE, o, 'sans_bold', anchor='l')
        label(cv, '正在优化海外库存', 1100, 460, 38, WHITE, o, 'sans_bold', anchor='l')
        label(cv, '预计中国市场全年仍正增长', 1100, 560, 28, GREY, o, 'sans_med', anchor='l')
        source(cv, '泡泡玛特 2026 年第三季度经营数据公告（2026.10.27）', a)
        credit(cv, 'v_labubu_hk' if 'labubu_hk' in CLIPS else 'nyc_store', a)
        return
    if t < T('g15') - 0.1:
        a = ease(lin(t, T('g13') - 0.2, T('g13') + 0.3)); dx = 60
        L = layer(); rect(L, 60 + dx, 160, 1020 + dx, 760, r=16); fill(cv, L, (0.14, 0.10, 0.10), 0.95 * a)
        big(cv, '段', 300 + dx, 450, 300, a=a * 0.9, color=(0.85, 0.40, 0.32), fname='serif_black', glow=0.3)
        label(cv, '段永平', 680 + dx, 380, 56, (1.0, 0.60, 0.50), a, 'serif_black')
        label(cv, 'Duan Yongping', 680 + dx, 440, 28, GREY, a, 'corm_med', track=0.1)
        L = layer(); pts = [(560 + dx + 400 * u, 540 + 140 * u ** 0.8 + 18 * math.sin(u * 14)) for u in np.linspace(0, 1, 30)]
        poly(L, pts, 3); stroke_layer(cv, L, RED, a * 0.8, glow=0.4)
        kk = eout(lin(t, WT('g13', '买入') - 0.2, WT('g13', '股份', end=True)))
        L = layer(); arrow(L, (760 + dx, 700), (760 + dx + 120 * kk, 700 - 150 * kk), 5, 20); stroke_layer(cv, L, GOLD, a * ease(kk * 3), glow=1.2)
        o1 = ease(lin(t, WT('g13', '百分之五') - 0.3, WT('g13', '百分之五') + 0.2))
        label(cv, '2026.05 举牌 5.69%', 1480, 250, 36, GOLD_HI, o1, 'sans_bold')
        label(cv, '→ 7 月增至 7.65%', 1480, 305, 36, GOLD_HI, o1, 'sans_bold')
        o2 = ease(lin(t, WT('g13', '十年') - 0.3, WT('g13', '十年') + 0.2))
        label(cv, '“我猜 10 年内', 1480, 420, 42, WHITE, o2, 'serif_semi')
        label(cv, '大概率是不会卖的。”', 1480, 480, 42, WHITE, o2, 'serif_semi')
        o3 = ease(lin(t, T('g14') - 0.2, T('g14') + 0.3))
        label(cv, '看好的是：创始人王宁', 1480, 610, 38, WHITE, o3, 'sans_bold')
        label(cv, '“没想到盈利如此之好”', 1480, 670, 34, GREY, ease(lin(t, WT('g14', '没想到') - 0.2, WT('g14', '没想到') + 0.2)), 'serif_semi')
        source(cv, '港交所权益披露；财联社、上海证券报、中证网报道', a)
        return
    a = ease(lin(t, T('g15') - 0.2, T('g15') + 0.3))
    o1 = ease(lin(t, WT('g15', '热度') - 0.2, WT('g15', '热度') + 0.3)) * (1 - 0.6 * ease(lin(t, WT('g15', '一家公司') - 0.2, WT('g15', '一家公司') + 0.3)))
    label(cv, '一只玩偶的热度，会退', W / 2, 230, 48, GREY, o1, 'sans_bold')
    o2 = ease(lin(t, WT('g15', '一次又一次') - 0.2, WT('g15', '一次又一次') + 0.3))
    for i in range(5):
        oo = ease(lin(t, WT('g15', '一次又一次') + i * 0.18, WT('g15', '一次又一次') + i * 0.18 + 0.3))
        L = layer(); circle(L, (W / 2 + (i - 2) * 170, 380), 52, 4); stroke_layer(cv, L, GOLD, oo * 0.9, glow=1.0)
        label(cv, 'IP', W / 2 + (i - 2) * 170, 380, 30, GOLD_HI, oo, 'oswald')
    label(cv, '一次又一次，造出让人想拥有的身份', W / 2, 510, 40, WHITE, o2, 'sans_bold')
    blink = 0.6 + 0.4 * math.sin(t * 5)
    s, o3 = pop(t, WT('g15', '答案') - 0.2, 0.5)
    check(cv, 700, 720, '?', o3 * blink, 80)
    big(cv, '答案，交给时间', 1060, 720, 76, a=o3, grad=GOLDG, glow=0.5)


# ═══════════════════════ 05 · 失守 ═══════════════════════
class FireworksH(V.Fireworks):
    def __init__(self, seed=11):
        r = np.random.default_rng(seed); self.b = []
        for i in range(30):
            self.b.append((r.uniform(260, 1660), r.uniform(430, 520), i * 0.38 + r.uniform(0, 0.25), r.uniform(0, 6.28)))
        self.dirs = r.normal(0, 1, (140, 2)); self.dirs /= np.linalg.norm(self.dirs, axis=1, keepdims=True); self.sp = r.uniform(0.55, 1.0, 140)


FWH = FireworksH()


def sc_betray(cv, t):
    bg(cv, t, (0.07, 0.05, 0.06))
    if t < T('q2') - 0.1:
        a = ease(lin(t, T('q1') - 0.2, T('q1') + 0.3))
        label(cv, '还有一种失守，比什么都快', W / 2, 280, 44, GREY, a, 'sans_bold')
        s, o = pop(t, WT('q1', '背叛') - 0.2, 0.5)
        big(cv, '品牌背叛了用户的身份', W / 2, 470, 110, a=o, grad=REDG, glow=0.5)
        L = layer(); line(L, (460, 600), (460 + 1000 * ease(lin(t, WT('q1', '背叛'), WT('q1', '身份', end=True))), 600), 4); stroke_layer(cv, L, RED, o, glow=1.0)
        return
    a = ease(lin(t, T('q2') - 0.2, T('q2') + 0.4))
    photo(cv, 'himalaya.jpg', t, T('q2') - 0.2, T('q4'), 1.03, 1.12, 0.5, 0.5, 0.45, 0.42, a=a, sat=0.6, warm=-0.2, contrast=1.1, gain=0.55)
    shade(cv, 0.45, 0.85, 0.08)
    tf = WT('q2', '烟花') - 0.3
    if t > tf: FWH.draw(cv, t - tf, a * (1 - ease(lin(t, T('q4') - 0.3, T('q4') + 0.3))))
    label(cv, '2025.09.19 · 喜马拉雅山脊 · 始祖鸟 × 蔡国强“升龙”', W / 2, 150, 30, WHITE, a, 'sans_bold')
    label(cv, '烟花为示意动画，背景为喜马拉雅道拉吉里峰（非事发地）', W / 2, 195, 24, GREY, a, 'sans_light')
    if t < T('q4') - 0.1:
        o = ease(lin(t, WT('q3', '敬畏自然') - 0.3, WT('q3', '敬畏自然') + 0.2))
        crack = ease(lin(t, HIT['fire'] - 0.1, HIT['fire'] + 0.4))
        cx, cy = W / 2, 680
        card(cv, cx - 290, cy - 60, cx + 290, cy + 60, (0.08, 0.10, 0.10), 0.92 * o, mix(TEAL, RED, crack), r=12, glow=0.5)
        label(cv, '“敬畏自然”', cx, cy, 54, mix(TEAL, RED, crack), o, 'serif_black')
        if crack > 0:
            L = layer(); poly(L, [(cx + 20, cy - 58), (cx, cy - 25), (cx + 35, cy + 10), (cx + 5, cy + 58)], 3); stroke_layer(cv, L, RED, crack, glow=1.0)
        o2 = ease(lin(t, WT('q3', '两天后') - 0.2, WT('q3', '两天后') + 0.3))
        chip(cv, '9.21 · 双方先后道歉', W / 2 - 220, 820, o2, WHITE, 30, (0.08, 0.08, 0.10))
        chip(cv, '日喀则成立调查组', W / 2 + 220, 820, ease(lin(t, WT('q3', '调查组') - 0.3, WT('q3', '调查组'))), WHITE, 30, (0.08, 0.08, 0.10))
        source(cv, '新华网、中新网、澎湃新闻 2025.09.21–22', o2)
    else:
        o = ease(lin(t, T('q4') - 0.1, T('q4') + 0.3)); dim(cv, 1 - 0.6 * o)
        big(cv, '为身份多付钱，', W / 2, 430, 88, a=o, grad=GOLDG, glow=0.4)
        big(cv, '也会因为身份，转身离开', W / 2, 570, 74, a=ease(lin(t, WT('q4', '转身') - 0.4, WT('q4', '转身'))), color=WHITE, glow=0.2)
    credit(cv, 'himalaya', a)


# ═══════════════════════ 06 · 答案 ═══════════════════════
FINAL_Y = (430, 570)


def sc_answer(cv, t):
    bg(cv, t, (0.07, 0.065, 0.06))
    if t < T('z3') - 0.1:
        a = ease(lin(t, T('z1') - 0.2, T('z1') + 0.4))
        bx, by = W / 2, 760
        L = layer(); fpoly(L, [(bx - 60, 330), (bx + 60, 330), (bx + 300, 790), (bx - 300, 790)]); fill(cv, cv2.GaussianBlur(L, (0, 0), 30), (1.0, 0.92, 0.75), 0.12 * a)
        L = layer(); poly(L, [(bx - 120, by), (bx - 100, by - 200), (bx + 100, by - 200), (bx + 120, by)], 5, closed=True); arc(L, (bx, by - 200), 70, 180, 360, 5)
        stroke_layer(cv, L, GOLD, a, glow=1.2)
        off = lin(t, WT('z2', '没有任何人') - 0.3, WT('z2', '知道', end=True) + 0.3)
        for i in range(8):
            ang = math.pi * (0.12 + 0.76 * i / 7); x = bx + 640 * math.cos(ang); y = 820 - 300 * math.sin(ang)
            on = 1 - ease(lin(off, i / 8, i / 8 + 0.15))
            L = layer(); poly(L, [(x - 26, y), (x, y - 14), (x + 26, y), (x, y + 14)], 3, closed=True); circle(L, (x, y), 6, fill=True)
            stroke_layer(cv, L, WHITE, a * (0.15 + 0.85 * on), glow=0.6 * on)
        o = ease(lin(t, WT('z2', '还愿意') - 0.3, WT('z2', '还愿意') + 0.2))
        big(cv, '你还愿意，多付同样多的钱吗？', W / 2, 210, 76, a=o, grad=GOLDG, glow=0.5)
        label(cv, '隐形测试', W / 2, 860, 34, GOLD, a, 'serif_semi', track=0.3)
        return
    if t < T('z4') - 0.1:
        a = ease(lin(t, T('z3') - 0.2, T('z3') + 0.3))
        for i, (q, ans, col, key) in enumerate((('愿意', '你买的是品质', TEAL, '如果愿意'), ('不愿意', '你买的是别人的目光', GOLD, '不愿意'))):
            s, o = pop(t, WT('z3', key) - 0.1, 0.45); y = 300 + i * 240
            card(cv, 460, y - 100, 1460, y + 100, (0.10, 0.10, 0.11), 0.92 * o, col, glow=0.5)
            label(cv, q, 540, y, 52, col, o, 'sans_black', anchor='l')
            label(cv, ans, 1400, y, 46, WHITE, o, 'serif_semi', anchor='r')
        o = ease(lin(t, WT('z3', '两种') - 0.2, WT('z3', '两种') + 0.3))
        big(cv, '两种，都没有错', W / 2, 790, 72, a=o, color=(1.0, 0.92, 0.80), glow=0.4)
        return
    if t < T('z5') - 0.1:
        V.blind_test(cv, t, ease(lin(t, T('z4') - 0.2, T('z4') + 0.3)), W / 2, 190, (760, 1160), 820, 400)
        return
    if t < T('z7') - 0.1:
        a = ease(lin(t, T('z5') - 0.1, T('z5') + 0.3))
        label(cv, '对投资者来说', 560, 220, 40, GREY, a, 'sans_bold')
        s, o = pop(t, WT('z5', '贵') - 0.1, 0.45)
        card(cv, 360, 280, 760, 500, (0.12, 0.11, 0.10), 0.92 * o, GREY, r=16, glow=0.2)
        big(cv, '贵', 560, 390, 130, a=o, color=WHITE, glow=0.1)
        k = ease(lin(t, WT('z5', '标价') - 0.1, WT('z5', '标价') + 0.3))
        L = layer(); line(L, (350, 500), (350 + 420 * k, 500 - 220 * k), 6); stroke_layer(cv, L, RED, k * 0.9, glow=0.8)
        label(cv, '只是一个标价，谁都能标', 560, 580, 40, GREY, ease(lin(t, WT('z5', '谁都能标') - 0.3, WT('z5', '谁都能标'))), 'sans_bold')
        o2 = ease(lin(t, T('z6') - 0.2, T('z6') + 0.3))
        gates(cv, t, o2, -1, y=300, done=(0, 1, 2), cx=1360)
        chip(cv, '+ 变成利润', 1360, 540, ease(lin(t, WT('z6', '利润') - 0.3, WT('z6', '利润'))), GOLD, 38)
        s3, o3 = pop(t, HIT['answer'] - 0.1, 0.5)
        big(cv, '= 护城河', 1360, 690, 88, a=o3, scale=0.9 + 0.1 * s3, grad=GOLDG, glow=0.6)
        return
    if t < T('z8') - 0.1:
        V.z7(cv, t, (600, 620), 0.8, (1320, 300), (1320, 420), (1320, 610))
        return
    a = ease(lin(t, T('z8') - 0.1, T('z8') + 0.4)) * (1 - ease(lin(t, HIT['logo'] - 0.5, HIT['logo'])))
    DUST.draw(cv, t, GOLD, 0.35)
    label(cv, '品牌的最高境界', W / 2, 290, 48, GREY, a, 'sans_bold')
    o1 = ease(lin(t, WT('z8', '我拥有它') - 0.3, WT('z8', '我拥有它') + 0.2)) * (1 - ease(lin(t, HIT['logo'] - 0.5, HIT['logo'])))
    big(cv, '不是“我拥有它”', W / 2, FINAL_Y[0], 84, a=o1, color=(0.85, 0.85, 0.88), glow=0.1)
    o2 = ease(lin(t, WT('z8', '它代表我') - 0.3, WT('z8', '它代表我') + 0.2)) * (1 - ease(lin(t, HIT['logo'] - 0.5, HIT['logo'])))
    big(cv, V.FINAL_LINE, W / 2, FINAL_Y[1], 96, a=o2, grad=GOLDG, glow=0.7)


# ── 片尾：沿用竖版的粒子与流光，只换纵向位置 ──
V.FINAL_Y = FINAL_Y
V.LOGO_Y = LOGO_Y = 330
V.LOGO = LOGO = load_logo(300)
Y_BRAND, Y_EN, Y_LINE, Y_F1, Y_F2 = 590, 685, 752, 820, 892


def sc_end(cv, t):
    if V.GATHER is None: V.GATHER = V.Gather()
    bg(cv, t, (0.07, 0.07, 0.09))
    t0, land, brand, slogan, fade_t = HIT['logo'], HIT['logo_land'], HIT['brand'], HIT['slogan'], HIT['fade']
    u = t - t0; out = 1 - ease(lin(t, fade_t, TOTAL - 0.15))
    DUST.draw(cv, t, GOLD, 0.35 * out)
    dur = land - t0 - 0.55
    pk = 1 - ease(lin(t, land - 0.15, land + 0.55))
    if pk > 0:
        tmp = np.zeros_like(cv); V.GATHER.draw(tmp, u, dur); cv += tmp * pk
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
    CLIPS['airport'] = Clip('airport.mp4', 1080, 0.5)
    CLIPS['peacock'] = Clip('peacock_h.mp4', 1280, 0.5)    # 横版用 1280×720 原分辨率
    for k in ('crowd', 'car', 'turn'): CLIPS['dfd_' + k] = Clip('dfd_%s.mp4' % k, 640, 0.5)
    for k in ('labubu_bj', 'labubu_hk'):
        if os.path.exists(os.path.join(MEDIA, 'clips', k + '.mp4')): CLIPS[k] = Clip(k + '.mp4', 1920, 0.5)


SC = [
    (0.0, T('o3') - 0.3, sc_intro), (T('o3') - 0.3, T('o6') - 0.3, sc_orange), (T('o6') - 0.3, T('o11') - 0.3, sc_halves),
    (T('o11') - 0.3, HIT['title'], sc_question), (HIT['title'], T('p1') - 0.25, sc_title),
    (T('p1') - 0.25, T('p7') - 0.3, sc_three), (T('p7') - 0.3, T('p10') - 0.3, sc_envy), (T('p10') - 0.3, T('p14') - 0.3, sc_signal),
    (T('p14') - 0.3, T('p19') - 0.3, sc_forces), (T('p19') - 0.3, T('p22') - 0.3, sc_formula), (T('p22') - 0.3, T('d1') - 0.3, sc_paradox),
    (T('d1') - 0.3, T('k1') - 0.3, sc_ruler),
    (T('k1') - 0.3, T('k7') - 0.3, sc_gate1), (T('k7') - 0.3, T('k17') - 0.3, sc_gate2), (T('k17') - 0.3, T('m1') - 0.3, sc_gate3),
    (T('m1') - 0.3, T('g1') - 0.25, sc_math), (T('g1') - 0.25, T('q1') - 0.3, sc_china), (T('q1') - 0.3, T('z1') - 0.3, sc_betray),
    (T('z1') - 0.3, HIT['logo'], sc_answer), (HIT['logo'], TOTAL + 1, sc_end)]


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
            t = float(x)
            try: cv2.imwrite(os.path.join(WORK, 'hstill_%06.2f.png' % t), to8(render(int(round(t * FPS))))[..., ::-1]); print('still', t)
            except Exception as e: print('ERR', t, repr(e), flush=True)
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
