"""强制对齐：整段旁白音频 + 已知文本 → 每个字（音节）的起止时间。
用 torchaudio 的 MMS_FA（多语种 wav2vec2 CTC 对齐模型），中文先转无声调拼音。
数字按实际读法展开（年份逐位读、百分数、小数、整数），并记录“原文字符 → 音节”的映射，
这样既能按句子切分，也能查到“376”“8.48”这类关键词的精确发声时刻。
"""
import re, json, os
import numpy as np

DIG = '零一二三四五六七八九'


def int_cn(n):
    if n == 0: return '零'
    units = [(100000000, '亿'), (10000, '万'), (1000, '千'), (100, '百'), (10, '十')]
    out, zero = '', False
    for u, name in units:
        q = n // u
        if q:
            if zero and out: out += '零'
            out += (int_cn(q) if q >= 10 else DIG[q]) + name; n %= u; zero = False
        elif out: zero = True
    if n:
        if zero and out: out += '零'
        out += DIG[n]
    if out.startswith('一十'): out = out[1:]
    return out


def num_cn(tok, nxt):
    """数字串 → 汉字读法"""
    if re.fullmatch(r'\d{4}', tok) and nxt == '年': return ''.join(DIG[int(c)] for c in tok)
    if '.' in tok:
        a, b = tok.split('.'); return int_cn(int(a)) + '点' + ''.join(DIG[int(c)] for c in b)
    return int_cn(int(tok))


def normalize(text):
    """返回 (读音汉字列表, 每个读音单元对应的原文字符下标)"""
    units, src = [], []
    i = 0
    while i < len(text):
        m = re.match(r'\d+(\.\d+)?', text[i:])
        if m:
            tok = m.group(0); j = i + len(tok)
            pct = j < len(text) and text[j] == '%'
            s = ('百分之' if pct else '') + num_cn(tok, text[j] if j < len(text) else '')
            for c in s: units.append(c); src.append(i)
            i = j + (1 if pct else 0); continue
        c = text[i]
        if '一' <= c <= '鿿': units.append(c); src.append(i)
        elif c.isascii() and c.isalpha():                     # 英文单词整体作为一个单元
            m = re.match(r'[A-Za-z]+', text[i:]); units.append(m.group(0).lower()); src.append(i); i += len(m.group(0)); continue
        i += 1
    return units, src


_M = {}
def model():
    if 'm' not in _M:
        import torch, torchaudio
        from torchaudio.pipelines import MMS_FA as B
        _M['m'] = (B.get_model(with_star=False), B.get_tokenizer(), B.get_aligner(), B.sample_rate, torch, torchaudio)
    return _M['m']


def romanize(units):
    from pypinyin import lazy_pinyin, Style
    out = []
    for u in units:
        if u.isascii(): out.append(re.sub('[^a-z]', '', u) or 'a'); continue
        p = lazy_pinyin(u, style=Style.NORMAL, v_to_u=False)[0].replace('v', 'u')
        out.append(re.sub('[^a-z]', '', p) or 'a')
    return out


def align(wav, text):
    """wav: 文件路径；text: 朗读文本。返回 [{'u': 单元, 'i': 原文下标, 's': 起, 'e': 止, 'score'}]"""
    m, tok, aligner, sr, torch, ta = model()
    y, r = ta.load(wav)
    y = y.mean(0, keepdim=True)
    if r != sr: y = ta.functional.resample(y, r, sr)
    units, src = normalize(text)
    words = romanize(units)
    with torch.inference_mode():
        em, _ = m(y)
    spans = aligner(em[0], tok(words))
    ratio = y.shape[1] / em.shape[1] / sr
    out = []
    for u, i, sp in zip(units, src, spans):
        out.append(dict(u=u, i=i, s=round(sp[0].start * ratio, 3), e=round(sp[-1].end * ratio, 3),
                        score=round(float(np.mean([x.score for x in sp])), 3)))
    return out


if __name__ == '__main__':
    import sys
    r = align(sys.argv[1], sys.argv[2])
    for x in r: print(x)
