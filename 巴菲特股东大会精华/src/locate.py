"""在整场股东大会的转写稿里自动定位每段金句的时间码。

    python3 src/locate.py        # -> work/located.json，work/subs/<id>.en.srt（整段英文转写，便于补全翻译）

每句英文先按词归一化，再在转写稿里做模糊匹配（difflib）。一段里最有辨识度的那句先全局定位，
其余句子只在它前后 5 分钟内找；片段起止点再加 pre/post 秒并吸附到最近的停顿。
"""
import bisect, difflib, json, os, sys
from collections import defaultdict
from common import load_json, wpath, norm_tokens, load_transcript, parse_tc, fmt_tc
from fetch import resolve, transcript_for

STOP = set('the a an and or of to in is it i you that this we for on be with as are was at but so if they he she not '
           'have has had do would could there what just its it\'s i\'m don\'t that\'s'.split())
MIN_SCORE = 0.55


def match_line(tokens, words, lo=0, hi=None):
    """返回 [(score, i0, i1)]：转写稿 words[i0:i1] 与 tokens 的最佳匹配候选（按分数降序）。"""
    hi = len(words) if hi is None else hi
    n = len(tokens)
    content = [t for t in tokens if t not in STOP] or tokens
    idx = defaultdict(list)
    for i in range(lo, hi):
        idx[words[i][0]].append(i)
    starts = set()
    for t in set(content):
        for p in idx.get(t, ()):
            starts.update(range(max(lo, p - n), min(hi, p + 1)))
    sm = difflib.SequenceMatcher(autojunk=False)
    sm.set_seq2(tokens)
    res = []
    span = n + max(3, n // 4)
    for s in sorted(starts):
        win = [w[0] for w in words[s:min(hi, s + span)]]
        sm.set_seq1(win)
        blocks = [b for b in sm.get_matching_blocks() if b.size]
        if not blocks:
            continue
        hit = sum(b.size for b in blocks)
        a0, a1 = blocks[0].a, blocks[-1].a + blocks[-1].size
        score = 2 * hit / (n + (a1 - a0))          # 覆盖率 × 紧凑度
        res.append((score, s + a0, s + a1))
    res.sort(key=lambda r: (-r[0], r[1]))
    out = []                                       # 去掉相互重叠的候选
    for r in res:
        if all(r[2] <= o[1] or r[1] >= o[2] for o in out):
            out.append(r)
    return out


def snap(words, t, direction, reach=2.5):
    """在 t 附近找最长的说话停顿，把切点放在停顿中间。"""
    ts = [w[1] for w in words]
    i = bisect.bisect_left(ts, t - reach)
    best, bt = 0.25, t
    for k in range(max(1, i), len(words)):
        if words[k][1] > t + reach:
            break
        gap = words[k][1] - words[k - 1][2]
        mid = (words[k][1] + words[k - 1][2]) / 2
        if (direction < 0 and mid > t + 0.6) or (direction > 0 and mid < t - 0.6):
            continue
        if gap > best:
            best, bt = gap, mid
    return bt


def locate_clip(clip, parts_words):
    lines = clip['lines']
    toks = [norm_tokens(l['en']) for l in lines]
    occ = clip.get('pick', 0)
    # 1) 先全局定位最有辨识度的那句（最长的句子），在所有分段里找
    order = sorted(range(len(lines)), key=lambda i: -len(toks[i]))
    anchor = order[0]
    cands = []
    for pk, words in enumerate(parts_words):
        for sc, i0, i1 in match_line(toks[anchor], words)[:30]:
            cands.append((sc, pk, i0, i1))
    if not cands:
        return None, f'找不到锚句: {lines[anchor]["en"]}'
    best = max(c[0] for c in cands)
    good = sorted([c for c in cands if c[0] >= best - 0.08 and c[0] >= MIN_SCORE], key=lambda c: (c[1], c[2]))
    if not good:
        return None, f'锚句匹配度太低 ({best:.2f}): {lines[anchor]["en"]}'
    sc, pk, i0, i1 = good[min(occ, len(good) - 1)]
    words = parts_words[pk]
    t_anchor = words[i0][1]
    lo = bisect.bisect_left([w[1] for w in words], t_anchor - 300)
    hi = bisect.bisect_right([w[1] for w in words], t_anchor + 300)
    found = {anchor: (sc, i0, i1)}
    # 2) 其余句子在锚点 ±5 分钟内找，取离锚点最近的高分候选
    for i in order[1:]:
        cs = [c for c in match_line(toks[i], words, lo, hi) if c[0] >= MIN_SCORE]
        if len(toks[i]) <= 3:                      # 很短的句子（如 "Charlie?"）只认锚点同侧 20 秒内的
            side = 1 if i > anchor else -1
            cs = [c for c in cs if 0 <= (words[c[1]][1] - t_anchor) * side < 20]
        if cs:
            top = cs[0][0]
            found[i] = min([c for c in cs if c[0] >= top - 0.1], key=lambda c: abs(words[c[1]][1] - t_anchor))
    res = []
    for i, l in enumerate(lines):
        if i in found:
            sc, a, b = found[i]
            res.append({'t0': words[a][1], 't1': words[b - 1][2], 'score': round(sc, 3)})
        else:
            res.append(None)
            print(f'  ! [{clip["id"]}] 未定位: {l["en"]}')
    got = [r for r in res if r]
    t0 = min(r['t0'] for r in got) - clip.get('pre', 2)
    t1 = max(r['t1'] for r in got) + clip.get('post', 2)
    if clip.get('start') is not None:
        t0 = parse_tc(clip['start'])
    else:
        t0 = snap(words, t0, -1, clip.get('snap', 2.5))
    if clip.get('end') is not None:
        t1 = parse_tc(clip['end'])
    else:
        t1 = snap(words, t1, +1, clip.get('snap', 2.5))
    fill = [[w[0], round(w[1] - t0, 3), round(w[2] - t0, 3)] for w in words if t0 <= w[1] < t1]
    return {'source': clip['source'], 'part': pk, 'start': round(t0, 3), 'end': round(t1, 3),
            'lines': [None if r is None else {'t0': round(r['t0'] - t0, 3), 't1': round(r['t1'] - t0, 3), 'score': r['score']}
                      for r in res],
            'words': fill}, None


def write_srt(path, words):
    """把片段内的英文转写按停顿切成句，写成 SRT（相对片段起点），方便后续补全中文翻译。"""
    cues, cur = [], []
    for w in words:
        if cur and (w[1] - cur[-1][2] > 0.6 or len(cur) >= 14):
            cues.append(cur); cur = []
        cur.append(w)
    if cur:
        cues.append(cur)
    with open(path, 'w', encoding='utf-8') as f:
        for k, c in enumerate(cues, 1):
            f.write(f'{k}\n{fmt_tc(c[0][1], True).replace(".", ",")} --> {fmt_tc(c[-1][2], True).replace(".", ",")}\n'
                    f'{" ".join(x[0] for x in c)}\n\n')


def fit(cfg, loc, cache):
    """总长不到 target_seconds 时，把差额平均分给各段，往前（多留提问/上下文）和往后延长，并吸附到停顿。"""
    from render import CARD                       # 片名 / 章节卡 / 片尾的时长与渲染保持一致
    chapters = {c['chapter'] for c in cfg['clips'] if c['id'] in loc}
    fixed = CARD['title'] + CARD['end'] + CARD['chapter'] * len(chapters)
    total = fixed + sum(s['end'] - s['start'] for s in loc.values())
    short = cfg.get('target_seconds', 600) - total
    clips = [c for c in cfg['clips'] if c['id'] in loc and c.get('start') is None and c.get('end') is None]
    if short < 5 or not clips:
        return
    each = min(short / len(clips), 25.0)
    for c in clips:
        seg = loc[c['id']]
        words = cache[c['source']][seg['part']]
        old0 = seg['start']
        t0 = snap(words, max(0.0, seg['start'] - each * 0.6), -1, 1.0)
        t1 = snap(words, seg['end'] + each * 0.4, +1, 1.0)
        shift = old0 - t0
        seg['start'], seg['end'] = round(t0, 3), round(t1, 3)
        seg['lines'] = [None if l is None else dict(l, t0=round(l['t0'] + shift, 3), t1=round(l['t1'] + shift, 3))
                        for l in seg['lines']]
        seg['words'] = [[w[0], round(w[1] - t0, 3), round(w[2] - t0, 3)] for w in words if t0 <= w[1] < t1]
        write_srt(wpath('subs', f'{c["id"]}.en.srt'), seg['words'])
    total = fixed + sum(s['end'] - s['start'] for s in loc.values())
    print(f'自动补足时长：每段约 +{each:.1f}s（往前 60%、往后 40%），预计成片 {fmt_tc(total)}')


def main(only=None):
    cfg, srcs = load_json('clips.json'), load_json('sources.json')
    cache, out, errs = {}, {}, []
    for clip in [dict(c, snap=c.get('snap', 0.5)) for c in cfg['coldopen']] + cfg['clips']:
        if only and clip['id'] not in only:
            continue
        y = clip['source']
        if y not in cache:
            pw = []
            for k, p in enumerate(resolve(y, srcs[y])):
                tp = transcript_for(y, k, p)
                pw.append(load_transcript(tp) if tp else [])
                if not tp:
                    print(f'[{y}] 分段 {k} 缺转写稿（先运行 fetch.py subs / whisper）')
            cache[y] = pw
        seg, err = locate_clip(clip, cache[y])
        if err:
            errs.append(f'[{clip["id"]} {y}] {err}')
            continue
        out[clip['id']] = seg
        write_srt(wpath('subs', f'{clip["id"]}.en.srt'), seg['words'])
        sc = [l['score'] for l in seg['lines'] if l]
        print(f'[{clip["id"]} {y}] {fmt_tc(seg["start"])}–{fmt_tc(seg["end"])}  时长 {seg["end"] - seg["start"]:5.1f}s'
              f'  匹配 {len(sc)}/{len(seg["lines"])} 句, 最低分 {min(sc):.2f}')
    prev = json.load(open(wpath('located.json'))) if only and os.path.exists(wpath('located.json')) else {}
    prev.update(out)
    if not only and cfg.get('auto_fit', True):
        fit(cfg, prev, cache)
    json.dump(prev, open(wpath('located.json'), 'w'), ensure_ascii=False)
    total = sum(s['end'] - s['start'] for s in prev.values())
    print(f'\n共 {len(prev)} 段，素材总时长 {total / 60:.1f} 分钟 -> {wpath("located.json")}')
    if errs:
        print('\n以下片段需要人工处理（在 clips.json 里填 start/end，或修改 lines 的英文原句）：')
        print('\n'.join(errs))
        sys.exit(1)


if __name__ == '__main__':
    main(set(sys.argv[1:]) or None)
