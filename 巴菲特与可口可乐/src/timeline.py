"""根据旁白时长排出全片时间线：work/timeline.json

旁白统一 1.12 倍速（atempo，不变调），去掉首尾静音；
章节之间留出音乐重拍与章节卡的时间。
"""
import sys, os, json, subprocess
import numpy as np, librosa, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, CHAPTERS

TEMPO = 1.12
GAP = 0.34                 # 同一章节内两句之间
GAP_AFTER = {'s02': 0.5, 's05': 1.0, 's12': 0.6, 's20': 0.45, 's23': 0.45, 's24': 0.4, 's27': 0.5,
             's30': 0.4, 's32': 0.7, 's34': 0.4, 's37': 0.5, 's38': 0.6, 's39': 0.4, 's42': 0.7,
             's43': 0.4, 's44': 0.4, 's45': 0.7, 's46': 0.7, 's47': 0.8}
HOOK_START = 1.6           # 开场 1.6s 心跳后第一句
TITLE_HOLD = 4.6           # 标题段落（含重拍）
CHAPTER_CARD = 2.0         # 章节卡
END_CARD = 13.0            # 品牌片尾
SR = 48000


def prep(work):
    """变速 + 去静音，写到 work/vo/<id>.wav，返回时长"""
    os.makedirs(os.path.join(work, 'vo'), exist_ok=True)
    durs = {}
    for l in LINES:
        src = os.path.join(work, 'tts', l[0] + '.wav'); dst = os.path.join(work, 'vo', l[0] + '.wav')
        y, sr = librosa.load(src, sr=SR)
        iv = librosa.effects.split(y, top_db=40)
        a = max(iv[0][0] - int(0.06 * SR), 0); b = min(iv[-1][1] + int(0.12 * SR), len(y))
        sf.write(dst, y[a:b], SR)
        # ffmpeg atempo（WSOLA）适合人声，变速不变调
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', dst, '-af', f'atempo={TEMPO}',
                        '-ar', str(SR), dst + '.tmp.wav'], check=True)
        os.replace(dst + '.tmp.wav', dst)
        y, _ = sf.read(dst, dtype='float32')
        fade = int(0.02 * SR); y[:fade] *= np.linspace(0, 1, fade); y[-fade:] *= np.linspace(1, 0, fade)
        sf.write(dst, y, SR)
        durs[l[0]] = len(y) / SR
    return durs


# 音乐卡点：某个章节/句子必须从音乐的某个节点开始（单位：成片秒）。
# 由 music_plan.py 根据所选配乐的重拍位置给出；自然排布更早时，空出的时间
# 均匀分给前面的句间停顿；自然排布更晚则报告「超时」。
ANCHORS = {}


def spread(segs, i0, i1, slack):
    """把 slack 秒均匀加到 segs[i0:i1] 的起点上（逐句递增）"""
    n = i1 - i0
    for k in range(i0, i1):
        segs[k]['start'] = round(segs[k]['start'] + slack * (k - i0 + 1) / (n + 1), 3)


def build(work, durs, anchors=None):
    anchors = anchors if anchors is not None else ANCHORS
    t = HOOK_START
    segs, chapters = [], {}
    cur = None; last_anchor_idx = 0
    report = []

    def anchor(key, t):
        nonlocal last_anchor_idx
        if key not in anchors: return t
        a = anchors[key]
        if a < t - 0.05: report.append(f'超时 {key}: 自然 {t:.2f} > 卡点 {a:.2f}')
        elif a > t:
            slack = a - t
            spread(segs, last_anchor_idx, len(segs), min(slack, 0.35 * (len(segs) - last_anchor_idx)))
            report.append(f'留白 {key}: {slack:.2f}s')
        last_anchor_idx = len(segs)
        return max(a, t)

    for l in LINES:
        lid, ch = l[0], l[1]
        if ch != cur:
            if ch == 'ch1':                     # 标题段
                t = anchor('title', t)
                chapters['title'] = [t, t + TITLE_HOLD]; t += TITLE_HOLD
            if ch != 'hook':
                t = anchor(ch, t)
                chapters[ch] = [t, None]; t += CHAPTER_CARD
            else:
                chapters['hook'] = [0, None]
            cur = ch
        t = anchor(lid, t)
        segs.append(dict(id=lid, ch=ch, text=l[2], start=round(t, 3), dur=round(durs[lid], 3)))
        t += durs[lid] + GAP_AFTER.get(lid, GAP)
    t = anchor('end', t + 0.6)
    end_start = t
    for r in report: print(r)
    chapters['end'] = [end_start, end_start + END_CARD]
    order = ['hook', 'ch1', 'ch2', 'ch3', 'ch4', 'ch5']
    for a, b in zip(order, order[1:]):
        chapters[a][1] = chapters['title'][0] if a == 'hook' else chapters[b][0]
    chapters['ch5'][1] = end_start
    total = end_start + END_CARD
    tl = dict(total=round(total, 3), segs=segs, chapters=chapters, tempo=TEMPO)
    json.dump(tl, open(os.path.join(work, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
    return tl


if __name__ == '__main__':
    work = sys.argv[1]
    durs = prep(work) if '--keep' not in sys.argv else \
        {l[0]: sf.info(os.path.join(work, 'vo', l[0] + '.wav')).duration for l in LINES}
    plan = os.path.join(work, 'music_plan.json')
    anchors = json.load(open(plan))['anchors'] if os.path.exists(plan) else {}
    tl = build(work, durs, anchors)
    print('total %.2f s = %d:%05.2f' % (tl['total'], tl['total'] // 60, tl['total'] % 60))
    for k, v in tl['chapters'].items(): print(k, [round(x, 2) for x in v])
