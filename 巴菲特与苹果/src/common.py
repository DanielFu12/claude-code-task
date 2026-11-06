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
MP = dict(hits=dict(logo=TL['logo']), dissolve=TL.get('dissolve', 1.5))   # 片尾 logo 重拍（由时间线给出，配乐对位到它）
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
    """句内某个词开始发声的时刻：有强制对齐数据（ct）时精确到字，否则按字数比例估算"""
    for src, exact in ((_SAY[i], True), (_TXT[i], False)):
        k = src.find(sub)
        if k < 0: continue
        if exact and SEG[i].get('ct'):
            for idx, tt in SEG[i]['ct']:
                if idx >= k: return S(i) + tt
        return S(i) + SEG[i]['dur'] * k / max(len(src), 1)
    raise KeyError(f'{sub} not in {i}')


def energy(t):
    k = int(t * FPS); return float(ENERGY[min(max(k, 0), len(ENERGY) - 1)])


def beat_pulse(t, decay=7.0):
    """最近一个节拍后的衰减脉冲 0..1"""
    i = np.searchsorted(BEATS, t) - 1
    if i < 0: return 0.0
    return math.exp(-(t - BEATS[i]) * decay)


# ------------------------------------------------------------------ 数据
def _yahoo(name):
    d = json.load(open(os.path.join(ROOT, 'data', name)))['chart']['result'][0]
    c = d['indicators']['quote'][0]['close']
    return [(dt.datetime.fromtimestamp(ts, dt.UTC).date(), v) for ts, v in zip(d['timestamp'], c) if v]


def yearf(d): return d.year + (d.timetuple().tm_yday - 0.5) / 366


AAPL = _yahoo('aapl_daily.json')
AA_Y = np.array([yearf(r[0]) for r in AAPL]); AA_P = np.array([r[1] for r in AAPL])
SP = _yahoo('sp500tr_daily.json')
SP_Y = np.array([yearf(r[0]) for r in SP]); SP_V = np.array([r[1] for r in SP])
HOLD = [(yearf(dt.date.fromisoformat(d)), sh) for d, sh in CALC['holdings']]      # 伯克希尔逐季持股（13F，拆股调整）
CLOSE = CALC['close']; ATH = CALC['ath']


def aa_at(y):
    i = int(np.searchsorted(AA_Y, y)); return float(AA_P[min(max(i, 0), len(AA_P) - 1)])


# ------------------------------------------------------------------ 资源
_cache = {}
def asset(name):
    if name not in _cache:
        p = os.path.join(ROOT, 'assets', 'media', name + '.jpg')
        im = cv2.imread(p)
        im = np.zeros((10, 10, 3), np.float32) if im is None else im[..., ::-1].astype(np.float32) / 255
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
    en_lines = wrap('“' + en + '”', 'typewriter', en_size, w - 90) if en else []
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
    cjk = any('\u4e00' <= c <= '\u9fff' for c in who)
    cv.text(who, x0 + 140, y0 + 64, 22 if cjk else 24, 'sans_light' if cjk else 'corm', col=GOLD, a=al, anchor='l')
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
    ca = al * eo((t - t0 - 0.3 - (typing * 0.6 if en else 0)) / 0.8)
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


import re as _re
_PUNCT = '，。；：？！'
_chunks = {}


def _split(s):
    """按标点切成短语（保留语义完整的最小单位），过短的并入下一段"""
    parts = [x for x in _re.split('([' + _PUNCT + '])', s)]
    out, cur = [], ''
    for x in parts:
        if not x: continue
        if x in _PUNCT:
            cur += x if x in '？！' else ''
            out.append(cur); cur = ''
        else: cur += x
    if cur: out.append(cur)
    merged = []
    for x in out:
        if merged and len(merged[-1].strip('“”')) < 5: merged[-1] += x
        else: merged.append(x)
    return [m for m in merged if m.strip()]


def sub_chunks(seg):
    """一句旁白 → [(短语, 起, 止)]：用强制对齐的逐字时刻，短语在读到它时出现"""
    i = seg['id']
    if i in _chunks: return _chunks[i]
    txt, say = _TXT[i], _SAY[i]
    tc, sc = _split(txt), _split(say)
    t0, dur = seg['start'], seg['dur']
    ct = seg.get('ct') or []
    def at(k):
        for idx, tt in ct:
            if idx >= k: return t0 + tt
        return t0 + dur * k / max(len(say), 1)
    starts = []
    if len(tc) == len(sc):
        pos = 0
        for c in sc:
            k = say.find(c.rstrip('？！')[:2], pos); k = pos if k < 0 else k
            starts.append(at(k)); pos = k + len(c)
    else:
        n = sum(len(c) for c in tc); acc = 0
        for c in tc: starts.append(t0 + dur * acc / n); acc += len(c)
    ends = starts[1:] + [t0 + dur]
    _chunks[i] = list(zip(tc, starts, ends))
    return _chunks[i]


def subtitles(cv, t):
    """逐段字幕：同一时刻只显示正在读的那一个短语（淡入 + 轻微上浮），读完换下一段"""
    for s in TL['segs']:
        if s['id'] == 'tease': continue
        if not (s['start'] - 0.2 <= t <= s['start'] + s['dur'] + 0.4): continue
        ch = sub_chunks(s)
        for k, (txt, a0, a1) in enumerate(ch):
            last = k == len(ch) - 1
            # 前一段完全淡出后，后一段才淡入（不叠影）；句末一段多停 0.25s（句间间隔 ≥0.35s）
            a = env(t, a0 - (0.06 if k == 0 else 0.0), a1 + (0.25 if last else 0.0), 0.14, 0.25 if last else 0.12)
            if a <= 0.004: continue
            rise = 10 * (1 - eo((t - a0) / 0.25))
            size = 50
            lines = split_balanced(txt, 'sans_med', size, 940) if text_size(txt, 'sans_med', size)[0] > 940 else [txt]
            n = len(lines)
            tw = max(text_size(l, 'sans_med', size)[0] for l in lines)
            yc = 1555 + 35 * (n - 1) + rise                      # 两行时第一行保持原位、第二行向下，避开上方出处行
            sub_backing(cv, W / 2 - tw / 2 - 50, yc - n * size * 0.75 - 30, W / 2 + tw / 2 + 50, yc + n * size * 0.75 + 30, a)
            for j, l in enumerate(lines):
                cv.text(l, W / 2, yc + (j - (n - 1) / 2) * size * 1.4, size, 'sans_med', col=(0.98, 0.97, 0.94), a=a, shadow=0.9)


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


NAV = ['看懂苹果', '买的是生意', '十年账本', '为什么卖', '卖与不卖']
TAKE = {'tk_ch1': ('01', '能力圈', '看得懂，才下重注', '巴菲特等了几十年，直到从身边的消费者身上看懂了苹果'),
        'tk_ch2': ('02', '买的是生意', '回购与透视盈余', '没发下来的利润，也在替股东赚钱；每股收益比净利润涨得更快'),
        'tk_ch3': ('03', '时间与复利', '十年，约 5.6 倍', '同样的钱买标普 500 年化约 15%，苹果年化约 29%'),
        'tk_ch4': ('04', '价格、税与仓位', '好生意，也有不划算的价格', '卖出的是对价格和仓位的判断，不是对生意的否定')}


def nav(cv, t):
    """顶部章节导航：五段进度条，当前章节高亮并随时间填充"""
    if t < CH['ch1'][0] + 0.3 or t > CH['end'][0]: return
    a = env(t, CH['ch1'][0] + 0.3, CH['end'][0], 0.6, 0.6)
    x0, x1, y = 70, 1010, 196
    sw = (x1 - x0) / 5; gap = 12
    for i, nm in enumerate(NAV):
        cid = f'ch{i + 1}'; a0, a1 = CH[cid]
        xa = x0 + i * sw + gap / 2; xb = x0 + (i + 1) * sw - gap / 2
        cv.rect(xa, y - 2, xb, y + 2, (0.3, 0.3, 0.33), a * 0.8)
        f = cl((t - a0) / max(a1 - a0, 1)) if t >= a0 else 0
        if f > 0: cv.rect(xa, y - 2, xa + (xb - xa) * f, y + 2, GOLD if a0 <= t < a1 else GOLD_D, a, glow=0.3 if a0 <= t < a1 else 0)
        cur = a0 <= t < a1
        cv.text(f'0{i + 1} {nm}', (xa + xb) / 2, y + 30, 22 if cur else 20, 'sans_med' if cur else 'sans_light',
                col=CREAM if cur else (0.55, 0.55, 0.58), a=a)


def takeaway(cv, t):
    """每章结尾的“本章要点”：巴菲特理念卡"""
    for k, (num, title, key, desc) in TAKE.items():
        if k not in CH: continue
        t0, t1 = CH[k]
        a = env(t, t0 - 0.15, t1 + 0.1, 0.35, 0.4)
        if a <= 0.004: continue
        p = t - t0
        cv.dim(1 - 0.95 * a); cv.glow *= (1 - 0.95 * a); cv.U = (cv.U * (1 - 0.95 * a)).astype(np.uint8)
        cv.rrect(90, 640, 990, 1260, 28, (0.05, 0.045, 0.04), a)
        cv.rrect(90, 640, 990, 1260, 28, GOLD, a * 0.7, fill=False, th=2, glow=0.2)
        chip(cv, '本章要点 · 巴菲特理念 ' + num, W / 2, 720, 28, a, col=GOLD)
        cv.text(title, W / 2, 850, 84, 'serif_black', gold=True, a=a * eo(p / 0.5), glow=0.3, scale=1.06 - 0.06 * eo(p / 0.5))
        L = 260 * eo((p - 0.3) / 0.6)
        cv.line((W / 2 - L, 940), (W / 2 + L, 940), GOLD_D, a, 2)
        cv.text(key, W / 2, 1020, 50, 'serif_semi', col=CREAM, a=a * eo((p - 0.5) / 0.5))
        for j, ln in enumerate(split_balanced(desc, 'sans_light', 30, 780)):
            cv.text(ln, W / 2, 1120 + j * 46, 30, 'sans_light', col=(0.75, 0.74, 0.72), a=a * eo((p - 0.9) / 0.5))


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


# ------------------------------------------------------------------ 图表：苹果股价（拆股调整，对数坐标）
def aapl_chart(cv, t, x0, x1, y0, y1, y_from=2016.0, y_to=2026.9, reveal=1.0, a=1.0, col=None, lw=3,
               show_axis=True, tip=True, lo=18.0, hi=420.0, ticks=(25, 50, 100, 200, 400)):
    if a <= 0.004: return None
    m = (AA_Y >= y_from) & (AA_Y <= y_to)
    Y, P = AA_Y[m], AA_P[m]
    xs = x0 + (Y - y_from) / (y_to - y_from) * (x1 - x0)
    ys = y1 - (np.log(P) - math.log(lo)) / (math.log(hi) - math.log(lo)) * (y1 - y0)
    n = max(2, int(len(xs) * cl(reveal)))
    step = max(1, n // 900)
    pts = np.vstack([np.stack([xs[:n:step], ys[:n:step]], 1), [xs[n - 1], ys[n - 1]]])
    if show_axis:
        for yr in range(int(math.ceil(y_from)), int(y_to) + 1, 2):
            xx = x0 + (yr - y_from) / (y_to - y_from) * (x1 - x0)
            cv.line((xx, y1 + 6), (xx, y1 + 16), DIM, a * 0.8, 1)
            cv.text(str(yr), xx, y1 + 38, 20, 'oswald', col=DIM, a=a * 0.9)
        for pv in ticks:
            yy = y1 - (math.log(pv) - math.log(lo)) / (math.log(hi) - math.log(lo)) * (y1 - y0)
            if y0 - 5 <= yy <= y1:
                cv.line((x0, yy), (x1, yy), (0.18, 0.18, 0.2), a * 0.6, 1)
                cv.text(f'${pv}', x0 - 12, yy, 18, 'oswald', col=DIM, a=a * 0.8, anchor='r')
    colr = CREAM if col is None else col
    cv.poly(pts, colr * 0.5, a * 0.45, lw + 6)
    cv.poly(pts, colr, a, lw)
    if tip: cv.glow_dot(pts[-1], 12 + 8 * beat_pulse(t), GOLD_L, a * 0.9)
    return pts[-1], (xs, ys)


def ax_y(v, y0, y1, lo=18.0, hi=420.0):
    return y1 - (math.log(v) - math.log(lo)) / (math.log(hi) - math.log(lo)) * (y1 - y0)


def ax_x(yr, x0, x1, y_from=2016.0, y_to=2026.9):
    return x0 + (yr - y_from) / (y_to - y_from) * (x1 - x0)


def holdings_chart(cv, t, x0, x1, y0, y1, reveal=1.0, a=1.0, hl=None, y_from=2016.0, y_to=2026.9, vmax=1.1e9):
    """伯克希尔逐季持股（亿股）柱状图"""
    if a <= 0.004: return
    bw = (x1 - x0) / ((y_to - y_from) * 4) * 0.72
    n = len(HOLD)
    for k, (yy, sh_) in enumerate(HOLD):
        if k / n > reveal: break
        x = ax_x(yy, x0, x1, y_from, y_to)
        h = (y1 - y0) * sh_ / vmax
        col = GOLD * 0.75 if not (hl and hl(yy)) else RED
        cv.rect(x - bw / 2, y1 - h, x + bw / 2, y1, col, a * 0.9)
    for v in (2e8, 5e8, 1e9):
        yy = y1 - (y1 - y0) * v / vmax
        cv.line((x0, yy), (x1, yy), (0.2, 0.2, 0.22), a * 0.5, 1)
        cv.text(f'{v / 1e8:.0f}亿股', x0 - 10, yy, 18, 'sans_light', col=DIM, a=a * 0.8, anchor='r')
    for yr in range(2016, 2027, 2):
        cv.text(str(yr), ax_x(yr + 0.5, x0, x1, y_from, y_to), y1 + 30, 20, 'oswald', col=DIM, a=a * 0.9)


# ------------------------------------------------------------------ 镜头：开场
def shot_hook(cv, t):
    import media as M
    # ---- 0 → h1：黑场中的金线心跳
    a0 = env(t, 0, S('h1') + 0.6, 0.0, 0.5)
    if a0 > 0:
        L = 420 * eo(t / 1.1)
        hb = math.exp(-max(t - 0.25, 0) * 6) * (t >= 0.25)
        cv.line((W / 2 - L, 960), (W / 2 + L, 960), GOLD, a0 * (0.5 + 0.5 * hb), 2)
        cv.glow_dot((W / 2, 960), 30 + 40 * hb, GOLD, a0 * 0.6)
    # ---- h1：2026 年秋，股价一再刷新纪录（Apple Park 航拍 + 十年股价曲线）
    t0, t1 = S('h1') - 0.3, S('h2') + 0.2
    a = env(t, t0, t1, 0.6, 0.5)
    if a > 0:
        M.full(cv, 'apple_park_aerial', t, t0, t1, z0=1.25, z1=1.4, focus=(0.5, 0.5), dark=0.55, a=a, cap='Apple Park 航拍')
        tr = WT('h1', '市值')
        p = eio5((t - t0) / (tr - t0))
        r = aapl_chart(cv, t, 130, 990, 520, 1180, reveal=0.02 + 0.98 * p, a=a, col=CREAM)
        cv.text('AAPL', 130, 330, 44, 'oswald', col=CREAM, a=a, anchor='l', track=0.1)
        cv.text('APPLE INC. · NASDAQ · 2016–2026', 250, 333, 22, 'corm', col=GREY, a=a, anchor='l', track=0.12)
        # 2026 年的历次收盘新高：点亮
        recs = [y for y, pp, prev in zip(AA_Y[1:], AA_P[1:], np.maximum.accumulate(AA_P)[:-1]) if y >= 2026 and pp > prev]
        if r:
            xs, ys = r[1]
            for y in recs:
                if y <= 2016 + (2026.9 - 2016) * (0.02 + 0.98 * p):
                    cv.glow_dot((ax_x(y, 130, 990), ax_y(aa_at(y), 520, 1180)), 7, GOLD, a * 0.7)
        k = eo((t - tr + 0.2) / 0.5)
        if k > 0:
            chip(cv, '2026 年 25 次收盘新高', 330, 440, 30, a * k, col=GOLD)
            cv.text('$348.91', 760, 440, 64, 'sans_bold', gold=True, a=a * k, glow=0.3)
            cv.text('2026.10.29 收盘', 760, 492, 20, 'sans_light', col=GREY, a=a * k)
        k2 = eo((t - WT('h1', '五万亿') + 0.1) / 0.5)
        if k2 > 0:
            cv.text('市值 ≈ $5 万亿', W / 2, 1300, 76, 'serif_black', gold=True, a=a * k2, glow=0.3, scale=1.05 - 0.05 * k2)
        source(cv, '数据：Yahoo Finance 日线（拆股调整）；市值 = 收盘价 × 2026 财年末股数 145.3 亿', a * 0.9, y=1462)
    # ---- h2：盛宴里最著名的股东（伯克希尔股东大会现场）
    t0, t1 = S('h2') - 0.2, S('h3') + 0.1
    a = env(t, t0, t1, 0.5, 0.4)
    if a > 0:
        M.full(cv, 'brk_meeting_2025', t, t0, t1, z0=1.3, z1=1.42, focus=(0.5, 0.45), dark=0.15, a=a, cap='伯克希尔股东大会 · 2025')
        cv.text('BERKSHIRE HATHAWAY', W / 2, 380, 46, 'oswald', col=GOLD_L, a=a * eo((t - t0 - 0.6) / 0.8), track=0.12, shadow=0.8)
    # ---- h3：10 亿股 → 2.28 亿股
    t0, t1 = S('h3') - 0.15, S('h4') + 0.1
    a = env(t, t0, t1, 0.35, 0.35)
    if a > 0:
        p = t - t0
        base = 1260
        k1 = eexp(p / 1.2)
        h1_ = 700 * 1.0099 * k1
        cv.rect(230, base - h1_, 430, base, GOLD * 0.7, a, glow=0.15)
        cv.text('10.1亿股', 330, base - h1_ - 50, 46, 'sans_bold', col=CREAM, a=a * k1)
        cv.text('2018 年峰值', 330, base + 40, 26, 'sans_light', col=GREY, a=a)
        tk = WT('h3', '如今') - t0
        k2 = eexp((p - tk) / 0.9)
        if k2 > 0:
            h2_ = 700 * 0.2279 * k2
            cv.rect(650, base - h2_, 850, base, RED, a, glow=0.15)
            cv.text('2.28亿股', 750, base - h2_ - 50, 46, 'sans_bold', col=CREAM, a=a * k2)
            cv.text('2026 年 6 月', 750, base + 40, 26, 'sans_light', col=GREY, a=a * k2)
        cv.text('伯克希尔持有的苹果股票', W / 2, 400, 36, 'sans_med', col=CREAM, a=a)
        source(cv, '数据：伯克希尔 13F 持仓报告（按 2020 年 1 拆 4 调整）', a, y=1462)
    # ---- h4：9.16 亿股中卖掉约四分之三，套现约 1340 亿美元
    t0, t1 = S('h4') - 0.15, S('h5') + 0.1
    a = env(t, t0, t1, 0.35, 0.35)
    if a > 0:
        p = t - t0
        cv.text('2023 年秋 · 9.16 亿股', W / 2, 360, 40, 'sans_med', col=CREAM, a=a)
        tq = WT('h4', '四分之三') - t0
        rng = np.random.default_rng(4)
        order = rng.permutation(100)
        for i in range(100):
            cx = 190 + (i % 10) * 78; cy = 520 + (i // 10) * 78
            sold = order[i] < 75
            k = eo((p - tq - order[i] * 0.012) / 0.5) if sold else 0
            col = GOLD if not sold else lerp(GOLD, RED, min(k * 2, 1))
            cv.rrect(cx - 28, cy - 28 - 60 * k * 0, cx + 28, cy + 28, 8, col * (0.9 - 0.65 * k), a * (1 - 0.55 * k))
        k3 = eo((t - WT('h4', '一千三百四十亿') + 0.1) / 0.5)
        if k3 > 0:
            cv.text('套现 ≈ $1340亿', W / 2, 1360, 84, 'serif_black', gold=True, a=a * k3, glow=0.3)
        cv.text('卖出约 3/4', W / 2, 1270, 40, 'sans_med', col=RED, a=a * eo((p - tq) / 0.5))
        source(cv, '估算：各季度减持股数 × 当季日均收盘价（税前）', a, y=1462)
    shot_hook_tail(cv, t)


def shot_hook_tail(cv, t):
    import media as M
    # ---- h5：若一股不卖，今天值约 3100 亿美元
    t0, t1 = WT('h4', '假如') - 0.15, S('h6') + 0.1
    a = env(t, t0, t1, 0.35, 0.35)
    if a > 0:
        p = t - t0
        cv.text('假如一股不卖', W / 2, 560, 44, 'sans_med', col=CREAM, a=a)
        k = eo((t - WT('h4', '三千一百亿') + 0.1) / 0.4)
        if k > 0:
            v = counter(1340, 3100, t, WT('h4', '三千一百亿') - 0.1, 1.0, lambda v: f'${v:,.0f}亿')
            cv.text(v, W / 2, 800, 200, 'sans_bold', gold=True, a=a * k, glow=0.35, scale=0.94 + 0.06 * k)
        cv.text('9.16亿股 × $338.32（2026.11.02 收盘）', W / 2, 990, 30, 'sans_light', col=GREY, a=a * eo((p - 1.0) / 0.5))
    # ---- h6：他是沃伦·巴菲特
    t0, t1 = S('h6') - 0.2, CH['title'][0] + 0.1
    a = env(t, t0, t1, 0.6, 0.15)
    if a > 0:
        M.full(cv, 'x_bwbi_a', t, t0, t1, z0=1.0, z1=1.08, focus=(0.42, 0.45), dark=0.05, a=a)
        k = eo((t - WT('h6', '沃伦') + 0.1) / 0.7)
        cv.text('WARREN BUFFETT', W / 2, 950, 60, 'corm', col=GOLD_L, a=a * k, track=0.2, shadow=0.8)
        k2 = eo((t - WT('h6', '卖错了吗') + 0.1) / 0.6)
        if k2 > 0:
            cv.text('他卖错了吗？', W / 2, 1120, 96, 'serif_black', gold=True, a=a * k2, shadow=0.8, glow=0.3)
        sink = eio((t - E('h6') - 0.2) / 1.0)
        if sink > 0: cv.dim(1 - 0.4 * sink)


# ------------------------------------------------------------------ 标题：苹果官方 logo（Wikimedia 公有领域矢量图，商标归 Apple Inc.）
_alog = {}
def apple_logo(cv, t, cx, cy, hgt, a, sweep_t0=0.0, scale=1.0):
    if a <= 0.004: return
    h = int(hgt * scale)
    if h not in _alog:
        m = cv2.imread(os.path.join(ROOT, 'assets', 'media', 'apple_logo_alpha.png'), 0).astype(np.float32) / 255
        w = int(m.shape[1] * h / m.shape[0]); m = cv2.resize(m, (w, h), interpolation=cv2.INTER_AREA)
        yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]; xx = np.linspace(0, 1, w, dtype=np.float32)[None, :]
        base = 0.93 - 0.32 * yy + 0.06 * np.cos((xx - 0.35) * 3.0)              # 银色金属：上亮下暗，带一点横向起伏
        rgb = np.stack([base * 0.97, base * 0.98, base * 1.02], -1)
        _alog[h] = (m, np.clip(rgb, 0, 1))
    m, rgb = _alog[h]
    hh, ww = m.shape
    x0, y0 = cx - ww / 2, cy - hh / 2
    halo = cv2.GaussianBlur(np.pad(m, 80), (0, 0), 40) * 0.55 * a
    cv.add(np.array([0.85, 0.9, 1.0], np.float32), halo, x0 - 80, y0 - 80, glow=0.6)
    col = rgb.copy()
    u = (t - sweep_t0) / 1.2
    if 0 <= u <= 1:                                                              # 斜向流光扫过
        xs = np.arange(ww)[None, :] + np.arange(hh)[:, None] * 0.5
        pos = -200 + u * (ww + 500)
        col = np.clip(col + np.exp(-((xs - pos) / 60) ** 2)[..., None] * 0.55, 0, 1.3)
    cv.over(col, m * a, x0, y0)
    cv._glow(col, m * a * 0.15, x0, y0)


# ------------------------------------------------------------------ 标题：玻璃苹果（旧版，已停用）
def apple_layer(cv, t, a=1.0, rot=0.0, camd=6.2, camy=1.5, shift=(0.0, 0.0), ex=1.0, fillk=0.6):
    if a <= 0.004: return
    b = sh('APPLE')(t=t, rot=rot, camd=camd, camy=camy, shift=shift, ex=ex, tint=(0.85, 0.18, 0.14), glass_a=1.0,
                    floorr=1.0, fillk=fillk)
    al = b[..., 3:4] * a
    cv.img = cv.img * (1 - al) + b[..., :3] * a
    cv.glow += np.clip(b[..., :3] * a - 0.55, 0, None) * 0.8


def shot_title(cv, t):
    t0, t1 = CH['title'][0], CH['ch1'][0] + 0.6
    a = env(t, t0, t1, 0.02, 0.6)
    if a <= 0: return
    p = t - t0
    flash = math.exp(-p * 5.0)
    apple_logo(cv, t, W / 2, 740, 560, a * eo(p / 0.35), sweep_t0=t0 + 0.45, scale=1.06 - 0.06 * eo(p / 0.8))
    R = 60 + p * 900
    cv.circle((W / 2, 760), R, GOLD, a * math.exp(-p * 2.2) * 0.8, 3)
    cv.glow_dot((W / 2, 760), 220, GOLD, a * flash * 0.9)
    k = eo((p - 0.15) / 0.6)
    cv.text('十年苹果', W / 2, 1260, 170, 'serif_black', gold=True, a=a * k, glow=0.3, scale=1.08 - 0.08 * k)
    cv.text('巴菲特为什么卖掉了大半', W / 2, 1430, 60, 'serif_semi', col=CREAM, a=a * eo((p - 0.5) / 0.6))
    cv.text('TEN YEARS OF APPLE', W / 2, 1530, 26, 'corm', col=GOLD, a=a * eo((p - 1.0) / 0.6), track=0.35)


# ------------------------------------------------------------------ 片尾：粒子汇聚成官方 logo
_end = {}
TEASE_L1, TEASE_L2 = '日本五大商社', '巴菲特为什么在东京下注？'
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
    ka = env(t, ts - 0.05, t_dis + 0.15, 0.6, 0.45)          # 上一镜头在 ts 前已淡出，不叠化
    if ka > 0.004:                                           # 下期预告的画面：东京丸之内街景
        import media as M
        pass
    if ka > 0.004:
        chip(cv, '下期预告', W / 2, 615, 26, ka, col=GOLD)
        cv.text(TEASE_L1, W / 2, TEASE_Y1, 76, 'serif_black', gold=True, a=ka, shadow=0.6, glow=0.12)
        k2 = eo((t - WT('tease', '巴菲特为什么') + 0.1) / 0.5)
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
    # 4) 下方一道细金线 → 整句品牌金渐变关注语 → 流光扫过（之后整体连同角标淡出，见 film.py）
    la2 = eo((t - hit - 1.4) / 0.8)
    if la2 > 0:
        Lw = 300 * la2
        cv.line((W / 2 - Lw, 1238), (W / 2 + Lw, 1238), GOLD_D, la2, 2)
        cv.glow_dot((W / 2 - Lw, 1238), 6, GOLD_L, la2 * 0.8); cv.glow_dot((W / 2 + Lw, 1238), 6, GOLD_L, la2 * 0.8)
        fa = eo((t - hit - 1.9) / 0.7)
        if fa > 0:
            gold_line_text(cv, t, '关注「巴芒价值」，传承大师智慧，领悟投资真谛', W / 2, 1300, 36, fa, hit + 2.7)


_gt = {}
def gold_line_text(cv, t, txt, x, y, size, a, shimmer_t0, fnt='serif_semi'):
    """整句品牌金：竖向渐变（brand SPEC 的 GOLD_STOPS）+ 一次 1.4s 斜向流光，与品牌字同一套质感"""
    k = (txt, size, fnt)
    if k not in _gt:
        m, base, w, h = text_mask(txt, fnt, size, 0.04)
        asc, _ = font(fnt, size).getmetrics()
        ys, = np.nonzero(m.max(1) > 0.01)
        g = grad_rgb(m.shape[0], GOLD_STOPS)
        gg = grad_rgb(ys[-1] - ys[0] + 1, GOLD_STOPS)
        g[ys[0]:ys[-1] + 1] = gg; g[:ys[0]] = gg[0]; g[ys[-1] + 1:] = gg[-1]
        _gt[k] = (m, np.repeat(g[:, None, :], m.shape[1], 1), w, base - asc * 0.40)
    m, col, w, yc = _gt[k]
    x0, y0 = x - w / 2, y - yc
    u = (t - shimmer_t0) / BRAND_SPEC['shimmer_dur']
    if 0 <= u <= 1:
        xs = np.arange(m.shape[1])[None, :] + np.arange(m.shape[0])[:, None] * 0.6
        pos = -60 + (0.5 - 0.5 * math.cos(u * math.pi)) * (m.shape[1] + 120)
        col = np.clip(col + np.exp(-((xs - pos) / 30) ** 2)[..., None] * 0.6, 0, 1.3)
    sh_ = cv2.GaussianBlur(m, (0, 0), 3) * 0.6 * a
    cv.img_mul(1 - sh_, x0 + 2, y0 + 3)
    cv.over(col, m * a, x0, y0)
    cv._glow(col, m * a * 0.12, x0, y0)


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


# ------------------------------------------------------------------ 分镜辅助：按旁白句子取时间窗
ORDER = [s['id'] for s in TL['segs']]
def nxt(i): return ORDER[ORDER.index(i) + 1] if ORDER.index(i) + 1 < len(ORDER) else None


def win(i, j=None, pre=0.3, post=0.12):
    """镜头从句子 i 发声前 pre 秒开始，到句子 j（缺省为下一句）发声后 post 秒结束"""
    j = j or nxt(i)
    t1 = S(j) + post if j else E(i) + 1.0
    return S(i) - pre, t1


def big_num(cv, t, tw, txt, y, size=170, a=1.0, sub=None, sub_size=32, col=None, dur=0.45):
    k = eo((t - tw + 0.1) / dur)
    if k <= 0: return
    if col is None: cv.text(txt, W / 2, y, size, 'sans_bold', gold=True, a=a * k, glow=0.3, scale=1.06 - 0.06 * k, shadow=0.7)
    else: cv.text(txt, W / 2, y, size, 'sans_bold', col=col, a=a * k, glow=0.2, scale=1.06 - 0.06 * k, shadow=0.7)
    if sub: cv.text(sub, W / 2, y + size * 0.62 + 10, sub_size, 'sans_light', col=CREAM, a=a * eo((t - tw - 0.4) / 0.5), shadow=0.7)


def headline(cv, txt, y, a, size=64, gold=True, col=None, k=1.0):
    if a * k <= 0.004: return
    if gold: cv.text(txt, W / 2, y, size, 'serif_black', gold=True, a=a * k, glow=0.25, shadow=0.8)
    else: cv.text(txt, W / 2, y, size, 'serif_black', col=col or CREAM, a=a * k, shadow=0.8)


def bars(cv, items, t, t0, a, x0=140, x1=940, base=1250, hmax=640, fmt=None, stagger=0.9, dur=1.2, label_size=28):
    """简单柱状对比：items = [(标签, 数值, 颜色, 出现时刻或 None)]"""
    vmax = max(v for _, v, _, _ in items)
    n = len(items); bw = (x1 - x0) / n * 0.55
    for k, (lab, v, col, tk) in enumerate(items):
        ts = t0 + k * stagger if tk is None else tk
        e = eexp((t - ts) / dur)
        if e <= 0: continue
        cx = x0 + (x1 - x0) * (k + 0.5) / n
        h = hmax * v / vmax * e
        cv.rect(cx - bw / 2, base - h, cx + bw / 2, base, col, a * 0.92, glow=0.12)
        cv.text(fmt(v * e) if fmt else f'{v * e:,.0f}', cx, base - h - 44, 44, 'sans_bold', col=CREAM, a=a * min(e * 2, 1), shadow=0.6)
        cv.text(lab, cx, base + 40, label_size, 'sans_light', col=GREY, a=a * min(e * 2, 1))


# ------------------------------------------------------------------ 正片中途关注语胶囊条（参考 claude/festive-brown-49d0no 的做法）
FOLLOW_DUR, FOLLOW_FADE = 4.5, 0.4


def _follow_schedule():
    """在句子说完的时刻浮出：第一章开播 50s 后开始，约每 150s 一次，最多 4 次；避开本章要点卡与章节卡"""
    ends = sorted(s['start'] + s['dur'] for s in TL['segs'] if s['id'] != 'tease')
    b0, b1 = CH['ch1'][0] + 50, CH['end'][0] - 25
    busy = [(v[0] - 1, v[1] + 1) for k, v in CH.items() if k.startswith('tk_')] + \
           [(CH[c][0] - 1, CH[c][0] + 3) for c in ('ch2', 'ch3', 'ch4', 'ch5')]
    ok = lambda e: b0 <= e <= b1 and not any(a <= e <= b or a <= e + FOLLOW_DUR <= b for a, b in busy)
    out = []
    for e in ends:
        if ok(e) and (not out or e - out[-1] >= 150): out.append(e)
    return out[:4]


FOLLOWS = _follow_schedule()


def follow_pill(cv, t):
    for t0 in FOLLOWS:
        if not (t0 <= t < t0 + FOLLOW_DUR): continue
        last = t0 == FOLLOWS[-1]
        a = env(t, t0, t0 + FOLLOW_DUR, FOLLOW_FADE, FOLLOW_FADE)
        dy = 16 * (1 - eo((t - t0) / FOLLOW_FADE))
        lg = 52
        t1, t2 = '关注 @巴芒价值', '传承大师智慧，领悟投资真谛'
        tw = max(text_size(t1, 'sans_med', 32)[0], text_size(t2, 'sans_light', 22)[0] if last else 0)
        w, h = 22 + lg + 16 + tw + 34, (100 if last else 78)
        x1 = W - 40; x0 = x1 - w; yc = 1750 + dy
        cv.rrect(x0, yc - h / 2, x1, yc + h / 2, h / 2, (0.03, 0.035, 0.06), a * 0.78)
        cv.rrect(x0, yc - h / 2, x1, yc + h / 2, h / 2, GOLD_D, a * 0.55, fill=False, th=2)
        rgb, al = logo(lg)
        cv.over(rgb, al * a, x0 + 22, yc - lg / 2)
        tx = x0 + 22 + lg + 16
        if last:
            cv.text(t1, tx, yc - 16, 32, 'sans_med', col=WHITE, a=a, anchor='l')
            cv.text(t2, tx, yc + 22, 22, 'sans_light', col=GOLD_L, a=a, anchor='l')
        else:
            cv.text(t1, tx, yc, 32, 'sans_med', col=WHITE, a=a, anchor='l')


# ------------------------------------------------------------------ 冲印照片：小尺寸的新闻老照片不硬撑满画窗，做成带白边的相片（轻微倾斜、缓慢推近、投影）
_prints = {}
def print_photo(cv, name, t, t0, t1, cx, cy, h, a=1.0, tilt=0.0, cap=None):
    import media as M
    al = env(t, t0, t1, 0.5, 0.4) * a
    if al <= 0.004: return
    if name not in _prints:
        src = M.img(name)
        if src is None: _prints[name] = None; return
        w = int(round(src.shape[1] * h / src.shape[0]))
        im = cv2.resize(src, (w, h), interpolation=cv2.INTER_LANCZOS4)
        im = np.clip(im + 0.55 * (im - cv2.GaussianBlur(im, (0, 0), 1.6)), 0, 1)          # 放大后轻度锐化
        im = np.clip((im - 0.5) * 1.05 + 0.5, 0, 1)
        b = 16
        card = np.ones((h + 2 * b, w + 2 * b, 3), np.float32) * np.float32([0.94, 0.92, 0.87])
        card[b:b + h, b:b + w] = im
        _prints[name] = card
    card = _prints[name]
    if card is None: return
    p = eio((t - t0) / max(t1 - t0, 1e-3))
    s = lerp(1.0, 1.04, p) * (0.97 + 0.03 * eo((t - t0) / 0.6))
    ch, cw = card.shape[:2]; D = int(math.hypot(ch, cw) * 1.1) + 40
    Mx = cv2.getRotationMatrix2D((cw / 2, ch / 2), tilt, s); Mx[0, 2] += D / 2 - cw / 2; Mx[1, 2] += D / 2 - ch / 2
    rgb = cv2.warpAffine(card, Mx, (D, D), flags=cv2.INTER_LINEAR)
    alp = cv2.warpAffine(np.ones((ch, cw), np.float32), Mx, (D, D), flags=cv2.INTER_LINEAR)
    x0, y0 = cx - D / 2, cy - D / 2
    sh = cv2.GaussianBlur(alp, (0, 0), 16) * 0.65 * al
    cv.img_mul(1 - sh, x0 + 8, y0 + 18)
    cv.over(rgb, alp * al, x0, y0)
    txt = ((cap + ' · ') if cap else '') + M.credit_text(name)
    cv.text(txt, cx, cy + ch * s / 2 + 42, 22, 'sans_light', col=(0.66, 0.64, 0.6), a=al * 0.95)
