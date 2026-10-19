"""分析三段配乐，找出卡点用的重拍，写入 assets/music3/music3.json。

重拍 = 低频（< 200Hz）能量的最大突增点（在提示词指定时间附近 ±6 秒内找）。
用法：python3 src/music3.py hook=<file> bed=<file> climax=<file>
"""
import json, os, sys
import numpy as np, librosa

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MDIR = os.path.join(ROOT, 'assets', 'music3')
SR = 22050


def low_env(path):
    y, _ = librosa.load(path, sr=SR, mono=True)
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=256))
    f = librosa.fft_frequencies(sr=SR, n_fft=2048)
    lo = S[f < 200].sum(0)
    full = S.sum(0)
    t = librosa.frames_to_time(np.arange(S.shape[1]), sr=SR, hop_length=256)
    return y, t, lo, full


def hit_near(path, guess, span=6.0):
    y, t, lo, full = low_env(path)
    d = np.maximum(np.diff(np.log(lo + 1e-6), prepend=0), 0) * (lo / lo.max())   # 低频能量突增 × 能量本身
    m = (t > guess - span) & (t < guess + span)
    i = np.argmax(d * m)
    return float(t[i]), float(librosa.get_duration(y=y, sr=SR))


def beats(path):
    y, _ = librosa.load(path, sr=SR, mono=True)
    tempo, b = librosa.beat.beat_track(y=y, sr=SR, units='time')
    return float(np.atleast_1d(tempo)[0]), b.tolist()


def main(files):
    M = {}
    hk = files['hook']; h, d = hit_near(os.path.join(MDIR, hk), 47.0)
    M['hook'] = dict(file=hk, hit=round(h, 3), dur=round(d, 2))
    cl = files['climax']; c, d = hit_near(os.path.join(MDIR, cl), 88.0, 8.0)
    f, _ = hit_near(os.path.join(MDIR, cl), c + 12.0, 4.0)
    tempo, bt = beats(os.path.join(MDIR, cl))
    M['climax'] = dict(file=cl, hit=round(c, 3), final=round(f, 3), dur=round(d, 2), tempo=round(tempo, 1))
    bd = files['bed']
    _, d = hit_near(os.path.join(MDIR, bd), 10.0)
    M['bed'] = dict(file=bd, dur=round(d, 2), start=0.0, loop=40.0, gain=1.0)
    json.dump(M, open(os.path.join(MDIR, 'music3.json'), 'w'), indent=1)
    print(json.dumps(M, indent=1))


if __name__ == '__main__':
    main(dict(a.split('=', 1) for a in sys.argv[1:]))
