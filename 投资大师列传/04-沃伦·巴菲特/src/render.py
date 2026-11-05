"""《沃伦·巴菲特：股神的复利人生》逐帧渲染。

用法：
  python3 src/render.py still <镜头号> <秒> out.png    # 预览单帧（镜头号从 1 开始）
  python3 src/render.py chunk <起始帧> <结束帧> out.mp4  # 渲染一段（无声）
依赖 work/timeline.json（先跑 src/music.py）。帧为 float32 RGB 0..1。
"""
import json, math, os, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
REPO = os.path.join(ROOT, "..", "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "brand"))  # brand/brand.py
from shots import SHOTS
from brand import Hud

W, H, FPS = 1920, 1080, 30
TL = json.load(open(os.path.join(ROOT, "work", "timeline.json")))
T0 = [s["t0"] for s in TL["shots"]]
T1 = [s["t1"] for s in TL["shots"]]

YELLOW = (1.0, 0.83, 0.0)
RED = (1.0, 0.23, 0.19)
WHITE = (1.0, 1.0, 1.0)
INK = (0.13, 0.13, 0.14)
GOLD_STOPS = [(0.0, (255, 243, 200)), (0.35, (255, 212, 120)), (0.62, (226, 160, 60)), (1.0, (255, 214, 130))]

# 章节划分
CH = []
cur = ""
for s in SHOTS:
    cur = s.get("ch") or cur
    CH.append(cur)
ERR = [c == "股神的错误清单" for c in CH]
# 重拍：闪白 + 硬切
HITS = {0}
for i, s in enumerate(SHOTS):
    if s.get("fx") in ("stamp", "compound") or (s["year"] in ("1956年", "1972年") and s.get("ch")) or (s["year"] == "2008年" and s.get("age")):
        HITS.add(i)

# ------------------------------------------------------------------ 工具
_fonts = {}


def font(name, size):
    k = (name, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(os.path.join(ROOT, "fonts", name + ".ttf"), size)
    return _fonts[k]


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def clamp01(x):
    return min(max(x, 0.0), 1.0)


class Sprite:
    """预乘前的 RGB + alpha（float32）。"""

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
    if wipe < 1.0:  # 软边擦除
        edge = min(40, ww)
        ramp = np.ones(x1 - x0, np.float32)
        cols = np.arange(sx, sx + x1 - x0)
        m = cols > ww - edge
        ramp[m] = np.clip((ww - cols[m]) / edge, 0, 1)
        a = a * ramp[None, :, None]
    reg = frame[y0:y1, x0:x1]
    reg *= 1 - a
    reg += a * sp.rgb[sy:sy + y1 - y0, sx:sx + x1 - x0]


def pil_sprite(img):
    arr = np.asarray(img, np.float32) / 255.0
    return Sprite(arr[..., :3].copy(), arr[..., 3].copy())


def parse_runs(line):
    """把【】标出的词拆出来，返回 [(文字, 是否红色)]"""
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


def text_sprite(lines, fname, size, color=WHITE, red=RED, gap=1.35, shadow=True, max_w=None, gold=False):
    """多行文字精灵，支持【红字】、阴影、金色渐变。"""
    f = font(fname, size)
    lines = [l for l in lines if l is not None]
    if max_w:  # 自动换行（按字符宽度）
        out = []
        for l in lines:
            cur = ""
            for ch in l:
                if f.getlength((cur + ch).replace("【", "").replace("】", "")) > max_w and cur:
                    out.append(cur)
                    cur = ""
                    if out[-1].count("【") > out[-1].count("】"):  # 跨行的红字
                        out[-1] += "】"
                        cur = "【"
                cur += ch
            out.append(cur)
        lines = out
    lh = int(size * gap)
    widths = [f.getlength(l.replace("【", "").replace("】", "")) for l in lines]
    pad = int(size * 0.35)
    cw, chh = int(max(widths) + 2 * pad) + 4, lh * (len(lines) - 1) + int(size * 1.45) + 2 * pad
    img = Image.new("RGBA", (cw, chh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    to8 = lambda c: tuple(int(v * 255) for v in c)
    for i, l in enumerate(lines):
        x = pad
        y = pad + i * lh
        for txt, isred in parse_runs(l):
            d.text((x, y), txt, font=f, fill=to8(red if isred else color) + (255,))
            x += f.getlength(txt)
    if gold:
        a = np.asarray(img, np.float32)[..., 3] / 255
        ys = np.linspace(0, 1, chh)
        ramp = np.zeros((chh, 3), np.float32)
        for c in range(3):
            ramp[:, c] = np.interp(ys, [p for p, _ in GOLD_STOPS], [v[c] / 255 for _, v in GOLD_STOPS])
        rgb = np.repeat(ramp[:, None, :], cw, 1)
        sp = Sprite(rgb, a)
    else:
        sp = pil_sprite(img)
    if shadow:
        sh = cv2.GaussianBlur(sp.a, (0, 0), size * 0.08 + 1.5) * 0.85
        sh = np.roll(np.roll(sh, 3, 0), 2, 1)
        a = sp.a + sh * (1 - sp.a)
        rgb = sp.rgb * (sp.a / np.maximum(a, 1e-4))[..., None]
        sp = Sprite(rgb, a)
    return sp


def rect_sprite(w, h, color, alpha=1.0):
    return Sprite(np.full((h, w, 3), color, np.float32), np.full((h, w), alpha, np.float32))


def fill_rect(frame, x0, y0, x1, y1, color, alpha=1.0):
    x0, y0, x1, y1 = max(int(x0), 0), max(int(y0), 0), min(int(x1), W), min(int(y1), H)
    if x1 <= x0 or y1 <= y0:
        return
    reg = frame[y0:y1, x0:x1]
    reg *= 1 - alpha
    reg += np.array(color, np.float32) * alpha


# ------------------------------------------------------------------ 全局层
_rng = np.random.default_rng(7)
GRAIN = [(_rng.standard_normal((H // 2, W // 2)).astype(np.float32)) for _ in range(6)]
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIGNETTE = (1 - 0.42 * (((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.68)) ** 2) ** 1.4).clip(0.35, 1)[..., None]
# 左下字幕区压暗
SCRIM = (1 - 0.62 * np.clip(1 - (xx / (W * 0.72)), 0, 1) ** 1.2 * np.clip((yy - H * 0.38) / (H * 0.62), 0, 1) ** 1.1)[..., None]
HUD = Hud()
DISCLAIM = text_sprite(["画面为 AI 生成示意 · 数据以公开资料为准"], "sans_reg", 20, color=(0.82, 0.82, 0.82), shadow=True)


def paper_bg():
    rng = np.random.default_rng(3)
    base = np.full((H, W, 3), (0.86, 0.86, 0.85), np.float32)
    n = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 1.2) * 0.018
    base += n[..., None]
    # 网点纹理（越靠右下越密）
    dots = np.zeros((H, W), np.float32)
    step = 14
    for y in range(0, H, step):
        for x in range(0, W, step):
            r = 2.2 * clamp01((x / W + y / H - 0.9) * 1.4)
            if r > 0.4:
                cv2.circle(dots, (x, y), int(round(r)), 1.0, -1, cv2.LINE_AA)
    base -= dots[..., None] * 0.07
    return base * (1 - 0.18 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2))[..., None]


PAPER = paper_bg()


def navy_bg():
    g = np.zeros((H, W, 3), np.float32)
    g[:] = (0.035, 0.05, 0.085)
    g += (np.exp(-(((xx - W * 0.62) / (W * 0.5)) ** 2 + ((yy - H * 0.4) / (H * 0.6)) ** 2)) * 0.09)[..., None] * np.array([0.5, 0.8, 1.4], np.float32)
    for x in range(0, W, 96):
        g[:, x:x + 1] += 0.018
    for y in range(0, H, 96):
        g[y:y + 1, :] += 0.018
    return g


NAVY = navy_bg()

# ------------------------------------------------------------------ 素材图
_img_cache = {}
FALLBACK = {"ketchup": "offer", "warehouse": "dotcom", "house": "partners", "crowd": "arena", "podium": "meeting"}  # Gemini 额度不足时的替补素材


def asset(key):
    if key not in _img_cache:
        p = os.path.join(ROOT, "assets", key + ".jpg")
        if not os.path.exists(p):
            p = os.path.join(ROOT, "assets", FALLBACK.get(key, "stamp") + ".jpg")
        im = cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)
        h, w = im.shape[:2]
        # 裁掉 3% 边，去掉生成图偶尔带的相框
        im = im[int(h * 0.03):int(h * 0.97), int(w * 0.03):int(w * 0.97)]
        im = cv2.resize(im, (int(W * 1.18), int(H * 1.18)), interpolation=cv2.INTER_AREA)
        _img_cache[key] = im
    return _img_cache[key]


def kenburns(key, u, i):
    im = asset(key)
    ih, iw = im.shape[:2]
    mode = i % 4
    z0, z1 = (1.0, 1.1) if mode in (0, 2) else (1.1, 1.0)
    z = z0 + (z1 - z0) * ease_io(u)
    base = max(W / iw, H / ih)
    s = base * z
    px = {0: (0.5, 0.5), 1: (0.5, 0.5), 2: (0.42, 0.58), 3: (0.6, 0.45)}[mode]
    cx = iw * (px[0] + (0.5 - px[0]) * u)
    cy = ih * (px[1] + (0.5 - px[1]) * u)
    M = np.array([[s, 0, W / 2 - cx * s], [0, s, H / 2 - cy * s]], np.float32)
    out = cv2.warpAffine(im, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return out.astype(np.float32) / 255.0


def grade(img, err=False, mono=0.0):
    if err or mono > 0:
        g = img.mean(2, keepdims=True)
        k = 0.65 if err else mono
        img = img * (1 - k) + g * k
        if err:
            img = img * np.array([0.9, 0.96, 1.08], np.float32)
    return img


# ------------------------------------------------------------------ 字幕（参照片版式）
_cap = {}


def caption_sprites(i):
    if i in _cap:
        return _cap[i]
    s = SHOTS[i]
    yr = s["year"]
    big = None
    if yr:
        f1 = font("sans_black", 104)
        f2 = font("sans_black", 78)
        age = f"-{s['age']}" if s["age"] else ""
        w1, w2 = f1.getlength(yr), f2.getlength(age)
        img = Image.new("RGBA", (int(w1 + w2) + 40, 150), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.text((10, 6), yr, font=f1, fill=(255, 212, 0, 255))
        if age:
            d.text((10 + w1 + 4, 32), age, font=f2, fill=(255, 212, 0, 255))
        sp = pil_sprite(img)
        sh = np.roll(np.roll(cv2.GaussianBlur(sp.a, (0, 0), 6) * 0.8, 4, 0), 3, 1)
        a = sp.a + sh * (1 - sp.a)
        big = Sprite(sp.rgb * (sp.a / np.maximum(a, 1e-4))[..., None], a)
    lines = None if s.get("fx") == "compound" else text_sprite(s["lines"], "sans_black", 48, gap=1.4, max_w=1500)
    _cap[i] = (big, lines)
    return _cap[i]


def draw_caption(frame, i, t):
    big, lines = caption_sprites(i)
    x = 118
    ly = 818 if big else 800
    a = ease(t / 0.35)
    if big:
        blit(frame, big, x - 12 - 50 * (1 - ease(t / 0.4)), ly - 136, a)
    if lines is None:
        return
    bar_h = lines.h - 26
    grow = ease((t - 0.1) / 0.35)
    fill_rect(frame, x, ly + 12, x + 9, ly + 12 + bar_h * grow, YELLOW, a)
    blit(frame, lines, x + 18, ly, a, wipe=ease((t - 0.18) / 0.7))


def draw_tag(frame, i, t):
    tag = SHOTS[i].get("tag")
    if not tag:
        return
    k = ("tag", i)
    if k not in _cap:
        sp = text_sprite([f"错误清单 {tag}"], "sans_black", 34, color=WHITE, shadow=False)
        _cap[k] = sp
    sp = _cap[k]
    a = ease(t / 0.25)
    x, y = 70, 54
    fill_rect(frame, x, y, x + sp.w + 18, y + sp.h - 6, (0.82, 0.1, 0.08), 0.92 * a)
    blit(frame, sp, x + 9, y - 3, a)


# ------------------------------------------------------------------ 纸卡 / 引语卡
def framed_photo(key, w, h):
    im = asset(key)
    im = cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    b = 14
    rgb = np.ones((h + 2 * b, w + 2 * b, 3), np.float32) * 0.97
    rgb[b:b + h, b:b + w] = im
    return Sprite(rgb, np.ones(rgb.shape[:2], np.float32))


def shadow_under(frame, x0, y0, x1, y1, strength=0.35, blur=22):
    m = np.zeros((H, W), np.float32)
    cv2.rectangle(m, (int(x0) + 8, int(y0) + 12), (int(x1) + 8, int(y1) + 12), 1.0, -1)
    m = cv2.GaussianBlur(m, (0, 0), blur)
    frame *= (1 - m * strength)[..., None]


def draw_card(frame, i, t, err=False):
    s = SHOTS[i]
    k = ("card", i)
    has_photo = bool(s.get("bg"))
    if k not in _cap:
        yr = s["year"] + (f"-{s['age']}" if s["age"] else "")
        head = text_sprite([yr], "sans_black", 64, color=(0.87, 0.62, 0.0), shadow=False) if yr else None
        quote = any("「" in l for l in s["lines"])
        body = text_sprite(s["lines"], "serif_black" if quote else "sans_black", 46 if has_photo else 64,
                           color=INK, red=(0.85, 0.12, 0.1), gap=1.5, shadow=False, max_w=880 if has_photo else 1200)
        photo = framed_photo(s["bg"], 640, 430) if has_photo else None
        _cap[k] = (head, body, photo)
    head, body, photo = _cap[k]
    a = ease(t / 0.4)
    dy = 30 * (1 - ease(t / 0.5))
    if photo:
        px, py = 1150, 250
        shadow_under(frame, px, py + dy, px + photo.w, py + photo.h + dy, 0.4 * a)
        blit(frame, photo, px, py + dy, a)
    cw = (body.w + 90) if photo else max(body.w + 120, 900)
    hh = (head.h if head else 0)
    ch = body.h + hh + 70
    cx = 140 if photo else (W - cw) // 2
    cy = (H - ch) // 2 + (60 if photo else 0)
    shadow_under(frame, cx, cy + dy, cx + cw, cy + ch + dy, 0.3 * a)
    fill_rect(frame, cx, cy + dy, cx + cw, cy + ch + dy, (0.95, 0.94, 0.91), a)
    fill_rect(frame, cx, cy + dy, cx + 10, cy + ch + dy, (0.95, 0.75, 0.0) if not err else (0.82, 0.1, 0.08), a)
    fill_rect(frame, cx, cy + dy, cx + cw, cy + 6 + dy, (0.95, 0.75, 0.0) if not err else (0.82, 0.1, 0.08), a)
    y = cy + 34 + dy
    if head:
        blit(frame, head, cx + 40, y - 14, a)
        y += hh - 10
    blit(frame, body, cx + 40, y, a, wipe=ease((t - 0.25) / 0.9))


# ------------------------------------------------------------------ 点阵地图
from global_land_mask import globe

MAPS = {
    "omaha": ((-60, 30, 3.2), (-95.94, 41.26, 13), "奥马哈", None),
    "newyork": ((-95.9, 41.3, 13), (-73.96, 40.81, 34), "纽约 · 哥伦比亚大学", None),
    "wallst": ((-80, 40, 20), (-74.01, 40.706, 110), "纽约 · 华尔街", None),
    "omaha_house": ((-80, 38, 9), (-95.94, 41.26, 22), "奥马哈 · 法纳姆街", "house"),
    "beijing": ((80, 30, 4), (116.4, 39.9, 26), "北京", None),
    "shenzhen": ((116.4, 39.9, 14), (114.06, 22.54, 40), "深圳", "byd"),
    "tokyo": ((-96, 41, 9), (139.7 - 360, 35.7, 30), "东京", "tokyo"),
}
STEP = 10
_gy, _gx = np.mgrid[STEP // 2:H:STEP, STEP // 2:W:STEP].astype(np.float32)
_dot = np.zeros((STEP, STEP), np.float32)
cv2.circle(_dot, (STEP // 2, STEP // 2), 3, 1.0, -1, cv2.LINE_AA)
DOTS = np.tile(_dot, (H // STEP + 1, W // STEP + 1))[:H, :W]


def map_frame(key, u):
    (lo0, la0, s0), (lo1, la1, s1), label, inset = MAPS[key]
    e = ease_io(min(u / 0.62, 1))
    lo = lo0 + (lo1 - lo0) * e
    la = la0 + (la1 - la0) * e
    sc = math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * e)
    if key == "tokyo":  # 跨太平洋时先拉远
        sc = sc / (1 + 4.0 * math.sin(math.pi * e))
    sc *= 1 + 0.06 * u
    lon = lo + (_gx - W / 2) / sc
    lat = la - (_gy - H / 2) / sc
    lon = (lon + 180) % 360 - 180
    land = globe.is_land(np.clip(lat, -89.9, 89.9), lon).astype(np.float32)
    big = cv2.resize(land, (W, H), interpolation=cv2.INTER_NEAREST)
    f = NAVY.copy() * 0.9
    # 离目标越近的点越亮
    tx = W / 2 + (lo1 - lo) * sc
    ty = H / 2 - (la1 - la) * sc
    near = np.exp(-(((xx - tx) ** 2 + (yy - ty) ** 2) / (2 * 420 ** 2)))
    col = np.array([0.22, 0.36, 0.55], np.float32)[None, None] + near[..., None] * np.array([0.2, 0.25, 0.3], np.float32)
    f += (big * DOTS)[..., None] * col
    # 海洋上的淡点
    f += ((1 - big) * DOTS)[..., None] * 0.025
    return f, (tx, ty), label, inset


def draw_pin(frame, x, y, u, label):
    k = ("pin", label)
    if k not in _cap:
        _cap[k] = text_sprite([label], "sans_black", 40, color=YELLOW)
    lab = _cap[k]
    p = clamp01((u - 0.5) / 0.12)
    if p <= 0:
        return
    drop = (1 - ease(p)) * -120
    bounce = math.sin(p * math.pi * 2) * 8 * (1 - p)
    py = y + drop + bounce
    # 脉冲圈
    q = ((u - 0.6) * 1.5) % 1.0 if u > 0.6 else 0
    if q > 0:
        m = np.zeros((H, W), np.float32)
        cv2.circle(m, (int(x), int(y)), int(10 + 70 * q), 1.0, 3, cv2.LINE_AA)
        frame += (m * (1 - q) * 0.8)[..., None] * np.array(RED, np.float32)
    m = np.zeros((H, W), np.float32)
    cv2.circle(m, (int(x), int(py - 34)), 17, 1.0, -1, cv2.LINE_AA)
    pts = np.array([[x - 15, py - 26], [x + 15, py - 26], [x, py]], np.int32)
    cv2.fillPoly(m, [pts], 1.0, cv2.LINE_AA)
    frame *= (1 - m)[..., None]
    frame += m[..., None] * np.array([0.9, 0.12, 0.1], np.float32)
    m2 = np.zeros((H, W), np.float32)
    cv2.circle(m2, (int(x), int(py - 34)), 6, 1.0, -1, cv2.LINE_AA)
    frame *= (1 - m2)[..., None]
    frame += m2[..., None]
    blit(frame, lab, x + 28, py - 70, ease(p), wipe=ease((u - 0.56) / 0.15))


# ------------------------------------------------------------------ 数据动画
def polyline(frame, pts, color, th=6, glow=True, prog=1.0):
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
        g = cv2.GaussianBlur(m, (0, 0), 10)
        frame += g[..., None] * np.array(color, np.float32) * 0.6
    frame *= (1 - m)[..., None]
    frame += m[..., None] * np.array(color, np.float32)
    return pts[-1]


def dot(frame, x, y, r, color, a=1.0):
    m = np.zeros((H, W), np.float32)
    cv2.circle(m, (int(x), int(y)), int(r), 1.0, -1, cv2.LINE_AA)
    m *= a
    frame *= (1 - m)[..., None]
    frame += m[..., None] * np.array(color, np.float32)


def label(frame, key, text, x, y, size=34, color=WHITE, a=1.0, fname="sans_black", center=False):
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
    ox = {"l": 0, "c": sp.w / 2, "r": sp.w}[anchor]
    blit(frame, sp, x - ox, y, a)


def chart_axes(frame, x0, y0, x1, y1, a=1.0):
    fill_rect(frame, x0, y1, x1, y1 + 2, (0.6, 0.65, 0.75), 0.6 * a)
    for k in range(1, 4):
        yy_ = y0 + (y1 - y0) * k / 4
        fill_rect(frame, x0, yy_, x1, yy_ + 1, (0.6, 0.65, 0.75), 0.15 * a)


def fx_draw(frame, fx, u, t, dur):
    GOLD = (1.0, 0.78, 0.25)
    GREY = (0.6, 0.63, 0.7)
    if fx in ("stock38", "stock200"):
        x0, x1, y0, y1 = 860, 1780, 200, 680
        vals = [38, 33, 27, 31, 36, 40] + ([55, 80, 70, 120, 150, 200] if fx == "stock200" else [])
        vmax = 210 if fx == "stock200" else 45
        vmin = 0 if fx == "stock200" else 20
        n = 12 if fx == "stock200" else 6
        chart_axes(frame, x0, y0, x1, y1)
        pts = [(x0 + (x1 - x0) * k / (n - 1), y1 - (v - vmin) / (vmax - vmin) * (y1 - y0)) for k, v in enumerate(vals)]
        if fx == "stock38":
            prog = ease(u / 0.8)
            end = polyline(frame, pts, GOLD, prog=prog)
            dot(frame, *end, 9, GOLD)
            if u > 0.05:
                label(frame, "b", "$38 买入", pts[0][0] - 20, pts[0][1] - 70, 34, WHITE, ease((u - 0.05) / 0.1))
            if u > 0.42:
                label(frame, "l", "$27", pts[2][0] - 30, pts[2][1] + 14, 34, RED, ease((u - 0.42) / 0.1))
            if u > 0.8:
                dot(frame, *pts[5], 13, RED)
                label(frame, "s", "$40 卖出", pts[5][0] - 150, pts[5][1] - 76, 36, YELLOW, ease((u - 0.8) / 0.1))
        else:
            polyline(frame, pts[:6], GREY, glow=False)
            dot(frame, *pts[5], 11, GREY)
            label(frame, "s2", "卖出", pts[5][0] - 34, pts[5][1] + 20, 30, GREY)
            end = polyline(frame, pts[5:], GOLD, prog=ease(u / 0.75))
            dot(frame, *end, 10, GOLD)
            if u > 0.75:
                num_text(frame, "$200", pts[-1][0] - 10, pts[-1][1] - 100, 80, YELLOW, ease((u - 0.75) / 0.1), anchor="r")
    elif fx == "count5000":
        v = int(5000 * ease(u / 0.7))
        num_text(frame, f"${v:,}", 1400, 300, 200, YELLOW, 1.0, gold=True, anchor="c")
    elif fx == "bars69":
        base = 690
        for k, (v, c, name) in enumerate([(29.5, GOLD, "巴菲特合伙公司"), (7.4, GREY, "道琼斯指数")]):
            x = 1080 + k * 330
            h = 15 * v * ease((u - 0.1 * k) / 0.6)
            fill_rect(frame, x, base - h, x + 200, base, c, 0.95)
            if h > 2:
                num_text(frame, f"{v * ease((u - 0.1 * k) / 0.6):.1f}%", x + 100, base - h - 110, 84, c, 1, anchor="c")
            label(frame, ("bar", k), name, x + 100, base + 14, 32, WHITE, 1, center=True)
    elif fx == "dotcom_cross":
        x0, x1, y0, y1 = 860, 1780, 200, 660
        chart_axes(frame, x0, y0, x1, y1)
        nas = [0.15, 0.3, 0.55, 0.95, 0.6, 0.35, 0.22]
        brk = [0.4, 0.33, 0.3, 0.38, 0.45, 0.5, 0.56]
        P = lambda vals: [(x0 + (x1 - x0) * k / 6, y1 - v * (y1 - y0)) for k, v in enumerate(vals)]
        e = polyline(frame, P(nas), RED, prog=ease(u / 0.8))
        dot(frame, *e, 8, RED)
        e2 = polyline(frame, P(brk), GOLD, prog=ease(u / 0.8))
        dot(frame, *e2, 8, GOLD)
        if u > 0.8:
            label(frame, "n", "纳斯达克", P(nas)[-1][0] - 150, P(nas)[-1][1] + 10, 32, RED, ease((u - 0.8) / 0.1))
            label(frame, "k", "伯克希尔", P(brk)[-1][0] - 150, P(brk)[-1][1] - 60, 32, YELLOW, ease((u - 0.8) / 0.1))
    elif fx == "apple":
        x0, x1, y0, y1 = 900, 1780, 220, 640
        vals = [0.05, 0.08, 0.15, 0.22, 0.3, 0.45, 0.6, 0.72, 0.9]
        pts = [(x0 + (x1 - x0) * k / 8, y1 - v * (y1 - y0)) for k, v in enumerate(vals)]
        e = polyline(frame, pts, GOLD, prog=ease(u / 0.8))
        dot(frame, *e, 10, GOLD)
        if u > 0.75:
            label(frame, "ap", "第一大持仓", e[0] - 200, e[1] - 70, 40, YELLOW, ease((u - 0.75) / 0.1))
    elif fx == "dexter":
        a = ease(u / 0.3)
        label(frame, "d1", "当时付出", 1000, 250, 34, WHITE, a)
        label(frame, "d1n", "4.33亿美元", 1000, 290, 104, GREY, a)
        label(frame, "d1b", "伯克希尔股票", 1000, 450, 30, GREY, a)
        if u > 0.4:
            b = ease((u - 0.4) / 0.25)
            label(frame, "d2", "这些股票后来价值", 1000, 540, 34, WHITE, b)
            label(frame, "d3", "数十亿美元", 1000, 590, 104, RED, b, fname="sans_black")
    elif fx == "oil":
        x0, x1, y0, y1 = 860, 1780, 200, 660
        vals = [0.2, 0.3, 0.45, 0.7, 0.95, 0.4, 0.25, 0.35]
        pts = [(x0 + (x1 - x0) * k / 7, y1 - v * (y1 - y0)) for k, v in enumerate(vals)]
        chart_axes(frame, x0, y0, x1, y1)
        e = polyline(frame, pts, (1.0, 0.6, 0.2), prog=ease(u / 0.8))
        dot(frame, *e, 8, (1.0, 0.6, 0.2))
        if u > 0.4:
            dot(frame, *pts[4], 14, RED)
            label(frame, "o1", "$147 买在高点", pts[4][0] - 120, pts[4][1] - 74, 34, RED, ease((u - 0.4) / 0.1))
    elif fx == "shrink":
        h = 420 * (1 - 0.55 * ease((u - 0.25) / 0.5))
        fill_rect(frame, 1350, 680 - 420, 1550, 680, (0.4, 0.4, 0.45), 0.35)
        fill_rect(frame, 1350, 680 - h, 1550, 680, RED, 0.9)
        label(frame, "sh", "估值缩水", 1450, 700, 34, WHITE, 1, center=True)
    elif fx == "writedown":
        p = ease((u - 0.2) / 0.15)
        if p > 0:
            label(frame, "wd", "-100亿美元", 1340, 330, 130, RED, p, center=True)
    elif fx == "cash":
        v = 3000 * ease(u / 0.7)
        h = 0.13 * v
        fill_rect(frame, 1300, 700 - h, 1560, 700, GOLD, 0.92)
        label(frame, ("cv", int(v) // 50), f"{int(v) // 50 * 50}亿美元", 1430, 700 - h - 110, 64, YELLOW, 1, center=True)
        label(frame, "c1", "现金储备", 1430, 716, 32, WHITE, 1, center=True)
    elif fx == "compound":
        p = ease(u / 0.75)
        label(frame, "c0", "1965–2024 累计涨幅", W / 2, 150, 40, WHITE, ease(u / 0.2), center=True)
        label(frame, "ca", "伯克希尔", 640, 260, 44, YELLOW, 1, center=True)
        num_text(frame, f"{int(5502284 * p):,}%", 640, 320, 120, YELLOW, 1, gold=True, anchor="c")
        label(frame, "cb", "标普500", 1300, 260, 44, GREY, 1, center=True)
        num_text(frame, f"{int(39054 * p):,}%", 1300, 320, 120, GREY, 1, anchor="c")
        if u > 0.55:
            q = ease((u - 0.55) / 0.15)
            label(frame, "c3", "年化 19.9%", 640, 490, 54, WHITE, q, center=True)
            label(frame, "c4", "年化 10.4%", 1300, 490, 54, GREY, q, center=True)
    elif fx == "wealth":
        x0, x1, y0, y1 = 860, 1780, 200, 660
        chart_axes(frame, x0, y0, x1, y1)
        ages = np.linspace(11, 95, 120)
        vals = np.exp((ages - 95) / 9.5)
        pts = [(x0 + (x1 - x0) * (a_ - 11) / 84, y1 - v * (y1 - y0)) for a_, v in zip(ages, vals)]
        xs65 = x0 + (x1 - x0) * (65 - 11) / 84
        if u > 0.3:
            fill_rect(frame, xs65, y0, x1, y1, YELLOW, 0.1 * ease((u - 0.3) / 0.2))
            fill_rect(frame, xs65, y0, xs65 + 2, y1, YELLOW, 0.7 * ease((u - 0.3) / 0.2))
            label(frame, "w65", "65岁", xs65 - 40, y1 + 10, 34, YELLOW, ease((u - 0.3) / 0.2))
        e = polyline(frame, pts, GOLD, prog=ease(u / 0.85))
        dot(frame, *e, 9, GOLD)
        label(frame, "w11", "11岁", x0 - 20, y1 + 10, 30, GREY)
        label(frame, "w95", "95岁", x1 - 60, y1 + 10, 30, GREY)


# ------------------------------------------------------------------ 印章
def stamp_sprite():
    k = "stamp"
    if k not in _cap:
        S = 420
        img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        c = (210, 30, 25, 255)
        d.ellipse((10, 10, S - 10, S - 10), outline=c, width=16)
        d.ellipse((40, 40, S - 40, S - 40), outline=c, width=5)
        f = font("sans_black", 92)
        for k2, ch in enumerate(["错误", "清单"]):
            w = f.getlength(ch)
            d.text(((S - w) / 2, 92 + k2 * 112), ch, font=f, fill=c)
        img = img.rotate(-12, resample=Image.BICUBIC)
        a = np.asarray(img, np.float32)[..., 3] / 255
        rng = np.random.default_rng(5)
        a *= (0.75 + 0.25 * (rng.random(a.shape) > 0.15)).astype(np.float32)
        _cap[k] = Sprite(np.asarray(img, np.float32)[..., :3] / 255, a)
    return _cap[k]


# ------------------------------------------------------------------ 片头 / 片尾
def title_frame(t):
    f = np.zeros((H, W, 3), np.float32)
    f[:] = (0.02, 0.025, 0.045)
    if "title" not in _cap:
        _cap["title"] = text_sprite(["沃伦·巴菲特"], "serif_black", 150, gold=True)
        _cap["sub"] = text_sprite(["股神的复利人生"], "serif_semi", 64, color=(0.92, 0.88, 0.8))
        _cap["ser"] = text_sprite(["投资大师列传 · 04"], "sans_bold", 30, color=(0.75, 0.7, 0.6))
        sp = _cap["title"]
        ys, xs = np.nonzero(sp.a > 0.5)
        rng = np.random.default_rng(1)
        sel = rng.choice(len(xs), 2600, replace=False)
        _cap["pts"] = (xs[sel] + (W - sp.w) / 2, ys[sel] + 330, rng.random((2600, 2)) * [W, H], rng.random(2600))
    sp = _cap["title"]
    tx, ty, start, ph = _cap["pts"]
    p = ease_io((t - 0.2) / 1.6)
    px = start[:, 0] + (tx - start[:, 0]) * p
    py = start[:, 1] + (ty - start[:, 1]) * p + np.sin(ph * 6 + t * 2) * 6 * (1 - p)
    acc = np.zeros((H, W), np.float32)
    ok = (px >= 0) & (px < W) & (py >= 0) & (py < H)
    np.add.at(acc, (py[ok].astype(int), px[ok].astype(int)), 1.0)
    acc = cv2.GaussianBlur(acc, (0, 0), 1.6) * 3 + cv2.GaussianBlur(acc, (0, 0), 8) * 6
    f += acc.clip(0, 1.5)[..., None] * np.array([1.0, 0.8, 0.45], np.float32) * (1 - 0.7 * ease((t - 1.7) / 0.5))
    # 飘雪
    rng = np.random.default_rng(9)
    sx, sy, sv = rng.random(220) * W, rng.random(220) * H, 0.3 + rng.random(220)
    for x_, y_, v_ in zip(sx, sy, sv):
        dot(f, x_ + math.sin(t + y_) * 20, (y_ + t * 40 * v_) % H, 1.5 + v_, (0.8, 0.85, 1.0), 0.25 * v_)
    a = ease((t - 1.6) / 0.6)
    blit(f, sp, (W - sp.w) / 2, 330, a)
    blit(f, _cap["sub"], (W - _cap["sub"].w) / 2, 545, ease((t - 2.0) / 0.5), wipe=ease((t - 2.0) / 0.8))
    fill_rect(f, W / 2 - 240 * ease((t - 1.9) / 0.6), 530, W / 2 + 240 * ease((t - 1.9) / 0.6), 532, (0.9, 0.7, 0.3), 0.8)
    blit(f, _cap["ser"], (W - _cap["ser"].w) / 2, 660, ease((t - 2.4) / 0.5))
    return f


def end_frame(t, dur):
    f = np.zeros((H, W, 3), np.float32)
    f[:] = (0.02, 0.025, 0.045)
    if "logo" not in _cap:
        lg = Image.open(os.path.join(REPO, "brand", "logo_baman.png")).convert("RGBA").resize((300, 300), Image.LANCZOS)
        _cap["logo"] = pil_sprite(lg)
        PADG = 120  # 光晕要在加了边距的画布上模糊，否则会被裁出方框
        _cap["logo_glow"] = cv2.GaussianBlur(np.pad(_cap["logo"].a, PADG), (0, 0), 30)
        _cap["e1"] = text_sprite(["巴芒价值"], "serif_black", 120, gold=True)
        _cap["e2"] = text_sprite(["B U F F E T T  ·  M U N G E R"], "corm", 40, color=(0.84, 0.7, 0.44), shadow=False)
        _cap["e3"] = text_sprite(["投资大师列传 · 04 沃伦·巴菲特：股神的复利人生"], "sans_bold", 30, color=(0.7, 0.7, 0.72))
    a = ease(t / 0.8)
    lg = _cap["logo"]
    x, y = (W - 300) / 2, 170
    g = _cap["logo_glow"]
    gy, gx = int(y) - 120, int(x) - 120
    f[gy:gy + g.shape[0], gx:gx + g.shape[1]] += g[..., None] * np.array([0.43, 0.69, 1.0], np.float32) * 0.35 * a
    blit(f, lg, x, y - 20 * (1 - a), a)
    e1 = _cap["e1"]
    blit(f, e1, (W - e1.w) / 2, 500, ease((t - 0.5) / 0.6))
    e2 = _cap["e2"]
    blit(f, e2, (W - e2.w) / 2, 700, ease((t - 0.9) / 0.6))
    e3 = _cap["e3"]
    blit(f, e3, (W - e3.w) / 2, 830, ease((t - 1.5) / 0.6))
    # 流光扫过「巴芒价值」
    if 2.0 < t < 3.4:
        q = (t - 2.0) / 1.4
        band = np.exp(-((xx[500:500 + e1.h, :] + yy[500:500 + e1.h, :] * 0.6 - (W * 0.3 + W * 0.5 * q)) / 30) ** 2)
        f[500:500 + e1.h] += band[..., None] * 0.5 * np.pad(e1.a, ((0, 0), ((W - e1.w) // 2, W - e1.w - (W - e1.w) // 2)))[..., None]
    out = max(0.0, (t - (dur - 1.6)) / 1.6)
    return f * (1 - ease_io(out))


# ------------------------------------------------------------------ 镜头
def render_shot(i, t):
    s = SHOTS[i]
    dur = T1[i] - T0[i]
    u = clamp01(t / dur)
    kind, fx, bg = s["kind"], s.get("fx"), s.get("bg")
    err = ERR[i]
    if kind == "title":
        return title_frame(t), False
    if kind == "end":
        return end_frame(t, dur), False
    if kind in ("card", "quote"):
        f = PAPER.copy()
        if err:
            f = f * np.array([0.97, 0.98, 1.0], np.float32)
        draw_card(f, i, t, err)
        if fx == "stamp":
            p = clamp01((t - 0.7) / 0.18)
            if p > 0:
                sp = stamp_sprite()
                sc_ = 1 + 1.4 * (1 - ease(p))
                img = cv2.resize(sp.rgb, None, fx=sc_, fy=sc_)
                al = cv2.resize(sp.a, None, fx=sc_, fy=sc_)
                blit(f, Sprite(img, al), 1500 - img.shape[1] / 2, 320 - img.shape[0] / 2, 0.92 * ease(p))
        if fx == "unstamp":
            sp = stamp_sprite()
            blit(f, sp, 1500 - sp.w / 2, 320 - sp.h / 2, 0.92 * (1 - ease((t - 0.8) / 1.2)))
            g = ease((t - 1.6) / 1.2)
            f += (np.exp(-(((xx - W / 2) / 700) ** 2 + ((yy - H / 2) / 400) ** 2)) * 0.18 * g)[..., None] * np.array([1, 0.8, 0.4], np.float32)
        draw_tag(f, i, t)
        return f, True
    if kind == "map":
        f, (px, py), lab, inset = map_frame(fx, u)
        draw_pin(f, px, py, u, lab)
        if inset and u > 0.62:
            ins = framed_photo(inset, 460, 300)
            q = ease((u - 0.62) / 0.15)
            shadow_under(f, 1380, 120 + 30 * (1 - q), 1380 + ins.w, 120 + ins.h + 30 * (1 - q), 0.5 * q)
            blit(f, ins, 1380, 120 + 30 * (1 - q), q)
        f *= SCRIM ** 0.6
        draw_caption(f, i, t)
        return f, False
    # photo / film / data
    if bg:
        f = kenburns(bg, u, i)
        f = grade(f, err, mono=ease_io((u - 0.2) / 0.6) if fx == "mono" else 0.0)
        if kind == "data":
            f = f * 0.38 + NAVY * 0.35
        f *= SCRIM
    else:
        f = NAVY.copy()
    if fx and fx not in ("mono",):
        fx_draw(f, fx, u, t, dur)
    draw_tag(f, i, t)
    draw_caption(f, i, t)
    return f, False


XF = 0.18


def frame_at(t):
    i = max(k for k in range(len(SHOTS)) if T0[k] <= t + 1e-6)
    i = min(i, len(SHOTS) - 1)
    lt = t - T0[i]
    f, paper = render_shot(i, lt)
    if i > 0 and lt < XF and i not in HITS:
        g, _ = render_shot(i - 1, T1[i - 1] - T0[i - 1] + lt)
        k = ease_io(lt / XF)
        f = g * (1 - k) + f * k
    if i in HITS and lt < 0.4:
        f = f + (1 - ease(lt / 0.4)) * 0.75
    kind = SHOTS[i]["kind"]
    # 统一质感：暗角 + 颗粒
    f = f * (VIGNETTE if not paper else VIGNETTE ** 0.5)
    gr = cv2.resize(GRAIN[int(t * FPS) % 6], (W, H), interpolation=cv2.INTER_LINEAR)
    f += gr[..., None] * 0.022
    if kind not in ("end",):
        HUD.draw(f, t, alpha=1.0 if kind != "title" else ease((t - 1.0) / 0.8))
    if kind not in ("title", "end"):
        blit(f, DISCLAIM, 40, H - 54, 0.75)
    return np.clip(f, 0, 1)


def to8(f):
    return (f * 255 + 0.5).astype(np.uint8)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "still":
        i, s = int(sys.argv[2]) - 1, float(sys.argv[3])
        Image.fromarray(to8(frame_at(T0[i] + s))).save(sys.argv[4])
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
