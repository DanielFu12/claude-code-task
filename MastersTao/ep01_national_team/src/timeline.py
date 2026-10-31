"""全片时间轴：音乐与画面共用（120 BPM，一小节 2 秒）。所有镜头、季度切换、重拍都对齐到小节 / 拍。

叙事线：钩子（259 → 32）→ 标题重拍 → 对决：汇金资管 vs 中国证金 19 个季度 → 今年以来（抽空 → 断崖 → 总结）
→ 科普：这两家是谁、起什么作用 → 怎么看名单 → 全景高潮 → 三条启示 → 品牌片尾
"""
import json, os

BPM = 120
BEAT = 60 / BPM          # 0.5 s
BAR = BEAT * 4           # 2.0 s
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def b(x):
    """小节号 → 秒"""
    return x * BAR


SCENES = [  # (名称, 起始小节, 结束小节)
    ("hook", 0, 5),
    ("title", 5, 7),
    ("duel", 7, 36),
    ("ytd", 36, 40),
    ("huijin", 40, 46),
    ("zhengjin", 46, 52),
    ("compare", 52, 54),
    ("rules", 54, 57),
    ("trend", 57, 68),
    ("lessons", 68, 78),
    ("end", 78, 83),
]
DURATION = b(83)          # 166 s

# 对决段每个季度的出场：(季度序号, 起始小节, 持续小节, 注释键)
QSCHED = [
    (0, 7, 2, "start"),
    (1, 9, 1, None), (2, 10, 1, None), (3, 11, 1, None), (4, 12, 1, None),
    (5, 13, 2, "cross"),
    (6, 15, 1, None), (7, 16, 1, None), (8, 17, 1, None), (9, 18, 1, None), (10, 19, 1, None),
    (11, 20, 1, None), (12, 21, 1, None), (13, 22, 1, None), (14, 23, 1, None), (15, 24, 1, None),
    # 25–27：今年以来（抽空）
    (16, 27, 2, "q1"),
    # 29：二季度前一小节，心跳蓄力
    (17, 30, 4, "collapse"),
    (18, 34, 2, "latest"),
]
YTD_BREAK = (25, 27)
PRE_DROP = (29, 30)
# 背景字幕条（起始小节, 结束小节, 标签, 文字）——不打断节奏，随季度流动
TICKER = [
    (16, 18.9, "ctx", "2023.10  汇金增持四大行，并开始买入 ETF"),
    (19, 20.9, "ctx", "2024.9.24  一揽子金融支持政策出台"),
    (22, 23.9, "ctx", "2025.4  关税冲击，汇金：发挥「类平准基金」作用"),
]

# 重拍（秒, 强度 0..1, 类型）
HITS = [
    (b(5), 1.0, "boom"), (b(7), 0.8, "boom"), (b(27), 0.85, "boom"), (b(30), 1.0, "drop"),
    (b(36), 0.8, "boom"), (b(40), 0.6, "pulse"), (b(46), 0.6, "pulse"), (b(52), 0.5, "pulse"),
    (b(57), 1.0, "boom"), (b(68), 0.6, "pulse"), (b(78), 0.9, "boom"),
]


def load_stats():
    with open(os.path.join(DATA, "stats.json"), encoding="utf-8") as f:
        return json.load(f)


def section(bar):
    for name, s, e in SCENES:
        if s <= bar < e:
            return name
    return "end"
