"""合并对齐结果与双语字幕，生成按原片时间计时的字幕条。
用法: python3 build_cues.py <align.json> <cues.txt> <out.json>
每句里的多条字幕按逐词时间码切分；没有词级时间的部分按词数插值。
"""
import json, re, sys
from align import tokens

FILL = 8.0

def parse(path):
    out, ch, spk, e = [], None, 'L', None
    for line in open(path, encoding='utf8'):
        line = line.rstrip('\n')
        if not line or line.startswith('# '): continue
        if line.startswith('## '): ch = int(line[3:]); spk = 'L'; continue
        if line in ('@Q', '@L'): spk = line[1]; continue
        if line.startswith('E: '): e = [x.strip() for x in line[3:].split('||')]; continue
        if line.startswith('Z: '):
            z = [x.strip() for x in line[3:].split('||')]
            assert len(z) == len(e), (e, z)
            out.append(dict(ch=ch, spk=spk, en=e, zh=z)); e = None; continue
        if line.startswith('N: '): out[-1]['note'] = line[3:].strip()      # 该句注释
    return out

def main(align_p, cues_p, out_p):
    A = json.load(open(align_p))
    S, C = A['sentences'], parse(cues_p)
    assert len(S) == len(C), (len(S), len(C))
    res = []
    for s, c in zip(S, C):
        assert ' '.join(c['en']) == s['text'] and s['ch'] == c['ch'], (s['text'], c['en'])
        wt = s.get('wt') or []
        wt = [t if t is not None and s['t0'] - .05 <= t <= s['t1'] else None for t in wt]
        n = [len(tokens(x)) for x in c['en']]
        bounds = [s['t0']]
        acc = 0
        for k in range(1, len(n)):
            acc += n[k - 1]
            t = next((wt[j] for j in range(acc, min(acc + 3, len(wt))) if wt and wt[j] is not None), None)
            if t is None or not (bounds[-1] < t < s['t1']):
                t = s['t0'] + (s['t1'] - s['t0']) * acc / max(1, sum(n))
            bounds.append(t)
        bounds.append(s['t1'])
        for k in range(len(n)):
            en = re.sub(r'\s*\[[^\]]*\]', '', c['en'][k]).strip()   # 编者补注不显示
            res.append(dict(ch=c['ch'], spk=c['spk'], t0=round(bounds[k], 3), t1=round(bounds[k + 1], 3), en=en, zh=c['zh'][k],
                            send=k == len(n) - 1,           # send：整句的最后一条（用于找句子结束点）
                            note=c.get('note') if k == len(n) - 1 else None))
    # 相邻字幕首尾相接：同章内小于 FILL 秒的空隙（停顿、口头语）由前一条延长补齐，避免字幕空白
    for a, b in zip(res, res[1:]):
        if a['ch'] == b['ch'] and 0 < b['t0'] - a['t1'] < FILL: a['t1'] = b['t0']
    # 最短显示时长：太短的字幕向后借时间（下一条足够长时把它的开头往后推）
    for k, a in enumerate(res):
        need = min(2.2, 0.7 + 0.075 * len(a['zh']))
        if a['t1'] - a['t0'] >= need: continue
        b = res[k + 1] if k + 1 < len(res) and res[k + 1]['ch'] == a['ch'] else None
        if b is None: a['t1'] = a['t0'] + need; continue
        give = max(0.0, min(need - (a['t1'] - a['t0']), (b['t1'] - b['t0']) - min(2.2, 0.7 + 0.075 * len(b['zh']))))
        a['t1'] += give; b['t0'] = a['t1']
    json.dump(res, open(out_p, 'w'), ensure_ascii=False, indent=0)
    print(len(res), 'cues; max zh', max(len(r['zh']) for r in res), 'max en words', max(len(r['en'].split()) for r in res))

if __name__ == '__main__':
    main(*sys.argv[1:4])
