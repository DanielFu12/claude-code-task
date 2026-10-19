"""原始影像片段：来源、出入点、裁切与中英字幕。

所有时间都是「源文件时间」（秒）。字幕起止来自本地 Whisper 词级时间戳（tools/wts.py），
英文为原话转写，中文为本片翻译（直译，不改变原意）。
源文件放在 footage/src/（不入库），获取方式见 tools/fetch_footage.sh；
prep_clips.py 会把每个片段处理成 footage/clips/<id>.mp4 + .wav。
"""
import json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
TRACK = os.path.join(ROOT, 'assets', 'track')

LILU = dict(who='李录', role='喜马拉雅资本创始人',
            event='哥伦比亚商学院 · 第 36 届格雷厄姆与多德年度活动 · 2026.10.05',
            credit='录像：Columbia Business School 官方录像（经 B 站转载版本截取，转载水印在画面外）')
MUNGER_BBC = dict(who='查理·芒格', role='伯克希尔·哈撒韦副董事长（1924–2023）',
                  event='BBC 专访 · 2009.10', credit='录像：BBC（经转载版本截取）')
MUNGER_USC = dict(who='查理·芒格', role='伯克希尔·哈撒韦副董事长（1924–2023）',
                  event='南加州大学法学院毕业典礼演讲 · 2007.05.13', credit='录像：USC Gould School of Law')
BRK1999 = dict(who='沃伦·巴菲特', role='伯克希尔·哈撒韦董事长',
               event='伯克希尔·哈撒韦 1999 年股东大会 · 奥马哈', credit='录像：伯克希尔·哈撒韦股东大会（经 B 站转载版本截取）')
BUFFETT_UF = dict(who='沃伦·巴菲特', role='伯克希尔·哈撒韦董事长',
                  event='佛罗里达大学商学院演讲 · 1998.10.15', credit='录像：University of Florida（经 B 站转载版本截取，原字幕已去除）')

# 官方录像为 1440×1080，16:9 画面上下有黑边，转载水印在上方黑边里：只取中间的 16:9 画面
LILU_BOX = (0, 135, 1440, 810)


def parts(c):
    return c.get('parts') or [(c['a'], c['b'])]


def length(c):
    return sum(b - a for a, b in parts(c))


def src_time(c, u):
    """片段内时间 u → 源文件时间（拼接片段逐段映射）"""
    for a, b in parts(c):
        if u <= b - a: return a + u
        u -= b - a
    a, b = parts(c)[-1]
    return b


def track(name):
    p = os.path.join(TRACK, name)
    return json.load(open(p)) if os.path.exists(p) else None


CLIPS = {
    # ---------------------------------------------------------------- 李录（官方多机位录像，时间即 YouTube 原片时间；合计 < 60 秒）
    'LB': dict(src='lilu_official_4970.mp4', off=4970.0, a=5064.85, b=5080.55, info=LILU, crop=LILU_BOX,
               context='语境：李录在谈「零和、短期」的人性倾向',
               cues=[(5065.02, 5067.30, 'Whatever you learn today is useless tomorrow.', '今天学到的，明天就没用了。'),
                     (5068.38, 5069.90, "You don't accumulate.", '你积累不下来。'),
                     (5070.66, 5073.85, 'And so you rely more and more on the impersonal.', '于是，你越来越依赖外物。'),
                     (5073.90, 5076.60, 'You get a bigger computer, and now you use AI.', '你买更大的电脑，现在又用上了 AI。'),
                     (5077.52, 5080.45, "And of course, you'll be replaced at some point.", '当然，到某个时候，你就会被取代。')]),
    'LC': dict(src='lilu_official_4970.mp4', off=4970.0, a=4983.65, b=4992.95, info=LILU, crop=LILU_BOX,
               cues=[(4983.80, 4989.50, 'And I always say, look, if you can compound your knowledge in a sustainable fashion,',
                      '我常说：如果你能以可持续的方式，让知识复利增长，'),
                     (4989.62, 4992.85, 'eventually you can compound your capital as well.', '最终，你的资本也能复利增长。')]),
    'LD': dict(src='lilu_official_4970.mp4', off=4970.0, a=5209.65, b=5230.35, info=LILU, crop=LILU_BOX,
               cues=[(5209.78, 5214.95, "And the basic idea of compounding is you don't lose what you already have,",
                      '复利的基本理念，是不要失去你已经拥有的。'),
                     (5215.30, 5217.35, "and that's a profound idea.", '这是一个深刻的道理。'),
                     (5218.68, 5220.55, "You don't lose what you already have.", '不要失去你已经拥有的——'),
                     (5220.92, 5222.70, "That's including your knowledge,", '包括你的知识，'),
                     (5223.46, 5226.00, "that's including your trusting relationship,", '包括你基于信任的关系，'),
                     (5226.78, 5230.25, "that's including the wisdom and even your health.", '包括你的智慧，甚至你的健康。')]),
    # 两段拼接：中间省略约 6 秒（一段停顿和半句 "always advocate is the relationship"），画面用短叠化过渡，字幕用省略号标出
    'LT': dict(src='lilu_official_4970.mp4', off=4970.0, parts=[(5104.45, 5109.25), (5115.45, 5122.30)], info=LILU, crop=LILU_BOX,
               cues=[(5104.58, 5109.20, 'And what my mentor, partner, teacher Charlie Munger always said…',
                      '我的导师、合伙人、老师查理·芒格常说……'),
                     (5115.62, 5122.25, 'the highest order of relationship he could discover is a seamless web of deserved trust.',
                      '他所能发现的最高级的关系，是一张无缝的、彼此值得信任的网。')]),
    # ---------------------------------------------------------------- 芒格 · BBC 2009
    'MB': dict(src='munger_bbc2009.mp4', a=29.45, b=47.00, info=MUNGER_BBC, crop=(0, 238, 505, 394),
               cues=[(29.60, 34.86, "In fact, you can argue that if you're not willing to react with equanimity",
                      '甚至可以说，如果你不能心平气和地面对'),
                     (34.86, 41.80, 'to a market price decline of 50% two or three times a century,',
                      '每个世纪两三次、市价下跌 50% 的情况，'),
                     (42.04, 46.90, "you're not fit to be a common shareholder, and you deserve the mediocre result you're going to get",
                      '你就不适合做普通股股东，你也只配得到平庸的结果。')]),
    # ---------------------------------------------------------------- 芒格 · USC 2007
    'MU': dict(src='munger_usc2007.mp4', a=390.85, b=415.35, info=MUNGER_USC, crop=(90, 20, 820, 640),
               cues=[(391.00, 394.20, 'I constantly see people rise in life', '我不断看到一些人在人生中崛起，'),
                     (394.20, 402.02, 'who were not the smartest, sometimes not even the most diligent, but they are learning machines.',
                      '他们不是最聪明的，有时甚至不是最勤奋的，但他们是「学习机器」。'),
                     (402.78, 407.22, 'They go to bed every night a little wiser than they were when they got up.',
                      '他们每晚睡觉时，都比早上起床时更聪明一点。'),
                     (408.00, 415.18, 'And boy, does that habit help, particularly when you have a long run ahead of you.',
                      '这个习惯太有用了——尤其当你前面还有很长的路要走。')]),
    'MT': dict(src='munger_usc2007.mp4', a=2149.20, b=2156.10, info=MUNGER_USC, crop=(90, 20, 820, 640),
               cues=[(2149.34, 2152.32, 'The highest form that civilization can reach', '文明所能达到的最高形态，'),
                     (2153.44, 2155.95, 'is a seamless web of deserved trust.', '是一张无缝的、彼此值得信任的网。')]),
    # ---------------------------------------------------------------- 巴菲特 · 1999 年股东大会（时间为整场录像时间；off = 片段文件的起点）
    'BA': dict(src='brk1999_a.mp4', off=1429.94, a=1440.05, b=1457.75, info=BRK1999, crop=(240, 135, 560, 368),
               cues=[(1440.22, 1441.32, 'You only have to get rich once.', '你只需要富一次。'),
                     (1441.74, 1445.16, 'And why do people, very bright people,', '为什么有些人——非常聪明的人——'),
                     (1446.16, 1450.66, "risk losing something that's very important to them to gain something that's totally unimportant?",
                      '会拿对自己非常重要的东西去冒险，只为得到完全不重要的东西？'),
                     (1450.94, 1453.36, 'The added money has no utility whatsoever.', '多赚的钱，毫无用处；'),
                     (1454.50, 1457.54, 'And the money that was lost had enormous utility.', '而亏掉的钱，却极其重要。')]),
    # 成片使用的是这 11.1 秒（第三版曾把出入点改到 13621.85，但片段文件没有重新生成，导致字幕与声音错位、后面冻结约 18 秒）
    'BB': dict(src='brk1999_b.mp4', off=13614.85, a=13639.55, b=13650.65, info=BRK1999, crop=(195, 115, 780, 400),
               cues=[(13639.80, 13643.30, 'The nature of compound interest is it behaves like a snowball of sticky snow,',
                      '复利的本质，就像滚一颗黏雪的雪球——'),
                     (13644.30, 13650.50, 'and the trick is to have a very long hill, which means either starting very young or living very, to be very old.',
                      '关键是要有一道很长的坡，要么很年轻就开始，要么活得很老。')]),
}
