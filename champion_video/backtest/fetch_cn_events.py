"""下载 A 股分红送转实施记录（东方财富数据中心 RPT_SHAREBONUS_DET），2014-12 至 2026-01 除权除息日。
字段：BONUS_IT_RATIO = 每 10 股送股+转增股数，PRETAX_BONUS_RMB = 每 10 股派现（税前，元）。"""
import json, sys, time, requests
out = sys.argv[1]
rows, page = [], 1
while True:
    for k in range(5):
        try:
            r = requests.get('https://datacenter-web.eastmoney.com/api/data/v1/get', params=dict(
                reportName='RPT_SHAREBONUS_DET',
                columns='SECURITY_CODE,SECURITY_NAME_ABBR,EX_DIVIDEND_DATE,EQUITY_RECORD_DATE,BONUS_IT_RATIO,BONUS_RATIO,IT_RATIO,PRETAX_BONUS_RMB,IMPL_PLAN_PROFILE,ASSIGN_PROGRESS',
                pageSize=500, pageNumber=page, sortColumns='EX_DIVIDEND_DATE,SECURITY_CODE', sortTypes='1,1',
                filter="(EX_DIVIDEND_DATE>='2014-12-01')(EX_DIVIDEND_DATE<='2026-01-31')"), timeout=30).json()
            break
        except Exception as e:
            print('retry', page, e); time.sleep(3)
    rows += r['result']['data']
    if page >= r['result']['pages']:
        break
    page += 1
json.dump(rows, open(out, 'w'), ensure_ascii=False)
print(len(rows), rows[0], rows[-1])
