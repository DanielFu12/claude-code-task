"""公共部件：音乐同步、背景、星尘、旁白、章节、片头片尾通用元素。"""
import json, math, os, sys
import numpy as np, cv2
from engine import *  # noqa

ROOT = os.path.abspath(os.path.join(HERE, '..'))
WORK = os.environ.get('WORK', os.path.join(ROOT, 'work'))
MUSIC = json.load(open(os.path.join(WORK, 'music.json')))
DUR = MUSIC['duration']
BEATS = np.array(MUSIC['beats'])
SRCB = np.array(MUSIC['src_beat'])
ONSET = np.array(MUSIC['onset'], np.float32)
LOW = np.array(MUSIC['low'], np.float32)
RMS = np.array(MUSIC['rms'], np.float32)
PER = MUSIC['period']

# 关键时间点（由 audio.py 的拼接方案决定；这里写死并校验）
T_D1, T_D2, T_D3, T_D4 = 17.14, 93.66, 157.41, 250.92          # 四个重拍
T_L1, T_L2, T_L3 = 78.78, 142.53, 236.04                       # 轻段
T_B1, T_B2, T_B3 = 87.29, 151.03, 244.54                       # 抽空段
for a, b in zip((T_D1, T_D2, T_D3, T_D4), MUSIC['events']['drop']):
    assert abs(a - b) < 0.06, (a, b)
END = DUR

DOWNBEATS = BEATS[SRCB % 4 == 0]


def fidx(t):
    return min(max(int(t * FPS), 0), len(ONSET) - 1)


def onset(t):
    i = fidx(t); seg = ONSET[max(0, i - 3):i + 1]
    w = np.exp(-np.arange(len(seg))[::-1] / 1.6)
    return float(min(1.6, (seg * w).max()))


def low(t):
    return float(LOW[fidx(t)])


def beat_pulse(t, decay=0.14):
    k = np.searchsorted(BEATS, t) - 1
    if k < 0: return 0.0
    return math.exp(-(t - BEATS[k]) / decay)


def bar_pulse(t, decay=0.3):
    k = np.searchsorted(DOWNBEATS, t) - 1
    if k < 0: return 0.0
    return math.exp(-(t - DOWNBEATS[k]) / decay)


HBEATS = np.array(MUSIC.get('heartbeats', []))


def heart(t):
    """心跳音效对应的画面脉冲（lub-dub 两下）"""
    k = np.searchsorted(HBEATS, t) - 1
    if k < 0: return 0.0
    x = t - HBEATS[k]
    v = math.exp(-x / 0.12)
    if x > 0.21: v += 0.6 * math.exp(-(x - 0.21) / 0.1)
    return v if x < 1.2 else 0.0


def heart_ring(f, x, y, t, col=WHITE, a=1.0):
    k = np.searchsorted(HBEATS, t) - 1
    if k < 0: return
    dt = t - HBEATS[k]
    if dt > 1.0: return
    hp = heart(t)
    f.glow((x, y), 14 + 10 * hp, col, 0.5 * hp * a)
    f.circle((x, y), 10 + 90 * eo(dt / 0.9), col, a * 0.45 * (1 - dt / 1.0), 1)


def energy(t):
    """0..1：抽空段和片尾低，主段高"""
    return float(cl(RMS[fidx(t)] * 1.1))


def in_break(t):
    return (10.76 <= t < T_D1) or (T_B1 <= t < T_D2) or (T_B2 <= t < T_D3) or (T_B3 <= t < T_D4)


# ---------------------------------------------------------------- 背景：情绪色调随章节变化
def _nebula(seed, c1, c2, k1=0.06, k2=0.05):
    n1 = fbm(W // 4, H // 4, seed, 5, 3)
    n2 = fbm(W // 4, H // 4, seed + 1, 5, 2)
    yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
    r = np.sqrt(((xx - W / 8) / (W / 4)) ** 2 + ((yy - H / 8) / (H / 4)) ** 2)
    v = np.exp(-r * r * 2.2)
    img = (n1 ** 2.2)[..., None] * np.array(c1, np.float32) * k1 + (n2 ** 3)[..., None] * np.array(c2, np.float32) * k2
    img = img * (0.35 + 0.65 * v[..., None])
    return cv2.resize(img, (W, H), interpolation=cv2.INTER_CUBIC)


BASE = np.array([0.010, 0.013, 0.024], np.float32)
_vy = (np.linspace(0, 1, H, dtype=np.float32)[:, None, None])
BASE_IMG = BASE + np.array([0.008, 0.010, 0.020], np.float32) * np.exp(-((_vy - 0.45) / 0.45) ** 2)
BASE_IMG = np.broadcast_to(BASE_IMG, (H, W, 3)).astype(np.float32)
MOODS = {
    'neutral': _nebula(11, C(60, 90, 180), C(120, 80, 200), 0.05, 0.03),
    'greed': _nebula(21, C(255, 70, 70), C(255, 150, 60), 0.075, 0.05),
    'fear': _nebula(31, C(20, 200, 150), C(40, 120, 255), 0.07, 0.05),
    'gold': _nebula(41, C(255, 190, 90), C(255, 230, 170), 0.07, 0.04),
    'void': np.zeros((H, W, 3), np.float32),
}
MOOD_KEYS = [
    (0, 'neutral'), (6, 'greed'), (10.76, 'void'), (T_D1, 'greed'), (T_L1, 'greed'), (T_B1, 'void'),
    (T_D2, 'fear'), (T_L2, 'neutral'), (T_B2, 'void'), (T_D3, 'gold'), (208.4, 'neutral'), (217, 'gold'),
    (T_B3, 'void'), (T_D4, 'gold'), (END, 'void'),
]


def background(t):
    k = max(i for i, (tt, _) in enumerate(MOOD_KEYS) if tt <= t)
    t0, m0 = MOOD_KEYS[k]
    if k + 1 < len(MOOD_KEYS):
        t1, m1 = MOOD_KEYS[k + 1]
    else:
        t1, m1 = t0 + 1, m0
    # 每段的前 1.2 秒内从上一个色调渐变过来
    prev = MOOD_KEYS[k - 1][1] if k > 0 else m0
    x = eio((t - t0) / 1.2)
    img = BASE_IMG + MOODS[prev] * (1 - x) + MOODS[m0] * x
    br = 1.0 + 0.25 * bar_pulse(t, 0.5) * energy(t)
    return img * br


# ---------------------------------------------------------------- 星尘（视差、重拍时跃迁）
_r = np.random.default_rng(3)
DUST_N = 1400
DUST = np.c_[_r.random(DUST_N) * W, _r.random(DUST_N) * H]
DUST_Z = _r.random(DUST_N) ** 1.8 * 0.9 + 0.1
DUST_A = (_r.random(DUST_N) ** 3 * 0.5 + 0.05) * DUST_Z
DUST_PH = _r.random(DUST_N) * 6.28


def warp_amount(t):
    v = 0.0
    for d in (T_D1, T_D2, T_D3, T_D4):
        if d - 0.6 < t < d + 2.0:
            v = max(v, eo((t - d + 0.6) / 0.6) * (1 - eio((t - d) / 2.0)))
    return v


def draw_dust(f, t, a=1.0, col=(0.85, 0.88, 1.0)):
    drift = t * 6.0
    x = (DUST[:, 0] + drift * DUST_Z * 2.0) % W
    y = (DUST[:, 1] - drift * DUST_Z * 0.6) % H
    tw = DUST_A * (0.6 + 0.4 * np.sin(1.3 * t + DUST_PH)) * a
    wa = warp_amount(t)
    if wa > 0.01:
        cx, cy = W / 2, H / 2
        dx, dy = x - cx, y - cy
        s = 1 + wa * DUST_Z * 0.35
        x, y = cx + dx * s, cy + dy * s
        # 径向拖尾
        for k in range(1, 5):
            sk = 1 + wa * DUST_Z * 0.35 * (1 - k * 0.18)
            f.splat(cx + dx * sk, cy + dy * sk, col, tw * 0.5 * wa, 'L')
    f.splat(x, y, col, tw, 'L')


# ---------------------------------------------------------------- 旁白
NARR = []          # (t0, t1, text)


def narr(t0, t1, s):
    NARR.append((t0, t1, s))


def draw_narration(f, t):
    L = sorted(NARR)
    for i, (t0, t1, s) in enumerate(L):
        nxt = L[i + 1][0] if i + 1 < len(L) else 1e9
        fo = 0.3
        if t1 + fo > nxt - 0.02:              # 下一句开始前必须完全淡出，不叠字
            fo = 0.14
            t1 = min(t1, nxt - 0.02 - fo)
        if t0 - 0.05 <= t <= t1 + fo:
            a = env(t, t0, t1, 0.25, fo)
            size = 38 if len(strip(s)) <= 26 else 34
            f.text(s, W / 2, 978, size, 'serif_med', INK, a, 'm', track=0.06, mode='O',
                   t0=t0, stag=0.012, dur=0.3, rise=8, hl=GOLD)


def narration_active(t):
    return any(t0 - 0.3 <= t <= t1 + 0.6 for t0, t1, _ in NARR)


# ---------------------------------------------------------------- 章节与界面
CHAPTERS = [
    (0.0, '序', 'PROLOGUE'),
    (T_D1, '01 上山', 'GREED'),
    (T_L1, '山顶', 'THE TOP'),
    (T_D2, '02 下山', 'FEAR'),
    (T_L2, '镜子', 'THE MIRROR'),
    (T_D3, '03 清醒', 'REASON'),
    (208.40, '04 纪律', 'DISCIPLINE'),
    (T_L3, '终章', 'EPILOGUE'),
]


def chrome_alpha(t):
    return env(t, 23.6, 247.0, 1.2, 1.0)


def draw_chrome(f, t):
    a = chrome_alpha(t)
    if a <= 0.003: return
    # 左上：片名
    f.text('你为什么总买在山顶？', 60, 52, 21, 'serif_med', INK, 0.82 * a, 'l', track=0.12, mode='O')
    f.text('WHY WE ALWAYS BUY AT THE TOP', 61, 82, 11, 'mono', GREY, 0.75 * a, 'l', track=0.32, mode='O')
    # 当前章节
    cur = max(i for i, c in enumerate(CHAPTERS) if c[0] <= t)
    name, en = CHAPTERS[cur][1], CHAPTERS[cur][2]
    k = eo((t - CHAPTERS[cur][0] - 0.3) / 0.8)
    f.line((61, 104), (61 + 30 * k, 104), GOLD, 0.7 * a, 1, buf='L')
    f.text(name, 102, 104, 14, 'sans_med', GOLD, 0.85 * a * k, 'l', track=0.15, mode='O')
    f.text(en, 102 + text_width(name, 'sans_med', 14, 0.15) + 14, 104, 10, 'mono', GREY, 0.7 * a * k, 'l',
           track=0.3, mode='O')
    # 底部：时间轴
    x0, x1, y = 60, 1860, 1046
    f.line((x0, y), (x1, y), WHITE, 0.10 * a, 1, buf='L')
    xp = x0 + (x1 - x0) * t / DUR
    f.line((x0, y), (xp, y), GOLD, 0.55 * a, 1, buf='L')
    for i, (c0, nm, _) in enumerate(CHAPTERS):
        x = x0 + (x1 - x0) * c0 / DUR
        done = t >= c0
        f.line((x, y - 6), (x, y), GOLD if done else WHITE, (0.6 if done else 0.25) * a, 1, buf='L')
        f.text(nm, x + 5, y - 12, 11, 'sans_med', GOLD if i == cur else GREY, (0.9 if i == cur else 0.5) * a, 'l',
               track=0.1, mode='O')
    bp = beat_pulse(t, 0.2)
    f.disc((xp, y), 2.2 + 2.5 * bp, GOLD, 0.9 * a, 'E')


def chapter_card(f, t, t0, num, title, sub, x=160, y=470, hold=2.4):
    """大号章节卡：01 + 标题 + 英文，带金线"""
    a = env(t, t0, t0 + hold, 0.5, 0.6)
    if a <= 0.003: return
    p = eo((t - t0) / 0.9)
    f.darken_rect(0, y - 190, 900, y + 150, 0.45 * a)
    f.text(num, x, y - 70, 150, 'corm', GOLD, a * 0.95, 'l', track=0.02, mode='O', t0=t0, stag=0.06, dur=0.6, rise=30)
    f.line((x, y + 20), (x + 380 * p, y + 20), GOLD, a * 0.8, 1, buf='E')
    f.text(title, x, y + 70, 54, 'serif_black', INK, a, 'l', track=0.18, mode='O', t0=t0 + 0.15, stag=0.05,
           dur=0.5, rise=20)
    f.text(sub, x + 2, y + 122, 15, 'mono', GREY, a * 0.85, 'l', track=0.35, mode='O', t0=t0 + 0.35, stag=0.01,
           dur=0.4, rise=8)


def scene_tag(f, t, t0, cn, en, t_end, big_dur=1.9):
    """机制标题：先在中间放大出现，再缩到左上角常驻"""
    if t < t0 or t > t_end + 0.5: return
    a = env(t, t0, t_end, 0.4, 0.5)
    m = eio((t - t0 - big_dur) / 0.7)        # 0 = 居中大字, 1 = 角落小字
    x = lerp(W / 2, 160, m); y = lerp(150, 168, m)
    s1 = int(round(lerp(64, 30, m))); s2 = int(round(lerp(16, 11, m)))
    anc = 'm' if m < 0.5 else 'l'
    if m < 0.5:
        aa = a * (1 - eio(m * 2))
        f.text(cn, W / 2, 150, 64, 'serif_black', INK, aa, 'm', track=0.25, mode='O', t0=t0, stag=0.05, dur=0.5,
               rise=16, glow=0.0)
        f.text(en, W / 2, 210, 16, 'mono', GOLD, aa * 0.9, 'm', track=0.4, mode='O', t0=t0 + 0.2, stag=0.01, dur=0.4)
        ln = 200 * eo((t - t0) / 0.8)
        f.line((W / 2 - ln, 238), (W / 2 + ln, 238), GOLD, aa * 0.5, 1, buf='L')
    else:
        aa = a * eio((m - 0.5) * 2)
        f.line((160, 150), (160, 186), GOLD, aa * 0.9, 2, buf='L')
        f.text(cn, 176, 160, 30, 'serif_black', INK, aa, 'l', track=0.15, mode='O')
        f.text(en, 177, 190, 11, 'mono', GOLD, aa * 0.85, 'l', track=0.35, mode='O')


# ---------------------------------------------------------------- 主角「你」
def draw_you(f, x, y, a=1.0, col=WHITE, label='你', t=0.0, r=5.0, ring=True, lab_dy=-30):
    if a <= 0.003: return
    f.disc((x, y), r, col, a, 'E')
    f.glow((x, y), r * 3.2, col, 0.55 * a)
    if ring:
        ph = (t * 0.8) % 1.0
        f.circle((x, y), r + 6 + 26 * ph, col, a * 0.5 * (1 - ph), 1)
    if label:
        f.text(label, x, y + lab_dy, 22, 'serif_bold', col, a, 'm', mode='O')


# ---------------------------------------------------------------- 曲线工具
def smooth_noise(n, seed, k=9):
    r = np.random.default_rng(seed).standard_normal(n)
    r = np.convolve(r, np.ones(k) / k, mode='same')
    return r / (np.abs(r).max() + 1e-9)


def polyline_upto(xs, ys, u):
    """前 u (0..1) 部分的折线；返回点集与端点"""
    n = len(xs)
    fi = u * (n - 1)
    i = int(fi)
    if i >= n - 1:
        return np.c_[xs, ys], (xs[-1], ys[-1])
    fr = fi - i
    hx = xs[i] + (xs[i + 1] - xs[i]) * fr
    hy = ys[i] + (ys[i + 1] - ys[i]) * fr
    pts = np.c_[np.r_[xs[:i + 1], hx], np.r_[ys[:i + 1], hy]]
    return pts, (hx, hy)


def draw_price(f, pts, a=1.0, th=2, glow=True, colorize=True, col=None, buf='E', smooth=1):
    """按涨跌着色的价格线：上涨红、下跌绿（A 股习惯）；smooth>1 时按平滑后的趋势着色"""
    if len(pts) < 2 or a <= 0.003: return
    if not colorize:
        f.poly(pts, col, a, th, buf=buf); return
    yy = pts[:, 1]
    if smooth > 1 and len(yy) > smooth:
        yy = np.convolve(np.r_[[yy[0]] * smooth, yy, [yy[-1]] * smooth], np.ones(smooth) / smooth, 'same')[smooth:-smooth]
    dy = np.diff(yy)
    up = dy <= 0
    # 合并同色连续段
    start = 0
    for i in range(1, len(up) + 1):
        if i == len(up) or up[i] != up[start]:
            seg = pts[start:i + 1]
            f.poly(seg, UP if up[start] else DOWN, a, th, buf=buf)
            start = i


def sample_mask_points(mask, n, seed, thr=0.3, jitter=1.0):
    ys, xs = np.nonzero(mask > thr)
    r = np.random.default_rng(seed)
    w = mask[ys, xs].astype(np.float64)
    pick = r.choice(len(xs), n, replace=len(xs) < n, p=w / w.sum())
    return np.c_[xs[pick] + r.random(n) * jitter, ys[pick] + r.random(n) * jitter]
