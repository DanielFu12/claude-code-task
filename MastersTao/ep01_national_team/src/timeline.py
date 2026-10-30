"""全片时间轴：音乐与画面共用（96 BPM，一小节 2.5 秒）。所有镜头、季度切换、重拍都对齐到小节 / 拍。"""
import json, os

BPM = 96
BEAT = 60 / BPM          # 0.625 s
BAR = BEAT * 4           # 2.5 s
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def b(x):
    """小节号 → 秒"""
    return x * BAR


SCENES = [  # (名称, 起始小节, 结束小节)
    ("open", 0, 5),
    ("title", 5, 8),
    ("huijin", 8, 12),
    ("zhengjin", 12, 16),
    ("rules", 16, 18),
    ("tunnel", 18, 50),
    ("trend", 50, 60),
    ("lessons", 60, 67),
    ("end", 67, 71),
]
DURATION = b(71)          # 177.5 s

# 时间隧道里每个季度的出场：(季度序号, 起始小节, 持续小节, 注释键)
QSCHED = [
    (0, 18, 2, "start"),
    (1, 20, 1, None), (2, 21, 1, None), (3, 22, 1, None), (4, 23, 1, None),
    (5, 24, 1, "zj2023q2"), (6, 25, 1, None),
    (7, 26, 2, "ctx2023"),
    (8, 28, 1, None), (9, 29, 1, None),
    (10, 30, 2, "ctx924"),
    (11, 32, 1, None), (12, 33, 1, None),
    (13, 34, 2, "ctx2025"),
    (14, 36, 3, "turn2025q3"),
    (15, 39, 1, None),
    (16, 40, 2, "turn2026q1"),
    # 42–44：抽空蓄力
    (17, 44, 4, "collapse"),
    (18, 48, 2, "latest"),
]
BREAK = (42, 44)

# 重拍（秒, 强度 0..1, 类型）
HITS = [
    (b(5), 1.0, "boom"), (b(8), 0.55, "pulse"), (b(12), 0.55, "pulse"), (b(16), 0.5, "pulse"),
    (b(18), 0.9, "boom"), (b(36), 0.8, "boom"), (b(40), 0.6, "pulse"),
    (b(44), 1.0, "drop"), (b(50), 1.0, "boom"), (b(60), 0.55, "pulse"), (b(67), 0.85, "boom"),
]


def qstart(i):
    for k, s, d, _ in QSCHED:
        if k == i:
            return b(s)


def load_stats():
    with open(os.path.join(DATA, "stats.json"), encoding="utf-8") as f:
        return json.load(f)


def cues():
    """给音频用的事件表"""
    ticks = [b(s) for k, s, d, _ in QSCHED if b(s) not in [h[0] for h in HITS]]
    return {"bpm": BPM, "bar": BAR, "duration": DURATION, "scenes": SCENES, "hits": HITS,
            "ticks": ticks, "break": BREAK, "qsched": QSCHED}
