"""原创配乐：按旁白时间线写 MIDI → FluidSynth(FluidR3 GM) 渲染 → 叠加合成低频冲击/气声 → 卷积混响。
80 BPM（每拍 0.75 秒），D 小调为主；飞轮段和结尾转 D 大调。
重拍（片名、"失血"、"效率"、"先拥有它的规模"、"值不值"、片尾 logo）直接取旁白里某个字的发声时刻。
没有镲片、没有高频扫频：转场只用低频轰鸣、弦乐渐强和低通过的气声。
python3 src/music.py WORK → WORK/music.wav（48k 立体声）、WORK/hits.json（给画面用的重拍时刻）
"""
import os, sys, json, subprocess
import numpy as np, soundfile as sf
import pretty_midi as pm
from scipy.signal import butter, sosfilt, fftconvolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import TL, BEAT, BAR

WORK = sys.argv[1]; tl = TL(WORK); TOTAL = tl.total
SR = 48000; SF2 = '/usr/share/sounds/sf2/FluidR3_GM.sf2'
mid = pm.PrettyMIDI(initial_tempo=80)
INS = {}


def ins(name, prog, drum=False):
    if name not in INS:
        INS[name] = pm.Instrument(program=prog, is_drum=drum, name=name); mid.instruments.append(INS[name])
    return INS[name]


def note(name, p, t0, t1, v):
    if t1 <= t0 or v <= 0: return
    ins(name, PROG[name]).notes.append(pm.Note(int(np.clip(v, 1, 127)), int(p), float(t0), float(t1)))


def cc(name, t, val, num=11):
    ins(name, PROG[name]).control_changes.append(pm.ControlChange(num, int(np.clip(val, 0, 127)), float(t)))


def ramp(name, t0, t1, v0, v1, n=24):
    for i in range(n + 1): cc(name, t0 + (t1 - t0) * i / n, v0 + (v1 - v0) * i / n)


PROG = dict(piano=0, celesta=8, strings=48, slow=49, cello=42, bass=43, pizz=45, timp=47, choir=52, horn=60,
            brass=61, pad=89, taiko=116, harp=46)
NOTE = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'Ab': 8, 'A': 9, 'Bb': 10, 'B': 11}
QUAL = {'': (0, 4, 7), 'm': (0, 3, 7), 'sus2': (0, 2, 7), 'sus4': (0, 5, 7), 'add9': (0, 4, 7, 14), 'madd9': (0, 3, 7, 14),
        'maj7': (0, 4, 7, 11), 'm7': (0, 3, 7, 10)}


def parse(c):
    r = c[:2] if len(c) > 1 and c[1] in '#b' else c[:1]
    return NOTE[r], QUAL[c[len(r):]]


def voicing(c, lo=50, n=4):
    r, iv = parse(c); pcs = sorted({(r + x) % 12 for x in iv}); out = []; p = lo
    while len(out) < n:
        if p % 12 in pcs: out.append(p)
        p += 1
    return out


def root(c, oct_=36):
    r, _ = parse(c); return oct_ + r


def grid(t): return round(t / BEAT) * BEAT
def bars(t0, t1, prog):
    """把和弦进行按小节铺到 [t0,t1)，返回 [(chord, s, e)]"""
    out = []; t = t0; i = 0
    while t < t1 - 1e-6:
        e = min(t + BAR, t1); out.append((prog[i % len(prog)], t, e)); t += BAR; i += 1
    return out


def pad(t0, t1, prog, v=46, lo=50, name='strings', bassname='bass', bv=None):
    for c, s, e in bars(t0, t1, prog):
        for p in voicing(c, lo): note(name, p, s, e + 0.08, v)
        if bassname: note(bassname, root(c, 38), s, e + 0.05, bv or v + 4)


def piano_motif(t0, tonic=62, v=58, major=False, step=BEAT):
    seq = [0, 7, 3, 2] if not major else [0, 7, 4, 2]
    for i, d in enumerate(seq):
        note('piano', tonic + d, t0 + i * step, t0 + i * step + step * (2.4 if i == 3 else 1.4), v - i * 3)


def arp(t0, t1, prog, v=44, lo=62, step=BEAT / 2, name='piano', pat=(0, 1, 2, 1, 3, 2, 1, 2)):
    for c, s, e in bars(t0, t1, prog):
        ps = voicing(c, lo, 4); t = s; k = 0
        while t < e - 1e-6:
            note(name, ps[pat[k % len(pat)] % 4], t, t + step * 1.6, v + (6 if k % 4 == 0 else 0)); t += step; k += 1


def ostinato(t0, t1, prog, v=50, step=BEAT / 2, name='cello', oct_=38, accent=4):
    for c, s, e in bars(t0, t1, prog):
        t = s; k = 0
        while t < e - 1e-6:
            note(name, root(c, oct_) + (12 if k % 8 == 6 else 0), t, t + step * 0.8, v + (10 if k % accent == 0 else 0))
            t += step; k += 1


def pulse(t0, t1, v=40, every=BEAT):
    """很轻的低鼓脉冲（GM 鼓：36 底鼓）"""
    t = t0
    while t < t1 - 1e-6:
        ins('drums', 0, True).notes.append(pm.Note(int(v), 36, float(t), float(t + 0.2))); t += every


def timp(t, p=38, v=90, roll=0.0):
    if roll > 0:
        n = int(roll / 0.07)
        for i in range(n): note('timp', p, t - roll + i * 0.07, t - roll + i * 0.07 + 0.1, 25 + 60 * i / n)
    note('timp', p, t, t + 2.5, v)


HITS = {}   # name -> time（画面用）
SUBS = []   # (t, gain, kind)

# ─────────────────────────── 时刻表 ───────────────────────────
H1 = tl.T('h1'); TITLE = tl.SE('h5') + 0.55
HITS['title'] = TITLE
B1 = grid(tl.S('b1') - BEAT); C1 = grid(tl.S('c1') - BEAT); D1 = grid(tl.S('d1') - BEAT); E1 = grid(tl.S('e1') - BEAT)
F1 = grid(tl.S('f1') - BEAT); G1 = grid(tl.S('g1') - BEAT); Q1 = grid(tl.S('q1') - BEAT); Z1 = grid(tl.S('z1') - BEAT)
END = tl.SE('z3') + 0.9; HITS['logo'] = END

# 0 冷开场：低音铺底 + 钢琴主题（D–A–F–E），讲到排队退押金时转暗
note('pad', 38, 0.0, TITLE - 0.3, 34); note('pad', 45, 0.0, TITLE - 0.3, 26)
ramp('pad', 0.0, 2.0, 30, 100)
piano_motif(H1 + 0.05, 62, 60)
note('piano', 50, H1 + 0.05, H1 + 3.0, 44)
piano_motif(tl.T('h2'), 60, 54)                         # 主题下移：寒意
note('cello', 38, tl.T('h3'), tl.SE('h4'), 52); note('cello', 45, tl.T('h3'), tl.SE('h4'), 44)
ramp('cello', tl.T('h3'), tl.SE('h4'), 50, 110)
for p in voicing('Dm', 50): note('slow', p, tl.T('h4'), TITLE, 40)
for p in voicing('Bb', 50): note('slow', p - 12 + 12, tl.WT('h4', '一个成了坟墓'), TITLE, 0)
ramp('slow', tl.T('h4'), TITLE - 0.05, 30, 120)          # 「差别到底在哪」→ 弦乐渐强到片名
note('piano', 74, tl.WT('h5', '哪'), tl.WT('h5', '哪') + 2, 50)
SUBS.append((TITLE, 1.0, 'boom')); timp(TITLE, 38, 112, roll=1.4)
for p in voicing('Dm', 38, 3) + voicing('Dm', 62, 3): note('brass', p, TITLE, TITLE + 2.6, 84)
for p in voicing('Dm', 50, 4): note('choir', p, TITLE, TITLE + 3.2, 60)
SUBS.append((TITLE - 1.6, 0.5, 'swell'))

# 1 直觉 + 2 试金石：脉动起，钢琴分解，c4「失血」重音
pr = ['Dm', 'Bb', 'F', 'C']
pad(B1, C1, pr, 40, name='strings'); arp(B1, C1, pr, 40)
ostinato(C1, tl.T('c4'), ['Dm', 'Bb', 'Gm', 'A'], 48); pad(C1, tl.T('c4'), ['Dm', 'Bb', 'Gm', 'A'], 38, name='strings', bassname=None)
pulse(C1, tl.T('c4'), 34)
arp(C1, tl.T('c4'), ['Dm', 'Bb', 'Gm', 'A'], 42, lo=64)
t_blood = tl.WT('c4', '失血'); HITS['blood'] = t_blood
timp(t_blood, 38, 96); SUBS.append((t_blood, 0.7, 'boom'))
for p in voicing('Dm', 50): note('strings', p, t_blood, D1 + 0.2, 36)
note('piano', 50, t_blood, t_blood + 3, 50)

# 3 巴菲特的用词：温暖，F 大调色彩；「成本最低」上弦乐亮起
pr = ['Bbmaj7', 'F', 'C', 'Dm'] if False else ['Bb', 'F', 'C', 'Dm']
pad(D1, E1, pr, 44, name='slow'); arp(D1, E1, pr, 36, lo=65, name='harp', step=BEAT / 2)
t_cost = tl.WT('d2', '成本最低'); HITS['lowcost'] = t_cost
for p in voicing('F', 62): note('choir', p, t_cost, E1, 48)
note('celesta', 77, t_cost, t_cost + 1.5, 60); note('celesta', 81, t_cost + 0.375, t_cost + 2, 54)

# 4 三个来源：每个「第一/第二/第三」一记太鼓；前两个小调，第三个转大调抬起来
pad(E1, tl.T('e4'), ['Dm', 'Dm', 'Bb', 'A'], 38, name='strings')
for lid, key in (('e2', '第一'), ('e3', '第二'), ('e4', '第三')):
    t = tl.WT(lid, key); HITS[lid] = t
    note('taiko', 45, t, t + 1.0, 96); SUBS.append((t, 0.45, 'boom'))
ostinato(tl.T('e3'), tl.T('e4'), ['Gm', 'A'], 46, step=BEAT / 2)
t_eff = tl.WT('e4', '效率'); HITS['eff'] = t_eff
pad(tl.T('e4'), F1, ['D', 'G', 'D', 'A'], 46, name='slow'); piano_motif(t_eff + 0.1, 62, 62, major=True)
for p in voicing('D', 62): note('choir', p, t_eff, t_eff + 3.5, 50)

# 5 飞轮：D 大调推进，弦乐八分音符固定音型 + 钢琴分解 + 轻鼓，逐段加码
prF = ['D', 'A', 'Bm', 'G']
pad(F1, tl.T('f5'), prF, 46, name='strings'); arp(F1, tl.T('f5'), prF, 44, lo=62)
ostinato(tl.T('f2'), tl.T('f5'), prF, 50, step=BEAT / 2)
pulse(tl.T('f2'), tl.T('f5'), 42); pulse(tl.T('f3'), tl.T('f5'), 30, every=BEAT / 2)
ramp('strings', F1, tl.T('f5'), 70, 115)
for c, s, e in bars(tl.T('f3'), tl.T('f5'), prF):
    for p in voicing(c, 55, 3): note('horn', p, s, e, 52)
t_share = tl.WT('f4', '规模经济分享'); HITS['share'] = t_share
for p in voicing('D', 62): note('choir', p, t_share, tl.T('f5'), 56)
t_scale = tl.WT('f5', '先拥有'); HITS['scale'] = t_scale
note('slow', 62, tl.T('f5'), t_scale, 0)
timp(t_scale, 38, 104); SUBS.append((t_scale, 0.85, 'boom'))
for p in voicing('D', 38, 3) + voicing('D', 62, 3): note('brass', p, t_scale, t_scale + 2.4, 80)
for p in voicing('D', 50, 4): note('slow', p, t_scale, G1 + 0.3, 50)

# 6 中国考题：紧张，D 小调；拨弦滴答 + 低铜管；拼多多段换成马林巴质感的钢琴高音
prG = ['Dm', 'Bb', 'Gm', 'A']
pad(G1, tl.T('g5'), prG, 40, name='strings'); ostinato(tl.T('g2'), tl.T('g5'), prG, 52, step=BEAT / 2, name='pizz', oct_=50)
pulse(tl.T('g2'), tl.T('g8'), 36)
for c, s, e in bars(tl.T('g3'), tl.T('g5'), prG):
    note('brass', root(c, 38), s, e, 50)
t60 = tl.WT('g4', '六十天'); HITS['d60'] = t60; note('timp', 38, t60, t60 + 1.5, 76)
pad(tl.T('g5'), tl.T('g8'), ['Gm', 'Dm', 'Bb', 'A'], 40, name='strings')
arp(tl.T('g5'), tl.T('g8'), ['Gm', 'Dm', 'Bb', 'A'], 40, lo=70, name='celesta', step=BEAT / 2)
ostinato(tl.T('g6'), tl.T('g8'), ['Gm', 'Dm', 'Bb', 'A'], 48, step=BEAT / 2)
pad(tl.T('g8'), Q1, ['Bb', 'C', 'Dm', 'Dm'], 46, name='slow')
ramp('slow', tl.T('g8'), tl.SE('g8'), 70, 118)
t_draw = tl.WT('g8', '透支'); HITS['overdraw'] = t_draw; timp(t_draw, 38, 90); SUBS.append((t_draw, 0.6, 'boom'))

# 7 底线：飞轮倒转——下行低音、半音摩擦，越来越暗；「值不值」前全停
for i, p in enumerate([50, 49, 48, 47, 46, 45, 44, 43]):
    t = tl.T('q1') + i * BAR / 2
    if t < tl.T('q3'): note('cello', p - 12, t, t + BAR / 2 + 0.05, 58); note('bass', p - 24, t, t + BAR / 2, 56)
for p in (62, 63): note('strings', p, tl.T('q1'), tl.T('q3'), 34)
ramp('strings', tl.T('q1'), tl.T('q3'), 60, 105)
pulse(tl.T('q2'), tl.T('q3'), 46, every=BEAT)
t_worth = tl.WT('q3', '值不值'); HITS['worth'] = t_worth
note('piano', 62, t_worth, t_worth + 3.5, 62); note('piano', 50, t_worth, t_worth + 3.5, 50); SUBS.append((t_worth, 0.5, 'boom'))

# 8 答案：D 大调全编制；z1 四句每句一小节，z3 抽到只剩钢琴；片尾 logo 一记落地
prZ = ['D', 'Bm', 'G', 'A']
pad(Z1, tl.T('z3'), prZ, 50, name='strings'); arp(Z1, tl.T('z3'), prZ, 46, lo=62)
ostinato(tl.T('z1'), tl.T('z3'), prZ, 50, step=BEAT / 2); pulse(tl.T('z1'), tl.T('z3'), 40)
for c, s, e in bars(tl.T('z1'), tl.T('z3'), prZ):
    for p in voicing(c, 55, 3): note('horn', p, s, e, 56)
for c, s, e in bars(tl.T('z2'), tl.T('z3'), prZ):
    for p in voicing(c, 62, 4): note('choir', p, s, e, 52)
piano_motif(tl.T('z3') + 0.1, 62, 54, major=True)
for p in voicing('Gmaj7', 55): note('slow', p, tl.T('z3'), END, 40)
timp(END, 38, 100, roll=1.2); SUBS.append((END, 0.9, 'boom'))
for p in voicing('D', 38, 3) + voicing('Dadd9' if False else 'D', 62, 4): note('brass', p, END, END + 4.5, 70)
for p in voicing('D', 50, 4): note('strings', p, END, TOTAL, 60)
ramp('strings', END + 1.0, TOTAL, 110, 0)

# ─────────────────────────── 渲染 ───────────────────────────
os.makedirs(os.path.join(WORK, 'music'), exist_ok=True)
mp = os.path.join(WORK, 'music', 'score.mid'); wp = os.path.join(WORK, 'music', 'score.wav')
for i in mid.instruments:
    if not i.is_drum and not any(c.number == 11 for c in i.control_changes): cc(i.name, 0, 100)
    i.control_changes.append(pm.ControlChange(91, 40, 0.0))  # GM 混响发送
mid.write(mp)
subprocess.run(['fluidsynth', '-ni', '-g', '0.6', '-r', str(SR), '-F', wp, SF2, mp], check=True, stdout=subprocess.DEVNULL)
y, sr = sf.read(wp); assert sr == SR
N = int(TOTAL * SR); y = np.pad(y, ((0, max(0, N - len(y))), (0, 0)))[:N]


def lp(x, f, o=4): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x, axis=0)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x, axis=0)


# 合成层：低频冲击（正弦下滑 + 轻微谐波）、气声渐强（粉噪低通到 1.2k，不刺耳）
fx = np.zeros((N, 2))
rng = np.random.default_rng(7)
for t, g, kind in SUBS:
    i0 = int(t * SR)
    if kind == 'boom':
        n = int(2.8 * SR); tt = np.arange(n) / SR
        f = 32 + 34 * np.exp(-tt * 5.5); ph = 2 * np.pi * np.cumsum(f) / SR
        s = (np.sin(ph) + 0.18 * np.sin(2 * ph)) * np.exp(-tt * 1.6) * np.minimum(1, tt / 0.006)
        s = s * 0.55 * g
    else:  # swell：起于 t，长 1.6 秒
        n = int(1.6 * SR); tt = np.arange(n) / SR
        w = rng.standard_normal(n); w = np.cumsum(w); w -= np.convolve(w, np.ones(400) / 400, 'same')
        w = lp(w, 1200) / (np.abs(w).max() + 1e-9)
        s = w * (tt / tt[-1]) ** 2.5 * 0.16 * g
    j = min(N, i0 + n) - i0
    if j > 0: fx[i0:i0 + j] += s[:j, None]
y = y + fx

# 卷积混响（暗色厅堂，RT60 ≈ 2.4s）
n = int(2.6 * SR); tt = np.arange(n) / SR
ir = rng.standard_normal((n, 2)) * np.exp(-tt * 6.9 / 2.4)[:, None]; ir = lp(ir, 3500)
ir[:int(0.012 * SR)] = 0; ir /= np.sqrt((ir ** 2).sum(0))
wet = np.stack([fftconvolve(y[:, k], ir[:, k])[:N] for k in range(2)], 1)
y = hp(0.82 * y + 0.30 * wet, 28)
y = lp(y, 11000, 2)
# 慢速电平均衡（3 秒窗 RMS，2:1 往中间收），再按响度归一到 −18 LUFS，软限幅
import pyloudnorm as pyln
from scipy.ndimage import uniform_filter1d, minimum_filter1d
rms = np.sqrt(uniform_filter1d((y ** 2).mean(1), int(3 * SR)) + 1e-10); db = 20 * np.log10(rms)
ref = np.median(db[db > -60]); g = np.clip(-(db - ref) * 0.5, -6, 9)
y *= (10 ** (g / 20))[:, None]
meter = pyln.Meter(SR); y *= 10 ** ((-18.0 - meter.integrated_loudness(y)) / 20)
lim = 10 ** (-2 / 20); pk = np.abs(y).max(1)
gg = minimum_filter1d(np.minimum(1, lim / np.maximum(pk, 1e-9)), 480); gg = np.convolve(gg, np.ones(480) / 480, 'same')
y *= np.minimum(gg, 1)[:, None]
sf.write(os.path.join(WORK, 'music.wav'), y.astype(np.float32), SR)
json.dump(HITS, open(os.path.join(WORK, 'hits.json'), 'w'), indent=1)
print('music %.1fs' % (N / SR), {k: round(v, 2) for k, v in HITS.items()})
