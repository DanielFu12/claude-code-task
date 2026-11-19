"""原创配乐（真实乐器音色）：MIDI 编曲 -> fluidsynth + FluidR3_GM 分轨渲染 -> 叠加合成重击/上升音 -> 混音。
所有落点读自 work/timeline.json（cues / sections），与画面共用。
情绪弧线：
  第一幕 D 小调钢琴叹息动机 + 琶音，每个「如今……」用定音鼓 + 低音弦乐重音砸下；
  追问：心跳加速、弦乐颤音渐强 → 抽空 → 标题全奏；
  第二幕：低音提琴 8 分音符暗涌；三记锤击 = 太鼓 + 定音鼓 + 铁砧 + 次低频，严格一小节一锤，锤前一拍抽空；
  第三幕：Dm-Gm-B♭-A 推进，每个真相落在重拍；
  第四幕：转 F 大调，动机变成大调，弦乐 + 圆号 + 合唱推到全片最高点，最后只剩钢琴。"""
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

STOP = [CUE['T2'], CUE['A2'], CUE['Z2'], CUE['N3'], CUE['M3'], CUE['M4'], CUE['M5'], CUE['k3_punch'], CUE['k6_26'], CUE['q_ask']]

# ---------------------------------------------------------------- 第一幕
t_c, t_piv = S['cases'], S['pivot']
chord('strings', DM, 0.0, t_c, 42); ramp('strings', 0, CUE['H1'], 40, 105); ramp('strings', CUE['H1'] + 0.1, t_c, 90, 60)
note('bass', M('D1'), 0.0, t_c + 1, 55)
motif('piano', 0.75, MOTIF_MIN[:6], 52)
for k in range(int(t_c / BEAT)):
    note('drums', 35, k * BEAT, 0.2, 52 if k % 2 == 0 else 34)          # 心跳
stab(CUE['H1'], 'D', 0.9)

prog = ['DM', 'BB', 'F', 'C']
q0 = LN['N2']['t0']
k0, k1 = int(round(t_c / BEAT)), int(round(q0 / BEAT))
for k in range(k0, k1):
    t = k * BEAT; bar = (k - k0) // 4; c = prog[bar % 4]; ms = CHD[c]
    if (k - k0) % 4 == 0:
        note('cello', M(ROOTS[c]) + 12, t, BAR * 0.95, 62)
        if not silence_mask(t + BAR * 0.9, BEAT): chord('strings', [m + 12 for m in ms], t, BAR * 0.98, 46)
    for h in range(2):
        th = t + h * BEAT / 2
        if silence_mask(th, BEAT): continue
        idx = [0, 1, 2, 1, 0, 2, 1, 2][((k - k0) % 4) * 2 + h]
        note('piano', ms[idx] + 12, th, BEAT * 0.9, 46 + 8 * (h == 0))
    if (k - k0) % 2 == 0 and not silence_mask(t, BEAT): note('drums', 35, t, 0.2, 58)
# 阿里之后，高音弦乐唱动机，情绪抬升
motif('slow', LN['A1']['t0'], MOTIF_MIN, 54, 12, 1.1); ramp('slow', LN['A1']['t0'], LN['A1']['t0'] + 6, 60, 95)
motif('slow', LN['Z1']['t0'], MOTIF_MIN, 58, 12, 1.1)
for key, root, big in (('T2', 'D', 0.95), ('A2', 'A#', 0.9), ('Z2', 'D', 0.95)):
    stab(CUE[key], root, big)
# 「这一次，总该对了吧？」：只剩心跳和一根高音弦
note('slow', M('A4'), q0, CUE['N3'] - q0, 50); ramp('slow', q0, CUE['N3'], 50, 100)
for k in range(int(round(q0 / BEAT)), int(round(CUE['N3'] / BEAT))):
    note('drums', 35, k * BEAT, 0.2, 60)
stab(CUE['N3'], 'D', 1.1)
chord('strings', Ms('D2', 'A2', 'D3'), CUE['N3'], t_piv - CUE['N3'] + 0.5, 50)

# ---------------------------------------------------------------- 追问 → 标题
t_ti = S['title']
kq = int(round(CUE['q_ask'] / BEAT))
for k in range(int(round(t_piv / BEAT)), kq):
    u = (k * BEAT - t_piv) / max(CUE['q_ask'] - t_piv, 1)
    note('drums', 35, k * BEAT, 0.2, 55 + 40 * u)
    if u > 0.45: note('drums', 35, k * BEAT + BEAT / 2, 0.2, 40 + 40 * u)
    for s16 in range(4):                                                 # 弦乐颤音渐强
        note('strings', M('D3'), k * BEAT + s16 * BEAT / 4, BEAT / 4, 40 + 60 * u)
        note('strings', M('A3'), k * BEAT + s16 * BEAT / 4, BEAT / 4, 36 + 60 * u)
chord('choir', Ms('D3', 'A3', 'D4'), t_piv + 2, CUE['q_ask'] - t_piv - 2, 50); ramp('choir', t_piv + 2, CUE['q_ask'], 40, 110)
for k in range(kq + 1, int(round(t_ti / BEAT))):
    note('drums', 35, k * BEAT, 0.2, 70)
# 标题全奏
tt = t_ti
chord('horn', Ms('D3', 'F3', 'A3', 'D4'), tt, 4.5, 105); chord('strings', Ms('D2', 'A2', 'D3', 'F3', 'A3', 'D4'), tt, 5.0, 112)
chord('choir', Ms('D3', 'F3', 'A3', 'D4'), tt, 5.0, 100); chord('bass', Ms('D1', 'D2'), tt, 5.0, 120)
note('timp', M('D2'), tt, 2.0, 127); note('taiko', M('C2'), tt, 1.5, 120)
for k in range(10): note('timp', M('A1'), tt - 1.2 + k * 0.11, 0.1, 40 + k * 6)    # 定音鼓滚奏推进
chord('piano', Ms('D1', 'D2', 'D3'), tt, 5.0, 110)
ramp('strings', tt + 0.5, S['hammer'], 110, 70)

# ---------------------------------------------------------------- 第二幕：铁锤人
t_h, t_s, t_a, t_two = S['hammer'], S['strikes'], S['ask'], S['two']
OST = ['D2', 'D2', 'D2', 'D2', 'A#1', 'A#1', 'A1', 'A1']
k0, k1 = int(round(t_h / BEAT)), int(round((CUE['M5'] + BEAT) / BEAT))
for k in range(k0, k1):
    for h in range(2):
        th = k * BEAT + h * BEAT / 2
        if silence_mask(th, BEAT) and th >= t_s - 0.01: continue
        p = M(OST[((k - k0) * 2 + h) % 8])
        note('bass', p, th, BEAT * 0.4, 88 if h == 0 else 70); note('cello', p + 12, th, BEAT * 0.4, 72 if h == 0 else 58)
    if (k - k0) % 4 == 0: note('timp', M('D2'), k * BEAT, 1.0, 70)
chord('choir', Ms('D3', 'F3', 'A3'), t_h, t_s - t_h, 55); ramp('choir', t_h, t_s, 50, 95)
chord('strings', Ms('D3', 'A3'), t_h, t_s - t_h + 0.5, 50)
for k, tw in enumerate(CUE['m2_words']):                                 # 五个公式词，一词一音
    note('piano', Ms('D5', 'F5', 'A5', 'C6', 'D6')[k], tw, 0.6, 72); note('harp', Ms('D4', 'F4', 'A4', 'C5', 'D5')[k], tw, 0.8, 70)
for i, key in enumerate(('M3', 'M4', 'M5')):                             # 三锤
    t = CUE[key]; big = 0.9 + 0.1 * i
    note('taiko', M('C2'), t, 1.5, 120); note('taiko', M('G1'), t, 1.5, 110)
    note('timp', M('D2'), t, 2.0, 120); chord('bass', Ms('D1', 'D2'), t, 1.6, 120)
    chord('horn', Ms('D3', 'A3'), t, 0.9, 85 + 10 * i); chord('strings', Ms('D2', 'D3', 'A3', 'D4'), t, 1.2, 100 + 8 * i)
# 「每一锤，都像价值投资。可你从没问过……」：抽空
note('cello', M('D2'), t_a, t_two - t_a, 55); note('slow', M('D5'), CUE['m6_ask'], t_two - CUE['m6_ask'], 40)
for k, (n_, b) in enumerate([('A4', 0), ('F4', 1.5), ('E4', 3), ('D4', 4.5)]):
    note('piano', M(n_), t_a + 0.3 + b * BEAT, 1.4, 48)
# 「能力圈，和反过来想」：暖色转调
chord('strings', Ms('A#2', 'F3', 'A#3', 'D4'), t_two, CUE['m7_two'] - t_two, 55); ramp('strings', t_two, CUE['m7_two'], 50, 100)
chord('strings', Ms('F2', 'C3', 'F3', 'A3', 'C4'), CUE['m7_two'], S['tx'] - CUE['m7_two'] + 0.3, 95)
chord('choir', Ms('F3', 'A3', 'C4'), CUE['m7_two'], S['tx'] - CUE['m7_two'], 85); chord('horn', Ms('F3', 'A3'), CUE['m7_two'], 3.0, 70)
note('harp', M('F4'), CUE['m7_two'], 2, 75); note('harp', M('A4'), CUE['m7_two'] + 0.12, 2, 70); note('harp', M('C5'), CUE['m7_two'] + 0.24, 2, 68)
ramp('strings', CUE['m7_two'] + 1, S['tx'], 100, 55)

# ---------------------------------------------------------------- 第三幕：拔钉子
t_cure = S['cure']
prog3 = ['DM', 'GM', 'BB', 'A']
k0, k1 = int(round(S['tx'] / BEAT)), int(round((t_cure - BEAT) / BEAT))
for k in range(k0, k1):
    t = k * BEAT; bar = (k - k0) // 4; c = prog3[bar % 4]; ms = CHD[c]
    if (k - k0) % 4 == 0 and not silence_mask(t + BAR * 0.9, BEAT):
        chord('strings', [m + 12 for m in ms], t, BAR * 0.98, 55); note('bass', M(ROOTS[c]), t, BAR * 0.95, 70)
    for h in range(2):
        th = t + h * BEAT / 2
        if silence_mask(th, BEAT): continue
        note('cello', M(ROOTS[c]) + 12 + (12 if h else 0), th, BEAT * 0.4, 62)
        idx = [0, 2, 1, 2, 0, 2, 1, 2][((k - k0) % 4) * 2 + h]
        note('piano', ms[idx] + 12, th, BEAT * 0.8, 44)
    if (k - k0) % 2 == 0 and not silence_mask(t, BEAT): note('drums', 35, t, 0.2, 62)
for key in ('tx', 'ali', 'zp', 'nv'):                                    # 每颗钉子：动机 + 重音
    t = S[key]; motif('slow', t, MOTIF_MIN[:5], 56, 12, 1.0)
    note('timp', M('D2'), t, 1.2, 95); note('taiko', M('C2'), t, 1.0, 80)
for key, big in (('k3_punch', 1.0), ('k4_buyback', 0.75), ('k5_q', 0.8), ('k6_26', 1.0)):
    stab(CUE[key], 'D', big)
# 市盈率从 40 多倍跌到 12 倍：弦乐下行
for k, n_ in enumerate(['D5', 'C5', 'A#4', 'A4', 'G4', 'F4', 'E4', 'D4']):
    note('slow', M(n_), CUE['k2_pe'] + k * BEAT / 2, BEAT / 2 * 1.05, 70)

# ---------------------------------------------------------------- 第四幕：解药（F 大调）
t_rep, t_ring, t_fin, t_out, t_card = S['report'], S['ring'], S['finale'], S['outro'], S['card']
chord('slow', Ms('F3', 'C4', 'F4'), t_cure, t_rep - t_cure + 0.5, 45)
motif('piano', t_cure + 0.2, MOTIF_MAJ, 58)
prog4 = [Ms('A#2', 'D3', 'F3'), Ms('F2', 'A2', 'C3'), Ms('C3', 'E3', 'G3'), Ms('D3', 'F3', 'A3')]
roots4 = ['A#1', 'F1', 'C2', 'D2']
k0, k1 = int(round(t_rep / BEAT)), int(round(t_out / BEAT))
for k in range(k0, k1):
    t = k * BEAT; bar = (k - k0) // 4; ms = prog4[bar % 4]
    build = (t - t_rep) / (t_fin - t_rep)
    if (k - k0) % 4 == 0:
        chord('strings', [m + 12 for m in ms] + [ms[0]], t, BAR * 0.98, 50 + 35 * min(build, 1.2))
        note('bass', M(roots4[bar % 4]), t, BAR * 0.95, 65 + 30 * min(build, 1.0))
        if t >= t_ring: chord('choir', [m + 12 for m in ms], t, BAR * 0.98, 50 + 40 * min(build, 1.2))
    for h in range(2):
        idx = [0, 2, 1, 2, 0, 2, 1, 2][((k - k0) % 4) * 2 + h]
        note('piano', ms[idx] + 24, t + h * BEAT / 2, BEAT * 0.9, 46 + 10 * min(build, 1))
    if t >= t_ring and (k - k0) % 2 == 0: note('drums', 35, t, 0.2, 55 + 25 * min(build, 1))
    if t >= t_fin and (k - k0) % 4 == 0: note('timp', M(roots4[bar % 4]), t, 1.0, 90)
motif('slow', t_ring, MOTIF_MAJ, 60, 0, 1.1)
# 终曲：圆号唱大调动机，全片最高点
motif('horn', t_fin, MOTIF_MAJ, 92, -12, 1.0); motif('slow', t_fin, MOTIF_MAJ, 75, 12, 1.0)
for i, key in enumerate(('report', 'ring', 'finale')): note('timp', M('F2'), S[key], 1.5, 80 + 12 * i)
note('timp', M('A#1'), CUE['e1_turn'], 1.5, 110); note('taiko', M('C2'), CUE['e1_turn'], 1.2, 95)
# 尾声：只剩钢琴
motif('piano', t_out, MOTIF_MAJ[:6], 55)
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

hit(CUE['H1'], 0.8)
for key, s_ in (('T2', 0.9), ('A2', 0.85), ('Z2', 0.9)):
    put(CUE[key] - 0.9, whoosh(0.9, 0.08)); hit(CUE[key], s_, f0=55, f1=28, dec=1.9)
put(CUE['N3'] - 1.6, riser(1.6, 0.10, 90, 900)); hit(CUE['N3'], 1.05, f0=58, f1=26, dec=2.2)
hit(S['cases'], 0.5)
put(S['title'] - 2.5, riser(2.5, 0.16, 90, 1400)); hit(S['title'], 1.4, f0=70, f1=26, dec=2.6)
for i, key in enumerate(('M3', 'M4', 'M5')):
    put(CUE[key] - 1.2, reverse_swell(1.2, 0.18 + 0.04 * i)); put(CUE[key], anvil(0.22 + 0.05 * i))
    hit(CUE[key], 1.15 + 0.1 * i, f0=66, f1=26, dec=2.2)
hit(CUE['m6_hit'], 0.7, f0=50, f1=24, dec=2.8)
hit(CUE['m7_two'], 0.55)
for key in ('tx', 'ali', 'zp', 'nv'):
    put(S[key] - 1.0, whoosh(1.0, 0.10)); hit(S[key], 0.75)
for key, s_ in (('k3_punch', 1.0), ('k4_buyback', 0.6), ('k5_q', 0.7), ('k6_26', 1.0)):
    put(CUE[key] - 1.1, reverse_swell(1.1, 0.12)); hit(CUE[key], s_)
hit(S['cure'], 0.6, f0=58, f1=32, dec=2.2)
hit(CUE['e1_turn'], 0.85, f0=55, f1=28, dec=2.6)
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

# 旁白闪避：人声时音乐压低约 7dB
v, _ = sf.read(f'{W}/voice.wav', dtype='float32')
env = np.abs(v); env = np.pad(env, (0, max(0, N - len(env))))[:N]
k = int(0.02 * SR); env = (np.convolve(env, np.ones(k) / k, 'same') > 0.01).astype(np.float32)
a_att, a_rel = np.exp(-1 / (0.08 * SR)), np.exp(-1 / (0.5 * SR))
g = np.maximum(signal.lfilter([1 - a_rel], [1, -a_rel], env), signal.lfilter([1 - a_att], [1, -a_att], env))
mix *= (1 - 0.55 * np.clip(g * 1.4, 0, 1))[:, None]
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
