"""《伯克希尔股东大会投资智慧录》第二集 · 风险不是波动 —— 全部文本的唯一来源。

INTRO      开场口播（反直觉问题 → 1994 年的提问）
ORIGINAL   1994 年股东大会上午场原始录像的字幕（英文逐字取自 CNBC 逐字稿 1994-M50，中文为本片翻译）
INSIGHT    投资启示解读（本片撰写的旁白；不是巴菲特或芒格的原话）
SUMMARY    一句话总结

每条口播：(id, 场景, 朗读文本, 句后停顿秒)。字幕按全角标点自动断成短句显示。
SAY 里是只为发音调整的朗读文本（屏幕字幕仍用原文）。
"""

# ------------------------------------------------------------------ 配音参数（与第一集相同，见 CLAUDE.md 第 3 节）
GEMINI_MODEL = 'gemini-3.8-flash-tts'
GEMINI_VOICE = 'charon'
GEMINI_STYLE = ('A steady authoritative male narrator for a financial documentary. '
                'Measured and deliberate pace, calm confidence, clear enunciation, quiet gravitas.')
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/interactions'
TEMPO = 1.07
TTS_GROUPS = [('S1', 'S2', 'S3'), ('I1', 'I2', 'I3'), ('I4', 'I5', 'I6'), ('I7', 'I8', 'I9', 'I10', 'I10b'), ('I11',), ('I12',), ('I13',), ('M',),
              ('Q',)]
TAGS = {'S2': '<short pause>', 'S3': '<breath>', 'I3': '<short pause>', 'I4': '<breath>', 'I5': '<short pause>',
        'I7': '<breath>', 'I9': '<short pause>', 'I10': '<short pause>', 'I10b': '<breath>', 'I11': '<breath>', 'I12': '<breath>',
        'I13': '<breath>', 'M': '<breath>', 'Q': '<breath>'}

# ------------------------------------------------------------------ 冷开场（原声）
COLD_IDS = ('A19',)

# ------------------------------------------------------------------ 开场口播（第二集起不再宣布新系列）
INTRO = [
    ('S1', 'drop', '一只股票，一年里跌掉25%——它是变得更危险了，还是更便宜了？', 0.35),
    ('S2', 'beta', '按教科书的贝塔理论：更危险。', 0.45),
    ('S3', 'ask', '1994年的伯克希尔股东大会上，一位股东当面追问巴菲特：你们说的风险，到底是什么？', 0.0),
]

# ------------------------------------------------------------------ 原始问答（字幕）
# 来源：CNBC Warren Buffett Archive 逐字稿 1994 Morning Session 第 50 章
#       「Risk is "inextricably wound up" in how long an asset is held」
# 场景名为 'omit' 的句子不进成片（节选时省略），只用于和语音识别结果对齐。
# 英文只省略口头重起的半句（A3 的 "if your risk is that you're going —"），其余逐字保留。
ORIGINAL = [
    ('Q0', 'omit', 'Hello, my name is Charles Pyle from Ann Arbor, Michigan.', ''),
    ('Q1', 'ask', 'I’d like to ask you to expound on your view of risk in the financial world,', '我想请您详细谈谈，您怎么看待金融世界里的风险。'),
    ('Q2', 'ask', 'and I ask that against the background of what appear to be a number of inconsistencies', '我这么问，是因为您的风险观'),
    ('Q3', 'ask', 'between your view of risk and the conventional view of risk.', '和传统的风险观之间，似乎有不少矛盾。'),
    ('Q4', 'ask', 'I mention that in a recent article you pointed out inconsistency', '比如，您在最近一篇文章里指出：'),
    ('Q5', 'ask', 'in the use of beta as a measure of risk, which is a common standard.', '用贝塔来衡量风险——这个通行的标准——是自相矛盾的。'),
    ('Q6', 'omit', 'And I mention that derivatives are dangerous, and yet you feel comfortable playing at derivatives through Salomon Brothers.', ''),
    ('Q7', 'omit', 'And betting on hurricanes is dangerous, and yet you feel comfortable playing with hurricanes through insurance companies.', ''),
    ('Q8', 'omit', 'So it appears that you have some view of risk that’s inconsistent with what would appear on the face of it to be the conventional view of risk.', ''),
    ('A1', 'define', 'Well, we do define risk as the possibility of harm or injury.', '我们对风险的定义，是受到伤害或损失的可能性。'),
    ('A2', 'define', 'And in that respect we think it’s inextricably wound up in your time horizon for holding an asset.',
     '从这个意义上说，风险和你打算持有一项资产多久，是密不可分的。'),
    ('A3', 'horizon', 'I mean, if you intend to buy XYZ Corporation at 11:30 this morning', '比如说，你打算今天上午11点半买入某家公司，'),
    ('A4', 'horizon', 'and sell it out before the close today,', '收盘前再卖掉，'),
    ('A5', 'horizon', 'I mean, that is, in our view, that is a very risky transaction.', '那么在我们看来，这是一笔风险非常高的交易。'),
    ('A6', 'horizon', 'Because we think 50 percent of the time you’re going to suffer some harm or injury.', '因为我们认为，你有一半的概率会受到损失。'),
    ('A7', 'coke', 'If you have a time horizon on a business,', '如果你对一门生意有长期的持有眼光，'),
    ('A8', 'coke', 'we think the risk of buying something like Coca-Cola at the price we bought it at a few years ago',
     '那么以我们几年前的买入价，买下可口可乐这样的公司，'),
    ('A9', 'coke', 'is essentially, is so close to nil, in terms of our perspective holding period.', '就我们预期的持有期而言，风险基本上接近于零。'),
    ('A10', 'coke', 'But if you asked me the risk of buying Coca-Cola this morning and you’re going to sell it tomorrow morning,',
     '但如果你问我：今天上午买入可口可乐、明天上午就卖，风险有多大？'),
    ('A11', 'coke', 'I say that is a very risky transaction.', '我会说，这是一笔风险非常高的交易。'),
    ('A12', 'beta', 'Now, as I pointed out in the annual report,', '我在年报里也指出过，'),
    ('A13', 'beta', 'it became very fashionable in the academic world, and then that spilled over into the financial markets,',
     '学术界开始流行——后来又蔓延到金融市场——'),
    ('A14', 'beta', 'to define risk in terms of volatility, of which beta became a measure.', '用波动来定义风险，而贝塔就成了衡量波动的指标。'),
    ('A15', 'beta', 'But that is no measure of risk to us.', '但对我们来说，那根本不是衡量风险的标准。'),
    ('O1', 'omit', 'The risk, in terms of our super-cat business, is not that we lose money in any given year.', ''),
    ('O2', 'omit', 'We know we’re going to lose money in some given day, that is for certain.', ''),
    ('O3', 'omit', 'And we’re extremely likely to lose money in a given year.', ''),
    ('O4', 'omit', 'Our time horizon of writing that business, you know, would be at least a decade.', ''),
    ('O5', 'omit', 'And we think the probability of losing money over a decade is low.', ''),
    ('O6', 'omit', 'So we feel that, in terms of our horizon of investment, that that is not a risky business.', ''),
    ('O7', 'omit', 'And it’s a whole lot less risky than writing something that’s much more predictable.', ''),
    ('A16', 'absurd', 'Interesting thing is that using conventional measures of risk,', '有意思的是，按照传统的风险衡量方法，'),
    ('A17', 'absurd', 'something whose return varies from year to year between plus-20 percent and plus-80 percent',
     '一项每年回报在正20%到正80%之间波动的投资，'),
    ('A18', 'absurd', 'is riskier, as defined, than something whose return is 5 percent a year every year.',
     '按定义，竟然比每年稳定回报5%的投资风险更高。'),
    ('A19', 'absurd', 'We just think the financial world has gone haywire in terms of measures of risk.', '我们只是觉得，金融界在风险的衡量上，已经乱了套。'),
    ('A20', 'expect', 'We look at what we do —', '看看我们自己的做法——'),
    ('A21', 'expect', 'we are perfectly willing to lose money on a given transaction,', '我们完全愿意在某一笔交易上亏钱，'),
    ('A22', 'expect', 'arbitrage being an example, any given insurance policy being another example.', '套利是一个例子，任何一张保单也是。'),
    ('A23', 'expect', 'We are perfectly willing to lose money on any given transaction.', '在任何单笔交易上亏钱，我们都完全能接受。'),
    ('A24', 'expect', 'We are not willing to enter into transactions in which we think the probability of doing a number of mutually independent events,',
     '我们不愿意做的是：把一系列相互独立、'),
    ('A25', 'expect', 'but of a similar type, has an expectancy of loss.', '但类型相似的交易加在一起，期望值是亏损。'),
    ('O8', 'omit', 'And we hope that we are entering into our transactions where our calculations of those probabilities have validity.', ''),
    ('O9', 'omit', 'And to do so, we try to narrow it down.', ''),
    ('O10', 'omit', 'There are a whole bunch of things we just won’t do because we don’t think we can write the equation on them.', ''),
    ('O11', 'omit', 'But we, basically, Charlie and I by nature are pretty risk-averse.', ''),
    ('O12', 'omit', 'But we are very willing to enter into transactions —', ''),
    ('O13', 'omit', 'We, if we knew it was an honest coin, and someone wanted to give us seven-to-five or something of the sort on one flip,', ''),
    ('O14', 'omit', 'how much of Berkshire’s net worth would we put on that flip?', ''),
    ('O15', 'omit', 'Well we would — it would sound like a big number to you.', ''),
    ('O16', 'omit', 'It would not be a huge percentage of the net worth, but it would be a significant number.', ''),
    ('O17', 'omit', 'We will do things when probabilities favor us.', ''),
    ('B1', 'munger', 'Charlie?', '查理？'),
    ('M1', 'munger', 'Yeah, we, I would say we try and think like Fermat and Pascal', '嗯，我想说，我们努力像费马和帕斯卡那样思考——'),
    ('M2', 'munger', 'as if they’d never heard of modern finance theory.', '就好像他们从没听说过现代金融理论。'),
    ('M3', 'munger', 'I really think that a lot of modern finance theory can only be described as disgusting.',
     '我真心觉得，很多现代金融理论，只能用“令人作呕”来形容。'),
]
LAUGH_AFTER = 'M3'           # 逐字稿在芒格这句之后标注 "(Laughter)"

# 节选：四段原声（按句子 id 首尾），中间三处省略在画面上先暗下去再亮起，并标出“节选”
QA_SEGMENTS = [('Q1', 'Q5'), ('A1', 'A15'), ('A16', 'A25'), ('B1', 'M3')]
QA_OMITTED = [
    '提问者的自我介绍（约 4 秒）',
    '提问里关于衍生品与飓风保险的两个例子（约 26 秒）',
    '回答中关于超级巨灾保险十年期限的例子（约 37 秒）',
    '回答中关于“只做能写出方程的交易”与抛硬币赔率的补充（约 49 秒）',
]

# ------------------------------------------------------------------ 投资启示（本片解读，旁白）
INSIGHT = [
    ('I1', 'define', '巴菲特说，风险是受到伤害或损失的可能性；而教科书里的风险，是价格的波动——贝塔。', 0.5),
    ('I2', 'letter', '他在1993年的信里写得更具体：真正的风险，是持有期结束时，你拿回的钱，能否保住当初的购买力。', 0.45),
    ('I3', 'swing', '波动，只是价格摆动的幅度；风险，是钱还在不在。', 0.7),
    ('I4', 'wapo', '1973年，伯克希尔用1060万美元买入华盛顿邮报；到1974年底，市值只剩800万。', 0.35),
    ('I5', 'wapo', '按贝塔理论，它反而“更危险”了。', 0.4),
    ('I6', 'wapo', '可这门生意一直在增长——二十年后，这笔持股价值超过4亿美元。', 0.7),
    ('I7', 'dexter', '1993年，伯克希尔用价值4.33亿美元的自家股票，全资收购德克斯特鞋业。', 0.35),
    ('I8', 'dexter', '它是私有公司，没有股价，也就没有一天的波动——按贝塔理论，它的风险是零。', 0.45),
    ('I9', 'crack', '可几年之内，海外竞争让它的优势荡然无存，这门生意价值归零。', 0.45),
    ('I10', 'cost', '更痛的是代价：当初付出的那2.5万股伯克希尔股票，如果没花出去，到2014年会值57亿美元。', 0.5),
    ('I10b', 'cost', '没有波动，不等于没有风险。', 0.7),
    ('I11', 'lever', '波动也会变成真正的风险：当你借了钱，或者必须在低点卖出，暂时的下跌，就被锁定成永久的损失。', 0.6),
    ('I12', 'today', '所以，账户大幅回撤时，先问两个问题：这门生意还在吗？我会被迫卖出吗？', 0.6),
    ('I13', 'close', '价格的剧烈波动，不必然意味着真正的风险；真正值得警惕的，是本金永久损失的可能性。', 0.0),
]
SUMMARY = ('M', 'motto', '波动不是风险，永久损失才是。', 0.0)
# 片尾互动：留给观众的一个问题（在品牌片尾之前）
ENDQ = ('Q', 'ask', '你持仓里跌得最惨的那一只，现在回头看——是波动，还是永久损失？', 0.0)

SAY = {
    'S1': '一只股票，一年里跌掉百分之二十五，它是变得更危险了，还是更便宜了？',
    'S3': '一九九四年的伯克希尔股东大会上，一位股东当面追问巴菲特：你们说的风险，到底是什么？',
    'I1': '巴菲特说，风险是受到伤害或损失的可能性；而教科书里的风险，是价格的波动，贝塔。',
    'I2': '他在一九九三年的信里写得更具体：真正的风险，是持有期结束时，你拿回的钱，能否保住当初的购买力。',
    'I4': '一九七三年，伯克希尔用一千零六十万美元买入华盛顿邮报；到一九七四年底，市值只剩八百万。',
    'I5': '按贝塔理论，它反而更危险了。',
    'I6': '可这门生意一直在增长，二十年后，这笔持股价值超过四亿美元。',
    'I7': '一九九三年，伯克希尔用价值四亿三千三百万美元的自家股票，全资收购德克斯特鞋业。',
    'I8': '它是私有公司，没有股价，也就没有一天的波动，按贝塔理论，它的风险是零。',
    'I10': '更痛的是代价：当初付出的那两万五千股伯克希尔股票，如果没花出去，到二零一四年会值五十七亿美元。',
    'Q': '你持仓里跌得最惨的那一只，现在回头看，是波动，还是永久损失？',
}

# ------------------------------------------------------------------ 来源（原始录像 + 事实核查）
ARCHIVE_ITEM = 'youtube-A2J-_BNkqm8'
ARCHIVE_URL = 'https://archive.org/download/youtube-A2J-_BNkqm8/A2J-_BNkqm8.mp4'
CLIP_IN, CLIP_LEN = 6820.0, 310.0        # 全场 1:53:40 起 310 秒：上一题结尾 → "Zone five?" → 芒格作答后的笑声
PIC_BOX = (205, 172, 1720, 786)          # 1920×1080 源里干净的画面区（避开左上角第三方水印与下方烧录字幕）
BROLL = [200, 1500, 6000]                # 片头用的上午场历史影像（各取 16 秒）
CNBC_CHAPTER = '1994-M50 · Risk is “inextricably wound up” in how long an asset is held'
CNBC_URL = 'https://buffett.cnbc.com/video/1994/04/25/morning-session---1994-berkshire-hathaway-annual-meeting.html'
MEETING_DATE = '1994-04-25'

FACTS = [
    # (用在哪, 事实, 出处)
    ('S2、I5', '按贝塔理论，股价相对大盘大跌的股票在更低价位反而“更有风险”；巴菲特以 1973 年买入时的华盛顿邮报为例',
     'Berkshire 1993 年致股东信：“under beta-based theory, a stock that has dropped very sharply compared to the market — as had Washington Post when we bought it in 1973 — becomes ‘riskier’ at the lower price”'),
    ('I1', '风险的定义：“the possibility of loss or injury”（信）/ “the possibility of harm or injury”（股东大会）；学术界把风险定义为相对波动，即贝塔',
     'Berkshire 1993 年致股东信；CNBC 逐字稿 1994-M50'),
    ('I2', '真正的风险：整个持有期内的税后所得，能否至少给投资者带回最初的购买力，再加一点合理利息',
     'Berkshire 1993 年致股东信：“the real risk that an investor must assess is whether his aggregate after-tax receipts … will, over his prospective holding period, give him at least as much purchasing power as he had to begin with, plus a modest rate of interest”'),
    ('I4', '1973 年年中买入华盛顿邮报，成本 1060 万美元；1974 年底市值 800 万美元，亏损约 25%；当时市场给整家公司 1 亿美元估值，而内在价值约 4–5 亿美元',
     'Berkshire 1985 年致股东信'),
    ('I6', '1973 年约 1000 万美元买入，到 1993 年持股价值超过 4 亿美元（持股表：市值 4.40 亿美元），每年股息 700 万美元',
     'Berkshire 1993 年致股东信'),
    ('I7', '1993 年以 4.33 亿美元的伯克希尔股票（25,203 股 A 股）收购德克斯特鞋业；1993 年 11 月 7 日完成合并',
     'Berkshire 2007 年致股东信；1993 年致股东信'),
    ('I8', '全资收购（非上市子公司，没有市场报价）；巴菲特同一封信里写道：“We don’t need a daily quote on our 100% position in See’s or H. H. Brown”',
     'Berkshire 1993 年致股东信'),
    ('I9', '竞争优势因海外竞争很快消失，价值迅速归零（“rather promptly, its value went to zero”）；“the worst deal that I’ve made”',
     'Berkshire 2014 年致股东信；2007 年致股东信'),
    ('I10', '用于收购的 25,203 股伯克希尔 A 股，如果留到 2014 年底约值 57 亿美元（约 22.6 万美元/股）；“价值归零”说的是买来的生意，57 亿说的是付出去的代价——用不断升值的自家股票支付，真实代价是这笔机会成本',
     'Berkshire 2014 年致股东信'),
    ('I8', '“按贝塔理论，它的风险是零”是本片解读：没有市场报价，就没有可度量的价格波动', '—'),
    ('I11', '“真正的投资者欢迎波动”的前提是：投资者完全自由，可以无视市场，也可以利用市场的愚蠢', 'Berkshire 1993 年致股东信（Mr. Market 一段）'),
]
