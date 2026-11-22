"""旁白 + 配乐混音与母带：旁白出现时配乐自动闪避（中频额外让位），最终响度约 -14 LUFS。"""
import json, os, sys
import numpy as np, soundfile as sf
from scipy.signal import resample_poly

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dsp import SR, follow, compress, limiter, sos_filter, peak, shelf

WORK = os.path.join(HERE, '..', 'work')


def run(out='final_audio.wav'):
    tl = json.load(open(os.path.join(WORK, 'timeline.json')))
    T = tl['total']
    st = np.load(os.path.join(WORK, 'music_stems.npz'))
    music, acc = st['music'], st['acc']
    N = int(T * SR)
    music, acc = music[:N], acc[:N]
    # ---- voice
    from tts import trim
    v = np.zeros(N, np.float32)
    for s in tl['scenes']:
        for u in s['utts']:
            y, sr = sf.read(os.path.join(WORK, u['wav']))
            if y.ndim > 1: y = y.mean(1)
            y, _ = trim(y)
            y = resample_poly(y, 147, 80).astype(np.float32)   # 24k -> 44.1k
            i = int(u['start'] * SR)
            n = min(len(y), N - i)
            v[i:i + n] += y[:n]
    v = sos_filter(v, 'highpass', 75)
    v = peak(v, 3200, 1.5, 0.9)          # 清晰度
    v = peak(v, 4800, 2.0, 1.0)          # 穿透力
    v = shelf(v, 180, 1.5, 'low')         # 厚度
    v = compress(v, -22, 2.5, 0.005, 0.12, 0)
    rms = np.sqrt(np.mean(v[np.abs(v) > 0.01] ** 2))
    v = v / rms * 10 ** (-17 / 20)        # 旁白 RMS ≈ -17 dBFS
    # ---- ducking
    env = follow(np.abs(v).astype(np.float32), 0.02, 0.35)
    act = np.clip(env / 0.035, 0, 1)
    act = follow(act.astype(np.float32), 0.06, 0.5)
    duck_all = 10 ** (-9.5 * act / 20)
    duck_mid = 10 ** (-5.0 * act / 20)
    # 中频（人声区）额外让位
    mlow = sos_filter(music, 'lowpass', 150)
    mhigh = sos_filter(music, 'highpass', 4500)
    mlm = sos_filter(music, 'bandpass', [150, 900])
    mmid = music - mlow - mhigh - mlm
    duck_lm = 10 ** (-5.0 * act / 20)
    music_d = (mlow + mhigh + mlm * duck_lm[:, None] + mmid * duck_mid[:, None]) * duck_all[:, None]
    acc_d = acc * (10 ** (-5.0 * act / 20))[:, None]
    # 配乐整体电平：无旁白段 ≈ -15 dBFS RMS
    mus = music_d + acc_d
    ref = np.sqrt(np.mean(music ** 2))
    mus *= 10 ** (-17.0 / 20) / (ref + 1e-9)
    mix = mus + v[:, None] * np.array([1.0, 1.0])[None, :]
    # ---- master
    mix = compress(mix, -10, 1.6, 0.02, 0.25, 0)
    mix = limiter(mix, 0.93)
    try:
        import pyloudnorm as pyln
        meter = pyln.Meter(SR)
        L = meter.integrated_loudness(mix)
        mix = mix * 10 ** ((-14.5 - L) / 20)
        mix = limiter(mix, 0.95)
        print('loudness', L, '->', meter.integrated_loudness(mix))
    except Exception as e:
        print('loudnorm skipped', e)
    f = int(3.0 * SR)
    mix[-f:] *= np.linspace(1, 0, f)[:, None] ** 2
    sf.write(os.path.join(WORK, out), mix, SR, subtype='PCM_16')
    sf.write(os.path.join(WORK, 'voice.wav'), v, SR, subtype='PCM_16')
    print('mix done', mix.shape, np.abs(mix).max())


if __name__ == '__main__':
    run()
