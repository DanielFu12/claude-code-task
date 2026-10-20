"""场景共用组件：背景星云、尘埃、引语卡、字幕、文字粒子化、照片档案框、数据标签。"""
import math, os
from functools import lru_cache
import numpy as np, cv2
from engine import *
import brand_bridge as BB

RNG = np.random.default_rng(2026)

# ------------------------------------------------------------------ 背景
@lru_cache(None)
def _noise_layers():
    """可平铺（周期性）的分形噪声：频域滤波，保证拼接处无缝"""
    out = []
    rng = np.random.default_rng(11)
    fy = np.fft.fftfreq(480)[:, None]; fx = np.fft.fftfreq(270)[None, :]
    r2 = fx ** 2 + fy ** 2
    for k in range(3):
        wn = np.fft.fft2(rng.normal(0, 1, (480, 270)))
        n = np.zeros((480, 270), np.float32)
        for s_, a in ((40, 1.0), (18, 0.55), (7, 0.3)):
            n += np.real(np.fft.ifft2(wn * np.exp(-2 * (np.pi * s_) ** 2 * r2))).astype(np.float32) * a * s_ / 10
        n = (n - n.min()) / (n.max() - n.min())
        out.append(np.tile(n, (2, 2)))
    return out


def backdrop(t, c1=(0.02, 0.035, 0.08), c2=(0.05, 0.10, 0.22), neb=(0.10, 0.22, 0.45), neb_amt=0.5, drift=1.0, top=0.0):
    """深色渐变 + 缓慢流动的星云；返回 H×W×3"""
    L = _noise_layers()
    ox = int((t * 6 * drift) % 270); oy = int((t * 3.5 * drift) % 480)
    a = L[0][oy:oy + 480, ox:ox + 270]
    b = L[1][(oy * 2) % 480:(oy * 2) % 480 + 480, (ox // 2):(ox // 2) + 270]
    n = np.clip(a * 0.65 + b * 0.5 - 0.35, 0, 1) ** 1.6
    n = cv2.resize(n, (W, H), interpolation=cv2.INTER_CUBIC)
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    base = np.asarray(c1, np.float32) * (1 - y) + np.asarray(c2, np.float32) * y * 0.6 + np.asarray(c1, np.float32) * y * 0.4
    f = base + n[..., None] * np.asarray(neb, np.float32) * neb_amt
    if top > 0:
        f = f + np.exp(-((y - 0.0) / 0.35) ** 2) * np.asarray(neb, np.float32) * top
    return np.ascontiguousarray(np.broadcast_to(f, (H, W, 3)), dtype=np.float32).copy()


DUST = RNG.uniform([-40, -60, 2], [40, 60, 140], (9000, 3)).astype(np.float32)
DUST_C = RNG.uniform(0.5, 1.0, (9000, 1)).astype(np.float32)


def dust(buf, cam, t, color=(0.55, 0.75, 1.0), amt=0.45, speed=0.0, focus=40, dof=0.08, n=9000):
    P = DUST[:n].copy()
    P[:, 2] = (P[:, 2] - t * speed) % 138 + 2
    P[:, 1] += np.sin(t * 0.2 + P[:, 0] * 0.1) * 0.3
    particles3d(buf, cam, P, DUST_C[:n] * np.asarray(color, np.float32), size=0.045, alpha=amt, focus=focus, dof=dof)


# ------------------------------------------------------------------ 文字工具
def put_text(frame, text, x, y, size=44, name='sans', color=WHITE, alpha=1.0, maxw=940, align='center',
             reveal=1.0, glow=0.0, lh=1.45, track=0, stagger=0.6, rise=14, shadow=0.55, mode='fade'):
    """在 frame 上画一段文字（带柔和投影和可选辉光），只处理文字包围盒，返回 TextBlock"""
    if alpha <= 0.002: return None
    tb = TextBlock(text, name, size, maxw, align, lh, track)
    draw_block(frame, tb, x, y, color, alpha, reveal, glow, stagger, rise, shadow, mode)
    return tb


def draw_block(frame, tb, x, y, color, alpha=1.0, reveal=1.0, glow=0.0, stagger=0.6, rise=14, shadow=0.55, mode='fade'):
    if not tb.chars or alpha <= 0.002: return
    size = tb.size
    m, x0, y0 = tb.render(x, y, reveal, mode, stagger, rise, pad=int(size * 0.8 + (size * 1.2 if glow else 0)))
    mh, mw = m.shape
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + mw, W), min(y0 + mh, H)
    if X1 <= X0 or Y1 <= Y0: return
    m = m[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
    reg = frame[Y0:Y1, X0:X1]
    col = np.asarray(color, np.float32)
    if shadow > 0:
        reg *= (1 - blur(m, size * 0.12 + 2) * shadow * alpha)[..., None]
    a = (m * alpha)[..., None]
    reg *= (1 - a); reg += a * col
    if glow > 0:
        reg += blur(m, size * 0.35)[..., None] * col * glow * alpha


def gold_text(frame, text, x, y, size, name='serif', alpha=1.0, reveal=1.0, glow=0.35, maxw=980, sweep=None, lh=1.3, stagger=0.6, track=0):
    """品牌金色渐变文字（GOLD_STOPS），可带一道扫光"""
    tb = TextBlock(text, name, size, maxw, 'center', lh, track)
    lay = np.zeros((H, W, 3), np.float32)
    m = tb.draw(lay, x, y, GOLD, 1.0, reveal, glow=glow, stagger=stagger)
    if m is None or alpha <= 0: return tb
    ys = np.where(m.max(axis=1) > 0.01)[0]
    if len(ys) == 0: return tb
    y0, y1 = ys[0], ys[-1] + 1
    ramp = np.zeros((H, 1, 3), np.float32)
    # 每行文字单独套一次品牌渐变：渐变贴合该行字形实际的上下边缘（按字形 mask 量出来），
    # 两端外的行取端点颜色——不能按字号估算，否则字的下边缘会落在渐变之外变成黑色，看起来发虚
    nl = max(len(tb.lines), 1)
    lhpx = size * lh
    ink = m.max(axis=1) > 0.02
    bands = [(int(y - tb.h / 2 + k * lhpx), int(y - tb.h / 2 + (k + 1) * lhpx)) for k in range(nl)]
    edges = [0] + [(bands[k][1] + bands[k + 1][0]) // 2 for k in range(nl - 1)] + [H]
    for k in range(nl):
        lo, hi = max(edges[k], 0), min(edges[k + 1], H)
        rows = np.where(ink[lo:hi])[0]
        if len(rows) == 0: continue
        a, b = lo + rows[0], lo + rows[-1] + 1
        g = BB.gold_ramp(b - a)
        ramp[a:b, 0] = g
        ramp[lo:a, 0] = g[0]; ramp[b:hi, 0] = g[-1]
    col = np.broadcast_to(ramp, (H, W, 3))
    sh = blur(m, size * 0.1 + 2) * 0.6 * alpha
    frame *= (1 - sh)[..., None]
    comp_mask(frame, m, col, alpha)
    frame += lay * alpha
    if sweep is not None and 0 <= sweep <= 1:
        xs = np.arange(W)[None, :] + np.arange(H)[:, None] * 0.35
        pos = (x - tb.w / 2 - 120) + sweep * (tb.w + 240 + H * 0.0)
        band = np.exp(-((xs - pos - (y - tb.h / 2) * 0.35) / (size * 0.45)) ** 2)
        frame += (m * band * alpha)[..., None] * np.array([1.0, 0.92, 0.7], np.float32) * 0.9
    return tb


def mask_points(text, size, name, n, cx, cy, maxw=980):
    """文字 mask → 采样 n 个屏幕坐标点（用于文字粒子化）"""
    tb = TextBlock(text, name, size, maxw)
    lay = np.zeros((H, W, 3), np.float32)
    m = tb.draw(lay, cx, cy, WHITE)
    ys, xs = np.where(m > 0.5)
    if len(xs) == 0: return np.zeros((0, 2), np.float32)
    idx = np.random.default_rng(3).choice(len(xs), n, replace=len(xs) < n)
    return np.stack([xs[idx], ys[idx]], 1).astype(np.float32) + np.random.default_rng(4).uniform(0, 1, (n, 2)).astype(np.float32)


# ------------------------------------------------------------------ 字幕
SUB_Y = 1530


def subtitle(frame, text, a):
    """旁白字幕：底部安全区上方，白色无衬线，最多两行"""
    if a <= 0.01 or not text: return
    tb = TextBlock(text, 'sans', 46, 900, 'center', 1.42)
    if len(tb.lines) > 2:
        tb = TextBlock(text, 'sans', 40, 940, 'center', 1.4)
    draw_block(frame, tb, W / 2, SUB_Y, np.array([0.97, 0.97, 0.95], np.float32), a, shadow=0.9)


# ------------------------------------------------------------------ 引语卡
def quote_card(frame, q, t, t0, t1, y=520, width=960, en_size=44, zh_size=48, tape=None, who_color=GOLD, big=False):
    """档案式引语卡：人物 · 出处 · 时间戳；英文原话（打字机显现）+ 中文译文。
    q: script.QUOTES 中的一项；tape: (秒, 总秒) 显示录像时间轴位置"""
    a = win(t, t0, t1, 0.5, 0.5)
    if a <= 0: return
    u = t - t0
    x0, x1 = (W - width) / 2, (W + width) / 2
    en = TextBlock(q['en'], 'corm_sb', en_size * (1.15 if big else 1), width - 90, 'left', 1.25)
    zh = TextBlock(q['zh'], 'serif_m', zh_size * (1.1 if big else 1), width - 90, 'left', 1.45)
    hdr_h = 112
    tape_h = 70 if tape else 0
    h = hdr_h + en.h + 34 + zh.h + 40 + tape_h + 30
    y0 = y - h / 2
    rise = (1 - ease_out(clamp01(u / 0.7))) * 30
    y0 += rise
    rect_panel(frame, x0, y0, x1, y0 + h, alpha=a, tint=(0.035, 0.045, 0.075), border=(0.95, 0.85, 0.6))
    # 头部：人物 + 出处（第二行）
    put_text(frame, q['who'], x0 + 45, y0 + 44, 38, 'serif', who_color, a, width, 'left', shadow=0)
    src = q['src'] + (('  ·  ' + q['ts']) if q.get('ts') else '')
    put_text(frame, src, x0 + 45, y0 + 86, 21, 'sans_l', GREY * 1.3, a, width - 90, 'left', shadow=0)
    if q.get('ctx'):
        who_w = font('serif', 38).getlength(q['who'])
        put_text(frame, '（' + q['ctx'] + '）', x0 + 45 + who_w + 16, y0 + 46, 22, 'sans_l', GREY * 1.2, a * 0.9, width - who_w - 120, 'left', shadow=0)
    # 金色细线
    ln = np.zeros((H, W, 3), np.float32)
    lw = (width - 90) * ease_out(clamp01(u / 0.9))
    glow_line(ln, [(x0 + 45, y0 + hdr_h), (x0 + 45 + lw, y0 + hdr_h)], GOLD, 1.2, 0.5, a * 0.8)
    frame += ln
    # 英文（打字机）
    rev = clamp01((u - 0.3) / max(1.2, len(q['en']) * 0.028))
    draw_block(frame, en, x0 + 45, y0 + hdr_h + 26 + en.h / 2, np.array([0.93, 0.94, 0.97], np.float32), a, rev,
               stagger=1.0, shadow=0, mode='type')
    # 中文译文
    rz = clamp01((u - 0.6 - len(q['en']) * 0.012) / 1.2)
    draw_block(frame, zh, x0 + 45, y0 + hdr_h + en.h + 60 + zh.h / 2, np.array([1.0, 0.86, 0.55], np.float32), a, rz,
               glow=0.2, shadow=0)
    put_text(frame, '中文为本片译文', x1 - 45, y0 + 44, 18, 'sans_l', GREY, a * 0.8, 400, 'right', shadow=0)
    if tape:
        tape_bar(frame, x0 + 45, x1 - 45, y0 + h - 52, tape[0], tape[1], a, u)


def tape_bar(frame, xa, xb, y, pos, total, a, u):
    """录像时间轴：总长 + 当前引用位置（档案感）"""
    lay = np.zeros((H, W, 3), np.float32)
    glow_line(lay, [(xa, y), (xb, y)], GREY * 0.6, 1.0, 0.0, a)
    p = xa + (xb - xa) * pos / total
    pe = xa + (p - xa) * ease_io(clamp01(u / 1.2))
    glow_line(lay, [(xa, y), (pe, y)], GOLD, 2.0, 0.6, a)
    ring(lay, pe, y, 6, GOLD, 2, a, 0.8)
    frame += lay
    hh, mm, ss = int(pos // 3600), int(pos % 3600 // 60), int(pos % 60)
    put_text(frame, f'{hh}:{mm:02d}:{ss:02d}', pe, y + 26, 20, 'mono', GOLD, a, 300, 'center', shadow=0)


# ------------------------------------------------------------------ 标签
def tag(frame, text, x, y, a, color=GOLD, size=22):
    """小标签：例如「解读」「示意」"""
    if a <= 0: return
    f = font('sans', size)
    w = f.getlength(text) + 28
    rect_panel(frame, x, y - size * 0.9, x + w, y + size * 0.9, alpha=a, tint=(0.04, 0.05, 0.08), border=color, radius=int(size * 0.8), blur_bg=6)
    put_text(frame, text, x + w / 2, y, size, 'sans', color, a, 400, 'center', shadow=0)


def footnote(frame, text, a, y=1700, size=21, color=None):
    put_text(frame, text, W / 2, y, size, 'sans_l', GREY * 1.15 if color is None else color, a, 960, 'center', shadow=0.3, lh=1.35)


# ------------------------------------------------------------------ 档案照片
@lru_cache(None)
def load_photo(path, w, h, gray=True):
    im = cv2.imread(path, cv2.IMREAD_COLOR)
    if im is None: return None
    im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    ih, iw = im.shape[:2]
    s = max(w / iw, h / ih) * 1.12
    im = cv2.resize(im, (int(iw * s), int(ih * s)), interpolation=cv2.INTER_AREA)
    if im.mean() < 0.25:   # 偏暗的现场照片：提亮暗部
        im = np.clip(im / max(np.percentile(im, 99.5), 1e-3), 0, 1) ** 0.62
    if gray:
        g = im.mean(axis=2, keepdims=True)
        im = g * np.array([1.0, 0.94, 0.82], np.float32) * 0.85 + im * 0.15   # 暖调单色档案感
    return im


def archive_photo(frame, path, cx, cy, w, h, t, t0, t1, credit, focus=(0.5, 0.35)):
    """档案照片：慢推镜、暖调单色、颗粒、细金框、署名"""
    a = win(t, t0, t1, 0.6, 0.6)
    if a <= 0: return
    im = load_photo(path, int(w), int(h))
    if im is None:
        put_text(frame, '[照片缺失]', cx, cy, 30, 'sans', RED, a); return
    u = clamp01((t - t0) / max(t1 - t0, 0.1))
    s = 1.0 + 0.06 * u
    ih, iw = im.shape[:2]
    cw, ch = w / s, h / s
    fx = np.clip(focus[0] * iw - cw / 2, 0, iw - cw); fy = np.clip(focus[1] * ih - ch / 2, 0, ih - ch)
    crop = im[int(fy):int(fy + ch), int(fx):int(fx + cw)]
    crop = cv2.resize(crop, (int(w), int(h)), interpolation=cv2.INTER_LINEAR)
    yy, xx = np.mgrid[0:int(h), 0:int(w)].astype(np.float32)
    vg = np.clip(1.2 - (((xx - w / 2) / w) ** 2 + ((yy - h / 2) / h) ** 2) * 1.6, 0.3, 1)[..., None]
    crop = crop * vg
    x0, y0 = int(cx - w / 2), int(cy - h / 2 + (1 - ease_out(clamp01((t - t0) / 0.8))) * 20)
    reg = frame[y0:y0 + int(h), x0:x0 + int(w)]
    reg[:] = reg * (1 - a) + crop[:reg.shape[0], :reg.shape[1]] * a
    lay = np.zeros((H, W, 3), np.float32)
    glow_line(lay, [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h), (x0, y0)], GOLD * 0.8, 1.2, 0.35, a)
    frame += lay
    put_text(frame, credit, x0 + w, y0 + h + 22, 17, 'sans_l', GREY * 1.2, a * 0.9, w, 'right', shadow=0.4)
