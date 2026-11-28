"""拉平长录音的音高漂移（只修慢趋势，不动逐句抑扬）。
pYIN 估基频 → 有声帧换半音 → ±25 秒滑动中位数作趋势 → Praat Manipulation 把每个音高点乘 2^(-k·趋势/12) → PSOLA 重合成。
python3 src/detrend.py in.wav out.wav [target_hz=126] [k=0.9]
"""
import sys, numpy as np, soundfile as sf, librosa, parselmouth
from parselmouth.praat import call


def consensus_f0(y, sr, path=None):
    """三种基频估计（Praat 互相关 / YIN / pYIN）逐帧取一致值：三者最大最小之比 < 1.12 才采用，取中位数"""
    y16 = librosa.resample(y, orig_sr=sr, target_sr=16000); hop = 320
    f1, v1, _ = librosa.pyin(y16, fmin=65, fmax=240, sr=16000, frame_length=1024, hop_length=hop)
    f2 = librosa.yin(y16, fmin=65, fmax=240, sr=16000, frame_length=1024, hop_length=hop)
    t = np.arange(len(f1)) * hop / 16000
    snd = parselmouth.Sound(y16, 16000)
    pp = call(snd, 'To Pitch (cc)', 0.01, 65, 15, 'no', 0.03, 0.45, 0.01, 0.35, 0.14, 240)
    f3 = np.interp(t, pp.xs(), pp.selected_array['frequency'])
    F = np.stack([np.where(v1, f1, np.nan), f2, np.where(f3 > 0, f3, np.nan)], 1)
    ok = np.all(np.isfinite(F), 1) & (np.nanmax(F, 1) / np.nanmin(F, 1) < 1.12)
    return t, np.where(ok, np.nanmedian(F, 1), np.nan)


def trend_semitones(y, sr, target):
    t, f = consensus_f0(y, sr)
    st = 12 * np.log2(f / target)
    tr = np.full_like(st, np.nan)
    for i in range(0, len(st)):
        w = st[max(0, i - 1250):i + 1250]; w = w[np.isfinite(w)]
        if len(w) > 50: tr[i] = np.median(w)
    ok = np.isfinite(tr); tr = np.interp(t, t[ok], tr[ok])
    return t, tr


def detrend(inp, out, target=126.0, k=0.9):
    y, sr = sf.read(inp)
    t, tr = trend_semitones(y, sr, target)
    snd = parselmouth.Sound(inp)
    man = call(snd, 'To Manipulation', 0.01, 60, 300)
    pt = call(man, 'Extract pitch tier')
    n = call(pt, 'Get number of points')
    pts = [(call(pt, 'Get time from index', i), call(pt, 'Get value at index', i)) for i in range(1, n + 1)]
    call(pt, 'Remove points between', 0, snd.duration + 1)
    for tt, f in pts:
        call(pt, 'Add point', tt, f * 2 ** (-k * np.interp(tt, t, tr) / 12))
    call([man, pt], 'Replace pitch tier')
    res = call(man, 'Get resynthesis (overlap-add)')
    z = res.values[0]
    z = z * (np.sqrt(np.mean(y ** 2)) / (np.sqrt(np.mean(z ** 2)) + 1e-12))
    sf.write(out, z.astype(np.float32), int(res.sampling_frequency))
    return t, tr


if __name__ == '__main__':
    a = sys.argv
    t, tr = detrend(a[1], a[2], float(a[3]) if len(a) > 3 else 126.0, float(a[4]) if len(a) > 4 else 0.9)
    print('trend range %.1f..%.1f st' % (tr.min(), tr.max()))
