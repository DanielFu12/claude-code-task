"""根据旁白排出全片时间线：work/timeline.json

旁白按段落整段录制（src/tts_passage.py），src/voice_build.py 对齐后切成逐句；这里：
  · 同一段落内：句与句之间保留原录音里的自然停顿（真人换气），不变速、不压停顿；
  · 段落之间、章节卡前后、钩子“为什么？”之后、“但这条路，并不平坦”之前：留出整段空气；
  · 配乐反过来按这里给出的叙事节点逐帧对位（src/score.py），旁白不再为音乐让步。
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, TEASE, SOTS

HOOK_START = 1.2           # 开场心跳后第一句
AFTER_HOOK = 0.6           # “为什么？”之后的空气（随后标题重拍）
TITLE_HOLD = 3.0           # 标题段落（含重拍）
PRE_CARD = -0.5            # v3：章节卡在“本章要点”卡淡出前 0.5s 就开始接上（两卡交接，中间不掉黑）
CHAPTER_CARD = 2.7         # 章节卡
CARD_EXTRA = {'ch5': 0.2}  # 章节卡之后再多留的空气
PASSAGE_GAP = 0.55          # 同一章节内两个段落之间
GAP_MIN, GAP_MAX = 0.35, 0.7   # 段内自然停顿的上下限（极端值才修正）
GAP_EXTRA = {'h1': 0.45, 'h2': 0.3, 'c1c': 0.4, 'c1e': 0.45, 'c2c': 0.5, 'c2e': 0.3, 'c3c': 0.3, 'c3d': 0.3, 'c4b': 0.3, 'c4c': 1.2, 'c4d': 0.6, 'c4g2': 0.2, 'c4h': 0.7, 'c4i': 0.6, 'c5a': 0.6, 'c5c': 0.5, 'c5e': 0.3, 'c5g': 0.3, 'c5h': 0.4, 'c6a2': 0.3, 'c6c': 0.5, 'c6e': 0.3, 'c6h': 0.5, 'c6i': 0.6, 'c1a': 0.3, 'c1a2': 0.5, 'c1d': 0.4, 'c1h': 0.3, 'c2d': 0.4, 'c3e': 0.5, 'c3h': 0.6, 'c4a': 0.4, 'c4e': 0.6, 'c4f': 0.6, 'c5k': 0.5, 'c6c2': 0.6}   # v3：关键数字/图表出现后多留一点时间看清（audit ③）   # 引语卡与转折前后多留一点（c4c“是我发起的”后留白）   # 转折与主题句前后多留一点
SOT_PRE, SOT_POST = 0.55, 0.75   # 引入句 → 巴菲特原声 → 下一句旁白（原声前后留空气，画面切换）
SOT_PRE_X = {'mlousy': 0.9, 'mcoke': 0.8, 'trick': 1.1}
TK_PRE = {'ch5': 1.0}     # v3：章末画面需要多看一会儿的章节，在要点卡前多留   # v3：引入的问题在屏幕上多停一会儿，再切原声
TAKEAWAY = 4.2            # 第一至六章结尾的“本章要点”卡
END_GAP = 1.8              # 最后一句之后 → 片尾卡
TEASE_LEAD, DISSOLVE, POST_LOGO = 0.8, 1.5, 5.8
TEASE_HOLD = 3.0          # v3：预告旁白结束后，引语与两行预告字再停 2.4s，然后化作粒子   # 片尾：预告 → 文字化作粒子汇聚成 logo → 品牌字/关注语 → 淡出


def build(work, quiet=False):
    vo = json.load(open(os.path.join(work, 'vo', 'vo.json')))
    sot = json.load(open(os.path.join(work, 'sot', 'sot.json')))
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
                    t += 0.35 + TK_PRE.get(cur, 0); chapters['tk_' + cur] = [t, t + TAKEAWAY]; t += TAKEAWAY
                    t += PRE_CARD
            chapters[ch] = [0 if ch == 'hook' else t, None]
            if ch != 'hook': t += CHAPTER_CARD + CARD_EXTRA.get(ch, 0)
            cur = ch
        elif segs and segs[-1].get('kind') == 'sot':
            t = segs[-1]['start'] + segs[-1]['dur'] + SOT_POST
        elif segs:
            prev = segs[-1]; pm = vo[prev['id']]
            same = pm['passage'].split(':')[0] == vo[lid]['passage'].split(':')[0]
            if not same: gap = PASSAGE_GAP
            elif pm['gap'] is None: gap = 0.55                  # 退回逐句录音时的句间停顿
            else: gap = min(max(pm['gap'], GAP_MIN), GAP_MAX)
            t = prev['start'] + prev['dur'] + gap + GAP_EXTRA.get(prev['id'], 0)
        m = vo[lid]
        segs.append(dict(id=lid, ch=ch, text=l[2], start=round(t, 3), dur=m['dur'], ct=m['ct']))
        for sid, so in SOTS.items():                      # 紧跟这句旁白的巴菲特原声
            if so['after'] != lid: continue
            sm = sot[sid]; ts_ = t + m['dur'] + SOT_PRE_X.get(sid, SOT_PRE)
            segs.append(dict(id='sot_' + sid, ch=ch, kind='sot', text=so['en'], start=round(ts_, 3), dur=sm['dur'],
                             lead=sm['lead'], len=sm['len'], ph=[[a - sm['lead'], b - sm['lead']] for a, b in sm['ph']], ct=[]))
    last = segs[-1]
    E = last['start'] + last['dur'] + END_GAP
    order = ['hook', 'ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6', 'ch7']
    for a, b in zip(order, order[1:]):
        chapters[a][1] = chapters['title'][0] if a == 'hook' else chapters[b][0]
    chapters = {k: v for k, v in chapters.items()}
    chapters['ch7'][1] = E
    tm = vo['tease']
    ts = E + TEASE_LEAD
    segs.append(dict(id='tease', ch='end', text=TEASE[0], start=round(ts, 3), dur=tm['dur'], ct=tm['ct']))
    logo = ts + tm['dur'] + TEASE_HOLD + DISSOLVE
    total = logo + POST_LOGO
    chapters['end'] = [E, total]
    tl = dict(total=round(total, 3), segs=segs, chapters=chapters, logo=round(logo, 3), dissolve=DISSOLVE)
    json.dump(tl, open(os.path.join(work, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
    return tl


if __name__ == '__main__':
    tl = build(sys.argv[1])
    print('total %.2f s = %d:%05.2f' % (tl['total'], tl['total'] // 60, tl['total'] % 60))
    for k, v in tl['chapters'].items(): print(k, [round(x, 2) for x in v])
