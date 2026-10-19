"""逐帧渲染。

python3 src/render.py still 12.5 33 80 ...        → work/stills/t_XXX.png
python3 src/render.py chunk F0 F1 out.mp4          → 渲染 [F0, F1) 帧
"""
import os, subprocess, sys, time
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import W, H, FPS, post, to_u8, smooth, clamp01
import scenes as S
from common import subtitle
from timeline import A, START, lines, DUR
from common import put_text
from engine import GOLD
from script import NARRATION, CAPTIONS
import brand_bridge as BB
import part1 as P1

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
HUD = BB.Hud(scale=1.0, frame_w=W)

# (起, 止, 函数)
SCENES = [
    (0.0, A['drop'], P1.sc_part1),              # 钩子：李录原声
    (A['drop'], A['calm'], S.sc_title),         # 标题重拍
    (A['calm'], A['climax'], P1.sc_part1),      # 李录 → 巴菲特、芒格原声
    (A['climax'], A['final'], S.sc_climax),     # 约 1 分钟动画：复利的第一性原理 → 人生的复利
    (A['final'], A['end'] + 1, S.sc_brand),     # 品牌片尾
]

# 屏幕文字（无配音）只用于动画段
LINES = [l for l in lines() if l[0] >= 'N18']


def scene_frame(t):
    for a, b, fn in SCENES:
        if a <= t < b:
            return fn(t)
    return np.zeros((H, W, 3), np.float32)


def sub_at(t):
    for nid, a, b in LINES:
        if a - 0.05 <= t <= b + 0.25:
            al = min(smooth((t - a + 0.05) / 0.2), smooth((b + 0.25 - t) / 0.25))
            return CAPTIONS.get(nid, NARRATION[nid]), al
    return None, 0


def post_params(t):
    p = dict(bloom=0.9, grain=0.012, ca=0.0, exposure=1.0)
    for hit in (A['drop'], A['crash'], A['epic'], A['final']):
        d = t - hit
        if 0 <= d < 0.5: p['ca'] = 6 * (1 - d / 0.5)
    return p


CHAPTERS = [  # 左上角章节标签（与右上角品牌角标对称）
    (0.6, A['drop'] - 1.0, '01', '李录 · AI 时代的复利'),
    (A['calm'], P1.T['BA'] - 4.2, '01', '李录 · AI 时代的复利'),
    (P1.T['BA'] - 4.0, A['climax'] - 0.8, '02', '巴菲特与芒格 · 不要失去'),
    (A['climax'], A['epic'] - 0.3, '03', '复利的第一性原理'),
    (A['epic'] - 0.3, A['final'] - 3.5, '04', '人生的复利'),
]


def chapter(F, t):
    for a, b, no, name in CHAPTERS:
        al = min(smooth((t - a - 0.3) / 0.6), smooth((b - t) / 0.4)) if a <= t <= b else 0
        if al > 0:
            put_text(F, no, 62, 72, 40, 'mono', GOLD, al, 200, 'left', shadow=0.5, glow=0.2)
            put_text(F, name, 126, 74, 26, 'serif_m', np.array([0.92, 0.88, 0.8]), al * 0.9, 600, 'left', shadow=0.5)


def frame(t):
    F = scene_frame(t)
    chapter(F, t)
    txt, al = sub_at(t)
    if txt and getattr(S, 'SHOW_SUB', lambda t: True)(t):
        subtitle(F, txt, al)
    F = post(F, t, **post_params(t))
    if t < A['climax']:
        P1.overlay(F, t)                          # 原始影像（显示空间合成，不经色调映射）
    # 品牌角标：全片右上角（最终淡出时随画面淡出）
    end_fade = 1 - smooth((t - (DUR - 2.2)) / 2.0)
    HUD.draw(F, t, alpha=1.0)
    F *= end_fade
    return F


def still(ts):
    out = os.path.join(ROOT, 'work', 'stills'); os.makedirs(out, exist_ok=True)
    for t in ts:
        t0 = time.time(); fr = frame(float(t))
        p = os.path.join(out, f't_{float(t):07.2f}.png')
        cv2.imwrite(p, cv2.cvtColor(to_u8(fr), cv2.COLOR_RGB2BGR))
        print(p, f'{time.time() - t0:.2f}s', flush=True)


def chunk(f0, f1, path, crf=14):
    cmd = ['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf), '-pix_fmt', 'yuv420p', path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(f0, f1):
        p.stdin.write(to_u8(frame(f / FPS)).tobytes())
        if (f - f0) % 60 == 0:
            print(f'{path}: frame {f} ({(f - f0 + 1) / (time.time() - t0 + 1e-6):.2f} fps)', flush=True)
    p.stdin.close(); p.wait()


if __name__ == '__main__':
    if sys.argv[1] == 'still':
        still(sys.argv[2:])
    elif sys.argv[1] == 'chunk':
        cv2.setNumThreads(1)
        chunk(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 14)
