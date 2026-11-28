"""第二季第二期《全押美国——巴菲特与 BNSF》旁白脚本（单一事实来源：字幕 = text，TTS 朗读 = say 或 text）。

定稿见 视频脚本.md（用户 2026-11-29 确认）；口径见 research/核实笔记.md。
一手来源：伯克希尔历年致股东信与 2025 年年报（Form 10-K）、BNSF 2009-11-03 联合新闻稿（SEC 8-K 附件 99.1）、
联合太平洋 2025 年业绩、美国地面运输委员会（STB）新闻稿。
大师原话：巴菲特真实原声 1 段（CNBC Squawk Box 2026-07-15 专访），原速、不改词、不拼接；其余原话只用屏幕引语卡。
旁白只用豆包刘飞音色，按章整录；开场直接入题（不承接、不报季数期数）；片尾预告下一期（台积电）。
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cnnum import to_reading

TITLE = ('全押美国', '巴菲特与 BNSF')
SEASON = ''
CHAPTERS = [
    ('hook', None, None),
    ('ch1', '恐惧里的报价', 'AN OFFER IN THE GLOOM'),
    ('ch2', '铁路这门生意', 'THE RAILROAD BUSINESS'),
    ('ch3', '护城河', 'THE MOAT'),
    ('ch4', '吃资本的生意', 'RAILROADS EAT CAPITAL'),
    ('ch5', '账怎么算', 'DOING THE MATH'),
    ('ch6', '掉队与变局', 'LAGGING, AND A SHAKE-UP'),
    ('ch7', '带走什么', 'WHAT TO TAKE AWAY'),
]

L = lambda y: f'伯克希尔 {y} 年致股东信'
PR = 'BNSF 与伯克希尔联合新闻稿（2009-11-03，SEC 8-K 附件 99.1）'
K25 = '伯克希尔 2025 年年报（Form 10-K）'

LINES = [
    # ---------------------------------------------------------------- 开场：重建要 5000 亿 → 买价 345 亿 → “哎哟” → 设问
    ('h1', 'hook', '假如要从头修一条铁路：两万三千多英里干线、一万三千多座桥、99 条隧道，横穿美国西部。', None, '', L(2023) + '（“23,759 miles of main track, 99 tunnels, 13,495 bridges”）'),
    ('h2', 'hook', '巴菲特估计，至少要花 5000 亿美元，再修上几十年。', None, '', L(2023) + '（“my guess is that it would cost at least $500 billion to replicate those assets and decades to complete the job”）'),
    ('h3', 'hook', '2010 年，伯克希尔买下了它的全部股权，作价 345 亿美元。', None, '', L(2025) + '（“acquired this iconic business in 2010 with an equity value of $34.5 billion”；含此前已持有的部分）'),
    ('h4', 'hook', '听起来像捡了个天大的便宜。可十几年后，巴菲特在股东信里，为它写下一个词：哎哟。', None, '', L(2023) + '（“Ouch!”）'),
    ('h5', 'hook', '他说，铁路是“吃资本”的生意；伯克希尔从它身上拿到的回报，只能算“可以接受”。', None, '', L(2023) + '（“railroads eat capital”；“an acceptable return on its purchase price”）'),
    ('h6', 'hook', '这家公司叫 BNSF，按货运量算，美国最大的铁路。护城河宽到几乎没人能复制，回报却只是一般。巴菲特为什么还说，买下它，是全押美国经济的未来？', None, '', L(2020) + '（“America’s largest railroad measured by freight volume”）；' + PR + '（“an all-in wager on the economic future of the United States”）'),
    # ---------------------------------------------------------------- 第一章：恐惧里的报价
    ('c1a', 'ch1', '时间回到 2009 年 10 月。金融危机还没过去，经济一片低迷。', None, '', L(2021) + '（“The Great Recession was in full force”）'),
    ('c1b', 'ch1', '那时，伯克希尔已经持有 BNSF 两成多的股票，巴菲特却从没去过它在得州沃斯堡的总部。', None, '', L(2008) + '（持股超过 20%）；' + L(2021) + '（“Despite that large stake, I had never visited the railroad’s headquarters”）'),
    ('c1c', 'ch1', '10 月 22 日，他去见了 CEO 马特·罗斯。不巧，当天晚些时候 BNSF 发布三季报，业绩很难看，市场反应很差。', None, '', L(2021) + '（“our get-together would coincide with BNSF’s third-quarter earnings report … The market reacted badly”）'),
    ('c1d', 'ch1', '第二天，巴菲特又去找他：伯克希尔能给铁路一个比上市公司更好的长久归宿。他还报出了自己愿意出的最高价。', None, '', L(2021) + '（“suggested that Berkshire would offer the railroad a better long-term home than it could expect as a public company. I also told him the maximum price”）'),
    ('c1e', 'ch1', '11 天后，双方宣布交易：每股 100 美元，现金加股票；连同 100 亿美元债务，总价约 440 亿美元，是伯克希尔史上最大的一笔收购。', None, '', L(2021) + '（“Eleven busy days later”）；' + PR + '（$100 per share in cash and stock；“valued at approximately $44 billion, including $10 billion of outstanding BNSF debt”；“the largest acquisition in Berkshire Hathaway history”）'),
    ('c1f', 'ch1', '巴菲特说：美国未来的繁荣，离不开一个高效、维护良好的铁路系统；最重要的是，这是全押美国经济的未来。', None, '', PR + '（“Our country’s future prosperity depends on its having an efficient and well-maintained rail system”；“Most important of all, however, it’s an all-in wager on the economic future of the United States”）'),
    ('c1g', 'ch1', '为了这笔买卖，他卖掉了一些股票，其中就有穆迪；还增发了约 6% 的新股。他说，自己讨厌发新股，就像讨厌做肠镜前的准备。最后他在信里承认：这个决定，很勉强。', None, '', L(2009) + '（“late in the year made other sales in anticipation of our BNSF purchase”；6.1%；“about as much as we relish prepping for a colonoscopy”；“the final decision was a close one”）'),
    # ---------------------------------------------------------------- 第二章：铁路这门生意
    ('c2a', 'ch2', '美国铁路走过 150 多年：疯狂修建、尔虞我诈、过度建设、破产、重组、合并，直到几十年前，才变成一个成熟、理性的行业。', None, '', L(2020) + '（“After 150 years or so of frenzied construction, skullduggery, overbuilding, bankruptcies, reorganizations and mergers, the railroad industry finally emerged a few decades ago as mature and rationalized”）'),
    ('c2b', 'ch2', '今天的 BNSF，是 1995 年由伯灵顿北方和圣太菲两家铁路合并而来，线路超过 3.25 万英里，横跨 28 个州。', None, '', 'BNSF 1995 财年 10-K（1995-09-22 合并生效）；' + K25 + '（over 32,500 route miles of track in 28 states）'),
    ('c2c', 'ch2', '它拉什么？进口集装箱、汽车这样的消费品，建材和化工品，粮食和能源，还有煤。2025 年，它运了约 960 万车货物。', None, '', K25 + '（2025 年 9,622 千车/箱：消费品 5,601、工业品 1,382、农产品与能源 1,421、煤 1,218）'),
    ('c2d', 'ch2', '按吨英里算，美国城市之间的货运，约 15% 走的是 BNSF，比任何一家承运商都多。巴菲特把铁路比作美国经济的循环系统，BNSF 是其中最大的动脉。', None, '', L(2020) + '（“about 15% of all non-local ton-miles … By a significant margin, BNSF’s loads top those of any other carrier”）；' + L(2011) + '（“the circulatory system of our economy. Your railroad is the largest artery”）'),
    ('c2e', 'ch2', '可伯克希尔买得并不早。芒格说，他和巴菲特讨厌铁路股好几十年，直到世界变了，美国剩下四家至关重要的大铁路；他们醒悟得慢，但迟到总比不到好。', None, '', L(2022) + '转述芒格（“Warren and I hated railroad stocks for decades … We were slow to recognize the change, but better late than never.”）'),
    # ---------------------------------------------------------------- 第三章：护城河
    ('c3a', 'ch3', '宽不宽，还是过两关。第一关：优势是不是真的。', None, '', '本片分析框架（两关：优势真实存在、对手难以长期复制）'),
    ('c3b', 'ch3', '铁路最大的对手是卡车。BNSF 用一加仑柴油，能把一吨货运 500 英里；巴菲特说，卡车干同样的活，油耗约是它的四倍。长途运重货，铁路的成本占优。', None, '', L(2013) + '（“carrying a ton of freight about 500 miles on a single gallon of diesel fuel. Trucks taking on the same job guzzle about four times as much fuel”）；' + L(2023) + '（“the most efficient way – measured by cost … Trucking wins for short hauls”）'),
    ('c3c', 'ch3', '2025 年，BNSF 每收 100 美元运费，营业利润约 34.5 美元。', None, '', K25 + '（营业收入 233.50 亿、营业利润 80.55 亿美元，运营比率 65.5%）；' + L(2025) + '（operating margin 34.5%）'),
    ('c3d', 'ch3', '第二关：对手能不能复制。重建它的资产，巴菲特估计要 5000 亿美元、几十年；而在美国西部，BNSF 的铁路对手，主要只有一家：联合太平洋。', None, '', L(2023) + '（重建估计）；' + K25 + '（“BNSF Railway’s primary rail competitor in the Western region of the U.S. is Union Pacific”）'),
    ('c3e', 'ch3', '两关都过了，护城河又宽又真。可问题来了：这么宽的护城河，回报为什么只是一般？', None, '', '本片设问'),
    # ---------------------------------------------------------------- 第四章：吃资本的生意
    ('c4a', 'ch4', '2023 年，巴菲特在信里写道：和大多数美国企业比，铁路“吃资本”。', None, '', L(2023) + '（“compared to most American businesses, railroads eat capital”）'),
    ('c4b', 'ch4', 'BNSF 每年花的钱，要超过折旧，才能维持现有的生意。收购后 14 年，超出折旧的部分累计 220 亿美元，平均每年 15 亿多。他写了一个词：哎哟。', None, '', L(2023) + '（“the outlays in excess of GAAP depreciation charges since our purchase 14 years ago have totaled a staggering $22 billion or more than $1 1/2 billion annually. Ouch!”）'),
    ('c4c', 'ch4', '这意味着，BNSF 交给伯克希尔的分红，常常明显少于账面利润，除非一直加债；而伯克希尔不打算这么做。', None, '', L(2023) + '（“dividends … will regularly fall considerably short of BNSF’s reported earnings unless we regularly increase the railroad’s debt. And that we do not intend to do.”）'),
    ('c4d', 'ch4', '铁路还有别的烦恼：工资谈判可能一路打到总统和国会；作为公共承运人，危险品也必须拉；暴雪和洪水来了，也得照常跑。', None, '', L(2023) + '（“Wage negotiations … can end up in the hands of the President and Congress”；“common carrier”；weather, flooding）'),
    ('c4e', 'ch4', '2014 年，BNSF 服务出了问题，让很多客户失望。第二年，它在线路和设备上砸了约 58 亿美元，差不多是折旧的三倍。', None, '', L(2014) + '（“BNSF disappointed many of its customers”）；' + L(2015) + '（“about $5.8 billion … nearly three times our annual depreciation charge”）'),
    ('c4f', 'ch4', '我们讲日本商社时说过：巴菲特把生意分三等，最好的赚了钱不用再投，第二等要不断投钱才能多赚，比如电力公司。BNSF 就属于第二等；巴菲特在 2009 年就写过，它的经济特性很像电力公司。', None, '', '回顾 · 日本五大商社（伯克希尔 2007 年信“三等生意”）；' + L(2009) + '（“certain important economic characteristics that resemble those of our electric utilities”）'),
    # ---------------------------------------------------------------- 第五章：账怎么算
    ('c5a', 'ch5', '那伯克希尔到底赚没赚钱？巴菲特的答案是两句话：按买价算，回报可以接受；按重建价值算，回报少得可怜。', None, '', L(2023) + '（“an acceptable return on its purchase price, though less than it might appear, and also a pittance on the replacement value of the property”）'),
    ('c5b', 'ch5', '他也说，这正是伯克希尔能在 2010 年，用重建成本的零头买下它的原因。', None, '', L(2023) + '（“It explains why we could buy BNSF in 2010 at a small fraction of its replacement value.”）'),
    ('c5c', 'ch5', '2025 年，BNSF 净利润约 55 亿美元，经营现金流 81 亿，给伯克希尔分红 44 亿。', None, '', K25 + '（净利润 54.76 亿美元）；' + L(2025) + '（“$8.1 billion in net operating cash flows and returned $4.4 billion of that cash to Berkshire through dividends”）'),
    ('c5d', 'ch5', '到 2020 年底，BNSF 已经累计给伯克希尔分红 418 亿美元；加上之后五年平均每年 41 亿，累计约 620 亿，早已超过当年 345 亿美元的股权作价。', None, '', L(2020) + '（“$41.8 billion in total”）；' + L(2025) + '（“its average annual dividend over the past five years was $4.1 billion”）；约 620 亿为本片推算'),
    ('c5e', 'ch5', '2026 年接受专访时，巴菲特还这样说起这条铁路：', None, '', 'CNBC Squawk Box 2026-07-15 专访（原声见 SOTS railroad）'),
    ('c5f', 'ch5', '买在恐慌里，是这笔交易最大的底气。巴菲特在 2009 年的信里写过：恐惧的气氛，是投资者最好的朋友。', None, '', L(2009) + '（“A climate of fear is their best friend.”）'),
    # ---------------------------------------------------------------- 第六章：掉队与变局
    ('c6a', 'ch6', '可是，最宽的护城河，并没有让 BNSF 跑在最前面。2023 年，巴菲特承认：BNSF 运的货、花的资本开支都是北美六大铁路里最多的，利润率却从收购以来，落后于其余五家。', None, '', L(2023) + '（“Though BNSF carries more freight and spends more on capital expenditures than any of the five other major North American railroads, its profit margins have slipped relative to all five since our purchase.”）'),
    ('c6b', 'ch6', '2025 年，BNSF 的营业利润率回升到 34.5%；同一年，联合太平洋的运营比率是 59.8%，换算成利润率约 40%。', None, '', L(2025) + '（34.5%，2024 年 32.0%）；联合太平洋 2025 年全年业绩（报告运营比率 59.8%）'),
    ('c6c', 'ch6', '阿贝尔说，利润率每提高 1 个百分点，每年就多出约 2.3 亿美元经营现金流。照此推算，追平联合太平洋，一年差了约 13 亿美元。', None, '', L(2025) + '（“Each one-percentage-point improvement in operating margin generates approximately $230 million of incremental operating cash flow”）；13 亿为本片推算（约 5.7 个百分点 × 2.3 亿）'),
    ('c6d', 'ch6', '变局也来了：联合太平洋提议合并东部的诺福克南方，组成一条横贯东西海岸的铁路。截至 2026 年 11 月，监管机构还没有批准。', None, '', 'STB 新闻稿 26-02、26-09、26-13；联合太平洋 2026 年三季度 10-Q（交易仍待 STB 审批，预计 2027 年下半年完成）'),
    ('c6e', 'ch6', '伯克希尔表态：不打算收购另一家一级铁路，眼下的价钱对股东不划算；BNSF 要确保客户仍能公平地进入东部市场。', None, '', L(2025) + '（“not interested in acquiring one of the other Class I railroads, since the current economics would not work in our shareholders’ favor … full and competitive access to Eastern rail markets”）'),
    # ---------------------------------------------------------------- 第七章：带走什么 + 下期预告
    ('c7a', 'ch7', '从 BNSF 身上，至少能带走三件事。', None, '', '本片总结'),
    ('c7b', 'ch7', '第一，护城河宽，不等于回报高。要不断砸钱维持的生意，赚来的钱，很大一部分得再投回去。', None, '', '本片解读（' + L(2023) + '）'),
    ('c7c', 'ch7', '第二，好资产也要好价钱。BNSF 的回报能“可以接受”，是因为买在了恐慌里，买在了重建成本的零头上。', None, '', '本片解读（' + L(2009) + '、' + L(2023) + '）'),
    ('c7d', 'ch7', '第三，护城河只挡住对手，不会替你干活。利润率掉了队，就得靠经营一点点追回来。', None, '', '本片解读（' + L(2023) + '、' + L(2025) + '）'),
    ('c7e', 'ch7', '巴菲特说：一百年后，BNSF 仍将是伯克希尔和美国的一项关键资产。全押美国，押的就是这一百年。', None, '', L(2021) + '（“BNSF will be a key asset for Berkshire and our country a century from now”）'),
    ('p1', 'ch7', '同样是重资产、宽护城河的生意，铁路他买下全部，一拿就是十几年；有一家芯片厂，伯克希尔买入后不到一年就清仓了。', None, '', '伯克希尔 2022 年三季度至 2023 年一季度 13F（台积电，买入约 41 亿美元，年底前卖出约 86%，2023 年一季度清仓）；Fortune 2023-04-12、2023-05-16'),
    ('p2', 'ch7', '下一期，我们讲台积电。护城河这么宽，伯克希尔为什么这么快就离场？', None, '', '下期预告（docs/第二季规划.md）'),
]

for _k, _l in enumerate(LINES):                 # 含数字且未手写朗读文本的句子，自动生成读法
    if _l[3] is None and any(c.isdigit() for c in _l[2]):
        _r = re.sub(r'(?<=[一-鿿]) (?=[一-鿿])', '', to_reading(_l[2]))
        _r = re.sub(r'(?<![一二三四五六七八九十零千百万])二(?=[千百])', '两', _r)
        _r = re.sub(r'(?<=[一-鿿A]) (?=[一-鿿A])', '', _r)
        LINES[_k] = (_l[0], _l[1], _l[2], _r, _l[4], _l[5])
    elif _l[3] is None:
        _r = re.sub(r'(?<=[一-鿿A]) (?=[一-鿿A])', '', _l[2])
        if _r != _l[2]: LINES[_k] = (_l[0], _l[1], _l[2], _r, _l[4], _l[5])


for _k, _l in enumerate(LINES):                 # 英文缩写按字母读
    _r = (_l[3] or _l[2]).replace('BNSF', 'B N S F').replace('CEO', 'C E O')
    if _r != (_l[3] or _l[2]): LINES[_k] = (_l[0], _l[1], _l[2], _r, _l[4], _l[5])

DROPPED = {}

SOT_SRC = 'CNBC Squawk Box · Becky Quick 专访巴菲特 · 2026-07-15'
SOTS = {
    'railroad': dict(after='c5e', ch='ch5', **{'in': 91.2, 'out': 95.80}, span=0.03, who='buffett', src='cnbc', srcname=SOT_SRC, ts='1:31',
                     en='We’ve got the Burlington Northern Railroad, which is certainly worth far more money.',
                     ph=[('We’ve got the Burlington Northern Railroad, which is certainly worth far more money.', '我们还有伯灵顿北方铁路，它值的钱肯定（比这笔投资）多得多。')]),
}

QUOTES = {
    'qwager': ('Most important of all, however, it’s an all-in wager on the economic future of the United States.',
               '最重要的是，这是全押美国经济的未来。', 'Warren Buffett · BNSF acquisition press release (Nov 3, 2009)'),
    'qclose': ('But the final decision was a close one.', '但最后这个决定，很勉强。', 'Warren Buffett · 2009 Letter to Shareholders'),
    'qmunger': ('Warren and I hated railroad stocks for decades, but the world changed … We were slow to recognize the change, but better late than never.',
                '我和沃伦讨厌铁路股好几十年，可世界变了……我们醒悟得慢，但迟到总比不到好。', 'Charlie Munger · quoted in the 2022 Letter'),
    'qeat': ('Compared to most American businesses, railroads eat capital.', '和大多数美国企业比，铁路吃资本。', 'Warren Buffett · 2023 Letter to Shareholders'),
    'qreturn': ('Berkshire is receiving an acceptable return on its purchase price … and also a pittance on the replacement value of the property.',
                '按买价算，伯克希尔拿到的回报可以接受……按重建价值算，回报少得可怜。', 'Warren Buffett · 2023 Letter to Shareholders'),
    'qfear': ('A climate of fear is their best friend.', '恐惧的气氛，是（投资者）最好的朋友。', 'Warren Buffett · 2009 Letter to Shareholders'),
    'qslip': ('Its profit margins have slipped relative to all five since our purchase.', '自我们收购以来，它的利润率落后于其余五家。', 'Warren Buffett · 2023 Letter to Shareholders'),
    'qcentury': ('BNSF will be a key asset for Berkshire and our country a century from now.', '一百年后，BNSF 仍将是伯克希尔和美国的一项关键资产。', 'Warren Buffett · 2021 Letter to Shareholders'),
}
