"""为每个段落挑选最好的整段录音：
  1) 用 Gemini 转写回听，和文本逐字比对（读错/漏读/多读的录音直接淘汰，同音字和数字写法不算错）；
  2) 剩下的候选随机顺序盲听打分（多轮取平均），选“最像真人讲述者、句间最连贯”的一条。
结果写入 work/tts_p/select.json（并打印每段得分）。

python3 src/select_takes.py WORK [pid ...]
"""
import sys, os, json, re, glob, base64, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tts_gen import post, transcribe
from tts_passage import PASSAGES, TEASE_P, spoken
from align import normalize

PROMPT = """以上 {n} 段音频是同一段中文纪录片旁白的不同录音（文字相同，顺序随机）。请作为严格的资深纪录片配音导演盲听：
只评价“像不像真人讲述者在自然地讲故事”：句与句之间是否连贯（还是每句重新起调、句尾一律同样下沉）、停顿和换气是否像真人、
语速与重音是否随语义变化、情绪是否贴合内容、有无机械感/电子感/口齿含糊。
只输出 JSON：{{"scores": {{"A": 0-100 的整数, ...}}}}"""


def cer(ref, hyp):
    """读音层面的字错误率：都展开成汉字读音单元再比（数字写法、标点不影响）"""
    from pypinyin import lazy_pinyin
    eq = lambda p: 'er' if p == 'liang' else p                       # “两/二”在数字里可互换
    r = [eq(p) for p in lazy_pinyin(''.join(normalize(ref)[0]))]; h = [eq(p) for p in lazy_pinyin(''.join(normalize(hyp)[0]))]
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        p, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (r[i - 1] != h[j - 1]))
    return d[len(h)] / max(len(r), 1)


def blind(files, rounds=3):
    tot = {f: [] for f in files}
    for _ in range(rounds):
        order = files[:]; random.shuffle(order)
        parts = []
        for i, f in enumerate(order):
            parts += [{'text': f'音频 {chr(65 + i)}：'},
                      {'inlineData': {'mimeType': 'audio/wav', 'data': base64.b64encode(open(f, 'rb').read()).decode()}}]
        parts.append({'text': PROMPT.format(n=len(order))})
        d = post('gemini-3.8-flash', {'contents': [{'parts': parts}], 'generationConfig': {'responseMimeType': 'application/json'}}, timeout=600)
        txt = ''.join(p.get('text', '') for p in d['candidates'][0]['content']['parts'])
        j = json.loads(txt[txt.index('{'):])
        for i, f in enumerate(order): tot[f].append(j['scores'][chr(65 + i)])
    return {f: sum(v) / len(v) for f, v in tot.items()}


def select_groups(work):
    """按“大段”整读的录音挑选：先逐字校对（读音字错误率 ≤ 2%），再选音高基线、语速最接近全片目标的一条，
    保证全片像同一个讲述者、语速一致（用户要求：不可各章节播报速度差太多）"""
    import librosa, numpy as np
    from tts_passage import GROUPS
    from voice_build import articulation_rate, TARGET_RATE
    d = os.path.join(work, 'tts_p'); P = {p[0]: p for p in PASSAGES + [TEASE_P]}
    cand = {}
    for g, pids in GROUPS.items():
        ref = ''.join(spoken(i) for pp in pids for i in P[pp][1])
        for f in sorted(glob.glob(os.path.join(d, f'{g}_*.wav'))):
            if not re.fullmatch(rf'{g}_\d+\.wav', os.path.basename(f)): continue
            e = cer(ref, transcribe(f))
            if e > 0.02: print(f'  {os.path.basename(f)} 字错误率 {e:.3f}，淘汰'); continue
            y, sr = librosa.load(f, sr=16000)
            f0, _, _ = librosa.pyin(y, fmin=60, fmax=300, sr=sr, frame_length=1024, hop_length=320)
            cand.setdefault(g, []).append((os.path.basename(f), float(np.nanmedian(f0)), articulation_rate(f, ref)))
    base = float(np.median([c[1] for cs in cand.values() for c in cs]))       # 全片音高基线
    sel = {}
    for g, cs in cand.items():
        cost = lambda c: abs(12 * np.log2(c[1] / base)) / 1.0 + abs(c[2] / TARGET_RATE - 1) / 0.04
        best = min(cs, key=cost); sel[g] = best[0]
        print(g, '→', best[0], f'音高 {best[1]:.1f}Hz（基线 {base:.1f}）语速 {best[2]:.2f}', flush=True)
    json.dump(sel, open(os.path.join(d, 'select.json'), 'w'), indent=1)
    return sel


if __name__ == '__main__':
    if '--groups' in sys.argv: select_groups(sys.argv[1]); sys.exit()
    work = sys.argv[1]; want = sys.argv[2:]
    d = os.path.join(work, 'tts_p')
    selp = os.path.join(d, 'select.json')
    sel = json.load(open(selp)) if os.path.exists(selp) else {}
    log = json.load(open(os.path.join(d, 'select_log.json'))) if os.path.exists(os.path.join(d, 'select_log.json')) else {}
    for pid, ids, mood in PASSAGES + [TEASE_P]:
        if want and pid not in want: continue
        files = sorted(f for f in glob.glob(os.path.join(d, f'{pid}_*.wav')) if re.fullmatch(rf'{pid}_\d+\.wav', os.path.basename(f)))
        if not files: continue
        ref = ''.join(spoken(i) for i in ids)
        ok = []
        for f in files:
            tr = transcribe(f); e = cer(ref, tr)
            print(f'  {os.path.basename(f)} 字错误率 {e:.3f}  {tr[:40]}…', flush=True)
            if e <= 0.04: ok.append(f)
        if not ok: ok = files; print('  （全部有读错，保留全部再盲听）')
        sc = blind(ok) if len(ok) > 1 else {ok[0]: None}
        best = max(ok, key=lambda f: sc[f] or 0)
        sel[pid] = os.path.basename(best)
        log[pid] = {os.path.basename(f): sc.get(f) for f in files}
        print(pid, '→', sel[pid], {os.path.basename(k): v for k, v in sc.items()}, flush=True)
        json.dump(sel, open(selp, 'w'), indent=1); json.dump(log, open(os.path.join(d, 'select_log.json'), 'w'), indent=1)
