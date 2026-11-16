"""合成音效与滤波工具（取自第 04 集 src/music_v.py，代码合成，不用外部素材）。"""
import os, sys
import numpy as np, librosa

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from shots import SHOTS

SR = 44100
rng = np.random.default_rng(11)


def chapters():
    ch, cur = [], ""
    for s in SHOTS:
        cur = s.get("ch") or cur
        ch.append(cur)
    return ch

# ---------------------------------------------------------------- 合成音效
def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR)).astype(np.float32)


def lp_noise(n, cutoff):
    x = rng.standard_normal(n).astype(np.float32)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, n).astype(np.float32) / 3


def bp_sweep_noise(n, f0, f1, q=0.6):
    """时变带通噪声（STFT 掩膜）"""
    x = rng.standard_normal(n + 2048).astype(np.float32)
    S = librosa.stft(x, n_fft=2048, hop_length=512)
    fr = librosa.fft_frequencies(sr=SR, n_fft=2048)[:, None]
    m = S.shape[1]
    fc = np.geomspace(f0, f1, m)[None, :]
    S *= np.exp(-0.5 * (np.log(fr / fc + 1e-9) / q) ** 2)
    y = librosa.istft(S, hop_length=512, length=n + 2048)[:n]
    return (y / (np.abs(y).max() + 1e-9)).astype(np.float32)


def impact(strength=1.0):
    n = int(2.4 * SR)
    t = np.arange(n) / SR
    f = 42 + 90 * np.exp(-t * 9)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.4)
    crack = lp_noise(n, 5000) * np.exp(-t * 28) * 1.2
    tail = lp_noise(n, 1800) * np.exp(-t * 2.2) * 0.35
    y = (boom * 1.0 + crack + tail) * strength
    return np.stack([y, y], 1).astype(np.float32)


def riser(dur):
    n = int(dur * SR)
    x = np.arange(n) / n
    nz = bp_sweep_noise(n, 400, 9000, 0.5) * x ** 2.2
    f = 180 + 1400 * x ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.18 * x ** 3
    y = (nz * 0.55 + tone)
    return np.stack([y * (0.9 + 0.1 * np.sin(x * 40)), y * (0.9 - 0.1 * np.sin(x * 40))], 1).astype(np.float32)


def whoosh(pan):
    n = int(0.55 * SR)
    x = np.arange(n) / n
    y = bp_sweep_noise(n, 3000, 500, 0.7) * np.sin(np.pi * x) ** 2
    l, r = (1 - pan) / 2 + 0.25, (1 + pan) / 2 + 0.25
    return np.stack([y * l, y * r], 1).astype(np.float32)


def glitch():
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    sq = np.sign(np.sin(2 * np.pi * 1300 * t)) * 0.25
    nz = rng.standard_normal(n) * 0.35
    gate = (np.floor(t * 70) % 2).astype(np.float32)
    y = (sq + nz) * gate * np.exp(-t * 12)
    y = np.round(y * 6) / 6
    return np.stack([y, -y * 0.8], 1).astype(np.float32)


def stamp():
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    thud = np.sin(2 * np.pi * (70 + 60 * np.exp(-t * 30)) * t) * np.exp(-t * 7)
    slap = lp_noise(n, 3500) * np.exp(-t * 60) * 1.4
    y = thud + slap
    return np.stack([y, y], 1).astype(np.float32)


def shimmer():
    n = int(3.2 * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for f, a in [(1568, .5), (2349, .4), (3136, .35), (4699, .25), (6272, .18), (2093, .3)]:
        y += a * np.sin(2 * np.pi * f * t + rng.random() * 6) * np.exp(-t * (1.2 + f / 6000))
    y += bp_sweep_noise(n, 2500, 12000, 0.4) * np.exp(-t * 2.5) * 0.25
    y *= np.minimum(1, t / 0.01)
    return np.stack([y * 0.9, y], 1).astype(np.float32) * 0.6


def reverse_swell(dur):
    n = int(dur * SR)
    tail = lp_noise(n, 2500)
    x = np.arange(n) / n
    y = tail * x ** 3
    return np.stack([y, y], 1).astype(np.float32)


def place(buf, clip, t, gain):
    i = int(t * SR)
    if i < 0:
        clip, i = clip[-i:], 0
    j = min(len(buf), i + len(clip))
    if j > i:
        buf[i:j] += clip[:j - i] * gain


# ---------------------------------------------------------------- 滤波递进
def lowpass_auto(y, cutoff_at):
    out = np.zeros_like(y)
    fr = librosa.fft_frequencies(sr=SR, n_fft=4096)[:, None]
    for c in range(2):
        S = librosa.stft(y[:, c], n_fft=4096, hop_length=1024)
        tt = librosa.frames_to_time(np.arange(S.shape[1]), sr=SR, hop_length=1024)
        fc = np.array([cutoff_at(t) for t in tt])[None, :]
        S *= 1 / np.sqrt(1 + (fr / fc) ** 6)
        out[:, c] = librosa.istft(S, hop_length=1024, length=len(y))
    return out


