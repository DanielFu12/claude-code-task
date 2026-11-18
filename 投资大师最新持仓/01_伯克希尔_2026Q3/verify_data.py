"""核对 src/data.py：
  1) 参考网页 masterstao.com/zh/masters/4 公开的每个数字（总市值、只数、前十大名称/代码/权重/股数变化）
  2) 其余所有数字：从 SEC EDGAR 重新下载伯克希尔 13F 原始 XML 逐只复核（与网页同口径：每个证券类别单独算）
用法：python3 verify_data.py   （需要能访问 masterstao.com 与 www.sec.gov）"""
import os, re, sys, json, html, urllib.request, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
import data as D

UA = {'User-Agent': 'Mozilla/5.0 (research-client contact@example.com)'}
NS = {'n': 'http://www.sec.gov/edgar/document/thirteenf/informationtable'}
FILINGS = {'25Q3': '000119312525282901', '25Q4': '000119312526054580', '26Q1': '000119312526226661',
           '26Q2': '000119312526352200', '26Q3': '000119312526463399'}
CUSIP = {tk: c for c, tk, v in D.ALL}

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA)).read()

ok = True
def check(label, a, b):
    global ok
    good = a == b
    ok &= good
    print(('OK  ' if good else 'FAIL'), label, a if good else f'{a!r} != {b!r}')

# ---------------------------------------------------------------- 1) 参考网页
page = html.unescape(get('https://masterstao.com/zh/masters/4').decode())
m = re.search(r'最新披露：(\S+) · (\d+) 只 · ([\d,]+) 美元', page)
check('网页 报告期', m.group(1), D.FILING['quarter'])
check('网页 只数', int(m.group(2)), D.N_POS)
check('网页 总市值', int(m.group(3).replace(',', '')), D.TOTAL)
rows = re.findall(r'<tr[^>]*>(.*?)</tr>', page, re.S)
web = []
for r in rows:
    cells = [re.sub(r'<[^>]+>', '', c).strip() for c in re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)]
    cells = [c for c in cells if c]
    if len(cells) >= 4 and '%' in cells[1]:
        nm, tk = re.match(r'(.+?) \((\w+)\)', cells[0]).groups()
        web.append((nm, tk, float(cells[1].rstrip('%')), int(cells[2].replace(',', ''))))
check('网页 前十大行数', len(web), 10)
for (nm, tk, w, d), row in zip(web, D.TOP):
    check(f'网页 {tk}', (nm, tk, w, d), (row[0], row[1], row[2], row[5]))

# ---------------------------------------------------------------- 2) SEC 原文
def load(acc):
    base = f'https://www.sec.gov/Archives/edgar/data/1067983/{acc}/'
    items = json.loads(get(base + 'index.json'))['directory']['item']
    name = [x['name'] for x in items if x['name'].endswith('.xml') and x['name'] != 'primary_doc.xml'][0]
    d = {}
    for it in ET.fromstring(get(base + name)).findall('n:infoTable', NS):
        c = it.find('n:cusip', NS).text
        e = d.setdefault(c, [0, 0])
        e[0] += int(it.find('n:shrsOrPrnAmt/n:sshPrnamt', NS).text); e[1] += int(it.find('n:value', NS).text)
    return d

Q = {k: load(v) for k, v in FILINGS.items()}
cur, prev = Q['26Q3'], Q['26Q2']
check('SEC 总市值', sum(v[1] for v in cur.values()), D.TOTAL)
check('SEC 上期总市值', sum(v[1] for v in prev.values()), D.TOTAL_PREV)
check('SEC 只数', len(cur), D.N_POS)
check('SEC 全部 30 只市值', {c: v[1] for c, v in cur.items()}, {c: v for c, tk, v in D.ALL})
for zh, tk, w, val, sh, dsh in D.TOP:
    c = CUSIP[tk]
    check(f'SEC {tk}', (val, sh, sh - prev[c][0], round(val / D.TOTAL * 100, 2)), (cur[c][1], cur[c][0], dsh, w))
check('SEC 苹果上期市值', prev[CUSIP['AAPL']][1], D.AAPL_PREV_VALUE)
for zh, tk, sh, val in D.NEW:
    c = CUSIP[tk]; check(f'SEC 新进 {tk}', (c not in prev, cur[c][0], cur[c][1]), (True, sh, val))
for zh, tk, a, b in D.ADD + D.CUT:
    c = CUSIP[tk]; check(f'SEC 增减 {tk}', (prev[c][0], cur[c][0]), (a, b))
check('SEC 增减持清单完整', {c for c in cur if c in prev and cur[c][0] != prev[c][0]},
      {CUSIP[x[1]] for x in D.ADD + D.CUT})
check('SEC 新进清单完整', {c for c in cur if c not in prev}, {CUSIP[x[1]] for x in D.NEW})
check('SEC 清仓', [c for c in prev if c not in cur], D.SOLD)
check('SEC 不变只数', sum(1 for c in cur if c in prev and cur[c][0] == prev[c][0]), D.N_UNCHANGED)
for tk, h in D.HIST.items():
    check(f'SEC 历史 {tk}', [Q[q].get(CUSIP[tk], [0])[0] for q in D.QUARTERS], h)
qs = list(FILINGS)
for q, n in D.EXITS:
    i = qs.index(q)
    check(f'SEC 清仓只数 {q}', len(set(Q[qs[i - 1]]) - set(Q[q])), n)
print('ALL OK' if ok else 'SOME CHECKS FAILED')
sys.exit(0 if ok else 1)
