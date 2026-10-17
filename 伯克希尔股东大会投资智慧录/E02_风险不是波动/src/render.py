"""《伯克希尔股东大会投资智慧录》第二集 · 风险不是波动 —— 逐帧渲染（1080×1920，30fps）。

三维玻璃场景用 glass.py（GLSL 光线步进，Mesa llvmpipe），需在 xvfb-run 下运行；其余为 2D 合成（gfx / fx）。
用法：
    python3 render.py nframes WORK
    python3 render.py chunk A B OUT.mp4 WORK
    python3 render.py stills OUT_DIR WORK t1 t2 …
所有画面都是时间 t 的纯函数；时间点全部来自 WORK/timeline.json。
"""
import json, math, os, subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'brand'))
from gfx import *                      # noqa: F401,F403
import gfx
import fx
import post as PP
import scenes_gl as SG
import brand as B
from script import PIC_BOX, BROLL

WORK = sys.argv[-1] if len(sys.argv) > 2 else os.path.join(HERE, '..', 'work')
TL = json.load(open(os.path.join(WORK, 'timeline.json')))
FPS = TL['fps']
ENV = np.load(os.path.join(WORK, 'orig_env.npy'))
SS = float(os.environ.get('GLASS_SS', '1.25'))        # 三维场景超采样倍数

# ---------------------------------------------------------------- 品牌（只用 brand/ 里的官方资产）
HUD = B.Hud(scale=1.0, frame_w=W)
LOGO_PX = 240
LOGO_RGB, LOGO_A = B.load_logo(LOGO_PX)
_lay = json.load(open(B.LAYOUT))
_lock = np.asarray(Image.open(B.LOCKUP_4X).convert('RGBA')).astype(np.float32) / 255
_tb = _lay['text_box']
_txt = _lock[_tb[1]:_tb[3], _tb[0]:_tb[2]]
_rows = np.where(_txt[..., 3].max(1) > 0.02)[0]
_gap = np.where(np.diff(_rows) > 3)[0]
_split = int(_rows[_gap[0]] + 2) if len(_gap) else int(_txt.shape[0] * 0.75)
END_SCALE = 0.78


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
ICE = np.array([0.62, 0.80, 1.0], np.float32)       # 冷色辅助（冰蓝）
SILVER = np.array([0.80, 0.84, 0.90], np.float32)
RED = np.array([0.95, 0.40, 0.30], np.float32)       # 只用于亏损 / 风险

QA_CLIP = Clip(os.path.join(WORK, 'qa_c.mp4'))
CLIPS = {k: Clip(os.path.join(WORK, f'broll_{k}_c.mp4')) for k in BROLL}

# ---------------------------------------------------------------- 时间点
INTRO, INS, SUM, END, QA = TL['intro'], TL['insight'], TL['summary'], TL['end'], TL['qa']
COLD = TL['cold']
T_TITLE = TL['t_title']
VOD = {v['id']: v for part in (INTRO, INS, SUM) for v in part['vo']}
WORDS = {}
for part in (INTRO, INS, SUM):
    for w in part['words']:
        WORDS.setdefault(w['id'], []).append(w)
QSC = {s['scene']: s for s in QA['scenes']}
QSUB = {s['id']: s for s in QA['subs']}
T_CTX = TL['ctx']['t0']; T_Q = QA['t0']; T_QE = QA['t1']; T_INS = INS['t_card']; T_SUM = SUM['t0']
NV = TL['nerves']
HITS = [tuple(h) for h in TL['hits']]
BARS = np.array(TL['beats'][::4])


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


def V(sid): return VOD[sid]


def ofr(t):
    i = min(max(int(t * FPS), 0), len(ENV) - 1)
    return ENV[i]


def qa_src(t):
    """片内时刻 → 原声片段里的源时间（秒，相对 CLIP_IN）；不在节选内返回 None"""
    for sg in QA['segs']:
        if sg['t0'] - 0.6 <= t <= sg['t1'] + 0.6:
            return min(max(sg['src_in'] + t - sg['t0'], sg['src_in']), sg['src_out'])
    return None


# ---------------------------------------------------------------- 三维渲染器（懒加载）
_R = None


def R():
    global _R
    if _R is None:
        from glass import Renderer
        _R = Renderer(W, H)
    return _R


def rgba_tex(rgb):
    """float RGB → uint8 RGBA（不透明）"""
    a = np.clip(rgb * 255, 0, 255).astype(np.uint8)
    return np.dstack([a, np.full(a.shape[:2], 255, np.uint8)])


def text_tex(s, fontname, size, pad=30):
    f = ImageFont.truetype(os.path.join(gfx.FONT_DIR, gfx.FONTS[fontname] + '.ttf'), size)
    w = int(f.getlength(s)) + pad * 2
    im = Image.new('RGBA', (w, int(size * 1.35) + pad), (255, 255, 255, 0))
    ImageDraw.Draw(im).text((pad, pad // 2), s, font=f, fill=(255, 255, 255, 255))
    return np.array(im)


TEX = {}


def tex_once(key, maker):
    if key not in TEX:
        TEX[key] = maker()
    return R().texture(key, TEX[key])


def cam_orbit(tgt, r, yaw, pitch):
    return (tgt[0] + r * math.sin(yaw) * math.cos(pitch), tgt[1] + r * math.sin(pitch), tgt[2] + r * math.cos(yaw) * math.cos(pitch))


def sea_params(**k):
    d = dict(amp=0.25, spd=1.0, ox=0.0, oz=0.0, R=0.55, gold=1.0, core=0.32, crack=0.0, shat=0.0, chain=0.0, pull=0.0,
             sea=1.0, arr=0.0, depth=0.9, cool=0.0, hov=0.25, rx=0.0, rz=0.0, rt=0.0, pulse=0.0)
    d.update(k)
    return [d[n] for n in ('amp', 'spd', 'ox', 'oz', 'R', 'gold', 'core', 'crack', 'shat', 'chain', 'pull', 'sea', 'arr', 'depth',
                           'cool', 'hov', 'rx', 'rz', 'rt', 'pulse')]


SEA_U = dict(uFloorY=-1.0, uGrid=0.45, uFov=0.8, uAbsorb=(1.4, 0.8, 0.45), uDisp=0.008, uSpec=0.15)


# ---------------------------------------------------------------- 三维场景调度：返回 (场景名, 源码, 相机, 目标, 参数, 统一变量, 贴图, 后期)
def gl_scene(t):
    S1, S2, S3 = V('S1'), V('S2'), V('S3')
    # ---- 冷开场：历史影像平面 + 缓缓滑过的玻璃棱柱
    if t < T_TITLE - 0.55:
        src = COLD['src_in'] + (t - COLD['t0'])
        fr = QA_CLIP.get(min(max(src, 0.0), 309.0))
        fr = grade(fr, sat=0.55, gain=0.95)
        tex = R().texture(('cold', int(t * FPS)), rgba_tex(fr))
        u = (t - 0.0) / (T_TITLE - 0.55)
        cam = (0.15 - 0.3 * u, 0.05, 4.6 - 0.5 * eio(u)); tgt = (0.0, 0.0, 0.0)
        bright = eio((t - 0.15) / 0.9) * (1 - 0.6 * eio((t - (T_TITLE - 1.6)) / 1.0))
        uni = dict(uT0o=(0.42, 0.05, 0), uT0u=(1.1, 0, 0), uT0v=(0, 0.446, 0), uT0c=tuple(np.array([1.15, 1.08, 1.0]) * bright), uT0a=1.0,
                   uFloorY=-1.6, uGrid=0.0, uFov=0.62, uSweep=-1.4 + 2.2 * u, uSweepI=0.9, uEnvI=0.8 * bright + 0.05, uDisp=0.006, uSpec=0.3)
        return ('prism', SG.PRISM, cam, tgt, [-2.6 + 5.4 * u, 0.6 * u, 2.4 - 4.6 * u], uni, (tex, None),
                dict(exposure=1.15, bloom_k=0.18, streak=0.08))
    # ---- 片名：七块玻璃在重拍上合拢成铭牌，金色片名嵌在玻璃里
    if t < S1['t0'] - 0.35:
        k = cl((t - (T_TITLE - 1.25)) / 1.25)
        close = k ** 2.4 if t < T_TITLE else 1.0
        after = max(0.0, t - T_TITLE)
        tex = tex_once('title', title_tex)
        tw = TEX['title'].shape[1] / TEX['title'].shape[0]
        hh = 0.40
        yaw = -0.30 + 0.24 * eio((t - (T_TITLE - 1.25)) / 3.5); pitch = 0.06
        cam = cam_orbit((0, 0, 0), 4.2 - 0.3 * eio(after / 3.0), yaw, pitch)
        gb = 0.55 + 0.9 * math.exp(-after / 0.9) if t >= T_TITLE else 0.45 + 0.1 * k
        uni = dict(uT0o=(0, 0.0, -0.34), uT0u=(hh * tw, 0, 0), uT0v=(0, hh, 0), uT0c=tuple(np.array([1.25, 0.86, 0.40]) * gb), uT0a=1.0,
                   uFloorY=-0.95, uGrid=0.35, uFov=0.66, uSweep=(-1.6 + 1.9 * eio(after / 1.6)) if t >= T_TITLE else -1.6,
                   uSweepI=0.6 + 1.4 * math.exp(-after / 1.2) if t >= T_TITLE else 0.5, uDisp=0.014)
        return ('plaque', SG.PLAQUE, cam, (0, 0.0, 0), [close, 0.64, 0.52, 0.15, 0.8, 0.0, cl(after / 1.8) if t >= T_TITLE else 0.0], uni,
                (tex, None), dict(exposure=1.2, bloom_k=0.24, streak=0.14))
    # ---- 开场 S1–S2：价格玻璃管（一年跌掉 25%）
    if t < S3['t0'] - 0.3:
        path = [100, 103, 99, 104, 108, 102, 105, 96, 90, 84, 78, 75]
        pts = []
        for i, p in enumerate(path):
            pts += [-0.72 + 1.44 * i / 11, (p - 100) / 100 * 6.5 + 0.45]
        t_drop = wt('S1', '跌掉')
        g0 = S1['t0'] - 0.9
        grow = 0.06 + 0.94 * eio((t - g0) / (t_drop + 0.9 - g0))
        hi = eo((t - t_drop) / 0.8)
        head = grow
        # 相机：跟随光头，S2 时拉远看全貌
        hx = -0.72 + 1.44 * head
        hy = (path[min(int(head * 11), 11)] - 100) / 100 * 6.5 + 0.45
        pull = eio((t - S2['t0'] + 0.4) / 1.6)
        tgt = (lerp(hx * 0.5, 0.0, pull), lerp(hy * 0.45 - 0.25, -0.35, pull), 0.0)
        cam = (tgt[0] - 0.55 + 0.3 * pull, tgt[1] + 0.35, lerp(lerp(2.5, 3.3, eio(grow * 1.6)), 4.6, pull))
        uni = dict(uFloorY=-1.75, uGrid=0.5, uFov=0.75, uSweep=-0.9 + 0.7 * grow, uSweepI=0.8, uDisp=0.012, uEnvI=0.95)
        return ('ribbon', SG.RIBBON, cam, tgt, [grow, head, hi] + pts, uni, (None, None),
                dict(exposure=1.25, bloom_k=0.26, streak=0.12, focus=float(np.linalg.norm(np.subtract(cam, tgt))), aperture=0.25))
    # ---- 开场 S3：1994 年的大会影像，透过玻璃棱柱
    if t < T_CTX:
        ct = (t - S3['t0'] + 0.3) % 15.5
        fr = grade(CLIPS[200].get(ct), sat=0.55, gain=0.95)
        tex = R().texture(('s3', int(t * FPS)), rgba_tex(fr))
        u = cl((t - S3['t0'] + 0.3) / (T_CTX - S3['t0'] + 0.3))
        cam = (-0.25 + 0.4 * u, 0.12, 3.9 - 0.4 * u)
        fade = 1 - eio((t - (T_CTX - 0.5)) / 0.5)
        uni = dict(uT0o=(0, 0.1, 0), uT0u=(0.76, 0, 0), uT0v=(0, 0.308, 0), uT0c=tuple(np.array([1.1, 1.04, 0.96]) * fade), uT0a=1.0,
                   uFloorY=-1.6, uGrid=0.0, uFov=0.66, uSweep=1.2 - 2.0 * u, uSweepI=0.8 * fade, uEnvI=0.8 * fade + 0.02, uDisp=0.006, uSpec=0.3)
        return ('prism', SG.PRISM, cam, (0, 0, 0), [2.6 - 5.2 * u, -0.5 * u, -2.2 + 4.0 * u], uni, (tex, None),
                dict(exposure=1.15, bloom_k=0.18, streak=0.08))
    if t < T_INS - 1.0 or t >= END['t_particles'] + 0.6:
        return None
    # ======== 投资启示 ========
    I = {k: V(k) for k in ('I1', 'I2', 'I3', 'I4', 'I5', 'I6', 'I7', 'I8', 'I9', 'I10', 'I11', 'I12', 'I13')}
    # ---- 启示卡 + I1：两块玻璃碑（波动 β / 损失的可能性）
    if t < I['I2']['t0'] - 0.3:
        rise = eo((t - T_INS) / 1.6)
        u = cl((t - T_INS) / (I['I2']['t0'] - T_INS))
        cam = (-0.45 + 0.9 * eio(u), 0.45, 5.6 - 0.5 * eio(u))
        wav = 0.2 + 0.8 * eo((t - wt('I1', '波动')) / 0.5)
        core = 0.4 + 1.2 * eo((t - wt('I1', '受到伤害')) / 0.6)
        uni = dict(uFloorY=-1.25, uGrid=0.5, uFov=0.7, uSweep=-1.0 + 0.6 * u, uSweepI=0.9, uDisp=0.012)
        return ('mono', SG.MONO, cam, (0, 0.1, 0), [rise, wav, core, 0.0, 0.47], uni, (None, None),
                dict(exposure=1.2 * eio((t - T_INS + 1.0) / 1.0) + 1e-3, bloom_k=0.22, streak=0.1, focus=float(np.linalg.norm(np.subtract(cam, (0, 0.1, 0)))), aperture=0.35))
    # ---- I2：持有期时间管（脉冲上下抖动地走到终点环）
    if t < I['I3']['t0'] - 0.3:
        a0, a1 = I['I2']['t0'] - 0.3, I['I3']['t0'] - 0.3
        u = cl((t - a0) / (a1 - a0))
        growk = eo((t - a0) / 1.0)
        pos = eio(cl((t - wt('I2', '持有期')) / (wt('I2', '购买力') - wt('I2', '持有期') + 0.3)))
        ring = eo((t - wt('I2', '购买力')) / 0.6)
        tgt = (0.0, 0.05, 0.0)
        cam = (lerp(-1.5, 1.3, eio(u)), 0.4, 5.0)
        uni = dict(uFloorY=-1.0, uGrid=0.5, uFov=0.72, uSweep=-0.4 + 0.8 * u, uSweepI=0.8, uDisp=0.012)
        return ('tube', SG.TUBE, cam, tgt, [pos, 1.0 - 0.0 * ring, ring, growk], uni, (None, None),
                dict(exposure=1.2, bloom_k=0.24, streak=0.1, focus=float(np.linalg.norm(np.subtract(cam, tgt))), aperture=0.4))
    # ---- I3–I11 + I13：玻璃海与悬浮玻璃球
    if t < I['I12']['t0'] - 0.3 or (t >= I['I13']['t0'] - 0.3 and t < T_SUM - 0.25):
        return sea_scene(t, I)
    # ---- I12：磨砂玻璃屏（账户回撤），镜头穿过屏幕
    if t < I['I13']['t0'] - 0.3:
        a0, a1 = I['I12']['t0'] - 0.3, I['I13']['t0'] - 0.3
        u = cl((t - a0) / (a1 - a0))
        tex = tex_once('dd', drawdown_tex)
        zc = lerp(0.0, 3.8, eio(cl((t - wt('I12', '先问')) / 1.6)))
        cam = (0.0, 0.25, 3.5)
        gold = 0.5 + 1.0 * eo((t - wt('I12', '这门生意')) / 0.8)
        uni = dict(uT0o=(0, 0.1, zc - 0.09), uT0u=(0.52, 0, 0), uT0v=(0, 0.92, 0), uT0c=(1.0, 1.0, 1.0), uT0a=1.0 if zc < 3.3 else 0.0,
                   uFloorY=-1.0, uGrid=0.4, uFov=0.8, uSweep=-0.3 + 0.6 * u, uSweepI=0.7, uFrost=0.0, uDisp=0.008)
        return ('screen', SG.SCREEN, cam, (0, 0.15, -1.0), [zc, 0.0, 1.0 if zc < 3.3 else 0.0, gold], uni, (tex, None),
                dict(exposure=1.2, bloom_k=0.2, streak=0.08))
    # ---- 一句话总结：透镜组在重拍上合拢
    if t >= T_SUM - 0.25:
        k = cl((t - (T_SUM - 1.1)) / 1.1)
        close = k ** 2.2 if t < T_SUM else 1.0
        after = max(0.0, t - T_SUM)
        beam = 0.2 + 1.6 * math.exp(-after / 1.6) if t >= T_SUM else 0.2
        fade = 1 - eio((t - END['t_particles'] + 0.2) / 0.8)
        cam = cam_orbit((0, -0.95, 0), 6.6 - 0.4 * eio(after / 4), 0.55 - 0.3 * eio(after / 5), 0.12)
        uni = dict(uFloorY=-2.4, uGrid=0.3 * fade, uFov=0.7, uSweep=0.2 + 0.6 * eio(after / 3), uSweepI=1.0 * fade, uEnvI=0.15 + 0.85 * fade, uDisp=0.016)
        return ('lens', SG.LENS, cam, (0, -0.95, 0), [close, beam * fade], uni, (None, None),
                dict(exposure=1.15, bloom_k=0.26, streak=0.14))
    return None


def sea_scene(t, I):
    """投资启示主场景的镜头与参数（玻璃海 + 悬浮玻璃球）"""
    U = dict(SEA_U)
    i3, i4, i7, i9, i10, i11, i13 = I['I3']['t0'], I['I4']['t0'], I['I7']['t0'], I['I9']['t0'], I['I10']['t0'], I['I11']['t0'], I['I13']['t0']
    if t < i4 - 0.2:
        # I3：第一次看见玻璃海；“风险，是钱还在不在”时推进到金核
        u = cl((t - (i3 - 0.3)) / (i4 - i3))
        push = eio((t - wt('I3', '风险')) / 1.8)
        tgt = (0, lerp(0.6, 0.85, push), 0)
        cam = cam_orbit(tgt, lerp(4.0, 2.0, push), lerp(-0.5, -0.15, u), lerp(0.20, 0.06, push))
        P = sea_params(amp=0.32, spd=1.0, gold=0.9 + 0.6 * push, core=0.3, hov=0.3)
        U.update(uSweep=-0.6 + 0.5 * u)
        return ('sea', SG.SEA, cam, tgt, P, U, (None, None), dict(exposure=1.2, bloom_k=0.22, streak=0.1,
                                                                   focus=float(np.linalg.norm(np.subtract(cam, tgt))), aperture=0.45))
    if t < i7 - 0.3:
        # 华盛顿邮报：风暴（配乐大段落进入）；市值下跌时球落进浪谷，生意增长时金核变大变亮
        u = cl((t - (i4 - 0.2)) / (i7 - i4))
        storm = eo((t - (i4 - 0.15)) / 0.6)
        grow = eio((t - V('I6')['t0']) / 4.5)
        rise = eio((t - wt('I6', '二十年后')) / 2.5)
        tgt = (0, 0.5 + 0.55 * rise, 0)
        cam = cam_orbit(tgt, lerp(4.8, 5.6, rise), -0.9 + 1.1 * u, lerp(0.16, 0.26, rise))
        P = sea_params(amp=0.32 + 0.5 * storm - 0.25 * rise, spd=1.25, gold=0.9 + 0.8 * grow, core=0.28 + 0.2 * grow, hov=0.25 + 0.55 * rise,
                       pulse=grow)
        U.update(uSweep=-1.2 + 1.6 * u, uSweepI=1.1)
        return ('sea', SG.SEA, cam, tgt, P, U, (None, None), dict(exposure=1.2, bloom_k=0.24, streak=0.12,
                                                                   focus=float(np.linalg.norm(np.subtract(cam, tgt))), aperture=0.35))
    if t < i11 - 0.3:
        # 德克斯特：镜面般平静的海，球一动不动 → 内部裂纹 → 碎裂下沉
        u = cl((t - (i7 - 0.3)) / (i11 - i7))
        calm = eio((t - (i7 - 0.3)) / 1.6)
        crack = eio(cl((t - (i9 - 0.1)) / (wt('I9', '价值归零') - i9 + 0.1)))
        shat = cl((t - wt('I9', '价值归零') + 0.05) / 3.2)
        shat = shat * shat * (3 - 2 * shat) * 0.9 + 0.1 * shat
        tgt = (0, 0.6 - 0.45 * shat, 0)
        yaw = 0.35 - 0.5 * u
        cam = cam_orbit(tgt, lerp(3.8, 3.2, eio((t - i9) / 2.0)) + 0.8 * shat, yaw, 0.10 + 0.16 * shat)
        P = sea_params(amp=0.32 * (1 - calm), spd=1.0, gold=1.1 * (1 - 0.75 * crack) * (1 - shat), core=0.3, crack=crack, shat=shat, hov=0.3,
                       rt=(t - wt('I9', '价值归零')) if shat > 0 else 0.0)
        U.update(uSweep=0.5 - 0.6 * u, uSweepI=0.9)
        return ('sea', SG.SEA, cam, tgt, P, U, (None, None), dict(exposure=1.2, bloom_k=0.26, streak=0.12,
                                                                   focus=float(np.linalg.norm(np.subtract(cam, tgt))), aperture=0.4))
    if t < i13 - 0.3:
        # 杠杆：锁链把球拴在海底；浪谷来临时被拉进海里，裂开
        u = cl((t - (i11 - 0.3)) / (V('I11')['t1'] - i11 + 0.6))
        chain = eo((t - wt('I11', '借了钱')) / 0.5)
        tp = wt('I11', '低点卖出')
        pull = eio((t - tp) / 1.2) * 1.3
        crack = eio((t - tp - 1.0) / 0.9)
        bob = 0.28 * math.sin((t - i11) * 1.9) * (1 - eio((t - tp) / 0.6))       # 价格的起伏：球上下浮动
        tgt = (0, 0.15 - 0.35 * pull, 0)
        cam = cam_orbit(tgt, 4.5 - 0.5 * u, -0.5 + 0.6 * u, 0.06)
        P = sea_params(amp=0.0, sea=0.0, gold=1.0 * (1 - 0.7 * crack), core=0.3, chain=chain, pull=pull, crack=0.8 * crack, hov=0.35 + bob)
        U.update(uSweep=-0.2 + 0.4 * u, uSweepI=1.0, uGrid=0.6)
        return ('sea', SG.SEA, cam, tgt, P, U, (None, None), dict(exposure=1.2, bloom_k=0.24, streak=0.1,
                                                                   focus=float(np.linalg.norm(np.subtract(cam, tgt))), aperture=0.35))
    # I13 收尾：俯瞰一片悬浮的玻璃球，暖金色的天光从地平线扫来
    u = cl((t - (i13 - 0.3)) / (T_SUM - i13))
    tgt = (0, 0.3, -1.5 - 1.2 * u)
    cam = (0.3 * math.sin(u * 2.0), lerp(2.2, 4.2, eio(u)), lerp(3.4, 2.0, eio(u)) - 1.2 * u)
    P = sea_params(amp=0.16, spd=0.7, gold=1.2, core=0.32, arr=1.0, hov=0.3)
    U.update(uSweep=0.9, uSweepI=0.45, uFov=0.85, uSpec=0.05)
    return ('sea', SG.SEA, cam, tgt, P, U, (None, None), dict(exposure=1.25, bloom_k=0.24, streak=0.12))


def title_tex():
    """片名贴图：两行（“风险” / “不是波动”）"""
    f1 = ImageFont.truetype(os.path.join(gfx.FONT_DIR, gfx.FONTS['serif_black'] + '.ttf'), 260)
    f2 = ImageFont.truetype(os.path.join(gfx.FONT_DIR, gfx.FONTS['serif_black'] + '.ttf'), 190)
    w = 900; im = Image.new('RGBA', (w, 640), (255, 255, 255, 0)); d = ImageDraw.Draw(im)
    for s, f, y in (('风险', f1, 20), ('不是波动', f2, 360)):
        d.text(((w - f.getlength(s)) / 2, y), s, font=f, fill=(255, 255, 255, 255))
    return np.array(im)


def drawdown_tex():
    """磨砂玻璃屏里的“账户回撤”界面（本片示意图，不是真实账户）"""
    w, h = 600, 1060
    im = Image.new('RGBA', (w, h), (8, 12, 20, 255))
    d = ImageDraw.Draw(im)
    f = lambda n, s: ImageFont.truetype(os.path.join(gfx.FONT_DIR, gfx.FONTS[n] + '.ttf'), s)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 46, outline=(120, 150, 190, 255), width=3)
    d.text((48, 70), '持仓市值', font=f('sans_med', 40), fill=(200, 210, 225, 255))
    d.text((48, 130), '−35.2%', font=f('inter_semi', 110), fill=(240, 96, 78, 255))
    d.text((48, 270), '近 6 个月', font=f('sans', 30), fill=(140, 150, 170, 255))
    rng = np.random.default_rng(4)
    pts = []
    v = 100.0
    for i in range(80):
        v *= 1 + rng.normal(-0.0055, 0.018)
        pts.append((48 + i * (w - 96) / 79, 760 - (v - 60) * 6.0))
    for y in range(380, 900, 100):
        d.line([(48, y), (w - 48, y)], fill=(40, 52, 70, 255), width=2)
    d.line(pts, fill=(240, 96, 78, 255), width=7, joint='curve')
    d.text((48, 940), '示意', font=f('sans', 26), fill=(110, 120, 140, 255))
    return np.array(im)


# ---------------------------------------------------------------- 2D 元素
def chapter_tag(img, t, title, a=1.0):
    if a <= 0.003: return
    text(img, '第二集 · 风险不是波动', 72, 66, 26, 'sans_med', SUB_GOLD, a * 0.95, 'l', track=0.12, shadow=0.3)
    line(img, (72, 92), (72 + 64, 92), SUB_GOLD, a * 0.7, 1)
    text(img, title, 72, 116, 22, 'sans', INK2, a * 0.85, 'l', track=0.08, shadow=0.3)


def gcard(img, x0, y0, x1, y1, a, r=26, tint=None, border=0.55, blur=16):
    """玻璃拟态卡片：背景模糊 + 冷色微染 + 上亮下暗的细边 + 斜向高光"""
    if a <= 0.003: return
    x0, y0, x1, y1 = [int(round(v)) for v in (x0, y0, x1, y1)]
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if X1 <= X0 or Y1 <= Y0: return
    reg = img[Y0:Y1, X0:X1]
    bl = cv2.GaussianBlur(reg, (0, 0), blur)
    m = np.zeros((y1 - y0, x1 - x0), np.float32)
    cv2.rectangle(m, (r, 0), (x1 - x0 - r, y1 - y0), 1, -1); cv2.rectangle(m, (0, r), (x1 - x0, y1 - y0 - r), 1, -1)
    for cx, cy in ((r, r), (x1 - x0 - r, r), (r, y1 - y0 - r), (x1 - x0 - r, y1 - y0 - r)):
        cv2.circle(m, (cx, cy), r, 1, -1, cv2.LINE_AA)
    m = m[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0][..., None] * a
    tint = ICE if tint is None else tint
    gy = np.linspace(1, 0, Y1 - Y0, dtype=np.float32)[:, None, None]
    glass = bl * 0.62 + tint * 0.035 + tint * 0.05 * gy ** 2
    reg[:] = reg * (1 - m) + glass * m
    # 细边：上沿亮、下沿暗
    for k, (aa, col) in enumerate(((border, SILVER), (border * 0.35, ICE))):
        rrect(img, x0 + k, y0 + k, x1 - k, y1 - k, r - k, col, a * aa * (1.0 if k == 0 else 0.6), 1)
    line(img, (x0 + r, y0 + 1), (x1 - r, y0 + 1), np.array([1, 1, 1], np.float32), a * 0.35, 1)


def label(img, x, y, zh, en=None, a=1.0, size=40, col=INK, anchor='m', en_col=None, name='sans_med', track=0.04):
    if a <= 0.003: return
    text(img, zh, x, y, size, name, col, a, anchor, track=track, shadow=0.7)
    if en:
        text(img, en, x, y + size * 0.95, int(size * 0.5), 'inter', en_col if en_col is not None else ICE * 0.85, a * 0.85, anchor,
             track=0.16, shadow=0.6)


def leader(img, p, q, a, col=None):
    if a <= 0.003: return
    col = ICE if col is None else col
    line(img, p, q, col, a * 0.7, 1)
    circle(img, p, 4, col, a, fill=True)
    glow(img, p, 10, col, a * 0.5)


def waveform(img, t, cx, cy, w, hmax, a=1.0, n=24, col=None):
    if a <= 0.003: return
    e = ofr(t)
    bw = w / n
    for k in range(n):
        v = float(e[k]) if k < len(e) else 0.0
        hh = 2 + hmax * min(v, 1.0)
        x = cx - w / 2 + (k + 0.5) * bw
        rect(img, x - 1.5, cy - hh, x + 1.5, cy + hh, col if col is not None else SUB_GOLD, a * (0.35 + 0.65 * min(v * 1.2, 1)))


def narr_sub(img, t, subs, y=1610, hide=()):
    for s in subs:
        if s['id'] in hide: continue
        if s['t0'] <= t <= s['t1']:
            a = env(t, s['t0'], s['t1'], 0.06, 0.08)
            text(img, s['text'], W / 2, y, 46, 'sans_med', INK, a, 'm', track=0.04, shadow=0.95, rise=(1 - a) * 6)


def orig_sub(img, t, s, a, y=1452):
    zl = wrap(s['zh'], 'sans_med', 46, 940)
    el = wrap(s['en'], 'ebg', 36, 930, cjk=False)
    for ln in zl:
        text(img, ln, W / 2, y, 46, 'sans_med', INK, a, 'm', track=0.03, shadow=0.9); y += 62
    y += 8
    for ln in el:
        text(img, ln, W / 2, y, 36, 'ebg', INK2 * 1.05, a * 0.95, 'm', shadow=0.9); y += 46


def hud_ticks(img, t, cx, cy, r, a, col=None):
    fx.hud_ring(img, t, (cx, cy), r, a, col=col if col is not None else ICE)


# ---------------------------------------------------------------- 冷开场
def s_cold(img, t):
    a = env(t, 0.4, T_TITLE - 0.6, 0.8, 0.5)
    if a <= 0: return
    text(img, '1994 · 伯克希尔股东大会 · 巴菲特原声', W / 2, 420, 28, 'sans_med', SUB_GOLD, a * 0.9, track=0.12, shadow=0.6)
    line(img, (W / 2 - 300, 458), (W / 2 + 300, 458), SUB_GOLD, a * 0.35, 1)
    waveform(img, t, W / 2, 1290, 420, 26, a * 0.9, col=ICE)
    for s in TL['cold_subs']:
        sa = env(t, s['t0'] - 0.1, s['t1'] + 0.1, 0.15, 0.2) * a
        if sa > 0: orig_sub(img, t, s, sa, y=1430)


# ---------------------------------------------------------------- 片名 2D 部分
def s_title(img, t):
    a = env(t, T_TITLE - 0.1, V('S1')['t0'] - 0.35, 0.1, 0.4)
    if a <= 0: return
    k = t - T_TITLE
    text(img, '巴菲特与芒格 · 伯克希尔股东大会投资智慧录', W / 2, 470, 32, 'serif_bold', SUB_GOLD, a * eo((k - 0.15) / 0.7), track=0.12, shadow=0.6)
    for sg in (-1, 1):
        L = 90 * eo((k - 0.3) / 0.9)
        line(img, (W / 2 + sg * 400, 470), (W / 2 + sg * (400 + L) * 1.0, 470), SUB_GOLD, a * 0.5, 1)
    text(img, 'RISK  ≠  VOLATILITY', W / 2, 1440, 34, 'corm', SILVER, a * eo((k - 0.6) / 0.8), track=0.32, shadow=0.6)
    ea = a * eo((k - 1.0) / 0.8)
    if ea > 0:
        gcard(img, W / 2 - 150, 1500, W / 2 + 150, 1570, ea, r=14)
        text(img, '第二集', W / 2, 1535, 36, 'sans_med', INK, ea, track=0.3)


# ---------------------------------------------------------------- 开场口播 2D 部分
def s_intro(img, t):
    S1, S2, S3 = V('S1'), V('S2'), V('S3')
    a = env(t, S1['t0'] - 0.3, S3['t0'] - 0.3, 0.3, 0.25)
    if a > 0:
        td = wt('S1', '百分之')
        k = eo((t - td + 0.05) / 0.35)
        if k > 0:
            fx.slam(img, '−25%', W / 2, 520, 150, 'inter_semi', t, td - 0.05, a, gold=False, col=RED, glow_=0.25)
            text(img, '一年', W / 2, 410, 34, 'sans_med', INK2, a * k, track=0.3)
        for i, (s, kw, x) in enumerate((('更危险？', '更危险', 300), ('更便宜？', '更便宜', 780))):
            tk = wt('S1', kw)
            kk = eo((t - tk + 0.05) / 0.4)
            if kk > 0 and t < S2['t0'] - 0.1:
                gcard(img, x - 170, 1120, x + 170, 1230, a * kk, r=20)
                text(img, s, x, 1175, 56, 'serif_black', INK if i == 0 else GOLD_HI, a * kk, rise=(1 - kk) * 10)
        # S2：教科书的答案
        kb = eo((t - S2['t0'] + 0.05) / 0.4)
        if kb > 0:
            gcard(img, W / 2 - 300, 1060, W / 2 + 300, 1290, a * kb, r=24, tint=RED * 0.6)
            text(img, '教科书 · 贝塔理论', W / 2, 1110, 30, 'sans_med', INK2, a * kb, track=0.2)
            fx.slam(img, 'β ↑  ＝  风险 ↑', W / 2, 1200, 76, 'inter_semi', t, wt('S2', '贝塔') - 0.05, a * kb, gold=False, col=INK, glow_=0.1)
            ke = eo((t - wt('S2', '更危险')) / 0.35)
            if ke > 0:
                fx.slam(img, '更危险', W / 2, 1390, 88, 'serif_black', t, wt('S2', '更危险') - 0.05, a, gold=False, col=RED, glow_=0.3)
    a3 = env(t, S3['t0'] - 0.3, T_CTX + 0.2, 0.3, 0.4)
    if a3 > 0:
        text(img, '1994 · 奥马哈 · 伯克希尔股东大会上午场实况', W / 2, 1110, 26, 'sans', INK2, a3 * 0.9, track=0.08, shadow=0.7)
        tq = wt('S3', '你们')
        fx.slam(img, '“你们说的风险，', W / 2, 1250, 72, 'serif_black', t, tq - 0.05, a3, glow_=0.3)
        fx.slam(img, '到底是什么？”', W / 2, 1350, 72, 'serif_black', t, wt('S3', '到底') - 0.05, a3, glow_=0.3)
    narr_sub(img, t, INTRO['subs'])


# ---------------------------------------------------------------- 回到 1994：背景卡
def s_ctx(img, t):
    a = env(t, T_CTX, T_Q + 1.2, 0.5, 0.8)
    if a <= 0: return
    k = t - T_CTX
    fr = grade(QA_CLIP.get(QA['segs'][0]['src_in'] + max(0.0, t - T_Q)), sat=0.4, gain=0.6)
    window(img, fr, W / 2, 960, 1080, 437, zoom=1.15 + 0.02 * k, a=a * 0.55, blur_bg=0.75)
    text(img, '1994', W / 2, 700, 330, 'corm_med', ICE * 0.6, a * 0.16, track=0.02, shadow=0)
    gcard(img, 90, 560, 990, 1370, a * eo(k / 0.6), r=30)
    text(img, '1994 年 4 月 25 日 · 美国奥马哈', W / 2, 650, 34, 'sans_med', SUB_GOLD, a * eo(k / 0.6), track=0.12)
    text(img, '伯克希尔·哈撒韦年度股东大会', W / 2, 750, 58, 'serif_bold', INK, a * eo((k - 0.2) / 0.7), track=0.04)
    text(img, '上午场 · 股东问答', W / 2, 840, 44, 'serif_med', INK2, a * eo((k - 0.4) / 0.7), track=0.2)
    line(img, (W / 2 - 160, 905), (W / 2 + 160, 905), SUB_GOLD, a * 0.5 * eo((k - 0.5) / 0.6), 1)
    text(img, 'CNBC 巴菲特档案 · 第 50 章', W / 2, 965, 28, 'sans', INK2, a * eo((k - 0.7) / 0.7), track=0.06)
    text(img, 'Risk is “inextricably wound up”', W / 2, 1025, 38, 'ebg_i', INK, a * eo((k - 0.8) / 0.7))
    text(img, 'in how long an asset is held', W / 2, 1075, 38, 'ebg_i', INK, a * eo((k - 0.9) / 0.7))
    na = a * eo((k - 1.3) / 0.8)
    text(img, '以下为原始录像节选，省略之处以“玻璃快门”标出', W / 2, 1200, 30, 'sans', INK2, na, track=0.02)
    text(img, '画面与声音均为 1994 年现场原始记录', W / 2, 1260, 30, 'sans', INK2, na, track=0.02)


# ---------------------------------------------------------------- 原始问答
QA_BACK = None


def qa_backdrop():
    """原声段的背景：一帧失焦的玻璃海（预渲染一次，之后只做缓慢平移）"""
    global QA_BACK
    if QA_BACK is None:
        p = os.path.join(WORK, 'qa_backdrop.npy')
        if os.path.exists(p):
            QA_BACK = np.load(p)
        else:
            P = sea_params(amp=0.25, gold=0.7, core=0.3, hov=0.3)
            cam = cam_orbit((0, 0.3, 0), 6.0, -0.4, 0.18)
            hdr = R().render('sea', SG.SEA, 3.0, cam, (0, 0.3, 0), P, scale=1.0, **SEA_U)
            img = PP.finish(hdr, 0, exposure=0.9, focus=1.5, aperture=1.2, bloom_k=0.2, streak=0.0)
            img = cv2.resize(img, (int(W * 1.12), int(H * 1.12)))
            QA_BACK = (cv2.GaussianBlur(img, (0, 0), 6) * 0.55).astype(np.float32)
            np.save(p, QA_BACK)
    return QA_BACK


def qa_env(t, sc, fi=0.45, fo=0.45, pre=0.3, post=0.3):
    s = QSC.get(sc)
    if not s: return 0.0
    return env(t, s['t0'] - pre, s['t1'] + post, fi, fo)


WIN_W, WIN_H = 1000, 405          # 源画面干净区域 1515×614（≈2.47:1），等比缩放


def s_qa(img, t):
    a = env(t, T_Q - 0.4, T_QE + 0.6, 0.6, 0.9)
    if a <= 0: return
    bk = qa_backdrop()
    ox = int((bk.shape[1] - W) * (0.5 + 0.4 * math.sin((t - T_Q) * 0.02)))
    oy = int((bk.shape[0] - H) * 0.5)
    img[:] = img * (1 - a) + bk[oy:oy + H, ox:ox + W] * a
    chapter_tag(img, t, '原始问答 · 1994 上午场原始录像（节选）', a)
    src = qa_src(t)
    if src is None: src = QA['segs'][-1]['src_out']
    fr = grade(QA_CLIP.get(src), sat=0.62, gain=0.98)
    # 芒格开口时，镜头缓缓推向芒格（画面右侧）
    mz = eio((t - QA['munger_t'] + 1.0) / 2.5)
    zoom = 1.0 + 0.32 * mz + 0.02 * math.sin((t - T_Q) * 0.05)
    pan = (0.17 * mz, -0.03 * mz)
    cy = 500
    gcard(img, (W - WIN_W) / 2 - 18, cy - WIN_H / 2 - 18, (W + WIN_W) / 2 + 18, cy + WIN_H / 2 + 18, a, r=22, blur=10)
    window(img, fr, W / 2, cy, WIN_W, WIN_H, zoom=zoom, pan=pan, a=a, feather=10)
    # 省略处：一道玻璃快门从画面上扫过，并标出“节选”
    for ct in QA['cuts']:
        k = (t - ct + 0.45) / 0.9
        if 0 < k < 1:
            x = lerp(-120, W + 120, eio(k))
            for dx, aa in ((0, 0.5), (26, 0.25), (52, 0.12)):
                rect(img, x - dx - 10, cy - WIN_H / 2 - 18, x - dx + 10, cy + WIN_H / 2 + 18, SILVER, a * aa * math.sin(math.pi * k))
            text(img, '· 节选 ·', W / 2, cy + WIN_H / 2 + 50, 26, 'sans_med', ICE, a * math.sin(math.pi * k), track=0.4)
    text(img, '画面与声音：1994 年上午场原始录像', 72, cy + WIN_H / 2 + 48, 22, 'sans', INK3 * 1.3, a * 0.95, 'l', track=0.04, shadow=0.5)
    # 说话人 + 原声波形
    mt, at = QA['munger_t'], QA['answer_t']
    spk = '查理·芒格' if t >= mt - 0.3 else ('沃伦·巴菲特' if t >= at - 0.2 else '提问 · 来自密歇根州的股东')
    circle(img, (84, 800), 6, GOLD, a, fill=True)
    text(img, spk, 104, 800, 30, 'sans_med', INK, a, 'l', track=0.04)
    waveform(img, t, 860, 800, 260, 22, a, col=ICE)
    line(img, (72, 846), (1008, 846), INK3, a * 0.5, 1)
    qa_panels(img, t, a)
    for s in QA['subs']:
        sa = env(t, s['t0'], s['t1'], 0.07, 0.07)
        if sa > 0: orig_sub(img, t, s, sa * a)
    la = env(t, TL['laugh']['t0'], TL['laugh']['t1'], 0.15, 0.2)
    if la > 0: text(img, '（现场笑声）', W / 2, 1560, 32, 'sans', INK2, la * a * 0.85, track=0.1)


def qs(sid, d=0.0):
    return QSUB[sid]['t0'] + d


def qa_panels(img, t, a):
    """关键观点面板（y 890–1390）：克制的玻璃卡片 + 简洁图示"""
    # 提问
    ka = qa_env(t, 'ask')
    if ka > 0:
        gcard(img, 110, 900, 970, 1380, a * ka)
        text(img, '股东的问题', W / 2, 960, 28, 'sans_med', SUB_GOLD, a * ka, track=0.3)
        k0 = eo((t - qs('Q1', 0.4)) / 0.6) * (1 - eo((t - qs('Q2')) / 0.5))
        text(img, '金融世界里的风险，', W / 2, 1110, 56, 'serif_bold', INK, a * ka * k0)
        text(img, '您怎么看？', W / 2, 1200, 56, 'serif_bold', a=a * ka * k0, gold=True)
        text(img, '您的风险观', 300, 1080, 50, 'serif_bold', INK, a * ka * eo((t - qs('Q2')) / 0.6))
        text(img, '传统的风险观', 780, 1080, 50, 'serif_bold', INK2, a * ka * eo((t - qs('Q3')) / 0.6))
        k = eo((t - qs('Q3', 1.0)) / 0.5)
        text(img, '≠', W / 2, 1080, 60, 'inter', RED, a * ka * k)
        kb = eo((t - qs('Q5')) / 0.6)
        text(img, '用 β（贝塔）衡量风险，', W / 2, 1220, 52, 'serif_bold', a=a * ka * kb, gold=True)
        text(img, '是否自相矛盾？', W / 2, 1300, 52, 'serif_bold', INK, a * ka * kb)
    # 定义
    ka = qa_env(t, 'define')
    if ka > 0:
        gcard(img, 110, 900, 970, 1380, a * ka)
        text(img, '巴菲特对风险的定义', W / 2, 960, 28, 'sans_med', SUB_GOLD, a * ka, track=0.3)
        k = eo((t - qs('A1', 0.6)) / 0.8)
        text(img, '受到伤害或损失', W / 2, 1090, 76, 'serif_black', a=a * ka * k, gold=True, glow=0.2, wipe=k)
        text(img, '的可能性', W / 2, 1185, 56, 'serif_bold', INK, a * ka * eo((t - qs('A1', 1.4)) / 0.6))
        text(img, 'the possibility of harm or injury', W / 2, 1255, 30, 'ebg_i', INK2, a * ka * eo((t - qs('A1', 1.8)) / 0.6))
        k2 = eo((t - qs('A2', 2.0)) / 0.7)
        text(img, '—— 与持有期限密不可分', W / 2, 1335, 38, 'sans_med', ICE, a * ka * k2, track=0.04)
    # 持有期：今天上午买、收盘卖
    ka = qa_env(t, 'horizon')
    if ka > 0:
        gcard(img, 110, 900, 970, 1380, a * ka)
        text(img, '持有一天', W / 2, 960, 28, 'sans_med', SUB_GOLD, a * ka, track=0.3)
        x0, x1, yc = 190, 890, 1120
        k = eo((t - qs('A3')) / 1.2)
        line(img, (x0, yc), (x0 + (x1 - x0) * k, yc), SILVER, a * ka, 2)
        text(img, '11:30 买入', x0, yc - 50, 34, 'inter_semi', INK, a * ka * eo((t - qs('A3', 1.5)) / 0.5), 'l')
        kk = eo((t - qs('A4')) / 0.5)
        text(img, '收盘前卖出', x1, yc - 50, 34, 'sans_med', INK, a * ka * kk, 'r')
        rng = np.random.default_rng(3)
        pts = []
        for i in range(60):
            x = x0 + (x1 - x0) * i / 59
            if x > x0 + (x1 - x0) * k: break
            pts.append((x, yc + 50 * math.sin(i * 0.9) * rng.uniform(0.3, 1.0)))
        if len(pts) > 1: poly(img, pts, ICE, a * ka * 0.8, 2)
        k3 = eo((t - qs('A6')) / 0.6)
        if k3 > 0:
            text(img, '50%', W / 2, 1270, 110, 'inter_semi', RED, a * ka * k3)
            text(img, '的概率受损', W / 2, 1345, 36, 'sans_med', INK2, a * ka * k3)
    # 可口可乐：同一家公司，持有期不同，风险完全不同
    ka = qa_env(t, 'coke')
    if ka > 0:
        gcard(img, 110, 900, 970, 1380, a * ka)
        text(img, '同一只可口可乐', W / 2, 960, 28, 'sans_med', SUB_GOLD, a * ka, track=0.3)
        k1 = eo((t - qs('A8')) / 0.7); k2 = eo((t - qs('A10')) / 0.7)
        for (x, title, sub, val, col, k) in ((330, '以买入价长期持有', '按我们的持有期', '≈ 0', GOLD_HI, k1),
                                             (750, '今早买 · 明早卖', '持有一夜', '高风险', RED, k2)):
            if k <= 0: continue
            gcard(img, x - 190, 1020, x + 190, 1340, a * ka * k, r=20, tint=col * 0.6)
            text(img, title, x, 1080, 36, 'serif_bold', INK, a * ka * k)
            text(img, sub, x, 1135, 26, 'sans', INK2, a * ka * k, track=0.06)
            text(img, '风险', x, 1205, 32, 'sans_med', INK2, a * ka * k, track=0.3)
            text(img, val, x, 1280, 74 if val != '高风险' else 64, 'serif_black', col, a * ka * k)
    # 贝塔：学术界的定义
    ka = qa_env(t, 'beta')
    if ka > 0:
        gcard(img, 110, 900, 970, 1380, a * ka)
        text(img, '学术界 → 金融市场', W / 2, 960, 28, 'sans_med', SUB_GOLD, a * ka, track=0.3)
        k0 = eo((t - qs('A12')) / 0.6)
        k1 = eo((t - qs('A14')) / 0.7)
        text(img, '“我在年报里也指出过”', W / 2, 1030, 32, 'sans', INK2, a * ka * k0 * (1 - k1), track=0.04)
        text(img, '风险 ＝ 波动', W / 2, 1090, 76, 'serif_black', INK, a * ka * max(k1, 0.35 * eo((t - qs('A13')) / 0.6)))
        text(img, '贝塔（β）：衡量过去的波动', W / 2, 1175, 34, 'sans', INK2, a * ka * k1, track=0.04)
        k2 = eo((t - qs('A15')) / 0.4)
        if k2 > 0:
            ww = text_w('风险 ＝ 波动', 'serif_black', 76)
            line(img, (W / 2 - ww / 2 - 10, 1090), (W / 2 - ww / 2 - 10 + (ww + 20) * k2, 1090), RED, a * ka, 4)
            text(img, '对我们来说，不是风险的衡量', W / 2, 1300, 46, 'serif_bold', a=a * ka * k2, gold=True)
    # 荒谬：+20%~+80% 比稳定 5% “风险更高”？
    ka = qa_env(t, 'absurd')
    if ka > 0:
        gcard(img, 110, 900, 970, 1380, a * ka)
        text(img, '按传统风险度量', W / 2, 960, 28, 'sans_med', SUB_GOLD, a * ka, track=0.3)
        yb, sc = 1260, 1.9
        kA = eo((t - qs('A17')) / 0.8); kB = eo((t - qs('A18')) / 0.8)
        for (x0_, title_, sub_, col, k, vals) in ((170, '投资 A', '每年 +20% ～ +80%', ICE, kA, [20 + 60 * (0.5 + 0.5 * math.sin(i * 2.3 + 1.0)) for i in range(8)]),
                                                 (590, '投资 B', '每年稳定 +5%', GOLD, kB, [5] * 8)):
            if k <= 0: continue
            text(img, title_, x0_ + 160, 1020, 36, 'serif_bold', INK, a * ka * k)
            text(img, sub_, x0_ + 160, 1068, 26, 'sans_med', col, a * ka * k)
            line(img, (x0_, yb), (x0_ + 320, yb), SILVER, a * ka * 0.6 * k, 1)
            for i, v in enumerate(vals):
                x = x0_ + 20 + i * 40
                h = v * sc * eo(k * 1.4 - i * 0.05)
                rect(img, x - 13, yb - h, x + 13, yb, col, a * ka * 0.85 * k)
            text(img, '0%', x0_ - 12, yb, 20, 'inter', INK2, a * ka * k, 'r')
        k3 = eo((t - qs('A18', 1.6)) / 0.5); k4 = eo((t - qs('A19')) / 0.5)
        if k3 > 0:
            text(img, '“A 的风险更高”？', W / 2, 1320, 46, 'serif_black', RED, a * ka * k3 * (1 - k4))
        if k4 > 0:
            text(img, 'haywire · 乱了套', W / 2, 1320, 50, 'serif_black', a=a * ka * k4, gold=True, glow=0.15)
    # 期望：单笔可以亏，一组的期望不能为负
    ka = qa_env(t, 'expect')
    if ka > 0:
        gcard(img, 110, 900, 970, 1380, a * ka)
        text(img, '伯克希尔的做法', W / 2, 960, 28, 'sans_med', SUB_GOLD, a * ka, track=0.3)
        k1 = eo((t - qs('A21')) / 0.6)
        text(img, '单笔交易：可以亏', W / 2, 1040, 44, 'serif_bold', INK, a * ka * k1)
        rng = np.random.default_rng(9)
        outs = rng.normal(0.35, 1.0, 36)
        n = int(36 * eio((t - qs('A22')) / 3.0))
        for i in range(n):
            x = 190 + (i % 18) * 40; y = 1120 + (i // 18) * 50
            v = outs[i]
            circle(img, (x, y), 13, GOLD if v > 0 else RED, a * ka * 0.9, fill=True)
        k2 = eo((t - qs('A24')) / 0.7)
        if k2 > 0:
            text(img, '一组同类、相互独立的交易：', W / 2, 1260, 36, 'sans_med', INK2, a * ka * k2)
            text(img, '期望值必须为正', W / 2, 1330, 56, 'serif_black', a=a * ka * eo((t - qs('A25')) / 0.6), gold=True, glow=0.2)
    # 芒格
    ka = qa_env(t, 'munger', post=0.8)
    if ka > 0:
        gcard(img, 110, 900, 970, 1380, a * ka)
        text(img, '芒格的补充', W / 2, 960, 28, 'sans_med', SUB_GOLD, a * ka, track=0.3)
        k1 = eo((t - qs('M1', 1.2)) / 0.7)
        text(img, '费马　·　帕斯卡', W / 2, 1080, 64, 'serif_black', a=a * ka * k1, gold=True, glow=0.15)
        text(img, 'FERMAT · PASCAL', W / 2, 1150, 26, 'corm', INK2, a * ka * k1, track=0.3)
        k2 = eo((t - qs('M2')) / 0.6)
        text(img, '像从没听说过现代金融理论那样', W / 2, 1240, 40, 'serif_bold', INK, a * ka * k2)
        text(img, '用概率思考', W / 2, 1310, 40, 'serif_bold', ICE, a * ka * k2)


# ---------------------------------------------------------------- 投资启示 2D 部分
def ins_card(img, t):
    a = env(t, T_INS - 0.1, V('I1')['t0'] + 1.2, 0.3, 0.6)
    if a <= 0: return
    k = t - T_INS
    text(img, '投资启示', W / 2, 400, 88, 'serif_black', a=a * eo(k / 0.6), gold=True, glow=0.25)
    text(img, 'INSIGHT', W / 2, 480, 26, 'corm', SILVER, a * eo((k - 0.2) / 0.6), track=0.5)
    text(img, '本片解读，非巴菲特或芒格原话', W / 2, 540, 26, 'sans', INK2, a * eo((k - 0.4) / 0.6), track=0.08)


def s_insight(img, t):
    if t < T_INS - 0.2 or t > T_SUM: return
    ins_card(img, t)
    I = {k: V(k) for k in ('I1', 'I2', 'I3', 'I4', 'I5', 'I6', 'I7', 'I8', 'I9', 'I10', 'I11', 'I12', 'I13')}
    ca = env(t, T_INS + 1.0, T_SUM - 0.3, 0.6, 0.4)
    chapter_tag(img, t, '投资启示 · 本片解读', ca)
    # I1：两块碑的标签
    a = env(t, I['I1']['t0'] - 0.2, I['I2']['t0'] - 0.35, 0.4, 0.3)
    if a > 0:
        k1 = eo((t - wt('I1', '受到伤害')) / 0.5); k2 = eo((t - wt('I1', '教科书')) / 0.5)
        label(img, 785, 300, '巴菲特', 'BUFFETT', a * k1, size=40, col=GOLD_HI)
        label(img, 785, 400, '损失的可能性', None, a * k1, size=38, col=INK)
        label(img, 295, 300, '教科书', 'TEXTBOOK', a * k2, size=40, col=ICE)
        label(img, 295, 400, '价格的波动 β', None, a * k2, size=38, col=INK)
    # I2：持有期（竖直时间管：从下往上）
    a = env(t, I['I2']['t0'] - 0.2, I['I3']['t0'] - 0.35, 0.4, 0.3)
    if a > 0:
        kc = eo((t - wt('I2', '购买力')) / 0.6)
        k = eo((t - wt('I2', '持有期')) / 0.5)
        label(img, 700, 1230, '买入', 'BUY', a * k, size=38, col=INK, anchor='l')
        k = eo((t - wt('I2', '持有期') - 1.0) / 0.5)
        label(img, 700, 470, '持有期结束', 'END OF HOLDING', a * k, size=38, col=INK, anchor='l')
        if kc > 0:
            gcard(img, 110, 1330, 970, 1540, a * kc, r=22, tint=GOLD * 0.5)
            text(img, '拿回的钱 ≥ 当初的购买力', W / 2, 1395, 50, 'serif_bold', a=a * kc, gold=True)
            text(img, '“at least as much purchasing power as he had to begin with”', W / 2, 1460, 22, 'ebg_i', INK2, a * kc)
            text(img, '—— 巴菲特 1993 年致股东信', W / 2, 1505, 22, 'sans', INK2, a * kc, track=0.06)
    # I3
    a = env(t, I['I3']['t0'] - 0.2, I['I4']['t0'] - 0.2, 0.3, 0.25)
    if a > 0:
        k1 = eo((t - I['I3']['t0']) / 0.5); k2 = eo((t - wt('I3', '风险')) / 0.5)
        label(img, W / 2, 1250, '波动 ＝ 价格摆动的幅度', None, a * k1 * (1 - 0.55 * k2), size=42, col=ICE)
        label(img, W / 2, 1340, '风险 ＝ 钱还在不在', None, a * k2, size=54, col=GOLD_HI, name='serif_black')
    # 华盛顿邮报
    a = env(t, I['I4']['t0'] - 0.15, I['I7']['t0'] - 0.3, 0.25, 0.35)
    if a > 0:
        gcard(img, 90, 330, 990, 470, a, r=22)
        text(img, '华盛顿邮报', 140, 382, 44, 'serif_black', INK, a, 'l')
        text(img, 'THE WASHINGTON POST · 1973', 140, 436, 22, 'inter', ICE, a * 0.9, 'l', track=0.16)
        tb = wt('I4', '一千零六十')
        kb = eo((t - tb) / 0.5)
        td = wt('I4', '八百万')
        kd = eo((t - td) / 0.5)
        tg = wt('I6', '超过')
        kg = eo((t - tg) / 0.6)
        if kg > 0:
            v = 0.106 + (4.40 - 0.106) * eio((t - tg) / 1.6)
            text(img, '> $4 亿' if (t - tg) > 1.6 else f'${v:.2f} 亿', 940, 400, 60, 'inter_semi', a=a * kg, gold=True, anchor='r', glow=0.2)
            text(img, '1993 年持股市值', 940, 452, 22, 'sans', INK2, a * kg, 'r', track=0.1)
        elif kd > 0:
            text(img, '$800 万', 940, 392, 56, 'inter_semi', RED, a * kd, 'r')
            text(img, '1974 年底 · −25%', 940, 448, 22, 'sans_med', RED, a * kd, 'r', track=0.08)
        elif kb > 0:
            text(img, '$1,060 万', 940, 392, 56, 'inter_semi', INK, a * kb, 'r')
            text(img, '1973 年买入成本', 940, 448, 22, 'sans', INK2, a * kb, 'r', track=0.1)
        k5 = env(t, V('I5')['t0'] - 0.1, V('I6')['t0'] + 0.6, 0.3, 0.4)
        if k5 > 0:
            gcard(img, W / 2 - 290, 1180, W / 2 + 290, 1300, a * k5, r=20, tint=RED * 0.6)
            text(img, 'β 理论：价格更低 → “更危险”', W / 2, 1240, 38, 'serif_bold', RED, a * k5)
        k6 = eo((t - V('I6')['t0']) / 0.6) * (1 - eo((t - tg) / 0.5))
        if k6 > 0:
            label(img, W / 2, 1250, '生意一直在增长', 'INTRINSIC VALUE GROWING', a * k6, size=48, col=GOLD_HI, name='serif_black')
    # 德克斯特
    a = env(t, I['I7']['t0'] - 0.2, I['I11']['t0'] - 0.35, 0.3, 0.35)
    if a > 0:
        gcard(img, 90, 330, 990, 470, a, r=22)
        text(img, '德克斯特鞋业', 140, 382, 44, 'serif_black', INK, a, 'l')
        text(img, 'DEXTER SHOE · 1993', 140, 436, 22, 'inter', ICE, a * 0.9, 'l', track=0.16)
        kb = eo((t - wt('I7', '价值')) / 0.5)
        t57 = wt('I10', '五十七')
        if t < t57 - 0.2:
            text(img, '$4.33 亿', 940, 392, 56, 'inter_semi', INK, a * kb, 'r')
            text(img, '以伯克希尔股票支付', 940, 448, 22, 'sans', INK2, a * kb, 'r', track=0.1)
        k8 = env(t, V('I8')['t0'] - 0.1, V('I9')['t0'] + 0.3, 0.3, 0.3)
        if k8 > 0:
            gcard(img, W / 2 - 300, 1170, W / 2 + 300, 1330, a * k8, r=20)
            text(img, '全资收购 · 没有股价', W / 2, 1220, 40, 'serif_bold', INK, a * k8)
            kf = eo((t - wt('I8', '波动')) / 0.5)
            line(img, (W / 2 - 220, 1285), (W / 2 - 220 + 300 * kf, 1285), ICE, a * k8, 2)
            text(img, '波动 ＝ 0', W / 2 + 160, 1285, 36, 'inter_semi', ICE, a * k8 * kf)
        k9 = eo((t - wt('I9', '海外')) / 0.5) * (1 - eo((t - wt('I9', '价值归零')) / 0.4))
        if k9 > 0:
            label(img, W / 2, 1250, '海外竞争 → 优势消失', 'COMPETITIVE ADVANTAGE VANISHED', a * k9, size=46, col=RED, name='serif_black')
        kz = env(t, wt('I9', '价值归零') - 0.05, V('I10')['t0'] + 0.2, 0.2, 0.3)
        if kz > 0:
            fx.slam(img, '价值 → 0', W / 2, 1260, 104, 'serif_black', t, wt('I9', '价值归零') - 0.05, a * kz, gold=False, col=RED, glow_=0.35)
        k10 = eo((t - t57 + 0.1) / 0.5)
        if k10 > 0:
            v = 0.433 + (5.7 - 0.433) * eio((t - t57) / 1.4)
            text(img, f'${v:.1f} 亿' if v < 5.69 else '$57 亿', 940, 392, 60, 'inter_semi', RED, a * k10, 'r', glow=0.0)
            text(img, '所付股票 2014 年的价值', 940, 448, 22, 'sans_med', RED, a * k10, 'r', track=0.06)
            kq = eo((t - t57 - 1.0) / 0.7)
            gcard(img, 130, 1180, 950, 1340, a * kq, r=20)
            text(img, '“迄今为止，我做过的最糟糕的交易。”', W / 2, 1238, 38, 'serif_bold', INK, a * kq)
            text(img, '“To date, Dexter is the worst deal that I’ve made.” —— 2007 年致股东信', W / 2, 1300, 21, 'ebg_i', INK2, a * kq)
    # 杠杆
    a = env(t, I['I11']['t0'] - 0.2, I['I12']['t0'] - 0.35, 0.3, 0.35)
    if a > 0:
        k1 = eo((t - wt('I11', '借了钱')) / 0.5)
        label(img, 280, 1450, '借来的钱', 'LEVERAGE', a * k1, size=42, col=RED)
        k2 = eo((t - wt('I11', '低点卖出')) / 0.5)
        label(img, 790, 1450, '被迫在低点卖出', 'FORCED SELLING', a * k2, size=42, col=RED)
        k3 = eo((t - wt('I11', '暂时')) / 0.5)
        if k3 > 0:
            gcard(img, 110, 330, 970, 520, a * k3, r=24)
            text(img, '暂时的下跌', 330, 425, 52, 'serif_bold', ICE, a * k3)
            text(img, '→', W / 2 + 10, 425, 52, 'inter', INK2, a * k3)
            text(img, '永久的损失', 760, 425, 52, 'serif_black', RED, a * eo((t - wt('I11', '永久')) / 0.4))
    # 今天
    a = env(t, I['I12']['t0'] - 0.2, I['I13']['t0'] - 0.3, 0.3, 0.35)
    if a > 0:
        q1 = eo((t - wt('I12', '这门生意')) / 0.5); q2 = eo((t - wt('I12', '我会')) / 0.5)
        if q1 > 0:
            gcard(img, 120, 330, 960, 460, a * q1, r=22, tint=GOLD * 0.5)
            text(img, '这门生意还在吗？', W / 2, 395, 58, 'serif_black', a=a * q1, gold=True, rise=(1 - q1) * 10)
        if q2 > 0:
            gcard(img, 120, 490, 960, 620, a * q2, r=22, tint=GOLD * 0.5)
            text(img, '我会被迫卖出吗？', W / 2, 555, 58, 'serif_black', a=a * q2, gold=True, rise=(1 - q2) * 10)
    # I13：收尾的整句（用大字代替字幕）
    a = env(t, I['I13']['t0'] - 0.2, T_SUM - 0.35, 0.4, 0.5)
    if a > 0:
        k1 = eo((t - I['I13']['t0'] + 0.1) / 1.0); k2 = eo((t - wt('I13', '真正值得') + 0.1) / 1.0)
        text(img, '价格的剧烈波动，', W / 2, 1020, 58, 'serif_bold', INK, a * k1, wipe=k1)
        text(img, '不必然意味着真正的风险；', W / 2, 1100, 58, 'serif_bold', INK, a * eo((t - wt('I13', '不必然') + 0.1) / 1.0),
             wipe=eo((t - wt('I13', '不必然') + 0.1) / 1.0))
        text(img, '真正值得警惕的，', W / 2, 1220, 62, 'serif_black', a=a * k2, gold=True, wipe=k2, glow=0.15)
        kk = eo((t - wt('I13', '本金') + 0.1) / 1.0)
        text(img, '是本金永久损失的可能性。', W / 2, 1305, 62, 'serif_black', a=a * kk, gold=True, wipe=kk, glow=0.2)
    narr_sub(img, t, INS['subs'], hide=('I13',))


# ---------------------------------------------------------------- 一句话总结 + 品牌片尾（与第一集相同的固定片尾）
def summary_masks():
    out = []
    for s, y in (('波动不是风险，', 880), ('永久损失才是。', 1010)):
        m, w, base, pad = text_mask(s, 'serif_black', 96, 0.04)
        out.append((m, int(W / 2 - w / 2 - pad), int(y + 96 * 0.36 - base)))
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
        text(img, '一句话总结', W / 2, 740, 28, 'sans_med', SUB_GOLD, a * eo(k / 0.6), track=0.4, shadow=0.6)
        for sg in (-1, 1):
            line(img, (W / 2 + sg * 110, 740), (W / 2 + sg * (110 + 90 * eo(k / 1.0)), 740), SUB_GOLD, a * 0.6, 1)
        w1 = eo((t - VOD['M']['t0'] + 0.1) / 1.0); w2 = eo((t - wt('M', '永久') + 0.05) / 1.0)
        sh = cl((t - VOD['M']['t1'] - 0.2) / 1.4) if VOD['M']['t1'] + 0.2 < t < VOD['M']['t1'] + 1.6 else None
        text(img, '波动不是风险，', W / 2, 880, 96, 'serif_black', a=a, gold=True, wipe=w1, shine=sh, track=0.04, glow=0.18)
        text(img, '永久损失才是。', W / 2, 1010, 96, 'serif_black', a=a, gold=True, wipe=w2, shine=sh, track=0.04, glow=0.18)
        text(img, '伯克希尔股东大会投资智慧录 · 第二集', W / 2, 1150, 26, 'sans', INK2, a * eo((k - 1.2) / 0.8), track=0.1, shadow=0.6)


def s_end(img, t):
    tp, tl_, tb = END['t_particles'], END['t_logo'], END['t_brand']
    if t < tp: return
    fade = 1 - eio((t - END['t_fade0']) / (END['t_fade1'] - END['t_fade0']))
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
    gk = eo((t - tl_) / 1.2) * fade
    glow(img, (W / 2, LOGO_CY), 120, BLUE * 0.35, gk * 0.6)
    if t >= tb: glow(img, (W / 2, LOGO_CY), 160, GOLD * 0.3, math.exp(-(t - tb) / 0.5) * fade)
    la = eo((t - tl_) / 1.0) * fade
    if la > 0:
        over(img, LOGO_RGB.astype(np.float32), LOGO_A.astype(np.float32) * la, int(W / 2 - LOGO_PX / 2), int(LOGO_CY - LOGO_PX / 2))
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
        kf = eo((t - END['t_follow']) / 0.9)
        if kf > 0:
            text(img, '关注「巴芒价值」，传承大师智慧，领悟投资真谛', W / 2, 1225 + 10 * (1 - kf), 36, 'sans_med', a=fade * kf,
                 gold=True, track=0.04, glow=0.2)
            ln = 300 * eo((t - END['t_follow'] - 0.3) / 0.9)
            line(img, (W / 2 - ln, 1285), (W / 2 + ln, 1285), SUB_GOLD * 0.7, fade * kf * 0.6, 1)


# ---------------------------------------------------------------- 合成一帧
def punch(img, t, strength=1.0):
    """卡点：推镜 + 闪光 + 色散（三维场景已在 HDR 里做过泛光，这里不再叠加）"""
    e = fx.hit_env(t, HITS) * strength
    be = fx.beat_env(t, BARS) * 0.35 * strength
    z = 1.0 + 0.04 * e + 0.006 * be
    out = img
    if z > 1.0005:
        M = cv2.getRotationMatrix2D((W / 2, H * 0.47), 0, z)
        out = cv2.warpAffine(out, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if e > 0.02:
        out = out + np.array([0.85, 0.92, 1.0], np.float32) * 0.09 * e
        d = int(round(7 * e))
        if d >= 1:
            out[:, d:, 0] = out[:, :-d, 0].copy()
            out[:, :-d, 2] = out[:, d:, 2].copy()
    return out


def frame(t):
    sc = gl_scene(t)
    if sc is not None:
        name, src, cam, tgt, P, uni, (t0_, t1_), po = sc
        hdr = R().render(name, src, t, cam, tgt, P, scale=SS, tex0=t0_, tex1=t1_, **uni)
        img = PP.finish(hdr, int(t * FPS), ss=SS, **po).astype(np.float32)
    else:
        img = BG.copy() * np.array([0.85, 0.9, 1.0], np.float32)
    s_cold(img, t)
    s_title(img, t)
    s_intro(img, t)
    s_ctx(img, t)
    s_qa(img, t)
    s_insight(img, t)
    s_summary(img, t)
    s_end(img, t)
    if sc is None:
        img = fx.post(img, t, HITS, BARS, strength=0.5 if T_Q + 1 < t < T_QE else 1.0)
        img *= VIG
        img += GRAIN[int(t * FPS) % len(GRAIN)]
    else:
        img = punch(img, t)
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
            print('still', tt, flush=True)
        return
    if cmd == 'chunk':
        a, b, path = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                              '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16',
                              '-pix_fmt', 'yuv420p', '-tune', 'film', path], stdin=subprocess.PIPE)
        for i in range(a, b):
            p.stdin.write(frame(i / FPS).tobytes())
            if (i - a) % 150 == 0: print(f'[{a}-{b}] {i - a}/{b - a}', flush=True)
        p.stdin.close(); p.wait()


if __name__ == '__main__':
    main()
