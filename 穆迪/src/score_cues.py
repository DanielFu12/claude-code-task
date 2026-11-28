"""配乐（第二版，按第二季第一期教训重做）：用高质量授权音乐按叙事剪辑、卡点，取代 score.py 的程序作曲。

曲目：Kevin MacLeod（incompetech.com），CC BY 4.0，可商用，片尾与 docs/SOURCES.md 署名。源文件下载到 work/music_src/（不入库）。
做法：
  · 每个 cue 把某首曲子的一段 [τa, τb] 放到时间线 [Ta, Tb]；两个锚点之间允许 ±3% 以内的变速（ffmpeg atempo，听不出来），
    让曲子里选好的重拍（段落进入、乐队齐奏）正好落在旁白的关键词或画面切换上；
  · “抽空再重拍”：重拍前留 0.4–0.6 秒真正的静默；设问处整段静默；
  · 不循环：同一首曲子的同一段不重复使用；每个 cue 都取曲子里有发展的段落（引子、推进、高潮），按能量曲线排；
  · 输出 WORK/music/score_raw.wav（48 kHz 立体声，−18 LUFS）与 beats.json（重拍时刻给画面用）。
python3 src/score_cues.py WORK [起-止秒]      # 可只渲染一段（做小样）
"""
import os, sys, json, subprocess
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES

WORK = sys.argv[1] if len(sys.argv) > 1 else 'work'
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SRC = os.path.join(WORK, 'music_src')
SR = 48000
TL = json.load(open(os.path.join(WORK, 'timeline.json')))
SEG = {s['id']: s for s in TL['segs']}
CH = TL['chapters']
_SAY = {l[0]: (l[3] or l[2]) for l in LINES}

TRACKS = {   # 简称: (文件名, 作者, 授权, 链接)
    'descent': ('The Descent.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'heroic': ('Heroic Age.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'unwritten': ('Unwritten Return.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
}


def S(i): return SEG[i]['start']
def E(i): return SEG[i]['start'] + SEG[i]['dur']


def WT(i, sub):
    k = _SAY[i].find(sub)
    if k < 0: raise KeyError((i, sub))
    for idx, tt in SEG[i].get('ct', []):
        if idx >= k: return S(i) + tt
    return S(i) + SEG[i]['dur'] * k / max(len(_SAY[i]), 1)


_cache = {}
def load(name, ta, tb, rate):
    """取曲子 [ta, tb]，按 rate 变速（rate>1 变快），返回 48k 立体声"""
    key = (name, round(ta, 3), round(tb, 3), round(rate, 5))
    if key not in _cache:
        assert 0.97 <= rate <= 1.03, f'{name} 变速 {rate:.3f} 超过 ±3%'
        f = os.path.join(SRC, TRACKS[name][0])
        af = f'atempo={rate:.5f}' if abs(rate - 1) > 1e-4 else 'anull'
        x = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{ta:.3f}', '-t', f'{tb - ta:.3f}', '-i', f, '-af', af,
                            '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
        _cache[key] = np.frombuffer(x, np.float32).reshape(-1, 2).copy()
    return _cache[key]


CUES = []      # dict(name, Ta, Tb, ta, tb, fi, fo, db)
HITS = []      # 重拍时刻（画面闪光、混音时短暂放开闪避）


def cue(name, Ta, Tb, anchor, rate=1.0, fi=0.08, fo=0.25, db=0.0, hit=False):
    """anchor = (T, τ)：曲子 τ 处落在时间线 T；rate 为变速"""
    T0, t0 = anchor
    ta = t0 + (Ta - T0) * rate; tb = t0 + (Tb - T0) * rate
    CUES.append(dict(name=name, Ta=Ta, Tb=Tb, ta=ta, tb=tb, rate=rate, fi=fi, fo=fo, db=db))
    if hit: HITS.append(round(T0, 3))


def cue2(name, Ta, Tb, a1, a2, **kw):
    """两个锚点 (T1, τ1)、(T2, τ2)：按两点定变速，保证两个重拍都对齐"""
    (T1, t1), (T2, t2) = a1, a2
    cue(name, Ta, Tb, a1, rate=(t2 - t1) / (T2 - T1), **kw)


def plan():
    title = CH['title'][0]; ch1 = CH['ch1'][0]
    # ======== 开场
    # h1–h2：The Descent 引子（低音弦乐 + 鼓点，一路收紧）→ “83%”前 0.45 秒静默 → 乐队齐奏重拍（曲中 117.14 s）落在“百分之八十三”
    t83 = WT('h2', '百分之八十三')
    cue('descent', 0.0, t83 - 0.45, (0.0, 0.0), fi=0.02, fo=0.10, db=-4.0)
    cue('descent', t83 - 0.03, E('h3') + 0.6, (t83, 117.14), fi=0.01, fo=1.0, db=1.5, hit=True)
    # h4 设问：静默（只剩上一段的余音）
    # h5 反转：“可是到了 2025 年”Heroic Age 中段推进进入；“六十四美元”对齐曲中 39.78 s 的重拍；
    #     一路推到“凭什么”，字落下后 0.45 秒静默，片名落在曲子最大的齐奏（60.07 s）
    tq = E('h7')
    a1 = (WT('h5', '六十四美元'), 39.78); a2 = (title, 60.07)
    cue2('heroic', S('h5') - 0.15, tq + 0.02, a1, a2, fi=0.12, fo=0.08, db=-1.0)
    HITS.append(round(a1[0], 3))
    cue('heroic', title - 0.02, ch1 + 2.6, (title, 60.07), fi=0.01, fo=1.4, db=3.0, hit=True)
    # ======== 第一章开头：Unwritten Return（钢琴 + 合成器，神秘的历史感），在章节卡上淡入
    cue('unwritten', ch1 + 1.6, CH['ch2'][0] + 0.5, (ch1 + 1.6, 0.07), fi=1.0, fo=1.5, db=-2.0)


def render(t_from=0.0, t_to=None):
    plan()
    total = TL['total'] + 1.0
    N = int(total * SR); out = np.zeros((N, 2), np.float32)
    for c in CUES:
        if t_to is not None and c['Ta'] > t_to: continue
        x = load(c['name'], c['ta'], c['tb'], c['rate'])
        n = min(len(x), int((c['Tb'] - c['Ta']) * SR))
        x = x[:n] * 10 ** (c['db'] / 20)
        fi, fo = int(c['fi'] * SR), int(c['fo'] * SR)
        if fi: x[:fi] *= np.linspace(0, 1, fi)[:, None]
        if fo: x[-fo:] *= np.linspace(1, 0, fo)[:, None]
        p = int(c['Ta'] * SR); e = min(p + n, N)
        out[p:e] += x[:e - p]
    import pyloudnorm as pyln
    seg = out[int(t_from * SR):int((t_to or total) * SR)]
    out *= 10 ** ((-18.0 - pyln.Meter(SR).integrated_loudness(seg)) / 20)
    os.makedirs(os.path.join(WORK, 'music'), exist_ok=True)
    sf.write(os.path.join(WORK, 'music', 'score_raw.wav'), out, SR, subtype='PCM_24')
    # 节拍：取每个 cue 所用曲子的节拍，映射到时间线（画面的节拍脉动用）
    import librosa
    beats = []
    for c in CUES:
        y, sr = librosa.load(os.path.join(SRC, TRACKS[c['name']][0]), sr=22050, offset=max(c['ta'], 0), duration=c['tb'] - c['ta'])
        _, b = librosa.beat.beat_track(y=y, sr=sr)
        beats += [round(c['Ta'] + float(t) / c['rate'], 3) for t in librosa.frames_to_time(b, sr=sr)]
    json.dump(dict(beats=sorted(beats), hits=sorted(HITS), soft=[]), open(os.path.join(WORK, 'music', 'beats.json'), 'w'))
    print('cues', len(CUES), 'hits', sorted(HITS))
    for c in CUES: print(f"  {c['name']:10} T {c['Ta']:7.2f}–{c['Tb']:7.2f}  曲中 {c['ta']:7.2f}–{c['tb']:7.2f}  变速 {c['rate']:.4f}")


if __name__ == '__main__':
    a, b = (map(float, sys.argv[2].split('-')) if len(sys.argv) > 2 else (0.0, None))
    render(a, b)
