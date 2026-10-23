"""冠军公司的年度归母净利润：美股取 SEC EDGAR XBRL（NetIncomeLoss，10-K 财年），A 股取东方财富年报（RPT_LICO_FN_CPD）。
输出 cache/profits.json：{市场: {代码: {财年: 净利润}}}。美股财年按「财年结束日所在自然年 − (结束月 ≤ 2 ? 1 : 0)」归入自然年
（英伟达财年 1 月结束，FY2018 ≈ 2017 自然年）。"""
import json, os, time, requests
from datetime import date
from common import CACHE
UA = {'User-Agent': 'champion-backtest research contact@example.com'}
US_CIK = {'NFLX': 1065280, 'NVDA': 1045810, 'NRG': 1013871, 'AMD': 2488, 'TSLA': 1318605, 'DVN': 1090012, 'OXY': 797468,
          'PLTR': 1321655}


def us(sym):
    j = requests.get(f'https://data.sec.gov/api/xbrl/companyconcept/CIK{US_CIK[sym]:010d}/us-gaap/NetIncomeLoss.json',
                     headers=UA, timeout=60).json()
    out = {}
    for x in j['units']['USD']:
        if x.get('form') != '10-K' or x.get('fp') != 'FY' or 'start' not in x: continue
        s, e = x['start'], x['end']
        days = (date.fromisoformat(e) - date.fromisoformat(s)).days
        if not 340 < days < 380: continue
        y = int(e[:4]) - (1 if int(e[5:7]) <= 2 else 0)
        out[y] = x['val']                         # 后提交的 10-K 覆盖先前数值（含重述）
    time.sleep(0.2)
    return out


def cn(code):
    d = requests.get('https://datacenter-web.eastmoney.com/api/data/v1/get', params=dict(
        reportName='RPT_LICO_FN_CPD', columns='SECURITY_CODE,REPORTDATE,PARENT_NETPROFIT', pageSize=200,
        filter=f'(SECURITY_CODE="{code}")', sortColumns='REPORTDATE', sortTypes=-1), timeout=30).json()
    return {int(x['REPORTDATE'][:4]): x['PARENT_NETPROFIT'] for x in (d['result'] or {}).get('data', [])
            if x['REPORTDATE'][5:10] == '12-31'}


if __name__ == '__main__':
    HERE = os.path.dirname(os.path.abspath(__file__))
    u = json.load(open(os.path.join(HERE, 'out_us.json'))); c = json.load(open(os.path.join(HERE, 'out_cn300.json')))
    res = {'us': {}, 'cn': {}}
    for s in sorted({r['picks'][0]['sym'] for r in u['main']}):
        res['us'][s] = us(s); print(s, {k: round(v / 1e6) for k, v in sorted(res['us'][s].items()) if 2013 <= k <= 2025})
    for s in sorted({r['picks'][0]['sym'][2:] for r in c['main']}):
        res['cn'][s] = cn(s); print(s, {k: round(v / 1e8, 2) for k, v in sorted(res['cn'][s].items()) if 2013 <= k <= 2025})
    json.dump(res, open(os.path.join(CACHE, 'profits.json'), 'w'), indent=1)
