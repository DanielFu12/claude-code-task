#!/usr/bin/env python3
"""独立复核：不用 pandas、不复用 build_dataset 的代码，直接从原始 csv 重算一遍，
并核对视频画面里写死的每一个数字。结果写入 data/VERIFICATION.md，任何一项不符即退出码 1。"""
import csv, gzip, json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "data")
RAW = os.path.join(D, "raw")
Q = [f"{y}-{md}" for y in range(2022, 2027) for md in ("03-31", "06-30", "09-30", "12-31") if f"{y}-{md}" <= "2026-09-30"]
L = {q: f"{q[:4]}Q{(int(q[5:7]) - 1) // 3 + 1}" for q in Q}
HJ = {"10061230", "10506881", "70415366", "70415393"}
ZJ = {"10196008"} | {str(c) for c in range(70405814, 70405824)}
ZJ_PLAN = {str(c) for c in range(70405814, 70405824)}

lines, bad = [], []


def check(name, got, want):
    ok = got == want
    lines.append(f"| {'✅' if ok else '❌'} | {name} | {got} | {want} |")
    if not ok:
        bad.append(name)


sets = {}
uni = {}
names_by_code = defaultdict(set)
rows_n = {}
for q in Q:
    s = defaultdict(set)
    u = set()
    for t in ("RPT_F10_EH_HOLDERS", "RPT_F10_EH_FREEHOLDERS"):
        with gzip.open(os.path.join(RAW, f"{t}_{q}.csv.gz"), "rt", encoding="utf-8") as f:
            rd = csv.DictReader(f)
            n = 0
            for r in rd:
                n += 1
                sc, code = r["SECUCODE"], r["SECURITY_CODE"]
                if sc[-3:] not in (".SH", ".SZ", ".BJ") or code.startswith(("900", "200")):
                    continue
                u.add(sc)
                hc = r["HOLDER_CODE"]
                if "转融通" in r["HOLDER_NAME"]:
                    continue
                if hc in HJ:
                    s["hj"].add(sc); names_by_code[hc].add(r["HOLDER_NAME"])
                if hc in ZJ:
                    s["zj"].add(sc); names_by_code[hc].add(r["HOLDER_NAME"])
                if hc in ZJ_PLAN:
                    s["zjplan"].add(sc)
                if hc == "10196008":
                    s["zjself"].add(sc)
                if hc == "10506881":
                    s["hjam"].add(sc)
                if hc == "10061230":
                    s["hjinv"].add(sc)
            rows_n[(t, q)] = n
    sets[L[q]] = s
    uni[L[q]] = u

# 1) 与 build_dataset 输出逐季比对
with open(os.path.join(D, "quarterly_counts.csv"), encoding="utf-8-sig") as f:
    qc = {r["quarter"]: r for r in csv.DictReader(f)}
lines += ["## 1. 独立重算 vs 统计表", "", "| | 项目 | 独立重算 | 统计表 |", "|---|---|---|---|"]
for q in Q:
    k = L[q]; s = sets[k]
    check(f"{k} 汇金系", len(s["hj"]), int(qc[k]["huijin"]))
    check(f"{k} 证金系", len(s["zj"]), int(qc[k]["zhengjin"]))
    check(f"{k} 合并去重", len(s["hj"] | s["zj"]), int(qc[k]["union"]))
    check(f"{k} 合并 = 汇金 + 证金 − 交集", len(s["hj"]) + len(s["zj"]) - len(s["hj"] & s["zj"]), int(qc[k]["union"]))
for a, b_ in zip(Q, Q[1:]):
    ka, kb = L[a], L[b_]
    check(f"{kb} 合并环比", len(sets[kb]["hj"] | sets[kb]["zj"]) - len(sets[ka]["hj"] | sets[ka]["zj"]), int(float(qc[kb]["union_qoq"])))

# 2) 原始数据完整性
lines += ["", "## 2. 原始文件完整性（19 季 × 2 表）", "", "| | 项目 | 值 | 期望 |", "|---|---|---|---|"]
check("原始文件数", len(rows_n), 38)
check("每张表行数均 > 40000", all(v > 40000 for v in rows_n.values()), True)
check("19 个季度全部有数据（无缺季）", all(len(uni[L[q]]) > 4000 for q in Q), True)

# 3) 新闻 / 公告抽查
P = {}
with gzip.open(os.path.join(D, "company_panel.csv.gz"), "rt", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        P.setdefault((r["quarter"], r["secucode"]), set()).add(r["entity"])
lines += ["", "## 3. 与公开报道抽查（21 财经 2026-08-16、界面新闻：汇金、证金退出贵州茅台等前十大股东）", "",
          "| | 项目 | 数据 | 报道 |", "|---|---|---|---|"]
for code, nm, q1, q2 in [("600519.SH", "贵州茅台", {"汇金资管", "证金公司"}, set()),
                         ("600674.SH", "川投能源", {"汇金资管", "证金公司"}, set()),
                         ("000001.SZ", "平安银行", {"证金公司"}, set()),
                         ("002236.SZ", "大华股份", {"证金公司"}, set()),
                         ("600633.SH", "浙数文化", {"汇金资管"}, set()),
                         ("600663.SH", "陆家嘴", {"汇金资管"}, set())]:
    check(f"{nm} 2026Q1 → 2026Q2", (sorted(P.get(("2026Q1", code), set())), sorted(P.get(("2026Q2", code), set()))),
          (sorted(q1), sorted(q2)))

# 4) 视频中出现的每个数字（本期主线：中央汇金资管 10506881 vs 中国证金自有账户 10196008）
S = json.load(open(os.path.join(D, "stats.json"), encoding="utf-8"))
idx = {}
with open(os.path.join(D, "index_quarter_end.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        idx[r["quarter"]] = float(r["上证指数"])
A = lambda k: len(sets[k]["hjam"]); B = lambda k: len(sets[k]["zjself"])
AB = lambda k: sets[k]["hjam"] | sets[k]["zjself"]
with open(os.path.join(D, "duo_counts.csv"), encoding="utf-8-sig") as f:
    duo = {r["quarter"]: r for r in csv.DictReader(f)}
lines += ["", "## 4. 主体对比：独立重算 vs duo_counts.csv", "", "| | 项目 | 独立重算 | 统计表 |", "|---|---|---|---|"]
for q in Q:
    k = L[q]
    check(f"{k} 汇金资管 / 证金 / 合并", (A(k), B(k), len(AB(k))),
          (int(duo[k]["huijin_am"]), int(duo[k]["csf"]), int(duo[k]["union"])))
check("stats.json 与独立重算一致", (S["duo"]["huijin_am"], S["duo"]["csf"], S["duo"]["union"]),
      ([A(L[q]) for q in Q], [B(L[q]) for q in Q], [len(AB(L[q])) for q in Q]))
lines += ["", "## 5. 画面数字核对", "", "| | 画面文字 | 数据 | 画面 |", "|---|---|---|---|"]
check("钩子：A 股公司数（2026Q3 已有名单）", len(uni["2026Q3"]), S["universe"][-1])
check("钩子 / 标题：2022Q1 两家合并 259", len(AB("2022Q1")), 259)
check("钩子 / 标题：2026Q3 只剩 32", len(AB("2026Q3")), 32)
check("对决起点 2022Q1：155 · 157", (A("2022Q1"), B("2022Q1")), (155, 157))
check("2023Q2 中国证金单季 −19", B("2023Q2") - B("2023Q1"), -19)
check("2026Q1 中国证金 111 → 76（−35）", (B("2025Q4"), B("2026Q1")), (111, 76))
check("2026Q1 汇金资管 140 → 139", (A("2025Q4"), A("2026Q1")), (140, 139))
check("2026Q2 汇金资管 139 → 17（−122）", (A("2026Q1"), A("2026Q2")), (139, 17))
check("2026Q2 中国证金 76 → 23（−53）", (B("2026Q1"), B("2026Q2")), (76, 23))
check("2026Q2 合并 188 → 32（趋势图标注 −156）", (len(AB("2026Q1")), len(AB("2026Q2"))), (188, 32))
for code, nm in (("600519.SH", "贵州茅台"), ("000002.SZ", "万科A"), ("000001.SZ", "平安银行")):
    check(f"2026Q2 退出名单：{nm}（Q1 在、Q2 不在）", (code in AB("2026Q1"), code in AB("2026Q2")), (True, False))
check("2026Q2 上证季末 4094 为 19 季最高", (round(idx["2026Q2"]), max(idx.values()) == idx["2026Q2"]), (4094, True))
check("2026Q3：17 · 23，与上季持平（同一批公司）", (A("2026Q3"), B("2026Q3"), AB("2026Q3") == AB("2026Q2")), (17, 23, True))
cov = len(uni["2026Q3"] & uni["2026Q2"]) / len(uni["2026Q2"]) * 100
check("2026Q3 已披露比例（画面保留 1 位小数）", round(cov, 1), round(S["universe_like"][-1], 1))
check("2026Q2 汇金系 / 证金系名单内公司在 2026Q3 全部已披露",
      len((sets["2026Q2"]["hj"] | sets["2026Q2"]["zj"]) - uni["2026Q3"]), 0)
check("2026Q2 两家名单内公司在 2026Q3 全部已披露", len(AB("2026Q2") - uni["2026Q3"]), 0)
check("今年以来 汇金资管 140 → 17，−88%", (A("2025Q4"), A("2026Q3"), round((A("2026Q3") - A("2025Q4")) / A("2025Q4") * 100)), (140, 17, -88))
check("今年以来 中国证金 111 → 23，−79%", (B("2025Q4"), B("2026Q3"), round((B("2026Q3") - B("2025Q4")) / B("2025Q4") * 100)), (111, 23, -79))
u0, u1 = len(AB("2025Q4")), len(AB("2026Q3"))
check("今年以来 两家合计 212 → 32，−85%", (u0, u1, round((u1 - u0) / u0 * 100)), (212, 32, -85))
check("科普：汇金投资本体每季均为 8 家", sorted({len(sets[L[q]]["hjinv"]) for q in Q}), [8])
check("科普：汇金资管委托计划 2 个（股东代码）", len({"70415366", "70415393"}), 2)
check("科普：中证金融资产管理计划 10 个（股东代码）", len(ZJ_PLAN), 10)
ever = set().union(*[AB(L[q]) for q in Q]); always = set.intersection(*[AB(L[q]) for q in Q])
check("全景：19 季里出现过 265 家", len(ever), 265)
check("全景：从未离开 32 家，且正是 2026Q3 的 32 家", (len(always), always == AB("2026Q3")), (32, True))

# 5) 主体名称变体
lines += ["", "## 6. 纳入统计的主体与其在原始数据中出现过的全部名称", ""]
for c in sorted(names_by_code):
    lines.append(f"- `{c}`：" + "；".join(sorted(names_by_code[c])))

missing = sorted(uni["2026Q2"] - uni["2026Q3"])
lines += ["", "## 7. 2026Q3 尚未取得名单的公司（相对 2026Q2）", "",
          f"共 {len(missing)} 家：" + "、".join(missing), "",
          "这些公司 2026Q2 均不在汇金系 / 证金系名单中，因此不影响 2026Q3 的统计（主体口径同理）；若其三季报后续披露并出现汇金或证金，"
          "重新运行 `./build.sh --refetch` 即可更新。"]

head = ["# 数据复核报告（自动生成）", "", f"结果：{'全部通过' if not bad else '有 ' + str(len(bad)) + ' 项不符：' + '、'.join(bad)}", ""]
with open(os.path.join(D, "VERIFICATION.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(head + lines) + "\n")
print("verify:", "OK" if not bad else f"FAILED {bad}")
sys.exit(1 if bad else 0)
