"""生成 docs/SOURCES.md（资料来源、引语出处与片中时间戳、素材授权）。时间戳取自 work/timeline.json。"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, QUOTES, TEASE

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
work = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work')
TL = json.load(open(os.path.join(work, 'timeline.json')))
C = json.load(open(os.path.join(ROOT, 'data', 'calc.json')))
CR = json.load(open(os.path.join(ROOT, 'assets', 'archive', 'credits.json')))
SEG = {s['id']: s for s in TL['segs']}


def ts(sec):
    d = int(round(sec * 10)); return f'{d // 600}:{(d % 600) / 10:04.1f}'


LET = 'https://www.berkshirehathaway.com/letters/'
QSRC = {
    'q1989': ('1989 年致股东信', LET + '1989.html', 's09'),
    'q1994': ('1994 年致股东信', LET + '1994.html', 's20'),
    'qauto': ('Charlie Munger，“Practical Thought about Practical Thought?”，1996-07-20 非正式演讲，收录于《穷查理宝典》第四讲',
              'https://www.stripe.press/poor-charlies-almanack/talk-four', 's17d'),
    'q1993': ('1993 年致股东信', LET + '1993.html', 's23'),
    'q2003': ('2003 年致股东信', LET + '2003ltr.pdf', 's37'),
    'q2004': ('2004 年致股东信', LET + '2004ltr.pdf', 's37'),
    'qabel': ('伯克希尔 2025 年报致股东信（Greg Abel 署名，2026 年 2 月发布）', LET + '2025ltr.pdf', 's42'),
    'q1996': ('1996 年致股东信', LET + '1996.html', 's45'),
    'qinvert': ('同上 Munger 1996 演讲（引数学家 Carl Jacobi）', 'https://www.stripe.press/poor-charlies-almanack/talk-four', 's43'),
    'q2010': ('2010 年致股东信', LET + '2010ltr.pdf', 's48'),
}

out = []
w = out.append
w('# 资料来源、引语出处与素材授权\n')
w(f'成片时长 {ts(TL["total"])}。下文时间戳为成片中的出现时间（由 `work/timeline.json` 自动生成）。\n')
w('## 1. 行情核实（切入点）\n')
w(f'- 可口可乐（KO）**2026-10-16 收盘 ${C["close"]:.2f}**，为历史最高收盘价；**2026-10-15 盘中最高 $94.10**（当日收盘 $92.00）。')
w('  - 一手数据：Nasdaq 历史行情接口 `api.nasdaq.com/api/quote/KO/historical`，与 Yahoo Finance 日线（`data/ko_daily.json`）一致。')
w('  - 背景新闻：2026-10-15 KFC 美国宣布自 2027 年起饮料合作从百事转向可口可乐（Reuters 等报道）；可口可乐第三季度财报定于 2026-10-27。')
w('- 本片所有市值、收益均按 2026-10-16 收盘价计算。\n')
w('## 2. 伯克希尔持仓、成本与股息（一手来源）\n')
w('| 时间 | 持股（当时股数） | 累计成本 | 来源 |')
w('|---|---|---|---|')
w(f'| 1988 年末 | 14,172,500 | $592,540K | [1988 年报]({LET}1988.html) 持仓表 |')
w(f'| 1989 年末 | 23,350,000 | $1,023,920K | [1989 年报]({LET}1989.html) |')
w(f'| 1994 年末 | 100,000,000（1992 年拆股后） | $1,298,888K | [1994 年报]({LET}1994.html)；[2022 信]({LET}2022ltr.pdf)：1994 年 8 月完成买入 |')
w(f'| 2025 年末 | 400,000,000（9.3%） | $1,299M；2025 年股息 $816M；市值 $27,964M | [2025 年报致股东信]({LET}2025ltr.pdf) |')
w('| 2026-06-30 | 400,000,000 | — | 伯克希尔 13F-HR（SEC，2026-08-14 提交，accession 0001193125-26-352200） |')
w('\n- 1988 年首次买入与此后增持分开计算（当前股本口径，拆股 1990/1992/1996/2012 各 1 拆 2）：')
for t in C['tranches']:
    w(f'  - {t["year"]}：新增 {t["add_shares_now"] / 1e6:,.2f} 百万股（今日口径），成本 ${t["add_cost"] / 1e6:,.1f}M，'
      f'今日市值 ${t["value_now"] / 1e9:,.2f}B（{t["multiple"]:.1f} 倍）')
w('- 「一股未卖」：[2003 信]({0}2003ltr.pdf)「we last changed our position in Coca-Cola in 1994」；[2023 信]({0}2023ltr.pdf)「During 2023, we did not buy or sell a share of either AMEX or Coke」；13F 2026Q2 仍为 4 亿股。'.format(LET))
w('- 伯克希尔公布的年度可口可乐股息：1994 年 $75M（2022 信）、1995 年 $88M（2010 信）、2010 年 $352M / 2011 年 $376M（2010 信）、2022 年 $704M（2022 信）、2025 年 $816M（2025 年报）。\n')
w('## 3. 计算口径（`data/calc.py` → `data/calc.json`）\n')
w(f'- 市值 = 400,000,000 × ${C["close"]:.2f} = **${C["market_value"] / 1e9:.2f}B（约 376 亿美元）**；总成本 $1.2989B；'
  f'未实现收益 **${C["unrealized_gain"] / 1e9:.2f}B（约 363 亿，未扣税）**；{C["multiple"]:.1f} 倍；平均成本 ${C["avg_cost_per_share"]:.3f}/股。')
w(f'- 2026 年股息：每股 $0.53 × 4 = $2.12（KO 2025 10-K：第 64 次连续年度提高）× 4 亿股 = **$848M（全年预计；截至 10 月已收 3 次 $636M）**，'
  f'约为成本的 {C["dividend_yield_on_cost"] * 100:.1f}%。')
w(f'- 累计股息（保守估算）≈ **${C["cum_dividends"] / 1e9:.2f}B**：按每个除息日伯克希尔已知的最低持股数 × 每股股息（Yahoo，拆股调整）；'
  '1988 年股息不计；1989-03-15 前按 1988 年末持股；1994、1995、2022、2025 用伯克希尔公布值；剔除 Yahoo 2001-09-12 的重复记录。'
  '股息未再投资，因此与股价回报分开列示。')
w(f'- 股价年化：1988 年批次成本 $2.613/股 → $93.90，约 **{C["cagr_price_from_1988_tranche"] * 100:.1f}%/年**。'
  f'含股息再投资（KO 复权价，1988 年下半年均价起）{C["cagr_ko_tr_1988"] * 100:.1f}%/年；同期标普 500 全收益指数 {C["cagr_sp_tr_1988"] * 100:.1f}%/年。')
pdl = C['per_dollar_1988']
w(f'- **1988 年投下的每 1 美元**（同一口径：1988 年批次每股成本 $2.613 → 2026-10-16，{pdl["years"]} 年）：只算股价 ${pdl["price"]:.1f}（年化 {pdl["cagr_price"] * 100:.1f}%）；'
  f'加上现金股息、不再投资 ${pdl["cash_dividends"]:.1f}（年化 {pdl["cagr_cash"] * 100:.1f}%，每股股息 1989–2026 累计，1988 年不计）；'
  f'股息全部再投入 ${pdl["reinvested"]:.1f}（年化 {pdl["cagr_reinvested"] * 100:.1f}%，KO 复权价）；同期标普 500 全收益 ${pdl["sp500_tr"]:.1f}（年化 {pdl["cagr_sp500_tr"] * 100:.1f}%）。'
  f'片中“跑赢指数”只比较两者都把股息再投入的口径（91 vs 62）；“复利 ×{pdl["reinvested"] / pdl["cash_dividends"]:.1f}”= 再投入 ÷ 现金股息。均未扣税。')
cmp_ = C['compare']
w(f'- 另一口径（伯克希尔整笔持仓 12.99 亿成本，1988–1994 分批买入）：市值 + 已收现金股息 ≈ ${cmp_["berkshire_actual_total"] / 1e9:.1f}B（{cmp_["berkshire_actual_total"] / C["cost"]:.0f} 倍）；'
  f'同样买入时点股息再投入 ≈ ${cmp_["ko_dividends_reinvested"] / 1e9:.1f}B（{cmp_["ko_dividends_reinvested"] / C["cost"]:.0f} 倍）；同样的钱同样时点买标普 500 全收益 ≈ ${cmp_["sp500_total_return"] / 1e9:.1f}B（{cmp_["sp500_total_return"] / C["cost"]:.0f} 倍）。'
  '两种口径结论一致（再投入的可口可乐跑赢标普 500），但倍数不能跨口径相减。')
d = C['decomp']
w(f'- 回报拆解：1988 年末股价 $2.79、持续经营 EPS $0.185（KO 1998 10-K，复权口径）→ 2025 摊薄 EPS $3.04（KO 2025 10-K）：'
  f'EPS ×{d["eps_growth"]:.1f}，市盈率 {d["pe_1988"]:.1f} → {d["pe_now"]:.1f}（×{d["pe_now"] / d["pe_1988"]:.2f}），股价 ×{d["price_growth"]:.1f}。')
b = C['bubble']
w(f'- 1998 泡沫：1998 年末市盈率 = $67.00 / $1.42 ≈ 47 倍（KO 1998 10-K）；1998 年收盘高点 {b["peak_day"]}，'
  f'股价直到 {b["price_recovered_on"]} 才收盘超过（{b["years_to_recover"]} 年）；伯克希尔持仓市值 1998 年末 $13.4B → 2005 年末 $8.1B（2005 信）。')
w(f'- 机会成本：{b["peak_day"]} → 2026-10-16，KO 含股息总回报 ×{b["ko_tr_since_peak"]:.2f}，标普 500 全收益 ×{b["sp_tr_since_peak"]:.2f}。'
  f'1988 年下半年 → 1998 高点：KO ×{b["ko_tr_1988_to_peak"]:.1f}，标普 ×{b["sp_tr_1988_to_peak"]:.1f}。')
w('- 卖出税负 ≈ $36.3B × 21%（美国联邦企业所得税率）≈ $7.6B —— **本片估算**，非巴菲特原话；实际税负取决于税法与州税。')
w('- 伯克希尔 1988 年末净资产约 $34 亿（1991 信：“When we loaded up on Coke three years ago, Berkshire\'s net worth was $3.4 billion”）。\n')
w('## 4. 可口可乐经营数据\n')
w('- 1988：收入 $8,065M、净利 $1,045M、净资产收益率 34.7%、资本回报率 21.3%（[KO 1993 10-K 十一年摘要](https://www.sec.gov/Archives/edgar/data/21344/0000950144-94-000600.txt)）；'
  '1988 年末股价 $5.58、持续经营 EPS $0.37（1998 口径，[KO 1998 10-K](https://www.sec.gov/Archives/edgar/data/21344/0000021344-99-000005.txt)）→ 市盈率约 15 倍。')
w('- 2025（[KO 2025 10-K](https://www.sec.gov/Archives/edgar/data/21344/000162828026010047/ko-20251231.htm)）：收入 $47,941M、毛利 $29,544M（61.6%）、资本开支 $2,112M（4.4%）、'
  '摊薄 EPS $3.04；每天 22 亿份；200 多个国家和地区；浓缩液业务占单位箱销量 85%、净营业收入 59%；2026 年季度股息 $0.53，第 64 次连续提高。')
w('- 1994：约 2,800 亿份 8 盎司饮料、每份赚不到 1 美分；伯克希尔 7.8% 权益对应近 $200M“汽水利润”（1994 信）。\n')
w('## 5. 大师原话（全部为可核实的文字原文；片中以英文原句 + 中文翻译呈现，1993 年“护城河”一句在画面中只以中文引出）\n')
w('| 片中时间 | 原文 | 中文 | 出处 |')
w('|---|---|---|---|')
for k, (en, cn, who) in sorted(QUOTES.items(), key=lambda kv: SEG[QSRC[kv[0]][2]]['start'] if kv[0] in QSRC else 1e9):
    if k not in QSRC: continue
    name, url, sid = QSRC[k]
    w(f'| {ts(SEG[sid]["start"])} | “{en}” | {cn} | [{name}]({url}) |')
w('\n旁白中的转述：1936 年 25 美分买 6 瓶、5 美分一瓶卖出，52 年未买、所列行业（1989 信）；郭思达 1981 年任 CEO、与基奥重新聚焦、海外销量爆发（1989 信）；'
  '芒格“200 万美元变 2 万亿”、商标、操作性条件反射、巴甫洛夫条件反射、社会认同、多因素合奏（lollapalooza）效应、'
  '无处不在的渠道、规模经济（Munger 1996）；“真正的钱在糖浆里”（1994 信）。\n')
w('**芒格思想实验的“七要素”**：片中把芒格 1996 年演讲（“Practical Thought about Practical Thought?”）里让可口可乐成为伟大公司的要素归纳为七项——'
  '商标保护、操作性条件反射、巴甫洛夫条件反射、社会认同、多因素合奏效应、无处不在的分销、规模经济，并重点展开其中三种心理学力量如何彼此放大。'
  '**这是本片对原文的七维归纳，并非芒格逐字给出的编号清单**；画面中有同样的脚注。片中英文引语“autocatalytic reaction… lollapalooza effect”为演讲原文。\n')
w('## 6. 旁白逐句出处\n')
w('| 时间 | 旁白 | 出处 |')
w('|---|---|---|')
for l in LINES:
    s = SEG[l[0]]
    w(f'| {ts(s["start"])} | {l[2]} | {l[5] or "本片叙述"} |')
w(f'| {ts(SEG["tease"]["start"])} | {TEASE[0]}（片尾系列预告） | {TEASE[2]} |')
w('\n- 下期预告的数字：伯克希尔 [2020 年致股东信]({0}2020ltr.pdf) 写苹果持仓“Our cost for that stake was $36 billion”（5.4% 持股）；'
  '[2018 年报持仓表]({0}2018ltr.pdf) 苹果成本 $36,044M、255,300,329 股（2020 年 1 拆 4 前，约合 10.21 亿股）；'
  '[2025 年报持仓表]({0}2025ltr.pdf) 苹果成本 $6,255M、市值 $61,962M；13F 2026Q2 持股 227,917,808 股。'
  '“卖掉了大半”按股数计：较高峰减持约 78%。'.format(LET))
w('\n## 7. 素材与授权\n')
w('**历史图片（Wikimedia Commons / 美国国会图书馆）**\n')
for k, c in CR.items():
    w(f'- `{k}`：{c["title"].replace("File:", "")} — {c["author"]}，{c["date"]}，**{c["license"]}**。[{c["page"]}]({c["page"]})')
w('- 世界陆地轮廓：Natural Earth 1:110m land（公有领域）。')
w('**生成与原创部分**\n')
w('- 旁白：Gemini TTS `gemini-3.8-flash-tts`（音色 Charon——与“巴芒价值”系列旁白统一），按 5 个大段各一次读完（用户给定的统一 AUDIO PROFILE），转写逐字校对、按音高与语速一致性选用并统一校准语速；为本片中文旁白，**未模仿巴菲特或芒格的声音**。')
w('- 配乐：Google Lyria `lyria-3-pro-preview` 生成的同调、同速、同主题的三大段原创管弦乐（`assets/generated/music3/`），按叙事节点剪辑对位（`src/score.py`）；低频冲击、sub drop 为程序合成。')
import json as _j
_h = _j.load(open(os.path.join(work, 'score_hits.json')))['hits'] if os.path.exists(os.path.join(work, 'score_hits.json')) else []
if _h:
    w('- 配乐重拍与叙事节点（成片时间）：' + '；'.join(f'{ts(t)}' + {'title': ' 标题', 'P1': ' 标题', 'logo': ' 片尾 logo'}.get(sid, '') for t, wgt, sid in _h) + '。')
w('- 三维瓶身、点阵地球、糖浆滴落、粒子与全部数据图表：本项目代码原创渲染（GLSL + numpy）。')
w('- 品牌：右上角全程使用 `brand.Hud`；片尾 logo 为 `brand/logo_baman.png` 原图（粒子汇聚以其透明通道为目标，最终显示原始 logo）。\n')
w('**未使用的真实影像（如实说明）**\n')
w('- 伯克希尔股东大会影像（1994 年至今）由 CNBC「Warren Buffett Archive」持有版权，公开访谈亦属各媒体版权；本项目无法获得授权，'
  '因此**没有剪入任何股东大会或访谈视频/原声**，改为引用可核实日期和上下文的致股东信与演讲文字原文，配合原创动画表达。')
w('- 网上流传的“巴菲特谈可口可乐”剪辑多为二次上传，来源与授权无法核实，未采用。')
open(os.path.join(ROOT, 'docs', 'SOURCES.md'), 'w').write('\n'.join(out) + '\n')
print('wrote docs/SOURCES.md')
