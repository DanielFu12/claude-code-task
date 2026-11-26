"""第八期配乐（第三版，整体重写）：按旁白时间线写 MIDI + 程序合成的电影音效层，MuseScore General 音色库渲染。

为什么重写：第二版全片一个速度（80 BPM）、一个调（D 小调）、一个四音动机循环，听感单调、催眠。这一版的原则：
  · 跟着故事走：每章有自己的调、速度和织体（开场的紧张脉冲、身世的温暖钢琴、交易的律动、护城河的驱动弦乐、
    出走的阴暗心跳、扩张的颂歌、收获的层层推进），章与章之间用“上扬 + 重拍”衔接，不掉黑、不硬切；
  · 一条主题旋律贯穿全片，但每次换配器、换调、换节奏出现（钢琴 → 铜管 → 钟琴 → 弦乐与合唱），有记忆点又不重复；
  · 卡点：揭晓、转折、数字落地的那个字上重拍；重拍前半拍到一拍“抽空”（静音），制造期待；引语卡与原声下面只留铺底；
  · 能量曲线：每段有起点能量与终点能量，配器随能量加减（鼓组、十六分音型、铜管、合唱逐层进入）。
旁白时由 audio_mix.py 做闪避，这里只管音乐本身的起伏。
python3 src/score.py WORK   → WORK/music/score.mid、score_raw.wav、beats.json
"""
import sys, os, json, subprocess, math
import numpy as np
import pretty_midi as pm
import soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve

WORK = sys.argv[1] if len(sys.argv) > 1 else 'work'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES

TL = json.load(open(os.path.join(WORK, 'timeline.json')))
SEG = {s['id']: s for s in TL['segs']}
CH = TL['chapters']
SAY = {l[0]: (l[3] or l[2]) for l in LINES}
SF = next(p for p in ('/usr/share/sounds/sf3/MuseScore_General_Full.sf3', '/usr/share/sounds/sf2/FluidR3_GM.sf2') if os.path.exists(p))
SR = 48000
T_END = TL['total']


def S(i): return SEG[i]['start']
def E(i): return SEG[i]['start'] + SEG[i]['dur']


def WT(i, sub):
    s = SAY[i]; k = s.find(sub)
    if k < 0: raise KeyError((i, sub))
    for idx, tt in SEG[i]['ct']:
        if idx >= k: return S(i) + tt
    return S(i) + SEG[i]['dur'] * k / len(s)


# ------------------------------------------------------------------ 乐理
PC = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'Ab': 8, 'A': 9, 'Bb': 10, 'B': 11}
SCALE = {'major': [0, 2, 4, 5, 7, 9, 11], 'minor': [0, 2, 3, 5, 7, 8, 10]}
ROMAN = {'i': 0, 'ii': 1, 'iii': 2, 'iv': 3, 'v': 4, 'vi': 5, 'vii': 6}


def chord_pcs(key, mode, rn):
    """罗马数字 → (根音 pc, [三和弦 pc])；大写为大三和弦、小写为小三和弦；后缀 sus4 / 7"""
    base = rn.rstrip('74sus')
    sus = rn.endswith('sus4'); sev = rn.endswith('7') and not sus
    deg = ROMAN[base.lower()]
    root = (PC[key] + SCALE[mode][deg]) % 12
    third = 4 if base.isupper() else 3
    pcs = [root, (root + (5 if sus else third)) % 12, (root + 7) % 12]
    if sev: pcs.append((root + 10) % 12)
    return root, pcs


def pitch_near(pc, lo):
    """不低于 lo 的、音级为 pc 的最低音"""
    p = lo + ((pc - lo) % 12)
    return p


def voice(pcs, lo, n):
    out = []; p = lo
    while len(out) < n:
        if p % 12 in pcs: out.append(p)
        p += 1
    return out


def scale_pitch(key, mode, deg, octave_base):
    """音阶级数（可跨八度，0 = 主音）→ MIDI 音高"""
    o, d = divmod(deg, 7)
    return octave_base + PC[key] + SCALE[mode][d] + 12 * o


# 全片主题（两小节，级数 + 拍数）：上行的“希望”音型，落在 3 级
THEME = [(4, 1.0), (2, 0.5), (3, 0.5), (4, 1.0), (7, 1.0), (6, 1.5), (4, 0.5), (2, 2.0)]
THEME_B = [(4, 1.0), (5, 0.5), (4, 0.5), (2, 1.0), (0, 1.0), (1, 1.5), (2, 0.5), (4, 2.0)]   # 应答句

# ------------------------------------------------------------------ 乐器（GM 音色号）
INS = {'piano': 0, 'epiano': 4, 'celesta': 8, 'glock': 9, 'marimba': 12, 'strings': 48, 'slowstr': 49, 'synstr': 50,
       'choir': 52, 'orchhit': 48, 'trumpet': 56, 'trombone': 57, 'tuba': 58, 'horn': 60, 'brass': 61, 'pizz': 45,
       'harp': 46, 'timp': 47, 'contra': 43, 'cello': 42, 'fbass': 33, 'sbass': 33, 'pad': 48, 'sweep': 49,
       'lead': 46, 'taiko': 116, 'revcym': 119, 'pluck': 25}
MID = pm.PrettyMIDI(initial_tempo=120)
TR = {}
MUTES = []                       # (a, b)：这段时间里不起新音、旧音截断（重拍前的“抽空”）
EVENTS = {'hits': [], 'soft': [], 'beats': []}


def tr(name):
    if name not in TR:
        TR[name] = pm.Instrument(program=0 if name == 'drums' else INS[name], name=name, is_drum=(name == 'drums'))
        MID.instruments.append(TR[name])
    return TR[name]


def muted(t):
    return any(a <= t < b for a, b in MUTES)


def note(ins, p, t0, t1, v, force=False):
    if t1 <= t0 + 0.01 or t0 < 0 or t0 >= T_END: return
    if not force and muted(t0): return
    for a, b in MUTES:                                   # 截断到抽空开始
        if t0 < a < t1 and not force: t1 = a
    v = int(max(1, min(127, v)))
    tr(ins).notes.append(pm.Note(v, int(p), float(t0), float(min(t1, T_END + 2))))


DR = {'kick': 36, 'snare': 38, 'rim': 37, 'clap': 39, 'hat': 42, 'phat': 44, 'ohat': 46, 'crash': 49, 'ride': 51,
      'tom1': 50, 'tom2': 47, 'tom3': 43, 'tamb': 54, 'shaker': 70, 'splash': 55, 'crash2': 57}


NOISY = {'hat', 'phat', 'ohat', 'shaker', 'tamb', 'ride', 'crash', 'crash2', 'splash', 'snare', 'clap', 'rim'}   # v4：不要沙沙声、刷声（用户要求）


def drum(n, t, v, force=False):
    if n in NOISY: return
    note('drums', DR[n], t, t + 0.12, v, force)


# ------------------------------------------------------------------ 程序合成音效层（48 kHz 立体声）
FX = np.zeros((int((T_END + 4) * SR), 2), np.float32)
RNG = np.random.default_rng(8)


def fx_add(t, y, gain=1.0):
    i = int(t * SR)
    if i < 0: y = y[-i:]; i = 0
    j = min(i + len(y), len(FX))
    if j > i: FX[i:j] += y[:j - i] * gain


def impact(size=1.0):
    """电影式重拍：次低频下滑 + 低频噪声爆破 + 一点高频瞬态，约 2.4 s"""
    n = int(2.4 * SR); tt = np.arange(n) / SR
    f = 30 + 45 * np.exp(-tt * 7)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * (2.2 / size))
    y = sub * 0.8 * size                                   # v4：只留次低频“咚”，去掉噪声爆破和高频瞬态
    return np.stack([y, y * 0.97], 1).astype(np.float32)


def riser(dur):
    """噪声上扬：带通中心 250 Hz → 7 kHz，音量指数上升，在重拍处戛然而止（交给重拍）"""
    n = int(dur * SR); tt = np.arange(n) / SR; u = tt / dur
    nz = RNG.standard_normal((n, 2))
    out = np.zeros((n, 2))
    blk = 2048
    for k in range(0, n, blk):
        fc = 250 * (7000 / 250) ** (u[k])
        sos = butter(2, [fc * 0.7, min(fc * 1.4, SR / 2 - 100)], 'bandpass', fs=SR, output='sos')
        out[k:k + blk] = sosfilt(sos, nz[k:k + blk], axis=0)
    tone = np.sin(2 * np.pi * np.cumsum(180 * 4 ** u) / SR) * 0.15
    env = (u ** 2.2)
    y = (out * 1.3 + tone[:, None]) * env[:, None]
    y[-int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))[:, None]
    return y.astype(np.float32)


def whoosh(dur=0.7):
    n = int(dur * SR); tt = np.arange(n) / SR; u = tt / dur
    nz = sosfilt(butter(2, [400, 3000], 'bandpass', fs=SR, output='sos'), RNG.standard_normal((n, 2)), axis=0)
    env = np.sin(np.pi * u) ** 2
    return (nz * env[:, None] * 0.6).astype(np.float32)


# ------------------------------------------------------------------ 事件
def hit(t, key, mode, rn='i', size=1.0, dark=False):
    """重拍：音效重拍 + 定音鼓 + 镲 + 低音铜管/弦乐长音（size<0.7 为“轻点”：不出镲与乐队齐奏）"""
    EVENTS['hits' if size >= 0.7 else 'soft'].append(round(t, 3))
    fx_add(t - 0.005, impact(size), 0.36 if size >= 0.7 else 0.2)
    root, pcs = chord_pcs(key, mode, rn)
    note('timp', pitch_near(root, 38), t, t + 2.5, 70 + 40 * size, True)
    note('taiko', 50, t, t + 1.2, 60 + 50 * size, True)
    if size >= 0.7:
        drum('crash', t, 80 + 30 * size, True)
        if not dark: drum('crash2', t, 70 + 30 * size, True)
        for p in voice(pcs, 53, 3): note('brass', p, t, t + 1.6 + size, 62 + 36 * size, True)
        for p in voice(pcs, 60, 4): note('strings', p, t, t + 2.0 + size, 60 + 40 * size, True)
        for p in voice(pcs, 72, 3): note('strings', p, t, t + 2.0 + size, 50 + 40 * size, True)
        note('contra', pitch_near(root, 28), t, t + 2.5, 90, True)
        if size >= 1.1:
            for p in voice(pcs, 72, 3): note('glock', p, t, t + 1.2, 80, True)
    else:
        for p in voice(pcs, 60, 3): note('harp', p, t, t + 1.5, 60, True)


def drop(t, length):
    """重拍前抽空：t - length 到 t 之间静音（重拍本身照常）"""
    MUTES.append((t - length, t - 0.002))


def rise(t_end, dur, snare=True, key='D', mode='major'):
    """v4：纯乐音的上扬——弦乐十六分音符沿音阶爬升、渐强 + 定音鼓滚奏 + 铜管长音渐强；不用噪声、反向镲"""
    beat = 0.125; n = int(dur / beat); t0 = t_end - n * beat
    for k in range(n):
        u = k / max(n - 1, 1); tt = t0 + k * beat
        deg = int(u * 9)
        note('strings', scale_pitch(key, mode, deg, 64), tt, tt + beat * 0.9, 40 + 70 * u, True)
        note('strings', scale_pitch(key, mode, deg, 76), tt, tt + beat * 0.9, 30 + 60 * u, True)
        if snare: note('timp', scale_pitch(key, mode, 0, 38), tt, tt + beat, 30 + 75 * u, True)
    root = scale_pitch(key, mode, 4, 55)
    for j in range(4):
        tt = t_end - dur + j * dur / 4
        note('brass', root, tt, tt + dur / 4, 45 + 18 * j, True)


# ------------------------------------------------------------------ 织体（每小节调用一次）
def theme_bar(sec, bar_t, beat, k, ins, octave, vel, phrase=None):
    """主题：两小节一句；k 为本段小节序号；偶数句用 THEME、奇数句用应答句"""
    ph = phrase or (THEME if (k // 2) % 2 == 0 else THEME_B)
    half = k % 2
    t = bar_t - half * 4 * beat
    acc = 0.0
    for deg, d in ph:
        st = t + acc * beat; acc += d
        if bar_t - 1e-6 <= st < bar_t + 4 * beat - 1e-6:
            note(ins, scale_pitch(sec['key'], sec['mode'], deg, octave), st, st + d * beat * 0.95, vel)


def st_pad(sec, b, beat, rn, e, k):
    root, pcs = chord_pcs(sec['key'], sec['mode'], rn)
    L = 4 * beat * sec['bpc']
    if k % sec['bpc']: return
    for p in voice(pcs, 52, 4): note('pad', p, b, b + L + 0.3, 40 + 40 * e)
    for p in voice(pcs, 48, 3): note('slowstr', p, b, b + L + 0.3, 30 + 45 * e)
    note('contra', pitch_near(root, 31), b, b + L, 40 + 40 * e)
    if sec.get('theme') and e > 0.25: theme_bar(sec, b, beat, k, sec.get('theme_ins', 'piano'), 72, 45 + 35 * e)


def st_warm(sec, b, beat, rn, e, k):
    root, pcs = chord_pcs(sec['key'], sec['mode'], rn)
    r = pitch_near(root, 45); th = pitch_near(pcs[1], r + 3); fi = pitch_near(pcs[2], r + 5)
    patt = [r, fi, r + 12, th + 12, fi + 12, th + 12, r + 12, fi]
    for j, p in enumerate(patt):
        note('piano', p, b + j * beat / 2, b + j * beat / 2 + beat * 0.9, 42 + 38 * e - (8 if j % 2 else 0))
    if k % 2 == 0:
        for p in voice(pcs, 55, 3): note('slowstr', p, b, b + 8 * beat + 0.2, 25 + 50 * e)
        note('cello', pitch_near(root, 36), b, b + 8 * beat, 40 + 40 * e)
    if e > 0.45:
        drum('kick', b, 50 + 40 * e); drum('kick', b + 2 * beat, 45 + 40 * e)
        for j in range(8): drum('shaker', b + j * beat / 2, 15 + 18 * e)
        drum('rim', b + beat, 40 + 30 * e); drum('rim', b + 3 * beat, 40 + 30 * e)
    if sec.get('theme') and k % 4 < 2: theme_bar(sec, b, beat, k, sec.get('theme_ins', 'piano'), 72, 55 + 35 * e)


def st_pulse(sec, b, beat, rn, e, k):
    root, pcs = chord_pcs(sec['key'], sec['mode'], rn)
    bp = pitch_near(root, 33)
    for j in range(8):
        acc = 1.0 if j in (0, 3, 6) else 0.7
        note('sbass', bp + (12 if j == 7 and e > 0.5 else 0), b + j * beat / 2, b + j * beat / 2 + beat * 0.42, (55 + 45 * e) * acc)
    if k % 2 == 0:
        for p in voice(pcs, 50, 3): note('pad', p, b, b + 8 * beat + 0.2, 35 + 40 * e)
    if e > 0.3:
        for j in range(16):
            if e > 0.5 or j % 2 == 0: drum('hat', b + j * beat / 4, (15 + 24 * e) * (1.25 if j % 4 == 2 else 1))
    drum('kick', b, 60 + 50 * e)
    if e > 0.5: drum('kick', b + 2 * beat, 55 + 45 * e); drum('kick', b + 2.75 * beat, 40 + 40 * e)
    if e > 0.6: drum('clap', b + beat, 40 + 40 * e); drum('clap', b + 3 * beat, 40 + 40 * e)
    if e > 0.55 and k % 4 == 3:
        for j, n in enumerate(('tom1', 'tom2', 'tom3', 'tom3')): drum(n, b + 3 * beat + j * beat / 4, 70 + 40 * e)
    # 高音钢琴：主音/五音的冷峻点子
    hi = voice(pcs, 76, 3)
    for j, bt in enumerate((0, 1.5, 3)):
        note('piano', hi[(k + j) % 3], b + bt * beat, b + bt * beat + beat * 0.8, 35 + 35 * e)
    if sec.get('theme') and e > 0.35 and k % 4 >= 2: theme_bar(sec, b, beat, k, sec.get('theme_ins', 'piano'), 72, 50 + 35 * e)


def st_groove(sec, b, beat, rn, e, k):
    root, pcs = chord_pcs(sec['key'], sec['mode'], rn)
    for bt in (0, 1.5, 2.5): drum('kick', b + bt * beat, 70 + 40 * e)
    for bt in (1, 3): drum('snare', b + bt * beat, 55 + 45 * e); drum('clap', b + bt * beat, 40 + 40 * e)
    sub = 4 if e > 0.68 else 2
    for j in range(4 * sub): drum('hat', b + j * beat / sub, (21 + 25 * e) * (1.2 if j % sub == 0 else 0.85))
    if e > 0.5: drum('ohat', b + 3.5 * beat, 45 + 30 * e)
    if k % 4 == 3 and e > 0.55:
        drum('snare', b + 3.5 * beat, 60 + 30 * e); drum('snare', b + 3.75 * beat, 70 + 30 * e)
    bp = pitch_near(root, 36)
    for bt, p, d in ((0, bp, 0.9), (0.75, bp, 0.3), (1.5, bp + 7, 0.5), (2.5, bp + 12, 0.4), (3, bp + 10 if sec['mode'] == 'minor' else bp + 7, 0.5), (3.5, bp, 0.4)):
        note('fbass', p, b + bt * beat, b + (bt + d) * beat, 70 + 35 * e)
    ch = voice(pcs, 60, 4)
    for bt in (0.5, 1.5, 2.5, 3.5) if e > 0.45 else (0, 2):
        for p in ch: note('epiano', p, b + bt * beat, b + bt * beat + beat * 0.45, 35 + 35 * e)
    if e > 0.6:
        arp = voice(pcs, 76, 6)
        for j in range(16):
            note('pluck' if sec['mode'] == 'major' else 'pizz', arp[(j * 2 + k) % len(arp)], b + j * beat / 4, b + j * beat / 4 + beat * 0.2, 30 + 30 * e)
    if sec.get('theme') and k % 4 >= 2: theme_bar(sec, b, beat, k, sec.get('theme_ins', 'glock'), 84, 55 + 35 * e)


def st_drive(sec, b, beat, rn, e, k):
    root, pcs = chord_pcs(sec['key'], sec['mode'], rn)
    r = pitch_near(root, 48)
    patt = [r, r + 7, r + 12, r + 7, r + 3 if sec['mode'] == 'minor' else r + 4, r + 7, r + 12, r + 15 if sec['mode'] == 'minor' else r + 16]
    for j in range(16):
        note('strings', patt[j % 8], b + j * beat / 4, b + j * beat / 4 + beat * 0.2, (48 + 42 * e) * (1.15 if j % 4 == 0 else 0.9))
    for j in range(8): note('sbass', pitch_near(root, 33), b + j * beat / 2, b + j * beat / 2 + beat * 0.4, 55 + 45 * e)
    for j in range(4): drum('kick', b + j * beat, 65 + 45 * e)
    if e > 0.5: note('taiko', 48, b, b + 0.8, 55 + 50 * e)
    if e > 0.62: drum('snare', b + beat, 55 + 45 * e); drum('snare', b + 3 * beat, 55 + 45 * e)
    for j in range(8): drum('hat', b + j * beat / 2 + beat / 4, 20 + 21 * e)
    if e > 0.72:
        for p in voice(pcs, 55, 3): note('brass', p, b, b + beat * 1.2, 60 + 45 * e)
    if k % 4 == 0 and e > 0.6: drum('crash', b, 60 + 30 * e)
    if sec.get('theme') and e > 0.65 and k % 4 >= 2: theme_bar(sec, b, beat, k, sec.get('theme_ins', 'horn'), 60, 60 + 35 * e)


def st_dark(sec, b, beat, rn, e, k):
    root, pcs = chord_pcs(sec['key'], sec['mode'], rn)
    if k % 2 == 0:
        note('slowstr', pitch_near(root, 36), b, b + 8 * beat + 0.2, 45 + 40 * e)
        note('slowstr', pitch_near((root + 7) % 12, 43), b, b + 8 * beat + 0.2, 40 + 35 * e)
        note('sweep', pitch_near(pcs[1], 55), b, b + 8 * beat + 0.3, 30 + 35 * e)
        note('contra', pitch_near(root, 28), b, b + 8 * beat, 50 + 40 * e)
    drum('kick', b, 55 + 40 * e); drum('kick', b + 0.35 * beat, 40 + 35 * e)          # 心跳
    if e > 0.45: drum('kick', b + 2 * beat, 50 + 40 * e); drum('kick', b + 2.35 * beat, 35 + 35 * e)
    if k % 2 == 1:                                                                     # 不协和的钢琴点子
        p = pitch_near(root, 72)
        note('piano', p, b + 2 * beat, b + 3.8 * beat, 40 + 30 * e); note('piano', p + 1, b + 2.5 * beat, b + 3.8 * beat, 30 + 25 * e)
    if e > 0.5 and k % 4 == 3:
        for j in range(12): note('timp', pitch_near(root, 38), b + 3 * beat + j * beat / 12, b + 3 * beat + (j + 1) * beat / 12, 30 + 6 * j)
    if e > 0.55:
        for j in range(8): drum('phat', b + j * beat / 2, 18 + 20 * e)


def st_pizz(sec, b, beat, rn, e, k):
    """俏皮：拨弦 + 钟琴 + 轻军鼓（开到隔壁）"""
    root, pcs = chord_pcs(sec['key'], sec['mode'], rn)
    bp = pitch_near(root, 40)
    for j, bt in enumerate((0, 1, 2, 3)): note('pizz', bp + (7 if j % 2 else 0), b + bt * beat, b + bt * beat + beat * 0.3, 90 + 30 * e)
    note('contra', pitch_near(root, 28), b, b + 4 * beat, 55 + 30 * e)
    ch = voice(pcs, 60, 3)
    for bt in (0.5, 1.5, 2.5, 3.5):
        for p in ch: note('pizz', p, b + bt * beat, b + bt * beat + beat * 0.25, 72 + 30 * e)
    for p in voice(pcs, 55, 3): note('slowstr', p, b, b + 4 * beat, 30 + 25 * e)
    drum('rim', b + beat, 50 + 30 * e); drum('rim', b + 3 * beat, 50 + 30 * e); drum('kick', b, 50 + 30 * e)
    for j in range(8): drum('shaker', b + j * beat / 2, 18 + 15 * e)
    if k % 2 == 1: theme_bar(sec, b, beat, k, 'glock', 84, 70 + 30 * e)


def st_anthem(sec, b, beat, rn, e, k):
    root, pcs = chord_pcs(sec['key'], sec['mode'], rn)
    for j in range(4): drum('kick', b + j * beat, 70 + 45 * e)
    if e > 0.55: drum('kick', b + 2.5 * beat, 60 + 40 * e)
    for bt in (1, 3): drum('snare', b + bt * beat, 70 + 45 * e); drum('clap', b + bt * beat, 50 + 40 * e)
    for j in range(8): drum('hat', b + j * beat / 2, 25 + 25 * e)
    if k % 4 == 0: drum('crash', b, 70 + 40 * e)
    if k % 4 == 3 and e > 0.6:
        for j, n in enumerate(('tom1', 'tom1', 'tom2', 'tom2', 'tom3', 'tom3', 'snare', 'snare')): drum(n, b + 2 * beat + j * beat / 4, 70 + 45 * e)
    for j in range(8): note('sbass', pitch_near(root, 33) + (12 if j % 2 else 0), b + j * beat / 2, b + j * beat / 2 + beat * 0.42, 60 + 45 * e)
    for p in voice(pcs, 55, 4): note('strings', p, b, b + 4 * beat, 45 + 45 * e)
    for j in range(8):
        for p in voice(pcs, 60, 3): note('strings', p + 12, b + j * beat / 2, b + j * beat / 2 + beat * 0.3, (35 + 40 * e) * (1.2 if j % 2 == 0 else 0.8))
    if e > 0.55:
        for p in voice(pcs, 52, 3): note('brass', p, b, b + 2 * beat, 55 + 45 * e)
    if e > 0.7:
        arp = voice(pcs, 72, 6)
        for j in range(16): note('lead', arp[(j + k) % 6], b + j * beat / 4, b + j * beat / 4 + beat * 0.2, 25 + 30 * e)
        for p in voice(pcs, 60, 3): note('choir', p, b, b + 4 * beat, 35 + 40 * e)
    if sec.get('theme'):
        theme_bar(sec, b, beat, k, 'strings', 72, 62 + 40 * e)
        if k % 4 >= 2: theme_bar(sec, b, beat, k, sec.get('theme_ins', 'horn'), 60, 70 + 40 * e)


def st_emotional(sec, b, beat, rn, e, k):
    root, pcs = chord_pcs(sec['key'], sec['mode'], rn)
    r = pitch_near(root, 43)
    for j, p in enumerate((r, r + 7, r + 12 + (4 if sec['mode'] == 'major' else 3), r + 19)):
        note('piano', p, b + j * beat * 0.5, b + 4 * beat, 45 + 30 * e)
    for p in voice(pcs, 55, 4): note('slowstr', p, b, b + 4 * beat + 0.2, 30 + 50 * e)
    note('cello', pitch_near(root, 36), b, b + 4 * beat, 40 + 40 * e)
    if e > 0.45:
        for p in voice(pcs, 60, 3): note('choir', p, b, b + 4 * beat + 0.2, 25 + 45 * e)
    if e > 0.6:
        note('timp', pitch_near(root, 38), b, b + beat, 50 + 40 * e)
        drum('kick', b, 50 + 40 * e)
    if sec.get('theme', True):
        theme_bar(sec, b, beat, k, sec.get('theme_ins', 'piano' if e < 0.5 else 'horn'), 72 if e < 0.5 else 60, 55 + 40 * e)


STYLE = {'pad': st_pad, 'warm': st_warm, 'pulse': st_pulse, 'groove': st_groove, 'drive': st_drive, 'dark': st_dark,
         'pizz': st_pizz, 'anthem': st_anthem, 'emotional': st_emotional}
PROG = {'minor': ['i', 'VI', 'III', 'VII'], 'minor2': ['i', 'iv', 'VI', 'V'], 'minor3': ['i', 'VI', 'iv', 'V'],
        'major': ['I', 'V', 'vi', 'IV'], 'major2': ['I', 'vi', 'IV', 'V'], 'major3': ['IV', 'I', 'V', 'vi'], 'major4': ['I', 'IV', 'vi', 'V']}


def section(t0, t1, key, mode, bpm, style, e0, e1, prog=None, bpc=None, **kw):
    """一段音乐：从 t0（第一个强拍）写到 t1；每小节按能量线性插值调用织体函数"""
    if t1 - t0 < 0.3: return
    beat = 60.0 / bpm; bar = 4 * beat
    pr = PROG[prog or ('major' if mode == 'major' else 'minor')]
    sec = dict(key=key, mode=mode, bpc=bpc or (2 if style in ('pad', 'dark', 'emotional', 'warm') else 1), **kw)
    k = 0; b = t0
    while b < t1 - 0.25 * beat:
        u = (b - t0) / max(t1 - t0, 1e-3)
        e = e0 + (e1 - e0) * u
        rn = pr[(k // sec['bpc']) % len(pr)]
        STYLE[style](sec, b, beat, rn, e, k)
        for j in range(4): EVENTS['beats'].append(round(b + j * beat, 3))
        b += bar; k += 1
    # 截断：本段写出的音不越过 t1 太多（铺底留 0.35 s 余音）
    for ins in MID.instruments:
        for n in ins.notes:
            if t0 <= n.start < t1 and n.end > t1 + 0.35 and ins.name not in ('pad', 'slowstr', 'contra', 'choir', 'timp'):
                n.end = t1 + 0.05


# ------------------------------------------------------------------ 全片编排
def build():
    title = CH['title'][0]; logo = TL['logo']
    chs = {k: CH[k][0] for k in ('ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6', 'ch7', 'end')}
    sot = {s['id'][4:]: (s['start'] - s.get('lead', 0), s['start'] + s['dur']) for s in TL['segs'] if s.get('kind') == 'sot'}

    # ======== 开场：紧张的脉冲（D 小调 92）→“六年后”抽空重拍 → 驱动 → 设问后静一拍 → 原声下铺底 → 三块牌子的律动 → 片名
    t6 = WT('h4', '六年后')
    section(0.15, t6, 'D', 'minor', 92, 'pulse', 0.4, 0.56, prog='minor2', theme=True, theme_ins='piano')
    for w in ('没有审计', '没有盘点', '也没有查'): hit(WT('h2', w), 'D', 'minor', 'i', 0.5, dark=True)
    hit(WT('h1', '五千五百'), 'D', 'minor', 'VI', 0.45)
    drop(t6, 0.55); hit(t6, 'D', 'minor', 'i', 1.0, dark=True)
    q_end = E('h5') + 0.15
    section(t6, q_end, 'D', 'minor', 92, 'drive', 0.62, 0.8, prog='minor3')
    hit(WT('h5', '还是'), 'D', 'minor', 'V', 0.5)
    MUTES.append((q_end, S('h6') - 0.35))
    g0, g1 = sot['good']
    section(S('h6') - 0.35, g1 + 0.25, 'F', 'major', 92, 'pad', 0.3, 0.3, prog='major4')
    section(g1 + 0.25, title, 'F', 'major', 100, 'groove', 0.5, 0.78, prog='major', theme=True, theme_ins='glock')
    for w, rn in (('好生意', 'I'), ('好价钱', 'V'), ('对的人', 'vi')): hit(WT('h7', w), 'F', 'major', rn, 0.55)
    rise(title, 2.4, key='F')
    # ======== 片名：重拍 + 铜管主题
    hit(title, 'F', 'major', 'I', 1.3)
    section(title, chs['ch1'], 'F', 'major', 100, 'emotional', 0.75, 0.6, theme_ins='brass')
    # ======== 第一章 对的人：温暖钢琴（A 小调 84）→ 被断货、被告（脉冲）→ 赢官司（转 C 大调律动）→ 困境与路易（深情）
    #          → “现金只有五十美元”抽空 → 卖得便宜、说真话（合唱）
    hit(chs['ch1'], 'A', 'minor', 'i', 0.55)
    section(chs['ch1'] + 0.05, S('c1f') - 0.2, 'A', 'minor', 84, 'warm', 0.25, 0.42, theme=True)
    tw = WT('c1h', '赢了所有官司')
    section(S('c1f') - 0.2, tw, 'A', 'minor', 84, 'pulse', 0.45, 0.66, prog='minor2')
    hit(tw, 'C', 'major', 'I', 0.75)
    section(tw, S('c1e') - 0.15, 'C', 'major', 84, 'groove', 0.5, 0.55, prog='major2')
    t50 = WT('c1i', '五十美元')
    section(S('c1e') - 0.15, t50, 'A', 'minor', 84, 'emotional', 0.35, 0.6, theme_ins='horn')
    drop(t50, 0.7); hit(t50, 'A', 'minor', 'i', 0.72, dark=True)
    section(t50, S('c1k') - 0.25, 'A', 'minor', 84, 'pad', 0.25, 0.25)
    section(S('c1k') - 0.25, chs['ch2'], 'C', 'major', 84, 'emotional', 0.45, 0.62, prog='major3')
    hit(WT('c1k', '卖得便宜'), 'C', 'major', 'I', 0.5)
    rise(chs['ch2'], 1.8, key='F')
    # ======== 第二章 好价钱：律动（F 大调 100）→“一个字没改”重拍 → 引语卡铺底 → 图表层层加码 →“两倍”重拍 → 芒格引语铺底 → 对的人
    hit(chs['ch2'], 'F', 'major', 'I', 1.0)
    section(chs['ch2'], S('c2f') - 0.1, 'F', 'major', 100, 'groove', 0.42, 0.62, prog='major', theme=True, theme_ins='glock')
    hit(WT('c2a', '一亿多'), 'F', 'major', 'V', 0.5)
    tz = WT('c2e', '一个字没改'); drop(tz, 0.45); hit(tz, 'F', 'major', 'I', 0.85)
    section(S('c2f') - 0.1, S('c2i') - 0.2, 'F', 'major', 100, 'pad', 0.32, 0.32, theme=True, theme_ins='piano')
    t2 = WT('c2m', '两倍')
    section(S('c2i') - 0.2, t2, 'F', 'major', 100, 'groove', 0.5, 0.9, prog='major2')
    drop(t2, 0.4); hit(t2, 'F', 'major', 'I', 1.0)
    section(t2, S('c2k') - 0.2, 'F', 'major', 100, 'pad', 0.32, 0.3, prog='major4', theme=True, theme_ins='piano')
    section(S('c2k') - 0.2, chs['ch3'], 'F', 'major', 100, 'groove', 0.55, 0.7, prog='major3')
    rise(chs['ch3'], 2.0, key='D', mode='minor')
    # ======== 第三章 好生意（v4：商业模式 + 护城河两关）
    #   灰熊之问（脉冲 D 小调）→ 五条打法（明亮律动 F 大调 108）→ 三千万 → 飞轮（驱动全速，“轮子”重拍）→ 河底（深情）
    #   → “两关”抽空重拍 → 第一关 Levitz（驱动弦乐 D 小调 112，“16.5%”重拍）→ 算账“倒贴”（暗重拍）
    #   → 第二关“反而拉大了”（大重拍转 F 大调）→ 三个原因（颂歌，逐条点）→ Dillard’s 引语铺底 → Levitz 清算（暗）→ 结论（颂歌）
    hit(chs['ch3'], 'D', 'minor', 'i', 0.9, dark=True)
    section(chs['ch3'], S('c3m1') - 0.2, 'D', 'minor', 104, 'pulse', 0.42, 0.5, prog='minor')
    section(S('c3m1') - 0.2, S('c3d') - 0.2, 'F', 'major', 108, 'groove', 0.5, 0.66, prog='major', theme=True, theme_ins='glock')
    hit(S('c3m1') - 0.2, 'F', 'major', 'I', 0.75)
    for w in ('一处地方', '量最大', '费用最低', '价格远低于', '家里人'): hit(WT('c3m1', w), 'F', 'major', 'IV' if w == '量最大' else 'I', 0.4)
    hit(WT('c3m2', '三千万'), 'F', 'major', 'IV', 0.6)
    tw = WT('c3d', '轮子')
    section(S('c3d') - 0.2, tw, 'F', 'major', 108, 'drive', 0.66, 0.95, prog='major', theme=True, theme_ins='horn')
    drop(tw, 0.35); hit(tw, 'F', 'major', 'I', 1.0)
    section(tw, S('c3s') - 0.2, 'F', 'major', 108, 'emotional', 0.5, 0.55, prog='major4', theme_ins='piano')
    ts_ = WT('c3s', '规模经济分享')                      # 尼克·斯利普：规模经济分享（点名处重拍，转入明亮律动）
    section(S('c3s') - 0.2, S('c3f') - 0.2, 'F', 'major', 108, 'groove', 0.55, 0.75, prog='major2', theme=True, theme_ins='glock')
    drop(ts_, 0.35); hit(ts_, 'F', 'major', 'I', 0.85)
    hit(WT('c3s', '他举的'), 'F', 'major', 'IV', 0.5)
    section(S('c3f') - 0.2, S('c3n1') - 0.25, 'F', 'major', 108, 'emotional', 0.45, 0.55, prog='major4', theme_ins='piano')
    t2 = WT('c3n1', '两关')
    hit(WT('c3n1', '低成本才是'), 'D', 'minor', 'III', 0.5)
    section(S('c3n1') - 0.25, t2, 'D', 'minor', 112, 'pulse', 0.45, 0.6, prog='minor2')
    drop(t2, 0.45); hit(t2, 'D', 'minor', 'i', 0.9, dark=True)
    t165 = WT('c3c', '百分之十六点五')
    section(t2, t165, 'D', 'minor', 112, 'drive', 0.55, 0.78, prog='minor3')
    hit(WT('c3b', '百分之四十四'), 'D', 'minor', 'VI', 0.5)
    drop(t165, 0.4); hit(t165, 'D', 'minor', 'III', 0.95)
    tl = WT('c3n3', '倒贴')
    section(t165, tl, 'D', 'minor', 112, 'pulse', 0.5, 0.66, prog='minor')
    drop(tl, 0.4); hit(tl, 'D', 'minor', 'i', 0.9, dark=True)
    tg = WT('c3n4', '反而拉大了')
    section(tl + 0.6, tg, 'D', 'minor', 112, 'drive', 0.5, 0.75, prog='minor2')
    drop(tg, 0.45); hit(tg, 'F', 'major', 'I', 1.15)
    section(tg, S('c3h') - 0.2, 'F', 'major', 112, 'anthem', 0.6, 0.85, prog='major', theme=True)
    for ln, w in (('c3n5', '第一是'), ('c3n6', '第二是'), ('c3n7', '第三是')): hit(WT(ln, w), 'F', 'major', 'I', 0.6)
    section(S('c3h') - 0.2, S('c3n8') - 0.2, 'D', 'minor', 112, 'pad', 0.32, 0.32, prog='minor')
    tq = WT('c3n8', '清算')
    section(S('c3n8') - 0.2, S('c3i') - 0.25, 'D', 'minor', 112, 'pulse', 0.45, 0.6, prog='minor3')
    hit(tq, 'D', 'minor', 'i', 0.7, dark=True)
    tc = WT('c3i', '学不来的便宜')
    section(S('c3i') - 0.25, chs['ch4'], 'F', 'major', 112, 'anthem', 0.7, 0.92, prog='major', theme=True)
    hit(S('c3i') - 0.25, 'F', 'major', 'I', 0.8)
    hit(tc, 'F', 'major', 'I', 1.1)
    rise(chs['ch4'], 1.6, snare=False, key='C', mode='minor')
    # ======== 第四章 开到隔壁：阴暗心跳（C 小调 76）→“辞职走了”抽空重拍 → 数字（脉冲）→ 隔壁新店（俏皮拨弦 Eb 大调 96）
    #          → 竞业禁止（阴暗）→“九十九岁”转降 A 大调 → 引语与“一百零四岁”（深情）
    hit(chs['ch4'], 'C', 'minor', 'i', 0.9, dark=True)
    tq = WT('c4b', '辞职走了')
    section(chs['ch4'], tq, 'C', 'minor', 76, 'dark', 0.4, 0.62, prog='minor2')
    drop(tq, 0.6); hit(tq, 'C', 'minor', 'i', 1.0, dark=True)
    section(tq + 1.2, S('c4d') - 0.2, 'C', 'minor', 76, 'pulse', 0.4, 0.5, prog='minor')
    section(S('c4d') - 0.2, S('c4e') - 0.2, 'Eb', 'major', 96, 'pizz', 0.5, 0.6, prog='major2')
    t99 = WT('c4f', '九十九岁')
    section(S('c4e') - 0.2, t99, 'C', 'minor', 76, 'dark', 0.42, 0.58, prog='minor3')
    hit(t99, 'Ab', 'major', 'I', 0.8)
    section(t99, chs['ch5'], 'Ab', 'major', 76, 'emotional', 0.45, 0.62, prog='major')
    hit(WT('c4h', '一百零四岁'), 'Ab', 'major', 'I', 0.5)
    rise(chs['ch5'], 2.0, key='D')
    # ======== 第五章 越开越大：原声下铺底 → 律动起势 → 颂歌（D 大调 118），数字落地处重拍
    hit(chs['ch5'], 'D', 'major', 'I', 1.0)
    b0, b1 = sot['blumkins']
    section(chs['ch5'], b1 + 0.25, 'D', 'major', 118, 'pad', 0.3, 0.3, prog='major4')
    section(b1 + 0.25, S('c5b') - 0.2, 'D', 'major', 118, 'groove', 0.5, 0.6, prog='major')
    section(S('c5b') - 0.2, chs['ch6'], 'D', 'major', 118, 'anthem', 0.6, 0.95, prog='major3', theme=True)
    for w, ln, sz in (('十倍', 'c5c', 0.85), ('一百八十万', 'c5d', 1.0), ('销售纪录', 'c5e', 0.55), ('四千五百', 'c5f', 0.85)):
        tt = WT(ln, w)
        if sz >= 0.8: drop(tt, 0.35)
        hit(tt, 'D', 'major', 'I', sz)
    rise(chs['ch6'], 1.6, snare=False, key='B', mode='minor')
    # ======== 第六章 还能好多久：原声下铺底 → 低沉脉冲（B 小调 88），三件事各点一下
    hit(chs['ch6'], 'B', 'minor', 'i', 0.85, dark=True)
    a0, a1 = sot['attacks']
    section(chs['ch6'], a1 + 0.25, 'B', 'minor', 88, 'pad', 0.3, 0.3, prog='minor')
    section(a1 + 0.25, chs['ch7'], 'B', 'minor', 88, 'pulse', 0.42, 0.6, prog='minor3')
    for ln, w in (('c6b', '第一'), ('c6c', '第二'), ('c6e', '第三')): hit(WT(ln, w), 'B', 'minor', 'i', 0.55, dark=True)
    rise(chs['ch7'], 2.0, key='D')
    # ======== 第七章 带走什么：深情（D 大调 100）→ 一家牵出一家（律动）→“三十三亿”重拍 → 三条收获（颂歌）
    #          → 两句话（钢琴 + 合唱）→ 落版字 → logo
    hit(chs['ch7'], 'D', 'major', 'I', 0.9)
    section(chs['ch7'], S('c7c') - 0.2, 'D', 'major', 100, 'emotional', 0.38, 0.5, prog='major4')
    t33 = WT('c7e', '三十三亿')
    section(S('c7c') - 0.2, t33, 'D', 'major', 100, 'groove', 0.55, 0.82, prog='major', theme=True, theme_ins='glock')
    for w in ('一九九五年的', '一九九七年的', '一九九九年的'): hit(WT('c7c', w), 'D', 'major', 'V', 0.45)
    drop(t33, 0.5); hit(t33, 'D', 'major', 'I', 1.2)
    section(t33, S('c7f') - 0.25, 'D', 'major', 100, 'anthem', 0.6, 0.88, prog='major3', theme=True)
    for ln, w in (('c7m', '第一'), ('c7n', '第二'), ('c7o', '第三')): hit(WT(ln, w), 'D', 'major', 'I', 0.6)
    section(S('c7f') - 0.25, S('c7g') - 0.3, 'D', 'major', 100, 'emotional', 0.45, 0.55, prog='major4')
    tg = WT('c7g', '一张支票')
    section(S('c7g') - 0.3, logo, 'D', 'major', 100, 'anthem', 0.7, 0.95, prog='major', theme=True, theme_ins='brass')
    hit(tg, 'D', 'major', 'I', 0.9)
    rise(logo, 2.2, key='D')
    hit(logo, 'D', 'major', 'I', 1.3)
    section(logo, T_END - 0.2, 'D', 'major', 100, 'emotional', 0.6, 0.35, prog='major4', theme_ins='piano')


def peq(y, f0, gain_db, q):
    """RBJ 峰值均衡"""
    A_ = 10 ** (gain_db / 40); w0 = 2 * np.pi * f0 / SR; al = np.sin(w0) / (2 * q)
    b_ = np.array([1 + al * A_, -2 * np.cos(w0), 1 - al * A_]); a_ = np.array([1 + al / A_, -2 * np.cos(w0), 1 - al / A_])
    from scipy.signal import lfilter
    return lfilter(b_ / a_[0], a_ / a_[0], y, axis=0)


def render():
    os.makedirs(os.path.join(WORK, 'music'), exist_ok=True)
    mid = os.path.join(WORK, 'music', 'score.mid'); raw = os.path.join(WORK, 'music', 'score_midi.wav')
    MID.write(mid)
    subprocess.run(['fluidsynth', '-ni', '-g', '0.45', '-r', str(SR), '-o', 'synth.reverb.room-size=0.5', '-o', 'synth.reverb.level=0.32',
                    '-F', raw, SF, mid], check=True, capture_output=True)
    x, sr = sf.read(raw, dtype='float32')
    n = int((T_END + 0.5) * SR)
    x = np.pad(x, ((0, max(0, n - len(x))), (0, 0)))[:n]
    fx = FX[:n]
    # 音效层过一点短混响，跟乐队在同一个空间里
    ir_n = int(1.2 * SR); tt = np.arange(ir_n) / SR
    ir = RNG.standard_normal(ir_n) * np.exp(-tt * 5); ir = sosfilt(butter(1, 3000, 'lowpass', fs=SR, output='sos'), ir); ir /= np.sqrt((ir ** 2).sum())
    fxw = np.stack([fftconvolve(fx[:, c], ir)[:n] for c in range(2)], 1) * 0.25
    y = x + fx + fxw
    y = sosfilt(butter(2, 32, 'highpass', fs=SR, output='sos'), y, axis=0)
    # v4 均衡：220–450 Hz 去闷（-3 dB），1.8–4 kHz 提亮（+2.5 dB），10 kHz 以上滚降（不要沙沙声）
    y = peq(y, 70, -3.0, 0.7); y = peq(y, 320, -3.0, 1.0); y = peq(y, 2700, 2.5, 0.9)
    y = sosfilt(butter(2, 10000, 'lowpass', fs=SR, output='sos'), y, axis=0)
    # 母线：轻压缩 + 软限幅，保留起伏
    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    y *= 10 ** ((-18.0 - meter.integrated_loudness(y)) / 20)
    lim = 10 ** (-1.0 / 20)
    y = np.where(np.abs(y) > lim * 0.8, np.sign(y) * (lim * 0.8 + lim * 0.2 * np.tanh((np.abs(y) - lim * 0.8) / (lim * 0.2))), y)
    sf.write(os.path.join(WORK, 'music', 'score_raw.wav'), y.astype(np.float32), SR, subtype='PCM_24')
    EVENTS['beats'] = sorted(set(EVENTS['beats'])); EVENTS['hits'] = sorted(set(EVENTS['hits'])); EVENTS['soft'] = sorted(set(EVENTS['soft']))
    json.dump(EVENTS, open(os.path.join(WORK, 'music', 'beats.json'), 'w'))
    print('ok', os.path.join(WORK, 'music', 'score_raw.wav'), 'hits', len(EVENTS['hits']), 'soft', len(EVENTS['soft']), 'notes',
          sum(len(i.notes) for i in MID.instruments))


if __name__ == '__main__':
    build()
    render()
