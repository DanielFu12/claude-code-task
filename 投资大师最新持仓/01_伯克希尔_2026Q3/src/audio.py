"""背景音乐剪辑 + 低频转场音效（全部本地合成，低沉、有质感，不用刺耳高频）

用法：python3 audio.py <work_dir>    需要 <work_dir>/src.wav（源曲，44.1 kHz 立体声）
输出：<work_dir>/mix.wav
"""
import sys, os
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import *

WK = sys.argv[1]
y, sr = sf.read(os.path.join(WK, 'src.wav'))
if y.ndim == 1: y = np.stack([y, y], 1)

# ------------------------------------------------------------ 1) 节拍对齐剪辑（等功率交叉淡化 60 ms）
a, bb = int(SRC_BEATS[CUT_A] * sr), int(SRC_BEATS[CUT_B] * sr)
xf = int(0.06 * sr)
head = y[:a + xf // 2]
tail = y[bb - xf // 2:]
w = np.linspace(0, 1, xf)[:, None]
mid = head[-xf:] * np.cos(w * np.pi / 2) + tail[:xf] * np.sin(w * np.pi / 2)
music = np.concatenate([head[:-xf], mid, tail[xf:]])
N = int(DUR * sr)
music = music[:N] if len(music) >= N else np.concatenate([music, np.zeros((N - len(music), 2))])
fo = int(2.6 * sr); music[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.6
fi = int(0.25 * sr); music[:fi] *= np.linspace(0, 1, fi)[:, None]

# ------------------------------------------------------------ 2) 音效合成
rng = np.random.default_rng(7)
sfx = np.zeros((N, 2))

def lp(x, f, o=4): return sosfilt(butter(o, f, 'low', fs=sr, output='sos'), x, axis=0)
def bp(x, f0, f1, o=2): return sosfilt(butter(o, [f0, f1], 'band', fs=sr, output='sos'), x, axis=0)

def put(t, sig, gain=1.0):
    i = int(t * sr)
    if sig.ndim == 1: sig = np.stack([sig, sig], 1)
    j0, j1 = max(i, 0), min(i + len(sig), N)
    if j1 > j0: sfx[j0:j1] += sig[j0 - i:j1 - i] * gain

def sub_boom(dur=3.2, f0=62, f1=31, drive=1.6):
    """深沉低频冲击：下滑正弦 + 软饱和 + 低通噪声体"""
    n = int(dur * sr); t = np.arange(n) / sr
    f = f1 + (f0 - f1) * np.exp(-t / 0.35)
    ph = 2 * np.pi * np.cumsum(f) / sr
    s = np.sin(ph) * np.exp(-t / 1.1)
    s = np.tanh(s * drive) / np.tanh(drive)
    body = lp(rng.standard_normal(n), 220) * np.exp(-t / 0.25) * 0.5
    att = np.minimum(t / 0.004, 1)
    return (s + body) * att

def thud(dur=1.0, f0=95, f1=48):
    n = int(dur * sr); t = np.arange(n) / sr
    f = f1 + (f0 - f1) * np.exp(-t / 0.06)
    s = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t / 0.28)
    s += lp(rng.standard_normal(n), 400) * np.exp(-t / 0.05) * 0.35
    return s * np.minimum(t / 0.003, 1)

def whoosh(dur=1.1, peak=0.75, f_lo=90, f_hi=900):
    """低沉气流声：棕噪声经动态低通，频率先升后降，左右轻微移动"""
    n = int(dur * sr); t = np.arange(n) / sr
    nz = np.cumsum(rng.standard_normal((n, 2)), 0); nz -= lp(nz, 20)       # 棕噪声，去直流漂移
    nz /= np.abs(nz).max() + 1e-9
    e = np.where(t < peak, (t / peak) ** 2.2, np.exp(-(t - peak) / 0.18))
    # 分 4 段近似滑动低通
    out = np.zeros_like(nz)
    cut = f_lo + (f_hi - f_lo) * e
    for k in range(4):
        lo = f_lo + (f_hi - f_lo) * k / 4; hi = f_lo + (f_hi - f_lo) * (k + 1) / 4
        wgt = np.clip((cut - lo) / (hi - lo), 0, 1)[:, None]
        out += bp(nz, max(lo, 30), hi) * wgt
    pan = 0.5 + 0.35 * np.sin(np.pi * t / dur)
    out[:, 0] *= 1.2 - pan; out[:, 1] *= 0.2 + pan
    return out * e[:, None]

def riser(dur):
    """低频上行蓄力：噪声带通从 60 Hz 升到 1.4 kHz + 低沉嗡鸣上滑"""
    n = int(dur * sr); t = np.arange(n) / sr; u = t / dur
    nz = rng.standard_normal((n, 2))
    out = np.zeros_like(nz)
    for k in range(6):
        c = 60 * (1400 / 60) ** (k / 5)
        wgt = np.exp(-((u * 5 - k) ** 2) / 1.2)[:, None]
        out += bp(nz, c * 0.7, c * 1.3) * wgt
    f = 40 + 60 * u ** 2
    drone = np.sin(2 * np.pi * np.cumsum(f) / sr) * 0.6 + np.sin(2 * np.pi * np.cumsum(f * 1.5) / sr) * 0.25
    return (out * 0.8 + drone[:, None]) * (u ** 2.4)[:, None]

def gong(dur=5.0):
    """片尾低频金属余韵（非谐泛音、全部在 500 Hz 以下）"""
    n = int(dur * sr); t = np.arange(n) / sr
    s = sum(a * np.sin(2 * np.pi * f * t + p) * np.exp(-t / d)
            for f, a, d, p in [(55, 1.0, 2.2, 0), (82.4, .6, 1.8, 1), (110.3, .45, 1.5, 2), (164.9, .25, 1.1, .5),
                               (233.1, .14, .8, 1.3), (311.0, .08, .6, .2)])
    return s * np.minimum(t / 0.01, 1)

def counter_ticks(t0, t1, n):
    """计数器滚动时的极轻低频「咔嗒」（木质感，~180 Hz）"""
    for k in range(n):
        tt = t0 + (t1 - t0) * (k / max(n - 1, 1)) ** 0.6
        m = int(0.05 * sr); x = np.arange(m) / sr
        put(tt, np.sin(2 * np.pi * 180 * x) * np.exp(-x / 0.012), 0.05)

# 冷开场：低频嗡鸣淡入
n = int(7.5 * sr); t = np.arange(n) / sr
drone = (np.sin(2 * np.pi * 41.2 * t) + 0.4 * np.sin(2 * np.pi * 61.8 * t + 1)) * np.minimum(t / 2.5, 1) * np.exp(-np.maximum(t - 4.5, 0) / 1.2)
put(0.0, drone, 0.16)
counter_ticks(0.9, 5.2, 22)

for t0, t1 in RISERS:
    put(t0, riser(t1 - t0), 0.20)
for ti, k in IMPACTS:
    put(ti, sub_boom(3.4 if k >= 1 else 2.2), 0.55 * k)
    put(ti - 0.6, whoosh(1.2, 0.6), 0.25 * k)
for tc in CUTS:
    put(tc - 0.62, whoosh(1.1, 0.62), 0.22)
    put(tc, thud(), 0.22)
# 四个数字逐一亮起（S3）与信号卡片：轻闷响
for i in (20, 22, 24, 26):
    put(b(i), thud(0.6, 80, 45), 0.14)
put(T_END, gong(), 0.28)

# 音效总线：整体再低通一次，保证不刺耳
sfx = lp(sfx, 2200, 2)

# ------------------------------------------------------------ 3) 混音：重拍处给音乐轻微侧链闪避
duck = np.ones(N)
for ti, k in IMPACTS:
    i = int(ti * sr); m = int(0.5 * sr)
    if i < N:
        e = 1 - 0.25 * k * np.exp(-np.arange(min(m, N - i)) / sr / 0.15)
        duck[i:i + len(e)] *= e
mix = music * duck[:, None] * 0.92 + sfx
peak = np.abs(mix).max()
mix = np.tanh(mix / peak * 1.15) / np.tanh(1.15) * 0.93      # 软限幅
sf.write(os.path.join(WK, 'mix.wav'), mix.astype(np.float32), sr, subtype='FLOAT')
print('mix', len(mix) / sr, 's  peak', peak)
