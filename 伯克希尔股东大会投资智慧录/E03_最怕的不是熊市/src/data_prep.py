"""解读图表用的公开数据 → data/*.json（已随仓库提交；只有想重新生成时才需要运行）。

用法：python3 src/data_prep.py
  sp_tr_1942.json    Shiller ie_data.xls（标普综合指数月均价 P、年化股息 D）→ 1942.03 起含股息再投资的累计倍数
  nq_brk_1994_2015.json  Yahoo Finance ^IXIC（纳斯达克综合指数）与 BRK-A（伯克希尔 A 股）每日收盘，1994-01-03 – 2015-12-31
依赖：pandas、xlrd
"""
import datetime as dt, io, json, os, ssl, urllib.request
import pandas as pd

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
CA = '/root/.ccr/ca-bundle.crt'
CTX = ssl.create_default_context(cafile=CA if os.path.exists(CA) else None)


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=120, context=CTX) as r:
        return r.read()


x = pd.read_excel(io.BytesIO(get('http://www.econ.yale.edu/~shiller/data/ie_data.xls')), sheet_name='Data', header=7)
x = x[pd.to_numeric(x['Date'], errors='coerce').notna()]
x = x[(x['Date'].astype(float) >= 1942.025) & (x['Date'].astype(float) <= 2019.015)]
P, D, T = x['P'].astype(float).tolist(), x['D'].astype(float).tolist(), x['Date'].astype(float).tolist()
tr = [1.0]
for i in range(1, len(P)):
    tr.append(tr[-1] * (P[i] + D[i] / 12) / P[i - 1])
json.dump(dict(source='Shiller ie_data.xls, S&P Composite monthly average price + dividends reinvested',
               date=[round(t, 2) for t in T], tr=[round(v, 4) for v in tr]), open(os.path.join(DATA, 'sp_tr_1942.json'), 'w'))
print('1942.03 → 2019.01 累计', round(tr[-1], 1), '倍')

def daily(sym):
    r = json.loads(get(f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1=757382400&period2=1451606400&interval=1d'))
    r = r['chart']['result'][0]
    days = [dt.datetime.fromtimestamp(t, dt.timezone.utc).date().isoformat() for t in r['timestamp']]
    return {d_: c for d_, c in zip(days, r['indicators']['quote'][0]['close']) if c}


nq, bk = daily('%5EIXIC'), daily('BRK-A')
days = sorted(set(nq) & set(bk))
json.dump(dict(source='Yahoo Finance ^IXIC 与 BRK-A 每日收盘（共同交易日）', date=days, ixic=[round(nq[d_], 2) for d_ in days],
               brka=[round(bk[d_], 1) for d_ in days]), open(os.path.join(DATA, 'nq_brk_1994_2015.json'), 'w'))
pk = max((nq[d_], d_) for d_ in days if d_ < '2001')
lo = min((nq[d_], d_) for d_ in days if '2000' < d_ < '2004')
rec = next((d_, nq[d_]) for d_ in days if d_ > '2002' and nq[d_] > pk[0])
print('纳指高点', pk, ' 低点', lo, f'{1 - lo[0] / pk[0]:.1%}', ' 收复', rec)
print('伯克希尔 1999', f"{bk['1999-12-31'] / bk['1998-12-31'] - 1:.1%}", ' 2000–2002', f"{bk['2002-12-31'] / bk['1999-12-31'] - 1:.1%}")
