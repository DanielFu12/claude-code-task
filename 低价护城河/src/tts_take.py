"""整篇一次合成 → 按逐字时间戳切句。
python3 src/tts_take.py WORK
输出：WORK/vo/take.mp3、WORK/vo/<id>.wav（48k 单声道）、WORK/vo.json {id: {dur, chars:[(char, t0, t1)], text}}
"""
import sys, os, json, hashlib, subprocess
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, SPEED
from tts import synth

WORK = sys.argv[1]; VO = os.path.join(WORK, 'vo'); os.makedirs(VO, exist_ok=True)
text = ''.join(l[1] for l in LINES)
h = hashlib.md5((text + str(SPEED)).encode()).hexdigest()[:10]
mp3 = os.path.join(VO, 'take_%s.mp3' % h); wj = mp3.replace('.mp3', '.json')
if not os.path.exists(wj):
    words = synth(text, mp3, voice_settings={'speed': SPEED})
    json.dump(words, open(wj, 'w'), ensure_ascii=False)
words = json.load(open(wj))
wav = mp3.replace('.mp3', '.wav')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', mp3, '-ac', '1', '-ar', '48000', wav], check=True)
y, sr = sf.read(wav)

# 时间戳可能分句给出且各自从 0 开始：检测回退并累加偏移
seq = []; off = 0.0; last = 0.0
for w, a, b in words:
    if a + off < last - 0.5: off = last
    seq.append((w, a + off, b + off)); last = max(last, b + off)
# 逐字对上文本
chars = []; k = 0
for w, a, b in seq:
    for c in w:
        while k < len(text) and text[k] != c: k += 1
        if k < len(text): chars.append((k, c, a, b)); k += 1
idx = {}
pos = 0
for lid, t, *_ in LINES:
    idx[lid] = (pos, pos + len(t)); pos += len(t)

def voiced(ch): return ch not in '，。、：；？！“”·,.:;?! '
spans = {}
for lid, t, *_ in LINES:
    s, e = idx[lid]
    got = {k: (c, a, b) for (k, c, a, b) in chars if s <= k < e}
    cs = []; prev = None
    for k in range(s, e):  # 每个文本位置一项；缺失的（标点等）取上一字结束时刻
        if k in got: cs.append(got[k]); prev = got[k][2]
        else:
            nxt = next((got[j][1] for j in range(k + 1, e) if j in got), prev)
            cs.append((text[k], prev if prev is not None else nxt, prev if prev is not None else nxt))
    vs = [x for x in cs if voiced(x[0]) and x[0] in [g[0] for g in got.values()]]
    spans[lid] = (vs[0][1], vs[-1][2], cs)

# 句界：两句之间停顿的能量最低点（在 [上句末, 下句首] 内）
env = np.convolve(np.abs(y), np.ones(480) / 480, mode='same')
ids = [l[0] for l in LINES]; cuts = {}
for i, lid in enumerate(ids):
    a, b, _ = spans[lid]
    if i == 0: start = max(0.0, a - 0.12)
    else: start = cuts[ids[i - 1]][1]
    if i + 1 < len(ids):
        na = spans[ids[i + 1]][0]
        lo, hi = int(b * sr), int(max(b + 0.02, na - 0.03) * sr)
        end = (lo + int(np.argmin(env[lo:hi]))) / sr if hi > lo else (b + na) / 2
    else: end = min(len(y) / sr, b + 0.6)
    cuts[lid] = (start, end)
out = {}
fade = int(0.012 * sr)
for lid, t, sub in LINES:
    s0, s1 = cuts[lid]
    seg = y[int(s0 * sr):int(s1 * sr)].copy()
    seg[:fade] *= np.linspace(0, 1, fade); seg[-fade:] *= np.linspace(1, 0, fade)
    sf.write(os.path.join(VO, lid + '.wav'), seg, sr)
    a, b, cs = spans[lid]
    out[lid] = dict(dur=len(seg) / sr, speech=(a - s0, b - s0), text=t, sub=sub or t,
                    chars=[(c, round(x - s0, 3), round(z - s0, 3)) for c, x, z in cs])
json.dump(out, open(os.path.join(WORK, 'vo.json'), 'w'), ensure_ascii=False, indent=0)
tot = sum(v['dur'] for v in out.values())
print('take %.1fs, lines %.1fs, %d chars, %.2f chars/s' % (len(y) / sr, tot, len(text), len(text) / tot))
for lid in ids: print(lid, '%.2f' % out[lid]['dur'], out[lid]['text'][:20])
