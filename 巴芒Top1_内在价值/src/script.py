"""全部字幕与旁白文本（唯一文本来源）。

ORIGINAL：1994 年股东大会下午场原始录音（股东提问 + 巴菲特回答）的字幕。
  英文逐字取自 CNBC 逐字稿 1994-A22，只省略口头重起的半句（如 “Well, the —” 里的 “the —”、
  “Now that —”、“(Laughter) The —”、“It —”）；中文为本片翻译。
  字幕时间由 align.py 用语音识别的逐词时间戳对齐到原声。
  每条：(id, 段落, 英文, 中文)；段落名决定画面（见 render.py）。

NARRATION：原片之后的“投资启示”中文解说（本片撰写，AI 配音）。
  每条：(id, 段落, 中文, 英文译文, 句后停顿秒)
"""

ORIGINAL = [
    # ---------------------------------------------------------------- 股东提问
    ('Q1', 'ask', 'Mr. Buffett, you’ve indicated that most of us in this room',
     '巴菲特先生，您曾说过，在座的大多数人'),
    ('Q2', 'ask', 'could acquire a lot of the information that you and Charlie acquire through the annual reports.',
     '都能从年报中获得您和查理掌握的大量信息。'),
    ('Q3', 'ask', 'Yet you both also indicated that the GAAP rules, a lot of times, leave a little to be desired.',
     '但您二位也说过，会计准则很多时候并不尽如人意。'),
    ('Q4', 'ask', 'Could you perhaps give an indication as to how you and Charlie come up with the economic value,',
     '能否请您谈谈，您和查理是如何得出经济价值，'),
    ('Q5', 'ask', 'or the intrinsic value, of the businesses that you finally decide to invest in?',
     '也就是你们最终决定投资的那些企业的内在价值？'),
    ('Q6', 'ask', 'And a little bit about the process that you go through with that? Thank you.',
     '再讲讲你们这样做的过程？谢谢。'),
    # ---------------------------------------------------------------- 巴菲特回答
    ('A1', 'answer', 'Well, in the 1992 annual report, we discuss that a fair amount.',
     '嗯，我们在 1992 年的年报里对此讨论得不少。'),
    ('A2', 'dcf', 'But the economic value of any asset, essentially,',
     '但任何资产的经济价值，本质上，'),
    ('A3', 'dcf', 'is the present value, the appropriate interest rate,',
     '就是按适当的利率折现后，'),
    ('A4', 'dcf', 'of all the future streams of cash going in or out of the business.',
     '企业未来全部现金流入和流出的现值。'),
    ('A5', 'fog', 'And there are all kinds of businesses that Charlie and I',
     '有各种各样的企业，查理和我'),
    ('A6', 'fog', 'don’t think we have the faintest idea what that future stream will look like.',
     '觉得自己完全不知道它们未来的现金流会是什么样子。'),
    ('A7', 'fog', 'And if we don’t have the faintest idea what the future stream is going to look like,',
     '而如果我们完全不知道未来的现金流会是什么样子，'),
    ('A8', 'fog', 'we don’t have the faintest idea what it’s worth, now.',
     '我们也就完全不知道它现在值多少钱。'),
    ('A9', 'dissonance', 'So, if you think you know what the price of a stock should be today,',
     '所以，如果你认为自己知道一只股票今天该值多少，'),
    ('A10', 'dissonance', 'but you don’t think you have any idea what the stream of cash will be over the next 20 years,',
     '却对它未来 20 年的现金流毫无概念，'),
    ('A11', 'dissonance', 'you’ve got cognitive dissonance, I guess, is what they call it.',
     '那你就有了所谓的“认知失调”吧。'),
    ('A12', 'range', 'So we are looking for things where we feel — fairly high degree of probability —',
     '所以我们寻找的是这样的东西：我们有相当高的把握，'),
    ('A13', 'range', 'that we can come within a range of looking at those numbers out over a period of time,',
     '能把未来一段时间里的这些数字，预测在一个区间之内，'),
    ('A14', 'range', 'and then we discount them back.',
     '然后再把它们折现回来。'),
    ('A15', 'cert', 'And we are more concerned with the certainty of those numbers',
     '我们更关心这些数字的确定性，'),
    ('A16', 'cert', 'than we are with getting the one that looks absolutely the cheapest,',
     '而不是去找那个看起来绝对最便宜、'),
    ('A17', 'cert', 'but based upon numbers that we don’t have any — we don’t have great confidence in.',
     '却建立在我们并没有多大把握的数字之上的东西。'),
    ('A18', 'cert', 'And that’s basically what economic value is all about.',
     '这基本上就是经济价值的全部含义。'),
    ('A19', 'report', 'The numbers in any accounting report mean nothing, per se, as to economic value.',
     '任何会计报告里的数字，本身都不代表经济价值。'),
    ('A20', 'report', 'They are guidelines to tell you something about how to get at economic value.',
     '它们只是指引，告诉你该如何去求得经济价值。'),
    ('A21', 'report', 'But they don’t tell you anything.',
     '但它们本身什么也说明不了。'),
    ('A22', 'report', 'There are no answers in the financial statements.',
     '财务报表里没有答案，'),
    ('A23', 'report', 'There are guidelines to enable you to figure out the answer.',
     '只有帮助你找到答案的指引。'),
    ('A24', 'report', 'And to figure out that answer, you have to understand something about business.',
     '而要找到答案，你必须懂一些生意。'),
    ('A25', 'report', 'You don’t have to understand a lot about mathematics. I mean, the math is not complicated.',
     '你不需要懂很多数学。我是说，数学并不复杂。'),
    ('A26', 'report', 'But you do have to understand something about the business.',
     '但你确实必须懂这门生意。'),
    ('A27', 'check', 'But that’s the same thing you would do if you were going to buy an apartment house,',
     '这和你打算买一栋公寓楼时会做的事情一样，'),
    ('A28', 'check', 'or a farm, or any other small business you might be interested in.',
     '或者买一座农场、任何你感兴趣的小生意。'),
    ('A29', 'check', 'You would try to figure out what you are laying out currently,',
     '你会设法弄清楚：你现在要付出多少，'),
    ('A30', 'check', 'and what you are likely to get back over time,',
     '随着时间推移可能收回多少，'),
    ('A31', 'check', 'and how certain you felt about getting it,',
     '你对收回它有多大把握，'),
    ('A32', 'check', 'and how it compared to other alternatives.',
     '以及它和其他选择相比如何。'),
    ('A33', 'check', 'That’s all we do, we just do it with large businesses, basically.',
     '我们做的就是这些，只不过对象是大企业而已。'),
    ('A34', 'massage', 'The accounting figures are very helpful to us,',
     '会计数字对我们非常有帮助，'),
    ('A35', 'massage', 'in the sense that they generally guide us to what we should be thinking about.',
     '因为它们通常会引导我们去思考该思考的东西。'),
    ('A36', 'massage', 'And of course, if we find numbers where it looks like people are taking',
     '当然，如果我们发现某些数字看起来是有人'),
    ('A37', 'massage', 'the most optimistic interpretation of things that they can under GAAP and all of that,',
     '在会计准则允许的范围内，做了最乐观的解释，'),
    ('A38', 'massage', 'we get very worried about people who look like they massage the numbers in any way.',
     '我们就会非常担心那些看起来在以任何方式粉饰数字的人。'),
    ('A39', 'massage', 'And there are plenty of people that do.',
     '而这样做的人多得是。'),
]

NARRATION = [
    ('L1', 'lesson', '估值的第一步，并不是挑选折现率。',
     'The first step in valuation is not choosing a discount rate.', 0.55),
    ('L2a', 'lesson', '而是先问自己一个问题：',
     'It is asking yourself one question:', 0.3),
    ('L2b', 'lesson', '这家企业未来的现金流，能否被有把握地预测在一个区间之内？',
     'can this business’s future cash flows be forecast, with confidence, within a range?', 0.75),
    ('L3', 'lesson', '如果不能，就把它放进“太难”的那一堆，价格再诱人，也不必理会。',
     'If not, it goes into the “too hard” pile, however tempting the price.', 0.6),
    ('L4', 'lesson', '如果能，再把它的价值，与价格放在一起比较。',
     'If so, only then do you weigh its value against its price.', 0.85),
    ('M', 'motto', '在巴菲特看来，确定性，比便宜更重要。',
     'For Buffett, certainty matters more than cheapness.', 0.0),
]
# 只为发音调整的朗读文本（字幕不变）
SAY = {'L3': '如果不能，就把它放进太难的那一堆，价格再诱人，也不必理会。'}

# 解说配音：sherpa-onnx Kokoro v1.1-zh 的 zm_015（speaker id 64），语速 0.9
VOICE_ID, VOICE_SPEED = 64, 0.9

# 原始录音来源：archive.org 收录的 1994 年股东大会全场录像（下午场在 CNBC 档案中只有音频）
ARCHIVE_URL = 'https://archive.org/download/youtube-A2J-_BNkqm8/A2J-_BNkqm8.mp4'
CLIP_IN, CLIP_LEN = 11800.0, 280.0     # 从全场 3:16:40 起取 280 秒，覆盖提问与完整回答

SOURCE_ZH = '原声：1994 年伯克希尔股东大会下午场 · CNBC 逐字稿第 22 章'
SOURCE_EN = 'Calculating intrinsic value · 下午场约 45:39–49:08'
ORIG_LABEL = '1994 年原始录音 · 本场仅存音频，无现场画面'
VO_LABEL = '解说为 AI 配音'
