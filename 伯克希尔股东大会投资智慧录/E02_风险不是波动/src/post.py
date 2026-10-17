"""玻璃三维场景的后期：景深（按深度）→ 泛光 / 横向光晕（HDR）→ ACES 色调映射 → 冷色调分级 → 暗角与颗粒。
输入为 glass.Renderer 输出的线性 HDR（float32 HxWx4，A 为相机距离），输出 sRGB 显示空间 float32 RGB（0..1）。
"""
import numpy as np, cv2


def dof(rgb, depth, focus, aperture, max_r=14.0):
    """按弥散圈半径在 4 档模糊之间插值（近似景深）。aperture 越大越虚；focus 为对焦距离。"""
    if aperture <= 0: return rgb
    coc = np.clip(aperture * np.abs(1.0 / np.maximum(depth, 0.05) - 1.0 / focus) * rgb.shape[0] / 1920, 0, max_r)
    levels = [rgb]
    for r in (2.0, 5.0, 10.0, 16.0):
        k = int(r * 2) * 2 + 1
        levels.append(cv2.GaussianBlur(rgb, (k, k), r * 0.5))
    rs = np.array([0.0, 2.0, 5.0, 10.0, 16.0], np.float32)
    # 背景的弥散圈也要扩散到前景边缘之外：对 coc 本身做一次小模糊，避免硬边
    coc = cv2.GaussianBlur(coc, (0, 0), 3)
    i = np.clip(np.searchsorted(rs, coc) - 1, 0, 3)
    f = np.clip((coc - rs[i]) / (rs[i + 1] - rs[i]), 0, 1)[..., None]
    out = np.zeros_like(rgb)
    for k in range(4):
        m = (i == k)[..., None]
        out += np.where(m, levels[k] * (1 - f) + levels[k + 1] * f, 0)
    return out


def bloom(rgb, strength=0.22, thr=0.9, streak=0.10, streak_tint=(0.55, 0.75, 1.0)):
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    knee = np.clip((lum - thr) / (thr + 1e-6), 0, None)[..., None]
    hi = rgb * knee / (1 + knee)
    h, w = rgb.shape[:2]
    small = cv2.resize(hi, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    acc = np.zeros_like(small)
    for s, wgt in ((2, 0.5), (6, 0.3), (16, 0.2)):
        acc += cv2.GaussianBlur(small, (0, 0), s) * wgt
    out = rgb + cv2.resize(acc, (w, h), interpolation=cv2.INTER_LINEAR) * strength * 4
    if streak > 0:
        st = cv2.resize(hi, (w // 8, h // 8), interpolation=cv2.INTER_AREA)
        st = cv2.GaussianBlur(st, (0, 0), sigmaX=24, sigmaY=0.6)
        out += cv2.resize(st, (w, h), interpolation=cv2.INTER_LINEAR) * np.array(streak_tint, np.float32) * streak * 6
    return out


def aces(x):
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    return np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)


LIFT = np.array([0.006, 0.010, 0.020], np.float32)     # 暗部微微偏深蓝


def grade(rgb, exposure=1.0, sat=1.0):
    x = aces(rgb * exposure)
    x = np.power(x, 1 / 2.2)
    if sat != 1.0:
        g = x @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        x = g[..., None] + (x - g[..., None]) * sat
    return np.clip(x + LIFT * (1 - x), 0, 1)


def vignette(img, k=0.35):
    h, w = img.shape[:2]
    y, x = np.ogrid[:h, :w]
    r = np.sqrt(((x - w / 2) / (w / 2)) ** 2 * 0.7 + ((y - h / 2) / (h / 2)) ** 2)
    return img * (1 - k * np.clip(r - 0.35, 0, 1) ** 1.6)[..., None].astype(np.float32)


def grain(img, seed, amt=0.012):
    rng = np.random.default_rng(seed)
    h, w = img.shape[:2]
    n = rng.standard_normal((h // 2, w // 2)).astype(np.float32)
    n = cv2.resize(n, (w, h), interpolation=cv2.INTER_LINEAR)
    return np.clip(img + n[..., None] * amt * (0.4 + 0.6 * (1 - img)), 0, 1)


def finish(hdr, frame_idx, exposure=1.0, focus=None, aperture=0.0, bloom_k=0.22, streak=0.10, ss=1.0, out_hw=(1920, 1080)):
    """hdr: 渲染器输出（可能是超采样尺寸）。返回 out_hw 尺寸的显示空间图像。"""
    rgb = np.nan_to_num(hdr[..., :3], nan=0.0, posinf=50.0, neginf=0.0)
    rgb = np.minimum(rgb, 60.0)
    depth = hdr[..., 3]
    if ss != 1.0:
        rgb = cv2.resize(rgb, (out_hw[1], out_hw[0]), interpolation=cv2.INTER_AREA)
        depth = cv2.resize(depth, (out_hw[1], out_hw[0]), interpolation=cv2.INTER_NEAREST)
    if focus is not None and aperture > 0:
        rgb = dof(rgb, depth, focus, aperture)
    rgb = bloom(rgb, bloom_k, streak=streak)
    x = grade(rgb, exposure)
    x = vignette(x)
    return grain(x, frame_idx)
