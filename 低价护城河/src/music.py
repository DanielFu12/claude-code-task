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
TITLE = tl.SE('o10') + 0.55; HITS['title'] = TITLE
G = lambda lid: grid(tl.S(lid) - BEAT)
END = tl.SE('z4') + 0.8; HITS['logo'] = END                   # 片尾动画开始：画面元素开始汇聚
LAND = grid(END + 2.25); HITS['logo_land'] = LAND            # logo 成形落定
BRAND = LAND + 2 * BEAT; HITS['brand'] = BRAND               # 重拍：金色「巴芒价值」
SLOGAN = BRAND + 3 * BEAT; HITS['slogan'] = SLOGAN           # 细金线引出关注语
FADE = TOTAL - 1.8; HITS['fade'] = FADE                      # 整体淡出

# 引子 · 内卷：低音弦乐脉动 + 轻鼓，像新闻快讯；o5 加码；o6 发问时抽空
note('pad', 38, 0.0, tl.T('o7'), 30); ramp('pad', 0.0, 2.0, 30, 100)
prI = ['Dm', 'Dm', 'Bb', 'A']
ostinato(tl.T('o2') - BEAT, tl.T('o6'), prI, 46, step=BEAT / 2)
pulse(tl.T('o2') - BEAT, tl.T('o6'), 34)
pad(tl.T('o2') - BEAT, tl.T('o6'), prI, 34, name='strings', bassname=None)
arp(tl.T('o3'), tl.T('o6'), prI, 36, lo=64)
for c, s_, e_ in bars(tl.T('o5'), tl.T('o6'), ['Bb', 'A']):
    for p in voicing(c, 50, 3): note('brass', p, s_, e_, 46)
t_q = tl.WT('o6', '谁建起了护城河'); HITS['q_moat'] = t_q
note('piano', 62, t_q, t_q + 3, 56); note('piano', 50, t_q, t_q + 3, 44)
# 热狗（暖）/ 小黄车（冷）/ 差别在哪 → 片名
piano_motif(tl.T('o7') + 0.1, 65, 58, major=True)
pad(tl.T('o7'), tl.T('o8'), ['F', 'C'], 38, name='slow', bassname=None)
piano_motif(tl.T('o8') + 0.1, 62, 52)
note('cello', 38, tl.T('o8'), tl.SE('o9'), 50); ramp('cello', tl.T('o8'), tl.SE('o9'), 50, 110)
for p in voicing('Dm', 50): note('slow', p, tl.T('o9'), TITLE, 40)
ramp('slow', tl.T('o9'), TITLE - 0.05, 30, 120)
note('piano', 74, tl.WT('o10', '哪'), tl.WT('o10', '哪') + 2, 50)
SUBS.append((TITLE, 1.0, 'boom')); timp(TITLE, 38, 112, roll=1.4); SUBS.append((TITLE - 1.6, 0.5, 'swell'))
for p in voicing('Dm', 38, 3) + voicing('Dm', 62, 3): note('brass', p, TITLE, TITLE + 2.6, 84)
for p in voicing('Dm', 50, 4): note('choir', p, TITLE, TITLE + 3.2, 60)

# 01 第一性原理：钢琴 + 铺底，思考感；纺织厂段落怀旧（慢弦 + 钢片琴）；检验段脉动
P1 = G('p1')
pad(P1, tl.T('p6'), ['Dm', 'Bb', 'F', 'C'], 38, name='strings'); arp(P1, tl.T('p6'), ['Dm', 'Bb', 'F', 'C'], 38, lo=62)
t_zero = tl.WT('p5', '挤到零'); HITS['zero'] = t_zero; timp(t_zero, 38, 70)
pad(tl.T('p6'), tl.T('p10'), ['Gm', 'Dm', 'Bb', 'A'], 42, name='slow')
arp(tl.T('p6'), tl.T('p10'), ['Gm', 'Dm', 'Bb', 'A'], 34, lo=70, name='celesta', step=BEAT)
t_buy = tl.WT('p8', '买家的口袋'); HITS['buyer'] = t_buy
for p in voicing('Bb', 62): note('choir', p, t_buy, t_buy + 3, 44)
prT = ['Dm', 'Bb', 'Gm', 'A']
ostinato(tl.T('p10'), tl.T('p12'), prT, 48); pad(tl.T('p10'), tl.T('p12'), prT, 36, name='strings', bassname=None)
pulse(tl.T('p10'), tl.T('p12'), 34); arp(tl.T('p10'), tl.T('p12'), prT, 40, lo=64)
t_blood = tl.WT('p12', '失血'); HITS['blood'] = t_blood
timp(t_blood, 38, 96); SUBS.append((t_blood, 0.7, 'boom'))
for p in voicing('Dm', 50): note('strings', p, t_blood, G('d1') + 0.2, 34)

# 02 两位大师：巴菲特（温暖铜管）↔ 段永平（对撞重拍）→ 和解（大调）→ 渐强到「三个条件」
D1 = G('d1')
pad(D1, tl.T('d3'), ['Bb', 'F', 'C', 'Dm'], 42, name='slow')
for c, s_, e_ in bars(tl.T('d2'), tl.T('d3'), ['Bb', 'F']):
    for p in voicing(c, 55, 3): note('horn', p, s_, e_, 54)
t_clash = tl.S('d3'); HITS['clash'] = t_clash
timp(t_clash, 38, 104, roll=0.8); SUBS.append((t_clash, 0.8, 'boom'))
pad(tl.T('d3'), tl.T('d5'), ['Dm', 'Gm', 'Dm', 'A'], 40, name='strings')
ostinato(tl.T('d3'), tl.T('d5'), ['Dm', 'Gm', 'Dm', 'A'], 46, step=BEAT / 2, name='pizz', oct_=50)
t_bm = tl.WT('d5', '商业模式'); HITS['bizmodel'] = t_bm
pad(tl.T('d5'), tl.T('d8'), ['F', 'C', 'Bb', 'F'], 44, name='slow'); arp(tl.T('d5'), tl.T('d8'), ['F', 'C', 'Bb', 'F'], 38, lo=65, name='harp')
t_pp = tl.WT('d6', '定价权'); HITS['pricing'] = t_pp
for p in voicing('F', 62): note('choir', p, t_pp, t_pp + 3, 52)
note('celesta', 77, t_pp, t_pp + 1.5, 60)
pad(tl.T('d8'), G('k1'), ['Bb', 'C'], 44, name='strings'); ramp('strings', tl.T('d8'), G('k1'), 60, 120)
SUBS.append((tl.S('k1') - 1.6, 0.6, 'swell'))

# 03 三个条件：每个条件一记太鼓 + 低频；条件二起飞轮推进；Costco 证据段温暖大调；会合处合唱
for lid in ('k1', 'k5', 'k8'):
    t = tl.WT(lid, '条件'); HITS['cond_' + lid] = t
    note('taiko', 45, t, t + 1.0, 100); timp(t, 38, 92); SUBS.append((t, 0.6, 'boom'))
prK1 = ['Dm', 'Bb', 'Gm', 'A']
pad(tl.T('k1'), tl.T('k5'), prK1, 40, name='strings'); ostinato(tl.T('k1'), tl.T('k5'), prK1, 46, step=BEAT / 2)
pulse(tl.T('k1'), tl.T('k5'), 34)
prF = ['D', 'A', 'Bm', 'G']
pad(tl.T('k5'), tl.T('k8'), prF, 46, name='strings'); arp(tl.T('k5'), tl.T('k8'), prF, 44, lo=62)
ostinato(tl.T('k6'), tl.T('k8'), prF, 50, step=BEAT / 2); pulse(tl.T('k6'), tl.T('k8'), 42)
ramp('strings', tl.T('k5'), tl.T('k8'), 70, 115)
t_gas = tl.WT('k7', '油门踩到底'); HITS['gas'] = t_gas; timp(t_gas, 38, 86)
prK3 = ['Bm', 'G', 'D', 'A']
pad(tl.T('k8'), tl.T('k10'), prK3, 44, name='slow'); ostinato(tl.T('k8'), tl.T('k10'), prK3, 44, step=BEAT / 2, name='pizz', oct_=50)
t_fuel = tl.WT('k9', '燃料'); HITS['fuel'] = t_fuel
for p in voicing('G', 55, 3): note('brass', p, t_fuel, t_fuel + 2.2, 62)
prC = ['D', 'G', 'Bm', 'A']
pad(tl.T('k10'), tl.T('k14'), prC, 44, name='strings'); arp(tl.T('k10'), tl.T('k14'), prC, 42, lo=62)
pulse(tl.T('k11'), tl.T('k14'), 36)
t_fee = tl.WT('k11', '六十五美元'); HITS['fee'] = t_fee; note('timp', 38, t_fee, t_fee + 1.5, 80)
t_pw = tl.WT('k13', '定价权'); HITS['power'] = t_pw
for c, s_, e_ in bars(tl.T('k13'), G('g1'), ['G', 'D']):
    for p in voicing(c, 55, 3): note('horn', p, s_, e_, 58)
t_meet = tl.WT('k14', '会合'); HITS['meet'] = t_meet
for p in voicing('D', 62): note('choir', p, t_meet - 0.6, G('g1') + 0.5, 58)
timp(t_meet, 38, 96); SUBS.append((t_meet, 0.7, 'boom'))
for p in voicing('D', 38, 3) + voicing('D', 62, 3): note('brass', p, t_meet, t_meet + 2.4, 74)

# 04 中国考题：紧张，拨弦滴答 + 低铜管；「内卷」处暗重拍
G1 = G('g1'); prG = ['Dm', 'Bb', 'Gm', 'A']
pad(G1, tl.T('g5'), prG, 40, name='strings'); ostinato(tl.T('g2'), tl.T('g5'), prG, 50, step=BEAT / 2, name='pizz', oct_=50)
pulse(tl.T('g2'), tl.T('g8'), 34)
for c, s_, e_ in bars(tl.T('g3'), tl.T('g5'), prG): note('brass', root(c, 38), s_, e_, 48)
t60 = tl.WT('g3', '六十天'); HITS['d60'] = t60; note('timp', 38, t60, t60 + 1.5, 76)
pad(tl.T('g5'), tl.T('g8'), ['Gm', 'Dm', 'Bb', 'A'], 40, name='strings')
arp(tl.T('g5'), tl.T('g8'), ['Gm', 'Dm', 'Bb', 'A'], 38, lo=70, name='celesta', step=BEAT / 2)
ostinato(tl.T('g6'), tl.T('g8'), ['Gm', 'Dm', 'Bb', 'A'], 46, step=BEAT / 2)
pad(tl.T('g8'), G('q1'), ['Bb', 'A', 'Dm', 'Dm'], 46, name='slow'); ramp('slow', tl.T('g8'), tl.SE('g8'), 70, 118)
t_inv = tl.WT('g8', '这就是内卷'); HITS['involution'] = t_inv; timp(t_inv, 38, 96); SUBS.append((t_inv, 0.7, 'boom'))

# 05 底线：飞轮倒转——下行低音、半音摩擦；「值不值」前全停
for i, p in enumerate([50, 49, 48, 47, 46, 45, 44, 43]):
    t = tl.T('q1') + i * BAR / 2
    if t < tl.T('q3'): note('cello', p - 12, t, t + BAR / 2 + 0.05, 58); note('bass', p - 24, t, t + BAR / 2, 56)
for p in (62, 63): note('strings', p, tl.T('q1'), tl.T('q3'), 34)
ramp('strings', tl.T('q1'), tl.T('q3'), 60, 105); pulse(tl.T('q2'), tl.T('q3'), 46)
t_worth = tl.WT('q3', '值不值'); HITS['worth'] = t_worth
note('piano', 62, t_worth, t_worth + 3.5, 62); note('piano', 50, t_worth, t_worth + 3.5, 50); SUBS.append((t_worth, 0.5, 'boom'))

# 06 答案：D 大调全编制；z3 三句各一记；z4 抽到钢琴；片尾 logo 落地
Z1 = G('z1'); prZ = ['D', 'Bm', 'G', 'A']
pad(Z1, tl.T('z4'), prZ, 50, name='strings'); arp(Z1, tl.T('z4'), prZ, 46, lo=62)
ostinato(tl.T('z2'), tl.T('z4'), prZ, 50, step=BEAT / 2); pulse(tl.T('z2'), tl.T('z4'), 40)
for c, s_, e_ in bars(tl.T('z2'), tl.T('z4'), prZ):
    for p in voicing(c, 55, 3): note('horn', p, s_, e_, 56)
for k_, key in enumerate(('一种选择', '一种能力', '才是护城河')):
    t = tl.WT('z3', key); HITS['z3_%d' % k_] = t; note('timp', 38, t, t + 1.4, 70 + 12 * k_)
    if k_ == 2: SUBS.append((t, 0.6, 'boom'))
for p in voicing('D', 62, 4): note('choir', p, tl.WT('z3', '定价权'), tl.T('z4') + 0.3, 56)
piano_motif(tl.T('z4') + 0.1, 62, 54, major=True)
for p in voicing('Gmaj7', 55): note('slow', p, tl.T('z4'), END + 0.4, 40)
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
