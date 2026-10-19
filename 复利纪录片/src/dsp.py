"""音频小工具：滤波、语音电平拉平、本地合成的低频音效（能量集中在 200Hz 以下）。"""
import numpy as np
from scipy.signal import butter, sosfiltfilt

SR = 48000


def lp(x, f, order=4): return sosfiltfilt(butter(order, f, 'low', fs=SR, output='sos'), x, axis=-1)


def hp(x, f, order=2): return sosfiltfilt(butter(order, f, 'high', fs=SR, output='sos'), x, axis=-1)


def high_shelf_soften(x, f=5500, cut_db=-4.0):
    """温和削减高频（避免尖锐）：x - (1-g)·HP(x)"""
    g = 10 ** (cut_db / 20)
    return x - (1 - g) * hp(x, f, 2)


def env_exp(n, tau): return np.exp(-np.arange(n) / (tau * SR)).astype(np.float32)


def sub_drop(dur=2.6, f0=62, f1=27, amp=0.9):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-tt / (dur * 0.28))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * env_exp(n, dur * 0.42) * np.minimum(tt / 0.008, 1)
    y = np.tanh(y * 1.6) / np.tanh(1.6)
    return (y * amp).astype(np.float32)


def boom(dur=3.0, cut=110, amp=0.8, seed=0):
    """低通滤波的低频轰鸣（截止 110Hz，听感是深沉的隆隆声，而不是白噪声）"""
    n = int(dur * SR)
    r = np.random.default_rng(seed).normal(0, 1, n).astype(np.float32)
    y = lp(lp(r, cut, 4), cut, 4)
    y = y / (np.abs(y).max() + 1e-9)
    y = y * env_exp(n, dur * 0.3) * np.minimum(np.arange(n) / (0.015 * SR), 1)
    thump = sub_drop(min(dur, 1.4), 70, 38, 1.0)
    y[:len(thump)] += thump * 0.8
    return (y / (np.abs(y).max() + 1e-9) * amp).astype(np.float32)


def thump(amp=0.5, f0=85, f1=42, dur=0.55):
    return sub_drop(dur, f0, f1, amp)


def swell(dur=3.0, f=41, amp=0.35):
    """低频脉冲式涨落（用于推进与「回到原点」）"""
    n = int(dur * SR); tt = np.arange(n) / SR
    e = np.sin(np.pi * tt / dur) ** 2
    y = np.sin(2 * np.pi * f * tt) * e * (0.7 + 0.3 * np.sin(2 * np.pi * 1.5 * tt))
    return (y * amp).astype(np.float32)


def movavg(x, k):
    """居中滑动平均（累加和实现，O(N)）"""
    c = np.concatenate([[0.0], np.cumsum(x, dtype=np.float64)])
    i = np.arange(len(x)); a = np.clip(i - k // 2, 0, len(x)); b = np.clip(i + k - k // 2, 0, len(x))
    return ((c[b] - c[a]) / np.maximum(b - a, 1)).astype(np.float32)


def level(s, win=0.4, amount=0.6, lim_db=8.0):
    """慢速语音电平拉平：按 0.4s 短时 RMS 把弱句子抬起来、强句子压一点（不是快速压缩，不会喘）"""
    rms = np.sqrt(movavg(s ** 2, int(win * SR)) + 1e-10)
    ref = np.sqrt(np.mean(s[rms > np.percentile(rms, 40)] ** 2) + 1e-10)
    g = np.clip((ref / rms) ** amount, 10 ** (-lim_db / 20), 10 ** (lim_db / 20))
    g[rms < ref * 0.06] = 1.0                        # 停顿处不抬底噪
    g = movavg(g, int(0.25 * SR))
    return (s * g).astype(np.float32)
