"""配乐合成：Lyria 生成的电影配乐 + 自行合成的低频音效层（重拍冲击、低频下潜、心跳脉冲、音调上升）。

不使用任何白噪声 / 高频 whoosh：所有音效都由正弦、扫频和低通后的谐波构成。
用法: python3 audio.py <music.mp3> <out.wav>   （事件时间表来自 timeline.py）
"""
import sys, os
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _t(d):
    return np.arange(int(d * SR)) / SR


def lowpass(x, fc, order=4):
    return sosfilt(butter(order, fc, 'low', fs=SR, output='sos'), x)


def highpass(x, fc, order=2):
    return sosfilt(butter(order, fc, 'high', fs=SR, output='sos'), x)


def sweep(f0, f1, d, curve=3.0):
    """指数下滑扫频正弦（相位连续）"""
    t = _t(d)
    f = f1 + (f0 - f1) * np.exp(-curve * t / d)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def boom(strength=1.0, d=2.6):
    """电影级低频冲击：110→38 Hz 扫频主体 + 55 Hz 尾音 + 轻微饱和"""
    t = _t(d)
    body = sweep(120, 38, d, 4.0) * np.exp(-t / 0.9)
    tail = np.sin(2 * np.pi * 41 * t) * np.exp(-t / 1.6) * 0.5 * (1 - np.exp(-t / 0.05))
    punch = sweep(260, 60, 0.12, 6) * np.exp(-_t(0.12) / 0.03)
    x = body + tail
    x[:len(punch)] += punch * 0.6
    x = np.tanh(x * 1.6) / 1.2
    return x * strength


def subdrop(d=1.8, f0=95, f1=26, strength=1.0):
    t = _t(d)
    x = sweep(f0, f1, d, 2.2) * (1 - np.exp(-t / 0.04)) * np.exp(-t / (d * 0.6))
    return np.tanh(x * 1.4) * strength


def pulse(strength=1.0):
    """心跳 lub-dub：两个 50~60Hz 短促低音"""
    a = sweep(75, 45, 0.25, 5) * np.exp(-_t(0.25) / 0.07)
    b = sweep(65, 40, 0.3, 5) * np.exp(-_t(0.3) / 0.09)
    x = np.zeros(int(0.6 * SR)); x[:len(a)] += a; o = int(0.22 * SR); x[o:o + len(b)] += b * 0.75
    return x * strength


def braam(d=3.0, root=36.71, strength=1.0):
    """低音铜管感和弦（D1/A1/D2/F2），带限谐波叠加 + 滤波包络"""
    t = _t(d)
    out = np.zeros_like(t)
    for ratio, g in [(1, 1.0), (1.5, 0.6), (2, 0.7), (2.378, 0.45), (3, 0.3)]:
        f = root * ratio
        for det in (-0.25, 0, 0.25):
            ff = f * (1 + det / 100)
            for h in range(1, 14):          # 带限锯齿（谐波不超过 ~1.2kHz，听感厚而不刺）
                if ff * h > 1200: break
                out += g * np.sin(2 * np.pi * ff * h * t + h) / h * 0.33
    envl = (1 - np.exp(-t / 0.03)) * np.exp(-t / (d * 0.45))
    x = lowpass(out * envl, 900)
    return np.tanh(x * 0.9) * strength


def riser(d=3.0, strength=0.6):
    """音调上升（不用噪声）：低音五度叠加，音高缓升 + 逐渐打开的低通"""
    t = _t(d)
    f = 55 * 2 ** (t / d * 1.0)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = sum(np.sin(ph * h) / h for h in range(1, 9)) + 0.6 * sum(np.sin(ph * 1.5 * h) / h for h in range(1, 6))
    x = x * (t / d) ** 2.2
    x = lowpass(x, 700)
    return x / (np.abs(x).max() + 1e-9) * strength


def tick(strength=0.25):
    """低沉木质滴答（约 420Hz，非高频）"""
    t = _t(0.12)
    return (np.sin(2 * np.pi * 420 * t) + 0.4 * np.sin(2 * np.pi * 630 * t)) * np.exp(-t / 0.018) * strength


def reverb_ir(d=2.4):
    rng = np.random.default_rng(3)
    t = _t(d)
    ir = rng.normal(0, 1, len(t)) * np.exp(-t / 0.55)
    ir = lowpass(ir, 2500)
    ir[0] = 1.0
    return ir / np.abs(ir).sum() * 40


SOUNDS = dict(boom=boom, subdrop=subdrop, pulse=pulse, braam=braam, riser=riser, tick=tick)


def edit_music(y, segments, xf=0.06):
    """按 [(原曲起点, 原曲终点), ...] 拼接原曲片段，接缝处做等功率交叉淡化"""
    out = None
    nx = int(xf * SR)
    for a, b in segments:
        seg = y[int(a * SR):int(b * SR)].copy()
        if out is None:
            out = seg; continue
        t = np.linspace(0, 1, nx)[:, None]
        mixz = out[-nx:] * np.cos(t * np.pi / 2) + seg[:nx] * np.sin(t * np.pi / 2)
        out = np.concatenate([out[:-nx], mixz, seg[nx:]])
    return out


def render(music_path, out_path, events, T, music_gain=1.0, segments=None):
    import librosa
    y, sr = librosa.load(music_path, sr=SR, mono=False)
    if y.ndim == 1:
        y = np.stack([y, y])
    y = y.T * music_gain
    if segments:
        y = edit_music(y, segments)
    n = int(T * SR)
    mus = np.zeros((n, 2))
    m = min(n, len(y))
    mus[:m] = y[:m]
    fi = int(0.12 * SR); mus[:fi] *= np.linspace(0, 1, fi)[:, None]      # 剪掉铺垫后，开头 0.12 s 渐入
    fx = np.zeros(n)
    duck = np.ones(n)
    for ev in events:
        t0, kind = ev[0], ev[1]
        kw = ev[2] if len(ev) > 2 else {}
        x = SOUNDS[kind](**kw)
        a = int(t0 * SR)
        if kind == 'riser':
            a -= len(x)     # 上升音在 t0 处结束
        a0, b0 = max(a, 0), min(a + len(x), n)
        if b0 <= a0: continue
        fx[a0:b0] += x[a0 - a:b0 - a]
        if kind in ('boom', 'braam', 'subdrop'):
            dl = int(0.9 * SR); dd = 1 - 0.35 * kw.get('strength', 1.0) * np.exp(-np.arange(dl) / (0.35 * SR))
            e = min(a0 + dl, n); duck[a0:e] = np.minimum(duck[a0:e], dd[:e - a0])
    wet = fftconvolve(fx, reverb_ir())[:n] * 0.18
    fxs = np.stack([fx + wet * 0.9, fx + np.roll(wet, 331) * 0.9], 1)
    out = mus * duck[:, None] + fxs * 0.55
    # 全片淡入淡出
    fo = int(3.5 * SR); out[-fo:] *= (np.linspace(1, 0, fo) ** 1.6)[:, None]
    # 软限幅 + 归一化到 -1 dBFS
    out = highpass(out.T, 22).T
    peak = np.abs(out).max()
    out = np.tanh(out / peak * 1.25) / np.tanh(1.25) * 0.89
    sf.write(out_path, out.astype(np.float32), SR)
    return out


if __name__ == '__main__':
    from timeline import AUDIO_EVENTS, T_TOTAL, MUSIC_EDIT
    render(sys.argv[1], sys.argv[2], AUDIO_EVENTS, T_TOTAL, segments=MUSIC_EDIT)
    print('wrote', sys.argv[2])
