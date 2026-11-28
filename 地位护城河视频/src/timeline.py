"""共享时间轴：音乐（music.py）与画面（video.py）都从这里取节拍和段落。

120 BPM，一拍 0.5 秒，一小节 2 秒。所有段落边界都落在小节线上。
"""
BPM = 120
BEAT = 60.0 / BPM
BAR = 4 * BEAT
DUR = 376.0

# (起点秒, 终点秒, 音乐风格, 和声进行)
PROG = {
    'A': ['Dm', 'Bb', 'F', 'C'],
    'B': ['Bb', 'F', 'C', 'Dm'],
    'C': ['Gm', 'Bb', 'Dm', 'C'],
    'D': ['Dm', 'Dm', 'Bb', 'A'],
    'E': ['Bb', 'F', 'C', 'Dm'],
    'Z': ['Bb', 'F', 'Gm', 'D'],
}
SEGMENTS = [
    (0, 12, 'intro', 'A'),
    (12, 16, 'rise', 'A'),
    (16, 24, 'full', 'A'),        # 标题
    (24, 38, 'grooveA', 'A'),     # 01 三个问题
    (38, 64, 'grooveA2', 'B'),    # 群居 / 昂贵信号
    (64, 78, 'grooveA3', 'A'),    # 价格拆解
    (78, 94, 'build', 'C'),       # 02 三股力量
    (94, 110, 'full', 'A'),       # 乘法公式
    (110, 122, 'half', 'B'),      # 不是凡勃伦
    (122, 140, 'grooveB', 'C'),   # 03 奢侈 vs 大众
    (140, 160, 'grooveB2', 'A'),  # 毛利率 / Costco
    (160, 178, 'full', 'A'),      # 04 苹果
    (178, 190, 'tension', 'D'),   # 山姆
    (190, 198, 'alarm', 'D'),     # 巧克力派争议
    (198, 216, 'grooveA', 'B'),   # 品牌筛选散点图
    (216, 224, 'break', 'B'),     # 05 悖论
    (224, 236, 'build', 'C'),     # 倒 U 曲线
    (236, 252, 'full', 'A'),      # 两股力量
    (252, 270, 'grooveB', 'C'),   # 06 五个条件
    (270, 290, 'full', 'A'),      # 经济利润
    (290, 306, 'break2', 'B'),    # 07 隐形测试
    (306, 312, 'rise', 'B'),
    (312, 344, 'fullplus', 'A'),  # 08 三角张力 / 最高境界
    (344, 364, 'epi', 'E'),       # 终章：五条教训
    (364, 376, 'outro', 'Z'),     # 片尾
]
# 重拍：时间、强度、颜色名（画面用）
IMPACTS = [(16, 1.0, 'gold'), (94, 0.8, 'cyan'), (122, 0.4, 'violet'), (160, 0.9, 'white'), (190, 0.7, 'red'),
           (236, 0.8, 'magenta'), (270, 0.5, 'gold'), (312, 1.0, 'gold')]
RISERS = [(12, 16), (90, 94), (156, 160), (232, 236), (306, 312)]
DROPOUTS = [(15.5, 16), (93.5, 94), (159.5, 160), (235.5, 236), (311.5, 312)]

CHAPTERS = [(0, '序', '序章', 'PROLOGUE'), (16, '00', '题解', 'THE MOAT'),
            (24, '01', '第一性原理', 'FIRST PRINCIPLES'), (78, '02', '三股力量', 'THREE FORCES'),
            (122, '03', '奢侈品 vs 大众品牌', 'LUXURY VS MASSTIGE'), (160, '04', '案例', 'CASES'),
            (216, '05', '普及悖论', 'THE PARADOX'), (252, '06', '投资框架', 'THE FRAMEWORK'),
            (290, '07', '隐形测试', 'THE INVISIBLE TEST'), (312, '08', '终极命题', 'THE TRIANGLE'),
            (344, '终', '五条教训', 'LESSONS'), (DUR, '', '', '')]


def segment_at(t):
    for s in SEGMENTS:
        if s[0] <= t < s[1]:
            return s
    return SEGMENTS[-1]


ENERGY_OF = {'intro': .25, 'rise': .35, 'full': 1.0, 'fullplus': 1.0, 'grooveA': .6, 'grooveA2': .65, 'grooveA3': .7,
             'build': .7, 'half': .5, 'grooveB': .7, 'grooveB2': .75, 'tension': .6, 'alarm': .8, 'break': .2,
             'break2': .15, 'epi': .55, 'outro': .25}
