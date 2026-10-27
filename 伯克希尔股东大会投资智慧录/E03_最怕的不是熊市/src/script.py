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
TTS_GROUPS = [('S1', 'S2', 'S3'), ('I1', 'I2', 'I3'), ('I5', 'I6'), ('I7', 'I8'), ('I10',), ('I11',), ('I12',), ('M',),
              ('Q',)]
TAGS = {'S2': '<breath>', 'S3': '<short pause>', 'I2': '<breath>', 'I3': '<short pause>', 'I5': '<breath>',
        'I6': '<short pause>', 'I7': '<breath>', 'I8': '<short pause>', 'I10': '<breath>', 'I11': '<breath>', 'I12': '<breath>',
        'M': '<breath>', 'Q': '<breath>'}

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
    ('O4', 'omit', 'You, as shareholders of Berkshire, unless you own your shares on borrowed money or are going to sell them in a very short period of time, are better off if stocks get cheaper, because it means that we can be doing more intelligent things on your behalf than would be the case otherwise.', ''),
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
QA_SEGMENTS = [('Q1', 'A2'), ('A3', 'A19'), ('B1', 'A20'), ('A25', 'A30')]
# 剪入点的搜索窗口（相对该句开口，秒）：A3 前面紧接着被省略的半句 "...difference to us."，两句之间只有约 60ms 的低谷
QA_IN_WINDOW = {'A3': (-0.2, -0.02)}
QA_OMITTED = [
    '提问者的自我介绍（约 3 秒）',
    '回答开头关于“不能拿知道的去换不知道的”的展开（约 33 秒；同一论点在 1942 年那段之后再次出现，保留）',
    '对伯克希尔股东的补充：除非借钱持股或短期内要卖出，股价更便宜对股东更有利；以及“我们根本不在乎别人怎么看”（约 26 秒；解读中引用）',
    '“不去想某件事何时发生，只想会发生什么”的几句（约 15 秒）：中文直译容易被理解成“未来必然发生”，与本片要讲的概率思维不符，故从节选中省略；其后的可口可乐例子完整保留',
]

# ------------------------------------------------------------------ 投资启示（本片解读，旁白）
# 逻辑链：概括原观点 → 第一性原理（买入价决定回报）→ 正例（1942，坏消息里买入）→ 反例（1995–2000 的疯狂牛市与科网泡沫）
#        → 前提与局限 → 今天 → 收尾
INSIGHT = [
    ('I1', 'recap', '巴菲特的逻辑是：伯克希尔是长年的买家，所以下跌等于打折；真正让他害怕的，是长期持续的非理性牛市。', 0.5),
    ('I2', 'price', '道理藏在价格里：一门每年赚10块的生意，花100块买，回报是10%；花200块买，就只剩5%。', 0.35),
    ('I3', 'price', '价格涨得越疯，留给买家的回报就越薄。', 0.6),
    ('I5', 'y1942', '1942年3月，美国刚卷入二战，坏消息天天传来。11岁的巴菲特，用攒下的114.75美元，买了三股股票。', 0.35),
    ('I6', 'y1942', '这笔钱如果投进标普500指数、股息再投资，到2019年初是60.7万美元——5288倍。', 0.6),
    ('I7', 'bubble', '再看另一头。说完这番话之后，标普500连续五年涨幅超过20%；1999年，伯克希尔股价反而跌了约两成，《巴伦周刊》发文质疑：巴菲特怎么了？', 0.35),
    ('I8', 'bubble', '他没有去追科技股。2000年3月泡沫见顶，纳斯达克随后跌去78%，整整15年才回到高点。', 0.6),
    ('I10', 'cond', '不过，前提是你真正看懂企业，而且不借钱、不急着卖；否则下跌不是机会，而是灾难。', 0.6),
    ('I11', 'today', '所以，下一次市场大跌，先别急着害怕。问问自己：是这门生意变了，还是只是价格打了折？', 0.6),
    ('I12', 'close', '熊市，是长期买家的打折季；长期持续的疯狂，才是真正的危险。', 0.0),
]
SUMMARY = ('M', 'motto', '最怕的不是熊市，而是长期的疯狂。', 0.0)
# 片尾互动：留给观众的一个问题（在品牌片尾之前）
ENDQ = ('Q', 'ask', '如果明天市场大跌三成，你会害怕，还是高兴？', 0.0)

SAY = {
    'S1': '市场低迷、账户缩水，你是不是也在犹豫：还要不要继续买？巴菲特看待下跌的方式，也许能帮你换个角度。',
    'S2': '一九九四年春天，美联储两个半月里三次加息，债券市场遭遇重挫。',
    'I2': '道理藏在价格里：一门每年赚十块的生意，花一百块买，回报是百分之十；花两百块买，就只剩百分之五。',
    'I5': '一九四二年三月，美国刚卷入二战，坏消息天天传来。十一岁的巴菲特，用攒下的一百一十四点七五美元，买了三股股票。',
    'I6': '这笔钱如果投进标普五百指数、股息再投资，到二零一九年初是六十点七万美元，五千二百八十八倍。',
    'I7': '再看另一头。说完这番话之后，标普五百连续五年涨幅超过百分之二十；一九九九年，伯克希尔股价反而跌了约两成，巴伦周刊发文质疑：巴菲特怎么了？',
    'I8': '他没有去追科技股。二零零零年三月泡沫见顶，纳斯达克随后跌去百分之七十八，整整十五年才回到高点。',
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
SP_1942 = 'sp_tr_1942.json'      # Shiller 标普综合指数月度数据（含股息再投资），1942.03–2019.01
IXIC = 'ixic_1994_2015.json'     # 纳斯达克综合指数每日收盘，1994-01 – 2015-12（Yahoo Finance ^IXIC）

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
    ('I2、I3', '“每年赚 10 块，花 100 块买回报 10%，花 200 块买回报 5%”是说明买入价与回报关系的算术示意（盈利收益率 = 盈利 ÷ 价格），画面标注“示意”', '—'),
    ('I3（画面）', '汉堡测验：“If you plan to eat hamburgers throughout your life and are not a cattle producer, should you wish for higher or lower prices for beef?” 以及 “Prospective purchasers should much prefer sinking prices.”',
     'Berkshire 1997 年致股东信「How We Think About Market Fluctuations」'),
    ('I5', '1942 年 3 月 11 日，11 岁，用从 6 岁开始攒下的 114.75 美元买了 3 股 Cities Service 优先股；当时美国参战仅三个月，“Bad news arrived daily”',
     'Berkshire 2018 年致股东信「The American Tailwind」'),
    ('I5', '巴菲特在 1994 年大会上说的是“probably April of 1942”；信中给出的日期是 3 月 11 日，旁白用信中日期', 'CNBC 逐字稿 1994-M47；2018 年致股东信'),
    ('I6', '若投入免费用的标普 500 指数基金、股息再投资，到 2019 年 1 月 31 日税前价值 606,811 美元，“a gain of 5,288 for 1”',
     'Berkshire 2018 年致股东信'),
    ('I6', '图表曲线形状取自 Shiller 标普综合指数月度数据（月均价，含股息再投资；1942.03–2019.01 约 4,469 倍），按信中终值 5,288 倍做了对数平滑校准；图中标注的事件（越战升级、工资与物价管制、两次石油危机、总统辞职、道指单日下跌 508 点、苏联解体、21% 的优惠利率、金融恐慌）均取自 1994 年与 2018 年致股东信列举的事件',
     'Shiller ie_data.xls；Berkshire 1994 年、2018 年致股东信'),
    ('I7', '1994 年大会之后，标普 500（含股息）1995–1999 年的年度回报：37.6%、23.0%、33.4%、28.6%、21.0%，连续五年超过 20%',
     'Berkshire 2018 年致股东信附表「Berkshire’s Performance vs. the S&P 500」'),
    ('I7', '1999 年伯克希尔股价下跌 19.9%（同年标普 500 上涨 21.0%）；旁白“跌了约两成”', 'Berkshire 2018 年致股东信附表'),
    ('I7', '《巴伦周刊》1999 年 12 月 27 日刊出 Andrew Bary 的文章「What’s Wrong, Warren?」，质疑巴菲特是否失去了手感', 'Barron’s, 1999-12-27；另见 hedgefundalpha.com/news/whats-wrong-warren/'),
    ('I8', '纳斯达克综合指数：1994 年 4 月 25 日收于 730.80 点；2000 年 3 月 10 日收于 5,048.62 点的高点；2002 年 10 月 9 日收于 1,114.11 点（较高点下跌 77.9%）；直到 2015 年 4 月 23 日（5,056.06 点）才首次收在 2000 年的高点之上',
     'Yahoo Finance ^IXIC 每日收盘'),
    ('I8（画面）', '2000–2002 年：标普 500（含股息）−9.1%、−11.9%、−22.1%，累计约 −37.6%；伯克希尔股价 +26.6%、+6.5%、−3.8%，累计约 +29.7%（累计值由年度数据连乘计算）',
     'Berkshire 2018 年致股东信附表'),
    ('I8', '“他没有去追科技股”：“This explains, by the way, why we don’t own stocks of tech companies…”；“we have no insights into which participants in the tech field possess a truly durable competitive advantage.” 同一封信承认 1999 年是“the worst absolute performance of my tenure and, compared to the S&P, the worst relative performance as well”', 'Berkshire 1999 年致股东信'),
    ('I10', '巴菲特在同一段回答里补充：除非借钱持股，或短期内就要卖出，股价更便宜对伯克希尔股东更有利（成片中节选省略，见 qa.omitted）',
     'CNBC 逐字稿 1994-M47'),
    ('I10', '“Only those who will be sellers of equities in the near future should be happy at seeing stocks rise.”', 'Berkshire 1997 年致股东信'),
    ('I11', '“是这门生意变了，还是只是价格打了折？”是本片解读，对应巴菲特本段回答的买菜 / 买车比喻与 1997 年信的汉堡测验', '—'),
]
