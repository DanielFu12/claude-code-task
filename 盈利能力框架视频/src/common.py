"""场景公用：时间轴、节拍、场景上下文、常用部件（图标、卡片、数字、3D 投影…）。"""
import json, math, os
import numpy as np, cv2
from engine import *

WORK = os.path.join(HERE, '..', 'work')
TL = json.load(open(os.path.join(WORK, 'timeline.json')))
BEAT, BAR, TOTAL = TL['beat'], TL['bar'], TL['total']
SCENES = TL['scenes']
SC = {s['id']: s for s in SCENES}
CHAP = {c['key']: c for c in TL['chapters']}
LAYER_COL = {'L0': RED, 'L1': C(255, 200, 90), 'L2': ORANGE, 'L3': TEAL, 'L4': C(90, 170, 255), 'L5': VIOLET}
LAYERS = [('L0', '生存'), ('L1', '价值创造与获取'), ('L2', '维持成本'), ('L3', '再投资'), ('L4', '资本与治理'), ('L5', '时间与演化')]

try:
    KICKS = np.load(os.path.join(WORK, 'kicks.npy'))
    KT = np.sort(KICKS[:, 0]) if len(KICKS) else np.array([-99.0])
except Exception:
    KT = np.array([-99.0])
STINGS = [s['start'] for s in SCENES if s['sting'] and s['start'] > 0]


def kick_pulse(t, d=0.14):
    i = np.searchsorted(KT, t, 'right') - 1
    if i < 0: return 0.0
    return math.exp(-(t - KT[i]) / d)


def beat_pulse(t, d=0.12):
    ph = (t / BEAT) % 1.0
    return math.exp(-ph * BEAT / d)


def sting_pulse(t, d=0.5):
    v = 0.0
    for s in STINGS:
        if s <= t < s + 4 * d:
            v = max(v, math.exp(-(t - s) / d))
    return v


class Ctx:
    """场景上下文：S.c('cue') 取量化后的提示点时刻，S.a('cue', 0.4) 取出现进度"""

    def __init__(self, sc, t, end=None):
        self.sc, self.t = sc, t
        self.start, self.end = sc['start'], (sc['end'] if end is None else end)
        self.lt = t - sc['start']
        self.dur = sc['end'] - sc['start']
        self.cq = sc['cq']
        self.raw = sc['cues']

    def c(self, k, default=None):
        if k in self.cq: return self.cq[k]
        if default is not None: return default
        raise KeyError(self.sc['id'] + ':' + k)

    def a(self, k, d=0.45, f=eo, off=0.0):
        return f((self.t - self.c(k) - off) / max(d, 1e-4))

    def since(self, k):
        return self.t - self.c(k)

    def at(self, tt, d=0.45, f=eo):
        return f((self.t - tt) / max(d, 1e-4))

    def p(self, k, d=0.35):
        return pulse(self.t, self.c(k), d)

    def w(self, sub, n=0, quant=True):
        """某个词在旁白里被念到的时刻"""
        cnt = 0
        for u in self.sc['utts']:
            i = u['text'].find(sub)
            while i >= 0:
                if cnt == n:
                    tt = u['ct'][i]
                    return round(tt / (BEAT / 2)) * (BEAT / 2) if quant else tt
                cnt += 1
                i = u['text'].find(sub, i + 1)
        raise KeyError(sub)

    def fade_out(self, d=0.5):
        return 1 - eio((self.t - (self.end - d)) / d)


# ---------------------------------------------------------------- widgets
def label_pill(fr, s, x, y, col, a=1.0, size=30, fnt='sans_bold', pad=18, h=None, fill=0.18, anchor='m', txtcol=None):
    tw = text_width(s, fnt, size)
    h = h or size * 1.6
    x0 = x - tw / 2 - pad if anchor == 'm' else (x if anchor == 'l' else x - tw - 2 * pad)
    fr.panel(x0, y - h / 2, x0 + tw + 2 * pad, y + h / 2, col, a, r=h / 2, fill=fill, th=2, glow=0.0)
    fr.text(s, x0 + pad + tw / 2, y, size, fnt, txtcol or lerpc(col, WHITE, 0.55), a)
    return x0, x0 + tw + 2 * pad


def number_ticker(v, fmt='{:,.0f}'):
    return fmt.format(v)


def draw_icon(fr, kind, cx, cy, s, col, a=1.0, th=3, t=0.0):
    """线性小图标，s 为尺寸"""
    if a <= 0.003: return
    h = s / 2
    if kind == 'bars':        # ROIC 柱高于 WACC 虚线
        for i, (x, hh) in enumerate(((-0.45, 0.5), (0.0, 0.9), (0.45, 0.7))):
            fr.rrect(cx + x * h - h * 0.16, cy + h * 0.8 - hh * h * 1.5, cx + x * h + h * 0.16, cy + h * 0.8, 3, col, a, th)
        for k in range(6):
            x0 = cx - h + k * h * 0.36
            fr.line((x0, cy + h * 0.05), (x0 + h * 0.2, cy + h * 0.05), WHITE, a * 0.8, 2)
    elif kind == 'cycle':
        fr.arc((cx, cy), h * 0.8, -2.6, 2.0, col, a, th)
        ang = 2.0
        p = (cx + h * 0.8 * math.cos(ang), cy + h * 0.8 * math.sin(ang))
        fr.line(p, (p[0] + h * 0.35, p[1] - h * 0.05), col, a, th)
        fr.line(p, (p[0] + h * 0.05, p[1] - h * 0.38), col, a, th)
    elif kind == 'branch':
        fr.line((cx - h, cy + h * 0.6), (cx - h * 0.1, cy), col, a, th)
        for dy in (-0.75, 0.0, 0.75):
            fr.arrow((cx - h * 0.1, cy), (cx + h, cy + dy * h), col, a, th, h * 0.3)
    elif kind == 'hourglass':
        fr.poly([(cx - h * 0.6, cy - h), (cx + h * 0.6, cy - h), (cx - h * 0.6, cy + h), (cx + h * 0.6, cy + h)], col, a, th, closed=True)
        fr.line((cx - h * 0.8, cy - h), (cx + h * 0.8, cy - h), col, a, th + 1)
        fr.line((cx - h * 0.8, cy + h), (cx + h * 0.8, cy + h), col, a, th + 1)
        fr.fillpoly([(cx - h * 0.3, cy + h * 0.9), (cx + h * 0.3, cy + h * 0.9), (cx, cy + h * 0.45)], col, a * 0.8, 'E')
    elif kind == 'pulse':
        pts = [(-1, 0), (-0.55, 0), (-0.4, -0.7), (-0.2, 0.8), (-0.05, -0.3), (0.1, 0), (1, 0)]
        fr.poly([(cx + x * h, cy + y * h) for x, y in pts], col, a, th)
        fr.line((cx + 0.3 * h, cy - 0.35 * h), (cx + 0.8 * h, cy + 0.35 * h), col, a, th)
        fr.line((cx + 0.8 * h, cy - 0.35 * h), (cx + 0.3 * h, cy + 0.35 * h), col, a, th)
    elif kind == 'warn':
        fr.poly([(cx, cy - h), (cx + h * 1.05, cy + h * 0.8), (cx - h * 1.05, cy + h * 0.8)], col, a, th, closed=True)
        fr.line((cx, cy - h * 0.35), (cx, cy + h * 0.25), col, a, th + 1)
        fr.disc((cx, cy + h * 0.52), th * 0.9, col, a)
    elif kind == 'check':
        fr.poly([(cx - h * 0.7, cy), (cx - h * 0.2, cy + h * 0.5), (cx + h * 0.8, cy - h * 0.6)], col, a, th + 1)
    elif kind == 'cross':
        fr.line((cx - h * 0.6, cy - h * 0.6), (cx + h * 0.6, cy + h * 0.6), col, a, th + 1)
        fr.line((cx + h * 0.6, cy - h * 0.6), (cx - h * 0.6, cy + h * 0.6), col, a, th + 1)
    elif kind == 'tag':        # 价格标签 + 上箭头
        fr.poly([(cx - h * 0.9, cy - h * 0.3), (cx - h * 0.3, cy - h * 0.8), (cx + h * 0.4, cy - h * 0.8), (cx + h * 0.4, cy + h * 0.2),
                 (cx - h * 0.3, cy + h * 0.2)], col, a, th, closed=True)
        fr.circle((cx - h * 0.05, cy - h * 0.48), h * 0.1, col, a, th - 1)
        fr.arrow((cx + h * 0.75, cy + h * 0.9), (cx + h * 0.75, cy - h * 0.2), col, a, th, h * 0.28)
    elif kind == 'coins':
        for k in range(4):
            yy = cy + h * 0.7 - k * h * 0.38
            fr.poly([(cx - h * 0.8, yy), (cx + h * 0.8, yy)], col, a, th)
            fr.arc((cx, yy - h * 0.12), h * 0.8, 0, math.pi, col, a * 0.6, th - 1)
        fr.rrect(cx - h * 0.8, cy - h * 0.6, cx + h * 0.8, cy + h * 0.7, 6, col, a * 0.6, th - 1)
    elif kind == 'gear':
        n = 8
        pts = []
        for k in range(n * 2):
            ang = k * math.pi / n + t
            r = h * (0.95 if k % 2 == 0 else 0.72)
            pts.append((cx + r * math.cos(ang - 0.12), cy + r * math.sin(ang - 0.12)))
            pts.append((cx + r * math.cos(ang + 0.12), cy + r * math.sin(ang + 0.12)))
        fr.poly(pts, col, a, th, closed=True)
        fr.circle((cx, cy), h * 0.3, col, a, th)
    elif kind == 'person':
        fr.circle((cx, cy - h * 0.45), h * 0.3, col, a, th)
        fr.arc((cx, cy + h * 0.65), h * 0.65, math.pi, 2 * math.pi, col, a, th)
    elif kind == 'pause':
        fr.circle((cx, cy), h * 0.95, col, a, th)
        fr.line((cx - h * 0.25, cy - h * 0.4), (cx - h * 0.25, cy + h * 0.4), col, a, th + 2)
        fr.line((cx + h * 0.25, cy - h * 0.4), (cx + h * 0.25, cy + h * 0.4), col, a, th + 2)
    elif kind == 'shield':
        fr.poly([(cx, cy - h), (cx + h * 0.8, cy - h * 0.65), (cx + h * 0.7, cy + h * 0.25), (cx, cy + h),
                 (cx - h * 0.7, cy + h * 0.25), (cx - h * 0.8, cy - h * 0.65)], col, a, th, closed=True)
    elif kind == 'factory':
        fr.poly([(cx - h, cy + h * 0.8), (cx - h, cy - h * 0.1), (cx - h * 0.5, cy + h * 0.2), (cx - h * 0.5, cy - h * 0.1),
                 (cx, cy + h * 0.2), (cx, cy - h * 0.1), (cx + h * 0.5, cy + h * 0.2), (cx + h * 0.5, cy - h * 0.9),
                 (cx + h * 0.8, cy - h * 0.9), (cx + h * 0.8, cy + h * 0.8)], col, a, th, closed=True)
    elif kind == 'plane':
        sc = h / 60
        body = [(-60, 0), (50, -4), (62, 0), (50, 5), (-60, 4)]
        fr.poly([(cx + x * sc, cy + y * sc) for x, y in body], col, a, th, closed=True)
        fr.poly([(cx - 5 * sc, cy), (cx + 10 * sc, cy - 45 * sc), (cx + 22 * sc, cy - 45 * sc), (cx + 15 * sc, cy)], col, a, th, closed=True)
        fr.poly([(cx - 5 * sc, cy + 3 * sc), (cx + 10 * sc, cy + 45 * sc), (cx + 22 * sc, cy + 45 * sc), (cx + 15 * sc, cy + 3 * sc)], col, a, th, closed=True)
        fr.poly([(cx - 50 * sc, cy), (cx - 62 * sc, cy - 18 * sc), (cx - 55 * sc, cy - 18 * sc), (cx - 42 * sc, cy)], col, a, th, closed=True)


def proj3(P, yaw, pitch, cx, cy, f=1400, dist=1600):
    """3D 点 (N,3) -> 屏幕 (N,2)，以及深度"""
    P = np.asarray(P, np.float64)
    cy_, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    x = P[:, 0] * cy_ + P[:, 2] * sy
    z = -P[:, 0] * sy + P[:, 2] * cy_
    y = P[:, 1] * cp - z * sp
    z2 = P[:, 1] * sp + z * cp
    s = f / (dist + z2)
    return np.stack([cx + x * s, cy - y * s], 1), z2


def shockwave(fr, c, t0, col, t=None, speed=1500, life=0.9, th=3, a=1.0):
    t = fr.t if t is None else t
    dt = t - t0
    if dt < 0 or dt > life: return
    r = dt * speed * (1 - dt / (life * 2.2))
    al = (1 - dt / life) ** 1.5 * a
    fr.circle(c, r, col, al, th)
    fr.circle(c, r * 0.82, col, al * 0.4, max(1, th - 1))


def light_rays(fr, c, n, length, col, a, t, width=0.05, buf='B'):
    for k in range(n):
        ang = k / n * 2 * math.pi + t * 0.1
        w = width * (0.6 + 0.4 * math.sin(k * 2.3 + t))
        p1 = (c[0] + math.cos(ang - w) * length, c[1] + math.sin(ang - w) * length)
        p2 = (c[0] + math.cos(ang + w) * length, c[1] + math.sin(ang + w) * length)
        fr.fillpoly([c, p1, p2], col, a * (0.5 + 0.5 * math.sin(k * 1.7 + t * 0.7)), buf)


def particle_text_points(s, fnt, size, step=3, track=0.0):
    m, cy = text_mask(s, fnt, size, track)
    ys, xs = np.where(m[::step, ::step] > 0.45)
    return xs * step - m.shape[1] / 2, ys * step - cy, m


def draw_line_chart(fr, xs, ys, col, a=1.0, th=3, prog=1.0, head=True, glow=0.0):
    n = len(xs)
    k = max(2, int(prog * (n - 1)) + 1)
    pts = np.stack([xs[:k], ys[:k]], 1)
    if prog < 1 and k < n:
        fx = prog * (n - 1) - (k - 1)
        last = (xs[k - 1] + (xs[min(k, n - 1)] - xs[k - 1]) * fx, ys[k - 1] + (ys[min(k, n - 1)] - ys[k - 1]) * fx)
        pts = np.vstack([pts, [last]])
    fr.poly(pts, col, a, th)
    if head and a > 0.01:
        fr.glow(tuple(pts[-1]), 10, col, a * 0.9)
        fr.disc(tuple(pts[-1]), 4.5, lerpc(col, WHITE, 0.5), a)
    return pts


def headline(fr, s, x, y, size, col, a=1.0, t0=None, fnt='serif_black', glow=0.35, anchor='m', stag=0.04, track=0.02):
    """金色渐变大标题"""
    grad = [lerpc(col, WHITE, 0.55), col, lerpc(col, (0.5, 0.3, 0.1), 0.25)]
    return fr.text(s, x, y, size, fnt, col, a, anchor=anchor, mode='L', glow=glow, grad=grad, t0=t0, stag=stag, track=track)


def typeline(fr, s, x, y, size, col, a, t0, cps=14, fnt='serif_med', anchor='m', glow=0.2, mode='L'):
    """逐字显现（打字机式淡入）"""
    n = len(s)
    chars = [cl((fr.t - t0) * cps - i, 0, 1) for i in range(n)]
    return fr.text(s, x, y, size, fnt, col, a, anchor=anchor, chars_alpha=chars, glow=glow, mode=mode)
