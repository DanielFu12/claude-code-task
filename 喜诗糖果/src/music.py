"""第五期原创配乐（沿用第四期的程序作曲框架）：按时间线（work/timeline.json）直接写 MIDI，再用 FluidSynth + FluidR3 GM 音色库渲染。

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
from script import LINES, TEASE

TL = json.load(open(os.path.join(WORK, 'timeline.json')))
SEG = {s['id']: s for s in TL['segs']}
CH = TL['chapters']
SAY = {l[0]: (l[3] or l[2]) for l in LINES}; SAY['tease'] = TEASE[1]
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
    # v3 卡点：片名、各章章节号亮起（章节卡开始后 0.5s）、h3“19 亿”、c3c“四倍多”、c4e“13.5 亿”、c5d“芒格把我扳了过来”、
    #           c7d“眼睛”、片尾“Costco”、logo。全部落在小节线上；章与章之间，要点卡期间音乐上扬，章节号亮起时重拍落下。
    hc = {k: c[k] + 0.5 for k in ('ch2', 'ch3', 'ch4', 'ch5', 'ch6', 'ch7')}
    t19 = WT('h3', '19 亿'); t4x = WT('c3c', '四倍多'); t_cash = WT('c4e', '十三点五亿'); t_turn = WT('c5d', '芒格把我扳了过来')
    t_eye = WT('c7d', '眼睛'); t_next = WT('tease', 'Costco'); logo = TL['logo']
    make_grid([title, t19, t4x, t_cash, t_turn, t_eye, t_next, logo] + list(hc.values()), T)
    tk = lambda cid: CH['tk_' + cid][0]

    def bridge(prev, cid, prog, to, v=92):
        """要点卡 → 章节号：弦乐颤音 + 合唱上扬，军鼓滚奏推到章节号的重拍"""
        a = tk(prev) - 0.2; h = hc[cid]
        section(a, h, prog, {'pad', 'trem', 'low', 'choir', 'nomotif'}, 46, 68)
        riser(h, min(2.8, h - snap(a) - 0.2), 84)
        hit(h, to, v, ring=3.5, big=False)
        return nxtbar(h)

    # ---- 开场：钢琴分解和弦讲故事 →“19 亿”点题 → 三个问题起势 → 撞进片名
    section(0.6, t19, ['F', 'C/E', 'Dm', 'Bb', 'F/A', 'Gm', 'Bb', 'C'], {'arp', 'pad2', 'low'}, 34, 52, tonic=5, major=True, motif_every=4)
    accent(t19, 'F', 84)
    section(t19, S('h4') - 0.2, ['F', 'Dm', 'Bb', 'C'], {'arp', 'pad', 'low', 'harp'}, 52, 58, tonic=5, major=True, motif_every=0)
    section(S('h4') - 0.2, title, ['Bb', 'Gm', 'C'], {'trem', 'low', 'ostinato', 'perc', 'nomotif'}, 60, 88)
    riser(title, 3.0, 92)
    hit(title, 'F', 110)
    # ---- 第一章：玛丽·喜的小店 → 谈判（D 小调拨弦，八分低音收紧）→ 成交与握手（温暖）→ 认错：芒格说对了（圆号主题）
    section(nxtbar(title), S('c1d') - 0.4, ['F', 'C/E', 'Dm', 'Bb', 'F/A', 'Gm', 'Bb', 'C'], {'arp', 'harp', 'pad2'}, 42, 52,
            tonic=5, major=True, motif_every=4)
    section(S('c1d') - 0.4, S('c1c') - 0.3, ['Dm', 'Bb', 'Gm', 'A'], {'pizz', 'eighths', 'pad2', 'low'}, 48, 62, motif_every=4, motif_oct=67)
    section(S('c1c') - 0.3, S('c1g') - 0.3, ['F', 'Bb', 'F/A', 'C'], {'arp', 'pad2', 'low'}, 50, 52, tonic=5, major=True, motif_every=0)
    section(S('c1g') - 0.3, tk('ch1'), ['Bb', 'F/A', 'Gm', 'C'], {'pad', 'low', 'horn'}, 50, 58, tonic=5, major=True, motif_every=4,
            motif_ins='horn', motif_oct=65)
    s2 = bridge('ch1', 'ch2', ['Bb', 'C'], 'Dm')
    # ---- 第二章：看不见的资产（钢琴和弦 + 铺底）→ 60% 的回报（拨弦推进）
    section(s2, S('c2e') - 0.4, ['Dm', 'Bb', 'F', 'C', 'Gm', 'Bb', 'Dm', 'C'], {'piano_chord', 'pad2', 'synth', 'low'}, 42, 52, motif_every=4, motif_oct=74)
    section(S('c2e') - 0.4, tk('ch2'), ['F', 'C', 'Dm', 'Bb'], {'pizz', 'pad', 'eighths', 'low'}, 48, 62, tonic=5, major=True, motif_every=4)
    s3 = bridge('ch2', 'ch3', ['Gm', 'C'], 'F')
    # ---- 第三章：定价权——表格逐行推进（固定音型 + 打击乐）→“四倍多”重拍 → 顾客的信（拨弦、竖琴，俏皮）→ 边界（转小调）
    section(s3, S('c3b') - 0.3, ['F', 'Bb', 'Dm', 'C'], {'pad2', 'arp'}, 42, 50, tonic=5, major=True, motif_every=0)
    section(S('c3b') - 0.3, t4x, ['F', 'C', 'Dm', 'Bb', 'F', 'C', 'Bb', 'C'], {'pad', 'low', 'ostinato', 'perc', 'eighths'}, 56, 80,
            tonic=5, major=True, motif_every=4)
    riser(t4x, 1.8, 80)
    hit(t4x, 'F', 96, ring=3.0, big=False)
    section(nxtbar(t4x), S('c3f') - 0.4, ['F', 'C/E', 'Dm', 'Bb'], {'pad', 'arp', 'low', 'eighths'}, 56, 50, tonic=5, major=True, motif_every=0)
    section(S('c3f') - 0.4, S('c3i') - 0.4, ['F', 'Dm', 'Gm', 'C', 'F', 'Bb', 'Gm', 'C'], {'pizz', 'harp', 'pad2'}, 46, 54, tonic=5, major=True,
            motif_every=4, motif_oct=74)
    section(S('c3i') - 0.4, tk('ch3'), ['Dm', 'Bb', 'Gm', 'A'], {'pad2', 'low', 'trem'}, 44, 50, motif_every=0)
    s4 = bridge('ch3', 'ch4', ['Bb', 'C'], 'Dm')
    # ---- 第四章：印钞机——行业平淡 → 利润与资本层层加码 → 13.5 亿（大重拍）→ 三种账户（拨弦）→ 繁衍（铜管主题）
    section(s4, S('c4d') - 0.3, ['Dm', 'Bb', 'F', 'C'], {'pad2', 'low', 'pizz'}, 42, 52, motif_every=4, motif_oct=67)
    section(S('c4d') - 0.3, t_cash, ['F', 'C', 'Dm', 'Bb'], {'pad', 'low', 'ostinato', 'perc', 'eighths'}, 58, 86, tonic=5, major=True, motif_every=0)
    riser(t_cash, 2.4, 88)
    hit(t_cash, 'F', 106, ring=4.0)
    section(nxtbar(t_cash), S('c4g') - 0.3, ['F', 'C/E', 'Dm', 'Bb'], {'pad', 'arp', 'low'}, 54, 52, tonic=5, major=True, motif_every=4)
    section(S('c4g') - 0.3, S('c4i') - 0.3, ['F', 'Bb', 'Gm', 'C', 'Dm', 'Bb', 'Gm', 'A'], {'pizz', 'pad2', 'harp'}, 46, 52, tonic=5, major=True,
            motif_every=4, motif_oct=74)
    section(S('c4i') - 0.3, tk('ch4'), ['F', 'C', 'Dm', 'Bb', 'F', 'C', 'Bb', 'C'], {'pad', 'low', 'ostinato', 'perc', 'brass', 'brassmotif', 'nomotif'},
            62, 76, tonic=5, major=True)
    s5 = bridge('ch4', 'ch5', ['Gm', 'A'], 'Dm', 90)
    # ---- 第五章：烟蒂（小调、心跳）→ 芒格原声（只留铺底）→“芒格把我扳了过来”（大重拍）→ 蓝图（圆号主题）→ 老搭档（钢琴）→ 喜诗成了课堂
    section(s5, t_turn, ['Dm', 'Gm/D', 'Bb', 'A'], {'pizz', 'low', 'pad2', 'heart'}, 40, 60, motif_every=4, motif_oct=62)
    riser(t_turn, 2.2, 84)
    hit(t_turn, 'F', 100, ring=3.5, big=False)
    section(nxtbar(t_turn), S('c5g') - 0.3, ['F', 'C/E', 'Dm', 'Bb', 'F/A', 'Bb', 'Gm', 'C'], {'pad', 'low', 'horn', 'ostinato'}, 56, 64,
            tonic=5, major=True, motif_every=4, motif_ins='horn', motif_oct=65)
    section(S('c5g') - 0.3, S('c5i') - 0.3, ['F', 'Dm', 'Bb', 'C'], {'piano_chord', 'pad2', 'synth'}, 46, 50, tonic=5, major=True, motif_every=2, motif_oct=74)
    section(S('c5i') - 0.3, tk('ch5'), ['F', 'C', 'Dm', 'Bb', 'Gm', 'Bb', 'C', 'C'], {'arp', 'pad', 'low', 'eighths'}, 50, 64, tonic=5, major=True,
            motif_every=4)
    s6 = bridge('ch5', 'ch6', ['Bb', 'A'], 'Dm', 86)
    # ---- 第六章：做不到的事（D 小调，心跳与长音）
    section(s6, tk('ch6'), ['Dm', 'Bb', 'Gm', 'A', 'Dm', 'Gm', 'Eb', 'A'], {'pad2', 'low', 'heart'}, 40, 48, motif_every=4, motif_oct=62)
    s7 = bridge('ch6', 'ch7', ['Bb', 'C'], 'F', 92)
    # ---- 第七章：百年老店 → 巴菲特原声（铺底）→ 结论：合唱与弦乐慢慢涨起，“眼睛”处点题 → 片尾：Costco 预告起新的律动 → logo
    so = S('sot_trick')
    section(s7, so - 0.3, ['F', 'C/E', 'Dm', 'Bb', 'F/A', 'Gm', 'Bb', 'C'], {'arp', 'harp', 'pad2'}, 44, 54, tonic=5, major=True, motif_every=4)
    section(so - 0.3, E('sot_trick') + 0.3, ['F', 'Dm', 'Bb', 'C'], {'pad2', 'low', 'nomotif'}, 32, 36, tonic=5, major=True)
    section(E('sot_trick') + 0.3, t_eye, ['Bb', 'C', 'Dm', 'Bb', 'F/A', 'Gm', 'Csus4', 'C'], {'pad', 'arp', 'low', 'choir', 'harp'}, 50, 72,
            tonic=5, major=True, motif_every=2)
    accent(t_eye, 'F', 96, ring=6.0)
    section(nxtbar(t_eye), t_next, ['F', 'Bb', 'F/A', 'C'], {'pad', 'choir', 'low', 'nomotif'}, 58, 46, tonic=5, major=True)
    riser(t_next, 1.6, 72)
    hit(t_next, 'Dm', 94, ring=3.0, big=False)
    section(nxtbar(t_next), logo, ['Dm', 'Bb', 'F', 'C', 'Dm', 'Bb', 'Gm', 'A'],
            {'pad', 'low', 'ostinato', 'perc', 'eighths', 'brass', 'nomotif'}, 58, 86)
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
    SOFT[:] = [t19, t4x, t_eye, t_next]                 # 句中的点题：配乐只半闪避，不压字
    return beats, [title, t19, t4x, t_cash, t_turn, t_eye, t_next, logo] + list(hc.values()), list(hc.values())


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
