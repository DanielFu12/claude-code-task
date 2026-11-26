"""竖版（1080×1920）：旁白、配乐、时间轴与横版完全相同。

主舞台复用横版场景渲染（去掉横版的字幕、导航和角标），居中放在竖屏中部；
上方是竖屏专属的大号章节标题与六层导航，下方是加大的双行字幕，右上角是品牌角标，
背景用同一帧画面的模糊放大铺满，上下羽化衔接。
用法：python3 src/vertical.py chunk f0 f1 out.mp4 / sheet out.png t1 t2 ...
"""
import math, os, subprocess, sys
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import video as V
from engine import glyph, text_width, eo, eio, cl, lerpc, C, GOLD, GOLD2, WHITE, GREY, FPS
from common import TL, SCENES, CHAP, LAYERS, LAYER_COL, TOTAL, kick_pulse
from brand import Hud

VW, VH = 1080, 1920
CROPX = 100                  # 横版左右各裁 100px，舞台放大
SW, SH = 1080, 694           # 舞台尺寸
SY = 690                     # 舞台顶边
HUDV = Hud(scale=1.0, frame_w=VW)
NFR = int(round(TOTAL * FPS))
_FEATHER = None


def feather():
    global _FEATHER
    if _FEATHER is None:
        m = np.ones((SH, SW), np.float32)
        f = 70
        ramp = np.linspace(0, 1, f) ** 1.5
        m[:f] *= ramp[:, None]; m[-f:] *= ramp[::-1][:, None]
        _FEATHER = m[..., None]
    return _FEATHER


def vtext(img, s, x, y, size, fnt, col, a=1.0, anchor='m', track=0.0, shadow=0.6, glow=0.0):
    if a <= 0.01 or not s: return
    size = int(size)
    tw = text_width(s, fnt, size, track)
    cx = x - tw / 2 if anchor == 'm' else (x if anchor == 'l' else x - tw)
    base = y + size * 0.36
    colv = np.array(col, np.float32)
    for ch in s:
        m, adv, pad, bl = glyph(ch, fnt, size)
        x0, y0 = int(round(cx - pad)), int(round(base - bl))
        h, w = m.shape
        X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + w, VW), min(y0 + h, VH)
        if X1 > X0 and Y1 > Y0 and ch != ' ':
            mm = m[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] * a
            if shadow > 0:
                sh = cv2.GaussianBlur(mm, (0, 0), size * 0.08) * shadow
                img[Y0:Y1, X0:X1] *= (1 - sh)[..., None]
            if glow > 0:
                g = cv2.GaussianBlur(mm, (0, 0), size * 0.25) * glow
                img[Y0:Y1, X0:X1] += g[..., None] * colv
            reg = img[Y0:Y1, X0:X1]
            reg *= (1 - mm)[..., None]
            reg += mm[..., None] * colv
        cx += adv + track * size


def wrap(s, n=15):
    if len(s) <= n: return [s]
    # 尽量在标点/中点断开
    k = len(s) // 2
    best = k
    for d in range(0, k):
        for j in (k - d, k + d):
            if 0 < j < len(s) and s[j - 1] in '，、：；':
                best = j; break
        else:
            continue
        break
    return [s[:best].rstrip('，'), s[best:]]


def chapter_of(t):
    return SCENES[V.scene_at(t)]


def top_block(img, t):
    s = chapter_of(t)
    ch = CHAP[s['ch']]
    first = next(x for x in SCENES if x['ch'] == s['ch'])
    k = eo((t - first['start'] - 0.3) / 0.6)
    col = C(*ch['col'])
    if s['id'] in ('hook', 'title', 'outro') or not ch['tag']:
        a = 1.0 if s['id'] == 'hook' else 0.0
        vtext(img, '企业盈利能力评估框架', VW / 2, 300, 66, 'serif_black', GOLD, a * min(1, t / 2.0), track=0.06, glow=0.25)
        vtext(img, '从巴菲特、芒格出发', VW / 2, 390, 34, 'serif_med', GOLD2, a * min(1, t / 2.0) * 0.9, track=0.2)
        return
    parts = ch['tag'].split(' · ')
    if len(parts) == 2:
        vtext(img, parts[0], VW / 2, 250, 44, 'sans_bold', lerpc(col, WHITE, 0.2), k, track=0.3)
        vtext(img, parts[1], VW / 2, 340, 82, 'serif_black', col, k, glow=0.3)
    else:
        vtext(img, parts[0], VW / 2, 320, 82, 'serif_black', col, k, glow=0.3)
    # 六层导航
    cur = s['ch'] if s['ch'].startswith('L') else None
    for j, (lk, nm) in enumerate(LAYERS):
        x = VW / 2 + (j - 2.5) * 150
        lc = LAYER_COL[lk]
        on = cur == lk
        r = 13 if on else 8
        c = (int(x), 470)
        cv2.circle(img, c, r, tuple(float(v) * (1 if on else 0.45) for v in lc), -1 if on else 2, cv2.LINE_AA)
        vtext(img, nm[:2] if len(nm) > 2 else nm, x, 515, 24, 'sans_med', lerpc(lc, WHITE, 0.3), k * (1 if on else 0.55), shadow=0)


def subtitle_block(img, t):
    if chapter_of(t)['id'] in ('quote', 'outro'): return
    for s in TL['subs']:
        if s['start'] - 0.05 <= t < s['end']:
            a = eo((t - s['start'] + 0.05) / 0.12) * (1 - eio((t - s['end'] + 0.12) / 0.12))
            rows = wrap(s['text'])
            for i, r in enumerate(rows):
                vtext(img, r, VW / 2, 1640 + (i - (len(rows) - 1) / 2) * 80, 56, 'sans_bold', (0.98, 0.98, 0.98), a, shadow=0.9)
            break


def fit_size(s, fnt, size, maxw=1000):
    w = text_width(s, fnt, int(size))
    return size * min(1.0, maxw / max(w, 1))


def callout_block(img, callouts):
    """场景标题：舞台上方一行主标题，舞台下方一行副标题（竖屏原生字号）"""
    if not callouts: return
    cs = sorted(callouts, key=lambda c: -c[3] * min(c[2], 1))
    seen, picked = set(), []
    for c in cs:
        if c[0] in seen: continue
        seen.add(c[0]); picked.append(c)
        if len(picked) == 2: break
    s, col, a, size, fnt = picked[0]
    sz = fit_size(s, fnt, min(max(size * 0.9, 64), 92))
    vtext(img, s, VW / 2, 610, sz, fnt, col, min(a, 1), glow=0.3, shadow=0.9)
    if len(picked) > 1:
        s, col, a, size, fnt = picked[1]
        sz = fit_size(s, fnt, min(max(size * 0.75, 48), 64))
        vtext(img, s, VW / 2, 1490, sz, fnt, col, min(a, 1), glow=0.25, shadow=0.9)


def bottom_block(img, t):
    y = 1800
    vtext(img, '巴芒价值 · 企业盈利能力评估框架', VW / 2, y - 40, 26, 'sans_med', GREY, 0.7, shadow=0)
    x1 = int(VW * t / TOTAL)
    col = C(*CHAP[chapter_of(t)['ch']]['col'])
    cv2.rectangle(img, (80, y), (VW - 80, y + 4), (0.12, 0.12, 0.14), -1)
    cv2.rectangle(img, (80, y), (80 + int((VW - 160) * t / TOTAL), y + 4), tuple(float(v) * 0.8 for v in col), -1)


def render_v(t):
    st, callouts = V.render(t, stage_only=True, vertical=True)   # 横版舞台 + 场景标题
    small = cv2.resize(st[:, CROPX:1920 - CROPX], (SW, SH), interpolation=cv2.INTER_AREA)
    # 背景：同一帧的模糊放大
    bgsrc = cv2.resize(st, (480, 270), interpolation=cv2.INTER_AREA)
    bgsrc = cv2.GaussianBlur(bgsrc, (0, 0), 6)
    bg = cv2.resize(bgsrc, (int(VH * 16 / 9), VH), interpolation=cv2.INTER_LINEAR)
    x0 = (bg.shape[1] - VW) // 2
    img = bg[:, x0:x0 + VW] * 0.35
    img = np.ascontiguousarray(img)
    f = feather()
    reg = img[SY:SY + SH]
    reg *= (1 - f)
    reg += small * f
    top_block(img, t)
    callout_block(img, callouts)
    subtitle_block(img, t)
    bottom_block(img, t)
    HUDV.draw(img, t)
    img = img + V.grain(0)[:VH, :VW] if V.grain(0).shape[0] >= VH else img
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def cmd_sheet(path, ts, cols=4, scale=0.4):
    ims = []
    for t in ts:
        im = cv2.resize(render_v(float(t)), (int(VW * scale), int(VH * scale)), interpolation=cv2.INTER_AREA)
        cv2.putText(im, f'{float(t):.1f}', (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        ims.append(im)
    while len(ims) % cols: ims.append(np.zeros_like(ims[0]))
    rows = [np.hstack(ims[i:i + cols]) for i in range(0, len(ims), cols)]
    cv2.imwrite(path, cv2.cvtColor(np.vstack(rows), cv2.COLOR_RGB2BGR))


def cmd_chunk(f0, f1, path, crf=14):
    f1 = min(f1, NFR)
    p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{VW}x{VH}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', str(crf),
                          '-pix_fmt', 'yuv420p', '-tune', 'animation', path], stdin=subprocess.PIPE)
    import time
    t0 = time.time()
    for fi in range(f0, f1):
        p.stdin.write(render_v(fi / FPS).tobytes())
        if (fi - f0) % 300 == 0:
            print(f'[{path}] {fi - f0}/{f1 - f0}  {(time.time() - t0) / max(fi - f0, 1):.3f}s/f', flush=True)
    p.stdin.close(); p.wait()


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'sheet': cmd_sheet(sys.argv[2], sys.argv[3:])
    elif c == 'chunk': cmd_chunk(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
