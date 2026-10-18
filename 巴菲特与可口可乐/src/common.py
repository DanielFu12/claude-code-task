"""分镜公用部分：数据、资源、通用构件（照片、原文卡、字幕、章节卡、背景）、开场、标题与片尾。
所有镜头的起止都挂在旁白句子（work/timeline.json）上，改稿后自动对齐。
"""
import sys, os, json, math, subprocess, datetime as dt
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import *          # noqa
import shaders
from script import QUOTES, CHAPTERS, LINES, TEASE

WORK = sys.argv[1] if len(sys.argv) > 1 else 'work'
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
TL = json.load(open(os.path.join(WORK, 'timeline.json')))
MP = json.load(open(os.path.join(WORK, 'music_plan.json')))
FEATS = json.load(open(os.path.join(WORK, 'audio_feats.json')))
CALC = json.load(open(os.path.join(ROOT, 'data', 'calc.json')))
SEG = {s['id']: s for s in TL['segs']}
CH = TL['chapters']
TOTAL = TL['total']
NFRAMES = int(round(TOTAL * FPS))
BEATS = np.array(FEATS['beats'])
ENERGY = np.array(FEATS['energy'])


def S(i): return SEG[i]['start']
def E(i): return SEG[i]['start'] + SEG[i]['dur']


_SAY = {l[0]: (l[3] or l[2]) for l in LINES}; _SAY['tease'] = TEASE[1]
_TXT = {l[0]: l[2] for l in LINES}; _TXT['tease'] = TEASE[0]


def WT(i, sub):
    """句内某个词大约被读出的时刻（按朗读文本的字数比例估算）"""
    for src in (_SAY[i], _TXT[i]):
        k = src.find(sub)
        if k >= 0: return S(i) + SEG[i]['dur'] * k / max(len(src), 1)
    raise KeyError(f'{sub} not in {i}')


def energy(t):
    k = int(t * FPS); return float(ENERGY[min(max(k, 0), len(ENERGY) - 1)])


def beat_pulse(t, decay=7.0):
    """最近一个节拍后的衰减脉冲 0..1"""
    i = np.searchsorted(BEATS, t) - 1
    if i < 0: return 0.0
    return math.exp(-(t - BEATS[i]) * decay)


# ------------------------------------------------------------------ 数据
def load_ko():
    d = json.load(open(os.path.join(ROOT, 'data', 'ko_daily.json')))['chart']['result'][0]
    q = d['indicators']['quote'][0]; adj = d['indicators']['adjclose'][0]['adjclose']
    rows = [(dt.datetime.fromtimestamp(ts, dt.UTC).date(), c, a) for ts, c, a in zip(d['timestamp'], q['close'], adj) if c]
    return rows


def load_sp():
    d = json.load(open(os.path.join(ROOT, 'data', 'sp500tr_daily.json')))['chart']['result'][0]
    c = d['indicators']['quote'][0]['close']
    return [(dt.datetime.fromtimestamp(ts, dt.UTC).date(), v) for ts, v in zip(d['timestamp'], c) if v]


def yearf(d): return d.year + (d.timetuple().tm_yday - 0.5) / 366


KO = load_ko()
KO_Y = np.array([yearf(r[0]) for r in KO]); KO_P = np.array([r[1] for r in KO]); KO_A = np.array([r[2] for r in KO])
m88 = KO_Y >= 1988.0
KO_Y, KO_P, KO_A = KO_Y[m88], KO_P[m88], KO_A[m88]
SP = load_sp()
SP_Y = np.array([yearf(r[0]) for r in SP]); SP_V = np.array([r[1] for r in SP])
PEAK98 = 1998 + (dt.date(1998, 7, 14).timetuple().tm_yday - 0.5) / 366


# ------------------------------------------------------------------ 资源
_cache = {}
def asset(name):
    if name not in _cache:
        p = os.path.join(ROOT, 'assets', 'archive', name + '.jpg')
        im = cv2.imread(p)[..., ::-1].astype(np.float32) / 255
        _cache[name] = im
    return _cache[name]


CREDITS = json.load(open(os.path.join(ROOT, 'assets', 'archive', 'credits.json'))) \
    if os.path.exists(os.path.join(ROOT, 'assets', 'archive', 'credits.json')) else {}

_sh = {}
def sh(name):
    if name not in _sh:
        _sh[name] = Shader(getattr(shaders, name))
    return _sh[name]


def logo(px):
    k = ('logo', px)
    if k not in _cache: _cache[k] = load_logo(px)
    return _cache[k]


# ------------------------------------------------------------------ 通用构件
def fmt_yi(v_usd, dec=0):
    """美元 → “376亿” 格式"""
    y = v_usd / 1e8
    return f'{y:,.{dec}f}亿'


def tone(img, mode='sepia', k=1.0):
    g = img @ np.array([0.3, 0.59, 0.11], np.float32)
    if mode == 'bw': out = np.repeat(g[..., None], 3, 2)
    else: out = g[..., None] * np.array([1.08, 0.93, 0.74], np.float32)[None, None]
    out = np.clip((out - 0.04) * 1.1, 0, 1)
    return img * (1 - k) + out * k


def photo(cv, name, t, t0, t1, cx, cy, w, h, z0=1.05, z1=1.18, pan=(0, 0, 0, 0), mode='sepia', caption=None,
          a=1.0, fi=0.6, fo=0.6, frame=True, focus=None):
    """Ken Burns 历史照片：裁切到 w×h，缓慢推近；带细框、暗角与说明文字"""
    al = env(t, t0, t1, fi, fo) * a
    if al <= 0.004: return
    im = asset(name)
    ih, iw = im.shape[:2]
    p = eio((t - t0) / max(t1 - t0, 1e-3))
    z = lerp(z0, z1, p)
    # 以填满 w×h 为基准再放大 z
    s = max(w / iw, h / ih) * z
    cw, chh = w / s, h / s
    fx, fy = focus if focus else (0.5, 0.5)
    ox = fx * iw - cw / 2 + lerp(pan[0], pan[2], p) * iw
    oy = fy * ih - chh / 2 + lerp(pan[1], pan[3], p) * ih
    ox = cl(ox, 0, iw - cw); oy = cl(oy, 0, ih - chh)
    M = np.array([[s, 0, -ox * s], [0, s, -oy * s]], np.float32)
    crop = cv2.warpAffine(im, M, (int(w), int(h)), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if mode: crop = tone(crop, mode)
    yy, xx = np.mgrid[0:int(h), 0:int(w)].astype(np.float32)
    v = 1 - 0.45 * (((xx - w / 2) / (w * 0.7)) ** 2 + ((yy - h / 2) / (h * 0.7)) ** 2)
    crop *= v[..., None].clip(0.3, 1)
    x0, y0 = cx - w / 2, cy - h / 2
    cv.over(crop, np.full((int(h), int(w)), al, np.float32), x0, y0)
    if frame:
        cv.rrect(x0 - 1, y0 - 1, x0 + w + 1, y0 + h + 1, 3, GOLD_D, al * 0.55, fill=False, th=2)
    if caption:
        cv.text(caption, cx, y0 + h + 30, 22, 'sans_light', col=GREY, a=al * 0.9)


def chip(cv, s, x, y, size=30, a=1.0, col=GOLD, fill=(0.08, 0.06, 0.05), fnt='sans_med', anchor='m'):
    if a <= 0.004: return
    tw, th = text_size(s, fnt, size)
    pad = size * 0.6
    if anchor == 'l': x = x + tw / 2 + pad
    cv.rrect(x - tw / 2 - pad, y - size * 0.85, x + tw / 2 + pad, y + size * 0.85, size * 0.85, fill, a * 0.85)
    cv.rrect(x - tw / 2 - pad, y - size * 0.85, x + tw / 2 + pad, y + size * 0.85, size * 0.85, col, a * 0.6, fill=False, th=2)
    cv.text(s, x, y, size, fnt, col=col, a=a)


def source(cv, s, a=1.0, y=1392):
    if a <= 0.004: return
    lines = split_balanced(s, 'sans_light', 24, 980)
    for i, l in enumerate(lines):
        cv.text(l, W / 2, y + (i - (len(lines) - 1) / 2) * 32, 24, 'sans_light', col=(0.55, 0.53, 0.52), a=a * 0.95)


def wrap(s, fnt, size, maxw):
    words = s.split(' '); lines = []; cur = ''
    for w_ in words:
        nxt = (cur + ' ' + w_).strip()
        if text_size(nxt, fnt, size)[0] > maxw and cur: lines.append(cur); cur = w_
        else: cur = nxt
    if cur: lines.append(cur)
    return lines


def wrap_cn(s, fnt, size, maxw):
    lines, cur = [], ''
    for ch in s:
        if text_size(cur + ch, fnt, size)[0] > maxw and cur:
            if ch in '，。、：；！？”）》': cur += ch; lines.append(cur); cur = ''; continue
            lines.append(cur); cur = ch
        else: cur += ch
    if cur: lines.append(cur)
    # 避免最后一行只剩一两个字
    if len(lines) >= 2 and len(lines[-1]) <= 3:
        k = max(2, (len(lines[-2]) + len(lines[-1])) // 2 - len(lines[-1]))
        lines[-1] = lines[-2][-k:] + lines[-1]; lines[-2] = lines[-2][:-k]
    return lines


def clear_glow(cv, x0, y0, x1, y1, a=1.0):
    """在文字区域压掉高光与辉光，保证文字不被光斑吞掉"""
    X0, Y0, X1, Y1 = int(max(x0, 0)), int(max(y0, 0)), int(min(x1, W)), int(min(y1, H))
    if X1 <= X0 or Y1 <= Y0 or a <= 0.004: return
    reg = cv.img[Y0:Y1, X0:X1]
    np.minimum(reg, 1.0 - 0.35 * a, out=reg)
    cv.glow[Y0:Y1, X0:X1] *= (1 - a)
    cv.U[Y0:Y1, X0:X1] = (cv.U[Y0:Y1, X0:X1] * (1 - a)).astype(np.uint8)


def quote_card(cv, key, t, t0, t1, cy=860, en_size=36, cn_size=42, hl=None, a=1.0, typing=1.6, w=900):
    """大师原文卡：英文原句（打字机字体，逐字显现）+ 中文翻译 + 出处"""
    al = env(t, t0, t1, 0.5, 0.5) * a
    if al <= 0.004: return
    en, cn, who = QUOTES[key]
    en_lines = wrap('“' + en + '”', 'typewriter', en_size, w - 90)
    cn_lines = wrap_nice(cn, 'serif_semi', cn_size, w - 110)
    lh_en, lh_cn = en_size * 1.42, cn_size * 1.5
    hgt = len(en_lines) * lh_en + len(cn_lines) * lh_cn + 190
    x0, x1 = W / 2 - w / 2, W / 2 + w / 2
    y0 = cy - hgt / 2
    lift = (1 - eo((t - t0) / 0.7)) * 30
    y0 += lift
    # 文字层压在一切光斑之上：先把卡片区域的高光压回 ≤1 并去掉辉光，再铺不透明度 0.94 的暗底
    X0, Y0, X1, Y1 = int(max(x0 - 12, 0)), int(max(y0 - 12, 0)), int(min(x1 + 12, W)), int(min(y0 + hgt + 12, H))
    reg = cv.img[Y0:Y1, X0:X1]
    np.minimum(reg, 1.0, out=reg)
    cv.glow[Y0:Y1, X0:X1] *= (1 - al)
    cv.U[Y0:Y1, X0:X1] = (cv.U[Y0:Y1, X0:X1] * (1 - al)).astype(np.uint8)
    cv.rrect(x0, y0, x1, y0 + hgt, 18, (0.03, 0.026, 0.024), al * 0.94)
    cv.rrect(x0, y0, x1, y0 + hgt, 18, GOLD_D, al * 0.45, fill=False, th=2)
    cv.line((x0 + 50, y0 + 64), (x0 + 50 + 70 * eo((t - t0) / 0.8), y0 + 64), GOLD, al, 3)
    cv.text(who.upper() if False else who, x0 + 140, y0 + 64, 24, 'corm', col=GOLD, a=al, anchor='l')
    total = sum(len(l) for l in en_lines)
    shown = (t - t0 - 0.3) / typing * total
    y = y0 + 130
    cnt = 0
    for l in en_lines:
        r = cl((shown - cnt) / max(len(l), 1)); cnt += len(l)
        if r > 0:
            cv.text(l, x0 + 50, y, en_size, 'typewriter', col=CREAM, a=al * 0.97, anchor='l', reveal=r, shadow=0.6)
            if hl and hl in l and r >= 1:
                pass
        y += lh_en
    y += 24
    ca = al * eo((t - t0 - 0.3 - typing * 0.6) / 0.8)
    for l in cn_lines:
        cv.text(l, x0 + 50, y, cn_size, 'serif_semi', col=GOLD_L, a=ca, anchor='l', shadow=0.6)
        y += lh_cn


def counter(v0, v1, t, t0, dur, fmt):
    """数字滚动：指数缓出，最后 15% 的时间直接落在终值上（不会停在 375 这类差一位的数）"""
    x = (t - t0) / dur
    p = 1.0 if x >= 0.85 else eexp(x)
    return fmt(lerp(v0, v1, p))


# ------------------------------------------------------------------ 字幕与章节
def glued(x, y):
    """数字、小数点、百分号、英文单词及“数字+单位”不能从中间断开"""
    num = '0123456789.$%,'
    if (x in num or x.isascii() and x.isalnum()) and (y in num or y.isascii() and y.isalnum()): return True
    return x.isdigit() and y in '亿万年倍份股元美个次' or x in '亿万' and y == '美'


def wrap_nice(txt, fnt, size, maxw):
    """引言卡中文断行：两行放得下时在标点处断成相对均衡的两行；否则逐行尽量放满。都不拆数字/英文单词"""
    if text_size(txt, fnt, size)[0] <= maxw: return [txt]
    best, bs = None, 1e9
    for i in range(2, len(txt) - 1):
        a, b = txt[:i], txt[i:]
        if b[0] in '，。、：；！？”）—…' or glued(a[-1], b[0]): continue
        wa, wb = text_size(a, fnt, size)[0], text_size(b, fnt, size)[0]
        if max(wa, wb) > maxw: continue
        sc = abs(wa - wb) - (0.45 * maxw if a[-1] in '，。、：；！？—' else 0)
        if sc < bs: best, bs = [a, b], sc
    if best: return best
    lines = []
    while txt:
        if text_size(txt, fnt, size)[0] <= maxw: lines.append(txt); break
        n = 1
        while n < len(txt) and text_size(txt[:n + 1], fnt, size)[0] <= maxw: n += 1
        ok = [i for i in range(2, n + 1) if i < len(txt) and txt[i] not in '，。、：；！？”）—…' and not glued(txt[i - 1], txt[i])]
        punct = [i for i in ok if txt[i - 1] in '，。、：；！？—' and text_size(txt[:i], fnt, size)[0] >= 0.6 * maxw]
        i = (punct or ok or [n])[-1]
        lines.append(txt[:i]); txt = txt[i:].lstrip(' ')
    return lines


def split_balanced(txt, fnt, size, maxw):
    """中文字幕断行：一行放得下就一行；否则在靠近中点、优先标点之后的位置断成两行"""
    if text_size(txt, fnt, size)[0] <= maxw: return [txt]
    best, bs = None, 1e9
    for i in range(4, len(txt) - 3):
        a, b = txt[:i], txt[i:]
        if b[0] in '，。、：；！？”）—…' or glued(a[-1], b[0]): continue
        wa, wb = text_size(a, fnt, size)[0], text_size(b, fnt, size)[0]
        if max(wa, wb) > maxw: continue
        score = abs(wa - wb) - (160 if a[-1] in '，。、：；！？—' else 0)
        if score < bs: best, bs = [a, b], score
    return best or wrap_cn(txt, fnt, size, maxw)


def sub_backing(cv, x0, y0, x1, y1, a, target=0.30, feather=30):
    """字幕底下的画面过亮（如糖浆滴、光斑）时，柔和地把这块压暗到 target 亮度以下；平时不动画面"""
    X0, Y0, X1, Y1 = int(max(x0, 0)), int(max(y0, 0)), int(min(x1, W)), int(min(y1, H))
    reg = cv.img[Y0:Y1, X0:X1]
    lum = np.percentile(reg.mean(-1) + cv.glow[Y0:Y1, X0:X1].mean(-1), 95)
    if lum <= target: return
    k = 1 - (1 - target / lum) * a
    yy = np.minimum(np.arange(Y1 - Y0), np.arange(Y1 - Y0)[::-1])[:, None]
    xx = np.minimum(np.arange(X1 - X0), np.arange(X1 - X0)[::-1])[None, :]
    m = (np.clip(yy / feather, 0, 1) * np.clip(xx / feather, 0, 1))[..., None]
    f = 1 - m * (1 - k)
    reg *= f
    cv.glow[Y0:Y1, X0:X1] *= f


def subtitles(cv, t):
    for s in TL['segs']:
        if s['id'] == 'tease': continue                 # 预告在片尾卡上单独排版
        a = env(t, s['start'] - 0.05, s['start'] + s['dur'] + 0.2, 0.12, 0.18)
        if a <= 0.004: continue
        txt = s['text'].replace('——', '—')
        size = 44
        lines = split_balanced(txt, 'sans_med', size, 920)
        if len(lines) > 2: size = 40; lines = split_balanced(txt, 'sans_med', size, 960)
        n = len(lines)
        tw = max(text_size(l, 'sans_med', size)[0] for l in lines)
        sub_backing(cv, W / 2 - tw / 2 - 50, 1530 - n * size * 0.71 - 34, W / 2 + tw / 2 + 50, 1530 + n * size * 0.71 + 34, a)
        for i, l in enumerate(lines):
            y = 1530 + (i - (n - 1) / 2) * size * 1.42
            cv.text(l, W / 2, y, size, 'sans_med', col=(0.97, 0.96, 0.93), a=a, shadow=0.85)


def chapter_label(cv, t):
    for cid, title, en in CHAPTERS:
        if title is None: continue
        a0, a1 = CH[cid]
        a = env(t, a0 + 1.6, a1 - 0.2, 0.6, 0.4) * 0.9
        if a > 0.004:
            num = '0' + str(int(cid[2]))
            cv.text(num, 52, 64, 30, 'oswald', col=GOLD, a=a, anchor='l')
            cv.line((96, 52), (96, 76), GOLD_D, a * 0.8, 2)
            cv.text(title, 110, 64, 26, 'sans_med', col=CREAM, a=a * 0.85, anchor='l')


def chapter_card(cv, t):
    for cid, title, en in CHAPTERS:
        if title is None: continue
        t0 = CH[cid][0]; t1 = t0 + 2.25
        a = env(t, t0, t1, 0.2, 0.45)
        if a <= 0.004: continue
        p = (t - t0)
        num = '0' + str(int(cid[2]))
        cv.dim(1 - 0.9 * a)
        sc = 1 + 0.04 * p
        cv.text(num, W / 2, 640, int(260 * sc), 'oswald', col=GOLD, a=a * 0.16, mode='add')
        cv.text(title, W / 2, 900, 78, 'serif_black', gold=True, a=a, reveal=eo(p / 0.7), glow=0.25)
        L = 300 * eo(p / 0.8)
        cv.line((W / 2 - L, 990), (W / 2 + L, 990), GOLD_D, a * 0.8, 2)
        cv.text(en, W / 2, 1040, 28, 'corm', col=GOLD, a=a * eo((p - 0.3) / 0.6), track=0.35)
        cv.text('第' + '一二三四五'[int(cid[2]) - 1] + '章', W / 2, 812, 30, 'sans_light', col=CREAM, a=a * 0.8, track=0.5)


# ------------------------------------------------------------------ 背景
CH_TINT = {  # (c1, c2, amt, rays)
    'hook': ((0.50, 0.06, 0.05), (0.45, 0.30, 0.10), 0.30, 0.25),
    'title': ((0.70, 0.10, 0.06), (0.60, 0.42, 0.14), 0.50, 0.7),
    'ch1': ((0.45, 0.30, 0.14), (0.40, 0.18, 0.08), 0.38, 0.45),
    'ch2': ((0.55, 0.08, 0.06), (0.50, 0.36, 0.12), 0.36, 0.5),
    'ch3': ((0.55, 0.40, 0.12), (0.45, 0.10, 0.06), 0.38, 0.55),
    'ch4': ((0.30, 0.05, 0.07), (0.12, 0.14, 0.25), 0.34, 0.2),
    'ch5': ((0.55, 0.42, 0.18), (0.50, 0.12, 0.08), 0.40, 0.6),
    'end': ((0.10, 0.20, 0.45), (0.50, 0.38, 0.14), 0.30, 0.3),
}


def chapter_at(t):
    for k in ['end', 'ch5', 'ch4', 'ch3', 'ch2', 'ch1', 'title']:
        if t >= CH[k][0]: return k
    return 'hook'


def background(t):
    k = chapter_at(t)
    order = ['hook', 'title', 'ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'end']
    i = order.index(k)
    c1, c2, amt, rays = CH_TINT[k]
    if i > 0:      # 章节切换处 1.5s 过渡
        pk = order[i - 1]; p = eio((t - CH[k][0]) / 1.5)
        a1, a2, aa, ar = CH_TINT[pk]
        c1 = tuple(lerp(x, y, p) for x, y in zip(a1, c1)); c2 = tuple(lerp(x, y, p) for x, y in zip(a2, c2))
        amt = lerp(aa, amt, p); rays = lerp(ar, rays, p)
    e = energy(t)
    amt *= 0.85 + 0.35 * e
    g = sh('BG')(t=t, c1=c1, c2=c2, amt=amt, focus=(0.5, 0.56), rays=rays)
    return g[..., :3]


def cube(cv, x, y, s, a, col=GOLD, depth=0.45):
    """等轴测立方体（金色面板 + 亮边）"""
    if a <= 0.004: return
    d = s * depth
    front = [(x - s / 2, y - s / 2), (x + s / 2, y - s / 2), (x + s / 2, y + s / 2), (x - s / 2, y + s / 2)]
    top = [(x - s / 2, y - s / 2), (x - s / 2 + d, y - s / 2 - d * 0.7), (x + s / 2 + d, y - s / 2 - d * 0.7), (x + s / 2, y - s / 2)]
    side = [(x + s / 2, y - s / 2), (x + s / 2 + d, y - s / 2 - d * 0.7), (x + s / 2 + d, y + s / 2 - d * 0.7), (x + s / 2, y + s / 2)]
    cv.fillpoly(front, col * 0.55, a); cv.fillpoly(top, col * 0.95, a, glow=0.15); cv.fillpoly(side, col * 0.35, a)
    cv.poly(front + [front[0]], GOLD_L, a * 0.7, 1); cv.poly(top, GOLD_L, a * 0.6, 1)


# ------------------------------------------------------------------ 镜头：开场
def ko_chart(cv, t, t0, x0, x1, y0, y1, y_from=1988.0, y_to=2027.0, reveal=1.0, a=1.0, log=True, col=None,
             lw=3, show_axis=True, tip_label=True, series=None):
    """KO 股价（拆股调整）曲线；对数坐标"""
    if a <= 0.004: return None
    Y, P = (KO_Y, KO_P) if series is None else series
    m = (Y >= y_from) & (Y <= y_to)
    Y, P = Y[m], P[m]
    vy = np.log(P) if log else P
    lo, hi = (math.log(2.0), math.log(110)) if log else (0, P.max() * 1.1)
    xs = x0 + (Y - y_from) / (y_to - y_from) * (x1 - x0)
    ys = y1 - (vy - lo) / (hi - lo) * (y1 - y0)
    n = max(2, int(len(xs) * cl(reveal)))
    step = max(1, n // 900)
    pts = np.stack([xs[:n:step], ys[:n:step]], 1)
    pts = np.vstack([pts, [xs[n - 1], ys[n - 1]]])
    if show_axis:
        for yr in range(1990, 2030, 5):
            if y_from <= yr <= y_to:
                xx = x0 + (yr - y_from) / (y_to - y_from) * (x1 - x0)
                cv.line((xx, y1 + 6), (xx, y1 + 16), DIM, a * 0.8, 1)
                cv.text(str(yr), xx, y1 + 38, 20, 'oswald', col=DIM, a=a * 0.9)
        for pv in (5, 10, 20, 50, 100):
            yy = y1 - ((math.log(pv) if log else pv) - lo) / (hi - lo) * (y1 - y0)
            if y0 - 5 <= yy <= y1:
                cv.line((x0, yy), (x1, yy), (0.18, 0.17, 0.17), a * 0.6, 1)
                cv.text(f'${pv}', x0 - 12, yy, 18, 'oswald', col=DIM, a=a * 0.8, anchor='r')
    colr = RED if col is None else col
    cv.poly(pts, colr * 0.55, a * 0.5, lw + 6)
    cv.poly(pts, colr, a, lw)
    tip = pts[-1]
    if tip_label:
        cv.glow_dot(tip, 14 + 8 * beat_pulse(t), GOLD_L, a * 0.9)
    return tip, (xs, ys)


def shot_hook(cv, t):
    # ---- 0 → s01：黑场中的金线心跳
    a0 = env(t, 0, S('s01') + 0.4, 0.0, 0.4)
    if a0 > 0:
        L = 420 * eo(t / 1.1)
        hb = sum(math.exp(-max(t - k, 0) * 6) * (t >= k) for k in (0.25,))
        cv.line((W / 2 - L, 960), (W / 2 + L, 960), GOLD, a0 * (0.5 + 0.5 * hb), 2)
        cv.glow_dot((W / 2, 960), 30 + 40 * hb, GOLD, a0 * 0.6)
    # ---- s01：“可口可乐，创历史新高了——93.9 美元。” 股价长线一口气冲上历史新高
    t0, t1 = S('s01') - 0.25, S('s03') + 0.25
    a = env(t, t0, t1, 0.35, 0.5)
    if a > 0:
        t_ath = WT('s01', '创历史新高')
        p = eio5((t - t0) / (t_ath + 0.25 - t0))
        r = ko_chart(cv, t, t0, 110, 990, 560, 1210, reveal=0.02 + 0.98 * p, a=a, col=RED)
        cv.text('KO', 120, 300, 40, 'oswald', col=CREAM, a=a, anchor='l', track=0.1)
        cv.text('THE COCA-COLA COMPANY · NYSE', 205, 302, 22, 'corm', col=GREY, a=a, anchor='l', track=0.12)
        ath = env(t, t_ath, t1, 0.18, 0.4)
        flash = math.exp(-max(t - t_ath, 0) * 3.5) * (t >= t_ath)
        if ath > 0:
            chip(cv, '历史新高', 230, 400, 40, ath, col=GOLD)
            if r:
                cv.glow_dot(r[0], 50 + 70 * flash, GOLD, ath * (0.35 + 0.45 * flash))
                cv.circle(r[0], 20 + 260 * (1 - math.exp(-max(t - t_ath, 0) * 3)), GOLD_L, ath * flash, 2)
        kp = eo((t - WT('s01', '九十三点九') + 0.1) / 0.35)
        if kp > 0:
            cv.text('$93.90', W / 2 + 120, 470, 150, 'sans_bold', gold=True, a=a * kp, glow=0.35, scale=1.1 - 0.1 * kp)
            cv.text('2026.10.16 收盘 · 盘中高点 $94.10（10.15）', W / 2 + 120, 570, 24, 'sans_light', col=GREY, a=a * kp)
        source(cv, '数据：Nasdaq / Yahoo Finance 日线（拆股调整）', a * 0.9)
    # ---- s03 前半：“有一位股东，已经持有它 38 年”——股东名册中被点亮的一行
    t_split = WT('s03', '当年')
    t0, t1 = S('s03') - 0.15, t_split + 0.25
    a = env(t, t0, t1, 0.3, 0.3)
    if a > 0:
        rng = np.random.default_rng(3)
        p = (t - t0)
        scroll = 1 - eo(p / 1.6)
        for i in range(-9, 10):
            y = 900 + i * 62 + scroll * 260
            w_ = 300 + rng.random() * 420
            hl = (i == 0)
            aa = a * (0.13 if not hl else 1.0) * (1 - min(abs(y - 900) / 700, 1))
            if not hl:
                cv.rrect(130, y - 9, 130 + w_, y + 9, 9, (0.32, 0.30, 0.30), aa)
                cv.rrect(860, y - 9, 950, y + 9, 9, (0.32, 0.30, 0.30), aa)
            else:
                k = eo((p - 0.6) / 0.5)
                cv.rrect(110, y - 40, 970, y + 40, 12, (0.16, 0.10, 0.06), a * k * 0.9, glow=0.0)
                cv.rrect(110, y - 40, 970, y + 40, 12, GOLD, a * k, fill=False, th=2)
                cv.text('BERKSHIRE HATHAWAY', 150, y, 40, 'oswald', col=GOLD_L, a=a * (0.25 + 0.75 * k), anchor='l', track=0.06)
                cv.text('since 1988', 940, y, 30, 'corm', col=GOLD, a=a * k, anchor='r')
        k38 = eo((t - WT('s03', '38') + 0.1) / 0.4)
        cv.text('38', W / 2, 420, 230, 'sans_light', col=WHITE, a=a * k38, glow=0.15)
        cv.text('年', W / 2 + 165, 470, 60, 'sans_med', col=GOLD, a=a * k38)
        cv.text('股东名册（示意）', W / 2, 1310, 22, 'sans_light', col=DIM, a=a * 0.8)
    # ---- s03 后半：13亿 → 376亿
    t0, t1 = t_split - 0.1, S('s04') + 0.15
    a = env(t, t0, t1, 0.3, 0.4)
    if a > 0:
        p = t - t0
        t376 = WT('s03', '376') - t0
        base = 1330
        cube(cv, 200, base - 40, 70, a * eo(p / 0.5))
        kk = eexp((p - t376 + 0.6) / 1.6)
        hcol = 760 * kk
        if hcol > 2:
            cv.rect(955, base - 75 - hcol, 1015, base - 75, GOLD * 0.7, a, glow=0.25)
            cv.rect(955, base - 75 - hcol, 963, base - 75, GOLD_L, a * 0.8)
        cv.text('成本', 200, base + 30, 24, 'sans_light', col=GREY, a=a * eo(p / 0.5))
        cv.text('市值', 985, base + 30, 24, 'sans_light', col=GREY, a=a * kk)
        cv.text('1988–1994 买入成本', W / 2, 520, 32, 'sans_light', col=GREY, a=a)
        cv.text('$13亿', W / 2, 640, 120, 'sans_light', col=CREAM, a=a * (1 - 0.6 * eo((p - t376 + 0.6) / 0.6)))
        k = eo((p - t376 + 0.6) / 0.5)
        if k > 0:
            v = counter(13, 376, t, t0 + t376 - 0.6, 1.4, lambda v: f'${v:,.0f}亿')
            cv.text('今日市值', W / 2, 800, 32, 'sans_light', col=GOLD, a=a * k)
            cv.text(v, W / 2, 960, 210, 'sans_bold', gold=True, a=a * k, glow=0.35, scale=0.94 + 0.06 * k)
            cv.text('×28.9', W / 2, 1130, 54, 'oswald', col=GOLD_L, a=a * eo((p - t376 - 0.6) / 0.5), track=0.06)
        source(cv, '成本：伯克希尔1994年报 $12.99亿 · 市值：4亿股 × $93.90', a)
    # ---- s04：股息 8.48 亿
    t0, t1 = S('s04') - 0.1, S('s05') + 0.1
    a = env(t, t0, t1, 0.35, 0.35)
    if a > 0:
        p = t - t0
        rng = np.random.default_rng(11)
        n = 300
        xs = rng.uniform(80, 1000, n); sp = rng.uniform(420, 900, n); ph = rng.uniform(0, 3, n)
        ys = ((p + ph) * sp) % 1500 + 150
        cv.splat(xs, ys, GOLD, a * 0.55 * np.minimum(1, p / 0.8), glow=1.5)
        cv.splat(xs, ys - 6, GOLD, a * 0.25 * np.minimum(1, p / 0.8), glow=1.0)
        cv.text('2026 年股息（全年预计）', W / 2, 600, 34, 'sans_light', col=GREY, a=a)
        k = eo((t - WT('s04', '八点四八') + 0.1) / 0.4)
        cv.text('$8.48亿', W / 2, 780, 190, 'sans_bold', gold=True, a=a * k, glow=0.3, scale=1.06 - 0.06 * k)
        cv.text('约为当初成本的 65%', W / 2, 960, 40, 'sans_med', col=CREAM, a=a * eo((t - WT('s04', '八点四八') - 0.9) / 0.5))
        source(cv, '每股 $0.53 × 4 季 × 4亿股（可口可乐 2025 年报：连续第64年提高股息）', a)
    # ---- s05：三次危机闪回 → “一股未卖” → 为什么？（之后是整段留白，直到标题重拍）
    t0, t1 = S('s05') - 0.1, CH['title'][0] + 0.05
    a = env(t, t0, t1, 0.2, 0.05)
    if a > 0:
        p = t - t0
        items = [('2000', '互联网泡沫', '泡沫'), ('2008', '金融危机', '危机'), ('2020', '全球疫情', '疫情')]
        for i, (yr, nm, w) in enumerate(items):
            ti = WT('s05', w) - t0 - 0.1
            k = env(p, ti, ti + 0.8, 0.08, 0.3)
            if k > 0:
                cv.text(yr, W / 2, 760, 200, 'oswald', col=RED, a=a * k * 0.9, glow=0.4)
                cv.text(nm, W / 2, 920, 56, 'serif_black', col=CREAM, a=a * k)
        tq = WT('s05', '他一股') - t0
        k = env(p, tq, 99, 0.25, 0)
        if k > 0:
            cv.text('一股未卖', W / 2, 840, 150, 'serif_black', gold=True, a=a * k, glow=0.35, scale=1.06 - 0.06 * eo((p - tq) / 0.8))
        k2 = env(p, WT('s05', '为什么') - t0, 99, 0.3, 0)
        if k2 > 0:
            cv.text('为什么？', W / 2, 1040, 64, 'serif_semi', col=CREAM, a=a * k2)
        # “为什么？”之后的空气：画面慢慢沉下去，只剩金字与心跳般的微光
        sink = eio((t - E('s05') - 0.2) / 1.2)
        if sink > 0: cv.dim(1 - 0.35 * sink)


# ------------------------------------------------------------------ 标题
def bottle_layer(cv, t, a=1.0, rot=0.0, fill=0.8, camd=7.6, camy=1.25, shift=(0.0, 0.0), ex=1.0, bub=1.0,
                 ripple=0.0, floorr=1.0, gold=1.0):
    if a <= 0.004: return
    b = sh('BOTTLE')(t=t, rot=rot, camy=camy, camd=camd, fill=fill, glass_a=1.0, key=(1.0, 0.95, 0.9), ex=ex,
                     bub=bub, shift=shift, tilt=0.0, gold=gold, ripple=ripple, floorr=floorr)
    al = b[..., 3:4] * a
    cv.img = cv.img * (1 - al) + b[..., :3] * a
    cv.glow += np.clip(b[..., :3] * a - 0.55, 0, None) * 0.8


def shot_title(cv, t):
    t0, t1 = CH['title'][0], CH['ch1'][0] + 0.6
    a = env(t, t0, t1, 0.02, 0.6)
    if a <= 0: return
    p = t - t0
    flash = math.exp(-p * 5.0)
    bottle_layer(cv, t, a * eo(p / 0.25), rot=0.6 + p * 0.25, fill=0.82, camd=8.2, camy=1.45, shift=(0.0, 0.11),
                 ex=0.6 + 0.8 * (1 - math.exp(-p * 3)), bub=1.0)
    # 冲击波光环
    R = 60 + p * 900
    cv.circle((W / 2, 760), R, GOLD, a * math.exp(-p * 2.2) * 0.8, 3)
    cv.glow_dot((W / 2, 760), 220, GOLD, a * flash * 0.9)
    k = eo((p - 0.15) / 0.6)
    cv.text('38年', W / 2, 1230, 190, 'serif_black', gold=True, a=a * k, glow=0.3, scale=1.08 - 0.08 * k)
    cv.text('一股未卖', W / 2, 1400, 120, 'serif_black', gold=True, a=a * eo((p - 0.45) / 0.6), glow=0.25)
    cv.text('巴菲特与可口可乐', W / 2, 1290 + 230, 44, 'sans_light', col=CREAM, a=a * eo((p - 0.9) / 0.6), track=0.3)
    cv.text('38 YEARS · NOT ONE SHARE SOLD', W / 2, 1600, 24, 'corm', col=GOLD, a=a * eo((p - 1.2) / 0.6), track=0.3)


# ------------------------------------------------------------------ 片尾：粒子汇聚成官方 logo
_end = {}
TEASE_L1, TEASE_L2 = '360亿美元买入苹果', '他为什么又卖掉了大半？'
TEASE_Y1, TEASE_Y2 = 735, 845


def text_points(s, fnt, size, x, y):
    """cv.text(s, x, y, anchor='m') 画出的文字像素位置（用于“文字化作粒子”）"""
    m, base, w, h = text_mask(s, fnt, size)
    asc, _ = font(fnt, size).getmetrics()
    ys, xs = np.nonzero(m > 0.5)
    return xs + x - w / 2, ys + y - (base - asc * 0.40)


def end_particles():
    if 'pts' not in _end:
        rgb, al = logo(300)
        ys, xs = np.nonzero(al > 0.35)
        rng = np.random.default_rng(5)
        n = 2600
        idx = rng.choice(len(xs), n, replace=len(xs) < n)
        tx = xs[idx] - 150 + W / 2 + rng.normal(0, 0.6, n); ty = ys[idx] - 150 + 760 + rng.normal(0, 0.6, n)
        col = rgb[ys[idx], xs[idx]]
        # 粒子的起点：下期预告的两行文字（文字淡去的同时化作金色粒子）
        p1 = text_points(TEASE_L1, 'serif_black', 76, W / 2, TEASE_Y1)
        p2 = text_points(TEASE_L2, 'serif_semi', 54, W / 2, TEASE_Y2)
        px = np.concatenate([p1[0], p2[0]]); py = np.concatenate([p1[1], p2[1]])
        k = rng.choice(len(px), n, replace=len(px) < n)
        sx = px[k] + rng.normal(0, 0.8, n); sy = py[k] + rng.normal(0, 0.8, n)
        delay = rng.uniform(0, 0.35, n); swirl = rng.uniform(-1.0, 1.0, n)
        _end['pts'] = (tx, ty, sx, sy, col, delay, swirl)
    return _end['pts']


def shot_end(cv, t):
    """片尾：下期预告 → 预告文字化作金色粒子，以官方 logo 透明通道为目标汇聚 → 原始 logo（重拍）
    → 金色「巴芒价值」+「BUFFETT · MUNGER」扫光 → 细金线 → 小字关注语 → 整体淡出（角标保留到最后）"""
    t0 = CH['end'][0]
    hit = MP['hits']['logo']
    if t < t0 - 0.6: return
    cx, cy = W / 2, 760
    ts = SEG['tease']['start']
    t_dis = hit - MP.get('dissolve', 1.5)                  # 文字开始化作粒子
    # 0) 下期预告（与旁白同步）
    ka = env(t, ts - 0.05, t_dis + 0.15, 0.6, 0.45)          # 上一镜头（s48）在 ts 前已淡出，不叠化
    if ka > 0.004:
        chip(cv, '下期预告', W / 2, 615, 26, ka, col=GOLD)
        cv.text(TEASE_L1, W / 2, TEASE_Y1, 76, 'serif_black', gold=True, a=ka, shadow=0.6, glow=0.12)
        k2 = eo((t - WT('tease', '他为什么') + 0.1) / 0.5)
        cv.text(TEASE_L2, W / 2, TEASE_Y2, 54, 'serif_semi', col=CREAM, a=ka * k2, shadow=0.6)
    # 1) 预告文字化作粒子，汇聚成官方 logo
    tx, ty, sx, sy, col, delay, swirl = end_particles()
    if t >= t_dis - 0.1:
        dur = hit - t_dis
        k = np.clip((t - t_dis - delay) / max(dur - 0.35, 0.4), 0, 1)
        ke = 1 - (1 - k) ** 3
        ang = swirl * np.sin(ke * np.pi) * 0.9
        px = lerp(sx, tx, ke); py = lerp(sy, ty, ke)
        dx, dy = px - cx, py - cy
        rx = cx + dx * np.cos(ang) - dy * np.sin(ang); ry = cy + dx * np.sin(ang) + dy * np.cos(ang)
        pcol = lerp(np.asarray(GOLD_L, np.float32)[None, :], col, ke[:, None])
        pa = eo((t - t_dis + 0.1) / 0.35) * (1 - eo((t - hit) / 0.5)) * 1.1
        if pa > 0.004:
            cv.splat(rx, ry, pcol * 1.4 + 0.15, pa, glow=1.6)
    # 2) 清晰的原始 logo 居中浮现（重拍）
    la = eo((t - hit + 0.15) / 0.5)
    if la > 0:
        rgb, al = logo(300)
        sc = 1 + 0.06 * (1 - eo((t - hit) / 1.2))
        s = int(300 * sc)
        rgb2 = cv2.resize(rgb * al[..., None], (s, s), interpolation=cv2.INTER_AREA)
        al2 = cv2.resize(al, (s, s), interpolation=cv2.INTER_AREA)
        rgbn = np.where(al2[..., None] > 1e-4, rgb2 / np.maximum(al2[..., None], 1e-4), 0)
        # 很淡的蓝色光晕（品牌规范）
        pad = 100                                   # 光晕在加边后的画布上模糊，避免被 logo 方框裁出一圈方形边界
        halo = cv2.GaussianBlur(np.pad(al2, pad), (0, 0), 30) * 0.35 * la
        cv.add(np.array([110, 175, 255], np.float32) / 255, halo, cx - s / 2 - pad, cy - s / 2 - pad)
        cv.over(rgbn, al2 * la, cx - s / 2, cy - s / 2)
        cv.glow_dot((cx, cy), 200, BLUE, la * math.exp(-max(t - hit, 0) * 2.5) * 0.8)
    # 3) 金色「巴芒价值」+「BUFFETT · MUNGER」随重拍出现，扫过流光
    ta = eo((t - hit - 0.25) / 0.6)
    if ta > 0:
        brand_title(cv, t, ta, hit + 1.0)
    # 4) 下方一道细金线 → 小字关注语
    la2 = eo((t - hit - 1.5) / 0.9)
    if la2 > 0:
        Lw = 300 * la2
        cv.line((W / 2 - Lw, 1238), (W / 2 + Lw, 1238), GOLD_D, la2, 2)
        cv.glow_dot((W / 2 - Lw, 1238), 6, GOLD_L, la2 * 0.8); cv.glow_dot((W / 2 + Lw, 1238), 6, GOLD_L, la2 * 0.8)
        fa = eo((t - hit - 2.1) / 0.9)
        cv.text('关注「巴芒价值」，传承大师智慧，领悟投资真谛', W / 2, 1300, 34, 'serif_semi', col=GOLD_L, a=fa * 0.95, track=0.04)


_bt = {}
def brand_title(cv, t, a, shimmer_t0):
    """片尾大号品牌字：金色宋体「巴芒价值」+ 等宽小字「BUFFETT · MUNGER」（规范取自 brand/brand.py SPEC）"""
    size = 132
    if 'title' not in _bt:
        m1, b1, w1, h1 = text_mask(BRAND_SPEC['title'], 'serif_black', size)
        ys, = np.nonzero(m1.max(1) > 0.01); m1 = m1[ys[0]:ys[-1] + 1]
        g = grad_rgb(m1.shape[0], GOLD_STOPS)
        # 小字两端对齐到主标题宽度
        sub = BRAND_SPEC['sub']; f2 = font('corm', 40)
        nat = sum(f2.getlength(c) for c in sub)
        tr = (m1.shape[1] - nat) / (len(sub) - 1)
        from PIL import Image, ImageDraw
        im = Image.new('L', (int(m1.shape[1] + 80), 90), 0); d = ImageDraw.Draw(im); x = 10
        for c in sub:
            d.text((x, 60), c, font=f2, fill=255, anchor='ls'); x += f2.getlength(c) + tr
        m2 = np.asarray(im, np.float32) / 255
        ys, = np.nonzero(m2.max(1) > 0.01); xs, = np.nonzero(m2.max(0) > 0.01)
        m2 = m2[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1]
        _bt['title'] = (m1, g, m2)
    m1, g, m2 = _bt['title']
    y1 = 1040
    x1 = W / 2 - m1.shape[1] / 2
    col = np.repeat(g[:, None, :], m1.shape[1], 1)
    # 流光：一次 1.4s 的斜向扫光（与角标流光节奏一致）
    u = (t - shimmer_t0) / BRAND_SPEC['shimmer_dur']
    if 0 <= u <= 1:
        xs = np.arange(m1.shape[1])[None, :] + np.arange(m1.shape[0])[:, None] * 0.6
        pos = -60 + (0.5 - 0.5 * math.cos(u * math.pi)) * (m1.shape[1] + 120)
        band = np.exp(-((xs - pos) / 34) ** 2)[..., None]
        col = np.clip(col + band * 0.6, 0, 1.3)
    cv.text_shadow = None
    sh_ = cv2.GaussianBlur(m1, (0, 0), 8) * 0.6 * a
    cv.img_mul(1 - sh_, x1 + 3, y1 - m1.shape[0] / 2 + 5)
    cv.over(col, m1 * a, x1, y1 - m1.shape[0] / 2)
    cv._glow(col, m1 * a * 0.18, x1, y1 - m1.shape[0] / 2)
    sy = y1 + m1.shape[0] / 2 + 28
    cv.over(np.array(SUB_GOLD, np.float32) / 255, m2 * a, W / 2 - m2.shape[1] / 2, sy)




# ------------------------------------------------------------------ 点阵地球（Natural Earth 陆地遮罩，公有领域）
_globe = {}
def globe_pts():
    if 'p' not in _globe:
        m = cv2.imread(os.path.join(ROOT, 'assets', 'geo', 'landmask.png'), 0)
        n = 26000; i = np.arange(n) + 0.5
        lat = np.arcsin(1 - 2 * i / n); lon = (np.pi * (1 + 5 ** 0.5) * i) % (2 * np.pi) - np.pi
        px = ((lon * 180 / np.pi + 180) * 2).astype(int).clip(0, 719); py = ((90 - lat * 180 / np.pi) * 2).astype(int).clip(0, 359)
        land = m[py, px] > 127
        _globe['p'] = (lat[land], lon[land])
    return _globe['p']


def sph(lat, lon):
    return np.stack([np.cos(lat) * np.sin(lon), np.sin(lat), np.cos(lat) * np.cos(lon)], -1)


ATL = (math.radians(33.75), math.radians(-84.39))
CITIES = [(51.5, -0.1), (35.7, 139.7), (19.4, -99.1), (-23.5, -46.6), (28.6, 77.2), (31.2, 121.5), (-33.9, 18.4),
          (55.8, 37.6), (6.5, 3.4), (-33.9, 151.2), (40.4, -3.7), (1.35, 103.8), (30.0, 31.2), (52.5, 13.4),
          (13.7, 100.5), (-34.6, -58.4), (24.7, 46.7), (37.6, 127.0), (-6.2, 106.8), (45.5, -73.6)]


def globe(cv, t, cx, cy, R, rot, tilt=0.35, a=1.0, arcs=0.0, col=GOLD, land_a=1.0, city_glow=1.0):
    if a <= 0.004: return
    lat, lon = globe_pts()
    def proj(v):
        x, y, z = v[..., 0], v[..., 1], v[..., 2]
        c, s = math.cos(rot), math.sin(rot)
        x, z = x * c + z * s, -x * s + z * c
        ct, st = math.cos(tilt), math.sin(tilt)
        y, z = y * ct - z * st, y * st + z * ct
        return x, y, z
    x, y, z = proj(sph(lat, lon))
    front = z > -0.05
    shade = np.clip(z, 0, 1) ** 0.7
    cv.splat(cx + x[front] * R, cy - y[front] * R, col, a * land_a * (0.2 + 1.1 * shade[front]), glow=0.7)
    # 大气辉光与轮廓
    cv.circle((cx, cy), R, col * 0.6, a * 0.35, 2)
    cv.glow_dot((cx, cy), R * 0.75, RED_D, a * 0.25)
    if arcs > 0:
        a0 = sph(np.array(ATL[0]), np.array(ATL[1]))
        for k, (la, lo) in enumerate(CITIES):
            pk = cl((arcs * len(CITIES) - k * 0.85) / 1.6)
            if pk <= 0: continue
            b = sph(np.array(math.radians(la)), np.array(math.radians(lo)))
            om = math.acos(cl(float(np.dot(a0, b)), -1, 1))
            ts = np.linspace(0, 1, 48)[:, None] * pk
            pts = (np.sin((1 - ts) * om) * a0 + np.sin(ts * om) * b) / math.sin(om)
            pts *= (1 + 0.10 * np.sin(np.pi * ts / max(pk, 1e-3)) * om / 2)
            px, py, pz = proj(pts)
            vis = pz > -0.1
            P = np.stack([cx + px * R, cy - py * R], 1)
            seg = P[vis]
            if len(seg) > 1: cv.poly(seg, RED, a * 0.9, 2)
            if pk >= 1 and pz[-1] > 0:
                cv.glow_dot((cx + px[-1] * R, cy - py[-1] * R), 7, GOLD_L, a * city_glow)
        ax, ay, az = proj(a0)
        if az > 0: cv.glow_dot((cx + ax * R, cy - ay * R), 12, RED, a)
