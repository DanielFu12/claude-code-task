"""核对 src/data.py：
  1) 参考网页 masterstao.com/zh/masters/4 渲染后的完整内容（35 只持仓的名称、代码、市值、占比、变动股份、动作、来源，
     以及资产规模、持股数量、近一年估算收益、2026Q4 动态）。默认用无头浏览器实时抓取（node fetch_page.js），
     抓不到时退回 data/ 下的快照。
  2) 网页没有展示、片中用到的精确股数与历史股数：从 SEC EDGAR 13F 原文复核。
用法：python3 verify_data.py [--offline]"""
import os, re, sys, json, glob, subprocess, urllib.request, xml.etree.ElementTree as ET
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'src'))
import data as D

ok = True
def check(label, a, b):
    global ok
    good = a == b
    ok &= good
    print(('OK  ' if good else 'FAIL'), label, a if good else f'{a!r} != {b!r}')

# ---------------------------------------------------------------- 1) 参考网页
text = None
if '--offline' not in sys.argv:
    try:
        text = subprocess.run(['node', os.path.join(HERE, 'fetch_page.js')], capture_output=True, text=True, timeout=120).stdout
        print('网页：实时抓取')
    except Exception as e:
        print('实时抓取失败：', e)
if not text or '持股数量' not in text:
    snap = sorted(glob.glob(os.path.join(HERE, 'data', 'masterstao_masters4_*.txt')))[-1]
    text = open(snap).read(); print('网页：使用快照', os.path.basename(snap))

head = {k: re.search(k + r'：(\S+)', text).group(1) for k in ['数据季度', '持股数量', '资产规模', '近一年估算收益']}
check('网页 数据季度', head['数据季度'], D.FILING['quarter'])
check('网页 持股数量', int(head['持股数量']), D.N_POS)
check('网页 资产规模', head['资产规模'], f'${D.ASSETS / 1e8:.2f}亿')
check('网页 近一年估算收益', head['近一年估算收益'], f'+{D.RET_1Y:.2f}%')
m = re.search(r'2026Q4 最新披露动态：(\d+) 项变动 —— 增持 (\d+) · 减持 (\d+)', text)
check('网页 2026Q4 动态', tuple(int(x) for x in m.groups()), D.Q4_NEWS)

seg = text[text.index('变动股份') + 4:text.index('上一页')]
L = [x.strip() for x in seg.split('\n') if x.strip()]
rows, filings, i = [], {}, 0
while i < len(L):
    name = L[i]; tk, _ = L[i + 1].split(' · ')
    val = L[i + 2].lstrip('$'); val = float(val[:-1]) if val.endswith('亿') else float(val[:-1]) / 1e4
    src = '13F' if L[i + 6] == '来源 13F' else ('JP' if '大量保有' in L[i + 6] else L[i + 6])
    j = i + 7
    if L[j].startswith('本季') and L[j].endswith('次申报'):
        nfil = int(L[j].split()[1]); j += 1
    else:
        nfil = 0
    date = L[j]; j += 1
    if nfil and j < len(L) and L[j] == '日期':          # 展开后的申报明细：日期 / 来源 / 持股 / 变动
        j += 4; fl = []
        for _ in range(nfil):
            fl.append((L[j], L[j + 1], L[j + 2].replace('股', '', 1) if L[j + 2].endswith('股') else L[j + 2], L[j + 3])); j += 4
        filings[tk] = fl
    rows.append((name, tk, round(val, 4), float(L[i + 3].rstrip('%')), L[i + 4], L[i + 5], src, date))
    i = j
check('网页 行数', len(rows), len(D.H))
for r, h in zip(rows, D.H):
    check(f'网页 {h[1]}', r[:7], h)
    if h[6] == 'JP':
        check(f'网页 {h[1]} 申报日', r[7], '申报 ' + D.JP_DATES[h[1]])
for zh, tk, s0, s1, web in D.ADD + D.CUT:
    r = [x for x in rows if x[1] == tk][0]
    check(f'网页 变动 {tk}', r[4], web)
    d = s1 - s0
    shown = (('+' if d > 0 else '-') + f'{round(abs(d) / 1e4)}万')
    check(f'网页变动 = 13F 股数差（四舍五入到万）{tk}', shown, web)
check('网页 新进', [r[1] for r in rows if r[5] == '新进'], [x[1] for x in D.NEW])
check('网页 不变只数', sum(1 for r in rows if r[5] == '不变'), D.N_UNCHANGED)
for tk, fl in D.FILINGS.items():
    check(f'网页 本季申报明细 {tk}', filings.get(tk), fl)

# ---------------------------------------------------------------- 2) SEC 13F 原文（精确股数 / 历史）
UA = {'User-Agent': 'research-client contact@example.com'}
NS = {'n': 'http://www.sec.gov/edgar/document/thirteenf/informationtable'}
FILINGS = {'25Q3': '000119312525282901', '25Q4': '000119312526054580', '26Q1': '000119312526226661',
           '26Q2': '000119312526352200', '26Q3': '000119312526463399'}
CUSIP = {'AAPL': '037833100', 'GOOGL': '02079K305', 'GOOG': '02079K107', 'LEN': '526057104', 'LEN.B': '526057302',
         'DAL': '247361702', 'M': '55616P104', 'BAC': '060505104', 'COF': '14040H105', 'VRSN': '92343E102',
         'NUE': '670346105', 'KR': '501044101', 'DVA': '23918K108', 'BSP': 'T19377109'}
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA)).read()
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
try:
    Q = {k: load(v) for k, v in FILINGS.items()}
    cur, prev = Q['26Q3'], Q['26Q2']
    for zh, tk, s0, s1, web in D.ADD + D.CUT:
        check(f'SEC {tk}', (prev[CUSIP[tk]][0], cur[CUSIP[tk]][0]), (s0, s1))
    check('SEC 新进 BSP 股数', cur[CUSIP['BSP']][0], D.NEW[0][2])
    for tk, h in D.HIST.items():
        check(f'SEC 历史 {tk}', [Q[q].get(CUSIP[tk], [0])[0] for q in D.QUARTERS], h)
    check('SEC 苹果上期市值', round(prev[CUSIP['AAPL']][1] / 1e8, 2), D.AAPL_VALUE_PREV)
    check('SEC 13F 只数 = 网页美股只数', len(cur), len(D.US))
    # 莱纳建筑-A 的三份 Form 4（Berkshire 申报）：逐笔买入、价格区间、申报后持股
    F = D.LEN_FORM4; days, pxs, afters, first_before = set(), [], [], None
    for acc in F['accs']:
        base = f'https://www.sec.gov/Archives/edgar/data/1067983/{acc}/'
        name = [x['name'] for x in json.loads(get(base + 'index.json'))['directory']['item'] if x['name'].endswith('.xml')][0]
        r = ET.fromstring(get(base + name))
        for tr in r.iter('nonDerivativeTransaction'):
            if tr.findtext('securityTitle/value') != 'Class A Common Stock': continue
            sh = int(tr.findtext('transactionAmounts/transactionShares/value'))
            aft = int(tr.findtext('postTransactionAmounts/sharesOwnedFollowingTransaction/value'))
            if first_before is None: first_before = aft - sh
            days.add(tr.findtext('transactionDate/value')); pxs.append(float(tr.findtext('transactionAmounts/transactionPricePerShare/value')))
            check(f'SEC Form 4 {acc[-6:]} 买入', tr.findtext('transactionCoding/transactionCode'), 'P')
        afters.append(aft)
    check('SEC Form 4 交易日数', len(days), F['days'])
    check('SEC Form 4 首末日', (min(days)[5:], max(days)[5:]), (F['first'], F['last']))
    check('SEC Form 4 价格区间', (min(pxs), max(pxs)), (F['px_lo'], F['px_hi']))
    check('SEC Form 4 起止持股', (first_before, afters[-1]), (F['start'], F['end']))
    check('SEC Form 4 申报后持股 = 网页明细', [f'{round(a / 1e4)}万' for a in afters],
          [x[2] for x in D.FILINGS['LEN'] if x[1].startswith('Form 4')])
except OSError as e:
    print('SEC 无法访问，跳过第 2 部分：', e)
print('ALL OK' if ok else 'SOME CHECKS FAILED')
sys.exit(0 if ok else 1)
