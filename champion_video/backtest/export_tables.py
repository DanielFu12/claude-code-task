"""把回测结果导出为可读的数据表：results.csv（逐年明细）+ RESULTS.md（含汇总、口径对照）。"""
import csv, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
us = json.load(open(os.path.join(HERE, 'out_us.json')))
cn = json.load(open(os.path.join(HERE, 'out_cn.json')))

US_CN = {'NFLX': '奈飞', 'NVDA': '英伟达', 'NRG': 'NRG能源', 'AMD': '超威半导体', 'TSLA': '特斯拉', 'DVN': '德文能源',
         'OXY': '西方石油', 'PLTR': 'Palantir'}


def pct(x, nd=1):
    return f'{x * 100:+,.{nd}f}%'


def cagr(m):
    return m ** 0.1 - 1


rows = []
for mk, res, bench, uni, cur in [('美股', us['main'], us['bench'], '标普500 当年年末成分股（含后来退市）', '$'),
                                  ('A股', cn['main'], cn['bench'], '沪深全部A股（含退市，剔除次新股：选股年及上一年上市的股票）', '¥')]:
    for r, b in zip(res, bench):
        p = r['picks'][0]
        code = p['sym'] if mk == '美股' else p['sym'][2:]
        name = US_CN.get(p['sym'], p['name']) if mk == '美股' else p['name']
        rows.append({'市场': mk, '投资年度': r['year'], '选股年度': r['year'] - 1, '股票池': uni, '股票池数量': r['universe_n'],
                     '冠军代码': code, '冠军名称': name, '选股年涨幅(总回报)': pct(p['prev']),
                     '买入日期': p['buy_date'], '买入价(当时实际成交价)': f"{cur}{p['buy_price']}",
                     '卖出日期': p['sell_date'], '卖出价(当时实际成交价)': f"{cur}{p['sell_price']}",
                     '持有年度总回报(未扣成本)': pct(p['gross']), '持有年度净收益(扣成本)': pct(r['net']),
                     '期末资金(本金10万)': f"{r['capital'] * 10:,.2f}万", '累计收益': pct(r['capital'] - 1),
                     '同期指数': pct(b['ret']), '指数累计': pct(b['capital'] - 1),
                     '年内最大回撤': pct(p['max_dd']), '备注': '；'.join(p.get('notes', []) + p.get('events', [])[:2])})

with open(os.path.join(HERE, 'results.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)


def table(mk):
    out = ['| 投资年度 | 冠军（代码） | 上一年涨幅 | 买入 | 卖出 | 当年净收益 | 期末资金 | 同期指数 |', '|---|---|---|---|---|---|---|---|']
    for r in rows:
        if r['市场'] != mk: continue
        out.append(f"| {r['投资年度']} | {r['冠军名称']}（{r['冠军代码']}） | {r['选股年涨幅(总回报)']} | {r['买入日期']} {r['买入价(当时实际成交价)']} | "
                   f"{r['卖出日期']} {r['卖出价(当时实际成交价)']} | {r['持有年度净收益(扣成本)']} | {r['期末资金(本金10万)']} | {r['同期指数']} |")
    return '\n'.join(out)


def var_line(name, res):
    c = res[-1]['capital']
    return f'| {name} | {pct(c - 1)} | {pct(cagr(c))} | {c * 10:,.2f} 万 |'


ut, ub = us['main'][-1]['capital'], us['bench'][-1]['capital']
ct, cb = cn['main'][-1]['capital'], cn['bench'][-1]['capital']
md = f"""# 十年回测结果（2016—2025 投资年度）

> 由 `backtest/us.py`、`backtest/cn.py` 生成，`export_tables.py` 导出。逐年完整字段见 `results.csv`。
> 本金 10 万（本币），复利滚动，收益均为含分红再投资的总回报，「净收益」已扣交易成本。

## 汇总

| 策略 | 十年累计 | 年化（CAGR） | 10 万变成 |
|---|---|---|---|
{var_line('美股：每年买入上一年标普500涨幅冠军', us['main'])}
{var_line('　对照：标普500 全收益指数（^SP500TR）', us['bench'])}
{var_line('A股：每年买入上一年全市场涨幅冠军', cn['main'])}
{var_line('　对照：沪深300 全收益指数（H00300）', cn['bench'])}

## 美股逐年明细（标普500 当年年末成分股）

{table('美股')}

## A股逐年明细（沪深全部 A 股，含已退市，剔除次新股）

{table('A股')}

## 稳健性检验（口径对照）

| 口径 | 十年累计 | 年化 | 10 万变成 |
|---|---|---|---|
{var_line('美股 · 主口径（年末成分股，只买冠军）', us['main'])}
{var_line('美股 · 年初成分股（排除年内新纳入，如 2020 年的特斯拉）', us['start_members'])}
{var_line('美股 · 前 5 名等权', us['top5'])}
{var_line('美股 · 前 10 名等权', us['top10'])}
{var_line('A股 · 主口径', cn['main'])}
{var_line('A股 · 保留次新股（只剔除当年新股，v1–v5 视频口径）', cn['incl_sub'])}
{var_line('A股 · 包含当年新股（新股涨幅按发行价计）', cn['with_ipo'])}
{var_line('A股 · 理想化：必能成交、零成本', cn['ideal'])}
{var_line('A股 · 前 5 名等权', cn['top5'])}
{var_line('A股 · 前 10 名等权', cn['top10'])}

### 「包含当年新股」口径下的 A 股冠军

| 投资年度 | 冠军 | 上一年涨幅（发行价起算） | 当年净收益 |
|---|---|---|---|
""" + '\n'.join(f"| {r['year']} | {r['picks'][0]['name']}（{r['picks'][0]['sym'][2:]}） | {pct(r['picks'][0]['prev'])} | {pct(r['net'])} |" for r in cn['with_ipo']) + """

### 美股「年初成分股」口径下的冠军

| 投资年度 | 冠军 | 上一年涨幅 | 当年净收益 |
|---|---|---|---|
""" + '\n'.join(f"| {r['year']} | {r['picks'][0]['sym']} | {pct(r['picks'][0]['prev'])} | {pct(r['net'])} |" for r in us['start_members']) + '\n'
open(os.path.join(HERE, 'RESULTS.md'), 'w').write(md)
print('wrote results.csv, RESULTS.md')
