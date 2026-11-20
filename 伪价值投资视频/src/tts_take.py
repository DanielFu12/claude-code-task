"""整篇旁白一次合成（一条录完）-> 按句切开 -> work/vo/Lxx.wav + work/vo/gaps.json（V10）

为什么：逐句、逐段合成时，每次请求的音色、音高、能量都各自起落，接缝处像换了一个人。
整篇只请求一次，全片就是同一条录音；后期不再做任何分段的移调或均衡，只有一个整体增益。

切句：Seed-TTS 2.0 不返回时间戳。逐句参考音频（tts_all.py，同一音色、同一语速）与整条录音做
逐句推进的子序列 DTW：把「本句 + 下一句开头」对齐到录音的一个窗口里，得到句界，再吸附到附近停顿的正中。
每一句再做校验（与本句参考最像，比相邻两句都像；时长比 0.7~1.4），不通过就整条重录。

第三章放慢：用 Praat 的 PSOLA 时长变换（不改音高）把这一章拉长，句间停顿也相应变长。"""
import os, sys, json, hashlib
import numpy as np, soundfile as sf, librosa
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, TONE
from tts import synth

SPK = 'zh_male_m191_uranus_bigtts'
RATE = int(os.environ.get('RATE', '25'))
W = sys.argv[1] if len(sys.argv) > 1 else 'work'
OUT, REF, CACHE = f'{W}/vo', f'{W}/vo_ref', f'{W}/vo_take'
os.makedirs(OUT, exist_ok=True); os.makedirs(CACHE, exist_ok=True)
SR = 48000
HOP = 320 / 16000
# 章节卡 / 小节转场：这些句子之前允许插入停顿（timeline.py 在这里放章节卡、片名、音乐呼吸）
BREAKS = ['L16', 'L25', 'L44', 'L61', 'L70', 'L85', 'L90']
# 放慢：第三章明显放慢，尾声略放慢
SLOW = {**{f'L{k}': 1.2 for k in range(85, 90)}, **{f'L{k}': 1.05 for k in range(90, 96)}}


def feat(y):
    z = librosa.resample(y, orig_sr=SR, target_sr=16000)
    m = librosa.feature.mfcc(y=z, sr=16000, n_mfcc=20, hop_length=320)[1:]
    return (m - m.mean(1, keepdims=True)) / (m.std(1, keepdims=True) + 1e-6)


def silences(y, thr_db=-34, min_len=0.05):
    hop = 240; n = len(y) // hop
    r = np.sqrt(np.mean(y[:n * hop].reshape(n, hop) ** 2, 1) + 1e-12)
    ref = np.percentile(r, 95)
    s = 20 * np.log10(r / ref + 1e-9) < thr_db
    out, k = [], 0
    while k < n:
        if s[k]:
            j = k
            while j < n and s[j]: j += 1
            if (j - k) * hop / SR >= min_len: out.append((k * hop / SR, j * hop / SR))
            k = j
        else: k += 1
    return out


def take():
    text = ''.join(L[1] for L in LINES)
    h = hashlib.md5((SPK + str(RATE) + TONE + text).encode()).hexdigest()[:10]
    mp3 = f'{CACHE}/take_{h}.mp3'
    if not os.path.exists(mp3):
        for k in range(4):
            try: synth(SPK, text, mp3, rate=RATE, ctx=TONE); break
            except Exception as e: print('retry', e, flush=True)
    y, _ = librosa.load(mp3, sr=SR)
    return y, mp3


def align(y, refs):
    """逐句推进：返回每个句界的停顿 (起, 止)（秒），以及首尾"""
    sil = silences(y)
    a0 = sil[0][1] if sil and sil[0][0] < 0.05 else 0.0
    a1 = sil[-1][0] if sil and sil[-1][1] > len(y) / SR - 0.05 else len(y) / SR
    Fy = feat(y)
    Fr = [feat(r) for r in refs]
    cur = a0; bounds = []
    for k in range(len(refs) - 1):
        nxt = Fr[k + 1][:, :int(1.5 / HOP)]
        X = np.hstack([Fr[k], nxt])
        dk = refs[k].shape[0] / SR
        i0 = max(0, int((cur - 0.4) / HOP)); i1 = min(Fy.shape[1], int((cur + 1.6 * dk + 3.0) / HOP))
        Y = Fy[:, i0:i1]
        D, wp = librosa.sequence.dtw(X, Y, metric='cosine', subseq=True)
        wp = wp[::-1]
        b = Fr[k].shape[1]
        ys = wp[wp[:, 0] == b, 1]
        tb = (i0 + (np.median(ys) if len(ys) else wp[np.argmin(np.abs(wp[:, 0] - b)), 1])) * HOP
        near = [s for s in sil if s[0] - 0.35 < tb < s[1] + 0.35 and s[0] > cur + 0.3]
        if near:
            s = max(near, key=lambda q: min(q[1] - q[0], 0.4) - 0.8 * abs((q[0] + q[1]) / 2 - tb))
        else:
            s = (tb - 0.02, tb + 0.02)
        bounds.append(s); cur = s[1]
    return bounds, a0, a1


def check(y, bounds, a0, a1, refs):
    cut = [a0] + [(q[0] + q[1]) / 2 for q in bounds] + [a1]
    segs = [y[int(cut[k] * SR):int(cut[k + 1] * SR)] for k in range(len(refs))]
    Fs = [feat(g) for g in segs]; Rs = [feat(r) for r in refs]
    def d(a, b):
        D, wp = librosa.sequence.dtw(a, b, metric='cosine'); return D[-1, -1] / len(wp)
    bad = []
    for k in range(len(refs)):
        ratio = len(segs[k]) / len(refs[k])
        d0 = d(Fs[k], Rs[k])
        nb = [d(Fs[k], Rs[j]) for j in (k - 1, k + 1) if 0 <= j < len(refs)]
        if not 0.7 < ratio < 1.4 or min(nb) < d0 * 1.02: bad.append((LINES[k][0], round(ratio, 2), round(d0, 3), [round(x, 3) for x in nb]))
    return bad


def detrend_pitch(y, target=128.0, amount=0.9, win=25.0):
    """长文本合成会越讲越高（实测首尾差 3~4 个半音）。用 Praat PSOLA 只拉平缓慢的音高趋势（±25 秒滑动中位数），
    逐句的抑扬顿挫不动；PSOLA 保留共振峰，音色不变。"""
    import parselmouth
    from parselmouth.praat import call
    snd = parselmouth.Sound(y.astype(np.float64), SR)
    man = call(snd, 'To Manipulation', 0.01, 60, 300)
    pt = call(man, 'Extract pitch tier')
    n = call(pt, 'Get number of points')
    T = np.array([call(pt, 'Get time from index', i) for i in range(1, n + 1)])
    F = np.array([call(pt, 'Get value at index', i) for i in range(1, n + 1)])
    # 趋势用 pYIN 估计（比 Praat 的音高点少倍频错误），再在 Praat 的音高点上按比例修正
    z = librosa.resample(y, orig_sr=SR, target_sr=16000)
    f0, vf, _ = librosa.pyin(z, fmin=60, fmax=300, sr=16000, frame_length=1024, hop_length=320)
    tt = np.arange(len(f0)) * 0.02; ok = vf & ~np.isnan(f0)
    tv, sv = tt[ok], 12 * np.log2(f0[ok] / target)
    grid = np.arange(0, tt[-1] + 1, 1.0)
    tr = np.array([np.median(sv[(tv > g - win) & (tv < g + win)]) for g in grid])
    trend = np.interp(T, grid, tr)
    G = F * 2 ** (-amount * trend / 12)
    new = call('Create PitchTier', 'new', snd.xmin, snd.xmax)
    for t_, g_ in zip(T, G): call(new, 'Add point', float(t_), float(g_))
    call([new, man], 'Replace pitch tier')
    out = call(man, 'Get resynthesis (overlap-add)').values[0]
    out = np.pad(out, (0, max(0, len(y) - len(out))))[:len(y)].astype(np.float32)
    lo, hi = trend.min(), trend.max()
    print('pitch trend %.1f..%.1f st around %.0f Hz -> corrected %d%%' % (lo, hi, target, amount * 100), flush=True)
    return out


def lengthen(y, f):
    import parselmouth
    from parselmouth.praat import call
    snd = parselmouth.Sound(y.astype(np.float64), SR)
    out = call(snd, 'Lengthen (overlap-add)', 70, 320, float(f))
    return out.values[0].astype(np.float32)


if __name__ == '__main__':
    y, mp3 = take()
    print('take', mp3, round(len(y) / SR, 1), 's', flush=True)
    y = detrend_pitch(y)
    refs = [sf.read(f'{REF}/{L[0]}.wav', dtype='float32')[0] for L in LINES]
    bounds, a0, a1 = align(y, refs)
    bad = check(y, bounds, a0, a1, refs)
    print('alignment check failures:', bad if bad else 'none', flush=True)
    if bad and not os.environ.get('ALLOW_BAD'): sys.exit('alignment failed')
    # 整条只做一个增益：有声部分 RMS → -20 dBFS
    act = y[np.abs(y) > 0.02]; y = y * (10 ** (-20 / 20) / np.sqrt(np.mean(act ** 2)))
    cut = [max(0.0, a0 - 0.05)] + [(q[0] + q[1]) / 2 for q in bounds] + [min(len(y) / SR, a1 + 0.2)]
    pause = [q[1] - q[0] for q in bounds] + [None]
    gaps = {}
    for k, L in enumerate(LINES):
        seg = y[int(cut[k] * SR):int(cut[k + 1] * SR)].copy()
        if L[0] in SLOW: seg = lengthen(seg, SLOW[L[0]])
        if k == 0 or L[0] in BREAKS: f = int(0.01 * SR); seg[:f] *= np.linspace(0, 1, f)
        nxt = LINES[k + 1][0] if k + 1 < len(LINES) else None
        end = nxt is None or nxt in BREAKS
        if end: f = int(0.06 * SR); seg[-f:] *= np.linspace(1, 0, f)
        sf.write(f'{OUT}/{L[0]}.wav', seg, SR, subtype='FLOAT')
        gaps[L[0]] = None if end else round(float(pause[k]), 3)
    json.dump(gaps, open(f'{OUT}/gaps.json', 'w'), indent=0)
    pk = max(np.abs(sf.read(f'{OUT}/{L[0]}.wav')[0]).max() for L in LINES)
    print('peak', round(pk, 3))
