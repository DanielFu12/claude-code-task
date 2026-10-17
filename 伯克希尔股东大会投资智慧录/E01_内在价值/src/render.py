"""《伯克希尔股东大会投资智慧录》第一集 · 内在价值 —— 逐帧渲染（1080×1920，30fps）。

用法：
    python3 render.py nframes WORK                 # 输出总帧数
    python3 render.py chunk A B OUT.mp4 WORK       # 渲染 [A, B) 帧（无声）
    python3 render.py stills OUT_DIR WORK t1 t2 …  # 输出若干时间点的单帧 PNG
所有画面都是时间 t 的纯函数；时间点全部来自 WORK/timeline.json。
"""
import json, math, os, subprocess, sys
import numpy as np, cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'brand'))
from gfx import *                      # noqa: F401,F403
import gfx
import brand as B                      # 仓库根目录 brand/：官方角标、logo 与品牌字体
from script import PIC_BOX

WORK = sys.argv[-1] if len(sys.argv) > 2 else os.path.join(HERE, '..', 'work')
TL = json.load(open(os.path.join(WORK, 'timeline.json')))
FPS = TL['fps']
ENV = np.load(os.path.join(WORK, 'orig_env.npy'))

# ---------------------------------------------------------------- 品牌（只用 brand/ 里的官方资产）
HUD = B.Hud(scale=1.0, frame_w=W)                     # 右上角角标：logo + 巴芒价值 + BUFFETT · MUNGER，含流光
LOGO_PX = 240
LOGO_RGB, LOGO_A = B.load_logo(LOGO_PX)               # 片尾 logo：官方 logo_baman.png，预乘 alpha 缩放
_lay = json.load(open(B.LAYOUT)); _k = _lay['k']
_lock = np.asarray(Image.open(B.LOCKUP_4X).convert('RGBA')).astype(np.float32) / 255
_tb = _lay['text_box']
_txt = _lock[_tb[1]:_tb[3], _tb[0]:_tb[2]]            # 官方预渲染的「巴芒价值」+「BUFFETT · MUNGER」（品牌金渐变）
_rows = np.where(_txt[..., 3].max(1) > 0.02)[0]
_gap = np.where(np.diff(_rows) > 3)[0]
_split = int(_rows[_gap[0]] + 2) if len(_gap) else int(_txt.shape[0] * 0.75)
END_SCALE = 0.78                                      # 4x 资产缩到片尾尺寸（主标题字高约 118px）


def _lock_part(a, b):
    p = _txt[a:b]
    w, h = int(p.shape[1] * END_SCALE), int(p.shape[0] * END_SCALE)
    rgb, al = B._resize_rgba(p[..., :3], p[..., 3], w, h)
    return rgb.astype(np.float32), al.astype(np.float32)


END_TITLE = _lock_part(0, _split)
END_SUB = _lock_part(_split, _txt.shape[0])

BG = make_background()
VIG = make_vignette()
GRAIN = make_grain()
STILL = cv2.cvtColor(cv2.imread(os.path.join(WORK, 'still_7800.png')), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
x0, y0, x1, y1 = PIC_BOX
STILL = cv2.fastNlMeansDenoisingColored((STILL[y0:y1, x0:x1] * 255).astype(np.uint8), None, 3, 3, 7, 21).astype(np.float32) / 255
STILL2 = cv2.cvtColor(cv2.imread(os.path.join(WORK, 'still_6000.png')), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
STILL2 = cv2.fastNlMeansDenoisingColored((STILL2[y0:y1, x0:x1] * 255).astype(np.uint8), None, 3, 3, 7, 21).astype(np.float32) / 255
CLIPS = {k: Clip(os.path.join(WORK, f'broll_{k}_c.mp4')) for k in (200, 1500, 6000, 7790, 8700)}
WIN_W, WIN_H = 1080, 438                              # 宽银幕窗口（≈2.47:1，与源画面干净区域同比例，不拉伸）

# ---------------------------------------------------------------- 时间点
INTRO, INS, SUM, END, QA = TL['intro'], TL['insight'], TL['summary'], TL['end'], TL['qa']
T_TITLE = TL['t_title']
VOD = {v['id']: v for part in (INTRO, INS, SUM) for v in part['vo']}
WORDS = {}
for part in (INTRO, INS, SUM):
    for w in part['words']:
        WORDS.setdefault(w['id'], []).append(w)
QSC = {s['scene']: s for s in QA['scenes']}
QSUB = {s['id']: s for s in QA['subs']}
T_CTX = TL['ctx']['t0']; T_Q = QA['t0']; T_QE = QA['t1']; T_INS = INS['t_card']; T_SUM = SUM['t0']


def wt(sid, sub, dflt=None):
    """口播 sid 中子串 sub 开始被读出的时刻"""
    ws = WORDS[sid]
    s = ''.join(w['w'] for w in ws)
    k = s.find(sub)
    if k < 0:
        return dflt if dflt is not None else VOD[sid]['t0']
    n = 0
    for w in ws:
        if n + len(w['w']) > k: return w['t']
        n += len(w['w'])
    return ws[-1]['t']


def span(*ids, pre=0.35, post=0.5):
    return VOD[ids[0]]['t0'] - pre, VOD[ids[-1]]['t1'] + post


def scene_env(t, a, b, fi=0.5, fo=0.5):
    return env(t, a, b, fi, fo)


def ofr(t):
    """原声频带包络（当前帧）"""
    i = min(int(t * FPS), len(ENV) - 1)
    return ENV[i]


# ---------------------------------------------------------------- 通用元素
def chapter_tag(img, t, title, a=1.0):
    if a <= 0.003: return
    text(img, '第一集 · 内在价值', 72, 66, 26, 'sans_med', SUB_GOLD, a * 0.95, 'l', track=0.12, shadow=0.3)
    line(img, (72, 92), (72 + 64, 92), SUB_GOLD, a * 0.7, 1)
    text(img, title, 72, 116, 22, 'sans', INK2, a * 0.85, 'l', track=0.08, shadow=0.3)


def waveform(img, t, cx, cy, w, hmax, a=1.0, n=24):
    if a <= 0.003: return
    e = ofr(t)
    bw = w / n
    for k in range(n):
        v = float(e[k]) if k < len(e) else 0.0
        hh = 2 + hmax * min(v, 1.0)
        x = cx - w / 2 + (k + 0.5) * bw
        rect(img, x - 1.5, cy - hh, x + 1.5, cy + hh, SUB_GOLD, a * (0.35 + 0.65 * min(v * 1.2, 1)))


def narr_sub(img, t, subs, y=1610, hide=()):
    for s in subs:
        if s['id'] in hide: continue
        if s['t0'] - 0.15 <= t <= s['t1'] + 0.15:
            a = env(t, s['t0'] - 0.12, s['t1'] + 0.12, 0.12, 0.14)
            text(img, s['text'], W / 2, y, 46, 'sans_med', INK, a, 'm', track=0.04, shadow=0.85, rise=(1 - a) * 6)


def orig_sub(img, t, s, a):
    """原声字幕：中文在上（主），英文在下"""
    zl = wrap(s['zh'], 'sans_med', 46, 940)
    el = wrap(s['en'], 'ebg', 36, 930, cjk=False)
    y = 1468
    for ln in zl:
        text(img, ln, W / 2, y, 46, 'sans_med', INK, a, 'm', track=0.03, shadow=0.85); y += 62
    y += 8
    for ln in el:
        text(img, ln, W / 2, y, 36, 'ebg', INK2 * 1.05, a * 0.95, 'm', shadow=0.85); y += 46


def dust(img, t, a=1.0, n=70, seed=5, col=None):
    """缓慢漂浮的金色微尘（克制，只在片名/总结/片尾）"""
    if a <= 0.003: return
    r = np.random.default_rng(seed)
    P = r.random((n, 6))
    for i in range(n):
        x = (P[i, 0] * W + 14 * math.sin(0.11 * t + P[i, 1] * 6.28)) % W
        y = (P[i, 2] * H - t * (6 + 10 * P[i, 3])) % H
        tw = 0.5 + 0.5 * math.sin(t * (0.6 + P[i, 4]) + P[i, 5] * 6.28)
        glow(img, (x, y), 1.2 + 1.6 * P[i, 3], col if col is not None else GOLD, a * 0.35 * tw)


# ---------------------------------------------------------------- 冷开场（0 – 7.4）：原声 + 同日静帧
def s_cold(img, t):
    a = env(t, 0.25, 6.95, 1.6, 0.55)
    if a <= 0: return
    z = 1.0 + 0.05 * eio(t / 7.0)
    window(img, grade(STILL, sat=0.45, gain=0.85), W / 2, 760, WIN_W, WIN_H, zoom=z, pan=(0.03, -0.02), a=a, blur_bg=0.55)
    text(img, '1994 · 伯克希尔股东大会 · 巴菲特原声', W / 2, 470, 28, 'sans_med', SUB_GOLD, a * 0.9, track=0.12, shadow=0.4)
    line(img, (W / 2 - 300, 510), (W / 2 + 300, 510), SUB_GOLD, a * 0.35, 1)
    waveform(img, t, W / 2, 1060, 420, 26, a * 0.9)
    for s in TL['cold_subs']:
        sa = env(t, s['t0'] - 0.1, s['t1'] + 0.1, 0.15, 0.2) * a
        if sa > 0: orig_sub(img, t, s, sa)


# ---------------------------------------------------------------- 片名（7.4 –）
def s_title(img, t):
    t1 = VOD['S1']['t1'] + 0.3
    a = env(t, T_TITLE - 0.05, t1, 0.05, 0.7)
    if a <= 0: return
    k = t - T_TITLE
    glow(img, (W / 2, 880), 260, GOLD * 0.25, math.exp(-max(k, 0) / 1.3) * a * 0.9)
    dust(img, t, a)
    text(img, '巴菲特与芒格', W / 2, 700, 42, 'serif_bold', SUB_GOLD, a * eo((k - 0.2) / 0.8), track=0.32, shadow=0.4)
    for sg in (-1, 1):
        L = 110 * eo((k - 0.3) / 1.0)
        line(img, (W / 2 + sg * 190, 700), (W / 2 + sg * (190 + L), 700), SUB_GOLD, a * 0.6, 1)
    sh = cl((k - 1.6) / 1.4) if 1.6 < k < 3.0 else None
    text(img, '伯克希尔股东大会', W / 2, 830, 96, 'serif_black', a=a, gold=True, wipe=eo(k / 1.1), shine=sh, track=0.04, glow=0.18)
    text(img, '投资智慧录', W / 2, 980, 132, 'serif_black', a=a, gold=True, wipe=eo((k - 0.25) / 1.1), shine=sh, track=0.08, glow=0.18)
    text(img, 'BERKSHIRE HATHAWAY · ANNUAL MEETING WISDOM', W / 2, 1100, 26, 'corm', SUB_GOLD * 0.9, a * eo((k - 1.0) / 1.0), track=0.2, shadow=0.3)
    ea = a * eo((k - 2.6) / 0.9)
    if ea > 0:
        rrect(img, W / 2 - 190, 1196, W / 2 + 190, 1268, 6, SUB_GOLD, ea * 0.55, 1)
        text(img, '第一集 · 内在价值', W / 2, 1232, 38, 'sans_med', INK, ea, track=0.14)


# ---------------------------------------------------------------- 系列片头口播
def s_intro(img, t):
    # S2：1994 至今 + 1994 年真实影像
    a0, b0 = span('S2', pre=0.5, post=0.0)
    b0 = VOD['S4']['t1'] + 0.6
    a = env(t, a0, b0, 0.6, 0.6)
    if a > 0:
        clip = 200 if t < VOD['S3']['t0'] else (1500 if t < VOD['S4']['t0'] else 6000)
        ct = t - a0 if clip == 200 else (t - VOD['S3']['t0'] if clip == 1500 else t - VOD['S4']['t0'])
        ct = ct % 15.5
        dim = 1.0 - 0.35 * env(t, VOD['S3']['t0'], b0, 0.6, 0.3)
        window(img, grade(CLIPS[clip].get(ct), gain=dim), W / 2, 640, WIN_W, WIN_H, zoom=1.03 + 0.0025 * ct, a=a, blur_bg=0.5)
        text(img, '1994 · 奥马哈 · 伯克希尔股东大会上午场实况', 72, 448, 24, 'sans', INK2, a * 0.9, 'l', track=0.06, shadow=0.5)
    # S2 时间轴
    a = env(t, VOD['S2']['t0'] - 0.3, VOD['S3']['t0'] - 0.1, 0.5, 0.4)
    if a > 0:
        p = eio((t - VOD['S2']['t0']) / (VOD['S2']['t1'] - VOD['S2']['t0']))
        xA, xB, yL = 130, 950, 1080
        line(img, (xA, yL), (xB, yL), INK3, a * 0.8, 1)
        for i, yr in enumerate(range(1994, 2027)):
            x = xA + (xB - xA) * i / 32
            big = yr in (1994, 2000, 2008, 2016, 2026)
            on = (i / 32) <= p
            line(img, (x, yL - (14 if big else 7)), (x, yL), GOLD if on else INK3, a * (0.95 if on else 0.6), 2 if big else 1)
            if big:
                text(img, str(yr), x, yL + 34, 24, 'inter', GOLD if on else INK3, a, shadow=0.3)
        glow(img, (xA + (xB - xA) * p, yL), 9, GOLD_HI, a * 0.9)
        text(img, '1994', 300, 1240, 120, 'corm_med', a=a, gold=True, track=0.02)
        text(img, '—', 540, 1240, 80, 'corm', SUB_GOLD, a * eo((t - wt('S2', '以来')) / 0.5))
        text(img, '至今', 770, 1240, 92, 'serif_bold', a=a * eo((t - wt('S2', '以来')) / 0.5), gold=True)
        text(img, '历届伯克希尔股东大会 · 问答精选', W / 2, 1360, 30, 'sans', INK2, a * eo((t - wt('S2', '历届')) / 0.6), track=0.1)
    # S3 八大主题，逐词点亮
    a = env(t, VOD['S3']['t0'] - 0.2, VOD['S3']['t1'] + 0.7, 0.4, 0.5)
    if a > 0:
        themes = ['价值投资', '企业估值', '商业模式', '竞争护城河', '风险管理', '市场周期', '投资心理', '人生智慧']
        keys = ['价值', '企业估值', '商业', '竞争', '风险', '市场', '投资心理', '人生']
        for i, (th, kk) in enumerate(zip(themes, keys)):
            tt = wt('S3', kk)
            k = eo((t - tt + 0.1) / 0.5)
            cx = 290 if i % 2 == 0 else 790; cy = 1000 + (i // 2) * 112
            text(img, f'{i + 1:02d}', cx - 170, cy, 24, 'inter_semi', GOLD, a * k, 'l', shadow=0.3)
            text(img, th, cx - 120, cy, 50, 'serif_bold', INK, a * k, 'l', track=0.06, rise=(1 - k) * 10)
        text(img, '经 典 问 答', W / 2, 1450, 26, 'sans', SUB_GOLD, a * eo((t - wt('S3', '经典')) / 0.5), track=0.3)
    # S4 每一期的结构
    a = env(t, VOD['S4']['t0'] - 0.2, VOD['S4']['t1'] + 0.6, 0.4, 0.5)
    if a > 0:
        steps = [('01', '原始问答', 'ORIGINAL Q&A', '原始视频'), ('02', '真实案例', 'BUSINESS CASES', '商业案例'),
                 ('03', '深度解读', 'INSIGHT', '深入解读')]
        for i, (n, zh, en, kk) in enumerate(steps):
            k = eo((t - wt('S4', kk) + 0.15) / 0.55)
            y = 1000 + i * 140
            circle(img, (170, y), 30, GOLD, a * k, 1)
            text(img, n, 170, y, 26, 'inter_semi', GOLD, a * k)
            text(img, zh, 230, y - 12, 50, 'serif_bold', INK, a * k, 'l', track=0.08)
            text(img, en, 232, y + 34, 22, 'corm_med', INK2, a * k, 'l', track=0.18, shadow=0.3)
            if i < 2:
                line(img, (170, y + 34), (170, y + 34 + 72 * eo((t - wt('S4', steps[i + 1][3]) + 0.4) / 0.5)), SUB_GOLD, a * 0.6, 1)
    # S5 说了什么 → 为什么这样思考
    a = env(t, VOD['S5']['t0'] - 0.2, VOD['S5']['t1'] + 0.55, 0.4, 0.5)
    if a > 0:
        tw_ = wt('S5', '更要')
        d = eo((t - tw_) / 0.5)
        text(img, '说了什么', W / 2, 780, 64, 'serif_med', INK2, a * (1 - 0.55 * d), track=0.1)
        if d > 0:
            ww = text_w('说了什么', 'serif_med', 64, 0.1)
            line(img, (W / 2 - ww / 2 - 10, 782), (W / 2 - ww / 2 - 10 + (ww + 20) * d, 782), INK2, a * 0.8, 2)
        text(img, '为什么这样思考', W / 2, 940, 92, 'serif_black', a=a, gold=True, wipe=eo((t - wt('S5', '他们')) / 0.9), glow=0.15)
    # S6–S7 投资与人生
    a = env(t, VOD['S6']['t0'] - 0.3, VOD['S7']['t1'] + 0.6, 0.5, 0.5)
    if a > 0:
        ct = (t - VOD['S6']['t0'] + 2) % 15.5
        window(img, grade(CLIPS[8700].get(ct), gain=0.9), W / 2, 600, WIN_W, WIN_H, zoom=1.04 + 0.002 * ct, a=a, blur_bg=0.5)
        text(img, '投资', 120, 920, 28, 'sans_med', GOLD, a, 'l', track=0.3)
        for i, (s, kk) in enumerate([('洞察企业价值', '洞察'), ('理性应对市场波动', '理性'), ('规避投资风险', '规避')]):
            k = eo((t - wt('S6', kk) + 0.1) / 0.5)
            text(img, s, 120, 990 + i * 70, 46, 'serif_bold', INK, a * k, 'l', track=0.05, rise=(1 - k) * 8)
        text(img, '人生', 120, 1230, 28, 'sans_med', GOLD, a * eo((t - VOD['S7']['t0']) / 0.5), 'l', track=0.3)
        for i, (s, kk) in enumerate([('做出更好的人生选择', '做出'), ('收获真正的幸福', '收获')]):
            k = eo((t - wt('S7', kk) + 0.1) / 0.5)
            text(img, s, 120, 1300 + i * 70, 46, 'serif_bold', INK, a * k, 'l', track=0.05, rise=(1 - k) * 8)
    # S8 理性 · 清醒 · 豁达
    a = env(t, VOD['S8']['t0'] - 0.2, VOD['S8']['t1'] + 0.7, 0.4, 0.6)
    if a > 0:
        text(img, '更系统的投资框架', W / 2, 700, 40, 'serif_med', INK2, a * eo((t - wt('S8', '建立')) / 0.6), track=0.12)
        for i, (s, kk) in enumerate([('理性', '理性'), ('清醒', '清醒'), ('豁达', '豁达')]):
            k = eo((t - wt('S8', kk) + 0.05) / 0.6)
            text(img, s, 230 + i * 310, 920, 112, 'serif_black', a=a * k, gold=True, glow=0.2 * k, rise=(1 - k) * 14)
        text(img, '处世哲学', W / 2, 1110, 40, 'serif_med', INK2, a * eo((t - wt('S8', '处世')) / 0.6), track=0.3)
    # S9–S11 回到 1994
    a = env(t, VOD['S9']['t0'] - 0.3, VOD['S11']['t1'] + 0.9, 0.5, 0.9)
    if a > 0:
        t9 = VOD['S9']['t0']
        p = eio((t - t9 - 0.6) / 2.6)
        yr = int(round(2026 - (2026 - 1994) * p))
        ys = 760 - 300 * eio((t - VOD['S10']['t0'] + 0.3) / 1.2)
        sz = 240 - 120 * eio((t - VOD['S10']['t0'] + 0.3) / 1.2)
        text(img, str(yr), W / 2, ys, sz, 'corm_med', a=a, gold=True, glow=0.25 * (1 if yr == 1994 else 0.4), track=0.02)
        text(img, 'OMAHA · NEBRASKA', W / 2, ys + sz * 0.62, 26, 'corm_med', SUB_GOLD, a * eo((t - t9 - 3.0) / 0.8) * (1 - eio((t - VOD['S10']['t0']) / 0.6)), track=0.3)
        wa = a * eo((t - VOD['S10']['t0'] + 0.2) / 0.9)
        if wa > 0:
            ct = (t - VOD['S10']['t0']) % 15.5
            window(img, grade(CLIPS[7790].get(ct), gain=0.92), W / 2, 820, WIN_W, WIN_H, zoom=1.02 + 0.003 * ct, a=wa, blur_bg=0.5)
            text(img, '1994 · 上午场实况（下午场问答仅存录音）', 72, 1066, 22, 'sans', INK2, wa * 0.85, 'l', track=0.05, shadow=0.5)
        qa_ = a * eo((t - VOD['S11']['t0'] + 0.1) / 0.6)
        if qa_ > 0:
            text(img, '一家企业的内在价值，', W / 2, 1230, 64, 'serif_black', a=qa_, gold=True, wipe=eo((t - VOD['S11']['t0'] + 0.1) / 0.9))
            text(img, '究竟该怎么算？', W / 2, 1330, 64, 'serif_black', a=qa_, gold=True, wipe=eo((t - wt('S11', '究竟')) / 0.8))
    narr_sub(img, t, INTRO['subs'], hide=('S11',))


# ---------------------------------------------------------------- 回到 1994：背景卡
def s_ctx(img, t):
    a = env(t, T_CTX, T_Q + 1.4, 0.6, 0.8)
    if a <= 0: return
    k = t - T_CTX
    text(img, '1994', W / 2, 760, 330, 'corm_med', GOLD * 0.55, a * 0.22, track=0.02, shadow=0)
    text(img, '1994 年 4 月 · 美国奥马哈', W / 2, 640, 34, 'sans_med', SUB_GOLD, a * eo(k / 0.6), track=0.12)
    text(img, '伯克希尔·哈撒韦年度股东大会', W / 2, 740, 58, 'serif_bold', INK, a * eo((k - 0.2) / 0.7), track=0.04)
    text(img, '下午场 · 股东问答', W / 2, 830, 44, 'serif_med', INK2, a * eo((k - 0.4) / 0.7), track=0.2)
    line(img, (W / 2 - 160, 900), (W / 2 + 160, 900), SUB_GOLD, a * 0.5 * eo((k - 0.5) / 0.6), 1)
    text(img, 'CNBC 巴菲特档案 · 第 22 章', W / 2, 960, 28, 'sans', INK2, a * eo((k - 0.7) / 0.7), track=0.06)
    text(img, 'Calculating intrinsic value', W / 2, 1010, 40, 'ebg_i', INK, a * eo((k - 0.8) / 0.7))
    na = a * eo((k - 1.3) / 0.8)
    rrect(img, 120, 1110, 960, 1280, 10, INK3, na * 0.8, 1)
    text(img, '这一段在档案中只保存了原始录音，没有现场画面。', W / 2, 1160, 30, 'sans', INK2, na, track=0.02)
    text(img, '以下声音为原始录音，未剪辑；画面为同日上午场静帧。', W / 2, 1225, 30, 'sans', INK2, na, track=0.02)


# ---------------------------------------------------------------- 原始问答
def qa_env(t, sc, fi=0.5, fo=0.5, pre=0.3, post=0.3):
    s = QSC.get(sc)
    if not s: return 0.0
    return env(t, s['t0'] - pre, s['t1'] + post, fi, fo)


def dcf_bars(img, t, a, mode, k_rise, k_disc, k_fog=0.0):
    """现金流柱：mode='dcf' 折现；fog 时看不清"""
    xA, xB, yb = 210, 960, 1290
    n = 10
    line(img, (130, yb), (xB + 10, yb), INK3, a, 1)
    pv_h = 0
    for i in range(n):
        x = xA + (xB - xA) * (i + 0.5) / n
        h0 = 110 + 9 * i
        h = h0 * eo((k_rise * 1.6 - i * 0.06))
        if h <= 0: continue
        disc = 1 / (1.10 ** (i + 1))
        hd = h * (1 - k_disc * (1 - disc))
        jit = 0
        if k_fog > 0:
            jit = k_fog * 38 * math.sin(t * (1.7 + i * 0.37) + i * 2.1)
            hd = max(10, hd + jit)
        col = GOLD if k_fog < 0.5 else INK3
        rect(img, x - 22, yb - hd, x + 22, yb, col, a * (0.85 - 0.45 * k_fog))
        if k_disc > 0 and k_fog == 0:
            rect(img, x - 22, yb - h, x + 22, yb - hd, GOLD, a * 0.18 * k_disc)
        if k_fog > 0:
            text(img, '?', x, yb - hd - 36, 40, 'ebg', INK2, a * k_fog)
        text(img, str(i + 1), x, yb + 28, 20, 'inter', INK3, a)
        pv_h += h0 * disc
    text(img, '第 N 年', 900, yb + 64, 20, 'sans', INK3, a, 'm')
    # 现值柱
    ph = pv_h * 0.32 * eio(k_disc)
    rect(img, 130, yb - ph, 180, yb, GOLD_HI if k_fog < 0.5 else INK3, a * (0.95 if k_fog < 0.5 else 0.5))
    text(img, '现值' if k_fog < 0.5 else '？', 155, yb + 30, 24, 'sans_med', GOLD if k_fog < 0.5 else INK2, a * max(eio(k_disc), k_fog))
    if 0.02 < k_disc < 0.98 and k_fog == 0:
        for i in range(n):
            x = xA + (xB - xA) * (i + 0.5) / n
            u = cl(k_disc * 1.3 - i * 0.03)
            px = lerp(x, 155, eio(u)); py = yb - 150 - 80 * math.sin(math.pi * u)
            glow(img, (px, py), 4, GOLD_HI, a * (1 - u) * 0.9)


def s_qa(img, t):
    a = env(t, T_Q + 0.6, T_QE + 0.6, 0.9, 0.9)
    if a <= 0: return
    chapter_tag(img, t, '原始问答 · 1994 下午场原声', a)
    # 提问时：巴菲特托腮倾听的静帧；回答时：同日上午场他讲话时的静帧（都是静帧，不冒充下午场的口型）
    ta = QA['answer_t']
    xf = eio((t - ta + 0.6) / 1.2)
    z1 = 1.0 + 0.06 * eio((t - T_Q) / (ta - T_Q))
    z2 = 1.0 + 0.08 * eio((t - ta) / (T_QE - ta))
    if xf < 1:
        window(img, grade(STILL, sat=0.5, gain=0.92), W / 2, 470, WIN_W, WIN_H, zoom=z1, pan=(-0.03 * eio((t - T_Q) / 40), -0.07), a=a, blur_bg=0.45)
    if xf > 0:
        window(img, grade(STILL2, sat=0.5, gain=0.92), W / 2, 470, WIN_W, WIN_H, zoom=z2, pan=(-0.05 * eio((t - ta) / 180), -0.06), a=a * xf, blur_bg=0.45 * xf)
    text(img, '画面：同日上午场静帧　｜　声音：下午场原始录音', 72, 712, 22, 'sans', INK3 * 1.25, a * 0.95, 'l', track=0.04, shadow=0.5)
    ans = t >= QA['answer_t'] - 0.2
    spk = '回答 · 沃伦·巴菲特' if ans else '提问 · 肖恩·巴里（加拿大里贾纳）'
    circle(img, (84, 790), 6, GOLD, a, fill=True)
    text(img, spk, 104, 790, 30, 'sans_med', INK, a, 'l', track=0.04)
    waveform(img, t, 860, 790, 260, 22, a)
    line(img, (72, 836), (1008, 836), INK3, a * 0.5, 1)
    # ---- 关键观点面板（y 880–1390）
    ka = qa_env(t, 'ask')
    if ka > 0:
        text(img, '股东的问题', W / 2, 960, 28, 'sans_med', GOLD, a * ka, track=0.3)
        text(img, '你们如何得出', W / 2, 1070, 60, 'serif_bold', INK, a * ka * eo((t - QSUB['Q4']['t0']) / 0.7))
        text(img, '一家企业的内在价值？', W / 2, 1160, 60, 'serif_bold', a=a * ka * eo((t - QSUB['Q5']['t0']) / 0.7), gold=True)
        text(img, '年报信息人人可得　·　会计准则并不完美', W / 2, 1270, 30, 'sans', INK2, a * ka * eo((t - QSUB['Q2']['t0']) / 0.7), track=0.04)
    ka = qa_env(t, 'open')
    if ka > 0:
        rrect(img, 250, 940, 830, 1300, 8, SUB_GOLD, a * ka * 0.6, 1)
        text(img, 'BERKSHIRE HATHAWAY INC.', W / 2, 1020, 28, 'corm_med', INK2, a * ka, track=0.08)
        text(img, '1992', W / 2, 1120, 96, 'corm_med', a=a * ka, gold=True)
        text(img, 'ANNUAL REPORT', W / 2, 1200, 30, 'corm_med', INK2, a * ka, track=0.3)
        text(img, '致股东信对此有专门论述', W / 2, 1255, 26, 'sans', INK3 * 1.3, a * ka, track=0.06)
    ka = max(qa_env(t, 'dcf'), qa_env(t, 'fog'))
    if ka > 0:
        s_d, s_f = QSC['dcf'], QSC['fog']
        k_rise = eo((t - s_d['t0']) / 1.6)
        k_disc = eio((t - QSUB['A3']['t0']) / 3.5)
        k_fog = eio((t - s_f['t0'] - 0.3) / 1.5)
        dcf_bars(img, t, a * ka, 'dcf', k_rise, k_disc, k_fog)
        h1 = 1 - k_fog
        text(img, '经济价值 ＝ 未来现金流的现值', W / 2, 960, 50, 'serif_bold', INK, a * ka * h1 * eo((t - s_d['t0']) / 0.8))
        if k_fog > 0:
            line1 = '看不清未来的现金流' if t < QSUB['A7']['t0'] else '就不知道它现在值多少'
            text(img, line1, W / 2, 960, 52, 'serif_bold', a=a * ka * k_fog, gold=True)
    ka = qa_env(t, 'dissonance')
    if ka > 0:
        k1 = eo((t - QSUB['A9']['t0']) / 0.7); k2 = eo((t - QSUB['A10']['t0']) / 0.7); k3 = eo((t - QSUB['A11']['t0'] - 0.8) / 0.8)
        text(img, '今天的股价', 290, 980, 44, 'serif_bold', INK, a * ka * k1)
        text(img, '“自以为知道”', 290, 1050, 32, 'sans', GOLD, a * ka * k1)
        text(img, '未来 20 年现金流', 790, 980, 44, 'serif_bold', INK, a * ka * k2)
        text(img, '“毫无概念”', 790, 1050, 32, 'sans', INK2, a * ka * k2)
        line(img, (540, 930), (540, 1090), INK3, a * ka * k2, 1)
        text(img, '认知失调', W / 2, 1230, 96, 'serif_black', a=a * ka * k3, gold=True, glow=0.2, wipe=k3)
    ka = qa_env(t, 'range')
    if ka > 0:
        x0_, x1_, yc = 150, 960, 1150
        k = eo((t - QSC['range']['t0']) / 1.2); k2 = eo((t - QSUB['A13']['t0']) / 1.2); k3 = eo((t - QSUB['A14']['t0']) / 1.0)
        line(img, (x0_, yc), (x0_ + (x1_ - x0_) * k, yc), INK3, a * ka, 1)
        n = 40
        top = [(x0_ + (x1_ - x0_) * i / n, yc - 8 - 165 * (i / n) ** 1.1 * k) for i in range(n + 1)]
        bot = [(x0_ + (x1_ - x0_) * i / n, yc + 8 + 165 * (i / n) ** 1.1 * k) for i in range(n + 1)]
        poly(img, top + bot[::-1], INK3, a * ka * 0.18, fill=True)
        poly(img, top, INK3, a * ka * 0.6, 1); poly(img, bot, INK3, a * ka * 0.6, 1)
        band_t = [(x0_ + (x1_ - x0_) * i / n, yc - 6 - 46 * (i / n) * k2) for i in range(n + 1)]
        band_b = [(x0_ + (x1_ - x0_) * i / n, yc + 6 + 46 * (i / n) * k2) for i in range(n + 1)]
        poly(img, band_t + band_b[::-1], GOLD, a * ka * 0.45 * k2, fill=True)
        text(img, '看不清：放进“太难”', 760, 955, 28, 'sans', INK2, a * ka * k, track=0.04)
        text(img, '高概率的区间', 820, 1150, 30, 'sans_med', GOLD_HI, a * ka * k2)
        if k3 > 0:
            for j in range(5):
                u = cl(k3 * 1.4 - j * 0.1)
                glow(img, (lerp(900, x0_, eio(u)), yc - 10 * math.sin(math.pi * u)), 5, GOLD_HI, a * ka * (1 - u))
            text(img, '→ 再折现回今天', 330, 1360, 30, 'sans_med', GOLD, a * ka * k3)
        text(img, '今天', x0_, yc + 44, 24, 'sans', INK2, a * ka * k)
    ka = qa_env(t, 'cert')
    if ka > 0:
        k1 = eo((t - QSUB['A15']['t0']) / 0.8); k2 = eo((t - QSUB['A16']['t0']) / 0.8)
        tilt = 0.16 * eio((t - QSUB['A17']['t0']) / 1.5)
        cx, cy, L = W / 2, 1120, 330
        dx, dy = math.cos(tilt), math.sin(tilt)
        pl = (cx - L * dx, cy + L * dy); pr = (cx + L * dx, cy - L * dy)
        line(img, pl, pr, INK2, a * ka * k1, 2)
        poly(img, [(cx, cy), (cx - 26, cy + 60), (cx + 26, cy + 60)], INK3, a * ka * k1, 2, closed=True)
        text(img, '确定性', pl[0] + 40, pl[1] + 70, 70, 'serif_black', a=a * ka * k1, gold=True, glow=0.15)
        text(img, '看起来最便宜', pr[0] - 40, pr[1] - 70, 40, 'serif_med', INK2, a * ka * k2)
        text(img, '但数字没把握', pr[0] - 40, pr[1] - 22, 26, 'sans', INK3 * 1.3, a * ka * eo((t - QSUB['A17']['t0']) / 0.8))
        text(img, '确定性　＞　看起来便宜', W / 2, 1350, 40, 'serif_bold', INK, a * ka * eo((t - QSUB['A18']['t0']) / 0.8), track=0.06)
    ka = qa_env(t, 'report')
    if ka > 0:
        k1 = eo((t - QSUB['A19']['t0']) / 0.8)
        dx0, dy0 = 160, 930
        rrect(img, dx0, dy0, dx0 + 300, dy0 + 380, 8, INK2, a * ka * k1, 1)
        text(img, '财务报表', dx0 + 150, dy0 + 50, 34, 'serif_bold', INK, a * ka * k1)
        for i in range(8):
            ww = 220 if i % 3 else 160
            line(img, (dx0 + 40, dy0 + 110 + i * 30), (dx0 + 40 + ww, dy0 + 110 + i * 30), INK3, a * ka * k1 * 0.9, 2)
        rx = 720
        rows = [('会计数字 ≠ 经济价值', 'A19', INK, 'serif_bold', 38), ('没有答案', 'A22', INK2, 'serif_black', 52),
                ('只有指引', 'A23', GOLD_HI, 'serif_black', 52), ('懂生意', 'A24', None, 'serif_black', 80),
                ('＞ 懂数学', 'A25', INK2, 'serif_med', 40)]
        ys = [990, 1090, 1170, 1280, 1370]
        for (s, sid, col, fn, sz), y in zip(rows, ys):
            k = eo((t - QSUB[sid]['t0']) / 0.7)
            if col is None:
                text(img, s, rx, y, sz, fn, a=a * ka * k, gold=True, glow=0.2)
            else:
                text(img, s, rx, y, sz, fn, col, a * ka * k)
    ka = qa_env(t, 'check')
    if ka > 0:
        k0 = eo((t - QSUB['A27']['t0']) / 0.8)
        text(img, '公寓楼　·　农场　·　小生意', W / 2, 950, 36, 'serif_med', INK2, a * ka * k0, track=0.06)
        items = [('现在要付出多少', 'A29'), ('将来能收回多少', 'A30'), ('有多大把握', 'A31'), ('与其他选择相比如何', 'A32')]
        for i, (s, sid) in enumerate(items):
            k = eo((t - QSUB[sid]['t0'] + 0.1) / 0.6)
            y = 1050 + i * 80
            circle(img, (230, y), 22, GOLD, a * ka * k, 1)
            text(img, str(i + 1), 230, y, 24, 'inter_semi', GOLD, a * ka * k)
            text(img, s, 280, y, 44, 'serif_bold', INK if i != 2 else GOLD_HI, a * ka * k, 'l', track=0.04, rise=(1 - k) * 8)
        text(img, '—— 只不过对象是大企业', W / 2 + 40, 1380, 30, 'sans', SUB_GOLD, a * ka * eo((t - QSUB['A33']['t0']) / 0.7))
    ka = qa_env(t, 'massage', post=0.9)
    if ka > 0:
        k1 = eo((t - QSUB['A34']['t0']) / 0.8)
        text(img, '会计数字：思考的向导', W / 2, 960, 44, 'serif_bold', INK, a * ka * k1)
        k2 = eio((t - QSUB['A36']['t0']) / 3.0)
        xs = [300, 420, 540, 660, 780]
        base = [120, 150, 135, 170, 160]
        yb = 1330
        line(img, (220, yb), (860, yb), INK3, a * ka * k1, 1)
        for x, h in zip(xs, base):
            hh = h * (1 + 0.9 * k2 * (0.6 + 0.4 * math.sin(x)))
            rect(img, x - 30, yb - hh, x + 30, yb, lerp(GOLD, BRICK, k2 * 0.8), a * ka * k1 * 0.85)
            if k2 > 0.05: rect(img, x - 30, yb - h - 1, x + 30, yb - h + 1, INK2, a * ka * k2)
        text(img, '最乐观的解释', 760, 1040, 30, 'sans', INK2, a * ka * eo((t - QSUB['A37']['t0']) / 0.7))
        text(img, '警惕粉饰数字', W / 2, 1410, 52, 'serif_black', BRICK * 1.15, a * ka * eo((t - QSUB['A38']['t0'] - 0.5) / 0.7), track=0.08)
    # ---- 字幕
    for s in QA['subs']:
        sa = env(t, s['t0'] - 0.05, s['t1'] + 0.05, 0.12, 0.15)
        if sa > 0: orig_sub(img, t, s, sa * a)
    la = env(t, TL['laugh']['t0'], TL['laugh']['t1'], 0.15, 0.2)
    if la > 0: text(img, '（现场笑声）', W / 2, 1490, 32, 'sans', INK2, la * a * 0.85, track=0.1)


# ---------------------------------------------------------------- 投资启示
def ins_span(*ids, pre=0.35, post=0.6):
    return VOD[ids[0]]['t0'] - pre, VOD[ids[-1]]['t1'] + post


def quote(img, lines, x, y, size, a, col=INK, name='ebg_i', lh=1.32):
    for i, ln in enumerate(lines):
        text(img, ln, x, y + i * size * lh, size, name, col, a, 'm', shadow=0.5)


def s_insight(img, t):
    # 标题卡
    a = env(t, T_INS - 0.05, VOD['I1']['t0'] - 0.25, 0.05, 0.6)
    if a > 0:
        k = t - T_INS
        glow(img, (W / 2, 880), 240, GOLD * 0.2, math.exp(-max(k, 0) / 1.2) * a)
        text(img, 'INSIGHT', W / 2, 760, 32, 'corm_med', SUB_GOLD, a * eo(k / 0.6), track=0.5)
        text(img, '投资启示', W / 2, 880, 120, 'serif_black', a=a, gold=True, wipe=eo(k / 1.0), glow=0.2)
        text(img, '以下为本片解读 · AI 配音 · 非巴菲特或芒格原话', W / 2, 1010, 28, 'sans', INK2, a * eo((k - 0.6) / 0.8), track=0.04)
    ta = env(t, VOD['I1']['t0'] - 0.4, VOD['I17']['t1'] + 0.8, 0.6, 0.6)
    chapter_tag(img, t, '投资启示 · 本片解读（AI 配音）', ta)
    # 公式
    a0, b0 = ins_span('I1', 'I3')
    a = env(t, a0, b0, 0.5, 0.5)
    if a > 0:
        k = eo((t - wt('I1', '一家')) / 0.9)
        hi = eio((t - wt('I3', '真正')) / 0.8)
        cy = 900
        dimc = lambda c: c * (1 - 0.55 * hi)
        text(img, 'V', 250, cy, 110, 'ebg_i', dimc(INK), a * k)
        text(img, '=', 345, cy, 90, 'ebg', dimc(INK2), a * k)
        text(img, 'Σ', 450, cy, 120, 'ebg', dimc(INK2), a * k)
        text(img, 'CF', 660, cy - 72, 92, 'ebg_i', GOLD_HI if hi > 0.5 else INK, a * k, glow=0.6 * hi, glow_col=GOLD)
        text(img, 't', 738, cy - 40, 52, 'ebg_i', GOLD_HI if hi > 0.5 else INK, a * k)
        line(img, (540, cy), (540 + 300 * k, cy), dimc(INK), a * k, 2)
        text(img, '(1 + r)', 670, cy + 78, 84, 'ebg_i', dimc(INK), a * k)
        text(img, 't', 800, cy + 38, 52, 'ebg_i', dimc(INK), a * k)
        text(img, '未来现金流', 690, cy - 170, 30, 'sans_med', GOLD, a * k * (0.6 + 0.4 * hi))
        text(img, '折现率', 690, cy + 170, 30, 'sans', INK3 * 1.3, a * k * (1 - 0.5 * hi))
        if hi > 0:
            for j in range(9):
                ang = j / 9 * 6.28 + t * 0.4
                glow(img, (690 + 120 * math.cos(ang), cy - 72 + 50 * math.sin(ang)), 3, GOLD_HI, a * hi * 0.6)
        ka = env(t, wt('I2', '出自') - 0.2, VOD['I2']['t1'] + 0.5, 0.5, 0.5)
        if ka > 0:
            line(img, (W / 2 - 200, 1170), (W / 2 + 200, 1170), SUB_GOLD, a * ka * 0.5, 1)
            text(img, 'John Burr Williams', W / 2, 1230, 44, 'ebg_i', INK, a * ka)
            text(img, 'The Theory of Investment Value · 1938', W / 2, 1290, 30, 'corm_med', INK2, a * ka, track=0.06)
            text(img, '《投资价值理论》', W / 2, 1350, 30, 'sans', INK2, a * ka)
    # 债券 vs 股票
    a0, b0 = ins_span('I4', 'I6')
    a = env(t, a0, b0, 0.5, 0.5)
    if a > 0:
        kb = eo((t - wt('I4', '债券')) / 0.8); ks = eo((t - wt('I4', '股票')) / 0.8)
        kf = eio((t - VOD['I6']['t0']) / 1.0)
        for row, (lab, y, kk) in enumerate([('债券', 760, kb), ('股票', 1060, ks)]):
            text(img, lab, 110, y - 60, 40, 'serif_bold', INK, a * kk, 'l')
            line(img, (110, y + 70), (980, y + 70), INK3, a * kk, 1)
            for i in range(10):
                x = 250 + i * 72
                if row == 0:
                    h = 60 if i < 9 else 190
                    rect(img, x - 18, y + 70 - h * eo(kk * 1.5 - i * 0.05), x + 18, y + 70, GOLD, a * kk * 0.85)
                else:
                    hh = 40 + 50 * (0.5 + 0.5 * math.sin(i * 1.9 + 0.7)) + kf * 30 * math.sin(t * 2.3 + i * 1.3)
                    rrect(img, x - 18, y + 70 - hh * eo(kk * 1.5 - i * 0.05), x + 18, y + 70, 3, INK2, a * kk * 0.8, 1)
                    text(img, '?', x, y + 70 - hh - 26, 28, 'ebg', INK3 * 1.4, a * kk * eo(kk * 1.5 - i * 0.05))
        text(img, '票息、到期日 · 写在合同上', 250, 870, 28, 'sans', GOLD, a * kb, 'l')
        text(img, '“票息” · 要投资者自己估计', 250, 1170, 28, 'sans', INK2, a * ks, 'l')
        qa_ = a * eo((t - wt('I4', '股票') - 0.4) / 0.8) * (1 - kf)
        if qa_ > 0:
            quote(img, ['“…in the case of equities, the investment analyst', 'must himself estimate the future “coupons.”'], W / 2, 1290, 34, qa_)
            text(img, '—— 伯克希尔 1992 年致股东信', W / 2, 1400, 26, 'sans', INK3 * 1.3, qa_)
        if kf > 0:
            text(img, '未来估错了', W / 2, 1290, 44, 'serif_bold', INK2, a * kf)
            text(img, '折现率再精确，也只是精确地犯错', W / 2, 1370, 46, 'serif_bold', a=a * eo((t - wt('I6', '也只是')) / 0.7), gold=True)
    # 喜诗糖果
    a0, b0 = ins_span('I7', 'I9')
    a = env(t, a0, b0, 0.5, 0.5)
    if a > 0:
        k0 = eo((t - VOD['I7']['t0']) / 0.7)
        text(img, '看得清', W / 2, 620, 40, 'serif_bold', GOLD, a * k0, track=0.3)
        k1 = eo((t - wt('I7', '1972')) / 0.8)
        text(img, '喜诗糖果', W / 2, 730, 80, 'serif_black', INK, a * k1, track=0.06)
        text(img, "See's Candies · 1972 年以 2500 万美元收购", W / 2, 815, 30, 'sans', SUB_GOLD, a * k1, track=0.02)
        k2 = eo((t - VOD['I9']['t0']) / 0.8)
        for i, (lab, v0, v1, note) in enumerate([('销量（磅/年）', '1600万', '3100万', '年增约 2%'), ('税前利润', '<500万', '8200万', '1972 → 2007')]):
            y = 930 + i * 110
            text(img, lab, 110, y, 30, 'sans', INK2, a * k2, 'l')
            text(img, v0, 470, y, 40, 'inter', INK2, a * k2, 'm')
            text(img, '→', 590, y, 36, 'inter', INK3 * 1.4, a * k2, 'm')
            text(img, v1, 720, y, 46, 'inter_semi', GOLD_HI, a * k2, 'm')
            text(img, note, 975, y, 24, 'sans', INK3 * 1.3, a * k2, 'r')
        k3 = eo((t - wt('I9', '累计')) / 1.4)
        yb = 1430
        hA = 250 * k3; hB = max(2, 250 * 32 / 1350) * eo((t - wt('I9', '追加')) / 0.8)
        rect(img, 260, yb - hA, 420, yb, GOLD, a * 0.9)
        rect(img, 660, yb - hB, 820, yb, INK2, a * 0.9)
        line(img, (200, yb), (880, yb), INK3, a * k3, 1)
        text(img, '13.5 亿美元', 340, yb - hA - 34, 40, 'inter_semi', GOLD_HI, a * k3)
        text(img, '累计税前利润', 340, yb + 34, 26, 'sans', INK2, a * k3)
        kB = eo((t - wt('I9', '追加')) / 0.8)
        text(img, '3200 万美元', 740, yb - hB - 34, 36, 'inter_semi', INK, a * kB)
        text(img, '追加投入的资本', 740, yb + 34, 26, 'sans', INK2, a * kB)
        text(img, '数据：伯克希尔 2007 年致股东信（收购经由蓝筹印花公司完成）', W / 2, 1520, 20, 'sans', INK3 * 1.2, a * k2)
    # 美国航空
    a0, b0 = ins_span('I11', 'I13')
    a = env(t, a0, b0, 0.5, 0.5)
    if a > 0:
        k0 = eo((t - VOD['I11']['t0']) / 0.7)
        text(img, '看不清', W / 2, 620, 40, 'serif_bold', INK2, a * k0, track=0.3)
        k1 = eo((t - wt('I11', '1989')) / 0.8)
        text(img, '美国航空优先股', W / 2, 730, 72, 'serif_black', INK, a * k1, track=0.04)
        text(img, 'USAir preferred stock · 1989 年买入', W / 2, 810, 30, 'sans', SUB_GOLD, a * k1)
        k2 = eo((t - wt('I12', '停付')) / 0.6)
        k3 = eio((t - wt('I12', '减记')) / 1.4)
        yb = 1240; hmax = 300
        h = hmax * (1 - 0.75 * k3) * eo((t - wt('I11', '3.58')) / 0.9)
        rrect(img, 390, yb - hmax * eo((t - wt('I11', '3.58')) / 0.9), 690, yb, 4, INK3, a * 0.8, 1)
        rect(img, 390, yb - h, 690, yb, lerp(GOLD, BRICK, k3), a * 0.9)
        text(img, '3.58 亿美元', 540, yb - hmax - 40, 40, 'inter_semi', INK, a * k1 * (1 - 0.6 * k3))
        if k3 > 0.05:
            text(img, '8950 万美元', 820, yb - h, 36, 'inter_semi', BRICK * 1.2, a * k3, 'l')
            text(img, '1994 年底减记', 820, yb - h + 46, 24, 'sans', INK2, a * k3, 'l')
        text(img, '1994.9  停付股息', 110, 950, 28, 'sans_med', BRICK * 1.15, a * k2, 'l')
        k4 = eo((t - wt('I12', '每一')) / 0.7)
        text(img, '$1  →  25¢', W / 2, 1330, 60, 'inter_semi', INK, a * k4)
        k5 = eo((t - wt('I13', '草率')) / 0.8)
        if k5 > 0:
            text(img, '“a case of sloppy analysis”', W / 2, 1420, 44, 'ebg_i', GOLD_HI, a * k5)
            text(img, '“草率的分析”—— 伯克希尔 1994 年致股东信', W / 2, 1480, 26, 'sans', INK2, a * k5)
        text(img, '注：1998 年航空股短暂回暖，伯克希尔获利卖出；巴菲特在 2007 年信中称之为运气', W / 2, 1530, 20, 'sans', INK3 * 1.2, a * k1)
    # 代价：错过
    a0, b0 = ins_span('I14', 'I15')
    a = env(t, a0, b0, 0.5, 0.5)
    if a > 0:
        k1 = eo((t - wt('I14', '芒格')) / 0.8)
        kf = eio((t - VOD['I15']['t0']) / 0.8)
        text(img, '2017 · 伯克希尔股东大会', W / 2, 700, 28, 'sans_med', SUB_GOLD, a * k1 * (1 - kf), track=0.12)
        quote(img, ['“…in retrospect, what was our worst', 'mistake in the tech field, I think we were', 'smart enough to figure out Google.”'], W / 2, 800, 38, a * k1 * (1 - kf))
        text(img, '—— 查理·芒格', W / 2, 960, 28, 'sans', INK2, a * k1 * (1 - kf))
        text(img, '代价：错过', W / 2, 1100, 56, 'serif_black', a=a * eo((t - VOD['I14']['t0']) / 0.7) * (1 - kf), gold=True)
        if kf > 0:
            for i, (l1, l2, col) in enumerate([('错过', '少赚', INK2), ('看错', '永久亏损', BRICK * 1.15)]):
                k = eo((t - wt('I15', l1) + 0.1) / 0.6)
                cx = 290 + i * 500
                rrect(img, cx - 200, 820, cx + 200, 1180, 10, col, a * k * kf * 0.7, 1)
                text(img, l1, cx, 930, 64, 'serif_black', INK, a * k * kf)
                text(img, '＝', cx, 1010, 40, 'inter', INK3 * 1.4, a * k * kf)
                text(img, l2, cx, 1090, 52, 'serif_bold', col, a * k * kf)
    # 今天
    a0, b0 = ins_span('I16', 'I17', post=0.9)
    a = env(t, a0, b0, 0.5, 0.6)
    if a > 0:
        k1 = eo((t - VOD['I16']['t0']) / 0.8)
        kf = eio((t - VOD['I17']['t0'] + 0.2) / 0.8)
        r = np.random.default_rng(4)
        lit = set(r.choice(120, 7, replace=False).tolist())
        k2 = eio((t - wt('I16', '越来越少')) / 1.2)
        for i in range(120):
            x = 150 + (i % 12) * 71; y = 700 + (i // 12) * 56
            on = i in lit
            c = lerp(INK3, GOLD_HI, k2) if on else INK3
            circle(img, (x, y), 6 if on else 5, c, a * k1 * (1 - kf) * (1.0 if on else 0.75 - 0.4 * k2), fill=True)
            if on and k2 > 0: glow(img, (x, y), 10, GOLD, a * k2 * (1 - kf) * 0.6)
        text(img, '能看清十年现金流的企业', W / 2, 1330, 40, 'serif_bold', INK, a * k1 * (1 - kf))
        text(img, '越来越少', W / 2, 1400, 40, 'serif_bold', GOLD_HI, a * k2 * (1 - kf))
        if kf > 0:
            text(img, '财务报表只给你指引；', W / 2, 900, 60, 'serif_bold', INK2, a * kf)
            text(img, '答案，在你对生意的理解里。', W / 2, 1010, 60, 'serif_black', a=a * eo((t - wt('I17', '答案')) / 0.8), gold=True, glow=0.15)
    narr_sub(img, t, INS['subs'], hide=('I17',))


# ---------------------------------------------------------------- 一句话总结 + 品牌片尾
def summary_masks():
    out = []
    for s, y in (('先问看不看得清，', 880), ('再问便不便宜。', 1010)):
        m, w, base, pad = text_mask(s, 'serif_black', 92, 0.04)
        out.append((m, int(W / 2 - w / 2 - pad), int(y + 92 * 0.36 - base)))
    return out


SUM_MASKS = summary_masks()


def _particles():
    r = np.random.default_rng(13)
    pts = []
    for m, x0_, y0_ in SUM_MASKS:
        ys, xs = np.nonzero(m > 0.5)
        pts.append(np.c_[xs + x0_, ys + y0_])
    src = np.concatenate(pts).astype(np.float64)
    N = 2600
    src = src[r.choice(len(src), N, replace=len(src) < N)] + r.normal(0, 0.6, (N, 2))
    ys, xs = np.nonzero(LOGO_A > 0.35)
    pick = r.choice(len(xs), N, replace=len(xs) < N, p=LOGO_A[ys, xs] / LOGO_A[ys, xs].sum())
    dst = np.c_[xs[pick] - LOGO_PX / 2 + W / 2, ys[pick] - LOGO_PX / 2 + LOGO_CY].astype(np.float64) + r.random((N, 2)) - 0.5
    col = LOGO_RGB[ys[pick], xs[pick]].astype(np.float32)
    delay = r.random(N) * 0.6
    swirl = r.normal(0, 1, (N, 2)) * 90
    return src, dst, col, delay, swirl


LOGO_CY = 760
PSRC, PDST, PCOL, PDEL, PSW = _particles()


def s_summary(img, t):
    tp = END['t_particles']
    a = env(t, T_SUM - 0.05, tp + 0.4, 0.05, 0.4)
    if a > 0:
        k = t - T_SUM
        glow(img, (W / 2, 950), 300, GOLD * 0.22, math.exp(-max(k, 0) / 1.4) * a)
        dust(img, t, a * 0.8)
        text(img, '一句话总结', W / 2, 740, 28, 'sans_med', SUB_GOLD, a * eo(k / 0.6), track=0.4)
        for sg in (-1, 1):
            line(img, (W / 2 + sg * 110, 740), (W / 2 + sg * (110 + 90 * eo(k / 1.0)), 740), SUB_GOLD, a * 0.6, 1)
        w1 = eo((t - VOD['M']['t0'] + 0.1) / 1.0); w2 = eo((t - wt('M', '再问') + 0.05) / 1.0)
        sh = cl((t - VOD['M']['t1'] - 0.2) / 1.4) if VOD['M']['t1'] + 0.2 < t < VOD['M']['t1'] + 1.6 else None
        text(img, '先问看不看得清，', W / 2, 880, 92, 'serif_black', a=a, gold=True, wipe=w1, shine=sh, track=0.04, glow=0.18)
        text(img, '再问便不便宜。', W / 2, 1010, 92, 'serif_black', a=a, gold=True, wipe=w2, shine=sh, track=0.04, glow=0.18)
        text(img, '伯克希尔股东大会投资智慧录 · 第一集', W / 2, 1150, 26, 'sans', INK2, a * eo((k - 1.2) / 0.8), track=0.1)


def s_end(img, t):
    tp, tl_, tb = END['t_particles'], END['t_logo'], END['t_brand']
    if t < tp: return
    fade = 1 - eio((t - END['t_fade0']) / (END['t_fade1'] - END['t_fade0']))
    # 微光与粒子汇聚：总结文字散成金色粒子，沿 logo 透明通道汇聚
    u = np.clip((t - tp - PDEL) / 2.9, 0, 1)
    e = u * u * (3 - 2 * u)
    P = PSRC + (PDST - PSRC) * e[:, None] + PSW * np.sin(np.pi * e)[:, None] * (1 - e[:, None])
    gold_c = np.array([1.0, 0.82, 0.5], np.float32)
    colmix = (1 - e)[:, None] * gold_c + e[:, None] * PCOL
    pa = (0.75 - 0.75 * eio((t - tl_ - 0.4) / 1.2)) * fade
    if pa > 0.003:
        buf = np.zeros((H, W, 3), np.float32)
        xi = np.clip(P[:, 0].astype(int), 0, W - 1); yi = np.clip(P[:, 1].astype(int), 0, H - 1)
        np.add.at(buf, (yi, xi), colmix * pa)
        y0_, y1_ = 300, 1250
        sub = buf[y0_:y1_]
        sub = cv2.GaussianBlur(sub, (0, 0), 1.1) * 2.2 + cv2.GaussianBlur(sub, (0, 0), 6) * 6
        img[y0_:y1_] += sub
    # logo 背后的淡蓝光晕（品牌规范）+ 重拍时的柔和闪光
    gk = eo((t - tl_) / 1.2) * fade
    glow(img, (W / 2, LOGO_CY), 120, BLUE * 0.35, gk * 0.6)
    if t >= tb: glow(img, (W / 2, LOGO_CY), 160, GOLD * 0.3, math.exp(-(t - tb) / 0.5) * fade)
    # 官方 logo 完整清晰呈现
    la = eo((t - tl_) / 1.0) * fade
    if la > 0:
        over(img, LOGO_RGB.astype(np.float32), LOGO_A.astype(np.float32) * la, int(W / 2 - LOGO_PX / 2), int(LOGO_CY - LOGO_PX / 2))
    # 金色「巴芒价值」+「BUFFETT · MUNGER」随重拍浮现（官方预渲染字样），随后流光扫过
    if t >= tb - 0.05:
        w1 = eo((t - tb + 0.05) / 0.9)
        rgb, al = END_TITLE
        sh = cl((t - END['t_shine']) / 1.4) if END['t_shine'] < t < END['t_shine'] + 1.4 else None
        rgb2 = rgb
        if sh is not None:
            hh, ww = al.shape
            xs = np.arange(ww)[None, :] + np.arange(hh)[:, None] * 0.6
            pos = -60 + (0.5 - 0.5 * math.cos(sh * math.pi)) * (ww + 120)
            rgb2 = np.clip(rgb + np.exp(-((xs - pos) / (0.06 * ww + 10)) ** 2)[..., None] * 0.6, 0, 1.25)
        soft = 0.3 * al.shape[1] + 30
        g = np.clip((w1 * (al.shape[1] + soft) - np.arange(al.shape[1])) / soft, 0, 1).astype(np.float32)
        ty = 1010
        over(img, rgb2, al * g[None, :] * fade, int(W / 2 - al.shape[1] / 2), int(ty - al.shape[0] / 2))
        hw = al.shape[1] / 2 + 40
        L = 150 * eo((t - tb - 0.3) / 1.0)
        for sg in (-1, 1):
            line(img, (W / 2 + sg * hw, ty), (W / 2 + sg * (hw + L), ty), SUB_GOLD * 0.8, fade * 0.8, 1)
        w2 = eo((t - tb - 0.35) / 0.9)
        rgb, al = END_SUB
        g = np.clip((w2 * (al.shape[1] + soft) - np.arange(al.shape[1])) / soft, 0, 1).astype(np.float32)
        over(img, rgb, al * g[None, :] * fade, int(W / 2 - al.shape[1] / 2), int(ty + 70 + 26 - al.shape[0] / 2))
        text(img, '伯克希尔股东大会投资智慧录', W / 2, 1220, 28, 'sans', INK2, fade * eo((t - tb - 1.2) / 0.9), track=0.2, shadow=0.4)


# ---------------------------------------------------------------- 合成一帧
def frame(t):
    img = BG.copy()
    s_cold(img, t)
    s_title(img, t)
    s_intro(img, t)
    s_ctx(img, t)
    s_qa(img, t)
    s_insight(img, t)
    s_summary(img, t)
    s_end(img, t)
    # 片头口播期间的章节标签
    ia = env(t, VOD['S2']['t0'] - 0.5, VOD['S11']['t1'] + 0.8, 0.6, 0.6)
    chapter_tag(img, t, '系列开篇', ia)
    img *= VIG
    img += GRAIN[int(t * FPS) % len(GRAIN)]
    # 右上角品牌角标：全程保留，片尾与画面一起淡出；冷开场黑场时同样可见
    fade_all = 1 - eio((t - END['t_fade0']) / (END['t_fade1'] - END['t_fade0']))
    HUD.draw(img, t, alpha=float(fade_all * env(t, 0.0, 1e9, 0.8, 0.01)))
    if t < 0.3: img *= t / 0.3
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    cmd = sys.argv[1]
    if cmd == 'nframes':
        print(TL['nframes']); return
    if cmd == 'stills':
        out = sys.argv[2]; os.makedirs(out, exist_ok=True)
        for ts in sys.argv[3:-1]:
            tt = float(ts)
            Image.fromarray(frame(tt)).save(os.path.join(out, f'f_{tt:07.2f}.png'))
        return
    if cmd == 'chunk':
        a, b, path = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                              '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16',
                              '-pix_fmt', 'yuv420p', '-tune', 'film', path], stdin=subprocess.PIPE)
        for i in range(a, b):
            p.stdin.write(frame(i / FPS).tobytes())
            if (i - a) % 300 == 0: print(f'[{a}-{b}] {i - a}/{b - a}', flush=True)
        p.stdin.close(); p.wait()


if __name__ == '__main__':
    main()
