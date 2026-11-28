"""第七期《银行赚 13%，它凭什么赚 30%？——巴菲特持有三十年的美国运通》全部镜头：开场、片名、第一至七章。

版式（沿用前几期）：上方画窗（y≈280–760）放真实影像；下方 y 880–1420 放动画解读；y≈1462 出处；y≈1555 字幕。
素材：archive.org 实拍（src/fetch_ia.py）——1958 年纽交所宣传片《The Big Board》nyse*、1960 年代运通旅行支票广告 tc_*、
1988/1989 年运通卡广告 ad88_* / ad89_*、2018 年百夫长贵宾厅开业 lg_*、2019 年达美航空首航 dl_*、ABC《20/20》2005 年 Costco a_*；
Wikimedia Commons 照片（assets/media/credits.json）；其余为年报、致股东信数据的图表与示意动画（示意处标注“示意”）。
自绘图形（油罐、卡片、网络图等）都是通用示意，不画任何公司的商标。
"""
import math
import numpy as np, cv2
from common import *          # noqa
from common import _SAY
import os
import media as M
import fx
from sot import FADE as SOT_FADE

PAPER = C(236, 228, 210)
INKD = C(40, 36, 32)
CHOC = C(92, 58, 38)
CHOC_D = C(52, 32, 22)
CREAM_W = C(246, 236, 214)
BLUE_L = C(150, 195, 255)
COST_R = C(225, 60, 60)        # 通用“红”（价签、警示）
GREEN = C(110, 200, 140)


# ======================================================================== 通用构件
def first_have(names):
    for n in names:
        if M.have(n): return n
    return None


def seq(cv, t, t0, t1, names, cy=560, w=1000, h=420, focus=None, xfade=0.45, cap=None, a=1.0):
    """多段素材按原速串接（不慢放单个镜头）：每段播放它在 USABLE 里的可用时长，用完换下一段。
    v3：段与段之间是真正的叠化——前一段保持不透明，后一段在上面淡入（不再两段同时变淡、中间掉黑）"""
    if not (t0 - 0.1 <= t <= t1 + 0.1): return
    durs = [M.USABLE.get(n, (0, 6))[1] - M.USABLE.get(n, (0, 6))[0] if n in M.USABLE else 6.0 for n in names]
    durs = [max(d, 1.5) for d in durs]
    k, start = 0, t0
    while start + durs[k % len(names)] < t and start + durs[k % len(names)] < t1 - 0.5:
        start += durs[k % len(names)] - xfade; k += 1
    if k >= len(names) and os.environ.get('LOOPLOG'):          # 素材不够、开始循环重放：记下来补素材
        open(os.environ['LOOPLOG'], 'a').write(f'{names} {t0:.1f}-{t1:.1f}\n')
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
            M.frame(cv, nm, t, s0, s1, cy=cy, w=w, h=hh, z0=1.0, z1=1.04, focus=fc, a=a, fi=fi, fo=fo, src_t0=st, speed=1.0, cap=cap,
                    hold=s1 < t1 - 1e-6)


PORTRAIT = {'c_moody1903', 'buffett_2010', 'buffett_2015', 'buffett_ku', 'munger', 'munger2', 'sinegal', 'c_munger', 'c_buffett_ku', 'c_buffett_2010'}      # 人像照片：整幅入窗，不放大成大头像


def photo_win(cv, name, t, t0, t1, cy=560, w=1000, h=562, focus=(0.5, 0.5), cap=None, a=1.0, z0=1.02, z1=1.12, pan=(0, 0, 0, 0)):
    if name in PORTRAIT:
        return M.frame(cv, name, t, t0, t1, cy=cy, w=w, h=h, z0=1.0, z1=1.03, focus=focus, a=a, cap=cap, fit='contain', pan=pan)
    return M.frame(cv, name, t, t0, t1, cy=cy, w=w, h=h, z0=z0, z1=z1, focus=focus, a=a, cap=cap, pan=pan)


def pic(cv, names, t, t0, t1, fb=None, fbcap=None, **kw):
    """names 里第一张已入库的照片；都没有时用 fb（档案影像）串接；仍没有则返回 False（调用方画后备画面）"""
    n = first_have(names)
    if n is None:
        if fb:
            seq(cv, t, t0, t1, fb, cap=fbcap, **{k: v for k, v in kw.items() if k in ('cy', 'w', 'h', 'a')}); return True
        return False
    photo_win(cv, n, t, t0, t1, **kw); return True


def qcard(cv, key, t, t0, t1, cy=1150, w=960, en=30, cn=36, a=1.0, typing=1.4):
    quote_card(cv, key, t, t0, t1, cy=cy, en_size=en, cn_size=cn, a=a, typing=typing, w=w)


def doc_page(cv, t, t0, t1, head, lines, cy=760, w=880, size=30, hl=None, hl_t=None, a=1.0, sub=None, font='typewriter'):
    """文件原文页（致股东信）：米色纸张 + 打字机字体；hl 为需要划金线的短语，hl_t 为划线时刻"""
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


def big_q(cv, t, txt, y, tw, size=60, a=1.0, col=None, x=None):
    k = eo((t - tw + 0.1) / 0.5)
    x = W / 2 if x is None else x
    if k > 0:
        if col is None: cv.text(txt, x, y + 16 * (1 - k), size, 'serif_black', gold=True, a=a * k, glow=0.2, shadow=0.8)
        else: cv.text(txt, x, y + 16 * (1 - k), size, 'serif_black', col=col, a=a * k, shadow=0.8)


def note(cv, s, y, a, size=24, col=None):
    if a > 0.004: cv.text(s, W / 2, y, size, 'sans_light', col=col if col is not None else GREY, a=a)


def money(cv, t, tw, txt, x, y, size=72, a=1.0, col=None, sub=None, sub_col=None):
    """大号金额：随时间从下方浮起；sub 为下方小字"""
    k = eo((t - tw + 0.1) / 0.45)
    if k <= 0: return
    if col is None: cv.text(txt, x, y + 18 * (1 - k), size, 'sans_bold', gold=True, a=a * k, glow=0.15, shadow=0.7)
    else: cv.text(txt, x, y + 18 * (1 - k), size, 'sans_bold', col=col, a=a * k, shadow=0.7)
    if sub: cv.text(sub, x, y + size * 0.85 + 8, 26, 'sans_light', col=sub_col or GREY, a=a * k)


def blocks(cv, t, t0, x0, y_base, n, a, s=46, gap=6, col=GOLD, per_row=10, stagger=0.04, label=None):
    """以小方块堆叠表示金额（每块 = 100 万美元）：从下往上、从左往右逐块落下"""
    for k in range(n):
        tk = t0 + k * stagger
        e = eo((t - tk) / 0.35)
        if e <= 0: continue
        r, c = divmod(k, per_row)
        x = x0 + c * (s + gap); y = y_base - r * (s + gap) - s - 30 * (1 - e)
        cv.rect(x, y, x + s, y + s, col * 0.75, a * e, glow=0.06)
        cv.line((x, y), (x + s, y), GOLD_L, a * e * 0.6, 1)


def disc(cv, c, r, col, a):
    """实心圆（不透明，画在图像层上；cv.circle 的填充在叠加层，会发光、不能遮挡）"""
    if a <= 0.004 or r <= 0.5: return
    k = max(16, int(r * 0.8)); k = min(k, 64)
    cv.fillpoly([(c[0] + r * math.cos(2 * math.pi * i / k), c[1] + r * math.sin(2 * math.pi * i / k)) for i in range(k)], col, a)


# ------------------------------------------------------------------ 自绘：糖盒、门店、印花、信封、烟蒂、蓝图、储蓄罐
def candy_box(cv, cx, cy, s, a, lid=0.0, glow=0.0):
    """白色盒装巧克力（自绘线稿，不是喜诗商标）：lid 0=盖着、1=打开见到 3×4 颗巧克力"""
    if a <= 0.004: return
    w, h = 360 * s, 250 * s
    x0, y0 = cx - w / 2, cy - h / 2
    sh = np.zeros((int(h) + 80, int(w) + 80), np.float32); sh[40:-40, 40:-40] = 1
    cv.img_mul(1 - cv2.GaussianBlur(sh, (0, 0), 18) * 0.55 * a, x0 - 40, y0 - 22)
    cv.rrect(x0, y0, x0 + w, y0 + h, 10 * s, CREAM_W * 0.92, a)
    cv.rrect(x0 + 10 * s, y0 + 10 * s, x0 + w - 10 * s, y0 + h - 10 * s, 6 * s, CHOC_D, a * 0.9)
    for r in range(3):
        for c in range(4):
            px = x0 + 10 * s + (c + 0.5) * (w - 20 * s) / 4; py = y0 + 10 * s + (r + 0.5) * (h - 20 * s) / 3
            cv.rrect(px - 34 * s, py - 28 * s, px + 34 * s, py + 28 * s, 8 * s, C(70, 44, 30), a)
            disc(cv, (px, py), 22 * s, C(118, 76, 50), a)
            cv.arc((px, py), 16 * s, math.pi * 1.1, math.pi * 1.6, C(190, 140, 100), a * 0.8, max(1, int(3 * s)))
    if lid < 1:
        k = eo(lid)
        ly = y0 - k * (h + 60 * s)
        la = a * (1 - k * 0.85)
        cv.rrect(x0 - 6 * s, ly - 6 * s, x0 + w + 6 * s, ly + h + 6 * s, 12 * s, CREAM_W, la)
        cv.rrect(x0 - 6 * s, ly - 6 * s, x0 + w + 6 * s, ly + h + 6 * s, 12 * s, GOLD_D, la * 0.7, fill=False, th=2)
        cv.rect(cx - 16 * s, ly - 6 * s, cx + 16 * s, ly + h + 6 * s, C(160, 40, 50), la * 0.9)          # 缎带
        cv.rect(x0 - 6 * s, ly + h / 2 - 14 * s, x0 + w + 6 * s, ly + h / 2 + 14 * s, C(160, 40, 50), la * 0.9)
        disc(cv, (cx, ly + h / 2), 26 * s, C(180, 50, 60), la)
    if glow > 0: cv.glow_dot((cx, cy), 220 * s, GOLD_L, a * glow * 0.5)


def storefront(cv, t, cx, cy, s, a, year=None, sign='CANDIES'):
    """示意：老式糖果小店（黑白格地砖、白色店面、橱窗里的糖盒、门上方招牌），全部自绘"""
    if a <= 0.004: return
    w, h = 640 * s, 420 * s
    x0, y0 = cx - w / 2, cy - h / 2
    cv.rect(x0, y0, x0 + w, y0 + h, CREAM_W * 0.95, a)
    cv.rect(x0, y0, x0 + w, y0 + 70 * s, CHOC_D, a)
    cv.text(sign, cx, y0 + 36 * s, int(34 * s), 'playfair', col=CREAM_W, a=a, track=0.3)
    # 橱窗
    for k, xx in enumerate((x0 + 40 * s, x0 + w - 260 * s)):
        cv.rect(xx, y0 + 110 * s, xx + 220 * s, y0 + 300 * s, C(40, 50, 60), a)
        cv.rrect(xx, y0 + 110 * s, xx + 220 * s, y0 + 300 * s, 4, GOLD_D, a * 0.7, fill=False, th=2)
        for j in range(3):
            bx = xx + 30 * s + j * 60 * s; by = y0 + 250 * s - (j % 2) * 40 * s
            cv.rect(bx, by, bx + 50 * s, by + 34 * s, CREAM_W, a * 0.95)
            cv.rect(bx + 22 * s, by, bx + 28 * s, by + 34 * s, C(160, 40, 50), a * 0.9)
        cv.glow_dot((xx + 110 * s, y0 + 200 * s), 90 * s, GOLD_L, a * 0.25 * (0.8 + 0.2 * math.sin(t * 2 + k)))
    # 门
    cv.rect(cx - 70 * s, y0 + 130 * s, cx + 70 * s, y0 + h, CHOC, a)
    cv.rect(cx - 50 * s, y0 + 150 * s, cx + 50 * s, y0 + 260 * s, C(60, 72, 84), a)
    disc(cv, (cx + 45 * s, y0 + 300 * s), 6 * s, GOLD_L, a)
    # 遮阳篷（红白条）
    for k in range(10):
        xa = x0 + k * w / 10
        cv.fillpoly([(xa, y0 + 70 * s), (xa + w / 10, y0 + 70 * s), (xa + w / 10 + 6 * s, y0 + 104 * s), (xa + 6 * s, y0 + 104 * s)],
                    C(170, 50, 55) if k % 2 == 0 else CREAM_W, a)
    # 黑白格地砖
    for k in range(16):
        xa = x0 + k * w / 16
        cv.rect(xa, y0 + h, xa + w / 16, y0 + h + 22 * s, INKD if k % 2 == 0 else CREAM_W, a)
    if year: cv.text(year, cx, y0 + h + 70 * s, int(30 * s), 'oswald', col=GOLD, a=a, track=0.2)


def stamp(cv, cx, cy, s, a, label='BLUE CHIP', sub='STAMPS', rot=0.0):
    """示意：一枚交易印花（蓝色锯齿边）"""
    if a <= 0.004: return
    w, h = 300 * s, 200 * s
    pts = []
    n = 14
    for i in range(n * 4):
        side = i // n; f = (i % n) / n
        if side == 0: x, y = -w / 2 + f * w, -h / 2
        elif side == 1: x, y = w / 2, -h / 2 + f * h
        elif side == 2: x, y = w / 2 - f * w, h / 2
        else: x, y = -w / 2, h / 2 - f * h
        r = 1 + (0.035 if i % 2 else 0)
        pts.append((x * r, y * r))
    cr, sr = math.cos(rot), math.sin(rot)
    P = [(cx + x * cr - y * sr, cy + x * sr + y * cr) for x, y in pts]
    cv.fillpoly(P, C(225, 232, 244), a)
    inner = [(cx + x * cr - y * sr, cy + x * sr + y * cr) for x, y in ((-w / 2 + 18 * s, -h / 2 + 18 * s), (w / 2 - 18 * s, -h / 2 + 18 * s),
                                                                     (w / 2 - 18 * s, h / 2 - 18 * s), (-w / 2 + 18 * s, h / 2 - 18 * s))]
    cv.fillpoly(inner, C(40, 80, 160), a)
    cv.text(label, cx, cy - 16 * s, int(40 * s), 'oswald', col=WHITE, a=a, track=0.12)
    cv.text(sub, cx, cy + 34 * s, int(24 * s), 'corm', col=C(220, 230, 250), a=a, track=0.4)


def envelope(cv, x, y, s, a, rot=0.0):
    if a <= 0.004: return
    w, h = 120 * s, 76 * s
    cr, sr = math.cos(rot), math.sin(rot)
    def R(px, py): return (x + px * cr - py * sr, y + px * sr + py * cr)
    box = [R(-w / 2, -h / 2), R(w / 2, -h / 2), R(w / 2, h / 2), R(-w / 2, h / 2)]
    cv.fillpoly(box, CREAM_W, a)
    cv.poly(box + [box[0]], GOLD_D, a * 0.8, 2)
    cv.poly([R(-w / 2, -h / 2), R(0, 6 * s), R(w / 2, -h / 2)], GOLD_D, a * 0.8, 2)


def cigar_butt(cv, t, cx, cy, s, a, smoke=1.0):
    """示意：街边捡到的烟蒂，冒出最后一缕烟"""
    if a <= 0.004: return
    cv.rrect(cx - 120 * s, cy - 18 * s, cx + 60 * s, cy + 18 * s, 8 * s, C(120, 80, 50), a)
    cv.rect(cx - 120 * s, cy - 18 * s, cx - 80 * s, cy + 18 * s, C(200, 170, 120), a)
    cv.rrect(cx + 50 * s, cy - 18 * s, cx + 74 * s, cy + 18 * s, 6 * s, C(70, 70, 70), a)
    cv.glow_dot((cx + 72 * s, cy), 22 * s, C(255, 120, 40), a * (0.7 + 0.3 * math.sin(t * 6)))
    for k in range(18):
        ph = (t * 0.35 + k / 18) % 1.0
        x = cx + 74 * s + math.sin(ph * 6 + k) * 30 * s * ph
        y = cy - 20 * s - ph * 260 * s
        cv.glow_dot((x, y), (8 + 26 * ph) * s, C(200, 200, 210), a * smoke * 0.22 * (1 - ph))


def blueprint(cv, x0, y0, x1, y1, a):
    if a <= 0.004: return
    cv.rect(x0, y0, x1, y1, C(18, 44, 92), a)
    for k in range(int((x1 - x0) / 40) + 1):
        cv.line((x0 + k * 40, y0), (x0 + k * 40, y1), C(80, 130, 200), a * (0.35 if k % 5 else 0.6), 1)
    for k in range(int((y1 - y0) / 40) + 1):
        cv.line((x0, y0 + k * 40), (x1, y0 + k * 40), C(80, 130, 200), a * (0.35 if k % 5 else 0.6), 1)
    cv.rrect(x0, y0, x1, y1, 4, C(160, 200, 255), a * 0.8, fill=False, th=2)


def jar(cv, t, cx, by, w, h, fill, a, col=GOLD, label=None, rate=None, arrow_in=0.0, arrow_out=0.0, rising=False):
    """储蓄罐（玻璃罐）：fill 为装满比例；arrow_in 上方“存入”箭头，arrow_out 下方“利息流出”"""
    if a <= 0.004: return
    x0, x1 = cx - w / 2, cx + w / 2; y0 = by - h
    fh = h * cl(fill)
    if fh > 2:
        cv.rect(x0 + 8, by - fh, x1 - 8, by - 6, col * 0.55, a)
        for k in range(int(fh / 26)):
            yy = by - 18 - k * 26
            cv.line((x0 + 14, yy), (x1 - 14, yy), col * 0.85, a * 0.5, 2)
    cv.rrect(x0, y0, x1, by, 18, C(180, 200, 220), a * 0.75, fill=False, th=3)
    cv.rect(x0 + 16, y0 - 26, x1 - 16, y0, C(150, 160, 170), a * 0.9)
    cv.line((x0 + 18, y0 + 20), (x0 + 18, by - 20), WHITE, a * 0.35, 3)
    if label: cv.text(label, cx, by + 46, 30, 'sans_bold', col=col, a=a)
    if rate: cv.text(rate, cx, by + 90, 24, 'sans_light', col=CREAM, a=a)
    if arrow_in > 0:
        for k in range(3):
            ph = (t * 0.9 + k / 3) % 1.0
            yy = y0 - 150 + ph * 120
            cv.text('$', cx, yy, 34, 'sans_bold', col=RED, a=a * arrow_in * math.sin(ph * math.pi))
        cv.text('往里存钱', cx, y0 - 180, 22, 'sans_light', col=RED, a=a * arrow_in)
    if arrow_out > 0:
        for k in range(4):
            ph = (t * 0.8 + k / 4) % 1.0
            ang = -math.pi / 2 + (k - 1.5) * 0.35
            d = 60 + ph * 140 * arrow_out
            x, y = cx + math.cos(ang) * d, y0 - 30 + math.sin(ang) * d
            cv.text('$', x, y, 30 if not rising else int(26 + 16 * ph), 'sans_bold', col=GOLD_L, a=a * arrow_out * (1 - ph))


def us_west(cv, cx, cy, sc, a, dots=None, t=0.0):
    """美国西部点阵（Natural Earth 陆地遮罩，公有领域）：dots = [(lat, lon, 亮度)]"""
    if a <= 0.004: return
    m = _landmask()
    for lat in np.arange(30.0, 50.1, 0.75):
        for lon in np.arange(-125.0, -103.9, 0.75):
            px = int((lon + 180) * 2) % 720; py = int((90 - lat) * 2)
            if m[py, px] > 127:
                x = cx + (lon + 114.5) * sc * math.cos(math.radians(40)); y = cy - (lat - 40) * sc
                disc(cv, (x, y), 2.6, C(120, 110, 100), a * 0.7)
    for (lat, lon, k) in (dots or []):
        if k <= 0: continue
        x = cx + (lon + 114.5) * sc * math.cos(math.radians(40)); y = cy - (lat - 40) * sc
        cv.glow_dot((x, y), 5 + 4 * k, GOLD_L, a * k)


_lm = {}
def _landmask():
    if 'm' not in _lm:
        _lm['m'] = cv2.imread(os.path.join(ROOT, 'assets', 'geo', 'landmask.png'), 0)
    return _lm['m']


# ======================================================================== 第六期新增构件（全部为通用示意图形）
def pre_sot(i, sid, pre=0.3):
    """引出原声的那句旁白：镜头在原声画面压上来之前收住（不与原声画面叠影）"""
    return S(i) - pre, S('sot_' + sid) - SEG['sot_' + sid]['lead'] - SOT_FADE


def hotdog(cv, cx, cy, s, a, t=0.0, steam=True):
    """示意：一根热狗 + 一杯汽水（通用线稿）"""
    if a <= 0.004: return
    cv.rrect(cx - 170 * s, cy - 10 * s, cx + 170 * s, cy + 60 * s, 34 * s, C(214, 160, 92), a)
    cv.rrect(cx - 160 * s, cy + 22 * s, cx + 160 * s, cy + 58 * s, 26 * s, C(188, 130, 70), a)
    cv.rrect(cx - 196 * s, cy - 30 * s, cx + 196 * s, cy + 18 * s, 24 * s, C(170, 70, 50), a)
    cv.line((cx - 170 * s, cy - 22 * s), (cx + 160 * s, cy - 22 * s), C(220, 120, 90), a * 0.6, max(1, int(4 * s)))
    pts = [(cx - 150 * s + k * 15 * s, cy - 6 * s + 9 * s * math.sin(k * 1.3)) for k in range(21)]
    cv.poly(pts, C(240, 200, 60), a, max(2, int(7 * s)))
    x = cx + 290 * s
    cv.fillpoly([(x - 60 * s, cy - 120 * s), (x + 60 * s, cy - 120 * s), (x + 46 * s, cy + 60 * s), (x - 46 * s, cy + 60 * s)], C(235, 235, 240), a)
    cv.rect(x - 58 * s, cy - 70 * s, x + 58 * s, cy - 20 * s, COST_R * 0.9, a)
    cv.rect(x - 64 * s, cy - 134 * s, x + 64 * s, cy - 120 * s, C(200, 200, 205), a)
    cv.line((x + 14 * s, cy - 134 * s), (x + 34 * s, cy - 200 * s), C(230, 230, 235), a, max(2, int(6 * s)))
    if steam:
        for k in range(3):
            ph = (t * 0.5 + k / 3) % 1.0
            cv.glow_dot((cx - 80 * s + k * 80 * s, cy - 60 * s - ph * 90 * s), 14 * s * (0.5 + ph), CREAM, a * 0.18 * (1 - ph))


def price_tag(cv, cx, cy, s, a, txt, sub=None, col=COST_R, rot=0.0):
    """价签（通用）"""
    if a <= 0.004: return
    w, h = 300 * s, 150 * s
    cr, sr = math.cos(rot), math.sin(rot)
    def R(x, y): return (cx + x * cr - y * sr, cy + x * sr + y * cr)
    P = [R(-w / 2 + 40 * s, -h / 2), R(w / 2, -h / 2), R(w / 2, h / 2), R(-w / 2 + 40 * s, h / 2), R(-w / 2, 0)]
    cv.fillpoly(P, CREAM_W, a)
    cv.poly(P + [P[0]], col, a * 0.9, max(2, int(4 * s)))
    disc(cv, R(-w / 2 + 34 * s, 0), 9 * s, INKD, a)
    p = R(14 * s, -8 * s if sub else 0); cv.text(txt, p[0], p[1], int(64 * s), 'sans_bold', col=col, a=a)
    if sub: p = R(14 * s, 44 * s); cv.text(sub, p[0], p[1], int(22 * s), 'sans_med', col=INKD, a=a)


def factory(cv, cx, cy, s, a, col=GOLD):
    """示意：工厂（锯齿屋顶 + 烟囱）"""
    if a <= 0.004: return
    w, h = 200 * s, 110 * s
    x0, y0 = cx - w / 2, cy - h / 2
    pts = [(x0, y0 + h), (x0, y0)]
    for k in range(3):
        pts += [(x0 + k * w / 3 + w / 3, y0 - 40 * s), (x0 + (k + 1) * w / 3, y0)]
    pts += [(x0 + w, y0 + h)]
    cv.fillpoly(pts, (0.09, 0.08, 0.07), a)
    cv.poly(pts + [pts[0]], col, a, 3)
    cv.rect(x0 + w - 40 * s, y0 - 90 * s, x0 + w - 18 * s, y0, (0.09, 0.08, 0.07), a)
    cv.poly([(x0 + w - 40 * s, y0), (x0 + w - 40 * s, y0 - 90 * s), (x0 + w - 18 * s, y0 - 90 * s), (x0 + w - 18 * s, y0)], col, a, 3)
    for k in range(3):
        cv.rect(x0 + 24 * s + k * 58 * s, y0 + 40 * s, x0 + 54 * s + k * 58 * s, y0 + 70 * s, col * 0.6, a)


def node(cv, x, y, txt, a, col=GOLD, size=30, w=None, sub=None, fill=(0.07, 0.06, 0.05)):
    """圆角信息框（宽度按标题与小字中较宽的一个）"""
    if a <= 0.004: return
    tw = text_size(txt, 'sans_bold', size)[0]
    if sub: tw = max(tw, text_size(sub, 'sans_light', int(size * 0.7))[0])
    w = w or tw + 60
    h = size * 2.1 + (size * 0.9 if sub else 0)
    cv.rrect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, 16, fill, a * 0.92)
    cv.rrect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, 16, col, a * 0.85, fill=False, th=2)
    cv.text(txt, x, y - (size * 0.42 if sub else 0), size, 'sans_bold', col=col if col is not GOLD else GOLD_L, a=a)
    if sub: cv.text(sub, x, y + size * 0.62, int(size * 0.7), 'sans_light', col=CREAM, a=a)


def arrow(cv, p0, p1, a, col=GOLD, th=3, head=16, k=1.0):
    if a <= 0.004 or k <= 0: return
    x = p0[0] + (p1[0] - p0[0]) * k; y = p0[1] + (p1[1] - p0[1]) * k
    cv.line(p0, (x, y), col, a, th)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    cv.fillpoly([(x, y), (x - head * math.cos(ang - 0.45), y - head * math.sin(ang - 0.45)),
                 (x - head * math.cos(ang + 0.45), y - head * math.sin(ang + 0.45))], col, a)


def person(cv, x, y, s, a, col=CREAM):
    if a <= 0.004: return
    disc(cv, (x, y - 34 * s), 14 * s, col, a)
    cv.fillpoly([(x - 20 * s, y + 20 * s), (x - 16 * s, y - 14 * s), (x + 16 * s, y - 14 * s), (x + 20 * s, y + 20 * s)], col, a)


def hangar(cv, cx, cy, s, a, t=0.0):
    """示意：拱顶飞机库改成的仓库"""
    if a <= 0.004: return
    w, h = 520 * s, 230 * s
    pts = [(cx - w / 2 + w * k / 40, cy - h * 0.25 - h * 0.75 * math.sin(math.pi * k / 40)) for k in range(41)]
    body = [(cx - w / 2, cy + h * 0.5)] + pts + [(cx + w / 2, cy + h * 0.5)]
    cv.fillpoly(body, (0.10, 0.10, 0.11), a)
    cv.poly(pts, GOLD_L, a, 3)
    cv.line((cx - w / 2, cy + h * 0.5), (cx + w / 2, cy + h * 0.5), GOLD_D, a, 3)
    cv.line((cx - w / 2, cy + h * 0.5), (cx - w / 2, cy - h * 0.25), GOLD_D, a, 3)
    cv.line((cx + w / 2, cy + h * 0.5), (cx + w / 2, cy - h * 0.25), GOLD_D, a, 3)
    for k in range(1, 8):
        x = cx - w / 2 + w * k / 8
        yy = cy - h * 0.25 - h * 0.75 * math.sin(math.pi * k / 8)
        cv.line((x, cy + h * 0.5), (x, yy), GOLD_D, a * 0.35, 1)
    cv.rect(cx - 120 * s, cy + h * 0.05, cx + 120 * s, cy + h * 0.5, (0.04, 0.04, 0.05), a)
    for j in range(4):
        for r in range(2):
            bx = cx - 100 * s + j * 52 * s; by = cy + h * 0.5 - 8 * s - (r + 1) * 30 * s
            cv.rect(bx, by, bx + 44 * s, by + 26 * s, C(160 + 20 * ((j + r) % 2), 130, 90), a * 0.85)
    for k in range(5): cv.glow_dot((cx - 200 * s + k * 100 * s, cy - h * 0.1), 8 * s, CREAM, a * 0.5 * (0.8 + 0.2 * math.sin(t * 3 + k)))


def card(cv, cx, cy, s, a, title, sub, col=C(200, 205, 215), rot=0.0):
    """示意：一张通用会员卡/信用卡（不画任何商标）"""
    if a <= 0.004: return
    w, h = 400 * s, 250 * s
    cr, sr = math.cos(rot), math.sin(rot)
    def R(x, y): return (cx + x * cr - y * sr, cy + x * sr + y * cr)
    P = [R(-w / 2, -h / 2), R(w / 2, -h / 2), R(w / 2, h / 2), R(-w / 2, h / 2)]
    cv.fillpoly(P, col * 0.55, a)
    cv.poly(P + [P[0]], col, a, 2)
    cv.fillpoly([R(-w / 2 + 34 * s, -30 * s), R(-w / 2 + 94 * s, -30 * s), R(-w / 2 + 94 * s, 14 * s), R(-w / 2 + 34 * s, 14 * s)], GOLD, a * 0.9)
    p = R(0, -h / 2 + 50 * s); cv.text(title, p[0], p[1], int(34 * s), 'sans_bold', col=WHITE, a=a)
    p = R(0, h / 2 - 40 * s); cv.text(sub, p[0], p[1], int(22 * s), 'oswald', col=CREAM, a=a, track=0.2)


def gauge(cv, cx, cy, r, v, a, col=GOLD, label=None, fmt='{:.1f}%', size=56):
    """环形进度（v：0–1）"""
    if a <= 0.004: return
    cv.arc((cx, cy), r, -math.pi / 2, 1.5 * math.pi, DIM, a * 0.7, 14)
    if v > 0: cv.arc((cx, cy), r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * v, col, a, 14)
    cv.text(fmt.format(v * 100), cx, cy, size, 'sans_bold', col=GOLD_L if col is GOLD else col, a=a)
    if label: cv.text(label, cx, cy + r + 46, 26, 'sans_med', col=CREAM, a=a)


def dial(cv, cx, cy, r, v, vmax, a, ticks=(0, 10, 20, 30, 40, 50, 60)):
    """半圆仪表（市盈率）"""
    if a <= 0.004: return
    for k in range(60):
        f0, f1 = k / 60, (k + 1) / 60
        c = lerp(np.asarray(GREEN, np.float32), np.asarray(COST_R, np.float32), (f0 + f1) / 2)
        cv.arc((cx, cy), r, math.pi + math.pi * f0, math.pi + math.pi * f1 + 0.004, c, a * 0.85, 22)
    for tk in ticks:
        ang = math.pi + math.pi * tk / vmax
        cv.line((cx + (r - 30) * math.cos(ang), cy + (r - 30) * math.sin(ang)), (cx + (r + 16) * math.cos(ang), cy + (r + 16) * math.sin(ang)), CREAM, a * 0.7, 2)
        cv.text(f'{tk}', cx + (r + 48) * math.cos(ang), cy + (r + 48) * math.sin(ang), 26, 'oswald', col=GREY, a=a)
    ang = math.pi + math.pi * min(v, vmax) / vmax
    cv.line((cx, cy), (cx + (r - 40) * math.cos(ang), cy + (r - 40) * math.sin(ang)), GOLD_L, a, 6)
    disc(cv, (cx, cy), 16, GOLD, a)


def anchor_icon(cv, cx, cy, s, a, col=GOLD):
    if a <= 0.004: return
    cv.circle((cx, cy - 70 * s), 14 * s, col, a, 4)
    cv.line((cx, cy - 56 * s), (cx, cy + 60 * s), col, a, 6)
    cv.line((cx - 40 * s, cy - 30 * s), (cx + 40 * s, cy - 30 * s), col, a, 6)
    cv.arc((cx, cy + 10 * s), 56 * s, 0.15 * math.pi, 0.85 * math.pi, col, a, 6)


def flow_dots(cv, t, pts, a, col=GOLD_L, n=6, speed=0.35, size=7):
    """沿折线流动的光点（循环示意）"""
    if a <= 0.004: return
    segs = list(zip(pts, pts[1:]))
    L = [math.hypot(b[0] - a_[0], b[1] - a_[1]) for a_, b in segs]; tot = sum(L)
    for k in range(n):
        d = ((t * speed + k / n) % 1.0) * tot
        for (p, q), l in zip(segs, L):
            if d <= l:
                f = d / max(l, 1e-3); cv.glow_dot((p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f), size, col, a * 0.9); break
            d -= l


def ring_cycle(cv, t, cx, cy, R, labels, a, ks, col=GOLD, title=None, size=30, spin=True):
    """循环图：labels 沿圆周排布；ks 为每个节点出现的进度；节点之间用弧形箭头相连，光点沿环流动"""
    n = len(labels)
    angs = [-math.pi / 2 + 2 * math.pi * j / n for j in range(n)]
    for j in range(n):
        k = ks[j]; k2 = ks[(j + 1) % n] if j + 1 < n else ks[0]
        if k > 0 and k2 > 0:
            a0, a1 = angs[j] + 0.36, angs[j] + 2 * math.pi / n - 0.36
            m = min(k, k2)
            cv.arc((cx, cy), R, a0, a0 + (a1 - a0) * m, GOLD_D, a * 0.9, 4)
            if m > 0.98:
                ex, ey = cx + R * math.cos(a1), cy + R * math.sin(a1)
                tang = a1 + math.pi / 2
                cv.fillpoly([(ex + 16 * math.cos(tang), ey + 16 * math.sin(tang)), (ex + 10 * math.cos(tang + 2.3), ey + 10 * math.sin(tang + 2.3)),
                             (ex + 10 * math.cos(tang - 2.3), ey + 10 * math.sin(tang - 2.3))], GOLD, a)
    if spin and min(ks) > 0.98:
        for k in range(8):
            ang = -math.pi / 2 + 2 * math.pi * ((t * 0.18 + k / 8) % 1.0)
            cv.glow_dot((cx + R * math.cos(ang), cy + R * math.sin(ang)), 6, GOLD_L, a * 0.7)
    for j, lb in enumerate(labels):
        k = ks[j]
        if k <= 0: continue
        x, y = cx + R * math.cos(angs[j]), cy + R * math.sin(angs[j])
        node(cv, x, y + 10 * (1 - k), lb, a * k, col=col, size=size)
    if title: cv.text(title, cx, cy, 34, 'serif_semi', col=CREAM, a=a * min(ks))


def mini_photo(cv, name, t, t0, t1, cx, cy, w, h, a=1.0, cap=None):
    """小幅照片（网格拼贴用）：裁切 + 细金框 + 下方小字"""
    al = env(t, t0, t1, 0.4, 0.4) * a
    if al <= 0.004 or not M.have(name): return
    src = M.img(name)
    fr = M._crop(src, int(w), int(h), 1.0 + 0.04 * eio((t - t0) / max(t1 - t0, 1e-3)), 0.5, 0.5)
    fr = M.grade(fr, 0.15, 0.9)
    x0, y0 = cx - w / 2, cy - h / 2
    cv.over(fr, np.full((int(h), int(w)), al, np.float32), x0, y0)
    cv.rrect(x0 - 1, y0 - 1, x0 + w + 1, y0 + h + 1, 2, GOLD_D, al * 0.6, fill=False, th=2)
    if cap: cv.text(cap, cx, y0 + h + 24, 20, 'sans_med', col=CREAM, a=al)


# ======================================================================== 开场

def spear(cv, x, y, s, a, col):
    """示意：一支矛（横向，矛尖朝右）"""
    if a <= 0.004: return
    cv.line((x - 130 * s, y), (x + 70 * s, y), col * 0.75, a, int(8 * s))
    cv.fillpoly([(x + 70 * s, y - 22 * s), (x + 140 * s, y), (x + 70 * s, y + 22 * s)], col, a, glow=0.15)
    cv.line((x + 60 * s, y - 26 * s), (x + 60 * s, y + 26 * s), col, a, int(5 * s))


def shield(cv, x, y, s, a, col):
    """示意：一面盾"""
    if a <= 0.004: return
    pts = [(x - 80 * s, y - 90 * s), (x + 80 * s, y - 90 * s), (x + 80 * s, y + 10 * s)] + \
          [(x + 80 * s * math.cos(math.pi * k / 12), y + 10 * s + 90 * s * math.sin(math.pi * k / 12)) for k in range(1, 12)] + [(x - 80 * s, y + 10 * s)]
    cv.fillpoly(pts, (0.10, 0.09, 0.07), a)
    cv.poly(pts + [pts[0]], col, a, int(4 * s) or 1)
    cv.line((x, y - 70 * s), (x, y + 80 * s), col * 0.8, a, int(4 * s) or 1)
    cv.line((x - 60 * s, y - 20 * s), (x + 60 * s, y - 20 * s), col * 0.8, a, int(4 * s) or 1)


