"""把 clips.CLIPS 中的每个片段处理成可直接合成的素材：
  footage/clips/<id>.mp4   30fps，去硬字幕、按人物追踪裁切、缩放到画中窗尺寸
  footage/clips/<id>.wav   48kHz 单声道原声
用法：python3 src/prep_clips.py [id ...]
"""
import os, sys, subprocess, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clips import CLIPS, ROOT, track
from desub import desub

SRC = os.path.join(ROOT, 'footage', 'src')
OUT = os.path.join(ROOT, 'footage', 'clips')
WIN_W, WIN_HMAX = 1000, 780
FPS = 30


def probe(path):
    s = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                                   '-of', 'json', path], capture_output=True, text=True).stdout)['streams'][0]
    return s['width'], s['height']


def crop_path(c, sw, sh, n):
    """每帧的裁切框 (x0, y0, w, h)"""
    if 'crop' in c:
        return [c['crop']] * n
    tr = track(c['track'])
    ts = np.array([d['t'] for d in tr if d['box']]); bx = np.array([d['box'] for d in tr if d['box']], np.float64) / 1000
    hx = (bx[:, 1] + bx[:, 3]) / 2 * sw; hy = (bx[:, 0] + bx[:, 2]) / 2 * sh
    tt = c['a'] + np.arange(n) / FPS
    x = np.interp(tt, ts, hx); y = np.interp(tt, ts, hy)
    k = np.exp(-0.5 * (np.arange(-30, 31) / 12) ** 2); k /= k.sum()       # 平滑，去抖
    x = np.convolve(np.pad(x, 30, mode='edge'), k, 'valid'); y = np.convolve(np.pad(y, 30, mode='edge'), k, 'valid')
    w, h = sw / c['zoom'], sh / c['zoom']
    out = []
    for xi, yi in zip(x, y):
        x0 = min(max(xi - w * 0.5, 0), sw - w)
        # 尽量让裁切框底边停在英文硬字幕带之上（0.80），但人头不低于框高 62%
        y0 = yi - h * 0.38
        if c.get('bands'): y0 = min(y0, max(0.80 * sh - h, yi - h * 0.62))
        y0 = min(max(y0, 0), sh - h)
        out.append((x0, y0, w, h))
    return out


def prep(cid):
    c = CLIPS[cid]
    src = os.path.join(SRC, c['src'])
    sw, sh = probe(src)
    dur = c['b'] - c['a']; n = int(round(dur * FPS))
    ss = c['a'] - c.get('off', 0.0)                       # 源文件中的起点
    boxes = crop_path(c, sw, sh, n)
    w0, h0 = boxes[0][2], boxes[0][3]
    oh = min(WIN_HMAX, WIN_W * h0 / w0); ow = int(round(oh * w0 / h0 / 2) * 2); oh = int(round(oh / 2) * 2)
    os.makedirs(OUT, exist_ok=True)
    dec = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-ss', f"{ss:.3f}", '-i', src, '-t', f'{dur:.3f}', '-r', str(FPS),
                            '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE)
    enc = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{ow}x{oh}', '-r', str(FPS),
                            '-i', '-', '-c:v', 'libx264', '-crf', '12', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                            os.path.join(OUT, f'{cid}.mp4')], stdin=subprocess.PIPE)
    fsz = sw * sh * 3; i = 0
    while True:
        buf = dec.stdout.read(fsz)
        if len(buf) < fsz: break
        f = np.frombuffer(buf, np.uint8).reshape(sh, sw, 3).copy()
        if c.get('bands'):
            f, _ = desub(f, c['bands'])
        x0, y0, w, h = boxes[min(i, len(boxes) - 1)]
        # 亚像素裁切 + 缩放：仿射一步完成
        M = np.array([[ow / w, 0, -x0 * ow / w], [0, oh / h, -y0 * oh / h]], np.float32)
        g = cv2.warpAffine(f, M, (ow, oh), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        bl = cv2.GaussianBlur(g, (0, 0), 1.6)
        g = cv2.addWeighted(g, 1.45, bl, -0.45, 0)            # 轻度锐化（放大后的软化补偿）
        enc.stdin.write(g.tobytes()); i += 1
    enc.stdin.close(); enc.wait(); dec.wait()
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', f"{ss:.3f}", '-i', src, '-t', f'{dur:.3f}', '-vn', '-ac', '1', '-ar', '48000',
                    os.path.join(OUT, f'{cid}.wav')], check=True)
    print(cid, f'{i} frames', f'{ow}x{oh}', f'{dur:.2f}s', flush=True)


if __name__ == '__main__':
    ids = sys.argv[1:] or list(CLIPS)
    for cid in ids:
        prep(cid)
