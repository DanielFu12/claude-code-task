"""全片版式审查（不出图）：按固定间隔逐帧运行渲染逻辑，记录每一处文字、每一块画面的位置、透明度与调用者，
自动找出：① 文字与文字重叠；② 文字压在影像上；③ 停留太短、读不完就消失的文字；④ 播放太短的影像镜头；⑤ 画面空档。

python3 src/audit.py WORK record 0 4      # 第 0 个分片（共 4 片），每秒 4 帧 → WORK/audit/rec_0.jsonl
python3 src/audit.py WORK report          # 汇总 → WORK/audit/report.txt
"""
import sys, os, json, math, inspect
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
WORK = sys.argv[1]
OUTD = os.path.join(WORK, 'audit'); os.makedirs(OUTD, exist_ok=True)
FPS_A = 4

SKIP_CALLERS = {'nav', 'chapter_label', 'follow_pill', 'brand_title', 'gold_line_text'}


def caller():
    for fr in inspect.stack()[2:8]:
        fn = os.path.basename(fr.filename)
        if fn in ('engine.py', 'audit.py'): continue
        return f'{fn}:{fr.function}:{fr.lineno}'
    return '?'


def record(part, nparts):
    import engine
    from engine import Canvas, text_mask, font
    REC = []
    state = {'in_text': 0}
    orig_text, orig_over = Canvas.text, Canvas.over

    def text(self, s, x, y, size, fnt='sans_med', col=None, a=1.0, anchor='m', track=0.0, glow=0.0, gold=False, shadow=0.0,
             mode='over', reveal=None, blur=0.0, scale=1.0):
        if a > 0.05 and s:
            fsz = int(size * scale) if scale != 1 else int(size)
            m, base, w, h = text_mask(s, fnt, fsz, track)
            asc, _ = font(fnt, fsz).getmetrics()
            x0 = x - w / 2 if anchor == 'm' else (x if anchor == 'l' else x - w)
            y0 = y - (base - asc * 0.40)
            ys, xs = np.nonzero(m > 0.15)
            if len(xs):
                vis = 1.0 if reveal is None else float(min(max(reveal, 0), 1))
                REC.append(dict(k='t', s=s, b=[round(x0 + xs.min()), round(y0 + ys.min()), round(x0 + xs.max()), round(y0 + ys.max())],
                                a=round(float(a) * vis, 3), sz=int(size), c=caller()))
        state['in_text'] += 1
        try:
            col = engine.WHITE if col is None else col
            return orig_text(self, s, x, y, size, fnt, col, a, anchor, track, glow, gold, shadow, mode, reveal, blur, scale)
        finally:
            state['in_text'] -= 1

    def over(self, rgb, a, x0, y0):
        if not state['in_text'] and np.ndim(rgb) == 3 and a.shape[0] >= 140 and a.shape[1] >= 200:
            am = float(a.mean())
            if am > 0.05:
                REC.append(dict(k='i', b=[round(x0), round(y0), round(x0 + a.shape[1]), round(y0 + a.shape[0])], a=round(am, 3), c=caller()))
        return orig_over(self, rgb, a, x0, y0)

    Canvas.text, Canvas.over = text, over
    import media as M
    orig_frame = M.frame

    def frame(cv, name, t, t0, t1, *args, **kw):
        n0 = len(REC)
        al = orig_frame(cv, name, t, t0, t1, *args, **kw)
        if al and al > 0.05:
            REC.append(dict(k='f', n=name, a=round(float(al), 3), c=caller()))
        return al
    M.frame = frame
    import gg; gg.M.frame = frame
    import film
    film.finish = lambda cv, i, **kw: None
    N = film.NFRAMES
    idx = list(range(0, N, 30 // FPS_A))
    mine = idx[part::nparts]
    out = open(os.path.join(OUTD, f'rec_{part}.jsonl'), 'w')
    for i in mine:
        REC.clear()
        try:
            film.render(i)
        except Exception as e:
            REC.append(dict(k='err', s=repr(e)))
        out.write(json.dumps(dict(t=round(i / 30, 3), r=REC), ensure_ascii=False) + '\n')
        out.flush()


# ------------------------------------------------------------------ 汇总
def inter(a, b, pad=2):
    x0, y0 = max(a[0], b[0]) - pad, max(a[1], b[1]) - pad
    x1, y1 = min(a[2], b[2]) + pad, min(a[3], b[3]) + pad
    return max(0, x1 - x0) * max(0, y1 - y0)


def area(b): return max(1, (b[2] - b[0]) * (b[3] - b[1]))


def kind(c):
    f = c.split(':')[1] if ':' in c else c
    return f


def report():
    import glob
    frames = []
    for p in glob.glob(os.path.join(OUTD, 'rec_*.jsonl')):
        for ln in open(p): frames.append(json.loads(ln))
    frames.sort(key=lambda f: f['t'])
    out = []
    # ① 文字重叠 / ② 文字压影像
    ov, onimg = {}, {}
    for f in frames:
        ts = [r for r in f['r'] if r['k'] == 't' and r['a'] > 0.3 and kind(r['c']) not in SKIP_CALLERS]
        ims = [r for r in f['r'] if r['k'] == 'i' and r['a'] > 0.3]
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                A, B = ts[i], ts[j]
                if A['s'] == B['s'] and inter(A['b'], B['b'], 0) > 0.5 * min(area(A['b']), area(B['b'])): continue
                ia = inter(A['b'], B['b'])
                if ia > 0.04 * min(area(A['b']), area(B['b'])):
                    key = (A['s'][:24], B['s'][:24], A['c'], B['c'])
                    ov.setdefault(key, []).append(f['t'])
        for A in ts:
            if kind(A['c']) in ('subtitles', 'captions', 'badge', 'name_super'): continue
            for I in ims:
                if inter(A['b'], I['b'], -6) > 0.3 * area(A['b']):
                    key = (A['s'][:30], A['c'], I['c'])
                    onimg.setdefault(key, []).append(f['t'])
    def spans(ts_, step=1 / FPS_A + 1e-3):
        ts_ = sorted(ts_); res = []; s = p = ts_[0]
        for x in ts_[1:]:
            if x - p > step * 1.5: res.append((s, p)); s = x
            p = x
        res.append((s, p)); return res
    out.append('① 文字与文字重叠（透明度都 > 0.3）')
    for k, v in sorted(ov.items(), key=lambda kv: min(kv[1])):
        for a, b in spans(v):
            out.append(f'  {a:7.2f}–{b:7.2f}s  「{k[0]}」 × 「{k[1]}」   [{k[2]} | {k[3]}]')
    out.append('\n② 文字压在影像/照片上（不含字幕与原声字幕）')
    for k, v in sorted(onimg.items(), key=lambda kv: min(kv[1])):
        for a, b in spans(v):
            out.append(f'  {a:7.2f}–{b:7.2f}s  「{k[0]}」   [{k[1]} on {k[2]}]')
    # ③ 停留太短的文字
    vis = {}
    for f in frames:
        seen = set()
        for r in f['r']:
            if r['k'] != 't' or r['a'] < 0.55: continue
            c = kind(r['c'])
            if c in SKIP_CALLERS | {'subtitles', 'captions', 'frame', 'source', 'credit_line', 'quote_card', 'badge'}: continue
            if r['sz'] < 22: continue
            key = (r['s'], r['c'])
            if key in seen: continue
            seen.add(key); vis.setdefault(key, []).append(f['t'])
    out.append('\n③ 停留太短的文字（完全可见的时长 < 读完所需）')
    rows = []
    for (s, c), v in vis.items():
        n = sum(1 for ch in s if ch.strip())
        need = 0.9 + 0.11 * n if any('一' <= ch <= '鿿' for ch in s) else 0.9 + 0.035 * n
        need = min(need, 3.2)
        for a, b in spans(v):
            d = b - a + 1 / FPS_A
            if d < need: rows.append((a, d, need, s, c))
    for a, d, need, s, c in sorted(rows):
        out.append(f'  {a:7.2f}s  可见 {d:4.2f}s < 需 {need:4.2f}s  「{s[:30]}」  [{c}]')
    # ④ 影像镜头太短
    fv = {}
    for f in frames:
        for r in f['r']:
            if r['k'] == 'f' and r['a'] > 0.6: fv.setdefault(r['n'], []).append(f['t'])
    out.append('\n④ 影像镜头完全可见 < 1.5s')
    rows = []
    for n, v in fv.items():
        for a, b in spans(v):
            if b - a + 1 / FPS_A < 1.5: rows.append((a, b - a + 1 / FPS_A, n))
    for a, d, n in sorted(rows): out.append(f'  {a:7.2f}s  {d:4.2f}s  {n}')
    # ⑤ 画面空档：内容区（y 260–1440）没有任何文字/画面
    out.append('\n⑤ 画面空档（内容区无文字、无影像、无动画文字）≥ 0.5s')
    empty = []
    for f in frames:
        has = False
        for r in f['r']:
            if r['k'] in ('t', 'i') and r['a'] > 0.25 and kind(r.get('c', '')) not in SKIP_CALLERS | {'subtitles', 'source'}:
                b = r['b']
                if b[3] > 260 and b[1] < 1440: has = True; break
            if r['k'] == 'f' and r['a'] > 0.25: has = True; break
        if not has: empty.append(f['t'])
    if empty:
        for a, b in spans(empty):
            if b - a + 1 / FPS_A >= 0.5: out.append(f'  {a:7.2f}–{b:7.2f}s')
    errs = [(f['t'], r['s']) for f in frames for r in f['r'] if r['k'] == 'err']
    if errs: out.append('\n错误：' + repr(errs[:5]))
    open(os.path.join(OUTD, 'report.txt'), 'w').write('\n'.join(out) + '\n')
    print('\n'.join(out))


if __name__ == '__main__':
    sys.argv = [sys.argv[0], WORK] + sys.argv[2:]
    if sys.argv[2] == 'record': record(int(sys.argv[3]), int(sys.argv[4]))
    else: report()
