"""汇金退出榜：时间轴（与配乐共用，136 BPM，一小节 ≈ 1.765 秒）。

叙事线：钩子（今年二季度一次退出 122 家）→ 标题 → 19 个季度逐季：家数变化 + 当季退出榜（按持股市值前 10）
→ 2026Q2 倒数揭晓（踩重拍）→ 总结 → 品牌片尾
"""
import json, os

BPM = 136                # 与原创配乐（Lyria 生成，实测 135.99 BPM）一致
BEAT = 60 / BPM
BAR = BEAT * 4
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def b(x):
    return x * BAR


def load():
    with open(os.path.join(DATA, "hjam.json"), encoding="utf-8") as f:
        return json.load(f)


S = load()
QL = S["quarters"]
BIG = QL.index("2026Q2")

# 每季时长：起点 2 小节；有退出 2 小节；无退出 1 小节；2026Q2 倒数揭晓 6 小节；最后一季 2 小节
QSCHED = []
bar = 6
for i, st in enumerate(S["steps"]):
    if i == 0: d = 2
    elif i == BIG: d = 6
    elif i == len(QL) - 1: d = 2
    elif st["n_exit"] == 0: d = 1
    else: d = 2
    QSCHED.append((i, bar, d))
    bar += d
MAIN_END = bar                       # 46
PRE_DROP = QSCHED[BIG][1] - 1        # 2026Q2 前一小节：压暗蓄力

SCENES = [("hook", 0, 4), ("title", 4, 6), ("main", 6, MAIN_END), ("summary", MAIN_END, MAIN_END + 4),
          ("end", MAIN_END + 4, MAIN_END + 7)]
DURATION = b(MAIN_END + 7)

HITS = [(b(4), 1.0, "boom"), (b(6), 0.8, "boom"), (b(QSCHED[BIG][1]), 1.0, "drop"),
        (b(QSCHED[BIG][1] + 2.5), 0.9, "boom"),            # 第 1 名（贵州茅台）落地
        (b(MAIN_END), 1.0, "boom"), (b(MAIN_END + 4), 0.9, "boom")]


def section(bar_):
    for name, s, e in SCENES:
        if s <= bar_ < e:
            return name
    return "end"
