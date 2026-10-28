"""解读图表用的公开数据 → data/*.json（已随仓库提交；只有想重新生成时才需要运行）。

用法：python3 src/data_prep.py
  cape_1881_2013.json  Shiller ie_data.xls：每月 CAPE 与此后十年年化实际回报（1881.01–2013.09），以及按 CAPE 五等份的平均回报
  nq_brk_1994_2015.json  Yahoo Finance ^IXIC（纳斯达克综合指数）与 BRK-A（伯克希尔 A 股）每日收盘，1994-01-03 – 2015-12-31
依赖：pandas、xlrd
"""
import datetime as dt, io, json, os, ssl, urllib.request
import numpy as np, pandas as pd

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
CA = '/root/.ccr/ca-bundle.crt'
CTX = ssl.create_default_context(cafile=CA if os.path.exists(CA) else None)


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=120, context=CTX) as r:
        return r.read()


x = pd.read_excel(io.BytesIO(get('http://www.econ.yale.edu/~shiller/data/ie_data.xls')), sheet_name='Data', header=7)
x = x[pd.to_numeric(x['Date'], errors='coerce').notna()].reset_index(drop=True)
D = x['Date'].astype(float).values
cape = pd.to_numeric(x['CAPE'], errors='coerce').values
fwd = pd.to_numeric(x['Real Return'], errors='coerce').values      # “10 Year Annualized Stock Real Return”（此后十年年化实际总回报）
m = ~np.isnan(cape) & ~np.isnan(fwd)
q = np.quantile(cape[m], [0.2, 0.8])
lo, hi = fwd[m][cape[m] <= q[0]].mean(), fwd[m][cape[m] >= q[1]].mean()
json.dump(dict(source='Shiller ie_data.xls：CAPE 与 10 Year Annualized Stock Real Return（含股息、扣除通胀）',
               date=[f'{d_:.2f}' for d_ in D[m]], cape=[round(float(v), 2) for v in cape[m]], fwd=[round(float(v), 4) for v in fwd[m]],
               q20=round(float(q[0]), 2), q80=round(float(q[1]), 2), mean_lo=round(float(lo), 4), mean_hi=round(float(hi), 4),
               corr=round(float(np.corrcoef(cape[m], fwd[m])[0, 1]), 3)),
          open(os.path.join(DATA, 'cape_1881_2013.json'), 'w'))
print(f'{D[m][0]:.2f}–{D[m][-1]:.2f}，{m.sum()} 个月；CAPE 最低五分之一（≤{q[0]:.1f}）此后十年年化 {lo:.1%}，最高五分之一（≥{q[1]:.1f}）{hi:.1%}')


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
