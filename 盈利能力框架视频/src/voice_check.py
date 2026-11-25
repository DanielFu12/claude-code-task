"""旁白自检：各章语速 / 音高、章节留白、旁白与配乐的响度差。"""
import json, os, sys
import numpy as np, soundfile as sf, librosa
WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'work')
tl = json.load(open(os.path.join(WORK, 'timeline.json')))
v, sr = sf.read(os.path.join(WORK, 'voice.wav')); v = v.mean(1)
mix, _ = sf.read(os.path.join(WORK, 'final_audio.wav')); mix = mix.mean(1)
music, _ = sf.read(os.path.join(WORK, 'music_bed.wav')); music = music.mean(1)
chap = {}
for s in tl['scenes']:
    for u in s['utts']:
        chap.setdefault(s['ch'], []).append(u)
print('章节   字/秒(含停顿)  音高中位数Hz')
meds = []
for ch, us in chap.items():
    chars = sum(len([c for c in u['text'] if c.isalnum()]) for u in us)
    dur = sum(u['end'] - u['start'] for u in us)
    seg = np.concatenate([v[int(u['start'] * sr):int(u['end'] * sr)] for u in us])
    y = librosa.resample(seg.astype(np.float32), orig_sr=sr, target_sr=16000)
    f0, vf, _ = librosa.pyin(y, fmin=60, fmax=300, sr=16000)
    m = float(np.nanmedian(f0[vf])); meds.append(m)
    print(f'{ch:6s} {chars / dur:5.2f}  {m:6.1f}')
print('各章音高差（半音）', round(12 * np.log2(max(meds) / min(meds)), 2))
# 章节留白：上一句结束到下一句开始
us = [u for s in tl['scenes'] for u in s['utts']]
gaps = [(round(b['start'] - a['end'], 2), b['text'][:10]) for a, b in zip(us, us[1:]) if b['start'] - a['end'] > 0.05]
print('句间插入的留白（秒）', gaps)
# 说话时旁白比配乐高多少
hop = sr // 10
def rms(x): return np.sqrt(np.convolve(x ** 2, np.ones(hop) / hop, 'same')[::hop] + 1e-12)
rv, rm = rms(v[:len(mix)]), rms(music)
sp = rv > 10 ** (-30 / 20)
print('说话时 旁白-配乐 平均差 dB', round(float(np.median(20 * np.log10(rv[sp] / rm[sp]))), 1))
