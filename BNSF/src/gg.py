"""第二季第二期《全押美国——巴菲特与 BNSF》全部镜头（开场、片名、第一至七章、下期预告）。

版式（沿用第一期）：上方画窗（cy≈540，1000×560）放真实影像；下方 y 880–1420 放动画解读；y≈1462 出处；y≈1555 字幕。
素材：
  · archive.org：1942 年《A Great Railroad at Work》g_*（只取不带“New Haven”字样的镜头）、1897/1898 年爱迪生公司铁路影片 rr_*、
    1941 年交易所影片 cx_*、纽约证券交易所资料片 ny_*（公有领域 / Prelinger Archives）；
  · 维基共享资源：BNSF / 联合太平洋 / 诺福克南方列车、沃斯堡、卡车、罐车、巴菲特、芒格、阿贝尔等照片（assets/media/credits.json）；
  · 本系列成片片段 s1_japan（日本五大商社），画面标「回顾 · 日本商社」；
  · 其余为股东信、年报、新闻稿、STB 公告数据的图表与示意动画。铁路网图是“主要干线走向示意”，不是精确线路图；自绘图形不画任何公司的商标。
时间全部挂在旁白句子与词锚点上（WT 用朗读文本）。
"""
from gg_base import *          # noqa
from gg_base import _SAY, _landmask        # noqa
from script import SEASON      # noqa

WCY, WH = 540, 560          # 上方画窗 1000×560（y 260–820，在章节导航之下）
RED_X = C(225, 70, 60)
SILVER = C(190, 198, 212)
NS_C = C(120, 160, 230)


def A(t, t0, t1, fi=0.4, fo=0.4): return env(t, t0, t1, fi, fo)


def CHE(cid):
    """本章画面结束时刻：下一章（章节卡）开始后 0.2 秒；第七章为片尾开始后 0.4 秒"""
    k = int(cid[2])
    return CH['ch%d' % (k + 1)][0] + 0.2 if k < 7 else CH['end'][0] + 0.4


def win2(i, j=None, pre=0.45, post=-0.1):
    """从 i 句开口前 pre 秒，到 j（或 i）句之后的下一句开口后 0.1 秒（前后镜头叠化，不掉黑）"""
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


def tick(cv, x, y, r, a, col=GOLD_L, th=6):
    if a <= 0.004: return
    cv.line((x - r, y), (x - r * 0.3, y + r * 0.7), col, a, th); cv.line((x - r * 0.3, y + r * 0.7), (x + r, y - r * 0.8), col, a, th)


def vis(cv, t, t0, t1, names, a, focus=None, cap=None):
    """画窗：names 按顺序取第一张已入库的照片（c_*）；没有照片或首项是影片时，把影片按原速串接"""
    photos = [n for n in names if n.startswith('c_') and M.have(n)]
    clips = [n for n in names if not n.startswith('c_') and M.have(n)]
    if photos and (names[0].startswith('c_') or not clips):
        photo_win(cv, photos[0], t, t0, t1, cy=WCY, h=WH, a=a, cap=cap if cap is not None else capof(photos[0]), focus=focus or (0.5, 0.5))
    elif clips:
        seq(cv, t, t0, t1, clips, cy=WCY, h=WH, a=a, cap=cap, focus=focus)


def recap(cv, t, t0, t1, clip, label, a=1.0):
    """回顾：本系列成片（竖屏）整幅放进画窗；左上角金色「回顾 · 某期」标签"""
    al = env(t, t0, t1, 0.45, 0.45) * a
    if al <= 0.004: return
    M.frame(cv, clip, t, t0, t1, cy=WCY, w=1000, h=WH, z0=1.0, z1=1.0, a=al, fit='contain', warm=0.0, sat=1.0,
            cap='本系列成片片段', hold=False, src_t0=M.USABLE.get(clip, (0, 0))[0])
    k = eo((t - t0 - 0.2) / 0.5)
    chip(cv, '回顾 · ' + label, 90, 300, 28, al * k, col=GOLD_L, anchor='l')


GATES = [('第一关', '优势是真的', 'REAL'), ('第二关', '对手难复制', 'HARD TO COPY')]


def two_gates(cv, t, a, ks, y=1110, hl=None, done=(0, 0)):
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
        if done[j] > 0:
            cv.circle((x + 170, yy - 92), 34, GOLD_L, a * done[j], 4)
            tick(cv, x + 170, yy - 92, 18, a * done[j])


def flow_box(cv, x, y, txt, a, col=GOLD, w=260, h=86, sub=None, size=34):
    if a <= 0.004: return
    cv.rrect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, 16, (0.06, 0.06, 0.08), a * 0.92)
    cv.rrect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, 16, col, a * 0.85, fill=False, th=2)
    cv.text(txt, x, y - (12 if sub else 0), size, 'sans_bold', col=CREAM, a=a)
    if sub: cv.text(sub, x, y + 24, 20, 'sans_light', col=GREY, a=a)


def stack_bar(cv, t, t0, a, y, parts, x0=110, x1=970, h=64, label=None, total_txt=None, step=0.35):
    """横向堆叠条：parts = [(名称, 数值, 颜色)]（按总和归一），从左到右依次长出；名称写在色块下方"""
    tot = sum(p[1] for p in parts)
    x = x0; tt = t0
    for j, (nm, v, col) in enumerate(parts):
        e = eexp((t - tt) / 0.7)
        L = (x1 - x0) * v / tot
        if e > 0:
            gbar(cv, x, y - h / 2, x + max(L * e, 2), y + h / 2, col, a, horizontal=True, glow=0.1, sheen_t=t - tt)
            cv.text(f'{v:g}万', x + L / 2, y, 26, 'sans_bold', col=INK, a=a * min(1, e * 2))
            cv.text(nm, x + L / 2, y + h / 2 + 26 + (24 if j % 2 else 0), 22, 'sans_med', col=CREAM, a=a * min(1, e * 2))
        x += L; tt += step
    if label: cv.text(label, x0, y - h / 2 - 28, 26, 'sans_med', col=CREAM, a=a, anchor='l')
    if total_txt: cv.text(total_txt, x1, y - h / 2 - 30, 34, 'sans_bold', col=GOLD_L, a=a * eo((t - tt) / 0.5), anchor='r')


def item_list(cv, t, a, rows, ks, cur, y0=960, dy=130, col=GOLD):
    """编号清单：rows = [(标题, 小字)]"""
    for j, (nm, sub) in enumerate(rows):
        k = ks[j]
        if k <= 0: continue
        y = y0 + j * dy; on = j == cur
        cv.rrect(90, y - 52, 990, y + 52, 14, (0.07, 0.07, 0.09) if on else (0.05, 0.05, 0.06), a * k * 0.9)
        cv.rrect(90, y - 52, 990, y + 52, 14, col if on else GREY, a * k * (0.9 if on else 0.4), fill=False, th=2)
        cv.text(f'0{j + 1}', 145, y, 34, 'oswald', col=col if on else GREY, a=a * k)
        cv.text(nm, 210, y - 16, 34, 'sans_bold', col=CREAM if on else GREY, a=a * k, anchor='l')
        cv.text(sub, 210, y + 26, 22, 'sans_light', col=CREAM if on else GREY, a=a * k, anchor='l')


def compare_bars(cv, t, a, rows, x0=150, x1=760, y0=1010, dy=120, vmax=None, unit=''):
    """横向对照条：rows = [(标签, 数值, 文字, 颜色, 出现时刻)]，标签在条上方"""
    vmax = vmax or max(r[1] for r in rows)
    for j, (lb, v, txt, col, ts) in enumerate(rows):
        e = eexp((t - ts) / 0.9)
        if e <= 0: continue
        y = y0 + j * dy
        L = max((x1 - x0) * v / vmax * e, 6)
        cv.text(lb, x0, y - 44, 28, 'sans_med', col=CREAM, a=a * min(1, e * 2), anchor='l')
        gbar(cv, x0, y - 22, x0 + L, y + 22, col, a, horizontal=True, glow=0.12, sheen_t=t - ts)
        cv.text(txt, x0 + L + 16, y, 36, 'sans_bold', col=GOLD_L if col is GOLD else CREAM, a=a * min(1, e * 2), anchor='l', shadow=0.6)


# ======================================================================== 美国铁路网（主要干线走向示意）
CITY = {
    'SEA': (47.6, -122.3), 'POR': (45.5, -122.7), 'SPK': (47.7, -117.4), 'HAV': (48.55, -109.7), 'MOT': (48.2, -101.3),
    'FAR': (46.9, -96.8), 'MSP': (44.98, -93.27), 'CHI': (41.88, -87.63), 'LA': (34.05, -118.24), 'BAR': (34.9, -117.0),
    'NDL': (34.85, -114.6), 'FLG': (35.2, -111.65), 'BEL': (34.66, -106.78), 'AMA': (35.2, -101.8), 'KC': (39.1, -94.58),
    'GAL': (40.95, -90.37), 'DEN': (39.74, -104.99), 'FTW': (32.75, -97.33), 'HOU': (29.76, -95.37), 'GIL': (44.29, -105.5),
    'ALL': (42.1, -102.87), 'LNK': (40.8, -96.7), 'BIL': (45.78, -108.5), 'OAK': (37.8, -122.27), 'STK': (37.95, -121.29),
    'SLC': (40.76, -111.89), 'OMA': (41.26, -95.93), 'ELP': (31.76, -106.49), 'MSY': (29.95, -90.07), 'MEM': (35.15, -90.05),
    'STL': (38.63, -90.2), 'ATL': (33.75, -84.39), 'ORF': (36.85, -76.29), 'HAR': (40.27, -76.88), 'NYC': (40.7, -74.1),
    'CIN': (39.1, -84.5), 'PIT': (40.44, -80.0), 'BHM': (33.5, -86.8), 'CLT': (35.2, -80.8), 'CLE': (41.5, -81.7),
    'POC': (42.87, -112.45), 'HIN': (45.85, -119.3), 'LIT': (34.75, -92.29), 'SAT': (29.42, -98.49),
}
BNSF_R = [['SEA', 'SPK', 'HAV', 'MOT', 'FAR', 'MSP', 'CHI'], ['POR', 'SPK'], ['LA', 'BAR', 'NDL', 'FLG', 'BEL', 'AMA', 'KC', 'GAL', 'CHI'],
          ['OAK', 'STK', 'BAR'], ['GIL', 'ALL', 'LNK', 'KC'], ['BIL', 'GIL', 'DEN'], ['DEN', 'AMA', 'FTW', 'HOU'], ['KC', 'FTW'],
          ['KC', 'MEM', 'BHM'], ['SPK', 'BIL'], ['LNK', 'GAL']]
UP_R = [['LA', 'SLC', 'OMA', 'CHI'], ['OAK', 'SLC'], ['POR', 'HIN', 'POC', 'SLC'], ['LA', 'ELP', 'SAT', 'HOU', 'MSY'], ['CHI', 'STL', 'LIT', 'HOU'],
        ['OMA', 'KC', 'FTW', 'SAT'], ['DEN', 'OMA']]
NS_R = [['CHI', 'CLE', 'PIT', 'HAR', 'NYC'], ['CHI', 'CIN', 'ATL'], ['ATL', 'CLT', 'ORF'], ['STL', 'CIN'], ['MSY', 'BHM', 'ATL'], ['KC', 'STL'], ['CIN', 'ORF']]
_MAP = {}


def _proj(lat, lon, cx, cy, sc): return (cx + (lon + 96.0) * sc * 0.788, cy - (lat - 38.0) * sc)


def _in_us(lat, lon):
    if lat > 49.2 or lat < 24.8: return False
    if lon > -95 and lat > lerp(49.0, 45.0, cl((lon + 95) / 12)) and lon < -83: return False
    if lon >= -83 and lat > (44.6 if lon < -75.5 else 47.3 - (lon + 67) * 0.3): return False
    if lon < -106.5 and lat < 31.4 + max(0.0, (-111 - lon) * 0.28): return False
    if -106.5 <= lon < -97.2 and lat < lerp(31.8, 26.0, (lon + 106.5) / 9.3): return False
    return True


def map_layer(cx, cy, sc):
    """美国本土点阵（Natural Earth 陆地遮罩，公有领域），预渲染成一层"""
    key = (cx, cy, sc)
    if key not in _MAP:
        m = _landmask()
        x0, y0 = _proj(50, -126, cx, cy, sc); x1, y1 = _proj(24, -66, cx, cy, sc)
        Wd, Hd = int(x1 - x0) + 20, int(y1 - y0) + 20
        rgb = np.zeros((Hd, Wd, 3), np.float32); al = np.zeros((Hd, Wd), np.float32)
        for lat in np.arange(24.5, 49.6, 0.6):
            for lon in np.arange(-125.0, -66.5, 0.6 / 0.788):
                px = int((lon + 180) * 2) % 720; py = int((90 - lat) * 2)
                if m[py, px] > 127 and _in_us(lat, lon):
                    x, y = _proj(lat, lon, cx, cy, sc)
                    cv2.circle(al, (int(x - x0 + 10), int(y - y0 + 10)), 2, 1.0, -1, cv2.LINE_AA)
        rgb[:] = np.array([150, 140, 128], np.float32) / 255
        _MAP[key] = (rgb, al * 0.75, x0 - 10, y0 - 10)
    return _MAP[key]


def routes(cv, routes_, k, col, cx, cy, sc, a, th=4, glow=True):
    """按比例 k 画出各条干线（每条从起点依次长出）"""
    if a <= 0.004 or k <= 0: return
    for r in routes_:
        pts = [_proj(*CITY[c], cx, cy, sc) for c in r]
        segl = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
        tot = sum(segl); L = tot * k; acc = 0
        for i, sl in enumerate(segl):
            if acc >= L: break
            f = min(1.0, (L - acc) / sl)
            p0, p1 = pts[i], (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f)
            if glow: cv.line(p0, p1, col, a * 0.25, th + 6)
            cv.line(p0, p1, col, a, th)
            acc += sl


def us_map(cv, t, a, cx=W / 2, cy=1150, sc=19.0, bnsf=0.0, up=0.0, ns=0.0, pulse=False, labels=()):
    if a <= 0.004: return
    rgb, al, x0, y0 = map_layer(cx, cy, sc)
    cv.over(rgb, al * a, x0, y0)
    routes(cv, UP_R, up, SILVER, cx, cy, sc, a * 0.9, th=3)
    routes(cv, NS_R, ns, NS_C, cx, cy, sc, a * 0.9, th=3)
    routes(cv, BNSF_R, bnsf, GOLD, cx, cy, sc, a, th=4)
    if pulse and bnsf >= 1:
        for r in BNSF_R[:4]:
            flow_dots(cv, t, [_proj(*CITY[c], cx, cy, sc) for c in r], a, col=GOLD_L, n=5, speed=0.18, size=6)
    for (c, txt, kk) in labels:
        if kk <= 0: continue
        x, y = _proj(*CITY[c], cx, cy, sc)
        cv.glow_dot((x, y), 8, GOLD_L, a * kk)
        cv.text(txt, x, y - 26, 22, 'sans_med', col=CREAM, a=a * kk, shadow=0.8)


def map_note(cv, a, y=1420):
    if a > 0.004: cv.text('示意：主要干线走向，非精确线路图', W - 110, y, 18, 'sans_light', col=GREY, a=a * 0.8, anchor='r')


# ======================================================================== 开场
def shot_hook(cv, t):
    a0 = env(t, 0, S('h1') + 0.6, 0.0, 0.5)
    if a0 > 0:                                        # 开场：两条铁轨从远处向画面延伸
        k = eo(t / 1.2)
        for s_ in (-1, 1):
            cv.line((W / 2 + s_ * 18, 700), (W / 2 + s_ * 18 + s_ * 360 * k, 700 + 600 * k), GOLD, a0 * 0.7, 3)
    # h1：两万三千多英里干线、一万三千多座桥、99 条隧道
    t0, t1 = win2('h1')
    a = A(t, t0 + 0.3, t1, 0.5, 0.4)
    if a > 0:
        vis(cv, t, t0, t1, ['g_switch'], a)
        big_q(cv, t, '假如要从头修一条铁路', 920, WT('h1', '假如'), 46, a, col=CREAM)
        for j, (sub, v, unit, fmt) in enumerate((('两万三千多英里', 23759, '英里干线', '{:,.0f}'), ('一万三千多座桥', 13495, '座桥', '{:,.0f}'),
                                                ('九十九条隧道', 99, '条隧道', '{:.0f}'))):
            kk = appear(t, 'h1', sub, lead=0.15)
            if kk <= 0: continue
            x = 220 + j * 320
            cv.text(counter(0, v, t, WT('h1', sub) - 0.15, 0.8, lambda q, f=fmt: f.format(q)), x, 1070, 70, 'oswald', col=GOLD_L, a=a * kk, glow=0.12)
            cv.text(unit, x, 1150, 30, 'sans_med', col=CREAM, a=a * kk)
        k = appear(t, 'h1', '横穿美国西部')
        if k > 0: chip(cv, '横穿美国西部', W / 2, 1270, 34, a * k, col=GOLD_L)
        source(cv, '伯克希尔 2023 年致股东信（“23,759 miles of main track, 99 tunnels, 13,495 bridges”）', a, y=1462)
    # h2：至少 5000 亿美元、几十年
    t0, t1 = win2('h2')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['g_ballast'], a)
        chip(cv, '巴菲特估计', W / 2, 920, 30, a * appear(t, 'h2', '巴菲特估计'), col=GOLD)
        money(cv, t, WT('h2', '五千亿'), '至少 $5000 亿', W / 2, 1060, 120, a, sub='重建这些资产')
        k = appear(t, 'h2', '几十年')
        if k > 0: cv.text('再修上几十年', W / 2, 1260, 52, 'serif_black', col=CREAM, a=a * k)
        source(cv, '伯克希尔 2023 年致股东信（“my guess is that it would cost at least $500 billion to replicate those assets and decades to complete the job”）', a, y=1462)
    # h3：2010 年买下全部股权，作价 345 亿美元（与 5000 亿对照）
    t0, t1 = win2('h3')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['c_bnsf_coal', 'g_smoke'], a, focus=(0.5, 0.55))
        chip(cv, '2010 年 · 伯克希尔买下全部股权', W / 2, 910, 30, a * appear(t, 'h3', '二零一零年'), col=GOLD)
        t5 = WT('h3', '伯克希尔') - 0.1; t3 = WT('h3', '三百四十五亿') - 0.15
        compare_bars(cv, t, a, [('重建估计', 5000, '$5000 亿+', GREY, t5), ('全部股权作价', 345, '$345 亿', GOLD, t3)], y0=1060, dy=150)
        source(cv, '伯克希尔 2025 年致股东信（“acquired this iconic business in 2010 with an equity value of $34.5 billion”，含此前已持有部分）；2023 年信', a, y=1462)
    # h4：天大的便宜？可巴菲特写下：哎哟
    t0, t1 = win2('h4')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['g_wheel'], a)
        to = WT('h4', '哎哟')
        kb = eo((t - WT('h4', '可十几年后') + 0.1) / 0.4)
        big_q(cv, t, '捡了个天大的便宜？', 1000, WT('h4', '捡了个'), 64, a * (1 - kb * 0.75))
        doc_page(cv, t, WT('h4', '可十几年后') - 0.1, t1, 'BERKSHIRE HATHAWAY · 2023 LETTER',
                 ['…have totaled a staggering $22 billion', 'or more than $1½ billion annually. Ouch!'],
                 cy=1170, w=900, size=30, hl='Ouch!', hl_t=to - 0.15, a=a)
        k = eo((t - to + 0.1) / 0.35)
        if k > 0: cv.text('哎哟', W / 2, 1330, 70, 'serif_black', col=RED_X, a=a * k, scale=1.25 - 0.25 * k, glow=0.15)
        source(cv, '伯克希尔 2023 年致股东信', a, y=1462)
    # h5：“吃资本”；回报只算“可以接受”
    t0, t1 = win2('h5')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['g_shop'], a)
        k = appear(t, 'h5', '吃资本')
        if k > 0:
            cv.text('“吃资本”的生意', W / 2, 1030, 66, 'serif_black', gold=True, a=a * k, glow=0.15)
            cv.text('RAILROADS EAT CAPITAL', W / 2, 1110, 24, 'corm_med', col=GOLD_D, a=a * k, track=0.3)
        k2 = appear(t, 'h5', '可以接受')
        if k2 > 0: chip(cv, '回报：只能算“可以接受”', W / 2, 1240, 38, a * k2, col=CREAM)
        source(cv, '伯克希尔 2023 年致股东信（“railroads eat capital”；“an acceptable return on its purchase price”）', a, y=1462)
    # h6：BNSF，美国最大的铁路；护城河宽、回报一般；为什么说是全押美国？
    t0, t1 = S('h6') - 0.45, CH['title'][0] + 0.2
    a = A(t, t0, t1, 0.4, 0.25)
    if a > 0:
        vis(cv, t, t0, t1, ['c_bnsf_bridge', 'c_bnsf_coal', 'g_diesel'], a)
        tq = WT('h6', '巴菲特为什么还说')
        kq = eo((t - tq + 0.2) / 0.4)
        k = appear(t, 'h6', '叫 B N S F', lead=0.2)
        if k > 0:
            cv.text('BNSF', W / 2, 960, 110, 'oswald', col=GOLD_L, a=a * k * (1 - 0.6 * kq), glow=0.2, scale=1.1 - 0.1 * k)
            cv.text('伯灵顿北方圣太菲铁路 · 按货运量美国最大', W / 2, 1050, 28, 'sans_med', col=CREAM, a=a * appear(t, 'h6', '美国最大的铁路') * (1 - 0.6 * kq))
        for j, (lb, v, w_, col) in enumerate((('护城河', '宽', '护城河宽到', GOLD_L), ('回报', '一般', '回报却只是一般', GREY))):
            kk = appear(t, 'h6', w_)
            if kk <= 0: continue
            x = 330 + j * 420
            cv.text(lb, x, 1150, 32, 'sans_med', col=CREAM, a=a * kk * (1 - 0.5 * kq))
            cv.text(v, x, 1225, 64, 'serif_black', col=col, a=a * kk * (1 - 0.5 * kq))
        big_q(cv, t, '为什么说，买下它是', 1310, tq, 42, a, col=CREAM)
        big_q(cv, t, '全押美国经济的未来？', 1380, WT('h6', '全押美国'), 54, a)
        source(cv, '伯克希尔 2020 年致股东信（“America’s largest railroad measured by freight volume”）；2009-11-03 收购新闻稿', a * (1 - kq), y=1462)


def shot_title(cv, t):
    t0, t1 = CH['title'][0], CH['ch1'][0] + 0.6
    a = env(t, t0, t1, 0.02, 0.6)
    if a <= 0: return
    p = t - t0
    flash = math.exp(-p * 5.0)
    k0 = eo(p / 0.5)
    # 一段铁轨伸向远方（透视示意）：两条钢轨 + 一根根亮起的枕木，钢轨越远越淡
    vx, vy = W / 2, 430
    for s_ in (-1, 1):
        for q in range(12):
            f0, f1 = q / 12, (q + 1) / 12
            if f1 > k0: break
            p0 = (vx + s_ * (8 + 330 * f0 * f0), vy + 560 * f0 * f0); p1 = (vx + s_ * (8 + 330 * f1 * f1), vy + 560 * f1 * f1)
            cv.line(p0, p1, GOLD, a * (0.25 + 0.7 * f1), max(2, int(5 * f1 + 1)))
    for j in range(1, 14):
        f = j / 14.0
        kk = eo((p - 0.05 * j) / 0.3)
        if kk <= 0 or f > k0: continue
        y = vy + 560 * f * f; hw = 8 + 330 * f * f + 70 * f * f
        cv.line((vx - hw, y), (vx + hw, y), GOLD_D, a * kk * (0.15 + 0.5 * f), max(2, int(9 * f)))
    cv.glow_dot((vx, vy), 160, GOLD, a * flash * 0.9)
    k = eo((p - 0.15) / 0.6)
    cv.text('全押美国', W / 2, 1060, 128, 'serif_black', gold=True, a=a * k, scale=1.08 - 0.08 * k, glow=0.3)
    cv.text('巴菲特与 BNSF', W / 2, 1200, 56, 'serif_semi', col=CREAM, a=a * eo((p - 0.5) / 0.6))
    cv.text('ALL-IN ON AMERICA', W / 2, 1290, 26, 'corm', col=GOLD, a=a * eo((p - 0.9) / 0.6), track=0.35)


# ======================================================================== 第一章：恐惧里的报价
def shot_ch1(cv, t):
    # c1a：2009 年 10 月，金融危机还没过去
    t0, t1 = win2('c1a')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['c_lehman', 'cx_quote'], a)
        k = appear(t, 'c1a', '二零零九年十月', lead=0.2)
        if k > 0: cv.text('2009 年 10 月', W / 2, 980, 80, 'sans_bold', col=GOLD_L, a=a * k)
        big_q(cv, t, '金融危机还没过去，经济一片低迷', 1120, WT('c1a', '金融危机'), 44, a, col=CREAM)
        source(cv, '伯克希尔 2021 年致股东信（“The Great Recession was in full force”）；照片为 2008-09-15 的雷曼兄弟总部', a, y=1462)
    # c1b：已持有两成多，却没去过沃斯堡总部
    t0, t1 = win2('c1b')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['c_fortworth', 'g_yard'], a)
        k = appear(t, 'c1b', '两成多')
        if k > 0:
            gauge(cv, 300, 1100, 110, 22.5 * eexp((t - WT('c1b', '两成多')) / 0.9), a * k, label='伯克希尔持股', fmt='两成多', size=40)
        k2 = appear(t, 'c1b', '从没去过')
        if k2 > 0:
            cv.text('沃斯堡总部', 760, 1060, 48, 'serif_black', col=CREAM, a=a * k2)
            cv.text('从没去过', 760, 1140, 48, 'serif_black', col=RED_X, a=a * k2)
            cv.text('得克萨斯州', 760, 1205, 24, 'sans_light', col=GREY, a=a * k2)
        source(cv, '伯克希尔 2008 年信（持股超过 20%）；2021 年信（第三大市值持股，“I had never visited its headquarters in Fort Worth”）', a, y=1462)
    # c1c：10 月 22 日见马特·罗斯；当天三季报，市场反应很差
    t0, t1 = win2('c1c', 'c1d')
    a = A(t, t0, t1)
    if a > 0:
        td = S('c1d') - 0.45
        if t < td + 0.5: vis(cv, t, t0, td + 0.5, ['ny_ticker'], a)
        if t >= td: vis(cv, t, td, t1, ['c_buffett_2010', 'c_obama_buffett'], a, focus=(0.5, 0.35))
        y = 1000
        cv.line((140, y + 60), (140 + 800 * eo((t - t0) / 1.2), y + 60), GOLD_D, a * 0.7, 3)
        k = appear(t, 'c1c', '十月二十二日')
        if k > 0:
            cv.glow_dot((240, y + 60), 10, GOLD_L, a * k)
            cv.text('10 月 22 日', 240, y, 36, 'sans_bold', col=GOLD_L, a=a * k)
            cv.text('见 CEO 马特·罗斯', 240, y + 120, 28, 'sans_med', col=CREAM, a=a * appear(t, 'c1c', '马特·罗斯'))
        k2 = appear(t, 'c1c', '当天晚些时候')
        if k2 > 0:
            cv.glow_dot((520, y + 60), 10, RED_X, a * k2)
            cv.text('当天晚些时候', 520, y, 30, 'sans_bold', col=RED_X, a=a * k2)
            cv.text('三季报很难看', 520, y + 120, 28, 'sans_med', col=CREAM, a=a * appear(t, 'c1c', '业绩很难看'))
            cv.text('市场反应很差', 520, y + 162, 28, 'sans_med', col=RED_X, a=a * appear(t, 'c1c', '市场反应很差'))
        k3 = appear(t, 'c1d', '第二天')
        if k3 > 0:
            cv.glow_dot((800, y + 60), 10, GOLD_L, a * k3)
            cv.text('第二天', 800, y, 36, 'sans_bold', col=GOLD_L, a=a * k3)
            cv.text('更好的长久归宿', 800, y + 120, 28, 'sans_med', col=CREAM, a=a * appear(t, 'c1d', '更好的长久归宿'))
            cv.text('报出最高价', 800, y + 162, 28, 'sans_bold', col=GOLD_L, a=a * appear(t, 'c1d', '最高价'))
        src_txt = ('伯克希尔 2021 年致股东信（10 月 22 日见 Matt Rose；当天 BNSF 发布三季报，“the market’s reaction was negative”；第二天提出伯克希尔是更好的归宿，并报出最高价）')
        source(cv, src_txt, a, y=1462)
    # c1e：11 天后宣布：每股 100 美元；含 100 亿债务总价约 440 亿；史上最大收购
    t0, t1 = win2('c1e')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['ny_floor'], a)
        k = appear(t, 'c1e', '十一天后', lead=0.2)
        if k > 0: chip(cv, '11 天后 · 2009 年 11 月 3 日 · 宣布交易', W / 2, 910, 30, a * k, col=GOLD_L)
        money(cv, t, WT('c1e', '每股一百美元'), '$100 / 股', 290, 1030, 72, a, col=CREAM, sub='现金加股票')
        money(cv, t, WT('c1e', '总价约'), '约 $440 亿', 780, 1030, 80, a, sub='连同 $100 亿债务')
        k2 = appear(t, 'c1e', '最大的一笔收购')
        if k2 > 0: cv.text('伯克希尔史上最大的一笔收购', W / 2, 1250, 48, 'serif_black', gold=True, a=a * k2, glow=0.15)
        source(cv, 'BNSF 与伯克希尔联合新闻稿（2009-11-03，SEC 8-K 附件 99.1：每股 $100，约 60% 现金、40% 股票；含 $100 亿 BNSF 债务约 $440 亿）', a, y=1462)
    # c1f：全押美国经济的未来
    t0, t1 = win2('c1f')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['c_bnsf_im', 'g_pass'], a)
        k = appear(t, 'c1f', '美国未来的繁荣')
        tq = WT('c1f', '最重要的是')
        if k > 0: cv.text('美国未来的繁荣，离不开高效、维护良好的铁路系统', W / 2, 940, 32, 'sans_med', col=CREAM, a=a * k)
        qcard(cv, 'qwager', t, tq - 0.3, t1, cy=1150, en=32, cn=44, a=a, typing=1.0, w=940)
        source(cv, '2009-11-03 收购新闻稿（“Our country’s future prosperity depends on its having an efficient and well-maintained rail system.”）', a, y=1462)
    # c1g：卖股票（含穆迪）、增发约 6% 新股、肠镜；“很勉强”
    t0, t1 = S('c1g') - 0.45, CHE('ch1')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['cx_floor'], a)
        tq = WT('c1g', '最后他在信里承认')
        kq = eo((t - tq + 0.2) / 0.4)
        for j, (s_, w_) in enumerate((('卖掉一些股票，其中就有穆迪', '其中就有穆迪'), ('增发约 6% 的新股', '百分之六'), ('“就像讨厌做肠镜前的准备”', '肠镜'))):
            kk = appear(t, 'c1g', w_)
            if kk > 0: cv.text(s_, W / 2, 970 + j * 90, 40, 'serif_black', col=GOLD_L if j == 2 else CREAM, a=a * kk * (1 - kq))
        qcard(cv, 'qclose', t, tq - 0.2, t1, cy=1150, en=36, cn=46, a=a, typing=0.8, w=900)
        source(cv, '伯克希尔 2009 年致股东信（增发占 6.1%；“about as much as we relish prepping for a colonoscopy”；“the final decision was a close one”）', a, y=1462)


# ======================================================================== 第二章：铁路这门生意
def shot_ch2(cv, t):
    # c2a：150 多年：疯狂修建……成熟、理性
    t0, t1 = win2('c2a')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['rr_station', 'rr_loco'], a)
        k = appear(t, 'c2a', '一百五十多年', lead=0.2)
        if k > 0: cv.text('150 多年', W / 2, 920, 56, 'sans_bold', col=GOLD_L, a=a * k)
        words = [('疯狂修建', '疯狂修建'), ('尔虞我诈', '尔虞我诈'), ('过度建设', '过度建设'), ('破产', '破产'), ('重组', '重组'), ('合并', '合并')]
        for j, (s_, w_) in enumerate(words):
            kk = appear(t, 'c2a', w_, d=0.3)
            if kk <= 0: continue
            x = 200 + (j % 3) * 340; y = 1040 + (j // 3) * 90
            chip(cv, s_, x, y, 34, a * kk * 0.85, col=GREY if j < 5 else CREAM)
        k2 = appear(t, 'c2a', '成熟、理性')
        if k2 > 0: cv.text('直到几十年前：成熟、理性', W / 2, 1290, 48, 'serif_black', gold=True, a=a * k2, glow=0.15)
        source(cv, '伯克希尔 2020 年致股东信（“about 150 years … frenzied overbuilding, fraud, bankruptcies, reorganizations and mergers … finally emerged a few decades ago as mature and rationalized”）', a, y=1462)
    # c2b：1995 年合并；3.25 万英里、28 个州
    t0, t1 = win2('c2b')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['c_bnsf_1997', 'g_yard2'], a)
        tm = WT('c2b', '线路超过')
        km = eo((t - tm + 0.3) / 0.5)
        if km < 1:
            k = appear(t, 'c2b', '一九九五年')
            if k > 0: chip(cv, '1995 年', W / 2, 920, 32, a * k * (1 - km), col=GOLD)
            flow_box(cv, 290, 1030, '伯灵顿北方', a * appear(t, 'c2b', '伯灵顿北方') * (1 - km), col=CREAM, w=320)
            flow_box(cv, 790, 1030, '圣太菲', a * appear(t, 'c2b', '圣太菲') * (1 - km), col=CREAM, w=320)
            k2 = appear(t, 'c2b', '合并而来')
            if k2 > 0:
                arrow(cv, (290, 1080), (W / 2 - 40, 1180), a * k2 * (1 - km), col=GOLD, k=k2)
                arrow(cv, (790, 1080), (W / 2 + 40, 1180), a * k2 * (1 - km), col=GOLD, k=k2)
                cv.text('BNSF', W / 2, 1240, 72, 'oswald', col=GOLD_L, a=a * k2 * (1 - km), glow=0.15)
        if km > 0:
            us_map(cv, t, a * km, cy=1130, sc=17.0, bnsf=eexp((t - tm) / 2.0))
            cv.text('线路 32,500+ 英里 · 28 个州', W / 2, 1390, 34, 'sans_bold', col=GOLD_L, a=a * appear(t, 'c2b', '二十八个州'))
            map_note(cv, a * km, y=1425)
        source(cv, 'BNSF 1995 年 10-K（1995-09-22 合并）；伯克希尔 2025 年 10-K（“over 32,500 route miles of track in 28 states”）', a, y=1462)
    # c2c：它拉什么；2025 年约 960 万车
    t0, t1 = win2('c2c')
    a = A(t, t0, t1)
    if a > 0:
        tg = WT('c2c', '粮食'); tcoal = WT('c2c', '还有煤')
        if t < tg + 0.5: vis(cv, t, t0, tg + 0.5, ['c_bnsf_im', 'g_freight'], a)
        if tg <= t < tcoal + 0.5: vis(cv, t, tg, tcoal + 0.5, ['c_bnsf_grain', 'g_yard3'], a)
        if t >= tcoal: vis(cv, t, tcoal, t1, ['c_bnsf_coal2', 'c_bnsf_coal', 'g_yard'], a)
        k = appear(t, 'c2c', '它拉什么')
        if k > 0: cv.text('它拉什么？', W / 2, 920, 48, 'serif_black', col=CREAM, a=a * k)
        t96 = WT('c2c', '九百六十万')
        parts = [('消费品（集装箱、汽车）', 560, GOLD), ('工业品', 138, GOLD_D), ('农产品与能源', 142, C(200, 170, 90)), ('煤', 122, GREY)]
        stack_bar(cv, t, WT('c2c', '进口集装箱') - 0.1, a, 1110, parts, label='2025 年运量（车 / 箱）', total_txt=None, step=0.9)
        kt = appear(t, 'c2c', '九百六十万', lead=0.15)
        if kt > 0: cv.text(counter(0, 962.2, t, t96 - 0.15, 0.9, lambda v: f'约 {v:,.0f} 万车'), W / 2, 1290, 76, 'sans_bold', col=GOLD_L, a=a * kt, glow=0.15)
        source(cv, '伯克希尔 2025 年 10-K（BNSF 运量 962.2 万车 / 箱：消费品 560 万、工业品 138 万、农产品与能源 142 万、煤 122 万）', a, y=1462)
    # c2d：约 15% 的城际吨英里；循环系统、最大的动脉
    t0, t1 = win2('c2d')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['c_bnsf_coal', 'c_bnsf_im2', 'g_diesel'], a)
        ta = WT('c2d', '巴菲特把铁路')
        ka = eo((t - ta + 0.3) / 0.5)
        k = appear(t, 'c2d', '百分之十五', lead=0.15)
        if k > 0 and ka < 1:
            p_ = 0.15 * eexp((t - WT('c2d', '百分之十五') + 0.15) / 0.9)
            cx_, cy_ = 300, 1120
            cv.arc((cx_, cy_), 120, -math.pi / 2, 1.5 * math.pi, DIM, a * k * (1 - ka), th=26)
            cv.arc((cx_, cy_), 120, -math.pi / 2, -math.pi / 2 + 2 * math.pi * max(p_, 0.01), GOLD, a * k * (1 - ka), th=26)
            cv.text('约 15%', cx_, cy_, 52, 'sans_bold', col=GOLD_L, a=a * k * (1 - ka))
            cv.text('美国城际货运（吨英里）', 720, 1070, 32, 'sans_med', col=CREAM, a=a * k * (1 - ka))
            cv.text('比任何一家承运商都多', 720, 1140, 40, 'serif_black', gold=True, a=a * appear(t, 'c2d', '比任何一家') * (1 - ka))
            cv.text('铁路、卡车、管道、驳船、飞机都算在内', 720, 1200, 22, 'sans_light', col=GREY, a=a * k * (1 - ka))
        if ka > 0:
            us_map(cv, t, a * ka, cy=1110, sc=17.0, bnsf=1.0, pulse=True)
            kk = appear(t, 'c2d', '最大的动脉')
            if kk > 0: cv.text('经济的循环系统里，最大的动脉', W / 2, 1385, 38, 'serif_black', gold=True, a=a * kk)
            map_note(cv, a * ka, y=1425)
        source(cv, '伯克希尔 2020 年信（“about 15% of all non-local ton-miles”）；2011 年信（“the circulatory system of our economy. Your railroad is the largest artery”）', a, y=1462)
    # c2e：芒格：讨厌铁路股几十年，迟到总比不到好
    t0, t1 = S('c2e') - 0.45, CHE('ch2')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['c_munger', 'rr_cars'], a, focus=(0.5, 0.3))
        k = appear(t, 'c2e', '买得并不早')
        if k > 0: cv.text('可伯克希尔买得并不早', W / 2, 920, 40, 'serif_black', col=CREAM, a=a * k)
        qcard(cv, 'qmunger', t, WT('c2e', '芒格说') - 0.2, t1, cy=1160, en=28, cn=38, a=a, typing=1.4, w=960)
        source(cv, '伯克希尔 2022 年致股东信（芒格语录，“many lifted from a very recent podcast”）', a, y=1462)


# ======================================================================== 第三章：护城河
def shot_ch3(cv, t):
    # c3a：过两关；第一关：优势是不是真的
    t0, t1 = win2('c3a')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['g_signal'], a)
        two_gates(cv, t, a, [appear(t, 'c3a', '两关'), appear(t, 'c3a', '两关', lead=-0.2)], y=1110, hl=0 if t >= WT('c3a', '第一关') - 0.2 else None)
    # c3b：一加仑柴油一吨货 500 英里；卡车约四倍
    t0, t1 = win2('c3b')
    a = A(t, t0, t1)
    if a > 0:
        tt = WT('c3b', '一加仑')
        if t < tt + 0.5: vis(cv, t, t0, tt + 0.5, ['c_trucks'], a)
        if t >= tt: vis(cv, t, tt, t1, ['c_bnsf_im2', 'c_bnsf_coal', 'g_diesel'], a)
        k = appear(t, 'c3b', '最大的对手是卡车')
        if k > 0: chip(cv, '第一关 · 最大的对手：卡车', W / 2, 910, 30, a * k, col=GOLD)
        k1 = appear(t, 'c3b', '一加仑')
        if k1 > 0:
            cv.text('1 加仑柴油', 220, 1010, 36, 'sans_bold', col=CREAM, a=a * k1)
            arrow(cv, (330, 1010), (420, 1010), a * appear(t, 'c3b', '一吨货'), col=GOLD)
            cv.text('1 吨货', 510, 1010, 36, 'sans_bold', col=CREAM, a=a * appear(t, 'c3b', '一吨货'))
            arrow(cv, (590, 1010), (680, 1010), a * appear(t, 'c3b', '五百英里'), col=GOLD)
            cv.text('500 英里', 810, 1010, 48, 'sans_bold', col=GOLD_L, a=a * appear(t, 'c3b', '五百英里'), glow=0.12)
        tf = WT('c3b', '四倍') - 0.2
        compare_bars(cv, t, a, [('铁路 · 同样的活的油耗', 1, '1', GOLD, WT('c3b', '卡车干同样的活') - 0.2), ('卡车', 4, '约 4 倍', RED_X, tf)],
                     y0=1150, dy=110)
        k3 = appear(t, 'c3b', '长途运重货')
        if k3 > 0: cv.text('长途运重货，铁路成本占优', W / 2, 1390, 36, 'serif_black', gold=True, a=a * k3)
        source(cv, '伯克希尔 2013 年致股东信（“about 500 miles on a single gallon of diesel fuel. Trucks … guzzle about four times as much fuel”）', a, y=1462)
    # c3c：每收 100 美元运费，营业利润约 34.5 美元
    t0, t1 = win2('c3c')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['g_drive', 'g_pass'], a)
        chip(cv, '2025 年 · BNSF', W / 2, 920, 30, a * appear(t, 'c3c', '二零二五年'), col=GOLD)
        k = appear(t, 'c3c', '每收一百美元')
        if k > 0:
            x0, x1, y = 140, 940, 1100
            cv.rrect(x0, y - 50, x1, y + 50, 12, (0.12, 0.12, 0.14), a * k)
            cv.text('每收 $100 运费', x0, y - 82, 32, 'sans_bold', col=CREAM, a=a * k, anchor='l')
            tw = WT('c3c', '三十四点五') - 0.2
            e = eexp((t - tw) / 0.9)
            if e > 0:
                gbar(cv, x0, y - 50, x0 + (x1 - x0) * 0.345 * e, y + 50, GOLD, a, horizontal=True, glow=0.2, sheen_t=t - tw)
                cv.text(counter(0, 34.5, t, tw, 0.9, lambda v: f'${v:.1f}'), x0 + (x1 - x0) * 0.345 * e + 20, y, 52, 'sans_bold', col=GOLD_L, a=a * e, anchor='l')
                cv.text('营业利润', x0 + (x1 - x0) * 0.17, y + 82, 28, 'sans_med', col=GOLD_L, a=a * e)
        source(cv, '伯克希尔 2025 年 10-K（BNSF 营业收入 233.50 亿美元、营业利润 80.55 亿美元，运营比率 65.5%）', a, y=1462)
    # c3d：第二关：重建 5000 亿、几十年；西部主要对手只有联合太平洋
    t0, t1 = win2('c3d')
    a = A(t, t0, t1)
    if a > 0:
        tu = WT('c3d', '而在美国西部')
        if t < tu + 0.5: vis(cv, t, t0, tu + 0.5, ['g_ties'], a)
        if t >= tu: vis(cv, t, tu, t1, ['c_up_train', 'c_up_train2', 'g_tower'], a)
        ku = eo((t - tu + 0.3) / 0.5)
        k = appear(t, 'c3d', '第二关')
        if k > 0: chip(cv, '第二关 · 对手能不能复制', W / 2, 910, 30, a * k, col=GOLD)
        if ku < 1:
            money(cv, t, WT('c3d', '五千亿'), '$5000 亿+', W / 2, 1060, 110, a * (1 - ku), sub='重建它的资产（巴菲特估计）')
            k2 = appear(t, 'c3d', '几十年')
            if k2 > 0: cv.text('再加几十年', W / 2, 1250, 48, 'serif_black', col=CREAM, a=a * k2 * (1 - ku))
        if ku > 0:
            us_map(cv, t, a * ku, cx=W / 2 + 260, cy=1150, sc=22.0, bnsf=1.0, up=eexp((t - WT('c3d', '联合太平洋')) / 1.5))
            cv.rrect(80, 960, 380, 1060, 10, (0.06, 0.06, 0.08), a * ku * 0.85)
            cv.line((100, 990), (150, 990), GOLD, a * ku, 5); cv.text('BNSF', 165, 990, 26, 'sans_bold', col=GOLD_L, a=a * ku, anchor='l')
            ku2 = appear(t, 'c3d', '联合太平洋')
            cv.line((100, 1035), (150, 1035), SILVER, a * ku2, 4); cv.text('联合太平洋', 165, 1035, 26, 'sans_bold', col=CREAM, a=a * ku2, anchor='l')
            k3 = appear(t, 'c3d', '主要只有一家')
            if k3 > 0: cv.text('西部的铁路对手，主要只有一家', W / 2, 1390, 36, 'serif_black', gold=True, a=a * k3)
            map_note(cv, a * ku, y=1425)
        source(cv, '伯克希尔 2023 年信（重建估计）；伯克希尔 2025 年 10-K（“BNSF’s primary rail competitor in the Western region of the United States is the Union Pacific”）', a, y=1462)
    # c3e：两关都过了；回报为什么只是一般？
    t0, t1 = S('c3e') - 0.45, CHE('ch3')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['c_bnsf_bridge2', 'c_bnsf_bridge', 'g_loco'], a)
        tq = WT('c3e', '可问题来了')
        kq = eo((t - tq + 0.2) / 0.4)
        dn = appear(t, 'c3e', '两关都过了', d=0.35)
        two_gates(cv, t, a * (1 - 0.7 * kq), [1, 1], y=1060, done=(dn, eo((t - WT('c3e', '两关都过了') - 0.25) / 0.35)))
        k = appear(t, 'c3e', '又宽又真')
        if k > 0 and kq < 1: cv.text('护城河：又宽又真', W / 2, 1250, 48, 'serif_black', gold=True, a=a * k * (1 - kq))
        big_q(cv, t, '回报为什么只是一般？', 1270, WT('c3e', '回报为什么'), 64, a)


# ======================================================================== 第四章：吃资本的生意
def shot_ch4(cv, t):
    # c4a：铁路“吃资本”
    t0, t1 = win2('c4a')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['g_shop'], a)
        chip(cv, '2023 年致股东信', W / 2, 910, 30, a * appear(t, 'c4a', '二零二三年'), col=GOLD)
        qcard(cv, 'qeat', t, WT('c4a', '和大多数') - 0.3, t1, cy=1130, en=36, cn=48, a=a, typing=0.9, w=920)
    # c4b：超过折旧才能维持；14 年累计 220 亿、每年 15 亿多；哎哟
    t0, t1 = win2('c4b')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['g_ties', 'g_rails'], a)
        k = appear(t, 'c4b', '要超过折旧')
        if k > 0:
            cv.text('维持现有生意 ＝ 每年花的钱 ＞ 折旧', W / 2, 930, 36, 'sans_bold', col=CREAM, a=a * k)
        # 14 根小柱：每年超出折旧的部分（示意：按平均值），累计 220 亿
        tb = WT('c4b', '收购后十四年')
        for j in range(14):
            e = eexp((t - tb - j * 0.12) / 0.4)
            if e <= 0: continue
            x = 160 + j * 54
            gbar(cv, x, 1270 - 110 * e, x + 36, 1270, GOLD_D, a, glow=0.05)
            if j % 3 == 0 or j == 13: cv.text(str(2010 + j), x + 18, 1296, 18, 'sans_light', col=GREY, a=a * e)
        kk = appear(t, 'c4b', '两百二十亿', lead=0.15)
        if kk > 0:
            cv.text(counter(0, 220, t, WT('c4b', '两百二十亿') - 0.15, 0.9, lambda v: f'累计 ${v:.0f} 亿+'), 900, 1010, 48, 'sans_bold', col=GOLD_L, a=a * kk, anchor='r', glow=0.12)
            cv.text('超出折旧的部分（2010–2023）', 900, 1062, 22, 'sans_light', col=GREY, a=a * kk, anchor='r')
        k2 = appear(t, 'c4b', '十五亿多')
        if k2 > 0: cv.text('平均每年 $15 亿多', 900, 1110, 30, 'sans_bold', col=CREAM, a=a * k2, anchor='r')
        to = WT('c4b', '哎哟')
        ko = eo((t - to + 0.1) / 0.35)
        if ko > 0: cv.text('“Ouch!” 哎哟', W / 2, 1380, 64, 'serif_black', col=RED_X, a=a * ko, scale=1.25 - 0.25 * ko, glow=0.15)
        source(cv, '伯克希尔 2023 年致股东信（“outlays in excess of GAAP depreciation … $22 billion or more than $1½ billion annually. Ouch!”）；柱高为平均值示意', a, y=1462)
    # c4c：分红明显少于账面利润，除非一直加债
    t0, t1 = win2('c4c')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['g_yard3', 'g_yard2'], a)
        k = appear(t, 'c4c', '交给伯克希尔的分红')
        if k > 0:
            flow_box(cv, W / 2, 960, '账面利润', a * k, col=CREAM, w=320)
            arrow(cv, (W / 2 - 60, 1005), (300, 1090), a * k, col=GOLD_D, k=k)
            arrow(cv, (W / 2 + 60, 1005), (780, 1090), a * appear(t, 'c4c', '明显少于'), col=GOLD, k=appear(t, 'c4c', '明显少于'))
            flow_box(cv, 300, 1140, '再投回铁路', a * k, col=GOLD_D, w=320, sub='超出折旧的资本开支')
            flow_box(cv, 780, 1140, '分红', a * appear(t, 'c4c', '明显少于'), col=GOLD, w=240, sub='常常明显少于利润')
        k2 = appear(t, 'c4c', '除非一直加债')
        if k2 > 0:
            cv.text('除非一直加债', W / 2 - 40, 1290, 42, 'serif_black', col=CREAM, a=a * k2)
            cross(cv, W / 2 + 140, 1290, 22, a * appear(t, 'c4c', '不打算'), th=7)
            cv.text('伯克希尔不打算这么做', W / 2, 1360, 28, 'sans_med', col=RED_X, a=a * appear(t, 'c4c', '不打算'))
        source(cv, '伯克希尔 2023 年致股东信（“BNSF dividends paid to Berkshire … will regularly fall considerably short of BNSF’s reported earnings unless we regularly increase the railroad’s debt. And that we do not intend to do.”）', a, y=1462)
    # c4d：工资谈判、危险品、暴雪洪水
    t0, t1 = win2('c4d')
    a = A(t, t0, t1)
    if a > 0:
        tw = WT('c4d', '危险品')
        if t < tw + 0.5: vis(cv, t, t0, tw + 0.5, ['g_signal', 'g_tower'], a)
        if t >= tw: vis(cv, t, tw, t1, ['c_tankcars', 'c_bnsf_winter', 'g_smoke'], a)
        k0 = appear(t, 'c4d', '别的烦恼')
        if k0 > 0: cv.text('铁路还有别的烦恼', W / 2, 920, 42, 'serif_black', col=CREAM, a=a * k0)
        rows = [('工资谈判', '可能一路打到总统和国会', '工资谈判'), ('公共承运人', '危险品也必须拉', '危险品'), ('极端天气', '暴雪、洪水来了也得照常跑', '暴雪')]
        for j, (h_, s_, w_) in enumerate(rows):
            kk = appear(t, 'c4d', w_)
            if kk <= 0: continue
            y = 1030 + j * 120
            cv.rrect(110, y - 46, 970, y + 46, 12, (0.07, 0.06, 0.06), a * kk * 0.9)
            cv.rrect(110, y - 46, 970, y + 46, 12, RED_X, a * kk * 0.6, fill=False, th=2)
            cv.text(h_, 150, y, 34, 'sans_bold', col=GOLD_L, a=a * kk, anchor='l')
            cv.text(s_, 400, y, 32, 'sans_med', col=CREAM, a=a * kk, anchor='l')
        source(cv, '伯克希尔 2023 年致股东信（工资谈判可能交给总统和国会；作为公共承运人须运输危险品；极端天气）', a, y=1462)
    # c4e：2014 年服务出问题；2015 年砸 58 亿，约折旧三倍
    t0, t1 = win2('c4e')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['g_wheel', 'g_loco'], a)
        k = appear(t, 'c4e', '二零一四年', lead=0.2)
        if k > 0:
            cv.text('2014', 260, 970, 72, 'oswald', col=RED_X, a=a * k)
            cv.text('服务出了问题', 260, 1045, 30, 'sans_bold', col=CREAM, a=a * appear(t, 'c4e', '服务出了问题'))
            cv.text('很多客户失望', 260, 1090, 26, 'sans_light', col=GREY, a=a * appear(t, 'c4e', '失望'))
        k2 = appear(t, 'c4e', '第二年', lead=0.2)
        if k2 > 0:
            cv.text('2015', 760, 970, 72, 'oswald', col=GOLD_L, a=a * k2)
            money(cv, t, WT('c4e', '五十八亿'), '约 $58 亿', 760, 1060, 56, a, sub='线路与设备')
        compare_bars(cv, t, a, [('折旧', 1, '1 份', GREY, WT('c4e', '差不多是') - 0.2), ('2015 年资本开支', 3, '约 3 倍', GOLD, WT('c4e', '三倍') - 0.2)],
                     y0=1240, dy=100)
        source(cv, '伯克希尔 2014 年信（“BNSF disappointed many of its customers”）；2015 年信（资本开支约 58 亿美元，“almost three times its annual depreciation charge”）', a, y=1462)
    # c4f：回顾日本商社：生意分三等；BNSF 属于第二等，像电力公司
    t0, t1 = S('c4f') - 0.45, CHE('ch4')
    a = A(t, t0, t1)
    if a > 0:
        recap(cv, t, t0, t1, 's1_japan', '日本商社', a=a)
        tiers = [('最好的', '赚了钱不用再投（如喜诗）', '最好的'), ('第二等', '要不断投钱才能多赚（如电力公司）', '第二等'), ('最差的', '越投越亏', '分三等')]
        for j, (h_, s_, w_) in enumerate(tiers):
            kk = appear(t, 'c4f', w_) if j < 2 else appear(t, 'c4f', '第二等', lead=-0.6)
            if kk <= 0: continue
            y = 950 + j * 110; x = 110 + j * 50
            on = j == 1 and t >= WT('c4f', '就属于第二等') - 0.2
            cv.rrect(x, y - 44, x + 640, y + 44, 10, (0.07, 0.07, 0.09), a * kk * 0.9)
            cv.rrect(x, y - 44, x + 640, y + 44, 10, GOLD if on else GREY, a * kk * (0.95 if on else 0.4), fill=False, th=3 if on else 2, glow=0.12 if on else 0)
            cv.text(h_, x + 30, y, 32, 'sans_bold', col=GOLD_L if on or j == 0 else GREY, a=a * kk, anchor='l')
            cv.text(s_, x + 190, y, 26, 'sans_med', col=CREAM, a=a * kk, anchor='l')
            if on: chip(cv, '← BNSF', x + 750, y, 30, a * eo((t - WT('c4f', '就属于第二等') + 0.2) / 0.4), col=GOLD_L)
        k = appear(t, 'c4f', '二零零九年就写过')
        if k > 0: cv.text('2009 年信：BNSF 的经济特性很像电力公司', W / 2, 1320, 34, 'serif_black', gold=True, a=a * k)
        source(cv, '回顾 · 本系列《东京下注》（伯克希尔 2007 年信 “The Great, the Good and the Gruesome”）；伯克希尔 2009 年信（BNSF 与电力公司经济特性相似）', a, y=1462)


# ======================================================================== 第五章：账怎么算
def shot_ch5(cv, t):
    # c5a：按买价：可以接受；按重建价值：少得可怜
    t0, t1 = win2('c5a')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['c_buffett_2010', 'c_obama_buffett'], a, focus=(0.5, 0.35))
        big_q(cv, t, '伯克希尔到底赚没赚钱？', 930, WT('c5a', '那伯克希尔'), 46, a, col=CREAM)
        for j, (h_, v_, w_, col) in enumerate((('按买价算', '可以接受', '按买价算', GOLD_L), ('按重建价值算', '少得可怜', '按重建价值算', RED_X))):
            kk = appear(t, 'c5a', w_)
            if kk <= 0: continue
            x = 300 + j * 480
            cv.rrect(x - 210, 1030, x + 210, 1230, 16, (0.06, 0.06, 0.08), a * kk * 0.9)
            cv.rrect(x - 210, 1030, x + 210, 1230, 16, col, a * kk * 0.8, fill=False, th=2)
            cv.text(h_, x, 1080, 30, 'sans_med', col=CREAM, a=a * kk)
            cv.text(v_, x, 1165, 56, 'serif_black', col=col, a=a * appear(t, 'c5a', v_))
        source(cv, '伯克希尔 2023 年信（“an acceptable return on its purchase price … and also a pittance on the replacement value of the property”）', a, y=1462)
    # c5b：用重建成本的零头买下
    t0, t1 = win2('c5b')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['g_ballast', 'g_ties'], a)
        compare_bars(cv, t, a, [('重建估计', 5000, '$5000 亿+', GREY, S('c5b')), ('2010 年全部股权作价', 345, '$345 亿', GOLD, WT('c5b', '零头') - 0.3)], y0=1000, dy=150)
        k = appear(t, 'c5b', '零头')
        if k > 0: cv.text('重建成本的零头', W / 2, 1310, 56, 'serif_black', gold=True, a=a * k, glow=0.15)
        source(cv, '伯克希尔 2023 年信（“why we could buy BNSF in 2010 at a small fraction of its replacement value”）', a, y=1462)
    # c5c：2025：净利润 55 亿、经营现金流 81 亿、分红 44 亿
    t0, t1 = win2('c5c')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['g_diesel', 'g_pass'], a)
        chip(cv, '2025 年 · BNSF', W / 2, 910, 30, a * appear(t, 'c5c', '二零二五年'), col=GOLD)
        vbars(cv, t, [('净利润', 54.76, WT('c5c', '五十五亿') - 0.2, GOLD * 0.7, None), ('经营现金流', 81, WT('c5c', '八十一亿') - 0.2, GOLD * 0.85, None),
                      ('分红给伯克希尔', 44, WT('c5c', '四十四亿') - 0.2, GOLD, None)], a, base=1330, hmax=300, fmt=lambda v: f'${v:,.0f}亿')
        source(cv, '伯克希尔 2025 年 10-K（BNSF 净利润 54.76 亿美元）；2025 年致股东信（经营现金流 81 亿、分红 44 亿美元）', a, y=1462)
    # c5d：累计分红 418 亿 + 41×5 ≈ 620 亿，超过 345 亿
    t0, t1 = win2('c5d')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['c_bnsf_grain', 'c_bnsf_im', 'g_smoke'], a)
        x0, x1, y = 120, 960, 1120
        def X(v): return x0 + (x1 - x0) * v / 650.0
        k1 = appear(t, 'c5d', '四百一十八亿', lead=0.2)
        if k1 > 0:
            e = eexp((t - WT('c5d', '四百一十八亿') + 0.2) / 0.9)
            gbar(cv, x0, y - 40, X(418 * e), y + 40, GOLD_D, a, horizontal=True, glow=0.1)
            cv.text('$418 亿', (x0 + X(418)) / 2, y, 34, 'sans_bold', col=INK, a=a * e)
            cv.text('截至 2020 年底累计分红', (x0 + X(418)) / 2, y + 66, 22, 'sans_light', col=GREY, a=a * e)
        tp = WT('c5d', '之后五年')
        for j in range(5):
            e = eexp((t - tp - j * 0.25) / 0.4)
            if e <= 0: continue
            xa = X(418 + 41 * j); xb = X(418 + 41 * (j + 1))
            gbar(cv, xa + 2, y - 40, xa + 2 + (xb - xa - 4) * e, y + 40, GOLD, a, horizontal=True, glow=0.1)
            cv.text(str(2021 + j), (xa + xb) / 2, y - 62, 18, 'sans_light', col=GREY, a=a * e)
        k2 = appear(t, 'c5d', '四十一亿')
        if k2 > 0: cv.text('+ 每年约 $41 亿 × 5', X(520), y + 66, 22, 'sans_light', col=GOLD_L, a=a * k2)
        kl = appear(t, 'c5d', '三百四十五亿')
        xl = X(345)
        if kl > 0:
            cv.line((xl, y - 110), (xl, y + 110), CREAM, a * kl, 3)
            cv.text('2010 年股权作价 $345 亿', xl, y - 135, 26, 'sans_bold', col=CREAM, a=a * kl)
        t620 = WT('c5d', '六百二十亿')
        k3 = eo((t - t620 + 0.15) / 0.45)
        if k3 > 0:
            cv.text(counter(345, 620, t, t620 - 0.15, 0.9, lambda v: f'累计约 ${v:.0f} 亿'), W / 2, 1290, 76, 'sans_bold', gold=True, a=a * k3, glow=0.2, scale=1.1 - 0.1 * k3)
            cv.text('本片推算：418 亿 + 41 亿 × 5（2021–2025 年平均）', W / 2, 1370, 22, 'sans_light', col=GREY, a=a * k3)
        source(cv, '伯克希尔 2020 年信（累计分红 418 亿美元）；2025 年信（过去五年平均每年分红 41 亿美元）；累计约 620 亿为本片推算', a, y=1462)
    # c5e：引出原声（2026 年专访）
    t0, t1 = S('c5e') - 0.45, E('c5e') + 0.6
    a = A(t, t0, t1, 0.4, 0.3)
    if a > 0:
        vis(cv, t, t0, t1, ['c_buffett_ku', 'c_buffett_2010'], a, focus=(0.5, 0.35))
        k = appear(t, 'c5e', '二零二六年', lead=0.2)
        if k > 0: chip(cv, '2026 年 7 月 · CNBC 专访', W / 2, 1040, 34, a * k, col=GOLD_L)
    # c5f：买在恐慌里；恐惧的气氛，是投资者最好的朋友
    t0, t1 = S('c5f') - 0.45, CHE('ch5')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['c_lehman', 'cx_floor'], a)
        tq = WT('c5f', '巴菲特在二零零九年')
        kq = eo((t - tq + 0.2) / 0.4)
        k = appear(t, 'c5f', '买在恐慌里')
        if k > 0 and kq < 1:
            cv.text('买在恐慌里', W / 2, 1040, 84, 'serif_black', gold=True, a=a * k * (1 - kq), glow=0.2)
            cv.text('是这笔交易最大的底气', W / 2, 1150, 44, 'serif_black', col=CREAM, a=a * appear(t, 'c5f', '最大的底气') * (1 - kq))
        qcard(cv, 'qfear', t, tq - 0.2, t1, cy=1130, en=40, cn=50, a=a, typing=0.8, w=900)
        source(cv, '伯克希尔 2009 年致股东信（“A climate of fear is their best friend.”）', a, y=1462)


# ======================================================================== 第六章：掉队与变局
def shot_ch6(cv, t):
    # c6a：运货、资本开支都最多，利润率却落后于其余五家
    t0, t1 = win2('c6a')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['c_bnsf_locos', 'c_bnsf_im2', 'g_yard2'], a)
        tq = WT('c6a', '利润率却')
        kq = eo((t - tq + 0.3) / 0.4)
        k = appear(t, 'c6a', '最宽的护城河')
        if k > 0 and kq < 1: cv.text('最宽的护城河 ≠ 跑在最前面', W / 2, 930, 42, 'serif_black', col=CREAM, a=a * k * (1 - kq))
        for j, (s_, w_) in enumerate((('运的货最多', '运的货'), ('资本开支最多', '花的资本开支'))):
            kk = appear(t, 'c6a', w_)
            if kk <= 0 or kq >= 1: continue
            x = 300 + j * 480
            chip(cv, s_, x, 1060, 38, a * kk * (1 - kq), col=GOLD_L)
            cv.text('北美六大铁路里', x, 1130, 24, 'sans_light', col=GREY, a=a * kk * (1 - kq))
        qcard(cv, 'qslip', t, tq - 0.2, t1, cy=1150, en=32, cn=44, a=a, typing=0.9, w=940)
        source(cv, '伯克希尔 2023 年信（“carries more freight and spends more on capital expenditures than any of the five other major North American railroads, its profit margins have slipped relative to all five since our purchase”）', a, y=1462)
    # c6b：BNSF 34.5% vs 联合太平洋约 40%
    t0, t1 = win2('c6b')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['c_up_train2', 'c_up_train', 'g_tower'], a)
        chip(cv, '2025 年 · 营业利润率', W / 2, 910, 30, a * appear(t, 'c6b', '二零二五年'), col=GOLD)
        compare_bars(cv, t, a, [('BNSF', 34.5, '34.5%', GOLD, WT('c6b', '百分之三十四点五') - 0.2),
                                ('联合太平洋', 40.2, '约 40%', SILVER, WT('c6b', '利润率约') - 0.2)], y0=1060, dy=140, vmax=45)
        k = appear(t, 'c6b', '运营比率')
        if k > 0: cv.text('联合太平洋运营比率 59.8% → 利润率 ≈ 100% − 59.8%', W / 2, 1360, 24, 'sans_light', col=GREY, a=a * k)
        source(cv, '伯克希尔 2025 年信 / 10-K（BNSF 营业利润率 34.5%）；联合太平洋 2025 年四季度业绩（运营比率 59.8%）', a, y=1462)
    # c6c：每 1 个百分点 ≈ 2.3 亿；追平差约 13 亿（本片推算）
    t0, t1 = win2('c6c')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['c_abel', 'ny_ticker'], a, focus=(0.5, 0.35))
        k = appear(t, 'c6c', '每提高')
        if k > 0:
            cv.text('利润率 +1 个百分点', 300, 1000, 36, 'sans_bold', col=CREAM, a=a * k)
            arrow(cv, (300, 1040), (300, 1100), a * appear(t, 'c6c', '二点三亿'), col=GOLD)
            money(cv, t, WT('c6c', '二点三亿'), '≈ $2.3 亿 / 年', 300, 1150, 52, a, sub='经营现金流')
        k2 = appear(t, 'c6c', '追平联合太平洋')
        if k2 > 0:
            cv.text('差距约 5.7 个百分点', 780, 1000, 36, 'sans_bold', col=CREAM, a=a * k2)
            cv.text('× $2.3 亿', 780, 1060, 32, 'sans_med', col=GREY, a=a * k2)
        k3 = appear(t, 'c6c', '十三亿', lead=0.15)
        if k3 > 0:
            cv.text(counter(0, 13, t, WT('c6c', '十三亿') - 0.15, 0.8, lambda v: f'≈ ${v:.0f} 亿 / 年'), 780, 1160, 60, 'sans_bold', col=RED_X, a=a * k3, glow=0.15)
            cv.text('本片推算', 780, 1230, 22, 'sans_light', col=GREY, a=a * k3)
        source(cv, '伯克希尔 2025 年信（阿贝尔：营业利润率每提高 1 个百分点约多 2.3 亿美元经营现金流）；差约 13 亿为本片推算', a, y=1462)
    # c6d：联合太平洋拟合并诺福克南方；截至 2026 年 11 月未批准
    t0, t1 = win2('c6d')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['c_ns_train', 'c_up_train', 'g_switch'], a)
        k0 = appear(t, 'c6d', '变局也来了')
        if k0 > 0: chip(cv, '变局', W / 2, 910, 32, a * k0, col=RED_X)
        km = appear(t, 'c6d', '联合太平洋提议')
        us_map(cv, t, a * km, cy=1140, sc=17.0, bnsf=0.0, up=eexp((t - WT('c6d', '联合太平洋提议')) / 1.2),
               ns=eexp((t - WT('c6d', '诺福克南方')) / 1.2))
        if km > 0:
            cv.line((120, 980), (170, 980), SILVER, a * km, 4); cv.text('联合太平洋', 185, 980, 24, 'sans_bold', col=CREAM, a=a * km, anchor='l')
            kn = appear(t, 'c6d', '诺福克南方')
            cv.line((120, 1020), (170, 1020), NS_C, a * kn, 4); cv.text('诺福克南方', 185, 1020, 24, 'sans_bold', col=CREAM, a=a * kn, anchor='l')
            kc = appear(t, 'c6d', '横贯东西海岸')
            if kc > 0: cv.text('横贯东西海岸', W / 2, 1335, 36, 'serif_black', col=CREAM, a=a * kc)
            map_note(cv, a * km, y=1425)
        k2 = appear(t, 'c6d', '监管机构还没有批准')
        if k2 > 0: chip(cv, '截至 2026 年 11 月：监管机构尚未批准', W / 2, 1390, 28, a * k2, col=GOLD_L)
        source(cv, '美国地面运输委员会（STB）公告 26-02、26-09、26-13；联合太平洋 2026 年三季度 10-Q（预计 2027 年下半年完成）', a, y=1462)
    # c6e：伯克希尔：不收购另一家一级铁路；确保客户进入东部市场
    t0, t1 = S('c6e') - 0.45, CHE('ch6')
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['c_bnsf_coal2', 'c_bnsf_locos', 'g_yard'], a)
        k = appear(t, 'c6e', '伯克希尔表态')
        if k > 0: cv.text('伯克希尔的表态', W / 2, 920, 42, 'serif_black', col=CREAM, a=a * k)
        rows = [('不收购另一家一级铁路', '眼下的价钱对股东不划算', '不打算收购', False), ('BNSF 的客户', '仍要能公平地进入东部市场', '确保客户', True)]
        for j, (h_, s_, w_, ok) in enumerate(rows):
            kk = appear(t, 'c6e', w_)
            if kk <= 0: continue
            y = 1060 + j * 150
            cv.rrect(110, y - 56, 970, y + 56, 14, (0.07, 0.07, 0.09), a * kk * 0.9)
            cv.rrect(110, y - 56, 970, y + 56, 14, GOLD if ok else RED_X, a * kk * 0.7, fill=False, th=2)
            if ok: tick(cv, 170, y, 22, a * kk)
            else: cross(cv, 170, y, 20, a * kk, th=6)
            cv.text(h_, 230, y - 16, 34, 'sans_bold', col=CREAM, a=a * kk, anchor='l')
            cv.text(s_, 230, y + 26, 24, 'sans_light', col=GREY, a=a * kk, anchor='l')
        source(cv, '伯克希尔 2025 年信（“the current economics would not work in our shareholders’ favor”；确保客户有完整、有竞争的东部市场通道）', a, y=1462)


# ======================================================================== 第七章：带走什么
LESSONS = [('护城河宽，不等于回报高', '要不断砸钱维持的生意，赚来的钱很大一部分得再投回去'),
           ('好资产也要好价钱', '买在恐慌里，买在重建成本的零头上'),
           ('护城河只挡对手，不替你干活', '利润率掉了队，得靠经营一点点追回来')]


def shot_ch7(cv, t):
    t0, t1 = S('c7a') - 0.45, S('c7e') + 0.1
    a = A(t, t0, t1)
    if a > 0:
        cur = 2 if t >= S('c7d') - 0.2 else 1 if t >= S('c7c') - 0.2 else 0 if t >= S('c7b') - 0.2 else -1
        nm = {-1: ['c_bnsf_bridge', 'g_diesel'], 0: ['g_ties', 'g_shop'], 1: ['c_lehman', 'cx_quote'], 2: ['c_bnsf_locos', 'g_loco']}[cur]
        ta = {-1: t0, 0: S('c7b') - 0.45, 1: S('c7c') - 0.45, 2: S('c7d') - 0.45}[cur]
        tb = {-1: S('c7b') + 0.1, 0: S('c7c') + 0.1, 1: S('c7d') + 0.1, 2: t1}[cur]
        vis(cv, t, ta, tb, nm, a)
        k = appear(t, 'c7a', '三件事')
        if k > 0: cv.text('从 BNSF 身上，带走三件事', W / 2, 890, 40, 'serif_black', gold=True, a=a * k)
        item_list(cv, t, a, LESSONS, [appear(t, 'c7b', '第一'), appear(t, 'c7c', '第二'), appear(t, 'c7d', '第三')], cur, y0=1000, dy=130)
        source(cv, {0: '伯克希尔 2023 年信（本片总结）', 1: '伯克希尔 2009、2023 年信（本片总结）', 2: '伯克希尔 2023、2025 年信（本片总结）'}.get(cur, '本片总结'), a, y=1462)
    # c7e：一百年后；全押美国，押的就是这一百年
    t0, t1 = S('c7e') - 0.45, S('p1') + 0.1
    a = A(t, t0, t1)
    if a > 0:
        vis(cv, t, t0, t1, ['c_bnsf_winter', 'c_bnsf_im2', 'g_pass'], a)
        tf = WT('c7e', '全押美国')
        kf = eo((t - tf + 0.2) / 0.4)
        qcard(cv, 'qcentury', t, t0 + 0.2, tf - 0.1, cy=1100, en=32, cn=44, a=a, typing=1.0, w=920)
        if kf > 0:
            cv.text('全押美国，', W / 2, 1060, 70, 'serif_black', col=CREAM, a=a * kf)
            cv.text('押的就是这一百年', W / 2, 1180, 84, 'serif_black', gold=True, a=a * appear(t, 'c7e', '这一百年'), glow=0.25)
        source(cv, '伯克希尔 2021 年致股东信', a * (1 - kf), y=1462)
    # p1：铁路买下全部、十几年；一家芯片厂不到一年清仓
    t0, t1 = win2('p1')
    a = A(t, t0, t1)
    if a > 0:
        tc = WT('p1', '有一家芯片厂')
        if t < tc + 0.5: vis(cv, t, t0, tc + 0.5, ['g_loco', 'rr_loco'], a)
        if t >= tc: vis(cv, t, tc, t1, ['ny_ticker', 'cx_quote'], a)
        k = appear(t, 'p1', '重资产')
        if k > 0: cv.text('同样是重资产、宽护城河', W / 2, 910, 38, 'serif_black', col=CREAM, a=a * k)
        k1 = appear(t, 'p1', '铁路他买下全部')
        if k1 > 0:
            cv.text('铁路', 290, 1030, 60, 'serif_black', gold=True, a=a * k1)
            cv.text('买下全部', 290, 1110, 32, 'sans_bold', col=CREAM, a=a * k1)
            cv.text('一拿就是十几年', 290, 1160, 28, 'sans_med', col=GOLD_L, a=a * appear(t, 'p1', '十几年'))
        k2 = appear(t, 'p1', '有一家芯片厂')
        if k2 > 0:
            cv.text('一家芯片厂', 790, 1030, 56, 'serif_black', col=CREAM, a=a * k2)
            cv.text('买入后不到一年', 790, 1110, 32, 'sans_bold', col=CREAM, a=a * appear(t, 'p1', '不到一年'))
            cv.text('就清仓了', 790, 1160, 32, 'sans_bold', col=RED_X, a=a * appear(t, 'p1', '清仓'))
        source(cv, '伯克希尔 13F 与 2023 年报道（2022 年三季度买入约 41 亿美元台积电 ADR，2023 年一季度清仓）', a, y=1462)
    # p2：下期预告：台积电
    t0, t1 = S('p2') - 0.45, CH['end'][0] + 0.4
    a = A(t, t0, t1, 0.4, 0.2)
    if a > 0:
        vis(cv, t, t0, t1, ['ny_floor'], a)
        k = appear(t, 'p2', '下一期', lead=0.2)
        if k > 0:
            chip(cv, '下期', W / 2, 890, 34, a * k, col=GOLD_L)
            cv.text('台积电', W / 2, 1010, 120, 'serif_black', gold=True, a=a * appear(t, 'p2', '台积电', lead=0.2), glow=0.25)
            cv.text('TSMC', W / 2, 1110, 34, 'corm_med', col=GOLD, a=a * appear(t, 'p2', '台积电'), track=0.4)
        k2 = appear(t, 'p2', '护城河这么宽')
        if k2 > 0: cv.text('护城河这么宽，伯克希尔为什么这么快就离场？', W / 2, 1230, 34, 'serif_black', col=CREAM, a=a * k2)
        k4 = eo((t - E('p2') - 0.2) / 0.5)              # 落版字：片尾接住它，化作粒子汇成 logo（common.shot_end）
        if k4 > 0: cv.text(END_L, W / 2, END_Y, END_SZ, 'serif_black', gold=True, a=a * k4, glow=0.15)
        source(cv, '第二季片单（docs/第二季规划.md）', a * 0.7 * (1 - k4), y=1462)
