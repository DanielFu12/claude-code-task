"""逐句合成旁白 -> work/vo/Lxx.wav（48k 单声道，裁掉首尾静音）并打印时长。"""
import os, sys, subprocess, concurrent.futures as cf
import numpy as np, soundfile as sf, librosa
sys.path.insert(0, os.path.dirname(__file__))
from script import LINES
from tts import synth
SPK = 'zh_male_m191_uranus_bigtts'
RATE = int(os.environ.get('RATE', '6'))
OUT = sys.argv[1] if len(sys.argv) > 1 else 'work/vo'
os.makedirs(OUT, exist_ok=True)
def one(L):
    i, text, sub, ctx, gap = L
    mp3 = f'{OUT}/{i}.mp3'; wav = f'{OUT}/{i}.wav'
    if not os.path.exists(mp3) or os.environ.get('FORCE'):
        for k in range(3):
            try: synth(SPK, text, mp3, rate=RATE, ctx=ctx); break
            except Exception as e: print('retry', i, e)
    y, sr = librosa.load(mp3, sr=48000)
    yt, idx = librosa.effects.trim(y, top_db=42, frame_length=1024, hop_length=128)
    a, b = max(idx[0] - 480, 0), min(idx[1] + 2400, len(y))
    y = y[a:b]
    # 响度归一：按有声部分的 RMS 对齐到 -20 dBFS，峰值不超过 -1 dBFS，避免句与句忽大忽小
    act = y[np.abs(y) > 0.02]
    rms = np.sqrt(np.mean(act ** 2)) if len(act) else 1e-3
    y = y * min(10 ** (-20 / 20) / rms, 10 ** (-1 / 20) / (np.abs(y).max() + 1e-9))
    sf.write(wav, y, 48000, subtype='FLOAT')
    return i, len(y) / 48000
with cf.ThreadPoolExecutor(6) as ex:
    res = list(ex.map(one, LINES))
tot = 0
for i, d in res: tot += d; print(i, round(d, 2))
print('speech total', round(tot, 1))
