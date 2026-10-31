#!/usr/bin/env python3
"""由原始股东名单生成 19 个季度的统计表（完全可复现，只读 data/raw）。

输出（data/）：
  entity_map.csv            所有名称中含「汇金 / 证券金融 / 中证金融 / 建银投资 / 梧桐树」的股东，逐一给出归属判定与理由
  quarterly_counts.csv      每季度：汇金系 / 证金系 / 合并去重 公司数、环比、各主体拆分、样本覆盖
  quarterly_flows.csv       每季度名单「新出现 / 消失」家数（仅描述名单变化，不等于买卖）
  company_panel.csv.gz      公司 × 季度 明细（哪家公司、哪个季度、哪个主体、出现在哪张表）
  stats.json                供视频渲染读取的精简数据

统计规则见 ../DATA_README.md。
"""
import csv, gzip, json, os, re
from collections import defaultdict
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")
OUT = os.path.join(HERE, "..", "data")

QUARTERS = [f"{y}-{md}" for y in range(2022, 2027) for md in ("03-31", "06-30", "09-30", "12-31")
            if f"{y}-{md}" <= "2026-09-30"]
QLABEL = {q: f"{q[:4]}Q{(int(q[5:7]) - 1) // 3 + 1}" for q in QUARTERS}
TABLES = {"RPT_F10_EH_HOLDERS": "十大股东", "RPT_F10_EH_FREEHOLDERS": "十大流通股东"}

# ---------------------------------------------------------------- 机构归属规则
# 判定顺序：先排除，再归类。每条规则都给出理由，写入 entity_map.csv。
EXCLUDE = [
    (r"转融通担保证券", "证金公司为券商开立的转融通担保证券账户，记载券商委托证金持有的担保品，不是证金自有持仓（沪深交易所规则：不计入证金自有证券）"),
    (r"中证金融科技", "指数基金（中证金融科技主题ETF），名称含「中证金融」但与证金无关"),
    (r"梧桐树", "梧桐树投资平台：国家外汇管理局全资，属外汇局体系，不属于汇金或证金"),
]
# 主口径以东方财富「股东代码」(HOLDER_CODE) 为准：同一主体在不同报告中可能出现简称/全称/截断名，
# 例如「大成中证金融资产管理计划」与「大成基金-农业银行-大成中证金融资产管理计划」同为 70405815。
_ZJ_PLAN = "2015 年证金公司出资、委托基金公司设立的「中证金融资产管理计划」（农业银行托管），市场俗称证金小号"
CODE_MAP = {
    "10061230": ("huijin", "汇金投资", "中央汇金投资有限责任公司本体（中投公司全资子公司）"),
    "10506881": ("huijin", "汇金资管", "中央汇金资产管理有限责任公司，汇金公司全资子公司（2015 年 11 月设立）"),
    "70415366": ("huijin", "汇金资管·委托计划", "易方达基金管理、汇金资管为唯一委托人的单一资产管理计划（名称载明委托人）"),
    "70415393": ("huijin", "汇金资管·委托计划", "华夏基金管理、汇金资管为唯一委托人的单一资产管理计划（名称载明委托人）"),
    "10196008": ("zhengjin", "证金公司", "中国证券金融股份有限公司自有账户"),
    **{str(c): ("zhengjin", "证金·资管计划", _ZJ_PLAN) for c in range(70405814, 70405824)},
    "10061231": ("huijin_ext", "建银投资",
                 "汇金公司全资子公司，持有的是原建行重组遗留股权；仅计入「扩展口径」，不计入主口径"),
}
BROAD = re.compile(r"汇金|证券金融|中证金融|建银投资|梧桐树")
SERIES_LABEL = {"huijin": "汇金系", "zhengjin": "证金系", "huijin_ext": "汇金系（扩展口径）"}


def classify(name, code):
    for pat, why in EXCLUDE:
        if re.search(pat, name):
            return "excluded", "", why
    if code in CODE_MAP:
        return CODE_MAP[code]
    return "excluded", "", "仅名称含相似字样（地方国资、私募、合伙企业、指数基金等），与中央汇金/中国证金无股权或委托关系"


def is_a_share(code, secucode):
    # 排除 B 股（沪 900xxx，深 200xxx）
    return secucode[-3:] in (".SH", ".SZ", ".BJ") and not code.startswith(("900", "200"))


def load(table, q):
    df = pd.read_csv(os.path.join(RAW, f"{table}_{q}.csv.gz"), dtype=str, keep_default_na=False)
    df = df[[is_a_share(c, s) for c, s in zip(df.SECURITY_CODE, df.SECUCODE)]]
    df["TABLE"] = TABLES[table]
    return df


def main():
    names = defaultdict(lambda: {"codes": set(), "rows": 0, "quarters": set()})  # key=(name, code)
    panel = []          # (q, secucode, name_abbr, series, entity, table, holder_name, rank, hold_num)
    universe = {}       # q -> 有任一张表数据的 A 股公司集合
    for q in QUARTERS:
        u = set()
        for t in TABLES:
            df = load(t, q)
            u |= set(df.SECUCODE)
            m = df[df.HOLDER_NAME.str.contains(BROAD) | df.HOLDER_CODE.isin(CODE_MAP)]
            for r in m.itertuples():
                n = names[(r.HOLDER_NAME, r.HOLDER_CODE)]
                n["codes"].add(r.HOLDER_CODE); n["rows"] += 1; n["quarters"].add(QLABEL[q])
                series, entity, _ = classify(r.HOLDER_NAME, r.HOLDER_CODE)
                if series != "excluded":
                    panel.append((QLABEL[q], r.SECUCODE, r.SECURITY_NAME_ABBR, series, entity,
                                  r.TABLE, r.HOLDER_NAME, r.HOLDER_RANK, r.HOLD_NUM))
        universe[q] = u

    # ---------------- entity_map.csv
    with open(os.path.join(OUT, "entity_map.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["原始股东名称", "东财股东代码", "判定", "主体", "理由", "出现行数", "出现季度数", "首次", "末次"])
        order = {"huijin": 0, "huijin_ext": 1, "zhengjin": 2, "excluded": 3}
        for (name, code), n in sorted(names.items(), key=lambda kv: (order[classify(*kv[0])[0]], -kv[1]["rows"])):
            series, entity, why = classify(name, code)
            qs = sorted(n["quarters"])
            w.writerow([name, "|".join(sorted(n["codes"])), SERIES_LABEL.get(series, "排除"), entity, why,
                        n["rows"], len(qs), qs[0], qs[-1]])

    pdf = pd.DataFrame(panel, columns=["quarter", "secucode", "name", "series", "entity", "table",
                                       "holder_name", "rank", "hold_num"])
    pdf.to_csv(os.path.join(OUT, "company_panel.csv.gz"), index=False, encoding="utf-8", compression="gzip")

    # ---------------- 每季度集合
    sets = {}
    for q in QUARTERS:
        L = QLABEL[q]
        sub = pdf[pdf.quarter == L]
        sets[L] = {
            "huijin": set(sub[sub.series == "huijin"].secucode),
            "zhengjin": set(sub[sub.series == "zhengjin"].secucode),
            "huijin_ext": set(sub[sub.series.isin(["huijin", "huijin_ext"])].secucode),
            **{f"e:{e}": set(sub[sub.entity == e].secucode) for e in
               ["汇金投资", "汇金资管", "汇金资管·委托计划", "证金公司", "证金·资管计划", "建银投资"]},
            "hj_top10": set(sub[(sub.series == "huijin") & (sub.table == "十大股东")].secucode),
            "hj_free": set(sub[(sub.series == "huijin") & (sub.table == "十大流通股东")].secucode),
            "zj_top10": set(sub[(sub.series == "zhengjin") & (sub.table == "十大股东")].secucode),
            "zj_free": set(sub[(sub.series == "zhengjin") & (sub.table == "十大流通股东")].secucode),
        }
        sets[L]["union"] = sets[L]["huijin"] | sets[L]["zhengjin"]
        sets[L]["both"] = sets[L]["huijin"] & sets[L]["zhengjin"]

    rows, flows = [], []
    prev = None
    for q in QUARTERS:
        L = QLABEL[q]; s = sets[L]
        r = {"quarter": L, "end_date": q, "universe": len(universe[q]),
             "huijin": len(s["huijin"]), "zhengjin": len(s["zhengjin"]), "union": len(s["union"]),
             "both": len(s["both"]), "huijin_ext": len(s["huijin_ext"]),
             "hj_in_top10": len(s["hj_top10"]), "hj_in_free": len(s["hj_free"]),
             "zj_in_top10": len(s["zj_top10"]), "zj_in_free": len(s["zj_free"])}
        for e in ["汇金投资", "汇金资管", "汇金资管·委托计划", "证金公司", "证金·资管计划", "建银投资"]:
            r[f"n_{e}"] = len(s[f"e:{e}"])
        if prev:
            P = sets[prev["quarter"]]
            for k in ("huijin", "zhengjin", "union"):
                r[f"{k}_qoq"] = r[k] - prev[k]
                r[f"{k}_qoq_pct"] = round((r[k] - prev[k]) / prev[k] * 100, 2) if prev[k] else None
            # 同口径环比：只看两个季度都已披露的公司，剔除新上市 / 退市 / 未披露带来的样本变化
            both_u = universe[q] & universe[prev["end_date"]]
            # 披露覆盖：上季度有名单的公司中，本季度已有名单的比例
            r["coverage_vs_prev_pct"] = round(len(both_u) / len(universe[prev["end_date"]]) * 100, 2)
            r["prev_missing_now"] = len(universe[prev["end_date"]] - universe[q])
            r["union_prev_missing_now"] = len(P["union"] - universe[q])
            for k in ("huijin", "zhengjin", "union"):
                a = len(s[k] & both_u); b = len(P[k] & both_u)
                r[f"{k}_like_for_like_prev"] = b
                r[f"{k}_like_for_like_now"] = a
                new = s[k] - P[k]; gone = P[k] - s[k]
                flows.append({"quarter": L, "series": k, "new": len(new), "gone": len(gone),
                              "gone_not_disclosed": len(gone - universe[q]),
                              "new_ipo_or_first_disclosure": len(new - universe[prev["end_date"]])})
        rows.append(r)
        prev = r
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "quarterly_counts.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(flows).to_csv(os.path.join(OUT, "quarterly_flows.csv"), index=False, encoding="utf-8-sig")

    # 公司 × 季度 出现矩阵（0 无 / 1 仅汇金系 / 2 仅证金系 / 3 两者）——视频粒子矩阵直接使用
    main = pdf[pdf.series.isin(["huijin", "zhengjin"])]
    comp = sorted(main.secucode.unique())
    names_ = dict(zip(main.secucode, main.name))
    labels = [QLABEL[q] for q in QUARTERS]
    presence = []
    for c in comp:
        row = []
        for L in labels:
            v = (1 if c in sets[L]["huijin"] else 0) + (2 if c in sets[L]["zhengjin"] else 0)
            row.append(v)
        presence.append({"code": c, "name": names_[c], "p": row})
    always = [x["name"] for x in presence if all(v > 0 for v in x["p"])]

    # 主体级对比：中央汇金资产管理有限责任公司 vs 中国证券金融股份有限公司（本期视频主线）
    duo_rows, duo_pres = [], []
    for L in labels:
        a_, b_ = sets[L]["e:汇金资管"], sets[L]["e:证金公司"]
        duo_rows.append({"quarter": L, "huijin_am": len(a_), "csf": len(b_), "union": len(a_ | b_), "both": len(a_ & b_)})
    pd.DataFrame(duo_rows).to_csv(os.path.join(OUT, "duo_counts.csv"), index=False, encoding="utf-8-sig")
    duo_comp = sorted(set().union(*[sets[L]["e:汇金资管"] | sets[L]["e:证金公司"] for L in labels]))
    duo_names = dict(zip(pdf.secucode, pdf.name))
    for c in duo_comp:
        duo_pres.append({"code": c, "name": duo_names[c],
                         "p": [(1 if c in sets[L]["e:汇金资管"] else 0) + (2 if c in sets[L]["e:证金公司"] else 0) for L in labels]})

    # 视频用精简数据
    last = rows[-1]["quarter"]
    stats = {"quarters": [r["quarter"] for r in rows],
             "huijin": [r["huijin"] for r in rows], "zhengjin": [r["zhengjin"] for r in rows],
             "union": [r["union"] for r in rows], "both": [r["both"] for r in rows],
             "universe": [r["universe"] for r in rows],
             "entities": {e: [r[f"n_{e}"] for r in rows] for e in
                          ["汇金投资", "汇金资管", "汇金资管·委托计划", "证金公司", "证金·资管计划", "建银投资"]},
             "flows": flows,
             "ever": len(comp), "always": always,
             "universe_like": [r.get("coverage_vs_prev_pct") for r in rows],
             "presence": presence,
             "duo": {"huijin_am": [r["huijin_am"] for r in duo_rows], "csf": [r["csf"] for r in duo_rows],
                     "union": [r["union"] for r in duo_rows], "both": [r["both"] for r in duo_rows],
                     "presence": duo_pres},
             "last": last}
    with open(os.path.join(OUT, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)
    print(pd.DataFrame(rows)[["quarter", "universe", "huijin", "zhengjin", "union", "both", "huijin_ext",
                              "n_汇金投资", "n_汇金资管", "n_汇金资管·委托计划", "n_证金公司", "n_证金·资管计划"]].to_string())


if __name__ == "__main__":
    main()
