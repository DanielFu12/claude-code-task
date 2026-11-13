"""第四期《二十年后的补票》全部镜头：开场、片名、第一至七章。

版式（沿用第三期）：上方画窗（y≈279–841）放真实影像；下方 y 900–1420 放动画解读；y≈1462 出处；y≈1555 字幕。
没有影像的镜头，动画可以占用 300–1420。
素材：CNBC 专访画面（c_*，src/cut_cnbc.py）、财讯 EP97 的阿贝尔与股东大会（e_*）、已核授权的 Wikimedia 照片；
其余用文件原文页、13F 表格、数据图与示意动画（示意处画面标注“示意”）。不使用谷歌的商标图形。
"""
import math
import numpy as np, cv2
from common import *          # noqa
import media as M
import fx

PAPER = C(236, 228, 210)
INKD = C(40, 36, 32)
BLUE_L = C(150, 195, 255)


# ======================================================================== 通用构件
def seq(cv, t, t0, t1, names, cy=560, w=1000, h=420, focus=None, xfade=0.35, cap=None, a=1.0):
    """多段素材按原速串接（不慢放单个镜头）：每段播放它在 USABLE 里的可用时长，用完换下一段，必要时循环"""
    if not (t0 - 0.1 <= t <= t1 + 0.1): return
    durs = [M.USABLE.get(n, (0, 6))[1] - M.USABLE.get(n, (0, 6))[0] if n in M.USABLE else 6.0 for n in names]
    durs = [max(d, 1.5) for d in durs]
    k, start = 0, t0
    while start + durs[k % len(names)] < t and start + durs[k % len(names)] < t1 - 0.5:
        start += durs[k % len(names)] - xfade; k += 1
    for j in (k - 1, k):
        if j < 0: continue
        s0 = t0 + sum(durs[i % len(names)] - xfade for i in range(j))
        s1 = min(s0 + durs[j % len(names)], t1) if j == k else s0 + durs[j % len(names)]
        if j == k and s1 >= t1 - 0.5: s1 = t1
        nm = names[j % len(names)]
        fi = 0.5 if j == 0 else xfade; fo = 0.5 if s1 >= t1 else xfade
        if s0 - 0.05 <= t <= s1 + 0.05:
            fc = focus or ((0.56, 0.45) if nm.startswith('c_') and not nm.startswith('c_two') else (0.66, 0.5) if nm.startswith('c_two') else (0.5, 0.5))
            st = M.USABLE.get(nm, (0, 0))[0]
            hh = min(h, 420) if (nm.startswith('c_') and not nm.startswith('c_two')) else h
            M.frame(cv, nm, t, s0, s1, cy=cy, w=w, h=hh, z0=1.0, z1=1.04, focus=fc, a=a, fi=fi, fo=fo, src_t0=st, speed=1.0, cap=cap)


PORTRAIT = {'buffett_2010', 'buffett_2015', 'buffett_ku'}      # 人像照片：整幅入窗，不放大成大头像


def photo_win(cv, name, t, t0, t1, cy=560, w=1000, h=562, focus=(0.5, 0.5), cap=None, a=1.0, z0=1.02, z1=1.12, pan=(0, 0, 0, 0)):
    if name in PORTRAIT:
        return M.frame(cv, name, t, t0, t1, cy=cy, w=w, h=h, z0=1.0, z1=1.03, focus=focus, a=a, cap=cap, fit='contain', pan=pan)
    return M.frame(cv, name, t, t0, t1, cy=cy, w=w, h=h, z0=z0, z1=z1, focus=focus, a=a, cap=cap, pan=pan)


def qcard(cv, key, t, t0, t1, cy=1150, w=960, en=30, cn=36, a=1.0, typing=1.4):
    quote_card(cv, key, t, t0, t1, cy=cy, en_size=en, cn_size=cn, a=a, typing=typing, w=w)


def doc_page(cv, t, t0, t1, head, lines, cy=760, w=880, size=30, hl=None, hl_t=None, a=1.0, sub=None, font='typewriter'):
    """文件原文页（招股书、季报、公告、判决书）：米色纸张 + 打字机字体；hl 为需要划金线的短语，hl_t 为划线时刻"""
    al = env(t, t0, t1, 0.45, 0.4) * a
    if al <= 0.004: return
    lh = size * 1.45
    hgt = 130 + len(lines) * lh + (40 if sub else 10)
    x0, y0 = W / 2 - w / 2, cy - hgt / 2 + (1 - eo((t - t0) / 0.7)) * 24
    sh = np.zeros((int(hgt) + 60, int(w) + 60), np.float32); sh[30:-30, 30:-30] = 1
    cv.img_mul(1 - cv2.GaussianBlur(sh, (0, 0), 14) * 0.55 * al, x0 - 30, y0 - 18)
    clear_glow(cv, x0, y0, x0 + w, y0 + hgt, al)
    cv.rrect(x0, y0, x0 + w, y0 + hgt, 6, PAPER * 0.93, al)
    cv.text(head, x0 + 44, y0 + 56, 22, 'sans_med', col=INKD * 1.6, a=al, anchor='l', track=0.08)
    cv.line((x0 + 44, y0 + 84), (x0 + w - 44, y0 + 84), INKD * 2.2, al * 0.6, 1)
    y = y0 + 130
    for ln in lines:
        cv.text(ln, x0 + 44, y, size, font, col=INKD, a=al, anchor='l')
        if hl and hl in ln and hl_t is not None:
            k = eo((t - hl_t) / 0.6)
            if k > 0:
                pre = ln[:ln.index(hl)]
                xa = x0 + 44 + text_size(pre, font, size)[0]; xb = xa + text_size(hl, font, size)[0]
                cv.rect(xa - 4, y - size * 0.62, xa + (xb - xa + 8) * k, y + size * 0.5, GOLD, al * 0.38)
                cv.line((xa, y + size * 0.55), (xa + (xb - xa) * k, y + size * 0.55), GOLD_D, al, 3)
        y += lh
    if sub: cv.text(sub, x0 + w - 44, y0 + hgt - 30, 20, 'sans_light', col=INKD * 2.4, a=al, anchor='r')


def tag(cv, s, t, tw, x, y, size=30, col=GOLD, a=1.0, anchor='m'):
    k = eo((t - tw + 0.1) / 0.4)
    if k > 0: chip(cv, s, x, y + 10 * (1 - k), size, a * k, col=col, anchor=anchor)


def hbar(cv, t, rows, a, x0=300, x1=900, y0=520, dy=110, vmax=None, fmt=lambda v: f'${v:,.0f}亿', size=40, lab=34, hl=None, dur=1.0):
    """横向柱状：rows = [(标签, 数值, 出现时刻, 颜色或 None)]"""
    vmax = vmax or max(abs(r[1]) for r in rows)
    for j, (lb, v, ts, col) in enumerate(rows):
        e = eexp((t - ts) / dur)
        if e <= 0: continue
        y = y0 + j * dy
        cv.text(lb, x0 - 24, y, lab, 'sans_med', col=CREAM, a=a * min(1, e * 2), anchor='r')
        L = (x1 - x0) * abs(v) / vmax * e
        c = col if col is not None else (GOLD if hl == j else GOLD * 0.62)
        gbar(cv, x0, y - 26, x0 + max(L, 2), y + 26, c, a, horizontal=True, glow=0.2 if hl == j else 0.06, sheen_t=t - ts)
        cv.text(fmt(v), x0 + L + 18, y, size, 'sans_bold', col=GOLD_L if hl == j else CREAM, a=a * min(1, e * 2), anchor='l',
                shadow=0.6, glow=0.15 if hl == j else 0.0)


def vbars(cv, t, items, a, x0=150, x1=930, base=1250, hmax=560, fmt=lambda v: f'${v:,.0f}亿', size=42, lab=26, dur=1.1, neg_room=0):
    """竖向柱状：items = [(标签, 数值, 出现时刻, 颜色或 None, 备注)]，支持负值（向下）"""
    vmax = max(abs(i[1]) for i in items); n = len(items); bw = (x1 - x0) / n * 0.56
    if any(i[1] < 0 for i in items): neg_room = 1
    grid_lines(cv, x0 - 20, x1 + 20, base, base - hmax, a * min(1, eexp((t - min(i[2] for i in items)) / 0.8)))
    for k, (lb, v, ts, col, note_) in enumerate(items):
        e = eexp((t - ts) / dur)
        if e <= 0: continue
        cx = x0 + (x1 - x0) * (k + 0.5) / n
        h = hmax * abs(v) / vmax * e
        c = col if col is not None else GOLD * 0.75
        vv = v * e if e < 0.995 else v                      # 数字随柱子滚动到终值
        if v >= 0:
            gbar(cv, cx - bw / 2, base - h, cx + bw / 2, base, c, a, sheen_t=t - ts, reflect=neg_room == 0)
            cv.text(fmt(vv), cx, base - h - 40, size, 'sans_bold', col=CREAM, a=a * min(e * 2, 1), shadow=0.6)
        else:
            gbar(cv, cx - bw / 2, base, cx + bw / 2, base + h, c, a, sheen_t=t - ts, reflect=False)
            cv.text(fmt(vv), cx, base + h + 40, size, 'sans_bold', col=c, a=a * min(e * 2, 1), shadow=0.6)
        cv.text(lb, cx, base - 34 if v < 0 else base + 40, lab, 'sans_light', col=GREY, a=a * min(e * 2, 1))
        if note_: cv.text(note_, cx, (base - h - 86) if v >= 0 else base + h + 86, 22, 'sans_light', col=GREY, a=a * min(e * 2, 1))
    cv.line((x0 - 20, base), (x1 + 20, base), DIM, a * 0.8, 2)


def search_box(cv, t, t0, t1, cy, text, typ_t, a=1.0, w=820, click_t=None):
    """通用搜索框（示意，不使用任何公司的商标）：逐字键入，光标闪烁，可选“点击”"""
    al = env(t, t0, t1, 0.4, 0.4) * a
    if al <= 0.004: return
    x0 = W / 2 - w / 2
    cv.rrect(x0, cy - 46, x0 + w, cy + 46, 46, C(26, 28, 34), al)
    cv.rrect(x0, cy - 46, x0 + w, cy + 46, 46, GREY, al * 0.7, fill=False, th=2)
    cv.circle((x0 + 58, cy - 4), 15, GREY, al, 3); cv.line((x0 + 69, cy + 8), (x0 + 80, cy + 19), GREY, al, 3)
    n = int(cl((t - typ_t) / 0.18 * 1.0, 0, len(text)))
    s = text[:n]
    cv.text(s, x0 + 104, cy, 40, 'sans_med', col=WHITE, a=al, anchor='l')
    if (t * 2) % 2 < 1.2:
        cx = x0 + 108 + text_size(s, 'sans_med', 40)[0] if s else x0 + 104
        cv.line((cx, cy - 24), (cx, cy + 24), WHITE, al * 0.9, 2)
    if click_t is not None:
        k = t - click_t
        if 0 <= k < 0.8:
            cv.circle((x0 + w - 70, cy), 20 + 70 * k, GOLD_L, al * (1 - k / 0.8), 3)


def ruler(cv, x0, x1, y, a, p=1.0):
    L = (x1 - x0) * eo(p)
    cv.rect(x0, y - 22, x0 + L, y + 22, GOLD * 0.35, a)
    cv.line((x0, y - 22), (x0 + L, y - 22), GOLD, a, 2)
    for k in range(int(L / 20) + 1):
        xx = x0 + k * 20
        cv.line((xx, y - 22), (xx, y - (2 if k % 5 else -6)), GOLD_L, a * 0.8, 2)


# 城堡与护城河（第五章贯穿）：城堡线稿 + 五段护城河（第五段红色＝花钱挖的）
MOAT_LAB = ['习惯', '广告', '入口', '数据与技术', '算力']


def castle(cv, t, cx, cy, s, a, lit=(), lit_t=(), red=False, red_t=None, rebuild=0.0):
    if a <= 0.004: return
    # 护城河：五段弧
    R = 330 * s
    for k in range(5):
        a0 = -math.pi / 2 + k * 2 * math.pi / 5 + 0.06; a1 = a0 + 2 * math.pi / 5 - 0.12
        on = 0.0
        if k in lit: on = eo((t - lit_t[lit.index(k)]) / 0.6)
        col = BLUE_L if k < 4 else C(120, 200, 255)
        cv.arc((cx, cy), R, a0, a1, DIM, a * 0.6, 14)
        if on > 0:
            cv.arc((cx, cy), R, a0, a0 + (a1 - a0) * on, col, a, 16)
            am = (a0 + a1) / 2
            lx, ly = cx + math.cos(am) * (R + (60 + 70 * abs(math.cos(am))) * s), cy + math.sin(am) * (R + 52 * s)
            cv.text(MOAT_LAB[k], lx, ly, int(30 * s + 6), 'sans_bold', col=col, a=a * on, shadow=0.7)
    # 城堡线稿
    pts = []
    base = cy + 120 * s; top = cy - 60 * s; wd = 300 * s
    xs = np.linspace(cx - wd / 2, cx + wd / 2, 7)
    pts = [(cx - wd / 2, base), (cx - wd / 2, top)]
    for i in range(6):
        xa, xb = xs[i], xs[i + 1]; m = (xa + xb) / 2
        pts += [(xa, top), (xa, top - 26 * s if i % 2 == 0 else top), (m, top - 26 * s if i % 2 == 0 else top), (m, top)]
    pts += [(cx + wd / 2, top), (cx + wd / 2, base)]
    cv.poly(pts, GOLD, a, 3)
    tw = 70 * s
    for x in (cx - wd / 2 - tw / 2, cx + wd / 2 + tw / 2):
        cv.poly([(x - tw / 2, base), (x - tw / 2, top - 70 * s), (x, top - 120 * s), (x + tw / 2, top - 70 * s), (x + tw / 2, base)], GOLD, a, 3)
    cv.poly([(cx - 40 * s, base), (cx - 40 * s, base - 70 * s), (cx, base - 100 * s), (cx + 40 * s, base - 70 * s), (cx + 40 * s, base)], GOLD_L, a, 3)
    cv.line((cx - wd / 2 - 90 * s, base), (cx + wd / 2 + 90 * s, base), GOLD_D, a, 2)
    if rebuild > 0:                       # 脚手架：重建
        for k in range(int(12 * rebuild)):
            x = cx - wd / 2 + (k % 6) * wd / 5; yy = base - (k // 6) * 90 * s
            cv.line((x, yy), (x, yy - 90 * s), GREY, a * 0.8, 2)
            cv.line((x, yy - 90 * s), (x + wd / 5, yy - 90 * s), GREY, a * 0.8, 2)
            cv.line((x, yy), (x + wd / 5, yy - 90 * s), GREY, a * 0.5, 1)


def siege(cv, t, cx, cy, s, a, t0):
    """示意：从四面八方射向城堡的“攻击”（光点拖尾），撞上护城河处闪光"""
    if a <= 0.004 or t < t0: return
    R = 330 * s
    for k in range(9):
        ang = k * 2.4 + 0.3; per = 1.6 + (k % 3) * 0.35
        ph = ((t - t0) / per + k * 0.37) % 1.0
        if t - t0 < k * 0.25: continue
        d = lerp(R + 420, R + 8, eio(ph))
        x, y = cx + math.cos(ang) * d, cy + math.sin(ang) * d
        x2, y2 = cx + math.cos(ang) * (d + 90), cy + math.sin(ang) * (d + 90)
        col = RED if k % 2 else GOLD_L
        cv.line((x2, y2), (x, y), col, a * 0.5 * (1 - ph * 0.4), 3)
        cv.glow_dot((x, y), 7, col, a * 0.9)
        if ph > 0.92: cv.glow_dot((cx + math.cos(ang) * R, cy + math.sin(ang) * R), 30 * (ph - 0.92) / 0.08 + 8, col, a * 0.7)


def servers(cv, t, cy, a, rows=4, growth=1.0, seed=3, f=430.0):
    """示意：数据中心走廊（透视）——两侧机柜向远处延伸，指示灯闪烁，顶部灯带，镜头缓慢前推；growth 控制机柜铺开的程度"""
    if a <= 0.004: return
    rng = np.random.default_rng(seed)
    cx = W / 2
    def P(X, Y, Z): return (cx + X / Z * f, cy - Y / Z * f)
    dolly = (t * 0.6) % 1.5
    nseg = 9; Y0, Y1 = -1.25, 1.55
    vis = growth * nseg
    # 地面反光与透视线
    for X in (-2.2, -1.0, 0.0, 1.0, 2.2):
        cv.line(P(X, Y0, 1.2), P(X, Y0, 16), C(60, 90, 140), a * 0.35, 2)
    for k in range(nseg + 1):
        Z = 1.6 + k * 1.5 - dolly
        if Z < 1.2: continue
        cv.line(P(-2.2, Y0, Z), P(2.2, Y0, Z), C(50, 70, 110), a * 0.25 / (1 + k * 0.3), 1)
    # 顶部灯带
    for X in (-0.6, 0.6):                                  # 顶部灯带（从中景开始，不压上方文字）
        for k in range(14):
            Za = 2.6 + k * 0.9 - (dolly % 0.9)
            if Za < 2.6: continue
            cv.line(P(X, Y1 + 0.3, Za), P(X, Y1 + 0.3, Za + 0.5), BLUE_L, a * 0.75 / (1 + 0.12 * k), 3)
    cv.glow_dot(P(0, 0, 16), 90, BLUE_L, a * 0.35)
    for k in reversed(range(nseg)):
        if k > vis: continue
        pop = cl(vis - k)
        Za = 1.6 + k * 1.5 - dolly; Zb = Za + 1.35
        if Za < 1.25: continue
        fog = 1 / (1 + 0.16 * (Za - 1.5))
        for X in (-2.2, 2.2):
            q = [P(X, Y0, Za), P(X, Y0 + (Y1 - Y0) * pop, Za), P(X, Y0 + (Y1 - Y0) * pop, Zb), P(X, Y0, Zb)]
            cv.fillpoly(q, C(20, 26, 38) * (0.6 + 0.6 * fog), a)
            cv.poly(q + [q[0]], C(80, 110, 160) * fog, a * 0.7, 1)
            # 机柜正面的指示灯：6 列 × 10 行
            for i in range(8):
                for j in range(16):
                    if (j + 0.5) / 16 > pop: continue
                    Z = Za + (i + 0.5) / 8 * (Zb - Za); Y = Y0 + (j + 0.5) / 16 * (Y1 - Y0)
                    on = math.sin(t * (2.0 + (i * 7 + j * 3 + k) % 5) + i * 1.7 + j * 2.3 + k) > 0.25
                    if on:
                        col = GREEN if (i + j + k) % 7 == 0 else BLUE_L
                        cv.glow_dot(P(X * 0.995, Y, Z), max(1.4, 3.6 * fog * 1.6 / Z * 2), col, a * fog)
    cv.glow_dot((cx, cy), 160, C(40, 80, 160), a * 0.25)


def icon(cv, kind, x, y, s, col, a):
    """线性图标（自绘，不用任何商标）：search 放大镜 / cloud 云 / cycle 资金循环"""
    if a <= 0.004: return
    if kind == 'search':
        cv.circle((x - 8 * s, y - 8 * s), 26 * s, col, a, 4); cv.line((x + 11 * s, y + 11 * s), (x + 34 * s, y + 34 * s), col, a, 6)
    elif kind == 'cloud':
        cv.arc((x - 18 * s, y + 4 * s), 20 * s, math.pi * 0.5, math.pi * 1.5, col, a, 4)
        cv.arc((x + 2 * s, y - 10 * s), 26 * s, math.pi * 1.0, math.pi * 1.95, col, a, 4)
        cv.arc((x + 26 * s, y + 6 * s), 18 * s, math.pi * 1.5, math.pi * 2.5, col, a, 4)
        cv.line((x - 18 * s, y + 24 * s), (x + 26 * s, y + 24 * s), col, a, 4)
    elif kind == 'cycle':
        cv.arc((x, y), 32 * s, -0.3, math.pi - 0.3, col, a, 4); cv.arc((x, y), 32 * s, math.pi - 0.3 + 0.0, 2 * math.pi - 0.6, col, a, 4)
        for ang in (-0.3, math.pi - 0.3):
            px, py = x + 32 * s * math.cos(ang), y + 32 * s * math.sin(ang)
            cv.fillpoly([(px - 9 * s, py - 4 * s), (px + 9 * s, py - 4 * s), (px, py + 10 * s)], col, a)
        cv.text('$', x, y, int(34 * s), 'sans_bold', col=col, a=a)


def browser(cv, t, cx, cy, w, h, a, url, body_a=1.0):
    """示意：浏览器窗口（标签栏三点 + 地址栏 + 搜索框 + 结果条），全部为自绘线框"""
    if a <= 0.004: return
    x0, y0 = cx - w / 2, cy - h / 2
    cv.rrect(x0, y0, x0 + w, y0 + h, 18, C(20, 22, 28), a * 0.95)
    cv.rrect(x0, y0, x0 + w, y0 + h, 18, C(90, 100, 120), a * 0.6, fill=False, th=2)
    cv.rect(x0 + 2, y0 + 60, x0 + w - 2, y0 + 62, C(70, 76, 90), a)
    for k, c_ in enumerate((RED, GOLD, GREEN)): cv.circle((x0 + 34 + k * 30, y0 + 31), 8, c_, a * 0.8, -1)
    cv.rrect(x0 + 140, y0 + 14, x0 + w - 30, y0 + 48, 17, C(36, 40, 50), a)
    cv.text(url, x0 + 164, y0 + 31, 24, 'mono', col=CREAM, a=a, anchor='l')
    ba = a * body_a
    cv.rrect(cx - w * 0.36, y0 + 150, cx + w * 0.36, y0 + 210, 30, C(36, 40, 50), ba)
    cv.rrect(cx - w * 0.36, y0 + 150, cx + w * 0.36, y0 + 210, 30, GREY, ba * 0.6, fill=False, th=2)
    for k in range(4):
        yy = y0 + 270 + k * 62
        cv.rect(x0 + 60, yy, x0 + 60 + (w - 200) * (0.55 + 0.1 * ((k * 7) % 4)), yy + 14, BLUE_L * 0.6, ba * 0.7)
        cv.rect(x0 + 60, yy + 24, x0 + 60 + (w - 160) * 0.8, yy + 32, GREY * 0.6, ba * 0.6)


def ticket(cv, t, cx, cy, a, price_old=None, price_new=None, strike_t=None, label='补票'):
    if a <= 0.004: return
    w, h = 620, 280
    cv.rrect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, 18, C(40, 32, 22), a)
    cv.rrect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, 18, GOLD, a * 0.8, fill=False, th=3, glow=0.2)
    for k in range(10): cv.circle((cx + w / 2 - 150, cy - h / 2 + 20 + k * 26), 4, GOLD_D, a, -1 if False else 2)
    cv.text(label, cx - 110, cy - 60, 54, 'serif_black', gold=True, a=a)
    cv.text('ADMIT ONE · 2004 → 2025', cx - 110, cy + 2, 22, 'corm', col=GOLD, a=a, track=0.2)
    if price_old:
        cv.text(price_old, cx - 110, cy + 74, 46, 'sans_bold', col=CREAM, a=a)
        if strike_t is not None:
            k = eo((t - strike_t) / 0.4)
            tw = text_size(price_old, 'sans_bold', 46)[0]
            if k > 0: cv.line((cx - 110 - tw / 2 - 8, cy + 74), (cx - 110 - tw / 2 - 8 + (tw + 16) * k, cy + 70), RED, a, 5)
            if price_new and k >= 1:
                cv.text(price_new, cx + w / 2 - 75, cy + 10, 46, 'sans_bold', col=RED, a=a * eo((t - strike_t - 0.4) / 0.4), glow=0.2)


def big_q(cv, t, txt, y, tw, size=60, a=1.0, col=None):
    k = eo((t - tw + 0.1) / 0.5)
    if k > 0:
        if col is None: cv.text(txt, W / 2, y + 16 * (1 - k), size, 'serif_black', gold=True, a=a * k, glow=0.2, shadow=0.8)
        else: cv.text(txt, W / 2, y + 16 * (1 - k), size, 'serif_black', col=col, a=a * k, shadow=0.8)


def note(cv, s, y, a, size=24, col=None):
    if a > 0.004: cv.text(s, W / 2, y, size, 'sans_light', col=col if col is not None else GREY, a=a)


# ======================================================================== 开场
def shot_hook(cv, t):
    a0 = env(t, 0, S('h1') + 0.6, 0.0, 0.5)
    if a0 > 0:
        L = 420 * eo(t / 1.1); hb = math.exp(-max(t - 0.25, 0) * 6) * (t >= 0.25)
        cv.line((W / 2 - L, 960), (W / 2 + L, 960), GOLD, a0 * (0.5 + 0.5 * hb), 2)
        cv.glow_dot((W / 2, 960), 30 + 40 * hb, GOLD, a0 * 0.6)
    # h1：2017 年股东大会，当众认错（环境全景 → 引语卡）
    t0, t1 = win('h1')
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        seq(cv, t, t0, t0 + 2.9, ['e_brk2026'], h=562, cap='伯克希尔股东大会（2026）')
        photo_win(cv, 'brk_meeting_2025', t, t0 + 2.4, t1, cap='伯克希尔股东大会现场（2025 年照片）', focus=(0.5, 0.45), z0=1.0, z1=1.06,
                  pan=(0.02, 0, -0.02, 0))
        tag(cv, '2017 · 伯克希尔股东大会', t, t0 + 0.4, W / 2, 940, 28, GOLD, a)
        qcard(cv, 'qblew', t, WT('h1', '搞砸了') - 0.7, t1, cy=1180, en=46, cn=46)
    # h2：八年后买进 → 第三大持仓 → 最新季报仍在前五
    t0, t1 = win('h2')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        tb = WT('h2', '开始买进')
        cv.text('伯克希尔前五大股票持仓 · 市值', W / 2, 360, 36, 'sans_med', col=CREAM, a=a)
        cv.text('SEC 13F · 2026-06-30', W / 2, 410, 24, 'corm', col=GOLD, a=a, track=0.15)
        tw = WT('h2', '第三大')
        rows = [('苹果', 659.5, t0 + 0.3, None), ('美国运通', 512.8, t0 + 0.5, None), ('谷歌 A+C', 377.6, tw - 0.3, GOLD),
                ('可口可乐', 325.1, t0 + 0.7, None), ('美国银行', 275.4, t0 + 0.9, None)]
        hbar(cv, t, rows, a, x0=300, x1=820, y0=540, dy=118, hl=2)
        tag(cv, 'No.3', t, tw + 0.4, 990, 776, 30, GOLD, a)
        tq = WT('h2', '最新季报')
        # 先让“第一次买进”标签完全淡出，再升起 10-Q 卡片，二者不在同一位置叠印
        ka = 1 - eo((t - (tq - 0.75)) / 0.35)
        if ka > 0.004: tag(cv, '2025 年三季度 · 第一次买进', t, tb, W / 2, 1180, 26, CREAM, a * ka)
        k = eo((t - (tq - 0.3)) / 0.5)
        if k > 0:
            cv.rrect(140, 1130 + 20 * (1 - k), 940, 1290 + 20 * (1 - k), 14, C(30, 26, 22), a * k * 0.95)
            cv.rrect(140, 1130 + 20 * (1 - k), 940, 1290 + 20 * (1 - k), 14, GOLD_D, a * k * 0.6, fill=False, th=2)
            # Cormorant 没有中文字形：英文用 corm，中文另起一段用黑体
            cv.text('FORM 10-Q · 2026-09-30', W / 2 - 70, 1180 + 20 * (1 - k), 24, 'corm', col=GOLD, a=a * k, track=0.08)
            cv.text('前五大持仓', W / 2 + 170, 1180 + 20 * (1 - k), 24, 'sans_med', col=GOLD, a=a * k)
            cv.text('Alphabet · 美国运通 · 苹果 · 美国银行 · 可口可乐', W / 2, 1240 + 20 * (1 - k), 30, 'sans_med', col=CREAM, a=a * k)
        source(cv, 'SEC 13F 原件（Alphabet A 7,879 万股 + C 2,719 万股，合计 $377.6 亿）；伯克希尔 2026 年三季度 10-Q（按字母顺序）', a, y=1462)
    # h3：引入原声——先给双人全景（采访现场），再切入原声中景
    t0, t1 = S('h3') - 0.3, S('sot_dontlike') - SEG['sot_dontlike']['lead'] + 0.2
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        seq(cv, t, t0, t1, ['c_two_e'], h=562)
        tag(cv, '2026 年 7 月 15 日 · CNBC 专访', t, t0 + 0.3, W / 2, 900, 26, GOLD, a)
        big_q(cv, t, '他却这么说 ——', 1120, WT('h3', '却说'), 52, a, col=CREAM)
    # h4：三个问题 → 2004
    t0, t1 = S('h4') - 0.3, CH['title'][0] + 0.1
    a = env(t, t0, t1, 0.4, 0.2)
    if a > 0:
        qs = [('当年为什么错过？', S('h4'), CREAM), ('二十年后，又为什么决定买入？', WT('h4', '二十年后'), CREAM),
              ('既然买了，为什么仍有保留？', WT('h4', '既然'), None)]
        for j, (q, tq, col) in enumerate(qs):
            k = eo((t - tq + 0.1) / 0.5)
            if k <= 0: continue
            y = 620 + j * 150
            cv.text(f'0{j + 1}', 150, y, 40, 'oswald', col=GOLD, a=a * k, anchor='l')
            cv.line((210, y - 26), (210, y + 26), GOLD_D, a * k, 2)
            if col is None: cv.text(q, 236 + 20 * (1 - k), y, 50, 'serif_black', gold=True, a=a * k, anchor='l', glow=0.2, shadow=0.8)
            else: cv.text(q, 236 + 20 * (1 - k), y, 50, 'serif_semi', col=col, a=a * k, anchor='l', shadow=0.8)
        k = eo((t - WT('h4', '2004') + 0.1) / 0.5)
        if k > 0: cv.text('2004', W / 2, 1180, 150, 'oswald', col=GOLD, a=a * k * 0.9, glow=0.3)


def shot_title(cv, t):
    t0, t1 = CH['title'][0], CH['ch1'][0] + 0.6
    a = env(t, t0, t1, 0.02, 0.6)
    if a <= 0: return
    p = t - t0
    flash = math.exp(-p * 5.0)
    ticket(cv, t, W / 2, 700, a * eo(p / 0.35), label='补票')
    R = 60 + p * 900
    cv.circle((W / 2, 720), R, GOLD, a * math.exp(-p * 2.2) * 0.8, 3)
    cv.glow_dot((W / 2, 720), 220, GOLD, a * flash * 0.9)
    k = eo((p - 0.15) / 0.6)
    cv.text('二十年后的补票', W / 2, 1100, 120, 'serif_black', gold=True, a=a * k, glow=0.3, scale=1.08 - 0.08 * k)
    cv.text('巴菲特为什么出手谷歌', W / 2, 1250, 60, 'serif_semi', col=CREAM, a=a * eo((p - 0.5) / 0.6))
    cv.text('A TICKET TWENTY YEARS LATE', W / 2, 1350, 26, 'corm', col=GOLD, a=a * eo((p - 1.0) / 0.6), track=0.35)


# ======================================================================== 第一章：写给巴菲特的上市信
def shot_ch1(cv, t):
    t0, t1 = win('c1a', pre=0.1)
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('2004 · 谷歌准备上市', W / 2, 360, 40, 'sans_med', col=CREAM, a=a)
        doc_page(cv, t, t0 + 0.2, t1, 'FORM S-1 · FOUNDERS’ LETTER · 2004',
                 ['2004 FOUNDERS’ IPO LETTER', '', '“An Owner’s Manual” for', 'Google’s Shareholders', '',
                  'Google is not a conventional company.', 'We do not intend to become one.'],
                 cy=820, w=900, size=32, hl='Google is not a conventional company.', hl_t=WT('c1a', '谷歌不是'), a=a)
        k = eo((t - WT('c1a', '谷歌不是') + 0.2) / 0.5)
        if k > 0: cv.text('谷歌不是一家传统的公司。', W / 2, 1300, 48, 'serif_semi', col=GOLD_L, a=a * k, shadow=0.7)
        source(cv, '谷歌 2004 年 S-1 招股书 · 创始人信', a, y=1462)
    t0, t1 = win('c1b')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        tm = WT('c1b', '脚注')
        k1 = 1 - eo((t - tm + 0.3) / 0.6)
        if k1 > 0:
            for j, (h, sub, x) in enumerate([('An Owner’s Manual', 'for Google’s Shareholders · 2004', 300),
                                              ('An Owner’s Manual', 'Berkshire Hathaway', 780)]):
                kk = eo((t - t0 - 0.3 - j * 0.6) / 0.5) * k1
                cv.rrect(x - 210, 520, x + 210, 1000, 8, PAPER * 0.92, a * kk)
                cv.text(h, x, 660, 34, 'playfair', col=INKD, a=a * kk)
                cv.text(sub, x, 720, 20, 'sans_med', col=INKD * 2, a=a * kk)
                for r in range(8): cv.line((x - 160, 800 + r * 22), (x + 160 - (r % 3) * 40, 800 + r * 22), INKD * 3, a * kk * 0.5, 2)
            cv.text('≈', W / 2, 760, 90, 'serif_black', gold=True, a=a * eo((t - t0 - 1.4) / 0.5) * k1)
            cv.text('几乎同名', W / 2, 1100, 46, 'serif_semi', col=GOLD_L, a=a * eo((t - t0 - 1.6) / 0.5) * k1)
        qcard(cv, 'qfoot', t, tm - 0.3, t1, cy=820, en=30, cn=36)
        source(cv, '谷歌 2004 年 S-1，创始人信脚注 1；伯克希尔《股东手册》（An Owner’s Manual）', a, y=1462)
    t0, t1 = win('c1c')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('双层股权：创始人握住投票权（示意）', W / 2, 400, 34, 'sans_med', col=CREAM, a=a)
        p = eo((t - t0 - 0.3) / 1.0)
        for j, (lb, share, col) in enumerate([('A 类股（公众）', 0.25, GREY), ('B 类股（创始人与高管）', 0.75, GOLD)]):
            y = 560 + j * 130
            cv.text(lb, 140, y - 40, 28, 'sans_med', col=CREAM, a=a, anchor='l')
            cv.rect(140, y - 18, 140 + 800 * share * p, y + 18, col, a, glow=0.1)
        note(cv, '只示意“投票权集中”，不代表真实比例；谷歌与伯克希尔两家的投票权比例并不相同', 860, a * p, 22)
        qcard(cv, 'qdual', t, WT('c1c', '伯克希尔') - 0.5, t1, cy=1130, en=30, cn=36)
    t0, t1 = win('c1d')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        photo_win(cv, 'omaha_river', t, t0, t1, cap='奥马哈', focus=(0.5, 0.55))
        for j, nm in enumerate(['施密特', '佩奇', '布林']):
            tag(cv, nm, t, WT('c1d', nm), 260 + j * 280, 930, 34, GOLD, a)
        qcard(cv, 'qvisit', t, WT('c1d', '只不过那次') - 0.4, t1, cy=1180, en=28, cn=34)
    t0, t1 = win('c1e')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('GEICO（伯克希尔旗下保险公司）', W / 2, 380, 34, 'sans_med', col=CREAM, a=a)
        search_box(cv, t, t0, t1, 520, '车险报价', t0 + 0.4, a)
        for k in range(3):
            y = 660 + k * 70; kk = eo((t - t0 - 1.0 - k * 0.3) / 0.4)
            cv.rrect(170, y - 26, 910, y + 26, 8, C(30, 30, 36), a * kk)
            cv.text('广告 · 汽车保险，几分钟拿到报价' if k == 0 else '搜索结果', 200, y, 26, 'sans_med' if k == 0 else 'sans_light',
                    col=GOLD_L if k == 0 else GREY, a=a * kk, anchor='l')
        note(cv, '示意画面', 880, a * 0.8, 20)
        qcard(cv, 'qmystery0', t, WT('c1e', '巴菲特说') - 0.4, t1, cy=1150, en=30, cn=36)
    t0, t1 = S('c1f') - 0.3, CH['tk_ch1'][0]
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = eo((t - t0) / 2.4)
        xs = np.linspace(0, p, 60)
        pts = [(140 + 800 * x, 1180 - 460 * x ** 1.7) for x in xs]
        # 曲线下的渐变面积
        for k in range(len(pts) - 1):
            (xa, ya), (xb, yb) = pts[k], pts[k + 1]
            cv.fillpoly([(xa, ya), (xb, yb), (xb, 1180), (xa, 1180)], GOLD * 0.35, a * 0.35)
        cv.poly(pts, GOLD_L, a, 5)
        hx, hy = pts[-1]
        cv.glow_dot((hx, hy), 14, GOLD_L, a); cv.glow_dot((hx, hy), 40, GOLD, a * 0.5)
        cv.poly([(140, 1180), (140 + 800 * p, 1180)], GREY, a, 4)
        cv.text('谷歌的生意', hx - 20, hy - 44, 32, 'sans_bold', col=GOLD_L, a=a * p, anchor='r', shadow=0.7)
        cv.text('伯克希尔的谷歌持仓：0', 940, 1230, 30, 'sans_med', col=GREY, a=a * p, anchor='r')
        for yr, x in (('2004', 0.0), ('2017', 1.0)):
            cv.text(yr, 140 + 800 * x, 1280, 26, 'oswald', col=GREY, a=a * p)
        note(cv, '示意', 1330, a * 0.7, 20)
        big_q(cv, t, '可他，没有买。', 480, S('c1f'), 66, a)


# ======================================================================== 第二章：我搞砸了
def shot_ch2(cv, t):
    t0, t1 = win('c2a')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        search_box(cv, t, t0, t1, 470, '车险', t0 + 0.3, a, click_t=WT('c2a', '随手点一下'))
        tc = WT('c2a', '随手点一下')
        n = int(cl((t - tc) / 0.45, 0, 6))
        if t >= tc:
            cv.text(f'${10.5 * max(n, 1):,.0f}', W / 2, 720, 130, 'sans_bold', gold=True, a=a, glow=0.3)
            cv.text(f'点击 × {max(n, 1)}', W / 2, 820, 30, 'sans_light', col=GREY, a=a)
        note(cv, '示意：每次点击约 10–11 美元（巴菲特 2017 年回忆）', 880, a * 0.8, 22)
        qcard(cv, 'qbucks', t, WT('c2a', '巴菲特回忆') - 0.3, t1, cy=1150, en=28, cn=34)
    t0, t1 = win('c2b')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = eo((t - t0 - 0.2) / 1.6)
        x0, x1, y0, y1 = 160, 920, 420, 820
        cv.line((x0, y1), (x1, y1), DIM, a, 2); cv.line((x0, y0), (x0, y1), DIM, a, 2)
        xs = np.linspace(0, 1, 60) * p
        cv.poly(np.stack([x0 + xs * (x1 - x0), y1 - (y1 - y0) * xs ** 1.4], 1), GOLD_L, a, 4)
        cv.poly(np.stack([x0 + xs * (x1 - x0), y1 - 10 - 6 * xs], 1), BLUE_L, a, 4)
        cv.text('广告收入', x1, y0 - 10, 28, 'sans_bold', col=GOLD_L, a=a * p, anchor='r')
        cv.text('每多一次广告的成本', x1, y1 - 50, 26, 'sans_med', col=BLUE_L, a=a * p, anchor='r')
        note(cv, '示意 · 这是巴菲特的看法；谷歌实际还要支付流量获取成本', 870, a * 0.8, 22)
        qcard(cv, 'qincr', t, WT('c2b', 'GEICO 付了') - 0.3, t1, cy=1150, en=30, cn=36)
    t0, t1 = win('c2c')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        photo_win(cv, 'buffett_2015', t, t0, t1, focus=(0.5, 0.3), cap='巴菲特 · 2015')
        qcard(cv, 'qblew', t, WT('c2c', '可我搞砸了') - 0.6, t1, cy=1130, en=44, cn=44)
        tag(cv, '2017 年股东大会', t, t0 + 0.4, W / 2, 945, 26, GOLD, a)
    t0, t1 = win('c2d')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('查理·芒格', W / 2, 420, 54, 'serif_black', gold=True, a=a)
        cv.text('CHARLIE MUNGER · 1924–2023', W / 2, 490, 24, 'corm', col=GOLD, a=a, track=0.25)
        tag(cv, '2017 年股东大会', t, t0 + 0.4, W / 2, 570, 26, GOLD, a)
        qcard(cv, 'qmunger17', t, t0 + 0.3, t1, cy=920, en=32, cn=38)
    t0, t1 = win('c2e')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        tm = WT('c2e', '又过了一年')
        tag(cv, '2018', t, t0 + 0.2, W / 2, 400, 30, GOLD, a * (1 - eo((t - tm + 0.4) / 0.4)))
        qcard(cv, 'qwrong', t, t0 + 0.2, tm - 0.1, cy=760, en=40, cn=42)
        tag(cv, '2019', t, tm, W / 2, 900, 30, GOLD, a)
        qcard(cv, 'qthumbs', t, tm - 0.1, t1, cy=1160, en=40, cn=42)
    t0, t1 = S('c2f') - 0.3, CH['tk_ch2'][0]
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        search_box(cv, t, t0, t1, 760, '', t0, a)
        big_q(cv, t, '看得懂，也认了错', 560, S('c2f'), 54, a, col=CREAM)
        big_q(cv, t, '当年为什么没有出手？', 980, WT('c2f', '原因'), 60, a)


# ======================================================================== 第三章：卡在哪里
ENGINES = ['AltaVista', 'Lycos', 'Excite', 'Yahoo!', 'Google']


def shot_ch3(cv, t):
    t0, t1 = win('c3a')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        tag(cv, '2018 年股东大会', t, t0 + 0.2, W / 2, 380, 28, GOLD, a)
        tg = WT('c3a', '比尔·盖茨')
        k = eo((t - tg) / 0.8)
        ka = eo((t - WT('c3a', 'AltaVista') + 0.3) / 0.6)
        # 浏览器：先是 AltaVista，盖茨的建议之后切到 Google（地址栏文字示意）
        bw_, bh_ = 900, 560
        sl = 60 * (1 - eo((t - t0) / 0.7))
        browser(cv, t, W / 2, 800 + sl, bw_, bh_, a * (1 - k), 'www.altavista.com', body_a=0.35 + 0.65 * ka)
        if k > 0:
            browser(cv, t, W / 2 + 40 * (1 - k), 850, bw_, bh_, a * k, 'www.google.com')
            cv.rrect(W / 2 - 300, 1170, W / 2 + 300, 1250, 40, C(30, 40, 60), a * k * 0.95)
            cv.text('比尔·盖茨：换成这个吧', W / 2, 1210, 34, 'sans_med', col=BLUE_L, a=a * k)
        cv.text('1990 年代 · 他用的搜索引擎', W / 2, 470, 34, 'sans_med', col=CREAM, a=a * ka * (1 - k))
        note(cv, '示意：自绘线框，非真实网页与商标', 1300, a * 0.7, 20)
        source(cv, '2018 年伯克希尔股东大会，CNBC 编辑版文字稿', a, y=1462)
    t0, t1 = win('c3b')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = cl((t - t0) / max(WT('c3b', '也正因为') - t0, 0.1))
        vals = [0.9 - 0.5 * p, 0.6 - 0.25 * p, 0.5 - 0.2 * p, 0.7 - 0.1 * p, 0.3 + 0.7 * p]
        for j, (nm, v) in enumerate(zip(ENGINES, vals)):
            y = 440 + j * 80
            col = GOLD if nm == 'Google' else GREY
            cv.text(nm, 330, y, 30, 'playfair', col=col, a=a, anchor='r')
            cv.rect(350, y - 16, 350 + 520 * v, y + 16, col, a * 0.85)
        kq = eo((t - WT('c3b', '会不会') + 0.2) / 0.5)
        if kq > 0:
            cv.rrect(350, 830, 900, 866, 6, GOLD, a * kq * 0.25)
            cv.text('？', 330, 848, 40, 'sans_bold', col=GOLD_L, a=a * kq, anchor='r')
        note(cv, '示意：早期搜索引擎此消彼长（不代表真实份额）', 920, a * 0.8, 22)
        qcard(cv, 'qskip', t, WT('c3b', '也正因为') - 0.4, t1, cy=1170, en=28, cn=34)
    t0, t1 = win('c3c')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        # 示意：行业利润池——竞争者越来越多，每家分到的越来越少，整个池子也在缩小
        cx, cy, R0 = W / 2, 610, 190
        tn = WT('c3c', '竞争者'); tk = WT('c3c', '谁都赚不到')
        n = 1 + int(4 * cl((t - tn + 0.3) / max(WT('c3c', '四五家') - tn + 0.6, 0.5)))
        shrink = eo((t - tk) / 1.4)
        R = R0 * (1 - 0.32 * shrink)
        cols = [GOLD, BLUE_L, CREAM * 0.8, C(150, 120, 200), RED]
        if n == 1:
            cv.circle((cx, cy), R, cols[0], a * 0.9, 2)
        for j in range(n):
            if n == 1:
                cv.circle((cx, cy), R - 1, cols[0] * 0.55, a * 0.8, -1); break
            a0 = -math.pi / 2 + j * 2 * math.pi / n + 0.03; a1 = -math.pi / 2 + (j + 1) * 2 * math.pi / n - 0.03
            kk = eo((t - tn - 0.25 * j) / 0.5) if n > 1 else 1.0
            us = np.linspace(a0, a0 + (a1 - a0) * kk, 40)
            pts = [(cx + R * math.cos(u), cy + R * math.sin(u)) for u in us] + [(cx + 86 * math.cos(u), cy + 86 * math.sin(u)) for u in us[::-1]]
            cv.fillpoly(pts, cols[j] * 0.55, a * 0.8)
            cv.poly(pts + [pts[0]], cols[j], a * 0.9, 2)
            am = (a0 + a1) / 2
            cv.text('ABCDE'[j], cx + (R + 34) * math.cos(am), cy + (R + 34) * math.sin(am), 28, 'oswald', col=cols[j], a=a * kk)
        cv.circle((cx, cy), R0 + 2, DIM, a * 0.5 * shrink, 2)
        cv.text('行业利润', cx, cy - (12 if shrink > 0 else 0), 28, 'sans_bold', col=WHITE, a=a, shadow=0.9)
        if shrink > 0: cv.text('在缩小', cx, cy + 26, 24, 'sans_med', col=RED, a=a * shrink, shadow=0.9)
        note(cv, '示意：几家互相厮杀，谁都赚不到该赚的钱', 900, a * 0.8, 22)
        qcard(cv, 'qmystery', t, WT('c3c', '神秘的是') - 0.4, t1, cy=1150, en=30, cn=36)
    t0, t1 = win('c3d')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = eo((t - t0) / 0.9); p2 = eo((t - WT('c3d', '确信') + 0.2) / 0.9)
        # 左：今天——清晰、明亮的上升台阶
        cv.rrect(80, 420, 520, 960, 22, C(34, 30, 24), a * p)
        cv.rrect(80, 420, 520, 960, 22, GOLD, a * p * 0.8, fill=False, th=2, glow=0.15)
        cv.text('看懂', 300, 490, 46, 'serif_black', gold=True, a=a * p)
        cv.text('今天怎么赚钱', 300, 550, 28, 'sans_med', col=CREAM, a=a * p)
        for k in range(5):
            e = eexp((t - t0 - 0.3 - k * 0.15) / 0.6)
            if e > 0: gbar(cv, 130 + k * 74, 900 - (60 + k * 50) * e, 180 + k * 74, 900, GOLD, a * p, sheen_t=t - t0, reflect=False)
        # 右：十年后——雾中的分岔线，问号
        cv.rrect(560, 420, 1000, 960, 22, C(24, 26, 34), a * p2)
        cv.rrect(560, 420, 1000, 960, 22, GREY, a * p2 * 0.6, fill=False, th=2)
        cv.text('确信', 780, 490, 46, 'serif_black', col=CREAM, a=a * p2)
        cv.text('十年后还能赢', 780, 550, 28, 'sans_med', col=GREY, a=a * p2)
        for j in range(6):
            pts = [(600 + 360 * x, 880 - 220 * x + (j - 2.5) * 70 * x ** 1.5 + 14 * math.sin(x * 7 + t * 1.2 + j)) for x in np.linspace(0, 1, 30)]
            cv.poly(pts, [GOLD, BLUE_L, GREY, RED, CREAM, GREY][j], a * p2 * (0.75 - 0.08 * j), 3)
        cv.text('?', 780, 690, 120, 'serif_black', col=GOLD_L, a=a * p2 * 0.45, glow=0.2)
        big_q(cv, t, '是两回事', 1130, WT('c3d', '是两回事'), 76, a)
    t0, t1 = win('c3e')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('GOOGL 股价（拆股调整）', W / 2, 380, 34, 'sans_med', col=CREAM, a=a)
        items = [('2017-05-05 收盘', 47.51, t0 + 0.5, GREY, '说“我搞砸了”时'),
                 ('2025 年三季度均价', 209.46, WT('c3e', '209'), GOLD, '伯克希尔第一次买进')]
        vbars(cv, t, items, a, x0=200, x1=880, base=1220, hmax=640, fmt=lambda v: f'${v:,.1f}' if v < 100 else f'${v:,.0f}', size=52, lab=26)
        tag(cv, '× 4.4', t, WT('c3e', '四倍多'), W / 2, 560, 44, GOLD, a)
        note(cv, '股价倍数不等于估值倍数，同期利润也在增长', 1320, a * 0.85, 22)
        source(cv, 'Yahoo Finance 日线收盘价（GOOGL，拆股调整）；三季度均价为日均收盘', a, y=1462)
    t0, t1 = S('c3f') - 0.3, CH['tk_ch3'][0]
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        ticket(cv, t, W / 2, 800, a, price_old='$47', price_new='$209', strike_t=t0 + 0.8)
        big_q(cv, t, '可伯克希尔还是买了', 1100, WT('c3f', '还是买了'), 62, a)


# ======================================================================== 第四章：是谁拍的板
def shot_ch4(cv, t):
    t0, t1 = win('c4a')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('SEC 13F · 2025-09-30 · BERKSHIRE HATHAWAY', W / 2, 380, 26, 'corm', col=GOLD, a=a, track=0.12)
        kt = eo((t - t0 - 0.2) / 0.6)
        cv.text('NAME OF ISSUER', 150, 460, 22, 'mono', col=GREY, a=a * kt, anchor='l')
        cv.text('SHARES', 760, 460, 22, 'mono', col=GREY, a=a * kt, anchor='r')
        cv.text('VALUE', 930, 460, 22, 'mono', col=GREY, a=a * kt, anchor='r')
        cv.line((120, 492), (120 + 840 * kt, 492), GOLD_D, a, 2)
        rows = [('ALPHABET INC CL A', '17,846,142', '$4,338M', WT('c4a', '1785')), ('APPLE INC', '减持', '', WT('c4a', '减持苹果'))]
        for j, (nm, sh_, v, ts) in enumerate(rows):
            k = eo((t - ts + 0.2) / 0.5)
            k0 = eo((t - t0 - 0.4 - j * 0.15) / 0.5)
            y = 590 + j * 170
            cv.rrect(120, y - 42, 960, y + 42, 8, C(26, 26, 30), a * k0)
            if k > 0:
                cv.rrect(120, y - 42, 960, y + 42, 8, GOLD_L if j == 0 else RED, a * k * 0.7, fill=False, th=2, glow=0.25)
                if 0 < t - ts + 0.2 < 0.9: cv.glow_dot((120 + 840 * eio((t - ts + 0.2) / 0.9), y - 42), 22, GOLD_L, a * 0.8)
            cv.text(nm, 150, y, 30, 'mono', col=GOLD_L if j == 0 else CREAM, a=a * k0 * (0.35 + 0.65 * k), anchor='l')
            cv.text(sh_, 760, y, 30, 'mono', col=GOLD_L if j == 0 else RED, a=a * k, anchor='r')
            cv.text(v, 930, y, 26, 'mono', col=GREY, a=a * k, anchor='r')
            if j == 0: tag(cv, 'NEW · 新建仓', t, ts + 0.3, 960, y + 84, 22, GOLD, a, anchor='r')
        tn = WT('c4a', '43')
        big_num(cv, t, tn, '≈ $43 亿', 1010, size=110, a=a)
        cv.text('三季度新买入 · 季末市值', W / 2, 1120, 30, 'sans_light', col=CREAM, a=a * eo((t - tn - 0.3) / 0.5), shadow=0.7)
        source(cv, '伯克希尔 2025 年三季度 13F（2025-11-14 提交）', a, y=1462)
    t0, t1 = win('c4b')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('谁做的决定？', W / 2, 400, 60, 'serif_black', gold=True, a=a)
        for j, (nm, ts) in enumerate([('巴菲特本人', WT('c4b', '巴菲特本人')), ('接班人阿贝尔', WT('c4b', '阿贝尔')),
                                      ('投资经理', WT('c4b', '投资经理'))]):
            k = eo((t - ts + 0.15) / 0.4)
            x = 220 + j * 320
            cv.circle((x, 720), 90, GOLD if k > 0.5 else DIM, a, 3)
            cv.circle((x, 690), 32, GREY, a * k, 3); cv.arc((x, 790), 58, math.pi, 2 * math.pi, GREY, a * k, 3)
            cv.text('?', x, 720, 70, 'serif_black', col=GOLD_L, a=a * k * 0.5)
            cv.text(nm, x, 860, 30, 'sans_med', col=CREAM, a=a * k)
        note(cv, '“这是巴菲特卸任 CEO 前的最后一份持仓报告”', 980, a, 26, col=CREAM)
        source(cv, 'Fortune 2025-11-15：不清楚是巴菲特、阿贝尔还是其他人做的决定', a, y=1462)
    t0, t1 = win('c4c')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        ti = WT('c4c', '是我发起的')
        seq(cv, t, t0, t1, ['c_two_a', 'c_initiated', 'c_approve'], h=430)
        tag(cv, '2026 年 7 月 15 日 · CNBC 专访', t, t0 + 0.3, W / 2, 870, 26, GOLD, a)
        qcard(cv, 'qinit', t, ti - 0.5, t1, cy=1160, en=34, cn=44, typing=1.0)
        if ti - 0.1 <= t <= ti + 1.2:
            cv.glow_dot((W / 2, 1160), 420 * eo((t - ti) / 0.3), GOLD, 0.35 * (1 - eo((t - ti - 0.3) / 0.9)) * a)
    t0, t1 = win('c4d')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        photo_win(cv, 'buffett_ku', t, t0, t1, focus=(0.55, 0.35), cap='巴菲特 · 2005')
        big_num(cv, t, S('c4d') + 0.6, '95 岁', 1060, size=160, a=a, sub='2025 年 · 第一笔谷歌')
        big_q(cv, t, '最后来补这张票的，还是他自己', 1330, WT('c4d', '最后来补'), 44, a, col=CREAM)
    t0, t1 = win('c4e')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['e_abel', 'c_approve', 'e_brk2026'], h=430, cap=None)
        kb = 1.0
        for j, (lb, v, ts) in enumerate([('2025-09-30', 1785, t0 + 0.3), ('2026-03-31', 5784, WT('c4e', '继续加仓'))]):
            e = eexp((t - ts) / 1.0)
            if e <= 0: continue
            x = 360 + j * 360; h = 300 * v / 5784 * e
            cv.rect(x - 70, 1300 - h, x + 70, 1300, GOLD if j else GOLD * 0.6, a * kb)
            cv.text(f'{v:,} 万股', x, 1300 - h - 36, 34, 'sans_bold', col=CREAM, a=a * kb * min(e * 2, 1))
            cv.text(lb, x, 1335, 22, 'sans_light', col=GREY, a=a * kb)
        big_q(cv, t, '现在由谁拍板？', 1398, WT('c4e', '由谁拍板'), 52, a)
        source(cv, '13F 2026-03-31（A 5,425 万 + C 359 万股）', a, y=1462)
    t0, t1 = win('c4e2')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['c_approve'], h=470)
        qcard(cv, 'qapprove', t, WT('c4e2', '阿贝尔不赞成') - 0.5, t1, cy=1170, en=30, cn=38)
        source(cv, 'CNBC 专访 2026-07-15', a, y=1462)
    t0, t1 = win('c4f')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['e_abel'], h=470, cap='阿贝尔')
        tr = WT('c4f', '一个周日')
        if t >= tr:
            for k in range(3):
                rr = ((t - tr) * 1.2 + k / 3) % 1
                cv.circle((W / 2, 1000), 50 + 110 * rr, GOLD, a * (1 - rr) * 0.8, 3)
            cv.text('周日早上', W / 2, 1000, 34, 'sans_bold', col=CREAM, a=a)
        big_num(cv, t, WT('c4f', '100'), '$100 亿？', 1260, size=100, a=a)
        cv.text('“10 billion and more”', W / 2, 1350, 26, 'corm', col=CREAM, a=a * eo((t - WT('c4f', '100') - 0.4) / 0.5))
        source(cv, '阿贝尔 CNBC 专访 2026-09-02', a, y=1462)
    t0, t1 = win('c4g')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        tm = WT('c4g', '6 月 1 日')
        qcard(cv, 'qabel65', t, t0 + 0.2, tm - 0.1, cy=760, en=30, cn=36)
        doc_page(cv, t, tm - 0.2, t1, 'ALPHABET · PRESS RELEASE · JUNE 1, 2026',
                 ['Alphabet has reached an agreement to sell', '$10 billion of stock to Berkshire Hathaway Inc.',
                  'in a private placement'], cy=700, w=960, size=30, hl='$10 billion of stock to Berkshire Hathaway Inc.',
                 hl_t=WT('c4g', '出资'), a=a)
        k = eo((t - WT('c4g', '新发行的股票') + 0.2) / 0.5)
        if k > 0:
            for j, (cls, sh_, px) in enumerate([('A 类', '1,421 万股', '$351.81'), ('C 类', '1,436 万股', '$348.20')]):
                y = 1080 + j * 110
                cv.rrect(160, y - 42, 920, y + 42, 10, C(28, 26, 24), a * k)
                cv.text(cls, 200, y, 34, 'sans_bold', col=GOLD, a=a * k, anchor='l')
                cv.text(sh_, 540, y, 34, 'sans_med', col=CREAM, a=a * k)
                cv.text('× ' + px, 880, y, 34, 'sans_bold', col=GOLD_L, a=a * k, anchor='r')
            note(cv, 'A、C 类各 50 亿美元 · 2026 年 6 月 4 日完成', 1310, a * k, 24)
        source(cv, 'Alphabet 2026-06-01 公告；8-K / 424B5；阿贝尔 CNBC 专访 2026-09-02', a, y=1462)
    t0, t1 = win('c4g2')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('每股价格对比', W / 2, 420, 40, 'sans_med', col=CREAM, a=a)
        for j, (cls, pub, brk, d) in enumerate([('A 类', 355.20, 351.81, '−1.0%'), ('C 类', 351.80, 348.20, '−1.0%')]):
            y = 600 + j * 230; k = eo((t - t0 - 0.2 - j * 0.3) / 0.5)
            cv.text(cls, 150, y, 40, 'sans_bold', col=GOLD, a=a * k, anchor='l')
            cv.text(f'公开发行 ${pub:.2f}', 300, y - 40, 30, 'sans_light', col=GREY, a=a * k, anchor='l')
            cv.text(f'伯克希尔 ${brk:.2f}', 300, y + 30, 38, 'sans_bold', col=GOLD_L, a=a * k, anchor='l')
            cv.text(d, 930, y, 46, 'sans_bold', col=GREEN, a=a * k, anchor='r')
        note(cv, '公开发行 6 月 2 日定价 · 阿贝尔建议的 6.5% 以什么价格为基准，未公开', 1100, a, 22)
        source(cv, 'Alphabet 2026 年三季度 10-Q（公开发行 A $355.1982、C $351.8018）；本片计算', a, y=1462)
    t0, t1 = win('c4h')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        base = 1180; sc = 640 / 10598
        segs = [('2026-03-31 持股', 5784, GOLD * 0.55, t0 + 0.2), ('定增', 2857, GOLD, t0 + 0.6), ('市场净买入', 1957, CREAM * 0.8, WT('c4h', '净买进'))]
        y = base
        cv.text('伯克希尔的谷歌持股 · 2026 年二季度', W / 2, 400, 34, 'sans_med', col=CREAM, a=a)
        for lb, v, col, ts in segs:
            e = eexp((t - ts) / 0.9)
            if e <= 0: continue
            h = v * sc * e
            gbar(cv, 380, y - h, 620, y, col, a, sheen_t=t - ts, reflect=(lb == '2026-03-31 持股'), glow=0.2 if lb == '定增' else 0.06)
            cv.text(f'{lb} {v:,} 万股', 660, y - h / 2, 30, 'sans_med', col=CREAM, a=a * min(e * 2, 1), anchor='l')
            y -= h
        tm = WT('c4h', '1.06')
        if t > tm:
            cv.text('≈ 1.06 亿股', 500, y - 60, 52, 'sans_bold', gold=True, a=a * eo((t - tm) / 0.4), glow=0.2)
        cv.text('2026-06-30', 500, base + 70, 22, 'sans_light', col=GREY, a=a)
        source(cv, '13F 2026-03-31、06-30（二季度增 4,814 万股 − 定增 2,857 万股 = 1,957 万股，净买入）', a, y=1462)
    t0, t1 = S('c4i') - 0.3, CH['tk_ch4'][0]
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        big_q(cv, t, '为什么偏偏在这时候出手？', 640, S('c4i'), 60, a)
        p = (t - WT('c4i', '尺子')) / 1.2
        if p > 0: ruler(cv, 140, 940, 900, a, p)
        if p > 0.5: cv.text('巴菲特和芒格的尺子', W / 2, 990, 34, 'sans_med', col=GOLD_L, a=a * eo(p - 0.5))


# ======================================================================== 第五章：护城河还在吗
# 护城河机器（m5–m9c、m12）：五股力量不是清单，而是一台循环的机器——
#   入口（安卓 / Chrome / YouTube / 地图 …）把人送进搜索框（习惯）→ 每次搜索带着需求进入广告竞价 → 广告收入再投入算力
#   → 更强的模型与数据技术 → 更好的搜索结果 → 留住更多人。镜头随旁白在机器的各部分之间推移；最后标出哪些部分“守住花钱不多”，
#   哪部分“要年年重金投入”。全部为示意（画面标注），数字均为片中旁白引用的公开数据。
SKY = C(120, 200, 255)
ICE = C(170, 220, 255)


class Cam:
    """二维摄影机：世界坐标 → 屏幕坐标（缩放 z，注视点 cx, cy 落在屏幕 (W/2, sy)）"""
    def __init__(self, cx, cy, z, sy=830):
        self.cx, self.cy, self.z, self.sy = cx, cy, z, sy
    def p(self, x, y): return (W / 2 + (x - self.cx) * self.z, self.sy + (y - self.cy) * self.z)
    def s(self, v): return v * self.z


def cam_path(t, keys):
    """keys = [(时刻, cx, cy, z)]：关键帧之间缓入缓出"""
    if t <= keys[0][0]: return keys[0][1:]
    for (ta, *A), (tb, *B) in zip(keys, keys[1:]):
        if t <= tb:
            k = eio5((t - ta) / max(tb - ta, 1e-3))
            return tuple(lerp(x, y, k) for x, y in zip(A, B))
    return keys[-1][1:]


def bez(p0, p1, p2, u):
    return ((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0], (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1])


def flow(cv, cam, t, p0, p1, p2, col, a, n=7, speed=0.45, size=6, label=None, lab_u=0.5, lab_off=(0, -30), grow=1.0, seed=0):
    """沿二次贝塞尔曲线流动的光点（带细轨迹线与箭头）；grow 0→1 控制轨迹生长"""
    if a <= 0.004 or grow <= 0: return
    us = np.linspace(0, grow, 28)
    cv.poly([cam.p(*bez(p0, p1, p2, u)) for u in us], col, a * 0.35, max(1, int(cam.s(2))))
    if grow >= 0.98:
        e = cam.p(*bez(p0, p1, p2, 1.0)); d = cam.p(*bez(p0, p1, p2, 0.93))
        ang = math.atan2(e[1] - d[1], e[0] - d[0]); L = cam.s(16)
        cv.fillpoly([e, (e[0] - L * math.cos(ang - 0.45), e[1] - L * math.sin(ang - 0.45)),
                     (e[0] - L * math.cos(ang + 0.45), e[1] - L * math.sin(ang + 0.45))], col, a * 0.8)
        for i in range(n):
            u = (t * speed + i / n + seed * 0.13) % 1.0
            x, y = cam.p(*bez(p0, p1, p2, u))
            cv.glow_dot((x, y), cam.s(size) * (0.7 + 0.3 * math.sin(u * math.pi)), col, a * math.sin(u * math.pi) ** 0.5)
    if label:
        x, y = cam.p(*bez(p0, p1, p2, lab_u))
        cv.text(label, x + cam.s(lab_off[0]), y + cam.s(lab_off[1]), int(cam.s(22)), 'sans_med', col=col, a=a * eo(grow), shadow=0.8)


def glass(cv, cam, x0, y0, x1, y1, col, a, r=18, glow=0.15):
    """玻璃质感面板：深色半透明底 + 细边 + 顶部高光"""
    if a <= 0.004: return
    X0, Y0 = cam.p(x0, y0); X1, Y1 = cam.p(x1, y1); R = cam.s(r)
    cv.rrect(X0, Y0, X1, Y1, R, C(14, 20, 32), a * 0.82)
    cv.rrect(X0, Y0, X1, Y1, R, col, a * 0.75, fill=False, th=2, glow=glow)
    cv.line((X0 + R, Y0 + 2), (X1 - R, Y0 + 2), WHITE, a * 0.25, 1)


QUERIES = ['车险报价', '附近的餐厅', '明天会下雨吗', '降噪耳机推荐', '去东京的机票']


def moat_machine(cv, t, cam, a, on, ai=0.0, durable=0.0):
    """on：各部分出现进度 dict(search, ads, entry, tech, compute)，0..1"""
    if a <= 0.004: return
    P, Sz = cam.p, cam.s
    # —— 入口：产品行
    k = on.get('entry', 0)
    if k > 0:
        names = ['安卓', 'Chrome', 'YouTube', '地图', 'Gmail']
        for j, nm in enumerate(names):
            kk = eo((k * 1.6 - j * 0.15))
            if kk <= 0: continue
            x = 150 + j * 195
            glass(cv, cam, x - 82, 400, x + 82, 462, SKY, a * kk, r=30, glow=0.1)
            cv.text(nm, *P(x, 431), int(Sz(24)), 'sans_med', col=ICE, a=a * kk)
            flow(cv, cam, t, (x, 466), (x, 560), (540 + (x - 540) * 0.35, 646), SKY, a * kk * (1 - 0.5 * ai), n=4, speed=0.5, size=5, seed=j,
                 grow=eo(k * 1.4 - 0.3 - j * 0.1))
        cv.text('入口', *P(540, 360), int(Sz(28)), 'sans_bold', col=SKY, a=a * eo(k * 2), shadow=0.8)
    # —— 搜索框（习惯）
    k = on.get('search', 0)
    if k > 0:
        x0, x1, cy = 290, 790, 700
        X0, Y0 = P(x0, cy - 48); X1, Y1 = P(x1, cy + 48)
        cv.rrect(X0, Y0, X1, Y1, Sz(48), C(20, 24, 34), a * k * 0.95)
        cv.rrect(X0, Y0, X1, Y1, Sz(48), GOLD_L if durable > 0 else ICE, a * k * 0.85, fill=False, th=3, glow=0.25 + 0.3 * durable)
        mx, my = P(x0 + 52, cy - 4)
        cv.circle((mx, my), Sz(15), ICE, a * k, max(2, int(Sz(3)))); cv.line(P(x0 + 63, cy + 8), P(x0 + 74, cy + 19), ICE, a * k, max(2, int(Sz(3))))
        ph = (t * 0.32) % 1; qi = int(t * 0.32) % len(QUERIES); q = QUERIES[qi]
        n = int(cl(ph / 0.45) * len(q))
        cv.text(q[:n], *P(x0 + 100, cy), int(Sz(36)), 'sans_med', col=WHITE, a=a * k * (1 - eo((ph - 0.85) / 0.15)), anchor='l')
        if ph > 0.55 and ph < 0.62: cv.glow_dot(P(x1 - 60, cy), Sz(30), ICE, a * k * 0.6)
        cv.text('习惯', *P(540, 790), int(Sz(28)), 'sans_bold', col=GOLD_L if durable > 0 else ICE, a=a * k, shadow=0.8)
    # —— 广告竞价
    k = on.get('ads', 0)
    if k > 0:
        bx, by = 850, 1000
        glass(cv, cam, bx - 150, by - 110, bx + 150, by + 110, GOLD_L if durable > 0 else GOLD, a * k, glow=0.12 + 0.3 * durable)
        cv.text('广告竞价', *P(bx, by - 78), int(Sz(26)), 'sans_bold', col=GOLD_L, a=a * k)
        rnd = int(t / 1.6); ph = (t / 1.6) % 1
        rng = np.random.default_rng(rnd)
        bids = rng.uniform(0.35, 1.0, 3); win_ = int(np.argmax(bids))
        for j in range(3):
            hh = 110 * bids[j] * eo(min(ph / 0.5, 1)) * k
            xx = bx - 80 + j * 80
            col = GOLD_L if (j == win_ and ph > 0.55) else C(110, 100, 80)
            X0, Y0 = P(xx - 22, by + 80 - hh); X1, Y1 = P(xx + 22, by + 80)
            cv.rect(X0, Y0, X1, Y1, col, a * k, glow=0.3 if (j == win_ and ph > 0.55) else 0)
        flow(cv, cam, t, (790, 730), (880, 760), (860, 886), GOLD_L, a * k, n=6, speed=0.55, label='需求', lab_off=(48, 0), grow=eo(k * 1.5 - 0.2))
    # —— 数据与技术
    k = on.get('tech', 0)
    if k > 0:
        bx, by = 230, 1000
        glass(cv, cam, bx - 150, by - 110, bx + 150, by + 110, SKY, a * k, glow=0.12)
        cv.text('数据与技术', *P(bx, by - 78), int(Sz(26)), 'sans_bold', col=ICE, a=a * k)
        order = [0, 1, 2] if (t // 2.2) % 2 == 0 else [1, 0, 2]
        sw = eio(((t % 2.2) - 1.6) / 0.5) if (t % 2.2) > 1.6 else 0
        for r in range(3):
            yy = by - 30 + r * 42
            j = order[r]
            X0, Y0 = P(bx - 110, yy - 10); X1, Y1 = P(bx - 110 + [190, 160, 120][j], yy + 10)
            cv.rrect(X0, Y0, X1, Y1, Sz(8), [ICE, SKY * 0.8, GREY * 0.7][j], a * k * 0.85)
            cv.text(f'{r + 1}', *P(bx + 120, yy), int(Sz(20)), 'oswald', col=GREY, a=a * k)
        flow(cv, cam, t, (230, 888), (226, 760), (296, 716), ICE, a * k, n=6, speed=0.5, label='更好的结果', lab_off=(-82, 6),
             lab_u=0.45, grow=eo(k * 1.5 - 0.2))
    # —— 算力底座
    k = on.get('compute', 0)
    if k > 0:
        x0, x1, y0, y1 = 250, 830, 1180, 1320
        hot = 1.0 - durable * 0.0
        glass(cv, cam, x0, y0, x1, y1, RED if durable > 0 else SKY, a * k, glow=0.15 + 0.35 * durable * (0.6 + 0.4 * math.sin(t * 5)))
        cv.text('算力 · 芯片 / 模型 / 云 / 数据中心', *P(540, y0 + 32), int(Sz(24)), 'sans_bold', col=ICE, a=a * k)
        for i in range(12):
            for j in range(2):
                cx_ = x0 + 40 + i * 46; cy_ = y0 + 74 + j * 40
                X0, Y0 = P(cx_ - 16, cy_ - 14); X1, Y1 = P(cx_ + 16, cy_ + 14)
                lit = 0.5 + 0.5 * math.sin(t * 3.1 + i * 0.9 + j * 2.1)
                cv.rect(X0, Y0, X1, Y1, C(40, 70, 110) * (0.6 + 0.6 * lit), a * k * eo(k * 3 - i * 0.12))
                cv.glow_dot(P(cx_, cy_), Sz(3), ICE, a * k * lit * 0.8)
        flow(cv, cam, t, (850, 1112), (850, 1200), (790, 1224), GOLD, a * k, n=6, speed=0.5, label='收入再投入', lab_off=(40, -44),
             grow=eo(k * 1.5 - 0.1))
        flow(cv, cam, t, (290, 1224), (226, 1200), (230, 1112), SKY, a * k, n=6, speed=0.5, label='更强的模型', lab_off=(-40, -44),
             grow=eo(k * 1.5 - 0.4))
    # —— AI：双刃剑（入口与搜索框之间多出一个节点）
    if ai > 0:
        nx, ny = 960, 592
        cv.circle(P(nx, ny), Sz(54), RED, a * ai * 0.85, max(2, int(Sz(3))))
        cv.glow_dot(P(nx, ny), Sz(22), RED, a * ai * (0.45 + 0.2 * math.sin(t * 4)))
        cv.text('直接问 AI', *P(nx, ny), int(Sz(22)), 'sans_bold', col=WHITE, a=a * ai)
        flow(cv, cam, t, (930, 466), (948, 500), (952, 536), RED, a * ai, n=3, speed=0.7, size=5, grow=eo(ai * 1.5))
        flow(cv, cam, t, (906, 610), (850, 660), (794, 684), ICE, a * ai, n=3, speed=0.7, size=5, grow=eo(ai * 1.5 - 0.3))
        cv.text('− 可能绕开搜索框', *P(nx, ny + 84), int(Sz(21)), 'sans_med', col=RED, a=a * eo(ai * 1.5 - 0.2), shadow=0.8)
        cv.text('+ 也能让搜索更好用', *P(nx, ny + 114), int(Sz(21)), 'sans_med', col=ICE, a=a * eo(ai * 1.5 - 0.5), shadow=0.8)


def clip_snap(cv):
    return cv.img.copy(), cv.glow.copy(), cv.U.copy()


def clip_band(cv, snap, top=(225, 300), bot=(1300, 1350)):
    """只对快照之后画上的内容（机器）做上下柔和裁切：nav 之下、信息条之上，背景不受影响"""
    y = np.arange(H, dtype=np.float32)
    f = np.minimum(np.clip((y - top[0]) / (top[1] - top[0]), 0, 1), np.clip((bot[1] - y) / (bot[1] - bot[0]), 0, 1))
    f = f ** 1.5
    i0, g0, u0 = snap
    cv.img = i0 + (cv.img - i0) * f[:, None, None]
    cv.glow = g0 + (cv.glow - g0) * f[:, None, None]
    fu = f.reshape((H,) + (1,) * (cv.U.ndim - 1))
    cv.U = np.clip(u0 + (cv.U.astype(np.float32) - u0) * fu, 0, 255).astype(np.uint8)


def moat_cam(t):
    keys = [(S('m5') - 0.4, 540, 700, 1.36), (S('m6') - 0.2, 540, 710, 1.3),
            (WT('m7', '广告主') - 0.6, 540, 720, 1.26), (WT('m7', '广告主') + 0.7, 650, 850, 1.15),
            (S('m8') - 0.2, 650, 850, 1.15), (S('m8') + 1.0, 540, 580, 1.15),
            (S('m9') - 0.2, 540, 590, 1.15), (S('m9') + 1.0, 330, 900, 1.25),
            (S('m9b') - 0.2, 330, 900, 1.25), (S('m9b') + 1.0, 540, 940, 1.04),
            (S('m9c') - 0.3, 540, 930, 1.04), (S('m9c') + 1.0, 560, 850, 0.98), (E('m9c') + 2, 560, 850, 0.96)]
    return Cam(*cam_path(t, keys))


def shot_ch5(cv, t):
    t0, t1 = win('m1')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        doc_page(cv, t, t0, t1, 'BERKSHIRE HATHAWAY · CHAIRMAN’S LETTER · 2007',
                 ['Businesses – The Great, the Good', 'and the Gruesome'], cy=470, w=900, size=36, font='playfair', a=a)
        castle(cv, t, W / 2, 850, 0.75, a * eo((t - t0 - 0.8) / 0.8))
        k = eo((t - WT('m1', '一次又一次')) / 0.5)
        if k > 0: siege(cv, t, W / 2, 850, 0.75, a * k * 0.7, WT('m1', '一次又一次'))
        qcard(cv, 'qmoat07', t, WT('m1', '真正伟大') - 0.4, t1, cy=1220, en=28, cn=34)
    t0, t1 = win('m2')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        qcard(cv, 'qask', t, t0 + 0.1, t1, cy=820, en=36, cn=40, typing=1.8)
        k = eo((t - WT('m2', '谷歌') + 0.1) / 0.5)
        if k > 0: cv.text('Google', W / 2, 1180, 90, 'playfair', col=GOLD_L, a=a * k, glow=0.35)
        source(cv, '伯克希尔 2007 年致股东信', a, y=1462)
    # 护城河机器：m5–m9c 一个连续镜头（m6 时机器退到背景，前景是判决书）
    t0, t1 = S('m5') - 0.4, E('m9c') + 0.6
    a = env(t, t0, t1, 0.5, 0.5)
    if a > 0:
        cam = moat_cam(t)
        on = dict(search=eo((t - S('m5') + 0.2) / 0.8), ads=eo((t - WT('m7', '广告主')) / 1.0),
                  entry=eo((t - WT('m8', '13 款')) / 1.4), tech=eo((t - S('m9')) / 1.0), compute=eo((t - S('m9b')) / 1.0))
        dm = env(t, S('m6') - 0.2, S('m7') - 0.2, 0.5, 0.6)          # m6：机器压暗退后
        ai = eo((t - WT('m9c', '可如果')) / 1.0)
        snap = clip_snap(cv)
        moat_machine(cv, t, cam, a * (1 - dm), on, ai=ai)
        clip_band(cv, snap)
        cv.text('示意', 1020, 1400, 20, 'sans_light', col=GREY, a=a * 0.7, anchor='r')
        # 各段的数字：屏幕坐标，固定在画面下部的信息条里（不随镜头移动，避免与机器重叠）
        def info(ts, te):
            return env(t, ts, te, 0.35, 0.3) * a
        p1 = info(WT('m5', '份额') - 0.3, S('m6') - 0.1)
        if p1 > 0:
            big_num(cv, t, WT('m5', '份额'), '≈ 91%', 1250, size=110, a=p1)
            cv.text('全球搜索份额 · 2026 年 10 月 · 长期在九成上下', W / 2, 1345, 26, 'sans_light', col=CREAM, a=p1, shadow=0.8)
            source(cv, 'StatCounter Global Stats（全平台、全球）', p1, y=1462)
        p2 = info(S('m6'), S('m7') - 0.2)
        if p2 > 0:
            doc_page(cv, t, S('m6'), S('m7') - 0.2, 'U.S. v. GOOGLE LLC · D.D.C. · AUG 5, 2024',
                     ['Google is a monopolist, and it has acted', 'as one to maintain its monopoly.'], cy=520, w=960, size=32,
                     hl='Google is a monopolist', hl_t=WT('m6', '垄断者'), a=p2)
            # 示意：手机里的默认搜索位置，谷歌付钱给苹果
            kd = eo((t - WT('m6', '默认搜索') + 0.3) / 0.6) * p2
            if kd > 0:
                px, py, pw, ph_ = 300, 900, 230, 400
                cv.rrect(px - pw / 2, py - ph_ / 2, px + pw / 2, py + ph_ / 2, 34, C(18, 22, 30), kd)
                cv.rrect(px - pw / 2, py - ph_ / 2, px + pw / 2, py + ph_ / 2, 34, GREY, kd * 0.8, fill=False, th=3)
                cv.rrect(px - 34, py - ph_ / 2 + 16, px + 34, py - ph_ / 2 + 26, 5, GREY * 0.6, kd)
                cv.rrect(px - 90, py - 120, px + 90, py - 76, 22, C(36, 42, 56), kd)
                cv.rrect(px - 90, py - 120, px + 90, py - 76, 22, GOLD_L, kd * 0.9, fill=False, th=2, glow=0.25)
                cv.text('默认搜索', px, py - 98, 22, 'sans_med', col=GOLD_L, a=kd)
                for r in range(3):
                    for c_ in range(3):
                        cv.rrect(px - 78 + c_ * 58, py - 30 + r * 64, px - 38 + c_ * 58, py + 10 + r * 64, 10, C(40, 50, 70), kd * 0.9)
                cv.text('手机 / 浏览器', px, py + ph_ / 2 + 36, 22, 'sans_light', col=GREY, a=kd)
                # 钱流：谷歌 → 苹果（右侧）
                k2 = eo((t - WT('m6', '200') + 0.3) / 0.6) * p2
                if k2 > 0:
                    cv.rrect(640, 820, 940, 980, 18, C(30, 26, 22), k2)
                    cv.rrect(640, 820, 940, 980, 18, RED, k2 * 0.8, fill=False, th=2, glow=0.2)
                    cv.text('2022 年付给苹果', 790, 860, 26, 'sans_med', col=CREAM, a=k2)
                    cv.text('约 $200 亿', 790, 925, 50, 'sans_bold', col=RED, a=k2, glow=0.15)
                    for i in range(6):
                        u = (t * 0.6 + i / 6) % 1
                        cv.glow_dot((lerp(px + 90, 630, u), py - 98 + math.sin(u * math.pi) * -30), 6, GOLD_L, k2 * math.sin(u * math.pi))
            tag(cv, '2025：法院禁止这类独家协议（谷歌已上诉）', t, WT('m6', '2025'), W / 2, 1210, 28, GOLD, p2)
            source(cv, 'Mehta 法官 2024-08-05 判决、2025-09-02 补救判决；苹果高管 Eddy Cue 庭审证词', p2, y=1462)
        p3 = info(WT('m7', 'GEICO') - 0.3, S('m8') - 0.1)
        if p3 > 0:
            tag(cv, '$10–11 / 一次点击 · GEICO（巴菲特 2017 年回忆）', t, WT('m7', 'GEICO'), W / 2, 1390, 26, GOLD_L, p3)
            source(cv, 'Alphabet 10-K（按点击计费）；Google Ads 帮助文档（广告竞价）；末句为本片解读', p3, y=1462)
        p4 = info(WT('m8', '13 款') - 0.2, S('m9') - 0.1)
        if p4 > 0:
            tag(cv, '13 款产品 · 各超 10 亿用户', t, WT('m8', '13 款'), W / 2, 1390, 28, SKY, p4)
            source(cv, 'Google I/O 2026 主题演讲（皮查伊）', p4, y=1462)
        p5 = info(WT('m9', '2025') - 0.3, S('m9b') - 0.1)
        if p5 > 0:
            tag(cv, '2025 补救判决：共享部分搜索索引与用户交互数据', t, WT('m9', '2025'), W / 2, 1390, 26, ICE, p5)
            source(cv, 'U.S. v. Google 2025-09-02 补救判决（remedies opinion）', p5, y=1462)
        p6 = info(WT('m9b', 'Gemini') - 0.3, S('m9c') - 0.1)
        if p6 > 0:
            tag(cv, 'Gemini 应用 · 10 亿用户', t, WT('m9b', 'Gemini'), 300, 1390, 26, SKY, p6)
            tag(cv, '云未履约合同 · $5,608 亿', t, WT('m9b', '5608'), 780, 1390, 26, GOLD_L, p6)
            source(cv, 'Alphabet 2026 年三季度 CEO 致辞；10-Q（Google Cloud remaining performance obligations）', p6, y=1462)
        p7 = info(S('m9c'), E('m9c') + 0.6)
        if p7 > 0:
            tag(cv, '三季度搜索查询量增速：五年来最高', t, WT('m9c', '三季度'), W / 2, 1390, 26, ICE, p7)
            source(cv, 'Alphabet 2026 年三季度 CEO 致辞；“改写”为本片解读', p7, y=1462)
    t0, t1 = win('m10')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        castle(cv, t, W / 2, 800, 0.85, a, lit=[0, 1, 2, 3, 4], lit_t=[t0 - 2] * 5)
        siege(cv, t, W / 2, 800, 0.85, a, t0 + 0.6)
        tag(cv, '2018：会不会有人超过谷歌？', t, t0 + 0.2, W / 2, 1290, 30, CREAM, a)
        tag(cv, '2026：专访的最后', t, WT('m10', '八年后'), W / 2, 1380, 30, GOLD, a)
    t0, t1 = win('m11')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['c_winner', 'c_quarter'], h=470)
        qcard(cv, 'qwinner', t, t0 + 0.4, t1, cy=1150, en=30, cn=36)
    # m12：原话卡 → 机器全景，标出“守住花钱不多”和“要年年重金投入”的部分
    t0, t1 = S('m12') - 0.3, CH['tk_ch5'][0]
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        tm = WT('m12', '习惯')
        qcard(cv, 'qrebuilt', t, t0, tm + 0.1, cy=820, en=36, cn=40)
        k = eo((t - tm + 0.2) / 0.8)
        if k > 0:
            cam = Cam(560, 840, 0.9, sy=790)
            dur = eo((t - tm) / 0.8)
            snap = clip_snap(cv)
            moat_machine(cv, t, cam, a * k, dict(search=1, ads=1, entry=1, tech=1, compute=1), durable=dur)
            clip_band(cv, snap, top=(225, 290), bot=(1290, 1325))
            kg = eo((t - tm - 0.3) / 0.5)
            cv.text('守住它们，花钱不多', W / 2, 270 + 0 * kg, 30, 'sans_bold', col=GOLD_L, a=a * k * kg, shadow=0.8)
            kr = eo((t - WT('m12', '算力') + 0.1) / 0.5)
            if kr > 0:
                X, Y = cam.p(540, 1345)
                cv.text('年年重金投入', X, Y + 20, 30, 'sans_bold', col=RED, a=a * kr, glow=0.15, shadow=0.8)
        kq = eo((t - WT('m12', '巴菲特更在意') + 0.1) / 0.5)
        if kq > 0:
            cv.rrect(90, 1330, 990, 1420, 16, C(20, 18, 16), a * kq * 0.92)
            cv.text('守住这条河要花多少钱？还能不能一直赚到高回报？', W / 2, 1375, 32, 'serif_semi', col=GOLD_L, a=a * kq)
        source(cv, '伯克希尔 2007 年致股东信；“哪些部分花钱多”为本片解读', a, y=1462)


# ======================================================================== 第六章：比不上四五家公司
def shot_ch6(cv, t):
    t0, t1 = win('c5a')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['c_two_b'], h=470)
        big_q(cv, t, '谷歌在伯克希尔，分量有多重？', 1150, WT('c5a', '分量'), 50, a)
    t0, t1 = win('c5a2')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['c_two_b', 'c_bnsf'], h=470)
        k3 = eo((t - WT('c5a2', '排第三') + 0.2) / 0.5)
        if k3 > 0:
            cv.text('主持人：No.3', 300, 960, 36, 'sans_med', col=GREY, a=a * k3)
            cv.text('巴菲特：No.5–6', 780, 960, 36, 'sans_bold', col=GOLD_L, a=a * eo((t - WT('c5a2', '全部生意') + 0.2) / 0.5))
            cv.line((W / 2, 925), (W / 2, 995), GOLD_D, a * k3, 2)
        k = eo((t - WT('c5a2', '全部生意') + 0.3) / 0.5)
        if k > 0:
            cv.text('“所有生意”一起排', W / 2, 1110, 52, 'serif_black', gold=True, a=a * k, glow=0.2)
            for j, nm in enumerate(['BNSF 铁路', '能源公司', 'GEICO …', '股票持仓']):
                tag(cv, nm, t, WT('c5a2', '包括') + j * 0.3, 190 + j * 235, 1240, 28, GOLD if j < 3 else GREY, a * k)
            note(cv, '巴菲特在专访中自己举了伯灵顿北方铁路（BNSF）的例子', 1340, a * k, 22)
    t0, t1 = win('c5b')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        tm = WT('c5b', '美国运通')
        big_q(cv, t, '巴菲特的尺子：资本回报', 470, t0 + 0.2, 52, a)
        cv.text('资本回报率（巴菲特在专访中的说法）', W / 2, 620, 30, 'sans_med', col=CREAM, a=a * eo((t - tm) / 0.5))
        hbar(cv, t, [('美国运通', 30, tm + 0.2, GOLD), ('多数银行', 13.5, WT('c5b', '普通银行'), GOLD * 0.5)], a,
             x0=330, x1=820, y0=780, dy=150, vmax=34, fmt=lambda v: '30%+' if v >= 30 else '13–14%', size=48, lab=36, hl=0)
        tag(cv, '风险却不比银行大', t, WT('c5b', '冒的风险'), W / 2, 1110, 32, GOLD, a)
        source(cv, 'CNBC 专访 2026-07-15（视频 3:43–4:08）', a, y=1462)
    t0, t1 = win('c5b2')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        photo_win(cv, 'treasury', t, t0, t1, cap='美国财政部大楼', focus=(0.5, 0.5))
        qcard(cv, 'qriskless', t, t0 + 0.2, t1, cy=1150, en=32, cn=40)
    t0, t1 = win('c5c')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        tag(cv, '2007：“Ask Microsoft or Google.”', t, t0 + 0.1, W / 2, 460, 30, GOLD, a)
        kj = 1 - eo((t - WT('c5c', '如今') + 0.3) / 0.4)
        if kj > 0:
            big_q(cv, t, '不需要大笔资本的榜样', 820, t0 + 0.3, 64, a * kj)
            ruler(cv, 240, 840, 950, a * kj, (t - t0 - 0.5) / 1.0)
            note(cv, '多卖一次广告，几乎不用多花钱', 1030, a * kj * eo((t - t0 - 0.8) / 0.5), 30, col=CREAM)
        g = eo((t - WT('c5c', '砸下去')) / 1.5)
        servers(cv, t, 900, a * eo((t - WT('c5c', '如今')) / 0.6), rows=3, growth=0.4 + 0.6 * g)
        note(cv, '示意：数据中心', 1250, a, 22)
    t0, t1 = win('c5d')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('谷歌资本开支（数据中心、芯片、机房）', W / 2, 380, 34, 'sans_med', col=CREAM, a=a)
        items = [('2024', 525, t0 + 0.2, GOLD * 0.5, ''), ('2025', 914, WT('c5d', '914'), GOLD * 0.75, ''),
                 ('2026 指引', 2000, WT('c5d', '2000'), GOLD, '$1,950–2,050 亿')]
        vbars(cv, t, items, a, x0=120, x1=780, base=1250, hmax=680, fmt=lambda v: f'${v:,.0f}亿', size=40, lab=26)
        k = eo((t - WT('c5d', '2027') + 0.1) / 0.5)
        if k > 0:
            cv.line((880, 1240), (880, 1240 - 640 * k), DIM, a, 6)
            cv.fillpoly([(850, 1240 - 640 * k), (910, 1240 - 640 * k), (880, 1240 - 640 * k - 50)], DIM, a)
            cv.text('2027', 880, 1290, 26, 'sans_light', col=GREY, a=a * k)
            cv.text('“大幅增加”', 880, 1240 - 640 * k - 90, 26, 'sans_med', col=CREAM, a=a * k)
        source(cv, 'Alphabet 2025 年报；2026 年指引 7 月上调至 $1,950–2,050 亿，10-28 三季度电话会维持并称 2027 年 “increase significantly”', a, y=1462)
    t0, t1 = win('c5e')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['c_two_d'], h=470)
        big_q(cv, t, '“不碰科技股”的巴菲特', 1080, t0 + 0.3, 54, a)
        big_q(cv, t, '这一次，是怎么回事？', 1220, WT('c5e', '这一次'), 54, a, col=CREAM)
    t0, t1 = win('c5e2')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['c_railroad', 'c_game'], h=470)
        qcard(cv, 'qsoftware', t, t0 + 0.2, t1, cy=1150, en=38, cn=42)
    t0, t1 = win('c5f')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('谷歌云 · 2026 年三季度 vs 一年前', W / 2, 380, 34, 'sans_med', col=CREAM, a=a)
        items = [('收入 25Q3', 151.6, t0 + 0.3, GOLD * 0.5, ''), ('收入 26Q3', 307.1, WT('c5f', '307'), GOLD, '×2'),
                 ('经营利润 25Q3', 35.9, WT('c5f', '36'), BLUE_L * 0.6, ''), ('经营利润 26Q3', 111.2, WT('c5f', '111'), BLUE_L, '')]
        vbars(cv, t, items, a, x0=130, x1=950, base=1250, hmax=700, fmt=lambda v: f'${v:,.0f}亿', size=38, lab=22)
        source(cv, 'Alphabet 2026 年三季度财报（云收入 $15,157M → $30,709M；云经营利润 $3,594M → $11,121M）', a, y=1462)
    t0, t1 = win('c5g')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('自由现金流（季度）', W / 2, 380, 34, 'sans_med', col=CREAM, a=a)
        items = [('25Q4', 245.5, t0 + 0.2, GOLD * 0.7, ''), ('26Q1', 101.2, t0 + 0.5, GOLD * 0.7, ''),
                 ('26Q2', -58.6, WT('c5g', '连续两个季度'), RED, ''), ('26Q3', -90.7, WT('c5g', '连续两个季度') + 0.4, RED, '')]
        vbars(cv, t, items, a, x0=150, x1=930, base=860, hmax=380, fmt=lambda v: f'${v:,.0f}亿', size=36, lab=24)
        k = eo((t - WT('c5g', '没有回购') + 0.1) / 0.5)
        if k > 0:
            cv.text('回购：2025 年 $457 亿 → 2026 年前九个月 0', W / 2, 1330, 34, 'sans_bold', col=GOLD_L, a=a * k)
        source(cv, 'Alphabet 2026 年三季度财报与 10-Q（“there were no repurchases”）', a, y=1462)
    t0, t1 = win('c5h')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        # 天平：左盘是看得见的投入（不断加码），右盘是还看不见的回报；横梁先被投入压低，再随“将来能赚回多少”摆动
        p = t - t0
        load = eo(p / 2.0)
        ang = 0.16 * load - 0.05 * math.sin(p * 1.4) * cl((t - WT('c5h', '将来')) / 1.0) * math.exp(-0.15 * max(t - WT('c5h', '将来'), 0))
        cx, cy = W / 2, 640
        cv.fillpoly([(cx - 80, 1140), (cx + 80, 1140), (cx + 16, cy + 10), (cx - 16, cy + 10)], C(60, 50, 36), a)
        cv.poly([(cx - 80, 1140), (cx - 16, cy + 10), (cx + 16, cy + 10), (cx + 80, 1140)], GOLD_D, a, 2)
        cv.rect(cx - 160, 1140, cx + 160, 1156, GOLD_D, a)
        L = 360; dx, dy = L * math.cos(ang), L * math.sin(ang)
        beam = [(cx - dx - 6 * math.sin(ang), cy - dy + 6 * math.cos(ang)), (cx + dx - 6 * math.sin(ang), cy + dy + 6 * math.cos(ang)),
                (cx + dx + 6 * math.sin(ang), cy + dy - 6 * math.cos(ang)), (cx - dx + 6 * math.sin(ang), cy - dy - 6 * math.cos(ang))]
        cv.fillpoly(beam, GOLD, a, glow=0.2)
        cv.glow_dot((cx, cy), 14, GOLD_L, a)
        for sgn, title, sub, col, n_coin in ((-1, '几千亿美元投入', '$914 亿（2025）→ 约 $2,000 亿（2026）', RED, 2 + int(7 * load)),
                                             (1, '将来的回报', '能赚回多少？要投多久？', GREEN, 0)):
            px, py = cx + sgn * dx, cy + sgn * dy
            for q in (-1, 1): cv.line((px, py), (px + q * 95, py + 190), GREY, a * 0.8, 2)
            pan = [(px - 120 + 240 * u, py + 190 + 46 * math.sin(math.pi * u)) for u in np.linspace(0, 1, 30)]
            cv.fillpoly(pan, col * 0.3, a * 0.85)
            cv.poly(pan + [pan[0]], col, a, 3)
            for c_ in range(n_coin):
                yy = py + 182 - c_ * 16
                cv.rrect(px - 60, yy - 7, px + 60, yy + 7, 7, C(170, 60, 50), a * 0.95)
                cv.line((px - 56, yy - 6), (px + 56, yy - 6), C(240, 140, 120), a * 0.6, 1)
            if n_coin == 0:
                cv.text('?', px, py + 150, 80, 'serif_black', col=GREEN, a=a * (0.5 + 0.3 * math.sin(t * 2)), glow=0.2)
            tx = min(max(px, 230), W - 230)
            cv.text(title, tx, py + 300, 36, 'sans_bold', col=col, a=a, shadow=0.7)
            cv.text(sub, tx, py + 346, 22, 'sans_light', col=CREAM, a=a * 0.9)
        note(cv, '本片解读 · 示意', 1240, a * 0.8, 22)
    t0, t1 = S('c5j') - 0.3, CH['tk_ch6'][0]
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        seq(cv, t, t0, t1, ['e_abel'], h=470, cap='阿贝尔')
        qcard(cv, 'qabelai', t, t0 + 0.4, t1, cy=1140, en=28, cn=34)


# ======================================================================== 第七章：这张票，补得值不值
def shot_ch7(cv, t):
    t0, t1 = win('c6a')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('伯克希尔的谷歌持股 · 2026-06-30', W / 2, 380, 34, 'sans_med', col=CREAM, a=a)
        base = 1150; sc = 600 / 10598
        e1 = eexp((t - WT('c6a', '在股市上')) / 1.0); e2 = eexp((t - WT('c6a', '定增')) / 1.0)
        h1 = 7741 * sc * e1; h2 = 2857 * sc * e2
        gbar(cv, 300, base - h1, 520, base, CREAM * 0.62, a, sheen_t=t - t0, reflect=True)
        if h2 > 1: gbar(cv, 300, base - h1 - h2, 520, base - h1, GOLD, a, sheen_t=t - t0, reflect=False, glow=0.25)
        if e1 > 0: cv.text('市场净买入 ≈ 7,741 万股', 560, base - h1 / 2, 30, 'sans_med', col=CREAM, a=a * min(e1 * 2, 1), anchor='l')
        if e2 > 0: cv.text('定增 2,857 万股 · $100 亿', 560, base - h1 - h2 / 2, 30, 'sans_bold', col=GOLD_L, a=a * min(e2 * 2, 1), anchor='l')
        k = eo((t - WT('c6a', '没有付给') + 0.1) / 0.5)
        if k > 0:
            cv.text('钱 → 卖出股票的人', 410, base + 50, 26, 'sans_light', col=GREY, a=a * k)
            cv.text('钱 → Alphabet', 760, base - h1 - h2 - 40, 30, 'sans_bold', col=GOLD, a=a * k)
        source(cv, '13F（季末持股，两期之差为“净增”）；Alphabet 8-K / 424B5（定增股数）', a, y=1462)
    t0, t1 = win('c6a2')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('谷歌 2026 年 6 月股权融资计划 · 共 $847.5 亿', W / 2, 350, 32, 'sans_med', col=CREAM, a=a)
        blocks = [('公开发行', '普通股 + 强制可转换优先股', 347.5, GOLD * 0.55, t0 + 0.2),
                  ('伯克希尔定增', '$100 亿', 100, GOLD, t0 + 0.6), ('ATM 分批发行（计划）', '主要用于员工股权奖励缴税，不是 AI 融资', 400, DIM, t0 + 1.0)]
        x = 90
        for nm, sub, v, col, ts in blocks:
            e = eexp((t - ts) / 0.9); w = 900 * v / 847.5 * e
            if w > 1: gbar(cv, x, 450, x + w, 560, col, a, horizontal=True, glow=0.2 if col is GOLD else 0.03, sheen_t=t - ts)
            if e > 0.5:
                if v < 200:          # 窄块：名称写在块上方
                    cv.text(nm, x + w / 2, 425, 26, 'sans_bold', col=GOLD_L, a=a)
                    cv.text(sub, x + w / 2, 505, 26, 'sans_bold', col=INK, a=a)
                else:
                    cv.text(nm, x + w / 2, 505, 26, 'sans_bold', col=CREAM, a=a)
                    for q, ln in enumerate(split_balanced(sub, 'sans_light', 20, w - 20)):
                        cv.text(ln, x + w / 2, 600 + q * 28, 20, 'sans_light', col=GREY, a=a)
            x += w + 6
        k = eo((t - WT('c6a2', '扩建') + 0.2) / 0.4)
        if k > 0: cv.rrect(90, 440, 90 + 900 * 447.5 / 847.5 + 6, 570, 6, BLUE_L, a * k, fill=False, th=3)
        tag(cv, '用于 AI 基础设施与算力', t, WT('c6a2', '扩建'), 330, 720, 26, BLUE_L, a)
        qcard(cv, 'quse', t, WT('c6a2', '扩建') - 0.3, t1, cy=1000, en=28, cn=34)
        big_q(cv, t, '也直接为谷歌的 AI 扩张出了钱', 1300, WT('c6a2', '也直接'), 48, a)
        source(cv, 'Alphabet 2026-06-01 融资公告、6-02 定价公告；10-Q（ATM 用途）· 计划额，实际募集以 10-Q 为准', a, y=1462)
    t0, t1 = win('c6b')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('2026 年 10 月 28 日 · 谷歌三季度财报', W / 2, 370, 34, 'sans_med', col=CREAM, a=a)
        rows = [('云业务收入', '+103%', WT('c6b', '云业务'), GREEN), ('搜索收入', '+12%', WT('c6b', '搜索收入'), CREAM),
                ('净利润', '$350 亿 → $265 亿', WT('c6b', '净利润'), RED)]
        for j, (nm, v, ts, col) in enumerate(rows):
            k = eo((t - ts + 0.1) / 0.4); y = 500 + j * 130; dx = 40 * (1 - k)
            cv.rrect(110 + dx, y - 52, 970 + dx, y + 52, 14, C(30, 28, 26), a * k * 0.92)
            cv.rect(110 + dx, y - 52, 118 + dx, y + 52, col, a * k, glow=0.4)
            cv.text(nm, 160 + dx, y, 36, 'sans_med', col=CREAM, a=a * k, anchor='l')
            cv.text(v, 930 + dx, y, 48, 'sans_bold', col=col, a=a * k, anchor='r', glow=0.12, shadow=0.6)
            if 0 < t - ts + 0.1 < 0.8: cv.glow_dot((110 + 860 * eio((t - ts + 0.1) / 0.8), y + 52), 20, col, a * 0.7)
        k = eo((t - WT('c6b', '主要是') + 0.1) / 0.4)
        if k > 0: note(cv, '其中：持有的其他公司股权账面亏损约 $87 亿', 850, a * k, 26, col=GOLD_L)
        k = eo((t - WT('c6b', '第二天') + 0.1) / 0.4)
        if k > 0:
            cv.text('$324.89 → $283.82', W / 2, 1010, 76, 'sans_bold', col=CREAM, a=a * k, shadow=0.7)
            cv.text('GOOGL · 10-28 → 10-29 收盘 · −12.6%', W / 2, 1100, 30, 'sans_med', col=RED, a=a * k, glow=0.1)
        note(cv, '只列事实，不判断哪一项“导致”下跌；公司称搜索增速放慢主要是汇率影响', 1200, a, 22)
        source(cv, 'Alphabet 2026 年三季度财报与电话会；Yahoo Finance 收盘价', a, y=1462)
    t0, t1 = win('c6c')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        items = [('定增价（A 类）', 351.81, t0 + 0.2, GOLD, '2026-06'), ('11-09 收盘（A 类）', 288.15, WT('c6c', '288'), RED, '−18%')]
        vbars(cv, t, items, a, x0=200, x1=880, base=1000, hmax=500, fmt=lambda v: f'${v:,.2f}', size=46, lab=24)
        k = eo((t - WT('c6c', '光是') + 0.1) / 0.5)
        if k > 0:
            cv.text('$100 亿 → 约 $82 亿', W / 2, 1200, 70, 'sans_bold', gold=True, a=a * k, glow=0.2)
            cv.text('按 A、C 两类股数分别乘以 11-09 收盘价', W / 2, 1290, 26, 'sans_light', col=GREY, a=a * k)
        source(cv, 'Alphabet 8-K（A 14,212,035 股、C 14,359,656 股）；Yahoo Finance 11-09 收盘（A $288.15、C $286.01）', a, y=1462)
    # 三件事（c6e–c6h 一个连续镜头）
    t0, t1 = S('c6e') - 0.3, E('c6h') + 0.6
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('未来十年，盯住三件事', W / 2, 420, 50, 'serif_black', gold=True, a=a)
        items = [('01', '搜索', '搜索广告收入与查询量', 'c6f'), ('02', '云', '云业务收入与经营利润', 'c6g'), ('03', '回报', '资本开支与自由现金流', 'c6h')]
        for j, (num, nm, sub, lid) in enumerate(items):
            y = 640 + j * 230
            on = eo((t - S(lid) + 0.2) / 0.5)
            cv.rrect(140, y - 90, 940, y + 90, 16, C(28, 26, 24), a * (0.5 + 0.5 * on))
            cv.rrect(140, y - 90, 940, y + 90, 16, GOLD if on > 0.5 else DIM, a * 0.8, fill=False, th=2, glow=0.15 * on)
            cv.text(num, 210, y, 56, 'oswald', col=GOLD if on > 0.5 else DIM, a=a)
            cv.text(nm, 300, y - 22, 46, 'serif_black', col=CREAM, a=a * on, anchor='l')
            cv.text(sub, 300, y + 40, 26, 'sans_light', col=GREY, a=a * on, anchor='l')
            icon(cv, ['search', 'cloud', 'cycle'][j], 860, y, 1.15, GOLD_L if on > 0.5 else DIM, a * (0.35 + 0.65 * on))
            if 0 < t - S(lid) + 0.2 < 0.9: fx.sweep(cv, t, S(lid) - 0.2, 0.8, a=0.25 * a)
        note(cv, '本片解读；“远高于国债的回报”取自巴菲特 2026-07-15 的标准', 1330, a * eo((t - S('c6h')) / 0.5), 22)
    t0, t1 = win('c6i')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        k = eo((t - WT('c6i', '二十年后')) / 1.0)
        doc_page(cv, t, t0, t1, 'FORM S-1 · 2004', ['An Owner’s Manual', 'for Google’s Shareholders'], cy=640, w=760, size=36,
                 font='playfair', a=a * (1 - 0.6 * k))
        doc_page(cv, t, WT('c6i', '二十年后') - 0.2, t1, 'SEC 13F · BERKSHIRE HATHAWAY · 2025',
                 ['ALPHABET INC CL A', '17,846,142'], cy=1060, w=760, size=36, font='mono', a=a)
    t0, t1 = S('c6j') - 0.3, CH['end'][0] + 0.5
    a = env(t, t0, t1, 0.4, 0.8)
    if a > 0:
        ks = eo((t - WT('c6j', '只是')) / 1.0)
        photo_win(cv, 'omaha_river', t, t0, t1, cap='奥马哈，隔着密苏里河从 Council Bluffs 拍摄', focus=(0.5, 0.55), a=1 - 0.6 * ks)
        snap = clip_snap(cv)
        servers(cv, t, 1060, a * ks, rows=3, growth=1.0, f=380.0)
        clip_band(cv, snap, top=(860, 900), bot=(1250, 1330))
        big_q(cv, t, '已经不是当年的谷歌了', 1390, WT('c6j', '已经不是'), 54, a)
