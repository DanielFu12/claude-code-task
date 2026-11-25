"""整篇一次合成的旁白（第三版，按 docs/旁白一致性与自然衔接.md 的做法）。

1. 整篇旁白一次请求 Seed-TTS 2.0，一条录完（全片同一口气、同一个人）。
2. 逐段再合成一份「参考音频」（同音色、同语速、同语气），只用于对齐和校验，不进成片。
3. 拉平长录音的音高漂移（pYIN 估 ±25 秒趋势，Praat PSOLA 只修趋势，不动逐句抑扬）。
4. 逐段子序列 DTW 对齐，在停顿正中切开；段内的逐字时刻由参考音频经 DTW 路径映射过来。
5. 逐段校验：时长比、与相邻段参考的距离。
输出 work/vo/seg_XX.wav + work/vo/segments.json
"""
import base64, hashlib, json, math, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np, soundfile as sf, librosa

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from script import SCENES, TTS_REPL, STYLE
from tts import parse, tts_text, align as punct_align, trim, PUNCT

VOICE = 'zh_male_ruyayichen_uranus_bigtts'
SR = 24000
RATE = int(os.environ.get('VO_RATE', 10))
WORK = os.path.join(HERE, '..', 'work')


def synth(text, out, rate=RATE):
    rp = {"text": text, "speaker": VOICE, "audio_params": {"format": "wav", "sample_rate": SR, "speech_rate": rate},
          "additions": json.dumps({"context_texts": [STYLE]}, ensure_ascii=False)}
    body = {"user": {"uid": "bmjz"}, "req_params": rp}
    for attempt in range(6):
        try:
            req = urllib.request.Request("https://openspeech.bytedance.com/api/v3/tts/unidirectional",
                                         data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json", "X-Api-App-Id": "x",
                                                  "X-Api-Access-Key": "x", "X-Api-Resource-Id": "seed-tts-2.0"})
            r = urllib.request.urlopen(req, timeout=900).read().decode()
            audio = b''
            for line in r.splitlines():
                if line.strip():
                    d = json.loads(line)
                    if d.get('data'): audio += base64.b64decode(d['data'])
            if not audio: raise RuntimeError(r[:300])
            tmp = out + '.tmp.wav'
            open(tmp, 'wb').write(audio)
            y, sr = sf.read(tmp)
            os.remove(tmp)
            sf.write(out, y, sr, format='FLAC' if out.endswith('.flac') else 'WAV')
            return
        except Exception as e:
            print('retry', attempt, text[:16], e, file=sys.stderr)
            time.sleep(3 + attempt * 5)
    raise RuntimeError('tts failed')


def paragraphs():
    out = []
    for si, sc in enumerate(SCENES):
        for ui, u in enumerate(sc['say']):
            text, cues = parse(u)
            out.append(dict(scene=sc['id'], si=si, ui=ui, text=text, tts=tts_text(text), cues=cues))
    return out


def h(s):
    return hashlib.md5((VOICE + str(RATE) + STYLE + s).encode()).hexdigest()[:16]


# ---------------------------------------------------------------- 音高漂移
def detrend_pitch(y, sr, target=None, amount=0.9, win=25):
    import parselmouth
    from parselmouth.praat import call
    f0, vf, _ = librosa.pyin(y.astype(np.float32), fmin=60, fmax=300, sr=sr, frame_length=1024, hop_length=256)
    tt = librosa.times_like(f0, sr=sr, hop_length=256)
    ok = vf & np.isfinite(f0)
    semi = np.full_like(f0, np.nan)
    semi[ok] = 12 * np.log2(f0[ok] / 100.0)
    # ±25 秒滑动中位数（每 1 秒取一个点）
    grid = np.arange(0, tt[-1] + 1, 1.0)
    trend = []
    for g in grid:
        m = ok & (np.abs(tt - g) <= win)
        trend.append(np.median(semi[m]) if m.sum() > 20 else np.nan)
    trend = np.array(trend)
    good = np.isfinite(trend)
    trend = np.interp(grid, grid[good], trend[good])
    tgt = np.median(trend) if target is None else 12 * np.log2(target / 100.0)
    dev = trend - tgt
    snd = parselmouth.Sound(y.astype(np.float64), sr)
    manip = call(snd, "To Manipulation", 0.01, 60, 300)
    pt = call(manip, "Extract pitch tier")
    n = call(pt, "Get number of points")
    times = [call(pt, "Get time from index", i + 1) for i in range(n)]
    vals = [call(pt, "Get value at index", i + 1) for i in range(n)]
    call(pt, "Remove points between", 0, snd.duration)
    for tm, v in zip(times, vals):
        d = np.interp(tm, grid, dev)
        call(pt, "Add point", tm, v * 2 ** (-amount * d / 12))
    call([pt, manip], "Replace pitch tier")
    out = call(manip, "Get resynthesis (overlap-add)")
    yo = out.values[0].astype(np.float32)
    per_min = [float(100 * 2 ** (np.median(semi[ok & (tt >= m * 60) & (tt < m * 60 + 60)]) / 12))
               for m in range(int(tt[-1] // 60) + 1) if (ok & (tt >= m * 60) & (tt < m * 60 + 60)).sum() > 50]
    return yo, per_min, float(dev.max() - dev.min())


# ---------------------------------------------------------------- 对齐
FR = 0.02


def feats(y, sr):
    y16 = librosa.resample(y.astype(np.float32), orig_sr=sr, target_sr=16000)
    m = librosa.feature.mfcc(y=y16, sr=16000, n_mfcc=21, n_fft=640, hop_length=320)[1:]
    m = (m - m.mean(1, keepdims=True)) / (m.std(1, keepdims=True) + 1e-6)
    return m


def pauses(y, sr, thr_db=24, min_len=0.10):
    hop = int(sr * 0.01)
    n = len(y) // hop
    rms = np.sqrt((y[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12)
    from scipy.ndimage import median_filter
    db = median_filter(20 * np.log10(rms + 1e-9), 5)
    q = db < db.max() - thr_db
    out, i = [], 0
    while i < n:
        if q[i]:
            j = i
            while j < n and q[j]: j += 1
            if (j - i) * 0.01 >= min_len: out.append((i * 0.01, j * 0.01))
            i = j
        else:
            i += 1
    return out


def snap(t, ps, rad=0.35):
    best, bs = None, 1e9
    for a, b in ps:
        c = (a + b) / 2
        if a - rad <= t <= b + rad:
            score = abs(c - t) - 0.5 * min(b - a, 0.6)
            if score < bs: best, bs = c, score
    return best if best is not None else t


def dtw_cost(A, B):
    D, wp = librosa.sequence.dtw(A, B, metric='cosine')
    return D[-1, -1] / (A.shape[1] + B.shape[1])


def build():
    os.makedirs(os.path.join(WORK, 'vo_take'), exist_ok=True)
    os.makedirs(os.path.join(WORK, 'vo_ref'), exist_ok=True)
    os.makedirs(os.path.join(WORK, 'vo'), exist_ok=True)
    P = paragraphs()
    full = ''.join(p['tts'] for p in P)
    take_p = os.path.join(WORK, 'vo_take', f'take_{h(full)}.flac')
    jobs = [(p['tts'], os.path.join(WORK, 'vo_ref', h(p['tts']) + '.wav')) for p in P]
    jobs = [j for j in jobs if not os.path.exists(j[1])]
    with ThreadPoolExecutor(4) as ex:
        fut = ex.submit(synth, full, take_p) if not os.path.exists(take_p) else None
        list(ex.map(lambda j: synth(*j), jobs))
        if fut: fut.result()
    y, sr = sf.read(take_p)
    if y.ndim > 1: y = y.mean(1)
    y, _ = trim(y)
    print(f'take: {len(full)} chars, {len(y) / sr:.1f}s, {len(full) / (len(y) / sr):.2f} 字/秒')
    # 音高拉平
    dt_p = take_p.replace('.flac', '_flat.flac')
    if not os.path.exists(dt_p):
        yf, per_min, spread = detrend_pitch(y, sr)
        # 第二遍：±10 秒窗口再修 60%，压住高潮段整体抬高的音高（逐句抑扬不动）
        yf, _, spread2 = detrend_pitch(yf, sr, amount=0.6, win=10)
        print('second pass spread', round(spread2, 2))
        sf.write(dt_p, yf, sr, format='FLAC')
        print('pitch per minute before:', [round(v) for v in per_min], 'trend spread', round(spread, 2), 'semitones')
    yf, _ = sf.read(dt_p)
    _, per_min2, _ = detrend_pitch(yf, sr, amount=0.0)
    print('pitch per minute after :', [round(v) for v in per_min2])
    # 对齐
    refs = []
    for p in P:
        r, _ = sf.read(os.path.join(WORK, 'vo_ref', h(p['tts']) + '.wav'))
        r, _ = trim(r)
        refs.append(r)
    F = feats(yf, sr)
    nfr = F.shape[1]
    ps = pauses(yf, sr)
    pos = 0.0
    bounds = [0.0]
    cmaps = []
    fails = []
    for i, p in enumerate(P):
        r = refs[i]
        Rf = feats(r, sr)
        tmpl = Rf
        if i + 1 < len(P):
            nxt = feats(refs[i + 1][:int(1.5 * sr)], sr)
            tmpl = np.concatenate([Rf, nxt], 1)
        w0 = max(0.0, pos - 0.4)
        w1 = min(nfr * FR, pos + 1.6 * len(r) / sr + 3)
        Wf = F[:, int(w0 / FR):int(w1 / FR)]
        D, wp = librosa.sequence.dtw(tmpl, Wf, metric='cosine', subseq=True)
        wp = wp[::-1]
        # 参考帧 -> 录音时刻
        rfr = wp[:, 0]; tfr = wp[:, 1]
        start = w0 + tfr[0] * FR if i > 0 else 0.0
        endf = Rf.shape[1]
        k = np.searchsorted(rfr, endf - 1)
        end_est = w0 + tfr[min(k, len(tfr) - 1)] * FR
        end = snap(end_est, ps) if i + 1 < len(P) else len(yf) / sr
        # 逐字：参考音频上的标点对齐 -> 经 DTW 路径映射
        ct_ref = punct_align(p['text'], r)
        uniq_r, idx = np.unique(rfr, return_index=True)
        tmap = w0 + tfr[idx] * FR
        ct = np.interp(np.asarray(ct_ref) / FR, uniq_r, tmap)
        ct = np.clip(ct, bounds[-1], end)
        cmaps.append(ct)
        ratio = (end - bounds[-1]) / (len(r) / sr)
        # 校验：与相邻参考的距离
        seg = F[:, int(bounds[-1] / FR):int(end / FR)]
        d_own = dtw_cost(Rf, seg)
        d_nb = [dtw_cost(feats(refs[j], sr), seg) for j in (i - 1, i + 1) if 0 <= j < len(P)]
        ok = (0.7 <= ratio <= 1.4 or (len(r) / sr < 1.5 and ratio >= 0.55)) and all(d_own < 0.98 * d for d in d_nb)
        if not ok: fails.append((i, p['text'][:14], round(ratio, 2), round(d_own, 3), [round(d, 3) for d in d_nb]))
        bounds.append(end)
        pos = end
    print('alignment check failures:', fails if fails else 'none')
    # 整条一个增益：有声部分 RMS -> -20 dBFS
    act = np.abs(yf) > 0.01
    g = 10 ** (-20 / 20) / (np.sqrt(np.mean(yf[act] ** 2)) + 1e-9)
    yf = yf * g
    segs = []
    for i, p in enumerate(P):
        a, b = bounds[i], bounds[i + 1]
        seg = yf[int(a * sr):int(b * sr)].astype(np.float32)
        fn = os.path.join(WORK, 'vo', f'seg_{i:02d}.wav')
        sf.write(fn, seg, sr)
        segs.append(dict(i=i, scene=p['scene'], ui=p['ui'], text=p['text'], take_start=a, take_end=b,
                         wav=os.path.relpath(fn, WORK), ct=[round(float(x) - a, 3) for x in cmaps[i]]))
    json.dump(dict(sr=sr, segs=segs, fails=fails), open(os.path.join(WORK, 'vo', 'segments.json'), 'w'), ensure_ascii=False, indent=1)
    return segs, fails


if __name__ == '__main__':
    build()
