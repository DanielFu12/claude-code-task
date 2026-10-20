"""第五版时间线：由 story.STORY 顺序拼接。

解说时长取自 work/vo_index.json（tts3.py 生成的逐句时长、逐字时间、句间停顿）；
还没有配音时按字数估算（约 4.6 字/秒），方便先做画面。
配乐节点（music.json，由 music3.py 分析配乐得到）用于把片名、总结、品牌字卡到重拍上：
做法是在相应段落前补一小段停顿，让它正好落在重拍上，不改动任何配音和原声。
"""
import json, os, re
import story as ST
from clips import CLIPS, length

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
WORK = os.path.join(ROOT, 'work')
VO_INDEX = os.path.join(WORK, 'vo_index.json')
MUSIC = os.path.join(ROOT, 'assets', 'music3', 'music3.json')
PUNCT = '，。；：？！、—…“”《》·（）,.;:?! 「」'

CLIP_PRE, CLIP_POST = 0.55, 0.50      # 原声前后留白（窗口淡入淡出）
SENT_GAP = 0.32                       # 估算时的句间停顿
GROUP_PRE = 0.25
TITLE_LEN = 6.4
ANIM_MIN = {'G10': 21.0, 'G11': 25.5, 'G12': 14.5, 'G13': 15.3}   # 动画段最短时长（给画面留出呼吸）
SUMMARY_LEN = 7.0
BRAND_LEN = 13.5
BRAND_BEAT = 2.4                      # 片尾开始后多少秒出现「巴芒价值」字标（落在配乐强拍上）


def _content(s):
    return [c for c in s if c not in PUNCT and not c.isspace()]


def load_vo():
    if os.path.exists(VO_INDEX):
        return json.load(open(VO_INDEX))
    return {}


VO = load_vo()
HAVE_VO = bool(VO)


def sent_info(sid, text):
    """(时长, 逐字时间 [(t0, t1, 字)], 到下一句的停顿)"""
    if sid in VO:
        v = VO[sid]
        return v['dur'], [tuple(w) for w in v['words']], v.get('gap', SENT_GAP)
    cs = _content(ST.SAY.get(sid, text))
    d = len(cs) / 4.6 / ST.TEMPO + 0.25
    words = [(0.1 + i * (d - 0.3) / len(cs), 0.1 + (i + 1) * (d - 0.3) / len(cs), c) for i, c in enumerate(cs)]
    return d, words, SENT_GAP


def music_anchors():
    return json.load(open(MUSIC)) if os.path.exists(MUSIC) else {}


def build(anim_len=None):
    """返回 (segments, sentences)
    segments: [dict(kind, id, t0, t1)]；sentences: {sid: dict(t0, t1, text, words(绝对时间), group)}"""
    M = music_anchors()
    segs, sents = [], {}
    t = 0.0
    for item in ST.STORY:
        kind, gid = item[0], item[1]
        if kind == 'clip':
            L = length(CLIPS[gid])
            segs.append(dict(kind='clip', id=gid, t0=t, a0=t + CLIP_PRE, t1=t + CLIP_PRE + L + CLIP_POST))
            t = segs[-1]['t1']
        elif kind == 'title':
            segs.append(dict(kind='title', id='title', t0=t, t1=t + TITLE_LEN)); t += TITLE_LEN
        elif kind == 'brand':
            segs.append(dict(kind='brand', id='brand', t0=t, t1=t + BRAND_LEN)); t += BRAND_LEN
        else:
            g0 = t; t += GROUP_PRE
            items = item[2]
            for k, (sid, text) in enumerate(items):
                d, words, gap = sent_info(sid, text)
                sents[sid] = dict(t0=t, t1=t + d, text=text, group=gid, kind=kind,
                                  words=[(t + a, t + b, c) for a, b, c in words])
                t += d + (gap if k < len(items) - 1 else 0.0)
            t += 0.45
            if kind == 'anim':
                t = max(t, g0 + (anim_len or ANIM_MIN).get(gid, 0))
            if kind == 'summary':
                # 配乐是按段落对齐的（总结句 = 高潮重拍），总结段的长度让品牌字标正好落在其后的强拍上
                L = SUMMARY_LEN
                if 'climax' in M:
                    L = M['climax']['brand_beat'] - M['climax']['hit'] - BRAND_BEAT
                t = g0 + L
            segs.append(dict(kind=kind, id=gid, t0=g0, t1=t))
    return segs, sents


def _solve():
    """让「四百多倍」正好落在高潮配乐中段的重拍上（配乐按总结句对齐，所以调整 G10 的长度）"""
    segs, sents = build()
    M = music_anchors()
    if 'climax' not in M or 'mid_hit' not in M['climax'] or 'A03' not in sents:
        return segs, sents
    sg = {x['id']: x for x in segs}
    globals()['SENTS'] = sents
    d = wt('A03', '四百多倍') - sg['G10']['t0']
    S = sum(sg[g]['t1'] - sg[g]['t0'] for g in ('G11', 'G12', 'G13'))
    L10 = M['climax']['hit'] - M['climax']['mid_hit'] + d - S
    need = sg['G10']['t1'] - sg['G10']['t0']
    if L10 < (sents['A03']['t1'] - sg['G10']['t0']) + 0.8:      # 不够放下解说：放弃对齐
        return segs, sents
    lens = dict(ANIM_MIN); lens['G10'] = L10
    return build(lens)




def seg_at(t):
    for s in SEGS:
        if s['t0'] <= t < s['t1']:
            return s
    return SEGS[-1]


def seg(kind_or_id):
    for s in SEGS:
        if s['id'] == kind_or_id or s['kind'] == kind_or_id:
            return s
    raise KeyError(kind_or_id)


def wt(sid, kw, end=False):
    """句子 sid 中关键词 kw 开始（或结束）被读到的时刻"""
    s = SENTS[sid]
    chars = ''.join(c for _, _, c in s['words'])
    k = chars.find(''.join(_content(kw)))
    if k < 0:
        return s['t1'] if end else s['t0']
    if end:
        k = k + len(_content(kw)) - 1
        return s['words'][k][1]
    return s['words'][k][0]


def gh_breaks():
    """「被速度裹挟」画面里四段曲线各自断掉的时刻（越切越快）：画面（bridges.gh）与混音（audio3 的低频点）共用"""
    h3 = SENTS['H03']['t0']; stop = wt('H03', '每一次失去')
    ks = [h3 + 0.25, wt('H03', '追风口'), wt('H03', '频繁') + 0.15, wt('H03', '切换') + 0.4]
    ks = [min(max(k, ks[i - 1] + 0.35 if i else k), stop - 0.35 * (4 - i)) for i, k in enumerate(ks)]
    return ks, ks[1:] + [stop]


SENTS = {}
SEGS, SENTS = _solve()
DUR = SEGS[-1]['t1']


if __name__ == '__main__':
    for s in SEGS:
        print(f"{s['kind']:7s} {s['id']:6s} {s['t0']:7.2f} → {s['t1']:7.2f}  ({s['t1'] - s['t0']:5.2f})")
    print('DUR', round(DUR, 2), 'have_vo', HAVE_VO)
