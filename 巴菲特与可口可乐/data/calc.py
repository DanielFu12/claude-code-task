"""伯克希尔持有可口可乐（KO）的收益与股息计算。

数据来源（均为一手或可复核来源）：
  - 持股数 / 成本：伯克希尔致股东信持仓表（1988、1989、1994、2025 年报）；
    2026-06-30 持股数来自伯克希尔 13F-HR（SEC，2026-08-14 提交）。
  - 股价 / 每股股息 / 拆股：Yahoo Finance 日线（ko_daily.json，已按拆股调整到当前股本口径）。
  - 标普 500 全收益指数：Yahoo Finance ^SP500TR（sp500tr_daily.json，1988-01-04 起）。
  - 伯克希尔公布的年度股息：1994 年 $75M（2022 信）、1995 年 $88M（2010 信）、
    2022 年 $704M（2022 信）、2025 年 $816M（2025 年报）。

口径：
  - 「当前股本口径」= 把历史股数按此后全部拆股（1990、1992、1996、2012 年各 1 拆 2，合计 ×16）换算。
  - 市值 = 400,000,000 股 × 收盘价；未实现收益 = 市值 − 总成本 $1,298,888,000（未扣税）。
  - 累计股息为估算：按每个除息日伯克希尔「当时已知的最低持股数」计（保守）——
    1988 年的股息不计；1989-03-15 前按 1988 年末持股计；1994 年按伯克希尔公布的 $75M。
  - 股息未再投资（伯克希尔实际是拿现金另作他用），因此「股价回报」与「股息回报」分开列示。
运行：python3 calc.py  → 输出 calc.json 并打印摘要。
"""
import json, datetime as dt, os

HERE = os.path.dirname(os.path.abspath(__file__))
COST_TOTAL = 1_298_888_000          # 1994 年报：100,000,000 股，成本 $1,298,888K
SPLIT_TO_NOW_FROM_1988 = 16         # 1990、1992、1996、2012 四次 1 拆 2
TRANCHES = [  # (标签, 年末持股[当时口径], 当时口径到现在的倍数, 累计成本[美元])
    ('1988', 14_172_500, 16, 592_540_000),     # 1988 年报
    ('1989', 23_350_000, 16, 1_023_920_000),   # 1989 年报
    ('1994', 100_000_000, 4, 1_298_888_000),   # 1994 年报（1992 拆股后口径）
]
REPORTED_DIV = {1994: 75e6, 1995: 88e6, 2022: 704e6, 2025: 816e6}


def load_ko():
    d = json.load(open(os.path.join(HERE, 'ko_daily.json')))['chart']['result'][0]
    q = d['indicators']['quote'][0]; adj = d['indicators']['adjclose'][0]['adjclose']
    px = {}
    for i, t in enumerate(d['timestamp']):
        if q['close'][i]:
            px[dt.datetime.fromtimestamp(t, dt.UTC).date()] = (q['close'][i], adj[i], q['high'][i])
    divs = sorted((dt.datetime.fromtimestamp(v['date'], dt.UTC).date(), v['amount'])
                  for v in d['events']['dividends'].values())
    # Yahoo 在 2001-09-12（9·11 休市）多记了一条 0.18 的重复记录，剔除
    divs = [x for x in divs if x[0] != dt.date(2001, 9, 12)]
    return px, divs


def load_sp():
    d = json.load(open(os.path.join(HERE, 'sp500tr_daily.json')))['chart']['result'][0]
    c = d['indicators']['quote'][0]['close']
    return {dt.datetime.fromtimestamp(t, dt.UTC).date(): v for t, v in zip(d['timestamp'], c) if v}


def on_or_before(series, day):
    ks = [k for k in series if k <= day]
    return series[max(ks)]


def avg_between(series, a, b, idx=None):
    v = [(series[k] if idx is None else series[k][idx]) for k in series if a <= k <= b]
    return sum(v) / len(v)


def shares_at(day):
    """伯克希尔在某除息日的保守持股数（当前股本口径）"""
    if day.year < 1989: return 0
    if day < dt.date(1989, 3, 15): return 14_172_500 * 16
    if day.year < 1994: return 23_350_000 * 16
    if day.year == 1994: return None          # 用公布值
    return 400_000_000


def main():
    px, divs = load_ko(); sp = load_sp()
    last_day = max(px); close, _, _ = px[last_day]
    ath_close_day = max(px, key=lambda k: px[k][0])
    ath_high_day = max(px, key=lambda k: px[k][2] or 0)
    shares_now = 400_000_000
    mv = shares_now * close
    out = dict(asof=str(last_day), close=round(close, 2),
               ath_close=[str(ath_close_day), round(px[ath_close_day][0], 2)],
               ath_intraday=[str(ath_high_day), round(px[ath_high_day][2], 2)],
               shares=shares_now, cost=COST_TOTAL, market_value=mv,
               unrealized_gain=mv - COST_TOTAL, multiple=mv / COST_TOTAL,
               avg_cost_per_share=COST_TOTAL / shares_now)

    # 历次买入（换算到当前股本口径）
    prev_sh = prev_cost = 0; tr = []
    for lab, sh, k, cost in TRANCHES:
        cur = sh * k
        add_sh, add_cost = cur - prev_sh, cost - prev_cost
        tr.append(dict(year=lab, add_shares_now=add_sh, add_cost=add_cost,
                       cost_per_share_now=add_cost / add_sh, value_now=add_sh * close,
                       multiple=add_sh * close / add_cost, cum_shares_now=cur, cum_cost=cost))
        prev_sh, prev_cost = cur, cost
    out['tranches'] = tr

    # 年度股息
    by_year = {}
    for d, a in divs:
        if d > last_day: continue
        s = shares_at(d)
        if s is None: continue
        by_year[d.year] = by_year.get(d.year, 0) + a * s
    by_year.update({y: v for y, v in REPORTED_DIV.items()})
    dps = {}
    for d, a in divs: dps[d.year] = dps.get(d.year, 0) + a
    by_year = {y: v for y, v in by_year.items() if v > 0}
    out['dividends_by_year'] = {y: round(by_year[y]) for y in sorted(by_year)}
    out['dps_by_year'] = {y: round(dps[y], 4) for y in sorted(dps)}
    out['cum_dividends'] = sum(by_year.values())
    ann = dps[last_day.year] if last_day.month >= 10 else None
    q_latest = divs[-1][1]
    out['annual_dividend_run_rate'] = q_latest * 4 * shares_now
    out['dividend_yield_on_cost'] = q_latest * 4 * shares_now / COST_TOTAL
    out['dividend_yield_at_price'] = q_latest * 4 / close
    # 2026 年已除息的股息（3 次）——截至 asof
    out['div_2026_so_far'] = by_year.get(2026)

    # 对比：同一时间点把同样的钱买入标普 500 全收益指数
    windows = [(dt.date(1988, 6, 1), dt.date(1988, 12, 30)), (dt.date(1989, 1, 3), dt.date(1989, 3, 15)),
               (dt.date(1994, 1, 3), dt.date(1994, 8, 31))]
    sp_now = on_or_before(sp, last_day); ko_adj_now = px[last_day][1]
    sp_val = ko_tr_val = 0
    for (a, b), t in zip(windows, tr):
        sp_val += t['add_cost'] * sp_now / avg_between(sp, a, b)
        ko_tr_val += t['add_cost'] * ko_adj_now / avg_between(px, a, b, idx=1)
    out['compare'] = dict(
        berkshire_actual_total=mv + out['cum_dividends'],   # 市值 + 已收现金股息（未再投资）
        ko_dividends_reinvested=ko_tr_val,                  # 同样买入时点，股息再投资
        sp500_total_return=sp_val)

    # 1998 年泡沫：峰值与回本
    p98 = {k: v for k, v in px.items() if k.year == 1998}
    peak_day = max(p98, key=lambda k: p98[k][0]); peak = p98[peak_day][0]
    recover = min(k for k in px if k > peak_day and px[k][0] > peak)
    out['bubble'] = dict(peak_day=str(peak_day), peak_close_now_basis=round(peak, 3),
                         price_recovered_on=str(recover),
                         years_to_recover=round((recover - peak_day).days / 365.25, 1))
    # 峰值后 KO（股息再投资）vs 标普全收益
    out['bubble']['ko_tr_since_peak'] = px[last_day][1] / px[peak_day][1]
    out['bubble']['sp_tr_since_peak'] = sp_now / on_or_before(sp, peak_day)
    # 1988-06 → 1998 峰值
    a = dt.date(1988, 6, 1)
    out['bubble']['ko_tr_1988_to_peak'] = px[peak_day][1] / avg_between(px, a, dt.date(1988, 12, 30), 1)
    out['bubble']['sp_tr_1988_to_peak'] = on_or_before(sp, peak_day) / avg_between(sp, a, dt.date(1988, 12, 30))
    yrs = (last_day - dt.date(1988, 9, 15)).days / 365.25
    out['cagr_price_from_1988_tranche'] = (close / tr[0]['cost_per_share_now']) ** (1 / yrs) - 1
    # 股价拆解：利润增长 × 估值变化（1998 年报口径 EPS 换算到当前股本：÷2）
    eps88, px88 = 0.37 / 2, 5.58 / 2          # 1988 持续经营 EPS、1988-12-31 股价（KO 1998 10-K）
    eps25 = 3.04                              # 2025 摊薄 EPS（KO 2025 10-K）
    out['decomp'] = dict(eps_1988=eps88, eps_2025=eps25, eps_growth=eps25 / eps88,
                         pe_1988=px88 / eps88, pe_now=close / eps25,
                         price_growth=close / px88, dps_1988=0.075, dps_2026=q_latest * 4,
                         dps_growth=q_latest * 4 / 0.075)
    out['cagr_ko_tr_1988'] = (px[last_day][1] / avg_between(px, a, dt.date(1988, 12, 30), 1)) ** (1 / yrs) - 1
    out['cagr_sp_tr_1988'] = (sp_now / avg_between(sp, a, dt.date(1988, 12, 30))) ** (1 / yrs) - 1
    out['cagr_price_from_avg_cost'] = (close / out['avg_cost_per_share']) ** (1 / ((last_day - dt.date(1990, 1, 1)).days / 365.25)) - 1

    # 1988 年批次每投入 1 美元，今天值多少（同一口径：38 年按 1988 年首笔买入起算）
    c88 = tr[0]['cost_per_share_now']
    cum_dps = sum(v for y, v in out['dps_by_year'].items() if 1989 <= int(y) <= last_day.year)   # 1988 年股息不计（保守）
    out['per_dollar_1988'] = dict(
        years=round(yrs, 2), price=close / c88, cash_dividends=(close + cum_dps) / c88,
        reinvested=(1 + out['cagr_ko_tr_1988']) ** yrs, sp500_tr=(1 + out['cagr_sp_tr_1988']) ** yrs,
        cagr_price=out['cagr_price_from_1988_tranche'], cagr_cash=((close + cum_dps) / c88) ** (1 / yrs) - 1,
        cagr_reinvested=out['cagr_ko_tr_1988'], cagr_sp500_tr=out['cagr_sp_tr_1988'])

    json.dump(out, open(os.path.join(HERE, 'calc.json'), 'w'), indent=1, ensure_ascii=False, default=str)
    return out


if __name__ == '__main__':
    o = main()
    for k, v in o.items():
        if k not in ('dividends_by_year', 'dps_by_year'): print(k, v)
    print('dividends_by_year', {y: round(v / 1e6, 1) for y, v in o['dividends_by_year'].items()})
