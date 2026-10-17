"""《伯克希尔股东大会投资智慧录》第一集 · 内在价值 —— 全部文本的唯一来源。

INTRO      系列片头口播（用户提供的系列介绍稿，只调整了断句；最后两句按本期原始问答重写）
ORIGINAL   1994 年股东大会下午场原始录音的字幕（英文逐字取自 CNBC 逐字稿 1994-A22，中文为本片翻译）
INSIGHT    投资启示解读（本片撰写的旁白；不是巴菲特或芒格的原话）
SUMMARY    一句话总结

每条口播：(id, 场景, 朗读文本, 句后停顿秒)。字幕按全角标点自动断成短句显示。
SAY 里是只为发音调整的朗读文本（屏幕字幕仍用原文）。
"""

# ------------------------------------------------------------------ 配音参数
# 主引擎：Google Gemini TTS（需要环境变量 GEMINI_API_KEY）。风格指令放在 speech_metadata.style，原样使用，不改写。
GEMINI_MODEL = 'gemini-3.8-flash-tts'
GEMINI_VOICE = 'charon'            # 男低音，沉稳
GEMINI_STYLE = ('A steady authoritative male narrator for a financial documentary. '
                'Measured and deliberate pace, calm confidence, clear enunciation, quiet gravitas.')
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/interactions'
# 按段落成组合成（同一段内的句子一次念完，语气连贯；段落之间的停顿由时间线控制）
TTS_GROUPS = [('S1',), ('S2', 'S3'), ('S4',), ('S5',), ('S6', 'S7'), ('S8',), ('S9', 'S10', 'S11'),
              ('I1', 'I2', 'I3'), ('I4', 'I6'), ('I7', 'I9'), ('I11', 'I12', 'I13'), ('I14', 'I15'), ('I16', 'I17'), ('M',)]
# 关键句前的停顿 / 换气标签（只进朗读稿，不进字幕）
TAGS = {'S5': '<breath>', 'S9': '<breath>', 'S11': '<short pause>', 'I3': '<short pause>', 'I7': '<breath>',
        'I11': '<breath>', 'I15': '<short pause>', 'I17': '<breath>', 'M': '<breath>'}
# 备用引擎：微软 Edge 神经网络语音「云健」（TTS_ENGINE=edge 或没有 GEMINI_API_KEY 时使用）
VOICE = 'zh-CN-YunjianNeural'
RATE, PITCH = '-7%', '-3Hz'

# ------------------------------------------------------------------ 冷开场（原声）
# 冷开场直接用本期原始录音里的一句（与后面完整问答中的 A7–A8 是同一段录音）
COLD_IDS = ('A7', 'A8')

# ------------------------------------------------------------------ 系列片头口播
INTRO = [
    ('S1', 'title', '大家好。从今天开始，我们将开启一个全新的系列——《巴菲特与芒格：伯克希尔股东大会投资智慧录》。', 0.75),
    ('S2', 'years', '我们将系统回顾，自1994年以来的历届伯克希尔股东大会，', 0.25),
    ('S3', 'themes', '精选巴菲特与芒格关于价值投资、企业估值、商业模式、竞争护城河、风险管理、市场周期、投资心理和人生智慧的经典问答。', 0.8),
    ('S4', 'method', '每一期，我们都会先呈现珍贵的原始视频片段，再结合真实的商业案例，深入解读其中蕴含的投资逻辑、思维方法与人生哲理。', 0.8),
    ('S5', 'why', '我们不仅要知道投资大师说了什么，更要理解，他们为什么这样思考。', 0.7),
    ('S6', 'life', '如何洞察企业价值，理性应对市场波动，规避投资风险；', 0.3),
    ('S7', 'life', '又如何运用智慧，做出更好的人生选择，收获真正的幸福。', 0.75),
    ('S8', 'calm', '希望通过这一系列，我们不仅能够建立更系统的投资框架，也能逐渐形成更加理性、清醒、豁达的处世哲学。', 0.9),
    ('S9', 'back', '下面，让我们回到1994年的伯克希尔股东大会。', 0.45),
    ('S10', 'back', '在下午的问答环节，一位来自加拿大的股东，向巴菲特和芒格提出了一个所有投资者都绕不开的问题：', 0.35),
    ('S11', 'question', '一家企业的内在价值，究竟该怎么算？', 0.0),
]

# ------------------------------------------------------------------ 原始问答（字幕）
# 来源：CNBC Warren Buffett Archive 逐字稿 1994 Afternoon Session 第 22 章「Calculating intrinsic value」
# 英文只省略口头重起的半句（"Well, the —" 的 "the —"、"Now that —"、"The —"、"It —"），其余逐字保留。
ORIGINAL = [
    ('Z', 'ask', 'Zone 2?', '请二号区提问。'),
    ('Q0', 'ask', 'Thank you. Sean Barry, Regina, Canada.', '谢谢。我是肖恩·巴里，来自加拿大里贾纳。'),
    ('Q1', 'ask', 'Mr. Buffett, you’ve indicated that most of us in this room', '巴菲特先生，您曾说过，在座的大多数人'),
    ('Q2', 'ask', 'could acquire a lot of the information that you and Charlie acquire through the annual reports.',
     '都能像您和查理一样，从年报中获得大量信息。'),
    ('Q3', 'ask', 'Yet you both also indicated that the GAAP rules, a lot of times, leave a little to be desired.',
     '但二位也说过，公认会计准则很多时候并不尽如人意。'),
    ('Q4', 'ask', 'Could you perhaps give an indication as to how you and Charlie come up with the economic value,',
     '能否请您谈谈，您和查理是如何得出经济价值——'),
    ('Q5', 'ask', 'or the intrinsic value, of the businesses that you finally decide to invest in?',
     '也就是你们最终决定投资的那些企业的内在价值？'),
    ('Q6', 'ask', 'And a little bit about the process that you go through with that? Thank you.',
     '再讲讲你们这样做的过程？谢谢。'),
    ('A1', 'open', 'Well, in the 1992 annual report, we discuss that a fair amount.', '嗯，我们在1992年的年报里对此谈得不少。'),
    ('A2', 'dcf', 'But the economic value of any asset, essentially,', '不过，任何资产的经济价值，本质上，'),
    ('A3', 'dcf', 'is the present value, the appropriate interest rate,', '就是按适当的利率，'),
    ('A4', 'dcf', 'of all the future streams of cash going in or out of the business.', '把这门生意未来所有现金流入和流出折算成的现值。'),
    ('A5', 'fog', 'And there are all kinds of businesses that Charlie and I', '有各种各样的企业，查理和我'),
    ('A6', 'fog', 'don’t think we have the faintest idea what that future stream will look like.',
     '都觉得自己完全不知道它们未来的现金流会是什么样子。'),
    ('A7', 'fog', 'And if we don’t have the faintest idea what the future stream is going to look like,',
     '而如果我们完全不知道未来的现金流会是什么样子，'),
    ('A8', 'fog', 'we don’t have the faintest idea what it’s worth, now.', '我们就完全不知道它现在值多少钱。'),
    ('A9', 'dissonance', 'So, if you think you know what the price of a stock should be today,', '所以，如果你觉得自己知道一只股票今天该值多少钱，'),
    ('A10', 'dissonance', 'but you don’t think you have any idea what the stream of cash will be over the next 20 years,',
     '却对它未来20年的现金流毫无概念，'),
    ('A11', 'dissonance', 'you’ve got cognitive dissonance, I guess, is what they call it.', '那你就陷入了——我想大家管这叫——“认知失调”。'),
    ('A12', 'range', 'So we are looking for things where we feel — fairly high degree of probability —',
     '所以，我们寻找的是这样的东西：我们有相当高的把握，'),
    ('A13', 'range', 'that we can come within a range of looking at those numbers out over a period of time,',
     '能把未来一段时间里的这些数字，估计在一个区间之内，'),
    ('A14', 'range', 'and then we discount them back.', '然后再把它们折现回来。'),
    ('A15', 'cert', 'And we are more concerned with the certainty of those numbers', '我们更在意这些数字的确定性，'),
    ('A16', 'cert', 'than we are with getting the one that looks absolutely the cheapest,', '而不是去找那个看起来绝对最便宜、'),
    ('A17', 'cert', 'but based upon numbers that we don’t have any — we don’t have great confidence in.',
     '却建立在我们并没有多大把握的数字之上的东西。'),
    ('A18', 'cert', 'And that’s basically what economic value is all about.', '这基本上就是经济价值的全部要义。'),
    ('A19', 'report', 'The numbers in any accounting report mean nothing, per se, as to economic value.',
     '任何会计报告里的数字，本身都不代表经济价值。'),
    ('A20', 'report', 'They are guidelines to tell you something about how to get at economic value.',
     '它们只是指引，告诉你该如何去求得经济价值。'),
    ('A21', 'report', 'But they don’t tell you anything.', '但它们本身什么也没告诉你。'),
    ('A22', 'report', 'There are no answers in the financial statements.', '财务报表里没有答案，'),
    ('A23', 'report', 'There are guidelines to enable you to figure out the answer.', '只有帮你找出答案的指引。'),
    ('A24', 'report', 'And to figure out that answer, you have to understand something about business.', '要找出答案，你必须懂一些生意。'),
    ('A25', 'report', 'You don’t have to understand a lot about mathematics.', '你不需要懂很多数学。'),
    ('A25b', 'report', 'I mean, the math is not complicated.', '我是说，数学并不复杂。'),
    ('A26', 'report', 'But you do have to understand something about the business.', '但你确实得懂这门生意。'),
    ('A27', 'check', 'But that’s the same thing you would do if you were going to buy an apartment house,',
     '这和你打算买一栋公寓楼时会做的事一样，'),
    ('A28', 'check', 'or a farm, or any other small business you might be interested in.', '或者买一座农场，或任何你感兴趣的小生意。'),
    ('A29', 'check', 'You would try to figure out what you are laying out currently,', '你会设法弄清楚：你现在要付出多少，'),
    ('A30', 'check', 'and what you are likely to get back over time,', '将来大概能收回多少，'),
    ('A31', 'check', 'and how certain you felt about getting it,', '你对收回它有多大把握，'),
    ('A32', 'check', 'and how it compared to other alternatives.', '以及它与其他选择相比如何。'),
    ('A33', 'check', 'That’s all we do, we just do it with large businesses, basically.', '我们做的就是这些，只不过对象基本上是大企业。'),
    ('A34', 'massage', 'The accounting figures are very helpful to us,', '会计数字对我们很有帮助，'),
    ('A35', 'massage', 'in the sense that they generally guide us to what we should be thinking about.',
     '因为它们通常会引导我们去思考该思考的问题。'),
    ('A36', 'massage', 'And of course, if we find numbers where it looks like people are taking', '当然，如果我们发现某些数字看起来是有人'),
    ('A37', 'massage', 'the most optimistic interpretation of things that they can under GAAP and all of that,',
     '在会计准则之类的框架下，做了所能做到的最乐观的解释，'),
    ('A38', 'massage', 'we get very worried about people who look like they massage the numbers in any way.',
     '我们就会非常担心——担心那些看起来在以任何方式粉饰数字的人。'),
    ('A39', 'massage', 'And there are plenty of people that do.', '而这样做的人，多得是。'),
]
LAUGH_AFTER = 'A11'            # 原声在 A11 之后有现场笑声（逐字稿标注 "(Laughter)"）

# ------------------------------------------------------------------ 投资启示（本片解读，旁白）
INSIGHT = [
    ('I1', 'formula', '巴菲特的回答，可以浓缩成一句话：一家企业的价值，等于它未来全部现金流的折现值。', 0.55),
    ('I2', 'formula', '这个公式，出自1938年威廉姆斯的《投资价值理论》。', 0.45),
    ('I3', 'formula', '公式人人都会写，真正的难点，是分子上那个“未来现金流”。', 0.65),
    ('I4', 'bond', '巴菲特在1992年的致股东信里说：债券的票息写在合同上；股票的“票息”，却要投资者自己去估计。', 0.5),
    ('I6', 'bond', '未来估错了，折现率再精确，也只是精确地犯错。', 0.7),
    ('I7', 'sees', '看得清，是什么样子？1972年，巴菲特和芒格用2500万美元，买下了喜诗糖果。', 0.3),
    ('I9', 'sees', '销量每年只增长百分之二，现金流却稳得出奇：到2007年，累计贡献13.5亿美元税前利润，追加投入只有3200万。', 0.7),
    ('I11', 'usair', '看不清，又是什么样子？1989年，伯克希尔用3.58亿美元，买入美国航空的优先股。', 0.3),
    ('I12', 'usair', '1994年9月，美国航空停付股息；年底，这笔投资被减记到每一美元只剩二十五美分。', 0.3),
    ('I13', 'usair', '巴菲特对自己的评价是：草率的分析。', 0.7),
    ('I14', 'limit', '这套方法的代价，是错过。芒格坦言，没买谷歌，是他们在科技领域最大的错误。', 0.35),
    ('I15', 'limit', '但错过，只是少赚；看错，却可能是永久的亏损。', 0.7),
    ('I16', 'today', '今天，能看清十年现金流的企业越来越少，这条标准也就越发珍贵。', 0.5),
    ('I17', 'today', '财务报表只给你指引；答案，在你对生意的理解里。', 0.0),
]
SUMMARY = ('M', 'motto', '先问看不看得清，再问便不便宜。', 0.0)

SAY = {
    'S1': '大家好。从今天开始，我们将开启一个全新的系列，巴菲特与芒格，伯克希尔股东大会投资智慧录。',
    'I4': '巴菲特在1992年的致股东信里说：债券的票息写在合同上；股票的票息，却要投资者自己去估计。',
    'I7': '看得清，是什么样子？1972年，巴菲特和芒格用两千五百万美元，买下了喜诗糖果。',
    'I9': '销量每年只增长百分之二，现金流却稳得出奇：到2007年，累计贡献十三点五亿美元税前利润，追加投入只有三千二百万。',
    'I11': '看不清，又是什么样子？1989年，伯克希尔用三点五八亿美元，买入美国航空的优先股。',
    'I13': '巴菲特对自己的评价是：草率的分析。',
    'I3': '公式人人都会写，真正的难点，是分子上那个，未来现金流。',
}

# ------------------------------------------------------------------ 来源（原始录音 + 事实核查）
ARCHIVE_ITEM = 'youtube-A2J-_BNkqm8'
ARCHIVE_URL = 'https://archive.org/download/youtube-A2J-_BNkqm8/A2J-_BNkqm8.mp4'
CLIP_IN, CLIP_LEN = 11800.0, 280.0       # 全场 3:16:40 起 280 秒：覆盖 "Zone 2?" 到回答结束
# 画面素材：同一份全场录像的上午场（有现场画面）。只截 4:3 画面区，避开第三方水印和烧录字幕。
BROLL = [200, 1500, 6000, 7790, 8700]    # 各取 16 秒，作片头与过场的历史影像
STILL_T = 7800.0                          # 巴菲特托腮倾听的上午场静帧，作原声段的底图
PIC_BOX = (205, 172, 1720, 786)           # 1920×1080 源里干净的画面区（x0, y0, x1, y1）

CNBC_CHAPTER = '1994-A22 · Calculating intrinsic value'
CNBC_URL = 'https://buffett.cnbc.com/video/1994/04/25/afternoon-session---1994-berkshire-hathaway-annual-meeting.html'

FACTS = [
    # (用在哪, 事实, 出处)
    ('I2', 'John Burr Williams《The Theory of Investment Value》(1938) 提出价值方程', 'Berkshire 1992 年致股东信「Investment Value」一节'),
    ('I4-I5', '债券有票息和到期日，股票的“票息”要分析师自己估计', 'Berkshire 1992 年致股东信'),
    ('I7-I10', '1972 年以 2500 万美元买下 See’s；当年税前利润不到 500 万；销量 1600 万磅→3100 万磅（年增约 2%）；2007 年税前利润 8200 万；累计税前 13.5 亿；追加资本 3200 万',
     'Berkshire 2007 年致股东信'),
    ('I11-I13', '1989 年 3.58 亿美元买入 USAir 优先股；1994 年 9 月暂停派息；年底减记至 8950 万（每美元 25 美分）；“sloppy analysis”；无差异化行业成本决定生存',
     'Berkshire 1994 年致股东信'),
    ('I14', '芒格：回头看，科技领域最大的错误是谷歌——“我们本来足够聪明，却没有去做”；巴菲特：“But I blew it”', 'CNBC 逐字稿 2017 年股东大会第 12 章「Making mistakes with IBM, Google, and Amazon」'),
]
