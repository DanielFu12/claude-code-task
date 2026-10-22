"""A 股：每年买入「上一年涨幅冠军」回测（含已退市股票，考虑停牌、一字涨跌停、交易成本）。

数据
- 价格：腾讯证券不复权行情（月线用于全市场排名，日线用于候选股精确计算与交易模拟）。
- 复权：东方财富「分红送配」实施记录（送股、转增、派现），按交易所除权参考价公式自行计算比例复权因子：
      参考价 = (前收盘 − 每股派现) / (1 + 每股送转)，  因子 = 前收盘 / 参考价
  这样得到的是「持有人真实总回报」。破产重整中定向给重整投资人/债权人的资本公积转增不分配给原股东，
  不计入复权（腾讯后复权会把它当成送股，造成虚假涨幅）。

主口径（A1）
- 选股池：沪深两市全部 A 股（主板、原中小板、创业板、科创板），含此后退市的股票；
  剔除选股年 Y 当年才上市的新股（没有完整年度涨幅）。北交所不在范围内。
- 涨幅：Y 年全年总回报（上一年最后收盘 → 当年最后收盘，含分红送转），取第一名。
- 买入：Y+1 年第一个交易日开盘价；若当天停牌或「一字涨停」（全天最高 = 最低且涨幅 ≥ 4.8%，
  覆盖 ST 5% / 主板 10% / 创业板科创板 20%），顺延到第一个能成交的交易日开盘买入，期间资金闲置。
- 卖出：Y+1 年最后一个交易日收盘；若停牌或一字跌停，顺延到第一个能成交的交易日收盘。
  持有期内退市：按最后成交价清算。
- 成本：佣金 0.025%×2 + 滑点 0.10%×2 + 卖出印花税（2023-08-28 前 0.1%，之后 0.05%）。
对照口径
- A2：包含当年新股，新股涨幅按「发行价 → 年末收盘」计算（媒体年度涨幅榜常见口径）。
- A3：理想化 —— 假设第一个交易日开盘必能买到、年末收盘必能卖出，不计成本。
- Top5 / Top10 等权；基准：沪深 300 全收益指数 H00300（中证指数公司，含分红再投资）。
"""
import json, os, sys, subprocess
from collections import defaultdict
import numpy as np, pandas as pd
from common import cagr, CACHE

HERE = os.path.dirname(os.path.abspath(__file__))
MDIR = os.path.join(CACHE, 'cn', 'month')
DDIR = os.path.join(CACHE, 'cn', 'day')
SLIP, COMM = 0.0010, 0.00025

IPO = {x['SECURITY_CODE']: x for x in json.load(open(os.path.join(CACHE, 'cn', 'ipo.json')))}
EV = defaultdict(list)
for e in json.load(open(os.path.join(CACHE, 'cn', 'events.json'))):
    if e.get('ASSIGN_PROGRESS') != '实施分配' or not e.get('EX_DIVIDEND_DATE'):
        continue
    EV[e['SECURITY_CODE']].append((pd.Timestamp(e['EX_DIVIDEND_DATE'][:10]), (e['BONUS_IT_RATIO'] or 0) / 10,
                                   (e['PRETAX_BONUS_RMB'] or 0) / 10, e['IMPL_PLAN_PROFILE'], e['SECURITY_NAME_ABBR']))
NAMES_P = os.path.join(CACHE, 'cn', 'names.json')
NAMES = json.load(open(NAMES_P)) if os.path.exists(NAMES_P) else {}


def stamp(d):
    return 0.0005 if d >= pd.Timestamp('2023-08-28') else 0.001


def _df(rows):
    df = pd.DataFrame([r[:6] for r in rows], columns=['date', 'open', 'close', 'high', 'low', 'vol'])
    df['date'] = pd.to_datetime(df.date)
    df = df.set_index('date').astype(float)
    return df[~df.index.duplicated(keep='last')].sort_index()


def all_month():
    out = {}
    for f in sorted(os.listdir(MDIR)):
        rows = json.load(open(os.path.join(MDIR, f)))
        if isinstance(rows, list) and rows:
            out[f[:-5]] = _df(rows)
    return out


def prefetch(syms):
    need = [s for s in syms if not os.path.exists(os.path.join(DDIR, f'{s}_raw.json'))]
    if need:
        subprocess.run([sys.executable, os.path.join(HERE, 'fetch_cn.py'), 'day', DDIR] + need, check=True)


_day = {}
def day(sym):
    """不复权日线 + 比例复权因子列 adj（当日价格 × adj = 复权价）"""
    if sym in _day:
        return _day[sym]
    p = os.path.join(DDIR, f'{sym}_raw.json')
    if not os.path.exists(p):
        subprocess.run([sys.executable, os.path.join(HERE, 'fetch_cn.py'), 'day', DDIR, sym], check=True)
    df = _df(json.load(open(p)))
    adj = pd.Series(1.0, index=df.index)
    for d, bonus, cash, _, _ in sorted(EV.get(sym[2:], [])):
        prev = df[df.index < d]
        if len(prev) == 0 or d > df.index[-1]:
            continue
        pc = prev.close.iloc[-1]
        ref = (pc - cash) / (1 + bonus)
        adj[adj.index >= d] *= pc / ref
    df['adj'] = adj
    _day[sym] = df
    return df


def name_of(sym, when=None):
    c = sym[2:]
    if when is not None:   # 取当时的简称（分红记录里带有简称）
        ev = [e for e in EV.get(c, []) if e[0] <= when]
        if ev and abs((when - ev[-1][0]).days) < 400:
            pass
    return NAMES.get(c) or (IPO.get(c) or {}).get('SECURITY_NAME') or c


def approx_year_return(df, y):
    """月线粗算：不复权涨幅 × 送转倍数 × (1 + 派现/当月收盘)"""
    e0, e1 = pd.Timestamp(f'{y - 1}-12-31'), pd.Timestamp(f'{y}-12-31')
    a, b = df[df.index <= e0], df[(df.index > e0) & (df.index <= e1)]
    if len(a) == 0 or len(b) == 0:
        return None
    return a, b


def rank_year(M, y, include_ipo=False, exact_top=30):
    e0, e1 = pd.Timestamp(f'{y - 1}-12-31'), pd.Timestamp(f'{y}-12-31')
    cand = []
    for s, df in M.items():
        b = df[(df.index > e0) & (df.index <= e1)]
        if len(b) == 0:
            continue
        a = df[df.index <= e0]
        if len(a):
            mult = 1.0
            for d, bonus, cash, _, _ in EV.get(s[2:], []):
                if a.index[-1] < d <= b.index[-1]:
                    px = df[df.index < d].close
                    mult *= (1 + bonus) * (1 + (cash / px.iloc[-1] if len(px) else 0))
            cand.append((b.close.iloc[-1] / a.close.iloc[-1] * mult - 1, s, 'full'))
        elif include_ipo:
            ipo = IPO.get(s[2:])
            if ipo and ipo['ISSUE_PRICE'] and ipo['LISTING_DATE'][:4] == str(y):
                mult = np.prod([1 + bonus for d, bonus, cash, _, _ in EV.get(s[2:], []) if d <= b.index[-1]] or [1])
                cand.append((b.close.iloc[-1] * mult / ipo['ISSUE_PRICE'] - 1, s, 'ipo'))
    cand.sort(reverse=True)
    prefetch([s for _, s, _ in cand[:exact_top]])
    # 前 exact_top 名用日线精确计算（比例复权），确保冠军认定准确
    rows = []
    for g, s, kind in cand[:exact_top]:
        d = day(s)
        a = d[d.index <= e0]; b = d[(d.index > e0) & (d.index <= e1)]
        if kind == 'full':
            r = (b.close.iloc[-1] * b.adj.iloc[-1]) / (a.close.iloc[-1] * a.adj.iloc[-1]) - 1
        else:
            ipo = IPO[s[2:]]
            r = b.close.iloc[-1] * b.adj.iloc[-1] / (ipo['ISSUE_PRICE'] * b.adj.iloc[0]) - 1
        rows.append((s, r, kind, g))
    rows.sort(key=lambda x: -x[1])
    assert rows[0][1] > cand[exact_top][0] * 0.98 + 0.0, ('need larger exact_top', y)
    return rows, len(cand)


def locked(row, prev_close, up=True):
    """一字板：全天只有一个价格，且相对昨收涨/跌超过 4.8%"""
    if row.high - row.low > 1e-6 * row.close:
        return False
    ch = row.close / prev_close - 1
    return ch >= 0.048 if up else ch <= -0.048


def hold(sym, y, realistic=True):
    d = day(sym)
    cal = TRADING_DAYS[y]
    notes = []
    bi = None
    for t in (cal if realistic else cal[:1]):
        if t not in d.index:
            notes.append(f'{t.date()} 停牌'); continue
        prev = d[d.index < t].close.iloc[-1]
        if realistic and locked(d.loc[t], prev, True):
            notes.append(f'{t.date()} 一字涨停，买不进'); continue
        bi = t; break
    if bi is None:
        yr = d[(d.index >= f'{y}-01-01') & (d.index <= f'{y}-12-31')]
        if realistic or len(yr) == 0:
            return None
        bi = yr.index[0]
    last = cal[-1]
    si = None
    if realistic:
        for t in d[d.index >= last].index:
            prev = d[d.index < t].close.iloc[-1]
            if locked(d.loc[t], prev, False):
                notes.append(f'{t.date()} 一字跌停，卖不出'); continue
            si = t; break
        if si is None:
            si = d.index[-1]
        if si != last:
            notes.append(f'实际卖出 {si.date()}' + ('（退市清算）' if si < last else ''))
    else:
        si = d[d.index <= last].index[-1]
    buy = d.loc[bi].open * d.loc[bi].adj
    sell = d.loc[si].close * d.loc[si].adj
    gross = sell / buy - 1
    net = (1 + gross) * (1 - SLIP - COMM) * (1 - SLIP - COMM - stamp(si)) - 1 if realistic else gross
    seg = d[(d.index >= bi) & (d.index <= si)]
    val = seg.close * seg.adj / buy
    return dict(buy_date=str(bi.date()), sell_date=str(si.date()),
                buy_price=round(float(d.loc[bi].open), 2), sell_price=round(float(d.loc[si].close), 2),
                gross=float(gross), net=float(net), path=val.round(5).tolist(), dates=[str(x.date()) for x in seg.index],
                max_dd=float((val / val.cummax() - 1).min()), notes=notes,
                events=[f'{e[0].date()} {e[3]}' for e in EV.get(sym[2:], []) if bi <= e[0] <= si])


def calendar():
    df = day('sh000001')
    return {y: [t for t in df.index if t.year == y] for y in range(2014, 2026)}


TRADING_DAYS = None


def run(M, include_ipo=False, topn=1, realistic=True, years=range(2016, 2026)):
    cap, out = 1.0, []
    for y in years:
        rows, n = rank_year(M, y - 1, include_ipo)
        picks, hs, i = [], [], 0
        while len(picks) < topn:
            s, r, kind, _ = rows[i]; i += 1
            h = hold(s, y, realistic)
            if h is None:
                print('  !! 全年无法买入', s, y); continue
            picks.append((s, r, kind)); hs.append(h)
        net = float(np.mean([h['net'] for h in hs]))
        cap *= 1 + net
        out.append(dict(year=y, net=net, capital=cap, universe_n=n,
                        picks=[dict(sym=s, name=name_of(s), prev=r, kind=k, **h) for (s, r, k), h in zip(picks, hs)],
                        runner_up=[(s, name_of(s), r) for s, r, _, _ in rows[1:4]]))
    return out, cap


def csi_tri(code='H00300'):
    """中证指数公司官网：沪深 300 全收益指数（含成分股分红再投资）"""
    p = os.path.join(CACHE, 'cn', f'{code}.json')
    if not os.path.exists(p):
        import requests
        r = requests.get('https://www.csindex.com.cn/csindex-home/perf/index-perf',
                         params=dict(indexCode=code, startDate='20141201', endDate='20251231'), timeout=60).json()
        json.dump(r['data'], open(p, 'w'), ensure_ascii=False)
    rows = json.load(open(p))
    return pd.Series([float(x['close']) for x in rows], index=pd.to_datetime([x['tradeDate'] for x in rows])).sort_index()


def bench(years=range(2016, 2026)):
    d = csi_tri()
    cap, out = 1.0, []
    for y in years:
        p = d[d.index < f'{y}-01-01'].iloc[-1]
        q = d[(d.index >= f'{y}-01-01') & (d.index <= f'{y}-12-31')]
        v = q / p
        cap *= v.iloc[-1]
        out.append(dict(year=y, ret=float(v.iloc[-1] - 1), capital=cap, path=v.round(5).tolist()))
    return out, cap


if __name__ == '__main__':
    os.makedirs(DDIR, exist_ok=True)
    TRADING_DAYS = calendar()
    M = all_month()
    print('stocks loaded', len(M))
    res = {}
    variants = [('main', {}), ('ideal', dict(realistic=False)), ('with_ipo', dict(include_ipo=True)),
                ('top5', dict(topn=5)), ('top10', dict(topn=10))]
    for name, kw in variants:
        o, c = run(M, **kw)
        res[name] = o
        print(f'== CN {name}: total {c - 1:.2%}  CAGR {cagr(c, 10):.2%}')
        for r in o:
            p = r['picks'][0]
            print(f"  {r['year']} {p['sym']} {p['name']:6s} prev {p['prev']*100:8.1f}% ({p['kind']}) hold {r['net']*100:7.1f}%  "
                  f"buy {p['buy_date']} ¥{p['buy_price']} sell {p['sell_date']} ¥{p['sell_price']} cap {r['capital']:.4f} "
                  f"n={r['universe_n']} {p['notes'][:3]} {p['events']}" +
                  (f"  next {[(a, b, round(c*100)) for a, b, c in r['runner_up']]}" if name == 'main' else ''))
    b, bc = bench()
    res['bench'] = b
    print(f'CSI300 TRI total {bc - 1:.2%} CAGR {cagr(bc, 10):.2%}', [round(x['ret'] * 100, 1) for x in b])
    json.dump(res, open(os.path.join(HERE, 'out_cn.json'), 'w'), default=float, ensure_ascii=False)
