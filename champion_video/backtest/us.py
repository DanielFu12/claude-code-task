"""美股：每年买入「上一年标普 500 涨幅冠军」回测。

规则（主口径）
- 选股池：选股年 Y 最后一个交易日仍在标普 500 指数内的成分股（时点成分，来自 fja05680/sp500 历史成分表，
  含后来被剔除/退市的公司，避免幸存者偏差）。
- 涨幅：Y 年全年总回报（Yahoo 复权收盘价 adjclose，含拆股与分红），取第一名。
- 交易：Y+1 年第一个交易日开盘买入，最后一个交易日收盘卖出；全部资金滚入下一年冠军。
- 成本：买卖各 0.10%（佣金 + 滑点的保守估计）。
- 对照：标普 500 全收益指数 ^SP500TR；稳健性：前 5 / 前 10 名等权、年初成分股口径。
"""
import json, os, sys
import numpy as np, pandas as pd
from common import load_us, cagr, CACHE

COST = 0.0010
HERE = os.path.dirname(os.path.abspath(__file__))
CONST = pd.read_csv(os.path.join(CACHE, 'sp500', 'S&P 500 Historical Components & Changes (Updated).csv'))
CONST['date'] = pd.to_datetime(CONST.date)


def members(on):
    r = CONST[CONST.date <= on].iloc[-1]
    return sorted(r.tickers.split(','))


_cache = {}
def series(sym):
    if sym not in _cache:
        _cache[sym] = load_us(sym)
    return _cache[sym]


def year_return(df, y):
    """Y 年全年总回报：(Y 年最后收盘 adj) / (Y-1 年最后收盘 adj)；要求两端都有数据且当年交易日完整"""
    a = df[df.index <= f'{y - 1}-12-31']
    b = df[(df.index > f'{y - 1}-12-31') & (df.index <= f'{y}-12-31')]
    if len(a) == 0 or len(b) < 200 or a.index[-1] < pd.Timestamp(f'{y - 1}-12-20') or b.index[-1] < pd.Timestamp(f'{y}-12-20'):
        return None
    return b.adjclose.iloc[-1] / a.adjclose.iloc[-1] - 1


def rank_year(y, universe='end'):
    syms = members(pd.Timestamp(f'{y}-12-31')) if universe == 'end' else members(pd.Timestamp(f'{y - 1}-12-31'))
    rows, missing = [], []
    for s in syms:
        df = series(s)
        r = year_return(df, y) if df is not None else None
        if r is None:
            missing.append(s)
        else:
            rows.append((s, r))
    rows.sort(key=lambda x: -x[1])
    return rows, missing, len(syms)


def hold(sym, y):
    """Y 年第一个交易日开盘买入、最后交易日收盘卖出；返回明细（含真实成交价）"""
    df = series(sym)
    d = df[(df.index >= f'{y}-01-01') & (df.index <= f'{y}-12-31')]
    b, e = d.iloc[0], d.iloc[-1]
    adj_open = b.open * b.adjclose / b.close            # 开盘价换算到复权口径
    gross = e.adjclose / adj_open - 1
    net = (1 + gross) * (1 - COST) * (1 - COST) - 1
    path = (d.adjclose / adj_open).round(5).tolist()     # 当年每日相对买入价的净值（用于动画）
    return dict(buy_date=str(d.index[0].date()), sell_date=str(d.index[-1].date()),
                buy_price=round(b.open * b.split_after, 2), sell_price=round(e.close * e.split_after, 2),
                gross=gross, net=net, path=path, dates=[str(x.date()) for x in d.index],
                max_dd=float((d.adjclose / d.adjclose.cummax() - 1).min()),
                full_year=bool(d.index[-1] >= pd.Timestamp(f'{y}-12-20')))


def run(universe='end', topn=1, years=range(2016, 2026)):
    cap, out = 1.0, []
    for y in years:
        rows, missing, n = rank_year(y - 1, universe)
        picks = rows[:topn]
        hs = [hold(s, y) for s, _ in picks]
        net = float(np.mean([h['net'] for h in hs]))
        cap *= 1 + net
        out.append(dict(year=y, picks=[dict(sym=s, name=series(s).attrs['name'], prev=r, **h) for (s, r), h in zip(picks, hs)],
                        net=net, capital=cap, universe_n=n, missing=missing, runner_up=rows[1:4]))
    return out, cap


def bench(years=range(2016, 2026)):
    df = series('^SP500TR')
    cap, out = 1.0, []
    for y in years:
        d = df[(df.index >= f'{y}-01-01') & (df.index <= f'{y}-12-31')]
        p = df[df.index < f'{y}-01-01'].adjclose.iloc[-1]
        r = d.adjclose.iloc[-1] / p - 1
        cap *= 1 + r
        out.append(dict(year=y, ret=r, capital=cap, path=(d.adjclose / p).round(5).tolist()))
    return out, cap


if __name__ == '__main__':
    res = {}
    main, cap = run()
    print('== US main: S&P 500 year-end members, champion, open->close, 0.1%/side')
    for r in main:
        p = r['picks'][0]
        print(f"{r['year']} {p['sym']:6s} {p['name'][:28]:28s} prev {p['prev']*100:8.1f}%  hold {p['net']*100:7.1f}%  "
              f"buy {p['buy_date']} ${p['buy_price']}  sell {p['sell_date']} ${p['sell_price']}  cap {r['capital']:.3f}  "
              f"n={r['universe_n']} miss={len(r['missing'])}  next: {[(s, round(x*100)) for s, x in r['runner_up']]}")
    print(f'total {cap - 1:.2%}  CAGR {cagr(cap, 10):.2%}')
    b, bc = bench()
    print(f'S&P500TR total {bc - 1:.2%} CAGR {cagr(bc, 10):.2%}', [round(x['ret'] * 100, 1) for x in b])
    res['main'] = main; res['bench'] = b
    for name, kw in [('top5', dict(topn=5)), ('top10', dict(topn=10)), ('start_members', dict(universe='start'))]:
        o, c = run(**kw)
        res[name] = o
        print(f'{name}: total {c - 1:.2%}  CAGR {cagr(c, 10):.2%}  yearly', [round(x['net'] * 100, 1) for x in o],
              [x['picks'][0]['sym'] for x in o] if name == 'start_members' else '')
    json.dump(res, open(os.path.join(HERE, 'out_us.json'), 'w'), default=float)
