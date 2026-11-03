#!/usr/bin/env python3
"""独立复核：用 EP01 另行全量下载的十大股东 / 十大流通股东原始名单（ep01_national_team/data/raw），
重算中央汇金资管（10506881）每季出现的公司与退出名单，与本期按股东代码下载的数据逐项比对；
再核对画面里出现的每一个数字。结果写入 data/VERIFICATION.md，任何一项不符即退出码 1。"""
import csv, gzip, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "data")
RAW1 = os.path.join(HERE, "..", "..", "ep01_national_team", "data", "raw")
Q = [f"{y}-{md}" for y in range(2022, 2027) for md in ("03-31", "06-30", "09-30", "12-31") if f"{y}-{md}" <= "2026-09-30"]
L = {q: f"{q[:4]}Q{(int(q[5:7]) - 1) // 3 + 1}" for q in Q}
lines, bad = [], []


def check(name, got, want):
    ok = got == want
    lines.append(f"| {'✅' if ok else '❌'} | {name} | {got} | {want} |")
    if not ok: bad.append(name)


ind = {}
for q in Q:
    s = set()
    for t in ("RPT_F10_EH_HOLDERS", "RPT_F10_EH_FREEHOLDERS"):
        with gzip.open(os.path.join(RAW1, f"{t}_{q}.csv.gz"), "rt", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if (r["HOLDER_CODE"] == "10506881" and r["SECUCODE"][-3:] in (".SH", ".SZ", ".BJ")
                        and not r["SECURITY_CODE"].startswith(("900", "200"))):      # 剔除 B 股
                    s.add(r["SECUCODE"])
    ind[L[q]] = s
J = json.load(open(os.path.join(D, "hjam.json"), encoding="utf-8"))
ex = list(csv.DictReader(open(os.path.join(D, "hjam_exits.csv"), encoding="utf-8-sig")))

lines += ["## 1. 独立重算（EP01 全量名单）vs 本期数据", "", "| | 项目 | 独立重算 | 本期 |", "|---|---|---|---|"]
for i, q in enumerate(Q):
    k = L[q]
    check(f"{k} 家数", len(ind[k]), J["count"][i])
    if i:
        p = L[Q[i - 1]]
        check(f"{k} 退出名单（公司集合）", sorted(ind[p] - ind[k]), sorted(e["secucode"] for e in ex if e["quarter"] == k))
for k in J["quarters"][1:]:
    caps = [float(e["cap_prev_qend_yi"]) for e in ex if e["quarter"] == k]
    check(f"{k} 退出榜按市值降序", caps == sorted(caps, reverse=True), True)

st = {s["quarter"]: s for s in J["steps"]}
lines += ["", "## 2. 画面数字核对", "", "| | 画面文字 | 数据 | 画面 |", "|---|---|---|---|"]
check("钩子：2026Q2 一次退出 122 家", st["2026Q2"]["n_exit"], 122)
check("钩子：139 → 17（−122）", (J["count"][-3], J["count"][-2]), (139, 17))
check("钩子：退出最大一笔 贵州茅台 150.8 亿", (st["2026Q2"]["exits"][0]["name"], round(st["2026Q2"]["exits"][0]["cap"], 1)),
      ("贵州茅台", 150.8))
check("2026Q2 新进 0 家", st["2026Q2"]["n_new"], 0)
check("总结：累计退出 153 次 / 145 家", (J["total_exits"], J["unique_exit_companies"]), (153, 145))
check("总结：退出市值合计 1,129 亿", round(J["total_exit_cap_yi"]), 1129)
check("总结：2026Q2 一季 876 亿，占 78%", (round(st["2026Q2"]["exit_cap_yi"]),
      round(st["2026Q2"]["exit_cap_yi"] / J["total_exit_cap_yi"] * 100)), (876, 78))
check("总结：留下 17 家，持股市值 864 亿", (J["count"][-1], round(J["cap"][-1])), (17, 864))
check("2026Q3 与上季同一批公司", ind["2026Q3"] == ind["2026Q2"], True)
check("中国重工退出标注为吸收合并退市", [e["note"] for e in ex if e["secucode"] == "601989.SH"],
      ["被中国船舶换股吸收合并，2025-09-05 终止上市"])

with open(os.path.join(D, "VERIFICATION.md"), "w", encoding="utf-8") as f:
    f.write("# 数据复核报告（自动生成）\n\n结果：" + ("全部通过" if not bad else "不符：" + "、".join(bad)) + "\n\n" + "\n".join(lines) + "\n")
print("verify:", "OK" if not bad else f"FAILED {bad}")
sys.exit(1 if bad else 0)
