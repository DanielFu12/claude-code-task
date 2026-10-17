"""“流光诗意纪录片”后期：柔和泛光（雾而不是烧）、胶片感色调曲线、深底抬升到炭灰蓝、2% 颗粒、轻暗角。"""
import numpy as np, cv2

BASE = np.array([0x18, 0x19, 0x22], np.float32) / 255.0     # 实测中位背景色 #181922


def bloom(x, strength=0.7, thr=0.35):
    h, w = x.shape[:2]
    lum = x.max(2)
    hi = x * np.clip((lum - thr) / (1.0 - thr + 1e-6), 0, 1)[..., None]
    s = cv2.resize(hi, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    acc = cv2.GaussianBlur(s, (0, 0), 4) * 0.45 + cv2.GaussianBlur(s, (0, 0), 14) * 0.35 + cv2.GaussianBlur(s, (0, 0), 36) * 0.2
    return x + cv2.resize(acc, (w, h), interpolation=cv2.INTER_LINEAR) * strength


def filmic(x, exposure=1.0):
    x = np.maximum(x * exposure, 0)
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    y = np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)
    return np.power(y, 1 / 2.2)


_VIG = {}


def vignette(h, w, k=0.28):
    if (h, w) not in _VIG:
        y, x = np.ogrid[:h, :w]
        r = np.sqrt(((x - w / 2) / (w / 2)) ** 2 * 0.75 + ((y - h * 0.48) / (h / 2)) ** 2)
        _VIG[(h, w)] = (1 - k * np.clip(r - 0.4, 0, 1) ** 1.5)[..., None].astype(np.float32)
    return _VIG[(h, w)]


def grain(x, seed, amt=0.02):
    rng = np.random.default_rng(seed)
    h, w = x.shape[:2]
    n = cv2.resize(rng.standard_normal((h // 2, w // 2)).astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    return x + n[..., None] * amt * 0.5


def finish(lin, seed, exposure=1.0, bloom_k=0.7, lift=1.0):
    """lin：线性 HDR（1080×1920×3）。返回显示空间 0..1。"""
    x = bloom(lin, bloom_k)
    x = filmic(x, exposure)
    x = x + BASE * lift * (1 - x)            # 暗部抬到炭灰蓝（不是纯黑）
    x = x * vignette(*x.shape[:2])
    return np.clip(grain(x, seed), 0, 1)
