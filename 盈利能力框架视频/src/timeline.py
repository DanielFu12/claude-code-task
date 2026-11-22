"""把旁白排到节拍网格上，生成 work/timeline.json。

- 120 BPM：一拍 0.5 s，一小节 2 s。
- 带 sting 的场景（章节开头）一律从小节线（重拍）开始，配乐在这里落下冲击音。
- 每句旁白的每个字都有时间戳；脚本里的 [cue] 换算成绝对时刻。
- 字幕按标点切分，每条不超过 MAXSUB 个字。
"""
import json, os, sys
import numpy as np, soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from script import SCENES, CHAPTERS
from tts import parse, tts_text, wav_path, trim, align, SR, PUNCT

BPM = 120
BEAT = 60 / BPM
BAR = BEAT * 4
GAP = 0.30          # 句间停顿
MAXSUB = 20
WORK = os.path.join(HERE, '..', 'work')


def qtime(t, grid=BEAT / 2):
    """把提示点量化到八分音符网格（音画同时落在这个时刻）"""
    return round(round(t / grid) * grid, 4)


def next_bar(t, min_lead=0.0):
    k = int(np.ceil((t + min_lead) / BAR - 1e-6))
    return k * BAR


def split_subs(text, times, t0):
    """按标点切字幕；返回 [(文本, 开始, 结束)]"""
    out, cur, cs = [], '', 0
    clauses, s = [], 0
    for i, ch in enumerate(text):
        if ch in PUNCT:
            clauses.append((s, i + 1)); s = i + 1
    if s < len(text): clauses.append((s, len(text)))
    groups = []
    for a, b in clauses:
        if groups and (b - groups[-1][0]) <= MAXSUB and (groups[-1][1] - groups[-1][0]) <= 7 \
                and text[groups[-1][1] - 1] in '，、':
            groups[-1] = (groups[-1][0], b)
        else:
            groups.append((a, b))
    for a, b in groups:
        seg = text[a:b].strip('，。；：、 ')
        seg = seg.replace('；', '，').strip('，')
        if not seg: continue
        out.append((seg, t0 + times[a], t0 + times[b]))
    return out


def build():
    T = 0.0
    scenes, subs, utts = [], [], []
    for si, sc in enumerate(SCENES):
        if sc.get('sting') and si > 0:
            T = next_bar(T, 0.25)
        start = T
        t = start + sc['lead']
        cues = {}
        su = []
        for u in sc['say']:
            text, cidx = parse(u)
            p = wav_path(tts_text(text))
            y, sr = sf.read(p)
            if y.ndim > 1: y = y.mean(1)
            y, _ = trim(y)
            times = align(text, y)
            dur = len(y) / SR
            for k, i in cidx.items():
                cues[k] = t + float(times[min(i, len(text))])
            subs += split_subs(text, times, t)
            su.append(dict(text=text, start=t, end=t + dur, wav=os.path.relpath(p, WORK),
                           ct=[round(t + float(x), 3) for x in times]))
            gap = GAP + (0.25 if text.endswith(('？', '。')) else 0.0)
            t += dur + gap
        if sc['say']:
            t -= gap
        end = t + sc['tail']
        cq = {k: qtime(v) for k, v in cues.items()}
        scenes.append(dict(id=sc['id'], ch=sc['ch'], start=start, end=end, cues=cues, cq=cq, utts=su,
                           sting=bool(sc.get('sting'))))
        utts += su
        T = end
    total = next_bar(T)
    # 每个场景的结束时间 = 下一个场景的开始（画面连续）
    for a, b in zip(scenes, scenes[1:]):
        a['end'] = b['start']
    scenes[-1]['end'] = total
    tl = dict(bpm=BPM, beat=BEAT, bar=BAR, total=total, scenes=scenes,
              subs=[dict(text=s, start=a, end=b) for s, a, b in subs],
              chapters=CHAPTERS)
    json.dump(tl, open(os.path.join(WORK, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
    return tl


if __name__ == '__main__':
    tl = build()
    for s in tl['scenes']:
        print(f"{s['id']:8s} {s['start']:7.2f} -> {s['end']:7.2f}  ({s['end'] - s['start']:5.1f}s) bars {s['start'] / BAR:6.1f}")
    print('TOTAL', tl['total'], f"{int(tl['total'] // 60)}:{tl['total'] % 60:04.1f}", 'subs', len(tl['subs']))
