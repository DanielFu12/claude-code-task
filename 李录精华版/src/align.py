"""把 script_en.txt 对齐到 YouTube 自动字幕（逐词时间码），并算出剪辑片段。
用法: python3 align.py <orig.en-orig.json3> <script_en.txt> <out.json>

1. 每句先用 3-gram 投票粗定位，取高置信度句子确定每章在原片中的范围；
2. 在该范围内对整章做序列比对（difflib），得到 文稿词 → 原片词 的映射；
3. 相邻两句在原片中间隔超过 GAP 个词，说明中间有被删掉的内容，在此处剪开。
输出 JSON: {sentences:[{ch,para,text,i0,i1,t0,t1}], segments:[{ch,t0,t1,s0,s1}]}
"""
import json, re, sys
from difflib import SequenceMatcher

NUM = {'zero':'0','one':'1','two':'2','three':'3','four':'4','five':'5','six':'6','seven':'7','eight':'8','nine':'9',
       'ten':'10','twenty':'20','thirty':'30','forty':'40','fifty':'50','sixty':'60','hundred':'100','colombia':'columbia'}
GAP = 14         # 原片中两句之间多出超过 GAP 个词且超过 GAP_S 秒 → 剪开
GAP_S = 5.0
# 人工校正的片段起止（秒），按章节；自动比对把前文的零散词误配为开头时用
SEG_FIX = {5: dict(t0=3720.45)}

def norm(w):
    w = re.sub(r"[^a-z0-9']", '', w.lower().replace('’', "'"))
    return NUM.get(w, w)

def words_asr(path):
    out = []
    for e in json.load(open(path))['events']:
        t = e.get('tStartMs', 0)
        for s in e.get('segs') or []:
            for w in s['utf8'].split():
                n = norm(w)
                if n: out.append([n, (t + s.get('tOffsetMs', 0)) / 1000])
    for i, w in enumerate(out):
        nxt = out[i + 1][1] if i + 1 < len(out) else w[1] + .5
        w.append(min(nxt, w[1] + 0.9))
    return out

def tokens(text):
    text = re.sub(r'\[[^\]]*\]', ' ', text)
    return [t for t in (norm(w) for w in re.sub(r'[—–\-/]', ' ', text).split()) if t]

def sentences(path):
    res = []
    for line in open(path, encoding='utf8'):
        line = line.strip()
        if not line: continue
        if line.startswith('## '): ch = int(line[3:]); pi = 0; continue
        pi += 1; note = False
        for s in re.split(r'(?<=[.!?])\s+(?=[A-Z"\[“])', line):
            starts = s.startswith('[')
            res.append(dict(ch=ch, para=pi, text=s, tok=tokens(s), note=note or starts))
            note = (note or starts) and not s.rstrip().endswith(']')
    return res

def rough(toks, atok, grams):
    votes = {}
    for j in range(len(toks) - 2):
        for i in grams.get(tuple(toks[j:j+3]), []): votes[i - j] = votes.get(i - j, 0) + 1
    if not votes: return None, 0
    off = max(votes, key=votes.get)
    return off, votes[off] / max(1, len(toks) - 2)

def main(asr_p, script_p, out_p):
    A = words_asr(asr_p); atok = [w[0] for w in A]
    grams = {}
    for i in range(len(atok) - 2): grams.setdefault(tuple(atok[i:i+3]), []).append(i)
    S = sentences(script_p)
    segs = []
    for ch in sorted({s['ch'] for s in S}):
        CS = [s for s in S if s['ch'] == ch]
        offs = sorted(o for o, sc in (rough(s['tok'], atok, grams) for s in CS) if o is not None and sc >= .5)
        med = offs[len(offs) // 2]
        offs = [o for o in offs if abs(o - med) < 2500]
        lo, hi = max(0, offs[0] - 250), min(len(atok), offs[-1] + 400)
        ctok, owner = [], []
        for k, s in enumerate(CS):
            ctok += s['tok']; owner += [k] * len(s['tok'])
        sm = SequenceMatcher(None, ctok, atok[lo:hi], autojunk=False)
        m = [None] * len(ctok)
        for b in sm.get_matching_blocks():
            if b.size < 2 and not (b.size == 1 and len(ctok[b.a]) > 3): continue
            for d in range(b.size): m[b.a + d] = lo + b.b + d
        for k, s in enumerate(CS):
            js = [j for j in range(len(ctok)) if owner[j] == k]
            # 只认成片匹配的词（与句内相邻词在原片中也相邻），排除零散误配
            idx = [m[j] for j in js if m[j] is not None and any(
                jj in js and m[jj] is not None and abs(m[jj] - m[j]) == 1 for jj in (j - 1, j + 1))]
            loose = [m[j] for j in js if m[j] is not None]
            if not idx: idx = loose
            s['l0'], s['l1'] = (min(loose), max(loose)) if loose else (None, None)   # 宽松范围：只用于判断剪辑点
            s['n_match'] = len(idx); s['n_tok'] = len(s['tok'])
            s['i0'], s['i1'] = (min(idx), max(idx)) if idx else (None, None)
            s['wt'] = [A[m[j]][1] if m[j] is not None else None for j in range(len(ctok)) if owner[j] == k]
        # 匹配太弱的句子（口语改写较多）先不参与切分，之后在前后句之间插值
        for s in CS: s['ok'] = s['i0'] is not None and s['n_match'] >= max(2, .3 * s['n_tok'])
        allCS = CS; CS = [s for s in CS if s['ok']]
        cur = None; bridge = False
        for s in allCS:
            if not s['ok']: bridge = True; continue      # 中间夹着改写较多的原话：不在这里剪
            gap_s = A[s['l0']][1] - A[cur['i1']][2] if cur else 0
            if cur and s['l0'] > cur['i1'] - 3 and (s['l0'] - cur['i1'] - 1 <= GAP or gap_s < GAP_S or (bridge and gap_s < 15)):
                cur['i1'] = max(cur['i1'], s['i1'])
            else:
                if cur: segs.append(cur)
                cur = dict(ch=ch, i0=s['l0'], i1=s['i1'])
            if s['l1'] - s['i1'] <= 8: cur['i1'] = max(cur['i1'], s['l1'])   # 句尾零散词也收进来，避免截掉最后一个词
            bridge = False
        segs.append(cur)
        for s in allCS:
            s['keep'] = not s['note']      # 方括号整句是编者补注，没有说出口
    for g in segs:
        g['t0'], g['t1'] = A[g['i0']][1], A[g['i1']][2]
        g.update({k: v for k, v in SEG_FIX.get(g['ch'], {}).items() if g is [x for x in segs if x['ch'] == g['ch']][0 if k == 't0' else -1]})
    keep = [s for s in S if s.get('keep')]
    for s in keep:
        if s['ok']: s['t0'], s['t1'] = A[s['i0']][1], A[s['i1']][2]
        else: s['t0'] = s['t1'] = None
        del s['tok']
    # 插值：弱匹配句放在前后句之间，按词数分配
    for ch in sorted({s['ch'] for s in keep}):
        CS = [s for s in keep if s['ch'] == ch]
        k = 0
        while k < len(CS):
            if CS[k]['t0'] is not None: k += 1; continue
            j = k
            while j < len(CS) and CS[j]['t0'] is None: j += 1
            a = CS[k - 1]['t1'] if k else min(g['t0'] for g in segs if g['ch'] == ch)
            b = CS[j]['t0'] if j < len(CS) else max(g['t1'] for g in segs if g['ch'] == ch)
            n = [max(1, len(CS[x]['text'].split())) for x in range(k, j)]; tot = sum(n); acc = a
            for x, w in zip(range(k, j), n):
                CS[x]['t0'] = acc; acc += (b - a) * w / tot; CS[x]['t1'] = acc; CS[x]['interp'] = True
            k = j
    for a, b in zip(keep, keep[1:]):   # 时间单调：后一句不早于前一句结束
        if a['ch'] == b['ch'] and b['t0'] < a['t1']: b['t0'] = a['t1']
    for s in keep:   # 片段起止被人工校正后，句子时间也夹到片段内
        g = [g for g in segs if g['ch'] == s['ch']]
        s['t0'] = max(s['t0'], g[0]['t0']); s['t1'] = max(s['t1'], s['t0'] + .3)
    json.dump(dict(sentences=keep, segments=segs, dropped=[s['text'] for s in S if not s.get('keep')], interp=[s['text'] for s in keep if s.get('interp')]),
              open(out_p, 'w'), ensure_ascii=False, indent=1)
    for g in segs:
        ctx0 = ' '.join(atok[g['i0']:g['i0'] + 8]); ctx1 = ' '.join(atok[max(g['i0'], g['i1'] - 7):g['i1'] + 1])
        print(f"ch{g['ch']} {g['t0']:8.2f}-{g['t1']:8.2f} ({g['t1']-g['t0']:6.1f}s)  [{ctx0} ... {ctx1}]")
    print('total', round(sum(g['t1'] - g['t0'] for g in segs), 1), 's;', len(segs), 'segments')
    print('dropped:', [s['text'][:50] for s in S if not s.get('keep')])
    print('interpolated:', [s['text'][:40] for s in keep if s.get('interp')])

if __name__ == '__main__':
    main(*sys.argv[1:4])
