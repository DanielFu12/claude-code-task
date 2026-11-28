"""《全押美国——巴菲特与 BNSF》渲染入口：一次渲染同时输出竖版（1080×1920）和横版（1920×1080）。

python3 src/film.py WORK frame 12.5s,40s out_#.jpg   # 渲染单帧（调试；# 替换为时间）
python3 src/film.py WORK chunk 0 900 seg0.mp4         # 渲染帧区间（同时写 seg0_h.mp4 横版）
python3 src/film.py WORK hframe 12.5s out_#.jpg        # 横版单帧
"""
import sys, os, subprocess, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *          # noqa
from script import CHAPTERS
# ------------------------------------------------------------------ 章节镜头（见 film_ch*.py）
from sot import sot_layer
from gg import shot_hook, shot_title, shot_ch1, shot_ch2, shot_ch3, shot_ch4, shot_ch5, shot_ch6, shot_ch7   # 第八期全部镜头


import media as MEDIA
_LAST = [-10]
_ZONE = None


def _zone():
    """氛围背景的明暗：上方画窗一带亮一些，中下部（解读图表、字幕）压得更暗，四角再收一点"""
    global _ZONE
    if _ZONE is None:
        y = np.linspace(0, 1, H)[:, None]; x = np.linspace(-1, 1, W)[None, :]
        v = np.interp(y, [0, 0.10, 0.42, 0.50, 0.78, 1.0], [0.16, 0.34, 0.34, 0.20, 0.17, 0.12])
        _ZONE = (v * (1 - 0.35 * x ** 2)).astype(np.float32)[..., None]
    return _ZONE


def underlay(cv, items):
    for small, al in items:
        b = cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR)
        g = b @ np.array([0.3, 0.59, 0.11], np.float32)
        b = (b * 0.7 + g[..., None] * 0.3) * np.array([1.04, 0.98, 0.90], np.float32) * _zone()
        cv.over(b, np.full((H, W), min(al, 1.0) * 0.92, np.float32), 0, 0)


def render(i, warm=False):
    if not warm and _LAST[0] != i - 1 and i > 0: render(i - 1, warm=True)     # 块首帧：先空跑上一帧，拿到它登记的背景
    _LAST[0] = i
    t = i / FPS
    bd = list(MEDIA.BD); MEDIA.BD.clear()
    cv = Canvas(t, background(t))
    underlay(cv, bd)
    if t < CH['title'][0] + 0.1: shot_hook(cv, t)
    if CH['title'][0] - 0.1 <= t < CH['ch1'][0] + 0.8: shot_title(cv, t)
    if CH['ch1'][0] <= t < CH['ch2'][0] + 0.8: shot_ch1(cv, t)
    if CH['ch2'][0] <= t < CH['ch3'][0] + 0.8: shot_ch2(cv, t)
    if CH['ch3'][0] <= t < CH['ch4'][0] + 0.8: shot_ch3(cv, t)
    if CH['ch4'][0] <= t < CH['ch5'][0] + 0.8: shot_ch4(cv, t)
    if CH['ch5'][0] <= t < CH['ch6'][0] + 0.8: shot_ch5(cv, t)
    if CH['ch6'][0] <= t < CH['ch7'][0] + 0.8: shot_ch6(cv, t)
    if CH['ch7'][0] <= t < CH['end'][0] + 0.8: shot_ch7(cv, t)
    if t >= CH['end'][0] - 0.6: shot_end(cv, t)
    if CH['ch1'][0] <= t < CH['end'][0]:
        import fx
        fx.dust(cv, t, 0.35, seed=9)
    sot_layer(cv, t)                      # 巴菲特原声段落：整屏转入采访现场
    # 镜头呼吸：极缓的推拉与漂移，让静态排版也有摄影机的生命感（字幕/角标不受影响）
    z = 1.012 + 0.012 * math.sin(t * 0.37)
    dx, dy = 6 * math.sin(t * 0.23), 8 * math.sin(t * 0.29 + 1)
    M = np.array([[z, 0, (1 - z) * W / 2 + dx], [0, z, (1 - z) * H / 2 + dy]], np.float32)
    cv.img = cv2.warpAffine(cv.img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    cv.glow = cv2.warpAffine(cv.glow, M, (W, H), flags=cv2.INTER_LINEAR)
    if cv.U.any(): cv.U = cv2.warpAffine(cv.U, M, (W, H), flags=cv2.INTER_LINEAR)
    interlude_dim(cv, t)                  # 幕间：要点卡 → 章节卡连续压暗（v3）
    takeaway(cv, t)
    chapter_card(cv, t)
    fade = 1.0
    if t > TOTAL - 1.8: fade = eio((TOTAL - t) / 1.8)          # 整体淡出（含角标）
    if t < 0.4: fade = eio(t / 0.4)
    if warm: return None
    snap = _Snap(cv) if WANT_H else None                       # 横版用的内容层（不含导航、字幕、角标）
    nav(cv, t)
    follow_pill(cv, t)
    subtitles(cv, t)
    vert = finish(cv, i, bloom_k=1.0, fade=fade)
    if not WANT_H: return vert
    return vert, landscape(snap, t, i, fade)


# ------------------------------------------------------------------ 横版（1920×1080）
# 不是把竖版裁切或加黑边：同一帧的内容层按区域重新排版——
#   · 常规镜头：上方画窗（影像 + 署名）放左边，下方的解读（图表、引语卡、出处）放右边；
#   · 原声段落：照片 + 声纹放左边，英文原话与中文翻译放右边；
#   · 片名、章节卡、片尾 logo：中央大块居中；
#   · 字幕、章节导航、角标按横版重新排（字幕在底部一行，导航在左上，角标在右上）。
WANT_H = os.environ.get('NO_H') is None
HW, HH = 1920, 1080
_HUD_H = None


class _Snap:
    def __init__(self, cv):
        self.t = cv.t; self.img = cv.img.copy(); self.glow = cv.glow.copy(); self.U = cv.U.copy(); self.post = []


def _cards():
    sp = [(CH['title'][0] - 0.35, CH['ch1'][0] + 2.25)]
    for cid, title, en in CHAPTERS:
        if title is None or cid == 'ch1': continue
        sp.append((CH[cid][0] - 0.25, CH[cid][0] + 2.25))
    sp.append((CH['end'][0] - 0.3, TOTAL + 1))
    return sp


CARDS = _cards()


def _card_w(t):
    w = 0.0
    for a, b in CARDS:
        w = max(w, env(t, a, b, 0.45, 0.45))
    return w


def _feather(h, w, f=40):
    y = np.minimum(np.arange(h) + 1, np.arange(h)[::-1] + 1)[:, None] / f
    x = np.minimum(np.arange(w) + 1, np.arange(w)[::-1] + 1)[None, :] / f
    return np.clip(np.minimum(y, x), 0, 1).astype(np.float32)


def _paste(dst, src, x0, y0, a):
    h, w = src.shape[:2]
    m = (_feather(h, w) * a)[..., None]
    reg = dst[y0:y0 + h, x0:x0 + w]
    reg *= 1 - m; reg += src * m


def _block(v, y0, y1, scale, x0=0, x1=None):
    blk = v[y0:y1, x0:x1 or W]
    h, w = blk.shape[:2]
    return cv2.resize(blk, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)


def _overlay_layer(t, i):
    """字幕与导航：画在一张黑底竖版画布上，再按亮度当透明度取出来（文字是亮色，衬底在黑底上不可见）"""
    oc = Canvas(t, None)
    subtitles(oc, t); nav(oc, t)
    img = np.clip(oc.img, 0, 1)
    return img


def landscape(snap, t, i, fade):
    global _HUD_H
    v = np.clip(np.nan_to_num(finish(snap, i, bloom_k=1.0, fade=1.0, hud_alpha=0.0).astype(np.float32) / 255), 0, 1)
    out = np.zeros((HH, HW, 3), np.float32)
    # 氛围底：同一帧中部放大、虚化、压暗，铺满横版
    small = cv2.resize(v[300:1500], (96, 54), interpolation=cv2.INTER_AREA)
    out[:] = cv2.resize(cv2.GaussianBlur(small, (0, 0), 2.0), (HW, HH), interpolation=cv2.INTER_LINEAR) * 0.42
    wc = _card_w(t)
    a_split = cl(1 - 2 * wc); a_card = cl(2 * wc - 1)          # 两种排版之间先淡出、再淡入（不叠在一起出现重影）
    if a_split > 0.001:                                      # 常规：左画窗 + 右解读
        a = a_split
        L = _block(v, 246, 870, 0.955)                      # 画窗 + 署名（竖版 y 246–870，整宽，署名不截断）
        R = _block(v, 852, 1500, 0.86, 40, 1040)            # 解读 + 出处（竖版 y 852–1500、x 40–1040）
        _paste(out, L, 20, 176, a)
        _paste(out, R, HW - R.shape[1] - 20, 176 + (L.shape[0] - R.shape[0]) // 2, a)
    if a_card > 0.001:                                      # 片名、章节卡、片尾：中央大块
        C_ = _block(v, 400, 1500, 0.88)
        _paste(out, C_, (HW - C_.shape[1]) // 2, 70, a_card)
    # 字幕（底部）与导航（左上）
    ol = _overlay_layer(t, i)
    sub = ol[1450:1720]
    alpha = np.clip(sub.max(2) * 1.4, 0, 1)
    ys, xs = np.nonzero(alpha > 0.02)
    if len(xs) > 0:
        x0s, x1s = max(xs.min() - 40, 0), min(xs.max() + 40, W); y0s, y1s = max(ys.min() - 20, 0), min(ys.max() + 20, sub.shape[0])
        sw = x1s - x0s; sh_ = y1s - y0s
        X0 = (HW - sw) // 2; Y0 = 1040 - sh_
        band = np.clip(alpha[y0s:y1s, x0s:x1s], 0, 1)
        bk = cv2.GaussianBlur(cv2.dilate(band, np.ones((15, 15), np.uint8)), (0, 0), 10) * 0.55
        reg = out[Y0:Y0 + sh_, X0:X0 + sw]
        reg *= (1 - bk)[..., None]
        reg *= (1 - band)[..., None]; reg += sub[y0s:y1s, x0s:x1s] * band[..., None] / np.maximum(band[..., None], 1e-3) * band[..., None]
    navl = ol[150:250]
    na = np.clip(navl.max(2) * 1.6, 0, 1)
    if na.max() > 0.02:
        nv = cv2.resize(navl, (int(W * 0.95), int(100 * 0.95)), interpolation=cv2.INTER_AREA)
        nal = cv2.resize(na, (nv.shape[1], nv.shape[0]), interpolation=cv2.INTER_AREA)
        reg = out[38:38 + nv.shape[0], 30:30 + nv.shape[1]]
        reg *= (1 - nal)[..., None]; reg += nv * nal[..., None] / np.maximum(nal[..., None], 1e-3) * nal[..., None]
    out *= fade
    if _HUD_H is None:
        from brand import Hud
        _HUD_H = Hud(scale=1.0, frame_w=HW)
    _HUD_H.draw(out, t, alpha=fade)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


if __name__ == '__main__':
    mode = sys.argv[2]
    if mode in ('frame', 'hframe'):
        for k in sys.argv[3].split(','):
            fi = int(round(float(k.rstrip('s')) * FPS)) if k.endswith('s') else int(k)
            out = render(fi)
            if isinstance(out, tuple): out = out[0] if mode == 'frame' else out[1]
            path = sys.argv[4].replace('#', k)
            cv2.imwrite(path, out[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 92])
    elif mode == 'chunk':
        a, b, path = int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
        b = min(b, NFRAMES)
        def enc(p, w, h):
            return subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                                     '-s', f'{w}x{h}', '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'fast',
                                     '-crf', '17', '-pix_fmt', 'yuv420p', '-threads', '1', p], stdin=subprocess.PIPE)
        pv = enc(path, W, H)
        ph = enc(path[:-4] + '_h.mp4', HW, HH) if WANT_H else None
        for i in range(a, b):
            out = render(i)
            if isinstance(out, tuple):
                pv.stdin.write(out[0].tobytes()); ph.stdin.write(out[1].tobytes())
            else: pv.stdin.write(out.tobytes())
            if (i - a) % 150 == 0: print(path, i, flush=True)
        pv.stdin.close(); pv.wait()
        if ph: ph.stdin.close(); ph.wait()
