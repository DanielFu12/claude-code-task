"""第五期《一盒糖的学费——芒格怎样改变了巴菲特》全部镜头：开场、片名、第一至七章。

版式（沿用前几期）：上方画窗（y≈279–841）放真实影像；下方 y 900–1420 放动画解读；y≈1462 出处；y≈1555 字幕。
没有影像的镜头，动画可以占用 300–1420。
素材（v2）：archive.org 实拍（src/fetch_ia.py）——喜诗工厂 f_*（Business Insider 2018）、门店 v_* / m_*（KVVU 2021、莫雷诺谷 2016）、
1981 年母亲节新闻 n_*、1988 年喜诗电视广告 a_*、卓别林《寻子遇仙记》k_*（1921，公有领域，“烟蒂”示意）、HBO 纪录片 x_bwb_*；
CNBC 2026-07-15 专访画面（c_*，src/cut_cnbc.py）；Wikimedia Commons 照片（assets/media/credits.json）；
其余为伯克希尔致股东信原文数据的图表与示意动画（示意处画面标注“示意”）。片名与片尾的糖盒为自绘线稿。
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


PORTRAIT = {'buffett_2010', 'buffett_2015', 'buffett_ku', 'munger', 'munger2'}      # 人像照片：整幅入窗，不放大成大头像


def photo_win(cv, name, t, t0, t1, cy=560, w=1000, h=562, focus=(0.5, 0.5), cap=None, a=1.0, z0=1.02, z1=1.12, pan=(0, 0, 0, 0)):
    if name in PORTRAIT:
        return M.frame(cv, name, t, t0, t1, cy=cy, w=w, h=h, z0=1.0, z1=1.03, focus=focus, a=a, cap=cap, fit='contain', pan=pan)
    return M.frame(cv, name, t, t0, t1, cy=cy, w=w, h=h, z0=z0, z1=z1, focus=focus, a=a, cap=cap, pan=pan)


def pic(cv, names, t, t0, t1, **kw):
    """names 里第一张已入库的照片；都没有则返回 False（调用方画自绘插画）"""
    n = first_have(names)
    if n is None: return False
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


# 1972 年时喜诗门店主要分布（示意：加州为主，西部各州少量；位置按城市大致经纬度，非逐店）
STORE_CITIES = [(34.05, -118.25), (37.77, -122.42), (37.34, -121.89), (32.72, -117.16), (38.58, -121.49), (34.15, -118.14),
                (33.83, -117.91), (36.74, -119.79), (37.80, -122.27), (34.42, -119.70), (33.98, -117.37), (35.37, -119.02),
                (37.55, -122.31), (38.44, -122.71), (33.66, -117.83), (34.10, -117.29), (36.97, -122.03), (40.80, -124.16),
                (35.08, -106.65), (33.45, -112.07), (32.22, -110.97), (36.17, -115.14), (45.52, -122.68), (47.61, -122.33),
                (40.76, -111.89), (39.53, -119.81), (34.05, -117.75), (37.96, -121.29), (34.20, -118.60), (33.77, -118.19)]


# ======================================================================== 开场
def shot_hook(cv, t):
    a0 = env(t, 0, S('h1') + 0.6, 0.0, 0.5)
    if a0 > 0:
        L = 420 * eo(t / 1.1); hb = math.exp(-max(t - 0.25, 0) * 6) * (t >= 0.25)
        cv.line((W / 2 - L, 960), (W / 2 + L, 960), GOLD, a0 * (0.5 + 0.5 * hb), 2)
        cv.glow_dot((W / 2, 960), 30 + 40 * hb, GOLD, a0 * 0.6)
    # h1：一家加州糖果公司 → 要价 3000 万，芒格说值
    t0, t1 = win('h1')
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['v_ext', 'f_kettle', 'f_coat'], h=562, a=a)
        tag(cv, '一家加州的糖果公司', t, t0 + 0.4, W / 2, 940, 30, GOLD, a)
        tw = WT('h1', '3000')
        money(cv, t, tw, '$3000 万', W / 2, 1120, 96, a, sub='卖家的要价')
        tag(cv, '芒格：值这个价', t, WT('h1', '芒格说'), W / 2, 1300, 32, GOLD_L, a)
        source(cv, '伯克希尔 2014 年致股东信', a, y=1462)
    # h2：巴菲特：最多 2500 万；有形资产 800 万 → 三倍 → “倒吸了一口气”
    t0, t1 = win('h2')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('1972 · 喜诗糖果', W / 2, 330, 34, 'sans_med', col=CREAM, a=a)
        base = 1000
        # 三根柱：有形资产 800 万 / 出价 2500 万 / 要价 3000 万
        cols = [('有形资产', 8, WT('h2', '有形资产'), GREY, '$800 万'),
                ('巴菲特出价', 25, WT('h2', '2500'), GOLD, '$2500 万'),
                ('卖家要价', 30, t0 + 0.2, CREAM * 0.6, '$3000 万')]
        xs = [250, 540, 830]
        for (lb, v, ts, col, txt), x in zip(cols, xs):
            e = eexp((t - ts) / 0.9)
            if e <= 0: continue
            h = 520 * v / 30 * e
            gbar(cv, x - 90, base - h, x + 90, base, col, a, sheen_t=t - ts)
            cv.text(txt, x, base - h - 40, 40, 'sans_bold', col=CREAM if col is not GOLD else GOLD_L, a=a * min(1, e * 2), shadow=0.6)
            cv.text(lb, x, base + 44, 28, 'sans_med', col=GREY, a=a * min(1, e * 2))
        k3 = eo((t - WT('h2', '三倍') + 0.1) / 0.5)
        if k3 > 0:
            for j in range(3):                       # 3 份“有形资产”叠到 2500 万旁边
                yy = base - (j + 1) * 520 * 8 / 30
                cv.rect(540 + 100, yy, 540 + 130, yy + 520 * 8 / 30 - 4, GREY * 0.8, a * k3 * eo((t - WT('h2', '三倍') - j * 0.15) / 0.3))
            cv.text('≈ 3 ×', 540 + 200, base - 260, 46, 'sans_bold', col=GOLD_L, a=a * k3, anchor='l')
        qcard(cv, 'qgulp', t, WT('h2', '他后来写道') - 0.4, t1, cy=1250, en=30, cn=36)
        source(cv, '伯克希尔 2014 年致股东信；1991 年致股东信', a, y=1462)
    # h3：卖家接受 → 到 2014 年：累计税前利润 19 亿 vs 追加投资 4000 万
    t0, t1 = win('h3')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        k = eo((t - t0 - 0.2) / 0.5)
        stamp_a = k * (1 - eo((t - WT('h3', '到 2014') + 0.4) / 0.5))
        if stamp_a > 0:
            cv.text('成交', W / 2, 640, 150, 'serif_black', gold=True, a=a * stamp_a, glow=0.3, scale=1.3 - 0.3 * k)
            cv.text('$2500 万', W / 2, 820, 60, 'sans_bold', col=CREAM, a=a * stamp_a)
        tb = WT('h3', '到 2014')
        kb = eo((t - tb + 0.1) / 0.6)
        if kb > 0:
            cv.text('到 2014 年', W / 2, 360, 40, 'sans_med', col=CREAM, a=a * kb)
            R1 = 300 * eo((t - WT('h3', '19 亿') + 0.1) / 1.0) if '19 亿' in _SAY['h3'] else 300 * kb
            disc(cv, (380, 760), R1, GOLD, a * 0.25); cv.circle((380, 760), R1, GOLD_L, a * 0.9, 3)
            money(cv, t, WT('h3', '19 亿') if '19 亿' in _SAY['h3'] else tb, '$19 亿', 380, 740, 84, a, sub='累计税前利润')
            r2 = 300 * math.sqrt(0.4 / 19) * eo((t - WT('h3', '4000') + 0.1) / 0.6)
            if r2 > 0:
                disc(cv, (830, 860), r2, CREAM, a * 0.5)
                money(cv, t, WT('h3', '4000'), '$4000 万', 830, 960, 50, a, col=CREAM, sub='追加投入')
            note(cv, '圆的面积与金额成比例', 1180, a * kb * 0.8, 22)
        source(cv, '伯克希尔 2014 年致股东信：“To date, See’s has earned $1.9 billion pre-tax, with its growth having required added investment of only $40 million.”', a, y=1462)
    # h4：喜诗糖果 → 梦想生意的原型 → 芒格怎样改变了巴菲特
    t0, t1 = S('h4') - 0.3, CH['title'][0] + 0.1
    a = env(t, t0, t1, 0.4, 0.2)
    if a > 0:
        seq(cv, t, t0, t1 - 0.2, ['f_rows2', 'f_tray'], h=562, a=a)
        big_q(cv, t, '喜诗糖果', 1000, S('h4'), 90, a)
        tag(cv, '“梦想生意的原型”', t, WT('h4', '梦想生意'), W / 2, 1130, 34, GOLD, a)
        big_q(cv, t, '芒格，怎样改变了巴菲特？', 1280, WT('h4', '芒格'), 52, a, col=CREAM)


def shot_title(cv, t):
    t0, t1 = CH['title'][0], CH['ch1'][0] + 0.6
    a = env(t, t0, t1, 0.02, 0.6)
    if a <= 0: return
    p = t - t0
    flash = math.exp(-p * 5.0)
    candy_box(cv, W / 2, 700, 1.0, a * eo(p / 0.35), lid=1.0, glow=0.4)
    R = 60 + p * 900
    cv.circle((W / 2, 720), R, GOLD, a * math.exp(-p * 2.2) * 0.8, 3)
    cv.glow_dot((W / 2, 720), 220, GOLD, a * flash * 0.9)
    k = eo((p - 0.15) / 0.6)
    cv.text('一盒糖的学费', W / 2, 1100, 120, 'serif_black', gold=True, a=a * k, glow=0.3, scale=1.08 - 0.08 * k)
    cv.text('芒格怎样改变了巴菲特', W / 2, 1250, 60, 'serif_semi', col=CREAM, a=a * eo((p - 0.5) / 0.6))
    cv.text('THE TUITION OF A CANDY BOX', W / 2, 1350, 26, 'corm', col=GOLD, a=a * eo((p - 1.0) / 0.6), track=0.35)


# ======================================================================== 第一章：差点谈崩的交易
def shot_ch1(cv, t):
    # c1a：玛丽·喜的第一家小店（1921）
    t0, t1 = win('c1a', pre=0.1)
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['v_wall', 'f_kettle2', 'f_fondant'], h=562, a=a)
        tag(cv, '1921 · 洛杉矶', t, WT('c1a', '一九二一年'), W / 2, 950, 30, GOLD, a)
        k = eo((t - WT('c1a', '自家配方') + 0.1) / 0.5)
        if k > 0: candy_box(cv, 300, 1170, 0.55, a * k, lid=1.0)
        if k > 0: cv.text('自家配方', 300, 1330, 32, 'sans_med', col=GOLD_L, a=a * k)
        k2 = eo((t - WT('c1a', '店员') + 0.1) / 0.5)
        if k2 > 0:
            cv.text('店员亲切热情', 760, 1170, 40, 'serif_semi', col=CREAM, a=a * k2)
            for j in range(5):
                cv.glow_dot((640 + j * 60, 1250), 8, GOLD_L, a * k2 * (0.6 + 0.4 * math.sin(t * 3 + j)))
        source(cv, '伯克希尔 2020 年致股东信（Mary See 与第一家洛杉矶小店）；喜诗官网大事记（1921）', a, y=1462)
    # c1a2：1952《我爱露西》：两位女主角到喜诗厨房学蘸巧克力、装糖盒（画面为今日喜诗厨房实拍，不是剧集）
    t0, t1 = win('c1a2')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['f_hands', 'f_rows', 'f_coat'], h=562, a=a, cap='今日喜诗厨房')
        tag(cv, '1952 · 电视喜剧《我爱露西》', t, t0 + 0.3, W / 2, 950, 30, GOLD, a)
        k = eo((t - WT('c1a2', '专门到喜诗的厨房') + 0.1) / 0.5)
        if k > 0:
            cv.text('两位女主角到喜诗厨房', W / 2, 1080, 46, 'serif_semi', col=CREAM, a=a * k)
            cv.text('学蘸巧克力、装糖盒', W / 2, 1150, 46, 'serif_semi', col=CREAM, a=a * k)
        k2 = eo((t - WT('c1a2', '后来拍出了') + 0.1) / 0.5)
        if k2 > 0:
            chip(cv, '→ 巧克力流水线那一集 · “Job Switching”', W / 2, 1280, 28, a * k2, col=GOLD_L)
        source(cv, '喜诗官网大事记 1952 “Lucy Loves See’s”（Lucille Ball 与 Vivian Vance 到 La Cienega 的喜诗厨房学艺）', a, y=1462)
    # c1b：1972 年：西海岸 167 家店
    t0, t1 = win('c1b')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('1972 年 · 美国西部', W / 2, 330, 36, 'sans_med', col=CREAM, a=a)
        n = len(STORE_CITIES); p = eo((t - t0 - 0.3) / 2.2)
        dots = [(la, lo, cl(p * n - i)) for i, (la, lo) in enumerate(STORE_CITIES)]
        us_west(cv, W / 2 + 40, 760, 36, a, dots, t)
        cnt = int(round(167 * p))
        cv.text(f'{cnt}', W / 2, 1210, 150, 'oswald', col=GOLD, a=a * min(1, p * 3), glow=0.2)
        cv.text('家门店（1972 年底）', W / 2, 1330, 34, 'sans_med', col=CREAM, a=a * p)
        note(cv, '光点为示意分布（以加州为主），不是逐店位置', 1390, a * p * 0.8, 20)
        source(cv, '伯克希尔 1984 年致股东信，喜诗历年数据表（1972 年底门店 167 家）', a, y=1462)
    # c1c：1972-01-03 蓝筹印花买下喜诗 → 后来并入伯克希尔
    t0, t1 = win('c1c')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        k = eo((t - t0 - 0.2) / 0.6)
        ks = eo((t - WT('c1c', '蓝筹印花') + 0.7) / 0.45)        # 大数字收起 → 变成顶部小标签
        if ks < 1:
            kz = 1 - ks
            cv.text('$2500', W / 2 + 110, 720, 150, 'oswald', col=GOLD, a=a * k * kz, glow=0.25, anchor='r')
            cv.text('万', W / 2 + 125, 735, 88, 'sans_bold', col=GOLD, a=a * k * kz, glow=0.25, anchor='l')
            cv.text('卖家接受了这个价格', W / 2, 850, 34, 'sans_med', col=CREAM, a=a * eo((t - t0 - 0.6) / 0.6) * kz)
            cv.text('比 3000 万的要价，少了 500 万', W / 2, 910, 26, 'sans_light', col=GREY, a=a * eo((t - t0 - 1.0) / 0.6) * kz)
        chip(cv, '成交价 $2500 万', W / 2, 330, 30, a * ks, col=GOLD_L)
        k0 = eo((t - WT('c1c', '一九七二年') + 0.1) / 0.5)
        cv.text('1972 年 1 月 3 日', W / 2, 440, 56, 'sans_bold', col=GOLD, a=a * k0, glow=0.2)
        stamp(cv, 330, 700, 1.0, a * eo((t - WT('c1c', '蓝筹印花') + 0.2) / 0.5), rot=-0.06)
        cv.text('蓝筹印花公司', 330, 860, 30, 'sans_med', col=CREAM, a=a * eo((t - WT('c1c', '蓝筹印花') + 0.2) / 0.5))
        cv.text('巴菲特、芒格与伯克希尔控制', 330, 905, 22, 'sans_light', col=GREY, a=a * eo((t - WT('c1c', '蓝筹印花') + 0.2) / 0.5))
        kb = eo((t - WT('c1c', '买下了喜诗') + 0.1) / 0.6)
        if kb > 0:
            cv.line((500, 700), (500 + 120 * kb, 700), GOLD, a, 4)
            cv.fillpoly([(620 * kb + 500 * (1 - kb) + 0, 686), (640 * kb + 500 * (1 - kb), 700), (620 * kb + 500 * (1 - kb), 714)], GOLD, a * kb)
            candy_box(cv, 800, 700, 0.62, a * kb, lid=0.0)
            cv.text('喜诗糖果', 800, 860, 30, 'sans_med', col=CREAM, a=a * kb)
        km = eo((t - WT('c1c', '蓝筹印花后来') + 0.1) / 0.6)
        if km > 0:
            cv.line((330, 960), (330, 1060 * km + 960 * (1 - km)), GOLD_D, a, 3)
            chip(cv, '1983 年并入伯克希尔·哈撒韦', W / 2, 1140, 32, a * km, col=GOLD)
        source(cv, '伯克希尔 1991 年致股东信（“the sellers accepted our offer”；成交日 1972-01-03）；1983 年致股东信（蓝筹印花合并）', a, y=1462)
    # c1d：名义要价 4000 万 − 多余现金 1000 万 = 实际要价 3000 万
    t0, t1 = win('c1d')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('卖家开价', W / 2, 340, 40, 'sans_med', col=CREAM, a=a)
        rows = [('名义要价', '$4000 万', S('c1d') + 0.2, CREAM), ('账上多余现金', '− $1000 万', WT('c1d', '1000'), GREY),
                ('实际要价', '$3000 万', WT('c1d', '所以'), GOLD_L)]
        for j, (lb, v, ts, col) in enumerate(rows):
            k = eo((t - ts + 0.1) / 0.5)
            if k <= 0: continue
            y = 560 + j * 170
            cv.text(lb, 200, y, 40, 'sans_med', col=CREAM, a=a * k, anchor='l')
            cv.text(v, 880, y, 64, 'sans_bold', col=col, a=a * k, anchor='r', shadow=0.6)
            if j == 1:
                kk = eo((t - ts - 0.3) / 0.4)
                cv.line((170, y + 70), (170 + 740 * kk, y + 70), GOLD_D, a * k, 2)
        source(cv, '伯克希尔 1991 年致股东信：“the true offering price was $30 million”', a, y=1462)
    # c1e：税前 420 万 / 税后约 200 万 / 有形资产
    t0, t1 = win('c1e')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('喜诗 · 1972 年', W / 2, 340, 40, 'sans_med', col=CREAM, a=a)
        money(cv, t, S('c1e') + 0.3, '$420 万', 300, 560, 80, a, sub='一年税前利润')
        money(cv, t, WT('c1e', '税后'), '≈ $200 万', 780, 560, 80, a, col=CREAM, sub='税后')
        k = eo((t - WT('c1e', '可巴菲特') + 0.1) / 0.5)
        if k > 0:
            cv.rrect(240, 880, 840, 1240, 14, C(36, 34, 32), a * k * 0.9)
            cv.rrect(240, 880, 840, 1240, 14, GREY, a * k * 0.6, fill=False, th=2)
            cv.text('资产负债表 · 有形资产', W / 2, 930, 28, 'sans_med', col=GREY, a=a * k)
            for j, (lb, w_) in enumerate([('存货', 0.5), ('厂房与设备', 0.8), ('其他', 0.3)]):
                y = 1010 + j * 70
                cv.text(lb, 290, y, 28, 'sans_light', col=CREAM, a=a * k, anchor='l')
                cv.rect(500, y - 16, 500 + 300 * w_ * eo((t - WT('c1e', '可巴菲特') - 0.2 - j * 0.2) / 0.5), y + 16, GREY * 0.8, a * k)
            cv.text('约 $800 万', W / 2, 1290, 44, 'sans_bold', col=CREAM, a=a * k)
        source(cv, '伯克希尔 1991 年信（税前 $4.2M）；1983 年信（税后约 $2M、有形净资产约 $8M）；2014 年信（“three times net tangible assets made me gulp”）', a, y=1462)
    # c1g：2014 年：芒格说值 3000 万，是对的；我的谨慎差点毁了这笔收购
    t0, t1 = win('c1g')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        # 价格刻度尺：800 万 … 2500 万（巴菲特）… 3000 万（芒格）
        y = 560
        x_of = lambda v: 160 + (v / 32) * 760
        p = eo((t - t0 - 0.2) / 0.8)
        cv.line((x_of(0), y), (x_of(0) + (x_of(32) - x_of(0)) * p, y), GOLD_D, a, 3)
        for v in (0, 8, 16, 25, 30):
            if x_of(v) > x_of(0) + (x_of(32) - x_of(0)) * p: continue
            cv.line((x_of(v), y - 12), (x_of(v), y + 12), GOLD_D, a, 2)
            cv.text(f'{v}', x_of(v), y + 44, 24, 'sans_light', col=GREY, a=a)
        cv.text('单位：百万美元', 920, y + 90, 20, 'sans_light', col=GREY, a=a * p, anchor='r')
        km = eo((t - WT('c1g', '芒格说它值') + 0.1) / 0.5)
        if km > 0:
            cv.line((x_of(30), y - 20), (x_of(30), y - 120), GOLD_L, a * km, 3)
            chip(cv, '芒格：值 3000 万 ✓', x_of(30) - 60, y - 160, 30, a * km, col=GOLD_L)
        kb = eo((t - WT('c1g', '倒是他自己') + 0.1) / 0.5)
        if kb > 0:
            cv.line((x_of(25), y + 70), (x_of(25), y + 150), CREAM, a * kb, 3)
            chip(cv, '巴菲特：2500 万都不太情愿', x_of(25) - 80, y + 190, 28, a * kb, col=CREAM)
        qcard(cv, 'qcaution', t, WT('c1g', '他说') - 0.4 if '他说' in _SAY['c1g'] else t0 + 2, t1, cy=1150, en=30, cn=36)
        qcard(cv, 'qright', t, t0 + 0.3, WT('c1g', '他说') - 0.5 if '他说' in _SAY['c1g'] else t0 + 2, cy=1150, en=34, cn=38)
        source(cv, '伯克希尔 2014 年致股东信（50 周年回顾）', a, y=1462)
    # c1h：查克·哈金斯：当天掌管，五分钟谈好薪酬，握手为定
    t0, t1 = win('c1h')
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        if not pic(cv, ['sees_hq', 'sees_hq_2025a'], t, t0, t1, cap='喜诗糖果旧金山总部', focus=(0.5, 0.5), pan=(0.0, 0.02, 0.0, -0.02)):
            storefront(cv, t, W / 2, 560, 1.0, a)
        tag(cv, '查克·哈金斯 · 当天接掌喜诗', t, WT('c1h', '查克'), W / 2, 930, 32, GOLD, a)
        k = eo((t - WT('c1h', '五分钟') + 0.1) / 0.5)
        if k > 0:
            cv.text('5', 330, 1150, 150, 'oswald', col=GOLD, a=a * k, glow=0.2)
            cv.text('分钟谈好薪酬', 330, 1270, 30, 'sans_med', col=CREAM, a=a * k)
        k2 = eo((t - WT('c1h', '握手为定') + 0.1) / 0.5)
        if k2 > 0:
            cv.rrect(620, 1060, 900, 1260, 6, PAPER * 0.9, a * k2)
            for r in range(5): cv.line((650, 1100 + r * 28), (870 - (r % 2) * 50, 1100 + r * 28), INKD * 3, a * k2 * 0.5, 2)
            kx = eo((t - WT('c1h', '从没写成') + 0.1) / 0.4)
            if kx > 0:
                cv.line((630, 1070), (630 + 260 * kx, 1070 + 180 * kx), RED, a * k2, 6)
                cv.line((890, 1070), (890 - 260 * kx, 1070 + 180 * kx), RED, a * k2, 6)
            cv.text('没有书面合同', 760, 1310, 30, 'sans_med', col=CREAM, a=a * k2)
        source(cv, '伯克希尔 1991 年致股东信；2005 年致股东信（哈金斯 1972 年接掌时 46 岁，任期 34 年）', a, y=1462)


# ======================================================================== 第二章：账上看不见的资产
def shot_ch2(cv, t):
    # c2a + c2b：2500 万 = 800 万有形资产 + 1700 万“商誉”，会计上 40 年摊销
    t0, t1 = S('c2a') - 0.3, win('c2b')[1]
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('$2500 万买到了什么？', W / 2, 340, 46, 'serif_semi', col=CREAM, a=a)
        x0, x1, ytop, ybot = 200, 880, 440, 1060
        H_ = ybot - ytop
        p = eo((t - t0 - 0.3) / 0.8)
        h8 = H_ * 8 / 25
        cv.rect(x0, ybot - h8 * p, x1, ybot, GREY * 0.7, a)
        cv.text('有形资产 · 约 $800 万', (x0 + x1) / 2, ybot - h8 / 2, 34, 'sans_bold', col=CREAM, a=a * p)
        kq = eo((t - WT('c2a', '1700') + 0.1) / 0.7) if '1700' in _SAY['c2a'] else eo((t - S('c2a') - 0.8) / 0.7)
        if kq > 0:
            h17 = (H_ - h8) * kq
            cv.rect(x0, ybot - h8 - h17, x1, ybot - h8 - 6, GOLD * 0.45, a, glow=0.12)
            cv.rrect(x0, ybot - h8 - h17, x1, ybot - h8 - 6, 4, GOLD_L, a * 0.8, fill=False, th=2)
            cv.text('?', (x0 + x1) / 2, ybot - h8 - h17 / 2 - 30, 120, 'serif_black', gold=True, a=a * kq * (1 - eo((t - S('c2b')) / 0.5)), glow=0.3)
            cv.text('多付的 $1700 万', (x0 + x1) / 2, ybot - h8 - h17 / 2 + 70, 36, 'sans_bold', col=GOLD_L, a=a * kq)
        kb = eo((t - WT('c2b', '商誉') + 0.1) / 0.5)
        if kb > 0:
            cv.text('会计上叫“商誉”', (x0 + x1) / 2, ytop + 150, 46, 'serif_semi', col=CREAM, a=a * kb)
            # 40 年摊销：每年 42.5 万，金块逐年变短
            ka = eo((t - WT('c2b', '四十年') + 0.1) / 2.5) if '四十年' in _SAY['c2b'] else 0
            y = 1180
            cv.text('会计摊销：40 年 × 每年 $42.5 万', W / 2, y - 50, 30, 'sans_med', col=CREAM, a=a * kb)
            cv.rect(160, y - 14, 160 + 760 * (1 - ka), y + 14, GOLD * 0.6, a * kb)
            cv.rect(160, y - 14, 920, y + 14, GOLD_D, a * kb * 0.3)
            yr = 1972 + int(40 * ka)
            cv.text(f'{yr}', 160 + 760 * (1 - ka), y + 50, 28, 'oswald', col=GOLD, a=a * kb)
        source(cv, '伯克希尔 1983 年致股东信附录《商誉及其摊销》：多付 $17M，计为商誉，40 年摊销、每年 $425,000', a, y=1462)
    # c2c：带来高回报的不是存货、应收账款、厂房，而是好名声
    t0, t1 = win('c2c')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        items = [('存货', WT('c2c', '存货')), ('应收账款', WT('c2c', '应收账款')), ('厂房', WT('c2c', '厂房'))]
        ki = 1 - eo((t - WT('c2c', '账上看不见') + 0.3) / 0.4)
        kh = eo((t - t0 - 0.1) / 0.5) * ki
        if kh > 0: cv.text('高回报，是从哪来的？', W / 2, 640, 52, 'serif_semi', col=CREAM, a=a * kh)
        for j, (lb, ts) in enumerate(items):
            k = eo((t - ts + 0.1) / 0.4) * ki
            if k <= 0: continue
            x = 220 + j * 320; y = 470
            cv.rrect(x - 120, y - 60, x + 120, y + 60, 10, C(40, 38, 36), a * k)
            cv.text(lb, x, y, 36, 'sans_med', col=CREAM, a=a * k)
            kx = eo((t - WT('c2c', '而是') + 0.2) / 0.4)
            if kx > 0: cv.line((x - 110, y), (x - 110 + 220 * kx, y), RED, a * k, 4)
        kr = eo((t - WT('c2c', '账上看不见') + 0.1) / 0.6)
        if kr > 0:
            seq(cv, t, WT('c2c', '账上看不见') - 0.2, t1, ['n_shop', 'm_counter', 'v_clerk'], h=562, a=a)
            k2 = eo((t - WT('c2c', '顾客买糖') + 0.1) / 0.5)
            if k2 > 0: cv.text('顾客的好名声', W / 2, 990, 64, 'serif_black', gold=True, a=a * kr * k2, glow=0.25, shadow=0.8)
        qcard(cv, 'qrep', t, WT('c2c', '好名声') - 0.2, t1, cy=1250, en=26, cn=32, typing=1.0)
        source(cv, '伯克希尔 1983 年致股东信附录《商誉及其摊销》', a, y=1462)
    # c2d：宁可要喜诗，也不要贵两三倍的糖 → 价格是你付出的，价值是你得到的
    t0, t1 = win('c2d')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['m_box', 'f_tray', 'f_rows2'], h=562, a=a)
        k = eo((t - WT('c2d', '宁可要喜诗') + 0.1) / 0.5)
        if k > 0 and t < WT('c2d', '他顺手') + 0.1:
            ka = k * (1 - eo((t - WT('c2d', '他顺手') + 0.2) / 0.3))
            cv.text('喜诗', 300, 1000, 48, 'serif_semi', col=GOLD_L, a=a * ka)
            cv.text('$', 300, 1100, 60, 'sans_bold', col=CREAM, a=a * ka)
            cv.text('别家', 780, 1000, 48, 'serif_semi', col=CREAM, a=a * ka)
            cv.text('$$ – $$$', 780, 1100, 60, 'sans_bold', col=CREAM, a=a * ka)
            cv.text('>', W / 2, 1050, 90, 'serif_black', gold=True, a=a * ka)
            note(cv, '巴菲特的看法：“we believe”', 1200, a * ka * 0.8, 22)
        qcard(cv, 'qprice', t, WT('c2d', '他顺手') + 0.1, t1, cy=1150, en=40, cn=44)
        source(cv, '伯克希尔 1983 年致股东信', a, y=1462)
    # c2e：几乎不需要钱周转：现款买卖、周期短
    t0, t1 = win('c2e')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['m_counter', 'f_pack', 'f_boxes'], h=562, a=a)
        cv.text('几乎不需要钱来周转', W / 2, 940, 44, 'serif_semi', col=CREAM, a=a)
        cx, cy, R = 280, 1190, 140
        p = (t - t0) * 0.45
        nodes = [('原料', -90), ('做糖', 0), ('门店', 90), ('现款', 180)]
        cv.circle((cx, cy), R, GOLD_D, a * 0.5, 2)
        for lb, ang in nodes:
            x, y = cx + R * math.cos(math.radians(ang)), cy + R * math.sin(math.radians(ang))
            disc(cv, (x, y), 48, C(40, 36, 32), a); cv.circle((x, y), 48, GOLD, a * 0.8, 2)
            cv.text(lb, x, y, 24, 'sans_med', col=CREAM, a=a)
        for k in range(5):
            ang = (p * 2 * math.pi + k * 2 * math.pi / 5)
            cv.glow_dot((cx + R * math.cos(ang), cy + R * math.sin(ang)), 8, GOLD_L, a)
        k1 = eo((t - WT('c2e', '现款买卖') + 0.1) / 0.5)
        if k1 > 0: chip(cv, '现款买卖 → 没有应收账款', 720, 1120, 28, a * k1, col=GOLD_L)
        k2 = eo((t - WT('c2e', '周期很短') + 0.1) / 0.5)
        if k2 > 0: chip(cv, '周期短 → 存货压钱少', 720, 1260, 28, a * k2, col=GOLD_L)
        note(cv, '循环图为示意', 1385, a * 0.7, 20)
        source(cv, '伯克希尔 2007 年致股东信', a, y=1462)
    # c2f：800 万资本 → 税前 400 多万：税前约 60%，税后约 25%
    t0, t1 = S('c2f') - 0.3, CH['tk_ch2'][0]
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        cv.text('每 100 美元的资本，一年赚多少？', W / 2, 340, 40, 'sans_med', col=CREAM, a=a)
        for j, (lb, v, ts, col) in enumerate([('税前', 60, WT('c2f', '税前回报率'), GOLD), ('税后', 25, WT('c2f', '税后也有'), GOLD * 0.7)]):
            e = eexp((t - ts) / 1.0)
            if e <= 0: continue
            cx = 360 + j * 360; base = 1080
            h = 600 * v / 60 * e
            gbar(cv, cx - 100, base - h, cx + 100, base, col, a, sheen_t=t - ts)
            cv.text(f'约 {int(round(v * e))}%', cx, base - h - 46, 56, 'sans_bold', col=GOLD_L if j == 0 else CREAM, a=a * min(1, e * 2), shadow=0.6)
            cv.text(lb, cx, base + 46, 32, 'sans_med', col=GREY, a=a * min(1, e * 2))
        source(cv, '伯克希尔 2007 年信（税前约 60%）；1983 年信（税后约 25%）', a, y=1462)


# ======================================================================== 第三章：涨价的底气
TABLE = [(1972, 31337, 16954, 167), (1975, 50492, 19134, 172), (1978, 73653, 22407, 182), (1981, 112578, 24052, 199), (1984, 135946, 24759, 214)]


def shot_ch3(cv, t):
    # c3a：唯一的洞察：没用出来的定价权
    t0, t1 = win('c3a')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['m_case', 'v_shelf', 'v_clerk'], h=562, a=a)
        qcard(cv, 'qpower', t, WT('c3a', '一个重要的洞察') - 0.2, t1, cy=1150, en=34, cn=40)
        source(cv, '伯克希尔 1991 年致股东信', a, y=1462)
    # c3b–c3e：1984 年原表：磅数、销售额、每磅价格 vs 通胀（以 1972 = 1 为基准）
    t0, t1 = S('c3b') - 0.3, S('c3f') + 0.35
    a = env(t, t0, t1, 0.4, 0.75)
    if a > 0:
        cv.text('喜诗历年数据 · 1972–1984', W / 2, 320, 36, 'sans_med', col=CREAM, a=a)
        cv.text('BERKSHIRE 1984 LETTER · SEE’S RECAP', W / 2, 362, 22, 'corm', col=GOLD, a=a, track=0.15)
        # 折线：以 1972 年 = 1
        x0, x1, base, top = 170, 900, 1180, 560
        vmax = 4.6
        Y = lambda v: base - (v - 0.0) / vmax * (base - top)
        X = lambda yr: x0 + (yr - 1972) / 12 * (x1 - x0)
        grid_lines(cv, x0 - 20, x1 + 20, base, top, a * 0.8)
        for v in (1, 2, 3, 4):
            cv.text(f'{v}×', x0 - 40, Y(v), 22, 'sans_light', col=GREY, a=a, anchor='r')
        for yr in (1972, 1976, 1980, 1984):
            cv.text(str(yr), X(yr), base + 36, 22, 'sans_light', col=GREY, a=a)
        cpi = {1972: 41.8, 1975: 53.8, 1978: 65.2, 1981: 90.9, 1984: 103.9}
        series = [('销量（磅）', [r[2] / TABLE[0][2] for r in TABLE], WT('c3b', '1972'), CREAM, '+46%'),
                  ('销售额', [r[1] / TABLE[0][1] for r in TABLE], S('c3c'), GOLD_L, '4.3×'),
                  ('每磅售价', [(r[1] / r[2]) / (TABLE[0][1] / TABLE[0][2]) for r in TABLE], S('c3d'), GOLD, '≈3×'),
                  ('美国物价（CPI）', [cpi[r[0]] / cpi[1972] for r in TABLE], WT('c3d', '同一时期'), C(140, 170, 220), '≈2.5×')]
        for j, (lb, vals, ts, col, end) in enumerate(series):
            e = eo((t - ts) / 1.6)
            if e <= 0: continue
            pts = [(X(TABLE[i][0]), Y(v)) for i, v in enumerate(vals)]
            n = 1 + e * (len(pts) - 1)
            i = int(n); f = n - i
            seg_ = pts[:i] + ([(lerp(pts[i - 1][0], pts[i][0], f), lerp(pts[i - 1][1], pts[i][1], f))] if i < len(pts) else [])
            if len(seg_) >= 2: cv.poly(seg_, col, a, 4 if j != 3 else 3)
            hx, hy = seg_[-1]
            cv.glow_dot((hx, hy), 9, col, a)
            if e > 0.98:
                cv.text(end, hx + 14, hy - 26, 34, 'sans_bold', col=col, a=a, anchor='l', shadow=0.6)
            cv.text(lb, 170 + (j % 2) * 380, 1290 + (j // 2) * 52, 28, 'sans_med', col=col, a=a * min(1, e * 3), anchor='l')
            cv.rect(140 + (j % 2) * 380, 1290 + (j // 2) * 52 - 4, 160 + (j % 2) * 380, 1290 + (j // 2) * 52 + 4, col, a * min(1, e * 3))
        k = eo((t - S('c3e') + 0.1) / 0.5)
        if k > 0: chip(cv, '涨价跑赢通胀，销量还在增长', W / 2, 480, 30, a * k, col=GOLD_L)
        source(cv, '伯克希尔 1984 年信原表（磅数、销售额；1984 年每磅 $5.49）；每磅售价与倍数为本片按原表推算；CPI-U 年均值：BLS', a, y=1462)
    # c3f：圣诞前 4 周：全年 40% 的生意、约 75% 的利润
    t0, t1 = win('c3f')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['n_boxes', 'n_shop', 'a_gift'], h=562, a=a)
        kt = eo((t - WT('c3f', '1984') + 0.1) / 0.5)
        cv.text('1984 年 · 圣诞节前的 4 个星期', W / 2, 935, 36, 'sans_med', col=GOLD_L, a=a * kt)
        k1 = eexp((t - WT('c3f', '40%') + 0.1) / 1.0) if '40%' in _SAY['c3f'] else eexp((t - WT('c3f', '百分之四十') + 0.1) / 1.0)
        k2 = eexp((t - WT('c3f', '75%') + 0.1) / 1.0) if '75%' in _SAY['c3f'] else eexp((t - WT('c3f', '百分之七十五') + 0.1) / 1.0)
        for j, (lb, v, k, col) in enumerate([('全年销量', 40, k1, GOLD * 0.7), ('全年利润', 75, k2, GOLD * 0.95)]):
            cx = 330 + j * 420; cy = 1120; R = 120
            kd = eo((t - WT('c3f', '圣诞节前') - j * 0.15) / 0.6)
            if kd <= 0: continue
            disc(cv, (cx, cy), R * (0.85 + 0.15 * kd), C(60, 56, 52), a * kd)
            cv.circle((cx, cy), R, GOLD_D, a * kd * 0.6, 2)
            if k > 0:
                ang1 = -math.pi / 2 + 2 * math.pi * v / 100 * k
                pts = [(cx, cy)] + [(cx + R * math.cos(-math.pi / 2 + (ang1 + math.pi / 2) * i / 40), cy + R * math.sin(-math.pi / 2 + (ang1 + math.pi / 2) * i / 40)) for i in range(41)]
                cv.fillpoly(pts, col, a)
                cv.text(f'{int(round(v * k))}%', cx, cy, 56, 'sans_bold', col=WHITE, a=a, shadow=0.8)
            cv.text(lb, cx, cy + R + 40, 30, 'sans_med', col=CREAM, a=a * kd)
        kg = eo((t - WT('c3f', '买来送人') + 0.1) / 0.5)
        if kg > 0:
            note(cv, '画面：1981 年圣地亚哥母亲节新闻；1988 年喜诗电视广告（送礼）。“买来送人”为本片解读', 1385, a * kg * 0.8, 20)
        source(cv, '伯克希尔 1984 年致股东信：“In the four weeks prior to Christmas, we do 40% of the year’s volume and earn about 75% of the year’s profits.”', a, y=1462)
    # c3g：停掉 14 款糖 → 几百封抗议信 → “愿你们的新松露巧克力在路上就化掉”
    t0, t1 = win('c3g')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, WT('c3g', '有一封信') - 0.2, ['a_box', 'm_case', 'f_tray'], h=562, a=a)
        k = eo((t - WT('c3g', '14') + 0.1) / 0.5) if '14' in _SAY['c3g'] else eo((t - WT('c3g', '十四') + 0.1) / 0.5)
        if k > 0:
            for i in range(14):
                x = 170 + (i % 7) * 123; y = 940 + (i // 7) * 110
                gone = i not in (3, 10)
                kk = eo((t - WT('c3g', '其中两款') + 0.1) / 0.4)
                disc(cv, (x, y), 36, C(110, 70, 46) if not gone or kk < 1 else C(60, 44, 36), a * k * (1 - (0.6 * kk if gone else 0)))
                if not gone and kk > 0: cv.circle((x, y), 46, GOLD_L, a * kk, 3)
        kl = eo((t - WT('c3g', '好几百封信') + 0.1) / 0.3)
        if kl > 0:
            for i in range(40):
                ph = ((t - WT('c3g', '好几百封信')) * 0.6 + i / 40) % 1.0
                x = 100 + (i * 197) % 880; y = 1300 - ph * 900
                envelope(cv, x, y, 0.55, a * kl * math.sin(ph * math.pi) * 0.9, rot=0.3 * math.sin(i))
        qcard(cv, 'qmelt', t, WT('c3g', '有一封信') - 0.2, t1, cy=1150, en=40, cn=42)
        source(cv, '伯克希尔 1987 年致股东信（删掉 14 款，其中 2 款被顾客强烈要求恢复，“many hundreds of letters”）', a, y=1462)
    # c3h：阿尔伯克基门店：263 位顾客
    t0, t1 = win('c3h')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['v_street', 'v_ext'], h=562, a=a, cap='喜诗门店（非阿尔伯克基店）')
        tag(cv, '1990 · 阿尔伯克基', t, t0 + 0.3, W / 2, 930, 30, GOLD, a)
        tw = WT('c3h', '两百六十三')
        p = eo((t - tw + 0.1) / 1.6)
        for i in range(int(263 * p)):
            r_, c_ = divmod(i, 33)
            disc(cv, (140 + c_ * 25, 1030 + r_ * 26), 8, GOLD_L, a * 0.9)
        if p > 0: cv.text(f'{int(263 * p)} 位顾客', W / 2, 1290, 44, 'sans_bold', col=GOLD_L, a=a * min(1, p * 3))
        k = eo((t - WT('c3h', '房东最后让了步') + 0.1) / 0.5)
        if k > 0: chip(cv, '房东让步 · 门店保住了', W / 2, 1370, 28, a * k, col=GOLD)
        source(cv, '伯克希尔 1990 年致股东信（店长 Ann Filkins 发动顾客，263 人来信来电）', a, y=1462)
    # c3i + c3j：定价权的边界
    t0, t1 = S('c3i') - 0.3, CH['tk_ch3'][0]
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        cv.text('定价权，不是想涨就涨', W / 2, 340, 50, 'serif_semi', col=CREAM, a=a)
        rows = [('1980 年代初', '同店销量连年下滑', WT('c3i', '同店销量'), RED),
                ('1985 年', '“只敢小幅提价”', WT('c3i', '只敢小幅提价'), CREAM),
                ('1988 年', '提价后，销售一度疲软', WT('c3i', '一九八八') if '一九八八' in _SAY['c3i'] else WT('c3i', '1988'), RED)]
        for j, (yr, txt, ts, col) in enumerate(rows):
            k = eo((t - ts + 0.1) / 0.5)
            if k <= 0: continue
            y = 520 + j * 150
            cv.text(yr, 160, y, 36, 'sans_bold', col=GOLD, a=a * k, anchor='l')
            cv.text(txt, 400, y, 38, 'sans_med', col=col if col is not RED else C(240, 140, 130), a=a * k, anchor='l')
            if j != 1:
                cv.text('↘', 940, y, 50, 'sans_bold', col=C(240, 140, 130), a=a * k)
        k = eo((t - S('c3j') + 0.1) / 0.6)
        if k > 0:
            cv.rrect(140, 1020, 940, 1300, 18, C(40, 30, 24), a * k * 0.9)
            cv.rrect(140, 1020, 940, 1300, 18, GOLD, a * k * 0.7, fill=False, th=2)
            cv.text('顾客的喜爱', W / 2, 1100, 50, 'serif_black', gold=True, a=a * k)
            cv.text('是定价权的来源，也是它的边界', W / 2, 1200, 36, 'sans_med', col=CREAM, a=a * k)
            note(cv, '本片解读', 1270, a * k * 0.8, 20)
        source(cv, '伯克希尔 1983、1985、1987 年致股东信', a, y=1462)


# ======================================================================== 第四章：一台只吐钱的机器
def shot_ch4(cv, t):
    # c4a：梦想生意的原型
    t0, t1 = win('c4a')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        doc_page(cv, t, t0, t1, 'BERKSHIRE HATHAWAY · 2007 LETTER TO SHAREHOLDERS',
                 ['Businesses – The Great, the Good', 'and the Gruesome', '', 'Let’s look at the prototype of a', 'dream business, our own See’s Candy.'],
                 cy=700, w=900, size=34, hl='prototype of a', hl_t=WT('c4a', '梦想生意'), a=a)
        big_q(cv, t, '“梦想生意的原型”', 1180, WT('c4a', '梦想生意'), 62, a)
        source(cv, '伯克希尔 2007 年致股东信', a, y=1462)
    # c4b：不起眼的行业：人均很少、不增长、四十年只有三家赚到像样利润
    t0, t1 = win('c4b')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('美国盒装巧克力行业', W / 2, 340, 40, 'sans_med', col=CREAM, a=a)
        p = eo((t - t0 - 0.3) / 1.4)
        x0, x1, y = 160, 920, 640
        cv.line((x0, y), (x0 + (x1 - x0) * p, y + 6 * math.sin(p * 9)), GREY, a, 4)
        cv.text('人均消费：很低，也不增长', W / 2, y - 70, 32, 'sans_light', col=GREY, a=a * p)
        k = eo((t - WT('c4b', '四十年来') + 0.1) / 0.5)
        if k > 0:
            for i in range(30):
                x = 180 + (i % 10) * 80; yy = 860 + (i // 10) * 110
                hl = i in (0, 13, 26)
                kk = eo((t - WT('c4b', '只有三家') - (0 if hl else 0.2)) / 0.5) if '只有三家' in _SAY['c4b'] else 0
                col = GOLD_L if hl and kk > 0 else C(90, 86, 80)
                disc(cv, (x, yy), 26 if hl else 20, col, a * k * (1 if hl else (1 - 0.6 * kk)))
            kk = eo((t - WT('c4b', '只有三家') + 0.1) / 0.5)
            if kk > 0: cv.text('只有 3 家赚到像样的利润', W / 2, 1230, 40, 'sans_bold', col=GOLD_L, a=a * kk)
            note(cv, '圆点为示意，不代表实际公司数', 1290, a * k * 0.8, 20)
        source(cv, '伯克希尔 2007 年致股东信', a, y=1462)
    # c4c：销量 1600 万磅 → 3100 万磅，每年约 2%
    t0, t1 = win('c4c')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['f_brittle', 'f_brittle2', 'f_workers'], h=562, a=a)
        cv.text('喜诗的销量（磅）', W / 2, 935, 34, 'sans_med', col=CREAM, a=a)
        rows = [('1972', 16, t0 + 0.3, GOLD * 0.6), ('2007', 31, WT('c4c', '2007') if '2007' in _SAY['c4c'] else t0 + 1.4, GOLD)]
        hbar(cv, t, rows, a, x0=230, x1=800, y0=1050, dy=120, vmax=34, fmt=lambda v: f'{v:.0f} 百万磅', size=38, lab=34, hl=1)
        k = eo((t - WT('c4c', '一年只增长') + 0.4) / 0.5)
        if k > 0: big_q(cv, t, '35 年，每年只增长约 2%', 1320, WT('c4c', '一年只增长') - 0.3, 48, a)
        source(cv, '伯克希尔 2007 年致股东信：“a growth rate of only 2% annually”', a, y=1462)
    # c4d：2007 年：销售 3.83 亿，税前 8200 万；经营所需资本 4000 万
    t0, t1 = win('c4d')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('喜诗 · 2007 年', W / 2, 340, 40, 'sans_med', col=CREAM, a=a)
        money(cv, t, WT('c4d', '销售额'), '$3.83 亿', 300, 560, 76, a, col=CREAM, sub='一年销售额')
        money(cv, t, WT('c4d', '税前利润'), '$8200 万', 780, 560, 76, a, sub='税前利润')
        k = eo((t - WT('c4d', '经营需要的资本') + 0.1) / 0.6)
        if k > 0:
            cv.line((140, 820), (940, 820), GOLD_D, a * k, 2)
            cv.text('经营需要的资本', W / 2, 900, 36, 'sans_med', col=CREAM, a=a * k)
            money(cv, t, WT('c4d', '经营需要的资本') + 0.5, '只有 $4000 万', W / 2, 1060, 96, a, sub='（1972 年为 $800 万）')
        source(cv, '伯克希尔 2007 年致股东信', a, y=1462)
    # c4e：35 年累计税前 13.5 亿，仅 3200 万留作再投入，其余全交伯克希尔
    t0, t1 = win('c4e')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('1972–2007 · 喜诗累计税前利润', W / 2, 330, 36, 'sans_med', col=CREAM, a=a)
        tc = WT('c4e', '十三点五亿')
        p = eexp((t - tc + 0.6) / 1.4)
        # 135 列 = 13.5 亿（每列 1000 万），其中 3.2 列（3200 万）留下
        x0, base, cw = 150, 1060, 5.6
        n = int(135 * p)
        for i in range(n):
            hcol = 520
            stay = i < 3.2
            col = CREAM * 0.8 if stay else GOLD
            cv.rect(x0 + i * cw, base - hcol, x0 + i * cw + cw - 1.2, base, col * (0.65 + 0.35 * ((i % 10) == 0)), a)
        if p > 0:
            money(cv, t, tc, '$13.5 亿', W / 2, 460, 96, a)
        ks = eo((t - WT('c4e', '三千二百万') + 0.1) / 0.5)
        if ks > 0:
            cv.line((x0 + 9, base + 20), (x0 + 9, base + 120), CREAM, a * ks, 3)
            chip(cv, '留下再投入：$3200 万', x0 + 180, base + 150, 28, a * ks, col=CREAM)
        kb = eo((t - WT('c4e', '其余的钱') + 0.1) / 0.6)
        if kb > 0:
            for k in range(14):
                ph = ((t - WT('c4e', '其余的钱')) * 0.7 + k / 14) % 1.0
                x = lerp(300 + (k * 47) % 600, W / 2, ph); y = lerp(800, 1340, eio(ph))
                cv.glow_dot((x, y), 8, GOLD_L, a * kb * math.sin(ph * math.pi))
            chip(cv, '其余全部交给伯克希尔', W / 2, 1340, 32, a * kb, col=GOLD_L)
        source(cv, '伯克希尔 2007 年致股东信：“pre-tax earnings have totaled $1.35 billion… except for the $32 million”（每格 = $1000 万）', a, y=1462)
    # c4f：一般公司要把利润从 500 万做到 8200 万，可能要投约 4 亿
    t0, t1 = win('c4f')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('利润从 $500 万做到 $8200 万，要投多少钱？', W / 2, 340, 36, 'sans_med', col=CREAM, a=a)
        rows = [('喜诗', 32, t0 + 0.4, GOLD_L), ('一般公司（巴菲特举例）', 400, WT('c4f', '可能得投进'), C(140, 150, 170))]
        vbars(cv, t, [(lb, v, ts, col, None) for lb, v, ts, col in rows], a, x0=200, x1=880, base=1180, hmax=640,
              fmt=lambda v: (f'${v / 100:.1f} 亿'.replace('.0 亿', ' 亿') if v >= 100 else f'${v * 100:,.0f} 万'.replace(',', '')), size=44, lab=28)
        note(cv, '喜诗：1972 年以来追加投入 $3200 万；一般公司为巴菲特举的例子，不是统计数', 1290, a * 0.85, 22)
        source(cv, '伯克希尔 2007 年致股东信：“require, say, $400 million or so of capital investment”', a, y=1462)
    # c4g + c4h：三种储蓄账户
    t0, t1 = S('c4g') - 0.3, win('c4h')[1]
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('三种“储蓄账户”', W / 2, 340, 50, 'serif_semi', col=CREAM, a=a)
        specs = [('最好的', '利率极高，还一年比一年高', WT('c4g', '最好的一种'), GOLD_L, 0.35, 0.0, 1.0, True),
                 ('不错的', '利率不错，新存的钱也拿这个利率', WT('c4g', '不错的一种'), GOLD * 0.8, 0.6, 0.5, 0.6, False),
                 ('最糟的', '利率太低，还得不停往里存', WT('c4g', '最糟的一种'), C(200, 110, 100), 0.8, 1.0, 0.15, False)]
        for j, (lb, sub, ts, col, fill, ain, aout, rising) in enumerate(specs):
            k = eo((t - ts + 0.1) / 0.5)
            if k <= 0: continue
            cx = 220 + j * 320
            jar(cv, t, cx, 1040, 220, 340, fill, a * k, col=col, label=lb, arrow_in=ain * k, arrow_out=aout * k, rising=rising)
            for i, ln in enumerate(split_balanced(sub, 'sans_light', 24, 260)):
                cv.text(ln, cx, 1140 + i * 32, 24, 'sans_light', col=CREAM, a=a * k)
        k1 = eo((t - S('c4h') + 0.1) / 0.5)
        if k1 > 0: chip(cv, '喜诗', 220, 1270, 34, a * k1, col=GOLD_L)
        k2 = eo((t - WT('c4h', '航空公司') + 0.1) / 0.5)
        if k2 > 0: chip(cv, '航空公司', 860, 1270, 34, a * k2, col=C(220, 130, 120))
        k3 = eo((t - WT('c4h', '长得很快') + 0.1) / 0.5)
        if k3 > 0: chip(cv, '长得快 · 要砸钱 · 不赚钱', 640, 1340, 26, a * k3, col=C(220, 130, 120))
        source(cv, '伯克希尔 2007 年致股东信：the great（利率极高且逐年升高）/ the good（新存入的钱也按这个利率）/ the gruesome（利率太低还得不停存）；“Think airlines.”', a, y=1462)
    # c4i + c4j：钱拿去买别的好生意（亚当与夏娃）；也是买 BNSF 的一部分本钱
    t0, t1 = S('c4i') - 0.3, win('c4j')[1]
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        root = (W / 2, 1200)
        candy_box(cv, root[0], root[1], 0.42, a, lid=0.0, glow=0.4)
        p = (t - S('c4i') - 1.2) / 3.5
        rng = np.random.default_rng(11)
        nodes = [root]; edges = []
        lv = [[root]]
        for depth in range(3):
            nxt_ = []
            for (x, y) in lv[-1]:
                for s_ in (-1, 1):
                    spread = 230 / (depth + 1)
                    nx_, ny_ = x + s_ * spread + rng.normal(0, 12), y - 190
                    edges.append(((x, y), (nx_, ny_), depth)); nxt_.append((nx_, ny_))
            lv.append(nxt_)
        for (p0, p1, d) in edges:
            k = cl(p * 3 - d)
            if k <= 0: continue
            q = (lerp(p0[0], p1[0], k), lerp(p0[1], p1[1], k))
            cv.line(p0, q, GOLD * 0.8, a * 0.9, 3)
            if k >= 1:
                disc(cv, p1, 18 - 3 * d, GOLD_L, a)
                cv.glow_dot(p1, 14, GOLD_L, a * 0.5)
        k1 = eo((t - WT('c4i', '买别的好生意') + 0.1) / 0.5)
        kj = 1 - eo((t - S('c4j') + 0.3) / 0.4)
        if k1 > 0: cv.text('交完税 → 去买别的好生意', W / 2, 400, 38, 'sans_med', col=CREAM, a=a * k1 * kj)
        k2 = eo((t - WT('c4i', '亚当和夏娃') + 0.1) / 0.5)
        if k2 > 0: cv.text('“就像亚当和夏娃”', W / 2, 470, 40, 'serif_semi', col=GOLD_L, a=a * k2 * kj)
        kb = eo((t - WT('c4j', 'B N S F') + 0.1) / 0.6) if 'B N S F' in _SAY['c4j'] else eo((t - WT('c4j', 'BNSF') + 0.1) / 0.6)
        if kb > 0:
            # 一列火车从右侧驶入顶部
            y = 470
            for k in range(8):
                x = 1100 - 700 * eo(kb) + k * 100
                cv.rrect(x, y - 30, x + 90, y + 30, 8, C(60, 70, 90) if k else C(200, 120, 40), a)
                disc(cv, (x + 22, y + 34), 10, GREY, a); disc(cv, (x + 68, y + 34), 10, GREY, a)
            cv.line((0, y + 46), (W, y + 46), GREY, a * 0.6, 2)
            chip(cv, 'BNSF 铁路（2010 年买下）', W / 2, 380, 30, a * kb, col=GOLD)
        note(cv, '示意：分枝代表伯克希尔用这些钱买下的其他生意', 1300, a * 0.8, 22)
        source(cv, '伯克希尔 2007 年致股东信（Adam and Eve）；2010 年致股东信（“part of the stake we needed to buy BNSF”）', a, y=1462)


# ======================================================================== 第五章：芒格把我扳了过来
def shot_ch5(cv, t):
    # c5a：吐出的最值钱的东西，是思路
    t0, t1 = win('c5a', pre=0.1)
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        candy_box(cv, W / 2, 760, 0.9, a, lid=1.0)
        k = eo((t - WT('c5a', '巴菲特的思路') + 0.1) / 0.7)
        for i in range(30):
            ph = ((t - t0) * 0.4 + i / 30) % 1.0
            x = W / 2 + math.sin(i * 1.7) * 120 * ph; y = 700 - ph * 300
            cv.text('$', x, y, 30, 'sans_bold', col=GOLD_L, a=a * (1 - k) * math.sin(ph * math.pi))
        if k > 0:
            cv.glow_dot((W / 2, 480), 120, BLUE_L, a * k * 0.5)
            cv.text('思路', W / 2, 480, 110, 'serif_black', gold=True, a=a * k, glow=0.3)
        note(cv, '本片解读', 1100, a * 0.7, 20)
    # c5b + c5c：格雷厄姆的“烟蒂”；五十年代最好的十年；钱一多就不管用
    t0, t1 = S('c5b') - 0.3, win('c5c')[1]
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        kp = 1 - eo((t - S('c5c') + 0.3) / 0.5)
        if kp > 0:
            seq(cv, t, t0, S('c5c') - 0.1, ['k_tin', 'k_light'], h=562, a=a * kp, cap='示意')
            tag(cv, '“烟蒂”投资法 · 格雷厄姆教的', t, S('c5b') + 0.2, W / 2, 950, 32, GOLD, a * kp)
            qcard(cv, 'qcigar', t, WT('c5b', '只剩最后一口') - 0.3, S('c5c') - 0.2, cy=1200, en=26, cn=32, typing=1.0)
        kc = eo((t - S('c5c') + 0.1) / 0.5)
        if kc > 0:
            cv.text('五十年代：他一生里最好的十年', W / 2, 400, 42, 'serif_semi', col=GOLD_L, a=a * kc)
            # 资金规模 ↑ → 烟蒂法的效果 ↓
            x0, x1, base, top = 200, 900, 1150, 560
            cv.line((x0, base), (x1, base), GREY, a * kc, 2); cv.line((x0, base), (x0, top), GREY, a * kc, 2)
            cv.text('管理的资金规模 →', x1, base + 40, 26, 'sans_light', col=GREY, a=a * kc, anchor='r')
            cv.text('烟蒂法的效果', x0 + 10, top - 30, 26, 'sans_light', col=GREY, a=a * kc, anchor='l')
            pe = eo((t - WT('c5c', '钱一多') + 0.1) / 1.2)
            pts = [(x0 + (x1 - x0) * u, top + 40 + (base - top - 60) * (u ** 2)) for u in np.linspace(0, max(pe, 0.01), 30)]
            if len(pts) > 1: cv.poly(pts, C(230, 140, 120), a * kc, 4)
            if pe > 0.45: chip(cv, '钱一多，就不管用了', 640, 760, 30, a * kc * eo((pe - 0.45) / 0.3), col=C(230, 140, 120))
            note(cv, '示意', 1210, a * kc * 0.7, 20)
        source(cv, '伯克希尔 2014 年致股东信（“Ben Graham had taught me that technique”）；1989 年致股东信（“cigar butt”）', a, y=1462)
    # c5c2：引入芒格原声（HBO 纪录片访谈）
    t0, t1 = S('c5c2') - 0.3, S('sot_mlousy') - SEG['sot_mlousy']['lead'] - SOT_FADE
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        k = eo((t - t0) / 0.6)
        cv.text('查理·芒格', W / 2, 640, 96, 'serif_black', gold=True, a=a * k, glow=0.2)
        cv.text('CHARLIE MUNGER', W / 2, 740, 30, 'corm', col=GOLD, a=a * k, track=0.3)
        tag(cv, '纪录片《成为沃伦·巴菲特》（HBO，2017）· 芒格访谈', t, WT('c5c2', '纪录片') if '纪录片' in _SAY['c5c2'] else t0 + 0.5, W / 2, 900, 28, GOLD_L, a)
        big_q(cv, t, '他怎么回忆喜诗？', 1100, WT('c5c2', '回忆过') - 0.6, 56, a, col=CREAM)
    # c5d + c5e：2014 年“Charlie Straightens Me Out”→ 蓝图
    t0, t1 = S('c5d') - 0.3, win('c5e')[1]
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        kd = 1 - eo((t - WT('c5e', '芒格给他的蓝图') + 0.4) / 0.5)
        if kd > 0:
            doc_page(cv, t, t0, t1, 'BERKSHIRE HATHAWAY · 2014 LETTER · 50 YEARS',
                     ['Charlie Straightens Me Out', '', 'It took Charlie Munger to break', 'my cigar-butt habits…'],
                     cy=700, w=900, size=40, hl='Charlie Straightens Me Out', hl_t=WT('c5d', '芒格把我扳了过来'), a=a * kd)
            big_q(cv, t, '芒格把我扳了过来', 1180, WT('c5d', '芒格把我扳了过来'), 66, a * kd)
        kb = eo((t - WT('c5e', '芒格给他的蓝图') + 0.1) / 0.6)
        if kb > 0:
            blueprint(cv, 110, 420, 970, 1300, a * kb)
            cv.text('BLUEPRINT · 芒格给的蓝图', W / 2, 480, 30, 'sans_med', col=C(200, 225, 255), a=a * kb, track=0.1)
            k1 = eo((t - WT('c5e', '忘掉') + 0.1) / 0.5)
            if k1 > 0:
                cv.text('普通生意  ×  好价格', W / 2, 700, 56, 'serif_semi', col=C(200, 220, 250), a=a * kb * k1)
                kx = eo((t - WT('c5e', '改成') + 0.1) / 0.4)
                if kx > 0: cv.line((260, 700), (260 + 560 * kx, 700), RED, a * kb, 6)
            k2 = eo((t - WT('c5e', '改成') + 0.1) / 0.5)
            if k2 > 0:
                cv.text('好生意  ×  合理价格', W / 2, 960, 70, 'serif_black', gold=True, a=a * kb * k2, glow=0.25)
                cv.line((240, 1030), (840, 1030), GOLD, a * kb * k2, 3)
        source(cv, '伯克希尔 2014 年致股东信，小节“Charlie Straightens Me Out”', a, y=1462)
    # c5g + c5g2：“你很聪明，而我是对的” → 芒格去世，差 33 天满一百岁 → 引入原声
    t0, t1 = S('c5g') - 0.3, S('sot_munger') - SEG['sot_munger']['lead'] - SOT_FADE
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        kq = 1 - eo((t - S('c5g2') + 0.3) / 0.4)
        if kq > 0:
            if not pic(cv, ['buffett_munger', 'buffett_munger2', 'munger'], t, t0, S('c5g2'), cap='巴菲特与芒格', focus=(0.5, 0.45)):
                photo_win(cv, 'brk_meeting_2025', t, t0, S('c5g2'), cap='伯克希尔股东大会（2025 年照片）', focus=(0.5, 0.45))
            qcard(cv, 'qsmart', t, S('c5g') + 0.8, S('c5g2') - 0.1, cy=1130, en=32, cn=38)
        k2 = eo((t - S('c5g2') + 0.1) / 0.6)
        if k2 > 0:
            cv.text('查理·芒格', W / 2, 560, 80, 'serif_black', gold=True, a=a * k2, glow=0.2)
            cv.text('1924 — 2023', W / 2, 680, 50, 'oswald', col=CREAM, a=a * k2, track=0.2)
            kk = eo((t - WT('c5g2', '三十三天') + 0.1) / 0.5)
            if kk > 0: cv.text('离一百岁只差 33 天', W / 2, 780, 40, 'sans_med', col=GREY, a=a * k2 * kk)
            k3 = eo((t - WT('c5g2', '二零二六年') + 0.1) / 0.5)
            if k3 > 0:
                seq(cv, t, WT('c5g2', '二零二六年') - 0.2, t1, ['c_two_c'], cy=1080, h=420)
                tag(cv, '2026 年 7 月 15 日 · CNBC 专访', t, WT('c5g2', '二零二六年'), W / 2, 1385, 26, GOLD, a)
        source(cv, '伯克希尔 2014 年致股东信；2023 年致股东信（“Charlie Munger died on November 28, just 33 days before his 100th birthday.”）', a, y=1462)
    # c5i：喜诗成了课堂（1991）
    t0, t1 = S('c5i') - 0.3, win('c5i')[1]
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        seq(cv, t, t0, t1, ['x_bwb_desk', 'x_bwb_office'], h=562, a=a)
        tag(cv, '喜诗 = 一间课堂', t, S('c5i') + 0.2, W / 2, 950, 32, GOLD, a)
        qcard(cv, 'qlessons', t, WT('c5i', '靠这些经验') - 0.4, t1, cy=1180, en=30, cn=36)
        source(cv, '伯克希尔 1991 年致股东信', a, y=1462)
    # c5j：他没在信里点名 → 芒格原声
    t0, t1 = S('c5j') - 0.3, S('sot_mcoke') - SEG['sot_mcoke']['lead'] - SOT_FADE
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        big_q(cv, t, '是哪些股票？', 720, S('c5j') + 0.2, 80, a)
        tag(cv, '芒格在同一段访谈里说', t, WT('c5j', '芒格'), W / 2, 920, 30, GOLD_L, a)
    # c5k：2011 年信原文 “Buy commodities, sell brands”（引用的商业公式）→ 可口可乐 1886 年起 → 规模小一些，喜诗也是
    t0, t1 = S('c5k') - 0.3, win('c5k')[1] + 0.25
    a = env(t, t0, t1, 0.4, 0.5)
    if a > 0:
        tc = WT('c5k', '可口可乐从')
        kd = 1 - eo((t - tc + 0.2) / 0.5)
        if kd > 0:
            doc_page(cv, t, t0, tc + 0.3, 'BERKSHIRE HATHAWAY · 2011 LETTER TO SHAREHOLDERS',
                     ['“Buy commodities, sell brands” has', 'long been a formula for business', 'success. It has produced enormous',
                      'and sustained profits for Coca-Cola', 'since 1886…'],
                     cy=720, w=900, size=34, hl='Buy commodities, sell brands', hl_t=WT('c5k', '买进大宗商品'), a=a * kd)
            k1 = eo((t - WT('c5k', '买进大宗商品') - 0.3) / 0.5)
            if k1 > 0: big_q(cv, t, '“买进大宗商品，卖出品牌”', 1180, WT('c5k', '买进大宗商品') + 0.4, 54, a * kd)
        kp = eo((t - tc + 0.3) / 0.5)
        if kp > 0:
            photo_win(cv, 'coke_bottles', t, tc - 0.3, t1, cap='可口可乐', focus=(0.5, 0.5), a=a)
            chip(cv, '可口可乐 · 1886 年起', 330, 960, 32, a * kp, col=GOLD_L)
            ks = eo((t - WT('c5k', '规模小一些') + 0.1) / 0.5)
            if ks > 0:
                chip(cv, '喜诗 · 规模小一些，也是', 760, 960, 32, a * ks, col=GOLD)
                candy_box(cv, 760, 1170, 0.5, a * ks, lid=1.0)
            k2 = eo((t - WT('c5k', '可口可乐从') - 0.2) / 0.5)
            if k2 > 0:
                pts = [(330 - 18, 1080), (330 + 18, 1080), (330 + 22, 1120), (330 + 48, 1170), (330 + 44, 1250), (330 + 50, 1280),
                       (330 - 50, 1280), (330 - 44, 1250), (330 - 48, 1170), (330 - 22, 1120)]
                cv.poly(pts + [pts[0]], C(200, 210, 200), a * k2, 3)       # 自绘瓶形轮廓（不是商标）
        source(cv, '伯克希尔 2011 年致股东信：“Buy commodities, sell brands” has long been a formula for business success… Coca-Cola since 1886… See’s Candy', a, y=1462)
    # c5k2：本片解读——买进的是谁都能买到的原料，卖出的是顾客认准的牌子（慢一点：原料 → 工厂 → 顾客认准的盒子）
    t0, t1 = S('c5k2') - 0.25, CH['tk_ch5'][0] + 0.2
    a = env(t, t0, t1, 0.45, 0.4)
    if a > 0:
        cv.text('买进的', 270, 360, 40, 'sans_med', col=GREY, a=a)
        cv.text('卖出去的', 810, 360, 40, 'sans_med', col=GOLD_L, a=a * eo((t - WT('c5k2', '卖出去的') + 0.1) / 0.5))
        # 左：一堆没有名字的原料（灰色方块，谁都能买到）
        rng = np.random.default_rng(3)
        for i in range(18):
            x = 170 + (i % 6) * 40 + rng.uniform(-6, 6); y = 760 - (i // 6) * 40 + rng.uniform(-4, 4)
            ki = eo((t - t0 - 0.2 - i * 0.04) / 0.4)
            cv.rect(x, y, x + 34, y + 34, C(120, 116, 110), a * ki)
        cv.text('谁都能买到的原料', 270, 880, 32, 'sans_med', col=CREAM, a=a * eo((t - t0 - 0.5) / 0.5))
        # 中：箭头流过（金色光点从左往右）
        kf = eo((t - WT('c5k2', '卖出去的') + 0.6) / 0.6)
        if kf > 0:
            cv.line((420, 700), (620, 700), GOLD_D, a * kf, 3)
            cv.fillpoly([(620, 686), (646, 700), (620, 714)], GOLD_D, a * kf)
            for k in range(4):
                ph = ((t - t0) * 0.5 + k / 4) % 1.0
                cv.glow_dot((420 + 220 * ph, 700), 7, GOLD_L, a * kf * math.sin(ph * math.pi))
        # 右：顾客认准的那个盒子（喜诗）
        kb = eo((t - WT('c5k2', '卖出去的') + 0.1) / 0.6)
        if kb > 0:
            candy_box(cv, 810, 700, 0.62, a * kb, lid=1.0, glow=0.4)
            cv.text('顾客认准的那个牌子', 810, 880, 32, 'sans_bold', col=GOLD_L, a=a * kb)
        kq = eo((t - WT('c5k2', '卖出去的') - 0.9) / 0.6)
        if kq > 0:
            cv.rrect(140, 1020, 940, 1280, 18, C(40, 30, 24), a * kq * 0.9)
            cv.rrect(140, 1020, 940, 1280, 18, GOLD, a * kq * 0.7, fill=False, th=2)
            cv.text('多付的钱，付给的是“认准”', W / 2, 1110, 44, 'serif_black', gold=True, a=a * kq)
            cv.text('这就是 1972 年那 1700 万“商誉”背后的东西', W / 2, 1195, 30, 'sans_med', col=CREAM, a=a * kq)
        note(cv, '本片解读 · 方块为示意', 1385, a * 0.7, 20)
        source(cv, '依据伯克希尔 2011 年致股东信（“Buy commodities, sell brands”）；1983 年信附录（商誉）', a, y=1462)


# ======================================================================== 第六章：喜诗做不到的事
def shot_ch6(cv, t):
    t0, t1 = S('c6a') - 0.3, CH['tk_ch6'][0]
    a = env(t, t0, t1, 0.4, 0.3)
    if a <= 0: return
    cv.text('喜诗做不到的事', W / 2, 330, 50, 'serif_semi', col=CREAM, a=a)
    # 一：长不大
    k1 = eo((t - S('c6b') + 0.1) / 0.5)
    k1o = 1 - eo((t - S('c6c') + 0.3) / 0.4)
    if k1 > 0 and k1o > 0:
        aa = a * k1 * k1o
        chip(cv, '一 · 长不大', W / 2, 450, 34, aa, col=GOLD)
        for j in range(4):
            x = 210 + j * 220
            kk = eo((t - WT('c6b', '扩大规模') - j * 0.35) / 0.5)
            cv.rrect(x - 80, 640, x + 80, 820, 10, C(46, 40, 34), aa * kk)
            cv.text('扩张尝试', x, 700, 26, 'sans_light', col=CREAM, a=aa * kk)
            kx = eo((t - WT('c6b', '白费力气') - j * 0.15) / 0.35)
            if kx > 0: cv.text('✕', x, 770, 60, 'sans_bold', col=C(230, 120, 110), a=aa * kx)
        qcard(cv, 'qfutile', t, WT('c6b', '白费力气') - 0.2, S('c6c') - 0.2, cy=1100, en=34, cn=38, a=k1o)
    # 二：一个地方、一个季节
    k2 = eo((t - S('c6c') + 0.1) / 0.5)
    k2o = 1 - eo((t - S('c6c2') + 0.3) / 0.4)
    if k2 > 0 and k2o > 0:
        aa = a * k2 * k2o
        chip(cv, '二 · 离不开一个地方、一个季节', W / 2, 450, 32, aa, col=GOLD)
        kc = eo((t - WT('c6c', '加州') + 0.1) / 0.6)
        cx, cy, R = 300, 780, 170
        disc(cv, (cx, cy), R, C(60, 56, 52), aa)
        if kc > 0:
            ang1 = -math.pi / 2 + 2 * math.pi * 0.8 * kc
            pts = [(cx, cy)] + [(cx + R * math.cos(-math.pi / 2 + (ang1 + math.pi / 2) * i / 40), cy + R * math.sin(-math.pi / 2 + (ang1 + math.pi / 2) * i / 40)) for i in range(41)]
            cv.fillpoly(pts, GOLD * 0.85, aa)
            cv.text('近 80%', cx, cy, 52, 'sans_bold', col=WHITE, a=aa, shadow=0.8)
        cv.text('销售来自加州（1991）', cx, cy + R + 46, 26, 'sans_med', col=CREAM, a=aa)
        km = eo((t - WT('c6c', '利润集中') + 0.1) / 0.6)
        if km > 0:
            x0 = 560
            for m_ in range(12):
                v = [0.2, 0.9, 0.3, 0.7, 0.2, -0.25, -0.35, -0.3, -0.1, 0.2, 0.5, 3.0][m_]
                h = 50 * v * km
                x = x0 + m_ * 34
                col = GOLD_L if m_ == 11 else (C(220, 120, 110) if v < 0 else GOLD * 0.6)
                cv.rect(x, 860 - max(h, 0), x + 24, 860 - min(h, 0), col, aa)
            cv.line((x0 - 10, 860), (x0 + 12 * 34, 860), GREY, aa, 2)
            cv.text('圣诞', x0 + 11 * 34 + 12, 880 + 22, 22, 'sans_light', col=GOLD_L, a=aa)
            ks = eo((t - WT('c6c', '夏天几个月') + 0.1) / 0.5)
            if ks > 0: cv.text('夏天亏钱（2001 年信）', x0 + 6 * 34 + 12, 930, 24, 'sans_light', col=C(220, 120, 110), a=aa * ks)
            note(cv, '月度柱为示意形状，不是实际数据', 1020, aa * 0.8, 20)
    # 二（续）：三十多年后，2025 年 10-K
    k25 = eo((t - S('c6c2') + 0.1) / 0.5)
    k25o = 1 - eo((t - S('c6d') + 0.3) / 0.4)
    if k25 > 0 and k25o > 0:
        aa = a * k25 * k25o
        seq(cv, t, S('c6c2') - 0.2, S('c6d') - 0.1, ['v_street', 'v_shelf', 'm_case'], cy=740, w=900, h=480, a=aa)
        cv.text('伯克希尔 2025 年年报（10-K）', W / 2, 1090, 30, 'sans_med', col=GOLD, a=aa)
        k1_ = eo((t - WT('c6c2', '两百五十家') + 0.1) / 0.5)
        if k1_ > 0: cv.text('约 250 家门店 · 主要在加州和美国西部', W / 2, 1175, 38, 'sans_bold', col=CREAM, a=aa * k1_)
        k2_ = eo((t - WT('c6c2', '一年大约一半') + 0.1) / 0.5)
        if k2_ > 0: cv.text('一年约一半收入 · 来自第四季度', W / 2, 1255, 38, 'sans_bold', col=GOLD_L, a=aa * k2_)
    # 三：价值要靠伯克希尔来实现（独立公司 vs 伯克希尔内部调配）
    k3 = eo((t - S('c6d') + 0.1) / 0.5)
    if k3 > 0:
        aa = a * k3
        chip(cv, '三 · 价值要靠伯克希尔来实现', W / 2, 450, 32, aa, col=GOLD)
        for j, (lb, x, leak) in enumerate([('留在伯克希尔', 290, False), ('如果是独立公司', 790, True)]):
            kk = eo((t - (S('c6d') + 0.3 if j == 0 else WT('c6d', '独立的公司')) + 0.1) / 0.5)
            if kk <= 0: continue
            candy_box(cv, x, 640, 0.42, aa * kk, lid=0.0)
            cv.text(lb, x, 760, 30, 'sans_med', col=CREAM, a=aa * kk)
            for i in range(10):
                ph = ((t - S('c6d')) * 0.6 + i / 10) % 1.0
                y = lerp(800, 1180, ph)
                lost = leak and i % 3 != 0 and ph > 0.4
                xx = x + (math.sin(i * 3) * 120 * (ph - 0.4) * 2 if lost else 0)
                cv.glow_dot((xx, y), 9, C(220, 120, 110) if lost else GOLD_L, aa * kk * math.sin(ph * math.pi))
            cv.text('→ 投到别的好生意' if not leak else '→ 分给股东再投', x, 1230, 26, 'sans_light', col=GOLD_L if not leak else CREAM, a=aa * kk)
            if leak:
                kl = eo((t - WT('c6d', '摩擦成本') + 0.1) / 0.5)
                if kl > 0: cv.text('税 · 摩擦成本', x + 150, 1020, 26, 'sans_med', col=C(230, 130, 120), a=aa * kk * kl)
        ke = eo((t - S('c6e') + 0.1) / 0.5)
        if ke > 0:
            cv.text('赚来的钱，有没有人能用好', W / 2, 1320, 40, 'serif_semi', col=GOLD_L, a=aa * ke)
            note(cv, '本片解读', 1380, aa * ke * 0.8, 20)
    src_ = ('伯克希尔 2025 年 10-K（约 250 家门店，约一半收入在第四季度）' if S('c6c2') - 0.3 <= t < S('c6d') - 0.3 else
            '伯克希尔 2014 年致股东信（扩张“largely futile”；独立公司的税与摩擦成本）；1991 年信（近 80% 在加州）；2001 年信（夏季亏损）')
    source(cv, src_, a, y=1462)


# ======================================================================== 第七章：一盒糖的学费
def shot_ch7(cv, t):
    # c7a：一百多岁 → 顾客就是老板 → “别乱动我的糖”
    t0, t1 = win('c7a', pre=0.1)
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        seq(cv, t, t0, t1, ['v_ext', 'v_clerk', 'm_counter', 'v_wall'], h=562, a=a)
        k = eo((t - t0 - 0.2) / 0.6)
        cv.text('100+', 300, 1000, 110, 'oswald', col=GOLD, a=a * k * (1 - eo((t - WT('c7a', '顾客就是老板') + 0.4) / 0.4)), glow=0.2)
        cv.text('年', 300, 1100, 34, 'sans_med', col=CREAM, a=a * k * (1 - eo((t - WT('c7a', '顾客就是老板') + 0.4) / 0.4)))
        tag(cv, '顾客就是老板', t, WT('c7a', '顾客就是老板'), 760, 1000, 40, GOLD_L, a * (1 - eo((t - WT('c7a', '别乱动') + 0.6) / 0.4)))
        qcard(cv, 'qcandy', t, WT('c7a', '别乱动') - 0.4, t1, cy=1130, en=54, cn=50)
        source(cv, '伯克希尔 2020 年致股东信', a, y=1462)
    # c7b2：一年只长 2% 的梦想生意 → 好生意的标准：每多赚一块钱，要多投多少钱
    t0, t1 = win('c7b2')
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        cv.text('好生意的标准', W / 2, 360, 54, 'serif_semi', col=CREAM, a=a)
        k0 = eo((t - t0 - 0.2) / 0.5)
        cv.text('喜诗：一年只长约 2%', 300, 560, 36, 'sans_med', col=GREY, a=a * k0)
        kd = eo((t - WT('c7b2', '梦想生意') + 0.1) / 0.5)
        if kd > 0: cv.text('却是“梦想生意”', 780, 560, 40, 'serif_black', gold=True, a=a * kd)
        k1 = eo((t - WT('c7b2', '不是看它长得多快') + 0.1) / 0.5)
        if k1 > 0:
            cv.text('长得多快？', W / 2, 760, 56, 'serif_semi', col=GREY, a=a * k1)
            kx = eo((t - WT('c7b2', '而是') + 0.1) / 0.4)
            if kx > 0: cv.line((W / 2 - 150, 762), (W / 2 - 150 + 300 * kx, 762), RED, a * k1, 6)
        k2 = eo((t - WT('c7b2', '每多赚一块钱') + 0.1) / 0.5)
        if k2 > 0:
            cv.text('每多赚 1 块钱，要多投多少钱？', W / 2, 920, 56, 'serif_black', gold=True, a=a * k2, glow=0.2)
            cv.line((180, 990), (900, 990), GOLD, a * k2, 3)
            cv.text('喜诗：税前利润从约 $500 万做到 $8200 万', W / 2, 1110, 32, 'sans_med', col=CREAM, a=a * k2)
            cv.text('只多投了 $3200 万', W / 2, 1180, 40, 'sans_bold', col=GOLD_L, a=a * k2)
            note(cv, '本片解读（依据 2007 年致股东信）', 1290, a * k2 * 0.8, 20)
        source(cv, '伯克希尔 2007 年致股东信（年增约 2%；“prototype of a dream business”；1972 年以来再投入 $3200 万）', a, y=1462)
    # c7c：引入原声（双人景）
    t0, t1 = S('c7c') - 0.3, S('sot_trick') - SEG['sot_trick']['lead'] - SOT_FADE
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        seq(cv, t, t0, t1, ['c_two_b'], h=562)
        tag(cv, '2026 年 7 月 15 日 · CNBC 专访', t, t0 + 0.3, W / 2, 935, 26, GOLD, a)
        # 1972 → 2026：同一个道理讲了 54 年
        kl = eo((t - WT('c7c', '95 岁') + 0.1) / 1.2)
        if kl > 0:
            y = 1090
            cv.line((200, y), (200 + 680 * kl, y), GOLD_D, a, 3)
            disc(cv, (200, y), 12, GOLD, a); cv.text('1972', 200, y - 46, 34, 'oswald', col=GOLD, a=a)
            cv.text('买下喜诗', 200, y + 46, 26, 'sans_light', col=CREAM, a=a)
            if kl > 0.98:
                disc(cv, (880, y), 12, GOLD_L, a); cv.text('2026', 880, y - 46, 34, 'oswald', col=GOLD_L, a=a)
                cv.text('95 岁', 880, y + 46, 26, 'sans_light', col=CREAM, a=a)
        big_q(cv, t, '同一个道理 ——', 1250, WT('c7c', '同一个道理') - 0.3, 52, a, col=CREAM)
    # c7d：500 万的学费 → 看得见品牌价值的眼睛
    t0, t1 = S('c7d') - 0.3, CH['end'][0] + 0.3
    a = env(t, t0, t1, 0.4, 0.5)
    if a > 0:
        k = eo((t - t0) / 0.8)
        cv.text('1972', W / 2, 400, 70, 'oswald', col=GOLD, a=a * k)
        tw = WT('c7d', '500') if '500' in _SAY['c7d'] else WT('c7d', '犹豫过')
        kp = eo((t - tw + 0.1) / 0.5)
        if kp > 0:
            cv.text('$3000 万  −  $2500 万  =  $500 万', W / 2, 560, 46, 'sans_bold', col=CREAM, a=a * kp)
        ke = eo((t - WT('c7d', '眼睛') + 0.1) / 0.8)
        cb = 1 - ke
        if cb > 0.01: candy_box(cv, W / 2, 860, 0.9, a * k * cb, lid=1.0, glow=0.3)
        if ke > 0:
            cx, cy = W / 2, 860
            w = 260 * ke
            top = [(cx - 300 + x, cy - math.sin(x / 600 * math.pi) * w * 0.55) for x in np.linspace(0, 600, 40)]
            bot = [(cx - 300 + x, cy + math.sin(x / 600 * math.pi) * w * 0.55) for x in np.linspace(0, 600, 40)]
            cv.poly(top, GOLD_L, a, 4); cv.poly(bot, GOLD_L, a, 4)
            disc(cv, (cx, cy), 100 * ke, GOLD, a * 0.5)
            candy_box(cv, cx, cy, 0.3 * ke, a * ke, lid=1.0)
            cv.glow_dot((cx, cy), 200, GOLD_L, a * ke * 0.4)
            cv.text('看得见品牌价值的眼睛', W / 2, 1180, 56, 'serif_black', gold=True, a=a * ke, glow=0.25)
        source(cv, '伯克希尔 2014 年致股东信：“I gained a business education about the value of powerful brands that opened my eyes…”', a, y=1462)
