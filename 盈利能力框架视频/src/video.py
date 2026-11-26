"""《企业盈利能力评估框架》10 分钟动态图形视频 —— 主渲染程序。

用法：
  python3 src/video.py frame 123.4 out.png      # 渲染单帧
  python3 src/video.py sheet out.png t1 t2 ...  # 多帧拼图
  python3 src/video.py chunk f0 f1 out.mp4      # 渲染帧区间
"""
import math, os, subprocess, sys
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', 'brand'))
from common import *
from brand import Hud, load_logo
import scenes_a, scenes_b, scenes_c, scenes_d

DRAW = {}
for mod in (scenes_a, scenes_b, scenes_c, scenes_d):
    DRAW.update(mod.DRAW)

HUD = Hud()
NFR = int(round(TOTAL * FPS))

# 场景交接时刻：非重拍切换时，旧画面保留到新场景第一个元素出现前（最多 1.8 秒）
HANDOFF = []
for _i, _s in enumerate(SCENES):
    if _i + 1 < len(SCENES) and not SCENES[_i + 1]['sting']:
        _n = SCENES[_i + 1]
        _fc = min(_n['cq'].values()) - 0.1 if _n['cq'] else _n['start'] + 0.5
        HANDOFF.append(min(max(_fc, _n['start'] + 0.3), _n['start'] + 1.8))
    else:
        HANDOFF.append(_s['end'])

# ---------------------------------------------------------------- background
NB1 = fbm(480, 270, 11, 6, 3)
NB2 = fbm(480, 270, 22, 6, 4)
NB3 = fbm(480, 270, 33, 5, 6)
RNG = np.random.default_rng(99)
NST = 1400
ST_X = RNG.uniform(-1.0, 1.0, NST); ST_Y = RNG.uniform(-1.0, 1.0, NST); ST_Z = RNG.uniform(0.15, 1.0, NST)
ST_TW = RNG.uniform(0, 6.28, NST)
ST_COL = np.array([lerpc(WHITE, [ICE, GOLD2, WHITE, VIOLET][i % 4], 0.35) for i in range(NST)], np.float32)

# 章节背景色（主色、副色、强度）
BGCOL = {
    'hook': (C(30, 50, 110), C(60, 30, 90), 0.75), 'core': (C(110, 80, 30), C(30, 50, 120), 0.85),
    'layer': (C(30, 70, 140), C(80, 40, 120), 0.9), 'L0': (C(140, 20, 35), C(60, 15, 50), 0.9),
    'L1': (C(130, 95, 25), C(40, 40, 110), 0.9), 'L2': (C(140, 70, 20), C(50, 30, 80), 0.85),
    'L3': (C(15, 110, 90), C(25, 50, 110), 0.9), 'L4': (C(25, 70, 150), C(60, 30, 110), 0.9),
    'L5': (C(80, 45, 150), C(25, 60, 120), 0.9), 'combo': (C(130, 90, 25), C(110, 30, 70), 1.0),
    'proc': (C(20, 90, 130), C(60, 40, 110), 0.9), 'end': (C(120, 85, 30), C(40, 30, 90), 0.85),
}


def scene_at(t):
    for i, s in enumerate(SCENES):
        if s['start'] <= t < s['end']:
            return i
    return len(SCENES) - 1


def bg_params(t):
    i = scene_at(t)
    s = SCENES[i]
    c1, c2, I = BGCOL[s['ch']]
    # 与上一章节的颜色过渡（章节重拍后 1.2 秒内）
    if i > 0 and SCENES[i - 1]['ch'] != s['ch']:
        x = eio((t - s['start']) / 1.2)
        p1, p2, pI = BGCOL[SCENES[i - 1]['ch']]
        c1, c2, I = lerpc(p1, c1, x), lerpc(p2, c2, x), lerp(pI, I, x)
    return c1, c2, I


def background(t):
    c1, c2, I = bg_params(t)
    if t < 3.5: I *= eio(t / 3.5)
    if SC['outro']['start'] <= t: I *= 0.7
    I *= 1 + 0.12 * kick_pulse(t, 0.2) + 0.5 * sting_pulse(t, 0.6)
    s = 1.0 + 0.05 * math.sin(t * 0.05)
    tx = -20 - 18 * math.sin(t * 0.031); ty = -10 - 9 * math.cos(t * 0.027)
    M = np.array([[s, 0, tx], [0, s, ty]], np.float32)
    n1 = cv2.warpAffine(NB1, M, (480, 270), borderMode=cv2.BORDER_REFLECT)
    M2 = np.array([[1.1, 0, -30 + 22 * math.cos(t * 0.022)], [0, 1.1, -15 + 12 * math.sin(t * 0.03)]], np.float32)
    n2 = cv2.warpAffine(NB2, M2, (480, 270), borderMode=cv2.BORDER_REFLECT)
    n3 = NB3
    a = np.clip((n1 - 0.38) * 1.7, 0, 1) ** 1.6
    b = np.clip((n2 - 0.45) * 1.9, 0, 1) ** 1.8
    d = np.clip((n3 - 0.55) * 2.0, 0, 1) ** 2
    img = (a[..., None] * np.array(c1, np.float32) * 0.42 + b[..., None] * np.array(c2, np.float32) * 0.36 +
           d[..., None] * np.array(lerpc(c1, WHITE, 0.3), np.float32) * 0.08) * I
    img += np.array((0.010, 0.013, 0.026), np.float32)
    bg = cv2.resize(img, (W, H), interpolation=cv2.INTER_LINEAR)
    return bg


def stars(fr, t):
    sp = 1.0 + 6.0 * sting_pulse(t, 0.45)
    zz = (ST_Z - (t * 0.012 * sp) % 1.0) % 1.0 + 0.08
    x = W / 2 + ST_X * W * 0.62 / zz * 0.35 + math.sin(t * 0.02) * 30
    y = H / 2 + ST_Y * H * 0.62 / zz * 0.35
    tw = 0.55 + 0.45 * np.sin(t * 1.3 + ST_TW)
    al = np.clip((1.1 - zz) * 0.55, 0, 0.8) * tw
    fade = cl(t / 3.0) * (0.6 if fr.t > SC['outro']['start'] else 1.0)
    fr.splat(x, y, ST_COL, al * fade * 0.85, 'G')
    big = zz < 0.32
    fr.dots(x[big], y[big], ST_COL[big], al[big] * fade * 0.5, 1, 'E')


# ---------------------------------------------------------------- chapter card / UI
def chapter_of(t):
    s = SCENES[scene_at(t)]
    return s['ch']


def ui(fr, t):
    """左上角章节标签 + 六层导航点 + 底部进度条"""
    i = scene_at(t)
    s = SCENES[i]
    ch = CHAP[s['ch']]
    # 章节首场景的前 1.6 秒，标签由大标题卡飞入；之后常驻
    first = next(x for x in SCENES if x['ch'] == s['ch'])
    k_in = eo((t - first['start'] - 1.1) / 0.6)
    if s['id'] in ('hook', 'title', 'outro') or not ch['tag']:
        k_in = 0.0
    col = C(*ch['col'])
    if k_in > 0.01:
        fr.line((60, 62), (60 + 6, 62), col, k_in, 6)
        fr.text(ch['tag'], 80, 62, 30, 'sans_bold', lerpc(col, WHITE, 0.35), k_in, anchor='l', mode='P')
        # 六层导航
        cur = s['ch'] if s['ch'].startswith('L') else None
        for j, (lk, nm) in enumerate(LAYERS):
            x = 84 + j * 34
            on = cur == lk
            lc = LAYER_COL[lk]
            fr.circle((x, 100), 7 if on else 5, lc, k_in * (1 if on else 0.45), 2)
            if on:
                fr.disc((x, 100), 4, lc, k_in)
                fr.glow((x, 100), 8, lc, k_in * 0.6)
    # 底部进度条
    if s['id'] != 'outro':
        y = H - 4
        x1 = W * t / TOTAL
        fr.rect(0, y, W, y + 3, (1, 1, 1), 0.06, 'L')
        prev = 0
        for sc in SCENES:
            if sc['sting'] and sc['start'] > 0:
                fr.rect(W * sc['start'] / TOTAL - 1, y - 3, W * sc['start'] / TOTAL + 1, y + 3, (1, 1, 1), 0.18, 'L')
        fr.rect(0, y, x1, y + 3, C(*CHAP[s['ch']]['col']), 0.65, 'L')
        fr.glow((x1, y + 1), 6, C(*CHAP[s['ch']]['col']), 0.8)


def chapter_card(fr, t):
    """章节重拍后：大号章节名，1.2 秒后收向左上角"""
    i = scene_at(t)
    s = SCENES[i]
    if not s['sting'] or s['id'] in ('title', 'outro', 'quote') or not CHAP[s['ch']]['tag']:
        return
    first = next(x for x in SCENES if x['ch'] == s['ch'])
    if first['id'] != s['id']:
        return
    lt = t - s['start']
    if lt > 1.8: return
    ch = CHAP[s['ch']]
    col = C(*ch['col'])
    tag = ch['tag']
    parts = tag.split(' · ')
    k = eo(lt / 0.35)
    mv = eio((lt - 1.0) / 0.7)
    a = k * (1 - mv)
    if a < 0.01: return
    big = parts[0]
    rest = ' · '.join(parts[1:])
    x = lerp(W / 2, 200, mv); y = lerp(H / 2 - 30, 62, mv)
    sc = lerp(1.0, 0.3, mv)
    if big.startswith('L') and len(big) == 2:
        fr.text(big, x, y - 70 * sc, int(170 * sc), 'orb', col, a, mode='E', glow=0.6, track=0.05)
        headline(fr, rest, x, y + 70 * sc, int(72 * sc), lerpc(col, WHITE, 0.25), a)
    else:
        headline(fr, tag.replace(' · ', '  ·  '), x, y, int(84 * sc), lerpc(col, WHITE, 0.25), a)
    w = 520 * k * sc
    fr.line((x - w, y + 150 * sc), (x + w, y + 150 * sc), col, a * 0.7, 2)
    fr.glow((x, y + 150 * sc), 18, col, a)


def sting_fx(fr, t):
    """章节重拍：闪白、色差、冲击波、镜头冲击"""
    for st in STINGS:
        dt = t - st
        if -0.02 <= dt < 1.2:
            s = SCENES[scene_at(st + 0.01)]
            big = s['id'] in ('title', 'combo', 'outro', 'rules')
            col = C(*CHAP[s['ch']]['col'])
            fr.flash = max(fr.flash, (0.55 if big else 0.32) * math.exp(-max(dt, 0) / 0.09))
            fr.ca = max(fr.ca, (9 if big else 5) * math.exp(-max(dt, 0) / 0.15))
            fr.zoom *= 1 + (0.05 if big else 0.025) * math.exp(-max(dt, 0) / 0.22)
            shockwave(fr, (W / 2, H / 2), st, col, t, speed=2600, life=1.0, th=4, a=0.9)
            shockwave(fr, (W / 2, H / 2), st + 0.08, lerpc(col, WHITE, 0.5), t, speed=1800, life=0.8, th=2, a=0.6)


def subtitles(fr, t):
    if SCENES[scene_at(t)]['id'] in ('quote', 'outro'):
        return
    for s in TL['subs']:
        if s['start'] - 0.05 <= t < s['end']:
            a = eo((t - s['start'] + 0.05) / 0.12) * (1 - eio((t - s['end'] + 0.12) / 0.12))
            txt = s['text']
            size = 40
            tw = text_width(txt, 'sans_med', size)
            # 柔和暗底
            fr.post_over.append((_sub_bg(int(tw + 80)), int(W / 2 - (tw + 80) / 2), 1000 - 36, np.zeros(3, np.float32), 0.55 * a))
            fr.text(txt, W / 2, 1000, size, 'sans_med', (0.97, 0.97, 0.97), a, mode='P', track=0.02)
            break


_SUBBG = {}


def _sub_bg(w):
    w = int(round(w / 20) * 20)
    if w not in _SUBBG:
        m = np.zeros((72, w), np.float32)
        cv2.rectangle(m, (36, 12), (w - 36, 60), 1.0, -1)
        _SUBBG[w] = cv2.GaussianBlur(m, (0, 0), 14)
    return _SUBBG[w]


# ---------------------------------------------------------------- frame
def render(t, stage_only=False, vertical=False):
    fr = Frame(t)
    fr.vertical = vertical
    i = scene_at(t)
    s = SCENES[i]
    bg = background(t)
    stars(fr, t)
    # 场景（非重拍切换做交叉淡化）
    nxt = SCENES[i + 1] if i + 1 < len(SCENES) else None
    prv = SCENES[i - 1] if i > 0 else None
    k_in = 1.0
    if prv is not None and not s['sting']:
        h = HANDOFF[i - 1]
        k_in = eio((t - (h - 0.45)) / 0.45)
        if t < h and prv['id'] in DRAW:
            fr.k = 1.0
            DRAW[prv['id']](fr, Ctx(prv, t, h))
    fr.k = k_in
    if s['id'] in DRAW:
        DRAW[s['id']](fr, Ctx(s, t, HANDOFF[i]))
    fr.k = 1.0
    if not vertical:
        chapter_card(fr, t)
    sting_fx(fr, t)
    out = compose(fr, bg)
    if stage_only:
        apply_over(out, fr.post_over)
        return (out, fr.callouts) if vertical else out
    # 镜头之外的层：UI、字幕、角标
    fr2 = Frame(t)
    ui(fr2, t)
    subtitles(fr2, t)
    out += fr2.L
    E2 = fr2.E + fr2.U.astype(np.float32) / 255
    out += E2 + bloom(E2 + fr2.B, 0.6) * 0.6
    apply_over(out, fr2.post_over)
    apply_over(out, fr.post_over)
    HUD.draw(out, t)
    return to_u8(out, int(t * FPS))


def cmd_frame(t, path):
    img = render(float(t))
    cv2.imwrite(path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))


def cmd_sheet(path, ts, cols=3, scale=0.5):
    imgs = []
    for t in ts:
        im = render(float(t))
        im = cv2.resize(im, (int(W * scale), int(H * scale)), interpolation=cv2.INTER_AREA)
        cv2.putText(im, f'{float(t):.2f}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 0), 2)
        imgs.append(im)
    while len(imgs) % cols: imgs.append(np.zeros_like(imgs[0]))
    rows = [np.hstack(imgs[i:i + cols]) for i in range(0, len(imgs), cols)]
    cv2.imwrite(path, cv2.cvtColor(np.vstack(rows), cv2.COLOR_RGB2BGR))


def cmd_chunk(f0, f1, path, crf=14):
    f1 = min(f1, NFR)
    p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', str(crf),
                          '-pix_fmt', 'yuv420p', '-tune', 'animation', path], stdin=subprocess.PIPE)
    import time
    t0 = time.time()
    for f in range(f0, f1):
        p.stdin.write(render(f / FPS).tobytes())
        if (f - f0) % 300 == 0:
            el = time.time() - t0
            print(f'[{path}] {f - f0}/{f1 - f0}  {el / max(f - f0, 1):.3f}s/f', flush=True)
    p.stdin.close(); p.wait()


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'frame': cmd_frame(sys.argv[2], sys.argv[3])
    elif c == 'sheet': cmd_sheet(sys.argv[2], sys.argv[3:])
    elif c == 'chunk': cmd_chunk(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
