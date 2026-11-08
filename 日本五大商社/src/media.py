"""真实影像素材：照片（Ken Burns 推拉）与视频片段（逐帧解码），全部来自 Wikimedia Commons 的公有领域 / CC 授权素材，
作者与授权写在 assets/media/credits.json，画面上以小字署名，片尾与 SOURCES.md 汇总。

两种构图：
  full  —— 满幅（9:16 裁切，焦点可调），上下压暗，给字幕和图表留出可读性；
  frame —— 横幅照片放在画面中部的“窗口”里，背后是同一张照片的虚化放大版（竖屏纪录片常用的处理）。
"""
import os, json, math
import numpy as np, cv2
from engine import *          # noqa

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MDIR = os.path.join(ROOT, 'assets', 'media')
CLIPDIR = os.path.join(ROOT, 'work_clips')
CREDITS = json.load(open(os.path.join(MDIR, 'credits.json'))) if os.path.exists(os.path.join(MDIR, 'credits.json')) else {}
_img = {}


def have(name):
    return os.path.exists(os.path.join(MDIR, name + '.jpg')) or os.path.exists(os.path.join(CLIPDIR, name + '.mp4'))


def img(name):
    if name not in _img:
        p = os.path.join(MDIR, name + '.jpg')
        im = cv2.imread(p)
        _img[name] = None if im is None else (im[..., ::-1].astype(np.float32) / 255) ** 1.0
    return _img[name]


# ------------------------------------------------------------------ 视频：预先转码好的片段（work_clips/<name>.mp4，30fps，见 prep_media.py）
class _Vid:
    def __init__(self, path):
        self.cap = cv2.VideoCapture(path); self.pos = -1; self.frame = None
        self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)); self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30

    def get(self, k):
        k = int(max(0, min(k, self.n - 1)))
        if k == self.pos and self.frame is not None: return self.frame
        if not (self.pos < k <= self.pos + 90):
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, k); self.pos = k - 1
        while self.pos < k:
            ok, fr = self.cap.read()
            if not ok: break
            self.pos += 1; self.frame = fr
        return self.frame


_vid = {}
def vframe(name, sec):
    if name not in _vid:
        p = os.path.join(CLIPDIR, name + '.mp4')
        _vid[name] = _Vid(p) if os.path.exists(p) else None
    v = _vid[name]
    if v is None: return None
    fr = v.get(round(sec * v.fps))
    if fr is None: return None
    if name in CROP:                                  # 新闻素材：裁掉底部滚动条与右上角台标
        h, w = fr.shape[:2]; x0, y0, x1, y1 = CROP[name]
        fr = fr[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
    if name.startswith('x_bwb'):                      # 纪录片素材里烧录的时间码（右上）与水印（下方居中）：局部重度模糊抹去
        fr = fr.copy(); h, w = fr.shape[:2]
        for x0, y0, x1, y1 in ((0.74, 0.0, 1.0, 0.14), (0.22, 0.84, 0.78, 0.97)):
            X0, Y0, X1, Y1 = int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)
            fr[Y0:Y1, X0:X1] = cv2.GaussianBlur(fr[Y0:Y1, X0:X1], (0, 0), 25)
    return fr[..., ::-1].astype(np.float32) / 255


CROP = {k: (0.04, 0.07, 0.96, 0.925) for k in ('j_tower', 'j_shinkansen', 'j_commuters', 'j_taxi')}
CROP.update({k: (0.08, 0.08, 1.0, 1.0) for k in ('j_lng_ship', 'j_lng_plant')})


IA = json.load(open(os.path.join(MDIR, 'ia_clips.json'))) if os.path.exists(os.path.join(MDIR, 'ia_clips.json')) else {}


def credit_text(name):
    if name in IA: return '影像：' + IA[name]['source']
    c = CREDITS.get(name.split('#')[0])
    if not c: return ''
    if c.get('via'): return '图片：' + c['via']                 # 新闻图片：注明刊发媒体
    art = (c.get('artist') or '').replace('\n', ' ').strip()
    if art.startswith('http') or 'flickr.com' in art: art = (c.get('credit') or '').strip() if not (c.get('credit') or '').startswith('http') else ''
    if art.lower() in ('own work', '') or art.startswith('http'): art = ''
    if len(art) > 34: art = art[:32] + '…'
    lic = c.get('license') or ''
    return f'{art} · {lic} · Wikimedia Commons' if art else f'{lic} · Wikimedia Commons'


def grade(im, warm=0.0, sat=1.0, lift=0.0, gain=1.0):
    """现代、通透的统一调色：保留原色彩（不做怀旧的暖黄或去饱和），略提饱和与对比，让高清素材更鲜明"""
    g = im @ np.array([0.3, 0.59, 0.11], np.float32)
    out = g[..., None] + (im - g[..., None]) * 1.08
    out = (out - 0.5) * 1.06 + 0.5
    return np.clip(out * gain + lift, 0, 1)


def _crop(src, w, h, z, fx, fy, px=0.0, py=0.0):
    ih, iw = src.shape[:2]
    s = max(w / iw, h / ih) * z
    cw, chh = w / s, h / s
    ox = cl(fx * iw - cw / 2 + px * iw, 0, max(iw - cw, 0)); oy = cl(fy * ih - chh / 2 + py * ih, 0, max(ih - chh, 0))
    M = np.array([[s, 0, -ox * s], [0, s, -oy * s]], np.float32)
    return cv2.warpAffine(src, M, (int(w), int(h)), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


_grad = {}
def _shade(h, top=0.45, bottom=0.62, mid=0.0):
    k = (h, top, bottom, mid)
    if k not in _grad:
        y = np.linspace(0, 1, h, dtype=np.float32)
        g = 1 - top * np.clip(1 - y / 0.28, 0, 1) ** 1.6 - bottom * np.clip((y - 0.58) / 0.42, 0, 1) ** 1.3 - mid
        _grad[k] = np.clip(g, 0.05, 1)[:, None, None]
    return _grad[k]


# 素材暂缺时的后备（同一主题、已下载的照片），保证任何时候都能完整渲染
FALLBACK = {'v_omaha_drone': 'omaha_river', 'v_dundee_drone': 'omaha_2026', 'v_apple_park': 'apple_park_aerial',
            'iphone11': 'iphone7', 'iphone11_cam': 'iphone7', 'flip_keypad': 'flip_moto', 'buffett_osu': 'buffett_osu2'}


def resolve(name, depth=0):
    if os.path.exists(os.path.join(CLIPDIR, name + '.mp4')) or os.path.exists(os.path.join(MDIR, name + '.jpg')) or depth > 3:
        return name
    return resolve(FALLBACK.get(name, name), depth + 1) if name in FALLBACK else name


# 每个视频片段里真正可用的时段（之后会切到别的画面）；镜头时长超出时自动放慢，保证不越界、不定格
USABLE = {'x_bwbm_munger': (0, 20), 'x_bwbm_munger2': (0, 9), 'j_cine_konbini': (0, 7), 'j_cine_city': (0, 3), 'j_cine_osaka': (0, 7),
          'j_cine_miyajima': (0, 7), 'j_cine_skyline': (0, 7), 'j_night_crossing': (0, 10), 'j_night_towers': (0, 10), 'j_night_street': (0, 10),
          'j_night_711': (0, 8), 'j_tower': (1.8, 3.5), 'j_shinkansen': (0, 4), 'j_commuters': (0, 5.5), 'j_taxi': (0, 2.5), 'j_market': (0, 10),
          'j_evening': (0, 10),
          'j_bay': (0, 14), 'j_aerial_river': (0, 12), 'j_aerial_city': (0, 12), 'j_crossing': (0, 10), 'j_street': (0, 10),
          'j_lawson': (0, 6.5), 'j_lng_ship': (0, 4.5), 'j_lng_plant': (0, 3.0), 'v_tokyo': (5, 132),
          'x_bwb_arena': (0, 3), 'x_bwb_cherrycoke': (0, 4.5), 'x_bwb_cokestore': (0, 3.2), 'x_bwb_desk': (0, 10.5),
          'x_bwb_meeting': (17, 30), 'x_bwb_office': (2, 10.5), 'x_bwb_walk': (0, 4), 'x_bwbi_a': (0, 20), 'x_bwbi_b': (0, 20),
          'x_bwbi_c': (0, 20), 'x_cook_roof': (0, 9.3), 'x_i6s_store': (0, 8), 'x_i6s_unbox': (7, 12.5), 'x_iphone_hand': (0, 3.2),
          'x_iphones_wall': (1.5, 10), 'x_jobs07_stage': (0, 7.5), 'x_jobs07_wave': (0, 8.5), 'x_jobs_council': (0, 2.2),
          'x_park_green': (0, 10), 'x_park_ring1': (2.5, 12.5), 'x_park_ring2': (3, 16), 'x_park_ring3': (0, 3), 'x_park_ring4': (0, 6.3),
          'x_park_theater': (0, 5.2), 'x_park_top': (8.3, 12)}


def fit_speed(name, src_t0, speed, dur):
    if name in USABLE:
        a, b = USABLE[name]; src_t0 = max(src_t0, a)
        speed = min(speed, max(b - src_t0 - 0.05, 0.1) / max(dur, 0.1))
    return src_t0, speed


def source_frame(name, t, t0, src_t0=0.0, speed=1.0):
    """name 为照片或视频；视频按 (t - t0) * speed + src_t0 取帧"""
    if os.path.exists(os.path.join(CLIPDIR, name + '.mp4')):
        return vframe(name, src_t0 + max(t - t0, 0) * speed), True
    return img(name), False


# 有人物的横版镜头：保留完整 16:9 画面放在中部（背后虚化铺底），不裁成竖屏满幅——否则人脸会被放大到占满画面
WIN_CY = 560          # 统一画窗：上方 1000×562（y 279–841），下方留给动画解读与字幕
PEOPLE = ('x_bwb', 'x_jobs', 'x_cook', 'x_i6s_store', 'x_i6s_unbox', 'x_iphones_wall', 'j_')


def full(cv, name, t, t0, t1, z0=1.04, z1=1.14, focus=(0.5, 0.5), pan=(0, 0, 0, 0), a=1.0, fi=0.6, fo=0.6,
         shade=(0.45, 0.62), dark=0.0, warm=0.0, sat=1.0, src_t0=0.0, speed=1.0, credit=True, cap=None, bw=False, sweep=True):
    """满幅照片/视频，带缓慢推拉；shade=(顶部压暗, 底部压暗)；dark 额外整体压暗（叠图表时用）"""
    if True:                                     # v5：所有影像一律放进上方画窗（不再整屏铺满或虚化铺底）
        fc = (0.5, 0.5) if name.startswith(PEOPLE) else focus
        return frame(cv, name, t, t0, t1, cy=WIN_CY, w=1000, h=562, z0=1.0, z1=1.05, focus=fc, a=a, fi=fi, fo=fo,
                     src_t0=src_t0, speed=speed, credit=credit, cap=cap)
    al = env(t, t0, t1, fi, fo) * a
    if al <= 0.004: return 0.0
    r = resolve(name)
    if r != name: name, cap = r, None
    src_t0, speed = fit_speed(name, src_t0, speed, t1 - t0)
    src, isv = source_frame(name, t, t0, src_t0, speed)
    if src is None: return 0.0
    p = eio((t - t0) / max(t1 - t0, 1e-3))
    z = lerp(z0, z1, p)
    fr = _crop(src, W, H, z, focus[0], focus[1], lerp(pan[0], pan[2], p), lerp(pan[1], pan[3], p))
    if bw: g = fr @ np.array([0.3, 0.59, 0.11], np.float32); fr = np.repeat(g[..., None], 3, 2)
    fr = grade(fr, warm, sat) * _shade(H, shade[0], shade[1], dark * 0.75)
    cv.over(fr, np.full((H, W), al, np.float32), 0, 0)
    if sweep:
        import fx
        fx.sweep(cv, t, t0 - 0.05, 0.75, a=0.45 * a)
    if credit: credit_line(cv, name, al, cap)
    return al


def frame(cv, name, t, t0, t1, cy=820, w=1000, h=680, z0=1.02, z1=1.10, focus=(0.5, 0.5), pan=(0, 0, 0, 0), a=1.0,
          fi=0.6, fo=0.6, warm=0.25, sat=0.85, src_t0=0.0, speed=1.0, bg=False, credit=True, cap=None, border=True, bw=False):
    """窗口构图：清晰的画面放在中部，背后同一画面虚化放大并压暗"""
    al = env(t, t0, t1, fi, fo) * a
    if al <= 0.004: return 0.0
    r = resolve(name)
    if r != name: name, cap = r, None
    src_t0, speed = fit_speed(name, src_t0, speed, t1 - t0)
    src, isv = source_frame(name, t, t0, src_t0, speed)
    if src is None: return 0.0
    p = eio((t - t0) / max(t1 - t0, 1e-3))
    if bg:
        small = _crop(src, W // 8, H // 8, 1.15, focus[0], focus[1])
        b = cv2.resize(cv2.GaussianBlur(small, (0, 0), 3.0), (W, H), interpolation=cv2.INTER_LINEAR)
        b = grade(b, warm, 1.0) * 0.38
        cv.over(b, np.full((H, W), al, np.float32), 0, 0)
    z = lerp(z0, z1, p)
    fr = _crop(src, w, h, z, focus[0], focus[1], lerp(pan[0], pan[2], p), lerp(pan[1], pan[3], p))
    if bw: g = fr @ np.array([0.3, 0.59, 0.11], np.float32); fr = np.repeat(g[..., None], 3, 2)
    fr = grade(fr, warm, sat)
    x0, y0 = W / 2 - w / 2, cy - h / 2
    # 柔和投影
    sh = np.zeros((int(h) + 80, int(w) + 80), np.float32); sh[40:-40, 40:-40] = 1
    sh = cv2.GaussianBlur(sh, (0, 0), 18) * 0.6 * al
    cv.img_mul(1 - sh, x0 - 40, y0 - 28)
    cv.over(fr, np.full((int(h), int(w)), al, np.float32), x0, y0)
    if border: cv.rrect(x0 - 1, y0 - 1, x0 + w + 1, y0 + h + 1, 2, GOLD_D, al * 0.5, fill=False, th=2)
    if credit:
        txt = (cap + ' · ' if cap else '') + credit_text(name)
        cv.text(txt, W / 2, y0 + h + 30, 19, 'sans_light', col=(0.62, 0.60, 0.58), a=al * 0.9)
    return al


def credit_line(cv, name, a, cap=None, y=1700):
    """满幅画面的署名：右下角极小字（避开字幕区，字幕在 1530 附近）"""
    txt = (cap + ' · ' if cap else '') + credit_text(name)
    if txt: cv.text(txt, W - 40, y + 40, 18, 'sans_light', col=(0.66, 0.64, 0.62), a=a * 0.85, anchor='r', shadow=0.8)


def split2(cv, names, t, t0, t1, caps=(None, None), a=1.0, cy=(560, 1130), h=520, **kw):
    """上下两幅对照"""
    for n, c, y in zip(names, caps, cy):
        frame(cv, n, t, t0, t1, cy=y, w=1000, h=h, bg=False, cap=c, a=a, **kw)
