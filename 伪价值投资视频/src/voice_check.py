"""旁白自检：逐句测音高中位数、响度、亮度（谱质心）、语速，列出相邻句之间的跳变，以及每章的语速。
用法：python3 src/voice_check.py work [vo目录]"""
import os, sys, re, json
import numpy as np, soundfile as sf, librosa
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES
W = sys.argv[1] if len(sys.argv) > 1 else 'work'
VO = sys.argv[2] if len(sys.argv) > 2 else f'{W}/vo'
SR = 48000
CHAP = [('序章', 'L01'), ('第一章', 'L16'), ('第二章', 'L70'), ('第三章', 'L85'), ('尾声', 'L90')]
rows = []
for i, text, sub, ctx, gap in LINES:
    y, _ = sf.read(f'{VO}/{i}.wav', dtype='float32')
    z = librosa.resample(y, orig_sr=SR, target_sr=16000)
    f0, vf, _ = librosa.pyin(z, fmin=70, fmax=320, sr=16000, frame_length=1024, hop_length=320)
    f = f0[vf & ~np.isnan(f0)]
    rms = librosa.feature.rms(y=z, frame_length=1024, hop_length=320)[0]
    act = rms > 0.1 * rms.max()
    cen = librosa.feature.spectral_centroid(y=z, sr=16000, n_fft=1024, hop_length=320)[0][:len(act)]
    n = len(re.sub(r'[^一-鿿0-9A-Za-z]', '', text))
    rows.append(dict(id=i, f0=float(np.median(f)) if len(f) else np.nan, db=float(20 * np.log10(np.sqrt(np.mean(z[np.abs(z) > 0.02] ** 2)) + 1e-9)),
                     cen=float(np.median(cen[act])), cps=n / (act.sum() * 0.02 + 1e-6), dur=len(y) / SR, n=n))
st = lambda a, b: 12 * np.log2(a / b)
print('%-5s %6s %6s %6s %6s' % ('id', 'ΔF0st', 'ΔdB', 'Δcen%', 'cps'))
flags = []
for k in range(1, len(rows)):
    a, b = rows[k - 1], rows[k]
    d = (st(b['f0'], a['f0']), b['db'] - a['db'], 100 * (b['cen'] / a['cen'] - 1))
    big = abs(d[0]) > 2.5 or abs(d[1]) > 3 or abs(d[2]) > 18
    if big: flags.append(b['id'])
    print('%-5s %+6.2f %+6.1f %+6.1f %6.2f %s' % (b['id'], *d, b['cps'], '<<' if big else ''))
print('flags:', flags)
ids = [r['id'] for r in rows]
for c, (name, s) in enumerate(CHAP):
    e = CHAP[c + 1][1] if c + 1 < len(CHAP) else None
    seg = rows[ids.index(s):ids.index(e) if e else None]
    print('%s 语速 %.2f 字/秒（有声部分），音高中位 %.0f Hz' % (name, sum(r['n'] for r in seg) / sum(r['n'] / r['cps'] for r in seg), np.nanmedian([r['f0'] for r in seg])))
