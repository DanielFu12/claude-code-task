"""第四期原创配乐：按时间线（work/timeline.json）直接写 MIDI，再用 FluidSynth + FluidR3 GM 音色库渲染。

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
    """t0–t1 之间按小节铺和弦进行 prog，tex 为配器集合；力度从 v0 线性到 v1"""
    nb = max(1, int(math.ceil((t1 - t0) / BAR - 1e-6)))
    for b in range(nb):
        bt = t0 + b * BAR; be = min(bt + BAR, t1)
        if be - bt < 0.3: break
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
                tt = bt + k * BEAT / 2
                if tt < be: note('piano', p, tt, tt + BEAT * 0.9, v * (0.62 if k else 0.72))
        if 'harp' in tex:
            ps = voicing(name, 55, 6)
            for k, p in enumerate(ps):
                tt = bt + k * BEAT / 3
                if tt < be: note('harp', p, tt, tt + BAR * 0.6, v * 0.5)
        if 'pizz' in tex:
            ps = voicing(name, 50, 3)
            for k in range(4):
                tt = bt + k * BEAT
                if tt < be: note('pizz', ps[k % 3] + (12 if k == 2 else 0), tt, tt + 0.25, v * 0.7)
        if 'eighths' in tex:                   # 弦乐八分音符低音持续（推进感）
            p = 48 + bass if 48 + bass <= 57 else 36 + bass
            for k in range(8):
                tt = bt + k * BEAT / 2
                if tt < be: note('cello', p, tt, tt + BEAT / 2 * 0.8, v * (0.55 if k % 2 else 0.68))
        if 'horn' in tex:
            for p in voicing(name, 53, 3): note('horn', p, bt, be + 0.2, v * 0.55)
        if 'choir' in tex:
            for p in voicing(name, 60, 3): note('choir', p, bt, be + 0.5, v * 0.4)
        if 'heart' in tex:                     # 定音鼓心跳（第 1、2 拍弱）
            note('timp', 26 + (r + 12) % 12 if (r % 12) < 7 else 26 + r % 12 - 12, bt, bt + 0.9, v * 0.55)
            note('timp', 26 + (r + 12) % 12 if (r % 12) < 7 else 26 + r % 12 - 12, bt + BEAT * 0.55, bt + BEAT * 1.4, v * 0.35)
        if 'piano_chord' in tex:
            for p in voicing(name, 57, 4): note('piano', p, bt, bt + BAR * 0.95, v * 0.55)
            note('piano', 36 + bass, bt, bt + BAR, v * 0.5)
        if 'trem' in tex:                      # 弦乐颤音：紧张、期待
            for p in voicing(name, 50, 4): note('trem', p, bt, be + 0.15, v * 0.62)
        if 'ostinato' in tex:                  # 弦乐十六分音符固定音型（推进、唤醒）
            ps = voicing(name, 62, 3)
            pat = [0, 1, 2, 1, 0, 1, 2, 1, 0, 2, 1, 2, 0, 1, 2, 1]
            for k, j in enumerate(pat):
                tt = bt + k * BEAT / 4
                if tt < be: note('spic', ps[j] + (12 if k in (8, 12) and 'high' in tex else 0), tt, tt + BEAT / 4 * 0.7,
                                 v * (0.62 if k % 4 == 0 else 0.46))
        if 'perc' in tex or 'perc2' in tex:    # 打击乐：大鼓 + 落地通鼓切分（perc2 更密，带太鼓）
            for k in range(8):
                tt = bt + k * BEAT / 2
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
        if 'brassmotif' in tex and b % 2 == 0 and be - bt > BAR * 0.9:     # 主题由小号 + 圆号齐奏（高潮段）
            motif('trumpet', tonic, bt, v * 0.85, octave=62, major=major, dur=BEAT, last=2.0)
            motif('horn', tonic, bt, v * 0.8, octave=50, major=major, dur=BEAT, last=2.0)
        if motif_every and b % motif_every == 0 and be - bt > BAR * 0.9 and 'nomotif' not in tex:
            motif(motif_ins, tonic, bt + BEAT * (0 if 'arp' not in tex else 0), v * 0.95, octave=motif_oct, major=major)


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
    # ---- 开场：悬念 → 巴菲特原声下只留颤音 → 原声后起势，打击乐 + 固定音型 + 上扬，撞进片名
    so = S('sot_dontlike')
    section(0.6, so - 0.3, ['Dm', 'Bb/D', 'Gm/D', 'A/C#'], {'pad2', 'low', 'heart'}, 30, 58, motif_every=2, motif_oct=62)
    section(so - 0.3, E('sot_dontlike') + 0.2, ['Dm', 'Gm/D'], {'trem', 'low', 'nomotif'}, 44, 50)
    section(E('sot_dontlike') + 0.2, title, ['Bb', 'Gm', 'A'], {'trem', 'low', 'ostinato', 'perc', 'nomotif'}, 62, 88)
    riser(title, 3.2, 92)
    hit(title, 'Dm', 112)
    # ---- 第一章：2004 年，温暖怀旧（F 大调，钢琴分解和弦）
    section(title + BAR * 1.5, c['ch2'], ['F', 'C/E', 'Dm', 'Bb', 'F/A', 'Gm', 'Bbmaj7', 'C'], {'arp', 'synth'}, 46, 54,
            tonic=5, major=True, motif_every=4, motif_oct=72)
    # ---- 第二章：认错（D 小调，钢琴主题 + 大提琴长音）
    section(c['ch2'], c['ch3'], ['Dm', 'Bb', 'Gm', 'A', 'Dm', 'F', 'Gm', 'A'], {'piano_chord', 'low'}, 40, 50, motif_every=2, motif_oct=74)
    # ---- 第三章：疑问（拨弦 + 弦乐铺底）；价格跑远时颤音收紧
    section(c['ch3'], S('c3e') - 0.4, ['Dm', 'Gm', 'Bb', 'Asus4', 'Dm', 'Gm', 'Ebmaj7', 'Asus4'], {'pizz', 'pad'}, 40, 50, motif_every=4, motif_oct=67)
    section(S('c3e') - 0.4, c['ch4'], ['Dm', 'Bb', 'Gm', 'A'], {'pizz', 'trem', 'low'}, 48, 60, motif_every=4, motif_oct=67)
    # ---- 第四章：推进（八分低音 → 十六分固定音型 + 打击乐）→ “是我发起的” → 留白 → 定增故事的节奏
    t_init = WT('c4c', '是我发起的')
    section(c['ch4'], S('c4b') - 0.3, ['Dm', 'Bb', 'F', 'C'], {'eighths', 'pad', 'pizz'}, 44, 58, motif_every=4, motif_oct=72)
    section(S('c4b') - 0.3, t_init - BEAT, ['Dm', 'Bb', 'Gm', 'A'], {'eighths', 'pad', 'ostinato', 'perc'}, 60, 86, motif_every=4, motif_oct=72)
    riser(t_init, 2.6, 88)
    hit(t_init, 'D', 106, ring=5.5)
    t_re = t_init + BAR * 2.2
    section(t_re, S('c4f') - 0.4, ['Dm', 'Bb', 'F', 'C'], {'arp', 'pad2', 'low'}, 40, 48, motif_every=4, motif_oct=72)
    section(S('c4f') - 0.4, S('c4h') - 0.4, ['Dm', 'Bb', 'F', 'C', 'Gm', 'Bb', 'C', 'A'], {'eighths', 'pad', 'perc'}, 50, 64, motif_every=4, motif_oct=72)
    section(S('c4h') - 0.4, S('c4i') - 0.3, ['F', 'C', 'Dm', 'Bb'], {'arp', 'pad2', 'low'}, 48, 52, tonic=5, major=True, motif_every=0)
    section(S('c4i') - 0.3, c['ch5'], ['Gm', 'Bb', 'Asus4', 'A'], {'trem', 'low', 'nomotif'}, 50, 66)
    riser(c['ch5'], 2.0, 70)
    # ---- 第五章：护城河。2007 年的信（D 大调，圆号）→ 四段护城河逐段点亮，层层加码到全编制铜管主题
    #      → 第五段“花钱挖的”突然转小调 → 原声“会遭到攻击”下只留低音 → 小调推进收章
    hit(c['ch5'], 'D', 84, ring=4.0, big=False)
    section(c['ch5'] + BAR * 0.5, S('m5') - 0.4, ['D', 'A/C#', 'Bm', 'G', 'D/F#', 'G', 'Em', 'A'], {'pad', 'low', 'harp', 'horn'}, 44, 56,
            major=True, motif_every=4, motif_ins='horn', motif_oct=62)
    P = ['D', 'Bm', 'G', 'A']
    section(S('m5') - 0.4, S('m6') - 0.3, P, {'pad', 'low', 'ostinato', 'perc', 'nomotif'}, 58, 66, major=True)
    section(S('m6') - 0.3, S('m7') - 0.3, P, {'pad', 'low', 'ostinato', 'perc', 'brass'}, 66, 72, major=True, motif_every=4, motif_ins='horn', motif_oct=62)
    section(S('m7') - 0.3, S('m8') - 0.5, P, {'pad', 'low', 'ostinato', 'high', 'perc2', 'brass', 'nomotif'}, 72, 82, major=True)
    riser(S('m8') - 0.25, 2.2, 84)
    hit(S('m8') - 0.25, 'D', 96, ring=3.0)
    section(S('m8') - 0.25, S('m9') - 0.35, ['D', 'G', 'A', 'D'], {'pad', 'low', 'ostinato', 'high', 'perc2', 'brass', 'brassmotif', 'choir', 'nomotif'},
            88, 92, major=True)
    t9 = S('m9') - 0.35
    note('trombone', 26, t9, t9 + 3.5, 90); drum('kick', t9, 100, 1.0); note('taiko', 26, t9, t9 + 2, 96)
    section(t9, S('m10') - 0.3, ['Dm', 'Bb', 'Gm', 'A'], {'pad2', 'low', 'trem', 'nomotif'}, 54, 50)
    section(S('m10') - 0.3, E('sot_attacks') + 0.3, ['Dm', 'Gm/D', 'Dm', 'Bb', 'Gm', 'A'], {'pad2', 'synth', 'nomotif'}, 36, 40)
    section(E('sot_attacks') + 0.3, S('m12') - 0.3, ['Dm', 'Bb', 'Gm', 'A'], {'pad', 'low', 'eighths'}, 46, 54, motif_every=2, motif_oct=62)
    section(S('m12') - 0.3, c['ch6'], ['Dm', 'Bb', 'Gm', 'A'], {'pad', 'low', 'eighths', 'trem', 'perc'}, 56, 64, motif_every=2, motif_oct=62)
    # ---- 第六章：采访与资本开支（低音弦乐 + 心跳）；2000 亿的资本开支 → 颤音与鼓点收紧；云收入稍亮，现金流收回
    section(c['ch6'], S('c5d') - 0.4, ['Dm', 'Gm', 'Bb', 'A', 'Dm', 'Gm', 'Eb', 'A'], {'pad2', 'low', 'heart'}, 40, 46, motif_every=4, motif_oct=62)
    section(S('c5d') - 0.4, S('c5e') - 0.2, ['Dm', 'Bb', 'Gm', 'A'], {'trem', 'low', 'eighths', 'perc', 'nomotif'}, 52, 72)
    section(S('c5e') - 0.2, S('c5f') - 0.5, ['Dm', 'Bb', 'Gm', 'A'], {'pad2', 'low', 'nomotif'}, 40, 44)
    section(S('c5f') - 0.5, S('c5g') - 0.4, ['F', 'C', 'Dm', 'Bb'], {'arp', 'pad2', 'ostinato'}, 48, 58, tonic=5, major=True, motif_every=0)
    section(S('c5g') - 0.4, c['ch7'], ['Dm', 'Bb', 'Gm', 'A'], {'pad', 'low', 'heart'}, 44, 46, motif_every=2, motif_oct=72)
    # ---- 第七章：复盘（钢琴主题）→ 三件事（脉动）→ 结尾全编制上扬，铜管主题，撞进片尾 logo
    section(c['ch7'], S('c6e') - 0.4, ['Dm', 'Bb', 'F', 'C', 'Gm', 'Dm', 'Eb', 'A'], {'piano_chord', 'synth'}, 38, 46, motif_every=2, motif_oct=74)
    section(S('c6e') - 0.4, S('c6i') - 0.5, ['Dm', 'Bb', 'F', 'C'], {'pad', 'low', 'pizz', 'perc', 'eighths'}, 50, 64, motif_every=4, motif_oct=72)
    section(S('c6i') - 0.5, S('c6j') - 0.3, ['Bb', 'F/A', 'Gm', 'Asus4'], {'pad', 'arp', 'low', 'choir', 'ostinato', 'nomotif'}, 62, 72, major=True)
    section(S('c6j') - 0.3, TL['logo'] - BEAT, ['D', 'Bm', 'G', 'A', 'D', 'G', 'Asus4', 'A'],
            {'pad', 'arp', 'low', 'choir', 'ostinato', 'high', 'perc2', 'brass', 'brassmotif', 'nomotif'}, 76, 90, major=True)
    riser(TL['logo'], 3.0, 96)
    hit(TL['logo'], 'D', 110, ring=T - TL['logo'] + 0.5)
    # 混响与声相
    for name, t in TR.items():
        if name == 'drums':
            t.control_changes += [pm.ControlChange(91, 50, 0.0), pm.ControlChange(7, 96, 0.0)]; continue
        pan = {'piano': 60, 'harp': 40, 'strings': 50, 'strings2': 78, 'cello': 70, 'bass': 64, 'pizz': 46, 'timp': 64, 'horn': 50,
               'choir': 64, 'pad': 64, 'celesta': 80, 'trem': 44, 'spic': 84, 'brass': 58, 'trumpet': 70, 'trombone': 54, 'taiko': 64}[name]
        t.control_changes += [pm.ControlChange(10, pan, 0.0), pm.ControlChange(91, 60 if name not in ('timp', 'taiko') else 40, 0.0),
                              pm.ControlChange(7, {'horn': 92, 'timp': 100, 'choir': 70, 'pad': 70, 'spic': 84, 'brass': 88,
                                                   'trumpet': 84, 'trombone': 88, 'taiko': 110}.get(name, 100), 0.0)]
    beats = [k * BEAT for k in range(int(T / BEAT) + 1)]
    return beats, [title, t_init, TL['logo']], [S('m8') - 0.25, S('m9') - 0.35, c['ch5']]


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
    json.dump(dict(beats=beats, hits=hits, accents=accents), open(os.path.join(d, 'beats.json'), 'w'))
    print('ok', wav, 'hits', [round(h, 2) for h in hits])
