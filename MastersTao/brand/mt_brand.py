"""MastersTao · 大师持仓洞察 —— 系列视觉体系（Python / numpy 合成）。

用法：
    import sys; sys.path.insert(0, 'MastersTao/brand')
    from mt_brand import Hud, PALETTE, load_logo
    hud = Hud(width=1080)          # 竖屏 1080×1920
    hud.draw(frame, t)             # frame: float32 RGB 0..1（线性叠加前的显示空间），t: 秒

所有 logo 像素取自 logo-kit/（官方 MastersTao v4 素材，蓝紫复利主色），不重新绘制。
规范见 BRAND.md。
"""
import math, os
from functools import lru_cache
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(HERE, "logo-kit")


def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


# ---------------------------------------------------------------- 系列色板
PALETTE = {
    "bg0": _hex("#05060C"),        # 最深底色（近黑偏蓝）
    "bg1": _hex("#0B0E1C"),        # 面板 / 卡片
    "ink": _hex("#F5F5F7"),        # 主文字（与字标一致）
    "ink2": _hex("#A9AEC4"),       # 次文字
    "ink3": _hex("#5E6480"),       # 注释 / 网格
    "brand_a": _hex("#279DFF"),    # 品牌渐变起点（蓝）
    "brand_b": _hex("#9560F3"),    # 品牌渐变终点（紫）
    # 数据系列（每期固定语义：A 系列暖金，B 系列冰蓝，合并为品牌紫）
    "series_a": _hex("#FFC529"),   # 暖金（取自官方 gold 配色）
    "series_b": _hex("#3FC8FF"),   # 冰蓝
    "series_ab": _hex("#B48CFF"),  # 合并 / 交集
    "up": _hex("#FF5A6A"),         # A 股习惯：红涨
    "down": _hex("#2FD39A"),       # 绿跌
    "warn": _hex("#FFB547"),       # 数据不完整 / 注意
}

# 三类说明标签（区分事实、相关性与推测），每期统一使用
TAGS = {
    "fact": ("事实", _hex("#F5F5F7")),
    "context": ("背景", _hex("#3FC8FF")),
    "guess": ("推测", _hex("#FFB547")),
}


@lru_cache(8)
def load_logo(variant="blue", kind="logo-dark", height=None):
    """返回 (rgb, alpha)，已裁掉透明边；rgb 为直通色（非预乘），float32 0..1。"""
    im = Image.open(os.path.join(KIT, variant, kind + ".png")).convert("RGBA")
    im = im.crop(im.getchannel("A").getbbox())
    if height:
        w = max(1, round(im.width * height / im.height))
        im = im.resize((w, height), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255.0
    return a[..., :3].copy(), a[..., 3].copy()


def _box_blur(img, r):
    if r < 1:
        return img
    k = 2 * r + 1
    pad = [(r, r), (r, r)] + [(0, 0)] * (img.ndim - 2)
    p = np.pad(img, pad, mode="constant")
    c = p.cumsum(0)
    c = np.concatenate([np.zeros_like(c[:1]), c], 0)
    p = (c[k:] - c[:-k]) / k
    c = p.cumsum(1)
    c = np.concatenate([np.zeros_like(c[:, :1]), c], 1)
    return (c[:, k:] - c[:, :-k]) / k


def _blur(img, sigma):
    r = max(1, int(sigma * 0.9))
    for _ in range(3):
        img = _box_blur(img, r)
    return img


class Hud:
    """右上角品牌角标：官方 logo（mark + 大师之道 + MastersTao）+ 系列名。

    - 以 1080 宽竖屏为基准：logo 高 64px，距右 44px、距上 64px（避开平台状态栏）。
    - logo 下方居右一行小字「大师持仓洞察」，品牌蓝紫渐变细线分隔。
    - logo 后有一层很淡的蓝紫光晕；底下垫淡暗阴影，亮画面上也能看清。
    - 流光：每 8 秒一次、持续 1.2 秒，只扫过 mark 图形。
    """

    def __init__(self, width=1080, series="大师持仓洞察", font_path=None):
        s = width / 1080.0
        self.s = s
        self.h = int(round(64 * s))
        self.rgb, self.a = load_logo("blue", "logo-dark", self.h)
        self.lw = self.rgb.shape[1]
        self.mx, self.my = int(44 * s), int(64 * s)
        # 系列名小字
        self.tag = None
        if series:
            from PIL import ImageDraw, ImageFont
            fp = font_path or os.path.join(HERE, "..", "fonts", "sans_med.ttf")
            f = ImageFont.truetype(fp, int(20 * s))
            tw = int(f.getlength(series) + len(series) * 6 * s)
            im = Image.new("L", (tw + 4, int(30 * s)), 0)
            d = ImageDraw.Draw(im)
            x = 0
            for ch in series:
                d.text((x, 0), ch, font=f, fill=255)
                x += f.getlength(ch) + 6 * s
            self.tag = np.asarray(im, np.float32) / 255.0
        # 光晕与阴影（预计算）
        pad = int(30 * s)
        A = np.pad(self.a, pad)
        self.pad = pad
        self.halo = _blur(A, 12 * s)
        self.shadow = _blur(A, 8 * s)
        # mark 区域（logo 左侧图形，约占高度 1.05 倍宽）
        self.mark_w = int(self.h * 1.08)

    def draw(self, frame, t, alpha=1.0):
        if alpha <= 0:
            return frame
        H, W = frame.shape[:2]
        x0 = W - self.mx - self.lw
        y0 = self.my
        p = self.pad
        # 阴影 + 光晕
        hh, ww = self.halo.shape
        X0, Y0 = x0 - p, y0 - p
        sl = (slice(max(Y0, 0), min(Y0 + hh, H)), slice(max(X0, 0), min(X0 + ww, W)))
        hs = (slice(sl[0].start - Y0, sl[0].stop - Y0), slice(sl[1].start - X0, sl[1].stop - X0))
        frame[sl] *= (1 - 0.35 * alpha * np.clip(self.shadow[hs] * 1.6, 0, 1))[..., None]
        glow = np.array([0.40, 0.48, 1.0], np.float32) * 0.16 * alpha
        frame[sl] += self.halo[hs][..., None] * glow
        # logo 本体（alpha over）
        rgb = self.rgb.copy()
        # 流光：扫过 mark
        ph = (t % 8.0) / 1.2
        if ph < 1.0:
            xs = np.arange(self.lw, dtype=np.float32)[None, :]
            ys = np.arange(self.h, dtype=np.float32)[:, None]
            cx = -0.3 * self.mark_w + ph * 1.6 * self.mark_w
            band = np.exp(-((xs + ys * 0.45 - cx) / (0.12 * self.mark_w)) ** 2)
            band[:, self.mark_w:] = 0
            rgb = np.clip(rgb + band[..., None] * 0.55 * math.sin(math.pi * ph), 0, 1)
        a = self.a[..., None] * alpha
        reg = frame[y0:y0 + self.h, x0:x0 + self.lw]
        reg[:] = reg * (1 - a) + rgb * a
        # 系列名
        if self.tag is not None:
            th, tw = self.tag.shape
            ty = y0 + self.h + int(14 * self.s)
            tx = W - self.mx - tw
            # 渐变细线
            ly = ty - int(6 * self.s)
            lx0 = tx
            n = W - self.mx - lx0
            u = np.linspace(0, 1, n, dtype=np.float32)[:, None]
            col = (1 - u) * np.array(PALETTE["brand_a"]) + u * np.array(PALETTE["brand_b"])
            frame[ly, lx0:lx0 + n] = frame[ly, lx0:lx0 + n] * (1 - 0.7 * alpha) + col * 0.7 * alpha
            m = self.tag[..., None] * alpha * 0.82
            reg = frame[ty:ty + th, tx:tx + tw]
            reg[:] = reg * (1 - m) + np.array(PALETTE["ink2"], np.float32) * m
        return frame
