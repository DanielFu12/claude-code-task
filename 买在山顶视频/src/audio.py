"""背景音乐：取自仓库根目录 opus5.5涌现.mp4，按节拍无缝拼接延长，并输出节拍/能量分析。

用法：python3 src/audio.py WORK_DIR
产物：WORK/bgm.wav（成片音轨）、WORK/music.json（节拍网格、关键时间点、逐帧能量与起音强度）
"""
import json, os, subprocess, sys
import numpy as np, soundfile as sf, librosa

WORK = sys.argv[1]
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'opus5.5涌现.mp4')
os.makedirs(WORK, exist_ok=True)
raw = os.path.join(WORK, 'ref.wav')
if not os.path.exists(raw):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-vn', '-ac', '2', '-ar', '44100', raw], check=True)
y, sr = sf.read(raw)                       # 立体声 44.1k
mono = y.mean(1)

# 原曲恒定速度 ≈112.9 BPM：用 librosa 的节拍做线性拟合，得到无漂移的节拍网格（第 32 拍 = 第一个重拍 17.14s）
y22 = librosa.resample(mono.astype(np.float32), orig_sr=sr, target_sr=22050)
_, b = librosa.beat.beat_track(y=y22, sr=22050, hop_length=512)
bt = librosa.frames_to_time(b, sr=22050, hop_length=512)
k = np.arange(len(bt))
per, off = np.polyfit(k, bt, 1)
off = off - per * round(off / per)          # 网格从第 0 拍开始
B = lambda i: off + per * i

# 拼接方案（拍号）：原曲中 b97↔b217、b83↔b139、b182↔b214 处的上下文几乎完全一致（相似度 ≥0.98）
SEGS = [(0, 217), (97, 217), (97, 139), (83, 182), (214, None)]


def refine(ta, tb):
    """在 ±25ms 内找让 y[ta+x] 与 y[tb+x+d] 最吻合的 d（以采样计）"""
    w = int(0.8 * sr); r = int(0.025 * sr)
    a = mono[int(ta * sr) - w:int(ta * sr) + w]
    best, bd = -1e9, 0
    for d in range(-r, r + 1, 2):
        s = int(tb * sr) + d
        c = float(np.dot(a, mono[s - w:s + w]))
        if c > best: best, bd = c, d
    return bd

xf = int(0.04 * sr); h = xf // 2
# 每段 (源起点采样, 源终点采样)；拼接处做以拼接点为中心的等功率交叉淡化，节拍网格严格连续
spans = []
prev_end_t = None
for i, (s, e) in enumerate(SEGS):
    if i == 0:
        si = 0
    else:
        si = int(B(s) * sr) + refine(prev_end_t, B(s))
    ei = int(B(e) * sr) if e is not None else len(y)
    spans.append((si, ei))
    prev_end_t = B(e) if e is not None else None
out = y[spans[0][0]:spans[0][1] - h].copy()
seg_starts = [0.0]
for (si, ei), (psi, pei) in zip(spans[1:], spans[:-1]):
    t = np.linspace(0, 1, xf)[:, None]
    mixed = y[pei - h:pei + h] * np.cos(t * np.pi / 2) + y[si - h:si + h] * np.sin(t * np.pi / 2)
    out = np.concatenate([out, mixed])
    seg_starts.append((len(out) - h) / sr)
    out = np.concatenate([out, y[si + h:(ei - h) if ei < len(y) else ei]])
starts = seg_starts
cum_beats = []            # (成片时间, 原曲拍号)
for (s, e), (si, ei), c0 in zip(SEGS, spans, seg_starts):
    for j in range(s, e if e is not None else 236):
        if B(j) * sr >= len(y): break
        cum_beats.append((round(c0 + B(j) - si / sr, 4), j))

# 结尾去掉静音
env = np.abs(out).max(1)
last = np.nonzero(env > 1e-3)[0][-1]
out = out[:last + int(0.3 * sr)]
fade = int(0.6 * sr); out[-fade:] *= np.linspace(1, 0, fade)[:, None]
# ---------- 音效：两个抽空段里加入低频心跳（每 2 拍一次，严格落在节拍网格上）
HB = []
def _beat_out(j_from, j_to):
    return [t_ for t_, j in cum_beats if j_from <= j < j_to]
BREAKS = [(20, 32, 0)]                     # 原曲第 20–31 拍：序章里的抽空段
seen = 0
for t_, j in cum_beats:
    if 164 <= j < 176:                     # 第一次出现的 164–175 拍：山顶的抽空段
        if seen < 12: HB.append(t_)
        seen += 1
HB = sorted(set(_beat_out(20, 32) + HB))[::2]
def _thump(n, f0, f1, dec, amp):
    tt = np.arange(n) / sr
    ph = 2 * np.pi * np.cumsum(f0 + (f1 - f0) * (1 - np.exp(-tt / 0.05))) / sr
    return amp * np.sin(ph) * np.exp(-tt / dec) * (1 - np.exp(-tt / 0.003))
n = int(0.5 * sr)
beat = _thump(n, 72, 44, 0.085, 1.0)
beat[int(0.21 * sr):] += _thump(n - int(0.21 * sr), 64, 40, 0.07, 0.62)
for k, t_ in enumerate(HB):
    i = int(t_ * sr)
    g = 0.42 * (0.7 + 0.3 * min(1, k / 4))
    seg = beat[:max(0, min(n, len(out) - i))] * g
    out[i:i + len(seg)] += seg[:, None]
# 软限幅：只压超过 0.9 的峰，不改变整体响度
ax = np.abs(out)
over = ax > 0.9
out[over] = np.sign(out[over]) * (0.9 + 0.09 * np.tanh((ax[over] - 0.9) / 0.09))
sf.write(os.path.join(WORK, 'bgm.wav'), out.astype(np.float32), sr)
DUR = len(out) / sr

# ---------- 分析：给画面用
m = librosa.resample(out.mean(1).astype(np.float32), orig_sr=sr, target_sr=22050)
FPS = 30
hop = 22050 // FPS
on = librosa.onset.onset_strength(y=m, sr=22050, hop_length=hop)
on = on / np.percentile(on, 99.5)
S = np.abs(librosa.stft(m, n_fft=2048, hop_length=hop)); f = librosa.fft_frequencies(sr=22050, n_fft=2048)
low = S[f < 140].sum(0); low = low / np.percentile(low, 99)
rms = librosa.feature.rms(y=m, hop_length=hop)[0]; rms = rms / np.percentile(rms, 99)
beats = [t for t, j in cum_beats]
srcb = [j for t, j in cum_beats]
# 关键点：原曲第 32 / 176 拍是重拍，第 148 拍进入轻段，第 164 拍进入抽空段
keys = {f'{name}_{n}': t for n, (name, jj) in enumerate([]) for t in []}
ev = {'drop': [t for t, j in cum_beats if j in (32, 176)],
      'light': [t for t, j in cum_beats if j == 148],
      'break': [t for t, j in cum_beats if j in (20, 164)]}
json.dump(dict(duration=DUR, fps=FPS, period=per, beats=beats, src_beat=srcb, events=ev, heartbeats=HB,
               onset=np.round(on, 3).tolist(), low=np.round(low, 3).tolist(), rms=np.round(rms, 3).tolist()),
          open(os.path.join(WORK, 'music.json'), 'w'))
print(f'duration {DUR:.2f}s  period {per:.4f}s  ({60 / per:.2f} BPM)')
print('segment starts', [round(s, 2) for s in starts])
for k_, v in ev.items(): print(k_, [round(x, 2) for x in v])
