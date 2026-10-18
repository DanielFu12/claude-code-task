"""分镜：每个 sc_* 返回该时刻的 HDR 帧（未做后期）。时间均为成片时间（秒）。"""
import math
import numpy as np, cv2
from engine import *
from common import *
from script import QUOTES, NARRATION, CAPTIONS, MATH, DATA, ASSUMPTIONS, TITLE, SUBTITLE
from timeline import A, START, C0, BEAT, dur
import os

ENV = np.load(os.path.join(ROOT, 'assets', 'music', 'env.npz'))
def kick(t):
    i = int(t * 30)
    return float(ENV['low'][min(max(i, 0), len(ENV['low']) - 1)])
def onset(t):
    i = int(t * 30)
    return float(ENV['onset'][min(max(i, 0), len(ENV['onset']) - 1)])

def word_time(nid, word):
    """旁白中某个词大约被读到的时刻（按字数比例估算）"""
    s = NARRATION[nid]; k = s.find(word)
    return START[nid] + dur(nid) * (k / max(len(s), 1))

PHOTO = os.path.join(ROOT, 'assets', 'photos')
TALK_LEN = 5300.0   # 只用于时间轴比例


# ================================================================== SC1 冷开场：加速（0 – 32）
TUN_N = 7000
_r = np.random.default_rng(5)
TUN_ANG = _r.uniform(0, 2 * np.pi, TUN_N).astype(np.float32)
TUN_RAD = (3.5 + _r.gamma(2.0, 4.0, TUN_N)).astype(np.float32)
TUN_Z0 = _r.uniform(0, 220, TUN_N).astype(np.float32)
TUN_COL = np.where(_r.uniform(0, 1, (TUN_N, 1)) < 0.12, np.array([1.0, 0.8, 0.5]), np.array([0.45, 0.75, 1.0])).astype(np.float32)
TUN_COL *= _r.uniform(0.5, 1.2, (TUN_N, 1)).astype(np.float32)
PLATES = [(_r.uniform(-7, 7), _r.uniform(-9, 9), _r.uniform(0, 220), _r.uniform(-0.6, 0.6), _r.uniform(-0.5, 0.5)) for _ in range(9)]


def tunnel_speed(t):
    if t < 22: return 8 + 52 * (t / 22) ** 1.6
    if t < 28.5: return 60 * (1 - smooth((t - 22) / 6.5)) + 1.0
    return 1.0


@lru_cache(None)
def _tunnel_dist():
    ts = np.arange(0, 34, 1 / 120)
    v = np.array([tunnel_speed(x) for x in ts])
    return ts, np.cumsum(v) / 120


def tunnel_pos(t):
    ts, d = _tunnel_dist()
    return float(np.interp(t, ts, d))


def sc_open(t):
    F = backdrop(t, c1=(0.01, 0.015, 0.035), c2=(0.02, 0.05, 0.12), neb=(0.06, 0.16, 0.38), neb_amt=0.55, drift=2.0)
    pulse = kick(t)
    imp = smooth((t - 30.9) / 1.0)                      # 31 秒起向中心坍缩
    cam = Camera((0, 0, 0), (0, 0, 1), fov=62 - 8 * imp, roll=0.05 * math.sin(t * 0.4))
    s = tunnel_pos(t)
    v = tunnel_speed(t)
    z = (TUN_Z0 - s) % 220 + 0.5
    P = np.stack([np.cos(TUN_ANG) * TUN_RAD * (1 - 0.9 * imp), np.sin(TUN_ANG) * TUN_RAD * (1 - 0.9 * imp), z], 1)
    amp = 0.55 + 0.35 * pulse + 1.2 * imp
    # 拖尾：沿运动方向多次采样
    nst = int(np.clip(v / 6, 1, 7))
    for k in range(nst):
        Q = P.copy(); Q[:, 2] += k * v * 0.012
        particles3d(F, cam, Q, TUN_COL, size=0.05, alpha=amp * (1 - k / (nst + 1)) / max(1, nst * 0.45), focus=25, dof=0.05)
    # 飞过的玻璃片（知识、模型的隐喻）
    boxes = []
    for (px, py, pz0, rx, ry) in PLATES:
        pz = (pz0 - s) % 220 + 2
        if pz > 120: continue
        boxes.append(make_box((px * (1 - imp), py * (1 - imp), pz), (1.6, 1.0, 0.03), (rx + t * 0.15, ry + t * 0.1, 0),
                              tint=(0.45, 0.75, 1.0), density=0.8, edge=0.8, opacity=0.9))
    F = render_boxes(F, cam, boxes, scale=0.5, t=t) if boxes else F

    # 关键词：迭代 / 贬值 / 消失 —— 出现后碎成粒子
    for w, col in (('迭代', CYAN), ('贬值', np.array([0.8, 0.85, 1.0])), ('消失', np.array([1.0, 0.55, 0.45]))):
        tw = word_time('N02', w) - 0.15
        u = t - tw
        if -0.1 < u < 2.4:
            word_burst(F, w, u, col)
    # 李录引语卡
    quote_card(F, QUOTES['Q_PACE'], t, 15.6, 22.2, y=640, tape=(18 * 60 + 18, TALK_LEN))
    # 问题
    q1 = win(t, 22.6, 31.4, 0.8, 0.5)
    if q1 > 0:
        put_text(F, '既然一切都在加速——', W / 2, 760, 66, 'serif_m', WHITE, q1, 980, reveal=clamp01((t - 22.6) / 1.4), glow=0.15)
    q2 = win(t, word_time('N04', '到底') - 0.2, 31.4, 0.6, 0.5)
    if q2 > 0:
        r = clamp01((t - word_time('N04', '到底') + 0.2) / 1.6)
        put_text(F, '什么，值得我们', W / 2, 900, 84, 'serif', np.array([1.0, 0.9, 0.7]), q2, 980, reveal=r, glow=0.25)
        put_text(F, '积累几十年？', W / 2, 1020, 104, 'serif', GOLD, q2, 980, reveal=clamp01(r * 1.3 - 0.3), glow=0.45)
    # 坍缩前的吸入感 + 31.9 白闪
    if t > 31.0:
        F *= 1 - 0.85 * smooth((t - 31.0) / 0.8)
        cy, cx = H / 2, W / 2
        yy, xx = np.ogrid[0:H, 0:W]
        F += (np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * (40 + 300 * (1 - imp)) ** 2)) * imp * 2.5)[..., None] * np.array([1, 0.85, 0.6], np.float32)
    return F


@lru_cache(None)
def _word_pts(w):
    return mask_points(w, 230, 'sans_b', 2600, W / 2, 1180)


def word_burst(F, w, u, col):
    col = np.asarray(col, np.float32)
    if u < 1.1:   # 文字本体 + 色差
        a = smooth(u / 0.18) * (1 - smooth((u - 0.85) / 0.25))
        sc = 1 + 0.06 * u
        for dx, c in ((-6, np.array([1, 0.2, 0.2])), (6, np.array([0.2, 0.5, 1.0])), (0, col)):
            put_text(F, w, W / 2 + dx * (1 - u), 1180, int(230 * sc), 'sans_b', c * (0.5 if dx else 1.0), a * (0.45 if dx else 1.0), 1000,
                     shadow=0, glow=0.4 if dx == 0 else 0)
    if u > 0.8:   # 碎裂成粒子，向镜头飞散
        P = _word_pts(w)
        k = u - 0.8
        rng = np.random.default_rng(len(w))
        vel = rng.normal(0, 1, (len(P), 2)).astype(np.float32) * 260 + np.array([0, -60], np.float32)
        xy = P + vel * k + (P - [W / 2, 1180]) * k * 1.5
        al = np.clip(1 - k / 1.5, 0, 1) * 0.9
        splat(F, xy[:, 0], xy[:, 1], np.full(len(P), 1.3 + k * 2, np.float32), col, al)


# ================================================================== SC2 标题（32 – 42.75）
_rb = np.random.default_rng(9)
BURST_N = 5000
BURST_DIR = _rb.normal(0, 1, (BURST_N, 3)).astype(np.float32)
BURST_DIR /= np.linalg.norm(BURST_DIR, axis=1, keepdims=True)
BURST_SPD = _rb.gamma(2.0, 6.0, (BURST_N, 1)).astype(np.float32)
BURST_COL = (GOLD[None, :] * _rb.uniform(0.5, 1.3, (BURST_N, 1))).astype(np.float32)


def sc_title(t):
    u = t - A['drop']
    F = backdrop(t, c1=(0.02, 0.016, 0.01), c2=(0.06, 0.045, 0.03), neb=(0.35, 0.24, 0.10), neb_amt=0.35 + 0.2 * math.exp(-u), drift=0.6)
    cam = Camera((0, 0, -30), (0, 0, 0), fov=50, roll=0)
    # 粒子爆发（阻尼）
    d = (1 - math.exp(-u * 1.6)) / 1.6
    P = BURST_DIR * BURST_SPD * d * 3.2
    P[:, 1] += -0.15 * u
    particles3d(F, cam, P, BURST_COL, size=0.06, alpha=0.9 * (0.35 + 0.65 * math.exp(-u * 0.8)), focus=30, dof=0.1)
    # 冲击波
    if u < 1.6:
        lay = np.zeros((H, W, 3), np.float32)
        ring(lay, W / 2, 960, 40 + 1400 * ease_out(u / 1.6), np.array([1.0, 0.85, 0.55]), 3 + 10 * (1 - u / 1.6), (1 - u / 1.6) ** 1.5, 1.2)
        F += lay
    # 闪白
    F += np.float32(1.3 * math.exp(-u * 10)) * np.array([1.0, 0.9, 0.75], np.float32)
    # 标题
    ta = win(t, A['drop'], A['calm'] - 0.6, 0.12, 0.8)
    rv = clamp01((u - 0.0) / 0.45)
    sweep = (u - 2.4) / 1.4
    gold_text(F, 'AI 越快，', W / 2, 800, 150, 'serif', ta, rv, glow=0.35 + 0.6 * math.exp(-u * 3), sweep=sweep, stagger=0.3)
    gold_text(F, '越要慢', W / 2, 990, 190, 'serif', ta, clamp01(rv * 1.6 - 0.6), glow=0.5 + 0.8 * math.exp(-u * 3), sweep=sweep - 0.15, stagger=0.3)
    sa = win(t, A['drop'] + 2.2, A['calm'] - 0.6, 0.8, 0.8)
    put_text(F, SUBTITLE, W / 2, 1170, 44, 'serif_m', np.array([0.95, 0.9, 0.8]), sa, 980, reveal=clamp01((u - 2.2) / 1.5), glow=0.1)
    ma = win(t, A['drop'] + 3.4, A['calm'] - 0.6, 0.8, 0.8)
    put_text(F, '李录  ·  巴菲特  ·  芒格', W / 2, 1265, 32, 'sans_l', GOLD_SUB * 1.2, ma, 900, track=6)
    lay = np.zeros((H, W, 3), np.float32)
    lw = 300 * ease_out(clamp01((u - 3.0) / 1.2))
    glow_line(lay, [(W / 2 - lw, 1222), (W / 2 + lw, 1222)], GOLD, 1.2, 0.4, ma * 0.7)
    F += lay
    da = win(t, A['drop'] + 4.5, A['calm'] - 0.6, 0.8, 0.8)
    footnote(F, '旁白为 AI 配音（Gemini TTS）  ·  大师引语均为原话，附本片中文译文与出处', da, y=1640, size=22)
    # 结尾压暗，过渡到沉静段
    F *= 1 - 0.9 * smooth((t - (A['calm'] - 0.9)) / 0.9)
    return F


# ================================================================== SC3 李录：复利的定义（42.75 – 93.3）
def stack_boxes(n_gold, t, base_y=0.0, flicker=None, tools=0.0, glow=1.0, slab=(2.1, 0.17, 2.1), gap=0.06, spin=0.0):
    """居中的玻璃层叠：n_gold 层金色（可为小数，最上一层按比例长出）"""
    boxes = []
    y = base_y
    full = int(n_gold)
    for k in range(int(math.ceil(n_gold))):
        f = 1.0 if k < full else n_gold - full
        th = slab[1] * ease_out(f)
        if th < 0.005: continue
        tint = GOLD * (0.75 + 0.25 * glow)
        boxes.append(make_box((0, y + th / 2, 0), (slab[0] / 2, th / 2, slab[2] / 2), (0, spin, 0), tint=tint,
                              density=0.9, edge=1.0 + 0.4 * glow, opacity=0.95 * min(1, f * 2)))
        y += th + gap
    if flicker is not None:   # 零和/短期：出现又消失的层
        for k, a in enumerate(flicker):
            if a <= 0.01: continue
            boxes.append(make_box((0, y + k * (slab[1] + gap) + slab[1] / 2, 0), (slab[0] / 2, slab[1] / 2, slab[2] / 2), (0, spin, 0),
                                  tint=CYAN, density=0.6, edge=0.9, opacity=a))
    return boxes, y


def sc_lilu(t):
    F = backdrop(t, c1=(0.01, 0.018, 0.04), c2=(0.03, 0.05, 0.10), neb=(0.08, 0.14, 0.30), neb_amt=0.35, drift=0.4)
    ang = 0.45 + 0.10 * (t - A['calm'])
    rise = smooth((t - A['build']) / 8.0)
    R = 14.5 - 1.0 * rise
    cam = Camera((math.sin(ang) * R, 3.2 + 2.5 * rise, -math.cos(ang) * R), (0, 0.85, 0), fov=40)
    dust(F, cam, t, color=(0.6, 0.75, 1.0), amt=0.35, focus=14, dof=0.12, n=5000)
    # 状态机
    t_use, t_know, t_core, t_n08 = 54.6, START['N06'], START['N07'], START['N08']
    n_gold = 0.0; flick = None
    if t < t_use:
        n_gold = 0
        flick = [0.25 + 0.1 * math.sin(t * 2 + k) for k in range(2)]
    elif t < t_know:
        n_gold = 0
        flick = []
        for k in range(4):      # 层出现又消失：积累不下来
            ph = ((t - t_use) * 1.2 + k * 0.37) % 1.0
            flick.append(math.sin(ph * math.pi) ** 2 * 0.9 if k < 3 else 0)
        flick = flick[:2]
    else:
        n_gold = min(10.0, (t - t_know - 0.6) / (BEAT * 1.5)) if t > t_know + 0.6 else 0
        n_gold = max(n_gold, 0)
    gl = 0.6 + 0.4 * kick(t) + (0.6 if t > t_core + 3 else 0)
    boxes, top = stack_boxes(n_gold, t, base_y=-1.2, flicker=flick, glow=gl, spin=0.0)
    # 工具（青色薄片）在 N08 中脱落
    if t > t_n08 - 2:
        for k in range(6):
            a_ = (k / 6) * 2 * math.pi + t * 0.15
            fall = max(0.0, t - (word_time('N08', '过时') + k * 0.25))
            y_ = 0.6 + (k % 3) * 0.9 - 2.5 * fall ** 2
            op = clamp01(1 - fall / 1.4) * smooth((t - t_n08 + 2) / 1.5)
            if op > 0.01:
                boxes.append(make_box((math.cos(a_) * 3.4, y_, math.sin(a_) * 3.4), (0.55, 0.36, 0.02), (0.2 * k + fall, a_, 0.3 * fall),
                                      tint=CYAN, density=0.6, edge=0.9, opacity=op))
    # 自上而下的体积光 + 地面光环（让沉静段也有呼吸感）
    xs_, ys_, _ = cam.project(np.array([[0, 6.0, 0], [0, -1.2, 0]], np.float32))
    q = np.zeros((H // 4, W // 4), np.float32)
    yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
    k_ = np.clip((yy - ys_[0] / 4) / max((ys_[1] - ys_[0]) / 4, 1), 0, 1)
    wid = 18 + 70 * k_
    q += np.exp(-((xx - xs_[0] / 4) / wid) ** 2) * k_ * (yy < ys_[1] / 4 + 4) * (0.10 + 0.05 * math.sin(t * 0.7))
    F += cv2.resize(cv2.GaussianBlur(q, (0, 0), 3), (W, H))[..., None] * np.array([0.75, 0.85, 1.0], np.float32) * (1 + min(n_gold / 10, 1) * np.array([0.6, 0.2, -0.3], np.float32))
    th_ = np.linspace(0, 2 * np.pi, 120)
    for rr, sp in ((2.4, 0.15), (3.3, -0.1)):
        ring3 = np.stack([np.cos(th_ + t * sp) * rr, np.full_like(th_, -1.22), np.sin(th_ + t * sp) * rr], 1).astype(np.float32)
        x_, y_, _ = cam.project(ring3)
        lay = np.zeros((H, W, 3), np.float32)
        glow_line(lay, list(zip(x_, y_))[:90], GOLD * 0.5, 1.2, 0.6, 0.6)
        F += lay
    F = render_boxes(F, cam, boxes, scale=0.6, t=t) if boxes else F
    # 底座的金色光（资本）
    if n_gold > 0:
        x, y, z = cam.project(np.array([[0, -1.25, 0]], np.float32))
        yy, xx = np.ogrid[0:H, 0:W]
        F += (np.exp(-(((xx - x[0]) / 380) ** 2 + ((yy - y[0]) / 70) ** 2)) * min(n_gold / 6, 1) * 0.5)[..., None] * GOLD

    # 层标签
    def slab_label(k, text, a, color=GOLD, side=1):
        if a <= 0.01: return
        yk = -1.2 + k * (0.17 + 0.06) + 0.085
        cs = np.array([[sx * 1.05, yk, sz * 1.05] for sx in (-1, 1) for sz in (-1, 1)], np.float32)
        x, y, z = cam.project(cs)
        i = int(np.argmax(x)) if side > 0 else int(np.argmin(x))
        x0_, y0_ = x[i] + 10 * side, y[i]
        lay = np.zeros((H, W, 3), np.float32)
        x2 = x0_ + 80 * side
        tw_ = font('serif_m', 34).getlength(text)
        if side > 0: x2 = min(x2, W - 80 - tw_ - 14)
        else: x2 = max(x2, 80 + tw_ + 14)
        glow_line(lay, [(x0_, y0_), (x2, y0_)], color, 1.0, 0.3, a * 0.8)
        ring(lay, x0_, y0_, 4, color, 2, a * 0.8, 0.5)
        F[:] += lay
        put_text(F, text, x2 + 14 * side, y0_, 34, 'serif_m', color, a, 400, 'left' if side > 0 else 'right', shadow=0.5, glow=0.15)

    if t_know + 2.0 < t < t_core:
        slab_label(0, '知识', smooth((t - t_know - 2.0) / 0.6))
        slab_label(5, '资本', smooth((t - t_know - 5.0) / 0.6), GOLD_HI)
    if t_core + 0.5 < t < t_n08 + 0.5:   # 李录列出的四样
        items = ['知识', '信任关系', '智慧', '健康']
        for k, it in enumerate(items):
            a = win(t, t_core + 3.6 + k * 0.5, t_n08 + 0.5, 0.5, 0.6)
            slab_label(1 + k * 2, it, a, GOLD_HI, side=1 if k % 2 == 0 else -1)
    if t > t_n08 + 0.5:
        for k, (wd, key) in enumerate((('知识', '知识'), ('判断力', '判断力'), ('信任', '信任'), ('信誉', '信誉'))):
            a = win(t, word_time('N08', key), A['build'] + 8.5, 0.4, 0.8)
            slab_label(1 + k * 2, wd, a, GOLD_HI, side=1 if k % 2 == 0 else -1)
        ta = win(t, word_time('N08', '工具') - 0.2, word_time('N08', '但') + 0.3, 0.3, 0.6)
        put_text(F, '工具会过时', W / 2, 330, 44, 'serif_m', CYAN, ta * 0.9, 900, glow=0.2)
        tb = win(t, word_time('N08', '一层') - 0.4, A['build'] + 7.9, 0.5, 0.6)
        gold_text(F, '积累会叠加', W / 2, 330, 60, 'serif', tb, glow=0.35)

    # 卡片
    ev = win(t, START['N05'] - 0.3, 54.4, 0.6, 0.5)
    if ev > 0:
        u = t - START['N05'] + 0.3
        rect_panel(F, 70, 330, W - 70, 820, alpha=ev, tint=(0.035, 0.045, 0.075), border=(0.95, 0.85, 0.6))
        put_text(F, 'Columbia Business School', W / 2, 400, 34, 'corm_sb', np.array([0.85, 0.88, 0.95]), ev, 900, shadow=0)
        put_text(F, '第 36 届格雷厄姆与多德年度午餐会', W / 2, 470, 44, 'serif', GOLD, ev, 940, reveal=clamp01(u / 1.0), glow=0.15, shadow=0)
        put_text(F, '36th Annual Graham & Dodd Event  ·  2026.10.05', W / 2, 530, 26, 'corm_sb', GREY * 1.3, ev, 940, shadow=0)
        lay = np.zeros((H, W, 3), np.float32)
        glow_line(lay, [(W / 2 - 330 * ease_out(clamp01(u / 1.2)), 575), (W / 2 + 330 * ease_out(clamp01(u / 1.2)), 575)], GOLD, 1.0, 0.4, ev * 0.7)
        F += lay
        put_text(F, '李录', W / 2 - 200, 650, 54, 'serif', WHITE, ev, 400, reveal=clamp01((u - 0.8) / 0.8), shadow=0)
        put_text(F, '喜马拉雅资本创始人', W / 2 - 200, 712, 24, 'sans_l', GREY * 1.4, ev, 400, shadow=0)
        put_text(F, '×', W / 2, 660, 36, 'sans_l', GOLD, ev * 0.8, 100, shadow=0)
        put_text(F, 'Tano Santos', W / 2 + 200, 650, 44, 'corm_sb', WHITE, ev, 400, reveal=clamp01((u - 1.2) / 0.8), shadow=0)
        put_text(F, '哥大海尔布伦中心学术主任', W / 2 + 200, 712, 24, 'sans_l', GREY * 1.4, ev, 400, shadow=0)
        put_text(F, '对谈尾声，李录谈到复利', W / 2, 775, 24, 'sans_l', GOLD_SUB * 1.2, ev * smooth((u - 2.5) / 0.8), 900, shadow=0)
    quote_card(F, QUOTES['Q_USELESS'], t, 54.6, 60.1, y=560, tape=(1 * 3600 + 24 * 60 + 18, TALK_LEN))
    quote_card(F, QUOTES['Q_KNOW'], t, START['N06'] + dur('N06') + 0.1, START['N07'] - 0.25, y=560, tape=(1 * 3600 + 23 * 60 + 3, TALK_LEN))
    # 核心定义：大号
    t1 = START['N07'] + dur('N07') + 0.05
    quote_card(F, QUOTES['Q_CORE'], t, t1, t_n08 - 0.15, y=480, tape=(1 * 3600 + 26 * 60 + 50, TALK_LEN), big=True)
    qa = win(t, t1 + 2.6, t_n08 - 0.15, 0.6, 0.5)
    if qa > 0:
        q = QUOTES['Q_CORE2']
        put_text(F, q['en'], W / 2, 830, 30, 'corm_sb', np.array([0.85, 0.87, 0.92]), qa, 920, lh=1.25, shadow=0.6)
        put_text(F, q['zh'], W / 2, 915, 34, 'serif_m', np.array([1.0, 0.86, 0.55]), qa, 920, reveal=clamp01((t - t1 - 3.2) / 1.2), shadow=0.6)
        put_text(F, '录像 1:26:59', W / 2, 970, 18, 'mono', GREY, qa * 0.8, 400, shadow=0)
    tag(F, '解读', 70, SUB_Y - 75, win(t, t_n08, START['N09'] - 0.4, 0.3, 0.3))
    # 过渡
    F *= 1 - 0.85 * smooth((t - (START['N09'] - 0.6)) / 0.5)
    return F


# ================================================================== SC4 巴菲特：企业价值的复利（93.3 – 123.2）
P_BUFFETT = os.path.join(PHOTO, 'buffett_2015_USITA_public_domain.jpg')
P_MEETING = os.path.join(PHOTO, 'brk_meeting_2007_TEDizen_CC-BY-2.0.jpg')


def sc_buffett(t):
    F = backdrop(t, c1=(0.015, 0.014, 0.02), c2=(0.05, 0.04, 0.035), neb=(0.20, 0.15, 0.08), neb_amt=0.3, drift=0.5)
    t9, t10, t11, t12 = START['N09'], START['N10'], START['N11'], START['N12']
    # ---- 可口可乐分红
    if t < t10 + 0.2:
        archive_photo(F, P_BUFFETT, W / 2, 420, 600, 420, t, t9 - 0.4, t10 + 0.2, '照片：美国国际贸易署，2015（公有领域）', focus=(0.72, 0.38))
        ca = win(t, t9 + 1.2, t10 + 0.2, 0.6, 0.5)
        if ca > 0:
            cam = Camera((1.6, 2.4, -14), (0, 1.15, 0), fov=40)
            u = clamp01((t - t9 - 1.2) / 2.5)
            HH = 1.75
            h1 = HH * 75 / 704; h2 = HH * ease_io(u)
            boxes = [make_box((-1.5, h1 / 2, 0), (0.42, h1 / 2, 0.42), tint=np.array([1.0, 0.45, 0.35]), density=0.9, edge=1.2, opacity=ca),
                     make_box((1.5, max(h2, 0.01) / 2, 0), (0.42, max(h2, 0.01) / 2, 0.42), tint=GOLD, density=0.9, edge=1.3, opacity=ca)]
            F = render_boxes(F, cam, boxes, scale=0.6, t=t)
            for (x3, hh, lab, val) in ((-1.5, h1, '1994', '7500 万美元'), (1.5, max(h2, 0.01), '2022', '7.04 亿美元')):
                x, y, z = cam.project(np.array([[x3, hh + 0.12, 0], [x3, -0.18, 0]], np.float32))
                put_text(F, val, x[0], y[0] - 30, 40, 'serif', GOLD_HI, ca * (1 if x3 < 0 else smooth(u * 3 - 2)), 500, glow=0.2)
                put_text(F, lab, x[1], y[1] + 12, 32, 'mono', GREY * 1.4, ca, 300)
            put_text(F, '可口可乐每年付给伯克希尔的现金分红', W / 2, 735, 38, 'serif_m', WHITE, ca, 980)
            put_text(F, '买入总成本 13 亿美元（1994 年 8 月完成建仓）· 数据：2022 年巴菲特致股东信', W / 2, 1262, 20, 'sans_l', GREY * 1.2, ca, 960)
            # 增长每年都发生（只显示两端真实数据；中间曲线为示意）
            lay = np.zeros((H, W, 3), np.float32)
            x, y, z = cam.project(np.array([[-1.5, h1, 0]] + [[-1.5 + 3.0 * k / 28, (h1 * (704 / 75) ** (k / 28)) if k / 28 <= u else np.nan, 0] for k in range(29)], np.float32))
            pts = [(a_, b_) for a_, b_ in zip(x[1:], y[1:]) if np.isfinite(b_)]
            if len(pts) > 2: glow_line(lay, pts, GOLD_HI, 1.4, 0.6, ca * 0.6)
            F += lay
            footnote(F, '曲线为示意：两端为真实数据，中间按年均约 8.3% 平滑连接，并非逐年数据', ca * smooth(u * 2 - 1), y=1292, size=19)
        q = QUOTES['Q_COKE']
        qa = win(t, t9 + 3.6, t10 + 0.2, 0.5, 0.4)
        put_text(F, q['en'], W / 2, 1355, 32, 'corm_sb', np.array([0.9, 0.9, 0.95]), qa, 960, lh=1.2, shadow=0.7)
        put_text(F, q['zh'] + ' —— 巴菲特', W / 2, 1412, 30, 'serif_m', np.array([1.0, 0.86, 0.55]), qa, 960, shadow=0.7)
    # ---- 时间是优秀企业的朋友
    elif t < t11 - 0.1:
        u = t - t10
        a = win(t, t10, t11 - 0.1, 0.5, 0.4)
        quote_card(F, QUOTES['Q_TIME'], t, t10 + 0.1, t11 - 0.1, y=470)
        lay = np.zeros((H, W, 3), np.float32)
        x0, x1, yb = 130, 950, 1330
        glow_line(lay, [(x0, yb), (x1, yb)], GREY * 0.6, 1.0, 0, a)
        prog = ease_io(clamp01((u - 0.4) / 4.5))
        n = max(int(prog * 200), 2)
        xs = np.linspace(x0, x0 + (x1 - x0) * prog, n)
        k = (xs - x0) / (x1 - x0)
        good = yb - 60 - 520 * (np.exp(2.2 * k) - 1) / (math.e ** 2.2 - 1)
        mid = yb - 60 - 40 * k
        price = good + 55 * np.sin(k * 37) * np.sin(k * 11 + 1) * (0.4 + k)
        glow_line(lay, list(zip(xs, mid)), GREY * 1.2, 1.6, 0.3, a)
        glow_line(lay, list(zip(xs, price)), CYAN * 0.8, 1.0, 0.3, a * 0.8)
        glow_line(lay, list(zip(xs, good)), GOLD, 2.4, 0.9, a)
        F += lay
        if prog > 0.6:
            put_text(F, '优秀企业的内在价值', xs[-1] - 10, good[-1] - 34, 28, 'serif_m', GOLD, a * smooth(prog * 4 - 2.6), 400, 'right')
            put_text(F, '股价：围绕价值波动', xs[-1] - 10, price[-1] + 60, 24, 'sans_l', CYAN, a * smooth(prog * 4 - 2.8), 400, 'right')
            put_text(F, '平庸企业', xs[-1] - 10, mid[-1] + 34, 26, 'sans_l', GREY * 1.4, a * smooth(prog * 4 - 3.0), 400, 'right')
        put_text(F, '时间 →', x1, yb + 32, 22, 'sans_l', GREY, a, 200, 'right')
        tag(F, '示意', x0 - 10, yb - 640, a, GREY * 1.3, 20)
    # ---- 能力圈
    elif t < t12 - 0.1:
        u = t - t11
        a = win(t, t11 - 0.1, t12 - 0.1, 0.4, 0.4)
        cam = Camera((0, 7.5, -11), (0, 0, 1.5), fov=44)
        rr = np.random.default_rng(12)
        pts = rr.uniform([-7, 0, -3], [7, 0, 12], (900, 3)).astype(np.float32)
        d = np.sqrt(pts[:, 0] ** 2 + (pts[:, 2] - 2.5) ** 2)
        inside = d < 3.2
        col = np.where(inside[:, None], GOLD[None, :] * 1.2, np.array([0.45, 0.55, 0.75])[None, :] * 0.55).astype(np.float32)
        pts[:, 1] = 0.05 * np.sin(t * 2 + pts[:, 0])
        particles3d(F, cam, pts, col, size=0.07, alpha=a * 0.9, focus=12, dof=0.05)
        th = np.linspace(0, 2 * np.pi, 160)
        edge = np.stack([3.2 * np.cos(th), np.zeros_like(th), 2.5 + 3.2 * np.sin(th)], 1).astype(np.float32)
        x, y, z = cam.project(edge)
        lay = np.zeros((H, W, 3), np.float32)
        pulse = 0.6 + 0.4 * math.sin(u * 4)
        glow_line(lay, list(zip(x, y)), GOLD_HI, 2.5, 1.2 * pulse, a)
        F += lay
        xc, yc, _ = cam.project(np.array([[0, 0, 2.5], [3.2, 0, 2.5]], np.float32))
        put_text(F, '知道边界', xc[1] - 30, yc[1] - 40, 30, 'serif_m', GOLD_HI, a * smooth(u - 1.0), 300, 'right')
        quote_card(F, QUOTES['Q_CIRCLE'], t, t11 + 0.2, t12 - 0.1, y=450)
        qe = QUOTES['Q_EDGE']
        ea = win(t, t11 + 2.0, t12 - 0.1, 0.5, 0.4)
        put_text(F, '李录（同场对谈，录像 0:08:30）', W / 2, 1290, 22, 'sans_l', GREY * 1.3, ea, 960)
        put_text(F, qe['zh'], W / 2, 1340, 32, 'serif_m', np.array([1.0, 0.86, 0.55]), ea, 960)
        put_text(F, qe['en'], W / 2, 1395, 22, 'corm_sb', np.array([0.8, 0.82, 0.88]), ea, 960)
    # ---- 四次大跌
    else:
        u = t - t12
        a = win(t, t12 - 0.1, START['N13'] + 0.2, 0.4, 0.5)
        put_text(F, '伯克希尔股价的四次重大下跌', W / 2, 360, 46, 'serif', WHITE, a, 980, reveal=clamp01(u / 0.8))
        put_text(F, '来源：2017 年巴菲特致股东信', W / 2, 420, 22, 'sans_l', GREY * 1.3, a, 980)
        for k, (per, pct) in enumerate(DATA['brk_dips']):
            tk = t12 + 1.0 + k * BEAT * 2
            ak = a * smooth((t - tk) / 0.25)
            if ak <= 0: continue
            y0 = 500 + k * 175 + (1 - ease_back((t - tk) / 0.5)) * -60
            rect_panel(F, 110, y0, W - 110, y0 + 145, alpha=ak, tint=(0.05, 0.03, 0.035), border=(1.0, 0.5, 0.45), radius=20)
            put_text(F, per, 160, y0 + 72, 34, 'mono', GREY * 1.5, ak, 600, 'left', shadow=0)
            put_text(F, f'−{pct:.1f}%', W - 160, y0 + 72, 72, 'serif', RED * 1.15, ak, 500, 'right', glow=0.3 * (1 + onset(t)), shadow=0)
        ga = a * smooth((t - (t12 + 1.0 + 4 * BEAT * 2 + 0.3)) / 0.6)
        gold_text(F, '同期（1965–2017）每股市值年复合 +20.9%', W / 2, 1270, 38, 'serif_m', ga, glow=0.25)
        put_text(F, '下跌是暂时的；企业价值的积累没有中断', W / 2, 1345, 30, 'sans_l', WHITE, ga, 960)
    F *= 1 - 0.8 * smooth((t - (START['N13'] - 0.3)) / 0.4)
    return F


# ================================================================== SC5 芒格 + 暂时回撤 vs 永久损失（123.2 – 140.2）
def sc_munger(t):
    F = backdrop(t, c1=(0.012, 0.012, 0.022), c2=(0.04, 0.035, 0.05), neb=(0.14, 0.10, 0.16), neb_amt=0.3, drift=0.5)
    t13, t14 = START['N13'], START['N14']
    if t < t14 - 0.1:
        archive_photo(F, P_MEETING, W / 2, 470, 900, 560, t, t13 - 0.3, t14 + 0.2, '2007 年伯克希尔股东大会 · 照片：TEDizen / CC BY 2.0', focus=(0.62, 0.5))
        put_text(F, '巴菲特（左）与芒格（右）', W / 2 - 300, 790, 22, 'sans_l', GREY * 1.4, win(t, t13, t14, 0.6, 0.4), 500, 'left', shadow=0.6)
        quote_card(F, QUOTES['Q_MUNGER50'], t, t13 + 1.6, t14 - 0.1, y=1110, en_size=34, zh_size=40)
    else:
        u = t - t14
        a = win(t, t14 - 0.1, START['N16'] - 0.2, 0.5, 0.5)
        ang = -0.42 + 0.18 * ease_io(clamp01(u / 9))
        cam = Camera((math.sin(ang) * 17.5, 0.2, -math.cos(ang) * 17.5), (0.0, -0.75, 0), fov=42)
        prog = ease_io(clamp01(u / 4.5))
        ks = np.linspace(0, prog, max(int(prog * 160), 2))
        X = -3.3 + 6.6 * ks
        lay = np.zeros((H, W, 3), np.float32)

        def P3(x, y, z=0.0):
            x_, y_, _ = cam.project(np.stack([np.asarray(x, np.float32), np.asarray(y, np.float32), np.full(np.shape(x), z, np.float32)], 1))
            return list(zip(x_, y_))

        def grid(y0):
            for gx in np.linspace(-3.3, 3.3, 9):
                glow_line(lay, P3(np.array([gx, gx]), np.array([y0, y0]), 0) + [], GREY * 0.5, 1.0, 0, a * 0.6)
            for gz in (0.0, 1.0, 2.0):
                pts = cam.project(np.array([[-3.3, y0, gz], [3.3, y0, gz]], np.float32))
                glow_line(lay, list(zip(pts[0], pts[1])), GREY * 0.45, 1.0, 0, a * 0.5)
            for gx in np.linspace(-3.3, 3.3, 9):
                pts = cam.project(np.array([[gx, y0, 0], [gx, y0, 2.0]], np.float32))
                glow_line(lay, list(zip(pts[0], pts[1])), GREY * 0.4, 1.0, 0, a * 0.5)

        def v2y(y0, v): return y0 + 0.9 * v          # v: 价值（起点 1.0，期末 2.0）
        # ---- A：暂时回撤
        yA = 1.4
        grid(yA)
        vA = 2 ** ks
        dip = np.where((ks > 0.3) & (ks < 0.75), np.sin(np.clip((ks - 0.3) / 0.45, 0, 1) * np.pi), 0)
        pA = vA * (1 - 0.5 * dip)
        glow_line(lay, P3(X, v2y(yA, vA)), GOLD, 2.6, 1.0, a)
        glow_line(lay, P3(X, v2y(yA, vA), 0.35), GOLD * 0.35, 1.2, 0.3, a)
        glow_line(lay, P3(X, v2y(yA, pA)), CYAN, 1.8, 0.7, a)
        # ---- B：永久损失
        yB = -2.6
        grid(yB)
        kb = 0.45
        vB = np.where(ks < kb, 2 ** ks, 0.5 * 2 ** ks)
        pre, post_ = ks < kb, ks >= kb
        glow_line(lay, P3(X[pre], v2y(yB, vB[pre])), GOLD, 2.6, 1.0, a)
        glow_line(lay, P3(X[pre], v2y(yB, vB[pre]), 0.35), GOLD * 0.35, 1.2, 0.3, a)
        if post_.sum() > 1:
            glow_line(lay, P3(X[post_], v2y(yB, vB[post_])), RED, 2.6, 1.0, a)
            gx_ = X[post_]; gy_ = v2y(yB, 2 ** ks[post_])
            for i in range(0, len(gx_) - 3, 8):
                glow_line(lay, P3(gx_[i:i + 4], gy_[i:i + 4]), GOLD * 0.45, 1.2, 0.2, a * 0.7)
        F += lay
        # 价值线上流动的光点 / 断裂处的碎片
        fl = (np.arange(60) / 60 + u * 0.12) % 1.0
        fl = fl[fl <= prog]
        if len(fl):
            PA = np.stack([-3.3 + 6.6 * fl, v2y(yA, 2 ** fl), np.zeros_like(fl)], 1).astype(np.float32)
            particles3d(F, cam, PA, GOLD * 1.3, size=0.07, alpha=a)
        if prog > kb:
            bu = (t - (t14 + 4.5 * 0.45)) * 0.8
            if bu > 0:
                Pb = CRASH_P[:400] * 0.25 * (0.3 + bu * 2.5) + np.array([-3.3 + 6.6 * kb, v2y(yB, 2 ** kb), 0], np.float32)
                Pb[:, 1] -= 1.5 * bu ** 2
                particles3d(F, cam, Pb, RED * 1.1, size=0.035, alpha=a * math.exp(-bu * 1.5))
        # 文字
        lx, ly = P3(np.array([-4.3]), np.array([v2y(yA, 2.2)]))[0]
        ta_ = P3(np.array([0.0, 0.0]), np.array([v2y(yA, 2.25), v2y(yB, 2.25)]))
        put_text(F, '暂时回撤', W / 2, ta_[0][1] - 70, 48, 'serif', CYAN, a, 900)
        put_text(F, '价格下跌，内在价值仍在；不被迫卖出，就可以等待', W / 2, ta_[0][1] - 14, 26, 'sans_l', WHITE, a, 960)
        put_text(F, '永久损失', W / 2, ta_[1][1] - 70, 48, 'serif', RED * 1.15, a, 900)
        put_text(F, '看错企业、价值毁损；或借钱持股、在低谷被迫卖出', W / 2, ta_[1][1] - 14, 26, 'sans_l', WHITE, a, 960)
        if prog > 0.95:
            e = P3(np.array([3.3, 3.3, -3.3 + 6.6 * 0.52]), np.array([v2y(yA, 2.0), v2y(yB, 1.0), v2y(yA, 2 ** 0.52 * 0.5)]))
            put_text(F, '价值', e[0][0] - 10, e[0][1] - 32, 26, 'sans', GOLD, a, 200, 'right')
            put_text(F, '价格', e[2][0], e[2][1] + 40, 26, 'sans', CYAN, a, 200)
            put_text(F, '回不去的部分', e[1][0] - 10, e[1][1] + 36, 26, 'sans', RED * 1.1, a, 300, 'right')
        q = QUOTES['Q_DEBT']
        qa = win(t, word_time('N14', '借钱') - 0.3, START['N16'] - 0.2, 0.5, 0.5)
        put_text(F, '巴菲特谈那张下跌表（2017 年致股东信）', W / 2, 1310, 21, 'sans_l', GREY * 1.3, qa, 960)
        put_text(F, q['zh'], W / 2, 1360, 30, 'serif_m', np.array([1.0, 0.86, 0.55]), qa, 960)
        put_text(F, q['en'], W / 2, 1422, 22, 'corm_sb', np.array([0.8, 0.82, 0.88]), qa, 980, lh=1.2)
        tag(F, '示意', 80, 330, a, GREY * 1.3, 20)
    F *= 1 - 0.8 * smooth((t - (START['N16'] - 0.4)) / 0.4)
    return F


# ================================================================== SC6 第一性原理：乘法（140.2 – 156.4）
def sc_formula(t):
    F = backdrop(t, c1=(0.008, 0.01, 0.02), c2=(0.02, 0.03, 0.05), neb=(0.08, 0.10, 0.16), neb_amt=0.25, drift=0.3)
    t16, t17 = START['N16'], START['N17']
    a = win(t, t16 - 0.2, A['climax'] + 0.2, 0.6, 0.5)
    u = t - t16
    gold_text(F, '终值 = 本金', W / 2, 360, 70, 'serif', a * smooth(u / 0.8), glow=0.3)
    factors = ['(1 + r₁)', '(1 + r₂)', '(1 + r₃)', '(1 + r₄)', '(1 + r₅)', '…', '(1 + r₃₀)']
    loss_t = word_time('N17', '一次') if t > t17 else 1e9
    for k, f in enumerate(factors):
        tk = t16 + 1.6 + k * BEAT
        ak = a * smooth((t - tk) / 0.3)
        if ak <= 0: continue
        y = 480 + k * 118
        hit = math.exp(-max(t - tk, 0) * 4)
        col = WHITE * (0.85 + 0.6 * hit)
        red = 0.0
        if k >= 3 and f != '…': red = smooth((t - loss_t - 0.3 - (k - 3) * 0.12) / 0.4)
        if f != '…':
            rect_panel(F, W / 2 - 230, y - 48, W / 2 + 230, y + 48, alpha=ak, tint=(0.04, 0.05, 0.08) if red < 0.5 else (0.08, 0.03, 0.03),
                       border=GOLD * (1 - red) + RED * red, radius=22, blur_bg=8)
        c = col * (1 - red) + RED * red
        put_text(F, ('× ' if f != '…' else '') + f, W / 2, y, 50 if f != '…' else 60, 'mono', c, ak, 600, glow=0.2 * hit, shadow=0)
    # N17：微小差异 / 一次重大损失
    da = win(t, word_time('N17', '微小') - 0.2, word_time('N17', '也会') + 0.2, 0.4, 0.4)
    if da > 0:
        put_text(F, '1.1 与 0.9：每次只差一点', W / 2, 1360, 34, 'serif_m', GOLD_HI, da, 960)
    la = win(t, loss_t - 0.1, A['climax'] + 0.2, 0.3, 0.4)
    if la > 0:
        put_text(F, '× 0.5', W / 2 + 330, 480 + 3 * 118 - 60, 62, 'serif', RED * 1.2, la, 300, glow=0.5, shadow=0)
        put_text(F, '一次重大损失，会乘进此后的每一年', W / 2, 1360, 34, 'serif_m', np.array([1.0, 0.6, 0.55]), la, 960)
    return F


EXTRA_SCENES = [
    ('sc_lilu', A['calm'], START['N09'] - 0.1),
    ('sc_buffett', START['N09'] - 0.1, START['N13'] - 0.2),
    ('sc_munger', START['N13'] - 0.2, START['N16'] - 0.2),
    ('sc_formula', START['N16'] - 0.2, A['climax']),
]


# ================================================================== SC7 高潮：复利的三幕（156.4 – 223.4）
H0 = 0.62                      # 价值 1.0 对应的塔高（世界单位）
GX, CX_ = -1.0, 1.35           # 金塔 / 青塔 x 位置
SLAB_W = 1.25
_rs = np.random.default_rng(77)


def years_at(t):
    return clamp01((t - A['year0']) / (30 * BEAT)) * 30


def tower(x, values, tint, t, w=SLAB_W, gap=0.025, grow_from=None, edge=1.0, op=1.0, twist=0.0, dens=0.85):
    """按价值序列堆塔：values[k] 为第 k 层顶部对应的累计价值；返回 boxes 与塔顶高度"""
    boxes = []
    prev = 0.0; y = 0.0
    for k, v in enumerate(values):
        th = max((v - prev) * H0 - gap, 0.004)
        boxes.append(make_box((x, y + th / 2, 0), (w / 2, th / 2, w / 2), (0, twist * k, 0), tint=tint, density=dens, edge=edge, opacity=op))
        y += th + gap; prev = v
    return boxes, y


def growth_values(yrs, r=0.1, start=1.0):
    n = int(yrs)
    vals = [start]
    for k in range(1, n + 1): vals.append(start * (1 + r) ** k)
    frac = yrs - n
    if frac > 0: vals.append(start * (1 + r) ** n * (1 + r * ease_back(frac / 0.35 if frac < 0.35 else 1)))
    return vals


# 崩塌碎片（预生成）
SHARDS = []
for k in range(46):
    SHARDS.append(dict(off=_rs.uniform([-0.6, 0, -0.6], [0.6, 1, 0.6]), v=_rs.normal(0, 1, 3) * np.array([2.2, 1.4, 2.2]) + np.array([0, 1.6, -0.6]),
                       w=_rs.normal(0, 3, 3), s=_rs.uniform(0.08, 0.28, 3)))
CRASH_P = _rs.normal(0, 1, (2600, 3)).astype(np.float32)


def cam_for(top, ang, extra=0.0, aim=0.47, x_aim=0.15):
    d = max(13.0, 2.9 * top + 3.0) + extra
    return Camera((x_aim + math.sin(ang) * d, top * 0.55 + 1.2, -math.cos(ang) * d), (x_aim, top * aim, 0), fov=40)


def sc_climax(t):
    c = t - C0
    if t < A['epic'] - 0.6:
        F = backdrop(t, c1=(0.01, 0.012, 0.025), c2=(0.03, 0.04, 0.07), neb=(0.10, 0.13, 0.24), neb_amt=0.3, drift=0.6)
    else:
        F = backdrop(t, c1=(0.02, 0.016, 0.012), c2=(0.06, 0.05, 0.04), neb=(0.30, 0.22, 0.10), neb_amt=0.45, drift=0.8)
    shake = 0.0
    # ------------------------------------------------ P1 分叉：30 年 +10% vs −10%
    if t < A['crash']:
        yrs = years_at(t)
        vals = growth_values(yrs)
        boxes, top = tower(GX, vals, GOLD, t, edge=1.1)
        dv = 0.9 ** yrs
        hd = max(dv * H0, 0.01)
        cyan_op = 1.0
        boxes.append(make_box((CX_, hd / 2, 0), (0.62, hd / 2, 0.62), tint=CYAN, density=0.8, edge=1.0, opacity=cyan_op))
        ang = -0.55 + 0.75 * ease_io(clamp01(c / 20.5))
        cam = cam_for(max(top, 1.0), ang)
        cam = Camera(cam.pos + np.array([0, 0.25 * math.sin(c * 0.9), 0], np.float32), cam.target, 40)
        dust(F, cam, t, color=(0.6, 0.75, 1.0), amt=0.3, focus=12, dof=0.1, n=4000)
        F = render_boxes(F, cam, boxes, scale=0.55, t=t)
        # 青塔顶部被侵蚀的粒子
        if yrs > 0.5:
            P = _rs.normal(0, 1, (300, 3)).astype(np.float32) * np.array([0.35, 0.05, 0.35], np.float32)
            ph = (np.arange(300) * 0.137 + t * 0.6) % 1.0
            P[:, 0] += CX_; P[:, 1] += hd + ph * 1.6
            particles3d(F, cam, P, CYAN * 0.9, size=0.03, alpha=(1 - ph) * 0.8)
        # 标注
        ny = int(yrs)
        xg, yg, _ = cam.project(np.array([[GX - SLAB_W / 2 - 0.15, top, -SLAB_W / 2], [CX_ + 0.75, hd, -0.62], [GX, 0, 0], [CX_, 0, 0]], np.float32))
        hit = math.exp(-((t - A['year0']) % BEAT) * 6) if 0 < yrs < 30 else 0
        put_text(F, '起  点' if ny == 0 else f'第 {ny:2d} 年', W / 2, 330, 64, 'mono' if ny else 'serif_m', WHITE * (0.9 + 0.5 * hit), 1.0, 600, glow=0.3 * hit, shadow=0.6)
        put_text(F, f'{1.1 ** ny:.2f} 倍', xg[0], yg[0], 46, 'serif', GOLD_HI, 1.0, 400, 'right', glow=0.25, shadow=0.6)
        put_text(F, f'{0.9 ** ny:.3f} 倍', xg[1], yg[1] - 10, 38, 'serif', CYAN, 1.0, 400, 'left', glow=0.2, shadow=0.6)
        put_text(F, '每年 +10%', xg[2], yg[2] + 46, 30, 'sans', GOLD, 1.0, 400, shadow=0.6)
        put_text(F, '每年 −10%', xg[3], yg[3] + 46, 30, 'sans', CYAN, 1.0, 400, shadow=0.6)
        ga = smooth((yrs - 29.6) / 0.4)
        if ga > 0:
            gold_text(F, f'相差约 {MATH["ratio"]:.0f} 倍', W / 2, 420, 62, 'serif', ga, glow=0.45)
        footnote(F, '1.1³⁰ ≈ 17.45　　0.9³⁰ ≈ 0.042　　' + ASSUMPTIONS, 1.0, y=1680, size=19)
    # ------------------------------------------------ P2 崩塌：−50%
    elif t < A['rebuild'] + 0.6:
        u = t - A['crash']
        tau = u * 0.42                                      # 慢动作
        vals = growth_values(30)
        keep = [v for v in vals if v <= MATH['up'] * 0.5 + 1e-6] + [MATH['up'] * 0.5]
        boxes, top = tower(GX, keep, GOLD * (1 - 0.35 * math.exp(-u)) + RED * 0.35 * math.exp(-u), t, edge=1.1)
        cam = cam_for(MATH['up'] * H0, -0.13, extra=1.0)
        shake = 0.25 * math.exp(-u * 3)
        cam = Camera(cam.pos + np.array([math.sin(t * 61) * shake, math.cos(t * 47) * shake, 0], np.float32), cam.target, 40)
        # 上半截碎成玻璃碎片
        y_half = MATH['up'] * 0.5 * H0
        y_top = MATH['up'] * H0
        for sh in SHARDS:
            p0 = np.array([GX, y_half, 0]) + sh['off'] * np.array([SLAB_W, y_top - y_half, SLAB_W])
            p = p0 + sh['v'] * tau * 2.2 + np.array([0, -4.9, 0]) * tau ** 2
            if p[1] < -1: continue
            boxes.append(make_box(p, sh['s'], tuple(sh['w'] * tau), tint=GOLD * 0.8 + RED * 0.2, density=0.9, edge=1.2, opacity=clamp01(1.4 - tau)))
        dust(F, cam, t, color=(1.0, 0.7, 0.5), amt=0.25, n=3000)
        F = render_boxes(F, cam, boxes, scale=0.55, t=t)
        P = CRASH_P * np.array([1.5, 1.0, 1.5], np.float32) * (0.3 + tau * 3.5) + np.array([GX, (y_half + y_top) / 2, 0], np.float32)
        P[:, 1] -= 4.9 * tau ** 2
        particles3d(F, cam, P, GOLD * 1.2, size=0.035, alpha=0.9 * math.exp(-tau * 1.2))
        # 原高度的虚影
        xg, yg, _ = cam.project(np.array([[GX - 0.9, y_top, 0], [GX + 0.9, y_top, 0], [GX, top, 0]], np.float32))
        lay = np.zeros((H, W, 3), np.float32)
        for i in range(0, 12, 2):
            glow_line(lay, [(xg[0] + (xg[1] - xg[0]) * i / 12, yg[0]), (xg[0] + (xg[1] - xg[0]) * (i + 1) / 12, yg[0])], GOLD * 0.6, 1.2, 0.2, smooth(u / 0.8))
        F += lay
        F += np.float32(1.0 * math.exp(-u * 9)) * np.array([1.0, 0.45, 0.35], np.float32)
        a1 = smooth(u / 0.15)
        put_text(F, '−50%', W / 2, 400, 170, 'serif', RED * 1.25, a1, 900, glow=0.6, shadow=0.5)
        a2 = smooth((u - 1.2) / 0.5)
        put_text(F, '要 +100%，才能回到原点', W / 2, 560, 52, 'serif_m', WHITE, a2, 980, reveal=clamp01((u - 1.2) / 0.9), shadow=0.6)
        footnote(F, '永久损失：例如企业价值受损、被迫低价卖出。0.5 × 2 = 1', a2, y=1680, size=20)
    # ------------------------------------------------ P3 漫长的恢复 + 暂时 vs 永久
    elif t < A['epic'] - 0.3:
        u = t - (A['rebuild'] + 0.6)
        ry = clamp01(u / (MATH['recover_years'] * 2 * BEAT)) * MATH['recover_years']   # 每两拍一年
        base = MATH['up'] * 0.5
        vals = [v for v in growth_values(30) if v <= base + 1e-6] + [base]
        k = int(ry)
        for j in range(1, k + 1): vals.append(base * 1.1 ** j)
        if ry > k: vals.append(base * 1.1 ** ry)
        boxes, top = tower(GX, vals, GOLD, t, edge=1.1)
        # 没有中断的路径（虚影塔）
        ghost_v = MATH['up'] * 1.1 ** ry
        gh = ghost_v * H0
        ga = smooth((t - START['N20'] + 0.5) / 1.0) if t > START['N20'] - 0.5 else smooth((ry - 1) / 1.5) * 0.6
        boxes.append(make_box((CX_ + 0.2, gh / 2, 0), (SLAB_W / 2, gh / 2, SLAB_W / 2), tint=np.array([0.5, 0.55, 0.65]), density=0.2, edge=0.7, opacity=0.35 * ga))
        tall = max(MATH['up'] * H0 * 1.12, gh * ga + top * (1 - ga), top)
        cam = cam_for(tall, -0.13 + 0.25 * ease_io(clamp01(u / 20)), extra=1.0 * (1 - smooth(u / 3)), x_aim=0.15 + 0.25 * smooth(u / 3))
        dust(F, cam, t, color=(0.7, 0.75, 0.9), amt=0.25, n=3000)
        F = render_boxes(F, cam, boxes, scale=0.55, t=t)
        y_top = MATH['up'] * H0
        xg, yg, _ = cam.project(np.array([[GX - 1.0, y_top, 0], [GX + 1.0, y_top, 0], [GX, top, 0], [CX_ + 0.2, gh, 0]], np.float32))
        lay = np.zeros((H, W, 3), np.float32)
        for i in range(0, 14, 2):
            glow_line(lay, [(xg[0] + (xg[1] - xg[0]) * i / 14, yg[0]), (xg[0] + (xg[1] - xg[0]) * (i + 1) / 14, yg[0])], GOLD_HI * 0.8, 1.2, 0.3, 0.9)
        F += lay
        put_text(F, '原来的高度', xg[1] + 14, yg[0], 24, 'sans', GOLD_HI, 0.9, 300, 'left', shadow=0.6)
        t_done = A['rebuild'] + 0.6 + MATH['recover_years'] * 2 * BEAT
        done = smooth((t - t_done) / 0.4)
        put_text(F, f'恢复第 {min(ry, MATH["recover_years"]):.1f} 年', W / 2, 330, 56, 'mono', WHITE, 1 - smooth((t - t_done + 0.35) / 0.3), 600, shadow=0.6)
        if done > 0:
            gold_text(F, '7.3 年，才回到原点', W / 2, 330, 64, 'serif', done * win(t, 0, START['N20'] + 1.2, 0, 0.6), glow=0.4)
        if ga > 0.05 and t > START['N20'] - 0.5:
            put_text(F, f'没有中断：{ghost_v:.1f} 倍', min(xg[3], W - 230), max(yg[3] - 36, 430), 32, 'serif_m', np.array([0.75, 0.8, 0.9]), ga, 400, shadow=0.6)
            put_text(F, f'中断一次：{vals[-1]:.1f} 倍', xg[2] - 60, yg[2] + 30, 32, 'serif_m', GOLD_HI, ga, 400, 'right', shadow=0.6)
            # 暂时 vs 永久
            b1 = smooth((t - word_time('N20', '只要')) / 0.6)
            b2 = smooth((t - word_time('N20', '真正')) / 0.6)
            rect_panel(F, 70, 1200, 520, 1415, alpha=b1, tint=(0.03, 0.06, 0.09), border=CYAN, radius=20)
            put_text(F, '暂时回撤', 295, 1250, 38, 'serif', CYAN, b1, 420)
            put_text(F, '价格下跌、价值仍在\n不被迫卖出 → 可以等待', 295, 1340, 25, 'sans_l', WHITE, b1, 420, lh=1.5)
            rect_panel(F, 560, 1200, 1010, 1415, alpha=b2, tint=(0.09, 0.03, 0.03), border=RED, radius=20)
            put_text(F, '永久损失', 785, 1250, 38, 'serif', RED * 1.15, b2, 420)
            put_text(F, '终值永久 × 0.5\n无论发生在哪一年', 785, 1340, 25, 'sans_l', WHITE, b2, 420, lh=1.5)
        footnote(F, '假设：一次永久性 −50% 之后，仍按每年 +10% 增长。7.27 年 = ln2 / ln1.1', 1.0, y=1680, size=19)
    # ------------------------------------------------ P4 人生的复利 → 汇聚
    else:
        F = sc_life(t, F)
    return F


LIFE = [('知识', np.array([0.62, 0.80, 1.0]), '理解，叠加在理解之上'),
        ('信任', np.array([1.0, 0.72, 0.38]), '建立在一次次兑现之上'),
        ('技能', np.array([0.40, 0.95, 0.85]), '每次练习，站在上一次之上'),
        ('健康', np.array([0.55, 0.95, 0.55]), '复利需要时间，健康给你时间')]
LIFE_X = [-3.4, -1.75, 1.75, 3.4]
_ang = _rs.uniform(0, 2 * np.pi, 5000); _rad = np.sqrt(_rs.uniform(0, 1, 5000)) * 9
RISE_P = np.stack([np.cos(_ang) * _rad, _rs.uniform(0, 14, 5000), np.sin(_ang) * _rad * 0.6 + 1.0], 1).astype(np.float32)
CONV_PT = (W / 2, 430)
HELIX = np.stack([_rs.uniform(0, 2 * np.pi, 700), _rs.uniform(0, 1, 700)], 1).astype(np.float32)


def sc_life(t, F):
    u = t - A['epic']
    conv = smooth((t - (START['N23'] - 2.6)) / 2.6)            # 汇聚
    ang = -0.75 + 1.3 * ease_io(clamp01(u / 20))               # 环绕五座塔的大幅运镜
    R_ = 22 - 3 * ease_io(clamp01(u / 20))
    cam = Camera((math.sin(ang) * R_, 4.2 + 2.2 * u / 22, -math.cos(ang) * R_), (0, 2.6 + 7.5 * conv, 0), fov=40)
    boxes = []
    # 中央金塔（金钱）
    vals = growth_values(30)
    b, top = tower(0, [v * 0.55 for v in vals], GOLD, t, w=1.1, edge=1.1)
    boxes += b
    for i, (name, col, cap) in enumerate(LIFE):
        ti = A['epic'] + 0.3 + i * 4 * BEAT
        g = clamp01((t - ti) / 7.0)
        if g <= 0: continue
        n = 2 + g * 18
        vals_i = [(1.12 ** k) * 0.6 for k in range(int(n) + 1)]
        bi, topi = tower(LIFE_X[i], vals_i, col, t, w=0.75, edge=1.0, twist=0.09, dens=0.7)
        for bb in bi: bb[2] = 0.8
        boxes += bi
    # 上升的光尘
    P = RISE_P.copy()
    P[:, 1] = (P[:, 1] + u * 1.2) % 14
    if conv <= 0:
        particles3d(F, cam, P, GOLD * 0.9, size=0.035, alpha=0.6 + 0.4 * kick(t))
    else:   # 屏幕空间汇聚到一点（带旋转）
        x, y, z = cam.project(P)
        ok = z > 0.5
        x, y = x[ok], y[ok]
        dx, dy = x - CONV_PT[0], y - CONV_PT[1]
        rot = conv * 2.2
        c_, s_ = math.cos(rot), math.sin(rot)
        k = (1 - ease_in(conv))
        xx = CONV_PT[0] + (dx * c_ - dy * s_) * k; yy = CONV_PT[1] + (dx * s_ + dy * c_) * k
        splat(F, xx, yy, np.full(len(xx), 1.3, np.float32), GOLD * 0.9, (0.6 + 0.4 * kick(t)) * (1 + conv))
    # 每座塔周围螺旋上升的光尘（复利的"吸收"）
    for i in range(-1, 4):
        xi = 0.0 if i < 0 else LIFE_X[i]
        col = GOLD if i < 0 else LIFE[i][1]
        ti = A['epic'] + (0.0 if i < 0 else 0.3 + i * 4 * BEAT)
        g = clamp01((t - ti) / 2.0) * (1 - conv)
        if g <= 0: continue
        th0 = HELIX[:, 0] + (t - ti) * (1.4 + 0.2 * i)
        hy = (HELIX[:, 1] + (t - ti) * 0.9) % 1.0
        hh = 6.5 if i < 0 else 4.0
        rr = (0.95 if i < 0 else 0.75) * (1.0 + 0.6 * (1 - hy))
        P = np.stack([xi + np.cos(th0 + hy * 6) * rr, hy * hh, (0 if i < 0 else 0.8) + np.sin(th0 + hy * 6) * rr], 1).astype(np.float32)
        particles3d(F, cam, P, col * 1.1, size=0.03, alpha=g * (1 - hy) * (0.7 + 0.5 * kick(t)))
    F = render_boxes(F, cam, boxes, scale=0.5, t=t)
    # 塔顶光柱（随重拍脉动）
    lay = np.zeros((H // 4, W // 4, 3), np.float32)
    for i in range(-1, 4):
        xi = 0.0 if i < 0 else LIFE_X[i]
        col = GOLD if i < 0 else LIFE[i][1]
        ti = A['epic'] + (0.0 if i < 0 else 0.3 + i * 4 * BEAT)
        g = clamp01((t - ti) / 2.0)
        if g <= 0: continue
        topy = (6.0 if i < 0 else (1.12 ** (2 + clamp01((t - ti) / 7.0) * 18)) * 0.6 * H0)
        x, y, _ = cam.project(np.array([[xi, topy, 0 if i < 0 else 0.8]], np.float32))
        yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
        beam = np.exp(-((xx - x[0] / 4) / (6 + 4 * conv)) ** 2) * np.clip(1 - (y[0] / 4 - yy) / (H / 4), 0, 1) * (yy < y[0] / 4)
        lay += beam[..., None] * col * g * (0.25 + 0.35 * kick(t) + 0.8 * conv)
    F += cv2.resize(cv2.GaussianBlur(lay, (0, 0), 2), (W, H))
    # 标签
    for i, (name, col, cap) in enumerate(LIFE):
        ti = A['epic'] + 0.3 + i * 4 * BEAT
        a = smooth((t - ti - 0.3) / 0.6) * (1 - conv)
        if a <= 0: continue
        x, y, _ = cam.project(np.array([[LIFE_X[i], -0.1, 0.8]], np.float32))
        xl = min(max(x[0], 125), W - 125)
        put_text(F, name, xl, y[0] + 44, 42, 'serif', col * 1.1, a, 300, glow=0.3)
        put_text(F, cap, xl, y[0] + 100, 21, 'sans_l', WHITE * 0.85, a, 200, lh=1.35)
    xm, ym, _ = cam.project(np.array([[0, -0.1, 0]], np.float32))
    put_text(F, '金钱', xm[0], ym[0] + 44, 42, 'serif', GOLD_HI, smooth(u / 0.8) * (1 - conv), 300, glow=0.3)
    # 光束汇聚到一点
    if conv > 0:
        F *= (1 - 0.6 * conv)
        yy, xx = np.ogrid[0:H, 0:W]
        F += (np.exp(-((xx - CONV_PT[0]) ** 2 + (yy - CONV_PT[1]) ** 2) / (2 * (25 + 70 * conv) ** 2)) * conv * 2.2)[..., None] * np.array([1.0, 0.88, 0.6], np.float32)
    footnote(F, '类比，不是等式：这些领域没有固定的"收益率"；共同点是持续积累、避免不可逆的损失', (1 - conv) * smooth(u / 1.5), y=1680, size=19)
    # 最后的一句话
    fa = win(t, START['N23'] - 0.2, A['final'] + 1.8, 0.6, 0.8)
    if fa > 0:
        r = clamp01((t - START['N23'] + 0.2) / 3.0)
        gold_text(F, '变化越快，', W / 2, 720, 92, 'serif', fa, clamp01(r * 3), glow=0.4)
        gold_text(F, '越需要知道，', W / 2, 860, 92, 'serif', fa, clamp01(r * 3 - 1), glow=0.4)
        gold_text(F, '什么值得长期积累。', W / 2, 1000, 92, 'serif', fa, clamp01(r * 3 - 2), glow=0.5, sweep=(t - A['final'] + 0.2) / 1.2)
    return F


# ================================================================== SC8 品牌片尾（223.4 – 236.86）
import brand_bridge as BB
LOGO_PX = 220                  # brand/BRAND.md：片尾 logo 约 220px 居中
LOGO_CY = 800


@lru_cache(None)
def _logo_pts():
    rgb, a = BB.load_logo(LOGO_PX)
    ys, xs = np.where(a > 0.5)
    r = np.random.default_rng(8)
    idx = r.choice(len(xs), 6000, replace=len(xs) < 6000)
    pts = np.stack([xs[idx], ys[idx]], 1).astype(np.float32) + r.uniform(0, 1, (6000, 2)).astype(np.float32)
    pts += np.array([W / 2 - LOGO_PX / 2, LOGO_CY - LOGO_PX / 2], np.float32)
    cols = rgb[ys[idx], xs[idx]].astype(np.float32)
    ang = r.uniform(0, 2 * np.pi, 6000); rad = r.gamma(2.0, 160, 6000)
    burst = np.stack([np.cos(ang) * rad, np.sin(ang) * rad], 1).astype(np.float32)   # 从最后的光点向外炸开的位移
    return pts, cols, burst


@lru_cache(None)
def _brand_text(size_title):
    """主标题「巴芒价值」+ 小字「BUFFETT · MUNGER」（与主标题等宽），字体/颜色取自 brand/"""
    from PIL import Image, ImageDraw
    S = BB.SPEC
    f1 = BB.brand_font(S['title_font'], size_title)
    im = Image.new('L', (int(f1.getlength(S['title']) + 60), int(size_title * 1.6)), 0)
    ImageDraw.Draw(im).text((20, int(size_title * 1.25)), S['title'], font=f1, fill=255, anchor='ls')
    t1 = np.asarray(im, np.float32) / 255
    ys, xs = np.where(t1 > 0.01); t1 = t1[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    sub_px = size_title * S['sub_px'] / S['title_px']
    f2 = BB.brand_font(S['sub_font'], int(sub_px * 2)) # 2 倍绘制再缩放，保证小字清晰
    nat = sum(f2.getlength(c) for c in S['sub'])
    tr = (t1.shape[1] * 2 - nat) / (len(S['sub']) - 1)
    im = Image.new('L', (int(nat + tr * len(S['sub']) + 40), int(sub_px * 4)), 0)
    d = ImageDraw.Draw(im); x = 10
    for ch in S['sub']:
        d.text((x, int(sub_px * 2.8)), ch, font=f2, fill=255, anchor='ls'); x += f2.getlength(ch) + tr
    t2 = np.asarray(im, np.float32) / 255
    ys, xs = np.where(t2 > 0.01); t2 = t2[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    t2 = cv2.resize(t2, (t1.shape[1], max(int(t2.shape[0] / 2), 1)), interpolation=cv2.INTER_AREA)
    return t1, t2, int(S['sub_gap_px'] * size_title / S['title_px'])


def _paste_rgba(F, rgb, a, x0, y0, alpha=1.0):
    h, w = a.shape
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if X1 <= X0 or Y1 <= Y0: return
    aa = (a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] * alpha)[..., None]
    reg = F[Y0:Y1, X0:X1]
    reg *= (1 - aa)
    reg += aa * (rgb[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] if rgb.ndim == 3 else rgb)


def sc_brand(t):
    u = t - A['final']
    F = backdrop(t, c1=(0.01, 0.012, 0.02), c2=(0.02, 0.025, 0.04), neb=(0.10, 0.14, 0.26), neb_amt=0.25 * smooth(u / 2), drift=0.3)
    pts, cols, burst = _logo_pts()
    # 0) 上一幕汇聚的光点在重拍上炸开
    F += np.float32(0.7 * math.exp(-u * 8)) * np.array([1.0, 0.9, 0.7], np.float32) * (u >= 0)
    yy, xx = np.ogrid[0:H, 0:W]
    F += (np.exp(-((xx - CONV_PT[0]) ** 2 + (yy - CONV_PT[1]) ** 2) / (2 * 90.0 ** 2)) * 2.0 * math.exp(-u * 2.5))[..., None] * np.array([1.0, 0.88, 0.6], np.float32)
    # 1) 光点汇聚成官方 logo 的形状（只用 logo 透明通道采样，最终显示原始 logo）
    out = 1 - math.exp(-u * 3.0)
    conv = ease_io(clamp01((u - 0.35) / 1.7))
    fade_p = 1 - smooth((u - 1.8) / 0.6)
    if fade_p > 0:
        swirl = (1 - conv) * 1.2
        c, s = math.cos(swirl), math.sin(swirl)
        st = np.array(CONV_PT, np.float32) + (burst * out) @ np.array([[c, -s], [s, c]], np.float32)
        xy = st * (1 - conv) + pts * conv
        colp = cols * conv + GOLD * (1 - conv)
        splat(F, xy[:, 0], xy[:, 1], np.full(len(xy), 1.1 + 1.6 * (1 - conv), np.float32), colp * 1.2, 0.8 * fade_p)
    # 2) 清晰的原始 logo 居中浮现（含淡蓝光晕）
    la = smooth((u - 1.5) / 0.8)
    if la > 0:
        rgb, a = BB.load_logo(LOGO_PX)
        x0, y0 = int(W / 2 - LOGO_PX / 2), int(LOGO_CY - LOGO_PX / 2)
        S_ = BB.SPEC
        glow = blur(np.pad(a, 60), S_['glow_sigma'] * LOGO_PX / S_['logo_px']) * S_['glow_strength'] * 1.6
        gx0, gy0 = x0 - 60, y0 - 60
        reg = F[gy0:gy0 + glow.shape[0], gx0:gx0 + glow.shape[1]]
        reg += glow[:reg.shape[0], :reg.shape[1], None] * (np.array(S_['glow_rgb'], np.float32) / 255) * la
        _paste_rgba(F, rgb, a, x0, y0, la)
    # 3) 金色「巴芒价值」随重拍出现 + 小字 BUFFETT · MUNGER + 流光
    bt = t - A['brand_hit']
    if bt > -0.05:
        t1, t2, gap = _brand_text(104)
        ta = smooth((bt + 0.05) / 0.35)
        sc = 1.0 + 0.06 * (1 - ease_out(clamp01(bt / 0.6)))
        if sc != 1.0:
            t1s = cv2.resize(t1, (int(t1.shape[1] * sc), int(t1.shape[0] * sc)), interpolation=cv2.INTER_LINEAR)
        else:
            t1s = t1
        ramp = BB.gold_ramp(t1s.shape[0])[:, None, :] * np.ones((1, t1s.shape[1], 1), np.float32)
        sw = (bt - 0.6) / 1.4                                           # 流光：约 1.4 秒
        if 0 <= sw <= 1:
            xs = np.arange(t1s.shape[1])[None, :] + np.arange(t1s.shape[0])[:, None] * 0.6
            pos = -80 + (0.5 - 0.5 * math.cos(sw * math.pi)) * (t1s.shape[1] + 160)
            ramp = np.clip(ramp + np.exp(-((xs - pos) / 40) ** 2)[..., None] * 0.6, 0, 1.25)
        ty = LOGO_CY + LOGO_PX / 2 + 70
        x1 = int(W / 2 - t1s.shape[1] / 2); y1 = int(ty)
        sh = blur(np.pad(t1s, 20), 6) * 0.6 * ta
        reg = F[y1 - 20:y1 - 20 + sh.shape[0], x1 - 20:x1 - 20 + sh.shape[1]]
        reg *= (1 - sh[:reg.shape[0], :reg.shape[1], None])
        _paste_rgba(F, ramp, t1s, x1, y1, ta)
        sa = smooth((bt - 0.25) / 0.5)
        _paste_rgba(F, BB.sub_gold() * np.ones((*t2.shape, 3), np.float32), t2, int(W / 2 - t2.shape[1] / 2), int(ty + t1.shape[0] + gap), sa)
        # 4) 细金线引出关注语
        lt = ease_out(clamp01((bt - 2.2) / 0.9))
        ly = ty + t1.shape[0] + gap + t2.shape[0] + 70
        if lt > 0:
            lay = np.zeros((H, W, 3), np.float32)
            glow_line(lay, [(W / 2 - 300 * lt, ly), (W / 2 + 300 * lt, ly)], GOLD, 1.2, 0.5, 0.9)
            F += lay
        put_text(F, '关注「巴芒价值」，传承大师智慧，领悟投资真谛', W / 2, ly + 70, 38, 'serif_m', np.array([1.0, 0.93, 0.78]),
                 smooth((bt - 2.8) / 0.8), 1000, reveal=clamp01((bt - 2.8) / 1.4), glow=0.12)
    # 资料与授权（小字）
    ca = smooth((u - 5.0) / 1.0)
    footnote(F, '引语出处：Columbia Business School 录像（2026.10.05）· 伯克希尔致股东信（1989/1996/2017/2022）· BBC（2009）· C-SPAN（1991）\n'
                '图片：美国国际贸易署（公有领域）· TEDizen（CC BY 2.0）　旁白：AI 配音（Gemini TTS）　配乐：AI 生成（Lyria）',
             ca * 0.9, y=1660, size=21)
    return F


def SHOW_SUB(t):
    # 最后一句以大字呈现，不再重复字幕
    return not (START['N23'] - 0.3 <= t <= A['final'] + 2)


EXTRA_SCENES += [
    ('sc_climax', A['climax'], A['final']),
    ('sc_brand', A['final'], A['end'] + 1),
]
