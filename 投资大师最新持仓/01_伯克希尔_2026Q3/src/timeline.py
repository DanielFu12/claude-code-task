"""音乐结构与全片时间轴（所有镜头都对齐到节拍网格）

背景音乐取自仓库根目录 `opus5.5涌现.mp4`（约 112 BPM，2:05）。
剪辑：源曲第 0–96 拍原样保留，第 96 拍直接接到第 144 拍（两处都是 16 拍乐句的起点），
跳过 48 拍（≈25.5 s）。这样就有：前奏 → 第一次重拍（18.2 s）→ 主律动 → 渐弱段 → 抽空 → 第二次重拍 → 尾声。
"""
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_BEATS = np.load(os.path.join(HERE, 'beats_src.npy'))
CUT_A, CUT_B = 96, 144                     # 源曲拍号：从 A 跳到 B
SHIFT = SRC_BEATS[CUT_B] - SRC_BEATS[CUT_A]   # ≈25.50 s
# 输出时间轴上的节拍（拍号 = 输出拍号）
BEATS = np.concatenate([SRC_BEATS[:CUT_A], SRC_BEATS[CUT_B:] - SHIFT])
DUR = 98.0                                 # 成片时长（秒）


def b(i):
    """输出第 i 拍的时间（秒）。"""
    return float(BEATS[i])


# ---------------------------------------------------------------- 镜头（输出拍号）
#  拍号      音乐                    镜头
#  0–12     前奏                     S1 冷开场：总市值计数 3042 亿美元
#  12–20    前奏                     S2 27 家公司的「星群」
#  20–32    鼓点抽空 + 蓄力           S3 本季四个数字：新进/增持/减持/清仓 → 坍缩
#  32       第一次重拍                S4 片名
#  40–56    主律动                   S5 前十大重仓环形图
#  56–64    主律动                   S6 集中度：前五大 71.6%
#  64–80    主律动                   S7 Alphabet：一年股数 ×5.9
#  80–96    主律动                   S8 新进 + 增持
#  96–116   渐弱段（剪辑点）          S9 减持
#  116–124  鼓点抽空                 S10 清仓 = 0
#  124      第二次重拍                S11 三个最值得关注的信号
#  164–     尾声                     S12 总结 + 片尾
T_S2, T_S3, T_DROP1 = b(12), b(20), b(32)
T_S5, T_S6, T_S7, T_S8 = b(40), b(56), b(64), b(80)
T_S9, T_S10, T_DROP2 = b(96), b(116), b(124)
T_SIG1, T_SIG2, T_SIG3 = b(128), b(140), b(152)
T_OUTRO, T_END = b(164), b(172)

IMPACTS = [(T_DROP1, 1.0), (T_DROP2, 1.0), (T_S10, 0.55), (T_END, 0.6)]
RISERS = [(b(28), T_DROP1), (b(120), T_DROP2)]
# 普通转场（低沉 whoosh + 闷响）
CUTS = [T_S2, T_S3, b(40), T_S6, T_S7, T_S8, T_S9, T_SIG2, T_SIG3, T_OUTRO]

if __name__ == '__main__':
    print('shift', SHIFT)
    for k, v in list(globals().items()):
        if k.startswith('T_'):
            print(f'{k:10s} {v:7.2f}')
