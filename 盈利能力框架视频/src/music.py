"""原创配乐：按 timeline.json 逐小节编曲，章节重拍处落冲击音，提示点处加卡点音效。

输出 work/music_stems.npz（各声部）和 work/music.wav。
"""
import json, os, sys
import numpy as np, soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import instruments as I
from dsp import SR, midi, make_ir, reverb, delay, compress, sos_filter, shelf, peak, tanh_sat

WORK = os.path.join(HERE, '..', 'work')
TL = json.load(open(os.path.join(WORK, 'timeline.json')))
BEAT, BAR, TOTAL = TL['beat'], TL['bar'], TL['total']
NB = int(round(TOTAL / BAR))
N = int((TOTAL + 6) * SR)
STEP = BEAT / 4

# ---------------------------------------------------------------- harmony
CH = {'Dm': [2, 5, 9], 'Bb': [10, 2, 5], 'F': [5, 9, 0], 'C': [0, 4, 7], 'Gm': [7, 10, 2], 'A': [9, 1, 4],
      'Am': [9, 0, 4], 'D': [2, 6, 9], 'Csus': [0, 5, 7], 'Bbmaj7': [10, 2, 5, 9], 'Fsus2': [5, 7, 0]}
PROG = {
    'hook':   ['Dm', 'Dm', 'Bb', 'Bb', 'Gm', 'Gm', 'A', 'A'],
    'epic':   ['Dm', 'Bb', 'F', 'C'],
    'layer':  ['Dm', 'F', 'Bb', 'C'],
    'dark':   ['Dm', 'Bb', 'Gm', 'A'],
    'bright': ['F', 'C', 'Dm', 'Bb'],
    'dark2':  ['Gm', 'Dm', 'Bb', 'A'],
    'calm':   ['Bbmaj7', 'F', 'Gm', 'Dm'],
    'drive':  ['Dm', 'C', 'Bb', 'C'],
    'tense':  ['Dm', 'Gm', 'Bb', 'A'],
    'ether':  ['Bb', 'C', 'Am', 'Dm'],
    'lift':   ['F', 'C', 'Dm', 'Bb'],
    'finale': ['Bb', 'F', 'C', 'Dm'],
    'outro':  ['Bb', 'C', 'D', 'D'],
}
# 场景 -> (和声进行, 基础能量 0-5)
SPEC = {
    'hook': ('hook', 0), 'title': ('epic', 5), 'formula': ('epic', 2), 'block': ('layer', 3), 'map': ('epic', 3),
    'L0': ('dark', 3), 'stick': ('bright', 2), 'loom': ('bright', 2), 'moat': ('bright', 3),
    'L2': ('calm', 2), 'L3': ('drive', 3), 'kitty': ('drive', 3), 'L4': ('tense', 3), 'gov': ('tense', 3),
    'L5': ('ether', 2), 'combo': ('epic', 5), 'proc': ('lift', 4), 'tests': ('lift', 4),
    'rules': ('finale', 4), 'quote': ('finale', 3), 'outro': ('outro', 2),
}
HALFTIME = {'L2', 'L5', 'quote', 'formula'}

# 主题动机（拍数，MIDI）——片头、组合规则、终章反复出现
MOTIF = [
    [(74, 1.5), (81, .5), (81, 1), (79, .5), (77, .5)],
    [(77, 1.5), (79, .5), (77, 1), (74, 1)],
    [(72, 1.5), (77, .5), (77, 1), (76, .5), (74, .5)],
    [(76, 3), (72, 1)],
    [(74, 1.5), (81, .5), (81, 1), (82, .5), (81, .5)],
    [(79, 1.5), (77, .5), (77, 1), (74, 1)],
    [(72, 1.5), (74, .5), (77, 1), (79, 1)],
    [(76, 2), (79, 1), (81, 1)],
]
MOTIF_FIN = [
    [(77, 1.5), (82, .5), (81, 1), (79, .5), (77, .5)],
    [(77, 1.5), (79, .5), (81, 1), (84, 1)],
    [(79, 1.5), (76, .5), (76, 1), (77, .5), (79, .5)],
    [(81, 4)],
]

scenes = TL['scenes']


def scene_at(t):
    for s in scenes:
        if s['start'] - 1e-6 <= t < s['end'] - 1e-6:
            return s
    return scenes[-1]


# 每小节信息
bars = []
anchor = {}
for b in range(NB):
    t = b * BAR
    s = scene_at(t + 0.01)
    prog, e = SPEC[s['id']]
    if s['id'] not in anchor:
        anchor[s['id']] = b
    bars.append(dict(b=b, t=t, scene=s, prog=prog, e=e, rel=b - anchor[s['id']]))

# 能量自动化
for bi in bars:
    sid, rel = bi['scene']['id'], bi['rel']
    if sid == 'title':
        bi['e'] = 5 if rel < 4 else 3
    if sid == 'hook':
        bi['e'] = 0 if rel < 8 else (1 if rel < 15 else 2)
    if sid == 'map':
        n = sum(1 for k in ('l0', 'l1', 'l2', 'l3', 'l4', 'l5') if bi['scene']['cq'].get(k, 1e9) <= bi['t'] + 0.1)
        bi['e'] = 3 if n < 3 else 4
    if sid == 'combo':
        bi['e'] = 5
    if sid == 'quote' and rel >= 4:
        bi['e'] = 2
    if sid == 'L0':
        veto = bi['scene']['cq'].get('veto', 1e9)
        if bi['t'] >= veto - 0.01:
            bi['e'] = 1

for i, bi in enumerate(bars):
    p = PROG[bi['prog']]
    bi['chord'] = p[bi['rel'] % len(p)] if bi['prog'] != 'hook' else p[(bi['rel'] // 2) % len(p) * 0 + min(bi['rel'] // 2, 3) * 2]
    if bi['prog'] == 'hook':
        bi['chord'] = ['Dm', 'Bb', 'Gm', 'A'][(bi['rel'] // 2) % 4]
    if bi['prog'] == 'outro' and bi['rel'] >= 2:
        bi['chord'] = 'D'

# 下一小节是否为章节重拍
sting_bars = {}
for s in scenes:
    if s['sting'] and s['start'] > 0:
        sting_bars[int(round(s['start'] / BAR))] = s
for bi in bars:
    bi['pre'] = (bi['b'] + 1) in sting_bars   # 本小节结束即章节重拍
    bi['sting'] = bi['b'] in sting_bars


# ---------------------------------------------------------------- buses
BUS = {k: np.zeros((N, 2), np.float32) for k in
       ('kick', 'drums', 'bass', 'pad', 'arp', 'keys', 'lead', 'choir', 'fx', 'acc')}
KICKS = []


def put(bus, sig, t, gain=1.0, pan=0.0):
    i = int(round(t * SR))
    if i >= N or gain <= 0: return
    if i < 0:
        sig = sig[-i:]; i = 0
    n = min(len(sig), N - i)
    if sig.ndim == 1:
        a = (pan + 1) * np.pi / 4
        BUS[bus][i:i + n, 0] += sig[:n] * gain * np.cos(a) * 1.414
        BUS[bus][i:i + n, 1] += sig[:n] * gain * np.sin(a) * 1.414
    else:
        BUS[bus][i:i + n] += sig[:n] * gain


def voicing(pcs, lo=50, hi=70, prev=None):
    import itertools
    cands = []
    opts = [[p + 12 * o for o in range(3, 7) if lo <= p + 12 * o <= hi] for p in pcs]
    for combo in itertools.product(*opts):
        c = sorted(combo)
        if c[-1] - c[0] > 14: continue
        cost = 0 if prev is None else sum(min(abs(x - y) for y in prev) for x in c)
        cost += abs(np.mean(c) - (lo + hi) / 2) * 0.3
        cands.append((cost, c))
    return min(cands)[1]


# ---------------------------------------------------------------- arrangement
prev_v = None
rng = np.random.default_rng(3)
for bi in bars:
    b, t0, e, ch = bi['b'], bi['t'], bi['e'], bi['chord']
    sid = bi['scene']['id']
    pcs = CH[ch]
    root = pcs[0]
    ht = sid in HALFTIME
    last_half_mute = bi['pre']
    big_pre = bi['pre'] and sting_bars[b + 1]['id'] in ('title', 'combo', 'proc', 'rules')

    # ---- pad
    v = voicing(pcs[:3], 50, 70, prev_v); prev_v = v
    if len(pcs) > 3: v = v + [pcs[3] + 60]
    cut = [900, 1400, 2000, 2700, 3600, 5200][e]
    pg = [0.20, 0.22, 0.22, 0.22, 0.25, 0.28][e]
    for k, m in enumerate(v):
        lfo = (lambda n, c=cut, ph=b * 0.7 + k: (c * (1 + 0.35 * np.sin(2 * np.pi * 0.23 * (np.arange(n) / SR) + ph))).astype(np.float32))
        put('pad', I.supersaw(midi(m), BAR, cutoff=cut, attack=0.25 if e >= 3 else 0.6, release=1.4, seed=b * 7 + k, bright_env=lfo), t0, pg)
    if e >= 4:   # 高八度亮层
        for m in v[1:]:
            put('pad', I.supersaw(midi(m + 12), BAR, voices=5, cutoff=cut * 1.2, attack=0.2, release=1.0, seed=b * 11 + m), t0, 0.07)

    # ---- bass
    br = 33 + ((root - 9) % 12)        # A1..G#2
    if e <= 1:
        put('bass', I.sub_bass(midi(br), BAR * 0.98, 0.55), t0, 0.5 if e == 1 else 0.35)
    elif e == 2 or ht:
        put('bass', I.sub_bass(midi(br), BAR * 0.95, 0.6), t0, 0.55)
        for st in ([0, 6, 8, 14] if not ht else [0, 10]):
            put('bass', I.bass_synth(midi(br + 12), STEP * 1.6, 0.5, cut=400), t0 + st * STEP, 0.30)
    else:
        put('bass', I.sub_bass(midi(br), BAR * 0.95, 0.6), t0, 0.55)
        steps = [0, 2, 4, 6, 8, 10, 12, 14] if e == 3 else [0, 3, 4, 6, 8, 11, 12, 14]
        for st in steps:
            if last_half_mute and st >= 12: continue
            oct_ = 12 if (st % 4 == 2) else 0
            put('bass', I.bass_synth(midi(br + 12 + oct_), STEP * 1.5, 0.75, cut=900 if e == 3 else 1400), t0 + st * STEP, 0.36)

    # ---- drums
    def K(st, vel=1.0):
        tt = t0 + st * STEP
        put('kick', I.kick(vel), tt, 0.9); KICKS.append((tt, vel))
    mute_from = 12 if last_half_mute else 99
    if big_pre: mute_from = 99
    if e == 1 and sid != 'hook':
        K(0, 0.6)
    elif e == 2:
        if ht:
            K(0, 0.8)
            if 10 < mute_from: K(10, 0.55)
            if 8 < mute_from: put('drums', I.snare(0.6), t0 + 8 * STEP, 0.35)
        else:
            K(0, 0.8)
            if 8 < mute_from: K(8, 0.7)
            if 12 < mute_from: put('drums', I.clap(0.5), t0 + 12 * STEP, 0.25)
        for st in (2, 6, 10, 14):
            if st < mute_from: put('drums', I.hat(0.45), t0 + st * STEP, 0.25, 0.3)
    elif e >= 3:
        for st in (0, 4, 8, 12):
            if st < mute_from: K(st, 1.0 if st == 0 else 0.92)
        for st in (4, 12):
            if st < mute_from:
                put('drums', I.clap(0.8), t0 + st * STEP, 0.38)
                if e >= 4: put('drums', I.snare(0.6), t0 + st * STEP, 0.25)
        for st in range(16):
            if st >= mute_from: break
            acc = 0.75 if st % 4 == 2 else (0.35 if st % 2 else 0.5)
            if st == 14 and bi['rel'] % 2 == 1:
                put('drums', I.hat(0.6, open_=True), t0 + st * STEP, 0.22, -0.25)
            else:
                put('drums', I.hat(acc * (0.85 + 0.3 * rng.random())), t0 + st * STEP + rng.normal(0, 0.003), 0.17, 0.25 if st % 2 else -0.1)
        if e >= 4:
            if 0 < mute_from: put('drums', I.taiko(0.9), t0, 0.45)
            if 10 < mute_from: put('drums', I.taiko(0.7, 1.1), t0 + 10 * STEP, 0.35)
            if bi['rel'] % 4 == 3 and not bi['pre']:
                for k, st in enumerate((12, 13, 14, 15)):
                    put('drums', I.tom(0.7 + 0.1 * k, [150, 130, 110, 90][k]), t0 + st * STEP, 0.4, 0.5 - k * 0.3)
        if e >= 4 and (bi['rel'] % 4 == 0):
            put('drums', I.crash(0.8), t0, 0.22)

    # ---- 军鼓滚奏（进入大段落前两小节）
    if bi['pre'] or ((b + 2) in sting_bars and sting_bars[b + 2]['id'] in ('title', 'combo')):
        nxt = sting_bars.get(b + 1) or sting_bars.get(b + 2)
        if nxt and nxt['id'] in ('title', 'combo', 'proc', 'rules', 'L3', 'L4', 'layers'):
            two = (b + 2) in sting_bars
            dens = [4, 8] if two else [8, 16]
            for half in range(2):
                d = dens[half]
                for k in range(d):
                    tt = t0 + half * BAR / 2 + k * (BAR / 2) / d
                    pos = (0 if two else 0.5) + (half * 0.5 + k / d * 0.5) * (0.5 if not two else 0.5)
                    put('drums', I.snare(0.4 + 0.6 * pos), tt, 0.16 + 0.22 * pos)

    # ---- arp
    if e >= 2:
        notes = sorted([p + 12 * o for p in pcs[:3] for o in (5, 6) if 64 <= p + 12 * o <= 88])
        pat = notes + notes[-2:0:-1]
        g = 0.10 if e == 2 else 0.12
        for st in range(16):
            if st >= mute_from: break
            if ht and st % 2: continue
            m = pat[(st + b * 3) % len(pat)]
            put('arp', I.pluck(midi(m), (0.85 if st % 4 == 0 else 0.6) * (0.85 + 0.3 * rng.random()), decay=0.22 if e < 4 else 0.18), t0 + st * STEP,
                g, 0.35 * np.sin(st * 0.8))

    # ---- strings ostinato
    if e >= 4:
        sr_ = 50 + ((root - 2) % 12)
        fig = [0, 0, 12, 0, 7, 0, 12, 7, 0, 0, 12, 0, 7, 12, 7, 0]
        for st in range(16):
            if st >= mute_from: break
            put('arp', I.string_stab(midi(sr_ + fig[st]), 0.8 if st % 4 == 0 else 0.55), t0 + st * STEP, 0.10, -0.3)

    # ---- choir
    if e >= 5 or sid in ('rules', 'quote'):
        for m in v:
            put('choir', I.choir(midi(m), BAR, 0.5, 'a' if e >= 4 else 'o'), t0, 0.16 if e >= 4 else 0.11)

    # ---- braam on phrase start in high energy
    if e >= 5 and bi['rel'] % 4 == 0:
        put('fx', I.braam(midi(26 + ((root - 2) % 12)), 1.0, 3.2), t0, 0.5)

    # ---- piano (hook / calm / quote / outro)
    if sid in ('hook', 'L2', 'quote', 'outro', 'L5'):
        lo = 38 + ((root - 2) % 12)
        put('keys', I.piano(midi(lo), 0.6 + 0.15 * rng.random(), BAR), t0 + rng.normal(0, 0.006), 0.5, -0.2)
        put('keys', I.piano(midi(lo + 7), 0.45 + 0.15 * rng.random(), BAR), t0 + 0.012 + rng.normal(0, 0.006), 0.35, -0.1)
        if sid in ('L2', 'quote', 'L5'):
            arp_n = v + [v[0] + 12]
            for k, st in enumerate((0, 3, 6, 8, 11, 14)):
                put('keys', I.piano(midi(arp_n[k % len(arp_n)] + 12), 0.35 + 0.2 * rng.random(), 0.8), t0 + st * STEP + rng.normal(0, 0.007), 0.30, 0.2)

# ---- hook：心跳、钟表、钢琴动机
hook = next(s for s in scenes if s['id'] == 'hook')
for k in range(int(hook['end'] / BEAT)):
    tt = k * BEAT
    if tt > hook['end'] - BAR / 2: break
    if tt >= 15 * BAR and k % 2 == 0:
        put('fx', I.tick(0.6 if k % 4 == 0 else 0.4), tt, 0.30, 0.25)
    if tt >= 17 * BAR and k % 4 == 0:
        put('drums', I.heartbeat(0.9), tt, 0.5)
hook_mel = [(2, 0, 74, 2), (2, 2, 81, 2), (3, 0, 79, 1.5), (3, 1.5, 77, 2.5), (5, 0, 77, 2), (5, 2, 76, 2), (6, 0, 74, 4),
            (8, 0, 74, 1.5), (8, 1.5, 81, 0.5), (8, 2, 81, 1), (8, 3, 79, .5), (8, 3.5, 77, .5), (9, 0, 77, 2), (9, 2, 76, 2)]
for bb, beat, m, d in hook_mel:
    hv = 0.62 + 0.25 * rng.random()
    put('keys', I.piano(midi(m), hv, d * BEAT), bb * BAR + beat * BEAT + rng.normal(0, 0.008), 0.55 * hv / 0.75, 0.15)
    put('keys', I.bell(midi(m + 12), 0.4, 2.0), bb * BAR + beat * BEAT, 0.08, 0.3)


def play_motif(start_bar, motif, inst='lead', gain=0.30, oct_=0):
    for k, barnotes in enumerate(motif):
        bt = 0.0
        for m, d in barnotes:
            tt = (start_bar + k) * BAR + bt * BEAT
            if inst == 'lead':
                put('lead', I.lead(midi(m + oct_), d * BEAT * 0.95, 0.9), tt, gain, -0.1)
                put('lead', I.lead(midi(m + oct_ - 12), d * BEAT * 0.95, 0.7, bright=2200), tt, gain * 0.5, 0.15)
            elif inst == 'bell':
                put('keys', I.bell(midi(m + oct_), 0.7, 2.2), tt, gain, 0.2)
                put('keys', I.piano(midi(m + oct_ - 12), 0.6, d * BEAT), tt, gain * 1.2, -0.1)
            bt += d


title_bar = int(round(next(s for s in scenes if s['id'] == 'title')['start'] / BAR))
play_motif(title_bar, MOTIF[:4], 'lead', 0.32)
combo = next(s for s in scenes if s['id'] == 'combo')
cb = int(round(combo['start'] / BAR))
play_motif(cb, MOTIF, 'lead', 0.20)
if (combo['end'] - combo['start']) / BAR >= 12:
    play_motif(cb + 8, MOTIF[:4], 'lead', 0.20, 12)
rules = next(s for s in scenes if s['id'] == 'rules')
rb = int(round(rules['start'] / BAR))
play_motif(rb, MOTIF_FIN * 3, 'lead', 0.14)
outro = next(s for s in scenes if s['id'] == 'outro')
ob = int(round(outro['start'] / BAR))
play_motif(ob, [[(74, 1.5), (81, .5), (81, 1), (79, .5), (77, .5)], [(78, 4)]], 'bell', 0.35)

# ---------------------------------------------------------------- transitions
PRE_GAPS = []
for b, s in sting_bars.items():
    tt = b * BAR
    big = s['id'] in ('title', 'combo', 'rules', 'proc', 'outro')
    gap = BEAT if big else 0.0
    put('fx', I.impact(1.0, 3.5), tt, 1.0 if big else 0.6)
    put('fx', I.metal_hit(1.0, 2.5), tt, 0.35 if big else 0.18)
    put('fx', I.crash(1.0, 3.0), tt, 0.40 if big else 0.25)
    put('fx', I.sub_drop(2.4, 1.0), tt, 0.75 if big else 0.35)
    if big:
        root = CH[bars[min(b, NB - 1)]['chord']][0]
        put('fx', I.braam(midi(26 + ((root - 2) % 12)), 1.0, 4.0), tt, 0.75)
        put('fx', I.braam(midi(38 + ((root - 2) % 12)), 1.0, 3.0), tt, 0.35)
        PRE_GAPS.append((tt - gap, tt))
    # 预备：反向镲 + 上升噪声（大段落在重拍前留出一拍空白）
    put('fx', I.reverse_cymbal(1.5, 1.0), tt - 1.5 - gap, 0.30)
    rlen = 2 * BAR if big else BAR
    put('fx', I.riser(rlen, 1.0), tt - rlen - gap, 0.26 if big else 0.13)
    put('fx', I.whoosh(0.9, 1.0), tt - 0.6 - gap, 0.18)

# ---------------------------------------------------------------- accents (卡点)
def sc_(sid):
    return next(s for s in scenes if s['id'] == sid)


def chord_at(t):
    return bars[min(int(t / BAR), NB - 1)]['chord']


def stab(t, gain=0.5, hi=False):
    pcs = CH[chord_at(t)]
    for m in voicing(pcs[:3], 55 if not hi else 62, 76 if not hi else 82):
        put('acc', I.string_stab(midi(m), 1.0, 0.22), t, gain * 0.5)
        put('acc', I.string_stab(midi(m - 12), 0.9, 0.22), t, gain * 0.35)
    put('acc', I.taiko(0.6, 1.2), t, gain * 0.5)


def blip(t, k=0, gain=0.5):
    pcs = CH[chord_at(t)]
    scale = sorted([p + 12 * o for p in pcs for o in (5, 6) if 67 <= p + 12 * o <= 88])
    m = scale[k % len(scale)]
    put('acc', I.blip(midi(m), 1.0), t, gain * 0.8, 0.3 * np.sin(k * 1.7))
    put('acc', I.pluck(midi(m), 0.8, 0.35, 3000, 400), t, gain * 0.35, 0.3 * np.sin(k * 1.7))
    put('acc', I.bell(midi(m - 12), 0.4, 1.4), t, gain * 0.2, 0.3 * np.sin(k * 1.7))


def hit(t, gain=0.6):
    put('acc', I.taiko(1.0), t, gain * 0.7)
    put('acc', I.impact(0.6, 1.5), t, gain * 0.35)
    stab(t, gain * 0.8)


def neg(t, gain=0.6):
    put('acc', tanh_sat(I.taiko(1.0, 0.7) * 2.0, 2.5) * 0.6, t, gain * 0.7)
    put('acc', I.sub_drop(1.2, 1.0), t, gain * 0.6)
    for m in (50, 51, 57):  # 小二度不协和
        put('acc', I.string_stab(midi(m), 1.0, 0.3), t, gain * 0.25)


def boom(t, gain=0.8):
    put('acc', I.impact(1.0, 3.0), t, gain)
    put('acc', I.crash(1.0, 2.5), t, gain * 0.3)
    put('acc', I.sub_drop(2.0), t, gain * 0.5)


BRAAM_N = [0]


def braam_hit(t, gain=0.6):
    root = CH[chord_at(t)][0]
    v = BRAAM_N[0] % 3; BRAAM_N[0] += 1
    put('acc', I.braam(midi(26 + ((root - 2) % 12)), 1.0, 2.5), t, gain * 0.8)
    if v == 1: put('acc', I.braam(midi(38 + ((root - 2) % 12)), 1.0, 2.0), t, gain * 0.45)
    if v == 2: put('acc', I.braam(midi(33 + ((root - 2) % 12)), 1.0, 2.2), t, gain * 0.45)
    put('acc', I.whoosh(0.5, 1.0, True), t - 0.45, gain * 0.35)
    put('acc', I.impact(0.8, 2.0), t, gain * 0.4)
    put('acc', I.crash(0.8, 2.0), t, gain * 0.2)


def whoosh_at(t, gain=0.4, up=False):
    put('acc', I.whoosh(0.7, 1.0, up), t - 0.35, gain)


ACC = {
    'hook': [('see', 'blip0'), ('see2', 'blip2'), ('see3', 'braam'), ('air', 'neg'), ('air2', 'neg'), ('vs', 'stab'), ('why', 'hit')],
    'formula': [('ep', 'blip0'), ('ic', 'blip2'), ('sum', 'blip3'), ('iv', 'stab'), ('ps', 'blip4')],
    'block': [('draw', 'whoosh'), ('x', 'blip0'), ('y', 'blip2'), ('z', 'blip4'), ('vol', 'braam'),
              ('h', 'hit'), ('m', 'hit'), ('d', 'hit'), ('l', 'hit'), ('cut', 'neg')],
    'map': [('l0', 'hit'), ('l1', 'hit'), ('l2', 'hit'), ('l3', 'hit'), ('l4', 'hit'), ('l5', 'hit')],
    'L0': [('die', 'boom'), ('m', 'neg'), ('knife', 'whoosh'), ('k2', 'boom'), ('d1', 'hit'), ('d2', 'neg'), ('d3', 'neg'),
           ('d4', 'neg'), ('d5', 'neg'), ('veto', 'boom')],
    'stick': [('wtp', 'blip4'), ('wts', 'blip1'), ('cs', 'stab'), ('ss', 'stab'), ('fp', 'hit'), ('av', 'braam'), ('av2', 'neg')],
    'loom': [('loom', 'blip0'), ('down', 'whoosh'), ('pv', 'neg'), ('nv', 'stab'), ('ap', 'stab')],
    'moat': [('moat', 'braam'), ('px', 'hit'), ('r1', 'blip1'), ('r2', 'blip3'), ('trap', 'neg'), ('base', 'stab')],
    'L2': [('see', 'blip2'), ('oe1', 'blip0'), ('oe2', 'blip2'), ('oe3', 'blip4'), ('shave', 'whoosh'), ('fab', 'neg'), ('gap', 'neg')],
    'L3': [('thick', 'braam'), ('a1', 'stab'), ('a2', 'stab'), ('a3', 'stab'), ('k1', 'hit'), ('k2', 'hit'), ('k5', 'neg')],
    'kitty': [('shot', 'scratch'), ('cow1', 'stab')],
    'L4': [('amp', 'hit'), ('lev', 'blip2'), ('risk', 'neg'), ('fl1', 'stab'), ('fl2', 'neg'), ('bb1', 'stab'), ('bb2', 'neg')],
    'gov': [('inc', 'hit'), ('inc1', 'neg'), ('inc2', 'stab'), ('cut', 'neg'), ('kr', 'boom')],
    'L5': [('fade', 'whoosh'), ('cap', 'stab'), ('m1', 'stab'), ('m2', 'neg'), ('m3', 'neg'), ('hard', 'blip3')],
    'combo': [('all', 'braam'), ('c1', 'braam'), ('c2', 'neg'), ('c3', 'braam'), ('c4', 'neg'), ('c5', 'braam'), ('c6', 'neg')],
    'proc': [('p1', 'blip0'), ('p2', 'blip1'), ('p3', 'blip2'), ('p4', 'blip3'), ('p5', 'blip4'), ('p6', 'blip5'), ('p7', 'blip6'), ('p8', 'hit')],
    'tests': [('t1', 'hit'), ('t2', 'hit'), ('t3', 'hit'), ('t4', 'hit'), ('t5', 'hit')],
    'rules': [('r1', 'stab'), ('r2', 'stab'), ('r3', 'stab'), ('r4', 'stab'), ('r5', 'hit')],
}
for sid, lst in ACC.items():
    s = sc_(sid)
    for cue, kind in lst:
        if cue not in s['cq']: print('missing cue', sid, cue); continue
        t = s['cq'][cue]
        if kind.startswith('blip'): blip(t, int(kind[4:]), 0.45)
        elif kind == 'stab': stab(t, 0.5)
        elif kind == 'hit': hit(t, 0.55)
        elif kind == 'neg': neg(t, 0.55)
        elif kind == 'boom': boom(t, 0.75)
        elif kind == 'braam': braam_hit(t, 0.6)
        elif kind == 'whoosh': whoosh_at(t, 0.45)
        elif kind == 'scratch':
            put('acc', I.scratch(1.0), t - 0.1, 0.5)
            boom(t + BEAT, 0.6)

# 「打下来」之后整体急停半小节
kit = sc_('kitty')
STOPS = [(kit['cq']['shot'] - 0.05, kit['cq']['shot'] + BEAT * 1.0)]
# L0 一票否决后：只剩氛围
L0s = sc_('L0')
STOPS.append((L0s['cq']['veto'] - BEAT * 0.5, L0s['cq']['veto']))

STOPS += PRE_GAPS
KICKS = [(t, v) for t, v in KICKS if not any(a <= t < b for a, b in PRE_GAPS)]
np.save(os.path.join(WORK, 'kicks.npy'), np.array(KICKS))


# ---------------------------------------------------------------- mix
def sidechain(depth=0.55, rel=0.16):
    g = np.ones(N, np.float32)
    tt = np.arange(int(0.6 * SR)) / SR
    shape = 1 - depth * np.exp(-tt / rel) * np.minimum(tt / 0.004, 1)
    for t, v in KICKS:
        i = int(t * SR)
        n = min(len(shape), N - i)
        if n <= 0: continue
        g[i:i + n] = np.minimum(g[i:i + n], 1 - (1 - shape[:n]) * min(v, 1))
    return g


def run():
    sc = sidechain()
    for k, d in (('pad', 0.55), ('bass', 0.6), ('arp', 0.35), ('choir', 0.4)):
        BUS[k] *= (1 - (1 - sc) * d / 0.55)[:, None]
    # 急停
    for a, b in STOPS:
        i, j = int(a * SR), int(b * SR)
        f = int(0.01 * SR)
        for k in BUS:
            if k in ('acc',): continue
            BUS[k][i:j] *= 0.0
            BUS[k][j:j + f] *= np.linspace(0, 1, f)[:, None]
    hall = make_ir(3.2, 0.03, 5000, seed=2)
    room = make_ir(0.9, 0.01, 7000, seed=3)
    # 均衡
    BUS['pad'] = sos_filter(BUS['pad'], 'highpass', 180)
    BUS['arp'] = sos_filter(BUS['arp'], 'highpass', 300)
    BUS['choir'] = sos_filter(BUS['choir'], 'highpass', 200)
    BUS['lead'] = sos_filter(BUS['lead'], 'highpass', 200)
    BUS['bass'] = sos_filter(BUS['bass'], 'lowpass', 2500)
    BUS['keys'] = shelf(BUS['keys'], 3000, -3.0, 'high')
    BUS['acc'] = shelf(BUS['acc'], 6000, -3.0, 'high')
    arp_dly = delay(BUS['arp'], BEAT * 0.75, BEAT * 0.5, 0.35, 6)
    lead_dly = delay(BUS['lead'], BEAT * 0.75, BEAT * 0.75, 0.25, 4)
    send = (BUS['pad'] * 0.25 + BUS['arp'] * 0.3 + arp_dly * 0.3 + BUS['keys'] * 0.4 + BUS['lead'] * 0.3 +
            BUS['choir'] * 0.5 + BUS['fx'] * 0.35 + BUS['acc'] * 0.3 + BUS['drums'] * 0.06)
    wet = reverb(send, hall, 1.0)
    wet_room = reverb(BUS['drums'] * 0.3 + BUS['kick'] * 0.05, room, 1.0)
    drums = compress(BUS['kick'] + BUS['drums'] + wet_room, -14, 3, 0.003, 0.08, 2)
    drums = peak(drums, 320, -3.0, 1.0)
    drums = shelf(drums, 60, 2.0, 'low')
    drums = shelf(drums, 11000, -3.0, 'high')
    # pad 加宽：右声道 Haas 延迟
    d = int(0.011 * SR)
    BUS['pad'][d:, 1] = BUS['pad'][:-d, 1].copy()
    music = (drums + BUS['bass'] + BUS['pad'] + BUS['arp'] + arp_dly * 0.6 + BUS['keys'] + BUS['lead'] + lead_dly * 0.5 +
             BUS['choir'] + BUS['fx'] + wet)
    # 段落动态：能量越高越响（dB）
    gdb = np.array([-7.0, -6.0, -4.5, -2.5, 0.0, 1.5])
    g = np.zeros(N, np.float32)
    for bi in bars:
        i0, i1 = int(bi['t'] * SR), int((bi['t'] + BAR) * SR)
        g[i0:i1] = gdb[bi['e']]
    g[int(NB * BAR * SR):] = gdb[2]
    from scipy.ndimage import uniform_filter1d
    g = uniform_filter1d(g, int(0.25 * SR))
    music *= (10 ** (g / 20))[:, None]
    music = sos_filter(music, 'highpass', 28)
    music = shelf(music, 9000, -2.5, 'high')
    acc = BUS['acc']
    stems = dict(music=music, acc=acc)
    np.savez(os.path.join(WORK, 'music_stems.npz'), **{k: v.astype(np.float32) for k, v in stems.items()})
    m = music + acc
    m = m / (np.abs(m).max() + 1e-9) * 0.9
    sf.write(os.path.join(WORK, 'music.wav'), m[:int(TOTAL * SR)], SR, subtype='PCM_16')
    print('music done', m.shape[0] / SR)


if __name__ == '__main__':
    run()
