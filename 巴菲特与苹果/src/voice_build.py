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
PITCH_BASE = 99.0         # 全片统一音高基线（Hz，中位数）：偏离超过 0.7 个半音的大段，保持共振峰微调回基线（最多 ±2 个半音）


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


def process(pid, ids, f, out, d, meta):
    """一个大段录音 → 统一语速/音高/响度 → 强制对齐 → 逐句切片写到 out/<id>.wav，元数据写进 meta"""
    import pyloudnorm as pyln, subprocess
    meter = pyln.Meter(SR)
    r = articulation_rate(f, ''.join(spoken(i) for i in ids)) / TARGET_RATE if TARGET_RATE else 1.0
    if not TARGET_RATE: r = 1.0
    pr = 1.0
    if PITCH_BASE:
        yy, ss = librosa.load(f, sr=16000)
        f0, _, _ = librosa.pyin(yy, fmin=60, fmax=300, sr=ss, frame_length=1024, hop_length=320)
        st = 12 * np.log2(float(np.nanmedian(f0)) / PITCH_BASE)
        if abs(st) > 0.7: pr = 2 ** (-max(min(st, 2.0), -2.0) / 12)
    if abs(r - 1) > 0.005 or pr != 1.0:
        g = os.path.join(d, f'_eq_{os.path.basename(f)}')
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', f, '-af',
                        f'rubberband=tempo={1 / r:.5f}:pitch={pr:.5f}:pitchq=quality:formant=preserved', '-ar', '24000', g], check=True)
        print(f'  {pid} {os.path.basename(f)}: 时长 ×{r:.3f}，音高 {12 * np.log2(pr):+.2f} 半音', flush=True)
        f = g
    y, sr = librosa.load(f, sr=SR)
    y = y * 10 ** ((-20.0 - meter.integrated_loudness(y)) / 20)      # 每段统一响度
    texts = [spoken(i) for i in ids]
    al = align(f, '\n'.join(texts))
    db, hop = frame_db(y, SR)
    floor = np.percentile(db[db > -120], 95) - 38
    spans, pos = [], 0
    for i, s_ in zip(ids, texts):
        us = [x for x in al if pos <= x['i'] < pos + len(s_)]
        a_, b_ = refine(y, SR, us[0]['s'], us[-1]['e'], floor)
        spans.append((a_, b_, us, pos)); pos += len(s_) + 1
    cuts = [max(spans[0][0] - 0.12, 0)]
    for k in range(len(spans) - 1): cuts.append((spans[k][1] + spans[k + 1][0]) / 2)
    cuts.append(min(spans[-1][1] + 0.35, len(y) / SR))
    os.makedirs(out, exist_ok=True)
    for k, (i, (a_, b_, us, p0)) in enumerate(zip(ids, spans)):
        c0, c1 = cuts[k], cuts[k + 1]
        seg = y[int(c0 * SR):int(c1 * SR)].copy()
        fl = int(0.01 * SR); seg[:fl] *= np.linspace(0, 1, fl); seg[-fl:] *= np.linspace(1, 0, fl)
        sf.write(os.path.join(out, f'{i}.wav'), seg, SR)
        meta[i] = dict(passage=pid, lead=round(a_ - c0, 3), dur=round(b_ - a_, 3), tail=round(c1 - b_, 3),
                       gap=round(spans[k + 1][0] - b_, 3) if k + 1 < len(spans) else None,
                       ct=[[x['i'] - p0, round(x['s'] - a_, 3)] for x in us],
                       score=round(float(np.mean([x['score'] for x in us])), 3), take=os.path.basename(f))
    print(pid, os.path.basename(f), ' '.join(f"{i}:{meta[i]['dur']:.1f}/{meta[i]['gap'] or 0:.2f}" for i in ids), flush=True)


def build(work):
    d = os.path.join(work, 'tts_p'); out = os.path.join(work, 'vo'); os.makedirs(out, exist_ok=True)
    sel = json.load(open(os.path.join(d, 'select.json'))) if os.path.exists(os.path.join(d, 'select.json')) else {}
    meta = {}
    units = []
    P = {p[0]: p for p in PASSAGES + [TEASE_P]}
    dbd = os.path.join(work, 'tts_db')
    if os.environ.get('VO_SRC', 'doubao') == 'doubao' and os.path.isdir(dbd):      # 豆包语音合成 2.0：逐段整读，不变调、不变速
        global TARGET_RATE, PITCH_BASE
        TARGET_RATE = None; PITCH_BASE = None
        for pid, ids, mood in PASSAGES + [TEASE_P]:
            units.append((pid, ids, os.path.join(dbd, f'{pid}_0.wav')))
    elif all(g in sel for g in GROUPS):                     # v8：按“大段”一次读完的录音（同一讲述者、同一语速）
        for g, pids in GROUPS.items():
            units.append((g, [i for pp in pids for i in P[pp][1]], os.path.join(d, sel[g])))
    for pid, ids, mood in ([] if units else PASSAGES + [TEASE_P]):
        f = os.path.join(d, sel.get(pid, f'{pid}_0.wav'))
        if os.path.exists(f): units.append((pid, ids, f))
        else:                                                # 该段还没有整段录音：退回逐句录音（work/tts/<id>.wav）
            units += [(f'{pid}:{i}', [i], os.path.join(work, 'tts', f'{i}.wav')) for i in ids]
    for pid, ids, f in units:
        process(pid, ids, f, out, d, meta)
    # 逐句替换：某句在主录音里读错时，改用同组另一条候选录音里的同一句（work/tts_p/override.json：{句: 候选文件}）
    ovp = os.path.join(d, 'override.json') if os.environ.get('VO_SRC', 'doubao') != 'doubao' else '/nonexistent'
    for i, take in (json.load(open(ovp)).items() if os.path.exists(ovp) else []):
        alt = os.path.join(work, 'vo_alt', take[:-4])
        am = json.load(open(os.path.join(alt, 'meta.json')))
        import shutil
        shutil.copy(os.path.join(alt, f'{i}.wav'), os.path.join(out, f'{i}.wav'))
        gap = meta[i]['gap']; meta[i] = dict(am[i], gap=gap, passage=meta[i]['passage'])
        print('  替换', i, '←', take, flush=True)
    json.dump(meta, open(os.path.join(out, 'vo.json'), 'w'), ensure_ascii=False, indent=0)
    return meta


def build_alt(work, take):
    """把某条候选录音也按同样方式切成逐句，存到 work/vo_alt/<take>/（供逐句替换）"""
    d = os.path.join(work, 'tts_p'); g = take.split('_')[0]
    P = {p[0]: p for p in PASSAGES + [TEASE_P]}
    idf = os.path.join(d, g + '.ids.json')                   # 带上下文补录的小段
    ids = json.load(open(idf)) if os.path.exists(idf) else [i for pp in GROUPS[g] for i in P[pp][1]]
    out = os.path.join(work, 'vo_alt', take); meta = {}
    process(g, ids, os.path.join(d, take + '.wav'), out, d, meta)
    json.dump(meta, open(os.path.join(out, 'meta.json'), 'w'), ensure_ascii=False, indent=0)


if __name__ == '__main__':
    if sys.argv[2:3] == ['--alt']:
        for t in sys.argv[3:]: build_alt(sys.argv[1], t)
    else: build(sys.argv[1])
