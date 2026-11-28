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
TITLE = tl.SE('o12') + 0.55; HITS['title'] = TITLE
G = lambda lid: grid(tl.S(lid) - BEAT)
END = tl.SE('z6') + 0.8; HITS['logo'] = END                   # 片尾动画开始：金句字形开始汇聚
LAND = grid(END + 2.25); HITS['logo_land'] = LAND            # logo 成形落定
BRAND = LAND + 2 * BEAT; HITS['brand'] = BRAND               # 重拍：金色「巴芒价值」
SLOGAN = BRAND + 3 * BEAT; HITS['slogan'] = SLOGAN           # 细金线引出关注语
FADE = TOTAL - 1.8; HITS['fade'] = FADE                      # 整体淡出


def hit(name, lid, word, v=80, boom=0.0, end=False):
    t = tl.WT(lid, word, end=end); HITS[name] = t
    if v: timp(t, 38, v)
    if boom: SUBS.append((t, boom, 'boom'))
    return t


# 引子 · 一年两半：钢片琴八音盒（玩偶）+ 低弦脉冲；拍卖槌一击；“分成了两半”抽空；两半各自的色彩
prO = ['Dm', 'Bb', 'F', 'A']
note('pad', 38, 0.0, tl.T('o3'), 30); ramp('pad', 0.0, 2.0, 30, 100)
arp(0.6, tl.T('o5'), prO, 40, lo=74, name='celesta', step=BEAT / 2, pat=(0, 2, 1, 3, 2, 1, 0, 2))
pulse(tl.T('o1') + BEAT, tl.T('o5'), 30)
pad(tl.T('o1'), tl.T('o5'), prO, 32, name='strings', bassname=None)
hit('auction', 'o2', '一百零八万', 92, 0.6)
pad(tl.T('o3'), tl.T('o5'), ['F', 'C', 'Bb', 'F'], 36, name='slow', bassname=None)
piano_motif(tl.T('o5') + 0.1, 62, 50)
for p in voicing('Dm', 50): note('slow', p, tl.T('o5'), tl.T('o6') + 0.3, 34)
hit('split', 'o6', '两半', 78, 0.45)
ostinato(tl.T('o7'), tl.T('o9'), ['Dm', 'Gm', 'Bb', 'A'], 48, step=BEAT / 2, name='pizz', oct_=50)
pad(tl.T('o7'), tl.T('o9'), ['Dm', 'Gm', 'Bb', 'A'], 38, name='strings')
pad(tl.T('o9'), tl.T('o10'), ['F', 'C'], 42, name='slow', bassname=None); arp(tl.T('o9'), tl.T('o10'), ['F', 'C'], 40, lo=69, name='harp')
for p in voicing('Bb', 50): note('slow', p, tl.T('o10'), tl.T('o12'), 40)
ramp('slow', tl.T('o10'), tl.T('o12'), 40, 110)
for p in voicing('Dm', 50): note('strings', p, tl.T('o12'), TITLE, 44)
ramp('strings', tl.T('o12'), TITLE - 0.05, 60, 122); SUBS.append((TITLE - 1.6, 0.8, 'swell'))
note('piano', 74, tl.WT('o12', '什么'), tl.WT('o12', '什么') + 2, 50)
# 片名：重拍
timp(TITLE, 38, 112, roll=0.4); SUBS.append((TITLE, 1.0, 'boom'))
for p in voicing('Dm', 38, 3) + voicing('Dm', 62, 4): note('brass', p, TITLE, TITLE + 2.6, 74)
for p in voicing('Dm', 50, 4): note('slow', p, TITLE, G('p1'), 46)

# 01 第一性原理：三个问题（竖琴三连）→ 芒格（低弦）→ 孔雀（竖琴上行 + 重拍“装不起”）→ 矛盾（弦乐绷紧）
P1 = G('p1'); prP = ['Dm', 'Bb', 'F', 'C']
pad(P1, tl.T('p6'), prP, 38, name='strings'); arp(P1, tl.T('p6'), prP, 38, lo=62, name='harp')
for k_, lid in enumerate(('p2', 'p3', 'p4')): note('celesta', (74, 77, 81)[k_], tl.S(lid), tl.S(lid) + 1.6, 56)
pad(tl.T('p6'), tl.T('p9'), ['Gm', 'Dm', 'Bb', 'A'], 42, name='slow'); ostinato(tl.T('p7'), tl.T('p9'), ['Gm', 'Dm', 'Bb', 'A'], 44, step=BEAT / 2)
hit('envy', 'p7', '嫉妒', 64)
pad(tl.T('p9'), tl.T('p11'), ['Bb', 'F'], 36, name='strings', bassname=None)
arp(tl.T('p11'), tl.T('p14'), ['Dm', 'F', 'Bb', 'C'], 42, lo=62, name='harp', step=BEAT / 2)
pad(tl.T('p11'), tl.T('p14'), ['Dm', 'F', 'Bb', 'C'], 40, name='slow')
hit('costly', 'p11', '装不起', 96, 0.7)
pad(tl.T('p14'), tl.T('p16'), ['F', 'C', 'Dm', 'Bb'], 40, name='strings'); arp(tl.T('p14'), tl.T('p16'), ['F', 'C', 'Dm', 'Bb'], 36, lo=67, name='piano')
for p in (62, 63): note('strings', p, tl.T('p16'), tl.SE('p18'), 40)
ramp('strings', tl.T('p16'), tl.SE('p18'), 60, 118); pulse(tl.T('p17'), tl.SE('p18'), 40, BEAT / 2)
hit('paradox', 'p18', '三角', 96, 0.75)

# 02 一把尺子：巴菲特（铜管低声部，稳重）
D1 = G('d1'); prD = ['Bb', 'F', 'Gm', 'D']
pad(D1, tl.T('d4'), prD, 42, name='slow')
for c, s_, e_ in bars(tl.T('d2'), tl.T('d4'), prD): note('horn', root(c, 50), s_, e_, 46)
hit('pricing', 'd2', '定价权', 70)
pad(tl.T('d4'), G('k1'), ['Bb', 'C', 'Dm', 'Dm'], 44, name='strings'); ramp('strings', tl.T('d4'), G('k1'), 60, 118)
hit('three', 'd4', '三道关', 84, 0.5)

# 03 三道关：每关开头一记定音鼓；第二关最紧张；第三关转温暖；算术段明亮
for lid in ('k1', 'k6', 'k16'): hit('gate_' + lid, lid, '关', 90, 0.55)
prK1 = ['Dm', 'Bb', 'F', 'C']
pad(tl.T('k1'), tl.T('k6'), prK1, 40, name='strings'); ostinato(tl.T('k1'), tl.T('k6'), prK1, 44, step=BEAT / 2, name='pizz', oct_=50)
arp(tl.T('k4'), tl.T('k6'), prK1, 38, lo=67, name='celesta', step=BEAT / 2)
prK2 = ['Dm', 'Dm', 'Bb', 'A']
pad(tl.T('k6'), tl.T('k12'), prK2, 44, name='strings'); ostinato(tl.T('k6'), tl.T('k12'), prK2, 52, step=BEAT / 2)
pulse(tl.T('k7'), tl.T('k12'), 40, BEAT / 2)
for c, s_, e_ in bars(tl.T('k8'), tl.T('k12'), prK2): note('brass', root(c, 38), s_, e_, 46)
t_crash = hit('crash', 'k9', '一半以上', 0, 0.9)
for i, p in enumerate((74, 72, 70, 69, 65, 62)): note('celesta', p, t_crash + i * 0.18, t_crash + i * 0.18 + 0.5, 50 - 4 * i)
hit('fake', 'k10', '九成', 70)
hit('discount', 'k11', '打折', 0, 0.5)
prK3 = ['F', 'C', 'Dm', 'Bb']
pad(tl.T('k12'), tl.T('k16'), prK3, 42, name='slow'); arp(tl.T('k12'), tl.T('k16'), prK3, 40, lo=65, name='harp')
hit('seynes', 'k14', '稀缺', 76)
prK4 = ['Bb', 'F', 'C', 'Dm']
pad(tl.T('k16'), tl.T('k21'), prK4, 40, name='strings'); arp(tl.T('k16'), tl.T('k21'), prK4, 38, lo=62, name='piano')
pad(tl.T('k21'), tl.T('m1'), ['Gm', 'Dm', 'Bb', 'A'], 42, name='strings'); ostinato(tl.T('k21'), tl.T('k23'), ['Gm', 'Dm', 'Bb', 'A'], 46, step=BEAT / 2, name='pizz', oct_=50)
hit('sam', 'k22', '炸了锅', 80, 0.5)
prM = ['F', 'C', 'Bb', 'F']
pad(G('m1'), G('g1'), prM, 46, name='slow'); arp(G('m1'), G('g1'), prM, 44, lo=65, name='harp'); pulse(tl.T('m2'), tl.T('m4'), 34)
hit('margin', 'm2', '七十一', 72)
hit('fee', 'm3', '六成', 64)

# 04 中国考题：悬疑（小调钢琴 + 低弦），段永平处一次逆向的上行
G1 = G('g1'); prG = ['Dm', 'Gm', 'Bb', 'A']
pad(G1, tl.T('g7'), prG, 40, name='strings'); ostinato(tl.T('g2'), tl.T('g7'), prG, 48, step=BEAT / 2, name='pizz', oct_=50)
arp(tl.T('g2'), tl.T('g7'), prG, 36, lo=69, name='piano', step=BEAT)
pulse(tl.T('g3'), tl.T('g6'), 34)
hit('duan', 'g7', '段永平', 86, 0.55)
pad(tl.T('g7'), G('q1'), ['F', 'C', 'Dm', 'Bb'], 44, name='slow'); arp(tl.T('g7'), tl.T('g9'), ['F', 'C', 'Dm', 'Bb'], 40, lo=65, name='harp')
for p in voicing('Dm', 50): note('strings', p, tl.T('g9'), G('q1'), 40)
ramp('strings', tl.T('g9'), G('q1'), 50, 105)

# 05 失守：低铜管警示；“火药”重拍；转身离开时只留低弦
Q1 = G('q1')
for i, p in enumerate([50, 50, 49, 49, 46, 46, 45, 45]):
    t = Q1 + i * BAR / 2
    if t < tl.T('q4'): note('cello', p - 12, t, t + BAR / 2 + 0.05, 56); note('bass', p - 24, t, t + BAR / 2, 54)
for p in (62, 63): note('strings', p, tl.T('q2'), tl.WT('q3', '火药'), 34)
ramp('strings', tl.T('q2'), tl.WT('q3', '火药'), 60, 110); pulse(tl.T('q2'), tl.WT('q3', '火药'), 42, BEAT / 2)
t_fire = hit('fire', 'q3', '火药', 102, 0.95)
for p in voicing('Dm', 38, 3): note('brass', p, t_fire, t_fire + 2.4, 70)
for p in voicing('Dm', 50, 3): note('slow', p, tl.T('q4'), G('z1'), 34)

# 06 答案：隐形测试几乎静音（只有心跳低频）→ “两种都没有错”回暖 → 转 D 大调 → 金句最大重拍
Z1 = G('z1')
t = Z1
while t < tl.T('z3') - 0.2:
    ins('drums', 0, True).notes.append(pm.Note(34, 36, float(t), float(t + 0.15)))
    ins('drums', 0, True).notes.append(pm.Note(22, 36, float(t + 0.28), float(t + 0.4))); t += 1.0
note('pad', 38, Z1, tl.T('z3'), 24)
pad(tl.T('z3'), tl.T('z4'), ['F', 'C'], 40, name='slow', bassname=None); piano_motif(tl.T('z3') + 0.2, 65, 50, major=True)
prZ = ['Bb', 'F', 'G', 'D']
pad(tl.T('z4'), tl.T('z6'), prZ, 48, name='strings'); arp(tl.T('z4'), tl.T('z6'), prZ, 44, lo=62)
ostinato(tl.T('z5'), tl.T('z5b'), prZ, 50, step=BEAT / 2); pulse(tl.T('z5'), tl.T('z5b'), 40)   # z5b（它代表我之前的那句）收一点，留给金句
hit('answer', 'z5', '护城河', 90, 0.6)
t_last = hit('last', 'z6', '代表我', 110, 1.0)
for p in voicing('D', 62, 4): note('choir', p, t_last, END + 0.3, 56)
for p in voicing('D', 38, 3) + voicing('D', 62, 4): note('brass', p, t_last, t_last + 2.6, 72)
for p in voicing('Gmaj7', 55): note('slow', p, tl.T('z6'), END + 0.4, 40)
# 片尾：汇聚 → 落定 → 重拍 → 关注语 → 淡出
for p in voicing('D', 50, 4): note('slow', p, END, LAND + 0.1, 40)
ramp('slow', END, LAND, 25, 118)                                      # 弦乐渐强托起汇聚
for i, p in enumerate([74, 78, 81, 83, 86, 90, 93]):                  # 钢片琴上行闪光（只到 F#6，不刺耳）
    t = END + 0.35 + i * (LAND - END - 0.5) / 7; note('celesta', p, t, t + 0.9, 44 + 4 * i)
SUBS.append((LAND - 1.6, 0.55, 'swell'))
timp(LAND, 38, 92); SUBS.append((LAND, 0.75, 'boom'))
for p in voicing('D', 62, 4): note('choir', p, LAND, FADE + 1.0, 50)
for p in voicing('D', 50, 4): note('strings', p, LAND, TOTAL, 52)
timp(BRAND, 38, 108, roll=0.5); SUBS.append((BRAND, 1.0, 'boom'))      # 主重拍
for p in voicing('D', 38, 3) + voicing('D', 62, 4): note('brass', p, BRAND, BRAND + 3.2, 78)
note('bass', 26, BRAND, TOTAL, 60)
for i, p in enumerate((62, 66, 69, 74)): note('harp', p, SLOGAN + i * BEAT / 2, SLOGAN + 3, 54)
piano_motif(SLOGAN + 2 * BEAT, 74, 48, major=True)
ramp('strings', FADE - 0.5, TOTAL, 110, 0); ramp('choir', FADE - 0.5, TOTAL, 110, 0); ramp('brass', FADE - 1.5, TOTAL, 100, 0)

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
