"""旁白与双语字幕（全部分镜的唯一文本来源）。

每一行：(段落, 语种, 英文字幕, 中文字幕, 句后停顿秒, 朗读文本或 None)
- 语种 'zh'：中文旁白（本片撰写），英文字幕为其译文。
- 语种 'en'：巴菲特原话，英文字幕逐字取自 CNBC 逐字稿 1994-A22（只删去句首的 But、句首字母大写），
  中文字幕为本片翻译；由 AI 配音朗读，不是巴菲特本人原声。
- 朗读文本为 None 时，中文段读中文字幕、英文段读英文字幕（只为发音做替换时才单独写）。
段落名决定画面（见 render.py 的 VISUALS）。
"""

VOICE = {'zh': 49, 'en': 16}      # Kokoro v1.0：zm_yunjian（中文男声）、am_michael（英文男声）
SPEED = {'zh': 1.0, 'en': 0.98}

LINES = [
    # ---------------------------------------------------------------- 开场（音乐前奏，第一个重拍前结束）
    ('title', 'zh', 'Out of 600+ highlights from 30 years of Berkshire meetings,',
     '巴菲特和芒格三十年的股东大会里，', 0.10, None),
    ('title', 'zh', 'this one ranks No. 1.',
     '六百多条精华，排名第一的是这一段。', 0.55, None),
    ('ask', 'zh', 'In 1994, a shareholder from Canada asked:',
     '1994 年，一位来自加拿大的股东问：', 0.15, '一九九四年，一位来自加拿大的股东问：'),
    ('ask', 'zh', 'How do you and Charlie figure out the intrinsic value of a business?',
     '您和芒格，是怎样算出一家企业的内在价值的？', 0.0, None),

    # ---------------------------------------------------------------- 巴菲特原话（从第一个重拍开始）
    ('dcf', 'en', 'The economic value of any asset, essentially,',
     '任何资产的经济价值，本质上，', 0.12, None),
    ('dcf', 'en', 'is the present value, the appropriate interest rate,',
     '就是以适当的利率折现，', 0.10, None),
    ('dcf', 'en', 'of all the future streams of cash going in or out of the business.',
     '企业未来所有现金流入和流出的现值。', 0.75, None),

    ('fog', 'en', 'And if we don’t have the faintest idea what the future stream is going to look like,',
     '如果我们对未来的现金流会是什么样子毫无头绪，', 0.12, None),
    ('fog', 'en', 'we don’t have the faintest idea what it’s worth, now.',
     '那么我们对它现在值多少钱也毫无头绪。', 0.75, None),

    ('range', 'en', 'So we are looking for things where we feel — fairly high degree of probability —',
     '所以我们寻找的是这样的东西：我们有相当高的把握，', 0.12,
     'So we are looking for things where we feel, fairly high degree of probability,'),
    ('range', 'en', 'that we can come within a range of looking at those numbers out over a period of time,',
     '能把未来一段时间里的这些数字，预测在一个区间之内，', 0.12, None),
    ('range', 'en', 'and then we discount them back.',
     '然后再把它们折现回来。', 0.75, None),

    ('cert', 'en', 'And we are more concerned with the certainty of those numbers',
     '我们更关心这些数字的确定性，', 0.10, None),
    ('cert', 'en', 'than we are with getting the one that looks absolutely the cheapest,',
     '而不是去找那个看起来绝对最便宜、', 0.10, None),
    ('cert', 'en', 'but based upon numbers that we don’t have any — we don’t have great confidence in.',
     '却建立在我们并没有多大把握的数字之上的东西。', 0.75,
     'but based upon numbers that we don’t have any, we don’t have great confidence in.'),

    ('report', 'en', 'There are no answers in the financial statements.',
     '财务报表里没有答案，', 0.25, None),
    ('report', 'en', 'There are guidelines to enable you to figure out the answer.',
     '只有帮助你找到答案的指引。', 0.30, None),
    ('report', 'en', 'And to figure out that answer, you have to understand something about business.',
     '要找到答案，你必须懂一些生意。', 0.45, None),
    ('report', 'en', 'You don’t have to understand a lot about mathematics. I mean, the math is not complicated.',
     '你不需要懂很多数学。我是说，数学并不复杂。', 0.20, None),
    ('report', 'en', 'But you do have to understand something about the business.',
     '但你确实必须懂这门生意。', 0.75, None),

    ('check', 'en', 'You would try to figure out what you are laying out currently,',
     '你会设法弄清楚：你现在要付出多少，', 0.10, None),
    ('check', 'en', 'and what you are likely to get back over time,',
     '随着时间推移可能收回多少，', 0.10, None),
    ('check', 'en', 'and how certain you felt about getting it,',
     '你对收回它有多大把握，', 0.10, None),
    ('check', 'en', 'and how it compared to other alternatives.',
     '以及它和其他选择相比如何。', 0.30, None),
    ('check', 'en', 'That’s all we do, we just do it with large businesses, basically.',
     '我们做的就是这些，只不过对象是大企业而已。', 0.90, None),

    # ---------------------------------------------------------------- 投资启示（中文旁白）
    ('lesson', 'zh', 'The first step in valuation isn’t picking a discount rate.',
     '估值的第一步，不是选折现率，', 0.10, None),
    ('lesson', 'zh', 'It’s judging whether you can forecast a range of cash flows with reasonable confidence.',
     '而是判断：能不能有合理的把握，预测现金流的区间。', 0.40, None),
    ('lesson', 'zh', 'If you can’t, put it in the “too hard” pile.',
     '不能，就放进“太难”的那一堆；', 0.15, None),
    ('lesson', 'zh', 'If you can, then compare it with the price.',
     '能，再去和价格比较。', 0.45, None),
    ('motto', 'zh', 'Certainty comes before cheapness.',
     '确定性，优先于便宜。', 0.0, '确定性，优先于便宜！'),
]

# 画面上的出处信息（逐字稿章节与估算时间来自 巴芒股东大会数据库/output/entries.json 的 1994-A22）
SOURCE_ZH = '出处：CNBC 巴菲特档案 · 1994 年股东大会下午场 · 第 22 章'
SOURCE_EN = 'Calculating intrinsic value · 约 0:59:09–1:01:27（估算）'
DISCLOSE = '英文原话取自 CNBC 逐字稿 · AI 配音朗读，非巴菲特本人原声'
