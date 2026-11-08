"""第三期数据：Yahoo Finance 日线（拆股调整收盘价，日元）→ data/prices.json；关键倍数 → data/calc.json

python3 data/calc.py          # 已有 prices.json 时只重算，不重新下载（--fetch 强制下载）
"""
import json, os, sys, datetime as dt, urllib.request
D = os.path.dirname(os.path.abspath(__file__))
SYMS = {'n225': '^N225', 'itochu': '8001.T', 'marubeni': '8002.T', 'mitsui': '8031.T', 'sumitomo': '8053.T',
        'mitsubishi': '8058.T', 'usdjpy': 'JPY=X'}
P1 = int(dt.datetime(1985, 1, 1).timestamp()); P2 = int(dt.datetime(2026, 11, 7).timestamp())


def fetch(sym):
    u = f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={P1}&period2={P2}&interval=1d'
    j = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60))
    r = j['chart']['result'][0]
    out = []
    for t, c in zip(r['timestamp'], r['indicators']['quote'][0]['close']):
        if c is None: continue
        d = (dt.datetime.utcfromtimestamp(t) + dt.timedelta(hours=9)).date().isoformat()
        if out and out[-1][0] == d: out[-1][1] = c
        else: out.append([d, c])
    return out


def at(series, day):
    best = None
    for d, c in series:
        if d <= day: best = c
        else: break
    return best


if __name__ == '__main__':
    pf = os.path.join(D, 'prices.json')
    if '--fetch' in sys.argv or not os.path.exists(pf):
        json.dump({k: fetch(s) for k, s in SYMS.items()}, open(pf, 'w'))
    P = json.load(open(pf))
    a, b = '2020-08-28', '2026-11-06'
    mult = {k: at(P[k], b) / at(P[k], a) for k in SYMS if k not in ('usdjpy',)}
    five = ['itochu', 'marubeni', 'mitsui', 'sumitomo', 'mitsubishi']
    calc = dict(base=a, close_day=b, mult=mult, avg5=sum(mult[k] for k in five) / 5,
                fx0=at(P['usdjpy'], '2020-08-31'), fx1=at(P['usdjpy'], b),
                n225_peak89=38915.87, n225_back=39098.68,
                cost=15382, mv2025=35368, div2025=862, yen_debt=14914, yen_rate=0.012,
                holdings2025={'mitsubishi': 10.8, 'itochu': 10.1, 'mitsui': 10.4, 'marubeni': 9.8, 'sumitomo': 9.7})
    json.dump(calc, open(os.path.join(D, 'calc.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps({k: round(v, 2) for k, v in mult.items()}, ensure_ascii=False), 'avg5', round(calc['avg5'], 2), 'fx', calc['fx0'], calc['fx1'])
