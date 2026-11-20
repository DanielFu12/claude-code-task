"""最终混音 -> work/mix.wav（V8）
- 旁白：高通、轻压缩、同一个小房间的短混响 + 极轻的房间底噪，把各段粘成同一个录音环境。
- 配乐闪避：有旁白时全频压低 12 dB，人声频段（700 Hz–4 kHz）再让出 5 dB；提前 0.15 秒开始压，
  句间短停顿（< 0.9 秒）保持压低，不让音乐在句缝里一涌一退。
- 响度：线性增益到 -14 LUFS + 峰值限制，不再用动态 loudnorm（它会把闪避又压平）。"""
import sys, json
import numpy as np, soundfile as sf, pyloudnorm as pyln
from scipy import signal

W = sys.argv[1] if len(sys.argv) > 1 else 'work'
SR = 48000
v, _ = sf.read(f'{W}/voice.wav', dtype='float32')
m, sr = sf.read(f'{W}/music.wav', dtype='float32'); assert sr == SR
N = max(len(v), len(m)); v = np.pad(v, (0, N - len(v))); m = np.pad(m, ((0, N - len(m)), (0, 0)))
meter = pyln.Meter(SR)

# ---------------------------------------------------------------- 旁白
v = signal.sosfilt(signal.butter(2, 70, 'hp', fs=SR, output='sos'), v)
e = np.sqrt(signal.lfilter([1 - np.exp(-1 / (0.05 * SR))], [1, -np.exp(-1 / (0.05 * SR))], v ** 2) + 1e-10)
thr = 10 ** (-24 / 20)
v = v * np.where(e > thr, (e / thr) ** (1 / 2.2 - 1), 1.0)            # 2.2:1 轻压缩
rng = np.random.default_rng(7)
ir_n = int(0.45 * SR); tt = np.arange(ir_n) / SR
ir = rng.standard_normal(ir_n) * np.exp(-tt / 0.09)                     # 小房间：RT60 约 0.6 秒
ir = signal.sosfilt(signal.butter(2, [250, 5000], 'bp', fs=SR, output='sos'), ir); ir[:int(0.012 * SR)] = 0
ir /= np.sqrt(np.sum(ir ** 2))
v = v + 0.1 * signal.fftconvolve(v, ir)[:N]
noise = signal.lfilter([0.049922035, -0.095993537, 0.050612699, -0.004408786], [1, -2.494956002, 2.017265875, -0.522189400],
                       rng.standard_normal(N))                          # 粉噪声
noise = signal.sosfilt(signal.butter(2, [120, 6000], 'bp', fs=SR, output='sos'), noise)
noise *= 10 ** (-64 / 20) / np.sqrt(np.mean(noise ** 2))
v = v + noise
v = v.astype(np.float32)

# ---------------------------------------------------------------- 闪避包络
hop = 240; nf = N // hop + 1
r = np.sqrt(np.mean(np.pad(v, (0, nf * hop - N)).reshape(nf, hop) ** 2, 1))
act = (20 * np.log10(r + 1e-9) > -42).astype(np.float32)
hold = int(0.9 * SR / hop); look = int(0.15 * SR / hop)
act = np.convolve(act, np.ones(hold), 'full')[:nf] > 0                 # 保持：短停顿不放开
act = np.roll(act, -look); act[-look:] = act[-look - 1]                 # 提前量
act = act.astype(np.float64)
g = np.zeros(nf); a_up, a_dn = np.exp(-hop / (0.08 * SR)), np.exp(-hop / (0.55 * SR))
for k in range(1, nf):
    a = a_up if act[k] > g[k - 1] else a_dn
    g[k] = a * g[k - 1] + (1 - a) * act[k]
g = np.interp(np.arange(N), np.arange(nf) * hop, g)
duck_all = 10 ** (-12 * g / 20); duck_mid = 10 ** (-5 * g / 20)
sos_mid = signal.butter(2, [700, 4000], 'bp', fs=SR, output='sos')
mid = signal.sosfiltfilt(sos_mid, m, axis=0)
m = (m - mid) * duck_all[:, None] + mid * (duck_all * duck_mid)[:, None]

# ---------------------------------------------------------------- 相对电平：音乐满电平比人声低 2 LU，闪避后约低 14~19 LU
lv = meter.integrated_loudness(v[g > 0.5]) if (g > 0.5).sum() > SR else meter.integrated_loudness(v)
lm = meter.integrated_loudness(sf.read(f'{W}/music.wav', dtype='float32')[0])
m = m * 10 ** ((lv - 2 - lm) / 20)
mix = m + v[:, None]
sp = g > 0.9
print('during speech: voice %.1f LUFS, music %.1f LUFS; music between lines/sections %.1f LUFS'
      % (meter.integrated_loudness(v[sp]), meter.integrated_loudness(m[sp]), meter.integrated_loudness(m[g < 0.1])))

# ---------------------------------------------------------------- 线性增益到 -14 LUFS + 峰值限制
L = meter.integrated_loudness(mix)
mix *= 10 ** ((-14 - L) / 20)
ceil = 10 ** (-1.5 / 20)
pk = np.abs(mix).max(1)
need = np.minimum(1.0, ceil / np.maximum(pk, 1e-9))
win = int(0.005 * SR)
from scipy.ndimage import minimum_filter1d, uniform_filter1d
gl = minimum_filter1d(need, 2 * win + 1)
gl = uniform_filter1d(gl, win)
gl = np.minimum(gl, need)
mix *= gl[:, None]
print('voice %.1f LUFS, music(full) %.1f LUFS, mix %.1f LUFS, limiter max -%.1f dB'
      % (lv, lm, meter.integrated_loudness(mix), -20 * np.log10(gl.min())))
sf.write(f'{W}/mix.wav', mix.astype(np.float32), SR, subtype='FLOAT')
