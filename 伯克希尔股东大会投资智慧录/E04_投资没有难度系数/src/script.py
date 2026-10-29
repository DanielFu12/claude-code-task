"""《伯克希尔股东大会投资智慧录》第四集 · 投资没有难度系数 —— 全部文本的唯一来源。

INTRO      开场口播（第 0 秒的中文钩子 → 1994 年春天的背景 → 那年的提问）
ORIGINAL   1994 年股东大会上午场原始录像的字幕（英文逐字取自 CNBC 逐字稿 1994-M38、M39，中文为本片翻译）
INSIGHT    投资启示解读（本片撰写的旁白；不是巴菲特或芒格的原话）
SUMMARY    一句话总结
ENDQ       片尾互动问题（本集不用：配乐的品牌重拍紧跟在高潮之后）

每条口播：(id, 场景, 朗读文本, 句后停顿秒)。字幕按全角标点自动断成短句显示。
SAY 里是只为发音调整的朗读文本（屏幕字幕仍用原文）。
"""

# ------------------------------------------------------------------ 配音参数（与前三集相同，见 CLAUDE.md 第 3 节）
GEMINI_MODEL = 'gemini-3.8-flash-tts'
GEMINI_VOICE = 'charon'
GEMINI_STYLE = ('A steady authoritative male narrator for a financial documentary. '
                'Measured and deliberate pace, calm confidence, clear enunciation, quiet gravitas.')
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/interactions'
TEMPO = 1.07
TTS_GROUPS = [('S1', 'S2', 'S3'), ('I1', 'I2', 'I3'), ('I5', 'I6'), ('I7', 'I8'), ('I10', 'I11'), ('M',)]
TAGS = {'S2': '<breath>', 'S3': '<short pause>', 'I2': '<breath>', 'I3': '<short pause>', 'I5': '<breath>', 'I6': '<short pause>',
        'I7': '<breath>', 'I8': '<short pause>', 'I10': '<breath>', 'I11': '<breath>', 'M': '<breath>'}

# ------------------------------------------------------------------ 冷开场（原声）：本集最有冲击力的一句
COLD_IDS = ('A12B',)

# ------------------------------------------------------------------ 开场口播（第二集起不再宣布新系列）
INTRO = [
    ('S1', 'hook', '选股的时候，你是不是也觉得：研究得越复杂、模型越精密，就越能赚钱？巴菲特的回答，也许会让你松一口气。', 0.35),
    ('S2', 'pg', '1994年春天，宝洁公司因为两笔复杂的利率掉期合约，一个季度就亏掉了1.57亿美元。', 0.45),
    ('S3', 'ask', '几周后的伯克希尔股东大会上，一位股东问：耐克、锐步这样的全球品牌，前景有哪些不确定性？', 0.0),
]

# ------------------------------------------------------------------ 原始问答（字幕）
# 来源：CNBC Warren Buffett Archive 逐字稿 1994 Morning Session 第 38 章「Nike and Reebok」与第 39 章
#       「“You don’t have to do exceptional things to get exceptional results”」（两章是同一个问答）。
# 场景名为 'omit' 的句子不进成片（节选时省略），只用于和语音识别结果对齐。
# 英文只省略口头重起的半句（A5 的 “I just — I don’t understand that —”、A7 的 “But I — I’m not —”、A20 的 “but you don’t — it —”），其余逐字保留。
ORIGINAL = [
    ('Q0', 'omit', 'Thank you for teaching me — teaching so much to all of us about business. My name is Mike Assail (PH) from New York City.', ''),
    ('Q1', 'omit', 'You mentioned earlier that Berkshire’s shoe business was great, but that other shoe businesses were not so good.', ''),
    ('Q2', 'ask', 'What are the uncertainties of the global brand leaders that Berkshire seems to like? They like Coke and Gillette.',
     '伯克希尔似乎偏爱全球领先的品牌，比如可口可乐和吉列。它们有哪些不确定性？'),
    ('Q3', 'ask', 'The global brand leaders in the shoe business being Nike and Reebok.', '在制鞋业，全球领先的品牌是耐克和锐步。'),
    ('Q4A', 'ask', 'What are their uncertainties, in terms of long-term competitive advantage, business economics, consumer behavior,',
     '它们有哪些不确定性？从长期竞争优势、生意的经济特性、消费者行为，'),
    ('Q4B', 'ask', 'and the other risk factors that you mentioned in the annual report this year? Thank you.', '以及您今年年报里提到的其他风险来看。谢谢。'),
    ('A1', 'omit', 'So, you’re really asking about the future prospects of Nike and Reebok? Yeah.', ''),
    ('A2', 'omit', 'I don’t know that much about those businesses.', ''),
    ('A3', 'omit', 'We do have one person in this audience, at least, who owns a lot of Reebok.', ''),
    ('A4', 'omit', 'But I am not expressing a negative view in any way on that.', ''),
    ('A5A', 'nike', 'I don’t understand their competitive position and the likelihood of permanence of their competitive position over a 10 or 20 year period',
     '我不理解它们的竞争地位，也看不清这种地位在 10 年、20 年里能不能持续——'),
    ('A5B', 'nike', 'as well as I think I understand the position of Brown and Dexter.', '不像我自认为理解布朗鞋业和德克斯特鞋业那样。'),
    ('A6', 'omit', 'That doesn’t mean I think that it’s inferior. Doesn’t mean I think that we’ve got better businesses or anything.', ''),
    ('A7', 'omit', 'I think we’ve got very good businesses. But I — I’m not — I haven’t done the work and I’m not sure if I did the work I would understand them.', ''),
    ('A8', 'nike', 'I think they are harder to understand, frankly, and to develop a fix on, than our kinds.', '坦白说，我觉得它们比我们这类企业更难理解，也更难拿准。'),
    ('A9', 'nike', 'But, they may be easier for other people who just have a better insight into that kind of business.',
     '不过，对更懂那一行的人来说，它们也许更容易。'),
    ('A10', 'pi', 'Some businesses are a lot easier to understand than others. And Charlie and I don’t like difficult problems.',
     '有些企业比别的企业容易理解得多。查理和我不喜欢难题。'),
    ('A11', 'pi', 'I mean, we — if something is hard to figure, you know, we’d rather multiply by three than by pi. I mean it’s just easier for us.',
     '要是一件事很难算，我们宁可乘以 3，也不乘以 π。对我们来说就是更容易。'),
    ('B1', 'labels', 'Charlie, you have any —?', '查理，你有什么要说的？'),
    ('M1', 'labels', 'Well, that is such an obvious point.', '这是再明显不过的道理。'),
    ('M2', 'labels', 'And yet so many people think if they just hire somebody with the appropriate labels they can do something very difficult.',
     '可还是有很多人以为，只要雇一个头衔合适的人，就能做成非常难的事。'),
    ('M3', 'labels', 'That is one of the most dangerous ideas a human being can have.', '这是一个人所能有的最危险的想法之一。'),
    ('M4', 'omit', 'All kinds of things just intrinsically create problems.', ''),
    ('M5', 'omit', 'The other day I was dealing with a problem and I said, this thing — it’s a new building — and I said this thing has three things I’ve learned to fear: an architect, a contractor, and a hill.', ''),
    ('M6', 'omit', 'And — if you go at life like that, I think you, at least, make fewer mistakes than people who think they can do anything by just hiring somebody with a label.', ''),
    ('B2', 'omit', 'We don’t comment — excuse me, go ahead.', ''),
    ('M7', 'labels', 'You don’t have to hire out your thinking if you keep it simple.', '只要保持简单，你就不必把思考外包出去。'),
    ('A12A', 'bar', 'You don’t have to do — we’ve said this before —', '你不需要——这话我们以前说过——'),
    ('A12B', 'bar', 'but you don’t have to do exceptional things to get exceptional results.', '你不需要做非凡的事，也能取得非凡的结果。'),
    ('A13', 'bar', 'And some people think that if you jump over a seven-foot bar that the ribbon they pin on you is going to be worth more money than if you step over a one-foot bar.',
     '有人以为，跳过七英尺高的横杆，别在身上的绶带会比跨过一英尺高的横杆更值钱。'),
    ('A14', 'bar', 'And it just isn’t true in the investment world, at all.', '在投资的世界里，完全不是这样。'),
    ('A15', 'coke', 'So, you can do very ordinary things. I mean, what is complicated about this?', '所以，你可以做很平常的事。这个（可口可乐）有什么复杂的？'),
    ('A16', 'coke', 'But, you know, we’re $3 billion pretax better off than we were a few years ago because of it.',
     '可就因为它，我们比几年前多了 30 亿美元的税前收益。'),
    ('A17A', 'coke', 'There’s nothing that I know about that product, or its distribution system, its finances, or anything,',
     '关于这个产品、它的分销体系、它的财务，我知道的任何东西，'),
    ('A17B', 'coke', 'that, really, hundreds of thousands — or millions — of people aren’t capable of, that they don’t already know.',
     '几十万、几百万人都能懂，他们其实早就知道。'),
    ('A18', 'coke', 'They just don’t do anything about it.', '他们只是什么也没做。'),
    ('A19A', 'report', 'And similarly, if you get into some complicated business, you can get a report that’s a thousand pages thick',
     '同样，如果你碰上一门复杂的生意，你可以拿到一份一千页厚的报告，'),
    ('A19B', 'report', 'and you got Ph.D.s working on it, but it doesn’t mean anything.', '有一群博士在研究，可那说明不了什么。'),
    ('A20', 'report', 'You know, what you’ve got is a report but you won’t understand that business, what it’s going to look like in 10 or 15 years.',
     '你拿到的只是一份报告，你还是不懂那门生意，不知道它 10 年、15 年后会是什么样子。'),
    ('A21', 'wrong', 'The big thing to do is avoid being wrong.', '最重要的，是避免犯错。'),
    ('M8', 'omit', 'There are some things that are so intrinsically dangerous.', ''),
]
LAUGHS = ('A11', 'A21')      # 逐字稿在这几句之后标注 "(Laughter)"
QUOTE_ID = 'A21'             # 问答结束后的金句卡

# 节选：按句子 id 首尾的几段原声，省略处画面先暗下去再亮起，并标出“节选”
QA_SEGMENTS = [('Q2', 'Q4B'), ('A5A', 'A5B'), ('A8', 'M3'), ('M7', 'A21')]
QA_IN_WINDOW = {}
QA_OMITTED = [
    '提问者的致谢与自我介绍，以及“您前面说伯克希尔的鞋业很好、别的鞋业不怎么样”的铺垫（约 14 秒）',
    '巴菲特开口的几句：“你其实是在问耐克和锐步的前景？……我对这两家了解不多。现场就有一位持有大量锐步股票的人。但我对它们没有任何负面看法。”（约 16 秒）：态度上的铺垫；“对更懂那一行的人也许更容易”一句保留了同样的公允',
    '“这不是说它们更差，也不是说我们的企业更好……我没做过功课，就算做了也不确定能看懂”（约 12 秒）：与紧接着的“它们更难理解、对更懂行的人也许更容易”意思相同，成片保留后者',
    '芒格的例子：“很多事本身就会制造麻烦……有三样东西我学会了害怕：建筑师、承包商和一座山”，以及“这样过日子，至少比以为雇个有头衔的人就什么都能办到的人少犯错”（约 33 秒）：与前后两句同义，成片保留“最危险的想法”与“保持简单就不必把思考外包”',
    '问答在“避免犯错”之后继续：芒格引用马克·吐温“矿井是骗子拥有的地洞”，两人谈卖方提供的盈利预测与“不要问理发师你是否需要理发”——这是另一个话题，留给系列里专讲预测的一集',
]

# ------------------------------------------------------------------ 投资启示（本片解读，旁白）
# 逻辑链：概括原观点 → 第一性原理（市场只为结果付钱；环节越多越容易错）→ 正反同一案例：十年赌局（最简单的指数基金 vs 两百多家对冲基金）
#        → 代价与局限：德克斯特鞋业（分辨一尺与七尺本身最难）→ 今天：三个问题与“太难”的篮子 → 收尾
INSIGHT = [
    ('I1', 'recap', '巴菲特的意思是：投资不按难度给分。跨过一尺高的栏，和跳过七尺高的栏，拿到的回报一样。', 0.5),
    ('I2', 'principle', '道理在于，市场只为结果付钱：回报取决于企业将来赚多少、你当初付多少，里面没有一项叫难度。', 0.4),
    ('I3', 'principle', '判断越复杂，要同时猜对的环节就越多：就算每一环都有九成把握，十环全对的机会也只剩三成五。', 0.6),
    ('I5', 'bet', '2008年，巴菲特打了一个十年的赌：他押最简单的标普500指数基金；对手挑了五只母基金，背后是两百多家对冲基金。', 0.4),
    ('I6', 'bet', '十年后，指数基金累计涨了125.8%；五只母基金，最好的87.7%，最差的只有2.8%。', 0.6),
    ('I7', 'dexter', '可最难的，恰恰是分辨哪是一尺、哪是七尺。就在这次大会上，巴菲特说自己看得懂的德克斯特鞋厂，没几年就被海外竞争击垮。', 0.4),
    ('I8', 'dexter', '他为它付出的伯克希尔股票，到2014年价值约57亿美元——他称之为最惨痛的错误。', 0.6),
    ('I10', 'today', '所以面对一只股票，先问三个问题：这门生意我看得懂吗？十年后它大概什么样？要猜对几件事才能赚钱？只要有一个答不上来，就把它放进“太难”的篮子。', 0.6),
    ('I11', 'close', '巴菲特宁愿把自己看得懂的范围想得小一点，也不愿想大。因为在投资里，少犯错，比做难事重要得多。', 0.0),
]
SUMMARY = ('M', 'motto', '投资没有难度系数：跨过一尺的栏，就够了。', 0.0)
ENDQ = None

SAY = {
    'S2': '一九九四年春天，宝洁公司因为两笔复杂的利率掉期合约，一个季度就亏掉了一点五七亿美元。',
    'I5': '二零零八年，巴菲特打了一个十年的赌：他押最简单的标普五百指数基金；对手挑了五只母基金，背后是两百多家对冲基金。',
    'I6': '十年后，指数基金累计涨了百分之一百二十五点八；五只母基金，最好的百分之八十七点七，最差的只有百分之二点八。',
    'I8': '他为它付出的伯克希尔股票，到二零一四年价值约五十七亿美元——他称之为最惨痛的错误。',
}

# ------------------------------------------------------------------ 来源（原始录像 + 事实核查）
ARCHIVE_ITEM = 'youtube-A2J-_BNkqm8'
ARCHIVE_URL = 'https://archive.org/download/youtube-A2J-_BNkqm8/A2J-_BNkqm8.mp4'
CLIP_IN, CLIP_LEN = 4745.0, 300.0        # 全场 1:19:05 起 300 秒："Zone 2." → 耐克与锐步 → 难度系数 → “避免犯错” → 马克·吐温
PIC_BOX = (205, 172, 1720, 786)          # 1920×1080 源里干净的画面区（避开左上角第三方水印与下方烧录字幕，与前两集同一录像）
BROLL = [1500, 6400]                     # 片头用的上午场历史影像（各取 16 秒）
CNBC_CHAPTER = '1994-M38、M39 · Nike and Reebok / “You don’t have to do exceptional things to get exceptional results”'
CNBC_URL = 'https://buffett.cnbc.com/video/1994/04/25/morning-session---1994-berkshire-hathaway-annual-meeting.html'
MEETING_DATE = '1994-04-25'

# 十年赌局（2017 年致股东信 “Here’s the final scorecard for the bet”）：每年的回报 %，2008–2017；D 在 2017 年清盘
BET_YEARS = list(range(2008, 2018))
BET = {
    'A': [-16.5, 11.3, 5.9, -6.3, 3.4, 10.5, 4.7, 1.6, -3.2, 12.2],
    'B': [-22.3, 14.5, 6.8, -1.3, 9.6, 15.2, 4.0, 2.5, 1.9, 10.6],
    'C': [-21.3, 21.4, 13.3, 5.9, 5.7, 8.8, 18.9, 5.4, -1.7, 15.6],
    'D': [-29.3, 16.5, 4.9, -6.3, 6.2, 14.2, 0.7, 1.4, 2.5, None],
    'E': [-30.1, 16.8, 11.9, -2.8, 9.1, 14.4, -2.1, -5.0, 4.4, 18.0],
    'SP': [-37.0, 26.6, 15.1, 2.1, 16.0, 32.3, 13.6, 1.4, 11.9, 21.8],
}
BET_FINAL = {'A': 21.7, 'B': 42.3, 'C': 87.7, 'D': 2.8, 'E': 27.0, 'SP': 125.8}

FACTS = [
    # (用在哪, 事实, 出处)
    ('S2', '宝洁公司 1994 年 1–3 月这个季度的利润表里，计入“$157 million ($102 million after-tax) charge for the close-out of two interest rate swaps”（为两笔利率掉期平仓，税前 1.57 亿美元）；这两笔是与信孚银行（Bankers Trust）做的杠杆利率掉期，宝洁在 1994 年 4 月公布这笔损失',
     'Procter & Gamble Form 10-Q（截至 1994 年 3 月 31 日的季度，1994-05-13 提交 SEC）；Washington Monthly 1994-10「Very Risky Business」'),
    ('背景卡', '1994 年 4 月 25 日伯克希尔股东大会上午场；问答为 CNBC 第 38 章「Nike and Reebok」与第 39 章「“You don’t have to do exceptional things to get exceptional results”」',
     'CNBC Warren Buffett Archive；原始录像 archive.org youtube-A2J-_BNkqm8（全场 1:19:08 起）'),
    ('A5B', 'Brown 指 1991 年收购的 H. H. Brown 鞋业，Dexter 指 1993 年 11 月 7 日收购的德克斯特鞋业', 'Berkshire 1993 年致股东信；1994 年致股东信（“Dexter’s earnings only from the date it was acquired, November 7, 1993”）'),
    ('A15–A16', '“this” 指可口可乐；1993 年底伯克希尔持有 9,340 万股可口可乐，成本 10.24 亿美元，市值 41.68 亿美元（账面浮盈约 31 亿美元，与“30 亿美元税前”吻合）', 'Berkshire 1993 年致股东信持股表'),
    ('冷开场、A12B', '“You don’t have to do exceptional things to get exceptional results.”', 'CNBC 逐字稿 1994-M39'),
    ('I1', '“we concentrated on identifying one-foot hurdles that we could step over rather than because we acquired any ability to clear seven-footers”；“in both business and investments it is usually far more profitable to simply stick with the easy and obvious than it is to resolve the difficult”',
     'Berkshire 1989 年致股东信「Mistakes of the First Twenty-five Years」'),
    ('I1（回声）', '1998 年大会：“this is not like Olympic diving … You get paid just as well for the most simple dive, as long as you execute it all right”；2005 年大会：“we get paid, not for jumping over 7-foot bars, but for stepping over 1-foot bars”',
     'CNBC 逐字稿 1998-M08、2005-A25'),
    ('I3', '“每一环九成把握，十环全对只剩三成五”：0.9 的 10 次方 ≈ 0.349（各环独立时的乘法原理；画面标注“示意”）', '概率乘法原理'),
    ('I5', '2008 年 1 月 1 日起的十年赌局：巴菲特押先锋标普 500 指数基金；对手 Protégé Partners 挑了五只母基金（funds-of-funds），“Those five funds-of-funds in turn owned interests in more than 200 hedge funds”',
     'Berkshire 2016 年、2017 年致股东信'),
    ('I6', '十年累计：标普 500 指数基金 +125.8%（年均 8.5%）；五只母基金 A +21.7%、B +42.3%、C +87.7%、D +2.8%（2017 年清盘，按九年计）、E +27.0%（年均 0.3%–6.5%）；母基金每年固定费用约 2.5%；2008 年五只全部跑赢指数，之后九年每一年整体都落后',
     'Berkshire 2017 年致股东信「Here’s the final scorecard for the bet」'),
    ('I7', '德克斯特鞋业：“What I had assessed as durable competitive advantage vanished within a few years”；“Its competitive strengths, however, were soon to evaporate because of foreign competition. And I simply didn’t see that coming.”',
     'Berkshire 2007 年、2014 年致股东信'),
    ('I8', '1993 年用 25,203 股伯克希尔 A 股（当时价值 4.33 亿美元）买下德克斯特；“the shares I used for the purchase are now worth about $5.7 billion”；“The most gruesome was Dexter Shoe”；2007 年信称其为“the worst deal that I’ve made”（当时算作 35 亿美元）',
     'Berkshire 2007 年、2014 年致股东信；1993 年致股东信'),
    ('I10', '“十年后它大概什么样”对应本段原声 A20（“what it’s going to look like in 10 or 15 years”）；“太难”的篮子（too hard）对应 2005 年大会：“maybe we cast out too many things as being too hard”', 'CNBC 逐字稿 1994-M39、2005-A25'),
    ('I11', '“I’d rather have the … universe … interpret it as being a little … smaller than it really is, than being interpreted as larger than it is.”', 'CNBC 逐字稿 2005-A25'),
]
