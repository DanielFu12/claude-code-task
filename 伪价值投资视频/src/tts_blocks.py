"""整段合成旁白，再按停顿切回逐句 -> work/vo/Lxx.wav + work/vo/gaps.json（V8）

为什么：逐句单独合成时，每一句的音高、音色、能量都各自起落，段落衔接处像换了一次人。
整段合成让同一段话共用一口气；跨段再做音高 / 频谱 / 响度的匹配，听起来像同一个人一口气讲完。

切句：Seed-TTS 2.0 不返回时间戳，所以用停顿检测 + 动态规划，按旧版逐句时长的比例找出句界；
校验不过就重合成，仍不过就把这段拆小再合成。"""
import os, re, sys, json, hashlib, concurrent.futures as cf
import numpy as np, soundfile as sf, librosa
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, TONE
from tts import synth

SPK = 'zh_male_m191_uranus_bigtts'
RATE = int(os.environ.get('RATE', '32'))
W = sys.argv[1] if len(sys.argv) > 1 else 'work'
OUT, REF, CACHE = f'{W}/vo', f'{W}/vo_ref', f'{W}/vo_blocks'
os.makedirs(OUT, exist_ok=True); os.makedirs(CACHE, exist_ok=True)
SR = 48000
# 按章（长章按小节）整段合成：接缝只出现在章节卡 / 小节转场处，那里本来就有音乐和画面的停顿
BREAKS = ['L01', 'L16', 'L25', 'L44', 'L61', 'L70', 'L85', 'L90']
ID = {L[0]: k for k, L in enumerate(LINES)}


def blocks():
    out, cur = [], []
    for L in LINES:
        if cur and L[0] in BREAKS: out.append(cur); cur = []
        cur.append(L)
    out.append(cur)
    return out


def ref_dur(i):
    y, _ = sf.read(f'{REF}/{i}.wav', dtype='float32'); return len(y) / SR


def silences(y, thr_db=-36, min_len=0.11):
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


def split(y, exp):
    """exp：各句期望时长。返回句界 [(静音起, 静音止)] × (N-1)，或 None"""
    N = len(exp)
    sil = silences(y)
    a0 = sil[0][1] if sil and sil[0][0] < 0.05 else 0.0
    a1 = sil[-1][0] if sil and sil[-1][1] > len(y) / SR - 0.05 else len(y) / SR
    if N == 1: return [], a0, a1
    C = [s for s in sil if a0 + 0.3 < (s[0] + s[1]) / 2 < a1 - 0.3]
    if len(C) < N - 1: return None
    exp = np.array(exp) * (a1 - a0) / sum(exp)
    M = len(C); INF = 1e18
    cost = lambda d, e: ((d - e) / (0.18 * e + 0.25)) ** 2
    bonus = lambda c: 1.2 * np.log((c[1] - c[0]) / 0.11)
    D = np.full((N - 1, M), INF); P = np.zeros((N - 1, M), int)
    for j, c in enumerate(C):
        D[0, j] = cost(c[0] - a0, exp[0]) - bonus(c)
    for k in range(1, N - 1):
        for j, c in enumerate(C):
            for jp in range(j):
                v = D[k - 1, jp] + cost(c[0] - C[jp][1], exp[k]) - bonus(c)
                if v < D[k, j]: D[k, j], P[k, j] = v, jp
    tot = [D[N - 2, j] + cost(a1 - C[j][1], exp[-1]) for j in range(M)]
    j = int(np.argmin(tot))
    if tot[j] >= INF / 2: return None
    path = [j]
    for k in range(N - 2, 0, -1): j = P[k, j]; path.append(j)
    b = [C[j] for j in reversed(path)]
    # 校验：每句时长与期望相差不超过 25% + 0.4 秒，句界停顿 ≥ 0.15 秒
    st = [a0] + [s[1] for s in b]; en = [s[0] for s in b] + [a1]
    for k in range(N):
        if abs((en[k] - st[k]) - exp[k]) > 0.25 * exp[k] + 0.4: return None
    if min(s[1] - s[0] for s in b) < 0.15: return None
    return b, a0, a1


def _feat(y):
    z = librosa.resample(y, orig_sr=SR, target_sr=16000)
    m = librosa.feature.mfcc(y=z, sr=16000, n_mfcc=20, hop_length=320)[1:]
    return (m - m.mean(1, keepdims=True)) / (m.std(1, keepdims=True) + 1e-6)


def align_split(y, refs):
    """强制对齐切句：把整段音频和逐句参考音频（同一文本、同一音色）的拼接做 DTW，
    把参考里的句界映射到整段里，再吸附到附近最安静的位置。返回 [(切点起, 切点止)]、首、尾（秒）"""
    hop = 320 / 16000
    F = _feat(y)
    R = [_feat(r) for r in refs]
    bounds = np.cumsum([r.shape[1] for r in R])[:-1]
    D, wp = librosa.sequence.dtw(F, np.hstack(R), metric='cosine', global_constraints=True, band_rad=0.12)
    wp = wp[::-1]
    sil = silences(y, thr_db=-32, min_len=0.05)
    a0 = sil[0][1] if sil and sil[0][0] < 0.05 else 0.0
    a1 = sil[-1][0] if sil and sil[-1][1] > len(y) / SR - 0.05 else len(y) / SR
    # 能量包络（10ms）
    h = 480; n = len(y) // h
    e = 20 * np.log10(np.sqrt(np.mean(y[:n * h].reshape(n, h) ** 2, 1)) + 1e-9)
    out = []
    for b in bounds:
        ys = wp[wp[:, 1] == b, 0]
        tb = (np.median(ys) if len(ys) else wp[np.argmin(np.abs(wp[:, 1] - b)), 0]) * hop
        # 附近 ±0.35 秒内的静音段优先，没有就取能量最低点
        near = [s_ for s_ in sil if s_[0] - 0.35 < tb < s_[1] + 0.35]
        if near:
            s_ = max(near, key=lambda q: (q[1] - q[0]) - 0.6 * abs((q[0] + q[1]) / 2 - tb))
        else:
            k0, k1 = int((tb - 0.25) / 0.01), int((tb + 0.25) / 0.01)
            k = k0 + int(np.argmin(e[max(k0, 0):k1])); s_ = (k * 0.01 - 0.02, k * 0.01 + 0.02)
        out.append(s_)
    return out, a0, a1


def seg_ok(y, b, a0, a1, refs):
    """校验：每一段与它对应的参考句最像（比相邻两句更像），时长比在 0.7~1.4"""
    st = [a0] + [s_[1] for s_ in b]; en = [s_[0] for s_ in b] + [a1]
    segs = [y[int(st[k] * SR):int(en[k] * SR)] for k in range(len(refs))]
    if any(len(g) < SR * 0.3 for g in segs): return False
    Fs = [_feat(g) for g in segs]; Rs = [_feat(r) for r in refs]
    def d(a, b_):
        D, wp = librosa.sequence.dtw(a, b_, metric='cosine'); return D[-1, -1] / len(wp)
    for k in range(len(refs)):
        if not 0.7 < len(segs[k]) / len(refs[k]) < 1.4: return False
        d0 = d(Fs[k], Rs[k])
        for j in (k - 1, k + 1):
            if 0 <= j < len(refs) and d(Fs[k], Rs[j]) < d0 * 1.02: return False
    return True


def synth_block(Ls, tag=''):
    text = ''.join(L[1] for L in Ls)
    h = hashlib.md5((SPK + str(RATE) + TONE + text + tag).encode()).hexdigest()[:10]
    mp3 = f'{CACHE}/{Ls[0][0]}_{h}.mp3'
    if not os.path.exists(mp3):
        for k in range(4):
            try: synth(SPK, text, mp3, rate=RATE, ctx=TONE); break
            except Exception as e: print('retry', Ls[0][0], e, flush=True)
    y, _ = librosa.load(mp3, sr=SR)
    return y


def do_block(Ls, depth=0):
    refs = [sf.read(f'{REF}/{L[0]}.wav', dtype='float32')[0] for L in Ls]
    r = None
    for attempt in range(3):
        y = synth_block(Ls, '' if attempt == 0 else f'#{attempt}')
        b, a0, a1 = align_split(y, refs)
        if seg_ok(y, b, a0, a1, refs): r = (b, a0, a1); break
        print('  align check failed', Ls[0][0], 'attempt', attempt, flush=True)
    if r is None:
        m = len(Ls) // 2
        print('  split fallback', Ls[0][0], '..', Ls[-1][0], '->', Ls[m][0], flush=True)
        return do_block(Ls[:m], depth + 1) + do_block(Ls[m:], depth + 1)
    b, a0, a1 = r
    # 段内切点取停顿正中：把这些句子首尾相接，就还原成原来那一整段连续的话
    cut = [max(0.0, a0 - 0.05)] + [(q[0] + q[1]) / 2 for q in b] + [min(len(y) / SR, a1 + 0.15)]
    pause = [q[1] - q[0] for q in b] + [None]
    out = []
    for k, L in enumerate(Ls):
        seg = y[int(cut[k] * SR):int(cut[k + 1] * SR)].copy()
        if k == 0: f = int(0.01 * SR); seg[:f] *= np.linspace(0, 1, f)
        if k == len(Ls) - 1: f = int(0.06 * SR); seg[-f:] *= np.linspace(1, 0, f)
        out.append(dict(id=L[0], y=seg, gap=pause[k], block=Ls[0][0]))
    return out


# ------------------------------------------------------------------ 跨段统一
def f0_median(y):
    f0 = librosa.yin(y, fmin=70, fmax=320, sr=SR, frame_length=2048, hop_length=512)
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0][:len(f0)]
    v = f0[(rms > np.percentile(rms, 40)) & (f0 > 75) & (f0 < 300)]
    return float(np.median(v)) if len(v) else 0.0


def ltas(y):
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512)) ** 2
    e = S.sum(0); m = e > np.percentile(e, 40)
    return 10 * np.log10(S[:, m].mean(1) + 1e-12)


def smooth_bands(d, n=2048):
    """线性频率 → 1/3 倍频程平滑"""
    f = np.linspace(0, SR / 2, len(d)); out = np.zeros_like(d)
    for k, fc in enumerate(f):
        if fc < 60: out[k] = 0; continue
        m = (f > fc / 2 ** (1 / 6)) & (f < fc * 2 ** (1 / 6))
        out[k] = d[m].mean() if m.any() else 0
    return out


def psola_shift(y, semi):
    """Praat PSOLA 移调：保留共振峰，只把整段的音高中心挪向全片中位数（最多 ±1.5 半音）"""
    import parselmouth
    from parselmouth.praat import call
    semi = float(np.clip(semi, -1.5, 1.5))
    snd = parselmouth.Sound(y.astype(np.float64), SR)
    man = call(snd, 'To Manipulation', 0.01, 70, 320)
    pt = call(man, 'Extract pitch tier')
    call(pt, 'Multiply frequencies', snd.xmin, snd.xmax, 2 ** (semi / 12))
    call([pt, man], 'Replace pitch tier')
    out = call(man, 'Get resynthesis (overlap-add)').values[0]
    out = np.pad(out, (0, max(0, len(y) - len(out))))
    return out[:len(y)].astype(np.float32)


def eq(y, corr_db):
    f = np.linspace(0, 1, len(corr_db)); g = 10 ** (corr_db / 20)
    h = signal.firwin2(1023, f, g)
    return signal.fftconvolve(y, h, 'full')[511:511 + len(y)].astype(np.float32)


if __name__ == '__main__':
    B = blocks()
    print(len(B), 'blocks:', [(b[0][0], b[-1][0], sum(len(L[1]) for L in b)) for b in B], flush=True)
    with cf.ThreadPoolExecutor(4) as ex:
        res = list(ex.map(do_block, B))
    segs = [s for r in res for s in r]
    assert [s['id'] for s in segs] == [L[0] for L in LINES]

    # 按合成段分组统计音高与频谱
    groups = {}
    for s in segs: groups.setdefault(s['block'], []).append(s)
    stat = {}
    for g, ss in groups.items():
        y = np.concatenate([s['y'] for s in ss])
        stat[g] = dict(f0=f0_median(y), lt=ltas(y))
    F0 = np.median([v['f0'] for v in stat.values()]); LT = np.mean([v['lt'] for v in stat.values()], 0)
    for g, ss in groups.items():
        st = stat[g]
        ratio = F0 / st['f0'] if st['f0'] else 1.0
        semi = 12 * np.log2(ratio)
        corr = np.clip(smooth_bands(LT - st['lt']), -4, 4)
        corr -= np.average(corr, weights=np.exp(-((np.linspace(0, SR / 2, len(corr)) - 1500) / 1500) ** 2))   # 只改音色，不改响度
        corr = np.clip(corr, -4, 4)
        y = np.concatenate([s['y'] for s in ss]); n = np.cumsum([0] + [len(s['y']) for s in ss])
        if abs(semi) > 0.25: y = psola_shift(y, 0.7 * semi)
        y = eq(y, corr)
        for k, s in enumerate(ss): s['y'] = y[n[k]:n[k + 1]]
        print('%-5s f0 %.1f Hz -> shift %+.2f st, eq max %.1f dB' % (g, st['f0'], float(np.clip(0.7 * semi, -1.5, 1.5)) if abs(semi) > 0.25 else 0, np.abs(corr).max()), flush=True)

    # 响度：每一整段统一到 -20 dBFS（有声 RMS）；段内不再逐句调整，保留原本的轻重起伏
    def arms(y):
        a = y[np.abs(y) > 0.02]; return np.sqrt(np.mean(a ** 2)) if len(a) else 1e-3
    for g, ss in groups.items():
        gb = 10 ** (-20 / 20) / arms(np.concatenate([s['y'] for s in ss]))
        for s in ss: s['y'] = s['y'] * gb
    pk = max(np.abs(s['y']).max() for s in segs)
    if pk > 0.89: [s.update(y=s['y'] * 0.89 / pk) for s in segs]
    gaps = {}
    for s in segs:
        sf.write(f"{OUT}/{s['id']}.wav", s['y'].astype(np.float32), SR, subtype='FLOAT')
        gaps[s['id']] = None if s['gap'] is None else round(float(s['gap']), 3)
    json.dump(gaps, open(f'{OUT}/gaps.json', 'w'), indent=0)
    tot = sum(len(s['y']) for s in segs) / SR
    print('speech total', round(tot, 1), 'old', round(sum(ref_dur(L[0]) for L in LINES), 1))
