"""分章音高校平（宪章 三.2：拉平长文本的音高漂移）：3.0 音色按章整录，个别章整体偏高。
逐句测 pYIN 中位基频，按章算相对开场的半音差；超过 1 个半音的章，用 Praat PSOLA（Change gender，共振峰与时长不变）把该章各句整体移回到开场附近。
在 voice_build.py 之后、timeline.py 之前运行：python3 src/pitch_level.py WORK"""
import sys, os, json
import numpy as np, soundfile as sf, librosa, parselmouth
from parselmouth.praat import call
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES
work = sys.argv[1]
def f0med(y, sr):
    f0, _, _ = librosa.pyin(librosa.resample(y.astype(np.float32), orig_sr=sr, target_sr=16000), fmin=60, fmax=300, sr=16000, frame_length=1024, hop_length=160)
    return float(np.nanmedian(f0))
med = {}; chs = {}
for l in LINES:
    y, sr = sf.read(os.path.join(work, 'vo', l[0] + '.wav')); y = y if y.ndim == 1 else y.mean(1)
    med[l[0]] = f0med(y, sr); chs.setdefault(l[1], []).append(l[0])
ref = np.median([med[i] for i in chs['hook']] + [med[i] for i in chs.get('ch1', [])])
report = {}
for ch, ids in chs.items():
    cm = np.median([med[i] for i in ids]); st = 12 * np.log2(cm / ref)
    report[ch] = round(float(st), 2)
    if abs(st) <= 1.0: continue
    target_ratio = 2 ** ((-st + 0.4 * np.sign(st)) / 12)          # 移回到距参考 0.4 个半音以内
    for i in ids:
        p = os.path.join(work, 'vo', i + '.wav')
        snd = parselmouth.Sound(p)
        new = call(snd, 'Change gender', 60, 300, 1.0, med[i] * target_ratio, 1.0, 1.0)
        y = new.values.T.squeeze(); sf.write(p, y.astype(np.float32), int(new.sampling_frequency), subtype='PCM_16')
    print(f'{ch}: {st:+.2f} 半音 → 移 {12 * np.log2(target_ratio):+.2f}', flush=True)
json.dump(report, open(os.path.join(work, 'vo', 'pitch_level.json'), 'w'))
print('各章相对参考（修正前）', report)
