# 资料来源、引语出处与素材授权

成片时长 5:26.9。下文时间戳为成片中的出现时间（由 `work/timeline.json` 自动生成）。

## 1. 行情核实（切入点）

- 可口可乐（KO）**2026-10-16 收盘 $93.90**，为历史最高收盘价；**2026-10-15 盘中最高 $94.10**（当日收盘 $92.00）。
  - 一手数据：Nasdaq 历史行情接口 `api.nasdaq.com/api/quote/KO/historical`，与 Yahoo Finance 日线（`data/ko_daily.json`）一致。
  - 背景新闻：2026-10-15 KFC 美国宣布自 2027 年起饮料合作从百事转向可口可乐（Reuters 等报道）；可口可乐第三季度财报定于 2026-10-27。
- 本片所有市值、收益均按 2026-10-16 收盘价计算。

## 2. 伯克希尔持仓、成本与股息（一手来源）

| 时间 | 持股（当时股数） | 累计成本 | 来源 |
|---|---|---|---|
| 1988 年末 | 14,172,500 | $592,540K | [1988 年报](https://www.berkshirehathaway.com/letters/1988.html) 持仓表 |
| 1989 年末 | 23,350,000 | $1,023,920K | [1989 年报](https://www.berkshirehathaway.com/letters/1989.html) |
| 1994 年末 | 100,000,000（1992 年拆股后） | $1,298,888K | [1994 年报](https://www.berkshirehathaway.com/letters/1994.html)；[2022 信](https://www.berkshirehathaway.com/letters/2022ltr.pdf)：1994 年 8 月完成买入 |
| 2025 年末 | 400,000,000（9.3%） | $1,299M；2025 年股息 $816M；市值 $27,964M | [2025 年报致股东信](https://www.berkshirehathaway.com/letters/2025ltr.pdf) |
| 2026-06-30 | 400,000,000 | — | 伯克希尔 13F-HR（SEC，2026-08-14 提交，accession 0001193125-26-352200） |

- 1988 年首次买入与此后增持分开计算（当前股本口径，拆股 1990/1992/1996/2012 各 1 拆 2）：
  - 1988：新增 226.76 百万股（今日口径），成本 $592.5M，今日市值 $21.29B（35.9 倍）
  - 1989：新增 146.84 百万股（今日口径），成本 $431.4M，今日市值 $13.79B（32.0 倍）
  - 1994：新增 26.40 百万股（今日口径），成本 $275.0M，今日市值 $2.48B（9.0 倍）
- 「一股未卖」：[2003 信](https://www.berkshirehathaway.com/letters/2003ltr.pdf)「we last changed our position in Coca-Cola in 1994」；[2023 信](https://www.berkshirehathaway.com/letters/2023ltr.pdf)「During 2023, we did not buy or sell a share of either AMEX or Coke」；13F 2026Q2 仍为 4 亿股。
- 伯克希尔公布的年度可口可乐股息：1994 年 $75M（2022 信）、1995 年 $88M（2010 信）、2010 年 $352M / 2011 年 $376M（2010 信）、2022 年 $704M（2022 信）、2025 年 $816M（2025 年报）。

## 3. 计算口径（`data/calc.py` → `data/calc.json`）

- 市值 = 400,000,000 × $93.90 = **$37.56B（约 376 亿美元）**；总成本 $1.2989B；未实现收益 **$36.26B（约 363 亿，未扣税）**；28.9 倍；平均成本 $3.247/股。
- 2026 年股息：每股 $0.53 × 4 = $2.12（KO 2025 10-K：第 64 次连续年度提高）× 4 亿股 = **$848M（全年预计；截至 10 月已收 3 次 $636M）**，约为成本的 65.3%。
- 累计股息（保守估算）≈ **$13.05B**：按每个除息日伯克希尔已知的最低持股数 × 每股股息（Yahoo，拆股调整）；1988 年股息不计；1989-03-15 前按 1988 年末持股；1994、1995、2022、2025 用伯克希尔公布值；剔除 Yahoo 2001-09-12 的重复记录。股息未再投资，因此与股价回报分开列示。
- 股价年化：1988 年批次成本 $2.613/股 → $93.90，约 **9.9%/年**。含股息再投资（KO 复权价，1988 年下半年均价起）12.6%/年；同期标普 500 全收益指数 11.4%/年。
- **1988 年投下的每 1 美元**（同一口径：1988 年批次每股成本 $2.613 → 2026-10-16，38.08 年）：只算股价 $35.9（年化 9.9%）；加上现金股息、不再投资 $48.4（年化 10.7%，每股股息 1989–2026 累计，1988 年不计）；股息全部再投入 $91.5（年化 12.6%，KO 复权价）；同期标普 500 全收益 $61.8（年化 11.4%）。片中“跑赢指数”只比较两者都把股息再投入的口径（91 vs 62）；“复利 ×1.9”= 再投入 ÷ 现金股息。均未扣税。
- 另一口径（伯克希尔整笔持仓 12.99 亿成本，1988–1994 分批买入）：市值 + 已收现金股息 ≈ $50.6B（39 倍）；同样买入时点股息再投入 ≈ $93.9B（72 倍）；同样的钱同样时点买标普 500 全收益 ≈ $69.5B（54 倍）。两种口径结论一致（再投入的可口可乐跑赢标普 500），但倍数不能跨口径相减。
- 回报拆解：1988 年末股价 $2.79、持续经营 EPS $0.185（KO 1998 10-K，复权口径）→ 2025 摊薄 EPS $3.04（KO 2025 10-K）：EPS ×16.4，市盈率 15.1 → 30.9（×2.05），股价 ×33.7。
- 1998 泡沫：1998 年末市盈率 = $67.00 / $1.42 ≈ 47 倍（KO 1998 10-K）；1998 年收盘高点 1998-07-14，股价直到 2014-10-08 才收盘超过（16.2 年）；伯克希尔持仓市值 1998 年末 $13.4B → 2005 年末 $8.1B（2005 信）。
- 机会成本：1998-07-14 → 2026-10-16，KO 含股息总回报 ×4.57，标普 500 全收益 ×10.82。1988 年下半年 → 1998 高点：KO ×20.0，标普 ×5.7。
- 卖出税负 ≈ $36.3B × 21%（美国联邦企业所得税率）≈ $7.6B —— **本片估算**，非巴菲特原话；实际税负取决于税法与州税。
- 伯克希尔 1988 年末净资产约 $34 亿（1991 信：“When we loaded up on Coke three years ago, Berkshire's net worth was $3.4 billion”）。

## 4. 可口可乐经营数据

- 1988：收入 $8,065M、净利 $1,045M、净资产收益率 34.7%、资本回报率 21.3%（[KO 1993 10-K 十一年摘要](https://www.sec.gov/Archives/edgar/data/21344/0000950144-94-000600.txt)）；1988 年末股价 $5.58、持续经营 EPS $0.37（1998 口径，[KO 1998 10-K](https://www.sec.gov/Archives/edgar/data/21344/0000021344-99-000005.txt)）→ 市盈率约 15 倍。
- 2025（[KO 2025 10-K](https://www.sec.gov/Archives/edgar/data/21344/000162828026010047/ko-20251231.htm)）：收入 $47,941M、毛利 $29,544M（61.6%）、资本开支 $2,112M（4.4%）、摊薄 EPS $3.04；每天 22 亿份；200 多个国家和地区；浓缩液业务占单位箱销量 85%、净营业收入 59%；2026 年季度股息 $0.53，第 64 次连续提高。
- 1994：约 2,800 亿份 8 盎司饮料、每份赚不到 1 美分；伯克希尔 7.8% 权益对应近 $200M“汽水利润”（1994 信）。

## 5. 大师原话（全部为可核实的文字原文；片中以英文原句 + 中文翻译呈现，1993 年“护城河”一句在画面中只以中文引出）

| 片中时间 | 原文 | 中文 | 出处 |
|---|---|---|---|
| 0:45.5 | “Only in the summer of 1988 did my brain finally establish contact with my eyes.” | 直到1988年夏天，我的大脑才终于和眼睛接上了线。 | [1989 年致股东信](https://www.berkshirehathaway.com/letters/1989.html) |
| 1:49.7 | “We are going to start something like an autocatalytic reaction—precisely the sort of multifactor-triggered lollapalooza effect we need.” | 我们将启动一种类似化学自催化的反应——正是我们需要的、由多因素触发的 lollapalooza 效应。 | [Charlie Munger，“Practical Thought about Practical Thought?”，1996-07-20 非正式演讲，收录于《穷查理宝典》第四讲](https://www.stripe.press/poor-charlies-almanack/talk-four) |
| 2:07.4 | “It took only fifty years before I finally got it: The real money was in the syrup.” | 只花了五十年，我终于明白：真正的钱在糖浆里。 | [1994 年致股东信](https://www.berkshirehathaway.com/letters/1994.html) |
| 2:22.9 | “…setting up a protective moat around their economic castles.” | ……在它们的经济城堡周围，筑起一道护城河。 | [1993 年致股东信](https://www.berkshirehathaway.com/letters/1993.html) |
| 3:56.0 | “I made a big mistake in not selling several of our larger holdings during The Great Bubble.” | 在大泡沫期间没有卖出几只大型持股，是我的一个大错误。 | [2003 年致股东信](https://www.berkshirehathaway.com/letters/2003ltr.pdf) |
| 3:56.0 | “I talked when I should have walked.” | 我只是说了，却没有做。 | [2004 年致股东信](https://www.berkshirehathaway.com/letters/2004ltr.pdf) |
| 4:24.5 | “…we may significantly adjust a holding if we see fundamental changes in its long-term economic prospects.” | ……如果看到其长期经济前景发生根本变化，我们可能大幅调整持仓。 | [伯克希尔 2025 年报致股东信（Greg Abel 署名，2026 年 2 月发布）](https://www.berkshirehathaway.com/letters/2025ltr.pdf) |
| 4:36.0 | “Invert, always invert.” | 反过来想，总是反过来想。 | [同上 Munger 1996 演讲（引数学家 Carl Jacobi）](https://www.stripe.press/poor-charlies-almanack/talk-four) |
| 4:48.7 | “You can, of course, pay too much for even the best of businesses.” | 当然，即使是最好的企业，你也可能付出过高的价格。 | [1996 年致股东信](https://www.berkshirehathaway.com/letters/1996.html) |
| 5:10.5 | “Time is the friend of the wonderful business.” | 时间是优秀企业的朋友。 | [2010 年致股东信](https://www.berkshirehathaway.com/letters/2010ltr.pdf) |

旁白中的转述：1936 年 25 美分买 6 瓶、5 美分一瓶卖出，52 年未买、所列行业（1989 信）；郭思达 1981 年任 CEO、与基奥重新聚焦、海外销量爆发（1989 信）；芒格“200 万美元变 2 万亿”、商标、操作性条件反射、巴甫洛夫条件反射、社会认同、多因素合奏（lollapalooza）效应、无处不在的渠道、规模经济（Munger 1996）；“真正的钱在糖浆里”（1994 信）。

**芒格思想实验的“七要素”**：片中把芒格 1996 年演讲（“Practical Thought about Practical Thought?”）里让可口可乐成为伟大公司的要素归纳为七项——商标保护、操作性条件反射、巴甫洛夫条件反射、社会认同、多因素合奏效应、无处不在的分销、规模经济，并重点展开其中三种心理学力量如何彼此放大。**这是本片对原文的七维归纳，并非芒格逐字给出的编号清单**；画面中有同样的脚注。片中英文引语“autocatalytic reaction… lollapalooza effect”为演讲原文。

## 6. 旁白逐句出处

| 时间 | 旁白 | 出处 |
|---|---|---|
| 0:01.2 | 可口可乐，创历史新高了——93.9美元。 | Nasdaq/Yahoo 日线：2026-10-16 收盘 $93.90，历史最高收盘 |
| 0:05.9 | 有一位股东，已经持有它38年：当年13亿美元买入，如今市值约376亿。 | 1994 年报：成本 $1,298.9M；400,000,000 股 × $93.90 |
| 0:14.2 | 仅股息一项，今年就有8.48亿美元。 | 2026 年每股 $2.12（KO 2025 10-K：第 64 次连续提高）× 4 亿股 |
| 0:18.5 | 泡沫、危机、疫情……他一股未卖。为什么？ | 2003 信：KO 持仓最后一次变动在 1994 年；2023 信：未买卖一股；13F 2026Q2：4 亿股 |
| 0:30.8 | 1936年，童年的巴菲特在祖父的杂货店，25美分买6瓶可乐，5美分一瓶卖给邻居。 | 1989 年致股东信 |
| 0:39.6 | 此后52年，他看着可乐席卷世界，却一股也没买。 | 1989 年致股东信 |
| 0:45.5 | 直到1988年夏天——用他的话说——“大脑终于和眼睛接上了线”。 | 1989 年致股东信 |
| 0:52.3 | 1981年郭思达接任CEO，可口可乐重新聚焦主业，海外销量随之爆发。 | 1989 年致股东信 |
| 0:59.5 | 1988年，它的净资产收益率34.7%，市盈率却只有约15倍。 | KO 1993 10-K 十一年财务摘要；KO 1998 10-K |
| 1:06.5 | 两年间，伯克希尔投入10.2亿美元，约占它当时净资产的三成。 | 1989 年报持仓表；1991 信（1988 年末净资产 $34 亿） |
| 1:14.6 | 一瓶糖水，凭什么成为持续创造现金的机器？芒格做过一个思想实验—— | 本片叙述 |
| 1:22.3 | 回到1884年的亚特兰大，怎样把200万美元，变成2万亿？ | Munger, “Practical Thought about Practical Thought?”（1996-07-20） |
| 1:29.2 | 第一步：打造一个受法律保护的强大商标。 | Munger 1996 |
| 1:33.8 | 操作性条件反射：甜、冰、提神，让人喝了还想喝。 | Munger 1996（operant conditioning） |
| 1:39.8 | 巴甫洛夫条件反射：把品牌和快乐、青春、庆祝绑在一起。 | Munger 1996（Pavlovian conditioning） |
| 1:45.6 | 社会认同：看到别人都在喝，你也想尝一口。 | Munger 1996（social proof） |
| 1:49.7 | 三者互相放大，芒格称之为“多因素合奏效应”。 | Munger 1996（autocatalytic reaction / lollapalooza effect） |
| 1:54.8 | 再加上无处不在的渠道：200多个国家和地区，每天22亿份。 | Munger 1996（available everywhere）；KO 2025 10-K |
| 2:01.1 | 工厂和卡车大多属于装瓶伙伴，它卖的是浓缩液和品牌。 | KO 2025 10-K：浓缩液业务占销量 85% |
| 2:07.4 | 巴菲特说：真正的钱，在糖浆里。 | 1994 年致股东信 |
| 2:11.3 | 毛利率61.6%，资本开支只占收入的4.4%。 | KO 2025 10-K |
| 2:16.7 | 巨大的销量摊薄了广告和分销成本——对手越追，代价越高。 | 1994 年致股东信（每份不到 1 美分）；Munger 1996（规模劣势 / 分销成本优势） |
| 2:22.9 | 这就是巴菲特说的：环绕经济城堡的护城河。 | 1993 年致股东信 |
| 2:30.0 | 1988年，首批1417万股，成本5.93亿美元。 | 1988 年报持仓表 |
| 2:37.8 | 1994年8月最后一次买入，总成本12.99亿美元。 | 1989、1994 年报；2022 信 |
| 2:44.1 | 四次拆股后，1股变16股：4亿股，均价每股3.25美元。 | KO 拆股：1990/1992/1996/2012 各 1 拆 2 |
| 2:51.9 | 按最新收盘价，市值约376亿美元，账面浮盈约363亿。 | data/calc.json |
| 2:59.4 | 股息从1994年的7500万，涨到今年预计的8.48亿；38年累计，保守估算约130亿美元。 | 2022 信（1994 年 $75M）；2026 年 $2.12 × 4 亿股；累计：data/calc.py（保守口径） |
| 3:11.6 | 算上股息，1988年投下的每一美元：拿现金，今天约48美元；再投入，是91美元。 | data/calc.py per_dollar_1988：1988 年批次每股成本 $2.613（拆股调整）；现金股息 = 1989–2026 每股股息累计、不再投资；再投资 = KO 复权价 |
| 3:21.8 | 同期标普500含股息是62美元，它跑赢了指数。48到91的差距，就是复利。 | data/calc.py：^SP500TR，1988 年下半年均价起至 2026-10-16 |
| 3:31.0 | 其中股价年化不到10%：每股利润涨了约16倍，估值从15倍升到31倍。 | data/calc.json：9.9%/年；KO 1998 10-K（1988 EPS）与 2025 10-K（EPS $3.04） |
| 3:42.6 | 但这条路，并不平坦。 | 本片叙述 |
| 3:45.9 | 1998年，可口可乐市盈率高达47倍。泡沫破裂后，股价用了整整16年，才重回高点。 | KO 1998 10-K（年末价 $67.00 / EPS $1.42）；Yahoo 日线：1998-07-14 → 2014-10-08 |
| 3:56.0 | 巴菲特后来承认，没在泡沫中卖出是个大错误：“我说了，却没有做。” | 2003、2004 年致股东信 |
| 4:03.8 | 从那个高点算起，可口可乐含股息总回报约4.6倍，标普500约10.8倍。 | data/calc.json（1998-07-14 → 2026-10-16） |
| 4:11.1 | 那他为什么还不卖？ | 本片叙述 |
| 4:13.1 | 因为生意没有变坏：股息连续64年增长。 | KO 2025 10-K |
| 4:18.3 | 而卖出要先缴巨额税款，同样优秀的替代品又极少。 | 本片分析（非巴菲特原话） |
| 4:24.5 | 但持有并非无条件。接班人阿贝尔写道：若长期前景发生根本变化，可能大幅调整持仓。 | 伯克希尔 2025 年报致股东信（Greg Abel，2026 年 2 月） |
| 4:36.0 | 芒格常说：反过来想。什么会让这笔投资失败？ | Munger 1996（引雅可比：Invert, always invert） |
| 4:41.4 | 买得太贵、借钱被迫卖出、恐慌中离场，或者护城河被攻破。 | 本片分析 |
| 4:48.7 | 再好的企业，也可能被买贵。 | 1996 年致股东信 |
| 4:52.0 | 长期持有本身并不创造价值；真正创造财富的，是企业持续增长的内在价值。 | 本片叙述 |
| 5:00.2 | 投资者最重要的能力，是在合理的价格识别伟大企业，并在基本面没有改变时，有耐心陪伴价值成长。 | 本片叙述 |
| 5:10.5 | 时间，是优秀企业的朋友。 | 2010 年致股东信 |
| 5:14.5 | 下期：360亿美元买入苹果，他为什么又卖掉了大半？（片尾系列预告） | 2020 年致股东信（苹果持仓成本 $36B）；2025 年报持仓表与 13F（2026-06-30 持股 2.28 亿股） |

- 下期预告的数字：伯克希尔 [2020 年致股东信](https://www.berkshirehathaway.com/letters/2020ltr.pdf) 写苹果持仓“Our cost for that stake was $36 billion”（5.4% 持股）；[2018 年报持仓表](https://www.berkshirehathaway.com/letters/2018ltr.pdf) 苹果成本 $36,044M、255,300,329 股（2020 年 1 拆 4 前，约合 10.21 亿股）；[2025 年报持仓表](https://www.berkshirehathaway.com/letters/2025ltr.pdf) 苹果成本 $6,255M、市值 $61,962M；13F 2026Q2 持股 227,917,808 股。“卖掉了大半”按股数计：较高峰减持约 78%。

## 7. 素材与授权

**历史图片（Wikimedia Commons / 美国国会图书馆）**

- `evans_coke_shack_1935`：Coca-Cola shack in Alabama by Walker Evans.jpg — Walker Evans，1935-12，**Public domain**。[https://commons.wikimedia.org/wiki/File%3ACoca-Cola_shack_in_Alabama_by_Walker_Evans.jpg](https://commons.wikimedia.org/wiki/File%3ACoca-Cola_shack_in_Alabama_by_Walker_Evans.jpg)
- `evans_sandwich_shop_1936`：Roadside sandwich shop. Ponchatoula, Louisiana, 1936-02.jpg — Walker Evans，1936-02，**Public domain**。[https://commons.wikimedia.org/wiki/File%3ARoadside_sandwich_shop._Ponchatoula%2C_Louisiana%2C_1936-02.jpg](https://commons.wikimedia.org/wiki/File%3ARoadside_sandwich_shop._Ponchatoula%2C_Louisiana%2C_1936-02.jpg)
- `bottle_patent_1915`：Coke bottle patent.png — Alexander Samuelson（发明人）/ 美国专利商标局，1915-11-16，**Public domain**。[https://commons.wikimedia.org/wiki/File%3ACoke_bottle_patent.png](https://commons.wikimedia.org/wiki/File%3ACoke_bottle_patent.png)
- `buffett_2015`：Warren Buffett at the 2015 SelectUSA Investment Summit.jpg — USA International Trade Administration，2015-04-17，**Public domain（美国联邦政府作品）**。[https://commons.wikimedia.org/wiki/File%3AWarren_Buffett_at_the_2015_SelectUSA_Investment_Summit.jpg](https://commons.wikimedia.org/wiki/File%3AWarren_Buffett_at_the_2015_SelectUSA_Investment_Summit.jpg)
- `munger_2010`：Charlie Munger.jpg — Nick Webb，2010-05-05，**CC BY 2.0**。[https://commons.wikimedia.org/wiki/File%3ACharlie_Munger.jpg](https://commons.wikimedia.org/wiki/File%3ACharlie_Munger.jpg)
- `coke_ad_1890s`：Cocacola-5cents-1900 edit1.jpg — 未署名（1890 年代广告），1890s，**Public domain**。[https://commons.wikimedia.org/wiki/File%3ACocacola-5cents-1900_edit1.jpg](https://commons.wikimedia.org/wiki/File%3ACocacola-5cents-1900_edit1.jpg)
- 世界陆地轮廓：Natural Earth 1:110m land（公有领域）。
**生成与原创部分**

- 旁白：Gemini TTS `gemini-3.8-flash-tts`（音色 Charon——与“巴芒价值”系列旁白统一），按 5 个大段各一次读完（用户给定的统一 AUDIO PROFILE），转写逐字校对、按音高与语速一致性选用并统一校准语速；为本片中文旁白，**未模仿巴菲特或芒格的声音**。
- 配乐：Google Lyria `lyria-3-pro-preview` 生成的同调、同速、同主题的三大段原创管弦乐（`assets/generated/music3/`），按叙事节点剪辑对位（`src/score.py`）；低频冲击、sub drop 为程序合成。
- 配乐重拍与叙事节点（成片时间）：0:24.6 标题；1:51.1；2:54.2；4:13.1；5:00.2；5:21.1 片尾 logo。
- 三维瓶身、点阵地球、糖浆滴落、粒子与全部数据图表：本项目代码原创渲染（GLSL + numpy）。
- 品牌：右上角全程使用 `brand.Hud`；片尾 logo 为 `brand/logo_baman.png` 原图（粒子汇聚以其透明通道为目标，最终显示原始 logo）。

**未使用的真实影像（如实说明）**

- 伯克希尔股东大会影像（1994 年至今）由 CNBC「Warren Buffett Archive」持有版权，公开访谈亦属各媒体版权；本项目无法获得授权，因此**没有剪入任何股东大会或访谈视频/原声**，改为引用可核实日期和上下文的致股东信与演讲文字原文，配合原创动画表达。
- 网上流传的“巴菲特谈可口可乐”剪辑多为二次上传，来源与授权无法核实，未采用。
