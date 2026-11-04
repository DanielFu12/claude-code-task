"""去掉整段录音开头 TTS 偶发的“幻觉前奏”（与正文无关的多读内容）：
在开头的停顿处逐个尝试下刀，保留剩余时长最接近正文应有时长的那一刀，再用转写逐字校对（读音字错误率 ≤ 2%）。
原文件改名为 *_raw.wav 保留。python3 src/trim_preamble.py WORK G01 G07 ...
"""
import sys, os, re, glob, shutil
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tts_passage import GROUPS, PASSAGES, TEASE_P, spoken
from tts_gen import transcribe
from select_takes import cer

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


work = sys.argv[1]
for g in sys.argv[2:]:
    ref = ''.join(spoken(i) for pp in GROUPS[g] for i in P[pp][1])
    for f in sorted(glob.glob(os.path.join(work, 'tts_p', f'{g}_[0-9].wav'))):
        raw = f.replace('.wav', '_raw.wav')
        src = raw if os.path.exists(raw) else f
        y, sr = sf.read(src); y = y if y.ndim == 1 else y.mean(1)
        # 用同组其他（未被污染的）录音不可得时，按正文字数估计应有时长：读音单元 / 每秒 4.2
        from pypinyin import lazy_pinyin
        from align import normalize
        n = len(lazy_pinyin(''.join(normalize(ref)[0])))
        dur = len(y) / sr; expect = n / 4.2
        if dur < expect * 1.15: print(g, os.path.basename(f), f'{dur:.1f}s 正常'); continue
        cands = [c for c in pauses(y, sr) if c < dur - expect * 0.8]
        cands.sort(key=lambda c: abs((dur - c) - expect))
        done = False
        for c in cands[:4]:
            z = y[int(c * sr):]
            tmp = f.replace('.wav', '_trim.wav'); sf.write(tmp, z, sr)
            e = cer(ref, transcribe(tmp))
            print(g, os.path.basename(f), f'下刀 {c:.2f}s，剩 {dur - c:.1f}s（应约 {expect:.1f}s），字错误率 {e:.3f}', flush=True)
            if e <= 0.02:
                if not os.path.exists(raw): shutil.move(f, raw)
                shutil.move(tmp, f); done = True; break
            os.remove(tmp)
        if not done: print(g, os.path.basename(f), '未能干净切除', flush=True)
