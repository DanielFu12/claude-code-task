"""音色指纹：MFCC（2–20 阶，均值与标准差）+ 音高中位数 + 频谱质心，只在有声帧上统计。
用全片所有候选录音的“中位数指纹”作为同一个讲述者的基准，挑最接近的录音；不变调、不拼接。
python3 src/timbre.py WORK [G01 ...]      # 打印各候选与基准的距离，写 work/tts_p/timbre.json
"""
import sys, os, glob, json, re
import numpy as np, librosa


def fp(path):
    y, sr = librosa.load(path, sr=16000)
    f0, vf, _ = librosa.pyin(y, fmin=60, fmax=300, sr=sr, frame_length=1024, hop_length=320)
    m = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=21, n_fft=1024, hop_length=320)[1:]
    n = min(m.shape[1], len(vf)); v = vf[:n]
    mv = m[:, :n][:, v] if v.sum() > 50 else m
    cen = librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=1024, hop_length=320)[0][:n]
    return np.concatenate([mv.mean(1), mv.std(1), [np.log(np.nanmedian(f0)) * 40, np.median(cen[v] if v.sum() > 50 else cen) / 40]])


if __name__ == '__main__':
    work = sys.argv[1]; d = os.path.join(work, 'tts_p')
    cache_p = os.path.join(d, 'timbre.json'); cache = json.load(open(cache_p)) if os.path.exists(cache_p) else {}
    files = sorted(f for f in glob.glob(os.path.join(d, 'G*_[0-9].wav')))
    for f in files:
        k = os.path.basename(f)
        if k not in cache or cache[k]['mtime'] != os.path.getmtime(f):
            cache[k] = dict(fp=fp(f).tolist(), mtime=os.path.getmtime(f))
    json.dump(cache, open(cache_p, 'w'))
    X = np.array([v['fp'] for v in cache.values()]); ref = np.median(X, 0); sd = X.std(0) + 1e-6
    want = sys.argv[2:]
    for k in sorted(cache):
        if want and not any(k.startswith(w) for w in want): continue
        dist = float(np.sqrt((((np.array(cache[k]['fp']) - ref) / sd) ** 2).mean()))
        print(k, f'距离 {dist:.2f}  音高 {np.exp(cache[k]["fp"][-2] / 40):.1f}Hz')
