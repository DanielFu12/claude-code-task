"""整段旁白 → 逐句音频 + 逐字时间（work/vo/<id>.wav + work/vo/vo.json）。

对齐直接用豆包语音合成返回的逐字时间戳（tts_db/<段>_0.json），不再跑强制对齐模型：
把每个“字”（数字串、英文词作为一个单元）按顺序对回各句的朗读文本，得到每句的发声起止；
在句与句之间停顿的正中切开，句内语气、换气完全保留，不变速、不压停顿。
vo.json 每句：lead（切片开头到发声）、dur（发声长度）、gap（到下一句发声的自然间隔）、
ct（[朗读文本中的字符下标, 相对发声起点的秒数]），供时间线、字幕、画面和配乐对位。
"""
import sys, os, json, re
import numpy as np, soundfile as sf, librosa
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tts_passage import PASSAGES, TEASE_P, spoken

SR = 48000
PUN = re.compile(r'[\s，。、：；？！“”‘’《》（）—…·,.;:?!"\'()\-]')


def frame_db(y, hop=0.005):
    h = int(hop * SR)
    e = np.sqrt(np.convolve(y ** 2, np.ones(h * 4) / (h * 4), 'same'))[::h]
    return 20 * np.log10(e + 1e-9), hop


def refine(db, hop, t0, t1, floor):
    i0, i1 = int(t0 / hop), int(t1 / hop)
    a = i0
    while a > 0 and db[a - 1] > floor and i0 - a < int(0.25 / hop): a -= 1
    b = min(i1, len(db) - 1)
    while b < len(db) - 1 and db[b + 1] > floor and b - i1 < int(0.6 / hop): b += 1
    return a * hop, b * hop


def map_words(ids, words):
    """words: [(文本, 起, 止)] → 每句 [(朗读文本下标, 起, 止)]"""
    out = {i: [] for i in ids}
    k = 0
    for i in ids:
        s = spoken(i); pos = 0
        while k < len(words):
            w = re.sub(r'^[^\w$]+|[^\w%]+$', '', words[k][0].strip()); w = PUN.sub('', w) if not re.search(r'\d', w) else w
            if not w: k += 1; continue
            # 在本句剩余文本里找这个单元（跳过标点、空格）
            j = pos
            while j < len(s) and PUN.match(s[j]): j += 1
            if s[j:j + len(w)].lower() != w.lower(): break
            out[i].append((j, words[k][1], words[k][2])); pos = j + len(w); k += 1
        rest = PUN.sub('', s[pos:])
        if rest: raise RuntimeError(f'{i}: 时间戳没能对上的剩余文本「{rest}」（豆包可能漏读或改读，需重录）')
    return out


def process(pid, ids, wav, js, out, meta):
    import pyloudnorm as pyln
    y, _ = librosa.load(wav, sr=SR)
    y = y * 10 ** ((-20.0 - pyln.Meter(SR).integrated_loudness(y)) / 20)
    words = [(w['word'], w['startTime'], w['endTime']) for s in json.load(open(js)) for w in s['words']]
    m = map_words(ids, words)
    db, hop = frame_db(y)
    floor = np.percentile(db[db > -120], 95) - 38
    sil = db < floor + 18                                    # 静音帧（比峰值低 32 dB 以上）

    def runs(t0, t1):
        """[t0,t1] 内的静音段 [(起, 止)]"""
        i0, i1 = max(int(t0 / hop), 0), min(int(t1 / hop), len(sil) - 1); out = []; k = i0
        while k <= i1:
            if sil[k]:
                j = k
                while j + 1 <= i1 and sil[j + 1]: j += 1
                out.append((k * hop, (j + 1) * hop)); k = j + 1
            else: k += 1
        return out
    # 豆包的逐字时间戳在句首会滞后（头两个字被压在一起），所以句间切点用能量定：
    # 在“上一句最后一个字开始”到“本句第一个字的时间戳”之间，取第一段 ≥0.18s 的静音（句号停顿；之后的逗号停顿属于本句）
    bounds = []
    for k in range(len(ids) - 1):
        a0 = m[ids[k]][-1][1]; b0 = m[ids[k + 1]][0][1]
        r = runs(a0, b0)
        if not r: r = [((m[ids[k]][-1][2] + m[ids[k + 1]][0][1]) / 2,) * 2]
        long_ = [x for x in r if x[1] - x[0] >= 0.18]
        bounds.append(long_[0] if long_ else max(r, key=lambda x: x[1] - x[0]))
    voiced = np.nonzero(~sil)[0]                            # 段首、段尾：第一个 / 最后一个有声帧（数字读音中间的短暂低谷不算结束）
    st0 = voiced[0] * hop if len(voiced) else 0.0
    en1 = (voiced[-1] + 1) * hop if len(voiced) else len(y) / SR
    spans = []
    for k, i in enumerate(ids):
        a_ = st0 if k == 0 else bounds[k - 1][1]
        b_ = en1 if k == len(ids) - 1 else bounds[k][0]
        spans.append((a_, b_))
    cuts = [max(spans[0][0] - 0.12, 0)]
    for k in range(len(spans) - 1): cuts.append((spans[k][1] + spans[k + 1][0]) / 2)
    cuts.append(min(spans[-1][1] + 0.35, len(y) / SR))
    for k, i in enumerate(ids):
        c0, c1 = cuts[k], cuts[k + 1]; a_, b_ = spans[k]
        seg = y[int(c0 * SR):int(c1 * SR)].copy()
        fl = int(0.01 * SR); seg[:fl] *= np.linspace(0, 1, fl); seg[-fl:] *= np.linspace(1, 0, fl)
        sf.write(os.path.join(out, f'{i}.wav'), seg, SR)
        meta[i] = dict(passage=pid, lead=round(a_ - c0, 3), dur=round(b_ - a_, 3), tail=round(c1 - b_, 3),
                       gap=round(spans[k + 1][0] - b_, 3) if k + 1 < len(ids) else None,
                       ct=[[j, round(max(s0 - a_, 0.0), 3)] for j, s0, _ in m[i]])
    print(pid, ' '.join(f"{i}:{meta[i]['dur']:.1f}/{meta[i]['gap'] or 0:.2f}" for i in ids), flush=True)


def build(work):
    out = os.path.join(work, 'vo'); os.makedirs(out, exist_ok=True); meta = {}
    for pid, ids, _ in PASSAGES + [TEASE_P]:
        b = os.path.join(work, 'tts_db', f'{pid}_0')
        process(pid, ids, b + '.wav', b + '.json', out, meta)
    json.dump(meta, open(os.path.join(out, 'vo.json'), 'w'), ensure_ascii=False, indent=0)
    return meta


if __name__ == '__main__':
    build(sys.argv[1])
