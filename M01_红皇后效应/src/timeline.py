"""M01《产品越来越强，为什么优势却未必变大？》—— 全片时间轴（音乐、音效、字幕共用）

100 BPM：1 拍 = 0.6 s = 18 帧（30fps），1 小节 = 2.4 s = 72 帧，所以每个拍点都正好落在整数帧上。
"""
import re

BPM = 100
BEAT = 60.0 / BPM          # 0.6 s
BAR = BEAT * 4             # 2.4 s
NBARS = 102
DUR = NBARS * BAR          # 244.8 s


def b(bar, beat=0.0):
    """小节 + 拍 → 秒"""
    return round((bar * 4 + beat) * BEAT, 4)


# ------------------------------------------------------------------ 音乐段落（小节）
#  安静段铺垫 → 上扬段展开 → 高潮段出核心观点
SECTIONS = [
    (0, 4, 'hook', '前奏 · 钩子'),          # 低频 drone + 心跳
    (4, 9, 'title', '标题'),                 # 第 1 个重拍
    (9, 25, 'ch1', '01 镜中的奔跑'),          # 安静段：铺垫
    (25, 41, 'ch2', '02 没有终点的赛跑'),     # 上扬段：鼓组进入
    (41, 57, 'drop1', '03 踮起脚尖的人群'),   # 高潮 1：核心公式 + 巴菲特
    (57, 69, 'break', '芒格的织机'),         # 抽空：sub drop 进入
    (69, 85, 'drop2', '04 三种投入'),         # 高潮 2：判断工具
    (85, 95, 'outro', '05 使用边界'),
    (95, 102, 'end', '片尾'),
]

# 重拍（画面闪光 / 冲击波 / 低频 boom 同时落下）
IMPACTS = [  # (秒, 强度)
    (b(4), 1.0), (b(41), 1.0), (b(69), 1.0), (b(98), 0.9),
]
# 次级转场
CUTS = [  # (秒, 强度, 音效类型)
    (b(9), 0.45, 'boom'), (b(25), 0.55, 'boom'), (b(57), 0.7, 'subdrop'),
    (b(85), 0.45, 'boom'), (b(95), 0.4, 'subdrop'), (b(97), 0.35, 'thud'),
    (b(44, 2), 0.3, 'thud'), (b(50), 0.4, 'boom'), (b(54), 0.3, 'thud'),
    (b(62), 0.35, 'thud'), (b(65), 0.3, 'thud'),
    (b(33, 2), 0.25, 'thud'), (b(19), 0.25, 'thud'), (b(14, 2), 0.3, 'thud'),
    (b(70, 2), 0.35, 'thud'), (b(72, 2), 0.35, 'thud'), (b(74, 2), 0.35, 'thud'),
    (b(76, 2), 0.3, 'thud'), (b(79, 2), 0.3, 'thud'),
    (b(1), 0.25, 'thud'), (b(91), 0.3, 'thud'),
]
# 重拍前的低频膨胀（结束点 = 重拍）
SWELLS = [(b(3), b(4)), (b(39), b(41)), (b(67), b(69)), (b(95), b(98))]


def section_at(t):
    for a, z, key, _ in SECTIONS:
        if b(a) <= t < b(z):
            return key
    return 'end'


# ------------------------------------------------------------------ 字幕
# {…} = 品牌金色高亮；'\n' 换行。y/size 为屏幕位置；kind: big 居中大字 / cap 下方字幕 / quote 引语
CAPS = []


def cap(t0, t1, text, y=860, size=52, kind='cap', en=None, who=None, fnt=None):
    CAPS.append(dict(t0=t0, t1=t1, text=text, y=y, size=size, kind=kind, en=en, who=who, fnt=fnt))


# ---- 钩子（0–9.6s）
cap(b(0, 0.25), b(2), '产品每年都在变强，', 400, 80, 'big')
cap(b(1), b(2), '优势却可能{一寸没涨}。', 530, 80, 'big')
cap(b(2), b(3), '为什么{越努力}，越像在{原地奔跑}？', 460, 72, 'big')
cap(b(3), b(4) - 0.15, '答案，藏在一则童话里。', 460, 64, 'big', fnt='serif_med')
# ---- 标题后：看完能得到什么（16.8–21.6）
cap(b(7), b(9) - 0.1, '看完你会带走一个判断工具：', 430, 50, 'big', fnt='sans_light')
cap(b(7, 2), b(9) - 0.1, '分清一笔投入，是在{原地奔跑}，还是在{拉开差距}。', 530, 62, 'big')
# ---- 01 镜中的奔跑（21.6–60s）
cap(b(10), b(11, 2), '在《爱丽丝镜中奇遇记》第二章，')
cap(b(11, 2), b(13), '{红皇后}拉着爱丽丝拼命奔跑。')
cap(b(13), b(14, 2), '跑了很久，周围的树却{一动没动}。')
cap(b(14, 2), b(17, 2), '「在这里，你得拼尽全力奔跑，\n才能{留在原地}。」', 470, 70, 'quote',
    en='“It takes all the running you can do, to keep in the same place.”',
    who='—— 刘易斯·卡罗尔《爱丽丝镜中奇遇记》')
cap(b(17, 2), b(19), '「想去别的地方，至少得{跑两倍快}。」', 470, 64, 'quote',
    en='“If you want to get somewhere else, you must run at least twice as fast as that!”',
    who='—— 红皇后对爱丽丝说')
cap(b(19), b(20, 2), '{1973年}，演化生物学家{范·瓦伦}借来了这个名字。',
    en='Leigh Van Valen, “A New Evolutionary Law”, Evolutionary Theory, 1973')
cap(b(20, 2), b(21, 2), '他翻查化石记录，发现：')
cap(b(21, 2), b(23), '一个类群存在得再久，{灭绝风险}也没有明显降低。')
cap(b(23), b(25) - 0.1, '他的解释：每个物种的进步，\n都在{恶化其他物种的环境}。', 860, 50)
# ---- 02 没有终点的赛跑（60–98.4s）
cap(b(26), b(27, 2), '后来的研究，常用{宿主与病原体}来理解它。')
cap(b(27, 2), b(29), '病原体演化出新{钥匙}，宿主换上新{锁}。')
cap(b(29), b(30, 2), '一代又一代，双方都在变，')
cap(b(30, 2), b(32), '却{谁也没能一劳永逸地赢}。')
cap(b(32), b(33), '回到商业，用{第一性原理}拆开看：', 520, 64, 'big')
cap(b(33), b(34, 2), '顾客从不只问：你有多好？')
cap(b(34, 2), b(36), '他们问的是：{你比别人好多少}？')
cap(b(36), b(37, 2), '你自己的提升，叫{绝对进步}；')
cap(b(37, 2), b(39), '你和对手的差距，才是{相对优势}。')
cap(b(39), b(41) - 0.3, '如果对手，跑得一样快……')
# ---- 03 踮起脚尖的人群（98.4–136.8s）
cap(b(43), b(44, 2), '进步一旦能被复制，{优势就会被抵消}。', 760, 54)
cap(b(44, 2), b(45, 2), '这不是纸上谈兵。', 520, 66, 'big')
cap(b(45, 2), b(47), '{伯克希尔}最早，是一家纺织公司。')
cap(b(47), b(48, 2), '降本设备的投资，单看{每一笔都很划算}。')
cap(b(48, 2), b(50), '但同行，也在做同样的投资。')
cap(b(50), b(54), '「单独看，每家公司的资本投资都划算又理性；\n合起来看，这些决策{互相抵消}，并不理性——\n就像看游行的人，个个以为{踮起脚尖}就能看清。」',
    300, 46, 'quote',
    en='“Viewed individually, each company\'s capital investment decision appeared cost-effective and rational; viewed collectively, the decisions neutralized each other …”',
    who='—— 沃伦·巴菲特，1985 年致股东信（中文为意译）')
cap(b(54), b(55, 1), '{1985年}，伯克希尔关闭了纺织业务。', 520, 64, 'big')
cap(b(55, 1), b(57) - 0.2, '钱，到底去了哪里？', 520, 72, 'big', fnt='serif_black')
# ---- 抽空：芒格的织机（136.8–165.6s）
cap(b(57, 1), b(58, 2), '芒格回忆：有人告诉巴菲特，')
cap(b(58, 2), b(60), '新织机的产能，能达到旧机器的{两倍}。')
cap(b(60), b(62), '巴菲特说：「但愿它不管用。\n要是管用，我就得{关掉工厂}。」', 860, 50)
cap(b(62), b(65), '「他知道，好机器带来的生产率提升，\n会{全部流向纺织品的买家}。\n作为所有者，我们{一点肉也长不上}。」',
    380, 54, 'quote',
    en='“… would all go to the benefit of the buyers of the textiles. Nothing was going to stick to our ribs as owners.”',
    who='—— 查理·芒格，1994 年南加州大学商学院演讲（意译）')
cap(b(65), b(67), '「微观经济学的一大教训，是分清技术\n什么时候帮你，{什么时候杀死你}。」', 470, 56, 'quote',
    en='“… discriminate between when technology is going to help you and when it\'s going to kill you.”',
    who='—— 查理·芒格，1994 年')
cap(b(67), b(69) - 0.3, '那么，投入还有意义吗？', 520, 72, 'big', fnt='serif_black')
# ---- 04 三种投入（165.6–204s）
cap(b(69), b(70, 2), '有。关键是看清：{每一笔钱，买到了什么}。', 860, 52)
cap(b(70, 2), b(72, 2), '{保住资格}：别人都有，你不能没有。\n回报是不掉队，不是领先。', 860, 46)
cap(b(72, 2), b(74, 2), '{改善用户价值}：用户真的受益；\n但对手若很快跟上，好处多半归用户。', 860, 46)
cap(b(74, 2), b(76, 2), '{积累可持续能力}：越投越厚，对手难以复制，\n差距才可能拉大。', 860, 46)
cap(b(76, 2), b(79, 2), '「投资的关键……是判断一家公司的竞争优势，\n尤其是这种{优势的持久性}。」', 860, 50, 'quote',
    en='“… determining the competitive advantage of any given company and, above all, the durability of that advantage.”',
    who='—— 沃伦·巴菲特，1999 年《财富》杂志')
cap(b(79, 2), b(81), '放到身边看：手机的{影像、快充、高刷屏}……')
cap(b(81), b(82, 2), '一项配置，从「卖点」变成「标配」，')
cap(b(82, 2), b(85) - 0.1, '投入就从{拉开差距}，变成了{保住资格}。')
# ---- 05 使用边界（204–228s）
cap(b(85), b(86), '这个模型，也有{边界}：', 230, 56, 'big')
# （四条边界由画面清单逐条呈现，见 video.py LIMITS；此处只做阅读时长校验）
cap(b(86), b(87, 2), '市场还在快速扩张时，大家可能一起变好；', kind='list')
cap(b(87, 2), b(89), '有专利、网络效应护着的进步，未必被抵消；', kind='list')
cap(b(89), b(90, 2), '变化也来自技术、需求和制度，不只来自对手；', kind='list')
cap(b(90, 2), b(92), '红皇后是{假说}，不是「必须永远内卷」的定律。', kind='list')
cap(b(92), b(95) - 0.1, '下次做预算，先问自己一句：', 420, 48, 'big', fnt='sans_light')
cap(b(92, 2), b(95) - 0.1, '这笔投入，是在{原地奔跑}，\n还是在{拉开差距}？', 560, 72, 'big', fnt='serif_black')


def plain(s):
    return re.sub(r'[{}\n]', '', s)


def reading_chars(s):
    """计入阅读时长的字数：汉字/字母数字，标点不计"""
    return len(re.findall(r'[一-鿿A-Za-z0-9]', plain(s)))


def check(verbose=True):
    bad = []
    for c in CAPS:
        n = reading_chars(c['text'])
        # 同屏叠加的字幕：从出现到消失的时长
        cps = n / (c['t1'] - c['t0'])
        if cps > 6.0:
            bad.append((c['t0'], c['text'], round(cps, 2)))
        if verbose:
            print(f"{c['t0']:7.2f}-{c['t1']:7.2f}  {n:3d}字  {cps:4.1f}字/秒  {plain(c['text'])}")
    return bad


if __name__ == '__main__':
    bad = check()
    print('DUR', DUR, 'too fast:', bad)
