"""混音：旁白按时间线摆放 → 轻处理（高通、轻压缩、小房间混响、底噪）→ 配乐闪避 → −14 LUFS + 峰值限制。
python3 src/mix.py WORK → WORK/mix.wav
"""
import os, sys, json
import numpy as np, soundfile as sf, pyloudnorm as pyln
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import TL

WORK = sys.argv[1]; tl = TL(WORK); SR = 48000; N = int(tl.total * SR)
vo = np.zeros(N)
for s in tl.d['segs']:
    y, sr = sf.read(os.path.join(WORK, 'vo', s['id'] + '.wav')); assert sr == SR
    i = int(s['start'] * SR); j = min(N, i + len(y)); vo[i:j] += y[:j - i]


def sos(kind, f, o=2): return butter(o, f, kind, fs=SR, output='sos')


vo = sosfilt(sos('high', 70), vo)
# 轻压缩 2.2:1（RMS 检测，起 8ms / 放 120ms）
env = np.sqrt(np.convolve(vo ** 2, np.ones(480) / 480, 'same') + 1e-12)
db = 20 * np.log10(env); thr = -22.0
gr = np.where(db > thr, (db - thr) * (1 - 1 / 2.2), 0.0)
a_att, a_rel = np.exp(-1 / (0.008 * SR)), np.exp(-1 / (0.12 * SR)); g = np.zeros_like(gr); cur = 0.0
for i in range(0, len(gr), 48):  # 每 1ms 更新
    x = gr[i]; cur = x + (cur - x) * (a_att ** 48 if x > cur else a_rel ** 48); g[i:i + 48] = cur
vo = vo * 10 ** (-g / 20)
# 小房间混响（RT60≈0.5s，湿 8%）
rng = np.random.default_rng(1); n = int(0.6 * SR); tt = np.arange(n) / SR
ir = rng.standard_normal(n) * np.exp(-tt * 6.9 / 0.5); ir = sosfilt(sos('low', 5000), ir); ir[:int(0.006 * SR)] = 0; ir /= np.sqrt((ir ** 2).sum())
vo = vo + 0.08 * fftconvolve(vo, ir)[:N]
vo += sosfilt(sos('low', 3000), rng.standard_normal(N)) * 10 ** (-66 / 20)
meter = pyln.Meter(SR)
vo *= 10 ** ((-17.0 - meter.integrated_loudness(vo)) / 20)

mus, sr = sf.read(os.path.join(WORK, 'music.wav')); assert sr == SR
mus = mus[:N] if len(mus) >= N else np.pad(mus, ((0, N - len(mus)), (0, 0)))
# 闪避：旁白有声处 −11 dB；提前 0.15s，保持 0.9s，起 80ms 放 550ms
act = (np.convolve(np.abs(vo), np.ones(960) / 960, 'same') > 10 ** (-45 / 20)).astype(float)
hold = int(0.9 * SR); look = int(0.15 * SR)
idx = np.flatnonzero(act)
act2 = np.zeros(N)
if len(idx):
    # 区间扩展：前移 look、后延 hold
    starts = idx[np.r_[True, np.diff(idx) > 1]]; ends = idx[np.r_[np.diff(idx) > 1, True]]
    for s0, e0 in zip(starts, ends): act2[max(0, s0 - look):min(N, e0 + hold)] = 1
duck = np.zeros(N); cur = 0.0
aa, ar = np.exp(-1 / (0.08 * SR / 48)), np.exp(-1 / (0.55 * SR / 48))
for i in range(0, N, 48):
    x = act2[i]; cur = x + (cur - x) * (aa if x > cur else ar); duck[i:i + 48] = cur
mus = mus * (10 ** (-11 * duck / 20))[:, None]
# 片尾品牌动画的重拍不要比旁白响：logo 落定前 0.5 秒起配乐整体 −3.5 dB（0.8 秒内平滑过渡）
HT = json.load(open(os.path.join(WORK, 'hits.json')))
if 'logo_land' in HT:
    tt = np.arange(N) / SR; k = np.clip((tt - (HT['logo_land'] - 0.5)) / 0.8, 0, 1)
    mus = mus * (10 ** (-3.5 * k / 20))[:, None]
mix = mus * 0.9 + vo[:, None]
L = meter.integrated_loudness(mix); mix *= 10 ** ((-14.0 - L) / 20)
# 峰值限制：逐样本所需增益 → 5ms 最小值滤波 → 平滑（真峰按 4 倍过采样估计，目标 −1.2 dBTP）
from scipy.ndimage import minimum_filter1d
lim = 10 ** (-1.2 / 20)
for _ in range(3):
    up = resample_poly(mix, 4, 1, axis=0); pk = np.abs(up).reshape(-1, 4, 2).max((1, 2))[:N]
    if pk.max() <= lim: break
    g = np.minimum(1, lim / np.maximum(pk, 1e-9)) ** 1.05
    g = minimum_filter1d(g, 240); g = np.convolve(g, np.ones(240) / 240, 'same')
    mix *= np.minimum(g, 1)[:, None]
sf.write(os.path.join(WORK, 'mix.wav'), mix.astype(np.float32), SR)
print('mix LUFS %.1f  peak %.2f dBFS' % (meter.integrated_loudness(mix), 20 * np.log10(np.abs(mix).max())))
