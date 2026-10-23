"""原版（沪深全 A，剔除次新股）的归因证据，输出 evidence_v6.json。

1. 冠军的第二年：两地冠军持有当年收益 vs 指数。
2. 第一性原理拆解：股价 ≈ 利润 × 估值。对每只冠军，持有当年的股价收益拆成
   「利润变化」（归母净利润同比）与「估值变化」（(1 + 股价收益) / (1 + 利润变化) − 1，近似市盈率变化，未计股本变动）。
   亏损或由亏转盈时估值变化无意义，单独标注。
3. 利润能否延续：冠军「夺冠年 → 持有年 → 再下一年」的利润轨迹。
4. 动量还是反转：上一年涨幅前 10 名，下一年相对股票池等权平均的超额收益（十年平均）。
   美股 = 标普 500 成分股；A 股 = 沪深全 A（剔除次新股，与回测同口径）。
5. 冠军是不是大盘股：冠军在夺冠年年末是否属于沪深 300 成分股。
"""
import json, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import CACHE
import cn as CN
import evidence as EV
import fetch_profits as FP
import cn300

YEARS = range(2015, 2025)


def main():
    E = {}
    u = json.load(open(os.path.join(HERE, 'out_us.json'))); c = json.load(open(os.path.join(HERE, 'out_cn.json')))
    uy = [r['net'] for r in u['main']]; ub = [r['ret'] for r in u['bench']]
    cy = [r['net'] for r in c['main']]; cb = [r['ret'] for r in c['bench']]
    E['next_year'] = dict(us_beat=sum(a > b for a, b in zip(uy, ub)), cn_beat=sum(a > b for a, b in zip(cy, cb)),
                          us_loss=sum(x < 0 for x in uy), cn_loss=sum(x < 0 for x in cy), us_worst=min(uy), cn_worst=min(cy),
                          cn_big_loss=sum(x <= -0.3 for x in cy))
    print(E['next_year'])
    # 利润
    P = json.load(open(os.path.join(CACHE, 'profits.json')))
    for r in c['main']:
        code = r['picks'][0]['sym'][2:]
        if code not in P['cn']:
            P['cn'][code] = {str(k): v for k, v in FP.cn(code).items()}
    json.dump(P, open(os.path.join(CACHE, 'profits.json'), 'w'), indent=1)
    rows = []
    for mk, res, key in [('us', u, lambda p: p['sym']), ('cn', c, lambda p: p['sym'][2:])]:
        for r in res['main']:
            p = r['picks'][0]; y = r['year']; d = {int(k): v for k, v in P[mk][key(p)].items()}
            a, b, n = d.get(y - 1), d.get(y), d.get(y + 1)
            g = (b / a - 1) if (a and b and a > 0) else None
            turn = a is not None and b is not None and a <= 0 < b
            pe = ((1 + r['net']) / (1 + g) - 1) if (g is not None and b > 0) else None
            rows.append(dict(mk=mk, year=y, sym=key(p), name=p['name'], np_champ=a, np_hold=b, np_after=n, growth=g, turn=turn,
                             loss=(b is not None and b <= 0), pe_change=pe, ret=r['net']))
            print(mk, y, key(p), p['name'], None if a is None else round(a / 1e8, 2), None if b is None else round(b / 1e8, 2),
                  None if g is None else round(g * 100), 'turn' if turn else '', None if pe is None else round(pe * 100), round(r['net'] * 100, 1))
    E['profit'] = rows
    # 动量 / 反转
    mom = json.load(open(os.path.join(HERE, 'evidence.json')))['momentum']['us']
    M = EV.cn_month_all()
    R = {y: {} for y in range(2015, 2026)}
    for s, df in M.items():
        for y in range(2015, 2026):
            r = EV.cn_ret(s, df, y)
            if r is not None:
                R[y][s] = r
    top10 = []
    for y in YEARS:
        prev = {s: v for s, v in R[y].items() if (CN.listing_year(s) is None or CN.listing_year(s) < y - 1)}
        _, t10, _ = EV.deciles(prev, R[y + 1])
        top10.append(t10)
    E['momentum'] = dict(us_top10=mom['top10'], cn_top10=float(np.mean(top10)), cn_top10_by_year=top10)
    print('momentum', round(mom['top10'] * 100, 1), round(np.mean(top10) * 100, 1))
    # 是否沪深 300 成分
    CN.TRADING_DAYS = CN.calendar()
    E['in_csi300'] = [dict(year=r['year'], name=r['picks'][0]['name'],
                           member=r['picks'][0]['sym'] in cn300.members(cn300.last_trading_day(r['year'] - 1))) for r in c['main']]
    print('in csi300', sum(x['member'] for x in E['in_csi300']))
    json.dump(E, open(os.path.join(HERE, 'evidence_v6.json'), 'w'), ensure_ascii=False, indent=1, default=float)


if __name__ == '__main__':
    main()
