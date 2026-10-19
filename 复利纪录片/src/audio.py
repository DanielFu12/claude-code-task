"""混音：配乐（Lyria 生成的两段原创配乐）+ 低频音效（本地合成，能量集中在 200Hz 以下）+ 原始影像原声，
原声出现时自动压低音乐（侧链闪避），无原声时音乐适度抬升。输出 work/mix.wav（48kHz 立体声）。
"""
import os, sys
import numpy as np, soundfile as sf, librosa
from scipy.signal import butter, sosfilt, sosfiltfilt
import pyloudnorm as pyln

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import A, START, C0, DUR, lines, BEAT
import part1 as P1
from clips import CLIPS
from script import DATA

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SR = 48000
N = int((DUR + 0.5) * SR)


def load(path, sr=SR):
    y, _ = librosa.load(path, sr=sr, mono=False)
    if y.ndim == 1: y = np.stack([y, y])
    return y.astype(np.float32)


def lp(x, f, order=4): return sosfiltfilt(butter(order, f, 'low', fs=SR, output='sos'), x, axis=-1)
def hp(x, f, order=2): return sosfiltfilt(butter(order, f, 'high', fs=SR, output='sos'), x, axis=-1)


def high_shelf_soften(x, f=5500, cut_db=-4.0):
    """温和削减高频（避免尖锐）：x - (1-g)·HP(x)"""
    g = 10 ** (cut_db / 20)
    return x - (1 - g) * hp(x, f, 2)


# ------------------------------------------------------------------ 低频音效（全部本地合成）
def env_exp(n, tau): return np.exp(-np.arange(n) / (tau * SR)).astype(np.float32)


def sub_drop(dur=2.6, f0=62, f1=27, amp=0.9):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-tt / (dur * 0.28))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * env_exp(n, dur * 0.42) * np.minimum(tt / 0.008, 1)
    y = np.tanh(y * 1.6) / np.tanh(1.6)
    return (y * amp).astype(np.float32)


def boom(dur=3.0, cut=110, amp=0.8, seed=0):
    """低通滤波的低频轰鸣（截止 110Hz，听感是深沉的隆隆声，而不是白噪声）"""
    n = int(dur * SR)
    r = np.random.default_rng(seed).normal(0, 1, n).astype(np.float32)
    y = lp(lp(r, cut, 4), cut, 4)
    y = y / (np.abs(y).max() + 1e-9)
    y = y * env_exp(n, dur * 0.3) * np.minimum(np.arange(n) / (0.015 * SR), 1)
    thump = sub_drop(min(dur, 1.4), 70, 38, 1.0)
    y[:len(thump)] += thump * 0.8
    return (y / (np.abs(y).max() + 1e-9) * amp).astype(np.float32)


def thump(amp=0.5, f0=85, f1=42, dur=0.55):
    return sub_drop(dur, f0, f1, amp)


def swell(dur=3.0, f=41, amp=0.35):
    """低频脉冲式涨落（用于推进与「回到原点」）"""
    n = int(dur * SR); tt = np.arange(n) / SR
    e = np.sin(np.pi * tt / dur) ** 2
    y = np.sin(2 * np.pi * f * tt) * e * (0.7 + 0.3 * np.sin(2 * np.pi * 1.5 * tt))
    return (y * amp).astype(np.float32)


def sfx_track():
    y = np.zeros(N, np.float32)

    def put(sig, t, g=1.0):
        i = int(t * SR)
        if i >= N: return
        m = min(len(sig), N - i); y[i:i + m] += sig[:m] * g

    put(swell(4.0, 38, 0.18), 0.0)                       # 开场低频脉动
    for cid, t0 in P1.FT.SEQ:                             # 每段原始影像入场：轻微低频落点
        put(thump(0.22, 75, 40, 0.6), t0 - 0.35)
    put(swell(3.5, 36, 0.30), 28.4)                       # 坍缩前的低频涨起
    put(sub_drop(3.2, 60, 25, 1.0), A['drop'])            # 标题重拍
    put(boom(4.0, 100, 0.65, 1), A['drop'])
    put(thump(0.35, 70, 38, 0.9), A['calm'])
    put(boom(3.0, 90, 0.40, 2), P1.T['BA'] - 0.4)          # 进入巴菲特、芒格
    put(sub_drop(1.5, 55, 30, 0.35), A['climax'])
    for k in range(0, 30, 2):                              # 30 年：每两拍一个低频脉冲，逐渐加强
        put(thump(0.12 + 0.18 * k / 30, 70, 40, 0.35), A['year0'] + k * BEAT)
    put(boom(5.0, 120, 1.0, 3), A['crash'])                # 崩塌
    put(sub_drop(4.0, 58, 22, 0.9), A['crash'])
    put(swell(3.0, 40, 0.30), A['rebuild'] + 0.6 + 7.27 * 2 * BEAT - 1.6)   # 回到原点
    put(boom(4.0, 110, 0.75, 4), A['epic'])
    put(sub_drop(3.0, 60, 26, 0.85), A['final'])
    put(boom(3.5, 100, 0.55, 5), A['final'])
    put(sub_drop(2.6, 64, 28, 1.0), A['brand_hit'])        # 「巴芒价值」出现
    put(boom(3.0, 90, 0.5, 6), A['brand_hit'])
    y = lp(y, 200, 4)                                      # 音效能量限制在 200Hz 以下
    return y


# ------------------------------------------------------------------ 旁白
def movavg(x, k):
    """居中滑动平均（累加和实现，O(N)）"""
    c = np.concatenate([[0.0], np.cumsum(x, dtype=np.float64)])
    i = np.arange(len(x)); a = np.clip(i - k // 2, 0, len(x)); b = np.clip(i + k - k // 2, 0, len(x))
    return ((c[b] - c[a]) / np.maximum(b - a, 1)).astype(np.float32)


def level(s, win=0.4, amount=0.6, lim_db=8.0):
    """慢速语音电平拉平：按 0.4s 短时 RMS 把弱句子抬起来、强句子压一点（不是快速压缩，不会喘）"""
    rms = np.sqrt(movavg(s ** 2, int(win * SR)) + 1e-10)
    ref = np.sqrt(np.mean(s[rms > np.percentile(rms, 40)] ** 2) + 1e-10)
    g = np.clip((ref / rms) ** amount, 10 ** (-lim_db / 20), 10 ** (lim_db / 20))
    g[rms < ref * 0.06] = 1.0                        # 停顿处不抬底噪
    g = movavg(g, int(0.25 * SR))
    return (s * g).astype(np.float32)


def voice_track():
    """原始影像原声：逐段响度归一（约 −20 LUFS），去低频隆隆声，首尾 30ms 淡入淡出"""
    v = np.zeros(N, np.float32)
    meter = pyln.Meter(SR)
    for cid, t0 in P1.FT.SEQ:
        p = os.path.join(ROOT, 'footage', 'clips', f'{cid}.wav')
        s, _ = librosa.load(p, sr=SR, mono=True)
        s = hp(s, 85, 2).astype(np.float32)
        s = high_shelf_soften(s, 7000, -2.0).astype(np.float32)
        s = level(s)
        if CLIPS[cid]['info']['who'] == '查理·芒格':          # 芒格的录音偏暗：+3dB 临场感
            s = s + 0.41 * sosfiltfilt(butter(2, [2500, 6000], 'band', fs=SR, output='sos'), s).astype(np.float32)
        l = meter.integrated_loudness(s)
        s = s * 10 ** ((-17.5 - l) / 20)
        fi, fo = int(0.08 * SR), int(0.12 * SR)
        s[:fi] *= np.linspace(0, 1, fi); s[-fo:] *= np.linspace(1, 0, fo)
        i = int(t0 * SR); m = min(len(s), N - i)
        v[i:i + m] += s[:m]
    return v


def follow(x, att=0.04, rel=0.45):
    """包络跟随（用于侧链闪避）"""
    e = np.abs(x)
    k = int(0.02 * SR)
    e = np.convolve(e, np.ones(k) / k, 'same')
    out = np.zeros_like(e)
    a_a, a_r = np.exp(-1 / (att * SR / 64)), np.exp(-1 / (rel * SR / 64))
    ds = e[::64]; o = np.zeros_like(ds); acc = 0.0
    for i, s in enumerate(ds):
        acc = a_a * acc + (1 - a_a) * s if s > acc else a_r * acc + (1 - a_r) * s
        o[i] = acc
    return np.interp(np.arange(len(e)), np.arange(len(ds)) * 64, o).astype(np.float32)


def main(out=None):
    out = out or os.path.join(ROOT, 'work', 'mix.wav')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    meter = pyln.Meter(SR)
    # 配乐
    m1 = load(os.path.join(ROOT, 'assets', 'music', 'score_main_lyria.mp3'))
    m2 = load(os.path.join(ROOT, 'assets', 'music', 'score_climax_lyria.mp3'))
    mus = np.zeros((2, N), np.float32)
    i1 = int(C0 * SR)
    seg = m1[:, :i1].copy()
    fo = int(1.2 * SR); seg[:, -fo:] *= np.linspace(1, 0, fo)       # 主题段尾部淡出
    mus[:, :seg.shape[1]] += seg
    m = min(m2.shape[1], N - i1); mus[:, i1:i1 + m] += m2[:, :m]
    mus = high_shelf_soften(mus, 5500, -4.5)
    mus = lp(mus, 14000, 4)
    # 片头重拍前的「吸气」：31.0–31.95s 压低音乐
    tt = np.arange(N) / SR
    suck = 1 - 0.75 * np.clip((tt - 31.0) / 0.6, 0, 1) * (tt < A['drop'])
    mus *= suck
    # 旁白
    v = voice_track()
    # 闪避包络按「片段」而不是按音节：整段原声期间稳定压低，句间停顿不会忽大忽小（避免抽吸感）
    speech = np.zeros(N, np.float32)
    for cid, t0 in P1.FT.SEQ:
        L = CLIPS[cid]['b'] - CLIPS[cid]['a']
        speech += np.clip(np.minimum((tt - (t0 - 0.45)) / 0.45, (t0 + L + 0.9 - tt) / 0.9), 0, 1).astype(np.float32)
    speech = np.clip(speech, 0, 1) ** 1.5
    duck = 1 - 0.82 * speech                    # 原声时音乐约 −15dB
    # 再在 1.2–4.5kHz 的语音清晰度频段多挖 6dB
    pres = sosfiltfilt(butter(2, [1200, 4500], 'band', fs=SR, output='sos'), mus, axis=-1)
    mus = mus - 0.5 * pres * speech[None, :]
    # 无讲话的段落适度抬升（+2dB），并在高潮段整体推起
    lift = 1 + 0.26 * (1 - speech)
    mus = mus * duck * lift
    sfx = sfx_track()
    mix = mus + sfx[None, :] * 0.9 + v[None, :]
    # 母线：软限幅 + 响度标准化（约 −14 LUFS，真峰值 < −1 dBFS）
    loud = meter.integrated_loudness(mix.T)
    mix = mix * 10 ** ((-14.0 - loud) / 20)
    peak = np.abs(mix).max()
    if peak > 0.89:
        mix = np.tanh(mix / 0.89 * 1.0) * 0.89
    tail = int(2.2 * SR); mix[:, -tail:] *= np.linspace(1, 0, tail) ** 1.5   # 与画面一起淡出
    sf.write(out, mix.T, SR, subtype='PCM_24')
    print('wrote', out, 'loudness', round(meter.integrated_loudness(mix.T), 1), 'LUFS peak', round(float(np.abs(mix).max()), 3))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
