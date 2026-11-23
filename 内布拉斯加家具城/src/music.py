"""第八期原创配乐（沿用第四期起的程序作曲框架）：按时间线（work/timeline.json）直接写 MIDI，再用 FluidSynth + FluidR3 GM 音色库渲染。

前几期的配乐素材（Lyria 生成）没有入库，本环境也无法调用该服务；本期改为程序作曲：
  · 一套统一的音乐语言：80 BPM、4/4（每小节 3 秒），D 小调为主，第五章转 D 大调；
  · 同一个四音主题（D–A–F–E，小调；大调段为 D–A–F#–E）贯穿全片，按章节换配器；
  · 段落起点、高潮点直接取旁白时间线（章节起点、某句某词开始发声），不需要事后剪辑对位；
  · 三处“点燃”：片名、c4c“是我发起的”、片尾 logo；c4c 之后留白约两小节。
  · v3：加入打击乐（大鼓、太鼓、通鼓、军鼓滚奏、镲）、弦乐颤音与十六分固定音型、铜管齐奏主题；
    重拍前噪声上扬、重拍上低频轰鸣；整体卷积混响。护城河四段逐段加码到全编制，第五段突转小调；
    巴菲特原声下只留低音铺底。
python3 src/music.py WORK      → WORK/music/score.mid, score.wav, beats.json
"""
import sys, os, json, subprocess, math
import numpy as np
import pretty_midi as pm

WORK = sys.argv[1] if len(sys.argv) > 1 else 'work'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES

TL = json.load(open(os.path.join(WORK, 'timeline.json')))
SEG = {s['id']: s for s in TL['segs']}
CH = TL['chapters']
SAY = {l[0]: (l[3] or l[2]) for l in LINES}
SF2 = '/usr/share/sounds/sf2/FluidR3_GM.sf2'
BAR = 3.0; BEAT = BAR / 4


def S(i): return SEG[i]['start']
def E(i): return SEG[i]['start'] + SEG[i]['dur']


def WT(i, sub):
    s = SAY[i]; k = s.find(sub)
    if k < 0: raise KeyError(sub)
    for idx, tt in SEG[i]['ct']:
        if idx >= k: return S(i) + tt
    return S(i) + SEG[i]['dur'] * k / len(s)


# ------------------------------------------------------------------ 和声
NOTE = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8,
        'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
QUAL = {'': (0, 4, 7), 'm': (0, 3, 7), 'sus4': (0, 5, 7), 'sus2': (0, 2, 7), 'add9': (0, 4, 7, 14), 'm7': (0, 3, 7, 10),
        '7': (0, 4, 7, 10), 'maj7': (0, 4, 7, 11), 'madd9': (0, 3, 7, 14)}


def chord(name):
    """'Dm' → (根音 pc, 音程)；'F/C' 低音另取"""
    name, _, bass = name.partition('/')
    r = name[:2] if len(name) > 1 and name[1] in '#b' else name[:1]
    return NOTE[r], QUAL[name[len(r):]], (NOTE[bass] if bass else NOTE[r])


def voicing(name, lo=55, n=4):
    """弦乐/铺底的密集排列：从 lo 往上取 n 个和弦音"""
    r, iv, _ = chord(name)
    pcs = sorted({(r + x) % 12 for x in iv})
    out = []; p = lo
    while len(out) < n:
        if p % 12 in pcs: out.append(p)
        p += 1
    return out


# ------------------------------------------------------------------ 乐器
INS = {'piano': 0, 'harp': 46, 'strings': 48, 'strings2': 49, 'cello': 42, 'bass': 43, 'pizz': 45, 'timp': 47,
       'horn': 60, 'choir': 52, 'pad': 89, 'celesta': 8, 'trem': 44, 'spic': 48, 'brass': 61, 'trumpet': 56,
       'trombone': 57, 'taiko': 116}
DRUM = {'kick': 35, 'kick2': 36, 'snare': 38, 'ltom': 41, 'ftom': 43, 'mtom': 45, 'crash': 49, 'crash2': 57, 'ride': 51,
        'chinese': 52, 'splash': 55}
MIDI = pm.PrettyMIDI(initial_tempo=80)
TR = {}


def tr(name):
    if name not in TR:
        TR[name] = pm.Instrument(program=INS.get(name, 0), name=name, is_drum=(name == 'drums'))
        MIDI.instruments.append(TR[name])
    return TR[name]


def note(ins, p, t0, t1, v):
    v = int(max(1, min(127, v)))
    if t1 - t0 < 0.03 or v < 2: return
    tr(ins).notes.append(pm.Note(velocity=v, pitch=int(p), start=float(t0), end=float(t1)))


def drum(k, t, v, d=0.3):
    note('drums', DRUM[k], t, t + d, v)


def cc(ins, t, val, num=11):
    tr(ins).control_changes.append(pm.ControlChange(number=num, value=int(max(0, min(127, val))), time=float(t)))


MOTIF_MIN = [0, 7, 3, 2]      # D–A–F–E（相对主音）
MOTIF_MAJ = [0, 7, 4, 2]      # D–A–F#–E


def motif(ins, tonic, t0, v, octave=72, major=False, dur=BEAT, last=2.0):
    m = MOTIF_MAJ if major else MOTIF_MIN
    for k, iv in enumerate(m):
        d = dur * (last if k == 3 else 1.0)
        note(ins, octave + (tonic + iv) % 12 if iv else octave + tonic % 12, t0 + k * dur, t0 + k * dur + d * 1.05, v * (1.0 if k else 1.08))


# ------------------------------------------------------------------ 段落写法
def section(t0, t1, prog, tex, v0=60, v1=60, tonic=2, major=False, motif_every=2, motif_ins='piano', motif_oct=72):
    """t0–t1 之间按小节铺和弦进行 prog，tex 为配器集合；力度从 v0 线性到 v1。
    v3：小节取自全片统一的小节网格 GRID（起止吸附到最近的小节线），段落之间拍子连续，不再各自从任意时刻重新起拍"""
    a, b_ = snap(t0), snap(t1)
    bars = [(g0, g1) for g0, g1 in zip(GRID, GRID[1:]) if a - 1e-6 <= g0 < b_ - 1e-6]
    nb = len(bars)
    for b, (bt, be) in enumerate(bars):
        BL = be - bt; B = BL / 4
        f = b / max(nb - 1, 1); v = v0 + (v1 - v0) * f
        name = prog[b % len(prog)]
        r, iv, bass = chord(name)
        if 'pad' in tex:
            for p in voicing(name, 55, 4): note('strings', p, bt, be + 0.25, v * 0.75)
        if 'pad2' in tex:
            for p in voicing(name, 50, 4): note('strings2', p, bt, be + 0.3, v * 0.6)
        if 'synth' in tex:
            for p in voicing(name, 57, 3): note('pad', p, bt, be + 0.4, v * 0.45)
        if 'low' in tex:
            note('bass', 36 + bass if 36 + bass <= 47 else 24 + bass, bt, be + 0.2, v * 0.85)
            note('cello', 48 + bass if 48 + bass <= 59 else 36 + bass, bt, be + 0.2, v * 0.65)
        if 'arp' in tex:                       # 钢琴八分分解和弦
            ps = voicing(name, 60, 4) + voicing(name, 72, 2)
            seq = [ps[0], ps[1], ps[2], ps[3], ps[4], ps[3], ps[2], ps[1]]
            for k, p in enumerate(seq):
                tt = bt + k * B / 2
                if tt < be: note('piano', p, tt, tt + B * 0.9, v * (0.62 if k else 0.72))
        if 'harp' in tex:
            ps = voicing(name, 55, 6)
            for k, p in enumerate(ps):
                tt = bt + k * B / 3
                if tt < be: note('harp', p, tt, tt + BL * 0.6, v * 0.5)
        if 'pizz' in tex:
            ps = voicing(name, 50, 3)
            for k in range(4):
                tt = bt + k * B
                if tt < be: note('pizz', ps[k % 3] + (12 if k == 2 else 0), tt, tt + 0.25, v * 0.7)
        if 'eighths' in tex:                   # 弦乐八分音符低音持续（推进感）
            p = 48 + bass if 48 + bass <= 57 else 36 + bass
            for k in range(8):
                tt = bt + k * B / 2
                if tt < be: note('cello', p, tt, tt + B / 2 * 0.8, v * (0.55 if k % 2 else 0.68))
        if 'horn' in tex:
            for p in voicing(name, 53, 3): note('horn', p, bt, be + 0.2, v * 0.55)
        if 'choir' in tex:
            for p in voicing(name, 60, 3): note('choir', p, bt, be + 0.5, v * 0.4)
        if 'heart' in tex:                     # 定音鼓心跳（第 1、2 拍弱）
            note('timp', 26 + (r + 12) % 12 if (r % 12) < 7 else 26 + r % 12 - 12, bt, bt + 0.9, v * 0.55)
            note('timp', 26 + (r + 12) % 12 if (r % 12) < 7 else 26 + r % 12 - 12, bt + B * 0.55, bt + B * 1.4, v * 0.35)
        if 'piano_chord' in tex:
            for p in voicing(name, 57, 4): note('piano', p, bt, bt + BL * 0.95, v * 0.55)
            note('piano', 36 + bass, bt, bt + BL, v * 0.5)
        if 'trem' in tex:                      # 弦乐颤音：紧张、期待
            for p in voicing(name, 50, 4): note('trem', p, bt, be + 0.15, v * 0.62)
        if 'ostinato' in tex:                  # 弦乐十六分音符固定音型（推进、唤醒）
            ps = voicing(name, 62, 3)
            pat = [0, 1, 2, 1, 0, 1, 2, 1, 0, 2, 1, 2, 0, 1, 2, 1]
            for k, j in enumerate(pat):
                tt = bt + k * B / 4
                if tt < be: note('spic', ps[j] + (12 if k in (8, 12) and 'high' in tex else 0), tt, tt + B / 4 * 0.7,
                                 v * (0.62 if k % 4 == 0 else 0.46))
        if 'perc' in tex or 'perc2' in tex:    # 打击乐：大鼓 + 落地通鼓切分（perc2 更密，带太鼓）
            for k in range(8):
                tt = bt + k * B / 2
                if tt >= be: break
                if k in (0, 4): drum('kick', tt, v * 0.95, 0.5)
                if k in (3, 6) : drum('ftom', tt, v * 0.62)
                if 'perc2' in tex:
                    if k in (2, 7): drum('ltom', tt, v * 0.5)
                    if k == 0: note('taiko', 36 + bass % 12 if bass % 12 < 8 else 24 + bass % 12, tt, tt + 1.0, v * 0.8)
                    drum('ride', tt, v * (0.32 if k % 2 else 0.4), 0.2)
        if 'brass' in tex:
            for p in voicing(name, 50, 3): note('brass', p, bt, be + 0.1, v * 0.62)
            note('trombone', 36 + bass if 36 + bass <= 46 else 24 + bass, bt, be + 0.1, v * 0.55)
        if 'brassmotif' in tex and b % 2 == 0 and be - bt > BL * 0.9:     # 主题由小号 + 圆号齐奏（高潮段）
            motif('trumpet', tonic, bt, v * 0.85, octave=62, major=major, dur=B, last=2.0)
            motif('horn', tonic, bt, v * 0.8, octave=50, major=major, dur=B, last=2.0)
        if motif_every and b % motif_every == 0 and be - bt > BL * 0.9 and 'nomotif' not in tex:
            motif(motif_ins, tonic, bt, v * 0.95, octave=motif_oct, major=major, dur=B)


GRID = []
SOFT = []


def make_grid(anchors, T):
    """全片小节网格：80 BPM（每小节 3 秒）匀速；每个卡点（重拍）都正好落在小节线上——
    卡点前的最后一小节吸收余数（1.5–4.5 秒，被滚奏与上扬盖住），其余小节保持原速"""
    an = []
    for x in sorted(anchors):
        if 0 < x < T and (not an or x - an[-1] > 2.0): an.append(x)
    g = []; x = an[0]
    while x > 0.05: g.append(x); x -= BAR
    g.append(0.0)
    for a, b in zip(an, an[1:]):
        x = a
        while x + BAR <= b - BAR * 0.5 + 1e-6: g.append(x); x += BAR
        g.append(x)
    x = an[-1]
    while x < T + BAR: g.append(x); x += BAR
    GRID[:] = sorted(set(round(v, 4) for v in g))


def snap(t):
    return min(GRID, key=lambda g: abs(g - t))


def nxtbar(t, k=1):
    i = min(range(len(GRID)), key=lambda j: abs(GRID[j] - t))
    return GRID[min(i + k, len(GRID) - 1)]


def accent(t, name, v=80, ring=4.0):
    """温和的点题：定音鼓 + 弦乐/合唱长音 + 轻镲（不带大鼓与低频轰鸣）"""
    r, iv, bass = chord(name)
    tp = 26 + r % 12 if r % 12 < 7 else 14 + r % 12
    for k in range(8): note('timp', tp, t - BEAT * 0.8 + k * BEAT / 10, t - BEAT * 0.8 + k * BEAT / 10 + 0.1, 24 + k * 5)
    note('timp', tp, t, t + 2.0, v * 0.9)
    drum('crash2', t, v * 0.55, 3.0)
    for p in voicing(name, 50, 5): note('strings', p, t, t + ring, v * 0.75)
    for p in voicing(name, 62, 3): note('choir', p, t, t + ring, v * 0.45)
    note('bass', 24 + bass if bass < 12 else 24, t, t + ring, v * 0.7)


RISERS, BOOMS = [], []


def riser(t, dur=3.0, v=80):
    """重拍前的上扬：军鼓滚奏渐强 + 弦乐颤音向上滑（另在音频后期叠加噪声上扬，见 post()）"""
    n = int(dur / (BEAT / 6))
    for k in range(n):
        tt = t - dur + k * BEAT / 6
        drum('snare', tt, 18 + (v - 18) * (k / n) ** 1.6, 0.08)
    RISERS.append((t, dur))


def hit(t, name, v=100, ring=6.0, big=True):
    """高潮重拍：圆号 + 全弦乐 + 定音鼓滚奏收束（滚奏在重拍前 1 拍开始）；加大鼓、镲、太鼓、铜管与低频轰鸣"""
    r, iv, bass = chord(name)
    drum('kick2', t, v, 1.0); drum('kick', t, v, 1.0); drum('crash', t, v * 0.9, 3.0)
    if big: drum('crash2', t + 0.01, v * 0.7, 3.0)
    note('taiko', 36 + bass % 12 if bass % 12 < 8 else 24 + bass % 12, t, t + 2.0, v)
    for p in voicing(name, 46, 4): note('brass', p, t, t + ring * 0.7, v * 0.75)
    note('trombone', 26 + bass % 12 if bass % 12 < 10 else 14 + bass % 12, t, t + ring * 0.7, v * 0.7)
    BOOMS.append((t, v / 127))
    tp = 26 + r % 12 if r % 12 < 7 else 14 + r % 12
    for k in range(10):                     # 定音鼓滚奏（渐强）
        tt = t - BEAT + k * BEAT / 10
        note('timp', tp, tt, tt + 0.12, 30 + k * 6)
    note('timp', tp, t, t + 2.5, v)
    for p in voicing(name, 50, 5): note('strings', p, t, t + ring, v * 0.85)
    for p in voicing(name, 53, 3): note('horn', p, t, t + ring * 0.8, v * 0.8)
    note('bass', 24 + bass if bass < 12 else 24, t, t + ring, v * 0.8)
    if big:
        for p in voicing(name, 62, 3): note('choir', p, t, t + ring, v * 0.45)
        for p in voicing(name, 48, 4) + voicing(name, 72, 2): note('piano', p, t, t + ring * 0.7, v * 0.6)


def build():
    T = TL['total']; title = CH['title'][0]
    c = {k: CH[k][0] for k in ('ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6', 'ch7', 'end')}
    # 第八期卡点：片名、各章章节号亮起（章节卡开始后 0.5s）、c1i“现金只有五十美元”、c2e“一个字没改”、c3c“百分之十六点五”、
    #             c4b“辞职走了”、c5d“一百八十万平方英尺”、c7e“三十三亿”、logo。本期没有原声段落。
    hc = {k: c[k] + 0.5 for k in ('ch2', 'ch3', 'ch4', 'ch5', 'ch6', 'ch7')}
    t_sign = WT('h4', '就签了'); t_fifty = WT('c1i', '五十美元'); t_word = WT('c2e', '一个字没改')
    t_cost = WT('c3c', '百分之十六点五'); t_quit = WT('c4b', '辞职走了'); t_tx = WT('c5d', '一百八十万')
    t_33 = WT('c7e', '三十三亿'); logo = TL['logo']
    t_judge = WT('c1h', '一千四百美元'); t_motto = WT('c1k', '卖得便宜'); t_enough = WT('c2g', '就够了')
    t_river = WT('c3g', '河底'); t_99 = WT('c4f', '九十九岁'); t_104 = WT('c4h', '一百零四岁'); t_rec = WT('c5e', '销售纪录')
    make_grid([title, t_fifty, t_word, t_cost, t_quit, t_tx, t_33, logo] + list(hc.values()), T)
    tk = lambda cid: CH['tk_' + cid][0]

    def bridge(prev, cid, prog, to, v=92):
        """要点卡 → 章节号：弦乐颤音 + 合唱上扬，军鼓滚奏推到章节号的重拍"""
        a = tk(prev) - 0.2; h = hc[cid]
        section(a, h, prog, {'pad', 'trem', 'low', 'choir', 'nomotif'}, 46, 68)
        riser(h, min(2.8, h - snap(a) - 0.2), 84)
        hit(h, to, v, ring=3.5, big=False)
        return nxtbar(h)

    # ---- 开场：1972 年的奥马哈（温暖的钢琴琶音）→ 1983 年生日那天（八分音符推进）→ 一个字没改就签了（点一下）
    #       → 引语卡（弦乐铺底）→ 两个问题（固定音型起势）→ 撞进片名
    section(0.6, S('h3') - 0.2, ['F', 'C/E', 'Dm', 'Bb'], {'arp', 'pad2', 'low', 'piano_chord'}, 38, 48, tonic=5, major=True, motif_every=4)
    section(S('h3') - 0.2, t_sign, ['F', 'C', 'Dm', 'Bb'], {'arp', 'pad', 'low', 'eighths'}, 48, 60, tonic=5, major=True, motif_every=0)
    accent(t_sign, 'F', 84)
    section(nxtbar(t_sign), S('h6') - 0.2, ['Bb', 'F/A', 'Gm', 'C'], {'pad', 'low', 'harp'}, 46, 52, tonic=5, major=True, motif_every=4)
    section(S('h6') - 0.2, title, ['Bb', 'Gm', 'C', 'Bb', 'Gm', 'C'], {'trem', 'low', 'ostinato', 'perc', 'nomotif'}, 58, 88)
    riser(title, 3.0, 92)
    hit(title, 'F', 110)
    # ---- 第一章：离开俄国（小调拨弦）→ 卖得便宜、被断货、被告（心跳推进）→ 法官买地毯（转大调点一下）
    #       → 现金只有五十美元（重拍，沉下去）→ 路易回来（圆号主题，温暖）→ 卖得便宜，说真话（合唱）
    section(nxtbar(title), S('c1d') - 0.3, ['Dm', 'Bb', 'F', 'C', 'Gm', 'Bb', 'Dm', 'A'], {'piano_chord', 'pad2', 'low', 'pizz'}, 40, 50,
            motif_every=4, motif_oct=74)
    section(S('c1d') - 0.3, t_judge, ['Dm', 'Bb', 'Gm', 'A'], {'pizz', 'eighths', 'pad2', 'low', 'heart'}, 46, 64, motif_every=4, motif_oct=62)
    accent(t_judge, 'F', 82)
    section(nxtbar(t_judge), t_fifty, ['Dm', 'Bb', 'Gm', 'A'], {'pad2', 'low', 'trem'}, 44, 54, motif_every=0)
    riser(t_fifty, 1.6, 74)
    hit(t_fifty, 'Dm', 90, ring=3.0, big=False)
    section(nxtbar(t_fifty), t_motto, ['F', 'C/E', 'Dm', 'Bb', 'F/A', 'Gm', 'Bb', 'C'], {'pad', 'low', 'horn', 'arp'}, 48, 60, tonic=5, major=True,
            motif_every=4, motif_ins='horn', motif_oct=65)
    accent(t_motto, 'F', 88, ring=4.0)
    section(nxtbar(t_motto), tk('ch1'), ['Bb', 'F/A', 'Gm', 'C'], {'pad', 'low', 'choir'}, 48, 54, tonic=5, major=True, motif_every=0)
    s2 = bridge('ch1', 'ch2', ['Bb', 'C'], 'F')
    # ---- 第二章：一亿多美元（明亮琶音）→ 提议书（拨弦）→ 一个字没改（重拍）→ 她的一句话就够了（合唱）→ 灰熊（固定音型）
    section(s2, S('c2d') - 0.3, ['F', 'C/E', 'Dm', 'Bb'], {'arp', 'pad', 'low', 'harp'}, 46, 56, tonic=5, major=True, motif_every=4)
    section(S('c2d') - 0.3, t_word, ['F', 'Bb', 'Dm', 'C'], {'pad2', 'pizz', 'eighths', 'low'}, 50, 62, tonic=5, major=True, motif_every=4)
    riser(t_word, 1.8, 80)
    hit(t_word, 'F', 98, ring=3.0)
    section(nxtbar(t_word), t_enough, ['Bb', 'F/A', 'Gm', 'C'], {'pad', 'low', 'harp', 'choir'}, 48, 56, tonic=5, major=True, motif_every=4)
    accent(t_enough, 'F', 86)
    section(nxtbar(t_enough), tk('ch2'), ['F', 'C', 'Dm', 'Bb', 'F', 'C', 'Bb', 'C'], {'pad', 'low', 'ostinato', 'perc', 'eighths'}, 52, 70,
            tonic=5, major=True, motif_every=0)
    s3 = bridge('ch2', 'ch3', ['Gm', 'C'], 'F')
    # ---- 第三章：Levitz 对比（数字一级级推进）→ 16.5%（大重拍）→ 飞轮（固定音型）→ 河底（点一下）→ Dillard’s → 都比别人便宜（铜管）
    section(s3, t_cost, ['F', 'C', 'Dm', 'Bb', 'F', 'C', 'Bb', 'C'], {'pad', 'low', 'ostinato', 'perc', 'eighths'}, 48, 70, tonic=5, major=True, motif_every=0)
    riser(t_cost, 2.2, 88)
    hit(t_cost, 'F', 104, ring=3.5)
    section(nxtbar(t_cost), t_river, ['F', 'C/E', 'Dm', 'Bb'], {'pad', 'arp', 'low', 'eighths'}, 50, 60, tonic=5, major=True, motif_every=4)
    accent(t_river, 'F', 84)
    section(nxtbar(t_river), tk('ch3'), ['Bb', 'F/A', 'Gm', 'C'], {'pad', 'low', 'brass', 'brassmotif', 'nomotif'}, 52, 64, tonic=5, major=True)
    s4 = bridge('ch3', 'ch4', ['Bb', 'A'], 'Dm', 90)
    # ---- 第四章：闹翻（小调心跳）→ 辞职走了（重拍）→ 开到隔壁（俏皮拨弦）→ 九十九岁签竞业（转大调）→ 一百零四岁（安静的合唱）
    section(s4, t_quit, ['Dm', 'Bb', 'Gm', 'A'], {'pizz', 'pad2', 'low', 'heart'}, 44, 62, motif_every=4, motif_oct=62)
    riser(t_quit, 1.8, 80)
    hit(t_quit, 'Dm', 96, ring=3.0, big=False)
    section(nxtbar(t_quit), t_99, ['Dm', 'Bb', 'F', 'C'], {'pad2', 'low', 'pizz', 'eighths'}, 44, 56, motif_every=4, motif_oct=67)
    accent(t_99, 'F', 86)
    section(nxtbar(t_99), t_104, ['F', 'C/E', 'Dm', 'Bb'], {'pad', 'low', 'harp'}, 46, 50, tonic=5, major=True, motif_every=4)
    accent(t_104, 'Bb', 72, ring=5.0)
    section(nxtbar(t_104), tk('ch4'), ['Bb', 'F/A', 'Gm', 'C'], {'pad', 'low', 'choir'}, 42, 50, tonic=5, major=True, motif_every=0)
    s5 = bridge('ch4', 'ch5', ['Bb', 'C'], 'F')
    # ---- 第五章：越开越大（明亮琶音 → 固定音型）→ 180 万平方英尺（重拍）→ 疫情下的纪录（点一下）→ 股东周（合唱）
    section(s5, t_tx, ['F', 'C/E', 'Dm', 'Bb', 'F', 'C', 'Bb', 'C'], {'arp', 'harp', 'pad', 'low', 'eighths', 'ostinato'}, 48, 70, tonic=5, major=True, motif_every=4)
    riser(t_tx, 2.0, 86)
    hit(t_tx, 'F', 100, ring=3.5)
    section(nxtbar(t_tx), t_rec, ['F', 'C', 'Dm', 'Bb'], {'pad', 'low', 'arp'}, 52, 60, tonic=5, major=True, motif_every=4)
    accent(t_rec, 'F', 86)
    section(nxtbar(t_rec), tk('ch5'), ['Bb', 'C', 'Dm', 'Bb', 'F/A', 'Gm', 'Csus4', 'C'], {'pad', 'arp', 'low', 'choir'}, 50, 64, tonic=5, major=True, motif_every=2)
    s6 = bridge('ch5', 'ch6', ['Bb', 'A'], 'Dm', 86)
    # ---- 第六章：三件事（小调心跳，逐条推进）→ 除了 NFM（铜管收束）
    section(s6, S('c6f') - 0.3, ['Dm', 'Bb', 'Gm', 'A', 'Dm', 'Bb', 'F', 'C'], {'pad2', 'low', 'heart', 'pizz'}, 42, 56, motif_every=4, motif_oct=62)
    section(S('c6f') - 0.3, tk('ch6'), ['F', 'C', 'Dm', 'Bb'], {'pad', 'low', 'horn', 'brass', 'brassmotif', 'nomotif'}, 50, 64, tonic=5, major=True)
    s7 = bridge('ch6', 'ch7', ['Bb', 'C'], 'F', 92)
    # ---- 第七章：一家牵出一家（合唱涨起）→ 三十三亿（重拍）→ 卖得便宜，说真话 → 落版字化作粒子 → logo
    section(s7, t_33, ['Bb', 'C', 'Dm', 'Bb', 'F/A', 'Gm', 'Csus4', 'C'], {'pad', 'arp', 'low', 'choir', 'harp'}, 46, 68,
            tonic=5, major=True, motif_every=2)
    riser(t_33, 2.0, 86)
    hit(t_33, 'F', 100, ring=3.5)
    section(nxtbar(t_33), S('c7g') - 0.2, ['F', 'Bb', 'F/A', 'C', 'F', 'Bb', 'Gm', 'C'], {'pad', 'choir', 'low', 'horn'}, 54, 52, tonic=5, major=True,
            motif_every=4, motif_ins='horn', motif_oct=65)
    section(S('c7g') - 0.2, logo, ['Bb', 'C', 'Dm', 'Bb', 'Gm', 'C'], {'pad', 'choir', 'low', 'horn', 'arp', 'nomotif'}, 56, 62, tonic=5, major=True)
    riser(logo, 3.0, 96)
    hit(logo, 'F', 110, ring=T - logo + 0.5)
    # 混响与声相
    for name, t in TR.items():
        if name == 'drums':
            t.control_changes += [pm.ControlChange(91, 50, 0.0), pm.ControlChange(7, 96, 0.0)]; continue
        pan = {'piano': 60, 'harp': 40, 'strings': 50, 'strings2': 78, 'cello': 70, 'bass': 64, 'pizz': 46, 'timp': 64, 'horn': 50,
               'choir': 64, 'pad': 64, 'celesta': 80, 'trem': 44, 'spic': 84, 'brass': 58, 'trumpet': 70, 'trombone': 54, 'taiko': 64}[name]
        t.control_changes += [pm.ControlChange(10, pan, 0.0), pm.ControlChange(91, 60 if name not in ('timp', 'taiko') else 40, 0.0),
                              pm.ControlChange(7, {'horn': 92, 'timp': 100, 'choir': 70, 'pad': 70, 'spic': 84, 'brass': 88,
                                                   'trumpet': 84, 'trombone': 88, 'taiko': 110}.get(name, 100), 0.0)]
    beats = sorted(g0 + k * (g1 - g0) / 4 for g0, g1 in zip(GRID, GRID[1:]) for k in range(4) if g0 < T)
    SOFT[:] = [t_fifty, t_word, t_cost, t_quit, t_tx, t_33, t_sign, t_judge, t_motto, t_enough, t_river, t_99, t_104, t_rec]   # 句中的点题：配乐只半闪避，不压字
    return beats, [title, t_fifty, t_word, t_cost, t_quit, t_tx, t_33, logo] + list(hc.values()), list(hc.values())


def post(wav):
    """后期：噪声上扬（重拍前）+ 低频轰鸣（重拍上）+ 立体声卷积混响（合成脉冲响应，2.6s）"""
    import soundfile as sf
    from scipy.signal import fftconvolve, butter, sosfilt
    y, sr = sf.read(wav, dtype='float32')
    if y.ndim == 1: y = np.stack([y, y], 1)
    rng = np.random.default_rng(7)
    hop = sr // 2
    rr = np.sqrt(np.mean(y[:len(y) // hop * hop].reshape(-1, hop, 2) ** 2, axis=(1, 2)))
    ref = float(np.median(rr[rr > 1e-5]))                 # 配乐的典型电平（0.5s RMS 的中位数）
    # 慢压缩：0.4s RMS 超过典型电平 +11 dB 的部分按 3:1 压下（重拍仍突出，但不至于把其余段落挤得太轻）
    h = int(0.4 * sr); e = np.sqrt(np.convolve((y ** 2).mean(1), np.ones(h) / h, 'same')) + 1e-9
    over = 20 * np.log10(e / ref) - 11
    gr = np.where(over > 0, -over * (1 - 1 / 3), 0)
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    gr = uniform_filter1d(minimum_filter1d(gr, int(0.3 * sr)), int(0.3 * sr))
    y *= (10 ** (gr / 20))[:, None].astype(np.float32)
    for t, dur in RISERS:
        n = int(dur * sr); a = int(t * sr) - n
        if a < 0: continue
        nz = rng.standard_normal((n, 2)).astype(np.float32)
        k = np.linspace(0, 1, n)
        # 分块带通，中心频率从 400Hz 扫到 6kHz
        out = np.zeros_like(nz); blk = 2048
        for i in range(0, n, blk):
            f = 400 * (15 ** k[i]); sos = butter(2, [f * 0.6, min(f * 1.6, sr / 2 - 100)], 'bandpass', fs=sr, output='sos')
            out[i:i + blk] = sosfilt(sos, nz[i:i + blk], axis=0)
        out *= (k ** 2.2)[:, None] * ref * 5.0 / (np.sqrt(np.mean(out[-sr // 2:] ** 2)) + 1e-9)
        y[a:a + n] += out
    for t, v in BOOMS:
        n = int(2.8 * sr); a = int(t * sr)
        if a + n > len(y): n = len(y) - a
        tt = np.arange(n) / sr
        f = 34 + 22 * np.exp(-tt * 6)
        b = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-tt * 1.6) * (1 - np.exp(-tt * 300)) * ref * 9.0 * v
        y[a:a + n] += b[:, None].astype(np.float32)
    # 卷积混响
    n = int(2.6 * sr); tt = np.arange(n) / sr
    ir = rng.standard_normal((n, 2)).astype(np.float32) * np.exp(-tt * 2.6)[:, None]
    sos = butter(1, 5000, 'lowpass', fs=sr, output='sos'); ir = sosfilt(sos, ir, axis=0)
    ir[:int(0.02 * sr)] = 0; ir /= np.sqrt((ir ** 2).sum(0))
    wet = np.stack([fftconvolve(y[:, 0], ir[:, 0])[:len(y)], fftconvolve(y[:, 1], ir[:, 1])[:len(y)]], 1)
    y = y * 0.82 + wet * 0.30
    y /= np.abs(y).max() / 0.9
    sf.write(wav, y.astype(np.float32), sr)


if __name__ == '__main__':
    d = os.path.join(WORK, 'music'); os.makedirs(d, exist_ok=True)
    beats, hits, accents = build()
    mid = os.path.join(d, 'score.mid'); MIDI.write(mid)
    wav = os.path.join(d, 'score_raw.wav')
    subprocess.run(['fluidsynth', '-ni', '-g', '0.6', '-r', '48000', '-F', wav, SF2, mid], check=True, capture_output=True)
    post(wav)
    json.dump(dict(beats=beats, hits=hits, accents=accents, soft=SOFT), open(os.path.join(d, 'beats.json'), 'w'))
    print('ok', wav, 'hits', [round(h, 2) for h in hits])
