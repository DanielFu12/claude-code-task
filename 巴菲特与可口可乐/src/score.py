"""配乐剪辑：一套统一的音乐语言贯穿全片，并在少数叙事节点上逐帧对位。

v6：三大段同调（D 小调 → D 大调）、同速（84 BPM）、同一主题动机的连续原创配乐（work/music3/，Lyria 生成），
段与段之间同调长交叉淡化；只在 5 个关键节点（标题、376 亿、因为生意没有变坏、主题句、片尾 logo）以及
“多因素合奏效应”处，用配乐自身的高潮“点燃”——不再收气、不再忽大忽小、不叠加外来素材。

对位方法：相邻两个锚点之间按整小节（不得已时半小节）剪辑/重复，再做保持音高的 rubberband 微变速，
让锚点（原曲内的高潮起点）分毫不差地落在叙事节点上。

节点写法：'title' 'ch1'…'ch5' 'end' 'logo'、'sXX'（该句开始发声）、'w:sXX:词'（该句里某个词开始发声，来自强制对齐）。
锚点 (原曲秒, 节点, 权重)：权重 > 0 表示这是一个“点燃”的高潮，叠加很轻的低频冲击。
"""
import os, sys, json, subprocess, tempfile
import numpy as np

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
MDIR = 'music3'

SCORE = [
    dict(id='P1', cue='P1_2', anchors=[(0.0, 'film0'), (23.53, 'title', 1.0)],
         out=('fade', 'ch2', 3.0, 0.9)),                                   # 开场 + 第一章
    dict(id='P2', cue='P2_2', anchors=[(0.10, 'ch2'), (34.00, 'w:s17d:芒格', 0.6), (90.47, 'w:s28:376', 1.0)],
         fade_in=1.5, out=('fade', 'ch4', 9.0, 0.9)),                      # 第二、三章；第三章最后一句起高潮慢慢退下，再转入第四章
    dict(id='P3', cue='P3_2', anchors=[(0.07, 'ch4'), (32.97, 's40', 0.8), (79.85, 's47', 1.0)],
         fade_in=1.5, out=('bed', 'end', 'logo', -15.0)),                  # 第四、五章；片尾预告时退成远处的低垫
    dict(id='logo', cue='P3_2', anchors=[(123.88, 'logo', 1.0)], out=('fade', 'total', 2.5, 0.0)),   # 同一首曲子的终和弦
]


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
    for unit_beats in (4, 2):
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
    beats_all = json.load(open(os.path.join(work, MDIR, 'beats.json')))
    node = Node = Nodes(tl)
    mus = np.zeros((N, 2), np.float32)
    hits, report = [], []
    from scipy import signal
    for sec in SCORE:
        x = load(os.path.join(work, MDIR, sec['cue'] + '.mp3'))
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
        kind = sec['out'][0]
        if kind == 'fade': until = node(sec['out'][1]) + sec['out'][3]
        else: until = node(sec['out'][2])
        sl = anc[-1][0]; need = until - anc[-1][1] + 0.05
        cend = content_end(x, sl)
        tail = x[ix(sl):ix(cend)]
        lz = sec.get('loop') or (max(sl, cend - 20), cend - 4)
        bs = [t for t in beats if lz[0] <= t <= lz[1]]
        if len(tail) / SR < need and len(bs) < 5:              # 终和弦等：原样放完，余下补静音
            tail = np.concatenate([x[ix(sl):], np.zeros((int(need * SR), 2), np.float32)])
        elif len(tail) / SR < need:
            a0, a1 = bs[0], bs[len(bs) - 1 - ((len(bs) - 1) % 4)]
            parts = [x[ix(sl):ix(a1)]]
            while sum(len(p) for p in parts) / SR < need: parts.append(x[ix(a0):ix(a1)])
            tail = xcat(parts)
            report.append(f"{sec['id']}: 尾段循环 {a0:.2f}-{a1:.2f}s")
        chunks.append(tail[:int(need * SR)])
        audio = xcat(chunks) if len(chunks) > 1 else chunks[0]
        n = len(audio); t = np.arange(n) / SR + start_film
        g = np.ones(n, np.float32)
        fi = sec.get('fade_in', 0.006)
        g *= np.clip((t - start_film) / fi, 0, 1) ** 1.5
        if kind == 'fade':
            g *= np.clip((until - t) / sec['out'][2], 0, 1) ** 1.5
        else:                                                # 退成低垫：3.5s 内降到 bed dB 并蒙上低通，logo 前 0.6s 淡出
            e0 = node(sec['out'][1]) - 1.0; db = sec['out'][3]
            k = np.clip((t - e0) / 3.5, 0, 1)
            low = signal.sosfiltfilt(signal.butter(2, 900, 'low', fs=SR, output='sos'), audio, axis=0)
            audio = audio * (1 - k)[:, None] + low * k[:, None]
            g *= 10 ** (db * k / 20)
            g *= np.clip((until - 0.15 - t) / 0.6, 0, 1)
        audio = audio * g[:, None] * 10 ** (sec.get('gain', 0) / 20)
        i0 = int(round(start_film * SR)) - int(0.012 * SR)
        i0c = max(i0, 0); audio = audio[i0c - i0:]
        m = min(len(audio), N - i0c)
        mus[i0c:i0c + m] += audio[:m]
        for sa, fa, w in anc:
            if w > 0: hits.append((round(fa, 3), w, sec['id']))
    return mus, hits, report


def analyze(work):
    """各段配乐素材的拍点（librosa，按 84 BPM 先验、高 tightness），写 work/music3/beats.json"""
    import librosa
    out = {}
    for cue in sorted({sec['cue'] for sec in SCORE}):
        y, sr = librosa.load(os.path.join(work, MDIR, cue + '.mp3'), sr=22050)
        on = librosa.onset.onset_strength(y=y, sr=sr, hop_length=256)
        _, bf = librosa.beat.beat_track(onset_envelope=on, sr=sr, hop_length=256, start_bpm=84, tightness=400)
        out[cue] = dict(beats=[round(float(b), 3) for b in librosa.frames_to_time(bf, sr=sr, hop_length=256)], dur=len(y) / sr)
    json.dump(out, open(os.path.join(work, MDIR, 'beats.json'), 'w'))


if __name__ == '__main__':
    work = sys.argv[1]
    if '--beats' in sys.argv: analyze(work); sys.exit()
    tl = json.load(open(os.path.join(work, 'timeline.json')))
    N = int((tl['total'] + 0.5) * SR)
    mus, hits, rep = build(work, tl, N)
    for r in rep: print(r)
    print('hits', hits)
    import soundfile as sf
    sf.write(os.path.join(work, 'score_test.wav'), mus, SR, subtype='PCM_16')
