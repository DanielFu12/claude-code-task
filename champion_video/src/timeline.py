"""全片时间轴：所有画面与音效事件都对齐到配乐的节拍网格。

配乐（Lyria 生成，见 README）实测 75 BPM：拍长 0.8 s，每 4 拍一小节，每 8 拍一个乐句（6.4 s）。
为了让开场更快、结尾的投资启示更从容，对原曲做了两处按乐句对齐的剪辑（见 MUSIC_EDIT）：
  1) 去掉开头 8 拍（6.4 s）的慢铺垫 —— 原曲 6.40 s 处成为成片 0 s，节拍网格相位不变；
  2) 在原曲 160.12 s（尾段重新进入的重拍）处把随后的 8 拍乐句再重复一次，延长投资启示段落。
成片里第 k 拍的时间仍是 B(k) = 0.12 + 0.8k。关键音乐事件（成片时间）：
  12.91 首个重击（标题）  25.7 主律动进入  108.4 全曲最强冲击  147–153 静默  153.7 / 160.1 尾段重拍  178.5 结束
"""
BEAT0, SPB = 0.12, 0.8


def B(k):
    """第 k 拍的时间（秒）"""
    return BEAT0 + SPB * k


T_TOTAL = 181.0
# 原曲剪辑：[(原曲起点, 原曲终点), ...] 依次拼接（交叉淡化 60 ms）
MUSIC_EDIT = [(6.40, 166.52), (160.12, 181.06)]

# ---------------------------------------------------------------- 章节
T_TITLE = 12.91          # 标题重击
T_RULES = B(22)          # 17.72 s 规则
RACE_K0 = 32             # 第一年开始于第 32 拍（25.72 s）
YEAR_BEATS = 8           # 每年 8 拍 = 6.4 s
YEARS = list(range(2016, 2026))


def year_t0(i):
    return B(RACE_K0 + YEAR_BEATS * i)


T_RACE_END = year_t0(10)            # 89.72 s
T_FINAL = T_RACE_END                 # 终局：两条资金曲线对撞
T_BREAK = B(129)                     # 103.32 s 音乐收束 →「为什么差距这么大？」
T_WHY = 108.40                       # 全曲最强冲击：原因分析开始
WHY_T = [T_WHY, B(144), B(152), B(160), B(168), B(176)]   # 六个原因面板，每个一个乐句
T_STATEMENT = 147.5                  # 音乐抽空：核心结论
T_VALUE = 153.71                     # 尾段重拍：投资启示
T_QUOTE = B(200)                     # 160.12 s 重复的尾段重拍：巴菲特 / 芒格
T_PRIN = B(206)                      # 164.92 s 四个原则 + 最终启示
T_END = 170.5                        # 片尾品牌动画
T_LOGO = B(216)                      # 172.92 logo 清晰浮现（配合 boom）
T_GOLD = B(218)                      # 174.52 金色「巴芒价值」
T_SUB = B(219)                       # 175.32 BUFFETT · MUNGER
T_FOLLOW = B(220)                    # 176.12 关注语
T_FADE = 178.6                       # 整体淡出至 181 s

# ---------------------------------------------------------------- 音效事件 (time, kind, kwargs)
AUDIO_EVENTS = []


def _ev(t, kind, **kw):
    AUDIO_EVENTS.append((t, kind, kw))


# 开场：第一帧就是一记低频冲击，随后心跳脉冲推进
_ev(0.0, 'boom', strength=0.9)
_ev(0.0, 'braam', strength=0.35, d=2.5)
_ev(B(2), 'pulse', strength=0.6)              # 连续 10 年
_ev(B(4), 'boom', strength=0.55)              # 两个账户
for k in (5, 6, 7):
    _ev(B(k), 'tick', strength=0.2)
_ev(B(8), 'boom', strength=0.7)               # 差多少？
for k in (9, 10, 11):
    _ev(B(k), 'tick', strength=0.22)
_ev(B(12), 'boom', strength=0.8)              # 相差超过 1000 倍
_ev(B(12), 'subdrop', strength=0.5)
_ev(T_TITLE, 'riser', d=2.6, strength=0.45)
_ev(T_TITLE, 'boom', strength=1.0)
_ev(T_TITLE, 'braam', strength=0.55)
_ev(year_t0(0), 'boom', strength=0.7)
for i in range(10):
    if i:
        _ev(year_t0(i), 'boom', strength=0.5)
    _ev(B(RACE_K0 + YEAR_BEATS * i + 4), 'pulse', strength=0.5)   # 年度收益揭晓
_ev(T_FINAL, 'subdrop', strength=0.8)
_ev(B(121), 'pulse', strength=0.55)           # 终点数字
_ev(B(123), 'boom', strength=0.6)             # 相差 1,333 倍
_ev(T_BREAK + 0.4, 'subdrop', d=2.6, strength=0.7)
_ev(T_WHY, 'riser', d=4.0, strength=0.5)
_ev(T_WHY, 'boom', strength=1.0)
_ev(T_WHY, 'braam', strength=0.6)
for t in WHY_T[1:]:
    _ev(t, 'boom', strength=0.45)
_ev(T_STATEMENT, 'subdrop', d=2.4, strength=0.75)
_ev(T_VALUE, 'boom', strength=0.75)
_ev(T_QUOTE, 'boom', strength=0.6)
_ev(T_PRIN, 'pulse', strength=0.45)
_ev(T_LOGO, 'boom', strength=0.85)
_ev(T_LOGO, 'braam', strength=0.4, d=4.0)
_ev(T_GOLD, 'pulse', strength=0.5)
_ev(T_FOLLOW, 'pulse', strength=0.3)
