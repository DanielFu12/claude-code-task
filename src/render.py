# -*- coding: utf-8 -*-
"""根据 content.py 的画面编排和 build/timeline.json 的时间轴，逐帧渲染视频并与音频合成。

用法：python3 render.py [--preview 秒数,秒数,...] [--workers N]
"""
import argparse
import functools
import io
import json
import math
import os
import subprocess
import sys
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from content import COL, SCENES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
ASSETS = os.path.join(ROOT, "assets")
W, H, FPS = 1920, 1080, 30

FONT_FILES = {
    "r": "fonts/SourceHanSansSC-Regular.otf",
    "m": "fonts/SourceHanSansSC-Medium.otf",
    "b": "fonts/SourceHanSansSC-Bold.otf",
    "h": "fonts/SourceHanSansSC-Heavy.otf",
    "serif": "fonts/SourceHanSerifCN-Heavy.otf",
}
DEFAULT_ANIM = {"text": "up", "chip": "pop", "card": "pop", "frame": "pop", "ring": "pop",
                "bar": "wipe", "pie": "pop", "circle": "pop", "bells": "fade"}


@functools.lru_cache(None)
def font(name, size):
    return ImageFont.truetype(os.path.join(ASSETS, FONT_FILES[name]), size)


def color(c, alpha=255):
    if isinstance(c, str):
        c = COL[c]
    return tuple(c) if len(c) == 4 else tuple(c) + (alpha,)


# ---------------------------------------------------------------- 资源
def twemoji_name(ch):
    cps = [f"{ord(c):x}" for c in ch]
    yield "-".join(cps)
    yield "-".join(c for c in cps if c != "fe0f")


@functools.lru_cache(None)
def emoji(ch, size):
    import cairosvg
    d = os.path.join(ASSETS, "emoji")
    os.makedirs(d, exist_ok=True)
    svg = None
    for name in twemoji_name(ch):
        p = os.path.join(d, name + ".svg")
        if not os.path.exists(p):
            try:
                url = f"https://raw.githubusercontent.com/jdecked/twemoji/main/assets/svg/{name}.svg"
                data = urllib.request.urlopen(url, timeout=30).read()
                open(p, "wb").write(data)
            except Exception:
                continue
        svg = p
        break
    if svg is None:
        raise RuntimeError(f"emoji not found: {ch!r}")
    png = cairosvg.svg2png(url=svg, output_width=size, output_height=size)
    return Image.open(io.BytesIO(png)).convert("RGBA")


# ---------------------------------------------------------------- 文本
def wrap(text, f, maxw):
    out = []
    for para in text.split("\n"):
        line = ""
        for ch in para:
            if maxw and f.getlength(line + ch) > maxw and line:
                out.append(line)
                line = ch
            else:
                line += ch
        out.append(line)
    return out


def text_layer(s, size, fname, col, maxw=None, align="center", spacing=1.3, shadow=True):
    f = font(fname, size)
    lines = wrap(s, f, maxw)
    asc, desc = f.getmetrics()
    lh = int(size * spacing)
    widths = [f.getlength(l) for l in lines]
    w = int(max(widths)) + 24
    h = lh * (len(lines) - 1) + asc + desc + 24
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    for i, (l, lw) in enumerate(zip(lines, widths)):
        x = 12 if align == "left" else 12 + (w - 24 - lw) / 2
        d.text((x, 12 + i * lh), l, font=f, fill=color(col))
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh.putalpha(img.getchannel("A").point(lambda v: v * 0.55).filter(ImageFilter.GaussianBlur(6)))
        base = Image.new("RGBA", img.size)
        base.alpha_composite(sh, (0, 3))
        base.alpha_composite(img)
        img = base
    return img


# ---------------------------------------------------------------- 元素图层
def place(img, x, y, al="c"):
    w, h = img.size
    if al == "l":
        return img, int(x - 12), int(y - h / 2)
    if al == "r":
        return img, int(x - w + 12), int(y - h / 2)
    return img, int(x - w / 2), int(y - h / 2)


def build_layer(el):
    t = el["t"]
    if t == "text":
        img = text_layer(el["s"], el["size"], el["font"], el["color"], el.get("maxw", 1700),
                         el.get("align", "center"), el.get("spacing", 1.3))
        return place(img, el["x"], el["y"], el.get("al", "c"))
    if t == "emoji":
        return place(emoji(el["ch"], el["size"]), el["x"], el["y"])
    if t == "rect":
        w, h, r = el["w"], el["h"], el["r"]
        img = Image.new("RGBA", (w + 8, h + 8))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((4, 4, w + 3, h + 3), r, fill=color(el["fill"]),
                            outline=color(el["outline"]) if el.get("outline") else None, width=3)
        return place(img, el["x"], el["y"])
    if t == "chip":
        f = font("b", el["size"])
        tw = f.getlength(el["s"])
        asc, desc = f.getmetrics()
        w, h = int(tw + el["size"] * 1.2), int(el["size"] * 1.7)
        img = Image.new("RGBA", (w, h))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=color(el["fill"]))
        d.text((w / 2, h / 2), el["s"], font=f, fill=color(el["color"]), anchor="mm")
        return place(img, el["x"], el["y"])
    if t == "line":
        x1, y1, x2, y2, lw = el["x1"], el["y1"], el["x2"], el["y2"], el["w"]
        pad = 30
        ox, oy = min(x1, x2) - pad, min(y1, y2) - pad
        img = Image.new("RGBA", (abs(x2 - x1) + 2 * pad, abs(y2 - y1) + 2 * pad))
        d = ImageDraw.Draw(img)
        a, b = (x1 - ox, y1 - oy), (x2 - ox, y2 - oy)
        c = color(el["color"])
        if el.get("head"):
            ang = math.atan2(b[1] - a[1], b[0] - a[0])
            hl = lw * 3.2
            tip = b
            base = (b[0] - hl * math.cos(ang), b[1] - hl * math.sin(ang))
            d.line((a, base), fill=c, width=lw)
            left = (base[0] + hl * 0.6 * math.sin(ang), base[1] - hl * 0.6 * math.cos(ang))
            right = (base[0] - hl * 0.6 * math.sin(ang), base[1] + hl * 0.6 * math.cos(ang))
            d.polygon([tip, left, right], fill=c)
        else:
            d.line((a, b), fill=c, width=lw)
            for p in (a, b):
                d.ellipse((p[0] - lw / 2, p[1] - lw / 2, p[0] + lw / 2, p[1] + lw / 2), fill=c)
        return img, ox, oy
    if t == "bar":
        bw = int(el["w"] * (el["f1"] - el["f0"]))
        img = Image.new("RGBA", (bw, el["h"]))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((0, 0, bw - 1, el["h"] - 1), min(12, bw // 2), fill=color(el["color"]))
        if el.get("label"):
            d.text((bw / 2, el["h"] / 2), el["label"], font=font("b", 32), fill=color("dark"), anchor="mm")
        return img, int(el["x"] + el["w"] * el["f0"]), int(el["y"] - el["h"] / 2)
    if t == "card":
        w, h = el["w"], el["h"]
        img = Image.new("RGBA", (w + 30, h + 30))
        sh = Image.new("RGBA", img.size)
        ImageDraw.Draw(sh).rounded_rectangle((15, 21, w + 15, h + 21), 24, fill=(0, 0, 0, 120))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((15, 15, w + 15, h + 15), 24, fill=color("ink"))
        if el.get("emoji"):
            em = emoji(el["emoji"], 120)
            img.alpha_composite(em, (15 + (w - 120) // 2, 15 + 50))
            d.text((15 + w / 2, 15 + h - 62), el["s"], font=font("h", 44), fill=color("dark"), anchor="mm")
        else:
            size = 150 if len(el["s"]) == 1 else 70
            d.text((15 + w / 2, 15 + h / 2), el["s"], font=font("h", size), fill=color("dark"), anchor="mm")
        return place(img, el["x"], el["y"])
    if t == "frame":
        w, h = el["w"], el["h"]
        img = Image.new("RGBA", (w + 10, h + 10))
        ImageDraw.Draw(img).rounded_rectangle((5, 5, w + 4, h + 4), 30, outline=color(el["color"]), width=8)
        return place(img, el["x"], el["y"])
    if t == "ring":
        r = el["r"]
        img = Image.new("RGBA", (2 * r + 12, 2 * r + 12))
        ImageDraw.Draw(img).ellipse((6, 6, 2 * r + 6, 2 * r + 6), outline=color(el["color"]), width=8)
        return place(img, el["x"], el["y"])
    if t == "circle":
        r = el["r"]
        img = Image.new("RGBA", (2 * r + 12, 2 * r + 12))
        ImageDraw.Draw(img).ellipse((6, 6, 2 * r + 6, 2 * r + 6), fill=color(el["color"], 70),
                                    outline=color(el["color"]), width=4)
        return place(img, el["x"], el["y"])
    if t == "pie":
        r = el["r"]
        img = Image.new("RGBA", (2 * r + 12, 2 * r + 12))
        d = ImageDraw.Draw(img)
        d.ellipse((6, 6, 2 * r + 6, 2 * r + 6), fill=(255, 255, 255, 30))
        d.pieslice((6, 6, 2 * r + 6, 2 * r + 6), -90, -90 + 360 * el["frac"], fill=color(el["color"]))
        return place(img, el["x"], el["y"])
    if t == "bells":
        w, h, sh = el["w"], el["h"], el["shift"]
        img = Image.new("RGBA", (w + 20, h + 60))
        d = ImageDraw.Draw(img)
        xs = np.linspace(-1, 1, 400)
        for mu, c in ((-sh / 2, "teal"), (sh / 2, "coral")):
            ys = np.exp(-((xs - mu) ** 2) / (2 * 0.22 ** 2))
            pts = [(10 + (x + 1) / 2 * w, 10 + h - y * (h - 20)) for x, y in zip(xs, ys)]
            d.polygon(pts + [(10 + w, 10 + h), (10, 10 + h)], fill=color(c, 70))
            d.line(pts, fill=color(c), width=5)
        d.line((10, 10 + h, 10 + w, 10 + h), fill=color("muted"), width=3)
        for mu, c, lab, anc, off in ((-sh / 2, "teal", "群体 A 平均", "rm", -10), (sh / 2, "coral", "群体 B 平均", "lm", 10)):
            px = 10 + (mu + 1) / 2 * w
            for yy in range(20, h, 18):
                d.line((px, 10 + yy, px, 10 + yy + 9), fill=color(c), width=3)
            d.text((px + off, 10 + h + 28), lab, font=font("m", 30), fill=color(c), anchor=anc)
        return place(img, el["x"], el["y"])
    raise ValueError(t)


# ---------------------------------------------------------------- 动画
def ease_out(p):
    return 1 - (1 - p) ** 3


def ease_back(p, s=1.7):
    p -= 1
    return 1 + (s + 1) * p ** 3 + s * p ** 2


def when(sc, at, f=0.0, d=0.0):
    if not sc["ls"]:
        return d
    if at >= len(sc["ls"]):
        return sc["dur"]
    return sc["ls"][at] + f * sc["ld"][at] + d


def anim_state(el, sc, t):
    """返回 (alpha, dx, dy, scale, wipe, settled) 或 None（尚未出现/已消失）。"""
    t0 = when(sc, el["at"], el.get("f", 0), el.get("d", 0))
    if t < t0:
        return None
    dur = el.get("dur", 0.5)
    p = min(1.0, (t - t0) / dur)
    anim = el.get("anim") or DEFAULT_ANIM.get(el["t"], "fade")
    a, dx, dy, s, wipe = 1.0, 0, 0, 1.0, 1.0
    e = ease_out(p)
    if anim == "up":
        a, dy = e, (1 - e) * 34
    elif anim == "left":
        a, dx = e, -(1 - e) * 50
    elif anim == "fade":
        a = e
    elif anim == "pop":
        s, a = max(0.01, ease_back(p)), min(1.0, p * 2.5)
    elif anim == "wipe":
        wipe, a = max(0.002, e), min(1.0, p * 5)
    settled = p >= 1
    for key, floor in (("out", 0.0), ("dim", 0.28)):
        if key in el:
            t1 = when(sc, el[key], el.get(key[0] + "f", 0))
            if t >= t1:
                q = min(1.0, (t - t1) / 0.4)
                a *= 1 - (1 - floor) * ease_out(q)
                settled = settled and q >= 1
    end = min(1.0, max(0.0, (sc["dur"] - t) / 0.35))
    a *= end
    settled = settled and end >= 1
    if a <= 0.003:
        return None
    return a, dx, dy, s, wipe, settled


def paste(canvas, img, x0, y0, a=1.0, s=1.0, wipe=1.0):
    if wipe < 1:
        img = img.crop((0, 0, max(1, int(img.width * wipe)), img.height))
    if abs(s - 1) > 1e-3:
        w, h = img.size
        cx, cy = x0 + w / 2, y0 + h / 2
        nw, nh = max(1, int(w * s)), max(1, int(h * s))
        img = img.resize((nw, nh), Image.BILINEAR)
        x0, y0 = int(cx - nw / 2), int(cy - nh / 2)
    if a < 0.999:
        img = img.copy()
        img.putalpha(img.getchannel("A").point([int(i * a) for i in range(256)]))
    x0, y0 = int(x0), int(y0)
    l, t = max(0, -x0), max(0, -y0)
    r, b = min(img.width, W - x0), min(img.height, H - y0)
    if r <= l or b <= t:
        return
    if (l, t, r, b) != (0, 0, img.width, img.height):
        img = img.crop((l, t, r, b))
    canvas.alpha_composite(img, (x0 + l, y0 + t))


# ---------------------------------------------------------------- 背景与常驻界面
def make_background():
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    top, bot = np.array([13, 19, 33]), np.array([27, 40, 62])
    g = top[None, None, :] * (1 - y[..., None]) + bot[None, None, :] * y[..., None]
    r = np.sqrt((x - 0.5) ** 2 * 1.2 + (y - 0.45) ** 2)
    glow = np.clip(1 - r * 1.6, 0, 1)[..., None] * np.array([18, 22, 30])
    vign = np.clip(1 - (r - 0.45) * 0.9, 0.55, 1)[..., None]
    img = np.clip((g + glow) * vign, 0, 255)
    noise = np.random.default_rng(1).normal(0, 1.6, img.shape[:2])[..., None]
    return Image.fromarray(np.clip(img + noise, 0, 255).astype(np.uint8), "RGB")


RNG = np.random.default_rng(7)
PARTICLES = [(RNG.uniform(0, W), RNG.uniform(0, H), RNG.uniform(2, 6), RNG.uniform(-6, 6), RNG.uniform(-14, -4),
              RNG.uniform(0, 6.28)) for _ in range(46)]


def draw_particles(img, t):
    d = ImageDraw.Draw(img, "RGBA")
    for x0, y0, r, vx, vy, ph in PARTICLES:
        x = (x0 + vx * t) % W
        y = (y0 + vy * t) % H
        a = int(14 + 12 * math.sin(t * 0.5 + ph))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(200, 220, 255, a))


def overlay(frame, lay, x, y, a):
    """把 RGBA 图层按透明度 a 叠加到 RGB 画面上。"""
    if a <= 0:
        return
    if a < 0.999:
        lay = lay.copy()
        lay.putalpha(lay.getchannel("A").point([int(i * a) for i in range(256)]))
    frame.paste(lay, (int(x), int(y)), lay)


@functools.lru_cache(64)
def subtitle_layer(s):
    f = font("m", 44)
    lines = wrap(s, f, 1560)
    lh = 60
    w = int(max(f.getlength(l) for l in lines)) + 64
    h = lh * len(lines) + 26
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 18, fill=(6, 9, 16, 165))
    for i, l in enumerate(lines):
        d.text((w / 2, 13 + lh * i + lh / 2), l, font=f, fill=(250, 248, 240, 255), anchor="mm")
    return img


@functools.lru_cache(16)
def chap_layer(s):
    return text_layer(s, 30, "m", (200, 205, 215), shadow=False)


# ---------------------------------------------------------------- 主渲染
class Renderer:
    def __init__(self, timeline):
        self.tl = timeline
        self.bg = make_background()
        self.layers = {}
        self.fg_key, self.fg_img = None, None
        self.starts = [s["start"] for s in timeline["scenes"]]

    def layer(self, si, ei):
        k = (si, ei)
        if k not in self.layers:
            self.layers[k] = build_layer(SCENES[si]["els"][ei])
        return self.layers[k]

    def dyn_layer(self, el, sc, t):
        """计数器、倒计时这类每帧内容会变化的元素。"""
        t0 = when(sc, el["at"], el.get("f", 0), el.get("d", 0))
        if el["t"] == "counter":
            p = ease_out(min(1, max(0, (t - t0) / el.get("dur", 1.5))))
            s = el["fmt"].format(int(round(el["to"] * p)))
            return place(text_layer(s, el["size"], el["font"], el["color"]), el["x"], el["y"]), (t >= t0)
        if el["t"] == "countdown":
            k = int(t - t0)
            if t < t0 or k >= el["n"]:
                return None, False
            frac = (t - t0) - k
            img = text_layer(str(el["n"] - k), el["size"], "serif", el["color"])
            ring = Image.new("RGBA", (el["size"] + 120, el["size"] + 120))
            ImageDraw.Draw(ring).arc((10, 10, ring.width - 10, ring.height - 10), -90, -90 + 360 * (1 - frac),
                                     fill=color(el["color"]), width=10)
            ring.alpha_composite(img, ((ring.width - img.width) // 2, (ring.height - img.height) // 2 - 10))
            return place(ring, el["x"], el["y"]), True
        raise ValueError(el["t"])

    def frame(self, t):
        scenes = self.tl["scenes"]
        si = max(0, np.searchsorted(self.starts, t, side="right") - 1)
        sc = scenes[si]
        lt = t - sc["start"]
        els = SCENES[si]["els"]

        states, all_settled, dyn = [], True, False
        for ei, el in enumerate(els):
            if el["t"] in ("counter", "countdown"):
                dyn = True
                continue
            st = anim_state(el, sc, lt)
            if st is None:
                continue
            states.append((ei, st))
            all_settled = all_settled and st[5]
        key = (si, tuple(ei for ei, _ in states), tuple(round(st[0], 2) for _, st in states))
        if all_settled and not dyn and key == self.fg_key:
            fg = self.fg_img
        else:
            fg = Image.new("RGBA", (W, H))
            for ei, (a, dx, dy, s, wipe, _) in states:
                img, x0, y0 = self.layer(si, ei)
                paste(fg, img, x0 + dx, y0 + dy, a, s, wipe)
            for el in els:
                if el["t"] in ("counter", "countdown"):
                    res, vis = self.dyn_layer(el, sc, lt)
                    if res and vis:
                        st = anim_state(el, sc, lt)
                        if st:
                            img, x0, y0 = res
                            paste(fg, img, x0 + st[1], y0 + st[2], st[0], 1.0 if el["t"] == "counter" else st[3])
            self.fg_key, self.fg_img = key, fg

        frame = self.bg.copy()
        draw_particles(frame, t)
        frame.paste(fg, (0, 0), fg)

        # 右上角章节标签
        chap = SCENES[si].get("chap")
        if chap and SCENES[si].get("kind", "normal") == "normal":
            lay = chap_layer(chap)
            a = min(1.0, lt / 0.4, max(0.0, (sc["dur"] - lt) / 0.35)) * 0.75
            overlay(frame, lay, W - lay.width - 40, 36, a)

        # 字幕
        for st, d, s in zip(sc["ls"], sc["ld"], sc["subs"]):
            if st - 0.05 <= lt <= st + d + 0.2:
                lay = subtitle_layer(s)
                a = min(1.0, (lt - st + 0.05) / 0.12, (st + d + 0.2 - lt) / 0.12)
                overlay(frame, lay, (W - lay.width) // 2, 1000 - lay.height // 2, a)
                break

        # 底部进度条
        d = ImageDraw.Draw(frame, "RGBA")
        d.rectangle((0, H - 6, W, H), fill=(255, 255, 255, 25))
        d.rectangle((0, H - 6, int(W * t / self.tl["total"]), H), fill=color("amber", 200))
        return frame


def render_range(args):
    idx, f0, f1, out = args
    tl = json.load(open(os.path.join(BUILD, "timeline.json")))
    r = Renderer(tl)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "26", "-tune", "animation",
           "-pix_fmt", "yuv420p", "-g", "120", "-threads", "2", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        p.stdin.write(r.frame(fi / FPS).tobytes())
        if idx == 0 and (fi - f0) % 300 == 0:
            print(f"  worker0 {fi - f0}/{f1 - f0}", flush=True)
    p.stdin.close()
    p.wait()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", help="逗号分隔的时间点（秒），输出 PNG 预览")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=os.path.join(ROOT, "output", "进化心理学_你大脑的出厂设置.mp4"))
    a = ap.parse_args()
    tl = json.load(open(os.path.join(BUILD, "timeline.json")))

    # 预先下载/渲染全部 emoji，避免多进程重复下载
    for sc in SCENES:
        for el in sc["els"]:
            if el["t"] == "emoji":
                emoji(el["ch"], el["size"])
            if el["t"] == "card" and el.get("emoji"):
                emoji(el["emoji"], 120)

    if a.preview:
        r = Renderer(tl)
        os.makedirs(os.path.join(BUILD, "preview"), exist_ok=True)
        for s in a.preview.split(","):
            t = float(s)
            path = os.path.join(BUILD, "preview", f"t{t:07.2f}.png")
            r.frame(t).save(path)
            print(path)
        return

    total_frames = int(math.ceil(tl["total"] * FPS))
    n = a.workers
    chunk = math.ceil(total_frames / n)
    jobs = [(i, i * chunk, min(total_frames, (i + 1) * chunk), os.path.join(BUILD, f"part{i}.mp4")) for i in range(n)]
    from multiprocessing import Pool
    with Pool(n) as pool:
        parts = pool.map(render_range, jobs)
    with open(os.path.join(BUILD, "parts.txt"), "w") as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i",
                    os.path.join(BUILD, "parts.txt"), "-i", os.path.join(BUILD, "audio.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-movflags", "+faststart", "-shortest", a.out], check=True)
    print("done:", a.out)


if __name__ == "__main__":
    sys.exit(main())
