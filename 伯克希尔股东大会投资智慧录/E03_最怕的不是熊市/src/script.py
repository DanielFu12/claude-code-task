"""《伯克希尔股东大会投资智慧录》第三集 · 巴菲特：最怕的不是熊市 —— 全部文本的唯一来源。

INTRO      开场口播（第 0 秒的中文钩子 → 1994 年的市场背景 → 那年的提问）
ORIGINAL   1994 年股东大会上午场原始录像的字幕（英文逐字取自 CNBC 逐字稿 1994-M47，中文为本片翻译）
INSIGHT    投资启示解读（本片撰写的旁白；不是巴菲特或芒格的原话）
SUMMARY    一句话总结
ENDQ       片尾互动问题

每条口播：(id, 场景, 朗读文本, 句后停顿秒)。字幕按全角标点自动断成短句显示。
SAY 里是只为发音调整的朗读文本（屏幕字幕仍用原文）。
"""

# ------------------------------------------------------------------ 配音参数（与前两集相同，见 CLAUDE.md 第 3 节）
GEMINI_MODEL = 'gemini-3.8-flash-tts'
GEMINI_VOICE = 'charon'
GEMINI_STYLE = ('A steady authoritative male narrator for a financial documentary. '
                'Measured and deliberate pace, calm confidence, clear enunciation, quiet gravitas.')
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/interactions'
TEMPO = 1.07
TTS_GROUPS = [('S1', 'S2', 'S3'), ('I1', 'I2', 'I3'), ('I7', 'I7B', 'I8'), ('I10',), ('I11',), ('M',), ('Q',)]
TAGS = {'S2': '<breath>', 'S3': '<short pause>', 'I2': '<breath>', 'I3': '<short pause>', 'I7': '<breath>', 'I7B': '<short pause>',
        'I8': '<breath>', 'I10': '<breath>', 'I11': '<breath>', 'M': '<breath>', 'Q': '<breath>'}

# ------------------------------------------------------------------ 冷开场（原声）：本集标题的出处——“我们真正害怕的，是一场长期持续的非理性牛市”
COLD_IDS = ('A19',)

# ------------------------------------------------------------------ 开场口播（第二集起不再宣布新系列）
INTRO = [
    ('S1', 'hook', '市场低迷、账户缩水，你是不是也在犹豫：还要不要继续买？巴菲特看待下跌的方式，也许能帮你换个角度。', 0.35),
    ('S2', 'rates', '1994年春天，美联储两个半月里三次加息，债券市场遭遇重挫。', 0.45),
    ('S3', 'ask', '那年的伯克希尔股东大会上，一位股东问得很直接：你们看涨，还是看跌？', 0.0),
]

# ------------------------------------------------------------------ 原始问答（字幕）
# 来源：CNBC Warren Buffett Archive 逐字稿 1994 Morning Session 第 47 章「Why we have no short-term opinion on stocks」
# 场景名为 'omit' 的句子不进成片（节选时省略），只用于和语音识别结果对齐。
# 英文只省略口头重起的半句（M1 的 "I think the —"、M3 的 "it's just,"），其余逐字保留。
ORIGINAL = [
    ('Q0', 'omit', 'Diane West (PH) from Corona Del Mar, California.', ''),
    ('Q1', 'ask', 'I know, Mr. Buffett, that you said that you don’t read what other people say about the market or the economy,',
     '巴菲特先生，我知道您说过，您不看别人对市场或经济的评论。'),
    ('Q2', 'ask', 'but do either you or Charlie have an opinion about how you think things are going to go?',
     '但您或查理，对接下来的走势有没有自己的看法？'),
    ('Q3', 'ask', 'Are you bullish or bearish?', '你们是看涨，还是看跌？'),
    ('A1', 'never', 'You may have trouble believing this, but Charlie and I never have an opinion about the market',
     '说出来你可能不信：查理和我对市场从来没有看法，'),
    ('A2', 'never', 'because it wouldn’t be any good and it might interfere with the opinions we have that are good.',
     '因为那种看法不会有什么用，还可能干扰我们那些真正有用的看法。'),
    ('O1', 'omit', 'If we’re right about a business, if we think a business is attractive, it would be very foolish for us to not take action on that because we thought something about what the market was going to do, or anything of that sort.', ''),
    ('O2', 'omit', 'Because we just don’t know.', ''),
    ('O3', 'omit', 'And to give up something that you do know and that is profitable for something that you don’t know and won’t know because of that, it just doesn’t make any sense to us, and it doesn’t really make any difference to us.', ''),
    ('A3', 'history', 'I mean, I bought my first stock in, probably, April of 1942 when I was 11.', '我买第一只股票，大概是在1942年4月，那年我11岁。'),
    ('A4', 'history', 'And since then, I mean, actually World War II didn’t look so good at that time.', '其实在那个时候，二战的形势看起来并不妙。'),
    ('A5', 'history', 'I mean, the prospects, they really didn’t.', '前景确实不乐观。'),
    ('A6', 'history', 'I mean, you know, we were not doing well in the Pacific.', '我们在太平洋战场打得很糟。'),
    ('A7', 'history', 'I’m not sure I calculated that into my purchase of my three shares.', '我不确定，买那三股的时候，我有没有把这个算进去。'),
    ('A8', 'history', 'But I mean, just think of all the things that have happened since then, you know?', '可你想想，从那以后发生了多少事？'),
    ('A9', 'history', 'Atomic weapons and major wars, presidents resigning, and all kinds of things, massive inflation at certain times.',
     '核武器、几场大战、总统辞职，各种各样的事，有些年份还有严重的通货膨胀。'),
    ('A10', 'history', 'To give up what you’re doing well because of guesses about what’s going to happen in some macro way just doesn’t make any sense to us.',
     '因为对宏观的种种猜测，就放弃自己擅长的事——在我们看来毫无道理。'),
    ('A11', 'buyer', 'The best thing that can happen from Berkshire’s standpoint — we don’t wish this on anybody —',
     '从伯克希尔的角度看，最好的事——我们并不希望任何人遭遇这个——'),
    ('A12', 'buyer', 'but is that over time is to have markets that go down a tremendous amount.', '是市场在一段时间里大幅下跌。'),
    ('A13', 'buyer', 'I mean, we are going to be buyers of things over time.', '因为我们今后会一直是买家。'),
    ('A14', 'buyer', 'And if you’re going to be buyers of groceries over time, you like grocery prices to go down.',
     '如果你今后要一直买菜，你会希望菜价下跌；'),
    ('A15', 'buyer', 'If you’re going to be buying cars over time, you like car prices to go down.', '如果你今后要不断买车，你会希望车价下跌。'),
    ('A16', 'buyer', 'We buy businesses. We buy pieces of businesses: stocks.', '我们买企业，也买企业的一部分——股票。'),
    ('A17', 'buyer', 'And we’re going to be much better off if we can buy those things at an attractive price than if we can’t.',
     '能以有吸引力的价格买到它们，我们的处境会好得多。'),
    ('A18', 'fear', 'So we don’t have any fear at all.', '所以，我们一点也不害怕。'),
    ('A19', 'fear', 'I mean, what we fear is an irrational bull market that’s sustained for some long period of time.',
     '我们真正害怕的，是一场长期持续的非理性牛市。'),
    ('O4A', 'holder', 'You, as shareholders of Berkshire, unless you own your shares on borrowed money or are going to sell them in a very short period of time,',
     '作为伯克希尔的股东，除非你是借钱持股，或者很快就要卖掉，'),
    ('O4B', 'holder', 'are better off if stocks get cheaper,', '否则股票变得更便宜，对你们更有利，'),
    ('O4C', 'holder', 'because it means that we can be doing more intelligent things on your behalf than would be the case otherwise.',
     '因为这样，我们就能替你们做更多明智的事。'),
    ('O5', 'omit', 'But we have no idea what — and we wouldn’t care what anybody thought about it. I mean, most of all ourselves.', ''),
    ('B1', 'munger', 'Charlie, do you have anything?', '查理，你有什么补充吗？'),
    ('M1', 'munger', 'No. If you’re agnostic about those macro factors', '没有。如果你对那些宏观因素持不可知的态度，'),
    ('M2', 'munger', 'and therefore devote all your time to thinking about the individual businesses and the individual opportunities,',
     '因而把全部时间都用来思考一家家具体的企业、一个个具体的机会，'),
    ('M3', 'munger', 'it’s a way more efficient way to behave, at least with our particular talents and lacks thereof.',
     '那是一种高效得多的做法——至少对我们这种长处和短处来说是这样。'),
    ('A20', 'right', 'If you’re right about the businesses, you’ll end up doing fine.', '只要你对企业的判断是对的，最后结果就不会差。'),
    ('A21', 'omit', 'We don’t know, and we don’t think about when something will happen. We think about what will happen.',
     '我们不知道、也不去想某件事什么时候发生。我们想的是：会发生什么。'),
    ('A22', 'omit', 'It’s not so difficult to figure out what will happen.', '弄清楚会发生什么，并不那么难；'),
    ('A23', 'omit', 'It’s impossible, in our view, to figure out when it will happen.', '在我们看来，弄清楚它什么时候发生，是不可能的。'),
    ('A24', 'omit', 'So we focus on what will happen.', '所以，我们专注于会发生什么。'),
    ('A25', 'coke', 'This company in 1890 or thereabouts, the whole company sold for $2,000.', '就说这家公司（可口可乐）：1890年前后，整个公司只卖2000美元。'),
    ('A26', 'coke', 'It’s got a market value now of about 50-odd-billion, you know?', '如今它的市值大约是500多亿美元。'),
    ('A27', 'coke', 'Somebody could’ve said to the fellow who was buying this in 1890, you know,', '1890年买下它的人，本来可能会听到这样的劝告：'),
    ('A28', 'coke', '“You’re going to have a couple of great World Wars, and you know, you’ll have the panic of 1907, all these things will happen.',
     '“接下来会有两次世界大战，还会有1907年的大恐慌，这些事都会发生——'),
    ('A29', 'coke', 'And wouldn’t it be a better idea to wait?”', '是不是等等再买更好？”'),
    ('A30', 'coke', 'We can’t afford that mistake, basically.', '这种错误，我们可犯不起。'),
]
LAUGHS = ('A2', 'A7', 'A29')  # 逐字稿在这几句之后标注 "(Laughter)"
QUOTE_ID = 'A30'             # 问答结束后的金句卡

# 节选：四段原声（按句子 id 首尾），中间三处省略在画面上先暗下去再亮起，并标出“节选”
QA_SEGMENTS = [('Q1', 'A2'), ('A3', 'O4C'), ('B1', 'A20'), ('A25', 'A30')]
# 剪入点的搜索窗口（相对该句开口，秒）：A3 前面紧接着被省略的半句 "...difference to us."，两句之间只有约 60ms 的低谷
QA_IN_WINDOW = {'A3': (-0.2, -0.02)}
QA_OMITTED = [
    '提问者的自我介绍（约 3 秒）',
    '回答开头关于“不能拿知道的去换不知道的”的展开（约 31 秒）：同一论点巴菲特在 1942 年那段之后用一句话再说了一遍（A10），成片保留那一句',
    '对股东的补充之后一句没说完的话：“But we have no idea what — and we wouldn’t care what anybody thought about it…”（约 9 秒，句子中途断开，与论证无关）',
    '“不去想某件事何时发生，只想会发生什么”的几句（约 15 秒）：中文直译容易被理解成“未来必然发生”，与本片要讲的概率思维不符，故从节选中省略；其后的可口可乐例子完整保留',
]

# ------------------------------------------------------------------ 投资启示（本片解读，旁白）
# 逻辑链：概括原观点 → 第一性原理（回报来自企业赚的钱，也取决于买入价；130 多年的真实数据）→ 历史上最贵的一次：1999
#        （巴菲特不碰科技股 = 做对；追高科技股 = 做错）→ 前提与局限（巴菲特在原声里亲口说的两条 + 看懂企业）→ 今天
INSIGHT = [
    ('I1', 'recap', '巴菲特的逻辑是：伯克希尔是长年的买家，所以下跌等于打折；真正让他害怕的，是长期持续的非理性牛市。', 0.5),
    ('I2', 'cape', '道理并不复杂：股票是企业的一部分，回报来自企业赚的钱，也取决于你买入的价格。', 0.4),
    ('I3', 'cape', '美股一百三十多年的数据：最便宜的两成时段买入，此后十年扣除通胀，年均约11%；最贵的两成，只有3%。', 0.6),
    ('I7', 'bubble', '历史上最贵的一次，正是1999年：纳斯达克一年涨了86%。巴菲特看不懂科技公司，一股也不碰。', 0.35),
    ('I7B', 'bubble', '结果那一年，伯克希尔股价反而跌了约两成，被质疑已经落伍。', 0.4),
    ('I8', 'bubble', '可泡沫终究会破：纳斯达克跌去78%，整整15年才回到原位；同一时期，伯克希尔股价不跌反涨。', 0.6),
    ('I10', 'cond', '前提，巴菲特自己说了：不借钱，不急着卖；还得真正看懂企业。否则下跌不是机会，而是灾难。', 0.6),
    ('I11', 'today', '下一次市场大跌，先问问自己：是这门生意变了，还是只是价格打了折？', 0.0),
]
SUMMARY = ('M', 'motto', '最怕的不是熊市，而是长期的疯狂。', 0.0)
# 片尾互动：留给观众的一个问题（在品牌片尾之前）
ENDQ = ('Q', 'ask', '如果明天市场大跌三成，你会害怕，还是高兴？', 0.0)

SAY = {
    'S1': '市场低迷、账户缩水，你是不是也在犹豫：还要不要继续买？巴菲特看待下跌的方式，也许能帮你换个角度。',
    'S2': '一九九四年春天，美联储两个半月里三次加息，债券市场遭遇重挫。',
    'I3': '美股一百三十多年的数据：最便宜的两成时段买入，此后十年扣除通胀，年均约百分之十一；最贵的两成，只有百分之三。',
    'I7': '历史上最贵的一次，正是一九九九年：纳斯达克一年涨了百分之八十六。巴菲特看不懂科技公司，一股也不碰。',
    'I7B': '结果那一年，伯克希尔股价反而跌了约两成，被质疑已经落伍。',
    'I8': '可泡沫终究会破：纳斯达克跌去百分之七十八，整整十五年才回到原位；同一时期，伯克希尔股价不跌反涨。',
    'Q': '如果明天市场大跌三成，你会害怕，还是高兴？',
}

# ------------------------------------------------------------------ 来源（原始录像 + 事实核查）
ARCHIVE_ITEM = 'youtube-A2J-_BNkqm8'
ARCHIVE_URL = 'https://archive.org/download/youtube-A2J-_BNkqm8/A2J-_BNkqm8.mp4'
CLIP_IN, CLIP_LEN = 5958.0, 292.0        # 全场 1:39:18 起 292 秒：上一题结尾 → "Zone 2." → 可口可乐的例子 → "Zone 3."
PIC_BOX = (205, 172, 1720, 786)          # 1920×1080 源里干净的画面区（避开左上角第三方水印与下方烧录字幕，与第二集同一录像）
BROLL = [700, 5200]         # 片头用的上午场历史影像（各取 16 秒）
CNBC_CHAPTER = '1994-M47 · Why we have no short-term opinion on stocks'
CNBC_URL = 'https://buffett.cnbc.com/video/1994/04/25/morning-session---1994-berkshire-hathaway-annual-meeting.html'
MEETING_DATE = '1994-04-25'

# 解读图表的数据（data/ 下的文件由 data_prep.py 从公开数据生成）
CAPE = 'cape_1881_2013.json'     # Shiller：每月的周期调整市盈率（CAPE）与此后十年年化实际回报，1881.01–2013.09
NQBK = 'nq_brk_1994_2015.json'   # 纳斯达克综合指数与伯克希尔 A 股每日收盘，1994-01 – 2015-12（Yahoo Finance ^IXIC、BRK-A）

# 伯克希尔年度业绩表（2018 年致股东信附表）：年份 → (伯克希尔股价年度涨跌 %, 标普 500 含股息年度回报 %)
BRK_TABLE = {1995: (57.4, 37.6), 1996: (6.2, 23.0), 1997: (34.9, 33.4), 1998: (52.2, 28.6), 1999: (-19.9, 21.0),
             2000: (26.6, -9.1), 2001: (6.5, -11.9), 2002: (-3.8, -22.1)}

FACTS = [
    # (用在哪, 事实, 出处)
    ('S2', '1994 年联邦基金目标利率：2 月 4 日 3.25%、3 月 22 日 3.50%、4 月 18 日 3.75%（大会前两个半月内三次加息；5 月 17 日起又加了三次）',
     '美联储 Open Market Operations 历史表（federalreserve.gov/monetarypolicy/openmarket_archive.htm）'),
    ('S2', '“债券市场遭遇重挫”：十年期美债收益率月均值 1994 年 1 月 5.75%，4 月 6.97%（收益率上升即债券价格下跌；画面图表标出这两个数字）', 'Robert Shiller《Irrational Exuberance》在线数据 ie_data.xls（GS10 列，源自美联储）'),
    ('背景卡', '1994 年 4 月 25 日伯克希尔股东大会上午场；问答 CNBC 第 47 章「Why we have no short-term opinion on stocks」',
     'CNBC Warren Buffett Archive；原始录像 archive.org youtube-A2J-_BNkqm8（全场 1:39:28 起）'),
    ('A25', '“This company” 指可口可乐：巴菲特说 1890 年前后整个公司只卖 2000 美元，如今市值 500 多亿美元',
     'CNBC 逐字稿 1994-M47（逐字稿中文译文即作“可口可乐”）'),
    ('冷开场、A19', '“What we fear is an irrational bull market that’s sustained for some long period of time.”（我们真正害怕的，是一场长期持续的非理性牛市）', 'CNBC 逐字稿 1994-M47'),
    ('I1', '“we are going to be buyers of things over time”；“The best thing that can happen from Berkshire’s standpoint … is to have markets that go down a tremendous amount.”', 'CNBC 逐字稿 1994-M47'),
    ('I2', '“股票是企业的一部分”：“We buy businesses. We buy pieces of businesses: stocks.”（同一段原声 A16）', 'CNBC 逐字稿 1994-M47'),
    ('I2（画面）', '“Price is what you pay; value is what you get.” Whether we’re talking about socks or stocks, I like buying quality merchandise when it is marked down.（同段还说：“we enjoy such price declines if we have funds available to increase our positions”）',
     'Berkshire 2008 年致股东信（巴菲特引述格雷厄姆）'),
    ('I3', '“最便宜的两成时段买入，此后十年扣除通胀年均约 11%；最贵的两成，只有 3%”：1881.01–2013.09 共 1,593 个月，按当月 CAPE（股价 ÷ 过去十年平均实际盈利）分成五等份；CAPE 最低的五分之一（≤ 11.1 倍）此后十年年化实际总回报（含股息、扣除通胀）平均 10.9%，最高的五分之一（≥ 21.0 倍）平均 3.0%；全部月份两者的相关系数 −0.52',
     'Robert Shiller ie_data.xls（CAPE 列与“10 Year Annualized Stock Real Return”列；本片按五等份计算平均值）'),
    ('I3（画面）', '散点图里的每个点是一个月份；标出的点：1982 年 7 月 CAPE 6.6 倍 → 此后十年年化实际 +14.3%；1999 年 12 月 CAPE 44.2 倍（历史最高）→ 此后十年年化实际 −3.2%', 'Shiller ie_data.xls'),
    ('I7', '“历史上最贵的一次，正是 1999 年”：Shiller CAPE 在 1999 年 12 月达到 44.2 倍，为 1881 年以来的最高值（截至数据末 2023 年 9 月）', 'Shiller ie_data.xls'),
    ('I7', '“到 1999 年进入疯狂：纳斯达克一年涨了 86%”：纳斯达克综合指数 1998 年底 2,192.69 点，1999 年底 4,069.31 点（+85.6%）；随后在 2000 年 3 月 10 日收于 5,048.62 点的高点。注意 1994–1998 年伯克希尔股价其实跑赢纳斯达克，两者在 1999 年才大幅背离', 'Yahoo Finance ^IXIC、BRK-A 每日收盘'),
    ('I7', '“看不懂科技公司，一股也不碰”：“This explains, by the way, why we don’t own stocks of tech companies…”；“we have no insights into which participants in the tech field possess a truly durable competitive advantage.”', 'Berkshire 1999 年致股东信'),
    ('I7B', '“结果那一年，伯克希尔股价反而跌了约两成”：1999 年伯克希尔股价 −19.9%（同年标普 500 含股息 +21.0%）（同一封信称这是“the worst absolute performance of my tenure and, compared to the S&P, the worst relative performance as well”）', 'Berkshire 2018 年致股东信附表；1999 年致股东信'),
    ('I7B（画面）', '“被质疑已经落伍”：《巴伦周刊》1999 年 12 月 27 日刊出 Andrew Bary 的文章「What’s Wrong, Warren?」，质疑巴菲特是否失去了手感', 'Barron’s, 1999-12-27；另见 hedgefundalpha.com/news/whats-wrong-warren/'),
    ('I8', '纳斯达克综合指数 2000 年 3 月 10 日收于 5,048.62 点的高点，2002 年 10 月 9 日收于 1,114.11 点（下跌 77.9%），直到 2015 年 4 月 23 日（5,056.06 点）才首次收在 2000 年的高点之上', 'Yahoo Finance ^IXIC 每日收盘'),
    ('I8（画面）', '“同一时期，伯克希尔股价不跌反涨”：2000–2002 年伯克希尔股价 +26.6%、+6.5%、−3.8%，累计约 +29.7%；同期标普 500（含股息）−9.1%、−11.9%、−22.1%，累计约 −37.6%（累计值由年度数据连乘计算，与 BRK-A 每日收盘一致）', 'Berkshire 2018 年致股东信附表；Yahoo Finance BRK-A'),
    ('I7–I8（画面）', '画面两条曲线以 1994 年 4 月 25 日为 1：纳斯达克综合指数与伯克希尔 A 股的每日收盘（价格，不含股息）', 'Yahoo Finance ^IXIC、BRK-A'),
    ('I10', '“不借钱，不急着卖”：巴菲特在本段原声（O4）里亲口说的两条前提——“unless you own your shares on borrowed money or are going to sell them in a very short period of time”', 'CNBC 逐字稿 1994-M47'),
    ('I10', '“还得真正看懂企业”对应本段原声 A20：“If you’re right about the businesses, you’ll end up doing fine.”', 'CNBC 逐字稿 1994-M47'),
    ('I11', '“是这门生意变了，还是只是价格打了折？”是本片解读，对应巴菲特本段回答的买菜 / 买车比喻与 1997 年信的汉堡测验', '—'),
]
