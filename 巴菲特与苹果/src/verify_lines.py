"""逐句严格核对：每句做两次独立转写（数字要求写成汉字），与朗读文本逐字比较（不做读音折算），
数字、年份、金额读错或含糊的句子会被列出。python3 src/verify_lines.py WORK [id ...] | --file F TEXT
"""
import sys, os, re, json, base64, difflib, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tts_gen import post
from script import LINES, TEASE

PROMPT = '逐字转写这段中文音频。所有数字一律用汉字逐字写出（例如：二零二六年、五万亿、百分之二十九、两点二八亿、三点八九亿），英文照写；开头或结尾如果有与正文无关的字词也要如实写出。只输出转写文本。'
SAY = {l[0]: (l[3] or l[2]) for l in LINES}; SAY['tease'] = TEASE[1]


def clean(s): return re.sub(r'[\s，。、：；！？“”"\'—…·,.:;!?()（）《》-]', '', s).replace('两', '二')


MODEL = 'gemini-3.8-flash'
RUNS = 4


def tr(path):
    b = {'contents': [{'parts': [{'inlineData': {'mimeType': 'audio/wav', 'data': base64.b64encode(open(path, 'rb').read()).decode()}}, {'text': PROMPT}]}]}
    d = post(MODEL, b, timeout=300)
    return ''.join(p.get('text', '') for p in d['candidates'][0]['content']['parts']).strip()


def check(path, ref):
    outs = [tr(path) for _ in range(RUNS)]
    a = clean(ref); cnt = {}
    for o in outs:
        b = clean(o)
        for op in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if op[0] != 'equal':
                k = f'{op[0]}「{a[op[1]:op[2]]}」→「{b[op[3]:op[4]]}」'; cnt[k] = cnt.get(k, 0) + 1
    issues = [f'{k}×{n}' for k, n in cnt.items() if n * 2 > RUNS]      # 多数转写都听到的问题才算
    return outs, issues


if __name__ == '__main__':
    work = sys.argv[1]
    if sys.argv[2:3] == ['--file']:
        outs, iss = check(sys.argv[3], sys.argv[4]); print(iss); print(outs); sys.exit()
    ids = sys.argv[2:] or list(SAY)
    res = {}
    with cf.ThreadPoolExecutor(6) as ex:
        futs = {ex.submit(check, os.path.join(work, 'vo', f'{i}.wav'), SAY[i]): i for i in ids}
        for f in cf.as_completed(futs):
            i = futs[f]; outs, iss = f.result(); res[i] = dict(issues=iss, tr=outs)
            if iss: print(i, ' | '.join(sorted(set(iss))), flush=True)
            json.dump(res, open(os.path.join(work, 'vo', 'verify.json'), 'w'), ensure_ascii=False, indent=1)
    json.dump(res, open(os.path.join(work, 'vo', 'verify.json'), 'w'), ensure_ascii=False, indent=1)
    print('done', sum(1 for v in res.values() if v['issues']), '/', len(res), 'flagged')
