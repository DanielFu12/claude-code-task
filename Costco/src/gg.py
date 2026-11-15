"""第六期《一块五的热狗——芒格为什么最爱 Costco》全部镜头：开场、片名、第一至七章。

版式（沿用前几期）：上方画窗（y≈279–841）放真实影像；下方 y 900–1420 放动画解读；y≈1462 出处；y≈1555 字幕。
素材：archive.org 实拍（src/fetch_ia.py）——ABC《20/20》2005 年 Costco 报道 a_*、CBS 8 圣地亚哥 1982 年 FedMart / Price Club / 索尔·普莱斯
fm_* / pc_* / sol_*、1966 年普莱斯采访 sol66_*、WBZ 1991 年 Costco 报道 w_*、2022 年《每日期刊》股东会芒格 m_dj*；
Wikimedia Commons 照片（assets/media/credits.json）；其余为年报、致股东信数据的图表与示意动画（示意处画面标注“示意”）。
所有自绘图形都是通用示意（热狗、价签、仓库、卡片等），不使用任何公司的商标或标识。
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


PORTRAIT = {'buffett_2010', 'buffett_2015', 'buffett_ku', 'munger', 'munger2', 'sinegal'}      # 人像照片：整幅入窗，不放大成大头像


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
def shot_hook(cv, t):
    a0 = env(t, 0, S('h1') + 0.6, 0.0, 0.5)
    if a0 > 0:
        L = 420 * eo(t / 1.1); hb = math.exp(-max(t - 0.25, 0) * 6) * (t >= 0.25)
        cv.line((W / 2 - L, 960), (W / 2 + L, 960), GOLD, a0 * (0.5 + 0.5 * hb), 2)
        cv.glow_dot((W / 2, 960), 30 + 40 * hb, GOLD, a0 * 0.6)
    # h1–h2：2011 年股东大会的劫机笑话（照片 + 两张引语卡）
    t0, t1 = S('h1') - 0.3, S('h3') - 0.2
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        if not pic(cv, ['buffett_munger2', 'buffett_munger', 'munger2'], t, t0, t1, cy=560, h=562, a=a, cap='巴菲特与芒格'):
            pic(cv, ['buffett_2015'], t, t0, t1, cy=560, h=562, a=a)
        tag(cv, '2011 · 伯克希尔股东大会', t, t0 + 0.3, W / 2, 940, 30, GOLD, a)
        k1 = eo((t - WT('h1', '劫持') + 0.1) / 0.5) * (1 - eo((t - WT('h2', '我想再讲') + 0.5) / 0.4))
        if k1 > 0:
            cv.text('一个笑话：飞机被劫持了', W / 2, 1070, 44, 'serif_semi', col=CREAM, a=a * k1)
            for j, nm in enumerate(('芒格的最后愿望？', '巴菲特的最后愿望？')):
                kk = eo((t - WT('h1', '每人') - j * 0.25) / 0.45)
                chip(cv, nm, 330 + j * 420, 1200, 32, a * k1 * kk, col=GOLD_L)
        t_q1 = WT('h2', '我想再讲') - 0.3; t_q2 = WT('h2', '那就先毙') - 0.4
        qcard(cv, 'qhijack', t, t_q1, t_q2 + 0.1, cy=1160, en=32, cn=38, a=a, typing=1.2)
        qcard(cv, 'qshoot', t, t_q2, t1, cy=1160, en=48, cn=46, a=a, typing=0.5)
        source(cv, '伯克希尔 2011 年股东大会下午场（CNBC 巴菲特档案逐字稿）', a, y=1462)
    # h3：芒格 1997–2023 任 Costco 董事
    t0, t1 = win('h3')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        pic(cv, ['costco_ext', 'costco_ext2'], t, t0, t1, fb=['w_ext'], fbcap='Costco 仓库（WBZ 1991）', cy=560, h=562, a=a, cap='Costco 仓库')
        y = 1110; xa, xb = 170, 910
        k = eexp((t - WT('h3', '一九九七') + 0.1) / 1.6)
        cv.line((xa, y), (xa + (xb - xa) * k, y), GOLD, a, 4)
        cv.text('1997', xa, y + 52, 34, 'oswald', col=GOLD_L, a=a * min(1, k * 4))
        k2 = eo((t - WT('h3', '二零二三') + 0.1) / 0.5)
        cv.text('2023', xb, y + 52, 34, 'oswald', col=GOLD_L, a=a * k2)
        for x, kk in ((xa, min(1, k * 4)), (xb, k2)): cv.glow_dot((x, y), 10, GOLD_L, a * kk)
        cv.text('查理·芒格 · Costco 董事', W / 2, y - 70, 40, 'serif_semi', col=CREAM, a=a * min(1, k * 3))
        cv.text(counter(0, 26, t, WT('h3', '一九九七'), 1.6, lambda v: f'近 {v:.0f} 年'), W / 2, y + 120, 46, 'sans_bold', col=GOLD_L, a=a * min(1, k * 3))
        source(cv, '芒格 1997 年起任 Costco 董事（Barchart、Morningstar 等报道）；伯克希尔 2023 年信：2023-11-28 去世', a, y=1462)
    # h4：喜诗 vs Costco：相反的两条路 → 商品毛利率 11.09%
    t0, t1 = win('h4')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['a_floor', 'a_aisle', 'a_cans'], h=562, a=a, cap='Costco 卖场（ABC 2005）')
        kc = eo((t - t0 - 0.2) / 0.5) * (1 - eo((t - WT('h4', '二零二六') + 0.4) / 0.4))
        if kc > 0:
            for j, (hd, sub, col, up) in enumerate((('喜诗糖果', '顾客愿意多付钱', GOLD_L, True), ('Costco', '刻意少赚顾客的钱', BLUE_L, False))):
                kk = kc * eo((t - (t0 if j == 0 else WT('h4', '相反的路')) + 0.1) / 0.5)
                if kk <= 0: continue
                x = 300 + j * 480
                cv.text(hd, x, 1010, 52, 'serif_black', col=col, a=a * kk)
                cv.text(sub, x, 1090, 30, 'sans_med', col=CREAM, a=a * kk)
                yy = 1230 + (-1 if up else 1) * 30 * math.sin(t * 2.2)
                cv.text('价格 ↑' if up else '毛利 ↓', x, yy, 54, 'sans_bold', col=col, a=a * kk)
        km = eo((t - WT('h4', '二零二六') + 0.1) / 0.5)
        if km > 0:
            big_num(cv, t, WT('h4', '百分之十一'), '11.09%', 1130, 170, a)
            cv.text('商品毛利率 · 2026 财年', W / 2, 1260, 32, 'sans_med', col=CREAM, a=a * km)
        source(cv, 'Costco 2026 财年 10-K（截至 2026-08-30）：gross margin percentage 11.09%', a, y=1462)
    # h5：净利润 92 亿 → 两个问题
    t0, t1 = S('h5') - 0.3, CH['title'][0] + 0.1
    a = env(t, t0, t1, 0.4, 0.2)
    if a > 0:
        seq(cv, t, t0, t1 - 0.2, ['a_crowd', 'a_entrance'], h=562, a=a, cap='Costco 新店开业（ABC 2005）')
        kq = eo((t - WT('h5', '少赚') + 0.3) / 0.4)
        big_num(cv, t, WT('h5', '九十二亿'), '$92 亿', 1080, 150, a * (1 - kq), sub='2026 财年净利润')
        big_q(cv, t, '少赚，为什么反而赚得多？', 1180, WT('h5', '少赚'), 56, a)
        big_q(cv, t, '好公司，一定是好投资吗？', 1300, WT('h5', '一家芒格'), 46, a, col=CREAM)
        source(cv, 'Costco 2026 财年 10-K：net income attributable to Costco $9,226M', a * (1 - kq), y=1462)


def shot_title(cv, t):
    t0, t1 = CH['title'][0], CH['ch1'][0] + 0.6
    a = env(t, t0, t1, 0.02, 0.6)
    if a <= 0: return
    p = t - t0
    flash = math.exp(-p * 5.0)
    hotdog(cv, W / 2 - 60, 720, 1.25, a * eo(p / 0.35), t)
    price_tag(cv, W / 2 + 250, 560, 0.7, a * eo((p - 0.25) / 0.4), '$1.50', rot=-0.12)
    R = 60 + p * 900
    cv.circle((W / 2, 720), R, GOLD, a * math.exp(-p * 2.2) * 0.8, 3)
    cv.glow_dot((W / 2, 720), 220, GOLD, a * flash * 0.9)
    k = eo((p - 0.15) / 0.6)
    cv.text('一块五的热狗', W / 2, 1100, 120, 'serif_black', gold=True, a=a * k, glow=0.3, scale=1.08 - 0.08 * k)
    cv.text('芒格为什么最爱 Costco', W / 2, 1250, 60, 'serif_semi', col=CREAM, a=a * eo((p - 0.5) / 0.6))
    cv.text('THE $1.50 HOT DOG', W / 2, 1350, 26, 'corm', col=GOLD, a=a * eo((p - 1.0) / 0.6), track=0.35)


# ======================================================================== 第一章：一块五的热狗
def shot_ch1(cv, t):
    # c1a：热狗套餐 1.5 美元，1985 年至今
    t0, t1 = win('c1a', pre=0.1)
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        pic(cv, ['hotdog1', 'hotdog2', 'foodcourt'], t, t0, t1, fb=['a_open', 'a_crowd'], fbcap='Costco 卖场（ABC 2005）', cy=560, h=562, a=a, cap='Costco 美食区的热狗套餐')
        k = eo((t - WT('c1a', '一根热狗') + 0.1) / 0.5)
        if k > 0: hotdog(cv, 360, 1150, 0.7, a * k, t)
        price_tag(cv, 800, 1110, 0.95, a * eo((t - WT('c1a', '一块五') + 0.1) / 0.45), '$1.50', '热狗 + 续杯汽水', rot=-0.06)
        kd = eo((t - WT('c1a', '一九八五') + 0.1) / 0.5)
        if kd > 0:
            cv.text('1985', 610, 1300, 40, 'oswald', col=GOLD_L, a=a * kd)
            arrow(cv, (680, 1300), (880, 1300), a * kd, GOLD, 3, 14, eo((t - WT('c1a', '一九八五')) / 0.8))
            cv.text('今天', 930, 1300, 36, 'sans_bold', col=GOLD_L, a=a * eo((t - WT('c1a', '到今天')) / 0.4))
        source(cv, 'NPR 2024-06-03；Fox Business（since 1985）；Motley Fool（维基百科记 1984 年推出）', a, y=1462)
    # c1b：40 年物价 ~3 倍 vs 热狗 1.5 美元
    t0, t1 = win('c1b')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('物价 vs 热狗套餐 · 1985 → 2025', W / 2, 360, 36, 'sans_med', col=CREAM, a=a)
        x0, x1, base, top = 160, 920, 1150, 560
        grid_lines(cv, x0, x1, base, top, a * 0.8)
        kk = eexp((t - t0 - 0.2) / 2.2)
        cpi = [107.6 * (326.0 / 107.6) ** (j / 40) for j in range(41)]       # 1985 → 2025 年末，按几何平均示意
        pts = [(x0 + (x1 - x0) * j / 40, base - (base - top) * (cpi[j] / 107.6 - 1) / 2.2) for j in range(int(1 + 40 * kk))]
        if len(pts) > 1: cv.poly(pts, COST_R, a, 5)
        if pts: cv.glow_dot(pts[-1], 12, COST_R, a)
        cv.line((x0, base), (x0 + (x1 - x0) * kk, base), GOLD_L, a, 6)
        cv.text('物价', pts[-1][0] - 20 if pts else x0, (pts[-1][1] - 50) if pts else base, 34, 'sans_bold', col=COST_R, a=a * min(1, kk * 3))
        cv.text('$1.50 热狗套餐', x0 + 20, base - 40, 32, 'sans_bold', col=GOLD_L, a=a * min(1, kk * 3), anchor='l')
        for j, yr in enumerate(('1985', '2005', '2025')):
            cv.text(yr, x0 + (x1 - x0) * j / 2, base + 46, 26, 'oswald', col=GREY, a=a)
        k3 = eo((t - WT('c1b', '三倍') + 0.1) / 0.5)
        if k3 > 0: cv.text('≈ 3 倍', 760, top + 20, 64, 'sans_bold', col=COST_R, a=a * k3, glow=0.15)
        note(cv, '示意：物价按美国劳工统计局 CPI-U（1985 年均 107.6 → 2025 年 12 月 326.0）', 1250, a * 0.85, 22)
        source(cv, 'BLS CPI-U（1982–84 = 100）', a, y=1462)
    # c1c：辛内格尔：“你要是敢给热狗涨价，我就宰了你”
    t0, t1 = win('c1c')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['a_greet', 'a_shelf', 'a_walk'], h=562, a=a, cap='辛内格尔巡店（ABC 2005）')
        kc = eo((t - t0 - 0.2) / 0.5) * (1 - eo((t - WT('c1c', '你要是敢') + 0.4) / 0.4))
        if kc > 0:
            node(cv, 290, 1020, '耶利内克', a * kc, col=CREAM, size=34, sub='时任 CEO（2018 年回忆）')
            node(cv, 790, 1020, '辛内格尔', a * kc * eo((t - WT('c1c', '创始人') + 0.1) / 0.4), col=GOLD, size=34, sub='Costco 联合创始人')
            kb = eo((t - WT('c1c', '一块五') + 0.1) / 0.4)
            if kb > 0:
                cv.rrect(150, 1170, 640, 1270, 22, (0.12, 0.10, 0.09), a * kc * kb)
                cv.text('“一块五卖下去要亏钱……”', 395, 1220, 32, 'sans_med', col=CREAM, a=a * kc * kb)
        qcard(cv, 'qhotdog', t, WT('c1c', '你要是敢') - 0.3, t1, cy=1150, en=34, cn=40, a=a, typing=1.0)
        source(cv, 'Craig Jelinek 2018 年演讲中的回忆（Yahoo/AOL、MediaPost、Snopes 等转述）', a, y=1462)
    # c1d：自己建厂做热狗
    t0, t1 = win('c1d')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        pic(cv, ['hotdog3', 'hotdog2', 'foodcourt2', 'foodcourt'], t, t0, t1, fb=['a_meat'], cy=560, h=562, a=a)
        k1 = eo((t - WT('c1d', '原来的供应商') + 0.1) / 0.5)
        node(cv, 270, 1080, '供应商涨价', a * k1, col=COST_R, size=34)
        k2 = eo((t - WT('c1d', '干脆') + 0.1) / 0.5)
        arrow(cv, (430, 1080), (600, 1080), a * k2, GOLD, 4, 18, k2)
        factory(cv, 800, 1090, 0.9, a * k2)
        cv.text('自己建厂做热狗', 800, 1230, 34, 'sans_bold', col=GOLD_L, a=a * k2)
        note(cv, '工厂为示意', 1320, a * k2 * 0.8, 22)
        source(cv, 'Chowhound、Food Republic、247wallst：2008–2009 年前后改为自产热狗（先加州，后芝加哥一带）', a, y=1462)
    # c1e：4.99 美元烤鸡 → 内布拉斯加：饲料厂、孵化场、加工厂，4.5 亿美元
    t0, t1 = win('c1e')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        tsw = WT('c1e', '为了守住')
        pic(cv, ['chicken_oven', 'chicken_pack'], t, t0, tsw + 0.3, fb=['a_chicken'], fbcap='Costco 的烤鸡（ABC 2005）', cy=560, h=562, a=a, cap='Costco 的烤鸡')
        seq(cv, t, tsw - 0.1, t1, ['a_meat', 'a_bake2'], h=562, a=a, cap='Costco 肉品区与烘焙（ABC 2005）')
        price_tag(cv, W / 2, 1010, 0.7, a * eo((t - WT('c1e', '四块九') + 0.1) / 0.45), '$4.99', '一只烤鸡', col=COST_R)
        steps = [('饲料厂', WT('c1e', '饲料厂')), ('孵化场', WT('c1e', '孵化场')), ('加工厂', WT('c1e', '加工厂'))]
        for j, (nm, ts) in enumerate(steps):
            k = eo((t - ts + 0.1) / 0.4)
            if k <= 0: continue
            x = 220 + j * 320
            node(cv, x, 1180, nm, a * k, col=GOLD, size=34, w=230)
            if j: arrow(cv, (x - 200, 1180), (x - 125, 1180), a * k, GOLD_D, 3, 14, k)
        km = eo((t - WT('c1e', '四点五亿') + 0.1) / 0.45)
        if km > 0:
            cv.text('总投资超过 $4.5 亿 · 内布拉斯加州，2019 年投产', W / 2, 1300, 32, 'sans_bold', col=GOLD_L, a=a * km)
        source(cv, 'NPR 2018-10-22；弗里蒙特市长：“over $450 million has been invested in the feed mill, the hatchery and the processing plant”', a, y=1462)
    # c1f：两只价格的锚
    t0, t1 = win('c1f')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        pic(cv, ['foodcourt', 'hotdog3', 'chicken_pack'], t, t0, t1, fb=['a_crowd'], cy=560, h=562, a=a)
        k0 = eo((t - t0 - 0.2) / 0.5) * (1 - eo((t - WT('c1f', '它们更像') + 0.4) / 0.4))
        if k0 > 0:
            cv.text('不等于什么都不涨价', W / 2, 1070, 38, 'sans_med', col=CREAM, a=a * k0)
            cv.text('也不说明一直在亏钱', W / 2, 1150, 38, 'sans_med', col=CREAM, a=a * k0 * eo((t - WT('c1f', '热狗和烤鸡') + 0.1) / 0.4))
        ka = eo((t - WT('c1f', '锚') + 0.1) / 0.5)
        if ka > 0:
            for j, (nm, px) in enumerate((('$1.50 热狗', 300), ('$4.99 烤鸡', 780))):
                anchor_icon(cv, px, 1050, 0.9, a * ka, GOLD)
                cv.text(nm, px, 1160, 34, 'sans_bold', col=GOLD_L, a=a * ka)
            for j, (s_, w_) in enumerate((('记得住', '记得住'), ('随时能比', '随时能比'), ('不趁机涨价', '这里没有'))):
                kk = eo((t - WT('c1f', w_) + 0.1) / 0.4)
                chip(cv, s_, 220 + j * 320, 1280, 30, a * kk, col=GOLD)
        source(cv, '本片解读', a * 0.8, y=1462)
    # c1g：这个习惯从哪来？
    t0, t1 = S('c1g') - 0.3, CH['tk_ch1'][0] + 0.3
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['a_aisle', 'a_lot'], h=562, a=a, cap='Costco 卖场（ABC 2005）')
        cv.text('成本涨了 →', W / 2, 1030, 40, 'sans_med', col=CREAM, a=a * eo((t - t0 - 0.2) / 0.4))
        cv.text('先降成本，不先涨价', W / 2, 1120, 50, 'serif_black', gold=True, a=a * eo((t - WT('c1g', '先逼') + 0.1) / 0.4))
        big_q(cv, t, '这个习惯，是从哪来的？', 1280, WT('c1g', '这个习惯'), 52, a, col=CREAM)


# ======================================================================== 第二章：飞机库里的师徒
def shot_ch2(cv, t):
    # c2a：1954 圣地亚哥 FedMart
    t0, t1 = win('c2a')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        tf = WT('c2a', '叫 FedMart')
        seq(cv, t, t0, tf + 0.2, ['sol66_cu'], h=562, a=a, cap='索尔·普莱斯（1966 年电视采访）')
        seq(cv, t, tf - 0.2, t1, ['fm_front', 'fm_ext'], h=562, a=a, cap='FedMart 门店（1982）')
        tag(cv, '1954 · 加州圣地亚哥', t, WT('c2a', '一九五四'), W / 2, 950, 32, GOLD, a)
        k = eo((t - WT('c2a', '索尔') + 0.1) / 0.45)
        cv.text('索尔·普莱斯', W / 2, 1060, 54, 'serif_black', col=CREAM, a=a * k)
        kf = eo((t - tf + 0.1) / 0.45)
        cv.text('创办 FedMart 折扣店', W / 2, 1150, 40, 'sans_bold', col=GOLD_L, a=a * kf)
        chip(cv, '只对政府雇员开放', 340, 1270, 30, a * eo((t - WT('c2a', '政府雇员') + 0.1) / 0.4), col=GOLD)
        chip(cv, '会费 $2', 780, 1270, 30, a * eo((t - WT('c2a', '会费') + 0.1) / 0.4), col=GOLD)
        source(cv, '维基百科 FedMart；Rational Walk《The Story of FedMart》；Supermarket News 名人堂', a, y=1462)
    # c2b：十几岁的辛内格尔，从卸床垫干起
    t0, t1 = win('c2b')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        pic(cv, ['sinegal'], t, t0, t1, fb=['a_hall'], fbcap='辛内格尔在总部（ABC 2005）', cy=560, h=562, a=a, cap='吉姆·辛内格尔')
        k = eo((t - WT('c2b', '卸床垫') + 0.1) / 0.5)
        for j in range(4):
            kk = eo((t - WT('c2b', '卸床垫') - j * 0.18) / 0.4)
            if kk <= 0: continue
            x = 250 + j * 60; y = 1170 - j * 34 - 30 * (1 - kk)
            cv.rrect(x - 110, y - 22, x + 110, y + 22, 10, C(225, 220, 205), a * kk)
            cv.line((x - 96, y), (x + 96, y), C(180, 170, 150), a * kk * 0.8, 2)
        cv.text('从卸床垫干起', 330, 1260, 36, 'sans_bold', col=GOLD_L, a=a * k)
        kn = eo((t - WT('c2b', '吉姆') + 0.1) / 0.45)
        cv.text('吉姆·辛内格尔', 760, 1110, 50, 'serif_black', gold=True, a=a * kn)
        cv.text('在普莱斯手下学会做零售', 760, 1190, 30, 'sans_med', col=CREAM, a=a * eo((t - WT('c2b', '普莱斯手下') + 0.1) / 0.45))
        source(cv, 'ABC《20/20》2005：“began in the warehouse business by loading mattresses”；维基百科 Jim Sinegal', a, y=1462)
    # c2c：雨果·曼买下 FedMart，普莱斯被挤出
    t0, t1 = win('c2c')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['sol_int1'], h=562, a=a, cap='索尔·普莱斯（CBS 8，1982）')
        tag(cv, '1970 年代中期', t, WT('c2c', '一九七零'), W / 2, 950, 30, GOLD, a)
        node(cv, W / 2, 1100, 'FedMart', a * eo((t - t0 - 0.2) / 0.4), col=CREAM, size=40, w=320)
        k1 = eo((t - WT('c2c', '雨果') + 0.1) / 0.45)
        if k1 > 0:
            node(cv, 200, 1100, '雨果·曼', a * k1, col=COST_R, size=34, sub='德国商人')
            arrow(cv, (300, 1100), (W / 2 - 170, 1100), a * k1, COST_R, 4, 18, k1)
        k2 = eo((t - WT('c2c', '挤出') + 0.1) / 0.5)
        if k2 > 0:
            node(cv, 860 + 40 * k2, 1250, '普莱斯', a * k2, col=GOLD, size=34)
            arrow(cv, (W / 2 + 60, 1150), (790, 1230), a * k2, GOLD_D, 3, 14, k2)
            cv.text('被挤出自己创办的公司', 860, 1330, 26, 'sans_light', col=CREAM, a=a * k2)
        source(cv, 'CBS 8 1982-04-29 报道；encyclopedia.com（1976 年失去领导权）', a, y=1462)
    # c2d：1976 飞机库里的 Price Club
    t0, t1 = win('c2d')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['pc_int1', 'pc_int3', 'sol_int2'], h=562, a=a, cap='Price Club 与普莱斯（CBS 8，1982）')
        k = eo((t - WT('c2d', '飞机库') + 0.1) / 0.6)
        hangar(cv, 300, 1130, 0.75, a * k, t)
        cv.text('1976 · Price Club', 300, 1300, 34, 'sans_bold', col=GOLD_L, a=a * eo((t - WT('c2d', '第一家') + 0.1) / 0.4))
        for j, (s_, w_) in enumerate((('不装修', '不装修'), ('品种少', '品种少'), ('整箱卖', '整箱卖'), ('会员制', '只对交了'))):
            kk = eo((t - WT('c2d', w_) + 0.1) / 0.4)
            chip(cv, s_, 780, 1010 + j * 92, 32, a * kk, col=GOLD)
        note(cv, '飞机库为示意', 1390, a * k * 0.7, 20)
        source(cv, 'San Diego Jewish World；Supermarket News（former aircraft hangar）；维基百科 Price Club（1976-07-12）', a, y=1462)
    # c2e：1982 FedMart 关门，对面 Price Club 生意兴旺
    t0, t1 = win('c2e')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        ts_ = WT('c2e', '马路对面')
        seq(cv, t, t0, ts_ + 0.2, ['fm_check', 'fm_bag'], h=562, a=a, cap='FedMart 最后的日子（CBS 8，1982）')
        seq(cv, t, ts_ - 0.2, t1, ['pc_int2', 'sol_int3'], h=562, a=a, cap='马路对面的 Price Club（CBS 8，1982）')
        tag(cv, '1982 · 圣地亚哥', t, t0 + 0.3, W / 2, 950, 30, GOLD, a)
        k1 = eo((t - WT('c2e', '关门') + 0.1) / 0.45)
        node(cv, 290, 1130, 'FedMart', a * k1, col=COST_R, size=40, sub='关门清仓', w=380)
        k2 = eo((t - ts_ + 0.1) / 0.45)
        node(cv, 790, 1130, 'Price Club', a * k2, col=GOLD, size=40, sub='生意正旺', w=380)
        if k2 > 0: cv.text('⇄  马路对面', W / 2, 1290, 30, 'sans_med', col=CREAM, a=a * k2)
        source(cv, 'CBS 8（KFMB News 8）1982-04-29：“across the street… stores opened by FedMart’s own founder are quietly booming”', a, y=1462)
    # c2f：1983 西雅图第一家 Costco
    t0, t1 = win('c2f')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['w_ext', 'a_sign'], h=562, a=a, cap='Costco 仓库（1991 / 2005 档案画面）')
        tag(cv, '1983 · 西雅图', t, WT('c2f', '一九八三'), W / 2, 950, 32, GOLD, a)
        k = eo((t - WT('c2f', '辛内格尔') + 0.1) / 0.45)
        cv.text('辛内格尔  +  布罗特曼', W / 2, 1070, 46, 'serif_black', col=CREAM, a=a * k)
        kc = eo((t - WT('c2f', '第一家 Costco') + 0.1) / 0.45)
        cv.text('第一家 Costco', W / 2, 1160, 54, 'serif_black', gold=True, a=a * kc)
        kp = eo((t - WT('c2f', '照着') + 0.1) / 0.45)
        if kp > 0:
            node(cv, 330, 1290, 'Price Club', a * kp, col=CREAM, size=30, w=260)
            arrow(cv, (480, 1290), (600, 1290), a * kp, GOLD, 3, 14, kp)
            cv.text('复制', 540, 1250, 24, 'sans_med', col=GOLD_L, a=a * kp)
            node(cv, 750, 1290, 'Costco', a * kp, col=GOLD, size=30, w=260)
        source(cv, '维基百科 Costco：1983-09-15 西雅图开业；两人对 CNN 说，计划就是“clone Price Club”', a, y=1462)
    # c2g：同一年，山姆会员店；沃尔顿：“借”来的点子
    t0, t1 = win('c2g')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        if not pic(cv, ['sams_us', 'sams_int'], t, t0, t1, cy=560, h=562, a=a, cap='山姆会员店（美国）'):
            kk = eo((t - t0) / 0.5)
            cv.text('山姆会员店', W / 2, 520, 110, 'serif_black', col=BLUE_L, a=a * kk, glow=0.15)
            cv.text('1983 · 俄克拉何马州', W / 2, 640, 34, 'sans_med', col=CREAM, a=a * kk)
        k = eo((t - WT('c2g', '山姆沃尔顿') + 0.1) / 0.45) * (1 - eo((t - WT('c2g', '他在自传') + 0.3) / 0.4))
        if k > 0:
            cv.text('1983 · 山姆会员店', W / 2, 1060, 46, 'serif_black', col=CREAM, a=a * k)
            cv.text('沃尔玛创始人 山姆·沃尔顿', W / 2, 1150, 34, 'sans_med', col=GOLD_L, a=a * k)
        qcard(cv, 'qborrow', t, WT('c2g', '他在自传') - 0.2, t1, cy=1150, en=30, cn=36, a=a, typing=1.4)
        source(cv, 'Sam Walton《Made in America》（1992）', a, y=1462)
    # c2h + c2i：师徒谱系图 → 省下来的钱归谁？
    t0, t1 = S('c2h') - 0.3, CH['tk_ch2'][0] + 0.3
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('仓储会员店的一张家谱', W / 2, 360, 40, 'serif_semi', col=CREAM, a=a)
        ks = lambda d: eo((t - t0 - d) / 0.5)
        node(cv, W / 2, 500, '索尔·普莱斯', a * ks(0.1), col=GOLD, size=36)
        node(cv, 220, 680, 'FedMart', a * ks(0.3), col=CREAM, size=30, sub='1954')
        node(cv, 520, 680, 'Price Club', a * ks(0.5), col=GOLD, size=30, sub='1976')
        node(cv, 840, 680, '山姆会员店', a * ks(0.7), col=CREAM, size=30, sub='1983 · 沃尔顿“借”来')
        node(cv, 520, 900, 'Costco', a * ks(0.9), col=BLUE_L, size=32, sub='1983 · 辛内格尔')
        for p0, p1, d in (((W / 2, 545), (220, 640), 0.3), ((W / 2, 545), (520, 640), 0.5), ((W / 2, 545), (840, 640), 0.7), ((520, 735), (520, 855), 0.9)):
            arrow(cv, p0, p1, a * ks(d), GOLD_D, 2, 12, ks(d))
        km = eo((t - WT('c2h', '合并') + 0.1) / 0.6)
        if km > 0:
            node(cv, 520, 1090, 'PriceCostco', a * km, col=GOLD, size=36, sub='1993 · 徒弟和师傅合并')
            arrow(cv, (520, 950), (520, 1035), a * km, GOLD, 3, 14, km)
        kq = eo((t - WT('c2i', '会员卡') + 0.1) / 0.45)
        if kq > 0:
            for j, s_ in enumerate(('会员卡', '大仓库', '整箱卖')):
                chip(cv, s_ + ' ✓ 容易学', 200 + j * 340, 1240, 26, a * kq * eo((t - WT('c2i', '会员卡') - j * 0.25) / 0.4), col=GREY)
        big_q(cv, t, '省下来的钱，归谁？', 1360, WT('c2i', '省下来的钱'), 58, a)
        source(cv, '维基百科 Costco、Price Club；encyclopedia.com（PriceCostco，1993）', a * (1 - kq), y=1462)


# ======================================================================== 第三章：省下的钱归谁
def shot_ch3(cv, t):
    # c3a：超市三万种 vs Costco 四千种
    t0, t1 = win('c3a')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['a_floor', 'a_cans'], h=480, cy=520, a=a, cap='Costco 卖场（ABC 2005）')
        k1 = eo((t - WT('c3a', '普通超市') + 0.1) / 0.4)
        k2 = eo((t - WT('c3a', '一家 Costco') + 0.1) / 0.4)
        for side, (n, x0, col, kk, lb) in enumerate(((300, 110, GREY, k1, '普通超市 · 约 30,000 种'), (40, 640, GOLD_L, k2, 'Costco · 约 4,000 种'))):
            if kk <= 0: continue
            cols_ = 20 if side == 0 else 8
            for j in range(n):
                r, c = divmod(j, cols_)
                e = eo((t - (WT('c3a', '普通超市') if side == 0 else WT('c3a', '一家 Costco')) - j * 0.004) / 0.3)
                if e <= 0: continue
                cv.rect(x0 + c * 17, 880 + r * 17, x0 + c * 17 + 13, 880 + r * 17 + 13, col * (0.7 if side == 0 else 1.0), a * e)
            cv.text(lb, x0 + (cols_ * 17) / 2, 1180, 30, 'sans_bold', col=col, a=a * kk)
        note(cv, '每个小方块 = 100 种商品', 1260, a * k2 * 0.85, 22)
        source(cv, 'Costco 官网公司介绍：“about 4,000 SKUs … compared to the 30,000 found at most supermarkets”', a, y=1462)
    # c3b：品种少 → 每种卖得多 → 订单大 → 进价低
    t0, t1 = win('c3b')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['a_fork', 'w_stock', 'a_cans'], h=562, a=a, cap='整托盘上架（ABC 2005 / WBZ 1991）')
        steps = [('品种少', '品种少了'), ('每种卖得多', '每一种'), ('订单更大', '订单越大'), ('进价更低', '进价'), ('运输上架更省', '运输')]
        for j, (s_, w_) in enumerate(steps):
            k = eo((t - WT('c3b', w_) + 0.1) / 0.4)
            if k <= 0: continue
            y = 950 + j * 92
            node(cv, W / 2, y + 10 * (1 - k), s_, a * k, col=GOLD if j >= 3 else CREAM, size=32, w=420)
            if j: arrow(cv, (W / 2, y - 62), (W / 2, y - 34), a * k, GOLD_D, 2, 10, k)
        source(cv, '本片解读', a * 0.8, y=1462)
    # c3c：引出芒格原声（2022 年每日期刊股东会）
    t0, t1 = pre_sot('c3c', 'titan')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        seq(cv, t, t0, t1, ['m_dj2'], h=562, a=a, cap='芒格（2022 年《每日期刊》股东会）')
        tag(cv, '2022 · 《每日期刊》股东会', t, t0 + 0.2, W / 2, 960, 30, GOLD, a)
        cv.text('芒格怎么看 Costco 的“少而精”', W / 2, 1100, 44, 'serif_semi', col=CREAM, a=a * eo((t - t0 - 0.4) / 0.5))
    # c3d：加价上限 14% / 15%
    t0, t1 = win('c3d')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        pic(cv, ['kirkland', 'costco_books', 'costco_int'], t, t0, t1, fb=['a_wine'], cy=560, h=562, a=a)
        cv.text('加价上限', W / 2, 960, 44, 'serif_black', col=CREAM, a=a * eo((t - WT('c3d', '加价的上限') + 0.1) / 0.4))
        price_tag(cv, 300, 1130, 0.85, a * eo((t - WT('c3d', '名牌商品') + 0.1) / 0.45), '≤14%', '名牌商品', col=GOLD_D)
        price_tag(cv, 780, 1130, 0.85, a * eo((t - WT('c3d', '科克兰') + 0.1) / 0.45), '≤15%', '自有品牌科克兰', col=GOLD_D)
        note(cv, '据多家媒体报道；Costco 没有正式披露这条规则', 1290, a * eo((t - WT('c3d', '据多家') + 0.1) / 0.4), 24)
        source(cv, 'Supermarket News、Mashed、Moneywise、RetailWire（转述《华尔街日报》）', a, y=1462)
    # c3e：加价率 ≠ 毛利率；100 → 114 → 12.3%；实际 11.09%
    t0, t1 = win('c3e')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('加价率 ≠ 毛利率', W / 2, 380, 56, 'serif_black', gold=True, a=a * eo((t - t0 - 0.1) / 0.45))
        x0, base = 240, 1000; sc = 4.2
        k1 = eexp((t - WT('c3e', '进价一百') + 0.1) / 0.8)
        if k1 > 0:
            gbar(cv, x0 - 90, base - 100 * sc * k1, x0 + 90, base, GREY, a, sheen_t=t)
            cv.text('进价 $100', x0, base + 44, 30, 'sans_med', col=CREAM, a=a * min(1, k1 * 2))
        k2 = eexp((t - WT('c3e', '一百一十四') + 0.1) / 0.8)
        if k2 > 0:
            gbar(cv, 600 - 90, base - 100 * sc, 600 + 90, base, GREY * 0.9, a, sheen_t=t)
            gbar(cv, 600 - 90, base - (100 + 14 * k2) * sc, 600 + 90, base - 100 * sc, GOLD, a, sheen_t=t)
            cv.text('售价 $114', 600, base + 44, 30, 'sans_med', col=CREAM, a=a * min(1, k2 * 2))
            cv.text('+$14', 600 + 130, base - 107 * sc, 34, 'sans_bold', col=GOLD_L, a=a * min(1, k2 * 2), anchor='l')
            cv.text('加价 14% = 14 ÷ 100', 860, 600, 26, 'sans_light', col=GREY, a=a * min(1, k2 * 2))
        k3 = eo((t - WT('c3e', '毛利率约') + 0.1) / 0.5)
        if k3 > 0:
            cv.text('毛利率 = 14 ÷ 114 ≈ 12.3%', W / 2, 1150, 46, 'sans_bold', col=GOLD_L, a=a * k3)
        k4 = eo((t - WT('c3e', '二零二六') + 0.1) / 0.5)
        if k4 > 0:
            cv.text('2026 财年实际商品毛利率', W / 2, 1260, 30, 'sans_med', col=CREAM, a=a * k4)
            cv.text('11.09%', W / 2, 1340, 64, 'sans_bold', gold=True, a=a * k4, glow=0.2)
        source(cv, '14 ÷ 114 = 12.28%；Costco 2026 财年 10-K（gross margin percentage 11.09%）', a, y=1462)
    # c3f：芒格的织布机故事
    t0, t1 = win('c3f')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        tag(cv, '芒格讲过的反例', t, t0 + 0.2, W / 2, 360, 32, GOLD, a)
        k1 = eo((t - WT('c3f', '纺织厂') + 0.1) / 0.5)
        if k1 > 0:
            factory(cv, 260, 620, 1.0, a * k1, GOLD)
            cv.text('伯克希尔早年的纺织厂', 260, 760, 28, 'sans_med', col=CREAM, a=a * k1)
        k2 = eo((t - WT('c3f', '新织布机') + 0.1) / 0.5)
        if k2 > 0:
            node(cv, 780, 600, '新织布机', a * k2, col=GOLD, size=36, sub='效率翻一倍')
        k3 = eo((t - WT('c3f', '省下的成本') + 0.1) / 0.5)
        if k3 > 0:
            arrow(cv, (420, 860), (700, 860), a * k3, GOLD_D, 4, 18, k3)
            cv.text('省下的成本', 560, 820, 28, 'sans_med', col=GOLD_L, a=a * k3)
            node(cv, 830, 860, '买布的人', a * k3 * eo((t - WT('c3f', '买布的人') + 0.1) / 0.4), col=CREAM, size=34)
            for j in range(5):
                ph = (t * 0.6 + j / 5) % 1.0
                cv.text('$', 440 + ph * 260, 900 + 8 * math.sin(ph * 6), 28, 'sans_bold', col=GOLD_L, a=a * k3 * math.sin(ph * math.pi))
        qcard(cv, 'qloom', t, WT('c3f', '巴菲特却') - 0.2, t1, cy=1180, en=32, cn=38, a=a, typing=1.2)
        source(cv, '芒格 1994 年南加大商学院演讲《A Lesson on Elementary, Worldly Wisdom》', a, y=1462)
    # c3g：被逼让 vs 主动让
    t0, t1 = win('c3g')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['a_cans', 'a_wine'], h=480, cy=520, a=a, cap='Costco 卖场（ABC 2005）')
        k1 = eo((t - WT('c3g', '纺织厂') + 0.1) / 0.45)
        node(cv, 290, 960, '纺织厂', a * k1, col=GREY, size=36, sub='被竞争逼着让出去', w=400)
        k2 = eo((t - WT('c3g', 'Costco') + 0.1) / 0.45)
        node(cv, 790, 960, 'Costco', a * k2, col=GOLD, size=36, sub='自己主动让出去', w=400)
        k3 = eo((t - WT('c3g', '进价降了') + 0.1) / 0.5)
        if k3 > 0:
            for j, (lb, col, w_) in enumerate((('进价', GREY, '进价降了'), ('售价', GOLD_L, '售价'))):
                kk = eo((t - WT('c3g', w_)) / 0.9)
                x = 640 + j * 260
                h1 = 220 - 70 * kk
                gbar(cv, x - 60, 1360 - h1, x + 60, 1360, col, a * k3, sheen_t=t)
                cv.text(lb + ' ↓', x, 1360 - h1 - 34, 30, 'sans_bold', col=col, a=a * k3)
            cv.text('一起降', 520, 1250, 34, 'sans_bold', col=GOLD_L, a=a * k3, anchor='r')
        source(cv, '本片解读', a * 0.8, y=1462)
    # c3h：规模经济共享（飞轮）
    t0, t1 = win('c3h')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('规模经济共享', W / 2, 360, 60, 'serif_black', gold=True, a=a * eo((t - WT('c3h', '规模经济共享') + 0.1) / 0.45), glow=0.2)
        cv.text('Scale Economies Shared · 尼克·斯利普', W / 2, 440, 26, 'corm', col=GOLD, a=a * eo((t - WT('c3h', '尼克') + 0.1) / 0.45), track=0.1)
        labels = ['规模更大', '成本更低', '让利顾客', '顾客更多']
        anchors = ['规模越大', '成本越低', '让给顾客', '顾客越多']
        ks = [eo((t - WT('c3h', w_) + 0.1) / 0.45) for w_ in anchors]
        ring_cycle(cv, t, W / 2, 900, 300, labels, a, ks, size=34)
        source(cv, 'Nomad Investment Partnership 致合伙人信（Nick Sleep & Qais Zakaria）', a, y=1462)
    # c3i：引出辛内格尔原声
    t0, t1 = pre_sot('c3i', 'sinegal')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        seq(cv, t, t0, t1, ['a_desk', 'a_fax'], h=562, a=a, cap='辛内格尔的办公室（ABC 2005）')
        cv.text('放弃眼前的钱', 300, 1080, 44, 'sans_bold', col=GREY, a=a * eo((t - WT('c3i', '放弃') + 0.1) / 0.4))
        arrow(cv, (480, 1080), (600, 1080), a * eo((t - WT('c3i', '换') + 0.1) / 0.4), GOLD, 3, 14, eo((t - WT('c3i', '换')) / 0.5))
        cv.text('换长远的生意', 790, 1080, 44, 'serif_black', gold=True, a=a * eo((t - WT('c3i', '换') + 0.1) / 0.4))
        tag(cv, '2005 · ABC《20/20》', t, WT('c3i', '二零零五'), W / 2, 1230, 30, GOLD, a)


# ======================================================================== 第四章：利润从哪里来
BR = dict(gm=329.68, sga=271.90, rem=57.78, fee=59.07, op=116.85, ni=92.26)


def shot_ch4(cv, t):
    # c4a：翻开年报
    t0, t1 = win('c4a')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        big_q(cv, t, '全靠会员费赚钱？', 470, t0 + 0.2, 64, a)
        doc_page(cv, t, WT('c4a', '用它') - 0.3, t1, 'COSTCO WHOLESALE CORPORATION · FORM 10-K · FISCAL 2026',
                 ['Net sales ................ $297,247M', 'Membership fees ............ $5,907M', 'Merchandise costs ........ $264,279M',
                  'SG&A ....................... $27,190M', 'Net income ................. $9,226M'], cy=1010, size=30, sub='截至 2026 年 8 月 30 日的 52 周')
        source(cv, 'Costco 2026 财年 10-K（2026-10-07 提交）', a, y=1462)
    # c4b–c4d：利润桥（瀑布图）
    t0, t1 = S('c4b') - 0.3, S('c4e') - 0.2
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('2026 财年 · 利润是怎么来的（亿美元）', W / 2, 340, 36, 'sans_med', col=CREAM, a=a)
        base, top = 1150, 470
        sc = (base - top) / 340.0
        items = [('商品毛利', 0, BR['gm'], GOLD, WT('c4b', '毛利')), ('销售与管理费用', BR['gm'], BR['rem'], COST_R, WT('c4b', '扣掉')),
                 ('卖货结余', 0, BR['rem'], GOLD_L, WT('c4b', '还剩下')), ('会员费', BR['rem'], BR['rem'] + BR['fee'], BLUE_L, WT('c4c', '会员费')),
                 ('营业利润', 0, BR['op'], GOLD, WT('c4c', '营业利润')), ('净利润', 0, BR['ni'], GOLD_L, WT('c4c', '净利润'))]
        xs = [130 + j * 164 for j in range(6)]
        grid_lines(cv, 70, 1010, base, top, a * 0.6)
        txt = {0: '330', 1: '−272', 2: '58', 3: '+59', 4: '≈117', 5: '92'}
        for j, (lb, v0, v1, col, ts) in enumerate(items):
            e = eexp((t - ts + 0.1) / 0.9)
            if e <= 0: continue
            lo, hi = min(v0, v1), max(v0, v1)
            if j == 1: y_top = base - hi * sc; y_bot = y_top + (hi - lo) * sc * e
            else: y_bot = base - lo * sc; y_top = y_bot - (hi - lo) * sc * e
            gbar(cv, xs[j] - 56, y_top, xs[j] + 56, y_bot, col, a, sheen_t=t - ts, reflect=False)
            cv.text(txt[j], xs[j], (y_top - 34) if j != 1 else (y_bot + 34), 38, 'sans_bold', col=col, a=a * min(1, e * 2), shadow=0.6)
            for li, ln in enumerate(wrap_cn(lb, 'sans_light', 24, 140)):
                cv.text(ln, xs[j], base + 40 + li * 30, 24, 'sans_light', col=GREY, a=a * min(1, e * 2))
            if j in (1, 3) and e > 0.99:
                cv.line((xs[j - 1] + 56, base - v0 * sc), (xs[j] - 56, base - v0 * sc), GREY, a * 0.6, 1)
        k5 = eo((t - WT('c4d', '会员费是在') + 0.1) / 0.5)
        if k5 > 0:
            cv.rrect(160, 1240, 920, 1400, 18, (0.07, 0.06, 0.05), a * k5 * 0.9)
            r = 56; cx_, cy_ = 260, 1320
            cv.arc((cx_, cy_), r, -math.pi / 2, 1.5 * math.pi, GOLD_D, a * k5, 16)
            cv.arc((cx_, cy_), r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * 0.506 * k5, BLUE_L, a * k5, 16)
            cv.text('会员费 ≈ 营业利润的一半', 600, 1295, 38, 'sans_bold', col=BLUE_L, a=a * k5)
            cv.text('59 ÷ 117 ≈ 51%；卖货本身毛利付完开销，还有结余', 600, 1355, 24, 'sans_light', col=CREAM, a=a * k5)
        kd = eo((t - WT('c4d', '卖货本身') + 0.1) / 0.5) * (1 - k5)
        if kd > 0: cv.text('卖货本身并不亏', W / 2, 1300, 50, 'serif_black', gold=True, a=a * kd)
        source(cv, 'Costco 2026 财年 10-K：merchandise gross margin $32,968M；SG&A $27,190M；membership fees $5,907M；net income $9,226M（营业利润为本片计算，约 $11.7B）', a, y=1462)
    # c4e：8410 万付费会员；续费率 92.3% / 89.8%
    t0, t1 = win('c4e')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        pic(cv, ['checkout', 'checkout2', 'card'], t, t0, t1, fb=['a_aisle', 'a_lot'], fbcap='Costco 会员（ABC 2005）', cy=520, h=480, a=a, cap='Costco 收银台')
        k = eo((t - WT('c4e', '八千四百') + 0.1) / 0.45)
        if k > 0:
            cv.text(counter(0, 8410, t, WT('c4e', '八千四百'), 1.2, lambda v: f'{v:,.0f} 万'), W / 2, 920, 84, 'sans_bold', gold=True, a=a * k, glow=0.2)
            cv.text('付费会员（2026 财年末）', W / 2, 1000, 28, 'sans_med', col=CREAM, a=a * k)
        g1 = eexp((t - WT('c4e', '美国和加拿大') + 0.1) / 1.2)
        gauge(cv, 330, 1210, 110, 0.923 * g1, a * min(1, g1 * 3), GOLD, '续费率 · 美国和加拿大', size=46)
        g2 = eexp((t - WT('c4e', '全球') + 0.1) / 1.2)
        gauge(cv, 750, 1210, 110, 0.898 * g2, a * min(1, g2 * 3), BLUE_L, '续费率 · 全球', size=46)
        source(cv, 'Costco 2026 财年 10-K：paid members 84.1M；renewal rate 92.3%（U.S. & Canada）/ 89.8%（worldwide）', a, y=1462)
    # c4f：$65 / 年；十个里九个续费
    t0, t1 = win('c4f')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        card(cv, W / 2, 620, 1.3, a * eo((t - t0 - 0.1) / 0.5), '会员卡（示意）', '$65 / YEAR', col=C(190, 200, 215), rot=-0.05)
        tag(cv, '美国普通会员卡 · 2024 年 9 月起 $65 / 年', t, WT('c4f', '六十五'), W / 2, 880, 30, GOLD, a)
        for j in range(10):
            on = j < 9
            kk = eo((t - WT('c4f', '十个会员') - j * 0.07) / 0.35)
            lit = eo((t - WT('c4f', '九个') - j * 0.05) / 0.35) if on else 0
            x = 135 + j * 90
            person(cv, x, 1090, 2.0, a * kk, col=lerp(np.asarray(GREY, np.float32), np.asarray(GOLD_L, np.float32), lit))
        cv.text('10 个会员里，9 个续费', W / 2, 1200, 44, 'sans_bold', col=GOLD_L, a=a * eo((t - WT('c4f', '九个') + 0.1) / 0.45))
        cv.text('算过账：留下来划算', W / 2, 1290, 36, 'serif_semi', col=CREAM, a=a * eo((t - WT('c4f', '算过账') + 0.1) / 0.45))
        source(cv, 'Axios 2024-08-31 等（2024-09-01 起 Gold Star $65）；续费率见 2026 财年 10-K', a, y=1462)
    # c4g：存货 193 亿 < 应付 226 亿
    t0, t1 = win('c4g')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['a_fork', 'a_cans'], h=480, cy=520, a=a, cap='Costco 仓库（ABC 2005）')
        hbar(cv, t, [('存货', 193.24, WT('c4g', '存货'), GOLD * 0.7), ('应付供应商', 225.91, WT('c4g', '欠供应商'), BLUE_L)], a,
             x0=330, x1=880, y0=930, dy=130, fmt=lambda v: f'${v:,.0f} 亿', size=40, lab=32)
        k = eo((t - WT('c4g', '很多货') + 0.1) / 0.5)
        if k > 0: cv.text('很多货，付款前就卖掉了', W / 2, 1250, 46, 'serif_black', gold=True, a=a * k)
        note(cv, '2026 财年末（2026-08-30）资产负债表', 1330, a * 0.8, 22)
        source(cv, 'Costco 2026 财年 10-K：merchandise inventories $19,324M；accounts payable $22,591M（据 stockanalysis 等数据整理）', a, y=1462)
    # c4h：939 家仓库，重资产
    t0, t1 = S('c4h') - 0.3, CH['tk_ch4'][0] + 0.3
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        grid = [('costco_neworleans', '美国'), ('costco_japan', '日本'), ('costco_korea', '韩国'), ('costco_taiwan', '中国台湾'),
                ('costco_uk', '英国'), ('costco_ext2', '美国'), ('costco_ext', '美国'), ('costco_pallets', '美国'), ('costco_books', '美国')]
        have = [g for g in grid if M.have(g[0])][:6]
        if len(have) < 3:                       # 照片不够拼贴：改用档案影像
            have = []
            seq(cv, t, t0, t1, ['w_ext', 'a_sign', 'a_entrance'], h=480, cy=520, a=a, cap='Costco 仓库（WBZ 1991 / ABC 2005）')
        for j, (nm, cp) in enumerate(have):
            r, c = divmod(j, 3)
            mini_photo(cv, nm, t, t0 + 0.15 * j, t1, 200 + c * 340, 480 + r * 270, 310, 200, a, cap=cp)
        k = eo((t - WT('c4h', '九百三十九') + 0.1) / 0.5)
        if k > 0:
            cv.text(counter(0, 939, t, WT('c4h', '九百三十九'), 1.0, lambda v: f'{v:,.0f}'), W / 2, 1060, 150, 'sans_bold', gold=True, a=a * k, glow=0.25)
            cv.text('家仓库（2026-08-30）', W / 2, 1170, 34, 'sans_med', col=CREAM, a=a * k)
        kh = eo((t - WT('c4h', '重资产') + 0.1) / 0.5)
        for j, s_ in enumerate(('土地', '房子', '物流')):
            chip(cv, s_, 300 + j * 240, 1290, 32, a * eo((t - WT('c4h', s_) + 0.1) / 0.4), col=GOLD)
        if kh > 0: cv.text('实打实的重资产', W / 2, 1380, 34, 'sans_bold', col=GOLD_L, a=a * kh)
        source(cv, 'Costco 2026 财年 10-K：939 warehouses（U.S. 647、Canada 115、Mexico 43、Japan 37、U.K. 29、Korea 20…）', a, y=1462)


# ======================================================================== 第五章：谁在 Costco 买东西
def shot_ch5(cv, t):
    # c5a：YouGov：高收入家庭占比
    t0, t1 = win('c5a')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        pic(cv, ['crowded', 'costco_int3', 'costco_int2'], t, t0, t1, fb=['a_crowd'], fbcap='Costco 卖场（ABC 2005）', cy=520, h=480, a=a, cap='Costco 卖场')
        cv.text('顾客里高收入家庭的占比', W / 2, 860, 34, 'sans_med', col=CREAM, a=a * eo((t - WT('c5a', 'YouGov') + 0.1) / 0.4))
        bars(cv, [('Costco', 18, GOLD, WT('c5a', '百分之十八')), ("BJ's", 15, GREY, WT('c5a', '百分之十八') + 0.5), ('山姆会员店', 12, BLUE_L, WT('c5a', '百分之十二'))],
             t, t0, a, x0=200, x1=880, base=1330, hmax=300, fmt=lambda v: f'{v:.0f}%', label_size=28)
        source(cv, 'YouGov：warehouse club competitors（Costco 18%、BJ’s 15%、Sam’s Club 12%）', a, y=1462)
    # c5b：整箱买需要的三个条件
    t0, t1 = win('c5b')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['a_lot', 'a_crowd'], h=480, cy=520, a=a, cap='满载而归（ABC 2005）')
        cv.text('整箱买才便宜，可你得……', W / 2, 860, 38, 'serif_semi', col=CREAM, a=a * eo((t - WT('c5b', '整箱买') + 0.1) / 0.4))
        items = [('一次拿得出钱', '拿得出钱', '$'), ('家里有地方放', '有地方放', 'house'), ('人口多、吃得完', '人口多', 'family')]
        for j, (s_, w_, ic) in enumerate(items):
            k = eo((t - WT('c5b', w_) + 0.1) / 0.45)
            if k <= 0: continue
            x = 200 + j * 340
            disc(cv, (x, 1050), 70, (0.09, 0.08, 0.07), a * k)
            cv.circle((x, 1050), 70, GOLD, a * k, 3)
            if ic == 'house':
                cv.fillpoly([(x - 40, 1050), (x, 1012), (x + 40, 1050)], GOLD_L, a * k)
                cv.rect(x - 30, 1050, x + 30, 1090, GOLD_L, a * k); cv.rect(x - 9, 1064, x + 9, 1090, (0.09, 0.08, 0.07), a * k)
            elif ic == 'family':
                person(cv, x - 26, 1070, 1.0, a * k, GOLD_L); person(cv, x + 26, 1070, 1.0, a * k, GOLD_L); person(cv, x, 1082, 0.7, a * k, GOLD_L)
            else: cv.text(ic, x, 1050, 64, 'sans_bold', col=GOLD_L, a=a * k)
            cv.text(s_, x, 1170, 30, 'sans_med', col=CREAM, a=a * k)
        k = eo((t - WT('c5b', '中高收入') + 0.1) / 0.45)
        if k > 0: cv.text('→ 更多落在中高收入家庭', W / 2, 1290, 40, 'sans_bold', col=GOLD_L, a=a * k)
        source(cv, '本片解读（参考脚本 V2 的观点）', a * 0.8, y=1462)
    # c5c：循环：买得多、续得稳 → 采购更大 → 价格更低
    t0, t1 = win('c5c')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        labels = ['买得多、续得稳', '采购量更大', '价格更低', '留住更多会员']
        anchors = ['买得多', '采购量', '价格更低', '这套循环']
        ks = [eo((t - WT('c5c', w_) + 0.1) / 0.45) for w_ in anchors]
        ring_cycle(cv, t, W / 2, 780, 290, labels, a, ks, size=30)
        k = eo((t - WT('c5c', '靠的不是') + 0.1) / 0.45)
        if k > 0:
            cv.text('靠的不是面子', W / 2, 1230, 40, 'sans_med', col=GREY, a=a * k)
            cv.text('是一笔算得清的账', W / 2, 1320, 54, 'serif_black', gold=True, a=a * eo((t - WT('c5c', '算得清') + 0.1) / 0.45))
        source(cv, '本片解读', a * 0.8, y=1462)
    # c5d：中国：山姆 1996 深圳；Costco 2019 上海
    t0, t1 = win('c5d')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        tc = WT('c5d', 'Costco 直到')
        if not pic(cv, ['sams_sz1999', 'sams_sz', 'sams_bj'], t, t0, tc + 0.3, cy=520, h=480, a=a, cap='山姆会员店（深圳）'):
            kk = env(t, t0, tc + 0.3, 0.4, 0.4)
            cv.text('1996 · 深圳', W / 2, 470, 90, 'serif_black', col=BLUE_L, a=a * kk, glow=0.15)
            cv.text('山姆会员店进入中国', W / 2, 590, 40, 'sans_med', col=CREAM, a=a * kk)
        pic(cv, ['costco_int2', 'crowded', 'costco_int3'], t, tc - 0.2, t1, fb=['a_crowd'], cy=520, h=480, a=a)
        y = 1060; xa, xb = 170, 910
        k = eexp((t - WT('c5d', '一九九六') + 0.1) / 1.4)
        cv.line((xa, y), (xa + (xb - xa) * k, y), GOLD_D, a, 4)
        if k > 0:
            node(cv, xa + 60, y - 90, '1996 · 山姆', a * min(1, k * 4), col=BLUE_L, size=30, sub='深圳首店')
        kc = eo((t - tc + 0.1) / 0.45)
        if kc > 0:
            node(cv, xb - 70, y - 90, '2019 · Costco', a * kc, col=GOLD, size=30, sub='上海首店')
            cv.text('相隔 23 年', W / 2, y + 50, 30, 'sans_med', col=CREAM, a=a * kc)
        kk = eo((t - WT('c5d', '提前关门') + 0.1) / 0.45)
        if kk > 0: chip(cv, '开业当天，人多到提前关门', W / 2, 1230, 32, a * kk, col=COST_R)
        source(cv, '36kr、界面（山姆 1996 年深圳福田首店）；CNBC、NBC、财新 2019-08-27（Costco 上海闵行开业当天提前关门）', a, y=1462)
    # c5e：公寓 → 一小时送到家；付费会员 1070 万+
    t0, t1 = win('c5e')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        if not pic(cv, ['sams_bj', 'sams_suzhou', 'sams_sz'], t, t0, t1, cy=520, h=480, a=a, cap='山姆会员店（中国）'):
            cv.text('城市家庭：公寓 · 小冰箱', W / 2, 540, 56, 'serif_black', col=BLUE_L, a=a * eo((t - t0) / 0.5))
        k1 = eo((t - WT('c5e', '公寓') + 0.1) / 0.45)
        if k1 > 0:
            for j in range(4):
                for r in range(6):
                    cv.rect(150 + j * 42, 880 + r * 46, 182 + j * 42, 914 + r * 46, C(80, 90, 110), a * k1 * 0.9)
            cv.text('公寓', 235, 1200, 30, 'sans_med', col=CREAM, a=a * k1)
            cv.text('没有大车库、大冰柜', 235, 1250, 24, 'sans_light', col=GREY, a=a * eo((t - WT('c5e', '没有大车库') + 0.1) / 0.4))
        k2 = eo((t - WT('c5e', '一小时') + 0.1) / 0.5)
        if k2 > 0:
            pts = [(360, 1000), (520, 960), (680, 1040), (860, 1000)]
            cv.poly(pts[:1 + int(3 * k2)] if k2 < 1 else pts, GOLD, a * 0.8, 3)
            flow_dots(cv, t, pts, a * k2, GOLD_L, n=4, speed=0.4, size=8)
            node(cv, 860, 1000, '山姆', a * k2, col=BLUE_L, size=28)
            cv.text('约 1 小时送到家', 610, 1110, 34, 'sans_bold', col=GOLD_L, a=a * k2)
        k3 = eo((t - WT('c5e', '变成随时下单') + 0.1) / 0.45)
        if k3 > 0: cv.text('一个月囤一次  →  随时下单', 610, 1190, 30, 'sans_med', col=CREAM, a=a * k3)
        k4 = eo((t - WT('c5e', '一千零七十万') + 0.1) / 0.45)
        if k4 > 0:
            cv.text('付费会员 1070 万+', W / 2, 1320, 52, 'sans_bold', gold=True, a=a * k4, glow=0.15)
            note(cv, '据报道', 1385, a * k4, 22)
        source(cv, '36kr、界面、商业观察家等报道（多数城市约 1 小时送达；付费会员超 1070 万）', a, y=1462)
    # c5f：方便 vs 成本
    t0, t1 = S('c5f') - 0.3, CH['tk_ch5'][0] + 0.3
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('送货到家：一笔还没算完的账', W / 2, 420, 40, 'serif_semi', col=CREAM, a=a * eo((t - t0 - 0.2) / 0.4))
        tilt = 0.12 * math.sin(t * 0.9) * eo((t - t0) / 1.0)
        cx_, cy_ = W / 2, 760
        cv.line((cx_, cy_), (cx_, cy_ + 360), GOLD_D, a, 6)
        cv.fillpoly([(cx_ - 90, cy_ + 380), (cx_ + 90, cy_ + 380), (cx_, cy_ + 330)], GOLD_D, a)
        L = 330
        p0 = (cx_ - L * math.cos(tilt), cy_ - L * math.sin(tilt)); p1 = (cx_ + L * math.cos(tilt), cy_ + L * math.sin(tilt))
        cv.line(p0, p1, GOLD, a, 6)
        disc(cv, (cx_, cy_), 12, GOLD_L, a)
        for p, (s_, col, w_) in zip((p0, p1), (('更方便', GREEN, '更方便'), ('更花钱', COST_R, '更花钱'))):
            k = eo((t - WT('c5f', w_) + 0.1) / 0.4)
            cv.line(p, (p[0], p[1] + 120), GREY, a * k, 2)
            node(cv, p[0], p[1] + 170, s_, a * k, col=col, size=36, w=230)
        k = eo((t - WT('c5f', '复购') + 0.1) / 0.45)
        if k > 0:
            cv.text('能不能成护城河，看复购和续费', W / 2, 1260, 40, 'sans_bold', col=GOLD_L, a=a * k)
            cv.text('能否消化掉配送的成本', W / 2, 1340, 32, 'sans_med', col=CREAM, a=a * eo((t - WT('c5f', '消化') + 0.1) / 0.45))
        source(cv, '本片解读', a * 0.8, y=1462)


# ======================================================================== 第六章：买、买、买
def shot_ch6(cv, t):
    # c6a：1997 董事席位：巴菲特婉拒，推荐芒格
    t0, t1 = win('c6a')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        if not pic(cv, ['buffett_munger2', 'buffett_munger', 'munger2'], t, t0, t1, cy=560, h=562, a=a, cap='巴菲特与芒格'):
            pic(cv, ['buffett_2015'], t, t0, t1, cy=560, h=562, a=a)
        tag(cv, '1997 · Costco 董事会的一个席位', t, WT('c6a', '一九九七'), W / 2, 950, 32, GOLD, a)
        k1 = eo((t - WT('c6a', '巴菲特当董事') + 0.1) / 0.45)
        node(cv, 300, 1130, '巴菲特', a * k1, col=GREY, size=40, w=300)
        k2 = eo((t - WT('c6a', '婉拒') + 0.1) / 0.4)
        if k2 > 0: cv.text('婉拒', 300, 1250, 36, 'sans_bold', col=COST_R, a=a * k2)
        k3 = eo((t - WT('c6a', '推荐了芒格') + 0.1) / 0.45)
        if k3 > 0:
            arrow(cv, (470, 1130), (610, 1130), a * k3, GOLD, 4, 18, k3)
            node(cv, 780, 1130, '芒格', a * k3, col=GOLD, size=44, w=300)
            cv.text('接过席位', 780, 1250, 32, 'sans_bold', col=GOLD_L, a=a * k3)
        source(cv, 'Barchart、moomoo / Yahoo 引《Acquired》2023 访谈：“This seat was first offered to Warren Buffett in 1997, which he declined”', a, y=1462)
    # c6b：1995 年信：零售是门难做的生意
    t0, t1 = win('c6b')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        doc_page(cv, t, t0, t1, 'BERKSHIRE HATHAWAY INC. · 1995 LETTER TO SHAREHOLDERS',
                 ['Retailing is a tough business. During my', 'investment career, I have watched a large',
                  'number of retailers enjoy terrific growth and', 'superb returns on equity for a period, and then',
                  'suddenly nosedive, often all the way into', 'bankruptcy.'], cy=640, size=30, hl='Retailing is a tough business.',
                 hl_t=WT('c6b', '零售是门'))
        k = eo((t - WT('c6b', '风光一阵') + 0.1) / 0.5)
        if k > 0:
            pts = []
            for j in range(int(1 + 38 * k)):
                if j < 27: y = 1240 - 160 * math.sin(min(j / 26, 1) * math.pi * 0.62) ** 1.4
                else: y = 1240 - 160 * 0.93 + (j - 27) * 24
                pts.append((160 + j * 20, y))
            if len(pts) > 1: cv.poly(pts, GOLD_L if k < 0.6 else COST_R, a, 5)
            cv.text('风光一阵 → 一头栽下去', 760, 1180, 34, 'sans_bold', col=COST_R, a=a * eo((t - WT('c6b', '一头栽') + 0.1) / 0.4))
        source(cv, '伯克希尔 1995 年致股东信（原文）', a, y=1462)
    # c6c：Hochschild Kohn：三年后差不多原价卖掉
    t0, t1 = win('c6c')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        tag(cv, '早年的一次教训', t, t0 + 0.2, W / 2, 380, 32, GOLD, a)
        y = 640; xa, xb = 220, 860
        k1 = eo((t - WT('c6c', '巴尔的摩') + 0.1) / 0.45)
        node(cv, xa, y, '买入', a * k1, col=GOLD, size=36, sub='巴尔的摩一家百货公司')
        k2 = eexp((t - WT('c6c', '三年后') + 0.1) / 1.0)
        if k2 > 0:
            arrow(cv, (xa + 170, y), (xb - 110, y), a, GOLD_D, 3, 16, k2)
            cv.text('3 年', W / 2 + 30, y - 40, 34, 'sans_bold', col=CREAM, a=a * min(1, k2 * 2))
        k3 = eo((t - WT('c6c', '只拿回') + 0.1) / 0.45)
        node(cv, xb, y, '卖出', a * k3, col=GREY, size=36, sub='≈ 原价')
        qcard(cv, 'qlucky', t, WT('c6c', '三年后') + 0.4, t1, cy=1050, en=32, cn=38, a=a, typing=1.0)
        source(cv, '伯克希尔 1989 年致股东信（Hochschild, Kohn）', a, y=1462)
    # c6d：引出芒格原声（文化与风气）
    t0, t1 = pre_sot('c6d', 'culture')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        seq(cv, t, t0, t1, ['m_dj1', 'm_dj3'], h=562, a=a, cap='芒格（2022 年《每日期刊》股东会）')
        cv.text('芒格看到的，是另一面', W / 2, 1060, 50, 'serif_black', gold=True, a=a * eo((t - t0 - 0.2) / 0.45))
        tag(cv, '2022 · 98 岁', t, WT('c6d', '九十八'), W / 2, 1180, 32, GOLD, a)
    # c6e：伯克希尔 2020 年清仓 433 万股；芒格一股没卖
    t0, t1 = win('c6e')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('同一只股票，两种做法', W / 2, 380, 40, 'serif_semi', col=CREAM, a=a * eo((t - t0 - 0.1) / 0.4))
        base = 980
        k1 = eo((t - t0) / 0.6)
        sh = 1 - eexp((t - WT('c6e', '全部卖掉') + 0.1) / 1.2)
        gbar(cv, 220, base - 420 * sh, 400, base, GREY, a * k1, sheen_t=t)
        cv.text(counter(433, 0, t, WT('c6e', '全部卖掉'), 1.2, lambda v: f'{v:,.0f} 万股'), 310, base - 420 * sh - 40, 36, 'sans_bold', col=CREAM, a=a * k1)
        cv.text('伯克希尔', 310, base + 50, 32, 'sans_med', col=CREAM, a=a * k1)
        cv.text('2020 年三季度清仓', 310, base + 96, 26, 'sans_light', col=GREY, a=a * eo((t - WT('c6e', '二零二零') + 0.1) / 0.4))
        k2 = eo((t - WT('c6e', '芒格自己') + 0.1) / 0.45)
        if k2 > 0:
            gbar(cv, 680, base - 300, 860, base, GOLD, a * k2, sheen_t=t)
            cv.text('一股没卖', 770, base - 340, 40, 'sans_bold', col=GOLD_L, a=a * k2)
            cv.text('芒格个人', 770, base + 50, 32, 'sans_med', col=CREAM, a=a * k2)
        qcard(cv, 'qaddict', t, WT('c6e', '一股没卖') - 0.2, t1, cy=1260, en=30, cn=36, a=a, typing=0.9)
        source(cv, '伯克希尔 2020 年三季度 13F（4,333,363 股，Motley Fool 等）；芒格 2022 年股东会（Yahoo Finance 报道）', a, y=1462)
    # c6f：2023 年 11 月芒格去世；Costco：没有人比查理更爱 Costco
    t0, t1 = win('c6f')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        if not pic(cv, ['munger2', 'munger'], t, t0, t1, cy=560, h=562, a=a, cap='查理·芒格'):
            seq(cv, t, t0, t1, ['m_dj2'], h=562, a=a, cap='查理·芒格（2022）')
        cv.text('查理·芒格  1924 – 2023', W / 2, 950, 40, 'serif_semi', col=CREAM, a=a * eo((t - t0 - 0.2) / 0.45))
        qcard(cv, 'qcostco', t, WT('c6f', 'Costco 在公告') - 0.2, t1, cy=1160, en=40, cn=44, a=a, typing=0.8)
        source(cv, 'Costco 2023-11-29 公告（CEO Craig Jelinek）；伯克希尔 2023 年致股东信', a, y=1462)
    # c6g：2024 年股东大会：买、买、买
    t0, t1 = S('c6g') - 0.3, CH['tk_ch6'][0] + 0.3
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        tb = WT('c6g', '买、买、买'); te = WT('c6g', '他说，他本该')
        pic(cv, ['buffett_2015', 'buffett_2010'], t, t0, tb - 0.1, cy=560, h=562, a=a, cap='沃伦·巴菲特')
        tag(cv, '2024 · 伯克希尔股东大会（芒格去世后第一次）', t, t0 + 0.2, W / 2, 905, 28, GOLD, a)
        kz = 1 - eo((t - te + 0.3) / 0.4)
        for j in range(3):
            kk = eo((t - tb - j * 0.28) / 0.25)
            if kk > 0: cv.text('买！', 280 + j * 260, 480, 120, 'serif_black', gold=True, a=a * kk * kz, glow=0.3, scale=1.3 - 0.3 * kk)
        for j, (s_, w_) in enumerate((('比亚迪', '比亚迪'), ('Costco', '一次是 Costco'))):
            kk = eo((t - WT('c6g', w_) + 0.1) / 0.4) * kz
            node(cv, 330 + j * 420, 700, s_, a * kk, col=GOLD if j else CREAM, size=44, w=300)
        qcard(cv, 'qbuy', t, WT('c6g', '他说，这么多年') - 0.1, te + 0.1, cy=1200, en=30, cn=36, a=a, typing=1.2)
        qcard(cv, 'qaggr', t, te - 0.2, t1, cy=1200, en=40, cn=44, a=a, typing=0.8)
        source(cv, '2024-05-04 伯克希尔股东大会（Steady Compounding 逐字稿、CNBC 报道）', a, y=1462)


# ======================================================================== 第七章：好公司与好价格
def shot_ch7(cv, t):
    # c7a：引出原声：估值创历史新高，新投资者怎么看？
    t0, t1 = pre_sot('c7a', 'price1')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        seq(cv, t, t0, t1, ['m_dj3', 'm_dj2'], h=562, a=a, cap='芒格（2022 年《每日期刊》股东会）')
        cv.text('最爱 Costco 的人，也泼过冷水', W / 2, 960, 42, 'serif_semi', col=CREAM, a=a * eo((t - t0 - 0.2) / 0.45))
        k = eo((t - WT('c7a', '有人问他') + 0.1) / 0.45)
        if k > 0:
            cv.rrect(110, 1060, 970, 1300, 22, (0.07, 0.06, 0.05), a * k * 0.92)
            cv.rrect(110, 1060, 970, 1300, 22, GOLD_D, a * k * 0.8, fill=False, th=2)
            cv.text('提问', 160, 1100, 24, 'sans_med', col=GOLD, a=a * k, anchor='l')
            cv.text('Costco 的估值创了历史新高，', W / 2, 1160, 40, 'sans_bold', col=CREAM, a=a * k)
            cv.text('新投资者该怎么看？', W / 2, 1230, 40, 'sans_bold', col=GOLD_L, a=a * eo((t - WT('c7a', '新投资者') + 0.1) / 0.4))
    # c7b / c7c：两段原声之间的串场
    for lid, sid, txt in (('c7b', 'price2', '但他接着说'), ('c7c', 'price3', '至于他自己')):
        t0, t1 = pre_sot(lid, sid, pre=0.4)
        a = env(t, t0, t1, 0.3, 0.3)
        if a > 0:
            seq(cv, t, t0, t1, ['m_dj2'], h=562, a=a, cap='芒格（2022）')
            cv.text(txt + '……', W / 2, 1100, 56, 'serif_black', gold=True, a=a * eo((t - t0) / 0.3))
    # c7d：市盈率 40 多倍到 50 倍
    t0, t1 = win('c7d')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('好公司 ≠ 什么价格都值得买', W / 2, 400, 50, 'serif_black', gold=True, a=a * eo((t - t0 - 0.1) / 0.45))
        k = eexp((t - WT('c7d', '市盈率') + 0.1) / 1.4)
        dial(cv, W / 2, 1020, 330, 48 * k, 60, a * min(1, eo((t - WT('c7d', '二零二六') + 0.1) / 0.5)))
        if k > 0.3:
            cv.text('40 多倍 ～ 50 倍', W / 2, 1130, 60, 'sans_bold', col=GOLD_L, a=a * min(1, (k - 0.3) * 2), glow=0.15)
            cv.text('Costco 市盈率 · 2026 年秋', W / 2, 1210, 30, 'sans_med', col=CREAM, a=a * min(1, (k - 0.3) * 2))
        note(cv, '示意：指针指向区间中部', 1290, a * 0.7, 22)
        source(cv, 'GuruFocus（2026-08-29：47.6 倍）；fullratio（2026-11-02：约 50 倍）；Motley Fool 2026-08', a, y=1462)
    # c7e：三件事
    t0, t1 = win('c7e')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('研究 Costco，盯住三件事', W / 2, 400, 50, 'serif_black', col=CREAM, a=a * eo((t - t0 - 0.1) / 0.45))
        items = [('循环有没有松动', '低毛利 · 大采购 · 高续费', '低毛利'), ('新投入，回报好不好', '新开的仓库 · 线上投入', '新开的仓库'), ('价格有没有留余地', '安全边际', '今天的价格')]
        for j, (hd, sub, w_) in enumerate(items):
            k = eo((t - WT('c7e', w_) + 0.1) / 0.45)
            if k <= 0: continue
            y = 640 + j * 230
            cv.rrect(120, y - 90, 960, y + 90, 20, (0.07, 0.06, 0.05), a * k * 0.92)
            cv.rrect(120, y - 90, 960, y + 90, 20, GOLD if j == 2 else GOLD_D, a * k * 0.8, fill=False, th=2)
            cv.text(f'{j + 1}', 190, y, 70, 'oswald', col=GOLD, a=a * k)
            cv.text(hd, 260, y - 22, 42, 'sans_bold', col=GOLD_L if j == 2 else CREAM, a=a * k, anchor='l')
            cv.text(sub, 262, y + 40, 26, 'sans_light', col=GREY, a=a * k, anchor='l')
        source(cv, '本片解读', a * 0.8, y=1462)
    # c7f：两种护城河
    t0, t1 = win('c7f')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('2007 年致股东信：两种护城河', W / 2, 420, 38, 'sans_med', col=CREAM, a=a * eo((t - t0 - 0.1) / 0.4))
        for j, (hd, sub, ex, w_, col) in enumerate((('强大的品牌', 'a powerful world-wide brand', '可口可乐 · 喜诗', '强大的品牌', GOLD_L),
                                                     ('成本最低', 'the low-cost producer', 'GEICO · Costco', '成本最低', BLUE_L))):
            kk = eo((t - WT('c7f', w_) + 0.1) / 0.5)
            if kk <= 0: continue
            x = 300 + j * 480
            cv.rrect(x - 210, 560, x + 210, 1000, 20, (0.06, 0.05, 0.045), a * kk * 0.92)
            cv.rrect(x - 210, 560, x + 210, 1000, 20, col, a * kk * 0.7, fill=False, th=2)
            cv.text(hd, x, 660, 54, 'serif_black', col=col, a=a * kk)
            cv.text(sub, x, 740, 24, 'corm', col=GREY, a=a * kk)
            cv.line((x - 140, 790), (x + 140, 790), col, a * kk * 0.6, 2)
            cv.text(ex, x, 860, 30, 'sans_med', col=CREAM, a=a * kk)
        qcard(cv, 'qmoat', t, WT('c7f', '成本最低') + 0.6, t1, cy=1210, en=28, cn=32, a=a, typing=1.2)
        source(cv, '伯克希尔 2007 年致股东信（原文）', a, y=1462)
    # c7g：一盒糖 vs 一根热狗 → 顾客一次又一次回来
    t0, t1 = S('c7g') - 0.3, CH['end'][0] + 0.4
    a = env(t, t0, t1, 0.4, 0.6)
    if a > 0:
        k1 = eo((t - t0 - 0.1) / 0.5)
        candy_box(cv, 290, 650, 0.8, a * k1, lid=1.0)
        cv.text('年年涨价的糖', 290, 860, 36, 'sans_bold', col=GOLD_L, a=a * k1)
        cv.text('价格 ↑', 290, 930 + 6 * math.sin(t * 2), 40, 'sans_bold', col=GOLD_L, a=a * k1)
        k2 = eo((t - WT('c7g', '一根') + 0.1) / 0.5)
        hotdog(cv, 760, 680, 0.6, a * k2, t)
        cv.text('四十年不涨价的热狗', 790, 860, 36, 'sans_bold', col=BLUE_L, a=a * k2)
        cv.text('$1.50 →', 790, 930, 40, 'sans_bold', col=BLUE_L, a=a * k2)
        k3 = eo((t - WT('c7g', '路是相反') + 0.1) / 0.45)
        if k3 > 0: cv.text('路是相反的', W / 2, 1070, 44, 'serif_semi', col=CREAM, a=a * k3)
        k4 = eo((t - WT('c7g', '顾客愿意') + 0.1) / 0.5)
        if k4 > 0:
            cv.text('顾客愿意一次又一次地回来', W / 2, 1200, 60, 'serif_black', gold=True, a=a * k4, glow=0.25)
            for j in range(10):
                ang = 2 * math.pi * ((t * 0.12 + j / 10) % 1.0)
                cv.glow_dot((W / 2 + 420 * math.cos(ang), 1200 + 60 * math.sin(ang)), 5, GOLD_L, a * k4 * 0.6)
