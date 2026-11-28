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
    'investigations': ('Investigations.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'thinking': ('Thinking Music.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'despair': ('Despair and Triumph.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'undaunted': ('Undaunted.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'hitman': ('Hitman.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'rynos': ('Rynos Theme.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'decisions': ('Decisions.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'legend': ('Truth of the Legend.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
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
        pre = max(0.0, -ta); ta0 = max(ta, 0.0)              # 起点早于曲子开头：前面补静音
        x = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{ta0:.3f}', '-t', f'{tb - ta0:.3f}', '-i', f, '-af', af,
                            '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
        y = np.frombuffer(x, np.float32).reshape(-1, 2)
        _cache[key] = np.concatenate([np.zeros((int(pre / rate * SR), 2), np.float32), y])
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
    sot = {x['id'][4:]: (x['start'] - x.get('lead', 0), x['start'] + x['dur']) for x in TL['segs'] if x.get('kind') == 'sot'}
    ch = lambda k: CH[k][0]

    def bed(sid, tau0):
        """原声下只留铺底：Despair and Triumph 的钢琴段落（每段原声取曲子不同的地方）"""
        a_, b_ = sot[sid]
        cue('despair', a_ - 0.5, b_ + 0.6, (a_ - 0.5, tau0), fi=0.6, fo=0.8, db=-5.0)

    # ======== 第一章 打分的生意：Unwritten Return（钢琴 + 合成器，神秘的历史感）；“倒了过来”抽空 → 重拍（曲中 56.31 s）
    td = WT('c1d', '倒了过来')
    tc = S('c1c') - 0.3                                   # 评级阶梯：换到曲子 186 s 起较空的织体（先落再起），避免 20 秒平直
    cue('unwritten', ch1 + 1.6, tc + 0.4, (ch1 + 1.6, 0.07), fi=1.0, fo=0.5, db=-2.0)
    cue('unwritten', tc, td - 0.42, (tc, 186.0), fi=0.4, fo=0.12, db=-1.0)
    cue('unwritten', td - 0.02, ch('ch2') + 0.3, (td, 56.31), fi=0.01, fo=1.2, db=-1.0, hit=True)
    # ======== 第二章 他看中了什么：Investigations（拨弦，好奇）→ 原声铺底 → Thinking Music（弦乐 + 竖琴，悬疑）→ 原声铺底 → Thinking Music 后段
    cue('investigations', ch('ch2') - 0.02, sot['pricing'][0] + 0.2, (ch('ch2'), 0.0), fi=0.01, fo=1.0, db=1.0, hit=True)
    bed('pricing', 0.0)
    cue('thinking', sot['pricing'][1] + 0.2, sot['unwilling'][0] + 0.2, (sot['pricing'][1] + 0.2, 95.0), fi=0.6, fo=1.0, db=2.5)
    bed('unwilling', 60.0)
    cue('thinking', sot['unwilling'][1] + 0.2, ch('ch3') + 0.3, (WT('c2g', '离不开'), 121.0), fi=0.5, fo=1.0, db=2.5)
    HITS.append(round(WT('c2g', '离不开'), 3))
    # ======== 第三章 护城河：Undaunted（钢琴 + 合成器驱动，史诗感）；“两关”进入，“百分之九十四”落在曲中 61 s 的高点；
    #          原声铺底；“大家都认它”落在曲中 108 s 齐奏段的开头
    t94 = WT('c3b', '百分之九十四')
    cue('undaunted', ch('ch3') - 0.02, t94 - 0.42, (t94, 61.0), fi=0.01, fo=0.12, db=2.0, hit=True)
    cue('undaunted', t94 - 0.02, sot['duopoly'][0] + 0.2, (t94, 61.0), fi=0.01, fo=1.0, db=3.0)
    HITS.append(round(t94, 3))
    bed('duopoly', 125.0)
    tk = WT('c3g', '大家都认它')
    cue('undaunted', sot['duopoly'][1] + 0.2, tk - 0.42, (tk, 108.0), fi=0.8, fo=0.12, db=2.0)
    cue('undaunted', tk - 0.02, ch('ch4') + 0.3, (tk, 108.0), fi=0.01, fo=1.0, db=4.0, hit=True)
    # ======== 第四章 关键齿轮：Hitman（低音弦乐 + 合唱，黑暗）；原声铺底；“八成”前静默 → 曲中 52 s 的齐奏进入
    cue('hitman', ch('ch4') - 0.02, sot['delusion'][0] + 0.2, (ch('ch4'), 0.0), fi=0.01, fo=1.0, db=-2.0, hit=True)
    bed('delusion', 30.0)
    t8 = WT('c4f', '八成')
    cue('hitman', sot['delusion'][1] + 0.2, t8 - 0.45, (t8, 52.0), fi=0.8, fo=0.10, db=-2.0)
    cue('hitman', t8 - 0.02, ch('ch5') + 0.3, (t8, 52.0), fi=0.01, fo=1.0, db=0.0, hit=True)
    # ======== 第五章 信誉崩了，生意还在：设问处静默 →“没有”落在 Rynos Theme 30 s 的齐奏；原声铺底；“五十一倍”落在曲中 130 s 的最高点
    tn = WT('c5b', '没有')
    tm = WT('c5d', '护城河却还在'); t5d = S('c5d') - 0.3
    cue('rynos', tn - 0.02, t5d + 0.4, (tn, 30.0), fi=0.01, fo=0.6, db=-1.0, hit=True)
    cue('rynos', t5d, tm - 0.42, (t5d, 84.0), fi=0.4, fo=0.12, db=-3.0)                 # 回顾可口可乐：曲子较空的一段，先落
    cue('rynos', tm - 0.02, sot['mistake'][0] + 0.2, (tm, 47.0), fi=0.01, fo=0.8, db=0.0, hit=True)   # “护城河却还在”重拍
    bed('mistake', 90.0)
    t51 = WT('c5i', '五十一倍')
    cue('rynos', sot['mistake'][1] + 0.2, t51 - 0.42, (t51, 130.0), fi=0.6, fo=0.10, db=-1.0)
    cue('rynos', t51 - 0.02, ch('ch6') + 0.3, (t51, 130.0), fi=0.01, fo=1.0, db=2.0, hit=True)
    # ======== 第六章 还能好多久：Decisions（低沉合成器脉冲，悬疑）
    cue('decisions', ch('ch6') - 0.02, ch('ch7') + 0.3, (ch('ch6'), 1.5), fi=0.01, fo=1.0, db=-3.0, hit=True)
    # ======== 第七章 带走什么：Heroic Age 开头（主题再现）；“没得选”落在曲中 30.53 s 的重拍
    te = WT('c7e', '没得选')
    cue2('heroic', ch('ch7') - 0.02, S('p1') - 0.1, (ch('ch7'), 0.0), (te, 30.53), fi=0.01, fo=0.8, db=-1.0)
    HITS.extend([round(ch('ch7'), 3), round(te, 3)])
    # ======== 下期预告：Truth of the Legend（史诗推进）；“下一期”落在强拍，logo 落在曲中 73 s 的最高点
    logo = TL['logo']
    cue2('legend', S('p1') - 0.3, TL['total'] + 0.5, (WT('p2', '下一期'), 58.3), (logo, 73.0), fi=0.6, fo=3.0, db=0.0)
    HITS.extend([round(WT('p2', '下一期'), 3), round(logo, 3)])


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
