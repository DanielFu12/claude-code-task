"""电影感特效：金色景深粒子（带视差）、横向镜头光晕、光扫转场、三维透视图层、三维镜头的屏幕投影。"""
import math
import numpy as np, cv2
from engine import *          # noqa


# ------------------------------------------------------------------ 景深粒子：近大远小、近快远慢，焦外虚化
_dust = {}
def dust(cv, t, a=1.0, n=160, seed=1, drift=(0.0, -18.0), col=None, depth=(0.3, 1.0)):
    if a <= 0.004: return
    if seed not in _dust:
        rng = np.random.default_rng(seed)
        _dust[seed] = (rng.uniform(0, W, n), rng.uniform(0, H, n), rng.uniform(*depth, n), rng.uniform(0, 6.28, n))
    x0, y0, z, ph = _dust[seed]
    xs = (x0 + drift[0] * t * z + 14 * np.sin(t * 0.4 + ph)) % W
    ys = (y0 + drift[1] * t * z) % H
    tw = 0.55 + 0.45 * np.sin(t * 1.3 + ph * 3)
    c = GOLD_L if col is None else col
    for lo, hi, sz, blur in ((0.3, 0.6, 2, 0.0), (0.6, 0.85, 4, 1.5), (0.85, 1.01, 9, 4.0)):
        m = (z >= lo) & (z < hi)
        if not m.any(): continue
        layer = np.zeros((H // 2, W // 2), np.float32)
        for x, y, w_ in zip(xs[m] / 2, ys[m] / 2, tw[m]):
            cv2.circle(layer, (int(x), int(y)), sz, float(w_), -1, cv2.LINE_AA)
        if blur: layer = cv2.GaussianBlur(layer, (0, 0), blur)
        layer = cv2.resize(layer, (W, H))
        cv.glow += layer[..., None] * np.asarray(c, np.float32) * a * 0.35
        cv.img += layer[..., None] * np.asarray(c, np.float32) * a * 0.18


# ------------------------------------------------------------------ 横向镜头光晕（变形宽银幕镜头的拉丝光）
def flare(cv, x, y, a=1.0, length=900, col=(0.55, 0.75, 1.0), core=GOLD_L):
    if a <= 0.004: return
    h = 90; w = int(length * 2)
    xs = np.linspace(-1, 1, w, dtype=np.float32)[None, :]; ys = np.linspace(-1, 1, h, dtype=np.float32)[:, None]
    streak = np.exp(-(ys * 9) ** 2) * (1 - np.abs(xs)) ** 2.2
    cv.add(np.asarray(col, np.float32), streak * a * 0.9, x - w / 2, y - h / 2, glow=1.2)
    cv.glow_dot((x, y), 60, core, a * 0.9)
    cv.glow_dot((x, y), 18, WHITE, a)


# ------------------------------------------------------------------ 光扫转场：一道斜向亮光扫过画面
def sweep(cv, t, t0, dur=0.7, a=1.0, col=GOLD_L):
    u = (t - t0) / dur
    if not 0 <= u <= 1: return
    pos = -400 + u * (W + 800)
    yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32) * 4
    d = (xx + yy * 0.35 - pos)
    band = np.exp(-(d / 120) ** 2) * math.sin(u * math.pi) * a
    band = cv2.resize(band, (W, H))[..., None]
    cv.glow += band * np.asarray(col, np.float32) * 0.9
    cv.img += band * np.asarray(col, np.float32) * 0.35


# ------------------------------------------------------------------ 三维透视图层：把一个 Canvas 画好的内容贴到倾斜的平面上（附倒影）
def plane_warp(cv, layer, tilt=0.35, yaw=0.0, cy=900, scale=1.0, a=1.0, reflect=0.25, z=1.0):
    """layer: 另一个 Canvas（黑底，只画图表）。tilt：绕 x 轴向后倒（弧度），yaw：绕 y 轴转"""
    if a <= 0.004: return
    f = 1500.0
    pts = []
    for (x, y) in ((0, 0), (W, 0), (W, H), (0, H)):
        X = (x - W / 2) * scale; Y = (y - H / 2) * scale; Z = 0.0
        # 绕 x 轴（上远下近）
        Y2 = Y * math.cos(tilt); Z2 = Y * math.sin(tilt)
        X3 = X * math.cos(yaw) + Z2 * math.sin(yaw); Z3 = -X * math.sin(yaw) + Z2 * math.cos(yaw)
        zz = f * z + Z3
        pts.append((W / 2 + X3 * f / zz, cy + Y2 * f / zz))
    src = np.float32([(0, 0), (W, 0), (W, H), (0, H)]); dst = np.float32(pts)
    M = cv2.getPerspectiveTransform(src, dst)
    def warp(im): return cv2.warpPerspective(im, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
    img = warp(layer.img); glow = warp(layer.glow)
    U = warp(layer.U.astype(np.float32) / 255) if layer.U.any() else None
    cv.img += img * a; cv.glow += glow * a
    if U is not None: cv.img += U * a; cv.glow += U * a * 0.8
    if reflect > 0:                                          # 地面倒影：上下翻转、向下渐隐
        bottom = int(max(p[1] for p in pts))
        if bottom < H:
            src_r = (img + (U if U is not None else 0))[max(0, 2 * bottom - H):bottom][::-1]
            hh = min(src_r.shape[0], H - bottom)
            if hh > 4:
                fade = np.linspace(reflect, 0, hh, dtype=np.float32)[:, None, None]
                cv.img[bottom:bottom + hh] += src_r[:hh] * fade * a


# ------------------------------------------------------------------ 三维镜头 → 屏幕坐标（与 shaders.BARS / CUBES 的摄影机一致）
def project(P, ro, ta, fl):
    ro = np.asarray(ro, float); f = np.asarray(ta, float) - ro; f /= np.linalg.norm(f)
    r = np.cross([0, 1, 0], f); r /= np.linalg.norm(r); u = np.cross(f, r)
    d = np.asarray(P, float) - ro
    x, y, z = d @ r, d @ u, d @ f
    qx, qy = x / z * fl, y / z * fl
    asp = W / H
    return (qx / (2 * asp) + 0.5) * W, (1 - (qy / 2 + 0.5)) * H


def layer_over(cv, rgba, a=1.0, glow_k=0.6):
    """三维着色器输出（RGBA）叠到画面，亮部进辉光"""
    al = rgba[..., 3:4] * a
    cv.img = cv.img * (1 - al) + rgba[..., :3] * a
    cv.glow += np.clip(rgba[..., :3] * a - 0.6, 0, None) * glow_k


# ------------------------------------------------------------------ 三维金属柱对比（两根柱子，摄影机缓慢环绕，数值标在柱顶）
_bs = {}
def bars3d(cv, t, t0, t1, left, right, a=1.0, title=None, sub=None, right_red=False, hmax=1.65, cam0=-0.55, cam1=-0.2):
    """left/right = (标签, 数值, 显示文本, 出现时刻)；左柱金色，右柱金色或红色"""
    if a <= 0.004: return
    import shaders
    if 'B' not in _bs: _bs['B'] = Shader(shaders.BARS)
    vmax = max(left[1], right[1])
    kl = eexp((t - left[3]) / 1.3); kr = eexp((t - right[3]) / 1.3)
    hl = max(hmax * left[1] / vmax * kl, 0.001); hr = max(hmax * right[1] / vmax * kr, 0.001)
    p = cl((t - t0) / max(t1 - t0, 1e-3))
    cam = lerp(cam0, cam1, eio(p)); camr = lerp(10.8, 9.2, eio(p))
    img = _bs['B'](t=t, cam=cam, camr=camr, h1=hl, h2=hr, ex=1.0, glow2=0.0, redk=1.0 if right_red else 0.0)
    layer_over(cv, img, a)
    ro = (math.sin(cam) * camr, 2.0, math.cos(cam) * camr); ta = (0, 1.45, 0)
    for (lab, v, txt, ts), x3, h, col in ((left, 0.85, hl, None), (right, -0.85, hr, (1.0, 0.45, 0.4) if right_red else None)):
        k = eo((t - ts - 0.6) / 0.5)
        if k <= 0: continue
        x, y = project((x3, 2 * h + 0.32, 0), ro, ta, 2.4)
        if col is None: cv.text(txt, x, y, 64, 'sans_bold', gold=True, a=a * k, glow=0.3, shadow=0.8)
        else: cv.text(txt, x, y, 64, 'sans_bold', col=col, a=a * k, glow=0.3, shadow=0.8)
        xb, yb = project((x3, -0.05, 0.6), ro, ta, 2.4)
        cv.text(lab, xb, yb + 40, 30, 'sans_med', col=CREAM, a=a * min(1, (t - ts) / 0.5 if t > ts else 0), shadow=0.8)
    if title: cv.text(title, W / 2, 330, 42, 'sans_med', col=CREAM, a=a, shadow=0.8)
    if sub: cv.text(sub, W / 2, 395, 26, 'sans_light', col=GREY, a=a, shadow=0.8)
