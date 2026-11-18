"""全片文字遮挡检查：每 0.1 秒采样一次，记录每一次文字绘制的外框与透明度，
报告两段同时可见（透明度都 > 0.12）且外框相交的文字。用法：python3 check_overlap.py [步长秒]"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
import engine
from engine import text_width
import video as V

REC = []
SCENE = ['?']
_orig = engine.Frame.text

def rec_text(self, s, x, y, size, fnt='sans_med', col=engine.WHITE, a=1.0, anchor='m', track=0.0, **kw):
    if s and a > 0.12:
        eff = a
        t0, out = kw.get('t0'), kw.get('out')
        if t0 is not None: eff *= engine.eo((self.t - t0) / kw.get('dur', 0.45))
        if out is not None: eff *= 1 - engine.eio((self.t - out[0]) / out[1])
        if eff > 0.12 and s.strip():
            tw = text_width(s, fnt, size, track)
            x0 = x - tw / 2 if anchor == 'm' else (x if anchor == 'l' else x - tw)
            REC.append((SCENE[0], s, x0, y - size * 0.42, x0 + tw, y + size * 0.42, eff))
    return _orig(self, s, x, y, size, fnt, col, a, anchor, track, **kw)

engine.Frame.text = rec_text

def wrap(fn):
    def w(f, t):
        SCENE[0] = fn.__name__
        return fn(f, t)
    w.__name__ = fn.__name__
    return w

scenes = [wrap(s) for s in V.SCENES] + [wrap(V.draw_chrome)]
step = float(sys.argv[1]) if len(sys.argv) > 1 else 0.1
issues = {}
t = 0.0
while t < V.DUR:
    REC.clear()
    f = engine.Frame(t)
    for s in scenes:
        s(f, t)
    R = REC[:]
    for i in range(len(R)):
        for j in range(i + 1, len(R)):
            a, b = R[i], R[j]
            ix = min(a[4], b[4]) - max(a[2], b[2]); iy = min(a[5], b[5]) - max(a[3], b[3])
            if ix > 4 and iy > 4:
                key = (a[0], a[1], b[0], b[1])
                issues.setdefault(key, []).append(round(t, 1))
    t += step
for (sa, ta, sb, tb), ts in sorted(issues.items(), key=lambda kv: kv[1][0]):
    print(f'{ts[0]:6.1f}–{ts[-1]:6.1f}s  [{sa}] {ta!r}  ×  [{sb}] {tb!r}  ({len(ts)} 帧)')
print('无遮挡' if not issues else f'共 {len(issues)} 处')
