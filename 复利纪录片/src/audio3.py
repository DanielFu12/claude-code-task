"""第四版混音：三段原创配乐（Lyria）+ 原始影像原声 + Gemini TTS 解说 + 低频音效。

配乐按段落卡点（节点由 music3.py 分析得到，存于 assets/music3/music3.json）：
  hook   的大鼓重拍  → 片名出现的那一帧
  bed    片名之后到动画段之前，铺在原声与解说下面（无缝循环拼接）
  climax 的高潮重拍  → 总结句；其后的最后一个强拍 → 片尾「巴芒价值」字标
原声与解说出现时，配乐按段落整体压低（不随音节抽吸）；无人声的片名、动画重拍、总结、片尾把配乐推起来。
输出 work/mix3.wav（48kHz 立体声，约 −14 LUFS，真峰值 < −1 dBFS）。
"""
import json, os, sys
import numpy as np, soundfile as sf, librosa
from scipy.signal import butter, sosfiltfilt
import pyloudnorm as pyln

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t3
from clips import CLIPS
from dsp import sub_drop, boom, thump, swell, high_shelf_soften, lp, hp, level, movavg

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SR = 48000
N = int((t3.DUR + 0.5) * SR)
MDIR = os.path.join(ROOT, 'assets', 'music3')
tt = np.arange(N) / SR


def load(path):
    y, _ = librosa.load(path, sr=SR, mono=False)
    if y.ndim == 1: y = np.stack([y, y])
    return y.astype(np.float32)


def place(buf, sig, t0, fade_in=0.0, fade_out=0.0):
    """把 sig（2×n）放到 t0（可为负：裁掉开头）"""
    i = int(round(t0 * SR)); s = sig
    if i < 0: s = s[:, -i:]; i = 0
    m = min(s.shape[1], N - i)
    if m <= 0: return
    s = s[:, :m].copy()
    if fade_in > 0:
        k = min(int(fade_in * SR), m); s[:, :k] *= np.linspace(0, 1, k)
    if fade_out > 0:
        k = min(int(fade_out * SR), m); s[:, -k:] *= np.linspace(1, 0, k)
    buf[:, i:i + m] += s


def env(spans, att=0.45, rel=0.9):
    """段落包络：spans 内为 1，前后线性过渡"""
    e = np.zeros(N, np.float32)
    for a, b in spans:
        e = np.maximum(e, np.clip(np.minimum((tt - (a - att)) / att, (b + rel - tt) / rel), 0, 1))
    return e


def main(out=None):
    out = out or os.path.join(ROOT, 'work', 'mix3.wav')
    M = json.load(open(os.path.join(MDIR, 'music3.json')))
    seg = {s['id']: s for s in t3.SEGS}
    meter = pyln.Meter(SR)
    mus = np.zeros((2, N), np.float32)
    # 1) hook：大鼓重拍对准片名
    hook = load(os.path.join(MDIR, M['hook']['file']))
    t_hook = seg['title']['t0'] - M['hook']['hit']
    hook_end = seg['title']['t1'] + 3.0
    hk = hook[:, :int((hook_end - t_hook) * SR)] if hook_end > t_hook else hook
    place(mus, hk, t_hook, fade_in=0.5, fade_out=3.0)
    # 第四版片名之前多了一段解说，hook 的起点晚于片头：把它开头 16 秒（8 小节，120 BPM）的安静引子向前循环，
    # 让冷开场的李录原声下面仍有配乐（拼接处 0.5 秒交叉淡化，节拍相位不变）
    intro = M['hook'].get('intro_loop', 16.0)
    k = 1
    while t_hook - (k - 1) * intro > 0:
        t0 = t_hook - k * intro
        place(mus, hook[:, :int((intro + 0.5) * SR)], t0, fade_in=2.0 if t0 - intro <= 0 else 0.5, fade_out=0.5)
        k += 1
    # 2) bed：片名之后到动画段（循环拼接，交叉淡化 4 秒）
    bed = load(os.path.join(MDIR, M['bed']['file'])) * M['bed'].get('gain', 1.0)
    b0, b1 = seg['title']['t1'] - 2.0, seg['G10']['t0'] + 3.0
    pos, src = b0, M['bed'].get('start', 0.0)
    while pos < b1:
        piece = bed[:, int(src * SR):]
        L = min(piece.shape[1] / SR, b1 - pos + 4.0)
        place(mus, piece[:, :int(L * SR)], pos, fade_in=4.0, fade_out=4.0)
        pos += L - 4.0; src = M['bed'].get('loop', 20.0)
    # 3) climax：高潮重拍对准总结句
    cl = load(os.path.join(MDIR, M['climax']['file']))
    t_cl = seg['G14']['t0'] - M['climax']['hit']
    place(mus, cl, t_cl, fade_in=3.0 if t_cl < seg['G10']['t0'] else 0.5, fade_out=0)
    mus = high_shelf_soften(mus, 5500, -4.0)
    mus = lp(mus, 14000, 4)
    # 片名前「吸气」
    th = seg['title']['t0']
    mus *= 1 - 0.7 * (np.clip((tt - (th - 0.9)) / 0.6, 0, 1) * (tt < th))

    # ---------------------------------------------------------------- 人声
    clip_v = np.zeros(N, np.float32); vo = np.zeros(N, np.float32)
    clip_spans, vo_spans = [], []
    for s in t3.SEGS:
        if s['kind'] != 'clip': continue
        x, _ = librosa.load(os.path.join(ROOT, 'footage', 'clips', f"{s['id']}.wav"), sr=SR, mono=True)
        x = hp(x, 85, 2).astype(np.float32)
        x = level(x)
        if CLIPS[s['id']]['info']['who'] == '查理·芒格':
            x = x + 0.41 * sosfiltfilt(butter(2, [2500, 6000], 'band', fs=SR, output='sos'), x).astype(np.float32)
        x = x * 10 ** ((-16.5 - meter.integrated_loudness(x)) / 20)
        fi, fo = int(0.08 * SR), int(0.12 * SR)
        x[:fi] *= np.linspace(0, 1, fi); x[-fo:] *= np.linspace(1, 0, fo)
        i = int(s['a0'] * SR); m = min(len(x), N - i)
        clip_v[i:i + m] += x[:m]
        clip_spans.append((s['a0'], s['a0'] + len(x) / SR))
    for sid, s in t3.SENTS.items():
        p = os.path.join(ROOT, 'work', 'vo', f'{sid}.wav')
        if not os.path.exists(p): continue
        x, _ = librosa.load(p, sr=SR, mono=True)
        x = hp(x, 70, 2).astype(np.float32)
        i = int(s['t0'] * SR); m = min(len(x), N - i)
        vo[i:i + m] += x[:m]
        vo_spans.append((s['t0'], s['t0'] + len(x) / SR))
    if np.abs(vo).max() > 0:                                       # 解说：有声部分 RMS 统一到 −19 dBFS
        act = np.abs(vo) > 1e-4
        rms = np.sqrt(np.mean(vo[act] ** 2)); vo = vo / (rms + 1e-9) * 10 ** (-19.0 / 20)
    # ---------------------------------------------------------------- 闪避与推起
    e_clip = env(clip_spans, 0.45, 0.9)
    e_vo = env(vo_spans, 0.3, 0.7)
    duck = 1 - np.maximum(0.82 * e_clip, 0.70 * e_vo)            # 原声 −15dB，解说 −10.5dB
    pres = sosfiltfilt(butter(2, [1200, 4500], 'band', fs=SR, output='sos'), mus, axis=-1)
    mus = mus - 0.6 * pres * np.maximum(e_clip, e_vo)[None, :]   # 人声期间再挖开语音频段
    push = env([(seg['title']['t0'], seg['title']['t1']), (seg['G14']['t0'], seg['brand']['t1'])], 0.05, 1.5)
    mus = mus * duck * (1 + 0.25 * push)

    # ---------------------------------------------------------------- 低频音效（200Hz 以下）
    sfx = np.zeros(N, np.float32)

    def put(sig, t, g=1.0):
        i = int(t * SR)
        if 0 <= i < N:
            m = min(len(sig), N - i); sfx[i:i + m] += sig[:m] * g
    put(sub_drop(3.2, 60, 25, 1.0), seg['title']['t0'])
    put(boom(3.5, 100, 0.6, 1), seg['title']['t0'])
    for sid, kw, g in (('A04', '亏掉一半', 0.9), ('A06', '乘以一个零', 1.0), ('A03', '四百多倍', 0.6)):
        put(sub_drop(2.4, 58, 26, g), t3.wt(sid, kw))
    put(sub_drop(3.0, 62, 24, 1.0), seg['G14']['t0'])
    put(boom(3.5, 100, 0.6, 3), seg['G14']['t0'])
    for s in t3.SEGS:
        if s['kind'] == 'clip':
            put(thump(0.18, 75, 40, 0.6), s['a0'] - 0.4)
    beat = seg['G14']['t0'] + M['climax']['brand_beat'] - M['climax']['hit']
    put(sub_drop(2.6, 64, 28, 0.8), beat)
    sfx = lp(sfx, 200, 4)

    mix = mus + sfx[None, :] * 0.85 + (clip_v + vo)[None, :]
    loud = meter.integrated_loudness(mix.T)
    mix = mix * 10 ** ((-14.0 - loud) / 20)
    if np.abs(mix).max() > 0.89:
        mix = np.tanh(mix / 0.89) * 0.89
    end = seg['brand']['t1']
    k = int(2.2 * SR); i1 = int(end * SR)
    mix[:, i1 - k:i1] *= np.linspace(1, 0, k) ** 1.5
    mix[:, i1:] = 0
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sf.write(out, mix.T, SR, subtype='PCM_24')
    print('wrote', out, 'loudness', round(meter.integrated_loudness(mix.T), 1), 'LUFS peak', round(float(np.abs(mix).max()), 3))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
