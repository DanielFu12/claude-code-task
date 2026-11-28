"""旁白一致性验收（逐句测量，按段汇总）。
每句单独用 Praat 互相关法测音高（65–240 Hz），再取段内各句的中位数；接缝 = 本段第一句 − 上一段最后一句。
同时给出频谱倾斜（发声用力）、谐噪比、有声响度。python3 src/voice_qc.py WORK"""
import sys, os, json, numpy as np, soundfile as sf, librosa, parselmouth
from parselmouth.praat import call
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES
WORK = sys.argv[1]; rep = json.load(open(os.path.join(WORK, 'vo_report.json')))['report']
ids = [l[0] for l in LINES]; chunk_of = {}
for r in rep:
    for lid in ids[ids.index(r[1]):ids.index(r[2]) + 1]: chunk_of[lid] = r[0]
line = {}
for lid in ids:
    y, sr = sf.read(os.path.join(WORK, 'vo', lid + '.wav')); snd = parselmouth.Sound(y, sr)
    p = call(snd, 'To Pitch (cc)', 0.01, 65, 15, 'no', 0.03, 0.45, 0.01, 0.35, 0.14, 240); pf = p.selected_array['frequency']
    y16 = librosa.resample(y, orig_sr=sr, target_sr=16000); S = np.abs(librosa.stft(y16, n_fft=1024, hop_length=320))
    rms = librosa.feature.rms(S=S, frame_length=1024)[0]; v = rms > np.percentile(rms, 40)
    fr = librosa.fft_frequencies(sr=16000, n_fft=1024); P = (S ** 2)[:, v].mean(1)
    tilt = 10 * np.log10(P[(fr >= 60) & (fr < 1000)].sum() / P[(fr >= 1000) & (fr < 4000)].sum())
    hnr = call(call(snd, 'To Harmonicity (cc)', 0.01, 75, 0.1, 1.0), 'Get mean', 0, 0)
    line[lid] = dict(f0=float(np.median(pf[pf > 0])), tilt=tilt, hnr=hnr, db=20 * np.log10(np.median(rms[v])), dur=len(y) / sr)
ref = np.median([line[l]['f0'] for l in ids]); tl = np.median([line[l]['tilt'] for l in ids]); dbr = np.median([line[l]['db'] for l in ids])
print('全片逐句音高中位数 %.1f Hz（Praat）' % ref)
print('段  起止        音高st  倾斜dB  HNR   响度dB  接缝st')
rows = []
for ci in sorted(set(chunk_of.values())):
    L = [l for l in ids if chunk_of[l] == ci]
    st = 12 * np.log2(np.median([line[l]['f0'] for l in L]) / ref)
    seam = 12 * np.log2(line[L[0]]['f0'] / line[prev_last]['f0']) if ci else 0.0
    rows.append(st); prev_last = L[-1]
    print('%2d  %-4s-%-4s  %+5.2f  %+5.2f  %4.1f  %+5.2f  %+5.2f' % (ci, L[0], L[-1], st, np.median([line[l]['tilt'] for l in L]) - tl,
          np.median([line[l]['hnr'] for l in L]), np.median([line[l]['db'] for l in L]) - dbr, seam))
# 逐句相邻跳变：段内 vs 接缝（接缝不应明显大于段内的正常起伏）
inner = []; seams = []
for a, b in zip(ids, ids[1:]):
    d = abs(12 * np.log2(line[b]['f0'] / line[a]['f0'])); (seams if chunk_of[a] != chunk_of[b] else inner).append(d)
print('段内相邻句音高差：中位 %.2f、90%% 分位 %.2f 半音；接缝：中位 %.2f、最大 %.2f 半音' % (np.median(inner), np.percentile(inner, 90), np.median(seams), max(seams)))
print('各段音高范围 %.2f 半音；HNR %.1f–%.1f dB' % (max(rows) - min(rows), min(line[l]['hnr'] for l in ids), max(line[l]['hnr'] for l in ids)))
