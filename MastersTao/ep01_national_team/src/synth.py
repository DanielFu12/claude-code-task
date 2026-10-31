"""原创配乐合成器（numpy）：深沉低频、弦乐铺底、固定音型、低频冲击 / Sub Drop。

刻意避开高频 Whoosh 与白噪声：所有「冲击」都由低频正弦扫频 + 低通后的身体感构成，
手机外放时靠二次 / 三次谐波保留低音存在感。
"""
import numpy as np

SR = 48000


def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def onepole_lp(x, fc):
    """一阶低通（可用于逐样本变化的 fc 数组）"""
    fc = np.broadcast_to(np.asarray(fc, np.float64), x.shape)
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    acc = 0.0
    # 分块以保证速度：fc 基本是缓变的
    blk = 256
    for i in range(0, len(x), blk):
        ai = a[i]
        seg = x[i:i + blk]
        from scipy.signal import lfilter
        out, zf = lfilter([1 - ai], [1, -ai], seg, zi=[acc * ai])
        y[i:i + blk] = out
        acc = out[-1]
    return y


def lp(x, fc, order=2):
    from scipy.signal import butter, sosfilt
    sos = butter(order, fc / (SR / 2), "low", output="sos")
    return sosfilt(sos, x, axis=0)


def hp(x, fc, order=2):
    from scipy.signal import butter, sosfilt
    sos = butter(order, fc / (SR / 2), "high", output="sos")
    return sosfilt(sos, x, axis=0)


def adsr(n, a, d, s, r, sr=SR):
    a, d, r = int(a * sr), int(d * sr), int(r * sr)
    sus = max(n - a - d - r, 0)
    e = np.concatenate([np.linspace(0, 1, max(a, 1)), np.linspace(1, s, max(d, 1)),
                        np.full(sus, s), np.linspace(s, 0, max(r, 1))])
    return e[:n] if len(e) >= n else np.pad(e, (0, n - len(e)))


def saw_soft(f, t, nh=14, bright=6.0, phase=0.0):
    """带限锯齿（谐波按 exp 衰减，柔和）"""
    out = np.zeros_like(t)
    for k in range(1, nh + 1):
        if f * k > 9000: break
        out += np.sin(2 * np.pi * f * k * t + phase * k) / k * np.exp(-(k - 1) / bright)
    return out


# ---------------------------------------------------------------- 乐器
def pad(notes, dur, bright=4.0, detune=0.12, att=1.2, rel=1.8, seed=0):
    """弦乐/合成铺底：每个音 3 个失谐声部，立体声"""
    t = t_axis(dur)
    rng = np.random.default_rng(seed)
    L = np.zeros_like(t); R = np.zeros_like(t)
    for n in notes:
        f = midi(n)
        for k, dt in enumerate((-detune, 0, detune)):
            ff = f * 2 ** (dt / 12)
            vib = 0.0025 * np.sin(2 * np.pi * (4.6 + rng.random()) * t + rng.random() * 6)
            ph = 2 * np.pi * np.cumsum(ff * (1 + vib)) / SR
            s = np.zeros_like(t)
            for h in range(1, 26):
                if ff * h > 11000: break
                s += np.sin(ph * h + rng.random() * 6) / h * np.exp(-(h - 1) / bright)
            pan = (k - 1) * 0.6
            L += s * (1 - pan) * 0.5; R += s * (1 + pan) * 0.5
    env = adsr(len(t), att, 0.3, 0.9, rel)
    return np.stack([L * env, R * env], 1) / max(len(notes), 1) * 0.6


def sub(note, dur, att=0.02, rel=0.4, drive=1.8):
    """Sub 低音：基频正弦 + 失真出的谐波（让手机也能「听到」低音）"""
    t = t_axis(dur)
    f = midi(note)
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
    s = np.tanh(s * drive) / np.tanh(drive)
    env = adsr(len(t), att, 0.1, 0.85, rel)
    m = s * env
    return np.stack([m, m], 1)


def pluck_bass(note, dur=0.32, cutoff=900, drive=2.2):
    """固定音型用的低音拨弦：锯齿 + 包络低通"""
    t = t_axis(dur)
    f = midi(note)
    s = saw_soft(f, t, nh=18, bright=5) + 0.6 * np.sin(2 * np.pi * f / 2 * t)
    env = np.exp(-t / (dur * 0.42)) * np.minimum(t / 0.004, 1)
    fc = 120 + cutoff * np.exp(-t / 0.07)
    s = onepole_lp(onepole_lp(s, fc), fc)
    s = np.tanh(s * drive) * env
    return np.stack([s, s], 1)


def kick(dur=0.6, f0=150, f1=44, decay=0.32, click=0.25, drive=2.0):
    t = t_axis(dur)
    f = f1 + (f0 - f1) * np.exp(-t / 0.045)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t / decay)
    s += click * np.sin(2 * np.pi * 900 * t) * np.exp(-t / 0.004)
    s = np.tanh(s * drive) / np.tanh(drive)
    return np.stack([s, s], 1)


def thump(dur=0.35, f0=120, f1=55):
    """季度切换用的低频脉冲（柔和、短）"""
    t = t_axis(dur)
    f = f1 + (f0 - f1) * np.exp(-t / 0.03)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.11)
    s = np.tanh(s * 1.6)
    return np.stack([s, s], 1)


def boom(dur=4.0, f0=95, f1=27, body=0.5, seed=1):
    """电影式低频冲击：长尾低频正弦 + 低通身体（截止 220Hz，不含高频噪声）"""
    t = t_axis(dur)
    f = f1 + (f0 - f1) * np.exp(-t / 0.18)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 1.1)
    rng = np.random.default_rng(seed)
    nz = lp(rng.standard_normal(len(t)), 220, 4) * np.exp(-t / 0.35) * body * 3
    s = np.tanh((s + nz) * 1.8)
    L = s; R = np.roll(s, 37)
    return np.stack([L, R], 1)


def subdrop(dur=2.2, f0=88, f1=24):
    """Sub Drop：从中低频持续下滑到次声区"""
    t = t_axis(dur)
    f = f1 + (f0 - f1) * np.exp(-t / 0.55)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    s = s + 0.3 * np.sin(2 * 2 * np.pi * np.cumsum(f) / SR)
    env = np.minimum(t / 0.01, 1) * np.exp(-t / 0.9)
    s = np.tanh(s * 1.5) * env
    return np.stack([s, s], 1)


def swell(dur=2.5, notes=(50, 57, 62), curve=2.5):
    """倒放式渐强：低频铺底由无到有，末端戛然而止（引向重拍），不用白噪声"""
    p = pad(notes, dur + 0.2, bright=3.0 + 3.0, att=0.05, rel=0.05)
    n = int(dur * SR)
    e = (np.arange(n) / n) ** curve
    out = p[:n] * e[:, None]
    # 末段音高微微上扬
    return out


def mallet(note, dur=0.5, vel=1.0):
    """木琴/马林巴式短音（「时钟」音型）：基频 + 4 倍泛音，快速衰减"""
    t = t_axis(dur)
    f = midi(note)
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.16) + 0.35 * np.sin(2 * np.pi * f * 3.98 * t) * np.exp(-t / 0.04)
         + 0.15 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t / 0.09))
    s *= np.minimum(t / 0.002, 1) * vel
    return np.stack([s, s], 1)


def bell(note, dur=2.4, bright=0.35):
    """玻璃质感的柔和钟音（数据点亮时用；音域中低，避免刺耳）"""
    t = t_axis(dur)
    f = midi(note)
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t / 1.2) +
         bright * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / 0.5) +
         0.12 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t / 0.25))
    s *= np.minimum(t / 0.003, 1)
    return np.stack([s, s], 1)


def piano(note, dur=3.0, vel=1.0):
    t = t_axis(dur)
    f = midi(note)
    s = np.zeros_like(t)
    for h, a in enumerate((1.0, 0.5, 0.28, 0.16, 0.09, 0.05), 1):
        s += a * np.sin(2 * np.pi * f * h * (1 + 0.0004 * h * h) * t) * np.exp(-t * (0.9 + 0.7 * h))
    s *= np.minimum(t / 0.004, 1) * vel
    return np.stack([s * 0.95, s * 1.05], 1)


def taiko(dur=1.6):
    t = t_axis(dur)
    f = 55 + 70 * np.exp(-t / 0.04)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.35)
    rng = np.random.default_rng(3)
    s += lp(rng.standard_normal(len(t)), 400, 2) * np.exp(-t / 0.05) * 0.6
    s = np.tanh(s * 2.2)
    return np.stack([s, s], 1)


# ---------------------------------------------------------------- 混音工具
class Bus:
    def __init__(self, dur):
        self.x = np.zeros((int(dur * SR) + SR * 6, 2))

    def add(self, sig, at, gain=1.0):
        i = int(round(at * SR))
        if i < 0:
            sig = sig[-i:]; i = 0
        n = min(len(sig), len(self.x) - i)
        if n > 0:
            self.x[i:i + n] += sig[:n] * gain


def reverb(x, decay=2.6, mix=0.25, pre=0.02, lpf=3500, seed=7):
    """合成混响：低通指数衰减 IR（左右独立），FFT 卷积"""
    from scipy.signal import fftconvolve
    n = int(decay * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    out = np.zeros_like(x)
    for c in range(2):
        ir = rng.standard_normal(n) * np.exp(-t * 6.9 / decay)
        ir = lp(ir, lpf, 2)
        ir = np.concatenate([np.zeros(int(pre * SR)), ir])
        ir /= np.sqrt((ir ** 2).sum())
        out[:, c] = fftconvolve(x[:, c], ir)[:len(x)]
    return x * (1 - mix) + out * mix * 1.6


def sidechain(times, n, depth=0.45, rel=0.28):
    """按重拍时间给铺底做「呼吸」压缩包络"""
    env = np.ones(n)
    tt = np.arange(n) / SR
    for t0 in times:
        i0 = int(t0 * SR); i1 = min(n, i0 + int(rel * 3 * SR))
        if i0 >= n: continue
        seg = tt[i0:i1] - t0
        env[i0:i1] = np.minimum(env[i0:i1], 1 - depth * np.exp(-seg / rel))
    return env


# ---------------------------------------------------------------- v2 新增：律动与情绪层
def clap(dur=0.35, seed=4):
    """有「身体」的拍手：中频带通噪声 3 次微爆 + 200Hz 音体；限制在 0.6–3.2kHz，不刺耳"""
    from scipy.signal import butter, sosfilt
    t = t_axis(dur)
    rng = np.random.default_rng(seed)
    nz = rng.standard_normal(len(t))
    sos = butter(2, [600 / (SR / 2), 3200 / (SR / 2)], "band", output="sos")
    nz = sosfilt(sos, nz)
    env = np.zeros_like(t)
    for d in (0.0, 0.011, 0.023):
        env += np.where(t >= d, np.exp(-(t - d) / 0.012), 0) * 0.6
    env += np.where(t >= 0.03, np.exp(-(t - 0.03) / 0.09), 0)
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.04) * 0.6
    s = np.tanh((nz * env * 1.6 + body) * 1.4)
    return np.stack([s * 0.95, s * 1.05], 1)


def supersaw(note, dur, att=0.02, rel=0.25, cutoff=3200, voices=5, det=0.16, seed=0):
    """主旋律：多声部失谐锯齿 + 低通，带轻微颤音"""
    t = t_axis(dur)
    rng = np.random.default_rng(seed)
    f = midi(note)
    L = np.zeros_like(t); R = np.zeros_like(t)
    for v in range(voices):
        dt = (v - (voices - 1) / 2) / ((voices - 1) / 2) * det
        ff = f * 2 ** (dt / 12)
        vib = 1 + 0.003 * np.sin(2 * np.pi * 5.2 * t) * np.minimum(t / 0.4, 1)
        ph = 2 * np.pi * np.cumsum(ff * vib) / SR + rng.random() * 6
        s = np.zeros_like(t)
        for h in range(1, 30):
            if ff * h > 9000: break
            s += np.sin(ph * h) / h
        pan = (v - (voices - 1) / 2) / voices
        L += s * (0.5 - pan); R += s * (0.5 + pan)
    env = adsr(len(t), att, 0.15, 0.75, rel)
    out = np.stack([L, R], 1) * env[:, None] / voices
    return lp(out, cutoff, 2)


def riser(dur, notes=(50, 57, 62, 69), oct_up=12, seed=2):
    """音高上扬的和声渐强（替代噪声 Whoosh）：铺底整体滑升 + 包络指数增长，末端截断"""
    t = t_axis(dur)
    rng = np.random.default_rng(seed)
    L = np.zeros_like(t); R = np.zeros_like(t)
    bend = 2 ** ((t / dur) ** 2 * oct_up / 12)
    for k, n in enumerate(notes):
        f = midi(n) * bend
        ph = 2 * np.pi * np.cumsum(f) / SR
        s = sum(np.sin(ph * h + rng.random() * 6) / h * np.exp(-(h - 1) / 4) for h in range(1, 10))
        L += s * (0.6 if k % 2 else 0.4); R += s * (0.4 if k % 2 else 0.6)
    env = (t / dur) ** 2.6
    out = np.stack([L, R], 1) * env[:, None] / len(notes)
    return lp(out, 4500, 2)


def tom_roll(dur, start_rate=4, end_rate=16):
    """加速的低音鼓滚奏：每拍 4 → 16 下，力度递增"""
    out = np.zeros((int(dur * SR) + SR, 2))
    t = 0.0
    while t < dur:
        p = t / dur
        rate = start_rate + (end_rate - start_rate) * p * p   # 次/秒
        hit = taiko(0.6) * (0.35 + 0.65 * p)
        i = int(t * SR)
        out[i:i + len(hit)] += hit[:len(out) - i]
        t += 1 / rate
    return out[:int(dur * SR) + SR // 2]


def tick_hat(dur=0.08, vel=1.0):
    """音调化的「镲」：6 个非谐和高频正弦，30ms 衰减，非噪声"""
    t = t_axis(dur)
    s = sum(np.sin(2 * np.pi * f * t + k) for k, f in enumerate((3150, 4270, 5110, 6030, 7340, 8190)))
    s = s / 6 * np.exp(-t / 0.018) * vel
    return np.stack([s * 0.9, s * 1.1], 1)


def pluck_lead(note, dur=0.22, cutoff=5200):
    """明亮短拨弦（琶音用）"""
    out = supersaw(note, dur, att=0.003, rel=0.12, cutoff=cutoff, voices=3, det=0.08)
    t = t_axis(len(out) / SR)
    return out * np.exp(-t / 0.09)[:, None]
