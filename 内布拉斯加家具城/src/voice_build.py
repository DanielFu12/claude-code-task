"""整篇旁白 → 逐句音频（docs/旁白一致性与自然衔接.md 第二节 3–4、6）。

  ① 拉平长文本的音高漂移：pYIN 估有声帧音高 → 半音 → ±25 秒滑动中位数作趋势；Praat Manipulation 每个音高点乘
     2^(−0.9 × 趋势/12)（目标为全篇中位数，修 90%）→ overlap-add 重合成。只动缓慢趋势，逐句抑扬不动。
  ② 逐句子序列 DTW 切句：16 kHz MFCC（20 维，去第 0 维，逐维标准化），帧长 20 ms，余弦距离；
     窗口 = [当前位置 − 0.4 s, 当前位置 + 1.6 × 本句参考时长 + 3 s]；模板 = 本句参考 + 下句参考开头 1.5 s；
     句界 ±0.35 s 内选“够长、离估计点近”的停顿，在停顿正中切；没有停顿取能量最低点。
  ③ 逐句校验（不过就整条重录）：切出的这一句与本句参考的 DTW 距离，比与上一句、下一句参考都小至少 2%；时长比 0.7–1.4。
     另用接口返回的逐字时间戳交叉核对句界（只报告，不参与切分）。
  ④ 整条只做一个增益（有声部分 RMS → −20 dBFS）。
  ⑤ 指定章节用 PSOLA（Praat Lengthen overlap-add）拉长，不改音高。
输出 WORK/vo/<id>.wav（切片含两侧各半个停顿，首尾相接即还原原录音）、WORK/vo/vo.json、WORK/vo/gaps.json、WORK/vo/report.txt。
vo.json 每句：lead（切片开头到发声）、dur（发声长度）、tail（发声结束到切片末尾）、gap（到下一句发声的自然间隔）、
ct（[朗读文本中的字符下标, 相对发声起点的秒数]，来自逐字时间戳）、stretch（PSOLA 倍数）。
python3 src/voice_build.py WORK
"""
import sys, os, json, re
import numpy as np, soundfile as sf, librosa
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES
import tts_take as T

SR, FS, HOP = 48000, 16000, 320            # 合成采样率；特征采样率与帧移（20 ms）
STRETCH = {'ch3': 1.14, 'c7f': 1.08, 'c7g': 1.08, '*': 1.04}   # 长文本越讲越快：全篇轻放慢 4%；讲概念的第三章再慢些；结尾两句略放慢
PUN = re.compile(r'[\s，。、：；？！“”‘’《》（）—…·,.;:?!"\'()\-]')


def say(l): return T.spoken(l)


# ------------------------------------------------------------------ ① 音高漂移
def detrend_pitch(y, rep):
    import parselmouth
    from parselmouth.praat import call
    y16 = librosa.resample(y, orig_sr=SR, target_sr=FS)
    f0, vf, _ = librosa.pyin(y16, fmin=60, fmax=300, sr=FS, frame_length=1024, hop_length=160)
    tt = np.arange(len(f0)) * 160 / FS
    ok = vf & np.isfinite(f0)
    st = 12 * np.log2(f0[ok] / 100.0); to = tt[ok]
    target = float(np.median(st))
    trend = np.array([np.median(st[(to > c - 25) & (to < c + 25)]) for c in to]) - target
    def per_minute(vals, times):
        return [round(float(100 * 2 ** (np.median(vals[(times >= m * 60) & (times < m * 60 + 60)]) / 12)), 1)
                for m in range(int(times[-1] // 60) + 1) if ((times >= m * 60) & (times < m * 60 + 60)).sum() > 50]
    rep.append('音高中位数（每分钟，修正前）Hz：' + ' '.join(map(str, per_minute(st, to))))
    snd = parselmouth.Sound(y.astype(np.float64), SR)
    man = call(snd, 'To Manipulation', 0.01, 60, 300)
    pt = call(man, 'Extract pitch tier')
    n = call(pt, 'Get number of points')
    times = np.array([call(pt, 'Get time from index', k) for k in range(1, n + 1)])
    vals = np.array([call(pt, 'Get value at index', k) for k in range(1, n + 1)])
    corr = np.interp(times, to, trend)
    new = vals * 2 ** (-0.9 * corr / 12)
    call(pt, 'Remove points between', 0, snd.duration)
    for a, b in zip(times, new): call(pt, 'Add point', float(a), float(b))
    call([man, pt], 'Replace pitch tier')
    out = call(man, 'Get resynthesis (overlap-add)')
    z = out.values[0].astype(np.float32)
    z = np.pad(z, (0, max(len(y) - len(z), 0)))[:len(y)]
    f1, v1, _ = librosa.pyin(librosa.resample(z, orig_sr=SR, target_sr=FS), fmin=60, fmax=300, sr=FS, frame_length=1024, hop_length=160)
    ok1 = v1 & np.isfinite(f1)
    st1 = 12 * np.log2(f1[ok1] / 100.0)
    pm1 = per_minute(st1, tt[ok1])
    rep.append('音高中位数（每分钟，修正后）Hz：' + ' '.join(map(str, pm1)) +
               '   首尾差 %.2f 半音' % (12 * np.log2(max(pm1) / min(pm1))))
    return z


def hnr(y, a, b):
    import parselmouth
    from parselmouth.praat import call
    s = parselmouth.Sound(y[int(a * SR):int(b * SR)].astype(np.float64), SR)
    h = call(s, 'To Harmonicity (cc)', 0.01, 75, 0.1, 1.0)
    return call(h, 'Get mean', 0, 0)


# ------------------------------------------------------------------ ② 特征与对齐
def feats(y16):
    m = librosa.feature.mfcc(y=y16, sr=FS, n_mfcc=21, n_fft=640, hop_length=HOP, win_length=640)[1:]
    m = (m - m.mean(1, keepdims=True)) / (m.std(1, keepdims=True) + 1e-6)
    return m


def voiced_span(y, sr, thr=-38):
    h = int(0.01 * sr)
    e = np.sqrt(np.convolve(y ** 2, np.ones(h) / h, 'same'))
    db = 20 * np.log10(e + 1e-9); top = np.percentile(db, 95)
    on = np.nonzero(db > top + thr)[0]
    return (on[0] / sr, on[-1] / sr) if len(on) else (0, len(y) / sr)


def energy_db(y, hop=0.005):
    h = int(hop * SR)
    e = np.sqrt(np.convolve(y ** 2, np.ones(h * 4) / (h * 4), 'same'))[::h]
    return 20 * np.log10(e + 1e-9), hop


def pauses(db, hop, a, b, floor):
    i0, i1 = max(int(a / hop), 0), min(int(b / hop), len(db) - 1); out = []; k = i0
    while k <= i1:
        if db[k] < floor:
            j = k
            while j + 1 <= i1 and db[j + 1] < floor: j += 1
            out.append((k * hop, (j + 1) * hop)); k = j + 1
        else: k += 1
    return out


def dtw_cost(A, B):
    D, wp = librosa.sequence.dtw(X=A, Y=B, metric='cosine')
    return D[-1, -1] / len(wp)


def map_one(text, js):
    """单句参考音频的逐字时间戳 → [(朗读文本下标, 起)]"""
    words = [(w['word'], w['startTime']) for s in js for w in s['words']]
    out, pos = [], 0
    for w, t0 in words:
        w = PUN.sub('', w.strip())
        if not w: continue
        j = pos
        while j < len(text) and PUN.match(text[j]): j += 1
        if text[j:j + len(w)].lower() != w.lower():
            k = text.lower().find(w.lower(), pos)
            if k < 0 or k - pos > 6: continue
            j = k
        out.append((j, t0)); pos = j + len(w)
    return out


def map_words(take_json):
    """接口逐字时间戳 → 每句 [(朗读文本下标, 起, 止)]（文本逐字比对；对不上的字跳过）"""
    words = [(w['word'], w['startTime'], w['endTime']) for s in take_json for w in s['words']]
    out = {l[0]: [] for l in LINES}; k = 0
    for l in LINES:
        s = say(l); pos = 0
        while k < len(words):
            w = PUN.sub('', words[k][0].strip())
            if not w: k += 1; continue
            j = pos
            while j < len(s) and PUN.match(s[j]): j += 1
            if s[j:j + len(w)].lower() != w.lower(): break
            out[l[0]].append((j, words[k][1], words[k][2])); pos = j + len(w); k += 1
        if PUN.sub('', s[pos:]):
            out[l[0]].append(('miss', PUN.sub('', s[pos:])[:20]))
    return out


def build(work):
    rep = []
    take = T.take_path(work)
    y, sr = sf.read(take, dtype='float32'); assert sr == SR
    ids = [l[0] for l in LINES]
    print('detrend pitch …', flush=True)
    hnr0 = hnr(y, 60, 120)
    y = detrend_pitch(y, rep)
    rep.append('谐噪比（60–120 s）：修正前 %.2f dB，修正后 %.2f dB' % (hnr0, hnr(y, 60, 120)))
    # ④ 整条一个增益：有声部分 RMS → −20 dBFS
    db, hop = energy_db(y)
    vmask = np.repeat(db > np.percentile(db, 95) - 35, int(hop * SR))[:len(y)]
    rms = np.sqrt(np.mean(y[:len(vmask)][vmask] ** 2)); y = y * (10 ** (-20 / 20) / rms)
    db, hop = energy_db(y)
    floor = np.percentile(db[db > -120], 95) - 24          # 合成录音的停顿里有极轻的气声，约比峰值低 25–40 dB
    from scipy.ndimage import median_filter
    db = median_filter(db, 11)                             # 55 ms 中值平滑：停顿中间的一下换气不把停顿切断
    print('align …', flush=True)
    y16 = librosa.resample(y, orig_sr=SR, target_sr=FS)
    F = feats(y16); fr = HOP / FS
    refs, refts = {}, {}
    for l in LINES:
        r, _ = sf.read(T.ref_path(work, l), dtype='float32')
        a, b = voiced_span(r, SR); r16 = librosa.resample(r[int(a * SR):int(b * SR) + 1], orig_sr=SR, target_sr=FS)
        refs[l[0]] = r16
        rj = json.load(open(T.ref_path(work, l)[:-4] + '.json'))
        refts[l[0]] = [(w[0], w[1] - a) for w in map_one(say(l), rj)]       # 参考音频自己的逐字时间（相对参考的发声起点）
    RF = {k: feats(v) for k, v in refs.items()}
    st0, en1 = voiced_span(y, SR)
    pos = max(st0 - 0.05, 0); bounds = []; starts = [st0]
    for k, i in enumerate(ids[:-1]):
        nx = ids[k + 1]
        tmpl = np.concatenate([refs[i], refs[nx][:int(1.5 * FS)]])
        TF = feats(tmpl); Li = RF[i].shape[1]
        w0 = max(pos - 0.4, 0); w1 = min(pos + 1.6 * len(refs[i]) / FS + 3, len(y16) / FS)
        WF = F[:, int(w0 / fr):int(w1 / fr)]
        D, wp = librosa.sequence.dtw(X=TF, Y=WF, metric='cosine', subseq=True)
        wp = wp[::-1]
        endi = [q for p_, q in wp if p_ <= Li - 1][-1]
        est = w0 + endi * fr
        cand = [p for p in pauses(db, hop, est - 0.35, est + 0.35, floor) if p[1] - p[0] >= 0.10]
        if cand:
            best = max(cand, key=lambda p: (p[1] - p[0]) - 0.6 * abs((p[0] + p[1]) / 2 - est))
            # 停顿两端：向外扩到真正的有声处（停顿可能延伸到搜索窗外）
            a_, b_ = best
            while a_ > 0 and db[int(a_ / hop) - 1] < floor: a_ -= hop
            while b_ < len(y) / SR and int(b_ / hop) < len(db) and db[int(b_ / hop)] < floor: b_ += hop
            bounds.append((a_, b_))
        else:
            i0, i1 = int((est - 0.35) / hop), int((est + 0.35) / hop)
            m = (i0 + int(np.argmin(db[i0:i1]))) * hop
            bounds.append((m, m)); rep.append(f'  {i}|{nx}：句界附近没有停顿，取能量最低点 {m:.2f}s')
        pos = (bounds[-1][0] + bounds[-1][1]) / 2
    # 每句：发声起止（停顿两端）与切点（停顿正中）
    spans = []
    for k, i in enumerate(ids):
        a_ = st0 if k == 0 else bounds[k - 1][1]
        b_ = en1 if k == len(ids) - 1 else bounds[k][0]
        spans.append((a_, b_))
    cuts = [max(spans[0][0] - 0.12, 0)] + [(spans[k][1] + spans[k + 1][0]) / 2 for k in range(len(ids) - 1)] + [min(spans[-1][1] + 0.4, len(y) / SR)]
    # ③ 校验
    fails = []
    for k, i in enumerate(ids):
        seg = y16[int(spans[k][0] * FS):int(spans[k][1] * FS)]
        SF_ = feats(seg)
        own = dtw_cost(RF[i], SF_)
        nb = [dtw_cost(RF[j], SF_) for j in (ids[k - 1] if k > 0 else None, ids[k + 1] if k + 1 < len(ids) else None) if j]
        ratio = (spans[k][1] - spans[k][0]) / (len(refs[i]) / FS)
        lo = 0.55 if len(refs[i]) / FS < 1.5 else 0.7       # 不到 1.5 秒的短句（如“巴菲特说：”）连读时本来就比单念短
        ok = all(own < x * 0.98 for x in nb) and lo <= ratio <= 1.4
        if not ok: fails.append(f'{i}: own {own:.3f} nb {[round(x, 3) for x in nb]} ratio {ratio:.2f}')
    rep.append('alignment check failures: ' + ('none' if not fails else '\n  ' + '\n  '.join(fails)))
    # 逐字时间戳交叉核对
    tj = json.load(open(take[:-4] + '.json'))
    mw = map_words(tj)
    miss = [(i, v[-1][1]) for i, v in mw.items() if v and v[-1][0] == 'miss']
    if miss: rep.append('时间戳没能对上的文本（只影响词锚点，回退按字数估算）：' + '; '.join(f'{i}「{m}」' for i, m in miss))
    dev = []
    for k, i in enumerate(ids):
        ws = [w for w in mw[i] if w[0] != 'miss']
        if ws: dev.append((abs(ws[0][1] - spans[k][0]), i))
    dev.sort(reverse=True)
    rep.append('句首：DTW 与逐字时间戳之差 最大 %s' % ', '.join(f'{i} {d:.2f}s' for d, i in dev[:5]))
    # ⑤ 输出（PSOLA 放慢指定章节）
    import parselmouth
    from parselmouth.praat import call
    out = os.path.join(work, 'vo'); os.makedirs(out, exist_ok=True)
    meta, gaps = {}, {}
    chap = {l[0]: l[1] for l in LINES}
    for k, i in enumerate(ids):
        c0, c1 = cuts[k], cuts[k + 1]; a_, b_ = spans[k]
        seg = y[int(c0 * SR):int(c1 * SR)].copy()
        f = STRETCH.get(i, STRETCH.get(chap[i], STRETCH.get('*', 1.0)))
        if f != 1.0:
            s = parselmouth.Sound(seg.astype(np.float64), SR)
            seg = call(s, 'Lengthen (overlap-add)', 60, 300, f).values[0].astype(np.float32)
        fl = int(0.008 * SR); seg[:fl] *= np.linspace(0, 1, fl); seg[-fl:] *= np.linspace(1, 0, fl)
        sf.write(os.path.join(out, f'{i}.wav'), seg, SR)
        # 逐字时间：参考音频的逐字时间戳 → 经 DTW 路径映射到本句录音（整篇的接口时间戳在后半段句首会挤成一团，不直接用）
        SF_ = feats(y16[int(a_ * FS):int(b_ * FS)])
        _, wp = librosa.sequence.dtw(X=RF[i], Y=SF_, metric='cosine'); wp = wp[::-1]
        rx, sx = wp[:, 0] * fr, wp[:, 1] * fr
        ct = []
        for j, tr_ in refts[i]:
            ts_ = float(np.interp(max(tr_, 0.0), rx, sx))
            if not ct or ts_ >= ct[-1][1]: ct.append([j, round(ts_ * f, 3)])
        meta[i] = dict(passage='take', lead=round((a_ - c0) * f, 3), dur=round((b_ - a_) * f, 3), tail=round((c1 - b_) * f, 3),
                       stretch=f, take=[round(c0, 3), round(c1, 3)], ct=ct)
        gaps[i] = None if k == 0 else round(spans[k][0] - spans[k - 1][1], 3)
    for k, i in enumerate(ids):
        meta[i]['gap'] = round(meta[i]['tail'] + meta[ids[k + 1]]['lead'], 3) if k + 1 < len(ids) else None
    json.dump(meta, open(os.path.join(out, 'vo.json'), 'w'), ensure_ascii=False, indent=0)
    json.dump(gaps, open(os.path.join(out, 'gaps.json'), 'w'), indent=0)
    # 各章语速（有声部分）
    for cid in dict.fromkeys(chap.values()):
        cs = [i for i in ids if chap[i] == cid]
        n = sum(len(PUN.sub('', say(next(l for l in LINES if l[0] == i)))) for i in cs)
        d = sum(meta[i]['dur'] for i in cs)
        rep.append(f'{cid}: 有声部分语速 {n / d:.2f} 字/秒（{len(cs)} 句，{d:.1f}s）')
    open(os.path.join(out, 'report.txt'), 'w').write('\n'.join(rep) + '\n')
    print('\n'.join(rep))
    return meta


if __name__ == '__main__':
    build(sys.argv[1])
