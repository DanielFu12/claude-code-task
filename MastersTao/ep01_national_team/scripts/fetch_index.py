#!/usr/bin/env python3
"""下载上证指数、沪深300 日线（新浪财经公开接口），存 data/raw/idx_<代码>.json，
并生成 data/index_quarter_end.csv（每季度最后一个交易日收盘价），仅用作市场背景。"""
import json, os, urllib.request
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")
URL = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={}&scale=240&ma=no&datalen=1300"

out = {}
for sym, name in (("sh000001", "上证指数"), ("sh000300", "沪深300")):
    path = os.path.join(RAW, f"idx_{sym}.json")
    if not os.path.exists(path):
        with urllib.request.urlopen(urllib.request.Request(URL.format(sym), headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
            open(path, "wb").write(r.read())
    d = pd.DataFrame(json.load(open(path)))
    d["day"] = pd.to_datetime(d.day); d["close"] = d.close.astype(float)
    d = d[(d.day >= "2022-01-01") & (d.day <= "2026-09-30")]
    q = d.groupby(d.day.dt.to_period("Q")).last()
    out[name] = q.close.round(2)
    out[name + "_日期"] = q.day.dt.strftime("%Y-%m-%d")
df = pd.DataFrame(out)
df.index = [f"{p.year}Q{p.quarter}" for p in df.index]
df.index.name = "quarter"
df.to_csv(os.path.join(HERE, "..", "data", "index_quarter_end.csv"), encoding="utf-8-sig")
print(df.to_string())
