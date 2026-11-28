"""第二季第一期《不情愿的顾客——巴菲特与穆迪》全部镜头（开场、片名、第一至七章、下期预告）。

版式（沿用第八期）：上方画窗（cy≈540，1000×560）放真实影像或文件影像；下方 y 880–1420 放动画解读；y≈1462 出处；y≈1555 字幕。
素材：
  · archive.org：1897–1903 年爱迪生公司等铁路影片（美国国会图书馆，公有领域）rr_*；1941 年《Work of the Stock Exchange》cx_* / db_book / bond_cert；
    纽约证券交易所资料片 ny_*（Prelinger Archives）；
  · 维基共享资源：约翰·穆迪 1903 年肖像、1904 年铁路集团图、世贸中心七号楼（穆迪总部）、止赎房屋、雷曼兄弟总部、巴菲特（2010）等；
  · 第一季成片片段（本系列）：s1_*，画面标「第一季 · 某期」；
  · 其余为股东信、年报、SEC 报告、FCIC 报告数据的图表与示意动画（示意处标注“示意”）。自绘图形不画任何公司的商标。
时间全部挂在旁白句子与词锚点上（WT 用朗读文本）。
"""
from gg_base import *          # noqa
from gg_base import _SAY        # noqa
import csv

WCY, WH = 540, 560          # 上方画窗 1000×560（y 260–820，在章节导航之下）
RED_X = C(225, 70, 60)
NAVY = C(70, 110, 190)


def A(t, t0, t1, fi=0.4, fo=0.4): return env(t, t0, t1, fi, fo)


def CHE(cid):
    """本章画面结束时刻：下一章（章节卡）开始后 0.2 秒；第七章为片尾开始后 0.4 秒"""
    k = int(cid[2])
    return CH['ch%d' % (k + 1)][0] + 0.2 if k < 7 else CH['end'][0] + 0.4


def win2(i, j=None, pre=0.45, post=-0.1):
    """从 i 句开口前 pre 秒，到 j（或 i）句之后的下一句开口后 0.1 秒（前后镜头叠化 0.55 秒，不掉黑）"""
    j = j or i
    nx = nxt(j)
    end = (S(nx) - post) if nx else E(j) + 0.6
    if nx and SEG[nx]['ch'] != SEG[j]['ch']:
        end = CHE(SEG[j]['ch'])
    return S(i) - pre, end


def appear(t, i, sub, d=0.45, lead=0.1):
    """词锚点 sub 开口前 lead 秒开始，用 d 秒缓入"""
    return eo((t - WT(i, sub) + lead) / d)


def cross(cv, x, y, r, a, col=RED_X, th=6):
    if a <= 0.004: return
    cv.line((x - r, y - r), (x + r, y + r), col, a, th); cv.line((x - r, y + r), (x + r, y - r), col, a, th)


# ======================================================================== 通用构件（本期）
def recap(cv, t, t0, t1, clip, label, a=1.0):
    """第一季回顾：本系列成片片段放进画窗，左上角金色「第一季 · 某期」标签 + 「回顾」字样"""
    al = env(t, t0, t1, 0.45, 0.45) * a
    if al <= 0.004: return
    seq(cv, t, t0, t1, [clip], cy=WCY, h=WH, a=al, cap='本系列第一季成片片段')
    k = eo((t - t0 - 0.2) / 0.5)
    chip(cv, '回顾 · ' + label, 90, 300, 28, al * k, col=GOLD_L, anchor='l')


def gate_tag(cv, n, a, y=880):
    if a <= 0.004: return
    g, txt, en = GATES[n - 1]
    chip(cv, f'{g}：{txt}', W / 2, y, 30, a, col=GOLD_L)


GATES = [('第一关', '优势是真的', 'REAL'), ('第二关', '对手长期学不会', 'HARD TO COPY')]


def two_gates(cv, t, a, ks, y=1110, hl=None):
    for j, (g, txt, en) in enumerate(GATES):
        k = ks[j]
        if k <= 0: continue
        x = 300 + j * 480; yy = y + 30 * (1 - k)
        on = hl is None or hl == j
        cv.rrect(x - 215, yy - 120, x + 215, yy + 120, 18, (0.06, 0.06, 0.08), a * k * 0.94)
        cv.rrect(x - 215, yy - 120, x + 215, yy + 120, 18, GOLD if on else GOLD_D, a * k * (0.95 if on else 0.5), fill=False, th=3, glow=0.12 if on else 0)
        cv.text(g, x, yy - 62, 34, 'sans_bold', col=GOLD_L if on else GREY, a=a * k)
        cv.text(txt, x, yy + 6, 42, 'serif_black', col=CREAM if on else GREY, a=a * k)
        cv.text(en, x, yy + 74, 22, 'sans_med', col=GOLD_D, a=a * k, track=0.12)


LADDER = [('三A', 'Aaa', True), ('双A', 'Aa', True), ('A', 'A', True), ('三B', 'Baa', True), ('双B', 'Ba', False), ('B', 'B', False), ('三C', 'Caa', False)]


def rating_ladder(cv, t, a, ks, x=W / 2, y0=930, dy=62, show_line=0.0):
    """评级阶梯（示意）：上四级投资级，下面是投机级（俗称垃圾债）；括号里是穆迪的写法"""
    for j, (cn, mo, inv) in enumerate(LADDER):
        k = ks[min(j, len(ks) - 1)] if isinstance(ks, (list, tuple)) else ks
        k = eo(cl((k * 7 - j) / 1.0)) if not isinstance(ks, (list, tuple)) else k
        if k <= 0: continue
        y = y0 + j * dy + (40 if not inv else 0)
        w = 520 - j * 46
        col = GOLD if inv else RED_X * 0.85
        cv.rrect(x - w / 2, y - 24, x + w / 2, y + 24, 10, col * 0.22, a * k)
        cv.rrect(x - w / 2, y - 24, x + w / 2, y + 24, 10, col, a * k * 0.8, fill=False, th=2)
        cv.text(cn, x - 40, y, 32, 'sans_bold', col=GOLD_L if inv else CREAM, a=a * k)
        cv.text(mo, x + w / 2 - 22, y, 22, 'corm_med', col=GREY, a=a * k, anchor='r')
    if show_line > 0:
        yl = y0 + 3.5 * dy + 20
        cv.line((x - 330, yl), (x + 330, yl), CREAM, a * show_line * 0.7, 2)
        cv.text('投资级', x - 330, yl - 26, 24, 'sans_med', col=GOLD_L, a=a * show_line, anchor='l')
        cv.text('投机级 · 俗称垃圾债', x - 330, yl + 28, 24, 'sans_med', col=RED_X, a=a * show_line, anchor='l')


def flow_box(cv, x, y, txt, a, col=GOLD, w=260, h=86, sub=None, size=34):
    if a <= 0.004: return
    cv.rrect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, 16, (0.06, 0.06, 0.08), a * 0.92)
    cv.rrect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, 16, col, a * 0.85, fill=False, th=2)
    cv.text(txt, x, y - (12 if sub else 0), size, 'sans_bold', col=CREAM, a=a)
    if sub: cv.text(sub, x, y + 24, 20, 'sans_light', col=GREY, a=a)


def stack_bar(cv, t, t0, a, y, parts, x0=110, x1=970, h=64, label=None, total_txt=None):
    """横向堆叠条：parts = [(名称, 百分比, 颜色)]，从左到右依次长出；名称写在色块下方"""
    x = x0; tt = t0
    for j, (nm, v, col) in enumerate(parts):
        e = eexp((t - tt) / 0.7)
        L = (x1 - x0) * v / 100.0
        if e > 0:
            gbar(cv, x, y - h / 2, x + max(L * e, 2), y + h / 2, col, a, horizontal=True, glow=0.1, sheen_t=t - tt)
            if L > 70: cv.text(f'{v:.1f}%' if v < 99 else f'{v:.0f}%', x + L / 2, y, 26, 'sans_bold', col=INK if col is not GREY else CREAM, a=a * min(1, e * 2))
            cv.text(nm, x + L / 2, y + h / 2 + 26, 22, 'sans_med', col=CREAM if col is not GREY else GREY, a=a * min(1, e * 2))
        x += L; tt += 0.35
    if label: cv.text(label, x0, y - h / 2 - 28, 26, 'sans_med', col=CREAM, a=a, anchor='l')
    if total_txt: cv.text(total_txt, x1, y - h / 2 - 28, 30, 'sans_bold', col=GOLD_L, a=a * eo((t - tt) / 0.5), anchor='r')


def _load_px():
    p = os.path.join(ROOT, 'assets', 'media', 'mco_monthly.csv')
    rows = [r for r in csv.reader(l for l in open(p) if not l.startswith('#'))][1:]
    return [(r[0], float(r[1]), float(r[2]), float(r[3])) for r in rows]


PX = _load_px()


def price_chart(cv, t, t0, a, m0='2000-01', m1='2012-12', x0=110, x1=970, y0=900, y1=1360, vmax=90.0, marks=(), dur=2.2):
    """穆迪月线（按拆股调整的收盘价，雅虎财经）：从左到右画出；marks = [(月份, 'high'/'low', 文字, 出现时刻)]"""
    pts = [(m, c, h, l) for (m, c, h, l) in PX if m0 <= m <= m1]
    n = len(pts)
    def X(i): return x0 + (x1 - x0) * i / max(n - 1, 1)
    def Y(v): return y1 - (y1 - y0) * v / vmax
    grid_lines(cv, x0, x1, y1, y0, a * 0.8, n=3)
    for v in (25, 50, 75):
        if v < vmax: cv.text(f'${v}', x0 - 10, Y(v), 20, 'sans_light', col=GREY, a=a * 0.8, anchor='r')
    k = eexp((t - t0) / dur)
    m = int(k * (n - 1))
    for i in range(m):
        cv.line((X(i), Y(pts[i][1])), (X(i + 1), Y(pts[i + 1][1])), GOLD, a, 3)
    for yr in range(int(m0[:4]), int(m1[:4]) + 1, 2):
        i = next((j for j, p in enumerate(pts) if p[0] == f'{yr}-01'), None)
        if i is not None: cv.text(str(yr), X(i), y1 + 30, 20, 'sans_light', col=GREY, a=a * 0.9)
    for (mm, kind, txt, tw) in marks:
        i = next((j for j, p in enumerate(pts) if p[0] == mm), None)
        if i is None or i > m: continue
        kk = eo((t - tw + 0.1) / 0.4)
        if kk <= 0: continue
        v = pts[i][2] if kind == 'high' else pts[i][3]
        cv.glow_dot((X(i), Y(v)), 9, GOLD_L if kind == 'high' else RED_X, a * kk)
        cv.text(txt, X(i), Y(v) + (-36 if kind == 'high' else 38), 28, 'sans_bold', col=GOLD_L if kind == 'high' else RED_X, a=a * kk, shadow=0.7)


def item_list(cv, t, a, rows, ks, cur, y0=960, dy=130, col=GOLD):
    """编号清单（风险 / 收获）：rows = [(标题, 小字)]"""
    for j, (nm, sub) in enumerate(rows):
        k = ks[j]
        if k <= 0: continue
        y = y0 + j * dy; on = j == cur
        cv.rrect(90, y - 52, 990, y + 52, 14, (0.07, 0.07, 0.09) if on else (0.05, 0.05, 0.06), a * k * 0.9)
        cv.rrect(90, y - 52, 990, y + 52, 14, col if on else GREY, a * k * (0.9 if on else 0.4), fill=False, th=2)
        cv.text(f'0{j + 1}', 145, y, 34, 'oswald', col=col if on else GREY, a=a * k)
        cv.text(nm, 210, y - 16, 34, 'sans_bold', col=CREAM if on else GREY, a=a * k, anchor='l')
        cv.text(sub, 210, y + 26, 22, 'sans_light', col=CREAM if on else GREY, a=a * k, anchor='l')


def ph(names, fb, cap_ph, cap_fb):
    """有照片用照片，没有就用档案影像"""
    n = first_have(names)
    return (n, cap_ph) if n else (fb, cap_fb)


def window(cv, t, t0, t1, names, cap, a, focus=None):
    """画窗：names 里是照片（c_*）就推拉，是视频就串接"""
    n = first_have(names) if all(x.startswith('c_') for x in names) else None
    if n: photo_win(cv, n, t, t0, t1, cy=WCY, h=WH, a=a, cap=cap, focus=focus or (0.5, 0.5))
    else: seq(cv, t, t0, t1, [x for x in names if not x.startswith('c_')] or names, cy=WCY, h=WH, a=a, cap=cap, focus=focus)


# ======================================================================== 开场
def shot_hook(cv, t):
    a0 = env(t, 0, S('h1') + 0.6, 0.0, 0.5)
    if a0 > 0:
        L = 420 * eo(t / 1.1); hb = math.exp(-max(t - 0.25, 0) * 6) * (t >= 0.25)
        cv.line((W / 2 - L, 960), (W / 2 + L, 960), GOLD, a0 * (0.5 + 0.5 * hb), 2)
        cv.glow_dot((W / 2, 960), 30 + 40 * hb, GOLD, a0 * 0.6)
    # h1：承接第一季（美国运通）
    t0, t1 = win2('h1')
    a = A(t, t0 + 0.4, t1, 0.5, 0.4)
    if a > 0:
        recap(cv, t, t0, t1, 's1_amex', '第一季 · 美国运通', a=a)
        k = appear(t, 'h1', '信任')
        if k > 0:
            cv.text('信任，', W / 2, 980, 70, 'serif_black', col=CREAM, a=a * k)
            cv.text('也能做成一门好生意', W / 2, 1090, 64, 'serif_black', gold=True, a=a * appear(t, 'h1', '可以做成'), glow=0.12)
        chip(cv, '第一季 · 第 7 期 · 美国运通', W / 2, 1220, 30, a * appear(t, 'h1', '美国运通'), col=GOLD)
        source(cv, '第一季 · 美国运通《银行赚13%，它凭什么赚30%》（本系列）', a, y=1462)
    # h2：第二季第一期：给别人的信用打分
    t0, t1 = win2('h2')
    a = A(t, t0, t1)
    if a > 0:
        n, cap = ph(['c_7wtc'], 'ny_floor', '纽约世贸中心七号楼：穆迪总部所在', '纽约证券交易所交易大厅（资料片）')
        window(cv, t, t0, t1, [n], cap, a)
        chip(cv, '第二季 · 第 1 期', W / 2, 920, 32, a * appear(t, 'h2', '第二季'), col=GOLD_L)
        k = appear(t, 'h2', '信用打分')
        if k > 0: cv.text('给别人的信用打分', W / 2, 1040, 76, 'serif_black', gold=True, a=a * k, glow=0.15, scale=1.06 - 0.06 * k)
        for j, s in enumerate(['三A', '双A', 'A', '三B', '…']):
            kk = eo((t - WT('h2', '信用打分') - 0.3 - j * 0.12) / 0.3)
            if kk > 0: chip(cv, s, W / 2 - 300 + j * 150, 1180, 34, a * kk, col=GOLD if j < 4 else GREY)
        source(cv, '本片过渡', a * 0.6, y=1462)
    # h3：4.5 万只三A 对 6 家公司
    t0, t1 = win2('h3')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['bond_cert'], cy=WCY, h=WH, a=a, cap='债券凭证（1941 年影片）')
        k = appear(t, 'h3', '四点五万', lead=0.2)
        if k > 0:
            cv.text(counter(0, 45000, t, WT('h3', '四点五万') - 0.2, 1.0, lambda v: f'{v:,.0f}'), 300, 1010, 104, 'oswald', col=GOLD_L, a=a * k, glow=0.12)
            cv.text('只房贷相关证券', 300, 1100, 30, 'sans_med', col=CREAM, a=a * k)
            cv.text('被穆迪评为三A（2000–2007）', 300, 1145, 24, 'sans_light', col=GREY, a=a * k)
        k2 = appear(t, 'h3', '只有六家', lead=0.15)
        if k2 > 0:
            cv.text('VS', W / 2, 1040, 34, 'sans_bold', col=GREY, a=a * appear(t, 'h3', '而到'))
            cv.text('6', 790, 1010, 150, 'oswald', col=RED_X, a=a * k2, glow=0.15, scale=1.25 - 0.25 * k2)
            cv.text('家美国私营公司', 790, 1100, 30, 'sans_med', col=CREAM, a=a * k2)
            cv.text('拿到三A（2010 年初）', 790, 1145, 24, 'sans_light', col=GREY, a=a * k2)
        source(cv, 'FCIC 最终报告“结论”第 xxv 页（“Moody’s rated nearly 45,000 mortgage-related securities as triple-A … six private-sector companies … in early 2010”）', a, y=1462)
    # h4：83% 被下调；关键齿轮
    t0, t1 = win2('h4')
    a = A(t, t0, t1)
    if a > 0:
        n, cap = ph(['c_foreclosure', 'c_foreclosure2'], 'cx_board', '止赎房屋的告示牌（金融危机期间）', '交易所报价（1941 年影片）')
        window(cv, t, t0, t1, [n], cap, a)
        tq = WT('h4', '危机调查委员会')
        kq = eo((t - tq + 0.2) / 0.4)
        k = appear(t, 'h4', '百分之八十三', lead=0.2)
        if k > 0 and kq < 1:
            cv.text(counter(0, 83, t, WT('h4', '百分之八十三') - 0.2, 0.9, lambda v: f'{v:.0f}%'), W / 2, 1040, 170, 'oswald', col=RED_X, a=a * k * (1 - kq), glow=0.15)
            cv.text('2006 年评为三A的房贷证券，最后被下调', W / 2, 1170, 34, 'sans_med', col=CREAM, a=a * k * (1 - kq))
        qcard(cv, 'qcogs', t, tq - 0.2, t1, cy=1110, en=30, cn=40, a=a, typing=1.2, w=940)
        source(cv, 'FCIC 最终报告“结论”第 xxv 页（“83% of the mortgage securities rated triple-A that year ultimately were downgraded”）', a, y=1462)
    # h5：8.64 亿美元和解
    t0, t1 = win2('h5')
    a = A(t, t0, t1)
    if a > 0:
        n, cap = ph(['c_7wtc2', 'c_7wtc'], 'ny_floor2', '纽约世贸中心一号楼与七号楼（2019）', '纽约证券交易所交易大厅（资料片）')
        window(cv, t, t0, t1, [n], cap, a)
        chip(cv, '2017 年 1 月', W / 2, 930, 32, a * appear(t, 'h5', '二零一七年'), col=GOLD)
        money(cv, t, WT('h5', '八点六四亿'), '近 $8.64 亿', W / 2, 1040, 120, a, sub='和解金额')
        k = appear(t, 'h5', '美国司法部')
        if k > 0:
            for j, s in enumerate(['美国司法部', '21 个州', '华盛顿特区']):
                chip(cv, s, W / 2 - 300 + j * 300, 1230, 32, a * eo((t - WT('h5', '美国司法部') - j * 0.25) / 0.35), col=CREAM)
        source(cv, '美国司法部新闻稿 17-070（2017-01-13：“nearly $864 million settlement”）', a, y=1462)
    # h6：信誉扫地，生意也该完了？
    t0, t1 = win2('h6')
    a = A(t, t0, t1)
    if a > 0:
        n, cap = ph(['c_deserted', 'c_lehman'], 'cx_quote', '止赎后空置的房子', '交易所报价板（1941 年影片）')
        window(cv, t, t0, t1, [n], cap, a)
        big_q(cv, t, '信誉扫地的评级公司', 1000, WT('h6', '信誉扫地'), 58, a, col=CREAM)
        big_q(cv, t, '生意也该完了？', 1110, WT('h6', '生意也该'), 72, a)
    # h7：每收 100 美元，调整后营业利润将近 64 美元
    t0, t1 = win2('h7')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['ny_floor'], cy=WCY, h=WH, a=a, cap='纽约证券交易所交易大厅（资料片）')
        chip(cv, '2025 年 · 穆迪评级业务', W / 2, 920, 30, a * appear(t, 'h7', '二零二五年'), col=GOLD)
        k = appear(t, 'h7', '一百美元')
        if k > 0:
            x0, x1, y = 140, 940, 1080
            cv.rrect(x0, y - 50, x1, y + 50, 12, (0.12, 0.12, 0.14), a * k)
            cv.text('每收 $100', x0, y - 82, 32, 'sans_bold', col=CREAM, a=a * k, anchor='l')
            e = eexp((t - WT('h7', '六十四美元') + 0.2) / 0.9)
            if e > 0:
                gbar(cv, x0, y - 50, x0 + (x1 - x0) * 0.636 * e, y + 50, GOLD, a, horizontal=True, glow=0.2, sheen_t=t - WT('h7', '六十四美元'))
                cv.text(counter(0, 63.6, t, WT('h7', '六十四美元') - 0.2, 0.9, lambda v: f'${v:.1f}'), x0 + (x1 - x0) * 0.636 * e / 2, y, 52, 'sans_bold', col=INK, a=a * e)
                cv.text('调整后营业利润', x0 + (x1 - x0) * 0.318, y + 82, 28, 'sans_med', col=GOLD_L, a=a * e)
        source(cv, '穆迪 2025 年全年业绩新闻稿（2026-02-18；MIS 调整后营业利润率 63.6%）', a, y=1462)
    # h8：阿贝尔第一封股东信点了名
    t0, t1 = win2('h8')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['cx_floor'], cy=WCY, h=WH, a=a, cap='交易所交易大厅（1941 年影片）')
        doc_page(cv, t, t0 + 0.2, t1, 'BERKSHIRE HATHAWAY · 2025 LETTER · GREG ABEL',
                 ['A large portion of our portfolio is concentrated in', 'a small number of American companies such as Apple,',
                  'American Express, Coca-Cola, and Moody’s – businesses', 'we understand well … and expect will compound over decades.'],
                 cy=1120, w=960, size=27, hl='Moody’s', hl_t=WT('h8', '点了名') - 0.2, a=a)
        source(cv, '伯克希尔 2025 年致股东信第 15 页（署名 Gregory E. Abel）', a, y=1462)
    # h9：这家公司叫穆迪；凭什么？
    t0, t1 = S('h9') - 0.45, CH['title'][0] + 0.2
    a = A(t, t0, t1, 0.4, 0.25)
    if a > 0:
        n, cap = ph(['c_7wtc'], 'ny_floor2', '纽约世贸中心七号楼：穆迪总部所在', '纽约证券交易所交易大厅（资料片）')
        window(cv, t, t0, t1, [n], cap, a)
        k = appear(t, 'h9', '叫穆迪', lead=0.2)
        if k > 0:
            cv.text('穆迪', W / 2, 1000, 120, 'serif_black', gold=True, a=a * k, glow=0.25, scale=1.1 - 0.1 * k)
            cv.text('MOODY’S', W / 2, 1100, 34, 'corm_med', col=GOLD, a=a * k, track=0.4)
        big_q(cv, t, '信誉崩了，生意却没丢，凭什么？', 1230, WT('h9', '信誉崩了'), 46, a, col=CREAM)


def shot_title(cv, t):
    t0, t1 = CH['title'][0], CH['ch1'][0] + 0.6
    a = env(t, t0, t1, 0.02, 0.6)
    if a <= 0: return
    p = t - t0
    flash = math.exp(-p * 5.0)
    # 一枚评级章（示意）：三A 在圆章里
    k0 = eo(p / 0.35)
    R = 150
    cv.circle((W / 2, 640), R, GOLD, a * k0 * 0.9, 4)
    cv.circle((W / 2, 640), R - 16, GOLD_D, a * k0 * 0.6, 2)
    cv.text('AAA', W / 2, 640, 96, 'oswald', col=GOLD_L, a=a * k0, glow=0.2, scale=1.15 - 0.15 * k0)
    cv.circle((W / 2, 640), 60 + p * 900, GOLD, a * math.exp(-p * 2.2) * 0.8, 3)
    cv.glow_dot((W / 2, 640), 220, GOLD, a * flash * 0.9)
    k = eo((p - 0.15) / 0.6)
    cv.text('不情愿的', W / 2, 1000, 100, 'serif_black', col=CREAM, a=a * k, scale=1.08 - 0.08 * k, shadow=0.8)
    cv.text('顾客', W / 2, 1135, 128, 'serif_black', gold=True, a=a * eo((p - 0.35) / 0.6), glow=0.3)
    cv.text('巴菲特与穆迪', W / 2, 1270, 52, 'serif_semi', col=CREAM, a=a * eo((p - 0.7) / 0.6))
    cv.text('AN UNWILLING CUSTOMER', W / 2, 1360, 26, 'corm', col=GOLD, a=a * eo((p - 1.0) / 0.6), track=0.35)
    chip(cv, SEASON, W / 2, 1450, 26, a * eo((p - 1.1) / 0.5), col=GOLD_D)


# ======================================================================== 第一章：打分的生意
def shot_ch1(cv, t):
    # c1a：1909 年，约翰·穆迪，铁路债券
    t0, t1 = win2('c1a')
    a = A(t, t0, t1)
    if a > 0:
        n = first_have(['c_moody1903'])
        if n: photo_win(cv, n, t, t0, t1, cy=WCY, h=WH, a=a, cap='约翰·穆迪（1903 年）', focus=(0.5, 0.35))
        else: seq(cv, t, t0, t1, ['rr_station'], cy=WCY, h=WH, a=a, cap='火车进站（1897 年影片）')
        k = appear(t, 'c1a', '一九零九年', lead=0.2)
        if k > 0: cv.text('1909', W / 2, 980, 130, 'oswald', col=GOLD_L, a=a * k, glow=0.15, scale=1.15 - 0.15 * k)
        chip(cv, '约翰·穆迪 · 铁路证券手册', W / 2, 1110, 34, a * appear(t, 'c1a', '约翰'), col=CREAM)
        k2 = appear(t, 'c1a', '一千三百')
        if k2 > 0:
            cv.text(counter(0, 1300, t, WT('c1a', '一千三百') - 0.1, 0.8, lambda v: f'近 {v:,.0f} 只铁路债券'), W / 2, 1230, 46, 'sans_bold', col=GOLD_L, a=a * k2)
            cv.text('第一次用字母等级打分', W / 2, 1300, 30, 'sans_med', col=CREAM, a=a * appear(t, 'c1a', '字母等级'))
        source(cv, 'Imperial College Business School；Wilson（2011）Financial History Review；NBER 工作论文（1909 年 4 月，近 1300 只铁路债券）', a, y=1462)
    # c1b：铁路是最大的发债人；一个字母省了功夫
    t0, t1 = win2('c1b')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['rr_loco', 'rr_cars'], cy=WCY, h=WH, a=a, cap='蒸汽机车与货车（1898 年影片）')
        k = appear(t, 'c1b', '最大的发债人')
        if k > 0: cv.text('铁路：当时美国最大的发债人', W / 2, 950, 44, 'serif_black', col=CREAM, a=a * k)
        k2 = appear(t, 'c1b', '看不懂')
        if k2 > 0:
            # 一摞账本 → 一个字母
            for j in range(5):
                cv.rrect(220 + j * 14, 1060 - j * 18, 420 + j * 14, 1180 - j * 18, 8, PAPER * (0.75 + 0.04 * j), a * k2)
                for r in range(4): cv.line((240 + j * 14, 1080 - j * 18 + r * 22), (400 + j * 14, 1080 - j * 18 + r * 22), INKD * 2.4, a * k2 * 0.6, 2)
            cv.text('看不懂的账', 340, 1230, 26, 'sans_light', col=GREY, a=a * k2)
        k3 = appear(t, 'c1b', '一个字母')
        if k3 > 0:
            arrow(cv, (480, 1110), (620, 1110), a * k3, col=GOLD, k=k3)
            cv.circle((780, 1110), 90, GOLD, a * k3, 4)
            cv.text('A', 780, 1110, 110, 'serif_black', gold=True, a=a * k3, glow=0.2, scale=1.2 - 0.2 * k3)
            cv.text('一个字母，省了功夫', 780, 1240, 28, 'sans_med', col=GOLD_L, a=a * k3)
        source(cv, '同上（铁路是当时主要发债人）；“省了功夫”为本片解读', a, y=1462)
    # c1c：评级阶梯
    t0, t1 = win2('c1c')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['bond_cert'], cy=WCY, h=WH, a=a, cap='债券凭证（1941 年影片）')
        k = eo((t - WT('c1c', '字母越分越细') + 0.1) / 1.6)
        rating_ladder(cv, t, a, k, y0=950, dy=58, show_line=appear(t, 'c1c', '投机级'))
        chip(cv, '标普 · 惠誉', W / 2, 875, 26, a * appear(t, 'c1c', '标普'), col=CREAM)
        source(cv, 'Poor’s 1916 年、Fitch 1924 年开始出售评级；评级符号为示意（括号内为穆迪写法）', a, y=1462)
    # c1d：投资人付费 → 发行人付费
    t0, t1 = win2('c1d')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['cx_board', 'cx_floor'], cy=WCY, h=WH, a=a, cap='交易所（1941 年影片）')
        tf = WT('c1d', '倒了过来')
        kf = eo((t - tf + 0.1) / 0.6)
        k = appear(t, 'c1d', '一开始')
        if k > 0:
            cv.text('1909 年起' if kf < 0.5 else '约 1970 年代初起', W / 2, 920, 34, 'sans_bold', col=GOLD_L, a=a * k)
            flow_box(cv, 250, 1080, '投资人' if kf < 0.5 else '发债公司', a * k, col=CREAM if kf < 0.5 else RED_X)
            flow_box(cv, 830, 1080, '评级机构', a * k, col=GOLD)
            arrow(cv, (390, 1060), (690, 1060), a * k, col=GOLD)
            cv.text('付钱', 540, 1030, 28, 'sans_med', col=GOLD_L, a=a * k)
            arrow(cv, (690, 1110), (390, 1110), a * k * 0.7, col=GREY)
            cv.text('评级' if kf < 0.5 else '给自己打分', 540, 1145, 26, 'sans_light', col=GREY, a=a * k)
            if kf > 0:
                cv.glow_dot((250, 1080), 120, RED_X, a * math.exp(-max(t - tf, 0) * 3) * 0.6)
                cv.text('付钱的人变了', W / 2, 1250, 40, 'serif_black', col=RED_X, a=a * kf)
        source(cv, 'Lawrence J. White，Mercatus 政策简报《A Brief History of Credit Rating Agencies》；White 2009 年参议院证词', a, y=1462)
    # c1e：1975 年 NRSRO
    t0, t1 = win2('c1e')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['ny_floor2'], cy=WCY, h=WH, a=a, cap='纽约证券交易所交易大厅（资料片）')
        k = appear(t, 'c1e', '一九七五年', lead=0.2)
        if k > 0: cv.text('1975', W / 2, 990, 120, 'oswald', col=GOLD_L, a=a * k, glow=0.12)
        chip(cv, '美国证监会：“全国认可的统计评级组织”（NRSRO）', W / 2, 1120, 30, a * appear(t, 'c1e', '全国认可'), col=CREAM)
        k2 = appear(t, 'c1e', '直接引用')
        if k2 > 0: cv.text('监管规则，开始直接引用它们的评级', W / 2, 1230, 38, 'serif_black', gold=True, a=a * k2)
        source(cv, '同上（1975 年 SEC 券商净资本规则引入 NRSRO，原有三家直接获认可）', a, y=1462)
    # c1f：两块生意
    t0, t1 = win2('c1f')
    a = A(t, t0, t1)
    if a > 0:
        n, cap = ph(['c_7wtc'], 'ny_ticker', '纽约世贸中心七号楼：穆迪总部所在', '纽约证券交易所报价带（资料片）')
        window(cv, t, t0, t1, [n], cap, a)
        chip(cv, '2025 年对外收入', W / 2, 900, 28, a * appear(t, 'c1f', '两块生意'), col=GOLD)
        hbar(cv, t, [('评级', 41.19, WT('c1f', '一块是评级'), GOLD), ('数据与分析', 35.99, WT('c1f', '另一块'), NAVY)], a,
             x0=320, x1=820, y0=1010, dy=130, vmax=45, fmt=lambda v: f'${v:.0f} 亿', size=44, lab=34)
        k = appear(t, 'c1f', '订阅收入')
        if k > 0: chip(cv, '数据与分析：96% 是订阅等经常性收入', W / 2, 1260, 28, a * k, col=CREAM)
        source(cv, '穆迪 2025 年全年业绩新闻稿（MIS 对外营收 41.19 亿美元，MA 对外营收 35.99 亿美元，MA 经常性收入 96%）', a, y=1462)
    # c1g：三分之二来自新债首次评级
    t0, t1 = S('c1g') - 0.45, CHE('ch1')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['cx_quote', 'cx_board'], cy=WCY, h=WH, a=a, cap='交易所报价板（1941 年影片）')
        k = appear(t, 'c1g', '评级的收入')
        if k > 0:
            stack_bar(cv, t, WT('c1g', '三分之二') - 0.2, a * k, 1080, [('新债首次评级等（交易性）', 67, GOLD), ('跟踪费（经常性）', 33, NAVY)],
                      label='2025 年评级收入', total_txt='')
        k2 = appear(t, 'c1g', '发债多的')
        if k2 > 0: cv.text('发债多的年份，赚得多；发债少，就少', W / 2, 1250, 36, 'serif_black', col=CREAM, a=a * k2)
        source(cv, '穆迪 2025 年全年业绩新闻稿表 6（MIS 交易性收入占 67%）', a, y=1462)


# ======================================================================== 第二章：他看中了什么
def shot_ch2(cv, t):
    # c2a：1999、2000 年初买入邓白氏
    t0, t1 = win2('c2a')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['db_book'], cy=WCY, h=WH, a=a, cap='邓白氏《参考手册》（1941 年影片）')
        big_q(cv, t, '伯克希尔是怎么拿到穆迪的？', 950, WT('c2a', '伯克希尔'), 50, a, col=CREAM)
        k = appear(t, 'c2a', '一九九九年')
        if k > 0:
            chip(cv, '1999 年', W / 2 - 170, 1100, 40, a * k, col=GOLD_L)
            chip(cv, '2000 年初', W / 2 + 170, 1100, 40, a * appear(t, 'c2a', '二零零零年初'), col=GOLD_L)
        k2 = appear(t, 'c2a', '邓白氏')
        if k2 > 0: cv.text('买入邓白氏公司（Dun & Bradstreet）', W / 2, 1220, 40, 'serif_black', gold=True, a=a * k2)
        source(cv, 'FCIC 访谈巴菲特录音（2010-05-26）：“in 1999 and in February of 2000 you invested in Dun and Bradstreet.” “That’s correct.”', a, y=1462)
    # c2b：2000-09-30 拆分，原公司改名穆迪，约 15%
    t0, t1 = win2('c2b')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['db_book', 'cx_board'], cy=WCY, h=WH, a=a, cap='邓白氏《参考手册》与交易所（1941 年影片）')
        chip(cv, '2000 年 9 月底', W / 2, 900, 30, a * appear(t, 'c2b', '二零零零年九月底'), col=GOLD)
        ks = eo((t - WT('c2b', '一拆为二') + 0.1) / 0.8)
        flow_box(cv, W / 2, 1010 - 0 * ks, '邓白氏', a * (1 - ks * 0.4), col=CREAM, w=300)
        if ks > 0:
            arrow(cv, (W / 2 - 60, 1060), (300, 1160), a * ks, col=GREY, k=ks)
            arrow(cv, (W / 2 + 60, 1060), (780, 1160), a * ks, col=GOLD, k=ks)
            flow_box(cv, 300, 1210, '新邓白氏', a * ks * appear(t, 'c2b', '新邓白氏'), col=GREY, sub='独立出去')
            flow_box(cv, 780, 1210, '穆迪', a * ks * appear(t, 'c2b', '改名叫穆迪'), col=GOLD, sub='原来的公司改名')
        k = appear(t, 'c2b', '百分之十五')
        if k > 0: chip(cv, '伯克希尔：约 15%', 780, 1320, 32, a * k, col=GOLD_L)
        source(cv, '邓白氏 2000 年 10-K405（2000-09-30 完成分拆，原公司更名为 Moody’s Corporation）；伯克希尔 2008 年信（“We purchased 15% of Moody’s”）', a, y=1462)
    # c2c：尽职调查？没有团队、自己分析、没见过任何人
    t0, t1 = win2('c2c')
    a = A(t, t0, t1)
    if a > 0:
        n = first_have(['c_obama_buffett', 'c_buffett_2010'])
        if n: photo_win(cv, n, t, t0, t1, cy=WCY, h=WH, a=a, cap='巴菲特（2010 年，白宫官方照片）' if n == 'c_obama_buffett' else '巴菲特（2010 年）', focus=(0.6, 0.4))
        else: seq(cv, t, t0, t1, ['cx_floor'], cy=WCY, h=WH, a=a, cap='交易所交易大厅（1941 年影片）')
        k = appear(t, 'c2c', '危机调查委员会')
        if k > 0: chip(cv, '2010 年 5 月 · 金融危机调查委员会访谈', W / 2, 910, 28, a * k, col=GOLD)
        big_q(cv, t, '“你和团队做了哪些尽职调查？”', 1010, WT('c2c', '买之前'), 44, a, col=CREAM)
        for j, (s, w) in enumerate((('没有团队', '没有团队'), ('分析都自己做', '分析都是'), ('没见过任何人', '也没见过'))):
            kk = appear(t, 'c2c', w)
            if kk > 0: chip(cv, s, W / 2 - 320 + j * 320, 1150 + 14 * (1 - kk), 38, a * kk, col=GOLD_L)
        source(cv, 'FCIC 访谈巴菲特录音（“There is no staff. I make all the investment decisions and I do all my own analysis … I never met with anybody.”）', a, y=1462)
    # c2d：引出原声（定价权）
    t0, t1 = S('c2d') - 0.45, S('c2d') + SEG['c2d']['dur'] + 0.6
    a = A(t, t0, t1, 0.4, 0.3)
    if a > 0:
        n = first_have(['c_buffett_2010', 'c_obama_buffett'])
        if n: photo_win(cv, n, t, t0, t1, cy=WCY, h=WH, a=a, cap='巴菲特（2010 年）', focus=(0.5, 0.4))
        k = appear(t, 'c2d', '经济特性')
        if k > 0: cv.text('他只看一样：这门生意的经济特性', W / 2, 1040, 46, 'serif_black', gold=True, a=a * k)
    # c2e：回顾喜诗：定价权来自顾客的喜爱
    t0, t1 = win2('c2e')
    a = A(t, t0, t1)
    if a > 0:
        recap(cv, t, t0, t1, 's1_sees', '第一季 · 喜诗糖果', a=a)
        k = appear(t, 'c2e', '定价权')
        if k > 0:
            cv.text('定价权', W / 2 - 200, 1060, 64, 'serif_black', gold=True, a=a * k)
            arrow(cv, (W / 2 - 80, 1060), (W / 2 + 40, 1060), a * appear(t, 'c2e', '来自'), col=GOLD)
            cv.text('顾客的喜爱', W / 2 + 190, 1060, 56, 'serif_black', col=CREAM, a=a * appear(t, 'c2e', '顾客的喜爱'))
        source(cv, '第一季 · 喜诗糖果《一盒糖的学费》（本系列）', a, y=1462)
    # c2f：从两边看：股东 + 顾客
    t0, t1 = S('c2f') - 0.45, S('c2f') + SEG['c2f']['dur'] + 0.6
    a = A(t, t0, t1, 0.4, 0.3)
    if a > 0:
        seq(cv, t, t0, t1, ['bond_cert'], cy=WCY, h=WH, a=a, cap='债券凭证（1941 年影片）')
        k = appear(t, 'c2f', '来路不一样')
        if k > 0: cv.text('穆迪的定价权：来路不一样', W / 2, 920, 44, 'serif_black', col=CREAM, a=a * k)
        k2 = appear(t, 'c2f', '伯克希尔旗下')
        if k2 > 0:
            flow_box(cv, 270, 1110, '股东', a * k2, col=GOLD, sub='持有穆迪', w=240)
            flow_box(cv, 810, 1110, '顾客', a * appear(t, 'c2f', '也要找'), col=RED_X, sub='发债要找穆迪评级', w=280)
            cv.circle((W / 2, 1110), 70, CREAM, a * k2 * 0.8, 3)
            cv.text('伯克希尔', W / 2, 1110, 30, 'sans_bold', col=CREAM, a=a * k2)
            arrow(cv, (W / 2 - 80, 1110), (400, 1110), a * k2, col=GOLD); arrow(cv, (W / 2 + 80, 1110), (660, 1110), a * appear(t, 'c2f', '也要找'), col=RED_X)
        k3 = appear(t, 'c2f', '两边看')
        if k3 > 0: cv.text('从两边看', W / 2, 1260, 40, 'sans_bold', col=GOLD_L, a=a * k3)
        source(cv, 'FCIC 访谈巴菲特录音（“we’re a customer of Moody’s too so I see this from both sides”）', a, y=1462)
    # c2g：不情愿，却离不开；非凡的生意不需要很好的管理
    t0, t1 = win2('c2g')
    a = A(t, t0, t1)
    if a > 0:
        n = first_have(['c_7wtc'])
        if n: photo_win(cv, n, t, t0, t1, cy=WCY, h=WH, a=a, cap='纽约世贸中心七号楼：穆迪总部所在')
        else: seq(cv, t, t0, t1, ['ny_floor'], cy=WCY, h=WH, a=a, cap='纽约证券交易所交易大厅（资料片）')
        tq = WT('c2g', '巴菲特说')
        kq = eo((t - tq + 0.2) / 0.4)
        k = appear(t, 'c2g', '顾客不情愿')
        if k > 0 and kq < 1:
            cv.text('不情愿，', W / 2 - 150, 1040, 70, 'serif_black', col=CREAM, a=a * k * (1 - kq))
            cv.text('却离不开', W / 2 + 160, 1040, 70, 'serif_black', gold=True, a=a * appear(t, 'c2g', '离不开') * (1 - kq), glow=0.15)
            big_q(cv, t, '管理层要紧吗？', 1170, WT('c2g', '管理层要紧吗'), 48, a * (1 - kq), col=CREAM)
        qcard(cv, 'qmgmt', t, tq - 0.2, t1, cy=1110, en=34, cn=44, a=a, typing=1.0, w=920)
        source(cv, 'FCIC 访谈巴菲特录音（“I’m not making any reference to Moody’s management, I didn’t know them”；“the extraordinary business does not require good management”）', a, y=1462)
    # c2h：没进过办公室、没打过电话、没要过董事席位
    t0, t1 = S('c2h') - 0.45, CHE('ch2')
    a = A(t, t0, t1)
    if a > 0:
        n, cap = ph(['c_7wtc'], 'ny_floor2', '纽约世贸中心七号楼：穆迪总部所在', '纽约证券交易所交易大厅（资料片）')
        window(cv, t, t0, t1, [n], cap, a)
        for j, (s, w) in enumerate((('没进过穆迪的办公室', '办公室'), ('没主动打过一个电话', '电话'), ('没要过一个董事席位', '董事席位'))):
            kk = appear(t, 'c2h', w)
            if kk <= 0: continue
            y = 990 + j * 110
            cv.text(s, W / 2 + 40, y, 48, 'serif_black', col=CREAM, a=a * kk)
            cross(cv, W / 2 - text_size(s, 'serif_black', 48)[0] / 2 - 20, y, 22, a * eo((t - WT('c2h', w) - 0.15) / 0.25), th=7)
        source(cv, 'FCIC 访谈巴菲特录音（“I’d never been in Moody’s offices. I don’t think I’ve ever initiated a call to them.”；董事席位：“No, I have no interest in it.”）', a, y=1462)


# ======================================================================== 第三章：护城河
def shot_ch3(cv, t):
    # c3a：两关
    t0, t1 = win2('c3a')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['ny_floor2'], cy=WCY, h=WH, a=a, cap='纽约证券交易所交易大厅（资料片）')
        big_q(cv, t, '顾客离不开，算不算护城河？', 920, WT('c3a', '顾客离不开'), 48, a, col=CREAM)
        two_gates(cv, t, a, [appear(t, 'c3a', '第一'), appear(t, 'c3a', '第二')], y=1130)
        source(cv, '本片分析框架（与第一季、内布拉斯加家具城一期相同的两关标准）', a, y=1462)
    # c3b：第一关：10 家，三家占 94% / 92%
    t0, t1 = win2('c3b')
    a = A(t, t0, t1)
    if a > 0:
        n, cap = ph(['c_nyse_floor'], 'ny_floor', '纽约证券交易所交易大厅（Carol M. Highsmith 摄）', '纽约证券交易所交易大厅（资料片）')
        window(cv, t, t0, t1, [n], cap, a)
        gate_tag(cv, 1, a * appear(t, 'c3b', '第一关'), y=880)
        k = appear(t, 'c3b', '一共十家')
        if k > 0:
            for j in range(10):
                kk = eo((t - WT('c3b', '一共十家') - j * 0.05) / 0.3)
                big3 = j < 3
                cv.circle((150 + j * 87, 975), 26, GOLD if big3 else GREY, a * kk * (1 if big3 else 0.7), 3)
                cv.text(['标普', '穆迪', '惠誉'][j] if big3 else '', 150 + j * 87, 975, 18, 'sans_bold', col=GOLD_L, a=a * kk)
            cv.text('SEC 登记的评级机构：10 家', W / 2, 1030, 24, 'sans_light', col=GREY, a=a * k)
        k2 = appear(t, 'c3b', '所有有效的评级')
        if k2 > 0:
            stack_bar(cv, t, WT('c3b', '标普') - 0.2, a * k2, 1130, [('标普', 49.96, GOLD), ('穆迪', 31.73, GOLD_L), ('惠誉', 12.46, GOLD_D), ('其余 7 家', 5.85, GREY)],
                      label='存续评级数量（2023 年底）', total_txt='三家 94%')
        k3 = appear(t, 'c3b', '收入')
        if k3 > 0:
            stack_bar(cv, t, WT('c3b', '收入') - 0.1, a * k3, 1300, [('三家大机构', 91.9, GOLD), ('其余', 8.1, GREY)], label='收入（2023 财年）', total_txt='92%')
        source(cv, 'SEC 评级办公室 NRSRO 年度报告（2025 年 1 月）Chart 1、Chart 3（截至 2023-12-31）、Chart 12（2023 财年）', a, y=1462)
    # c3c：赚钱的本事：几乎是无穷大
    t0, t1 = win2('c3c')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['ny_floor'], cy=WCY, h=WH, a=a, cap='纽约证券交易所交易大厅（资料片）')
        gate_tag(cv, 1, a, y=880)
        k = appear(t, 'c3c', '无穷大', lead=0.25)
        if k > 0:
            cv.text('∞', W / 2, 1040, 200, 'serif_black', gold=True, a=a * k, glow=0.25, scale=1.2 - 0.2 * k)
            cv.text('“huge returns on tangible assets, almost infinite”', W / 2, 1190, 30, 'corm_med', col=CREAM, a=a * k)
            cv.text('有形资产回报，几乎是无穷大', W / 2, 1250, 36, 'sans_bold', col=GOLD_L, a=a * k)
        source(cv, 'FCIC 访谈巴菲特录音（“huge returns on tangible assets, almost infinite”）', a, y=1462)
    # c3d：第二关：付钱的是发债公司，说了算的是买债的人
    t0, t1 = win2('c3d')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['cx_floor'], cy=WCY, h=WH, a=a, cap='交易所交易大厅（1941 年影片）')
        gate_tag(cv, 2, a * appear(t, 'c3d', '第二关'), y=880)
        k = appear(t, 'c3d', '付钱的是')
        if k > 0:
            flow_box(cv, 220, 1090, '发债公司', a * k, col=RED_X, sub='付钱', w=250)
            flow_box(cv, W / 2, 1090, '评级', a * k, col=GOLD, w=170)
            arrow(cv, (350, 1090), (450, 1090), a * k, col=RED_X)
        k2 = appear(t, 'c3d', '买债的人')
        if k2 > 0:
            flow_box(cv, 860, 1090, '买债的人', a * k2, col=GOLD_L, sub='说了算', w=250)
            arrow(cv, (630, 1090), (730, 1090), a * k2, col=GOLD)
            cv.text('谁付钱 ≠ 谁说了算', W / 2, 1240, 46, 'serif_black', gold=True, a=a * k2, glow=0.12)
        source(cv, '本片解读（依据 SEC 评级办公室 2025 年报告第 35 页“investor acceptance”一段）', a, y=1462)
    # c3e：投资规定、指数规则点名要这三家
    t0, t1 = win2('c3e')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['cx_board'], cy=WCY, h=WH, a=a, cap='交易所报价（1941 年影片）')
        gate_tag(cv, 2, a, y=880)
        doc_page(cv, t, t0 + 0.2, t1, 'SEC OFFICE OF CREDIT RATINGS · STAFF REPORT · JAN 2025',
                 ['It is common for these types of contracts and', 'guidelines to require the use of ratings of', 'specified NRSROs … many of these guidelines refer to',
                  'the ratings from the large NRSROs by name.'], cy=1080, w=960, size=27, hl='by name', hl_t=WT('c3e', '点名') - 0.2, a=a)
        k = appear(t, 'c3e', '不好卖')
        if k > 0: cv.text('找别家打分，债就不好卖', W / 2, 1320, 40, 'serif_black', col=RED_X, a=a * k)
        source(cv, 'SEC 评级办公室 NRSRO 年度报告（2025 年 1 月）第 35–36 页（投资指引、指数入选规则）', a, y=1462)
    # c3f：SEC 承认进入壁垒；引出原声
    t0, t1 = S('c3f') - 0.45, S('c3f') + SEG['c3f']['dur'] + 0.6
    a = A(t, t0, t1, 0.4, 0.3)
    if a > 0:
        seq(cv, t, t0, t1, ['ny_floor'], cy=WCY, h=WH, a=a, cap='纽约证券交易所交易大厅（资料片）')
        gate_tag(cv, 2, a, y=880)
        qcard(cv, 'qbarrier', t, t0 + 0.2, t1, cy=1100, en=34, cn=42, a=a, typing=1.0, w=920)
        source(cv, 'SEC 评级办公室 NRSRO 年度报告（2025 年 1 月）第 35 页', a, y=1462)
    # c3g：降一半价换不来信任；大家都认它；监管帮了大忙
    t0, t1 = S('c3g') - 0.45, CHE('ch3')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['ny_floor2', 'ny_floor'], cy=WCY, h=WH, a=a, cap='纽约证券交易所交易大厅（资料片）')
        k = appear(t, 'c3g', '降一半价')
        tk = WT('c3g', '护城河不在')
        kk = eo((t - tk + 0.2) / 0.4)
        if k > 0 and kk < 1:
            price_tag(cv, W / 2 - 200, 1050, 1.2, a * k * (1 - kk), '−50%', sub='降一半价')
            arrow(cv, (W / 2 - 60, 1050), (W / 2 + 60, 1050), a * k * (1 - kk), col=GREY)
            cv.text('信任', W / 2 + 200, 1050, 64, 'serif_black', col=CREAM, a=a * k * (1 - kk))
            cross(cv, W / 2 + 200, 1050, 50, a * appear(t, 'c3g', '换不来') * (1 - kk), th=8)
        if kk > 0:
            cv.text('护城河 ≠ 一纸牌照', W / 2, 990, 44, 'sans_bold', col=GREY, a=a * kk)
            cv.text('几十年攒下的“大家都认它”', W / 2, 1100, 58, 'serif_black', gold=True, a=a * appear(t, 'c3g', '大家都认它'), glow=0.2)
            chip(cv, '巴菲特：监管拿它们当标准，帮了大忙', W / 2, 1240, 30, a * appear(t, 'c3g', '监管拿'), col=CREAM)
        source(cv, '本片解读；FCIC 访谈巴菲特录音（“it’s assisted by the fact that the two of them became the standard for regulators”）', a, y=1462)


# ======================================================================== 第四章：关键齿轮
def shot_ch4(cv, t):
    # c4a：大跟头
    t0, t1 = win2('c4a')
    a = A(t, t0, t1)
    if a > 0:
        n, cap = ph(['c_foreclosure2', 'c_foreclosure'], 'cx_quote', '止赎房屋（金融危机期间）', '交易所报价板（1941 年影片）')
        window(cv, t, t0, t1, [n], cap, a)
        big_q(cv, t, '“大家都认它”', 1000, WT('c4a', '大家都认它'), 56, a, col=CREAM)
        big_q(cv, t, '差点让它栽了大跟头', 1110, WT('c4a', '大跟头'), 60, a, col=RED_X)
    # c4b：房贷 → 打包证券 → 评级 → 好卖
    t0, t1 = win2('c4b')
    a = A(t, t0, t1)
    if a > 0:
        n, cap = ph(['c_deserted'], 'ny_floor', '金融危机后空置的房子', '纽约证券交易所交易大厅（资料片）')
        window(cv, t, t0, t1, [n], cap, a)
        k = appear(t, 'c4b', '成千上万笔房贷')
        if k > 0:
            for j in range(12):
                kk = eo((t - WT('c4b', '成千上万笔房贷') - j * 0.04) / 0.3)
                x = 120 + (j % 4) * 50; y = 1000 + (j // 4) * 50
                cv.rrect(x, y, x + 38, y + 38, 6, CREAM * 0.5, a * kk)
            cv.text('房贷', 195, 1180, 26, 'sans_med', col=CREAM, a=a * k)
        k2 = appear(t, 'c4b', '打包成证券')
        if k2 > 0:
            arrow(cv, (330, 1060), (420, 1060), a * k2, col=GREY)
            flow_box(cv, 530, 1060, '证券', a * k2, col=CREAM, w=180, sub='打包')
        k3 = appear(t, 'c4b', '请评级机构')
        if k3 > 0:
            arrow(cv, (630, 1060), (720, 1060), a * k3, col=GOLD)
            cv.circle((830, 1060), 70, GOLD, a * k3, 4)
            cv.text('三A', 830, 1060, 44, 'sans_bold', col=GOLD_L, a=a * appear(t, 'c4b', '拿到三A'), glow=0.2)
        k4 = appear(t, 'c4b', '才好卖')
        if k4 > 0: cv.text('拿到三A，才好卖', W / 2, 1260, 44, 'serif_black', gold=True, a=a * k4)
        source(cv, 'FCIC 最终报告“结论”（“could not have been marketed and sold without their seal of approval”）；流程为示意', a, y=1462)
    # c4c：每个工作日 30 只
    t0, t1 = win2('c4c')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['bond_cert'], cy=WCY, h=WH, a=a, cap='债券凭证（1941 年影片）')
        chip(cv, '2006 年', W / 2, 900, 32, a * appear(t, 'c4c', '二零零六年'), col=GOLD)
        tw = WT('c4c', '三十只')
        for j in range(30):
            kk = eo((t - tw + 0.4 - j * 0.035) / 0.25)
            if kk <= 0: continue
            x = 180 + (j % 10) * 80; y = 1010 + (j // 10) * 80
            cv.circle((x, y), 30, GOLD, a * kk, 2)
            cv.text('AAA', x, y, 18, 'oswald', col=GOLD_L, a=a * kk)
        k = appear(t, 'c4c', '每个工作日')
        if k > 0: cv.text('每个工作日，30 只', W / 2, 1290, 48, 'serif_black', col=CREAM, a=a * k)
        source(cv, 'FCIC 最终报告“结论”（“In 2006 alone, Moody’s put its triple-A stamp of approval on 30 mortgage-related securities every working day.”）', a, y=1462)
    # c4d：委员会列出的原因
    t0, t1 = win2('c4d')
    a = A(t, t0, t1)
    if a > 0:
        n, cap = ph(['c_lehman'], 'cx_board', '雷曼兄弟总部（2008-09-15）', '交易所报价（1941 年影片）')
        window(cv, t, t0, t1, [n], cap, a)
        rows = [('模型有缺陷', '模型有缺陷'), ('一心抢市场份额', '抢市场份额'), ('付钱的金融公司施压', '施加压力'), ('监管形同虚设', '监管')]
        for j, (s, w) in enumerate(rows):
            kk = appear(t, 'c4d', w)
            if kk <= 0: continue
            x = 300 + (j % 2) * 480; y = 1000 + (j // 2) * 140
            cv.rrect(x - 220, y - 50, x + 220, y + 50, 14, (0.10, 0.05, 0.05), a * kk * 0.9)
            cv.rrect(x - 220, y - 50, x + 220, y + 50, 14, RED_X, a * kk * 0.8, fill=False, th=2)
            cv.text(s, x, y, 34, 'sans_bold', col=CREAM, a=a * kk)
        source(cv, 'FCIC 最终报告“结论”（“the flawed computer models, the pressure from financial firms that paid for the ratings, the relentless drive for market share … the absence of meaningful public oversight”）', a, y=1462)
    # c4e：巴菲特：同一个错觉（引出原声）
    t0, t1 = S('c4e') - 0.45, S('c4e') + SEG['c4e']['dur'] + 0.6
    a = A(t, t0, t1, 0.4, 0.3)
    if a > 0:
        n = first_have(['c_buffett_2010'])
        if n: photo_win(cv, n, t, t0, t1, cy=WCY, h=WH, a=a, cap='巴菲特（2010 年）', focus=(0.5, 0.4))
        else: seq(cv, t, t0, t1, ['cx_floor'], cy=WCY, h=WH, a=a)
        k = appear(t, 'c4e', '大股东')
        if k > 0: chip(cv, '当时仍是穆迪的大股东', W / 2, 950, 32, a * k, col=GOLD)
        big_q(cv, t, '掉进同一个错觉的，不只是它们', 1080, WT('c4e', '掉进'), 48, a, col=CREAM)
    # c4f：大批下调；股价跌约八成
    t0, t1 = win2('c4f')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['cx_quote', 'cx_board'], cy=WCY, h=WH, a=a, cap='交易所报价板（1941 年影片）')
        k = appear(t, 'c4f', '穆迪的股价')
        if k > 0:
            price_chart(cv, t, WT('c4f', '穆迪的股价') - 0.2, a * k, '2003-01', '2010-12', y0=900, y1=1320, vmax=90,
                        marks=[('2007-02', 'high', '$76', WT('c4f', '七十六美元')), ('2009-03', 'low', '$15.6', WT('c4f', '十五点六美元'))], dur=2.4)
        k2 = appear(t, 'c4f', '八成', lead=0.2)
        if k2 > 0: cv.text('−80%', 840, 960, 80, 'oswald', col=RED_X, a=a * k2, glow=0.15, scale=1.2 - 0.2 * k2)
        chip(cv, '2007 年夏起：大批下调评级', W / 2, 880, 26, a * appear(t, 'c4f', '大批下调') * (1 - k), col=CREAM)
        source(cv, '雅虎财经 MCO 月线（按拆股调整；2007-02 最高 76.09，2009-03 最低 15.57）；FCIC 访谈（2007 年 7 月起大批下调）', a, y=1462)
    # c4g：多德-弗兰克；和解承认关键事实
    t0, t1 = S('c4g') - 0.45, CHE('ch4')
    a = A(t, t0, t1)
    if a > 0:
        n, cap = ph(['c_7wtc2', 'c_7wtc'], 'ny_floor2', '纽约世贸中心一号楼与七号楼（2019）', '纽约证券交易所交易大厅（资料片）')
        window(cv, t, t0, t1, [n], cap, a)
        k = appear(t, 'c4g', '二零一零年')
        if k > 0:
            cv.text('2010', 250, 1000, 80, 'oswald', col=GOLD_L, a=a * k)
            cv.text('多德-弗兰克法案 第 939A 条', 250, 1080, 26, 'sans_bold', col=CREAM, a=a * k)
            cv.text('删掉监管规则里对评级的引用', 250, 1125, 22, 'sans_light', col=GREY, a=a * appear(t, 'c4g', '删掉'))
        k2 = appear(t, 'c4g', '那笔和解')
        if k2 > 0:
            cv.text('2017', 820, 1000, 80, 'oswald', col=GOLD_L, a=a * k2)
            cv.text('近 8.64 亿美元和解', 820, 1080, 26, 'sans_bold', col=CREAM, a=a * k2)
            cv.text('穆迪承认了关键事实', 820, 1125, 22, 'sans_light', col=GREY, a=a * appear(t, 'c4g', '承认'))
        source(cv, '多德-弗兰克法案第 939A 条；美国司法部新闻稿 17-070（“a Statement of Facts in which Moody’s acknowledges key aspects of its conduct”）', a, y=1462)


# ======================================================================== 第五章：信誉崩了，生意还在
BIG3 = [('2020', 94.1), ('2021', 93.2), ('2022', 91.1), ('2023', 91.9)]
MED = [('2020', 5.1), ('2021', 5.6), ('2022', 7.3), ('2023', 6.7)]


def shot_ch5(cv, t):
    # c5a：顾客跑了吗？
    t0, t1 = win2('c5a')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['ny_floor'], cy=WCY, h=WH, a=a, cap='纽约证券交易所交易大厅（资料片）')
        for j, (s, w) in enumerate((('信誉受重创', '信誉'), ('罚款交了', '罚款'), ('规矩改了', '规矩'))):
            chip(cv, s, W / 2 - 300 + j * 300, 960, 34, a * appear(t, 'c5a', w), col=CREAM)
        big_q(cv, t, '顾客跑了吗？', 1120, WT('c5a', '顾客跑了吗'), 80, a)
    # c5b：三家收入份额 94% → 92%
    t0, t1 = win2('c5b')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['ny_floor2'], cy=WCY, h=WH, a=a, cap='纽约证券交易所交易大厅（资料片）')
        k = appear(t, 'c5b', '没有', lead=0.15)
        if k > 0: cv.text('没有。', W / 2, 920, 64, 'serif_black', gold=True, a=a * k, glow=0.2)
        tb = WT('c5b', '三家大机构')
        vbars(cv, t, [(y, v, tb + 0.15 * j, GOLD if y in ('2020', '2023') else GOLD * 0.6, None) for j, (y, v) in enumerate(BIG3)], a * appear(t, 'c5b', '三家大机构'),
              x0=200, x1=880, base=1340, hmax=300, fmt=lambda v: f'{v:.1f}%', size=36, lab=26)
        k2 = appear(t, 'c5b', '两个百分点')
        if k2 > 0: chip(cv, '三家大机构的收入份额 · 只降了约 2 个百分点', W / 2, 1010, 26, a * k2, col=CREAM)
        source(cv, 'SEC 评级办公室 NRSRO 年度报告（2025 年 1 月）Chart 12（Large NRSROs 收入份额）', a, y=1462)
    # c5c：中型机构 5.1% → 6.7%
    t0, t1 = win2('c5c')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['cx_floor'], cy=WCY, h=WH, a=a, cap='交易所交易大厅（1941 年影片）')
        tb = WT('c5c', '中型评级机构')
        vbars(cv, t, [(y, v, tb + 0.15 * j, NAVY, None) for j, (y, v) in enumerate(MED)], a,
              x0=200, x1=880, base=1300, hmax=260, fmt=lambda v: f'{v:.1f}%', size=36, lab=26)
        k = appear(t, 'c5c', '大局没变')
        if k > 0: cv.text('在追，可大局没变', W / 2, 940, 48, 'serif_black', col=CREAM, a=a * k)
        chip(cv, '中型评级机构的收入份额', W / 2, 880, 26, a * appear(t, 'c5c', '中型'), col=NAVY * 1.4)
        source(cv, 'SEC 评级办公室 NRSRO 年度报告（2025 年 1 月）Chart 12（Medium NRSROs 收入份额）', a, y=1462)
    # c5d：回顾可口可乐：护城河被攻破
    t0, t1 = win2('c5d')
    a = A(t, t0, t1)
    if a > 0:
        recap(cv, t, t0, t1, 's1_coke', '第一季 · 可口可乐', a=a)
        k = appear(t, 'c5d', '穆迪的信誉')
        if k > 0:
            cv.text('信誉：被攻破了', W / 2, 1020, 52, 'serif_black', col=RED_X, a=a * k)
            cv.text('护城河：还在', W / 2, 1140, 64, 'serif_black', gold=True, a=a * appear(t, 'c5d', '护城河却还在'), glow=0.2)
        source(cv, '第一季 · 可口可乐《38年一股未卖》（本系列）；本片解读', a, y=1462)
    # c5e：2009 年卖出一部分
    t0, t1 = win2('c5e')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['cx_floor'], cy=WCY, h=WH, a=a, cap='交易所交易大厅（1941 年影片）')
        chip(cv, '2009 年：卖掉一部分穆迪', W / 2, 920, 34, a * appear(t, 'c5e', '二零零九年'), col=GOLD)
        k = appear(t, 'c5e', '年初')
        if k > 0:
            flow_box(cv, 300, 1100, '年初', a * k, col=CREAM, sub='为买陶氏化学、瑞士再保险筹钱', w=400, h=110)
        k2 = appear(t, 'c5e', '年底')
        if k2 > 0:
            flow_box(cv, 790, 1100, '年底', a * k2, col=GOLD, sub='为一笔大收购筹钱', w=360, h=110)
            cv.text('?', 790, 1210, 56, 'serif_black', col=GOLD_L, a=a * k2)
        source(cv, '伯克希尔 2009 年信（“In 2009, our largest sales were in ConocoPhillips, Moody’s …”）', a, y=1462)
    # c5f：引出原声（没卖的错）
    t0, t1 = S('c5f') - 0.45, S('c5f') + SEG['c5f']['dur'] + 0.6
    a = A(t, t0, t1, 0.4, 0.3)
    if a > 0:
        n = first_have(['c_buffett_2010', 'c_obama_buffett'])
        if n: photo_win(cv, n, t, t0, t1, cy=WCY, h=WH, a=a, cap='巴菲特（2010 年）', focus=(0.5, 0.4))
        chip(cv, '2010 年 5 月 · 对危机调查委员会', W / 2, 1000, 32, a * appear(t, 'c5f', '调查委员会'), col=GOLD)
    # c5g：持股：4800 万 → 2467 万
    t0, t1 = win2('c5g')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['ny_floor2'], cy=WCY, h=WH, a=a, cap='纽约证券交易所交易大厅（资料片）')
        k = appear(t, 'c5g', '涨到很高时没卖')
        if k > 0: cv.text('错在：涨到很高时没卖', W / 2, 920, 44, 'serif_black', col=CREAM, a=a * k)
        tb = WT('c5g', '到二零一三年')
        vbars(cv, t, [('2007 年底', 4800, tb - 0.4, GOLD * 0.6, '占 19.1%'), ('2013 年底', 2467, tb + 0.3, GOLD, '占 11.5%'), ('2025 年底', 2467, WT('c5g', '一股没动'), GOLD_L, '占 13.9%')],
              a * appear(t, 'c5g', '到二零一三年', lead=0.5), x0=200, x1=880, base=1340, hmax=300, fmt=lambda v: f'{v:,.0f} 万股', size=32, lab=26)
        source(cv, '伯克希尔 2007、2013 年信持股表；2025 年年报持股表（24,669,778 股，13.9%）', a, y=1462)
    # c5h：回购替股东增持：11.5% → 13.9%（回顾苹果）
    t0, t1 = win2('c5h')
    a = A(t, t0, t1)
    if a > 0:
        tr = WT('c5h', '第一季苹果')
        if t < tr - 0.2:
            seq(cv, t, t0, tr + 0.3, ['cx_quote'], cy=WCY, h=WH, a=a, cap='交易所报价板（1941 年影片）')
        else:
            recap(cv, t, tr - 0.45, t1, 's1_apple', '第一季 · 苹果', a=a)
        k = appear(t, 'c5h', '回购股票')
        if k > 0:
            gauge(cv, 330, 1110, 120, lerp(0.115, 0.139, eexp((t - WT('c5h', '百分之十三点九') + 0.2) / 0.9)), a * k, label='伯克希尔持股比例', fmt='{:.1f}%', size=50)
            cv.text('没花一分钱', 780, 1050, 52, 'serif_black', gold=True, a=a * appear(t, 'c5h', '没花一分钱'))
            cv.text('2013 年 11.5% → 2025 年 13.9%', 780, 1140, 30, 'sans_med', col=CREAM, a=a * appear(t, 'c5h', '百分之十三点九'))
        source(cv, '伯克希尔 2013 年信持股表（11.5%）；2025 年年报持股表（13.9%）；第一季 · 苹果《十年苹果》（本系列）', a, y=1462)
    # c5i：成本 2.48 亿，市值 126 亿，约 51 倍；分红 9300 万
    t0, t1 = S('c5i') - 0.45, CHE('ch5')
    a = A(t, t0, t1)
    if a > 0:
        n, cap = ph(['c_7wtc'], 'ny_floor', '纽约世贸中心七号楼：穆迪总部所在', '纽约证券交易所交易大厅（资料片）')
        window(cv, t, t0, t1, [n], cap, a)
        chip(cv, '2025 年底 · 这部分持股', W / 2, 890, 28, a * appear(t, 'c5i', '二零二五年底'), col=GOLD)
        vbars(cv, t, [('成本', 2.48, WT('c5i', '成本'), GREY, None), ('市值', 126.03, WT('c5i', '市值'), GOLD, None)], a,
              x0=250, x1=830, base=1330, hmax=340, fmt=lambda v: f'${v:,.2f} 亿' if v < 10 else f'${v:,.0f} 亿', size=40, lab=28)
        k = appear(t, 'c5i', '五十一倍', lead=0.2)
        if k > 0: cv.text('≈51×', 850, 990, 80, 'oswald', col=GOLD_L, a=a * k, glow=0.2, scale=1.2 - 0.2 * k)
        k2 = appear(t, 'c5i', '分红')
        if k2 > 0: chip(cv, '2025 年分红：$9300 万', 300, 990, 30, a * k2, col=CREAM)
        source(cv, '伯克希尔 2025 年年报持股表（成本 248、市值 12,603、分红 93，百万美元）；51 倍为本片推算（不含已卖出部分与历年分红）', a, y=1462)


# ======================================================================== 第六章：还能好多久
RISKS = [('利益冲突', '仍然是发债的公司付钱，请它打分'), ('周期', '评级收入三分之二靠新发债；订阅收入是缓冲'), ('监管与对手', '巴菲特 2010 年：双寡头格局“可能会变”')]


def shot_ch6(cv, t):
    t0, t1 = S('c6a') - 0.45, CHE('ch6')
    a = A(t, t0, t1)
    if a <= 0: return
    cur = 2 if t >= S('c6d') - 0.2 else 1 if t >= S('c6c') - 0.2 else 0 if t >= S('c6b') - 0.2 else -1
    ks = [appear(t, 'c6b', '第一'), appear(t, 'c6c', '第二'), appear(t, 'c6d', '第三')]
    if cur < 0:
        seq(cv, t, t0, S('c6b') - 0.2, ['ny_floor2'], cy=WCY, h=WH, a=a, cap='纽约证券交易所交易大厅（资料片）')
        big_q(cv, t, '这条护城河，还能守多久？', 980, WT('c6a', '还能守多久'), 60, a)
        k = appear(t, 'c6a', '三件事')
        if k > 0: cv.text('有三件事，要盯住', W / 2, 1110, 46, 'sans_bold', col=GOLD_L, a=a * k)
    else:
        if cur == 0:
            seq(cv, t, S('c6b') - 0.45, S('c6c') + 0.1, ['bond_cert'], cy=WCY, h=WH, a=a, cap='债券凭证（1941 年影片）')
        elif cur == 1:
            seq(cv, t, S('c6c') - 0.45, S('c6d') + 0.1, ['ny_ticker'], cy=WCY, h=WH, a=a, cap='纽约证券交易所报价带（资料片）')
        else:
            n, cap = ph(['c_7wtc'], 'ny_floor', '纽约世贸中心七号楼：穆迪总部所在', '纽约证券交易所交易大厅（资料片）')
            window(cv, t, S('c6d') - 0.45, t1, [n], cap, a)
        item_list(cv, t, a, RISKS, ks, cur, col=RED_X * 1.1)
    src = {0: 'FCIC 最终报告“结论”（付费方施压）；发行人付费模式至今未变（SEC 评级办公室 2025 年报告）',
           1: '穆迪 2025 年全年业绩新闻稿（MIS 交易性收入占 67%；MA 经常性收入占 96%）；周期影响为本片解读',
           2: 'FCIC 访谈巴菲特录音（“It’s a natural duopoly to some extent, now that may get changed”）；SEC 2025 年报告 Chart 12'}.get(cur, '本片过渡')
    source(cv, src, a, y=1462)


# ======================================================================== 第七章：带走什么 + 下期预告
LESSONS = [('定价权，不一定来自喜爱', '喜诗靠顾客喜欢；穆迪靠顾客离不开'), ('护城河保护生意，不分对错', '犯了大错，顾客照样离不开——所以监管要一直盯着'),
           ('伟大的公司，股价也会跌八成', '没卖是个错；留下的那一半，二十多年后约 51 倍')]
END_TXT = '下期 · BNSF'


def shot_ch7(cv, t):
    # c7a–c7d：三条收获
    t0, t1 = S('c7a') - 0.45, S('c7e') + 0.1
    a = A(t, t0, t1)
    if a > 0:
        cur = 2 if t >= S('c7d') - 0.2 else 1 if t >= S('c7c') - 0.2 else 0 if t >= S('c7b') - 0.2 else -1
        nm = {-1: ['ny_floor'], 0: ['s1_sees'], 1: ['c_7wtc'], 2: ['cx_quote']}[cur]
        cap = {-1: '纽约证券交易所交易大厅（资料片）', 0: '本系列第一季成片片段（喜诗糖果）', 1: '纽约世贸中心七号楼：穆迪总部所在', 2: '交易所报价板（1941 年影片）'}[cur]
        ta = {-1: t0, 0: S('c7b') - 0.45, 1: S('c7c') - 0.45, 2: S('c7d') - 0.45}[cur]
        tb = {-1: S('c7b') + 0.1, 0: S('c7c') + 0.1, 1: S('c7d') + 0.1, 2: t1}[cur]
        if nm[0].startswith('c_') and not M.have(nm[0]): nm = ['ny_floor2']
        window(cv, t, ta, tb, nm, cap, a)
        k = appear(t, 'c7a', '三件事')
        if k > 0: cv.text('从穆迪身上，带走三件事', W / 2, 890, 40, 'serif_black', gold=True, a=a * k)
        item_list(cv, t, a, LESSONS, [appear(t, 'c7b', '第一'), appear(t, 'c7c', '第二'), appear(t, 'c7d', '第三')], cur, y0=1000, dy=130)
        source(cv, {0: '第一季 · 喜诗糖果；FCIC 访谈“unwilling customer”（本片解读）', 1: 'SEC 2025 年报告 Chart 12；多德-弗兰克法案第 939A 条（本片解读）',
                    2: 'MCO 月线；FCIC 访谈；伯克希尔 2025 年年报持股表（本片解读）'}.get(cur, '本片总结'), a, y=1462)
    # c7e：结语
    t0, t1 = S('c7e') - 0.45, S('p1') + 0.1
    a = A(t, t0, t1)
    if a > 0:
        n, cap = ph(['c_7wtc'], 'ny_floor2', '纽约世贸中心七号楼：穆迪总部所在', '纽约证券交易所交易大厅（资料片）')
        window(cv, t, t0, t1, [n], cap, a)
        k = appear(t, 'c7e', '不情愿的顾客')
        if k > 0: cv.text('不情愿的顾客，', W / 2, 1000, 66, 'serif_black', col=CREAM, a=a * k)
        k2 = appear(t, 'c7e', '也是顾客')
        if k2 > 0: cv.text('也是顾客', W / 2, 1110, 84, 'serif_black', gold=True, a=a * k2, glow=0.25)
        k3 = appear(t, 'c7e', '没得选')
        if k3 > 0: chip(cv, '护城河，建在“没得选”三个字上', W / 2, 1240, 34, a * k3, col=GOLD_L)
    # p1：线索：铁路债券；为买一家铁路公司筹钱
    t0, t1 = win2('p1')
    a = A(t, t0, t1)
    if a > 0:
        n = first_have(['c_rrgroups'])
        tl = WT('p1', '二零零九年')
        if t < tl - 0.1 or not n:
            seq(cv, t, t0, tl + 0.3, ['rr_loco'], cy=WCY, h=WH, a=a, cap='蒸汽机车牵引货车（1898 年影片）')
        if n and t >= tl - 0.45:
            photo_win(cv, n, t, tl - 0.45, t1, cy=WCY, h=WH, a=a, cap='约翰·穆迪 1904 年著作中的美国铁路集团图')
        chip(cv, '下期线索', W / 2, 890, 30, a * appear(t, 'p1', '线索'), col=GOLD_L)
        k = appear(t, 'p1', '铁路债券')
        if k > 0:
            cv.text('1909', 260, 1010, 80, 'oswald', col=GOLD_L, a=a * k)
            cv.text('穆迪最早打分的：铁路债券', 260, 1090, 26, 'sans_bold', col=CREAM, a=a * k)
        k2 = appear(t, 'p1', '二零零九年')
        if k2 > 0:
            cv.text('2009', 820, 1010, 80, 'oswald', col=GOLD_L, a=a * k2)
            cv.text('卖掉一部分穆迪', 820, 1090, 26, 'sans_bold', col=CREAM, a=a * k2)
            cv.text('为买下一家铁路公司筹钱', 820, 1135, 24, 'sans_light', col=GOLD_L, a=a * appear(t, 'p1', '铁路公司'))
        qcard(cv, 'qsales', t, WT('p1', '铁路公司') - 0.1, t1, cy=1290, en=24, cn=30, a=a, typing=0.8, w=900)
        source(cv, '1909 年铁路债券评级（Imperial College 等）；伯克希尔 2009 年信（“in anticipation of our BNSF purchase”）', a, y=1462)
    # p2：下期预告 BNSF
    t0, t1 = S('p2') - 0.45, CH['end'][0] + 0.4
    a = A(t, t0, t1, 0.4, 0.2)
    if a > 0:
        seq(cv, t, t0, t1, ['rr_station', 'rr_elev'], cy=WCY, h=WH, a=a, cap='火车进站（1897 年影片）· 纽约高架铁路（1903 年影片）')
        k = appear(t, 'p2', '下一期', lead=0.2)
        if k > 0:
            chip(cv, '下期', W / 2, 890, 34, a * k, col=GOLD_L)
            cv.text('BNSF', W / 2, 1010, 130, 'oswald', col=GOLD_L, a=a * appear(t, 'p2', 'B N S F', lead=0.2), glow=0.25)
            cv.text('伯灵顿北方圣太菲铁路', W / 2, 1110, 34, 'sans_med', col=CREAM, a=a * appear(t, 'p2', 'B N S F'))
        k2 = appear(t, 'p2', '护城河最宽')
        if k2 > 0: cv.text('护城河最宽的生意，为什么回报却很一般？', W / 2, 1220, 34, 'serif_black', col=CREAM, a=a * k2)
        k3 = appear(t, 'p2', '押注美国')
        if k3 > 0: cv.text('为什么说，买下它是押注美国的未来？', W / 2, 1300, 34, 'serif_black', gold=True, a=a * k3)
        k4 = eo((t - E('p2') - 0.2) / 0.5)              # 落版字：片尾接住它，化作粒子汇成 logo（common.shot_end）
        if k4 > 0: cv.text(END_L, W / 2, END_Y, END_SZ, 'serif_black', gold=True, a=a * k4, glow=0.15)
        source(cv, '第二季片单（docs/第二季规划.md）', a * 0.7 * (1 - k4), y=1462)
