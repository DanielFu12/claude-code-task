#!/usr/bin/env python3
"""下载中央汇金资产管理有限责任公司（东方财富股东代码 10506881）在全部 A 股公司
前十大股东 / 前十大流通股东中的逐条记录（含季末持股数量与持股市值），2022Q1—2026Q3。

数据源：东方财富数据中心 RPT_F10_EH_HOLDERS / RPT_F10_EH_FREEHOLDERS（整理自上市公司定期报告）。
输出：data/raw/hjam_<表>.csv
"""
import csv, json, os, time, urllib.parse, urllib.request

API = "https://datacenter-web.eastmoney.com/api/data/v1/get"
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")
CODE = "10506881"
COLS = "SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,END_DATE,HOLDER_NAME,HOLDER_CODE,HOLDER_RANK,HOLD_NUM,HOLDER_MARKET_CAP"


def get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    for k in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if k == 5: raise
            time.sleep(2 ** k)


os.makedirs(RAW, exist_ok=True)
for table in ("RPT_F10_EH_HOLDERS", "RPT_F10_EH_FREEHOLDERS"):
    rows, page = [], 1
    while True:
        d = get({"reportName": table, "columns": COLS, "pageSize": 500, "pageNumber": page,
                 "sortColumns": "END_DATE,SECUCODE", "sortTypes": "1,1",
                 "filter": f'(HOLDER_CODE="{CODE}")(END_DATE>=\'2022-03-31\')(END_DATE<=\'2026-09-30\')'})
        res = d.get("result") or {}
        rows += res.get("data") or []
        if page >= (res.get("pages") or 0): break
        page += 1
    path = os.path.join(RAW, f"hjam_{table}.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); names = COLS.split(","); w.writerow(names)
        for r in rows: w.writerow([r.get(c) for c in names])
    print(table, len(rows), "rows ->", path, "| total", res.get("count"))
