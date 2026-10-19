"""第三版（6–7 分钟）的完整叙事：原始影像 + Gemini TTS 解说 + 复利动画 + 品牌片尾。

STORY 按播放顺序排列，每一项是：
  ('vo', 段落id, [(句子id, 字幕文本), ...])      解说（同一段落一次合成，保证语气连贯）
  ('clip', 片段id)                                  原始影像（clips.py）
  ('title', None) / ('anim', 段落id) / ('summary', None) / ('brand', None)
SAY 是只为发音调整的朗读文本（字幕仍用原文）；TAGS 是加在句首的停顿/呼吸标签。
所有事实的出处见 SOURCES.md。
"""

# ------------------------------------------------------------------ 配音（只用 Gemini TTS gemini-3.8-flash-tts）
TTS_MODEL = 'gemini-3.8-flash-tts'
VOICE = 'orus'
STYLE = ('A seasoned Mandarin documentary narrator telling a true story to a friend: natural, warm and conversational, '
         'with real breathing and subtle emotion; moderately brisk, steady pace; no broadcaster tone, no sing-song endings, '
         'no exaggerated pauses.')
TEMPO = 1.04          # rubberband 轻微提速（保留音高与共振峰）
# 动画段配乐逐渐推向高潮，解说也要随之更有力量（仍保持自然，不播音腔）
STYLE_BY_GROUP = {
    'G10': STYLE + ' Build energy: more emphatic and engaged, as if revealing something important.',
    'G11': STYLE + ' Rising intensity and conviction; land the key numbers firmly, with weight on 一个零 and 全部蒸发.',
    'G12': STYLE + ' Firm, passionate conviction, like stating a hard-won rule.',
    'G13': STYLE + ' Warm and stirring, building toward a climax; emphasize 不是慢，而是中断.',
    'G14': ('A seasoned Mandarin documentary narrator delivering the final line at the emotional climax: slow, powerful, '
            'deeply felt and resonant, with a clear pause after each phrase; natural human voice, not broadcaster tone.'),
}

STORY = [
    ('clip', 'LB'),                                   # 冷开场：李录原声（AI 与“学到的明天就没用了”）
    ('vo', 'G1', [
        ('S01', '说这番话的，是喜马拉雅资本创始人李录。'),
        ('S02', '2026 年 10 月，在哥伦比亚商学院第 36 届格雷厄姆与多德年度活动上，他谈到这一轮 AI 浪潮：变化的速度、涉及的规模，都前所未有。'),
        ('S03', '他担心的，是一种零和、短期的活法——学到的东西不断作废，什么也积累不下来。'),
        ('S04', '那么，在一个越来越快的时代，什么才值得我们花几十年去积累？'),
    ]),
    ('title', None),                                  # 片名「AI 越快，越要慢」：落在配乐第一个大鼓上
    ('vo', 'G2', [
        ('S05', '李录给出的答案，是复利。但他说的复利，和很多人想的不太一样。'),
    ]),
    ('clip', 'LC'),
    ('vo', 'G3', [
        ('S06', '那么，复利最关键的是什么？他的回答，朴素得出人意料。'),
    ]),
    ('clip', 'LD'),
    ('vo', 'G4', [
        ('S07', '复利，首先不是更快，而是不失去。'),
        ('S08', '知识、信任、智慧、健康，一旦积累起来，就会一年一年地叠加；可一旦失去，往往要从头再来。'),
        ('S09', '而这套人生观，李录说，来自一个人。'),
    ]),
    ('clip', 'LT'),
    ('vo', 'G5', [
        ('S10', '查理·芒格，和他的搭档沃伦·巴菲特，用了半个多世纪，在伯克希尔的股东大会上反复讲同一件事。'),
        ('S11', '1999 年，一位股东问巴菲特：如果你三十出头、从头再来，会怎么做？'),
    ]),
    ('clip', 'BB'),
    ('vo', 'G6', [
        ('S12', '坡要够长，雪球还不能半路散掉。'),
        ('S13', '就在前一年，一家由华尔街顶尖聪明人管理、还有两位诺贝尔经济学奖得主坐镇的对冲基金——长期资本管理公司，靠高杠杆，在短短几个月里几乎赔光了全部资本。'),
        ('S14', '巴菲特这样评价：'),
    ]),
    ('clip', 'BA'),
    ('vo', 'G7', [
        ('S15', '那么，市场下跌，算不算失去？'),
        ('S16', '伯克希尔自己的股价，就曾经四次大跌，最深的一次跌去 59%。芒格的看法是：'),
    ]),
    ('clip', 'MB'),
    ('vo', 'G8', [
        ('S17', '价格的下跌是暂时的；真正的损失，是企业的价值被毁掉，或者在低点被迫卖出。'),
        ('S18', '只要价值还在、不被迫卖出，复利就没有中断。'),
        ('S19', '而在芒格看来，最重要的复利，发生在一个人自己身上。'),
    ]),
    ('clip', 'MU'),
    ('vo', 'G9', [
        ('S20', '还有信任——正是李录念念不忘的那句话。'),
    ]),
    ('clip', 'MT'),
    # ---------------------------------------------------------------- 动画：复利的第一性原理（约 1 分 35 秒）
    ('anim', 'G10', [
        ('A01', '复利，本质上是乘法：每一年的结果，都乘在上一年之上。'),
        ('A02', '每年多 10%，三十年后是 17.4 倍；每年少 10%，只剩不到 5%。'),
        ('A03', '起点一样，终点相差四百多倍。'),
    ]),
    ('anim', 'G11', [
        ('A04', '可乘法也有残酷的一面：亏掉一半，要翻一倍才能回来——按每年 10% 算，要七年多。'),
        ('A05', '如果乘上的是一个零呢？'),
        ('A06', '巴菲特在 2010 年的致股东信里写道：一长串正数，不管多么亮眼，只要乘以一个零，就会全部蒸发。'),
    ]),
    ('anim', 'G12', [
        ('A07', '所以他引用赛车界的一条原则：要想第一个冲过终点，首先得冲过终点。'),
        ('A08', '暂时的下跌可以等待；永久的损失，才会改写结局。'),
    ]),
    ('anim', 'G13', [
        ('A09', '这个道理，不只适用于钱。'),
        ('A10', '知识、信任、技能、健康，都在复利。它们共同的敌人，不是慢，而是中断。'),
    ]),
    ('summary', 'G14', [
        ('A11', 'AI 越快，越要慢。复利的秘密，不是更快，而是不失去。'),
    ]),
    ('brand', None),
]

SAY = {
    'S02': '二零二六年十月，在哥伦比亚商学院第三十六届格雷厄母与多德年度活动上，他谈到这一轮 AI 浪潮：变化的速度、涉及的规模，都前所未有。',
    'S11': '一九九九年，一位股东问巴菲特：如果你三十出头、从头再来，会怎么做？',
    'S16': '伯克希尔自己的股价，就曾经四次大跌，最深的一次跌去百分之五十九。芒格的看法是：',
    'A02': '每年多百分之十，三十年后是十七点四倍；每年少百分之十，只剩不到百分之五。',
    'A04': '可乘法也有残酷的一面：亏掉一半，要翻一倍才能回来——按每年百分之十算，要七年多。',
    'A06': '巴菲特在二零一零年的致股东信里写道：一长串正数，不管多么亮眼，只要乘以一个零，就会全部蒸发。',
}
TAGS = {'S03': '<breath>', 'S04': '<short pause>', 'S08': '<breath>', 'S09': '<short pause>', 'S11': '<breath>',
        'S13': '<breath>', 'S16': '<breath>', 'S18': '<short pause>', 'S19': '<breath>', 'A03': '<short pause>',
        'A05': '<breath>', 'A06': '<short pause>', 'A08': '<breath>', 'A10': '<breath>'}

TITLE = 'AI 越快，越要慢'
SUBTITLE = '复利的秘密，不是更快，而是不失去'
SLOGAN = '关注「巴芒价值」，传承大师智慧，领悟投资真谛'


def vo_groups():
    return [it for it in STORY if it[0] in ('vo', 'anim', 'summary')]


def sentences():
    return [(sid, txt) for it in vo_groups() for sid, txt in it[2]]
