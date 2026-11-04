"""针对性听辨：对可疑处做“二选一”判断（选项顺序随机，问 3 次取多数）。
python3 src/ab_check.py WORK          # 用下面 CHECKS 清单，结果写 work/vo/ab.json
"""
import sys, os, json, base64, random, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tts_gen import post

CHECKS = [   # (句子, 正确说法, 可疑说法)
    ('h1', '二零二六年秋天', '二零二零年秋天'), ('h1', '五万亿', '两万亿'),
    ('c1q', '苹果的生意模式', '苹果的商业模式'), ('c2c', '最好的生意', '最好的声音'),
    ('c2h', '二零二五财年', '二零二四财年'), ('c2k', '二零二六财年', '二零二四财年'),
    ('c3c', '一百一十亿', '一百一十一亿'), ('c3i', '一千三百九十亿', '一千三百九十一亿'),
    ('c3f', '二零二六年起', '二零二六年代'), ('c4h', '三百三十八美元', '两百三十八美元'),
    ('c5d', '二零二六年中', '二零二四年中'), ('c5d', '二零二六年中', '二零二六年底'),
    ('c5e', '二零二五年的股东大会', '二零二一年的股东大会'), ('c3g', '算一算总账', '算算总账'),
]


def ask(path, x, y):
    opts = [x, y]; random.shuffle(opts)
    b = {'contents': [{'parts': [{'inlineData': {'mimeType': 'audio/wav', 'data': base64.b64encode(open(path, 'rb').read()).decode()}},
                                 {'text': f'仔细听这段中文音频。说话人实际说出的是下面哪一个？\nA. {opts[0]}\nB. {opts[1]}\n如果听不清或两者都不像，回答 C。只回答一个字母。'}]}]}
    d = post('gemini-3.8-flash', b, timeout=300)
    r = ''.join(p.get('text', '') for p in d['candidates'][0]['content']['parts']).strip().upper()[:1]
    return {'A': opts[0], 'B': opts[1]}.get(r, '听不清')


def run(work, items, vdir='vo'):
    res = {}
    def one(it):
        i, x, y = it[:3]; path = it[3] if len(it) > 3 else os.path.join(work, vdir, f'{i}.wav')
        votes = [ask(path, x, y) for _ in range(3)]
        return it, votes
    with cf.ThreadPoolExecutor(6) as ex:
        for it, votes in ex.map(one, items):
            ok = votes.count(it[1]) >= 2
            res[f'{it[0]}:{it[1]}|{it[2]}' + (f'@{os.path.basename(os.path.dirname(it[3]))}' if len(it) > 3 else '')] = dict(votes=votes, ok=ok)
            print('OK ' if ok else 'BAD', it[0], it[1], 'vs', it[2], votes, flush=True)
    return res


if __name__ == '__main__':
    work = sys.argv[1]
    res = run(work, CHECKS)
    json.dump(res, open(os.path.join(work, 'vo', 'ab.json'), 'w'), ensure_ascii=False, indent=1)
