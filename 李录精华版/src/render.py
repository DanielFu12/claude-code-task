"""《李录 · 哥大演讲精华》9:16 竖屏渲染（1080×1920 · 30fps）。

版式（自上而下）:
  0–110     右上角官方角标 brand.Hud（全程），左上角系列标签
  160–200   九章进度条（顶部分区导航，当前章高亮并显示本章进度）
  225–425   当前章节：CHAPTER 编号 + 金色中文章名 + 英文章名
  452–1532  原片画面：按镜头人脸位置裁出 1:1 方形，放大到 1080×1080
  1572–1850 中英双语字幕
片头为九章导览；每章前有 3 秒章节卡；片尾为品牌动画（粒子汇聚成官方 logo → 重拍出字 → 流光 → 关注语 → 淡出）。

用法:
  python3 render.py stills <out_dir> <t1> <t2> ...     # 抽帧检查（成片时间，秒）
  python3 render.py chunk <f0> <f1> <out.mp4>          # 渲染一段帧（无声），build.sh 并行调用
环境变量 LILU_SRC 指向原片 mp4，LILU_WORK 指向工作目录（默认 ../work）。
"""
import json, math, os, subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, '..', 'brand'))
import edl
# 品牌：角标、logo、金色、字体、流光参数一律取自仓库 brand/（规范见 brand/BRAND.md）
from brand import Hud, load_logo, SPEC, GOLD_STOPS, SUB_GOLD, _ramp, _font as brand_font

W, H, FPS = 1080, 1920, edl.FPS
SRC = os.environ.get('LILU_SRC', os.path.join(edl.WORK, 'orig.mp4'))
ASR = os.path.join(HERE, 'youtube_asr.en.json3')
ITEMS, CUES, TOTAL = edl.load(ASR)
LONG_LAST_CLIP = [it for it in ITEMS if it['kind'] == 'clip'][-1]    # 长片最后一个片段（片尾粒子取自它的末帧）
# 拆分版：LILU_SPLIT=章号 → 本章章节卡 + 本章正片 + 片尾；顶部去掉九章导航，首行下移
SPLIT = int(os.environ.get('LILU_SPLIT', '0'))
SPLIT_TOP = int(os.environ.get('LILU_SPLIT_TOP', '72'))           # 拆分版首行（标签、角标）距顶边
LONG_OUTRO_T0 = None
_lo = [it for it in ITEMS if it['kind'] == 'outro'][0]
LONG_OUTRO_F0, LONG_TOTAL = _lo['f0'], TOTAL                     # 长片片尾首帧帧号、长片总长
if SPLIT:
    ITEMS, CUES, TOTAL, LONG_OUTRO_T0 = edl.load_chapter(ASR, SPLIT)
SHOTS = json.load(open(os.path.join(edl.WORK, 'shots.json')))
NFRAMES = int(round(TOTAL * FPS))

HUD = Hud(scale=1.0, frame_w=W)
if SPLIT: HUD.y0 = SPLIT_TOP                                      # 官方角标整体下移（组件本身不改）
GLOW_RGB = np.array(SPEC['glow_rgb'], np.float32) / 255
SUBG = np.array(SUB_GOLD, np.float32) / 255
GOLD_HI = np.array(GOLD_STOPS[1][1], np.float32) / 255
WHITE = np.array((245, 240, 228), np.float32) / 255
GREY = np.array((176, 170, 158), np.float32) / 255
DIM = np.array((96, 92, 86), np.float32) / 255

VY, VS = 452, 1080                     # 画面区域：y 起点、边长
AY, AH, AW = 136, 808, 1440            # 原片有效画面
SUB_Y = 1572
SUB_BASE0 = 80                         # 字幕图层内首行基线

# ---------------------------------------------------------------- 字体与文字
FONT_DIR = os.path.join(ROOT, 'fonts')
_fc = {}
def font(name, size):
    k = (name, size)
    if k not in _fc:
        if name in ('serif_black', 'corm'):
            _fc[k] = brand_font(name, size)            # 品牌字体：思源宋体 Black / Cormorant Garamond
        else:
            _fc[k] = ImageFont.truetype(os.path.join(FONT_DIR, name + '.ttf'), size)
    return _fc[k]

_tc = {}
def text_mask(s, name, size, track=0.0):
    """返回 (alpha[h,w] float32, baseline_y)；track 为字距（相对字号）"""
    k = (s, name, size, track)
    if k in _tc: return _tc[k]
    f = font(name, size)
    widths = [f.getlength(c) for c in s]
    tw = int(sum(widths) + track * size * max(0, len(s) - 1) + size)
    asc, desc = f.getmetrics()
    im = Image.new('L', (tw + 8, asc + desc + 8), 0)
    d = ImageDraw.Draw(im)
    x = 4
    for c, w in zip(s, widths):
        d.text((x, 4 + asc), c, font=f, fill=255, anchor='ls'); x += w + track * size
    a = np.asarray(im, np.float32) / 255
    cols = np.where(a.max(0) > 0.01)[0]
    a = a[:, cols.min():cols.max() + 1] if len(cols) else a[:, :1]
    _tc[k] = (a, 4 + asc)
    return _tc[k]

def text_width(s, name, size, track=0.0):
    return text_mask(s, name, size, track)[0].shape[1]

def fit_size(s, name, size, maxw, track=0.0, minsize=30):
    while size > minsize and text_width(s, name, size, track) > maxw: size -= 2
    return size

def gold_rgb(h):
    return _ramp(h, GOLD_STOPS).astype(np.float32)[:, None, :]      # 品牌金色竖向渐变

def blend(img, a, rgb, x, y, alpha=1.0):
    """img float32 H×W×3；a 为 alpha 蒙版；rgb 为颜色(3,) 或同尺寸图；(x,y) 左上角"""
    if alpha <= 0.003: return
    h, w = a.shape
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(img.shape[1], x + w), min(img.shape[0], y + h)
    if x1 <= x0 or y1 <= y0: return
    aa = a[y0 - y:y1 - y, x0 - x:x1 - x][..., None] * alpha
    c = rgb if np.ndim(rgb) == 1 else rgb[y0 - y:y1 - y, x0 - x:x1 - x] if rgb.shape[1] > 1 else rgb[y0 - y:y1 - y]
    reg = img[y0:y1, x0:x1]
    reg *= (1 - aa); reg += aa * c

def put_text(img, s, name, size, x, y, col, alpha=1.0, track=0.0, anchor='l', gold=False):
    """y 为文字基线；anchor: l / m / r"""
    a, base = text_mask(s, name, size, track)
    w = a.shape[1]
    xx = x if anchor == 'l' else x - w // 2 if anchor == 'm' else x - w
    rgb = gold_rgb(a.shape[0]) if gold else col
    blend(img, a, rgb, int(xx), int(y - base), alpha)
    return xx, w

PUNCT = '，、；：。！？—'
def wrap_zh(s, name, size, maxw):
    """中文换行：cues.txt 中的 / 为人工断行；否则在最均衡且放得下的标点处断开；都不行再逐字换行"""
    if '/' in s:
        return [x for p in s.split('/') for x in wrap_zh(p, name, size, maxw)]
    if text_width(s, name, size) <= maxw: return [s]
    cands = [i + 1 for i, c in enumerate(s[:-1]) if c in PUNCT
             and text_width(s[:i + 1], name, size) <= maxw and text_width(s[i + 1:], name, size) <= maxw]
    if cands:
        k = min(cands, key=lambda i: abs(text_width(s[:i], name, size) - text_width(s[i:], name, size)))
        return [s[:k], s[k:]]
    lines, cur = [], ''
    for c in s:
        if text_width(cur + c, name, size) > maxw and cur:
            if c in '，。、；：！？」』）》,.;:!?)' :          # 标点不放行首
                cur, c = cur[:-1], cur[-1] + c
            lines.append(cur); cur = c
        else: cur += c
    if cur: lines.append(cur)
    return lines

def wrap_en(s, name, size, maxw):
    lines, cur = [], ''
    for w in s.split():
        t = (cur + ' ' + w).strip()
        if text_width(t, name, size) > maxw and cur: lines.append(cur); cur = w
        else: cur = t
    if cur: lines.append(cur)
    return lines

# ---------------------------------------------------------------- 缓动
def cl(x): return min(1.0, max(0.0, x))
def eo(x): x = cl(x); return 1 - (1 - x) ** 3
def eio(x): x = cl(x); return 3 * x * x - 2 * x ** 3
def env(t, a, b, fi, fo): return cl((t - a) / fi) * cl((b - t) / fo) if fi > 0 and fo > 0 else float(a <= t < b)

# ---------------------------------------------------------------- 背景与固定版式（每章预渲染一次）
_yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
BG = (np.array((15, 18, 30), np.float32) / 255) * (1 - _yy) + (np.array((6, 7, 12), np.float32) / 255) * _yy
BG = np.repeat(BG, W, axis=1)
_xx = np.linspace(-1, 1, W, dtype=np.float32)[None, :]
_y2 = np.linspace(-1, 1, H, dtype=np.float32)[:, None]
BG += (np.exp(-((_xx / 0.9) ** 2 + ((_y2 + 0.78) / 0.25) ** 2)) * 0.035)[..., None] * GOLD_HI     # 顶部淡金光
BG = BG.astype(np.float32)

def hairline(img, y, alpha=0.55, x0=0, x1=W):
    xs = np.linspace(-1, 1, x1 - x0, dtype=np.float32)
    a = (1 - xs ** 2) ** 1.5 * alpha
    img[y, x0:x1] = img[y, x0:x1] * (1 - a[:, None]) + a[:, None] * SUBG

PB_Y, PB_H, PB_X0, PB_X1, PB_GAP = 168, 6, 52, 1028, 10
PB_W = (PB_X1 - PB_X0 - PB_GAP * 8) / 9
def slot_x(i): return int(PB_X0 + i * (PB_W + PB_GAP))

_chrome = {}
def chrome(ch):
    """固定版式：背景、左上标签、进度条（不含当前章的进度填充）、章节标题、细金线、出处"""
    if ch in _chrome: return _chrome[ch]
    img = BG.copy()
    if SPLIT:   # 拆分版：首行与下移后的角标上下对齐（角标文字区 y0+8 … y0+60）
        put_text(img, '李录 · 哥大演讲精华', 'sans_med', 30, 52, SPLIT_TOP + 34, WHITE)
        put_text(img, '第 36 届格雷厄姆-多德年度午餐会 · 2026', 'sans_reg', 20, 52, SPLIT_TOP + 66, GREY, 0.9)
        zh, en = edl.CHAPTERS[ch]
        put_text(img, zh, 'serif_black', fit_size(zh, 'serif_black', 66, 976), 52, 344, None, gold=True)
        put_text(img, en, 'latin_reg', fit_size(en, 'latin_reg', 27, 976), 52, 394, GREY, 0.9)
        hairline(img, 426, 0.5, 52, 1028)
        hairline(img, VY - 1, 0.6); hairline(img, VY + VS, 0.6)
        _chrome[ch] = img
        return img
    put_text(img, '李录 · 哥大演讲精华', 'sans_med', 30, 52, 66, WHITE)
    put_text(img, '第 36 届格雷厄姆-多德年度午餐会 · 2026', 'sans_reg', 20, 52, 100, GREY, 0.9)
    for i in range(9):
        x = slot_x(i)
        col, al = (SUBG, 0.85) if ch and i + 1 < ch else (DIM, 0.55)
        if ch == i + 1: col, al = (DIM, 0.8)
        img[PB_Y:PB_Y + PB_H, x:int(x + PB_W)] = img[PB_Y:PB_Y + PB_H, x:int(x + PB_W)] * (1 - al) + col * al
        cur = ch == i + 1
        put_text(img, f'{i + 1:02d}', 'serif_semi', 22 if cur else 19, x + PB_W / 2, PB_Y + 38,
                 GOLD_HI if cur else (SUBG if ch and i + 1 < ch else GREY), 1.0 if cur else 0.6, anchor='m')
    if ch:
        zh, en = edl.CHAPTERS[ch]
        put_text(img, f'CHAPTER {ch:02d}', 'latin_reg', 24, 52, 262, SUBG, track=0.2)
        put_text(img, '/ 09', 'latin_reg', 24, 52 + text_width(f'CHAPTER {ch:02d}', 'latin_reg', 24, 0.2) + 14, 262, GREY, 0.6, track=0.2)
        sz = fit_size(zh, 'serif_black', 66, 976)
        put_text(img, zh, 'serif_black', sz, 52, 344, None, gold=True)
        put_text(img, en, 'latin_reg', fit_size(en, 'latin_reg', 27, 976), 52, 394, GREY, 0.9)
    else:
        put_text(img, 'OVERVIEW', 'latin_reg', 24, 52, 262, SUBG, track=0.2)
        put_text(img, '九个主题 · 精华导览', 'serif_black', 66, 52, 344, None, gold=True)
        put_text(img, 'Li Lu at the 36th Annual Graham & Dodd Event, Columbia Business School', 'latin_reg', 24, 52, 394, GREY, 0.9)
    hairline(img, 426, 0.5, 52, 1028)
    hairline(img, VY - 1, 0.6); hairline(img, VY + VS, 0.6)
    _chrome[ch] = img
    return img

def draw_progress(img, ch, p, a=1.0):
    if not ch or SPLIT: return
    x = slot_x(ch - 1)
    w = int(PB_W * cl(p))
    if w > 0:
        reg = img[PB_Y:PB_Y + PB_H, x:x + w]
        reg[:] = reg * (1 - a) + GOLD_HI * a
        if w > 2:   # 进度头部一点亮光
            img[PB_Y - 2:PB_Y + PB_H + 2, x + w - 2:x + w] = img[PB_Y - 2:PB_Y + PB_H + 2, x + w - 2:x + w] * (1 - a) + 1.0 * a

# ---------------------------------------------------------------- 原片读取
class Reader:
    """顺序读取原片有效画面（rgb24, 1440×808），按需从 src_t 处重新定位"""
    def __init__(self): self.p = None; self.t = None
    def get(self, src_t):
        n = AW * AH * 3
        if self.p is None or self.t is None or abs(src_t - self.t) > 0.5 / FPS:
            self.close()
            self.p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-ss', f'{src_t:.4f}', '-i', SRC,
                                       '-vf', f'crop={AW}:{AH}:0:{AY}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                                      stdout=subprocess.PIPE, bufsize=n * 2)
            self.t = src_t
        b = self.p.stdout.read(n)
        self.t += 1 / FPS
        if len(b) < n: return None
        return np.frombuffer(b, np.uint8).reshape(AH, AW, 3)
    def close(self):
        if self.p: self.p.kill(); self.p.wait(); self.p = None

def build_track(clip, dead=90.0, vmax=140.0, k=2.2):
    """逐帧裁切位置：镜头内跟随人脸（死区 + 限速平滑），切镜头时直接跳到新镜头的位置"""
    n = int(round((clip['src1'] - clip['src0']) * FPS)) + 2
    ts = clip['src0'] + np.arange(n) / FPS
    fx = np.array(clip.get('faces') or [], np.float32).reshape(-1, 3)
    cuts = [s['t'] for s in clip['shots']] + [clip['src1'] + 1]
    out = np.zeros(n, np.float32)
    for si, s in enumerate(clip['shots']):
        a, b = cuts[si], cuts[si + 1]
        m = (ts >= a - 1e-3) & (ts < b)
        f = fx[(fx[:, 0] >= a) & (fx[:, 0] < b)] if len(fx) else fx
        if len(f) >= 2:
            # 中值滤波去掉误检，再插值到逐帧
            xs = np.array([np.median(f[max(0, i - 3):i + 4, 1]) for i in range(len(f))], np.float32)
            tgt = np.interp(ts[m], f[:, 0], xs)
        else:
            tgt = np.full(m.sum(), s['cx'], np.float32)
        c = s['cx'] if s['cx'] is not None else tgt[0]
        c = float(np.median(tgt[:45])) if len(tgt) else c
        v = 0.0; res = []
        for g in tgt:
            e = g - c
            want = 0.0 if abs(e) < dead else (e - math.copysign(dead * 0.5, e)) * k
            want = max(-vmax, min(vmax, want))
            v += (want - v) * 0.12
            c += v / FPS
            res.append(c)
        out[m] = res
    return np.clip(np.round(out - AH / 2), 0, AW - AH).astype(int)

TRACKS = [build_track(c) for c in SHOTS]

def shot_x0(src_t):
    for clip, tr in zip(SHOTS, TRACKS):
        if clip['src0'] - 0.1 <= src_t <= clip['src1'] + 0.1:
            return int(tr[min(len(tr) - 1, max(0, int(round((src_t - clip['src0']) * FPS))))])
    return (AW - AH) // 2

def square(frame, src_t):
    x0 = shot_x0(src_t)
    sq = frame[:, x0:x0 + AH]
    return cv2.resize(sq, (VS, VS), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255

_still = {}
def still(src_t):
    k = round(src_t, 3)
    if k not in _still:
        p = subprocess.run(['ffmpeg', '-loglevel', 'error', '-ss', f'{src_t:.4f}', '-i', SRC, '-frames:v', '1',
                            '-vf', f'crop={AW}:{AH}:0:{AY}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True)
        _still[k] = square(np.frombuffer(p.stdout[:AW * AH * 3], np.uint8).reshape(AH, AW, 3), src_t)
    return _still[k]

def soft(img, k):
    """暗化 + 模糊（章节卡背景）"""
    small = cv2.resize(img, (VS // 4, VS // 4), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), 6)
    return cv2.resize(small, (VS, VS), interpolation=cv2.INTER_LINEAR) * k

# ---------------------------------------------------------------- 字幕
SPEAKER = {'L': ('李录', '喜马拉雅资本创始人、董事长'), 'Q': ('塔诺', '哥大商学院教授 · 主持人')}
_sc = {}
def cue_layer(i):
    """预渲染一条字幕 → (alpha, rgb, y0)"""
    if i in _sc: return _sc[i]
    c = CUES[i]
    zl = wrap_zh(c['zh'], 'sans_med', 50, 960)
    el = wrap_en(c['en'], 'latin_reg', 29, 990)
    hgt = SUB_BASE0 + len(zl) * 68 + 16 + len(el) * 40 + 30
    a = np.zeros((hgt, W), np.float32); rgb = np.zeros((hgt, W, 3), np.float32)
    y = SUB_BASE0
    for ln in zl:
        m, base = text_mask(ln, 'sans_med', 50)
        x = (W - m.shape[1]) // 2
        yy = y - base
        a[yy:yy + m.shape[0], x:x + m.shape[1]] = np.maximum(a[yy:yy + m.shape[0], x:x + m.shape[1]], m)
        rgb[yy:yy + m.shape[0], x:x + m.shape[1]] = WHITE
        y += 68
    y += 4
    for ln in el:
        m, base = text_mask(ln, 'latin_reg', 29)
        x = (W - m.shape[1]) // 2
        yy = y - base
        a[yy:yy + m.shape[0], x:x + m.shape[1]] = np.maximum(a[yy:yy + m.shape[0], x:x + m.shape[1]], m)
        rgb[yy:yy + m.shape[0], x:x + m.shape[1]] = GREY
        y += 40
    _sc[i] = (a, rgb)
    if len(_sc) > 40: _sc.pop(next(iter(_sc)))
    return _sc[i]

def draw_subs(img, t):
    for i, c in enumerate(CUES):
        if c['o0'] - 0.1 <= t < c['o1'] + 0.12:
            al = cl((t - c['o0'] + 0.1) / 0.12) * cl((c['o1'] + 0.12 - t) / 0.12)
            a, rgb = cue_layer(i)
            blend(img, a, rgb, 0, SUB_Y + 36 - SUB_BASE0, al)      # 首行中文基线在 SUB_Y + 36

_tagc = {}
def speaker_tag(img, spk, a):
    if a <= 0.003: return
    if spk not in _tagc:
        name, role = SPEAKER[spk]
        m1, b1 = text_mask(name, 'sans_bold', 30); m2, b2 = text_mask(role, 'sans_reg', 23)
        w = 28 + m1.shape[1] + 18 + 2 + 18 + m2.shape[1] + 28; h = 58
        al = np.zeros((h, w), np.float32); rgb = np.zeros((h, w, 3), np.float32)
        r = 10
        box = np.zeros((h, w), np.uint8); cv2.rectangle(box, (r, 0), (w - r, h), 255, -1); cv2.rectangle(box, (0, r), (w, h - r), 255, -1)
        for cx, cy in ((r, r), (w - r - 1, r), (r, h - r - 1), (w - r - 1, h - r - 1)): cv2.circle(box, (cx, cy), r, 255, -1, cv2.LINE_AA)
        al[:] = box / 255 * 0.62; rgb[:] = (0.03, 0.035, 0.06)
        def put(m, base, x, col):
            y = 29 + (base - m.shape[0] / 2) - base + int(m.shape[0] * 0.0)
            y = int((h - m.shape[0]) / 2)
            reg = al[y:y + m.shape[0], x:x + m.shape[1]]
            rgb[y:y + m.shape[0], x:x + m.shape[1]] = rgb[y:y + m.shape[0], x:x + m.shape[1]] * (1 - m[..., None]) + m[..., None] * col
            al[y:y + m.shape[0], x:x + m.shape[1]] = np.maximum(reg, m)
        put(m1, b1, 28, GOLD_HI)
        xs = 28 + m1.shape[1] + 18
        al[16:h - 16, xs:xs + 2] = 0.8; rgb[16:h - 16, xs:xs + 2] = SUBG
        put(m2, b2, xs + 20, WHITE)
        _tagc[spk] = (al, rgb)
    al, rgb = _tagc[spk]
    blend(img, al, rgb, 40, VY + VS - 40 - al.shape[0], a)

# ---------------------------------------------------------------- 片头 / 章节卡
def intro(img, t, bg):
    img[VY:VY + VS] = soft(bg, 0.32 * eo(t / 0.8) + 0.08)
    a = env(t, 0.15, 6.0, 0.6, 0.55)
    cx = W // 2
    put_text(img, 'COLUMBIA BUSINESS SCHOOL · GRAHAM & DODD', 'corm', 26, cx, VY + 120, SUBG, a * eo((t - 0.2) / 0.6), track=0.16, anchor='m')
    k = eo((t - 0.35) / 0.7)
    put_text(img, '李录：价值投资、AI 与中国', 'serif_black', 64, cx, VY + 215 - 14 * (1 - k), None, a * k, anchor='m', gold=True)
    put_text(img, '2026 哥大格雷厄姆-多德年度午餐会 · 精华版', 'sans_reg', 28, cx, VY + 270, WHITE, a * eo((t - 0.7) / 0.6), anchor='m')
    w = int(620 * eo((t - 0.9) / 0.8))
    if w > 2: hairline(img, VY + 312, 0.8 * a, cx - w // 2, cx + w // 2)
    for i in range(9):
        ti = 1.4 + i * 0.22
        k = eo((t - ti) / 0.45)
        y = VY + 392 + i * 74
        zh = edl.CHAPTERS[i + 1][0]
        put_text(img, f'{i + 1:02d}', 'serif_semi', 32, 150 - 30 * (1 - k), y, GOLD_HI, a * k)
        put_text(img, zh, 'sans_med', 36, 226 - 30 * (1 - k), y, WHITE, a * k)

def card(img, t, ch, bg):
    """章节卡：模糊暗化的首帧 + 大号章节号 + 金色章名；最后 0.5s 画面清晰化，无缝接入正片"""
    clear = eio((t - (edl.CARD - 0.55)) / 0.55)
    base = soft(bg, 0.30) * (1 - clear) + bg * clear
    img[VY:VY + VS] = base
    a = env(t, 0.0, edl.CARD - 0.25, 0.25, 0.4)
    cx, cy = W // 2, VY + VS // 2
    put_text(img, f'{ch:02d}', 'serif_semi', 280, cx, cy - 40, SUBG, a * 0.18 * eo(t / 0.5), anchor='m')
    put_text(img, f'CHAPTER {ch:02d}', 'latin_reg', 26, cx, cy - 120, SUBG, a * eo((t - 0.1) / 0.4), track=0.3, anchor='m')
    zh, en = edl.CHAPTERS[ch]
    k = eo((t - 0.24) / 0.55)                       # 0.24s 处是音乐重拍
    sz = fit_size(zh, 'serif_black', 76, 960)
    put_text(img, zh, 'serif_black', sz, cx, cy + 20 + 18 * (1 - k), None, a * k, anchor='m', gold=True)
    put_text(img, en, 'latin_reg', fit_size(en, 'latin_reg', 30, 960), cx, cy + 80, WHITE, a * 0.85 * eo((t - 0.5) / 0.5), anchor='m')
    w = int(520 * eo((t - 0.4) / 0.7))
    if w > 2: hairline(img, cy + 118, 0.9 * a, cx - w // 2, cx + w // 2)

# ---------------------------------------------------------------- 片尾品牌动画
LOGO_PX = 240
LOGO_RGB, LOGO_A = load_logo(LOGO_PX)                   # 官方 logo：brand/logo_baman.png
LOGO_CY = 760
TITLE_Y, SUB_Y2, LINE_Y, FOLLOW_Y = 1030, 1100, 1168, 1232
import render_consts as RC
HIT = RC.OUTRO_HIT                                      # 片尾音乐重拍（见 render_consts.py）
_rng = np.random.default_rng(7)
_ys, _xs = np.where(LOGO_A > 0.5)
_pick = _rng.choice(len(_ys), 3200, replace=len(_ys) < 3200)
P_TGT = np.stack([_xs[_pick] + W / 2 - LOGO_PX / 2 + _rng.normal(0, .6, len(_pick)),
                  _ys[_pick] + LOGO_CY - LOGO_PX / 2 + _rng.normal(0, .6, len(_pick))], 1).astype(np.float32)
P_TCOL = LOGO_RGB[_ys[_pick], _xs[_pick]].astype(np.float32)
P_DELAY = _rng.uniform(0, 0.7, len(_pick)).astype(np.float32)
P_SWIRL = _rng.uniform(-1.2, 1.2, len(_pick)).astype(np.float32)

def glow_blob(img, cx, cy, sigma, rgb, a):
    r = int(sigma * 3)
    y0, y1, x0, x1 = max(0, cy - r), min(H, cy + r), max(0, cx - r), min(W, cx + r)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    g = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma ** 2)).astype(np.float32)[..., None]
    img[y0:y1, x0:x1] += g * rgb * a

def shimmer_band(a_shape, x_off, u, scale):
    """与 brand.Hud 相同的流光：斜向高光带扫过文字（u: 0..1）"""
    h, w = a_shape
    xs = np.arange(w)[None, :] + x_off + np.arange(h)[:, None] * 0.6
    span = w + 80 * scale
    pos = x_off - 40 * scale + (0.5 - 0.5 * math.cos(u * math.pi)) * span
    return np.exp(-((xs - pos) / (16 * scale)) ** 2)[..., None].astype(np.float32)

def outro(img, t, last):
    # 0–0.8s：画面与版式淡出成深色背景
    fade = eio(t / 0.8)
    img[:] = img * (1 - fade) + BG * fade
    # 粒子：从最后一帧画面的像素出发，汇聚成官方 logo
    if t < 3.8:
        if not hasattr(outro, 'src'):
            ys = _rng.integers(0, VS, len(_pick)); xs = _rng.integers(0, VS, len(_pick))
            outro.src = np.stack([xs, ys + VY], 1).astype(np.float32)
            outro.scol = last[ys, xs].astype(np.float32)
        p = eio((t - 0.15 - P_DELAY) / 2.2)[:, None] if False else np.clip((t - 0.15 - P_DELAY) / 2.2, 0, 1)[:, None]
        p = p * p * (3 - 2 * p)
        ang = P_SWIRL[:, None] * (1 - p) * 1.6
        c = np.array([W / 2, LOGO_CY], np.float32)
        d = (outro.src - c)
        rot = np.concatenate([d[:, :1] * np.cos(ang) - d[:, 1:] * np.sin(ang), d[:, :1] * np.sin(ang) + d[:, 1:] * np.cos(ang)], 1)
        pos = c + rot * (1 - p) + (P_TGT - c) * p
        col = outro.scol * (1 - p) + P_TCOL * p
        pa = cl(t / 0.4) * (1 - eio((t - 2.9) / 0.8))
        if pa > 0.003:
            buf = np.zeros((H, W, 3), np.float32)
            xi = np.clip(pos[:, 0].astype(int), 0, W - 1); yi = np.clip(pos[:, 1].astype(int), 0, H - 1)
            np.add.at(buf, (yi, xi), col * 1.6)
            sharp = cv2.GaussianBlur(buf, (0, 0), 1.1)
            glow = cv2.GaussianBlur(buf, (0, 0), 7)
            img += (sharp * 2.6 + glow * 6.0) * pa
    # 清晰的官方 logo 居中浮现（含品牌淡蓝光晕）
    la = eo((t - 2.7) / 0.9)
    if la > 0:
        glow_blob(img, W // 2, LOGO_CY, 70, GLOW_RGB, SPEC['glow_strength'] * 1.6 * la)
        sc = 1.04 - 0.04 * la
        sz = int(LOGO_PX * sc)
        rgb, a = (LOGO_RGB, LOGO_A) if sz == LOGO_PX else load_logo(sz)
        blend(img, a, rgb, W // 2 - sz // 2, LOGO_CY - sz // 2, la)
    # 重拍：金色「巴芒价值」与「BUFFETT · MUNGER」
    if t >= HIT - 0.02:
        k = eo((t - HIT) / 0.45)
        flash = math.exp(-max(0, t - HIT) / 0.25)
        glow_blob(img, W // 2, TITLE_Y - 40, 260, GOLD_HI, 0.10 * flash)
        title_a, tb = text_mask('巴芒价值', 'serif_black', 116, 0.06)
        tw = title_a.shape[1]
        sub = 'BUFFETT · MUNGER'
        # 小字两端对齐到与主标题等宽（同 brand.build）
        f2 = font('corm', 34); nat = sum(f2.getlength(ch) for ch in sub)
        tr = (tw - nat) / (len(sub) - 1) / 34
        sub_a, sb = text_mask(sub, 'corm', 34, tr)
        x_t = W // 2 - tw // 2
        u = (t - (HIT + 0.6)) / SPEC['shimmer_dur']
        rgb_t = np.repeat(gold_rgb(title_a.shape[0]), tw, 1)
        rgb_s = np.broadcast_to(SUBG, sub_a.shape + (3,)).copy()
        if 0 <= u <= 1:
            rgb_t = np.clip(rgb_t + shimmer_band(title_a.shape, x_t, u, 3.0) * 0.6, 0, 1.25)
            rgb_s = np.clip(rgb_s + shimmer_band(sub_a.shape, W // 2 - sub_a.shape[1] // 2, u, 3.0) * 0.6, 0, 1.25)
        dy = int(26 * (1 - k))
        blend(img, title_a, rgb_t, x_t, TITLE_Y - tb + dy, k)
        ks = eo((t - HIT - 0.18) / 0.45)
        blend(img, sub_a, rgb_s, W // 2 - sub_a.shape[1] // 2, SUB_Y2 - sb + int(16 * (1 - ks)), ks)
    # 细金线引出关注语
    w = int(640 * eio((t - 6.4) / 0.8))
    if w > 2:
        for dy in (0, 1): hairline(img, LINE_Y + dy, 1.0, W // 2 - w // 2, W // 2 + w // 2)
        glow_blob(img, W // 2, LINE_Y, 40, GOLD_HI, 0.05 * eio((t - 6.4) / 0.8))
    kf = eo((t - 7.0) / 0.7)
    if kf > 0:
        put_text(img, '关注「巴芒价值」，传承大师智慧，领悟投资真谛', 'sans_med', 36, W // 2, FOLLOW_Y + int(10 * (1 - kf)), None, kf,
                 anchor='m', gold=True)                          # 品牌金色（brand.GOLD_STOPS 竖向渐变）

# ---------------------------------------------------------------- 主渲染
READER = Reader()

def item_at(f):
    for it in ITEMS:
        if it['f0'] <= f < it['f1']: return it
    return ITEMS[-1]

def next_clip(it):
    k = ITEMS.index(it)
    return next(x for x in ITEMS[k:] if x['kind'] == 'clip')

def chapter_progress(ch, t):
    its = [x for x in ITEMS if x.get('ch') == ch]
    a, b = its[0]['t0'], its[-1]['t1']
    return (t - a) / (b - a)

def render(f):
    t = f / FPS
    it = item_at(f)
    lt = t - it['t0']
    t_hud, t_end = t, TOTAL
    if SPLIT:
        t_hud = t + LONG_OUTRO_T0 - ITEMS[-1]['t0']
        if it['kind'] == 'outro':
            # 片尾按帧号映射到长片片尾的同一帧：动画、角标流光、淡出与长片逐帧同步
            t_hud = (LONG_OUTRO_F0 + f - it['f0']) / FPS
            lt, t, t_end = t_hud - LONG_OUTRO_T0, t_hud, LONG_TOTAL
    ch = it.get('ch', 0) if it['kind'] != 'outro' else 9
    img = chrome(ch).copy()
    # 章节切换：版式 0.5s 交叉淡化
    if it['kind'] == 'card' and lt < 0.5 and not SPLIT:
        k = eio(lt / 0.5)
        img = chrome(ch - 1 if ch > 1 else 0) * (1 - k) + img * k
    if it['kind'] == 'intro':
        intro(img, lt, still(ITEMS[2]['src0']))
    elif it['kind'] == 'card':
        card(img, lt, ch, still(next_clip(it)['src0']))
        draw_progress(img, ch, chapter_progress(ch, t), eio(lt / 0.5))
    elif it['kind'] == 'clip':
        st = it['src0'] + (f - it['f0']) / FPS
        fr = READER.get(st)
        img[VY:VY + VS] = square(fr, st) if fr is not None else 0
        draw_progress(img, ch, chapter_progress(ch, t))
        # 说话人标签：每段开头和换人时显示 5 秒
        cs = [c for c in CUES if c['o0'] <= t + 0.05 and c['ch'] == ch]
        if cs:
            spk = cs[-1]['spk']
            since = cs[-1]['o0']
            for c in reversed(cs):
                if c['spk'] != spk: break
                since = c['o0']
            since = max(since, it['t0'])
            speaker_tag(img, spk, env(t, since + 0.3, since + 5.3, 0.4, 0.5))
        draw_subs(img, t)
    else:   # outro
        draw_progress(img, 9, 1.0)
        if not hasattr(render, 'last'):
            render.last = still(LONG_LAST_CLIP['src1'] - 2 / FPS)    # 与长片相同：取长片最后一帧
        img[VY:VY + VS] = render.last
        outro(img, lt, render.last)
    # 右上角官方角标：全程保留，直到片尾整体淡出
    end_fade = 1 - eio((t - (t_end - 1.5)) / 1.5)
    h = HUD.y0 + HUD.h + HUD.P + 2
    reg = np.clip(img[:h], 0, 1)
    HUD.draw(reg, t_hud, 1.0)                  # 拆分版：流光相位与长片片尾对齐
    img[:h] = reg
    img = np.clip(img, 0, 1)
    fade = cl(f / FPS / 0.5) * end_fade
    return (img * (255 * fade) + 0.5).astype(np.uint8)

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'stills':
        out = sys.argv[2]; os.makedirs(out, exist_ok=True)
        for tt in sys.argv[3:]:
            READER.close()
            img = render(int(round(float(tt) * FPS)))
            cv2.imwrite(os.path.join(out, 'f_%07.2f.png' % float(tt)), img[..., ::-1])
    elif mode == 'chunk':
        a, b, path = int(sys.argv[2]), min(int(sys.argv[3]), NFRAMES), sys.argv[4]
        crf = os.environ.get('LILU_CRF', '18')
        p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                              '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', crf,
                              '-pix_fmt', 'yuv420p', '-threads', '2', path], stdin=subprocess.PIPE)
        for i in range(a, b):
            p.stdin.write(render(i).tobytes())
            if (i - a) % 900 == 0: print(path, i, f'{i / FPS:.1f}s', flush=True)
        p.stdin.close(); p.wait()
    elif mode == 'info':
        print('frames', NFRAMES, 'total', TOTAL)
