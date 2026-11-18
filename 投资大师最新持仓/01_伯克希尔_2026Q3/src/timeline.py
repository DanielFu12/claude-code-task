"""全片时间轴：原创配乐 120 BPM（1 拍 = 0.5 s，1 小节 = 4 拍 = 2 s），所有镜头、动画、音效都落在拍点上。

配乐由 music.py 按同一套拍号逐音符合成，所以画面与音乐是「同一张谱」——天然卡点。

  小节   时间       音乐段落                     镜头
  0–3    0–8 s     前奏：滤波琶音逐渐打开、闷鼓   S1 冷开场：总市值计数
  4–5    8–12 s    鼓组进入                      S2 30 只持仓「星群」
  6–7    12–16 s   停顿式重音（每半小节一击）     S3 新进 / 增持 / 减持 / 清仓 四个数字
  8      16–18 s   军鼓滚奏 + 上行蓄力           S3 坍缩
  9      18 s      第一次 DROP                   S4 片名
  9–24   18–50 s   主段（满编）                  S5 前十大 → S6 集中度 → S7 谷歌 → S8 新进 / 增持
  25–29  50–60 s   半速段（暗色和声）             S9 减持 → 美国银行
  30–31  60–64 s   抽空：心跳 + 蓄力             S10 清仓 = 0
  32     64 s      第二次 DROP                   S11 三个信号
  42–43  84–88 s   尾段                          S12 总结
  44     88 s      终止重击 + 余韵                片尾
"""
import numpy as np

BPM = 120.0
SPB = 60.0 / BPM          # 0.5 s / 拍
DUR = 94.0
BEATS = np.arange(0, DUR / SPB + 1) * SPB


def b(i):
    """第 i 拍的时间（秒），可为小数拍。"""
    return float(i) * SPB


T_S2, T_S3, T_DROP1 = b(16), b(24), b(36)
T_S5, T_S6, T_S7, T_S8 = b(44), b(60), b(68), b(84)
T_ADD = b(92)
T_S9, T_BAC, T_S10, T_DROP2 = b(100), b(112), b(120), b(128)
T_SIG1, T_SIG2, T_SIG3 = b(132), b(144), b(156)
T_OUTRO, T_END = b(168), b(176)

IMPACTS = [(T_DROP1, 1.0), (T_DROP2, 1.0), (T_S10, 0.55), (T_END, 0.7)]
RISERS = [(b(32), T_DROP1), (b(124), T_DROP2)]
# 普通转场：画面光扫 + 音乐里的重音（tom + 低频冲击 + 镲片涌起）
CUTS = [T_S2, T_S3, T_S5, T_S6, T_S7, T_S8, T_ADD, T_S9, T_BAC, T_SIG1, T_SIG2, T_SIG3, T_OUTRO]
# 四个数字逐一弹出的重音
TILE_HITS = [b(24), b(26), b(28), b(30)]

if __name__ == '__main__':
    for k, v in list(globals().items()):
        if k.startswith('T_'):
            print(f'{k:10s} {v:6.2f}s  bar {v / 2:5.2f}')
