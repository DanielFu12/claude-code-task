"""把脚本里的阿拉伯数字、百分号、英文缩写转成大致读音（只用于核对识别结果，不影响配音）"""
import re
DIG = '零一二三四五六七八九'


def int_cn(n):
    if n == 0: return '零'
    out, zero = '', False
    for u, name in ((100000000, '亿'), (10000, '万'), (1000, '千'), (100, '百'), (10, '十')):
        q = n // u
        if q:
            if zero and out: out += '零'
            out += (int_cn(q) if q >= 10 else DIG[q]) + name; n %= u; zero = False
        elif out: zero = True
    if n:
        if zero and out: out += '零'
        out += DIG[n]
    return out[1:] if out.startswith('一十') else out


def to_reading(s):
    def rep(m):
        tok = m.group(0).replace(',', ''); nxt = s[m.end():m.end() + 2].strip()
        pct = tok.endswith('%'); tok = tok.rstrip('%')
        if re.fullmatch(r'\d{4}', tok) and nxt.startswith('年'): r = ''.join(DIG[int(c)] for c in tok)
        elif '.' in tok: a, b = tok.split('.'); r = int_cn(int(a)) + '点' + ''.join(DIG[int(c)] for c in b)
        else: r = int_cn(int(tok))
        return ('百分之' + r) if pct else r
    return re.sub(r'\d[\d,]*(\.\d+)?%?', rep, s)
