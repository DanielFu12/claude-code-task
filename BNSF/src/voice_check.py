"""旁白自检（docs/旁白一致性与自然衔接.md 第三节）：在切好的逐句音频上
  · 各章语速（有声部分）与音高中位数（各章相差应 < 1.5 个半音）；
  · 相邻句的音高、响度、亮度跳变：一条录音里，跳变只来自正常语调；若集中出现在章节交界处，说明接缝有问题。
python3 src/voice_check.py WORK
"""
import sys, os, json, re
import numpy as np, soundfile as sf, librosa
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES

PUN = re.compile(r'[\s，。、：；？！“”‘’《》（）—…·,.;:?!"\'()\-]')
work = sys.argv[1]
vo = json.load(open(os.path.join(work, 'vo', 'vo.json')))
rows = []
for l in LINES:
    y, sr = sf.read(os.path.join(work, 'vo', l[0] + '.wav'), dtype='float32')
    m = vo[l[0]]; a, b = int(m['lead'] * sr), int((m['lead'] + m['dur']) * sr)
    seg = librosa.resample(y[a:b], orig_sr=sr, target_sr=16000)
    f0, vf, _ = librosa.pyin(seg, fmin=60, fmax=300, sr=16000, frame_length=1024, hop_length=160)
    f = f0[vf & np.isfinite(f0)]
    st = float(np.median(12 * np.log2(f / 100))) if len(f) else np.nan
    rms = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)
    cen = float(np.median(librosa.feature.spectral_centroid(y=seg, sr=16000)))
    n = len(PUN.sub('', l[3] or l[2]))
    rows.append(dict(id=l[0], ch=l[1], st=st, rms=rms, cen=cen, rate=n / m['dur']))
out = []
for ch in dict.fromkeys(r['ch'] for r in rows):
    rs = [r for r in rows if r['ch'] == ch]
    out.append(f"{ch}: 语速 {np.mean([r['rate'] for r in rs]):.2f} 字/秒；音高中位数 {100 * 2 ** (np.nanmedian([r['st'] for r in rs]) / 12):.1f} Hz")
chs = [np.nanmedian([r['st'] for r in rows if r['ch'] == ch]) for ch in dict.fromkeys(r['ch'] for r in rows)]
out.append(f'各章音高中位数最大相差 {max(chs) - min(chs):.2f} 个半音（要求 < 1.5）')
jumps = []
for p, q in zip(rows, rows[1:]):
    jumps.append((abs(q['st'] - p['st']), abs(q['rms'] - p['rms']), abs(q['cen'] - p['cen']) / p['cen'], q['id'], q['ch'] != p['ch']))
for k, name in ((0, '音高（半音）'), (1, '响度（dB）'), (2, '亮度（相对）')):
    v = np.array([j[k] for j in jumps]); brk = np.array([j[4] for j in jumps])
    top = sorted(jumps, key=lambda j: -j[k])[:3]
    out.append(f"相邻句{name}跳变：中位 {np.median(v):.2f}，章节交界处中位 {np.median(v[brk]):.2f}；最大：" + '、'.join(f"{j[3]} {j[k]:.2f}" for j in top))
open(os.path.join(work, 'vo', 'voice_check.txt'), 'w').write('\n'.join(out) + '\n')
print('\n'.join(out))
