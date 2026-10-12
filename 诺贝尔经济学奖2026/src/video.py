"""渲染入口。

python3 video.py still 12.5 30 61.2 ...        # 输出若干时间点的单帧 PNG（build/stills/）
python3 video.py sheet 0 188 2.0 out.png        # 按间隔生成缩略图联系表
python3 video.py render [WORKERS]               # 并行渲染整片（build/chunk_*.mp4）并合成音轨
python3 video.py range T0 T1 out.mp4            # 渲染某一段（带音频）用于检查
"""
import math
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
from PIL import Image

from common import *            # noqa: F401,F403
from timeline import DUR, FADE_T0, FPS, H, W
import scenes_a                 # noqa: F401
import scenes_b                 # noqa: F401
import scenes_c                 # noqa: F401
from registry import SCENES

HUD = BR.Hud(frame_w=W)         # 竖屏：按 1080 宽定位到右上角（BRAND.md 边距 52/30，scale=1）


def hud_alpha(t):
    """右上角官方角标：开场即出现，全程保留（片尾大 logo 期间也在），直到整片最终淡出。"""
    return cl(t / 0.5) * global_fade(t)


def global_fade(t):
    return cl(t / 0.25) * (1 - ss((t - FADE_T0) / (DUR - FADE_T0)))


def render_frame(t):
    fr = Frame(t)
    bg = background(t)
    for (t0, t1, fi, fo, fn) in SCENES:
        if t0 - fi <= t <= t1 + fo:
            a = 1.0
            if t < t0:
                a = ss((t - (t0 - fi)) / fi) if fi > 0 else 0.0
            elif t > t1:
                a = 1 - ss((t - t1) / fo) if fo > 0 else 0.0
            if a > 0.002:
                fn(fr, t, a)
    chapter_overlay(fr, t)
    img = compose(fr, bg)
    img *= vignette()
    img += grain(int(t * FPS))[..., None] * 0.006
    g = global_fade(t)
    if g < 1:
        img *= g
    HUD.draw(img, t, hud_alpha(t))
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def ffmpeg_writer(path, crf=16, preset='medium', audio=None, t0=0.0, dur=None):
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
           '-i', '-']
    if audio:
        cmd += ['-ss', f'{t0:.3f}', '-t', f'{dur:.3f}', '-i', audio, '-map', '0:v', '-map', '1:a', '-c:a', 'aac',
                '-b:a', '192k']
    cmd += ['-c:v', 'libx264', '-preset', preset, '-crf', str(crf), '-pix_fmt', 'yuv420p', '-threads', '2',
            '-x264-params', 'aq-mode=3:deblock=-1,-1', path]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def render_chunk(args):
    ci, f0, f1, crf, preset = args
    path = os.path.join(BUILD, f'chunk_{ci:02d}.mp4')
    p = ffmpeg_writer(path, crf, preset)
    st = time.time()
    for f in range(f0, f1):
        p.stdin.write(render_frame(f / FPS).tobytes())
        if (f - f0) % 150 == 0:
            el = time.time() - st
            print(f'chunk {ci}: {f - f0}/{f1 - f0}  {el / max(f - f0, 1):.2f}s/f', flush=True)
    p.stdin.close()
    p.wait()
    return path


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'render'
    os.makedirs(BUILD, exist_ok=True)
    if mode == 'still':
        d = os.path.join(BUILD, 'stills')
        os.makedirs(d, exist_ok=True)
        for s in sys.argv[2:]:
            t = float(s)
            st = time.time()
            im = render_frame(t)
            Image.fromarray(im).save(os.path.join(d, f't{t:06.2f}.png'))
            print(f't={t:.2f}  {time.time() - st:.2f}s', flush=True)
    elif mode == 'sheet':
        t0, t1, step = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
        out = sys.argv[5]
        ts = np.arange(t0, t1 + 1e-6, step)
        cols = 8
        tw, th = W // 5, H // 5
        rows = math.ceil(len(ts) / cols)
        sheet = Image.new('RGB', (cols * tw, rows * (th + 22)), (20, 20, 20))
        from PIL import ImageDraw
        dr = ImageDraw.Draw(sheet)
        for i, t in enumerate(ts):
            im = Image.fromarray(render_frame(float(t))).resize((tw, th), Image.LANCZOS)
            x, y = (i % cols) * tw, (i // cols) * (th + 22)
            sheet.paste(im, (x, y + 22))
            dr.text((x + 6, y + 4), f'{t:.1f}s', fill=(255, 220, 120))
        sheet.save(out)
        print('saved', out)
    elif mode == 'range':
        t0, t1, out = float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
        audio = os.path.join(BUILD, 'music.wav')
        p = ffmpeg_writer(out, 20, 'veryfast', audio if os.path.exists(audio) else None, t0, t1 - t0)
        for f in range(int(round(t0 * FPS)), int(round(t1 * FPS))):
            p.stdin.write(render_frame(f / FPS).tobytes())
        p.stdin.close()
        p.wait()
        print('saved', out)
    elif mode == 'render':
        workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4
        crf = int(os.environ.get('CRF', 15))
        preset = os.environ.get('PRESET', 'slow')
        total = int(round(DUR * FPS))
        n = workers * 3
        step = math.ceil(total / n)
        jobs = [(i, i * step, min(total, (i + 1) * step), crf, preset) for i in range(n) if i * step < total]
        with Pool(workers) as pool:
            paths = pool.map(render_chunk, jobs, chunksize=1)
        lst = os.path.join(BUILD, 'chunks.txt')
        with open(lst, 'w') as f:
            f.writelines(f"file '{p}'\n" for p in paths)
        print('chunks done', flush=True)


if __name__ == '__main__':
    main()
