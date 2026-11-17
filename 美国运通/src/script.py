"""第七期《银行赚 13%，它凭什么赚 30%？——巴菲特持有三十年的美国运通》旁白脚本（单一事实来源：字幕 = text，TTS 朗读 = say 或 text）。

每条旁白标注出处（src），口径见 research/核实笔记.md。参考了用户提供的定稿脚本的结构与叙事；
凡无法核实或口径有误的说法，一律按核实笔记更正或删去（核实笔记末尾“参考脚本勘误”）。
大师原话：巴菲特 2026-07-15 CNBC 专访有公开原声，播放真实原声（原速、不改词、不拼接，经语音识别逐句核对），
屏幕同时给出英文原话 + 中文翻译 + 出处；致股东信等文字材料只做屏幕引语卡。
旁白只用豆包刘飞音色，不用 AI 模仿任何真实人物的声音。
say 为 None 且字幕含数字时，朗读文本由 cnnum.to_reading 自动生成（年份逐位读，百分数读“百分之”）；
注意：WT 词锚点要按朗读文本写（例如“二零二五年”而不是“2025 年”）。
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cnnum import to_reading

CHAPTERS = [
    ('hook', None, None),
    ('ch1', '色拉油里的信任', 'TRUST IN A TANK OF OIL'),
    ('ch2', '一个闭环', 'THE CLOSED LOOP'),
    ('ch3', '七百二十二亿的账本', 'READING THE LEDGER'),
    ('ch4', 'Costco 走了以后', 'AFTER COSTCO'),
    ('ch5', '面子与里子', 'STATUS AND SUBSTANCE'),
    ('ch6', '要盯住的四件事', 'WHAT CAN GO WRONG'),
    ('ch7', '三家公司，一个答案', 'ONE ANSWER'),
]

AR = '美国运通 2025 年度报告（含 2025 Form 10-K）'
Q4 = '美国运通 2025 年第四季度财报附表（Exhibit 99.2）'
BRK25 = '伯克希尔 2025 年致股东信（持仓表，截至 2025-12-31）'

# 每条：(id, 章节, 字幕文本, 朗读文本或 None, 情绪提示, 出处)
LINES = [
    # ---------------------------------------------------------------- 开场
    ('h1', 'hook', '2026 年 7 月，95 岁的巴菲特在 CNBC 的专访里，拿美国运通和银行做了一个比较。',
     '二零二六年七月，九十五岁的巴菲特在 CNBC 的专访里，拿美国运通和银行做了一个比较。', '', 'CNBC Squawk Box 2026-07-15 专访（原声见 SOTS open）'),
    ('h2', 'hook', '这句话，他有资格说。伯克希尔对运通的买入，1995 年就基本完成，一共花了大约 13 亿美元。最近二十多年，一股没买，一股没卖。',
     None, '', '2022 年信：“purchases of Amex were essentially completed in 1995 … cost $1.3 billion”；2023 年信：“did not buy or sell a share … well over two decades”'),
    ('h3', 'hook', '运通年年回购自己的股票，伯克希尔不花一分钱，持股比例就涨到了 22.1%。到 2025 年底，这笔投资市值 561 亿美元；光是 2025 年一年的分红，就有 4.79 亿。',
     None, '', BRK25 + '：22.1%，成本 $1,287M，市值 $56,088M，分红 $479M；2022 年信：“repurchases increased Berkshire’s ownership … without any cost to us”'),
    ('h4', 'hook', '同样是发信用卡、借钱给消费者，凭什么银行赚 13%，它能赚 30%？这家做了 175 年生意的公司，护城河在哪里？又有哪些风险，必须盯住？',
     '同样是发信用卡、借钱给消费者，凭什么银行赚百分之十三，它能赚百分之三十？这家做了一百七十五年生意的公司，护城河在哪里？又有哪些风险，必须盯住？',
     '', '巴菲特原声（13%–14% vs 30%+）；运通 1850 年成立（2023 年信）'),

    # ---------------------------------------------------------------- 第一章：色拉油里的信任
    ('c1a', 'ch1', '美国运通 1850 年在纽约成立，最早做的是快运：替人押送货物、现金和贵重物品。1891 年，它推出了旅行支票，出门在外，不用再揣着大把现金。',
     None, '', '2023 年信（“American Express began operations in 1850”）；维基百科 American Express（1891 年推出 Travelers Cheque）'),
    ('c1b', 'ch1', '替人保管钱和货，卖的其实是两个字：信任。1963 年，这份信任差点被一罐色拉油毁掉。',
     None, '', '本片解读；色拉油丑闻见下'),
    ('c1c', 'ch1', '一个叫德安吉利斯的商人，拿仓库里的植物油作抵押，向银行借钱。替他证明“油就在罐里”的，是运通旗下的一家仓储子公司。',
     None, '', '维基百科 Salad oil scandal（引 Miller《The Great Salad Oil Swindle》1965）：American Express Warehousing 开具仓单'),
    ('c1d', 'ch1', '可罐里大多是水，油只浮在上面；有的罐里还有暗格，同一批油在罐子之间挪来挪去，被重复点数。1963 年 11 月骗局败露，贷款人的损失超过 1.8 亿美元。',
     None, '', '维基百科（“hidden compartments … the tanks were otherwise filled with water”；损失超过 $180M；1963-11 Allied 破产）'),
    ('c1e', 'ch1', '仓储子公司破产了。母公司没有撇清关系，主动拿出 6000 万美元和解。运通的股价，从 1963 年 10 月的 65 美元左右，跌到了第二年 1 月的 37 美元左右。',
     None, '', '维基百科（子公司破产；运通代为和解 $60M；股价跌去三分之一以上）；Fortune 2024-09-22、gurufocus（65 → 37）'),
    ('c1f', 'ch1', '华尔街在抛售，33 岁的巴菲特，却去了奥马哈的餐馆。据传记和报道，他想看一件事：丑闻上了报纸，顾客还用不用运通的卡和旅行支票？',
     None, '', 'Fortune 2024-09-22、InvestSmart《Salad oil: the making of Warren Buffett》（走访餐馆等处，观察顾客是否照常使用）；巴菲特生于 1930-08-30，1964 年春买入时 33 岁'),
    ('c1g', 'ch1', '答案是：照用不误。丑闻伤的是公司的钱包，没有伤到顾客的信任。',
     None, '', '同上；“伤的是钱包”为本片概括'),
    ('c1h', 'ch1', '他把合伙基金大约四成的钱，押在了运通上。这是合伙基金有史以来最大的一笔投资。',
     None, '', '1994 年信：“we put about 40% of Buffett Partnership Ltd.’s capital into the stock - the largest investment the partnership had ever made … over 5% ownership … $13 million”'),
    ('c1i', 'ch1', '六十年后，巴菲特在 2023 年的信里，这样写运通：',
     None, '', '2023 年致股东信（引语卡 qtrust）'),
    ('c1j', 'ch1', '那么今天的运通，是怎么把这份信任，变成钱的？',
     None, '', '本片过渡'),

    # ---------------------------------------------------------------- 第二章：一个闭环
    ('c2a', 'ch2', '先看你平时刷的一张 Visa 卡。一笔钱要经过四方：发卡的银行，比如摩根大通，负责借钱给你、承担坏账；Visa 只管清算这条路，不放贷；收单机构替商户收款；最后才是商户。',
     None, '', '四方模式为行业通行结构（运通 10-K Item 1 竞争一节对比 Visa/万事达网络）；本片概括'),
    ('c2b', 'ch2', '四方各赚一段：银行赚利息和年费，Visa 收过路费，收单机构收服务费。谁也拿不到一笔交易的全部。',
     None, '', '本片概括'),
    ('c2c', 'ch2', '运通不一样。它自己发卡，自己有清算网络，还直接和大量商户签约。年报里把这叫作“闭环”：一头连着持卡人，一头连着商户，中间是它自己的网络。',
     None, '', AR + ' 致股东信：“our closed-loop network, which gives us direct relationships with millions of premium Card Members and merchants”'),
    ('c2d', 'ch2', '闭环的好处有两样。一是钱：商户手续费、持卡人年费、贷款利息，都进了同一个口袋。二是数据：谁、在哪家店、花了多少，它看得一清二楚。',
     None, '', '致股东信：“The data the closed loop generates gives us rich insights into our customers’ spending patterns”'),
    ('c2e', 'ch2', '2025 年，运通自己发的卡有 8660 万张，一年刷了 1.67 万亿美元；全球能刷运通卡的地方，超过 1.7 亿个。闭环也不是百分之百：有些卡是别的银行发的，有些小商户由第三方代签。',
     None, '', AR + '：worldwide billed business $1,670B；86.6M proprietary cards；170M+ merchant locations（含第三方收单、支付机构、数字钱包）；第三方发卡 66.2M 张；OptBlue'),
    ('c2f', 'ch2', '这套网络转起来，靠的是一个飞轮。运通说，它的卡平均每张一年的消费额，大约是 Visa 和万事达卡的三倍。',
     None, '', '致股东信：“average annual spending on our Cards approximately three times that of cards on other networks”（注 6：2025 年每卡网络交易额 vs Visa、万事达信用卡/签账卡加权平均）'),
    ('c2g', 'ch2', '花得多的客人，商户舍不得拒绝，所以运通向商户收的手续费，通常比 Visa、万事达高一些。多收的钱，再拿去给持卡人发积分、建贵宾厅，吸引更多花得多的客人。',
     None, '', 'Nilson Report（2016：运通约 2.36%，Visa/万事达信用卡约 2.12%，Practical Ecommerce 转引）；飞轮为本片概括'),

    # ---------------------------------------------------------------- 第三章：七百二十二亿的账本
    ('c3a', 'ch3', '飞轮转出来的钱，写在年报里。2025 年，运通扣除利息支出后的营收，是 722 亿美元。',
     None, '', Q4 + '：total revenues net of interest expense $72,229M'),
    ('c3b', 'ch3', '最大的一块，是向商户收的手续费，374 亿，占一半多；持卡人交的年费，接近 100 亿，增长 18%，已经连续 30 个季度两位数增长；另外还有 75 亿服务费。',
     None, '', Q4 + '：discount revenue $37,401M；net card fees $9,993M（+18%）；service fees and other $7,471M；致股东信（30 个季度）'),
    ('c3c', 'ch3', '真正靠放贷吃利差的净利息收入，是 174 亿，只占四分之一左右。四分之三的收入，跟着刷卡和会员走，不靠放贷利差。',
     None, '', Q4 + '：net interest income $17,364M（24.0%）；非利息收入 $54,865M（76.0%）'),
    ('c3d', 'ch3', '这就是它和银行的分水岭。银行想多赚钱，就得多放贷款；每多放一笔，就要多押一份资本，多担一份坏账的风险。',
     None, '', '本片解读'),
    ('c3e', 'ch3', '看一个更直接的数：每 100 美元资产，一年赚多少钱。2025 年，全美银行业平均是 1.2 美元；运通是 3.8 美元，是银行的三倍多。',
     None, '', 'FDIC Quarterly Banking Profile 2025Q4（全年 ROA 1.20%）；运通：净利润 $10,833M ÷ 平均总资产 $285,757M ≈ 3.8%（本片计算，' + Q4 + '）'),
    ('c3f', 'ch3', '它也没有靠多借钱放大回报：运通每 9 美元资产里，大约有 1 美元是股东自己的钱。2025 年，它的净资产收益率是 33.9%，近三年都在 31% 到 35% 之间。',
     None, '', Q4 + '：股东权益 $33,474M ÷ 总资产 $300,052M ≈ 11%；' + AR + '：ROE 33.9%（2025）、34.6%（2024）、31.5%（2023）'),
    ('c3g', 'ch3', '风险呢？2025 年，全美商业银行的信用卡核销率，在 4% 以上；运通卡贷款的净核销率，是 2.2%，大约只有一半。这就是巴菲特说的：赚得多，风险却不比银行大。',
     None, '', '美联储 FRED CORCCACBS（2025 年四个季度 4.43%、4.18%、4.18%、4.11%）；' + Q4 + '：Card Member loans net write-off rate (principal only) 2.2%'),
    ('c3h', 'ch3', '不过，这些钱不是白来的。2025 年，运通花在积分和持卡人服务上的钱，有 245 亿美元，相当于营收的三分之一。',
     None, '', Q4 + '：Card Member rewards $18,409M + Card Member services $6,057M = $24,466M（÷ $72,229M ≈ 34%）'),
    ('c3i', 'ch3', '剩下的利润，大量还给了股东：2025 年分红加回购，一共 76 亿美元。股票越回购越少，开头说的那 22.1%，就是这么来的。',
     None, '', '致股东信：“we delivered $7.6 billion to our shareholders through dividends and share buybacks”；2022 年伯克希尔信'),

    # ---------------------------------------------------------------- 第四章：Costco 走了以后
    ('c4a', 'ch4', '这台机器，也遇到过大麻烦。麻烦来自上一期的主角：Costco。',
     None, '', '本片过渡'),
    ('c4b', 'ch4', '从 1999 年起，Costco 美国门店只收运通一种信用卡；2004 年起，两家还一起发联名卡。',
     None, '', '维基百科 American Express（引 Bloomberg 2015-10-15：独家协议始于 1999 年；联名卡始于 2004 年）'),
    ('c4c', 'ch4', '2015 年 2 月，运通宣布：这份合作到 2016 年 3 月底结束，不再续约。Costco 联名卡，约占运通全球卡贷款的 20%、发卡量的一成。消息一出，运通股价当天跌了约 6%。',
     None, '', '运通 8-K 2015-02-12；Fortune 2015-02-12；运通声明（“about 20% of worldwide loans and about 10% of worldwide cards in force”）；Motley Fool、Fortune（当日约 −6%）'),
    ('c4d', 'ch4', '为什么谈不拢？据彭博商业周刊报道，Costco 接受运通卡的成本，已经低到每笔约 0.6%；Costco 还希望会员手里的卡，能在更多地方刷。它向别家招标，花旗和 Visa 开出了更好的条件。',
     None, '', 'Bloomberg Businessweek 2015-10-15《How American Express Lost Costco》（0.6%；Costco 招标；Visa 可用范围）'),
    ('c4e', 'ch4', '运通时任 CEO 谢诺后来说，这笔账算不过来。2016 年 6 月，Costco 美国门店改收 Visa，花旗发卡。',
     None, '', 'Kenneth Chenault 2015-03：“The numbers didn’t add up”（Bloomberg、多家报道）；CS Monitor 2016、维基百科（2016-06 改收 Visa，花旗发卡）'),
    ('c4f', 'ch4', '失去 Costco 以后，运通把更多力气放在了收年费的卡上。2018 年接任 CEO 的斯奎里，一次次升级白金卡、金卡的权益，2019 年买下餐厅预订平台 Resy，在机场扩建贵宾厅。',
     None, '', AR + ' 致股东信（“Framework for Winning … in place since 2018”）；Resy 2019 年收购（运通公告、10-K）；“更多力气”为本片概括'),
    ('c4g', 'ch4', '结果写在账本上：年费收入，从 2018 年的 34 亿美元，涨到了 2025 年的近 100 亿，差不多三倍。',
     None, '', '运通 2019 年第四季度财报附表（SEC EX-99.2：2018 年 net card fees $3,441M）；' + Q4 + '（2025 年 $9,993M）'),
    ('c4h', 'ch4', '丢了一个大客户，换来一门更靠会员费的生意。不过这是事后看的结果；当年，谁也不敢打包票。',
     None, '', '本片解读（不作因果断言）'),

    # ---------------------------------------------------------------- 第五章：面子与里子
    ('c5a', 'ch5', '上一期我们说：名气是拉新的矛，商品和价格，才是留存的盾。在运通身上，这两样都看得到。',
     None, '', '第六期第五章结论（本片解读）'),
    ('c5b', 'ch5', '先说矛。上世纪八十年代，坊间一直传说，运通有一张不做广告、只发给顶级富豪的黑卡。运通欧洲的负责人后来承认：传言不是真的，但他们决定，顺势把它做出来。',
     None, '', '维基百科 Centurion Card（引 Snopes：“It wasn’t true, but we decided to capitalize on the idea anyway.”；1988 年《华尔街日报》报道）'),
    ('c5c', 'ch5', '1999 年，百夫长卡正式推出，只能受邀办理。如今据报道，入会费 1 万美元，年费 5000 美元。',
     None, '', '维基百科 Centurion Card（1999）；The Points Guy、One Mile at a Time（现行入会费 $10,000、年费 $5,000，2020 年上调）'),
    ('c5d', 'ch5', '很多人以为，运通是老一辈商界精英的卡。2025 年的年报却显示：全球新增的个人账户里，约 65% 来自千禧一代和 Z 世代；在美国新办的金卡、白金卡里，这个比例约 75%。',
     None, '', AR + ' 致股东信（≈65% 全球新增个人账户；≈75% 美国新办金卡与白金卡）'),
    ('c5e', 'ch5', '新办白金卡的人，平均 33 岁；办金卡的，平均只有 29 岁。',
     None, '', AR + ' 致股东信（“the average age of new customers … Platinum Card and Gold Card in 2025 was 33 and 29”）'),
    ('c5f', 'ch5', '面子，能让人办下第一张卡；第二年还续不续，要看里子：权益，值不值这份年费。',
     None, '', '本片解读（呼应第六期“矛与盾”）'),
    ('c5g', 'ch5', '2025 年 9 月，运通把美国白金卡的年费，从 695 美元提到了 895 美元。运通说，权益加起来超过 3500 美元；但那要把每一项额度都用满，有媒体估算，普通人实际用得上的要少得多。',
     None, '', 'The Points Guy、Fortune 2025-09-19（$695 → $895）；运通发言人（“$3,500 in benefits”，Fortune、Benzinga）；Kudos、Card Savvy 等第三方测算（多数持卡人实际约 $1,500–2,500）'),
    ('c5h', 'ch5', '不少权益，是运通和二十多个合作品牌一起出的。对这些品牌来说，这是花钱接触运通那批花得多的客人。',
     None, '', '致股东信：“partnerships we have with over 20 leading brands with whom we co-create benefits”；后半句为本片解读'),
    ('c5i', 'ch5', '交了几百美元年费，人就会想把它用回来：订酒店、坐飞机、吃饭，尽量都刷这张卡。刷得越多，运通从商户那里收的手续费也越多。',
     None, '', '本片解读；2025 年平均每张自营基础卡年消费 $25,453（' + AR + '）'),
    ('c5j', 'ch5', '2025 年，运通新发了 1250 万张卡，七成以上的新账户是收年费的卡。改版后的白金卡，运通说，表现超出了预期。',
     None, '', AR + ' 致股东信（12.5M new proprietary cards；over 70% on fee-paying products；“The new Platinum Cards have exceeded our expectations”）'),
    ('c5k', 'ch5', '面子把人请进门，里子把人留下来。年费涨得越高，这份里子就得做得越足。',
     None, '', '本片解读'),

    # ---------------------------------------------------------------- 第六章：要盯住的四件事
    ('c6a', 'ch6', '那么，运通是不是一门没有风险的生意？不是。至少有四件事，要盯住。',
     None, '', '本片过渡'),
    ('c6b', 'ch6', '第一，信贷。它不像 Visa 那样完全不放贷：2025 年底，账上的卡贷款和应收账款，有 2139 亿美元。经济一旦衰退，刷卡会变少，坏账会变多。',
     None, '', Q4 + '：Card Member loans and receivables $213,863M'),
    ('c6c', 'ch6', '第二，成本。摩根大通等对手，也在抢高端客人。2025 年，运通花在积分和服务上的钱，增长了 14%，比营收的增速还快。',
     None, '', Q4 + '：rewards + services $24,466M vs $21,381M（+14.4%）；营收 +10%；对手加码高端卡（CNBC 2026 等报道）'),
    ('c6d', 'ch6', '第三，集中度。达美航空一家的联名卡，就占了运通全球刷卡额的约 13%、卡贷款的约 21%；现在的协议，到 2029 年底。',
     None, '', AR + ' 10-K Item 1：“Delta cobrand portfolio … approximately 13 percent of worldwide billed business and approximately 21 percent of worldwide Card Member loans … runs through the end of 2029”'),
    ('c6e', 'ch6', '第四，费率。运通在年报里承认：受理的商户越多，手续费率就越有往下走的压力；各地的监管和诉讼，也在压费率。',
     None, '', AR + ' 10-K 风险因素：“We have also experienced erosion of our merchant discount rates as we increase merchant acceptance.”'),
    ('c6f', 'ch6', '这四件事落到年报上，每年最该看的，是三个数：年费收入还能不能稳定增长；核销率会不会抬头；积分和服务的花费，会不会跑得比收入还快。',
     None, '', '本片解读'),

    # ---------------------------------------------------------------- 第七章：三家公司，一个答案
    ('c7a', 'ch7', '把最近这三期放在一起：喜诗糖果，靠的是顾客愿意多付钱；Costco，把省下来的钱让给会员；美国运通，用信任和闭环，把会员费做成了一门生意。',
     None, '', '第五、六、七期结论（本片解读）'),
    ('c7b', 'ch7', '它们长得完全不同，却有同一个特点：顾客一次又一次地回来，公司不用投太多钱，就能长期赚到很高的回报。',
     None, '', '本片解读'),
    ('c7c', 'ch7', '还是 2026 年那次专访，巴菲特接着说：',
     None, '', 'CNBC 2026-07-15（原声见 SOTS trick，紧接开场那段之后）'),
    ('c7d', 'ch7', '从 1964 年那笔重仓，到今天伯克希尔持有 22.1%，巴菲特看了运通六十年，看的就是这一件事。',
     None, '', '1994 年信；' + BRK25),
]

for _k, _l in enumerate(LINES):                 # 含数字且未手写朗读文本的句子，自动生成读法
    if _l[3] is None and any(c.isdigit() for c in _l[2]):
        _r = re.sub(r'(?<=[\u4e00-\u9fff]) (?=[\u4e00-\u9fff])', '', to_reading(_l[2]))
        _r = re.sub(r'(?<![一二三四五六七八九十零千百万])二(?=[千百])', '两', _r)
        LINES[_k] = (_l[0], _l[1], _l[2], _r, _l[4], _l[5])

DROPPED = {}

# 原声（SOT）。原速、不改词、不拼接；入出点切在自然停顿，经本地语音识别逐句核对（cut_sot.py）。
SOT_SRC = 'CNBC Squawk Box · Becky Quick 专访巴菲特 · 2026-07-15'
SOTS = {
    'open': dict(after='h1', ch='hook', **{'in': 216.05, 'out': 249.7}, span=0.1, who='buffett', src='cnbc', srcname=SOT_SRC, ts='3:36', cuts=[2.5, 12.6, 15.3, 23.45, 26.3],
                 en='But if you take something like American Express, you know, most of the banks earn — 13, 14% on — on capital. If I asked everybody to guess — but American Express, they would come up with some figure similar, but it’s so different that it earns 30% plus on capital and does not incur more risk in doing so than the banks that earn 13 or 14 percent.',
                 ph=[('But if you take something like American Express,', '拿美国运通这样的公司来说，'),
                     ('you know, most of the banks earn — 13, 14% on — on capital.', '大多数银行的资本回报率是百分之十三、十四。'),
                     ('If I asked everybody to guess —', '如果让大家猜一猜，'),
                     ('but American Express, they would come up with some figure similar, but it’s so different', '美国运通，你也会猜个差不多的数，可它完全不同：'),
                     ('that it earns 30% plus on capital', '它的资本回报率在百分之三十以上，'),
                     ('and does not incur more risk in doing so than the banks that earn 13 or 14 percent.', '而它承担的风险，并不比那些只赚百分之十三、十四的银行更大。')]),
    'trick': dict(after='c7c', ch='ch7', **{'in': 249.75, 'out': 259.98}, span=0.1, who='buffett', src='cnbc', srcname=SOT_SRC, ts='4:10', cuts=[4.3],
                  en='The trick in life is to find — I mean, in investing, is to find businesses that are going to earn high returns on capital for an extended period of time.',
                  ph=[('The trick in life is to find — I mean, in investing,', '人生的诀窍在于找到——我是说，在投资上，'),
                      ('is to find businesses that are going to earn high returns on capital for an extended period of time.', '就是找到那些能在很长时间里，持续赚取高资本回报的生意。')]),
}

# 第七期起片尾不再预告下一期（用户要求）：最后一句之后，落版字化作粒子汇聚成品牌 logo。

# 屏幕上出现的原话（英文原句 + 中文翻译 + 出处）
QUOTES = {
    'qtrust': ('the consumption of liquids and the need for unquestioned financial trust are timeless essentials of our world.',
               '人要喝饮料，人也需要毫无疑问的金融信任——这两样，是这个世界永恒的必需品。', 'Warren Buffett · 2023 Letter to Shareholders'),
    'qbpl': ('we put about 40% of Buffett Partnership Ltd.’s capital into the stock - the largest investment the partnership had ever made.',
             '我们把巴菲特合伙基金约 40% 的资本投进了这只股票——这是合伙基金有史以来最大的一笔投资。', 'Warren Buffett · 1994 Letter to Shareholders'),
    'qrip': ('During 2023, we did not buy or sell a share of either AMEX or Coke – extending our own Rip Van Winkle slumber that has now lasted well over two decades.',
             '2023 年，运通和可口可乐，我们一股没买、一股没卖——我们的“瑞普·凡·温克尔式沉睡”，已经持续了二十多年。', 'Warren Buffett · 2023 Letter to Shareholders'),
    'qloop': ('our closed-loop network, which gives us direct relationships with millions of premium Card Members and merchants around the world.',
              '我们的闭环网络，让我们和全世界数以百万计的高端持卡人与商户，建立了直接的联系。', 'Stephen Squeri · American Express 2025 Annual Report'),
    'qnumbers': ('The numbers didn’t add up.', '这笔账，算不过来。', 'Kenneth Chenault, American Express CEO · March 2015'),
    'qrumor': ('It wasn’t true, but we decided to capitalize on the idea anyway.', '传言不是真的，但我们还是决定顺势把它做出来。',
               'American Express Europe executive, to Snopes'),
    'qplat': ('The new Platinum Cards have exceeded our expectations.', '新的白金卡，表现超出了我们的预期。', 'Stephen Squeri · American Express 2025 Annual Report'),
    'qerode': ('We have also experienced erosion of our merchant discount rates as we increase merchant acceptance.',
               '随着受理商户增加，我们的商户折扣率也在受到侵蚀。', 'American Express · 2025 Form 10-K, Risk Factors'),
}
