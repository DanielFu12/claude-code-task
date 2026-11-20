"""把旁白排到 80BPM 节拍网格上 -> work/timeline.json + work/voice.wav（V7）
规则：
- 台词默认起于半拍；镜头（shot）起于整拍；章节卡起于小节线。
- 带「揭晓点」的台词（数字落地、锤子落下、金句）反推起点，让揭晓点正好落在整拍上；三锤严格间隔一小节。
- cues 记录所有揭晓点，配乐重击与画面落点共用。"""
import json, math, os, sys
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES
W = sys.argv[1] if len(sys.argv) > 1 else 'work'
BPM = 80; BEAT = 60 / BPM; BAR = 4 * BEAT; SR = 48000
up = lambda t, q: math.ceil(t / q - 1e-6) * q
GAP_K = 1.0


def pauses(y, db_thr=-32, min_frames=7):
    """句内停顿 [(起, 止)]（相对句首，秒）"""
    hop = 480; n = len(y) // hop
    r = np.sqrt(np.mean(y[:n * hop].reshape(n, hop) ** 2, 1) + 1e-12)
    sil = 20 * np.log10(r / r.max()) < db_thr
    out, k = [], 0
    while k < n:
        if sil[k]:
            j = k
            while j < n and sil[j]: j += 1
            if j - k >= min_frames and k > 5 and j < n - 5: out.append((k * hop / SR, j * hop / SR))
            k = j
        else: k += 1
    return [(round(a, 3), round(b, 3)) for a, b in out]


def fine_pauses(y):
    hop = 240; n = len(y) // hop
    r = np.sqrt(np.mean(y[:n * hop].reshape(n, hop) ** 2, 1) + 1e-12)
    sil = 20 * np.log10(r / r.max()) < -24; out, k = [], 0
    while k < n:
        if sil[k]:
            j = k
            while j < n and sil[j]: j += 1
            if (j - k) * hop / SR >= 0.1 and k > 3: out.append((k * hop / SR, j * hop / SR))
            k = j
        else: k += 1
    return out


def chunks(sub, ps, t0, d):
    """字幕按 | 分段，分段点吸附到最近的停顿"""
    parts = sub.split('|')
    if len(parts) == 1: return [(sub, round(t0, 3), round(t0 + d, 3))]
    w = lambda s: max(1, len(s.replace(' ', '')))
    tot = sum(w(p) for p in parts); acc = 0; bounds = []
    for p in parts[:-1]:
        acc += w(p); est = d * acc / tot
        cand = [(abs((a + b) / 2 - est), b) for a, b in ps if b not in bounds and b > (bounds[-1] if bounds else 0)]
        bounds.append(min(cand)[1] if cand and min(cand)[0] < 1.0 else est)
    ts = [0] + bounds + [d]
    return [(p, round(t0 + ts[k], 3), round(t0 + ts[k + 1], 3)) for k, p in enumerate(parts)]


# 镜头 / 章节：(名字, 起始台词, 起点前额外留白拍数, 对齐方式)
SECTIONS = [
    ('post', 'L01', 0, 'beat'), ('books', 'L02', 0, 'half'), ('tencent', 'L03', 0, 'beat'), ('dest', 'L05', 0, 'half'),
    ('unwilling', 'L06', 1, 'beat'), ('catl', 'L07', 0, 'beat'), ('ali', 'L08', 0, 'beat'), ('zp', 'L09', 0, 'beat'),
    ('halves', 'L10', 0, 'half'), ('gold', 'L11', 0, 'beat'), ('nv', 'L12', 0, 'beat'), ('wall', 'L14', 1, 'beat'),
    ('q1', 'L16', 0, 'bar'), ('anchor', 'L17', 0, 'beat'), ('scale', 'L19', 0, 'beat'), ('twoscales', 'L22', 0, 'beat'),
    ('gold1', 'L24', 1, 'beat'), ('tenyear', 'L25', 0, 'bar'), ('moat', 'L26', 0, 'beat'), ('quotes', 'L29', 0, 'beat'),
    ('newmoat', 'L31', 0, 'beat'), ('keep', 'L33', 0, 'beat'), ('tech', 'L35', 1, 'beat'), ('ibm', 'L37', 0, 'beat'),
    ('baskets', 'L39', 1, 'beat'), ('circle', 'L42', 0, 'beat'), ('story', 'L44', 0, 'bar'), ('cars', 'L46', 0, 'beat'),
    ('air', 'L47', 0, 'beat'), ('capital', 'L48', 0, 'beat'), ('lowpe', 'L50', 1, 'beat'), ('stair', 'L55', 0, 'beat'),
    ('q99', 'L57', 0, 'beat'), ('expect', 'L58', 1, 'beat'), ('post2', 'L61', 0, 'bar'), ('hammer', 'L62', 0, 'beat'),
    ('strikes', 'L63a', 0, 'bar'), ('verdict', 'L64', 0, 'beat'), ('inv', 'L67', 1, 'beat'),
    ('q2', 'L70', 0, 'bar'), ('noise', 'L72', 0, 'beat'), ('drops', 'L73', 0, 'beat'), ('band', 'L75', 0, 'beat'),
    ('guarantee', 'L78', 0, 'beat'), ('branches', 'L80', 0, 'beat'), ('line', 'L83', 1, 'beat'),
    ('q3', 'L85', 0, 'bar'), ('principles', 'L86', 0, 'beat'), ('rebuild', 'L87', 0, 'beat'), ('diversify', 'L88', 0, 'beat'),
    ('finale', 'L89', 1, 'bar'), ('epilogue', 'L90', 7, 'bar'), ('hardest', 'L93', 1, 'beat'), ('last', 'L95', 0, 'beat')]
SEC_START = {s[1]: s for s in SECTIONS}
CHAPTER_BEATS = {'q1': 4, 'q2': 4, 'q3': 4}       # 章节卡单独亮相的拍数（全奏落点）
TITLE_BEATS = 6                                   # 片名卡
GOLDEN = {'L24', 'L34', 'L54', 'L60', 'L84', 'L92'}  # 金句：句首落在整拍


def reveal_off(i, y, d):
    """揭晓点相对句首的偏移"""
    fp = fine_pauses(y)
    last_phrase = lambda: max([b for a, b in fp if b < d - 0.8] or [d * 0.55])
    if i in ('L04', 'L07', 'L08', 'L09', 'L13'): return last_phrase()      # 370 多 / 又跌三成 / 63 / 跌破 400 / 继续下跌
    if i in ('L63a', 'L63b', 'L63c'): return 0.05                           # 「看到……」开口 = 锤子落下
    if i in GOLDEN: return 0.0
    return None


NAT = json.load(open(f'{W}/vo/gaps.json')) if os.path.exists(f'{W}/vo/gaps.json') else {}
lines, secs, cues = [], {}, {}
voice = np.zeros(int(1000 * SR), np.float32)
t = BEAT
HOLD = {'L06': 0.9, 'L07': 1.1, 'L08': 1.2, 'L10': 0.35, 'L13': 1.3, 'L71': 1.0, 'L79': 0.3, 'L83': 0.35, 'L85': 0.45, 'L86': 1.6, 'L87': 0.45, 'L88': 0.45}   # 讲故事的人会在这几句后面停一下
inside = False          # 当前句是否接在同一整段合成的上一句后面（首尾相接 = 原来那一口气）
prev_pause = 0.0
for (i, text, sub, ctx, gap) in LINES:
    y, _ = sf.read(f'{W}/vo/{i}.wav', dtype='float32')
    d = len(y) / SR; ps = pauses(y)
    if i in SEC_START:
        name, _, pad, al = SEC_START[i]
        if not inside:                                 # 整段的开头：留出音乐呼吸，对齐网格
            if name == 'q1':                           # 片名卡 → 第一章章节卡
                t = up(t + BEAT, BAR); secs['title'] = t; t += TITLE_BEATS * BEAT
            q = {'bar': BAR, 'beat': BEAT, 'half': BEAT / 2}[al]
            t = up(t + pad * BEAT, q)
            if name in CHAPTER_BEATS:
                secs[name + '_card'] = t; t += CHAPTER_BEATS[name] * BEAT
        pend = name                                    # 段内的小节：画面跟着话走，不打断语流（起点在揭晓对齐之后再定）
    else: pend = None
    off = reveal_off(i, y, d)
    if off is not None:
        c = t + off
        prev = {'L63b': 'L63a', 'L63c': 'L63b'}.get(i)
        if prev:
            dp = lines[-1]['t1'] - cues[prev]       # 三锤：每锤间隔半小节的整数倍，放得下上一句为止
            c = cues[prev] + 2 * BEAT * math.ceil((dp + 0.3) / (2 * BEAT))
        elif i == 'L63a': c = up(c, BEAT)              # 第一锤落在整拍
        elif i in GOLDEN: c = up(c, BEAT) if up(c, BEAT) - c < 0.6 else up(c, BEAT / 2)   # 金句前多留半口气
        else:                                          # 数字揭晓：只在停顿里挪动，最多前后 0.19 秒
            g = round(c / (BEAT / 2)) * (BEAT / 2)
            back = max(0.0, prev_pause / 2 - 0.03) if inside else 0.0
            c = g if -back <= g - c <= 0.3 else up(c, BEAT / 2)
        t = c - off
        cues[i] = round(c, 3)
    if pend: secs[pend] = t
    lines.append(dict(id=i, t0=round(t, 4), t1=round(t + d, 4), sub=sub, pauses=ps, chunks=chunks(sub, ps, t, d)))
    a = int(t * SR); voice[a:a + len(y)] += y
    ng = NAT.get(i)
    inside = ng is not None; prev_pause = ng or 0.0
    t = t + d + HOLD.get(i, 0.0) if inside else up(t + d + gap * GAP_K, BEAT / 2)
secs['card'] = up(t + 1.5, BEAT)
T = secs['card'] + 6 * BEAT
voice = voice[:int(T * SR)]
sf.write(f'{W}/voice.wav', voice, SR, subtype='FLOAT')
json.dump(dict(cues=cues, bpm=BPM, beat=BEAT, bar=BAR, total=T, sections=secs, lines=lines),
          open(f'{W}/timeline.json', 'w'), ensure_ascii=False, indent=1)
print('total %.1f s = %d:%02d' % (T, T // 60, T % 60))
print('cues', cues)
for k in ('title', 'q1_card', 'q2_card', 'q3_card', 'strikes', 'epilogue', 'card'): print(k, secs[k])
