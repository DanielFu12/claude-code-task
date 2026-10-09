"""《你为什么总买在山顶？》逐帧渲染入口。

    python3 src/film.py preview 3.2 17.5 40          # 输出若干时间点的预览帧到 work/preview/
    python3 src/film.py sheet 0 265 2.0              # 每隔 2 秒一帧，拼成联系表
    python3 src/film.py chunk F0 F1 OUT.mp4          # 渲染第 F0..F1 帧（build.sh 并行调用）
"""
import os, subprocess, sys, time
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa
# 巴芒价值品牌角标与片尾资产：统一取自仓库根目录 brand/（规范见 brand/BRAND.md）
sys.path.insert(0, os.path.join(ROOT, '..', 'brand'))
from brand import Hud  # noqa: E402
import scenes_a, scenes_b, scenes_c  # noqa: E402
HUD = Hud()

SCENES = scenes_a.SCENES_A + scenes_b.SCENES_B + scenes_c.SCENES_C
DROPS = (T_D1, T_D2, T_D3, T_D4)
DROP_COL = {T_D1: (1.0, 0.92, 0.88), T_D2: (0.75, 1.0, 0.92), T_D3: (1.0, 0.93, 0.75), T_D4: (1.0, 0.93, 0.78)}


def global_fade(t):
    return cl(t / 0.5) * (1 - eio((t - (END - 2.6)) / 2.4))


def render_frame(t, i=0):
    f = Frame(t)
    bg = background(t)
    dust_a = 0.0 if in_break(t) else 1.0
    draw_dust(f, t, 0.35 + 0.65 * dust_a)
    for s in SCENES:
        s(f, t)
    for d in DROPS:
        if d <= t < d + 1.2:
            x = t - d
            f.flash = max(f.flash, (0.10 if d == T_D4 else 0.24) * math.exp(-x / 0.11))
            f.flash_col = DROP_COL[d]
            f.ca = max(f.ca, 7 * math.exp(-x / 0.25))
            if x < 0.45:
                rr = np.random.default_rng(int(t * 1000))
                amp = 9 * (1 - x / 0.45)
                f.shake = (int(rr.normal() * amp), int(rr.normal() * amp))
    draw_chrome(f, t)
    draw_narration(f, t)
    band = 1.0 if narration_active(t) else 0.5
    out = finish(f, bg, i, band)
    g = global_fade(t)
    HUD.draw(out, t, 1.0)        # 右上角角标全程保留，只随整片最终淡出
    out *= g
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    mode = sys.argv[1]
    if mode == 'preview':
        d = os.path.join(WORK, 'preview'); os.makedirs(d, exist_ok=True)
        for s in sys.argv[2:]:
            t = float(s)
            t0 = time.time()
            img = render_frame(t, int(t * FPS))
            Image.fromarray(img).save(os.path.join(d, f't{t:07.2f}.png'))
            print(f'{t:.2f}  {time.time() - t0:.2f}s', flush=True)
    elif mode == 'sheet':
        t0, t1, step = map(float, sys.argv[2:5])
        out = sys.argv[5] if len(sys.argv) > 5 else os.path.join(WORK, 'sheet.png')
        ts = np.arange(t0, t1, step)
        thumbs = [Image.fromarray(render_frame(t, int(t * FPS))).resize((480, 270), Image.LANCZOS) for t in ts]
        cols = 5
        rows = (len(thumbs) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * 480, rows * 290), (0, 0, 0))
        from PIL import ImageDraw
        dr = ImageDraw.Draw(sheet)
        for k, (t, im) in enumerate(zip(ts, thumbs)):
            x, y = (k % cols) * 480, (k // cols) * 290
            sheet.paste(im, (x, y))
            dr.text((x + 4, y + 272), f'{t:.2f}', fill=(200, 200, 200))
        sheet.save(out)
        print('sheet ->', out)
    elif mode == 'chunk':
        cv2.setNumThreads(1)          # 多进程并行时避免线程超订
        f0, f1, path = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        # 中间文件：近无损（最终成片由 build.sh 统一做两遍编码）
        p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                              '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '10',
                              '-pix_fmt', 'yuv420p', '-threads', '1', path], stdin=subprocess.PIPE)
        t0 = time.time()
        for i in range(f0, f1):
            p.stdin.write(render_frame(i / FPS, i).tobytes())
            if (i - f0) % 150 == 0:
                el = time.time() - t0
                print(f'[{f0}-{f1}] {i - f0}/{f1 - f0}  {el:.0f}s', flush=True)
        p.stdin.close(); p.wait()


if __name__ == '__main__':
    main()
