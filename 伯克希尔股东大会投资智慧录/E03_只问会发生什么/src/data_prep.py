"""解读图表用的公开数据 → data/*.json（已随仓库提交；只有想重新生成时才需要运行）。

用法：python3 src/data_prep.py
  sp_tr_1942.json    Shiller ie_data.xls（标普综合指数月均价 P、年化股息 D）→ 1942.03 起含股息再投资的累计倍数
  sp_2008_2010.json  Yahoo Finance ^GSPC 每日收盘，2008-09-22 – 2010-11-16
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

r = json.loads(get('https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?period1=1222000000&period2=1290000000&interval=1d'))
r = r['chart']['result'][0]
days = [dt.datetime.fromtimestamp(t, dt.timezone.utc).date().isoformat() for t in r['timestamp']]
close = r['indicators']['quote'][0]['close']
json.dump(dict(source='Yahoo Finance ^GSPC daily close', date=days, close=[round(c, 2) for c in close]),
          open(os.path.join(DATA, 'sp_2008_2010.json'), 'w'))
lo = min(zip(close, days))
print('最低收盘', lo, ' 2010-09-20', close[days.index('2010-09-20')])
