# 《十年苹果——巴菲特为什么卖掉了大半》资料来源、引语出处与素材授权

成片时长 13:06.6。时间戳为该句旁白在成片中开始的时刻（由 `work/timeline.json` 自动生成）。行情与持仓数据截至 2026-11-02 收盘（AAPL $338.32；历史最高收盘 2026-10-29 $348.91）。

## 1. 数据口径

- **持股**：伯克希尔 SEC 13F（CIK 1067983），2016Q1–2026Q2，按 2020 年 1 拆 4 调整。
- **买入/卖出金额（估算）**：各季度持股变动 × 该季度 AAPL 日均收盘价（`data/calc.py`），税前；伯克希尔从未逐笔披露成交价。
- **股息（估算）**：每股股息 × 除息日前一季末持股。
- **总账**：买入约 $412 亿；卖出所得约 $1,467 亿；股息约 $60 亿；剩余 2.28 亿股 × $338.32 ≈ $771 亿；合计约为投入的 5.6 倍。
- **年化回报**：按每季度买卖与股息的实际时间计算的内部收益率，约 29.2%；同额同期买入标普 500 全收益指数（^SP500TR）并持有至今约 $1394 亿，年化约 14.8%（`research/stories.md` D 节）。
- **市盈率**：季度日均价 ÷ 上一财年摊薄每股收益（苹果 10-K，拆股调整）。

## 2. 逐句出处


### 开场

- `0:01.2` 2026年秋天，苹果的股价一次又一次刷新历史纪录，市值一度突破5万亿美元。  
  出处：Yahoo Finance 日线：2026 年以来 25 次收盘新高，最高 2026-10-29 $348.91；× 苹果 FY2026 期末股数 145.3 亿 ≈ $5.07 万亿
- `0:11.0` 然而，在这场盛宴里，它最著名的一位股东，却早已把大部分股票卖掉了。  
  出处：本片叙述
- `0:18.4` 他执掌多年的公司，最多时持有苹果超过10亿股；如今，只剩约2.28亿股。  
  出处：13F：2018-09-30 持股 1,009,915,116（按 2020 年拆股调整）；2026-06-30 持股 227,917,808
- `0:26.3` 2023年秋天，这家公司还持有约9.16亿股；此后，它卖掉了其中约四分之三。按各季度的平均股价估算，套现约1340亿美元。  
  出处：13F：2023-09-30 915,560,382 股 → 2025-12-31 227,917,808 股；金额 = 各季度减持股数 × 季度日均收盘价（data/calc.py，估算，税前）
- `0:39.9` 假如当初一股不卖，这9.16亿股，今天值约3100亿美元。  
  出处：915,560,382 股 × $338.32（2026-11-02 收盘）
- `0:46.8` 他是沃伦·巴菲特。卖掉苹果，他卖错了吗？要回答这个问题，得从十年前说起。  
  出处：本片叙述

### 看懂一部手机

- `1:01.7` 几十年来，巴菲特一直守着一条规矩：看不懂的生意，不碰。他把这叫作“能力圈”。  
  出处：本片叙述
- `1:09.9` 所以，他长期远离科技股。少有的一次例外，是2011年买入IBM，投入一百多亿美元；后来他承认判断有误，到2018年全部卖光。  
  出处：Bloomberg 2018-05-04（Buffett: almost certain Berkshire holds zero IBM after Q1 2018 sales）；伯克希尔 2011 年起买入 IBM 逾 $100 亿
- `1:23.8` 就连他自己用的手机，也一直是一部老式翻盖机。  
  出处：CNBC 2020-02-24（此前约 20 美元的三星翻盖手机）
- `1:28.8` 而另一个人，比他更早看懂了苹果。  
  出处：本片叙述
- `1:33.1` 2006年，一位中国企业家以62万美元，拍下了与巴菲特共进午餐的机会，只比第二名多出100美元。他竞拍用的账户名，叫“快即是慢”。  
  出处：美联社 2006-06-23：eBay 格莱德基金会拍卖，2006-06-22 结束，“fastisslow” 出价 $620,100，第二名 $620,000
- `1:50.5` 他叫段永平，步步高的创始人。他说，他从巴菲特身上学到了很多，只是想找个机会，当面谢谢巴菲特。  
  出处：美联社 2006-06-23：“I learned a lot from Warren Buffett and his philosophy” / “I wanted to find a chance to say thanks to him.”
- `2:01.7` 他还准备了一个问题：钱太多，又找不到好的投资对象，该怎么办？  
  出处：美联社 2006-06-23：“when you have too much money in your hand, and don’t find very good targets, what do you do?”
- `2:08.5` 2011年初，段永平开始买入苹果。按他自己的说法，那时他终于想通了：苹果把用户体验做到了极致，它的生意模式，已经形成了护城河。  
  出处：段永平网络问答 2011-01-22、2024-09-12（《大道：段永平投资问答录》收录）
- `2:23.3` 后来，苹果成了他投资组合里分量最重的股票。  
  出处：H&H International 13F（2018 起有数据）：苹果占比约五成至八成，均为第一
- `2:28.8` 五年后，2016年第一季度，伯克希尔第一次买入苹果，投入约10亿美元。出手的并不是巴菲特本人，而是他的两位投资经理之一，托德·库姆斯或特德·韦施勒。巴菲特后来证实了这一点，但从没说过是哪一位。  
  出处：13F 2016Q1（2016-05-16 披露）：拆股前 9,811,747 股，约 $1.07B；CNBC 2017-08-30：巴菲特确认由两位投资经理之一买入，拒绝透露是谁
- `2:50.0` 当时的苹果，正被市场看淡：2016财年，iPhone的销量第一次出现下滑，苹果的全年营收，也迎来了15年来的首次下降。  
  出处：苹果 FY2016 10-K：iPhone 销量 2.119 亿部（FY2015 2.312 亿部）；营收 $215.6B（FY2015 $233.7B，上一次下降为 FY2001）
- `3:03.0` 那年年底，巴菲特亲自出手，开始大举买入。那时，苹果的股价只相当于它一年每股利润的约14倍，也就是市盈率约14倍。  
  出处：2020 年致股东信：“We began buying Apple stock late in 2016”；2016Q4 均价 $28.35 ÷ FY2016 摊薄 EPS $2.08 ≈ 13.6 倍
- `3:16.4` 他看懂苹果，靠的不只是财报，还有身边的小事。周日，他常带十几个孩子去自家旗下的冰雪皇后吃冰淇淋；孩子们个个低头看着自己的苹果设备，除了点单，几乎顾不上跟他说话。  
  出处：CNBC Squawk Box 2017-02-27 实录（冰雪皇后为伯克希尔旗下企业）
- `3:34.5` 在自家的内布拉斯加家具城，他又注意到：店里卖苹果产品，定价低到自己几乎不赚钱；可只要一缺货，顾客就转身离开，去别的店买。  
  出处：2024 年股东大会：“selling Apple products at a price where we weren’t even making any money… people left the store and went to Best Buy”
- `3:48.0` 多年以后他回忆：这些观察日积月累，在某一刻凝结成了行动。心理学家管这叫“统觉团”；而在苹果上，那是一次大行动。  
  出处：2024 年股东大会：“apperceptive mass… crystallizes your thinking into action… big action in the case of Apple”
- `4:01.2` 到2018年7月初，伯克希尔已持有略多于10亿股苹果，成本约360亿美元。苹果，成了它的第一大持仓。  
  出处：2020 年致股东信；2018 年持仓表（苹果市值 $40.3B 居首）
- `4:14.0` 也是在2018年，段永平专程去见了巴菲特。饭桌上，他说：我觉得苹果的生意模式，比可口可乐还要好。巴菲特回了一句：I got it。  
  出处：段永平 2025-01-05 浙江大学讲座（IT之家、证券之星文字实录一致）
- `4:27.3` 不过那时，巴菲特已经买了两年。段永平后来说：他买苹果，跟我没关系。  
  出处：同上讲座：“他买了很多苹果（股票），这个跟我没关系”；段永平雪球：“巴菲特买苹果是他自己的决定”
- `4:35.2` 2020年，巴菲特终于换上了iPhone。他说：我的翻盖手机，永远退役了。  
  出处：CNBC 2020-02-24：“My flip phone is permanently gone.”（iPhone 11）

### 买的是生意

- `4:46.1` 在巴菲特眼里，苹果从来不只是一家卖手机的公司。  
  出处：本片叙述
- `4:51.4` 2020年他说：我不把苹果当成一只股票，我把它当作伯克希尔的第三大生意，仅次于保险和铁路。  
  出处：CNBC 2020-02-24：“I don’t think of Apple as a stock. I think of it as our third business… a bigger commitment than… any business except insurance and the railroad”
- `5:01.8` 他还说，这可能是他所知道的，世界上最好的生意。  
  出处：CNBC 2020-02-24：“It's probably the best business I know in the world.”
- `5:07.0` 好在哪里？2023年，他打了个比方：如果让用户在第二辆车和iPhone之间放弃一个，他们会放弃第二辆车。  
  出处：2023 年股东大会实录
- `5:18.8` 这背后，是他一生的信条：买股票，就是买下一门生意的一部分。股价每天都在变，而生意的价值，取决于它未来能赚多少钱。  
  出处：本片叙述（巴菲特历年致股东信的一贯观点）
- `5:31.8` 那么，这门生意替伯克希尔赚了多少？以2021年为例：苹果付给伯克希尔的股息是7.85亿美元；而按持股比例，伯克希尔应占的苹果利润，高达56亿美元。  
  出处：2021 年致股东信
- `5:49.4` 剩下的大部分利润，苹果没有发下来，而是用来回购自己的股票。  
  出处：2021 年致股东信：“Much of what the company retained was used to repurchase Apple shares”
- `5:55.2` 从2016到2025财年，苹果累计花了约7130亿美元回购，流通在外的股票减少了约三成。  
  出处：苹果 10-K（FY2016–FY2025）回购合计 $713.2B；摊薄加权股数 22.00B → 15.00B（−31.8%）
- `6:06.1` 结果是：2021年，伯克希尔没有花钱增持，持股比例却从5.39%升到了5.55%。巴菲特写道：我们没花伯克希尔一分钱，苹果的回购替我们做到了。  
  出处：2021 年致股东信
- `6:23.4` 这些没有发下来、却实实在在属于股东的利润，巴菲特称之为“透视盈余”。  
  出处：巴菲特历年致股东信（look-through earnings）
- `6:31.0` 回购还有一个效果：同样的利润，由更少的股票来分。从2016到2026财年，苹果的净利润从457亿美元增至1322亿，约为原来的2.9倍；每股收益从2.08美元增至8.98美元，约为原来的4.3倍。  
  出处：苹果 10-K：FY2016 净利 $45.7B、摊薄 EPS $2.08（拆股调整）；FY2026 净利 $132.2B、摊薄 EPS $8.98

### 十年账本

- `6:56.3` 好生意，加上好价格，账本很快给出了答案。  
  出处：本片叙述
- `7:01.6` 到2023年底，伯克希尔持有的苹果市值约1743亿美元，几乎占了它全部股票投资的一半。  
  出处：2023 年报 K-84/85：$174.3B ÷ $353.8B ≈ 49%
- `7:11.2` 这期间，他也零星卖过一些。卖得最多的是2020年，落袋约110亿美元；三年后，他在股东大会上说：那是个愚蠢的决定。  
  出处：2020 年致股东信（$11 billion）；2023 年股东大会（“it was a dumb decision”）
- `7:23.4` 然而，从2023年底开始，真正的减持来了。  
  出处：13F：2023Q4 −1,000 万股；2024Q1 −1.16 亿股
- `7:27.9` 2024年第二季度，伯克希尔一个季度就卖出约3.89亿股，接近当时持仓的一半。  
  出处：13F 2024Q2：789,368,450 → 400,000,000
- `7:35.0` 到2025年底，只剩约2.28亿股。2026年起，格雷格·阿贝尔接任首席执行官，巴菲特留任董事长；截至2026年6月底的持仓报告显示，苹果没有再卖。  
  出处：13F 2025Q4、2026Q1、2026Q2：均为 227,917,808 股；2025 年致股东信署名 Gregory E. Abel, CEO（巴菲特为董事长）
- `7:49.2` 算算总账。按估算，十年间伯克希尔前后累计买入苹果约410亿美元。  
  出处：data/calc.py（估算）：各季度增持股数 × 季度日均收盘价
- `7:56.5` 卖出所得约1470亿，股息约60亿，再加上手里剩下的股票约770亿，合计约2300亿美元，约为投入的5.6倍。这些都是税前的数字。  
  出处：data/calc.py（估算，税前）：卖出 $146.7B + 股息 $6.0B + 现值 $77.1B = $229.8B；÷ 买入 $41.2B
- `8:10.7` 把每一笔买入、卖出和股息的时间都算进去，年化回报约29%。如果同样的钱、在同样的时间买入标普500指数，并一直持有到今天，含股息约值1390亿美元，年化约15%。苹果这笔投资的年化回报，差不多是它的两倍。  
  出处：data/calc.py（估算，税前）：苹果现金流内部收益率 29.2%；同期同额买入 ^SP500TR 并持有至 2026-11-02 价值 $139.4B，IRR 14.8%

### 他为什么卖

- `8:34.9` 既然这么好，为什么要卖？2024年的股东大会上，他给出了线索。  
  出处：2024 年股东大会
- `8:41.6` 第一，价格。他开始大举买入时，苹果的市盈率约14倍；2024年大举卖出时，已接近30倍。生意还是那门好生意，可同样一块钱的利润，市场的出价却高了一倍多。  
  出处：data/calc.py：2016Q4 13.6 倍；2024Q2 30.4 倍（季度均价 ÷ 上一财年摊薄 EPS）
- `9:00.1` 第二，税。他说，伯克希尔在苹果上实现的收益，要按21%缴联邦税；这个税率，不久前还是35%，过去更曾高达52%。  
  出处：2024 年股东大会：“we are paying a 21% federal rate on the gains we’re taking in Apple… that rate was 35% not that long ago, and it’s been 52% in the past”
- `9:15.6` 他判断，未来税率上调的可能性不小。言下之意：与其将来按更高的税率缴，不如趁现在先卖一部分。  
  出处：2024 年股东大会（CNBC 段落摘要：higher taxes are quite likely）；“言下之意”为本片解读
- `9:25.7` 第三，现金。他说，在当前情况下，他一点也不介意增加现金。当年段永平想问的那个问题：钱太多，好机会太少，如今也摆在了巴菲特自己面前。  
  出处：2024 年股东大会：“But I don’t mind at all, under current conditions, building the cash position.”；后半句为本片叙述
- `9:41.7` 还有一点，他没有明说，却摆在桌面上：一只股票，占了伯克希尔股票投资的近一半。再好的生意，这样的集中度，也是风险。  
  出处：2023 年报（49%）；本片解读，非巴菲特原话
- `9:54.1` 但他同时强调：苹果，仍会是我们最大的投资。到2025年底，它依然是伯克希尔的第一大持仓。  
  出处：2024 年股东大会；2025 年致股东信持仓表（苹果 $62.0B，居首）
- `10:05.0` 那么，卖错了吗？2023年秋天以来卖出的约6.9亿股，估算均价约195美元；今天，苹果的股价是338美元。  
  出处：data/calc.py（估算）：687,642,574 股，均价 $195.10；2026-11-02 收盘 $338.32
- `10:18.7` 如果没卖，这些股票今天会比当初卖出的价钱多值约1000亿美元。不过，这只是税前、只看股价的账面差额，还没算卖出后那笔现金买国债挣到的利息。  
  出处：687.6M × ($338.32 − $195.10) ≈ $985 亿（税前）
- `10:33.5` 卖出之后的这两年多，苹果的每股收益又增长了近一半，市场给它的估值，也从约30倍升到了约38倍。而这两件事，在他卖出的那一刻，谁也无法确知。  
  出处：摊薄 EPS：FY2023 $6.13 → FY2026 $8.98（+46%）；P/E：2024Q2 30.4 → 2026-11-02 37.7
- `10:48.5` 所以，他卖掉的，是对价格、税和仓位的判断，而不是对这门生意的否定。  
  出处：本片观点

### 卖与不卖

- `10:57.8` 回头看，同样是伟大的企业：可口可乐，他持有38年，一股未卖；苹果，十年之内，卖掉了四分之三。  
  出处：第一期；13F
- `11:09.9` 1998年，可口可乐的市盈率高达约47倍，他没有卖。后来，他在致股东信里承认：我说了，却没有做。  
  出处：KO 1998 10-K；2004 年致股东信：“I talked when I should have walked.”
- `11:20.6` 2024年，苹果的市盈率接近30倍，又占了伯克希尔股票投资的近一半。这一次，他卖了。  
  出处：13F；data/calc.py
- `11:30.0` 比他更早重仓苹果的段永平，也在减持。外界普遍认为由他管理的那只基金，持仓报告显示：苹果从2024年中的约6400万股，减到了2026年中的约2700万股，少了近六成。  
  出处：H&H International 13F：2024-06-30 63,924,255 股 → 2026-06-30 27,098,707 股（−57.6%）；基金归属为媒体报道
- `11:49.4` 2026年7月，他在网上打了个比方：自己的“水果”，已经比较成熟了。卖出的钱，他也买了美国短期国债。  
  出处：澎湃新闻 2026-07-23（香港01 同日报道相同内容）：“我的水果（苹果公司）已经比较成熟了，刚刚被call走了一些（买了t-bill了）”
- `12:02.2` 2025年的股东大会上，巴菲特说：说来有点惭愧，蒂姆·库克为伯克希尔赚的钱，比我为伯克希尔赚的还要多得多。  
  出处：2025 年股东大会
- `12:13.9` 这十年，留下了四条朴素的道理。  
  出处：本片总结
- `12:18.0` 第一，看得懂，才下重注。  
  出处：本片总结
- `12:21.5` 第二，买股票，就是买生意。  
  出处：本片总结
- `12:25.0` 第三，再好的生意，也要看价格。  
  出处：本片总结
- `12:29.0` 第四，仓位和税，都要算进账里。  
  出处：本片总结
- `12:33.6` 至于他卖错了没有：比起是否卖在了最高点，更值得学的，是每一个决定在做出的那一刻，是否算得清、讲得通。  
  出处：本片观点
- `12:45.2` 伟大的企业，值得长期陪伴；但没有任何一只股票，值得不计价格、不计仓位地拥有。  
  出处：全片主题
- `12:54.4` 下期：日本五大商社——巴菲特为什么在东京下注？  
  出处：2020 年致股东信：伯克希尔投资日本五家大型商社

## 3. 屏幕上的原话（只用已核实的文字记录）

- **Warren Buffett · CNBC, Feb 27, 2017**：“When I take a dozen kids, as I do on Sundays out to Dairy Queen they're all holding their Apple, they barely can talk to me except if I'm ordering ice cream or something like that.” 周日我带十几个孩子去冰雪皇后，他们个个拿着苹果，除了我给他们点冰淇淋的时候，几乎顾不上跟我说话。
- **Warren Buffett · Annual Meeting, May 4, 2024**：“But I think the psychologists call this apperceptive mass… big action in the case of Apple.” 我想心理学家管这叫“统觉团”……在苹果上，是一次大行动。
- **Warren Buffett · CNBC, Feb 24, 2020**：“My flip phone is permanently gone.” 我的翻盖手机，永远退役了。
- **Warren Buffett · CNBC, Feb 24, 2020**：“It's probably the best business I know in the world.” 这可能是我所知道的，世界上最好的生意。
- **Warren Buffett · CNBC, Feb 24, 2020**：“I don't think of Apple as a stock. I think of it as our third business.” 我不把苹果当成一只股票，我把它当成我们的第三大生意。
- **Duan Yongping · AP, 2006**：“I learned a lot from Warren Buffett and his philosophy.” 我从巴菲特和他的理念中学到了很多。
- **Warren Buffett · Annual Meeting, May 4, 2024**：“if we didn't have it, people left the store and went to Best Buy or someplace.” 如果我们缺货，顾客就离开，去百思买或者别的店。
- **Warren Buffett · Annual Meeting, May 4, 2024**：“it's one of the great products, maybe the greatest product of all time.” 它是伟大的产品之一，也许是有史以来最伟大的产品。
- **段永平 · 浙江大学讲座，2025-01-05（回忆 2018 年与巴菲特的晚餐）**： “我觉得苹果的生意模式，是比可口可乐要好的。”
- **Duan Yongping · AP, 2006**：“I wanted to find a chance to say thanks to him.” 我只是想找个机会，当面谢谢他。
- **Warren Buffett · CNBC, Feb 27, 2017**：“Apple strikes me as having quite a sticky product and an enormously useful product to people that use it, not that I do” 在我看来，苹果的产品很有黏性，对使用它的人非常有用——虽然我自己不用。
- **Warren Buffett · Annual Meeting, May 5, 2018**：“I love the idea of having our 5 percent, or whatever it may be, grow to 6 or 7 percent without us laying out a dime.” 我很喜欢这样：我们的 5% 不花一分钱，就涨到 6% 或 7%。
- **Warren Buffett · 2021 Chairman's Letter**：“We spent no Berkshire funds to gain our accretion. Apple's repurchases did the job.” 我们没有花伯克希尔一分钱，苹果的回购替我们做到了。
- **Warren Buffett · Annual Meeting, May 6, 2023**：“And if they had to give up a second car or give up their iPhone, they'd give up their second car.” 如果让他们在第二辆车和 iPhone 之间放弃一个，他们会放弃第二辆车。
- **Warren Buffett · Annual Meeting, May 6, 2023**：“It just happens to be a better business than any we own” 它恰好比我们拥有的任何生意都更好。
- **Warren Buffett · Annual Meeting, May 6, 2023**：“having heard me say that, it was a dumb decision.” （2020 年卖出一部分）听我这么说，那是个愚蠢的决定。
- **Warren Buffett · Annual Meeting, May 4, 2024**：“And we are paying a 21% federal rate on the gains we're taking in Apple.” 我们在苹果上实现的收益，要缴 21% 的联邦税。
- **Warren Buffett · Annual Meeting, May 4, 2024**：“But I don't mind at all, under current conditions, building the cash position.” 在当前情况下，我一点也不介意增加现金。
- **Warren Buffett · Annual Meeting, May 4, 2024**：“we will have Apple as our largest investment.” 苹果仍会是我们最大的投资。
- **Warren Buffett · 2024 Chairman's Letter**：“To be precise, Berkshire last year made four payments to the IRS that totaled $26.8 billion.” 确切地说，伯克希尔去年向美国国税局缴了四笔税，合计 268 亿美元。
- **Warren Buffett · Annual Meeting, May 3, 2025**：“I'm somewhat embarrassed to say that Tim Cook has made Berkshire a lot more money than I've ever made Berkshire Hathaway.” 说来有点惭愧：蒂姆·库克为伯克希尔赚的钱，比我自己赚的多得多。
- **Warren Buffett · 2004 Chairman's Letter**：“I talked when I should have walked.” 我只是说了，却没有做。

更完整的核实记录见 `research/meeting_quotes.md`、`research/letters_apple.md`、`research/stories.md`。本片不使用任何 AI 模仿的巴菲特、芒格或段永平的声音；旁白为 Gemini TTS（音色 Charon）。

## 4. 影像素材授权（Wikimedia Commons）

片中照片与视频均为公有领域或知识共享授权素材，已按授权要求署名；画面中另有小字署名。“示意”标注的画面仅表现时代或场景，并非事件现场。

- `apple_5th` — [File:Apple Store - Fifth Avenue (7181848534).jpg](https://commons.wikimedia.org/wiki/File%3AApple_Store_-_Fifth_Avenue_%287181848534%29.jpg) · 作者：Jorge Láscar from Australia · 授权：CC BY 2.0
- `apple_5th_2006` — [File:Apple Store Fifth Avenue New York NY-2006-05-20.jpg](https://commons.wikimedia.org/wiki/File%3AApple_Store_Fifth_Avenue_New_York_NY-2006-05-20.jpg) · 作者：https://www.flickr.com/people/brianoberkirch/ · 授权：CC BY-SA 2.0
- `apple_5th_displays` — [File:Apple Fifth Avenue store displays.jpg](https://commons.wikimedia.org/wiki/File%3AApple_Fifth_Avenue_store_displays.jpg) · 作者：Anders Carlsson · 授权：CC BY 2.0
- `apple_campus2_2016` — [File:Apple Campus 2 1 2016-09-19.jpg](https://commons.wikimedia.org/wiki/File%3AApple_Campus_2_1_2016-09-19.jpg) · 作者：FASTILY · 授权：CC BY-SA 4.0
- `apple_park_aerial` — [File:Apple Park aerial view, June 2024.jpg](https://commons.wikimedia.org/wiki/File%3AApple_Park_aerial_view%2C_June_2024.jpg) · 作者：Nils Huenerfuerst · 授权：CC0
- `apple_park_dusk` — [File:Apple Park dusk aerial.jpg](https://commons.wikimedia.org/wiki/File%3AApple_Park_dusk_aerial.jpg) · 作者：Dicklyon · 授权：CC BY-SA 4.0
- `brk_meeting_2025` — [File:Berkshire Hathaway Annual Meeting 2025.jpg](https://commons.wikimedia.org/wiki/File%3ABerkshire_Hathaway_Annual_Meeting_2025.jpg) · 作者：Good-investing · 授权：CC0
- `buffett_2010` — [File:Warren Buffett Wall Street Money Never Sleeps Premiere, New York City, 2010 (55363166973)-corp.jpg](https://commons.wikimedia.org/wiki/File%3AWarren_Buffett_Wall_Street_Money_Never_Sleeps_Premiere%2C_New_York_City%2C_2010_%2855363166973%29-corp.jpg) · 作者：Anthony Quintano · 授权：CC BY 4.0
- `buffett_2015` — [File:Warren Buffett at the 2015 SelectUSA Investment Summit.jpg](https://commons.wikimedia.org/wiki/File%3AWarren_Buffett_at_the_2015_SelectUSA_Investment_Summit.jpg) · 作者：USA International Trade Administration · 授权：Public domain
- `buffett_ku` — [File:Warren Buffett KU Visit.jpg](https://commons.wikimedia.org/wiki/File%3AWarren_Buffett_KU_Visit.jpg) · 作者：Mark Hirschey · 授权：CC BY-SA 2.0
- `buffett_osu` — [File:Warren Buffett with Fisher College of Business Student - 4395164676.jpg](https://commons.wikimedia.org/wiki/File%3AWarren_Buffett_with_Fisher_College_of_Business_Student_-_4395164676.jpg) · 作者：Aaron Friedman · 授权：CC BY 2.0
- `buffett_osu2` — [File:Warren Buffett with Fisher College of Business Student - 4394391213.jpg](https://commons.wikimedia.org/wiki/File%3AWarren_Buffett_with_Fisher_College_of_Business_Student_-_4394391213.jpg) · 作者：Aaron Friedman · 授权：CC BY 2.0
- `buffett_pitch` — [File:Warren Buffett! He caught a ceremonial first pitch tonight.jpg](https://commons.wikimedia.org/wiki/File%3AWarren_Buffett%21_He_caught_a_ceremonial_first_pitch_tonight.jpg) · 作者：Minda Haas Kuhlmann · 授权：CC BY 2.0
- `cook_2017` — [File:Tim Cook (2017, cropped).jpg](https://commons.wikimedia.org/wiki/File%3ATim_Cook_%282017%2C_cropped%29.jpg) · 作者：Austin Community College · 授权：CC BY 2.0
- `dairy_queen` — [File:Dairy Queen - October 2023 - Sarah Stierch.jpg](https://commons.wikimedia.org/wiki/File%3ADairy_Queen_-_October_2023_-_Sarah_Stierch.jpg) · 作者：Missvain · 授权：CC BY 4.0
- `flip_moto` — [File:Motorola flip phone, closed.jpg](https://commons.wikimedia.org/wiki/File%3AMotorola_flip_phone%2C_closed.jpg) · 作者：Jud McCranie · 授权：CC BY-SA 4.0
- `glide` — [File:Glide Memorial.jpg](https://commons.wikimedia.org/wiki/File%3AGlide_Memorial.jpg) · 作者：Rob Thomas · 授权：CC BY-SA 4.0
- `ibm_chq` — [File:IBM CHQ - Oct 2014.jpg](https://commons.wikimedia.org/wiki/File%3AIBM_CHQ_-_Oct_2014.jpg) · 作者：Treesmittenex · 授权：CC BY-SA 4.0
- `iphone11` — [File:IPhone 11.jpeg](https://commons.wikimedia.org/wiki/File%3AIPhone_11.jpeg) · 作者：Rberchie · 授权：CC BY-SA 4.0
- `iphone7` — [File:Apple iPhone 7 in Apple leather case.jpg](https://commons.wikimedia.org/wiki/File%3AApple_iPhone_7_in_Apple_leather_case.jpg) · 作者：Jiří Sedláček · 授权：CC BY-SA 4.0
- `jobs_2010` — [File:Steve Jobs Headshot 2010-CROP (cropped 2).jpg](https://commons.wikimedia.org/wiki/File%3ASteve_Jobs_Headshot_2010-CROP_%28cropped_2%29.jpg) · 作者：Matthew Yohe (talk) · 授权：CC BY-SA 3.0
- `kiewit` — [File:Kiewit Plaza Omaha.jpg](https://commons.wikimedia.org/wiki/File%3AKiewit_Plaza_Omaha.jpg) · 作者：JonClee86 · 授权：CC BY-SA 3.0
- `nfm_kc` — [File:Nebraska Furniture Mart (KC).jpg](https://commons.wikimedia.org/wiki/File%3ANebraska_Furniture_Mart_%28KC%29.jpg) · 作者：Lectrician2 · 授权：CC BY-SA 4.0
- `omaha_2026` — [File:Omaha Skyline viewed from Harrah's, August 2026.jpg](https://commons.wikimedia.org/wiki/File%3AOmaha_Skyline_viewed_from_Harrah%27s%2C_August_2026.jpg) · 作者：Hurstbergn · 授权：CC0
- `omaha_river` — [File:City of Omaha, Nebraska Skyline on the Missouri River (30899969517) (cropped).jpg](https://commons.wikimedia.org/wiki/File%3ACity_of_Omaha%2C_Nebraska_Skyline_on_the_Missouri_River_%2830899969517%29_%28cropped%29.jpg) · 作者：Tony Webster from Minneapolis, Minnesota, United States · 授权：CC BY 2.0

## 5. 配乐与品牌

- 配乐：Lyria（lyria-3-pro-preview）为本片生成的原创配乐，同一调性与主题动机，经节拍对位剪辑（`src/score.py`）。
- 品牌角标与片尾 logo：仓库 `brand/` 目录官方资产。
