"""根据旁白时长排出全片时间线：work/timeline.json

旁白统一 1.16 倍速（atempo，不变调），去掉首尾静音；句内超过 0.45 秒的停顿压到 0.45 秒（保留换气，去掉空洞）。
呼吸感：章节卡前后、钩子结尾“为什么？”之后、“但这条路，并不平坦”前后都留出整段无旁白的空气。
"""
import sys, os, json, subprocess
import numpy as np, librosa, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, CHAPTERS, TEASE

TEMPO = 1.16
GAP = 0.40                 # 同一章节内两句之间
MAX_PAUSE = 0.45           # 句内停顿上限
PRE_CARD = 0.7             # 章节最后一句之后、下一章节卡之前的留白
PRE_CARD_CH = {'ch2': 0.5, 'ch3': 0.25}  # 第三章卡正好落在配乐 A 的段落重拍上
CARD_EXTRA = {'ch4': 0.9}  # 章节卡之后再多留的空气（“并不平坦”之前）
CH_GAP = {'ch1': 0.35, 'ch2': 0.33}     # 信息密集的章节句间稍紧
GAP_AFTER = {'s05': 1.4, 's11': 0.75, 's17c': 0.4, 's17d': 0.5, 's20': 0.5, 's22': 0.7,
             's27': 0.5, 's34': 0.9, 's37': 0.6, 's38': 0.7, 's39': 0.6, 's43': 0.5, 's44': 0.6, 's45': 0.95,
             's46': 0.8, 's47': 0.9}
HOOK_START = 1.3           # 开场心跳后第一句
TITLE_HOLD = 4.4           # 标题段落（含重拍）
CHAPTER_CARD = 2.0         # 章节卡
END_CARD = 12.0            # 品牌片尾
SR = 48000


def prep(work):
    """变速 + 去静音，写到 work/vo/<id>.wav，返回时长"""
    os.makedirs(os.path.join(work, 'vo'), exist_ok=True)
    durs = {}
    for l in LINES + [('tease',)]:
        src = os.path.join(work, 'tts', l[0] + '.wav'); dst = os.path.join(work, 'vo', l[0] + '.wav')
        y, sr = librosa.load(src, sr=SR)
        iv = librosa.effects.split(y, top_db=40)
        # 句内长停顿压到 MAX_PAUSE（两侧各留一半，40ms 交叉淡化）
        parts = []; xf = int(0.04 * SR)
        for k, (a, b) in enumerate(iv):
            a = max(a - int(0.06 * SR), 0) if k == 0 else a
            b = min(b + int(0.12 * SR), len(y)) if k == len(iv) - 1 else b
            seg = y[a:b].copy()
            if k > 0:
                gap = iv[k][0] - iv[k - 1][1]
                keep = min(gap, int(MAX_PAUSE * SR))
                pre = y[iv[k - 1][1]:iv[k - 1][1] + keep // 2]; post = y[iv[k][0] - keep // 2:iv[k][0]]
                parts += [pre, post]
            parts.append(seg)
        y = np.concatenate(parts)
        sf.write(dst, y, SR)
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


def build(work, durs, anchors=None, quiet=False):
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
            if cur not in (None, 'hook'):
                t += PRE_CARD_CH.get(ch, PRE_CARD) - GAP_AFTER.get(segs[-1]['id'], CH_GAP.get(cur, GAP))
            if ch == 'ch1':                     # 标题段
                t = anchor('title', t)
                chapters['title'] = [t, t + TITLE_HOLD]; t += TITLE_HOLD
            if ch != 'hook':
                t = anchor(ch, t)
                chapters[ch] = [t, None]; t += CHAPTER_CARD + CARD_EXTRA.get(ch, 0)
            else:
                chapters['hook'] = [0, None]
            cur = ch
        t = anchor(lid, t)
        segs.append(dict(id=lid, ch=ch, text=l[2], start=round(t, 3), dur=round(durs[lid], 3)))
        t += durs[lid] + GAP_AFTER.get(lid, CH_GAP.get(ch, GAP))
    t = anchor('end', t + 0.6)
    end_start = t
    if not quiet:
        for r in report: print(r)
    chapters['end'] = [end_start, end_start + END_CARD]
    # 片尾系列预告：logo 重拍之后读出
    tease_at = anchors.get('tease', end_start + 5.0)
    segs.append(dict(id='tease', ch='end', text=TEASE[0], start=round(tease_at, 3), dur=round(durs['tease'], 3)))
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
        {l[0]: sf.info(os.path.join(work, 'vo', l[0] + '.wav')).duration for l in LINES + [('tease',)]}
    plan = os.path.join(work, 'music_plan.json')
    anchors = json.load(open(plan))['anchors'] if os.path.exists(plan) else {}
    tl = build(work, durs, anchors)
    print('total %.2f s = %d:%05.2f' % (tl['total'], tl['total'] // 60, tl['total'] % 60))
    for k, v in tl['chapters'].items(): print(k, [round(x, 2) for x in v])
