"""沪深 300 版的归因证据（与 out_cn300.json 同一套数据）。输出 evidence300.json。

1. 冠军的下一年：两地冠军持有当年收益 vs 指数；赢的年份数、最差一年。
2. 复利的不对称：A 股冠军「赢的年份」与「输的年份」各自的复利乘积。
3. 利润 vs 股价：每只冠军持有当年的净利润变化（美股 SEC 10-K，A 股东方财富年报）与当年股价收益。
4. 动量还是反转（同为大盘股池）：按上一年涨幅排序，前 10 名在下一年相对股票池等权平均的超额收益。
   美股 = 选股年年末标普 500 成分股；A 股 = 选股年年末沪深 300 成分股。
"""
import json, os, sys, math
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import CACHE
import cn as CN
import cn300
import evidence as EV

YEARS = range(2015, 2025)


def main():
    E = {}
    u = json.load(open(os.path.join(HERE, 'out_us.json'))); c = json.load(open(os.path.join(HERE, 'out_cn300.json')))
    # 1 / 2
    uy = [r['net'] for r in u['main']]; ub = [r['ret'] for r in u['bench']]
    cy = [r['net'] for r in c['main']]; cb = [r['ret'] for r in c['bench']]
    win = [x for x in cy if x > 0]; lose = [x for x in cy if x <= 0]
    E['next_year'] = dict(us_beat=sum(a > b for a, b in zip(uy, ub)), cn_beat=sum(a > b for a, b in zip(cy, cb)),
                          us_worst=min(uy), cn_worst=min(cy), us_loss_years=sum(x < 0 for x in uy), cn_loss_years=sum(x < 0 for x in cy),
                          cn_win_mult=float(np.prod([1 + x for x in win])), cn_lose_mult=float(np.prod([1 + x for x in lose])),
                          cn_wins=win, cn_losses=lose)
    print(E['next_year'])
    # 3 利润
    P = json.load(open(os.path.join(CACHE, 'profits.json')))
    prof = []
    for mk, res, key in [('us', u, lambda p: p['sym']), ('cn', c, lambda p: p['sym'][2:])]:
        for r in res['main']:
            p = r['picks'][0]; y = r['year']; d = P[mk][key(p)]
            a, b = d.get(str(y - 1)), d.get(str(y))
            if a is None or b is None:
                g = None
            elif a > 0:
                g = b / a - 1
            else:
                g = None            # 亏损 → 盈利：增速无意义，单独标注
            prof.append(dict(mk=mk, year=y, sym=key(p), name=p['name'], np_prev=a, np_hold=b, growth=g,
                             turn=(a is not None and b is not None and a <= 0 < b), ret=r['net']))
            print(mk, y, key(p), p['name'], a, b, None if g is None else round(g * 100), round(r['net'] * 100, 1))
    E['profit'] = prof
    # 4 动量 / 反转（大盘股池）
    mom = json.load(open(os.path.join(HERE, 'evidence.json')))['momentum']['us']
    M = EV.cn_month_all()
    R = {y: {} for y in range(2015, 2026)}
    for s, df in M.items():
        for y in range(2015, 2026):
            r = EV.cn_ret(s, df, y)
            if r is not None:
                R[y][s] = r
    CN.TRADING_DAYS = CN.calendar()
    dec, top10 = [], []
    for y in YEARS:
        mem = cn300.members(cn300.last_trading_day(y))
        prev = {s: v for s, v in R[y].items() if s in mem}
        nxt = {s: v for s, v in R[y + 1].items() if s in prev}
        d, t10, _ = EV.deciles(prev, nxt)
        dec.append(d); top10.append(t10)
    E['momentum'] = dict(us=dict(top10=mom['top10'], deciles=mom['deciles']),
                         cn300=dict(top10=float(np.mean(top10)), deciles=list(np.mean(dec, 0)), top10_by_year=top10))
    print('momentum cn300 top10', round(np.mean(top10) * 100, 1), [round(x * 100, 1) for x in np.mean(dec, 0)], 'us', round(mom['top10'] * 100, 1))
    json.dump(E, open(os.path.join(HERE, 'evidence300.json'), 'w'), ensure_ascii=False, indent=1, default=float)


if __name__ == '__main__':
    main()
