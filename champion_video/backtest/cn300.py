"""A 股（沪深 300 股票池）：每年买入「上一年沪深 300 成分股里的涨幅冠军」。

与美股口径对称：美股用「选股年年末的标普 500 成分股」，这里用「选股年年末的沪深 300 成分股」。
沪深 300 只纳入上市满一定时间、规模和流动性靠前的公司，天然排除了绝大多数次新股和小盘题材股，
比较更公平。价格、复权、停牌 / 一字板处理、交易成本与 cn.py 完全相同（直接复用）。

成分股历史（point-in-time）：qlib 社区数据集 chenditc/investment_data 的 instruments/csi300.txt
（代码、纳入日期、剔除日期；由中证指数公司调样公告整理）。核对：每年年末恰好 300 只；
与中证指数官网 2026-10-22 的 000300cons.xls 对比，300 只中 299 只一致。

口径
- main：选股年 Y 年末仍在沪深 300 中的成分股（同样剔除 Y 年当年上市的新股），取全年总回报第一名。
- start：只用 Y 年初就在指数里的成分股（排除年内新纳入的股票）。
- top5 / top10 等权；ideal：必能成交、零成本。基准：沪深 300 全收益指数 H00300。
"""
import json, os
import numpy as np, pandas as pd
import cn
from cn import CACHE, cagr

HERE = os.path.dirname(os.path.abspath(__file__))
# 已随仓库提交一份快照（data/csi300_history.txt，取自 qlib_bin/instruments/csi300.txt，2026-10-22 发布）
Q = pd.read_csv(os.path.join(HERE, 'data', 'csi300_history.txt'), sep='\t', header=None,
                names=['code', 's', 'e'])
Q['s'] = pd.to_datetime(Q.s); Q['e'] = pd.to_datetime(Q.e)
Q['sym'] = Q.code.str.lower()


def members(when):
    when = pd.Timestamp(when)
    return set(Q[(Q.s <= when) & (Q.e >= when)].sym)


def last_trading_day(y):
    return cn.TRADING_DAYS[y][-1]


def first_trading_day(y):
    return cn.TRADING_DAYS[y][0]


def run(M, topn=1, realistic=True, start=False, years=range(2016, 2026)):
    cap, out = 1.0, []
    for y in years:
        sel = y - 1
        mem = members(first_trading_day(sel)) if start else members(last_trading_day(sel))
        MM = {s: df for s, df in M.items() if s in mem}
        rows, n = cn.rank_year(MM, sel, False, exact_top=min(30, len(MM) - 1), exclude_sub=False)   # 沪深300版口径：只剔除当年新股
        picks, hs, i = [], [], 0
        while len(picks) < topn:
            s, r, kind, _ = rows[i]; i += 1
            h = cn.hold(s, y, realistic)
            if h is None:
                print('  !! 全年无法买入', s, y); continue
            picks.append((s, r, kind)); hs.append(h)
        net = float(np.mean([h['net'] for h in hs]))
        cap *= 1 + net
        out.append(dict(year=y, net=net, capital=cap, universe_n=n,
                        picks=[dict(sym=s, name=cn.name_of(s), prev=r, kind=k, **h) for (s, r, k), h in zip(picks, hs)],
                        runner_up=[(s, cn.name_of(s), r) for s, r, _, _ in rows[1:4]]))
    return out, cap


if __name__ == '__main__':
    cn.TRADING_DAYS = cn.calendar()
    M = cn.all_month()
    for y in range(2015, 2025):
        print(y, 'members at year end', len(members(last_trading_day(y))), 'with monthly data',
              len(members(last_trading_day(y)) & set(M)))
    res = {}
    for name, kw in [('main', {}), ('start', dict(start=True)), ('ideal', dict(realistic=False)),
                     ('top5', dict(topn=5)), ('top10', dict(topn=10))]:
        o, c = run(M, **kw)
        res[name] = o
        print(f'== CSI300 {name}: total {c - 1:.2%}  CAGR {cagr(c, 10):.2%}')
        for r in o:
            p = r['picks'][0]
            print(f"  {r['year']} {p['sym']} {p['name']:6s} prev {p['prev']*100:8.1f}% hold {r['net']*100:7.1f}%  "
                  f"buy {p['buy_date']} ¥{p['buy_price']} sell {p['sell_date']} ¥{p['sell_price']} cap {r['capital']:.4f} "
                  f"n={r['universe_n']} {p['notes'][:3]}" + (f"  next {[(a, b, round(c*100)) for a, b, c in r['runner_up']]}" if name == 'main' else ''))
    b, bc = cn.bench()
    res['bench'] = b
    print(f'CSI300 TRI total {bc - 1:.2%} CAGR {cagr(bc, 10):.2%}')
    json.dump(res, open(os.path.join(HERE, 'out_cn300.json'), 'w'), default=float, ensure_ascii=False)
