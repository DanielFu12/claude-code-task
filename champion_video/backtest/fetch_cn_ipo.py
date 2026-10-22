"""下载 A 股发行上市信息（东方财富数据中心 RPTA_APP_IPOAPPLY）：代码、简称、发行价、上市日期。
用于：①核对股票池完整性 ②「含新股」对照口径中，以发行价计算新股当年涨幅。"""
import json, os, sys, requests
out = sys.argv[1]
rows, page = [], 1
while True:
    r = requests.get('https://datacenter-web.eastmoney.com/api/data/v1/get', params=dict(
        reportName='RPTA_APP_IPOAPPLY', columns='SECURITY_CODE,SECURITY_NAME,ISSUE_PRICE,LISTING_DATE,TRADE_MARKET,MARKET_TYPE_NEW',
        pageSize=500, pageNumber=page, sortColumns='SECURITY_CODE', sortTypes=1), timeout=30).json()
    rows += r['result']['data']
    if page >= r['result']['pages']:
        break
    page += 1
json.dump(rows, open(out, 'w'), ensure_ascii=False)
print(len(rows))
