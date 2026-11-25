"""旁白 + 配乐混音与母带（第三版）。

- 旁白是整篇一条录音切开再按时间轴摆放，段内不做任何修剪。
- 旁白：70 Hz 高通、2.2:1 轻压缩、同一个小房间的短混响（RT60≈0.6 s，湿声 0.1）、−64 dBFS 粉噪底。
- 闪避放在最后一步（母带压缩之后）：人声时全频 −12 dB，人声频段 700 Hz–4 kHz 再 −5 dB；
  提前 0.15 s 开始压、保持 0.9 s，起 80 ms、放 550 ms。
- 响度：线性增益到 −14 LUFS + 峰值限制。
"""
import json, os, sys
import numpy as np, soundfile as sf
from scipy.signal import resample_poly
from scipy.ndimage import maximum_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dsp import SR, follow, compress, limiter, sos_filter, make_ir, reverb, peak

WORK = os.path.join(HERE, '..', 'work')


def run(out='final_audio.wav'):
    tl = json.load(open(os.path.join(WORK, 'timeline.json')))
    T = tl['total']
    st = np.load(os.path.join(WORK, 'music_stems.npz'))
    N = int(T * SR)
    music = st['music'][:N] + st['acc'][:N]
    # ---- voice
    v = np.zeros(N, np.float32)
    for s in tl['scenes']:
        for u in s['utts']:
            y, sr = sf.read(os.path.join(WORK, u['wav']))
            if y.ndim > 1: y = y.mean(1)
            y = resample_poly(y, 147, 80).astype(np.float32)   # 24k -> 44.1k
            f = int(0.008 * SR)                                   # 切点都在停顿里，只做极短的防咔哒淡入淡出
            y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f)
            i = int(round(u['start'] * SR))
            n = min(len(y), N - i)
            v[i:i + n] += y[:n]
    v = sos_filter(v, 'highpass', 70)
    v = peak(v, 4500, 1.5, 1.0)
    v = compress(v, -24, 2.2, 0.01, 0.15, 0)
    act = np.abs(v) > 0.01
    v = v / (np.sqrt(np.mean(v[act] ** 2)) + 1e-9) * 10 ** (-17 / 20)
    room = make_ir(0.6, 0.008, 6000, seed=9)
    vs = np.stack([v, v], 1)
    vs = vs + reverb(vs, room, 0.10)
    rng = np.random.default_rng(4)
    pink = np.cumsum(rng.standard_normal((N, 2)).astype(np.float32), 0)
    pink = sos_filter(pink, 'highpass', 40)
    pink = pink / (np.sqrt(np.mean(pink ** 2)) + 1e-9) * 10 ** (-64 / 20)
    vs = vs + pink
    # ---- 配乐电平与母带压缩（闪避之前）
    music = music / (np.sqrt(np.mean(music ** 2)) + 1e-9) * 10 ** (-17 / 20)
    music = compress(music, -14, 1.8, 0.02, 0.25, 0)
    # ---- 闪避（压缩之后）
    env = (np.abs(v) > 10 ** (-38 / 20)).astype(np.float32)
    hold = int(0.9 * SR); pre = int(0.15 * SR)
    env = maximum_filter1d(env, size=hold + pre, origin=-(hold - pre) // 2)
    g = follow(env, 0.08, 0.55)
    duck_all = 10 ** (-14 * g / 20)
    duck_band = 10 ** (-5 * g / 20)
    band = sos_filter(music, 'bandpass', [700, 4000])
    music = (music - band + band * duck_band[:, None]) * duck_all[:, None]
    mix = music + vs
    try:
        import pyloudnorm as pyln
        meter = pyln.Meter(SR)
        L = meter.integrated_loudness(mix)
        gl = 10 ** ((-14 - L) / 20)
        mix, music, vs = mix * gl, music * gl, vs * gl
    except Exception as e:
        print('loudness skipped', e)
    mix = limiter(mix, 0.95)
    f = int(3.0 * SR)
    mix[-f:] *= np.linspace(1, 0, f)[:, None] ** 2
    sf.write(os.path.join(WORK, out), mix, SR, subtype='PCM_16')
    sf.write(os.path.join(WORK, 'voice.wav'), vs, SR, subtype='PCM_16')
    sf.write(os.path.join(WORK, 'music_bed.wav'), music, SR, subtype='PCM_16')
    try:
        print('final loudness', round(meter.integrated_loudness(mix), 2))
    except Exception:
        pass


if __name__ == '__main__':
    run()
