"""解说段（G1–G9）的画面：每句解说配一个信息画面，关键视觉卡在解说的关键词上（t3.wt）。"""
import math
import numpy as np, cv2
from engine import W, H, GOLD, GOLD_HI, GOLD_SUB, CYAN, RED, WHITE, GREY, smooth, clamp01, ease_out, ease_io, win, lerp, splat
from common import put_text, gold_text, footnote
import vis as V
import ftscene as FT
import t3

S, wt = t3.SENTS, t3.wt
RED_S = np.array([1.0, 0.36, 0.30], np.float32)


def st(sid): return S[sid]['t0']
def en(sid): return S[sid]['t1']


def still(F, cid, u, cx, cy, w, a, zoom=(1.0, 1.08), dur=8.0, t=0.0, t0=0.0, dim=1.0):
    """把处理好的影像片段的一帧作为「静帧」放进画面（缓慢推镜），HDR 空间内保持原色"""
    if a <= 0.003: return
    fr = FT.frame_of(cid, u)
    h = int(w * fr.shape[0] / fr.shape[1])
    z = lerp(zoom[0], zoom[1], ease_io(clamp01((t - t0) / dur)))
    big = cv2.resize(fr, (int(w * z), int(h * z)), interpolation=cv2.INTER_AREA)
    ox, oy = (big.shape[1] - w) // 2, (big.shape[0] - h) // 2
    img = FT.inv_tonemap(np.minimum(big[oy:oy + h, ox:ox + w], 0.82)) * dim      # 压住高光，饱和的红色不会泛成光晕
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    m = FT._round_mask(w, h, 16) * a
    V.darken_box(F, x0, y0 + 14, x0 + w, y0 + h + 14, 0.6 * a, 40)
    reg = F[y0:y0 + h, x0:x0 + w]
    reg[:] = reg * (1 - m[..., None]) + img * m[..., None]
    V.bracket(F, x0 - 14, y0 - 14, x0 + w + 14, y0 + h + 14, GOLD, a * 0.8, L=30)
    return x0, y0, w, h


def event_card(F, t, a, y=640):
    if a <= 0.003: return
    V.bracket(F, 90, y - 150, W - 90, y + 150, GOLD, a, plate=0.45)
    put_text(F, '2026.10.05  ·  纽约 · 大都会俱乐部', W / 2, y - 80, 30, 'sans', GOLD_SUB * 1.15, a, 900, track=3, shadow=0)
    gold_text(F, '第 36 届格雷厄姆与多德年度活动', W / 2, y, 52, 'serif', a, 1.0, glow=0.25)
    put_text(F, 'Columbia Business School · Heilbrunn Center for Graham & Dodd Investing', W / 2, y + 76, 22, 'sans_l', V.DIM, a, 960, shadow=0)


# ------------------------------------------------------------------ G1：钩子
_rk = np.random.default_rng(7)
TILE_SEEDS = _rk.uniform(0, 1, (40, 3))


def g1(F, t):
    # S01：李录静帧（接冷开场的最后一帧）
    a1 = win(t, st('S01') - 0.3, st('S02') - 0.1, 0.4, 0.4)
    if a1 > 0:
        still(F, 'LB', 15.4, W / 2, 760, 900, a1, t=t, t0=st('S01'), dur=5)
        put_text(F, '李录', W / 2 - 330, 1120, 54, 'serif', GOLD, a1, 400, 'left', shadow=0.6)
        put_text(F, '喜马拉雅资本创始人、董事长', W / 2 - 330, 1185, 28, 'sans', V.INK_T, a1 * 0.9, 900, 'left', shadow=0.6)
    # S02：活动卡 → “速度 / 规模 / 前所未有”
    a2 = win(t, st('S02') - 0.2, st('S03') - 0.1, 0.4, 0.4)
    if a2 > 0:
        ea = a2 * (1 - smooth((t - wt('S02', '他谈到') + 0.2) / 0.5))
        event_card(F, t, ea)
        k0 = wt('S02', '变化的速度')
        if t > k0 - 0.3:
            # 加速的光流：越来越快
            u = max(t - k0, 0.0)
            n = 90
            r = np.random.default_rng(3)
            ys = r.uniform(420, 1300, n); sp = r.uniform(0.6, 1.4, n)
            xs = ((r.uniform(0, 1, n) + (u ** 1.6) * 0.35 * sp) % 1.0) * (W + 400) - 200
            for i in range(n):
                L = 40 + 260 * min(u / 3, 1) * sp[i]
                V.line(F, [(xs[i] - L, ys[i]), (xs[i], ys[i])], CYAN if i % 5 else GOLD_HI, 1.2, a2 * 0.35, 0.4)
            V.slam(F, '速度', W / 2 - 200, 720, 120, t, k0, a2, gold=False, color=WHITE)
            V.slam(F, '规模', W / 2 + 200, 720, 120, t, wt('S02', '涉及的规模'), a2, gold=False, color=WHITE)
            V.slam(F, '前所未有', W / 2, 930, 150, t, wt('S02', '前所未有'), a2)
    # S03：零和、短期——积木搭起又散掉
    a3 = win(t, st('S03') - 0.2, st('S04') - 0.1, 0.4, 0.4)
    if a3 > 0:
        V.rise(F, '零和  ·  短期', W / 2, 500, 64, t, st('S03'), 'serif', V.INK_T, a3)
        cyc = 2.2
        u = (t - st('S03')) % cyc
        base_y = 1180
        nbuilt = int(min(u / 0.28, 6))
        for k in range(6):
            if k < nbuilt:
                y = base_y - k * 72
                x = W / 2 + (k % 2) * 8 - 4
                crash = clamp01((u - 1.75) / 0.4)
                dx = (TILE_SEEDS[k, 0] - 0.5) * 500 * crash; dy = 900 * crash ** 2 * (0.6 + TILE_SEEDS[k, 1])
                al = a3 * (1 - crash)
                col = np.array([0.55, 0.75, 1.0], np.float32)
                pts = [(x - 150 + dx, y - 30 + dy), (x + 150 + dx, y - 30 + dy), (x + 150 + dx, y + 30 + dy), (x - 150 + dx, y + 30 + dy)]
                V.fill_poly(F, pts, col * 0.25, al)
                V.line(F, pts, col, 1.6, al, 0.6, closed=True)
        put_text(F, '学到的东西不断作废', W / 2, 1300, 34, 'sans', V.DIM, a3 * smooth((t - wt('S03', '学到的东西')) / 0.4), 900, shadow=0)
    # S04：问题
    a4 = win(t, st('S04') - 0.2, t3.seg('title')['t0'] + 0.05, 0.4, 0.25)
    if a4 > 0:
        V.rise(F, '在一个越来越快的时代', W / 2, 760, 54, t, st('S04'), 'serif_m', V.INK_T, a4)
        k = wt('S04', '什么才值得')
        V.rise(F, '什么才值得我们', W / 2, 880, 62, t, k, 'serif', V.INK_T, a4)
        V.slam(F, '花几十年去积累？', W / 2, 1000, 84, t, wt('S04', '几十年'), a4)


# ------------------------------------------------------------------ GH：AI 时代的两种诱惑 → 守住复利
# 第五版：放在李录讲完复利的定义（S07–S08）之后、「这套人生观来自一个人」（S09）之前，与 G4 同段解说。
_rn = np.random.default_rng(21)
_NODE = _rn.normal(0, 1, (64, 3)); _NODE /= np.linalg.norm(_NODE, axis=1, keepdims=True)
_EDGE = [(i, j) for i in range(64) for j in range(i + 1, 64) if _NODE[i] @ _NODE[j] > 0.80]
_PULSE = _rn.integers(0, len(_EDGE), 18), _rn.uniform(0, 1, 18), _rn.uniform(0.6, 1.4, 18)
_VORT = np.c_[_rn.uniform(0, 2 * math.pi, 700), _rn.uniform(380, 900, 700), _rn.uniform(0.5, 1.5, 700)]


def circle(cx, cy, r, n=96):
    th = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.c_[cx + r * np.cos(th), cy + r * np.sin(th)].astype(np.float32)


def ai_core(F, cx, cy, R, t, a, energy=0.5):
    """旋转的神经网络球：节点 + 近邻连线（按前后深度分三层画）+ 沿连线跑动的光脉冲 + 中心「AI」"""
    if a <= 0.003: return
    th = t * 0.45; c, s_ = math.cos(th), math.sin(th)
    P = _NODE @ np.array([[c, 0, -s_], [0, 1, 0], [s_, 0, c]], np.float32).T
    P = P @ np.array([[1, 0, 0], [0, math.cos(0.35), -math.sin(0.35)], [0, math.sin(0.35), math.cos(0.35)]], np.float32).T
    xy = np.c_[cx + P[:, 0] * R, cy + P[:, 1] * R]
    depth = (P[:, 2] + 1) / 2                                       # 0 远 → 1 近
    pad = 40
    x0, y0 = int(cx - R - pad), int(cy - R - pad); w = h = int(2 * R + 2 * pad)
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if X1 <= X0 or Y1 <= Y0: return
    lay = np.zeros((h, w), np.float32)
    for lo, hi, k in ((0, 0.4, 0.25), (0.4, 0.7, 0.55), (0.7, 1.01, 1.0)):
        m = np.zeros((h, w), np.uint8)
        segs = [np.round((np.array([xy[i], xy[j]]) - [x0, y0]) * 16).astype(np.int32) for i, j in _EDGE
                if lo <= (depth[i] + depth[j]) / 2 < hi]
        if segs: cv2.polylines(m, segs, False, 255, 1, cv2.LINE_AA, shift=4)
        lay += m.astype(np.float32) / 255 * k
    g = lay + cv2.GaussianBlur(lay, (0, 0), 4) * (0.8 + 1.2 * energy) + cv2.GaussianBlur(lay, (0, 0), 14) * (0.5 + 1.0 * energy)
    F[Y0:Y1, X0:X1] += g[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0, None] * (CYAN * 0.75 * a)
    splat(F, xy[:, 0].astype(np.float32), xy[:, 1].astype(np.float32), (1.6 + 2.2 * depth).astype(np.float32),
          np.outer(0.4 + 0.6 * depth, CYAN * 0.6 + 0.4), a * (0.5 + 0.5 * energy))
    ei, ph, sp = _PULSE                                              # 光脉冲
    u = (ph + t * sp * (0.6 + 1.2 * energy)) % 1.0
    pa = np.array([xy[_EDGE[k][0]] for k in ei]); pb = np.array([xy[_EDGE[k][1]] for k in ei])
    pp = pa + (pb - pa) * u[:, None]
    splat(F, pp[:, 0].astype(np.float32), pp[:, 1].astype(np.float32), np.full(len(pp), 2.6, np.float32), WHITE * 1.4, a * energy)
    V.dot(F, cx, cy, R * 0.22, CYAN * 0.5, a * (0.25 + 0.35 * energy), 1.0)
    put_text(F, 'AI', cx, cy, int(R * 0.42), 'mono', WHITE, a, 400, shadow=0, glow=0.4 + 0.6 * energy)


def person(F, x, y, a, s=1.0, col=GOLD):
    """线描人像：头 + 肩"""
    if a <= 0.003: return
    V.line(F, circle(x, y, 46 * s, 64), col, 2.4, a, 0.7, closed=True)
    u = np.linspace(0, 1, 40)
    sx = x + (u - 0.5) * 230 * s
    sy = y + 190 * s - 120 * s * np.sin(u * math.pi) ** 0.6
    V.line(F, np.c_[sx, sy], col, 2.4, a, 0.7)


def bezier(p0, p1, p2, u):
    u = np.asarray(u)[:, None]
    return (1 - u) ** 2 * p0 + 2 * (1 - u) * u * p1 + u ** 2 * p2


def gh(F, t):
    h1, h2, h3, h4 = st('H01'), st('H02'), st('H03'), st('H04')
    end = st('S09')
    # ---------------------------------------------------------------- AI 核心：H01 居中长大 → H02 退到右上 → H03 消失
    ac = win(t, h1 - 0.05, h3 + 0.2, 0.5, 0.45)
    if ac > 0:
        grow = ease_out(clamp01((t - wt('H01', '越强大') + 0.1) / 0.9))
        mv = ease_io(clamp01((t - h2 + 0.1) / 0.8))
        cx, cy = lerp(W / 2, 790, mv), lerp(820, 650, mv)
        R = lerp(lerp(130, 250, grow), 150, mv)
        en = 0.35 + 0.65 * grow * (1 - 0.4 * mv) + 0.3 * math.exp(-max(t - wt('H01', '越强大'), 0) * 3) * (t > wt('H01', '越强大'))
        if t < h2 + 0.3:                                              # 长大时的冲击波
            ku = t - wt('H01', '越强大')
            if 0 < ku < 1.3:
                V.line(F, circle(cx, cy, R + 500 * ease_out(ku / 1.3)), CYAN, 2.5, ac * (1 - ku / 1.3) ** 1.6, 1.0, closed=True)
        ai_core(F, cx, cy, R, t, ac, en)
        # 诱惑：金色微粒被卷进漩涡
        kv = wt('H01', '诱惑')
        va = ac * smooth((t - kv + 0.4) / 0.5) * (1 - mv)
        if va > 0:
            ang, r0, spd = _VORT[:, 0], _VORT[:, 1], _VORT[:, 2]
            u = max(t - kv + 0.4, 0)
            rr = r0 * np.exp(-u * 0.55 * spd) + R * 0.3
            aa = ang + u * 1.6 * spd + 260 / rr
            splat(F, (cx + np.cos(aa) * rr).astype(np.float32), (cy + np.sin(aa) * rr * 0.92).astype(np.float32),
                  np.full(len(aa), 1.5, np.float32), GOLD_HI, va * 0.55 * np.clip(rr / 300, 0.2, 1))
        if t < h2 + 0.2:
            V.slam(F, '诱惑也越大', W / 2, 1270, 108, t, kv, ac * (1 - smooth((t - h2 + 0.3) / 0.4)))
    # ---------------------------------------------------------------- H02：外包思考
    a2 = win(t, h2 - 0.1, h3 + 0.05, 0.5, 0.4)
    if a2 > 0:
        put_text(F, '诱惑一', 150, 430, 30, 'sans', CYAN, a2, 300, 'left', shadow=0, track=4)
        V.rise(F, '把思考外包给 AI', 150, 486, 52, t, h2 + 0.1, 'serif', WHITE, a2, align='left')
        hx, hy = 250, 820
        person(F, hx, hy, a2 * smooth((t - h2) / 0.6))
        ko = wt('H02', '外包')
        fa = a2 * smooth((t - ko + 0.3) / 0.4)
        if fa > 0:                                                    # 思考的光点沿弧线流向 AI
            p0, p1, p2 = np.array([hx + 40, hy - 30.]), np.array([480, 560.]), np.array([690, 640.])
            u = ((np.arange(60) / 60 + (t - ko) * 0.55) % 1.0)
            q = bezier(p0, p1, p2, u)
            splat(F, q[:, 0].astype(np.float32), (q[:, 1] + np.sin(u * 20 + t * 3) * 6).astype(np.float32),
                  np.full(60, 2.2, np.float32), GOLD_HI, fa * np.sin(u * math.pi) ** 0.7)
            V.dot(F, hx, hy, 10, GOLD_HI, fa * (0.6 + 0.4 * math.sin(t * 9)), 1.4)
        # 底部图表：AI 的能力一路上扬，自己的积累停在 0
        kn = wt('H02', '不再积累')
        ga = a2 * smooth((t - kn + 0.6) / 0.5)
        if ga > 0:
            x0, x1, yb = 140, 940, 1390
            u = ease_out(clamp01((t - kn + 0.6) / 2.0))
            xs = np.linspace(0, u, 60)
            V.line(F, np.c_[x0 + xs * (x1 - x0), yb - 200 * (np.exp(3 * xs) - 1) / (math.e ** 3 - 1)], CYAN, 2.6, ga, 0.8)
            V.line(F, np.c_[x0 + xs * (x1 - x0), np.full(60, yb - 2.0)], GOLD, 3.0, ga, 0.8)
            V.line(F, [(x0, yb + 14), (x1, yb + 14)], V.DIM, 1.0, ga * 0.5, 0)
            put_text(F, 'AI 的能力', x0 + u * (x1 - x0) - 10, yb - 200 * (math.exp(3 * u) - 1) / (math.e ** 3 - 1) - 40, 30, 'sans', CYAN, ga * smooth(u / 0.5), 300, 'right', shadow=0)
            put_text(F, '自己的积累  0', x0 + u * (x1 - x0) - 10, yb - 36, 30, 'sans', GOLD, ga * smooth(u / 0.5), 400, 'right', shadow=0)
        km = wt('H02', '没有积累')
        if t > km - 0.1:
            V.slam(F, '没有积累，谈何复利？', W / 2, 1062, 66, t, km - 0.1, a2, gold=False, color=WHITE)
    # ---------------------------------------------------------------- H03：被速度裹挟——曲线一次次归零
    a3 = win(t, h3 - 0.15, h4 + 0.6, 0.4, 0.6)
    x0, x1, yb, Hc = 120, 960, 1290, 520
    if a3 > 0:
        u = max(t - h3, 0.0)
        r = np.random.default_rng(11)
        ys = r.uniform(400, 1400, 60); sp = r.uniform(0.6, 1.6, 60); xo = r.uniform(0, 1, 60)
        for i in range(60):                                           # 掠过的速度线
            x = ((xo[i] + u * 0.6 * sp[i]) % 1.0) * (W + 300) - 150
            V.line(F, [(x - 160 * sp[i], ys[i]), (x, ys[i])], CYAN if i % 4 else WHITE, 1.0, a3 * 0.20 * (1 - 0.6 * smooth((t - h4) / 0.6)), 0.2)
        put_text(F, '诱惑二', 150, 430, 30, 'sans', RED_S, a3 * (1 - smooth((t - h4) / 0.4)), 300, 'left', shadow=0, track=4)
        V.rise(F, '被速度裹挟', 150, 486, 52, t, h3 + 0.1, 'serif', WHITE, a3 * (1 - smooth((t - h4) / 0.4)), align='left')
        V.line(F, [(x0, yb), (x1, yb)], V.DIM, 1.2, a3 * 0.7, 0)
        # 每个「风口」：指数上升 → 切换时断掉归零
        k_starts, k_ends = t3.gh_breaks()                           # 越切越快
        k_stop = k_ends[-1]
        span = (x1 - x0) / 4
        for j, ks in enumerate(k_starts):
            if t < ks: break
            ke = k_ends[j]
            f = ease_out(clamp01((min(t, ke) - ks) / max(ke - ks, 0.3)) ** 0.8)
            xa = x0 + j * span
            xs = np.linspace(0, f * 0.86, 40)
            yv = Hc * 0.42 * (np.exp(2.4 * xs) - 1) / (math.exp(2.4 * 0.86) - 1)
            pts = np.c_[xa + xs * span, yb - yv]
            broke = t >= ke
            V.line(F, pts, GOLD_HI if not broke else GOLD * 0.55, 2.6, a3, 0.7)
            put_text(F, '风口', xa + span * 0.43, yb + 34, 24, 'sans', V.DIM, a3 * smooth(f / 0.3), 200, shadow=0)
            if broke:
                kb = t - ke
                xe, ye = pts[-1]
                V.line(F, [(xe, ye), (xe, ye + (yb - ye) * ease_out(clamp01(kb / 0.18)))], RED_S, 3.0, a3, 1.0)
                if kb < 0.6:
                    F += np.float32(0.05 * (1 - kb / 0.6)) * np.array([1.0, 0.3, 0.25], np.float32)
                rr = np.random.default_rng(j)
                n = 40
                sx = xe + rr.normal(0, 14, n) + rr.normal(0, 60, n) * min(kb, 1.2)
                sy = ye + rr.uniform(-10, 10, n) + 520 * min(kb, 1.2) ** 2 * rr.uniform(0.5, 1.2, n)
                splat(F, sx.astype(np.float32), sy.astype(np.float32), np.full(n, 1.8, np.float32), RED_S * 1.2, a3 * clamp01(1 - kb / 1.2))
                V.dot(F, xe, yb, 6, RED_S, a3 * 0.9, 1.0)
        # 失去的部分：本该连续复利的虚线（与下面 H04 的金色曲线同一条）
        if t > k_stop - 0.1:
            gu = ease_out(clamp01((t - k_stop + 0.1) / 1.2))
            xs = np.linspace(0, gu, 80)
            gy = yb - Hc * (np.exp(3.0 * xs) - 1) / (math.e ** 3 - 1)
            for i in range(0, 79, 2):
                V.line(F, [(x0 + xs[i] * (x1 - x0), gy[i]), (x0 + xs[i + 1] * (x1 - x0), gy[i + 1])], GOLD, 1.6, a3 * 0.6 * (1 - smooth((t - h4) / 0.5)), 0.3)
            kq = wt('H03', '复利的中断')
            ta = a3 * (1 - smooth((t - h4 + 0.2) / 0.4))
            V.slam(F, '每一次失去', W / 2, 640, 92, t, k_stop - 0.05, ta, gold=False, color=RED_S)
            if t > kq - 0.1:
                V.rise(F, '都是复利的中断', W / 2, 760, 60, t, kq - 0.1, 'serif', WHITE, ta)
    # ---------------------------------------------------------------- H04：守住已有的，让人生复利
    a4 = win(t, h4 - 0.1, end + 0.05, 0.5, 0.35)
    if a4 > 0:
        V.rise(F, '所以在 AI 时代，复利反而成了', W / 2, 470, 44, t, h4 + 0.05, 'serif_m', V.INK_T, a4)
        V.slam(F, '最稀缺的能力', W / 2, 590, 104, t, wt('H04', '最稀缺'), a4)
        kh = wt('H04', '守住已有的'); kl = wt('H04', '让人生复利')
        if t > h4 + 0.2:
            u = ease_io(clamp01((t - h4 - 0.2) / max(kl - h4 + 0.2, 1.0)))     # 从「所以」开始画，到「让人生复利」画满
            xs = np.linspace(0, u, 120)
            gy = yb - Hc * (np.exp(3.0 * xs) - 1) / (math.e ** 3 - 1)
            pts = np.c_[x0 + xs * (x1 - x0), gy]
            gs = np.linspace(u, 1, 60)                               # 还没画到的部分：沿用上一句「本该如此」的虚线，金线把它一点点填满
            gq = np.c_[x0 + gs * (x1 - x0), yb - Hc * (np.exp(3.0 * gs) - 1) / (math.e ** 3 - 1)]
            for i in range(0, 59, 2):
                V.line(F, [gq[i], gq[i + 1]], GOLD, 1.6, a4 * 0.45, 0.3)
            V.fill_poly(F, list(map(tuple, pts)) + [(pts[-1, 0], yb), (x0, yb)], GOLD * 0.30, a4, top=float(gy.min()), bottom=yb, grad=(0.9, 0.0))
            V.line(F, pts, GOLD_HI, 3.4, a4, 1.0)
            V.dot(F, pts[-1, 0], pts[-1, 1], 4 + 5 * smooth(u / 0.3), GOLD_HI, a4, 1.0 + 0.6 * smooth(u / 0.3))
            r = np.random.default_rng(5); n = 50                     # 彗星尾
            back = r.uniform(0, 0.25, n)
            q = np.c_[x0 + np.clip(u - back, 0, 1) * (x1 - x0), yb - Hc * (np.exp(3.0 * np.clip(u - back, 0, 1)) - 1) / (math.e ** 3 - 1)]
            splat(F, (q[:, 0] + r.normal(0, 6, n)).astype(np.float32), (q[:, 1] + r.normal(0, 6, n) - 30 * back).astype(np.float32),
                  np.full(n, 1.6, np.float32), GOLD_HI, a4 * (1 - back / 0.25) * 0.8)
            V.line(F, [(x0, yb), (x1, yb)], V.DIM, 1.2, a4 * 0.6, 0)
            if t > kh - 0.05:
                V.slam(F, '守住已有的，', 400, 930, 76, t, kh - 0.05, a4, gold=False, color=WHITE)    # 曲线左上方的空白处
        if t > kl - 0.1:
            ku = t - kl
            if ku < 1.1:
                V.line(F, circle(x1, yb - Hc, 20 + 420 * ease_out(ku / 1.1)), GOLD_HI, 3, a4 * (1 - ku / 1.1) ** 1.5, 1.0, closed=True)
            V.slam(F, '让人生复利', 400, 1050, 84, t, kl - 0.1, a4)


# ------------------------------------------------------------------ G2 / G3
def g2(F, t):
    a = win(t, st('S05') - 0.2, en('S05') + 0.4, 0.35, 0.45)
    V.slam(F, '复利', W / 2, 820, 220, t, wt('S05', '复利'), a)
    k = wt('S05', '但他说的')
    if t > k:
        put_text(F, '—— 但和很多人想的，不太一样', W / 2, 1060, 40, 'serif_m', V.INK_T, a * smooth((t - k) / 0.5), 980, shadow=0.5)


def g3(F, t):
    a = win(t, st('S06') - 0.2, en('S06') + 0.4, 0.35, 0.45)
    if a <= 0: return
    # 身后一条缓缓画出的复利曲线，曲线头上是一个跳动的问号；说到「朴素」时，曲线收成一个点
    u = ease_out(clamp01((t - st('S06') + 0.2) / 2.6))
    ks = wt('S06', '朴素')
    shrink = ease_io(clamp01((t - ks + 0.1) / 0.9))
    x0, x1, yb = 150, 930, 1330
    xs = np.linspace(shrink * u, u, 90)
    pts = np.c_[x0 + xs * (x1 - x0), yb - 420 * (np.exp(3 * xs) - 1) / (math.e ** 3 - 1)]
    V.line(F, pts, GOLD, 2.4, a * 0.75 * (1 - 0.5 * shrink), 0.7)
    hx, hy = pts[-1]
    if shrink < 1:
        V.dot(F, hx, hy, 8, GOLD_HI, a * (1 - shrink), 1.4)
        put_text(F, '?', hx + 46, hy - 64, 110, 'corm_sb', GOLD_HI, a * smooth((u - 0.6) / 0.3) * (1 - shrink) * (0.75 + 0.25 * math.sin(t * 5)), 200, shadow=0)
    if shrink > 0:
        V.dot(F, hx, hy, 5 + 4 * math.sin(clamp01((t - ks) / 1.2) * math.pi), WHITE, a * shrink, 1.2)
    V.rise(F, '复利最关键的是什么？', W / 2, 760, 76, t, st('S06'), 'serif', WHITE, a, glow=0.1)
    if t > ks - 0.1:
        V.rise(F, '答案，朴素得出人意料', W / 2, 880, 44, t, ks - 0.1, 'serif_m', GOLD_SUB * 1.2, a)


# ------------------------------------------------------------------ G4：不是更快，而是不失去 → 四种积累 → “来自一个人”
LIFE4 = [('知识', np.array([0.62, 0.80, 1.0], np.float32)), ('信任', np.array([1.0, 0.75, 0.42], np.float32)),
         ('智慧', np.array([0.85, 0.70, 1.0], np.float32)), ('健康', np.array([0.50, 0.95, 0.62], np.float32))]


def g4(F, t):
    a = win(t, st('S07') - 0.2, st('S08') - 0.05, 0.35, 0.35)
    if a > 0:
        k1 = wt('S07', '不是更快')
        V.rise(F, '不是', W / 2 - 250, 760, 60, t, k1, 'serif_m', V.DIM, a)
        V.rise(F, '更快', W / 2 - 250, 880, 110, t, k1 + 0.1, 'serif', V.DIM, a)
        s = clamp01((t - wt('S07', '而是') + 0.3) / 0.35)
        if s > 0:
            V.line(F, [(W / 2 - 380, 880), (W / 2 - 380 + 260 * s, 880)], RED_S, 5, a, 0.6)
        V.rise(F, '而是', W / 2 + 230, 760, 60, t, wt('S07', '而是'), 'serif_m', V.INK_T, a)
        V.slam(F, '不失去', W / 2 + 230, 880, 120, t, wt('S07', '不失去'), a)
    a = win(t, st('S08') - 0.2, st('H01') - 0.15, 0.35, 0.35)
    if a > 0:
        lose_t = wt('S08', '失去')
        for i, (name, col) in enumerate(LIFE4):
            x = 180 + i * 240
            ti = wt('S08', name)
            ai = a * smooth((t - ti + 0.2) / 0.35)
            if ai <= 0: continue
            g = clamp01((t - ti) / 3.0)
            n = 1 + int(g * 9)
            broken = (i == 1) and t > lose_t
            for k in range(n):
                y = 1150 - k * 52
                fall = clamp01((t - lose_t - k * 0.04) / 0.6) if broken else 0
                al = ai * (1 - fall)
                if al <= 0.01: continue
                pts = [(x - 80, y - 20 + 300 * fall ** 2), (x + 80, y - 20 + 300 * fall ** 2), (x + 80, y + 20 + 300 * fall ** 2), (x - 80, y + 20 + 300 * fall ** 2)]
                V.fill_poly(F, pts, col * 0.35, al)
                V.line(F, pts, col, 1.4, al * 0.9, 0.5, closed=True)
            put_text(F, name, x, 1240, 42, 'serif', col * 1.1, ai, 300, shadow=0.5)
        if t > lose_t:
            put_text(F, '一旦失去，从头再来', W / 1.0 / 2, 520, 50, 'serif_m', RED_S * 1.1, a * smooth((t - lose_t) / 0.4), 980, shadow=0.5)
        else:
            put_text(F, '一年一年地叠加', W / 2, 520, 50, 'serif_m', GOLD_HI, a * smooth((t - wt('S08', '叠加')) / 0.4), 980, shadow=0.5)
    a = win(t, st('S09') - 0.2, t3.seg('LT')['t0'] + 0.3, 0.35, 0.3)
    if a > 0:
        still(F, 'MU', 3.0, W / 2, 800, 760, a * (0.3 + 0.7 * smooth((t - wt('S09', '来自一个人')) / 0.6)), t=t, t0=st('S09'), dur=4,
              dim=0.35 + 0.2 * smooth((t - wt('S09', '来自一个人')) / 0.6))           # 先暗暗地出现，说到「来自一个人」再亮起
        V.rise(F, '这套人生观，来自一个人', W / 2, 1230, 54, t, st('S09'), 'serif', V.INK_T, a)
    gh(F, t)


def g4_mood(t):
    """讲 AI 的那几句转为冷色，讲完回到暖色"""
    return ('warm', 'cool', smooth((t - st('H01') + 0.4) / 0.8) * (1 - smooth((t - st('H04') - 0.5) / 1.5)))


# ------------------------------------------------------------------ G5：芒格与巴菲特 → 1999 年的问题
def g5(F, t):
    a = win(t, st('S10') - 0.2, st('S11') - 0.05, 0.4, 0.35)
    if a > 0:
        still(F, 'BB', 0.6, W / 2, 760, 980, a, t=t, t0=st('S10'), zoom=(1.0, 1.12), dur=8)
        put_text(F, '查理·芒格  ×  沃伦·巴菲特', W / 2, 1110, 46, 'serif', GOLD, a * smooth((t - wt('S10', '沃伦')) / 0.5), 980, shadow=0.6)
        put_text(F, '伯克希尔·哈撒韦股东大会 · 半个多世纪', W / 2, 1180, 28, 'sans', V.INK_T, a * smooth((t - wt('S10', '半个多世纪')) / 0.5), 980, shadow=0.6)
    a = win(t, st('S11') - 0.2, t3.seg('BB')['t0'] + 0.3, 0.4, 0.3)
    if a > 0:
        V.bracket(F, 90, 560, W - 90, 1060, GOLD, a, plate=0.5)
        put_text(F, '1999 · 伯克希尔股东大会 · 股东提问', W / 2, 620, 28, 'sans', GOLD_SUB * 1.15, a, 900, track=3, shadow=0)
        V.rise(F, '如果你三十出头、从头再来，', W / 2, 760, 56, t, wt('S11', '如果你'), 'serif', WHITE, a)
        V.rise(F, '会怎么做？', W / 2, 870, 56, t, wt('S11', '会怎么做'), 'serif', WHITE, a)
        put_text(F, '"How can I make $30 billion?"', W / 2, 980, 30, 'corm', V.DIM, a * smooth((t - wt('S11', '会怎么做')) / 0.6), 900, shadow=0)


# ------------------------------------------------------------------ G6：雪球不能散 → LTCM
def g6(F, t):
    a = win(t, st('S12') - 0.2, st('S13') - 0.05, 0.35, 0.35)
    if a > 0:
        u = clamp01((t - st('S12')) / max(en('S12') - st('S12'), 0.5))
        # 一道长坡：雪球（金色粒子球）沿坡滚下并变大，坡底前散开的虚影是“半路散掉”
        p0, p1 = np.array([140, 560.0]), np.array([940, 1180.0])
        V.line(F, [p0, p1], V.DIM, 2, a * 0.7, 0.2)
        pos = p0 + (p1 - p0) * ease_io(u)
        r = 18 + 70 * u
        rng = np.random.default_rng(11)
        P = rng.normal(0, 1, (500, 2)); P /= np.maximum(np.linalg.norm(P, axis=1, keepdims=True), 1e-3)
        P *= np.sqrt(rng.uniform(0, 1, (500, 1))) * r
        rot = t * 3
        c, s_ = math.cos(rot), math.sin(rot)
        P = P @ np.array([[c, -s_], [s_, c]], np.float32)
        splat(F, (pos[0] + P[:, 0]).astype(np.float32), (pos[1] - r + P[:, 1]).astype(np.float32), np.full(500, 1.4, np.float32), GOLD_HI, a * 0.55)
        V.dot(F, pos[0], pos[1] - r, r * 0.5, GOLD * 0.6, a * 0.5, 1.0)
        put_text(F, '坡要够长', 300, 1300, 54, 'serif', V.INK_T, a * smooth((t - st('S12')) / 0.4), 600, shadow=0.5)
        put_text(F, '雪球不能散', 780, 1300, 54, 'serif', GOLD, a * smooth((t - wt('S12', '雪球')) / 0.4), 600, shadow=0.5)
    a = win(t, st('S13') - 0.2, st('S14') - 0.05, 0.35, 0.35)
    if a > 0:
        V.bracket(F, 80, 420, W - 80, 1330, RED_S * 0.9, a, plate=0.5)
        put_text(F, '1998', W / 2, 500, 40, 'mono', RED_S, a, 400, shadow=0)
        V.rise(F, '长期资本管理公司（LTCM）', W / 2, 590, 50, t, st('S13'), 'serif', WHITE, a)
        tags = [('华尔街顶尖交易员', '华尔街顶尖'), ('两位诺贝尔经济学奖得主', '诺贝尔'), ('高杠杆', '高杠杆')]
        for i, (txt, kw) in enumerate(tags):
            ti = wt('S13', kw)
            put_text(F, txt, W / 2, 690 + i * 64, 36, 'sans', V.INK_T if i < 2 else RED_S, a * smooth((t - ti) / 0.4), 900, shadow=0)
        # 资本曲线：先稳步上升，然后几个月内断崖式下跌（示意）
        k = wt('S13', '几个月')
        x0, x1, yb, yt = 170, W - 170, 1250, 920
        xs = np.linspace(x0, x1, 120)
        frac = np.linspace(0, 1, 120)
        val = np.where(frac < 0.72, 0.55 + 0.4 * frac / 0.72, 0.95 * np.exp(-((frac - 0.72) / 0.07) ** 2 * 1.3))
        val = np.maximum(val, 0.03)
        draw = clamp01((t - st('S13') - 1.0) / max(k - st('S13') - 0.6, 0.5)) * 0.72 + 0.28 * clamp01((t - k) / 1.2)
        nn = max(2, int(draw * 120))
        pts = np.c_[xs[:nn], yb - val[:nn] * (yb - yt)]
        crash = t > k
        V.line(F, pts, RED_S if crash and nn > 86 else GOLD_HI, 2.4, a, 0.8)
        V.line(F, [(x0, yb), (x1, yb)], V.DIM, 1, a * 0.5, 0)
        if t > k + 0.6:
            V.slam(F, '几个月，几乎赔光', W / 2, 1180, 46, t, k + 0.6, a, gold=False, color=RED_S, name='serif')
        put_text(F, '曲线为示意', x1, yb + 30, 20, 'sans_l', V.DIM, a * 0.8, 300, 'right', shadow=0)
    a = win(t, st('S14') - 0.2, t3.seg('BA')['t0'] + 0.3, 0.3, 0.3)
    if a > 0:
        V.rise(F, '巴菲特这样评价', W / 2, 860, 64, t, st('S14'), 'serif', GOLD, a)


# ------------------------------------------------------------------ G7：伯克希尔四次大跌（2017 年致股东信）
DIPS = [('1973.03–1975.01', -59.1), ('1987.10.02–10.27', -37.1), ('1998.06.19–2000.03.10', -48.9), ('2008.09.19–2009.03.05', -50.7)]


def g7(F, t):
    a = win(t, st('S15') - 0.2, st('S16') - 0.05, 0.35, 0.35)
    if a > 0:
        V.rise(F, '市场下跌，', W / 2, 800, 80, t, st('S15'), 'serif', WHITE, a)
        V.slam(F, '算不算失去？', W / 2, 930, 90, t, wt('S15', '算不算'), a)
    a = win(t, st('S16') - 0.2, t3.seg('MB')['t0'] + 0.3, 0.35, 0.3)
    if a > 0:
        V.bracket(F, 80, 470, W - 80, 1330, GOLD, a, plate=0.5)
        put_text(F, '伯克希尔股价的四次大跌', W / 2, 540, 46, 'serif', GOLD, a, 900, shadow=0.4)
        put_text(F, '资料：伯克希尔 2017 年致股东信', W / 2, 600, 22, 'sans_l', V.DIM, a, 900, shadow=0)
        k0 = wt('S16', '四次')
        for i, (span, pct) in enumerate(DIPS):
            ti = k0 + i * 0.35
            g = ease_out(clamp01((t - ti) / 0.6))
            x = 210 + i * 220
            h = 560 * (-pct) / 60 * g
            y0 = 700
            deepest = i == 0 and t > wt('S16', '最深')
            col = RED_S * (1.25 if deepest else 0.85)
            V.fill_poly(F, [(x - 55, y0), (x + 55, y0), (x + 55, y0 + h), (x - 55, y0 + h)], col * 0.45, a, top=y0, bottom=y0 + h, grad=(0.9, 0.35))
            V.line(F, [(x - 55, y0 + h), (x + 55, y0 + h)], col, 2.2, a * g, 0.8)
            if g > 0.05:
                put_text(F, f'{pct:.1f}%', x, y0 + h + 40, 40 if deepest else 34, 'mono', col * 1.1, a * g, 300, shadow=0)
                put_text(F, span.split('–')[0][:4], x, y0 - 34, 26, 'mono', V.DIM, a * g, 300, shadow=0)
        V.line(F, [(130, 700), (W - 130, 700)], V.DIM, 1.2, a * 0.7, 0)


# ------------------------------------------------------------------ G8：暂时 vs 永久 → 人自己的复利
def g8(F, t):
    a = win(t, st('S17') - 0.2, st('S19') - 0.05, 0.35, 0.35)
    if a > 0:
        # 价值线（稳步上升，金色）与价格线（围绕价值大幅波动，蓝色）
        x0, x1, yb = 130, W - 130, 1240
        u_draw = clamp01((t - st('S17')) / 4.0)
        xs = np.linspace(x0, x1, 240); fr = np.linspace(0, 1, 240)
        value = 0.2 + 0.65 * fr
        price = value * (1 + 0.18 * np.sin(fr * 15) - 0.42 * np.exp(-((fr - 0.45) / 0.07) ** 2))
        nn = max(2, int(u_draw * 240))
        scale = 620
        V.line(F, np.c_[xs[:nn], yb - value[:nn] * scale], GOLD, 3, a, 0.8)
        V.line(F, np.c_[xs[:nn], yb - price[:nn] * scale], CYAN, 2, a * 0.85, 0.5)
        V.line(F, [(x0, yb), (x1, yb)], V.DIM, 1, a * 0.5, 0)
        put_text(F, '价值', x0 + 10, yb - value[0] * scale - 50, 32, 'serif', GOLD, a * smooth(u_draw * 4), 300, 'left', shadow=0)
        put_text(F, '价格', x0 + 10, yb - price[0] * scale + 40, 32, 'serif', CYAN, a * smooth(u_draw * 4), 300, 'left', shadow=0)
        ka = wt('S17', '暂时')
        put_text(F, '暂时的下跌', W / 2 - 220, 500, 52, 'serif', CYAN, a * smooth((t - ka) / 0.4), 500, shadow=0.5)
        kp = wt('S17', '真正的损失')
        put_text(F, '真正的损失', W / 2 + 220, 500, 52, 'serif', RED_S, a * smooth((t - kp) / 0.4), 500, shadow=0.5)
        put_text(F, '价值被毁  ·  低点被迫卖出', W / 2 + 220, 570, 28, 'sans', V.INK_T, a * smooth((t - wt('S17', '被迫卖出')) / 0.4), 600, shadow=0)
        k18 = st('S18')
        if t > k18:
            V.slam(F, '复利没有中断', W / 2, 700, 64, t, wt('S18', '复利'), a)
    a = win(t, st('S19') - 0.2, t3.seg('MU')['t0'] + 0.3, 0.35, 0.3)
    if a > 0:
        still(F, 'MU', 1.0, W / 2, 780, 820, a * 0.9, t=t, t0=st('S19'), dur=4, dim=0.7)
        V.rise(F, '最重要的复利', W / 2, 1180, 64, t, wt('S19', '最重要的复利'), 'serif', GOLD, a)
        V.rise(F, '发生在一个人自己身上', W / 2, 1270, 44, t, wt('S19', '发生在'), 'serif_m', V.INK_T, a)


def g9(F, t):
    a = win(t, st('S20') - 0.2, t3.seg('MT')['t0'] + 0.3, 0.3, 0.3)
    if a > 0:
        V.slam(F, '信任', W / 2, 780, 180, t, st('S20') + 0.05, a)
        put_text(F, '"…a seamless web of deserved trust."  —— 李录引用芒格', W / 2, 1010, 30, 'corm', V.INK_T,
                 a * smooth((t - wt('S20', '那句话')) / 0.5), 980, shadow=0.4)


SCENES = {'G1': (g1, 'cool'), 'G2': (g2, 'warm'), 'G3': (g3, 'warm'), 'G4': (g4, g4_mood), 'G5': (g5, 'neutral'),
          'G6': (g6, 'neutral'), 'G7': (g7, 'neutral'), 'G8': (g8, 'neutral'), 'G9': (g9, 'warm')}
