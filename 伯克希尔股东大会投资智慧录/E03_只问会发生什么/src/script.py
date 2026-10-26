"""《伯克希尔股东大会投资智慧录》第三集 · 只问会发生什么，不猜何时发生 —— 全部文本的唯一来源。

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
TTS_GROUPS = [('S1', 'S2', 'S3'), ('I1', 'I3', 'I4'), ('I5', 'I6'), ('I8', 'I9'), ('I10',), ('I11',), ('I12',), ('M',),
              ('Q',)]
TAGS = {'S2': '<breath>', 'S3': '<short pause>', 'I3': '<breath>', 'I4': '<short pause>', 'I5': '<breath>',
        'I6': '<short pause>', 'I9': '<short pause>', 'I10': '<breath>', 'I11': '<breath>', 'I12': '<breath>',
        'M': '<breath>', 'Q': '<breath>'}

# ------------------------------------------------------------------ 冷开场（原声）：会发生什么不难，何时发生不可能
COLD_IDS = ('A22', 'A23')

# ------------------------------------------------------------------ 开场口播（第二集起不再宣布新系列）
INTRO = [
    ('S1', 'hook', '战争、加息、股灾……局势不明朗的时候，该买，还是再等等？', 0.35),
    ('S2', 'rates', '1994年春天，美联储两个半月里三次加息，债券市场遭遇重挫。', 0.45),
    ('S3', 'ask', '那年的伯克希尔股东大会上，一位股东问得很直接：你们看涨，还是看跌？', 0.0),
]

# ------------------------------------------------------------------ 原始问答（字幕）
# 来源：CNBC Warren Buffett Archive 逐字稿 1994 Morning Session 第 47 章「Why we have no short-term opinion on stocks」
# 场景名为 'omit' 的句子不进成片（节选时省略），只用于和语音识别结果对齐。
# 英文只省略口头重起的半句（M1 的 "I think the —"、M3 的 "it's just,"、A22 的 "It's fairly,"），其余逐字保留。
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
     '因为猜测宏观上会发生什么，就放弃自己擅长的事——在我们看来毫无道理。'),
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
    ('A20', 'what', 'If you’re right about the businesses, you’ll end up doing fine.', '只要你对企业的判断是对的，最后结果就不会差。'),
    ('A21', 'what', 'We don’t know, and we don’t think about when something will happen. We think about what will happen.',
     '我们不知道、也不去想某件事什么时候发生。我们想的是：会发生什么。'),
    ('A22', 'what', 'It’s not so difficult to figure out what will happen.', '弄清楚会发生什么，并不那么难；'),
    ('A23', 'what', 'It’s impossible, in our view, to figure out when it will happen.', '在我们看来，弄清楚它什么时候发生，是不可能的。'),
    ('A24', 'what', 'So we focus on what will happen.', '所以，我们专注于会发生什么。'),
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

# 节选：三段原声（按句子 id 首尾），中间两处省略在画面上先暗下去再亮起，并标出“节选”
QA_SEGMENTS = [('Q1', 'A2'), ('A3', 'A19'), ('B1', 'A30')]
# 剪入点的搜索窗口（相对该句开口，秒）：A3 前面紧接着被省略的半句 "...difference to us."，两句之间只有约 60ms 的低谷
QA_IN_WINDOW = {'A3': (-0.2, -0.02)}
QA_OMITTED = [
    '提问者的自我介绍（约 3 秒）',
    '回答开头关于“不能拿知道的去换不知道的”的展开（约 33 秒；同一论点在 1942 年那段之后再次出现，保留）',
    '对伯克希尔股东的补充：除非借钱持股或短期内要卖出，股价更便宜对股东更有利；以及“我们根本不在乎别人怎么看”（约 26 秒；解读中引用）',
]

# ------------------------------------------------------------------ 投资启示（本片解读，旁白）
INSIGHT = [
    ('I1', 'recap', '归结起来：会发生什么，可以研究；什么时候发生，无法预测。', 0.5),
    ('I3', 'burger', '他在1997年的信里出过一道题：如果你一辈子都要吃汉堡，又不养牛，你希望牛肉涨价，还是降价？', 0.35),
    ('I4', 'burger', '股票也一样：同样的钱，价格越低，买到的企业就越多。', 0.6),
    ('I5', 'y1942', '1942年3月，美国刚卷入二战，坏消息天天传来。11岁的巴菲特，用攒下的114.75美元，买了三股股票。', 0.35),
    ('I6', 'y1942', '这笔钱如果投进标普500指数、股息再投资，到2019年初是60.7万美元——5288倍。', 0.45),
    ('I8', 'wait', '反过来，等局势明朗往往就太晚了。2009年3月，标普500见底；', 0.3),
    ('I9', 'wait', '官方直到2010年9月才宣布衰退结束——这时，指数已从底部涨了69%。', 0.6),
    ('I10', 'cond', '不过，前提是你真正看懂企业，而且不借钱、不急着卖；否则下跌不是机会，而是灾难。', 0.6),
    ('I11', 'today', '每年都有新的理由让人“再等等”。与其猜涨跌，不如问：十年后，这门生意会是什么样？', 0.6),
    ('I12', 'close', '会发生什么，靠研究；什么时候发生，交给时间。', 0.0),
]
SUMMARY = ('M', 'motto', '只问会发生什么，不猜何时发生。', 0.0)
# 片尾互动：留给观众的一个问题（在品牌片尾之前）
ENDQ = ('Q', 'ask', '你有没有因为“再等等”，错过过一次好机会？', 0.0)

SAY = {
    'S1': '战争、加息、股灾，局势不明朗的时候，该买，还是再等等？',
    'S2': '一九九四年春天，美联储两个半月里三次加息，债券市场遭遇重挫。',
    'I3': '他在一九九七年的信里出过一道题：如果你一辈子都要吃汉堡，又不养牛，你希望牛肉涨价，还是降价？',
    'I5': '一九四二年三月，美国刚卷入二战，坏消息天天传来。十一岁的巴菲特，用攒下的一百一十四点七五美元，买了三股股票。',
    'I6': '这笔钱如果投进标普五百指数、股息再投资，到二零一九年初是六十点七万美元，五千二百八十八倍。',
    'I8': '反过来，等局势明朗往往就太晚了。二零零九年三月，标普五百见底；',
    'I9': '官方直到二零一零年九月才宣布衰退结束，这时，指数已从底部涨了百分之六十九。',
    'I11': '每年都有新的理由让人再等等。与其猜涨跌，不如问：十年后，这门生意会是什么样？',
    'Q': '你有没有因为再等等，错过过一次好机会？',
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
SP_0810 = 'sp_2008_2010.json'    # 标普 500 每日收盘，2008-09 – 2010-11（Yahoo Finance ^GSPC）

FACTS = [
    # (用在哪, 事实, 出处)
    ('S2', '1994 年联邦基金目标利率：2 月 4 日 3.25%、3 月 22 日 3.50%、4 月 18 日 3.75%（大会前两个半月内三次加息；5 月 17 日起又加了三次）',
     '美联储 Open Market Operations 历史表（federalreserve.gov/monetarypolicy/openmarket_archive.htm）'),
    ('S2', '“债券市场遭遇重挫”：十年期美债收益率月均值 1994 年 1 月 5.75%，4 月 6.97%（收益率上升即债券价格下跌；画面图表标出这两个数字）', 'Robert Shiller《Irrational Exuberance》在线数据 ie_data.xls（GS10 列，源自美联储）'),
    ('背景卡', '1994 年 4 月 25 日伯克希尔股东大会上午场；问答 CNBC 第 47 章「Why we have no short-term opinion on stocks」',
     'CNBC Warren Buffett Archive；原始录像 archive.org youtube-A2J-_BNkqm8（全场 1:39:28 起）'),
    ('A25', '“This company” 指可口可乐：巴菲特说 1890 年前后整个公司只卖 2000 美元，如今市值 500 多亿美元',
     'CNBC 逐字稿 1994-M47（逐字稿中文译文即作“可口可乐”）'),
    ('I1', '“We don’t know, and we don’t think about when something will happen. We think about what will happen.”', 'CNBC 逐字稿 1994-M47'),
    ('I3、I4', '汉堡测验：“If you plan to eat hamburgers throughout your life and are not a cattle producer, should you wish for higher or lower prices for beef?” 以及 “Prospective purchasers should much prefer sinking prices.”',
     'Berkshire 1997 年致股东信「How We Think About Market Fluctuations」'),
    ('I5', '1942 年 3 月 11 日，11 岁，用从 6 岁开始攒下的 114.75 美元买了 3 股 Cities Service 优先股；当时美国参战仅三个月，“Bad news arrived daily”',
     'Berkshire 2018 年致股东信「The American Tailwind」'),
    ('I5', '巴菲特在 1994 年大会上说的是“probably April of 1942”；信中给出的日期是 3 月 11 日，旁白用信中日期', 'CNBC 逐字稿 1994-M47；2018 年致股东信'),
    ('I6', '若投入免费用的标普 500 指数基金、股息再投资，到 2019 年 1 月 31 日税前价值 606,811 美元，“a gain of 5,288 for 1”',
     'Berkshire 2018 年致股东信'),
    ('I6', '图表曲线形状取自 Shiller 标普综合指数月度数据（月均价，含股息再投资；1942.03–2019.01 约 4,469 倍），按信中终值 5,288 倍做了对数平滑校准；图中标注的事件（越战升级、工资与物价管制、两次石油危机、总统辞职、道指单日下跌 508 点、苏联解体、21% 的优惠利率、金融恐慌）均取自 1994 年与 2018 年致股东信列举的事件',
     'Shiller ie_data.xls；Berkshire 1994 年、2018 年致股东信'),
    ('I8', '标普 500 在 2009 年 3 月 9 日收于 676.53 点，为这轮熊市的收盘最低点', 'Yahoo Finance ^GSPC 每日收盘'),
    ('I9', 'NBER 商业周期测定委员会于 2010 年 9 月 20 日宣布：经济活动的谷底出现在 2009 年 6 月，即衰退在 2009 年 6 月结束',
     'NBER Business Cycle Dating Committee Announcement, September 20, 2010'),
    ('I9', '画面字幕“官方宣布时，衰退已结束 15 个月”：谷底在 2009 年 6 月，宣布于 2010 年 9 月 20 日', 'NBER Business Cycle Dating Committee Announcement, September 20, 2010'),
    ('I9', '标普 500 在 2010 年 9 月 20 日收于 1142.71 点，比 2009 年 3 月 9 日的 676.53 点上涨 68.9%；2009 年 6 月 30 日收于 919.32 点',
     'Yahoo Finance ^GSPC 每日收盘'),
    ('I10', '巴菲特在同一段回答里补充：除非借钱持股，或短期内就要卖出，股价更便宜对伯克希尔股东更有利（成片中节选省略，见 qa.omitted）',
     'CNBC 逐字稿 1994-M47'),
    ('I10', '“Only those who will be sellers of equities in the near future should be happy at seeing stocks rise.”', 'Berkshire 1997 年致股东信'),
    ('I11', '“每年都有新的理由让人再等等”是本片解读；巴菲特在 1994 年的信里写道：“A different set of major shocks is sure to occur in the next 30 years. We will neither try to predict these nor to profit from them.”',
     'Berkshire 1994 年致股东信'),
]
