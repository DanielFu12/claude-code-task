"""巴芒价值 · 品牌角标（右上角 logo + 金色「巴芒价值」）

所有视频 / 图片任务统一使用本模块，规范见 brand/BRAND.md。

运行时只依赖 numpy + opencv + Pillow，不需要字体：文字已预渲染进 hud_lockup@4x.png。
只有改设计时才需要 `python3 brand/brand.py build`（会从 Google Fonts 下载思源宋体）。

用法（帧为 float32 RGB，0..1，H×W×3）::

    from brand import Hud
    hud = Hud()                       # 默认 logo 显示高 60px（1080p）
    hud.draw(frame, t)                # t = 当前秒数；原地合成，含光晕、阴影、流光

    # 也可以直接拿静态 PNG 给 ffmpeg overlay： brand/hud_lockup.png（1x，无流光）
"""
import json, math, os, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO_PNG = os.path.join(HERE, 'logo_baman.png')          # 透明底、去白边的 logo 原图（1024²）
LOCKUP_4X = os.path.join(HERE, 'hud_lockup@4x.png')       # logo + 文字 组合（4 倍分辨率）
LAYOUT = os.path.join(HERE, 'hud_layout.json')

# ---------------------------------------------------------------- 设计参数（改这里再 build）
SPEC = dict(
    logo_px=60,              # logo 显示高度（1080p 画面）
    gap_px=14,               # logo 与文字间距
    title='巴芒价值', title_px=38, title_font='serif_black',
    sub='BUFFETT · MUNGER', sub_px=12.5, sub_font='corm', sub_gap_px=7,   # 小字自动两端对齐到主标题宽度
    margin_right=52, margin_top=30,
    glow_rgb=(110, 175, 255), glow_sigma=11, glow_strength=0.20,   # logo 后的淡蓝光晕
    shadow_sigma=6, shadow_strength=0.7,
    shimmer_period=7.5, shimmer_dur=1.4, shimmer_first=2.0,         # 流光：每 7.5s 一次，每次 1.4s
)
GOLD_STOPS = [(0.0, (255, 243, 200)), (0.35, (255, 212, 120)), (0.62, (226, 160, 60)), (1.0, (255, 214, 130))]
SUB_GOLD = (214, 178, 112)


def _ramp(h, stops):
    y = np.linspace(0, 1, h)
    return np.stack([np.interp(y, [s[0] for s in stops], [s[1][c] for s in stops]) for c in range(3)], 1) / 255.0


def _resize_rgba(rgb, a, w, h):
    """预乘 alpha 缩放，避免边缘渗色/白边"""
    pm = cv2.resize(rgb * a[..., None], (w, h), interpolation=cv2.INTER_AREA)
    aa = cv2.resize(a, (w, h), interpolation=cv2.INTER_AREA)
    return np.where(aa[..., None] > 1e-4, pm / np.maximum(aa[..., None], 1e-4), 0), aa


def load_logo(px):
    im = np.asarray(Image.open(LOGO_PNG).convert('RGBA')).astype(np.float32) / 255
    return _resize_rgba(im[..., :3], im[..., 3], px, px)


# ---------------------------------------------------------------- build（仅改设计时运行）
FONT_URLS = {'serif_black': ('Noto+Serif+SC', 900), 'corm': ('Cormorant+Garamond', 600)}

def _font(name, size):
    d = os.path.join(HERE, 'fonts'); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name + '.ttf')
    if not os.path.exists(p):
        import re, urllib.request
        fam, w = FONT_URLS[name]
        css = urllib.request.urlopen(urllib.request.Request(
            f'https://fonts.googleapis.com/css2?family={fam}:wght@{w}', headers={'User-Agent': 'curl'})).read().decode()
        urllib.request.urlretrieve(re.search(r'https://[^)]+\.ttf', css).group(0), p)
    return ImageFont.truetype(p, size)


def _ink(img):
    a = np.asarray(img, np.float32) / 255
    ys, xs = np.where(a > 0.01)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def build(k=4):
    S = SPEC
    lp = int(S['logo_px'] * k)
    lrgb, la = load_logo(lp)
    f1 = _font(S['title_font'], int(S['title_px'] * k))
    im = Image.new('L', (int(f1.getlength(S['title']) + 40 * k), int(S['title_px'] * k * 1.6)), 0)
    ImageDraw.Draw(im).text((10 * k, int(S['title_px'] * k * 1.25)), S['title'], font=f1, fill=255, anchor='ls')
    t1 = _ink(im)
    f2 = _font(S['sub_font'], int(S['sub_px'] * k))
    nat = sum(f2.getlength(c) for c in S['sub'])
    # 小字两端对齐到主标题宽度（与「巴芒价值」等宽）
    tr = (t1.shape[1] - nat) / (len(S['sub']) - 1)
    w2 = int(sum(f2.getlength(c) for c in S['sub']) + tr * len(S['sub']) + 20 * k)
    im = Image.new('L', (w2, int(S['sub_px'] * k * 2)), 0)
    d = ImageDraw.Draw(im); x = 5 * k
    for c in S['sub']:
        d.text((x, int(S['sub_px'] * k * 1.4)), c, font=f2, fill=255, anchor='ls'); x += f2.getlength(c) + tr
    t2 = _ink(im)[:, :t1.shape[1]]
    gap2 = int(S['sub_gap_px'] * k)
    th = t1.shape[0] + gap2 + t2.shape[0]
    tw = max(t1.shape[1], t2.shape[1])
    pad = int(4 * k)
    H = max(lp, th) + 2 * pad
    gx = int(S['gap_px'] * k)
    Wd = pad + lp + gx + tw + pad
    A = np.zeros((H, Wd), np.float32); RGB = np.zeros((H, Wd, 3), np.float32)
    oy = (H - lp) // 2
    A[oy:oy + lp, pad:pad + lp] = la; RGB[oy:oy + lp, pad:pad + lp] = lrgb
    x0 = pad + lp + gx
    ty = (H - th) // 2
    A[ty:ty + t1.shape[0], x0:x0 + t1.shape[1]] = t1
    RGB[ty:ty + t1.shape[0], x0:x0 + t1.shape[1]] = _ramp(t1.shape[0], GOLD_STOPS)[:, None, :]
    sx = x0 + (t1.shape[1] - t2.shape[1]) // 2          # 小字与主标题居中对齐
    sy = ty + t1.shape[0] + gap2
    A[sy:sy + t2.shape[0], sx:sx + t2.shape[1]] = t2
    RGB[sy:sy + t2.shape[0], sx:sx + t2.shape[1]] = np.array(SUB_GOLD) / 255
    out = np.dstack([RGB, A])
    Image.fromarray((out * 255 + 0.5).clip(0, 255).astype(np.uint8), 'RGBA').save(LOCKUP_4X)
    lay = dict(k=k, logo_box=[pad, oy, pad + lp, oy + lp], text_box=[x0, ty, x0 + tw, ty + th], size=[Wd, H])
    json.dump(lay, open(LAYOUT, 'w'), indent=1)
    # 1x 静态版（给 ffmpeg overlay 等场景直接用）
    rgb1, a1 = _resize_rgba(RGB, A, Wd // k, H // k)
    Image.fromarray((np.dstack([rgb1, a1]) * 255 + 0.5).clip(0, 255).astype(np.uint8), 'RGBA').save(
        os.path.join(HERE, 'hud_lockup.png'))
    print('built', LOCKUP_4X, lay)


# ---------------------------------------------------------------- runtime
class Hud:
    def __init__(self, scale=1.0, frame_w=1920):
        """scale=1 对应 1080p；4K 画面用 scale=2。"""
        S = SPEC
        lay = json.load(open(LAYOUT))
        k = lay['k']
        im = np.asarray(Image.open(LOCKUP_4X).convert('RGBA')).astype(np.float32) / 255
        w, h = int(round(lay['size'][0] / k * scale)), int(round(lay['size'][1] / k * scale))
        self.rgb, self.a = _resize_rgba(im[..., :3], im[..., 3], w, h)
        f = w / lay['size'][0]
        lb = [int(round(v * f)) for v in lay['logo_box']]; tb = [int(round(v * f)) for v in lay['text_box']]
        self.w, self.h, self.lb, self.tb = w, h, lb, tb
        self.frame_w = frame_w
        self.x0 = int(frame_w - w - S['margin_right'] * scale)
        self.y0 = int(S['margin_top'] * scale)
        # 光晕：只来自 logo；阴影：整个角标
        la = np.zeros_like(self.a); la[lb[1]:lb[3], lb[0]:lb[2]] = self.a[lb[1]:lb[3], lb[0]:lb[2]]
        P = int(S['glow_sigma'] * 3 * scale)
        self.P = P
        big = np.pad(la, P)
        self.glow = cv2.GaussianBlur(big, (0, 0), S['glow_sigma'] * scale)[..., None] * \
            (np.array(S['glow_rgb'], np.float32) / 255) * S['glow_strength']
        self.shadow = cv2.GaussianBlur(np.pad(self.a, P), (0, 0), S['shadow_sigma'] * scale) * S['shadow_strength']
        self.textmask = np.zeros_like(self.a); self.textmask[tb[1]:tb[3], tb[0]:tb[2]] = 1
        self.scale = scale

    def shimmer(self, t):
        """返回流光带位置 0..1（不在扫光时返回 None）"""
        S = SPEC
        if t < S['shimmer_first']: return None
        ph = (t - S['shimmer_first']) % S['shimmer_period']
        return ph / S['shimmer_dur'] if ph < S['shimmer_dur'] else None

    def rgb_at(self, t):
        u = self.shimmer(t)
        if u is None: return self.rgb
        tb = self.tb
        xs = np.arange(self.w)[None, :] + np.arange(self.h)[:, None] * 0.6
        span = (tb[2] - tb[0]) + 80 * self.scale
        pos = tb[0] - 40 * self.scale + (0.5 - 0.5 * math.cos(u * math.pi)) * span
        band = np.exp(-((xs - pos) / (16 * self.scale)) ** 2)[..., None] * self.textmask[..., None]
        return np.clip(self.rgb + band * 0.6, 0, 1.25)

    def draw(self, frame, t, alpha=1.0):
        """frame: float32 H×W×3 (0..1)，原地合成。"""
        if alpha <= 0.003: return frame
        P, x0, y0 = self.P, self.x0, self.y0
        H, W = frame.shape[:2]
        # 阴影（加深）+ 光晕（加色）
        X0, Y0 = x0 - P, y0 - P
        sh, gl = self.shadow, self.glow
        ys, xs = slice(max(Y0, 0), min(Y0 + sh.shape[0], H)), slice(max(X0, 0), min(X0 + sh.shape[1], W))
        cy, cx = slice(ys.start - Y0, ys.stop - Y0), slice(xs.start - X0, xs.stop - X0)
        frame[ys, xs] *= (1 - sh[cy, cx] * alpha)[..., None]
        frame[ys, xs] += gl[cy, cx] * alpha
        a = (self.a * alpha)[..., None]
        reg = frame[y0:y0 + self.h, x0:x0 + self.w]
        reg *= (1 - a)
        reg += a * self.rgb_at(t)
        return frame


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'build':
        build()
    elif len(sys.argv) > 1 and sys.argv[1] == 'preview':
        # 生成深色背景预览图：python3 brand/brand.py preview out.png
        hud = Hud()
        fr = np.zeros((220, 1920, 3), np.float32); fr[:] = (0.02, 0.025, 0.06)
        a = hud.draw(fr.copy(), 0.5); b = hud.draw(fr.copy(), SPEC['shimmer_first'] + 0.7)
        img = np.vstack([a, b])[:, 1920 - 760:]
        Image.fromarray((img.clip(0, 1) * 255).astype(np.uint8)).resize((760 * 2, 440 * 2), Image.NEAREST).save(sys.argv[2])
