"""解说声纹一致性：用 Resemblyzer（GE2E 说话人编码器）比较各段解说与参照段的声纹余弦相似度，并给出基频与亮度。
用法：python3 tools/voice_sim.py REF.wav[+REF2.wav] A.wav B.wav ...
"""
import sys, types
_pr = types.ModuleType('pkg_resources')           # webrtcvad 导入时只读一下版本号，新版 setuptools 已移除 pkg_resources
_pr.get_distribution = lambda name: types.SimpleNamespace(version='0')
sys.modules.setdefault('pkg_resources', _pr)
import numpy as np, librosa
from resemblyzer import VoiceEncoder, preprocess_wav

_ENC = None


def embed(path):
    global _ENC
    if _ENC is None: _ENC = VoiceEncoder('cpu', verbose=False)
    return _ENC.embed_utterance(preprocess_wav(load(path), 16000))


def load(paths):
    """一个或多个文件（多个时首尾相接，作为同一参照）"""
    paths = [paths] if isinstance(paths, str) else paths
    return np.concatenate([librosa.load(p, sr=16000)[0] for p in paths])


def stats(path):
    y, sr = load(path), 16000
    f0, v, _ = librosa.pyin(y, fmin=60, fmax=300, sr=sr)
    f0 = f0[v & ~np.isnan(f0)]
    cen = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    q = np.percentile(f0, [25, 50, 75])
    return dict(f0=float(q[1]), f0_q=[float(v) for v in q], f0_iqr=float(q[2] - q[0]), centroid=float(np.median(cen)))


def f0_dev(s, ref):
    """基频分布（四分位）与参照的平均相对偏离：只看中位数容易被八度跳变误导"""
    return float(np.mean([abs(a - b) / b for a, b in zip(s['f0_q'], ref['f0_q'])]))


def sim(a, b):
    return float(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b))


PUNCT = '，。；：？！、—…“”《》·（）,.;:?! '


def profile(path, text):
    """更贴近听感的声色画像：声纹、平均 MFCC（音色）、基频分布（半音）、语速（每秒字数，不含停顿）、亮度"""
    y = load(path); sr = 16000
    f0, v, _ = librosa.pyin(y, fmin=70, fmax=300, sr=sr, frame_length=1024)
    st = 12 * np.log2(f0[v & ~np.isnan(f0)] / 100)
    db = 20 * np.log10(librosa.feature.rms(y=y, frame_length=512, hop_length=160)[0] + 1e-9)
    sp = db > db.max() - 35
    S = np.abs(librosa.stft(y, n_fft=1024, hop_length=160))[:, :len(sp)]
    vs = S[:, sp[:S.shape[1]]]
    mf = librosa.feature.mfcc(S=librosa.power_to_db(librosa.feature.melspectrogram(S=vs ** 2, sr=sr)), n_mfcc=14)[1:].mean(1)
    n = len([c for c in text if c not in PUNCT and not c.isspace()])
    return dict(emb=embed(path), mfcc=mf, st=np.percentile(st, [10, 50, 90]), rate=n / (sp.mean() * len(y) / sr),
                cen=float(np.median(librosa.feature.spectral_centroid(S=vs, sr=sr)[0])))


def distance(a, r, pitch_unit=0.8):
    """与参照的综合距离（越小越像）：各项按「听得出差别」的量级归一后相加。
    pitch_unit：音高差多少半音算 1 分（第五版起用 0.5——被指出声色不一致的段落都是偏低沉）"""
    d = dict(emb=(1 - sim(a['emb'], r['emb'])) / 0.04, mfcc=float(np.linalg.norm(a['mfcc'] - r['mfcc'])) / 12,
             pitch=abs(a['st'][1] - r['st'][1]) / pitch_unit, range=abs(a['st'][2] - r['st'][2]) / 1.5,
             rate=abs(a['rate'] - r['rate']) / 0.4, bright=abs(a['cen'] - r['cen']) / 120)
    return sum(d.values()), d


if __name__ == '__main__':
    refp = sys.argv[1].split('+')                 # 参照可以是多个文件：a.wav+b.wav
    ref = embed(refp); rs = stats(refp)
    print(f"REF {sys.argv[1]}  F0 {rs['f0']:.0f}Hz  IQR {rs['f0_iqr']:.0f}  亮度 {rs['centroid']:.0f}Hz")
    for p in sys.argv[2:]:
        s = stats(p)
        print(f"{sim(ref, embed(p)):.3f}  F0 {s['f0']:.0f}Hz  IQR {s['f0_iqr']:.0f}  偏离 {f0_dev(s, rs):.0%}  亮度 {s['centroid']:.0f}Hz  {p}")
