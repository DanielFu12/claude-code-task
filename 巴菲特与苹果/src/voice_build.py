"""整段旁白 → 逐句音频 + 精确字时间（work/vo/<id>.wav + work/vo/vo.json）。

每段（tts_passage.PASSAGES）选定一个录音（work/tts_p/select.json，缺省取 _0），强制对齐到文本，
在句与句之间停顿的正中切开：句子内部和句间的语气、换气完全保留，不变速、不压停顿。
vo.json 记录每句：lead（切片开头到发声）、dur（发声长度）、gap（原录音里到下一句发声的自然间隔）、
ct（每个读音单元在原文中的下标与相对发声时刻），供时间线、字幕、画面和音效对位。
"""
import sys, os, json
import numpy as np, soundfile as sf, librosa
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tts_passage import PASSAGES, TEASE_P, GROUPS, spoken
from align import align

SR = 48000
TARGET_RATE = 4.55        # 全片统一语速（音节/秒，不含停顿）：从容、不赶


def articulation_rate(f, text):
    """音节/秒：读音单元数 ÷ 发声时长（去掉 0.25s 以上的停顿）"""
    from align import normalize
    y, sr = librosa.load(f, sr=16000)
    iv = librosa.effects.split(y, top_db=38)
    sp = sum(b - a for a, b in iv) / sr
    short = sum(g for g in ((iv[k][0] - iv[k - 1][1]) / sr for k in range(1, len(iv))) if g < 0.25)
    return len(normalize(text)[0]) / (sp + short)


def frame_db(y, sr, hop=0.005):
    h = int(hop * sr)
    e = np.sqrt(np.convolve(y ** 2, np.ones(h * 4) / (h * 4), 'same'))[::h]
    return 20 * np.log10(e + 1e-9), hop


def refine(y, sr, t0, t1, floor_db):
    """对齐给出的 [t0,t1] → 按能量把起点往前、终点往后扩到真正的发声边界（保留辅音起始和尾音）"""
    db, hop = frame_db(y, sr)
    i0 = int(t0 / hop); i1 = int(t1 / hop)
    a = i0
    while a > 0 and db[a - 1] > floor_db and i0 - a < int(0.25 / hop): a -= 1
    b = i1
    while b < len(db) - 1 and db[b + 1] > floor_db and b - i1 < int(0.6 / hop): b += 1
    return a * hop, b * hop


def build(work):
    d = os.path.join(work, 'tts_p'); out = os.path.join(work, 'vo'); os.makedirs(out, exist_ok=True)
    sel = json.load(open(os.path.join(d, 'select.json'))) if os.path.exists(os.path.join(d, 'select.json')) else {}
    meta = {}
    units = []
    P = {p[0]: p for p in PASSAGES + [TEASE_P]}
    if all(g in sel for g in GROUPS):                     # v8：按“大段”一次读完的录音（同一讲述者、同一语速）
        for g, pids in GROUPS.items():
            units.append((g, [i for pp in pids for i in P[pp][1]], os.path.join(d, sel[g])))
    for pid, ids, mood in ([] if units else PASSAGES + [TEASE_P]):
        f = os.path.join(d, sel.get(pid, f'{pid}_0.wav'))
        if os.path.exists(f): units.append((pid, ids, f))
        else:                                                # 该段还没有整段录音：退回逐句录音（work/tts/<id>.wav）
            units += [(f'{pid}:{i}', [i], os.path.join(work, 'tts', f'{i}.wav')) for i in ids]
    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    rates = {}
    if TARGET_RATE:                                       # 各大段语速统一：先测每段“音节/秒”，用保持音高的 rubberband 校准到同一语速
        for pid, ids, f in units:
            rates[pid] = articulation_rate(f, ''.join(spoken(i) for i in ids))
    for pid, ids, f in units:
        if pid in rates:
            r = rates[pid] / TARGET_RATE                  # >1 表示原来偏快，要放慢
            if abs(r - 1) > 0.005:
                g = os.path.join(d, f'_eq_{pid}.wav')
                import subprocess
                subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', f, '-af', f'rubberband=tempo={1 / r:.5f}:pitchq=quality:formant=preserved',
                                '-ar', '24000', g], check=True)
                print(f'  {pid}: 语速 {rates[pid]:.2f} → {TARGET_RATE} 音节/秒（时长 ×{r:.3f}）', flush=True)
                f = g
        y, sr = librosa.load(f, sr=SR)
        y = y * 10 ** ((-20.0 - meter.integrated_loudness(y)) / 20)      # 每段统一响度，段落之间不忽大忽小
        texts = [spoken(i) for i in ids]
        text = '\n'.join(texts)
        al = align(f, text)
        db, hop = frame_db(y, SR)
        floor = np.percentile(db[db > -120], 95) - 38             # 相对整段响度的静音门限
        spans, pos = [], 0
        for i, s in zip(ids, texts):
            us = [x for x in al if pos <= x['i'] < pos + len(s)]
            a, b = refine(y, SR, us[0]['s'], us[-1]['e'], floor)
            spans.append((a, b, us, pos)); pos += len(s) + 1
        # 切点：句间停顿的正中；首句前留 0.12s，末句后留到尾音结束 + 0.35s
        cuts = [max(spans[0][0] - 0.12, 0)]
        for k in range(len(spans) - 1):
            cuts.append((spans[k][1] + spans[k + 1][0]) / 2)
        cuts.append(min(spans[-1][1] + 0.35, len(y) / SR))
        for k, (i, (a, b, us, p0)) in enumerate(zip(ids, spans)):
            c0, c1 = cuts[k], cuts[k + 1]
            seg = y[int(c0 * SR):int(c1 * SR)].copy()
            fl = int(0.01 * SR); seg[:fl] *= np.linspace(0, 1, fl); seg[-fl:] *= np.linspace(1, 0, fl)
            sf.write(os.path.join(out, f'{i}.wav'), seg, SR)
            meta[i] = dict(passage=pid, lead=round(a - c0, 3), dur=round(b - a, 3), tail=round(c1 - b, 3),
                           gap=round(spans[k + 1][0] - b, 3) if k + 1 < len(spans) else None,
                           ct=[[x['i'] - p0, round(x['s'] - a, 3)] for x in us],
                           score=round(float(np.mean([x['score'] for x in us])), 3))
        print(pid, os.path.basename(f), ' '.join(f"{i}:{meta[i]['dur']:.1f}/{meta[i]['gap'] or 0:.2f}" for i in ids), flush=True)
    json.dump(meta, open(os.path.join(out, 'vo.json'), 'w'), ensure_ascii=False, indent=0)
    return meta


if __name__ == '__main__':
    build(sys.argv[1])
