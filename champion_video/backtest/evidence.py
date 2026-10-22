"""「为什么两地差异这么大」的证据数据（全部来自回测所用的同一套数据）。

1. 动量还是反转：每年把全部股票按「上一年涨幅」分成 10 组，看下一年相对全市场等权平均的超额收益。
   美股 = 当年标普 500 成分股；A 股 = 沪深全部 A 股（含退市，剔除当年新股）。
2. 炒新：A 股每年涨幅前 50 名里，新股（当年上市，按发行价算涨幅）与次新股（上一年上市）的占比。
3. 利润 vs 股价：A 股冠军在「成为冠军那一年」的净利润增速，与股价涨幅对比（东方财富年报数据）。
4. 换手：A 股冠军当年的换手率 vs 全市场中位数（腾讯月线换手率字段）。
输出 evidence.json
"""
import json, os, sys, math
from collections import defaultdict
import numpy as np, pandas as pd, requests
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import CACHE
import us as US
import cn as CN

YEARS = range(2015, 2025)       # 选股年


# ---------------------------------------------------------------- A 股：月线（不复权 + 送转/派现近似复权）
def cn_month_all():
    out = {}
    for f in os.listdir(CN.MDIR):
        rows = json.load(open(os.path.join(CN.MDIR, f)))
        if isinstance(rows, list) and rows:
            df = pd.DataFrame([r[:8] if len(r) >= 8 else r[:6] + [None, None] for r in rows],
                              columns=['date', 'open', 'close', 'high', 'low', 'vol', 'x', 'turn'])
            df['date'] = pd.to_datetime(df.date)
            df = df.set_index('date')
            for c in ['open', 'close', 'high', 'low', 'vol']:
                df[c] = df[c].astype(float)
            df['turn'] = pd.to_numeric(df['turn'], errors='coerce')
            out[f[:-5]] = df[~df.index.duplicated(keep='last')].sort_index()
    return out


def cn_ret(s, df, y):
    """y 年总回报（年末收盘 → 年末收盘，送转按比例、派现按除权月前收盘近似再投资）"""
    e0, e1 = pd.Timestamp(f'{y - 1}-12-31'), pd.Timestamp(f'{y}-12-31')
    a, b = df[df.index <= e0], df[(df.index > e0) & (df.index <= e1)]
    if len(a) == 0 or len(b) == 0:
        return None
    mult = 1.0
    for d, bonus, cash, _, _ in CN.EV.get(s[2:], []):
        if a.index[-1] < d <= b.index[-1]:
            px = df[df.index < d].close
            mult *= (1 + bonus) * (1 + (cash / px.iloc[-1] if len(px) else 0))
    return b.close.iloc[-1] / a.close.iloc[-1] * mult - 1


def deciles(prev, nxt):
    """prev/nxt: dict sym->ret；返回 10 组下一年超额收益（组内等权 − 全体等权）与前 10 名超额"""
    syms = [s for s in prev if s in nxt]
    p = np.array([prev[s] for s in syms]); n = np.array([nxt[s] for s in syms])
    n = np.clip(n, -1, 20)
    order = np.argsort(p)
    groups = np.array_split(order, 10)
    base = n.mean()
    return [float(n[g].mean() - base) for g in groups], float(n[order[-10:]].mean() - base), float(n[order[-1]] - base)


def main():
    E = {}
    # ---------------- 1) 动量 / 反转
    M = cn_month_all()
    cn_r = {y: {} for y in range(2015, 2026)}
    for s, df in M.items():
        for y in range(2015, 2026):
            r = cn_ret(s, df, y)
            if r is not None:
                cn_r[y][s] = r
    us_r = {y: {} for y in range(2015, 2026)}
    for y in range(2015, 2026):
        for s in US.members(pd.Timestamp(f'{y}-12-31')) + US.members(pd.Timestamp(f'{y - 1}-12-31')):
            df = US.series(s)
            if df is None: continue
            r = US.year_return(df, y)
            if r is not None:
                us_r[y][s] = r
    out = {}
    for mk, R, uni in [('us', us_r, lambda y: set(US.members(pd.Timestamp(f'{y}-12-31')))), ('cn', cn_r, None)]:
        dec, top10, top1 = [], [], []
        for y in YEARS:
            prev = {s: v for s, v in R[y].items() if uni is None or s in uni(y)}
            d, t10, t1 = deciles(prev, R[y + 1])
            dec.append(d); top10.append(t10); top1.append(t1)
        out[mk] = dict(deciles=list(np.mean(dec, 0)), top10=float(np.mean(top10)), top1=float(np.mean(top1)),
                       top10_by_year=top10, n_years=len(dec))
    E['momentum'] = out
    print('momentum us', [round(x * 100, 1) for x in out['us']['deciles']], round(out['us']['top10'] * 100, 1))
    print('momentum cn', [round(x * 100, 1) for x in out['cn']['deciles']], round(out['cn']['top10'] * 100, 1))

    # ---------------- 2) 炒新：涨幅前 50 名中新股 / 次新股占比
    ipo = CN.IPO
    rows = []
    for y in YEARS:
        cand = []
        for s, df in M.items():
            info = ipo.get(s[2:])
            ld = info['LISTING_DATE'][:10] if info else None
            if s in cn_r[y]:
                kind = 'sub' if ld and ld[:4] == str(y - 1) else 'old'
                cand.append((cn_r[y][s], s, kind))
            elif info and info['ISSUE_PRICE'] and ld[:4] == str(y):
                b = df[(df.index > f'{y - 1}-12-31') & (df.index <= f'{y}-12-31')]
                if len(b):
                    mult = np.prod([1 + bonus for d, bonus, cash, _, _ in CN.EV.get(s[2:], []) if d <= b.index[-1]] or [1])
                    cand.append((b.close.iloc[-1] * mult / info['ISSUE_PRICE'] - 1, s, 'new'))
        cand.sort(reverse=True)
        top = cand[:50]
        n_new = sum(k == 'new' for _, _, k in top); n_sub = sum(k == 'sub' for _, _, k in top)
        nxt = [cn_r[y + 1].get(s) for _, s, _ in top if s in cn_r[y + 1]]
        rows.append(dict(year=y, new=n_new, sub=n_sub, old=50 - n_new - n_sub, top50_next=float(np.mean(np.clip(nxt, -1, 20))),
                         market_next=float(np.mean(np.clip(list(cn_r[y + 1].values()), -1, 20))),
                         top1=top[0][1], top1_kind=top[0][2], top1_ret=top[0][0]))
        print(y, 'top50 new', n_new, 'sub', n_sub, 'next', round(rows[-1]['top50_next'] * 100, 1), 'mkt', round(rows[-1]['market_next'] * 100, 1))
    E['ipo'] = rows
    E['ipo_summary'] = dict(new_sub_share=float(np.mean([(r['new'] + r['sub']) / 50 for r in rows])),
                            new_share=float(np.mean([r['new'] / 50 for r in rows])),
                            top1_new_years=sum(r['top1_kind'] == 'new' for r in rows))

    # ---------------- 3) 利润 vs 股价（A 股冠军）
    cn_out = json.load(open(os.path.join(HERE, 'out_cn.json')))
    prof = []
    for r in cn_out['main']:
        p = r['picks'][0]; code = p['sym'][2:]; y = r['year'] - 1
        d = requests.get('https://datacenter-web.eastmoney.com/api/data/v1/get', params=dict(
            reportName='RPT_LICO_FN_CPD', columns='SECURITY_CODE,REPORTDATE,PARENT_NETPROFIT',
            pageSize=200, filter=f'(SECURITY_CODE="{code}")', sortColumns='REPORTDATE', sortTypes=-1), timeout=30).json()
        np_ = {x['REPORTDATE'][:4]: x['PARENT_NETPROFIT'] for x in (d['result'] or {}).get('data', []) if x['REPORTDATE'][5:10] == '12-31'}
        a, b, c = np_.get(str(y - 1)), np_.get(str(y)), np_.get(str(y + 1))
        prof.append(dict(code=code, name=p['name'], year=y, price=p['prev'], np_prev=a, np_y=b, np_next=c,
                         growth=(b / a - 1) if a and b and a > 0 else None, next_ret=r['net']))
        print(y, p['name'], 'price', round(p['prev'] * 100), 'np', a, b, c)
    E['cn_profit'] = prof

    # ---------------- 4) 换手率
    turn = []
    for r in cn_out['main']:
        p = r['picks'][0]; s = p['sym']; y = r['year'] - 1
        def ann(df):
            q = df[(df.index > f'{y - 1}-12-31') & (df.index <= f'{y}-12-31')].turn
            return float(q.sum()) if q.notna().any() else None
        allt = [v for v in (ann(df) for ss, df in M.items() if ss in cn_r[y]) if v is not None]
        turn.append(dict(year=y, name=p['name'], champ=ann(M[s]), median=float(np.median(allt))))
        print(y, p['name'], 'turnover %', turn[-1]['champ'], 'median', round(turn[-1]['median']))
    E['turnover'] = turn
    json.dump(E, open(os.path.join(HERE, 'evidence.json'), 'w'), ensure_ascii=False, indent=1, default=float)


if __name__ == '__main__':
    CN.TRADING_DAYS = CN.calendar()
    main()
