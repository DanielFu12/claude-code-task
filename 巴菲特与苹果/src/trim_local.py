"""离线剪除“多读前奏”：在开头各个停顿处试切，用 MMS 声学模型计算剪后音频与正文的 CTC 负对数似然（按帧数归一），
取最小者；原文件保留为 *_raw.wav。python3 src/trim_local.py WORK G01_6 G01_7 ...
"""
import sys, os, shutil
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tts_passage import GROUPS, PASSAGES, TEASE_P, spoken
from align import model, normalize, romanize

P = {p[0]: p for p in PASSAGES + [TEASE_P]}


def pauses(y, sr, min_len=0.35):
    w = int(0.02 * sr); e = np.sqrt(np.convolve(y ** 2, np.ones(w) / w, 'same'))
    db = 20 * np.log10(e + 1e-9); thr = np.percentile(db, 90) - 32
    sil = db < thr; out = []; i = 0
    while i < len(sil):
        if sil[i]:
            j = i
            while j < len(sil) and sil[j]: j += 1
            if (j - i) / sr >= min_len: out.append(((i + j) / 2) / sr)
            i = j
        else: i += 1
    return out


def score(y, sr, text):
    m, tok, aligner, msr, torch, ta = model()
    x = torch.tensor(y, dtype=torch.float32)[None]
    if sr != msr: x = ta.functional.resample(x, sr, msr)
    with torch.inference_mode(): em, _ = m(x)
    ids = [i for w in tok(romanize(normalize(text)[0])) for i in w]
    lp = torch.log_softmax(em[0], -1)
    return float(torch.nn.functional.ctc_loss(lp[:, None, :], torch.tensor([ids]), torch.tensor([lp.shape[0]]),
                                              torch.tensor([len(ids)]), blank=0, reduction='sum'))


if __name__ == '__main__':
    work = sys.argv[1]
    for take in sys.argv[2:]:
        g = take.split('_')[0]
        ref = ''.join(spoken(i) for pp in GROUPS[g] for i in P[pp][1])
        f = os.path.join(work, 'tts_p', take + '.wav'); raw = f.replace('.wav', '_raw.wav')
        y, sr = sf.read(raw if os.path.exists(raw) else f); y = y if y.ndim == 1 else y.mean(1)
        dur = len(y) / sr
        cands = [0.0] + [c for c in pauses(y, sr) if c < dur * 0.75]
        res = sorted((score(y[int(c * sr):], sr, ref), c) for c in cands)
        best = res[0]
        print(take, f'原长 {dur:.1f}s → 下刀 {best[1]:.2f}s（剩 {dur - best[1]:.1f}s），NLL {best[0]:.0f}，次优 {res[1][1]:.2f}s NLL {res[1][0]:.0f}', flush=True)
        if best[1] > 0:
            if not os.path.exists(raw): shutil.copy(f, raw)
            sf.write(f, y[int(best[1] * sr):], sr)
