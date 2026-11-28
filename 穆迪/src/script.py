"""第二季第一期《不情愿的顾客——巴菲特与穆迪》旁白脚本（单一事实来源：字幕 = text，TTS 朗读 = say 或 text）。

每条旁白标注出处（src），口径见 research/核实笔记.md（一手来源：伯克希尔历年致股东信与 2025 年年报、穆迪 2025 年业绩新闻稿、
SEC 评级办公室 2025 年 1 月 NRSRO 年度报告、金融危机调查委员会（FCIC）最终报告与 2010-05-26 访谈巴菲特录音、美国司法部 2017 年新闻稿）。
大师原话：巴菲特真实原声（FCIC 工作人员访谈录音，2011 年公开），原速、不改词、不拼接，经语音识别逐句核对；
其余原话只用屏幕引语卡（英文原句 + 中文翻译 + 出处）。
旁白只用豆包刘飞音色，按章整录（docs/旁白一致性与自然衔接.md），不用 AI 模仿任何真实人物的声音。
第二季起：开场承接上一期（第一季美国运通），片尾预告下一期（BNSF）；和第一季有关联处做简短回顾（屏幕标「第一季 · 某期」）。
say 为 None 且字幕含数字时，朗读文本由 cnnum.to_reading 自动生成（年份逐位读，百分数读“百分之”）；
注意：WT 词锚点要按朗读文本写（例如“一九零九年”而不是“1909 年”）。
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cnnum import to_reading

TITLE = ('不情愿的顾客', '巴菲特与穆迪')
SEASON = '第二季 · 第 1 期'
CHAPTERS = [
    ('hook', None, None),
    ('ch1', '打分的生意', 'THE RATING BUSINESS'),
    ('ch2', '他看中了什么', 'WHAT HE SAW'),
    ('ch3', '护城河', 'THE MOAT'),
    ('ch4', '关键齿轮', 'ESSENTIAL COGS'),
    ('ch5', '信誉崩了，生意还在', 'THE MOAT HELD'),
    ('ch6', '还能好多久', 'WHAT TO WATCH'),
    ('ch7', '带走什么', 'WHAT TO TAKE AWAY'),
]

FCIC = 'FCIC 工作人员访谈巴菲特录音（2010-05-26，2011 年公开；逐字稿 Santangel’s Review 整理）'
FCR = '金融危机调查委员会（FCIC）最终报告“结论”第 xxv 页（2011）'
MCO25 = '穆迪 2025 年四季度及全年业绩新闻稿（2026-02-18，8-K 附件 99.1）'
SEC25 = 'SEC 评级办公室 NRSRO 年度报告（2025 年 1 月）'
L25 = '伯克希尔 2025 年致股东信 / 年报第 15 页持股表（2025-12-31）'
DOJ = '美国司法部新闻稿 17-070（2017-01-13，穆迪和解）'

# 每条：(id, 章节, 字幕文本, 朗读文本或 None, 情绪提示, 出处)
LINES = [
    # ---------------------------------------------------------------- 开场：承接第一季 → 冲突 → 设问
    ('h1', 'hook', '第一季最后一期，我们讲了美国运通：信任，可以做成一门好生意。',
     None, '', '第一季 · 美国运通（本片回顾）'),
    ('h2', 'hook', '第二季第一期，这家公司的生意更直接：给别人的信用打分。',
     None, '', '本片过渡'),
    ('h3', 'hook', '2000 年到 2007 年，它给近 4.5 万只房贷证券，打了最高的三A。而到 2010 年初，全美国拿到三A 的私营公司，只有 6 家。',
     None, '', FCR + '（“From 2000 to 2007, Moody’s rated nearly 45,000 mortgage-related securities as triple-A. This compares with six private-sector companies in the United States that carried this coveted rating in early 2010.”）'),
    ('h4', 'hook', '2006 年评为三A 的那批房贷证券，最后 83% 被下调。危机调查委员会说，评级机构是这场金融破坏的“关键齿轮”。',
     None, '', FCR + '（“83% of the mortgage securities rated triple-A that year ultimately were downgraded”；“essential cogs in the wheel of financial destruction”）'),
    ('h5', 'hook', '2017 年，它付了近 8.64 亿美元，和美国司法部、21 个州及华盛顿特区和解。',
     None, '', DOJ + '（“nearly $864 million settlement … the Department, 21 states and the District of Columbia”）'),
    ('h6', 'hook', '照理说，信誉扫地的评级公司，生意也该完了。',
     None, '', '本片设问'),
    ('h7', 'hook', '可是到了 2025 年，它的评级业务每收 100 美元，调整后的营业利润有将近 64 美元。',
     None, '', MCO25 + '（MIS 调整后营业利润率 63.6%）'),
    ('h8', 'hook', '伯克希尔新任 CEO 阿贝尔在他的第一封股东信里，把它和苹果、美国运通、可口可乐一起点了名。',
     None, '', L25 + '（“a small number of American companies such as Apple, American Express, Coca-Cola, and Moody’s – businesses we understand well … expect will compound over decades”；署名 Gregory E. Abel）'),
    ('h9', 'hook', '这家公司，叫穆迪。信誉崩了，生意却没丢，凭什么？',
     None, '', '本片设问'),

    # ---------------------------------------------------------------- 第一章：打分的生意
    ('c1a', 'ch1', '1909 年，一个叫约翰·穆迪的人，出了一本铁路证券手册，第一次用字母等级，给近 1300 只铁路债券打分。',
     None, '', 'Imperial College Business School《Credit ratings: where they come from and why they matter》；Wilson（2011）Financial History Review；NBER 工作论文（1909 年 4 月，铁路债券，近 1300 只）'),
    ('c1b', 'ch1', '那时候，铁路是美国最大的发债人。普通人看不懂铁路公司的账，一个字母，就替他们省了功夫。',
     None, '', '同上（铁路是当时主要发债人）；“省了功夫”为本片解读'),
    ('c1c', 'ch1', '后来有了标普和惠誉，字母越分越细：三A 最稳，往下是双A、A、三B；再往下，就是投机级，俗称垃圾债。',
     '后来有了标普和惠誉，字母越分越细：三A最稳，往下是双A、A、三B；再往下，就是投机级，俗称垃圾债。', '', 'Poor’s 1916 年、Fitch 1924 年开始出售评级（同上）；评级符号为本片解释（穆迪写作 Aaa、Aa、A、Baa）'),
    ('c1d', 'ch1', '一开始，评级是卖给投资人的，谁想看谁买手册。大约 1970 年代初，规矩倒了过来：发债的公司付钱，请评级机构给自己打分。',
     None, '', 'Lawrence J. White，Mercatus 政策简报《A Brief History of Credit Rating Agencies》；White 2009 年参议院证词（约 1970 年代初由投资者付费转为发行人付费）'),
    ('c1e', 'ch1', '1975 年，美国证监会在监管规则里，认定了“全国认可”的评级机构。从此，监管规则开始直接引用这几家的评级。',
     None, '', '同上（1975 年 SEC 券商净资本规则引入 NRSRO，原有三家直接获认可）'),
    ('c1f', 'ch1', '今天的穆迪，有两块生意。一块是评级，2025 年对外收入 41 亿美元；另一块是数据和分析软件，36 亿美元，九成以上是订阅收入。',
     None, '', MCO25 + '（MIS 对外营收 41.19 亿美元，MA 对外营收 35.99 亿美元，MA 经常性收入占 96%）'),
    ('c1g', 'ch1', '评级的收入，三分之二来自新债的首次评级。发债多的年份就赚得多，这一点，后面还会说到。',
     None, '', MCO25 + '（表 6：MIS 交易性收入 27.41 亿，占 67%）'),

    # ---------------------------------------------------------------- 第二章：他看中了什么
    ('c2a', 'ch2', '伯克希尔是怎么拿到穆迪的？1999 年和 2000 年初，它买入了邓白氏公司的股票。',
     None, '', FCIC + '（“in 1999 and in February of 2000 you invested in Dun and Bradstreet.” “That’s correct.”）'),
    ('c2b', 'ch2', '2000 年 9 月底，邓白氏一拆为二：新邓白氏独立出去，原来的公司改名叫穆迪。伯克希尔手里，就有了穆迪约 15% 的股份。',
     None, '', '邓白氏 2000 年 10-K405（2000-09-30 完成分拆，原公司更名为 Moody’s Corporation）；伯克希尔 2008 年信（“We purchased 15% of Moody’s some years ago and have not since bought a share.”）'),
    ('c2c', 'ch2', '十年后，危机调查委员会问他：买之前，你和团队做了哪些尽职调查？他说，没有团队，分析都是他自己做的，也没见过任何人。',
     None, '', FCIC + '（“There is no staff. I make all the investment decisions and I do all my own analysis … And I never met with anybody.”）'),
    ('c2d', 'ch2', '他看的，是这门生意的经济特性。他说：',
     None, '', FCIC + '（“it was an evaluation … of the economics of their business”）；原声见 SOTS pricing'),
    ('c2e', 'ch2', '第一季讲喜诗糖果时说过：定价权，来自顾客的喜爱。',
     None, '', '第一季 · 喜诗糖果（本片回顾：“定价权来自顾客的喜爱”）'),
    ('c2f', 'ch2', '穆迪的定价权，来路不一样。伯克希尔旗下的公司发债，也要找穆迪评级。巴菲特说，这门生意他是从两边看的：',
     None, '', FCIC + '（“we’re a customer of Moody’s too so I see this from both sides”）；原声见 SOTS unwilling'),
    ('c2g', 'ch2', '顾客不情愿，却离不开。这样的生意，管理层要紧吗？巴菲特说，他不认识穆迪的管理层；非凡的生意，不需要很好的管理。',
     None, '', FCIC + '（“I’m not making any reference to Moody’s management, I didn’t know them”；“the extraordinary business does not require good management”；引语卡 qmgmt）'),
    ('c2h', 'ch2', '他从没进过穆迪的办公室，没主动打过一个电话，也没要过一个董事席位。',
     None, '', FCIC + '（“I’d never been in Moody’s offices. I don’t think I’ve ever initiated a call to them.”；“Have you pressed for the election of any Board members … No, I have no interest in it.”）'),

    # ---------------------------------------------------------------- 第三章：护城河（两关）
    ('c3a', 'ch3', '顾客离不开，算不算护城河？还是用同一套标准，过两关：第一，优势是不是真的；第二，对手能不能长期学会。',
     None, '', '本片分析框架（与第一季、内布拉斯加家具城一期相同的两关标准）'),
    ('c3b', 'ch3', '先看第一关。美国证监会登记的评级机构，一共 10 家。可到 2023 年底，所有有效的评级里，标普、穆迪、惠誉三家占了 94%；收入，占了 92%。',
     None, '', SEC25 + '（截至 2024-12-31 共 10 家 NRSRO；Chart 3：截至 2023-12-31 三家合计占存续评级 94.15%；Chart 12：2023 财年三家占收入 91.9%）'),
    ('c3c', 'ch3', '赚钱的本事也是真的。巴菲特说，穆迪的有形资产回报，“几乎是无穷大”。',
     None, '', FCIC + '（“huge returns on tangible assets, almost infinite”）'),
    ('c3d', 'ch3', '再看第二关：为什么学不来？怪就怪在，付钱的是发债公司，可评级值不值钱，是买债的人说了算。',
     None, '', '本片解读（依据 SEC25 第 35 页“investor acceptance”一段）'),
    ('c3e', 'ch3', '基金和养老金的投资规定，债券指数的入选规则，常常点名要这三家的评级。发债公司找别家打分，债就不好卖。',
     None, '', SEC25 + '第 35–36 页（“it is common for these types of contracts and guidelines to require the use of ratings of specified NRSROs … many of these guidelines refer to the ratings from the large NRSROs by name”；指数入选规则）'),
    ('c3f', 'ch3', '美国证监会自己的报告也承认：这一行的进入壁垒，至今还在。巴菲特说得更直白：',
     None, '', SEC25 + '第 35 页（“Barriers to entry continue to exist in the credit ratings industry”）；原声见 SOTS duopoly'),
    ('c3g', 'ch3', '在别的行业，降价能抢来顾客；在这一行，降一半价，也换不来信任。护城河不在一纸牌照，而在几十年攒下的“大家都认它”。巴菲特也承认，监管拿它们当标准，帮了大忙。',
     None, '', '本片解读；' + FCIC + '（“it’s assisted by the fact that the two of them became the standard for regulators … So it’s been assisted by the governmental actions over time.”）'),

    # ---------------------------------------------------------------- 第四章：关键齿轮
    ('c4a', 'ch4', '可正是这份“大家都认它”，差点让它栽了大跟头。',
     None, '', '本片过渡'),
    ('c4b', 'ch4', '本世纪初，美国房价连年上涨。华尔街把成千上万笔房贷打包成证券，再请评级机构打分。拿到三A，这些证券才好卖。',
     None, '', FCR + '（“The mortgage-related securities at the heart of the crisis could not have been marketed and sold without their seal of approval.”）'),
    ('c4c', 'ch4', '光是 2006 年，穆迪每个工作日，就给 30 只房贷证券评三A。',
     None, '', FCR + '（“In 2006 alone, Moody’s put its triple-A stamp of approval on 30 mortgage-related securities every working day.”）'),
    ('c4d', 'ch4', '委员会列出了它出错的原因：模型有缺陷，一心抢市场份额，付钱请它评级的金融公司施加压力，监管也形同虚设。',
     None, '', FCR + '（“the flawed computer models, the pressure from financial firms that paid for the ratings, the relentless drive for market share … the absence of meaningful public oversight”）'),
    ('c4e', 'ch4', '巴菲特当时仍是穆迪的大股东。他认为评级机构有责任，可掉进同一个错觉的，不只是它们：',
     None, '', FCIC + '（“I think every aspect of society contributed to it virtually. But they fell prey to the same delusion”）；原声见 SOTS delusion'),
    ('c4f', 'ch4', '2007 年夏天起，穆迪和标普大批下调评级。穆迪的股价，从 2007 年 2 月最高的 76 美元，跌到 2009 年 3 月最低的 15.6 美元，跌了约八成。',
     None, '', FCIC + '（访谈人：“both Moody’s and S&P downgraded securities en masse in July of 2007”）；雅虎财经 MCO 月线（2007-02 最高 76.09，2009-03 最低 15.57）'),
    ('c4g', 'ch4', '2010 年，美国通过多德-弗兰克法案，要求监管机构把规则里引用评级的地方删掉。开头说的那笔和解里，穆迪也承认了关键事实。',
     None, '', '多德-弗兰克法案第 939A 条（SEC 规则文件）；' + DOJ + '（“a Statement of Facts in which Moody’s acknowledges key aspects of its conduct”）'),

    # ---------------------------------------------------------------- 第五章：信誉崩了，生意还在
    ('c5a', 'ch5', '信誉受了重创，罚款交了，规矩也改了。顾客跑了吗？',
     None, '', '本片设问'),
    ('c5b', 'ch5', '没有。三家大机构的收入份额，2020 年是 94%，2023 年是 92%，只降了两个百分点。',
     None, '', SEC25 + ' Chart 12（Large NRSROs：2020 年 94.1%，2023 年 91.9%）'),
    ('c5c', 'ch5', '中型评级机构的份额，从 5.1% 涨到 6.7%，在追，可大局没变。',
     None, '', SEC25 + ' Chart 12（Medium NRSROs：2020 年 5.1%，2023 年 6.7%）'),
    ('c5d', 'ch5', '第一季可口可乐那期，列过几种让长期持有失败的情况，其中一种，是护城河被攻破。穆迪的信誉被攻破了，护城河却还在。',
     None, '', '第一季 · 可口可乐（本片回顾：“买得太贵、借钱被迫卖出、恐慌中离场，或者护城河被攻破”）；本片解读'),
    ('c5e', 'ch5', '那伯克希尔呢？2009 年，它卖掉了一部分穆迪。股东信里写了原因：年初为买陶氏化学和瑞士再保险筹钱，年底为一笔大收购筹钱。',
     None, '', '伯克希尔 2009 年信（“In 2009, our largest sales were in ConocoPhillips, Moody’s … We made some sales early in 2009 to raise cash for our Dow and Swiss Re purchases and late in the year made other sales in anticipation of our BNSF purchase.”）'),
    ('c5f', 'ch5', '2010 年，巴菲特对调查委员会说：',
     None, '', FCIC + '；原声见 SOTS mistake'),
    ('c5g', 'ch5', '他说的错，是股价涨到很高时没卖。到 2013 年，持股降到 2467 万股，此后一股没动。',
     None, '', FCIC + '（“it got to very lofty heights and we didn’t sell”）；伯克希尔 2013 年信持股表（24,669,778 股）；2025 年持股表股数相同'),
    ('c5h', 'ch5', '穆迪年年回购股票，伯克希尔没花一分钱，持股比例就从 2013 年的 11.5%，升到了 2025 年的 13.9%。第一季苹果那期讲过：回购，替股东增持。',
     None, '', '伯克希尔 2013 年信持股表（11.5%）；' + L25 + '（13.9%）；第一季 · 苹果（本片回顾：“苹果的回购替我们做到了”）'),
    ('c5i', 'ch5', '2025 年底，这部分持股的成本是 2.48 亿美元，市值 126 亿，约 51 倍。光是 2025 年一年的分红，就有 9300 万美元。',
     None, '', L25 + '（成本 248、市值 12,603、2025 年分红 93，单位百万美元）；51 倍为本片推算（不含已卖出部分与历年分红）'),

    # ---------------------------------------------------------------- 第六章：还能好多久
    ('c6a', 'ch6', '这条护城河，还能守多久？有三件事要盯住。',
     None, '', '本片过渡'),
    ('c6b', 'ch6', '第一，利益冲突没有变。今天，仍然是发债的公司付钱，请它打分。危机调查委员会点过的问题，模式还在。',
     None, '', FCR + '（“the pressure from financial firms that paid for the ratings”）；发行人付费模式至今未变（' + SEC25 + '）'),
    ('c6c', 'ch6', '第二，周期。评级收入三分之二靠新发债，利率一涨、市场一冷，收入就会掉。好在数据和分析那一半生意，九成以上是订阅，算是一层缓冲。',
     None, '', MCO25 + '（MIS 交易性收入占 67%；MA 经常性收入占 96%）；周期影响为本片解读'),
    ('c6d', 'ch6', '第三，监管和对手。巴菲特 2010 年就说过，双寡头的格局“可能会变”。规则在改，中型机构也在追。',
     None, '', FCIC + '（“It’s a natural duopoly to some extent, now that may get changed”）；' + SEC25 + ' Chart 12'),

    # ---------------------------------------------------------------- 第七章：带走什么 + 下期预告
    ('c7a', 'ch7', '从穆迪身上，至少能带走三件事。',
     None, '', '本片总结'),
    ('c7b', 'ch7', '第一，定价权不一定来自喜爱。喜诗靠顾客喜欢，穆迪靠的是顾客离不开。',
     None, '', '本片解读（第一季 · 喜诗糖果；FCIC 访谈“unwilling customer”）'),
    ('c7c', 'ch7', '第二，护城河保护的是生意，不分对错。犯了大错，顾客照样离不开，这也正是监管要一直盯着它的原因。',
     None, '', '本片解读（SEC25 Chart 12；多德-弗兰克法案第 939A 条）'),
    ('c7d', 'ch7', '第三，伟大的公司，股价也会跌掉八成。巴菲特说没卖是个错；可留下的那一半，二十多年后涨到了约 51 倍。',
     None, '', '本片解读（MCO 月线；FCIC 访谈；' + L25 + '）'),
    ('c7e', 'ch7', '不情愿的顾客，也是顾客。这门生意的护城河，就建在“没得选”三个字上。',
     None, '', '本片结语（FCIC 访谈“an unwilling customer, but we’re a customer nevertheless”）'),
    ('p1', 'ch7', '最后留个线索：穆迪最早打分的，是铁路债券；2009 年伯克希尔卖掉一部分穆迪，有一部分钱，是为了买下一家铁路公司。',
     None, '', '1909 年铁路债券评级（同 c1a 出处）；伯克希尔 2009 年信（“in anticipation of our BNSF purchase”）'),
    ('p2', 'ch7', '下一期，我们就讲这家铁路公司：BNSF。护城河最宽的生意，为什么回报却很一般？巴菲特又为什么说，买下它，是押注美国的未来？',
     '下一期，我们就讲这家铁路公司：B N S F。护城河最宽的生意，为什么回报却很一般？巴菲特又为什么说，买下它，是押注美国的未来？', '', '下期预告（第二季片单，docs/第二季规划.md）；“押注美国的未来”出处待 BNSF 一期核实笔记确认后定稿'),
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

DROPPED = {}

# 原声（SOT）：FCIC 工作人员访谈巴菲特录音（只有声音，画面用照片 + 声波）。入出点按本地语音识别（research/raw/fcic_asr_*.txt）定位，
# 再在附近找能量最低的切点；原速、不改词、不拼接；出点单独核查最后 1.5 秒（访谈人是另一个男声，靠识别文字核对）。
SOT_SRC = 'FCIC 工作人员访谈巴菲特录音 · 2010-05-26（2011 年公开）'
SOTS = {
    'pricing': dict(after='c2d', ch='ch2', **{'in': 165.3, 'out': 184.66}, span=0.08, who='buffett', src='fcic', srcname=SOT_SRC, ts='2:45', cuts=[5.9, 11.7, 15.45],
                    en='The single most important decision in evaluating a business is pricing power. You’ve got the power to raise prices without losing business to a competitor, and you’ve got a very good business. And if you have to have a prayer session before raising the price by a tenth of a cent, then you’ve got a terrible business. I’ve been in both and I know the difference.',
                    ph=[('The single most important decision in evaluating a business is pricing power.', '评估一门生意，最重要的一点，是定价权。'),
                        ('You’ve got the power to raise prices without losing business to a competitor, and you’ve got a very good business.', '能涨价，又不会把生意丢给对手，那就是很好的生意。'),
                        ('And if you have to have a prayer session before raising the price by a tenth of a cent,', '要是涨价一分钱的十分之一，都得先开个祈祷会，'),
                        ('then you’ve got a terrible business. I’ve been in both and I know the difference.', '那就是糟糕的生意。两种我都做过，知道差别在哪。')]),
    'unwilling': dict(after='c2f', ch='ch2', **{'in': 293.13, 'out': 308.1}, span=0.08, who='buffett', src='fcic', srcname=SOT_SRC, ts='4:53', cuts=[4.2, 8.6],
                      en='We’re both — we’re a customer of Moody’s too, so I see this from both sides — an unwilling customer, but we’re a customer nevertheless. And what I see as a customer is reflected in what’s happened in their financial record.',
                      ph=[('We’re both — we’re a customer of Moody’s too, so I see this from both sides —', '我们也是穆迪的顾客，所以两边我都看得到：'),
                          ('an unwilling customer, but we’re a customer nevertheless.', '是不情愿的顾客，但终归是顾客。'),
                          ('And what I see as a customer is reflected in what’s happened in their financial record.', '我作为顾客看到的，都写在它的财务记录里。')]),
    'duopoly': dict(after='c3f', ch='ch3', **{'in': 468.3, 'out': 492.8}, span=0.08, who='buffett', src='fcic', srcname=SOT_SRC, ts='7:48', cuts=[6.0, 10.1, 14.8, 18.9],
                    en='There are very few businesses that had the competitive position that Moody’s and Standard and Poor’s had, they both had the same position essentially. Very few businesses like that in the world. It’s a natural duopoly to some extent. Now that may get changed, but it’s historically been a natural duopoly where anybody coming in and offering to cut their price in half had no chance of success.',
                    ph=[('There are very few businesses that had the competitive position that Moody’s and Standard and Poor’s had,', '很少有生意，拥有穆迪和标普那样的竞争地位，'),
                        ('they both had the same position essentially. Very few businesses like that in the world.', '它们俩的地位基本一样。这样的生意，世上少有。'),('It’s a natural duopoly to some extent. Now that may get changed,', '某种程度上，这是天然的双寡头。现在可能会变，'),
                        ('but it’s historically been a natural duopoly', '但从历史上看，它一直是天然的双寡头：'),
                        ('where anybody coming in and offering to cut their price in half had no chance of success.', '谁进来报价砍一半，都毫无机会。')]),
    'delusion': dict(after='c4e', ch='ch4', **{'in': 766.85, 'out': 784.1}, span=0.06, who='buffett', src='fcic', srcname=SOT_SRC, ts='12:47', cuts=[7.18, 11.77],
                     en='But they fell prey to the same delusion that existed throughout the country eventually. And it meant that the models they had were no good. They didn’t contemplate — but neither did the models in the minds of 300 million Americans contemplate what was going to happen.',
                     ph=[('But they fell prey to the same delusion that existed throughout the country eventually.', '可它们落入了最终席卷全国的同一个错觉。'),
                         ('And it meant that the models they had were no good. They didn’t contemplate —', '这意味着它们的模型不管用。它们没想到，'),
                         ('but neither did the models in the minds of 300 million Americans contemplate what was going to happen.', '可 3 亿美国人脑子里的模型，也没想到会发生什么。')]),
    'mistake': dict(after='c5f', ch='ch5', **{'in': 457.3, 'out': 462.42}, span=0.03, who='buffett', src='fcic', srcname=SOT_SRC, ts='7:38',
                    en='I made a mistake in that it got to very lofty heights and we didn’t sell.',
                    ph=[('I made a mistake in that it got to very lofty heights and we didn’t sell.', '我犯了个错：它涨到很高的时候，我们没卖。')]),
}

# 屏幕上出现的原话（英文原句 + 中文翻译 + 出处）
QUOTES = {
    'qabel': ('Businesses we understand well, have a high regard for their leaders, and expect will compound over decades.',
              '这些生意，我们很了解，敬重它们的掌舵人，并且相信它们能复利几十年。', 'Greg Abel · 2025 Letter to Shareholders'),
    'qcogs': ('We conclude the failures of credit rating agencies were essential cogs in the wheel of financial destruction.',
              '我们的结论是：评级机构的失败，是这台金融破坏之轮上的关键齿轮。', 'Financial Crisis Inquiry Commission · Final Report (2011)'),
    'qmgmt': ('The extraordinary business does not require good management.',
              '非凡的生意，不需要很好的管理。', 'Warren Buffett · FCIC staff interview (May 26, 2010)'),
    'qbarrier': ('Barriers to entry continue to exist in the credit ratings industry.',
                 '评级行业的进入壁垒，至今依然存在。', 'SEC Office of Credit Ratings · Staff Report (Jan 2025)'),
    'qsales': ('Late in the year made other sales in anticipation of our BNSF purchase.',
               '年底的另一些卖出，是为收购 BNSF 做准备。', 'Warren Buffett · 2009 Letter to Shareholders'),
}
