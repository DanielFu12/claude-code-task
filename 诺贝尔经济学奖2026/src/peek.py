"""python3 peek.py out.png t1 t2 ...  → 渲染若干帧并拼成联系表（每帧 360×640，每行 6 张）"""
import sys, os
from multiprocessing import Pool
from PIL import Image, ImageDraw
import numpy as np


def one(t):
    import video
    return t, video.render_frame(t)


if __name__ == '__main__':
    out = sys.argv[1]
    ts = [float(x) for x in sys.argv[2:]]
    with Pool(4) as p:
        res = p.map(one, ts)
    cols = min(6, len(ts))
    rows = (len(ts) + cols - 1) // cols
    sw, sh = 360, 640
    sheet = Image.new('RGB', (cols * sw, rows * (sh + 20)), (25, 25, 25))
    d = ImageDraw.Draw(sheet)
    for i, (t, im) in enumerate(res):
        x, y = (i % cols) * sw, (i // cols) * (sh + 20)
        sheet.paste(Image.fromarray(im).resize((sw, sh), Image.LANCZOS), (x, y + 20))
        d.text((x + 4, y + 3), f'{t:.2f}s', fill=(255, 210, 120))
        Image.fromarray(im).save(os.path.join(os.path.dirname(out), f'f{t:06.2f}.png'))
    sheet.save(out)
    print('saved', out)
