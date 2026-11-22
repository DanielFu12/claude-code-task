"""全片时间轴：原创配乐 120 BPM（1 拍 = 0.5 s，1 小节 = 4 拍 = 2 s），所有镜头、动画、音效都落在拍点上。

配乐由 music.py 按同一套拍号逐音符合成，所以画面与音乐是「同一张谱」——天然卡点。

  小节    时间          音乐段落                      镜头
  0–4     0–10 s       前奏：滤波琶音逐渐打开、闷鼓    S1 冷开场：资产规模计数
  5–8     10–18 s      鼓组进入                       S2 35 只持仓「星群」
  9–10    18–22 s      停顿式重音                     S3 新进 / 增持 / 减持 三个数字
  11      22–24 s      军鼓滚奏 + 上行蓄力            S3 坍缩
  12      24 s         第一次 DROP                    S4 片名
  12–29   24–60 s      主段（满编）                   S5 前十大 → S6 集中度 → S7 谷歌
  30–35   60–72 s      轻编段（去掉拍手与开镲）        S8 新进：Bending Spoons 是做什么的
  36–39   72–80 s      主段                           S8b 增持
  40–48   80–98 s      半速段（暗色和声）              S9 减持 → 美国银行
  49–52   98–106 s     抽空：心跳 + 滴答 + 蓄力        S10 现金储备 3,523 亿美元
  53      106 s        第二次 DROP                    S11 三个信号
  70–72   140–146 s    尾段                           S12 总结
  73      146 s        终止重击 + 余韵                 片尾
"""
import numpy as np

BPM = 120.0
SPB = 60.0 / BPM          # 0.5 s / 拍
DUR = 154.0
BEATS = np.arange(0, DUR / SPB + 1) * SPB


def b(i):
    """第 i 拍的时间（秒），可为小数拍。"""
    return float(i) * SPB


T_S2, T_S3, T_DROP1 = b(20), b(36), b(48)
T_S5, T_S6, T_S7, T_S8 = b(56), b(84), b(100), b(120)
T_ADD = b(144)
T_S9, T_BAC, T_S10, T_DROP2 = b(160), b(180), b(196), b(212)
T_SIG1, T_SIG2, T_SIG3 = b(220), b(240), b(260)
T_OUTRO, T_END = b(280), b(292)

IMPACTS = [(T_DROP1, 1.0), (T_DROP2, 1.0), (T_END, 0.7)]
RISERS = [(b(206), T_DROP2), (b(44), T_DROP1)]
# 普通转场：画面光扫 + 音乐里的重音（tom + 低频冲击 + 镲片涌起）
CUTS = [T_S2, T_S3, T_S5, T_S6, T_S7, T_S8, T_ADD, T_S9, T_BAC, T_S10, T_SIG1, T_SIG2, T_SIG3, T_OUTRO]
# 三个数字逐一弹出的重音
TILE_HITS = [b(36), b(38), b(40)]

if __name__ == '__main__':
    for k, v in list(globals().items()):
        if k.startswith('T_'):
            print(f'{k:10s} {v:6.2f}s  bar {v / 2:5.2f}')
