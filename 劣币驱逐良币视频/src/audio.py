"""配乐：Lyria 3 Pro 生成的原创配乐 A1（assets/score_lyria_A1.mp3，105 BPM）
按节拍网格无缝拼接延长，并叠加低频转场音效（sub drop / boom / pulse）。
用法: python3 src/audio.py WORKDIR   -> WORKDIR/score.wav, WORKDIR/music_only.wav
"""
import os, sys, subprocess
import numpy as np, soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'assets', 'score_lyria_A1.mp3')
SR = 48000
P, O = 0.5715714, 0.1080853            # 节拍网格（周期 / 偏移，秒），由 librosa 拟合
# 拼接表：(源起始拍, 源结束拍)；拍数为整数 -> 新时间轴上节拍网格保持连续
SEGS = [(8, 60), (44, 96), (80, 292), (240, 256), (240, 256), (240, 256), (240, None)]   # 去掉前 8 拍前奏；终段多循环两次给投资启示
XF = 0.05                               # 等功率交叉淡化（秒）
# 拼接后再做的「原地重复」：(x, L) 表示播到分镜第 x 拍时，把 [x-L, x) 这 L 拍再播一遍（与 timeline.WARP 一一对应）
REPEATS = [(128, 16), (212, 8), (352, 16), (368, 16), (384, 16)]
SKIP = 8


def bt(b):
    return O + P * b


def load():
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', SRC, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def bt_new(n):
    return O + P * (n - SKIP)


def xfade_concat(pieces):
    n = int(XF * SR)
    out = pieces[0]
    w = np.linspace(0, 1, n)[:, None]
    for seg in pieces[1:]:
        mix = out[-n:] * np.cos(w * np.pi / 2) + seg[:n] * np.sin(w * np.pi / 2)
        out = np.concatenate([out[:-n], mix, seg[n:]])
    return out


def repeats(y):
    n = int(XF * SR) // 2
    pieces, cur = [], 0
    for x, L in REPEATS:
        e = int(bt_new(x) * SR)
        pieces.append(y[cur:e + n])
        cur = int(bt_new(x - L) * SR) - n
    pieces.append(y[cur:])
    return xfade_concat(pieces)


def splice(y):
    out = None
    n = int(XF * SR)
    for a, b in SEGS:
        s = int(bt(a) * SR)
        e = int(bt(b) * SR) if b is not None else len(y)
        if out is None:
            # 第一段从「第 a 拍之前 O 秒」开始，保证新时间轴上第 a 拍仍落在 O 秒处（与 timeline.B 一致）
            out = y[int((bt(a) - O) * SR):min(e + n // 2, len(y))].copy()
            continue
        seg = y[max(s - n // 2, 0):min(e + n // 2, len(y))].copy()
        w = np.linspace(0, 1, n)[:, None]
        mix = out[-n:] * np.cos(w * np.pi / 2) + seg[:n] * np.sin(w * np.pi / 2)
        out = np.concatenate([out[:-n], mix, seg[n:]])
    return out


# ---------------------------------------------------------------- 低频音效
def sub_drop(dur=2.4, f0=78, f1=26, amp=0.55):
    t = np.arange(int(dur * SR)) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.35)
    ph = 2 * np.pi * np.cumsum(f) / SR
    env = (1 - np.exp(-t / 0.006)) * np.exp(-t / (dur * 0.38))
    x = np.sin(ph) + 0.25 * np.sin(2 * ph) * np.exp(-t / 0.2)
    return np.tanh(1.6 * x * env) * amp


def boom(dur=3.2, amp=0.5):
    """深沉轰鸣：低频正弦 + 低通噪声的厚度（截止 < 180Hz）"""
    t = np.arange(int(dur * SR)) / SR
    rng = np.random.default_rng(7)
    nz = rng.standard_normal(len(t))
    # 简单的一阶低通多级 -> 只留低频隆隆声
    for fc in (160, 120, 90):
        a = np.exp(-2 * np.pi * fc / SR)
        y = np.empty_like(nz); acc = 0.0
        for i in range(len(nz)):
            acc = a * acc + (1 - a) * nz[i]; y[i] = acc
        nz = y
    nz /= np.abs(nz).max() + 1e-9
    f = 34 + 22 * np.exp(-t / 0.5)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR)
    env = (1 - np.exp(-t / 0.01)) * np.exp(-t / (dur * 0.33))
    return np.tanh((tone * 0.9 + nz * 0.8) * env * 1.4) * amp


def pulse(amp=0.35):
    """低频脉冲（心跳/数字跳变）"""
    t = np.arange(int(0.5 * SR)) / SR
    f = 46 + 40 * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12) * (1 - np.exp(-t / 0.003)) * amp


def add(out, x, t):
    i = int(t * SR)
    if i >= len(out): return
    x = x[:len(out) - i]
    out[i:i + len(x)] += x[:, None]


# 新时间轴上的低频事件（秒）——与 video.py 中的镜头切换一一对应
def sfx_events():
    from timeline import SFX
    return SFX


if __name__ == '__main__':
    work = sys.argv[1]
    os.makedirs(work, exist_ok=True)
    y = repeats(splice(load()))
    sf.write(os.path.join(work, 'music_only.wav'), y.astype(np.float32), SR)
    sys.path.insert(0, HERE)
    out = y * 0.92
    kinds = {'drop': sub_drop, 'boom': boom, 'pulse': pulse}
    cache = {}
    for t, kind, amp in sfx_events():
        if kind not in cache: cache[kind] = kinds[kind]()
        add(out, cache[kind] * amp, t)
    # 软限幅，防止叠加后削波
    peak = np.abs(out).max()
    out = np.tanh(out * 1.05) / np.tanh(1.05)
    fade = int(1.5 * SR)
    print('dur %.2f  peak before limit %.2f' % (len(out) / SR, peak))
    sf.write(os.path.join(work, 'score.wav'), out.astype(np.float32), SR)
