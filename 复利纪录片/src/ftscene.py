"""原始影像段落：画中窗 + 中英字幕 + 人名条 + 出处。

渲染分两层：
  ft_bg(F, t)      HDR 阶段：用当前影像的模糊放大版铺底（压暗），让窗口与背景同色调
  ft_overlay(F, t) 显示空间（post 之后）：影像窗口本身、人名条、字幕——保证原始画面不被色调映射改色
"""
import os, math
import numpy as np, cv2
from engine import font, W, H, FPS, GOLD, GOLD_HI, GREY, WHITE, RED, smooth, clamp01, ease_out, blur
from common import put_text, TextBlock, draw_block
from clips import CLIPS, ROOT

CLIP_DIR = os.path.join(ROOT, 'footage', 'clips')
WIN_CY = 740                       # 窗口中心
SUB_ZH_Y = 1372                    # 中文字幕中心
FADE_IN, FADE_OUT = 0.35, 0.40     # 窗口在原声前后多停留的时间


def clip_len(cid):
    c = CLIPS[cid]
    return c['b'] - c['a']


class Reader:
    """顺序读帧（分块渲染时帧号连续），带单帧缓存"""
    def __init__(self, cid):
        self.cap = cv2.VideoCapture(os.path.join(CLIP_DIR, f'{cid}.mp4'))
        self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.pos = -1; self.cur = None

    def get(self, i):
        i = min(max(i, 0), self.n - 1)
        if i == self.pos: return self.cur
        if i != self.pos + 1:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, f = self.cap.read()
        if not ok: return self.cur
        self.cur = cv2.cvtColor(f, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
        self.pos = i
        return self.cur


_READERS = {}
def frame_of(cid, u):
    """片段内时间 u（秒）对应的画面（显示空间 0..1）"""
    if cid not in _READERS: _READERS[cid] = Reader(cid)
    return _READERS[cid].get(int(round(u * FPS)))


def inv_tonemap(d):
    """post() 中色调映射的反函数：让铺底颜色经过 post 后与原画面一致"""
    d = np.clip(d, 0, 0.96)
    a = 2.43 * d - 2.51; b = 0.59 * d - 0.03; c = 0.14 * d
    return (-b - np.sqrt(b * b - 4 * a * c)) / (2 * a)


# ------------------------------------------------------------------ 时间轴上的片段
SEQ = []          # [(cid, t0)]，由 timeline 填充


def active(t):
    """当前时刻的片段：(cid, u=片段内时间, a=窗口不透明度, s=入场缩放)"""
    for cid, t0 in SEQ:
        L = clip_len(cid)
        if t0 - FADE_IN <= t <= t0 + L + FADE_OUT:
            a = min(smooth((t - t0 + FADE_IN) / FADE_IN), smooth((t0 + L + FADE_OUT - t) / FADE_OUT))
            s = 0.955 + 0.045 * ease_out(clamp01((t - t0 + FADE_IN) / 0.6))
            return cid, min(max(t - t0, 0), L - 1 / FPS), a, s
    return None


def ft_bg(F, t):
    """HDR：用影像铺底（模糊、压暗、偏冷）"""
    ac = active(t)
    if not ac: return
    cid, u, a, _ = ac
    fr = frame_of(cid, u)
    sm = cv2.resize(fr, (54, int(54 * fr.shape[0] / fr.shape[1])), interpolation=cv2.INTER_AREA)
    sm = inv_tonemap(cv2.GaussianBlur(sm, (0, 0), 2.0)).astype(np.float32)
    big = cv2.resize(sm, (int(H * fr.shape[1] / fr.shape[0]), H), interpolation=cv2.INTER_CUBIC)
    x0 = (big.shape[1] - W) // 2
    lin = big[:, x0:x0 + W] * 0.22
    lin = lin * np.array([0.85, 0.92, 1.1], np.float32)
    F[:] = F * (1 - 0.85 * a) + lin * 0.85 * a


def _round_mask(w, h, r):
    m = np.zeros((h, w), np.float32)
    cv2.rectangle(m, (r, 0), (w - r, h), 1, -1); cv2.rectangle(m, (0, r), (w, h - r), 1, -1)
    for cx, cy in ((r, r), (w - r, r), (r, h - r), (w - r, h - r)):
        cv2.circle(m, (cx, cy), r, 1, -1, cv2.LINE_AA)
    return cv2.GaussianBlur(m, (0, 0), 0.7)


_MASKS = {}
def window_rect(cid):
    c = cv2.VideoCapture(os.path.join(CLIP_DIR, f'{cid}.mp4'))
    w, h = int(c.get(cv2.CAP_PROP_FRAME_WIDTH)), int(c.get(cv2.CAP_PROP_FRAME_HEIGHT))
    return int(W / 2 - w / 2), int(WIN_CY - h / 2), w, h


_RECTS = {}
def rect_of(cid):
    if cid not in _RECTS: _RECTS[cid] = window_rect(cid)
    return _RECTS[cid]


def cue_at(cid, u):
    c = CLIPS[cid]
    ts = c['a'] + u
    for a, b, en, zh in c['cues']:
        if a - 0.08 <= ts <= b + 0.3:
            al = min(smooth((ts - a + 0.08) / 0.15), smooth((b + 0.3 - ts) / 0.2))
            return en, zh, al
    return None


def balance(text, name, size, maxw):
    """中文字幕两行时，在靠近中间的标点处断行（避免「让知/识」这样的断法）"""
    f = font(name, size)
    if f.getlength(text) <= maxw: return text
    best = None
    for i, ch in enumerate(text[:-1]):
        if ch in '，、：；——':
            a, b = text[:i + 1], text[i + 1:]
            if f.getlength(a) <= maxw and f.getlength(b) <= maxw:
                d = abs(f.getlength(a) - f.getlength(b))
                if best is None or d < best[0]: best = (d, i + 1)
    k = best[1] if best else len(text) // 2
    return text[:k] + '\n' + text[k:].lstrip('——')


SUB_COL = np.array([0.98, 0.97, 0.94], np.float32)
EN_COL = np.array([0.72, 0.74, 0.78], np.float32)


def ft_overlay(F, t):
    """显示空间：窗口 + 原声标记 + 人名条 + 字幕"""
    ac = active(t)
    if not ac: return
    cid, u, a, s = ac
    c = CLIPS[cid]; info = c['info']
    x0, y0, w, h = rect_of(cid)
    fr = frame_of(cid, u)
    # 入场缩放
    if s < 0.999:
        sw, sh = int(w * s), int(h * s)
        fr = cv2.resize(fr, (sw, sh), interpolation=cv2.INTER_AREA)
        x0, y0, w, h = int(W / 2 - sw / 2), int(WIN_CY - sh / 2), sw, sh
    key = (w, h)
    if key not in _MASKS: _MASKS[key] = _round_mask(w, h, 18)
    m = _MASKS[key] * a
    # 投影
    pad = 60
    sh_m = np.zeros((h + 2 * pad, w + 2 * pad), np.float32); sh_m[pad:pad + h, pad:pad + w] = 1
    sh_m = cv2.GaussianBlur(sh_m, (0, 0), 26) * 0.75 * a
    ys, xs = max(y0 - pad + 18, 0), max(x0 - pad, 0)
    reg = F[ys:ys + sh_m.shape[0], xs:xs + sh_m.shape[1]]
    reg *= (1 - sh_m[:reg.shape[0], :reg.shape[1], None])
    # 画面（底部渐暗：弱化去字幕残留，也让人名条更清楚）
    if c.get('bands'):
        gy = np.linspace(0, 1, h, dtype=np.float32)
        fr = fr * (1 - 0.42 * np.clip((gy - 0.66) / 0.34, 0, 1) ** 1.3)[:, None, None]
    reg = F[y0:y0 + h, x0:x0 + w]
    reg[:] = reg * (1 - m[..., None]) + fr * m[..., None]
    # 金色细边
    e = np.zeros((h, w), np.float32)
    e = cv2.Canny((_MASKS[key] * 255).astype(np.uint8), 60, 160).astype(np.float32) / 255
    e = cv2.GaussianBlur(e, (0, 0), 0.8) * 1.6
    reg += (np.clip(e, 0, 1) * a * 0.55)[..., None] * GOLD[None, None, :] * 0.8
    # 「原声」标记
    la = a * smooth((u - 0.2) / 0.4)
    if la > 0:
        px, py = x0 + 26, y0 + 30
        dm = np.zeros((24, 24), np.float32); cv2.circle(dm, (12, 12), 7, 1.0, -1, cv2.LINE_AA)
        reg = F[py - 12:py + 12, px - 4:px + 20]
        reg[:] = reg * (1 - dm[..., None] * la) + RED[None, None, :] * dm[..., None] * la
        put_text(F, '原声', px + 26, py, 24, 'sans_b', WHITE, la, 300, 'left', shadow=0.9)
    # 人名条
    ny = y0 + h + 62
    na = a * smooth((u - 0.15) / 0.5)
    if na > 0:
        bx = 70
        reg = F[int(ny - 34):int(ny + 46), bx:bx + 5]
        reg[:] = reg * (1 - na) + GOLD[None, None, :] * na
        put_text(F, info['who'], bx + 24, ny - 12, 44, 'serif', GOLD, na, 500, 'left', shadow=0.7)
        tb = TextBlock(info['who'], 'serif', 44, 500, 'left')
        put_text(F, info['role'], bx + 24 + tb.w + 22, ny - 8, 26, 'sans', WHITE * 0.9, na, 700, 'left', shadow=0.7)
        put_text(F, info['event'], bx + 24, ny + 32, 24, 'sans_l', GREY * 1.25, na, 900, 'left', shadow=0.6)
    # 语境说明
    if c.get('context'):
        ca = a * smooth((u - 0.6) / 0.5)
        put_text(F, c['context'], W / 2, y0 - 40, 26, 'sans', np.array([0.95, 0.85, 0.6]), ca, 960, shadow=0.8)
    # 字幕
    cu = cue_at(cid, u)
    if cu:
        en, zh, al = cu
        al *= a
        tb = TextBlock(balance(zh, 'sans_b', 52, 980), 'sans_b', 52, 1000, 'center', 1.38)
        draw_block(F, tb, W / 2, SUB_ZH_Y, SUB_COL, al, shadow=1.0)
        put_text(F, en, W / 2, SUB_ZH_Y + tb.h / 2 + 46, 28, 'sans_l', EN_COL, al * 0.95, 940, shadow=0.8, lh=1.3)
