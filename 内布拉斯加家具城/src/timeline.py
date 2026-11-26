"""根据旁白排出全片时间线：WORK/timeline.json（docs/旁白一致性与自然衔接.md 第二节 5）

整篇旁白一次合成（src/tts_take.py），src/voice_build.py 在停顿正中切成逐句；这里：
  · 段内首尾相接：t_next = t + dur + 原录音里的自然间隔（vo.json 的 gap），不插停顿——放回去就是原来那一条录音；
  · 只在“本来就该停”的地方留白：片名、本章要点卡 + 章节卡、屏幕引语卡（引语读完再接下一句）；
  · 少数关键句之后加“讲故事的停顿”（0.6–1.3 秒），比整体放慢更有效；
  · 配乐反过来按这里给出的叙事节点逐帧对位（src/music.py），旁白不为音乐让步。
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, SOTS

HOOK_START = 0.9           # 开场：音乐起两拍后第一句
AFTER_HOOK = 0.5           # 开场最后一句之后的空气（随后标题重拍）
TITLE_HOLD = 2.8           # 标题段落（含重拍）
PRE_CARD = 0.0
CHAPTER_CARD = 2.2         # 章节卡（v3：配乐在章节号上重拍；去掉了“本章要点”卡，节奏更紧）
TAKEAWAY = 0.0             # v3：不再插“本章要点”卡（要点并到第七章的三条收获里）
TK_PRE = {}
# 旁白引出屏幕引语卡（“他后来写道：”）：引语读完再接下一句（按引语长度）
QUOTE_HOLD = {'c2f': 5.4, 'c2l': 7.0, 'c3z': 4.4, 'c3h': 4.4, 'c4g': 5.4}
# 讲故事的停顿：只放在“该停”的地方——揭晓、转折、数字落地之后（其余句子首尾相接）
STORY = {'h2': 0.5, 'h3': 0.7, 'h4': 0.4, 'h5': 1.0, 'h7': 0.4,
         'c1d': 0.3, 'c1h': 0.7, 'c1j': 0.3, 'c1i': 1.1, 'c1k': 0.6,
         'c2t': 0.4, 'c2e': 0.6, 'c2j': 0.5, 'c2m': 0.9, 'c2k': 0.4,
         'c3m1': 0.3, 'c3m2': 0.5, 'c3d': 0.3, 'c3s': 0.6, 'c3f': 0.4, 'c3g': 0.3, 'c3n1': 0.6, 'c3c': 0.4, 'c3n3': 0.8, 'c3n4': 0.8,
         'c3n5': 0.3, 'c3n6': 0.3, 'c3n7': 0.5, 'c3n8': 0.6, 'c3i': 0.7,
         'c4b': 1.0, 'c4c': 0.4, 'c4d': 0.5, 'c4e': 0.8, 'c4f': 0.8, 'c4h': 1.2,
         'c5c': 0.4, 'c5d': 0.5, 'c5e': 0.4, 'c5f': 0.5,
         'c6a': 0.3, 'c6b': 0.4, 'c6c': 0.4, 'c6e': 0.4, 'c6f': 0.5,
         'c7b': 0.4, 'c7e': 0.8, 'c7l': 0.3, 'c7m': 0.4, 'c7n': 0.4, 'c7o': 0.9, 'c7f': 0.9}
END_GAP = 2.0              # 最后一句之后 → 片尾
DISSOLVE, POST_LOGO = 1.5, 5.8
END_HOLD = 0.8             # 最后一句的落版字再停一会儿，然后化作粒子汇聚成 logo


def build(work, quiet=False):
    vo = json.load(open(os.path.join(work, 'vo', 'vo.json')))
    sotp = os.path.join(work, 'sot', 'sot.json')
    sot = json.load(open(sotp)) if os.path.exists(sotp) else {}
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
                    t += 0.6 + TK_PRE.get(cur, 0)
                    if TAKEAWAY > 0: chapters['tk_' + cur] = [t, t + TAKEAWAY]; t += TAKEAWAY
                    t += PRE_CARD
            chapters[ch] = [0 if ch == 'hook' else t, None]
            if ch != 'hook': t += CHAPTER_CARD
            cur = ch
        elif segs and segs[-1].get('kind') == 'sot':
            t = segs[-1]['start'] + segs[-1]['dur'] + 0.75
        elif segs:
            prev = segs[-1]; pm = vo[prev['id']]
            t = prev['start'] + prev['dur'] + pm['gap'] + QUOTE_HOLD.get(prev['id'], 0) + STORY.get(prev['id'], 0)
        m = vo[lid]
        segs.append(dict(id=lid, ch=ch, text=l[2], start=round(t, 3), dur=m['dur'], ct=m['ct']))
        for sid, so in SOTS.items():                      # 紧跟这句旁白的巴菲特原声
            if so['after'] != lid: continue
            sm = sot[sid]; ts_ = t + m['dur'] + 0.6
            segs.append(dict(id='sot_' + sid, ch=ch, kind='sot', text=so['en'], start=round(ts_, 3), dur=sm['dur'],
                             lead=sm['lead'], len=sm['len'], ph=[[a - sm['lead'], b - sm['lead']] for a, b in sm['ph']], ct=[]))
    last = segs[-1]
    E = last['start'] + last['dur'] + END_GAP
    order = ['hook', 'ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6', 'ch7']
    for a, b in zip(order, order[1:]):
        chapters[a][1] = chapters['title'][0] if a == 'hook' else chapters[b][0]
    chapters['ch7'][1] = E
    logo = E + END_HOLD + DISSOLVE
    total = logo + POST_LOGO
    chapters['end'] = [E, total]
    tl = dict(total=round(total, 3), segs=segs, chapters=chapters, logo=round(logo, 3), dissolve=DISSOLVE)
    json.dump(tl, open(os.path.join(work, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
    return tl


if __name__ == '__main__':
    tl = build(sys.argv[1])
    print('total %.2f s = %d:%05.2f' % (tl['total'], tl['total'] // 60, tl['total'] % 60))
    for k, v in tl['chapters'].items(): print(k, [round(x, 2) for x in v])
