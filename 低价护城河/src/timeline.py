"""时间线：旁白逐句排布 + 章节起点对齐配乐网格。
python3 src/timeline.py WORK → WORK/timeline.json
被 import 时提供 T(id) 句首、WT(id, '词') 某词发声时刻、CH 章节表。
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, BREAK

BPM = 80.0; BEAT = 60 / BPM; BAR = 4 * BEAT
INTRO = 1.5            # 冷开场：第一句前的环境声 + 画面起
OUTRO = 12.0           # 最后一句后：片尾品牌动画
CHAPTERS = [  # (起始句, 章节标签, 英文)
    ('o1', '', ''), ('p1', '01 · 第一性原理', 'FIRST PRINCIPLES'), ('d1', '02 · 两位大师', 'THE CLASH'),
    ('k1', '03 · 三个条件', 'THREE CONDITIONS'), ('g1', '04 · 中国考题', 'CHINA'), ('q1', '05 · 底线', 'QUALITY'),
    ('z1', '06 · 答案', 'THE ANSWER')]
SNAP = {c[0] for c in CHAPTERS[1:]}


def build(work):
    vo = json.load(open(os.path.join(work, 'vo.json')))
    t = INTRO; segs = []
    for lid, *_ in LINES:
        t += BREAK.get(lid, 0.0)
        if lid in SNAP:  # 章节句首（第一个发声字）对齐半小节
            sp = vo[lid]["speech"][0]; g = BEAT
            k = -(-(t + sp) // g); t = k * g - sp
        segs.append(dict(id=lid, start=round(t, 4), dur=vo[lid]['dur'], speech=vo[lid]['speech'],
                         chars=vo[lid]['chars'], sub=vo[lid]['sub'], text=vo[lid]['text']))
        t += vo[lid]['dur']
    total = t + OUTRO
    ch = []
    for i, (lid, name, en) in enumerate(CHAPTERS):
        s = next(x for x in segs if x['id'] == lid)['start']
        ch.append(dict(id=lid, name=name, en=en, start=s))
    tl = dict(total=round(total, 3), bpm=BPM, segs=segs, chapters=ch)
    json.dump(tl, open(os.path.join(work, 'timeline.json'), 'w'), ensure_ascii=False, indent=0)
    return tl


class TL:
    def __init__(self, work):
        self.d = json.load(open(os.path.join(work, 'timeline.json')))
        self.seg = {s['id']: s for s in self.d['segs']}
        self.total = self.d['total']

    def T(self, lid): return self.seg[lid]['start']
    def E(self, lid): return self.seg[lid]['start'] + self.seg[lid]['dur']
    def S(self, lid): return self.seg[lid]['start'] + self.seg[lid]['speech'][0]   # 第一个字发声
    def SE(self, lid): return self.seg[lid]['start'] + self.seg[lid]['speech'][1]  # 最后一个字结束

    def WT(self, lid, sub, end=False, nth=0):
        s = self.seg[lid]; txt = s['text']; k = -1
        for _ in range(nth + 1): k = txt.find(sub, k + 1)
        if k < 0: raise KeyError((lid, sub))
        # chars 与 text 逐字对应（含标点）
        c = s['chars'][min(k + (len(sub) - 1 if end else 0), len(s['chars']) - 1)]
        return s['start'] + (c[2] if end else c[1])


if __name__ == '__main__':
    tl = build(sys.argv[1])
    print('total %.1fs' % tl['total'])
    for c in tl['chapters']: print('%6.2f %s' % (c['start'], c['name']))
