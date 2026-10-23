"""沪深 300 版回测结果导出：results_hs300.csv（逐年明细）+ RESULTS_hs300.md（汇总、口径对照、归因证据）。"""
import csv, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
us = json.load(open(os.path.join(HERE, 'out_us.json')))
cn = json.load(open(os.path.join(HERE, 'out_cn300.json')))
E = json.load(open(os.path.join(HERE, 'evidence300.json')))
US_CN = {'NFLX': '奈飞', 'NVDA': '英伟达', 'NRG': 'NRG能源', 'AMD': '超威半导体', 'TSLA': '特斯拉', 'DVN': '德文能源', 'OXY': '西方石油', 'PLTR': 'Palantir'}
CN_AT = {'300072': '三聚环保（今海新能科）', '601012': '隆基股份（今隆基绿能）', '601888': '中国国旅（今中国中免）', '603501': '韦尔股份（今豪威集团）'}
pct = lambda x, nd=1: f'{x * 100:+,.{nd}f}%'
cagr = lambda m: m ** 0.1 - 1

rows = []
for mk, res, bench, uni, cur in [('美股', us['main'], us['bench'], '标普500 当年年末成分股', '$'), ('A股', cn['main'], cn['bench'], '沪深300 当年年末成分股', '¥')]:
    for r, b in zip(res, bench):
        p = r['picks'][0]
        code = p['sym'] if mk == '美股' else p['sym'][2:]
        name = US_CN.get(code, p['name']) if mk == '美股' else CN_AT.get(code, p['name'])
        rows.append({'市场': mk, '投资年度': r['year'], '选股年度': r['year'] - 1, '股票池': uni, '股票池数量': r['universe_n'],
                     '冠军代码': code, '冠军名称': name, '选股年涨幅(总回报)': pct(p['prev']), '买入日期': p['buy_date'],
                     '买入价(当时实际成交价)': f"{cur}{p['buy_price']}", '卖出日期': p['sell_date'], '卖出价(当时实际成交价)': f"{cur}{p['sell_price']}",
                     '持有年度总回报(未扣成本)': pct(p['gross']), '持有年度净收益(扣成本)': pct(r['net']), '期末资金(本金10万)': f"{r['capital'] * 10:,.2f}万",
                     '累计收益': pct(r['capital'] - 1), '同期指数': pct(b['ret']), '指数累计': pct(b['capital'] - 1), '年内最大回撤': pct(p['max_dd']),
                     '备注': '；'.join(p.get('notes', []) + p.get('events', [])[:2])})
with open(os.path.join(HERE, 'results_hs300.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)


def table(mk):
    out = ['| 投资年度 | 冠军（代码） | 上一年涨幅 | 买入 | 卖出 | 当年净收益 | 期末资金 | 同期指数 |', '|---|---|---|---|---|---|---|---|']
    for r in rows:
        if r['市场'] == mk:
            out.append(f"| {r['投资年度']} | {r['冠军名称']}（{r['冠军代码']}） | {r['选股年涨幅(总回报)']} | {r['买入日期']} {r['买入价(当时实际成交价)']} | "
                       f"{r['卖出日期']} {r['卖出价(当时实际成交价)']} | {r['持有年度净收益(扣成本)']} | {r['期末资金(本金10万)']} | {r['同期指数']} |")
    return '\n'.join(out)


def vl(name, res):
    c = res[-1]['capital']; return f'| {name} | {pct(c - 1)} | {pct(cagr(c))} | {c * 10:,.2f} 万 |'


ny = E['next_year']
prof = '\n'.join(f"| {'美股' if p['mk'] == 'us' else 'A股'} | {p['year']} | {US_CN.get(p['sym'], CN_AT.get(p['sym'], p['name']))} | "
                 f"{'扭亏为盈' if p['turn'] else ('—' if p['growth'] is None else pct(p['growth'], 0))} | {pct(p['ret'])} |" for p in E['profit'])
md = f"""# 十年回测结果 · 沪深 300 版（2016—2025 投资年度）

> A 股股票池换成「选股年年末的沪深 300 成分股」，与美股「选股年年末的标普 500 成分股」对称，剔除次新股与小盘题材股的影响。
> 由 `cn300.py`（A 股）、`us.py`（美股）、`evidence300.py`（归因证据）生成，`export_tables300.py` 导出；逐年完整字段见 `results_hs300.csv`。
> 成分股历史：`data/csi300_history.txt`（qlib 社区数据集 chenditc/investment_data，2026-10-22 发布；每年年末恰好 300 只，与中证指数官网当日成分 300 只中 299 只一致）。
> 本金 10 万（本币），复利滚动，收益均为含分红再投资的总回报，「净收益」已扣交易成本。

## 汇总

| 策略 | 十年累计 | 年化（CAGR） | 10 万变成 |
|---|---|---|---|
{vl('美股：每年买入上一年标普500涨幅冠军', us['main'])}
{vl('　对照：标普500 全收益指数', us['bench'])}
{vl('A股：每年买入上一年沪深300涨幅冠军', cn['main'])}
{vl('　对照：沪深300 全收益指数（H00300）', cn['bench'])}

两个账户相差 {us['main'][-1]['capital'] / cn['main'][-1]['capital']:,.0f} 倍（全市场版为 1,332 倍）。

## 美股逐年明细

{table('美股')}

## A股逐年明细（沪深 300 成分股）

{table('A股')}

## 稳健性检验

| 口径 | 十年累计 | 年化 | 10 万变成 |
|---|---|---|---|
{vl('美股 · 年初成分股', us['start_members'])}
{vl('美股 · 前 5 名等权', us['top5'])}
{vl('美股 · 前 10 名等权', us['top10'])}
{vl('A股 · 年初成分股（排除年内新纳入）', cn['start'])}
{vl('A股 · 理想化：必能成交、零成本', cn['ideal'])}
{vl('A股 · 前 5 名等权', cn['top5'])}
{vl('A股 · 前 10 名等权', cn['top10'])}

## 归因证据

- 冠军的下一年：美股 10 年 {ny['us_beat']} 年跑赢标普500，最差一年 {pct(ny['us_worst'])}；A股 10 年 {ny['cn_beat']} 年跑赢沪深300，{ny['cn_loss_years']} 年亏损，最差一年 {pct(ny['cn_worst'])}。
- 复利的不对称：A股冠军赢的 {len(ny['cn_wins'])} 年合计 ×{ny['cn_win_mult']:.2f}，输的 {len(ny['cn_losses'])} 年合计 ×{ny['cn_lose_mult']:.3f}，十年合计 ×{cn['main'][-1]['capital']:.3f}。
- 动量（同为大盘股池）：上一年涨幅前 10 名，下一年相对股票池等权平均的超额收益（十年平均）—— 标普500 {pct(E['momentum']['us']['top10'])}，沪深300 {pct(E['momentum']['cn300']['top10'])}。

### 持有当年的利润变化 vs 股价收益（美股 SEC 10-K 归母净利润；A 股东方财富年报归母净利润）

| 市场 | 持有年度 | 冠军 | 当年净利润变化 | 当年股价收益（扣成本） |
|---|---|---|---|---|
{prof}
"""
open(os.path.join(HERE, 'RESULTS_hs300.md'), 'w').write(md)
print('wrote results_hs300.csv, RESULTS_hs300.md')
