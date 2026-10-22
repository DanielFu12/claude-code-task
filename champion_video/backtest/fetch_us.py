"""下载美股日线（Yahoo Finance chart API），含拆股/分红事件，缓存为 JSON。

用法: python3 fetch_us.py <cache_dir> <tickers.txt>
"""
import json, os, sys, time
from curl_cffi import requests

UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'}
P1, P2 = 1417392000, 1768262400  # 2014-12-01 .. 2026-01-13


# 更名后的代码（历史成分表用旧代码，Yahoo 只认新代码）。只收录同一家公司的改名，不含被收购。
ALIAS = {'FB': 'META', 'ABC': 'COR', 'ANTM': 'ELV', 'FBHS': 'FBIN', 'PKI': 'RVTY', 'RE': 'EG', 'PEAK': 'DOC',
         'HCP': 'DOC', 'NLOK': 'GEN', 'SYMC': 'GEN', 'FLT': 'CPAY', 'CDAY': 'DAY', 'WLTW': 'WTW', 'HFC': 'DINO',
         'COG': 'CTRA', 'CTL': 'LUMN', 'JEC': 'J', 'UTX': 'RTX', 'DWDP': 'DD', 'BHGE': 'BKR', 'TMK': 'GL',
         'ADS': 'BFH', 'LB': 'BBWI', 'MYL': 'VTRS', 'BK': 'BNY', 'GPS': 'GAP', 'DISCA': 'WBD', 'DISCK': 'WBD',
         'VIAC': 'PARA', 'VIAB': 'PARA', 'CBS': 'PARA', 'FI': 'FISV', 'MMC': 'MRSH', 'BLL': 'BALL', 'DISH': 'SATS',
         'INFO': 'SPGI', 'TSS': 'GPN', 'ARNC': 'HWM', 'CSRA': 'GD', 'FTR': 'FYBR', 'COL': 'RTX', 'RTN': 'RTX'}
ACQUIRED_ALIAS = {'INFO', 'TSS', 'CSRA', 'COL', 'RTN', 'FTR'}  # 这些映射是收购方，不能用来代表原公司，仅作缺失记录
_ = ACQUIRED_ALIAS


def _get(url):
    for k in range(6):
        r = requests.get(url, impersonate="chrome", timeout=30)
        if r.status_code == 429:
            time.sleep(5 * (k + 1)); continue
        return r.json()
    return {}


def fetch(sym, out):
    if os.path.exists(out):
        return 'cached'
    cands = [sym.replace('.', '-')]
    if sym in ALIAS and sym not in ACQUIRED_ALIAS:
        cands.append(ALIAS[sym])
    for ysym in cands:
        for q in (f'period1={P1}&period2={P2}', 'range=max'):   # 上市晚于 P1 的股票需用 range=max
            j = _get(f'https://query2.finance.yahoo.com/v8/finance/chart/{ysym}?{q}'
                     f'&interval=1d&events=div%2Csplits&includeAdjustedClose=true')
            if (j.get('chart') or {}).get('result'):
                j['alias'] = ysym
                json.dump(j, open(out, 'w'))
                return 'ok'
    json.dump(j, open(out, 'w'))
    return 'missing'


if __name__ == '__main__':
    cache, lst = sys.argv[1], sys.argv[2]
    os.makedirs(cache, exist_ok=True)
    syms = [s.strip() for s in open(lst) if s.strip()]
    stat = {}
    for i, s in enumerate(syms):
        st = fetch(s, os.path.join(cache, s + '.json'))
        stat[st] = stat.get(st, 0) + 1
        if st != 'cached':
            time.sleep(0.25)
        if i % 50 == 0:
            print(i, s, st, stat, flush=True)
    print(stat)
