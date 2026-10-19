"""根据旁白排出全片时间线：work/timeline.json

旁白按段落整段录制（src/tts_passage.py），src/voice_build.py 对齐后切成逐句；这里：
  · 同一段落内：句与句之间保留原录音里的自然停顿（真人换气），不变速、不压停顿；
  · 段落之间、章节卡前后、钩子“为什么？”之后、“但这条路，并不平坦”之前：留出整段空气；
  · 配乐反过来按这里给出的叙事节点逐帧对位（src/score.py），旁白不再为音乐让步。
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, TEASE

HOOK_START = 1.2           # 开场心跳后第一句
AFTER_HOOK = 1.0           # “为什么？”之后的空气（随后标题重拍）
TITLE_HOLD = 4.0           # 标题段落（含重拍）
PRE_CARD = 0.55             # 章节最后一句之后、下一章节卡之前
CHAPTER_CARD = 1.8         # 章节卡
CARD_EXTRA = {'ch4': 0.4}  # 章节卡之后再多留的空气（“并不平坦”之前）
PASSAGE_GAP = 0.7          # 同一章节内两个段落之间
GAP_MIN, GAP_MAX = 0.3, 0.75   # 段内自然停顿的上下限（极端值才修正）
GAP_EXTRA = {'s45': 0.15}   # 核心句前后再多留一点
END_GAP = 0.7              # 最后一句之后 → 片尾卡
TEASE_LEAD, DISSOLVE, POST_LOGO = 0.35, 1.4, 5.6   # 片尾：预告 → 文字化作粒子汇聚成 logo → 品牌字/关注语 → 淡出


def build(work, quiet=False):
    vo = json.load(open(os.path.join(work, 'vo', 'vo.json')))
    t = HOOK_START
    segs, chapters = [], {}
    cur = None
    for k, l in enumerate(LINES):
        lid, ch = l[0], l[1]
        if ch != cur:
            if cur is not None:
                last = segs[-1]; t = last['start'] + last['dur']
                if cur == 'hook':
                    t += AFTER_HOOK
                    chapters['title'] = [t, t + TITLE_HOLD]; t += TITLE_HOLD
                else:
                    t += PRE_CARD
            chapters[ch] = [0 if ch == 'hook' else t, None]
            if ch != 'hook': t += CHAPTER_CARD + CARD_EXTRA.get(ch, 0)
            cur = ch
        elif segs:
            prev = segs[-1]; pm = vo[prev['id']]
            same = pm['passage'].split(':')[0] == vo[lid]['passage'].split(':')[0]
            if not same: gap = PASSAGE_GAP
            elif pm['gap'] is None: gap = 0.55                  # 退回逐句录音时的句间停顿
            else: gap = min(max(pm['gap'], GAP_MIN), GAP_MAX)
            t = prev['start'] + prev['dur'] + gap + GAP_EXTRA.get(prev['id'], 0)
        m = vo[lid]
        segs.append(dict(id=lid, ch=ch, text=l[2], start=round(t, 3), dur=m['dur'], ct=m['ct']))
    last = segs[-1]
    E = last['start'] + last['dur'] + END_GAP
    order = ['hook', 'ch1', 'ch2', 'ch3', 'ch4', 'ch5']
    for a, b in zip(order, order[1:]):
        chapters[a][1] = chapters['title'][0] if a == 'hook' else chapters[b][0]
    chapters['ch5'][1] = E
    tm = vo['tease']
    ts = E + TEASE_LEAD
    segs.append(dict(id='tease', ch='end', text=TEASE[0], start=round(ts, 3), dur=tm['dur'], ct=tm['ct']))
    logo = ts + tm['dur'] + DISSOLVE
    total = logo + POST_LOGO
    chapters['end'] = [E, total]
    tl = dict(total=round(total, 3), segs=segs, chapters=chapters, logo=round(logo, 3), dissolve=DISSOLVE)
    json.dump(tl, open(os.path.join(work, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
    return tl


if __name__ == '__main__':
    tl = build(sys.argv[1])
    print('total %.2f s = %d:%05.2f' % (tl['total'], tl['total'] // 60, tl['total'] % 60))
    for k, v in tl['chapters'].items(): print(k, [round(x, 2) for x in v])
