"""第二期《巴菲特与苹果》的全部数字（截至 2026-11-02 收盘）。

数据：
  - 苹果日线（含股息、拆股事件）：Yahoo Finance，data/aapl_daily.json；标普 500 全收益 ^SP500TR：data/sp500tr_daily.json
  - 伯克希尔 13F（2016Q1–2026Q2，逐季持股，已按 2020 年 1 拆 4 调整）：research/13f_apple.json（SEC EDGAR）
  - 伯克希尔致股东信持仓表（成本、市值）：research/letters_apple.md
口径说明：
  - 13F 只给季末持股，季度内的买卖价格未知 → 按该季度日均收盘价估算买卖金额（标注为“估算”）；
    官方给出的成本（2018 年末 $36,044M；2020 信“Our cost for that stake was $36 billion”）优先。
  - 股息：每个除息日的每股股息（拆股调整）× 上一季末 13F 持股（估算）。
"""
import json, os, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
ASOF = dt.date(2026, 11, 2)


def series(f):
    d = json.load(open(os.path.join(HERE, f)))['chart']['result'][0]
    q = d['indicators']['quote'][0]; adj = d['indicators'].get('adjclose', [{}])[0].get('adjclose') or q['close']
    rows = [(dt.datetime.fromtimestamp(t, dt.UTC).date(), c, a) for t, c, a in zip(d['timestamp'], q['close'], adj) if c]
    divs = sorted((dt.datetime.fromtimestamp(int(k), dt.UTC).date(), v['amount']) for k, v in d.get('events', {}).get('dividends', {}).items())
    return [r for r in rows if r[0] <= ASOF], [x for x in divs if x[0] <= ASOF]


def avg(rows, a, b, idx=1):
    v = [r[idx] for r in rows if a <= r[0] <= b]
    return sum(v) / len(v)


def at(rows, d, idx=1):
    return [r for r in rows if r[0] <= d][-1][idx]


def qbounds(q):
    y, n = int(q[:4]), int(q[5])
    a = dt.date(y, 3 * n - 2, 1); b = dt.date(y + (n == 4), (3 * n % 12) + 1, 1) - dt.timedelta(days=1)
    return a, b


def main():
    px, divs = series('aapl_daily.json')
    sp, _ = series('sp500tr_daily.json')
    f13 = json.load(open(os.path.join(ROOT, 'research', '13f_apple.json')))
    Q = f13['berkshire_13f_aapl']
    close = at(px, ASOF)
    out = dict(asof=str(ASOF), close=close)
    ath = max(px, key=lambda r: r[1]); out['ath'] = dict(date=str(ath[0]), close=ath[1])
    # ---- 逐季持股与估算现金流
    prev = 0; flows = []; buys = sells = 0.0; sold_sh = 0
    hold = []
    for q in Q:
        sh = q['split_adjusted_shares']; d = sh - prev
        a, b = qbounds(q['quarter'])
        p = avg(px, a, b)
        if d > 0: buys += d * p; flows.append((b, -d * p))
        if d < 0: sells += -d * p; sold_sh += -d; flows.append((b, -d * p))
        hold.append((q['period'], sh)); prev = sh
    out['holdings'] = hold
    peak = max(hold, key=lambda x: x[1]); out['peak'] = dict(period=peak[0], shares=peak[1])
    now_sh = hold[-1][1]; out['shares_now'] = now_sh
    out['est_buys'] = buys; out['est_sells'] = sells; out['shares_sold_since_peak'] = peak[1] - now_sh
    # 2023 年起的减持（最后一次买入 2023Q1 之后）
    s23 = 0.0; sh23 = 0; prev = None
    for q in Q:
        sh = q['split_adjusted_shares']
        if prev is not None and q['quarter'] >= '2023Q4' and sh < prev:
            a, b = qbounds(q['quarter']); s23 += (prev - sh) * avg(px, a, b); sh23 += prev - sh
        prev = sh
    out['sells_since_2023'] = dict(shares=sh23, proceeds_est=s23, avg_price=s23 / sh23)
    # ---- 股息（估算）
    def shares_on(day):
        h = [s for p, s in hold if dt.date.fromisoformat(p) < day]
        return h[-1] if h else 0
    cum_div = sum(a * shares_on(d) for d, a in divs if d >= dt.date(2016, 4, 1))
    out['cum_dividends_est'] = cum_div
    # ---- 今天的状态
    out['value_now'] = now_sh * close
    out['value_if_held_peak'] = peak[1] * close
    out['value_if_held_915m'] = 915_560_382 * close
    out['cost_official_2018'] = 36_044e6
    out['avg_cost_per_share'] = 36_044e6 / 1_021_201_316 if False else 36e9 / peak[1]
    # 总回报（估算）：现值 + 已卖出所得 + 累计股息 − 买入
    out['total_value_est'] = out['value_now'] + sells + cum_div
    out['total_multiple_est'] = out['total_value_est'] / buys
    # 同样的钱、同样时间买标普 500 全收益并持有至今
    spv = 0.0
    for d, cf in flows:
        if cf < 0: spv += -cf * at(sp, ASOF) / at(sp, d)
    out['sp500_same_buys'] = spv
    # ---- 估值：买入时 vs 卖出时（13F 隐含价 / 年报 EPS）
    fund = f13['apple_fundamentals']
    out['pe'] = dict(buy_2016=f13.get('apple_derived', {}), )
    eps = {k: v['eps_diluted_split_adjusted'] for k, v in fund.items()}
    out['eps'] = eps
    out['pe_points'] = dict(
        q4_2016=avg(px, dt.date(2016, 10, 1), dt.date(2016, 12, 31)) / eps['FY2016'],
        q1_2018=avg(px, dt.date(2018, 1, 1), dt.date(2018, 3, 31)) / eps['FY2017'],
        q2_2024=avg(px, dt.date(2024, 4, 1), dt.date(2024, 6, 30)) / eps['FY2023'],
        now=close / eps['FY2026'])
    out['net_income'] = {k: v['net_income_usd'] for k, v in fund.items()}
    out['shares_out'] = {k: v['diluted_wavg_shares_split_adjusted'] for k, v in fund.items()}
    out['buybacks'] = {k: v.get('buybacks_usd') for k, v in fund.items()}
    json.dump(out, open(os.path.join(HERE, 'calc.json'), 'w'), indent=1, default=str, ensure_ascii=False)
    return out


if __name__ == '__main__':
    o = main()
    for k in ['close', 'ath', 'peak', 'shares_now', 'est_buys', 'est_sells', 'sells_since_2023', 'cum_dividends_est', 'value_now',
              'value_if_held_peak', 'value_if_held_915m', 'total_value_est', 'total_multiple_est', 'sp500_same_buys', 'pe_points']:
        v = o[k]
        print(k, (f'{v/1e9:,.1f}B' if isinstance(v, float) and v > 1e6 else v))
