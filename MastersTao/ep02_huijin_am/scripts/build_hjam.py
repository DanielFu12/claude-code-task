#!/usr/bin/env python3
"""中央汇金资产管理有限责任公司：每季出现在 A 股前十大股东 / 前十大流通股东中的公司数，
以及每季「退出名单」的公司按持股市值排序（取上一季末——即最后一次披露时的持股市值）。

规则：同一公司两张表都在只计 1 次；持股市值取两张表中较大的一个（前十大股东口径含限售股）。
输出：data/hjam_quarterly.csv、data/hjam_exits.csv、data/hjam_entries.csv、data/hjam.json
"""
import csv, json, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "data")
Q = [f"{y}-{md}" for y in range(2022, 2027) for md in ("03-31", "06-30", "09-30", "12-31") if f"{y}-{md}" <= "2026-09-30"]
L = {q: f"{q[:4]}Q{(int(q[5:7]) - 1) // 3 + 1}" for q in Q}

hold = defaultdict(dict)     # quarter -> secucode -> {name, cap, num}
for t in ("RPT_F10_EH_HOLDERS", "RPT_F10_EH_FREEHOLDERS"):
    with open(os.path.join(D, "raw", f"hjam_{t}.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            sc = r["SECUCODE"]
            if sc[-3:] not in (".SH", ".SZ", ".BJ") or r["SECURITY_CODE"].startswith(("900", "200")):
                continue
            q = r["END_DATE"][:10]
            if q not in L: continue
            cap = float(r["HOLDER_MARKET_CAP"] or 0); num = float(r["HOLD_NUM"] or 0)
            cur = hold[L[q]].get(sc)
            if cur is None or cap > cur["cap"]:
                hold[L[q]][sc] = {"name": r["SECURITY_NAME_ABBR"], "cap": cap, "num": num}

# 退出原因核实：公司本身不再存在（终止上市 / 吸收合并）的，单独标注，不当作「退出」解读
NOTES = {"601989.SH": "被中国船舶换股吸收合并，2025-09-05 终止上市"}

rows, exits, entries, out = [], [], [], {"quarters": [], "count": [], "cap": [], "steps": []}
prev = None
for q in Q:
    k = L[q]; cur = hold[k]
    total_cap = sum(v["cap"] for v in cur.values())
    r = {"quarter": k, "count": len(cur), "total_cap_yi": round(total_cap / 1e8, 1),
         "qoq": "", "n_exit": "", "n_new": "", "exit_cap_yi": ""}
    step = {"quarter": k, "count": len(cur), "exits": [], "n_exit": 0, "n_new": 0, "exit_cap_yi": 0}
    if prev:
        P = hold[prev]
        gone = sorted(set(P) - set(cur), key=lambda c: -P[c]["cap"])
        new = sorted(set(cur) - set(P), key=lambda c: -cur[c]["cap"])
        r.update({"qoq": len(cur) - len(P), "n_exit": len(gone), "n_new": len(new),
                  "exit_cap_yi": round(sum(P[c]["cap"] for c in gone) / 1e8, 1)})
        for rank, c in enumerate(gone, 1):
            exits.append({"quarter": k, "rank": rank, "secucode": c, "name": P[c]["name"],
                          "cap_prev_qend_yi": round(P[c]["cap"] / 1e8, 2), "shares_prev_qend": int(P[c]["num"]),
                          "note": NOTES.get(c, "")})
        for c in new:
            entries.append({"quarter": k, "secucode": c, "name": cur[c]["name"], "cap_yi": round(cur[c]["cap"] / 1e8, 2)})
        step.update({"n_exit": len(gone), "n_new": len(new), "exit_cap_yi": r["exit_cap_yi"],
                     "exits": [{"name": P[c]["name"], "cap": round(P[c]["cap"] / 1e8, 2), "note": NOTES.get(c, "")}
                               for c in gone[:10]]})
    rows.append(r); out["steps"].append(step)
    out["quarters"].append(k); out["count"].append(len(cur)); out["cap"].append(round(total_cap / 1e8, 1))
    prev = k

def wcsv(name, data):
    with open(os.path.join(D, name), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0].keys()) if data else ["quarter"]); w.writeheader(); w.writerows(data)
wcsv("hjam_quarterly.csv", rows); wcsv("hjam_exits.csv", exits); wcsv("hjam_entries.csv", entries)
allx = [e for e in exits]
out["total_exits"] = len(allx)
out["unique_exit_companies"] = len({e["secucode"] for e in allx})
out["total_exit_cap_yi"] = round(sum(e["cap_prev_qend_yi"] for e in allx), 1)
json.dump(out, open(os.path.join(D, "hjam.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in rows: print(r)
