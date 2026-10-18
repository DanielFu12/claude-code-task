"""配乐剪辑方案 + 卡点（写 work/music_plan.json，供 timeline.py 和 audio_mix.py 使用）。

三段 Lyria 原创配乐（同一调性/配器，提示词见 music_gen.py）：
  A = A_2：开场悬念 → 标题重拍 → 怀旧钢琴（第一章）→ 推进的弦乐固定音型（第二章）
  C = A_1 的后段：第三章「复利账本」从安静处起步，层层叠加到高潮
  B = B_0：第四章泡沫的阴影 → 坚定 → 第五章反思钢琴 → 史诗升腾 → 片尾大和弦

旁白有自己的呼吸节奏，配乐去迁就旁白：当旁白比音乐的下一个段落点长时，
在该段落中间“按整小节重复”一段平稳的音乐（拍点对齐拼接），让段落点（重拍）
正好落在章节切换 / 关键句上；略多出的时间作为旁白前的留白。
所有时间：音乐时间 m（原曲内秒数）→ 成片时间 = 片段起点 + m + 之前插入的重复长度。
"""
import json, os, sys, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as TLM
from script import LINES

# 每段配乐的关键点（原曲内秒数，librosa onset 检测 + 包络图人工核对）
A_TITLE, A_CH2, A_CH3 = 26.11, 71.70, 128.81
C_IN, C_S27, C_S28 = 126.6, 142.91, 154.2
B_S39, B_CH5, B_S46, B_END, B_LOGO = 27.23, 51.3, 72.37, 91.9, 95.79
# 片尾：先读下期预告（预告文字随后化作金色粒子汇聚成 logo），logo 落在 B 的最后一个重拍上
TEASE_LEAD, DISSOLVE = 0.45, 1.5
# 可重复的平稳区段（原曲内秒数）：为某个卡点补时间时，从这里取整小节重复
LOOP_ZONES = {
    ('A', 'ch2'): 40.0,      # 第一章怀旧钢琴的中段
    ('A', 'ch3'): 92.0,      # 第二章固定音型的中段
    ('C', 's27'): 131.5,     # 第三章安静起步
    ('C', 's28'): 145.0,     # 第三章叠加中
    ('B', 's39'): 8.0,       # 第四章低沉张力
    ('B', 'ch5'): 33.0,      # 坚定段
    ('B', 's46'): 56.0,      # 反思钢琴
    ('B', 'end'): 77.0,      # 升腾段
}


def beats_of(work, f):
    cache = os.path.join(work, 'music', f + '.beats.json')
    if os.path.exists(cache): return np.array(json.load(open(cache)))
    import librosa
    y, sr = librosa.load(os.path.join(work, 'music', f), sr=22050)
    _, b = librosa.beat.beat_track(y=y, sr=sr, hop_length=256)
    bt = librosa.frames_to_time(b, sr=sr, hop_length=256)
    json.dump([float(x) for x in bt], open(cache, 'w'))
    return bt


class Piece:
    def __init__(self, name, file, beats):
        self.name, self.file, self.beats = name, file, beats
        self.loops = []                     # [(start, end)] 原曲内被重复的区段
        self.cuts = []                      # [(start, end)] 原曲内被剪掉的区段

    def shift(self, m):
        return sum(e - s for s, e in self.loops if s <= m) - sum(e - s for s, e in self.cuts if e <= m)

    def adjust(self, zone, delta):
        """delta>0：在 zone 处重复整 4 拍倍数的区段补时间；delta<0：剪掉整 4 拍倍数的区段。
        取最接近 delta 的整小节数（误差 ≤ 半小节，多出的部分由旁白留白吸收）。"""
        b = self.beats
        i = int(np.argmin(np.abs(b - zone)))
        period = float(np.median(np.diff(b)))
        bars = round(abs(delta) / (4 * period))
        if delta > 0: bars = max(bars, 1) if delta > 2 * period else bars
        if bars == 0: return 0.0
        j = min(i + 4 * bars, len(b) - 1)
        seg = (float(b[i]), float(b[j]))
        (self.loops if delta > 0 else self.cuts).append(seg)
        return (seg[1] - seg[0]) * (1 if delta > 0 else -1)


def natural(work, durs, anchors, key):
    tl = TLM.build(work, durs, anchors, quiet=True)
    if key in tl['chapters']: return tl['chapters'][key][0]
    return {s['id']: s['start'] for s in tl['segs']}[key]


def plan(work):
    durs = {l[0]: TLM.sf.info(os.path.join(work, 'vo', l[0] + '.wav')).duration for l in LINES + [('tease',)]}
    A = Piece('A', 'A_2.mp3', beats_of(work, 'A_2.mp3'))
    C = Piece('C', 'A_1.mp3', beats_of(work, 'A_1.mp3'))
    B = Piece('B', 'B_0.mp3', beats_of(work, 'B_0.mp3'))
    anchors = {}
    log = []
    title = natural(work, durs, anchors, 'title')
    A_at = title - A_TITLE                                  # 标题重拍对齐
    anchors['title'] = title

    def fit(piece, at, key, m, anchor=True):
        nat = natural(work, durs, anchors, key)
        film = at + m + piece.shift(m)
        if abs(nat - film) > 0.5:
            got = piece.adjust(LOOP_ZONES[(piece.name, key)], nat - film)
            log.append(f'{piece.name}: {key} 需要 {nat - film:+.2f}s，{"重复" if got > 0 else "剪掉"} {abs(got):.2f}s')
            film = at + m + piece.shift(m)
        if anchor and film > nat - 1.2: anchors[key] = max(film, nat)   # 音乐点不早于旁白 1.2s 以上时才卡点
        log.append(f'  {key}: 旁白 {nat:.2f} / 音乐点 {film:.2f}')
        return film

    fit(A, A_at, 'ch2', A_CH2)
    C_AT = fit(A, A_at, 'ch3', A_CH3); anchors['ch3'] = C_AT                         # A 的段落重拍 → 切到 C
    C_at = C_AT - C_IN
    fit(C, C_at, 's27', C_S27, anchor=False)                 # 第三章内部不强制卡点，只让叠加大致对位
    fit(C, C_at, 's28', C_S28, anchor=False)
    B_AT = natural(work, durs, anchors, 'ch4') - 0.4          # B 的低沉铺底比章节卡早 0.4s 进入
    fit(B, B_AT, 's39', B_S39)
    fit(B, B_AT, 'ch5', B_CH5)
    fit(B, B_AT, 's46', B_S46 - 2.0)                          # 升腾前 2s 开始核心句
    delay = TEASE_LEAD + durs['tease'] + DISSOLVE             # 片尾卡开始 → logo 重拍
    end = fit(B, B_AT, 'end', B_LOGO - delay)
    logo = B_AT + B_LOGO + B.shift(B_LOGO)
    E = anchors.get('end', end)
    anchors['tease'] = max(E + 0.25, logo - DISSOLVE - durs['tease'])
    anchors['logo'] = logo
    cend = C_at + 184.0 + C.shift(184.0)
    pieces = [
        dict(name='A', file=A.file, src_in=0.0, at=A_at, until=C_AT + 1.2, fade_in=0.0, fade_out=2.6, loops=A.loops, cuts=A.cuts),
        dict(name='C', file=C.file, src_in=C_IN - 1.2, at=C_AT - 1.2, until=B_AT + 1.5, fade_in=1.6, fade_out=3.0,
             loops=C.loops, cuts=C.cuts),
        dict(name='B', file=B.file, src_in=0.0, at=B_AT, until=None, fade_in=0.8, fade_out=4.0, loops=B.loops, cuts=B.cuts),
    ]
    fA = lambda m: A_at + m + A.shift(m)
    fC = lambda m: C_at + m + C.shift(m)
    fB = lambda m: B_AT + m + B.shift(m)
    # 原曲里的上扬/镲片过渡（Gemini 听审 + 频谱核对），这些窗口内配乐低通到 2.5kHz
    lp_windows = [(fA(24.6), fA(26.4)), (fA(69.8), fA(71.6)), (fA(126.5), C_AT + 0.6),
                  (fC(128.0), fC(129.2)), (fB(84.5), fB(93.0))]
    hits = {'title': title, 'ch2': anchors['ch2'], 'ch3': C_AT, 'logo': logo}
    return dict(pieces=pieces, anchors=anchors, hits=hits, lp_windows=lp_windows, log=log,
                A_OFF=A_at, C_OFF=C_at, B_AT=B_AT, C_END=cend, dissolve=DISSOLVE)


if __name__ == '__main__':
    work = sys.argv[1]
    p = plan(work)
    json.dump(p, open(os.path.join(work, 'music_plan.json'), 'w'), indent=1)
    for l in p['log']: print(l)
    for k, v in p['anchors'].items(): print(k, round(v, 2))
