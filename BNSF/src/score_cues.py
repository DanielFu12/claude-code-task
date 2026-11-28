"""配乐（第二版，按第二季第一期教训重做）：用高质量授权音乐按叙事剪辑、卡点，取代 score.py 的程序作曲。

曲目：Kevin MacLeod（incompetech.com），CC BY 4.0，可商用，片尾与 docs/SOURCES.md 署名。源文件下载到 work/music_src/（不入库）。
做法：
  · 每个 cue 把某首曲子的一段 [τa, τb] 放到时间线 [Ta, Tb]；两个锚点之间允许 ±3% 以内的变速（ffmpeg atempo，听不出来），
    让曲子里选好的重拍（段落进入、乐队齐奏）正好落在旁白的关键词或画面切换上；
  · “抽空再重拍”：重拍前留 0.4–0.6 秒真正的静默；设问处整段静默；
  · 不循环：同一首曲子的同一段不重复使用；每个 cue 都取曲子里有发展的段落（引子、推进、高潮），按能量曲线排；
  · 输出 WORK/music/score_raw.wav（48 kHz 立体声，−18 LUFS）与 beats.json（重拍时刻给画面用）。
python3 src/score_cues.py WORK [起-止秒]      # 可只渲染一段（做小样）
第二季第二期（BNSF）曲目与卡点见 plan()。
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
    'industrial': ('Industrial Cinematic.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'rising': ('Rising Game.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'hiding': ('Hiding Your Reality.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'vale': ('Ascending the Vale.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'feather': ('Blue Feather.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'prelude': ('Prelude and Action.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'interloper': ('Interloper.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'dreams': ('Dreams Become Real.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'achilles': ('Achilles.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'constance': ('Constance.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
    'mining': ('Mining by Moonlight.mp3', 'Kevin MacLeod', 'CC BY 4.0', 'https://incompetech.com'),
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
    sot = {x['id'][4:]: (x['start'] - x.get('lead', 0), x['start'] + x['dur']) for x in TL['segs'] if x.get('kind') == 'sot'}
    ch = lambda k: CH[k][0]
    G = 0.42                                              # 重拍前的静默
    # ======== 开场：Industrial Cinematic（112 拍，机械脉冲，像车轮压过铁轨）
    #   曲子开头的重音（0.06 s）在 h1 刚开口后进入；“五千亿”前静默 → 曲中 8.78 s 的重音；“三百四十五亿”落在 15.33 s 的重音
    t5k = WT('h2', '五千亿'); t345 = WT('h3', '三百四十五亿')
    cue2('industrial', t5k - 8.72, t5k - G, (t5k, 8.78), (t345, 15.33), fi=0.02, fo=0.10, db=-3.0)
    cue2('industrial', t5k - 0.02, WT('h4', '哎哟') - 0.35, (t5k, 8.78), (t345, 15.33), fi=0.01, fo=0.30, db=-1.0, hit=True)
    HITS.append(round(t345, 3))
    #   “哎哟”：整段抽空（只有旁白）。h5“吃资本”Rising Game 进入，一路推到片名，片名落在曲子平台段的第一个重音（71.25 s）
    #   h5 用曲子开头较空的织体（压低）；h6 抬到曲子推进段；“巴菲特为什么还说”前抽空 0.4 秒再推向片名
    th6 = S('h6'); tw = WT('h6', '巴菲特为什么还说')
    cue('rising', S('h5') - 0.1, th6 - 0.25, (S('h5') - 0.1, 0.0), fi=0.15, fo=0.4, db=0.0)
    cue('rising', th6 - 0.3, tw - 0.38, (title, 71.25), fi=0.3, fo=0.08, db=-2.0)
    cue('rising', tw - 0.02, title + 0.6, (title, 71.25), fi=0.02, fo=0.05, db=0.0)
    HITS.extend([round(S('h5'), 3), round(tw, 3)])
    cue('rising', title - 0.02, ch1 + 1.6, (title, 71.25), fi=0.01, fo=1.2, db=2.5, hit=True)

    def bed(sid, tau0):
        """原声下只留铺底：Blue Feather 的钢琴"""
        a_, b_ = sot[sid]
        cue('feather', a_ - 0.5, b_ + 0.5, (a_ - 0.5, tau0), fi=0.5, fo=0.6, db=-4.0)

    # ======== 第一章 恐惧里的报价：Hiding Your Reality（144 拍，紧张的弦乐脉冲）
    #   开头较空，随危机、见面、三季报一路收紧；“十一天后”前静默 → 曲中 71.54 s 的齐奏（宣布交易）；
    #   c1g 讲“很勉强”时曲子自己落下（98–100 s 处收薄）
    t11 = WT('c1e', '十一天后')
    cue('hiding', ch1 + 0.9, t11 - G, (ch1 + 0.9, 0.0), fi=0.6, fo=0.10, db=-2.0)
    cue('hiding', t11 - 0.02, ch('ch2') + 0.3, (t11, 71.54), fi=0.01, fo=1.0, db=0.0, hit=True)
    # ======== 第二章 铁路这门生意：Ascending the Vale（96 拍，开阔、行进）；“九百六十万车”落在曲中 48.04 s 的进入
    #   芒格那段换成 Blue Feather 的钢琴（回望、自嘲）
    t960 = WT('c2c', '九百六十万')
    cue2('vale', ch('ch2') - 0.02, S('c2e') - 0.1, (ch('ch2'), 16.45), (t960, 48.04), fi=0.01, fo=1.0, db=1.0, hit=True)
    HITS.append(round(t960, 3))
    cue('feather', S('c2e') - 0.3, ch('ch3') + 0.3, (S('c2e') - 0.3, 129.0), fi=0.6, fo=0.8, db=2.0)
    # ======== 第三章 护城河：Prelude and Action（129 拍，动作感）；章卡落在曲中 11.04 s 的进入；
    #   “第二关”换到曲子后段，“两关都过了”落在 75.86 s 的高点；“可问题来了”前收掉，设问在静默里
    t2 = WT('c3d', '第二关'); tok = WT('c3e', '两关都过了'); tq = WT('c3e', '可问题来了')
    cue('prelude', ch('ch3') - 0.02, t2 - 0.3, (ch('ch3'), 11.04), fi=0.01, fo=0.25, db=1.0, hit=True)
    cue('prelude', t2 - 0.05, tq - 0.25, (tok, 75.86), fi=0.15, fo=0.35, db=1.5)
    HITS.append(round(tok, 3))
    # ======== 第四章 吃资本的生意：Interloper（136 拍，低音脉冲，压迫感）；章卡落在 35.43 s 的重音；
    #   “哎哟”前静默 → 54.21 s 的重音（这次真的落下来）；回顾日本商社换成 Blue Feather 钢琴
    tou = WT('c4b', '哎哟')
    cue2('interloper', ch('ch4') - 0.02, tou - G, (ch('ch4'), 35.43), (tou, 54.21), fi=0.01, fo=0.10, db=-1.0, hit=True)
    cue('interloper', tou - 0.02, S('c4f') - 0.1, (tou, 54.21), fi=0.01, fo=1.0, db=0.0, hit=True)
    cue('feather', S('c4f') - 0.4, ch('ch5') + 0.2, (S('c4f') - 0.4, 37.59), fi=0.05, fo=0.6, db=1.0)
    # ======== 第五章 账怎么算：Dreams Become Real（96 拍，明亮）章卡落在 44.51 s 的进入；
    #   “六百二十亿”前静默 → Achilles 27.26 s 的齐奏（全片最高点）；原声铺底；
    #   “买在恐慌里”落在 Achilles 46.21 s 的终段，曲子在引语处自然收尾，引语留白
    #   c5c 起换到 Achilles 的引子（一路收紧），“六百二十亿”前静默 → 齐奏
    t620 = WT('c5d', '六百二十亿')
    cue('dreams', ch('ch5') - 0.02, S('c5c') - 0.1, (ch('ch5'), 44.51), fi=0.01, fo=0.8, db=4.0, hit=True)
    cue('achilles', S('c5c') - 0.6, t620 - G, (t620, 27.26), fi=0.8, fo=0.10, db=1.0)
    cue('achilles', t620 - 0.02, sot['railroad'][0] - 0.2, (t620, 27.26), fi=0.01, fo=0.8, db=2.5, hit=True)
    bed('railroad', 16.72)
    cue('achilles', S('c5f') - 0.05, ch('ch6') - 0.5, (S('c5f'), 46.21), fi=0.02, fo=1.5, db=1.0, hit=True)
    # ======== 第六章 掉队与变局：Constance（83 拍，克制）；“变局也来了”前静默 → 开场的 Industrial Cinematic
    #   回来（主题再现，换成曲子后段乐队全开的织体，167.78 s 的重音）
    tv = WT('c6d', '变局')
    cue('constance', ch('ch6') - 0.02, tv - G, (ch('ch6'), 0.06), fi=0.01, fo=0.12, db=-1.0, hit=True)
    cue('industrial', tv - 0.02, ch('ch7') - 0.4, (tv, 167.78), fi=0.01, fo=0.8, db=-1.0, hit=True)
    # ======== 第七章 带走什么：Mining by Moonlight（161 拍，明亮有推动力）；“一百年后”前静默 → 54.04 s 的重新进入
    t100 = WT('c7e', '一百年后')
    #   “三件事”做成三级台阶：第一（−7 dB）→ 第二（−4 dB）→ 第三（−1 dB），同一锚点，交界 0.3 秒交叉
    k2, k3 = S('c7c'), S('c7d')
    cue('mining', ch('ch7') - 0.02, k2 + 0.15, (t100, 54.04), fi=0.02, fo=0.3, db=-7.0)
    cue('mining', k2 - 0.15, k3 + 0.15, (t100, 54.04), fi=0.3, fo=0.3, db=-4.0)
    cue('mining', k3 - 0.15, t100 - G, (t100, 54.04), fi=0.3, fo=0.10, db=-1.0)
    HITS.extend([round(ch('ch7'), 3), round(k2, 3), round(k3, 3)])
    cue('mining', t100 - 0.02, S('p1') - 0.2, (t100, 54.04), fi=0.01, fo=0.6, db=-1.0, hit=True)
    # ======== 下期预告：回到第一章的 Hiding Your Reality 后段（同一条紧张的脉冲，预告“另一笔交易”）；
    #   logo 落在 181.60 s 的重音，之后曲子自然收尾
    logo = TL['logo']
    cue('hiding', S('p1') - 0.3, TL['total'] + 0.5, (logo, 181.60), fi=0.5, fo=3.0, db=0.0)
    HITS.append(round(logo, 3))


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
