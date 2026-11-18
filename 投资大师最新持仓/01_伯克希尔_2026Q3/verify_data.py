"""从 SEC EDGAR 重新下载伯克希尔 13F 原始 XML，逐项核对 src/data.py 里的每一个数字。
用法：python3 verify_data.py   （需要能访问 www.sec.gov）"""
import os, sys, urllib.request, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
import data as D

UA = {'User-Agent': 'research-client contact@example.com'}
NS = {'n': 'http://www.sec.gov/edgar/document/thirteenf/informationtable'}
FILINGS = {'25Q3': '000119312525282901', '25Q4': '000119312526054580', '26Q1': '000119312526226661',
           '26Q2': '000119312526352200', '26Q3': '000119312526463399'}
TICK = {'AAPL': '037833', 'AXP': '025816', 'GOOGL': '02079K', 'KO': '191216', 'BAC': '060505', 'CVX': '166764',
        'OXY': '674599', 'MCO': '615369', 'CB': 'H1467J', 'KHC': '500754', 'BEND': 'T19377', 'LEN': '526057',
        'DAL': '247361', 'M': '55616P', 'COF': '14040H', 'VRSN': '92343E', 'NUE': '670346', 'KR': '501044',
        'DVA': '23918K', 'AXP': '025816'}

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA)).read()

def load(acc):
    import json
    base = f'https://www.sec.gov/Archives/edgar/data/1067983/{acc}/'
    items = json.loads(get(base + 'index.json'))['directory']['item']
    name = [x['name'] for x in items if x['name'].endswith('.xml') and x['name'] != 'primary_doc.xml'][0]
    d = {}
    for it in ET.fromstring(get(base + name)).findall('n:infoTable', NS):
        c = it.find('n:cusip', NS).text[:6]
        e = d.setdefault(c, [0, 0])
        e[0] += int(it.find('n:shrsOrPrnAmt/n:sshPrnamt', NS).text); e[1] += int(it.find('n:value', NS).text)
    return d

Q = {k: load(v) for k, v in FILINGS.items()}
cur, prev = Q['26Q3'], Q['26Q2']
ok = True
def check(label, a, b):
    global ok
    good = a == b
    ok &= good
    print(('OK  ' if good else 'FAIL'), label, a, b)

check('total', sum(v[1] for v in cur.values()), D.TOTAL)
check('total prev', sum(v[1] for v in prev.values()), D.TOTAL_PREV)
check('issuers', len(cur), D.N_ISSUERS)
check('issuers 25Q4', len(Q['25Q4']), D.N_ISSUERS_Q4_25)
top = sorted(cur.items(), key=lambda x: -x[1][1])[:10]
for (zh, tk, val, sh, sh0), (c, (s, v)) in zip(D.TOP, top):
    check(f'top {tk} cusip', TICK[tk], c); check(f'top {tk} value', v, val)
    check(f'top {tk} shares', s, sh); check(f'top {tk} prev shares', prev.get(c, [0])[0], sh0)
for zh, tk, sh, val in D.NEW:
    check(f'new {tk}', (TICK[tk] not in prev, cur[TICK[tk]][0], cur[TICK[tk]][1]), (True, sh, val))
for zh, tk, a, b in D.ADD + D.CUT:
    check(f'chg {tk}', (prev[TICK[tk]][0], cur[TICK[tk]][0]), (a, b))
# 所有增减都已列出
chg = {c for c in cur if c in prev and cur[c][0] != prev[c][0]}
check('all changes listed', chg, {TICK[x[1]] for x in D.ADD + D.CUT})
check('new list', {c for c in cur if c not in prev}, {TICK[x[1]] for x in D.NEW})
check('sold list', {c for c in prev if c not in cur}, set())
for tk, h in D.HIST.items():
    check(f'hist {tk}', [Q[q].get(TICK[tk], [0])[0] for q in D.QUARTERS], h)
check('aapl prev value', prev['037833'][1], D.AAPL_PREV_VALUE)
check('all 27', {c: v[1] for c, v in cur.items()}, {c: val for c, tk, val in D.ALL})
qs = list(FILINGS)
for q, n in D.EXITS:
    i = qs.index(q)
    check(f'exits {q}', len(set(Q[qs[i - 1]]) - set(Q[q])), n)
print('ALL OK' if ok else 'SOME CHECKS FAILED')
sys.exit(0 if ok else 1)
