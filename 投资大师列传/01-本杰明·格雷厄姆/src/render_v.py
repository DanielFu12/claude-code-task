"""《本杰明·格雷厄姆：安全边际的守门人》竖屏版（1080×1920）逐帧渲染。品牌为 MastersTao（`MastersTao/brand`）。

用法：
  python3 src/render_v.py still <镜头号> <镜头内秒数> out.png
  python3 src/render_v.py at <全片秒数> out.png
  python3 src/render_v.py chunk <起始帧> <结束帧> out.mp4
依赖 work/timeline_v.json（先跑 src/music_v.py）。帧为 float32 RGB 0..1。

版式：顶部系列名 + 章节名（右上品牌角标，整体下移避开手机状态栏）；中部 16:9 清晰画面带，背景为同图放大模糊；
下部黄色大字年份 + 白色字幕（左侧黄条、关键词红色）。
卡点：章节开头闪白 + 放大回弹 + 抖动 + 中央章节大字；普通切镜纵向推移 + 运动模糊；
错误清单故障转场；序章、落幕柔和淡化；强拍上画面轻微脉冲。
"""
import json, math, os, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
REPO = os.path.join(ROOT, "..", "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "MastersTao", "brand"))  # MastersTao 官方品牌（取自 claude/masters-tao-holdings-video-q3crid）
from shots import SHOTS
from mt_brand import Hud, load_logo as mt_logo, PALETTE

W, H, FPS = 1080, 1920, 30
# TL=r 时使用参照片配乐的时间线（src/music_r.py），默认用 Lyria 配乐的时间线（src/music_v.py）
TL = json.load(open(os.path.join(ROOT, "work", "timeline_r.json" if os.environ.get("TL") == "r" else "timeline_v.json")))
T0 = [s["t0"] for s in TL["shots"]]
T1 = [s["t1"] for s in TL["shots"]]
CHN = [s["ch"] for s in TL["shots"]]
HITCUT = {s["i"] for s in TL["shots"] if s.get("hit")}
ENERGY = TL["energy"]
BEATS = np.array(TL["beats"])
DOWNS = np.array(TL["downbeats"])
FIN = TL["finale"]
ANCH = TL["anchors"]
CH_START = {i for i in range(len(SHOTS)) if any(abs(T0[i] - v) < 1e-3 for v in ANCH.values()) and i > 0}
STAMP_T = [e["t"] for e in TL["events"] if e["type"] == "stamp"]
ERR_CH = "格雷厄姆的错误清单"
ERR = [c == ERR_CH for c in CHN]
CH_NO = {n: k for k, n in enumerate(ANCH)}  # 序章=0
CN = "零一二三四五六七八九十"

YELLOW = (1.0, 0.83, 0.0)
RED = (1.0, 0.23, 0.19)
WHITE = (1.0, 1.0, 1.0)
INK = (0.13, 0.13, 0.14)
GOLD_STOPS = [(0.0, (255, 243, 200)), (0.35, (255, 212, 120)), (0.62, (226, 160, 60)), (1.0, (255, 214, 130))]

BAND_Y, BAND_H = 540, 608        # 中部画面带
CAP_Y = 1200                     # 年份大字顶部

# ------------------------------------------------------------------ 工具
_fonts = {}


def font(name, size):
    k = (name, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(os.path.join(ROOT, "fonts", name + ".ttf"), size)
    return _fonts[k]


def clamp01(x):
    return min(max(x, 0.0), 1.0)


def ease(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def back(x, s=1.7):
    x = clamp01(x) - 1
    return x * x * ((s + 1) * x + s) + 1


class Sprite:
    def __init__(self, rgb, a):
        self.rgb, self.a = rgb, a
        self.h, self.w = a.shape


def blit(frame, sp, x, y, alpha=1.0, wipe=1.0):
    if alpha <= 0.002 or wipe <= 0.0:
        return
    x, y = int(round(x)), int(round(y))
    h, w = sp.h, sp.w
    ww = int(w * clamp01(wipe))
    if ww <= 0:
        return
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + ww, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    sx, sy = x0 - x, y0 - y
    a = sp.a[sy:sy + y1 - y0, sx:sx + x1 - x0, None] * alpha
    if wipe < 1.0:
        edge = min(40, ww)
        cols = np.arange(sx, sx + x1 - x0)
        ramp = np.clip((ww - cols) / edge, 0, 1).astype(np.float32)
        a = a * ramp[None, :, None]
    reg = frame[y0:y1, x0:x1]
    reg *= 1 - a
    reg += a * sp.rgb[sy:sy + y1 - y0, sx:sx + x1 - x0]


def scaled(sp, s):
    if abs(s - 1) < 1e-3:
        return sp
    return Sprite(cv2.resize(sp.rgb, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR),
                  cv2.resize(sp.a, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR))


def blit_c(frame, sp, cx, cy, alpha=1.0, s=1.0):
    sp = scaled(sp, s)
    blit(frame, sp, cx - sp.w / 2, cy - sp.h / 2, alpha)


def pil_sprite(img):
    arr = np.asarray(img, np.float32) / 255.0
    return Sprite(arr[..., :3].copy(), arr[..., 3].copy())


def parse_runs(line):
    runs, red, buf = [], False, ""
    for ch in line:
        if ch in "【】":
            if buf:
                runs.append((buf, red))
            buf, red = "", ch == "【"
        else:
            buf += ch
    if buf:
        runs.append((buf, red))
    return runs


def _wrap1(lines, f, max_w):
    out = []
    for l in lines:
        cur = ""
        for ch in l:
            if f.getlength((cur + ch).replace("【", "").replace("】", "")) > max_w and cur:
                # 避免标点落在行首
                if ch in "，。、；：！？」）%" and len(cur) > 1:
                    out.append(cur[:-1])
                    cur = cur[-1]
                else:
                    out.append(cur)
                    cur = ""
                if out[-1].count("【") > out[-1].count("】"):
                    out[-1] += "】"
                    cur = "【" + cur
            cur += ch
        out.append(cur)
    return out


# 竖屏下没有标点可断的长句：手工指定断点
BREAKS = {
    "全家把姓氏从格罗斯鲍姆改为格雷厄姆": ["全家把姓氏从「格罗斯鲍姆」", "改为「格雷厄姆」"],
    "价值 = 每股收益 ×（8.5 + 2 × 增长率）": ["价值 = 每股收益", "×（8.5 + 2 × 增长率）"],
    "《格雷厄姆-多德都市的超级投资者们》": ["《格雷厄姆-多德都市的", "超级投资者们》"],
    "英文、数学、哲学三个系都请他留校任教": ["英文、数学、哲学三个系", "都请他留校任教"],
}


def wrap(lines, f, max_w):
    out = []
    clean = lambda x: x.replace("【", "").replace("】", "")
    lines = [p for l in lines for p in BREAKS.get(l, [l])]
    for l in lines:
        if f.getlength(clean(l)) > max_w:   # 优先在标点后断开
            cands = [k + 1 for k, ch in enumerate(l[:-1]) if ch in "，、：；"
                     and f.getlength(clean(l[:k + 1])) <= max_w and f.getlength(clean(l[k + 1:])) <= max_w
                     and l[:k + 1].count("【") == l[:k + 1].count("】")]
            if cands:
                k = min(cands, key=lambda k: abs(k - len(l) / 2))
                out += [l[:k], l[k:]]
                continue
        seg = _wrap1([l], f, max_w)
        if len(seg) >= 2 and len(clean(seg[-1])) <= 3:   # 末行只剩几个字：按平均行宽重新换行
            w_avg = f.getlength(clean(l)) / len(seg)
            for k in range(30):
                s2 = _wrap1([l], f, w_avg * (1.04 + 0.02 * k))
                if len(s2) == len(seg) and len(clean(s2[-1])) > 3:
                    seg = s2
                    break
        out += seg
    return out


def text_sprite(lines, fname, size, color=WHITE, red=RED, gap=1.35, shadow=True, max_w=None, gold=False, track=0, center=False):
    f = font(fname, size)
    lines = [l for l in lines if l is not None]
    if max_w:
        lines = wrap(lines, f, max_w)
    lh = int(size * gap)
    clean = [l.replace("【", "").replace("】", "") for l in lines]
    widths = [f.getlength(l) + track * max(0, len(l) - 1) for l in clean]
    pad = int(size * 0.35)
    cw, chh = int(max(widths) + 2 * pad) + 4, lh * (len(lines) - 1) + int(size * 1.45) + 2 * pad
    img = Image.new("RGBA", (cw, chh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    to8 = lambda c: tuple(int(v * 255) for v in c)
    for i, l in enumerate(lines):
        x = pad + ((max(widths) - widths[i]) / 2 if center else 0)
        y = pad + i * lh
        for txt, isred in parse_runs(l):
            for ch in (txt if track else [txt]):
                d.text((x, y), ch, font=f, fill=to8(red if isred else color) + (255,))
                x += f.getlength(ch) + track
    if gold:
        a = np.asarray(img, np.float32)[..., 3] / 255
        ys = np.linspace(0, 1, chh)
        ramp = np.zeros((chh, 3), np.float32)
        for c in range(3):
            ramp[:, c] = np.interp(ys, [p for p, _ in GOLD_STOPS], [v[c] / 255 for _, v in GOLD_STOPS])
        sp = Sprite(np.repeat(ramp[:, None, :], cw, 1), a)
    else:
        sp = pil_sprite(img)
    if shadow:
        sh = cv2.GaussianBlur(sp.a, (0, 0), size * 0.08 + 1.5) * 0.85
        sh = np.roll(np.roll(sh, 3, 0), 2, 1)
        a = sp.a + sh * (1 - sp.a)
        sp = Sprite(sp.rgb * (sp.a / np.maximum(a, 1e-4))[..., None], a)
    return sp


def fill_rect(frame, x0, y0, x1, y1, color, alpha=1.0):
    x0, y0, x1, y1 = max(int(x0), 0), max(int(y0), 0), min(int(x1), W), min(int(y1), H)
    if x1 <= x0 or y1 <= y0:
        return
    reg = frame[y0:y1, x0:x1]
    reg *= 1 - alpha
    reg += np.array(color, np.float32) * alpha


def shadow_under(frame, x0, y0, x1, y1, strength=0.35, blur=22):
    m = np.zeros((H // 4, W // 4), np.float32)
    cv2.rectangle(m, (int(x0 / 4) + 2, int(y0 / 4) + 3), (int(x1 / 4) + 2, int(y1 / 4) + 3), 1.0, -1)
    m = cv2.resize(cv2.GaussianBlur(m, (0, 0), blur / 4), (W, H))
    frame *= (1 - m * strength)[..., None]


# ------------------------------------------------------------------ 全局层
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
_rng = np.random.default_rng(7)
GRAIN = [_rng.standard_normal((H // 2, W // 2)).astype(np.float32) for _ in range(6)]
VIGNETTE = (1 - 0.40 * (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2) ** 1.3).clip(0.35, 1)[..., None]
# 下部字幕区和顶部标题区压暗
SCRIM = (1 - 0.70 * np.clip((yy - 1080) / 500, 0, 1) ** 1.2 - 0.45 * np.clip((300 - yy) / 300, 0, 1))[..., None]
HUD = Hud(width=W)    # MastersTao 官方 logo 角标（右上角，logo 高 64px，距右 44px）
HUD.my = 116          # 竖屏：下移避开手机状态栏，和左侧章节名对齐
BA, BB = np.array(PALETTE["brand_a"], np.float32), np.array(PALETTE["brand_b"], np.float32)
INK2, INK3 = np.array(PALETTE["ink2"], np.float32), np.array(PALETTE["ink3"], np.float32)


def paper_bg():
    rng = np.random.default_rng(3)
    base = np.full((H, W, 3), (0.86, 0.86, 0.85), np.float32)
    n = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 1.2) * 0.018
    base += n[..., None]
    dots = np.zeros((H, W), np.float32)
    for y in range(0, H, 14):
        for x in range(0, W, 14):
            r = 2.2 * clamp01((x / W * 0.6 + y / H - 0.85) * 1.6)
            if r > 0.4:
                cv2.circle(dots, (x, y), int(round(r)), 1.0, -1, cv2.LINE_AA)
    base -= dots[..., None] * 0.07
    return base * (1 - 0.2 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2))[..., None]


PAPER = paper_bg()


def navy_bg():
    g = np.zeros((H, W, 3), np.float32)
    g[:] = (0.035, 0.05, 0.085)
    g += (np.exp(-(((xx - W * 0.6) / (W * 0.8)) ** 2 + ((yy - H * 0.4) / (H * 0.45)) ** 2)) * 0.09)[..., None] * np.array([0.5, 0.8, 1.4], np.float32)
    for x in range(0, W, 90):
        g[:, x:x + 1] += 0.018
    for y in range(0, H, 90):
        g[y:y + 1, :] += 0.018
    return g


NAVY = navy_bg()

# ------------------------------------------------------------------ 素材
_img = {}
# Gemini 额度/密钥不可用时的替补：借用第 04 集风格相近的素材（制作规范 4.1），生成本集素材后自动改用本集图片
EP04 = os.path.join(ROOT, "..", "04-沃伦·巴菲特", "assets")
FALLBACK = {
    "london": "grocery", "mourning": "partners", "panic1907": "bank", "boy_work": "paperboy", "columbia": "classroom",
    "wallst1914": "newsroom", "analyst1914": "annual", "mining": "mill_dark", "ww1": "wedding", "office1923": "insurance",
    "factory1920s": "textile", "partners1926": "dinner", "archive": "annual", "proxy1928": "meeting", "cigar": "offer",
    "classroom1928": "classroom", "notes1927": "book", "crash1929": "crash74", "forbes1932": "magazine", "ledger": "annual",
    "book1934": "book", "office1936": "office_door", "insurance1948": "insurance", "boardroom": "meeting", "book1949": "book",
    "mrmarket": "newsroom", "senate1955": "hearing", "stamp": "stamp", "tire1919": "shoes", "reader1949": "book",
    "classroom1950": "classroom", "office_door": "office_door", "office1954": "partners", "baby1954": "wedding",
    "cocoa": "candy", "analysts": "meeting", "book_revise": "offer", "provence": "farewell", "speech1984": "arena",
    "campus_now": "classroom", "podium_old": "meeting", "library": "book", "wallst_dusk": "lehman",
}


def asset_raw(key):
    p = os.path.join(ROOT, "assets", key + ".jpg")
    if not os.path.exists(p):
        p = os.path.join(EP04, FALLBACK.get(key, "stamp") + ".jpg")
    im = cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)
    h, w = im.shape[:2]
    return im[int(h * 0.03):int(h * 0.97), int(w * 0.03):int(w * 0.97)]


def asset(key):
    k = ("band", key)
    if k not in _img:
        _img[k] = cv2.resize(asset_raw(key), (int(W * 1.16), int(BAND_H * 1.16)), interpolation=cv2.INTER_AREA)
    return _img[k]


def asset_blur(key):
    k = ("blur", key)
    if k not in _img:
        im = asset_raw(key)
        h, w = im.shape[:2]
        s = (H / 4) / h
        sm = cv2.resize(im, (int(w * s), int(H / 4)), interpolation=cv2.INTER_AREA)
        cx = sm.shape[1] // 2
        sm = sm[:, cx - W // 8 - 20:cx + W // 8 + 20]
        sm = cv2.GaussianBlur(sm.astype(np.float32) / 255, (0, 0), 7)
        _img[k] = sm
    return _img[k]


def bg_blur(key, u):
    sm = asset_blur(key)
    h, w = sm.shape[:2]
    off = int((w - W / 4) * (0.5 + 0.4 * (u - 0.5)))
    crop = sm[:, max(0, off):max(0, off) + W // 4]
    return cv2.resize(crop, (W, H), interpolation=cv2.INTER_LINEAR) * 0.42


def kenburns(key, u, i, w=W, h=BAND_H, punch=0.0):
    im = asset(key)
    ih, iw = im.shape[:2]
    mode = i % 4
    z0, z1 = (1.0, 1.12) if mode in (0, 2) else (1.12, 1.0)
    z = (z0 + (z1 - z0) * ease_io(u)) * (1 + punch)
    s = max(w / iw, h / ih) * z
    px = {0: (0.5, 0.5), 1: (0.5, 0.5), 2: (0.4, 0.55), 3: (0.6, 0.45)}[mode]
    cx = iw * (px[0] + (0.5 - px[0]) * u)
    cy = ih * (px[1] + (0.5 - px[1]) * u)
    M = np.array([[s, 0, w / 2 - cx * s], [0, s, h / 2 - cy * s]], np.float32)
    return cv2.warpAffine(im, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255


def grade(img, err=False, mono=0.0, warm=0.0):
    if err or mono > 0:
        g = img.mean(2, keepdims=True)
        k = 0.65 if err else mono
        img = img * (1 - k) + g * k
        if err:
            img = img * np.array([0.9, 0.96, 1.08], np.float32)
    if warm > 0:
        img = img * (1 + warm * np.array([0.08, 0.02, -0.06], np.float32))
    return img


# ------------------------------------------------------------------ 节拍
def beat_pulse(t, ch):
    """强拍脉冲 0..1"""
    e = ENERGY.get(ch, 0.5)
    if e < 0.55:
        return 0.0
    k = np.searchsorted(DOWNS, t + 1e-6) - 1
    if k < 0:
        return 0.0
    dt = t - DOWNS[k]
    return float(math.exp(-dt / 0.16)) * (e - 0.45)


# ------------------------------------------------------------------ 顶部标题 / 字幕
_cap = {}


def header(frame, i, t):
    ch = CHN[i]
    if ch in ("序章", "片尾"):
        return
    k = ("hdr", ch)
    if k not in _cap:
        n = CH_NO.get(ch, 0)
        _cap[k] = (text_sprite(["投资大师列传 · 本杰明·格雷厄姆"], "sans_bold", 30, color=(0.85, 0.72, 0.45)),
                   text_sprite([f"第{CN[n]}章  {ch}"], "sans_black", 42, color=WHITE))
    a, b = _cap[k]
    blit(frame, a, 50, 102)
    fill_rect(frame, 60, 162, 65, 212, YELLOW if not ERR[i] else RED, 1.0)
    blit(frame, b, 68, 150)


def caption_sprites(i):
    if i in _cap:
        return _cap[i]
    s = SHOTS[i]
    yr = s["year"]
    big = None
    if yr:
        f1, f2 = font("sans_black", 128), font("sans_black", 92)
        age = f"-{s['age']}" if s["age"] else ""
        w1, w2 = f1.getlength(yr), f2.getlength(age)
        img = Image.new("RGBA", (int(w1 + w2) + 40, 180), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.text((10, 6), yr, font=f1, fill=(255, 212, 0, 255))
        if age:
            d.text((10 + w1 + 4, 40), age, font=f2, fill=(255, 212, 0, 255))
        sp = pil_sprite(img)
        sh = np.roll(np.roll(cv2.GaussianBlur(sp.a, (0, 0), 7) * 0.85, 5, 0), 3, 1)
        a = sp.a + sh * (1 - sp.a)
        big = Sprite(sp.rgb * (sp.a / np.maximum(a, 1e-4))[..., None], a)
    lines = None if s.get("fx") == "compound" else text_sprite(s["lines"], "sans_black", 54, gap=1.42, max_w=870)
    _cap[i] = (big, lines)
    return _cap[i]


def beat_len():
    return 0.510839


def draw_caption(frame, i, t):
    big, lines = caption_sprites(i)
    x = 60
    a = ease(t / 0.25)
    if big:
        s = 1 + 0.35 * (1 - back(t / 0.32))
        bs = scaled(big, s)
        blit(frame, bs, x - 12, CAP_Y - (bs.h - big.h) / 2, a)
    if lines is None:
        return
    ly = CAP_Y + (170 if big else 40)
    td = beat_len() * 0.5
    bar_h = lines.h - 30
    grow = ease((t - td) / 0.3)
    fill_rect(frame, x, ly + 14, x + 10, ly + 14 + bar_h * grow, YELLOW if not ERR[i] else RED, a)
    blit(frame, lines, x + 18, ly, ease((t - td) / 0.2), wipe=ease((t - td) / 0.55))


def draw_tag(frame, i, t):
    tag = SHOTS[i].get("tag")
    if not tag:
        return
    k = ("tag", i)
    if k not in _cap:
        _cap[k] = text_sprite([f"错误清单 {tag}"], "sans_black", 40, color=WHITE, shadow=False)
    sp = _cap[k]
    a = ease(t / 0.2)
    x, y = 60, 290
    s = 1 + 0.4 * (1 - back(t / 0.3))
    fill_rect(frame, x, y, x + (sp.w + 18) * s, y + (sp.h - 6) * s, (0.82, 0.1, 0.08), 0.95 * a)
    blit(frame, scaled(sp, s), x + 9, y - 3, a)


def chapter_title(frame, i, t):
    """章节开头：画面中央的大号章节名，随冲击出现"""
    if i not in CH_START or CHN[i] in ("片尾",):
        return
    ch = CHN[i]
    k = ("cht", ch)
    if k not in _cap:
        n = CH_NO.get(ch, 0)
        _cap[k] = (text_sprite([f"第{CN[n]}章"], "sans_bold", 40, color=(1, 0.86, 0.5), track=14),
                   text_sprite([ch], "serif_black", 96 if len(ch) <= 6 else 80, gold=True, track=6))
    a_, b_ = _cap[k]
    if t > 1.9:
        return
    al = ease(t / 0.12) * (1 - ease_io((t - 1.4) / 0.5))
    s = 1 + 0.25 * (1 - back(t / 0.35))
    cy = BAND_Y + BAND_H / 2
    if SHOTS[i]["kind"] == "data" and not SHOTS[i].get("bg"):   # 纯数据镜头：放到图表上方，免得压住数字
        cy = 340
    fill_rect(frame, 0, cy - 120, W, cy + 120, (0, 0, 0), 0.45 * al)
    blit_c(frame, a_, W / 2, cy - 62, al)
    blit_c(frame, b_, W / 2, cy + 22, al, s)


# ------------------------------------------------------------------ 正片中途关注语（参照 claude/festive-brown-49d0no 的胶囊条）
FOLLOWS = TL.get("follows", [])
FOLLOW_DUR, FOLLOW_FADE = 4.5, 0.4
FOLLOW_Y = 1800       # 胶囊底边：字幕最低约 1680，平台底部文案区之上


def pill_sprite(tagged):
    k = ("pill", tagged)
    if k in _cap:
        return _cap[k]
    m1 = text_sprite(["关注 MastersTao"], "sans_bold", 38, color=WHITE, shadow=False)
    m2 = text_sprite(["更多投资大师 · 主页合集"], "sans_bold", 26, color=tuple(PALETTE["series_ab"]), shadow=False) if tagged else None
    lg = 60
    logo = Sprite(*mt_logo("blue", "mark", lg))           # MastersTao 官方图形
    tw = max(m1.w, m2.w if m2 else 0)
    h = 116 if tagged else 88
    w = 20 + lg + 10 + tw + 18
    a = np.zeros((h, w), np.float32)
    r = h // 2
    box = np.zeros((h, w), np.uint8)
    cv2.rectangle(box, (r, 0), (w - r, h - 1), 255, -1)
    cv2.circle(box, (r, r), r, 255, -1, cv2.LINE_AA)
    cv2.circle(box, (w - r - 1, r), r, 255, -1, cv2.LINE_AA)
    a[:] = box / 255 * 0.62
    sp = Sprite(np.zeros((h, w, 3), np.float32) + np.array([0.03, 0.035, 0.06], np.float32), a)
    for src, x, y in [(logo, 20, (h - lg) // 2)] + ([(m1, 20 + lg + 4, (h - m1.h - m2.h + 22) // 2), (m2, 20 + lg + 4, (h - m1.h - m2.h + 22) // 2 + m1.h - 22)] if m2 else [(m1, 20 + lg + 4, (h - m1.h) // 2)]):
        al = src.a[..., None]
        reg = sp.rgb[y:y + src.h, x:x + src.w]
        hh, ww = reg.shape[:2]
        reg[:] = reg * (1 - al[:hh, :ww]) + src.rgb[:hh, :ww] * al[:hh, :ww]
        sp.a[y:y + hh, x:x + ww] = np.maximum(sp.a[y:y + hh, x:x + ww], src.a[:hh, :ww])
    _cap[k] = sp
    return sp


def follow_pill(frame, t):
    for fo in FOLLOWS:
        t0 = fo["t"]
        if not (t0 <= t < t0 + FOLLOW_DUR):
            continue
        sp = pill_sprite(fo["tagged"])
        q = t - t0
        a = min(1.0, q / FOLLOW_FADE, (FOLLOW_DUR - q) / FOLLOW_FADE)
        dy = 14 * (1 - ease(q / FOLLOW_FADE))
        blit(frame, sp, (W - sp.w) / 2, FOLLOW_Y - sp.h + dy, a)   # 底部居中：字幕下方，避开平台右侧按钮


# ------------------------------------------------------------------ 纸卡
def framed_photo(key, w, h):
    im = cv2.resize(asset_raw(key), (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    b = 14
    rgb = np.ones((h + 2 * b, w + 2 * b, 3), np.float32) * 0.97
    rgb[b:b + h, b:b + w] = im
    return Sprite(rgb, np.ones(rgb.shape[:2], np.float32))


def draw_card(frame, i, t, err=False):
    s = SHOTS[i]
    k = ("card", i)
    has_photo = bool(s.get("bg"))
    if k not in _cap:
        yr = s["year"] + (f"-{s['age']}" if s["age"] else "")
        head = text_sprite([yr], "sans_black", 76, color=(0.87, 0.62, 0.0), shadow=False) if yr else None
        quote = any("「" in l for l in s["lines"])
        body = text_sprite(s["lines"], "serif_black" if quote else "sans_black", 48 if has_photo else 64,
                           color=INK, red=(0.85, 0.12, 0.1), gap=1.5, shadow=False, max_w=860)
        photo = framed_photo(s["bg"], 900, 506) if has_photo else None
        _cap[k] = (head, body, photo)
    head, body, photo = _cap[k]
    a = ease(t / 0.3)
    dy = 40 * (1 - back(t / 0.45))
    accent = (0.95, 0.75, 0.0) if not err else (0.82, 0.1, 0.08)
    if photo:
        px, py = (W - photo.w) / 2, 390
        shadow_under(frame, px, py - dy, px + photo.w, py + photo.h - dy, 0.4 * a)
        blit(frame, photo, px, py - dy, a)
    cw = 960
    hh = head.h if head else 0
    ch = body.h + hh + 80
    cx = (W - cw) / 2
    cy = 990 if photo else ((H - ch) / 2 - 20 if s.get("fx") != "criteria" else 420)
    shadow_under(frame, cx, cy + dy, cx + cw, cy + ch + dy, 0.3 * a)
    fill_rect(frame, cx, cy + dy, cx + cw, cy + ch + dy, (0.95, 0.94, 0.91), a)
    fill_rect(frame, cx, cy + dy, cx + 12, cy + ch + dy, accent, a)
    fill_rect(frame, cx, cy + dy, cx + cw, cy + 7 + dy, accent, a)
    y = cy + 38 + dy
    if head:
        blit(frame, head, cx + 46, y - 16, a)
        y += hh - 10
    blit(frame, body, cx + 46, y, a, wipe=ease((t - beat_len() * 0.5) / 0.9))


# ------------------------------------------------------------------ 点阵地图
from global_land_mask import globe

# 起点视野 (经度, 纬度, 像素/度) → 终点视野、地名、插图、起点标记 (经度, 纬度, 名称)、中途拉远倍数
MAPS = {
    "london_ny": ((-0.13, 51.5, 24), (-74.0, 40.71, 22), "纽约", None, (-0.13, 51.5, "伦敦"), 3.2),
    "california": ((-74.0, 40.71, 14), (-118.24, 34.05, 9), "洛杉矶 · 加州", None, (-74.0, 40.71, "纽约"), 0.5),
}
STEP = 10
_gy, _gx = np.mgrid[STEP // 2:H:STEP, STEP // 2:W:STEP].astype(np.float32)
_dot = np.zeros((STEP, STEP), np.float32)
cv2.circle(_dot, (STEP // 2, STEP // 2), 3, 1.0, -1, cv2.LINE_AA)
DOTS = np.tile(_dot, (H // STEP + 1, W // STEP + 1))[:H, :W]
MAP_CY = 820


def map_frame(key, u):
    (lo0, la0, s0), (lo1, la1, s1), label, inset, origin, zout = MAPS[key]
    e = ease_io(min(u / 0.6, 1))
    lo = lo0 + (lo1 - lo0) * e
    la = la0 + (la1 - la0) * e
    sc = math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * e)
    sc = sc / (1 + zout * math.sin(math.pi * e))      # 跨大洋时中途拉远
    sc *= 1 + 0.06 * u
    lon = lo + (_gx - W / 2) / sc
    lat = la - (_gy - MAP_CY) / sc
    lon = (lon + 180) % 360 - 180
    land = globe.is_land(np.clip(lat, -89.9, 89.9), lon).astype(np.float32)
    big = cv2.resize(land, (W, H), interpolation=cv2.INTER_NEAREST)
    f = NAVY.copy() * 0.9
    tx = W / 2 + (lo1 - lo) * sc
    ty = MAP_CY - (la1 - la) * sc
    near = np.exp(-(((xx - tx) ** 2 + (yy - ty) ** 2) / (2 * 380 ** 2)))
    col = np.array([0.22, 0.36, 0.55], np.float32)[None, None] + near[..., None] * np.array([0.2, 0.25, 0.3], np.float32)
    f += (big * DOTS)[..., None] * col
    f += ((1 - big) * DOTS)[..., None] * 0.025
    org = None
    if origin:
        org = (W / 2 + (origin[0] - lo) * sc, MAP_CY - (origin[1] - la) * sc, origin[2])
    return f, (tx, ty), label, inset, org


def draw_origin(frame, org, tgt, u):
    """起点标记 + 指向终点的航线（虚线弧）"""
    ox, oy, name = org
    tx, ty = tgt
    a = ease(u / 0.12)
    dot(frame, ox, oy, 11, YELLOW, a)
    if u < 0.12:
        q = ((u * 6) % 1.0)
        m = np.zeros((H, W), np.float32)
        cv2.circle(m, (int(ox), int(oy)), int(12 + 60 * q), 1.0, 3, cv2.LINE_AA)
        frame += (m * (1 - q) * 0.7 * a)[..., None] * np.array(YELLOW, np.float32)
    label(frame, ("org", name), name, ox + 22 if ox < W - 200 else ox - 150, oy - 70, 42, WHITE, a)
    p = ease_io(clamp01((u - 0.08) / 0.5))
    if p > 0:
        n = 60
        ts = np.linspace(0, p, n)
        mx, my = (ox + tx) / 2, (oy + ty) / 2 - 0.25 * math.hypot(tx - ox, ty - oy)
        px = (1 - ts) ** 2 * ox + 2 * (1 - ts) * ts * mx + ts ** 2 * tx
        py = (1 - ts) ** 2 * oy + 2 * (1 - ts) * ts * my + ts ** 2 * ty
        for k in range(0, n - 1, 2):
            polyline(frame, [(px[k], py[k]), (px[k + 1], py[k + 1])], YELLOW, th=5, glow=False)


def draw_pin(frame, x, y, u, label, left=False):
    k = ("pin", label)
    if k not in _cap:
        _cap[k] = text_sprite([label], "sans_black", 46, color=YELLOW)
    lab = _cap[k]
    p = clamp01((u - 0.5) / 0.12)
    if p <= 0:
        return
    drop = (1 - ease(p)) * -140
    bounce = math.sin(p * math.pi * 2) * 9 * (1 - p)
    py = y + drop + bounce
    q = ((u - 0.6) * 1.5) % 1.0 if u > 0.6 else 0
    if q > 0:
        m = np.zeros((H, W), np.float32)
        cv2.circle(m, (int(x), int(y)), int(10 + 80 * q), 1.0, 3, cv2.LINE_AA)
        frame += (m * (1 - q) * 0.8)[..., None] * np.array(RED, np.float32)
    m = np.zeros((H, W), np.float32)
    cv2.circle(m, (int(x), int(py - 38)), 19, 1.0, -1, cv2.LINE_AA)
    cv2.fillPoly(m, [np.array([[x - 17, py - 29], [x + 17, py - 29], [x, py]], np.int32)], 1.0, cv2.LINE_AA)
    frame *= (1 - m)[..., None]
    frame += m[..., None] * np.array([0.9, 0.12, 0.1], np.float32)
    m2 = np.zeros((H, W), np.float32)
    cv2.circle(m2, (int(x), int(py - 38)), 7, 1.0, -1, cv2.LINE_AA)
    frame *= (1 - m2)[..., None]
    frame += m2[..., None]
    lx = x + 30 if x + 30 + lab.w < W - 20 and not left else x - 30 - lab.w
    blit(frame, lab, lx, py - 80, ease(p), wipe=ease((u - 0.56) / 0.15))


# ------------------------------------------------------------------ 数据动画（竖屏：图表区 x 90–990，y 380–1080）
def polyline(frame, pts, color, th=7, glow=True, prog=1.0):
    pts = np.array(pts, np.float32)
    if prog < 1:
        seg = np.sqrt((np.diff(pts, axis=0) ** 2).sum(1))
        L = seg.sum() * prog
        acc, out = 0, [pts[0]]
        for k, sl in enumerate(seg):
            if acc + sl >= L:
                out.append(pts[k] + (pts[k + 1] - pts[k]) * ((L - acc) / max(sl, 1e-6)))
                break
            acc += sl
            out.append(pts[k + 1])
        pts = np.array(out, np.float32)
    m = np.zeros((H, W), np.float32)
    cv2.polylines(m, [np.round(pts * 4).astype(np.int32)], False, 1.0, th, cv2.LINE_AA, shift=2)
    if glow:
        frame += cv2.GaussianBlur(m, (0, 0), 10)[..., None] * np.array(color, np.float32) * 0.6
    frame *= (1 - m)[..., None]
    frame += m[..., None] * np.array(color, np.float32)
    return pts[-1]


def dot(frame, x, y, r, color, a=1.0):
    m = np.zeros((H, W), np.float32)
    cv2.circle(m, (int(x), int(y)), int(r), 1.0, -1, cv2.LINE_AA)
    m *= a
    frame *= (1 - m)[..., None]
    frame += m[..., None] * np.array(color, np.float32)


def label(frame, key, text, x, y, size=38, color=WHITE, a=1.0, fname="sans_black", center=False):
    k = ("lab", key, text, size, color)
    if k not in _cap:
        _cap[k] = text_sprite([text], fname, size, color=color)
    sp = _cap[k]
    blit(frame, sp, x - (sp.w / 2 if center else 0), y, a)


def num_text(frame, text, x, y, size, color, a=1.0, gold=False, anchor="l"):
    k = ("num", text, size, color, gold)
    if k not in _cap:
        _cap[k] = text_sprite([text], "oswald", size, color=color, gold=gold)
    sp = _cap[k]
    blit(frame, sp, x - {"l": 0, "c": sp.w / 2, "r": sp.w}[anchor], y, a)


def chart_axes(frame, x0, y0, x1, y1):
    fill_rect(frame, x0, y1, x1, y1 + 2, (0.6, 0.65, 0.75), 0.6)
    for k in range(1, 4):
        fill_rect(frame, x0, y0 + (y1 - y0) * k / 4, x1, y0 + (y1 - y0) * k / 4 + 1, (0.6, 0.65, 0.75), 0.15)


CX0, CX1, CY0, CY1 = 110, 970, 430, 1060
GOLD = (1.0, 0.78, 0.25)
GREY = (0.6, 0.63, 0.7)
STEEL = (0.35, 0.55, 0.85)
BASE = 1000          # 柱状图基线


def hdash(frame, x0, x1, y, color, a=1.0, th=4, dash=22):
    for x in np.arange(x0, x1, dash * 2):
        fill_rect(frame, x, y - th / 2, min(x + dash, x1), y + th / 2, color, a)


def bar(frame, key, x, w, h, color, name=None, val=None, vsize=72, vcolor=None, a=1.0, base=BASE):
    """从基线向上长的柱子：下方名称、上方数值"""
    if h > 1:
        fill_rect(frame, x, base - h, x + w, base, color, 0.95 * a)
    if name:
        label(frame, ("bn", key), name, x + w / 2, base + 16, 38, WHITE, a, center=True)
    if val is not None and h > 1:
        label(frame, ("bv", key, val), val, x + w / 2, base - h - vsize * 1.45, vsize, vcolor or color, a, center=True)


def big_text(frame, key, text, cx, cy, size, color, a=1.0, s=1.0, fname="sans_black", gold=False):
    k = ("big", key, text, size)
    if k not in _cap:
        _cap[k] = text_sprite([text], fname, size, color=color, gold=gold)
    blit_c(frame, _cap[k], cx, cy, a, s)


def slam(frame, key, text, cx, cy, size, color, u, u0):
    """数字砸下：放大回弹出现"""
    q = (u - u0) / 0.12
    if q > 0:
        big_text(frame, key, text, cx, cy, size, color, ease(q), 1 + 0.6 * (1 - back((u - u0) / 0.2)))


def series(vals, x0=CX0, x1=CX1, y0=CY0, y1=CY1, vmax=1.0):
    n = len(vals)
    return [(x0 + (x1 - x0) * k / (n - 1), y1 - v / vmax * (y1 - y0)) for k, v in enumerate(vals)]


def box(frame, key, text, cx, cy, w, h, color, a=1.0, fill=(0.06, 0.08, 0.13)):
    fill_rect(frame, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, fill, 0.9 * a)
    fill_rect(frame, cx - w / 2, cy - h / 2, cx - w / 2 + 8, cy + h / 2, color, a)
    for yy_ in (cy - h / 2, cy + h / 2 - 3):
        fill_rect(frame, cx - w / 2, yy_, cx + w / 2, yy_ + 3, color, 0.6 * a)
    big_text(frame, ("box", key), text, cx, cy, 50, WHITE, a)


def arrow_down(frame, cx, y0, y1, color, p):
    if p <= 0:
        return
    ye = y0 + (y1 - y0) * p
    fill_rect(frame, cx - 4, y0, cx + 4, ye - 10, color, 1)
    m = np.zeros((H, W), np.float32)
    cv2.fillPoly(m, [np.array([[cx - 22, ye - 24], [cx + 22, ye - 24], [cx, ye + 6]], np.int32)], 1.0, cv2.LINE_AA)
    frame *= (1 - m)[..., None]
    frame += m[..., None] * np.array(color, np.float32)


def fx_draw(frame, fx, u, t):
    x0, x1, y0, y1 = CX0, CX1, CY0, CY1
    if fx == "panic1907":            # 股价断崖 + 爆仓
        chart_axes(frame, x0, y0, x1, y1)
        vals = [0.42, 0.5, 0.47, 0.58, 0.66, 0.63, 0.7, 0.2, 0.08]
        pts = series(vals)
        p = ease(u / 0.75)
        polyline(frame, pts[:7], GOLD, prog=min(1, p / 0.7))
        if p > 0.7:
            e = polyline(frame, pts[6:], RED, prog=(p - 0.7) / 0.3)
            dot(frame, *e, 10, RED)
        label(frame, "p07", "1907年10月", pts[6][0] - 130, y1 + 14, 38, GREY)
        slam(frame, "bao", "爆仓", pts[-1][0] - 110, pts[-1][1] - 120, 110, RED, u, 0.78)
    elif fx == "guggenheim":         # 持有资产价值 > 股价
        p = ease(u / 0.5)
        bar(frame, "g1", 200, 260, 520 * p, GOLD, "持有资产价值")
        bar(frame, "g2", 620, 260, 380 * p, GREY, "股价")
        if u > 0.55:
            q = ease((u - 0.55) / 0.2)
            fill_rect(frame, 620, BASE - 520, 880, BASE - 380, YELLOW, 0.35 * q)
            hdash(frame, 200, 880, BASE - 520, YELLOW, q)
            label(frame, "gg", "套利空间", 750, BASE - 520 - 76, 50, YELLOW, q, center=True)
    elif fx == "dupont_gm":          # 杜邦市值 ≈ 所持通用汽车股票市值
        p = ease(u / 0.45)
        conv = ease((u - 0.62) / 0.3)
        hd = (430 + 70 * conv) * p
        bar(frame, "d1", 200, 260, hd, GREY, "杜邦市值")
        bar(frame, "d2", 620, 260, 500 * p, GOLD, "所持通用股票")
        if u > 0.4:
            q = ease((u - 0.4) / 0.12)
            label(frame, "dbuy", "买入", 330, BASE + 80, 46, YELLOW, q, center=True)
            label(frame, "dsell", "卖空", 750, BASE + 80, 46, RED, q, center=True)
        if 0.5 < u:
            q = ease((u - 0.5) / 0.12)
            gap = (500 - 430) * (1 - conv)
            if gap > 4:
                fill_rect(frame, 200, BASE - 500, 460, BASE - 430 - 70 * conv, RED, 0.35 * q)
            label(frame, "dgap", "价差" if conv < 0.9 else "价差收敛", 330, BASE - 500 - 80, 46, RED if conv < 0.9 else YELLOW, q, center=True)
    elif fx in ("pipeline", "pipeline2"):   # 每股资产约 95 美元 vs 股价约 65 美元
        k = 5.0
        if fx == "pipeline":
            p = ease(u / 0.6)
            bar(frame, "pa", 380, 320, 95 * k * p, GOLD, "每股债券和现金", f"${int(round(95 * p))}", 96)
        else:
            bar(frame, "pa", 200, 280, 95 * k, GOLD, "每股债券和现金", "$95", 90)
            p = ease(u / 0.5)
            bar(frame, "pb", 620, 280, 65 * k * p, GREY, "股价", f"${int(round(65 * p))}", 90, WHITE)
            if u > 0.55:
                q = ease((u - 0.55) / 0.2)
                fill_rect(frame, 620, BASE - 95 * k, 900, BASE - 65 * k, YELLOW, 0.35 * q)
                label(frame, "pd", "差价约$30", 760, BASE - 95 * k - 130, 54, YELLOW, q, center=True)
    elif fx == "netnet":             # 股价只到净流动资产的三分之二
        p = ease(u / 0.4)
        hA = 540
        bar(frame, "n1", 200, 260, hA * p, GOLD, "净流动资产")
        if u > 0.3:
            q = ease((u - 0.3) / 0.15)
            hdash(frame, 160, 920, BASE - hA * 2 / 3, YELLOW, q)
            label(frame, "n23", "2/3", 925, BASE - hA * 2 / 3 - 60, 52, YELLOW, q, center=False, fname="sans_black")
        p2 = ease((u - 0.4) / 0.35)
        bar(frame, "n2", 620, 260, hA * 0.58 * p2, GREY, "股价")
        if u > 0.78:
            slam(frame, "nbuy", "买入", 750, BASE - hA * 0.58 - 210, 80, YELLOW, u, 0.78)
    elif fx in ("crash29", "crash29b", "early"):   # 联合账户净值
        chart_axes(frame, x0, y0, x1, y1)
        vals = [1.0, 1.04, 0.86, 0.78, 0.82, 0.66, 0.6, 0.5, 0.45, 0.38, 0.33, 0.3]
        pts = series(vals, vmax=1.08)
        hdash(frame, x0, x1, pts[0][1], GREY, 0.5, 2)
        label(frame, "c100", "本金", x0, pts[0][1] - 56, 34, GREY)
        label(frame, "c29", "1929", x0 - 10, y1 + 14, 36, GREY)
        label(frame, "c32", "1932", x1 - 80, y1 + 14, 36, GREY)
        if fx == "crash29":
            e = polyline(frame, pts[:8], RED, prog=ease(u / 0.85))
            dot(frame, *e, 10, RED)
        elif fx == "crash29b":
            polyline(frame, pts[:8], (0.7, 0.25, 0.22), glow=False)
            e = polyline(frame, pts[7:], RED, prog=ease(u / 0.6))
            dot(frame, *e, 10, RED)
            slam(frame, "m70", "-70%", pts[-1][0] - 150, pts[-1][1] - 150, 150, RED, u, 0.6)
        else:
            e = polyline(frame, pts, RED, prog=ease(u / 0.85))
            dot(frame, *e, 10, RED)
            if u > 0.25:
                q = ease((u - 0.25) / 0.1)
                dot(frame, *pts[4], 16, YELLOW, q)
                label(frame, "ebuy", "加仓抄底", pts[4][0] - 80, pts[4][1] - 90, 44, YELLOW, q)
            if u > 0.86:
                label(frame, "edeep", "越跌越深", pts[-1][0] - 230, pts[-1][1] + 20, 44, RED, ease((u - 0.86) / 0.1))
    elif fx == "belowcash":          # 股价柱都低于每股现金虚线
        label(frame, "bl1", "— — 每股现金", 140, 400, 38, YELLOW, ease(u / 0.2))
        label(frame, "bl2", "■ 股价", 560, 400, 38, RED, ease(u / 0.2))
        cash = [0.62, 0.48, 0.7, 0.55, 0.66, 0.5]
        price = [0.4, 0.3, 0.45, 0.33, 0.38, 0.28]
        for k in range(6):
            x = 140 + k * 140
            q = ease((u - 0.08 * k) / 0.35)
            hdash(frame, x - 12, x + 112, BASE - cash[k] * 560, YELLOW, ease((u - 0.08 * k) / 0.15), 4, 12)
            fill_rect(frame, x, BASE - price[k] * 560 * q, x + 100, BASE, RED, 0.85)
        fill_rect(frame, 110, BASE, 970, BASE + 2, GREY, 0.6)
    elif fx == "geico":              # 一根长柱 vs 其余总和
        hs = [40, 30, 55, 25, 45, 35, 30, 40]
        acc = 0
        for k, h in enumerate(hs):
            q = ease((u - 0.04 * k) / 0.2)
            fill_rect(frame, 620, BASE - acc - h * q, 880, BASE - acc - 3, GREY, 0.9)
            acc += h * q
        label(frame, "go", "其余所有投资", 750, BASE + 16, 38, WHITE, 1, center=True)
        p = ease((u - 0.35) / 0.45)
        bar(frame, "gc", 200, 260, 560 * p, GOLD, "GEICO")
        if u > 0.82:
            slam(frame, "gw", "胜过总和", 330, BASE - 560 - 80, 64, YELLOW, u, 0.82)
    elif fx == "value_price":        # 价格围绕价值波动，跌进买入区就买
        vy = 700
        zone = vy + 150
        a = ease(u / 0.2)
        fill_rect(frame, x0, zone, x1, y1, YELLOW, 0.13 * a)
        label(frame, "vz", "买入区", x0 + 10, y1 - 70, 42, YELLOW, a)
        hdash(frame, x0, x1, vy, GOLD, a, 5)
        label(frame, "vv", "内在价值", x1 - 180, vy - 66, 40, GOLD, a)
        xs = np.linspace(0, 1, 160)
        py = vy - 230 * np.sin(xs * 2 * np.pi * 2.2 + 0.4) * (0.8 + 0.2 * np.sin(xs * 17)) - 40 * np.sin(xs * 31)
        pts = [(x0 + (x1 - x0) * x_, y_) for x_, y_ in zip(xs, py)]
        p = ease(u / 0.85)
        e = polyline(frame, pts, WHITE, th=5, prog=p)
        dot(frame, *e, 9, WHITE)
        label(frame, "vp", "价格", x0 + 10, pts[0][1] - 70, 40, WHITE, a)
        n = int(p * 159)
        for k in range(1, n):
            if py[k] > zone and py[k] >= py[k - 1] and py[k] >= py[min(k + 1, 159)]:
                dot(frame, pts[k][0], pts[k][1], 15, YELLOW)
    elif fx == "graham_number":      # 15 × 1.5 = 22.5
        rows = [("gn1", "市盈率 ≤ 15", 520, WHITE, 0.0), ("gn2", "×", 640, GREY, 0.18), ("gn3", "市净率 ≤ 1.5", 760, WHITE, 0.25),
                ("gn4", "=", 880, GREY, 0.45)]
        for key, txt, y, c, u0 in rows:
            q = ease((u - u0) / 0.12)
            if q > 0:
                big_text(frame, key, txt, W / 2, y + 20 * (1 - q), 76, c, q)
        slam(frame, "gn5", "≤ 22.5", W / 2, 1010, 130, RED, u, 0.55)
    elif fx == "graham_formula":     # 价值 = EPS ×（8.5 + 2g）
        q1 = ease(u / 0.15)
        big_text(frame, "gf1", "价值 = 每股收益 ×（8.5 + 2g）", W / 2, 500, 60, WHITE, q1)
        label(frame, "gf1b", "g = 预期年增长率（%）", W / 2, 570, 36, GREY, q1, center=True)
        q2 = ease((u - 0.3) / 0.15)
        if q2 > 0:
            big_text(frame, "gf2", "例：每股收益 2 元，增长率 5%", W / 2, 720, 48, YELLOW, q2)
        q3 = ease((u - 0.5) / 0.15)
        if q3 > 0:
            big_text(frame, "gf3", "2 ×（8.5 + 2×5）", W / 2, 850, 64, WHITE, q3)
        slam(frame, "gf4", "= 37 元", W / 2, 990, 110, GOLD, u, 0.68)
    elif fx == "stock_bond":         # 股票占比在 25%–75% 之间摆动
        bx0, bx1, by, bh = 110, 970, 700, 130
        share = 50 + 25 * math.sin(2 * math.pi * (u * 1.6 - 0.05)) * ease(u / 0.15)
        xs_ = bx0 + (bx1 - bx0) * share / 100
        fill_rect(frame, bx0, by, xs_, by + bh, GOLD, 0.95)
        fill_rect(frame, xs_, by, bx1, by + bh, STEEL, 0.9)
        for v in (25, 75):
            xv = bx0 + (bx1 - bx0) * v / 100
            fill_rect(frame, xv - 3, by - 60, xv + 3, by + bh + 60, RED, 0.95)
            label(frame, ("sb", v), f"{v}%", xv, by + bh + 70, 46, RED, 1, center=True)
        label(frame, ("sbp", int(share)), f"股票 {int(round(share))}%", bx0, by - 110, 56, YELLOW)
        label(frame, "sbl", "债券", bx1 - 100, by - 110, 46, STEEL)
        bull = math.cos(2 * math.pi * (u * 1.6 - 0.05)) < 0
        label(frame, ("sbm", bull), "牛市 → 减股" if bull else "熊市 → 加股", W / 2, 470, 56, WHITE, ease(u / 0.2), center=True)
    elif fx == "diversify10":        # 10–30 只
        n = int(30 * ease(u / 0.8)) if u > 0.05 else 0
        for k in range(30):
            r, c = divmod(k, 6)
            x, y = 165 + c * 130, 500 + r * 100
            col = GOLD if k < 10 else (0.95, 0.85, 0.55)
            fill_rect(frame, x, y, x + 110, y + 80, (0.2, 0.22, 0.3), 0.6)
            if k < n:
                fill_rect(frame, x, y, x + 110, y + 80, col, 0.95)
        label(frame, ("dv", max(10, n)), f"{max(10, n) if n >= 10 else n} 只", W / 2, 1010, 72, YELLOW, 1, center=True)
    elif fx == "leverage":           # 同样跌 30%：不加杠杆 vs 2 倍杠杆
        p = ease((u - 0.2) / 0.5)
        bar(frame, "lv1", 200, 260, 480 * (1 - 0.3 * p), GREY, "不加杠杆", f"-{int(30 * p)}%", 72, WHITE)
        bar(frame, "lv2", 620, 260, 480 * (1 - 0.6 * p), RED, "2倍杠杆", f"-{int(60 * p)}%", 72, RED)
        hdash(frame, 160, 920, BASE - 480, GREY, 0.6, 3)
        label(frame, "lv0", "本金", 120, BASE - 480 - 56, 34, GREY)
    elif fx == "diversify":          # 上百只小便宜股 vs 一只 GEICO
        rng = np.random.default_rng(12)
        hs = rng.uniform(8, 60, 120)
        q = ease(u / 0.5)
        for k in range(120):
            r, c = divmod(k, 24)
            x = 120 + c * 21
            yb = 640 + r * 90
            if k < int(120 * q):
                fill_rect(frame, x, yb - hs[k] * 0.9, x + 14, yb, GREY, 0.85)
        label(frame, "dvs", "数百只便宜股", 370, BASE + 16, 38, WHITE, 1, center=True)
        p = ease((u - 0.4) / 0.4)
        bar(frame, "dvg", 720, 200, 600 * p, GOLD, "GEICO")
    elif fx == "cocoa":              # 股票 → 可可豆仓单 → 价差
        steps = [("c1", "洛克伍德股票", 520, GREY), ("c2", "可可豆仓单", 760, GOLD), ("c3", "价差利润", 1000, YELLOW)]
        for k, (key, txt, cy, c) in enumerate(steps):
            q = ease((u - 0.25 * k) / 0.15)
            if q > 0:
                box(frame, key, txt, W / 2, cy, 620, 130, c, q)
            if k > 0:
                arrow_down(frame, W / 2, cy - 240 + 65, cy - 65 - 8, WHITE, ease((u - 0.25 * k + 0.1) / 0.12))
    elif fx == "ville":              # 门徒业绩柱全部高于市场线
        mk = 0.4
        vals = [0.78, 0.62, 0.9, 0.7, 0.66, 0.84, 0.74, 0.6, 0.95]
        for k, v in enumerate(vals):
            q = ease((u - 0.05 * k) / 0.3)
            x = 130 + k * 94
            fill_rect(frame, x, BASE - v * 560 * q, x + 70, BASE, GOLD, 0.92)
        fill_rect(frame, 110, BASE, 970, BASE + 2, GREY, 0.6)
        a = ease((u - 0.5) / 0.15)
        hdash(frame, 110, 970, BASE - mk * 560, RED, a, 5)
        label(frame, "vm", "市场", 120, BASE - mk * 560 - 60, 40, RED, a)
        label(frame, "vd", "格雷厄姆-多德的门徒们", W / 2, BASE + 20, 40, WHITE, 1, center=True)
    elif fx == "gn_return":          # 约 20% vs 约 12%
        for k, (v, c, name) in enumerate([(20, GOLD, "格雷厄姆-纽曼"), (12, GREY, "同期股市")]):
            x = 200 + k * 420
            p = ease((u - 0.1 * k) / 0.6)
            h = 22 * v * p
            bar(frame, ("gr", k), x, 260, h, c, name)
            if h > 2:
                num_text(frame, f"{v * p:.0f}%", x + 130, BASE - h - 130, 100, c, 1, anchor="c")
        label(frame, "grl", "年化回报（约）", W / 2, 380, 44, WHITE, ease(u / 0.2), center=True)


def criteria_list(frame, t):
    items = ["规模够大", "财务稳健", "连续盈利", "长期分红"]
    for k, it in enumerate(items):
        q = ease((t - 0.8 - 0.55 * k) / 0.25)
        y = 1000 + k * 140
        fill_rect(frame, 170, y, 910, y + 112, (0.95, 0.94, 0.91), 0.95)
        fill_rect(frame, 170, y, 180, y + 112, (0.95, 0.75, 0.0), 1)
        fill_rect(frame, 210, y + 26, 270, y + 86, (0.3, 0.3, 0.32), 1)
        fill_rect(frame, 214, y + 30, 266, y + 82, (1, 1, 1), 1)
        label(frame, ("cr", k), it, 300, y + 12, 54, INK, 1, fname="sans_black")
        if q > 0:
            m = np.zeros((H, W), np.float32)
            pts = np.array([[220, y + 56], [238, y + 76], [282, y + 18]], np.float32)
            cv2.polylines(m, [np.round(pts * 4).astype(np.int32)], False, 1.0, 9, cv2.LINE_AA, shift=2)
            m *= q
            frame *= (1 - m)[..., None]
            frame += m[..., None] * np.array((0.85, 0.12, 0.1), np.float32)


# ------------------------------------------------------------------ 印章
def stamp_sprite():
    if "stamp" not in _cap:
        S = 440
        img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        c = (210, 30, 25, 255)
        d.ellipse((10, 10, S - 10, S - 10), outline=c, width=16)
        d.ellipse((40, 40, S - 40, S - 40), outline=c, width=5)
        f = font("sans_black", 96)
        for k2, ch in enumerate(["错误", "清单"]):
            d.text(((S - f.getlength(ch)) / 2, 96 + k2 * 118), ch, font=f, fill=c)
        img = img.rotate(-12, resample=Image.BICUBIC)
        a = np.asarray(img, np.float32)[..., 3] / 255
        a *= (0.75 + 0.25 * (np.random.default_rng(5).random(a.shape) > 0.15)).astype(np.float32)
        _cap["stamp"] = Sprite(np.asarray(img, np.float32)[..., :3] / 255, a)
    return _cap["stamp"]


# ------------------------------------------------------------------ 片头
def dot_add(acc, px, py, w=1.0):
    ok = (px >= 0) & (px < W) & (py >= 0) & (py < H)
    np.add.at(acc, (py[ok].astype(int), px[ok].astype(int)), w if np.isscalar(w) else w[ok])


def title_frame(t, dur):
    f = np.zeros((H, W, 3), np.float32)
    f[:] = (0.02, 0.025, 0.045)
    if "title" not in _cap:
        _cap["title"] = text_sprite(["本杰明·格雷厄姆"], "serif_black", 128, gold=True)   # 8 字，150px 超出画幅
        _cap["sub"] = text_sprite(["安全边际的守门人"], "serif_semi", 76, color=(0.92, 0.88, 0.8))
        sp = _cap["title"]
        ys, xs = np.nonzero(sp.a > 0.5)
        rng = np.random.default_rng(1)
        sel = rng.choice(len(xs), 3000, replace=False)
        _cap["pts"] = (xs[sel] + (W - sp.w) / 2, ys[sel] + 700, rng.random((3000, 2)) * [W, H], rng.random(3000))
    sp = _cap["title"]
    tx, ty, start, ph = _cap["pts"]
    T = dur - 0.8                   # 标题在镜头末尾前定格
    p = ease_io((t - 0.2) / (T * 0.6))
    ang = (1 - p) * 2.5 * (ph - 0.5)
    dx, dy = start[:, 0] - tx, start[:, 1] - ty
    px = tx + (dx * np.cos(ang) - dy * np.sin(ang)) * (1 - p)
    py = ty + (dx * np.sin(ang) + dy * np.cos(ang)) * (1 - p)
    acc = np.zeros((H, W), np.float32)
    dot_add(acc, px, py)
    acc = cv2.GaussianBlur(acc, (0, 0), 1.6) * 3 + cv2.GaussianBlur(acc, (0, 0), 9) * 7
    f += acc.clip(0, 1.5)[..., None] * np.array([1.0, 0.8, 0.45], np.float32) * (1 - 0.7 * ease((t - T * 0.6) / 0.5))
    rng = np.random.default_rng(9)
    sx, sy, sv = rng.random(260) * W, rng.random(260) * H, 0.3 + rng.random(260)
    snow = np.zeros((H, W), np.float32)
    dot_add(snow, (sx + np.sin(t + sy) * 20) % W, (sy + t * 50 * sv) % H, sv)
    f += cv2.GaussianBlur(snow, (0, 0), 1.8)[..., None] * np.array([0.8, 0.85, 1.0], np.float32) * 2.5
    a = ease((t - T * 0.6) / 0.6)
    blit(f, sp, (W - sp.w) / 2, 700, a)
    blit(f, _cap["sub"], (W - _cap["sub"].w) / 2, 935, ease((t - T * 0.75) / 0.5), wipe=ease((t - T * 0.75) / 0.8))
    return f


# ------------------------------------------------------------------ 片尾：MastersTao 品牌片尾（参照 claude/masters-tao-holdings-video-q3crid 的 sc_end）
LOGO_H = 230          # 官方 logo 高 230px
LOGO_Y = 600          # logo 顶边


def finale_setup():
    if "fin" in _cap:
        return _cap["fin"]
    logo = Sprite(*mt_logo("blue", "logo-dark", LOGO_H))
    lw = logo.w
    lx = (W - lw) / 2
    # 马赛克：片中画面的缩略图拼成满屏
    keys = list(dict.fromkeys(s["bg"] for s in SHOTS if s.get("bg") and s["bg"] != "map"))
    tw, th = 270, 152
    cols, rows = W // tw, int(math.ceil(H / th))
    mosaic = np.zeros((rows * th, cols * tw, 3), np.float32)
    rng = np.random.default_rng(4)
    for r in range(rows):
        for c in range(cols):
            k = keys[(r * cols + c) * 7 % len(keys)]
            mosaic[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = cv2.resize(asset_raw(k), (tw, th), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    mosaic = mosaic[:H, :W]
    # 粒子：起点取自马赛克，终点取自官方 logo 轮廓
    N = 18000
    ys, xs = np.nonzero(logo.a > 0.5)
    sel = rng.choice(len(xs), N, replace=len(xs) < N)
    gx, gy = xs[sel] + lx, ys[sel] + LOGO_Y
    gcol = logo.rgb[ys[sel], xs[sel]]
    sx, sy = rng.random(N) * (W - 1), rng.random(N) * (H - 1)
    scol = np.clip(mosaic[sy.astype(int), sx.astype(int)] * 1.7 + np.array([0.05, 0.07, 0.14], np.float32), 0, 1)
    # 星云与星空（低速品牌光环背景）
    neb = np.zeros((H // 4, W // 4, 3), np.float32)
    for (cx, cy, r, col) in [(0.3, 0.38, 0.55, BA), (0.72, 0.5, 0.6, BB), (0.5, 0.75, 0.5, BA * 0.5 + BB * 0.5)]:
        g = np.exp(-(((np.arange(W // 4)[None, :] / (W / 4) - cx) ** 2 + (np.arange(H // 4)[:, None] / (H / 4) - cy) ** 2 * 0.35) / (2 * (r * 0.35) ** 2)))
        neb += g[..., None] * col * 0.16
    noise = cv2.GaussianBlur(rng.random((H // 4, W // 4)).astype(np.float32), (0, 0), 6)
    neb *= (0.7 + 0.6 * (noise - noise.mean()) / (noise.std() * 3 + 1e-6))[..., None]
    stars = (rng.random((900, 2)) * [W, H], rng.random(900))
    mark_cx = lx + LOGO_H * 0.55          # logo 左侧图形中心
    _cap["fin"] = dict(logo=logo, lx=lx, mosaic=mosaic, gx=gx, gy=gy, gcol=gcol, sx=sx, sy=sy, scol=scol,
                       delay=rng.random(N) * 0.35, spin=(rng.random(N) - 0.5) * 2, neb=neb, stars=stars, mark_cx=mark_cx,
                       f1=text_sprite(["关注 MastersTao"], "sans_black", 68, color=WHITE),
                       f2=text_sprite(["传承大师智慧，领悟投资真谛。"], "sans_bold", 46, color=tuple(INK2)),
                       f3=text_sprite(["masterstao.com"], "sans_bold", 30, color=tuple(INK3 + 0.2), track=3))
    return _cap["fin"]


def particles(F, t, tl, acc, wgt):
    p = np.clip((t - 0.3 - F["delay"]) / (tl - 1.1), 0, 1)   # logo 形状提前约 0.6s 成形
    e = p * p * (3 - 2 * p)
    ang = (1 - e) * 3.2 * F["spin"]
    cx, cy = W / 2, LOGO_Y + LOGO_H / 2
    rx, ry = F["sx"] - cx, F["sy"] - cy
    r = 1 - e
    px = cx + (rx * np.cos(ang) - ry * np.sin(ang)) * r + (F["gx"] - cx) * e
    py = cy + (rx * np.sin(ang) + ry * np.cos(ang)) * r + (F["gy"] - cy) * e
    col = (F["scol"] * (1 - e[:, None]) + F["gcol"] * e[:, None]) * wgt
    ok = (px >= 0) & (px < W - 1) & (py >= 0) & (py < H - 1)
    for c in range(3):
        np.add.at(acc[..., c], (py[ok].astype(int), px[ok].astype(int)), col[ok, c])


def glow_dot(f, cx, cy, r, col, a):
    x0, x1 = int(max(0, cx - 3 * r)), int(min(W, cx + 3 * r))
    y0, y1 = int(max(0, cy - 3 * r)), int(min(H, cy + 3 * r))
    g = np.exp(-((xx[y0:y1, x0:x1] - cx) ** 2 + (yy[y0:y1, x0:x1] - cy) ** 2) / (2 * r * r))
    f[y0:y1, x0:x1] += g[..., None] * col * a


def finale_frame(t, dur):
    F = finale_setup()
    tl = FIN["logo"] - FIN["start"]     # 最后一个大重拍：logo 揭示
    tt = FIN["text"] - FIN["start"]     # 4 拍后：关注语
    f = np.zeros((H, W, 3), np.float32)
    f[:] = PALETTE["bg0"]
    cyl = LOGO_Y + LOGO_H / 2
    # 星云 + 星空（随时间缓慢漂移）
    nb = cv2.resize(F["neb"], (W, H), interpolation=cv2.INTER_LINEAR)
    f += np.roll(nb, int(t * 6), 1) * (0.4 + 0.6 * ease(t / 1.5))
    (sp_, tw_) = F["stars"]
    acc = np.zeros((H, W), np.float32)
    dot_add(acc, (sp_[:, 0] + t * 4) % W, sp_[:, 1], 0.4 + 0.6 * (0.5 + 0.5 * np.sin(t * 3 + tw_ * 20)))
    f += cv2.GaussianBlur(acc, (0, 0), 1.0)[..., None] * np.array([0.8, 0.85, 1.0], np.float32) * 1.6
    # 马赛克闪现 → 碎裂成粒子
    if t < 1.1:
        f += F["mosaic"] * 0.85 * ease(t / 0.15) * (1 - ease((t - 0.3) / 0.6))
    if t < tl + 0.25:
        acc = np.zeros((H, W, 3), np.float32)
        for lag, wgt in ((0.0, 1.0), (0.05, 0.55), (0.1, 0.3), (0.15, 0.15)):   # 运动拖尾
            particles(F, t - lag, tl, acc, wgt)
        acc = cv2.GaussianBlur(acc, (0, 0), 0.9) * 2.4 + cv2.GaussianBlur(acc, (0, 0), 5) * 1.6
        f += acc.clip(0, 2.5) * (1 - ease((t - tl) / 0.25))
    if t >= tl - 0.05:
        q = t - tl
        # 光环隧道：以 logo 为中心向外扩散的品牌渐变椭圆环
        amt = 0.35 * ease(q / 1.0)
        d = np.hypot((xx - W / 2) / 1.0, (yy - cyl) / 0.62)
        for k in range(10):
            rad = ((k / 10 + q * 0.12) % 1.0) ** 1.6 * 1500 + 40
            ring = np.exp(-np.abs(d - rad) / 3.5) * (1 - rad / 1600)
            col = BA * (1 - k / 10) + BB * (k / 10)
            f += ring[..., None] * col * amt
        # 光晕：mark 后
        a = ease(q / 0.9)
        glow_dot(f, F["mark_cx"], cyl, 160, BB * 0.22, a)
        glow_dot(f, F["mark_cx"], cyl, 60, BA * 0.3, a)
        # 官方 logo：从左向右扫光揭示（亮边）
        lg = F["logo"]
        rev = ease((q - 0.0) / 1.4)
        cut = int(lg.w * rev)
        if cut > 0:
            m = lg.a.copy()
            m[:, cut:] = 0
            blit(f, Sprite(lg.rgb, m), F["lx"], LOGO_Y, a)
            lo = max(cut - 36, 0)
            if cut < lg.w:
                edge = np.zeros_like(lg.a)
                edge[:, lo:cut] = lg.a[:, lo:cut] * np.linspace(0, 1, cut - lo)[None, :]
                y0, x0 = LOGO_Y, int(F["lx"])
                f[y0:y0 + lg.h, x0:x0 + lg.w] += edge[..., None] * 1.2 * a
        f += 0.35 * math.exp(-max(q, 0) / 0.15)            # 重拍闪光
    if t >= tt - 0.02:
        q = t - tt
        a = 1.0
        w2 = 300 * ease_io(q / 0.8)                          # 品牌渐变细线
        if w2 > 2:
            ly = int(LOGO_Y + LOGO_H + 90)
            xs_ = np.arange(int(W / 2 - w2), int(W / 2 + w2))
            u = ((xs_ - xs_[0]) / max(1, len(xs_) - 1))[:, None]
            f[ly:ly + 3, xs_] = f[ly:ly + 3, xs_] * 0.2 + ((1 - u) * BA + u * BB)[None, :, :] * 0.95
        blit(f, F["f1"], (W - F["f1"].w) / 2, 1040, ease(q / 0.3), wipe=ease((q - 0.0) / 0.8))
        blit(f, F["f2"], (W - F["f2"].w) / 2, 1166, ease((q - 0.5) / 0.3), wipe=ease((q - 0.5) / 0.9))
        blit_c(f, F["f3"], W / 2, 1360, ease((q - 1.1) / 0.5))
    out = clamp01((t - (dur - 1.6)) / 1.6)
    return f * (1 - ease_io(out))


# ------------------------------------------------------------------ 镜头
def render_shot(i, t):
    s = SHOTS[i]
    dur = T1[i] - T0[i]
    u = clamp01(t / dur)
    kind, fx, bg = s["kind"], s.get("fx"), s.get("bg")
    err = ERR[i]
    ch = CHN[i]
    gt = T0[i] + t
    pulse = beat_pulse(gt, ch)
    if kind == "title":
        return title_frame(t, dur), "dark"
    if kind == "end":
        return finale_frame(t, dur), "dark"
    if kind in ("card", "quote"):
        f = PAPER.copy()
        if err:
            f = f * np.array([0.97, 0.98, 1.0], np.float32)
        draw_card(f, i, t, err)
        if fx == "criteria":
            criteria_list(f, t)
        if fx == "stamp":
            ts = STAMP_T[0] - T0[i]
            p = clamp01((t - ts + 0.12) / 0.12)
            if p > 0:
                sp = stamp_sprite()
                blit_c(f, sp, 790, 420, 0.92 * ease(p), 1 + 1.6 * (1 - ease(p)))
        if fx == "unstamp":
            sp = stamp_sprite()
            blit_c(f, sp, 790, 420, 0.92 * (1 - ease((t - 0.8) / 1.2)))
            g = ease((t - 1.6) / 1.2)
            f += (np.exp(-(((xx - W / 2) / 500) ** 2 + ((yy - H / 2) / 700) ** 2)) * 0.18 * g)[..., None] * np.array([1, 0.8, 0.4], np.float32)
        header(f, i, t)
        draw_tag(f, i, t)
        return f, "paper"
    if kind == "map":
        f, (px, py), lab, inset, org = map_frame(fx, u)
        if org:
            draw_origin(f, org, (px, py), u)
        draw_pin(f, px, py, u, lab, left=bool(org) and org[0] > px + 100)
        if inset and u > 0.62:
            ins = framed_photo(inset, 520, 292)
            q = ease((u - 0.62) / 0.15)
            yy0 = 340 + 30 * (1 - q)
            shadow_under(f, W - 60 - ins.w, yy0, W - 60, yy0 + ins.h, 0.5 * q)
            blit(f, ins, W - 60 - ins.w, yy0, q)
        f *= SCRIM ** 0.7
        header(f, i, t)
        chapter_title(f, i, t)
        draw_caption(f, i, t)
        return f, "dark"
    # photo / film / data：背景模糊 + 中部画面带
    warm = 0.6 if ch == "尾声" else 0.0
    if bg:
        f = bg_blur(bg, u)
        if err:
            f = grade(f, True)
        band = kenburns(bg, u, i, punch=0.03 * pulse)
        band = grade(band, err, mono=ease_io((u - 0.2) / 0.6) if fx == "mono" else 0.0, warm=warm)
        if kind == "data":
            f = f * 0.5 + NAVY * 0.5
            band = band * 0.45
            # 数据镜头：画面带作为背景铺在图表后
        by = BAND_Y
        shadow_under(f, 0, by, W, by + BAND_H, 0.5)
        f[by:by + BAND_H] = band
        # 画面带上下细线
        fill_rect(f, 0, by - 3, W, by, (1, 1, 1), 0.25)
        fill_rect(f, 0, by + BAND_H, W, by + BAND_H + 3, (1, 1, 1), 0.25)
        f *= SCRIM
        f += pulse * 0.05
    else:
        f = NAVY.copy()
    if fx and fx != "mono":
        if kind == "data" and bg:
            f[CY0 - 60:CY1 + 80] *= 0.75
        fx_draw(f, fx, u, t)
    if warm:  # 尾声：暖色漏光
        lk = np.exp(-(((xx - W * (0.2 + 0.6 * u)) / 500) ** 2 + ((yy - 300) / 600) ** 2))
        f += lk[..., None] * np.array([0.35, 0.2, 0.05], np.float32) * 0.6
    header(f, i, t)
    draw_tag(f, i, t)
    chapter_title(f, i, t)
    draw_caption(f, i, t)
    return f, "dark"


# ------------------------------------------------------------------ 转场
def motion_blur_v(img, k):
    k = int(k)
    if k < 3:
        return img
    return cv2.blur(img, (1, k))


def shift_v(img, dy, fill=0.0):
    out = np.full_like(img, fill)
    dy = int(dy)
    if dy >= 0:
        out[dy:] = img[:H - dy] if dy < H else 0
    else:
        out[:H + dy] = img[-dy:]
    return out


def glitch(img, amt, seed):
    rng = np.random.default_rng(seed)
    out = img.copy()
    sh = int(18 * amt)
    out[..., 0] = np.roll(img[..., 0], sh, 1)
    out[..., 2] = np.roll(img[..., 2], -sh, 1)
    for _ in range(int(10 * amt) + 1):
        y0 = rng.integers(0, H - 40)
        h = rng.integers(8, 60)
        out[y0:y0 + h] = np.roll(out[y0:y0 + h], int(rng.integers(-80, 80) * amt), 1)
    return out


def trans_type(i):
    if i == 0:
        return "none"
    if i in CH_START:
        return "impact"
    ch = CHN[i]
    if SHOTS[i]["kind"] == "end":
        return "fade"
    if ch == ERR_CH:
        return "glitch"
    if i in HITCUT:
        return "hit"
    if ENERGY.get(ch, 0.5) < 0.55:
        return "fade"
    return "push"


def frame_at(t):
    i = int(np.searchsorted(T0, t + 1e-6) - 1)
    i = max(0, min(i, len(SHOTS) - 1))
    lt = t - T0[i]
    f, mode = render_shot(i, lt)
    tr = trans_type(i)
    if tr == "push" and lt < 0.24:
        g, _ = render_shot(i - 1, T1[i - 1] - T0[i - 1] + lt)
        k = ease_io(lt / 0.24)
        d = -1 if i % 2 else 1
        blur = 90 * math.sin(math.pi * k)
        f = motion_blur_v(shift_v(g, d * k * H * 0.5), blur) * (1 - k) + motion_blur_v(shift_v(f, -d * (1 - k) * H * 0.5), blur) * k
    elif tr == "fade" and lt < 0.35:
        g, _ = render_shot(i - 1, T1[i - 1] - T0[i - 1] + lt)
        k = ease_io(lt / 0.35)
        f = g * (1 - k) + f * k
    elif tr == "glitch" and lt < 0.16:
        f = glitch(f, 1 - lt / 0.16, int(t * 1000))
    elif tr == "hit" and lt < 0.32:      # 踩在重拍上的切镜
        z = 1 + 0.07 * (1 - ease(lt / 0.3))
        M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
        sh = (1 - lt / 0.32) * 7
        M[0, 2] += math.sin(lt * 90) * sh
        M[1, 2] += math.cos(lt * 77) * sh
        f = cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        f = f + (1 - ease(lt / 0.2)) * 0.45
    elif tr == "impact" and lt < 0.5:
        z = 1 + 0.12 * (1 - ease(lt / 0.45))
        if z > 1.001:
            M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
            sh = (1 - lt / 0.5) * 14
            M[0, 2] += math.sin(lt * 90) * sh
            M[1, 2] += math.cos(lt * 77) * sh
            f = cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        f = f + (1 - ease(lt / 0.35)) * 0.8
    # 统一质感
    f = f * (VIGNETTE if mode != "paper" else VIGNETTE ** 0.5)
    f += cv2.resize(GRAIN[int(t * FPS) % 6], (W, H))[..., None] * 0.02
    if SHOTS[i]["kind"] != "end":
        a = 1.0 if SHOTS[i]["kind"] != "title" else ease((lt - 1.0) / 0.8)
        HUD.draw(f, t, alpha=a)
    if SHOTS[i]["kind"] not in ("title", "end"):
        follow_pill(f, t)
    return np.clip(f, 0, 1)


def to8(f):
    return (f * 255 + 0.5).astype(np.uint8)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "still":
        i, s = int(sys.argv[2]) - 1, float(sys.argv[3])
        Image.fromarray(to8(frame_at(T0[i] + s))).save(sys.argv[4])
    elif cmd == "at":
        Image.fromarray(to8(frame_at(float(sys.argv[2])))).save(sys.argv[3])
    elif cmd == "chunk":
        a, b, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        import subprocess
        p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                              "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                              "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
        for n in range(a, b):
            p.stdin.write(to8(frame_at(n / FPS)).tobytes())
            if n % 150 == 0:
                print(f"{out}: {n}/{b}", flush=True)
        p.stdin.close()
        p.wait()
