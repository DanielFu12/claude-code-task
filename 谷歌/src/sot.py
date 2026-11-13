"""巴菲特原声段落（SOT）的画面：整屏转入“采访现场”。

· 画面：专访原片原速播放，与原声同一入点（口型同步）；放大到整幅宽、近 4:5 的人像取景，上下羽化融入暗场，缓慢推近；
· 左上“原声”标签 + 由原声实际响度驱动的声纹条；首次 3 秒出人名条；
· 下方：英文原话（逐句）+ 中文翻译，按原声里的停顿逐句切换；出处行写明节目、日期与片中时间；
· 进出：0.35s 推拉 + 金色光扫；普通旁白字幕在原声段落里不显示（common.subtitles 跳过 kind=sot）。
"""
import os, math, json
import numpy as np, cv2, soundfile as sf
from common import *          # noqa
import media as M
import fx
from script import SOTS, SOT_SRC

SOTSEG = [s for s in TL['segs'] if s.get('kind') == 'sot']
FADE = 0.38
_env = {}


def _envelope(sid):
    """原声每帧响度（0..1），驱动声纹条"""
    if sid not in _env:
        y, sr = sf.read(os.path.join(WORK, 'sot', sid + '.wav'), dtype='float32')
        hop = sr // FPS
        r = np.sqrt(np.convolve(y ** 2, np.ones(hop) / hop, 'same'))[::hop]
        _env[sid] = np.clip(r / (np.percentile(r, 97) + 1e-9), 0, 1)
    return _env[sid]


_feather = {}
def _feather_mask(w, h):
    if (w, h) not in _feather:
        y = np.linspace(0, 1, h, dtype=np.float32)[:, None]; x = np.linspace(0, 1, w, dtype=np.float32)[None, :]
        my = np.clip(y / 0.10, 0, 1) ** 1.2 * np.clip((1 - y) / 0.30, 0, 1) ** 1.5
        mx = np.clip(x / 0.04, 0, 1) * np.clip((1 - x) / 0.04, 0, 1)
        _feather[(w, h)] = (my * mx).astype(np.float32)
    return _feather[(w, h)]


ZOOM = {'decider': 1.22}            # 双人景：巴菲特在画面右侧，收紧取景
FOCUS = {'dontlike': (0.53, 0.42), 'decider': (0.9, 0.5), 'attacks': (0.55, 0.42), 'rank': (0.55, 0.42),
         'trick': (0.53, 0.42), 'hundreds': (0.53, 0.42)}


def footage(cv, sid, t, c0, ln, al):
    """c0：片段第 0 秒对应的时间线时刻（= 原声入点）"""
    name = 'sot_' + sid
    fr = M.vframe(name, max(t - c0, 0.0))
    if fr is None: return
    src = fr[..., ::-1].astype(np.float32) / 255 if fr.dtype == np.uint8 else fr
    w, h = W, 980
    p = cl((t - c0) / max(ln, 0.1))
    push = 1.0 + 0.055 * eio(p)
    intro = 1 + 0.06 * (1 - eo((t - c0 + FADE) / 0.6))           # 进场时从稍大处落定
    fx_, fy_ = FOCUS.get(sid, (0.53, 0.42))
    img = M._crop(src, w, h, push * intro * ZOOM.get(sid, 1.0), fx_, fy_)
    img = M.grade(img, 0.18, 0.92)
    img = np.clip((img - 0.5) * 1.08 + 0.5 - 0.015, 0, 1)        # 略加反差
    y0 = 250
    cv.over(img, _feather_mask(w, h) * al, 0, y0)
    # 取景框角标（细金线）
    for (x, y, dx, dy) in ((60, 300, 1, 1), (W - 60, 300, -1, 1), (60, 1010, 1, -1), (W - 60, 1010, -1, -1)):
        cv.line((x, y), (x + 46 * dx, y), GOLD, al * 0.55, 2); cv.line((x, y), (x, y + 46 * dy), GOLD, al * 0.55, 2)


def badge(cv, sid, t, c0, al):
    e = _envelope(sid); k = int((t - c0) * FPS)
    x, y = 70, 345
    cv.rrect(x, y - 24, x + 196, y + 24, 24, (0.05, 0.04, 0.035), al * 0.75)
    cv.rrect(x, y - 24, x + 196, y + 24, 24, GOLD, al * 0.6, fill=False, th=2)
    blink = 0.6 + 0.4 * (math.sin(t * 5.5) > -0.2)
    cv.glow_dot((x + 28, y), 8, RED, al * blink)
    cv.text('原声 · SOT', x + 112, y, 24, 'sans_med', col=CREAM, a=al)
    # 声纹条
    for j in range(22):
        kk = k - (21 - j) * 2
        v = e[kk] if 0 <= kk < len(e) else 0.0
        hh = 4 + 34 * v
        xx = x + 220 + j * 11
        cv.rect(xx, y - hh / 2, xx + 6, y + hh / 2, GOLD_L if j > 16 else GOLD * 0.8, al * (0.35 + 0.65 * j / 21))


def name_super(cv, t, c0, al):
    p = t - c0
    k = env(p, 0.25, 3.6, 0.5, 0.5)
    if k <= 0.004: return
    x, y = 70, 1150
    L = 6 + 420 * eo((p - 0.25) / 0.6)
    cv.rect(x, y - 52, x + 6, y + 40, GOLD, al * k, glow=0.3)
    cv.text('沃伦·巴菲特', x + 30, y - 18, 48, 'serif_black', gold=True, a=al * k, anchor='l', reveal=eo((p - 0.3) / 0.6), shadow=0.8)
    cv.text('WARREN BUFFETT · 伯克希尔·哈撒韦董事长', x + 32, y + 30, 22, 'sans_med', col=CREAM, a=al * k * 0.9, anchor='l',
            track=0.04, shadow=0.8)
    cv.line((x + 30, y + 58), (x + 30 + L, y + 58), GOLD_D, al * k * 0.8, 2)


def captions(cv, seg, t, c0, al):
    """英文原话 + 中文翻译：逐句，按原声停顿切换（不叠影）"""
    sid = seg['id'][4:]; ph = SOTS[sid]['ph']; tm = seg['ph']
    vs = seg['start']
    for j, ((en, cn), (a0, a1)) in enumerate(zip(ph, tm)):
        last = j == len(ph) - 1
        s0, s1 = vs + a0 - (0.25 if j == 0 else 0.05), vs + a1 + (0.6 if last else -0.05)
        k = env(t, s0, s1, 0.18, 0.18 if not last else 0.4)
        if k <= 0.004: continue
        rise = 14 * (1 - eo((t - s0) / 0.35))
        en_l = wrap('“' + en + '”' if (j == 0 and len(ph) == 1) else en, 'corm_med', 44, 960)
        cn_l = wrap_nice(cn, 'serif_semi', 54, 960)
        n_en, n_cn = len(en_l), len(cn_l)
        top = 1300 + rise
        hh = n_en * 50 + n_cn * 74 + 60
        sub_backing(cv, 40, top - 40, W - 40, top + hh - 10, k * al, target=0.42)
        y = top
        for l in en_l:
            cv.text(l, W / 2, y, 44, 'corm_med', col=(0.93, 0.91, 0.86), a=k * al, shadow=0.9); y += 50
        y += 18
        for l in cn_l:
            cv.text(l, W / 2, y + 8, 54, 'serif_semi', col=GOLD_L, a=k * al, shadow=0.9, glow=0.05); y += 74


def sot_layer(cv, t):
    for seg in SOTSEG:
        c0 = seg['start'] - seg['lead']; ln = seg['len']
        if not (c0 - FADE - 0.05 <= t <= c0 + ln + FADE + 0.05): continue
        al = env(t, c0 - FADE, c0 + ln + FADE * 0.6, FADE, FADE)
        if al <= 0.004: continue
        sid = seg['id'][4:]
        # 暗场：压掉原画面（含光斑与线条层）
        d = 0.94 * al
        cv.dim(1 - d); cv.glow *= (1 - d); cv.U = (cv.U * (1 - d)).astype(np.uint8)
        footage(cv, sid, t, c0, ln, al)
        if t - c0 < 0.8: fx.sweep(cv, t, c0 - 0.1, 0.8, a=0.5 * al)
        badge(cv, sid, t, c0, al)
        if sid in FIRST_SUPER: name_super(cv, t, c0, al)
        captions(cv, seg, t, c0, al)
        src = f'原声 · {SOT_SRC}（专访 {SOTS[sid]["ts"]}）'
        source(cv, src, al, y=1640)


FIRST_SUPER = {'dontlike', 'decider', 'attacks', 'rank'}     # 每章第一段原声出人名条
