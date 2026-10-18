"""《AI 越快，越要慢》全部文字内容：旁白、引语卡、数据。

规则：
- QUOTES 里的英文是原话（来源、时间戳见 SOURCES.md），中文是本片译文。
- NARRATION 是 AI 旁白（Gemini TTS），属于本片的解读，不代表任何大师原话。
- 所有数字都在 MATH / DATA 里集中计算或标注出处，画面只引用这里的值。
"""
import math

TITLE = 'AI 越快，越要慢'
SUBTITLE = '复利真正的秘密，不是更快，而是不失去'

# ------------------------------------------------------------------ 旁白（id -> 文本）
NARRATION = {
    'N01': 'AI 正在以前所未有的速度，改变世界。',
    'N02': '模型不断迭代，知识快速贬值，曾经的优势，随时可能消失。',
    'N03': '二〇二六年十月，李录在哥伦比亚商学院，这样形容这一波 AI。',
    'N04': '既然一切都在加速，我们为什么还需要长期主义？到底什么，值得我们积累几十年？',
    'N05': '在那场格雷厄姆与多德年度午餐会的最后，李录谈到了复利。他先提醒，人性容易滑向零和与短期。',
    'N06': '然后，他指出了另一条路。',
    'N07': '以及，他对复利最朴素的定义。',
    'N08': '复利，首先不是更快，而是不失去。具体的工具会过时，但知识、判断力、信任与信誉，在适当的条件下，可以一层一层地叠加。',
    'N09': '巴菲特在二〇二二年的股东信里，算过一笔账。',
    'N10': '股价每天都在波动；真正复利的，是企业创造价值的能力。',
    'N11': '而前提是，你真的看得懂。',
    'N12': '但不失去，不等于永远不下跌。伯克希尔的股价，就曾四次大跌，最深接近六成。',
    'N13': '芒格的说法，更加直接。',
    'N14': '暂时的回撤可以等待；可怕的是永久损失：看错企业，或者借钱持股、被迫低价卖出。',
    'N16': '回到第一性原理。复利是乘法：每一年的结果，都乘在上一年之上。',
    'N17': '乘法会把微小的差异，放大成鸿沟；也会让一次重大损失，拖住此后的每一年。',
    'N18': '每年加百分之十，三十年后，是十七点四倍。每年减百分之十，只剩百分之四。',
    'N19': '一次永久性的腰斩，需要翻倍，才能回到原点。按每年百分之十计算，要七年多。',
    'N20': '只要价值仍在、不被迫卖出，暂时的下跌可以等待；真正改写结果的，是不可逆的损失。',
    'N21': '金钱如此，知识、信任、技能与健康，也是如此。',
    'N22': '在变化的世界里，持续积累真正有价值的东西，并尽可能避免不可逆的损失。',
    'N23': '变化越快，越需要知道，什么值得长期积累。',
}

# 屏幕字幕用的写法（数字用阿拉伯数字，便于阅读；朗读文本用汉字避免 TTS 读错）
CAPTIONS = {
    'N03': '2026 年 10 月，李录在哥伦比亚商学院，这样形容这一波 AI。',
    'N09': '巴菲特在 2022 年的股东信里，算过一笔账。',
    'N12': '但"不失去"，不等于永远不下跌。伯克希尔的股价，就曾四次大跌，最深接近六成。',
    'N18': '每年 +10%，30 年后是 17.4 倍。每年 −10%，只剩 4%。',
    'N19': '一次永久性的腰斩（−50%），需要翻倍（+100%）才能回到原点。按每年 10% 计算，要 7 年多。',
}

# ------------------------------------------------------------------ 引语卡（英文原话 + 本片中文译文 + 出处）
LILU_EVENT = '2026.10.05 · 哥伦比亚商学院 · 第 36 届格雷厄姆与多德年度午餐会'
LILU_SRC = 'Columbia Business School 官方录像'
QUOTES = {
    'Q_PACE': dict(who='李录', en='"…the pace of change, the scale that is involved… they\'re all incredibly unprecedented."',
                   zh='“……变化的速度、涉及的规模……都前所未有。”', src=LILU_EVENT, ts='录像 0:18:18'),
    'Q_USELESS': dict(who='李录', en='"Whatever you learn today is useless tomorrow. You don\'t accumulate."',
                      zh='“今天学到的，明天就没用了。你积累不下来。”', src=LILU_EVENT, ts='录像 1:24:18',
                      ctx='谈零和、短期的人性倾向时'),
    'Q_KNOW': dict(who='李录', en='"If you can compound your knowledge in a sustainable fashion, eventually you can compound your capital as well."',
                   zh='“如果你能让知识以可持续的方式复利增长，最终，你的资本也能复利增长。”', src=LILU_EVENT, ts='录像 1:23:03'),
    'Q_CORE': dict(who='李录', en='"The basic idea of compounding is you don\'t lose what you already have."',
                   zh='“复利的基本理念，是不要失去你已经拥有的东西。”', src=LILU_EVENT, ts='录像 1:26:50'),
    'Q_CORE2': dict(who='李录', en='"That includes your knowledge… your trusting relationship… the wisdom, and even your health."',
                    zh='“这包括你的知识、你基于信任的关系、智慧，甚至健康。”', src=LILU_EVENT, ts='录像 1:26:59'),
    'Q_COKE': dict(who='巴菲特', en='"Growth occurred every year, just as certain as birthdays."',
                   zh='“增长每年都在发生，就像生日一样确定。”', src='2022 年致伯克希尔股东信', ts='"The Secret Sauce" 一节'),
    'Q_TIME': dict(who='巴菲特', en='"Time is the friend of the wonderful business, the enemy of the mediocre."',
                   zh='“时间是优秀企业的朋友，平庸企业的敌人。”', src='1989 年致伯克希尔股东信', ts=''),
    'Q_CIRCLE': dict(who='巴菲特', en='"The size of that circle is not very important; knowing its boundaries, however, is vital."',
                     zh='“能力圈的大小并不重要；知道它的边界，才至关重要。”', src='1996 年致伯克希尔股东信', ts=''),
    'Q_EDGE': dict(who='李录', en='"…the most important concept of a circle of competence is really knowing the edge of it."',
                   zh='“能力圈最重要的，是真正知道它的边缘。”', src=LILU_EVENT, ts='录像 0:08:30'),
    'Q_MUNGER50': dict(who='芒格', en='"…if you\'re not willing to react with equanimity to a market price decline of 50% two or three times a century, you\'re not fit to be a common shareholder…"',
                       zh='“……如果你不能平静面对一个世纪两三次、50% 的市价下跌，你就不适合做普通股股东……”',
                       src='BBC 访谈 · 2009 年 10 月', ts='访谈 0:39'),
    'Q_DEBT': dict(who='巴菲特', en='"This table offers the strongest argument I can muster against ever using borrowed money to own stocks."',
                   zh='“这张表，是我能给出的反对借钱买股票的最有力论据。”', src='2017 年致伯克希尔股东信', ts=''),
    'Q_REPUTE': dict(who='巴菲特', en='"Lose money for the firm, and I will be understanding. Lose a shred of reputation for the firm, and I will be ruthless."',
                     zh='“让公司亏钱，我能理解；让公司损失一丝声誉，我将毫不留情。”',
                     src='1991.09.04 · 美国众议院听证会（所罗门国债投标丑闻）', ts='C-SPAN 录像'),
    'Q_TRUST': dict(who='芒格', en='"The highest form that civilization can reach is a seamless web of deserved trust."',
                    zh='“文明所能达到的最高形式，是一张由值得的信任编织成的无缝之网。”', src='2007 年南加州大学法学院毕业演讲', ts='（李录在本次对谈 1:25:04 亦引用此语）'),
}

# ------------------------------------------------------------------ 数据（均有出处，见 SOURCES.md）
DATA = dict(
    coke_div_1994=75, coke_div_2022=704,          # 百万美元，2022 年股东信
    coke_cost=1.3,                                # 十亿美元
    brk_dips=[('1973.03–1975.01', 59.1), ('1987.10.02–10.27', 37.1), ('1998.06–2000.03', 48.9), ('2008.09–2009.03', 50.7)],  # 2017 年股东信
    brk_cagr_1965_2017=20.9,                      # 每股市值年复合，2017 年股东信首页
)
DATA['coke_cagr'] = (DATA['coke_div_2022'] / DATA['coke_div_1994']) ** (1 / (2022 - 1994)) - 1   # ≈ 8.3%

# ------------------------------------------------------------------ 数学（画面上的每个数都从这里来）
YEARS = 30
MATH = dict(
    up=1.1 ** YEARS,                 # 17.449
    down=0.9 ** YEARS,               # 0.04239
    ratio=(1.1 / 0.9) ** YEARS,      # 411.6
    recover_years=math.log(2) / math.log(1.1),   # 7.27 年
    halved=0.5 * 1.1 ** YEARS,       # 一次永久 −50% 叠加在 30 年 +10% 上：8.72（终值 ×0.5，与发生在哪一年无关）
)
ASSUMPTIONS = '数学示意：假设固定年化收益率，不计税费、通胀与分红再投资差异；不代表任何资产的预期收益。'

if __name__ == '__main__':
    for k, v in MATH.items(): print(k, round(v, 4))
    print('coke_cagr', round(DATA['coke_cagr'] * 100, 2), '%')
    print('narration chars', sum(len(v) for v in NARRATION.values()))
