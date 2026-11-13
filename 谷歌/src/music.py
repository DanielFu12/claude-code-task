"""第四期原创配乐：按时间线（work/timeline.json）直接写 MIDI，再用 FluidSynth + FluidR3 GM 音色库渲染。

前几期的配乐素材（Lyria 生成）没有入库，本环境也无法调用该服务；本期改为程序作曲：
  · 一套统一的音乐语言：80 BPM、4/4（每小节 3 秒），D 小调为主，第五章转 D 大调；
  · 同一个四音主题（D–A–F–E，小调；大调段为 D–A–F#–E）贯穿全片，按章节换配器；
  · 段落起点、高潮点直接取旁白时间线（章节起点、某句某词开始发声），不需要事后剪辑对位；
  · 三处“点燃”：片名、c4c“是我发起的”、片尾 logo；c4c 之后留白约两小节。
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
       'horn': 60, 'choir': 52, 'pad': 89, 'celesta': 8}
MIDI = pm.PrettyMIDI(initial_tempo=80)
TR = {}


def tr(name):
    if name not in TR:
        TR[name] = pm.Instrument(program=INS[name], name=name, is_drum=False)
        MIDI.instruments.append(TR[name])
    return TR[name]


def note(ins, p, t0, t1, v):
    v = int(max(1, min(127, v)))
    if t1 - t0 < 0.03 or v < 2: return
    tr(ins).notes.append(pm.Note(velocity=v, pitch=int(p), start=float(t0), end=float(t1)))


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
        if motif_every and b % motif_every == 0 and be - bt > BAR * 0.9 and 'nomotif' not in tex:
            motif(motif_ins, tonic, bt + BEAT * (0 if 'arp' not in tex else 0), v * 0.95, octave=motif_oct, major=major)


def hit(t, name, v=100, ring=6.0, big=True):
    """高潮重拍：圆号 + 全弦乐 + 定音鼓滚奏收束（滚奏在重拍前 1 拍开始）"""
    r, iv, bass = chord(name)
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
    # 开场：悬念（低音 D 持续 + 心跳 + 主题在钢琴上若隐若现），向片名渐强
    section(0.6, title, ['Dm', 'Bb/D', 'Gm/D', 'A/C#'], {'pad2', 'low', 'heart'}, 30, 70, motif_every=2, motif_oct=62)
    hit(title, 'Dm', 104)
    # 第一章：2004 年，温暖怀旧（F 大调，钢琴分解和弦）
    section(title + BAR * 1.5, c['ch2'], ['F', 'C/E', 'Dm', 'Bb', 'F/A', 'Gm', 'Bbmaj7', 'C'], {'arp', 'synth'}, 46, 52,
            tonic=5, major=True, motif_every=4, motif_oct=72)
    # 第二章：认错（D 小调，钢琴主题 + 大提琴长音）
    section(c['ch2'], c['ch3'], ['Dm', 'Bb', 'Gm', 'A', 'Dm', 'F', 'Gm', 'A'], {'piano_chord', 'low'}, 40, 48, motif_every=2, motif_oct=74)
    # 第三章：疑问（拨弦 + 弦乐铺底，结尾悬置）
    section(c['ch3'], c['ch4'], ['Dm', 'Gm', 'Bb', 'Asus4', 'Dm', 'Gm', 'Ebmaj7', 'Asus4'], {'pizz', 'pad'}, 40, 50, motif_every=4, motif_oct=67)
    # 第四章：推进 → “是我发起的” → 留白 → 定增故事（稳步前行）
    t_init = WT('c4c', '是我发起的')
    section(c['ch4'], t_init - BEAT, ['Dm', 'Bb', 'F', 'C', 'Dm', 'Bb', 'Gm', 'A'], {'eighths', 'pad', 'pizz'}, 42, 76, motif_every=4, motif_oct=72)
    hit(t_init, 'D', 98, ring=5.5)
    t_re = t_init + BAR * 2.2
    section(t_re, c['ch5'], ['Dm', 'Bb', 'F', 'C', 'Gm', 'Bb', 'C', 'A'], {'arp', 'pad2', 'low'}, 40, 52, motif_every=4, motif_oct=72)
    # 第五章：护城河（D 大调，圆号与弦乐，开阔）；m10 收窄；m12 转回小调
    t10 = S('m10') - BAR
    section(c['ch5'], t10, ['D', 'A/C#', 'Bm', 'G', 'D/F#', 'G', 'Em', 'A'], {'pad', 'low', 'harp', 'horn'}, 44, 62, major=True,
            motif_every=4, motif_ins='horn', motif_oct=62)
    t12 = S('m12') - 0.5
    section(t10, t12, ['Bm', 'G', 'Em', 'A'], {'pad2', 'piano_chord'}, 44, 48, major=True, motif_every=0)
    section(t12, c['ch6'], ['Dm', 'Bb', 'Gm', 'A'], {'pad', 'low', 'eighths'}, 46, 58, motif_every=2, motif_oct=62)
    # 第六章：分量（低音弦乐 + 心跳），c5f 稍亮，c5h 收回
    section(c['ch6'], S('c5f') - 0.5, ['Dm', 'Gm', 'Bb', 'A', 'Dm', 'Gm', 'Eb', 'A'], {'pad2', 'low', 'heart'}, 42, 50, motif_every=4, motif_oct=62)
    section(S('c5f') - 0.5, S('c5h') - 0.5, ['F', 'C', 'Dm', 'Bb'], {'arp', 'pad2'}, 44, 50, tonic=5, major=True, motif_every=0)
    section(S('c5h') - 0.5, c['ch7'], ['Dm', 'Bb', 'Gm', 'A'], {'pad', 'low'}, 44, 46, motif_every=2, motif_oct=72)
    # 第七章：开放的结尾（钢琴主题），c6i 起温暖收束到 D 大调
    t6i = S('c6i') - 0.6
    section(c['ch7'], t6i, ['Dm', 'Bb', 'F', 'C', 'Gm', 'Dm', 'Eb', 'A'], {'piano_chord', 'synth'}, 38, 46, motif_every=2, motif_oct=74)
    section(t6i, TL['logo'] - BEAT, ['Bb', 'F/A', 'Gm', 'Asus4', 'D'], {'pad', 'arp', 'low', 'choir'}, 46, 60, major=True, motif_every=2,
            motif_oct=74)
    hit(TL['logo'], 'D', 92, ring=T - TL['logo'] + 0.5)
    # 混响与声相
    for name, t in TR.items():
        pan = {'piano': 60, 'harp': 40, 'strings': 50, 'strings2': 78, 'cello': 70, 'bass': 64, 'pizz': 46, 'timp': 64, 'horn': 50,
               'choir': 64, 'pad': 64, 'celesta': 80}[name]
        t.control_changes += [pm.ControlChange(10, pan, 0.0), pm.ControlChange(91, 90 if name != 'timp' else 60, 0.0),
                              pm.ControlChange(7, {'horn': 92, 'timp': 100, 'choir': 70, 'pad': 70}.get(name, 100), 0.0)]
    beats = [k * BEAT for k in range(int(T / BEAT) + 1)]
    return beats, [title, t_init, TL['logo']]


if __name__ == '__main__':
    d = os.path.join(WORK, 'music'); os.makedirs(d, exist_ok=True)
    beats, hits = build()
    mid = os.path.join(d, 'score.mid'); MIDI.write(mid)
    wav = os.path.join(d, 'score_raw.wav')
    subprocess.run(['fluidsynth', '-ni', '-g', '0.6', '-r', '48000', '-F', wav, SF2, mid], check=True, capture_output=True)
    json.dump(dict(beats=beats, hits=hits), open(os.path.join(d, 'beats.json'), 'w'))
    print('ok', wav, 'hits', [round(h, 2) for h in hits])
