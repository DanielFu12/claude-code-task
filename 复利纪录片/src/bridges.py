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
    img = FT.inv_tonemap(big[oy:oy + h, ox:ox + w]) * dim
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
    a4 = win(t, st('S04') - 0.2, t3.seg('GH')['t0'] + 0.35, 0.4, 0.35)
    if a4 > 0:
        V.rise(F, '在一个越来越快的时代', W / 2, 760, 54, t, st('S04'), 'serif_m', V.INK_T, a4)
        k = wt('S04', '什么才值得')
        V.rise(F, '什么才值得我们', W / 2, 880, 62, t, k, 'serif', V.INK_T, a4)
        V.slam(F, '花几十年去积累？', W / 2, 1000, 84, t, wt('S04', '几十年'), a4)


# ------------------------------------------------------------------ GH：AI 时代的两种诱惑 → 守住复利（第四版新增，引出片名）
def ai_chip(F, x, y, r, a, glow=0.6, label='AI'):
    pts = [(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r)]
    V.fill_poly(F, pts, CYAN * 0.18, a)
    V.line(F, pts, CYAN, 2.0, a, glow, closed=True)
    for k in range(4):                                   # 芯片引脚
        d = -r * 0.6 + k * r * 0.4
        for (x0, y0, x1, y1) in ((x + d, y - r, x + d, y - r - 16), (x + d, y + r, x + d, y + r + 16),
                                 (x - r, y + d, x - r - 16, y + d), (x + r, y + d, x + r + 16, y + d)):
            V.line(F, [(x0, y0), (x1, y1)], CYAN, 1.4, a * 0.8, 0.3)
    put_text(F, label, x, y, int(r * 0.9), 'mono', WHITE, a, 400, shadow=0, glow=0.3)


def gh(F, t):
    # H01：AI 越强大（芯片 + 扩散的波纹），诱惑也越大
    a1 = win(t, st('H01') - 0.3, st('H02') + 0.1, 0.4, 0.45)
    if a1 > 0:
        u = t - st('H01')
        grow = ease_out(clamp01((t - wt('H01', '越强大')) / 0.8))
        ai_chip(F, W / 2, 760, 90 + 40 * grow, a1, 0.6 + 0.6 * grow)
        for i in range(4):
            ph = (u * 0.9 + i / 4) % 1.0
            V.line(F, AN_circle(W / 2, 760, 150 + 420 * ph), CYAN, 1.6, a1 * (1 - ph) * 0.6 * smooth(u / 0.4), 0.6, closed=True)
        V.slam(F, '诱惑也越大', W / 2, 1100, 96, t, wt('H01', '诱惑'), a1)
    # H02：外包思考——思考流向 AI，自己的积累停在 0
    a2b = win(t, st('H02') - 0.2, st('H04') + 0.1, 0.4, 0.45)
    a2 = a2b * (1 - 0.45 * smooth((t - st('H03')) / 0.5))       # 第二种诱惑出现时，第一张卡片退后
    if a2 > 0:
        V.bracket(F, 90, 420, W - 90, 880, CYAN, a2, plate=0.45)
        V.rise(F, '①  把思考外包给 AI', W / 2, 488, 46, t, st('H02'), 'serif', WHITE, a2)
        k = wt('H02', '外包')
        pa = a2 * smooth((t - k + 0.2) / 0.4)
        if pa > 0:
            V.dot(F, 290, 640, 52, GOLD * 0.5, pa * 0.5, 0.6)
            V.line(F, AN_circle(290, 640, 52), GOLD, 2, pa, 0.5, closed=True)
            put_text(F, '你', 290, 640, 44, 'serif', WHITE, pa, 200, shadow=0)
            ai_chip(F, 790, 640, 52, pa, 0.5)
            for i in range(6):                           # 一串「思考」流向 AI
                ph = ((t - k) * 0.8 + i / 6) % 1.0
                x = 360 + 350 * ph
                V.dot(F, x, 640 + math.sin(ph * math.pi * 2 + i) * 10, 6, GOLD_HI, pa * math.sin(ph * math.pi), 1.2)
            V.dashed(F, (360, 640), (710, 640), V.DIM, 1.2, pa * 0.6, phase=(t - k) * 40)
        k2 = wt('H02', '不再积累')
        ka = a2 * smooth((t - k2 + 0.2) / 0.4)
        if ka > 0:
            V.line(F, [(200, 790), (880, 790)], V.DIM, 1.4, ka * 0.8, 0.2)
            put_text(F, '自己的积累', 200, 752, 26, 'sans', V.DIM, ka, 400, 'left', shadow=0)
            put_text(F, '0', 900, 790, 30, 'mono', RED_S, ka, 100, 'left', shadow=0)
        if t > wt('H02', '没有积累') - 0.1:
            V.slam(F, '没有积累，谈何复利？', W / 2, 945, 56, t, wt('H02', '没有积累') - 0.1, a2b * (1 - smooth((t - st('H03') + 0.1) / 0.4)),
                   gold=False, color=WHITE)
    # H03：被速度裹挟——追风口、频繁切换，曲线一次次归零
    a3 = win(t, st('H03') - 0.2, st('H04') + 0.1, 0.4, 0.45)
    if a3 > 0:
        V.bracket(F, 90, 990, W - 90, 1450, RED_S * 0.9, a3, plate=0.45)
        V.rise(F, '②  被速度裹挟', W / 2, 1056, 46, t, st('H03'), 'serif', WHITE, a3)
        u = max(t - st('H03'), 0.0)
        r = np.random.default_rng(11)
        ys = r.uniform(1000, 1440, 40); sp = r.uniform(0.7, 1.4, 40); x0s = r.uniform(0, 1, 40)
        for i in range(40):                              # 掠过的速度线
            x = ((x0s[i] + u * 0.45 * sp[i]) % 1.0) * (W - 180) + 90
            V.line(F, [(x - 90 * sp[i], ys[i]), (x, ys[i])], CYAN, 1.0, a3 * 0.22, 0.2)
        x0, x1, yb = 170, 910, 1380
        V.line(F, [(x0, yb), (x1, yb)], V.DIM, 1.2, a3 * 0.7, 0)
        cyc = 1.35; nseg = 4
        tags = ['追风口', '切换', '再追', '再切换']
        prog = u / cyc
        for j in range(nseg):
            if prog < j: break
            f = clamp01(prog - j)
            xa = x0 + (x1 - x0) * j / nseg; xw = (x1 - x0) / nseg
            xs = np.linspace(0, f * 0.82, 30)
            pts = np.c_[xa + xs * xw, yb - 150 * (np.exp(2.2 * xs) - 1) / (np.exp(2.2 * 0.82) - 1)]
            V.line(F, pts, GOLD_HI, 2.4, a3, 0.6)
            if f > 0.82:                                 # 断掉：归零
                xe = xa + 0.82 * xw
                cut = clamp01((f - 0.82) / 0.1)
                V.line(F, [(xe, yb - 150), (xe, yb - 150 + 150 * cut)], RED_S, 2.4, a3 * 0.9, 0.8)
                V.line(F, [(xe - 12, yb - 87), (xe + 12, yb - 63)], RED_S, 3, a3 * cut, 0.8)
                V.line(F, [(xe + 12, yb - 87), (xe - 12, yb - 63)], RED_S, 3, a3 * cut, 0.8)
            put_text(F, tags[j], xa + xw * 0.4, yb + 30, 24, 'sans', V.DIM, a3 * smooth(f / 0.3), 300, shadow=0)
        k3 = wt('H03', '每一次失去')
        if t > k3 - 0.1:
            V.rise(F, '每一次失去，都是复利的中断', W / 2, 1150, 44, t, k3 - 0.1, 'serif', RED_S, a3)
    # H04：所以在 AI 时代，复利反而成了最稀缺的能力：守住已有的，让人生复利
    a4 = win(t, st('H04') - 0.1, t3.seg('title')['t0'] + 0.05, 0.5, 0.25)
    if a4 > 0:
        V.rise(F, '所以在 AI 时代，复利反而成了', W / 2, 560, 46, t, st('H04') + 0.1, 'serif_m', V.INK_T, a4)
        V.slam(F, '最稀缺的能力', W / 2, 680, 100, t, wt('H04', '最稀缺'), a4)
        k = wt('H04', '守住已有的')
        if t > k - 0.3:
            u = clamp01((t - k + 0.3) / max(t3.seg('title')['t0'] - k, 1.5))
            x0, x1, yb = 190, 890, 1180
            xs = np.linspace(0, ease_out(u), 80)
            ys = yb - 330 * (np.exp(3.0 * xs) - 1) / (np.exp(3.0) - 1)
            pts = np.c_[x0 + xs * (x1 - x0), ys]
            V.fill_poly(F, list(map(tuple, pts)) + [(pts[-1, 0], yb), (x0, yb)], GOLD * 0.25, a4, top=float(ys.min()), bottom=yb, grad=(0.9, 0.0))
            V.line(F, pts, GOLD_HI, 3, a4, 0.9)
            V.dot(F, pts[-1, 0], pts[-1, 1], 9, GOLD_HI, a4, 1.6)
            V.line(F, [(x0, yb), (x1, yb)], V.DIM, 1.2, a4 * 0.6, 0)
            V.slam(F, '守住已有的', W / 2, 1290, 76, t, k, a4, gold=False, color=WHITE)
        if t > wt('H04', '让人生复利') - 0.1:
            V.slam(F, '让人生复利', W / 2, 1400, 64, t, wt('H04', '让人生复利') - 0.1, a4)


def AN_circle(cx, cy, r, n=96):
    th = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.c_[cx + r * np.cos(th), cy + r * np.sin(th)].astype(np.float32)


# ------------------------------------------------------------------ G2 / G3
def g2(F, t):
    a = win(t, st('S05') - 0.2, en('S05') + 0.4, 0.35, 0.45)
    V.slam(F, '复利', W / 2, 820, 220, t, wt('S05', '复利'), a)
    k = wt('S05', '但他说的')
    if t > k:
        put_text(F, '—— 但和很多人想的，不太一样', W / 2, 1060, 40, 'serif_m', V.INK_T, a * smooth((t - k) / 0.5), 980, shadow=0.5)


def g3(F, t):
    a = win(t, st('S06') - 0.2, en('S06') + 0.4, 0.35, 0.45)
    V.rise(F, '复利最关键的是什么？', W / 2, 860, 76, t, st('S06'), 'serif', WHITE, a, glow=0.1)


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
    a = win(t, st('S08') - 0.2, st('S09') - 0.05, 0.35, 0.35)
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
        still(F, 'MU', 3.0, W / 2, 800, 760, a * smooth((t - wt('S09', '来自一个人')) / 0.6), t=t, t0=st('S09'), dur=4, dim=0.55)
        V.rise(F, '这套人生观，来自一个人', W / 2, 1230, 54, t, st('S09'), 'serif', V.INK_T, a)


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


SCENES = {'G1': (g1, 'cool'), 'GH': (gh, 'cool'), 'G2': (g2, 'warm'), 'G3': (g3, 'warm'), 'G4': (g4, 'warm'), 'G5': (g5, 'neutral'),
          'G6': (g6, 'neutral'), 'G7': (g7, 'neutral'), 'G8': (g8, 'neutral'), 'G9': (g9, 'warm')}
