"""第三版逐帧渲染。

python3 src/render3.py still 12.5 33 80 ...        → work/stills3/t_XXX.png
python3 src/render3.py chunk F0 F1 out.mp4 [crf]   → 渲染 [F0, F1) 帧
"""
import os, subprocess, sys, time, math
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import W, H, FPS, post, to_u8, smooth, clamp01, ease_out, GOLD, GOLD_SUB, WHITE
from common import put_text, gold_text, footnote
import t3
import ftscene as FT
import vis as V
import bridges as BR
import anim as AN
import brand_bridge as BB
from clips import CLIPS

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
HUD = BB.Hud(scale=1.0, frame_w=W)
FT.SEQ[:] = [(s['id'], s['a0']) for s in t3.SEGS if s['kind'] == 'clip']

# 原始影像上方的标题
HEAD = {
    'LB': ('李录 · 2026 年 10 月', '「今天学到的，明天就没用了」'),
    'LC': ('李录', '知识的复利 → 资本的复利'),
    'LD': ('李录', '复利的基本理念：不要失去'),
    'LT': ('李录', '「我的导师、合伙人、老师查理·芒格」'),
    'BB': ('巴菲特 · 1999 年股东大会', '复利，就像滚雪球'),
    'BA': ('巴菲特 · 1999 年股东大会', '「你只需要富一次」'),
    'MB': ('芒格 · BBC 专访', '「下跌 50%，你能心平气和吗？」'),
    'MU': ('芒格 · 南加州大学毕业演讲', '「每晚睡前，都比早上更聪明一点」'),
    'MT': ('芒格 · 南加州大学毕业演讲', '「无缝的、值得信任的网」'),
}
CLIP_MOOD = {'L': 'warm', 'B': 'neutral', 'M': 'neutral'}


def chapters():
    s = {x['id']: x for x in t3.SEGS}
    return [(s['LB']['t0'] + 0.6, s['title']['t0'] - 0.3, '01', '热点 · 李录谈 AI 与复利'),
            (s['title']['t1'] + 0.2, s['G5']['t0'] - 0.2, '01', '热点 · 李录谈 AI 与复利'),
            (s['G5']['t0'], s['MT']['t1'] - 0.3, '02', '巴菲特与芒格 · 不要失去'),
            (s['G10']['t0'] + 0.3, s['G13']['t0'] - 0.2, '03', '复利的第一性原理'),
            (s['G13']['t0'], s['G13']['t1'] - 1.5, '04', '人生的复利')]


CHAP = chapters()


def chapter(F, t):
    for a, b, no, name in CHAP:
        al = min(smooth((t - a) / 0.6), smooth((b - t) / 0.4)) if a <= t <= b else 0
        if al > 0:
            put_text(F, no, 62, 72, 40, 'mono', GOLD, al, 200, 'left', shadow=0.5, glow=0.2)
            put_text(F, name, 126, 74, 26, 'serif_m', np.array([0.92, 0.88, 0.8]), al * 0.9, 700, 'left', shadow=0.5)


def clip_head(F, t):
    ac = FT.active(t)
    if not ac: return
    cid, u, a, _ = ac
    if cid not in HEAD: return
    small, big = HEAD[cid]
    x0, y0, w, h = FT.rect_of(cid)
    yb = min(y0 - 70, 300)
    if CLIPS[cid].get('context'): yb = min(yb, y0 - 110)
    put_text(F, small, W / 2, yb - 64, 28, 'sans', GOLD_SUB * 1.15, a, 900, shadow=0.6, track=2)
    gold_text(F, big, W / 2, yb, 54, 'serif', a, clamp01((u + 0.3) / 0.6), glow=0.25)


def title(F, t):
    seg = t3.seg('title')
    u = t - seg['t0']
    a = min(1.0, smooth((seg['t1'] + 0.3 - t) / 0.7))
    F += np.float32(1.2 * math.exp(-u * 9)) * np.array([1.0, 0.9, 0.75], np.float32)
    if u < 1.5:
        V.line(F, AN._circle(W / 2, 900, 60 + 1300 * ease_out(u / 1.5)), np.array([1.0, 0.85, 0.55]), 5, (1 - u / 1.5) ** 1.5, 1.2, closed=True)
    r = np.random.default_rng(9)
    n = 1200; ang = r.uniform(0, 2 * math.pi, n); sp = r.gamma(2, 230, n)
    d = (1 - math.exp(-u * 1.6)) / 1.6
    from engine import splat, GOLD_HI
    splat(F, (W / 2 + np.cos(ang) * sp * d).astype(np.float32), (900 + np.sin(ang) * sp * d * 1.4).astype(np.float32),
          np.full(n, 1.5, np.float32), GOLD_HI, a * 0.75 * math.exp(-u * 0.5))
    gold_text(F, 'AI 越快，', W / 2, 800, 150, 'serif', a, clamp01(u / 0.4), glow=0.35 + 0.6 * math.exp(-u * 3), sweep=(u - 2.0) / 1.4)
    gold_text(F, '越要慢', W / 2, 990, 190, 'serif', a, clamp01(u / 0.4 * 1.6 - 0.6), glow=0.5 + 0.8 * math.exp(-u * 3), sweep=(u - 2.15) / 1.4)
    put_text(F, '复利的秘密，不是更快，而是不失去', W / 2, 1170, 44, 'serif_m', np.array([0.95, 0.9, 0.8]), a * smooth((u - 1.6) / 0.7), 980,
             reveal=clamp01((u - 1.6) / 1.2), glow=0.1)
    put_text(F, '李录  ·  巴菲特  ·  芒格', W / 2, 1265, 32, 'sans_l', GOLD_SUB * 1.2, a * smooth((u - 2.4) / 0.7), 900, track=6)
    footnote(F, '李录、巴菲特、芒格的讲话均为原始影像原声 · 中文字幕为本片翻译', a * smooth((u - 3.0) / 0.7), y=1640, size=22)


HITS = []          # (时刻, 强度)：卡点闪光 + 色散


def _hits():
    s = {x['id']: x for x in t3.SEGS}
    h = [(s['title']['t0'], 1.0), (s['G14']['t0'], 1.0)]
    for sid, kw, k in (('A03', '四百多倍', 0.6), ('A04', '亏掉一半', 0.8), ('A06', '乘以一个零', 0.9), ('A07', '首先得', 0.5)):
        h.append((t3.wt(sid, kw), k))
    return h


HITS = _hits()


def post_params(t):
    p = dict(bloom=0.9, grain=0.012, ca=0.0, exposure=1.0)
    for th, k in HITS:
        d = t - th
        if 0 <= d < 0.45: p['ca'] = max(p['ca'], 6 * k * (1 - d / 0.45))
    return p


def frame(t):
    sg = t3.seg_at(t)
    kind = sg['kind']
    if kind == 'clip':
        F = V.bg(t, CLIP_MOOD.get(sg['id'][0], 'neutral'), stars=0.6)
        FT.ft_bg(F, t)
        clip_head(F, t)
    elif kind == 'vo':
        fn, mood = BR.SCENES[sg['id']]
        F = V.bg(t, mood)
        V.grid_floor(F, t, 0.5)
        fn(F, t)
        # 片段窗口的淡入淡出跨越到解说段时，也要画背景铺底
        FT.ft_bg(F, t)
    elif kind == 'title':
        F = V.bg(t, 'warm', stars=1.2)
        title(F, t)
    elif kind == 'anim':
        fn, mood = AN.SCENES[sg['id']]
        F = V.bg(t, mood)
        V.grid_floor(F, t, 0.35, speed=0.5)
        fn(F, t)
    elif kind == 'summary':
        F = V.bg(t, 'warm', stars=1.0)
        AN.summary(F, t)
    else:
        F = V.bg(t, 'neutral', stars=0.4, drift=0.3)
        AN.brand(F, t)
    if kind in ('vo', 'anim'):
        # 缓慢推镜：每个段落内画面从 1.0 推到 1.035 倍，给静态信息画面一点呼吸感
        z = 1.0 + 0.035 * smooth((t - sg['t0']) / max(sg['t1'] - sg['t0'], 1.0))
        M = cv2.getRotationMatrix2D((W / 2, 880), 0, z)
        F = cv2.warpAffine(F, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if kind not in ('title', 'summary', 'brand'):
        chapter(F, t)
    if kind in ('vo', 'anim'):
        V.vo_sub(F, t, t3.SENTS)
    F = post(F, t, **post_params(t))
    FT.ft_overlay(F, t)                           # 原始影像：显示空间合成
    HUD.draw(F, t, alpha=1.0)
    if kind == 'brand':
        F *= AN.brand_fade(t)                     # 整体（含右上角角标）淡出
    return F


def still(ts):
    out = os.path.join(ROOT, 'work', 'stills3'); os.makedirs(out, exist_ok=True)
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
