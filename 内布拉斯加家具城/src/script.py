"""第八期《一张支票，换一句话——巴菲特与内布拉斯加家具城》旁白脚本（单一事实来源：字幕 = text，TTS 朗读 = say 或 text）。

每条旁白标注出处（src），口径见 research/核实笔记.md（一手来源：伯克希尔历年致股东信、2013 年年报所附 1983 年收购提议书
与 NFM 1946 年报表原件、伯克希尔 2025 年 10-K）。
大师原话：巴菲特真实原声 3 段（CNBC 2026-07-15 专访 2 段、1994 年股东会 1 段），原速、不改词、不拼接，经语音识别逐句核对；
其余原话（致股东信）只用屏幕引语卡（英文原句 + 中文翻译 + 出处）。
旁白只用豆包刘飞音色，整篇一次合成（docs/旁白一致性与自然衔接.md），不用 AI 模仿任何真实人物的声音。
say 为 None 且字幕含数字时，朗读文本由 cnnum.to_reading 自动生成（年份逐位读，百分数读“百分之”）；
注意：WT 词锚点要按朗读文本写（例如“一九八三年”而不是“1983 年”）。
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cnnum import to_reading

TITLE = ('一张支票，换一句话', '巴菲特与内布拉斯加家具城')
CHAPTERS = [
    ('hook', None, None),
    ('ch1', '对的人', 'THE RIGHT PERSON'),
    ('ch2', '好价钱', 'THE RIGHT TERMS'),
    ('ch3', '好生意', 'A GOOD BUSINESS'),
    ('ch4', '开到隔壁', 'THE STORE NEXT DOOR'),
    ('ch5', '越开越大', 'BIGGER AND BIGGER'),
    ('ch6', '还能好多久', 'HOW LONG?'),
    ('ch7', '带走什么', 'WHAT TO TAKE AWAY'),
]

L83, L84 = '伯克希尔 1983 年致股东信', '伯克希尔 1984 年致股东信'
PROP = '巴菲特 1983-08-30 收购提议书原件（伯克希尔 2013 年年报第 114–115 页）'
K25 = '伯克希尔 2025 年年报（Form 10-K）'
L89 = '伯克希尔 1989 年致股东信'

# 每条：(id, 章节, 字幕文本, 朗读文本或 None, 情绪提示, 出处)
LINES = [
    ('h1', 'hook', '1983 年 8 月 30 日，巴菲特 53 岁生日这天，用一页多纸的提议书，谈下了一家家具店九成的股份，作价 5535 万美元现金。',
     None, '', '伯克希尔 2013 年信（“August 30, 1983 – my birthday … carrying a 1 1⁄4-page purchase proposal”；“Mrs. B was 89 at the time”）；巴菲特 1983-08-30 收购提议书原件（伯克希尔 2013 年年报第 114–115 页）（90%，$55,350,000 cash）'),
    ('h2', 'hook', '没有审计，没有盘点库存，也没有查产权。',
     None, '', '伯克希尔 1984 年致股东信（“NFM had never had an audit and we did not request one; we did not take an inventory nor verify the receivables; we did not check property titles”）'),
    ('h3', 'hook', '卖家，是一位 89 岁、没上过一天学的俄国移民老太太。',
     '卖家，是一位八十九岁、没上过一天学的俄国移民老太太。', '', '伯克希尔 2013 年信（“Mrs. B was 89 at the time”）；伯克希尔 1983 年致股东信（“no formal education”；“to leave Russia for America”）'),
    ('h4', 'hook', '六年后，她却和家人闹翻，辞职出走，在隔壁开了一家新店，跟她亲手创办的家具城抢生意。',
     None, '', '伯克希尔 1989 年信（“quit in May … she has started a new business selling - what else? - carpet and furniture”）；1992 年信（“opened up her own operation next door”）'),
    ('h5', 'hook', '巴菲特是看走了眼，还是看得太准？',
     None, '', '本片设问'),
    ('h6', 'hook', '四十多年后，95 岁的他在一次专访里，说出了答案：',
     '四十多年后，九十五岁的他在一次专访里，说出了答案：', '', 'CNBC Squawk Box 2026-07-15 专访（原声见 SOTS good）'),
    ('h7', 'hook', '好生意，好价钱，对的人。这三样，内布拉斯加家具城全占了。故事，要从这位老太太说起。',
     None, '', '本片概括（呼应原声）'),
    ('c1a', 'ch1', '罗丝·布鲁姆金，大家叫她 B 太太。23 岁那年，她说服边境守卫放行，从俄国去了美国。',
     '罗丝·布鲁姆金，大家叫她B太太。二十三岁那年，她说服边境守卫放行，从俄国去了美国。', '', '伯克希尔 1983 年致股东信（“Mrs. Blumkin, then 23, talked her way past a border guard to leave Russia for America”）'),
    ('c1b', 'ch1', '她没上过一天学，也不会英语，是大女儿每天放学回家，一个词一个词教会她的。',
     None, '', '伯克希尔 1983 年致股东信（“no formal education … knew no English … her older daughter taught her, every evening, the words she had learned in school”）'),
    ('c1c', 'ch1', '她靠卖旧衣服攒钱。1937 年，她拿出 500 美元，在奥马哈开了一家家具店：内布拉斯加家具城，简称 NFM。',
     None, '', '伯克希尔 1983 年致股东信（“In 1937, after many years of selling used clothing, Mrs. Blumkin had saved $500”）；2020 年信（落脚奥马哈）'),
    ('c1d', 'ch1', '没有好地段，没有独家的货，对手都是有钱的老店。她只有一招：卖得便宜。',
     None, '', '伯克希尔 1983 年致股东信（“no locational or product advantage goes up against rich, long-entrenched competition”）；“办法只有一个”为本片概括'),
    ('c1f', 'ch1', '同行坐不住了，逼着厂商不给她供货。她就想方设法从别处进货，照样降价。',
     None, '', '伯克希尔 1983 年致股东信（“pressured furniture and carpet manufacturers not to sell to her. But by various strategies she obtained merchandise and cut prices sharply”）'),
    ('c1g', 'ch1', '她还被告上法庭，理由是她卖得比厂商规定的最低价还低，违反了当时的“公平贸易法”。',
     None, '', '伯克希尔 1983 年致股东信（“hauled into court for violation of Fair Trade laws”）；公平贸易法即转售价格维持法（允许厂商规定最低零售价），本片解释'),
    ('c1h', 'ch1', '她赢了所有官司。有一场审完，法官还从她那儿买走了 1400 美元的地毯。',
     None, '', '伯克希尔 1983 年致股东信（“She not only won all the cases … she sold the judge $1400 worth of carpet”）'),
    ('c1e', 'ch1', '最难的时候，她把自己家里的家具和电器都卖了，按约定一分不少地还了债。',
     None, '', '伯克希尔 1983 年致股东信（“she simply sold the furniture and appliances from her home in order to pay creditors precisely as promised”）'),
    ('c1j', 'ch1', '1945 年底，她唯一的儿子路易从战场回来。他在诺曼底的奥马哈海滩登陆，负过伤，得过紫心勋章。母子俩没日没夜地干。',
     None, '', '伯克希尔 2020 年信（“Louie fought at Normandy’s Omaha Beach … Purple Heart … Battle of the Bulge … sailed home in November 1945 … worked days, nights and weekends”）'),
    ('c1i', 'ch1', '可 1946 年底的账本上，现金只有 50 美元。',
     None, '', 'NFM 1946 年资产负债表原件（伯克希尔 2013 年年报第 116 页：Cash on Hand $50.00；Balance $72,264.41）；2020 年信'),
    ('c1k', 'ch1', 'B 太太把做生意的道理，归成一句话：卖得便宜，说真话。',
     '这位B太太，把做生意的道理，归成一句话：卖得便宜，说真话。', '', '伯克希尔 1984 年致股东信（“Mrs. B boils it down to ‘sell cheap and tell the truth’”；引语卡 qmotto）'),
    ('c2s', 'ch2', '1972 年出版的《超级金钱》里记着：巴菲特指着这家店说，这是门好生意。',
     None, '', '《Supermoney》（Adam Smith，1972），伯克希尔 2013 年信卷首引用：“See that store … That’s a really good business.”'),
    ('c2t', 'ch2', '作者问：那你怎么不买？他说，它是私人公司；又补了一句：说不定哪天，我还是会买。',
     None, '', '同上：“Why don’t you buy it?” … “It’s privately held,” … “I might buy it anyway,” Warren said. “Someday.”'),
    ('c2a', 'ch2', '十一年后，NFM 一年卖出一亿多美元，全靠奥马哈一家店，比全城同行加起来还多。',
     None, '', '伯克希尔 1983 年致股东信（“over $100 million of sales annually out of one 200,000 square-foot store. No other home furnishings store in the country comes close”）；伯克希尔 1983 年致股东信（“sells more furniture, carpets, and appliances than do all Omaha competitors combined”）'),
    ('c2c', 'ch2', '89 岁的 B 太太，为了家族的长远打算，愿意卖了。',
     '八十九岁的B太太，为了家族的长远打算，愿意卖了。', '', '伯克希尔 1983 年致股东信（“for far-sighted family reasons, was willing to sell the business”）；巴菲特 1983-08-30 收购提议书原件（伯克希尔 2013 年年报第 114–115 页）签字页（五位股东各 20%）'),
    ('c2d', 'ch2', '巴菲特的提议书只有一页多：现金买下九成，剩下一成留给路易和他的儿子们，店还由这一家人管。',
     None, '', '巴菲特 1983-08-30 收购提议书原件（伯克希尔 2013 年年报第 114–115 页）（“90% … for $55,350,000 cash. All of the 10% … not sold to Berkshire will be retained by Mr. Louis Blumkin and his sons”）；伯克希尔 1983 年致股东信'),
    ('c2e', 'ch2', '没有投资银行，也没有律师。B 太太一个字没改，五位家人依次签了名。',
     '没有投资银行，也没有律师。B太太一个字没改，五位家人依次签了名。', '', '2013 年信（“without the involvement of investment bankers or lawyers”）；巴菲特 1983-08-30 收购提议书原件（伯克希尔 2013 年年报第 114–115 页）签字页'),
    ('c2f', 'ch2', '店里从没审计过，巴菲特也没要求。他后来写道：',
     None, '', '伯克希尔 1984 年致股东信（“Our evaluation of the integrity of Mrs. B and her family was demonstrated when we purchased 90% of the business: NFM had never had an audit and we did not request one”）；伯克希尔 1984 年致股东信（引语卡 qcheck）'),
    ('c2i', 'ch2', '这个价钱，贵不贵？买下后的第一个完整年度，1984 年，NFM 税前赚了 1450 万美元。',
     None, '', '伯克希尔 1984 年致股东信（利润表：Nebraska Furniture Mart 1984 年税前 $14,511K，100% 口径）'),
    ('c2j', 'ch2', '整家公司作价约 6000 万，只是这一年税前利润的四倍出头。',
     None, '', '2020 年信（“a business worth $60 million”）；1984–1990 年信利润表（税前 $14.5M、12.7M、17.7M、16.8M、18.4M、17.1M、17.2M，合计 $114.5M，本片计算）'),
    ('c2m', 'ch2', '买下之后七年，税前利润加起来，将近这个作价的两倍。',
     None, '', '2020 年信（“a business worth $60 million”）；1984–1990 年信利润表（税前 $14.5M、12.7M、17.7M、16.8M、18.4M、17.1M、17.2M，合计 $114.5M，本片计算）'),
    ('c2l', 'ch2', '好生意，配上合理的价钱。巴菲特说，这个道理，是芒格先想明白的：',
     None, '', '伯克希尔 1989 年致股东信（引语卡 qfair：“It’s far better to buy a wonderful company at a fair price … Charlie understood this early; I was a slow learner.”）'),
    ('c2k', 'ch2', '而对的人，也一直在店里。91 岁的 B 太太，照样每周七天，从开门干到关门。巴菲特说，她一天做的决定，比大多数 CEO 一年做的还多。',
     '而对的人，也一直在店里。九十一岁的B太太，照样每周七天，从开门干到关门。巴菲特说，她一天做的决定，比大多数 CEO 一年做的还多。', '', '伯克希尔 1984 年致股东信（“Mrs. B, Chairman of the Board, is now 91 … at the store seven days a week, from opening to close, and probably makes more decisions in a day than most CEOs do in a year (better ones, too)”）'),
    ('c3z', 'ch3', '巴菲特评估一家公司，总会问自己：假如我有足够的钱和人手，愿不愿意跟它竞争？对 B 太太，他的回答是：',
     '巴菲特评估一家公司，总会问自己：假如我有足够的钱和人手，愿不愿意跟它竞争？对B太太，他的回答是：', '', '伯克希尔 1983 年致股东信（“One question I always ask myself in appraising a business is how I would like … to compete with it.”；引语卡 qgrizzly）'),
    ('c3a', 'ch3', '她凭什么这么难打？巴菲特拿 NFM 和全美最大的独立家具零售商 Levitz 比了一比。',
     None, '', '伯克希尔 1984 年致股东信（“the largest independent specialty retailer of home furnishings in the country, Levitz Furniture”）'),
    ('c3b', 'ch3', 'Levitz 自称比一般家具店便宜，毛利率却有 44.4%。NFM 的毛利率，只有它的一半多一点。',
     None, '', '伯克希尔 1984 年致股东信（Levitz 1984 财年 10-K：“prices … generally lower”；gross margin 44.4%；“The gross margin at NFM is not much more than half of that.”）'),
    ('c3c', 'ch3', '卖得这么便宜还能赚钱，靠的是成本：工资、房租、广告这些费用，Levitz 要花掉销售额的 35.6%，NFM 只花 16.5% 左右。',
     None, '', '伯克希尔 1984 年致股东信（“operating expenses (payroll, occupancy, advertising, etc.) are about 16.5% of sales versus 35.6% at Levitz”）'),
    ('c3d', 'ch3', '成本低，价格就低；价格低，顾客就多；卖得多，进货就能压价，成本又更低。轮子越转越快。',
     None, '', '伯克希尔 1984 年致股东信（“unparalleled efficiency and astute volume purchasing”）；1989 年信（成功公式五条）；飞轮为本片概括'),
    ('c3e', 'ch3', '巴菲特估算，单靠低价，NFM 每年至少替顾客省下 3000 万美元。',
     None, '', '伯克希尔 1984 年致股东信（“saving its customers at least $30 million annually”）'),
    ('c3f', 'ch3', '顾客也愿意跑远路。在得梅因的 20 家家具店里，NFM 人气排第三，可它远在 130 英里外。',
     None, '', '伯克希尔 1990 年信（“NFM was Number 3 in popularity among 20 furniture retailers serving that city … 19 of those retailers are located in Des Moines, whereas our store is 130 miles away”）'),
    ('c3g', 'ch3', 'B 太太有句话：只要你的价钱最低，就算店开在河底，顾客也会找到你。',
     'B太太有句话：只要你的价钱最低，就算店开在河底，顾客也会找到你。', '', '伯克希尔 2003 年信（“If you have the lowest price, customers will find you at the bottom of a river.”）'),
    ('c3h', 'ch3', '连对手都服了。Dillard’s 百货进军奥马哈，别的城市都卖家具，在这儿偏偏不卖。它的董事长说：',
     '连对手都服了。迪拉德百货进军奥马哈，别的城市都卖家具，在这儿偏偏不卖。它的董事长说：', '', '伯克希尔 1988 年信（“In many of its stores, Dillards runs a full furniture department … his new store would not sell furniture”；引语卡 qdillard）'),
    ('c3i', 'ch3', '这条护城河不是专利，也不是名牌，而是一件说起来简单、做起来极难的事：每天、每样东西，都比别人便宜。',
     None, '', '本片解读'),
    ('c4b', 'ch4', '可就连 B 太太自己，也和家人闹翻了。1989 年 5 月，95 岁的她，为了地毯部怎么装修、怎么经营，和家人意见不合，辞职走了。',
     '可就连B太太自己，也和家人闹翻了。一九八九年五月，九十五岁的她，为了地毯部怎么装修、怎么经营，和家人意见不合，辞职走了。', '', '伯克希尔 1989 年信（“quit in May, after disagreeing with other members of the Blumkin family/management about the remodeling and operation of the carpet department”）；B 太太生于 1893-12-03'),
    ('c4c', 'ch4', '这一次，巴菲特站在家人一边：过去三年，店里其他部门的销售涨了 24%，地毯却跌了 17%。',
     None, '', '伯克希尔 1989 年信（“while the store’s other departments increased sales by 24%, carpet sales declined by 17%”）'),
    ('c4d', 'ch4', 'B 太太没有回家养老。几个月后，她在家具城隔壁、自己早年买下的大楼里，开了一家新店，卖的还是地毯和家具。',
     'B太太没有回家养老。几个月后，她在家具城隔壁、自己早年买下的大楼里，开了一家新店，卖的还是地毯和家具。', '', '伯克希尔 1989 年信（“she has started a new business selling - what else? - carpet and furniture”）；1992 年信（“opened up her own operation next door in a large building that she had owned for several years”）'),
    ('c4e', 'ch4', '原来，1983 年那份提议书里，少了一条：竞业禁止。巴菲特后来承认，自己在这一点上不够小心。',
     None, '', '伯克希尔 1992 年信（“having been incautious on this point when she was 89”）'),
    ('c4f', 'ch4', '1992 年底，B 太太把大楼和土地卖给了家具城，自己留下来接着卖地毯，还主动签了竞业禁止协议。那一年，她 99 岁。',
     '一九九二年底，B太太把大楼和土地卖给了家具城，自己留下来接着卖地毯，还主动签了竞业禁止协议。那一年，她九十九岁。', '', '伯克希尔 1992 年信（“Mrs. B decided to sell her building and land to NFM … graciously offered to sign a non-compete agreement … Signing a non-compete at 99”）'),
    ('c4g', 'ch4', '巴菲特说：',
     None, '', '伯克希尔 1992 年信（引语卡 qpartner）'),
    ('c4h', 'ch4', '她一直干到 103 岁，退休后第二年去世，享年 104 岁。',
     None, '', '伯克希尔 2011 年信（“worked until she was 103. (After retiring, she died the next year …)”）；维基百科 Rose Blumkin（1998-08-09 去世）'),
    ('c5z', 'ch5', '1994 年的伯克希尔股东会上，巴菲特介绍旗下的经理人，第一个点到的，就是这一家：',
     '一九九四年的伯克希尔股东会上，巴菲特介绍旗下的经理人，第一个点到的，就是这一家：', '', '1994 年伯克希尔股东会录像，介绍经理人环节（原声见 SOTS blumkins：“First of all, from the Nebraska Furniture Mart … Louie, Ron and Irv Blumkin”）'),
    ('c5a', 'ch5', 'B 太太的孙子罗恩和欧文，把这套打法带出了奥马哈。',
     'B太太的孙子罗恩和欧文，把这套打法带出了奥马哈。', '', '伯克希尔 2011 年信（“Louie’s sons, Ron and Irv, have taken the company to new heights, first opening the Kansas City store and now gearing up for Texas”）'),
    ('c5b', 'ch5', '2003 年，堪萨斯城店开业。店开在人烟稀少的城郊，25 英亩的停车场有时都停不下，成了全美销量最大的家居店。',
     None, '', '伯克希尔 2003 年信（“located in one of the area’s more sparsely populated parts … more than 25 acres of parking, the lot has at times overflowed”；“the country’s largest-volume home-furnishings store”）'),
    ('c5c', 'ch5', '到 2011 年，NFM 的利润创下纪录，是 1983 年的十倍还多。',
     None, '', '伯克希尔 2007 年信（“our Omaha and Kansas City stores each had sales of about $400 million”）；2011 年信（“netting more than ten times what it did in 1983”）'),
    ('c5d', 'ch5', '又过了四年，达拉斯北郊的第三家大店开业，一个屋顶下面，足足 180 万平方英尺。',
     None, '', '伯克希尔 2013 年信（“under one roof, and on a 433-acre site – 1.8 million square feet of retail and supporting warehouse space”）；维基百科（2015-05-07 开业）；足球场按 105×68 米折算（本片换算）'),
    ('c5e', 'ch5', '2020 年，疫情让门店关了六个多星期，三家店照样都创了销售纪录。巴菲特说，全美最大的三家家居店，都是 NFM 的。',
     None, '', '伯克希尔 2020 年信（“NFM now owns the three largest home-furnishings stores in the U.S. Each set a sales record in 2020 … despite the closing of NFM’s stores for more than six weeks”）'),
    ('c5f', 'ch5', '每年股东会那一周，奥马哈店给股东员工价。2016 年那一周，它卖了 4550 万美元，平时一周大约 900 万。',
     None, '', '伯克希尔 2016 年信（“the Omaha store recording one-week volume of $45.5 million”）；2014、2015 年信（“An average week for NFM’s Omaha store is about $9 million”）；1997 年信起（员工折扣）'),
    ('c6z', 'ch6', '可再好的生意，也有对手盯着。还是那次专访，巴菲特说：',
     None, '', 'CNBC Squawk Box 2026-07-15 专访（原声见 SOTS attacks）'),
    ('c6a', 'ch6', 'NFM 还能好多久？至少有三件事，要盯住。',
     None, '', '本片过渡（呼应原声）'),
    ('c6b', 'ch6', '第一，家具是大件，日子一紧，换沙发、换地毯很容易往后推。2024 年，伯克希尔旗下家居零售的收入降了 6.4%。',
     None, '', '伯克希尔 2025 年年报（Form 10-K）（“Revenues of the home furnishings businesses declined 6.4% in 2024 versus 2023, primarily attributable to lower sales volumes and increased price competition”）'),
    ('c6c', 'ch6', '第二，便宜，必须一直便宜下去。巴菲特写过：在零售业，一停下来歇口气，就会失败。如今点几下手机就能比价，这条护城河，得靠每天的效率去守。',
     None, '', '伯克希尔 1995 年信（“Retailing is a tough business … Your competitor is always copying and then topping whatever you do … In retailing, to coast is to fail.”）；比价为本片解读'),
    ('c6e', 'ch6', '第三，这是一门靠人的生意。B 太太的秘诀，是一家人天天守在店里。如今第四代已经进了公司，还能传多少代，谁也不敢打包票。',
     '第三，这是一门靠人的生意。B太太的秘诀，是一家人天天守在店里。如今第四代已经进了公司，还能传多少代，谁也不敢打包票。', '', '伯克希尔 1989 年信（“friendly personalized service with family members on hand at all times”）；2011 年信（“several members of the fourth Blumkin generation have joined NFM”）'),
    ('c6f', 'ch6', '还有一点：伯克希尔不单独公布 NFM 的营收和利润。2025 年年报只说了一句：零售板块里，除了 NFM，其他公司的利润都持平或下降。',
     None, '', '伯克希尔 2025 年年报（Form 10-K）（“With the exception of NFM, our retailing businesses generated flat or lower earnings in 2025 compared to the prior year.”）'),
    ('c7b', 'ch7', '这笔投资最大的回报，也许不在 NFM 本身。巴菲特每进一个陌生的行业，都会问新伙伴一句：家里还有像你们这样的吗？',
     None, '', '伯克希尔 1997 年信（“I always ask our new partners, ‘Are there any more at home like you?’ Upon our purchase of Nebraska Furniture Mart in 1983, therefore, the Blumkin family told me about three outstanding furniture retailers”；引语卡 qmore）'),
    ('c7c', 'ch7', '布鲁姆金一家给他指了路：1995 年的 R.C. Willey，1997 年的 Star Furniture，1999 年的 Jordan’s，一家牵出一家。',
     '布鲁姆金一家给他指了路：一九九五年的 R C Willey，一九九七年的 Star Furniture，一九九九年的 Jordan’s，一家牵出一家。', '', '伯克希尔 1995 年信（“It was Nebraska Furniture Mart’s Irv Blumkin who did the walking around in the case of R.C. Willey, long the leading home furnishings business in Utah”）；伯克希尔 1997 年信（“made a deal in a single, two-hour session”）；1999 年信（“Their invariable answer was the Tatelman brothers of New England and their remarkable furniture business, Jordan’s”）'),
    ('c7e', 'ch7', '据业界媒体估算，这四家家具零售商，2025 年合起来卖了约 33 亿美元。',
     None, '', 'Home News Now 2026-06-22（伯克希尔家居零售板块 2025 年营收约 $3.34B，业界媒体估算）；伯克希尔 1999 年信（“My thanks go to Louie, Ron and Irv Blumkin for getting me started in the furniture business”）'),
    ('c7l', 'ch7', '回头看这笔交易，至少能带走三件事。',
     None, '', '本片总结'),
    ('c7m', 'ch7', '第一，好生意的护城河，可以就是低成本：每天比别人便宜一点，日积月累，就是对手追不上的距离。',
     None, '', '本片解读（1984 年信：营业费用率 16.5% 对 35.6%；1990 年信：130 英里外的顾客）'),
    ('c7n', 'ch7', '第二，好价钱不靠捡便宜：用四倍左右的税前利润，买下一门还在长大的好生意，比便宜买一家平庸的公司强得多。',
     None, '', '本片解读（1984 年信利润表；1989 年信“wonderful company at a fair price”）'),
    ('c7o', 'ch7', '第三，看人比看报表更要紧；可该写进合同的，一条也不能少。',
     None, '', '本片解读（1984 年信：没有审计；1992 年信：竞业禁止“incautious”）'),
    ('c7f', 'ch7', '卖得便宜，说真话。前一句，是这家店的护城河；后一句，是那笔交易的底气。',
     None, '', '本片解读（1990 年信：130 英里外的顾客；1984 年信：不审计）'),
    ('c7g', 'ch7', '一张支票，换一句话。那句话，四十多年来，一直算数。',
     None, '', '本片结语（1984 年信“a check for $55 million and she gave us her word”）'),
]

for _k, _l in enumerate(LINES):                 # 含数字且未手写朗读文本的句子，自动生成读法
    if _l[3] is None and any(c.isdigit() for c in _l[2]):
        _r = re.sub(r'(?<=[一-鿿]) (?=[一-鿿])', '', to_reading(_l[2]))
        _r = re.sub(r'(?<![一二三四五六七八九十零千百万])二(?=[千百])', '两', _r)
        LINES[_k] = (_l[0], _l[1], _l[2], _r.replace('B 太太', 'B太太'), _l[4], _l[5])
    elif _l[3] is None:
        _r = re.sub(r'(?<=[一-鿿]) (?=[一-鿿])', '', _l[2])
        _r = re.sub(r'B 太太', 'B太太', _r)
        if _r != _l[2]: LINES[_k] = (_l[0], _l[1], _l[2], _r, _l[4], _l[5])

DROPPED = {}

# 原声（SOT）：本片暂无可公开下载、可核对的巴菲特谈 B 太太原声（KFF 访谈全文转写无相关段落；C-SPAN 2018 档案为受限资源，不绕过）。
SOT_SRC = 'CNBC Squawk Box · Becky Quick 专访巴菲特 · 2026-07-15'
AGM94 = '1994 年伯克希尔·哈撒韦股东大会（录像转载）'
SOTS = {
    'good': dict(after='h6', ch='hook', **{'in': 117.84, 'out': 123.98}, span=0.0, fade=0.05, who='buffett', src='cnbc', srcname=SOT_SRC, ts='1:58',      # 124.02 起是主持人的“Okay, but you've”（女声基频 190–260 Hz），出点必须在它之前
                 cuts=[2.7],      # 118.36 处的低谷是 important 的 /p/ 闭塞，不是停顿；入点改在 material 与 the 之间
                 en='The important thing is to buy a good business and to buy it on the right terms and they get the right person to run it.',
                 ph=[('The important thing is to buy a good business', '重要的是，买一门好生意，'),
                     ('and to buy it on the right terms and they get the right person to run it.', '价钱要合适，还要找对经营它的人。')]),
    'blumkins': dict(after='c5z', ch='ch5', **{'in': 510.30, 'out': 521.0}, span=0.1, who='buffett94', src='agm94', srcname=AGM94, ts='8:30',
                     cuts=[4.25, 5.55],      # 32.5–34.5s（片源时间）之间是一句听不清的旁白插话，原样保留、屏幕记作“……”，不剪不拼
                     en='First of all, from the Nebraska Furniture Mart … Louie, Ron and Irv Blumkin. I’m not sure who’s here, but would you stand, please, any of the Blumkins that are present?',
                     ph=[('First of all, from the Nebraska Furniture Mart …', '首先，是内布拉斯加家具城的……'),
                         ('Louie, Ron and Irv Blumkin.', '路易、罗恩和欧文·布鲁姆金。'),
                         ('I’m not sure who’s here, but would you stand, please, any of the Blumkins that are present?', '不知道谁来了。布鲁姆金家到场的，请站起来一下好吗？')]),
    'attacks': dict(after='c6z', ch='ch6', **{'in': 676.85, 'out': 687.3}, span=0.08, who='buffett', src='cnbc', srcname=SOT_SRC, ts='11:17',
                    cuts=[1.91, 3.9, 7.45],
                    en='If you have a wonderful business, you are going to be subject to attacks. So it’s not a question of whether it was wonderful yesterday. The question is how long is it going to be wonderful?',
                    ph=[('If you have a wonderful business,', '如果你有一门了不起的生意，'),
                        ('you are going to be subject to attacks.', '就一定会遭到攻击。'),
                        ('So it’s not a question of whether it was wonderful yesterday.', '所以问题不在于它昨天好不好，'),
                        ('The question is how long is it going to be wonderful?', '而在于它还能好多久。')]),
}

# 第七期起片尾不再预告下一期：最后一句之后，落版字化作粒子汇聚成品牌 logo。

# 屏幕上出现的原话（英文原句 + 中文翻译 + 出处）
QUOTES = {
    'qsuper': ('“I might buy it anyway,” Warren said. “Someday.”',
               '“说不定哪天，我还是会买。”巴菲特说。', 'Adam Smith · Supermoney (1972), quoted in the 2013 Letter'),
    'qcheck': ('We gave Mrs. B a check for $55 million and she gave us her word. That made for an even exchange.',
               '我们给了 B 太太一张 5500 万美元的支票，她给了我们一句话。这是一笔公平的交换。', 'Warren Buffett · 1984 Letter to Shareholders'),
    'qmotto': ('Sell cheap and tell the truth.', '卖得便宜，说真话。', 'Mrs. B (Rose Blumkin), quoted in the 1984 Letter'),
    'qword': ('In short, her word was good enough for us.', '一句话：她说的话，对我们来说就够了。', 'Warren Buffett · 1993 Letter to Shareholders'),
    'qgrizzly': ('I’d rather wrestle grizzlies than compete with Mrs. B and her progeny.',
                 '我宁可去和灰熊摔跤，也不愿意和 B 太太一家竞争。', 'Warren Buffett · 1983 Letter to Shareholders'),
    'qriver': ('If you have the lowest price, customers will find you at the bottom of a river.',
               '只要你的价钱最低，就算你在河底，顾客也会找到你。', 'Mrs. B, quoted in the 2003 Letter'),
    'qdillard': ('We don’t want to compete with them. We think they are about the best there is.',
                 '我们不想跟他们竞争。我们觉得，他们差不多是最好的。', 'William Dillard, quoted in the 1988 Letter'),
    'qpartner': ('I have always been a fan of hers, whether she was a partner or a competitor. But believe me, partner is better.',
                 '不管她是合伙人还是对手，我一直是她的粉丝。不过相信我，还是合伙人好。', 'Warren Buffett · 1992 Letter to Shareholders'),
    'qfair': ('It’s far better to buy a wonderful company at a fair price than a fair company at a wonderful price. Charlie understood this early; I was a slow learner.',
              '用合理的价钱买一家了不起的公司，远胜过用便宜的价钱买一家普通的公司。查理很早就懂了，我学得慢。', 'Warren Buffett · 1989 Letter to Shareholders'),
    'qcoast': ('In retailing, to coast is to fail.', '在零售业，一停下来歇口气，就会失败。', 'Warren Buffett · 1995 Letter to Shareholders'),
    'qmore': ('Are there any more at home like you?', '家里还有像你们这样的吗？', 'Warren Buffett · 1997 Letter to Shareholders'),
}
