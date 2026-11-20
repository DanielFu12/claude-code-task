"""原创配乐（真实乐器音色）：MIDI 编曲 -> fluidsynth + FluidR3_GM 分轨渲染 -> 叠加合成重击/上升音 -> 混音。
所有落点读自 work/timeline.json（cues / sections），与画面共用。
情绪弧线：
  第一幕 D 小调钢琴叹息动机 + 琶音，每个「如今……」用定音鼓 + 低音弦乐重音砸下；
  追问：心跳加速、弦乐颤音渐强 → 只剩一个钢琴单音 → 标题全奏；
  第二幕倒带：每段开头一声磁带倒卷；内心独白只铺一层弦乐，芒格的问题落在整拍并进入「心跳」律动；
  第五段铁锤：低音提琴 8 分暗涌，三锤 = 太鼓 + 定音鼓 + 铁砧 + 次低频，严格一小节一锤，锤前一拍抽空，之后全部抽空；
  第三幕觉醒：钢琴独奏 → 转 F 大调，三个问题各落一记，「真正的安全边际」由圆号唱出全片最高点，最后只剩钢琴。"""
import json, os, sys, subprocess
import numpy as np, soundfile as sf
from scipy import signal
import mido

W = sys.argv[1] if len(sys.argv) > 1 else 'work'
TL = json.load(open(f'{W}/timeline.json'))
SR = 48000; BEAT = TL['beat']; BAR = 4 * BEAT; T = TL['total']
S = TL['sections']; LN = {l['id']: l for l in TL['lines']}; CUE = TL['cues']
SF2 = '/usr/share/sounds/sf2/FluidR3_GM.sf2'
N = int(T * SR) + SR * 4
rng = np.random.default_rng(7)
HITS = []

# ================================================================ MIDI 编曲
NOTE = {n: i for i, n in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])}
def M(s): return 12 * (int(s[-1]) + 1) + NOTE[s[:-1]]
def Ms(*ss): return [M(x) for x in ss]

STEMS = {}   # stem -> list of (time, msg)
PROG = dict(piano=(0, 0), strings=(1, 48), slow=(2, 49), cello=(3, 42), bass=(4, 43), choir=(5, 52),
            horn=(6, 60), timp=(7, 47), taiko=(8, 116), drums=(9, None), harp=(10, 46))
STEM_OF = dict(piano='piano', harp='piano', strings='str', slow='str', cello='low', bass='low', choir='str',
               horn='brass', timp='perc', taiko='perc', drums='perc')

def ev(inst, t, msg):
    STEMS.setdefault(STEM_OF[inst], []).append((max(t, 0.0), msg))

def note(inst, p, t, dur, vel):
    ch = PROG[inst][0]; vel = int(np.clip(vel, 1, 127))
    ev(inst, t, mido.Message('note_on', channel=ch, note=int(p), velocity=vel))
    ev(inst, t + max(dur, 0.05), mido.Message('note_off', channel=ch, note=int(p), velocity=0))

def chord(inst, ps, t, dur, vel, spread=0.0):
    for k, p in enumerate(ps): note(inst, p, t + k * spread, dur - k * spread, vel)

def cc(inst, t, ctl, val):
    ev(inst, t, mido.Message('control_change', channel=PROG[inst][0], control=ctl, value=int(np.clip(val, 0, 127))))

def ramp(inst, t0, t1, v0, v1, ctl=11, step=0.08):
    n = max(2, int((t1 - t0) / step))
    for k in range(n + 1):
        u = k / n; cc(inst, t0 + (t1 - t0) * u, ctl, v0 + (v1 - v0) * u)

def write_midis():
    paths = {}
    for stem, evs in STEMS.items():
        mid = mido.MidiFile(ticks_per_beat=480); tr = mido.MidiTrack(); mid.tracks.append(tr)
        tr.append(mido.MetaMessage('set_tempo', tempo=750000, time=0))
        for inst, (ch, pg) in PROG.items():
            if STEM_OF[inst] != stem: continue
            if pg is not None: tr.append(mido.Message('program_change', channel=ch, program=pg, time=0))
            tr.append(mido.Message('control_change', channel=ch, control=7, value=110, time=0))
            tr.append(mido.Message('control_change', channel=ch, control=11, value=110, time=0))
            tr.append(mido.Message('control_change', channel=ch, control=91, value=0, time=0))
            tr.append(mido.Message('control_change', channel=ch, control=93, value=0, time=0))
        last = 0
        for t, msg in sorted(evs, key=lambda e: (e[0], e[1].type == 'note_on')):
            tick = int(round(t / BEAT * 480))
            tr.append(msg.copy(time=tick - last)); last = tick
        tr.append(mido.MetaMessage('end_of_track', time=480 * 8))
        p = f'{W}/stem_{stem}.mid'; mid.save(p); paths[stem] = p
    return paths

def render(paths):
    out = {}
    for stem, p in paths.items():
        wav = p.replace('.mid', '.wav')
        subprocess.run(['fluidsynth', '-ni', '-q', '-g', '0.7', '-R', '0', '-C', '0', '-r', str(SR), '-F', wav, SF2, p],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        y, sr = sf.read(wav, dtype='float32')
        if y.ndim == 1: y = np.stack([y, y], 1)
        z = np.zeros((N, 2), np.float32); n = min(len(y), N); z[:n] = y[:n]; out[stem] = z
    return out

# ---------------------------------------------------------------- 动机
MOTIF_MIN = [('A4', 0, 1), ('D5', 1, 1), ('C5', 2, .5), ('A4', 2.5, .5), ('G4', 3, 1), ('F4', 4, 1.5), ('E4', 5.5, .5), ('D4', 6, 2)]
MOTIF_MAJ = [('C5', 0, 1), ('F5', 1, 1), ('E5', 2, .5), ('C5', 2.5, .5), ('A#4', 3, 1), ('A4', 4, 1.5), ('G4', 5.5, .5), ('F4', 6, 2)]
def motif(inst, t0, mot, vel=60, shift=0, sus=1.0):
    for n_, b, d in mot:
        note(inst, M(n_) + shift, t0 + b * BEAT, d * BEAT * sus, vel + (6 if b in (1, 4) else 0))

DM, BB, F_, C_, GM_, A_ = Ms('D3', 'F3', 'A3'), Ms('A#2', 'D3', 'F3'), Ms('F3', 'A3', 'C4'), Ms('C3', 'E3', 'G3'), Ms('G2', 'A#2', 'D3'), Ms('A2', 'C#3', 'E3')
ROOTS = {'DM': 'D2', 'BB': 'A#1', 'F': 'F2', 'C': 'C2', 'GM': 'G1', 'A': 'A1'}
CHD = dict(DM=DM, BB=BB, F=F_, C=C_, GM=GM_, A=A_)

def stab(t, root='D', big=1.0):
    """「如今……」的重音：定音鼓 + 低音弦乐 sfz + 钢琴低音八度"""
    r2, r1 = M(root + '2'), M(root + '1')
    note('timp', r2, t, 1.5, 100 * big + 10); note('timp', r2 - 12 + 12, t + 0.01, 1.0, 60)
    chord('bass', [r1, r2], t, 2.2, 112 * big); chord('cello', [r2, r2 + 12], t, 1.8, 105 * big)
    chord('piano', [r1 + 12, r2 + 12], t, 2.5, 95 * big)

def silence_mask(t, win):
    return any(c - win <= t < c for c in STOP)

CHD['EB'] = Ms('D#3', 'G3', 'A#3'); ROOTS['EB'] = 'D#2'
CHD['FM'] = Ms('F3', 'A3', 'C4');    ROOTS['FM'] = 'F2'
GOLDEN = ['L24', 'L34', 'L54', 'L60', 'L84', 'L92']
REVEAL = ['L04', 'L07', 'L08', 'L09', 'L13']
STOP = [CUE[k] for k in REVEAL + GOLDEN + ['L63a', 'L63b', 'L63c']] + [S['title'], S['q1_card'], S['q2_card'], S['q3_card']]
L0 = lambda i: LN[i]['t0']; L1 = lambda i: LN[i]['t1']

def arp_bed(t0, t1, prog, vel=46, drum=True, bassline=True, low=False):
    """钢琴 8 分琶音 + 大提琴根音 + 弦乐和声（遇到揭晓点前一拍自动抽空）"""
    k0, k1 = int(round(t0 / BEAT)), int(round(t1 / BEAT))
    for k in range(k0, k1):
        t = k * BEAT; bar = (k - k0) // 4; c = prog[bar % len(prog)]; ms = CHD[c]
        if (k - k0) % 4 == 0:
            if bassline: note('cello', M(ROOTS[c]) + 12, t, BAR * 0.95, 58)
            if not silence_mask(t + BAR * 0.9, BEAT): chord('strings', [m + 12 for m in ms], t, BAR * 0.98, vel)
        for h in range(2):
            th = t + h * BEAT / 2
            if silence_mask(th, BEAT): continue
            idx = [0, 1, 2, 1, 0, 2, 1, 2][((k - k0) % 4) * 2 + h]
            note('piano', ms[idx] + (0 if low else 12), th, BEAT * 0.9, vel + 8 * (h == 0))
        if drum and (k - k0) % 2 == 0 and not silence_mask(t, BEAT): note('drums', 35, t, 0.2, 56)

def pulse(t0, t1, prog, vel=64, timp=True, choir=0):
    """低音弦乐 8 分律动（冷静推进 / 暗涌）"""
    k0, k1 = int(round(t0 / BEAT)), int(round(t1 / BEAT))
    for k in range(k0, k1):
        t = k * BEAT; bar = (k - k0) // 4; c = prog[bar % len(prog)]
        for h in range(2):
            th = t + h * BEAT / 2
            if silence_mask(th, BEAT): continue
            p = M(ROOTS[c]) + (12 if h else 0)
            note('bass', M(ROOTS[c]), th, BEAT * 0.42, vel * (1 if h == 0 else 0.8)); note('cello', p + 12, th, BEAT * 0.4, vel * 0.85)
        if (k - k0) % 4 == 0 and not silence_mask(t + BAR * 0.9, BEAT):
            chord('strings', [m + 12 for m in CHD[c]], t, BAR * 0.98, vel * 0.7)
            if choir: chord('choir', CHD[c], t, BAR * 0.98, choir)
            if timp: note('timp', M(ROOTS[c]), t, 1.0, vel + 6)

def broken(t0, t1, prog, vel=50, melody=None, mel_inst='cello'):
    """钢琴分解和弦（4 分）+ 弦乐长音，可叠一条旋律（反思 / 温暖）"""
    k0, k1 = int(round(t0 / BEAT)), int(round(t1 / BEAT))
    for k in range(k0, k1):
        t = k * BEAT; bar = (k - k0) // 4; c = prog[bar % len(prog)]; ms = CHD[c]
        if silence_mask(t, BEAT): continue
        note('piano', ms[(k - k0) % 3] + 12, t, BEAT * 1.6, vel)
        if (k - k0) % 4 == 0:
            note('piano', M(ROOTS[c]), t, BAR, vel + 6)
            if not silence_mask(t + BAR * 0.9, BEAT): chord('strings', [m + 12 for m in ms], t, BAR * 0.98, vel - 6)
    if melody:
        for tm in range(k0, k1 - 7, 16): motif(mel_inst, tm * BEAT, melody, vel + 4, -12 if mel_inst == 'cello' else 0, 1.05)

def anthem(t0, t1, prog, build0=0.3, build1=1.2, horn=True):
    """F 大调全奏：弦乐 + 合唱 + 低音 + 钢琴琶音 + 定音鼓（逐渐增强）"""
    k0, k1 = int(round(t0 / BEAT)), int(round(t1 / BEAT))
    for k in range(k0, k1):
        t = k * BEAT; bar = (k - k0) // 4; c = prog[bar % len(prog)]; ms = CHD[c]
        b = build0 + (build1 - build0) * (k - k0) / max(k1 - k0, 1)
        if silence_mask(t, BEAT): continue
        if (k - k0) % 4 == 0:
            chord('strings', [m + 12 for m in ms] + [ms[0]], t, BAR * 0.98, 45 + 40 * min(b, 1.1))
            note('bass', M(ROOTS[c]), t, BAR * 0.95, 60 + 30 * min(b, 1))
            if b > 0.5: chord('choir', [m + 12 for m in ms], t, BAR * 0.98, 40 + 45 * min(b, 1.1))
            if b > 0.7: note('timp', M(ROOTS[c]), t, 1.0, 70 + 30 * min(b, 1))
        for h in range(2):
            idx = [0, 2, 1, 2, 0, 2, 1, 2][((k - k0) % 4) * 2 + h]
            note('piano', ms[idx] + 24, t + h * BEAT / 2, BEAT * 0.9, 42 + 14 * min(b, 1))
        if b > 0.45 and (k - k0) % 2 == 0: note('drums', 35, t, 0.2, 48 + 28 * min(b, 1))

def sigh(t0, t1, root='D2', chord_=DM, vel=42):
    """钢琴叹息：长音铺底 + 动机"""
    chord('strings', chord_, t0, t1 - t0, vel); note('bass', M(root) - 12, t0, t1 - t0 + 0.5, 50)

def golden(key, root='D', big=0.7):
    """金句落点：抽空一拍后，定音鼓 + 低音 + 钢琴低八度"""
    stab(CUE[key], root, big)

# ---------------------------------------------------------------- 序章 · 雪球热帖
t_ten = S['tencent']
sigh(0.0, t_ten); ramp('strings', 0, t_ten, 40, 70)
motif('piano', 0.4, MOTIF_MIN, 54)
for k in range(int(t_ten / BEAT)): note('drums', 35, k * BEAT, 0.2, 46 if k % 2 == 0 else 30)
arp_bed(t_ten, S['unwilling'] - 0.1, ['DM', 'BB', 'F', 'C'])
stab(CUE['L04'], 'D', 0.95)
note('piano', M('D3'), S['unwilling'], 2.5, 62); chord('strings', Ms('D3', 'A3'), S['unwilling'], S['catl'] - S['unwilling'], 45)
arp_bed(S['catl'], S['wall'] - 0.1, ['DM', 'BB', 'F', 'C', 'GM', 'BB', 'C', 'A'])
motif('slow', S['ali'], MOTIF_MIN, 54, 12, 1.1); ramp('slow', S['ali'], S['ali'] + 6, 60, 95)
motif('slow', S['zp'], MOTIF_MIN, 58, 12, 1.1); motif('slow', S['nv'], MOTIF_MIN, 62, 12, 1.1)
for key, root, big in (('L07', 'A#', 0.85), ('L08', 'D', 0.9), ('L09', 'D', 0.95), ('L13', 'D', 1.05)): stab(CUE[key], root, big)
# 墙：琶音退去，只剩心跳和一根越来越高的弦
tw, tt = S['wall'], S['title']
note('slow', M('A4'), tw, tt - tw - BEAT, 48); ramp('slow', tw, tt - BEAT, 48, 105)
for k in range(int(round(tw / BEAT)), int(round((tt - BEAT) / BEAT))):
    u = (k * BEAT - tw) / max(tt - tw, 1); note('drums', 35, k * BEAT, 0.2, 50 + 40 * u)
    if u > 0.5: note('drums', 35, k * BEAT + BEAT / 2, 0.2, 40 + 40 * u)
chord('choir', Ms('D3', 'A3', 'D4'), tw + 2, tt - tw - 2 - BEAT, 50); ramp('choir', tw + 2, tt - BEAT, 40, 105)
# 片名卡：全奏
chord('horn', Ms('D3', 'F3', 'A3', 'D4'), tt, 4.5, 105); chord('strings', Ms('D2', 'A2', 'D3', 'F3', 'A3', 'D4'), tt, 4.5, 112)
chord('choir', Ms('D3', 'F3', 'A3', 'D4'), tt, 4.5, 100); chord('bass', Ms('D1', 'D2'), tt, 4.5, 120)
note('timp', M('D2'), tt, 2.0, 127); note('taiko', M('C2'), tt, 1.5, 120)
for k in range(10): note('timp', M('A1'), tt - 1.2 + k * 0.11, 0.1, 40 + k * 6)
chord('piano', Ms('D1', 'D2', 'D3'), tt, 4.5, 110)

def chapter_hit(t, ch=DM, root='D', big=1.0):
    chord('strings', [m - 12 for m in ch] + ch + [m + 12 for m in ch], t, BAR * 1.3, 100 * big)
    chord('choir', ch, t, BAR * 1.2, 85 * big); chord('bass', [M(root + '1'), M(root + '2')], t, BAR * 1.2, 110 * big)
    note('timp', M(root + '2'), t, 1.6, 115 * big); note('taiko', M('C2'), t, 1.2, 100 * big)
    if big > 0.9: chord('horn', [m for m in ch], t, BAR, 90 * big)

# ---------------------------------------------------------------- 问题一 · 价格与价值
chapter_hit(S['q1_card'], GM_, 'G', 0.9)
pulse(S['q1'], S['tenyear'] - 0.1, ['DM', 'GM', 'BB', 'A'], 58, True)
motif('piano', S['scale'], MOTIF_MIN, 52, 12); motif('slow', S['twoscales'], MOTIF_MIN[:5], 56, 12)
golden('L24', 'D', 0.8)
# ---------------------------------------------------------------- 问题一 · 护城河与能力圈（降 B 大调的反思色彩）
broken(S['tenyear'], S['ibm'] - 0.1, ['GM', 'EB', 'BB', 'F'], 48, MOTIF_MIN, 'cello')
golden('L34', 'G', 0.65)
broken(S['ibm'], S['baskets'] - 0.1, ['DM', 'BB', 'GM', 'A'], 42)                 # IBM：收窄
broken(S['baskets'], S['story'] - 0.1, ['BB', 'F', 'GM', 'EB'], 46)
for i, ln in enumerate(('L39', 'L40', 'L42')): note('harp', M(['D5', 'F5', 'A5'][i]), L0(ln) + 0.3, 2.0, 74)
# ---------------------------------------------------------------- 问题一 · 时代故事 → 周期 → 预期
arp_bed(S['story'], S['capital'] - 0.1, ['BB', 'F', 'GM', 'EB'], 50)               # 壮阔
motif('slow', S['story'], MOTIF_MAJ, 60, 12, 1.1); motif('horn', S['cars'], MOTIF_MAJ[:5], 70, -12)
for k in range(int(round(S['story'] / BEAT)), int(round(S['capital'] / BEAT)), 4): note('taiko', M('C2'), k * BEAT, 1.0, 62)
pulse(S['capital'], S['stair'] - 0.1, ['DM', 'BB', 'GM', 'A'], 62, True, 0)        # 转暗：资本涌入、周期
golden('L54', 'D', 0.9)
broken(S['stair'], S['expect'] - 0.1, ['F', 'C', 'DM', 'BB'], 48)                  # 台阶：短暂的光
pulse(S['expect'], S['post2'] - 0.1, ['DM', 'GM', 'BB', 'A'], 60, True, 45)
golden('L60', 'D', 0.95)
# ---------------------------------------------------------------- 铁锤
t_p2, t_h, t_v, t_inv, t_q2c = S['post2'], S['hammer'], S['verdict'], S['inv'], S['q2_card']
chord('strings', Ms('D3', 'F3', 'A3'), t_p2, t_h - t_p2, 45); motif('piano', t_p2 + 0.3, MOTIF_MIN[:5], 48)
OST = ['D2', 'D2', 'D2', 'D2', 'A#1', 'A#1', 'A1', 'A1']
k0, k1 = int(round(t_h / BEAT)), int(round((CUE['L63c'] + BAR) / BEAT))
for k in range(k0, k1):
    for h in range(2):
        tk = k * BEAT + h * BEAT / 2
        if silence_mask(tk, BEAT) and tk >= CUE['L63a'] - 1: continue
        p = M(OST[((k - k0) * 2 + h) % 8])
        note('bass', p, tk, BEAT * 0.4, 88 if h == 0 else 70); note('cello', p + 12, tk, BEAT * 0.4, 72 if h == 0 else 58)
    if (k - k0) % 4 == 0: note('timp', M('D2'), k * BEAT, 1.0, 70)
chord('choir', Ms('D3', 'F3', 'A3'), t_h, CUE['L63a'] - t_h, 55); ramp('choir', t_h, CUE['L63a'], 50, 100)
for i, key in enumerate(('L63a', 'L63b', 'L63c')):
    t = CUE[key]
    note('taiko', M('C2'), t, 1.5, 120); note('taiko', M('G1'), t, 1.5, 110); note('timp', M('D2'), t, 2.0, 120)
    chord('bass', Ms('D1', 'D2'), t, 1.6, 120); chord('horn', Ms('D3', 'A3'), t, 0.9, 85 + 10 * i)
    chord('strings', Ms('D2', 'D3', 'A3', 'D4'), t, 1.2, 100 + 8 * i)
# 「这些判断，都有自己的道理。但……」：全部抽空，只剩钢琴单音
for j, ln in enumerate(('L64', 'L65', 'L66')): note('piano', M(['A3', 'F3', 'D3'][j]), L0(ln), 3.0, 60)
note('cello', M('D2'), t_v, t_inv - t_v, 42)
chord('strings', Ms('A2', 'E3', 'A3'), t_inv, t_q2c - t_inv - 0.3, 50); ramp('strings', t_inv, t_q2c - 0.5, 45, 85)
# ---------------------------------------------------------------- 问题二 · 钢琴独奏 → 慢慢回暖到 F 大调
chord('strings', Ms('F2', 'C3', 'F3', 'A3'), S['q2_card'], BAR * 1.3, 70); note('timp', M('F2'), S['q2_card'], 1.5, 85)
chord('choir', Ms('F3', 'A3', 'C4'), S['q2_card'], BAR * 1.2, 60)
motif('piano', S['q2'], MOTIF_MIN, 50); note('cello', M('D2'), S['q2'], S['drops'] - S['q2'], 40)
broken(S['noise'], S['band'] - 0.1, ['DM', 'BB', 'GM', 'A'], 42)
broken(S['band'], S['line'] - 0.1, ['BB', 'F', 'C', 'DM'], 48, MOTIF_MAJ, 'slow')
broken(S['line'], S['q3_card'] - 0.1, ['BB', 'F', 'C', 'FM'], 52)
golden('L84', 'F', 0.75)
# ---------------------------------------------------------------- 问题三 · F 大调全奏
chapter_hit(S['q3_card'], Ms('F3', 'A3', 'C4'), 'F', 1.0)
prog4 = ['BB', 'FM', 'C', 'DM']
anthem(S['q3'], S['finale'] - 0.1, prog4, 0.2, 0.9)
anthem(S['finale'], S['epilogue'] - 0.1, prog4, 1.0, 1.25)
motif('horn', S['finale'], MOTIF_MAJ, 92, -12, 1.0); motif('slow', S['finale'], MOTIF_MAJ, 78, 12, 1.0)
note('timp', M('F2'), S['finale'], 1.5, 110); note('taiko', M('C2'), S['finale'], 1.2, 95)
# ---------------------------------------------------------------- 尾声 · 钢琴回到主题
t_e, t_h2, t_l, t_card = S['epilogue'], S['hardest'], S['last'], S['card']
motif('piano', t_e + 0.3, MOTIF_MAJ, 54); chord('strings', Ms('F2', 'C3', 'F3'), t_e, t_h2 - t_e, 40)
golden('L92', 'F', 0.55)
broken(t_h2, t_card - 0.1, ['BB', 'FM', 'GM', 'C'], 46, MOTIF_MAJ, 'slow')
fin = Ms('F2', 'C3', 'F3', 'A3', 'C4', 'G4')
chord('piano', fin, t_card, 6.0, 70, 0.08); chord('strings', Ms('F2', 'C3', 'F3', 'A3'), t_card, 5.5, 60)
chord('choir', Ms('F3', 'A3', 'C4'), t_card, 5.0, 50); note('timp', M('F2'), t_card, 2.0, 70)

stems = render(write_midis())

# ================================================================ 合成音效
def lp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), 'low'); return signal.lfilter(b, a, x, axis=0)
def hp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), 'high'); return signal.lfilter(b, a, x, axis=0)
def bp(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], 'band'); return signal.lfilter(b, a, x, axis=0)
fx = np.zeros((N, 2), np.float32)
def put(t, x, gain=1.0):
    i = int(t * SR)
    if x.ndim == 1: x = np.stack([x, x], 1)
    n = min(len(x), N - i)
    if n > 0 and i >= 0: fx[i:i + n] += x[:n] * gain

def sub_boom(strength=1.0, f0=62, f1=30, dec=1.6):
    n = int(3.5 * SR); t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 5)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / dec) * np.minimum(t / 0.003, 1)
    nz = lp(rng.standard_normal(n), 160) * np.exp(-t * 14) * 0.8
    return np.tanh((x + nz) * 1.2) * 0.5 * strength

def anvil(v=0.3):
    """锤子落下的金属感：几个非谐波分量，低通到 3.5kHz 内，不刺耳"""
    n = int(1.8 * SR); t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, a, d in
            [(212, 1.0, 3.2), (537, 0.6, 4.5), (893, 0.35, 6.0), (1310, 0.2, 8.0)])
    x += lp(rng.standard_normal(n), 2500) * np.exp(-t * 60) * 0.6
    return lp(x, 3500) * v

def riser(dur, v=0.2, f_lo=120, f_hi=1500):
    n = int(dur * SR); t = np.arange(n) / SR; u = t / dur
    nz = rng.standard_normal(n); out = np.zeros(n); seg = int(0.05 * SR)
    for i in range(0, n, seg):
        c = f_lo * (f_hi / f_lo) ** (u[i] ** 1.6)
        out[i:i + seg] = bp(nz[max(0, i - 2000):i + seg], c * 0.7, c * 1.3, 1)[-len(out[i:i + seg]):]
    tone = np.sin(2 * np.pi * np.cumsum(55 * 2 ** (u * 1.0)) / SR) * 0.5
    return (out * 0.8 + tone) * u ** 2.2 * v

def reverse_swell(dur=1.2, v=0.25):
    """锤前吸气：反向混响式的渐强，落点前骤停"""
    n = int(dur * SR); t = np.arange(n) / SR; u = t / dur
    x = lp(rng.standard_normal(n), 700) * u ** 3
    x += np.sin(2 * np.pi * 73.4 * t) * u ** 2 * 0.6
    return x * v

def whoosh(dur=1.0, v=0.12):
    n = int(dur * SR); u = np.arange(n) / n
    return lp(rng.standard_normal(n), 900) * np.sin(np.pi * u) ** 2 * v

def hit(t, s=1.0, **kw):
    put(t, sub_boom(s, **kw)); HITS.append((round(t, 3), s))

def tape_rewind(dur=1.1, v=0.22):
    """倒带：磁带倒卷的「嗖嗖」声——下滑的音高 + 低通颤动噪声"""
    n = int(dur * SR); t = np.arange(n) / SR; u = t / dur
    f = 900 * (1 - u) ** 1.5 + 120
    tone = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.04 * np.sin(2 * np.pi * 23 * t))) / SR) * 0.35
    nz = bp(rng.standard_normal(n), 200, 1800, 2) * (0.5 + 0.5 * np.sin(2 * np.pi * 31 * t))
    env = np.sin(np.pi * np.clip(u * 1.15, 0, 1)) ** 0.7
    return lp(tone + nz * 0.6, 2200) * env * v

for key, s_ in (('L04', 0.9), ('L07', 0.8), ('L08', 0.85), ('L09', 0.9)):
    put(CUE[key] - 0.9, whoosh(0.9, 0.08)); hit(CUE[key], s_, f0=55, f1=28, dec=1.9)
put(CUE['L13'] - 1.6, riser(1.6, 0.10, 90, 900)); hit(CUE['L13'], 1.0, f0=58, f1=26, dec=2.2)
put(S['title'] - 2.2, riser(2.2, 0.16, 90, 1400)); hit(S['title'], 1.4, f0=70, f1=26, dec=2.6)
for key, s_ in (('q1_card', 1.05), ('q2_card', 0.6), ('q3_card', 1.15)):
    put(S[key] - 1.6, riser(1.6, 0.10 + 0.04 * (s_ > 1), 100, 1200)); hit(S[key], s_, f0=62, f1=28, dec=2.4)
for key in ('L24', 'L34', 'L54', 'L60', 'L84', 'L92'):
    put(CUE[key] - 1.0, reverse_swell(1.0, 0.10)); hit(CUE[key], 0.75)
for key in ('anchor', 'scale', 'moat', 'ibm', 'baskets', 'cars', 'lowpe', 'expect', 'noise', 'band', 'branches', 'principles', 'rebuild'):
    put(S[key] - 0.8, whoosh(0.8, 0.07))
for i, key in enumerate(('L63a', 'L63b', 'L63c')):
    put(CUE[key] - 1.2, reverse_swell(1.2, 0.18 + 0.04 * i)); put(CUE[key], anvil(0.22 + 0.05 * i))
    hit(CUE[key], 1.15 + 0.1 * i, f0=66, f1=26, dec=2.2)
hit(LN['L65']['t0'], 0.55, f0=48, f1=24, dec=3.0)
hit(S['finale'], 0.9, f0=55, f1=28, dec=2.6)
hit(S['card'], 0.7, f0=55, f1=30, dec=2.8)

# ================================================================ 混音
def ir(dur, dec, fc, seed):
    r = np.random.default_rng(seed); n = int(dur * SR); t = np.arange(n) / SR
    x = r.standard_normal(n) * np.exp(-t / dec) * np.minimum(t / 0.012, 1)
    return lp(x, fc) / np.sqrt(np.sum(x ** 2))
IRL, IRR = ir(4.0, 0.9, 5000, 1), ir(4.0, 0.9, 5000, 2)
def verb(x, wet):
    m = x.mean(1)
    return np.stack([signal.fftconvolve(m, IRL)[:N], signal.fftconvolve(m, IRR)[:N]], 1) * wet

def norm(x, rms=0.1):
    r = np.sqrt(np.mean(x ** 2)) + 1e-9; return x * (rms / r)

G = dict(piano=(0.95, 0.55), str=(0.9, 0.45), low=(0.85, 0.15), brass=(0.55, 0.4), perc=(0.85, 0.3))
mix = np.zeros((N, 2), np.float32)
for k, (g, wet) in G.items():
    if k not in stems: continue
    x = norm(stems[k]) * g
    mix += x + verb(x, wet)
mix += fx * 1.0 + verb(fx, 0.35)
mix = hp(mix, 30, 2)
mix = lp(mix, 10000, 2)                    # 去刺耳高频

# 旁白闪避移到 src/mix.py 的最终混音里做（在压缩之后，才不会被压缩器抹平）
mix = mix[:int(T * SR)]
f = int(3.0 * SR); mix[-f:] *= np.linspace(1, 0, f)[:, None] ** 1.5
mix /= np.sqrt(np.mean(mix ** 2)) / 0.09
# 母带压缩：RMS 包络（300ms），阈值以上 3:1，收住标题全奏/锤击与铺底之间过大的落差
e = np.sqrt(signal.lfilter([1 - np.exp(-1 / (0.3 * SR))], [1, -np.exp(-1 / (0.3 * SR))], (mix ** 2).mean(1)) + 1e-9)
thr = 0.09 * 10 ** (3 / 20)
gain = np.where(e > thr, (e / thr) ** (1 / 3 - 1), 1.0)
mix *= gain[:, None].astype(np.float32)
mix /= np.sqrt(np.mean(mix ** 2)) / 0.09
mix = np.tanh(mix / 0.8) * 0.8
sf.write(f'{W}/music.wav', mix.astype(np.float32), SR, subtype='FLOAT')
json.dump(sorted(HITS), open(f'{W}/hits.json', 'w'))
print('music ok', len(mix) / SR, 'hits', len(HITS), 'stems', list(stems))
