"""取原始素材：只按区间读取 archive.org 上 1994 年全场录像中需要的音频与影像，不下载整片（约 1.5GB）。

用法：python3 src/fetch.py WORK
输出：WORK/orig_src.m4a（问答原声 310 秒）、WORK/orig16.wav（识别用）、
      WORK/qa_c.mp4（同一区间的上午场录像，已裁到干净画面区并轻度降噪）、WORK/broll_<秒>_c.mp4（片头历史影像）
ffmpeg 不读 HTTPS_PROXY 环境变量，这里显式传 -http_proxy。
"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import ARCHIVE_URL, CLIP_IN, CLIP_LEN, BROLL, PIC_BOX

work = sys.argv[1]
os.makedirs(work, exist_ok=True)
proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
FF = ['ffmpeg', '-loglevel', 'error', '-y']
NET = FF + (['-http_proxy', proxy] if proxy else [])


def run(args):
    for k in range(4):
        if subprocess.run(args).returncode == 0: return
    raise SystemExit('failed: ' + ' '.join(args))


x0, y0, x1, y1 = PIC_BOX
CROP = f'crop={x1 - x0}:{y1 - y0}:{x0}:{y0},hqdn3d=1.5:1.5:4:4'
raw = os.path.join(work, 'qa_raw.mp4')
if not os.path.exists(raw):
    run(NET + ['-ss', str(CLIP_IN), '-i', ARCHIVE_URL, '-t', str(CLIP_LEN), '-c', 'copy', raw])
p = os.path.join(work, 'orig_src.m4a')
if not os.path.exists(p):
    run(FF + ['-i', raw, '-vn', '-c:a', 'copy', p])
run(FF + ['-i', p, '-ac', '1', '-ar', '16000', os.path.join(work, 'orig16.wav')])
out = os.path.join(work, 'qa_c.mp4')
if not os.path.exists(out):
    run(FF + ['-i', raw, '-an', '-vf', CROP, '-c:v', 'libx264', '-crf', '14', '-g', '15', '-pix_fmt', 'yuv420p', out])
for b in BROLL:
    r = os.path.join(work, f'broll_{b}.mp4'); o = os.path.join(work, f'broll_{b}_c.mp4')
    if not os.path.exists(r):
        run(NET + ['-ss', str(b), '-i', ARCHIVE_URL, '-t', '16', '-an', '-c:v', 'copy', r])
    if not os.path.exists(o):
        run(FF + ['-i', r, '-vf', CROP, '-c:v', 'libx264', '-crf', '14', '-g', '15', '-pix_fmt', 'yuv420p', o])
print('fetched into', work)
