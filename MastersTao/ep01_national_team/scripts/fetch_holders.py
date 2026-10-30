#!/usr/bin/env python3
"""下载 A 股全市场「前十大股东」与「前十大流通股东」原始名单（2022Q1—2026Q3）。

数据源：东方财富数据中心公开接口 datacenter-web.eastmoney.com
  - RPT_F10_EH_HOLDERS      前十大股东（定期报告披露口径）
  - RPT_F10_EH_FREEHOLDERS  前十大流通股东（定期报告披露口径）

每个报告期、每张表全量下载后存为 data/raw/<表>_<报告期>.csv.gz，
后续统计（build_dataset.py）只读这些本地文件，保证结果可复现。

用法：python3 fetch_holders.py [--force] [YYYY-MM-DD ...]
"""
import csv, gzip, json, os, sys, time, urllib.parse, urllib.request

API = "https://datacenter-web.eastmoney.com/api/data/v1/get"
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")

TABLES = {
    # 表名: (列, 单页上限)
    "RPT_F10_EH_HOLDERS": ("SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,END_DATE,HOLDER_RANK,"
                           "HOLDER_NAME,HOLDER_CODE,HOLD_NUM,HOLD_NUM_RATIO,HOLD_NUM_CHANGE,SHARES_TYPE", 5000),
    "RPT_F10_EH_FREEHOLDERS": ("SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,END_DATE,HOLDER_RANK,"
                               "HOLDER_NAME,HOLDER_CODE,HOLD_NUM,FREE_HOLDNUM_RATIO,HOLD_NUM_CHANGE", 2500),
}


def quarters():
    out = []
    for y in range(2022, 2027):
        for md in ("03-31", "06-30", "09-30", "12-31"):
            d = f"{y}-{md}"
            if d <= "2026-09-30":
                out.append(d)
    return out


def get(params, tries=6):
    url = API + "?" + urllib.parse.urlencode(params)
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read().decode("utf-8"))
            if d.get("success") or d.get("result") is None and d.get("code") == 9201:
                return d
            raise RuntimeError(d.get("message"))
        except Exception as e:  # 网络抖动：指数退避重试
            if k == tries - 1:
                raise
            time.sleep(2 ** k)


def fetch(table, date, force=False):
    cols, ps = TABLES[table]
    path = os.path.join(RAW, f"{table}_{date}.csv.gz")
    if os.path.exists(path) and not force:
        return path
    rows, page = [], 1
    while True:
        d = get({"reportName": table, "columns": cols, "pageSize": ps, "pageNumber": page,
                 "sortColumns": "SECUCODE,HOLDER_RANK", "sortTypes": "1,1",
                 "filter": f"(END_DATE='{date}')"})
        res = d.get("result") or {}
        data = res.get("data") or []
        rows += data
        pages = res.get("pages") or 0
        if page >= pages:
            break
        page += 1
        time.sleep(0.3)
    expect = (res.get("count") or len(rows))
    assert len(rows) == expect, (table, date, len(rows), expect)
    names = cols.split(",")
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(names)
        for r in rows:
            w.writerow([r.get(c) for c in names])
    os.replace(tmp, path)
    print(f"{table} {date}: {len(rows)} rows, {pages} pages", flush=True)
    return path


if __name__ == "__main__":
    os.makedirs(RAW, exist_ok=True)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    for date in (args or quarters()):
        for t in TABLES:
            fetch(t, date, force)
    with open(os.path.join(RAW, "FETCH_LOG.txt"), "a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S %z") + f" fetched {args or 'all'} force={force}\n")
