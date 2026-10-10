"""《科学思维》逐帧渲染：场景合成、字幕、章节标签、品牌角标与片尾 logo。

    python3 src/video.py preview 3.5 20 ...     # 导出若干时间点的预览帧到 work/preview/
    python3 src/video.py render                 # 4 进程并行渲染 → work/video.mp4
"""
import math
import os
import re
import subprocess
import sys

import cv2
import numpy as np
import skia
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E  # noqa: E402
import timeline as T  # noqa: E402
from engine import W, H, FPS, CX, clip01, ease  # noqa: E402
import scenes_a  # noqa: E402
import scenes_b  # noqa: E402
import scenes_c  # noqa: E402
import outro  # noqa: E402

WORK = T.WORK
SCENES = scenes_a.SCENES + scenes_b.SCENES + scenes_c.SCENES + outro.SCENES

# ---------------------------------------------------------------- 背景色调（随章节情绪变化）
TINT = {
    "hook": (0.0, 0.0, 0.0), "blood": (0.10, 0.015, 0.025), "title": (0.07, 0.05, 0.02),
    "cause": (0.015, 0.045, 0.10), "falsify": (0.035, 0.03, 0.10), "barnum": (0.07, 0.025, 0.09),
    "correct": (0.01, 0.07, 0.07), "invest": (0.075, 0.055, 0.015), "end": (0.03, 0.04, 0.09),
    "outro": (0.02, 0.035, 0.08),
}
CHAPTER = {
    "hook": ("序章", "眼见为实？"), "blood": ("序章", "眼见为实？"),
    "cause": ("01", "相关 ≠ 因果"), "falsify": ("02", "可证伪性"), "barnum": ("03", "伪科学的魔术"),
    "correct": ("04", "纠错的机器"), "invest": ("05", "像科学家一样投资"), "end": ("终章", "不要欺骗自己"),
}


def section_at(t):
    for k, (a, b) in T.SEC.items():
        if a <= t < b:
            return k
    return "outro"


def tint_at(t):
    names = list(T.SEC.keys())
    cur = section_at(t)
    i = names.index(cur)
    base = np.array(TINT[cur])
    if i > 0:
        a = T.SEC[cur][0]
        k = ease((t - a) / 1.6)
        base = np.array(TINT[names[i - 1]]) * (1 - k) + base * k
    return base


# ---------------------------------------------------------------- 字幕：按标点切块，时间按字数分配
PUNCT = "，。：；？！、—"


def _chunks(sub):
    parts = re.findall(r"[^，。：；？！]+[，。：；？！]?", sub.replace("——", "—"))
    out, cur = [], ""
    for p in parts:
        core = len(re.sub(r"[\s" + PUNCT + "「」]", "", cur + p))
        if cur and core > 21:
            out.append(cur)
            cur = p
        else:
            cur += p
    if cur:
        out.append(cur)
    return out


def _weight(s):
    return len(re.sub(r"[\s" + PUNCT + "「」]", "", s)) + 1.6 * len(re.findall(r"[，。：；？！—]", s))


SUBS = []
for lid in T.ORDER:
    t0, t1, sub = T.LINES[lid]
    if not sub:
        continue
    ch = _chunks(sub)
    ws = [_weight(c) for c in ch]
    tot = sum(ws)
    acc = t0
    for c, w in zip(ch, ws):
        d = (t1 - t0) * w / tot
        txt = c.rstrip("，。：；、—")
        SUBS.append((acc, acc + d, txt))
        acc += d


def draw_subtitle(c, t):
    for i, (a, b, s) in enumerate(SUBS):
        nxt = SUBS[i + 1][0] if i + 1 < len(SUBS) else 1e9
        hold = min(b + 0.35, nxt - 0.1)    # 句间短暂停顿时保持字幕；下一句出现前先收起，不重叠
        if a - 0.02 <= t <= hold + 0.08:
            al = ease((t - a + 0.02) / 0.12) * (1 - ease((t - hold) / 0.08))
            if al <= 0:
                continue
            size = 40
            tw = E.measure(s, size, "sans_med", 1.5)
            y = 1006
            E.rrect(c, CX - tw / 2 - 26, y - 34, tw + 52, 66, 14, E.paint((0, 0, 0), 0.38 * al, blur=14))
            # 「」内的词用品牌金色高亮
            x = CX - tw / 2
            hl = False
            f = E.font("sans_med", size)
            for ch in s:
                if ch == "「":
                    hl = True
                if ch == "」":
                    hl = False
                col = E.GOLD if (hl and ch not in "「」") else E.INK
                c.drawString(ch, x, y + size * 0.36, f, E.paint(col, al))
                x += f.measureText(ch) + 1.5


def draw_chapter(c, t):
    sec = section_at(t)
    if sec not in CHAPTER:
        return
    a0, a1 = T.SEC[sec]
    if sec in ("hook", "blood"):
        a0, a1 = T.SEC["hook"][0], T.SEC["blood"][1]
    al = ease((t - a0 - 0.6) / 0.8) * (1 - ease((t - a1 + 0.5) / 0.4))
    if al <= 0:
        return
    num, name = CHAPTER[sec]
    w = E.text(c, num, 64, 62, 22, "inter_med" if num.isdigit() else "serif_bold", E.GOLD, 0.95 * al, "l", 2)
    c.drawLine(64 + w + 16, 62, 64 + w + 16 + 26 * al, 62, E.paint(E.GOLD, 0.7 * al, stroke=1.4))
    E.text(c, name, 64 + w + 54, 62, 22, "serif_med", E.INK, 0.85 * al, "l", 3)


# ---------------------------------------------------------------- 合成


class Ctx:
    def __init__(self, t, canvas):
        self.t = t
        self.c = canvas
        self._parts = None
        self.bloom = 1.0
        self.vign = 1.0
        self.grain = 1.0
        self.bg = 1.0
        self.zoom = 1.0

    def splat(self, P, Wt):
        """场景粒子：与 skia 画布使用同一个镜头缩放。"""
        if self.zoom != 1.0:
            P = (P - [CX, 540]) * self.zoom + [CX, 540]
        E.splat(self.parts, P, Wt)

    @property
    def parts(self):
        if self._parts is None:
            self._parts = np.zeros((H, W, 3), np.float32)
        return self._parts


STAR_N = 900
_r = np.random.default_rng(11)
STAR = np.c_[_r.random(STAR_N) * W, _r.random(STAR_N) * H]
STAR_A = (_r.random(STAR_N) ** 3 * 0.28 + 0.02).astype(np.float32)
STAR_PH = _r.random(STAR_N) * 6.28
STAR_F = 0.3 + _r.random(STAR_N) * 1.4


def hit_env(t, tau):
    v = 0.0
    for h in T.HITS:
        if h <= t:
            v = max(v, math.exp(-(t - h) / tau))
    return v


def render_frame(t):
    arr = np.zeros((H, W, 4), np.uint8)
    arr[..., 3] = 255
    surf = skia.Surface(arr, colorType=skia.kRGBA_8888_ColorType)
    c = surf.getCanvas()
    ctx = Ctx(t, c)
    sec = section_at(t)
    # 镜头：每个章节缓慢推近（序章的棋盘自带镜头）
    a0, a1 = T.SEC[sec]
    zoom = 1.0 if sec in ("hook", "outro") else 1.0 + 0.035 * ease((t - a0) / max(a1 - a0, 1))
    ctx.zoom = zoom
    c.save()
    c.translate(CX, 540)
    c.scale(zoom, zoom)
    c.translate(-CX, -540)
    for (t0, t1, fn) in SCENES:
        if t0 <= t < t1:
            fn(ctx)
    # 重拍：一圈冲击波
    for h in T.HITS:
        if 0 <= t - h < 1.3 and h != T.BRAND_T:
            k = E.ease_out((t - h) / 1.3)
            r = 40 + 1300 * k
            c.drawCircle(CX, 540, r, E.paint(E.GOLD, 0.30 * (1 - k), stroke=3 + 10 * (1 - k), blur=4 + 10 * k))
    c.restore()
    del surf
    img = arr[..., :3].astype(np.float32) * (1 / 255)
    # 背景：底色 + 星云 + 星点（场景可用 ctx.bg 压暗）
    bgk = ctx.bg
    if bgk > 0:
        img += (E.BASE + E.nebula(t, tint_at(t), 1.0)) * bgk
        tw = STAR_A * (0.6 + 0.4 * np.sin(STAR_F * t + STAR_PH)).astype(np.float32)
        drift = np.c_[np.full(STAR_N, -3.0 * t), np.zeros(STAR_N)]
        P = (STAR + drift) % [W, H]
        E.splat(ctx.parts, P, (tw * bgk)[:, None] * np.array([0.8, 0.86, 1.0], np.float32))
    if ctx._parts is not None:
        img += ctx._parts
    img = E.post(img, t, bloom=ctx.bloom, vign=ctx.vign, grain=ctx.grain, ca=hit_env(t, 0.22) * 1.2)
    # 重拍闪白
    fl = hit_env(t, 0.12)
    if fl > 0.01 and sec != "hook":
        img += fl * 0.22
    gfade = clip01(t / 0.6) * clip01((T.DUR - t) / 1.6)
    outro.draw_logo(img, t)                       # 片尾原始 logo 与品牌字（后期之后合成，颜色不被改动）
    img *= gfade
    E.BRAND_HUD.draw(img, t, gfade)               # 右上角官方角标：全程保留，只随整片最终淡出
    out = np.empty((H, W, 4), np.uint8)
    out[..., :3] = (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
    out[..., 3] = 255
    s2 = skia.Surface(out, colorType=skia.kRGBA_8888_ColorType)
    c2 = s2.getCanvas()
    c2.saveLayerAlpha(None, int(255 * gfade))
    draw_chapter(c2, t)
    draw_subtitle(c2, t)
    c2.restore()
    del s2
    return out[..., :3]


E.BRAND_HUD = E.BRAND.Hud()


# ---------------------------------------------------------------- 渲染


def render_chunk(args):
    ci, f0, f1 = args
    cv2.setNumThreads(1)
    path = os.path.join(WORK, f"chunk_{ci}.mp4")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                          "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-threads", "1",
                          path], stdin=subprocess.PIPE)
    for f in range(f0, f1):
        p.stdin.write(np.ascontiguousarray(render_frame(f / FPS)).tobytes())
        if (f - f0) % 300 == 0:
            print(f"chunk {ci}: {f - f0}/{f1 - f0}", flush=True)
    p.stdin.close()
    p.wait()
    return path


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "render"
    if mode == "preview":
        d = os.path.join(WORK, "preview")
        os.makedirs(d, exist_ok=True)
        for s in sys.argv[2:]:
            t = float(s)
            Image.fromarray(render_frame(t)).save(os.path.join(d, f"t{t:07.2f}.png"))
        return
    if mode == "clip":                      # 渲染一段：clip t0 t1 out.mp4
        t0, t1, out = float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                              "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                              "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
        for f in range(int(t0 * FPS), int(t1 * FPS)):
            p.stdin.write(np.ascontiguousarray(render_frame(f / FPS)).tobytes())
        p.stdin.close()
        p.wait()
        return
    if mode == "chunk":                     # 子进程：chunk ci f0 f1
        render_chunk((int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])))
        return
    total = int(math.ceil(T.DUR * FPS))
    workers = int(os.environ.get("WORKERS", 4))
    step = math.ceil(total / workers)
    # 每个分段是独立进程（避免 fork 之后 skia / OpenCV 线程死锁）
    procs, paths = [], []
    for i in range(workers):
        f0, f1 = i * step, min(total, (i + 1) * step)
        procs.append(subprocess.Popen([sys.executable, os.path.abspath(__file__), "chunk", str(i), str(f0), str(f1)]))
        paths.append(os.path.join(WORK, f"chunk_{i}.mp4"))
    for p in procs:
        if p.wait() != 0:
            raise SystemExit("chunk failed")
    lst = os.path.join(WORK, "chunks.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{os.path.abspath(p)}'\n" for p in paths)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    os.path.join(WORK, "video.mp4")], check=True)
    print("done:", os.path.join(WORK, "video.mp4"))


if __name__ == "__main__":
    main()
