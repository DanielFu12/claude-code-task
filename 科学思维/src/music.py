"""《科学思维》卡点配乐：以仓库根目录的 opus5.5涌现.mp4 原曲为底（CLAUDE.md：根目录 mp4 为背景音乐来源）。

原曲实测 112.9 BPM，拍点与固定网格的中位偏差约 3 ms，4 小节一个和声循环（F–F–D♭–E♭）。
timeline.MUSIC_MAP 规定每一章用原曲的哪些小节：本脚本按小节把原曲重新编排成整片长度（采样级对齐），
章与章的拼接都落在和声循环起点；章节重拍前 0.27 s 抽空，重拍上叠加原创合成的冲击音效。
同时导出 work/pulse.npy：成片每一帧的「底鼓脉冲」（来自最终混音的低频起音），画面用它跟着鼓点呼吸。

用法：python3 src/music.py work/   → work/score.wav（48 kHz 立体声）、work/pulse.npy
"""
import math
import os
import subprocess
import sys

import numpy as np
import soundfile as sf
from scipy import signal
from scipy.ndimage import maximum_filter1d

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as T  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = sys.argv[1] if len(sys.argv) > 1 else T.WORK
SRC = os.path.join(HERE, "..", "..", "opus5.5涌现.mp4")
SR = 48000
rng = np.random.default_rng(2026)


def load_source():
    wav = os.path.join(WORK, "opus_src.wav")
    if not os.path.exists(wav):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", SRC, "-vn", "-ac", "2", "-ar", str(SR), wav], check=True)
    x, sr = sf.read(wav, dtype="float32")
    return x.T


X = load_source()
SRC_LEN = X.shape[1]


def src_bar(b):
    """原曲第 b 小节的起点（采样）。"""
    return int(round((T.ORIGIN + b * T.BAR) * SR))


N = int((T.DUR + 0.6) * SR)
out = np.zeros((2, N), np.float32)


# ---------------------------------------------------------------- 按小节重新编排原曲
def place(src_a, src_b, dst, fade_in=0.004, tail=0.03):
    """把原曲 [src_a, src_b) 采样放到输出 dst 处；尾部多带 tail 秒做交叉淡出，头部极短淡入保住起音。"""
    nt = int(tail * SR)
    seg = X[:, src_a:min(src_b + nt, SRC_LEN)].copy()
    n_main = src_b - src_a
    fi = int(fade_in * SR)
    seg[:, :fi] *= np.linspace(0, 1, fi)[None, :]
    if seg.shape[1] > n_main:
        k = seg.shape[1] - n_main
        seg[:, n_main:] *= np.cos(np.linspace(0, np.pi / 2, k))[None, :]
    e = min(dst + seg.shape[1], N)
    out[:, dst:e] += seg[:, :e - dst]


# 片头：原曲第 0 小节之前的一小段
place(0, src_bar(0), 0, fade_in=0.0)
order = ["hook", "eight", "title", "cause", "falsify", "barnum", "correct", "invest", "end", "outro"]
out_bar = 0
SPLICES = []
for name in order:
    for (a, b) in T.MUSIC_MAP[name]:
        dst = src_bar(out_bar)
        place(src_bar(a), src_bar(b), dst)
        SPLICES.append((round(dst / SR, 3), name, a, b))
        out_bar += b - a
# 原曲在最后一小节之后的自然余音
tail_src = src_bar(58)
place(tail_src, SRC_LEN, src_bar(out_bar), tail=0.0)


# ---------------------------------------------------------------- 原创合成的冲击音效（只在重拍 / 关键揭示点上）
def lowpass(x, fc, order=2):
    b, a = signal.butter(order, min(fc, SR / 2 * 0.95) / (SR / 2), "low")
    return signal.lfilter(b, a, x)


def highpass(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), "high")
    return signal.lfilter(b, a, x)


def bandpass(x, f0, f1, order=2):
    b, a = signal.butter(order, [f0 / (SR / 2), min(f1, SR / 2 * 0.95) / (SR / 2)], "band")
    return signal.lfilter(b, a, x)


def subdrop(dur=2.0, f0=85, f1=30):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.4)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (dur * 0.35))


def impact(dur=2.4):
    n = int(dur * SR)
    t = np.arange(n) / SR
    body = lowpass(rng.normal(0, 1, n), 180, 4) * np.exp(-t / 0.35) * 2.5
    crack_ = highpass(rng.normal(0, 1, n), 3000) * np.exp(-t / 0.05) * 0.5
    air = highpass(rng.normal(0, 1, n), 6000) * np.exp(-t / 0.9) * 0.12
    return body + crack_ + air + subdrop(dur) * 0.9


def reverse_swell(dur):
    """反向镲片：在重拍前逐渐涌起。"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = highpass(rng.normal(0, 1, n), 3000) * (t / dur) ** 3
    return x * 0.6


def thump():
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    f = 45 + 70 * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.18) + \
        bandpass(rng.normal(0, 1, n), 800, 5000) * np.exp(-t / 0.03) * 0.25


def add(t, sig, gain=1.0, pan=0.0):
    i0 = int(round(t * SR))
    l, r = math.cos((pan + 1) * math.pi / 4) * 1.414, math.sin((pan + 1) * math.pi / 4) * 1.414
    n = min(len(sig), N - i0)
    if n > 0 and i0 >= 0:
        fx[0, i0:i0 + n] += sig[:n] * gain * l
        fx[1, i0:i0 + n] += sig[:n] * gain * r


fx = np.zeros((2, N), np.float32)
HITS = T.HITS
# 重拍前抽空 0.27 s（音乐整体），重拍上一记冲击
gate = np.ones(N, np.float32)
ramp = int(0.015 * SR)
for h in HITS[:-1]:
    i0, i1 = int((h - 0.27) * SR), int(h * SR)
    gate[i0:i1] = 0.0
    gate[i0 - ramp:i0] = np.minimum(gate[i0 - ramp:i0], np.linspace(1, 0, ramp))
    add(h - 2 * T.BEAT, reverse_swell(2 * T.BEAT - 0.27), 0.22)
for h in HITS:
    big = h in (T.SEC["eight"][0], T.SEC["title"][0], T.BRAND_T)
    add(h, impact(), 0.30 if big else 0.20)
out *= gate[None, :]
# 段落中的关键揭示点：一记轻的低频「咚」，与原曲底鼓叠在一起加重拍点
for a in T.ACCENTS:
    if all(abs(a - h) > 0.2 for h in HITS):
        add(a, thump(), 0.10)

mix = out + fx
# 结尾：原曲余音自然收尾，最后 1.2 s 再淡出
fo = int(1.2 * SR)
end_i = int(T.DUR * SR)
mix[:, end_i - fo:end_i] *= np.linspace(1, 0, fo)[None, :] ** 1.5
mix[:, end_i:] = 0


# ---------------------------------------------------------------- 响度与真峰值
def tp_limit(x, peak_db=-2.0):
    up = signal.resample_poly(lowpass(x, 16000, 4), 4, 1, axis=1)
    peak = 10 ** (peak_db / 20)
    need = np.maximum(np.abs(up).max(0) / peak, 1.0)
    win_ = int(0.004 * SR * 4)
    need = maximum_filter1d(need, size=2 * win_ + 1)
    g = 1 / need
    rel = math.exp(-1 / (0.08 * SR * 4))
    g = np.minimum(g, signal.lfilter([1 - rel], [1, -rel], g - 1) + 1)
    return np.clip(signal.resample_poly(up * g[None, :], 1, 4, axis=1), -peak, peak)


import pyloudnorm as pyln  # noqa: E402

meter = pyln.Meter(SR)
TARGET = -14.5
gain_db = TARGET - meter.integrated_loudness(mix.T)
for _ in range(4):
    res = tp_limit(mix * 10 ** (gain_db / 20))
    l2 = meter.integrated_loudness(res.T)
    if abs(l2 - TARGET) < 0.2:
        break
    gain_db += TARGET - l2
mix = res
sf.write(os.path.join(WORK, "score.wav"), mix.T.astype(np.float32), SR, subtype="PCM_24")

# ---------------------------------------------------------------- 画面用的鼓点脉冲（每帧一个值，0..1）
mono = mix.mean(0)
low = lowpass(np.abs(lowpass(mono, 150, 4)), 40, 2)
hop = SR // T.FPS
fr = np.array([low[i * hop:(i + 1) * hop].max() if i * hop < len(low) else 0 for i in range(int(T.DUR * T.FPS) + 2)])
on = np.maximum(0, np.diff(fr, prepend=fr[0]))
on = on / (np.percentile(on[on > 0], 98) + 1e-9)
pulse = np.zeros_like(on)
v = 0.0
for i, o in enumerate(on):
    v = max(v * math.exp(-1 / (T.FPS * 0.16)), min(1.0, o))
    pulse[i] = v
np.save(os.path.join(WORK, "pulse.npy"), pulse.astype(np.float32))
print("after limiter", round(l2, 2), "LUFS; splices:", len(SPLICES))
for sp in SPLICES:
    print("  ", sp)
print("written", os.path.join(WORK, "score.wav"), round(N / SR, 2), "s")
