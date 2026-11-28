"""用停顿 + 离线识别给整篇录音找句界：对相邻两句，在接口逐字时间附近的每个停顿处切开，
取“左边识别结果以上一句末尾几个字结尾、右边以下一句开头几个字开头”的那个停顿正中。输出 CUT 字典。"""
import sys, os, re, json
import numpy as np, soundfile as sf, librosa, sherpa_onnx
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tts_take as T, voice_build as VB
from script import LINES
work = sys.argv[1]; ids = sys.argv[2].split(',')
D = os.path.join(work, 'asr', 'sherpa-onnx-paraformer-zh-small-2024-03-09') + '/'
rec = sherpa_onnx.OfflineRecognizer.from_paraformer(paraformer=D + 'model.int8.onnx', tokens=D + 'tokens.txt', num_threads=4)
tp = T.take_path(work); y, sr = sf.read(tp, dtype='float32'); mw = VB.map_words(json.load(open(tp[:-4] + '.json')))
order = [l[0] for l in LINES]; say = {l[0]: T.spoken(l) for l in LINES}
cn = lambda s: re.sub(r'[^一-鿿]', '', s)
def asr(a, b):
    x = librosa.resample(y[int(a * sr):int(b * sr)], orig_sr=sr, target_sr=16000)
    s = rec.create_stream(); s.accept_waveform(16000, x); rec.decode_stream(s); return cn(s.result.text)
hop = int(0.01 * sr)
out = {}
for i in ids:
    k = order.index(i); nx = order[k + 1]
    tb = [w for w in mw[nx] if w[0] != 'miss'][0][1]
    a0, a1 = tb - 2.5, tb + 2.0
    x = y[int(a0 * sr):int(a1 * sr)]
    e = np.array([np.sqrt(np.mean(x[j:j + hop] ** 2) + 1e-12) for j in range(0, len(x) - hop, hop)]); db = 20 * np.log10(e)
    sil = db < np.percentile(db, 95) - 24; cands = []; j = 0
    while j < len(sil):
        if sil[j]:
            q = j
            while q < len(sil) and sil[q]: q += 1
            if q - j >= 8: cands.append(a0 + (j + q) / 2 * 0.01)
            j = q
        else: j += 1
    endw, begw = cn(say[i])[-2:], cn(say[nx])[:2]
    best = None
    for m in cands:
        L, R = asr(m - 4, m), asr(m, m + 4)
        ok = L.endswith(endw) and R.startswith(begw)
        if ok and (best is None or abs(m - tb) < abs(best - tb)): best = m
    print(i, '|', nx, 'TTS', round(tb, 2), '→', None if best is None else round(best, 2), flush=True)
    if best is not None: out[i] = round(best, 2)
print(json.dumps(out))
