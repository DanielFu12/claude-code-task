"""第八期《一张支票，换一句话——巴菲特与内布拉斯加家具城》全部镜头（开场、片名、第一至七章）。

版式（沿用前几期）：上方画窗（cy≈520，1000×480）放真实影像或文件影像；下方 y 880–1420 放动画解读；y≈1462 出处；y≈1555 字幕。
素材：
  · 文件影像：伯克希尔 2013 年年报第 114–117 页（1983-08-30 收购提议书、NFM 1946 年报表原件）doc_*；
  · 美国国会图书馆：FSA 1938 年奥马哈 loc_*（John Vachon）、1939–1940 年二手家具店（Russell Lee、John Vachon）、
    普罗库金-戈尔斯基的俄罗斯帝国村庄 loc_ru*、1944 年奥马哈海滩 loc_jaws / loc_dday、Carol M. Highsmith 的城市照片；
  · archive.org：2015 年 NFM 得州店（The Colony 市政府）tx_* / op_*、约 1960 年地毯宣传片 cp_*、1958 年《American Look》al_*、
    1921 年教育片（搬演）eu_*、1999 年 Levitz 广告 lv_*；
  · 其余为致股东信、年报数据的图表与示意动画（示意处标注“示意”）。自绘图形不画任何公司的商标。
时间全部挂在旁白句子与词锚点上（WT 用朗读文本）。
"""
from gg_base import *          # noqa
from gg_base import _SAY, _landmask        # noqa

WOOD = C(150, 104, 62)
WCY, WH = 540, 560          # v2：上方画窗加大到 1000×560（y 260–820，在章节导航之下；v1 为 1000×480）
RED_X = C(225, 70, 60)


def A(t, t0, t1, fi=0.4, fo=0.4): return env(t, t0, t1, fi, fo)


def CHE(cid):
    """本章画面结束时刻：下一章（章节卡）开始后 0.2 秒；第七章为片尾开始后 0.4 秒"""
    k = int(cid[2])
    return CH['ch%d' % (k + 1)][0] + 0.2 if k < 7 else CH['end'][0] + 0.4


def win2(i, j=None, pre=0.45, post=-0.1):
    """从 i 句开口前 pre 秒，到 j（或 i）句之后的下一句开口后 0.1 秒。
    v3：前后两个镜头各有 0.4 秒淡入淡出、互相重叠 0.55 秒，叠化过去，不在句与句之间掉黑"""
    j = j or i
    nx = nxt(j)
    end = (S(nx) - post) if nx else E(j) + 0.6
    if nx and SEG[nx]['ch'] != SEG[j]['ch']:
        end = CHE(SEG[j]['ch'])
    return S(i) - pre, end


def appear(t, i, sub, d=0.45, lead=0.1):
    """词锚点 sub 开口前 lead 秒开始，用 d 秒缓入"""
    return eo((t - WT(i, sub) + lead) / d)


# ======================================================================== 通用构件（第八期）
def docview(cv, name, t, t0, t1, keys, hls=(), cy=WCY, w=1000, h=WH, cap=None, a=1.0, fi=0.5, fo=0.5):
    """文件影像：纸张放进画窗，按关键帧推拉 keys = [(时刻, 中心 x, 中心 y, 可见宽度占页宽比例)]（0..1 归一化坐标）；
    hls = [(x0, y0, x1, y1, 出现时刻)]：荧光笔从左到右划过 + 金色下划线"""
    al = env(t, t0, t1, fi, fo) * a
    if al <= 0.004 or not M.have(name): return 0.0
    cy = WCY if cy is None else cy; h = WH if h is None else h
    src = M.img(name); ih, iw = src.shape[:2]
    ks = sorted(keys)
    if t <= ks[0][0]: k = ks[0][1:]
    elif t >= ks[-1][0]: k = ks[-1][1:]
    else:
        for (ta, *pa), (tb, *pb) in zip(ks, ks[1:]):
            if ta <= t <= tb:
                u = eio5((t - ta) / max(tb - ta, 1e-3)); k = [lerp(x, y, u) for x, y in zip(pa, pb)]; break
    fx, fy, vw = k
    s = w / (vw * iw)
    ox, oy = fx * iw * s - w / 2, fy * ih * s - h / 2
    M_ = np.array([[s, 0, -ox], [0, s, -oy]], np.float32)
    fr = cv2.warpAffine(src, M_, (int(w), int(h)), flags=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR, borderValue=(0.93, 0.92, 0.9))
    fr = fr * np.array([0.97, 0.93, 0.84], np.float32)             # 暖色纸张
    M.backdrop_register(fr, al * 0.55)
    # 荧光笔
    for (x0, y0, x1, y1, th) in hls:
        e = eo((t - th) / 0.6)
        if e <= 0: continue
        X0, Y0 = x0 * iw * s - ox, y0 * ih * s - oy; X1, Y1 = x1 * iw * s - ox, y1 * ih * s - oy
        xe = X0 + (X1 - X0) * e
        xa, xb, ya, yb = int(max(X0, 0)), int(min(xe, w)), int(max(Y0, 0)), int(min(Y1, h))
        if xb > xa and yb > ya:
            fr[ya:yb, xa:xb] = fr[ya:yb, xa:xb] * (1 - 0.42) + np.array([1.0, 0.82, 0.30], np.float32) * 0.42
            fr[min(yb, int(h) - 1):min(yb + 3, int(h)), xa:xb] = np.array([0.80, 0.52, 0.12], np.float32)
    x0, y0 = W / 2 - w / 2, cy - h / 2
    sh = np.zeros((int(h) + 80, int(w) + 80), np.float32); sh[40:-40, 40:-40] = 1
    cv.img_mul(1 - cv2.GaussianBlur(sh, (0, 0), 18) * 0.6 * al, x0 - 40, y0 - 28)
    cv.over(np.clip(fr, 0, 1), np.full((int(h), int(w)), al, np.float32), x0, y0)
    cv.rrect(x0 - 1, y0 - 1, x0 + w + 1, y0 + h + 1, 2, GOLD_D, al * 0.5, fill=False, th=2)
    txt = (cap + ' · ' if cap else '') + M.credit_text(name)
    cv.text(txt, W / 2, y0 + h + 30, 19, 'sans_light', col=(0.62, 0.60, 0.58), a=al * 0.9)
    return al


# ---- 点阵美国地图（Natural Earth 陆地遮罩，公有领域）；预渲染缓存
CITY = {'奥马哈': (41.26, -95.94), '得梅因': (41.59, -93.62), '堪萨斯城': (39.12, -94.82), '达拉斯': (33.09, -96.89),
        '奥斯汀': (30.51, -97.82), '盐湖城': (40.76, -111.89), '休斯敦': (29.76, -95.37), '波士顿': (42.36, -71.06)}
_maps = {}


def map_xy(lat, lon, cx, cy, sc, lat0=38.5, lon0=-96.0):
    return cx + (lon - lon0) * sc * math.cos(math.radians(lat0)), cy - (lat - lat0) * sc


def usmap(cv, cx, cy, sc, a, lat0=38.5, lon0=-96.0, box=None):
    if a <= 0.004: return
    key = (round(cx), round(cy), round(sc, 2), lat0, lon0)
    if key not in _maps:
        m = _landmask(); lay = np.zeros((H, W), np.float32)
        step = 0.55 if sc > 30 else 0.75
        for lat in np.arange(24.5, 49.6, step):
            for lon in np.arange(-125.0, -66.5, step):
                if m[int((90 - lat) * 2), int((lon + 180) * 2) % 720] > 127:
                    x, y = map_xy(lat, lon, cx, cy, sc, lat0, lon0)
                    if 0 <= x < W and 0 <= y < H: cv2.circle(lay, (int(x * 4), int(y * 4)), int(2.4 * 4), 1.0, -1, cv2.LINE_AA, 2)
        _maps[key] = lay
    lay = _maps[key]
    if box:
        x0, y0, x1, y1 = box; sub = np.zeros_like(lay); sub[y0:y1, x0:x1] = lay[y0:y1, x0:x1]; lay = sub
    cv.over(np.ones((H, W, 3), np.float32) * C(150, 138, 120), lay * a * 0.85, 0, 0)


def city(cv, nm, cx, cy, sc, a, k=1.0, col=GOLD_L, sub=None, dx=18, anchor='l', hollow=False, size=30, lat0=38.5, lon0=-96.0):
    if a * k <= 0.004: return
    x, y = map_xy(*CITY[nm], cx, cy, sc, lat0, lon0)
    if hollow: cv.circle((x, y), 10, col, a * k, 3)
    else: cv.glow_dot((x, y), 9 + 5 * k, col, a * k)
    cv.text(nm, x + (dx if anchor == 'l' else -dx), y - (12 if sub else 0), size, 'sans_bold', col=col, a=a * k, anchor=anchor, shadow=0.8)
    if sub: cv.text(sub, x + (dx if anchor == 'l' else -dx), y + 22, 22, 'sans_light', col=CREAM, a=a * k, anchor=anchor, shadow=0.8)


def link(cv, p, q, a, k, col=GOLD, dashed=False, th=3):
    if a * k <= 0.004: return
    x, y = p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k
    if dashed:
        n = int(math.hypot(x - p[0], y - p[1]) / 18)
        for j in range(n):
            if j % 2 == 0:
                u0, u1 = j / max(n, 1), (j + 1) / max(n, 1)
                cv.line((p[0] + (x - p[0]) * u0, p[1] + (y - p[1]) * u0), (p[0] + (x - p[0]) * u1, p[1] + (y - p[1]) * u1), col, a, th)
    else: cv.line(p, (x, y), col, a, th)


def check_art(cv, cx, cy, s, a, amount='$55,000,000', rot=-0.04):
    """示意：一张空白支票（只有金额，不画任何真实名称、签名或银行标识）"""
    if a <= 0.004: return
    w, h = 720 * s, 300 * s
    cr, sr = math.cos(rot), math.sin(rot)
    def R(x, y): return (cx + x * cr - y * sr, cy + x * sr + y * cr)
    P = [R(-w / 2, -h / 2), R(w / 2, -h / 2), R(w / 2, h / 2), R(-w / 2, h / 2)]
    cv.fillpoly(P, C(232, 226, 205), a)
    cv.poly(P + [P[0]], GOLD_D, a, 3)
    for yy in (-40, 30, 95):
        cv.line(R(-w / 2 + 50 * s, yy * s), R(w / 2 - 260 * s if yy == -40 else w / 2 - 50 * s, yy * s), C(150, 140, 120), a, 2)
    q = R(w / 2 - 150 * s, -40 * s)
    cv.rrect(q[0] - 120 * s, q[1] - 34 * s, q[0] + 120 * s, q[1] + 26 * s, 6, C(250, 246, 230), a)
    cv.text(amount, q[0], q[1] - 6 * s, int(40 * s), 'mono', col=INKD, a=a)
    p = R(-w / 2 + 60 * s, -h / 2 + 40 * s); cv.text('PAY TO THE ORDER OF', p[0], p[1], int(20 * s), 'corm', col=C(110, 100, 80), a=a, anchor='l')
    p = R(w / 2 - 40 * s, h / 2 - 30 * s); cv.text('支票（示意）', p[0], p[1], int(20 * s), 'sans_light', col=C(110, 100, 80), a=a, anchor='r')


def store_box(cv, cx, cy, s, a, sign, col=GOLD, sub=None, glow=0.0):
    """示意：一栋大卖场（方盒子 + 招牌 + 门），不画真实店面"""
    if a <= 0.004: return
    w, h = 300 * s, 180 * s
    x0, y0 = cx - w / 2, cy - h / 2
    cv.rect(x0, y0, x0 + w, y0 + h, (0.12, 0.11, 0.10), a)
    cv.rrect(x0, y0, x0 + w, y0 + h, 4, col, a * 0.8, fill=False, th=2, glow=glow)
    cv.rect(x0 + 20 * s, y0 + 18 * s, x0 + w - 20 * s, y0 + 64 * s, col * 0.35, a)
    cv.text(sign, cx, y0 + 41 * s, int(28 * s), 'sans_bold', col=GOLD_L if col is GOLD else CREAM, a=a)
    for j in range(4):
        xx = x0 + 30 * s + j * 64 * s
        cv.rect(xx, y0 + 88 * s, xx + 44 * s, y0 + 130 * s, C(60, 72, 84), a)
    cv.rect(cx - 26 * s, y0 + 120 * s, cx + 26 * s, y0 + h, CHOC, a)
    if sub: cv.text(sub, cx, y0 + h + 34 * s, int(26 * s), 'sans_med', col=CREAM, a=a)


def cross(cv, x, y, r, a, col=RED_X, th=6):
    if a <= 0.004: return
    cv.line((x - r, y - r), (x + r, y + r), col, a, th); cv.line((x - r, y + r), (x + r, y - r), col, a, th)


def check_list(cv, t, items, x, y0, dy, a, size=40):
    """“没有……”清单：每项出现后打一个红叉"""
    for j, (txt, tw) in enumerate(items):
        k = eo((t - tw + 0.1) / 0.4)
        if k <= 0: continue
        y = y0 + j * dy
        cv.text(txt, x, y, size, 'sans_bold', col=CREAM, a=a * k, anchor='l')
        cross(cv, x - 44, y, 16, a * eo((t - tw - 0.25) / 0.3))


def pct_bars(cv, t, rows, a, x0=330, x1=920, y0=960, dy=130, vmax=50.0, size=48, lab=32):
    """横向百分比柱：rows = [(标签, 数值 或 None, 显示文字, 出现时刻, 颜色)]"""
    for j, (lb, v, txt, ts, col) in enumerate(rows):
        e = eexp((t - ts) / 1.0)
        if e <= 0: continue
        y = y0 + j * dy
        cv.text(lb, x0 - 26, y, lab, 'sans_bold', col=CREAM, a=a * min(1, e * 2), anchor='r')
        L = (x1 - x0) * (v or 0) / vmax * e
        gbar(cv, x0, y - 30, x0 + max(L, 2), y + 30, col, a, horizontal=True, glow=0.12, sheen_t=t - ts)
        cv.text(txt, x0 + L + 20, y, size, 'sans_bold', col=GOLD_L if col is GOLD else CREAM, a=a * min(1, e * 2), anchor='l', shadow=0.6)


NFM_PRETAX = [(1984, 1451), (1985, 1269), (1986, 1769), (1987, 1684), (1988, 1844), (1989, 1707), (1990, 1725)]   # 万美元，全公司税前（各年致股东信利润表）


def right_terms_chart(cv, t, a):
    """“好价钱”：七年税前利润逐年柱 + 累计线，对照作价（$6000 万）与两倍作价"""
    x0, x1, yb, ytop = 150, 960, 780, 330
    vmax = 12000.0
    def Y(v): return yb - (yb - ytop) * v / vmax
    ka = eo((t - S('c2i') + 0.45) / 0.6)
    if ka <= 0: return
    cv.rrect(60, 262, 1020, 822, 14, (0.05, 0.045, 0.04), a * ka * 0.85)
    cv.rrect(60, 262, 1020, 822, 14, GOLD_D, a * ka * 0.5, fill=False, th=2)
    cv.line((x0, yb), (x1, yb), GREY, a * ka, 2)
    cv.text('NFM 税前利润（万美元，全公司）', 90, 292, 22, 'sans_med', col=GREY, a=a * ka, anchor='l')
    # 作价线与两倍线
    kp = appear(t, 'c2j', '作价')
    for v, lb, k_, col in ((6000, '作价 ≈ $6000 万', kp, CREAM), (12000, '作价 × 2', appear(t, 'c2m', '两倍'), GOLD_L)):
        if k_ <= 0: continue
        y = Y(v); L = (x1 - x0) * eo(k_)
        for xx in range(int(x0), int(x0 + L), 22): cv.line((xx, y), (min(xx + 12, x0 + L), y), col, a * k_ * 0.8, 2)
        cv.text(lb, x0 + 10, y - 22, 24, 'sans_bold', col=col, a=a * k_, anchor='l')
    bw = (x1 - x0) / 7
    cum = 0.0; pts = []
    t84 = WT('c2i', '一九八四'); tseven = WT('c2m', '买下之后')
    for j, (yr, v) in enumerate(NFM_PRETAX):
        tj = t84 if j == 0 else tseven + 0.15 * j
        e = eexp((t - tj) / 0.7)
        if e <= 0: continue
        cx = x0 + bw * (j + 0.5)
        gbar(cv, cx - bw * 0.3, Y(v * e), cx + bw * 0.3, yb, GOLD if j == 0 else GOLD * 0.75, a, glow=0.1, reflect=False)
        cv.text(str(yr), cx, yb + 24, 22, 'oswald', col=CREAM, a=a * min(1, e * 2))
        if j == 0 or appear(t, 'c2m', '加起来') > 0:
            cv.text(f'{v:,}', cx, Y(v * e) - 18, 20, 'sans_med', col=GOLD_L, a=a * min(1, e * 2))
        cum += v * e; pts.append((cx, Y(cum)))
    kc = appear(t, 'c2m', '加起来')
    if kc > 0 and len(pts) > 1:
        n = 1 + (len(pts) - 1) * eo(kc)
        for j in range(int(n) - 1 if n >= 2 else 0):
            cv.line(pts[j], pts[j + 1], GOLD_L, a * kc, 4)
        cv.glow_dot(pts[min(int(n) - 1, len(pts) - 1)], 10, GOLD_L, a * kc)
        if kc > 0.6: cv.text('累计约 $1.14 亿', pts[-1][0] - 24, pts[-1][1] + 34, 26, 'sans_bold', col=GOLD_L, a=a * kc, anchor='r')


# ======================================================================== 开场
def shot_hook(cv, t):
    a0 = env(t, 0, S('h1') + 0.6, 0.0, 0.5)
    if a0 > 0:
        L = 420 * eo(t / 1.1); hb = math.exp(-max(t - 0.25, 0) * 6) * (t >= 0.25)
        cv.line((W / 2 - L, 960), (W / 2 + L, 960), GOLD, a0 * (0.5 + 0.5 * hb), 2)
        cv.glow_dot((W / 2, 960), 30 + 40 * hb, GOLD, a0 * 0.6)
    # h1：1983-08-30，生日那天，一页多纸的提议书，九成、5535 万
    t0, t1 = S('h1') - 0.4, S('h2') + 0.1
    a = A(t, t0, t1, 0.5, 0.3)
    if a > 0:
        tb = WT('h1', '一页多纸')
        photo_win(cv, 'buffett_2015', t, t0, tb + 0.4, cy=WCY, h=WH, a=a, cap='沃伦·巴菲特（2015 年）')
        tm = WT('h1', '五千五百')
        docview(cv, 'doc_proposal1', t, tb - 0.1, t1 + 0.6, [(tb, 0.5, 0.30, 0.95), (tm - 0.8, 0.40, 0.272, 0.58), (tm + 1.2, 0.47, 0.272, 0.42)],
                hls=[(0.142, 0.262, 0.19, 0.283, WT('h1', '九成') - 0.2), (0.44, 0.260, 0.565, 0.284, tm - 0.1)],
                a=a, cap='1983-08-30 收购提议书第 1 页：买下 90%，现金 $55,350,000')
        k = appear(t, 'h1', '一九八三年'); kf = 1 - appear(t, 'h1', '五千五百', d=0.35, lead=0.5)
        if k > 0:
            cv.text('1983 · 8 · 30', W / 2, 960, 104, 'oswald', col=GOLD_L, a=a * k * kf, glow=0.15)
            chip(cv, '巴菲特 53 岁生日', W / 2, 1080, 34, a * appear(t, 'h1', '五十三岁') * kf, col=GOLD)
            chip(cv, '一页多纸的收购提议书', W / 2, 1170, 34, a * appear(t, 'h1', '一页多纸') * kf, col=CREAM)
        money(cv, t, tm, '$5535 万', W / 2, 1010, 120, a, sub='买下 90% 股份 · 全部现金')
        source(cv, '伯克希尔 2013 年信（“August 30, 1983 – my birthday … a 1 1⁄4-page purchase proposal”）；提议书原件（2013 年年报第 114 页）', a, y=1462)
    # h2：没有审计、没有盘点、没有查产权
    t0, t1 = S('h2') - 0.4, S('h3') + 0.1
    a = A(t, t0, t1, 0.25, 0.3)
    if a > 0:
        docview(cv, 'doc_proposal2', t, t0 - 0.3, t1 + 0.3, [(t0, 0.5, 0.45, 0.95), (t1, 0.45, 0.55, 0.75)], a=a, cap='提议书签字页（1983-08-30）', fi=0.2)
        for j, (txt, tw) in enumerate((('没有审计', '没有审计'), ('没有盘点库存', '没有盘点'), ('没有查产权', '也没有查'))):
            k = eo((t - WT('h2', tw) + 0.12) / 0.3)
            if k <= 0: continue
            y = 960 + j * 120
            cv.text(txt, W / 2 + 40, y, 64, 'serif_black', col=CREAM, a=a * k, scale=1.15 - 0.15 * k)
            cross(cv, W / 2 - text_size(txt, 'serif_black', 64)[0] / 2 - 20, y, 28, a * eo((t - WT('h2', tw) - 0.15) / 0.25), th=8)
        source(cv, '伯克希尔 1984 年信（“NFM had never had an audit … we did not take an inventory … we did not check property titles”）', a, y=1462)
    # h3：卖家——89 岁、没上过一天学的俄国移民
    t0, t1 = S('h3') - 0.4, S('h4') + 0.1
    a = A(t, t0, t1, 0.3, 0.35)
    if a > 0:
        photo_win(cv, 'loc_ru1', t, t0, t1, cy=WCY, h=WH, a=a, cap='俄罗斯帝国的村庄（1909）——她出生的那片土地', z0=1.0, z1=1.12)
        k = appear(t, 'h3', '八十九岁', lead=0.15)
        if k > 0:
            cv.text('89', W / 2 - 50, 1010, 190, 'oswald', col=GOLD_L, a=a * k, glow=0.2, scale=1.2 - 0.2 * k)
            cv.text('岁', W / 2 + 110, 1050, 60, 'serif_black', col=CREAM, a=a * k)
        chip(cv, '没上过一天学', W / 2 - 190, 1220, 36, a * appear(t, 'h3', '没上过'), col=RED_X)
        chip(cv, '俄国移民', W / 2 + 190, 1220, 36, a * appear(t, 'h3', '俄国移民'), col=CREAM)
        source(cv, '伯克希尔 2013 年信（“Mrs. B was 89 at the time”）；1983 年信（“no formal education”）', a, y=1462)
    # h4：六年后，她辞职出走，在隔壁开店抢生意
    t0, t1 = S('h4') - 0.4, S('h5') + 0.1
    a = A(t, t0, t1, 0.25, 0.3)
    if a > 0:
        seq(cv, t, t0, t1, ['tx_promo1', 'tx_promo2', 'op_crowd'], cy=WCY, h=WH, a=a, cap='今天的 NFM：得州店（2015）')
        k = appear(t, 'h4', '六年后', lead=0.15)
        if k > 0: cv.text('1989', W / 2, 935, 96, 'oswald', col=RED_X, a=a * k, glow=0.1, scale=1.25 - 0.25 * k)
        store_box(cv, 300, 1130, 0.85, a * appear(t, 'h4', '辞职出走'), 'NFM', col=GOLD, sub='她亲手创办的家具城')
        k2 = appear(t, 'h4', '在隔壁')
        if k2 > 0:
            store_box(cv, 780, 1130 + 30 * (1 - k2), 0.85, a * k2, "MRS. B'S", col=RED_X, sub='她的新店', glow=0.25)
            cv.text('隔壁', W / 2, 1050, 32, 'sans_bold', col=CREAM, a=a * k2)
            arrow(cv, (470, 1090), (610, 1090), a * k2, RED_X, k=k2)
        k3 = appear(t, 'h4', '抢生意')
        if k3 > 0: cv.text('抢生意', W / 2, 1330, 64, 'serif_black', col=RED_X, a=a * k3, glow=0.15, scale=1.2 - 0.2 * k3)
        cv.text('示意', 990, 1250, 20, 'sans_light', col=GREY, a=a * appear(t, 'h4', '在隔壁'))
        source(cv, '伯克希尔 1989 年信（“she has started a new business”）；1992 年信（“opened up her own operation next door”）', a, y=1462)
    # h5：看走了眼，还是看得太准？
    t0, t1 = S('h5') - 0.4, S('h6') + 0.1
    a = A(t, t0, t1, 0.3, 0.35)
    if a > 0:
        photo_win(cv, first_have(['c_buffett_ku', 'buffett_2010']), t, t0, t1, cy=WCY, h=WH, a=a, cap='沃伦·巴菲特（2005 年）', focus=(0.5, 0.35))
        big_q(cv, t, '看走了眼？', 1000, WT('h5', '看走了眼'), 86, a, col=CREAM)
        big_q(cv, t, '还是看得太准？', 1150, WT('h5', '还是'), 86, a)
    # h6：四十多年后的专访（引出原声）
    t0, t1 = S('h6') - 0.3, S('h6') + SEG['h6']['dur'] + 0.9
    a = A(t, t0, t1, 0.4, 0.3)
    if a > 0:
        seq(cv, t, t0, t1, ['cnbc_two1'], cy=WCY, h=WH, a=a, cap='CNBC 专访现场（2026-07-15）', focus=(0.72, 0.5))
        k = appear(t, 'h6', '四十多年后')
        if k > 0:
            cv.text('1983', 300, 960, 84, 'oswald', col=GREY, a=a * k)
            arrow(cv, (420, 960), (640, 960), a * k, GOLD, k=appear(t, 'h6', '九十五岁', d=0.6))
            cv.text('2026', 780, 960, 84, 'oswald', col=GOLD_L, a=a * appear(t, 'h6', '九十五岁'), glow=0.15)
        k2 = appear(t, 'h6', '专访')
        if k2 > 0: chip(cv, 'CNBC 专访 · 2026 年 7 月 15 日', W / 2, 1100, 32, a * k2, col=GOLD)
        k3 = appear(t, 'h6', '说出了答案')
        if k3 > 0: cv.text('95 岁的巴菲特，讲起买公司', W / 2, 1230, 46, 'serif_black', col=CREAM, a=a * k3)
        source(cv, 'CNBC Squawk Box：Becky Quick 专访巴菲特（2026-07-15）', a, y=1462)
    # h7：好生意，好价钱，对的人——全片主线；故事要从这位老太太说起
    t0, t1 = S('h7') - 0.4, CH['title'][0] + 0.1
    a = A(t, t0, t1, 0.4, 0.25)
    if a > 0:
        seq(cv, t, t0, t1, ['ad01_lamps', 'ad01_tv', 'ad01_rugs', 'ad01_card'], cy=WCY, h=WH, a=a, cap='NFM 奥马哈店（2001 年电视广告画面）')
        three_pillars(cv, t, a, [WT('h7', '好生意'), WT('h7', '好价钱'), WT('h7', '对的人')], y=1060)
        k = appear(t, 'h7', '全占了')
        if k > 0: cv.text('内布拉斯加家具城，三样全占了', W / 2, 1310, 44, 'serif_black', gold=True, a=a * k, glow=0.12)
        source(cv, 'CNBC 2026-07-15 专访原话（“buy a good business … on the right terms … the right person to run it”）；本片概括', a, y=1462)


def supermoney(cv, t):
    """第二章开头：1972 年《超级金钱》里的一幕（原在开场）"""
    t0, t1 = S('c2s') - 0.45, S('c2a') + 0.1
    a = A(t, t0, t1, 0.6, 0.4)
    if a <= 0: return
    photo_win(cv, 'loc_omaha_a', t, t0, t1, cy=WCY, h=WH, a=a, cap='奥马哈（1938 年）', z0=1.02, z1=1.10)
    k = eo((t - t0 - 0.3) / 0.6)
    bx, by = 230, 1100
    cv.rrect(bx - 110, by - 150, bx + 110, by + 150, 8, C(70, 40, 30), a * k)
    cv.rrect(bx - 110, by - 150, bx + 110, by + 150, 8, GOLD_D, a * k * 0.8, fill=False, th=2)
    cv.text('SUPERMONEY', bx, by - 60, 30, 'playfair', col=GOLD_L, a=a * k, track=0.08)
    cv.text('《超级金钱》', bx, by, 30, 'serif_semi', col=CREAM, a=a * k)
    cv.text('1972', bx, by + 70, 34, 'oswald', col=GOLD, a=a * k)
    cv.text('书（示意）', bx, by + 182, 20, 'sans_light', col=GREY, a=a * k)
    lines = [('c2s', '这是门好生意', '“That’s a really good business.”', 960),
             ('c2t', '那你怎么不买', '', 1065), ('c2t', '它是私人公司', '“It’s privately held.”', 1155),
             ('c2t', '说不定哪天', '“I might buy it anyway … Someday.”', 1265)]
    for i, sub, en, y in lines:
        kk = appear(t, i, sub)
        if kk <= 0: continue
        who = '作者' if sub == '那你怎么不买' else '巴菲特'
        txt = {'这是门好生意': '“这是门好生意。”', '那你怎么不买': '“那你怎么不买？”', '它是私人公司': '“它是私人公司。”',
               '说不定哪天': '“说不定哪天，我还是会买。”'}[sub]
        cv.text(who, 410, y - 16, 26, 'sans_light', col=GOLD if who == '巴菲特' else GREY, a=a * kk, anchor='l')
        cv.text(txt, 490, y - 16, 40 if len(txt) < 12 else 34, 'serif_semi', col=CREAM if who != '巴菲特' else GOLD_L, a=a * kk, anchor='l')
        if en: cv.text(en, 490, y + 30, 22, 'corm', col=GREY, a=a * kk, anchor='l')
    source(cv, 'Adam Smith《Supermoney》（1972），伯克希尔 2013 年致股东信卷首引用', a, y=1462)


PILLARS = [('好生意', 'A GOOD BUSINESS'), ('好价钱', 'THE RIGHT TERMS'), ('对的人', 'THE RIGHT PERSON')]


def three_pillars(cv, t, a, tws, y=1060, checks=None, size=58):
    """全片主线：三块金边牌子依次落下；checks：每块打勾的时刻（片尾回扣用）"""
    for j, ((cn, en), tw) in enumerate(zip(PILLARS, tws)):
        k = eo((t - tw + 0.15) / 0.45)
        if k <= 0: continue
        x = W / 2 + (j - 1) * 330
        yy = y + 30 * (1 - k)
        cv.rrect(x - 150, yy - 95, x + 150, yy + 95, 16, (0.07, 0.06, 0.05), a * k * 0.92)
        cv.rrect(x - 150, yy - 95, x + 150, yy + 95, 16, GOLD, a * k * 0.85, fill=False, th=2, glow=0.15 * k)
        cv.text(cn, x, yy - 18, size, 'serif_black', gold=True, a=a * k, glow=0.12)
        cv.text(en, x, yy + 52, 19, 'corm', col=GOLD, a=a * k * 0.9, track=0.12)
        if checks:
            kc = eo((t - checks[j]) / 0.35)
            if kc > 0:
                cx_, cy_ = x + 120, yy - 80
                cv.glow_dot((cx_, cy_), 26, GOLD, a * kc * 0.5)
                cv.circle((cx_, cy_), 24, GOLD_L, a * kc, 3)
                cv.line((cx_ - 11, cy_), (cx_ - 3, cy_ + 9), GOLD_L, a * kc, 4); cv.line((cx_ - 3, cy_ + 9), (cx_ + 13, cy_ - 9), GOLD_L, a * kc, 4)


def shot_title(cv, t):
    t0, t1 = CH['title'][0], CH['ch1'][0] + 0.6
    a = env(t, t0, t1, 0.02, 0.6)
    if a <= 0: return
    p = t - t0
    flash = math.exp(-p * 5.0)
    check_art(cv, W / 2, 640, 1.05, a * eo(p / 0.35), rot=-0.05 + 0.02 * eo(p / 1.5))
    R = 60 + p * 900
    cv.circle((W / 2, 640), R, GOLD, a * math.exp(-p * 2.2) * 0.8, 3)
    cv.glow_dot((W / 2, 640), 220, GOLD, a * flash * 0.9)
    k = eo((p - 0.15) / 0.6)
    cv.text('一张支票，', W / 2, 1000, 108, 'serif_black', col=CREAM, a=a * k, scale=1.08 - 0.08 * k, shadow=0.8)
    cv.text('换一句话', W / 2, 1135, 120, 'serif_black', gold=True, a=a * eo((p - 0.35) / 0.6), glow=0.3)
    cv.text('巴菲特与内布拉斯加家具城', W / 2, 1270, 52, 'serif_semi', col=CREAM, a=a * eo((p - 0.7) / 0.6))
    cv.text('A CHECK FOR HER WORD', W / 2, 1360, 26, 'corm', col=GOLD, a=a * eo((p - 1.0) / 0.6), track=0.35)


# ======================================================================== 第一章：五百美元起家
def shot_ch1(cv, t):
    # c1a：俄国 → 美国
    t0, t1 = win2('c1a')
    a = A(t, t0, t1)
    if a > 0:
        tm = WT('c1a', '去了美国')
        photo_win(cv, 'loc_ru1', t, t0, tm + 0.3, cy=WCY, h=WH, a=a, cap='俄罗斯帝国的村庄（1909）')
        seq(cv, t, tm - 0.2, t1, ['eu_ship'], cy=WCY, h=WH, a=a, cap='移民船（1921 年教育片，搬演）')
        k = appear(t, 'c1a', '罗丝')
        if k > 0:
            cv.text('罗丝·布鲁姆金', W / 2, 960, 64, 'serif_black', gold=True, a=a * k, glow=0.12)
            cv.text('ROSE BLUMKIN', W / 2 - 70, 1040, 30, 'corm', col=GOLD, a=a * k, track=0.12)
            cv.text('· B 太太', W / 2 + 110, 1040, 28, 'sans_med', col=GOLD, a=a * k)
        k2 = appear(t, 'c1a', '二十三岁')
        if k2 > 0: chip(cv, '23 岁 · 说服边境守卫放行', W / 2, 1150, 34, a * k2, col=CREAM)
        k3 = appear(t, 'c1a', '从俄国')
        if k3 > 0:
            node(cv, 300, 1290, '俄国', a * k3, col=CREAM, size=36, w=220)
            arrow(cv, (430, 1290), (650, 1290), a * k3, GOLD, k=appear(t, 'c1a', '去了美国', d=0.6))
            node(cv, 780, 1290, '美国', a * appear(t, 'c1a', '去了美国'), col=GOLD, size=36, w=220)
        source(cv, '伯克希尔 1983 年信（“then 23, talked her way past a border guard to leave Russia for America”）', a, y=1462)
    # c1b：没上过学；女儿教英语
    t0, t1 = win2('c1b')
    a = A(t, t0, t1)
    if a > 0:
        photo_win(cv, 'loc_ru2', t, t0, t1, cy=WCY, h=WH, a=a, cap='俄罗斯帝国的村庄（1909）')
        for j, (s_, tw) in enumerate((('没上过一天学', '没上过'), ('不会说英语', '英语'))):
            chip(cv, s_, 330 + j * 420, 950, 38, a * appear(t, 'c1b', tw), col=RED_X)
        k = appear(t, 'c1b', '大女儿')
        if k > 0:
            person(cv, 400, 1230, 2.2, a * k, CREAM)
            person(cv, 560, 1250, 1.5, a * k, GOLD_L)
            for j, ch_ in enumerate('ABC'):
                kk = eo((t - WT('c1b', '一个词') - j * 0.25) / 0.35)
                if kk > 0:
                    cv.rrect(660 + j * 90, 1150, 740 + j * 90, 1230, 8, GOLD * 0.35, a * kk)
                    cv.text(ch_, 700 + j * 90, 1190, 50, 'playfair', col=GOLD_L, a=a * kk)
            cv.text('大女儿每天放学回家教她', W / 2, 1340, 30, 'sans_med', col=CREAM, a=a * k)
        source(cv, '伯克希尔 1983 年信（“no formal education … knew no English … her older daughter taught her, every evening”）', a, y=1462)
    # c1c：卖旧衣服 → 1937 年，500 美元
    t0, t1 = win2('c1c')
    a = A(t, t0, t1)
    if a > 0:
        t37 = WT('c1c', '一九三七')
        photo_win(cv, 'loc_omaha1915', t, t0, t37 + 0.3, cy=WCY, h=WH, a=a, cap='奥马哈的商店街（1915 年前后）')
        photo_win(cv, 'loc_loans', t, t37 - 0.1, t1, cy=WCY, h=WH, a=a, cap='奥马哈道格拉斯街的当铺与旧货店（1938）')
        k = appear(t, 'c1c', '卖旧衣服')
        if k > 0: chip(cv, '靠卖旧衣服过日子', W / 2, 920, 34, a * k * (1 - appear(t, 'c1c', '一九三七')), col=CREAM)
        k2 = appear(t, 'c1c', '一九三七')
        if k2 > 0:
            cv.text('1937', 300, 1040, 90, 'oswald', col=GOLD_L, a=a * k2, glow=0.1)
            money(cv, t, WT('c1c', '五百美元'), '$500', 760, 1040, 100, a, sub='攒下的全部本钱')
        k3 = appear(t, 'c1c', '内布拉斯加')
        if k3 > 0:
            cv.text('Nebraska Furniture Mart', W / 2, 1230, 46, 'playfair', col=GOLD_L, a=a * k3)
            cv.text('内布拉斯加家具城 · NFM', W / 2, 1310, 36, 'serif_semi', col=CREAM, a=a * k3)
        source(cv, '伯克希尔 1983 年信（“In 1937, after many years of selling used clothing, Mrs. Blumkin had saved $500”）；2020 年信', a, y=1462)
    # c1d：没有优势，只有便宜
    t0, t1 = win2('c1d')
    a = A(t, t0, t1)
    if a > 0:
        tb = WT('c1d', '对手')
        photo_win(cv, 'loc_sa_furn', t, t0, tb + 0.3, cy=WCY, h=WH, a=a, cap='一家旧家具店（得州圣安东尼奥，1939，仅示意年代）')
        photo_win(cv, 'loc_brandeis', t, tb - 0.1, t1, cy=WCY, h=WH, a=a, cap='奥马哈最大的布兰代斯百货（1938）')
        for j, (s_, tw) in enumerate((('没有好地段', '没有好地段'), ('没有独家的货', '独家'))):
            k = appear(t, 'c1d', tw)
            if k > 0:
                cv.text(s_, 300, 940 + j * 70, 36, 'sans_bold', col=CREAM, a=a * k)
                cross(cv, 120, 940 + j * 70, 14, a * k)
        k = appear(t, 'c1d', '对手')
        if k > 0:
            node(cv, 790, 975, '对手：老店', a * k, col=GREY, size=34, w=360, sub='有钱 · 扎根多年')
        k2 = appear(t, 'c1d', '卖得便宜')
        if k2 > 0:
            cv.text('卖得便宜', W / 2, 1220, 110, 'serif_black', gold=True, a=a * k2, glow=0.3, scale=1.1 - 0.1 * k2)
        source(cv, '伯克希尔 1983 年信（“no locational or product advantage goes up against rich, long-entrenched competition”）', a, y=1462)
    # c1e：卖掉自家的家具还债
    t0, t1 = win2('c1e')
    a = A(t, t0, t1)
    if a > 0:
        photo_win(cv, 'loc_chanute', t, t0, t1, cy=WCY, h=WH, a=a, cap='开在自家门口的旧家具店（堪萨斯州，1940，仅示意年代）')
        k = appear(t, 'c1e', '自己家里')
        if k > 0:
            hx, hy = 330, 1110
            cv.fillpoly([(hx - 120, hy - 20), (hx, hy - 120), (hx + 120, hy - 20)], GOLD * 0.5, a * k)
            cv.rect(hx - 100, hy - 20, hx + 100, hy + 110, (0.14, 0.12, 0.10), a * k)
            cv.rrect(hx - 100, hy - 20, hx + 100, hy + 110, 4, GOLD_D, a * k, fill=False, th=2)
            cv.text('自家的家具、电器', hx, hy + 170, 28, 'sans_med', col=CREAM, a=a * k)
        k2 = appear(t, 'c1e', '按约定')
        if k2 > 0:
            arrow(cv, (480, 1110), (640, 1110), a * k2, GOLD, k=k2)
            cv.text('$', 760, 1100, 110, 'sans_bold', gold=True, a=a * k2, glow=0.2)
            cv.text('按约定，一分不少还清', 760, 1280, 32, 'sans_bold', col=GOLD_L, a=a * k2)
        source(cv, '伯克希尔 1983 年信（“she simply sold the furniture and appliances from her home in order to pay creditors precisely as promised”）', a, y=1462)
    # c1f：同行施压，厂商断货
    t0, t1 = win2('c1f')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['cp_room', 'cp_sweep', 'al_chair'], cy=WCY, h=WH, a=a, cap='地毯与家具（约 1960 年宣传片 / 1958 年影片）')
        y = 1050
        k1 = appear(t, 'c1f', '同行'); k2 = appear(t, 'c1f', '厂商'); k3 = appear(t, 'c1f', '不给她')
        node(cv, 190, y, '奥马哈同行', a * k1, col=GREY, size=30, w=250)
        arrow(cv, (320, y), (420, y), a * k1, GREY, k=k2)
        node(cv, 560, y, '家具、地毯厂商', a * k2, col=CREAM, size=30, w=270)
        node(cv, 920, y, 'B 太太', a * k3, col=GOLD, size=32, w=200)
        if k3 > 0:
            cv.line((700, y), (810, y), RED_X, a * k3, 4); cross(cv, 755, y, 18, a * k3)
            cv.text('不许供货', 755, y - 50, 26, 'sans_bold', col=RED_X, a=a * k3)
        k4 = appear(t, 'c1f', '想方设法')
        if k4 > 0:
            cv.text('她从别处进货，照样降价', W / 2, 1250, 44, 'serif_black', gold=True, a=a * k4, glow=0.1)
        source(cv, '伯克希尔 1983 年信（“pressured furniture and carpet manufacturers not to sell to her. But by various strategies she obtained merchandise and cut prices sharply”）', a, y=1462)
    # c1g–c1h：被告上法庭；法官买地毯
    t0, t1 = S('c1g') - 0.45, S('c1e') + 0.1
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['cp_slipper', 'al_living', 'al_dining'], cy=WCY, h=WH, a=a, cap='示意画面：地毯与客厅（约 1960 年宣传片 / 1958 年影片）')
        kc = 1 - eo((t - S('c1h') + 0.3) / 0.4)
        if kc > 0.004:
            k = appear(t, 'c1g', '公平贸易法')
            if k > 0:
                cv.text('“公平贸易法”', W / 2, 920, 48, 'serif_black', col=CREAM, a=a * k * kc)
                cv.text('允许厂商规定最低零售价', W / 2, 990, 30, 'sans_med', col=GREY, a=a * k * kc)
            k2 = appear(t, 'c1g', '最低价')
            price_tag(cv, 360, 1170, 1.0, a * k2 * kc, '最低价', sub='厂商规定', col=GREY)
            k3 = appear(t, 'c1g', '还低')
            price_tag(cv, 760, 1190, 1.1, a * k3 * kc, '更低', sub='B 太太', col=COST_R, rot=0.05)
        k4 = appear(t, 'c1h', '赢了所有官司')
        if k4 > 0: cv.text('官司全赢', W / 2, 980, 96, 'serif_black', gold=True, a=a * k4, glow=0.25)
        k5 = appear(t, 'c1h', '一千四百', lead=0.25)
        if k5 > 0:
            cv.text(counter(0, 1400, t, WT('c1h', '一千四百'), 1.0, lambda v: f'${v:,.0f}'), W / 2, 1170, 90, 'sans_bold', gold=True, a=a * k5, glow=0.15)
            cv.text('法官从她那儿买走的地毯', W / 2, 1270, 34, 'sans_med', col=CREAM, a=a * k5)
        source(cv, '伯克希尔 1983 年信（“hauled into court for violation of Fair Trade laws … won all the cases … sold the judge $1400 worth of carpet”）', a, y=1462)
    # c1i：1946 年的账本
    t0, t1 = win2('c1i')
    a = A(t, t0, t1)
    if a > 0:
        t50 = WT('c1i', '五十美元'); t72 = t50 - 1.6
        docview(cv, 'doc_bs1946', t, t0, t1, [(t0, 0.5, 0.14, 0.75), (t72 - 0.6, 0.58, 0.70, 0.62), (t50 - 0.7, 0.5, 0.21, 0.55)],
                hls=[(0.725, 0.712, 0.865, 0.738, t72), (0.155, 0.194, 0.31, 0.214, t50 - 0.25), (0.585, 0.194, 0.725, 0.214, t50)],
                a=a, cap='NFM 1946 年资产负债表')
        money(cv, t, t50, '$50', W / 2, 1060, 170, a, col=RED_X, sub='1946 年底 · 账上现金')
        source(cv, 'NFM 1946 年资产负债表原件（伯克希尔 2013 年年报第 116 页：Cash on Hand $50.00；Balance $72,264.41）', a, y=1462)
    # c1j：路易从战场回来
    t0, t1 = win2('c1j')
    a = A(t, t0, t1)
    if a > 0:
        tw = WT('c1j', '母子俩')
        photo_win(cv, 'loc_jaws', t, t0, tw + 0.3, cy=WCY, h=WH, a=a, cap='1944 年 6 月 6 日，诺曼底奥马哈海滩', z0=1.0, z1=1.08)
        photo_win(cv, 'loc_dday', t, tw - 0.1, t1, cy=WCY, h=WH, a=a, cap='奥马哈海滩（1944）')
        k = appear(t, 'c1j', '一九四五')
        if k > 0:
            cv.text('路易·布鲁姆金', W / 2, 950, 56, 'serif_black', gold=True, a=a * k, glow=0.1)
            cv.text('B 太太唯一的儿子', W / 2, 1020, 28, 'sans_med', col=CREAM, a=a * k)
        for j, (s_, tw_) in enumerate((('诺曼底 · 奥马哈海滩', '诺曼底'), ('负伤 · 紫心勋章', '负过伤'), ('1945 年底回家', '一九四五'))):
            kk = appear(t, 'c1j', tw_)
            chip(cv, s_, W / 2, 1120 + j * 75, 30, a * kk, col=GOLD if j < 2 else CREAM)
        k2 = appear(t, 'c1j', '没日没夜')
        if k2 > 0: cv.text('母子俩没日没夜地干', W / 2, 1360, 34, 'sans_bold', col=GOLD_L, a=a * k2)
        source(cv, '伯克希尔 2020 年信（Omaha Beach、Purple Heart、Battle of the Bulge、“sailed home in November 1945”）', a, y=1462)
    # c1k：卖得便宜，说真话
    t0, t1 = S('c1k') - 0.45, CHE('ch1')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['al_sideboard'], cy=WCY, h=WH, a=a, cap='家具（1958 年影片）')
        qcard(cv, 'qmotto', t, WT('c1k', '一句话') - 0.2, t1, cy=1100, en=40, cn=56, a=a, typing=0.9, w=900)
        source(cv, '伯克希尔 1984 年信（“Mrs. B boils it down to ‘sell cheap and tell the truth’”）', a, y=1462)


# ======================================================================== 第二章：一页多纸
def shot_ch2(cv, t):
    supermoney(cv, t)
    # c2a–c2b：一家店，一亿多美元，比全城同行加起来还多
    t0, t1 = S('c2a') - 0.45, S('c2c') + 0.1
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['al_dining', 'al_chair', 'al_living'], cy=WCY, h=WH, a=a, cap='示意画面：家具（1958 年影片）')
        k = appear(t, 'c2a', '一亿多')
        if k > 0:
            store_box(cv, 260, 1010, 0.9, a * k, 'NFM', sub='奥马哈 · 1983')
            cv.text(counter(0, 100, t, WT('c2a', '一亿多'), 1.0, lambda v: f'${v:.0f}00 万+' if v < 100 else '$1 亿+'), 720, 980, 90, 'sans_bold', gold=True, a=a * k, glow=0.15)
            cv.text('1983 年销售额', 720, 1070, 30, 'sans_med', col=CREAM, a=a * k)
        k2 = appear(t, 'c2a', '全靠')
        if k2 > 0: chip(cv, '全靠奥马哈一家店', W / 2, 1160, 32, a * k2 * (1 - appear(t, 'c2a', '比全城')), col=GOLD)
        k3 = appear(t, 'c2a', '比全城')
        if k3 > 0:
            e = eexp((t - WT('c2a', '比全城')) / 1.0)
            gbar(cv, 220, 1300 - 150 * e, 400, 1300, GOLD, a * k3, glow=0.2)
            gbar(cv, 600, 1300 - 120 * e, 860, 1300, BLUE_L * 0.5, a * k3)
            cv.text('NFM 一家店', 310, 1340, 26, 'sans_bold', col=GOLD_L, a=a * k3)
            cv.text('奥马哈所有同行合计', 730, 1340, 26, 'sans_med', col=CREAM, a=a * k3)
            cv.text('示意', 960, 1340, 20, 'sans_light', col=GREY, a=a * k3)
        source(cv, '伯克希尔 1983 年信（“over $100 million of sales annually out of one 200,000 square-foot store … more … than do all Omaha competitors combined”）', a, y=1462)
    # c2c：89 岁，为家族的长远打算，愿意卖了
    t0, t1 = win2('c2c')
    a = A(t, t0, t1)
    if a > 0:
        docview(cv, 'doc_proposal2', t, t0, t1, [(t0, 0.5, 0.45, 0.95), (t1, 0.55, 0.62, 0.72)], a=a, cap='提议书签字页：B 太太与家人（1983-08-30）')
        k = appear(t, 'c2c', '八十九岁')
        if k > 0: cv.text('89 岁的 B 太太，愿意卖了', W / 2, 960, 56, 'serif_black', gold=True, a=a * k, glow=0.1)
        k2 = appear(t, 'c2c', '长远打算')
        if k2 > 0: chip(cv, '为家族的长远打算', W / 2, 1080, 34, a * k2, col=CREAM)
        source(cv, '伯克希尔 1983 年信（“for far-sighted family reasons, was willing to sell”）', a, y=1462)
    # c2d：提议书——现金买九成，一成留给家族，店还交给这一家人
    t0, t1 = win2('c2d')
    a = A(t, t0, t1)
    if a > 0:
        docview(cv, 'doc_proposal1', t, t0, t1, [(t0, 0.5, 0.26, 0.85), (WT('c2d', '剩下一成') - 0.4, 0.46, 0.284, 0.62)],
                hls=[(0.142, 0.262, 0.19, 0.283, WT('c2d', '九成') - 0.1), (0.66, 0.262, 0.79, 0.283, WT('c2d', '剩下一成')),
                     (0.142, 0.283, 0.765, 0.302, WT('c2d', '剩下一成') + 0.5)], a=a, cap='提议书第 1 页第 (2) 条')
        e = eexp((t - WT('c2d', '九成') + 0.1) / 1.0)
        if e > 0:
            cx, cy, R = 300, 1130, 150
            cv.arc((cx, cy), R - 22, -math.pi / 2, -math.pi / 2 + 2 * math.pi * 0.9 * e, GOLD, a, 44)
            k2 = appear(t, 'c2d', '剩下一成')
            if k2 > 0: cv.arc((cx, cy), R - 22, -math.pi / 2 + 2 * math.pi * 0.9, -math.pi / 2 + 2 * math.pi * (0.9 + 0.1 * k2), CREAM, a, 44)
            cv.text('90%', cx, cy - 12, 56, 'oswald', col=GOLD_L, a=a * e)
            cv.text('伯克希尔 · 现金', cx, cy + 44, 22, 'sans_med', col=CREAM, a=a * e)
        k3 = appear(t, 'c2d', '剩下一成')
        if k3 > 0: cv.text('10% 留给路易和儿子们', 720, 1060, 34, 'sans_bold', col=CREAM, a=a * k3)
        k4 = appear(t, 'c2d', '店还由')
        if k4 > 0: cv.text('店，还由这一家人管', 720, 1180, 42, 'serif_black', gold=True, a=a * k4)
        source(cv, '收购提议书原件（“90% … for $55,350,000 cash. All of the 10% … retained by Mr. Louis Blumkin and his sons”）', a, y=1462)
    # c2e：签字
    t0, t1 = win2('c2e')
    a = A(t, t0, t1)
    if a > 0:
        ts = WT('c2e', '依次签了名')
        docview(cv, 'doc_proposal2', t, t0, t1, [(t0, 0.55, 0.37, 0.62), (ts - 0.3, 0.35, 0.53, 0.62), (t1, 0.35, 0.74, 0.62)],
                hls=[(0.47, 0.355, 0.80, 0.395, t0 + 0.4)], a=a, cap='签字页：巴菲特与五位股东（1983-08-30）')
        for j, (s_, tw) in enumerate((('没有投资银行', '没有投资银行'), ('没有律师', '律师'))):
            k = appear(t, 'c2e', tw)
            if k > 0:
                cv.text(s_, 300 + j * 480, 960, 38, 'sans_bold', col=CREAM, a=a * k)
                cross(cv, 300 + j * 480 - text_size(s_, 'sans_bold', 38)[0] / 2 - 40, 960, 14, a * k)
        k = appear(t, 'c2e', '一个字没改')
        if k > 0: cv.text('一个字没改', W / 2, 1090, 92, 'serif_black', gold=True, a=a * k, glow=0.2, scale=1.15 - 0.15 * k)
        for j in range(5):
            kk = eo((t - WT('c2e', '依次签了名') - j * 0.16) / 0.35)
            if kk <= 0: continue
            x = 200 + j * 170
            person(cv, x, 1250, 1.3, a * kk, GOLD_L if j == 0 else CREAM)
            cv.text('20%', x, 1325, 28, 'oswald', col=GOLD_L, a=a * kk)
        source(cv, '伯克希尔 2013 年信（“accepted my offer without changing a word … without the involvement of investment bankers or lawyers”）；签字页（五位股东各 20%）', a, y=1462)
    # c2f：从没审计，也没要求 → “一张支票，换一句话”
    t0, t1 = win2('c2f')
    a = A(t, t0, t1)
    if a > 0:
        photo_win(cv, first_have(['buffett_2010', 'c_buffett_2010']), t, t0, t1, cy=WCY, h=WH, a=a, cap='沃伦·巴菲特（2010 年）')
        kq = eo((t - E('c2f') + 0.3) / 0.4)
        check_list(cv, t, [('从没审计过', WT('c2f', '从没审计')), ('也没要求审计', WT('c2f', '也没要求'))], 360, 930, 76, a * (1 - kq), size=40)
        qcard(cv, 'qcheck', t, E('c2f') - 0.2, t1, cy=1110, en=31, cn=40, a=a, typing=1.8, w=960)
        source(cv, '伯克希尔 1984 年信（“NFM had never had an audit and we did not request one … We gave Mrs. B a check for $55 million and she gave us her word”）', a, y=1462)
    # c2i：价钱贵不贵？1984 年税前 1450 万
    t0, t1 = S('c2i') - 0.45, S('c2l') + 0.1
    a = A(t, t0, t1, 0.4, 0.4)
    if a > 0:
        right_terms_chart(cv, t, a)
        k = appear(t, 'c2i', '贵不贵')
        if k > 0 and t < S('c2j'): big_q(cv, t, '这个价钱，贵不贵？', 940, WT('c2i', '贵不贵'), 60, a * (1 - appear(t, 'c2i', '一千四百')))
        k2 = appear(t, 'c2i', '一千四百', lead=0.25)
        if k2 > 0:
            kf = 1 - appear(t, 'c2j', '作价', d=0.3, lead=0.6)
            cv.text(counter(0, 1451, t, WT('c2i', '一千四百'), 1.0, lambda v: f'${v:,.0f} 万'), W / 2, 1000, 104, 'sans_bold', gold=True, a=a * k2 * kf, glow=0.15)
            cv.text('1984 年 · NFM 税前利润（全公司）', W / 2, 1100, 32, 'sans_med', col=CREAM, a=a * k2 * kf)
        k3 = appear(t, 'c2j', '作价', lead=-0.05)
        if k3 > 0:
            kf = 1 - appear(t, 'c2m', '买下之后', d=0.3, lead=0.45)
            cv.text('作价 ≈ $6000 万', W / 2, 960, 60, 'serif_black', col=CREAM, a=a * k3 * kf)
            cv.text('≈ 当年税前利润 × 4', W / 2, 1060, 72, 'serif_black', gold=True, a=a * appear(t, 'c2j', '四倍') * kf, glow=0.15)
        k4 = appear(t, 'c2m', '买下之后', d=0.4, lead=-0.1)
        if k4 > 0:
            cv.text('1984–1990 · 七年税前利润合计', W / 2, 950, 34, 'sans_med', col=CREAM, a=a * k4)
            cv.text(counter(0, 1.1448, t, WT('c2m', '加起来'), 1.0, lambda v: f'约 ${v:.2f} 亿'), W / 2, 1050, 96, 'sans_bold', gold=True, a=a * appear(t, 'c2m', '加起来', lead=0.25), glow=0.15)
            cv.text('≈ 作价 × 1.9', W / 2, 1150, 48, 'serif_black', col=GOLD_L, a=a * appear(t, 'c2m', '两倍'))
        cv.text('口径：NFM 全公司税前利润；作价按 2020 年信“价值 6000 万美元”', W / 2, 1380, 20, 'sans_light', col=GREY, a=a * appear(t, 'c2j', '作价'))
        source(cv, '伯克希尔 1984–1990 年信利润表（NFM 税前：1984 $14.5M … 1990 $17.2M，七年合计 $114.5M 为本片加总）；2020 年信（“a business worth $60 million”）', a, y=1462)
    # c2l：合理的价钱——芒格先想明白的
    t0, t1 = S('c2l') - 0.45, S('c2k') + 0.1
    a = A(t, t0, t1, 0.4, 0.4)
    if a > 0:
        nm = first_have(['c_buffett_munger', 'c_munger', 'buffett_2010'])
        photo_win(cv, nm, t, t0, t1, cy=WCY, h=WH, a=a, cap={'c_buffett_munger': '巴菲特与芒格', 'c_munger': '查理·芒格（2010 年）'}.get(nm, '沃伦·巴菲特（2010 年）'))
        k = appear(t, 'c2l', '合理的价钱')
        if k > 0 and t < E('c2l') - 0.3:
            cv.text('好生意 + 合理的价钱', W / 2, 1000, 62, 'serif_black', gold=True, a=a * k * (1 - eo((t - E('c2l') + 0.6) / 0.3)), glow=0.12)
        qcard(cv, 'qfair', t, E('c2l') - 0.2, t1, cy=1110, en=29, cn=37, a=a, typing=2.2, w=960)
    # c2k：对的人——经营的人没换
    t0, t1 = win2('c2k')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['op_crowd', 'tx_promo2'], cy=WCY, h=WH, a=a, cap='NFM 得州店的员工（2015-05-07 开业当天）')
        k = appear(t, 'c2k', '对的人')
        if k > 0: chip(cv, '对的人：经营的人没换', W / 2, 900, 32, a * k, col=GOLD)
        k2 = appear(t, 'c2k', '九十一岁')
        if k2 > 0:
            cv.text('每周 7 天', 300, 1030, 72, 'serif_black', gold=True, a=a * k2, glow=0.1)
            cv.text('从开门干到关门', 300, 1110, 32, 'sans_med', col=CREAM, a=a * appear(t, 'c2k', '开门'))
            cv.text('91 岁的 B 太太（1984）', 300, 1165, 24, 'sans_light', col=GREY, a=a * k2)
        k3 = appear(t, 'c2k', '一天做的决定')
        if k3 > 0:
            cv.text('她的 1 天', 780, 1000, 40, 'sans_bold', col=GOLD_L, a=a * k3)
            cv.text('>', 780, 1068, 52, 'oswald', col=CREAM, a=a * appear(t, 'c2k', '比大多数'))
            cv.text('多数 CEO 的 1 年', 780, 1135, 40, 'sans_bold', col=CREAM, a=a * appear(t, 'c2k', '比大多数'))
            cv.text('（决定的数量）', 780, 1190, 24, 'sans_light', col=GREY, a=a * appear(t, 'c2k', '比大多数'))
        k4 = appear(t, 'c2k', '一年做的还多')
        if k4 > 0: cv.text('“better ones, too.” —— 还做得更好', W / 2, 1300, 32, 'corm', col=GOLD_L, a=a * eo((t - E('c2k') + 0.2) / 0.4))
        source(cv, '伯克希尔 1984 年信（“Mrs. B, Chairman of the Board, is now 91 … at the store seven days a week, from opening to close, and probably makes more decisions in a day than most CEOs do in a year (better ones, too)”）', a, y=1462)


# ======================================================================== 第三章：好生意——商业模式与低成本护城河
GATES = [('第一关', '优势是真的', 'REAL'), ('第二关', '对手长期学不来', 'HARD TO COPY')]
FORMULA = [('一处地方，品种最全', '一处地方'), ('量最大，进货最精', '量最大'), ('费用最低', '费用最低'),
           ('价格远低于对手', '价格远低于'), ('家里人永远在店里', '家里人')]
BARRIERS = [('规模', '一家店的销量 ≈ 全美任何同行的两倍', 'c3n5', '第一是'), ('人', '一家人守在店里，精打细算、当场拍板', 'c3n6', '第二是'),
            ('甘愿少赚', '对手靠四成多毛利过日子，跟降就是自断财路', 'c3n7', '第三是')]


def gate_tag(cv, n, a, y=860):
    """小标：第一关 / 第二关"""
    if a <= 0.004: return
    g, txt, en = GATES[n - 1]
    chip(cv, f'{g}：{txt}', W / 2, y, 30, a, col=GOLD_L)


def two_gates(cv, t, a, ks, y=1110, hl=None):
    for j, (g, txt, en) in enumerate(GATES):
        k = ks[j]
        if k <= 0: continue
        x = 300 + j * 480; yy = y + 30 * (1 - k)
        on = hl is None or hl == j
        cv.rrect(x - 215, yy - 120, x + 215, yy + 120, 18, (0.075, 0.06, 0.045), a * k * 0.94)
        cv.rrect(x - 215, yy - 120, x + 215, yy + 120, 18, GOLD if on else GOLD_D, a * k * (0.95 if on else 0.5), fill=False, th=3, glow=0.12 if on else 0)
        cv.text(g, x, yy - 62, 34, 'sans_bold', col=GOLD_L if on else GREY, a=a * k)
        cv.text(txt, x, yy + 6, 44 if j == 0 else 40, 'serif_black', col=CREAM if on else GREY, a=a * k)
        cv.text(en, x, yy + 74, 22, 'sans_med', col=GOLD_D, a=a * k, track=0.12)


def shot_ch3(cv, t):
    # c3z：愿不愿意跟它竞争？ → 灰熊
    t0, t1 = S('c3z') - 0.45, S('c3m1') + 0.1
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['tx_promo1', 'tx_promo2', 'op_crowd'], cy=WCY, h=WH, a=a, cap='今天的 NFM：得州店（2015）')
        kq = appear(t, 'c3z', '他的回答')
        big_q(cv, t, '假如我有足够的钱和人手，', 960, WT('c3z', '假如'), 44, a * (1 - kq), col=CREAM)
        big_q(cv, t, '愿不愿意跟它竞争？', 1060, WT('c3z', '愿不愿意'), 60, a * (1 - kq))
        qcard(cv, 'qgrizzly', t, E('c3z') - 0.1, t1, cy=1100, en=32, cn=40, a=a, typing=1.4, w=940)
        source(cv, '伯克希尔 1983 年信（“One question I always ask myself in appraising a business is how I would like … to compete with it”）', a * (1 - kq * 0.5), y=1462)

    # c3m1：商业模式——巴菲特总结的五条打法（1989 年信）
    t0, t1 = S('c3m1') - 0.45, S('c3m2') + 0.1
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['op_crowd', 'tx_promo2', 'cp_room', 'tx_promo1'], cy=WCY - 40, h=480, a=a, cap='NFM 得州店（2015）/ 地毯宣传片（约 1960）')
        k0 = eo((t - t0 - 0.2) / 0.5)
        cv.text('它靠什么赚钱？', W / 2, 865, 50, 'serif_black', gold=True, a=a * k0)
        for j, (txt, w_) in enumerate(FORMULA):
            k = appear(t, 'c3m1', w_)
            if k <= 0: continue
            y = 960 + j * 92 + 20 * (1 - k)
            cur = j == max([i for i, (_, ww) in enumerate(FORMULA) if t >= WT('c3m1', ww) - 0.1] or [0])
            cv.rrect(110, y - 38, 970, y + 38, 14, (0.08, 0.065, 0.045) if cur else (0.05, 0.045, 0.04), a * k * 0.92)
            cv.rrect(110, y - 38, 970, y + 38, 14, GOLD if cur else GOLD_D, a * k * (0.9 if cur else 0.4), fill=False, th=2)
            cv.text(f'{j + 1}', 165, y, 40, 'oswald', col=GOLD_L if cur else GOLD_D, a=a * k)
            cv.text(txt, 220, y, 38, 'sans_bold', col=CREAM if cur else (0.78, 0.76, 0.72), a=a * k, anchor='l')
        source(cv, '伯克希尔 1989 年信（成功公式：“unparalleled depth and breadth of merchandise at one location; the lowest operating costs …”）', a, y=1462)

    # c3m2：薄利多销，省下的钱让给顾客 → 每年至少 3000 万
    t0, t1 = win2('c3m2')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['op_flags', 'op_ribbon'], cy=WCY, h=WH, a=a, cap='NFM 得州店开业那天的顾客（2015-05-07）')
        k = appear(t, 'c3m2', '每件货')
        k2 = appear(t, 'c3m2', '薄利')
        k3 = appear(t, 'c3m2', '三千万', lead=0.25)
        if k > 0 and k3 < 1:
            aa = a * (1 - k3)
            cv.text('不靠每件货多赚', 300, 930, 38, 'sans_bold', col=GREY, a=aa * k)
            cross(cv, 300, 930, 34, aa * k2 * 0.8, th=4)
            cv.text('薄利多销', 780, 930, 52, 'serif_black', gold=True, a=aa * k2, glow=0.15)
            ka = appear(t, 'c3m2', '让给顾客')
            if ka > 0:
                arrow(cv, (420, 1080), (660, 1080), aa * ka, GOLD, k=ka)
                node(cv, 280, 1080, '省下的钱', aa * ka, col=CREAM, size=34)
                node(cv, 820, 1080, '顾客', aa * ka, col=GOLD, size=40)
        if k3 > 0:
            cv.text(counter(0, 3000, t, WT('c3m2', '三千万'), 1.2, lambda v: f'≥ ${v:,.0f} 万'), W / 2, 990, 104, 'sans_bold', gold=True, a=a * k3, glow=0.12)
            cv.text('每年替顾客省下（巴菲特 1984 年估算）', W / 2, 1095, 32, 'sans_med', col=CREAM, a=a * k3)
            kr = appear(t, 'c3m2', '资本回报')
            if kr > 0:
                chip(cv, '自己的资本回报：照样出色', W / 2, 1200, 36, a * kr, col=GOLD_L)
                cv.text('“excellent returns on capital”', W / 2, 1275, 28, 'serif_reg', col=CREAM, a=a * kr)
        source(cv, '伯克希尔 1983 年信（“pass on to their customers much of the savings”）；1984 年信（“earn excellent returns on capital while saving its customers at least $30 million annually”）', a, y=1462)

    # c3d：飞轮
    t0, t1 = win2('c3d')
    a = A(t, t0, t1)
    if a > 0:
        labels = ['价格低', '顾客多', '进货量大', '成本更低']
        ks = [appear(t, 'c3d', '价格低'), appear(t, 'c3d', '顾客就多'), appear(t, 'c3d', '进货就能'), appear(t, 'c3d', '成本更低')]
        ring_cycle(cv, t, W / 2, 640, 230, labels, a, ks, col=GOLD, size=40)
        k = appear(t, 'c3d', '摊到')
        if k > 0:
            chip(cv, '压低进价', 300, 1030, 32, a * appear(t, 'c3d', '压价'), col=CREAM); chip(cv, '摊薄房租、工资、广告', 720, 1030, 32, a * k, col=CREAM)
        k2 = appear(t, 'c3d', '轮子')
        if k2 > 0: cv.text('轮子越转越快', W / 2, 1200, 72, 'serif_black', gold=True, a=a * k2, glow=0.15)
        source(cv, '伯克希尔 1984 年信（“unparalleled efficiency and astute volume purchasing”）；1989 年信（成功公式）；飞轮为本片概括', a, y=1462)
    # c3s：尼克·斯利普的“规模经济分享”
    t0, t1 = win2('c3s')
    a = A(t, t0, t1)
    if a > 0:
        k0 = eo((t - t0 - 0.2) / 0.5)
        cv.text('规模经济分享', W / 2, 330, 72, 'serif_black', gold=True, a=a * appear(t, 'c3s', '规模经济分享'), glow=0.12)
        cv.text('SCALE ECONOMIES SHARED', W / 2, 410, 26, 'sans_med', col=GOLD_D, a=a * appear(t, 'c3s', '规模经济分享'), track=0.18)
        chip(cv, '投资人 尼克·斯利普（Nomad 合伙人信）', W / 2, 250, 28, a * k0, col=CREAM)
        steps = [('成本优势', '规模经济分享'), ('让利 → 低价', '长期分给'), ('顾客更多', '长期分给'), ('规模更大', '他举的'), ('成本更低', '他举的')]
        for j, (lb, w_) in enumerate(steps):
            k = appear(t, 'c3s', w_, lead=0.1 - j * 0.25)
            if k <= 0: continue
            y = 530 + j * 92
            node(cv, W / 2, y + 12 * (1 - k), lb, a * k, col=GOLD if j in (0, 4) else CREAM, size=32, w=330)
            if j < 4 and appear(t, 'c3s', steps[j + 1][1], lead=0.1 - (j + 1) * 0.25) > 0: arrow(cv, (W / 2, y + 34), (W / 2, y + 58), a, GOLD_D, head=10)
        kb = appear(t, 'c3s', '不是短期')
        if kb > 0:
            cv.text('不是短期贴钱抢市场', 300, 1060, 32, 'sans_bold', col=GREY, a=a * kb)
            cross(cv, 300, 1060, 30, a * kb * 0.7, th=4)
            cv.text('而是长期分享规模效率', 780, 1060, 34, 'sans_bold', col=GOLD_L, a=a * appear(t, 'c3s', '长期分给'))
        kc = appear(t, 'c3s', '他举的')
        if kc > 0:
            chip(cv, 'Costco', 380, 1190, 40, a * kc, col=GOLD); chip(cv, '亚马逊 Amazon', 720, 1190, 40, a * kc, col=GOLD)
            cv.text('NFM 早在几十年前就是这样做的', W / 2, 1290, 30, 'sans_med', col=CREAM, a=a * kc)
        source(cv, 'Nomad Investment Partnership 合伙人信（Nick Sleep、Qais Zakaria，2001–2013）：“scale economics shared”，以 Costco、Amazon 为例', a, y=1462)
    # c3f：得梅因，130 英里外的第三名
    t0, t1 = win2('c3f')
    a = A(t, t0, t1)
    if a > 0:
        photo_win(cv, 'loc_desmoines', t, t0, t1, cy=WCY, h=WH, a=a, cap='艾奥瓦州得梅因（Carol M. Highsmith 摄）')
        mx, my, sc = 560, 1150, 150
        km = eo((t - WT('c3f', '可它远在') + 0.3) / 0.6)
        if km > 0:
            usmap(cv, mx, my, sc, a * km, lat0=41.4, lon0=-94.8, box=(60, 900, 1020, 1400))
            city(cv, '奥马哈', mx, my, sc, a, km, lat0=41.4, lon0=-94.8, anchor='r', sub='NFM 唯一的店')
            pd = map_xy(*CITY['得梅因'], mx, my, sc, 41.4, -94.8); po = map_xy(*CITY['奥马哈'], mx, my, sc, 41.4, -94.8)
            kk = appear(t, 'c3f', '一百三十')
            link(cv, po, pd, a, kk, GOLD, dashed=True)
            if kk > 0: cv.text('130 英里', (po[0] + pd[0]) / 2, (po[1] + pd[1]) / 2 - 36, 36, 'sans_bold', col=GOLD_L, a=a * kk, shadow=0.8)
            rng = np.random.default_rng(4)
            for j in range(19):
                ang, rr = rng.uniform(0, 2 * math.pi), rng.uniform(8, 46)
                cv.glow_dot((pd[0] + rr * math.cos(ang), pd[1] + rr * math.sin(ang)), 4, CREAM, a * km * 0.8)
            city(cv, '得梅因', mx, my, sc, a, km, col=CREAM, lat0=41.4, lon0=-94.8, sub='19 家本地家具店', dx=60)
        k = appear(t, 'c3f', '排第三')
        if k > 0 and km < 1:
            cv.text('20 家家具店里，NFM 人气第三', W / 2, 1000, 44, 'serif_black', gold=True, a=a * k * (1 - km))
        if km > 0 and appear(t, 'c3f', '排第三') > 0:
            chip(cv, '人气第 3', 280, 1300, 32, a * km, col=GOLD)
        source(cv, '伯克希尔 1990 年信（“NFM was Number 3 in popularity among 20 furniture retailers serving that city … our store is 130 miles away”）', a, y=1462)
    # c3g：河底也找得到
    t0, t1 = win2('c3g')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['tx_promo2', 'op_crowd'], cy=WCY, h=WH, a=a, cap='今天的 NFM：得州店（2015）')
        qcard(cv, 'qriver', t, t0 + 0.4, t1, cy=1110, en=30, cn=38, a=a, typing=1.4, w=940)
    # c3n1：低价是策略，低成本才是优势；低成本要成为护城河，得过两关
    t0, t1 = win2('c3n1')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['tx_promo1', 'tx_render'], cy=WCY, h=WH, a=a, cap='NFM 得州店（2015）')
        kg = appear(t, 'c3n1', '还得过两关')
        k1 = appear(t, 'c3n1', '低价只是') * (1 - kg)
        if k1 > 0:
            cv.rrect(90, 900, 520, 1230, 18, (0.05, 0.045, 0.04), a * k1 * 0.92)
            cv.rrect(90, 900, 520, 1230, 18, GOLD_D, a * k1 * 0.5, fill=False, th=2)
            cv.text('低价', 305, 975, 56, 'serif_black', col=CREAM, a=a * k1)
            cv.text('= 竞争策略', 305, 1060, 38, 'sans_bold', col=GREY, a=a * k1)
            cv.text('谁都可以降价', 305, 1150, 30, 'sans_med', col=GREY, a=a * appear(t, 'c3n1', '谁都可以') * (1 - kg))
            k2 = appear(t, 'c3n1', '低成本才是') * (1 - kg)
            if k2 > 0:
                cv.rrect(560, 900, 990, 1230, 18, (0.08, 0.065, 0.045), a * k2 * 0.94)
                cv.rrect(560, 900, 990, 1230, 18, GOLD, a * k2 * 0.95, fill=False, th=3, glow=0.12)
                cv.text('低成本', 775, 975, 56, 'serif_black', gold=True, a=a * k2)
                cv.text('= 竞争优势', 775, 1060, 38, 'sans_bold', col=GOLD_L, a=a * k2)
                cv.text('撑得起长期低价', 775, 1150, 30, 'sans_med', col=CREAM, a=a * k2)
        if kg > 0:
            cv.text('低成本要成为护城河', W / 2, 900, 52, 'serif_black', gold=True, a=a * kg, glow=0.1)
            two_gates(cv, t, a * kg, [appear(t, 'c3n1', '第一'), appear(t, 'c3n1', '第二')], y=1130)
        source(cv, '本片分析框架：低价是竞争策略，低成本是竞争优势；低成本优势须真实存在，且对手难以长期复制', a, y=1462)
    # c3a–c3b：Levitz 毛利率 44.4%，NFM 一半多一点
    t0, t1 = S('c3a') - 0.45, S('c3c') + 0.1
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['lv_sofa', 'lv_sofa2', 'tx_promo1', 'tx_promo2', 'al_living'], cy=WCY, h=WH, a=a, cap='Levitz 电视广告（1999）/ NFM 得州店（2015）')
        gate_tag(cv, 1, a * eo((t - t0 - 0.3) / 0.5))
        chip(cv, '巴菲特 1984 年致股东信', W / 2, 905, 26, a * eo((t - t0 - 0.3) / 0.5), col=GOLD_D)
        k = appear(t, 'c3a', 'Levitz')
        kb = appear(t, 'c3b', '毛利率')
        if k > 0 and kb < 1:
            node(cv, 280, 1050, 'Levitz', a * k * (1 - kb), col=BLUE_L, size=40, sub='全美最大的独立家具商')
            cv.text('VS', W / 2, 1050, 40, 'oswald', col=GOLD, a=a * k * (1 - kb))
            node(cv, 800, 1050, 'NFM', a * k * (1 - kb), col=GOLD, size=40, sub='奥马哈 · 一家店')
        k2 = appear(t, 'c3b', '百分之四十四')
        if k2 > 0:
            price_tag(cv, 840, 1000, 0.75, a * k2, '$100', sub='Levitz 售价', col=BLUE_L * 0.8)
            cv.text('进价 $55.6', 840, 1090, 26, 'sans_med', col=CREAM, a=a * k2)
        if kb > 0: cv.text('毛利率', 200, 990, 32, 'sans_bold', col=CREAM, a=a * kb, anchor='l')
        pct_bars(cv, t, [('Levitz', 44.4, '44.4%', WT('c3b', '百分之四十四'), BLUE_L * 0.7),
                         ('NFM', 24.0, '一半多一点', WT('c3b', '一半多'), GOLD)], a, x0=330, x1=780, y0=1170, dy=110, vmax=50, size=38, lab=30)
        if appear(t, 'c3b', '一半多') > 0: cv.text('NFM 柱长为示意（原信：“not much more than half”）', W / 2, 1360, 20, 'sans_light', col=GREY, a=a * appear(t, 'c3b', '一半多'))
        source(cv, '伯克希尔 1984 年信（引 Levitz 1984 财年 10-K：毛利率 44.4%；“The gross margin at NFM is not much more than half of that”）', a, y=1462)
    # c3c：营业费用（第一关） 35.6% vs 16.5%
    t0, t1 = win2('c3c')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['al_dining', 'al_chair', 'al_sideboard'], cy=WCY, h=WH, a=a, cap='示意画面：家具（1958 年影片）')
        k = appear(t, 'c3c', '成本')
        if k > 0: cv.text('秘诀在成本', W / 2, 920, 56, 'serif_black', gold=True, a=a * k)
        k2 = appear(t, 'c3c', '工资')
        if k2 > 0: cv.text('营业费用（工资、房租、广告……）占销售额', W / 2, 1010, 28, 'sans_med', col=CREAM, a=a * k2)
        pct_bars(cv, t, [('Levitz', 35.6, '35.6%', WT('c3c', '百分之三十五'), BLUE_L * 0.7),
                         ('NFM', 16.5, '约 16.5%', WT('c3c', '百分之十六'), GOLD)], a, x0=300, x1=900, y0=1130, dy=130, vmax=40, size=50, lab=34)
        source(cv, '伯克希尔 1984 年信（“operating expenses (payroll, occupancy, advertising, etc.) are about 16.5% of sales versus 35.6% at Levitz”）', a, y=1462)
    # c3n3：算一笔账——Levitz 压到 NFM 的价钱会怎样
    t0, t1 = win2('c3n3')
    a = A(t, t0, t1)
    if a > 0:
        gate_tag(cv, 1, a)
        cv.text('假如 Levitz 卖 NFM 的价钱', W / 2, 330, 50, 'serif_black', gold=True, a=a * eo((t - t0 - 0.2) / 0.5))
        cv.text('每 $100 销售额', W / 2, 410, 30, 'sans_med', col=CREAM, a=a * eo((t - t0 - 0.2) / 0.5))
        base, top = 1040, 500
        def Y(v): return base - (base - top) * v / 40.0
        km = appear(t, 'c3n3', '毛利只剩')
        if km > 0:
            h = 24 * km
            gbar(cv, 170, Y(h), 390, base, GOLD, a, glow=0.12, sheen_t=t - WT('c3n3', '毛利只剩'))
            cv.text('毛利', 280, base + 50, 34, 'sans_bold', col=CREAM, a=a * km)
            cv.text('约 $22–26', 280, Y(h) - 40, 40, 'sans_bold', col=GOLD_L, a=a * km)
        kf = appear(t, 'c3n3', '费用却要')
        if kf > 0:
            h = 35.6 * kf
            gbar(cv, 430, Y(h), 650, base, BLUE_L * 0.7, a, glow=0.06, sheen_t=t - WT('c3n3', '费用却要'))
            cv.text('Levitz 的费用', 540, base + 50, 34, 'sans_bold', col=CREAM, a=a * kf)
            cv.text('$35.6', 540, Y(h) - 40, 40, 'sans_bold', col=CREAM, a=a * kf)
        kl = appear(t, 'c3n3', '倒贴')
        if kl > 0:
            gbar(cv, 690, Y(0), 910, Y(0) + (base - top) * 10.0 / 40 * kl, COST_R, a, glow=0.15, reflect=False)
            cv.text('约 −$10', 800, Y(0) - 50, 56, 'sans_bold', col=COST_R, a=a * kl, glow=0.12)
            cv.text('每卖 $100 倒贴', 800, base + 50 + 120, 30, 'sans_bold', col=CREAM, a=a * kl)
        cv.line((130, base), (950, base), GREY, a * 0.7, 2)
        if kl > 0: cv.text('按 1984 年信的约数推算；未计利息与税', W / 2, 1300, 22, 'sans_med', col=GREY, a=a * kl)
        source(cv, '本片推算：Levitz 毛利率 44.4% 的“一半多一点”≈ 22%–26%，减去 Levitz 营业费用率 35.6%（伯克希尔 1984 年信）', a, y=1462)

    # c3n4：第二关——差距六年后反而拉大
    t0, t1 = win2('c3n4')
    a = A(t, t0, t1)
    if a > 0:
        gate_tag(cv, 2, a * eo((t - t0 - 0.2) / 0.5), y=1000)
        cv.text('营业费用率（占销售额）', W / 2, 270, 30, 'sans_bold', col=CREAM, a=a * eo((t - t0 - 0.2) / 0.5))
        base, top = 820, 330
        def Y(v): return base - (base - top) * v / 42.0
        groups = [('1984', 16.5, 35.6, WT('c3n4', '学不学得来') - 0.1, '约 16.5%', '35.6%'), ('1990', 15.0, 40.0, WT('c3n4', '费用率'), '15%', '约 40%')]
        for g, (yr, vn, vl, ts, tn, tl) in enumerate(groups):
            e = eexp((t - ts) / 0.9)
            if e <= 0: continue
            xc = 300 + g * 480
            for j, (v, col, lb, tx) in enumerate(((vn, GOLD, 'NFM', tn), (vl, BLUE_L * 0.7, 'Levitz', tl))):
                x0 = xc - 150 + j * 160
                gbar(cv, x0, Y(v * e), x0 + 130, base, col, a, glow=0.12 if j == 0 else 0.05, sheen_t=t - ts)
                cv.text(tx, x0 + 65, Y(v * e) - 34, 34, 'sans_bold', col=GOLD_L if j == 0 else CREAM, a=a * e)
                cv.text(lb, x0 + 65, base + 34, 26, 'sans_med', col=CREAM, a=a * e)
            cv.text(f'{yr} 年', xc, base + 84, 36, 'oswald', col=GOLD_L, a=a * e)
        cv.line((100, base), (980, base), GREY, a * 0.6, 2)
        kg = appear(t, 'c3n4', '反而拉大了')
        if kg > 0:
            cv.text('差距：19 个点 → 25 个点', W / 2, 1110, 46, 'sans_bold', col=CREAM, a=a * kg)
            cv.text('没缩小，反而拉大了', W / 2, 1220, 70, 'serif_black', gold=True, a=a * kg, glow=0.15)
        source(cv, '伯克希尔 1984 年信（16.5% 对 35.6%）；1990 年信（“operating costs are rock-bottom - 15% in 1990 against about 40% for Levitz”）', a, y=1462)

    # c3n5–c3n7：学不来的三个原因
    t0, t1 = S('c3n5') - 0.45, S('c3h') + 0.1
    a = A(t, t0, t1)
    if a > 0:
        cur = 2 if t >= WT('c3n7', '第三是') - 0.1 else (1 if t >= WT('c3n6', '第二是') - 0.1 else 0)
        names = [['op_crowd', 'tx_promo2'], ['cp_sweep', 'cp_room'], ['lv_sofa', 'lv_sofa2']]
        caps = ['NFM 得州店开业（2015）', '地毯宣传片里的店员（约 1960，仅示意）', 'Levitz 电视广告（1999）']
        for j in range(3):
            s0 = t0 if j == 0 else WT(BARRIERS[j][2], BARRIERS[j][3]) - 0.45
            s1 = t1 if j == 2 else WT(BARRIERS[j + 1][2], BARRIERS[j + 1][3]) + 0.1
            if s0 - 0.1 <= t <= s1 + 0.1: seq(cv, t, s0, s1, names[j], cy=WCY - 70, h=430, a=a, cap=caps[j])
        k0 = appear(t, 'c3n5', '学不来')
        cv.text('为什么学不来？', W / 2, 840, 50, 'serif_black', gold=True, a=a * k0)
        for j, (tg, sub, ln, w_) in enumerate(BARRIERS):
            k = appear(t, ln, w_)
            if k <= 0: continue
            y = 960 + j * 140 + 20 * (1 - k); on = j == cur
            cv.rrect(80, y - 60, 1000, y + 60, 16, (0.08, 0.065, 0.045) if on else (0.05, 0.045, 0.04), a * k * 0.92)
            cv.rrect(80, y - 60, 1000, y + 60, 16, GOLD if on else GOLD_D, a * k * (0.95 if on else 0.45), fill=False, th=2, glow=0.12 if on else 0)
            cv.text(f'0{j + 1}', 140, y, 44, 'oswald', col=GOLD_L if on else GOLD_D, a=a * k)
            cv.text(tg, 200, y - 22, 40, 'serif_black', col=CREAM if on else GREY, a=a * k, anchor='l')
            cv.text(sub, 200, y + 30, 27, 'sans_med', col=CREAM if on else GREY, a=a * k, anchor='l')
        srcs = ['伯克希尔 1990 年信（“NFM does close to double the volume of any other home furnishings store in the country”）；1989 年信（进货量大、买得最精）',
                '伯克希尔 1984 年信（布鲁姆金家的秘诀：干劲、在能力圈内当机立断）；1989 年信（“family members on hand at all times”）',
                '伯克希尔 1984 年信（Levitz 毛利率 44.4%）；“跟降就是自断财路”为本片推论']
        source(cv, srcs[cur], a, y=1462)
    # c3h：Dillard's 不卖家具 → 引语
    t0, t1 = S('c3h') - 0.45, S('c3n8') + 0.1
    a = A(t, t0, t1)
    if a > 0:
        kq = eo((t - E('c3h') + 0.2) / 0.4)
        photo_win(cv, 'loc_boston', t, t0, t1, cy=WCY, h=WH, a=a, cap='奥马哈的百货公司橱窗（1938，仅示意业态）', focus=(0.5, 0.45))
        k = appear(t, 'c3h', '迪拉德') * (1 - kq)
        if k > 0:
            cv.text('Dillard’s 百货进军奥马哈', W / 2, 905, 40, 'sans_bold', col=CREAM, a=a * k)
            store_box(cv, 300, 1060, 0.9, a * k, '别的城市', col=CREAM)
            chip(cv, '卖家具', 300, 1220, 30, a * k, col=CREAM)
            ka = appear(t, 'c3h', '在这儿')
            store_box(cv, 780, 1060, 0.9, a * k * ka, '奥马哈', col=GOLD)
            if ka > 0:
                chip(cv, '不卖家具', 780, 1220, 30, a * k * ka, col=RED_X)
                cross(cv, 780, 1060, 54, a * k * ka * 0.8)
            cv.text('示意', 990, 1300, 20, 'sans_light', col=GREY, a=a * k)
        qcard(cv, 'qdillard', t, E('c3h') - 0.1, t1, cy=1110, en=32, cn=40, a=a, typing=1.4, w=940)
        source(cv, '伯克希尔 1988 年信（“In many of its stores, Dillards runs a full furniture department … his new store would not sell furniture”）', a * (1 - kq * 0.5), y=1462)
    # c3n8：大连锁绕开奥马哈；Levitz 后来破产、清算
    t0, t1 = win2('c3n8')
    a = A(t, t0, t1)
    if a > 0:
        kl = appear(t, 'c3n8', '而当年')
        if kl < 1:
            photo_win(cv, 'loc_omaha_signs', t, t0, WT('c3n8', '而当年') + 0.4, cy=WCY, h=WH, a=a, cap='奥马哈街景（1938，仅示意）')
        if kl > 0:
            seq(cv, t, WT('c3n8', '而当年') - 0.3, t1, ['lv_sofa', 'lv_sofa2'], cy=WCY, h=WH, a=a, cap='Levitz 电视广告（1999）')
        k = appear(t, 'c3n8', '大连锁店')
        if k > 0 and kl < 1:
            cv.text('“major chains … steer clear of Omaha”', W / 2, 950, 36, 'serif_reg', col=CREAM, a=a * k * (1 - kl))
            cv.text('大连锁店干脆绕开奥马哈', W / 2, 1040, 52, 'serif_black', gold=True, a=a * k * (1 - kl))
        if kl > 0:
            ev = [('1984', '被巴菲特拿来对比', '而当年'), ('1997', '申请破产保护', '申请破产'), ('2007', '第三次破产，随后清算', '清算')]
            cv.line((150, 1100), (930, 1100), GOLD_D, a * kl, 3)
            for j, (yr, txt, w_) in enumerate(ev):
                kk = appear(t, 'c3n8', w_)
                if kk <= 0: continue
                x = 200 + j * 340
                cv.glow_dot((x, 1100), 10, COST_R if j else GOLD, a * kk)
                cv.text(yr, x, 1040, 44, 'oswald', col=COST_R if j else GOLD_L, a=a * kk)
                cv.text(txt, x, 1165, 28, 'sans_bold', col=CREAM, a=a * kk)
            cv.text('Levitz', W / 2, 940, 50, 'sans_bold', col=BLUE_L, a=a * kl)
        source(cv, '伯克希尔 1990 年信（“major chains, knowing what they will face, steer clear of Omaha”）；Levitz 破产：1997-09 美联社报道、Wikipedia', a, y=1462)

    # c3i：护城河不是低价本身，而是学不来的低成本（及其换来的顾客与规模）
    t0, t1 = S('c3i') - 0.45, CHE('ch3')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['tx_promo1', 'tx_promo2', 'op_flags'], cy=WCY, h=WH, a=a, cap='今天的 NFM：得州店（2015）')
        k = appear(t, 'c3i', '不是低价本身')
        if k > 0:
            cv.text('护城河 ≠ 低价本身', W / 2, 920, 46, 'sans_bold', col=CREAM, a=a * k)
        k2 = appear(t, 'c3i', '学不来的低成本')
        if k2 > 0: cv.text('而是对手学不来的低成本', W / 2, 1020, 60, 'serif_black', gold=True, a=a * k2, glow=0.15)
        labels = [('撑得起长期低价', '撑得起'), ('照样赚钱', '照样赚钱'), ('换来顾客和规模', '换来的'), ('成本更低', '又让成本')]
        for j, (lb, w_) in enumerate(labels):
            kk = appear(t, 'c3i', w_)
            if kk <= 0: continue
            x = 150 + j * 260
            node(cv, x, 1160 + 10 * (1 - kk), lb, a * kk, col=GOLD if j == 3 else CREAM, size=26, w=228)
            if j < 3 and appear(t, 'c3i', labels[j + 1][1]) > 0: arrow(cv, (x + 116, 1160), (x + 144, 1160), a, GOLD_D, head=9)
        source(cv, '本片解读（1984 年信：低价与“excellent returns on capital”并存；1984、1990 年信费用率对比；1988、1990 年信对手的反应）', a * 0.7, y=1462)


# ======================================================================== 第四章：开到隔壁
def shot_ch4(cv, t):
    # c4b–c4c：1989 年，闹翻；地毯 −17%
    t0, t1 = S('c4b') - 0.45, S('c4d') + 0.1
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['cp_sweep', 'cp_slipper', 'cp_room', 'al_living', 'al_chair'], cy=WCY, h=WH, a=a, cap='示意画面：地毯与家具（约 1960 年宣传片 / 1958 年影片）')
        kc = 1 - eo((t - S('c4c') + 0.3) / 0.4)
        k = appear(t, 'c4b', '一九八九')
        if k > 0 and kc > 0:
            cv.text('1989', W / 2 - 60, 950, 80, 'oswald', col=GOLD_L, a=a * k * kc)
            cv.text('年 5 月', W / 2 + 110, 962, 40, 'sans_bold', col=GOLD_L, a=a * k * kc)
            cv.text('95 岁的 B 太太辞职走了', W / 2, 1060, 46, 'serif_black', gold=True, a=a * appear(t, 'c4b', '辞职') * kc)
            chip(cv, '分歧：地毯部怎么装修、怎么经营', W / 2, 1170, 30, a * appear(t, 'c4b', '地毯部') * kc, col=CREAM)
        k2 = appear(t, 'c4c', '站在家人')
        if k2 > 0: cv.text('这一次，巴菲特站在家人一边', W / 2, 890, 40, 'sans_bold', col=GOLD_L, a=a * k2)
        e1 = eexp((t - WT('c4c', '百分之二十四') + 0.1) / 0.9); e2 = eexp((t - WT('c4c', '百分之十七') + 0.1) / 0.9)
        base = 1190
        if e1 > 0:
            gbar(cv, 300 - 90, base - 180 * e1, 300 + 90, base, GOLD, a, sheen_t=t, reflect=False)
            cv.text('+24%', 300, base - 180 * e1 - 44, 56, 'sans_bold', gold=True, a=a * min(1, e1 * 2))
            cv.text('其他部门', 300, base + 40, 30, 'sans_med', col=CREAM, a=a)
        if e2 > 0:
            cv.line((640, base), (920, base), GREY, a, 2)
            gbar(cv, 780 - 90, base, 780 + 90, base + 128 * e2, RED_X, a, reflect=False)
            cv.text('−17%', 780, base + 128 * e2 + 44, 56, 'sans_bold', col=RED_X, a=a * min(1, e2 * 2))
            cv.text('地毯', 780, base - 40, 30, 'sans_med', col=CREAM, a=a)
        if e1 > 0: cv.text('过去三年的销售变化', 300, 1290, 24, 'sans_light', col=GREY, a=a * min(1, e1 * 2))
        source(cv, '伯克希尔 1989 年信（“quit in May, after disagreeing … about the remodeling and operation of the carpet department … other departments increased sales by 24%, carpet sales declined by 17%”）', a, y=1462)
    # c4d：开到隔壁
    t0, t1 = win2('c4d')
    a = A(t, t0, t1)
    if a > 0:
        photo_win(cv, 'loc_omaha_signs', t, t0, t1, cy=WCY, h=WH, a=a, cap='奥马哈老城的砖楼（2021，仅示意）', z0=1.0, z1=1.10)
        k = appear(t, 'c4d', '没有回家')
        if k > 0: cv.text('她没有回家养老', W / 2, 905, 44, 'serif_black', gold=True, a=a * k)
        store_box(cv, 300, 1070, 0.85, a * eo((t - t0 - 0.2) / 0.5), 'NFM', col=GOLD, sub='内布拉斯加家具城')
        k2 = appear(t, 'c4d', '隔壁')
        if k2 > 0:
            store_box(cv, 780, 1070 + 30 * (1 - k2), 0.85, a * k2, "MRS. B'S", col=RED_X, sub='她自己的新店', glow=0.2)
            cv.text('隔壁', W / 2, 985, 34, 'sans_bold', col=CREAM, a=a * k2)
            arrow(cv, (470, 1025), (610, 1025), a * k2, CREAM, k=k2)
        cv.text('示意', 990, 1200, 20, 'sans_light', col=GREY, a=a * k)
        for j, (s_, tw) in enumerate((('一栋自己早年买下的大楼', '早年买下'), ('卖的还是地毯和家具', '卖的还是'))):
            chip(cv, s_, W / 2 - 210 + j * 420, 1260, 28, a * appear(t, 'c4d', tw), col=CREAM if j == 0 else GOLD)
        k3 = appear(t, 'c4d', '开了一家新店')
        if k3 > 0: cv.text('95 岁 → 从对手做起', W / 2, 1365, 48, 'serif_black', col=RED_X, a=a * k3)
        source(cv, '伯克希尔 1989 年信（“she has started a new business selling - what else? - carpet and furniture”）；1992 年信（“opened up her own operation next door in a large building that she had owned for several years”）', a, y=1462)
    # c4e：提议书里少了一条
    t0, t1 = win2('c4e')
    a = A(t, t0, t1)
    if a > 0:
        docview(cv, 'doc_proposal1', t, t0, t1, [(t0, 0.5, 0.5, 1.0), (t1, 0.5, 0.62, 0.9)], a=a, cap='1983 年提议书')
        k = appear(t, 'c4e', '竞业禁止')
        if k > 0:
            bx0, by0, bx1, by1 = 170, 860, 910, 950
            for j in range(0, 740, 28):
                x = bx0 + j
                if x < bx1: cv.line((x, by0), (min(x + 14, bx1), by0), RED_X, a * k, 4); cv.line((x, by1), (min(x + 14, bx1), by1), RED_X, a * k, 4)
            cv.rect(bx0, by0, bx1, by1, (0.1, 0.03, 0.03), a * k * 0.75)
            cv.text('提议书里：没有竞业禁止条款', W / 2, (by0 + by1) / 2, 42, 'sans_bold', col=RED_X, a=a * k)
        k2 = appear(t, 'c4e', '不够小心')
        if k2 > 0:
            cv.text('“having been incautious on this point', W / 2, 1040, 32, 'typewriter', col=CREAM, a=a * k2)
            cv.text('when she was 89”', W / 2, 1090, 32, 'typewriter', col=CREAM, a=a * k2)
            cv.text('她 89 岁那年，我在这一点上不够小心', W / 2, 1180, 38, 'serif_semi', col=GOLD_L, a=a * k2)
            cv.text('Warren Buffett · 1992 Letter to Shareholders', W / 2, 1250, 24, 'corm', col=GOLD, a=a * k2)
        source(cv, '伯克希尔 1992 年信（“and I, having been incautious on this point when she was 89, snapped at the deal”）', a, y=1462)
    # c4f：1992 年底回归；99 岁签竞业禁止
    t0, t1 = S('c4f') - 0.3, S('c4g') + 0.2
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['al_sideboard', 'al_dining'], cy=WCY, h=WH, a=a, cap='示意画面：家具（1958 年影片）')
        k = appear(t, 'c4f', '一九九二')
        kb = 1 - appear(t, 'c4f', '主动签了', d=0.4)
        if k > 0:
            cv.text('1992', W / 2 - 40, 905, 56, 'oswald', col=GOLD_L, a=a * k)
            cv.text('年底', W / 2 + 70, 911, 36, 'sans_bold', col=GOLD_L, a=a * k)
        k2 = appear(t, 'c4f', '卖给了')
        if kb > 0.004:
            store_box(cv, 300, 1080, 0.85, a * k * kb, 'NFM', col=GOLD)
            if k2 > 0:
                store_box(cv, lerp(780, 560, eio(k2)), 1080, 0.85, a * (1 - 0.2 * k2) * kb, 'NFM', col=GOLD, glow=0.2 * k2)
                cv.text('大楼和土地卖给家具城', W / 2, 1240, 34, 'sans_bold', col=CREAM, a=a * k2 * kb)
            else:
                store_box(cv, 780, 1080, 0.85, a * k * kb, "MRS. B'S", col=RED_X)
            k3 = appear(t, 'c4f', '接着卖地毯')
            if k3 > 0: chip(cv, 'B 太太留在原地，继续卖地毯', W / 2, 1320, 30, a * k3 * kb, col=CREAM)
        k4 = appear(t, 'c4f', '主动签了')
        if k4 > 0: cv.text('主动签下竞业禁止协议', W / 2, 1020, 50, 'serif_black', gold=True, a=a * k4)
        k5 = appear(t, 'c4f', '九十九岁')
        if k5 > 0:
            cv.text('99', W / 2 - 40, 1190, 150, 'oswald', col=GOLD_L, a=a * k5, glow=0.2)
            cv.text('岁', W / 2 + 90, 1220, 50, 'sans_bold', col=CREAM, a=a * k5)
        source(cv, '伯克希尔 1992 年信（“sell her building and land to NFM … graciously offered to sign a non-compete agreement … Signing a non-compete at 99”）', a, y=1462)
    # c4g：合伙人更好
    t0, t1 = S('c4g') - 0.2, S('c4h') - 0.2
    a = A(t, t0, t1)
    if a > 0:
        photo_win(cv, first_have(['c_buffett_2010', 'buffett_2010']), t, t0, t1, cy=WCY, h=WH, a=a, cap='沃伦·巴菲特（2010 年）')
        qcard(cv, 'qpartner', t, t0 + 0.3, t1, cy=1110, en=32, cn=40, a=a, typing=2.0, w=960)
    # c4h：干到 103 岁，104 岁去世
    t0, t1 = S('c4h') - 0.45, CHE('ch4')
    a = A(t, t0, t1)
    if a > 0:
        xa, xb, y = 110, 970, 1000
        ev = [(1893, '出生'), (1937, '$500 开店'), (1983, '卖给伯克希尔'), (1989, '出走'), (1992, '回归'), (1997, '103 岁退休'), (1998, '104 岁去世')]
        XS = [130, 270, 410, 545, 680, 815, 950]                       # 非等比时间轴
        k = eexp((t - t0 - 0.2) / 2.2)
        cv.line((xa, y), (xa + (xb - xa) * k, y), GOLD_D, a, 3)
        if k > 0.9: cv.text('时间轴非等比', xb, y + 150, 18, 'sans_light', col=GREY, a=a, anchor='r')
        for j, (yr, lb) in enumerate(ev):
            x = XS[j]
            kk = cl((k * (xb - xa) - (x - xa)) / 40 + 1) if x > xa else min(1, k * 5)
            if kk <= 0: continue
            hi = yr >= 1997
            cv.glow_dot((x, y), 9 if not hi else 13, GOLD_L if hi else GOLD, a * kk)
            up = j % 2 == 0
            cv.text(str(yr), x, y + (-46 if up else 50), 26, 'oswald', col=GOLD_L if hi else CREAM, a=a * kk)
            cv.text(lb, x, y + (-86 if up else 90), 24, 'sans_med', col=GOLD_L if hi else CREAM, a=a * kk)
        k2 = appear(t, 'c4h', '一百零三')
        if k2 > 0: cv.text('一直干到 103 岁', W / 2, 600, 70, 'serif_black', gold=True, a=a * k2, glow=0.2)
        k3 = appear(t, 'c4h', '一百零四')
        if k3 > 0: cv.text('享年 104 岁', W / 2, 720, 50, 'serif_semi', col=CREAM, a=a * k3)
        source(cv, '伯克希尔 2011 年信（“worked until she was 103. (After retiring, she died the next year …)”）；维基百科 Rose Blumkin（1893-12-03 — 1998-08-09）', a, y=1462)


# ======================================================================== 第五章：越开越大
def shot_ch5(cv, t):
    # c5z：1994 年股东会，第一个点到的经理人（引出原声）
    t0, t1 = S('c5z') - 0.3, S('c5z') + SEG['c5z']['dur'] + 0.9
    a = A(t, t0, t1, 0.4, 0.3)
    if a > 0:
        nm = first_have(['c_brk2015', 'c_kiewit'])
        if nm: photo_win(cv, nm, t, t0, t1, cy=WCY, h=WH, a=a, cap='伯克希尔股东会（2015 年）' if nm == 'c_brk2015' else '伯克希尔总部所在的基威特广场（奥马哈）')
        k = appear(t, 'c5z', '一九九四')
        if k > 0: cv.text('1994', W / 2, 980, 110, 'oswald', col=GOLD_L, a=a * k, glow=0.15)
        k2 = appear(t, 'c5z', '股东会')
        if k2 > 0: chip(cv, '伯克希尔股东会 · 介绍旗下经理人', W / 2, 1110, 32, a * k2, col=CREAM)
        k3 = appear(t, 'c5z', '第一个点到')
        if k3 > 0: cv.text('第一个点名：NFM', W / 2, 1240, 54, 'serif_black', gold=True, a=a * k3, glow=0.12)
        source(cv, '1994 年伯克希尔股东会录像（archive.org 转载件，片中 8:30）', a, y=1462)
    # c5a：孙子罗恩和欧文
    t0, t1 = win2('c5a')
    a = A(t, t0, t1)
    if a > 0:
        rows = [(380, [('B 太太', '1893–1998')]), (620, [('路易', '儿子')]), (860, [('罗恩', '孙子'), ('欧文', '孙子')]), (1100, [('第四代', '已进公司')])]
        for j, (y, ppl) in enumerate(rows):
            k = eo((t - t0 - 0.2 - j * 0.35) / 0.5) if j < 2 else appear(t, 'c5a', '罗恩') if j == 2 else appear(t, 'c5a', '带出了')
            for m, (nm, sub) in enumerate(ppl):
                x = W / 2 + (m - (len(ppl) - 1) / 2) * 340
                node(cv, x, y, nm, a * k, col=GOLD if j == 2 else CREAM, size=40, w=260, sub=sub)
                if j > 0 and k > 0: cv.line((W / 2, y - 160), (x, y - 70), GOLD_D, a * k * 0.7, 2)
        k = appear(t, 'c5a', '带出了')
        if k > 0: cv.text('把这套打法带出奥马哈', W / 2, 1290, 46, 'serif_black', gold=True, a=a * k)
        source(cv, '伯克希尔 2011 年信（“Louie’s sons, Ron and Irv, have taken the company to new heights … several members of the fourth Blumkin generation have joined NFM”）', a, y=1462)
    # c5b：堪萨斯城
    t0, t1 = win2('c5b')
    a = A(t, t0, t1)
    if a > 0:
        if M.have('c_nfm_kc'):
            photo_win(cv, 'c_nfm_kc', t, t0, t1, cy=WCY, h=WH, a=a, cap='NFM 堪萨斯城店与停车场（2021 年航拍）', focus=(0.5, 0.55), z0=1.0, z1=1.12)
        else:
            photo_win(cv, 'loc_ks_speedway', t, t0, t1, cy=WCY, h=WH, a=a, cap='堪萨斯城西郊的堪萨斯赛车场，NFM 堪萨斯城店就在它对面（2021）')
        mx, my, sc = 520, 1130, 70
        usmap(cv, mx, my, sc, a * 0.9, lat0=40.2, lon0=-95.4, box=(60, 880, 1020, 1400))
        city(cv, '奥马哈', mx, my, sc, a, 1.0, lat0=40.2, lon0=-95.4, anchor='r')
        k = appear(t, 'c5b', '堪萨斯城')
        po = map_xy(*CITY['奥马哈'], mx, my, sc, 40.2, -95.4); pk = map_xy(*CITY['堪萨斯城'], mx, my, sc, 40.2, -95.4)
        link(cv, po, pk, a, k, GOLD)
        city(cv, '堪萨斯城', mx, my, sc, a, k, lat0=40.2, lon0=-95.4, sub='2003 年开业')
        k2 = appear(t, 'c5b', '二十五英亩')
        if k2 > 0: chip(cv, '25 英亩停车场，有时都停不下', 300, 1340, 28, a * k2, col=CREAM)
        k3 = appear(t, 'c5b', '全美销量最大')
        if k3 > 0: chip(cv, '全美销量最大的家居店', 780, 1340, 28, a * k3, col=GOLD)
        source(cv, '伯克希尔 2003 年信（“sparsely populated parts … more than 25 acres of parking, the lot has at times overflowed”；“the country’s largest-volume home-furnishings store”）', a, y=1462)
    # c5c：2011 年利润是 1983 年的十倍还多
    t0, t1 = win2('c5c')
    a = A(t, t0, t1)
    if a > 0:
        nm = first_have(['c_west_omaha', 'c_omaha_dt', 'c_omaha_sky'])
        if nm: photo_win(cv, nm, t, t0, t1, cy=WCY, h=WH, a=a, cap={'c_west_omaha': '奥马哈西区航拍', 'c_omaha_dt': '奥马哈市中心', 'c_omaha_sky': '奥马哈天际线'}[nm])
        else: seq(cv, t, t0, t1, ['tx_promo2', 'tx_promo1', 'op_ribbon'], cy=WCY, h=WH, a=a, cap='NFM 得州店（2015）')
        k2 = appear(t, 'c5c', '二零一一')
        if k2 > 0:
            cv.text('2011 年 · NFM 利润创纪录', W / 2, 950, 40, 'sans_bold', col=CREAM, a=a * k2)
            cv.text('1983 年的 10 倍还多', W / 2, 1070, 84, 'serif_black', gold=True, a=a * appear(t, 'c5c', '十倍'), glow=0.2)
            for j in range(10):
                kk = eo((t - WT('c5c', '十倍') - j * 0.06) / 0.3)
                if kk > 0: cv.rect(190 + j * 72, 1200, 250 + j * 72, 1260, GOLD * 0.75, a * kk, glow=0.05)
            cv.rect(190, 1290, 250, 1350, GOLD * 0.4, a * appear(t, 'c5c', '十倍'))
            cv.text('← 1983 年', 340, 1320, 24, 'sans_light', col=GREY, a=a * appear(t, 'c5c', '十倍'))
        source(cv, '伯克希尔 2011 年信（“NFM … netting more than ten times what it did in 1983”）', a, y=1462)
    # c5d：达拉斯，180 万平方英尺
    t0, t1 = win2('c5d')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['tx_render', 'tx_promo1', 'tx_promo2'], cy=WCY, h=WH, a=a, cap='NFM 得州店：效果图（2014）与开业后（2015）')
        k = appear(t, 'c5d', '又过了四年')
        if k > 0:
            cv.text('2015 · 达拉斯北郊 The Colony', W / 2, 920, 40, 'sans_bold', col=GOLD_L, a=a * k)
        k2 = appear(t, 'c5d', '一百八十万')
        if k2 > 0:
            cv.text(counter(0, 180, t, WT('c5d', '一百八十万'), 1.0, lambda v: f'{v:.0f} 万'), W / 2 - 60, 1070, 120, 'sans_bold', gold=True, a=a * k2, glow=0.2)
            cv.text('平方英尺', W / 2 + 200, 1090, 40, 'sans_med', col=CREAM, a=a * k2)
            cv.text('一个屋顶下：卖场 + 仓库 · 约合 23 个标准足球场', W / 2, 1190, 30, 'sans_med', col=CREAM, a=a * k2)
            for j in range(23):
                kk = eo((t - WT('c5d', '一百八十万') - 0.4 - j * 0.04) / 0.3)
                if kk > 0:
                    x = 150 + (j % 12) * 66; y = 1270 + (j // 12) * 52
                    cv.rrect(x, y, x + 56, y + 38, 3, C(70, 140, 80), a * kk * 0.8)
                    cv.line((x + 28, y), (x + 28, y + 38), CREAM, a * kk * 0.5, 1)
        source(cv, '伯克希尔 2013 年信（“under one roof … 1.8 million square feet of retail and supporting warehouse space”）；足球场按 105×68 米折算（本片换算）', a, y=1462)
    # c5e：三家最大；疫情下创纪录
    t0, t1 = win2('c5e')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['op_crowd', 'op_flags', 'op_ribbon'], cy=WCY, h=WH, a=a, cap='NFM 得州店开业典礼（2015-05-07）')
        k = appear(t, 'c5e', '全美最大的三家')
        for j, nm in enumerate(('奥马哈', '堪萨斯城', '达拉斯')):
            kk = eo((t - WT('c5e', '全美最大的三家') - j * 0.2) / 0.4)
            store_box(cv, 220 + j * 320, 1010, 0.85, a * kk, nm, col=GOLD)
        if k > 0: cv.text('全美最大的三家家居店，都是 NFM 的', W / 2, 1180, 38, 'sans_bold', col=GOLD_L, a=a * k)
        k2 = appear(t, 'c5e', '疫情')
        if k2 > 0: chip(cv, '2020：疫情关店 6 周多', 300, 1290, 30, a * k2, col=RED_X)
        k3 = appear(t, 'c5e', '销售纪录')
        if k3 > 0: chip(cv, '三家店都创销售纪录', 770, 1290, 30, a * k3, col=GOLD)
        source(cv, '伯克希尔 2020 年信（“NFM now owns the three largest home-furnishings stores in the U.S. Each set a sales record in 2020 … despite the closing of NFM’s stores for more than six weeks”）', a, y=1462)
    # c5f：股东会那一周
    t0, t1 = win2('c5f')
    a = A(t, t0, t1)
    if a > 0:
        if M.have('c_brk2015'): photo_win(cv, 'c_brk2015', t, t0, t1, cy=WCY, h=WH, a=a, cap='伯克希尔股东会（2015 年）')
        else: seq(cv, t, t0, t1, ['op_crowd'], cy=WCY, h=WH, a=a, cap='NFM 得州店（2015）')
        k = appear(t, 'c5f', '员工价')
        if k > 0: chip(cv, '股东会期间：股东享员工价', W / 2, 920, 32, a * k, col=CREAM)
        e1 = eexp((t - WT('c5f', '平时一周') + 0.1) / 0.9); e2 = eexp((t - WT('c5f', '四千五百') + 0.1) / 1.0)
        base = 1330
        if e2 > 0:
            gbar(cv, 640 - 100, base - 300 * e2, 640 + 100, base, GOLD, a, sheen_t=t, glow=0.2)
            cv.text('$4550 万', 640, base - 300 * e2 - 46, 54, 'sans_bold', gold=True, a=a * min(1, e2 * 2), glow=0.15)
            cv.text('2016 年股东会那一周', 640, base + 40, 26, 'sans_med', col=GOLD_L, a=a * min(1, e2 * 2))
        if e1 > 0:
            gbar(cv, 330 - 100, base - 300 * 900 / 4550 * e1, 330 + 100, base, BLUE_L * 0.55, a)
            cv.text('~$900 万', 330, base - 300 * 900 / 4550 * e1 - 40, 44, 'sans_bold', col=CREAM, a=a * min(1, e1 * 2))
            cv.text('平时一周', 330, base + 40, 26, 'sans_med', col=CREAM, a=a * min(1, e1 * 2))
        if e2 > 0: cv.text('奥马哈店', 900, 1100, 26, 'sans_light', col=GREY, a=a * e2)
        source(cv, '伯克希尔 2016 年信（“the Omaha store recording one-week volume of $45.5 million”）；2014、2015 年信（“An average week for NFM’s Omaha store is about $9 million”）', a, y=1462)


# ======================================================================== 第六章：要盯住的三件事
RISKS = [('大件消费，可买可不买', '2024 年家居零售收入 −6.4%'), ('便宜，必须一直便宜下去', '比价越来越容易，对手抄得越来越快'), ('靠人：一家人守在店里', '第四代已进公司，能传多少代？')]


def risk_list(cv, t, a, cur, ks):
    for j, (nm, sub) in enumerate(RISKS):
        k = ks[j]
        if k <= 0: continue
        y = 960 + j * 130; on = j == cur
        cv.rrect(90, y - 52, 990, y + 52, 14, (0.08, 0.07, 0.06) if on else (0.05, 0.05, 0.05), a * k * 0.9)
        cv.rrect(90, y - 52, 990, y + 52, 14, COST_R if on else GREY, a * k * (0.9 if on else 0.4), fill=False, th=2)
        cv.text(f'0{j + 1}', 145, y, 34, 'oswald', col=COST_R if on else GREY, a=a * k)
        cv.text(nm, 210, y - 16, 34, 'sans_bold', col=CREAM if on else GREY, a=a * k, anchor='l')
        cv.text(sub, 210, y + 26, 22, 'sans_light', col=CREAM if on else GREY, a=a * k, anchor='l')


def shot_ch6(cv, t):
    # c6z：好生意也有对手盯着（引出原声）
    t0, t1 = S('c6z') - 0.3, S('c6z') + SEG['c6z']['dur'] + 0.9
    a = A(t, t0, t1, 0.4, 0.3)
    if a > 0:
        seq(cv, t, t0, t1, ['cnbc_two2'], cy=WCY, h=WH, a=a, cap='CNBC 专访现场（2026-07-15）', focus=(0.72, 0.5))
        k = appear(t, 'c6z', '对手盯着')
        if k > 0: cv.text('再好的生意，也有对手盯着', W / 2, 1000, 56, 'serif_black', gold=True, a=a * k, glow=0.1)
        k2 = appear(t, 'c6z', '那次专访')
        if k2 > 0: chip(cv, 'CNBC 专访 · 2026 年 7 月 15 日', W / 2, 1130, 32, a * k2, col=CREAM)
        source(cv, 'CNBC Squawk Box：Becky Quick 专访巴菲特（2026-07-15）', a, y=1462)
    t0, t1 = S('c6a') - 0.45, S('c6f') + 0.1
    a = A(t, t0, t1)
    if a > 0:
        cur = 2 if t >= S('c6e') - 0.2 else 1 if t >= S('c6c') - 0.2 else 0 if t >= S('c6b') - 0.2 else -1
        ks = [appear(t, 'c6b', '第一'), appear(t, 'c6c', '第二'), appear(t, 'c6e', '第三')]
        if t < S('c6b') - 0.2:
            seq(cv, t, t0, S('c6b') - 0.2, ['op_flags'], cy=WCY, h=WH, a=a, cap='NFM 得州店开业典礼（2015-05-07）')
            big_q(cv, t, '这门生意，还能好多久？', 980, WT('c6a', '还能好多久'), 64, a)
            k = appear(t, 'c6a', '三件事')
            if k > 0: cv.text('至少有三件事，要盯住', W / 2, 1120, 46, 'sans_bold', col=GOLD_L, a=a * k)
        else:
            if cur == 0:
                seq(cv, t, S('c6b') - 0.45, S('c6c') + 0.1, ['al_living', 'al_chair'], cy=WCY, h=WH, a=a * (1 - appear(t, 'c6b', '二零二四')), cap='示意画面：家具（1958 年影片）')
                k = appear(t, 'c6b', '二零二四')
                if k > 0:
                    cv.text('2024 年', W / 2, 360, 40, 'sans_bold', col=CREAM, a=a * k)
                    if appear(t, 'c6b', '百分之六点四', lead=0.25) > 0: cv.text(counter(0, -6.4, t, WT('c6b', '百分之六点四'), 0.9, lambda v: f'{v:.1f}%'), W / 2, 500, 140, 'sans_bold', col=RED_X, a=a * k, glow=0.15)
                    cv.text('伯克希尔旗下家居零售收入', W / 2, 620, 32, 'sans_med', col=CREAM, a=a * k)
                    cv.text('卖得少了 · 价格竞争更激烈', W / 2, 700, 34, 'sans_bold', col=GOLD_L, a=a * appear(t, 'c6b', '百分之六点四'))
            elif cur == 1:
                if t < WT('c6c', '如今点几下') - 0.2:
                    qcard(cv, 'qcoast', t, WT('c6c', '巴菲特写过') - 0.1, WT('c6c', '如今点几下') - 0.2, cy=520, en=34, cn=42, a=a, typing=1.0, w=900)
                else:
                    # 手机比价（示意）
                    k = eo((t - WT('c6c', '如今点几下') + 0.1) / 0.5)
                    px, py = W / 2, 540
                    cv.rrect(px - 150, py - 260, px + 150, py + 260, 30, (0.06, 0.06, 0.07), a * k)
                    cv.rrect(px - 150, py - 260, px + 150, py + 260, 30, GREY, a * k, fill=False, th=3)
                    for j, (nm, pr) in enumerate((('A 店', '$899'), ('B 店', '$849'), ('C 店', '$829'), ('D 店', '$799'))):
                        kk = eo((t - WT('c6c', '如今点几下') - 0.3 - j * 0.25) / 0.3)
                        y = py - 170 + j * 110
                        cv.rrect(px - 120, y - 40, px + 120, y + 40, 10, (0.12, 0.12, 0.13), a * kk)
                        cv.text(nm, px - 95, y, 28, 'sans_med', col=CREAM, a=a * kk, anchor='l')
                        cv.text(pr, px + 95, y, 30, 'sans_bold', col=GOLD_L if j == 3 else CREAM, a=a * kk, anchor='r')
                    cv.text('示意', px + 190, py + 240, 20, 'sans_light', col=GREY, a=a * k)
            elif cur == 2:
                for j in range(4):
                    kk = eo((t - S('c6e') - 0.2 - j * 0.3) / 0.4)
                    x = 240 + j * 200
                    person(cv, x, 560, 2.2 - j * 0.1, a * kk, GOLD_L if j < 3 else CREAM)
                    cv.text(['第一代', '第二代', '第三代', '第四代'][j], x, 640, 28, 'sans_med', col=CREAM, a=a * kk)
                k = appear(t, 'c6e', '还能传')
                if k > 0: cv.text('?', 1000 - 40, 520, 120, 'serif_black', col=RED_X, a=a * k)
                if appear(t, 'c6e', '天天守在') > 0: cv.text('一家人天天守在店里', W / 2, 360, 40, 'sans_bold', col=GOLD_L, a=a * appear(t, 'c6e', '天天守在'))
            risk_list(cv, t, a, cur, ks)
        src = {0: '伯克希尔 2025 年 10-K（“Revenues of the home furnishings businesses declined 6.4% in 2024 … lower sales volumes and increased price competition”）',
               1: '伯克希尔 1995 年信（“Retailing is a tough business … In retailing, to coast is to fail.”）；比价为本片解读',
               2: '伯克希尔 1989 年信（家族成员始终在场）；2011 年信（第四代已加入 NFM）'}.get(cur, '本片过渡')
        source(cv, src, a, y=1462)
    # c6f：不单独披露；2025 年年报：除了 NFM
    t0, t1 = S('c6f') - 0.45, CHE('ch6')
    a = A(t, t0, t1)
    if a > 0:
        nm = first_have(['c_brk2015', 'c_kiewit'])
        if nm: photo_win(cv, nm, t, t0, t1, cy=WCY, h=WH, a=a, cap='伯克希尔股东会（2015 年）')
        k = appear(t, 'c6f', '不单独公布')
        if k > 0:
            cv.text('NFM 的营收、利润：不单独公布', W / 2, 920, 46, 'serif_black', col=CREAM, a=a * k)
        doc_page(cv, t, WT('c6f', '只说了一句') - 0.2, t1, 'BERKSHIRE HATHAWAY · 2025 FORM 10-K',
                 ['With the exception of NFM, our retailing', 'businesses generated flat or lower earnings', 'in 2025 compared to the prior year.'],
                 cy=1145, w=900, size=32, hl='With the exception of NFM', hl_t=WT('c6f', '除了') - 0.1, a=a)
        k2 = appear(t, 'c6f', '除了')
        if k2 > 0: cv.text('零售板块里，除了 NFM，其他公司利润都持平或下降', W / 2, 1330, 32, 'sans_bold', col=GOLD_L, a=a * k2)
        source(cv, '伯克希尔 2025 年 10-K（MD&A，零售板块）', a, y=1462)

# ======================================================================== 第七章：家里还有吗
CHAIN = [('NFM', '奥马哈 · 1983', '奥马哈', None), ('R.C. Willey', '犹他 · 1995', '盐湖城', 'c7c'), ('Star Furniture', '休斯敦 · 1997', '休斯敦', 'c7d'),
         ("Jordan’s", '新英格兰 · 1999', '波士顿', 'c7d')]


LESSONS = [('好生意', '低价不是护城河，学不来的低成本才是', '费用率 16.5% 对 35.6%，六年后 15% 对约 40%：靠规模、一家人、甘愿少赚'),
           ('好价钱', '好价钱，不靠捡便宜', '约 4 倍税前利润，买下一门还在长大的好生意'),
           ('对的人', '看人比看报表更要紧', '可该写进合同的，一条也不能少（竞业禁止）')]


def lesson_list(cv, t, a, ks, cur):
    for j, (tag_, head, sub) in enumerate(LESSONS):
        k = ks[j]
        if k <= 0: continue
        y = 1010 + j * 136 + 24 * (1 - k); on = j == cur
        cv.rrect(80, y - 58, 1000, y + 58, 16, (0.08, 0.065, 0.045) if on else (0.05, 0.045, 0.04), a * k * 0.92)
        cv.rrect(80, y - 58, 1000, y + 58, 16, GOLD if on else GOLD_D, a * k * (0.95 if on else 0.45), fill=False, th=2, glow=0.15 if on else 0)
        cv.text(f'0{j + 1}', 140, y, 44, 'oswald', col=GOLD_L if on else GOLD_D, a=a * k)
        chip(cv, tag_, 250, y - 22, 24, a * k, col=GOLD if on else GOLD_D)
        cv.text(head, 320, y - 22, 36, 'serif_black', col=CREAM if on else GREY, a=a * k, anchor='l')
        cv.text(sub, 200, y + 28, 23, 'sans_med', col=CREAM if on else GREY, a=a * k, anchor='l')


def shot_ch7(cv, t):
    # c7b：最大的回报也许不在 NFM 本身——家里还有像你们这样的吗？
    t0, t1 = S('c7b') - 0.45, S('c7c') + 0.1
    a = A(t, t0, t1)
    if a > 0:
        if M.have('c_buffett_ku'): photo_win(cv, 'c_buffett_ku', t, t0, t1, cy=WCY, h=WH, a=a, cap='沃伦·巴菲特（2005 年）')
        else: seq(cv, t, t0, t1, ['tx_promo1', 'op_crowd'], cy=WCY, h=WH, a=a, cap='NFM 得州店（2015）')
        k = appear(t, 'c7b', '也许') * (1 - appear(t, 'c7b', '家里还有', d=0.3, lead=0.4))
        if k > 0: cv.text('最大的回报，也许不在 NFM 本身', W / 2, 1000, 48, 'serif_black', gold=True, a=a * k)
        qcard(cv, 'qmore', t, WT('c7b', '家里还有') - 0.3, t1, cy=1060, en=42, cn=50, a=a, typing=0.9, w=900)
        source(cv, '伯克希尔 1997 年信（“I always ask our new partners, ‘Are there any more at home like you?’”）', a, y=1462)
    # c7c–c7e：一家牵出一家 → 33 亿
    t0, t1 = S('c7c') - 0.45, S('c7l') + 0.1
    a = A(t, t0, t1)
    if a > 0:
        t95, t97, t99 = WT('c7c', '一九九五年的'), WT('c7c', '一九九七年的'), WT('c7c', '一九九九年的')
        if t < t97: photo_win(cv, 'loc_slc', t, t0, t97 + 0.3, cy=WCY, h=WH, a=a, cap='犹他州盐湖城：R.C. Willey 的大本营（Carol M. Highsmith 摄，2022）')
        elif t < t99: photo_win(cv, 'loc_houston', t, t97 - 0.3, t99 + 0.3, cy=WCY, h=WH, a=a, cap='休斯敦：Star Furniture 的大本营（Carol M. Highsmith 摄，2014）')
        elif t < S('c7e') - 0.1: photo_win(cv, 'loc_boston_sky', t, t99 - 0.3, S('c7e') + 0.2, cy=WCY, h=WH, a=a, cap='波士顿：Jordan’s 所在的新英格兰（Carol M. Highsmith 摄，2019）')
        else:
            mx, my, sc = 540, 540, 15.5
            km = eo((t - S('c7e') + 0.2) / 0.5)
            usmap(cv, mx, my, sc, a * km, lat0=37.5, lon0=-96.5, box=(40, 280, 1040, 810))
            for nm, sub, cty, _ in CHAIN:
                city(cv, cty, mx, my, sc, a, km, lat0=37.5, lon0=-96.5, sub=nm, size=24, anchor='r' if cty in ('盐湖城',) else 'l')
        ys = [910, 1030, 1150, 1270]
        tws = [S('c7c') - 0.1, t95, t97, t99]
        kf = 1 - appear(t, 'c7e', '三十三亿', d=0.35, lead=0.3)
        for j, ((nm, sub, cty, _), y, tw) in enumerate(zip(CHAIN, ys, tws)):
            k = eo((t - tw + 0.1) / 0.45) * kf
            if k <= 0: continue
            x = 240 if j == 0 else 620
            if j == 0: node(cv, x, ys[0] + 180, nm, a * k, col=GOLD, size=40, w=300, sub=sub)
            else:
                node(cv, x + 120, y, nm, a * k, col=CREAM, size=32, w=420, sub=sub)
                arrow(cv, (395, ys[0] + 180), (x + 120 - 215, y), a * k, GOLD_D, th=2, k=k)
        k3 = appear(t, 'c7c', '一家牵出一家')
        if k3 > 0: chip(cv, '一家牵出一家', 240, 1350, 28, a * k3 * kf, col=GOLD)
        k4 = appear(t, 'c7e', '三十三亿')
        if k4 > 0:
            cv.text(counter(0, 33, t, WT('c7e', '三十三亿'), 1.0, lambda v: f'约 ${v:.0f} 亿'), W / 2, 1040, 130, 'sans_bold', gold=True, a=a * k4, glow=0.25)
            cv.text('四家家具零售商 · 2025 年合计营收（业界媒体估算）', W / 2, 1160, 30, 'sans_med', col=CREAM, a=a * k4)
        srcs = '伯克希尔 1995 年信（R.C. Willey，“It was Nebraska Furniture Mart’s Irv Blumkin who did the walking around”）；1997 年信（Star）；1999 年信（Jordan’s）'
        if t >= S('c7e') - 0.2: srcs = 'Home News Now 2026-06-22（伯克希尔家居零售板块 2025 年营收约 $3.34B，业界媒体估算）'
        source(cv, srcs, a, y=1462)
    # c7l–c7o：带走三件事
    t0, t1 = S('c7l') - 0.45, S('c7f') + 0.1
    a = A(t, t0, t1)
    if a > 0:
        tm, tn, to = S('c7m'), S('c7n'), S('c7o')
        if t < tn - 0.1: seq(cv, t, t0, tn + 0.3, ['tx_promo2', 'tx_promo1', 'op_flags'], cy=WCY, h=WH, a=a, cap='NFM 得州店（2015）')
        elif t < to - 0.1: photo_win(cv, first_have(['c_munger', 'buffett_2010']), t, tn - 0.3, to + 0.3, cy=WCY, h=WH, a=a, cap='查理·芒格（2010 年）')
        else: docview(cv, 'doc_proposal1', t, to - 0.3, t1, [(to - 0.3, 0.5, 0.45, 0.95), (t1, 0.5, 0.62, 0.8)], a=a, cap='1983 年提议书：没有竞业禁止条款')
        k0 = appear(t, 'c7l', '三件事')
        if k0 > 0: cv.text('回头看这笔交易 · 带走三件事', W / 2, 900, 40, 'serif_black', gold=True, a=a * k0)
        ks = [appear(t, 'c7m', '第一'), appear(t, 'c7n', '第二'), appear(t, 'c7o', '第三')]
        cur = 2 if t >= to - 0.2 else 1 if t >= tn - 0.2 else 0
        lesson_list(cv, t, a, ks, cur)
        source(cv, {0: '本片解读（1984 年信：营业费用率 16.5% 对 35.6%；1990 年信：130 英里外的顾客）',
                    1: '本片解读（1984–1990 年信利润表；1989 年信“a wonderful company at a fair price”）',
                    2: '本片解读（1984 年信：没有审计；1992 年信：竞业禁止上“incautious”）'}[cur], a, y=1462)
    # c7f：两句话
    t0, t1 = win2('c7f')
    a = A(t, t0, t1)
    if a > 0:
        seq(cv, t, t0, t1, ['tx_promo2', 'op_crowd'], cy=WCY, h=WH, a=a, cap='NFM 得州店（2015）')
        k = appear(t, 'c7f', '卖得便宜')
        if k > 0:
            cv.text('卖得便宜', 290, 950, 56, 'serif_black', gold=True, a=a * k)
            cv.text('顾客从 130 英里外开车来', 290, 1030, 28, 'sans_med', col=CREAM, a=a * k)
            cv.text('→ 靠学不来的低成本', 290, 1080, 28, 'sans_bold', col=GOLD_L, a=a * appear(t, 'c7f', '学不来'))
        k2 = appear(t, 'c7f', '说真话')
        if k2 > 0:
            cv.text('说真话', 790, 950, 56, 'serif_black', gold=True, a=a * k2)
            cv.text('不审计，就开出支票', 790, 1030, 28, 'sans_med', col=CREAM, a=a * k2)
            cv.text('→ 那笔交易的底气', 790, 1080, 28, 'sans_bold', col=GOLD_L, a=a * k2)
        k3 = appear(t, 'c7f', '说真话，是')
        if k3 > 0: cv.line((W / 2, 900), (W / 2, 1110), GOLD_D, a * k3 * 0.6, 2)
        source(cv, '本片解读（1990 年信：130 英里外的顾客；1984 年信：没有审计）', a * 0.7, y=1462)
    # c7g：落版字
    t0, t1 = S('c7g') - 0.3, CH['end'][0] + 0.4
    a = A(t, t0, t1, 0.4, 0.6)
    if a > 0:
        docview(cv, 'doc_proposal2', t, t0, t1, [(t0, 0.36, 0.56, 0.75), (t1, 0.40, 0.62, 0.65)], a=a * 0.8, cap='1983 年提议书签字页')
        check_art(cv, W / 2, 1010, 0.8, a * eo((t - t0) / 0.6), rot=-0.03)
        k2 = appear(t, 'c7g', '一张支票')
        if k2 > 0 and t < CH['end'][0]:      # 落版字在片尾开始时交给 common.shot_end（同一位置），随后化作粒子
            cv.text(END_L, W / 2, END_Y, END_SZ, 'serif_black', gold=True, a=k2, glow=0.15)
        k3 = appear(t, 'c7g', '那句话')
        if k3 > 0 and t < CH['end'][0] + 0.3:
            cv.text('四十多年来，一直算数', W / 2, 1360, 34, 'serif_semi', col=CREAM, a=a * k3)
