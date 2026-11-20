"""从 脚本.md 解析旁白 -> src/script.py
- 去掉〔〕里的修改说明
- 第 63 句拆成三句（三记锤击各占一小节）
- 配音文本：数字转口语读法；字幕文本：保留阿拉伯数字，按标点自动分屏（每屏 ≤18 字）"""
import re, os
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, '..', '脚本.md')).read()
rows = re.findall(r'^\| (\d+) \| (.+?) \| ', src, re.M)
rows = [(int(k), re.sub(r'〔.*?〕', '', v).strip()) for k, v in rows]

DIG = '零一二三四五六七八九'
def zh(n):
    if n == 0: return '零'
    th, hu, te, on = n // 1000, n // 100 % 10, n // 10 % 10, n % 10
    s = ''
    if th: s += ('两' if th == 2 else DIG[th]) + '千'
    if hu: s += ('两' if hu == 2 and not th else DIG[hu]) + '百'
    elif th and (te or on): s += '零'
    if te: s += ('' if (te == 1 and not th and not hu) else DIG[te]) + '十'
    elif (th or hu) and on: s += '零'
    if on: s += DIG[on]
    return s

def speak(t):
    t = re.sub(r'(\d{4})\s*年', lambda m: ''.join(DIG[int(c)] for c in m.group(1)) + '年', t)
    def num(m):
        n = int(m.group(1)); nxt = m.group(2) or ''
        s = zh(n)
        if not nxt:                       # 口语：后面没有单位时，一千五百 → 一千五，一百八十 → 一百八
            s = re.sub(r'^(.+千)(.)百$', r'\1\2', s)
            s = re.sub(r'^(.+百)(.)十$', r'\1\2', s)
        return s + nxt
    t = re.sub(r'(\d+)\s*(多|港元|美元|元|倍|年)?', num, t)
    t = t.replace('「', '').replace('」', '').replace('“', '').replace('”', '')
    return re.sub(r'\s+', '', t)

def subs(t, lim=18):
    t = t.replace('「', '“').replace('」', '”')
    parts = re.findall(r'[^，。？！；：、]+[，。？！；：、]?', t)
    out, cur = [], ''
    L = lambda s: len(re.sub(r'[^一-鿿0-9A-Za-z]', '', s))
    for p in parts:
        if cur and (L(cur + p) > lim or cur.rstrip().endswith(('。', '？', '！'))): out.append(cur); cur = p
        else: cur += p
    if cur: out.append(cur)
    clean = lambda s: re.sub(r'[，。；：、]$', '', s.strip())
    return '|'.join(clean(s) for s in out if clean(s))

lines = []
for k, v in rows:
    if k == 63:
        for j, sent in enumerate(re.findall(r'[^。]+。', v)):
            lines.append((f'L63{"abc"[j]}', sent))
    else:
        lines.append((f'L{k:02d}', v))
with open(os.path.join(HERE, 'script.py'), 'w') as f:
    f.write('"""旁白（由 gen_script.py 从 脚本.md 生成，勿手改）：(id, 配音文本, 字幕文本, 语气提示, 句后停顿秒)"""\n')
    f.write("TONE = '你是一位经历过牛熊、亏过也赚过的老投资人，在深夜跟一位刚被套牢的朋友掏心窝子聊天：情绪真实饱满，讲到亏损时有惋惜，讲到转折时语气一顿再加重，讲到结论时笃定有力；口语化，有呼吸感，不播音腔，语速偏快、干脆利落，全程同一个人、同一种状态'\n\n")
    f.write('LINES = [\n')
    for i, v in lines:
        gap = 0.35 if v.endswith(('。', '？', '！', '…')) else 0.2
        f.write(f' ({i!r}, {speak(v)!r}, {subs(v)!r}, TONE, {gap}),\n')
    f.write(']\n')
print(len(lines), 'lines')
