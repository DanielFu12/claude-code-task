"""v5 配乐剪辑：按“叙事节点”逐帧对位。

每一段配乐（Lyria 原创素材，work/music2/）给出若干锚点：(原曲内某个重拍/高潮的秒数, 成片里的叙事节点)。
相邻两个锚点之间：先在平稳处按“半小节”（2 拍，拍点对齐）剪掉或重复，使长度误差 ≤ 1 拍，
再用 rubberband（保持音高）做 ±几个百分点的微小变速，让下一个锚点“分毫不差”地落在节点上。
段落交接：下一段若以重拍进入，上一段在重拍前 0.45s 迅速“收气”（suck-back），让重拍炸开；
若下一段是安静进入，则两段交叉淡化。高潮前原曲里的上升音/镲片就落在收气区里，被去掉。

节点写法：'title' 'ch1'…'ch5' 'end' 'logo'（片尾 logo 重拍）、'sXX'（该句开始发声）、
'w:sXX:词'（该句里某个词开始发声的时刻，来自强制对齐）。
"""
import os, sys, json, subprocess, tempfile
import numpy as np

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))

# hit=True：这个锚点是要“点燃”的重拍（叠加低频冲击、前面收气）
SCORE = [
    dict(id='hook', cue='H_0', anchors=[(0.0, 'film0'), (23.12, 'title')], out=('fade', 'title', 2.6, 0.0), gain=-2.0),
    dict(id='title', cue='H_1', anchors=[(48.13, 'title', 1.0)], out=('fade', 'ch1', 1.8, 0.2), gain=0.0),
    dict(id='ch1', cue='C1_1', anchors=[(1.1, 'ch1'), (31.83, 's09', 0.6)], out=('fade', 'ch2', 1.0, 0.0), gain=-1.0),
    dict(id='ch2', cue='C2_0', anchors=[(20.45, 'ch2', 0.75), (62.1, 'w:s17d:芒格', 0.9)], loop=(64.0, 80.0),
         out=('suck', 'ch3'), gain=-2.5),
    dict(id='ch3', cue='C3_0', anchors=[(21.13, 'ch3', 0.7), (43.11, 'w:s28:376', 1.0)], out=('suck', 'ch4'), gain=0.0, ring_db=-8),
    dict(id='ch4', cue='C4_1', anchors=[(0.09, 'ch4', 0.9), (33.43, 's40', 1.0)], out=('fade', 'ch5', 1.4, 0.0), gain=-1.0),
    dict(id='ch5', cue='C5_1', anchors=[(7.7, 'ch5'), (35.12, 's47', 1.0), (44.11, 's48', 0.6)], out=('suck', 'logo'), gain=0.0),
    dict(id='logo', cue='C5_0', anchors=[(40.11, 'logo', 1.0)], out=('fade', 'total', 2.5, 0.0), gain=0.0),
]


# 补强重拍：从同一套配乐素材里取一记真实的管弦乐重击（H_1 32.1s：铜管 + 大鼓），叠在需要“宣告”的节点上
STINGERS = [('H_1', 32.1, 2.8, 's40', -4.0)]


def load(path):
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def stretch(x, ratio):
    """时长 ×ratio（保持音高），rubberband"""
    if abs(ratio - 1) < 2e-4: return x
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, 'a.f32'), os.path.join(d, 'b.f32')
        x.astype(np.float32).tofile(a)
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', a,
                        '-af', f'rubberband=tempo={1 / ratio:.6f}:transients=crisp:detector=compound:pitchq=quality',
                        '-f', 'f32le', '-ar', str(SR), '-ac', '2', b], check=True)
        y = np.fromfile(b, np.float32).reshape(-1, 2)
    n = int(round(len(x) * ratio))
    return y[:n] if len(y) >= n else np.concatenate([y, np.zeros((n - len(y), 2), np.float32)])


class Nodes:
    """叙事节点 → 成片时间"""
    def __init__(self, tl):
        self.tl = tl; self.seg = {s['id']: s for s in tl['segs']}

    def __call__(self, key):
        tl = self.tl
        if key == 'film0': return 0.0
        if key == 'total': return tl['total']
        if key == 'title': return tl['chapters']['title'][0]
        if key == 'logo': return tl['logo']
        if key in tl['chapters']: return tl['chapters'][key][0]
        if key.startswith('w:'):
            _, i, sub = key.split(':', 2)
            return word_time(self.seg[i], sub)
        return self.seg[key]['start']


def word_time(seg, sub):
    """句内某个词开始发声的时刻（有对齐数据时精确到字，否则按字数比例）"""
    sys.path.insert(0, HERE)
    from script import LINES, TEASE
    say = {l[0]: (l[3] or l[2]) for l in LINES}; say['tease'] = TEASE[1]
    txt = {l[0]: l[2] for l in LINES}; txt['tease'] = TEASE[0]
    i = seg['id']
    for src, exact in ((say[i], True), (txt[i], False)):
        k = src.find(sub)
        if k < 0: continue
        if exact and seg.get('ct'):
            for idx, t in seg['ct']:
                if idx >= k: return seg['start'] + t
        return seg['start'] + seg['dur'] * k / max(len(src), 1)
    raise KeyError(f'{sub} not in {i}')


def plan_interval(beats, a, b, df):
    """原曲 [a,b) 要占成片 df 秒：返回 [(s0,s1), ...] 片段（拍点对齐剪辑后）与变速比。
    优先按整小节（4 拍）剪/补，残差变速超过 2.5% 时依次改用半小节、1 拍，使变速尽量 ≤ ±3%"""
    best = None
    for unit_beats in (4, 2, 1):
        pieces, r = _plan(beats, a, b, df, unit_beats)
        if best is None or abs(r - 1) < abs(best[1] - 1) - 1e-9: best = (pieces, r)
        if abs(r - 1) <= 0.025: return pieces, r
    return best


def _plan(beats, a, b, df, ub):
    ds = b - a
    period = float(np.median(np.diff(beats)))
    unit = ub * period
    n = int(round((df - ds) / unit))
    pieces = [(a, b)]
    if n != 0:
        inner = [t for t in beats if a + 1.5 < t < b - 1.5 - (max(-n, 0) * unit)]
        if inner:
            mid = a + ds / 2
            e = inner[int(np.argmin([abs(t - mid) for t in inner]))]
            ei = int(np.argmin(np.abs(np.asarray(beats) - e)))
            if n < 0:                                     # 剪掉 [e, e + ub·|n| 拍)
                j = min(ei + ub * (-n), len(beats) - 1)
                pieces = [(a, e), (beats[j], b)]
            else:                                         # 重复 [e - ub·n 拍, e)
                j = max(ei - ub * n, 0)
                pieces = [(a, e), (beats[j], e), (e, b)]
    src_len = sum(p[1] - p[0] for p in pieces)
    return pieces, df / src_len


def xcat(chunks, xf=int(0.045 * SR)):
    out = chunks[0]
    for c in chunks[1:]:
        if len(out) < xf or len(c) < xf: out = np.concatenate([out, c]); continue
        w = np.sin(np.linspace(0, np.pi / 2, xf))[:, None]
        mid = out[-xf:] * np.cos(np.linspace(0, np.pi / 2, xf))[:, None] + c[:xf] * w
        out = np.concatenate([out[:-xf], mid, c[xf:]])
    return out


def sweep_lp(audio, t, h, dur=1.5):
    """[h-dur, h] 内低通截止频率从 12kHz 指数扫到 700Hz（交叉淡化 4 个固定截止的低通版本）"""
    from scipy import signal
    k = np.clip((t - (h - dur)) / dur, 0, 1) * (t < h)          # 只作用在重拍之前，重拍一到立刻恢复全频
    if not (k > 0).any(): return audio
    fcs = [12000, 5000, 2200, 700]
    lows = [signal.sosfiltfilt(signal.butter(4, f, 'low', fs=SR, output='sos'), audio, axis=0) for f in fcs]
    pos = k * (len(fcs) - 1)
    on = (k > 0)[:, None]
    out = np.where(on, 0.0, audio)
    for i in range(len(fcs)):
        w = np.clip(1 - np.abs(pos - i), 0, 1) * (k > 0)
        out = out + lows[i] * w[:, None]
    return out.astype(np.float32)


def reverb_tail(x, db, rt=2.5, seed=3):
    from scipy import signal
    rng = np.random.default_rng(seed)
    n = int(rt * SR); tt = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)) * np.exp(-6.9 * tt / rt)[:, None]
    ir = signal.sosfilt(signal.butter(2, 1800, 'low', fs=SR, output='sos'), ir, axis=0)
    ir /= np.sqrt((ir ** 2).sum(0))
    y = np.stack([signal.fftconvolve(x[:, c], ir[:, c]) for c in range(2)], 1)
    y *= 10 ** (db / 20) * np.sqrt(len(x)) / max(np.sqrt((y ** 2).sum() / 2), 1e-9) * np.sqrt((x ** 2).mean())
    return y[len(x) // 2:].astype(np.float32)


def ix(t):
    """原曲秒 → 采样下标（重拍前 12ms 下刀，保住起音；不小于 0）"""
    return max(int(t * SR) - int(0.012 * SR), 0)


def content_end(x, after):
    """原曲在 after 之后真正结束的位置（后面超过 1s 的近乎静音不算）"""
    w = int(0.25 * SR)
    r = np.sqrt(np.convolve((x ** 2).mean(1), np.ones(w) / w, 'same'))[::w]
    db = 20 * np.log10(r + 1e-9)
    i0 = int(after / 0.25)
    for i in range(i0, len(db) - 4):
        if (db[i:i + 4] < -50).all(): return i * 0.25
    return len(x) / SR


def build(work, tl, N):
    beats_all = json.load(open(os.path.join(work, 'music2', 'beats.json')))
    node = Nodes(tl)
    mus = np.zeros((N, 2), np.float32)
    hits, report = [], []
    pre = int(0.012 * SR)                                     # 重拍前 12ms 下刀，保住起音
    for sec in SCORE:
        x = load(os.path.join(work, 'music2', sec['cue'] + '.mp3'))
        beats = beats_all[sec['cue']]['beats']
        anc = [(a[0], node(a[1]), a[2] if len(a) > 2 else 0.0) for a in sec['anchors']]
        chunks = []
        start_film = anc[0][1]
        for (sa, fa, _), (sb, fb, _) in zip(anc, anc[1:]):
            pieces, r = plan_interval(beats, sa, sb, fb - fa)
            seg = xcat([x[ix(p0):ix(p1)] for p0, p1 in pieces])
            chunks.append(stretch(seg, r))
            report.append(f"{sec['id']}: {sa:.2f}->{sb:.2f}s 原曲 {sb - sa:.2f}s → 成片 {fb - fa:.2f}s，"
                          f"剪辑 {'/'.join(f'{p0:.2f}-{p1:.2f}' for p0, p1 in pieces)}，变速 {(r - 1) * 100:+.1f}%")
        # 最后一个锚点之后：原速播到交接点（不够长就在 loop 区间按整小节循环）
        kind, until_key = sec['out'][0], sec['out'][1]
        until = node(until_key) + (sec['out'][3] if kind == 'fade' else 0.0)
        sl = anc[-1][0]; need = until - anc[-1][1] + 0.05
        cend = content_end(x, sl)
        tail = x[ix(sl):ix(cend)]
        if len(tail) / SR < need:
            lz = sec.get('loop') or (max(sl, cend - 20), cend - 4)
            bs = [t for t in beats if lz[0] <= t <= lz[1]]
            a0, a1 = bs[0], bs[len(bs) - 1 - ((len(bs) - 1) % 4)]
            body = x[ix(sl):ix(a1)]; loopc = x[ix(a0):ix(a1)]
            parts = [body]
            while sum(len(p) for p in parts) / SR < need: parts.append(loopc)
            tail = xcat(parts)
            report.append(f"{sec['id']}: 尾段循环 {a0:.2f}-{a1:.2f}s")
        chunks.append(tail[:int(need * SR)])
        audio = xcat(chunks) if len(chunks) > 1 else chunks[0]
        n = len(audio); t = np.arange(n) / SR + start_film
        g = np.ones(n, np.float32)
        g[:int(0.006 * SR)] = np.linspace(0, 1, int(0.006 * SR))
        if kind == 'fade':
            fl = sec['out'][2]
            g *= np.clip((until - t) / fl, 0, 1) ** 1.5
        else:                                                # 收气：重拍前 1.5s 低通扫频（去掉原曲的上升音/镲片），0.45s 内降到 -24dB
            h = node(until_key)
            audio = sweep_lp(audio, t, h)
            k = np.clip((t - (h - 0.45)) / 0.41, 0, 1)
            g *= (1 - k) + k * 10 ** (-24 / 20)
            ring_src = audio[(t >= h - 0.7) & (t < h - 0.45)] * 10 ** (sec.get('gain', 0) / 20)
            g[t >= h - 0.04] = 0
        for sa, fa, w in anc[1:]:                            # 段内重拍：同样先收气（1.2s 低通扫频 + 最后 0.3s 下潜 10dB），再炸开
            if w >= 0.6:
                audio = sweep_lp(audio, t, fa, 1.2)
                kk = np.clip((t - (fa - 0.3)) / 0.27, 0, 1) * (t < fa - 0.02)
                g *= 1 - kk * (1 - 10 ** (-10 / 20))
            if w >= 0.9:                                     # 最重的重拍：前 3s 音乐慢慢退后 6dB，形成“蓄力→爆发”的反差
                ramp = np.clip((t - (fa - 3.0)) / 2.7, 0, 1) * (t < fa)
                g *= 10 ** (-6 * ramp / 20)
        if anc[0][2] <= 0 and sec['id'] != 'hook':           # 不是重拍进入：0.8s 柔和淡入，避免半句切入的电平跳变
            g *= np.clip((t - start_film) / 0.8, 0, 1) ** 1.5
        audio = audio * g[:, None] * 10 ** (sec.get('gain', 0) / 20)
        if kind == 'suck' and len(ring_src):                 # 转场尾音：上一段的最后一口气化作 2.5s 低沉混响拖尾，“沉下去”而不是被掐断
            tail_ring = reverb_tail(ring_src, sec.get('ring_db', -12))
            j = int(round((h - 0.02) * SR)); m = min(len(tail_ring), N - j)
            if m > 0: mus[j:j + m] += tail_ring[:m]
        i0 = int(round(start_film * SR)) - pre
        i0c = max(i0, 0); audio = audio[i0c - i0:]
        m = min(len(audio), N - i0c)
        mus[i0c:i0c + m] += audio[:m]
        for sa, fa, w in anc:
            if w > 0: hits.append((round(fa, 3), w, sec['id']))
    for cue, src_t, dur, key, db in STINGERS:
        x = load(os.path.join(work, 'music2', cue + '.mp3'))
        st = x[ix(src_t):ix(src_t) + int(dur * SR)].copy()
        fo = int(1.2 * SR); st[-fo:] *= np.cos(np.linspace(0, np.pi / 2, fo))[:, None] ** 2
        j = int(round(node(key) * SR)) - int(0.012 * SR); m = min(len(st), N - j)
        mus[j:j + m] += st[:m] * 10 ** (db / 20)
        report.append(f'补强重拍 {cue}@{src_t}s → {key} ({node(key):.2f}s)')
    return mus, hits, report


def analyze(work):
    """各段配乐素材的拍点（librosa，按 90 BPM 先验、高 tightness），写 work/music2/beats.json"""
    import librosa
    out = {}
    for cue in sorted({sec['cue'] for sec in SCORE} | {c for c, *_ in STINGERS}):
        y, sr = librosa.load(os.path.join(work, 'music2', cue + '.mp3'), sr=22050)
        on = librosa.onset.onset_strength(y=y, sr=sr, hop_length=256)
        _, bf = librosa.beat.beat_track(onset_envelope=on, sr=sr, hop_length=256, start_bpm=90, tightness=400)
        out[cue] = dict(beats=[round(float(b), 3) for b in librosa.frames_to_time(bf, sr=sr, hop_length=256)], dur=len(y) / sr)
    json.dump(out, open(os.path.join(work, 'music2', 'beats.json'), 'w'))


if __name__ == '__main__':
    work = sys.argv[1]
    if '--beats' in sys.argv: analyze(work); sys.exit()
    tl = json.load(open(os.path.join(work, 'timeline.json')))
    if 'logo' not in tl: tl['logo'] = json.load(open(os.path.join(work, 'music_plan.json')))['hits']['logo']
    N = int((tl['total'] + 0.5) * SR)
    mus, hits, rep = build(work, tl, N)
    for r in rep: print(r)
    print('hits', hits)
    import soundfile as sf
    sf.write(os.path.join(work, 'score_test.wav'), mus, SR, subtype='PCM_16')
