"""拼接两段 Lyria 原创配乐，得到与画面同一条 120 BPM 节拍网格的完整音轨。

partA（0–136s）：狂热上升 → 骤停崩塌 → 24.06s 重击 → 主题段 → 钢琴尾声
partB 从全局 135.96s 开始，使它 8.1s 处的鼓点爆发正好落在小节线 144.06s 上。
"""
import sys, numpy as np, soundfile as sf, librosa

WORK = sys.argv[1]
SR = 44100
B_OFFSET = 135.96          # partB 在全片中的起点（秒）
DUR = 296.0

a, _ = librosa.load(f'{WORK}/../music/partA.mp3', sr=SR, mono=False)
b, _ = librosa.load(f'{WORK}/../music/partB.mp3', sr=SR, mono=False)
a, b = a.T, b.T
out = np.zeros((int(DUR * SR), 2), np.float32)
# partA 在 135.5–137.0s 淡出（原曲本身已在这里收尾）
na = min(len(a), int(137.0 * SR))
fa = np.ones(na, np.float32)
i0, i1 = int(135.5 * SR), na
fa[i0:i1] = np.cos(np.linspace(0, np.pi / 2, i1 - i0)) ** 2
out[:na] += a[:na] * fa[:, None]
o = int(B_OFFSET * SR)
nb = min(len(b), len(out) - o)
out[o:o + nb] += b[:nb]
f = int(3.0 * SR)
out[-f:] *= np.linspace(1, 0, f)[:, None] ** 1.5
peak = np.abs(out).max()
if peak > 0.98: out *= 0.98 / peak
sf.write(f'{WORK}/bgm.wav', out, SR)
print('bgm.wav', len(out) / SR, 's  peak', peak)
